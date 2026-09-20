"""Exact Stage 3.2-R2 member/profile domain contract tests."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from typing import cast

import pytest

import frp_master_connection.domain.member_profile as subject
from frp_master_connection.domain.member_profile import (
    DIRECT_TEE_CURVED_SURFACE_REASON,
    AngleProfileDimensions,
    ChannelProfileDimensions,
    ExactProfileVector3D,
    FlatPlateProfileDimensions,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    ProfileLocalBounds3D,
    ProfileSectionGeometryAdapter,
    ProfileSurfaceDefinition,
    RectangularHollowProfileDimensions,
    RoundHollowProfileDimensions,
    WideFlangeIProfileDimensions,
    canonical_member_profile_json,
    canonical_profile_geometry_json,
    member_profile_fingerprint,
    profile_geometry_fingerprint,
    profile_section_geometry_adapter,
    profile_surface_registry,
    require_direct_tee_profile_surface,
    resolve_profile_surface,
    section_family_for_profile,
    selectable_profile_surfaces,
)
from frp_master_connection.domain.section_topology import (
    FRPComponentOrientation,
    PhysicalSectionElementRole,
)
from frp_master_connection.domain.values import (
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    MemberRole,
    PrincipalAxisFamily,
    SectionFamily,
)

D = Decimal


def _material_orientation(
    member_id: str = "member-1",
    *,
    frame_kind: CoordinateFrameKind = CoordinateFrameKind.MEMBER_LOCAL,
    lengthwise_axis: PrincipalAxisFamily = PrincipalAxisFamily.X,
) -> FRPComponentOrientation:
    return FRPComponentOrientation(
        CoordinateFrameReference(frame_kind, member_id),
        lengthwise_axis,
    )


DIMENSIONS: dict[MemberProfileFamily, MemberProfileDimensions] = {
    MemberProfileFamily.ANGLE: AngleProfileDimensions(D("8"), D("4"), D("3"), D("0.5")),
    MemberProfileFamily.CHANNEL: ChannelProfileDimensions(
        D("8"), D("6"), D("3"), D("0.5"), D("0.5")
    ),
    MemberProfileFamily.WIDE_FLANGE_I: WideFlangeIProfileDimensions(
        D("8"), D("8"), D("8"), D("0.5"), D("0.5")
    ),
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: RectangularHollowProfileDimensions(
        D("8"), D("6"), D("4"), D("0.5")
    ),
    MemberProfileFamily.FLAT_PLATE: FlatPlateProfileDimensions(D("8"), D("4"), D("0.5")),
    MemberProfileFamily.ROUND_HOLLOW_SECTION: RoundHollowProfileDimensions(
        D("8"), D("4"), D("0.25")
    ),
}

SURFACES = {
    MemberProfileFamily.ANGLE: MemberProfileSurfaceId.LEG_Y_OUTER,
    MemberProfileFamily.CHANNEL: MemberProfileSurfaceId.WEB_OUTER,
    MemberProfileFamily.WIDE_FLANGE_I: MemberProfileSurfaceId.WEB_POS_FACE,
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: MemberProfileSurfaceId.Y_POS_FACE,
    MemberProfileFamily.FLAT_PLATE: MemberProfileSurfaceId.FACE_POS,
    MemberProfileFamily.ROUND_HOLLOW_SECTION: None,
}


def _profile(
    family: MemberProfileFamily = MemberProfileFamily.ANGLE,
    *,
    role: MemberRole = MemberRole.BRACE,
    orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0,
    selected_surface: MemberProfileSurfaceId | object | None = ...,
    material_kind: ComponentMaterialKind = ComponentMaterialKind.PULTRUDED_FRP,
    material_orientation: FRPComponentOrientation | object | None = ...,
    profile_id: str = "profile-1",
    member_id: str = "member-1",
) -> MemberProfile:
    surface = SURFACES[family] if selected_surface is ... else selected_surface
    frp_orientation = (
        _material_orientation(member_id)
        if material_orientation is ... and material_kind is ComponentMaterialKind.PULTRUDED_FRP
        else None
        if material_orientation is ...
        else material_orientation
    )
    assert surface is None or isinstance(surface, MemberProfileSurfaceId)
    assert frp_orientation is None or isinstance(frp_orientation, FRPComponentOrientation)
    return MemberProfile(
        profile_id,
        member_id,
        role,
        family,
        DIMENSIONS[family],
        material_kind,
        frp_orientation,
        orientation,
        surface,
    )


def test_profile_values_are_exact_immutable_and_slotted() -> None:
    profile = _profile()

    assert profile.member_length == D("8")
    assert profile.section_family is SectionFamily.ANGLE
    assert profile.size_basis is MemberProfileSizeBasis.CUSTOM_DIMENSIONS
    assert hash(profile) == hash(profile)
    assert not hasattr(profile, "__dict__")
    with pytest.raises(FrozenInstanceError):
        profile.role = MemberRole.BEAM  # type: ignore[misc]


@pytest.mark.parametrize(
    ("orientation", "turns"),
    [
        (MemberProfileOrientation.ROTATION_0, 0),
        (MemberProfileOrientation.ROTATION_90, 1),
        (MemberProfileOrientation.ROTATION_180, 2),
        (MemberProfileOrientation.ROTATION_270, 3),
    ],
)
def test_profile_orientation_has_exact_right_hand_quarter_turns(
    orientation: MemberProfileOrientation,
    turns: int,
) -> None:
    assert orientation.quarter_turns == turns


@pytest.mark.parametrize(
    ("family", "expected_section", "expected_factory", "expected_names", "offsets"),
    [
        (
            MemberProfileFamily.ANGLE,
            SectionFamily.ANGLE,
            "create_angle_geometry",
            ("leg_y", "leg_z", "thickness"),
            (D("2"), D("1.5")),
        ),
        (
            MemberProfileFamily.CHANNEL,
            SectionFamily.CHANNEL,
            "create_channel_geometry",
            ("overall_depth", "flange_width", "web_thickness", "flange_thickness"),
            (D("1.5"), D("0")),
        ),
        (
            MemberProfileFamily.WIDE_FLANGE_I,
            SectionFamily.WIDE_FLANGE,
            "create_wide_flange_geometry",
            ("overall_depth", "flange_width", "web_thickness", "flange_thickness"),
            (D("0"), D("0")),
        ),
        (
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            SectionFamily.RECTANGULAR_TUBE,
            "create_rectangular_tube_geometry",
            ("outside_width", "outside_depth", "wall_thickness"),
            (D("0"), D("0")),
        ),
        (
            MemberProfileFamily.FLAT_PLATE,
            SectionFamily.PLATE,
            "create_plate_geometry",
            ("width", "thickness"),
            (D("0"), D("0")),
        ),
        (
            MemberProfileFamily.ROUND_HOLLOW_SECTION,
            SectionFamily.ROUND_TUBE,
            "create_round_tube_geometry",
            ("outer_diameter", "wall_thickness"),
            (D("0"), D("0")),
        ),
    ],
)
def test_profile_geometry_adapter_reuses_existing_section_families_and_factories(
    family: MemberProfileFamily,
    expected_section: SectionFamily,
    expected_factory: str,
    expected_names: tuple[str, ...],
    offsets: tuple[Decimal, Decimal],
) -> None:
    profile = _profile(family)
    adapter = profile_section_geometry_adapter(profile)

    assert section_family_for_profile(family) is expected_section
    assert adapter.section_family is expected_section
    assert adapter.geometry_factory_name == expected_factory
    assert tuple(name for name, _ in adapter.dimension_values) == expected_names
    assert adapter.member_length == D("8")
    assert (adapter.section_datum_offset_y, adapter.section_datum_offset_z) == offsets


def test_profile_geometry_adapter_rejects_non_profiles() -> None:
    with pytest.raises(TypeError, match="profile must be"):
        profile_section_geometry_adapter(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("family", "surfaces"),
    [
        (
            MemberProfileFamily.ANGLE,
            (MemberProfileSurfaceId.LEG_Y_OUTER, MemberProfileSurfaceId.LEG_Z_OUTER),
        ),
        (
            MemberProfileFamily.CHANNEL,
            (
                MemberProfileSurfaceId.WEB_OUTER,
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
                MemberProfileSurfaceId.FLANGE_NEG_OUTER,
            ),
        ),
        (
            MemberProfileFamily.WIDE_FLANGE_I,
            (
                MemberProfileSurfaceId.WEB_POS_FACE,
                MemberProfileSurfaceId.WEB_NEG_FACE,
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
                MemberProfileSurfaceId.FLANGE_NEG_OUTER,
            ),
        ),
        (
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            (
                MemberProfileSurfaceId.Y_POS_FACE,
                MemberProfileSurfaceId.Y_NEG_FACE,
                MemberProfileSurfaceId.Z_POS_FACE,
                MemberProfileSurfaceId.Z_NEG_FACE,
            ),
        ),
        (
            MemberProfileFamily.FLAT_PLATE,
            (MemberProfileSurfaceId.FACE_POS, MemberProfileSurfaceId.FACE_NEG),
        ),
        (MemberProfileFamily.ROUND_HOLLOW_SECTION, ()),
    ],
)
def test_surface_filtering_is_an_exact_closed_family_vocabulary(
    family: MemberProfileFamily,
    surfaces: tuple[MemberProfileSurfaceId, ...],
) -> None:
    assert selectable_profile_surfaces(family) == surfaces
    assert tuple(item.surface_id for item in profile_surface_registry(_profile(family))) == surfaces


@pytest.mark.parametrize(
    "function",
    [selectable_profile_surfaces, section_family_for_profile],
)
def test_family_helpers_require_typed_profile_identity(function: object) -> None:
    with pytest.raises(TypeError):
        function("ANGLE")  # type: ignore[operator]


@pytest.mark.parametrize(
    ("family", "expected"),
    [
        (
            MemberProfileFamily.ANGLE,
            {
                MemberProfileSurfaceId.LEG_Y_OUTER: (PrincipalAxisFamily.Z, D("0"), (0, 0, -1)),
                MemberProfileSurfaceId.LEG_Z_OUTER: (PrincipalAxisFamily.Y, D("0"), (0, -1, 0)),
            },
        ),
        (
            MemberProfileFamily.CHANNEL,
            {
                MemberProfileSurfaceId.WEB_OUTER: (PrincipalAxisFamily.Y, D("0"), (0, -1, 0)),
                MemberProfileSurfaceId.FLANGE_POS_OUTER: (
                    PrincipalAxisFamily.Z,
                    D("3"),
                    (0, 0, 1),
                ),
                MemberProfileSurfaceId.FLANGE_NEG_OUTER: (
                    PrincipalAxisFamily.Z,
                    D("-3"),
                    (0, 0, -1),
                ),
            },
        ),
        (
            MemberProfileFamily.WIDE_FLANGE_I,
            {
                MemberProfileSurfaceId.WEB_POS_FACE: (
                    PrincipalAxisFamily.Y,
                    D("0.25"),
                    (0, 1, 0),
                ),
                MemberProfileSurfaceId.WEB_NEG_FACE: (
                    PrincipalAxisFamily.Y,
                    D("-0.25"),
                    (0, -1, 0),
                ),
                MemberProfileSurfaceId.FLANGE_POS_OUTER: (
                    PrincipalAxisFamily.Z,
                    D("4"),
                    (0, 0, 1),
                ),
                MemberProfileSurfaceId.FLANGE_NEG_OUTER: (
                    PrincipalAxisFamily.Z,
                    D("-4"),
                    (0, 0, -1),
                ),
            },
        ),
        (
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            {
                MemberProfileSurfaceId.Y_POS_FACE: (PrincipalAxisFamily.Y, D("2"), (0, 1, 0)),
                MemberProfileSurfaceId.Y_NEG_FACE: (PrincipalAxisFamily.Y, D("-2"), (0, -1, 0)),
                MemberProfileSurfaceId.Z_POS_FACE: (PrincipalAxisFamily.Z, D("3"), (0, 0, 1)),
                MemberProfileSurfaceId.Z_NEG_FACE: (PrincipalAxisFamily.Z, D("-3"), (0, 0, -1)),
            },
        ),
        (
            MemberProfileFamily.FLAT_PLATE,
            {
                MemberProfileSurfaceId.FACE_POS: (PrincipalAxisFamily.Z, D("0.25"), (0, 0, 1)),
                MemberProfileSurfaceId.FACE_NEG: (PrincipalAxisFamily.Z, D("-0.25"), (0, 0, -1)),
            },
        ),
    ],
)
def test_owner_g1_to_g5_planes_normals_bounds_and_physical_layers_are_exact(
    family: MemberProfileFamily,
    expected: dict[
        MemberProfileSurfaceId,
        tuple[PrincipalAxisFamily, Decimal, tuple[int, int, int]],
    ],
) -> None:
    definitions = profile_surface_registry(_profile(family))

    assert {item.surface_id for item in definitions} == set(expected)
    for item in definitions:
        axis, coordinate, normal = expected[item.surface_id]
        assert item.plane_axis is axis
        assert item.plane_coordinate == coordinate
        assert (
            item.local_outward_normal.x,
            item.local_outward_normal.y,
            item.local_outward_normal.z,
        ) == tuple(D(value) for value in normal)
        assert item.contact_bounds.min_x == D("-4")
        assert item.contact_bounds.max_x == D("4")
        assert item.center == item.contact_bounds.center
        assert item.layer_thickness > 0
        assert item.physical_element_id == item.physical_element_role.value
        assert len(item.penetration_bounds) == len(item.opposing_patch_ids)


def test_owner_g1_and_g3_penetration_filters_exclude_nonphysical_overlap() -> None:
    angle = {item.surface_id: item for item in profile_surface_registry(_profile())}
    wide_flange = {
        item.surface_id: item
        for item in profile_surface_registry(_profile(MemberProfileFamily.WIDE_FLANGE_I))
    }

    assert angle[MemberProfileSurfaceId.LEG_Y_OUTER].penetration_bounds[0].min_y == D("0.5")
    assert angle[MemberProfileSurfaceId.LEG_Z_OUTER].penetration_bounds[0].min_z == D("0.5")
    assert len(wide_flange[MemberProfileSurfaceId.FLANGE_POS_OUTER].penetration_bounds) == 2
    assert len(wide_flange[MemberProfileSurfaceId.FLANGE_NEG_OUTER].penetration_bounds) == 2


def test_full_contact_spans_use_fail_closed_physical_element_penetration_regions() -> None:
    """Owner contact spans stay whole while invalid element junctions are not penetrable."""
    channel = {
        item.surface_id: item
        for item in profile_surface_registry(_profile(MemberProfileFamily.CHANNEL))
    }
    rectangular_hollow = {
        item.surface_id: item
        for item in profile_surface_registry(
            _profile(MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION)
        )
    }

    channel_flange = channel[MemberProfileSurfaceId.FLANGE_POS_OUTER]
    assert (channel_flange.contact_bounds.min_y, channel_flange.contact_bounds.max_y) == (
        D("0"),
        D("3"),
    )
    assert channel_flange.penetration_bounds[0].min_y == D("0.5")
    rhs_side = rectangular_hollow[MemberProfileSurfaceId.Y_POS_FACE]
    assert (rhs_side.contact_bounds.min_z, rhs_side.contact_bounds.max_z) == (D("-3"), D("3"))
    assert (rhs_side.penetration_bounds[0].min_z, rhs_side.penetration_bounds[0].max_z) == (
        D("-2.5"),
        D("2.5"),
    )


@pytest.mark.parametrize(
    ("orientation", "axis", "coordinate", "normal"),
    [
        (MemberProfileOrientation.ROTATION_0, PrincipalAxisFamily.Z, D("0.25"), (0, 0, 1)),
        (MemberProfileOrientation.ROTATION_90, PrincipalAxisFamily.Y, D("-0.25"), (0, -1, 0)),
        (MemberProfileOrientation.ROTATION_180, PrincipalAxisFamily.Z, D("-0.25"), (0, 0, -1)),
        (MemberProfileOrientation.ROTATION_270, PrincipalAxisFamily.Y, D("0.25"), (0, 1, 0)),
    ],
)
def test_profile_orientation_rotates_surface_geometry_about_local_x(
    orientation: MemberProfileOrientation,
    axis: PrincipalAxisFamily,
    coordinate: Decimal,
    normal: tuple[int, int, int],
) -> None:
    surface = resolve_profile_surface(
        _profile(MemberProfileFamily.FLAT_PLATE, orientation=orientation)
    )

    assert surface.plane_axis is axis
    assert surface.plane_coordinate == coordinate
    assert (
        surface.local_outward_normal.x,
        surface.local_outward_normal.y,
        surface.local_outward_normal.z,
    ) == tuple(D(value) for value in normal)
    assert surface.layer_thickness == D("0.5")


def test_rotation_of_a_y_plane_uses_its_y_opposite_coordinate() -> None:
    surface = resolve_profile_surface(
        _profile(
            MemberProfileFamily.ANGLE,
            orientation=MemberProfileOrientation.ROTATION_90,
            selected_surface=MemberProfileSurfaceId.LEG_Z_OUTER,
        )
    )

    assert surface.plane_axis is PrincipalAxisFamily.Z
    assert surface.plane_coordinate == D("0")
    assert surface.local_outward_normal == ExactProfileVector3D(D("0"), D("0"), D("-1"))
    assert surface.opposite_plane_coordinate == D("0.5")


def test_wide_flange_local_geometry_is_independent_of_support_role() -> None:
    column = _profile(
        MemberProfileFamily.WIDE_FLANGE_I,
        role=MemberRole.COLUMN,
        selected_surface=MemberProfileSurfaceId.FLANGE_POS_OUTER,
    )
    beam = replace(column, id="profile-2", role=MemberRole.BEAM)

    assert resolve_profile_surface(column) == resolve_profile_surface(beam)
    assert profile_geometry_fingerprint(column) == profile_geometry_fingerprint(beam)
    assert member_profile_fingerprint(column) != member_profile_fingerprint(beam)


def test_round_hollow_identity_is_valid_but_direct_tee_surface_is_rejected() -> None:
    profile = _profile(MemberProfileFamily.ROUND_HOLLOW_SECTION)

    assert profile_surface_registry(profile) == ()
    assert len(profile_geometry_fingerprint(profile)) == 64
    with pytest.raises(ValueError, match=DIRECT_TEE_CURVED_SURFACE_REASON):
        require_direct_tee_profile_surface(profile)


@pytest.mark.parametrize("function", [profile_surface_registry, resolve_profile_surface])
def test_surface_resolvers_reject_non_profiles(function: object) -> None:
    with pytest.raises(TypeError, match="profile must be"):
        function(object())  # type: ignore[operator]


def test_canonical_fingerprints_are_stable_exact_and_scope_display_state_out() -> None:
    profile = _profile()
    equal_decimal_spelling = replace(
        profile,
        dimensions=AngleProfileDimensions(D("8.0"), D("4.00"), D("3.0"), D("0.500")),
    )
    other_surface = replace(profile, selected_surface=MemberProfileSurfaceId.LEG_Z_OUTER)

    assert canonical_profile_geometry_json(profile) == canonical_profile_geometry_json(
        equal_decimal_spelling
    )
    assert profile_geometry_fingerprint(profile) == profile_geometry_fingerprint(
        equal_decimal_spelling
    )
    assert canonical_member_profile_json(profile) == canonical_member_profile_json(profile)
    assert member_profile_fingerprint(profile) == member_profile_fingerprint(profile)
    assert profile_geometry_fingerprint(profile) == profile_geometry_fingerprint(other_surface)
    assert member_profile_fingerprint(profile) != member_profile_fingerprint(other_surface)
    assert "camera" not in canonical_member_profile_json(profile)
    assert "0.500" not in canonical_profile_geometry_json(equal_decimal_spelling)
    assert subject._canonical_decimal(D("-0")) == "0"


def test_closed_surface_dimension_union_rejects_unvalidated_internal_call() -> None:
    with pytest.raises(TypeError, match="Unsupported profile dimensions"):
        subject._base_surface_registry(object())  # type: ignore[arg-type]


def test_full_fingerprint_supports_non_frp_without_material_orientation() -> None:
    profile = _profile(
        material_kind=ComponentMaterialKind.STEEL,
        material_orientation=None,
    )

    assert '"material_orientation":null' in canonical_member_profile_json(profile)


@pytest.mark.parametrize(
    "function",
    [canonical_profile_geometry_json, profile_geometry_fingerprint, canonical_member_profile_json],
)
def test_fingerprint_helpers_reject_non_profiles(function: object) -> None:
    with pytest.raises(TypeError, match="profile must be"):
        function(object())  # type: ignore[operator]


@pytest.mark.parametrize(
    "dimensions",
    [
        FlatPlateProfileDimensions(D("1"), D("1"), D("0.1")),
        AngleProfileDimensions(D("1"), D("1"), D("1"), D("0.1")),
        ChannelProfileDimensions(D("1"), D("1"), D("1"), D("0.1"), D("0.1")),
        WideFlangeIProfileDimensions(D("1"), D("1"), D("1"), D("0.1"), D("0.1")),
        RectangularHollowProfileDimensions(D("1"), D("1"), D("1"), D("0.1")),
        RoundHollowProfileDimensions(D("1"), D("1"), D("0.1")),
    ],
)
def test_all_dimension_contracts_are_frozen_and_hashable(dimensions: object) -> None:
    assert hash(dimensions) == hash(dimensions)
    assert not hasattr(dimensions, "__dict__")


@pytest.mark.parametrize(
    ("factory", "error"),
    [
        (lambda: FlatPlateProfileDimensions(cast(Decimal, 1), D("1"), D("0.1")), TypeError),
        (lambda: FlatPlateProfileDimensions(D("NaN"), D("1"), D("0.1")), ValueError),
        (lambda: FlatPlateProfileDimensions(D("0"), D("1"), D("0.1")), ValueError),
        (lambda: AngleProfileDimensions(D("1"), D("0.1"), D("1"), D("0.1")), ValueError),
        (lambda: AngleProfileDimensions(D("1"), D("1"), D("0.1"), D("0.1")), ValueError),
        (lambda: ChannelProfileDimensions(D("1"), D("1"), D("1"), D("0.1"), D("0.5")), ValueError),
        (
            lambda: ChannelProfileDimensions(D("1"), D("1"), D("0.1"), D("0.1"), D("0.1")),
            ValueError,
        ),
        (
            lambda: RectangularHollowProfileDimensions(D("1"), D("0.2"), D("1"), D("0.1")),
            ValueError,
        ),
        (
            lambda: RectangularHollowProfileDimensions(D("1"), D("1"), D("0.2"), D("0.1")),
            ValueError,
        ),
        (lambda: RoundHollowProfileDimensions(D("1"), D("0.2"), D("0.1")), ValueError),
    ],
)
def test_invalid_dimensions_are_rejected(factory: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        factory()  # type: ignore[operator]


def test_member_profile_requires_matching_typed_dimensions() -> None:
    with pytest.raises(TypeError, match="requires AngleProfileDimensions"):
        replace(_profile(), dimensions=DIMENSIONS[MemberProfileFamily.FLAT_PLATE])


@pytest.mark.parametrize(
    ("changes", "error", "match"),
    [
        ({"role": "BRACE"}, TypeError, "MemberProfile.role"),
        ({"family": "ANGLE"}, TypeError, "MemberProfile.family"),
        ({"material_kind": "PULTRUDED_FRP"}, TypeError, "MemberProfile.material_kind"),
        ({"orientation": "ROTATION_0"}, TypeError, "MemberProfile.orientation"),
        ({"size_basis": "CUSTOM_DIMENSIONS"}, TypeError, "MemberProfile.size_basis"),
        ({"selected_surface": None}, TypeError, "selected_surface"),
        ({"selected_surface": MemberProfileSurfaceId.WEB_OUTER}, ValueError, "not exposed"),
    ],
)
def test_member_profile_rejects_untyped_or_cross_family_state(
    changes: dict[str, object],
    error: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error, match=match):
        replace(_profile(), **changes)  # type: ignore[arg-type]


def test_round_profile_rejects_direct_flat_surface_selection() -> None:
    with pytest.raises(ValueError, match="no selectable direct flat surface"):
        _profile(
            MemberProfileFamily.ROUND_HOLLOW_SECTION,
            selected_surface=MemberProfileSurfaceId.FACE_POS,
        )


def test_frp_profile_requires_member_local_material_orientation_for_same_member() -> None:
    with pytest.raises(TypeError, match="require material orientation"):
        _profile(material_orientation=None)
    with pytest.raises(ValueError, match="member-local frame"):
        _profile(
            material_orientation=_material_orientation(
                frame_kind=CoordinateFrameKind.CONNECTOR_LOCAL
            )
        )
    with pytest.raises(ValueError, match="member-local frame"):
        _profile(material_orientation=_material_orientation("other-member"))


def test_non_frp_profile_rejects_frp_orientation() -> None:
    with pytest.raises(ValueError, match="must not carry"):
        _profile(
            material_kind=ComponentMaterialKind.STEEL,
            material_orientation=_material_orientation(),
        )


def _valid_bounds() -> ProfileLocalBounds3D:
    return ProfileLocalBounds3D(D("-1"), D("1"), D("0"), D("0"), D("-1"), D("1"))


def _valid_surface() -> ProfileSurfaceDefinition:
    bounds = _valid_bounds()
    return ProfileSurfaceDefinition(
        MemberProfileSurfaceId.WEB_OUTER,
        PrincipalAxisFamily.Y,
        D("0"),
        ExactProfileVector3D(D("0"), D("-1"), D("0")),
        bounds,
        (bounds,),
        PhysicalSectionElementRole.WEB,
        "WEB:OUTSIDE",
        ("WEB:INSIDE",),
        D("0.5"),
    )


def test_exact_bounds_center_and_validation() -> None:
    bounds = _valid_bounds()

    assert bounds.center == ExactProfileVector3D(D("0"), D("0"), D("0"))
    with pytest.raises(TypeError):
        ExactProfileVector3D(cast(Decimal, 0), D("0"), D("0"))
    with pytest.raises(ValueError, match="finite"):
        ExactProfileVector3D(D("Infinity"), D("0"), D("0"))
    with pytest.raises(TypeError):
        ProfileLocalBounds3D(cast(Decimal, 0), D("1"), D("0"), D("0"), D("-1"), D("1"))
    with pytest.raises(ValueError, match="nondecreasing"):
        ProfileLocalBounds3D(D("1"), D("-1"), D("0"), D("0"), D("-1"), D("1"))
    with pytest.raises(ValueError, match="exactly one finite plane"):
        ProfileLocalBounds3D(D("-1"), D("1"), D("-1"), D("1"), D("-1"), D("1"))
    with pytest.raises(ValueError, match="exactly one finite plane"):
        ProfileLocalBounds3D(D("0"), D("0"), D("0"), D("0"), D("-1"), D("1"))


@pytest.mark.parametrize(
    ("changes", "error", "match"),
    [
        ({"surface_id": "WEB_OUTER"}, TypeError, "surface_id"),
        ({"plane_axis": "Y"}, TypeError, "plane_axis"),
        ({"plane_axis": PrincipalAxisFamily.X}, ValueError, "longitudinal"),
        ({"plane_coordinate": 0}, TypeError, "plane_coordinate"),
        ({"opposite_plane_coordinate": D("NaN")}, ValueError, "finite"),
        ({"opposite_plane_coordinate": D("0")}, ValueError, "positive through-thickness"),
        ({"local_outward_normal": (0, -1, 0)}, TypeError, "normal"),
        (
            {"local_outward_normal": ExactProfileVector3D(D("1"), D("0"), D("0"))},
            ValueError,
            "axis-aligned",
        ),
        ({"contact_bounds": object()}, TypeError, "contact_bounds"),
        (
            {
                "contact_bounds": ProfileLocalBounds3D(
                    D("-1"), D("1"), D("1"), D("1"), D("-1"), D("1")
                )
            },
            ValueError,
            "declared plane",
        ),
        ({"penetration_bounds": [_valid_bounds()]}, TypeError, "penetration_bounds"),
        ({"penetration_bounds": ()}, ValueError, "requires penetrable"),
        ({"penetration_bounds": (object(),)}, TypeError, "exact bounds"),
        (
            {
                "penetration_bounds": (
                    ProfileLocalBounds3D(D("-1"), D("1"), D("1"), D("1"), D("-1"), D("1")),
                )
            },
            ValueError,
            "declared plane",
        ),
        (
            {
                "penetration_bounds": (
                    ProfileLocalBounds3D(D("-2"), D("2"), D("0"), D("0"), D("-1"), D("1")),
                )
            },
            ValueError,
            "within contact",
        ),
        ({"physical_element_role": "WEB"}, TypeError, "physical_element_role"),
        ({"outside_patch_id": ""}, ValueError, "outside_patch_id"),
        ({"opposing_patch_ids": ["WEB:INSIDE"]}, TypeError, "opposing_patch_ids"),
        ({"opposing_patch_ids": ()}, ValueError, "one opposing"),
        ({"opposing_patch_ids": ("",)}, ValueError, "item"),
        (
            {
                "penetration_bounds": (_valid_bounds(), _valid_bounds()),
                "opposing_patch_ids": ("WEB:INSIDE", "WEB:INSIDE"),
            },
            ValueError,
            "unique",
        ),
    ],
)
def test_surface_definition_rejects_invalid_exact_geometry(
    changes: dict[str, object],
    error: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error, match=match):
        replace(_valid_surface(), **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "error", "match"),
    [
        ({"section_family": "ANGLE"}, TypeError, "section_family"),
        ({"geometry_factory_name": ""}, ValueError, "geometry_factory_name"),
        ({"dimension_values": []}, TypeError, "dimension_values"),
        ({"dimension_values": ()}, ValueError, "requires cross-section"),
        ({"dimension_values": (("width", D("1"), D("2")),)}, TypeError, "name/value pairs"),
        ({"dimension_values": (("", D("1")),)}, ValueError, "dimension name"),
        ({"dimension_values": (("width", 1),)}, TypeError, "Decimal"),
        ({"dimension_values": (("width", D("0")),)}, ValueError, "greater than zero"),
        (
            {"dimension_values": (("width", D("1")), ("width", D("2")))},
            ValueError,
            "unique",
        ),
        ({"member_length": D("0")}, ValueError, "greater than zero"),
        ({"section_datum_offset_y": 0}, TypeError, "offset_y"),
        ({"section_datum_offset_z": D("NaN")}, ValueError, "finite"),
    ],
)
def test_geometry_adapter_contract_rejects_invalid_recipes(
    changes: dict[str, object],
    error: type[Exception],
    match: str,
) -> None:
    adapter = ProfileSectionGeometryAdapter(
        SectionFamily.PLATE,
        "create_plate_geometry",
        (("width", D("1")),),
        D("1"),
        D("0"),
        D("0"),
    )
    with pytest.raises(error, match=match):
        replace(adapter, **changes)  # type: ignore[arg-type]
