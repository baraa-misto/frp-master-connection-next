"""Stage 2.5B RC1 eccentric-demand resistance-handoff verification."""

import hashlib
from dataclasses import FrozenInstanceError, replace
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

import frp_master_connection.calculation.resistance_handoff as handoff_module
from frp_master_connection.calculation import (
    BEARING_DIRECTION_BOUNDARY_DEGREES,
    RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION,
    RESISTANCE_HANDOFF_DECIMAL_PRECISION,
    RESISTANCE_HANDOFF_ENGINE_VERSION,
    RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION,
    RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION,
    RESISTANCE_HANDOFF_RULE_SET_VERSION,
    BearingForceDirection,
    BlockShearCompatibilityEvidence,
    BlockShearCompatibilityStatus,
    BlockShearEccentricityClassification,
    BlockShearEccentricityContext,
    DemandAnalysisAvailability,
    DemandAnalysisWarningCode,
    EccentricDemandInput,
    EccentricDemandResult,
    EccentricResistanceHandoffInput,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
    ExplicitBoltAxisDemand,
    FRPPropertyKind,
    InPlaneQuantityVector,
    LayerBearingAxisContext,
    LayerInPlaneDemandAllocation,
    MaterialDirection,
    MultiRowCalculationResult,
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowEquationMethod,
    MultiRowExecutableCheck,
    MultiRowExecutionBundle,
    MultiRowMethodApplicability,
    MultiRowOverallDisposition,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    NumericalComparison,
    PhysicalQuantity,
    PlanAvailability,
    QualificationDisposition,
    ResistanceCheckHandoff,
    ResistanceHandoffCoverage,
    ResistanceHandoffDemandSource,
    ResistanceHandoffFingerprintEnvelope,
    ResistanceHandoffTraceStage,
    ResistanceHandoffVersionContext,
    ResistanceHandoffWarningCode,
    Unit,
    calculate_eccentric_bolt_group_demand,
    calculate_eccentric_resistance_handoff,
    calculate_multirow_connection,
    canonical_resistance_handoff_input_json,
    resistance_handoff_input_fingerprint,
)
from tests.calculation.golden_loader import (
    FrozenJson,
    decimal_strings,
    load_slice_3_resistance_handoff_rc1_golden_fixture,
)
from tests.calculation.test_multirow_engine import _bundle, _check


def _mapping(value: FrozenJson) -> MappingProxyType[str, FrozenJson]:
    return cast(MappingProxyType[str, FrozenJson], value)


def _tuple(value: FrozenJson) -> tuple[FrozenJson, ...]:
    return cast(tuple[FrozenJson, ...], value)


def _quantity_vector(values: tuple[str, str, str], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity.of(item, unit) for item in values))


def _scaled_bundle(
    total: str = "3",
    *,
    checks: tuple[object, ...] | None = None,
    required_ids: tuple[str, ...] | None = None,
) -> MultiRowExecutionBundle:
    base = _bundle()
    factor = Decimal(total) / Decimal(2)
    demand = base.planning_root.demand
    scenarios = tuple(
        replace(
            scenario,
            rows=tuple(
                replace(
                    row,
                    row_demand=row.row_demand * factor,
                    per_bolt_demands=tuple(
                        replace(item, demand=item.demand * factor) for item in row.per_bolt_demands
                    ),
                )
                for row in scenario.rows
            ),
        )
        for scenario in demand.scenarios
    )
    demand = replace(
        demand,
        total_in_plane_demand=PhysicalQuantity.of(total, Unit.KIP),
        scenarios=scenarios,
    )
    planning = replace(base.planning_root, demand=demand)
    bolts = tuple(
        replace(item, in_plane_demand=item.in_plane_demand * factor) for item in base.bolts
    )
    lines = tuple(replace(item, demand=item.demand * factor) for item in base.bolt_lines)
    signed = replace(
        base.signed_demand,
        in_plane_magnitude=PhysicalQuantity.of(total, Unit.KIP),
    )
    if checks is None:
        bolt_checks = tuple(
            check
            for index, bolt in enumerate(bolts, start=1)
            for check in (
                _check(
                    f"shear:bolt:{index}",
                    MultiRowCheckFamily.BOLT_SHEAR,
                    MultiRowEquationMethod.BOLT_SHEAR,
                    demand=str(Decimal(total) / 4),
                    bolt_id=bolt.bolt_id,
                ),
                _check(
                    f"bearing:bolt:{index}",
                    MultiRowCheckFamily.PIN_BEARING,
                    MultiRowEquationMethod.PIN_BEARING,
                    demand=str(Decimal(total) / 4),
                    layer_id="LAYER-1",
                    bolt_id=bolt.bolt_id,
                ),
            )
        )
        first = _check(
            "first-row",
            MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
            MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED,
            demand=total,
            layer_id="LAYER-1",
            plan=planning.first_row_net_tension[0],
        )
        interrow = tuple(
            _check(
                f"interrow:{index}",
                MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12,
                demand=str(Decimal(total) / 2),
                layer_id="LAYER-1",
                bolt_line_id=plan.bolt_line_id,
                plan=plan,
            )
            for index, plan in enumerate(planning.interrow_shear_out, start=1)
        )
        typed_checks = (*bolt_checks, first, *interrow)
    else:
        typed_checks = cast(tuple[MultiRowExecutableCheck, ...], checks)
    required = (
        tuple(item.check_id for item in typed_checks) if required_ids is None else required_ids
    )
    return replace(
        base,
        planning_root=planning,
        bolts=bolts,
        bolt_lines=lines,
        signed_demand=signed,
        checks=typed_checks,
        required_checks=MultiRowRequiredCheckContract(required),
    )


