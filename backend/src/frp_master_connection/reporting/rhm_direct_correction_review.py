"""Print immutable R2 results and geometric witnesses; no resistance calculation."""

import io
from decimal import Decimal
from html import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
)

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_corrections import DirectCorrections

TITLE = "Direct RHM R2 - corrected LTV and actual-hole evidence"


def projection_drawing(record: DirectCorrections) -> Drawing:
    """Draw stored coordinates; the COS bar has deliberately unassigned endpoints."""
    drawing = Drawing(500, 285)
    ox, oy, scale = 185, 145, 65

    def line(a: tuple[Decimal, Decimal], b: tuple[Decimal, Decimal], color: colors.Color) -> None:
        drawing.add(
            Line(
                ox + float(a[0]) * scale,
                oy + float(a[1]) * scale,
                ox + float(b[0]) * scale,
                oy + float(b[1]) * scale,
                strokeColor=color,
            )
        )

    book = record.corrected
    top, bottom = book.paths.bolt_centers
    for index, point in enumerate((top, bottom), 1):
        drawing.add(
            Circle(
                ox + float(point[0]) * scale,
                oy + float(point[1]) * scale,
                float(book.geometry.hole.to(Unit.IN).magnitude) * scale / 2,
                fillColor=None,
            )
        )
        drawing.add(
            String(
                10,
                265 - index * 14,
                f"B{index} = ({float(point[0]):.6f}, {float(point[1]):.9f}) in",
                fontSize=9,
            )
        )
    line(top, bottom, colors.black)
    line(*record.d_segment_projection_endpoints, colors.darkblue)
    brace_v = record.physical_blocks[0]
    axis = brace_v.force_axis
    origin = (Decimal(0), Decimal(0))
    line(origin, axis, colors.darkblue)
    p_axis = next(b.force_axis for b in record.physical_blocks if b.branch == "P")
    line(origin, p_axis, colors.darkgreen)
    drawing.add(String(265, 235, "V: blue; P: green; x right / y up", fontSize=9))
    drawing.add(String(265, 220, "Same force axes for both member V branches", fontSize=9))
    drawing.add(
        String(265, 200, f"s_v = {float(record.vertical_bolt_spacing_in):.9f} in", fontSize=9)
    )
    drawing.add(String(265, 185, "Vertical B1-B2 physical center spacing", fontSize=9))
    drawing.add(String(265, 165, "Blue oblique segment = pair projection on V", fontSize=9))
    drawing.add(String(265, 150, "d_span = 2 in; endpoints tabulated below", fontSize=9))
    drawing.add(
        String(
            10,
            32,
            f"Actual pair perpendicular to V: "
            f"{float(record.actual_v_perpendicular_spacing_in):.9f} in",
            fontSize=9,
        )
    )
    drawing.add(
        Line(265, 75, 265 + float(record.corrected_ltv_in) * scale, 75, strokeColor=colors.darkred)
    )
    drawing.add(String(265, 60, f"Owner COS = {float(record.corrected_ltv_in):.9f} in", fontSize=9))
    drawing.add(String(265, 45, "Unassigned fracture endpoints; reference only", fontSize=9))
    return drawing


