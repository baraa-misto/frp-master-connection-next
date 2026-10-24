"""Print verified immutable D2 evidence; no engineering or status calculations."""

import io
from decimal import Decimal
from html import escape
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

TITLE = "Direct hybrid - engineering adoption review"


def number(value: object) -> str:
    """Paper precision only; exact backend operands remain in the appendix/JSON."""
    return "not established" if value is None else format(Decimal(str(value)), ".16g")


def path_drawing(record: dict[str, Any], member: str) -> Drawing:
    blocks = [b for b in record["blocks"] if b["member"] == member]
    points = [p["start"] for b in blocks for p in b["paths"]]
    points += [p["end"] for b in blocks for p in b["paths"] if p["end"] is not None]
    xs, ys = [float(p[0]) for p in points], [float(p[1]) for p in points]
    scale = min(170 / max(1, max(xs) - min(xs)), 110 / max(1, max(ys) - min(ys)))
    ox, oy = 35 - min(xs) * scale, 30 - min(ys) * scale
    drawing = Drawing(250, 185)
    drawing.add(String(12, 170, member + " - stored directed rays", fontSize=9))
    for block in blocks:
        color = colors.darkblue if block["branch"] == "P" else colors.darkgreen
        for path in block["paths"]:
            x, y = ox + float(path["start"][0]) * scale, oy + float(path["start"][1]) * scale
            drawing.add(Circle(x, y, 4, fillColor=colors.white))
            if path["end"] is not None:
                ex = ox + float(path["end"][0]) * scale
                ey = oy + float(path["end"][1]) * scale
                drawing.add(Line(x, y, ex, ey, strokeColor=color))
                drawing.add(Circle(ex, ey, 2, fillColor=color))
            drawing.add(String(x + 5, y + 5, path["bolt_id"], fontSize=7))
    drawing.add(
        String(12, 12, "Blue=P; green=V. Candidate cuts, not adopted fracture.", fontSize=7)
    )
    return drawing


