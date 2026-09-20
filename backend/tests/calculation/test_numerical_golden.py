"""Independent high-precision comparison with every RC2 numerical oracle value."""

from decimal import ROUND_HALF_EVEN, Decimal
from types import MappingProxyType

from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    CalculationReadinessStatus,
    CleavageTrace,
    CombinedBoltTrace,
    FinalCalculationResult,
    FinalResultAvailability,
    LimitState,
    MaterialDirectionFamily,
    NetTensionTrace,
    NumericalComparison,
    PhysicalQuantity,
    PullThroughTrace,
    SingleBoltCalculationResult,
    Unit,
    calculate_single_bolt,
)
from tests.calculation.golden_loader import FrozenJson, load_golden_fixture
from tests.calculation.numerical_fixtures import (
    b1_input,
    direction_90_input,
    j1_input,
    p1_input,
    p2a_input,
    p2b_input,
    pt1_input,
)

SCALE = Decimal("0.000000000001")


def _expected(case: str, *path: str) -> Decimal:
    value: FrozenJson = load_golden_fixture()["benchmarks"]
    for key in (case, *path):
        assert isinstance(value, MappingProxyType)
        value = value[key]
    assert isinstance(value, str)
    return Decimal(value)


def _result(
    calculation: SingleBoltCalculationResult,
    limit_state: LimitState,
    layer_id: str | None,
) -> FinalCalculationResult:
    matches = tuple(
        result
        for result in calculation.results
        if result.plan.limit_state is limit_state and result.plan.layer_id == layer_id
    )
    assert len(matches) == 1
    return matches[0]


def _force(quantity: PhysicalQuantity) -> Decimal:
    return quantity.to(Unit.KIP).magnitude


def _layer_values(
    calculation: SingleBoltCalculationResult,
    layer_id: str,
    *,
    include_cleavage: bool = True,
) -> dict[str, Decimal]:
    bearing = _result(calculation, LimitState.PIN_BEARING, layer_id)
    net = _result(calculation, LimitState.NET_SECTION_TENSION, layer_id)
    shear = _result(calculation, LimitState.SHEAR_OUT, layer_id)
    assert bearing.nominal_resistance is not None
    assert bearing.design_resistance is not None
    assert net.nominal_resistance is not None
    assert net.design_resistance is not None
    assert shear.nominal_resistance is not None
    assert shear.design_resistance is not None
    assert bearing.utilization is not None
    assert net.utilization is not None
    assert shear.utilization is not None
    assert isinstance(net.equation_trace, NetTensionTrace)
    values = {
        "Spr": net.equation_trace.spr,
        "Theta": net.equation_trace.theta,
        "Knt": net.equation_trace.knt,
        "Rbr_nom": _force(bearing.nominal_resistance),
        "Rbr_design": _force(bearing.design_resistance),
        "U_br": bearing.utilization,
        "Rnt_nom": _force(net.nominal_resistance),
        "Rnt_design": _force(net.design_resistance),
        "U_nt": net.utilization,
        "Rsh_nom": _force(shear.nominal_resistance),
        "Rsh_design": _force(shear.design_resistance),
        "U_sh": shear.utilization,
    }
    if include_cleavage:
        cleavage = _result(calculation, LimitState.CLEAVAGE, layer_id)
        assert cleavage.nominal_resistance is not None
        assert cleavage.design_resistance is not None
        assert cleavage.utilization is not None
        assert isinstance(cleavage.equation_trace, CleavageTrace)
        trace = cleavage.equation_trace
        demand = bearing.demand
        assert demand is not None
        values.update(
            {
                "Rcl_a_nom": _force(trace.branch_a_factor_trace.nominal_resistance),
                "Rcl_a_design": _force(trace.branch_a_factor_trace.design_resistance),
                "U_cl_a": demand.canonical_magnitude
                / trace.branch_a_factor_trace.design_resistance.canonical_magnitude,
                "Rcl_b_nom": _force(trace.branch_b_factor_trace.nominal_resistance),
                "Rcl_b_design": _force(trace.branch_b_factor_trace.design_resistance),
                "Rcl_design": _force(cleavage.design_resistance),
                "U_cl": cleavage.utilization,
            }
        )
    return values


