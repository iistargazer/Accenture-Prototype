"""
Movement detection. Pure statistics - z-score against trailing history plus
a business-materiality threshold pulled from the KPI contract. No LLM
anywhere in this file. method tags on every output so the UI/report can
show exactly which technique produced which number.
"""
from dataclasses import dataclass
from .data_loader import KpiSeries


@dataclass
class Movement:
    kpi: str
    latest_period: str
    latest_value: float
    prior_value: float
    pct_change: float
    z_score: float | None
    materiality_threshold_pct: float
    is_material: bool
    is_sparse_history: bool
    n_periods: int
    method: str


def detect_movement(ks: KpiSeries) -> Movement:
    w = ks.weekly
    n = len(w)
    latest = w.iloc[-1]
    prior = w.iloc[-2] if n >= 2 else w.iloc[-1]

    pct_change = ((latest.value - prior.value) / prior.value * 100) if prior.value else 0.0

    z = None
    method = "pct_change_vs_prior_period"
    if n >= 5:
        trailing = w.iloc[:-1]["value"]
        mean, std = trailing.mean(), trailing.std(ddof=0)
        if std and std > 0:
            z = (latest.value - mean) / std
            method = "z_score_vs_trailing_mean (n={})".format(len(trailing))

    threshold = ks.contract.get("materiality_threshold_pct", 10.0)
    is_material = abs(pct_change) >= threshold or (z is not None and abs(z) >= 2.0)

    min_periods = ks.contract.get("min_periods_for_full_confidence", 5)
    is_sparse = n < min_periods

    return Movement(
        kpi=ks.kpi,
        latest_period=str(latest.week_start.date()) if hasattr(latest.week_start, "date") else str(latest.week_start),
        latest_value=round(float(latest.value), 2),
        prior_value=round(float(prior.value), 2),
        pct_change=round(float(pct_change), 2),
        z_score=round(float(z), 2) if z is not None else None,
        materiality_threshold_pct=threshold,
        is_material=bool(is_material),
        is_sparse_history=is_sparse,
        n_periods=n,
        method=method,
    )
