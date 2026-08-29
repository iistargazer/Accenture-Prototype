"""
Confidence scoring + abstention. This is deliberately simple and legible -
a judge should be able to read this file top to bottom and see exactly
why the engine trusts or distrusts a given finding. No LLM involved.
"""
from dataclasses import dataclass
from .detection import Movement
from .driver_analysis import Driver


@dataclass
class ConfidenceResult:
    score: float              # 0-1
    should_abstain: bool
    reasons: list[str]


def score_confidence(movement: Movement, drivers: list[Driver]) -> ConfidenceResult:
    reasons = []
    score = 1.0

    if movement.is_sparse_history:
        score -= 0.35
        reasons.append(f"only {movement.n_periods} periods of history (needs more for a stable baseline)")

    if movement.z_score is None:
        score -= 0.15
        reasons.append("insufficient trailing history to compute a z-score; using raw pct-change only")

    quantified = [d for d in drivers if d.contribution_pct is not None]
    if not quantified:
        score -= 0.4
        reasons.append("no quantifiable driver identified")
    else:
        signs = set(1 if d.contribution_pct > 0 else -1 for d in quantified)
        magnitudes_close = False
        if len(quantified) >= 2:
            top_two = sorted(quantified, key=lambda d: abs(d.contribution_pct), reverse=True)[:2]
            if abs(abs(top_two[0].contribution_pct) - abs(top_two[1].contribution_pct)) < 15:
                magnitudes_close = True
        if len(signs) > 1 and magnitudes_close:
            score -= 0.3
            reasons.append("top drivers point in different directions with similar magnitude (contradictory evidence)")

    decomposition = [d for d in quantified if d.method.startswith("price_volume_mix")]
    correlations = [d for d in quantified if d.method.startswith("pearson_correlation")]
    if decomposition and correlations:
        decomp_sign = 1 if decomposition[0].contribution_pct > 0 else -1
        for c in correlations:
            corr_sign = 1 if c.contribution_pct > 0 else -1
            if corr_sign != decomp_sign:
                score -= 0.15
                reasons.append(
                    f"a correlational signal ({c.name}) disagrees in direction with the decomposition-based "
                    f"driver ({decomposition[0].name}) - treat the correlation as a caveat, not a cause"
                )
                break

    weak_corr_only = (
        len(quantified) == 1
        and quantified[0].name == "marketing_spend"
        and "correlation" in quantified[0].method
    )
    if weak_corr_only:
        score -= 0.2
        reasons.append("only a correlational signal available, no decomposition-grade driver")

    score = max(0.0, min(1.0, round(score, 2)))
    should_abstain = score < 0.45

    if not reasons:
        reasons.append("sufficient history, clear dominant driver, no contradicting signals")

    return ConfidenceResult(score=score, should_abstain=should_abstain, reasons=reasons)
