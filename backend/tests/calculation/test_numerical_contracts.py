"""Fail-closed contract and defensive orchestration tests for Stage 2.1B."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    CalculationReadinessStatus,
    FinalCalculationResult,
    FinalResultAvailability,
    FRPPropertyKind,
    LimitState,
    NumericalComparison,
    PhysicalQuantity,
    QualificationStatus,
    SingleBoltCalculationResult,
    Unit,
    aggregate_calculation_status,
    calculate_single_bolt,
    create_locked_f593_fastener_snapshot,
)
from frp_master_connection.calculation.evaluation import (
    _bolt_result,
    _frp_result,
    _layer,
    _property,
)
from tests.calculation.numerical_fixtures import b1_input, p1_input, pt1_input


def _result(
    calculation: SingleBoltCalculationResult,
    state: LimitState,
    layer_id: str | None,
) -> FinalCalculationResult:
    matches = tuple(
        result
        for result in calculation.results
        if result.plan.limit_state is state and result.plan.layer_id == layer_id
    )
    assert len(matches) == 1
    return matches[0]


def test_layer_input_and_effective_width_fail_closed_contracts() -> None:
    source = p1_input()
    with pytest.raises(TypeError, match="element_form"):
        replace(source.layers[0], element_form="SHAPE")  # type: ignore[arg-type]

    invalid_mapping = replace(
        source.layers[0].mapping,
        effective_width=source.layers[0].mapping.hole_diameter,
    )
    invalid = calculate_single_bolt(
        replace(source, layers=(replace(source.layers[0], mapping=invalid_mapping),))
    )
    net = _result(invalid, LimitState.NET_SECTION_TENSION, "P1")
    assert net.availability is FinalResultAvailability.INVALID_GEOMETRY
    assert invalid.aggregate_status is AggregatePlanningStatus.INVALID_GEOMETRY


def test_final_result_contract_rejects_inconsistent_shapes_and_types() -> None:
    calculated = _result(calculate_single_bolt(p1_input()), LimitState.PIN_BEARING, "P1")
    unavailable = _result(calculate_single_bolt(p1_input()), LimitState.PULL_THROUGH, "P1")
    with pytest.raises(TypeError, match="PlannedCheck"):
        replace(calculated, plan="plan")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="CalculationSourceSnapshot"):
        replace(calculated, source_snapshot="source")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(calculated, warnings=[])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonnegative"):
        replace(calculated, utilization=Decimal("-0.1"))
    with pytest.raises(ValueError, match="requires demand"):
        replace(calculated, demand=None)
    with pytest.raises(ValueError, match="PASS or FAIL"):
        replace(calculated, numerical_comparison=NumericalComparison.NOT_EVALUATED)
    with pytest.raises(ValueError, match="requires utilization"):
        replace(calculated, utilization=None)
    with pytest.raises(ValueError, match="cannot have utilization"):
        replace(
            calculated,
            design_resistance=PhysicalQuantity.of("-1", Unit.KIP),
        )
    with pytest.raises(ValueError, match="cannot contain calculated"):
        replace(unavailable, demand=PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="remain NOT_EVALUATED"):
        replace(unavailable, numerical_comparison=NumericalComparison.PASS)


def test_single_bolt_result_contract_rejects_order_identity_and_version_errors() -> None:
    result = calculate_single_bolt(p1_input())
    with pytest.raises(TypeError, match="immutable tuples"):
        replace(result, results=list(result.results))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuples"):
        replace(result, governing_check_ids=list(result.governing_check_ids))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="planning order"):
        replace(result, results=tuple(reversed(result.results)))
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(result, input_fingerprint="A" * 64)
    with pytest.raises(ValueError, match="versions are required"):
        replace(result, calculation_engine_version="")
    with pytest.raises(ValueError, match="versions are required"):
        replace(result, engineering_rule_set_version="")


def test_aggregate_calculation_status_all_terminal_branches() -> None:
    source = _result(calculate_single_bolt(p1_input()), LimitState.PIN_BEARING, "P1")
    clean_plan = replace(source.plan, qualification_flags=())
    passing = replace(source, plan=clean_plan)
    assert (
        aggregate_calculation_status((passing,), CalculationReadinessStatus.READY)
        is AggregatePlanningStatus.PASS
    )
    failing = replace(passing, numerical_comparison=NumericalComparison.FAIL)
    assert (
        aggregate_calculation_status((failing,), CalculationReadinessStatus.READY)
        is AggregatePlanningStatus.FAIL
    )
    invalid = replace(
        passing,
        plan=replace(clean_plan, readiness_status=CalculationReadinessStatus.INVALID_GEOMETRY),
    )
    assert (
        aggregate_calculation_status((invalid,), CalculationReadinessStatus.READY)
        is AggregatePlanningStatus.INVALID_GEOMETRY
    )
    unavailable = _result(calculate_single_bolt(p1_input()), LimitState.PULL_THROUGH, "P1")
    required_na = replace(unavailable, plan=replace(unavailable.plan, required=True))
    assert (
        aggregate_calculation_status((required_na,), CalculationReadinessStatus.READY)
        is AggregatePlanningStatus.NOT_APPLICABLE
    )
    qualification = replace(
        passing,
        plan=replace(
            clean_plan,
            qualification_flags=(QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,),
        ),
    )
    assert (
        aggregate_calculation_status((qualification,), CalculationReadinessStatus.READY)
        is AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )


def test_defensive_orchestration_guards_reject_impossible_ready_plans() -> None:
    source = p1_input()
    with pytest.raises(ValueError, match="unexpectedly lacks property"):
        _property(source, FRPPropertyKind.FC_T)

    net_plan = _result(calculate_single_bolt(source), LimitState.NET_SECTION_TENSION, "P1").plan
    with pytest.raises(ValueError, match="exactly one planning layer"):
        _layer(source, replace(net_plan, layer_id="missing"))
    with pytest.raises(ValueError, match="width and property"):
        _frp_result(
            replace(
                source,
                layers=(
                    replace(
                        source.layers[0],
                        mapping=replace(source.layers[0].mapping, effective_width=None),
                    ),
                ),
            ),
            net_plan,
        )
    with pytest.raises(ValueError, match="width and property"):
        _frp_result(source, replace(net_plan, required_property_kind=None))

    pull_source = pt1_input()
    pull_plan = _result(calculate_single_bolt(pull_source), LimitState.PULL_THROUGH, "P1").plan
    with pytest.raises(ValueError, match="washer geometry"):
        _frp_result(replace(pull_source, washer=None), pull_plan)

    bolt_source = b1_input()
    bolt_plan = _result(calculate_single_bolt(bolt_source), LimitState.BOLT_SHEAR, None).plan
    with pytest.raises(ValueError, match="explicit Fnt"):
        _bolt_result(
            replace(bolt_source, fastener=create_locked_f593_fastener_snapshot()),
            bolt_plan,
        )


def test_combined_result_is_forced_to_fail_when_pure_shear_fails() -> None:
    source = b1_input()
    high_shear = replace(
        source.demand,
        in_plane_force_vector=replace(source.demand.in_plane_force_vector, x=30.0),
    )
    result = _result(
        calculate_single_bolt(replace(source, demand=high_shear)),
        LimitState.BOLT_COMBINED_TENSION_SHEAR,
        None,
    )
    assert result.numerical_comparison is NumericalComparison.FAIL
    assert "Pure bolt shear comparison also fails." in result.warnings
