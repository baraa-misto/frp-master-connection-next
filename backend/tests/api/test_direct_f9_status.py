"""F9 precedence, real owner parity, source currency and nonactivation boundaries."""

from __future__ import annotations

import asyncio
import io
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any, Literal

import httpx
import pytest
from pypdf import PdfReader
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design
from tests.direct_f9_fixtures import authoritative_input

from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_qualification import compare_strength
from frp_master_connection.api.direct_status import (
    _ratio,
    attach_direct_status,
    check_label,
    direct_status_snapshot_current,
    input_direct_status,
    qualification_authority,
    qualification_message,
)
from frp_master_connection.application.direct_qualification_records import content_digest
from frp_master_connection.application.direct_status import WHOLE_CONNECTION, decide_direct_status
from frp_master_connection.reporting.direct_status import (
    coverage_rows,
    engineering_notation,
    executive_rows,
)
from frp_master_connection.reporting.pdf import (
    ReportOptions,
    _font_setup,
    _styles,
    render_report_pdf,
)
from frp_master_connection.reporting.snapshot import SnapshotSigner


@pytest.mark.parametrize(
    ("required", "expected"),
    [(".99999999999999", "GREEN"), ("1", "GREEN"), ("1.00000000000001", "RED")],
)
def test_general_strength_boundary_consumes_the_unchanged_f8_comparison(
    required: str, expected: str
) -> None:
    data = authoritative_input()
    evaluation = {
        **data.qualification,
        **compare_strength(Decimal(1), Decimal(required), None, False),
    }
    assert decide_direct_status(replace(data, qualification=evaluation))["final_status"] == expected


@pytest.mark.parametrize(
    ("strength", "expected"),
    [("1.19999999999999", "RED"), ("1.2", "RED"), ("1.20000000000001", "GREEN")],
)
def test_literal_gravity_boundary_consumes_known_d_l_without_decomposition(
    strength: str, expected: str
) -> None:
    from tests.direct_f8_fixtures import qa_context

    from frp_master_connection.api.schemas import QuantityDTO
    from frp_master_connection.calculation.quantities import Unit

    context = qa_context("PURE_QA_DECLARATION_ONLY").model_copy(
        update={
            "loading_type": "GRAVITY_D_L",
            "dead_load": QuantityDTO(value="1", unit=Unit.N),
            "live_load": QuantityDTO(value="0", unit=Unit.N),
        }
    )
    data = authoritative_input()
    evaluation = {
        **data.qualification,
        **compare_strength(Decimal(strength), Decimal(".5"), context, True),
    }
    assert (
        decide_direct_status(replace(data, qualification=evaluation, gravity_applicable=True))[
            "final_status"
        ]
        == expected
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("record_state", "WITHDRAWN"),
        ("record_state", "SUPERSEDED"),
        ("record_state", "NO_APPROVED_RECORD"),
        ("statistics_state", "INVALID"),
        ("scope_match_state", "MISMATCH"),
        ("coverage_state", "QUALIFICATION_COVERAGE_MISSING"),
        ("covered_response_ids", []),
        ("mismatch_reasons", ["Unsupported action history"]),
        ("synthetic", True),
        ("capacity_state", "UNEVALUATED"),
    ],
)
def test_missing_mismatched_incomplete_or_synthetic_evidence_never_closes(
    field: str,
    value: object,
) -> None:
    data = authoritative_input()
    q = {**data.qualification, field: value}
    result = decide_direct_status(replace(data, qualification=q))
    assert result["final_status"] == "YELLOW"
    assert result["qualification_capacity_state"] == "UNEVALUATED"
    assert result["analytical_check_summary"]["counts"]["REQUIRED_UNRESOLVED"] == 6


@pytest.mark.parametrize(
    ("state", "value", "expected"),
    [
        ("stale", True, "STALE"),
        ("current", False, "NOT CALCULATED"),
        ("geometry_valid", False, "GEOMETRY INVALID"),
        ("input_error", True, "INPUT NEEDED"),
    ],
)
def test_stale_or_invalid_input_is_gray_even_with_failures(
    state: str, value: bool, expected: str
) -> None:
    data = authoritative_input()
    checks = (replace(data.checks[0], utilization=Decimal("2"), outcome="FAIL"), *data.checks[1:])
    changed_fields: dict[str, Any] = {state: value}
    result = decide_direct_status(replace(data, checks=checks, **changed_fields))
    assert result["final_status"] == "GRAY"
    assert expected in result["final_status_reason"]


