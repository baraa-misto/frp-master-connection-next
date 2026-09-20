"""Stage 2.1B orchestration, unit-equivalence, and invariance tests."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    ApplicabilityReasonCode,
    DemandDistributionStatus,
    DemandSourceKind,
    EndUseFactors,
    FinalCalculationResult,
    FinalResultAvailability,
    LapConfiguration,
    LimitState,
    NumericalComparison,
    PhysicalQuantity,
    SingleBoltCalculationResult,
    SingleBoltPlanningInput,
    ThreadStatus,
    ThreadStatusAssignment,
    Unit,
    calculate_single_bolt,
    create_lap_factor_plan,
)
from frp_master_connection.calculation.evaluation import _comparison
from tests.calculation.numerical_fixtures import (
    b1_input,
    demand,
    direction_90_input,
    j1_input,
    p1_input,
    p2a_input,
    p2b_input,
    pt1_input,
    to_si,
)


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


def _design(result: FinalCalculationResult) -> PhysicalQuantity:
    assert result.design_resistance is not None
    return result.design_resistance


@pytest.mark.parametrize(
    "factory",
    [
        p1_input,
        pt1_input,
        p2a_input,
        p2b_input,
        j1_input,
        lambda: j1_input(compression=True),
        b1_input,
        direction_90_input,
    ],
)
def test_every_golden_case_is_exactly_equivalent_from_converted_si_quantities(
    factory: Callable[[], SingleBoltPlanningInput],
) -> None:
    us_input = factory()
    si_input = to_si(us_input)
    us = calculate_single_bolt(us_input)
    si = calculate_single_bolt(si_input)
    assert si.input_fingerprint == us.input_fingerprint
    assert si.calculation_engine_version == us.calculation_engine_version
    assert si.engineering_rule_set_version == us.engineering_rule_set_version
    assert si.aggregate_status is us.aggregate_status
    assert si.governing_check_ids == us.governing_check_ids
    assert len(si.results) == len(us.results)
    for us_result, si_result in zip(us.results, si.results, strict=True):
        assert si_result.plan == us_result.plan
        assert si_result.availability is us_result.availability
        assert si_result.numerical_comparison is us_result.numerical_comparison
        assert si_result.demand == us_result.demand
        assert si_result.nominal_resistance == us_result.nominal_resistance
        assert si_result.design_resistance == us_result.design_resistance
        assert si_result.utilization == us_result.utilization
        assert si_result.source_snapshot == us_result.source_snapshot


def test_calculation_is_pure_deterministic_and_preserves_plan_order() -> None:
    source = p2a_input()
    retained = deepcopy(source)
    first = calculate_single_bolt(source)
    second = calculate_single_bolt(source)
    assert source == retained
    assert first == second
    assert tuple(result.plan for result in first.results) == first.planning_result.checks
    assert first.input_fingerprint == source.input_fingerprint


def test_exact_boundary_passes_slightly_greater_fails_and_zero_utilization_passes() -> None:
    equality = calculate_single_bolt(replace(p1_input(), demand=demand("3.375")))
    bearing_equal = _result(equality, LimitState.PIN_BEARING, "P1")
    assert bearing_equal.numerical_comparison is NumericalComparison.PASS
    assert bearing_equal.utilization == Decimal(1)

    greater = calculate_single_bolt(replace(p1_input(), demand=demand("3.375000000001")))
    bearing_greater = _result(greater, LimitState.PIN_BEARING, "P1")
    assert bearing_greater.numerical_comparison is NumericalComparison.FAIL
    assert bearing_greater.utilization is not None
    assert bearing_greater.utilization > 1

    zero_comparison, zero_utilization, zero_warnings = _comparison(
        PhysicalQuantity.of("0", Unit.KIP), PhysicalQuantity.of("1", Unit.KIP)
    )
    assert zero_comparison is NumericalComparison.PASS
    assert zero_utilization == 0
    assert zero_warnings == ()


def test_nonpositive_design_fails_without_clamping_or_utilization() -> None:
    comparison, utilization, warnings = _comparison(
        PhysicalQuantity.of("1", Unit.KIP), PhysicalQuantity.of("-0.1", Unit.KIP)
    )
    assert comparison is NumericalComparison.FAIL
    assert utilization is None
    assert warnings == ("Calculated design resistance is nonpositive and was not clamped.",)


def test_known_failure_precedes_unsupported_and_unsupported_prevents_pass() -> None:
    failed = calculate_single_bolt(p2b_input())
    assert failed.aggregate_status is AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK
    passing_known = calculate_single_bolt(replace(p2b_input(), demand=demand("0.5")))
    assert passing_known.aggregate_status is AggregatePlanningStatus.CALCULATION_NOT_SUPPORTED


def test_demand_thickness_hole_and_strength_monotonicity() -> None:
    baseline_input = p1_input()
    baseline = calculate_single_bolt(baseline_input)
    higher_demand = calculate_single_bolt(replace(baseline_input, demand=demand("3.1")))
    for state in (LimitState.PIN_BEARING, LimitState.NET_SECTION_TENSION, LimitState.SHEAR_OUT):
        low = _result(baseline, state, "P1")
        high = _result(higher_demand, state, "P1")
        assert low.utilization is not None
        assert high.utilization is not None
        assert high.utilization >= low.utilization

    thicker_mapping = replace(
        baseline_input.layers[0].mapping,
        layer_thickness=PhysicalQuantity.of("0.5", Unit.IN),
    )
    thicker = calculate_single_bolt(
        replace(
            baseline_input,
            layers=(replace(baseline_input.layers[0], mapping=thicker_mapping),),
        )
    )
    assert _design(_result(thicker, LimitState.PIN_BEARING, "P1")) >= _design(
        _result(baseline, LimitState.PIN_BEARING, "P1")
    )

    larger_hole_mapping = replace(
        baseline_input.layers[0].mapping,
        hole_diameter=PhysicalQuantity.of("0.6", Unit.IN),
    )
    larger_hole = calculate_single_bolt(
        replace(
            baseline_input,
            layers=(replace(baseline_input.layers[0], mapping=larger_hole_mapping),),
        )
    )
    for state in (LimitState.NET_SECTION_TENSION, LimitState.SHEAR_OUT):
        assert _design(_result(larger_hole, state, "P1")) <= _design(_result(baseline, state, "P1"))

    strengthened_entries = tuple(
        replace(entry, value=entry.value * Decimal("1.1")) if entry.kind.value == "FBR_L" else entry
        for entry in baseline_input.material.properties
    )
    stronger = calculate_single_bolt(
        replace(
            baseline_input,
            material=replace(baseline_input.material, properties=strengthened_entries),
        )
    )
    assert _design(_result(stronger, LimitState.PIN_BEARING, "P1")) >= _design(
        _result(baseline, LimitState.PIN_BEARING, "P1")
    )


def test_layer_order_and_bolt_axis_patch_provenance_do_not_change_physical_results() -> None:
    source = p2a_input()
    forward = calculate_single_bolt(source)
    reverse_stack = calculate_single_bolt(replace(source, layers=tuple(reversed(source.layers))))
    forward_values = {
        result.plan.check_id: (result.design_resistance, result.utilization)
        for result in forward.results
    }
    reverse_values = {
        result.plan.check_id: (result.design_resistance, result.utilization)
        for result in reverse_stack.results
    }
    assert reverse_values == forward_values
    forward_layer_order = tuple(
        result.plan.layer_id for result in forward.results if result.plan.layer_id is not None
    )
    reverse_layer_order = tuple(
        result.plan.layer_id for result in reverse_stack.results if result.plan.layer_id is not None
    )
    assert reverse_layer_order == tuple(reversed(forward_layer_order))

    reversed_patches = tuple(
        replace(
            layer,
            mapping=replace(
                layer.mapping,
                source_surface_patch_ids=(
                    layer.mapping.source_surface_patch_ids[1],
                    layer.mapping.source_surface_patch_ids[0],
                ),
            ),
        )
        for layer in source.layers
    )
    reversed_axis = calculate_single_bolt(replace(source, layers=reversed_patches))
    assert {
        result.plan.check_id: (result.design_resistance, result.utilization)
        for result in reversed_axis.results
    } == forward_values
    assert reversed_patches[0].mapping.source_surface_patch_ids == tuple(
        reversed(source.layers[0].mapping.source_surface_patch_ids)
    )


def test_lap_and_end_use_factors_do_not_leak_into_bolt_or_pull_through_equations() -> None:
    pt = pt1_input()
    pt_single = replace(pt, lap_factor=create_lap_factor_plan(LapConfiguration.SINGLE_LAP))
    assert (
        _result(calculate_single_bolt(pt), LimitState.PULL_THROUGH, "P1").design_resistance
        == _result(
            calculate_single_bolt(pt_single), LimitState.PULL_THROUGH, "P1"
        ).design_resistance
    )

    bolt = b1_input()
    altered = replace(
        bolt,
        lap_factor=create_lap_factor_plan(LapConfiguration.SINGLE_LAP),
        end_use_factors=EndUseFactors(
            Decimal("0.8"),
            Decimal("0.9"),
            Decimal("0.7"),
            "fixture",
            ("explicit",),
        ),
    )
    for state in (
        LimitState.BOLT_TENSION,
        LimitState.BOLT_SHEAR,
        LimitState.BOLT_COMBINED_TENSION_SHEAR,
    ):
        assert (
            _result(calculate_single_bolt(bolt), state, None).design_resistance
            == _result(calculate_single_bolt(altered), state, None).design_resistance
        )


def test_zero_and_multiple_shear_planes_fail_closed_with_distinct_statuses() -> None:
    one = b1_input()
    no_plane = replace(
        one,
        fastener=replace(
            one.fastener,
            shear_plane_thread_statuses=(),
            number_of_shear_planes=0,
        ),
    )
    no_plane_result = _result(calculate_single_bolt(no_plane), LimitState.BOLT_SHEAR, None)
    assert no_plane_result.availability is FinalResultAvailability.INCOMPLETE_INPUT
    assert ApplicabilityReasonCode.SHEAR_PLANE_REQUIRED in (
        no_plane_result.plan.applicability_reason_codes
    )

    two_planes = replace(
        one,
        fastener=replace(
            one.fastener,
            shear_plane_thread_statuses=(
                ThreadStatusAssignment("plane-1", ThreadStatus.EXCLUDED),
                ThreadStatusAssignment("plane-2", ThreadStatus.INCLUDED),
            ),
            number_of_shear_planes=2,
        ),
    )
    two_plane_result = _result(calculate_single_bolt(two_planes), LimitState.BOLT_SHEAR, None)
    assert two_plane_result.availability is FinalResultAvailability.CALCULATION_NOT_SUPPORTED
    assert ApplicabilityReasonCode.MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED in (
        two_plane_result.plan.applicability_reason_codes
    )


def test_undistributed_demand_is_preserved_without_numerical_execution() -> None:
    source = p1_input()
    undistributed = replace(
        source.demand,
        source_kind=DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED,
        distribution_status=DemandDistributionStatus.UNRESOLVED,
    )
    result = calculate_single_bolt(replace(source, demand=undistributed))
    assert result.aggregate_status is (
        AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    )
    assert all(
        item.availability is FinalResultAvailability.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
        for item in result.results
        if item.plan.required
    )
    assert all(item.utilization is None for item in result.results if item.plan.required)
    assert result.governing_check_ids == ()
