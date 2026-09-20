"""Controlled Stage 3.2-R7 exact Angle bolt-path geometry tests."""

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
    AngleLegBoltPathReason,
    AngleProfileDimensions,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ExactProfileVector3D,
    FlatPlateProfileDimensions,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PrincipalAxisFamily,
    resolve_angle_leg_bolt_path,
    resolve_profile_surface,
)

D = Decimal
_GOLDEN_PATH = (
    Path(__file__).parents[1] / "golden" / "stage_3_2_r7_angle_bolt_path_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "99E1959875E178C806EC783F521C03862C48EC25C6F8A0F306BE34F4AFC531FE"


def _golden() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_GOLDEN_PATH.read_text(encoding="utf-8")))


def _point(data: dict[str, str]) -> ExactProfileVector3D:
    return ExactProfileVector3D(D(data["x"]), D(data["y"]), D(data["z"]))


def _angle_profile(
    selected_surface: MemberProfileSurfaceId,
    *,
    orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0,
) -> MemberProfile:
    return MemberProfile(
        "tee-r7-angle-profile",
        "tee-brace",
        MemberRole.BRACE,
        MemberProfileFamily.ANGLE,
        AngleProfileDimensions(D("8"), D("6"), D("6"), D("0.5")),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "tee-brace"),
            PrincipalAxisFamily.X,
        ),
        orientation,
        selected_surface,
    )


def test_r7_golden_copy_is_exact_complete_and_test_only() -> None:
    payload = _GOLDEN_PATH.read_bytes()
    golden = _golden()

    assert len(payload) == 2114
    assert sha256(payload).hexdigest().upper() == _GOLDEN_SHA256
    assert b"\r\n" not in payload
    assert golden["decimal_policy"] == "All engineering values are exact decimal strings."
    assert [item["id"] for item in golden["benchmarks"]] == [
        "R7_G1_LEG_Y_EXPOSED_OPPOSING_FACE",
        "R7_G2_LEG_Z_EXPOSED_OPPOSING_FACE",
        "R7_G3_HEEL_OVERLAP_NOT_EXPOSED",
        "R7_G4_FREE_EDGE_OUTSIDE_INVALID",
        "R7_G5_ORIENTATION_PRESERVES_THICKNESS",
    ]


@pytest.mark.parametrize(
    "benchmark_id", ["R7_G1_LEG_Y_EXPOSED_OPPOSING_FACE", "R7_G2_LEG_Z_EXPOSED_OPPOSING_FACE"]
)
def test_r7_g1_g2_resolve_one_exposed_opposing_face_at_exact_thickness(
    benchmark_id: str,
) -> None:
    benchmark = next(item for item in _golden()["benchmarks"] if item["id"] == benchmark_id)
    profile = _angle_profile(MemberProfileSurfaceId(benchmark["selected_surface"]))

    result = resolve_angle_leg_bolt_path(profile, _point(benchmark["outer_surface_point_local"]))

    assert result.valid is benchmark["expected"]["valid"]
    assert result.reason is None
    assert result.opposing_patch_id in {
        "LEG_1:OPEN_AREA_TT_BROAD",
        "LEG_2:OPEN_AREA_TT_BROAD",
    }
    assert result.opposing_surface_point_local == _point(
        benchmark["expected"]["opposing_surface_point_local"]
    )
    assert result.penetrated_thickness == D(benchmark["expected"]["penetrated_thickness"])
    assert benchmark["expected"]["opposing_face_count"] == 1


