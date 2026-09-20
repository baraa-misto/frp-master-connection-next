"""Controlled Stage 3.3C3 paired profile/support expansion regressions."""

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

from frp_master_connection.api.paired_clip_angle_mapping import (
    map_paired_clip_angle_request,
)
from frp_master_connection.api.paired_clip_angle_schemas import (
    PairedClipAngleConnectorRequestDTO,
)
from frp_master_connection.application import (
    PairedClipAngleDesignStatus,
    PairedClipAnglePreviewResult,
    preview_paired_clip_angle,
)
from frp_master_connection.application.clip_angle_orchestration import (
    _placed_connected_profile,
)
from frp_master_connection.application.paired_clip_angle_orchestration import (
    PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION,
    _placement_with_full_through_paths,
    _single_request,
)
from frp_master_connection.application.shared_support_integration import (
    IntegratedFullThroughBoltTrace,
    build_integrated_full_through_bolt,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ClipAngleHand,
    FullThroughHardwareLocation,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    PhysicalBoltPathSegmentKind,
    RoundHollowProfileDimensions,
)
from frp_master_connection.geometry import PlacedComponentGeometry3D
from tests.paired_clip_angle_fixtures import (
    build_paired_clip_angle_c3_payload,
    build_paired_clip_angle_payload,
    build_paired_clip_angle_request,
)

ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = (
    ROOT / "backend/tests/golden/"
    "stage_3_3c3_paired_clip_angle_profile_support_expansion_golden_benchmarks_rc1.json"
)
CONTROLLED_ARTIFACTS = (
    (
        ROOT / "docs/engineering/"
        "STAGE_3_3C3_PAIRED_CLIP_ANGLE_PROFILE_SUPPORT_EXPANSION_"
        "ENGINEERING_SPECIFICATION_RC1.md",
        "86E6A20040250EF787290569D54FB1CDB57F073599CC1E9F8C435F0E03A4F0F3",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        GOLDEN_PATH,
        "DFBA62165C09DCC784A8EDD791BF9AD61BDEBE9AFC541CE7B3B06C8287FE1A3C",
        None,
    ),
    (
        ROOT / "docs/qa/"
        "STAGE_3_3C3_PAIRED_CLIP_ANGLE_PROFILE_SUPPORT_EXPANSION_"
        "AUTHORITY_LEDGER_RC1.md",
        "A0DD2221D18525496AEE98B9069F600C912BF2C9478CE4DFB2B7A42C6C3D83AE",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _length(value: str, unit_system: str) -> dict[str, str]:
    amount = Decimal(value) * (Decimal("25.4") if unit_system == "SI" else Decimal(1))
    return {"value": str(amount), "unit": "mm" if unit_system == "SI" else "in"}


def _payload(
    connected: str = "ANGLE",
    support: str = "W_COLUMN_FLANGE",
    *,
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    value = build_paired_clip_angle_c3_payload(
        connected_profile_family=connected,
        support_target=support,
        unit_system=unit_system,
    )
    profile = value["support_profile"]
    if support in {"W_COLUMN_FLANGE", "W_BEAM_FLANGE"}:
        profile["flange_width"] = _length("20", unit_system)
    elif support in {"W_COLUMN_WEB", "CHANNEL_COLUMN_WEB"}:
        profile["depth"] = _length("20", unit_system)
    elif support == "ANGLE_COLUMN_LEG":
        profile["leg_y"] = _length("20", unit_system)
        profile["leg_z"] = _length("20", unit_system)
    elif support in {
        "RECTANGULAR_HOLLOW_COLUMN_WALL",
        "SOLID_RECTANGULAR_COLUMN_FACE",
    }:
        profile["width"] = _length("20", unit_system)
    return value


def _preview(
    connected: str = "ANGLE",
    support: str = "W_COLUMN_FLANGE",
    *,
    unit_system: str = "US_CUSTOMARY",
) -> PairedClipAnglePreviewResult:
    dto = PairedClipAngleConnectorRequestDTO.model_validate(
        _payload(connected, support, unit_system=unit_system)
    )
    return preview_paired_clip_angle(map_paired_clip_angle_request(dto))


def _paths(
    result: PairedClipAnglePreviewResult, prefix: str
) -> tuple[IntegratedFullThroughBoltTrace, ...]:
    paths = result.rectangular_full_through_paths
    return tuple(item for item in paths if item.path.bolt_id.startswith(prefix))


def test_c3_controlled_artifacts_are_exact_and_golden_has_g1_through_g20() -> None:
    for path, expected_hash, sentinel in CONTROLLED_ARTIFACTS:
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest().upper() == expected_hash
        if sentinel is not None:
            assert content.rstrip().endswith(sentinel)
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert [item["id"].split("_", 2)[:2] for item in golden["benchmarks"]] == [
        ["C3", f"G{index}"] for index in range(1, 21)
    ]


def test_c3_strict_contract_exposes_six_profiles_and_shared_support_only() -> None:
    for family in (
        "FLAT_PLATE",
        "WIDE_FLANGE_I",
        "CHANNEL",
        "ANGLE",
        "RECTANGULAR_HOLLOW_SECTION",
        "SOLID_RECTANGULAR_SECTION",
    ):
        PairedClipAngleConnectorRequestDTO.model_validate(_payload(family))
    stale = _payload()
    stale["support_role"] = "W_COLUMN_FLANGE"
    with pytest.raises(ValidationError, match="stale legacy"):
        PairedClipAngleConnectorRequestDTO.model_validate(stale)
    missing = _payload()
    missing.pop("support_profile")
    with pytest.raises(ValidationError, match="requires support_target_id"):
        PairedClipAngleConnectorRequestDTO.model_validate(missing)


def test_c3_g1_g3_connected_angle_path_is_current_without_equal_sharing() -> None:
    result = _preview()
    assert result.geometry_status.value == "VALID"
    assert result.assembly_status is PairedClipAngleDesignStatus.NOT_EVALUATED
    assert result.symmetry_proof.equal_sharing_eligible is False
    assert result.branch_actions == ()
    assert result.common_member_group.placement.bolts
    assert all(
        item.layer_ids
        == (
            "POSITIVE_CLIP_CONNECTED_LEG",
            "MEMBER_ANGLE_SELECTED_LEG",
            "NEGATIVE_CLIP_CONNECTED_LEG",
        )
        for item in result.common_member_group.placement.bolts
    )


def test_c3_g2_angle_heel_collision_is_invalid_without_auto_reposition() -> None:
    payload = _payload()
    payload["common_member_layout"]["heel_edge_distance"] = _length("0.1", "US_CUSTOMARY")
    request = map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(payload)
    )
    result = preview_paired_clip_angle(request)
    assert result.geometry_status.value == "INVALID_GEOMETRY"
    assert "COMMON_MEMBER_THROUGH_BOLT_GROUP:COMPLETE_HOLE_CONTAINMENT_INVALID" in (
        result.geometry_invalid_reasons
    )
    assert request.common_member_layout.heel_edge_distance == Decimal("0.1")


@pytest.mark.parametrize(
    ("family", "identities", "lengths"),
    [
        (
            "RECTANGULAR_HOLLOW_SECTION",
            (
                "POSITIVE_CLIP_CONNECTED_LEG",
                "RHS_NEAR_WALL",
                "RHS_CAVITY",
                "RHS_FAR_WALL",
                "NEGATIVE_CLIP_CONNECTED_LEG",
            ),
            ("0.5", "0.5", "5", "0.5", "0.5"),
        ),
        (
            "SOLID_RECTANGULAR_SECTION",
            (
                "POSITIVE_CLIP_CONNECTED_LEG",
                "SOLID_RECTANGULAR_SECTION",
                "NEGATIVE_CLIP_CONNECTED_LEG",
            ),
            ("0.5", "6", "0.5"),
        ),
    ],
)
def test_c3_g4_g5_connected_rectangular_common_paths(
    family: str,
    identities: tuple[str, ...],
    lengths: tuple[str, ...],
) -> None:
    result = _preview(family)
    assert result.geometry_status.value == "VALID"
    paths = _paths(result, "COMMON")
    assert len(paths) == len(result.common_member_group.placement.bolts)
    for trace in paths:
        assert tuple(item.identity for item in trace.path.segments) == identities
        assert tuple(item.length for item in trace.path.segments) == tuple(
            Decimal(item) for item in lengths
        )
        assert trace.hardware.physical_bolt_count == 1
        assert trace.hardware.continuous_shank_count == 1
        assert trace.hardware.internal_hardware_count == 0
        assert trace.hardware.shank_length == Decimal(7)


@pytest.mark.parametrize(
    ("target", "member_identity"),
    [
        ("W_COLUMN_WEB", "W_WEB"),
        ("CHANNEL_COLUMN_WEB", "CHANNEL_WEB"),
        ("ANGLE_COLUMN_LEG", "ANGLE_SELECTED_LEG"),
    ],
)
def test_c3_g6_g8_open_support_groups_are_distinct_and_contained(
    target: str,
    member_identity: str,
) -> None:
    result = _preview("ANGLE", target)
    assert result.geometry_status.value == "VALID"
    positive = result.positive_support_group.placement
    negative = result.negative_support_group.placement
    assert positive.bolt_group_id != negative.bolt_group_id
    assert {item.global_center for item in positive.bolts}.isdisjoint(
        {item.global_center for item in negative.bolts}
    )
    assert all(
        item.layer_ids == ("POSITIVE_CLIP_SUPPORT_LEG", member_identity) for item in positive.bolts
    )
    assert all(
        item.layer_ids == ("NEGATIVE_CLIP_SUPPORT_LEG", member_identity) for item in negative.bolts
    )


@pytest.mark.parametrize(
    ("target", "core_identity", "free_span"),
    [
        ("RECTANGULAR_HOLLOW_COLUMN_WALL", "RHS_CAVITY", True),
        ("SOLID_RECTANGULAR_COLUMN_FACE", "SOLID_RECTANGULAR_SECTION", False),
    ],
)
def test_c3_g9_g10_support_rectangular_groups_are_two_external_paths(
    target: str,
    core_identity: str,
    free_span: bool,
) -> None:
    result = _preview("ANGLE", target)
    assert result.geometry_status.value == "VALID"
    positive = _paths(result, "POS-SUPPORT")
    negative = _paths(result, "NEG-SUPPORT")
    assert len(positive) == len(result.positive_support_group.placement.bolts)
    assert len(negative) == len(result.negative_support_group.placement.bolts)
    assert {item.path.bolt_id for item in positive}.isdisjoint(
        {item.path.bolt_id for item in negative}
    )
    for trace in (*positive, *negative):
        assert core_identity in {item.identity for item in trace.path.segments}
        assert bool(trace.path.free_shank_spans) is free_span
        assert trace.hardware.internal_hardware_count == 0


def test_c3_g11_g13_endpoint_hardware_and_solid_identity() -> None:
    rhs = _preview("RECTANGULAR_HOLLOW_SECTION")
    common = _paths(rhs, "COMMON")
    assert len({item.path.bolt_id for item in common}) == len(common)
    assert all(item.physical_start_point.x > item.physical_end_point.x for item in common)
    assert all(
        item.hardware.head_location is FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE
        and item.hardware.nut_location is FullThroughHardwareLocation.EXTERIOR_FAR_SIDE
        for item in common
    )
    srs = _preview("SOLID_RECTANGULAR_SECTION")
    assert all(
        not item.path.free_shank_spans
        and any(
            segment.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER
            and segment.identity == "SOLID_RECTANGULAR_SECTION"
            for segment in item.path.segments
        )
        for item in _paths(srs, "COMMON")
    )


@pytest.mark.parametrize(
    ("connected", "support"),
    [
        ("ANGLE", "W_COLUMN_FLANGE"),
        ("RECTANGULAR_HOLLOW_SECTION", "W_COLUMN_FLANGE"),
        ("SOLID_RECTANGULAR_SECTION", "W_COLUMN_FLANGE"),
        ("ANGLE", "RECTANGULAR_HOLLOW_COLUMN_WALL"),
        ("ANGLE", "SOLID_RECTANGULAR_COLUMN_FACE"),
    ],
)
def test_c3_g14_us_si_geometry_paths_and_fingerprints_are_exact(
    connected: str,
    support: str,
) -> None:
    us = _preview(connected, support)
    si = _preview(connected, support, unit_system="SI")
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.connector_geometry_fingerprint == si.connector_geometry_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert [item.path_fingerprint for item in us.rectangular_full_through_paths] == [
        item.path_fingerprint for item in si.rectangular_full_through_paths
    ]


def test_c3_g15_legacy_stage_b_fingerprints_remain_exact() -> None:
    legacy = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert legacy.canonical_input_fingerprint == (
        "1a1967aa0ed47593b5c33fbdef82ae0a4e18dc082500f8d794962b831fd16b5e"
    )
    assert legacy.engineering_fingerprint == (
        "67fbf413b78f57f73eebb63c467d12c9e299f3edf603edc7f51eeab6a68e1db8"
    )


def test_c3_g16_unsupported_distribution_keeps_current_geometry() -> None:
    payload = _payload("ANGLE", "CHANNEL_COLUMN_WEB")
    result = preview_paired_clip_angle(
        map_paired_clip_angle_request(PairedClipAngleConnectorRequestDTO.model_validate(payload))
    )
    assert result.geometry_status.value == "VALID"
    assert result.assembly_status is PairedClipAngleDesignStatus.NOT_EVALUATED
    assert result.symmetry_proof.equal_sharing_eligible is False
    assert result.positive_support_group.demand is None


@pytest.mark.parametrize(
    "family",
    ["ANGLE", "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION"],
)
def test_c3_g17_g18_trim_preserves_profile_topology_and_recomputes_endpoints(
    family: str,
) -> None:
    payload = _payload(family)
    request = map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(payload)
    )
    request = replace(
        request,
        connector_dimensions=replace(
            request.connector_dimensions,
            connector_length=Decimal(6),
        ),
        common_member_layout=replace(
            request.common_member_layout,
            heel_edge_distance=Decimal(1),
        ),
        connected_member_inclination_degrees=Decimal(25),
        connected_member_end_trim_enabled=True,
        connected_member_end_clearance=PhysicalQuantity.of("0.5", Unit.IN),
    )
    result = preview_paired_clip_angle(request)
    assert result.geometry_status.value == "VALID"
    assert result.trim.geometry_valid is True
    assert result.visualization is not None
    assert result.visualization.meshes
    if family is MemberProfileFamily.ANGLE.value:
        assert len(result.visualization.meshes) == 2
    elif family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION.value:
        assert len(result.visualization.meshes) == 4
        assert all(
            item.physical_start_point != item.physical_end_point
            for item in _paths(result, "COMMON")
        )
    else:
        assert len(result.visualization.meshes) == 1


def test_c3_g19_has_no_duplicate_common_or_support_bolts() -> None:
    result = _preview(
        "RECTANGULAR_HOLLOW_SECTION",
        "RECTANGULAR_HOLLOW_COLUMN_WALL",
    )
    all_ids = [
        item.bolt_id
        for group in (
            result.common_member_group,
            result.positive_support_group,
            result.negative_support_group,
        )
        for item in group.placement.bolts
    ]
    assert len(all_ids) == len(set(all_ids))
    path_ids = [item.path.bolt_id for item in result.rectangular_full_through_paths]
    assert sorted(path_ids) == sorted(all_ids)


def test_c3_limitations_are_design_states_not_geometry_errors() -> None:
    rhs = _preview("RECTANGULAR_HOLLOW_SECTION")
    assert rhs.geometry_status.value == "VALID"
    assert set(rhs.limitations) == {
        "RHS_LOCAL_WALL_RESPONSE",
        "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
    }
    assert rhs.assembly_status is PairedClipAngleDesignStatus.NOT_EVALUATED
    srs = _preview("SOLID_RECTANGULAR_SECTION")
    assert srs.limitations == ("SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY",)


def test_c3_transport_rejects_unknown_version_and_mismatched_support() -> None:
    wrong_version = _payload()
    wrong_version["orchestration_contract_version"] = "3.3C3-DRAFT"
    with pytest.raises(ValidationError, match=r"3\.3C3-RC1"):
        PairedClipAngleConnectorRequestDTO.model_validate(wrong_version)
    mismatch = deepcopy(_payload())
    mismatch["support_target_id"] = "CHANNEL_COLUMN_WEB"
    with pytest.raises(ValidationError, match="inconsistent"):
        PairedClipAngleConnectorRequestDTO.model_validate(mismatch)


def test_c3_transport_and_domain_contracts_reject_mixed_legacy_shapes() -> None:
    legacy_payload = build_paired_clip_angle_payload()

    missing = deepcopy(legacy_payload)
    missing.pop("support_role")
    with pytest.raises(ValidationError, match="require W-flange support fields"):
        PairedClipAngleConnectorRequestDTO.model_validate(missing)

    mixed = deepcopy(legacy_payload)
    c3 = _payload()
    mixed["support_target_id"] = c3["support_target_id"]
    mixed["support_profile"] = c3["support_profile"]
    with pytest.raises(ValidationError, match="forbid C3 support fields"):
        PairedClipAngleConnectorRequestDTO.model_validate(mixed)

    disallowed = deepcopy(legacy_payload)
    disallowed["connected_member_profile"] = c3["connected_member_profile"]
    with pytest.raises(ValidationError, match="Flat Plate, W/I Web, or Channel Web"):
        PairedClipAngleConnectorRequestDTO.model_validate(disallowed)

    legacy = build_paired_clip_angle_request()
    c3_request = map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(c3)
    )
    with pytest.raises(ValueError, match="forbid C3 support fields"):
        replace(
            legacy,
            support_target_id=c3_request.support_target_id,
            support_profile=c3_request.support_profile,
        )
    with pytest.raises(ValueError, match="requires one shared support"):
        replace(
            legacy,
            orchestration_contract_version=PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION,
        )
    round_profile = replace(
        legacy.connected_member_profile,
        family=MemberProfileFamily.ROUND_HOLLOW_SECTION,
        dimensions=RoundHollowProfileDimensions(Decimal(12), Decimal(4), Decimal("0.25")),
        selected_surface=None,
    )
    with pytest.raises(ValueError, match="six authorized planar connected profiles"):
        replace(
            legacy,
            orchestration_contract_version=PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION,
            connected_member_profile=round_profile,
            support_target_id=c3_request.support_target_id,
            support_profile=c3_request.support_profile,
        )


