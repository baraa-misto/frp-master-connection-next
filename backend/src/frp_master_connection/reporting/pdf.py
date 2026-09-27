"""Controlled vector PDF presentation of an authenticated REPORT1 snapshot.

This renderer presents native numbers and trace records. It does not evaluate a
connection or synthesize a resistance from diagram dimensions.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import Destination, PDFString
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from frp_master_connection.reporting.multirow_substitutions import multirow_native_substitution
from frp_master_connection.reporting.reader_data import humanize, readable_value, short_number
from frp_master_connection.reporting.snapshot import ReportSnapshot
from frp_master_connection.reporting.substitutions import single_native_substitutions
from frp_master_connection.reporting.units import (
    DisplayUnits,
    converted_quantity_rows,
    display_quantity,
    resolved_display_units,
)

PAPER_SIZES = {"LETTER": letter, "A4": A4}
MAX_TABLE_ROWS = 15_000


class ReportingCoverageError(ValueError):
    """An executed native calculation lacks a faithful REPORT1 adapter."""


class _ReportTable(Table):
    """Retain the final-fragment rule when ReportLab splits a long table again."""

    _cellvalues: list[list[Any]]
    _rowSplitRange: tuple[int, int] | None

    def onSplit(self, child: Table, byRow: int = 1) -> None:
        del byRow
        report_child = cast(_ReportTable, child)
        if len(report_child._cellvalues) >= 8:
            report_child._rowSplitRange = (2, -5)
        elif len(report_child._cellvalues) >= 3:
            report_child._rowSplitRange = (2, -2)


@dataclass(frozen=True, slots=True)
class ReportOptions:
    paper: Literal["LETTER", "A4"] = "LETTER"
    display_units: DisplayUnits = "INHERIT"
    project_name: str = ""
    project_number: str = ""
    connection_id: str = ""
    location: str = ""
    revision: str = ""
    prepared_by: str = ""
    checked_by: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class MethodTemplate:
    title: str
    expression: str
    explanation: str


_SINGLE_BOLT_METHODS = {
    "BOLT_TENSION": MethodTemplate(
        "Bolt tension",
        "A_b = pi d^2 / 4; R_d = phi A_b F_nt",
        "Direct axial bolt tension using the native bolt area and stated fastener source.",
    ),
    "BOLT_SHEAR": MethodTemplate(
        "Bolt shear",
        "A_b = pi d^2 / 4; R_d = phi A_b F_nv",
        "Single-plane fastener shear with the native thread condition and source stress.",
    ),
    "BOLT_COMBINED_TENSION_SHEAR": MethodTemplate(
        "Combined bolt tension and shear",
        "F'_nt = min[F_nt, 1.3 F_nt - F_nt f_v / (phi F_nv)]; R_d = phi A_b F'_nt",
        "The interaction modifies tensile stress using the actually applied shear stress.",
    ),
    "PULL_THROUGH": MethodTemplate(
        "FRP pull-through",
        "R_n = min[0.5 pi D_w t F_LT, 0.4 pi D_w t F_INT]; R_d = phi lambda C_delta R_n",
        "The lesser native branch governs; through-thickness and interlaminar data "
        "have separate roles.",
    ),
    "PIN_BEARING": MethodTemplate(
        "FRP pin bearing",
        "R_n = t d F_br C_thread; R_d = phi lambda C_delta C_lap R_n",
        "Actual layer thickness, bearing direction and thread factor control the check.",
    ),
    "NET_SECTION_TENSION": MethodTemplate(
        "FRP net tension",
        "R_n = (w - d_n) t F_t / K_nt; R_d = phi lambda C_delta C_lap R_n",
        "The native Appendix coefficient K_nt and selected element form remain in the trace.",
    ),
    "SHEAR_OUT": MethodTemplate(
        "FRP shear-out",
        "R_n = 1.4 (e_1 - d_n / 2) t F_s; R_d = phi lambda C_delta C_lap R_n",
        "The actual end distance and effective hole diameter appear in the input schedule.",
    ),
    "CLEAVAGE": MethodTemplate(
        "FRP cleavage",
        "R_n,A = 0.15 [(2e_2-d_n)F_t + 2e_1 F_s]t; "
        "R_n,B = R_n,bearing (10/9 - 4d_n/(9e_1))^2 if e_1/d < 4, "
        "otherwise R_n,bearing; R_d = min[phi_A lambda C_delta C_lap R_n,A, "
        "phi_B lambda C_delta C_lap R_n,B]",
        "The trace retains both branch factors, the selected branch and governing resistance.",
    ),
}

_MULTIROW_METHODS = {
    "BOLT_TENSION": _SINGLE_BOLT_METHODS["BOLT_TENSION"],
    "BOLT_SHEAR": MethodTemplate(
        "Fastener shear",
        "A_b = pi d^2/4; R_d = phi A_b F_nv",
        "Physical bolt shear plane, thread condition and authorized fastener source.",
    ),
    "BOLT_COMBINED_TENSION_SHEAR": _SINGLE_BOLT_METHODS["BOLT_COMBINED_TENSION_SHEAR"],
    "PULL_THROUGH": _SINGLE_BOLT_METHODS["PULL_THROUGH"],
    "PIN_BEARING": MethodTemplate(
        "FRP pin bearing",
        "R_n = t d F_br C_thread; R_d = phi lambda C_lap C_delta R_n",
        "Local bearing at each physical bolt and material layer.",
    ),
    "FIRST_ROW_SIMPLIFIED": MethodTemplate(
        "First-row net tension",
        "R_n = 0.2 w t F_t; R_d = phi lambda C_lap C_delta R_n",
        "Simplified ASCE/SEI 74-23 Equations 8-10/8-11 using planning-resolved width.",
    ),
    "FIRST_ROW_COMMENTARY_FULL": MethodTemplate(
        "Full first-row net tension",
        "S_pr = (w if N_b=1 else g)/d; K_nt = [1+C_i(S_pr-1.5 r^theta)]/"
        "[w/(N_b d)-1]; K_op = 1+C_op[1+(1-1/S_pr)^3]; "
        "A=K_nt w/(N_b d); B=K_op/[1-N_b d_n/w]; "
        "R_n=w t F_t/[A L_br+B(1-L_br)]",
        "Executed Appendix CA8.3.3 branch. The native trace records geometry, "
        "theta, coefficients, L_br and each denominator term.",
    ),
    "FIRST_ROW_RATIONAL_LOWER_ENVELOPE": MethodTemplate(
        "First-row lower envelope",
        "R_d=min[R_d,simplified, R_d,full(L_br=0), R_d,full(L_br=1)]",
        "The selected value is the native minimum over the simplified extension "
        "and both exact unknown-L_br endpoints; ties remain listed.",
    ),
    "INTERROW_ASCE_EQ_8_12": MethodTemplate(
        "Inter-row shear-out",
        "R_n = 1.4 (e_1 - d_n/2 + p) t F_s",
        "ASCE/SEI 74-23 Eq. 8-12; the trace retains the physical pitch and hole deduction.",
    ),
    "INTERROW_ASCE_EQ_8_13": MethodTemplate(
        "Inter-row shear-out",
        "R_n = 2 (sum of physical pitches) t F_s",
        "ASCE/SEI 74-23 Eq. 8-13 for the actual three-row span.",
    ),
    "INTERROW_RATIONAL_EXTENSION_EQ_8_13": MethodTemplate(
        "Inter-row shear-out: actual-row-span extension",
        "R_n = 2 (sum of all physical pitches) t F_s",
        "The native approved rational extension uses the actual physical pitch sum "
        "for more than three rows. It is distinct from direct prescriptive Eq. 8-13.",
    ),
    "BLOCK_SHEAR_ASCE_EQ_8_14A": MethodTemplate(
        "FRP block shear",
        "R_n = 0.5 (A_nv F_s + A_nt F_t)",
        "Accepted native path areas for the executed 8-14a branch are shown below.",
    ),
    "BLOCK_SHEAR_ASCE_EQ_8_14B": MethodTemplate(
        "FRP block shear",
        "R_n = 0.5 (A_nv F_s + 0.5 A_nt F_t)",
        "Accepted native path areas for the executed 8-14b branch are shown below.",
    ),
    "STATUS_ONLY": MethodTemplate(
        "Material/source review",
        "Not a numerical equation",
        "This is a required source or qualification state, not a calculated resistance.",
    ),
}


def _font_setup() -> None:
    if "ReportVera" in pdfmetrics.getRegisteredFontNames():
        return
    font_root = Path(__file__).resolve().parent / "fonts"
    pdfmetrics.registerFont(TTFont("ReportVera", str(font_root / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("ReportVeraBold", str(font_root / "DejaVuSans-Bold.ttf")))


def _text(value: object) -> str:
    if value is None:
        return "Not supplied"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str):
        return value if value else "Not supplied"
    if isinstance(value, dict | list):
        from frp_master_connection.reporting.reader_data import readable_value

        return readable_value(value)
    return str(value)


def _ratio_side(ratio: Decimal) -> str:
    """Label the unrounded native ratio without assigning engineering status."""

    if ratio > 1:
        return "above 1.0"
    if ratio < 1:
        return "below 1.0"
    return "at 1.0"


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    plain = _text(value)
    return Paragraph(escape(plain).replace("\n", "<br/>"), style)


def _flatten(prefix: str, value: object) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return [
            row
            for key, child in value.items()
            for row in _flatten(f"{prefix}.{key}" if prefix else str(key), child)
        ]
    if isinstance(value, list):
        return [
            row
            for index, child in enumerate(value)
            for row in _flatten(f"{prefix}[{index}]", child)
        ]
    return [(prefix, _text(value))]


def _input_source_rows(snapshot: ReportSnapshot) -> list[tuple[str, str]]:
    """Explain submitted, server-defaulted and backend-resolved field origins."""

    rows = [
        (
            "Submitted request fields",
            "Explicit values sent to the native API. The server cannot distinguish an "
            "unchanged workspace initial value from a user edit.",
        ),
        (
            "Backend-resolved fields",
            "Native result and preview paths below are calculation outputs, including "
            "derived dimensions and assignments; they are not entered values.",
        ),
    ]
    defaults = snapshot.input_provenance.get("server_defaulted_fields")
    if isinstance(defaults, dict) and defaults:
        rows.extend(
            row
            for path, value in defaults.items()
            for row in _flatten(f"Server default: {path}", value)
        )
    else:
        rows.append(("Server defaults", "None recorded for this validated request"))
    return rows


def _number(point: dict[str, object], axis: str) -> float:
    return float(str(point[axis]))


def _xyz(point: dict[str, object]) -> tuple[float, float, float]:
    return _number(point, "x"), _number(point, "y"), _number(point, "z")


def _box_vertices(primitive: dict[str, Any]) -> list[tuple[float, float, float]]:
    parameters = {item["name"]: float(item["value"]) for item in primitive["parameters"]}
    center = primitive["center"]
    axes = [primitive["x_axis"], primitive["y_axis"], primitive["z_axis"]]
    ranges = [
        (parameters["x_start"], parameters["x_end"]),
        (parameters["min_y"], parameters["max_y"]),
        (parameters["min_z"], parameters["max_z"]),
    ]

    def vertex(local: tuple[float, float, float]) -> tuple[float, float, float]:
        def coordinate(name: str) -> float:
            return _number(center, name) + sum(
                (local[index] - sum(ranges[index]) / 2) * _number(axes[index], name)
                for index in range(3)
            )

        return coordinate("x"), coordinate("y"), coordinate("z")

    return [
        vertex(local)
        for local in ((x, y, z) for x in ranges[0] for y in ranges[1] for z in ranges[2])
    ]


def _projection(point: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = point
    if view == "isometric":
        return x - 0.55 * y, z + 0.35 * (x + y)
    if view == "elevation":
        return x, z
    return x, y


def _dimension_witness(
    drawing: Drawing,
    first: tuple[float, float],
    second: tuple[float, float],
    *,
    axis: Literal["x", "y"],
    offset: float,
    label: str,
) -> None:
    """Attach a labelled witness to two projected canonical points."""

    ink = colors.HexColor("#374d59")
    if axis == "x":
        x0, x1 = first[0], second[0]
        drawing.add(Line(x0, first[1], x0, offset + 4, strokeColor=ink, strokeWidth=0.4))
        drawing.add(Line(x1, second[1], x1, offset + 4, strokeColor=ink, strokeWidth=0.4))
        drawing.add(Line(x0, offset, x1, offset, strokeColor=ink, strokeWidth=0.6))
        for x in (x0, x1):
            drawing.add(Line(x - 2, offset - 3, x + 2, offset + 3, strokeColor=ink))
        drawing.add(
            String(
                (x0 + x1) / 2,
                offset - 11,
                label,
                textAnchor="middle",
                fontName="ReportVera",
                fontSize=7.5,
            )
        )
    else:
        y0, y1 = first[1], second[1]
        drawing.add(Line(first[0], y0, offset - 4, y0, strokeColor=ink, strokeWidth=0.4))
        drawing.add(Line(second[0], y1, offset - 4, y1, strokeColor=ink, strokeWidth=0.4))
        drawing.add(Line(offset, y0, offset, y1, strokeColor=ink, strokeWidth=0.6))
        for y in (y0, y1):
            drawing.add(Line(offset - 3, y - 2, offset + 3, y + 2, strokeColor=ink))
        drawing.add(
            String(offset + 3, (y0 + y1) / 2 + 2, label, fontName="ReportVera", fontSize=7.5)
        )


def _length_label(value: object, source_unit: str, system: DisplayUnits) -> str:
    return display_quantity({"value": str(value), "unit": source_unit}, system)


def _dimension_label(value: object, system: DisplayUnits) -> str:
    """Readable dimension text; exact native values remain in the appendix."""

    shown = display_quantity(value, system)
    magnitude, separator, unit = shown.rpartition(" ")
    if separator:
        try:
            return f"{float(Decimal(magnitude)):.8g} {unit}"
        except ValueError, ArithmeticError:
            pass
    return shown


def _drawing(visual: dict[str, Any], view: str) -> Drawing:
    primitives = [item for item in visual.get("primitives", []) if item.get("kind") == "BOX"]
    if not primitives:
        raise ReportingCoverageError("Canonical box geometry is unavailable for this report")
    all_vertices = [_box_vertices(item) for item in primitives]
    projected = [[_projection(vertex, view) for vertex in vertices] for vertices in all_vertices]
    all_points = [point for polygon in projected for point in polygon]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    width, height = 455.0, 245.0
    scale = min((width - 195) / max(max_x - min_x, 0.01), (height - 55) / max(max_y - min_y, 0.01))

    def paper(point: tuple[float, float]) -> tuple[float, float]:
        return 25 + (point[0] - min_x) * scale, 30 + (point[1] - min_y) * scale

    figure = Drawing(width, height)
    label_counts: dict[str, int] = {}
    for primitive in primitives:
        label = str(primitive.get("physical_element_id") or primitive.get("owner_id") or "Part")
        label_counts[label] = label_counts.get(label, 0) + 1
    labelled: set[str] = set()
    for primitive, vertices in zip(primitives, projected, strict=True):
        points = [paper(point) for point in vertices]
        for first, second in (
            (0, 1),
            (0, 2),
            (0, 4),
            (3, 1),
            (3, 2),
            (3, 7),
            (5, 1),
            (5, 4),
            (5, 7),
            (6, 2),
            (6, 4),
            (6, 7),
        ):
            line = Line(*points[first], *points[second])
            line.strokeColor = colors.HexColor("#586b78")
            line.strokeWidth = 0.65
            figure.add(line)
        label = str(primitive.get("physical_element_id") or primitive.get("owner_id") or "Part")
        if label not in labelled and len(labelled) < 14:
            mid = paper((sum(p[0] for p in vertices) / 8, sum(p[1] for p in vertices) / 8))
            label_y = height - 34 - len(labelled) * 13
            figure.add(
                Line(
                    mid[0],
                    mid[1],
                    294,
                    label_y,
                    strokeColor=colors.HexColor("#a2adb2"),
                    strokeWidth=0.3,
                )
            )
            suffix = f" ({label_counts[label]})" if label_counts[label] > 1 else ""
            figure.add(
                String(
                    298,
                    label_y,
                    f"{label[:20]}{suffix}",
                    fontName="ReportVera",
                    fontSize=9,
                    fillColor=colors.HexColor("#203846"),
                )
            )
            labelled.add(label)
    bolt = visual.get("bolt")
    if isinstance(bolt, dict):
        start = bolt.get("stack_start")
        end = bolt.get("stack_end")
        center = bolt.get("center")
        if isinstance(start, dict) and isinstance(end, dict) and isinstance(center, dict):
            start_xyz = _xyz(start)
            end_xyz = _xyz(end)
            center_xyz = _xyz(center)
            start_xy = paper(_projection(start_xyz, view))
            end_xy = paper(_projection(end_xyz, view))
            center_xy = paper(_projection(center_xyz, view))
            figure.add(
                Line(
                    *start_xy,
                    *end_xy,
                    strokeColor=colors.HexColor("#9b4435"),
                    strokeWidth=2.0,
                )
            )
            if view == "plan":
                radius = float(bolt["bolt_diameter"]) * scale / 2
                figure.add(
                    Circle(
                        center_xy[0],
                        center_xy[1],
                        radius,
                        strokeColor=colors.HexColor("#9b4435"),
                        fillColor=None,
                        strokeWidth=1.1,
                    )
                )
            label_y = height - 34 - min(len(labelled), 14) * 13
            figure.add(
                Line(
                    center_xy[0],
                    center_xy[1],
                    294,
                    label_y,
                    strokeColor=colors.HexColor("#b57369"),
                    strokeWidth=0.3,
                )
            )
            figure.add(
                String(
                    298,
                    label_y,
                    str(bolt.get("bolt_location_id", "Bolt")),
                    fontName="ReportVeraBold",
                    fontSize=9,
                    fillColor=colors.HexColor("#9b4435"),
                )
            )
    unit = str(visual.get("length_unit", "length units"))
    if view != "isometric":
        extent = max_x - min_x
        line_y = 15.0
        left, right = paper((min_x, min_y))[0], paper((max_x, min_y))[0]
        figure.add(Line(left, line_y, right, line_y, strokeColor=colors.black, strokeWidth=0.7))
        for endpoint in (left, right):
            figure.add(
                Line(
                    endpoint,
                    line_y - 4,
                    endpoint,
                    line_y + 5,
                    strokeColor=colors.black,
                    strokeWidth=0.7,
                )
            )
        figure.add(
            String(
                (left + right) / 2,
                3,
                f"Overall projected extent: {extent:.4g} {unit}",
                textAnchor="middle",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    figure.add(
        String(
            8, height - 12, f"{view.title()} - not to scale", fontName="ReportVeraBold", fontSize=9
        )
    )
    return figure


def _direct_layer_detail(
    layer: dict[str, Any], bolt: dict[str, Any], system: DisplayUnits
) -> Drawing:
    """Witness the native bolt-to-boundary mapping for one physical ply."""

    mapping = layer.get("code_mapping")
    if not isinstance(mapping, dict):
        raise ReportingCoverageError("Direct layer lacks its native boundary mapping")
    required = (
        "forward_e1",
        "reverse_end_distance",
        "effective_e3",
        "effective_e4",
        "layer_thickness",
        "bolt_diameter",
        "hole_diameter",
    )
    if any(not isinstance(mapping.get(key), dict) for key in required):
        raise ReportingCoverageError("Direct layer boundary mapping lacks a dimension")
    drawing = Drawing(455, 238)
    drawing.add(
        String(
            8,
            225,
            f"{layer.get('layer_id')} / {layer.get('physical_element_id')} "
            "- native local boundary detail; not to scale",
            fontName="ReportVeraBold",
            fontSize=9,
        )
    )
    boundary = Rect(52, 57, 328, 120)
    boundary.strokeColor = colors.HexColor("#526675")
    boundary.fillColor = None
    drawing.add(boundary)
    drawing.add(Circle(214, 117, 10, strokeColor=colors.HexColor("#526675"), fillColor=None))
    drawing.add(Circle(214, 117, 7, strokeColor=colors.HexColor("#9b4435"), fillColor=None))
    drawing.add(
        String(
            225, 122, str(bolt.get("bolt_location_id", "Bolt")), fontName="ReportVera", fontSize=8
        )
    )
    _dimension_witness(
        drawing,
        (52, 117),
        (214, 117),
        axis="x",
        offset=44,
        label="reverse end " + _dimension_label(mapping["reverse_end_distance"], system),
    )
    _dimension_witness(
        drawing,
        (214, 117),
        (380, 117),
        axis="x",
        offset=31,
        label="forward e1 " + _dimension_label(mapping["forward_e1"], system),
    )
    _dimension_witness(
        drawing,
        (214, 57),
        (214, 117),
        axis="y",
        offset=28,
        label="e3 " + _dimension_label(mapping["effective_e3"], system),
    )
    _dimension_witness(
        drawing,
        (214, 117),
        (214, 177),
        axis="y",
        offset=28,
        label="e4 " + _dimension_label(mapping["effective_e4"], system),
    )
    drawing.add(
        String(
            52,
            200,
            f"t {display_quantity(mapping['layer_thickness'], system)} | "
            f"bolt d {display_quantity(mapping['bolt_diameter'], system)} | "
            f"hole d {display_quantity(mapping['hole_diameter'], system)}",
            fontName="ReportVera",
            fontSize=8.5,
        )
    )
    drawing.add(
        String(
            52,
            188,
            f"Physical surfaces: {layer.get('entry_surface_patch_id')} / "
            f"{layer.get('exit_surface_patch_id')}",
            fontName="ReportVera",
            fontSize=7,
        )
    )
    return drawing


def _direct_bolt_axis(
    visual: dict[str, Any], layers: list[dict[str, Any]], system: DisplayUnits
) -> Drawing:
    bolt = visual.get("bolt")
    if not isinstance(bolt, dict) or not isinstance(bolt.get("holes"), list):
        raise ReportingCoverageError("Direct bolt-axis stack is unavailable")
    drawing = Drawing(455, 174)
    drawing.add(
        String(
            8,
            160,
            "Native through-bolt and ply stack; not to scale",
            fontName="ReportVeraBold",
            fontSize=9,
        )
    )
    count = max(len(layers), 1)
    cell = 300 / count
    for index, layer in enumerate(layers):
        x = 55 + index * cell
        ply = Rect(x, 69, cell, 45)
        ply.strokeColor = colors.HexColor("#526675")
        ply.fillColor = None
        drawing.add(ply)
        mapping = layer.get("code_mapping", {})
        drawing.add(
            String(
                x + 3,
                133,
                f"{layer.get('layer_id')}: t "
                f"{display_quantity(mapping.get('layer_thickness'), system)}",
                fontName="ReportVera",
                fontSize=8,
            )
        )
        drawing.add(
            String(
                x + 3,
                120,
                f"hole d {display_quantity(layer.get('hole_diameter'), system)}",
                fontName="ReportVera",
                fontSize=8,
            )
        )
    drawing.add(Line(41, 91, 369, 91, strokeColor=colors.HexColor("#9b4435"), strokeWidth=3))
    unit = str(visual.get("length_unit", ""))
    drawing.add(
        String(
            55,
            50,
            f"Bolt d {_length_label(bolt.get('bolt_diameter'), unit, system)}",
            fontName="ReportVera",
            fontSize=8,
        )
    )
    washers = bolt.get("washers", [])
    if isinstance(washers, list):
        for index, washer in enumerate(washers[:2]):
            if isinstance(washer, dict):
                drawing.add(
                    String(
                        55,
                        37 - index * 12,
                        f"{washer.get('location')} washer OD "
                        f"{_length_label(washer.get('outside_diameter'), unit, system)}",
                        fontName="ReportVera",
                        fontSize=8,
                    )
                )
    return drawing


def _multirow_drawing(
    visual: dict[str, Any], view: str, system: DisplayUnits = "INHERIT"
) -> Drawing:
    """Project the native plate and witness its physical row/line dimensions."""

    boundary = visual.get("boundary")
    bolts = visual.get("bolts")
    layers = visual.get("layers")
    if (
        not isinstance(boundary, list)
        or len(boundary) != 4
        or not isinstance(bolts, list)
        or not isinstance(layers, list)
        or not layers
    ):
        raise ReportingCoverageError("Canonical multi-row geometry is incomplete")
    x0, x1, y0, y1 = (float(value) for value in boundary)
    thickness = sum(float(layer["thickness"]["value"]) for layer in layers)
    corners = [
        (x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (-thickness / 2, thickness / 2)
    ]
    projected = [_projection(point, view) for point in corners]
    min_x = min(x for x, _ in projected)
    max_x = max(x for x, _ in projected)
    min_y = min(y for _, y in projected)
    max_y = max(y for _, y in projected)
    width = 455.0
    height = 295.0 if view == "plan" else 180.0 if view == "elevation" else 245.0
    scale = min(
        (width - 60) / max(max_x - min_x, 0.01),
        (height - (100 if view == "plan" else 55)) / max(max_y - min_y, 0.01),
    )

    def paper(point: tuple[float, float]) -> tuple[float, float]:
        return 38 + (point[0] - min_x) * scale, 42 + (point[1] - min_y) * scale

    figure = Drawing(width, height)
    points = [paper(point) for point in projected]
    for first, second in (
        (0, 1),
        (0, 2),
        (0, 4),
        (3, 1),
        (3, 2),
        (3, 7),
        (5, 1),
        (5, 4),
        (5, 7),
        (6, 2),
        (6, 4),
        (6, 7),
    ):
        figure.add(Line(*points[first], *points[second], strokeColor=colors.HexColor("#586b78")))
    for bolt in bolts:
        bolt_id = str(bolt["bolt_id"])
        x, y = float(bolt["x"]), float(bolt["y"])
        center = paper(_projection((x, y, 0), view))
        radius = float(bolt["bolt_diameter"]["value"]) * scale / 2
        if view == "plan":
            hole_radius = float(bolt["hole_diameter"]["value"]) * scale / 2
            figure.add(
                Circle(
                    center[0],
                    center[1],
                    hole_radius,
                    strokeColor=colors.HexColor("#526675"),
                    fillColor=None,
                    strokeWidth=0.55,
                )
            )
            figure.add(
                Circle(
                    center[0],
                    center[1],
                    radius,
                    strokeColor=colors.HexColor("#9b4435"),
                    fillColor=None,
                )
            )
        else:
            start = paper(_projection((x, y, -thickness / 2), view))
            end = paper(_projection((x, y, thickness / 2), view))
            figure.add(Line(*start, *end, strokeColor=colors.HexColor("#9b4435"), strokeWidth=2))
        figure.add(
            String(
                center[0] if view == "plan" else center[0] + 3,
                center[1] - radius - 10 if view == "plan" else center[1] + 4,
                bolt_id,
                textAnchor="middle" if view == "plan" else "start",
                fontName="ReportVera",
                fontSize=7.5 if view == "plan" else 9,
            )
        )
    unit = str(visual.get("source_length_unit", "length units"))
    if view == "plan":
        row_x = sorted({float(bolt["x"]) for bolt in bolts})
        line_y = sorted({float(bolt["y"]) for bolt in bolts})
        x_chain = [x0, *row_x, x1]
        y_chain = [y0, *line_y, y1]
        for index, (left_x, right_x) in enumerate(pairwise(x_chain)):
            native = (
                visual.get("unloaded_end_e1")
                if index == 0
                else visual.get("loaded_boundary_to_row_1_distance")
                if index == len(x_chain) - 2
                else visual.get("pitch")
            )
            label = (
                _dimension_label(native, system)
                if isinstance(native, dict)
                else _length_label(right_x - left_x, unit, system)
            )
            _dimension_witness(
                figure,
                paper((left_x, y0)),
                paper((right_x, y0)),
                axis="x",
                offset=25,
                label=("e1 " if index == 0 else "p " if index < len(x_chain) - 2 else "eL ")
                + label,
            )
        for index, (low_y, high_y) in enumerate(pairwise(y_chain)):
            native = (
                visual.get("negative_side_distance")
                if index == 0
                else visual.get("positive_side_distance")
                if index == len(y_chain) - 2
                else visual.get("gauge")
            )
            label = (
                _dimension_label(native, system)
                if isinstance(native, dict)
                else _length_label(high_y - low_y, unit, system)
            )
            _dimension_witness(
                figure,
                paper((x0, low_y)),
                paper((x0, high_y)),
                axis="y",
                offset=21,
                label=("s- " if index == 0 else "g " if index < len(y_chain) - 2 else "s+ ")
                + label,
            )
        first_bolt = bolts[0]
        figure.add(
            String(
                235,
                265,
                f"Bolt d {display_quantity(first_bolt['bolt_diameter'], system)}; "
                f"hole d {display_quantity(first_bolt['hole_diameter'], system)}",
                fontName="ReportVera",
                fontSize=8,
            )
        )
        for index, layer in enumerate(layers[:3]):
            figure.add(
                String(
                    235,
                    253 - 11 * index,
                    f"{layer.get('layer_id')}: t "
                    f"{display_quantity(layer.get('thickness'), system)}",
                    fontName="ReportVera",
                    fontSize=8,
                )
            )
    if view == "elevation":
        figure.add(
            String(
                15,
                7,
                f"Boundary X: {x0:g} to {x1:g} {unit}; Y: {y0:g} to {y1:g} {unit}",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    figure.add(
        String(
            8, height - 12, f"{view.title()} - not to scale", fontName="ReportVeraBold", fontSize=9
        )
    )
    return figure


MAX_REPORT_PAGES = 1200


class _ReportDocument(BaseDocTemplate):
    def __init__(self, stream: io.BytesIO, *, pagesize: tuple[float, float], footer: str) -> None:
        super().__init__(
            stream, pagesize=pagesize, leftMargin=48, rightMargin=48, topMargin=54, bottomMargin=46
        )
        self.footer_text = footer
        self._outline_count = 0
        frame = Frame(48, 46, pagesize[0] - 96, pagesize[1] - 100, id="normal")
        self.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=self._on_page))

    def beforeDocument(self) -> None:
        self._outline_count = 0

    def _on_page(self, canvas: Canvas, document: BaseDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("ReportVera", 8)
        canvas.setFillColor(colors.HexColor("#526674"))
        available = self.pagesize[0] - 180
        footer = self.footer_text
        prefix, separator, digest = footer.rpartition(" | ")
        if separator:
            while pdfmetrics.stringWidth(footer, "ReportVera", 8) > available and prefix:
                prefix = prefix[:-1]
                footer = f"{prefix.rstrip(' |')}... | {digest}"
        else:
            while pdfmetrics.stringWidth(footer, "ReportVera", 8) > available and footer:
                footer = footer[:-1]
            if footer != self.footer_text:
                footer = footer.rstrip(" |") + "..."
        canvas.drawString(48, 30, footer)
        canvas.restoreState()

    def afterFlowable(self, flowable: Flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name.startswith("ReportHeading"):
            self._outline_count += 1
            key = f"section-{self._outline_count}"
            self.canv.bookmarkPage(key)
            title = flowable.getPlainText()
            first_word = title.split(" ", 1)[0]
            level = 0 if first_word.isdigit() or title.startswith(("Appendix", "TECHNICAL")) else 1
            self.canv.addOutlineEntry(title, key, level=level)
            self.notify("TOCEntry", (level, escape(title), self.page, key))

    def afterPage(self) -> None:
        if self.page > MAX_REPORT_PAGES:
            raise ReportingCoverageError(
                f"REPORT1 exceeds the {MAX_REPORT_PAGES}-page export limit"
            )


class _NumberedCanvas(Canvas):
    _page_states: list[dict[str, Any]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self._doc.Catalog.Lang = PDFString("en-US")  # type: ignore[attr-defined]
        self._page_states = []
        self._pending_bookmarks: dict[int, list[str]] = {}

    def bookmarkPage(
        self,
        key: object,
        fit: str = "Fit",
        left: object = None,
        top: object = None,
        bottom: object = None,
        right: object = None,
        zoom: object = None,
    ) -> Destination:
        """Bind anchors when buffered pages are finally emitted.

        The page-number footer replays the canvas at save time. ReportLab's
        document page counter stays at page one during the first pass, so an
        ordinary bookmarkPage call binds every destination to that page.
        """

        if (
            not isinstance(key, str)
            or fit != "Fit"
            or any(value is not None for value in (left, top, bottom, right, zoom))
        ):
            raise ValueError("REPORT1 section anchors use whole-page destinations")
        self._pending_bookmarks.setdefault(len(self._page_states) + 1, []).append(key)
        return cast("Destination", self._bookmarkReference(key))  # type: ignore[attr-defined]

    def showPage(self) -> None:
        self._page_states.append(dict(self.__dict__))
        self._startPage()  # type: ignore[attr-defined]

    def save(self) -> None:
        total = len(self._page_states)
        for page_number, state in enumerate(self._page_states, start=1):
            self.__dict__.update(state)
            for key in self._pending_bookmarks.get(page_number, []):
                super().bookmarkPage(key)
            self.saveState()
            self.setFont("ReportVera", 8)
            self.setFillColor(colors.HexColor("#526674"))
            self.drawRightString(
                self._pagesize[0] - 48,  # type: ignore[attr-defined]
                30,
                f"Page {self._pageNumber} of {total}",  # type: ignore[attr-defined]
            )
            self.restoreState()
            super().showPage()
        super().save()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="ReportVeraBold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#153949"),
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "ReportHeading",
            parent=base["Heading2"],
            fontName="ReportVeraBold",
            fontSize=12,
            leading=15,
            spaceBefore=13,
            spaceAfter=6,
            keepWithNext=1,
            textColor=colors.HexColor("#153949"),
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="ReportVera",
            fontSize=10.5,
            leading=14,
            spaceAfter=5,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName="ReportVera",
            fontSize=9,
            leading=12,
            spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "ReportTable", parent=base["BodyText"], fontName="ReportVera", fontSize=9, leading=12
        ),
        "caption": ParagraphStyle(
            "ReportCaption",
            parent=base["BodyText"],
            fontName="ReportVera",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=9,
        ),
    }


def _table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    if len(rows) > MAX_TABLE_ROWS:
        raise ReportingCoverageError("REPORT1 table exceeds the configured row limit")
    data = [[_paragraph("Field", styles["table"]), _paragraph("Native value", styles["table"])]]
    data.extend(
        [_paragraph(name, styles["table"]), _paragraph(value, styles["table"])]
        for name, value in rows
    )
    table = _ReportTable(
        data,
        colWidths=[190, 295],
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
        rowSplitRange=(2, -5) if len(data) >= 8 else (2, -2) if len(data) >= 3 else None,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#9cadb5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _append_bounded_tables(
    story: list[Flowable], rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> None:
    """Keep a final schedule chunk from becoming a lone-row continuation."""

    offset = 0
    while offset < len(rows):
        end = min(offset + 80, len(rows))
        if len(rows) - end == 1:
            end -= 1
        story.append(_table(rows[offset:end], styles))
        offset = end


def _add_linked_contents(story: list[Flowable], styles: dict[str, ParagraphStyle]) -> None:
    """Insert an indexed, linked contents with actual page numbers."""

    headings = [
        flowable.getPlainText()
        for flowable in story
        if isinstance(flowable, Paragraph) and flowable.style.name.startswith("ReportHeading")
    ]
    if len(headings) < 5:
        return
    major = ParagraphStyle(
        "ReportContentsMajor",
        parent=styles["small"],
        fontName="ReportVeraBold",
        fontSize=8.6,
        leading=10,
        leftIndent=0,
        rightIndent=35,
        spaceBefore=1,
    )
    minor = ParagraphStyle(
        "ReportContentsMinor",
        parent=styles["small"],
        fontSize=8,
        leading=9.5,
        leftIndent=18,
        rightIndent=35,
        spaceBefore=0,
    )
    contents = TableOfContents(
        levelStyles=[major, minor],
        dotsMinLevel=1,
        tableStyle=TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        ),
    )
    cover_table = next(
        (index for index, flowable in enumerate(story) if isinstance(flowable, Table)), 0
    )
    story[cover_table + 1 : cover_table + 1] = [
        PageBreak(),
        _paragraph("Contents", styles["title"]),
        contents,
        PageBreak(),
    ]


def _quantity(value: object, system: DisplayUnits = "INHERIT") -> str:
    if isinstance(value, dict) and "value" in value:
        return display_quantity(value, system)
    return _text(value)


def _factor_substitution(trace: object, system: DisplayUnits = "INHERIT") -> str:
    """Format the factor multiplication already performed by the native engine."""

    if not isinstance(trace, dict):
        raise ReportingCoverageError("Executed check lacks a native factor trace")
    if "equation_nominal_resistance" in trace:
        nominal = _quantity(trace.get("equation_nominal_resistance"), system)
        adjusted = _quantity(trace.get("connection_adjusted_nominal_resistance"), system)
        design = _quantity(trace.get("design_resistance"), system)
        names = (
            "lap_factor_c_lap",
            "pitch_factor_c_delta",
            "resistance_factor_phi",
            "time_effect_factor_lambda",
        )
        if any(name not in trace for name in names) or "Not supplied" in {
            nominal,
            adjusted,
            design,
        }:
            raise ReportingCoverageError("Executed check lacks a complete native factor trace")
        return (
            f"R_adj = R_n({nominal}) x C_lap({trace['lap_factor_c_lap']}) x "
            f"C_delta({trace['pitch_factor_c_delta']}) = {adjusted}\n"
            f"R_d = R_adj({adjusted}) x phi({trace['resistance_factor_phi']}) x "
            f"lambda({trace['time_effect_factor_lambda']}) = {design}"
        )
    nominal = _quantity(trace.get("nominal_resistance"), system)
    design = _quantity(trace.get("design_resistance"), system)
    factors = [
        (symbol, _text(trace[key]))
        for symbol, key in (
            ("C_delta", "c_delta"),
            ("C_lap", "c_lap"),
            ("phi", "phi"),
            ("lambda", "lambda_factor"),
        )
        if key in trace
    ]
    if not factors or nominal == "Not supplied" or design == "Not supplied":
        raise ReportingCoverageError("Executed check lacks a complete native factor trace")
    terms = " x ".join(f"{symbol}({_text(value)})" for symbol, value in factors)
    return f"R_d = ({nominal}) x {terms} = {design}"


def _single_factor_substitutions(
    check: dict[str, Any], system: DisplayUnits = "INHERIT"
) -> list[tuple[str, str]]:
    trace = check.get("equation_trace")
    if not isinstance(trace, dict):
        return []
    if "factor_trace" in trace:
        return [
            ("Executed factor substitution", _factor_substitution(trace["factor_trace"], system))
        ]
    if "branch_a_factor_trace" in trace and "branch_b_factor_trace" in trace:
        return [
            (
                "Cleavage branch A factor substitution",
                _factor_substitution(trace["branch_a_factor_trace"], system),
            ),
            (
                "Cleavage branch B factor substitution",
                _factor_substitution(trace["branch_b_factor_trace"], system),
            ),
        ]
    if "resistance_factor" in trace:
        return [
            (
                "Executed bolt factor substitution",
                f"R_d = ({_quantity(check.get('nominal_resistance'), system)}) x "
                f"phi({_text(trace['resistance_factor'])}) = "
                f"{_quantity(check.get('design_resistance'), system)}",
            )
        ]
    return []


def _append_result_unit_equivalents(
    story: list[Flowable],
    snapshot: ReportSnapshot,
    options: ReportOptions,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Show alternate units for every native result quantity without changing its value."""

    if options.display_units == "INHERIT":
        return
    rows = converted_quantity_rows(snapshot.result, options.display_units)
    if not rows:
        return
    story.append(_paragraph("Calculated result display-unit equivalents", styles["heading"]))
    _append_bounded_tables(story, rows, styles)


