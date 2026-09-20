"""Strict Stage 3.5B stateless API and OpenAPI tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

import frp_master_connection.api.routes as calculation_routes
from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_side_lap_concrete_schemas import (
    DirectSideLapConcreteRequestDTO,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import MemberProfileFamily, MemberProfileSurfaceId
from tests.direct_side_lap_concrete_fixtures import build_direct_side_lap_concrete_payload


def _app() -> FastAPI:
    return create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_preview_and_design_are_deterministic_and_external_by_contract() -> None:
    payload = build_direct_side_lap_concrete_payload()
    preview = _post("/api/v1/calculations/direct-side-lap-concrete/preview", payload)
    repeated = _post("/api/v1/calculations/direct-side-lap-concrete/preview", payload)
    design = _post("/api/v1/calculations/direct-side-lap-concrete/design-check", payload)
    assert preview.status_code == repeated.status_code == design.status_code == 200
    assert preview.json() == repeated.json()
    assert preview.json()["resistance_evaluated"] is False
    assert preview.json()["result"]["external_anchor_handoff_json"]
    assert design.json()["ordinary_pass_allowed"] is False


def test_channel_flange_nonzero_user_moment_and_extra_identity_are_rejected() -> None:
    flange = build_direct_side_lap_concrete_payload()
    flange["connected_profile"]["selected_profile_surface"] = "FLANGE_POS_OUTER"
    assert _post("/api/v1/calculations/direct-side-lap-concrete/preview", flange).status_code == 422
    moment = build_direct_side_lap_concrete_payload()
    moment["user_moment_lsn"] = {"x": "1", "y": "0", "z": "0", "unit": "kip-in"}
    assert _post("/api/v1/calculations/direct-side-lap-concrete/preview", moment).status_code == 422
    identity = build_direct_side_lap_concrete_payload()
    identity["engineering_fingerprint"] = "client-authored"
    assert (
        _post("/api/v1/calculations/direct-side-lap-concrete/preview", identity).status_code == 422
    )


def test_invalid_overlap_is_engineering_200_and_request_is_not_mutated() -> None:
    payload = build_direct_side_lap_concrete_payload(side_lap_length="7")
    original = deepcopy(payload)
    response = _post("/api/v1/calculations/direct-side-lap-concrete/preview", payload)
    assert response.status_code == 200
    assert response.json()["geometry_status"] == "INVALID_GEOMETRY"
    assert response.json()["design_check_ready"] is False
    assert payload == original


def test_openapi_declares_only_the_two_new_stateless_routes() -> None:
    paths = _app().openapi()["paths"]
    assert paths["/api/v1/calculations/direct-side-lap-concrete/preview"]["post"]
    assert paths["/api/v1/calculations/direct-side-lap-concrete/design-check"]["post"]


def test_request_dto_validates_blank_identity_and_closed_profile_scope() -> None:
    blank = build_direct_side_lap_concrete_payload()
    blank["request_id"] = " "
    with pytest.raises(ValidationError, match="request_id must be nonempty"):
        DirectSideLapConcreteRequestDTO.model_validate(blank)

    def validate(family: MemberProfileFamily, surface: MemberProfileSurfaceId) -> None:
        candidate = cast(
            DirectSideLapConcreteRequestDTO,
            SimpleNamespace(
                connected_profile=SimpleNamespace(
                    profile_family=family,
                    selected_profile_surface=surface,
                )
            ),
        )
        validator = cast(
            Callable[[DirectSideLapConcreteRequestDTO], DirectSideLapConcreteRequestDTO],
            DirectSideLapConcreteRequestDTO.validate_profile_scope,
        )
        validator(candidate)

    with pytest.raises(ValueError, match="only Angle or Channel"):
        validate(MemberProfileFamily.WIDE_FLANGE_I, MemberProfileSurfaceId.WEB_POS_FACE)
    with pytest.raises(ValueError, match="CHANNEL_WEB_CONTACT_ONLY"):
        validate(MemberProfileFamily.CHANNEL, MemberProfileSurfaceId.FLANGE_POS_OUTER)
    with pytest.raises(ValueError, match="ANGLE_SELECTED_LEG_CONTACT_REQUIRED"):
        validate(MemberProfileFamily.ANGLE, MemberProfileSurfaceId.WEB_OUTER)


def test_design_mapping_failure_is_a_structured_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_mapping(_request: object) -> object:
        raise ValueError("controlled mapping failure")

    monkeypatch.setattr(
        calculation_routes,
        "design_check_direct_side_lap_concrete",
        fail_mapping,
    )
    response = _post(
        "/api/v1/calculations/direct-side-lap-concrete/design-check",
        build_direct_side_lap_concrete_payload(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "CANONICAL_DIRECT_SIDE_LAP_CONCRETE_MAPPING_INVALID",
        "message": "controlled mapping failure",
    }
