"""Compact engineering matrices for the reader section of REPORT1."""

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

from frp_master_connection.reporting.reader_data import (
    CheckView,
    governing,
    humanize,
    readable_value,
    short_number,
)
from frp_master_connection.reporting.units import DisplayUnits


def _cell(value: object) -> Paragraph:
    style = ParagraphStyle("ReaderMatrixCell", fontName="ReportVera", fontSize=7.4, leading=9.2)
    return Paragraph(escape(str(value)), style)


def _matrix(rows: list[list[str]], widths: list[float]) -> Table:
    table = Table(
        [[_cell(value) for value in row] for row in rows],
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe9ed")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f7")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#738c99")),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def results_matrix(checks: list[CheckView], system: DisplayUnits) -> Table:
    critical = governing(checks)
    rows = [
        [
            "Check",
            "Component",
            "Bolt / path",
            "Demand",
            "Design resistance",
            "Utilization",
            "Outcome",
            "Coverage",
        ]
    ]
    rows.extend(
        [
            f"GOVERNING — {check.name}" if check is critical else check.name,
            check.component,
            check.location,
            readable_value(check.demand, system),
            readable_value(check.resistance, system),
            short_number(check.utilization, ratio=True)
            if check.utilization is not None
            else "Not evaluated",
            humanize(check.outcome),
            humanize(check.availability),
        ]
        for check in checks
    )
    table = _matrix(rows, [77, 61, 54, 54, 60, 65, 45, 69])
    if critical is not None:
        row = checks.index(critical) + 1
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#fff0e7")),
                    ("LINEBEFORE", (0, row), (0, row), 3, colors.HexColor("#a43c20")),
                    ("LINEBELOW", (0, row), (-1, row), 0.7, colors.HexColor("#a43c20")),
                ]
            )
        )
    return table


def limitations_matrix(checks: list[CheckView]) -> Table:
    rows = [["Check / component", "Native state", "Reason", "Authority / next step"]]
    rows.extend(
        [
            f"{check.name} — {check.component}; {check.location}",
            humanize(check.availability),
            check.reason,
            humanize(check.qualification),
        ]
        for check in checks
        if check.availability not in {"CALCULATED", "NOT_APPLICABLE"} and check.required
    )
    if len(rows) == 1:
        rows.append(["No required unevaluated native check", "—", "—", "—"])
    return _matrix(rows, [113, 90, 155, 127])


def loads_matrix(vectors: list[tuple[str, str, str, str]]) -> Table:
    rows = [["Submitted action / reference", "H or X", "V or Y", "N or Z"]]
    rows.extend([name, first, second, third] for name, first, second, third in vectors)
    return _matrix(rows, [161, 108, 108, 108])