@pytest.mark.parametrize("authority", [True, False])
def test_actual_analytical_failure_precedes_qualification(authority: bool) -> None:
    data = authoritative_input()
    checks = (
        replace(data.checks[0], utilization=Decimal("1.0000000000000000001")),
        *data.checks[1:],
    )
    result = decide_direct_status(
        replace(data, checks=checks, qualification_authority_valid=authority)
    )
    assert result["final_status"] == "RED"
    assert result["final_status_reason"] == "NUMERICAL DESIGN FAIL"
    assert result["governing_check_or_gate"] == checks[0].identity


@pytest.mark.parametrize(
    ("capacity", "gravity", "applicable", "expected"),
    [
        ("CAPACITY_PASS", "PASS", False, "GREEN"),
        ("CAPACITY_FAIL", "PASS", False, "RED"),
        ("CAPACITY_PASS", "NOT_PASS", True, "RED"),
        ("CAPACITY_PASS", "UNAVAILABLE", True, "YELLOW"),
        ("CAPACITY_PASS", "NOT_PASS", False, "GREEN"),
    ],
)
def test_isolated_authoritative_strength_and_strict_gravity_states(
    capacity: str,
    gravity: str,
    applicable: bool,
    expected: str,
) -> None:
    data = authoritative_input()
    q = {**data.qualification, "capacity_state": capacity, "gravity_eq_2_2_state": gravity}
    result = decide_direct_status(replace(data, qualification=q, gravity_applicable=applicable))
    assert result["final_status"] == expected
    counts = result["analytical_check_summary"]["counts"]
    assert counts["QUALIFICATION_COVERED"] == 5
    assert counts["QUALIFICATION_CAPACITY_EVALUATED"] == 1
    assert counts["ANALYTICALLY_EVALUATED"] == 1
    assert counts["NOT_APPLICABLE"] == 1
    assert counts["NEUTRAL_INFORMATION"] == 1
    covered = [r for r in result["schedule"] if r["category"] == "QUALIFICATION_COVERED"]
    assert all(r["outcome"] == "COVERED_BY_QUALIFICATION" for r in covered)
    assert all(r["design_resistance"] is None and r["utilization"] is None for r in covered)
    assert all(r["whole_connection_reference"] == WHOLE_CONNECTION for r in covered)
    assert (
        next(r for r in result["schedule"] if r["check_id"] == "HEEL")["outcome"]
        == "NOT_APPLICABLE"
    )


@pytest.mark.parametrize(
    "case",
    [
        "authority",
        "snapshot",
        "missing_schedule",
        "duplicate",
        "no_analytical",
        "na_source",
        "extra_gate",
        "analytic_source",
        "analytic_missing",
        "analytic_unknown",
        "analytic_nonfinite",
        "analytic_negative",
    ],
)
def test_every_unproven_requirement_prevents_hypothetical_green(case: str) -> None:
    data = authoritative_input()
    if case == "authority":
        data = replace(data, qualification_authority_valid=False)
    elif case == "snapshot":
        data = replace(data, snapshot_digest="")
    elif case == "missing_schedule":
        data = replace(data, checks=data.checks[:1])
    elif case == "duplicate":
        data = replace(data, checks=(*data.checks, data.checks[0]))
    elif case == "no_analytical":
        data = replace(data, checks=data.checks[1:])
    elif case == "na_source":
        data = replace(
            data,
            checks=(*data.checks[:7], replace(data.checks[7], source_backed=False), data.checks[8]),
        )
    elif case == "extra_gate":
        data = replace(data, additional_gates=("Additional required axis-tension check",))
    else:
        changes: dict[str, dict[str, Any]] = {
            "analytic_source": {"source_backed": False},
            "analytic_missing": {"utilization": None},
            "analytic_unknown": {"outcome": "NOT_EVALUATED"},
            "analytic_nonfinite": {"utilization": Decimal("NaN")},
            "analytic_negative": {"utilization": Decimal("-1")},
        }
        change = changes[case]
        data = replace(data, checks=(replace(data.checks[0], **change), *data.checks[1:]))
    assert decide_direct_status(data)["final_status"] == "YELLOW"


def test_material_limit_failure_is_red_without_fabricating_a_check() -> None:
    result = decide_direct_status(
        replace(authoritative_input(), authoritative_failure="Applicable temperature limit fails")
    )
    assert result["final_status"] == "RED"
    assert result["governing_check_or_gate"] == "PROJECT_MATERIAL_LIMIT"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(".3", Decimal(".3")), (None, None), ("NaN", None), ("-1", None), ("Infinity", None)],
)
def test_native_utilization_requires_finite_nonnegative_decimal(
    value: object, expected: Decimal | None
) -> None:
    assert _ratio(value) == expected


