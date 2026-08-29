"""
Runs every scenario the hackathon's 'minimum prototype expectations' list
requires, using the mock LLM provider, and writes output/scenarios.json.
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

# 1. Multi-factor material movement, two personas on the SAME evidence
for persona in ["exec", "regional_manager_west", "sales_analyst"]:
    region = "East"
    if persona == "regional_manager_west":
        region = "West"  # this persona is entitled to West only -> demonstrates row-level security below
    scenarios[f"multi_driver_revenue__{persona}"] = run_pipeline(
        "revenue", persona, llm, region=region, category_for_drivers="existing_A" if region == "East" else "existing_B"
    )

# 2. Sparse-history KPI (new_launch_revenue - only 2 weeks of data)
scenarios["sparse_history_new_launch"] = run_pipeline(
    "new_launch_revenue", "sales_analyst", llm, region=None
)

# 3. Low-confidence / contradictory-evidence / abstention scenario
#    existing_B in West, latest week: stockout recovery + ambiguous marketing signal
scenarios["low_confidence_abstain"] = run_pipeline(
    "units_sold", "sales_analyst", llm, region="West", category_for_drivers="existing_B"
)

# 4. Role-based security scenario: regional_manager_west tries to access an East-only cut
scenarios["security_denied_cross_region"] = run_pipeline(
    "revenue", "regional_manager_west", llm, region="East", category_for_drivers="existing_A"
)

# 5. Feedback loop demo: simulate two analysts flagging avg_selling_price alerts as false alarms,
#    then show the suggested threshold adjustment on a subsequent run.
record_feedback("avg_selling_price", "period-1", "sales_analyst", "false_alarm", "seasonal, not material")
record_feedback("avg_selling_price", "period-1", "regional_manager_west", "false_alarm", "known promo cycle")
scenarios["feedback_loop_after_2_false_alarms"] = run_pipeline(
    "avg_selling_price", "sales_analyst", llm, region=None
)

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
