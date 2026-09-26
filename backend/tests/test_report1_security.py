"""REPORT1 authority, route inventory and display conversion boundaries."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import zlib

import httpx
import pytest
from pydantic import ValidationError

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.capture import reportable_route
from frp_master_connection.reporting.flatten import flatten_unique
from frp_master_connection.reporting.pdf import ReportingCoverageError
from frp_master_connection.reporting.routes import ExportRequest
from frp_master_connection.reporting.snapshot import (
    ReportSnapshotStore,
    SnapshotError,
    SnapshotSigner,
)
from frp_master_connection.reporting.units import converted_quantity_rows


@pytest.mark.parametrize(
    ("path", "body", "expected"),
    [
        ("/api/v1/calculations/single-bolt/evaluate", {}, ("single-bolt", "design")),
        ("/api/v1/calculations/multi-row/preview", {}, ("multi-row", "input_only")),
        (
            "/api/v1/calculations/stair-stringer-miter/analytical-design-check",
            {},
            ("stair-stringer-miter", "design"),
        ),
        (
            "/api/v1/frp-materials/family/design-check",
            {"family_id": "clip-angle"},
            ("clip-angle", "design"),
        ),
        ("/api/v1/frp-materials/single-bolt/design-check", {}, ("single-bolt", "design")),
        ("/api/v1/calculations/unknown/design-check", {}, None),
        ("/api/v1/calculations/multi-row/defaults", {}, None),
        ("/api/v1/frp-materials/family/design-check", {"family_id": "bogus"}, None),
        ("/api/v1/frp-materials/unknown/design-check", {}, None),
    ],
)
def test_only_native_calculation_routes_mint_report_authority(
    path: str,
    body: dict[str, object],
    expected: tuple[str, str] | None,
) -> None:
    assert reportable_route(path, body) == expected


def _signed_token() -> tuple[SnapshotSigner, str]:
    signer = SnapshotSigner(b"r" * 32)
    token = signer.issue(
        family="single-bolt",
        kind="design",
        request={"id": "A"},
        result={"overall_status": "SOURCE_REQUIRED"},
        account_id="owner",
        now=1_000,
    )
    return signer, token


@pytest.mark.parametrize(
    "change",
    [
        lambda token: "bad",
        lambda token: "R0." + token.split(".", 1)[1],
        lambda token: token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1:],
        lambda token: token + ".extra",
    ],
)
def test_invalid_signed_envelopes_fail_closed(change: object) -> None:
    signer, token = _signed_token()
    forged = change(token)  # type: ignore[operator]
    with pytest.raises(SnapshotError):
        signer.verify(forged, account_id="owner", now=1_001)


def test_snapshot_store_expiry_and_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    import frp_master_connection.reporting.snapshot as module

    monkeypatch.setattr(module, "MAX_STORED_SNAPSHOT_BYTES", 10)
    store = ReportSnapshotStore()
    first = store.put("123456", now=1_000)
    second = store.put("abcdef", now=1_001)
    with pytest.raises(SnapshotError, match="unavailable"):
        store.get(first, now=1_002)
    assert store.get(second, now=1_002) == "abcdef"
    with pytest.raises(SnapshotError, match="unavailable"):
        store.get(second, now=2_000)
    with pytest.raises(SnapshotError, match="capacity"):
        store.put("12345678901", now=2_000)


@pytest.mark.parametrize(
    ("system", "expected"),
    [
        ("SI", ["1 in = 25.4 mm", "212 degF = 100 degC"]),
        ("US_CUSTOMARY", ["25.4 mm = 1 in", "100 degC = 212 degF"]),
    ],
)
def test_display_equivalents_use_native_values_without_rechecking(
    system: str,
    expected: list[str],
) -> None:
    quantities = (
        {"length": {"value": "1", "unit": "in"}, "temperature": {"value": "212", "unit": "degF"}}
        if system == "SI"
        else {
            "length": {"value": "25.4", "unit": "mm"},
            "temperature": {"value": "100", "unit": "degC"},
        }
    )
    rows = converted_quantity_rows(quantities, system)  # type: ignore[arg-type]
    assert [value for _, value in rows] == expected


def test_unknown_and_nonfinite_quantities_cannot_invent_equivalents() -> None:
    source = [
        {"value": "NaN", "unit": "in"},
        {"value": "3", "unit": "made-up"},
        {"value": "4", "unit": "1"},
    ]
    assert converted_quantity_rows(source, "SI") == []
    assert converted_quantity_rows(source, "INHERIT") == []


def test_identical_reused_list_has_one_value_and_an_explicit_native_reference() -> None:
    shared = [{"value": "3", "unit": "in"}]
    rows = dict(
        flatten_unique("record", {"first": shared, "second": shared}, minimum_alias_leaves=1)
    )
    assert rows["record.first[0]"] == "3 in"
    assert rows["record.second"].startswith("Identical native record at record.first")


def test_already_target_temperature_does_not_invent_a_conversion() -> None:
    assert converted_quantity_rows({"value": "100", "unit": "degC"}, "SI") == []
    assert converted_quantity_rows({"value": "212", "unit": "degF"}, "US_CUSTOMARY") == []


def _resign(token: str, change: object) -> str:
    version, packed, _ = token.split(".")
    raw = base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4))
    payload = json.loads(zlib.decompress(raw))
    change(payload)  # type: ignore[operator]
    changed = (
        base64.urlsafe_b64encode(
            zlib.compress(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), 9)
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    mac = (
        base64.urlsafe_b64encode(hmac.digest(b"r" * 32, changed.encode(), "sha256"))
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"{version}.{changed}.{mac}"


def test_snapshot_signing_rejects_weak_key_missing_identity_and_size_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import frp_master_connection.reporting.snapshot as module

    with pytest.raises(ValueError, match="at least 32 bytes"):
        SnapshotSigner(b"short")
    signer, token = _signed_token()
    with pytest.raises(ValueError, match="trusted account"):
        signer.issue(family="", kind="design", request={}, result={}, account_id="owner")
    with pytest.raises(ValueError, match="trusted account"):
        signer.issue(family="single-bolt", kind="design", request={}, result={}, account_id="")
    monkeypatch.setattr(module, "MAX_SNAPSHOT_JSON_BYTES", 30)
    with pytest.raises(SnapshotError, match="snapshot size"):
        signer.issue(family="single-bolt", kind="design", request={}, result={}, account_id="owner")
    monkeypatch.setattr(module, "MAX_SNAPSHOT_JSON_BYTES", 8_000_000)
    monkeypatch.setattr(module, "MAX_TOKEN_BYTES", 80)
    with pytest.raises(SnapshotError, match="transport size"):
        signer.issue(family="single-bolt", kind="design", request={}, result={}, account_id="owner")
    with pytest.raises(SnapshotError, match="transport size"):
        signer.verify(token, account_id="owner", now=1_001)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda payload: payload.update(version="R0"), "identity"),
        (lambda payload: payload.update(account_id="other"), "identity"),
        (lambda payload: payload.update(issued_at=1_100), "time"),
        (lambda payload: payload.update(content_sha256="0" * 64), "digest"),
        (lambda payload: payload.pop("content"), "invalid"),
    ],
)
def test_validly_signed_but_inconsistent_snapshot_is_rejected(change: object, message: str) -> None:
    signer, token = _signed_token()
    changed = _resign(token, change)
    with pytest.raises(SnapshotError, match=message):
        signer.verify(changed, account_id="owner", now=1_001)


def test_snapshot_expiry_and_incomplete_compressed_payload() -> None:
    signer, token = _signed_token()
    with pytest.raises(SnapshotError, match="expired"):
        signer.verify(token, account_id="owner", now=2_000)
    version, packed, _ = token.split(".")
    raw = base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4))[:-2]
    incomplete = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    mac = (
        base64.urlsafe_b64encode(hmac.digest(b"r" * 32, incomplete.encode(), "sha256"))
        .rstrip(b"=")
        .decode("ascii")
    )
    with pytest.raises(SnapshotError, match="incomplete"):
        signer.verify(f"{version}.{incomplete}.{mac}", account_id="owner", now=1_001)


def test_validly_signed_unsupported_content_shape_is_rejected() -> None:
    signer, token = _signed_token()

    def change(payload: dict[str, object]) -> None:
        content = payload["content"]
        assert isinstance(content, dict)
        content["kind"] = "bogus"
        payload["content_sha256"] = hashlib.sha256(
            json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()

    changed = _resign(token, change)
    with pytest.raises(SnapshotError, match="shape"):
        signer.verify(changed, account_id="owner", now=1_001)


@pytest.mark.parametrize(
    "body",
    [{}, {"report_snapshot": "x" * 80, "report_handle": "h" * 32}],
)
def test_export_requires_exactly_one_server_authority(body: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ExportRequest.model_validate(body)


def test_input_only_route_rejects_unknown_family_and_oversized_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import frp_master_connection.reporting.snapshot as snapshot_module

    async def run() -> tuple[httpx.Response, httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            unknown = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "unknown", "draft": {}},
            )
            monkeypatch.setattr(snapshot_module, "MAX_SNAPSHOT_JSON_BYTES", 80)
            oversized = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "clip-angle", "draft": {"length": "x" * 200}},
            )
            return unknown, oversized

    unknown, oversized = asyncio.run(run())
    assert unknown.status_code == 422
    assert oversized.status_code == 413


def test_unmapped_executed_check_is_a_report_failure_not_a_source_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import frp_master_connection.reporting.routes as routes_module

    def missing_adapter(*_: object) -> bytes:
        raise ReportingCoverageError("Executed check lacks a report adapter")

    monkeypatch.setattr(routes_module, "render_report_pdf", missing_adapter)

    async def run() -> httpx.Response:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            draft = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "clip-angle", "draft": {}},
            )
            return await client.post(
                "/api/v1/reports/export",
                json={"report_handle": draft.json()["report_handle"]},
            )

    result = asyncio.run(run())
    assert result.status_code == 422
    assert result.json()["detail"] == "Executed check lacks a report adapter"


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        ("exception", 503, "REPORT1 rendering failed"),
        ("timeout", 503, "REPORT1 rendering timed out"),
        ("oversized", 413, "REPORT1 PDF exceeds the export size limit"),
    ],
)
def test_render_failure_returns_no_partial_pdf(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_status: int,
    expected_detail: str,
) -> None:
    import time

    import frp_master_connection.reporting.routes as routes_module

    def renderer(*_: object) -> bytes:
        if failure == "exception":
            raise RuntimeError("internal path must stay private")
        if failure == "timeout":
            time.sleep(0.04)
        return b"%PDF-long"

    monkeypatch.setattr(routes_module, "render_report_pdf", renderer)
    if failure == "timeout":
        monkeypatch.setattr(routes_module, "MAX_RENDER_SECONDS", 0.005)
    if failure == "oversized":
        monkeypatch.setattr(routes_module, "MAX_PDF_BYTES", 4)

    async def run() -> httpx.Response:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            draft = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "clip-angle", "draft": {}},
            )
            return await client.post(
                "/api/v1/reports/export",
                json={"report_handle": draft.json()["report_handle"]},
            )

    result = asyncio.run(run())
    assert result.status_code == expected_status
    assert result.json()["detail"] == expected_detail
    assert "internal path" not in result.text
    assert result.headers["content-type"] == "application/json"


def test_render_queue_has_a_bounded_busy_response(monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    import frp_master_connection.reporting.routes as routes_module

    gate = threading.Event()
    both_started = threading.Event()
    counter_lock = threading.Lock()
    started = 0

    def renderer(*_: object) -> bytes:
        nonlocal started
        with counter_lock:
            started += 1
            if started == 2:
                both_started.set()
        gate.wait(timeout=2)
        return b"%PDF-queue-test"

    monkeypatch.setattr(routes_module, "render_report_pdf", renderer)
    monkeypatch.setattr(routes_module, "MAX_QUEUE_SECONDS", 0.01)

    async def run() -> tuple[list[httpx.Response], httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            draft = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={"family": "clip-angle", "draft": {}},
            )
            body = {"report_handle": draft.json()["report_handle"]}
            first = asyncio.create_task(client.post("/api/v1/reports/export", json=body))
            second = asyncio.create_task(client.post("/api/v1/reports/export", json=body))
            try:
                assert await asyncio.to_thread(both_started.wait, 1)
                busy = await client.post("/api/v1/reports/export", json=body)
            finally:
                gate.set()
            return list(await asyncio.gather(first, second)), busy

    accepted, busy = asyncio.run(run())
    assert [response.status_code for response in accepted] == [200, 200]
    assert busy.status_code == 503
    assert busy.json()["detail"] == "REPORT1 renderer is busy; try again"