@pytest.mark.parametrize(
    "identity",
    [
        WHOLE_CONNECTION,
        "BOLT_SHEAR:B_R2_L1",
        "PIN_BEARING:layer-B:B_R1_L1",
        "INTERROW:layer-A:BOLT_LINE_1",
        "EXTRA_RESPONSE",
    ],
)
def test_human_labels_keep_exact_ids_in_schedule_only(identity: str) -> None:
    label = check_label(identity)
    assert label
    assert "layer-" not in label
    assert "B_R" not in label


@pytest.mark.parametrize(
    "reason",
    [
        "GEOMETRY MISMATCH",
        "PRODUCT MISMATCH",
        "HARDWARE MISMATCH",
        "ACTION / ECCENTRICITY MISMATCH",
        "SUPPORT / FIXTURE MISMATCH",
        "ENVIRONMENT MISMATCH",
        "STATISTICS INVALID",
        "APPROVED_AVAILABLE_RECORD_REQUIRED",
        "QUALIFICATION_COVERAGE_MISSING",
        "UNKNOWN_INTERNAL_REQUIREMENT",
        "Missing actual project evidence",
    ],
)
def test_mismatch_messages_are_actionable_without_json_paths(reason: str) -> None:
    assert ":" not in qualification_message(
        reason + ":geometry_scope.row_count" if reason.isupper() else reason
    )


def test_private_authority_identity_is_pure_and_fail_closed() -> None:
    # Metadata only: no specimens, laboratory files, approved record or provider installation.
    record = {
        "digest": "D",
        "activation_permitted": True,
        "evidence_origin": "REAL_CONTROLLED_EVIDENCE",
        "synthetic": False,
        "status": "AVAILABLE_FOR_MATCH",
        "withdrawn": False,
        "qualification_record_id": "HYPOTHETICAL",
        "revision": 1,
    }
    q = {"record_digest": "D", "selected_record_id": "HYPOTHETICAL", "record_revision": 1}
    audit: dict[str, Any] = {"record": record, "evaluation": q.copy()}
    q["evaluation_digest"] = content_digest(audit)
    assert qualification_authority(q, audit)
    assert not qualification_authority(q, {})
    for field, value in [
        ("digest", "changed"),
        ("activation_permitted", False),
        ("evidence_origin", "SYNTHETIC_QA"),
        ("synthetic", True),
        ("status", "WITHDRAWN"),
        ("withdrawn", True),
        ("qualification_record_id", "wrong"),
        ("revision", 2),
    ]:
        changed = deepcopy(audit)
        changed["record"][field] = value
        assert not qualification_authority(q, changed)
    changed = deepcopy(audit)
    changed["evaluation"] = {}
    assert not qualification_authority(q, changed)
    changed = deepcopy(audit)
    changed["extra"] = "tampered"
    assert not qualification_authority(q, changed)


def test_actual_owner_decision_and_snapshot_binding_preserve_native_authority() -> None:
    body = f6_cases()["owner-135"]
    result = design(body)
    decision = result["final_decision"]
    assert decision["final_status"] == "YELLOW"
    assert decision["analytical_check_summary"]["counts"] == {
        "ANALYTICALLY_EVALUATED": 8,
        "QUALIFICATION_COVERED": 0,
        "QUALIFICATION_CAPACITY_EVALUATED": 0,
        "NOT_APPLICABLE": 1,
        "REQUIRED_UNRESOLVED": 6,
        "NEUTRAL_INFORMATION": 2,
    }
    assert direct_status_snapshot_current(result, body)
    assert direct_status_snapshot_current(result, body["legacy_request"])
    assert direct_status_snapshot_current({}, {})
    changed = deepcopy(result)
    changed["final_decision"]["qualification_record_identity"]["evaluation_digest"] = "wrong"
    assert not direct_status_snapshot_current(changed, body)
    changed = deepcopy(body)
    changed["legacy_request"]["row_count"] = 3
    assert not direct_status_snapshot_current(result, changed)
    assert not direct_status_snapshot_current(result, {"row_count": 0})
    assert attach_direct_status(result, {}, {}) is result


