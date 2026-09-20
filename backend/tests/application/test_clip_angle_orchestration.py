"""Stage 3.3A controlled clip-angle application and golden tests."""

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import frp_master_connection.application.clip_angle_orchestration as clip_module
from frp_master_connection.application import (
    VisualizationPrimitiveKind,
    build_placed_component_visualization_snapshots,
    design_check_clip_angle,
    preview_clip_angle,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowDemandSource,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.calculation.eccentric_demand import DemandAnalysisAvailability
from frp_master_connection.calculation.multirow_engine import MultiRowOverallDisposition
from frp_master_connection.domain import (
    ClipAngleBoltLayout,
    ClipAngleBoltPlacementMode,
    ClipAngleDimensions,
    ClipAngleHand,
    ClipAngleLengthAnchor,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    ComponentMaterialKind,
    FlatPlateProfileDimensions,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
    RoundHollowProfileDimensions,
    WideFlangeIProfileDimensions,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import (
    CartesianFrame3D,
    PlacedComponentGeometry3D,
    PlanarRectangularSurface3D,
    UnitVector3D,
    create_component_surface_set,
)
from tests.clip_angle_fixtures import build_clip_angle_request

_REPOSITORY_ROOT = Path(__file__).parents[3]
_CONTROLLED_ARTIFACTS = (
    (
        _REPOSITORY_ROOT
        / "docs/engineering/STAGE_3_3A_SINGLE_CLIP_ANGLE_ENGINEERING_SPECIFICATION_RC1.md",
        "275D9E83F0C9E171723C274876835EE7D8DD279809429CCEC40FDDC7CD1A7F21",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _REPOSITORY_ROOT
        / "backend/tests/golden/stage_3_3a_single_clip_angle_golden_benchmarks_rc1.json",
        "C2FFE88CF80C474C39099D8C74682B116DAA8CACFCF29F42C54862C7AC577159",
        None,
    ),
    (
        _REPOSITORY_ROOT / "docs/qa/STAGE_3_3A_SINGLE_CLIP_ANGLE_AUTHORITY_LEDGER_RC1.md",
        "A2936781B1EB3CD80F4F36448ADEF3FA034D83127E68DBBEF678029FBBB9FFEB",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)

_PROFILE_ELEMENTS = {
    "FLAT_PLATE": ("PLATE",),
    "ANGLE": ("LEG_1", "LEG_2"),
    "CHANNEL": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "WIDE_FLANGE_I": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "RECTANGULAR_HOLLOW_SECTION": (
        "TOP_WALL",
        "BOTTOM_WALL",
        "SIDE_WALL_1",
        "SIDE_WALL_2",
    ),
}

_R1_ENGINEERING_FINGERPRINTS = {
    ("BRACE", "FLAT_PLATE"): "01b37ccfb93c33c700157ee16b1d70fe6d2ac0d502b77403654ee81cb4272d71",
    ("BRACE", "ANGLE"): "d5f64bc569730599664fd29f7e0800aa256ff09061efb9fffa5ae627be137ac2",
    ("BRACE", "CHANNEL"): "deea9ea9408ebd5a9e8c212e2266b9e51edf2339fb7056aace19ef1e83447dac",
    ("BRACE", "WIDE_FLANGE_I"): "2039514faf34f9889f3c384e6179630b4e77576fccb201c8938369f290db05b6",
    (
        "BRACE",
        "RECTANGULAR_HOLLOW_SECTION",
    ): "8228c0573f32282cc00097d9ab037538abca29518a3b5f97c568abf4a8a31d33",
    ("BEAM", "FLAT_PLATE"): "3fe6936cf987a040d3aabab833c10563bfdb178bb6b14af9f4040f9834544c0c",
    ("BEAM", "ANGLE"): "14894b938455d80d6e38986b48adb3ae38087120917ce71cf788d92104737656",
    ("BEAM", "CHANNEL"): "eee136baca282b251850c5ec8b99f599ba12837a8063c719e363d946bf928974",
    ("BEAM", "WIDE_FLANGE_I"): "598499a9d0fa4f4cf32b4e8b669111010d948728b3124a0b524f59cad6251ef1",
    (
        "BEAM",
        "RECTANGULAR_HOLLOW_SECTION",
    ): "2c168d03538ec9a98e996141fd9e8cf07b1588e7a4cf246562a2f7fa3c3ae563",
}


def _with_clear_wide_flange_web(
    request: clip_module.ClipAngleOrchestrationRequest,
) -> clip_module.ClipAngleOrchestrationRequest:
    dimensions = cast(WideFlangeIProfileDimensions, request.connected_member_profile.dimensions)
    clear_depth = (
        request.connector_dimensions.connector_length + Decimal(4) * dimensions.flange_thickness
    )
    return replace(
        request,
        connected_member_profile=replace(
            request.connected_member_profile,
            dimensions=replace(dimensions, depth=clear_depth),
        ),
    )


def _contact_clear_request(
    profile_family: str,
    *,
    connected_role: str = "BRACE",
    unit_system: str = "US_CUSTOMARY",
) -> clip_module.ClipAngleOrchestrationRequest:
    request = build_clip_angle_request(
        profile_family=profile_family,
        connected_role=connected_role,
        unit_system=unit_system,
    )
    return _with_clear_wide_flange_web(request) if profile_family == "WIDE_FLANGE_I" else request


def _valid_trim_request(
    profile_family: str,
    *,
    inclination: str = "25",
    clearance: str = "0.5",
    connected_role: str = "BRACE",
    orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0,
) -> clip_module.ClipAngleOrchestrationRequest:
    request = build_clip_angle_request(
        profile_family=profile_family,
        connected_role=connected_role,
    )
    profile = request.connected_member_profile
    if profile_family == "WIDE_FLANGE_I":
        profile = replace(
            profile,
            dimensions=replace(
                cast(WideFlangeIProfileDimensions, profile.dimensions),
                depth=Decimal("10"),
                flange_width=Decimal("8"),
                web_thickness=Decimal("0.5"),
                flange_thickness=Decimal("0.5"),
                member_length=Decimal("8"),
            ),
        )
    return replace(
        request,
        connector_dimensions=replace(
            request.connector_dimensions,
            connector_length=Decimal("6"),
        ),
        connected_member_profile=replace(profile, orientation=orientation),
        interface_a_layout=replace(
            request.interface_a_layout,
            heel_edge_distance=Decimal("1"),
        ),
        connected_member_inclination_degrees=Decimal(inclination),
        connected_member_end_trim_enabled=True,
        connected_member_end_clearance=PhysicalQuantity.of(clearance, Unit.IN),
    )


def _box_projection(
    value: clip_module.ClipAngleBoxTrace,
    axis: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal]:
    center = tuple(item.to(Unit.IN).magnitude for item in value.center)
    half = (
        value.size_s.to(Unit.IN).magnitude / Decimal(2),
        value.size_p.to(Unit.IN).magnitude / Decimal(2),
        value.size_l.to(Unit.IN).magnitude / Decimal(2),
    )
    projected_center = sum(
        (component * direction for component, direction in zip(center, axis, strict=True)),
        Decimal(0),
    )
    radius = sum(
        (
            extent
            * abs(
                sum(
                    (
                        basis_component * direction
                        for basis_component, direction in zip(basis, axis, strict=True)
                    ),
                    Decimal(0),
                )
            )
            for extent, basis in zip(half, value.basis, strict=True)
        ),
        Decimal(0),
    )
    return projected_center - radius, projected_center + radius


def test_controlled_stage_3_3a_artifacts_are_byte_exact_and_golden_driven() -> None:
    for path, digest, sentinel in _CONTROLLED_ARTIFACTS:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == digest
        if sentinel is not None:
            assert sentinel in raw

    golden = json.loads(_CONTROLLED_ARTIFACTS[1][0].read_bytes())
    assert golden["artifact"] == (
        "FRP_MASTER_CONNECTION_STAGE_3_3A_SINGLE_CLIP_ANGLE_GOLDEN_BENCHMARKS_RC1"
    )
    assert [case["id"] for case in golden["benchmarks"]] == [
        "G1_DEFAULT_RIGHT_HAND_CONCENTRIC_2X2_2X2",
        "G2_INDEPENDENT_GROUPS_A_2X1_B_2X2",
        "G3_COLUMN_BEAM_SUPPORT_LOCAL_INVARIANCE",
        "G4_CLIP_ANGLE_HAND_MIRROR",
        "G5_INCLINED_MEMBER_FIXED_GRID_WITH_TRIM",
        "G6_SUPPORT_INTERFACE_NORMAL_ACTION_FAIL_CLOSED",
        "G7_US_SI_EQUIVALENCE",
        "G8_CLIP_ANGLE_MATERIAL_REGIONS",
        "G9_COMPLETE_FASTENER_PRESENTATION",
        "G10_CONNECTOR_BODY_LIMITATION_AND_FAILURE_PRECEDENCE",
    ]


def _magnitudes(result: clip_module.ClipAnglePreviewResult, side: str) -> tuple[Decimal, ...]:
    interface = result.interface_a if side == "A" else result.interface_b
    scenario = interface.demand.scenarios[0]
    return tuple(item.total_force_magnitude.to(Unit.KIP).magnitude for item in scenario.per_bolt)


def test_g1_controlled_geometry_action_and_body_limitation() -> None:
    result = preview_clip_angle(build_clip_angle_request())

    assert tuple(item.magnitude for item in result.interface_a.placement.width_coordinates) == (
        Decimal("1.25"),
        Decimal("3.25"),
    )
    assert tuple(item.magnitude for item in result.interface_b.placement.length_coordinates) == (
        Decimal("-1"),
        Decimal("1"),
    )
    for placement in (result.interface_a.placement, result.interface_b.placement):
        assert placement.clearances.heel.magnitude == Decimal("0.4685")
        assert placement.clearances.free_edge.magnitude == Decimal("0.4685")
        assert placement.clearances.positive_length_end.magnitude == Decimal("2.7185")
        assert placement.clearances.negative_length_end.magnitude == Decimal("2.7185")
    assert result.interface_a.normal_component.magnitude == 0
    assert result.interface_b.normal_component.magnitude == 0
    assert _magnitudes(result, "A") == (Decimal("0.75"),) * 4
    assert _magnitudes(result, "B") == (Decimal("0.75"),) * 4
    assert all(item.residual_moment.magnitude == 0 for item in result.interface_a.demand.scenarios)
    assert result.connector_body_required_check == "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE"
    assert result.connector_body_status.value == "NOT_EVALUATED"
    assert result.ordinary_pass_allowed is False
    assert result.resistance_evaluated is False


def test_g2_independent_groups_have_independent_geometry_and_demands() -> None:
    request = build_clip_angle_request()
    layout_a = replace(
        request.interface_a_layout,
        bolts_per_row=1,
        placement_mode=ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
        length_offset=Decimal(0),
        width_offset=Decimal(0),
    )
    changed = preview_clip_angle(replace(request, interface_a_layout=layout_a))
    baseline = preview_clip_angle(request)

    assert len(changed.interface_a.placement.bolts) == 2
    assert len(changed.interface_b.placement.bolts) == 4
    assert _magnitudes(changed, "A") == (Decimal("1.5"),) * 2
    assert _magnitudes(changed, "B") == (Decimal("0.75"),) * 4
    assert (
        changed.interface_b.placement.geometry_fingerprint
        == baseline.interface_b.placement.geometry_fingerprint
    )


def test_g3_support_role_reuses_local_geometry_and_changes_support_transform() -> None:
    column = preview_clip_angle(build_clip_angle_request())
    beam = preview_clip_angle(
        replace(build_clip_angle_request(), support_role=ClipAngleSupportRole.W_BEAM_FLANGE)
    )

    assert (
        column.interface_a.placement.width_coordinates
        == beam.interface_a.placement.width_coordinates
    )
    assert (
        column.interface_b.placement.length_coordinates
        == beam.interface_b.placement.length_coordinates
    )
    assert _magnitudes(column, "A") == _magnitudes(beam, "A")
    assert column.visualization is not None
    assert beam.visualization is not None
    column_support = next(
        item for item in column.visualization.boxes if item.role == "SELECTED_W_FLANGE"
    )
    beam_support = next(
        item for item in beam.visualization.boxes if item.role == "SELECTED_W_FLANGE"
    )
    assert column_support.size_s != beam_support.size_s


def test_g4_hand_mirrors_centers_axes_and_preserves_clearances() -> None:
    positive = preview_clip_angle(build_clip_angle_request())
    negative = preview_clip_angle(
        replace(build_clip_angle_request(), hand=ClipAngleHand.NEGATIVE_S_SIDE)
    )

    for positive_interface, negative_interface in (
        (positive.interface_a, negative.interface_a),
        (positive.interface_b, negative.interface_b),
    ):
        assert positive_interface.placement.clearances == negative_interface.placement.clearances
        assert _magnitudes(
            positive, "A" if positive_interface is positive.interface_a else "B"
        ) == _magnitudes(negative, "A" if negative_interface is negative.interface_a else "B")
        for first, second in zip(
            positive_interface.placement.bolts,
            negative_interface.placement.bolts,
            strict=True,
        ):
            assert first.global_center[0].magnitude == -second.global_center[0].magnitude
            assert first.axis[0] == -second.axis[0]


def test_g5_trim_is_fixed_to_clip_angle_and_preserves_grid() -> None:
    request = build_clip_angle_request(profile_family="ANGLE")
    trimmed = preview_clip_angle(
        replace(
            request,
            connected_member_inclination_degrees=Decimal(25),
            connected_member_end_trim_enabled=True,
            connected_member_end_clearance=PhysicalQuantity.of("0.25", Unit.IN),
        )
    )
    baseline = preview_clip_angle(request)

    assert trimmed.interface_a.placement.bolts == baseline.interface_a.placement.bolts
    assert trimmed.trim.reference_plane_id == "CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE"
    assert trimmed.trim.measured_plane_clearance == PhysicalQuantity.of("0.25", Unit.IN)
    assert trimmed.trim.interference_status.value == "TRIMMED_CLEAR"
    assert trimmed.trim.geometry_valid is True


@pytest.mark.parametrize(
    ("profile_family", "expected_elements"),
    tuple((family, elements) for family, elements in _PROFILE_ELEMENTS.items()),
)
def test_r4_trims_every_real_profile_solid_and_publishes_only_authoritative_meshes(
    profile_family: str,
    expected_elements: tuple[str, ...],
) -> None:
    result = preview_clip_angle(_valid_trim_request(profile_family))
    visualization = result.visualization

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert visualization is not None
    assert not any(item.owner_id == "clip-angle-connected-member" for item in visualization.boxes)
    assert tuple(item.physical_element_id for item in visualization.meshes) == expected_elements
    assert all(item.owner_id == "clip-angle-connected-member" for item in visualization.meshes)
    assert all(len(item.points) >= 12 for item in visualization.meshes)
    assert result.trim.reference_plane_id == "CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE"
    assert result.trim.reference_plane_origin[1] == PhysicalQuantity.of("0.5", Unit.IN)
    assert result.trim.cut_plane_id == "CLIP_ANGLE_CONNECTED_MEMBER_END_CUT_PLANE"
    assert result.trim.cut_plane_origin is not None
    assert result.trim.cut_plane_origin[1] == PhysicalQuantity.of("1.0", Unit.IN)
    assert result.trim.measured_plane_clearance == PhysicalQuantity.of("0.5", Unit.IN)
    assert result.trim.trimmed_member_geometry_identity is not None
    assert len(result.trim.fabricated_trim_edge_ids) == len(expected_elements)
    assert result.trim.fabricated_trim_edge_id in result.trim.fabricated_trim_edge_ids
    assert result.trim.minimum_hole_edge_clearance == PhysicalQuantity.of("0.2185", Unit.IN)
    assert result.trim.exact_deficit is None


def test_r4_exact_wide_flange_reproduction_uses_current_full_profile_geometry() -> None:
    request = _valid_trim_request("WIDE_FLANGE_I")
    placed = clip_module._placed_connected_profile(request)
    source_elements = tuple(item.source_element.id for item in placed.physical_elements)
    result = preview_clip_angle(request)

    assert source_elements == ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE")
    assert result.visualization is not None
    assert tuple(item.role for item in result.visualization.meshes) == source_elements
    assert result.trim.interference_status is clip_module.ClipAngleInterferenceStatus.TRIMMED_CLEAR
    assert result.trim.geometry_valid is True


@pytest.mark.parametrize("clearance", ["0", "0.25", "0.50"])
def test_r4_requested_clearance_equals_exact_backend_plane_gap(clearance: str) -> None:
    result = preview_clip_angle(_valid_trim_request("FLAT_PLATE", clearance=clearance))

    assert result.trim.measured_plane_clearance == PhysicalQuantity.of(clearance, Unit.IN)
    assert result.trim.cut_plane_origin is not None
    assert result.trim.cut_plane_origin[1].magnitude - result.trim.reference_plane_origin[
        1
    ].magnitude == Decimal(clearance)


def test_r4_trim_recomputes_hole_clearance_without_moving_either_bolt_group() -> None:
    request = _valid_trim_request("ANGLE")
    trimmed = preview_clip_angle(request)
    untrimmed = preview_clip_angle(
        replace(
            request,
            connected_member_inclination_degrees=Decimal(0),
            connected_member_end_trim_enabled=False,
            connected_member_end_clearance=None,
        )
    )

    assert trimmed.interface_a.placement.bolts == untrimmed.interface_a.placement.bolts
    assert trimmed.interface_b.placement.bolts == untrimmed.interface_b.placement.bolts
    assert tuple(item.bolt_id for item in trimmed.trim.bolt_clearances) == tuple(
        item.bolt_id for item in trimmed.interface_a.placement.bolts
    )
    assert trimmed.trim.governing_bolt_id == "CLIP-A-R1-B1"
    assert trimmed.trim.governing_trim_edge_id == trimmed.trim.fabricated_trim_edge_id


def test_r4_negative_trim_edge_clearance_is_physical_invalidity() -> None:
    request = replace(
        _valid_trim_request("ANGLE"),
        interface_a_layout=build_clip_angle_request(profile_family="ANGLE").interface_a_layout,
    )
    result = preview_clip_angle(request)

    assert result.trim.interference_status is clip_module.ClipAngleInterferenceStatus.TRIMMED_CLEAR
    assert result.trim.minimum_hole_edge_clearance == PhysicalQuantity.of("-0.0315", Unit.IN)
    assert result.trim.exact_deficit == PhysicalQuantity.of("0.0315", Unit.IN)
    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.INVALID_GEOMETRY
    assert result.geometry_invalid_reasons == ("HOLE_EDGE_CLEARANCE_TO_FABRICATED_END_IS_NEGATIVE",)
    assert result.visualization is None


@pytest.mark.parametrize("connected_role", ["BRACE", "BEAM"])
@pytest.mark.parametrize("inclination", ["0", "5", "25", "-25", "45"])
@pytest.mark.parametrize(
    "orientation",
    [MemberProfileOrientation.ROTATION_0, MemberProfileOrientation.ROTATION_90],
)
def test_r4_trim_plane_stays_connector_fixed_across_role_inclination_and_roll(
    connected_role: str,
    inclination: str,
    orientation: MemberProfileOrientation,
) -> None:
    result = preview_clip_angle(
        _valid_trim_request(
            "ANGLE",
            connected_role=connected_role,
            inclination=inclination,
            orientation=orientation,
        )
    )

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert result.visualization is not None
    assert result.trim.reference_plane_origin[1] == PhysicalQuantity.of("0.5", Unit.IN)
    assert result.trim.cut_plane_origin is not None
    assert result.trim.cut_plane_origin[1] == PhysicalQuantity.of("1.0", Unit.IN)
    assert result.trim.measured_plane_clearance == PhysicalQuantity.of("0.5", Unit.IN)


def test_r4_trim_fails_closed_when_member_does_not_cross_cut_plane() -> None:
    with pytest.raises(ValueError, match="direction must cross the clip-angle cut plane"):
        preview_clip_angle(_valid_trim_request("ANGLE", inclination="90"))


def test_untrimmed_inclined_shape_fails_closed_for_interference() -> None:
    request = replace(
        build_clip_angle_request(profile_family="CHANNEL"),
        connected_member_inclination_degrees=Decimal(25),
    )
    result = preview_clip_angle(request)

    assert result.assembly_status.value == "INVALID_GEOMETRY"
    assert result.trim.interference_status.value == "INTERFERENCE_DETECTED"
    assert result.visualization is None
    assert result.design_check_ready is False


def test_g6_normal_action_is_retained_without_prying_or_axis_tension() -> None:
    result = preview_clip_angle(build_clip_angle_request(force=("0", "1", "0")))

    assert result.interface_a.normal_component.to(Unit.KIP).magnitude == 0
    assert result.interface_b.normal_component.to(Unit.KIP).magnitude == Decimal("1")
    assert result.interface_b.normal_action_supported is False
    assert result.interface_b.automatic_axis_tension_generated is False
    assert result.interface_b.prying_generated is False
    assert result.assembly_status.value == "NOT_EVALUATED"
    assert result.ordinary_pass_allowed is False


def test_g7_us_si_equivalence_including_all_fingerprints() -> None:
    customary = preview_clip_angle(build_clip_angle_request(unit_system="US_CUSTOMARY"))
    metric = preview_clip_angle(build_clip_angle_request(unit_system="SI"))

    assert customary.canonical_input_fingerprint == metric.canonical_input_fingerprint
    assert customary.connector_geometry_fingerprint == metric.connector_geometry_fingerprint
    assert customary.interface_a.interface_fingerprint == metric.interface_a.interface_fingerprint
    assert customary.interface_b.interface_fingerprint == metric.interface_b.interface_fingerprint
    assert customary.engineering_fingerprint == metric.engineering_fingerprint
    assert _magnitudes(customary, "A") == _magnitudes(metric, "A")


def test_g8_region_specific_material_bases_are_independent_and_right_handed() -> None:
    result = preview_clip_angle(build_clip_angle_request())
    connected, support = result.material_regions

    assert connected.physical_element_id == "CONNECTED_MEMBER_LEG"
    assert connected.lw == (Decimal(0), Decimal(0), Decimal(1))
    assert connected.cw == (Decimal(0), Decimal(-1), Decimal(0))
    assert connected.tt == (Decimal(1), Decimal(0), Decimal(0))
    assert support.physical_element_id == "SUPPORT_LEG"
    assert support.cw == (Decimal(-1), Decimal(0), Decimal(0))
    assert support.tt == (Decimal(0), Decimal(-1), Decimal(0))


def test_g9_visualization_has_eight_distinct_engineering_bolts() -> None:
    visualization = preview_clip_angle(build_clip_angle_request()).visualization
    assert visualization is not None
    bolts = (*visualization.interface_a_bolts, *visualization.interface_b_bolts)
    assert len(bolts) == 8
    assert len({(item.layer_ids, item.bolt_id) for item in bolts}) == 8
    assert visualization.bolt_diameter == PhysicalQuantity.of("0.5", Unit.IN)


@pytest.mark.parametrize("connected_role", ["BRACE", "BEAM"])
@pytest.mark.parametrize(("profile_family", "elements"), _PROFILE_ELEMENTS.items())
def test_clip_angle_visualization_uses_complete_selected_profile_solids(
    connected_role: str,
    profile_family: str,
    elements: tuple[str, ...],
) -> None:
    request = _contact_clear_request(
        profile_family=profile_family,
        connected_role=connected_role,
    )
    result = preview_clip_angle(request)
    visualization = result.visualization
    assert visualization is not None
    profile_boxes = tuple(
        item for item in visualization.boxes if item.owner_id == "clip-angle-connected-member"
    )

    assert visualization.connected_member_profile_id == request.connected_member_profile.id
    assert visualization.connected_member_role.value == connected_role
    assert visualization.connected_member_profile_family.value == profile_family
    assert visualization.connected_member_profile_orientation == (
        request.connected_member_profile.orientation
    )
    assert tuple(item.physical_element_id for item in profile_boxes) == elements
    assert len(profile_boxes) == len(elements)
    assert all(item.material_region_id is not None for item in profile_boxes)
    assert all(item.id != "clip-angle-connected-member-profile" for item in profile_boxes)
    assert len(visualization.connected_member_material_regions) == len(elements)
    assert {
        item.physical_element_id for item in visualization.connected_member_material_regions
    } == set(elements)
    selected = require_direct_tee_profile_surface(request.connected_member_profile)
    assert visualization.selected_connected_surface_id == (
        f"clip-angle-connected-member:{selected.surface_id.value}"
    )


@pytest.mark.parametrize("profile_family", tuple(_PROFILE_ELEMENTS))
def test_connected_member_contact_matrix_is_face_to_face_and_clear(
    profile_family: str,
) -> None:
    request = _contact_clear_request(profile_family)
    result = preview_clip_angle(request)
    visualization = result.visualization
    assert visualization is not None
    selected = require_direct_tee_profile_surface(request.connected_member_profile)
    placed = clip_module._placed_connected_profile(request)
    surface = next(
        item
        for item in create_component_surface_set(placed).patches
        if item.id == selected.outside_patch_id
    ).geometry
    assert isinstance(surface, PlanarRectangularSurface3D)
    assert surface.center.x == 0
    assert surface.normal == UnitVector3D(1.0, 0.0, 0.0)
    assert len(surface.corners) == 4

    connector = next(
        item for item in visualization.boxes if item.id == "clip-angle-connected-leg-solid"
    )
    profile_boxes = tuple(
        item for item in visualization.boxes if item.owner_id == "clip-angle-connected-member"
    )
    selected_box = next(
        item for item in profile_boxes if item.physical_element_id == selected.physical_element_id
    )
    axis = (Decimal(1), Decimal(0), Decimal(0))
    assert _box_projection(selected_box, axis)[1] == 0
    assert _box_projection(connector, axis)[0] == 0
    assert all(
        not clip_module._boxes_have_positive_volume_overlap(
            item,
            connector,
            request.source_length_unit,
        )
        for item in profile_boxes
    )
    assert clip_module._profile_contact_is_clear(request, visualization.boxes) is True


def test_wide_flange_web_faces_and_flange_face_resolve_on_the_exterior_side() -> None:
    for selected_surface in (
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
    ):
        request = _with_clear_wide_flange_web(
            build_clip_angle_request(profile_family="WIDE_FLANGE_I")
        )
        request = replace(
            request,
            connected_member_profile=replace(
                request.connected_member_profile,
                selected_surface=selected_surface,
            ),
        )
        result = preview_clip_angle(request)
        assert result.visualization is not None
        placed = clip_module._placed_connected_profile(request)
        selected = require_direct_tee_profile_surface(request.connected_member_profile)
        surface = next(
            item
            for item in create_component_surface_set(placed).patches
            if item.id == selected.outside_patch_id
        ).geometry
        assert isinstance(surface, PlanarRectangularSurface3D)
        assert surface.normal == UnitVector3D(1.0, 0.0, 0.0)
        assert surface.center.x == 0


def test_finite_wide_flange_web_collision_fails_closed_without_moving_the_connector() -> None:
    request = build_clip_angle_request(profile_family="WIDE_FLANGE_I")
    result = preview_clip_angle(request)
    profile_boxes, _directions = clip_module._profile_visualization(request)
    _selected, center, _positive, _negative = clip_module._anchor_coordinates(request)
    boxes = clip_module._boxes(request, center, profile_boxes)
    connected_leg = next(item for item in boxes if item.id == "clip-angle-connected-leg-solid")

    assert result.assembly_status.value == "INVALID_GEOMETRY"
    assert result.visualization is None
    assert result.trim.interference_status.value == "INTERFERENCE_DETECTED"
    assert "CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE" in result.warnings
    assert clip_module._profile_contact_is_clear(request, boxes) is False
    assert any(
        clip_module._boxes_have_positive_volume_overlap(
            item,
            connected_leg,
            request.source_length_unit,
        )
        for item in profile_boxes
    )
    assert _box_projection(connected_leg, (Decimal(1), Decimal(0), Decimal(0))) == (
        Decimal(0),
        Decimal("0.5"),
    )

    trimmed = preview_clip_angle(
        replace(
            request,
            connected_member_end_trim_enabled=True,
            connected_member_end_clearance=PhysicalQuantity.of("0.25", Unit.IN),
        )
    )
    assert trimmed.assembly_status.value == "INVALID_GEOMETRY"
    assert trimmed.trim.interference_status.value == "REMAINING_INTERFERENCE"
    assert trimmed.visualization is None


def test_support_interface_and_sharp_heel_body_remain_exact() -> None:
    request = build_clip_angle_request()
    result = preview_clip_angle(request)
    visualization = result.visualization
    assert visualization is not None
    placement = result.interface_b.placement
    assert placement.normal_axis == (Decimal(0), Decimal(-1), Decimal(0))
    assert placement.geometry_fingerprint == (
        "8d8728ebc6a34aa6d066cb19838624082f8f9eabfb4d50aef297b8c5be5ffdaf"
    )
    assert tuple(
        tuple(item.magnitude for item in bolt.global_center) for bolt in placement.bolts
    ) == (
        (Decimal("1.25"), Decimal(0), Decimal(-1)),
        (Decimal("3.25"), Decimal(0), Decimal(-1)),
        (Decimal("1.25"), Decimal(0), Decimal(1)),
        (Decimal("3.25"), Decimal(0), Decimal(1)),
    )
    connected = next(
        item for item in visualization.boxes if item.id == "clip-angle-connected-leg-solid"
    )
    support = next(
        item for item in visualization.boxes if item.id == "clip-angle-support-leg-solid"
    )
    assert _box_projection(connected, (Decimal(1), Decimal(0), Decimal(0))) == (
        Decimal(0),
        Decimal("0.5"),
    )
    assert _box_projection(support, (Decimal(0), Decimal(1), Decimal(0))) == (
        Decimal(0),
        Decimal("0.5"),
    )
    assert (
        clip_module._boxes_have_positive_volume_overlap(
            connected,
            support,
            request.source_length_unit,
        )
        is True
    )


def test_interface_a_bolt_path_layer_order_and_hardware_sides_remain_exact() -> None:
    request = build_clip_angle_request()
    placement = preview_clip_angle(request).interface_a.placement
    assert placement.normal_axis == (Decimal(1), Decimal(0), Decimal(0))
    for bolt in placement.bolts:
        assert bolt.axis == (Decimal(1), Decimal(0), Decimal(0))
        assert bolt.layer_ids == (
            "clip-angle-connected-member:SELECTED_PROFILE_REGION",
            "single-clip-angle-connector:CONNECTED_MEMBER_LEG",
        )
        assert bolt.stack_start[0] == PhysicalQuantity.of("-0.375", Unit.IN)
        assert bolt.stack_end[0] == PhysicalQuantity.of("0.5", Unit.IN)
        assert bolt.stack_start[1:] == bolt.stack_end[1:]


def test_hand_mirrors_profile_contact_without_changing_support_or_bolt_stack() -> None:
    positive_request = build_clip_angle_request()
    negative_request = replace(positive_request, hand=ClipAngleHand.NEGATIVE_S_SIDE)
    positive = preview_clip_angle(positive_request)
    negative = preview_clip_angle(negative_request)
    assert positive.visualization is not None
    assert negative.visualization is not None
    positive_profile = next(
        item
        for item in positive.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    negative_profile = next(
        item
        for item in negative.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    positive_connector = next(
        item for item in positive.visualization.boxes if item.id == "clip-angle-connected-leg-solid"
    )
    negative_connector = next(
        item for item in negative.visualization.boxes if item.id == "clip-angle-connected-leg-solid"
    )
    assert positive_profile.center[0].magnitude == -negative_profile.center[0].magnitude
    assert positive_connector.center[0].magnitude == -negative_connector.center[0].magnitude
    for first, second in zip(
        positive.interface_b.placement.bolts,
        negative.interface_b.placement.bolts,
        strict=True,
    ):
        assert second.global_center[0].magnitude == -first.global_center[0].magnitude
        assert second.global_center[1] == first.global_center[1]
        assert second.global_center[2].magnitude == -first.global_center[2].magnitude
        assert second.axis == first.axis
        assert second.layer_ids == first.layer_ids
        for first_point, second_point in (
            (first.stack_start, second.stack_start),
            (first.stack_end, second.stack_end),
        ):
            assert second_point[0].magnitude == -first_point[0].magnitude
            assert second_point[1] == first_point[1]
            assert second_point[2].magnitude == -first_point[2].magnitude
    assert clip_module._profile_contact_is_clear(
        positive_request,
        positive.visualization.boxes,
    )
    assert clip_module._profile_contact_is_clear(
        negative_request,
        negative.visualization.boxes,
    )


def test_inclination_roll_and_trim_keep_interface_a_external_and_fixed() -> None:
    request = build_clip_angle_request(profile_family="ANGLE")
    baseline = preview_clip_angle(request)
    adjusted = preview_clip_angle(
        replace(
            request,
            connected_member_profile=replace(
                request.connected_member_profile,
                orientation=MemberProfileOrientation.ROTATION_90,
            ),
            connected_member_inclination_degrees=Decimal(25),
            connected_member_end_trim_enabled=True,
            connected_member_end_clearance=PhysicalQuantity.of("0.25", Unit.IN),
        )
    )
    assert baseline.visualization is not None
    assert adjusted.visualization is not None
    assert adjusted.trim.interference_status.value == "TRIMMED_CLEAR"
    assert adjusted.interface_a.placement.bolts == baseline.interface_a.placement.bolts
    assert adjusted.interface_b.placement.bolts == baseline.interface_b.placement.bolts
    assert clip_module._profile_contact_is_clear(
        replace(
            request,
            connected_member_profile=replace(
                request.connected_member_profile,
                orientation=MemberProfileOrientation.ROTATION_90,
            ),
            connected_member_inclination_degrees=Decimal(25),
            connected_member_end_trim_enabled=True,
            connected_member_end_clearance=PhysicalQuantity.of("0.25", Unit.IN),
        ),
        adjusted.visualization.boxes,
    )


def test_r1_engineering_fingerprints_are_exact_for_both_roles_and_all_profiles() -> None:
    for (connected_role, profile_family), expected in _R1_ENGINEERING_FINGERPRINTS.items():
        result = preview_clip_angle(
            build_clip_angle_request(
                profile_family=profile_family,
                connected_role=connected_role,
            )
        )
        assert result.engineering_fingerprint == expected


def test_profile_dimension_edit_replaces_only_visualization_geometry_identity() -> None:
    request = build_clip_angle_request(profile_family="FLAT_PLATE")
    baseline = preview_clip_angle(request)
    dimensions = replace(
        cast(FlatPlateProfileDimensions, request.connected_member_profile.dimensions),
        width=Decimal("7"),
    )
    changed = preview_clip_angle(
        replace(
            request,
            connected_member_profile=replace(
                request.connected_member_profile,
                dimensions=dimensions,
            ),
        )
    )
    assert baseline.visualization is not None
    assert changed.visualization is not None
    baseline_profile = tuple(
        item
        for item in baseline.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    changed_profile = tuple(
        item
        for item in changed.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    assert changed_profile != baseline_profile
    assert changed.interface_a.placement == baseline.interface_a.placement
    assert changed.interface_b.placement == baseline.interface_b.placement


@pytest.mark.parametrize("profile_family", tuple(_PROFILE_ELEMENTS))
def test_profile_visualization_is_physically_equivalent_in_us_and_si(
    profile_family: str,
) -> None:
    customary = preview_clip_angle(
        _contact_clear_request(profile_family, unit_system="US_CUSTOMARY")
    )
    metric = preview_clip_angle(_contact_clear_request(profile_family, unit_system="SI"))
    assert customary.visualization is not None
    assert metric.visualization is not None
    customary_boxes = tuple(
        item
        for item in customary.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    metric_boxes = tuple(
        item
        for item in metric.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    )
    assert tuple(item.physical_element_id for item in customary_boxes) == tuple(
        item.physical_element_id for item in metric_boxes
    )
    for customary_box, metric_box in zip(customary_boxes, metric_boxes, strict=True):
        for customary_value, metric_value in zip(
            (
                *customary_box.center,
                customary_box.size_s,
                customary_box.size_p,
                customary_box.size_l,
            ),
            (*metric_box.center, metric_box.size_s, metric_box.size_p, metric_box.size_l),
            strict=True,
        ):
            assert float(customary_value.to(Unit.IN).magnitude) == pytest.approx(
                float(metric_value.to(Unit.IN).magnitude),
                abs=1e-12,
            )


def test_g10_supported_interface_failure_precedes_body_limitation() -> None:
    result = design_check_clip_angle(build_clip_angle_request())

    assert result.connector_body_status.value == "NOT_EVALUATED"
    assert result.supported_interface_failure_present is True
    assert result.assembly_status.value == "FAIL"
    assert result.ordinary_pass_allowed is False
    assert result.interface_a.resistance is not None
    assert result.interface_b.resistance is not None


def test_length_anchors_move_body_without_moving_bolt_groups() -> None:
    request = build_clip_angle_request()
    baseline = preview_clip_angle(request)
    positive = preview_clip_angle(
        replace(
            request,
            connector_length_anchor=ClipAngleLengthAnchor.POSITIVE_L_END,
            connector_length_anchor_position=PhysicalQuantity.of("7", Unit.IN),
        )
    )
    negative = preview_clip_angle(
        replace(
            request,
            connector_length_anchor=ClipAngleLengthAnchor.NEGATIVE_L_END,
            connector_length_anchor_position=PhysicalQuantity.of("-5", Unit.IN),
        )
    )

    assert positive.longitudinal_placement.positive_end_coordinate.magnitude == 7
    assert negative.longitudinal_placement.negative_end_coordinate.magnitude == -5
    assert positive.interface_a.placement.bolts == baseline.interface_a.placement.bolts
    assert negative.interface_b.placement.bolts == baseline.interface_b.placement.bolts


def test_preview_calls_zero_resistance_and_design_reuses_each_exact_demand_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = evaluate_multirow_connection_with_resolved_demand
    captured: list[object] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Preview must execute zero resistance.")

    monkeypatch.setattr(clip_module, "evaluate_multirow_connection_with_resolved_demand", forbidden)
    preview_clip_angle(build_clip_angle_request())

    def recording(*args: object, **kwargs: object) -> object:
        captured.append(args[1])
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(clip_module, "evaluate_multirow_connection_with_resolved_demand", recording)
    design = design_check_clip_angle(build_clip_angle_request())
    assert captured == [design.interface_a.demand, design.interface_b.demand]


def test_resolved_demand_seam_validates_identity_and_integrates_exact_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_clip_angle_request()
    placement = preview_clip_angle(request).interface_a.placement
    demand, force_u, force_v, _normal = clip_module._demand(request, placement, None)
    multirow_request = clip_module._multirow_request(
        request,
        placement,
        request.interface_a_layout,
        force_u,
        force_v,
    )
    assert multirow_request is not None

    with pytest.raises(ValueError, match="explicit interface"):
        evaluate_multirow_connection_with_resolved_demand(
            cast(
                Any,
                SimpleNamespace(demand_source=MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE),
            ),
            demand,
        )
    with pytest.raises(TypeError, match="EccentricDemandResult"):
        evaluate_multirow_connection_with_resolved_demand(multirow_request, cast(Any, object()))
    with pytest.raises(ValueError, match="identify one interface"):
        evaluate_multirow_connection_with_resolved_demand(
            multirow_request,
            replace(
                demand,
                interface_frame=replace(demand.interface_frame, interface_id="OTHER_INTERFACE"),
            ),
        )

    sentinel = cast(Any, SimpleNamespace(overall_disposition="NOT_EVALUATED"))
    monkeypatch.setattr(
        "frp_master_connection.application.multirow_orchestration.calculate_eccentric_group_mode_compatibility",
        lambda _value: sentinel,
    )
    monkeypatch.setattr(
        "frp_master_connection.application.multirow_orchestration._integrate_group_mode_results",
        lambda values: values[0],
    )
    response = evaluate_multirow_connection_with_resolved_demand(multirow_request, demand)
    assert response.automatic_demand_result is demand
    assert response.demand_source is MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND
    assert response.automatic_group_mode_integration is sentinel

    def different_failure(_value: object) -> None:
        raise ValueError("different group-mode error")

    monkeypatch.setattr(
        "frp_master_connection.application.multirow_orchestration.calculate_eccentric_group_mode_compatibility",
        different_failure,
    )
    with pytest.raises(ValueError, match="different group-mode error"):
        evaluate_multirow_connection_with_resolved_demand(multirow_request, demand)


def test_invalid_complete_hole_containment_is_reported_without_resistance() -> None:
    request = build_clip_angle_request()
    invalid_layout = replace(request.interface_a_layout, heel_edge_distance=Decimal("0.1"))
    result = preview_clip_angle(replace(request, interface_a_layout=invalid_layout))

    assert result.interface_a.placement.clearances.geometry_valid is False
    assert result.interface_a.placement.clearances.exact_deficit is not None
    assert result.assembly_status.value == "INVALID_GEOMETRY"
    assert result.visualization is None


def test_vector_and_request_contracts_reject_invalid_runtime_values() -> None:
    request = build_clip_angle_request()
    with pytest.raises(TypeError, match="physical quantities"):
        clip_module.ClipAngleVectorInput(
            cast(Any, Decimal(1)), request.global_force.y, request.global_force.z
        )
    with pytest.raises(ValueError, match="share one dimension"):
        clip_module.ClipAngleVectorInput(
            request.global_force.x, request.global_force.y, request.global_reference_point.z
        )

    invalid_cases: tuple[tuple[dict[str, Any], type[Exception], str], ...] = (
        ({"request_id": ""}, ValueError, "nonempty"),
        ({"orchestration_contract_version": "old"}, ValueError, "Unsupported"),
        ({"source_length_unit": Unit.MM}, ValueError, "must match"),
        ({"connected_member_profile": cast(Any, object())}, TypeError, "MemberProfile"),
        ({"connected_member_inclination_degrees": cast(Any, 10)}, TypeError, "Decimal"),
        ({"connected_member_inclination_degrees": Decimal(91)}, ValueError, "-90 through 90"),
        ({"connected_member_end_trim_enabled": cast(Any, 1)}, TypeError, "Boolean"),
        (
            {"connected_member_end_trim_enabled": True, "connected_member_end_clearance": None},
            ValueError,
            "nonnegative length",
        ),
        (
            {"connected_member_end_clearance": PhysicalQuantity.of("1", Unit.IN)},
            ValueError,
            "forbidden",
        ),
        (
            {"connector_length_anchor_position": PhysicalQuantity.of("1", Unit.MM)},
            ValueError,
            "source length unit",
        ),
        ({"bolt_diameter": PhysicalQuantity.of("1", Unit.KIP)}, ValueError, "positive length"),
        ({"hole_diameter": PhysicalQuantity.of("0.25", Unit.IN)}, ValueError, "smaller"),
        ({"global_force": request.global_reference_point}, ValueError, "force quantities"),
        ({"global_moment": request.global_force}, ValueError, "moment quantities"),
        ({"global_reference_point": request.global_force}, ValueError, "length quantities"),
    )
    for values, exception, message in invalid_cases:
        with pytest.raises(exception, match=message):
            replace(request, **values)

    wrong_owner = replace(request.connected_member_profile, role=MemberRole.OTHER)
    with pytest.raises(ValueError, match="authorized FRP"):
        replace(request, connected_member_profile=wrong_owner)
    round_profile = MemberProfile(
        "round-profile",
        "clip-angle-connected-member",
        MemberRole.BRACE,
        MemberProfileFamily.ROUND_HOLLOW_SECTION,
        RoundHollowProfileDimensions(Decimal(8), Decimal(4), Decimal("0.25")),
        ComponentMaterialKind.PULTRUDED_FRP,
        request.connected_member_profile.material_orientation,
        MemberProfileOrientation.ROTATION_0,
        None,
        MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )
    with pytest.raises(ValueError, match="Round profiles"):
        replace(request, connected_member_profile=round_profile)


def test_nonprescriptive_row_count_and_not_calculated_warning_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_clip_angle_request()
    four_rows = replace(
        request.interface_a_layout,
        row_count=4,
        pitch=Decimal("0.5"),
        negative_end_distance=Decimal("2.25"),
    )
    result = preview_clip_angle(replace(request, interface_a_layout=four_rows))
    assert result.interface_a.demand.method_applicability.value == (
        "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE"
    )

    calculated = result.interface_a.demand
    unsupported = replace(
        calculated,
        availability=DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED,
    )
    monkeypatch.setattr(
        clip_module, "calculate_eccentric_bolt_group_demand", lambda _value: unsupported
    )
    warned = preview_clip_angle(request)
    assert any("DEMAND_CALCULATION_NOT_SUPPORTED" in item for item in warned.warnings)

    failed_integration = SimpleNamespace(overall_disposition=MultiRowOverallDisposition.FAIL)
    resistance = SimpleNamespace(
        automatic_group_mode_integration=failed_integration,
        calculation_result=None,
    )
    interface = replace(result.interface_a, resistance=cast(Any, resistance))
    assert clip_module._supported_failure(interface) is True


@pytest.mark.parametrize("inclination", ["0", "5", "25", "-25", "45"])
def test_r3_valid_inclination_matrix_stays_current_with_body_limitation(
    inclination: str,
) -> None:
    angle = Decimal(inclination)
    request = build_clip_angle_request(profile_family="ANGLE")
    result = preview_clip_angle(
        replace(
            request,
            connected_member_inclination_degrees=angle,
            connected_member_end_trim_enabled=angle != 0,
            connected_member_end_clearance=(
                None if angle == 0 else PhysicalQuantity.of("0.25", Unit.IN)
            ),
        )
    )

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert result.geometry_invalid_reasons == ()
    assert result.visualization is not None
    assert result.connector_body_status is clip_module.ClipAngleBodyResistanceStatus.NOT_EVALUATED
    assert result.assembly_status is clip_module.ClipAngleAssemblyStatus.NOT_EVALUATED
    assert result.ordinary_pass_allowed is False


@pytest.mark.parametrize("connected_role", ["BRACE", "BEAM"])
@pytest.mark.parametrize("profile_family", tuple(_PROFILE_ELEMENTS))
def test_r3_valid_profile_and_role_matrix_separates_geometry_from_body_status(
    connected_role: str,
    profile_family: str,
) -> None:
    result = preview_clip_angle(
        _contact_clear_request(profile_family, connected_role=connected_role)
    )

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert result.geometry_invalid_reasons == ()
    assert result.visualization is not None
    assert result.connector_body_status is clip_module.ClipAngleBodyResistanceStatus.NOT_EVALUATED
    assert "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED" in result.warnings


def test_r3_true_invalid_geometry_has_only_physical_invalid_reasons() -> None:
    request = build_clip_angle_request()
    invalid = preview_clip_angle(
        replace(
            request,
            interface_a_layout=replace(
                request.interface_a_layout,
                heel_edge_distance=Decimal("0.1"),
            ),
        )
    )

    assert invalid.geometry_status is clip_module.ClipAngleGeometryStatus.INVALID_GEOMETRY
    assert invalid.geometry_invalid_reasons == ("INTERFACE_A_COMPLETE_HOLE_CONTAINMENT_INVALID",)
    assert "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED" not in (
        invalid.geometry_invalid_reasons
    )
    assert invalid.visualization is None
    assert invalid.design_check_ready is False


def test_r3_normal_action_is_current_but_not_design_ready() -> None:
    result = preview_clip_angle(build_clip_angle_request(force=("0", "1", "0")))

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert result.geometry_invalid_reasons == ()
    assert result.visualization is not None
    assert result.interface_b.normal_component == PhysicalQuantity.of("1", Unit.KIP)
    assert result.interface_b.normal_action_supported is False
    assert result.interface_b.automatic_axis_tension_generated is False
    assert result.interface_b.prying_generated is False
    assert result.design_check_ready is False


def test_r3_qualification_required_method_is_current_but_not_design_ready() -> None:
    request = build_clip_angle_request()
    four_rows = replace(
        request.interface_a_layout,
        row_count=4,
        pitch=Decimal("0.5"),
        negative_end_distance=Decimal("2.25"),
    )
    result = preview_clip_angle(replace(request, interface_a_layout=four_rows))

    assert result.geometry_status is clip_module.ClipAngleGeometryStatus.VALID
    assert result.geometry_invalid_reasons == ()
    assert result.visualization is not None
    assert result.interface_a.demand.method_applicability.value == (
        "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE"
    )
    assert result.interface_a.demand.qualification.value == ("SECTION_2_3_2_QUALIFICATION_REQUIRED")
    assert result.design_check_ready is False


@pytest.mark.parametrize("case", ["INVALID_GEOMETRY", "NORMAL_ACTION", "METHOD"])
def test_r3_design_does_not_execute_resistance_when_prerequisites_are_blocked(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_clip_angle_request()
    if case == "INVALID_GEOMETRY":
        request = replace(
            request,
            interface_a_layout=replace(
                request.interface_a_layout,
                heel_edge_distance=Decimal("0.1"),
            ),
        )
    elif case == "NORMAL_ACTION":
        request = build_clip_angle_request(force=("0", "1", "0"))
    else:
        request = replace(
            request,
            interface_a_layout=replace(
                request.interface_a_layout,
                row_count=4,
                pitch=Decimal("0.5"),
                negative_end_distance=Decimal("2.25"),
            ),
        )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Blocked design prerequisites must execute zero resistance.")

    monkeypatch.setattr(
        clip_module,
        "evaluate_multirow_connection_with_resolved_demand",
        forbidden,
    )
    result = design_check_clip_angle(request)

    assert result.preview.resistance_evaluated is False
    assert result.interface_a.resistance is None
    assert result.interface_b.resistance is None
    assert result.ordinary_pass_allowed is False
    assert result.assembly_status.value == (
        "INVALID_GEOMETRY" if case == "INVALID_GEOMETRY" else "NOT_EVALUATED"
    )


def test_r3_design_without_supported_failure_remains_not_evaluated() -> None:
    result = design_check_clip_angle(
        build_clip_angle_request(force=("0", "0", "0"), reference=("0", "0", "0"))
    )

    assert result.supported_interface_failure_present is False
    assert result.connector_body_status is clip_module.ClipAngleBodyResistanceStatus.NOT_EVALUATED
    assert result.assembly_status is clip_module.ClipAngleAssemblyStatus.NOT_EVALUATED
    assert result.ordinary_pass_allowed is False


def test_clip_angle_dimension_and_layout_contracts_fail_closed() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        ClipAngleDimensions(cast(Any, 4), Decimal(4), Decimal("0.5"), Decimal(8))
    with pytest.raises(ValueError, match="greater than zero"):
        ClipAngleDimensions(Decimal(0), Decimal(4), Decimal("0.5"), Decimal(8))
    with pytest.raises(ValueError, match="less than both"):
        ClipAngleDimensions(Decimal(4), Decimal(4), Decimal(4), Decimal(8))
    with pytest.raises(ValueError, match="positive clear web"):
        ClipAngleSupportDimensions(
            Decimal(16), Decimal(1), Decimal(8), Decimal("0.5"), Decimal("0.5")
        )
    with pytest.raises(ValueError, match="wider than its web"):
        ClipAngleSupportDimensions(
            Decimal(16), Decimal(8), Decimal("0.5"), Decimal("0.5"), Decimal("0.5")
        )

    base = ClipAngleBoltLayout(
        2,
        2,
        Decimal(2),
        Decimal(2),
        Decimal("0.75"),
        Decimal("0.75"),
        Decimal(3),
        Decimal(3),
    )
    with pytest.raises(ValueError, match="non-Boolean integer"):
        replace(base, row_count=cast(Any, True))
    with pytest.raises(TypeError, match="placement_mode"):
        replace(base, placement_mode=cast(Any, "CENTER"))
    with pytest.raises(ValueError, match="forbids group offsets"):
        replace(base, length_offset=Decimal(0))
    with pytest.raises(ValueError, match="requires length and width"):
        replace(
            base,
            placement_mode=ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            length_offset=Decimal(0),
        )
    with pytest.raises(TypeError, match="must be a Decimal"):
        replace(
            base,
            placement_mode=ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            length_offset=cast(Any, 0),
            width_offset=Decimal(0),
        )
    with pytest.raises(ValueError, match="must be finite"):
        replace(
            base,
            placement_mode=ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            length_offset=Decimal("NaN"),
            width_offset=Decimal(0),
        )


@pytest.mark.parametrize(
    ("stage", "failure", "exception", "message"),
    [
        ("initial", "missing", ValueError, "did not resolve uniquely"),
        ("initial", "nonplanar", TypeError, "requires one planar"),
        ("initial", "misaligned", ValueError, "not contact-parallel"),
        ("reoriented", "missing", ValueError, "Reoriented.*did not resolve uniquely"),
        ("reoriented", "nonplanar", TypeError, "Reoriented.*remain planar"),
        ("reoriented", "wrong-facing", ValueError, "cannot face"),
        ("final", "missing", ValueError, "Placed.*did not resolve uniquely"),
        ("final", "nonplanar", TypeError, "Placed.*remain planar"),
        ("final", "wrong-facing", ValueError, "does not face"),
    ],
)
def test_connected_profile_placement_rejects_broken_shared_geometry_invariants(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    failure: str,
    exception: type[Exception],
    message: str,
) -> None:
    request = build_clip_angle_request()
    selected_id = require_direct_tee_profile_surface(
        request.connected_member_profile
    ).outside_patch_id
    original = create_component_surface_set
    call_count = 0
    contact_sign = float(request.hand.sign)

    def with_normal(
        geometry: PlanarRectangularSurface3D,
        normal_kind: str,
    ) -> PlanarRectangularSurface3D:
        if normal_kind == "toward-contact":
            normal = UnitVector3D(contact_sign, 0.0, 0.0)
            transverse = UnitVector3D(0.0, 1.0, 0.0)
            third = UnitVector3D(0.0, 0.0, contact_sign)
        elif normal_kind == "away-from-contact":
            normal = UnitVector3D(-contact_sign, 0.0, 0.0)
            transverse = UnitVector3D(0.0, 1.0, 0.0)
            third = UnitVector3D(0.0, 0.0, -contact_sign)
        else:
            normal = UnitVector3D(0.0, 1.0, 0.0)
            transverse = UnitVector3D(0.0, 0.0, 1.0)
            third = UnitVector3D(1.0, 0.0, 0.0)
        return replace(
            geometry,
            frame=CartesianFrame3D(geometry.center, normal, transverse, third),
        )

    def broken_surface_set(placed: PlacedComponentGeometry3D) -> SimpleNamespace:
        nonlocal call_count
        call_count += 1
        surface_set = original(placed)
        patch = next(item for item in surface_set.patches if item.id == selected_id)
        geometry = cast(PlanarRectangularSurface3D, patch.geometry)
        target_call = 1 if stage == "initial" else 2
        if call_count == 1 and stage == "reoriented":
            geometry = with_normal(geometry, "away-from-contact")
        elif call_count == 1 and stage == "final":
            geometry = with_normal(geometry, "toward-contact")
        if call_count == target_call:
            if failure == "missing":
                return SimpleNamespace(patches=())
            if failure == "nonplanar":
                return SimpleNamespace(
                    patches=(SimpleNamespace(id=selected_id, geometry=object()),)
                )
            if failure == "misaligned":
                geometry = with_normal(geometry, "misaligned")
            elif failure == "wrong-facing":
                geometry = with_normal(geometry, "away-from-contact")
        return SimpleNamespace(patches=(SimpleNamespace(id=selected_id, geometry=geometry),))

    monkeypatch.setattr(clip_module, "create_component_surface_set", broken_surface_set)
    with pytest.raises(exception, match=message):
        clip_module._placed_connected_profile(request)


def test_connected_profile_visualization_rejects_incomplete_shared_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_clip_angle_request()
    placed = clip_module._placed_connected_profile(request)
    components, primitives, directions = build_placed_component_visualization_snapshots((placed,))
    box = next(item for item in primitives if item.kind is VisualizationPrimitiveKind.BOX)
    monkeypatch.setattr(clip_module, "_placed_connected_profile", lambda _request: placed)

    with monkeypatch.context() as context:
        context.setattr(
            clip_module,
            "build_placed_component_visualization_snapshots",
            lambda _placed: (components, (replace(box, parameters=()),), directions),
        )
        with pytest.raises(ValueError, match="lacks exact x_end"):
            clip_module._profile_visualization(request)

    with monkeypatch.context() as context:
        context.setattr(
            clip_module,
            "build_placed_component_visualization_snapshots",
            lambda _placed: (components, (replace(box, center=None),), directions),
        )
        with pytest.raises(ValueError, match="lacks exact physical ownership"):
            clip_module._profile_visualization(request)

    with monkeypatch.context() as context:
        context.setattr(
            clip_module,
            "build_placed_component_visualization_snapshots",
            lambda _placed: (
                components,
                (box,),
                (replace(directions[0], through_thickness=None),),
            ),
        )
        with pytest.raises(ValueError, match="require exact material axes"):
            clip_module._profile_visualization(request)
