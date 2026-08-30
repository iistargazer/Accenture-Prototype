# KPI Intelligence-to-Action Engine

A prototype built for BusinessIntelligence.ai for Round 2 of the Accenture Innovation Challenge 2026: 

Detects material KPI movements, ranks their drivers using the appropriate analytical method for each (not just an LLM
guessing), generates persona-specific narratives grounded in traceable evidence, and
recommends concrete actions — with explicit confidence scoring, abstention when
evidence is weak, role-based data security, a feedback loop, and full cost/latency
telemetry.

# Made by Team Raijin.
# Rohan Chinta
# Mohammad Saad Ansari
# S Vageesh

Link to the dashboard
https://htmlpreview.github.io/?https://github.com/iistargazer/KPI-Intelligence-to-Action-Engine/blob/main/kpi_engine_source/kpi_engine/output/dashboard.html
---

## 1. Implementation approach

The core design decision: **the LLM is never the source of a number.** Every KPI
value, every driver contribution, every confidence score is produced by deterministic
code (pandas arithmetic, a documented statistical test, or a rule lookup) *before* any
model call happens. The LLM's only job is to read a finished, structured evidence
object and turn it into persona-appropriate prose. This is enforced by the code
structure, not just a design intention — the LLM provider classes physically cannot
see a raw dataframe; they receive one plain dict.

Concretely, for every KPI/persona request, the pipeline runs, in order:

1. **Reconcile** — pull the KPI's raw source(s), resolve them to a common analysis
   grain per a governed contract (see below).
2. **Detect** — is this period's value a material movement? (statistics, not LLM)
3. **Explain** — rank candidate drivers by evidence quality: an exact decomposition
   outranks a rule-based flag, which outranks a correlation coefficient. A
   correlation is never allowed to look more important than it is just because its
   number happens to be larger.
4. **Score confidence** — a transparent, inspectable point-deduction system; if
   confidence falls below a threshold, the engine **abstains** rather than guessing.
5. **Enforce entitlements** — row/column-level filtering by persona, applied to the
   structured evidence *before* it reaches the LLM.
6. **Recommend actions** — a driver → lever → action → owner → monitoring-plan
   lookup table, not LLM generation.
7. **Narrate** — the one and only LLM call, given the finished evidence object and a
   persona's tone/detail-level, with a system prompt that forbids inventing numbers
   and requires it to say so plainly when the evidence says to abstain.

The LLM layer talks to a plain interface (`llm/base_provider.py`), so it's not tied
to one vendor. We currently run on **Google Gemini** (free tier), with a
**deterministic mock provider** as an automatic fallback if the live API is
unavailable — every narrative in the output is labelled with which one actually
produced it, so nothing is silently misrepresented as real model output.

## 2. Solution architecture

```
sales_daily.csv ─┐
marketing_spend_weekly.csv ─┼──> semantic layer (kpi_contracts.yaml + data_loader.py)
ops_monthly.csv ─┘                         │
                                            v
                               detection.py (z-score / pct-change)
                                            │
                                            v
                    driver_analysis.py (PVM decomposition, correlation, rule lookup)
                                            │
                                            v
                        confidence.py (scoring + abstention rule)
                                            │
                                            v
                          evidence.py  (structured evidence object)
                                            │
                            ______________  |  ______________
                            v                                v
                   security.py (entitlements)       action_rules.py (lever library)
                            │                                │
                            |______________  |  ______________|
                                             v
                     llm/ (Gemini primary, mock fallback) - narrative synthesis only
                                             │
                                             v
                                  dashboard.html (static, self-contained)
```

Two other pieces sit alongside the main pipeline:
- **`engine/feedback.py`** — analysts can flag an alert as a false alarm; after
  enough flags on one KPI, the engine surfaces a suggested (not auto-applied)
  materiality threshold change. Human approves before it's written back.