@pytest.mark.parametrize(
    "case", ["owner-135", "si-owner", "real-along-row-force", "single-row-failure"]
)
def test_native_supported_and_blocked_configurations_receive_current_decisions(case: str) -> None:
    if case == "single-row-failure":
        from tests.api.test_asce_shape_f5 import f5_body

        body = f5_body(row_count=1)
        body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
            "force"
        ]["y"] = "1.75"
        result = design(body)
        single = result["native_design"]["automatic_group_mode_integration"][
            "direct_single_row_result"
        ]
        evaluated = {
            row["check_id"]
            for row in result["final_decision"]["schedule"]
            if row["category"] == "ANALYTICALLY_EVALUATED"
        }
        assert all(
            row["result_id"] in evaluated
            for row in single["checks"]
            if row["availability"] == "CALCULATED"
        )
    else:
        result = design(f6_cases()[case])
    assert result["final_decision"]["final_status"] == (
        "GRAY"
        if case == "real-along-row-force"
        else "RED"
        if case == "single-row-failure"
        else "YELLOW"
    )


def test_actual_owner_engineer_pdf_uses_backend_status_and_native_precision() -> None:
    body = f6_cases()["owner-135"]
    result = design(body)
    signer = SnapshotSigner(b"DIRECT-F9-REPORT-IMMUTABILITY-TEST-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f9"
        ),
        account_id="f9",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions())
    pages = PdfReader(io.BytesIO(pdf)).pages
    text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
    assert "YELLOW — QUALIFICATION REQUIRED" in text
    assert "8 evaluated — PASS" in text
    assert "6 required checks/evidence items unresolved" in text
    assert "ASCE Eq. 8-14b" in text
    assert "0.7185" in text
    assert "0.718500000000" not in text
    assert "final status integration pending" not in text
    assert "ASCE_8_14B_DIRECT_PHYSICAL_L_PATH_RATIONAL" not in text
    assert "Catalog SHA-256" not in text
    assert len(pages) <= 11
    assert (snapshot.request, snapshot.result) == before


def test_report_status_helpers_render_hypothetical_categories_without_engineering() -> None:
    decision = decide_direct_status(authoritative_input())
    rows = coverage_rows(decision, [])
    assert any("COVERED BY QUALIFICATION" in value for _, value in rows)
    assert any("NOT APPLICABLE" in value for _, value in rows)
    assert executive_rows(decision, "SI")
    empty = decide_direct_status(replace(authoritative_input(), checks=()))
    assert any(value == "Not evaluated" for _, value in executive_rows(empty, "SI"))
    unresolved = decide_direct_status(
        replace(authoritative_input(), qualification_authority_valid=False)
    )
    assert coverage_rows(unresolved, [])
    _font_setup()
    paragraph = engineering_notation(
        "R_n = 0.718500000000 in²; A_nt = 1.2; plain 12", _styles()["body"]
    )
    assert "0.7185" in paragraph.text
    assert "<sub>n</sub>" in paragraph.text


def test_signed_currency_api_rejects_wrong_handles_drafts_mutation_and_client_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = f6_cases()["owner-135"]

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://testserver"
        ) as client:
            response = await client.post("/api/v1/frp-materials/multi-row/design-check", json=body)
            handle = response.headers["X-Report-Handle"]
            url = "/api/v1/reports/direct-decision-current"
            request = {"report_handle": handle}
            current = await client.post(url, json=request)
            assert current.status_code == 200
            assert current.json()["current"] is True
            assert "no-store" in current.headers["Cache-Control"]
            assert (
                await client.post(url, json={**request, "final_status": "GREEN"})
            ).status_code == 422
            assert (await client.post(url, json={"report_handle": "x" * 32})).status_code == 409
            draft = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "multi-row", "draft": {"final_status": "GREEN"}},
            )
            assert (
                await client.post(url, json={"report_handle": draft.json()["report_handle"]})
            ).status_code == 409
            monkeypatch.setattr(
                "frp_master_connection.reporting.routes.direct_status_snapshot_current",
                lambda _result, _request: False,
            )
            assert (await client.post(url, json=request)).status_code == 409
            assert (await client.post("/api/v1/reports/export", json=request)).status_code == 409
            monkeypatch.setattr(
                "frp_master_connection.reporting.routes.direct_status_snapshot_current",
                lambda _result, _request: True,
            )
            monkeypatch.setattr(
                "frp_master_connection.reporting.routes.qualification_snapshot_current",
                lambda _result: False,
            )
            assert (await client.post(url, json=request)).status_code == 409

    asyncio.run(run())


