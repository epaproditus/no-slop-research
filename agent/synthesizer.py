"""
Phase 4: Synthesizer — Merges improvement points from the Challenger Team
back into the research profile, triggering targeted re-research to address weaknesses.
"""


def _build_synthesis_prompt(topic: str, profile: str, improvement_points: list,
                            validation_result: str, challenge_result: str,
                            round_num: int) -> str:
    """Build the prompt for synthesis."""
    improvements_text = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(improvement_points))

    return f"""You are a RESEARCH SYNTHESIZER. Your job is to take a Research Profile,
the adversarial challenge results, and merge improvements back into a stronger profile.

TOPIC: {topic}
SYNTHESIS ROUND: {round_num}

CURRENT RESEARCH PROFILE:
{profile[:10000]}

VALIDATOR TEAM (Team A) FINDINGS:
{validation_result[:4000]}

CHALLENGER TEAM (Team B) ATTACK:
{challenge_result[:4000]}

IMPROVEMENT POINTS TO ADDRESS:
{improvements_text}

YOUR MISSION:
Rewrite the Research Profile to address EVERY improvement point while preserving
the strong findings that survived validation.

PROCESS:
1. Keep findings that the Validator rated as Strong/Moderate evidence
2. For each improvement point, either:
   a. Add missing information/address the gap
   b. Weaken claims that the Challenger proved were overstated
   c. Add caveats and nuance where needed
   d. Flag for further research if the gap can't be filled from existing data
3. Re-structure the profile to be more balanced and comprehensive
4. Update confidence ratings based on both teams' input

OUTPUT FORMAT:
Return the COMPLETE updated Research Profile in the same structure as the original:
- Executive Summary (updated)
- Key Findings (with updated evidence ratings)
- Data Points
- Stakeholder Map
- Contradictions & Tensions (updated)
- Knowledge Gaps (updated — what still needs research)
- Sources (updated)
- Confidence Assessment (updated)

Mark any NEW research areas with [NEEDS-RESEARCH] tags so they can be
investigated in the next round if needed.

Be thorough. This is the iterative improvement that makes research bulletproof."""


class Synthesizer:
    """Merges improvement points back into the research profile."""

    def merge(self, topic: str, original_profile: str, improvement_points: list,
              validation_result: str, challenge_result: str, round_num: int) -> str:
        """
        Merge improvement points into the profile.
        Returns updated Research Profile.
        """
        prompt = _build_synthesis_prompt(
            topic=topic,
            profile=original_profile,
            improvement_points=improvement_points,
            validation_result=validation_result,
            challenge_result=challenge_result,
            round_num=round_num
        )

        # The Hermes skill executes this as a subagent
        # In standalone mode, return the prompt
        return prompt

    def extract_needs_research(self, synthesized_profile: str) -> list:
        """
        Extract items tagged with [NEEDS-RESEARCH] for potential re-research.
        """
        import re
        pattern = r'\[NEEDS-RESEARCH\]\s*(.+?)(?=\n|$)'
        return re.findall(pattern, synthesized_profile)

    def calculate_improvement_delta(self, original_profile: str, updated_profile: str) -> dict:
        """
        Calculate how much the profile changed between rounds.
        Returns metrics on improvement.
        """
        original_len = len(original_profile)
        updated_len = len(updated_profile)

        # Count confidence mentions
        import re
        original_high = len(re.findall(r'high confidence', original_profile.lower()))
        updated_high = len(re.findall(r'high confidence', updated_profile.lower()))

        original_low = len(re.findall(r'low confidence', original_profile.lower()))
        updated_low = len(re.findall(r'low confidence', updated_profile.lower()))

        return {
            "size_change": updated_len - original_len,
            "size_pct": round((updated_len - original_len) / max(original_len, 1) * 100, 1),
            "high_confidence_change": updated_high - original_high,
            "low_confidence_change": original_low - updated_low,  # Positive = improvement
        }