@pytest.mark.parametrize(
    ("benchmark_id", "reason"),
    [
        (
            "R7_G3_HEEL_OVERLAP_NOT_EXPOSED",
            AngleLegBoltPathReason.NO_FINITE_EXPOSED_OPPOSING_BROAD_FACE,
        ),
        (
            "R7_G4_FREE_EDGE_OUTSIDE_INVALID",
            AngleLegBoltPathReason.OUTSIDE_SELECTED_LEG_SURFACE,
        ),
    ],
)
def test_r7_g3_g4_keep_heel_and_free_edge_paths_invalid(
    benchmark_id: str,
    reason: AngleLegBoltPathReason,
) -> None:
    benchmark = next(item for item in _golden()["benchmarks"] if item["id"] == benchmark_id)
    result = resolve_angle_leg_bolt_path(
        _angle_profile(MemberProfileSurfaceId(benchmark["selected_surface"])),
        _point(benchmark["outer_surface_point_local"]),
    )

    assert result.valid is False
    assert result.reason is reason
    assert result.opposing_patch_id is None
    assert result.opposing_surface_point_local is None
    assert result.penetrated_thickness is None


def test_r7_g5_orientation_rotates_pair_without_changing_physical_thickness() -> None:
    profile = _angle_profile(
        MemberProfileSurfaceId.LEG_Y_OUTER,
        orientation=MemberProfileOrientation.ROTATION_90,
    )
    result = resolve_angle_leg_bolt_path(
        profile,
        ExactProfileVector3D(D("2"), D("0"), D("2")),
    )
    surface = resolve_profile_surface(profile)

    assert result.valid is True
    assert result.selected_surface is MemberProfileSurfaceId.LEG_Y_OUTER
    assert result.opposing_patch_id == "LEG_1:OPEN_AREA_TT_BROAD"
    assert result.opposing_surface_point_local == ExactProfileVector3D(D("2"), D("-0.5"), D("2"))
    assert result.penetrated_thickness == D("0.5") == surface.layer_thickness
    assert surface.plane_axis is PrincipalAxisFamily.Y


def test_angle_resolution_is_immutable_slotted_and_fail_closed_for_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _angle_profile(MemberProfileSurfaceId.LEG_Y_OUTER)
    surface = resolve_profile_surface(profile)
    ambiguous = replace(
        surface,
        penetration_bounds=(surface.penetration_bounds[0], surface.penetration_bounds[0]),
        opposing_patch_ids=(
            surface.opposing_patch_ids[0],
            "LEG_1:ALTERNATE_OPEN_AREA_TT_BROAD",
        ),
    )
    monkeypatch.setattr(subject, "profile_surface_registry", lambda _: (ambiguous,))

    result = resolve_angle_leg_bolt_path(
        profile,
        ExactProfileVector3D(D("2"), D("2"), D("0")),
    )

    assert result.reason is AngleLegBoltPathReason.AMBIGUOUS_FINITE_EXPOSED_OPPOSING_BROAD_FACE
    assert result.valid is False
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.valid = True  # type: ignore[misc]


def test_angle_resolution_rejects_wrong_profile_and_input_types() -> None:
    profile = _angle_profile(MemberProfileSurfaceId.LEG_Y_OUTER)
    point = ExactProfileVector3D(D("2"), D("2"), D("0"))

    with pytest.raises(TypeError, match="profile must be a MemberProfile"):
        resolve_angle_leg_bolt_path(cast(MemberProfile, object()), point)
    with pytest.raises(ValueError, match="requires an Angle profile"):
        resolve_angle_leg_bolt_path(
            replace(
                profile,
                family=MemberProfileFamily.FLAT_PLATE,
                dimensions=FlatPlateProfileDimensions(D("8"), D("6"), D("0.5")),
                selected_surface=MemberProfileSurfaceId.FACE_POS,
            ),
            point,
        )
    with pytest.raises(TypeError, match="outer_surface_point_local"):
        resolve_angle_leg_bolt_path(profile, cast(ExactProfileVector3D, object()))


def test_r7_production_module_does_not_read_controlled_golden() -> None:
    source = Path(subject.__file__).read_text(encoding="utf-8")

    assert "stage_3_2_r7_angle_bolt_path_golden_benchmarks_rc1.json" not in source
    assert (
        "json"
        not in source.split("def resolve_angle_leg_bolt_path", maxsplit=1)[1].split(
            "def _half_length", maxsplit=1
        )[0]
    )
