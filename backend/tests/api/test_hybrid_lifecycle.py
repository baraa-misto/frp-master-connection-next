"""Currentness, authentic export and isolation tests for the live candidate bridge."""

import asyncio
import io
import time
from datetime import date
from threading import Event
from typing import cast

import httpx
import pytest
from pypdf import PdfReader
from tests.api.test_hybrid_workflow import BASE, LiveTransport
from tests.hybrid_workflow_fixtures import live_native, live_source, q

import frp_master_connection.api.hybrid_workflow as bridge
from frp_master_connection.api.hybrid_app import create_hybrid_app
from frp_master_connection.application.hyb1_contract import PairedActions
from frp_master_connection.application.hyb1_review import NativeCapture
from frp_master_connection.application.hyb2_d2 import D2Assessment, SourceConditions
from frp_master_connection.application.hybrid_workflow import declared_fit
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry
from frp_master_connection.reporting.hybrid_store import FAMILY, HybridStore
from frp_master_connection.reporting.snapshot import SnapshotError
from frp_master_connection.security import TrustedIdentity


def test_p25_26_late_computation_cannot_seal_after_a_new_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started, release = Event(), Event()
    from frp_master_connection.application.hyb2_d2 import assess_d2

    original = assess_d2

    def delayed(
        actions: PairedActions,
        native: NativeCapture,
        *,
        geometry: R3Geometry | None,
        conditions: SourceConditions,
        today: date,
    ) -> D2Assessment:
        started.set()
        assert release.wait(10)
        return original(actions, native, geometry=geometry, conditions=conditions, today=today)

    monkeypatch.setattr(bridge, "assess_d2", delayed)

    async def exercise() -> None:
        app = create_hybrid_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            body = live_source()
            old = asyncio.create_task(client.post(BASE + "/assess", json=body))
            try:
                assert await asyncio.to_thread(started.wait, 10)
                newer = await client.post(
                    BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": 1}
                )
                assert newer.status_code == 200
            finally:
                release.set()
            response = await old
            assert response.status_code == 409
            assert "Late/superseded" in response.text
            assert "report_handle" not in response.json()

    asyncio.run(exercise())


def test_p27_account_expiry_and_immutable_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class Identity:
        production_capable = True
        account = "A"

        async def resolve(self) -> TrustedIdentity:
            return TrustedIdentity(self.account, None, frozenset(), "trusted-test-resolver")

    identity = Identity()
    client = LiveTransport()
    client.app = create_hybrid_app(identity_resolver=identity)
    result = client.post(BASE + "/assess", json=live_source()).json()
    handle = result["report_handle"]
    current = client.get(BASE + "/records/" + handle)
    assert current.status_code == 200
    assert current.json() == result["record"]
    assert current.headers["cache-control"] == "no-store"
    identity.account = "B"
    assert client.get(BASE + "/reports/" + handle).status_code == 409
    assert client.get(BASE + "/records/" + handle).status_code == 409
    identity.account = "A"
    assert client.get(BASE + "/records/" + handle).status_code == 200
    import frp_master_connection.reporting.snapshot as snapshot

    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + snapshot.SNAPSHOT_LIFETIME_SECONDS + 1)
    assert client.get(BASE + "/reports/" + handle).status_code == 409


def test_store_monotonic_revision_fingerprint_and_foreign_family() -> None:
    store = HybridStore()
    fingerprint = store.register("A", "W", 2, {"input": 1})
    store.invalidate("A", "W", 2)
    with pytest.raises(SnapshotError, match="Superseded"):
        store.invalidate("A", "W", 1)
    with pytest.raises(SnapshotError, match="Changed inputs"):
        store.register("A", "W", 2, {"input": 2})
    request = {"workspace_id": "W", "revision": 2, "fingerprint": fingerprint}
    token = store.signer.issue(
        family=FAMILY + "OTHER", kind="design", request=request, result={}, account_id="A"
    )
    with pytest.raises(SnapshotError, match="another report family"):
        store.export(store.store.put(token), "A")
    for i in range(255):
        store.invalidate("A", str(i), 0)
    with pytest.raises(SnapshotError, match="workspace limit"):
        store.invalidate("A", "new", 0)
    assert store.register("A", "W", 2, {"input": 1}) == fingerprint


