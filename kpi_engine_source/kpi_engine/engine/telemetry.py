"""
Runtime telemetry for a pipeline run: stage latency, model call count,
token usage, estimated cost. This is what lets you answer "what does one
insight cost, and where does the time go" - required by the brief's
LLM-economics bullet.
"""
import time
from dataclasses import dataclass, field


@dataclass
class Telemetry:
    stage_latency_ms: dict = field(default_factory=dict)
    model_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    cache_hit: bool = False

    def time_stage(self, name):
        return _StageTimer(self, name)

    def record_llm_call(self, llm_result):
        self.model_calls += 1
        self.total_input_tokens += llm_result.input_tokens
        self.total_output_tokens += llm_result.output_tokens
        self.total_cost_usd += llm_result.estimated_cost_usd

    def to_dict(self):
        return {
            "stage_latency_ms": self.stage_latency_ms,
            "total_latency_ms": round(sum(self.stage_latency_ms.values()), 1),
            "model_calls": self.model_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 5),
            "cache_hit": self.cache_hit,
        }


class _StageTimer:
    def __init__(self, telemetry, name):
        self.telemetry = telemetry
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed = (time.perf_counter() - self.start) * 1000
        self.telemetry.stage_latency_ms[self.name] = round(elapsed, 2)
