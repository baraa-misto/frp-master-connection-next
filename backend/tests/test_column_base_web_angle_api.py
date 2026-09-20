"""Strict Stage 3.5C stateless API, transport, and OpenAPI verification."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

import frp_master_connection.api.routes as calculation_routes
from frp_master_connection.api.app import create_app
from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
    serialize_column_base_web_angle_design,
    serialize_column_base_web_angle_preview,
)
from frp_master_connection.api.column_base_web_angle_schemas import (
    ColumnBaseWebAngleRequestDTO,
    ColumnBaseWebAngleSignedRequestDTO,
)
from frp_master_connection.application import (
    design_check_column_base_web_angles,
    preview_column_base_web_angles,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from tests.column_base_web_angle_fixtures import (
    build_column_base_signed_payload,
    build_column_base_web_angle_payload,
)


def _app() -> FastAPI:
    return create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_preview_and_design_routes_are_deterministic_stateless_and_external() -> None:
    payload = build_column_base_web_angle_payload()
    original = deepcopy(payload)
    preview = _post("/api/v1/calculations/column-base-web-angles/preview", payload)
    repeated = _post("/api/v1/calculations/column-base-web-angles/preview", payload)
    design = _post("/api/v1/calculations/column-base-web-angles/design-check", payload)
    assert preview.status_code == repeated.status_code == design.status_code == 200
    assert preview.json() == repeated.json()
    assert preview.json()["resistance_evaluated"] is False
    assert preview.json()["ordinary_pass_allowed"] is False
    assert preview.json()["external_design_required"] is True
    assert preview.json()["result"]["external_handoff_json"]
    assert design.json()["ordinary_pass_allowed"] is False
    assert payload == original


def test_invalid_geometry_is_engineering_200_but_uplift_and_client_authority_are_422() -> None:
    invalid = build_column_base_web_angle_payload()
    invalid["external_anchor"]["specified_embedment"] = {"value": "13", "unit": "in"}
    response = _post("/api/v1/calculations/column-base-web-angles/preview", invalid)
    assert response.status_code == 200
    assert response.json()["geometry_status"] == "INVALID_GEOMETRY"
    uplift = build_column_base_web_angle_payload(axial_compression="-1")
    assert _post("/api/v1/calculations/column-base-web-angles/preview", uplift).status_code == 422
    extra = build_column_base_web_angle_payload()
    extra["engineering_fingerprint"] = "client-authored"
    assert _post("/api/v1/calculations/column-base-web-angles/preview", extra).status_code == 422
    moment = build_column_base_web_angle_payload()
    moment["user_moment_s_t_l"] = {"x": "1", "y": "0", "z": "0", "unit": "kip-in"}
    assert _post("/api/v1/calculations/column-base-web-angles/preview", moment).status_code == 422


def test_request_dto_rejects_blank_identity_non_w_column_and_unequal_double_payload() -> None:
    blank = build_column_base_web_angle_payload()
    blank["request_id"] = " "
    with pytest.raises(ValidationError, match="request_id must be nonempty"):
        ColumnBaseWebAngleRequestDTO.model_validate(blank)
    non_w = build_column_base_web_angle_payload()
    non_w["column"]["profile_family"] = "CHANNEL"
    with pytest.raises(ValidationError):
        ColumnBaseWebAngleRequestDTO.model_validate(non_w)
    unequal = build_column_base_web_angle_payload()
    unequal["negative_angle"] = {"connector_length": {"value": "5.5", "unit": "in"}}
    with pytest.raises(ValidationError, match="Extra inputs"):
        ColumnBaseWebAngleRequestDTO.model_validate(unequal)


def test_mapping_serializers_and_openapi_are_exact() -> None:
    dto = ColumnBaseWebAngleRequestDTO.model_validate(build_column_base_web_angle_payload())
    request = map_column_base_web_angle_request(dto)
    preview = preview_column_base_web_angles(request)
    design = design_check_column_base_web_angles(request)
    preview_dto = serialize_column_base_web_angle_preview(preview)
    design_dto = serialize_column_base_web_angle_design(design)
    assert preview_dto.orchestration_contract_version == "3.5C-RC1"
    assert preview_dto.preview_schema_version == "0.1.0-draft"
    assert design_dto.required_check_status == "NOT_EVALUATED"
    paths = _app().openapi()["paths"]
    assert paths["/api/v1/calculations/column-base-web-angles/preview"]["post"]
    assert paths["/api/v1/calculations/column-base-web-angles/design-check"]["post"]


def test_signed_successor_routes_are_strict_deterministic_and_publish_discriminator() -> None:
    payload = build_column_base_signed_payload(signed_axial_force="20")
    preview = _post("/api/v1/calculations/column-base-web-angles/preview", payload)
    repeated = _post("/api/v1/calculations/column-base-web-angles/preview", payload)
    design = _post("/api/v1/calculations/column-base-web-angles/design-check", payload)
    assert preview.status_code == repeated.status_code == design.status_code == 200
    assert preview.json() == repeated.json()
    assert preview.json()["orchestration_contract_version"] == "3.5C-R2-RC1"
    assert preview.json()["result"]["component_transfer"]["axial_mode"] == "UPLIFT"
    assert design.json()["orchestration_contract_version"] == "3.5C-R2-RC1"
    schema = _app().openapi()["components"]["schemas"]
    assert "ColumnBaseWebAngleSignedRequestDTO" in schema
    request_body = _app().openapi()["paths"]["/api/v1/calculations/column-base-web-angles/preview"][
        "post"
    ]["requestBody"]["content"]["application/json"]["schema"]
    assert request_body["discriminator"]["propertyName"] == "orchestration_contract_version"


def test_signed_successor_rejects_historical_axial_extra_blank_id_and_unknown_version() -> None:
    both = build_column_base_signed_payload()
    both["axial_compression"] = {"value": "20", "unit": "kip"}
    assert _post("/api/v1/calculations/column-base-web-angles/preview", both).status_code == 422
    historical_with_signed = build_column_base_web_angle_payload()
    historical_with_signed["signed_axial_force"] = {"value": "-20", "unit": "kip"}
    assert (
        _post(
            "/api/v1/calculations/column-base-web-angles/preview", historical_with_signed
        ).status_code
        == 422
    )
    blank = build_column_base_signed_payload()
    blank["request_id"] = " "
    with pytest.raises(ValidationError, match="request_id must be nonempty"):
        ColumnBaseWebAngleSignedRequestDTO.model_validate(blank)
    unknown = build_column_base_signed_payload()
    unknown["orchestration_contract_version"] = "3.5C-R3-DRAFT"
    assert _post("/api/v1/calculations/column-base-web-angles/preview", unknown).status_code == 422


@pytest.mark.parametrize(
    "route_name", ["preview_column_base_web_angles", "design_check_column_base_web_angles"]
)
def test_route_mapping_failures_are_structured_422(
    monkeypatch: pytest.MonkeyPatch, route_name: str
) -> None:
    def fail_mapping(_request: object) -> object:
        raise ValueError("controlled Stage 3.5C mapping failure")

    monkeypatch.setattr(calculation_routes, route_name, fail_mapping)
    suffix = "preview" if route_name.startswith("preview") else "design-check"
    response = _post(
        f"/api/v1/calculations/column-base-web-angles/{suffix}",
        build_column_base_web_angle_payload(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "CANONICAL_COLUMN_BASE_WEB_ANGLE_MAPPING_INVALID",
        "message": "controlled Stage 3.5C mapping failure",
    }