def test_stale_assess_invalidate_and_changed_same_revision() -> None:
    with LiveTransport() as client:
        body = live_source()
        assert client.post(BASE + "/preview", json=body).status_code == 200
        body["geometry"]["xb"] = q(".5")
        assert client.post(BASE + "/preview", json=body).status_code == 409
        assert (
            client.post(
                BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": 2}
            ).status_code
            == 200
        )
        assert (
            client.post(
                BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": 1}
            ).status_code
            == 409
        )
        assert client.post(BASE + "/assess", json=body).status_code == 409


@pytest.mark.parametrize("target", ["preview", "assess"])
def test_invalid_geometric_input_raises_actionable_422(target: str) -> None:
    with LiveTransport() as client:
        body = live_source()
        body["geometry"]["column_thickness"] = q("4")
        body["geometry"]["column_flange"] = q("8")
        response = client.post(BASE + "/" + target, json=body)
        assert response.status_code == 422
        assert "source I8" in response.text


def test_native_missing_conditions_and_support_no_fit_are_independent() -> None:
    with LiveTransport() as client:
        body = live_native()
        body["native_request"].pop("material_request")
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200, response.text
        assert "Native calculation withheld" in str(response.json()["record"]["withheld"])
        assert response.json()["record"]["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
        body["revision"] += 1
        body["native_request"]["alignment"] = body["alignment"] = "SUPPORT"
        body["native_request"]["offset"] = {
            "support_longitudinal": q("0"),
            "support_transverse": q("50"),
        }
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["native_geometry"]["geometry"]["aggregate_state"] == "DOES_NOT_FIT"
        assert response.json()["record"]["assessment"]["fit"]["state"] == "NOT_FIT"


def test_native_material_report_and_actual_end_rule_failure() -> None:
    with LiveTransport() as client:
        body = live_native()
        legacy = body["native_request"]["legacy"]
        legacy["loaded_boundary_to_row_1_distance"] = q(".9")
        legacy["unloaded_end_e1"] = q(".9")
        legacy["physical_connection"]["geometry_template"]["bolt_to_brace_end_distance"] = q(".9")
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200, response.text
        record = response.json()["record"]
        failures = record["detailing_failures"]
        assert any("END_DISTANCE" in c["check_kind"] for c in failures), record["detailing_checks"]
        assert all(c["actual_distance"] is not None and c["source_rule"] for c in failures)
        pdf = client.get(BASE + "/reports/" + response.json()["report_handle"])
        assert pdf.status_code == 200, pdf.text
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages)
        assert "DETAILING REQUIREMENT FAIL" in text
        assert "Table 8-1" in text
        assert (
            client.get(
                BASE + "/reports/" + response.json()["report_handle"] + "?technical=true"
            ).status_code
            == 200
        )
        body = live_native()
        body["revision"] = 2
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200
        pdf = client.get(BASE + "/reports/" + response.json()["report_handle"])
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages)
        assert "Actual native material records" in text
        assert "Actual native hardware" in text
        assert (
            client.get(
                BASE + "/reports/" + response.json()["report_handle"] + "?technical=true"
            ).status_code
            == 200
        )


def test_units_native_rejection_reverse_conversion_unknown_and_independent_lrfd() -> None:
    with LiveTransport() as client:
        assert (
            client.post(BASE + "/units", json={"inputs": live_native(), "system": "mm"}).status_code
            == 422
        )
        body = live_source()
        body["lrfd_cases"] = [body["asd_cases"][0]]
        body["asd_cases"][0]["components"][3] = None
        body["washer_od"] = q("1")
        body["native_edge_distance"] = q(".4375")
        converted = client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
        assert converted.status_code == 200
        reverted = client.post(BASE + "/units", json={"inputs": converted.json(), "system": "in"})
        assert reverted.status_code == 200
        result = client.post(BASE + "/assess", json=reverted.json())
        assert result.status_code == 200
        assert len(result.json()["record"]["actions"]["lrfd"]) == 1
        assert result.json()["record"]["requested_computation"]["native_checks_executed"] == 0