@pytest.mark.parametrize("draft", [{"client_draft": []}, {"legacy_request": []}, {}])
def test_non_direct_or_non_object_drafts_receive_no_direct_authority(draft: dict[str, Any]) -> None:
    result = {"status": "INPUT_NOT_EVALUATED"}
    assert input_direct_status(result, draft) is result


@pytest.mark.parametrize("case", ["normal", "invalid", "malformed"])
def test_input_reports_remain_gray_and_preserve_complete_audit(case: str) -> None:
    body = f6_cases()["owner-135"]
    if case == "malformed":
        body["legacy_request"]["physical_connection"] = "Incomplete physical input"
        body["assignments"] = "Incomplete material input"
    request = {"client_draft": body}
    result = input_direct_status(
        {
            "status": "INPUT_VALIDATION_FAILED" if case == "invalid" else "INPUT_NOT_EVALUATED",
            "validation_issues": ["Choose valid project geometry"],
        },
        request,
    )
    assert result["final_decision"]["final_status"] == "GRAY"
    signer = SnapshotSigner(b"DIRECT-F9-INPUT-ONLY-IMMUTABILITY-TEST")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="input_only", request=request, result=result, account_id="f9"
        ),
        account_id="f9",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    modes: tuple[Literal["ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"], ...] = (
        "ENGINEER_REPORT",
        "FULL_TECHNICAL_AUDIT",
    )
    for mode in modes:
        pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
        assert "GRAY" in text
        assert "None evaluated" in text
        assert "No current validated engineering result" in text
        if mode == "FULL_TECHNICAL_AUDIT":
            assert "current_snapshot_digest" in "".join(text.split())
            assert "Choose valid project geometry" in text
    assert (snapshot.request, snapshot.result) == before


@pytest.mark.parametrize("injection", ["synthetic", "activation", "custom-result", "record-id"])
def test_empty_production_provider_cannot_be_approved_by_client_json(injection: str) -> None:
    from tests.direct_f8_fixtures import qa_context

    body = f6_cases()["owner-135"]
    if injection == "record-id":
        body["qualification_context"] = qa_context("CLIENT_CANNOT_APPROVE").model_dump(mode="json")
    else:
        body[
            {
                "synthetic": "synthetic",
                "activation": "activation_permitted",
                "custom-result": "final_decision",
            }[injection]
        ] = True

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://testserver"
        ) as client:
            response = await client.post("/api/v1/frp-materials/multi-row/design-check", json=body)
            if injection != "record-id":
                assert response.status_code == 422
            else:
                assert response.status_code == 200
                assert response.json()["final_decision"]["final_status"] == "YELLOW"
                assert (
                    response.json()["final_decision"]["staleness_source_validity"][
                        "qualification_authority_valid"
                    ]
                    is False
                )

    asyncio.run(run())


def test_legacy_and_concise_qualification_tables_preserve_evidence() -> None:
    from frp_master_connection.reporting.direct_qualification import qualification_summary_rows

    q: dict[str, Any] = {
        "record_digest": "hypothetical",
        "selected_record_id": "PURE_PRESENTATION_ONLY",
        "record_revision": 1,
        "laboratory": "QA only",
        "rdp_approval": "Unapproved QA",
        "statistics": {"accepted_n": 10, "Ro": None, "VR": ".1", "phi_p": ".2"},
        "Rd_q": None,
        "Ru": None,
        "scope_match_state": "MISMATCH",
        "coverage_state": "QUALIFICATION_COVERAGE_MISSING",
        "capacity_state": "UNEVALUATED",
        "utilization": None,
        "gravity_eq_2_2_state": "NOT_APPLICABLE",
        "covered_response_ids": [],
        "mismatch_reasons": ["QA mismatch"],
        "factor_trace": [
            {"factor": "Rn", "value": "100"},
            {"factor": "phi_p", "value": ".2"},
            {"factor": "lambda", "applied": ".6"},
        ],
    }
    assert ("Active qualification limits", "QA mismatch") in qualification_summary_rows(q, "SI")
    assert any(
        label == "Source / approval limits"
        for label, _ in qualification_summary_rows(q, "SI", concise=True)
    )
    q.update(utilization=".5", covered_response_ids=["ONE"], mismatch_reasons=[])
    q["statistics"]["Ro"] = "100"
    assert ("Qualification utilization", "0.5 (below 1.0)") in qualification_summary_rows(q, "SI")
    assert not any(
        label == "Source / approval limits"
        for label, _ in qualification_summary_rows(q, "SI", concise=True)
    )
