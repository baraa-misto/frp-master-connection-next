"""Controlled Stage 3.2-R8 exact profile-wall bolt-path geometry tests."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

import frp_master_connection.domain.member_profile as subject
from frp_master_connection.domain import (
    INTERNAL_FASTENER_ACCESS_REQUIRED,
    AngleProfileDimensions,
    ChannelProfileDimensions,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ExactProfileVector3D,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PrincipalAxisFamily,
    ProfileWallBoltPathReason,
    RectangularHollowProfileDimensions,
    WideFlangeIProfileDimensions,
    resolve_profile_wall_bolt_path,
)

D = Decimal
_RADIUS = D("0.2815")
_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "stage_3_2_r8_profile_wall_bolt_path_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "2C561803503E7870E39C00428EAEE9E9236291912F94131CFC57FA8DA3A93622"


def _golden() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_GOLDEN_PATH.read_text(encoding="utf-8")))


def _profile(
    family: MemberProfileFamily,
    surface: MemberProfileSurfaceId,
    *,
    orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0,
) -> MemberProfile:
    dimensions: MemberProfileDimensions
    if family is MemberProfileFamily.CHANNEL:
        dimensions = ChannelProfileDimensions(D("8"), D("6"), D("3"), D("0.5"), D("0.5"))
    elif family is MemberProfileFamily.WIDE_FLANGE_I:
        dimensions = WideFlangeIProfileDimensions(D("8"), D("8"), D("8"), D("0.5"), D("0.75"))
    else:
        if family is not MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION:
            raise ValueError("R8 profile fixtures support Channel, W/I, or RHS.")
        dimensions = RectangularHollowProfileDimensions(D("8"), D("6"), D("4"), D("0.5"))
    return MemberProfile(
        f"r8-{family.value.lower()}-profile",
        "tee-brace",
        MemberRole.BRACE,
        family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "tee-brace"),
            PrincipalAxisFamily.X,
        ),
        orientation,
        surface,
    )


def test_r8_golden_copy_is_exact_complete_and_test_only() -> None:
    payload = _GOLDEN_PATH.read_bytes()
    golden = _golden()

    assert len(payload) == 3042
    assert sha256(payload).hexdigest().upper() == _GOLDEN_SHA256
    assert b"\r\n" not in payload
    assert golden["decimal_policy"] == "Exact decimal engineering values."
    assert [item["id"] for item in golden["benchmarks"]] == [
        "R8_G1_CHANNEL_WEB_CLEAR",
        "R8_G2_CHANNEL_WEB_FLANGE_JUNCTION_INVALID",
        "R8_G3_CHANNEL_FLANGE_OVERHANG_CLEAR",
        "R8_G4_CHANNEL_FLANGE_WEB_OVERLAP_INVALID",
        "R8_G5_RHS_POS_Y_CLEAR",
        "R8_G6_RHS_CORNER_OVERLAP_INVALID",
        "R8_G7_WIDE_FLANGE_REGRESSION",
    ]


def test_r8_g1_g2_channel_web_clear_and_junction_cases() -> None:
    profile = _profile(MemberProfileFamily.CHANNEL, MemberProfileSurfaceId.WEB_OUTER)

    clear = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("0"), D("0")),
        _RADIUS,
    )
    junction = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("0"), D("2.3")),
        _RADIUS,
    )

    assert clear.valid is True
    assert clear.opposing_patch_id == "WEB:VOID_FACING_INNER_BROAD"
    assert clear.opposing_surface_point_local == ExactProfileVector3D(D("0"), D("0.5"), D("0"))
    assert clear.penetrated_thickness == D("0.5")
    assert clear.qualifications == ()
    assert junction.valid is False
    assert junction.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE


def test_r8_g3_g4_channel_flange_overhang_and_web_overlap_cases() -> None:
    profile = _profile(MemberProfileFamily.CHANNEL, MemberProfileSurfaceId.FLANGE_POS_OUTER)

    clear = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("1.5"), D("3")),
        _RADIUS,
    )
    overlap = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("0.7"), D("3")),
        _RADIUS,
    )

    assert clear.valid is True
    assert clear.opposing_patch_id == "TOP_FLANGE:INNER_VOID_STRIP"
    assert clear.opposing_surface_point_local == ExactProfileVector3D(D("0"), D("1.5"), D("2.5"))
    assert clear.penetrated_thickness == D("0.5")
    assert overlap.valid is False
    assert overlap.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE


def test_r8_g5_g6_rhs_clear_wall_corner_and_access_qualification() -> None:
    golden = _golden()["benchmarks"]
    clear_data = next(item for item in golden if item["id"] == "R8_G5_RHS_POS_Y_CLEAR")
    corner_data = next(item for item in golden if item["id"] == "R8_G6_RHS_CORNER_OVERLAP_INVALID")
    profile = _profile(
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileSurfaceId.Y_POS_FACE,
    )

    clear = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(
            **{key: D(value) for key, value in clear_data["outer_point_conceptual"].items()}
        ),
        _RADIUS,
    )
    corner = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(
            **{key: D(value) for key, value in corner_data["outer_point_conceptual"].items()}
        ),
        D("0"),
    )

    assert clear.valid is True
    assert clear.opposing_patch_id == "SIDE_WALL_2:VOID_FACING_BROAD"
    assert clear.opposing_surface_point_local == ExactProfileVector3D(D("2"), D("1.5"), D("0"))
    assert clear.penetrated_thickness == D("0.5")
    assert clear.qualifications == (INTERNAL_FASTENER_ACCESS_REQUIRED,)
    assert corner.valid is False
    assert corner.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE
    assert corner.qualifications == (INTERNAL_FASTENER_ACCESS_REQUIRED,)


@pytest.mark.parametrize(
    ("surface", "outer", "opposing_id", "inner"),
    [
        ("Y_POS_FACE", ("0", "2", "0"), "SIDE_WALL_2:VOID_FACING_BROAD", ("0", "1.5", "0")),
        ("Y_NEG_FACE", ("0", "-2", "0"), "SIDE_WALL_1:VOID_FACING_BROAD", ("0", "-1.5", "0")),
        ("Z_POS_FACE", ("0", "0", "3"), "TOP_WALL:VOID_FACING_BROAD", ("0", "0", "2.5")),
        ("Z_NEG_FACE", ("0", "0", "-3"), "BOTTOM_WALL:VOID_FACING_BROAD", ("0", "0", "-2.5")),
    ],
)
def test_all_rhs_walls_resolve_only_the_corresponding_inner_cavity_face(
    surface: str,
    outer: tuple[str, str, str],
    opposing_id: str,
    inner: tuple[str, str, str],
) -> None:
    result = resolve_profile_wall_bolt_path(
        _profile(
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            MemberProfileSurfaceId(surface),
        ),
        ExactProfileVector3D(*(D(value) for value in outer)),
        _RADIUS,
    )

    assert result.valid is True
    assert result.opposing_patch_id == opposing_id
    assert result.opposing_surface_point_local == ExactProfileVector3D(
        *(D(value) for value in inner)
    )
    assert result.penetrated_thickness == D("0.5")


def test_r8_g7_wide_flange_clear_web_flange_and_intersection_exclusions() -> None:
    web = _profile(MemberProfileFamily.WIDE_FLANGE_I, MemberProfileSurfaceId.WEB_POS_FACE)
    flange = _profile(MemberProfileFamily.WIDE_FLANGE_I, MemberProfileSurfaceId.FLANGE_POS_OUTER)

    clear_web = resolve_profile_wall_bolt_path(
        web,
        ExactProfileVector3D(D("0"), D("0.25"), D("0")),
        _RADIUS,
    )
    junction = resolve_profile_wall_bolt_path(
        web,
        ExactProfileVector3D(D("0"), D("0.25"), D("3.1")),
        _RADIUS,
    )
    clear_flange = resolve_profile_wall_bolt_path(
        flange,
        ExactProfileVector3D(D("0"), D("2"), D("4")),
        _RADIUS,
    )
    intersection = resolve_profile_wall_bolt_path(
        flange,
        ExactProfileVector3D(D("0"), D("0"), D("4")),
        D("0"),
    )

    assert clear_web.opposing_patch_id == "WEB:NEGATIVE_TT_BROAD"
    assert clear_web.penetrated_thickness == D("0.5")
    assert junction.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE
    assert clear_flange.opposing_patch_id == "TOP_FLANGE:INNER_POSITIVE_CW_STRIP"
    assert clear_flange.penetrated_thickness == D("0.75")
    assert intersection.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE


def test_profile_wall_orientation_preserves_exact_surface_pair_and_thickness() -> None:
    profile = _profile(
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileSurfaceId.Y_POS_FACE,
        orientation=MemberProfileOrientation.ROTATION_90,
    )

    result = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("0"), D("2")),
        _RADIUS,
    )

    assert result.valid is True
    assert result.opposing_patch_id == "SIDE_WALL_2:VOID_FACING_BROAD"
    assert result.opposing_surface_point_local == ExactProfileVector3D(D("0"), D("0"), D("1.5"))
    assert result.penetrated_thickness == D("0.5")


def test_profile_wall_resolution_is_immutable_and_fails_closed_for_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(MemberProfileFamily.CHANNEL, MemberProfileSurfaceId.WEB_OUTER)
    surface = subject.resolve_profile_surface(profile)
    ambiguous = replace(
        surface,
        penetration_bounds=(surface.penetration_bounds[0], surface.penetration_bounds[0]),
        opposing_patch_ids=(surface.opposing_patch_ids[0], "WEB:ALTERNATE_INNER_BROAD"),
    )
    monkeypatch.setattr(subject, "profile_surface_registry", lambda _: (ambiguous,))

    result = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("0"), D("0"), D("0")),
        D("0"),
    )

    assert result.valid is False
    assert result.reason is ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.valid = True  # type: ignore[misc]


def test_profile_wall_resolution_rejects_outside_unsupported_and_invalid_inputs() -> None:
    profile = _profile(MemberProfileFamily.CHANNEL, MemberProfileSurfaceId.WEB_OUTER)
    point = ExactProfileVector3D(D("0"), D("0"), D("0"))
    outside = resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(D("4.1"), D("0"), D("0")),
        D("0"),
    )

    assert outside.reason is ProfileWallBoltPathReason.OUTSIDE_SELECTED_PROFILE_SURFACE
    unsupported = replace(
        profile,
        family=MemberProfileFamily.ANGLE,
        dimensions=AngleProfileDimensions(D("8"), D("6"), D("6"), D("0.5")),
        selected_surface=MemberProfileSurfaceId.LEG_Y_OUTER,
    )
    with pytest.raises(TypeError, match="profile must be a MemberProfile"):
        resolve_profile_wall_bolt_path(cast(MemberProfile, object()), point, D("0"))
    with pytest.raises(ValueError, match="requires Channel, W/I, or RHS"):
        resolve_profile_wall_bolt_path(unsupported, point, D("0"))
    with pytest.raises(TypeError, match="outer_surface_point_local"):
        resolve_profile_wall_bolt_path(profile, cast(ExactProfileVector3D, object()), D("0"))
    with pytest.raises(TypeError, match="hole_radius must be a Decimal"):
        resolve_profile_wall_bolt_path(profile, point, cast(Decimal, 0.0))
    with pytest.raises(ValueError, match="hole_radius must be nonnegative"):
        resolve_profile_wall_bolt_path(profile, point, D("-0.1"))


def test_r8_production_resolver_uses_no_golden_float_tolerance_or_rounding() -> None:
    source = Path(subject.__file__).read_text(encoding="utf-8")
    resolver = source.split("def resolve_profile_wall_bolt_path", maxsplit=1)[1].split(
        "def _half_length", maxsplit=1
    )[0]

    assert "stage_3_2_r8_profile_wall_bolt_path_golden_benchmarks_rc1.json" not in source
    for forbidden in ("float", "isclose", "epsilon", "round(", "quantize"):
        assert forbidden not in resolver
