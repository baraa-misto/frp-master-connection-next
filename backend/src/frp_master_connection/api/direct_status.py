"""Translate the current Direct native schedule and private F8 evidence once."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application.direct_qualification_matching import COVERED_RESPONSES
from frp_master_connection.application.direct_qualification_records import content_digest
from frp_master_connection.application.direct_status import (
    WHOLE_CONNECTION,
    DirectDecisionInput,
    RequiredCheck,
    decide_direct_status,
)


def check_label(identity: str) -> str:
    names = {
        "BOLT_SHEAR": "Bolt shear",
        "PIN_BEARING": "FRP pin bearing",
        "INTERROW": "Inter-row shear-out",
        "FIRST_ROW": "First-row net tension",
        "BLOCK_SHEAR": "Block shear",
        "MATERIAL_SOURCE_REVIEW": "Material basis information",
    }
    if identity == WHOLE_CONNECTION:
        return "Whole-connection Section 2.3.2 qualification"
    if identity == "BLOCK_SHEAR:layer-A:BLOCK_L_RIGHT_ROW_1_BOLT_LINE_1":
        return "Block shear — Angle heel side"
    parts = identity.split(":")
    member = "Angle" if "layer-A" in parts else "Supporting W" if "layer-B" in parts else ""
    bolt = next(
        (p.replace("B_R", "row ").replace("_L", ", bolt ") for p in parts if p.startswith("B_R")),
        "",
    )
    return " — ".join(
        p for p in [names.get(parts[0], parts[0].replace("_", " ").title()), member, bolt] if p
    )


def snapshot_digest(legacy: dict[str, Any], result: dict[str, Any]) -> str:
    # The signed REPORT1 envelope retains this core identity and its own complete
    # envelope digest. Excluding the decision avoids a circular self-hash.
    return content_digest(
        {
            "request": legacy,
            "result": {
                k: v for k, v in result.items() if k not in {"final_decision", "report_snapshot"}
            },
        }
    )


def qualification_message(reason: str) -> str:
    """Normal-user message; the exact F8 reason remains in the audit trace."""
    messages = {
        "GEOMETRY MISMATCH": (
            "Qualification does not cover the selected geometry or brace orientation."
        ),
        "PRODUCT MISMATCH": "Qualification requires different FRP product or material identity.",
        "HARDWARE MISMATCH": "Qualification requires different bolt or installed hardware details.",
        "ACTION / ECCENTRICITY MISMATCH": (
            "Qualification loading protocol, actions or reference point do not cover this design."
        ),
        "SUPPORT / FIXTURE MISMATCH": (
            "Qualification fixture does not cover the selected supporting W conditions."
        ),
        "ENVIRONMENT MISMATCH": (
            "Qualification does not cover the actual project environment or conditions."
        ),
        "STATISTICS INVALID": "Qualification statistics require valid approved specimen evidence.",
        "APPROVED_AVAILABLE_RECORD_REQUIRED": (
            "Qualification evidence is unavailable, withdrawn or not approved."
        ),
        "QUALIFICATION_COVERAGE_MISSING": (
            "Qualification must cover every required response and physical 3D mode."
        ),
    }
    for prefix, message in messages.items():
        if reason.startswith(prefix):
            return message
    return (
        reason
        if not reason.isupper() and ":" not in reason
        else "Review source / qualification requirements with the engineering administrator."
    )


def _ratio(value: object) -> Decimal | None:
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number >= 0 else None
    except InvalidOperation:
        return None


def qualification_authority(q: dict[str, Any], audit: dict[str, Any]) -> bool:
    """Pure identity check over private F8 output; no record installation or approval."""
    record = audit.get("record") or {}
    return bool(
        bool(record)
        and record.get("digest") == q.get("record_digest")
        and record.get("activation_permitted") is True
        and record.get("evidence_origin") != "SYNTHETIC_QA"
        and record.get("synthetic") is False
        and record.get("status") == "AVAILABLE_FOR_MATCH"
        and record.get("withdrawn") is False
        and record.get("qualification_record_id") == q.get("selected_record_id")
        and record.get("revision") == q.get("record_revision")
        and audit.get("evaluation") == {k: v for k, v in q.items() if k != "evaluation_digest"}
        and content_digest(audit) == q.get("evaluation_digest")
    )


def attach_direct_status(
    result: dict[str, Any],
    legacy: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    if legacy.get("direct_finalization_contract_version") != "SHEAR01-DIRECT-F1":
        return result
    native = result["native_design"]
    preview = native["preview"]
    integration = native.get("automatic_group_mode_integration") or {}
    single = integration.get("direct_single_row_result") or {}
    analytical = {}
    history = {}
    for scenario in [
        *integration.get("scenario_results", []),
        *integration.get("direct_angle_block_results", []),
        single,
    ]:
        for check in [*scenario.get("supported_results", []), *scenario.get("checks", [])]:
            analytical[check["result_id"]] = check
        for row in scenario.get("history_results", []):
            history[row["result_id"]] = row
    required = single.get("required_check_ids", integration.get("required_check_ids", []))
    neutral = set(integration.get("not_required_check_ids", []))
    schedule = []
    for identity in required:
        check = analytical.get(identity)
        if check is not None and check.get("availability") == "CALCULATED":
            schedule.append(
                RequiredCheck(
                    identity,
                    check_label(identity),
                    "ANALYTICALLY_EVALUATED",
                    str(check["numerical_comparison"]),
                    _ratio(check.get("utilization")),
                    check.get("demand"),
                    check.get("design_resistance"),
                    source_backed=bool(check.get("source_locator"))
                    and check.get("geometry_status", preview.get("geometry_status")) == "VALID",
                )
            )
        elif identity in neutral and identity.startswith("MATERIAL_SOURCE_REVIEW:"):
            schedule.append(
                RequiredCheck(
                    identity,
                    check_label(identity),
                    "NEUTRAL_INFORMATION",
                    reason=(
                        "ASCE minimum shape material basis; actual tested product remains separate."
                    ),
                )
            )
        elif identity in neutral and identity in history:
            row = history[identity]
            schedule.append(
                RequiredCheck(
                    identity,
                    check_label(identity),
                    "NOT_APPLICABLE",
                    reason=str(row.get("reason", "")),
                    source_backed=row.get("availability") == "NOT_APPLICABLE"
                    and bool(row.get("reason")),
                )
            )
        else:
            reason = (
                "Section 2.3.2 whole-connection qualification coverage required"
                if identity in COVERED_RESPONSES
                else "Approved matching Section 2.3.2 qualification record required"
                if identity == WHOLE_CONNECTION
                else check_label(identity)
                + ": required method, source or applicability unresolved."
            )
            schedule.append(
                RequiredCheck(
                    identity,
                    check_label(identity),
                    "REQUIRED_UNRESOLVED",
                    reason=reason,
                )
            )
    q = result["qualification_evaluation"]
    audit = provenance.get("direct_qualification_audit") or {}
    authority = qualification_authority(q, audit)
    issues = tuple(str(issue) for issue in result.get("material_issues", []))
    decision = decide_direct_status(
        DirectDecisionInput(
            snapshot_digest(legacy, result),
            tuple(schedule),
            q,
            authority,
            audit.get("design_scope", {}).get("action_scope", {}).get("loading_type")
            == "GRAVITY_D_L",
            preview.get("geometry_status") == "VALID"
            and preview.get("plan_availability") == "READY",
            current=bool(result.get("design_check_performed")),
            additional_gates=issues,
            authoritative_failure="Applicable project material-temperature limit fails."
            if result.get("overall_status") == "FAIL"
            and not integration.get("failed_check_ids")
            and not single.get("failed_check_ids")
            else None,
        )
    )
    decision["decision_trace"]["native_unresolved_requirements"] = decision[
        "unresolved_requirements"
    ]
    decision["unresolved_requirements"] = list(
        dict.fromkeys(
            qualification_message(reason) for reason in decision["unresolved_requirements"]
        )
    )
    return {**result, "final_decision": decision}


def direct_status_snapshot_current(result: dict[str, Any], request: dict[str, Any]) -> bool:
    decision = result.get("final_decision")
    if decision is None:
        return True
    legacy = request.get("legacy_request", request)
    try:
        legacy = MultiRowConnectionRequestDTO.model_validate(legacy).model_dump(mode="json")
    except ValueError:
        return False
    return bool(
        decision.get("current_snapshot_digest") == snapshot_digest(legacy, result)
        and decision.get("qualification_record_identity", {}).get("evaluation_digest")
        == result.get("qualification_evaluation", {}).get("evaluation_digest")
    )


def input_direct_status(result: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Label a Direct input capture as GRAY; captured JSON grants no engineering authority."""
    draft = request.get("client_draft", request)
    if not isinstance(draft, dict):
        return result
    legacy = draft.get("legacy_request", draft)
    if (
        not isinstance(legacy, dict)
        or legacy.get("direct_finalization_contract_version") != "SHEAR01-DIRECT-F1"
    ):
        return result
    invalid = result.get("status") == "INPUT_VALIDATION_FAILED"
    decision = decide_direct_status(
        DirectDecisionInput(
            content_digest({"request": request, "result": result}),
            (),
            {},
            False,
            False,
            False,
            current=invalid,
            input_error=invalid,
        )
    )
    return {**result, "final_decision": decision}
