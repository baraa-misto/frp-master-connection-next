"""Report-only explanations of already unevaluated Direct first-row checks.

Consumes the authenticated native snapshot. No resistance, force, status,
qualification, applicability or governing result is created or changed here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def direct_first_row_reason(check_id: str, result: dict[str, Any]) -> str | None:
    """Describe a native unsupported row without claiming an engineering closure."""

    if not check_id.startswith("FIRST_ROW:"):
        return None
    demand = result.get("automatic_demand_result")
    if not isinstance(demand, dict):
        return "METHOD REQUIRED: authenticated first-row demand is unavailable."
    scenarios = demand.get("scenarios", [])
    eccentric = any(Decimal(item["residual_moment"]["canonical_value"]) != 0 for item in scenarios)
    if check_id.startswith("FIRST_ROW:layer-B"):
        reason = (
            "METHOD REQUIRED: W oblique net-section plane, row identity and width "
            "need an approved mapping."
        )
        if eccentric:
            reason = (
                "METHOD REQUIRED: W oblique net-section plane/width and eccentric "
                "stress need approved methods."
            )
        return reason
    if eccentric:
        return (
            "METHOD REQUIRED: external eccentric moment needs an approved first-row stress handoff."
        )
    return (
        "METHOD REQUIRED: physical Figure C8-11 effective width and the first-row "
        "demand need an approved mapping."
    )
