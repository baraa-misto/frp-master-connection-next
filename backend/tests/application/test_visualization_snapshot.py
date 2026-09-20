"""Stage 2.3 canonical visualization snapshot verification."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import cast

import pytest

import frp_master_connection.application.visualization as visualization_module
from frp_master_connection.api.calculation_mapping import (
    map_single_bolt_request,
    serialize_single_bolt_response,
)
from frp_master_connection.api.schemas import SingleBoltEvaluationRequestDTO
from frp_master_connection.application import (
    ActionDirectionSnapshot,
    SingleBoltOrchestrationRequest,
    SingleBoltOrchestrationResponse,
    SingleBoltVisualizationSnapshot,
    VisualizationPrimitiveKind,
    VisualizationResolutionStatus,
    build_single_bolt_visualization_snapshot,
    evaluate_single_bolt_connection,
)
from frp_master_connection.application.visualization import _zone_snapshot
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    AssemblySupport,
    CylindricalMaterialOrientation,
    EngineeringUnitSystem,
    MaterialRegionRole,
    MemberRole,
    PositionVector3D,
    SectionFamily,
    SupportKind,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    ResolvedConnectionZone,
    RoundTubeDimensions,
    Vector3D,
    create_bounded_support_surface,
    create_component_surface_set,
    create_round_tube_geometry,
    place_member,
)
from tests.api_fixtures import build_api_payload
from tests.application.orchestration_fixtures import (
    build_j1_case,
    build_j1_visual_case,
    build_plate_case,
)


def test_view_extensions_ignore_non_brace_and_non_column_member_roles() -> None:
    dto = SingleBoltEvaluationRequestDTO.model_validate(build_api_payload("P1"))
    request = map_single_bolt_request(dto)
    member = replace(request.assembly.members[0], role=MemberRole.OTHER)
    placed = SimpleNamespace(component=member)
    selected_interface = request.geometry_context.basis.resolved_interfaces[0]
    fake_request = SimpleNamespace(
        geometry_context=SimpleNamespace(
            basis=SimpleNamespace(placed_members=(placed,)),
        ),
    )

    assert (
        visualization_module._view_extension_primitives(
            cast(SingleBoltOrchestrationRequest, fake_request),
            selected_interface,
            visualization_module.ConnectionViewExtents(4.0, 4.0, 4.0),
        )
        == ()
    )


def _snapshot(
    *,
    compression: bool = False,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
) -> tuple[
    SingleBoltOrchestrationRequest,
    SingleBoltOrchestrationResponse,
    SingleBoltVisualizationSnapshot,
]:
    request = build_j1_case(
        compression=compression,
        unit_system=unit_system,
    ).request
    response = evaluate_single_bolt_connection(request)
    return request, response, build_single_bolt_visualization_snapshot(request, response)


def test_j1_snapshot_is_immutable_deterministic_and_identity_bound() -> None:
    request, response, first = _snapshot()
    second = build_single_bolt_visualization_snapshot(request, response)
    assert first == second
    assert first.snapshot_version == "1.3.0-draft"
    assert first.assembly_id == "benchmark-assembly"
    assert first.interface_id == "interface-1"
    assert first.bolt_group_id == "bolt-group-1"
    assert first.bolt_location_id == "bolt-1"
    with pytest.raises(FrozenInstanceError):
        first.snapshot_version = "changed"  # type: ignore[misc]


def test_j1_component_primitives_preserve_exact_standard_shape_elements() -> None:
    _request, _response, snapshot = _snapshot()
    assert tuple(item.id for item in snapshot.components) == ("member-a", "member-b")
    assert snapshot.components[0].section_family == "ANGLE"
    assert snapshot.components[1].section_family == "WIDE_FLANGE"
    assert tuple(item.id for item in snapshot.components[0].elements) == ("LEG_1", "LEG_2")
    assert tuple(item.id for item in snapshot.components[1].elements) == (
        "WEB",
        "TOP_FLANGE",
        "BOTTOM_FLANGE",
    )
    assert tuple(item.kind for item in snapshot.primitives) == (
        VisualizationPrimitiveKind.BOX,
        VisualizationPrimitiveKind.BOX,
        VisualizationPrimitiveKind.DEFERRED_RECTANGLE,
        VisualizationPrimitiveKind.BOX,
        VisualizationPrimitiveKind.BOX,
        VisualizationPrimitiveKind.BOX,
        VisualizationPrimitiveKind.DEFERRED_RULED_SURFACE,
        VisualizationPrimitiveKind.DEFERRED_RULED_SURFACE,
    )
    assert all(item.center is not None for item in snapshot.primitives[:6])
    assert all(
        item.resolution_status is VisualizationResolutionStatus.DEFERRED
        for item in snapshot.primitives
        if item.kind.value.startswith("DEFERRED")
    )


def test_snapshot_contains_global_joint_member_interface_and_bolt_frames() -> None:
    _request, _response, snapshot = _snapshot()
    assert tuple(item.id for item in snapshot.frames) == (
        "GLOBAL",
        "JOINT_LOCAL:benchmark-assembly",
        "MEMBER_LOCAL:member-a",
        "MEMBER_LOCAL:member-b",
        "INTERFACE_LOCAL:interface-1",
        "BOLT_GROUP_LOCAL:bolt-group-1",
    )
    assert all(item.inspection.valid for item in snapshot.frames)
    global_frame = snapshot.frames[0]
    assert global_frame.frame.origin.x == global_frame.frame.origin.y == 0.0
    assert global_frame.inspection.determinant == 1.0
    assert global_frame.inspection.xy_dot == 0.0


def test_j1_material_directions_are_exact_per_planar_region() -> None:
    _request, _response, snapshot = _snapshot()
    angle_leg = next(
        item
        for item in snapshot.material_directions
        if item.component_id == "member-a" and item.physical_element_id == "LEG_1"
    )
    w_flange = next(
        item
        for item in snapshot.material_directions
        if item.component_id == "member-b" and item.physical_element_id == "TOP_FLANGE"
    )
    assert angle_leg.resolution_status is VisualizationResolutionStatus.EXACT
    assert angle_leg.lengthwise is not None
    assert angle_leg.crosswise is not None
    assert angle_leg.through_thickness is not None
    assert (angle_leg.lengthwise.x, angle_leg.lengthwise.y, angle_leg.lengthwise.z) == (
        1.0,
        0.0,
        0.0,
    )
    assert w_flange.lengthwise is not None
    assert w_flange.lengthwise.x == pytest.approx(2**-0.5)
    assert w_flange.lengthwise.y == pytest.approx(2**-0.5)
    assert w_flange.crosswise is not None
    assert w_flange.through_thickness is not None


def test_stage_2_3r_j1_visual_fixture_is_one_proper_rotation_with_vertical_column() -> None:
    request = build_j1_visual_case().request
    response = evaluate_single_bolt_connection(request)
    snapshot = build_single_bolt_visualization_snapshot(request, response)
    frames = {item.owner_id: item for item in snapshot.frames if item.owner_id is not None}
    brace = frames["member-a"]
    column = frames["member-b"]
    assert column.frame.x_axis.x == pytest.approx(0.0, abs=1e-12)
    assert column.frame.x_axis.y == pytest.approx(0.0, abs=1e-12)
    assert column.frame.x_axis.z == pytest.approx(1.0)
    assert column.inspection.determinant == pytest.approx(1.0)
    assert brace.frame.x_axis.x == pytest.approx(0.0, abs=1e-12)
    assert brace.frame.x_axis.y == pytest.approx(-(2**-0.5))
    assert brace.frame.x_axis.z == pytest.approx(2**-0.5)
    references = {item.id: item for item in snapshot.reference_points}
    assert references["member-b:start"].position.z < references["member-b:end"].position.z
    brace_lw = next(
        item.lengthwise
        for item in snapshot.material_directions
        if item.component_id == "member-a" and item.physical_element_id == "LEG_1"
    )
    column_lw = next(
        item.lengthwise
        for item in snapshot.material_directions
        if item.component_id == "member-b" and item.physical_element_id == "TOP_FLANGE"
    )
    assert brace_lw is not None
    assert column_lw is not None
    assert abs(brace_lw.dot(column_lw)) == pytest.approx(2**-0.5)
    assert snapshot.bolt.axis.x == pytest.approx(-1.0)
    assert snapshot.bolt.axis.y == pytest.approx(0.0, abs=1e-12)
    assert snapshot.bolt.axis.z == pytest.approx(0.0, abs=1e-12)


def test_non_frp_planar_region_reports_no_invented_material_triad() -> None:
    request = build_plate_case("P1").request
    response = evaluate_single_bolt_connection(request)
    snapshot = build_single_bolt_visualization_snapshot(request, response)
    steel = next(item for item in snapshot.material_directions if item.component_id == "member-b")
    assert steel.resolution_status is VisualizationResolutionStatus.NOT_APPLICABLE
    assert steel.lengthwise is steel.crosswise is steel.through_thickness is None
    assert steel.reason == "No fixed planar material-direction triad is resolved for this region."


def test_interface_zones_and_bolt_path_are_canonical() -> None:
    _request, _response, snapshot = _snapshot()
    assert tuple((item.side, item.id) for item in snapshot.interface_zones) == (
        ("FIRST", "first-zone"),
        ("SECOND", "second-zone"),
    )
    assert all(item.geometry_kind == "PLANAR_RECTANGLE" for item in snapshot.interface_zones)
    assert all(len(item.corners) == 4 for item in snapshot.interface_zones)
    assert snapshot.bolt.center.x == 2.0
    assert snapshot.bolt.center.y == 0.1875
    assert snapshot.bolt.axis.z == 1.0
    assert snapshot.bolt.bolt_diameter == 0.5
    assert tuple(item.physical_element_id for item in snapshot.bolt.holes) == (
        "LEG_1",
        "TOP_FLANGE",
    )
    assert snapshot.bolt.holes[0].diameter == 0.563
    assert tuple(item.location for item in snapshot.bolt.washers) == (
        "UNDER_HEAD",
        "UNDER_NUT",
    )
    assert all(item.outside_diameter == 1.0 for item in snapshot.bolt.washers)
    assert snapshot.bolt.washers[0].end == snapshot.bolt.stack_start
    assert snapshot.bolt.washers[1].start == snapshot.bolt.stack_end


def test_washer_display_is_omitted_when_geometry_or_locations_are_not_declared() -> None:
    request = build_j1_case().request
    without_geometry = replace(
        request,
        fastener_snapshot=replace(request.fastener_snapshot, washer_geometry=None),
    )
    response = evaluate_single_bolt_connection(without_geometry)
    snapshot = build_single_bolt_visualization_snapshot(without_geometry, response)
    assert snapshot.bolt.washers == ()

    washer = request.fastener_snapshot.washer_geometry
    assert washer is not None
    without_locations = replace(
        request,
        fastener_snapshot=replace(
            request.fastener_snapshot,
            washer_geometry=replace(washer, under_head=False, under_nut=False),
        ),
    )
    response = evaluate_single_bolt_connection(without_locations)
    snapshot = build_single_bolt_visualization_snapshot(without_locations, response)
    assert snapshot.bolt.washers == ()


def test_round_tube_support_and_annular_zone_snapshot_use_exact_physical_geometry() -> None:
    request, response, _snapshot_value = _snapshot()
    first_member = request.assembly.members[0]
    round_topology = create_standard_section_topology(
        SectionFamily.ROUND_TUBE,
        orientations={
            MaterialRegionRole.CYLINDRICAL_WALL: CylindricalMaterialOrientation(),
        },
    )
    round_member = replace(
        first_member,
        section_family=SectionFamily.ROUND_TUBE,
        section_topology=round_topology,
    )
    round_placed = place_member(
        round_member,
        create_round_tube_geometry(round_topology, RoundTubeDimensions(10.0, 1.0)),
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(4.0, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )
    support_entity = AssemblySupport("support-1", "Bounded support", SupportKind.CONCRETE)
    support = create_bounded_support_surface(
        support_entity,
        "bearing-surface",
        "Bounded bearing surface",
        request.geometry_context.basis.joint_frame,
        20.0,
        30.0,
    )
    round_assembly = replace(
        request.assembly,
        members=(round_member, request.assembly.members[1]),
        supports=(*request.assembly.supports, support_entity),
    )
    basis = replace(
        request.geometry_context.basis,
        assembly=round_assembly,
        placed_members=(round_placed, request.geometry_context.basis.placed_members[1]),
        component_surface_sets=(
            create_component_surface_set(round_placed),
            request.geometry_context.basis.component_surface_sets[1],
        ),
        support_surfaces=(support,),
    )
    round_request = replace(
        request,
        assembly=round_assembly,
        geometry_context=replace(request.geometry_context, basis=basis),
    )
    snapshot = build_single_bolt_visualization_snapshot(round_request, response)
    annular_cylinder = next(
        item
        for item in snapshot.primitives
        if item.kind is VisualizationPrimitiveKind.ANNULAR_CYLINDER
    )
    assert {item.name: item.value for item in annular_cylinder.parameters} == {
        "x_start": 0.0,
        "x_end": 4.0,
        "outer_radius": 5.0,
        "inner_radius": 4.0,
    }
    support_rectangle = next(
        item
        for item in snapshot.primitives
        if item.kind is VisualizationPrimitiveKind.SUPPORT_RECTANGLE
    )
    assert isinstance(support.geometry, PlanarRectangularSurface3D)
    assert support_rectangle.points == support.geometry.corners

    annular_patch = next(
        item
        for item in create_component_surface_set(round_placed).patches
        if isinstance(item.geometry, PlanarAnnularSurface3D)
    )
    zone = ResolvedConnectionZone(
        ConnectionZoneSpecification(
            "annular-zone",
            "Exact annular end zone",
            annular_patch.reference,
            ConnectionZoneKind.WHOLE_PATCH,
        ),
        annular_patch,
    )
    zone_snapshot = _zone_snapshot("interface-round", "FIRST", zone)
    assert zone_snapshot.geometry_kind == "PLANAR_ANNULUS"
    assert zone_snapshot.corners == ()
    assert {item.name: item.value for item in zone_snapshot.parameters} == {
        "outer_radius": 5.0,
        "inner_radius": 4.0,
    }


def test_reference_points_include_start_end_connected_end_and_origins() -> None:
    _request, _response, snapshot = _snapshot()
    by_id = {item.id: item for item in snapshot.reference_points}
    assert tuple(by_id) == (
        "joint-origin",
        "member-a:start",
        "member-a:end",
        "member-b:start",
        "member-b:end",
        "interface:interface-1:origin",
        "bolt-group:bolt-group-1:origin",
        "bolt:bolt-1:center",
        "action:action-1:reference",
    )
    assert by_id["member-a:start"].connected is True
    assert by_id["member-a:end"].connected is False
    assert by_id["action:action-1:reference"].provenance == ("MEMBER_CONNECTED_END_SECTION_DATUM")
    assert by_id["bolt:bolt-1:center"].position == snapshot.bolt.center


def test_positive_and_applied_action_directions_retain_sign_zero_and_provenance() -> None:
    _request, _response, snapshot = _snapshot()
    assert tuple(item.component.value for item in snapshot.positive_action_directions) == (
        "FX",
        "FY",
        "FZ",
        "MX",
        "MY",
        "MZ",
    )
    applied = {item.component.value: item for item in snapshot.applied_action_directions}
    assert applied["FX"].signed_value == 0.7
    assert applied["FX"].axis.x == 1.0
    assert applied["FX"].sense == "POSITIVE"
    assert applied["FX"].axial_loading_sense == "TENSION"
    assert applied["FY"].is_zero is True
    assert applied["FY"].sense == "ZERO"
    assert applied["MZ"].signed_value == 1.0
    assert applied["MZ"].unit is Unit.KIP_IN
    assert all(item.reference_point_id == "action:action-1:reference" for item in applied.values())


def test_negative_action_reverses_applied_axis_without_changing_positive_axis() -> None:
    payload = build_api_payload("J1-T")
    assembly = cast(dict[str, object], payload["joint_assembly"])
    actions = cast(list[dict[str, object]], assembly["member_end_actions"])
    action = actions[0]
    force = cast(dict[str, object], action["force"])
    force["x"] = "-0.7"
    request = map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))
    response = evaluate_single_bolt_connection(request)
    snapshot = build_single_bolt_visualization_snapshot(request, response)
    positive = snapshot.positive_action_directions[0]
    applied = snapshot.applied_action_directions[0]
    assert positive.axis.x == 1.0
    assert applied.axis.x == -1.0
    assert applied.signed_value == -0.7
    assert applied.sense == "NEGATIVE"
    assert applied.axial_loading_sense == "COMPRESSION"


def test_snapshot_remains_available_when_member_end_distribution_is_unsupported() -> None:
    request = build_j1_case(explicit_demand=False).request
    response = evaluate_single_bolt_connection(request)
    snapshot = build_single_bolt_visualization_snapshot(request, response)
    assert response.aggregate_status is not None
    assert response.aggregate_status.value == "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    assert snapshot.components
    assert snapshot.bolt.holes
    assert len(snapshot.applied_action_directions) == 6


def test_snapshot_without_resolvable_source_action_omits_action_only_data() -> None:
    payload = build_api_payload("J1-T")
    payload["source_action_id"] = "missing-action"
    request = map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))
    response = evaluate_single_bolt_connection(request)
    snapshot = build_single_bolt_visualization_snapshot(request, response)
    assert response.source_action_trace is None
    assert snapshot.positive_action_directions == ()
    assert snapshot.applied_action_directions == ()
    assert all(item.kind != "MEMBER_CONNECTED_END" for item in snapshot.reference_points)


def test_us_and_si_snapshots_are_physically_equivalent() -> None:
    _us_request, _us_response, us = _snapshot()
    _si_request, _si_response, si = _snapshot(unit_system=EngineeringUnitSystem.SI)
    assert us.length_unit is Unit.IN
    assert si.length_unit is Unit.MM
    assert si.bolt.center.x == pytest.approx(us.bolt.center.x * 25.4)
    assert si.bolt.center.y == pytest.approx(us.bolt.center.y * 25.4)
    assert si.bolt.bolt_diameter == pytest.approx(us.bolt.bolt_diameter * 25.4)
    assert tuple(item.id for item in si.frames) == tuple(item.id for item in us.frames)
    assert tuple(item.axis for item in si.applied_action_directions) == tuple(
        item.axis for item in us.applied_action_directions
    )


def test_serialization_adds_no_style_camera_or_fingerprint_change() -> None:
    request, response, snapshot = _snapshot()
    serialized = serialize_single_bolt_response(response, snapshot)
    rendering = serialized.visualization
    flattened = repr(rendering).lower()
    assert "camera" not in flattened
    assert "color" not in flattened
    assert "pixel" not in flattened
    assert "webgl" not in flattened
    assert serialized.calculation_fingerprint == response.calculation_fingerprint
    assert rendering["snapshot_version"] == "1.3.0-draft"
    bolt = cast(dict[str, object], rendering["bolt"])
    assert bolt["center"] == {
        "x": "2",
        "y": "0.1875",
        "z": "0",
        "unit": "in",
    }
    assert request is not None


def test_visualization_builder_rejects_invalid_or_mismatched_boundaries() -> None:
    request = build_j1_case().request
    response = evaluate_single_bolt_connection(request)
    with pytest.raises(TypeError, match="request"):
        build_single_bolt_visualization_snapshot(object(), response)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="response"):
        build_single_bolt_visualization_snapshot(request, object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="identities"):
        build_single_bolt_visualization_snapshot(
            request,
            replace(response, calculation_id="other"),
        )


def test_action_direction_snapshot_is_a_frozen_transport_neutral_value() -> None:
    _request, _response, snapshot = _snapshot(compression=True)
    value = snapshot.applied_action_directions[0]
    assert isinstance(value, ActionDirectionSnapshot)
    assert value.kind == "LINEAR"
    assert value.unit is Unit.KIP
    with pytest.raises(FrozenInstanceError):
        value.signed_value = 1.0  # type: ignore[misc]