def render_direct_corrections(record: DirectCorrections) -> bytes:
    """Preserve full Decimal evidence in print; conditional areas stay conditional."""
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 10
    styles["BodyText"].wordWrap = "CJK"
    styles["BodyText"].spaceAfter = 4
    story: list[Flowable] = []

    def p(value: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(value)), styles[style]))

    def table(rows: list[list[object]], widths: list[int]) -> None:
        story.append(
            Table(
                [
                    [
                        Paragraph(
                            escape(format(x, ".12g") if isinstance(x, Decimal) else str(x)),
                            styles["BodyText"],
                        )
                        for x in row
                    ]
                    for row in rows
                ],
                colWidths=widths,
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ],
            )
        )

    p(TITLE, "Title")
    p("Reference calculations - not an adopted design", "Heading2")
    p(
        "Calculated reference PASS/FAIL is independent of coverage, applicability "
        "and qualification. "
        "No actual Direct resistance, public result, status or material authority changes."
    )
    p(
        "Coverage not established. Physical applicability: "
        + record.physical_applicability
        + ". Qualification: Section 2.3.2 unresolved. Public activation: false."
    )
    p(
        "Material limitations: source polyester listed strengths / SF4 and original temperature "
        "schedule only. Product/statistical, duration and other environmental applicability remain "
        "unestablished; these are not current MAT1/ASCE characteristic properties."
    )
    p(
        "Required first-row, independent receiving-W release, heel/junction and 3D mechanisms "
        "remain unevaluated. No missing check becomes PASS or N/A."
    )
    p("Correction ledger", "Heading2")
    p("HISTORICAL_REPLICATION: Input!L64=L51*SIN(N45); L65=L64. Original workbook unchanged.")
    p(
        "CORRECTED_SOURCE_CANDIDATE: Input!L64=L51*COS(N45); L65=L64. Owner R2 proposal; "
        "Calcs!D96 / D214, their areas, component capacities and D121 / D239 freshly recalculated."
    )
    p("Order SHA256: " + record.order_sha256)
    p("Workbook SHA256: " + record.historical.source_hash)
    p(f"Historical LTV={record.historical_ltv_in} in")
    p(f"Owner COS LTV={record.corrected_ltv_in} in")
    p(
        "Xb is the identifiable brace edge-to-bolt-column centerline distance; "
        "saved value .4375 in. "
        "The old thickness recipe is historical only. Local shear remains edge-to-centerline; "
        "no local half-hole deduction. Positive P/V only; opposite signs need their own edge paths."
    )
    p(
        "Hole diameter = "
        + str(record.corrected.geometry.hole.to(Unit.IN).magnitude)
        + " in, explicitly supplied review geometry; not an original workbook "
        "operand. Additional allowance = "
        + str(record.additional_hole_allowance_in)
        + " in. No implicit ASCE allowance."
    )
    p("Net-area interpretation", "Heading2")
    p(
        "Actual circle/cut net areas are geometric evidence. Source effective area "
        "minus actual-cut "
        "hole area is reported as HOLES_ONLY_CONDITIONAL / COMBINED_CONDITIONAL sensitivity, "
        "not validated actual net resistance. No geometry is resized to reconcile the source."
    )
    p(record.endpoint_question)
    story.append(PageBreak())
    p("Physical segment and force directions", "Heading1")
    story.append(projection_drawing(record))
    p(
        "Projection endpoints for the 2-in d_span witness: "
        + repr(record.d_segment_projection_endpoints)
    )
    p(f"Physical vertical bolt spacing s_v={record.vertical_bolt_spacing_in} in")
    p(f"Actual perpendicular-to-V center spacing={record.actual_v_perpendicular_spacing_in} in")
    p(
        "The 2-in segment is the vertical pair's projection onto V under the "
        "inherited source frame. "
        "It is not demonstrated to be a physical connector with the owner's assumed orientation. "
        "Its COS projection cannot be substituted for the actual vertical-pair perpendicular width."
    )
    p(
        "Brace V rays meet one common free edge: lengths 1 and 3 in; source assumes 2 x 1 in. "
        "The actual vertical tension connector length also differs from the source effective LTV. "
        "Neither force equilibrium nor arithmetic establishes fracture stress capacity."
    )
    for block in record.physical_blocks:
        p(
            f"{block.member} {block.branch}: force axis={block.force_axis}; "
            f"perpendicular pair width={block.force_perpendicular_width_in} in"
        )
    for group in record.variants:
        story.append(PageBreak())
        p(f"{group.member} / {group.variant}", "Heading1")
        p(
            f"Reference numerical result: {group.numerical_outcome}; summed V/Rv + P/Rp "
            f"= {group.utilization}"
        )
        p(
            "Conditional scenarios do not establish physical net resistance. Listed stress x area "
            "is a source arithmetic sum before SF4/temperature, not an LRFD nominal resistance."
        )
        labels = [
            ("Source effective shear area (in2)", "source_shear_area_in2"),
            ("Source effective tension area (in2)", "source_tension_area_in2"),
            ("Actual cut hole shear area removed (in2)", "removed_shear_area_in2"),
            ("Actual cut hole tension area removed (in2)", "removed_tension_area_in2"),
            ("Conditional residual shear area (in2)", "conditional_net_shear_area_in2"),
            ("Conditional residual tension area (in2)", "conditional_net_tension_area_in2"),
            ("Listed shear stress (ksi)", "listed_shear_stress_ksi"),
            ("Listed tension stress (ksi)", "listed_tension_stress_ksi"),
            ("Allowable shear stress incl. Ts (ksi)", "allowable_shear_stress_ksi"),
            ("Allowable tension stress incl. Ts (ksi)", "allowable_tension_stress_ksi"),
            ("Listed stress x area sum (kip)", "listed_stress_area_sum_kip"),
            ("Allowable source capacity (kip)", "allowable_capacity_kip"),
            ("Independent ASD demand (kip)", "demand_kip"),
            ("Directional reference ratio", "ratio"),
        ]
        table(
            [["Operand", "V branch", "P branch"]]
            + [
                [label, *(getattr(row, field) for row in group.branches)] for label, field in labels
            ],
            [190, 165, 165],
        )
        p("Full source-cell trace (areas in in2, stress in psi, capacity in kip)", "Heading3")
        for row in group.branches:
            p(
                f"{row.branch} listed stress x area sum (kip), full precision: "
                f"{row.listed_stress_area_sum_kip}"
            )
            p(
                row.branch
                + ": "
                + "; ".join(f"Calcs!{cell}={value}" for cell, value in row.cell_trace)
            )
            p(row.applicability + (": " + row.reason if row.reason else ""))
    for block in record.physical_blocks:
        story.append(PageBreak())
        p(f"Technical cut audit / {block.member} {block.branch}", "Heading1")
        p(block.disposition)
        p(
            f"Actual gross/net shear areas={block.actual_shear_gross_area_in2} / "
            f"{block.actual_shear_net_area_in2} in2; actual gross/net tension areas="
            f"{block.actual_tension_gross_area_in2} / {block.actual_tension_net_area_in2} in2"
        )
        for surface in block.cuts:
            p(surface.cut.cut_id, "Heading2")
            p(
                f"Start={surface.cut.start}; end={surface.cut.end}; "
                f"thickness={surface.cut.thickness}"
            )
            p(
                f"Gross / union-removed length={surface.gross_length_in} / "
                f"{surface.removed_length_in} in; "
                f"gross / removed / net area={surface.gross_area_in2} / "
                f"{surface.removed_area_in2} / "
                f"{surface.net_area_in2} in2; positive residual={surface.available}"
            )
            for hit in surface.intersections:
                p(
                    f"{hit.hole_id}: {hit.disposition}; interval={hit.entry_in} to {hit.exit_in} "
                    f"in; "
                    f"removed length={hit.removed_length_in} in; diameter "
                    f"fraction={hit.diameter_fraction}"
                )
        p(
            "Intervals are unioned once per surface. Coincident brace/column holes are "
            "separate member "
            "surfaces. Full/half/partial intersections follow geometry, not a blanket hole count."
        )
    output = io.BytesIO()

    def footer(canvas: Canvas, _: BaseDocTemplate) -> None:
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(566, 20, f"R2 inactive reference - Page {canvas.getPageNumber()}")

    SimpleDocTemplate(
        output,
        pagesize=(612, 792),
        leftMargin=46,
        rightMargin=46,
        topMargin=36,
        bottomMargin=36,
        title=TITLE,
        author="Inactive HYB2 R2 review",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
