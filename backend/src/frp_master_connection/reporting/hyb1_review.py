"""Separate HYB1 internal report/capture boundary; original Engineer Reports untouched."""

from __future__ import annotations

import io
import json
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from html import escape
from typing import Any, cast

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Paragraph, SimpleDocTemplate, Spacer

from frp_master_connection.application.hyb1_contract import ActionBasis, PairedActions
from frp_master_connection.application.hyb1_mapping import direct_mappings
from frp_master_connection.application.hyb1_review import ComparisonRow, HybridReview, NativeCapture
from frp_master_connection.calculation.rhm_reference import WORKBOOK_SHA256
from frp_master_connection.calculation.rhm_workbook_case import WorkbookCase
from frp_master_connection.reporting.snapshot import SnapshotSigner

TITLE = "ASCE-based LRFD checks with supplemental RHM ASD candidate checks"


def canonical_record(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def request_digest(request: object) -> str:
    return sha256(canonical_record(request)).hexdigest()


def capture_signed_native(
    signer: SnapshotSigner,
    token: str,
    actions: PairedActions,
    case_id: str,
) -> NativeCapture:
    """Verify server snapshot/account; keep a private immutable copy without exporting its handle.

    Both geometry/material revisions conservatively bind the entire unchanged request.
    The review caller must bind the full original action case; no basis conversion occurs here.
    """
    snapshot = signer.verify(token, account_id=actions.identity.account)
    digest = request_digest(snapshot.request)
    if actions.identity.geometry != digest or actions.identity.material != digest:
        raise ValueError("Native request does not match the current geometry/material identity.")
    case = next((case for case in actions.lrfd if case.case_id == case_id), None)
    if case is None:
        raise ValueError("Native calculation requires its original LRFD combination identity.")
    if snapshot.input_provenance.get("hyb1_lrfd_action_digest") != case.digest:
        raise ValueError(
            "Verified native capture must seal the independently resolved original action case."
        )
    decision = snapshot.result.get("final_decision")
    if snapshot.kind != "design" or not isinstance(decision, dict):
        raise ValueError("A native Direct calculation snapshot with its F9 decision is required.")
    result_bytes = canonical_record(snapshot.result)
    rows = tuple(
        ComparisonRow(
            row["check_id"],
            case_id,
            case.digest,
            ActionBasis.LRFD,
            None if row["utilization"] is None else Decimal(row["utilization"]),
            {
                "CAPACITY_PASS": "PASS",
                "CAPACITY_FAIL": "FAIL",
                "COVERED_BY_QUALIFICATION": "NOT_EVALUATED",
            }.get(row["outcome"], row["outcome"]),
            "UNCHANGED_NATIVE_ASCE; see original signed calculation",
            json.dumps(
                {"demand": row["demand"], "design_resistance": row["design_resistance"]},
                sort_keys=True,
            ),
            "UNCHANGED_NATIVE",
            "UNCHANGED_NATIVE_ASCE",
            row["reason"],
            row["outcome"],
        )
        for row in decision["schedule"]
    )
    return NativeCapture(
        actions.identity,
        actions.digest,
        result_bytes,
        sha256(result_bytes).hexdigest(),
        rows,
        decision["final_status"],
        "VERIFIED_INTERNAL_SNAPSHOT:" + snapshot.digest,
        tuple(
            str(decision.get(key, "NOT_REPORTED"))
            for key in (
                "qualification_scope_state",
                "qualification_coverage_state",
                "qualification_capacity_state",
            )
        ),
    )


def review_record(review: HybridReview, actions: PairedActions) -> dict[str, Any]:
    if review.identity != actions.identity or review.paired_digest != actions.digest:
        raise ValueError("Review output cannot mix a result with different current inputs.")

    def encode(value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError("Unsupported HYB1 record value.")

    # Native payload and reusable handles are excluded; all executed native comparisons remain.
    data: dict[str, Any] = {
        "title": TITLE,
        "review": asdict(review),
        "actions": asdict(actions),
        "mappings": [asdict(row) for row in direct_mappings(review.identity.alignment)],
    }
    data["review"]["identity"]["account"] = "REDACTED_ACCOUNT_BOUND"
    data["actions"]["identity"]["account"] = "REDACTED_ACCOUNT_BOUND"
    return cast(dict[str, Any], json.loads(json.dumps(data, default=encode)))


def render_hyb1_review(
    review: HybridReview,
    actions: PairedActions,
    *,
    workbooks: tuple[WorkbookCase, ...] = (),
) -> bytes:
    """Render immutable executed records; never evaluate engineering in a PDF shim."""
    record = review_record(review, actions)
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    story: list[Any] = []

    def paragraph(text: str, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(text), styles[style]))
        story.append(Spacer(1, 5))

    paragraph(TITLE, "Title")
    paragraph("HYB1 INACTIVE REVIEW CANDIDATE - OWNER ENGINEERING REVIEW PENDING", "Heading2")
    paragraph(
        f"Evidence: {review.evidence_scope}. Native F9: {review.native_status}, unchanged. "
        f"Numerical comparisons: {review.numerical_outcome}; current: {review.current}. "
        f"Case sets complete: {review.case_sets_complete}; analytical candidate coverage: "
        f"{review.analytical_candidate_complete}."
    )
    paragraph(
        "Every method keeps its own LRFD design or ASD allowable basis. The index is a "
        "maximum of method-specific check ratios, NOT a mixed connection capacity. "
        "Synthetic completeness is test-only. No actual qualified GREEN, method adoption "
        "or Section 2.3.2/C13 acceptance is installed."
    )
    paragraph(
        f"Basis adoption: {review.basis_adoption}; qualification: {review.qualification}; "
        f"owner acceptance: {review.owner_acceptance}; "
        f"public activation: {review.public_activation}."
    )
    paragraph("Physical and calculation binding", "Heading2")
    for key, value in record["review"]["identity"].items():
        paragraph(key + ": " + str(value))
    paragraph("Paired action digest: " + review.paired_digest)
    paragraph("Native payload SHA256: " + review.native_payload_sha256)
    paragraph("Native provenance: " + review.native_provenance)
    paragraph("Retained actions and combination manifest", "Heading2")
    paragraph(json.dumps(record["actions"]["manifest"], sort_keys=True))
    paragraph(
        "Explicit supplied combinations; generation/code completeness not independently verified. "
        "Absent ASD is incomplete; unknown components remain unknown. No LRFD/1.6 inference."
    )
    for basis, cases in (("LRFD", actions.lrfd), ("ASD", actions.asd)):
        if not cases:
            paragraph(basis + ": NO SUPPLIED CASES - NOT EVALUATED")
        for case in cases:
            paragraph(
                f"{basis}: {case.case_id}; source={case.source_id}; "
                f"scenario={case.scenario_family}; "
                f"frame={case.frame}; reference=" + repr(case.reference)
            )
            paragraph("Fx,Fy,Fz,Mx,My,Mz = " + repr(case.components))
    paragraph("Executed comparisons - every basis and combination", "Heading2")
    for original in actions.transport_trace:
        paragraph(
            f"Original action before reference transport: {original.case_id}; "
            f"frame={original.frame}; P={original.reference}; F/M={original.components}"
        )
    if actions.transport_trace:
        paragraph("Current case retains M_G=M_P+(P-G) cross F; no transported moment was erased.")
    for row in review.rows:
        paragraph(f"{row.mechanism} / {row.basis} / {row.case_id}", "Heading3")
        paragraph(
            f"{row.outcome}; ratio={row.ratio}; mapping={row.mapping}; "
            f"evidence={row.evidence_scope}"
        )
        paragraph(row.equation + "; " + row.resistance_trace)
        if row.na_reason:
            paragraph("Applicability/source: " + row.na_reason)
        if row.native_outcome:
            paragraph("Original native outcome (unchanged): " + row.native_outcome)
    paragraph("Physical coverage and independent method questions", "Heading2")
    paragraph("Uncovered mandatory mechanisms: " + ", ".join(review.uncovered))
    for mapping in record["mappings"]:
        paragraph(mapping["native_id"] + " / " + mapping["disposition"], "Heading3")
        for key, value in mapping.items():
            paragraph(key + ": " + str(value))
    for workbook in workbooks:
        paragraph("Workbook technical audit - " + workbook.stream.value, "Heading2")
        paragraph("Original workbook SHA256: " + WORKBOOK_SHA256)
        paragraph(
            f"Column summary: {workbook.column_summary}; source={workbook.summary_cell}; "
            f"storm multiplier={workbook.storm_multiplier}"
        )
        paragraph("Shared operands and factor ledger - complete cell-level audit", "Heading3")
        for operand in workbook.comparisons[0].operands:
            paragraph(
                f"{operand.name}={operand.quantity.magnitude} {operand.quantity.unit}; "
                f"{operand.source_cell}; {operand.meaning}"
            )
        for comparison in workbook.comparisons:
            paragraph(comparison.method_id + " - " + comparison.equation, "Heading3")
            paragraph("Cells: " + ", ".join(comparison.cells))
            paragraph(
                "Capacities: "
                + repr(comparison.capacities)
                + "; directional ratios="
                + repr(comparison.components)
                + "; complete ratio="
                + str(comparison.utilization)
            )
            paragraph("Assumptions: " + "; ".join(comparison.assumptions))
        for optional in workbook.optional:
            paragraph(f"Optional {optional.component_id}: {optional.state}; {optional.reason}")
        paragraph("Historical discrepancies: " + "; ".join(workbook.discrepancies))

    def footer(canvas: Canvas, _: BaseDocTemplate) -> None:
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(567, 20, f"HYB1 inactive review - Page {canvas.getPageNumber()}")

    SimpleDocTemplate(
        output,
        pagesize=(8.5 * inch, 11 * inch),
        rightMargin=45,
        leftMargin=45,
        topMargin=42,
        bottomMargin=42,
        title=TITLE,
        author="HYB1 internal review",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