@pytest.mark.parametrize("failure", ["queue", "render", "size", "cancelled"])
def test_report_resource_limits_are_bounded(failure: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if failure == "queue":
        monkeypatch.setattr(bridge, "MAX_CONCURRENT_REPORTS", 0)
        monkeypatch.setattr(bridge, "MAX_QUEUE_SECONDS", 0.001)
    elif failure == "render":

        def timed_out(*args: object, **kwargs: object) -> bytes:
            raise TimeoutError

        monkeypatch.setattr(bridge, "render_hybrid", timed_out)
    elif failure == "size":
        monkeypatch.setattr(bridge, "MAX_PDF_BYTES", 1)
    else:

        def cancelled(*args: object, **kwargs: object) -> bytes:
            raise asyncio.CancelledError

        monkeypatch.setattr(bridge, "render_hybrid", cancelled)
    with LiveTransport() as client:
        response = client.post(BASE + "/assess", json=live_source())
        if failure == "cancelled":
            with pytest.raises(RuntimeError, match="No response returned"):
                client.get(BASE + "/reports/" + response.json()["report_handle"])
            return
        exported = client.get(BASE + "/reports/" + response.json()["report_handle"])
        assert exported.status_code == 503


@pytest.mark.parametrize(
    "guard", ["direct_status_snapshot_current", "qualification_snapshot_current"]
)
def test_native_export_preserves_original_currency_guards(
    guard: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with LiveTransport() as client:
        response = client.post(BASE + "/assess", json=live_native())
        assert response.status_code == 200
        handle = response.json()["report_handle"]
        monkeypatch.setattr(bridge, guard, lambda *_args: False)
        for path in ["reports", "records"]:
            exported = client.get(BASE + "/" + path + "/" + handle)
            assert exported.status_code == 409
            assert "qualification evidence changed" in exported.text


def test_timed_out_renderer_retains_its_concurrency_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    started, release = Event(), Event()
    calls = []

    def held(*args: object, **kwargs: object) -> bytes:
        calls.append(1)
        started.set()
        assert release.wait(10)
        return b"PDF-render-resource-test-only"

    monkeypatch.setattr(bridge, "MAX_CONCURRENT_REPORTS", 1)
    monkeypatch.setattr(bridge, "MAX_RENDER_SECONDS", 0.01)
    monkeypatch.setattr(bridge, "MAX_QUEUE_SECONDS", 0.01)
    monkeypatch.setattr(bridge, "render_hybrid", held)

    async def exercise() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_hybrid_app()), base_url="http://testserver"
        ) as client:
            response = await client.post(BASE + "/assess", json=live_source())
            path = BASE + "/reports/" + response.json()["report_handle"]
            try:
                assert (await client.get(path)).status_code == 503
                assert started.is_set()
                assert (await client.get(path)).status_code == 503
                assert calls == [1]
            finally:
                release.set()

    asyncio.run(exercise())


def test_runtime_binding_and_oversized_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRP_HYBRID_CANDIDATE_SHA", "explicit-startup-receipt-required")
    with LiveTransport() as client:
        runtime = client.get(BASE + "/runtime")
        assert runtime.status_code == 200
        assert runtime.json()["candidate_sha"] == "explicit-startup-receipt-required"
        assert runtime.json()["backend_module"].endswith("hybrid_app.py")
        assert not runtime.json()["structural_method_activation"]
        response = client.post(BASE + "/preview", json={"oversized": "x" * 8_000_001})
        assert response.status_code == 413


def test_export_rechecks_revision_after_the_renderer_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.reporting.hybrid_workflow import render_hybrid

    started, release = Event(), Event()

    def held(record: dict[str, object], *, technical: bool = False) -> bytes:
        started.set()
        assert release.wait(10)
        return render_hybrid(record, technical=technical)

    monkeypatch.setattr(bridge, "render_hybrid", held)

    async def exercise() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_hybrid_app()), base_url="http://testserver"
        ) as client:
            body = live_source()
            assessed = await client.post(BASE + "/assess", json=body)
            pending = asyncio.create_task(
                client.get(BASE + "/reports/" + assessed.json()["report_handle"])
            )
            try:
                assert await asyncio.to_thread(started.wait, 10)
                assert (
                    await client.post(
                        BASE + "/invalidate",
                        json={"workspace_id": body["workspace_id"], "revision": 1},
                    )
                ).status_code == 200
            finally:
                release.set()
            response = await pending
            assert response.status_code == 409

    asyncio.run(exercise())


@pytest.mark.parametrize(("edge", "washer"), [("-1", "1"), ("1", "0")])
def test_elementary_fit_rejects_impossible_dimensions_without_an_engineering_tolerance(
    edge: str, washer: str
) -> None:
    with pytest.raises(ValueError, match="Nonnegative edge"):
        declared_fit(
            cast(D2Assessment, None),
            edge=PhysicalQuantity.of(edge, Unit.IN),
            washer=PhysicalQuantity.of(washer, Unit.IN),
            face="UNKNOWN",
        )
