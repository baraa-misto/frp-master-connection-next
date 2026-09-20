"""Golden numerical verification through canonical Stage 2.2A orchestration."""

from collections.abc import Callable
from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from frp_master_connection.application import (
    OrchestrationIssueCode,
    SingleBoltOrchestrationRequest,
    evaluate_single_bolt_connection,
)
from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    CalculationReadinessStatus,
    CombinedBoltTrace,
    FinalResultAvailability,
    LimitState,
    MaterialDirectionFamily,
    NumericalComparison,
    PullThroughTrace,
    SingleBoltCalculationResult,
    SingleBoltPlanningInput,
    ThreadStatusAssignment,
    Unit,
    calculate_single_bolt,
)
from frp_master_connection.domain import EngineeringUnitSystem
from tests.application.orchestration_fixtures import (
    CanonicalOrchestrationCase,
    build_j1_case,
    build_j1_visual_case,
    build_plate_case,
)
from tests.calculation.numerical_fixtures import (
    b1_input,
    p1_input,
    p2a_input,
    p2b_input,
    pt1_input,
)
from tests.calculation.test_numerical_golden import (
    SCALE,
    _assert_expected,
    _force,
    _layer_values,
    _result,
)


def _calculation(
    case_request: SingleBoltOrchestrationRequest,
) -> SingleBoltCalculationResult:
    response = evaluate_single_bolt_connection(case_request)
    assert response.calculation_result is not None
    return response.calculation_result


def _rounded_result_signature(
    calculation: SingleBoltCalculationResult,
) -> tuple[tuple[str, str | None, str, Decimal | None, Decimal | None], ...]:
    return tuple(
        (
            result.plan.limit_state.value,
            result.plan.layer_id,
            result.availability.value,
            (
                None
                if result.design_resistance is None
                else result.design_resistance.to(Unit.KIP).magnitude.quantize(
                    SCALE,
                    rounding=ROUND_HALF_EVEN,
                )
            ),
            (
                None
                if result.utilization is None
                else result.utilization.quantize(SCALE, rounding=ROUND_HALF_EVEN)
            ),
        )
        for result in calculation.results
    )


def _direct_signature(
    calculation: SingleBoltCalculationResult,
    layer_mapping: dict[str, str],
) -> tuple[tuple[str, str | None, str, Decimal | None, Decimal | None], ...]:
    return tuple(
        (
            result.plan.limit_state.value,
            _mapped_layer(result.plan.layer_id, layer_mapping),
            result.availability.value,
            (
                None
                if result.design_resistance is None
                else result.design_resistance.to(Unit.KIP).magnitude.quantize(
                    SCALE,
                    rounding=ROUND_HALF_EVEN,
                )
            ),
            (
                None
                if result.utilization is None
                else result.utilization.quantize(SCALE, rounding=ROUND_HALF_EVEN)
            ),
        )
        for result in calculation.results
    )


def _mapped_layer(layer_id: str | None, layer_mapping: dict[str, str]) -> str | None:
    return None if layer_id is None else layer_mapping.get(layer_id, layer_id)


def test_p1_and_pt1_reproduce_every_approved_golden_value_through_orchestration() -> None:
    p1 = _calculation(build_plate_case("P1").request)
    _assert_expected("P1", _layer_values(p1, "layer-A"), "results")
    assert p1.aggregate_status is AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED
    assert p1.governing_check_ids == (
        "interface-1:bolt-1:layer-A:pin_bearing",
        "interface-1:bolt-1:layer-A:cleavage",
    )
    pt1 = _calculation(build_plate_case("PT1").request)
    pull = _result(pt1, LimitState.PULL_THROUGH, "layer-A")
    assert isinstance(pull.equation_trace, PullThroughTrace)
    assert pull.design_resistance is not None
    assert pull.utilization is not None
    _assert_expected(
        "PT1",
        {
            "Rtt_branch_8_4a_nom_kip": _force(pull.equation_trace.branch_8_4a_nominal),
            "Rtt_branch_8_4b_nom_kip": _force(pull.equation_trace.branch_8_4b_nominal),
            "Rtt_design_kip": _force(pull.design_resistance),
            "utilization": pull.utilization,
        },
    )


