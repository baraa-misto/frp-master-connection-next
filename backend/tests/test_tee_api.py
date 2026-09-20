"""Stage 3.2 Tee stateless HTTP and strict mapping tests."""

import asyncio
from dataclasses import dataclass
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

import frp_master_connection.api.tee_mapping as tee_mapping
from frp_master_connection.api.app import create_app
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_design,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    design_check_tee_connector,
    preview_tee_connector,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.security import TrustedIdentity
from tests.tee_fixtures import (
    build_tee_c2_workspace_rhs_payload,
    build_tee_payload,
    build_tee_r2_payload,
    build_tee_r4_benchmark_payload,
    build_tee_r7_angle_payload,
    build_tee_r8_profile_wall_payload,
)

PREVIEW_ROUTE = "/api/v1/calculations/tee-connector/preview"
DESIGN_ROUTE = "/api/v1/calculations/tee-connector/design-check"


@dataclass(slots=True)
class _Resolver:
    production_capable: bool = True
    calls: int = 0

    async def resolve(self) -> TrustedIdentity:
        self.calls += 1
        return TrustedIdentity("tee-api-test", None, frozenset({"tester"}), "test")


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


def test_mapping_preserves_exact_server_owned_material_and_two_layouts() -> None:
    dto = TeeConnectorRequestDTO.model_validate(build_tee_payload())
    request = map_tee_connector_request(dto)

    assert request.request_id == "TEE-COLUMN-US_CUSTOMARY"
    assert request.connector_dimensions.stem_thickness == Decimal("0.375")
    assert request.interface_a_layout == request.interface_b_layout
    assert request.interface_a_layout is not request.interface_b_layout
    assert request.bolt_diameter.unit is Unit.IN


def test_si_mapping_converts_exact_dimensions_and_uses_si_transport() -> None:
    payload = build_tee_payload(
        role="BEAM",
        unit_system="SI",
        force=("0.44482216152605", "0", "0"),
    )
    request = map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))
    preview = preview_tee_connector(request)

    assert request.connector_dimensions.connector_length == Decimal("203.2")
    assert request.bolt_diameter.unit is Unit.MM
    assert preview.support_role.value == "BEAM"
    assert preview.interface_a.normal_component is not None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("connector_material", "CUSTOM_FRP"), "PULTRUDED_FRP"),
        (("fastener_material", "CUSTOM_FRP"), "STAINLESS_STEEL_316"),
        (("fastener_snapshot_id", "invented"), "ASTM_F593"),
        (("request_id", " "), "nonempty"),
    ],
)
def test_strict_dto_rejects_unapproved_or_empty_identity(
    mutation: tuple[str, str], message: str
) -> None:
    payload = build_tee_payload()
    payload[mutation[0]] = mutation[1]
    with pytest.raises(ValidationError, match=message):
        TeeConnectorRequestDTO.model_validate(payload)


def test_strict_dto_rejects_extra_fields_and_noninteger_layout_counts() -> None:
    payload = build_tee_payload()
    payload["client_authority"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        TeeConnectorRequestDTO.model_validate(payload)

    payload = build_tee_payload()
    payload["interface_a_layout"]["row_count"] = 0
    with pytest.raises(ValidationError, match="positive integers"):
        TeeConnectorRequestDTO.model_validate(payload)
    payload["interface_a_layout"]["row_count"] = "2"
    with pytest.raises(ValidationError, match="valid integer"):
        TeeConnectorRequestDTO.model_validate(payload)


def test_preview_and_design_serializers_are_deterministic() -> None:
    request = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(build_tee_payload(force=("0", "0", ".001")))
    )
    preview = serialize_tee_connector_preview(preview_tee_connector(request))
    design = serialize_tee_connector_design(design_check_tee_connector(request))

    assert preview.api_transport_schema_version == "0.1.0-draft"
    assert preview.resistance_evaluated is False
    dimensions = preview.result["connector_dimensions"]
    assert isinstance(dimensions, dict)
    assert dimensions["connector_length"] == "8"
    assert design.tee_body_resistance_status == "NOT_EVALUATED"
    assert design.ordinary_pass_allowed is False
    assert design.supported_interface_failure_present is False
    assert serialize_tee_connector_preview(preview_tee_connector(request)) == preview
    assert serialize_tee_connector_design(design_check_tee_connector(request)) == design


