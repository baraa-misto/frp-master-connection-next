"""Defensive SAB2 boundary, authentication, renderer and source-path proofs."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Literal, cast

import httpx
import pytest
from tests.api.test_direct_two_bolt import quantity, sab2_body
from tests.api.test_mat1_routes import call

import frp_master_connection.api.direct_two_bolt as api
import frp_master_connection.application.direct_two_bolt_source as source
import frp_master_connection.reporting.direct_two_bolt as renderer
from frp_master_connection.api.app import create_app
from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application.connection_preview import preview_single_bolt_connection
from frp_master_connection.application.direct_support_ends import DirectSupportEndCondition
from frp_master_connection.application.multirow_orchestration import (
    DirectMultiRowPreviewResult,
    MultiRowOrchestrationRequest,
    preview_multirow_connection,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.reporting.pdf import _font_setup
from frp_master_connection.reporting.snapshot import ReportSnapshot, SnapshotError


@pytest.mark.parametrize("change", ["unmarked", "no-physical", "channel", "hole-small"])
def test_new_scope_rejects_unsupported_structural_contracts(change: str) -> None:
    body = sab2_body()
    body.pop("material_request")
    if change == "unmarked":
        body["legacy"].pop("direct_finalization_contract_version")
    elif change == "no-physical":
        body["legacy"]["physical_connection"] = None
    elif change == "channel":
        member = body["legacy"]["physical_connection"]["joint_assembly"]["members"][1]
        member["section"]["kind"] = "CHANNEL"
    else:
        body["hole_diameter"] = quantity(".49")
    assert call("POST", "/api/v1/direct-two-bolt/preview", body).status_code == 422


def test_quantity_and_unmarked_optional_material_view_identity() -> None:
    with pytest.raises(ValueError, match="in or mm"):
        api.inches(QuantityDTO.model_validate({"value": "1", "unit": "kip"}))
    body = sab2_body()
    body.pop("material_request")
    first = api.fingerprint(api.TwoBoltRequestDTO.model_validate(body))
    body["legacy"]["display_unit_system"] = "SI"
    body["revision"] = "ONLY-VIEW"
    assert api.fingerprint(api.TwoBoltRequestDTO.model_validate(body)) == first


def test_defensive_typed_contract_guards_and_geometry_error_on_both_routes() -> None:
    dto = api.TwoBoltRequestDTO.model_validate(sab2_body()).model_copy(
        update={"material_request": None}
    )
    for change in ({"direct_finalization_contract_version": None}, {"physical_connection": None}):
        invalid = dto.model_copy(update={"legacy": dto.legacy.model_copy(update=change)})
        with pytest.raises(ValueError, match=r"accepted physical|actual Angle"):
            cast(Callable[[], api.TwoBoltRequestDTO], invalid.validate_scope)()
        assert len(api.fingerprint(invalid)) == 64
    changed = dto.model_copy(deep=True)
    assert changed.legacy.physical_connection is not None
    object.__setattr__(
        changed.legacy.physical_connection.joint_assembly.members[0].section, "kind", "CHANNEL"
    )
    with pytest.raises(ValueError, match="actual Angle"):
        cast(Callable[[], api.TwoBoltRequestDTO], changed.validate_scope)()
    body = sab2_body(
        hardware=[
            {
                "kind": "HEAD",
                "radius": quantity("-1"),
                "axial_start": quantity("1"),
                "axial_end": quantity("2"),
                "source": "Invalid negative radius control",
            }
        ]
    )
    for route in ("preview", "design-check"):
        response = call("POST", "/api/v1/direct-two-bolt/" + route, body)
        assert response.status_code == 422
        assert "cylinder" in response.text


def mapped() -> MultiRowOrchestrationRequest:
    return map_multirow_request(api.TwoBoltRequestDTO.model_validate(sab2_body()).legacy)


def test_geometry_source_no_caller_crops_and_actual_end_authority() -> None:
    request = replace(mapped(), connection_view_extents=None)
    visual, ends = source.unmapped_geometry_source(request)
    assert len(visual.physical_bolts) == 2
    assert visual.physical_connection.bolt.holes[0].participant_id == "member-a"
    assert ends.actual_end(True) is None
    assert ends.actual_end(False) is None
    _, absent = source.unmapped_geometry_source(
        replace(request, supporting_w_longitudinal_ends=None)
    )
    assert absent.condition.value == "UNSPECIFIED"
    assert request.supporting_w_longitudinal_ends is not None
    declaration = replace(
        request.supporting_w_longitudinal_ends,
        condition=DirectSupportEndCondition.FINITE_BOTH_ENDS,
        negative_end_distance=PhysicalQuantity.of("5", Unit.IN),
        positive_end_distance=PhysicalQuantity.of("7", Unit.IN),
    )
    _, finite = source.unmapped_geometry_source(
        replace(request, supporting_w_longitudinal_ends=declaration)
    )
    assert finite.positive is not None
    assert finite.negative is not None
    assert finite.positive - finite.negative == 12


def test_unresolved_source_geometry_fails_without_relaxing_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = mapped()
    invalid = deepcopy(request)
    object.__setattr__(invalid, "physical_connection_request", None)
    with pytest.raises(ValueError, match="Typed physical"):
        source.unmapped_geometry_source(invalid)
    assert request.physical_connection_request is not None
    original = preview_single_bolt_connection(request.physical_connection_request)
    monkeypatch.setattr(
        source,
        "preview_single_bolt_connection",
        lambda *args: replace(original, visualization=None),
    )
    with pytest.raises(ValueError, match="Physical geometry"):
        source.unmapped_geometry_source(replace(request, connection_view_extents=None))
    with pytest.raises(ValueError, match="ordered two-member"):
        source.unmapped_geometry_source(request)


def test_corrupt_physical_station_and_missing_end_authority_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dto = api.TwoBoltRequestDTO.model_validate(sab2_body())
    native = preview_multirow_connection(map_multirow_request(dto.legacy))
    assert isinstance(native, DirectMultiRowPreviewResult)
    assert native.visualization is not None
    monkeypatch.setattr(
        api,
        "preview_multirow_connection",
        lambda _: replace(native, visualization=replace(native.visualization, physical_bolts=())),
    )
    with pytest.raises(ValueError, match="Both physical"):
        api.resolve_geometry(dto)
    second = native.visualization.physical_bolts[1]
    center = second.display.center
    corrupted = replace(
        second, display=replace(second.display, center=replace(center, x=center.x + 1))
    )
    monkeypatch.setattr(
        api,
        "preview_multirow_connection",
        lambda _: replace(
            native,
            visualization=replace(
                native.visualization,
                physical_bolts=(native.visualization.physical_bolts[0], corrupted),
            ),
        ),
    )
    with pytest.raises(ValueError, match="governed brace frame"):
        api.resolve_geometry(dto)
    monkeypatch.setattr(
        api,
        "preview_multirow_connection",
        lambda _: replace(native, direct_support_end_authority=None),
    )
    with pytest.raises(ValueError, match="end authority"):
        api.resolve_geometry(dto)


@pytest.mark.parametrize("mode", ["busy", "timeout", "failed", "oversize", "cancelled"])
def test_bounded_renderer_failures_release_slots_without_producing_approval(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    if mode == "busy":
        monkeypatch.setattr(api, "MAX_CONCURRENT_REPORTS", 0)
        monkeypatch.setattr(api, "MAX_QUEUE_SECONDS", 0.001)
    if mode == "timeout":
        monkeypatch.setattr(api, "MAX_RENDER_SECONDS", 0.001)
    monkeypatch.setattr(api, "MAX_PDF_BYTES", 3)

    def render(_: object) -> bytes:
        if mode == "failed":
            raise ValueError("Deliberate renderer failure")
        if mode == "timeout":
            time.sleep(0.02)
        if mode == "cancelled":
            raise asyncio.CancelledError()
        return b"%PDF"

    monkeypatch.setattr(renderer, "render_geometry_review", render)
    body = sab2_body(alignment="SUPPORT")

    async def run() -> None:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            data = (await client.post("/api/v1/direct-two-bolt/preview", json=body)).json()
            export = {"report_handle": data["geometry_report_handle"], "current_request": body}
            if mode == "cancelled":
                with pytest.raises(RuntimeError, match="No response returned"):
                    await client.post("/api/v1/direct-two-bolt/geometry-review", json=export)
            else:
                response = await client.post("/api/v1/direct-two-bolt/geometry-review", json=export)
                assert response.status_code == (413 if mode == "oversize" else 503)
                assert (
                    mode.split("d")[0] in response.text
                    or "size limit" in response.text
                    or "timed out" in response.text
                )
            await asyncio.sleep(0.04)

    asyncio.run(run())


def test_geometry_export_rejects_another_account_and_another_snapshot_family() -> None:
    body = sab2_body()

    async def run() -> None:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            for family, account in (
                ("direct-sab2-geometry", "other-account"),
                ("multi-row", "local-development-account"),
            ):
                token = app.state.report_signer.issue(
                    family=family,
                    kind="input_only",
                    request=body,
                    result=api.geometry_response(api.TwoBoltRequestDTO.model_validate(body)),
                    account_id=account,
                )
                handle = app.state.report_snapshot_store.put(token)
                response = await client.post(
                    "/api/v1/direct-two-bolt/geometry-review",
                    json={"report_handle": handle, "current_request": body},
                )
                assert response.status_code == 409

    asyncio.run(run())


def test_renderer_refuses_structural_snapshot_and_clips_oblique_cut_line() -> None:
    for family, kind in (("multi-row", "input_only"), ("direct-sab2-geometry", "design")):
        with pytest.raises(SnapshotError, match="own authenticated"):
            renderer.render_geometry_review(
                ReportSnapshot(
                    family, cast(Literal["input_only", "design"], kind), {}, {}, 0, "digest"
                )
            )
    data = api.geometry_response(api.TwoBoltRequestDTO.model_validate(sab2_body()))
    _font_setup()
    face = data["pair_input"]["faces"][0]
    for limit in ("2", "100"):
        changed = deepcopy(data)
        changed["pair_input"]["faces"][0]["boundaries"].append(
            {
                "a": "1",
                "b": "1",
                "limit": limit,
                "id": "DRAWING-CUT",
                "role": "PHYSICAL_END_OR_SIDE",
            }
        )
        drawing = renderer.face_drawing(changed, 0)
        assert drawing.width == 490
    assert face["boundaries"] == data["pair_input"]["faces"][0]["boundaries"]


def test_fully_cut_prism_is_absent_without_dropping_other_members() -> None:
    body = sab2_body(
        end_cuts=[
            {
                "member_id": "member-a",
                "polygon": [
                    [quantity("20"), quantity("20")],
                    [quantity("21"), quantity("20")],
                    [quantity("21"), quantity("21")],
                    [quantity("20"), quantity("21")],
                ],
                "source": "Explicit no physical overlap control",
            }
        ]
    )
    result = api.geometry_response(api.TwoBoltRequestDTO.model_validate(body))
    assert result["geometry"]["aggregate_state"] == "DOES_NOT_FIT"
    assert not any(
        p["owner_id"] == "member-a" and p["kind"] in {"BOX", "TRIANGLE_MESH"}
        for p in result["visualization"]["physical_connection"]["primitives"]
    )
    assert any(
        p["owner_id"] == "member-b"
        for p in result["visualization"]["physical_connection"]["primitives"]
    )
