"""
driver -> controllable lever -> action -> owner -> monitoring plan.
This is a lookup table, not an LLM generation - the LLM only phrases
the entries this file returns, per the "action recommendation" format
the brief specifies: driver -> lever -> action -> expected impact ->
owner -> confidence -> monitoring plan.
"""

LEVER_LIBRARY = {
    "price": {
        "lever": "pricing",
        "action": "Re-evaluate the recent price increase; consider a targeted promo or price rollback in the affected region",
        "owner": "Pricing team",
        "monitoring_plan": "Track weekly units and revenue for 3 weeks post-change; alert if volume declines further",
    },
    "volume": {
        "lever": "demand generation",
        "action": "Investigate demand-side causes (price, competition, availability) before adjusting spend",
        "owner": "Category Manager",
        "monitoring_plan": "Monitor sell-through and stock levels weekly",
    },
    "marketing_spend": {
        "lever": "media mix / budget allocation",
        "action": "Run a holdout or geo-test before reallocating budget on the strength of a correlation alone",
        "owner": "Marketing Lead",
        "monitoring_plan": "Compare treated vs holdout region ROAS over 2-3 weeks",
    },
    "stockouts": {
        "lever": "inventory / supply",
        "action": "Expedite replenishment for the affected SKU/region; flag to supply planning",
        "owner": "Supply Planning",
        "monitoring_plan": "Daily stock-level check until back above safety threshold",
    },
    "mix": {
        "lever": "assortment",
        "action": "Review category/channel mix shift; confirm whether it's seasonal or structural",
        "owner": "Category Manager",
        "monitoring_plan": "Track mix % by category monthly",
    },
}


def recommend_actions(drivers: list[dict], confidence: float) -> list[dict]:
    actions = []
    for d in drivers:
        rule = LEVER_LIBRARY.get(d["name"])
        if not rule:
            continue
        actions.append({
            "driver": d["name"],
            "lever": rule["lever"],
            "action": rule["action"],
            "expected_impact": f"~{abs(d['contribution_pct']):.0f}% of the movement is attributable here" if d["contribution_pct"] is not None else "directional only - not yet quantified",
            "owner": rule["owner"],
            "confidence": confidence,
            "monitoring_plan": rule["monitoring_plan"],
        })
    return actions