@pytest.mark.parametrize("role", ["COLUMN", "BEAM"])
def test_stateless_preview_exposes_both_interfaces_normal_trace_and_solids(role: str) -> None:
    resolver = _Resolver()
    payload = build_tee_payload(
        role=role,
        force=("0", "1", "3") if role == "COLUMN" else ("3", "1", "0"),
    )
    response = _post(PREVIEW_ROUTE, payload, _app(resolver))

    assert response.status_code == 200
    body = response.json()
    assert body["support_role"] == role
    assert body["resistance_evaluated"] is False
    assert body["ordinary_pass_allowed"] is False
    assert body["result"]["interface_a"]["normal_component"] is not None
    assert body["result"]["interface_a"]["automatic_axis_tension_generated"] is False
    assert body["result"]["interface_b"]["bolt_group_id"] == "tee-bolt-group-b"
    assert len(body["result"]["visualization"]["interface_a_bolts"]) == 4
    assert len(body["result"]["visualization"]["interface_b_bolts"]) == 4
    assert resolver.calls == 1


def test_c2_workspace_rhs_preview_returns_the_full_through_contract() -> None:
    response = _post(PREVIEW_ROUTE, build_tee_c2_workspace_rhs_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["orchestration_contract_version"] == "3.3C2-RC1"
    assert body["result"]["visualization"] is not None
    paths = body["result"]["rectangular_full_through_paths"]
    assert len(paths) == 4
    assert [item["identity"] for item in paths[0]["path"]["segments"]] == [
        "TEE_STEM",
        "RHS_NEAR_WALL",
        "RHS_CAVITY",
        "RHS_FAR_WALL",
    ]


def test_r2_route_exposes_strict_profile_trace_and_owner_contact_surface() -> None:
    response = _post(
        PREVIEW_ROUTE,
        build_tee_r2_payload(profile_family="CHANNEL", selected_surface="WEB_OUTER"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["orchestration_contract_version"] == "3.2-R2"
    assert body["preview_schema_version"] == "0.2.0-draft"
    trace = body["result"]["connected_member_profile"]
    scene = body["result"]["visualization"]
    assert trace["profile_family"] == "CHANNEL"
    assert trace["surface_patch_id"] == "PROFILE_CONTACT:WEB_OUTER"
    assert scene["schema_version"] == "0.2.0-draft"
    assert scene["selected_connected_surface_id"] == "WEB_OUTER"
    assert scene["selected_connected_surface_patch_id"] == trace["surface_patch_id"]

    design = _post(
        DESIGN_ROUTE,
        build_tee_r2_payload(
            profile_family="CHANNEL",
            selected_surface="WEB_OUTER",
            force=("0", "0", ".001"),
        ),
    )
    assert design.status_code == 200
    design_body = design.json()
    assert design_body["orchestration_contract_version"] == "3.2-R2"
    assert design_body["ordinary_pass_allowed"] is False
    assert (
        design_body["result"]["preview"]["connected_member_profile"]["surface_patch_id"]
        == "PROFILE_CONTACT:WEB_OUTER"
    )


@pytest.mark.parametrize("unit_system", ["US_CUSTOMARY", "SI"])
def test_r4_flat_plate_benchmark_route_is_valid_in_both_unit_systems(
    unit_system: str,
) -> None:
    response = _post(PREVIEW_ROUTE, build_tee_r4_benchmark_payload(unit_system=unit_system))

    assert response.status_code == 200
    body = response.json()
    assert body["assembly_status"] == "NOT_EVALUATED"
    assert body["design_check_ready"] is True
    assert body["result"]["connected_member_profile"]["profile_family"] == "FLAT_PLATE"
    assert body["result"]["connected_member_profile"]["selected_profile_surface"] == "FACE_POS"
    assert body["result"]["interface_a"]["preview"]["geometry_status"] == "VALID"
    assert body["result"]["interface_b"]["preview"]["geometry_status"] == "VALID"
    assert all("Row-1-to-unloaded-end" not in warning for warning in body["warnings"])


@pytest.mark.parametrize(
    ("family", "expected_surface", "qualification"),
    [
        ("CHANNEL", "WEB_OUTER", None),
        (
            "RECTANGULAR_HOLLOW_SECTION",
            "Y_POS_FACE",
            "INTERNAL_FASTENER_ACCESS_REQUIRED",
        ),
    ],
)
def test_r8_profile_wall_preview_routes_are_valid_and_trace_rhs_access(
    family: str,
    expected_surface: str,
    qualification: str | None,
) -> None:
    response = _post(
        PREVIEW_ROUTE,
        build_tee_r8_profile_wall_payload(profile_family=family),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assembly_status"] == "NOT_EVALUATED"
    assert body["design_check_ready"] is (family != "RECTANGULAR_HOLLOW_SECTION")
    assert body["result"]["connected_member_profile"]["profile_family"] == family
    assert (
        body["result"]["connected_member_profile"]["selected_profile_surface"] == expected_surface
    )
    assert len(body["result"]["visualization"]["interface_a_bolts"]) == 4
    if qualification is None:
        assert "INTERNAL_FASTENER_ACCESS_REQUIRED" not in body["warnings"]
    else:
        assert qualification not in body["warnings"]
        assert qualification not in body["result"]["warnings"]
        assert body["result"]["design_limitations"] == [
            "RHS_LOCAL_WALL_RESPONSE",
            "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
        ]
        assert all(
            trace["hardware"]["internal_hardware_count"] == 0
            for trace in body["result"]["rectangular_full_through_paths"]
        )


def test_r9_routes_accept_independent_counts_and_expose_authoritative_inclination() -> None:
    payload = build_tee_r7_angle_payload(unloaded_end_distance="6")
    payload["interface_a_layout"]["bolts_per_row"] = 1
    payload["brace_inclination_degrees"] = "30"
    payload["connector_dimensions"]["connector_length"]["value"] = "16"
    payload["connected_member_profile"]["dimensions"].update(
        {
            "leg_y": {"value": "12", "unit": "in"},
            "leg_z": {"value": "12", "unit": "in"},
            "member_length": {"value": "20", "unit": "in"},
        }
    )

    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["result"]["visualization"]["interface_a_bolts"]) == 2
    assert len(body["result"]["visualization"]["interface_b_bolts"]) == 4
    trace = body["result"]["connected_member_profile"]
    assert trace["brace_inclination_degrees"] == "30"
    assert set(trace["brace_placement_frame"]) == {"origin", "x_axis", "y_axis", "z_axis"}
    assert (
        body["result"]["interface_a"]["interface_fingerprint"]
        != (body["result"]["interface_b"]["interface_fingerprint"])
    )

    payload["interface_a_layout"]["row_count"] = 1
    design = _post(DESIGN_ROUTE, payload)
    assert design.status_code == 200
    design_body = design.json()
    assert design_body["result"]["interface_a"]["design"] is None
    assert design_body["result"]["ordinary_pass_allowed"] is False


def test_r9_route_rejects_out_of_domain_inclination_before_mapping() -> None:
    payload = build_tee_r7_angle_payload()
    payload["brace_inclination_degrees"] = "90.1"

    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 422
    assert "brace_inclination_degrees" in response.text


def test_r10_preview_route_exposes_exact_placement_frame_and_clearance_trace() -> None:
    payload = build_tee_r7_angle_payload()
    payload["interface_a_layout"]["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
    payload["interface_a_layout"]["vertical_offset"] = {
        "value": "-1.7185",
        "unit": "in",
    }
    payload["interface_a_layout"]["horizontal_offset"] = {
        "value": "0",
        "unit": "in",
    }

    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 200
    placement = response.json()["result"]["interface_a"]["placement"]
    assert placement["datum_id"] == "TEE_STEM_CENTER_DATUM_A"
    assert placement["placement_mode"] == "GROUP_OFFSET_CONTROLLED"
    assert placement["vertical_offset"]["value"] == "-1.7185"
    assert placement["horizontal_offset"]["value"] == "0"
    assert placement["clearances"]["minimum"]["value"] == "0"
    assert placement["clearances"]["minimum_complete_hole_containment"]["value"] == ("1.2815")
    assert set(placement["datum_point"]) == {"x", "y", "z"}
    assert set(placement["vertical_axis"]) == {"x", "y", "z"}
    assert len(placement["bolt_centers_hvn"]) == 4


def test_r10_invalid_angle_clearance_route_returns_exact_safe_feedback() -> None:
    response = _post(
        PREVIEW_ROUTE,
        build_tee_r7_angle_payload(unloaded_end_distance="1.2814"),
    )

    assert response.status_code == 422
    assert "Complete-hole clearance -0.0001 in" in response.text
    assert "Minimum for complete-hole containment: 1.2815 in" in response.text


def test_r12_preview_route_exposes_authoritative_member_end_trim_trace() -> None:
    payload = build_tee_r7_angle_payload()
    payload["brace_inclination_degrees"] = "25"
    payload["interface_a_layout"]["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
    payload["interface_a_layout"]["vertical_offset"] = {"value": "0", "unit": "in"}
    payload["interface_a_layout"]["horizontal_offset"] = {"value": "0", "unit": "in"}
    payload["connected_member_end_trim_enabled"] = True
    payload["connected_member_end_clearance"] = {"value": "0.25", "unit": "in"}

    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 200
    result = response.json()["result"]
    trace = result["connected_member_end_trim"]
    assert trace["reference_plane_id"] == "TEE_FLANGE_INNER_CLEARANCE_PLANE"
    assert trace["cut_plane_id"] == "CONNECTED_MEMBER_END_CUT_PLANE"
    assert trace["normalized_clearance"]["value"] == "0.25"
    assert trace["normalized_clearance"]["unit"] == "in"
    assert trace["measured_plane_clearance"]["value"] == "0.25"
    assert trace["measured_plane_clearance"]["unit"] == "in"
    assert trace["interference_status"] == "TRIMMED_CLEAR"
    assert trace["geometry_valid"] is True
    assert trace["minimum_hole_edge_clearance"]["value"] == "0.4685"
    assert trace["minimum_hole_edge_clearance"]["unit"] == "in"
    assert any(
        primitive["kind"] == "TRIANGLE_MESH" and primitive["owner_id"] == "tee-brace"
        for primitive in result["visualization"]["base_connection"]["view_extension_primitives"]
    )
    assert result["resistance_evaluated"] is False
    assert result["design_check_ready"] is False


def test_design_route_returns_not_evaluated_or_fail_never_pass() -> None:
    no_failure = _post(DESIGN_ROUTE, build_tee_payload(force=("0", "0", ".001")))
    failure = _post(DESIGN_ROUTE, build_tee_payload(force=("0", "0", "3")))

    assert no_failure.status_code == 200
    assert no_failure.json()["assembly_status"] == "NOT_EVALUATED"
    assert no_failure.json()["supported_interface_failure_present"] is False
    assert failure.status_code == 200
    assert failure.json()["assembly_status"] == "FAIL"
    assert failure.json()["supported_interface_failure_present"] is True


def test_invalid_geometry_and_transport_fail_closed_with_422() -> None:
    payload = build_tee_payload()
    payload["connector_dimensions"]["stem_thickness"]["value"] = "7"
    response = _post(PREVIEW_ROUTE, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_TEE_MAPPING_INVALID"

    response = _post(DESIGN_ROUTE, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_TEE_MAPPING_INVALID"

    payload = build_tee_payload()
    payload["interface_b_layout"]["pitch"]["value"] = "not-decimal"
    response = _post(DESIGN_ROUTE, payload)
    assert response.status_code == 422


def test_openapi_registers_narrow_tee_routes_and_fixed_material_literals() -> None:
    schema = _app().openapi()
    assert PREVIEW_ROUTE in schema["paths"]
    assert DESIGN_ROUTE in schema["paths"]
    request_schema = schema["components"]["schemas"]["TeeConnectorRequestDTO"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["properties"]["connector_material"]["const"] == "PULTRUDED_FRP"
    assert request_schema["properties"]["fastener_material"]["const"] == "STAINLESS_STEEL_316"


def test_old_api_route_remains_registered_unchanged() -> None:
    schema = _app().openapi()
    assert "/api/v1/calculations/single-bolt/evaluate" in schema["paths"]
    assert "/api/v1/calculations/multi-row/design-check" in schema["paths"]


def test_mapping_rejects_nonlength_and_nonpositive_physical_dimensions() -> None:
    from frp_master_connection.api.schemas import QuantityDTO

    with pytest.raises(ValueError, match="length quantities"):
        tee_mapping._length(QuantityDTO(value="1", unit=Unit.KIP), Unit.IN)
    with pytest.raises(ValueError, match="positive"):
        tee_mapping._length(QuantityDTO(value="0", unit=Unit.IN), Unit.IN)
    assert tee_mapping._serialize([Decimal("1")]) == ["1"]
    assert tee_mapping._serialize({"value": Decimal("2")}) == {"value": "2"}
