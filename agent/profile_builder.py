"""
Phase 2: Profile Builder — Synthesizes raw research data into a structured
Research Profile document that becomes the basis for adversarial interrogation.
"""


def _build_profile_prompt(topic: str, research_data: str) -> str:
    """Build the prompt for profile synthesis."""
    return f"""You are a research synthesis expert. Your job is to take raw research data and
compile it into a STRUCTURED RESEARCH PROFILE.

TOPIC: {topic}

RAW RESEARCH DATA:
{research_data[:15000]}

Create a Research Profile with these EXACT sections:

## 1. EXECUTIVE SUMMARY
2-3 paragraph overview of what we know about this topic.

## 2. KEY FINDINGS
Bullet list of the most important findings, each with:
- The claim
- Supporting evidence strength (Strong / Moderate / Weak)
- Source quality assessment

## 3. DATA POINTS
Specific numbers, statistics, metrics — presented in a clean list.

## 4. STAKEHOLDER MAP
Key entities, people, companies, or forces involved and their positions.

## 5. CONTRADICTIONS & TENSIONS
Any conflicting information found during research. Note what each side claims.

## 6. KNOWLEDGE GAPS
What we DON'T know or couldn't verify. Areas where data is missing or outdated.

## 7. SOURCES
Full list of all sources cited, with URLs where available.

## 8. CONFIDENCE ASSESSMENT
Overall confidence level: HIGH / MEDIUM / LOW
Justify why. Note which areas have strong evidence vs speculation.

Be thorough but concise. Every claim should be traceable to a source.
Do NOT fill gaps with speculation — mark them as gaps."""


class ProfileBuilder:
    """Synthesizes raw research data into a structured Research Profile."""

    def build(self, topic: str, research_data: str) -> str:
        """
        Build a Research Profile from raw research data.

        When running inside Hermes, this uses a subagent for synthesis.
        When running standalone, it formats the data directly.
        """
        prompt = _build_profile_prompt(topic, research_data)

        # In standalone mode, return the formatted prompt
        # The Hermes skill will execute this as a subagent
        return prompt

    def build_from_summary(self, topic: str, research_data: str, summary: str) -> str:
        """
        Build a profile when a synthesis summary is already available
        (e.g., from a Hermes subagent result).
        """
        return f"""# Research Profile: {topic}

{summary}

---
Profile built from research data ({len(research_data)} chars of raw data).
"""