"""
The only file that calls everything else. Read top to bottom, this IS
the "breakdown of LLM vs non-LLM processing" the brief asks for: every
stage is labelled with the method it used before the LLM is invoked
exactly once, at the very end, to phrase (not compute) the answer.
"""
from .data_loader import compute_kpi_series, load_contracts
from .detection import detect_movement
from .driver_analysis import price_volume_mix, marketing_correlation, stockout_check, rank_drivers
from .confidence import score_confidence
from .evidence import build_evidence
from .security import check_access, redact_evidence, PERSONAS
from .action_rules import recommend_actions
from .telemetry import Telemetry
from .feedback import suggested_threshold_adjustment


def run_pipeline(kpi_name: str, persona_key: str, llm_provider, region: str | None = None,
                  category_for_drivers: str | None = None) -> dict:
    telemetry = Telemetry()
    contracts = load_contracts()
    contract = contracts[kpi_name]

    access = check_access(contract, persona_key, region)
    if not access.allowed:
        return {"error": access.audit_note, "telemetry": telemetry.to_dict()}

    with telemetry.time_stage("load_and_reconcile_grain"):
        # For revenue / units_sold, slice the KPI series to the same category
        # the driver analysis will examine, so the "movement" and its
        # explanation refer to the same underlying data.
        slice_category = category_for_drivers if kpi_name in ("revenue", "units_sold") else None
        ks = compute_kpi_series(kpi_name, region=region, category=slice_category)

    with telemetry.time_stage("detect_movement"):
        movement = detect_movement(ks)

    with telemetry.time_stage("driver_analysis"):
        drivers = []
        if region and category_for_drivers:
            drivers += price_volume_mix(region, category_for_drivers)
            sc = stockout_check(region, category_for_drivers)
            if sc:
                drivers.append(sc)
        mc = marketing_correlation(ks.weekly)
        if mc:
            drivers.append(mc)
        drivers = rank_drivers(drivers)

    with telemetry.time_stage("confidence_scoring"):
        confidence = score_confidence(movement, drivers)

    evidence = build_evidence(kpi_name, contract, region, movement, drivers, confidence, ks.freshness)
    evidence_dict = redact_evidence(evidence.to_dict(), persona_key)

    with telemetry.time_stage("action_rules"):
        actions = [] if confidence.should_abstain else recommend_actions(evidence_dict["drivers"], confidence.score)

    with telemetry.time_stage("llm_narrative_synthesis"):
        llm_result = llm_provider.generate_narrative(evidence_dict, persona_key, PERSONAS[persona_key])
        telemetry.record_llm_call(llm_result)

    suggested_threshold, threshold_note = suggested_threshold_adjustment(
        kpi_name, contract["materiality_threshold_pct"]
    )

    return {
        "kpi": kpi_name,
        "persona": persona_key,
        "region": region,
        "access_audit": access.audit_note,
        "evidence": evidence_dict,
        "actions": actions,
        "narrative": llm_result.text,
        "narrative_model": llm_result.model,
        "telemetry": telemetry.to_dict(),
        "feedback_loop": {"threshold_note": threshold_note, "suggested_threshold_pct": suggested_threshold},
    }
