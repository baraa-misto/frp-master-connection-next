"""Stage 3.3A strict stateless HTTP and transport mapping tests."""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

import frp_master_connection.api.clip_angle_mapping as mapping
import frp_master_connection.api.routes as routes
from frp_master_connection.api.app import create_app
from frp_master_connection.api.clip_angle_mapping import (
    map_clip_angle_request,
    serialize_clip_angle_design,
    serialize_clip_angle_preview,
)
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application import design_check_clip_angle, preview_clip_angle
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.security import TrustedIdentity
from tests.clip_angle_fixtures import (
    build_clip_angle_c2_payload,
    build_clip_angle_payload,
    build_clip_angle_request,
)

PREVIEW_ROUTE = "/api/v1/calculations/clip-angle/preview"
DESIGN_ROUTE = "/api/v1/calculations/clip-angle/design-check"


@dataclass(slots=True)
class _Resolver:
    production_capable: bool = True
    calls: int = 0

    async def resolve(self) -> TrustedIdentity:
        self.calls += 1
        return TrustedIdentity("clip-angle-api-test", None, frozenset({"tester"}), "test")


def _app(resolver: _Resolver | None = None) -> FastAPI:
    return create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )


def _post(route: str, payload: dict[str, object], app: FastAPI | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app() if app is None else app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(route, json=payload)

    return asyncio.run(send())


def test_mapping_preserves_exact_dimensions_profiles_and_independent_groups() -> None:
    request = map_clip_angle_request(
        ClipAngleConnectorRequestDTO.model_validate(build_clip_angle_payload())
    )

    assert request.connector_dimensions.connected_leg_width == Decimal(4)
    assert request.connected_member_profile.family.value == "FLAT_PLATE"
    assert request.interface_a_layout == request.interface_b_layout
    assert request.interface_a_layout is not request.interface_b_layout
    assert request.bolt_diameter == PhysicalQuantity.of("0.5", Unit.IN)


def test_si_mapping_retains_exact_physical_fixture() -> None:
    request = map_clip_angle_request(
        ClipAngleConnectorRequestDTO.model_validate(build_clip_angle_payload(unit_system="SI"))
    )
    result = preview_clip_angle(request)

    assert request.connector_dimensions.connector_length == Decimal("203.2")
    assert request.bolt_diameter.unit is Unit.MM
    assert result.interface_a.placement.width_coordinates[0].magnitude == Decimal("31.75")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("connector_material", "METAL", "PULTRUDED_FRP"),
        ("fastener_material", "FRP", "STAINLESS_STEEL_316"),
        ("fastener_snapshot_id", "invented", "ASTM_F593"),
        ("request_id", " ", "nonempty"),
        ("connected_member_inclination_degrees", "nan", "finite"),
        ("connected_member_inclination_degrees", "91", "-90 through 90"),
    ],
)
def test_strict_dto_rejects_unapproved_identity_and_invalid_inclination(
    field: str,
    value: str,
    message: str,
) -> None:
    payload = build_clip_angle_payload()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        ClipAngleConnectorRequestDTO.model_validate(payload)