def _demand_input(
    bundle: MultiRowExecutionBundle,
    *,
    total: str = "3",
    offset_v: str = "0",
    normal: str = "0",
    member_moment: str = "0",
) -> EccentricDemandInput:
    geometry = bundle.physical_geometry
    centroid_x = sum((item.x for item in geometry.bolts), Decimal(0)) / len(geometry.bolts)
    centroid_y = sum((item.y for item in geometry.bolts), Decimal(0)) / len(geometry.bolts)
    return EccentricDemandInput(
        "ACTION-SOURCE-1",
        "MEMBER-1",
        _quantity_vector((total, "0", normal), Unit.KIP),
        _quantity_vector(("0", "0", member_moment), Unit.KIP_IN),
        _quantity_vector(("0", "0", "0"), Unit.KIP_IN),
        _quantity_vector((str(centroid_x), str(centroid_y + Decimal(offset_v)), "0"), Unit.IN),
        ExactInterfaceFrame(
            geometry.interface_id,
            _quantity_vector(("0", "0", "0"), Unit.IN),
            (Decimal(1), Decimal(0), Decimal(0)),
            (Decimal(0), Decimal(1), Decimal(0)),
            (Decimal(0), Decimal(0), Decimal(1)),
        ),
        geometry,
        bundle.planning_root.demand,
        bundle.planning_root.applicability.method_applicability,
        bundle.planning_root.applicability.qualification,
        ("Stage 2.5B test action",),
    )


def _handoff_input(
    *,
    total: str = "3",
    offset_v: str = "0",
    normal: str = "0",
    member_moment: str = "0",
    bundle: MultiRowExecutionBundle | None = None,
    explicit: tuple[ExplicitBoltAxisDemand, ...] = (),
    block: BlockShearCompatibilityEvidence | None = None,
) -> EccentricResistanceHandoffInput:
    actual_bundle = _scaled_bundle(total) if bundle is None else bundle
    parent = calculate_eccentric_bolt_group_demand(
        _demand_input(
            actual_bundle,
            total=total,
            offset_v=offset_v,
            normal=normal,
            member_moment=member_moment,
        )
    )
    return EccentricResistanceHandoffInput(
        parent,
        parent.scenarios[0].scenario_id,
        actual_bundle,
        tuple(
            LayerBearingAxisContext(
                layer.layer_id, (Decimal(1), Decimal(0)), layer.source_geometry_ids
            )
            for layer in actual_bundle.layers
        ),
        explicit,
        block,
        ("DEMAND_ANALYSIS", "COMPATIBILITY_HANDOFF", "RESISTANCE_CALCULATION"),
    )


def _serialized(value: PhysicalQuantity, unit: Unit) -> str:
    return format(
        value.to(unit).magnitude.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN),
        ".12f",
    )


def test_layer_specific_demand_allocation_validation_is_fail_closed() -> None:
    base = _handoff_input()
    assert handoff_module._group_layer_allocation(base, None) is None
    bolt_id = base.demand_result.bolts[0].bolt_id
    layer_id = base.execution_bundle.layers[0].layer_id
    fingerprint = base.demand_result.result_fingerprint

    with pytest.raises(ValueError, match="greater than zero"):
        LayerInPlaneDemandAllocation(bolt_id, layer_id, Decimal(0), "TEST", fingerprint)
    with pytest.raises(ValueError, match="at most one"):
        LayerInPlaneDemandAllocation(bolt_id, layer_id, Decimal("1.1"), "TEST", fingerprint)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        LayerInPlaneDemandAllocation(bolt_id, layer_id, Decimal(1), "TEST", "BAD")

    def allocation(
        *,
        bolt: str = bolt_id,
        layer: str = layer_id,
        parent: str = fingerprint,
    ) -> LayerInPlaneDemandAllocation:
        return LayerInPlaneDemandAllocation(bolt, layer, Decimal(1), "TEST", parent)

    with pytest.raises(ValueError, match="physical bolt"):
        replace(base, layer_demand_allocations=(allocation(bolt="UNKNOWN"),))
    with pytest.raises(ValueError, match="penetrated layer"):
        replace(base, layer_demand_allocations=(allocation(layer="UNKNOWN"),))
    with pytest.raises(ValueError, match="parent demand fingerprint"):
        replace(base, layer_demand_allocations=(allocation(parent="0" * 64),))
    with pytest.raises(ValueError, match="every penetrated bolt layer"):
        replace(base, layer_demand_allocations=(allocation(),))

    complete = tuple(
        LayerInPlaneDemandAllocation(
            bolt.bolt_id,
            layer,
            Decimal("0.5")
            if bolt.bolt_id == base.execution_bundle.bolts[0].bolt_id
            else Decimal(1),
            "TEST",
            fingerprint,
        )
        for bolt in base.execution_bundle.bolts
        for layer in bolt.layer_ids
    )
    with pytest.raises(ValueError, match="one controlled fraction"):
        replace(base, layer_demand_allocations=complete)


def _decimal_serialized(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN), ".12f")


