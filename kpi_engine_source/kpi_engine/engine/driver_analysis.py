"""
Driver identification and ranking. Each function is a distinct analytical
method (classical decomposition, correlation, rule-based lookup against a
low-frequency source) - each output is tagged with its method so nothing
gets attributed to "the model" when it was actually arithmetic.
"""
from dataclasses import dataclass, field
import pandas as pd
from .data_loader import load_sales, load_marketing, load_ops


@dataclass
class Driver:
    name: str
    contribution_pct: float   # signed, share of the total movement explained
    direction: str            # "increases" | "decreases" | "ambiguous"
    method: str
    source: str
    detail: str


def price_volume_mix(region: str, category: str) -> list[Driver]:
    """Classic PVM decomposition between the latest two weeks for one
    region/category cut. Deterministic arithmetic, no ML."""
    sales = load_sales()
    sales = sales[(sales.region == region) & (sales.category == category)]
    weekly = sales.groupby("week_start").apply(
        lambda d: pd.Series({"units": d.units.sum(), "price": (d.units * d.price).sum() / d.units.sum()}),
        include_groups=False,
    ).sort_index()

    if len(weekly) < 2:
        return []

    prev, cur = weekly.iloc[-2], weekly.iloc[-1]
    prev_rev = prev.units * prev.price
    cur_rev = cur.units * cur.price
    if prev_rev == 0:
        return []

    price_effect = (cur.price - prev.price) * prev.units
    volume_effect = (cur.units - prev.units) * prev.price
    interaction = (cur.price - prev.price) * (cur.units - prev.units)
    volume_effect += interaction  # fold interaction into volume for a 2-factor split

    # Express each effect as percentage POINTS of prior-period revenue, not
    # as a share of the net movement - the latter blows up (e.g. -208%) when
    # two drivers partly offset each other, which reads as broken in a demo
    # even though it's arithmetically correct PVM. Points-of-base sum to
    # ~= the net pct change and stay interpretable.
    drivers = []
    for name, effect in [("price", price_effect), ("volume", volume_effect)]:
        contribution_pct = round(effect / prev_rev * 100, 1)
        drivers.append(Driver(
            name=name,
            contribution_pct=contribution_pct,
            direction="increases" if effect > 0 else "decreases",
            method="price_volume_mix_decomposition (pct points of prior-period revenue)",
            source=f"sales_daily ({region}/{category})",
            detail=f"price {prev.price:.2f}->{cur.price:.2f}, units {prev.units:.0f}->{cur.units:.0f}",
        ))
    return drivers


def marketing_correlation(kpi_weekly, lookback: int = 8) -> Driver | None:
    """Rolling correlation between weekly spend and the KPI's weekly value.
    Correlation, not causation - labelled as such in `detail`."""
    mkt = load_marketing().groupby("week_start")["spend"].sum().reset_index()
    merged = kpi_weekly.merge(mkt, on="week_start", how="inner").tail(lookback)
    if len(merged) < 4:
        return None
    corr = merged["value"].corr(merged["spend"])
    if corr != corr:  # NaN guard
        return None
    recent_spend_change_pct = (
        (merged["spend"].iloc[-1] - merged["spend"].iloc[-2]) / merged["spend"].iloc[-2] * 100
        if len(merged) >= 2 and merged["spend"].iloc[-2] else 0.0
    )
    return Driver(
        name="marketing_spend",
        contribution_pct=round(corr * 100, 1),
        direction="increases" if corr > 0 else "decreases",
        method=f"pearson_correlation (n={len(merged)} weeks, spend +{recent_spend_change_pct:.0f}% latest wk)",
        source="marketing_spend_weekly",
        detail="correlation only - not a causal estimate; confirm with a holdout/geo test before acting",
    )


def stockout_check(region: str, category: str) -> Driver | None:
    """Rule-based lookup against a low-frequency operational source."""
    ops = load_ops()
    row = ops[(ops.region == region) & (ops.category == category) & (ops.stockout_flag == 1)]
    if row.empty:
        return None
    days = int(row.stockout_days.iloc[0])
    return Driver(
        name="stockouts",
        contribution_pct=None,
        direction="decreases",
        method="rule_lookup (ops_monthly.stockout_flag)",
        source="ops_monthly",
        detail=f"{days} stockout day(s) recorded for {region}/{category} in the current month",
    )


def rank_drivers(drivers: list[Driver]) -> list[Driver]:
    """Ranks by EVIDENCE QUALITY first, magnitude second. A correlation
    coefficient and a revenue-decomposition percentage are not the same
    kind of number - treating them as comparable would be exactly the
    'LLM-grade' sloppiness the brief warns against. Decomposition
    (exact, deterministic) outranks rule-based flags (definite but
    unquantified), which outrank correlation (suggestive, not causal)."""
    tier = {"price_volume_mix_decomposition": 0, "rule_lookup": 1, "pearson_correlation": 2}

    def method_tier(d: Driver) -> int:
        for key_, t in tier.items():
            if d.method.startswith(key_):
                return t
        return 3

    def magnitude(d: Driver):
        return abs(d.contribution_pct) if d.contribution_pct is not None else 0

    valid = [d for d in drivers if d is not None]
    return sorted(valid, key=lambda d: (method_tier(d), -magnitude(d)))
