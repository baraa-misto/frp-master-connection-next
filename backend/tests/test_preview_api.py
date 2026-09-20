"""Stage 2.3R5 canonical preview endpoint and zero-resistance contracts."""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI

import frp_master_connection.api.routes as routes_module
import frp_master_connection.application.connection_preview as preview_module
from frp_master_connection.api.app import create_app
from frp_master_connection.api.calculation_mapping import (
    map_connection_view_extents,
    map_single_bolt_preview_request,
    serialize_single_bolt_preview_response,
)
from frp_master_connection.api.schemas import SingleBoltPreviewRequestDTO
from frp_master_connection.application import (
    ConnectionViewExtents,
    SingleBoltOrchestrationRequest,
    evaluate_single_bolt_connection,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import EngineeringUnitSystem
from frp_master_connection.security import TrustedIdentity
from tests.api_fixtures import (
    build_api_payload,
    build_j1_preview_api_payload,
    build_j1_template_api_payload,
)
from tests.application.orchestration_fixtures import build_plate_case

PREVIEW_ROUTE = "/api/v1/calculations/single-bolt/preview"
DESIGN_ROUTE = "/api/v1/calculations/single-bolt/evaluate"


class _CountingIdentityResolver:
    production_capable = True

    def __init__(self) -> None:
        self.calls = 0

    async def resolve(self) -> TrustedIdentity:
        self.calls += 1
        return TrustedIdentity("preview-account", None, frozenset({"engineer"}), "test")


def _application(resolver: _CountingIdentityResolver | None = None) -> FastAPI:
    return create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )


