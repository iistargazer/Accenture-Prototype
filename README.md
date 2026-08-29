# KPI intelligence-to-action engine — base prototype

## Run it

```bash
pip install pandas numpy pyyaml
cd kpi_engine
python3 data/generate_data.py      # (re)generate synthetic sources
python3 run_scenarios.py           # runs the pipeline end-to-end, writes output/scenarios.json
python3 build_dashboard.py         # bakes scenarios.json into a standalone dashboard
open output/dashboard.html         # or double-click it
```

No API key, no server, no internet access needed — the dashboard is a single static HTML
file with the run's output embedded in it.

## Architecture, one line each

- `contracts/kpi_contracts.yaml` — the governed semantic layer. Definitions, grain,
  thresholds, lineage, access roles for every KPI. Everything else reads from here.
- `data/` — 3 synthetic sources at different grains/cadences (daily sales, weekly
  marketing spend, monthly ops/stockouts), with scenarios deliberately engineered in.
- `engine/data_loader.py` — reconciles source grain → weekly analysis grain per KPI.
- `engine/detection.py` — materiality detection (z-score + pct-change vs threshold).
- `engine/driver_analysis.py` — price-volume-mix decomposition, correlation, rule-based
  stockout lookup. Ranks by **evidence quality** (decomposition > rule > correlation),
  not just raw magnitude.
- `engine/confidence.py` — confidence scoring + abstention rule, all legible arithmetic.
- `engine/evidence.py` — the structured object that's the boundary between the
  deterministic core and the LLM. The LLM never sees a dataframe, only this.
- `engine/security.py` — personas + row/column-level entitlement filtering, applied
  before evidence reaches the LLM.
- `engine/action_rules.py` — driver → lever → action → owner → monitoring plan lookup.
- `engine/feedback.py` — feedback capture + naive "suggest a new threshold" loop.
- `engine/telemetry.py` — per-stage latency, model calls, tokens, cost.
- `engine/orchestrator.py` — wires all of the above; read this file to see the
  full LLM-vs-non-LLM breakdown in one place.
- `llm/mock_provider.py` — deterministic narrative synthesis, no API key needed.
  Swap for a real call: implement `AnthropicProvider(LLMProvider)` in `llm/`, change
  one line in `run_scenarios.py`. The system prompt for the real version should say
  "only use the evidence JSON given; never invent a number; if `should_abstain` is
  true, say so and ask a clarifying question."

## Requirement → where it's demonstrated

| # | Requirement | Where |
|---|---|---|
| 1 | Detect & prioritize movements | `detection.py`, scenario: any entry in Alerts feed |
| 2 | Reconcile heterogeneous sources | `kpi_contracts.yaml` + `data_loader.py`, 3 grains |
| 3 | Rank explanatory drivers | `driver_analysis.py`, quality-tiered ranking |
| 4 | Persona narratives w/ evidence | `personas` tab — same evidence, 2 personas |
| 5 | Uncertainty & abstention | `abstain` tab — sparse-history KPI, confidence 10% |
| 6 | Action recommendations | `action_rules.py`, shown in Driver breakdown tab |
| 7 | Feedback loop | `feedback.py`, `feedback` tab |
| 8 | Cost/latency/security constraints | `telemetry.py` + `security.py`, respective tabs |

## What's deliberately simplified (say this out loud to judges)

- Data is synthetic, engineered to contain known scenarios — real connectors are
  a separate, solvable problem; this demo is about the reasoning architecture.
- The LLM layer is mocked with deterministic templates. The abstraction boundary
  (`llm/base_provider.py`) is real — plugging in Claude/GPT is a ~30-line class.
- The feedback loop suggests a threshold change; it never auto-writes back to the
  contract. Kept as a human-in-the-loop step on purpose.
- Correlation is explicitly never treated as causal — every correlation-derived
  driver carries a caveat string and is ranked below decomposition-grade evidence.

## Getting a real key (no budget needed)

- **Anthropic (preferred, matches the product story):** sign up at console.anthropic.com.
  New accounts get a one-time free trial credit (phone verification, no credit card) —
  enough for a hackathon-scale demo. Set `ANTHROPIC_API_KEY` and use
  `llm/anthropic_provider.py`.
- **Google Gemini (no-card fallback):** get a key at aistudio.google.com — genuinely
  free tier, no card at all. Check the current free-tier model name on that page before
  running (`llm/gemini_provider.py` has a placeholder that may be stale by the time you
  read this) and set `GEMINI_API_KEY`.
- Either way, swapping providers is a two-line change in `run_scenarios.py` — the
  interface (`llm/base_provider.py`) is identical across mock/Anthropic/Gemini.

## Next for the team

- Swap in a real Anthropic key (`llm/anthropic_provider.py`) — narratives currently
  are template text, not model-generated.
- Add a 4th source at an even coarser grain (e.g. quarterly headcount) to stress-test
  the semantic layer further.
- Tighten the contradictory-evidence detection in `confidence.py` — it's currently a
  simple sign/magnitude heuristic, not a real statistical disagreement test.
