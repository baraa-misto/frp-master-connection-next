"""Stage 3.2-R2 Tee integration tests over real member/profile surfaces."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import frp_master_connection.api.tee_mapping as tee_mapping
import frp_master_connection.application.tee_orchestration as tee_orchestration
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    TEE_R2_ORCHESTRATION_CONTRACT_VERSION,
    TEE_R2_PREVIEW_SCHEMA_VERSION,
    TEE_R2_VISUALIZATION_SCHEMA_VERSION,
    adapt_legacy_tee_brace_profile,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    INTERNAL_FASTENER_ACCESS_REQUIRED,
    AngleLegBoltPathResolution,
    AssemblyMember,
    ComponentMaterialKind,
    ExactProfileVector3D,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    MemberRole,
    ProfileWallBoltPathResolution,
    RoundHollowProfileDimensions,
    TeeBraceDimensions,
    create_standard_section_topology,
    require_direct_tee_profile_surface,
    resolve_angle_leg_bolt_path,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.geometry import (
    PlanarRectangularSurface3D,
    UnitVector3D,
    create_component_surface_set,
)
from tests.tee_fixtures import (
    build_tee_payload,
    build_tee_r2_payload,
    build_tee_r2_request,
    build_tee_r7_angle_request,
    build_tee_r8_profile_wall_request,
    build_tee_request,
)

_PROFILE_SURFACES = {
    "ANGLE": ("LEG_Y_OUTER", "LEG_Z_OUTER"),
    "CHANNEL": ("WEB_OUTER", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"),
    "WIDE_FLANGE_I": (
        "WEB_POS_FACE",
        "WEB_NEG_FACE",
        "FLANGE_POS_OUTER",
        "FLANGE_NEG_OUTER",
    ),
    "RECTANGULAR_HOLLOW_SECTION": (
        "Y_POS_FACE",
        "Y_NEG_FACE",
        "Z_POS_FACE",
        "Z_NEG_FACE",
    ),
    "FLAT_PLATE": ("FACE_POS", "FACE_NEG"),
}
_ORIENTATIONS = ("ROTATION_0", "ROTATION_90", "ROTATION_180", "ROTATION_270")
_PROFILE_CASES = tuple(
    (family, surface, orientation)
    for family, surfaces in _PROFILE_SURFACES.items()
    for surface in surfaces
    for orientation in _ORIENTATIONS
)


@pytest.mark.parametrize(("family", "surface", "orientation"), _PROFILE_CASES)
def test_every_authorized_surface_and_orientation_uses_real_finite_bolt_paths(
    family: str,
    surface: str,
    orientation: str,
) -> None:
    request = build_tee_r2_request(
        profile_family=family,
        selected_surface=surface,
        profile_orientation=orientation,
    )
    resolved = resolve_tee_connector_request(request)
    group = next(
        item
        for item in resolved.context.resolved_bolt_groups
        if item.bolt_group.id == "tee-bolt-group-a"
    )
    preview = preview_tee_connector(request)

    assert len(group.paths) == (
        request.interface_a_layout.row_count * request.interface_a_layout.bolts_per_row
    )
    assert {path.layers[0].definition.physical_element_id for path in group.paths} == {
        resolved.connected_member_profile.physical_element_role.value
    }
    owner_surface = require_direct_tee_profile_surface(request.connected_member_profile)
    assert all(
        path.layers[0].raw_thickness == pytest.approx(float(owner_surface.layer_thickness))
        for path in group.paths
    )
    assert all(path.layers[0].raw_minimum_patch_clearance > 0 for path in group.paths)
    assert preview.orchestration_contract_version == TEE_R2_ORCHESTRATION_CONTRACT_VERSION
    assert preview.preview_schema_version == TEE_R2_PREVIEW_SCHEMA_VERSION
    assert preview.connected_member_profile.profile_family == MemberProfileFamily(family)
    assert preview.connected_member_profile.selected_profile_surface == MemberProfileSurfaceId(
        surface
    )
    assert any(
        item.participant.entity_id == "tee-brace"
        and item.id == preview.connected_member_profile.surface_patch_id
        for item in resolved.context.basis.all_surfaces
    )
    assert preview.visualization is not None
    assert preview.visualization.schema_version == TEE_R2_VISUALIZATION_SCHEMA_VERSION
    assert preview.visualization.selected_connected_surface_id == MemberProfileSurfaceId(surface)
    assert (
        preview.visualization.selected_connected_surface_patch_id
        == preview.connected_member_profile.surface_patch_id
    )


def test_r2_profile_identity_changes_fingerprint_but_not_interface_b() -> None:
    base = preview_tee_connector(build_tee_r2_request())
    changed = preview_tee_connector(
        build_tee_r2_request(
            profile_family="RECTANGULAR_HOLLOW_SECTION",
            selected_surface="Z_POS_FACE",
            profile_orientation="ROTATION_90",
        )
    )

    assert base.engineering_fingerprint != changed.engineering_fingerprint
    assert (
        base.connected_member_profile.member_profile_fingerprint
        != changed.connected_member_profile.member_profile_fingerprint
    )
    assert (
        base.connected_member_profile.profile_geometry_fingerprint
        != changed.connected_member_profile.profile_geometry_fingerprint
    )
    assert base.interface_b.preview.automatic_demand_result == (
        changed.interface_b.preview.automatic_demand_result
    )
    assert base.interface_b.preview.geometry_status == changed.interface_b.preview.geometry_status
    assert base.interface_b.preview.method_applicability == (
        changed.interface_b.preview.method_applicability
    )
    assert base.interface_b.preview.qualification == changed.interface_b.preview.qualification
    assert base.visualization is not None
    assert changed.visualization is not None
    assert base.visualization.interface_b_bolts == changed.visualization.interface_b_bolts


def test_column_and_beam_supports_reuse_one_wide_flange_profile_geometry() -> None:
    column = resolve_tee_connector_request(build_tee_r2_request(role="COLUMN"))
    beam = resolve_tee_connector_request(build_tee_r2_request(role="BEAM"))
    column_support = column.context.basis.placed_members[1]
    beam_support = beam.context.basis.placed_members[1]

    assert column_support.cross_section == beam_support.cross_section
    assert column_support.global_frame != beam_support.global_frame


@pytest.mark.parametrize(
    ("family", "surface"),
    [("ANGLE", "LEG_Y_OUTER"), ("CHANNEL", "WEB_OUTER")],
)
def test_composite_contact_keeps_full_owner_bounds_and_reduced_penetration(
    family: str,
    surface: str,
) -> None:
    request = build_tee_r2_request(profile_family=family, selected_surface=surface)
    owner = require_direct_tee_profile_surface(request.connected_member_profile)
    resolved = resolve_tee_connector_request(request)
    interface = resolved.context.basis.resolved_interfaces[0]
    primary = interface.first_side.primary_zone
    penetration = next(
        item for item in interface.first_side.zones if item.id == "tee-zone-a-brace-penetration"
    )
    contact_geometry = primary.geometry
    penetration_geometry = penetration.geometry
    assert isinstance(contact_geometry, PlanarRectangularSurface3D)
    assert isinstance(penetration_geometry, PlanarRectangularSurface3D)
    owner_transverse_span = (
        owner.contact_bounds.max_z - owner.contact_bounds.min_z
        if owner.plane_axis.value == "Y"
        else owner.contact_bounds.max_y - owner.contact_bounds.min_y
    )

    assert contact_geometry.extent_y == float(
        owner.contact_bounds.max_x - owner.contact_bounds.min_x
    )
    assert contact_geometry.extent_z == float(owner_transverse_span)
    assert penetration_geometry.extent_z < contact_geometry.extent_z
    assert primary.surface.id.startswith("PROFILE_CONTACT:")
    group = resolved.context.resolved_bolt_groups[0]
    assert all(path.layers[0].exit.surface.id == owner.outside_patch_id for path in group.paths)
    assert all(path.layers[0].zones[0].id == "tee-zone-a-brace-penetration" for path in group.paths)


def test_r2_response_serializes_profile_trace_and_actual_surface_identity() -> None:
    preview = preview_tee_connector(
        build_tee_r2_request(profile_family="CHANNEL", selected_surface="WEB_OUTER")
    )
    response = serialize_tee_connector_preview(preview).model_dump(mode="json")
    trace = response["result"]["connected_member_profile"]
    scene = response["result"]["visualization"]

    assert response["api_transport_schema_version"] == "0.1.0-draft"
    assert response["orchestration_contract_version"] == "3.2-R2"
    assert response["preview_schema_version"] == "0.2.0-draft"
    assert trace["profile_family"] == "CHANNEL"
    assert len(trace["member_profile_fingerprint"]) == 64
    assert len(trace["profile_geometry_fingerprint"]) == 64
    assert trace["surface_patch_id"] == "PROFILE_CONTACT:WEB_OUTER"
    assert trace["physical_element_role"] == "WEB"
    assert scene["selected_connected_surface_id"] == "WEB_OUTER"
    assert scene["selected_connected_surface_patch_id"] == trace["surface_patch_id"]


def test_legacy_rc1_adapter_is_explicit_and_deterministic() -> None:
    first = build_tee_request()
    second = build_tee_request()

    assert first.connected_member_profile == second.connected_member_profile
    assert first.connected_member_profile.family is MemberProfileFamily.FLAT_PLATE
    assert first.connected_member_profile.selected_surface is MemberProfileSurfaceId.FACE_NEG
    assert first.brace_dimensions is not None
    assert first.connected_member_profile.dimensions.member_length == (
        first.brace_dimensions.view_length
    )


@pytest.mark.parametrize(
    ("version", "include_legacy", "include_r2"),
    [
        ("3.2-RC1", True, True),
        ("3.2-RC1", False, False),
        ("3.2-R2", True, True),
        ("3.2-R2", False, False),
    ],
)
def test_versioned_contract_rejects_mixed_or_missing_profile_inputs(
    version: str,
    include_legacy: bool,
    include_r2: bool,
) -> None:
    legacy = build_tee_payload()
    r2 = build_tee_r2_payload()
    payload = deepcopy(legacy)
    payload["orchestration_contract_version"] = version
    if not include_legacy:
        payload.pop("brace_dimensions")
    if include_r2:
        payload["connected_member_profile"] = r2["connected_member_profile"]

    with pytest.raises(ValidationError):
        TeeConnectorRequestDTO.model_validate(payload)


def test_family_surface_mismatch_is_rejected_at_transport_boundary() -> None:
    payload = build_tee_r2_payload()
    payload["connected_member_profile"]["selected_profile_surface"] = "WEB_OUTER"

    with pytest.raises(ValidationError):
        TeeConnectorRequestDTO.model_validate(payload)


def test_round_hollow_direct_tee_contact_remains_fail_closed() -> None:
    with pytest.raises(
        ValueError,
        match="CURVED_SURFACE_REQUIRES_SEPARATELY_DEFINED_INTERFACE_OR_ADAPTER",
    ):
        build_tee_r2_request(profile_family="ROUND_HOLLOW_SECTION")


def test_finite_selected_profile_surface_rejects_out_of_bounds_holes() -> None:
    payload = build_tee_r2_payload()
    payload["connected_member_profile"]["dimensions"]["leg_y"] = {
        "value": "2",
        "unit": "in",
    }
    mapped = TeeConnectorRequestDTO.model_validate(payload)

    with pytest.raises(ValueError, match="finite opposing broad face"):
        preview_tee_connector(map_tee_connector_request(mapped))


def test_legacy_mapping_fails_closed_without_brace_dimensions() -> None:
    invalid = TeeConnectorRequestDTO.model_construct(
        connected_member_profile=None,
        brace_dimensions=None,
    )

    with pytest.raises(ValueError, match="Legacy Tee mapping requires brace_dimensions"):
        tee_mapping._connected_member_profile(invalid, Unit.IN)


def test_profile_id_rejects_whitespace_only_at_transport_boundary() -> None:
    payload = build_tee_r2_payload()
    payload["connected_member_profile"]["profile_id"] = " "

    with pytest.raises(ValidationError, match="profile_id must be nonempty"):
        TeeConnectorRequestDTO.model_validate(payload)


def test_legacy_profile_adapter_rejects_wrong_runtime_type() -> None:
    with pytest.raises(TypeError, match="dimensions must be a TeeBraceDimensions"):
        adapt_legacy_tee_brace_profile(cast(TeeBraceDimensions, object()))


def test_request_rejects_wrong_connected_profile_runtime_type() -> None:
    request = build_tee_request()

    with pytest.raises(TypeError, match="connected_member_profile must be a MemberProfile"):
        replace(request, connected_member_profile=cast(MemberProfile, object()))


@pytest.mark.parametrize("invalid_identity", ["member_id", "role", "material_kind"])
def test_request_rejects_profiles_outside_controlled_brace_identity(
    invalid_identity: str,
) -> None:
    request = build_tee_request()
    profile = request.connected_member_profile
    if invalid_identity == "member_id":
        material_orientation = profile.material_orientation
        assert material_orientation is not None
        invalid = replace(
            profile,
            member_id="other-brace",
            material_orientation=replace(
                material_orientation,
                coordinate_frame=replace(
                    material_orientation.coordinate_frame,
                    owner_id="other-brace",
                ),
            ),
        )
    elif invalid_identity == "role":
        invalid = replace(profile, role=MemberRole.COLUMN)
    else:
        invalid = replace(
            profile,
            material_kind=ComponentMaterialKind.STEEL,
            material_orientation=None,
        )

    with pytest.raises(ValueError, match="controlled FRP brace member"):
        replace(request, connected_member_profile=invalid)


def test_rc1_request_requires_legacy_dimensions() -> None:
    request = build_tee_request()

    with pytest.raises(ValueError, match=r"3\.2-RC1 requires legacy brace dimensions"):
        replace(request, brace_dimensions=None)


def test_rc1_request_requires_exact_deterministic_profile_adapter() -> None:
    request = build_tee_request()
    invalid = replace(request.connected_member_profile, id="alternate-flat-plate-profile")

    with pytest.raises(ValueError, match="deterministic flat-plate adapter"):
        replace(request, connected_member_profile=invalid)


def test_r2_request_forbids_legacy_dimensions() -> None:
    request = build_tee_r2_request()
    legacy = build_tee_request()
    assert legacy.brace_dimensions is not None

    with pytest.raises(ValueError, match=r"3\.2-R2 forbids legacy brace dimensions"):
        replace(request, brace_dimensions=legacy.brace_dimensions)


def test_round_profile_cross_section_remains_fail_closed() -> None:
    base = build_tee_r2_request().connected_member_profile
    profile = replace(
        base,
        family=MemberProfileFamily.ROUND_HOLLOW_SECTION,
        dimensions=RoundHollowProfileDimensions(
            member_length=Decimal("6"),
            outer_diameter=Decimal("8"),
            wall_thickness=Decimal("0.375"),
        ),
        selected_surface=None,
    )
    topology = create_standard_section_topology(profile.section_family)

    with pytest.raises(ValueError, match="Round hollow profiles"):
        tee_orchestration._profile_cross_section(profile, topology)


def test_profile_orientation_must_remain_transverse_to_member() -> None:
    request = build_tee_r2_request()
    longitudinal, transverse, _, _ = tee_orchestration._unit_axes(
        request.support_role,
        request.selected_support_flange,
    )

    with pytest.raises(ValueError, match="orientation did not remain transverse"):
        tee_orchestration._effective_profile_local_z(
            request.connected_member_profile,
            longitudinal,
            transverse,
            transverse,
        )


def test_profile_placement_rejects_surface_facing_away_from_stem() -> None:
    request = build_tee_r2_request()
    resolved = resolve_tee_connector_request(request)
    member = resolved.context.basis.placed_members[0].component
    assert isinstance(member, AssemblyMember)
    topology = member.section_topology
    assert topology is not None
    longitudinal, transverse, normal, _ = tee_orchestration._unit_axes(
        request.support_role,
        request.selected_support_flange,
    )
    reversed_local_z = UnitVector3D(-transverse.x, -transverse.y, -transverse.z)

    with (
        patch.object(
            tee_orchestration,
            "_effective_profile_local_z",
            return_value=reversed_local_z,
        ),
        pytest.raises(ValueError, match="does not face the Tee stem"),
    ):
        tee_orchestration._place_connected_profile(
            member,
            request.connected_member_profile,
            topology,
            request.connector_dimensions,
            longitudinal,
            transverse,
            normal,
        )


def test_bolt_group_frame_rejects_parallel_in_plane_reference() -> None:
    resolved = resolve_tee_connector_request(build_tee_r2_request())
    interface = resolved.context.basis.resolved_interfaces[0]

    with pytest.raises(ValueError, match="in-plane reference is parallel"):
        tee_orchestration._bolt_group_frame(
            interface,
            0.0,
            interface.interface_frame.x_axis,
            interface.tolerance,
        )


def test_opposing_patch_selection_skips_same_direction_face() -> None:
    resolved = resolve_tee_connector_request(build_tee_r2_request())
    group = resolved.context.resolved_bolt_groups[0]
    wrong_facing_patch = group.paths[0].layers[0].exit.surface

    with pytest.raises(ValueError, match="one finite opposing broad face"):
        tee_orchestration._opposing_patch_for_location(
            group.bolt_group.locations[0],
            group.bolt_group_frame,
            (wrong_facing_patch,),
            0.1,
            group.tolerance,
        )


def test_resolver_rejects_changed_selected_patch_identity() -> None:
    request = build_tee_r2_request()
    resolved = resolve_tee_connector_request(request)
    placed = resolved.context.basis.placed_members[0]
    kernel_surfaces = create_component_surface_set(placed)
    wrong_selected = next(
        item for item in kernel_surfaces.patches if item.id == "LEG_2:EXTERIOR_TT_BROAD"
    )
    contact = next(
        item
        for item in resolved.context.basis.all_surfaces
        if item.id == resolved.connected_member_profile.surface_patch_id
    )

    with (
        patch.object(
            tee_orchestration,
            "_place_connected_profile",
            return_value=(placed, wrong_selected, contact),
        ),
        pytest.raises(RuntimeError, match="selected patch identity changed"),
    ):
        resolve_tee_connector_request(request)


def test_r7_controlled_angle_fixture_resolves_finite_physical_leg_paths() -> None:
    request = build_tee_r7_angle_request()
    resolved = resolve_tee_connector_request(request)
    preview = preview_tee_connector(request)
    group = next(
        item
        for item in resolved.context.resolved_bolt_groups
        if item.bolt_group.id == "tee-bolt-group-a"
    )

    assert len(group.paths) == 4
    assert {path.definition.bolt_location_id for path in group.paths} == {
        "tee-base-bolt-a",
        "tee-bolt-a-r1-l2",
        "tee-bolt-a-r2-l1",
        "tee-bolt-a-r2-l2",
    }
    assert all(len(path.layers) == 2 for path in group.paths)
    brace_layers = tuple(path.layers[0] for path in group.paths)
    assert {layer.definition.physical_element_id for layer in brace_layers} == {"LEG_1"}
    assert {layer.physical_element.source_element.role.value for layer in brace_layers} == {"LEG_1"}
    assert {layer.physical_element.source_material_region.id for layer in brace_layers} == {"LEG_1"}
    assert {layer.entry.surface.id for layer in brace_layers} == {"LEG_1:OPEN_AREA_TT_BROAD"}
    assert {layer.exit.surface.id for layer in brace_layers} == {"LEG_1:EXTERIOR_TT_BROAD"}
    assert all(layer.raw_thickness == pytest.approx(0.5) for layer in brace_layers)
    assert all(layer.raw_minimum_patch_clearance >= 0 for layer in brace_layers)
    assert preview.design_check_ready is True
    assert preview.connected_member_profile.profile_family is MemberProfileFamily.ANGLE
    assert (
        preview.connected_member_profile.selected_profile_surface
        is MemberProfileSurfaceId.LEG_Y_OUTER
    )
    assert preview.visualization is not None
    assert (
        preview.visualization.connected_member_profile.profile_family is MemberProfileFamily.ANGLE
    )


def test_r7_smallest_exact_end_adjustment_preserves_invalid_free_edge_case() -> None:
    with pytest.raises(ValueError, match="one finite opposing broad face"):
        resolve_tee_connector_request(build_tee_r7_angle_request(unloaded_end_distance="1.2814"))

    resolved = resolve_tee_connector_request(
        build_tee_r7_angle_request(unloaded_end_distance="1.2815")
    )

    assert len(resolved.context.resolved_bolt_groups[0].paths) == 4


def test_r7_original_visual_angle_fixture_remains_invalid() -> None:
    with pytest.raises(ValueError, match="one finite opposing broad face"):
        resolve_tee_connector_request(build_tee_r7_angle_request(unloaded_end_distance="1"))


def test_r7_rotation_changes_global_placement_not_leg_pair_or_thickness() -> None:
    zero = resolve_tee_connector_request(build_tee_r7_angle_request())
    ninety = resolve_tee_connector_request(
        build_tee_r7_angle_request(profile_orientation="ROTATION_90")
    )
    zero_group = zero.context.resolved_bolt_groups[0]
    ninety_group = ninety.context.resolved_bolt_groups[0]
    zero_placed = next(
        item for item in zero.context.basis.placed_members if item.component.id == "tee-brace"
    )
    ninety_placed = next(
        item for item in ninety.context.basis.placed_members if item.component.id == "tee-brace"
    )

    assert tee_orchestration._owner_profile_frame(
        zero_placed, zero.request.connected_member_profile
    ) != tee_orchestration._owner_profile_frame(
        ninety_placed, ninety.request.connected_member_profile
    )
    for group in (zero_group, ninety_group):
        brace_layers = tuple(path.layers[0] for path in group.paths)
        assert {layer.definition.physical_element_id for layer in brace_layers} == {"LEG_1"}
        assert {layer.entry.surface.id for layer in brace_layers} == {"LEG_1:OPEN_AREA_TT_BROAD"}
        assert {layer.exit.surface.id for layer in brace_layers} == {"LEG_1:EXTERIOR_TT_BROAD"}
        assert all(layer.raw_thickness == pytest.approx(0.5) for layer in brace_layers)


def test_r7_interface_b_is_unchanged_by_valid_angle_fixture() -> None:
    prior = preview_tee_connector(build_tee_r2_request())
    corrected = preview_tee_connector(build_tee_r7_angle_request())

    assert prior.interface_b.preview.automatic_demand_result == (
        corrected.interface_b.preview.automatic_demand_result
    )
    assert (
        prior.interface_b.preview.geometry_status == corrected.interface_b.preview.geometry_status
    )
    assert prior.interface_b.preview.method_applicability == (
        corrected.interface_b.preview.method_applicability
    )
    assert prior.interface_b.preview.qualification == corrected.interface_b.preview.qualification
    assert prior.visualization is not None
    assert corrected.visualization is not None
    assert prior.visualization.interface_b_bolts == corrected.visualization.interface_b_bolts


def test_r7_angle_path_rejects_wrong_owner_patch_identity() -> None:
    request = build_tee_r7_angle_request()
    resolved = resolve_tee_connector_request(request)
    group = resolved.context.resolved_bolt_groups[0]
    path = group.paths[0]
    placed = next(
        item for item in resolved.context.basis.placed_members if item.component.id == "tee-brace"
    )
    contact = path.layers[0].exit.surface
    wrong_candidate = path.layers[1].entry.surface

    with pytest.raises(ValueError, match="one finite opposing broad face"):
        tee_orchestration._angle_opposing_patch_for_location(
            group.bolt_group.locations[0],
            group.bolt_group_frame,
            request.connected_member_profile,
            placed,
            contact,
            (wrong_candidate,),
            float(request.bolt_diameter.to(Unit.IN).magnitude) / 2.0,
            group.tolerance,
        )


def test_r7_angle_path_rejects_nonexact_physical_layer_thickness() -> None:
    request = build_tee_r7_angle_request()

    def wrong_thickness(
        profile: MemberProfile,
        point: ExactProfileVector3D,
    ) -> AngleLegBoltPathResolution:
        resolution = resolve_angle_leg_bolt_path(profile, point)
        return replace(resolution, penetrated_thickness=Decimal("0.25"))

    with (
        patch.object(
            tee_orchestration,
            "resolve_angle_leg_bolt_path",
            side_effect=wrong_thickness,
        ),
        pytest.raises(ValueError, match="exact profile leg thickness"),
    ):
        resolve_tee_connector_request(request)


@pytest.mark.parametrize(
    ("family", "element", "material_region", "opposing", "outside", "qualification"),
    [
        (
            "CHANNEL",
            "WEB",
            "WEB",
            "WEB:VOID_FACING_INNER_BROAD",
            "WEB:EXTERIOR_BACK_BROAD",
            None,
        ),
        (
            "RECTANGULAR_HOLLOW_SECTION",
            "SIDE_WALL_2",
            "WALL_PAIR_2",
            "SIDE_WALL_2:VOID_FACING_BROAD",
            "SIDE_WALL_2:EXTERIOR_BROAD",
            INTERNAL_FASTENER_ACCESS_REQUIRED,
        ),
    ],
)
def test_r8_controlled_profile_wall_fixtures_resolve_exact_physical_paths(
    family: str,
    element: str,
    material_region: str,
    opposing: str,
    outside: str,
    qualification: str | None,
) -> None:
    request = build_tee_r8_profile_wall_request(profile_family=family)
    resolved = resolve_tee_connector_request(request)
    preview = preview_tee_connector(request)
    serialized = serialize_tee_connector_preview(preview).model_dump(mode="json")
    group = resolved.context.resolved_bolt_groups[0]
    brace_layers = tuple(path.layers[0] for path in group.paths)

    assert len(group.paths) == 4
    assert {layer.definition.physical_element_id for layer in brace_layers} == {element}
    assert {layer.physical_element.source_element.role.value for layer in brace_layers} == {element}
    assert {layer.physical_element.source_material_region.id for layer in brace_layers} == {
        material_region
    }
    assert {layer.entry.surface.id for layer in brace_layers} == {opposing}
    assert {layer.exit.surface.id for layer in brace_layers} == {outside}
    assert all(layer.raw_thickness == pytest.approx(0.5) for layer in brace_layers)
    assert all(layer.raw_minimum_patch_clearance >= 0 for layer in brace_layers)
    assert preview.design_check_ready is (family != "RECTANGULAR_HOLLOW_SECTION")
    assert preview.connected_member_profile.profile_family is MemberProfileFamily(family)
    assert preview.visualization is not None
    assert preview.visualization.connected_member_profile.profile_family is MemberProfileFamily(
        family
    )
    if qualification is None:
        assert INTERNAL_FASTENER_ACCESS_REQUIRED not in preview.warnings
    else:
        assert qualification not in preview.warnings
        assert qualification not in serialized["warnings"]
        assert qualification not in serialized["result"]["warnings"]
        assert preview.design_limitations == (
            "RHS_LOCAL_WALL_RESPONSE",
            "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
        )
        assert all(
            trace.hardware.internal_hardware_count == 0
            for trace in preview.rectangular_full_through_paths
        )


@pytest.mark.parametrize("family", ["CHANNEL", "RECTANGULAR_HOLLOW_SECTION"])
def test_r8_exact_complete_hole_boundary_is_smallest_valid_end_adjustment(
    family: str,
) -> None:
    for invalid in ("1.3", "1.7814"):
        with pytest.raises(ValueError, match="one finite opposing broad face"):
            resolve_tee_connector_request(
                build_tee_r8_profile_wall_request(
                    profile_family=family,
                    unloaded_end_distance=invalid,
                )
            )

    resolved = resolve_tee_connector_request(
        build_tee_r8_profile_wall_request(
            profile_family=family,
            unloaded_end_distance="1.7815",
        )
    )

    assert len(resolved.context.resolved_bolt_groups[0].paths) == 4


@pytest.mark.parametrize(
    ("family", "expected"),
    [
        (
            "CHANNEL",
            (
                ExactProfileVector3D(Decimal("-1"), Decimal("0"), Decimal("-2.2185")),
                ExactProfileVector3D(Decimal("-3"), Decimal("0"), Decimal("-2.2185")),
                ExactProfileVector3D(Decimal("-1"), Decimal("0"), Decimal("-0.2185")),
                ExactProfileVector3D(Decimal("-3"), Decimal("0"), Decimal("-0.2185")),
            ),
        ),
        (
            "RECTANGULAR_HOLLOW_SECTION",
            (
                ExactProfileVector3D(Decimal("-1"), Decimal("2"), Decimal("2.2185")),
                ExactProfileVector3D(Decimal("-3"), Decimal("2"), Decimal("2.2185")),
                ExactProfileVector3D(Decimal("-1"), Decimal("2"), Decimal("0.2185")),
                ExactProfileVector3D(Decimal("-3"), Decimal("2"), Decimal("0.2185")),
            ),
        ),
    ],
)
def test_r8_exact_owner_points_are_derived_without_float_reconstruction(
    family: str,
    expected: tuple[ExactProfileVector3D, ...],
) -> None:
    request = build_tee_r8_profile_wall_request(profile_family=family)
    surface = require_direct_tee_profile_surface(request.connected_member_profile)

    actual = tuple(
        tee_orchestration._exact_profile_wall_outer_point(
            surface,
            request.connector_dimensions,
            request.interface_a_layout,
            row,
            line,
        )
        for row in range(2)
        for line in range(2)
    )

    assert actual == expected


def test_r8_profile_wall_change_leaves_interface_b_exact() -> None:
    channel = preview_tee_connector(build_tee_r8_profile_wall_request(profile_family="CHANNEL"))
    rhs = preview_tee_connector(
        build_tee_r8_profile_wall_request(profile_family="RECTANGULAR_HOLLOW_SECTION")
    )

    assert (
        channel.interface_b.preview.automatic_demand_result
        == rhs.interface_b.preview.automatic_demand_result
    )
    assert channel.interface_b.preview.geometry_status == rhs.interface_b.preview.geometry_status
    assert (
        channel.interface_b.preview.method_applicability
        == rhs.interface_b.preview.method_applicability
    )
    assert channel.interface_b.preview.qualification == rhs.interface_b.preview.qualification
    assert channel.visualization is not None
    assert rhs.visualization is not None
    assert channel.visualization.interface_b_bolts == rhs.visualization.interface_b_bolts


def test_r8_profile_wall_path_rejects_wrong_owner_patch_identity() -> None:
    request = build_tee_r8_profile_wall_request(profile_family="CHANNEL")
    resolved = resolve_tee_connector_request(request)
    group = resolved.context.resolved_bolt_groups[0]
    wrong_candidate = group.paths[0].layers[1].entry.surface
    surface = require_direct_tee_profile_surface(request.connected_member_profile)
    exact_point = tee_orchestration._exact_profile_wall_outer_point(
        surface,
        request.connector_dimensions,
        request.interface_a_layout,
        0,
        0,
    )

    with pytest.raises(ValueError, match="one finite opposing broad face"):
        tee_orchestration._profile_wall_opposing_patch_for_location(
            group.bolt_group.locations[0],
            group.bolt_group_frame,
            request.connected_member_profile,
            exact_point,
            (wrong_candidate,),
            0.2815,
            Decimal("0.2815"),
            group.tolerance,
        )


def test_r8_profile_wall_path_rejects_nonexact_physical_layer_thickness() -> None:
    request = build_tee_r8_profile_wall_request(profile_family="CHANNEL")

    def wrong_thickness(
        profile: MemberProfile,
        point: ExactProfileVector3D,
        radius: Decimal,
    ) -> ProfileWallBoltPathResolution:
        resolution = resolve_profile_wall_bolt_path(profile, point, radius)
        return replace(resolution, penetrated_thickness=Decimal("0.25"))

    with (
        patch.object(
            tee_orchestration,
            "resolve_profile_wall_bolt_path",
            side_effect=wrong_thickness,
        ),
        pytest.raises(ValueError, match="exact physical wall thickness"),
    ):
        resolve_tee_connector_request(request)