def test_controlled_golden_identity_schema_inventory_decimal_data_and_immutability() -> None:
    repository_root = Path(__file__).parents[3]
    path = Path(__file__).parents[1] / "golden" / "calculation_slice_3_resistance_handoff_rc1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == (
        "A2B0BF8D37F085739BD4A984A79A0406A3D0BBEF26D4E3ADF0BBFE761AA6FEE2"
    )
    first = load_slice_3_resistance_handoff_rc1_golden_fixture()
    second = load_slice_3_resistance_handoff_rc1_golden_fixture()
    assert first == second
    assert first is not second
    assert first["schema_version"] == (
        "frp-master-connection-calculation-slice-3-resistance-handoff-golden-rc1"
    )
    assert {cast(str, _mapping(item)["id"]) for item in _tuple(first["handoff_cases"])} == {
        "CONCENTRIC_2X2_FULL_HANDOFF",
        "SMALL_ECCENTRIC_2X2_PARTIAL_SUPPORTED_CHECKS_PASS",
        "ECCENTRIC_2X2_BEARING_DIRECTION_SHIFT_FAIL",
        "MULTILAYER_PER_BOLT_BEARING_DIRECTION",
        "BEARING_ANGLE_BOUNDARY",
        "ZERO_DEMAND_BOLT_NOT_REQUIRED",
        "ECCENTRIC_BLOCK_SHEAR_MATCHED_CONTEXT",
        "ECCENTRIC_BLOCK_SHEAR_UNMATCHED_CONTEXT",
    }
    assert len(_tuple(first["status_cases"])) == 4
    parent = _mapping(first["parent_authorities"])
    assert parent == {
        "slice_2_rc2_spec_sha256": (
            "C296E5FB3B304985A62D49B3F486EF6DB8E5D212EDFE2B83AACB6D68E09B71FD"
        ),
        "slice_2_rc2_golden_sha256": (
            "B3A49FB44089E065F7B4659F52AB856288298247504423970C3D19B8FCEA7B0B"
        ),
        "slice_3_demand_rc1_spec_sha256": (
            "38D742EAB8AA9EE2706135C96B32A4E01E74082D1A6360D82C3D787BB42E0470"
        ),
        "slice_3_demand_rc1_golden_sha256": (
            "0B2999DE96F1C4C02A1B68D4E4F262E4BFE3FBD65F3D8D1A50DE7F9B65C01D7B"
        ),
    }
    specification_path = repository_root / (
        "docs/engineering/CALCULATION_SLICE_3_RESISTANCE_HANDOFF_ENGINEERING_SPECIFICATION_RC1.md"
    )
    ledger_path = repository_root / (
        "docs/qa/CALCULATION_SLICE_3_RESISTANCE_HANDOFF_RC1_INDEPENDENT_VERIFICATION_LEDGER.md"
    )
    controlled = {
        specification_path: ("C0E2C63096DA357D23E684B835DFACA050F9112C21E9B7EC5E90EFFEA890105F"),
        ledger_path: ("3E85C61AD10865B5293165DF5847B63E96F80D19361E194A180B40EFB403ED27"),
    }
    assert {
        file_path: hashlib.sha256(file_path.read_bytes()).hexdigest().upper()
        for file_path in controlled
    } == controlled
    assert decimal_strings(first)
    with pytest.raises(TypeError):
        first["schema_version"] = "changed"  # type: ignore[index]


def test_versions_are_exact_and_parent_results_remain_immutable() -> None:
    versions = ResistanceHandoffVersionContext()
    assert (
        versions.calculation_contract_version,
        versions.resistance_handoff_engine_version,
        versions.resistance_handoff_rule_set_version,
        versions.resistance_handoff_result_schema_version,
        versions.resistance_handoff_fingerprint_schema_version,
        RESISTANCE_HANDOFF_DECIMAL_PRECISION,
        BEARING_DIRECTION_BOUNDARY_DEGREES,
    ) == (
        RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION,
        RESISTANCE_HANDOFF_ENGINE_VERSION,
        RESISTANCE_HANDOFF_RULE_SET_VERSION,
        RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION,
        RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION,
        80,
        Decimal(5),
    )
    value = _handoff_input()
    before = value.demand_result
    bundle_before = value.execution_bundle
    parent_fingerprint = value.demand_result.result_fingerprint
    result = calculate_eccentric_resistance_handoff(value)
    assert value.demand_result.result_fingerprint == parent_fingerprint
    assert result.parent_demand_result_fingerprint == parent_fingerprint
    assert value.demand_result == before
    assert value.execution_bundle == bundle_before
    assert result.trace_stages == (
        ResistanceHandoffTraceStage.DEMAND_ANALYSIS,
        ResistanceHandoffTraceStage.COMPATIBILITY_HANDOFF,
        ResistanceHandoffTraceStage.RESISTANCE_CALCULATION,
    )
    assert result.source_trace == value.source_trace
    with pytest.raises(FrozenInstanceError):
        result.coverage = ResistanceHandoffCoverage.PARTIAL_ECCENTRIC  # type: ignore[misc]


def test_concentric_full_handoff_is_numerically_identical_to_legacy_slice_2() -> None:
    value = _handoff_input()
    expected = calculate_multirow_connection(value.execution_bundle)
    result = calculate_eccentric_resistance_handoff(value)
    assert result.coverage is ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR
    assert result.legacy_result == expected
    assert result.supported_results == tuple(
        item
        for item in expected.results
        if item.availability is MultiRowResultAvailability.CALCULATED
    )
    assert result.overall_disposition == expected.overall_disposition
    assert result.numerical_comparison == expected.numerical_comparison
    assert result.governing_supported_check_ids == expected.governing_result_ids
    assert all(
        item.demand_source is ResistanceHandoffDemandSource.STAGE_2_4B_LEGACY_DIRECT
        for item in result.checks
    )
    assert all(
        _serialized(item.magnitude, Unit.KIP) == "0.750000000000"
        for item in result.per_bolt_demands
    )


