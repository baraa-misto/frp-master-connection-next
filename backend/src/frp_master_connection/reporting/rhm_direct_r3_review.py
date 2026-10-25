"""Print immutable R3 records. No calculation, action transport or status authority."""

import io
from collections.abc import Sequence
from decimal import Decimal
from html import escape
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Table

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Block, R3ReviewBundle

TITLE = "Direct R3 - confirmed bolt geometry and physical paths"
OWNER_IMAGE = (
    Path(__file__).resolve().parents[4]
    / "docs/engineering/figures/HYB2_R3_OWNER_CONFIRMED_GEOMETRY.png"
)


def geometry_view(bundle: R3ReviewBundle, block: R3Block | None = None) -> Drawing:
    """Only map stored points to paper. Arrows and projection foot are backend records."""
    r = bundle.current
    d = Drawing(260, 255)
    if block is None:
        points = [xy for _, xy in r.bolt_centers] + [r.projection_foot]
    else:
        points = [p.start for p in block.paths] + [p.end for p in block.paths if p.end is not None]
    xs, ys = [float(p[0]) for p in points], [float(p[1]) for p in points]
    scale = min(175 / max(1, max(xs) - min(xs)), 140 / max(1, max(ys) - min(ys)))
    ox, oy = 45 - min(xs) * scale, 55 - min(ys) * scale

    def xy(point: tuple[Decimal, Decimal]) -> tuple[float, float]:
        return ox + float(point[0]) * scale, oy + float(point[1]) * scale

    def line(a: tuple[Decimal, Decimal], b: tuple[Decimal, Decimal], color: colors.Color) -> None:
        ax, ay = xy(a)
        bx, by = xy(b)
        d.add(Line(ax, ay, bx, by, strokeColor=color))

    for name, point in r.bolt_centers:
        x, y = xy(point)
        d.add(Circle(x, y, 4, fillColor=colors.white))
        d.add(String(x + 8, y + 5, name, fontSize=8))
    if block is None:
        centers = dict(r.bolt_centers)
        b1, b2 = centers["B1"], centers["B2"]
        line(b1, b2, colors.black)
        line(b1, r.projection_foot, colors.darkgreen)
        line(b2, r.projection_foot, colors.darkblue)
        fx, fy = xy(r.projection_foot)
        d.add(String(fx + 4, fy + 4, "F (projection foot; no hole)", fontSize=7))
        # Right-angle mark in the stored P/N directions, only graphic sizing.
        px, py = float(r.p_axis[0]) * 7, float(r.p_axis[1]) * 7
        nx, ny = float(r.n_axis[0]) * 7, float(r.n_axis[1]) * 7
        d.add(Line(fx - px, fy - py, fx - px - nx, fy - py - ny))
        d.add(Line(fx - px - nx, fy - py - ny, fx - nx, fy - ny))
        for label, axis, color in (
            ("P", r.p_axis, colors.darkgreen),
            ("V=-n", r.sketch_v_axis, colors.darkblue),
        ):
            x, y = 165, 205
            ex, ey = x + float(axis[0]) * 37, y + float(axis[1]) * 37
            d.add(Line(x, y, ex, ey, strokeColor=color))
            ux, uy = float(axis[0]), float(axis[1])
            d.add(
                Polygon(
                    [
                        ex,
                        ey,
                        ex - ux * 7 - uy * 3,
                        ey - uy * 7 + ux * 3,
                        ex - ux * 7 + uy * 3,
                        ey - uy * 7 - ux * 3,
                    ],
                    fillColor=color,
                    strokeColor=color,
                )
            )
            d.add(String(ex + 3, ey, label, fontSize=8, fillColor=color))
        for i, text in enumerate(
            (
                f"Actual B1-B2: {r.vertical_pitch_in:.6f} in",
                f"Transverse LTV: {r.transverse_ltv_in:.9f} in",
                f"Longitudinal / perpendicular to V: {r.longitudinal_stagger_in:.9f} in",
            )
        ):
            d.add(String(4, 35 - i * 13, text, fontSize=8))
    else:
        d.add(String(3, 240, block.member + " / " + block.branch + " release", fontSize=10))
        for path in block.paths:
            if path.end is not None:
                line(path.start, path.end, colors.darkblue)
            length = "WITHHELD" if path.length_in is None else f"{path.length_in:.6f} in"
            y = 25 if path.bolt_id == "B1" else 12
            d.add(String(3, y, path.bolt_id + " -> common edge: " + length, fontSize=8))
        ends = [p.end for p in block.paths if p.end is not None]
        if len(ends) == 2:
            line(ends[0], ends[1], colors.red)
        d.add(String(3, 224, block.edge.edge_id, fontSize=7))
    return d


