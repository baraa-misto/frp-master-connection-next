"""Stage 3.5A-R2 material-axis and three-component force golden regressions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    map_beam_concrete_paired_angle_request,
)
from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.application import (
    BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
    ExternalAnchorHandoffMode,
    design_check_beam_concrete_paired_angle,
    preview_beam_concrete_paired_angle,
)
from frp_master_connection.application import (
    beam_concrete_paired_angle_orchestration as module,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import WallQuantityVector
from tests.beam_concrete_paired_angle_fixtures import (
    build_beam_concrete_paired_angle_payload,
    build_beam_concrete_paired_angle_request,
)

_ROOT = Path(__file__).parents[3]
_CONTRACT = BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
_FAMILIES = (
    "FLAT_PLATE",
    "ANGLE",
    "CHANNEL",
    "WIDE_FLANGE_I",
    "RECTANGULAR_HOLLOW_SECTION",
    "SOLID_RECTANGULAR_SECTION",
)
_ARTIFACTS: tuple[tuple[Path, str, bytes | None], ...] = (
    (
        _ROOT / "docs/governance/STAGE_3_5A_R2_MATERIAL_AXES_THREE_COMPONENT_FORCE_DECISION.md",
        "8436AB8B453DC586A48524044AD45163C5A00E3FBFB321ED198D4F54AF298E50",
        b"**END OF STAGE 3.5A-R2 MATERIAL-AXIS AND THREE-COMPONENT FORCE DECISION**",
    ),
    (
        _ROOT
        / "docs/engineering"
        / "STAGE_3_5A_R2_MATERIAL_AXES_THREE_COMPONENT_FORCE_ENGINEERING_SPECIFICATION_RC1.md",
        "DA5E525F39EF95CA7859D756BD67E0CCB0DF285E3FF94A3EE7467204E3CAC877",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _ROOT
        / "backend/tests/golden"
        / "stage_3_5a_r2_material_axes_three_component_force_golden_benchmarks_rc1.json",
        "0A0C67715A73DFA02078E5F3BB7A5456775AAD9F9359EF5D66CF07B5CFF36078",
        None,
    ),
    (
        _ROOT / "docs/qa/STAGE_3_5A_R2_MATERIAL_AXES_THREE_COMPONENT_FORCE_AUTHORITY_LEDGER_RC1.md",
        "DE62CFA17DB219D707D3F4F3CE6C38FD8544CE0515F18404E42493AC0CC2A816",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _values(vector: WallQuantityVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return tuple(getattr(vector, name).to(unit).magnitude for name in ("h", "v", "n"))


def _dot(
    left: tuple[Decimal, Decimal, Decimal], right: tuple[Decimal, Decimal, Decimal]
) -> Decimal:
    return sum((a * b for a, b in zip(left, right, strict=True)), Decimal(0))


def _cross(
    left: tuple[Decimal, Decimal, Decimal], right: tuple[Decimal, Decimal, Decimal]
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def test_r2_controlled_artifacts_and_g1_through_g34_are_exact() -> None:
    for path, expected, sentinel in _ARTIFACTS:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == expected
        if sentinel is not None:
            assert raw.rstrip().endswith(sentinel)
    golden = json.loads(_ARTIFACTS[2][0].read_text(encoding="utf-8"))
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{index}" for index in range(1, 35)
    ]


@pytest.mark.parametrize(
    ("major", "minor", "axial", "force", "moment", "mode"),
    [
        ("-4", "0", "0", ("0", "-4", "0"), ("16", "0", "0"), "BRANCH_RESOLVED"),
        ("0", "0", "4", ("0", "0", "4"), ("0", "0", "0"), "BRANCH_RESOLVED"),
        ("0", "0", "-4", ("0", "0", "-4"), ("0", "0", "0"), "BRANCH_RESOLVED"),
        ("0", "2", "0", ("2", "0", "0"), ("0", "8", "0"), "COMBINED_LAYOUT"),
        ("-4", "2", "3", ("2", "-4", "3"), ("16", "8", "0"), "COMBINED_LAYOUT"),
        ("-4", "0", "3", ("0", "-4", "3"), ("16", "0", "0"), "BRANCH_RESOLVED"),
    ],
)
def test_g3_through_g12_exact_force_wrench_and_handoff_modes(
    major: str,
    minor: str,
    axial: str,
    force: tuple[str, str, str],
    moment: tuple[str, str, str],
    mode: str,
) -> None:
    result = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT,
            major_shear=major,
            minor_shear=minor,
            axial_force=axial,
        )
    )
    assert _values(result.combined_wall_wrench.force_hvn, Unit.KIP) == tuple(
        Decimal(item) for item in force
    )
    assert _values(result.combined_wall_wrench.moment_hvn, Unit.KIP_IN) == tuple(
        Decimal(item) for item in moment
    )
    assert result.handoff_mode is ExternalAnchorHandoffMode(mode)
    assert result.external_anchor_handoff.handoff_mode is ExternalAnchorHandoffMode(mode)
    assert result.external_anchor_handoff.all_anchors == (
        result.positive_wall_group.anchors + result.negative_wall_group.anchors
    )
    if mode == "BRANCH_RESOLVED":
        assert result.branch_allocation_status == "RESOLVED"
        assert result.positive_wall_group.wrench is not None
        assert result.negative_wall_group.wrench is not None
    else:
        assert result.branch_allocation_status == "NOT_EVALUATED"
        assert result.positive_wall_group.wrench is None
        assert result.negative_wall_group.wrench is None
        exported = json.loads(result.external_anchor_handoff_json)
        assert "wrench" not in exported["positive_group"]
        assert "wrench" not in exported["negative_group"]


def test_g5_g6_g12_exact_symmetric_branch_forces_and_moments() -> None:
    tension = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, major_shear="0", axial_force="4"
        )
    )
    assert tension.positive_wall_group.wrench is not None
    assert tension.negative_wall_group.wrench is not None
    assert _values(tension.positive_wall_group.wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(0),
        Decimal(2),
    )
    assert _values(tension.positive_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(0),
        Decimal(6),
        Decimal(0),
    )
    assert _values(tension.negative_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(0),
        Decimal(-6),
        Decimal(0),
    )
    combined = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, major_shear="-4", axial_force="3"
        )
    )
    assert combined.positive_wall_group.wrench is not None
    assert combined.negative_wall_group.wrench is not None
    assert _values(combined.positive_wall_group.wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-2),
        Decimal("1.5"),
    )
    assert _values(combined.positive_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal("4.5"),
        Decimal(6),
    )
    assert _values(combined.negative_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal("-4.5"),
        Decimal(-6),
    )


def test_g13_g14_g17_limitations_and_no_generated_normal_resistance() -> None:
    minor = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, major_shear="0", minor_shear="2"
        )
    )
    assert minor.common_group_normal_action == PhysicalQuantity.of(Decimal(2), Unit.KIP)
    assert minor.common_beam_group.resistance is None
    assert {
        "MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION": "NOT_EVALUATED",
        "COMMON_MEMBER_GROUP_BOLT_AXIS_RESPONSE": "NOT_EVALUATED",
        "NONMAJOR_FORCE_CONNECTION_QUALIFICATION": "NOT_EVALUATED",
        "WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION": "EXTERNAL_DESIGN_REQUIRED",
    }.items() <= dict(minor.limitations).items()
    axial = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, major_shear="0", axial_force="-4"
        )
    )
    assert {
        "CLIP_ANGLE_WALL_LEG_AXIAL_TRANSFER_AND_PRYING": "NOT_EVALUATED",
        "WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION": "EXTERNAL_DESIGN_REQUIRED",
        "NONMAJOR_FORCE_CONNECTION_QUALIFICATION": "NOT_EVALUATED",
    }.items() <= dict(axial.limitations).items()
    design = design_check_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(
            contract_version=_CONTRACT, major_shear="0", minor_shear="2"
        )
    )
    assert design.preview.resistance_evaluated is False
    assert design.preview.common_beam_group.resistance is None


def test_g15_r2_strict_action_schema_and_zero_moment() -> None:
    payload = build_beam_concrete_paired_angle_payload(contract_version=_CONTRACT)
    request = map_beam_concrete_paired_angle_request(
        BeamConcretePairedAngleRequestDTO.model_validate(payload)
    )
    assert _values(request.user_force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-4),
        Decimal(0),
    )
    assert _values(request.user_moment_hvn, Unit.KIP_IN) == (Decimal(0),) * 3
    no_moment = dict(payload)
    no_moment.pop("user_moment_hvn")
    mapped = map_beam_concrete_paired_angle_request(
        BeamConcretePairedAngleRequestDTO.model_validate(no_moment)
    )
    assert _values(mapped.user_moment_hvn, Unit.KIP_IN) == (Decimal(0),) * 3
    nonzero = json.loads(json.dumps(payload))
    nonzero["user_moment_hvn"]["x"] = "1"
    with pytest.raises(ValueError, match="MOMENT_NOT_ALLOWED"):
        map_beam_concrete_paired_angle_request(
            BeamConcretePairedAngleRequestDTO.model_validate(nonzero)
        )
    for forbidden in ("reaction_shear", "user_force_hvn", "torsion"):
        invalid = json.loads(json.dumps(payload))
        invalid[forbidden] = {"value": "0", "unit": "kip"}
        with pytest.raises(ValidationError):
            BeamConcretePairedAngleRequestDTO.model_validate(invalid)
    missing = json.loads(json.dumps(payload))
    missing.pop("minor_shear")
    with pytest.raises(ValidationError, match="requires exactly"):
        BeamConcretePairedAngleRequestDTO.model_validate(missing)

    historical_profile = build_beam_concrete_paired_angle_payload(
        contract_version="3.5A-R1-RC1", profile_family="ANGLE"
    )
    historical_profile["orchestration_contract_version"] = "3.5A-RC1"
    with pytest.raises(ValidationError, match="only the W/I"):
        BeamConcretePairedAngleRequestDTO.model_validate(historical_profile)
    incomplete_historical = build_beam_concrete_paired_angle_payload()
    incomplete_historical.pop("reaction_shear")
    with pytest.raises(ValidationError, match=r"Historical Stage 3\.5A contracts require"):
        BeamConcretePairedAngleRequestDTO.model_validate(incomplete_historical)


def test_defensive_mapping_and_domain_contract_boundaries() -> None:
    payload = build_beam_concrete_paired_angle_payload(contract_version=_CONTRACT)
    dto = BeamConcretePairedAngleRequestDTO.model_validate(payload)
    object.__setattr__(dto, "major_shear", None)
    with pytest.raises(ValueError, match="incomplete"):
        map_beam_concrete_paired_angle_request(dto)
    historical = BeamConcretePairedAngleRequestDTO.model_validate(
        build_beam_concrete_paired_angle_payload()
    )
    object.__setattr__(historical, "reaction_shear", None)
    with pytest.raises(ValueError, match="force fields"):
        map_beam_concrete_paired_angle_request(historical)
    historical = BeamConcretePairedAngleRequestDTO.model_validate(
        build_beam_concrete_paired_angle_payload()
    )
    object.__setattr__(historical, "user_moment_hvn", None)
    with pytest.raises(ValueError, match="moment field"):
        map_beam_concrete_paired_angle_request(historical)
    request = build_beam_concrete_paired_angle_request(contract_version=_CONTRACT)
    with pytest.raises(ValueError, match="Major shear"):
        replace(
            request,
            reaction_shear=PhysicalQuantity.of(Decimal(-3), Unit.KIP),
        )


def test_g19_through_g27_backend_material_axes_match_physical_regions() -> None:
    for family in _FAMILIES:
        result = preview_beam_concrete_paired_angle(
            build_beam_concrete_paired_angle_request(
                contract_version=_CONTRACT, profile_family=family
            )
        )
        assert result.visualization is not None
        regions: tuple[Any, ...] = (
            *result.visualization.material_regions,
            *result.visualization.beam_material_regions,
        )
        assert regions
        for region in regions:
            axes = (region.lw, region.cw, region.tt)
            assert tuple(_dot(axis, axis) for axis in axes) == (Decimal(1),) * 3
            assert (_dot(axes[0], axes[1]), _dot(axes[0], axes[2]), _dot(axes[1], axes[2])) == (
                Decimal(0),
                Decimal(0),
                Decimal(0),
            )
            assert abs(_dot(_cross(axes[0], axes[1]), axes[2])) == 1
        assert all(
            item.owner_id != "concrete-wall"
            for item in result.visualization.boxes
            if item.material_region_id is not None
        )
        if family == "RECTANGULAR_HOLLOW_SECTION":
            assert {
                item.physical_element_id for item in result.visualization.beam_material_regions
            } == {
                "TOP_WALL",
                "BOTTOM_WALL",
                "SIDE_WALL_1",
                "SIDE_WALL_2",
            }
    wi = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(contract_version=_CONTRACT)
    )
    assert wi.visualization is not None
    boxes = wi.visualization.boxes
    for region in wi.visualization.beam_material_regions:
        box = next(
            item
            for item in boxes
            if item.owner_id == "clip-angle-connected-member"
            and item.role == region.physical_element_id
        )
        sizes = (box.size_s.magnitude, box.size_p.magnitude, box.size_l.magnitude)
        normal = box.basis[sizes.index(min(sizes))]
        assert abs(_dot(normal, region.tt)) == 1
        assert _dot(normal, region.lw) == _dot(normal, region.cw) == 0
    for region in wi.visualization.material_regions:
        owner = (
            "POSITIVE_CLIP_ANGLE"
            if region.physical_element_id.startswith("POSITIVE")
            else "NEGATIVE_CLIP_ANGLE"
        )
        role = (
            "CONNECTED_MEMBER_LEG"
            if region.physical_element_id.endswith("CONNECTED_MEMBER_LEG")
            else "SUPPORT_LEG"
        )
        box = next(item for item in boxes if item.owner_id == owner and item.role == role)
        sizes = (box.size_s.magnitude, box.size_p.magnitude, box.size_l.magnitude)
        normal = box.basis[sizes.index(min(sizes))]
        assert abs(_dot(normal, region.tt)) == 1
        assert _dot(region.cw, region.tt) == 0


def test_g29_g31_preview_zero_resistance_and_exact_us_si_fingerprints() -> None:
    kwargs = {
        "contract_version": _CONTRACT,
        "major_shear": "-4",
        "minor_shear": "2",
        "axial_force": "3",
    }
    us = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request(**kwargs))
    si = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(unit_system="SI", **kwargs)
    )
    assert us.resistance_evaluated is si.resistance_evaluated is False
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.combined_wall_handoff_fingerprint == si.combined_wall_handoff_fingerprint
    assert (
        us.external_anchor_handoff.handoff_fingerprint
        == si.external_anchor_handoff.handoff_fingerprint
    )
    assert us.application_fingerprint == si.application_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    exported = cast(dict[str, Any], module._export_value(us.external_anchor_handoff))
    assert exported["handoff_mode"] == "COMBINED_LAYOUT"


def test_r2_production_never_reads_the_golden_fixture() -> None:
    source = Path(module.__file__).read_text(encoding="utf-8").lower()
    assert "stage_3_5a_r2_material_axes_three_component_force_golden" not in source
    assert "tests/golden" not in source