def _assert_expected(case: str, actual: dict[str, Decimal], *prefix: str) -> None:
    for key, value in actual.items():
        expected = _expected(case, *prefix, key)
        assert value.quantize(SCALE, rounding=ROUND_HALF_EVEN) == expected, (
            case,
            prefix,
            key,
            value,
            expected,
            abs(value - expected),
        )


def test_p1_reproduces_every_recorded_numerical_value_and_governing_tie() -> None:
    calculation = calculate_single_bolt(p1_input())
    _assert_expected("P1", _layer_values(calculation, "P1"), "results")
    assert calculation.aggregate_status is AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED
    assert calculation.governing_check_ids == (
        "connection-1:bolt-1:P1:pin_bearing",
        "connection-1:bolt-1:P1:cleavage",
    )
    assert _result(calculation, LimitState.PULL_THROUGH, "P1").availability is (
        FinalResultAvailability.NOT_APPLICABLE
    )


def test_pt1_reproduces_every_recorded_pull_through_value() -> None:
    result = _result(calculate_single_bolt(pt1_input()), LimitState.PULL_THROUGH, "P1")
    assert isinstance(result.equation_trace, PullThroughTrace)
    assert result.design_resistance is not None
    assert result.utilization is not None
    actual = {
        "Rtt_branch_8_4a_nom_kip": _force(result.equation_trace.branch_8_4a_nominal),
        "Rtt_branch_8_4b_nom_kip": _force(result.equation_trace.branch_8_4b_nominal),
        "Rtt_design_kip": _force(result.design_resistance),
        "utilization": result.utilization,
    }
    _assert_expected("PT1", actual)


def test_p2a_reproduces_every_recorded_layer_value_and_single_lap_tie() -> None:
    calculation = calculate_single_bolt(p2a_input())
    _assert_expected("P2A", _layer_values(calculation, "layer_A"), "layer_A", "results")
    _assert_expected("P2A", _layer_values(calculation, "layer_B"), "layer_B", "results")
    assert calculation.governing_check_ids == (
        "connection-1:bolt-1:layer_A:pin_bearing",
        "connection-1:bolt-1:layer_A:cleavage",
    )


def test_p2b_reproduces_known_failure_and_unsupported_required_check() -> None:
    calculation = calculate_single_bolt(p2b_input())
    bearing = _result(calculation, LimitState.PIN_BEARING, "layer_B")
    net = _result(calculation, LimitState.NET_SECTION_TENSION, "layer_B")
    shear = _result(calculation, LimitState.SHEAR_OUT, "layer_B")
    cleavage = _result(calculation, LimitState.CLEAVAGE, "layer_B")
    assert bearing.design_resistance is not None
    assert bearing.utilization is not None
    assert net.design_resistance is not None
    assert net.utilization is not None
    assert shear.design_resistance is not None
    assert shear.utilization is not None
    actual = {
        "Rbr_design_kip": _force(bearing.design_resistance),
        "U_br": bearing.utilization,
        "Rnt_design_kip": _force(net.design_resistance),
        "U_nt": net.utilization,
        "Rsh_design_kip": _force(shear.design_resistance),
        "U_sh": shear.utilization,
    }
    _assert_expected("P2B", actual, "layer_B")
    assert bearing.numerical_comparison is net.numerical_comparison is NumericalComparison.FAIL
    assert shear.numerical_comparison is NumericalComparison.PASS
    assert cleavage.availability is FinalResultAvailability.CALCULATION_NOT_SUPPORTED
    assert (
        calculation.aggregate_status is AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK
    )


