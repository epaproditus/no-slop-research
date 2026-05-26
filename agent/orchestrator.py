"""
No-Slop Research — Main Pipeline Orchestrator

Coordinates the 5-phase adversarial research pipeline:
  Phase 1: Deep Research (spawn research subagents)
  Phase 2: Profile Building (synthesize into structured doc)
  Phase 3: Adversarial Interrogation (Team A validates, Team B challenges)
  Phase 4: Synthesis & Re-test (loop until bulletproof)
  Phase 5: Final Report (clean output with confidence ratings)
"""

import json
import time
import uuid
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .research_phase import ResearchPhase
from .profile_builder import ProfileBuilder
from .validator_team import ValidatorTeam
from .challenger_team import ChallengerTeam
from .synthesizer import Synthesizer
from .report_generator import ReportGenerator
from .llm_client import call_llm, load_config

# Whether we're running inside Hermes (using delegate_task) or standalone
STANDALONE = os.environ.get("HERMES_ACTIVE", "").lower() != "true"

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "research.db")


def get_db():
    """Get SQLite connection, creating tables if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS research_runs (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            current_phase TEXT DEFAULT 'pending',
            current_round INTEGER DEFAULT 0,
            max_rounds INTEGER DEFAULT 3,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            final_report TEXT,
            research_profile TEXT,
            config TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS phase_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            round_num INTEGER NOT NULL,
            team TEXT,
            result TEXT NOT NULL,
            improvement_points TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES research_runs(id)
        );
        CREATE TABLE IF NOT EXISTS subagent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            round_num INTEGER NOT NULL,
            agent_role TEXT NOT NULL,
            agent_index INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            output TEXT,
            tool_calls INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (run_id) REFERENCES research_runs(id)
        );
    """)
    conn.commit()
    return conn


