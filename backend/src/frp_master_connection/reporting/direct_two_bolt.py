"""Presentation of a sealed SAB2 geometry snapshot; no engineering evaluation."""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterator
from copy import deepcopy
from typing import Any
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from frp_master_connection.application.direct_two_bolt_geometry import GEOMETRY_BANNER
from frp_master_connection.reporting.pdf import _font_setup
from frp_master_connection.reporting.snapshot import ReportSnapshot, SnapshotError


def _audit_entries(
    value: object, path: str = "", seen: dict[str, str] | None = None
) -> Iterator[tuple[str, str]]:
    """Print identical large subtrees once and retain explicit reversible aliases.

    The authenticated snapshot remains unchanged. Each alias names an exact
    earlier appendix path, so no inputs or machine evidence are discarded.
    """
    if seen is None:
        seen = {}
    if isinstance(value, (dict, list)) and value:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) >= 160:
            if encoded in seen:
                yield path, "Exact JSON subtree reference: " + seen[encoded]
                return
            seen[encoded] = path
        if isinstance(value, dict) and all(not isinstance(v, (dict, list)) for v in value.values()):
            yield path, encoded
            return
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in items:
            child = (
                (f"{path}.{key}" if path else str(key))
                if isinstance(value, dict)
                else f"{path}[{key}]"
            )
            yield from _audit_entries(item, child, seen)
    else:
        yield path, json.dumps(value, ensure_ascii=False)


def face_drawing(result: dict[str, Any], face_index: int) -> Drawing:
    """Draw the backend's face-local witnesses, with explicit display crop lines."""
    face = result["pair_input"]["faces"][face_index]
    points = [p for p in result["geometry"]["face_points"] if p["face_id"] == face["id"]]
    u = [float(p["local_center"][0]) for p in points]
    v = [float(p["local_center"][1]) for p in points]
    radius = float(result["pair_input"]["washer_radius"])
    spacing = float(result["pair_input"]["spacing"])
    u0, u1 = min(u) - max(1, spacing), max(u) + max(1, spacing)
    v0, v1 = min(v) - 1.5, max(v) + 1.5
    for b in face["boundaries"]:
        a, bb, c = float(b["a"]), float(b["b"]), float(b["limit"])
        if bb == 0 and a != 0:
            if a < 0:
                u0 = c / a
            else:
                u1 = c / a
        if a == 0 and bb != 0:
            if bb < 0:
                v0 = c / bb
            else:
                v1 = c / bb
    # An outside station remains visible even when it fails physical containment.
    u0, u1 = min(u0, min(u) - radius), max(u1, max(u) + radius)
    v0, v1 = min(v0, min(v) - radius), max(v1, max(v) + radius)
    size = min(440 / (u1 - u0), 165 / (v1 - v0))
    x0, y0 = 30.0, 28.0

    def x(value: float) -> float:
        return x0 + (value - u0) * size

    def y(value: float) -> float:
        return y0 + (value - v0) * size

    drawing = Drawing(490, 230)
    drawing.add(
        String(
            10,
            216,
            f"{face['member_id']} / {face['id'].split(':')[1]}",
            fontName="ReportVeraBold",
            fontSize=10,
        )
    )
    window = Rect(x0, y0, (u1 - u0) * size, (v1 - v0) * size)
    window.fillColor = colors.HexColor("#edf3f8")
    window.strokeColor = colors.HexColor("#87939e")
    window.strokeDashArray = [3, 3]
    drawing.add(window)
    for low, high in face["seating_strips"]:
        lo, hi = float(low), float(high)
        strip = Rect(x0, y(lo), (u1 - u0) * size, (hi - lo) * size)
        strip.fillColor = colors.HexColor("#d4e8dd")
        strip.strokeColor = None
        drawing.add(strip)
    for boundary in face["boundaries"]:
        a, b, c = float(boundary["a"]), float(boundary["b"]), float(boundary["limit"])
        if b == 0:
            drawing.add(
                Line(
                    x(c / a),
                    y(v0),
                    x(c / a),
                    y(v1),
                    strokeColor=colors.HexColor("#173e5b"),
                    strokeWidth=1.3,
                )
            )
        elif a == 0:
            drawing.add(
                Line(
                    x(u0),
                    y(c / b),
                    x(u1),
                    y(c / b),
                    strokeColor=colors.HexColor("#173e5b"),
                    strokeWidth=1.3,
                )
            )
        else:
            candidates = [
                (u0, (c - a * u0) / b),
                (u1, (c - a * u1) / b),
                ((c - b * v0) / a, v0),
                ((c - b * v1) / a, v1),
            ]
            visible = list(
                dict.fromkeys(
                    (uu, vv) for uu, vv in candidates if u0 <= uu <= u1 and v0 <= vv <= v1
                )
            )
            if len(visible) >= 2:
                drawing.add(
                    Line(
                        x(visible[0][0]),
                        y(visible[0][1]),
                        x(visible[-1][0]),
                        y(visible[-1][1]),
                        strokeColor=colors.HexColor("#a16620"),
                    )
                )
    for point in points:
        pu, pv = float(point["local_center"][0]), float(point["local_center"][1])
        drawing.add(
            Circle(
                x(pu), y(pv), radius * size, fillColor=None, strokeColor=colors.HexColor("#c8791d")
            )
        )
        drawing.add(
            Circle(
                x(pu),
                y(pv),
                float(result["pair_input"]["hole_radius"]) * size,
                fillColor=None,
                strokeColor=colors.HexColor("#173e5b"),
            )
        )
        drawing.add(
            String(x(pu) + 4, y(pv) + 4, point["station"], fontName="ReportVeraBold", fontSize=8)
        )
    drawing.add(
        String(
            10,
            12,
            "u / v in inches. Solid: physical bounds. Dashed: view window only. Orange: washer.",
            fontName="ReportVera",
            fontSize=7,
        )
    )
    drawing.add(
        String(
            10,
            202,
            f"Pair spacing p = {result['pair_input']['spacing']} in",
            fontName="ReportVera",
            fontSize=8,
        )
    )
    for index, point in enumerate(points):
        drawing.add(
            String(
                10 + index * 245,
                0,
                f"{point['station']}: u={float(point['local_center'][0]):.6f}, "
                f"v={float(point['local_center'][1]):.6f} in",
                fontName="ReportVera",
                fontSize=7,
            )
        )
    return drawing