def test_strict_dto_rejects_extra_fields_round_profile_and_invalid_layout_modes() -> None:
    payload = build_clip_angle_payload()
    payload["client_fingerprint"] = "forged"
    with pytest.raises(ValidationError, match="Extra inputs"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload = build_clip_angle_payload()
    profile = payload["connected_member_profile"]
    assert isinstance(profile, dict)
    profile["profile_family"] = "ROUND_HOLLOW_SECTION"
    with pytest.raises(ValidationError):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload = build_clip_angle_payload()
    layout = payload["interface_a_layout"]
    assert isinstance(layout, dict)
    layout["row_count"] = 0
    with pytest.raises(ValidationError, match="positive integers"):
        ClipAngleConnectorRequestDTO.model_validate(payload)
    layout["row_count"] = 2
    layout["length_offset"] = {"value": "0", "unit": "in"}
    with pytest.raises(ValidationError, match="forbids group offsets"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    layout["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
    layout.pop("length_offset")
    with pytest.raises(ValidationError, match="requires length_offset"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    layout["length_offset"] = {"value": "0", "unit": "in"}
    layout["width_offset"] = {"value": "0", "unit": "in"}
    assert ClipAngleConnectorRequestDTO.model_validate(payload).interface_a_layout.length_offset


def test_trim_transport_pair_is_strict() -> None:
    payload = build_clip_angle_payload()
    payload["connected_member_end_trim_enabled"] = True
    with pytest.raises(ValidationError, match="requires connected_member_end_clearance"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload = build_clip_angle_payload()
    payload["connected_member_end_clearance"] = {"value": "0.25", "unit": "in"}
    with pytest.raises(ValidationError, match="forbidden"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload["connected_member_end_trim_enabled"] = True
    assert ClipAngleConnectorRequestDTO.model_validate(payload).connected_member_end_trim_enabled


def test_blank_profile_id_and_non_decimal_inclination_are_rejected() -> None:
    payload = build_clip_angle_payload()
    profile = payload["connected_member_profile"]
    assert isinstance(profile, dict)
    profile["profile_id"] = " "
    with pytest.raises(ValidationError, match="profile_id must be nonempty"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload = build_clip_angle_payload()
    payload["connected_member_inclination_degrees"] = "not-decimal"
    with pytest.raises(ValidationError, match="exact decimal string"):
        ClipAngleConnectorRequestDTO.model_validate(payload)

    payload = build_clip_angle_payload()
    payload["connected_member_inclination_degrees"] = "25"
    assert (
        ClipAngleConnectorRequestDTO.model_validate(payload).connected_member_inclination_degrees
        == "25"
    )


def test_preview_and_design_serializers_are_deterministic_and_zero_preview_resistance() -> None:
    request = build_clip_angle_request()
    preview = serialize_clip_angle_preview(preview_clip_angle(request))
    design = serialize_clip_angle_design(design_check_clip_angle(request))

    assert preview.resistance_evaluated is False
    assert preview.ordinary_pass_allowed is False
    assert preview.result["connector_kind"] == "SINGLE_CLIP_ANGLE"
    assert design.connector_body_status == "NOT_EVALUATED"
    assert design.ordinary_pass_allowed is False
    assert serialize_clip_angle_preview(preview_clip_angle(request)) == preview
    assert serialize_clip_angle_design(design_check_clip_angle(request)) == design


def test_preview_and_design_routes_return_strict_deterministic_contracts() -> None:
    resolver = _Resolver()
    app = _app(resolver)
    preview = _post(PREVIEW_ROUTE, build_clip_angle_payload(), app)
    design = _post(DESIGN_ROUTE, build_clip_angle_payload(), app)

    assert preview.status_code == 200
    assert preview.json()["geometry_status"] == "VALID"
    assert preview.json()["geometry_invalid_reasons"] == []
    assert preview.json()["resistance_evaluated"] is False
    assert (
        preview.json()["result"]["visualization"]["interface_a_bolts"][0]["bolt_id"]
        == "CLIP-A-R1-B1"
    )
    assert design.status_code == 200
    assert design.json()["ordinary_pass_allowed"] is False
    assert design.json()["connector_body_status"] == "NOT_EVALUATED"
    assert resolver.calls == 2


@pytest.mark.parametrize(
    "support_target",
    [
        "W_COLUMN_FLANGE",
        "W_BEAM_FLANGE",
        "W_COLUMN_WEB",
        "CHANNEL_COLUMN_WEB",
        "ANGLE_COLUMN_LEG",
        "RECTANGULAR_HOLLOW_COLUMN_WALL",
        "SOLID_RECTANGULAR_COLUMN_FACE",
    ],
)
def test_c2_support_matrix_serializes_the_current_contract(support_target: str) -> None:
    payload = build_clip_angle_c2_payload(support_target=support_target)
    if support_target == "RECTANGULAR_HOLLOW_COLUMN_WALL":
        support = cast(dict[str, object], payload["support_profile"])
        support["width"] = {"value": "10", "unit": "in"}
    response = _post(
        PREVIEW_ROUTE,
        payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_transport_schema_version"] == "0.1.0-draft"
    assert body["orchestration_contract_version"] == "3.3C2-RC1"
    assert body["preview_schema_version"] == "0.1.0-draft"
    assert body["result"]["orchestration_contract_version"] == "3.3C2-RC1"
    assert body["result"]["support_target_id"] == support_target
    assert body["result"]["visualization"]["schema_version"] == "0.1.0-draft"


@pytest.mark.parametrize(
    ("profile_family", "connected_role"),
    [
        ("FLAT_PLATE", "BRACE"),
        ("ANGLE", "BEAM"),
        ("CHANNEL", "BRACE"),
        ("WIDE_FLANGE_I", "BEAM"),
        ("RECTANGULAR_HOLLOW_SECTION", "BRACE"),
        ("SOLID_RECTANGULAR_SECTION", "BEAM"),
    ],
)
def test_c2_connected_profile_matrix_serializes_the_current_contract(
    profile_family: str,
    connected_role: str,
) -> None:
    payload = build_clip_angle_c2_payload(connected_profile_family=profile_family)
    profile = cast(dict[str, object], payload["connected_member_profile"])
    profile["role"] = connected_role
    if profile_family == "WIDE_FLANGE_I":
        dimensions = cast(dict[str, object], profile["dimensions"])
        dimensions["depth"] = {"value": "10", "unit": "in"}
    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 200
    body = response.json()
    assert body["orchestration_contract_version"] == "3.3C2-RC1"
    assert body["result"]["orchestration_contract_version"] == "3.3C2-RC1"
    visualization = body["result"]["visualization"]
    assert visualization["connected_member_profile_family"] == profile_family
    assert visualization["connected_member_role"] == connected_role
    assert visualization["boxes"] or visualization["meshes"]


def test_c2_design_preserves_current_identity_and_unknown_future_contract_fails_closed() -> None:
    payload = build_clip_angle_c2_payload()
    design = _post(DESIGN_ROUTE, payload)
    assert design.status_code == 200
    assert design.json()["orchestration_contract_version"] == "3.3C2-RC1"
    assert design.json()["result"]["preview"]["orchestration_contract_version"] == "3.3C2-RC1"

    payload["orchestration_contract_version"] = "3.3C3-RC1"
    rejected = _post(PREVIEW_ROUTE, payload)
    assert rejected.status_code == 422


def test_r4_preview_route_serializes_trimmed_meshes_without_untrimmed_duplicates() -> None:
    payload = build_clip_angle_payload(profile_family="WIDE_FLANGE_I")
    payload["connected_member_inclination_degrees"] = "25"
    payload["connected_member_end_trim_enabled"] = True
    payload["connected_member_end_clearance"] = {"value": "0.5", "unit": "in"}
    connector = cast(dict[str, object], payload["connector_dimensions"])
    connector["connector_length"] = {"value": "6", "unit": "in"}
    layout = cast(dict[str, object], payload["interface_a_layout"])
    layout["heel_edge_distance"] = {"value": "1", "unit": "in"}
    profile = cast(dict[str, object], payload["connected_member_profile"])
    profile["dimensions"] = {
        "member_length": {"value": "8", "unit": "in"},
        "depth": {"value": "10", "unit": "in"},
        "flange_width": {"value": "8", "unit": "in"},
        "web_thickness": {"value": "0.5", "unit": "in"},
        "flange_thickness": {"value": "0.5", "unit": "in"},
    }

    response = _post(PREVIEW_ROUTE, payload)
    assert response.status_code == 200
    result = response.json()["result"]
    visualization = result["visualization"]
    assert visualization is not None
    assert not any(
        item["owner_id"] == "clip-angle-connected-member" for item in visualization["boxes"]
    )
    assert [item["physical_element_id"] for item in visualization["meshes"]] == [
        "WEB",
        "TOP_FLANGE",
        "BOTTOM_FLANGE",
    ]
    assert all(len(item["points"]) >= 12 for item in visualization["meshes"])
    trim = result["trim"]
    assert trim["cut_plane_id"] == "CLIP_ANGLE_CONNECTED_MEMBER_END_CUT_PLANE"
    assert trim["measured_plane_clearance"]["value"] == "0.5"
    assert trim["measured_plane_clearance"]["unit"] == "in"
    assert len(trim["fabricated_trim_edge_ids"]) == 3
    assert trim["minimum_hole_edge_clearance"]["value"] == "0.2185"
    assert trim["minimum_hole_edge_clearance"]["unit"] == "in"


def test_invalid_geometry_and_transport_fail_closed_with_422() -> None:
    payload = build_clip_angle_payload()
    dimensions = payload["connector_dimensions"]
    assert isinstance(dimensions, dict)
    thickness = dimensions["thickness"]
    assert isinstance(thickness, dict)
    thickness["value"] = "5"
    response = _post(PREVIEW_ROUTE, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_CLIP_ANGLE_MAPPING_INVALID"

    payload = build_clip_angle_payload()
    interface = payload["interface_a_layout"]
    assert isinstance(interface, dict)
    pitch = interface["pitch"]
    assert isinstance(pitch, dict)
    pitch["value"] = "not-decimal"
    assert _post(DESIGN_ROUTE, payload).status_code == 422


def test_r3_preview_api_separates_geometry_reasons_from_design_limitations() -> None:
    valid = _post(PREVIEW_ROUTE, build_clip_angle_payload(force=("0", "1", "0")))
    valid_body = valid.json()
    assert valid.status_code == 200
    assert valid_body["geometry_status"] == "VALID"
    assert valid_body["geometry_invalid_reasons"] == []
    assert valid_body["assembly_status"] == "NOT_EVALUATED"
    assert valid_body["design_check_ready"] is False
    assert valid_body["result"]["connector_body_status"] == "NOT_EVALUATED"

    invalid_payload = build_clip_angle_payload()
    interface = invalid_payload["interface_a_layout"]
    assert isinstance(interface, dict)
    heel = interface["heel_edge_distance"]
    assert isinstance(heel, dict)
    heel["value"] = "0.1"
    invalid = _post(PREVIEW_ROUTE, invalid_payload)
    invalid_body = invalid.json()
    assert invalid.status_code == 200
    assert invalid_body["geometry_status"] == "INVALID_GEOMETRY"
    assert invalid_body["geometry_invalid_reasons"] == [
        "INTERFACE_A_COMPLETE_HOLE_CONTAINMENT_INVALID"
    ]
    assert (
        "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED"
        not in (invalid_body["geometry_invalid_reasons"])
    )


def test_design_route_maps_canonical_application_failure_to_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid(_request: object) -> None:
        raise ValueError("controlled design mapping failure")

    monkeypatch.setattr(routes, "design_check_clip_angle", invalid)
    response = _post(DESIGN_ROUTE, build_clip_angle_payload())
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "CANONICAL_CLIP_ANGLE_MAPPING_INVALID",
        "message": "controlled design mapping failure",
    }


def test_openapi_registers_only_narrow_clip_angle_routes_and_fixed_sources() -> None:
    schema = _app().openapi()
    assert PREVIEW_ROUTE in schema["paths"]
    assert DESIGN_ROUTE in schema["paths"]
    request_schema = schema["components"]["schemas"]["ClipAngleConnectorRequestDTO"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["properties"]["connector_material"]["const"] == "PULTRUDED_FRP"
    assert request_schema["properties"]["fastener_material"]["const"] == "STAINLESS_STEEL_316"
    assert "/api/v1/calculations/tee-connector/preview" in schema["paths"]


def test_mapping_helpers_reject_invalid_units_and_serialize_supported_values() -> None:
    with pytest.raises(ValueError, match="length quantities"):
        mapping._length(QuantityDTO(value="1", unit=Unit.KIP), Unit.IN)
    with pytest.raises(ValueError, match="positive"):
        mapping._length(QuantityDTO(value="0", unit=Unit.IN), Unit.IN)
    assert mapping._length(QuantityDTO(value="25.4", unit=Unit.MM), Unit.IN) == Decimal(1)
    with pytest.raises(ValueError, match="positive"):
        mapping._length(QuantityDTO(value="-1", unit=Unit.IN), Unit.IN, allow_zero=True)
    assert mapping._serialize([Decimal(1)]) == ["1"]
    assert mapping._serialize({"value": Decimal(2)}) == {"value": "2"}
    assert mapping._serialize(1.25) == "1.25"

    signed = mapping._signed_length(QuantityDTO(value="-1", unit=Unit.IN), Unit.MM)
    assert signed == Decimal("-25.4")
    with pytest.raises(ValueError, match="length quantities"):
        mapping._signed_length(QuantityDTO(value="1", unit=Unit.KIP), Unit.IN)

    for family in ("WIDE_FLANGE_I", "RECTANGULAR_HOLLOW_SECTION"):
        payload = build_clip_angle_payload(profile_family=family)
        dto = ClipAngleConnectorRequestDTO.model_validate(payload)
        assert map_clip_angle_request(dto).connected_member_profile.family.value == family

    unsupported = SimpleNamespace(connected_member_profile=SimpleNamespace(dimensions=object()))
    with pytest.raises(TypeError, match="Unsupported"):
        mapping._profile(cast(Any, unsupported), Unit.IN)