def _reader_opening(
    snapshot: ReportSnapshot,
    options: ReportOptions,
    result: dict[str, Any],
    status: str,
    system: DisplayUnits,
    styles: dict[str, ParagraphStyle],
    *,
    multirow_visual: dict[str, Any] | None = None,
) -> list[Flowable]:
    """Shared engineer-readable front matter for the specialized Direct modes."""

    from frp_master_connection.reporting.geometry import (
        canonical_bolt_points,
        canonical_boxes,
        canonical_faces,
        canonical_visual,
    )
    from frp_master_connection.reporting.reader_data import (
        collect_checks,
        governing,
        humanize,
        readable_value,
        short_number,
    )
    from frp_master_connection.reporting.reader_views import (
        colored_view,
        component_legend,
        multirow_physical_geometry,
    )

    checks = collect_checks(result)
    critical = governing(checks)
    missing = sum(
        check.required and check.availability not in {"CALCULATED", "NOT_APPLICABLE"}
        for check in checks
    )
    issued = datetime.fromtimestamp(snapshot.issued_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    story: list[Flowable] = [
        _paragraph(
            "Inputs and model report — design not evaluated"
            if snapshot.kind == "input_only"
            else "Connection calculation report",
            styles["title"],
        ),
        _paragraph(f"Status: {humanize(status)}", styles["small"]),
        _paragraph("1  Executive engineering summary", styles["heading"]),
        _table(
            [
                ("Project", options.project_name),
                ("Project number", options.project_number),
                ("Connection ID", options.connection_id or _text(result.get("connection_id"))),
                ("Revision", options.revision),
                ("Connection family", humanize(snapshot.family)),
                ("Native connection status", humanize(status)),
                (
                    "Numerical design status",
                    (
                        f"{humanize(critical.outcome)} (evaluated checks only)"
                        if status not in {"PASS", "FAIL"}
                        else humanize(critical.outcome)
                    )
                    if critical and snapshot.kind == "design"
                    else "Not evaluated",
                ),
                (
                    "Qualification / authority",
                    humanize(status) if status not in {"PASS", "FAIL"} else "See limitations",
                ),
                (
                    "Report completeness",
                    "Input draft only; no checks run"
                    if snapshot.kind == "input_only"
                    else f"{missing} required checks unevaluated",
                ),
                (
                    "Governing check",
                    f"{critical.name} — {critical.component}"
                    if critical
                    else "No evaluated numerical check",
                ),
                (
                    "Governing demand",
                    readable_value(critical.demand, system) if critical else "Not evaluated",
                ),
                (
                    "Design resistance",
                    readable_value(critical.resistance, system) if critical else "Not evaluated",
                ),
                (
                    "Utilization",
                    short_number(critical.utilization, ratio=True)
                    if critical and critical.utilization is not None
                    else "Not evaluated",
                ),
                ("Governing outcome", humanize(critical.outcome) if critical else "Not evaluated"),
                ("Calculated at", issued),
                ("Snapshot ID", snapshot.digest[:12]),
            ],
            styles,
        ),
    ]
    if multirow_visual is None:
        native_visual = canonical_visual(result)
        boxes = canonical_boxes(native_visual) if native_visual is not None else []
        faces = canonical_faces(native_visual) if native_visual is not None else []
        bolts = canonical_bolt_points(native_visual) if native_visual is not None else []
    else:
        boxes, bolts = multirow_physical_geometry(multirow_visual)
        faces = []
    story.append(_paragraph("2  Physical connection model", styles["heading"]))
    if snapshot.kind == "input_only":
        story.append(_paragraph("SUBMITTED GEOMETRY — NOT VALIDATED", styles["body"]))
    if boxes or faces:
        for view in ("isometric", "elevation", "plan"):
            story.append(colored_view(boxes, faces, bolts, view))
            if view == "isometric":
                story.append(_paragraph("Isometric - not to scale", styles["caption"]))
        story.append(
            _paragraph(
                "Fixed camera views of physical geometry in the authenticated backend "
                "snapshot. Color supplements native component IDs and shapes.",
                styles["small"],
            )
        )
        story.append(_table(component_legend(boxes, faces, bolts), styles))
    return story


def _reader_engineering_sections(
    snapshot: ReportSnapshot,
    result: dict[str, Any],
    system: DisplayUnits,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    from frp_master_connection.reporting.reader_data import (
        collect_checks,
        grouped_inputs,
        load_vectors,
    )
    from frp_master_connection.reporting.reader_tables import (
        limitations_matrix,
        loads_matrix,
        results_matrix,
    )

    story: list[Flowable] = []
    checks = collect_checks(result)
    groups = grouped_inputs(snapshot.request, system)
    story.append(_paragraph("3  Engineering inputs and design basis", styles["heading"]))
    for index, group in enumerate(
        (
            "Connection configuration",
            "Connected member",
            "Support and external handoff",
            "Connector",
            "Bolt, hole and hardware",
            "Bolt pattern",
            "Materials",
            "Environment and conditions",
        ),
        start=1,
    ):
        if groups.get(group):
            story.append(_paragraph(f"3.{index}  {group}", styles["heading"]))
            _append_bounded_tables(story, groups[group], styles)
    if groups.get("Loads and moments"):
        story.append(_paragraph("4  Submitted loads and moments", styles["heading"]))
        vectors = load_vectors(snapshot.request, system)
        if vectors:
            story.append(loads_matrix(vectors))
        _append_bounded_tables(story, groups["Loads and moments"], styles)
    if snapshot.kind != "input_only":
        story.append(_paragraph("5  Engineering results", styles["heading"]))
        if checks:
            story.append(results_matrix(checks, system))
        else:
            story.append(_paragraph("No native numerical check was evaluated.", styles["body"]))
        story.append(_paragraph("6  Unevaluated checks and design limitations", styles["heading"]))
        story.append(limitations_matrix(checks))
    return story


def render_single_bolt_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Render all native single-bolt inputs, check traces and canonical views."""

    if snapshot.family != "single-bolt":
        raise ReportingCoverageError(f"REPORT1 method adapter is missing for {snapshot.family}")
    _font_setup()
    system = resolved_display_units(snapshot.request, snapshot.result, options.display_units)
    result = snapshot.result.get(
        "client_design", snapshot.result.get("native_design", snapshot.result)
    )
    if not isinstance(result, dict):
        raise ReportingCoverageError("Native single-bolt result is unavailable")
    styles = _styles()
    status = _text(snapshot.result.get("overall_status", result.get("aggregate_status")))
    checks = result.get("results", [])
    if not isinstance(checks, list):
        raise ReportingCoverageError("Native check inventory is malformed")
    title = (
        "Inputs and model report - design not evaluated"
        if snapshot.kind == "input_only"
        else "Connection calculation report"
    )
    story = _reader_opening(snapshot, options, result, status, system, styles)
    if options.notes:
        story.append(_paragraph(f"Project notes: {options.notes}", styles["small"]))
    story.append(_paragraph("Scope and dimensioned geometry", styles["heading"]))
    story.append(
        _paragraph(
            "The direct connection transfers the submitted action through the selected bolt "
            "and its physical FRP layers. Only the listed load case and evaluated local "
            "checks are represented. Whole-member stability and any missing qualification "
            "remain outside this result.",
            styles["body"],
        )
    )
    visual = result.get("visualization")
    if not isinstance(visual, dict):
        raise ReportingCoverageError("Canonical native visualization is missing")
    direct_layers = result.get("resolved_layers")
    if isinstance(direct_layers, list) and isinstance(visual.get("bolt"), dict):
        story.append(
            _paragraph("Physical boundary and bolt-axis dimension details", styles["heading"])
        )
        for layer in direct_layers:
            if not isinstance(layer, dict):
                raise ReportingCoverageError("Direct physical layer is malformed")
            story.append(_direct_layer_detail(layer, visual["bolt"], system))
        story.append(_direct_bolt_axis(visual, direct_layers, system))
    story.extend(_reader_engineering_sections(snapshot, result, system, styles))
    story.append(_paragraph("7  Native check equations and substitutions", styles["heading"]))
    resolved_layers = result.get("resolved_layers", [])
    layers_by_id = (
        {
            layer["layer_id"]: layer
            for layer in resolved_layers
            if isinstance(layer, dict) and isinstance(layer.get("layer_id"), str)
        }
        if isinstance(resolved_layers, list)
        else {}
    )
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("plan"), dict):
            raise ReportingCoverageError("Native check record is malformed")
        plan = check["plan"]
        method = plan.get("limit_state")
        template = _SINGLE_BOLT_METHODS.get(str(method))
        if template is None:
            raise ReportingCoverageError(f"Executed check has no REPORT1 method template: {method}")
        evaluated = check.get("availability") == "CALCULATED"
        if evaluated and check.get("equation_trace") is None:
            raise ReportingCoverageError(
                f"Executed check has no numerical trace: {plan.get('check_id')}"
            )
        worked_rows = (
            single_native_substitutions(
                check,
                layers_by_id.get(plan.get("layer_id")),
                result.get("fastener") if isinstance(result.get("fastener"), dict) else None,
                system,
            )
            if evaluated
            else []
        )
        factor_rows = _single_factor_substitutions(check, system) if evaluated else []
        if evaluated and (
            not worked_rows
            or any("unavailable" in value.lower() for _, value in worked_rows + factor_rows)
        ):
            raise ReportingCoverageError(
                f"Executed single-bolt check lacks a faithful substitution: {plan.get('check_id')}"
            )
        story.append(_paragraph(f"{plan.get('check_id')} - {template.title}", styles["heading"]))
        story.append(_paragraph(template.explanation, styles["body"]))
        story.append(
            _table(
                [
                    ("Applicability", _text(check.get("availability"))),
                    (
                        "Source",
                        f"{plan.get('source_section', '')} / {plan.get('source_equation', '')}",
                    ),
                    ("Native expression", template.expression if evaluated else "Not executed"),
                    *worked_rows,
                    *factor_rows,
                    ("Demand", readable_value(check.get("demand"), system)),
                    ("Nominal resistance", readable_value(check.get("nominal_resistance"), system)),
                    ("Design resistance", readable_value(check.get("design_resistance"), system)),
                    (
                        "Utilization (display)",
                        short_number(check.get("utilization"), ratio=True)
                        if evaluated
                        else "Not evaluated",
                    ),
                    ("Outcome", humanize(check.get("numerical_comparison"))),
                    (
                        "Reason codes",
                        ", ".join(str(x) for x in plan.get("applicability_reason_codes", [])),
                    ),
                ],
                styles,
            )
        )
    story.append(_paragraph("Coverage and limitations", styles["heading"]))
    story.append(
        _table(
            [
                ("Aggregate status", status),
                (
                    "Governing check IDs",
                    ", ".join(str(x) for x in result.get("governing_check_ids", [])),
                ),
                (
                    "Qualification flags",
                    ", ".join(str(x) for x in result.get("qualification_flags", [])),
                ),
                ("Warnings", ", ".join(str(x) for x in result.get("warnings", []))),
                ("Issues", readable_value(result.get("issues", []), system)),
            ],
            styles,
        )
    )
    story.append(PageBreak())
    story.append(_paragraph("TECHNICAL AUDIT APPENDIX — COMPLETE NATIVE RECORD", styles["heading"]))
    story.append(
        _paragraph(
            "Exact submitted paths, native calculation records, source state and full "
            "precision are retained below.",
            styles["body"],
        )
    )
    story.append(_paragraph("Appendix A — Submitted request and provenance", styles["heading"]))
    _append_bounded_tables(
        story, [*_input_source_rows(snapshot), *_flatten("request", snapshot.request)], styles
    )
    story.append(_paragraph("Appendix B — Complete native result", styles["heading"]))
    _append_bounded_tables(story, _flatten("result", result), styles)
    if options.display_units != "INHERIT":
        input_equivalents = converted_quantity_rows(snapshot.request, options.display_units)
        if input_equivalents:
            story.append(_paragraph("Alternate display-unit equivalents", styles["heading"]))
            _append_bounded_tables(story, input_equivalents, styles)
    _append_result_unit_equivalents(story, snapshot, options, styles)
    if result is not snapshot.result:
        story.append(_paragraph("MAT1 material and condition authority", styles["heading"]))
        story.append(
            _table(
                _flatten(
                    "material_wrapper",
                    {
                        key: value
                        for key, value in snapshot.result.items()
                        if key not in {"client_design", "native_design"}
                    },
                ),
                styles,
            )
        )
    story.append(_paragraph("Calculation identity", styles["heading"]))
    story.append(
        _table(
            [
                ("Snapshot SHA-256", snapshot.digest),
                ("Native fingerprint", _text(result.get("calculation_fingerprint"))),
                ("Engine", _text(result.get("calculation_engine_version"))),
                ("Rule set", _text(result.get("engineering_rule_set_version"))),
                ("Calculation time (UTC epoch)", str(snapshot.issued_at)),
            ],
            styles,
        )
    )
    stream = io.BytesIO()
    document = _ReportDocument(
        stream,
        pagesize=PAPER_SIZES[options.paper],
        footer=(
            f"{options.connection_id or 'Connection'} | "
            f"{options.revision or 'No revision'} | {humanize(status)} | {snapshot.digest[:12]}"
        ),
    )
    document.title = title
    document.author = options.prepared_by or "FRP Master Connection"
    document.subject = "Native connection calculation with explicit design limits"
    _add_linked_contents(story, styles)
    document.multiBuild(story, canvasmaker=_NumberedCanvas)
    output = stream.getvalue()
    if not output.startswith(b"%PDF-"):
        raise RuntimeError("REPORT1 renderer did not produce a PDF")
    return output


def render_multirow_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Render the actual multi-row distribution and every native path result."""

    if snapshot.family != "multi-row":
        raise ReportingCoverageError(f"REPORT1 method adapter is missing for {snapshot.family}")
    _font_setup()
    system = resolved_display_units(snapshot.request, snapshot.result, options.display_units)
    result = snapshot.result.get(
        "client_design", snapshot.result.get("native_design", snapshot.result)
    )
    if not isinstance(result, dict):
        raise ReportingCoverageError("Native multi-row result is unavailable")
    preview = result.get("preview", result)
    if not isinstance(preview, dict) or not isinstance(preview.get("visualization"), dict):
        raise ReportingCoverageError("Canonical multi-row preview geometry is missing")
    calculation = result.get("calculation_result")
    if snapshot.kind == "design" and not isinstance(calculation, dict):
        raise ReportingCoverageError("Multi-row design response lacks its native result")
    checks = [] if calculation is None else calculation.get("results", [])
    if not isinstance(checks, list):
        raise ReportingCoverageError("Multi-row native check inventory is malformed")
    status = (
        "DESIGN_NOT_EVALUATED"
        if snapshot.kind == "input_only"
        else _text(
            snapshot.result.get("overall_status")
            or (calculation.get("overall_disposition") if isinstance(calculation, dict) else None)
        )
    )
    styles = _styles()
    visual = preview["visualization"]
    story = _reader_opening(
        snapshot, options, result, status, system, styles, multirow_visual=visual
    )
    story.append(_paragraph("Native dimensioned bolt layout", styles["heading"]))
    story.append(
        _paragraph(
            "The following witnesses identify the native boundary, row, gauge, bolt and "
            "hole dimensions. e1 is loaded end distance; p is bolt pitch; g is gauge; "
            "s+ and s- are side edge distances; hole d is hole diameter. "
            "All figures are not to scale.",
            styles["body"],
        )
    )
    for view in ("isometric", "plan", "elevation"):
        story.append(_multirow_drawing(visual, view, system))
        story.append(
            _paragraph(
                f"Canonical multi-row {view} projection. Dimensions and coordinates are listed "
                "from the same backend snapshot below.",
                styles["caption"],
            )
        )
    story.extend(_reader_engineering_sections(snapshot, result, system, styles))
    if isinstance(calculation, dict):
        story.append(_paragraph("7  Native check equations and substitutions", styles["heading"]))
        for check in checks:
            if not isinstance(check, dict):
                raise ReportingCoverageError("Multi-row native check record is malformed")
            method = str(check.get("equation_method"))
            template = _MULTIROW_METHODS.get(method)
            if template is None:
                raise ReportingCoverageError(
                    f"Executed multi-row method has no REPORT1 template: {method}"
                )
            evaluated = check.get("availability") == "CALCULATED"
            if evaluated and not isinstance(check.get("equation_trace"), dict):
                raise ReportingCoverageError(
                    f"Executed multi-row check has no native trace: {check.get('result_id')}"
                )
            try:
                executed_substitution = (
                    multirow_native_substitution(check, visual, system)
                    if evaluated
                    else "Not executed"
                )
            except ValueError as exc:
                raise ReportingCoverageError(str(exc)) from exc
            story.append(
                _paragraph(
                    f"{check.get('result_id')} - {template.title}",
                    styles["heading"],
                )
            )
            story.append(_paragraph(template.explanation, styles["body"]))
            story.append(
                _table(
                    [
                        ("Native method", method),
                        ("Source locator", _text(check.get("source_locator"))),
                        ("Expression", template.expression if evaluated else "Not executed"),
                        ("Executed numerical substitution", executed_substitution),
                        (
                            "Executed factor substitution",
                            _factor_substitution(check.get("factor_trace"), system)
                            if evaluated
                            else "Not executed",
                        ),
                        ("Applicability", _text(check.get("method_applicability"))),
                        ("Availability", _text(check.get("availability"))),
                        (
                            "Component / path",
                            " / ".join(
                                _text(check.get(key))
                                for key in (
                                    "layer_id",
                                    "bolt_id",
                                    "row_id",
                                    "bolt_line_id",
                                    "path_id",
                                )
                            ),
                        ),
                        ("Demand", readable_value(check.get("demand"), system)),
                        (
                            "Nominal resistance",
                            readable_value(check.get("equation_nominal_resistance"), system),
                        ),
                        (
                            "Adjusted resistance",
                            readable_value(
                                check.get("connection_adjusted_nominal_resistance"), system
                            ),
                        ),
                        (
                            "Design resistance",
                            readable_value(check.get("design_resistance"), system),
                        ),
                        (
                            "Utilization (display)",
                            short_number(check.get("utilization"), ratio=True)
                            if evaluated
                            else "Not evaluated",
                        ),
                        ("Outcome", humanize(check.get("numerical_comparison"))),
                        ("Qualification", humanize(check.get("qualification"))),
                        ("Warnings", _text(check.get("warnings"))),
                    ],
                    styles,
                )
            )
    story.append(PageBreak())
    story.append(_paragraph("TECHNICAL AUDIT APPENDIX — COMPLETE NATIVE RECORD", styles["heading"]))
    story.append(
        _paragraph(
            "Exact submitted paths, native calculation records, source state and full "
            "precision are retained below.",
            styles["body"],
        )
    )
    story.append(_paragraph("Appendix A — Submitted request and provenance", styles["heading"]))
    _append_bounded_tables(
        story, [*_input_source_rows(snapshot), *_flatten("request", snapshot.request)], styles
    )
    story.append(_paragraph("Appendix B — Complete native result", styles["heading"]))
    _append_bounded_tables(story, _flatten("result", result), styles)
    if options.display_units != "INHERIT":
        input_equivalents = converted_quantity_rows(snapshot.request, options.display_units)
        if input_equivalents:
            story.append(_paragraph("Alternate display-unit equivalents", styles["heading"]))
            _append_bounded_tables(story, input_equivalents, styles)
    if result is not snapshot.result:
        story.append(_paragraph("MAT1 material and condition authority", styles["heading"]))
        story.append(
            _table(
                _flatten(
                    "material_wrapper",
                    {
                        key: value
                        for key, value in snapshot.result.items()
                        if key not in {"client_design", "native_design"}
                    },
                ),
                styles,
            )
        )
    _append_result_unit_equivalents(story, snapshot, options, styles)
    story.append(_paragraph("Calculation identity", styles["heading"]))
    story.append(
        _table(
            [
                ("Snapshot SHA-256", snapshot.digest),
                ("Native fingerprint", _text(result.get("result_fingerprint"))),
                ("Calculation time (UTC epoch)", str(snapshot.issued_at)),
                ("Prepared by", options.prepared_by),
                ("Checked by", options.checked_by),
                ("Location", options.location),
                ("Project notes", options.notes),
            ],
            styles,
        )
    )
    stream = io.BytesIO()
    document = _ReportDocument(
        stream,
        pagesize=PAPER_SIZES[options.paper],
        footer=(
            f"{options.connection_id or 'Connection'} | "
            f"{options.revision or 'No revision'} | {humanize(status)} | {snapshot.digest[:12]}"
        ),
    )
    document.title = "Multi-row connection calculation report"
    document.author = options.prepared_by or "FRP Master Connection"
    document.subject = "Native multi-row calculation with explicit design limits"
    _add_linked_contents(story, styles)
    document.multiBuild(story, canvasmaker=_NumberedCanvas)
    return stream.getvalue()


def render_report_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Dispatch the native response through the shared ReportLab pipeline."""

    if snapshot.kind == "input_only" and snapshot.result.get("status") in {
        "INPUT_VALIDATION_FAILED",
        "INPUT_NOT_EVALUATED",
    }:
        from frp_master_connection.reporting.generic import render_generic_pdf

        return render_generic_pdf(snapshot, options)
    if snapshot.family == "single-bolt":
        return render_single_bolt_pdf(snapshot, options)
    if snapshot.family == "multi-row":
        return render_multirow_pdf(snapshot, options)
    from frp_master_connection.reporting.generic import render_generic_pdf

    return render_generic_pdf(snapshot, options)


__all__ = (
    "ReportOptions",
    "ReportingCoverageError",
    "render_multirow_pdf",
    "render_report_pdf",
    "render_single_bolt_pdf",
)
