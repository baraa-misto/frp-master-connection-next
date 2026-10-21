"Successor current-input calculation report; prints immutable backend results only."

import io
from html import escape
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from frp_master_connection.reporting.hyb2_d2_review import number, path_drawing, render_d2
from frp_master_connection.reporting.pdf import (
    ReportOptions,
    _font_setup,
    _multirow_drawing,
    render_report_pdf,
)
from frp_master_connection.reporting.snapshot import ReportSnapshot


def render_hybrid(record: dict[str, Any], *, technical: bool = False) -> bytes:
    """No engineering recomputation, applicability inference or status repainting."""
    a = record["assessment"]
    out = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    styles["BodyText"].spaceAfter = 6
    story: list[Flowable] = []

    def p(value: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(value)), styles[style]))

    def table(rows: list[list[object]], widths: list[int]) -> None:
        t = Table(
            [[Paragraph(escape(str(x)), styles["BodyText"]) for x in row] for row in rows],
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)

    p("Hybrid Connection Calculation Report", "Title")
    p(
        "Engineer-assisted calculation; ASCE-based LRFD and supplemental "
        "RHM ASD calculations retain separate bases."
    )
    p("Evaluated checks: " + a["evaluated_outcome"] + " - scoped to calculated methods", "Heading2")
    if a["r3_records"]:
        p(
            "RHM calculations are reference/conditional method calculations; "
            "structural applicability is not established."
        )
    p("Analytical coverage: " + a["coverage_state"] + ". " + record["coverage_summary"])
    p(
        "Qualification: "
        + a["qualification"]
        + ". Native F8/F9: "
        + a["native_status"]
        + " (unchanged)."
    )
    p("Physical fit: " + a["fit"]["state"] + ". " + a["fit"]["action"])
    for check in record["detailing_failures"]:
        p(
            "DETAILING REQUIREMENT FAIL: "
            + check["check_kind"]
            + "; "
            + check["boundary_label"]
            + "; actual "
            + str(check["actual_distance"])
            + " "
            + check["unit"]
            + "; required "
            + str(check["required_distance"])
            + " "
            + check["unit"]
            + ". "
            + check["source_rule"]
        )
    p("Workflow operational; structural method adoption and owner acceptance are not granted.")
    p("Current inputs and methods", "Heading2")
    p("Revision " + str(record["revision"]) + "; fingerprint " + record["fingerprint"])
    p("Data provenance: " + record["data_provenance"])
    p("Domain: " + a["source_domain"])
    q = record["inputs"]
    if q["geometry"] is not None:
        table(
            [["Geometry input", "Current declared value"]]
            + [
                [k, (v["value"] + " " + v["unit"]) if isinstance(v, dict) else v]
                for k, v in q["geometry"].items()
            ],
            [200, 310],
        )
    else:
        native = q["native_request"]["legacy"]["physical_connection"]["joint_assembly"]
        p("Native member geometry: " + str([(m["id"], m["section"]) for m in native["members"]]))
        p("Native original member-end actions: " + str(native["member_end_actions"]))
    p(
        "Selected alignment: "
        + q["alignment"]
        + ". Same backend geometry is used by the current viewer and calculation."
    )
    p(
        "Supplemental profile: "
        + q["source_profile"]
        + (
            "; source polyester 100 F, listed strengths/SF4, Ts=.85 and "
            "repeated Ts in D31/D221. Source 316SS included-thread shear 12.75"
            " ksi; no MAT1/F593 blending or storm relief."
        )
    )
    native = record["native_result"]
    materials = native.get("material_sources", {})
    if materials:
        material = materials["default"]
        p(
            "Actual native material records: "
            + str(material["display_name"])
            + "; ID "
            + str(material["id"])
            + "; "
            + str(material["property_basis"])
        )
        p("Actual native conditions: " + str(materials["condition_basis"]["default"]))
        fastener = native["fastener_source"]
        p(
            "Actual native hardware: "
            + str(fastener["catalog_record_id"])
            + "; Fnt "
            + str(fastener["fnt"])
            + "; "
            + str(fastener["source_classification"])
        )
        p("Current native bolt layout diagnostic", "Heading2")
        p(
            "The native template boundary is not automatically a physical free edge. "
            "Physical end/edge checks remain separate. Dimensions are from this same "
            "snapshot; not to scale."
        )
        _font_setup()
        story.append(_multirow_drawing(native["native_design"]["preview"]["visualization"], "plan"))
    p("Executed calculations", "Heading2")
    c = record["requested_computation"]
    p(
        str(c["rhm_comparisons_executed"])
        + "/"
        + str(c["rhm_comparisons_requested"])
        + " requested RHM comparisons and "
        + str(c["native_checks_executed"])
        + (
            " native numerical checks executed. This is computation scope, not"
            " complete structural coverage."
        )
    )
    table(
        [["Basis / case", "Check / scope", "Utilization / outcome"]]
        + [
            [
                r["basis"] + " / " + r["case_id"],
                r["mechanism"] + " / " + r["evidence_scope"],
                number(r["ratio"]) + " / " + r["outcome"],
            ]
            for r in a["comparisons"]
        ],
        [115, 270, 125],
    )
    for label, key in [("Governing LRFD", "governing_lrfd"), ("Governing ASD", "governing_asd")]:
        row = a[key]
        p(
            label + ": NOT EVALUATED"
            if row is None
            else label
            + ": "
            + row["mechanism"]
            + " / "
            + row["case_id"]
            + " / UR "
            + number(row["ratio"])
        )
        if row is not None:
            p("Governing equation: " + row["equation"])
            p("Current calculation trace: " + row["resistance_trace"])
    p("Supplied independent action sets", "Heading2")
    for basis in ["lrfd", "asd"]:
        for case in record["actions"][basis]:
            p(
                basis.upper()
                + " "
                + case["case_id"]
                + "; frame "
                + case["frame"]
                + "; reference "
                + str(case["reference"])
                + "; six actions "
                + str(case["components"])
            )
    for case, reason in record["withheld"]:
        p("NOT EVALUATED - " + case + ": " + reason)
    if a["r3_records"]:
        current = a["r3_records"][0][1]
        p("Current physical geometry and failure-path witnesses", "Heading2")
        p(
            "Actual vertical spacing "
            + current["vertical_pitch_in"]
            + " in; transverse LTV "
            + current["transverse_ltv_in"]
            + " in; longitudinal projection "
            + current["longitudinal_stagger_in"]
            + " in. Candidate cuts are not adopted fracture paths."
        )
        story.append(
            Table(
                [[path_drawing(current, "BRACE"), path_drawing(current, "COLUMN")]],
                colWidths=[255, 255],
            )
        )
    p("Detailing and coverage limitations", "Heading2")
    p(a["fit"]["action"])
    for text in a["fit"]["unknowns"]:
        p(text)
    p(record["coverage_summary"])
    p(record["field_use_note"])
    p(
        "OWNER_FIELD_USE_REPORTED. User declarations and programmatic "
        "input hashes are not laboratory, survey or professional-adoption "
        "evidence."
    )
    story.append(Spacer(1, 8))
    p(
        "No full connection qualification or unqualified installation "
        "approval is asserted. C13 and Section 2.3.2 remain open."
    )
    if technical:
        p("All current native detailing rule comparisons: " + str(record["detailing_checks"]))
    SimpleDocTemplate(
        out, pagesize=(612, 792), leftMargin=45, rightMargin=45, topMargin=38, bottomMargin=38
    ).build(story)
    primary = out.getvalue()
    if not technical:
        return primary
    # Preserve the complete D2/R3 native and exact calculation evidence in the audit.
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(primary)))
    writer.append(PdfReader(io.BytesIO(render_d2(record, technical=True))))
    context = record["native_report_context"]
    if context is not None:
        # The verified native snapshot context is itself sealed in this current
        # Hybrid record. Reuse its original report adapter, without engineering.
        snapshot = ReportSnapshot(
            context["family"],
            "design",
            context["request"],
            native,
            context["issued_at"],
            context["digest"],
            context["input_provenance"],
        )
        writer.append(
            PdfReader(
                io.BytesIO(render_report_pdf(snapshot, ReportOptions(mode="FULL_TECHNICAL_AUDIT")))
            )
        )
    audit = io.BytesIO()
    writer.write(audit)
    return audit.getvalue()
