"""Strict Stage 3.5A stateless API and OpenAPI tests."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from frp_master_connection.api.app import create_app
from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    map_beam_concrete_paired_angle_request,
    serialize_beam_concrete_paired_angle_design,
    serialize_beam_concrete_paired_angle_preview,
)
from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.application import (
    design_check_beam_concrete_paired_angle,
    preview_beam_concrete_paired_angle,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from tests.beam_concrete_paired_angle_fixtures import (
    build_beam_concrete_paired_angle_payload,
)


def _app() -> FastAPI:
    return create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


@pytest.mark.parametrize("unit_system", ["US_CUSTOMARY", "SI"])
def test_preview_and_design_routes_are_strict_stateless_and_deterministic(unit_system: str) -> None:
    payload = build_beam_concrete_paired_angle_payload(unit_system=unit_system)
    preview = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    repeated = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    design = _post("/api/v1/calculations/beam-concrete-paired-angle/design-check", payload)
    assert preview.status_code == repeated.status_code == design.status_code == 200
    assert preview.json() == repeated.json()
    assert preview.json()["resistance_evaluated"] is False
    assert preview.json()["external_design_required"] is True
    assert design.json()["ordinary_pass_allowed"] is False
    assert design.json()["required_check_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "profile_family",
    [
        "FLAT_PLATE",
        "ANGLE",
        "CHANNEL",
        "WIDE_FLANGE_I",
        "RECTANGULAR_HOLLOW_SECTION",
        "SOLID_RECTANGULAR_SECTION",
    ],
)
def test_successor_preview_route_exposes_all_profiles_and_one_by_one_external_handoff(
    profile_family: str,
) -> None:
    payload = build_beam_concrete_paired_angle_payload(
        contract_version="3.5A-R1-RC1", profile_family=profile_family
    )
    response = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    assert response.status_code == 200
    body = response.json()
    assert body["orchestration_contract_version"] == "3.5A-R1-RC1"
    assert body["geometry_status"] == "VALID"
    result = body["result"]
    assert len(result["positive_wall_group"]["anchors"]) == 1
    assert len(result["negative_wall_group"]["anchors"]) == 1
    assert result["positive_wall_group"]["nominal_demand"] is None
    assert result["negative_wall_group"]["nominal_demand"] is None
    assert result["external_design_required"] is True
    assert result["resistance_evaluated"] is False


def test_mapping_and_serialization_preserve_backend_handoff_verbatim() -> None:
    dto = BeamConcretePairedAngleRequestDTO.model_validate(
        build_beam_concrete_paired_angle_payload()
    )
    request = map_beam_concrete_paired_angle_request(dto)
    preview = serialize_beam_concrete_paired_angle_preview(
        preview_beam_concrete_paired_angle(request)
    )
    design = serialize_beam_concrete_paired_angle_design(
        design_check_beam_concrete_paired_angle(request)
    )
    assert (
        preview.result["external_anchor_handoff_json"]
        == preview_beam_concrete_paired_angle(request).external_anchor_handoff_json
    )
    assert preview.application_fingerprint == preview.result["application_fingerprint"]
    assert design.result_fingerprint == design.result["result_fingerprint"]


@pytest.mark.parametrize(
    ("major", "minor", "axial", "mode"),
    [
        ("-4", "0", "0", "BRANCH_RESOLVED"),
        ("0", "0", "4", "BRANCH_RESOLVED"),
        ("0", "2", "0", "COMBINED_LAYOUT"),
        ("-4", "2", "3", "COMBINED_LAYOUT"),
    ],
)
def test_r2_three_component_routes_preserve_authoritative_handoff_modes(
    major: str, minor: str, axial: str, mode: str
) -> None:
    payload = build_beam_concrete_paired_angle_payload(
        contract_version="3.5A-R2-RC1",
        major_shear=major,
        minor_shear=minor,
        axial_force=axial,
    )
    preview = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    design = _post("/api/v1/calculations/beam-concrete-paired-angle/design-check", payload)
    assert preview.status_code == design.status_code == 200
    body = preview.json()
    assert body["orchestration_contract_version"] == "3.5A-R2-RC1"
    assert body["result"]["handoff_mode"] == mode
    assert body["result"]["external_anchor_handoff"]["handoff_mode"] == mode
    for component in ("h", "v", "n"):
        assert body["result"]["visualization"]["user_moment_hvn"][component]["value"] == "0"
        assert body["result"]["visualization"]["user_moment_hvn"][component]["unit"] == "kip-in"
    if mode == "COMBINED_LAYOUT":
        assert body["result"]["positive_wall_group"]["wrench"] is None
        assert body["result"]["negative_wall_group"]["wrench"] is None
        assert body["result"]["branch_allocation_status"] == "NOT_EVALUATED"
    else:
        assert body["result"]["positive_wall_group"]["wrench"]
        assert body["result"]["negative_wall_group"]["wrench"]


def test_r2_api_rejects_historical_force_fields_and_nonzero_user_moment() -> None:
    payload = build_beam_concrete_paired_angle_payload(contract_version="3.5A-R2-RC1")
    payload["reaction_shear"] = {"value": "-4", "unit": "kip"}
    assert (
        _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload).status_code == 422
    )
    payload = build_beam_concrete_paired_angle_payload(contract_version="3.5A-R2-RC1")
    payload["user_moment_hvn"]["y"] = "1"
    response = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    assert response.status_code == 422
    assert "STAGE_3_5A_USER_APPLIED_MOMENT_NOT_ALLOWED" in response.text


def test_blank_request_id_and_nonforce_reaction_fail_at_strict_boundaries() -> None:
    blank = build_beam_concrete_paired_angle_payload()
    blank["request_id"] = " "
    with pytest.raises(ValidationError, match="request_id"):
        BeamConcretePairedAngleRequestDTO.model_validate(blank)

    nonforce = build_beam_concrete_paired_angle_payload()
    nonforce["reaction_shear"] = {"value": "1", "unit": "in"}
    dto = BeamConcretePairedAngleRequestDTO.model_validate(nonforce)
    with pytest.raises(ValueError, match="force"):
        map_beam_concrete_paired_angle_request(dto)
    response = _post(
        "/api/v1/calculations/beam-concrete-paired-angle/design-check",
        nonforce,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "CANONICAL_BEAM_CONCRETE_PAIRED_ANGLE_MAPPING_INVALID"
    )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            lambda value: value["user_moment_hvn"].update({"x": "1"}),
            "STAGE_3_5A_USER_APPLIED_MOMENT_NOT_ALLOWED",
        ),
        (
            lambda value: value["user_force_hvn"].update({"x": "1"}),
            "STAGE_3_5A_ONLY_VERTICAL_REACTION_SHEAR_ALLOWED",
        ),
        (
            lambda value: value["user_force_hvn"].update({"z": "1"}),
            "STAGE_3_5A_ONLY_VERTICAL_REACTION_SHEAR_ALLOWED",
        ),
        (lambda value: value["beam_end_gap"].update({"value": "-0.1"}), "beam_end_gap"),
    ],
)
def test_disallowed_actions_and_negative_gap_are_rejected(mutation: object, reason: str) -> None:
    payload = build_beam_concrete_paired_angle_payload()
    mutation(payload)  # type: ignore[operator]
    response = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    assert response.status_code == 422
    assert reason in response.text


def test_wrong_profile_unequal_group_shape_extra_fields_and_client_identity_are_rejected() -> None:
    cases: list[dict[str, object]] = []
    wrong = build_beam_concrete_paired_angle_payload()
    wrong["beam_profile"]["profile_family"] = "CHANNEL"
    cases.append(wrong)
    unequal = build_beam_concrete_paired_angle_payload()
    unequal["positive_wall_anchor_pattern"] = deepcopy(unequal["wall_anchor_pattern"])
    cases.append(unequal)
    identity = build_beam_concrete_paired_angle_payload()
    identity["engineering_fingerprint"] = "client-authored"
    cases.append(identity)
    version = build_beam_concrete_paired_angle_payload()
    version["orchestration_contract_version"] = "3.5B-RC1"
    cases.append(version)
    for payload in cases:
        with pytest.raises(ValidationError):
            BeamConcretePairedAngleRequestDTO.model_validate(payload)


def test_openapi_exposes_only_declared_stage_3_5a_routes_without_pass_schema() -> None:
    schema = _app().openapi()
    paths = schema["paths"]
    preview = paths["/api/v1/calculations/beam-concrete-paired-angle/preview"]["post"]
    design = paths["/api/v1/calculations/beam-concrete-paired-angle/design-check"]["post"]
    assert preview["requestBody"]["required"] is True
    assert design["responses"]["200"]
    text = str(
        {preview["summary"]: preview["description"], design["summary"]: design["description"]}
    ).lower()
    assert "concrete" in text
    assert "external" in text
    assert "ordinary pass" in text


def test_route_does_not_mutate_request_and_invalid_geometry_is_engineering_200() -> None:
    payload = build_beam_concrete_paired_angle_payload()
    original = deepcopy(payload)
    first = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    assert payload == original
    assert first.status_code == 200
    payload["wall"]["width"]["value"] = "6"
    invalid = _post("/api/v1/calculations/beam-concrete-paired-angle/preview", payload)
    assert invalid.status_code == 200
    assert invalid.json()["geometry_status"] == "INVALID_GEOMETRY"
    assert invalid.json()["design_check_ready"] is False