def render_r3(bundle: R3ReviewBundle, *, technical: bool = False) -> bytes:
    """Round display only; exact full operands remain in technical PDF and paired JSON."""
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 11
    styles["BodyText"].spaceAfter = 5
    styles["BodyText"].wordWrap = "CJK"
    story: list[Flowable] = []

    def p(value: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(value)), styles[style]))

    def table(rows: Sequence[Sequence[object]], widths: list[int]) -> None:
        story.append(
            Table(
                [
                    [
                        Paragraph(
                            escape(
                                format(x, ".9g")
                                if isinstance(x, Decimal) and not technical
                                else str(x)
                            ),
                            styles["BodyText"],
                        )
                        for x in row
                    ]
                    for row in rows
                ],
                colWidths=widths,
                repeatRows=1,
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ],
            )
        )

    r = bundle.current
    p(TITLE + (" - exact technical appendix" if technical else ""), "Title")
    p("Reference calculations - not an adopted design", "Heading2")
    p(r.geometry_status + ". Public activation=false; qualification and owner acceptance pending.")
    if not technical:
        story.append(
            Table(
                [[Image(str(OWNER_IMAGE), width=210, height=248), geometry_view(bundle)]],
                colWidths=[225, 275],
            )
        )
        p(
            "Left: untouched nominal owner sketch. Right: current calculated "
            "annotation. Gauge x right/y up. "
            "Arrows indicate signed force direction. F is a right-angle "
            "projection foot, not a bolt."
        )
        p(
            f"Actual pitch is {r.vertical_pitch_in:.6f} in "
            f"({r.geometry.vertical_bolt_pitch.to(Unit.MM).magnitude:.6f} mm), without division by "
            "cos(phi). LTV is transverse to P and parallel to V; "
            "the perpendicular-to-V width is the longitudinal projection. "
            "These are not interchangeable tensile faces."
        )
        p(
            "Owner spacing and axes resolved; numerical results below are "
            "scoped reference arithmetic. "
            "Analytical coverage remains incomplete: Angle/W first-row, "
            "independent W paths, junction and C13 are unclosed. "
            "Source polyester listed strengths / SF4 and repeated Ts remain "
            "material limitations, not adopted product resistance."
        )
        p("Owner image SHA-256: " + r.sketch_sha256)
        story.append(PageBreak())
        p("Fresh paths in both members", "Heading1")
        story.append(
            Table(
                [
                    [geometry_view(bundle, r.blocks[0]), geometry_view(bundle, r.blocks[1])],
                    [geometry_view(bundle, r.blocks[2]), geometry_view(bundle, r.blocks[3])],
                ],
                colWidths=[250, 250],
            )
        )
        p(
            "Red joins the two endpoints on the identified common edge. Each "
            "ray was solved independently. "
            "Release rays oppose each member's action; the receiving column "
            "has the opposite reaction. "
            "For sketch V=-n, the column V release reaches the identified LEFT edge; "
            "its equation and datums are retained in the technical appendix."
        )
        p(r.placement_contract)
        story.append(PageBreak())
        p("Before / after numerical comparisons", "Heading1")
        p(
            "A: historical SIN; B: R2 COS with old pair; C: R3 actual "
            "gross-cut arithmetic; D: R3 same-surface net arithmetic. "
            "A/B and C/D describe different geometry and geometric "
            "conventions. No result is copied to a new layout."
        )
        rows: list[list[object]] = [
            ["Comparison / UR", "A historical", "B R2 COS", "C R3 gross", "D R3 net"]
        ]
        for old in bundle.predecessor.historical.comparisons:
            previous = next(
                x for x in bundle.predecessor.corrected.comparisons if x.method_id == old.method_id
            )
            current = [x for x in r.checks if x.method_id == old.method_id]
            rows.append(
                [
                    old.method_id,
                    old.utilization,
                    previous.utilization,
                    current[0].utilization,
                    current[1].utilization,
                ]
            )
        table(rows, [160, 85, 85, 85, 85])
        p("Current reference calculation outcomes", "Heading2")
        for row in r.checks:
            if (
                row.method_id.startswith("DIRECT_")
                and row.variant == "R3_SAME_SURFACE_NET_ARITHMETIC"
            ):
                color = (
                    "red"
                    if row.numerical_outcome == "FAIL"
                    else "green"
                    if row.numerical_outcome == "PASS"
                    else "black"
                )
                story.append(
                    Paragraph(
                        escape(row.method_id)
                        + ': <font color="'
                        + color
                        + '">'
                        + row.numerical_outcome
                        + "</font>",
                        styles["BodyText"],
                    )
                )
        p(
            "Local UR retains the source component/n convention and uses the "
            "shortest actual centerline path per branch; "
            "each separate bolt/path ratio remains in the exact record. Global"
            " witness uses Fs*actual Av + Ft*actual oblique At, "
            "with no claim this establishes an orthotropic failure law. No "
            "first-row or independent side path is inferred."
        )
        story.append(PageBreak())
        p("Same-surface material and limits", "Heading1")
        table(
            [
                [
                    "Member / branch",
                    "Actual Av gross/net in2",
                    "Connector gross/net in2",
                    "Projected connector net in2",
                ]
            ]
            + [
                [
                    b.member + " / " + b.branch,
                    f"{b.shear_gross_area_in2:.9f} / {b.shear_net_area_in2:.9f}",
                    f"{b.connector_gross_area_in2:.9f} / {b.connector_net_area_in2:.9f}",
                    b.perpendicular_projected_net_area_in2,
                ]
                for b in r.blocks
            ],
            [110, 135, 135, 120],
        )
        p(
            f"Actual B1-B2 connector length={r.blocks[0].cuts[-1].gross_length_in:.6f} in; "
            f"actual hole union removes {r.blocks[0].cuts[-1].removed_length_in:.6f} in. "
            "Projected gross and removed "
            "areas are BOTH projected. "
            "No projected effective width is mixed with an unprojected diameter deduction."
        )
        table(
            [["Preserved source factor", "Value (ksi unless dimensionless)"]]
            + [[k, v] for k, v in r.factor_trace],
            [300, 200],
        )
        p("Fresh brace-aligned comparison", "Heading2")
        p(
            f"Rotated corrected {r.vertical_pitch_in:.6f}-in pair about the same midpoint, "
            "boundaries fixed: "
            + "; ".join(f"{name}=({x:.6f}, {y:.6f}) in" for name, (x, y) in r.rotation_centers)
        )
        p(
            "Nominal hole fit: "
            + str(r.rotation_fit)
            + ". No inherited capacity. A no-fit result for this fixed placement "
            "does not rule out every brace-aligned connection."
        )
        p(
            "Isolated moment witness: 12 lbf-in, lever arm "
            + str(bundle.moment.actual_lever_arm_in)
            + " in; bolt forces "
            + "; ".join(f"({x:.6f}, {y:.6f})" for x, y in bundle.moment.forces_lbf)
            + " lbf; reconstructed moment="
            + str(bundle.moment.reconstructed_moment_lbf_in)
            + " lbf-in. This is not a finite-moment FRP resistance method."
        )
        for limit in r.limitations:
            p(limit)
        p(
            "The exact technical appendix and paired JSON retain coordinates, "
            "intersections, factors, dependent values "
            "and predecessor streams. The old spacing question is CLOSED by "
            "the owner sketch; remaining method questions are separate."
        )
    else:
        p("Current input binding: " + r.input_digest)
        p("Controlling order SHA-256: " + r.order_sha256)
        p("Controlling owner image SHA-256: " + r.sketch_sha256)
        p(r.placement_contract)
        for name, value in (
            ("bolt centers", r.bolt_centers),
            ("P axis", r.p_axis),
            ("N axis", r.n_axis),
            ("sketch V axis", r.sketch_v_axis),
            ("projection foot F", r.projection_foot),
            ("transverse LTV in", r.transverse_ltv_in),
            ("longitudinal projection in", r.longitudinal_stagger_in),
        ):
            p(name + ": " + str(value))
        for b in r.blocks:
            story.append(PageBreak())
            p(b.member + " / " + b.branch + " exact physical cuts", "Heading1")
            p(b.edge)
            p(
                "Member action axis: "
                + str(b.member_action_axis)
                + "; release axis: "
                + str(b.release_axis)
            )
            p(b.disposition)
            for path in b.paths:
                p(path)
            for cut in b.cuts:
                p(cut.cut.cut_id, "Heading2")
                p("Start: " + str(cut.cut.start) + "; end: " + str(cut.cut.end))
                p("Thickness: " + str(cut.cut.thickness))
                p(
                    "Actual length in: "
                    + str(cut.gross_length_in)
                    + "; union removed length: "
                    + str(cut.removed_length_in)
                )
                p(
                    "Gross / removed / net area in2: "
                    + str((cut.gross_area_in2, cut.removed_area_in2, cut.net_area_in2))
                )
                for hit in cut.intersections:
                    p(hit)
            p(
                "Separate perpendicular projections gross / removed / net in2: "
                + str(
                    (
                        b.perpendicular_projected_gross_area_in2,
                        b.perpendicular_projected_removed_area_in2,
                        b.perpendicular_projected_net_area_in2,
                    )
                )
            )
        story.append(PageBreak())
        p("Executed comparisons and factors", "Heading1")
        for row in r.checks:
            p(row)
        for factor in r.factor_trace:
            p(factor)
        for item in r.factor_ledger:
            p("Inherited source ledger: " + item)
        story.append(PageBreak())
        p("Numerical dependency ledger", "Heading1")
        for dependency in bundle.dependency_ledger:
            if dependency.quantity.endswith(":Lv/At/net"):
                continue  # Complete cut values above and JSON; no duplicate dataclass prose.
            p(dependency)
        p(
            "Full unrounded machine/native detail and both unchanged "
            "predecessor streams: paired JSON. "
            "Legacy R2 conditionals are evidence of old arithmetic, not adopted R3 areas."
        )
    stream = io.BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=(612, 792),
        leftMargin=48,
        rightMargin=48,
        topMargin=42,
        bottomMargin=42,
        title=TITLE,
    )

    def footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            48, 24, "R3 reference only | coverage / qualification pending | public activation=false"
        )
        canvas.drawRightString(564, 24, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
