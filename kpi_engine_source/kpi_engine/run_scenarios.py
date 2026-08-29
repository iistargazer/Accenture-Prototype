"""
Runs every scenario the hackathon's 'minimum prototype expectations' list
requires, and writes output/scenarios.json.
This is also the fastest way to sanity-check the whole pipeline.
"""
import json
from pathlib import Path
from engine.orchestrator import run_pipeline
from engine.feedback import record_feedback
from llm.gemini_provider import GeminiProvider

llm = GeminiProvider()
OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

scenarios = {}


def safe_run(name, *args, **kwargs):
    """Wraps run_pipeline so a single flaky network call (timeout, quota,
    transient 5xx that outlasts the provider's own retries) doesn't take
    down the other 6 scenarios with it. Failed scenarios show up in the
    JSON/dashboard with a clear error message instead of crashing the run."""
    try:
        scenarios[name] = run_pipeline(*args, **kwargs)
    except Exception as e:
        print(f"[WARN] scenario '{name}' failed: {e}")
        scenarios[name] = {"error": f"pipeline exception: {e}"}


# 1. Multi-factor material movement, two personas on the SAME evidence
for persona in ["exec", "regional_manager_west", "sales_analyst"]:
    region = "East"
    if persona == "regional_manager_west":
        region = "West"  # this persona is entitled to West only -> demonstrates row-level security below
    safe_run(
        f"multi_driver_revenue__{persona}",
        "revenue", persona, llm, region=region, category_for_drivers="existing_A" if region == "East" else "existing_B"
    )

# 2. Sparse-history KPI (new_launch_revenue - only 2 weeks of data)
safe_run("sparse_history_new_launch", "new_launch_revenue", "sales_analyst", llm, region=None)

# 3. Low-confidence / contradictory-evidence / abstention scenario
#    existing_B in West, latest week: stockout recovery + ambiguous marketing signal
safe_run("low_confidence_abstain", "units_sold", "sales_analyst", llm, region="West", category_for_drivers="existing_B")

# 4. Role-based security scenario: regional_manager_west tries to access an East-only cut
safe_run("security_denied_cross_region", "revenue", "regional_manager_west", llm, region="East", category_for_drivers="existing_A")

# 5. Feedback loop demo: simulate two analysts flagging avg_selling_price alerts as false alarms,
#    then show the suggested threshold adjustment on a subsequent run.
record_feedback("avg_selling_price", "period-1", "sales_analyst", "false_alarm", "seasonal, not material")
record_feedback("avg_selling_price", "period-1", "regional_manager_west", "false_alarm", "known promo cycle")
safe_run("feedback_loop_after_2_false_alarms", "avg_selling_price", "sales_analyst", llm, region=None)

with open(OUT / "scenarios.json", "w") as f:
    json.dump(scenarios, f, indent=2, default=str)

print(f"Wrote {len(scenarios)} scenarios to {OUT / 'scenarios.json'}")
for name, result in scenarios.items():
    print("\n===", name, "===")
    if "error" in result:
        print("ERROR:", result["error"])
        continue
    print("abstain:", result["evidence"]["should_abstain"], "| confidence:", result["evidence"]["confidence"])
    print("narrative:", result["narrative"][:200].replace("\n", " | "))