def test_c3_full_through_defensive_contracts_and_invalid_containment() -> None:
    request = map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(_payload("RECTANGULAR_HOLLOW_SECTION"))
    )
    result = preview_paired_clip_angle(request)
    with pytest.raises(ValueError, match="exactly one path"):
        _placement_with_full_through_paths(
            result.common_member_group.placement,
            result.rectangular_full_through_paths[:1],
            Unit.IN,
        )

    profile = request.connected_member_profile
    assert profile.selected_surface is MemberProfileSurfaceId.Z_POS_FACE
    with pytest.raises(TypeError, match="requires placed_profile"):
        build_integrated_full_through_bolt(
            profile,
            selected_surface=profile.selected_surface,
            bolt_id="C3-DEFENSIVE",
            local_uv=(Decimal(0), Decimal(0)),
            hole_radius=Decimal("0.25"),
            connector_identity="POSITIVE_CLIP_CONNECTED_LEG",
            connector_thickness=Decimal("0.5"),
            connector_material_region_id="POSITIVE_CLIP_CONNECTED_LEG",
            rectangular_material_region_id="RHS_PROFILE",
            source_length_unit=Unit.IN,
            placed_profile=cast(PlacedComponentGeometry3D, object()),
        )
    placed = _placed_connected_profile(_single_request(request, ClipAngleHand.POSITIVE_S_SIDE))
    with pytest.raises(ValueError, match="far connector layer requires"):
        build_integrated_full_through_bolt(
            profile,
            selected_surface=profile.selected_surface,
            bolt_id="C3-DEFENSIVE",
            local_uv=(Decimal(0), Decimal(0)),
            hole_radius=Decimal("0.25"),
            connector_identity="POSITIVE_CLIP_CONNECTED_LEG",
            connector_thickness=Decimal("0.5"),
            connector_material_region_id="POSITIVE_CLIP_CONNECTED_LEG",
            rectangular_material_region_id="RHS_PROFILE",
            source_length_unit=Unit.IN,
            placed_profile=placed,
            far_connector_identity="NEGATIVE_CLIP_CONNECTED_LEG",
        )

    rectangular_invalid = _payload("RECTANGULAR_HOLLOW_SECTION")
    rectangular_invalid["common_member_layout"]["gauge"] = _length("30", "US_CUSTOMARY")
    invalid_result = preview_paired_clip_angle(
        map_paired_clip_angle_request(
            PairedClipAngleConnectorRequestDTO.model_validate(rectangular_invalid)
        )
    )
    assert "RECTANGULAR_OPPOSING_FACE_HOLE_CONTAINMENT_INVALID" in (
        invalid_result.geometry_invalid_reasons
    )

    open_support_invalid = build_paired_clip_angle_c3_payload(support_target="ANGLE_COLUMN_LEG")
    open_support_invalid["mirrored_support_layout"]["gauge"] = _length("30", "US_CUSTOMARY")
    open_result = preview_paired_clip_angle(
        map_paired_clip_angle_request(
            PairedClipAngleConnectorRequestDTO.model_validate(open_support_invalid)
        )
    )
    assert "SUPPORT_PROFILE_SELECTED_SURFACE_HOLE_CONTAINMENT_INVALID" in (
        open_result.geometry_invalid_reasons
    )