def test_small_eccentric_golden_uses_actual_total_vectors_and_fails_group_modes_closed() -> None:
    result = calculate_eccentric_resistance_handoff(_handoff_input(offset_v="0.1"))
    assert result.coverage is ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    assert result.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert result.numerical_comparison is NumericalComparison.NOT_EVALUATED
    expected = (
        ("0.712500000000", "0.037500000000", "0.713486159642", "3.012787504183"),
        ("0.787500000000", "0.037500000000", "0.788392351561", "2.726310993906"),
        ("0.712500000000", "-0.037500000000", "0.713486159642", "3.012787504183"),
        ("0.787500000000", "-0.037500000000", "0.788392351561", "2.726310993906"),
    )
    actual = sorted(
        (
            _serialized(item.force.u, Unit.KIP),
            _serialized(item.force.v, Unit.KIP),
            _serialized(item.magnitude, Unit.KIP),
            _decimal_serialized(cast(Decimal, selection.angle_degrees)),
        )
        for item, selection in zip(result.per_bolt_demands, result.bearing_selections, strict=True)
    )
    assert actual == sorted(expected)
    assert all(
        item.material_direction is MaterialDirection.LONGITUDINAL
        and item.property_kind is FRPPropertyKind.FBR_L
        for item in result.bearing_selections
    )
    assert set(result.unsupported_required_check_ids) == {
        "first-row",
        "interrow:1",
        "interrow:2",
    }
    assert {warning.code for warning in result.warnings} == {
        ResistanceHandoffWarningCode.ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1,
        ResistanceHandoffWarningCode.ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1,
    }
    shear_results = tuple(
        item
        for item in result.supported_results
        if item.limit_state is MultiRowCheckFamily.BOLT_SHEAR
    )
    assert tuple(cast(PhysicalQuantity, item.demand) for item in shear_results) == tuple(
        item.magnitude for item in result.per_bolt_demands
    )
    bearing_results = tuple(
        item
        for item in result.supported_results
        if item.limit_state is MultiRowCheckFamily.PIN_BEARING
    )
    assert tuple(
        _decimal_serialized(cast(Decimal, item.utilization)) for item in bearing_results
    ) == (
        "0.211403306560",
        "0.233597733796",
        "0.211403306560",
        "0.233597733796",
    )


def test_large_eccentric_bearing_shift_is_transverse_and_known_fail_wins() -> None:
    result = calculate_eccentric_resistance_handoff(_handoff_input(total="10", offset_v="2"))
    assert result.coverage is ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    assert result.numerical_comparison is NumericalComparison.FAIL
    assert result.overall_disposition is MultiRowOverallDisposition.FAIL
    assert all(
        item.material_direction is MaterialDirection.TRANSVERSE
        and item.property_kind is FRPPropertyKind.FBR_T
        for item in result.bearing_selections
    )
    bearing = tuple(
        item
        for item in result.supported_results
        if item.limit_state is MultiRowCheckFamily.PIN_BEARING
    )
    assert tuple(_decimal_serialized(cast(Decimal, item.utilization)) for item in bearing) == (
        "1.234567901235",
        "2.760577750000",
        "1.234567901235",
        "2.760577750000",
    )
    assert set(result.unsupported_required_check_ids) == {
        "first-row",
        "interrow:1",
        "interrow:2",
    }


def test_same_bolt_selects_different_bearing_families_for_two_layer_lw_axes() -> None:
    base = _scaled_bundle("10")
    first_layer = base.layers[0]
    second_layer = replace(first_layer, layer_id="LAYER-V", component_id="COMPONENT-V")
    bolts = tuple(replace(item, layer_ids=("LAYER-1", "LAYER-V")) for item in base.bolts)
    target = bolts[0]
    checks = (
        _check(
            "bearing-u",
            MultiRowCheckFamily.PIN_BEARING,
            MultiRowEquationMethod.PIN_BEARING,
            layer_id="LAYER-1",
            bolt_id=target.bolt_id,
        ),
        _check(
            "bearing-v",
            MultiRowCheckFamily.PIN_BEARING,
            MultiRowEquationMethod.PIN_BEARING,
            layer_id="LAYER-V",
            bolt_id=target.bolt_id,
        ),
    )
    bundle = replace(
        base,
        layers=(first_layer, second_layer),
        bolts=bolts,
        checks=checks,
        required_checks=MultiRowRequiredCheckContract(tuple(item.check_id for item in checks)),
    )
    value = _handoff_input(total="10", offset_v="2", bundle=bundle)
    value = replace(
        value,
        layer_axes=(
            LayerBearingAxisContext("LAYER-1", (Decimal(1), Decimal(0)), ("LW-U",)),
            LayerBearingAxisContext("LAYER-V", (Decimal(0), Decimal(1)), ("LW-V",)),
        ),
    )
    result = calculate_eccentric_resistance_handoff(value)
    selected = tuple(item for item in result.bearing_selections if item.bolt_id == target.bolt_id)
    assert tuple(item.material_direction for item in selected) == (
        MaterialDirection.TRANSVERSE,
        MaterialDirection.LONGITUDINAL,
    )
    assert tuple(
        _decimal_serialized(cast(Decimal, item.utilization)) for item in result.supported_results
    ) == (
        "1.234567901235",
        "0.740740740741",
    )


@pytest.mark.parametrize(
    ("vector", "angle", "direction"),
    [
        (("1", "0"), "0.000000000000", MaterialDirection.LONGITUDINAL),
        (
            ("0.996194698092", "0.087155742748"),
            "5.000000000018",
            MaterialDirection.LONGITUDINAL,
        ),
        (
            ("0.996194696571", "0.087155760135"),
            "5.000001000024",
            MaterialDirection.TRANSVERSE,
        ),
        (("0", "1"), "90.000000000000", MaterialDirection.TRANSVERSE),
    ],
)
def test_direction_boundary_is_decimal_exact_and_uses_no_binary_float(
    vector: tuple[str, str], angle: str, direction: MaterialDirection
) -> None:
    force = (Decimal(vector[0]), Decimal(vector[1]))
    axis = (Decimal(1), Decimal(0))
    assert _decimal_serialized(handoff_module._acute_angle_degrees(force, axis)) == angle
    assert handoff_module._material_direction(force, axis) is direction


def test_force_and_axis_reversal_preserve_sign_independent_acute_direction() -> None:
    force = (Decimal("3"), Decimal("0.1"))
    axis = (Decimal(1), Decimal(0))
    expected = handoff_module._material_direction(force, axis)
    assert handoff_module._material_direction((-force[0], -force[1]), axis) is expected
    assert handoff_module._material_direction(force, (-axis[0], -axis[1])) is expected
    assert handoff_module._acute_angle_degrees((-force[0], -force[1]), axis) == (
        handoff_module._acute_angle_degrees(force, axis)
    )


