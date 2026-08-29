"""
Personas + row/column-level entitlement filtering. This runs BEFORE the
evidence object reaches the LLM layer - masking happens on structured
data, not by asking the LLM to "please don't mention X".
"""
from dataclasses import dataclass

PERSONAS = {
    "exec": {
        "label": "VP Sales (exec)",
        "role": "exec",                 # matches kpi_contracts.yaml access_roles
        "detail_level": "summary",
        "region_scope": None,          # sees all regions
        "hidden_dimensions": [],
        "tone": "concise, bottom-line first, one recommended action",
    },
    "regional_manager_west": {
        "label": "Regional Manager - West",
        "role": "regional_manager",
        "detail_level": "detailed",
        "region_scope": "West",        # row-level restriction
        "hidden_dimensions": ["margin", "channel_cost"],
        "tone": "operational, action-oriented, region-specific",
    },
    "sales_analyst": {
        "label": "Sales Analyst",
        "role": "sales_analyst",
        "detail_level": "full",
        "region_scope": None,
        "hidden_dimensions": [],
        "tone": "detailed, methodological, includes confidence caveats",
    },
}


@dataclass
class EntitlementResult:
    allowed: bool
    audit_note: str


def check_access(kpi_contract: dict, persona_key: str, region: str | None) -> EntitlementResult:
    persona = PERSONAS[persona_key]
    if persona["role"] not in kpi_contract.get("access_roles", []):
        return EntitlementResult(False, f"denied: role '{persona['role']}' ({persona_key}) not in access_roles for this KPI")

    scope = persona["region_scope"]
    if scope and region and region != scope:
        return EntitlementResult(False, f"denied: '{persona_key}' is scoped to {scope}, requested region was {region}")

    return EntitlementResult(True, f"allowed: '{persona_key}' cleared for {kpi_contract['display_name']}"
                                     + (f" ({scope} only)" if scope else ""))


def redact_evidence(evidence_dict: dict, persona_key: str) -> dict:
    """Column-level masking: strip restricted dimensions/fields for this persona."""
    persona = PERSONAS[persona_key]
    hidden = set(persona["hidden_dimensions"])
    if not hidden:
        return evidence_dict
    redacted = dict(evidence_dict)
    redacted["drivers"] = [
        {k: ("[redacted]" if k == "detail" and d["name"] in hidden else v) for k, v in d.items()}
        for d in evidence_dict["drivers"]
    ]
    return redacted