def _post(
    payload: dict[str, object],
    *,
    route: str = PREVIEW_ROUTE,
    application: FastAPI | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        selected = _application() if application is None else application
        transport = httpx.ASGITransport(app=selected)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(route, json=payload)

    return asyncio.run(send())


def _preview(
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
    angle_degrees: str = "45",
    bolt_to_brace_end_distance: str | None = None,
    column_view_extent_below: str | None = None,
    column_view_extent_above: str | None = None,
    brace_view_length: str | None = None,
    column_flange_connection_side: str = "EXTERIOR",
    outstanding_leg_side: str = "POSITIVE_INTERFACE_Z",
) -> dict[str, Any]:
    response = _post(
        build_j1_preview_api_payload(
            unit_system=unit_system,
            explicit_demand=explicit_demand,
            angle_degrees=angle_degrees,
            bolt_to_brace_end_distance=bolt_to_brace_end_distance,
            column_view_extent_below=column_view_extent_below,
            column_view_extent_above=column_view_extent_above,
            brace_view_length=brace_view_length,
            column_flange_connection_side=column_flange_connection_side,
            outstanding_leg_side=outstanding_leg_side,
        )
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _contains_key_fragment(value: object, fragments: tuple[str, ...]) -> bool:
    if isinstance(value, Mapping):
        return any(
            any(fragment in str(key).lower() for fragment in fragments)
            or _contains_key_fragment(item, fragments)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key_fragment(item, fragments) for item in value)
    return False


def test_preview_endpoint_resolves_trusted_identity_once() -> None:
    resolver = _CountingIdentityResolver()
    response = _post(build_j1_preview_api_payload(), application=_application(resolver))

    assert response.status_code == 200
    assert resolver.calls == 1


def test_default_j1_preview_is_valid_deterministic_and_design_ready() -> None:
    payload = build_j1_preview_api_payload()
    first = _post(payload)
    second = _post(payload)

    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    body = first.json()
    assert body["preview_schema_version"] == "0.2.0-draft"
    assert body["geometry_status"] == "PREVIEW_VALID"
    assert body["geometry_issues"] == []
    assert body["design_check_ready"] is True
    assert body["design_check_blocking_reasons"] == []
    assert len(body["resolved_layers"]) == 2
    assert len(body["visualization"]["frames"]) >= 6


def test_preview_contains_no_resistance_result_utilization_or_fingerprint_fields() -> None:
    body = _preview()

    assert not _contains_key_fragment(
        body,
        ("resistance", "capacity", "utilization", "fingerprint", "governing", "pass_fail"),
    )
    assert "results" not in body
    assert "plans" not in body
    assert "aggregate_status" not in body


def test_preview_never_calls_the_design_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(_request: object) -> object:
        raise AssertionError("the design evaluator must not execute during preview")

    monkeypatch.setattr(routes_module, "evaluate_single_bolt_connection", forbidden)

    assert _post(build_j1_preview_api_payload()).status_code == 200


def test_invalid_interference_is_http_200_and_blocks_design() -> None:
    body = _preview(outstanding_leg_side="NEGATIVE_INTERFACE_Z")
    orientation = body["visualization"]["connection_orientation"]

    assert body["geometry_status"] == "PREVIEW_INVALID_GEOMETRY"
    assert body["geometry_issues"]
    assert body["design_check_ready"] is False
    assert "INVALID_GEOMETRY" in body["design_check_blocking_reasons"]
    assert orientation["geometry_valid"] is False
    assert orientation["interference_classifications"]
    assert orientation["interference_participant_ids"]
    assert orientation["interference_physical_element_ids"]


def test_valid_web_side_preview_uses_the_inner_flange_face_and_same_bolt_stack() -> None:
    body = _preview(column_flange_connection_side="WEB_SIDE")
    orientation = body["visualization"]["connection_orientation"]

    assert body["geometry_status"] == "PREVIEW_VALID"
    assert orientation["connection_side"] == "WEB_SIDE"
    assert orientation["selected_flange_surface_id"] == "TOP_FLANGE:INNER_NEGATIVE_CW_STRIP"
    assert [layer["physical_element_id"] for layer in body["resolved_layers"]] == [
        "LEG_1",
        "TOP_FLANGE",
    ]
    assert [hole["physical_element_id"] for hole in body["visualization"]["bolt"]["holes"]] == [
        "LEG_1",
        "TOP_FLANGE",
    ]


@pytest.mark.parametrize("angle", ["5", "45", "60", "90", "120", "135", "150", "175"])
def test_preview_resolves_supported_angles_material_relationships_and_frames(angle: str) -> None:
    body = _preview(angle_degrees=angle)
    orientation = body["visualization"]["connection_orientation"]
    brace_frame = next(
        frame for frame in body["visualization"]["frames"] if frame["owner_id"] == "member-a"
    )

    assert orientation["brace_to_column_directed_angle_degrees"] == angle
    assert orientation["plan_angle_degrees"] == "0"
    assert brace_frame["inspection"]["orthonormal"] is True
    assert brace_frame["inspection"]["right_handed"] is True
    assert len(body["material_relationships"]) == 2
    assert all("theta_degrees" in item for item in body["material_relationships"])


@pytest.mark.parametrize(
    ("geometry_angle", "material_angle", "direction_family"),
    [
        ("45", 45.0, "TRANSVERSE"),
        ("90", 90.0, "TRANSVERSE"),
        ("120", 60.0, "TRANSVERSE"),
        ("135", 45.0, "TRANSVERSE"),
        ("150", 30.0, "TRANSVERSE"),
        ("175", 5.0, "LONGITUDINAL"),
    ],
)
def test_directed_geometry_and_sign_independent_material_angles_are_separate(
    geometry_angle: str,
    material_angle: float,
    direction_family: str,
) -> None:
    body = _preview(angle_degrees=geometry_angle)
    orientation = body["visualization"]["connection_orientation"]
    relationship = next(
        item for item in body["material_relationships"] if item["layer_id"] == "layer-B"
    )
    brace_frame = next(
        item for item in body["visualization"]["frames"] if item["owner_id"] == "member-a"
    )

    assert orientation["brace_to_column_directed_angle_degrees"] == geometry_angle
    assert float(relationship["theta_degrees"]) == pytest.approx(material_angle, abs=1e-12)
    assert relationship["direction_family"] == direction_family
    assert float(brace_frame["inspection"]["determinant"]) == pytest.approx(1.0, abs=1e-12)
    assert float(brace_frame["frame"]["x_axis"]["y"]) < 0.0


@pytest.mark.parametrize("angle", ["0", "180", "181", "NaN", "Infinity", True])
def test_preview_rejects_out_of_range_or_nonfinite_directed_angles(angle: object) -> None:
    payload = build_j1_preview_api_payload()
    cast(dict[str, object], payload["geometry_template"])["brace_to_column_directed_angle_deg"] = (
        angle
    )

    assert _post(payload).status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("column_view_extent_below", "12"),
        ("column_view_extent_above", "3"),
        ("brace_view_length", "6"),
    ],
)
def test_preview_view_extents_change_only_non_targetable_visualization_context(
    field: str,
    value: str,
) -> None:
    baseline = _preview()
    if field == "column_view_extent_below":
        changed = _preview(column_view_extent_below=value)
    elif field == "column_view_extent_above":
        changed = _preview(column_view_extent_above=value)
    else:
        changed = _preview(brace_view_length=value)

    assert (
        changed["visualization"]["view_extension_primitives"]
        != baseline["visualization"]["view_extension_primitives"]
    )
    for key in (
        "primitives",
        "interface_zones",
        "bolt",
        "reference_points",
        "connection_orientation",
    ):
        assert changed["visualization"][key] == baseline["visualization"][key]
    assert changed["resolved_layers"] == baseline["resolved_layers"]


