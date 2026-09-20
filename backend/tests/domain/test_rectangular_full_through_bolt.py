"""Stage 3.3C1 shared rectangular-section/full-through-bolt contract tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.application.member_profile_geometry import (
    create_member_profile_cross_section,
    create_oriented_standard_topology,
)
from frp_master_connection.domain import (
    RECTANGULAR_LOCAL_MECHANICS_LIMITATIONS,
    SHARED_SUPPORT_TARGET_REGISTRY,
    SOLID_RECTANGULAR_MATERIAL_BASIS,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ExactProfileVector3D,
    FaceHoleContainment,
    FiniteBoundaryValidatorId,
    FlatPlateProfileDimensions,
    FRPComponentOrientation,
    FullThroughBoltPath,
    FullThroughHardwareLocation,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    OppositeSurfaceBehavior,
    PhysicalBoltPathSegment,
    PhysicalBoltPathSegmentKind,
    PrincipalAxisFamily,
    RectangularBoltAxis,
    RectangularContainmentStatus,
    RectangularFaceLocalFrame,
    RectangularHollowProfileDimensions,
    RectangularLocalMechanicsLimitation,
    RectangularMaterialBasis,
    SharedSupportTargetId,
    SolidRectangularProfileDimensions,
    SupportAccessQualification,
    SupportBoltPathClass,
    SupportPhysicalRegion,
    SupportSurfaceClass,
    aggregate_full_through_containment,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    canonical_full_through_bolt_json,
    compose_external_connector_layers,
    evaluate_face_hole_containment,
    evaluate_full_through_containment,
    external_connector_layer,
    full_through_bolt_fingerprint,
    full_through_bolt_hardware,
    profile_section_geometry_adapter,
    profile_surface_registry,
    rectangular_opposing_face_pair,
    shared_support_target,
    shared_support_target_registry,
    solid_rectangular_material_basis,
)

D = Decimal
ONE = D("1")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "backend"
    / "tests"
    / "golden"
    / "stage_3_3c1_shared_rectangular_section_full_through_bolt_golden_benchmarks_rc1.json"
)
SPECIFICATION_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "engineering"
    / "STAGE_3_3C1_SHARED_RECTANGULAR_SECTION_FULL_THROUGH_BOLT_ENGINEERING_SPECIFICATION_RC1.md"
)
LEDGER_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "qa"
    / "STAGE_3_3C1_SHARED_RECTANGULAR_SECTION_FULL_THROUGH_BOLT_AUTHORITY_LEDGER_RC1.md"
)


def _golden() -> dict[str, Any]:
    value = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _benchmark(benchmark_id: str) -> dict[str, Any]:
    values = _golden()["benchmarks"]
    assert isinstance(values, list)
    return next(item for item in values if item["id"] == benchmark_id)


def _canonical(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _profile(
    family: MemberProfileFamily,
    *,
    selected: MemberProfileSurfaceId = MemberProfileSurfaceId.Y_POS_FACE,
    scale: Decimal = ONE,
) -> MemberProfile:
    dimensions = (
        RectangularHollowProfileDimensions(
            D("8") * scale,
            D("6") * scale,
            D("4") * scale,
            D("0.5") * scale,
        )
        if family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
        else SolidRectangularProfileDimensions(
            D("8") * scale,
            D("6") * scale,
            D("4") * scale,
        )
    )
    return MemberProfile(
        f"{family.value.lower()}-profile",
        f"{family.value.lower()}-member",
        MemberRole.COLUMN,
        family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(
                CoordinateFrameKind.MEMBER_LOCAL,
                f"{family.value.lower()}-member",
            ),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        selected,
    )


def _rhs(*, scale: Decimal = ONE) -> MemberProfile:
    return _profile(MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION, scale=scale)


def _srs(*, scale: Decimal = ONE) -> MemberProfile:
    return _profile(MemberProfileFamily.SOLID_RECTANGULAR_SECTION, scale=scale)


def _flat_plate() -> MemberProfile:
    return MemberProfile(
        "flat-profile",
        "flat-member",
        MemberRole.BRACE,
        MemberProfileFamily.FLAT_PLATE,
        FlatPlateProfileDimensions(D("8"), D("4"), D("0.5")),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "flat-member"),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.FACE_POS,
    )


def _basis() -> RectangularMaterialBasis:
    return SOLID_RECTANGULAR_MATERIAL_BASIS


def _rhs_core(*, scale: Decimal = ONE) -> FullThroughBoltPath:
    return build_rhs_full_through_core(
        _rhs(scale=scale),
        MemberProfileSurfaceId.Z_POS_FACE,
        bolt_id="bolt-1",
        local_uv=(D("1.25") * scale, D("0")),
        material_region_id="rhs-walls",
    )


def _srs_core(*, scale: Decimal = ONE) -> FullThroughBoltPath:
    return build_srs_full_through_core(
        _srs(scale=scale),
        MemberProfileSurfaceId.Z_POS_FACE,
        bolt_id="bolt-1",
        local_uv=(D("1.25") * scale, D("0")),
        material_region_id="srs-volume",
    )


def test_c1_controlled_artifacts_are_byte_exact_complete_and_golden_driven() -> None:
    expected_hashes = {
        SPECIFICATION_PATH: "0A73AC9910E506E9E721A98EBEE39A072C096364513C62C63B736E4642591957",
        GOLDEN_PATH: "649070D1B4082D8FFC839262C586DC3B1FEAA6BAD12254F15186F85B39EA24D5",
        LEDGER_PATH: "21009D185C999CBDD08EBC70C2A9CE38C2AF4A221C60C4799D3E91230797946C",
    }
    for path, expected_hash in expected_hashes.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == expected_hash
    assert (
        SPECIFICATION_PATH.read_text(encoding="utf-8")
        .rstrip()
        .endswith("**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**")
    )
    assert (
        LEDGER_PATH.read_text(encoding="utf-8").rstrip().endswith("**END OF AUTHORITY LEDGER RC1**")
    )

    golden = _golden()
    assert golden["artifact"] == (
        "FRP_MASTER_CONNECTION_STAGE_3_3C1_SHARED_RECTANGULAR_SECTION_"
        "FULL_THROUGH_BOLT_GOLDEN_BENCHMARKS_RC1"
    )
    assert [item["id"] for item in golden["benchmarks"]] == [
        "C1_G1_RHS_CORE_FULL_THROUGH_PATH",
        "C1_G2_SRS_CORE_FULL_THROUGH_PATH",
        "C1_G3_RHS_ONE_SIDED_EXTERNAL_CONNECTOR_STACK",
        "C1_G4_RHS_PAIRED_EXTERNAL_CONNECTOR_STACK",
        "C1_G5_SRS_PAIRED_EXTERNAL_CONNECTOR_STACK",
        "C1_G6_RHS_OPPOSING_WALL_HOLE_ALIGNMENT",
        "C1_G7_RHS_BOTH_WALL_CONTAINMENT_REQUIRED",
        "C1_G8_SUPPORT_TARGET_REGISTRY",
        "C1_G9_NO_INTERNAL_RHS_HARDWARE",
        "C1_G10_CAVITY_IS_NOT_MATERIAL",
        "C1_G11_EXACT_US_SI_EQUIVALENCE",
        "C1_G12_UNSUPPORTED_LOCAL_RESISTANCE_REMAINS_FAIL_CLOSED",
    ]


def test_c1_golden_g1_to_g12_match_production_derived_architecture() -> None:
    rhs = _rhs_core()
    srs = _srs_core()
    near = external_connector_layer(
        "POSITIVE_CONNECTOR",
        D("0.5"),
        material_region_id="positive-connector",
        material_basis=_basis(),
    )
    far = external_connector_layer(
        "NEGATIVE_CONNECTOR",
        D("0.5"),
        material_region_id="negative-connector",
        material_basis=_basis(),
    )

    g1 = _benchmark("C1_G1_RHS_CORE_FULL_THROUGH_PATH")
    assert [
        {"kind": item.kind.value, "identity": item.identity, "length_in": _canonical(item.length)}
        for item in rhs.segments
    ] == g1["expected_segments"]
    assert _canonical(rhs.shank_length) == g1["expected"]["total_section_traversal_in"]
    assert rhs.physical_bolt_count == g1["expected"]["physical_bolt_count"]
    assert (
        full_through_bolt_hardware(rhs).internal_hardware_count
        == g1["expected"]["internal_hardware_count"]
    )

    g2 = _benchmark("C1_G2_SRS_CORE_FULL_THROUGH_PATH")
    assert [
        {"kind": item.kind.value, "identity": item.identity, "length_in": _canonical(item.length)}
        for item in srs.segments
    ] == g2["expected_segments"]
    assert _canonical(srs.shank_length) == g2["expected"]["total_section_traversal_in"]
    assert (
        _canonical(sum((item.length for item in srs.free_shank_spans), start=D("0")))
        == g2["expected"]["cavity_span_in"]
    )

    one_sided = compose_external_connector_layers(rhs, near_layers=(near,))
    rhs_paired = compose_external_connector_layers(rhs, near_layers=(near,), far_layers=(far,))
    srs_paired = compose_external_connector_layers(srs, near_layers=(near,), far_layers=(far,))
    assert (
        _canonical(one_sided.shank_length)
        == _benchmark("C1_G3_RHS_ONE_SIDED_EXTERNAL_CONNECTOR_STACK")["expected"][
            "stack_span_before_hardware_in"
        ]
    )
    assert (
        _canonical(rhs_paired.shank_length)
        == _benchmark("C1_G4_RHS_PAIRED_EXTERNAL_CONNECTOR_STACK")["expected"][
            "stack_span_before_hardware_in"
        ]
    )
    assert (
        _canonical(srs_paired.shank_length)
        == _benchmark("C1_G5_SRS_PAIRED_EXTERNAL_CONNECTOR_STACK")["expected"][
            "stack_span_before_hardware_in"
        ]
    )

    g6 = _benchmark("C1_G6_RHS_OPPOSING_WALL_HOLE_ALIGNMENT")
    aligned = RectangularBoltAxis(
        MemberProfileSurfaceId(g6["selected_face"]),
        MemberProfileSurfaceId(g6["opposite_face"]),
        *(D(item) for item in g6["near_hole_local_uv_in"]),
    )
    assert [str(item) for item in aligned.near_local_uv] == g6["near_hole_local_uv_in"]
    assert [str(item) for item in aligned.far_local_uv] == g6["far_hole_local_uv_in"]

    g7 = _benchmark("C1_G7_RHS_BOTH_WALL_CONTAINMENT_REQUIRED")["expected"]
    valid_near = FaceHoleContainment(
        MemberProfileSurfaceId.Y_POS_FACE, "bolt-1", True, D("1"), D("0")
    )
    valid_far = FaceHoleContainment(
        MemberProfileSurfaceId.Y_NEG_FACE, "bolt-1", True, D("1"), D("0")
    )
    invalid_near = FaceHoleContainment(
        MemberProfileSurfaceId.Y_POS_FACE, "bolt-1", False, D("-1"), D("1")
    )
    invalid_far = FaceHoleContainment(
        MemberProfileSurfaceId.Y_NEG_FACE, "bolt-1", False, D("-1"), D("1")
    )
    assert (
        aggregate_full_through_containment(valid_near, invalid_far).status.value
        == g7["near_wall_valid_far_wall_invalid_overall"]
    )
    assert (
        aggregate_full_through_containment(invalid_near, valid_far).status.value
        == g7["near_wall_invalid_far_wall_valid_overall"]
    )
    assert (
        aggregate_full_through_containment(valid_near, valid_far).status.value
        == g7["both_valid_overall"]
    )

    g8 = _benchmark("C1_G8_SUPPORT_TARGET_REGISTRY")
    assert [item.target_id.value for item in shared_support_target_registry()] == g8[
        "required_targets"
    ]
    assert len(shared_support_target_registry()) == g8["expected"]["count"]
    assert (
        "W_BEAM_WEB" in {item.target_id.value for item in shared_support_target_registry()}
    ) is g8["expected"]["w_beam_web_present"]

    g9 = _benchmark("C1_G9_NO_INTERNAL_RHS_HARDWARE")["expected"]
    hardware = full_through_bolt_hardware(rhs)
    assert hardware.head_location.value == g9["head_location"]
    assert hardware.nut_location.value == g9["nut_location"]
    assert [item.value for item in hardware.washer_locations] == g9["washer_locations"]
    assert g9["cavity_allowed_contents"] == ["BOLT_SHANK"]

    cavity = rhs.free_shank_spans[0]
    g10 = _benchmark("C1_G10_CAVITY_IS_NOT_MATERIAL")["expected"]
    assert (cavity.material_region_id is not None) is g10["cavity_receives_material_id"]
    assert (cavity.material_basis is not None) is g10["cavity_receives_material_axes"]
    assert cavity.receives_bearing_demand is g10["cavity_receives_bearing_demand"]
    assert cavity.receives_resistance_check is g10["cavity_receives_resistance_check"]

    g11 = _benchmark("C1_G11_EXACT_US_SI_EQUIVALENCE")["conversions"]

    assert g11 == {
        "6_in_mm": _canonical(D("6") * D("25.4")),
        "5_in_mm": _canonical(D("5") * D("25.4")),
        "4_in_mm": _canonical(D("4") * D("25.4")),
        "0.5_in_mm": _canonical(D("0.5") * D("25.4")),
        "8_in_mm": _canonical(D("8") * D("25.4")),
    }
    g12 = _benchmark("C1_G12_UNSUPPORTED_LOCAL_RESISTANCE_REMAINS_FAIL_CLOSED")
    assert [item.value for item in RECTANGULAR_LOCAL_MECHANICS_LIMITATIONS] == g12[
        "expected_required_checks"
    ]
    assert g12["expected"] == {
        "new_resistance_equation_used": False,
        "ordinary_pass_created_by_c1": False,
    }


def test_c1_srs_is_a_real_solid_profile_with_exact_geometry_and_not_rhs() -> None:
    srs = _srs()
    rhs = _rhs()

    assert isinstance(srs.dimensions, SolidRectangularProfileDimensions)
    assert not isinstance(srs.dimensions, RectangularHollowProfileDimensions)
    assert srs.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION
    adapter = profile_section_geometry_adapter(srs)
    assert adapter.geometry_factory_name == "create_plate_geometry"
    assert adapter.dimension_values == (("width", D("4")), ("thickness", D("6")))

    srs_geometry = create_member_profile_cross_section(
        srs,
        create_oriented_standard_topology(srs.section_family),
    )
    rhs_geometry = create_member_profile_cross_section(
        rhs,
        create_oriented_standard_topology(rhs.section_family),
    )
    assert (srs_geometry.outside_bounds.min_y, srs_geometry.outside_bounds.max_y) == (-2, 2)
    assert (srs_geometry.outside_bounds.min_z, srs_geometry.outside_bounds.max_z) == (-3, 3)
    assert len(srs_geometry.physical_elements) == 1
    assert srs_geometry.nominal_voids == ()
    assert len(rhs_geometry.physical_elements) == 4
    assert len(rhs_geometry.nominal_voids) == 1


@pytest.mark.parametrize(
    ("selected", "opposite", "separation"),
    [
        (MemberProfileSurfaceId.Y_POS_FACE, MemberProfileSurfaceId.Y_NEG_FACE, D("4")),
        (MemberProfileSurfaceId.Y_NEG_FACE, MemberProfileSurfaceId.Y_POS_FACE, D("4")),
        (MemberProfileSurfaceId.Z_POS_FACE, MemberProfileSurfaceId.Z_NEG_FACE, D("6")),
        (MemberProfileSurfaceId.Z_NEG_FACE, MemberProfileSurfaceId.Z_POS_FACE, D("6")),
    ],
)
@pytest.mark.parametrize(
    "family",
    [
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    ],
)
def test_c1_rhs_and_srs_have_exact_four_face_opposing_registry(
    family: MemberProfileFamily,
    selected: MemberProfileSurfaceId,
    opposite: MemberProfileSurfaceId,
    separation: Decimal,
) -> None:
    profile = _profile(family, selected=selected)
    pair = rectangular_opposing_face_pair(profile, selected)

    assert tuple(item.surface_id for item in profile_surface_registry(profile)) == (
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    )
    assert pair.selected_surface.surface_id is selected
    assert pair.opposite_surface.surface_id is opposite
    assert pair.separation == separation
    assert pair.selected_frame.origin == pair.selected_surface.center
    assert pair.opposite_frame.origin == pair.opposite_surface.center
    assert pair.selected_frame.normal == pair.selected_surface.local_outward_normal
    assert pair.selected_frame.u_axis == pair.opposite_frame.u_axis
    assert pair.selected_frame.v_axis == pair.opposite_frame.v_axis


def test_c1_srs_has_controlled_stable_volume_material_basis() -> None:
    assert solid_rectangular_material_basis(_srs()) == RectangularMaterialBasis(
        ExactProfileVector3D(D("1"), D("0"), D("0")),
        ExactProfileVector3D(D("0"), D("1"), D("0")),
        ExactProfileVector3D(D("0"), D("0"), D("1")),
    )
    with pytest.raises(ValueError, match="requires an SRS"):
        solid_rectangular_material_basis(_rhs())
    with pytest.raises(TypeError, match="MemberProfile"):
        solid_rectangular_material_basis(object())  # type: ignore[arg-type]


def test_c1_support_target_registry_is_exactly_the_seven_controlled_targets() -> None:
    expected = tuple(SharedSupportTargetId)
    actual = shared_support_target_registry()

    assert actual is SHARED_SUPPORT_TARGET_REGISTRY
    assert tuple(item.target_id for item in actual) == expected
    assert len(actual) == 7
    assert "W_BEAM_WEB" not in {item.target_id.value for item in actual}
    assert shared_support_target(SharedSupportTargetId.W_COLUMN_WEB).bolt_path_class is (
        SupportBoltPathClass.W_WEB_LAYER
    )
    assert (
        shared_support_target(SharedSupportTargetId.CHANNEL_COLUMN_WEB).finite_boundary_validator_id
        is FiniteBoundaryValidatorId.CHANNEL_CLEAR_WEB_BOUNDS
    )
    assert (
        shared_support_target(SharedSupportTargetId.ANGLE_COLUMN_LEG).finite_boundary_validator_id
        is FiniteBoundaryValidatorId.ANGLE_EXPOSED_LEG_R7
    )
    rhs_target = shared_support_target(SharedSupportTargetId.RECTANGULAR_HOLLOW_COLUMN_WALL)
    srs_target = shared_support_target(SharedSupportTargetId.SOLID_RECTANGULAR_COLUMN_FACE)
    assert rhs_target.opposite_surface_behavior is OppositeSurfaceBehavior.RECTANGULAR_FULL_THROUGH
    assert rhs_target.bolt_path_class is SupportBoltPathClass.RHS_FULL_THROUGH
    assert srs_target.bolt_path_class is SupportBoltPathClass.SRS_FULL_THROUGH
    assert rhs_target.access_qualification is SupportAccessQualification.EXTERNAL_BOTH_ENDS_REQUIRED
    assert srs_target.physical_region is SupportPhysicalRegion.SOLID_RECTANGULAR_VOLUME
    assert srs_target.surface_class is SupportSurfaceClass.SOLID_RECTANGULAR_EXTERIOR_FACE


def test_c1_g1_rhs_core_is_exact_near_wall_cavity_far_wall() -> None:
    path = _rhs_core()

    assert tuple((item.kind.value, item.identity, item.length) for item in path.segments) == (
        ("MATERIAL_LAYER", "NEAR_WALL", D("0.5")),
        ("FREE_SHANK_SPAN", "CAVITY", D("5")),
        ("MATERIAL_LAYER", "FAR_WALL", D("0.5")),
    )
    assert path.shank_length == D("6")
    assert path.physical_bolt_count == path.continuous_shank_count == 1
    assert len(path.material_layers) == 2
    assert len(path.free_shank_spans) == 1
    cavity = path.free_shank_spans[0]
    assert cavity.material_region_id is None
    assert cavity.material_basis is None
    assert cavity.receives_bearing_demand is False
    assert cavity.receives_resistance_check is False
    assert all(item.receives_bearing_demand for item in path.material_layers)


def test_c1_g2_srs_core_is_one_continuous_material_volume() -> None:
    path = _srs_core()

    assert len(path.segments) == len(path.material_layers) == 1
    assert path.free_shank_spans == ()
    assert path.segments[0].identity == "SOLID_RECTANGULAR_SECTION"
    assert path.segments[0].length == path.shank_length == D("6")
    assert path.segments[0].material_basis is SOLID_RECTANGULAR_MATERIAL_BASIS


def test_c1_g3_to_g5_external_connector_composition_preserves_one_bolt() -> None:
    near = external_connector_layer(
        "POSITIVE_CONNECTOR",
        D("0.5"),
        material_region_id="positive-connector",
        material_basis=_basis(),
    )
    far = external_connector_layer(
        "NEGATIVE_CONNECTOR",
        D("0.5"),
        material_region_id="negative-connector",
        material_basis=_basis(),
    )

    rhs_one_sided = compose_external_connector_layers(_rhs_core(), near_layers=(near,))
    rhs_paired = compose_external_connector_layers(
        _rhs_core(), near_layers=(near,), far_layers=(far,)
    )
    srs_paired = compose_external_connector_layers(
        _srs_core(), near_layers=(near,), far_layers=(far,)
    )
    assert rhs_one_sided.shank_length == D("6.5")
    assert rhs_paired.shank_length == srs_paired.shank_length == D("7")
    assert rhs_paired.bolt_id == srs_paired.bolt_id == "bolt-1"
    assert rhs_paired.physical_bolt_count == rhs_paired.continuous_shank_count == 1
    assert tuple(item.identity for item in rhs_paired.segments) == (
        "POSITIVE_CONNECTOR",
        "NEAR_WALL",
        "CAVITY",
        "FAR_WALL",
        "NEGATIVE_CONNECTOR",
    )


def test_c1_g6_one_axis_owns_exact_equal_near_and_far_projected_coordinates() -> None:
    axis = RectangularBoltAxis(
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        D("1.25"),
        D("2.5"),
    )

    assert axis.near_local_uv == axis.far_local_uv == (D("1.25"), D("2.5"))
    with pytest.raises(ValueError, match="exact registered opposing pair"):
        RectangularBoltAxis(
            MemberProfileSurfaceId.Y_POS_FACE,
            MemberProfileSurfaceId.Z_NEG_FACE,
            D("1.25"),
            D("2.5"),
        )


def test_c1_g7_both_faces_are_independently_required_and_governing_is_exact() -> None:
    pair = rectangular_opposing_face_pair(_rhs(), MemberProfileSurfaceId.Z_POS_FACE)
    near_valid = evaluate_face_hole_containment(
        pair.selected_surface,
        bolt_id="bolt-1",
        local_uv=(D("1.25"), D("0")),
        hole_radius=D("0.25"),
    )
    far_valid = evaluate_face_hole_containment(
        pair.opposite_surface,
        bolt_id="bolt-1",
        local_uv=(D("1.25"), D("0")),
        hole_radius=D("0.25"),
    )
    far_invalid = evaluate_face_hole_containment(
        pair.opposite_surface,
        bolt_id="bolt-1",
        local_uv=(D("1.25"), D("1.4")),
        hole_radius=D("0.25"),
    )
    near_invalid = evaluate_face_hole_containment(
        pair.selected_surface,
        bolt_id="bolt-1",
        local_uv=(D("1.25"), D("-1.4")),
        hole_radius=D("0.25"),
    )

    valid = aggregate_full_through_containment(near_valid, far_valid)
    far_governs = aggregate_full_through_containment(near_valid, far_invalid)
    near_governs = aggregate_full_through_containment(near_invalid, far_valid)
    assert valid.status is RectangularContainmentStatus.VALID
    assert valid.exact_deficit == D("0")
    assert far_governs.status is RectangularContainmentStatus.INVALID_GEOMETRY
    assert far_governs.governing_face is MemberProfileSurfaceId.Z_NEG_FACE
    assert far_governs.governing_bolt == "bolt-1"
    assert far_governs.exact_deficit == D("0.15")
    assert near_governs.status is RectangularContainmentStatus.INVALID_GEOMETRY
    assert near_governs.governing_face is MemberProfileSurfaceId.Z_POS_FACE
    with pytest.raises(ValueError, match="one physical bolt"):
        aggregate_full_through_containment(
            near_valid,
            replace(far_valid, bolt_id="different-bolt"),
        )
    actual = evaluate_full_through_containment(
        _rhs(), _rhs_core().axis, bolt_id="bolt-1", hole_radius=D("0.25")
    )
    assert actual.status is RectangularContainmentStatus.VALID


def test_c1_g9_hardware_is_external_and_rhs_cavity_contains_shank_only() -> None:
    hardware = full_through_bolt_hardware(_rhs_core())

    assert hardware.shank_length == D("6")
    assert hardware.head_location is FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE
    assert hardware.nut_location is FullThroughHardwareLocation.EXTERIOR_FAR_SIDE
    assert hardware.washer_locations == (
        FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,
        FullThroughHardwareLocation.EXTERIOR_FAR_SIDE,
    )
    assert hardware.physical_bolt_count == hardware.continuous_shank_count == 1
    assert hardware.internal_hardware_count == 0


def test_c1_g11_exact_us_si_path_equivalence_and_fingerprints() -> None:
    per_inch = D("25.4")
    rhs_us = _rhs_core()
    srs_us = _srs_core()
    rhs_si_normalized = _rhs_core(scale=per_inch)
    srs_si_normalized = _srs_core(scale=per_inch)

    def normalize(path: FullThroughBoltPath) -> FullThroughBoltPath:
        return replace(
            path,
            axis=replace(
                path.axis,
                local_u=path.axis.local_u / per_inch,
                local_v=path.axis.local_v / per_inch,
            ),
            segments=tuple(replace(item, length=item.length / per_inch) for item in path.segments),
        )

    assert [item.length for item in rhs_si_normalized.segments] == [
        D("12.7"),
        D("127"),
        D("12.7"),
    ]
    assert rhs_si_normalized.shank_length == D("152.4")
    assert srs_si_normalized.shank_length == D("152.4")
    assert full_through_bolt_fingerprint(rhs_us) == full_through_bolt_fingerprint(
        normalize(rhs_si_normalized)
    )
    assert full_through_bolt_fingerprint(srs_us) == full_through_bolt_fingerprint(
        normalize(srs_si_normalized)
    )
    assert canonical_full_through_bolt_json(rhs_us).startswith('{"axis":')


def test_c1_g12_records_only_fail_closed_future_local_mechanics() -> None:
    assert RECTANGULAR_LOCAL_MECHANICS_LIMITATIONS == (
        RectangularLocalMechanicsLimitation.RHS_LOCAL_WALL_RESPONSE,
        RectangularLocalMechanicsLimitation.RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT,
        RectangularLocalMechanicsLimitation.SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY,
    )
    assert not hasattr(RectangularLocalMechanicsLimitation, "PASS")


def test_c1_path_and_registry_contracts_are_frozen_slotted_and_strict() -> None:
    path = _rhs_core()
    with pytest.raises(FrozenInstanceError):
        path.bolt_id = "other"  # type: ignore[misc]
    assert not hasattr(path, "__dict__")

    with pytest.raises(TypeError, match="target_id"):
        shared_support_target("W_COLUMN_WEB")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="column or beam"):
        replace(SHARED_SUPPORT_TARGET_REGISTRY[0], support_role=MemberRole.BRACE)
    with pytest.raises(ValueError, match="at least one"):
        replace(SHARED_SUPPORT_TARGET_REGISTRY[0], selectable_surface_ids=())
    with pytest.raises(TypeError, match="MemberProfileSurfaceId"):
        replace(
            SHARED_SUPPORT_TARGET_REGISTRY[0],
            selectable_surface_ids=("bad",),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="unique"):
        replace(
            SHARED_SUPPORT_TARGET_REGISTRY[0],
            selectable_surface_ids=(
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
            ),
        )


def test_c1_low_level_contracts_reject_malformed_physical_paths() -> None:
    basis = _basis()
    material = external_connector_layer(
        "CONNECTOR", D("0.5"), material_region_id="connector", material_basis=basis
    )
    free = PhysicalBoltPathSegment(
        PhysicalBoltPathSegmentKind.FREE_SHANK_SPAN,
        "FREE",
        D("1"),
        "ENTRY",
        "EXIT",
    )

    with pytest.raises(TypeError, match="Decimal"):
        replace(material, length=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        replace(material, length=D("NaN"))
    with pytest.raises(ValueError, match="greater than zero"):
        replace(material, length=D("0"))
    with pytest.raises(ValueError, match="distinct"):
        replace(material, exit_plane_id=material.entry_plane_id)
    with pytest.raises(ValueError, match="material-region"):
        replace(material, material_region_id=None)
    with pytest.raises(TypeError, match="material basis"):
        replace(material, material_basis=None)
    with pytest.raises(ValueError, match="cannot carry"):
        replace(free, material_region_id="bad")
    with pytest.raises(TypeError, match="RectangularBoltAxis"):
        FullThroughBoltPath("bolt", object(), (material,))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at least one"):
        FullThroughBoltPath("bolt", _rhs_core().axis, ())
    with pytest.raises(TypeError, match="PhysicalBoltPathSegment"):
        FullThroughBoltPath("bolt", _rhs_core().axis, (object(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="FullThroughBoltPath"):
        compose_external_connector_layers(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="physical path segments"):
        compose_external_connector_layers(_rhs_core(), near_layers=(object(),))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="material layers only"):
        compose_external_connector_layers(_rhs_core(), near_layers=(free,))
    with pytest.raises(TypeError, match="FullThroughBoltPath"):
        full_through_bolt_hardware(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="FullThroughBoltPath"):
        canonical_full_through_bolt_json(object())  # type: ignore[arg-type]


def test_c1_low_level_geometry_contracts_reject_invalid_types_and_values() -> None:
    pair = rectangular_opposing_face_pair(_rhs(), MemberProfileSurfaceId.Y_POS_FACE)
    with pytest.raises(TypeError, match="MemberProfile"):
        rectangular_opposing_face_pair(object(), MemberProfileSurfaceId.Y_POS_FACE)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires RHS or SRS"):
        rectangular_opposing_face_pair(
            _flat_plate(),
            MemberProfileSurfaceId.Y_POS_FACE,
        )
    with pytest.raises(TypeError, match="selected_surface_id"):
        rectangular_opposing_face_pair(_rhs(), "Y_POS_FACE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="four rectangular"):
        rectangular_opposing_face_pair(_rhs(), MemberProfileSurfaceId.WEB_OUTER)
    with pytest.raises(TypeError, match="two-item tuple"):
        build_rhs_full_through_core(
            _rhs(),
            MemberProfileSurfaceId.Y_POS_FACE,
            bolt_id="bolt",
            local_uv=[D("0"), D("0")],  # type: ignore[arg-type]
            material_region_id="rhs",
        )
    with pytest.raises(ValueError, match="RHS member profile"):
        build_rhs_full_through_core(
            _srs(),
            MemberProfileSurfaceId.Y_POS_FACE,
            bolt_id="bolt",
            local_uv=(D("0"), D("0")),
            material_region_id="rhs",
        )
    with pytest.raises(ValueError, match="SRS member profile"):
        build_srs_full_through_core(
            _rhs(),
            MemberProfileSurfaceId.Y_POS_FACE,
            bolt_id="bolt",
            local_uv=(D("0"), D("0")),
            material_region_id="srs",
        )
    assert pair.selected_frame.origin == pair.selected_surface.center


def test_c1_face_and_aggregate_containment_contracts_are_fail_closed() -> None:
    surface = rectangular_opposing_face_pair(
        _srs(), MemberProfileSurfaceId.Y_POS_FACE
    ).selected_surface
    valid = evaluate_face_hole_containment(
        surface, bolt_id="bolt", local_uv=(D("0"), D("0")), hole_radius=D("0")
    )
    invalid = FaceHoleContainment(
        MemberProfileSurfaceId.Y_NEG_FACE,
        "bolt",
        False,
        D("-1"),
        D("1"),
    )
    with pytest.raises(TypeError, match="must be a bool"):
        replace(valid, valid=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ProfileSurfaceDefinition"):
        evaluate_face_hole_containment(
            object(),  # type: ignore[arg-type]
            bolt_id="bolt",
            local_uv=(D("0"), D("0")),
            hole_radius=D("0"),
        )
    with pytest.raises(TypeError, match="two-item tuple"):
        evaluate_face_hole_containment(
            surface,
            bolt_id="bolt",
            local_uv=(D("0"),),  # type: ignore[arg-type]
            hole_radius=D("0"),
        )
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_face_hole_containment(
            surface, bolt_id="bolt", local_uv=(D("0"), D("0")), hole_radius=D("-1")
        )
    with pytest.raises(TypeError, match="FaceHoleContainment"):
        aggregate_full_through_containment(valid, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RectangularBoltAxis"):
        evaluate_full_through_containment(
            _srs(),
            object(),  # type: ignore[arg-type]
            bolt_id="bolt",
            hole_radius=D("0"),
        )
    with pytest.raises(ValueError, match="two distinct"):
        aggregate_full_through_containment(valid, valid)
    with pytest.raises(ValueError, match="exactly two"):
        replace(
            aggregate_full_through_containment(valid, invalid),
            face_results=(valid,),
        )
    aggregate = aggregate_full_through_containment(valid, invalid)
    with pytest.raises(ValueError, match="governing containment"):
        replace(aggregate, governing_bolt="wrong")
    with pytest.raises(ValueError, match="status"):
        replace(aggregate, status=RectangularContainmentStatus.VALID)
    with pytest.raises(ValueError, match="negative-clearance"):
        replace(invalid, exact_deficit=D("0"))
    with pytest.raises(ValueError, match="validity"):
        replace(invalid, valid=True)


def test_c1_frames_bases_pairs_and_hardware_enforce_exact_invariants() -> None:
    x = ExactProfileVector3D(D("1"), D("0"), D("0"))
    y = ExactProfileVector3D(D("0"), D("1"), D("0"))
    z = ExactProfileVector3D(D("0"), D("0"), D("1"))
    pair = rectangular_opposing_face_pair(_srs(), MemberProfileSurfaceId.Y_POS_FACE)

    with pytest.raises(TypeError, match="basis axes"):
        RectangularMaterialBasis(x, y, object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="cardinal"):
        RectangularMaterialBasis(x, y, ExactProfileVector3D(D("1"), D("1"), D("0")))
    with pytest.raises(ValueError, match="orthogonal"):
        RectangularMaterialBasis(x, y, y)
    with pytest.raises(TypeError, match="face-frame values"):
        RectangularFaceLocalFrame(object(), y, x, z)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="cardinal"):
        RectangularFaceLocalFrame(
            ExactProfileVector3D(D("0"), D("0"), D("0")),
            ExactProfileVector3D(D("1"), D("1"), D("0")),
            x,
            z,
        )
    with pytest.raises(ValueError, match="orthogonal"):
        RectangularFaceLocalFrame(ExactProfileVector3D(D("0"), D("0"), D("0")), y, x, x)
    with pytest.raises(ValueError, match="requires RHS or SRS"):
        replace(pair, profile_family=MemberProfileFamily.ANGLE)
    with pytest.raises(TypeError, match="profile surface definitions"):
        replace(pair, selected_surface=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact local frames"):
        replace(pair, selected_frame=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="one exact plane axis"):
        replace(
            pair,
            opposite_surface=rectangular_opposing_face_pair(
                _srs(), MemberProfileSurfaceId.Z_NEG_FACE
            ).selected_surface,
        )
    with pytest.raises(ValueError, match="separation must be exact"):
        replace(pair, separation=D("3"))
    with pytest.raises(ValueError, match="normals must be exact opposites"):
        replace(
            pair,
            opposite_surface=replace(
                pair.opposite_surface,
                local_outward_normal=pair.selected_surface.local_outward_normal,
            ),
        )
    with pytest.raises(ValueError, match="share one exact"):
        replace(
            pair,
            opposite_frame=replace(
                pair.opposite_frame,
                v_axis=ExactProfileVector3D(D("0"), D("0"), D("-1")),
            ),
        )

    hardware = full_through_bolt_hardware(_srs_core())
    with pytest.raises(ValueError, match="near exterior"):
        replace(hardware, head_location=FullThroughHardwareLocation.EXTERIOR_FAR_SIDE)
    with pytest.raises(ValueError, match="far exterior"):
        replace(hardware, nut_location=FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE)
    with pytest.raises(ValueError, match="both exterior"):
        replace(hardware, washer_locations=(FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,))
    with pytest.raises(ValueError, match="one bolt/shank"):
        replace(hardware, internal_hardware_count=1)
