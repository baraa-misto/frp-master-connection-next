"""Stage 3.3C2 Tee/Single support and rectangular full-through integration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import frp_master_connection.application.tee_orchestration as tee_module
from frp_master_connection.api.clip_angle_mapping import map_clip_angle_request
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.api.shared_support_mapping import _length
from frp_master_connection.api.tee_mapping import map_tee_connector_request
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    ClipAnglePreviewResult,
    TeeConnectorPreviewResult,
    preview_clip_angle,
    preview_paired_clip_angle,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.application.shared_support_integration import (
    build_integrated_full_through_bolt,
)
from frp_master_connection.application.tee_orchestration import (
    _canonical,
    _expanded_rectangular_bolt_points,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileSurfaceId,
    PhysicalBoltPathSegmentKind,
    SharedSupportSelection,
    SharedSupportTargetId,
    shared_support_target_registry,
)
from tests.clip_angle_fixtures import (
    build_clip_angle_c2_payload,
    build_clip_angle_payload,
    build_clip_angle_request,
)
from tests.paired_clip_angle_fixtures import build_paired_clip_angle_request
from tests.tee_fixtures import (
    build_tee_c2_payload,
    build_tee_c2_workspace_rhs_payload,
    build_tee_r2_payload,
    build_tee_r2_request,
    build_tee_r8_profile_wall_request,
)

ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = (
    ROOT / "backend/tests/golden/"
    "stage_3_3c2_tee_single_clip_support_rectangular_expansion_golden_benchmarks_rc1.json"
)
CONTROLLED_ARTIFACTS = (
    (
        ROOT / "docs/engineering/"
        "STAGE_3_3C2_TEE_SINGLE_CLIP_SUPPORT_RECTANGULAR_EXPANSION_"
        "ENGINEERING_SPECIFICATION_RC1.md",
        "530CCB7A3743DE429AC0CF663D81E528660C73D0A82352D826EE6B67BCC8BC3B",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        GOLDEN_PATH,
        "CD365FAF66AC004218DABD825C3A354BFD756F604D0583EFD309A93547B367BC",
        None,
    ),
    (
        ROOT / "docs/qa/"
        "STAGE_3_3C2_TEE_SINGLE_CLIP_SUPPORT_RECTANGULAR_EXPANSION_"
        "AUTHORITY_LEDGER_RC1.md",
        "F958ADD9DB039B9F0699D7716CD36D1A9B1DDDCDC7CFEF7FF502A7E2CAE7CF87",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)
TARGETS = tuple(item.value for item in SharedSupportTargetId)
OPEN_TARGET_ELEMENTS = {
    "W_COLUMN_WEB": "WEB",
    "CHANNEL_COLUMN_WEB": "WEB",
    "ANGLE_COLUMN_LEG": "LEG_1",
}
LIMITATIONS = {
    "RECTANGULAR_HOLLOW_COLUMN_WALL": {
        "RHS_LOCAL_WALL_RESPONSE",
        "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
    },
    "SOLID_RECTANGULAR_COLUMN_FACE": {
        "SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY",
    },
}


def _golden() -> dict[str, Any]:
    value = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _case(case_id: str) -> dict[str, Any]:
    matches = tuple(item for item in _golden()["benchmarks"] if item["id"] == case_id)
    assert len(matches) == 1
    return cast(dict[str, Any], matches[0])


def _tee(payload: dict[str, Any]) -> TeeConnectorPreviewResult:
    return preview_tee_connector(
        map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))
    )


def _clip(payload: dict[str, Any]) -> ClipAnglePreviewResult:
    return preview_clip_angle(
        map_clip_angle_request(ClipAngleConnectorRequestDTO.model_validate(payload))
    )


def _valid_rectangular_support_payload(
    family: str,
    target: str,
    *,
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    payload = (
        build_tee_c2_payload(support_target=target, unit_system=unit_system)
        if family == "TEE"
        else build_clip_angle_c2_payload(support_target=target, unit_system=unit_system)
    )
    if target == "RECTANGULAR_HOLLOW_COLUMN_WALL":
        payload["support_profile"]["width"] = {
            "value": "10" if unit_system == "US_CUSTOMARY" else "254.0",
            "unit": "in" if unit_system == "US_CUSTOMARY" else "mm",
        }
    return payload


def _segments(
    result: TeeConnectorPreviewResult | ClipAnglePreviewResult,
) -> tuple[tuple[str, str, Decimal], ...]:
    trace = result.rectangular_full_through_paths[0]
    return tuple((item.kind.value, item.identity, item.length) for item in trace.path.segments)


def test_controlled_artifacts_are_byte_exact_and_golden_parses_through_g18() -> None:
    for path, expected_hash, sentinel in CONTROLLED_ARTIFACTS:
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest().upper() == expected_hash
        if sentinel is not None:
            assert content.rstrip().endswith(sentinel)
    assert [item["id"] for item in _golden()["benchmarks"]] == [
        f"C2_G{index}_{suffix}"
        for index, suffix in enumerate(
            (
                "TEE_W_COLUMN_WEB",
                "TEE_CHANNEL_COLUMN_WEB",
                "TEE_ANGLE_COLUMN_LEG",
                "TEE_RHS_COLUMN_FULL_THROUGH",
                "TEE_SRS_COLUMN_FULL_THROUGH",
                "SINGLE_W_COLUMN_WEB",
                "SINGLE_CHANNEL_COLUMN_WEB",
                "SINGLE_ANGLE_COLUMN_LEG",
                "SINGLE_RHS_COLUMN_FULL_THROUGH",
                "SINGLE_SRS_COLUMN_FULL_THROUGH",
                "TEE_CONNECTED_RHS_SUCCESSOR",
                "SINGLE_CONNECTED_RHS_SUCCESSOR",
                "TEE_CONNECTED_SRS",
                "SINGLE_CONNECTED_SRS",
                "RHS_HARDWARE_AND_CONTAINMENT",
                "US_SI_EQUIVALENCE",
                "LEGACY_NON_RHS_INVARIANCE",
                "RECTANGULAR_LIMITATIONS_ARE_NOT_GEOMETRY_ERRORS",
            ),
            start=1,
        )
    ]


def test_one_shared_support_contract_has_exactly_seven_targets_and_no_w_beam_web() -> None:
    registry = shared_support_target_registry()
    assert registry == tuple(shared_support_target_registry())
    assert tuple(item.target_id.value for item in registry) == TARGETS
    assert len(registry) == 7
    assert "W_BEAM_WEB" not in TARGETS


@pytest.mark.parametrize("target", TARGETS)
def test_tee_and_single_angle_accept_the_complete_shared_support_matrix(target: str) -> None:
    tee_payload = build_tee_c2_payload(support_target=target)
    clip_payload = build_clip_angle_c2_payload(support_target=target)
    if target == "RECTANGULAR_HOLLOW_COLUMN_WALL":
        tee_payload = _valid_rectangular_support_payload("TEE", target)
        clip_payload = _valid_rectangular_support_payload("SINGLE_CLIP_ANGLE", target)
    tee = _tee(tee_payload)
    clip = _clip(clip_payload)
    assert tee.assembly_status.value == "NOT_EVALUATED"
    assert clip.geometry_status.value == "VALID"
    assert tee.support_target_id.value == target
    assert clip.support_target_id.value == target
    assert tee.visualization is not None
    assert clip.visualization is not None
    assert tee.visualization.support_profile.target_id.value == target
    assert clip.visualization.support_profile.target_id.value == target


@pytest.mark.parametrize("target", tuple(OPEN_TARGET_ELEMENTS))
def test_open_support_paths_use_actual_web_or_angle_leg_geometry(target: str) -> None:
    request = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(build_tee_c2_payload(support_target=target))
    )
    resolved = resolve_tee_connector_request(request)
    support_layers = resolved.context.resolved_bolt_groups[1].paths[0].layers
    assert [item.definition.physical_element_id for item in support_layers] == [
        "FLANGE",
        OPEN_TARGET_ELEMENTS[target],
    ]
    clip = _clip(build_clip_angle_c2_payload(support_target=target))
    assert clip.interface_b.placement.bolts[0].layer_ids == (
        "single-clip-angle-connector:SUPPORT_LEG",
        {
            "W_COLUMN_WEB": "W_WEB",
            "CHANNEL_COLUMN_WEB": "CHANNEL_WEB",
            "ANGLE_COLUMN_LEG": "ANGLE_SELECTED_LEG",
        }[target],
    )


@pytest.mark.parametrize(
    ("family", "target", "case_id"),
    [
        ("TEE", "RECTANGULAR_HOLLOW_COLUMN_WALL", "C2_G4_TEE_RHS_COLUMN_FULL_THROUGH"),
        ("TEE", "SOLID_RECTANGULAR_COLUMN_FACE", "C2_G5_TEE_SRS_COLUMN_FULL_THROUGH"),
        (
            "SINGLE_CLIP_ANGLE",
            "RECTANGULAR_HOLLOW_COLUMN_WALL",
            "C2_G9_SINGLE_RHS_COLUMN_FULL_THROUGH",
        ),
        (
            "SINGLE_CLIP_ANGLE",
            "SOLID_RECTANGULAR_COLUMN_FACE",
            "C2_G10_SINGLE_SRS_COLUMN_FULL_THROUGH",
        ),
    ],
)
def test_rectangular_support_paths_match_controlled_golden(
    family: str,
    target: str,
    case_id: str,
) -> None:
    payload = _valid_rectangular_support_payload(family, target)
    result = _tee(payload) if family == "TEE" else _clip(payload)
    expected = _case(case_id)["expected"]["segments"]
    assert _segments(result) == tuple(
        (item["kind"], item["identity"], Decimal(item["length_in"])) for item in expected
    )
    assert len(result.rectangular_full_through_paths) == 4
    for trace in result.rectangular_full_through_paths:
        assert trace.hardware.physical_bolt_count == 1
        assert trace.hardware.continuous_shank_count == 1
        assert trace.hardware.internal_hardware_count == 0
        assert trace.geometry_valid is True
        assert len(trace.containment.face_results) == 2
        assert all(item.valid for item in trace.containment.face_results)
        assert all(
            segment.receives_bearing_demand
            is (segment.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER)
            for segment in trace.path.segments
        )


@pytest.mark.parametrize(
    ("family", "connected_profile", "case_id"),
    [
        ("TEE", "RECTANGULAR_HOLLOW_SECTION", "C2_G11_TEE_CONNECTED_RHS_SUCCESSOR"),
        (
            "SINGLE_CLIP_ANGLE",
            "RECTANGULAR_HOLLOW_SECTION",
            "C2_G12_SINGLE_CONNECTED_RHS_SUCCESSOR",
        ),
        ("TEE", "SOLID_RECTANGULAR_SECTION", "C2_G13_TEE_CONNECTED_SRS"),
        (
            "SINGLE_CLIP_ANGLE",
            "SOLID_RECTANGULAR_SECTION",
            "C2_G14_SINGLE_CONNECTED_SRS",
        ),
    ],
)
def test_connected_rectangular_profiles_match_successor_goldens(
    family: str,
    connected_profile: str,
    case_id: str,
) -> None:
    payload = (
        build_tee_c2_payload(connected_profile_family=connected_profile)
        if family == "TEE"
        else build_clip_angle_c2_payload(connected_profile_family=connected_profile)
    )
    result = _tee(payload) if family == "TEE" else _clip(payload)
    expected = _case(case_id)["expected"]["segments"]
    assert _segments(result) == tuple(
        (item["kind"], item["identity"], Decimal(item["length_in"])) for item in expected
    )
    assert len(result.rectangular_full_through_paths) == 4
    assert result.visualization is not None
    assert result.design_check_ready is False


def test_workspace_tee_rhs_reaches_the_full_through_builder_without_single_wall_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_single_wall_resolver(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("RHS must not call the historical single-wall resolver.")

    monkeypatch.setattr(
        tee_module,
        "resolve_profile_wall_bolt_path",
        forbidden_single_wall_resolver,
    )
    result = _tee(build_tee_c2_workspace_rhs_payload())

    assert result.visualization is not None
    assert len(result.rectangular_full_through_paths) == 4
    assert {
        trace.path.axis.selected_face.value for trace in result.rectangular_full_through_paths
    } == {"Y_POS_FACE"}
    assert {
        trace.path.axis.opposite_face.value for trace in result.rectangular_full_through_paths
    } == {"Y_NEG_FACE"}
    assert _segments(result) == (
        ("MATERIAL_LAYER", "TEE_STEM", Decimal("0.375")),
        ("MATERIAL_LAYER", "RHS_NEAR_WALL", Decimal("0.5")),
        ("FREE_SHANK_SPAN", "RHS_CAVITY", Decimal("3.0")),
        ("MATERIAL_LAYER", "RHS_FAR_WALL", Decimal("0.5")),
    )
    assert all(
        trace.hardware.internal_hardware_count == 0
        for trace in result.rectangular_full_through_paths
    )
    assert all(
        len(trace.containment.face_results) == 2 for trace in result.rectangular_full_through_paths
    )


def test_tee_rhs_trim_retains_hollow_full_through_paths() -> None:
    payload = build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
    payload["connected_member_end_trim_enabled"] = True
    payload["connected_member_end_clearance"] = {"value": "0.5", "unit": "in"}
    result = _tee(payload)

    assert result.connected_member_end_trim.geometry_valid is True
    assert len(result.connected_member_end_trim.fabricated_trim_edge_ids) == 4
    assert len(result.rectangular_full_through_paths) == 4
    assert all(
        tuple(segment.identity for segment in trace.path.segments)
        == ("TEE_STEM", "RHS_NEAR_WALL", "RHS_CAVITY", "RHS_FAR_WALL")
        for trace in result.rectangular_full_through_paths
    )


@pytest.mark.parametrize("family", ["TEE", "SINGLE_CLIP_ANGLE"])
@pytest.mark.parametrize("target", tuple(LIMITATIONS))
def test_rectangular_limitations_do_not_promote_valid_geometry_to_invalid(
    family: str,
    target: str,
) -> None:
    payload = _valid_rectangular_support_payload(family, target)
    if family == "TEE":
        tee_result = _tee(payload)
        assert tee_result.visualization is not None
        assert tee_result.assembly_status.value == "NOT_EVALUATED"
        assert tee_result.design_check_ready is False
        assert tee_result.ordinary_pass_allowed is False
        assert set(tee_result.design_limitations) == LIMITATIONS[target]
    else:
        clip_result = _clip(payload)
        assert clip_result.visualization is not None
        assert clip_result.geometry_status.value == "VALID"
        assert clip_result.geometry_invalid_reasons == ()
        assert clip_result.design_check_ready is False
        assert clip_result.ordinary_pass_allowed is False
        assert set(clip_result.design_limitations) == LIMITATIONS[target]


def test_both_face_containment_fails_closed_without_moving_the_bolt_group() -> None:
    payload = build_clip_angle_c2_payload(support_target="RECTANGULAR_HOLLOW_COLUMN_WALL")
    invalid = _clip(payload)
    valid = _clip(
        _valid_rectangular_support_payload("SINGLE_CLIP_ANGLE", payload["support_target_id"])
    )
    assert invalid.geometry_status.value == "INVALID_GEOMETRY"
    assert invalid.geometry_invalid_reasons == (
        "RECTANGULAR_OPPOSING_FACE_HOLE_CONTAINMENT_INVALID",
    )
    assert invalid.interface_b.placement.bolts == valid.interface_b.placement.bolts
    assert any(not item.geometry_valid for item in invalid.rectangular_full_through_paths)


@pytest.mark.parametrize("family", ["TEE", "SINGLE_CLIP_ANGLE"])
@pytest.mark.parametrize(
    ("target", "connected_profile"),
    [
        ("RECTANGULAR_HOLLOW_COLUMN_WALL", "FLAT_PLATE"),
        ("SOLID_RECTANGULAR_COLUMN_FACE", "FLAT_PLATE"),
        ("W_COLUMN_FLANGE", "RECTANGULAR_HOLLOW_SECTION"),
        ("W_COLUMN_FLANGE", "SOLID_RECTANGULAR_SECTION"),
    ],
)
def test_rectangular_us_si_paths_and_engineering_fingerprints_are_exact(
    family: str,
    target: str,
    connected_profile: str,
) -> None:
    builder = build_tee_c2_payload if family == "TEE" else build_clip_angle_c2_payload
    evaluator = _tee if family == "TEE" else _clip
    customary = evaluator(
        builder(
            support_target=target,
            connected_profile_family=connected_profile,
            unit_system="US_CUSTOMARY",
        )
    )
    metric = evaluator(
        builder(
            support_target=target,
            connected_profile_family=connected_profile,
            unit_system="SI",
        )
    )
    assert customary.engineering_fingerprint == metric.engineering_fingerprint
    assert [item.path_fingerprint for item in customary.rectangular_full_through_paths] == [
        item.path_fingerprint for item in metric.rectangular_full_through_paths
    ]


def test_exact_allowed_rhs_successors_and_non_rhs_invariance() -> None:
    tee_c2_rhs = _tee(build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION"))
    assert tee_c2_rhs.engineering_fingerprint == (
        "a089c44a4652b207ff1145d8a5790154855c1078cf006a6022c8d649f947a6f9"
    )
    tee_rhs = preview_tee_connector(
        build_tee_r8_profile_wall_request(profile_family="RECTANGULAR_HOLLOW_SECTION")
    )
    assert tee_rhs.engineering_fingerprint == (
        "9269fc2ec373686d2a946970e0c1633a2c6188f8d0c4ca650e30088771a7c0d5"
    )
    assert tee_rhs.engineering_fingerprint != (
        "77fe6b02d379e189ed7b2279360c3610d1bc74d52fe3a91e0d1a81114348f196"
    )
    exact_clip_rhs = {
        "BRACE": (
            "134b392d915a7a9fc6265e308ec19e2fc1fb6d3c62e2f8ca0c516d90b571e00f",
            "8228c0573f32282cc00097d9ab037538abca29518a3b5f97c568abf4a8a31d33",
            "16ae7ce854c5b5b4d34da713373bcf5924f5fc411687e5dc0a765928e5db3288",
        ),
        "BEAM": (
            "c3416a2bdb7505417782c75a9bb5c4b2e1963f7ef041857344e0147b253bd75d",
            "2c168d03538ec9a98e996141fd9e8cf07b1588e7a4cf246562a2f7fa3c3ae563",
            "1c995ab0e90b76cd405bff1c5f4990bef2fdbba83e12daac47dffd9fbace7c51",
        ),
    }
    for role, (before, after, c2_fingerprint) in exact_clip_rhs.items():
        result = preview_clip_angle(
            build_clip_angle_request(
                profile_family="RECTANGULAR_HOLLOW_SECTION",
                connected_role=role,
            )
        )
        assert result.engineering_fingerprint == after
        assert result.engineering_fingerprint != before
        c2_payload = build_clip_angle_c2_payload(
            connected_profile_family="RECTANGULAR_HOLLOW_SECTION"
        )
        c2_payload["connected_member_profile"]["role"] = role
        c2_result = _clip(c2_payload)
        assert c2_result.orchestration_contract_version == "3.3C2-RC1"
        assert c2_result.engineering_fingerprint == c2_fingerprint

    for target, role in (("W_COLUMN_FLANGE", "COLUMN"), ("W_BEAM_FLANGE", "BEAM")):
        c2 = _tee(build_tee_c2_payload(support_target=target))
        legacy = preview_tee_connector(build_tee_r2_request(profile_family="FLAT_PLATE", role=role))
        assert c2.engineering_fingerprint == legacy.engineering_fingerprint
        c2_clip = _clip(build_clip_angle_c2_payload(support_target=target))
        legacy_clip = preview_clip_angle(build_clip_angle_request(support_role=target))
        assert c2_clip.engineering_fingerprint == legacy_clip.engineering_fingerprint


def test_shared_c2_dto_rejects_target_incompatible_and_stale_fields() -> None:
    payload = build_tee_c2_payload(support_target="CHANNEL_COLUMN_WEB")
    payload["support_profile"]["wall_thickness"] = {"value": "0.5", "unit": "in"}
    with pytest.raises(ValidationError):
        TeeConnectorRequestDTO.model_validate(payload)
    legacy = build_clip_angle_c2_payload(support_target="ANGLE_COLUMN_LEG")
    legacy["support_dimensions"] = {
        "member_length": {"value": "16", "unit": "in"},
        "overall_depth": {"value": "8", "unit": "in"},
        "flange_width": {"value": "8", "unit": "in"},
        "web_thickness": {"value": "0.5", "unit": "in"},
        "flange_thickness": {"value": "0.75", "unit": "in"},
    }
    with pytest.raises(ValidationError):
        ClipAngleConnectorRequestDTO.model_validate(legacy)

    stale_tee = build_tee_c2_payload()
    stale_tee["support_role"] = "COLUMN"
    with pytest.raises(ValidationError, match="forbids stale legacy"):
        TeeConnectorRequestDTO.model_validate(stale_tee)


def test_shared_support_dto_and_length_mapping_reject_invalid_contracts() -> None:
    blank = build_tee_c2_payload()
    blank["support_profile"]["profile_id"] = "   "
    with pytest.raises(ValidationError, match="profile_id must be nonempty"):
        TeeConnectorRequestDTO.model_validate(blank)

    wrong_role = build_tee_c2_payload(support_target="W_COLUMN_FLANGE")
    wrong_role["support_profile"]["role"] = "BEAM"
    with pytest.raises(ValidationError, match="inconsistent with support_target_id"):
        TeeConnectorRequestDTO.model_validate(wrong_role)

    wrong_flange_surface = build_tee_c2_payload(support_target="W_COLUMN_FLANGE")
    wrong_flange_surface["support_profile"]["selected_profile_surface"] = "WEB_POS_FACE"
    with pytest.raises(ValidationError, match="requires a selected exterior flange"):
        TeeConnectorRequestDTO.model_validate(wrong_flange_surface)

    wrong_web_surface = build_tee_c2_payload(support_target="W_COLUMN_WEB")
    wrong_web_surface["support_profile"]["selected_profile_surface"] = "FLANGE_POS_OUTER"
    with pytest.raises(ValidationError, match="requires a selected web broad face"):
        TeeConnectorRequestDTO.model_validate(wrong_web_surface)

    with pytest.raises(ValueError, match="must be length quantities"):
        _length(QuantityDTO(value="1", unit=Unit.KIP), Unit.IN)
    with pytest.raises(ValueError, match="must be positive"):
        _length(QuantityDTO(value="0", unit=Unit.IN), Unit.IN)


def test_versioned_dtos_reject_missing_and_cross_version_support_fields() -> None:
    tee_missing_profile = build_tee_c2_payload()
    tee_missing_profile["connected_member_profile"] = None
    with pytest.raises(ValidationError, match="requires connected_member_profile"):
        TeeConnectorRequestDTO.model_validate(tee_missing_profile)

    tee_missing_support = build_tee_c2_payload()
    tee_missing_support["support_target_id"] = None
    tee_missing_support["support_profile"] = None
    with pytest.raises(ValidationError, match="requires support_target_id"):
        TeeConnectorRequestDTO.model_validate(tee_missing_support)

    tee_legacy_missing = build_tee_r2_payload()
    tee_legacy_missing["support_dimensions"] = None
    with pytest.raises(ValidationError, match="Legacy Tee requests require"):
        TeeConnectorRequestDTO.model_validate(tee_legacy_missing)

    tee_legacy_crossed = build_tee_r2_payload()
    tee_c2 = build_tee_c2_payload()
    tee_legacy_crossed["support_target_id"] = tee_c2["support_target_id"]
    tee_legacy_crossed["support_profile"] = tee_c2["support_profile"]
    with pytest.raises(ValidationError, match="forbid C2 support fields"):
        TeeConnectorRequestDTO.model_validate(tee_legacy_crossed)

    clip_missing_support = build_clip_angle_c2_payload()
    clip_missing_support["support_target_id"] = None
    clip_missing_support["support_profile"] = None
    with pytest.raises(ValidationError, match="requires support_target_id"):
        ClipAngleConnectorRequestDTO.model_validate(clip_missing_support)

    clip_legacy_missing = build_clip_angle_payload()
    clip_legacy_missing["support_dimensions"] = None
    with pytest.raises(ValidationError, match="Legacy clip-angle requests require"):
        ClipAngleConnectorRequestDTO.model_validate(clip_legacy_missing)

    clip_legacy_crossed = build_clip_angle_payload()
    clip_c2 = build_clip_angle_c2_payload()
    clip_legacy_crossed["support_target_id"] = clip_c2["support_target_id"]
    clip_legacy_crossed["support_profile"] = clip_c2["support_profile"]
    with pytest.raises(ValidationError, match="forbid C2 support fields"):
        ClipAngleConnectorRequestDTO.model_validate(clip_legacy_crossed)


def test_domain_and_application_support_contracts_fail_closed() -> None:
    tee_column = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(build_tee_c2_payload())
    )
    column_profile = cast(MemberProfile, tee_column.support_profile)
    with pytest.raises(TypeError, match="profile must be a MemberProfile"):
        SharedSupportSelection(
            SharedSupportTargetId.W_COLUMN_FLANGE,
            cast(MemberProfile, object()),
        )
    orientation = cast(FRPComponentOrientation, column_profile.material_orientation)
    with pytest.raises(ValueError, match="integrated support member"):
        SharedSupportSelection(
            SharedSupportTargetId.W_COLUMN_FLANGE,
            replace(
                column_profile,
                member_id="other-member",
                material_orientation=replace(
                    orientation,
                    coordinate_frame=replace(
                        orientation.coordinate_frame,
                        owner_id="other-member",
                    ),
                ),
            ),
        )

    tee_beam = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(build_tee_c2_payload(support_target="W_BEAM_FLANGE"))
    )
    with pytest.raises(ValueError, match="role is inconsistent"):
        SharedSupportSelection(
            SharedSupportTargetId.W_COLUMN_FLANGE,
            cast(MemberProfile, tee_beam.support_profile),
        )

    tee_channel = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_c2_payload(support_target="CHANNEL_COLUMN_WEB")
        )
    )
    with pytest.raises(ValueError, match="family is inconsistent"):
        SharedSupportSelection(
            SharedSupportTargetId.W_COLUMN_FLANGE,
            cast(MemberProfile, tee_channel.support_profile),
        )
    with pytest.raises(ValueError, match="surface is inconsistent"):
        SharedSupportSelection(
            SharedSupportTargetId.W_COLUMN_FLANGE,
            replace(
                column_profile,
                selected_surface=MemberProfileSurfaceId.WEB_POS_FACE,
            ),
        )

    with pytest.raises(ValueError, match="supplied together"):
        replace(tee_column, support_profile=None)
    with pytest.raises(ValueError, match="require the C2 contract"):
        replace(tee_column, orchestration_contract_version="3.2-R2")

    clip = map_clip_angle_request(
        ClipAngleConnectorRequestDTO.model_validate(build_clip_angle_c2_payload())
    )
    with pytest.raises(ValueError, match="supplied together"):
        replace(clip, support_profile=None)
    with pytest.raises(ValueError, match="require the C2 contract"):
        replace(clip, orchestration_contract_version="3.3A-RC1")


def test_rectangular_integration_and_tee_expansion_reject_unsupported_shapes() -> None:
    tee = map_tee_connector_request(TeeConnectorRequestDTO.model_validate(build_tee_c2_payload()))
    support_profile = cast(MemberProfile, tee.support_profile)
    with pytest.raises(ValueError, match="requires RHS or SRS"):
        build_integrated_full_through_bolt(
            support_profile,
            selected_surface=cast(MemberProfileSurfaceId, support_profile.selected_surface),
            bolt_id="UNSUPPORTED",
            local_uv=(Decimal(0), Decimal(0)),
            hole_radius=Decimal("0.25"),
            connector_identity="CONNECTOR",
            connector_thickness=Decimal("0.5"),
            connector_material_region_id="CONNECTOR_REGION",
            rectangular_material_region_id="PROFILE_REGION",
            source_length_unit=Unit.IN,
        )

    resolved = resolve_tee_connector_request(
        map_tee_connector_request(
            TeeConnectorRequestDTO.model_validate(
                build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
            )
        )
    )
    group = resolved.context.resolved_bolt_groups[0]
    with pytest.raises(ValueError, match="requires one seed or one center per bolt"):
        _expanded_rectangular_bolt_points(
            replace(group, master_centers=()),
            resolved.request.interface_a_layout,
            "A",
        )


def test_negative_w_support_face_and_canonical_c2_identity() -> None:
    tee_payload = build_tee_c2_payload(support_target="W_COLUMN_FLANGE")
    tee_payload["support_profile"]["selected_profile_surface"] = "FLANGE_NEG_OUTER"
    request = map_tee_connector_request(TeeConnectorRequestDTO.model_validate(tee_payload))
    result = preview_tee_connector(request)
    assert result.visualization is not None
    assert result.support_target_id is SharedSupportTargetId.W_COLUMN_FLANGE
    canonical = cast(dict[str, Any], _canonical(request))
    assert "support_target_id" not in canonical
    assert "support_profile" not in canonical

    channel_request = map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_c2_payload(support_target="CHANNEL_COLUMN_WEB")
        )
    )
    channel_canonical = cast(dict[str, Any], _canonical(channel_request))
    assert channel_canonical["support_target_id"] == "CHANNEL_COLUMN_WEB"
    assert isinstance(channel_canonical["support_profile"], dict)


def test_paired_angle_production_fingerprint_remains_exact() -> None:
    paired = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert paired.engineering_fingerprint == (
        "67fbf413b78f57f73eebb63c467d12c9e299f3edf603edc7f51eeab6a68e1db8"
    )
    assert paired.canonical_input_fingerprint == (
        "1a1967aa0ed47593b5c33fbdef82ae0a4e18dc082500f8d794962b831fd16b5e"
    )
