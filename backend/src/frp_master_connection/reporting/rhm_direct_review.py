"""Print-only immutable Direct source reference; no engineering in the PDF renderer."""

import io
from html import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_reference import DirectSourceCase


def source_path_drawing(book: DirectSourceCase) -> Drawing:
    """Dimensioned coordinate witness from the already executed support pair record."""
    drawing = Drawing(500, 245)
    scale, ox, oy = 48, 285, 125
    xb = float(book.geometry.xb.to(Unit.IN).magnitude)
    xc = float(book.geometry.xc.to(Unit.IN).magnitude)
    spacing = float(book.paths.vertical_spacing.magnitude)
    for x, color, label in (
        (-xb, colors.darkgreen, "Candidate brace-cut datum x=-Xb (review pending)"),
        (xc, colors.darkblue, "Column free edge x=Xc"),
    ):
        drawing.add(Line(ox + x * scale, 30, ox + x * scale, 220, strokeColor=color))
        drawing.add(String(15, 232 if x < 0 else 8, label, fontSize=9, fillColor=color))
    for i, (bolt_x, bolt_y) in enumerate(book.paths.bolt_centers, 1):
        px, py = ox + float(bolt_x) * scale, oy + float(bolt_y) * scale
        drawing.add(
            Circle(
                px,
                py,
                float(book.geometry.hole.to(Unit.IN).magnitude) / 2 * scale,
                strokeColor=colors.black,
                fillColor=None,
            )
        )
        drawing.add(String(15, py - 3, f"B{i} (0, {float(bolt_y):.6f}) in", fontSize=9))
        drawing.add(Line(ox - xb * scale, py, px, py, strokeColor=colors.darkgreen))
        drawing.add(Line(px, py, ox + xc * scale, py, strokeColor=colors.darkblue))
    drawing.add(Line(440, oy - spacing / 2 * scale, 440, oy + spacing / 2 * scale))
    drawing.add(String(15, 42, f"Pair spacing d_span/cos(phi) = {spacing:.9f} in", fontSize=9))
    drawing.add(
        String(
            15,
            28,
            f"Xb={xb:g} in, Xc={xc:g} in; "
            f"d_span={book.geometry.d_span.to(Unit.IN).magnitude} in (not bolt d)",
            fontSize=9,
        )
    )
    return drawing


def render_direct_reference(book: DirectSourceCase) -> bytes:
    """Render every executed comparison, assumptions and source summary without recalculation."""
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    story: list[Flowable] = []

    def p(text: str, style: str = "BodyText") -> None:
        story.extend((Paragraph(escape(text), styles[style]), Spacer(1, 5)))

    p("Direct L4/I8 supplemental source review", "Title")
    p("Reference calculations - not an adopted design", "Heading2")
    p("Stream: " + book.stream.value + "; method: HYB2-D1-R1-REFERENCE; ASD source basis.")
    p(
        "Coverage not established. Qualification: Section 2.3.2 unresolved. "
        "Public activation: false."
    )
    p(
        "Complete connection verification is not established: Angle and "
        "Supporting W first-row net tension, independent receiving-column "
        "inter-row and opposite-side block releases, Angle heel and W "
        "flange/web-junction behavior, out-of-plane contact/prying remain "
        "outstanding."
    )
    p(
        "Material limitations: source polyester listed properties/SF4 with "
        "its own temperature schedule. Product/statistical, duration and "
        "additional environmental applicability are not established. This is "
        "separate from current MAT1 and ASCE characteristic material "
        "authority."
    )
    p(
        "Owner reports satisfactory real-project use. No laboratory "
        "qualification or documented testing envelope is supplied."
    )
    p(
        "Original saved source: L4x4x0.5 / I8x4x0.375, direct one-sided contact. Two 0.5-in "
        "316SS bolts, included-thread fixed 12.75-ksi reference. No Tee, "
        "doubler or reinforcement."
    )
    p("Source workbook SHA256: " + book.source_hash)
    p("Dimensioned coordinate mapping", "Heading2")
    p(
        "Candidate datum interpretation only: x right, y up; source brace "
        "u=(cos(phi),-sin(phi)). Supporting pair centered at origin. True Xb "
        "fabrication datum and source gross/effective length convention "
        "remain subject to owner review. No displayed crop creates a member "
        "end."
    )
    story.append(source_path_drawing(book))
    p("Geometry and path ledger", "Heading2")
    p(repr(book.geometry))
    p(
        "Holes: "
        + ", ".join(book.paths.hole_inventory)
        + (
            "; explicit hole input is a geometry witness, absent from the source "
            "resistance equations. No hole deduction policy is invented."
        )
    )
    for name, length in book.paths.lengths:
        p(f"Input!{name} = {length.magnitude} {length.unit}")
    p(
        "LTV=d_span*sin(phi) is retained as the source-prescribed length. It "
        "is not automatically the projection of the actual vertical bolt "
        "spacing along the brace axis (spacing*sin(phi)). These differ; "
        "physical fracture-path adoption remains open."
    )
    p("Executed reference comparisons", "Heading2")
    p("Shared input and property audit", "Heading3")
    for op in book.comparisons[0].operands:
        p(f"{op.name}={op.quantity.magnitude} {op.quantity.unit}; {op.source_cell}; {op.meaning}")
    for row in book.comparisons:
        p(row.method_id + " / ASD reference / " + row.numerical_outcome, "Heading3")
        p(row.equation)
        p("Source cells: " + ", ".join(row.cells))
        p("Allowable capacities: " + repr(row.capacities))
        p("Directional reference ratios: " + repr(row.components))
        p("Complete reference utilization: " + str(row.utilization))
    p("Eight original summary locators - seven unique comparisons", "Heading2")
    for cell, value in book.source_summary:
        p(f"Calcs!{cell} = {value}")
    p("D46 and D159 refer to the same physical group. Resistance is not added or counted twice.")
    p(
        f"Bolt status in this stream: {book.bolt_status}. "
        f"Original literal E46: {book.original_literal_e46}. "
        "Corrected reference status follows D46; historical text remains historical."
    )
    p("Factor and applicability audit", "Heading2")
    for entry in book.factor_ledger:
        p(entry)
    p("Optional parts: " + book.optional_state)
    p(
        "Input!R50 historically reads blank R47. The tested R49 wiring "
        "correction is arithmetic evidence only. The scalar source couple is "
        "not a general vector demand model. Nonzero moments, signed reversal "
        "and out-of-plane actions are retained and withheld from "
        "authoritative supplemental use."
    )
    output = io.BytesIO()
    SimpleDocTemplate(
        output,
        pagesize=(612, 792),
        leftMargin=45,
        rightMargin=45,
        topMargin=40,
        bottomMargin=40,
        title="Direct L4/I8 source reference",
        author="Inactive HYB2 review",
    ).build(story)
    return output.getvalue()