@pytest.mark.parametrize("length", ["4", "5", "8", "12"])
def test_j1_brace_view_length_preserves_engineering_geometry_and_design(length: str) -> None:
    payload = build_j1_preview_api_payload(brace_view_length=length)
    dto = SingleBoltPreviewRequestDTO.model_validate(payload)
    request = map_single_bolt_preview_request(dto)
    preview = preview_module.preview_single_bolt_connection(
        request,
        map_connection_view_extents(dto),
    )
    design = evaluate_single_bolt_connection(request)
    baseline_dto = SingleBoltPreviewRequestDTO.model_validate(build_j1_preview_api_payload())
    baseline_request = map_single_bolt_preview_request(baseline_dto)
    baseline_preview = preview_module.preview_single_bolt_connection(
        baseline_request,
        map_connection_view_extents(baseline_dto),
    )
    baseline_design = evaluate_single_bolt_connection(baseline_request)

    assert preview.geometry_status is preview_module.PreviewGeometryStatus.VALID
    assert preview.visualization is not None
    assert baseline_preview.visualization is not None
    assert preview.visualization.bolt == baseline_preview.visualization.bolt
    assert preview.visualization.interface_zones == baseline_preview.visualization.interface_zones
    assert preview.visualization.reference_points == baseline_preview.visualization.reference_points
    assert design.calculation_fingerprint == baseline_design.calculation_fingerprint
    assert design.calculation_result == baseline_design.calculation_result
    layer_a = next(
        item for item in preview.material_relationships if item.physical_element_id == "layer-A"
    )
    assert float(layer_a.forward_e1.to(Unit.IN).magnitude) == pytest.approx(2.0, abs=1e-12)


@pytest.mark.parametrize(
    ("length", "expected"),
    [("101.6", 4.0), ("127", 5.0), ("203.2", 8.0), ("304.8", 12.0)],
)
def test_si_brace_view_lengths_are_exact_equivalents(length: str, expected: float) -> None:
    body = _preview(unit_system=EngineeringUnitSystem.SI, brace_view_length=length)
    layer_a = next(item for item in body["resolved_layers"] if item["layer_id"] == "layer-A")

    assert float(layer_a["code_mapping"]["forward_e1"]["value"]) / 25.4 == pytest.approx(
        2.0,
        abs=1e-12,
    )
    brace = next(
        item
        for item in body["visualization"]["view_extension_primitives"]
        if item["owner_id"] == "member-a"
    )
    parameters = {item["name"]: float(item["value"]) for item in brace["parameters"]}
    assert (parameters["x_end"] - parameters["x_start"]) / 25.4 == pytest.approx(
        expected,
        abs=1e-12,
    )


def test_preview_member_dimension_and_bolt_dimension_change_canonical_geometry() -> None:
    payload = build_j1_preview_api_payload()
    baseline = _post(payload).json()["visualization"]
    changed = copy.deepcopy(payload)
    members = changed["joint_assembly"]["members"]
    angle = next(member for member in members if member["id"] == "member-a")
    angle["section"]["leg_y"]["value"] = "3.5"
    changed["bolt_diameter"]["value"] = "0.52"

    response = _post(changed)
    assert response.status_code == 200
    assert response.json()["visualization"] != baseline


