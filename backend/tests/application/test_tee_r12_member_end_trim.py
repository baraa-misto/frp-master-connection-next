"""Controlled Stage 3.2-R12 member-end trim and clearance regressions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import frp_master_connection.application.tee_orchestration as tee_orchestration_module
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    TeeAssemblyStatus,
    TeeConnectorOrchestrationRequest,
    TeeMemberEndInterferenceStatus,
    design_check_tee_connector,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.application.visualization import VisualizationPrimitiveKind
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    AssemblyMember,
    PositionVector3D,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import (
    AuthoritativeCutPlane3D,
    GeometryComparisonTolerance,
    PlacedComponentGeometry3D,
    TrimmedComponentSolids3D,
    Vector3D,
    place_member,
    trim_placed_rectangular_component,
)
from tests.tee_fixtures import (
    build_tee_r2_payload,
    build_tee_r7_angle_payload,
    build_tee_r8_profile_wall_payload,
)

_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "stage_3_2_r12_member_end_trim_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "55F54BBCB7A45D6AE1E7065278D65F0F1E3EFF8943171BE73BE3FCC9DAD765DE"


def _group_offset(
    payload: dict[str, Any], *, vertical_a: str = "0", horizontal_a: str = "0"
) -> None:
    for key in ("interface_a_layout", "interface_b_layout"):
        layout = payload[key]
        layout["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
        layout["vertical_offset"] = {
            "value": vertical_a if key == "interface_a_layout" else "0",
            "unit": payload["source_length_unit"],
        }
        layout["horizontal_offset"] = {
            "value": horizontal_a if key == "interface_a_layout" else "0",
            "unit": payload["source_length_unit"],
        }


def _payload(
    clearance: str | None,
    *,
    family: str = "ANGLE",
    angle: str = "25",
    vertical_a: str = "0",
    horizontal_a: str = "0",
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    if family == "ANGLE":
        payload = build_tee_r7_angle_payload()
    elif family in {"CHANNEL", "RECTANGULAR_HOLLOW_SECTION"}:
        payload = build_tee_r8_profile_wall_payload(profile_family=family)
    else:
        payload = build_tee_r2_payload(profile_family=family, unit_system=unit_system)
    payload["brace_inclination_degrees"] = angle
    _group_offset(payload, vertical_a=vertical_a, horizontal_a=horizontal_a)
    if clearance is not None:
        payload["connected_member_end_trim_enabled"] = True
        payload["connected_member_end_clearance"] = {
            "value": clearance,
            "unit": payload["source_length_unit"],
        }
    return payload


def _request(payload: dict[str, Any]) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))


def test_r12_owner_golden_is_byte_exact_and_complete() -> None:
    raw = _GOLDEN_PATH.read_bytes()
    fixture = json.loads(raw)

    assert hashlib.sha256(raw).hexdigest().upper() == _GOLDEN_SHA256
    assert fixture["version"] == "RC1"
    assert fixture["semantic_clearance_frame"]["reference_plane_id"] == (
        "TEE_FLANGE_INNER_CLEARANCE_PLANE"
    )
    assert [item["id"] for item in fixture["benchmarks"]] == [
        "R12_T1_TRIM_DISABLED_BACKWARD_COMPATIBILITY",
        "R12_T2_ANGLE_25_ZERO_CLEARANCE",
        "R12_T3_ANGLE_25_QUARTER_INCH_CLEARANCE",
        "R12_T4_ANGLE_25_HALF_INCH_CLEARANCE",
        "R12_T5_NEGATIVE_CLEARANCE_REJECTED",
        "R12_T6_TRIM_EDGE_CLEARANCE_IS_PHYSICAL",
        "R12_T7_PROFILE_GENERIC_CUT",
    ]


def test_r12_trim_disabled_or_omitted_preserves_legacy_geometry_and_fingerprint() -> None:
    omitted = build_tee_r7_angle_payload()
    explicit_off = deepcopy(omitted)
    explicit_off["connected_member_end_trim_enabled"] = False

    omitted_preview = preview_tee_connector(_request(omitted))
    explicit_preview = preview_tee_connector(_request(explicit_off))

    assert omitted_preview.engineering_fingerprint == explicit_preview.engineering_fingerprint
    assert omitted_preview.interface_a.interface_fingerprint == (
        explicit_preview.interface_a.interface_fingerprint
    )
    assert omitted_preview.visualization is not None
    assert explicit_preview.visualization is not None
    assert omitted_preview.visualization.base_connection.primitives == (
        explicit_preview.visualization.base_connection.primitives
    )
    assert not omitted_preview.connected_member_end_trim.enabled
    assert omitted_preview.connected_member_end_trim.normalized_clearance is None


@pytest.mark.parametrize(
    ("clearance", "expected_origin_x"),
    [("0", Decimal("0.5")), ("0.25", Decimal("0.75")), ("0.5", Decimal("1"))],
)
def test_r12_t2_t3_t4_exact_parallel_cut_plane_and_gap(
    clearance: str,
    expected_origin_x: Decimal,
) -> None:
    preview = preview_tee_connector(_request(_payload(clearance)))
    trace = preview.connected_member_end_trim

    assert trace.enabled
    assert trace.reference_plane_id == "TEE_FLANGE_INNER_CLEARANCE_PLANE"
    assert trace.cut_plane_id == "CONNECTED_MEMBER_END_CUT_PLANE"
    assert trace.cut_plane_normal == trace.reference_plane_normal
    assert trace.reference_plane_normal.x == 1
    assert trace.cut_plane_origin is not None
    assert Decimal(str(trace.cut_plane_origin.x)) == expected_origin_x
    assert trace.measured_plane_clearance is not None
    assert trace.measured_plane_clearance.magnitude == Decimal(clearance)
    assert trace.interference_status is TeeMemberEndInterferenceStatus.TRIMMED_CLEAR


def test_r12_negative_or_non_authoritative_clearance_is_rejected() -> None:
    missing = _payload(None)
    missing["connected_member_end_trim_enabled"] = True
    with pytest.raises(ValidationError, match="is required"):
        TeeConnectorRequestDTO.model_validate(missing)
    with pytest.raises(ValidationError, match="must be nonnegative"):
        TeeConnectorRequestDTO.model_validate(_payload("-0.01"))
    wrong_unit = _payload("0.25")
    wrong_unit["connected_member_end_clearance"]["unit"] = "mm"
    with pytest.raises(ValidationError, match="source_length_unit"):
        TeeConnectorRequestDTO.model_validate(wrong_unit)
    off_with_value = _payload(None)
    off_with_value["connected_member_end_clearance"] = {"value": "0", "unit": "in"}
    with pytest.raises(ValidationError, match="not authoritative"):
        TeeConnectorRequestDTO.model_validate(off_with_value)


def test_r12_domain_request_trim_guards_are_fail_closed() -> None:
    request = _request(_payload(None))
    with pytest.raises(TypeError, match="must be a bool"):
        replace(request, connected_member_end_trim_enabled=cast(Any, 1))
    with pytest.raises(TypeError, match="must be a PhysicalQuantity"):
        replace(request, connected_member_end_trim_enabled=True)
    with pytest.raises(ValueError, match="nonnegative length"):
        replace(
            request,
            connected_member_end_trim_enabled=True,
            connected_member_end_clearance=PhysicalQuantity.of(Decimal("-0.01"), Unit.IN),
        )
    with pytest.raises(ValueError, match="absent when trim is disabled"):
        replace(
            request,
            connected_member_end_clearance=PhysicalQuantity.of(Decimal("0"), Unit.IN),
        )


def test_r12_inclination_does_not_rotate_connector_cut_plane() -> None:
    positive = resolve_tee_connector_request(_request(_payload("0.25", angle="25")))
    negative = resolve_tee_connector_request(_request(_payload("0.25", angle="0")))

    assert positive.connected_member_end_trim.cut_plane_normal == (
        negative.connected_member_end_trim.cut_plane_normal
    )
    assert positive.connected_member_end_trim.cut_plane_origin == (
        negative.connected_member_end_trim.cut_plane_origin
    )
    assert positive.trimmed_connected_member_solids is not None
    assert negative.trimmed_connected_member_solids is not None
    assert positive.trimmed_connected_member_solids.geometry_fingerprint != (
        negative.trimmed_connected_member_solids.geometry_fingerprint
    )


@pytest.mark.parametrize(
    ("family", "vertical_a", "minimum_solids"),
    [
        ("ANGLE", "0", 2),
        ("CHANNEL", "1", 3),
        ("WIDE_FLANGE_I", "0", 3),
        ("RECTANGULAR_HOLLOW_SECTION", "1", 4),
        ("FLAT_PLATE", "0", 1),
    ],
)
def test_r12_generic_trim_clips_actual_standard_profile_solids(
    family: str,
    vertical_a: str,
    minimum_solids: int,
) -> None:
    resolved = resolve_tee_connector_request(
        _request(_payload("0.25", family=family, vertical_a=vertical_a))
    )
    trimmed = resolved.trimmed_connected_member_solids

    assert trimmed is not None
    assert len(trimmed.solids) >= minimum_solids
    assert len(trimmed.fabricated_face_ids) >= minimum_solids
    assert all(solid.triangulated_points for solid in trimmed.solids)


def test_r12_off_reports_actual_interference_and_on_replaces_member_with_meshes() -> None:
    off = preview_tee_connector(_request(_payload(None)))
    on = preview_tee_connector(_request(_payload("0.25")))

    assert off.connected_member_end_trim.interference_status is (
        TeeMemberEndInterferenceStatus.INTERFERENCE_DETECTED
    )
    assert off.connected_member_end_trim.interfering_physical_element_ids == (
        "LEG_1",
        "LEG_2",
    )
    assert "CONNECTED_MEMBER_INTERFERES_WITH_TEE_FLANGE_ROOT" in off.warnings
    assert on.visualization is not None
    member_primitives = tuple(
        item
        for item in on.visualization.base_connection.view_extension_primitives
        if item.owner_id == "tee-brace"
    )
    assert member_primitives
    assert all(item.kind is VisualizationPrimitiveKind.TRIANGLE_MESH for item in member_primitives)
    assert all(item.points for item in member_primitives)


def test_r12_physical_hole_clearances_govern_and_change_with_cut_not_legacy_edge() -> None:
    quarter = preview_tee_connector(_request(_payload("0.25")))
    half = preview_tee_connector(_request(_payload("0.5")))
    quarter_trace = quarter.connected_member_end_trim
    half_trace = half.connected_member_end_trim

    assert len(quarter_trace.bolt_clearances) == 4
    assert quarter_trace.governing_bolt_id == "tee-bolt-a-r1-l2"
    assert quarter_trace.minimum_hole_edge_clearance is not None
    assert half_trace.minimum_hole_edge_clearance is not None
    assert quarter_trace.minimum_hole_edge_clearance.magnitude == Decimal("0.4685")
    assert half_trace.minimum_hole_edge_clearance.magnitude == Decimal("0.2185")
    assert quarter_trace.minimum_hole_edge_clearance.magnitude != (
        quarter.interface_a.placement.equivalent_edge_distances.unloaded_end_distance
    )


def test_r12_r11_user_offset_away_increases_trim_edge_clearance_without_auto_move() -> None:
    centered = preview_tee_connector(_request(_payload("0.25")))
    moved = preview_tee_connector(_request(_payload("0.25", horizontal_a="-0.5")))
    centered_clearance = centered.connected_member_end_trim.minimum_hole_edge_clearance
    moved_clearance = moved.connected_member_end_trim.minimum_hole_edge_clearance

    assert centered_clearance is not None
    assert moved_clearance is not None
    assert moved_clearance.magnitude - centered_clearance.magnitude == Decimal("0.5")
    assert moved.interface_a.placement.horizontal_offset.magnitude == Decimal("-0.5")


def test_r12_negative_hole_edge_clearance_is_invalid_with_exact_recovery() -> None:
    preview = preview_tee_connector(_request(_payload("1")))
    trace = preview.connected_member_end_trim

    assert preview.assembly_status is TeeAssemblyStatus.INVALID_GEOMETRY
    assert trace.minimum_hole_edge_clearance is not None
    assert trace.minimum_hole_edge_clearance.magnitude == Decimal("-0.2815")
    assert trace.exact_deficit is not None
    assert trace.exact_deficit.magnitude == Decimal("0.2815")
    assert trace.recovery_guidance == (
        "Move the bolt group away from the fabricated end by at least 0.2815 in."
    )


def test_r12_trimmed_free_edge_does_not_silently_enter_existing_resistance() -> None:
    request = _request(_payload("0.25"))
    preview = preview_tee_connector(request)
    design = design_check_tee_connector(request)

    assert not preview.design_check_ready
    assert "CONNECTED_MEMBER_TRIM_RESISTANCE_MAPPING_NOT_EVALUATED" in preview.warnings
    assert design.interface_a.design is None
    assert design.assembly_status is TeeAssemblyStatus.NOT_EVALUATED


def test_r12_defensive_geometry_boundaries_reject_parallel_axis_and_missing_scene() -> None:
    request = _request(_payload(None))
    resolved = resolve_tee_connector_request(request)
    group = resolved.context.resolved_bolt_groups[0]
    profile = request.connected_member_profile
    placed_brace = next(
        item for item in resolved.context.basis.placed_members if item.component.id == "tee-brace"
    )
    contact = next(
        patch
        for surface_set in resolved.context.basis.component_surface_sets
        for patch in surface_set.patches
        if patch.id == resolved.connected_member_profile.surface_patch_id
    )
    with pytest.raises(ValueError, match="must intersect"):
        tee_orchestration_module._owner_point_on_contact(
            group.master_centers[0].bolt_location,
            group.bolt_group_frame,
            profile,
            placed_brace,
            contact,
            GeometryComparisonTolerance(1e-9, 2.0),
        )

    trimmed = resolve_tee_connector_request(
        _request(_payload("0.25"))
    ).trimmed_connected_member_solids
    assert trimmed is not None
    preview = preview_tee_connector(request)
    assert preview.visualization is not None
    with pytest.raises(RuntimeError, match="unavailable"):
        tee_orchestration_module._trimmed_visualization(
            preview.visualization.base_connection,
            replace(trimmed, component_id="missing-member"),
        )


def test_r12_parallel_member_cut_and_remaining_material_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    off_request = _request(_payload(None))
    on_request = _request(_payload("0.25"))
    resolved = resolve_tee_connector_request(off_request)
    brace = next(
        item for item in resolved.context.basis.placed_members if item.component.id == "tee-brace"
    )
    tee = resolved.context.basis.placed_connectors[0]
    group = resolved.context.resolved_bolt_groups[0]
    longitudinal, transverse, normal, _ = tee_orchestration_module._unit_axes(
        on_request.support_role,
        on_request.selected_support_flange,
    )
    profile_surface = require_direct_tee_profile_surface(on_request.connected_member_profile)
    parallel_brace = place_member(
        cast(AssemblyMember, brace.component),
        brace.cross_section,
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(0.0, 8.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
        brace.section_offset,
    )
    with pytest.raises(ValueError, match="must cross"):
        tee_orchestration_module._member_end_trim(
            on_request,
            parallel_brace,
            tee,
            normal,
            longitudinal,
            transverse,
            group,
            Decimal("0.2815"),
            profile_surface,
        )

    original_trim = trim_placed_rectangular_component

    def retained_material_behind_reference(
        placed: PlacedComponentGeometry3D,
        plane: AuthoritativeCutPlane3D,
    ) -> TrimmedComponentSolids3D:
        result = original_trim(placed, plane)
        first_solid = result.solids[0]
        first_face = first_solid.faces[0]
        first_point = first_face.vertices[0]
        invalid_face = replace(
            first_face,
            vertices=(
                PositionVector3D(0.0, first_point.y, first_point.z),
                *first_face.vertices[1:],
            ),
        )
        invalid_solid = replace(
            first_solid,
            faces=(invalid_face, *first_solid.faces[1:]),
        )
        return replace(result, solids=(invalid_solid, *result.solids[1:]))

    monkeypatch.setattr(
        tee_orchestration_module,
        "trim_placed_rectangular_component",
        retained_material_behind_reference,
    )
    trace, _ = tee_orchestration_module._member_end_trim(
        on_request,
        brace,
        tee,
        normal,
        longitudinal,
        transverse,
        group,
        Decimal("0.2815"),
        profile_surface,
    )
    assert trace.interference_status is TeeMemberEndInterferenceStatus.REMAINING_INTERFERENCE
    assert not trace.geometry_valid


def test_r12_api_trace_and_si_normalization_are_deterministic() -> None:
    payload = _payload("6.35", family="FLAT_PLATE", unit_system="SI")
    first = preview_tee_connector(_request(payload))
    second = preview_tee_connector(_request(payload))
    serialized = serialize_tee_connector_preview(first)

    assert first.engineering_fingerprint == second.engineering_fingerprint
    assert first.connected_member_end_trim.measured_plane_clearance is not None
    assert first.connected_member_end_trim.measured_plane_clearance.magnitude == Decimal("6.35")
    trim_result = cast(dict[str, Any], serialized.result["connected_member_end_trim"])
    assert trim_result["cut_plane_id"] == ("CONNECTED_MEMBER_END_CUT_PLANE")
