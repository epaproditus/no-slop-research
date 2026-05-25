"""
Phase 3a: Validator Team (Team A) — Takes the research profile and argues
WHY the findings are correct. Cross-references claims with sources,
identifies strong evidence chains, and rates confidence levels.
"""


def _build_validation_prompt(topic: str, profile: str, round_num: int) -> str:
    """Build the prompt for the validator team."""
    return f"""You are a VALIDATOR — a rigorous fact-checker and evidence analyst.
Your job is to take a Research Profile and determine how VALID and RELIABLE its findings are.

TOPIC: {topic}
VALIDATION ROUND: {round_num}

RESEARCH PROFILE:
{profile[:12000]}

YOUR MISSION:
Analyze every claim in this profile and assess its validity. Be RIGOROUS but FAIR.

For each key finding, evaluate:
1. SOURCE QUALITY — Are the sources credible? Primary or secondary? Biased?
2. EVIDENCE CHAIN — Does the evidence logically support the claim?
3. CONSISTENCY — Do multiple sources agree? Are there contradictions?
4. COMPLETENESS — Is important context missing?
5. RECENCY — Is the information current or potentially outdated?

OUTPUT FORMAT:

## VALIDATION SUMMARY
Overall assessment: How reliable is this research profile?
Rate: HIGH CONFIDENCE / MODERATE CONFIDENCE / LOW CONFIDENCE

## CLAIM-BY-CLAIM ANALYSIS
For each key finding:
- **Claim:** [what the profile states]
- **Evidence Quality:** [Strong/Moderate/Weak]
- **Source Check:** [do sources actually support this?]
- **Confidence Rating:** [0-100]%
- **Notes:** [any caveats or concerns]

## STRONGEST FINDINGS
Which findings have the strongest evidence? Why?

## WEAKEST FINDINGS
Which findings are most questionable? Why?

## VALIDATION VERDICT
Is this research profile ready to be published as reliable?
If not, what specific improvements are needed?

Be honest. Your job is truth, not comfort."""


class ValidatorTeam:
    """Team A — validates research findings and rates confidence."""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def validate(self, topic: str, profile: str, round_num: int) -> str:
        """
        Run validation on a research profile.
        Returns validation analysis.
        """
        prompt = _build_validation_prompt(topic, profile, round_num)

        # The Hermes skill executes this as a subagent
        # In standalone mode, return the prompt
        return prompt

    def extract_confidence_score(self, validation_result: str) -> float:
        """
        Extract an overall confidence score from the validation result.
        Returns 0.0 - 1.0
        """
        result_lower = validation_result.lower()

        if "high confidence" in result_lower:
            return 0.85
        elif "moderate confidence" in result_lower:
            return 0.6
        elif "low confidence" in result_lower:
            return 0.35
        else:
            return 0.5

    def get_claim_scores(self, validation_result: str) -> list:
        """
        Parse individual claim confidence ratings from validation output.
        Returns list of dicts with claim and score.
        """
        claims = []
        lines = validation_result.split("\n")
        current_claim = None

        for line in lines:
            line_lower = line.lower().strip()
            if "**claim:**" in line_lower or "claim:" in line_lower:
                current_claim = line.split(":", 1)[-1].strip().strip("*").strip()
            elif "confidence rating" in line_lower and current_claim:
                # Try to extract percentage
                import re
                pct_match = re.search(r'(\d+)%', line)
                if pct_match:
                    score = int(pct_match.group(1)) / 100.0
                    claims.append({"claim": current_claim, "score": score})
                current_claim = None

        return claims
