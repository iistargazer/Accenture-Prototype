"""
Evidence object: the contract between the deterministic/statistical core
and the LLM layer. The LLM NEVER sees raw dataframes - only this object.
That boundary is what makes "LLM is not the source of quantitative truth"
enforceable rather than aspirational.
"""
from dataclasses import dataclass, asdict
from .detection import Movement
from .driver_analysis import Driver
from .confidence import ConfidenceResult


@dataclass
class Evidence:
    kpi: str
    display_name: str
    region: str | None
    period: str
    latest_value: float
    prior_value: float
    pct_change: float
    z_score: float | None
    is_material: bool
    drivers: list[dict]
    confidence: float
    should_abstain: bool
    confidence_reasons: list[str]
    freshness: dict
    lineage: str
    owner_role: str

    def to_dict(self):
        return asdict(self)


def build_evidence(kpi: str, contract: dict, region: str | None, movement: Movement,
                    drivers: list[Driver], confidence: ConfidenceResult, freshness: dict) -> Evidence:
    return Evidence(
        kpi=kpi,
        display_name=contract["display_name"],
        region=region,
        period=movement.latest_period,
        latest_value=movement.latest_value,
        prior_value=movement.prior_value,
        pct_change=movement.pct_change,
        z_score=movement.z_score,
        is_material=movement.is_material,
        drivers=[asdict(d) for d in drivers],
        confidence=confidence.score,
        should_abstain=confidence.should_abstain,
        confidence_reasons=confidence.reasons,
        freshness=freshness,
        lineage=contract["lineage"],
        owner_role=contract["owner_role"],
    )
