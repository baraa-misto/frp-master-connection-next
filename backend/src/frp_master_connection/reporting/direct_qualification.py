"""Read-only F8 summary of the authenticated backend evaluation."""

from __future__ import annotations

from typing import Any

from frp_master_connection.reporting.reader_data import readable_value, short_number
from frp_master_connection.reporting.units import DisplayUnits


def qualification_summary_rows(
    evaluation: dict[str, Any], system: DisplayUnits
) -> list[tuple[str, str]]:
    if evaluation["record_digest"] is None:
        return [("Qualification", "Required — no approved matching record")]
    stats = evaluation["statistics"]
    rows = [
        (
            "Record / revision",
            f"{evaluation['selected_record_id']} / {evaluation['record_revision']}",
        ),
        ("Laboratory / RDP", f"{evaluation['laboratory']} / {evaluation['rdp_approval']}"),
        ("Accepted specimens", str(stats["accepted_n"])),
        (
            "Ro",
            "Unevaluated"
            if stats["Ro"] is None
            else readable_value({"value": stats["Ro"], "unit": "N"}, system),
        ),
        ("COV / phi_p", f"{short_number(stats['VR'])} / {short_number(stats['phi_p'])}"),
        ("Qualified design strength", readable_value(evaluation["Rd_q"], system)),
        ("Current required strength", readable_value(evaluation["Ru"], system)),
        ("Scope / coverage", f"{evaluation['scope_match_state']} / {evaluation['coverage_state']}"),
        ("Capacity comparison", str(evaluation["capacity_state"])),
        ("Eq. 2-2 strict gravity comparison", str(evaluation["gravity_eq_2_2_state"])),
        ("Covered response IDs", "; ".join(evaluation["covered_response_ids"]) or "None"),
    ]
    rows.extend(
        (
            {
                "Rn": "Nominal qualification strength Rn",
                "phi_p": "Qualification resistance factor phi_p",
            }.get(item["factor"], "Applicable factor: " + item["factor"]),
            readable_value({"value": item["value"], "unit": "N"}, system)
            if item["factor"] == "Rn"
            else str(item.get("applied", item.get("value"))),
        )
        for item in evaluation["factor_trace"]
    )
    if evaluation["mismatch_reasons"]:
        rows.append(("Active qualification limits", "; ".join(evaluation["mismatch_reasons"])))
    return rows


__all__ = ("qualification_summary_rows",)
