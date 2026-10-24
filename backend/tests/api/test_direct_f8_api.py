"""Authenticated normal workflow, immutable audit, staleness and F7 parity."""

from __future__ import annotations

import asyncio
import io
import json
import platform
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from pypdf import PdfReader
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design, supported
from tests.api.test_mat1_routes import condition, selection
from tests.direct_f8_fixtures import qa_design, synthetic_record
from tests.test_multirow_api import _payload as multirow_payload

import frp_master_connection.api.direct_qualification as service
from frp_master_connection.api.app import create_app
from frp_master_connection.infrastructure.direct_qualification_records import canonical_record
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotError, SnapshotSigner


@pytest.fixture(scope="module")
def qa() -> tuple[Any, ...]:
    return qa_design()


def test_normal_owner_all_eight_full_records_exact_f7_parity() -> None:
    actual = design(f6_cases()["owner-135"])
    baseline = json.loads(
        (
            Path(__file__).parents[1] / "fixtures/direct_f8_accepted_f7_342_engineering.json"
        ).read_text(encoding="utf-8")
    )
    expected = baseline["references"]["windows" if platform.system() == "Windows" else "ubuntu"]
    assert supported(actual) == expected["checks"]
    assert (
        actual["native_design"]["automatic_group_mode_integration"] == expected["owner_aggregate"]
    )
    assert actual["material_ledgers"] == expected["material_ledgers"]
    assert actual["overall_status"] == "ENGINEERING_REVIEW_REQUIRED"
    evaluation = actual["qualification_evaluation"]
    assert evaluation["record_digest"] is None
    assert evaluation["covered_response_ids"] == []
    assert evaluation["ordinary_pass_allowed"] is False
    assert "specimens" not in json.dumps(evaluation)


@pytest.mark.parametrize("name", ["owner-135", "si-owner"])
def test_real_owner_engineer_report_wording_and_full_audit(name: str) -> None:
    body = f6_cases()[name]
    result = design(body)
    signer = SnapshotSigner(b"DIRECT-F8-AUTHENTICATED-REPORT-TEST-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row",
            kind="design",
            request=body,
            result=result,
            account_id="f8",
            input_provenance=service.qualification_snapshot_provenance(result),
        ),
        account_id="f8",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions())
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "Required — no approved matching record" in text
    assert "Section 2.3.2 whole-connection qualification coverage required" in text
    assert "Approved matching Section 2.3.2 qualification record required" in text
    assert "8 supported checks evaluated" in text
    assert "6 required checks/evidence items unresolved" in text
    assert before == (snapshot.request, snapshot.result)


@pytest.mark.parametrize("case", ["exact", "geometry", "action", "statistics", "capacity"])
def test_synthetic_real_pdf_summary_and_private_evidence(
    tmp_path: Path,
    qa: tuple[Any, ...],
    case: str,
) -> None:
    body, result, scope, required, ledgers, context = qa
    payload = synthetic_record(scope, tmp_path, strength="100" if case == "capacity" else "10000")
    current = deepcopy(scope)
    if case == "geometry":
        current["geometry_scope"]["row_count"] = 3
    elif case == "action":
        current["action_scope"]["Mx"] = "1"
    elif case == "statistics":
        payload["statistical_protocol"]["lab_reported_cov"]["value"] = "0.15"
        payload["digest"] = ""
    public, audit = service.evaluate_record(
        canonical_record(payload),
        current,
        required,
        ledgers,
        context,
        qa_preview=True,
    )
    native_before = deepcopy(result)
    augmented = {**result, "qualification_evaluation": public}
    signer = SnapshotSigner(b"DIRECT-F8-SYNTHETIC-NONACTIVATING-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row",
            kind="design",
            request=body,
            result=augmented,
            account_id="qa",
            input_provenance={"direct_qualification_audit": audit},
        ),
        account_id="qa",
    )
    pdf = render_report_pdf(snapshot, ReportOptions())
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN" in text
    assert "SYNTHETIC_QA_ONLY / 1" in text
    assert "SYNTHETIC_QA_1" not in text
    if case == "capacity":
        assert "CAPACITY_FAIL" in text
    elif case in {"geometry", "action", "statistics"}:
        assert "UNEVALUATED" in text
    else:
        assert "CAPACITY_PASS" in text
    assert result == native_before
    if case == "exact":
        audit_pdf = render_report_pdf(snapshot, ReportOptions(mode="FULL_TECHNICAL_AUDIT"))
        audit_text = " ".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(audit_pdf)).pages
        )
        assert "SYNTHETIC_QA_10" in audit_text
        assert audit["design_snapshot_digest"] in audit_text.replace("\n", "")
        assert public["evaluation_digest"] in audit_text.replace("\n", "")


