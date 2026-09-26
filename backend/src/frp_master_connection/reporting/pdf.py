"""Controlled vector PDF presentation of an authenticated REPORT1 snapshot.

This renderer presents native numbers and trace records. It does not evaluate a
connection or synthesize a resistance from diagram dimensions.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFString
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

from frp_master_connection.reporting.snapshot import ReportSnapshot
from frp_master_connection.reporting.substitutions import single_native_substitutions
from frp_master_connection.reporting.units import DisplayUnits, converted_quantity_rows

PAPER_SIZES = {"LETTER": letter, "A4": A4}
MAX_TABLE_ROWS = 15_000


class ReportingCoverageError(ValueError):
    """An executed native calculation lacks a faithful REPORT1 adapter."""


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


def _multirow_drawing(visual: dict[str, Any], view: str) -> Drawing:
    """Project only the native plate boundary, layer thickness and bolt centers."""

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
    width, height = 455.0, 245.0
    scale = min((width - 60) / max(max_x - min_x, 0.01), (height - 55) / max(max_y - min_y, 0.01))

    def paper(point: tuple[float, float]) -> tuple[float, float]:
        return 25 + (point[0] - min_x) * scale, 30 + (point[1] - min_y) * scale

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
        figure.add(String(center[0] + 3, center[1] + 4, bolt_id, fontName="ReportVera", fontSize=9))
    unit = str(visual.get("source_length_unit", "length units"))
    if view != "isometric":
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
            self.canv.addOutlineEntry(flowable.getPlainText(), key, level=0)

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

    def showPage(self) -> None:
        if not hasattr(self, "_page_states"):
            self._page_states = []
        self._page_states.append(dict(self.__dict__))
        self._startPage()  # type: ignore[attr-defined]

    def save(self) -> None:
        total = len(self._page_states)
        for state in self._page_states:
            self.__dict__.update(state)
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
    table = Table(data, colWidths=[190, 295], repeatRows=1, hAlign="LEFT", splitByRow=1)
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


def _add_linked_contents(story: list[Flowable], styles: dict[str, ParagraphStyle]) -> None:
    """Link the reader-facing contents to the same numbered PDF outline bookmarks."""

    headings = [
        flowable.getPlainText()
        for flowable in story
        if isinstance(flowable, Paragraph) and flowable.style.name.startswith("ReportHeading")
    ]
    if len(headings) < 5:
        return
    contents: list[Flowable] = [PageBreak(), _paragraph("Contents", styles["title"])]
    contents.extend(
        Paragraph(
            f'<link href="#section-{index}">{escape(title)}</link>',
            styles["small"],
        )
        for index, title in enumerate(headings, start=1)
    )
    contents.append(PageBreak())
    first_figure = next(
        (index for index, flowable in enumerate(story) if isinstance(flowable, Drawing)),
        None,
    )
    first_heading = next(
        (
            index
            for index, flowable in enumerate(story)
            if isinstance(flowable, Paragraph) and flowable.style.name.startswith("ReportHeading")
        ),
        len(story),
    )
    insert_at = first_figure + 1 if first_figure is not None else first_heading
    story[insert_at:insert_at] = contents


def _quantity(value: object) -> str:
    if isinstance(value, dict) and "value" in value:
        return f"{value['value']} {value.get('unit', '')}".strip()
    return _text(value)


def _factor_substitution(trace: object) -> str:
    """Format the factor multiplication already performed by the native engine."""

    if not isinstance(trace, dict):
        return "No native factor-stage trace supplied"
    nominal = _quantity(trace.get("nominal_resistance"))
    design = _quantity(trace.get("design_resistance"))
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
        return "Native factor-stage substitution unavailable"
    terms = " x ".join(f"{symbol}({_text(value)})" for symbol, value in factors)
    return f"R_d = ({nominal}) x {terms} = {design}"


def _single_factor_substitutions(check: dict[str, Any]) -> list[tuple[str, str]]:
    trace = check.get("equation_trace")
    if not isinstance(trace, dict):
        return []
    if "factor_trace" in trace:
        return [("Executed factor substitution", _factor_substitution(trace["factor_trace"]))]
    if "branch_a_factor_trace" in trace and "branch_b_factor_trace" in trace:
        return [
            (
                "Cleavage branch A factor substitution",
                _factor_substitution(trace["branch_a_factor_trace"]),
            ),
            (
                "Cleavage branch B factor substitution",
                _factor_substitution(trace["branch_b_factor_trace"]),
            ),
        ]
    if "resistance_factor" in trace:
        return [
            (
                "Executed bolt factor substitution",
                f"R_d = ({_quantity(check.get('nominal_resistance'))}) x "
                f"phi({_text(trace['resistance_factor'])}) = "
                f"{_quantity(check.get('design_resistance'))}",
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
    for offset in range(0, len(rows), 80):
        story.append(_table(rows[offset : offset + 80], styles))


def render_single_bolt_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Render all native single-bolt inputs, check traces and canonical views."""

    if snapshot.family != "single-bolt":
        raise ReportingCoverageError(f"REPORT1 method adapter is missing for {snapshot.family}")
    _font_setup()
    result = snapshot.result.get(
        "client_design", snapshot.result.get("native_design", snapshot.result)
    )
    if not isinstance(result, dict):
        raise ReportingCoverageError("Native single-bolt result is unavailable")
    styles = _styles()
    story: list[Flowable] = []
    status = _text(snapshot.result.get("overall_status", result.get("aggregate_status")))
    checks = result.get("results", [])
    if not isinstance(checks, list):
        raise ReportingCoverageError("Native check inventory is malformed")
    calculated = [
        check
        for check in checks
        if isinstance(check, dict) and check.get("availability") == "CALCULATED"
    ]
    ratios = [
        (Decimal(str(check["utilization"])), str(check["plan"]["check_id"]))
        for check in calculated
        if check.get("utilization") is not None
    ]
    max_ratio = max(ratios, default=None)
    title = (
        "Inputs and model report - design not evaluated"
        if snapshot.kind == "input_only"
        else "Connection calculation report"
    )
    story.append(_paragraph(title, styles["title"]))
    story.append(_paragraph(f"Single-bolt direct connection | Status: {status}", styles["body"]))
    story.append(
        _table(
            [
                ("Calculated checks", str(len(calculated))),
                (
                    "Required checks not evaluated",
                    str(
                        sum(
                            bool(check.get("plan", {}).get("required"))
                            and check.get("availability") != "CALCULATED"
                            for check in checks
                            if isinstance(check, dict)
                        )
                    ),
                ),
                (
                    "Highest calculated utilization",
                    (
                        f"{max_ratio[0] * 100:.3f}% ({_ratio_side(max_ratio[0])}; "
                        f"exact native U in check detail) - {max_ratio[1]}"
                        if max_ratio is not None
                        else "None; no resistance evaluated"
                    ),
                ),
                ("Calculation case", _text(result.get("load_combination_id"))),
            ],
            styles,
        )
    )
    if status not in {"PASS", "FAIL"}:
        story.append(
            _paragraph(
                "Incomplete design - engineering review and source evidence may be required. "
                "This report records the identified calculation only.",
                styles["body"],
            )
        )
    story.append(
        _table(
            [
                ("Project", options.project_name),
                ("Project number", options.project_number),
                ("Connection ID", options.connection_id),
                ("Location", options.location),
                ("Revision", options.revision),
                ("Prepared by", options.prepared_by),
                ("Checked by", options.checked_by),
            ],
            styles,
        )
    )
    if options.notes:
        story.append(_paragraph(f"Project notes: {options.notes}", styles["small"]))
    story.append(_paragraph("Scope and geometry", styles["heading"]))
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
    for view in ("isometric", "elevation", "plan"):
        story.append(_drawing(visual, view))
        story.append(
            _paragraph(
                f"Canonical {view} projection; overall extent is derived from backend box "
                "geometry. Deferred heel/junction features are listed in the input schedule.",
                styles["caption"],
            )
        )
    story.append(_paragraph("Submitted and resolved input schedule", styles["heading"]))
    story.append(_table(_input_source_rows(snapshot), styles))
    story.append(
        _paragraph(
            "Every scalar submitted field is shown with its request path. Blank values mean "
            "not supplied; geometry and design values are not inferred from the drawing.",
            styles["small"],
        )
    )
    story.append(_table(_flatten("request", snapshot.request), styles))
    if options.display_units != "INHERIT":
        story.append(_paragraph("Alternate display-unit equivalents", styles["heading"]))
        story.append(
            _table(converted_quantity_rows(snapshot.request, options.display_units), styles)
        )
    for heading, key in (
        ("Materials and hardware", "material_assignments"),
        ("Resolved layer geometry", "resolved_layers"),
        ("Load assignment and transport", "source_action_trace"),
        ("Resolved bolt demand", "resolved_demand"),
    ):
        story.append(_paragraph(heading, styles["heading"]))
        story.append(_table(_flatten(key, result.get(key)), styles))
    story.append(_paragraph("Native check results and executed equations", styles["heading"]))
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
                    *(
                        single_native_substitutions(
                            check,
                            layers_by_id.get(plan.get("layer_id")),
                            result.get("fastener")
                            if isinstance(result.get("fastener"), dict)
                            else None,
                        )
                        if evaluated
                        else []
                    ),
                    *_single_factor_substitutions(check),
                    ("Demand", _quantity(check.get("demand"))),
                    ("Nominal resistance", _quantity(check.get("nominal_resistance"))),
                    ("Design resistance", _quantity(check.get("design_resistance"))),
                    ("Native utilization", _text(check.get("utilization"))),
                    ("Outcome", _text(check.get("numerical_comparison"))),
                    (
                        "Reason codes",
                        ", ".join(str(x) for x in plan.get("applicability_reason_codes", [])),
                    ),
                ],
                styles,
            )
        )
        if evaluated:
            story.append(
                _paragraph(
                    "Executed numerical substitution and intermediate trace", styles["small"]
                )
            )
            story.append(_table(_flatten("trace", check["equation_trace"]), styles))
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
                ("Issues", "; ".join(str(x) for x in result.get("issues", []))),
            ],
            styles,
        )
    )
    _append_result_unit_equivalents(story, snapshot, options, styles)
    story.append(_paragraph("Calculation identity", styles["heading"]))
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
            f"{options.revision or 'No revision'} | {status} | {snapshot.digest[:12]}"
        ),
    )
    document.title = title
    document.author = options.prepared_by or "FRP Master Connection"
    document.subject = "Native connection calculation with explicit design limits"
    _add_linked_contents(story, styles)
    document.build(story, canvasmaker=_NumberedCanvas)
    output = stream.getvalue()
    if not output.startswith(b"%PDF-"):
        raise RuntimeError("REPORT1 renderer did not produce a PDF")
    return output