def render_geometry_review(snapshot: ReportSnapshot) -> bytes:
    if snapshot.family != "direct-sab2-geometry" or snapshot.kind != "input_only":
        raise SnapshotError(
            "A Geometry and Constructability Review requires its own "
            "authenticated geometry snapshot."
        )
    _font_setup()
    body = ParagraphStyle("SAB2Body", fontName="ReportVera", fontSize=8.5, leading=12, spaceAfter=6)
    heading = ParagraphStyle(
        "SAB2Heading", fontName="ReportVeraBold", fontSize=15, leading=20, spaceAfter=12
    )
    small = ParagraphStyle("SAB2Small", fontName="ReportVera", fontSize=7, leading=9)

    def paragraph(value: object, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(str(value)), style)

    def table(rows: list[list[object]], widths: list[float]) -> Table:
        cells = [[paragraph(c, small) for c in row] for row in rows]
        result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        result.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4edf3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5dd")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return result

    result = snapshot.result
    geometry = result["geometry"]
    story: list[Flowable] = [
        paragraph("Geometry and Constructability Review", heading),
        paragraph(
            "Two common bolt centers evaluated against both connected members. "
            "This document contains no new structural design approval, "
            "resistance, utilization, per-bolt demand or qualification."
        ),
        table(
            [
                ["Identity", "Sealed current geometry"],
                ["Fingerprint", result["geometry_fingerprint"]],
                ["Snapshot digest", snapshot.digest],
                [
                    "Alignment / spacing",
                    f"{result['alignment']} / {result['pair_input']['spacing']} in",
                ],
                ["Midpoint, global inches", result["pair_input"]["midpoint"]],
                ["Structural route", result["structural_route"]],
                ["Structural disposition", result["structural_reason"]],
            ],
            [126, 374],
        ),
        Spacer(1, 10),
        table(
            [
                ["Separate outcome", "State"],
                ["Hole containment", geometry["hole_state"]],
                ["Shaft / rear-web path", geometry["shaft_state"]],
                ["Washer seating", geometry["washer_state"]],
                ["Known physical obstruction", geometry["obstruction_state"]],
                ["Represented head / nut body", geometry["hardware_state"]],
                ["Installation access", geometry["installation_state"]],
                ["Aggregate constructability", geometry["aggregate_state"]],
            ],
            [210, 290],
        ),
        paragraph(
            "A known negative margin controls even when other faces seat "
            "correctly. Exact contact and incomplete manufactured or installation"
            " data remain conditional. Nominal root geometry does not certify an "
            "actual manufactured fillet."
        ),
        PageBreak(),
        paragraph("Same stations on both member faces", heading),
        face_drawing(result, 0),
        face_drawing(result, 1),
        paragraph(
            "B1/B2 are neutral geometric station labels. They do not establish "
            "ASCE first-row or bolt-demand authority. Shafts remain normal to the"
            " physical stack; alignment changes the center line only."
        ),
        PageBreak(),
        paragraph("Signed clearance witnesses", heading),
    ]
    rows: list[list[object]] = [["Station / owner", "Envelope", "Boundary / source", "Margin (in)"]]
    for margin in geometry["margins"]:
        rows.append(
            [
                f"{margin['station']} / {margin['owner']}",
                margin["role"],
                f"{margin['boundary']}\n{margin['source']}",
                margin["value"],
            ]
        )
    story.append(table(rows, [95, 55, 270, 80]))
    story.extend([PageBreak(), paragraph("Limitations and comparison", heading)])
    for unknown in geometry["unknowns"]:
        story.append(paragraph(unknown))
    story.append(
        paragraph(
            "Installation sequence, bolt length, tools and actual head/nut sizes "
            "require explicit project dimensions where not represented. No source"
            " upload is required to use nominal geometry. Missing dimensions are "
            "not assumed zero."
        )
    )
    comparison = result["comparison"]
    story.append(paragraph(comparison["basis"]))
    story.append(
        paragraph(
            "Reference transport diagnostic: "
            + json.dumps(result["moment_diagnostic"], ensure_ascii=False)
        )
    )
    story.append(
        table(
            [
                ["Other fixed alignment", "Aggregate", "Washer"],
                [
                    comparison["alignment"],
                    comparison["geometry"]["aggregate_state"],
                    comparison["geometry"]["washer_state"],
                ],
            ],
            [150, 180, 170],
        )
    )
    story.append(
        paragraph(
            "Bounded proposals preserve members, hardware and submitted spacing. "
            "They change no input until explicitly applied. A region vertex "
            "centroid is a proposed test point, not a maximum-clearance or "
            "robustness proof."
        )
    )
    story.extend(
        [
            PageBreak(),
            paragraph("Technical audit appendix", heading),
            paragraph(
                "Complete submitted inputs and unrounded backend geometry evidence "
                "follow. Materials, conditions, actions, reference points and the "
                "unchanged legacy mapping request are preserved as provenance; this "
                "geometry-only report does not execute their engineering equations."
            ),
            paragraph(
                "Identical large JSON subtrees appear once with explicit exact-path references. "
                "Resolve each reference to its earlier appendix path to recover all original "
                "inputs and outputs. No numerical evidence is deleted or rounded."
            ),
        ]
    )
    audit = {
        "request": snapshot.request,
        "geometry_snapshot": result,
        "input_provenance": snapshot.input_provenance,
    }
    attachment_name = "SAB2_complete_technical_audit.json"
    audit_bytes = json.dumps(
        audit, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    story.append(
        paragraph(
            f"Complete technical audit attachment: {attachment_name}. "
            f"{len(audit_bytes)} bytes; SHA-256 {hashlib.sha256(audit_bytes).hexdigest()}. "
            "The embedded JSON contains every submitted input and unrounded backend "
            "output, including every native station and display mesh. It is software "
            "evidence, not an engineering approval. Use a PDF viewer's Attachments "
            "panel or pypdf to extract it."
        )
    )
    printed = deepcopy(audit)
    printed["geometry_snapshot"]["visualization"] = {
        "complete_record": attachment_name + ": geometry_snapshot.visualization",
        "scope": (
            "Display meshes and presentation data; all analytic geometry remains on these pages"
        ),
    }
    audit_rows: list[list[object]] = [["Exact path / datum", "Backend value"]]
    audit_rows.extend([p, v] for p, v in _audit_entries(printed))
    story.append(table(audit_rows, [245, 255]))
    stream = io.BytesIO()
    doc = SimpleDocTemplate(
        stream, pagesize=letter, leftMargin=56, rightMargin=56, topMargin=68, bottomMargin=49
    )

    def page(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.setFont("ReportVeraBold", 7)
        canvas.setFillColor(colors.HexColor("#9b4b14"))
        canvas.drawString(36, 758, GEOMETRY_BANNER)
        canvas.setFont("ReportVera", 7)
        canvas.drawString(
            56,
            28,
            f"Geometry review · {result['geometry_fingerprint'][:16]} · Page {document.page}",
        )

    doc.build(story, onFirstPage=page, onLaterPages=page)
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(stream.getvalue())))
    writer.add_attachment(attachment_name, audit_bytes)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
