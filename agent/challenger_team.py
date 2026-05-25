"""
Phase 3b: Challenger Team (Team B) — Takes the research profile and actively
tries to BREAK it. Looks for missing perspectives, biased framing,
cherry-picked data, contradicting evidence, logical gaps, and unstated assumptions.
"""

import re


def _build_challenge_prompt(topic: str, profile: str, round_num: int) -> str:
    """Build the prompt for the challenger team."""
    return f"""You are a CHALLENGER — a professional skeptic and devil's advocate.
Your job is to take a Research Profile and try to DESTROY it.
Find every flaw, gap, bias, and weakness. Be ruthless but constructive.

TOPIC: {topic}
CHALLENGE ROUND: {round_num}

RESEARCH PROFILE:
{profile[:12000]}

YOUR MISSION:
This research profile claims to be comprehensive and accurate. YOUR JOB IS TO PROVE IT WRONG.

Attack from these angles:

1. MISSING PERSPECTIVES
   - Whose voice is absent? Who benefits from this framing?
   - What geographic, demographic, or ideological viewpoints are missing?

2. BIASED FRAMING
   - Is the research cherry-picking favorable data?
   - Are conclusions stronger than the evidence warrants?
   - Is there confirmation bias in source selection?

3. CONTRADICTING EVIDENCE
   - What evidence exists that contradicts the profile's claims?
   - Are there credible sources that tell a different story?

4. LOGICAL GAPS
   - Where does the reasoning jump from evidence to conclusion?
   - What assumptions are being made without evidence?

5. STALENESS & CONTEXT
   - Is any data outdated?
   - Has the landscape changed since sources were published?

6. ADVERSARIAL SCENARIOS
   - What would a critic say about each major finding?
   - If you had to debunk this in a debate, what would you use?

OUTPUT FORMAT:

## CHALLENGE SUMMARY
Overall assessment: How vulnerable is this research?
Rate: BULLETPROOF / MINOR GAPS / SIGNIFICANT FLAWS / CRITICALLY WEAK

## ATTACK SURFACE
For each weakness found:
- **Weakness:** [what's wrong]
- **Severity:** [Critical / Major / Minor]
- **Evidence:** [what contradicts or undermines this]
- **Fix Required:** [specific action to address it]

## IMPROVEMENT POINTS
Numbered list of SPECIFIC, ACTIONABLE improvements needed.
Each point should be concrete enough that a researcher could execute it.

Format each improvement point as:
[IMPROVE-1] <description of what needs to be fixed and how>
[IMPROVE-2] <description>
...

## CHALLENGE VERDICT
What's the single biggest vulnerability in this research?
What would make this 10x stronger?

Be brutal. Be specific. Be constructive. Your goal is to make this research UNBREAKABLE."""


class ChallengerTeam:
    """Team B — challenges research findings and identifies flaws."""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def challenge(self, topic: str, profile: str, round_num: int) -> str:
        """
        Run adversarial challenge on a research profile.
        Returns challenge analysis.
        """
        prompt = _build_challenge_prompt(topic, profile, round_num)

        # The Hermes skill executes this as a subagent
        # In standalone mode, return the prompt
        return prompt

    def extract_improvement_points(self, challenge_result: str) -> list:
        """
        Extract numbered improvement points from the challenge result.
        Returns list of improvement point strings.
        """
        points = []
        # Look for [IMPROVE-N] pattern
        pattern = r'\[IMPROVE-\d+\]\s*(.+?)(?=\[IMPROVE-|\Z)'
        matches = re.findall(pattern, challenge_result, re.DOTALL)
        if matches:
            for m in matches:
                point = m.strip().split("\n")[0].strip()
                if point:
                    points.append(point)
            return points

        # Fallback: look for numbered improvement points
        lines = challenge_result.split("\n")
        in_improvements = False
        for line in lines:
            if "improvement point" in line.lower() or "improvements needed" in line.lower():
                in_improvements = True
                continue
            if in_improvements:
                line_stripped = line.strip()
                if line_stripped and (line_stripped[0].isdigit() or line_stripped.startswith("-") or line_stripped.startswith("*")):
                    # Clean up the point
                    point = line_stripped.lstrip("0123456789.-*) ").strip()
                    if point and len(point) > 10:
                        points.append(point)
                elif line_stripped.startswith("##") and points:
                    break  # Next section

        return points

    def assess_vulnerability(self, challenge_result: str) -> str:
        """
        Extract the overall vulnerability assessment.
        Returns: bulletproof, minor_gaps, significant_flaws, or critically_weak
        """
        result_lower = challenge_result.lower()
        if "bulletproof" in result_lower:
            return "bulletproof"
        elif "critically weak" in result_lower:
            return "critically_weak"
        elif "significant flaw" in result_lower:
            return "significant_flaws"
        elif "minor gap" in result_lower:
            return "minor_gaps"
        return "unknown"