def test_snapshot_cache_missing_and_eviction_fail_closed() -> None:
    assert service.qualification_snapshot_provenance({}) == {}
    with pytest.raises(SnapshotError, match="unavailable"):
        service.qualification_snapshot_provenance(
            {"qualification_evaluation": {"evaluation_digest": "missing"}}
        )
    for i in range(65):
        service.remember_audit({"evaluation_digest": "cache-test-" + str(i)}, {"value": i})
    with pytest.raises(SnapshotError):
        service.qualification_snapshot_provenance(
            {"qualification_evaluation": {"evaluation_digest": "cache-test-0"}}
        )
    assert (
        service.qualification_snapshot_provenance(
            {"qualification_evaluation": {"evaluation_digest": "cache-test-64"}}
        )["direct_qualification_audit"]["value"]
        == 64
    )


def test_catalog_and_snapshot_lifecycle_policy_double(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qa: tuple[Any, ...],
) -> None:
    # Test-double supplied record bypasses provider deliberately; it never installs
    # synthetic qualification. Real provider rejection is covered separately.
    record = canonical_record(synthetic_record(qa[2], tmp_path))
    records = [record]
    monkeypatch.setattr(
        service, "production_provider", lambda: SimpleNamespace(read=lambda: (tuple(records), ()))
    )
    catalog = service.qualification_catalog()
    assert catalog["records"][0]["digest"] == record.digest
    assert "specimens" not in json.dumps(catalog)
    result = {
        "qualification_evaluation": {
            "record_digest": record.digest,
            "selected_record_id": "SYNTHETIC_QA_ONLY",
            "record_revision": 1,
        }
    }
    assert service.qualification_snapshot_current(result)
    records.clear()
    assert not service.qualification_snapshot_current(result)
    assert service.qualification_snapshot_current({})
    assert service.qualification_snapshot_current(
        {"qualification_evaluation": {"record_digest": None}}
    )
    wrong_id = deepcopy(result)
    wrong_id["qualification_evaluation"]["selected_record_id"] = "wrong"
    records.append(record)
    assert not service.qualification_snapshot_current(wrong_id)
    wrong_id["qualification_evaluation"].update(
        selected_record_id="SYNTHETIC_QA_ONLY", record_revision=2
    )
    assert not service.qualification_snapshot_current(wrong_id)
    legacy = deepcopy(qa[0]["legacy_request"])
    attached = service.attach_qualification(
        qa[1], legacy, qa[5], "SYNTHETIC_QA_ONLY", qa[2]["environmental_scope"]["conditions"], qa[4]
    )
    assert attached["qualification_evaluation"]["capacity_state"] == "UNEVALUATED"
    assert attached["native_design"] == qa[1]["native_design"]
    legacy["direct_finalization_contract_version"] = None
    assert service.attach_qualification(qa[1], legacy, None, None, {}, []) is qa[1]
    with pytest.raises(ValueError, match="DIRECT_ANGLE_TO_W_ONLY"):
        service.attach_qualification(qa[1], legacy, qa[5], None, {}, [])


def test_authenticated_export_rejects_withdrawn_qualification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = f6_cases()["owner-135"]

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://testserver"
        ) as client:
            catalog = await client.get("/api/v1/frp-materials/direct-qualification/records")
            assert catalog.status_code == 200
            # A valid existing non-Direct design must reject qualification selection
            # at the authenticated Direct-only boundary, without altering that family.
            materials = await client.get("/api/v1/frp-materials/catalog")
            legacy = multirow_payload()
            non_direct = {
                "contract": "MAT1-MULTI-ROW-RC0",
                "legacy_request": legacy,
                "assignments": {
                    "default_material": selection(materials.json()["records"][1]),
                    "default_conditions": condition(cast(str, legacy["time_effect_category"])),
                },
                "qualification_record_id": "NON-DIRECT-QUALIFICATION-MUST-REJECT",
            }
            rejected = await client.post(
                "/api/v1/frp-materials/multi-row/design-check", json=non_direct
            )
            assert rejected.status_code == 422
            assert rejected.json()["detail"]["code"] == (
                "QUALIFICATION_SCOPE_IS_DIRECT_ANGLE_TO_W_ONLY"
            )
            response = await client.post(
                "/api/v1/frp-materials/multi-row/design-check?report_snapshot=1", json=body
            )
            assert response.status_code == 200
            monkeypatch.setattr(
                "frp_master_connection.reporting.routes.qualification_snapshot_current",
                lambda _result: False,
            )
            pdf = await client.post(
                "/api/v1/reports/export",
                json={"report_snapshot": response.json()["report_snapshot"]},
            )
            assert pdf.status_code == 409
            assert "fresh Design Check" in pdf.text

    asyncio.run(run())


def test_missing_action_and_inapplicable_declared_context_fail_closed(qa: tuple[Any, ...]) -> None:
    legacy = deepcopy(qa[0]["legacy_request"])
    materials = {
        **qa[1]["material_sources"],
        "qualification_conditions": qa[2]["environmental_scope"]["conditions"],
    }
    legacy["physical_connection"]["joint_assembly"]["member_end_actions"] = []
    scope, required = service.authenticated_scope(legacy, materials, {}, None)
    assert required is None
    assert scope["action_scope"]["frame_kind"] is None
    legacy = deepcopy(qa[0]["legacy_request"])
    legacy["demand_source"] = "EXPLICIT_GROUP_RESULTANT"
    _, required = service.authenticated_scope(legacy, materials, {}, qa[5])
    assert required is None
    assert service.normalized([{"x": "1", "y": "2", "z": "0", "unit": "in"}]) == [
        {"x": "25.4", "y": "50.8", "z": "0", "unit": "mm"}
    ]
    assert service.normalized("text") == "text"