def render_multirow_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Render the actual multi-row distribution and every native path result."""

    if snapshot.family != "multi-row":
        raise ReportingCoverageError(f"REPORT1 method adapter is missing for {snapshot.family}")
    _font_setup()
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
    story: list[Flowable] = [
        _paragraph(
            "Inputs and model report - design not evaluated"
            if snapshot.kind == "input_only"
            else "Connection calculation report",
            styles["title"],
        ),
        _paragraph(f"Direct multi-row connection | Status: {status}", styles["body"]),
        _table(
            [
                ("Project", options.project_name),
                ("Project number", options.project_number),
                ("Connection ID", options.connection_id or _text(result.get("connection_id"))),
                ("Revision", options.revision),
                (
                    "Evaluation",
                    "None" if snapshot.kind == "input_only" else "Native multi-row design",
                ),
                (
                    "Calculated check count",
                    str(len(calculation.get("calculated_check_ids", [])))
                    if isinstance(calculation, dict)
                    else "0",
                ),
                (
                    "Incomplete check IDs",
                    ", ".join(calculation.get("incomplete_check_ids", []))
                    if isinstance(calculation, dict)
                    else "Design not run",
                ),
            ],
            styles,
        ),
        _paragraph("Load path and canonical geometry", styles["heading"]),
        _paragraph(
            "The submitted connection actions are assigned to the physical rows, bolt lines "
            "and FRP layers by the native distribution method recorded below. Local bolt, "
            "bearing, net-tension, inter-row and block paths are represented only where "
            "the backend executed or explicitly classified them. Whole-member and source "
            "qualification limitations remain visible.",
            styles["body"],
        ),
    ]
    visual = preview["visualization"]
    for view in ("isometric", "plan", "elevation"):
        story.append(_multirow_drawing(visual, view))
        story.append(
            _paragraph(
                f"Canonical multi-row {view} projection. Dimensions and coordinates are listed "
                "from the same backend snapshot below.",
                styles["caption"],
            )
        )
    story.append(_paragraph("Submitted inputs and selected conditions", styles["heading"]))
    story.append(_table(_input_source_rows(snapshot), styles))
    story.append(_table(_flatten("request", snapshot.request), styles))
    if options.display_units != "INHERIT":
        story.append(_paragraph("Alternate display-unit equivalents", styles["heading"]))
        story.append(
            _table(converted_quantity_rows(snapshot.request, options.display_units), styles)
        )
    story.append(_paragraph("Resolved geometry and load assignment", styles["heading"]))
    story.append(_table(_flatten("preview", preview), styles))
    for key, title in (
        ("automatic_demand_result", "Automatic demand assignment"),
        ("automatic_handoff_results", "Bolt and layer handoff"),
        ("automatic_group_mode_integration", "Group-mode integration"),
    ):
        if result.get(key) is not None:
            story.append(_paragraph(title, styles["heading"]))
            story.append(_table(_flatten(key, result[key]), styles))
    if isinstance(calculation, dict):
        story.append(_paragraph("Complete native check matrix", styles["heading"]))
        story.append(
            _table(
                [
                    (
                        str(check.get("result_id")),
                        f"{check.get('limit_state')} | {check.get('availability')} | "
                        f"demand {_quantity(check.get('demand'))} | "
                        f"R_d {_quantity(check.get('design_resistance'))} | "
                        f"UR {_text(check.get('utilization'))} | "
                        f"{check.get('numerical_comparison')}",
                    )
                    for check in checks
                    if isinstance(check, dict)
                ],
                styles,
            )
        )
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
                        (
                            "Executed factor substitution",
                            _factor_substitution(check.get("factor_trace"))
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
                        ("Demand", _quantity(check.get("demand"))),
                        ("Nominal resistance", _quantity(check.get("equation_nominal_resistance"))),
                        (
                            "Adjusted resistance",
                            _quantity(check.get("connection_adjusted_nominal_resistance")),
                        ),
                        ("Design resistance", _quantity(check.get("design_resistance"))),
                        ("Native utilization", _text(check.get("utilization"))),
                        ("Outcome", _text(check.get("numerical_comparison"))),
                        ("Qualification", _text(check.get("qualification"))),
                        ("Warnings", _text(check.get("warnings"))),
                    ],
                    styles,
                )
            )
            if evaluated:
                story.append(
                    _paragraph("Executed numerical inputs and intermediate values", styles["small"])
                )
                story.append(_table(_flatten("trace", check["equation_trace"]), styles))
        story.append(_paragraph("Coverage and limitations", styles["heading"]))
        story.append(
            _table(
                _flatten(
                    "calculation",
                    {key: value for key, value in calculation.items() if key != "results"},
                ),
                styles,
            )
        )
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
            f"{options.revision or 'No revision'} | {status} | {snapshot.digest[:12]}"
        ),
    )
    document.title = "Multi-row connection calculation report"
    document.author = options.prepared_by or "FRP Master Connection"
    document.subject = "Native multi-row calculation with explicit design limits"
    _add_linked_contents(story, styles)
    document.build(story, canvasmaker=_NumberedCanvas)
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