def test_zero_demand_bolt_has_no_angle_bearing_property_or_utilization() -> None:
    value = _handoff_input(offset_v="0.1")
    scenario = value.demand_result.scenarios[0]
    zero = replace(
        scenario.per_bolt[0],
        total_force=InPlaneQuantityVector(
            PhysicalQuantity.of(0, Unit.KIP), PhysicalQuantity.of(0, Unit.KIP)
        ),
        total_force_magnitude=PhysicalQuantity.of(0, Unit.KIP),
    )
    parent = replace(
        value.demand_result,
        scenarios=(replace(scenario, per_bolt=(zero, *scenario.per_bolt[1:])),),
    )
    result = calculate_eccentric_resistance_handoff(replace(value, demand_result=parent))
    actual = result.per_bolt_demands[0]
    selection = result.bearing_selections[0]
    assert actual.bearing_force_direction is BearingForceDirection.UNDEFINED_ZERO_DEMAND
    assert selection.direction is BearingForceDirection.UNDEFINED_ZERO_DEMAND
    assert selection.angle_degrees is None
    assert selection.material_direction is None
    assert selection.property_kind is None
    assert selection.property_entry_id is None
    assert selection.property_source_document is None
    zero_checks = tuple(
        item for item in result.checks if item.check_id in {"shear:bolt:1", "bearing:bolt:1"}
    )
    assert all(
        item.availability is MultiRowResultAvailability.NOT_APPLICABLE for item in zero_checks
    )
    assert all(item.resistance_result is None for item in zero_checks)


def test_matched_and_unmatched_block_shear_contexts_are_explicit() -> None:
    base = _scaled_bundle("6")
    block_plan = base.block_shear_plans.candidates[0]
    check = _check(
        "block",
        MultiRowCheckFamily.BLOCK_SHEAR,
        MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14A,
        demand="6",
        layer_id="LAYER-1",
        plan=block_plan,
    )
    bundle = replace(
        base,
        checks=(check,),
        required_checks=MultiRowRequiredCheckContract((check.check_id,)),
    )
    plan = replace(
        block_plan,
        gross_shear_length=PhysicalQuantity.of("8", Unit.IN),
        net_shear_length=PhysicalQuantity.of("12.87", Unit.IN),
        gross_tension_length=PhysicalQuantity.of("2.75", Unit.IN),
        net_tension_length=PhysicalQuantity.of("2.124", Unit.IN),
        gross_shear_area=PhysicalQuantity.of("6", Unit.IN2),
        net_shear_area=PhysicalQuantity.of("4.82625", Unit.IN2),
        gross_tension_area=PhysicalQuantity.of("1.03125", Unit.IN2),
        net_tension_area=PhysicalQuantity.of("0.7965", Unit.IN2),
        shear_net_to_gross=Decimal("0.804375"),
        tension_net_to_gross=Decimal("0.772363636364"),
    )
    eccentricity = replace(
        cast(BlockShearEccentricityContext, bundle.eccentricity),
        signed_eccentricity=PhysicalQuantity.of("0.001", Unit.IN),
        classification=BlockShearEccentricityClassification.ECCENTRIC,
    )
    check = replace(check, block_plan=plan)
    bundle = replace(
        bundle,
        block_shear_plans=replace(bundle.block_shear_plans, candidates=(plan,)),
        checks=(check,),
        eccentricity=eccentricity,
    )
    evidence = BlockShearCompatibilityEvidence(
        BlockShearCompatibilityStatus.MATCHED,
        "MATCH-1",
        "ACTION-SOURCE-1",
        bundle.physical_geometry.interface_id,
        bundle.signed_demand.source_id,
        bundle.physical_geometry.interface_id,
        eccentricity.geometric_reference,
        eccentricity.source_geometry_ids,
        (check.check_id,),
    )
    matched = calculate_eccentric_resistance_handoff(
        _handoff_input(total="6", offset_v="0.1", bundle=bundle, block=evidence)
    )
    assert matched.checks[0].availability is MultiRowResultAvailability.CALCULATED
    assert _serialized(
        cast(PhysicalQuantity, matched.supported_results[0].design_resistance), Unit.KIP
    ) == ("11.644256250000")
    assert _decimal_serialized(cast(Decimal, matched.supported_results[0].utilization)) == (
        "0.515275503320"
    )
    assert any(
        warning.code.value == "LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS"
        for warning in matched.supported_results[0].warnings
    )
    assert matched.resistance_warnings == matched.supported_results[0].warnings
    assert matched.qualification is QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
    unmatched = calculate_eccentric_resistance_handoff(
        _handoff_input(
            total="6",
            offset_v="0.1",
            bundle=bundle,
            block=replace(evidence, status=BlockShearCompatibilityStatus.UNPROVEN),
        )
    )
    assert unmatched.unsupported_required_check_ids == ("block",)
    assert unmatched.warnings[0].code is (
        ResistanceHandoffWarningCode.BLOCK_SHEAR_FORCE_LINE_COMPATIBILITY_NOT_PROVEN
    )
    assert unmatched.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED


def test_member_moment_and_missing_normal_axis_transfer_block_ordinary_pass() -> None:
    moment = calculate_eccentric_resistance_handoff(
        _handoff_input(offset_v="0.1", member_moment="1")
    )
    assert moment.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    assert moment.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL in {
        item.code for item in moment.parent_action_transfer_warnings
    }
    bolt = _scaled_bundle().bolts[0]
    axis_checks = (
        _check(
            "combined",
            MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
            MultiRowEquationMethod.BOLT_COMBINED_TENSION_SHEAR,
            bolt_id=bolt.bolt_id,
        ),
        _check(
            "pull-through",
            MultiRowCheckFamily.PULL_THROUGH,
            MultiRowEquationMethod.PULL_THROUGH,
            bolt_id=bolt.bolt_id,
            layer_id="LAYER-1",
        ),
    )
    bundle = _scaled_bundle(checks=axis_checks)
    missing = calculate_eccentric_resistance_handoff(
        _handoff_input(normal="1", offset_v="0.1", bundle=bundle)
    )
    assert missing.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    assert missing.incomplete_required_check_ids == ("combined", "pull-through")
    assert all(item.resistance_result is None for item in missing.checks)


