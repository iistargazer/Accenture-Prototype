"""
Google Gemini provider - fallback if an Anthropic key isn't available in
time. Google AI Studio (aistudio.google.com) issues free-tier API keys
with no credit card required.

IMPORTANT: Gemini's free-tier model names change frequently (this
environment's knowledge may be stale by the time you read this). Before
using this file:
  1. Go to aistudio.google.com, create an API key.
  2. Check the current free-tier model list on the page (look for a
     Flash-class model marked free) and set MODEL_NAME below to match
     EXACTLY what's listed - do not guess.
  3. export GEMINI_API_KEY=...
  4. In run_scenarios.py: swap in `from llm.gemini_provider import
     GeminiProvider; llm = GeminiProvider()`.

Gemini doesn't return a cost figure the way Anthropic does on the free
tier (it's $0 by definition there) - COST_PER_1K_* below are placeholders
for when/if you move off the free tier; check ai.google.dev/pricing.
"""
import os
import time
import json
import requests
from .base_provider import LLMProvider, LLMResult

MODEL_NAME = "gemini-flash-latest"   # confirmed reachable via curl test - verify still current before demo
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 8   # free-tier models occasionally return 503 "high demand" - worth a few retries

COST_PER_1K_INPUT = 0.0    # free tier - update if you move to paid
COST_PER_1K_OUTPUT = 0.0

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


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set GEMINI_API_KEY (see llm/gemini_provider.py docstring)")

    def generate_narrative(self, evidence: dict, persona_key: str, persona_cfg: dict) -> LLMResult:
        user_prompt = (
            f"Persona: {persona_cfg['label']} (detail_level={persona_cfg['detail_level']}, "
            f"tone={persona_cfg['tone']})\n\n"
            f"Evidence JSON:\n{json.dumps(evidence, indent=2)}\n\n"
            f"Write the narrative for this persona now."
        )

        start = time.perf_counter()
        last_error = None
        for attempt in range(MAX_RETRIES):
            resp = requests.post(
                f"{API_BASE}/{MODEL_NAME}:generateContent",
                headers={"content-type": "application/json", "x-goog-api-key": self.api_key},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                },
                timeout=30,
            )
            if resp.status_code == 503 and attempt < MAX_RETRIES - 1:
                # Free-tier model overloaded ("high demand") - back off and retry
                # rather than fail the whole pipeline run over a transient blip.
                last_error = resp.text
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            break
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + (output_tokens / 1000 * COST_PER_1K_OUTPUT)

        return LLMResult(
            text=text,
            model=MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1),
            estimated_cost_usd=round(cost, 5),
        )