def test_preview_transports_independent_canonical_bolt_and_physical_hole_diameters() -> None:
    payload = build_j1_preview_api_payload()
    baseline = _post(payload).json()["visualization"]["bolt"]
    changed = copy.deepcopy(payload)
    changed["bolt_diameter"]["value"] = "0.75"

    response = _post(changed)

    assert response.status_code == 200
    bolt = response.json()["visualization"]["bolt"]
    assert baseline["bolt_diameter"] == "0.5"
    assert bolt["bolt_diameter"] == "0.75"
    assert [item["diameter"] for item in baseline["holes"]] == ["0.563", "0.563"]
    assert [item["diameter"] for item in bolt["holes"]] == ["0.563", "0.563"]


@pytest.mark.parametrize(
    ("force", "expected_sense", "expected_zero"),
    [("-0.7", "NEGATIVE", False), ("0", "ZERO", True), ("1.2", "POSITIVE", False)],
)
def test_preview_applied_action_preserves_signed_and_zero_arrow_data(
    force: str,
    expected_sense: str,
    expected_zero: bool,
) -> None:
    payload = build_j1_preview_api_payload()
    action = payload["joint_assembly"]["member_end_actions"][0]
    action["force"]["x"] = force
    body = _post(payload).json()
    arrow = next(
        item
        for item in body["visualization"]["applied_action_directions"]
        if item["component"] == "FX"
    )

    assert body["source_action_trace"]["global_force"] is not None
    assert arrow["signed_value"] == force
    assert arrow["sense"] == expected_sense
    assert arrow["is_zero"] is expected_zero


@pytest.mark.parametrize(
    ("unit_system", "component", "vector_kind", "coordinate", "expected_kind", "expected_unit"),
    [
        (EngineeringUnitSystem.US_CUSTOMARY, "FX", "force", "x", "LINEAR", "kip"),
        (EngineeringUnitSystem.US_CUSTOMARY, "MZ", "moment", "z", "ROTATIONAL", "kip-in"),
        (EngineeringUnitSystem.SI, "FX", "force", "x", "LINEAR", "kN"),
        (EngineeringUnitSystem.SI, "MZ", "moment", "z", "ROTATIONAL", "kN-mm"),
    ],
)
def test_preview_applied_force_and_moment_quantities_retain_server_directions_and_units(
    unit_system: EngineeringUnitSystem,
    component: str,
    vector_kind: str,
    coordinate: str,
    expected_kind: str,
    expected_unit: str,
) -> None:
    positive_payload = build_j1_preview_api_payload(unit_system=unit_system)
    negative_payload = build_j1_preview_api_payload(unit_system=unit_system)
    positive_payload["joint_assembly"]["member_end_actions"][0][vector_kind][coordinate] = "1.2"
    negative_payload["joint_assembly"]["member_end_actions"][0][vector_kind][coordinate] = "-1.2"

    positive_body = _post(positive_payload).json()
    negative_body = _post(negative_payload).json()
    positive_arrow = next(
        item
        for item in positive_body["visualization"]["applied_action_directions"]
        if item["component"] == component
    )
    negative_arrow = next(
        item
        for item in negative_body["visualization"]["applied_action_directions"]
        if item["component"] == component
    )

    assert positive_arrow["signed_value"] == "1.2"
    assert negative_arrow["signed_value"] == "-1.2"
    assert positive_arrow["kind"] == negative_arrow["kind"] == expected_kind
    assert positive_arrow["unit"] == negative_arrow["unit"] == expected_unit
    assert positive_arrow["sense"] == "POSITIVE"
    assert negative_arrow["sense"] == "NEGATIVE"
    for axis in ("x", "y", "z"):
        assert float(negative_arrow["axis"][axis]) == pytest.approx(
            -float(positive_arrow["axis"][axis]),
            abs=1e-12,
        )
    assert "results" not in positive_body
    assert "results" not in negative_body


def test_member_end_only_request_previews_geometry_but_is_not_design_ready() -> None:
    body = _preview(explicit_demand=False)

    assert body["geometry_status"] == "PREVIEW_VALID"
    assert body["visualization"] is not None
    assert body["source_action_trace"] is not None
    assert body["design_check_ready"] is False
    assert "EXPLICIT_RESOLVED_BOLT_DEMAND_REQUIRED" in body["design_check_blocking_reasons"]


