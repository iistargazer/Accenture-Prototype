"""
Real Anthropic provider. Same interface as MockLLMProvider - swap it in
run_scenarios.py and nothing else in the codebase needs to change.

Setup:
  1. Get a key at console.anthropic.com (new accounts get a one-time free
     trial credit - no credit card needed, phone verification required).
  2. export ANTHROPIC_API_KEY=sk-ant-...
  3. In run_scenarios.py: replace
        from llm.mock_provider import MockLLMProvider
        llm = MockLLMProvider()
     with
        from llm.anthropic_provider import AnthropicProvider
        llm = AnthropicProvider()

Verify MODEL_NAME and per-token pricing against
https://docs.claude.com/en/docs/about-claude/pricing before the demo -
both change over time and this file may be out of date by the time you
read it.
"""
import os
import time
import json
import requests
from .base_provider import LLMProvider, LLMResult

MODEL_NAME = "claude-sonnet-5"          # verify against docs.claude.com
API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Verify current rates at https://docs.claude.com/en/docs/about-claude/pricing
COST_PER_1K_INPUT = 0.003
COST_PER_1K_OUTPUT = 0.015

SYSTEM_PROMPT = """You are a KPI narrative assistant. You will be given a
structured evidence JSON object describing a business metric's movement.

Hard rules:
- Only use numbers and facts present in the evidence JSON. Never invent,
  estimate, or "fill in" a figure that isn't there.
- If evidence.should_abstain is true, do NOT explain a root cause. Say
  plainly that confidence is too low, cite the confidence_reasons given,
  and suggest what additional evidence would help.
- Match the requested tone/detail level exactly - a summary persona gets
  2-3 sentences with the bottom line and one action; a full/detailed
  persona gets the driver-by-driver breakdown with methods and sources.
- Never state a correlation as if it were a proven cause.
"""


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set ANTHROPIC_API_KEY (see llm/anthropic_provider.py docstring)")

    def generate_narrative(self, evidence: dict, persona_key: str, persona_cfg: dict) -> LLMResult:
        user_prompt = (
            f"Persona: {persona_cfg['label']} (detail_level={persona_cfg['detail_level']}, "
            f"tone={persona_cfg['tone']})\n\n"
            f"Evidence JSON:\n{json.dumps(evidence, indent=2)}\n\n"
            f"Write the narrative for this persona now."
        )

        start = time.perf_counter()
        resp = requests.post(
            API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "max_tokens": 500,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()

        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + (output_tokens / 1000 * COST_PER_1K_OUTPUT)

        return LLMResult(
            text=text,
            model=MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1),
            estimated_cost_usd=round(cost, 5),
        )
