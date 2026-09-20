"""Controlled Stage 3.3B paired clip-angle application and golden regressions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import frp_master_connection.application.clip_angle_orchestration as clip_module
import frp_master_connection.application.paired_clip_angle_orchestration as pair_module
from frp_master_connection.application import (
    PAIRED_CLIP_ANGLE_EQUAL_SHARING_REASON,
    PAIRED_CLIP_ANGLE_REQUIRED_CHECKS,
    PairedClipAngleDesignStatus,
    design_check_paired_clip_angle,
    preview_paired_clip_angle,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ClipAngleBoltLayout,
    ClipAngleBoltPlacementMode,
    ClipAngleHand,
    ClipAngleSupportRole,
    PairedClipAngleFrame,
    PairedClipAngleGroupIdentity,
    PairedClipAngleLayerIdentity,
    PairedClipAngleSymmetryProof,
)
from tests.clip_angle_fixtures import build_clip_angle_request
from tests.paired_clip_angle_fixtures import build_paired_clip_angle_request

_ROOT = Path(__file__).parents[3]
_ARTIFACTS = (
    (
        _ROOT
        / (
            "docs/engineering/"
            "STAGE_3_3B_SYMMETRIC_PAIRED_CLIP_ANGLE_ENGINEERING_SPECIFICATION_RC1.md"
        ),
        "A0804095AB0C52E281AC4727169CCFAE46A56E978586BEF2194134B058F7E542",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _ROOT
        / "backend/tests/golden/stage_3_3b_symmetric_paired_clip_angle_golden_benchmarks_rc1.json",
        "6C6BB25C31873AEBDC512AD50B669EB125FCF207118010A9C56D37C45E62FE99",
        None,
    ),
    (
        _ROOT / "docs/qa/STAGE_3_3B_SYMMETRIC_PAIRED_CLIP_ANGLE_AUTHORITY_LEDGER_RC1.md",
        "408DA8DC9C53069749ED3BBD3644CA45E136029FF6DE92DCE5D753C68A1077E9",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _per_bolt(group: object) -> tuple[Decimal, ...]:
    demand = group.demand  # type: ignore[attr-defined]
    return tuple(
        item.total_force_magnitude.to(Unit.KIP).magnitude for item in demand.scenarios[0].per_bolt
    )


def test_controlled_artifacts_and_golden_case_ids_are_exact() -> None:
    for path, digest, sentinel in _ARTIFACTS:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == digest
        if sentinel is not None:
            assert sentinel in raw
    golden = json.loads(_ARTIFACTS[1][0].read_bytes())
    assert [item["id"] for item in golden["benchmarks"]] == [
        f"G{index}_{suffix}"
        for index, suffix in enumerate(
            (
                "DEFAULT_SYMMETRIC_FLAT_PLATE_PAIR",
                "COMMON_GROUP_2X1_SUPPORT_GROUPS_2X2",
                "W_I_WEB_THREE_LAYER_STACK",
                "COLUMN_BEAM_SUPPORT_LOCAL_INVARIANCE",
                "EXACT_PAIR_AND_SUPPORT_GROUP_MIRROR",
                "EQUAL_SHARING_ELIGIBILITY_PASS",
                "OFF_PLANE_FORCE_EQUAL_SHARING_FAIL",
                "OFF_SYMMETRY_REFERENCE_EQUAL_SHARING_FAIL",
                "METHOD_UNSUPPORTED_GEOMETRY_CURRENT",
                "PAIRED_TRIM_25_DEGREES_HALF_INCH",
                "US_SI_EQUIVALENCE",
                "COMMON_THROUGH_BOLT_HARDWARE",
                "PAIR_MATERIAL_REGIONS",
                "LIMITATIONS_AND_FAIL_PRECEDENCE",
            ),
            start=1,
        )
    ]


def test_domain_frame_and_symmetry_contracts_fail_closed() -> None:
    assert PairedClipAngleFrame().handedness == "S_P cross P_P = L_P"
    with pytest.raises(ValueError, match="fixes S_P"):
        PairedClipAngleFrame(s_axis=(Decimal(-1), Decimal(0), Decimal(0)))
    with pytest.raises(ValueError, match="fixes P_P"):
        PairedClipAngleFrame(p_axis=(Decimal(0), Decimal(-1), Decimal(0)))
    with pytest.raises(ValueError, match="fixes L_P"):
        PairedClipAngleFrame(l_axis=(Decimal(0), Decimal(0), Decimal(-1)))
    with pytest.raises(ValueError, match="provenance"):
        PairedClipAngleFrame(symmetry_plane="x=0")
    with pytest.raises(ValueError, match="requires both"):
        PairedClipAngleSymmetryProof(False, True, True, ())
    with pytest.raises(ValueError, match="cannot contain"):
        PairedClipAngleSymmetryProof(True, True, True, ("unexpected",))
    with pytest.raises(ValueError, match="explicit reason"):
        PairedClipAngleSymmetryProof(True, False, False, ())


def test_request_domain_validation_rejects_bad_identity_contract_and_profile() -> None:
    request = build_paired_clip_angle_request()
    with pytest.raises(ValueError, match="request_id"):
        replace(request, request_id=" ")
    with pytest.raises(ValueError, match="contract version"):
        replace(request, orchestration_contract_version="3.3B-DRAFT")
    angle = build_clip_angle_request(profile_family="ANGLE").connected_member_profile
    with pytest.raises(ValueError, match="Flat Plate"):
        replace(request, connected_member_profile=angle)


def test_g1_default_pair_geometry_demands_and_layer_allocation() -> None:
    result = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert result.geometry_status.value == "VALID"
    assert result.symmetry_proof.equal_sharing_eligible is True
    assert result.design_check_ready is True
    assert len(result.branch_actions) == 2
    assert [item.force.z.to(Unit.KIP).magnitude for item in result.branch_actions] == [
        Decimal(2),
        Decimal(2),
    ]
    assert len(result.common_member_group.placement.bolts) == 4
    assert _per_bolt(result.common_member_group) == (Decimal(1),) * 4
    assert _per_bolt(result.positive_support_group) == (Decimal("0.5"),) * 4
    assert _per_bolt(result.negative_support_group) == (Decimal("0.5"),) * 4
    first = result.common_member_group.layer_demands[:3]
    assert [item.layer_id for item in first] == list(PairedClipAngleLayerIdentity)
    assert [item.total_force_magnitude.to(Unit.KIP).magnitude for item in first] == [
        Decimal("0.5"),
        Decimal(1),
        Decimal("0.5"),
    ]
    common_demand = result.common_member_group.demand
    assert common_demand is not None
    parent_vector = common_demand.scenarios[0].per_bolt[0].total_force
    assert all(item.parent_total_force is parent_vector for item in first)
    assert all(item.parent_demand_fingerprint for item in first)


def test_support_handoff_preserves_full_mirrored_branch_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[clip_module.ClipAngleOrchestrationRequest] = []
    original = clip_module._resolve_interface

    def capture(
        request: clip_module.ClipAngleOrchestrationRequest,
        placement: clip_module.ClipAngleInterfacePlacementTrace,
        layout: ClipAngleBoltLayout,
    ) -> clip_module.ClipAngleInterfaceResult:
        captured.append(request)
        return original(request, placement, layout)

    monkeypatch.setattr(pair_module, "_resolve_interface", capture)
    result = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert len(captured) == 3
    assert [item.global_reference_point for item in captured[1:]] == [
        item.reference_point for item in result.branch_actions
    ]


def test_g2_common_2x1_keeps_both_support_groups_2x2() -> None:
    request = build_paired_clip_angle_request()
    layout = replace(
        request.common_member_layout,
        bolts_per_row=1,
        placement_mode=ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
        width_offset=Decimal(0),
        length_offset=Decimal(0),
    )
    result = preview_paired_clip_angle(replace(request, common_member_layout=layout))
    assert len(result.common_member_group.placement.bolts) == 2
    assert _per_bolt(result.common_member_group) == (Decimal(2),) * 2
    assert _per_bolt(result.positive_support_group) == (Decimal("0.5"),) * 4


@pytest.mark.parametrize("family", ["FLAT_PLATE", "WIDE_FLANGE_I", "CHANNEL"])
def test_g3_profile_binding_and_double_sided_exterior_contact(family: str) -> None:
    result = preview_paired_clip_angle(build_paired_clip_angle_request(profile_family=family))
    assert result.geometry_status.value == "VALID"
    assert result.visualization is not None
    assert result.visualization.connected_member_profile_family.value == family
    owners = {item.owner_id for item in result.visualization.boxes}
    assert "POSITIVE_CLIP_ANGLE" in owners
    assert "NEGATIVE_CLIP_ANGLE" in owners
    positive = next(
        item
        for item in result.visualization.boxes
        if item.id.endswith("clip-angle-connected-leg-solid")
        and item.owner_id == "POSITIVE_CLIP_ANGLE"
    )
    negative = next(
        item
        for item in result.visualization.boxes
        if item.id.endswith("clip-angle-connected-leg-solid")
        and item.owner_id == "NEGATIVE_CLIP_ANGLE"
    )
    assert positive.center[0].magnitude == -negative.center[0].magnitude


def test_g4_column_beam_reuses_pair_local_geometry() -> None:
    column = preview_paired_clip_angle(build_paired_clip_angle_request())
    beam = preview_paired_clip_angle(build_paired_clip_angle_request(support_role="W_BEAM_FLANGE"))
    assert column.common_member_group.placement.width_coordinates == (
        beam.common_member_group.placement.width_coordinates
    )
    assert column.positive_support_group.placement.width_coordinates == (
        beam.positive_support_group.placement.width_coordinates
    )
    assert beam.support_role is ClipAngleSupportRole.W_BEAM_FLANGE


def test_g5_pair_and_support_group_are_exact_mirrors() -> None:
    result = preview_paired_clip_angle(build_paired_clip_angle_request())
    positive = result.positive_support_group.placement
    negative = result.negative_support_group.placement
    assert positive.bolt_group_id == PairedClipAngleGroupIdentity.POSITIVE_SUPPORT_BOLT_GROUP
    assert negative.bolt_group_id == PairedClipAngleGroupIdentity.NEGATIVE_SUPPORT_BOLT_GROUP
    assert [item.magnitude for item in positive.width_coordinates] == [
        -item.magnitude for item in negative.width_coordinates
    ]
    assert [item.axis for item in positive.bolts] == [item.axis for item in negative.bolts]


@pytest.mark.parametrize(
    ("force", "reference"),
    [(("1", "0", "4"), ("0", "2.25", "0")), (("0", "0", "4"), ("0.25", "2.25", "0"))],
)
def test_g7_g8_symmetry_failure_keeps_geometry_current(
    force: tuple[str, str, str], reference: tuple[str, str, str]
) -> None:
    result = preview_paired_clip_angle(
        build_paired_clip_angle_request(force=force, reference=reference)
    )
    assert result.geometry_status.value == "VALID"
    assert result.branch_actions == ()
    assert result.design_check_ready is False
    assert result.assembly_status is PairedClipAngleDesignStatus.NOT_EVALUATED
    assert PAIRED_CLIP_ANGLE_EQUAL_SHARING_REASON in result.symmetry_proof.reasons
    assert result.positive_support_group.demand is None


def test_g9_four_rows_are_current_but_outside_prescriptive_scope() -> None:
    request = build_paired_clip_angle_request()
    layout = replace(
        request.common_member_layout,
        row_count=4,
        pitch=Decimal("0.5"),
        negative_end_distance=Decimal("3.25"),
        positive_end_distance=Decimal("3.25"),
    )
    result = preview_paired_clip_angle(replace(request, common_member_layout=layout))
    assert result.geometry_status.value == "VALID"
    assert result.common_member_group.demand is not None
    assert (
        result.common_member_group.demand.method_applicability.value
        == "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE"
    )
    assert result.design_check_ready is False


def test_g10_trim_publishes_full_profile_meshes_without_ghost_boxes() -> None:
    request = build_paired_clip_angle_request(profile_family="WIDE_FLANGE_I")
    request = replace(
        request,
        connector_dimensions=replace(request.connector_dimensions, connector_length=Decimal(6)),
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
    assert result.trim.measured_plane_clearance is not None
    assert result.trim.measured_plane_clearance.magnitude == Decimal("0.5")
    assert result.visualization is not None
    assert result.visualization.meshes
    assert not any(
        item.owner_id == "clip-angle-connected-member" for item in result.visualization.boxes
    )


def test_g11_us_si_engineering_fingerprint_is_exact() -> None:
    us = preview_paired_clip_angle(build_paired_clip_angle_request())
    si = preview_paired_clip_angle(build_paired_clip_angle_request(unit_system="SI"))
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint


def test_g12_g13_hardware_and_material_region_ownership() -> None:
    result = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert result.visualization is not None
    assert len(result.visualization.common_member_bolts) == 4
    assert len(result.visualization.positive_support_bolts) == 4
    assert len(result.visualization.negative_support_bolts) == 4
    assert all(len(item.layer_ids) == 3 for item in result.visualization.common_member_bolts)
    assert len(result.material_regions) == 4
    assert {item.physical_element_id.split(":", 1)[0] for item in result.material_regions} == {
        "POSITIVE_CLIP_ANGLE",
        "NEGATIVE_CLIP_ANGLE",
    }


def test_g14_design_runs_handoff_but_retains_required_limitations() -> None:
    result = design_check_paired_clip_angle(build_paired_clip_angle_request())
    assert result.preview.resistance_evaluated is True
    assert result.preview.common_member_group.resistance is not None
    assert result.preview.positive_support_group.resistance is not None
    assert result.preview.negative_support_group.resistance is not None
    assert result.preview.required_checks == PAIRED_CLIP_ANGLE_REQUIRED_CHECKS
    assert result.required_check_status == "NOT_EVALUATED"
    assert result.ordinary_pass_allowed is False
    assert result.assembly_status is PairedClipAngleDesignStatus.FAIL
    assert result.supported_interface_failure_present is True
    allocations = result.preview.common_member_group.resistance.automatic_handoff_results[0]
    layer_checks = tuple(
        item
        for item in allocations.checks
        if item.resistance_result is not None
        and item.resistance_result.layer_id
        in {member.value for member in PairedClipAngleLayerIdentity}
        and item.family.value
        in {"PIN_BEARING", "FIRST_ROW_NET_TENSION", "INTERROW_SHEAR_OUT", "BLOCK_SHEAR"}
    )
    assert layer_checks
    assert {item.demand_source.value for item in layer_checks} == {
        "STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE"
    }
    first_row: dict[str, Decimal] = {}
    for item in layer_checks:
        if item.family.value != "FIRST_ROW_NET_TENSION":
            continue
        check_result = item.resistance_result
        assert check_result is not None
        assert check_result.layer_id is not None
        assert check_result.demand is not None
        first_row[check_result.layer_id] = check_result.demand.to(Unit.KIP).magnitude
    assert first_row == {
        PairedClipAngleLayerIdentity.POSITIVE_CONNECTED_LEG.value: Decimal(1),
        PairedClipAngleLayerIdentity.CONNECTED_MEMBER.value: Decimal(2),
        PairedClipAngleLayerIdentity.NEGATIVE_CONNECTED_LEG.value: Decimal(1),
    }


def test_connected_profile_material_regions_follow_the_paired_member_shift() -> None:
    result = preview_paired_clip_angle(build_paired_clip_angle_request())
    assert result.visualization is not None
    origins = result.visualization.connected_member_material_regions
    assert origins
    profile_centers = {
        item.center[0].to(Unit.IN).magnitude
        for item in result.visualization.boxes
        if item.owner_id == "clip-angle-connected-member"
    }
    assert {item.origin[0].to(Unit.IN).magnitude for item in origins} <= profile_centers


@pytest.mark.parametrize("design", [False, True])
def test_stage_2_5a_is_called_once_per_physical_group(
    monkeypatch: pytest.MonkeyPatch, design: bool
) -> None:
    calls = 0
    original = vars(clip_module)["calculate_eccentric_bolt_group_demand"]

    def counted(value: object) -> object:
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(clip_module, "calculate_eccentric_bolt_group_demand", counted)
    if design:
        design_check_paired_clip_angle(build_paired_clip_angle_request())
    else:
        preview_paired_clip_angle(build_paired_clip_angle_request())
    assert calls == 3


def test_true_hole_containment_failure_is_geometry_invalid() -> None:
    request = build_paired_clip_angle_request()
    invalid = replace(
        request.common_member_layout,
        heel_edge_distance=Decimal("3.75"),
        free_edge_distance=Decimal("0.01"),
    )
    result = preview_paired_clip_angle(replace(request, common_member_layout=invalid))
    assert result.geometry_status.value == "INVALID_GEOMETRY"
    assert result.visualization is None
    assert result.assembly_status is PairedClipAngleDesignStatus.INVALID_GEOMETRY


def test_trim_failure_and_internal_empty_demand_paths_are_explicit() -> None:
    request = build_paired_clip_angle_request(profile_family="WIDE_FLANGE_I")
    invalid_trim = replace(
        request,
        connector_dimensions=replace(request.connector_dimensions, connector_length=Decimal(6)),
        connected_member_inclination_degrees=Decimal(25),
        connected_member_end_trim_enabled=True,
        connected_member_end_clearance=PhysicalQuantity.of("0.5", Unit.IN),
    )
    result = preview_paired_clip_angle(invalid_trim)
    assert "CONNECTED_MEMBER_PAIRED_CLIP_ANGLE_INTERFERENCE" in result.geometry_invalid_reasons
    demand = result.common_member_group.demand
    assert demand is not None
    assert (
        pair_module._layer_demands(
            replace(demand, scenarios=()),
            "0" * 64,
        )
        == ()
    )


def test_common_handoff_rejects_zero_in_plane_design_demand() -> None:
    request = build_paired_clip_angle_request()
    zero_request = replace(
        request,
        global_force=pair_module._vector_zero_like(request.global_force),
    )
    single = pair_module._single_request(
        zero_request,
        ClipAngleHand.POSITIVE_S_SIDE,
    )
    common, *_rest = pair_module._paired_placements(zero_request)
    interface = clip_module._resolve_interface(
        single,
        common,
        zero_request.common_member_layout,
    )
    with pytest.raises(ValueError, match="nonzero"):
        pair_module._with_common_resistance(
            zero_request,
            single,
            interface,
            (),
        )
