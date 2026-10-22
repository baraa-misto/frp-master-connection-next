"Successor current-input calculation report; prints immutable backend results only."

import io
from collections.abc import Sequence
from decimal import Decimal
from html import escape
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from frp_master_connection.reporting.hyb2_d2_review import path_drawing, render_d2
from frp_master_connection.reporting.hybrid_labels import label, utilization
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
    same = record.get("same_connection_lrfd")
    out = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    styles["BodyText"].spaceAfter = 6
    styles["Heading3"].keepWithNext = True
    if same is not None:
        styles["Heading1"].keepWithNext = True
        styles["Heading2"].keepWithNext = True
    story: list[Flowable] = []

    def p(value: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(value)), styles[style]))

    def table(rows: Sequence[Sequence[object]], widths: list[int]) -> None:
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
    p("Analytical coverage: " + label(a["coverage_state"]) + ". " + record["coverage_summary"])
    p(
        "Qualification: "
        + label(a["qualification"])
        + (
            ". The original native route was not invoked; freshly mapped ASCE components "
            "are identified below. Original F8/F9 authority is unchanged."
            if same is not None
            else ". Native completeness: " + label(a["native_status"]) + " (unchanged)."
        )
    )
    p("Physical fit: " + label(a["fit"]["state"]) + ". " + a["fit"]["action"])
    for check in record["detailing_failures"]:
        p(
            "DETAILING REQUIREMENT FAIL: "
            + (
                label(check["check_kind"])
                if "same_connection_lrfd" in record
                else check["check_kind"]
            )
            + (
                " / " + check["bolt_id"] + " / " + check["case_id"]
                if "same_connection_lrfd" in record and "bolt_id" in check
                else ""
            )
            + "; "
            + check["boundary_label"]
            + "; actual "
            + (
                utilization(check["actual_distance"], technical=technical)
                if "same_connection_lrfd" in record
                else str(check["actual_distance"])
            )
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
    p("Domain: " + label(a["source_domain"]))
    q = record["inputs"]
    if q["geometry"] is not None:
        table(
            [["Geometry input", "Current declared value"]]
            + [
                [label(k), (v["value"] + " " + v["unit"]) if isinstance(v, dict) else v]
                for k, v in q["geometry"].items()
            ],
            [200, 310],
        )
    else:
        native = q["native_request"]["legacy"]["physical_connection"]["joint_assembly"]
        table(
            [["Member / section input", "Current declared value"]]
            + [
                [
                    label(m["id"]) + " - " + label(k),
                    (v["value"] + " " + v["unit"]) if isinstance(v, dict) else label(v),
                ]
                for m in native["members"]
                for k, v in m["section"].items()
            ]
            + [
                [label(k), v["value"] + " " + v["unit"]]
                for k, v in q["native_request"]["legacy"].items()
                if isinstance(v, dict) and "value" in v
            ],
            [250, 260],
        )
        if technical:
            p("Native original member-end actions: " + str(native["member_end_actions"]))
    p(
        "Selected alignment: "
        + q["alignment"]
        + ". Same backend geometry is used by the current viewer and calculation."
    )
    p(
        "Supplemental profile: "
        + label(q["source_profile"])
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
    if same is not None:
        p("Same physical connection - ASCE component mapping", "Heading2")
        p(
            "The actual R3 bolt centers and thicknesses are used for every fresh ASCE component "
            "calculation below. No result from the different native BRACE example is copied."
        )
        for item in same["assumptions"]:
            p(item)
        conditions = same["materials"]["conditions"]
        p(
            "ASCE current project conditions: design temperature "
            + conditions["maximum_f"]
            + " F; moisture "
            + label(conditions["moisture"])
            + "; chemical "
            + label(conditions["chemical"])
            + "; load classification "
            + label(conditions["time_category"])
            + "."
        )
        p(
            "ASCE hardware selection: "
            + str(same["materials"]["fastener"].get("display_name", "User-selected hardware"))
        )
        for adapter in same["materials"]["resolved_materials"]:
            p("ASCE " + adapter["original"]["display_name"] + "; " + adapter["original"]["id"])
            for ledger in adapter["ledgers"]:
                if ledger["property_id"] in ("bearing_strength_L", "bearing_strength_T"):
                    p(
                        label(ledger["property_id"])
                        + ": original "
                        + str(ledger["original"])
                        + "; adjusted "
                        + str(ledger["adjusted_candidate"])
                        + " "
                        + ledger["unit"]
                        + "; CM="
                        + str(ledger["cm"])
                        + ", CT="
                        + str(ledger["ct"])
                        + ", CCH="
                        + str(ledger["cch"])
                        + "."
                    )
        for case in same["cases"]:
            p(
                "ASCE LRFD case "
                + case["case_id"]
                + "; row pitch "
                + utilization(case["row_pitch_in"], technical=technical)
                + " in; C_delta="
                + utilization(case["c_delta"], technical=technical)
                + "."
            )
            table(
                [["Current ASCE component", "Demand / resistance (kip)"]]
                + [
                    [
                        label(x["mechanism"]),
                        format(Decimal(x["demand_kip"]), ".4f")
                        + " / "
                        + format(Decimal(x["resistance_kip"]), ".4f"),
                    ]
                    for x in case["checks"]
                ],
                [330, 180],
            )
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
                label(r["mechanism"]) + " / " + label(r["evidence_scope"]),
                utilization(r["ratio"], technical=technical) + " / " + r["outcome"],
            ]
            for r in a["comparisons"]
        ],
        [115, 270, 125],
    )
    for governing_label, key in [
        ("Governing LRFD", "governing_lrfd"),
        ("Governing ASD", "governing_asd"),
    ]:
        row = a[key]
        p(
            governing_label + ": NOT EVALUATED"
            if row is None
            else governing_label
            + ": "
            + label(row["mechanism"])
            + " / "
            + row["case_id"]
            + " / UR "
            + utilization(row["ratio"], technical=technical)
        )
        if row is not None:
            if technical:
                p("Governing equation: " + row["equation"])
                p("Current calculation trace: " + row["resistance_trace"])
            else:
                p(
                    "Exact governing substitutions and intermediate values are retained "
                    "in Technical Audit and the current calculation JSON."
                )
    maximum = record.get("numerical_governing")
    if maximum is not None:
        p(
            "Maximum evaluated utilization: "
            + utilization(maximum["ratio"], technical=technical)
            + " / "
            + maximum["basis"]
            + " / "
            + maximum["case_id"]
            + " / "
            + label(maximum["mechanism"])
            + ". Separate bases are not combined into a resistance."
        )
    p("Supplied independent action sets", "Heading2")
    for basis in ["lrfd", "asd"]:
        for case in record["actions"][basis]:
            if same is not None and not technical:
                p(basis.upper() + " " + case["case_id"] + "; frame " + label(case["frame"]))
                p(
                    "Reference (x, y, z): "
                    + ", ".join(
                        format(Decimal(x["magnitude"]), ".6g") + " " + x["unit"]
                        for x in case["reference"]
                    )
                    + ". Actions in that frame: "
                    + "; ".join(
                        name + " = " + format(Decimal(x["magnitude"]), ".6g") + " " + x["unit"]
                        for name, x in zip(
                            ("Fx / P", "Fy / sketch V", "Fz", "Mx", "My", "Mz"),
                            case["components"],
                            strict=True,
                        )
                    )
                    + ". Exact inputs are retained in Technical Audit and JSON."
                )
                continue
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
            + utilization(current["vertical_pitch_in"], technical=technical or same is None)
            + " in; transverse LTV "
            + utilization(current["transverse_ltv_in"], technical=technical or same is None)
            + " in; longitudinal projection "
            + utilization(current["longitudinal_stagger_in"], technical=technical or same is None)
            + " in. Candidate cuts are not adopted fracture paths."
        )
        story.append(
            Table(
                [[path_drawing(current, "BRACE"), path_drawing(current, "COLUMN")]],
                colWidths=[255, 255],
            )
        )
    p("Detailing and coverage limitations", "Heading2")
    for mechanism in record.get("physical_mechanisms", []):
        p(mechanism["mechanism"], "Heading3")
        p(mechanism["evidence"])
        p("Remaining evidence: " + mechanism["remaining_evidence"])
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
        if same is not None:
            p("Same-connection ASCE exact technical audit", "Heading1")
            p("Contract: " + same["contract"] + "; geometry digest " + same["geometry_digest"])
            p("Actual shared centers (in): " + str(same["physical_centers_in"]))
            p(
                "Original declared LRFD cases before coordinate transforms: "
                + str(same["declared_lrfd_cases"])
            )
            p("Complete selected source records: " + str(same["materials"]))
            for case in same["cases"]:
                p("Independent LRFD combination " + case["case_id"], "Heading2")
                for key, value in case.items():
                    if key != "checks":
                        p(key + ": " + str(value))
                for check in case["checks"]:
                    p(check["mechanism"], "Heading3")
                    p(check)
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
