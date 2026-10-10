"""F9 presentation over a sealed decision; never determine engineering status."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from frp_master_connection.reporting.reader_data import CheckView, readable_value, short_number
from frp_master_connection.reporting.units import DisplayUnits


def executive_rows(decision: dict[str, Any], system: DisplayUnits) -> list[tuple[str, str]]:
    summary = decision["analytical_check_summary"]
    highest = next(
        (r for r in decision["schedule"] if r["check_id"] == summary["highest_analytical_check"]),
        None,
    )
    return [
        ("Design status", decision["final_status"] + " — " + decision["final_status_reason"]),
        ("Governing check / gate", decision["governing_label"]),
        ("Numerical checks", f"{summary['evaluated']} evaluated — {summary['numerical_outcome']}"),
        ("Highest analytical check", highest["label"] if highest else "Not evaluated"),
        (
            "Analytical demand",
            readable_value(highest["demand"], system) if highest else "Unevaluated",
        ),
        (
            "Analytical design resistance",
            readable_value(highest["design_resistance"], system) if highest else "Unevaluated",
        ),
        (
            "Highest analytical utilization",
            short_number(summary["highest_utilization"], ratio=True) if highest else "Unevaluated",
        ),
        (
            "Whole connection",
            decision["qualification_capacity_state"] + "; Section 2.3.2 qualification",
        ),
        (
            "Remaining incompleteness",
            f"{summary['counts']['REQUIRED_UNRESOLVED']} required checks/evidence items unresolved",
        ),
    ]


def coverage_rows(decision: dict[str, Any], checks: list[CheckView]) -> list[tuple[str, str]]:
    native = {check.identity: check for check in checks}
    rows = []
    for row in decision["schedule"]:
        if row["category"] in {"ANALYTICALLY_EVALUATED", "NEUTRAL_INFORMATION"}:
            continue
        description = row["category"].replace("_", " ")
        if row["category"] == "REQUIRED_UNRESOLVED":
            check = native.get(row["check_id"])
            description = "METHOD REQUIRED / QUALIFICATION REQUIRED. " + (
                check.reason if check is not None else row["reason"]
            )
        elif row["category"] == "QUALIFICATION_COVERED":
            description = "COVERED BY QUALIFICATION — see the single whole-connection capacity."
        elif row["category"] == "NOT_APPLICABLE":
            description = "NOT APPLICABLE — " + row["reason"]
        rows.append((row["label"], description))
    return rows


def engineering_notation(text: str, style: ParagraphStyle) -> Paragraph:
    """Shorten display decimals, then typeset subscripts; audit operands stay exact."""

    def compact(match: re.Match[str]) -> str:
        number = Decimal(match[0])
        shown = format(number, ".8g")
        return shown.rstrip("0").rstrip(".") if "." in shown and "e" not in shown.lower() else shown

    value = re.sub(r"(?<![A-Za-z_\d])-?\d+\.\d+(?:[Ee][+-]?\d+)?", compact, text)
    value = escape(value).replace("\n", "<br/>")
    value = re.sub(r"\b(R|A|F|C|e|phi)_([A-Za-z0-9]+)\b", r"\1<sub>\2</sub>", value)
    return Paragraph(value, style)
