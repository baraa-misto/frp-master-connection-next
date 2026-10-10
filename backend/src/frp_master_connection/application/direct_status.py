"""Direct F9 status reduction over authoritative results; no resistance equations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from frp_master_connection.application.direct_qualification_matching import COVERED_RESPONSES

WHOLE_CONNECTION = "DIRECT_WHOLE_CONNECTION_SECTION_2_3_2_QUALIFICATION"
Category = Literal[
    "ANALYTICALLY_EVALUATED",
    "QUALIFICATION_COVERED",
    "QUALIFICATION_CAPACITY_EVALUATED",
    "NOT_APPLICABLE",
    "REQUIRED_UNRESOLVED",
    "NEUTRAL_INFORMATION",
]


@dataclass(frozen=True, slots=True)
class RequiredCheck:
    identity: str
    label: str
    category: Category
    outcome: str = "NOT_EVALUATED"
    utilization: Decimal | None = None
    demand: object = None
    resistance: object = None
    reason: str = ""
    source_backed: bool = True


@dataclass(frozen=True, slots=True)
class DirectDecisionInput:
    snapshot_digest: str
    checks: tuple[RequiredCheck, ...]
    qualification: dict[str, Any]
    qualification_authority_valid: bool
    gravity_applicable: bool
    geometry_valid: bool
    current: bool = True
    stale: bool = False
    input_error: bool = False
    additional_gates: tuple[str, ...] = ()
    authoritative_failure: str | None = None


def decide_direct_status(data: DirectDecisionInput) -> dict[str, Any]:
    """Pure reducer. Callers supply backend authority; this is not an API input."""
    q = data.qualification
    complete_coverage = set(COVERED_RESPONSES) <= set(q.get("covered_response_ids", []))
    eligible = (
        data.qualification_authority_valid
        and not q.get("synthetic", False)
        and q.get("record_state") == "AVAILABLE_FOR_MATCH"
        and q.get("statistics_state") == "VALID"
        and q.get("scope_match_state") == "MATCHED"
        and q.get("coverage_state") == "COVERED_BY_QUALIFICATION"
        and complete_coverage
        and not q.get("mismatch_reasons")
        and q.get("capacity_state") in {"CAPACITY_PASS", "CAPACITY_FAIL"}
    )
    capacity_state = q.get("capacity_state", "UNEVALUATED") if eligible else "UNEVALUATED"
    gravity = q.get("gravity_eq_2_2_state", "UNAVAILABLE")
    qualification_closed = (
        eligible
        and capacity_state == "CAPACITY_PASS"
        and (not data.gravity_applicable or gravity == "PASS")
    )
    schedule = []
    unresolved = list(data.additional_gates)
    if not data.snapshot_digest:
        unresolved.append("Current authenticated design snapshot required.")
    identities = [check.identity for check in data.checks]
    if len(identities) != len(set(identities)) or identities.count(WHOLE_CONNECTION) != 1:
        unresolved.append(
            "Complete unique required-check schedule and one qualification row required."
        )
    if not set(COVERED_RESPONSES) <= set(identities):
        unresolved.append("All five required qualification response identities must be scheduled.")
    for check in data.checks:
        category, outcome, reason = check.category, check.outcome, check.reason
        if check.identity in COVERED_RESPONSES and eligible:
            category, outcome, reason = (
                "QUALIFICATION_COVERED",
                "COVERED_BY_QUALIFICATION",
                "Covered by the approved whole-connection qualification; no component capacity.",
            )
        elif check.identity == WHOLE_CONNECTION and eligible:
            category, outcome = "QUALIFICATION_CAPACITY_EVALUATED", capacity_state
            reason = "One whole-connection strength comparison; gravity criterion remains separate."
        elif category == "NOT_APPLICABLE" and not check.source_backed:
            category, reason = "REQUIRED_UNRESOLVED", "Source-backed N/A disposition required."
        elif category == "NOT_APPLICABLE":
            outcome = "NOT_APPLICABLE"
        if category == "ANALYTICALLY_EVALUATED" and (
            outcome not in {"PASS", "FAIL"}
            or check.utilization is None
            or not check.utilization.is_finite()
            or check.utilization < 0
            or not check.source_backed
        ):
            category, reason = (
                "REQUIRED_UNRESOLVED",
                check.label + ": analytical result authority incomplete.",
            )
        if category == "REQUIRED_UNRESOLVED":
            unresolved.append(
                reason or check.label + ": required authoritative result unavailable."
            )
        schedule.append(
            {
                "check_id": check.identity,
                "label": check.label,
                "category": category,
                "outcome": outcome,
                "reason": reason,
                "demand": check.demand
                if category == "ANALYTICALLY_EVALUATED"
                else q.get("Ru")
                if category == "QUALIFICATION_CAPACITY_EVALUATED"
                else None,
                "design_resistance": check.resistance
                if category == "ANALYTICALLY_EVALUATED"
                else q.get("Rd_q")
                if category == "QUALIFICATION_CAPACITY_EVALUATED"
                else None,
                "utilization": str(check.utilization)
                if category == "ANALYTICALLY_EVALUATED" and check.utilization is not None
                else q.get("utilization")
                if category == "QUALIFICATION_CAPACITY_EVALUATED"
                else None,
                "whole_connection_reference": WHOLE_CONNECTION
                if category == "QUALIFICATION_COVERED"
                else None,
            }
        )
    if not eligible:
        unresolved.extend(
            q.get("mismatch_reasons")
            or ["No approved Section 2.3.2 qualification record matches this Direct connection."]
        )
    if eligible and data.gravity_applicable and gravity != "PASS":
        unresolved.append(
            "Applicable Eq. 2-2 requires known approved D/L and strictly greater strength."
        )
    evaluated_ids = {r["check_id"] for r in schedule if r["category"] == "ANALYTICALLY_EVALUATED"}
    analytical = [c for c in data.checks if c.identity in evaluated_ids]
    failed = [
        c
        for c in analytical
        if c.source_backed
        and c.utilization is not None
        and (c.outcome == "FAIL" or c.utilization > 1)
    ]
    critical = max(
        (c for c in analytical if c.utilization is not None),
        key=lambda c: c.utilization or Decimal(0),
        default=None,
    )
    governing = critical.identity if critical else None
    governing_label = critical.label if critical else "No analytical result"
    status, reason = "YELLOW", "QUALIFICATION REQUIRED"
    if data.stale or not data.current:
        status, reason = "GRAY", "STALE — RUN DESIGN CHECK" if data.stale else "NOT CALCULATED"
    elif data.input_error or not data.geometry_valid:
        status, reason = "GRAY", "GEOMETRY INVALID / INPUT NEEDED"
    elif failed or data.authoritative_failure:
        status, reason = "RED", "NUMERICAL DESIGN FAIL"
        if failed:
            failure = max(failed, key=lambda c: c.utilization or Decimal(0))
            governing, governing_label = failure.identity, failure.label
        else:
            governing, governing_label = "PROJECT_MATERIAL_LIMIT", str(data.authoritative_failure)
    elif eligible and (
        capacity_state == "CAPACITY_FAIL" or (data.gravity_applicable and gravity == "NOT_PASS")
    ):
        status, reason = "RED", "QUALIFIED CONNECTION STRENGTH INSUFFICIENT"
        governing, governing_label = WHOLE_CONNECTION, "Whole-connection qualification capacity"
    elif qualification_closed and not unresolved and analytical:
        status, reason = "GREEN", "DESIGN PASS"
    else:
        governing, governing_label = WHOLE_CONNECTION, "Approved matching connection qualification"
        if q.get("record_digest") is not None:
            reason = "MATCHING QUALIFICATION REQUIRED"
    counts = {
        category: sum(row["category"] == category for row in schedule)
        for category in (
            "ANALYTICALLY_EVALUATED",
            "QUALIFICATION_COVERED",
            "QUALIFICATION_CAPACITY_EVALUATED",
            "NOT_APPLICABLE",
            "REQUIRED_UNRESOLVED",
            "NEUTRAL_INFORMATION",
        )
    }
    return {
        "contract": "DIRECT-STATUS-F9",
        "final_status": status,
        "final_status_reason": reason,
        "current_snapshot_digest": data.snapshot_digest,
        "analytical_check_summary": {
            "evaluated": len(analytical),
            "failed": len(failed),
            "counts": counts,
            "highest_utilization": None if critical is None else str(critical.utilization),
            "highest_analytical_check": None if critical is None else critical.identity,
            "numerical_outcome": "FAIL" if failed else "PASS" if analytical else "NOT_EVALUATED",
        },
        "qualification_record_identity": {
            "record_id": q.get("selected_record_id"),
            "revision": q.get("record_revision"),
            "digest": q.get("record_digest"),
            "evaluation_digest": q.get("evaluation_digest"),
            "laboratory": q.get("laboratory"),
            "rdp_approval": q.get("rdp_approval"),
        },
        "qualification_scope_state": q.get("scope_match_state", "UNEVALUATED"),
        "qualification_coverage_state": q.get("coverage_state", "QUALIFICATION_COVERAGE_MISSING"),
        "qualification_capacity_state": capacity_state,
        "required_strength": q.get("Ru"),
        "design_strength": q.get("Rd_q") if eligible else None,
        "qualification_utilization": q.get("utilization") if eligible else None,
        "governing_check_or_gate": governing,
        "governing_label": governing_label,
        "unresolved_requirements": list(dict.fromkeys(unresolved)),
        "staleness_source_validity": {
            "current": data.current and not data.stale,
            "geometry_valid": data.geometry_valid,
            "qualification_authority_valid": data.qualification_authority_valid,
            "synthetic": bool(q.get("synthetic", False)),
        },
        "schedule": schedule,
        "decision_trace": {
            "precedence": [
                "STALE_OR_INPUT",
                "ANALYTICAL_FAIL",
                "APPLICABLE_QUALIFICATION_FAIL",
                "ALL_REQUIREMENTS_PASS",
                "INCOMPLETE",
            ],
            "qualification_eligible": eligible,
            "complete_response_coverage": complete_coverage,
            "gravity_applicable": data.gravity_applicable,
            "gravity_state": gravity,
            "qualification_closed": qualification_closed,
            "additional_gates": list(data.additional_gates),
        },
    }
