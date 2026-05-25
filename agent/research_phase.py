"""
Phase 1: Deep Research — Spawns multiple research subagents to gather
comprehensive data on the topic from diverse angles.
"""

import os
import json
import time
import subprocess
from typing import Callable, Optional


# Research angles — each subagent focuses on a different perspective
RESEARCH_ANGLES = [
    {
        "name": "primary",
        "focus": "Core facts, definitions, key players, market data, and primary sources",
        "instruction": "Gather the most comprehensive primary research possible. Focus on facts, data points, statistics, key entities, and foundational knowledge."
    },
    {
        "name": "critical",
        "focus": "Criticisms, counter-arguments, failures, risks, and negative outcomes",
        "instruction": "Focus specifically on the NEGATIVE side: criticisms, failures, risks, counter-arguments, things that went wrong, and reasons this might fail or be wrong."
    },
    {
        "name": "comparative",
        "focus": "Alternatives, competitors, adjacent approaches, and market context",
        "instruction": "Focus on the COMPETITIVE LANDSCAPE: alternatives, competitors, adjacent approaches, how others solve the same problem, and market positioning."
    },
    {
        "name": "emerging",
        "focus": "Recent developments, trends, future outlook, and emerging signals",
        "instruction": "Focus on the FUTURE and EMERGING TRENDS: recent developments, where this is heading, new research, upcoming changes, and forward-looking signals."
    }
]


def _build_research_prompt(topic: str, angle: dict) -> str:
    """Build a self-contained research prompt for a subagent."""
    return f"""You are a deep research agent. Your job is to gather COMPREHENSIVE, FACTUAL research on the following topic.

TOPIC: {topic}

YOUR ANGLE: {angle['name'].upper()} — {angle['focus']}

INSTRUCTIONS:
{angle['instruction']}

RESEARCH PROCESS:
1. Use web search to find 5-10 high-quality sources on this topic
2. For each source, extract key facts, data points, and insights
3. Look for SPECIFIC numbers, dates, names, and verifiable claims
4. Note any contradictions you find between sources
5. Identify gaps in available information

OUTPUT FORMAT:
Return your findings as a structured research dump with:
- KEY FACTS: Bullet list of verified facts with source URLs
- DATA POINTS: Specific numbers, statistics, metrics
- CONTRADICTIONS: Any conflicting information found
- GAPS: What you couldn't find or verify
- SOURCES: Full list of URLs consulted

Be thorough. Be specific. Cite everything. Do NOT fabricate information you cannot find."""


class ResearchPhase:
    """Spawns research subagents to gather comprehensive data on a topic."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.subagent_timeout = self.config.get("subagent_timeout", 300)

    def execute(self, topic: str, num_agents: int = 4, run_id: str = "",
                log_fn: Optional[Callable] = None) -> str:
        """
        Spawn research subagents and collect their findings.
        Returns concatenated research data from all agents.

        When running inside Hermes, uses delegate_task.
        When running standalone, uses direct web search.
        """
        angles = RESEARCH_ANGLES[:num_agents]
        results = []

        # Check if we're running inside Hermes
        hermes_available = self._check_hermes_available()

        if hermes_available:
            results = self._run_via_hermes(topic, angles, run_id, log_fn)
        else:
            results = self._run_direct(topic, angles)

        # Combine all research into one document
        combined = self._combine_results(topic, results)
        return combined

    def _check_hermes_available(self) -> bool:
        """Check if Hermes delegate_task is available."""
        return os.environ.get("HERMES_ACTIVE", "").lower() == "true"

    def _run_via_hermes(self, topic: str, angles: list, run_id: str,
                        log_fn: Optional[Callable] = None) -> list:
        """Run research using Hermes delegate_task."""
        # This will be called from the Hermes skill context
        # The actual delegate_task calls happen at the skill level
        # This method prepares the prompts and returns them
        prompts = []
        for i, angle in enumerate(angles):
            prompt = _build_research_prompt(topic, angle)
            prompts.append({
                "angle": angle["name"],
                "prompt": prompt,
                "index": i
            })
        return prompts  # Return prompts for the skill to execute

    def _run_direct(self, topic: str, angles: list) -> list:
        """Run research directly using available tools (standalone mode)."""
        results = []
        for angle in angles:
            result = self._research_angle(topic, angle)
            results.append({
                "angle": angle["name"],
                "data": result
            })
        return results

    def _research_angle(self, topic: str, angle: dict) -> str:
        """Research a single angle using available search tools."""
        # This uses a subprocess to call a research script
        # In standalone mode, we use the research_script.py
        script_path = os.path.join(os.path.dirname(__file__), "research_script.py")
        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    ["python3", script_path, topic, angle["name"]],
                    capture_output=True, text=True, timeout=self.subagent_timeout
                )
                if result.returncode == 0:
                    return result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Fallback: return the prompt for manual execution
        return _build_research_prompt(topic, angle)

    def _combine_results(self, topic: str, results: list) -> str:
        """Combine research results from all agents into one document."""
        sections = [f"# Research Data: {topic}\n"]
        for r in results:
            if isinstance(r, dict):
                angle = r.get("angle", "unknown")
                data = r.get("data", "")
            else:
                angle = "unknown"
                data = str(r)
            sections.append(f"\n## Research Angle: {angle.upper()}\n\n{data}\n")
            sections.append("---\n")
        return "\n".join(sections)


def get_research_prompts(topic: str, num_agents: int = 4) -> list:
    """
    Public helper: get research prompts for manual execution.
    Used by the Hermes skill to spawn delegate_task calls.
    """
    angles = RESEARCH_ANGLES[:num_agents]
    return [_build_research_prompt(topic, angle) for angle in angles]
