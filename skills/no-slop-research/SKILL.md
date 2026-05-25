---
name: no-slop-research
description: "Adversarial research & validation agent — eliminates bias, gaps, and unverified claims through multi-phase interrogation with Team A (validators) vs Team B (challengers)."
version: 1.0.0
author: No-Slop Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, validation, adversarial, market-research, fact-checking]
    related_skills: [firecrawl-search, web-search, mirofish-marketing]
---

# No-Slop Research — Adversarial Research Agent

When given a topic, this skill runs a multi-phase adversarial research pipeline that eliminates three common LLM failures:
1. **Bias** toward telling the user what they want to hear
2. **Incomplete research** that misses key angles
3. **No verification** that the answer is actually correct

## Quick Start

```
/no-slop-research <topic or question>
```

Example:
```
/no-slop-research What is the current state of AI email APIs in 2025? Who are the competitors and what gaps exist?
```

## How It Works

### Phase 1: Deep Research
Spawn 4 research subagents, each focusing on a different angle:
- **Primary**: Core facts, definitions, key players, market data
- **Critical**: Criticisms, failures, risks, counter-arguments
- **Comparative**: Alternatives, competitors, market context
- **Emerging**: Recent developments, trends, future outlook

Each agent does deep web research using available search tools (TinyFish MCP, web search, Firecrawl).

### Phase 2: Profile Building
All gathered data is synthesized into a "Research Profile" — a structured document containing:
- Key findings with evidence strength ratings
- Data points and statistics
- Stakeholder map
- Contradictions found
- Knowledge gaps identified
- Source citations

### Phase 3: Adversarial Interrogation
Two opposing teams interrogate the profile:

**Team A (Validators):**
- Argues WHY findings are correct
- Cross-references claims with sources
- Rates confidence levels (0-100%)

**Team B (Challengers):**
- Actively tries to BREAK the research
- Finds missing perspectives and biased framing
- Searches for contradicting evidence
- Identifies logical gaps and assumptions
- Produces specific improvement points

### Phase 4: Synthesis & Re-test
Improvement points from Team B are fed BACK into the research. Updated profile goes through adversarial interrogation again. Loop repeats until Team B finds no significant flaws (max 3 rounds).

### Phase 5: Final Report
Clean report with:
- Executive summary
- Key findings with confidence ratings
- What was challenged and how it was addressed
- Remaining caveats
- Full source citations

## Execution Instructions

When the user provides a topic, execute this pipeline:

### Step 1: Research Phase
Spawn 4 research subagents in parallel using `delegate_task`:

```
delegate_task(tasks=[
    {
        "goal": "Deep research on [TOPIC] — PRIMARY angle: Core facts, definitions, key players, data",
        "context": "Use web search to find 5-10 high-quality sources. Extract facts, data points, statistics. Cite all sources with URLs. Return structured findings.",
        "toolsets": ["web"]
    },
    {
        "goal": "Deep research on [TOPIC] — CRITICAL angle: Criticisms, failures, risks",
        "context": "Focus on NEGATIVE side: criticisms, failures, risks, counter-arguments. Find what went wrong and why this might fail. Cite sources.",
        "toolsets": ["web"]
    },
    {
        "goal": "Deep research on [TOPIC] — COMPARATIVE angle: Alternatives, competitors",
        "context": "Focus on COMPETITIVE LANDSCAPE: alternatives, competitors, market positioning. Cite sources.",
        "toolsets": ["web"]
    },
    {
        "goal": "Deep research on [TOPIC] — EMERGING angle: Trends, future outlook",
        "context": "Focus on FUTURE and EMERGING TRENDS: recent developments, where this is heading. Cite sources.",
        "toolsets": ["web"]
    }
])
```

### Step 2: Profile Building
Combine all research results into a structured Research Profile. Use `delegate_task` with a synthesis prompt.

### Step 3: Adversarial Loop (repeat up to 3 times)
For each round:
1. Spawn Team A (validator) subagent
2. Spawn Team B (challenger) subagent
3. Extract improvement points from Team B
4. If improvement_points == 0: break (research validated!)
5. Otherwise: synthesize improvements back into profile

### Step 4: Final Report
Generate clean final report from the validated profile.

## Running the Dashboard

```bash
cd no-slop-research
pip install -r requirements.txt
python -m dashboard.app
```

Dashboard runs on http://localhost:5060

Features:
- Start research from the UI
- View active pipelines and progress
- Team A vs Team B comparison
- Improvement points tracker
- API key management (supports OpenAI, OpenRouter, Anthropic, Groq, Together AI, DeepSeek, custom)
- Research history and final report viewer

## File Structure

```
no-slop-research/
├── README.md                    # Full documentation
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py          # Main pipeline controller
│   ├── research_phase.py        # Research subagent spawning
│   ├── profile_builder.py       # Synthesizes research into profile
│   ├── validator_team.py        # Team A — validates findings
│   ├── challenger_team.py       # Team B — finds flaws
│   ├── synthesizer.py           # Merges improvement points back
│   └── report_generator.py      # Final output
├── dashboard/
│   ├── app.py                   # Flask dashboard (port 5060)
│   └── templates/
│       └── index.html           # Dark-themed dashboard UI
├── skills/
│   └── no-slop-research/
│       └── SKILL.md             # This file
└── examples/
    └── sample_run.md            # Example research run
```

## Pitfalls

- **API keys required**: You need at least one LLM API key configured (OpenAI, OpenRouter, etc.)
- **Subagent timeout**: Each research agent has a 300s timeout. Deep research topics may need longer.
- **Max rounds**: Default 3 rounds. Increase for complex topics, decrease for quick checks.
- **Token usage**: Each adversarial round uses significant tokens. Budget accordingly.
- **Web search quality**: Results depend on available search tools (TinyFish MCP, web search).

## Verification

After running, verify:
1. Dashboard loads at http://localhost:5060
2. API key is saved and shows as "Active"
3. Research starts and progresses through phases
4. Final report has confidence ratings and source citations
5. Improvement points are tracked per round