- **`engine/telemetry.py`** — wraps every pipeline stage with a timer, and every LLM
  call with token/cost accounting, so a single run reports exactly where time and
  money went.

`run_scenarios.py` exercises the whole pipeline across the specific scenarios the
brief's minimum-prototype checklist asks for (multi-driver movement, sparse-history
KPI, security denial, feedback loop, two personas on identical evidence) and writes
the results to `output/scenarios.json`. `build_dashboard.py` bakes that JSON into a
single static HTML file — no server, no build step, works offline.

## 3. Dependencies

- Python 3.10+ (uses `X | None` type-hint syntax)
- `pandas`, `numpy` — data reconciliation and statistics
- `pyyaml` — reading the KPI contract
- `requests` — calling the Gemini API
- A free Google AI Studio API key (aistudio.google.com — no credit card required)
  set as the `GEMINI_API_KEY` environment variable. No key at all is required to run
  with the mock provider instead.

No database, no server, no paid services, no internet access required at all if
you're fine with the mock provider's template narratives instead of live-generated
ones.

## 4. Execution instructions

```bash
pip install pandas numpy pyyaml requests
cd kpi_engine

# 1. Generate the synthetic source data (3 tables, different grains, with
#    known scenarios engineered in)
python data/generate_data.py

# 2. Set your Gemini key (skip this to run on the mock provider instead)
export GEMINI_API_KEY=your_key_here          # Windows PowerShell: $env:GEMINI_API_KEY="..."

# 3. Run the full pipeline across all required scenarios
python run_scenarios.py

# 4. Build the dashboard
python build_dashboard.py

# 5. Open output/dashboard.html directly in a browser
```

---

## Requirement → where it's demonstrated

| # | Requirement | Where |
|---|---|---|
| 1 | Detect & prioritize movements | `engine/detection.py`; Alerts feed tab |
| 2 | Reconcile heterogeneous sources | `contracts/kpi_contracts.yaml` + `engine/data_loader.py`; 3 grains |
| 3 | Rank explanatory drivers | `engine/driver_analysis.py`; quality-tiered ranking |
| 4 | Persona narratives w/ evidence | Persona comparison tab — identical evidence, 2 personas |
| 5 | Uncertainty & abstention | Abstention tab — sparse-history KPI, 10% confidence |
| 6 | Action recommendations | `engine/action_rules.py`; Driver breakdown tab |
| 7 | Feedback loop | `engine/feedback.py`; Feedback loop tab |
| 8 | Cost/latency/security constraints | `engine/telemetry.py` + `engine/security.py`; respective tabs |

## What's deliberately simplified

- Data is synthetic, engineered to contain known scenarios — real connectors are a
  separate, solvable problem; this prototype is about the reasoning architecture.
- The contradictory-evidence check in `engine/confidence.py` is a straightforward
  sign/magnitude heuristic, not a formal statistical disagreement test — it catches
  the obvious cases (a correlation pointing the opposite way from a decomposition)
  but isn't a rigorous causal-inference method.
- The feedback loop suggests a threshold change; it never auto-writes back to the
  contract. Kept as a human-in-the-loop step on purpose.
- Correlation is explicitly never treated as causal — every correlation-derived
  driver carries a caveat string and is ranked below decomposition-grade evidence.
- The LLM fallback (Gemini to mock) is a genuine resilience feature, not a demo
  crutch — it's how we'd want a production version to behave if a provider has an
  outage, and every narrative is labelled with which path actually produced it.

## Possible next steps

- A formal causal-inference check (e.g. treating one region as a rough control group)
  to back up the confidence heuristic with something more rigorous.
- A second LLM provider (e.g. Anthropic Claude) as an additional fallback tier, since
  the abstraction (`llm/base_provider.py`) already supports adding one in ~30 lines.
- A 4th data source at a coarser grain (e.g. quarterly headcount) to stress-test the
  semantic layer with an even bigger grain mismatch.
