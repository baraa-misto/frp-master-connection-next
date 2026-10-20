"""Actual authenticated native capture, isolated HTTP flow, export and rendered PDF evidence."""

import asyncio
import io
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.hyb2_d2_review import create_d2_review_app
from frp_master_connection.application.hyb1_mapping import EXISTING_IDS
from frp_master_connection.application.hyb2_d2 import (
    D2Assessment,
    HardwareEvidence,
    SourceConditions,
    assess_d2,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest
from frp_master_connection.reporting.hyb2_d2_review import path_drawing, render_d2
from frp_master_connection.reporting.hyb2_d2_service import (
    D2ReviewService,
    ReviewSource,
    assessment_record,
)
from frp_master_connection.reporting.snapshot import SnapshotError, SnapshotSigner
from frp_master_connection.security.identity import TrustedIdentity
from tests.hyb1_fixtures import q
from tests.hyb2_d2_fixtures import actual_native_source, support_source


class Resolver:
    production_capable = False

    def __init__(self, account: str) -> None:
        self.account = account

    async def resolve(self) -> TrustedIdentity:
        return TrustedIdentity(self.account, None, frozenset({"reviewer"}), "isolated-test-server")


@pytest.fixture(scope="module")
def real_native() -> tuple[SnapshotSigner, ReviewSource, dict[str, Any]]:
    return actual_native_source()


def text(pdf: bytes) -> str:
    return " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )


def test_d2_06_signed_native_eight_results_preserved(
    real_native: tuple[SnapshotSigner, ReviewSource, dict[str, Any]],
) -> None:
    signer, s, original = real_native
    before = repr(original)
    service = D2ReviewService(signer)
    revision = service.register("native", s)
    handle, record = service.calculate("native", revision, s.actions.identity.account)
    a = record["assessment"]
    assert a["native_status"] == original["final_decision"]["final_status"] == "YELLOW"
    native_rows = {r["mechanism"]: r for r in a["comparisons"]}
    for row in original["final_decision"]["schedule"]:
        assert native_rows[row["check_id"]]["native_outcome"] == row["outcome"]
        assert native_rows[row["check_id"]]["ratio"] == row["utilization"]
    assert {
        c["native_id"] for c in a["coverage"] if c["disposition"] == "ASCE_CURRENT_EVALUATED"
    } == set(EXISTING_IDS)
    assert a["evaluated_outcome"] == "PASS"
    assert a["tone"] == "green"
    assert a["coverage_state"] == "PARTIAL"
    assert not a["case_sets_complete"]
    assert not a["r3_records"]
    assert service.export_record(handle, s.actions.identity.account) == record
    pdf = text(render_d2(record))
    assert "NOT_ESTABLISHED_SECTION_2_3_2" in pdf
    assert "Native F8/F9: YELLOW (unchanged)" in pdf
    assert before == repr(original)


def test_d2_07_real_native_overload_remains_red() -> None:
    signer, s, original = actual_native_source(overload=True)
    service = D2ReviewService(signer)
    rev = service.register("red", s)
    _, record = service.calculate("red", rev, s.actions.identity.account)
    assert original["final_decision"]["final_status"] == "RED"
    assert record["assessment"]["evaluated_outcome"] == "FAIL"
    assert record["assessment"]["tone"] == "red"


@pytest.mark.parametrize(
    "kind", ["source", "overload", "invalid", "properties", "missing", "confirmed-washer", "brace"]
)
@pytest.mark.parametrize("technical", [False, True])
def test_d2_21_25_26_real_report_records_print_only(kind: str, technical: bool) -> None:
    s = support_source()
    a = s.actions
    if kind == "overload":
        case = replace(a.asd[0], components=(q("60"), *a.asd[0].components[1:]))
        s = replace(s, actions=replace(a, asd=(case,)))
    elif kind == "invalid":
        g = R3Geometry(hole=q("3", Unit.IN))
        s = replace(
            s,
            geometry=g,
            actions=replace(a, identity=replace(a.identity, geometry=geometry_digest(g))),
        )
    elif kind == "properties":
        s = replace(s, conditions=SourceConditions(resin="UNAPPROVED_PRODUCT"))
    elif kind == "missing":
        s = replace(s, actions=replace(a, asd=()))
    elif kind == "confirmed-washer":
        s = replace(
            s, hardware=HardwareEvidence("R3_BRACE_END_FREE_EDGE", q("1", Unit.IN), "a" * 64)
        )
    elif kind == "brace":
        from frp_master_connection.application.hyb1_contract import Alignment

        s = replace(s, actions=replace(a, identity=replace(a.identity, alignment=Alignment.BRACE)))
    service = D2ReviewService(SnapshotSigner())
    rev = service.register("source", s)
    handle, record = service.calculate("source", rev, a.identity.account)
    before = repr(record)
    raw = render_d2(service.export_record(handle, a.identity.account), technical=technical)
    pdf = text(raw)
    assert raw.startswith(b"%PDF")
    assert before == repr(record)
    assert "Complete connection verification is not established" in pdf
    assert record["assessment"]["evaluated_outcome"] in pdf
    assert "REDACTED_ACCOUNT_BOUND" not in pdf  # No account identity in the professional view.
    assert a.identity.account not in pdf
    assert handle not in pdf
    assert "R1." not in pdf
    if kind == "source":
        assert "0.023493653732061" in pdf
        assert "0.054161323634086" in pdf
        assert "0.0625" in pdf
        assert "FACE_UNKNOWN_CONDITIONAL_SCREEN" in pdf
        assert "1.716129811447" in pdf
        if technical:
            assert "HALF_AT_CENTER_ENDPOINT" in pdf
    if kind in ("invalid", "confirmed-washer", "brace"):
        assert "NOT_FIT" in pdf


def test_d2_22_27_http_account_binding_injection_and_stale_exports() -> None:
    async def run() -> None:
        s = support_source()
        service = D2ReviewService(SnapshotSigner())
        rev = service.register("source", s)
        app = create_d2_review_app(service, Resolver(s.actions.identity.account))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://isolated-review"
        ) as client:
            response = await client.post(
                "/review/assess", json={"case_key": "source", "revision": rev}
            )
            assert response.status_code == 200
            handle = response.json()["report_handle"]
            assert (await client.get("/review/report/" + handle)).content.startswith(b"%PDF")
            view = await client.get("/review/view/" + handle)
            assert view.status_code == 200
            assert "PASS (scoped)" in view.text
            assert "NOT_ESTABLISHED" in view.text
            for bad in (
                {"capacity": "10000"},
                {"approved": True},
                {"account": "other"},
                {"result": {"status": "GREEN"}},
            ):
                rejected = await client.post(
                    "/review/assess", json={"case_key": "source", "revision": rev, **bad}
                )
                assert rejected.status_code == 422
            assert (
                await client.post("/review/assess", json={"case_key": "missing", "revision": 1})
            ).status_code == 409
            service.register("source", s)
            assert (await client.get("/review/report/" + handle)).status_code == 409
            assert (await client.get("/review/view/" + handle)).status_code == 409
            assert (
                await client.post("/review/assess", json={"case_key": "source", "revision": rev})
            ).status_code == 409
        app2 = create_d2_review_app(service, Resolver("OTHER_ACCOUNT"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app2), base_url="http://isolated-review"
        ) as client:
            assert (
                await client.post("/review/assess", json={"case_key": "source", "revision": 2})
            ).status_code == 409
            assert (await client.get("/review/report/" + handle)).status_code == 409

    asyncio.run(run())


