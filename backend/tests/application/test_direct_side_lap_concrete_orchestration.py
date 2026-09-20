"""Stage 3.5B geometry, wrench, limitation, and golden-boundary tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import frp_master_connection.application.direct_side_lap_concrete_orchestration as direct_side_lap
from frp_master_connection.application import (
    design_check_direct_side_lap_concrete,
    preview_direct_side_lap_concrete,
)
from frp_master_connection.application.direct_side_lap_concrete_orchestration import (
    DirectSideLapAnchorPattern,
    DirectSideLapPreviewResult,
    DirectSideLapWallGeometry,
    SideLapFrame,
    SideLapVector,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    DemandAnalysisWarningCode,
)
from frp_master_connection.domain import (
    ExternalAnchorGeometry,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
)
from tests.beam_concrete_paired_angle_fixtures import (
    build_beam_concrete_paired_angle_request,
)
from tests.direct_side_lap_concrete_fixtures import (
    build_direct_side_lap_concrete_request,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = (
    ROOT
    / "tests"
    / "golden"
    / "stage_3_5b_direct_side_lap_angle_channel_concrete_wall_golden_benchmarks_rc1.json"
)


def _values(result: DirectSideLapPreviewResult) -> list[str]:
    assert result.visualization is not None
    return [
        item.coordinate_lsn.l.canonical_string for item in result.visualization.external_anchors
    ]


def test_controlled_golden_is_exact_and_complete() -> None:
    raw = GOLDEN.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == (
        "860767C7A1246E19524DB77FBABD8754CBBB719011C0AE05AA5102310FBC3E1F"
    )
    data = json.loads(raw)
    assert len(data["benchmarks"]) == 37
    assert data["benchmarks"][0]["id"] == "G1_DEFAULT_CHANNEL_SIDE_LAP_GEOMETRY"
    assert data["benchmarks"][-1]["id"] == "G37_FROZEN_REGRESSION_BOUNDARY"


@pytest.mark.parametrize("family", ["CHANNEL", "ANGLE"])
def test_default_profiles_resolve_finite_overlap_direct_anchor_paths_and_axes(family: str) -> None:
    result = preview_direct_side_lap_concrete(
        build_direct_side_lap_concrete_request(profile_family=family)
    )
    assert result.geometry_status == "VALID"
    assert result.assembly_status.value == "NOT_EVALUATED"
    assert result.resistance_evaluated is False
    assert result.ordinary_pass_allowed is False
    assert result.visualization is not None
    assert _values(result) == ["-203.2", "-101.6"]
    assert all(
        trace.penetrated_layers[-1] == "CONCRETE_EMBEDMENT"
        for trace in result.visualization.external_anchors
    )
    assert len(result.visualization.material_regions) == (3 if family == "CHANNEL" else 2)


@pytest.mark.parametrize(
    ("family", "expected_regions", "expected_tt"),
    [
        (
            "CHANNEL",
            (("WEB", "WEB"), ("TOP_FLANGE", "FLANGES"), ("BOTTOM_FLANGE", "FLANGES")),
            ((Decimal(0), Decimal(-1), Decimal(0)),) + ((Decimal(0), Decimal(0), Decimal(-1)),) * 2,
        ),
        (
            "ANGLE",
            (("LEG_1", "LEG_1"), ("LEG_2", "LEG_2")),
            ((Decimal(0), Decimal(-1), Decimal(0)), (Decimal(0), Decimal(0), Decimal(1))),
        ),
    ],
)
def test_r14b_material_bases_are_exact_orthonormal_physical_region_records(
    family: str,
    expected_regions: tuple[tuple[str, str], ...],
    expected_tt: tuple[tuple[Decimal, Decimal, Decimal], ...],
) -> None:
    result = preview_direct_side_lap_concrete(
        build_direct_side_lap_concrete_request(profile_family=family)
    )
    assert result.visualization is not None
    regions = result.visualization.material_regions
    assert (
        tuple((item.physical_element_id, item.material_region_id) for item in regions)
        == expected_regions
    )
    assert tuple(item.tt for item in regions) == expected_tt
    for item in regions:
        vectors = (item.lw, item.cw, item.tt)
        assert tuple(sum(value * value for value in vector) for vector in vectors) == (
            Decimal(1),
            Decimal(1),
            Decimal(1),
        )
        assert sum(a * b for a, b in zip(item.lw, item.cw, strict=True)) == 0
        assert sum(a * b for a, b in zip(item.lw, item.tt, strict=True)) == 0
        assert sum(a * b for a, b in zip(item.cw, item.tt, strict=True)) == 0


def test_lap_changes_do_not_move_anchors_and_explicit_center_value_does() -> None:
    base = build_direct_side_lap_concrete_request()
    longer = preview_direct_side_lap_concrete(replace(base, side_lap_length=Decimal("18")))
    assert longer.visualization is not None
    assert _values(longer) == ["-203.2", "-101.6"]
    centered_pattern = replace(base.anchor_pattern, centroid_distance_behind_free_end=Decimal("9"))
    centered = preview_direct_side_lap_concrete(
        replace(base, side_lap_length=Decimal("18"), anchor_pattern=centered_pattern)
    )
    assert centered.anchor_group_centroid_lsn.l.to(Unit.IN).magnitude == Decimal("-9")


def test_anchor_outside_overlap_and_excess_embedment_fail_closed() -> None:
    base = build_direct_side_lap_concrete_request()
    overlap = preview_direct_side_lap_concrete(replace(base, side_lap_length=Decimal("7")))
    assert overlap.geometry_status == "INVALID_GEOMETRY"
    assert any(
        "ANCHOR_OUTSIDE_PHYSICAL_SIDE_LAP_OVERLAP" in item
        for item in overlap.geometry_invalid_reasons
    )
    anchor = replace(
        base.external_anchor,
        specified_embedment=base.external_anchor.specified_embedment * Decimal("3"),
    )
    embedment = preview_direct_side_lap_concrete(replace(base, external_anchor=anchor))
    assert "ANCHOR_EMBEDMENT_EXCEEDS_WALL_THICKNESS" in embedment.geometry_invalid_reasons


def test_exact_wrench_translation_retains_every_generated_component() -> None:
    result = preview_direct_side_lap_concrete(
        build_direct_side_lap_concrete_request(axial_force="3", major_shear="-4", minor_shear="2")
    )
    wrench = result.anchor_group_wrench
    assert tuple(
        item.to(Unit.KIP).magnitude
        for item in (wrench.force_lsn.l, wrench.force_lsn.s, wrench.force_lsn.n)
    ) == (Decimal("3"), Decimal("-4"), Decimal("2"))
    assert any(
        item.canonical_magnitude != 0
        for item in (wrench.moment_lsn.l, wrench.moment_lsn.s, wrench.moment_lsn.n)
    )
    limitations = dict(result.limitations)
    assert limitations["DIRECT_SIDE_LAP_BOLT_AXIS_RESPONSE"] == "NOT_EVALUATED"
    assert limitations["DIRECT_SIDE_LAP_FRP_PULL_THROUGH"] == "NOT_EVALUATED"
    assert (
        limitations["WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION"] == "EXTERNAL_DESIGN_REQUIRED"
    )

    unloaded = preview_direct_side_lap_concrete(
        build_direct_side_lap_concrete_request(major_shear="0")
    )
    assert "DIRECT_SIDE_LAP_OUT_OF_PLANE_RESPONSE" not in dict(unloaded.limitations)


def test_us_si_equivalence_is_exact_for_geometry_wrench_and_fingerprints() -> None:
    us = preview_direct_side_lap_concrete(build_direct_side_lap_concrete_request())
    si = preview_direct_side_lap_concrete(build_direct_side_lap_concrete_request(unit_system="SI"))
    assert us.geometry_fingerprint == si.geometry_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert (
        us.external_anchor_handoff.handoff_fingerprint
        == si.external_anchor_handoff.handoff_fingerprint
    )
    assert us.anchor_group_wrench == si.anchor_group_wrench


@pytest.mark.parametrize(
    ("family", "surface"),
    [
        ("CHANNEL", MemberProfileSurfaceId.WEB_OUTER),
        ("ANGLE", MemberProfileSurfaceId.LEG_Y_OUTER),
        ("ANGLE", MemberProfileSurfaceId.LEG_Z_OUTER),
    ],
)
def test_g31_supported_longitudinal_frp_failure_retains_fail_precedence(
    family: str,
    surface: MemberProfileSurfaceId,
) -> None:
    request = build_direct_side_lap_concrete_request(
        profile_family=family,
        axial_force="20",
        major_shear="0",
    )
    request = replace(
        request,
        connected_profile=replace(request.connected_profile, selected_surface=surface),
    )
    preview = preview_direct_side_lap_concrete(request)
    assert preview.resistance_evaluated is False
    result = design_check_direct_side_lap_concrete(request)
    assert result.preview.resistance_evaluated is True
    assert result.supported_local_frp_failure_present is True
    assert result.assembly_status.value == "FAIL"
    assert dict(result.preview.limitations)["ANCHOR_SYSTEM_RESISTANCE"] == (
        "EXTERNAL_DESIGN_REQUIRED"
    )
    assert any(item.startswith("SUPPORTED_LOCAL_FRP_FAILURE:") for item in result.preview.warnings)


def test_supported_local_frp_pass_cannot_promote_whole_connection_to_pass() -> None:
    request = build_direct_side_lap_concrete_request(axial_force="0.1", major_shear="0")
    result = design_check_direct_side_lap_concrete(request)
    assert result.preview.resistance_evaluated is True
    assert result.supported_local_frp_failure_present is False
    assert result.assembly_status.value == "NOT_EVALUATED"
    assert result.ordinary_pass_allowed is False


def test_pattern_requires_positive_counts() -> None:
    with pytest.raises(ValueError, match="positive"):
        DirectSideLapAnchorPattern(0, 1, Decimal("4"), Decimal("4"), Decimal("6"))


def test_frame_vector_wall_and_anchor_pattern_validate_every_controlled_boundary() -> None:
    with pytest.raises(ValueError, match="right-handed"):
        replace(SideLapFrame(), n_axis=(Decimal(0), Decimal(0), Decimal(-1)))
    with pytest.raises(ValueError, match="physical dimension"):
        SideLapVector(
            PhysicalQuantity.of(1, Unit.IN),
            PhysicalQuantity.of(1, Unit.KIP),
            PhysicalQuantity.of(1, Unit.IN),
        )
    with pytest.raises(ValueError, match="wall dimensions"):
        DirectSideLapWallGeometry(Decimal(0), Decimal(48), Decimal(8))
    with pytest.raises(ValueError, match="positive non-Boolean"):
        DirectSideLapAnchorPattern(True, 1, Decimal(4), Decimal(4), Decimal(6))
    with pytest.raises(ValueError, match="pitch and gauge"):
        DirectSideLapAnchorPattern(1, 1, Decimal(0), Decimal(4), Decimal(6))
    with pytest.raises(ValueError, match="pitch and gauge"):
        DirectSideLapAnchorPattern(1, 1, Decimal(4), Decimal(0), Decimal(6))
    with pytest.raises(ValueError, match="behind wall free end"):
        DirectSideLapAnchorPattern(1, 1, Decimal(4), Decimal(4), Decimal(0))
    with pytest.raises(ValueError, match="offset must be finite"):
        DirectSideLapAnchorPattern(1, 1, Decimal(4), Decimal(4), Decimal(6), Decimal("NaN"))


def test_request_contract_rejects_every_prohibited_identity_and_action() -> None:
    base = build_direct_side_lap_concrete_request()
    with pytest.raises(ValueError, match="request_id"):
        replace(base, request_id=" ")
    with pytest.raises(ValueError, match="contract version"):
        replace(base, contract_version="future")
    with pytest.raises(ValueError, match="unit system"):
        replace(base, source_length_unit=Unit.MM)
    with pytest.raises(ValueError, match="Side-lap length"):
        replace(base, side_lap_length=Decimal(0))
    with pytest.raises(ValueError, match="member projection"):
        replace(base, member_projection_beyond_wall=Decimal(0))

    unsupported = build_beam_concrete_paired_angle_request().beam_profile
    with pytest.raises(ValueError, match="only Angle or Channel"):
        replace(base, connected_profile=unsupported)
    channel_flange = cast(
        MemberProfile,
        SimpleNamespace(
            family=MemberProfileFamily.CHANNEL,
            selected_surface=MemberProfileSurfaceId.FLANGE_POS_OUTER,
        ),
    )
    with pytest.raises(ValueError, match="CHANNEL_WEB_CONTACT_ONLY"):
        replace(base, connected_profile=channel_flange)
    angle_web = cast(
        MemberProfile,
        SimpleNamespace(
            family=MemberProfileFamily.ANGLE,
            selected_surface=MemberProfileSurfaceId.WEB_OUTER,
        ),
    )
    with pytest.raises(ValueError, match="ANGLE_SELECTED_LEG_CONTACT_REQUIRED"):
        replace(base, connected_profile=angle_web)

    with pytest.raises(ValueError, match="must be forces"):
        replace(base, axial_force=PhysicalQuantity.of(1, Unit.IN))
    moment = replace(
        base.user_moment_lsn,
        l=PhysicalQuantity.of(1, Unit.KIP_IN),
    )
    with pytest.raises(ValueError, match="USER_APPLIED_MOMENT_NOT_ALLOWED"):
        replace(base, user_moment_lsn=moment)
    wrong_embedment = cast(
        ExternalAnchorGeometry,
        SimpleNamespace(specified_embedment=PhysicalQuantity.of(1, Unit.KIP)),
    )
    with pytest.raises(ValueError, match="embedment must be a length"):
        replace(base, external_anchor=wrong_embedment)
    with pytest.raises(ValueError, match="ICE FRP material source"):
        replace(base, connected_material_source="uncontrolled")
    with pytest.raises(ValueError, match="design authority must remain external"):
        replace(base, anchor_design_authority="INTERNAL")


def test_orientation_wall_face_and_complete_hole_failures_are_distinct() -> None:
    base = build_direct_side_lap_concrete_request()
    rotated = preview_direct_side_lap_concrete(
        replace(
            base,
            connected_profile=replace(
                base.connected_profile,
                orientation=MemberProfileOrientation.ROTATION_90,
            ),
        )
    )
    assert "ANGLE_FREE_LEG_OR_CHANNEL_FLANGE_EMBEDDED_IN_CONCRETE" in (
        rotated.geometry_invalid_reasons
    )

    behind_wall = preview_direct_side_lap_concrete(
        replace(
            base,
            side_lap_length=Decimal(100),
            anchor_pattern=replace(
                base.anchor_pattern,
                centroid_distance_behind_free_end=Decimal(60),
            ),
        )
    )
    assert any(
        item.startswith("ANCHOR_CENTER_OUTSIDE_FINITE_WALL_FACE")
        for item in behind_wall.geometry_invalid_reasons
    )

    outside_profile = preview_direct_side_lap_concrete(
        replace(
            base,
            anchor_pattern=replace(base.anchor_pattern, transverse_offset=Decimal(10)),
        )
    )
    assert any(
        item.startswith("FRP_SELECTED_REGION_COMPLETE_HOLE_CONTAINMENT_INVALID")
        for item in outside_profile.geometry_invalid_reasons
    )


def test_single_anchor_and_invalid_geometry_design_remain_not_evaluated() -> None:
    base = build_direct_side_lap_concrete_request(axial_force="2", major_shear="0")
    one_anchor = replace(
        base,
        anchor_pattern=replace(base.anchor_pattern, row_count=1, anchors_per_row=1),
    )
    single = design_check_direct_side_lap_concrete(one_anchor)
    assert single.preview.resistance_evaluated is False
    assert single.assembly_status.value == "NOT_EVALUATED"
    invalid = design_check_direct_side_lap_concrete(replace(base, side_lap_length=Decimal(1)))
    assert invalid.assembly_status.value == "INVALID_GEOMETRY"
    assert invalid.preview.visualization is None


def test_unavailable_reused_demand_fails_closed_with_exact_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = SimpleNamespace(code=DemandAnalysisWarningCode.UNSUPPORTED_BOLT_GROUP_GEOMETRY)
    unavailable = SimpleNamespace(
        availability=DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED,
        warnings=(warning,),
        result_fingerprint="controlled-unavailable-demand",
    )
    monkeypatch.setattr(
        direct_side_lap,
        "calculate_eccentric_bolt_group_demand",
        lambda _input: unavailable,
    )
    result = design_check_direct_side_lap_concrete(
        build_direct_side_lap_concrete_request(axial_force="2", major_shear="0")
    )
    assert result.preview.resistance_evaluated is False
    assert result.preview.warnings == ("UNSUPPORTED_BOLT_GROUP_GEOMETRY",)


def test_canonical_export_sorts_dictionary_keys() -> None:
    assert direct_side_lap._export({"b": Decimal(2), "a": Decimal(1)}) == {
        "a": "1",
        "b": "2",
    }
