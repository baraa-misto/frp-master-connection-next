"""Pure orchestration of approved Stage 2.1B single-bolt numerical checks."""

from __future__ import annotations

from decimal import Decimal, localcontext

from frp_master_connection.calculation.applicability import (
    LayerPlanningInput,
    SingleBoltPlanningInput,
    plan_single_bolt_checks,
)
from frp_master_connection.calculation.equations import (
    CALCULATION_ENGINE_VERSION,
    ENGINEERING_RULE_SET_VERSION,
    BearingTrace,
    CleavageTrace,
    EndUsePropertyTrace,
    EquationTrace,
    NetTensionTrace,
    PullThroughTrace,
    ShearOutTrace,
    adjust_frp_property,
    bolt_shear_resistance,
    bolt_tension_resistance,
    cleavage_resistance,
    combined_bolt_tension_shear_resistance,
    net_tension_resistance,
    pin_bearing_resistance,
    pull_through_resistance,
    shear_out_resistance,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyEntry,
    FRPPropertyKind,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.calculation.results import (
    CalculationReadinessStatus,
    FinalCalculationResult,
    FinalResultAvailability,
    LimitState,
    MaterialDirectionFamily,
    NumericalComparison,
    PlannedCheck,
    SingleBoltCalculationResult,
    aggregate_calculation_status,
    governing_check_ids,
)
from frp_master_connection.calculation.sources import (
    CalculationSourceSnapshot,
    asce_74_23_chapter_8_source,
)

_UNAVAILABLE_BY_READINESS = {
    CalculationReadinessStatus.NOT_APPLICABLE: FinalResultAvailability.NOT_APPLICABLE,
    CalculationReadinessStatus.INCOMPLETE_INPUT: FinalResultAvailability.INCOMPLETE_INPUT,
    CalculationReadinessStatus.SOURCE_DATA_PENDING: FinalResultAvailability.SOURCE_DATA_PENDING,
    CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED: (
        FinalResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED
    ),
    CalculationReadinessStatus.ENGINEERING_REVIEW_REQUIRED: (
        FinalResultAvailability.ENGINEERING_REVIEW_REQUIRED
    ),
    CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED: (
        FinalResultAvailability.CALCULATION_NOT_SUPPORTED
    ),
    CalculationReadinessStatus.INVALID_GEOMETRY: FinalResultAvailability.INVALID_GEOMETRY,
    CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED: (
        FinalResultAvailability.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    ),
}


def _source(plan: PlannedCheck) -> CalculationSourceSnapshot:
    interpretation = (
        "TRANSVERSE_ENDPOINT_INCLUDED"
        if plan.theta_degrees == Decimal("90")
        and plan.selected_direction_family is MaterialDirectionFamily.TRANSVERSE
        else None
    )
    return asce_74_23_chapter_8_source(
        section=plan.source_section,
        equation_reference=plan.source_equation,
        interpretation_id=interpretation,
    )


def _unavailable(plan: PlannedCheck) -> FinalCalculationResult:
    return FinalCalculationResult(
        plan=plan,
        availability=_UNAVAILABLE_BY_READINESS[plan.readiness_status],
        numerical_comparison=NumericalComparison.NOT_EVALUATED,
        demand=None,
        nominal_resistance=None,
        design_resistance=None,
        utilization=None,
        equation_trace=None,
        source_snapshot=_source(plan),
        warnings=plan.warnings,
    )


def _property(planning_input: SingleBoltPlanningInput, kind: FRPPropertyKind) -> FRPPropertyEntry:
    entry = planning_input.material.lookup(kind)
    if entry is None:
        raise ValueError(f"Ready plan unexpectedly lacks property {kind.value}.")
    return entry


def _adjusted(
    planning_input: SingleBoltPlanningInput,
    kind: FRPPropertyKind,
) -> EndUsePropertyTrace:
    entry = _property(planning_input, kind)
    return adjust_frp_property(
        kind,
        entry.value,
        entry.qualification_status,
        planning_input.end_use_factors,
    )


def _layer(planning_input: SingleBoltPlanningInput, plan: PlannedCheck) -> LayerPlanningInput:
    matches = tuple(
        layer
        for layer in planning_input.layers
        if layer.mapping.physical_element_id == plan.layer_id
    )
    if len(matches) != 1:
        raise ValueError("A ready layer check must resolve to exactly one planning layer.")
    return matches[0]


def _axial_demand(planning_input: SingleBoltPlanningInput) -> PhysicalQuantity:
    return (
        planning_input.demand.bolt_axis_tensile_demand
        + planning_input.demand.externally_supplied_prying_demand
    )


def _comparison(
    demand: PhysicalQuantity,
    design_resistance: PhysicalQuantity,
) -> tuple[NumericalComparison, Decimal | None, tuple[str, ...]]:
    if design_resistance.magnitude <= 0:
        return (
            NumericalComparison.FAIL,
            None,
            ("Calculated design resistance is nonpositive and was not clamped.",),
        )
    with localcontext() as context:
        context.prec = 60
        utilization = demand.canonical_magnitude / design_resistance.canonical_magnitude
    comparison = (
        NumericalComparison.PASS if demand <= design_resistance else NumericalComparison.FAIL
    )
    return comparison, utilization, ()


def _result(
    plan: PlannedCheck,
    demand: PhysicalQuantity,
    nominal: PhysicalQuantity,
    design: PhysicalQuantity,
    trace: EquationTrace,
    *,
    forced_failure: bool = False,
    warnings: tuple[str, ...] = (),
) -> FinalCalculationResult:
    comparison, utilization, comparison_warnings = _comparison(demand, design)
    if forced_failure:
        comparison = NumericalComparison.FAIL
    return FinalCalculationResult(
        plan=plan,
        availability=FinalResultAvailability.CALCULATED,
        numerical_comparison=comparison,
        demand=demand,
        nominal_resistance=nominal,
        design_resistance=design,
        utilization=utilization,
        equation_trace=trace,
        source_snapshot=_source(plan),
        warnings=(*plan.warnings, *warnings, *comparison_warnings),
    )


def _bolt_result(
    planning_input: SingleBoltPlanningInput,
    plan: PlannedCheck,
) -> FinalCalculationResult:
    diameter = planning_input.layers[0].mapping.bolt_diameter
    fnt = planning_input.fastener.fnt
    if fnt is None:
        raise ValueError("A ready bolt plan requires explicit Fnt.")
    if plan.limit_state is LimitState.BOLT_TENSION:
        trace = bolt_tension_resistance(diameter, fnt)
        demand = _axial_demand(planning_input)
        return _result(
            plan,
            demand,
            trace.nominal_resistance,
            trace.design_resistance,
            trace,
        )
    thread_status = planning_input.fastener.shear_plane_thread_statuses[0].status
    shear_demand = planning_input.demand.in_plane_force_magnitude
    if plan.limit_state is LimitState.BOLT_SHEAR:
        trace = bolt_shear_resistance(diameter, fnt, thread_status)
        return _result(
            plan,
            shear_demand,
            trace.nominal_resistance,
            trace.design_resistance,
            trace,
        )
    combined = combined_bolt_tension_shear_resistance(
        diameter,
        fnt,
        thread_status,
        shear_demand,
    )
    pure_shear = bolt_shear_resistance(diameter, fnt, thread_status)
    pure_shear_failed = shear_demand > pure_shear.design_resistance
    return _result(
        plan,
        _axial_demand(planning_input),
        combined.nominal_tensile_resistance,
        combined.design_tensile_resistance,
        combined,
        forced_failure=pure_shear_failed,
        warnings=("Pure bolt shear comparison also fails.",) if pure_shear_failed else (),
    )


def _bearing_trace(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> BearingTrace:
    property_kind = (
        FRPPropertyKind.FBR_L
        if layer.mapping.direction_family is MaterialDirectionFamily.LONGITUDINAL
        else FRPPropertyKind.FBR_T
    )
    return pin_bearing_resistance(
        layer.mapping.layer_thickness,
        layer.mapping.bolt_diameter,
        _adjusted(planning_input, property_kind),
        layer.bearing_thread_status,
        c_delta=planning_input.geometry_factor.planning_value,
        c_lap=planning_input.lap_factor.applicable_in_plane_frp_factor,
        lambda_factor=planning_input.time_effect.value,
    )


def _frp_result(
    planning_input: SingleBoltPlanningInput,
    plan: PlannedCheck,
) -> FinalCalculationResult:
    layer = _layer(planning_input, plan)
    mapping = layer.mapping
    c_delta = planning_input.geometry_factor.planning_value
    c_lap = planning_input.lap_factor.applicable_in_plane_frp_factor
    lambda_factor = planning_input.time_effect.value
    demand = planning_input.demand.in_plane_force_magnitude
    trace: PullThroughTrace | BearingTrace | NetTensionTrace | ShearOutTrace | CleavageTrace
    if plan.limit_state is LimitState.PULL_THROUGH:
        washer = planning_input.washer
        if washer is None:
            raise ValueError("A ready pull-through plan requires washer geometry.")
        trace = pull_through_resistance(
            washer.outside_diameter,
            mapping.layer_thickness,
            _adjusted(planning_input, FRPPropertyKind.FSH_LT),
            _adjusted(planning_input, FRPPropertyKind.FSH_INT),
            c_delta=c_delta,
            lambda_factor=lambda_factor,
        )
        return _result(
            plan,
            _axial_demand(planning_input),
            trace.factor_trace.nominal_resistance,
            trace.factor_trace.design_resistance,
            trace,
        )
    if plan.limit_state is LimitState.PIN_BEARING:
        trace = _bearing_trace(planning_input, layer)
    elif plan.limit_state is LimitState.NET_SECTION_TENSION:
        width = mapping.effective_width
        property_kind = plan.required_property_kind
        if width is None or property_kind is None:
            raise ValueError("A ready net-tension plan requires width and property selection.")
        trace = net_tension_resistance(
            width,
            mapping.bolt_diameter,
            mapping.hole_diameter,
            mapping.layer_thickness,
            mapping.forward_e1,
            _adjusted(planning_input, property_kind),
            layer.element_form,
            mapping.direction_family is MaterialDirectionFamily.LONGITUDINAL,
            c_delta=c_delta,
            c_lap=c_lap,
            lambda_factor=lambda_factor,
        )
    elif plan.limit_state is LimitState.SHEAR_OUT:
        trace = shear_out_resistance(
            mapping.forward_e1,
            mapping.hole_diameter,
            mapping.layer_thickness,
            _adjusted(planning_input, FRPPropertyKind.FSH_LT),
            c_delta=c_delta,
            c_lap=c_lap,
            lambda_factor=lambda_factor,
        )
    else:
        trace = cleavage_resistance(
            mapping.forward_e1,
            mapping.raw_side_distance_1,
            mapping.bolt_diameter,
            mapping.hole_diameter,
            mapping.layer_thickness,
            _adjusted(planning_input, FRPPropertyKind.FT_L),
            _adjusted(planning_input, FRPPropertyKind.FSH_LT),
            _bearing_trace(planning_input, layer),
            c_delta=c_delta,
            c_lap=c_lap,
            lambda_factor=lambda_factor,
        )
    if isinstance(trace, CleavageTrace):
        nominal = trace.selected_nominal_resistance
        design = trace.selected_design_resistance
    else:
        nominal = trace.factor_trace.nominal_resistance
        design = trace.factor_trace.design_resistance
    return _result(plan, demand, nominal, design, trace)


def calculate_single_bolt(
    planning_input: SingleBoltPlanningInput,
) -> SingleBoltCalculationResult:
    """Plan and execute only ready first-slice checks without mutating engineering input."""

    planning_result = plan_single_bolt_checks(planning_input)
    results: list[FinalCalculationResult] = []
    for plan in planning_result.checks:
        if plan.readiness_status is not CalculationReadinessStatus.READY:
            results.append(_unavailable(plan))
        elif plan.limit_state in {
            LimitState.BOLT_TENSION,
            LimitState.BOLT_SHEAR,
            LimitState.BOLT_COMBINED_TENSION_SHEAR,
        }:
            results.append(_bolt_result(planning_input, plan))
        else:
            results.append(_frp_result(planning_input, plan))
    final_results = tuple(results)
    return SingleBoltCalculationResult(
        planning_result,
        final_results,
        aggregate_calculation_status(final_results, planning_result.whole_connection_status),
        governing_check_ids(final_results),
        planning_input.input_fingerprint,
        CALCULATION_ENGINE_VERSION,
        ENGINEERING_RULE_SET_VERSION,
    )


__all__ = ("calculate_single_bolt",)