def test_explicit_axis_demand_is_consumed_for_combined_and_pullthrough_not_generated() -> None:
    bolt = _scaled_bundle().bolts[0]
    checks = (
        _check(
            "tension",
            MultiRowCheckFamily.BOLT_TENSION,
            MultiRowEquationMethod.BOLT_TENSION,
            bolt_id=bolt.bolt_id,
        ),
        _check(
            "combined",
            MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
            MultiRowEquationMethod.BOLT_COMBINED_TENSION_SHEAR,
            bolt_id=bolt.bolt_id,
        ),
        _check(
            "pull-through",
            MultiRowCheckFamily.PULL_THROUGH,
            MultiRowEquationMethod.PULL_THROUGH,
            bolt_id=bolt.bolt_id,
            layer_id="LAYER-1",
        ),
    )
    bundle = _scaled_bundle(checks=checks)
    explicit = ExplicitBoltAxisDemand(
        bolt.bolt_id,
        PhysicalQuantity.of("0.1", Unit.KIP),
        "EXPLICIT-AXIS-1",
        "accepted resolved bolt-axis demand",
        True,
    )
    result = calculate_eccentric_resistance_handoff(
        _handoff_input(normal="1", offset_v="0.1", bundle=bundle, explicit=(explicit,))
    )
    assert result.coverage is ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    assert result.incomplete_required_check_ids == ()
    assert all(item.availability is MultiRowResultAvailability.CALCULATED for item in result.checks)
    assert all(item.resistance_result is not None for item in result.checks)
    combined = next(item for item in result.checks if item.check_id == "combined")
    assert combined.demand_source is (
        ResistanceHandoffDemandSource.STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE
    )
    assert combined.axis_demand_source is (ResistanceHandoffDemandSource.EXPLICIT_BOLT_AXIS_TENSION)
    assert all(
        cast(
            PhysicalQuantity,
            cast(MultiRowCheckResult, item.resistance_result).demand,
        )
        == explicit.demand
        for item in result.checks
    )
    assert {warning.code for warning in result.warnings} == {
        ResistanceHandoffWarningCode.EXPLICIT_BOLT_AXIS_DEMAND_CONSUMED_NOT_GENERATED
    }


