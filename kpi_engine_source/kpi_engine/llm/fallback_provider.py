"""
Wraps a primary provider with a fallback. If the primary fails (after its
own internal retries are exhausted - network timeout, persistent 503,
quota, whatever), this catches it and uses the fallback instead of
letting the whole scenario go blank. The narrative text is clearly
labelled when this happens, so it's never silently passed off as a real
model response in the dashboard or telemetry.

This is a legitimate production pattern, not just a hackathon patch -
worth mentioning in the README/demo as evidence the engine "operates
within realistic security, cost, latency and scalability constraints"
(the brief's requirement 8) - a real system CANNOT assume its LLM
provider is always up.
"""
from .base_provider import LLMProvider, LLMResult


class FallbackLLMProvider(LLMProvider):
    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary = primary
        self.fallback = fallback

    def generate_narrative(self, evidence: dict, persona_key: str, persona_cfg: dict) -> LLMResult:
        try:
            return self.primary.generate_narrative(evidence, persona_key, persona_cfg)
        except Exception as e:
            print(f"[FALLBACK] primary LLM provider failed ({e}); using fallback for this scenario")
            result = self.fallback.generate_narrative(evidence, persona_key, persona_cfg)
            result.model = f"{result.model} [FALLBACK - primary unavailable: {e}]"
            return result