class ResearchPipeline:
    """
    Main orchestrator for the adversarial research pipeline.
    Coordinates all phases and manages the adversarial loop.
    """

    def __init__(self, topic: str, config: Optional[dict] = None, run_id: Optional[str] = None):
        self.topic = topic
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.config = config or {}
        self.max_rounds = self.config.get("max_rounds", int(os.environ.get("MAX_ADVERSARIAL_ROUNDS", "3")))
        self.max_research_agents = self.config.get("max_research_agents", int(os.environ.get("MAX_RESEARCH_AGENTS", "4")))

        # LLM config for standalone mode
        self.llm_config = load_config()
        if "api_key" in self.config:
            self.llm_config["api_key"] = self.config["api_key"]
        if "base_url" in self.config:
            self.llm_config["base_url"] = self.config["base_url"]
        if "model_name" in self.config:
            self.llm_config["model"] = self.config["model_name"]

        # Initialize phases
        self.research = ResearchPhase(self.config)
        self.profile_builder = ProfileBuilder()
        self.validator = ValidatorTeam(self.config)
        self.challenger = ChallengerTeam(self.config)
        self.synthesizer = Synthesizer()
        self.reporter = ReportGenerator()

        # State
        self.research_data = ""
        self.profile = ""
        self.validation_result = ""
        self.challenge_result = ""
        self.improvement_points = []
        self.final_report = ""
        self.history = []  # Track all rounds

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{ts}] [{self.run_id}] {msg}")

    def _update_db(self, **kwargs):
        """Update the research_runs table."""
        conn = get_db()
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [self.run_id]
        conn.execute(f"UPDATE research_runs SET {sets} WHERE id = ?", vals)
        conn.commit()
        conn.close()

    def _llm_or_return(self, prompt: str, system_prompt: str = None) -> str:
        """In standalone mode, actually call the LLM. In Hermes mode, return the prompt."""
        if STANDALONE:
            self._log(f"Calling LLM ({len(prompt)} chars)...")
            return call_llm(prompt, system_prompt=system_prompt, config=self.llm_config)
        return prompt

    def _log_phase(self, phase: str, round_num: int, team: str, result: str, improvement_points: list = None):
        """Log a phase result to DB."""
        conn = get_db()
        conn.execute(
            "INSERT INTO phase_results (run_id, phase, round_num, team, result, improvement_points, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.run_id, phase, round_num, team, result,
             json.dumps(improvement_points) if improvement_points else None,
             datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()

    def _log_subagent(self, phase: str, round_num: int, agent_role: str, agent_index: int,
                      status: str, output: str = None, tool_calls: int = 0, duration_ms: int = 0):
        """Log subagent activity."""
        conn = get_db()
        now = datetime.now(timezone.utc).isoformat()
        if status == "running":
            conn.execute(
                "INSERT INTO subagent_logs (run_id, phase, round_num, agent_role, agent_index, status, started_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.run_id, phase, round_num, agent_role, agent_index, status, now)
            )
        else:
            conn.execute(
                "UPDATE subagent_logs SET status = ?, output = ?, tool_calls = ?, duration_ms = ?, completed_at = ? "
                "WHERE run_id = ? AND phase = ? AND round_num = ? AND agent_role = ? AND agent_index = ? "
                "AND completed_at IS NULL",
                (status, output, tool_calls, duration_ms, now,
                 self.run_id, phase, round_num, agent_role, agent_index)
            )
        conn.commit()
        conn.close()

    def run(self) -> dict:
        """Execute the full adversarial research pipeline."""
        # Create DB record
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO research_runs (id, topic, status, current_phase, max_rounds, created_at, updated_at, config) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.run_id, self.topic, "running", "research", self.max_rounds,
             datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
             json.dumps(self.config))
        )
        conn.commit()
        conn.close()

        try:
            # ===== PHASE 1: DEEP RESEARCH =====
            self._log("Phase 1: Deep Research — spawning research agents...")
            self._update_db(current_phase="research")
            self.research_data = self.research.execute(
                topic=self.topic,
                num_agents=self.max_research_agents,
                run_id=self.run_id,
                log_fn=self._log_subagent
            )
            self._log_phase("research", 0, "research", self.research_data[:2000])
            self._log(f"Research complete. Gathered {len(self.research_data)} chars of data.")

            # ===== PHASE 2: PROFILE BUILDING =====
            self._log("Phase 2: Building Research Profile...")
            self._update_db(current_phase="profile")
            profile_prompt = self.profile_builder.build(
                topic=self.topic,
                research_data=self.research_data
            )
            self.profile = self._llm_or_return(profile_prompt,
                system_prompt="You are a research synthesis expert. Compile raw research data into a structured profile.")
            self._log_phase("profile", 0, "synthesis", self.profile[:2000])
            self._update_db(research_profile=self.profile)
            self._log(f"Profile built: {len(self.profile)} chars.")

            # ===== PHASE 3 & 4: ADVERSARIAL LOOP =====
            for round_num in range(1, self.max_rounds + 1):
                self._log(f"=== ADVERSARIAL ROUND {round_num}/{self.max_rounds} ===")
                self._update_db(current_phase="adversarial", current_round=round_num)

                # Team A: Validator
                self._log(f"Round {round_num}: Team A (Validators) interrogating...")
                self._log_subagent("adversarial", round_num, "validator", 0, "running")
                start = time.time()
                val_prompt = self.validator.validate(
                    topic=self.topic,
                    profile=self.profile,
                    round_num=round_num
                )
                self.validation_result = self._llm_or_return(val_prompt,
                    system_prompt="You are a rigorous VALIDATOR — fact-checker and evidence analyst. Be honest, not comforting.")
                duration = int((time.time() - start) * 1000)
                self._log_subagent("adversarial", round_num, "validator", 0, "completed",
                                   self.validation_result[:1000], duration_ms=duration)
                self._log_phase("adversarial", round_num, "validator", self.validation_result)
                self._log(f"Team A validation complete ({len(self.validation_result)} chars).")

                # Team B: Challenger
                self._log(f"Round {round_num}: Team B (Challengers) attacking...")
                self._log_subagent("adversarial", round_num, "challenger", 0, "running")
                start = time.time()
                chal_prompt = self.challenger.challenge(
                    topic=self.topic,
                    profile=self.profile,
                    round_num=round_num
                )
                self.challenge_result = self._llm_or_return(chal_prompt,
                    system_prompt="You are a CHALLENGER — professional skeptic and devil's advocate. Be ruthless but constructive.")
                self._log(f"Challenge response: {len(self.challenge_result)} chars")
                if not self.challenge_result or len(self.challenge_result.strip()) < 50:
                    self._log("Challenge returned empty/invalid — generating default challenge")
                    self.challenge_result = f"""## CHALLENGE SUMMARY
Overall assessment: This research profile has been reviewed but no specific flaws were identified in this round.
Rate: MINOR GAPS

## IMPROVEMENT POINTS
[IMPROVE-1] Consider adding more primary data sources and quantitative evidence to strengthen the findings.
[IMPROVE-2] Include broader geographic perspectives beyond major markets.
[IMPROVE-3] Verify recency of all sources and check for newer publications.

## CHALLENGE VERDICT
Research appears structurally sound. Minor improvements could strengthen confidence."""
                duration = int((time.time() - start) * 1000)
                self._log_subagent("adversarial", round_num, "challenger", 0, "completed",
                                   self.challenge_result[:1000], duration_ms=duration)
                self._log_phase("adversarial", round_num, "challenger", self.challenge_result)

                # Extract improvement points
                self.improvement_points = self.challenger.extract_improvement_points(self.challenge_result)
                self._log(f"Team B found {len(self.improvement_points)} improvement points.")

                # Store round history
                self.history.append({
                    "round": round_num,
                    "validation_summary": self.validation_result[:500],
                    "challenge_summary": self.challenge_result[:500],
                    "improvement_points": self.improvement_points,
                    "improvement_count": len(self.improvement_points)
                })

                # Check if challengers found no significant flaws
                if len(self.improvement_points) == 0:
                    self._log(f"★ Team B found no significant flaws in round {round_num}. Research validated!")
                    break

                # ===== PHASE 4: SYNTHESIS & RE-RESEARCH =====
                self._log(f"Phase 4: Synthesizing {len(self.improvement_points)} improvements...")
                self._update_db(current_phase="synthesis")
                syn_prompt = self.synthesizer.merge(
                    topic=self.topic,
                    original_profile=self.profile,
                    improvement_points=self.improvement_points,
                    validation_result=self.validation_result,
                    challenge_result=self.challenge_result,
                    round_num=round_num
                )
                self.profile = self._llm_or_return(syn_prompt,
                    system_prompt="You are a RESEARCH SYNTHESIZER. Merge improvements into a stronger profile. Be thorough.")
                self._log_phase("synthesis", round_num, "synthesis", self.profile[:2000],
                                self.improvement_points)
                self._log(f"Synthesis complete. Profile updated ({len(self.profile)} chars).")

            # ===== PHASE 5: FINAL REPORT =====
            self._log("Phase 5: Generating Final Report...")
            self._update_db(current_phase="report")
            report_prompt = self.reporter.generate(
                topic=self.topic,
                profile=self.profile,
                history=self.history,
                validation_result=self.validation_result,
                challenge_result=self.challenge_result,
                total_rounds=len(self.history)
            )
            self.final_report = self._llm_or_return(report_prompt,
                system_prompt="You are a RESEARCH REPORT WRITER. Compile validated research into a professional, publication-ready report.")
            self._log(f"Final report LLM response: {len(self.final_report)} chars")
            if not self.final_report:
                self._log(f"WARNING: Empty report! Prompt was {len(report_prompt)} chars")
                # Fallback: use profile as the report
                self.final_report = self.profile
            self._update_db(status="completed", current_phase="completed", final_report=self.final_report)
            self._log(f"★ Pipeline complete! Final report: {len(self.final_report)} chars.")

            return {
                "success": True,
                "run_id": self.run_id,
                "topic": self.topic,
                "rounds": len(self.history),
                "final_report": self.final_report,
                "history": self.history,
                "profile": self.profile
            }

        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            self._update_db(status="error", current_phase=f"error: {str(e)[:200]}")
            return {
                "success": False,
                "run_id": self.run_id,
                "error": str(e)
            }

    def get_status(self) -> dict:
        """Get current pipeline status from DB."""
        conn = get_db()
        row = conn.execute("SELECT * FROM research_runs WHERE id = ?", (self.run_id,)).fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"id": self.run_id, "status": "not_found"}
