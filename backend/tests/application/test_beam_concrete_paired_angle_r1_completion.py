"""Controlled Stage 3.5A-R1 completion and regression tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.application import preview_beam_concrete_paired_angle
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    MemberProfileFamily,
    MemberRole,
    RoundHollowProfileDimensions,
    WallQuantityVector,
)
from tests.beam_concrete_paired_angle_fixtures import (
    build_beam_concrete_paired_angle_payload,
    build_beam_concrete_paired_angle_request,
)

_ROOT = Path(__file__).parents[3]
_CONTRACT = "3.5A-R1-RC1"
_FAMILIES = (
    MemberProfileFamily.FLAT_PLATE,
    MemberProfileFamily.ANGLE,
    MemberProfileFamily.CHANNEL,
    MemberProfileFamily.WIDE_FLANGE_I,
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
    MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
)
_ARTIFACTS = (
    (
        _ROOT / "docs/governance/STAGE_3_5A_R1_CONCRETE_WALL_PAIRED_ANGLE_COMPLETION_DECISION.md",
        "655B768C83F7B07C30908950323E9D5CA30F33F42167D0D9E9E7CF9511AAA29B",
        b"**END OF STAGE 3.5A-R1 CONCRETE-WALL PAIRED-ANGLE COMPLETION DECISION**",
    ),
    (
        _ROOT
        / "docs/engineering"
        / "STAGE_3_5A_R1_CONCRETE_WALL_PAIRED_ANGLE_COMPLETION_ENGINEERING_SPECIFICATION_RC1.md",
        "4E15CF476039A4D8910FC201D87C9FA987F936BD28D26512B7B9D1757A99A353",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _ROOT
        / "backend/tests/golden"
        / "stage_3_5a_r1_concrete_wall_paired_angle_completion_golden_benchmarks_rc1.json",
        "00391A534854D6A3C9EE03A3FA5D7545D47EFF1E17A9BCEA12DE736336BC7B62",
        None,
    ),
    (
        _ROOT
        / "docs/qa/STAGE_3_5A_R1_CONCRETE_WALL_PAIRED_ANGLE_COMPLETION_AUTHORITY_LEDGER_RC1.md",
        "FBEF732897B21B172C3CE8C0DAD8B2D3E8912C25ADEB83B9E02886A07BC0455E",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _values(vector: WallQuantityVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return tuple(getattr(vector, name).to(unit).magnitude for name in ("h", "v", "n"))


def test_controlled_r1_artifacts_and_g1_through_g30_are_exact() -> None:
    for path, expected, sentinel in _ARTIFACTS:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == expected
        if sentinel is not None:
            assert raw.rstrip().endswith(sentinel)
    golden = json.loads(_ARTIFACTS[2][0].read_text(encoding="utf-8"))
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{index}" for index in range(1, 31)
    ]


def test_g1_historical_contract_is_bit_exact() -> None:
    result = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    assert result.canonical_input_fingerprint == (
        "09c2c297de51109472ec71712fcd7075e1458e1ab0edc0c39e2a0a1b4b5d2491"
    )
    assert result.wall_geometry_fingerprint == (
        "567c4ab203ae55d120f6f436698b4ce6c4edb0e61022cde0b8e52f6e3d40f731"
    )
    assert result.beam_geometry_fingerprint == (
        "102db7a3213bea32dc640500667aa1e7a17d25d5e832b40ee957cbf668d14699"
    )
    assert result.paired_connector_geometry_fingerprint == (
        "e21e7aa8461bf2d4c82072968a3af8adb01c1696dd16d4b357edf24d63a603cb"
    )
    assert result.combined_wall_handoff_fingerprint == (
        "d4d7ba6a171d6e059a7f9c20a83e2b1e601dc36a42136d34fba319caff656122"
    )
    assert result.external_anchor_handoff.handoff_fingerprint == (
        "592aa3c34d176688909c4dbb01d7171719e60776dfd72faa68be9595d820b353"
    )
    assert result.application_fingerprint == (
        "1cf31db46be8a5114f0fcd1fb58562792813cbb99a1b0a2ac184511023e9877c"
    )
    assert result.engineering_fingerprint == (
        "2e1f9dca79aa4af75238f27d7ae7e96232da1ca6083a613d9c6d00d75ae66e98"
    )
    assert len(result.positive_wall_group.anchors) == 4


def test_g3_through_g8_default_one_by_one_keeps_exact_wrenches_without_fabrication() -> None:
    request = build_beam_concrete_paired_angle_request(contract_version=_CONTRACT)
    result = preview_beam_concrete_paired_angle(request)
    assert len(result.positive_wall_group.anchors) == 1
    assert len(result.negative_wall_group.anchors) == 1
    assert result.positive_wall_group.wrench is not None
    assert result.negative_wall_group.wrench is not None
    assert _values(result.positive_wall_group.wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-2),
        Decimal(0),
    )
    assert _values(result.positive_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal(0),
        Decimal(6),
    )
    assert _values(result.negative_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal(0),
        Decimal(-6),
    )
    assert _values(result.combined_wall_wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-4),
        Decimal(0),
    )
    assert _values(result.combined_wall_wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(16),
        Decimal(0),
        Decimal(0),
    )
    assert result.positive_wall_group.nominal_demand is None
    assert result.negative_wall_group.nominal_demand is None
    assert result.positive_wall_group.force_equilibrium is False
    assert result.positive_wall_group.moment_equilibrium is False
    assert dict(result.limitations)["WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION"] == (
        "EXTERNAL_DESIGN_REQUIRED"
    )

    two_by_one = preview_beam_concrete_paired_angle(
        replace(
            request,
            wall_anchor_pattern=replace(
                request.wall_anchor_pattern, row_count=2, anchors_per_row=1
            ),
        )
    )
    assert len(two_by_one.positive_wall_group.anchors) == 2
    assert two_by_one.positive_wall_group.nominal_demand is not None
    two_by_two = preview_beam_concrete_paired_angle(
        replace(
            request,
            wall_anchor_pattern=replace(
                request.wall_anchor_pattern, row_count=2, anchors_per_row=2
            ),
        )
    )
    assert len(two_by_two.positive_wall_group.anchors) == 4
    assert two_by_two.positive_wall_group.nominal_demand is not None


@pytest.mark.parametrize("family", _FAMILIES)
def test_g9_through_g22_six_profile_scene_and_material_matrix(
    family: MemberProfileFamily,
) -> None:
    result = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(contract_version=_CONTRACT, profile_family=family)
    )
    assert result.geometry_status.value == "VALID"
    assert result.visualization is not None
    owners = {item.owner_id for item in result.visualization.boxes}
    assert {
        "clip-angle-connected-member",
        "POSITIVE_CLIP_ANGLE",
        "NEGATIVE_CLIP_ANGLE",
        "concrete-wall",
    } <= owners
    assert sum(item.owner_id == "POSITIVE_CLIP_ANGLE" for item in result.visualization.boxes) == 2
    assert sum(item.owner_id == "NEGATIVE_CLIP_ANGLE" for item in result.visualization.boxes) == 2
    assert len(result.visualization.material_regions) == 4
    assert result.visualization.beam_material_regions

    common = result.visualization.common_beam_bolts[0]
    if family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION:
        assert common.layer_ids == (
            "POSITIVE_CLIP_CONNECTED_LEG",
            "RHS_NEAR_WALL",
            "RHS_CAVITY",
            "RHS_FAR_WALL",
            "NEGATIVE_CLIP_CONNECTED_LEG",
        )
        assert not any(
            "CAVITY" in item.material_region_id
            for item in result.visualization.beam_material_regions
        )
    elif family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        assert "RHS_CAVITY" not in common.layer_ids
        assert "SOLID_RECTANGULAR_SECTION" in common.layer_ids


@pytest.mark.parametrize(
    "family",
    [MemberProfileFamily.WIDE_FLANGE_I, MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION],
)
def test_g27_us_si_geometry_wrenches_handoff_and_fingerprints_are_exact(
    family: MemberProfileFamily,
) -> None:
    us = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(contract_version=_CONTRACT, profile_family=family)
    )
    si = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, profile_family=family, unit_system="SI"
        )
    )
    assert us.geometry_status == si.geometry_status
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.wall_geometry_fingerprint == si.wall_geometry_fingerprint
    assert us.beam_geometry_fingerprint == si.beam_geometry_fingerprint
    assert us.paired_connector_geometry_fingerprint == si.paired_connector_geometry_fingerprint
    assert us.common_beam_group.result_fingerprint == si.common_beam_group.result_fingerprint
    assert us.combined_wall_handoff_fingerprint == si.combined_wall_handoff_fingerprint
    assert (
        us.external_anchor_handoff.handoff_fingerprint
        == si.external_anchor_handoff.handoff_fingerprint
    )
    assert us.application_fingerprint == si.application_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint


def test_successor_dto_is_strictly_family_specific_and_historical_is_w_only() -> None:
    flat = build_beam_concrete_paired_angle_payload(
        contract_version=_CONTRACT, profile_family="FLAT_PLATE"
    )
    BeamConcretePairedAngleRequestDTO.model_validate(flat)
    flat["beam_profile"]["dimensions"]["web_thickness"] = {"value": "0.5", "unit": "in"}
    with pytest.raises(ValidationError):
        BeamConcretePairedAngleRequestDTO.model_validate(flat)

    rhs = build_beam_concrete_paired_angle_payload(
        contract_version=_CONTRACT, profile_family="RECTANGULAR_HOLLOW_SECTION"
    )
    del rhs["beam_profile"]["dimensions"]["wall_thickness"]
    with pytest.raises(ValidationError):
        BeamConcretePairedAngleRequestDTO.model_validate(rhs)

    historical = build_beam_concrete_paired_angle_payload()
    historical["beam_profile"] = build_beam_concrete_paired_angle_payload(
        contract_version=_CONTRACT, profile_family="CHANNEL"
    )["beam_profile"]
    with pytest.raises(ValidationError, match=r"Historical Stage 3\.5A accepts only the W/I"):
        BeamConcretePairedAngleRequestDTO.model_validate(historical)


def test_successor_domain_rejects_wrong_identity_role_and_unsupported_family() -> None:
    request = build_beam_concrete_paired_angle_request(contract_version=_CONTRACT)
    with pytest.raises(ValueError, match="controlled connected-member identity and beam role"):
        replace(request, beam_profile=replace(request.beam_profile, role=MemberRole.BRACE))
    with pytest.raises(ValueError, match="six authorized connected profiles"):
        replace(
            request,
            beam_profile=replace(
                request.beam_profile,
                family=MemberProfileFamily.ROUND_HOLLOW_SECTION,
                dimensions=RoundHollowProfileDimensions(Decimal(16), Decimal(6), Decimal("0.5")),
                selected_surface=None,
            ),
        )
