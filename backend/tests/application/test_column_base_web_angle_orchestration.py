"""Stage 3.5C geometry, demand, equilibrium, direction, and regression verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
)
from frp_master_connection.api.column_base_web_angle_schemas import ColumnBaseWebAngleRequestDTO
from frp_master_connection.application import (
    ColumnBaseGeometryStatus,
    design_check_column_base_web_angles,
    preview_column_base_web_angles,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    ColumnBaseComponentTransferTrace,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ColumnBaseAnchorPattern,
    ColumnBaseAssembly,
    ColumnBaseConcreteGeometry,
    ColumnBaseRequest,
    ColumnBaseSide,
    ColumnBaseStatus,
    ColumnBaseVector,
    ColumnBaseWideFlangeGeometry,
    EngineeringUnitSystem,
)
from tests.column_base_web_angle_fixtures import (
    build_column_base_web_angle_payload,
    build_column_base_web_angle_request,
)

_ROOT = Path(__file__).resolve().parents[3]
_CONTROLLED_HASHES = {
    _ROOT / "docs/governance/STAGE_3_5C_COLUMN_BASE_WEB_ANGLES_CONCRETE_SELECTION_DECISION.md": (
        "3e5f46cfdeca4c475d95f55a98e65244524fe8c8ae800021b1fe8898c81a6b45"
    ),
    _ROOT / "docs/engineering/STAGE_3_5C_COLUMN_BASE_WEB_ANGLES_CONCRETE_ENGINEERING_"
    "SPECIFICATION_RC1.md": "28d134c09acb2482fe2c13a8cfa8ad463dc3f28b1100664c13032760bb6070dd",
    _ROOT / "backend/tests/golden/stage_3_5c_column_base_web_angles_concrete_golden_"
    "benchmarks_rc1.json": "e494165a965b75fd92f893e06f0828e965a075cd42a4f85b7175d05be5b6d999",
    _ROOT / "docs/qa/STAGE_3_5C_COLUMN_BASE_WEB_ANGLES_CONCRETE_AUTHORITY_LEDGER_RC1.md": (
        "a5278df6224c998846f6cd8e4f6c725e6ad75b9ecd3698f53cfc6cbb17f27b83"
    ),
}
_GOLDEN = next(path for path in _CONTROLLED_HASHES if path.suffix == ".json")


def _request(payload: dict[str, object]) -> ColumnBaseRequest:
    return map_column_base_web_angle_request(ColumnBaseWebAngleRequestDTO.model_validate(payload))


def _magnitudes(vector: ColumnBaseVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return (
        vector.s.to(unit).magnitude,
        vector.t.to(unit).magnitude,
        vector.longitudinal.to(unit).magnitude,
    )


def test_controlled_artifacts_are_byte_exact_and_g1_through_g43_parse() -> None:
    for path, expected in _CONTROLLED_HASHES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert [item["id"] for item in golden["benchmarks"]] == [
        f"G{index}_{item['id'].split('_', 1)[1]}"
        for index, item in enumerate(golden["benchmarks"], start=1)
    ]
    assert golden["benchmarks"][-1]["id"] == "G43_FROZEN_REGRESSION_BOUNDARY"


def test_default_double_geometry_material_axes_paths_and_component_demands() -> None:
    result = preview_column_base_web_angles(build_column_base_web_angle_request())
    assert result.base_frame.handedness == "S_C cross T_C = L_C"
    assert result.base_frame.concrete_top == "L_C=0"
    assert result.geometry_status is ColumnBaseGeometryStatus.VALID
    assert result.assembly_status is ColumnBaseStatus.NOT_EVALUATED
    assert result.ordinary_pass_allowed is result.resistance_evaluated is False
    assert result.visualization is not None
    roles = [item.role for item in result.visualization.boxes]
    assert roles.count("CONCRETE_BASE") == 1
    assert roles.count("COLUMN_WEB") == 1
    assert roles.count("COLUMN_FLANGE") == 2
    assert roles.count("BASE_ANGLE_VERTICAL_LEG") == 2
    assert roles.count("BASE_ANGLE_HORIZONTAL_LEG") == 2
    assert len(result.visualization.web_bolts) == 4
    assert all(
        item.layer_ids
        == (
            "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
            "COLUMN_WEB",
            "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
        )
        for item in result.visualization.web_bolts
    )
    assert len(result.anchor_groups) == 2
    assert len(result.visualization.anchors) == 4
    assert all(
        anchor.axis_s_t_l == (Decimal(0), Decimal(0), Decimal(-1))
        and anchor.shank_end_s_t_l.longitudinal.magnitude == Decimal(-4)
        and "FAR_SIDE" not in " ".join(anchor.penetrated_layers)
        for anchor in result.visualization.anchors
    )
    transfer = result.component_transfer
    assert isinstance(transfer, ColumnBaseComponentTransferTrace)
    assert transfer.column_web_axial_demand.magnitude == Decimal(20)
    assert transfer.column_web_fraction == transfer.angle_system_fraction == Decimal(1)
    assert transfer.column_web_material_direction == "LW"
    assert transfer.angle_vertical_leg_material_direction == "CW"
    assert transfer.positive_angle_axial_demand is not None
    assert transfer.negative_angle_axial_demand is not None
    assert transfer.positive_angle_axial_demand.magnitude == Decimal(10)
    assert transfer.negative_angle_axial_demand.magnitude == Decimal(10)
    assert transfer.foundation_axial_action.magnitude == Decimal(20)
    assert transfer.component_design_demands_summed_for_equilibrium is False
    regions = {item.physical_element_id: item for item in result.visualization.material_regions}
    assert regions["COLUMN_WEB"].lw == (Decimal(0), Decimal(0), Decimal(1))
    assert regions["POSITIVE_BASE_ANGLE_VERTICAL_LEG"].cw == (
        Decimal(0),
        Decimal(0),
        Decimal(1),
    )
    assert regions["POSITIVE_BASE_ANGLE_HORIZONTAL_LEG"].tt == (
        Decimal(0),
        Decimal(0),
        Decimal(1),
    )


def test_default_stage_2_5a_demand_allocations_and_exact_wrenches_match_goldens() -> None:
    result = preview_column_base_web_angles(build_column_base_web_angle_request())
    assert result.web_group_demand.scenarios
    per_bolt = result.web_group_demand.scenarios[0].per_bolt
    assert len(per_bolt) == 4
    assert all(item.total_force.u.to(Unit.KIP).magnitude == Decimal(1) for item in per_bolt)
    assert all(item.total_force.v.to(Unit.KIP).magnitude == Decimal(-5) for item in per_bolt)
    expected = Decimal("5.099019513592784830028224109022781989564")
    quantum = Decimal("1e-39")
    with localcontext() as context:
        context.prec = 100
        assert all(
            item.total_force_magnitude.to(Unit.KIP).magnitude.quantize(quantum) == expected
            for item in per_bolt
        )
    by_layer = {(item.bolt_id, item.layer_id): item for item in result.layer_demands}
    for item in per_bolt:
        web = by_layer[(item.bolt_id, "COLUMN_WEB")]
        positive_layer = by_layer[(item.bolt_id, "POSITIVE_BASE_ANGLE_VERTICAL_LEG")]
        negative_layer = by_layer[(item.bolt_id, "NEGATIVE_BASE_ANGLE_VERTICAL_LEG")]
        assert web.fraction_of_parent == Decimal(1)
        assert positive_layer.fraction_of_parent == Decimal("0.5")
        assert negative_layer.fraction_of_parent == Decimal("0.5")
        with localcontext() as context:
            context.prec = 100
            assert web.resultant.magnitude.quantize(quantum) == expected
            half_expected = Decimal("2.549509756796392415014112054511390994782")
            assert positive_layer.resultant.magnitude.quantize(quantum) == half_expected
            assert negative_layer.resultant.magnitude.quantize(quantum) == half_expected
    assert _magnitudes(result.combined_foundation_wrench.force_s_t_l, Unit.KIP) == (
        Decimal(4),
        Decimal(0),
        Decimal(-20),
    )
    assert _magnitudes(result.combined_foundation_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal(0),
        Decimal(16),
        Decimal(0),
    )
    positive_anchor, negative_anchor = result.anchor_groups
    assert positive_anchor.branch_wrench is not None
    assert negative_anchor.branch_wrench is not None
    assert _magnitudes(positive_anchor.branch_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal("32.5"),
        Decimal(8),
        Decimal("6.5"),
    )
    assert _magnitudes(negative_anchor.branch_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal("-32.5"),
        Decimal(8),
        Decimal("-6.5"),
    )
    assert json.loads(result.external_handoff_json)["handoff_fingerprint"] == (
        result.external_handoff.handoff_fingerprint
    )


@pytest.mark.parametrize(
    ("side", "expected_t", "expected_s_moment", "expected_l_moment"),
    [("+T_C", "3.25", "65", "13"), ("-T_C", "-3.25", "-65", "-13")],
)
def test_single_angle_positive_and_negative_are_exact_mirrors_with_full_demand(
    side: str, expected_t: str, expected_s_moment: str, expected_l_moment: str
) -> None:
    payload = build_column_base_web_angle_payload(assembly="SINGLE_BASE_ANGLE", single_side=side)
    result = preview_column_base_web_angles(_request(payload))
    assert result.geometry_status is ColumnBaseGeometryStatus.VALID
    assert len(result.anchor_groups) == 1
    group = result.anchor_groups[0]
    assert group.centroid_s_t_l.t.magnitude == Decimal(expected_t)
    assert group.branch_wrench is not None
    assert _magnitudes(group.branch_wrench.force_s_t_l, Unit.KIP) == (
        Decimal(4),
        Decimal(0),
        Decimal(-20),
    )
    assert _magnitudes(group.branch_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal(expected_s_moment),
        Decimal(16),
        Decimal(expected_l_moment),
    )
    transfer = result.component_transfer
    assert isinstance(transfer, ColumnBaseComponentTransferTrace)
    assert transfer.single_angle_axial_demand is not None
    assert transfer.single_angle_axial_demand.magnitude == Decimal(20)
    assert all(item.fraction_of_parent == Decimal(1) for item in result.layer_demands)
    assert all(len(item.layer_ids) == 2 for item in result.visualization.web_bolts)  # type: ignore[union-attr]


def test_pure_and_combined_material_direction_classification_is_per_layer() -> None:
    axial = preview_column_base_web_angles(
        _request(build_column_base_web_angle_payload(web_plane_shear="0"))
    )
    axial_directions = {item.layer_id: item for item in axial.layer_directions}
    assert axial_directions["COLUMN_WEB"].bearing_direction_classification == "LONGITUDINAL"
    assert all(
        item.bearing_direction_classification == "TRANSVERSE"
        for key, item in axial_directions.items()
        if key != "COLUMN_WEB"
    )
    shear = preview_column_base_web_angles(
        _request(build_column_base_web_angle_payload(axial_compression="0"))
    )
    shear_directions = {item.layer_id: item for item in shear.layer_directions}
    assert shear_directions["COLUMN_WEB"].bearing_direction_classification == "TRANSVERSE"
    assert all(
        item.bearing_direction_classification == "LONGITUDINAL"
        for key, item in shear_directions.items()
        if key != "COLUMN_WEB"
    )
    combined = preview_column_base_web_angles(build_column_base_web_angle_request())
    assert {item.material_axis_angle_degrees for item in combined.layer_directions} == {
        Decimal(0),
        Decimal(90),
    }
    assert any(
        name == "COMBINED_IN_PLANE_LOCAL_RESISTANCE_PATH" for name, _ in combined.limitations
    )


def test_web_normal_action_is_retained_without_tension_prying_or_double_branch_split() -> None:
    result = preview_column_base_web_angles(
        _request(build_column_base_web_angle_payload(web_normal_shear="3"))
    )
    assert result.combined_foundation_wrench.force_s_t_l.t.magnitude == Decimal(3)
    assert all(group.branch_wrench is None for group in result.anchor_groups)
    assert (
        "WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION",
        "NOT_EVALUATED",
    ) in result.limitations
    assert ("COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE", "NOT_EVALUATED") in result.limitations
    assert not any(
        "TENSION_CAPACITY" in name or "PRYING_CAPACITY" in name for name, _ in result.limitations
    )
    assert result.external_handoff.combined_foundation_wrench == result.combined_foundation_wrench


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("embedment", "ANCHOR_EMBEDMENT_EXCEEDS_CONCRETE_DEPTH"),
        ("anchor_leg", "ANCHOR_HOLE_OUTSIDE_HORIZONTAL_LEG"),
        ("anchor_concrete", "ANCHOR_HOLE_OUTSIDE_CONCRETE_PLAN"),
        ("web_bolt", "WEB_BOLT_COMPLETE_HOLE_CONTAINMENT_INVALID"),
    ],
)
def test_true_geometry_failures_are_invalid_and_fail_closed(mutation: str, reason: str) -> None:
    payload = build_column_base_web_angle_payload()
    if mutation == "embedment":
        payload["external_anchor"]["specified_embedment"] = {"value": "13", "unit": "in"}
    elif mutation == "anchor_leg":
        payload["anchor_pattern"]["centroid_offset_t"] = {"value": "8", "unit": "in"}
    elif mutation == "anchor_concrete":
        payload["anchor_pattern"]["centroid_offset_t"] = {"value": "20", "unit": "in"}
    else:
        payload["web_group"]["centroid_height_l"] = {"value": "7", "unit": "in"}
    result = preview_column_base_web_angles(_request(payload))
    assert result.geometry_status is ColumnBaseGeometryStatus.INVALID_GEOMETRY
    assert result.assembly_status is ColumnBaseStatus.INVALID_GEOMETRY
    assert any(item.startswith(reason) for item in result.geometry_invalid_reasons)
    assert result.visualization is None
    assert result.design_check_ready is False


def test_design_runs_existing_pure_direction_local_seams_and_failure_precedence() -> None:
    axial_payload = build_column_base_web_angle_payload(web_plane_shear="0")
    design = design_check_column_base_web_angles(_request(axial_payload))
    assert design.web_group_resistance is not None
    assert design.ordinary_pass_allowed is False
    shear_payload = build_column_base_web_angle_payload(axial_compression="0")
    shear = design_check_column_base_web_angles(_request(shear_payload))
    assert shear.web_group_resistance is not None
    single_payload = build_column_base_web_angle_payload(
        assembly="SINGLE_BASE_ANGLE", web_plane_shear="0"
    )
    single = design_check_column_base_web_angles(_request(single_payload))
    assert single.web_group_resistance is not None
    combined = design_check_column_base_web_angles(build_column_base_web_angle_request())
    assert combined.web_group_resistance is None
    high = build_column_base_web_angle_payload(web_plane_shear="0", axial_compression="100000")
    failed = design_check_column_base_web_angles(_request(high))
    assert failed.supported_local_failure_present is True
    assert failed.assembly_status is ColumnBaseStatus.FAIL
    assert failed.preview.limitations


def test_zero_in_plane_action_retains_normal_handoff_without_resistance() -> None:
    payload = build_column_base_web_angle_payload(
        axial_compression="0", web_plane_shear="0", web_normal_shear="3"
    )
    preview = preview_column_base_web_angles(_request(payload))
    assert all(
        item.bearing_direction_classification == "NO_IN_PLANE_ACTION"
        for item in preview.layer_directions
    )
    design = design_check_column_base_web_angles(_request(payload))
    assert design.web_group_resistance is None
    assert design.preview.design_check_ready is True


def test_us_si_geometry_demands_wrenches_handoff_and_fingerprints_are_exactly_equivalent() -> None:
    us = preview_column_base_web_angles(
        _request(build_column_base_web_angle_payload(unit_system="US_CUSTOMARY"))
    )
    si = preview_column_base_web_angles(
        _request(build_column_base_web_angle_payload(unit_system="SI"))
    )
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert us.application_fingerprint == si.application_fingerprint
    assert us.external_handoff.handoff_fingerprint == si.external_handoff.handoff_fingerprint
    assert tuple(
        value.canonical_magnitude
        for value in (
            us.combined_foundation_wrench.force_s_t_l.s,
            us.combined_foundation_wrench.moment_s_t_l.t,
        )
    ) == tuple(
        value.canonical_magnitude
        for value in (
            si.combined_foundation_wrench.force_s_t_l.s,
            si.combined_foundation_wrench.moment_s_t_l.t,
        )
    )


def test_domain_contract_rejects_wrong_identity_units_actions_and_geometry_types() -> None:
    request = build_column_base_web_angle_request()
    with pytest.raises(ValueError, match="request_id"):
        replace(request, request_id=" ")
    with pytest.raises(ValueError, match="Unsupported"):
        replace(request, contract_version="3.5C-DRAFT")
    with pytest.raises(ValueError, match="Source length"):
        replace(request, source_length_unit=Unit.MM)
    with pytest.raises(ValueError, match="positive lengths"):
        replace(request, web_bolt_diameter=PhysicalQuantity.of(0, Unit.IN))
    with pytest.raises(ValueError, match="smaller"):
        replace(request, web_hole_diameter=PhysicalQuantity.of("0.4", Unit.IN))
    with pytest.raises(ValueError, match="force quantities"):
        replace(request, web_plane_shear=PhysicalQuantity.of(1, Unit.IN))
    with pytest.raises(ValueError, match="UPLIFT"):
        replace(request, axial_compression=PhysicalQuantity.of(-1, Unit.KIP))
    with pytest.raises(ValueError, match="moment quantities"):
        replace(
            request,
            user_moment=ColumnBaseVector(
                *tuple(PhysicalQuantity.of(0, Unit.KIP) for _ in range(3))
            ),
        )
    with pytest.raises(ValueError, match="MOMENT_NOT_ALLOWED"):
        replace(
            request,
            user_moment=ColumnBaseVector(
                PhysicalQuantity.of(1, Unit.KIP_IN),
                PhysicalQuantity.of(0, Unit.KIP_IN),
                PhysicalQuantity.of(0, Unit.KIP_IN),
            ),
        )
    with pytest.raises(ValueError, match="action_reference"):
        replace(
            request,
            action_reference=ColumnBaseVector(
                PhysicalQuantity.of(0, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP),
            ),
        )


def test_domain_value_objects_reject_invalid_dimensions_and_expose_both_side_signs() -> None:
    assert ColumnBaseSide.POSITIVE_T_C.sign == Decimal(1)
    assert ColumnBaseSide.NEGATIVE_T_C.sign == Decimal(-1)
    with pytest.raises(ValueError, match="Concrete dimensions"):
        ColumnBaseConcreteGeometry(
            PhysicalQuantity.of(0, Unit.IN),
            PhysicalQuantity.of(1, Unit.IN),
            PhysicalQuantity.of(1, Unit.IN),
        )
    with pytest.raises(ValueError, match="positive lengths"):
        ColumnBaseWideFlangeGeometry(
            PhysicalQuantity.of(10, Unit.IN),
            PhysicalQuantity.of(8, Unit.IN),
            PhysicalQuantity.of(0, Unit.IN),
            PhysicalQuantity.of("0.5", Unit.IN),
            PhysicalQuantity.of(24, Unit.IN),
        )
    with pytest.raises(ValueError, match="web must be thinner"):
        replace(
            build_column_base_web_angle_request().column,
            web_thickness=PhysicalQuantity.of(8, Unit.IN),
        )
    with pytest.raises(ValueError, match="leave a positive web"):
        replace(
            build_column_base_web_angle_request().column,
            flange_thickness=PhysicalQuantity.of(5, Unit.IN),
        )
    with pytest.raises(ValueError, match="supports only"):
        replace(build_column_base_web_angle_request().column, profile_family="CHANNEL")
    with pytest.raises(ValueError, match="counts must be positive"):
        ColumnBaseAnchorPattern(
            0,
            1,
            PhysicalQuantity.of(1, Unit.IN),
            PhysicalQuantity.of(0, Unit.IN),
            PhysicalQuantity.of(1, Unit.IN),
        )
    with pytest.raises(ValueError, match="nonnegative lengths"):
        ColumnBaseAnchorPattern(
            1,
            1,
            PhysicalQuantity.of(-1, Unit.IN),
            PhysicalQuantity.of(0, Unit.IN),
            PhysicalQuantity.of(1, Unit.IN),
        )
    with pytest.raises(ValueError, match="share one dimension"):
        ColumnBaseVector(
            PhysicalQuantity.of(0, Unit.IN),
            PhysicalQuantity.of(0, Unit.KIP),
            PhysicalQuantity.of(0, Unit.IN),
        )


def test_canonical_fingerprint_helper_covers_mapping_payloads() -> None:
    import frp_master_connection.application.column_base_web_angle_orchestration as module

    request = build_column_base_web_angle_request()
    first = module._canonical_fingerprint(
        {"quantity": request.axial_compression, "enum": ColumnBaseAssembly.SINGLE_BASE_ANGLE}
    )
    second = module._canonical_fingerprint(
        {"enum": ColumnBaseAssembly.SINGLE_BASE_ANGLE, "quantity": request.axial_compression}
    )
    assert first == second
    assert module._fingerprint((Decimal("1.0"), "x")) == module._fingerprint((Decimal(1), "x"))
    preview = preview_column_base_web_angles(request)
    assert (
        module._layer_demands_for_request(request, replace(preview.web_group_demand, scenarios=()))
        == ()
    )
    assert request.unit_system is EngineeringUnitSystem.US_CUSTOMARY