def test_p2a_and_p2b_preserve_order_direction_factors_and_failure_precedence() -> None:
    response = evaluate_single_bolt_connection(build_plate_case("P2A").request)
    calculation = response.calculation_result
    assert calculation is not None
    assert tuple(item.layer_id for item in response.resolved_layers) == ("layer-A", "layer-B")
    _assert_expected("P2A", _layer_values(calculation, "layer-A"), "layer_A", "results")
    _assert_expected("P2A", _layer_values(calculation, "layer-B"), "layer_B", "results")

    p2b = _calculation(build_plate_case("P2B").request)
    bearing = _result(p2b, LimitState.PIN_BEARING, "layer-B")
    net = _result(p2b, LimitState.NET_SECTION_TENSION, "layer-B")
    shear = _result(p2b, LimitState.SHEAR_OUT, "layer-B")
    cleavage = _result(p2b, LimitState.CLEAVAGE, "layer-B")
    assert bearing.design_resistance is not None
    assert bearing.utilization is not None
    assert net.design_resistance is not None
    assert net.utilization is not None
    assert shear.design_resistance is not None
    assert shear.utilization is not None
    _assert_expected(
        "P2B",
        {
            "Rbr_design_kip": _force(bearing.design_resistance),
            "U_br": bearing.utilization,
            "Rnt_design_kip": _force(net.design_resistance),
            "U_nt": net.utilization,
            "Rsh_design_kip": _force(shear.design_resistance),
            "U_sh": shear.utilization,
        },
        "layer_B",
    )
    assert bearing.plan.selected_direction_family is MaterialDirectionFamily.TRANSVERSE
    assert bearing.numerical_comparison is net.numerical_comparison is NumericalComparison.FAIL
    assert shear.numerical_comparison is NumericalComparison.PASS
    assert cleavage.availability is FinalResultAvailability.CALCULATION_NOT_SUPPORTED
    assert p2b.aggregate_status is AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK


