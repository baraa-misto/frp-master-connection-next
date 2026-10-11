"""Read-only presentation helpers over the existing sealed Direct evidence."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def signed_number(value: object) -> str:
    """Six significant display digits, with explicit sign and nonzero tiny values.

    No comparison, classification, tolerance or stored datum is changed.
    """
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    if not number.is_finite():
        return str(value)
    if number == 0:
        return "0 (exact)"
    return format(number, "+.6g")


def moment_rows(diagnostic: dict[str, Any]) -> list[tuple[str, str]]:
    """Label the existing transported vectors; never calculate a moment or demand."""
    rows = [("Reference transport equation", str(diagnostic["equation"]))]
    for name, label, unit in (
        ("F_global_kip", "F — global force", "kip"),
        ("P_global_in", "P — submitted action reference", "in"),
        ("G_global_in", "G — geometric bolt centroid", "in"),
        ("M_P_global_kip_in", "M_P — submitted moment at P", "kip·in"),
        ("M_G_global_kip_in", "M_G — transported moment at G", "kip·in"),
    ):
        rows.append(
            (
                label,
                "; ".join(
                    f"{axis} = {signed_number(value)} {unit}"
                    for axis, value in zip("XYZ", diagnostic[name], strict=True)
                ),
            )
        )
    rows.extend(
        (label, str(diagnostic[key]))
        for key, label in (
            ("state", "Native diagnostic state"),
            ("per_bolt_demand_evaluated", "Per-bolt demand evaluated"),
            ("resistance_center_established", "Resistance center established"),
        )
    )
    return rows


def source_stop_rows(result: dict[str, Any]) -> list[tuple[str, str]]:
    """Foreground an actual MC1 source stop, preserving the F9 status/count authority."""
    gate = result.get("direct_material_applicability")
    if not isinstance(gate, dict) or not gate.get("blocked_check_ids"):
        return []
    decision = result.get("final_decision")
    if not isinstance(decision, dict):
        return []
    checked = [row for row in decision["schedule"] if row["category"] == "ANALYTICALLY_EVALUATED"]
    bolts = sum(row["check_id"].startswith("BOLT_SHEAR:") for row in checked)
    other = len(checked) - bolts
    evaluation = f"{bolts} independent bolt shear checks evaluated"
    evaluation += f"; {other} other independent checks evaluated" if other else " only"
    return [
        ("FRP SOURCE-DATA STOP", "FRP resistance checks not evaluated: " + str(gate["reason"])),
        (
            "Independent evaluated checks",
            evaluation + ". This is not an FRP or whole-connection approval.",
        ),
        (
            "Source-blocked FRP checks",
            str(len(gate["blocked_check_ids"]))
            + "; exact IDs and diagnostic reconstruction retained in the technical audit",
        ),
    ]


def audit_index_rows(decision: dict[str, Any]) -> list[tuple[str, str]]:
    """Exact locators in the existing printed audit; no new report attachment/API."""
    rows = [
        ("Submitted engineering inputs", "Appendix A: request.*"),
        ("Material / condition assignment", "Appendix A: request.mat1_assignments.*"),
        ("Canonical physical model and boundaries", "Appendix B: result.preview.*"),
        (
            "Executed native equations and operands",
            "Appendix B: result.automatic_handoff_results.* / "
            "result.automatic_group_mode_integration.*",
        ),
        (
            "Signed material / source / qualification authority",
            "MAT1 material and condition authority: material_wrapper.*",
        ),
    ]
    rows.extend(
        (
            row["check_id"],
            f"material_wrapper.final_decision.schedule[{index}]; "
            f"{row['category']} / {row['outcome']}",
        )
        for index, row in enumerate(decision["schedule"])
    )
    return rows
