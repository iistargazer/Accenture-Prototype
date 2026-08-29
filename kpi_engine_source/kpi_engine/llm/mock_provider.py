"""
MOCK LLM PROVIDER — no API key required.

This simulates what a real LLM call would produce: it reads ONLY the
structured evidence object (never raw data) and synthesizes persona-
appropriate prose, exactly like a real narrative-synthesis prompt would.
Token/cost/latency numbers are estimated the same way you'd estimate them
for a real call, so the telemetry panel is meaningful even before a key
is wired in.

To go live: implement AnthropicProvider(LLMProvider) in this package
calling api.anthropic.com/v1/messages with a system prompt that says
"only use the evidence JSON provided; never invent numbers; if
should_abstain is true, say so and ask a clarifying question" - then
swap the provider in orchestrator.py.
"""
import time
import random
from .base_provider import LLMProvider, LLMResult

MOCK_MODEL_NAME = "mock-narrative-v1 (stand-in for claude-sonnet-5)"
COST_PER_1K_INPUT = 0.003
COST_PER_1K_OUTPUT = 0.015


def _fmt_pct(x):
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.1f}%"


class MockLLMProvider(LLMProvider):
    def generate_narrative(self, evidence: dict, persona_key: str, persona_cfg: dict) -> LLMResult:
        start = time.perf_counter()

        if evidence["should_abstain"]:
            text = self._abstain_text(evidence, persona_cfg)
        elif persona_cfg["detail_level"] == "summary":
            text = self._exec_text(evidence)
        elif persona_cfg["detail_level"] == "full":
            text = self._analyst_text(evidence)
        else:
            text = self._manager_text(evidence, persona_cfg)

        # simulate network latency proportional to output length
        time.sleep(min(0.05, len(text) / 20000))
        latency_ms = (time.perf_counter() - start) * 1000 + random.uniform(180, 320)

        input_tokens = len(str(evidence)) // 4
        output_tokens = len(text) // 4
        cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + (output_tokens / 1000 * COST_PER_1K_OUTPUT)

        return LLMResult(
            text=text,
            model=MOCK_MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1),
            estimated_cost_usd=round(cost, 5),
        )

    def _abstain_text(self, ev, persona_cfg):
        reasons = "; ".join(ev["confidence_reasons"])
        return (
            f"I'm not confident enough to explain the {_fmt_pct(ev['pct_change'])} move in "
            f"{ev['display_name']} ({ev['period']}) to give you a reliable root cause. "
            f"Confidence is {ev['confidence']:.0%}, below the threshold to act on. "
            f"Why: {reasons}. Recommend: pull one more week of data before drawing a conclusion, "
            f"or confirm manually with the category team."
        )

    def _exec_text(self, ev):
        top = ev["drivers"][0] if ev["drivers"] else None
        driver_line = f"driven mainly by {top['name']} ({_fmt_pct(top['contribution_pct'])} of the move)" if top and top["contribution_pct"] is not None else "driver still being isolated"
        return (
            f"{ev['display_name']} moved {_fmt_pct(ev['pct_change'])} in {ev['period']} "
            f"(${ev['prior_value']:,.0f} -> ${ev['latest_value']:,.0f}), {driver_line}. "
            f"Confidence: {ev['confidence']:.0%}. Recommended action: "
            f"{'see driver breakdown for the top lever' if top else 'monitor next period'}."
        )

    def _manager_text(self, ev, persona_cfg):
        scope = f" in {ev['region']}" if ev.get("region") else ""
        lines = [f"{ev['display_name']}{scope} moved {_fmt_pct(ev['pct_change'])} in {ev['period']}."]
        for d in ev["drivers"]:
            c = f"{_fmt_pct(d['contribution_pct'])}" if d["contribution_pct"] is not None else "directional signal"
            lines.append(f"- {d['name']}: {c} ({d['method']})")
        lines.append(f"Confidence: {ev['confidence']:.0%}.")
        return "\n".join(lines)

    def _analyst_text(self, ev):
        scope = f" ({ev['region']})" if ev.get("region") else ""
        lines = [
            f"{ev['display_name']}{scope}: {ev['period']}, {_fmt_pct(ev['pct_change'])} vs prior period "
            f"(z={ev['z_score']})." if ev['z_score'] is not None else
            f"{ev['display_name']}{scope}: {ev['period']}, {_fmt_pct(ev['pct_change'])} vs prior period (z-score unavailable - short history)."
        ]
        lines.append("Driver breakdown:")
        for d in ev["drivers"]:
            c = f"{_fmt_pct(d['contribution_pct'])}" if d["contribution_pct"] is not None else "n/a (directional only)"
            lines.append(f"  - {d['name']}: {c} | method: {d['method']} | source: {d['source']} | {d['detail']}")
        lines.append(f"Confidence: {ev['confidence']:.0%}. Reasons: {'; '.join(ev['confidence_reasons'])}")
        lines.append(f"Lineage: {ev['lineage']}")
        return "\n".join(lines)
