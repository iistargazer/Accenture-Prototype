"""
Generates three source tables at DIFFERENT grains and refresh cadences,
simulating the "fragmented systems" reality the brief describes:

  sales_daily.csv            - daily grain, transactional system
  marketing_spend_weekly.csv - weekly grain, marketing platform
  ops_monthly.csv            - monthly grain, ops/supply system (stockouts)

Engineered scenarios (deliberately, so the engine has something real to find):
  1. Week 12: existing_A price +12% in the East region -> volume drop,
     partially offset by a marketing spend increase the same week.
     This is the "multi-factor KPI movement with known underlying drivers".
  2. West region: a stockout event in week 11 (ops_monthly) suppresses
     units for existing_B in West - a confounding driver from a THIRD,
     low-frequency source.
  3. 'new_launch' category only has 2 weeks of history -> sparse-history
     scenario.
  4. 'existing_B' in the West region has a movement where two drivers
     point in different directions with similar magnitude -> the
     contradictory-evidence / low-confidence / abstention scenario.
"""
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
rng = np.random.default_rng(7)

WEEKS = 12
START = pd.Timestamp("2026-06-01")
regions = ["East", "West"]
categories = ["existing_A", "existing_B", "new_launch"]

rows = []
for w in range(WEEKS):
    week_start = START + pd.Timedelta(days=7 * w)
    for d in range(7):
        date = week_start + pd.Timedelta(days=d)
        for region in regions:
            for cat in categories:
                if cat == "new_launch" and w < WEEKS - 2:
                    continue  # sparse history: launched 2 weeks ago

                base_price = {"existing_A": 40.0, "existing_B": 25.0, "new_launch": 18.0}[cat]
                base_units = {"existing_A": 220, "existing_B": 180, "new_launch": 90}[cat]

                price = base_price
                units_mean = base_units * (1 + 0.03 * np.sin(w / 2))  # mild seasonality

                # Scenario 1: existing_A East price hike in the FINAL week only,
                # so latest-vs-prior-period comparison actually shows the jump.
                if cat == "existing_A" and region == "East" and w == WEEKS - 1:
                    price = base_price * 1.12
                    units_mean *= 0.82  # demand response to price

                # Scenario 2: West stockout, second-to-last week, existing_B
                if cat == "existing_B" and region == "West" and w == WEEKS - 2:
                    units_mean *= 0.55

                # Scenario 4: existing_B West, final week - contradictory signals.
                # Units partially rebound from the stockout (up vs prior week),
                # while price ticks up slightly at the same time - two drivers
                # pointing in different directions with comparable magnitude.
                if cat == "existing_B" and region == "West" and w == WEEKS - 1:
                    units_mean *= 0.80
                    price = base_price * 1.08

                units = max(0, int(rng.normal(units_mean / 7, units_mean * 0.05 / 7)))
                rows.append([date.date().isoformat(), region, cat, units, round(price, 2)])

sales = pd.DataFrame(rows, columns=["date", "region", "category", "units", "price"])
sales.to_csv(OUT / "sales_daily.csv", index=False)

# marketing spend - weekly grain, by channel, only 2 channels, national (not region-split)
mkt_rows = []
for w in range(WEEKS):
    week_start = (START + pd.Timedelta(days=7 * w)).date().isoformat()
    for channel, base in [("paid_search", 4000), ("social", 2500)]:
        spend = base * (1 + 0.05 * rng.normal())
        if w >= WEEKS - 2:
            spend *= 1.35  # marketing push coincides with the price hike week
        mkt_rows.append([week_start, channel, round(spend, 2)])
mkt = pd.DataFrame(mkt_rows, columns=["week_start", "channel", "spend"])
mkt.to_csv(OUT / "marketing_spend_weekly.csv", index=False)

# ops - monthly grain, stockout flags (only affects West / existing_B in one window)
ops_rows = [
    ["2026-06", "East", "existing_A", 0, 0],
    ["2026-06", "East", "existing_B", 0, 0],
    ["2026-06", "West", "existing_A", 0, 0],
    ["2026-06", "West", "existing_B", 0, 0],
    ["2026-07", "East", "existing_A", 0, 0],
    ["2026-07", "East", "existing_B", 0, 0],
    ["2026-07", "West", "existing_A", 0, 0],
    ["2026-07", "West", "existing_B", 1, 5],  # stockout event
]
ops = pd.DataFrame(ops_rows, columns=["month", "region", "category", "stockout_flag", "stockout_days"])
ops.to_csv(OUT / "ops_monthly.csv", index=False)

print(f"sales_daily: {len(sales)} rows")
print(f"marketing_spend_weekly: {len(mkt)} rows")
print(f"ops_monthly: {len(ops)} rows")