@pytest.mark.parametrize("compression", [False, True])
def test_j1_direct_angle_to_w_geometry_reproduces_approved_behavior(
    compression: bool,
) -> None:
    response = evaluate_single_bolt_connection(build_j1_case(compression=compression).request)
    calculation = response.calculation_result
    assert calculation is not None
    assert response.aggregate_status is (
        AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert tuple(item.physical_element_id for item in response.resolved_layers) == (
        "LEG_1",
        "TOP_FLANGE",
    )
    assert response.resolved_layers[0].code_mapping is not None
    assert response.resolved_layers[1].code_mapping is not None
    assert response.resolved_layers[0].code_mapping.direction_family is (
        MaterialDirectionFamily.LONGITUDINAL
    )
    assert response.resolved_layers[1].code_mapping.direction_family is (
        MaterialDirectionFamily.TRANSVERSE
    )
    if compression:
        for layer_id, fixture_layer in (("layer-A", "angle_leg"), ("layer-B", "w_flange")):
            bearing = _result(calculation, LimitState.PIN_BEARING, layer_id)
            shear = _result(calculation, LimitState.SHEAR_OUT, layer_id)
            assert bearing.design_resistance is not None
            assert bearing.utilization is not None
            assert shear.design_resistance is not None
            assert shear.utilization is not None
            _assert_expected(
                "J1_C",
                {
                    "Rbr_design_kip": _force(bearing.design_resistance),
                    "U_br": bearing.utilization,
                    "Rsh_design_kip": _force(shear.design_resistance),
                    "U_sh": shear.utilization,
                },
                fixture_layer,
            )
            assert (
                _result(calculation, LimitState.NET_SECTION_TENSION, layer_id).availability
                is FinalResultAvailability.NOT_APPLICABLE
            )
            assert _result(calculation, LimitState.CLEAVAGE, layer_id).availability is (
                FinalResultAvailability.NOT_APPLICABLE
            )
    else:
        _assert_expected(
            "J1_T",
            _layer_values(calculation, "layer-A"),
            "angle_leg",
            "results",
        )
        _assert_expected(
            "J1_T",
            _layer_values(calculation, "layer-B", include_cleavage=False),
            "w_flange",
            "results",
        )
        assert _result(calculation, LimitState.CLEAVAGE, "layer-B").availability is (
            FinalResultAvailability.CALCULATION_NOT_SUPPORTED
        )
        assert calculation.governing_check_ids == ("interface-1:bolt-1:layer-B:net_tension",)


@pytest.mark.parametrize("compression", [False, True])
def test_j1_vertical_visual_fixture_preserves_approved_engineering_behavior(
    compression: bool,
) -> None:
    historical = evaluate_single_bolt_connection(build_j1_case(compression=compression).request)
    visual = evaluate_single_bolt_connection(build_j1_visual_case(compression=compression).request)
    assert historical.calculation_result is not None
    assert visual.calculation_result is not None
    assert _rounded_result_signature(visual.calculation_result) == _rounded_result_signature(
        historical.calculation_result
    )
    assert visual.aggregate_status is historical.aggregate_status
    assert visual.governing_check_ids == historical.governing_check_ids
    assert tuple(item.physical_element_id for item in visual.resolved_layers) == (
        "LEG_1",
        "TOP_FLANGE",
    )
    assert tuple(
        item.code_mapping.direction_family
        for item in visual.resolved_layers
        if item.code_mapping is not None
    ) == (MaterialDirectionFamily.LONGITUDINAL, MaterialDirectionFamily.TRANSVERSE)


def test_b1_executes_synthetic_bolt_equations_without_claiming_f593_source() -> None:
    response = evaluate_single_bolt_connection(build_plate_case("B1").request)
    calculation = response.calculation_result
    assert calculation is not None
    shear = _result(calculation, LimitState.BOLT_SHEAR, None)
    combined = _result(calculation, LimitState.BOLT_COMBINED_TENSION_SHEAR, None)
    assert shear.design_resistance is not None
    assert shear.utilization is not None
    assert isinstance(combined.equation_trace, CombinedBoltTrace)
    assert combined.design_resistance is not None
    assert combined.utilization is not None
    trace = combined.equation_trace
    _assert_expected(
        "B1_SYNTHETIC",
        {
            "Ab_in2": trace.area_trace.area.to(Unit.IN2).magnitude,
            "Fnv_ksi": trace.fnv.to(Unit.KSI).magnitude,
            "shear_design_resistance_kip": _force(shear.design_resistance),
            "shear_utilization": shear.utilization,
            "required_shear_stress_ksi": trace.required_shear_stress.to(Unit.KSI).magnitude,
            "modified_tensile_stress_ksi": trace.modified_tensile_stress.to(Unit.KSI).magnitude,
            "combined_tension_design_resistance_kip": _force(combined.design_resistance),
            "combined_tension_utilization": combined.utilization,
        },
    )
    assert response.fastener_snapshot.id == "B1_SYNTHETIC"
    assert "SYNTHETIC" in response.fastener_snapshot.bolt_specification
    assert OrchestrationIssueCode.FASTENER_SOURCE_PENDING not in {
        issue.code for issue in response.issues
    }


@pytest.mark.parametrize(
    ("fixture", "direct", "layer_mapping"),
    [
        ("P1", p1_input, {"P1": "layer-A"}),
        ("PT1", pt1_input, {"P1": "layer-A"}),
        ("P2A", p2a_input, {"layer_A": "layer-A", "layer_B": "layer-B"}),
        ("P2B", p2b_input, {"layer_A": "layer-A", "layer_B": "layer-B"}),
        ("B1", b1_input, {"B1": "layer-A"}),
    ],
)
def test_stage_2_1b_numerical_regression_is_unchanged(
    fixture: str,
    direct: Callable[[], SingleBoltPlanningInput],
    layer_mapping: dict[str, str],
) -> None:
    orchestrated = _calculation(build_plate_case(fixture).request)
    baseline = calculate_single_bolt(direct())
    assert _rounded_result_signature(orchestrated) == _direct_signature(
        baseline,
        layer_mapping,
    )


def test_us_si_complete_path_equivalence_for_p1_p2a_and_j1_t() -> None:
    builders: tuple[Callable[[EngineeringUnitSystem], CanonicalOrchestrationCase], ...] = (
        _p1_unit_case,
        _p2a_unit_case,
        _j1_unit_case,
    )
    for builder in builders:
        us_response = evaluate_single_bolt_connection(
            builder(EngineeringUnitSystem.US_CUSTOMARY).request
        )
        si_response = evaluate_single_bolt_connection(builder(EngineeringUnitSystem.SI).request)
        assert us_response.calculation_result is not None
        assert si_response.calculation_result is not None
        assert us_response.aggregate_status is si_response.aggregate_status
        assert us_response.governing_check_ids == si_response.governing_check_ids
        assert tuple(
            item.code_mapping.direction_family
            for item in us_response.resolved_layers
            if item.code_mapping is not None
        ) == tuple(
            item.code_mapping.direction_family
            for item in si_response.resolved_layers
            if item.code_mapping is not None
        )
        assert _rounded_result_signature(us_response.calculation_result) == (
            _rounded_result_signature(si_response.calculation_result)
        )
    p1_us = evaluate_single_bolt_connection(build_plate_case("P1").request)
    p1_si = evaluate_single_bolt_connection(
        build_plate_case("P1", unit_system=EngineeringUnitSystem.SI).request
    )
    p2a_us = evaluate_single_bolt_connection(build_plate_case("P2A").request)
    p2a_si = evaluate_single_bolt_connection(
        build_plate_case("P2A", unit_system=EngineeringUnitSystem.SI).request
    )
    assert p1_us.calculation_fingerprint == p1_si.calculation_fingerprint
    assert p2a_us.calculation_fingerprint == p2a_si.calculation_fingerprint


def _p1_unit_case(unit: EngineeringUnitSystem) -> CanonicalOrchestrationCase:
    return build_plate_case("P1", unit_system=unit)


def _p2a_unit_case(unit: EngineeringUnitSystem) -> CanonicalOrchestrationCase:
    return build_plate_case("P2A", unit_system=unit)


def _j1_unit_case(unit: EngineeringUnitSystem) -> CanonicalOrchestrationCase:
    return build_j1_case(unit_system=unit)


def test_locked_f593_keeps_bolt_checks_source_pending_while_frp_can_calculate() -> None:
    response = evaluate_single_bolt_connection(build_plate_case("P1").request)
    calculation = response.calculation_result
    assert calculation is not None
    bolt_plans = tuple(
        result
        for result in calculation.results
        if result.plan.limit_state
        in {
            LimitState.BOLT_TENSION,
            LimitState.BOLT_SHEAR,
            LimitState.BOLT_COMBINED_TENSION_SHEAR,
        }
    )
    assert any(
        result.availability is FinalResultAvailability.SOURCE_DATA_PENDING for result in bolt_plans
    )
    assert _result(calculation, LimitState.PIN_BEARING, "layer-A").availability is (
        FinalResultAvailability.CALCULATED
    )
    assert response.aggregate_status is not AggregatePlanningStatus.PASS
    assert response.fastener_snapshot.fnt is None
    assert OrchestrationIssueCode.FASTENER_SOURCE_PENDING in {
        issue.code for issue in response.issues
    }


def test_no_demand_response_contains_no_plans_or_equation_results() -> None:
    response = evaluate_single_bolt_connection(build_j1_case(explicit_demand=False).request)
    assert response.calculation_result is None
    assert response.aggregate_status is (
        AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    )
    assert response.source_action_trace is not None
    assert response.source_action_trace.automatic_moment_shift_applied is False
    assert response.governing_check_ids == ()
    assert response.qualification_flags == ()
    assert OrchestrationIssueCode.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED in {
        issue.code for issue in response.issues
    }
    assert all(
        trace.code_mapping is None and trace.code_geometry_validation is None
        for trace in response.resolved_layers
    )


def test_multiple_executable_shear_planes_fail_closed_in_existing_vocabulary() -> None:
    case = build_plate_case("B1")
    request = case.request
    request = replace(
        request,
        fastener_snapshot=replace(
            request.fastener_snapshot,
            shear_plane_thread_statuses=(
                request.fastener_snapshot.shear_plane_thread_statuses[0],
                ThreadStatusAssignment(
                    "shear-plane-2",
                    request.fastener_snapshot.shear_plane_thread_statuses[0].status,
                ),
            ),
            number_of_shear_planes=2,
        ),
    )
    response = evaluate_single_bolt_connection(request)
    assert response.calculation_result is not None
    assert OrchestrationIssueCode.MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED in {
        issue.code for issue in response.issues
    }
    shear = _result(response.calculation_result, LimitState.BOLT_SHEAR, None)
    assert shear.plan.readiness_status is CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
    assert shear.equation_trace is None
