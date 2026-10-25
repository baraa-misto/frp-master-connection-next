"""Separate inactive review presentation axes; no public F8/F9 status replacement."""

from dataclasses import dataclass

from .hyb1_review import HybridReview


def mechanism_name(key: str) -> str:
    if key.startswith("BOLT_SHEAR"):
        return "Row " + ("1" if "B_R1" in key else "2") + " bolt shear"
    if key.startswith("PIN_BEARING"):
        return (
            ("Angle" if "layer-A" in key else "Supporting W")
            + " row "
            + ("1" if "B_R1" in key else "2")
            + " pin bearing"
        )
    if key.startswith("FIRST_ROW"):
        return ("Angle" if "layer-A" in key else "Supporting W") + " first-row net tension"
    if key.startswith("INTERROW"):
        return ("Angle" if "layer-A" in key else "Supporting W") + " inter-row shear-out"
    if key.startswith("BLOCK_SHEAR"):
        return (
            ("Angle" if "layer-A" in key else "Supporting W")
            + (" right" if "RIGHT" in key else " left")
            + " block-shear release"
        )
    return {
        "ANGLE_HEEL_3D": "Angle heel (3D)",
        "W_FLANGE_WEB_JUNCTION_3D": "Supporting W flange/web junction (3D)",
        "OUT_OF_PLANE_CONTACT_PRYING": "Out-of-plane contact and prying",
    }.get(key, key.replace("_", " "))


@dataclass(frozen=True, slots=True)
class ReviewPresentation:
    calculated_heading: str
    calculated_tone: str
    coverage_heading: str
    omissions: tuple[str, ...]
    executive_limit: str
    method_notes: tuple[str, ...]
    qualification: str
    report_permitted: bool
    reference_heading: str = "Reference calculations - not an adopted design"
    qualified_complete: bool = False
    failure_details: tuple[str, ...] = ()
    uncovered_count: int = 0
    reference_streams: tuple[str, ...] = ()


def present_review(review: HybridReview) -> ReviewPresentation:
    """Keep material omissions adjacent to scoped PASS/FAIL."""
    if not review.current:
        return ReviewPresentation(
            "Results are stale - recalculate with current inputs",
            "neutral",
            "Coverage not established",
            tuple(mechanism_name(k) for k in review.uncovered),
            "Complete connection verification is not established: current calculation required.",
            ("Prior results and utilization are unavailable as current design evidence.",),
            review.qualification,
            False,
            uncovered_count=len(review.uncovered),
        )
    reference_only = (
        review.numerical_outcome == "NOT_EVALUATED" and review.reference_outcome != "NOT_EVALUATED"
    )
    heading, tone = {
        "PASS": ("Evaluated checks: PASS", "green"),
        "FAIL": ("Evaluated checks: FAIL", "red"),
        "NOT_EVALUATED": ("No structural checks evaluated", "neutral"),
    }[review.numerical_outcome]
    if reference_only:
        heading = "Reference calculations - not an adopted design"
    coverage = (
        "Coverage not established"
        if reference_only
        else "Required analytical coverage: "
        + ("COMPLETE" if review.analytical_candidate_complete else "PARTIAL")
    )
    omissions = tuple(dict.fromkeys(mechanism_name(key) for key in review.uncovered))
    pending = (
        "; ".join(omissions) if omissions else "method adoption and Section 2.3.2 qualification"
    )
    notes: tuple[str, ...] = (
        "Method review: supplemental ASD source comparisons remain reference calculations.",
        "Missing evidence: Section 2.3.2 whole-connection qualification remains unresolved.",
        (
            "Software acceptance: C13 and owner acceptance remain open. Method "
            "developer/reviewer owns method decisions."
        ),
    )
    if not review.case_sets_complete:
        notes += (
            (
                "Missing input: complete independently supplied ASD/LRFD action "
                "sets. Available valid checks remain executable."
            ),
        )
    failure_details: tuple[str, ...] = ()
    if review.numerical_outcome == "FAIL":
        failure_details = tuple(
            f"{row.basis} / {row.case_id} / {mechanism_name(row.mechanism)}: "
            f"utilization={row.ratio}; {row.resistance_trace}"
            for row in (review.governing_lrfd, review.governing_asd)
            if row is not None and row.outcome == "FAIL"
        ) or (
            (
                "Native ASCE failure retained; governing numerical row is "
                "unavailable in the captured schedule. See the original signed "
                "native result."
            ),
        )
    return ReviewPresentation(
        heading,
        tone,
        coverage,
        omissions,
        "Complete connection verification is not established: " + pending + ".",
        notes + review.limitations,
        review.qualification,
        True,
        failure_details=failure_details,
        uncovered_count=len(review.uncovered),
        reference_streams=tuple(
            dict.fromkeys(row.reference_stream for row in review.rows if row.reference_stream)
        ),
    )
