"""Print immutable HYB1 supplementary source records; no engineering in renderer."""

import io
import json
from dataclasses import asdict
from html import escape
from typing import Any

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Paragraph, SimpleDocTemplate, Spacer

from frp_master_connection.application.hyb1_contract import Alignment
from frp_master_connection.application.hyb1_mapping import clip_tee_reference_uses
from frp_master_connection.calculation.rhm_clip_tee_reference import ClipTeeWorkbookCase


def render_clip_tee_reference(case: ClipTeeWorkbookCase) -> bytes:
    """Reference supplements never replace or mutate any signed Direct snapshot."""
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    story: list[Any] = []

    def paragraph(text: str, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(text), styles[style]))
        story.append(Spacer(1, 5))

    paragraph("HYB1 supplementary Clip Tee workbook reference", "Title")
    paragraph("INACTIVE REFERENCE - OWNER ENGINEERING REVIEW PENDING", "Heading2")
    paragraph(
        f"Stream: {case.stream}; source: {case.source_id}; geometry: {case.geometry_identity}. "
        f"Workbook SHA256: {case.workbook_sha256}. Extraction ZIP SHA256: {case.extraction_sha256}."
    )
    paragraph(
        "This separate W8 brace-to-chord source uses a 316SS Clip Tee, selected reinforcement "
        "and separate six-bolt groups. It is not the actual Direct Angle-to-W connection. "
        "All comparisons are source-reference arithmetic. No actual coverage, adopted method, "
        "qualified GREEN, public Tee workspace or ASCE replacement is created."
    )
    paragraph(
        "Normal/sliding inputs are the original saved resolution caches scaled explicitly, "
        "not independently recomputed trigonometry or a general eccentric bolt distribution. "
        "Recomputed component ratios below are distinct from original cached output cells."
    )
    paragraph("Combined Tee flange correction", "Heading2")
    paragraph(
        f"Recomputed summary: {case.tee_flange.summary}; source: {case.tee_flange.summary_cell}; "
        f"summary outcome: {case.tee_flange.summary_outcome}. Complete combined ratio: "
        f"{case.tee_flange.comparison.utilization}."
    )
    paragraph(
        "Historical Summary C14 and E144/F144 use bending-only D142. Corrected-reference "
        "summary AND status use combined D144, retaining both bending and axial terms. "
        "Historical behavior is retained only in the labelled historical stream."
    )
    paragraph(
        f"M={case.tee_flange.moment}; S={case.tee_flange.section_modulus_in3} in3; "
        f"fb={case.tee_flange.bending_stress}; fa={case.tee_flange.axial_stress}."
    )
    paragraph("Reinforcement and web attachment applicability", "Heading2")
    paragraph(
        f"Reinforcement selected: {case.reinforcement_selected}; web attachment selected: "
        f"{case.web_attachment_selected}; state: {case.web_attachment_state}."
    )
    paragraph(
        "The unreinforced variant is freshly calculated without reinforcement moment or "
        "bearing credit. Inactive web-bolt source caches NA provide no receiving-web or "
        "junction coverage. Active attachment without established transfer stays incomplete. "
        "Tee stem checks have no corresponding Tee component in actual Direct geometry."
    )
    paragraph("Recomputed reference comparisons", "Heading2")
    for row in case.comparisons:
        paragraph(row.method_id, "Heading3")
        paragraph(
            f"{row.numerical_outcome}; ratio={row.utilization}; components={row.components}; "
            f"capacities={row.capacities}; basis={row.basis}; mapping={row.mapping}."
        )
        paragraph(row.equation + "; cells=" + repr(row.cells))
    paragraph("Proposed source uses - actual HYB1 mechanism identities", "Heading2")
    for alignment in Alignment:
        for mapping in clip_tee_reference_uses(alignment):
            paragraph(f"{alignment}: {mapping.native_id} / {mapping.disposition}", "Heading3")
            paragraph(json.dumps(asdict(mapping), sort_keys=True))
    paragraph("Technical audit - operands and original saved output cells", "Heading2")
    for operand in case.operands:
        paragraph(
            f"{operand.name}={operand.quantity}; cell={operand.source_cell}; {operand.meaning}"
        )
    paragraph("Original saved example caches (not outputs of a modified variant):")
    for cell, cache in case.original_saved_cache_cells:
        paragraph(cell + " = " + cache)
    paragraph("Assumptions: " + "; ".join(case.comparisons[0].assumptions))

    def footer(canvas: Canvas, _: BaseDocTemplate) -> None:
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(567, 20, f"HYB1 source supplement - Page {canvas.getPageNumber()}")

    SimpleDocTemplate(
        output,
        pagesize=(612, 792),
        rightMargin=45,
        leftMargin=45,
        topMargin=42,
        bottomMargin=42,
        title="HYB1 supplementary Clip Tee reference",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