def test_preview_and_design_share_engineering_geometry_but_not_view_context() -> None:
    preview = _post(build_j1_preview_api_payload()).json()
    design = _post(build_j1_template_api_payload(), route=DESIGN_ROUTE).json()

    assert preview["visualization"]["view_extension_primitives"]
    assert design["visualization"]["view_extension_primitives"] == []
    for key in ("primitives", "interface_zones", "bolt", "reference_points"):
        assert preview["visualization"][key] == design["visualization"][key]


@pytest.mark.parametrize("mutation", ["missing", "extra", "malformed"])
def test_preview_dto_is_strict_and_malformed_requests_are_422(mutation: str) -> None:
    payload = build_j1_preview_api_payload()
    if mutation == "missing":
        payload.pop("interface_id")
    elif mutation == "extra":
        payload["client_geometry_status"] = "VALID"
    else:
        payload["bolt_diameter"] = {"value": "not-a-number", "unit": "in"}

    response = _post(payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_preview_openapi_is_post_only_and_excludes_client_authority_and_design_fields() -> None:
    schema = _application().openapi()
    operation = schema["paths"][PREVIEW_ROUTE]
    request_reference = operation["post"]["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    request_name = request_reference.rsplit("/", 1)[1]
    request_schema = json.dumps(schema["components"]["schemas"][request_name], sort_keys=True)

    assert set(operation) == {"post"}
    assert "view_extents" in request_schema
    for prohibited in (
        "trusted_identity",
        "geometry_status",
        "end_use_factors",
        "time_effect_category",
        "fnt",
        "utilization",
    ):
        assert prohibited not in request_schema
    design_operation = schema["paths"][DESIGN_ROUTE]
    design_reference = design_operation["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    design_name = design_reference.rsplit("/", 1)[1]
    design_request_schema = json.dumps(
        schema["components"]["schemas"][design_name],
        sort_keys=True,
    )
    assert "view_extents" not in design_request_schema


def test_design_endpoint_and_j1_design_result_remain_unchanged() -> None:
    response = _post(build_j1_template_api_payload(), route=DESIGN_ROUTE)
    body = response.json()

    assert response.status_code == 200
    assert body["api_transport_schema_version"] == "0.5.0-draft"
    assert body["aggregate_status"] == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    assert body["results"]
    assert body["calculation_fingerprint"] is not None


def test_us_and_si_preview_preserve_canonical_orientation() -> None:
    us = _preview()
    si = _preview(unit_system=EngineeringUnitSystem.SI)

    for field in ("connection_side", "connected_leg", "outstanding_leg_side", "geometry_valid"):
        assert (
            us["visualization"]["connection_orientation"][field]
            == si["visualization"]["connection_orientation"][field]
        )
    assert us["unit_system"] == "US_CUSTOMARY"
    assert si["unit_system"] == "SI"


def test_preview_application_rejects_the_wrong_request_type() -> None:
    with pytest.raises(TypeError, match="SingleBoltOrchestrationRequest"):
        preview_module.preview_single_bolt_connection(
            cast(SingleBoltOrchestrationRequest, object())
        )

    with pytest.raises(TypeError, match="view_extents"):
        preview_module.preview_single_bolt_connection(
            build_plate_case("P1").request,
            cast(ConnectionViewExtents, object()),
        )


def test_explicit_geometry_preview_uses_the_same_non_template_service_path() -> None:
    result = preview_module.preview_single_bolt_connection(build_plate_case("P1").request)

    assert result.geometry_status is preview_module.PreviewGeometryStatus.VALID
    assert result.visualization is not None
    assert result.orchestration_trace.resolved_layers


def test_unresolved_target_returns_incomplete_preview_without_visualization() -> None:
    request = replace(build_plate_case("P1").request, interface_id="missing-interface")
    result = preview_module.preview_single_bolt_connection(request)

    assert result.geometry_status is preview_module.PreviewGeometryStatus.INCOMPLETE_INPUT
    assert result.visualization is None
    assert result.design_check_ready is False
    assert set(result.design_check_blocking_reasons) == {
        "INTERFACE_NOT_FOUND",
        "BOLT_PATH_NOT_FOUND",
    }


def test_missing_action_and_demand_is_unsupported_but_still_returns_geometry() -> None:
    request = replace(
        build_plate_case("P1").request,
        source_action_id=None,
        resolved_demand=None,
    )
    result = preview_module.preview_single_bolt_connection(request)

    assert result.geometry_status is preview_module.PreviewGeometryStatus.UNSUPPORTED
    assert result.visualization is not None
    assert "EXPLICIT_RESOLVED_BOLT_DEMAND_REQUIRED" in result.design_check_blocking_reasons


def test_empty_nonvalid_status_uses_the_status_as_the_design_blocker() -> None:
    blockers = preview_module._design_blockers(
        preview_module.PreviewGeometryStatus.UNSUPPORTED,
        (),
        has_explicit_demand=True,
    )

    assert blockers == ("PREVIEW_UNSUPPORTED",)


@pytest.mark.parametrize(
    "participant",
    [None, SimpleNamespace(material_orientation=None, material_kind="PULTRUDED_FRP")],
)
def test_missing_component_material_orientation_fails_preview_closed(
    participant: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preview_module, "_participant", lambda *_args: participant)

    result = preview_module.preview_single_bolt_connection(build_plate_case("P2A").request)

    assert result.geometry_status is preview_module.PreviewGeometryStatus.INVALID_GEOMETRY
    assert any(
        "lengthwise orientation" in issue.message for issue in result.orchestration_trace.issues
    )


def test_geometry_mapping_failure_is_converted_to_invalid_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_mapping(_request: object) -> object:
        raise ValueError("controlled mapping failure")

    monkeypatch.setattr(preview_module, "resolve_geometry_to_code_mapping", fail_mapping)

    result = preview_module.preview_single_bolt_connection(build_plate_case("P2A").request)

    assert result.geometry_status is preview_module.PreviewGeometryStatus.INVALID_GEOMETRY
    assert any(
        "controlled mapping failure" in issue.message for issue in result.orchestration_trace.issues
    )


def test_wrong_preview_fastener_identity_is_a_safe_mapping_422() -> None:
    payload = build_j1_preview_api_payload()
    payload["fastener_snapshot"]["id"] = "client-spoofed-fastener"

    response = _post(payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_MAPPING_INVALID"


def test_unresolved_target_serializes_an_incomplete_preview_without_visualization() -> None:
    request = replace(build_plate_case("P1").request, interface_id="missing-interface")
    result = preview_module.preview_single_bolt_connection(request)

    body = serialize_single_bolt_preview_response(result)

    assert body.geometry_status == "PREVIEW_INCOMPLETE_INPUT"
    assert body.visualization is None


@pytest.mark.parametrize("geometry_sources", ["neither", "both"])
def test_preview_requires_exactly_one_geometry_source(geometry_sources: str) -> None:
    payload = build_j1_preview_api_payload()
    if geometry_sources == "neither":
        payload.pop("geometry_template")
    else:
        payload["geometry"] = build_api_payload("P1")["geometry"]

    response = _post(payload)

    assert response.status_code == 422
    assert "exactly one of geometry or geometry_template" in response.text


@pytest.mark.parametrize("invalid_extent_source", ["missing-template-view", "explicit-with-view"])
def test_preview_requires_view_extents_only_for_template_geometry(
    invalid_extent_source: str,
) -> None:
    payload = build_j1_preview_api_payload()
    if invalid_extent_source == "missing-template-view":
        payload.pop("view_extents")
    else:
        payload["geometry"] = build_api_payload("P1")["geometry"]
        payload.pop("geometry_template")

    response = _post(payload)

    assert response.status_code == 422
    assert "view_extents" in response.text


def test_preview_view_extent_mapper_handles_explicit_none_and_rejects_nonpositive() -> None:
    explicit_payload = build_j1_preview_api_payload()
    explicit_payload["geometry"] = build_api_payload("P1")["geometry"]
    explicit_payload.pop("geometry_template")
    explicit_payload.pop("view_extents")
    explicit_dto = SingleBoltPreviewRequestDTO.model_validate(explicit_payload)
    assert map_connection_view_extents(explicit_dto) is None

    nonpositive_payload = build_j1_preview_api_payload(brace_view_length="0")
    nonpositive_dto = SingleBoltPreviewRequestDTO.model_validate(nonpositive_payload)
    with pytest.raises(ValueError, match="brace_view_length"):
        map_connection_view_extents(nonpositive_dto)


@pytest.mark.parametrize("value", [True, "4", 0.0, -1.0, float("nan"), float("inf")])
def test_connection_view_extents_require_positive_finite_real_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="brace_view_length"):
        ConnectionViewExtents(cast(float, value), 4.0, 4.0)