def test_d2_22_late_response_cannot_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    import frp_master_connection.reporting.hyb2_d2_service as module

    s = support_source()
    service = D2ReviewService(SnapshotSigner())
    rev = service.register("source", s)
    original = assess_d2

    def late(*args: object, **kwargs: object) -> D2Assessment:
        evaluator: Callable[..., D2Assessment] = original
        result = evaluator(*args, **kwargs)
        service.register("source", s)
        return result

    monkeypatch.setattr(module, "assess_d2", late)
    with pytest.raises(SnapshotError, match="stale"):
        service.calculate("source", rev, s.actions.identity.account)


def test_service_validation_and_export_revalidation() -> None:
    from tests.application.test_hyb2_d2 import result

    s = support_source()
    with pytest.raises(ValueError, match="Native audit"):
        assessment_record(result(s), s, b"{}")
    service = D2ReviewService(SnapshotSigner())
    for key in ("", "x" * 101):
        with pytest.raises(ValueError, match="key"):
            service.register(key, s)
    rev = service.register("source", s)
    handle, record = service.calculate("source", rev, s.actions.identity.account)
    with pytest.raises(SnapshotError, match="identity"):
        service.export_record(handle, "OTHER")
    wrong = service._signer.issue(
        family="HYB2_D2_ISOLATED_REVIEW",
        kind="design",
        request={
            "case_key": "source",
            "revision": rev,
            "fingerprint": "corrupt",
            "assessment_date": datetime.now(UTC).date().isoformat(),
        },
        result=record,
        account_id=s.actions.identity.account,
    )
    with pytest.raises(SnapshotError, match="evidence/date"):
        service.export_record(service._store.put(wrong), s.actions.identity.account)
    old = service._signer.issue(
        family="HYB2_D2_ISOLATED_REVIEW",
        kind="design",
        request={
            "case_key": "source",
            "revision": rev,
            "fingerprint": s.fingerprint,
            "assessment_date": (datetime.now(UTC).date() - timedelta(days=1)).isoformat(),
        },
        result=record,
        account_id=s.actions.identity.account,
    )
    with pytest.raises(SnapshotError, match="evidence/date"):
        service.export_record(service._store.put(old), s.actions.identity.account)
    r3 = record["assessment"]["r3_records"][0][1]
    for b in r3["blocks"]:
        for p in b["paths"]:
            p["end"] = None
    assert path_drawing(r3, "BRACE") is not None