def test_j1_t_reproduces_every_component_value_and_qualification_boundary() -> None:
    calculation = calculate_single_bolt(j1_input())
    _assert_expected("J1_T", _layer_values(calculation, "angle_leg"), "angle_leg", "results")
    w_values = _layer_values(calculation, "w_flange", include_cleavage=False)
    _assert_expected("J1_T", w_values, "w_flange", "results")
    assert _result(calculation, LimitState.CLEAVAGE, "w_flange").availability is (
        FinalResultAvailability.CALCULATION_NOT_SUPPORTED
    )
    assert calculation.governing_check_ids == ("connection-1:bolt-1:w_flange:net_tension",)
    assert (
        calculation.aggregate_status is AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )


def test_j1_c_reproduces_recorded_values_and_excludes_tension_limit_states() -> None:
    calculation = calculate_single_bolt(j1_input(compression=True))
    for layer, fixture_layer in (("angle_leg", "angle_leg"), ("w_flange", "w_flange")):
        bearing = _result(calculation, LimitState.PIN_BEARING, layer)
        shear = _result(calculation, LimitState.SHEAR_OUT, layer)
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
        assert _result(calculation, LimitState.NET_SECTION_TENSION, layer).availability is (
            FinalResultAvailability.NOT_APPLICABLE
        )
        assert _result(calculation, LimitState.CLEAVAGE, layer).availability is (
            FinalResultAvailability.NOT_APPLICABLE
        )


def test_b1_synthetic_reproduces_every_recorded_bolt_value() -> None:
    calculation = calculate_single_bolt(b1_input())
    shear = _result(calculation, LimitState.BOLT_SHEAR, None)
    combined = _result(calculation, LimitState.BOLT_COMBINED_TENSION_SHEAR, None)
    assert shear.design_resistance is not None
    assert shear.utilization is not None
    assert isinstance(combined.equation_trace, CombinedBoltTrace)
    assert combined.design_resistance is not None
    assert combined.utilization is not None
    trace = combined.equation_trace
    actual = {
        "Ab_in2": trace.area_trace.area.to(Unit.IN2).magnitude,
        "Fnv_ksi": trace.fnv.to(Unit.KSI).magnitude,
        "shear_design_resistance_kip": _force(shear.design_resistance),
        "shear_utilization": shear.utilization,
        "required_shear_stress_ksi": trace.required_shear_stress.to(Unit.KSI).magnitude,
        "modified_tensile_stress_ksi": trace.modified_tensile_stress.to(Unit.KSI).magnitude,
        "combined_tension_design_resistance_kip": _force(combined.design_resistance),
        "combined_tension_utilization": combined.utilization,
    }
    _assert_expected("B1_SYNTHETIC", actual)


def test_exact_90_fixture_consumes_transverse_selection_without_reinterpretation() -> None:
    calculation = calculate_single_bolt(direction_90_input())
    bearing = _result(calculation, LimitState.PIN_BEARING, "DIRECTION_90")
    net = _result(calculation, LimitState.NET_SECTION_TENSION, "DIRECTION_90")
    cleavage = _result(calculation, LimitState.CLEAVAGE, "DIRECTION_90")
    assert bearing.plan.selected_direction_family is MaterialDirectionFamily.TRANSVERSE
    assert net.plan.selected_direction_family is MaterialDirectionFamily.TRANSVERSE
    assert bearing.plan.required_property_kind is not None
    assert bearing.plan.required_property_kind.value == _expected_text(
        "DIRECTION_90", "bearing_property_selection"
    )
    assert net.plan.required_property_kind is not None
    assert net.plan.required_property_kind.value == _expected_text(
        "DIRECTION_90", "net_tension_property_selection"
    )
    assert cleavage.plan.readiness_status is CalculationReadinessStatus.NOT_APPLICABLE


def _expected_text(case: str, *path: str) -> str:
    value: FrozenJson = load_golden_fixture()["benchmarks"]
    for key in (case, *path):
        assert isinstance(value, MappingProxyType)
        value = value[key]
    assert isinstance(value, str)
    return value