def test_heterogeneous_joint_factors_require_approved_basis(
    tmp_path: Path, qa: tuple[Any, ...]
) -> None:
    data = synthetic_record(qa[2], tmp_path)
    ledgers = [*qa[4], replace(qa[4][0], component_id="member-b", ct=Decimal(".6"))]
    rd, _, blockers = service.qualification_capacity(
        data, qa[2], ledgers, Decimal(10000), Decimal(1)
    )
    assert rd is None
    assert "WHOLE_JOINT_MULTIPLE_MATERIAL_FACTOR_BASIS_UNRESOLVED" in blockers


@pytest.mark.parametrize(
    "mutation",
    ["chemical", "live", "fatigue", "unknown-reference", "position", "finite", "wrong-product"],
)
def test_authenticated_scope_unknowns_are_not_wildcards(qa: tuple[Any, ...], mutation: str) -> None:
    legacy = deepcopy(qa[0]["legacy_request"])
    conditions = deepcopy(qa[2]["environmental_scope"]["conditions"])
    context = qa[5]
    action = legacy["physical_connection"]["joint_assembly"]["member_end_actions"][0]
    if mutation == "chemical":
        conditions["chemical"] = "SPECIFIED_SOURCE_REQUIRED"
    elif mutation == "live":
        conditions["time_category"] = "LIVE_LOAD"
    elif mutation == "fatigue":
        conditions["fatigue_cycles"] = "10000"
    elif mutation == "unknown-reference":
        action["reference_point"]["kind"] = "OTHER_UNRESOLVED"
    elif mutation == "position":
        action["reference_point"]["position"] = {"x": "1", "y": "0", "z": "0", "unit": "in"}
    elif mutation == "finite":
        legacy["supporting_w_longitudinal_ends"] = {
            "condition": "FINITE_BOTH_ENDS",
            "negative_end_distance": {"value": "20", "unit": "in"},
            "positive_end_distance": {"value": "20", "unit": "in"},
        }
    else:
        payload = context.model_dump(mode="json")
        payload["products"]["member-a"]["mat1_record_id"] = "wrong"
        context = service.QualificationDesignContext.model_validate(payload)
    materials = {**qa[1]["material_sources"], "qualification_conditions": conditions}
    scope, required = service.authenticated_scope(
        legacy, materials, qa[1]["fastener_source"], context, qa[1]["native_design"]["preview"]
    )
    assert required is not None
    assert scope != qa[2]


@pytest.mark.parametrize("required", [None, Decimal(-1)])
def test_unknown_required_action_prevents_qualification_capacity(
    tmp_path: Path, qa: tuple[Any, ...], required: Decimal | None
) -> None:
    result, _ = service.evaluate_record(
        canonical_record(synthetic_record(qa[2], tmp_path)),
        qa[2],
        required,
        qa[4],
        qa[5],
        qa_preview=True,
    )
    assert result["capacity_state"] == "UNEVALUATED"
    assert "QUALIFICATION_LOAD_SCOPE_UNRESOLVED" in result["mismatch_reasons"]


@pytest.mark.parametrize(("dead", "live"), [("-1", "0"), ("0", "-1"), ("mm", "0"), ("0", "mm")])
def test_invalid_nominal_gravity_components_are_unavailable(
    qa: tuple[Any, ...], dead: str, live: str
) -> None:
    payload = qa[5].model_dump(mode="json")
    payload.update(
        loading_type="GRAVITY_D_L",
        dead_load={"value": "1" if dead == "mm" else dead, "unit": "mm" if dead == "mm" else "N"},
        live_load={"value": "1" if live == "mm" else live, "unit": "mm" if live == "mm" else "N"},
    )
    context = service.QualificationDesignContext.model_validate(payload)
    assert service.compare_strength(Decimal(100), Decimal(10), context, True)[
        "gravity_eq_2_2_state"
    ].startswith("UNAVAILABLE")


def test_unspecified_support_end_never_becomes_continuous(qa: tuple[Any, ...]) -> None:
    legacy = deepcopy(qa[0]["legacy_request"])
    legacy["supporting_w_longitudinal_ends"] = {"condition": "UNSPECIFIED"}
    scope, _ = service.authenticated_scope(
        legacy,
        {
            **qa[1]["material_sources"],
            "qualification_conditions": qa[2]["environmental_scope"]["conditions"],
        },
        qa[1]["fastener_source"],
        None,
    )
    assert scope["support_scope"]["longitudinal_ends"]["condition"] == "UNSPECIFIED"