def render_d2(record: dict[str, Any], *, technical: bool = False) -> bytes:
    a = record["assessment"]
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].spaceAfter = 7
    styles["BodyText"].wordWrap = "CJK"
    styles.add(ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=7.5, leading=10))
    styles.add(
        ParagraphStyle(
            "Outcome",
            parent=styles["Heading2"],
            textColor={
                "red": colors.red,
                "green": colors.darkgreen,
                "neutral": colors.darkblue,
            }[a["tone"]],
        )
    )
    story: list[Flowable] = []

    def p(text: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(text)), styles[style]))

    def table(rows: list[list[object]], widths: list[int]) -> None:
        cells = [[Paragraph(escape(str(c)), styles["Cell"]) for c in row] for row in rows]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd2da")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)

    p(TITLE, "Title")
    p("REVIEW ONLY - NO ENGINEERING ADOPTION GRANTED", "Heading2")
    p("Evaluated checks: " + a["evaluated_outcome"] + " (scoped)", "Outcome")
    p("Analytical coverage: " + a["coverage_state"] + "; physical fit: " + a["fit"]["state"])
    p(
        "Qualification: "
        + a["qualification"]
        + ". Complete connection verification is not established."
    )
    p("Native F8/F9: " + a["native_status"] + " (unchanged).")
    p("Authority: " + a["scope"])
    p(
        "ASCE/SEI 74-23 LRFD and supplemental RHM ASD retain independent actions and resistance "
        "bases. A numerical PASS applies only to evaluated comparisons; it is not complete design "
        "acceptance. Method-development notes do not recolor numerical results. "
        "Actual FAIL stays red."
    )
    p("Source and material scope", "Heading2")
    p(a["source_domain"])
    c = record["source_conditions"]
    if a["source_domain"] == "NATIVE_GEOMETRY_ONLY_NO_SOURCE_MAPPING":
        p("No supplemental RHM property set is applied to this native calculation.")
    else:
        p(
            "Source resin: " + c["resin"] + "; temperature: " + str(c["temperature_f"]) + " F. "
            "RHM listed strengths / SF4; source Ts=.85, including repeated Ts in D31/D221. "
            "316SS included-thread 12.75-ksi shear remains reference only."
        )
        p(
            "Actual MAT1/F593 authority is independent. Source product statistics, duration, "
            "moisture, chemical and orthotropic applicability are not established. Storm relief "
            "is excluded. Entered M=0 does not prove zero transported 3D moment."
        )
    native = record["native_result"]
    material = native.get("material_sources", {}).get("default", {})
    if material:
        p(
            "Actual native material: "
            + str(material.get("display_name")).replace("\u2014", "-")
            + "; record="
            + str(material.get("id"))
        )
        condition = native["material_sources"]["condition_basis"]["default"]
        p(
            "Native conditions: sustained="
            + str(condition["sustained_f"])
            + " F; maximum="
            + str(condition["maximum_f"])
            + " F; moisture="
            + str(condition["reference_condition"])
            + "; Tg basis="
            + str(condition["tg_evidence"])
        )
        fastener = native.get("fastener_source", {})
        p(
            "Actual native fastener: "
            + str(fastener.get("catalog_record_id"))
            + "; Fnt="
            + str(fastener.get("fnt"))
            + "; source="
            + str(fastener.get("source_classification"))
        )
    p("Physical installation", "Heading2")
    f = a["fit"]
    h = record["hardware_evidence"]
    p("Hole containment: " + f["hole_state"] + "; washer: " + f["washer_state"])
    p("Bearing face: " + h["bearing_face"] + "; actual washer OD: " + str(h["washer_od"]))
    p(
        "ASCE 8.2.4 conditional screen: OD=" + number(f["screening_od_in"]) + " in; "
        "Xb overhang=" + number(f["conditional_overhang_in"]) + " in if this is the bearing-face "
        "free edge. Confirmed actual overhang=" + number(f["actual_overhang_in"]) + " in."
    )
    p(f["action"])
    for unknown in f["unknowns"]:
        p("Unverified: " + unknown)
    p(a["notes"][0])
    p("Paired actions digest: " + a["paired_digest"])
    p("Native payload SHA256: " + a["native_payload_sha256"])
    p("Current source fingerprint: " + record["source_fingerprint"])
    story.append(PageBreak())

    p("Executed calculations", "Heading1")
    p(
        "Seven unique source comparisons count the shared physical bolt group once. Native rows "
        "retain their original per-bolt/member IDs. Capacities and utilization "
        "are never added across bases."
    )
    rows: list[list[object]] = [
        ["Check / method", "Basis / combination", "Utilization", "Outcome / scope"]
    ]
    for row in a["comparisons"]:
        rows.append(
            [
                row["mechanism"],
                row["basis"] + " / " + row["case_id"],
                number(row["ratio"]),
                row["outcome"] + " / " + row["evidence_scope"],
            ]
        )
    table(rows, [170, 105, 92, 165])
    for case, reason in a["withheld"]:
        p(case + " NOT EVALUATED: " + reason)
    p("Governing comparisons", "Heading2")
    for basis in ("lrfd", "asd"):
        g = a["governing_" + basis]
        p(
            basis.upper()
            + ": "
            + (
                g["mechanism"] + " / " + g["case_id"] + " / UR=" + number(g["ratio"])
                if g
                else "NOT EVALUATED"
            )
        )
    p("Complete independent design action sets: " + str(a["case_sets_complete"]))
    for basis in ("lrfd", "asd"):
        for case in record["actions"][basis]:
            values = [
                "unknown" if x is None else number(x["magnitude"]) + " " + x["unit"]
                for x in case["components"]
            ]
            p(
                basis.upper()
                + " "
                + case["case_id"]
                + "; source="
                + case["source_id"]
                + "; frame="
                + case["frame"]
                + "; six actions=["
                + ", ".join(values)
                + "]."
            )
    p(
        "Exact equations, substitutions, capacities, source cells, reference-point coordinates, "
        "all factors and full precision are retained in the technical audit "
        "appendix and companion JSON."
    )
    story.append(PageBreak())

    p("Physical paths and net material", "Heading1")
    for case, r3 in a["r3_records"]:
        p(case + ": one owner-confirmed pair shared by both members", "Heading2")
        p(
            "Actual vertical pitch="
            + number(r3["vertical_pitch_in"])
            + " in; transverse LTV="
            + number(r3["transverse_ltv_in"])
            + " in; longitudinal projection="
            + number(r3["longitudinal_stagger_in"])
            + " in."
        )
        story.append(
            Table([[path_drawing(r3, "BRACE"), path_drawing(r3, "COLUMN")]], colWidths=[260, 260])
        )
        paths: list[list[object]] = [
            ["Member / load branch", "Directed edge", "Lengths, in", "Net connector, in2"]
        ]
        for b in r3["blocks"]:
            paths.append(
                [
                    b["member"] + " / " + b["branch"],
                    b["edge"]["edge_id"],
                    " / ".join(number(x["length_in"]) for x in b["paths"]),
                    number(b["connector_net_area_in2"]),
                ]
            )
        table(paths, [90, 160, 160, 122])
        p(
            "The receiving I V rays cross an integral web. Flange-only lines do not "
            "establish a detached "
            "3D fragment. P and V are not independent left/right releases. Actual "
            "hole unions use the "
            "same surface; local tear-out retains source edge-to-centerline lengths."
        )
    if not a["r3_records"]:
        p(
            "No source resistance result is transferred onto this "
            "geometry/action/property selection. "
            "Use the unchanged native model where supplied; the fixed R3 BRACE "
            "rotation remains no-fit."
        )
    p(
        "Fs*Av + Ft*At on the actual oblique connector is an arithmetic witness. Its tensile term "
        "does not alone establish first-row net/bearing-bypass coverage. No "
        "3D/contact or qualification "
        "coverage is inferred from bolt equilibrium."
    )
    if a["r3_records"]:
        story.append(PageBreak())

    p("Engineering adoption decisions", "Heading1")
    p(
        "No production approvals are installed. Each unresolved mechanism below needs the named "
        "artifact from a qualified structural method reviewer / engineer of record."
    )
    decisions: list[list[object]] = [
        ["Required mechanism / disposition", "Exact evidence required"]
    ]
    for row in a["coverage"]:
        decisions.append(
            [
                row["native_id"] + " / " + row["disposition"],
                row["missing_artifact"].removeprefix(
                    "Separately fitted BRACE geometry and signed applicability proof. "
                )
                if row["missing_artifact"]
                else "Unchanged native authority; exact signed payload identity on cover.",
            ]
        )
    table(decisions, [212, 320])
    p("Unsigned decision record", "Heading2")
    p(
        "Engineer/date/signature: NOT PROVIDED. Adopted methods: NONE. Evidence must bind exact "
        "method, physical domain, source, validation and actions. "
        "Section 2.3.2 requires separate evidence."
    )
    p("C13-05/06/07/08 and qualification remain unresolved. Native F8/F9 authority is unchanged.")

    if technical:
        story.append(PageBreak())
        p("Technical audit appendix - exact stored evidence", "Heading1")
        p("Source conditions: " + str(record["source_conditions"]))
        p("Hardware evidence: " + str(record["hardware_evidence"]))
        for basis in ("lrfd", "asd", "transport_trace"):
            for case in record["actions"][basis]:
                p(case)
        for comparison in a["comparisons"]:
            p(comparison)
        for proposal in a["method_packet"]:
            p(proposal)
        for case, r3 in a["r3_records"]:
            p(case + " exact coordinates / edge equations", "Heading2")
            p(r3["bolt_centers"])
            for edge in r3["edges"]:
                p(edge)
            for block in r3["blocks"]:
                p(block["member"] + " " + block["branch"], "Heading2")
                p(block)
            for check in r3["checks"]:
                p(check)
            for dependency in r3["dependencies"]:
                p(dependency)
            for factor in r3["factor_ledger"]:
                p(factor)
            p(r3["factor_trace"])
        for note in a["notes"]:
            p(note)
        p("Companion JSON retains the complete backend record without truncation.")

    def footer(canvas: Canvas, doc: object) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 24, "D2-A | Inactive review | No qualification or adoption granted")
        canvas.drawRightString(565, 24, str(canvas.getPageNumber()))
        canvas.restoreState()

    SimpleDocTemplate(
        output, pagesize=(612, 792), leftMargin=40, rightMargin=40, topMargin=35, bottomMargin=42
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
