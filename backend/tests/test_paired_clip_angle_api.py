"""Strict Stage 3.3B paired clip-angle API tests."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from frp_master_connection.api.app import create_app
from frp_master_connection.api.paired_clip_angle_mapping import (
    map_paired_clip_angle_request,
    serialize_paired_clip_angle_design,
    serialize_paired_clip_angle_preview,
)
from frp_master_connection.api.paired_clip_angle_schemas import (
    PairedClipAngleConnectorRequestDTO,
)
from frp_master_connection.application import (
    design_check_paired_clip_angle,
    preview_paired_clip_angle,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from tests.paired_clip_angle_fixtures import (
    build_paired_clip_angle_c3_payload,
    build_paired_clip_angle_payload,
)


def _app() -> FastAPI:
    return create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_preview_and_design_routes_are_stateless_and_deterministic() -> None:
    payload = build_paired_clip_angle_payload()
    preview = _post("/api/v1/calculations/paired-clip-angle/preview", payload)
    design = _post("/api/v1/calculations/paired-clip-angle/design-check", payload)
    assert preview.status_code == design.status_code == 200
    assert preview.json()["resistance_evaluated"] is False
    assert preview.json()["result"]["connector_kind"] == "SYMMETRIC_PAIRED_CLIP_ANGLES"
    assert design.json()["required_check_status"] == "NOT_EVALUATED"
    assert design.json()["ordinary_pass_allowed"] is False


@pytest.mark.parametrize("unit_system", ["US_CUSTOMARY", "SI"])
def test_c3_preview_and_design_routes_preserve_strict_new_contract(
    unit_system: str,
) -> None:
    payload = build_paired_clip_angle_c3_payload(unit_system=unit_system)
    preview = _post("/api/v1/calculations/paired-clip-angle/preview", payload)
    design = _post("/api/v1/calculations/paired-clip-angle/design-check", payload)
    assert preview.status_code == design.status_code == 200
    assert preview.json()["orchestration_contract_version"] == "3.3C3-RC1"
    assert preview.json()["result"]["support_target_id"] == "W_COLUMN_FLANGE"
    assert preview.json()["result"]["symmetry_proof"]["equal_sharing_eligible"] is False
    assert design.json()["orchestration_contract_version"] == "3.3C3-RC1"
    assert design.json()["required_check_status"] == "NOT_EVALUATED"


def test_mapping_and_serializers_match_routes() -> None:
    dto = PairedClipAngleConnectorRequestDTO.model_validate(build_paired_clip_angle_payload())
    request = map_paired_clip_angle_request(dto)
    preview = serialize_paired_clip_angle_preview(preview_paired_clip_angle(request))
    design = serialize_paired_clip_angle_design(design_check_paired_clip_angle(request))
    assert preview.request_id == design.request_id == request.request_id
    assert preview.engineering_fingerprint == preview.result["engineering_fingerprint"]
    assert design.result_fingerprint == design.result["result_fingerprint"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("unexpected", True),
        lambda value: value.__setitem__("pair_symmetry", "EDITABLE"),
        lambda value: value["connected_member_profile"].__setitem__(
            "selected_profile_surface", "FLANGE_POS_OUTER"
        ),
        lambda value: value.__setitem__(
            "connected_member_end_clearance", {"value": "0", "unit": "in"}
        ),
    ],
)
def test_strict_request_rejects_untrusted_or_inconsistent_fields(mutation: object) -> None:
    payload = deepcopy(build_paired_clip_angle_payload())
    mutation(payload)  # type: ignore[operator]
    with pytest.raises(ValidationError):
        PairedClipAngleConnectorRequestDTO.model_validate(payload)


@pytest.mark.parametrize(
    "field_value",
    [" ", "not-a-number", "NaN", "91"],
)
def test_request_identity_and_inclination_are_strict(field_value: str) -> None:
    payload = build_paired_clip_angle_payload()
    if field_value == " ":
        payload["request_id"] = field_value
    else:
        payload["connected_member_inclination_degrees"] = field_value
    with pytest.raises(ValidationError):
        PairedClipAngleConnectorRequestDTO.model_validate(payload)


def test_mapping_error_is_http_422() -> None:
    payload = build_paired_clip_angle_payload()
    payload["hole_diameter"] = {"value": "0.4", "unit": "in"}
    response = _post("/api/v1/calculations/paired-clip-angle/preview", payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_PAIRED_CLIP_ANGLE_MAPPING_INVALID"


def test_design_mapping_error_is_http_422() -> None:
    payload = build_paired_clip_angle_payload()
    payload["hole_diameter"] = {"value": "0.4", "unit": "in"}
    response = _post("/api/v1/calculations/paired-clip-angle/design-check", payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_PAIRED_CLIP_ANGLE_MAPPING_INVALID"


def test_symmetry_violation_is_http_200_engineering_not_evaluated() -> None:
    payload = build_paired_clip_angle_payload(force=("1", "0", "4"))
    response = _post("/api/v1/calculations/paired-clip-angle/design-check", payload)
    assert response.status_code == 200
    assert response.json()["assembly_status"] == "NOT_EVALUATED"
    assert response.json()["result"]["preview"]["geometry_status"] == "VALID"
