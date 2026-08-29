"""
Provider interface. The engine talks to this interface only - swapping
the mock for a real Anthropic/OpenAI call means writing one new class
here and changing one line in orchestrator.py. Nothing else changes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    estimated_cost_usd: float


class LLMProvider(ABC):
    @abstractmethod
    def generate_narrative(self, evidence: dict, persona_key: str, persona_cfg: dict) -> LLMResult:
        ...
