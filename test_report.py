"""Test the final report generation step."""
import os
import sys
sys.path.insert(0, '.')
from agent.llm_client import call_llm, load_config

cfg = load_config()

# Simulate what the reporter generates
prompt = """
Write a final research report about the Email API market in 2026.

## Executive Summary
2-3 paragraph overview of key findings.

## Key Findings
List the top 3 findings with evidence strength ratings.

## Conclusion
What this means for a developer entering this market.

Make it about 300-500 words. Be specific and include market data.
"""

try:
    result = call_llm(prompt, system_prompt="You are a research report writer.", config=cfg)
    print(f"SUCCESS! Result length: {len(result)}")
    print(result[:500])
    print("---")
    print(f"[Last 100 chars: ...{result[-100:]}]")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