def test_status_only_checks_reuse_slice_2_and_preserve_or_strengthen_qualification() -> None:
    check = _check(
        "qualification",
        MultiRowCheckFamily.QUALIFICATION,
        MultiRowEquationMethod.STATUS_ONLY,
        availability=PlanAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        applicability=MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
        qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    )
    bundle = _scaled_bundle(checks=(check,))
    result = calculate_eccentric_resistance_handoff(_handoff_input(offset_v="0.1", bundle=bundle))
    assert result.checks[0].demand_source is ResistanceHandoffDemandSource.STATUS_ONLY
    assert result.checks[0].availability is (
        MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert result.qualification is (QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED)


def test_fingerprint_is_deterministic_and_display_free() -> None:
    value = _handoff_input(offset_v="0.1")
    first = calculate_eccentric_resistance_handoff(value)
    second = calculate_eccentric_resistance_handoff(value)
    assert first == second
    assert len(first.result_fingerprint) == 64
    assert resistance_handoff_input_fingerprint(value) == resistance_handoff_input_fingerprint(
        value
    )
    assert canonical_resistance_handoff_input_json(
        value
    ) == canonical_resistance_handoff_input_json(value)
    one = ResistanceHandoffFingerprintEnvelope(value, display_unit_profile="US", camera_state={})
    two = ResistanceHandoffFingerprintEnvelope(
        value,
        display_unit_profile="SI",
        display_rounding="12",
        camera_state={"x": 1},
        ui_selection="bolt",
        request_timestamp="tomorrow",
    )
    assert handoff_module._sha256(one) == handoff_module._sha256(two)
    changed_parent = replace(
        value.demand_result,
        result_fingerprint="f" * 64,
    )
    assert (
        calculate_eccentric_resistance_handoff(
            replace(value, demand_result=changed_parent)
        ).result_fingerprint
        != first.result_fingerprint
    )
    compatibility = BlockShearCompatibilityEvidence(
        BlockShearCompatibilityStatus.UNPROVEN,
        "COMPATIBILITY-A",
        value.demand_result.action_source_id,
        value.demand_result.interface_frame.interface_id,
        value.execution_bundle.signed_demand.source_id,
        value.execution_bundle.physical_geometry.interface_id,
        "UNPROVEN",
        ("GEOMETRY",),
        (),
    )
    assert (
        calculate_eccentric_resistance_handoff(
            replace(value, block_shear_compatibility=compatibility)
        ).result_fingerprint
        != first.result_fingerprint
    )


def test_supported_bearing_utilization_is_monotonic_at_fixed_direction() -> None:
    lower = calculate_eccentric_resistance_handoff(_handoff_input(total="3", offset_v="0.1"))
    higher = calculate_eccentric_resistance_handoff(_handoff_input(total="4", offset_v="0.1"))
    lower_bearing = tuple(
        cast(Decimal, item.utilization)
        for item in lower.supported_results
        if item.limit_state is MultiRowCheckFamily.PIN_BEARING
    )
    higher_bearing = tuple(
        cast(Decimal, item.utilization)
        for item in higher.supported_results
        if item.limit_state is MultiRowCheckFamily.PIN_BEARING
    )
    assert all(high > low for low, high in zip(lower_bearing, higher_bearing, strict=True))
    assert tuple(item.material_direction for item in lower.bearing_selections) == tuple(
        item.material_direction for item in higher.bearing_selections
    )


def test_full_legacy_collinear_authorizes_existing_concentric_block_shear() -> None:
    result = calculate_eccentric_resistance_handoff(_handoff_input(total="2", bundle=_bundle()))
    block = next(
        item
        for item in result.supported_results
        if item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR
    )
    expected = next(
        item
        for item in cast(MultiRowCalculationResult, result.legacy_result).results
        if item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR
    )
    assert result.coverage is ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR
    assert block == expected


def test_invalid_parent_scenario_unavailable_parent_and_legacy_demand_mismatch_fail_closed() -> (
    None
):
    value = _handoff_input(offset_v="0.1")
    with pytest.raises(ValueError, match="scenario_id"):
        calculate_eccentric_resistance_handoff(replace(value, scenario_id="missing"))
    scenario = replace(
        value.demand_result.scenarios[0],
        availability=DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED,
    )
    unavailable = calculate_eccentric_resistance_handoff(
        replace(value, demand_result=replace(value.demand_result, scenarios=(scenario,)))
    )
    assert unavailable.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    assert set(unavailable.incomplete_required_check_ids) == set(
        value.execution_bundle.required_checks.required_check_ids
    )
    assert {item.warnings[0].code for item in unavailable.checks} == {
        ResistanceHandoffWarningCode.PARENT_DEMAND_RESULT_NOT_CALCULATED
    }
    concentric = _handoff_input()
    mismatched_bolt = replace(
        concentric.execution_bundle.bolts[0],
        in_plane_demand=PhysicalQuantity.of("0.8", Unit.KIP),
    )
    mismatched = replace(
        concentric,
        execution_bundle=replace(
            concentric.execution_bundle,
            bolts=(mismatched_bolt, *concentric.execution_bundle.bolts[1:]),
        ),
    )
    with pytest.raises(ValueError, match="identical inherited"):
        calculate_eccentric_resistance_handoff(mismatched)


def test_public_contract_validation_and_decimal_canonicalizer_reject_bad_values() -> None:
    value = _handoff_input(offset_v="0.1")
    with pytest.raises(TypeError, match="handoff_input"):
        calculate_eccentric_resistance_handoff(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="value"):
        resistance_handoff_input_fingerprint(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="value"):
        canonical_resistance_handoff_input_json(object())  # type: ignore[arg-type]
    assert handoff_module._canonicalize(7) == "7"
    with pytest.raises(TypeError, match="binary floats"):
        handoff_module._canonicalize(1.0)
    with pytest.raises(TypeError, match="Unsupported resistance-handoff"):
        handoff_module._canonicalize(object())
    with pytest.raises(ValueError, match="approved RC1"):
        replace(value.versions, resistance_handoff_engine_version="changed")
    with pytest.raises(TypeError, match="lw_axis"):
        LayerBearingAxisContext("LAYER", cast(tuple[Decimal, Decimal], (Decimal(1),)), ("G",))
    with pytest.raises(ValueError, match="cannot be zero"):
        LayerBearingAxisContext("LAYER", (Decimal(0), Decimal(0)), ("G",))
    with pytest.raises(ValueError, match="nonnegative force"):
        ExplicitBoltAxisDemand("B", PhysicalQuantity.of(-1, Unit.KIP), "S", "B", True)
    with pytest.raises(TypeError, match="Boolean"):
        ExplicitBoltAxisDemand("B", PhysicalQuantity.of(1, Unit.KIP), "S", "B", cast(bool, 1))


def test_handoff_module_is_pure_and_has_no_golden_api_application_or_frontend_access() -> None:
    repository_root = Path(__file__).parents[3]
    path = repository_root / "backend/src/frp_master_connection/calculation/resistance_handoff.py"
    source = path.read_text(encoding="utf-8")
    forbidden = (
        "tests.golden",
        "calculation_slice_3_resistance_handoff_rc1.json",
        "frp_master_connection.api",
        "frp_master_connection.application",
        "random.",
        "datetime.now",
        "open(",
        "socket",
        "prying",
    )
    assert all(item not in source for item in forbidden)
    assert "calculate_eccentric_bolt_group_demand" not in source
    assert "bolt_shear_resistance" not in source
    assert "pin_bearing_resistance" not in source
    application_path = (
        repository_root / "backend/src/frp_master_connection/application/multirow_orchestration.py"
    )
    application_source = application_path.read_text(encoding="utf-8")
    # Stage 3.3A adds one public resolved-demand seam while retaining the accepted paths.
    assert application_source.count("calculate_eccentric_resistance_handoff") == 4
    api_sources = tuple((repository_root / "backend/src/frp_master_connection/api").rglob("*.py"))
    frontend_sources = tuple((repository_root / "frontend/src").rglob("*"))
    combined = "\n".join(
        source_path.read_text(encoding="utf-8")
        for source_path in (*api_sources, *frontend_sources)
        if source_path.is_file()
    )
    assert "calculate_eccentric_resistance_handoff" not in combined


def test_exact_parent_geometry_and_identity_contracts_reject_mismatch() -> None:
    value = _handoff_input(offset_v="0.1")
    with pytest.raises(ValueError, match="interface identities"):
        replace(
            value,
            demand_result=replace(
                value.demand_result,
                interface_frame=replace(value.demand_result.interface_frame, interface_id="OTHER"),
            ),
        )
    fewer_bolts = replace(
        value.demand_result,
        bolts=value.demand_result.bolts[:-1],
    )
    with pytest.raises(ValueError, match="bolt identities"):
        replace(value, demand_result=fewer_bolts)
    with pytest.raises(ValueError, match="Every resistance layer"):
        replace(value, layer_axes=())


def test_no_duplicate_layer_axis_axis_demand_or_source_identity_is_accepted() -> None:
    value = _handoff_input(offset_v="0.1")
    axis = value.layer_axes[0]
    with pytest.raises(ValueError, match="layer-axis IDs"):
        replace(value, layer_axes=(axis, axis))
    bolt_id = value.execution_bundle.bolts[0].bolt_id
    explicit = ExplicitBoltAxisDemand(bolt_id, PhysicalQuantity.of(0, Unit.KIP), "S", "B", True)
    with pytest.raises(ValueError, match="axis-demand IDs"):
        replace(value, explicit_axis_demands=(explicit, explicit))
    with pytest.raises(ValueError, match="identify a physical bolt"):
        replace(value, explicit_axis_demands=(replace(explicit, bolt_id="UNKNOWN"),))
    with pytest.raises(ValueError, match="source_geometry_ids"):
        LayerBearingAxisContext("LAYER", (Decimal(1), Decimal(0)), ("G", "G"))


def test_block_compatibility_requires_every_stable_identity() -> None:
    value = _handoff_input(offset_v="0.1")
    check = value.execution_bundle.checks[0]
    evidence = BlockShearCompatibilityEvidence(
        BlockShearCompatibilityStatus.MATCHED,
        "MATCH",
        value.demand_result.action_source_id,
        value.demand_result.interface_frame.interface_id,
        value.execution_bundle.signed_demand.source_id,
        value.execution_bundle.physical_geometry.interface_id,
        cast(
            BlockShearEccentricityContext, value.execution_bundle.eccentricity
        ).geometric_reference,
        cast(
            BlockShearEccentricityContext, value.execution_bundle.eccentricity
        ).source_geometry_ids,
        (check.check_id,),
    )
    assert handoff_module._block_compatible(
        replace(value, block_shear_compatibility=evidence), check
    )
    fields_to_change = (
        "action_source_id",
        "demand_interface_id",
        "resistance_source_id",
        "resistance_interface_id",
        "eccentricity_reference",
        "source_geometry_ids",
        "compatible_check_ids",
    )
    for name in fields_to_change:
        replacement: object = ("OTHER",) if name.endswith("ids") else "OTHER"
        changed = replace(evidence, **{name: replacement})  # type: ignore[arg-type]
        assert not handoff_module._block_compatible(
            replace(value, block_shear_compatibility=changed), check
        )
    assert not handoff_module._block_compatible(value, check)
    assert not handoff_module._block_compatible(
        replace(value, execution_bundle=replace(value.execution_bundle, eccentricity=None)), check
    )


def test_defensive_contract_branches_and_fail_closed_helpers() -> None:
    value = _handoff_input(offset_v="0.1")
    evidence = BlockShearCompatibilityEvidence(
        BlockShearCompatibilityStatus.UNPROVEN,
        "MATCH",
        "ACTION",
        "INTERFACE",
        "RESISTANCE",
        "INTERFACE",
        "REFERENCE",
        ("GEOMETRY",),
        (),
    )
    with pytest.raises(TypeError, match="BlockShearCompatibilityStatus"):
        replace(evidence, status=cast(BlockShearCompatibilityStatus, "MATCHED"))
    with pytest.raises(TypeError, match="demand_result"):
        replace(value, demand_result=cast(EccentricDemandResult, object()))
    with pytest.raises(TypeError, match="execution_bundle"):
        replace(value, execution_bundle=cast(MultiRowExecutionBundle, object()))
    with pytest.raises(TypeError, match="block_shear_compatibility"):
        replace(
            value,
            block_shear_compatibility=cast(BlockShearCompatibilityEvidence, object()),
        )
    with pytest.raises(TypeError, match="versions"):
        replace(
            value,
            versions=cast(ResistanceHandoffVersionContext, object()),
        )
    with pytest.raises(ValueError, match="accepted parent bolt ID"):
        handoff_module._scenario_bolt(value.demand_result.scenarios[0], "UNKNOWN")
    concentric = _handoff_input()
    with pytest.raises(ValueError, match="identical accepted material direction"):
        calculate_eccentric_resistance_handoff(
            replace(
                concentric,
                layer_axes=(
                    replace(
                        concentric.layer_axes[0],
                        lw_axis=(Decimal(0), Decimal(1)),
                    ),
                ),
            )
        )

    qualified_checks = tuple(
        replace(item, qualification=QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE)
        for item in value.execution_bundle.checks
    )
    engineering = replace(
        value,
        demand_result=replace(
            value.demand_result,
            qualification=QualificationDisposition.ENGINEERING_REVIEW_REQUIRED,
        ),
        execution_bundle=replace(value.execution_bundle, checks=qualified_checks),
    )
    assert handoff_module._qualification(engineering) is (
        QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
    )
    assert (
        handoff_module._overall(
            ResistanceHandoffCoverage.PARTIAL_ECCENTRIC,
            (),
            NumericalComparison.PASS,
            QualificationDisposition.ENGINEERING_REVIEW_REQUIRED,
        )
        is MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED
    )
    invalid = ResistanceCheckHandoff(
        "invalid",
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowResultAvailability.INVALID_GEOMETRY,
        ResistanceHandoffDemandSource.STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE,
        None,
        (),
    )
    assert (
        handoff_module._overall(
            ResistanceHandoffCoverage.PARTIAL_ECCENTRIC,
            (invalid,),
            NumericalComparison.NOT_EVALUATED,
            QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE,
        )
        is MultiRowOverallDisposition.INVALID_GEOMETRY
    )

    assert handoff_module._canonicalize(PhysicalQuantity.of("1", Unit.KIP)) == {
        "dimension": "FORCE",
        "magnitude": "4448.2216152605",
        "unit": "N",
    }
    with pytest.raises(ValueError, match="nonempty text"):
        handoff_module._require_text("", "identity")
    with pytest.raises(ValueError, match="immutable nonempty tuple"):
        handoff_module._require_unique_text_tuple((), "identities")
    with pytest.raises(ValueError, match="contain nonempty text"):
        handoff_module._require_unique_text_tuple(("",), "identities")
    with pytest.raises(TypeError, match="immutable tuple"):
        handoff_module._require_typed_tuple(cast(tuple[object, ...], []), str, "values")
