"""Deterministic first-slice applicability and readiness planning."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.geometry_mapping import (
    CodeGeometryValidation,
    EffectiveWidthMappingStatus,
    GeometryToCodeMapping,
)
from frp_master_connection.calculation.inputs import (
    DemandSourceKind,
    EndUseFactors,
    GeometryFactorPlan,
    LapFactorPlan,
    LayerLoadingSense,
    PultrudedElementForm,
    ResolvedSingleBoltDemand,
    TimeEffectFactor,
)
from frp_master_connection.calculation.properties import (
    FastenerSnapshot,
    FRPPropertyEntry,
    FRPPropertyKind,
    MaterialPropertySnapshot,
    ThreadStatus,
    WasherGeometry,
)
from frp_master_connection.calculation.results import (
    AggregatePlanningStatus,
    ApplicabilityReasonCode,
    CalculationReadinessStatus,
    LimitState,
    MaterialDirectionFamily,
    NumericalComparison,
    PlannedCheck,
    SuppliedNumericalFixtureResult,
    aggregate_planning_status,
)
from frp_master_connection.calculation.sources import QualificationStatus


@dataclass(frozen=True, slots=True)
class LayerPlanningInput:
    """One independently planned FRP layer in an ordered physical bolt stack."""

    mapping: GeometryToCodeMapping
    geometry_validation: CodeGeometryValidation
    bearing_thread_status: ThreadStatus
    potential_perpendicular_element_exemption: bool = False
    element_form: PultrudedElementForm = PultrudedElementForm.SHAPE_ELEMENT

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, GeometryToCodeMapping):
            raise TypeError("mapping must be a GeometryToCodeMapping.")
        if not isinstance(self.geometry_validation, CodeGeometryValidation):
            raise TypeError("geometry_validation must be a CodeGeometryValidation.")
        if not isinstance(self.bearing_thread_status, ThreadStatus):
            raise TypeError("bearing_thread_status must be a ThreadStatus.")
        if not isinstance(self.element_form, PultrudedElementForm):
            raise TypeError("element_form must be a PultrudedElementForm.")


@dataclass(frozen=True, slots=True)
class SingleBoltPlanningInput:
    """Complete explicit Stage 2.1A input for one logical bolt/one row."""

    connection_id: str
    bolt_id: str
    demand: ResolvedSingleBoltDemand
    layers: tuple[LayerPlanningInput, ...]
    material: MaterialPropertySnapshot
    fastener: FastenerSnapshot
    washer: WasherGeometry | None
    time_effect: TimeEffectFactor
    end_use_factors: EndUseFactors
    lap_factor: LapFactorPlan
    geometry_factor: GeometryFactorPlan
    input_fingerprint: str
    whole_connection_requires_section_2_3_2: bool = False

    def __post_init__(self) -> None:
        if not self.connection_id.strip() or not self.bolt_id.strip():
            raise ValueError("Planning connection and bolt identities must be nonempty.")
        if not self.layers:
            raise ValueError("Single-bolt planning requires at least one explicit FRP layer.")
        layer_ids = [layer.mapping.physical_element_id for layer in self.layers]
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError("Each physical FRP layer may occur only once in a bolt stack.")


@dataclass(frozen=True, slots=True)
class SingleBoltPlanningResult:
    """Planned checks plus whole-connection and aggregate readiness."""

    checks: tuple[PlannedCheck, ...]
    whole_connection_status: CalculationReadinessStatus
    aggregate_status: AggregatePlanningStatus


def _property(
    material: MaterialPropertySnapshot,
    kind: FRPPropertyKind,
) -> FRPPropertyEntry | None:
    try:
        return material.lookup(kind)
    except KeyError:
        return None


def _material_qualification_flags(
    material: MaterialPropertySnapshot,
) -> tuple[QualificationStatus, ...]:
    return tuple(
        status
        for status in material.qualification_statuses
        if status
        in {
            QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
            QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        }
    )


def _factor_metadata(
    planning_input: SingleBoltPlanningInput,
    *,
    include_lap: bool,
) -> tuple[str, ...]:
    metadata = (
        f"lambda_category:{planning_input.time_effect.category.value}",
        f"lambda:{planning_input.time_effect.value}",
        f"CM:{planning_input.end_use_factors.cm}",
        f"CT:{planning_input.end_use_factors.ct}",
        f"CCH:{planning_input.end_use_factors.cch}",
        f"C_delta_plan:{planning_input.geometry_factor.planning_value}",
        "factors_not_applied_in_stage_2_1a",
    )
    if include_lap:
        return (
            *metadata,
            f"lap:{planning_input.lap_factor.configuration.value}",
            f"C_lap_plan:{planning_input.lap_factor.applicable_in_plane_frp_factor}",
        )
    return metadata


def _plan(
    planning_input: SingleBoltPlanningInput,
    *,
    suffix: str,
    limit_state: LimitState,
    component_id: str | None,
    layer_id: str | None,
    source_section: str,
    source_equation: str,
    status: CalculationReadinessStatus,
    reasons: tuple[ApplicabilityReasonCode, ...],
    required_property: FRPPropertyKind | None = None,
    direction: MaterialDirectionFamily | None = None,
    theta: Decimal | None = None,
    geometry_inputs: tuple[str, ...] = (),
    include_lap: bool = False,
    qualification_flags: tuple[QualificationStatus, ...] = (),
    warnings: tuple[str, ...] = (),
    assumptions: tuple[str, ...] = (),
    unsupported: tuple[str, ...] = (),
    required: bool = True,
) -> PlannedCheck:
    return PlannedCheck(
        check_id=f"{planning_input.connection_id}:{planning_input.bolt_id}:{suffix}",
        limit_state=limit_state,
        component_id=component_id,
        layer_id=layer_id,
        bolt_id=planning_input.bolt_id,
        source_section=source_section,
        source_equation=source_equation,
        readiness_status=status,
        numerical_comparison=NumericalComparison.NOT_EVALUATED,
        applicability_reason_codes=reasons,
        required_property_kind=required_property,
        selected_direction_family=direction,
        theta_degrees=theta,
        required_geometry_inputs=geometry_inputs,
        factor_metadata=_factor_metadata(planning_input, include_lap=include_lap),
        qualification_flags=qualification_flags,
        warnings=warnings,
        assumptions=assumptions,
        unsupported_conditions=unsupported,
        input_fingerprint=planning_input.input_fingerprint,
        required=required,
    )


def _distribution_status(
    demand: ResolvedSingleBoltDemand,
) -> CalculationReadinessStatus | None:
    if demand.source_kind is DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED:
        return CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    if not demand.factored_action_confirmed:
        return CalculationReadinessStatus.INCOMPLETE_INPUT
    return None


def _bolt_status(
    fastener: FastenerSnapshot,
    applicable: bool,
) -> tuple[CalculationReadinessStatus, tuple[ApplicabilityReasonCode, ...]]:
    if not applicable:
        return (
            CalculationReadinessStatus.NOT_APPLICABLE,
            (ApplicabilityReasonCode.ZERO_IN_PLANE_DEMAND,),
        )
    if fastener.fnt is None:
        return (
            CalculationReadinessStatus.SOURCE_DATA_PENDING,
            (ApplicabilityReasonCode.LOCKED_FASTENER_FNT_SOURCE_PENDING,),
        )
    return (
        CalculationReadinessStatus.READY,
        (
            ApplicabilityReasonCode.EXPLICIT_FNT_RETAINED,
            ApplicabilityReasonCode.READY_FOR_FUTURE_NUMERICAL_IMPLEMENTATION,
            ApplicabilityReasonCode.PHYSICAL_NUMERICAL_EVALUATION_NOT_AUTHORIZED,
        ),
    )


def _bolt_shear_status(
    fastener: FastenerSnapshot,
    applicable: bool,
) -> tuple[CalculationReadinessStatus, tuple[ApplicabilityReasonCode, ...]]:
    status, reasons = _bolt_status(fastener, applicable)
    if not applicable or fastener.fnt is None:
        return status, reasons
    if fastener.number_of_shear_planes == 0:
        return (
            CalculationReadinessStatus.INCOMPLETE_INPUT,
            (ApplicabilityReasonCode.SHEAR_PLANE_REQUIRED,),
        )
    if fastener.number_of_shear_planes > 1:
        return (
            CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED,
            (ApplicabilityReasonCode.MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED,),
        )
    return status, reasons


def _plan_bolt_checks(planning_input: SingleBoltPlanningInput) -> tuple[PlannedCheck, ...]:
    demand = planning_input.demand
    distribution = _distribution_status(demand)
    in_plane = demand.in_plane_force_magnitude.magnitude > 0
    axial = (
        demand.bolt_axis_tensile_demand.magnitude > 0
        or demand.externally_supplied_prying_demand.magnitude > 0
    )
    definitions = (
        (LimitState.BOLT_TENSION, "bolt_tension", axial, "8.3.2.1", "8-2"),
        (LimitState.BOLT_SHEAR, "bolt_shear", in_plane, "8.3.2.1", "8-2"),
        (
            LimitState.BOLT_COMBINED_TENSION_SHEAR,
            "bolt_combined",
            axial and in_plane,
            "8.3.2.1",
            "8-3a/b",
        ),
    )
    plans: list[PlannedCheck] = []
    for limit_state, suffix, applicable, section, equation in definitions:
        status, reasons = (
            _bolt_status(planning_input.fastener, applicable)
            if limit_state is LimitState.BOLT_TENSION
            else _bolt_shear_status(planning_input.fastener, applicable)
        )
        if distribution is not None and applicable:
            status = distribution
            reasons = (ApplicabilityReasonCode.MEMBER_END_ACTION_NOT_DISTRIBUTED,)
        plans.append(
            _plan(
                planning_input,
                suffix=suffix,
                limit_state=limit_state,
                component_id=None,
                layer_id=None,
                source_section=section,
                source_equation=equation,
                status=status,
                reasons=reasons,
                geometry_inputs=("bolt_diameter", "thread_status_by_shear_plane"),
                required=applicable and planning_input.fastener.fnt is not None,
            )
        )
    return tuple(plans)


def _geometry_or_distribution_status(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> CalculationReadinessStatus | None:
    distribution = _distribution_status(planning_input.demand)
    if distribution is not None:
        return distribution
    if layer.geometry_validation.status is not CalculationReadinessStatus.READY:
        return layer.geometry_validation.status
    return None


def _base_ready_reasons() -> tuple[ApplicabilityReasonCode, ...]:
    return (
        ApplicabilityReasonCode.READY_FOR_FUTURE_NUMERICAL_IMPLEMENTATION,
        ApplicabilityReasonCode.PHYSICAL_NUMERICAL_EVALUATION_NOT_AUTHORIZED,
    )


def _plan_pull_through(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> PlannedCheck:
    demand = planning_input.demand
    reasons: tuple[ApplicabilityReasonCode, ...]
    positive = (
        demand.bolt_axis_tensile_demand.magnitude > 0
        or demand.externally_supplied_prying_demand.magnitude > 0
    )
    status_override = _geometry_or_distribution_status(planning_input, layer)
    required_entries = (
        _property(planning_input.material, FRPPropertyKind.FSH_LT),
        _property(planning_input.material, FRPPropertyKind.FSH_INT),
    )
    if not positive:
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.BOLT_AXIS_TENSION_AND_PRYING_ZERO,)
        required = False
    elif status_override is not None:
        status = status_override
        reasons = (
            ApplicabilityReasonCode.MEMBER_END_ACTION_NOT_DISTRIBUTED
            if status is CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
            else ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,
        )
        required = True
    elif planning_input.washer is None or any(entry is None for entry in required_entries):
        status = CalculationReadinessStatus.INCOMPLETE_INPUT
        reasons = (ApplicabilityReasonCode.REQUIRED_PULL_THROUGH_INPUT_MISSING,)
        required = True
    else:
        status = CalculationReadinessStatus.READY
        reasons = (
            ApplicabilityReasonCode.POSITIVE_EXPLICIT_BOLT_AXIS_OR_PRYING_DEMAND,
            *_base_ready_reasons(),
        )
        required = True
    return _plan(
        planning_input,
        suffix=f"{layer.mapping.physical_element_id}:pull_through",
        limit_state=LimitState.PULL_THROUGH,
        component_id=layer.mapping.component_id,
        layer_id=layer.mapping.physical_element_id,
        source_section="8.3.2.2",
        source_equation="8-4a/b",
        status=status,
        reasons=reasons,
        required_property=FRPPropertyKind.FSH_INT,
        direction=layer.mapping.direction_family,
        theta=layer.mapping.theta_degrees,
        geometry_inputs=("washer_outside_diameter", "layer_thickness", "washer_faces"),
        qualification_flags=(
            _material_qualification_flags(planning_input.material)
            if status is CalculationReadinessStatus.READY
            else ()
        ),
        required=required,
    )


def _directional_property(
    mapping: GeometryToCodeMapping,
    longitudinal: FRPPropertyKind,
    transverse: FRPPropertyKind,
) -> FRPPropertyKind:
    return (
        longitudinal
        if mapping.direction_family is MaterialDirectionFamily.LONGITUDINAL
        else transverse
    )


def _plan_bearing(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> PlannedCheck:
    mapping = layer.mapping
    reasons: tuple[ApplicabilityReasonCode, ...]
    property_kind = _directional_property(mapping, FRPPropertyKind.FBR_L, FRPPropertyKind.FBR_T)
    status_override = _geometry_or_distribution_status(planning_input, layer)
    if planning_input.demand.in_plane_force_magnitude.magnitude == 0:
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.ZERO_IN_PLANE_DEMAND,)
        required = False
    elif status_override is not None:
        status = status_override
        reasons = (ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,)
        required = True
    elif _property(planning_input.material, property_kind) is None:
        status = CalculationReadinessStatus.INCOMPLETE_INPUT
        reasons = (ApplicabilityReasonCode.REQUIRED_PROPERTY_MISSING,)
        required = True
    else:
        status = CalculationReadinessStatus.READY
        reasons = (*_base_ready_reasons(),)
        required = True
    qualifications = (
        _material_qualification_flags(planning_input.material)
        if status is CalculationReadinessStatus.READY
        else ()
    )
    if qualifications:
        reasons = (*reasons, ApplicabilityReasonCode.ICE_DEVELOPMENT_PROPERTY_REQUIRES_REVIEW)
    if mapping.direction_interpretation_id is not None:
        reasons = (*reasons, ApplicabilityReasonCode.EXACT_90_TRANSVERSE_INTERPRETATION)
    return _plan(
        planning_input,
        suffix=f"{mapping.physical_element_id}:pin_bearing",
        limit_state=LimitState.PIN_BEARING,
        component_id=mapping.component_id,
        layer_id=mapping.physical_element_id,
        source_section="8.3.2.3",
        source_equation="8-5/8-6",
        status=status,
        reasons=reasons,
        required_property=property_kind,
        direction=mapping.direction_family,
        theta=mapping.theta_degrees,
        geometry_inputs=("bolt_diameter", "hole_diameter", "layer_thickness"),
        include_lap=True,
        qualification_flags=qualifications,
        warnings=(f"bearing_threads:{layer.bearing_thread_status.value}",),
        required=required,
    )


def _plan_net_tension(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> PlannedCheck:
    mapping = layer.mapping
    reasons: tuple[ApplicabilityReasonCode, ...]
    property_kind = _directional_property(mapping, FRPPropertyKind.FT_L, FRPPropertyKind.FT_T)
    status_override = _geometry_or_distribution_status(planning_input, layer)
    if planning_input.demand.loading_sense is LayerLoadingSense.COMPRESSION:
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.COMPRESSION_EXCLUDES_TENSION_LIMIT_STATE,)
        required = False
    elif status_override is not None:
        status = status_override
        reasons = (ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,)
        required = True
    elif mapping.effective_width_status is EffectiveWidthMappingStatus.CALCULATION_NOT_SUPPORTED:
        status = CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
        reasons = (ApplicabilityReasonCode.EFFECTIVE_WIDTH_MAPPING_UNSUPPORTED,)
        required = True
    elif mapping.effective_width is None or mapping.effective_width <= mapping.hole_diameter:
        status = CalculationReadinessStatus.INVALID_GEOMETRY
        reasons = (ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,)
        required = True
    elif _property(planning_input.material, property_kind) is None:
        status = CalculationReadinessStatus.INCOMPLETE_INPUT
        reasons = (ApplicabilityReasonCode.REQUIRED_PROPERTY_MISSING,)
        required = True
    else:
        status = CalculationReadinessStatus.READY
        reasons = _base_ready_reasons()
        required = True
    return _plan(
        planning_input,
        suffix=f"{mapping.physical_element_id}:net_tension",
        limit_state=LimitState.NET_SECTION_TENSION,
        component_id=mapping.component_id,
        layer_id=mapping.physical_element_id,
        source_section="8.3.2.4",
        source_equation="8-7a/b",
        status=status,
        reasons=reasons,
        required_property=property_kind,
        direction=mapping.direction_family,
        theta=mapping.theta_degrees,
        geometry_inputs=("effective_width", "hole_diameter", "layer_thickness", "e1"),
        include_lap=True,
        qualification_flags=(
            _material_qualification_flags(planning_input.material)
            if status is CalculationReadinessStatus.READY
            else ()
        ),
        required=required,
    )


def _plan_shear_out(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> PlannedCheck:
    mapping = layer.mapping
    reasons: tuple[ApplicabilityReasonCode, ...]
    status_override = _geometry_or_distribution_status(planning_input, layer)
    if planning_input.demand.in_plane_force_magnitude.magnitude == 0:
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.ZERO_IN_PLANE_DEMAND,)
        required = False
    elif status_override is not None:
        status = status_override
        reasons = (ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,)
        required = True
    elif _property(planning_input.material, FRPPropertyKind.FSH_LT) is None:
        status = CalculationReadinessStatus.INCOMPLETE_INPUT
        reasons = (ApplicabilityReasonCode.REQUIRED_PROPERTY_MISSING,)
        required = True
    else:
        status = CalculationReadinessStatus.READY
        reasons = _base_ready_reasons()
        required = True
    warnings: tuple[str, ...] = ()
    if layer.potential_perpendicular_element_exemption:
        reasons = (
            *reasons,
            ApplicabilityReasonCode.POTENTIAL_PERPENDICULAR_ELEMENT_EXEMPTION_NOT_CREDITED,
        )
        warnings = ("Perpendicular return-element exemption was not credited.",)
    return _plan(
        planning_input,
        suffix=f"{mapping.physical_element_id}:shear_out",
        limit_state=LimitState.SHEAR_OUT,
        component_id=mapping.component_id,
        layer_id=mapping.physical_element_id,
        source_section="8.3.2.5",
        source_equation="8-8",
        status=status,
        reasons=reasons,
        required_property=FRPPropertyKind.FSH_LT,
        direction=mapping.direction_family,
        theta=mapping.theta_degrees,
        geometry_inputs=("e1", "hole_diameter", "layer_thickness"),
        include_lap=True,
        qualification_flags=(
            _material_qualification_flags(planning_input.material)
            if status is CalculationReadinessStatus.READY
            else ()
        ),
        warnings=warnings,
        required=required,
    )


def _plan_cleavage(
    planning_input: SingleBoltPlanningInput,
    layer: LayerPlanningInput,
) -> PlannedCheck:
    mapping = layer.mapping
    reasons: tuple[ApplicabilityReasonCode, ...]
    status_override = _geometry_or_distribution_status(planning_input, layer)
    if planning_input.demand.loading_sense is LayerLoadingSense.COMPRESSION:
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.COMPRESSION_EXCLUDES_TENSION_LIMIT_STATE,)
        required = False
    elif mapping.theta_degrees == Decimal("90"):
        status = CalculationReadinessStatus.NOT_APPLICABLE
        reasons = (ApplicabilityReasonCode.TRANSVERSE_TENSION_CLEAVAGE_NOT_APPLICABLE,)
        required = False
    elif mapping.direction_family is MaterialDirectionFamily.TRANSVERSE:
        status = CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
        reasons = (ApplicabilityReasonCode.OBLIQUE_TENSION_CLEAVAGE_NOT_SUPPORTED,)
        required = True
    elif status_override is not None:
        status = status_override
        reasons = (ApplicabilityReasonCode.GEOMETRY_REQUIREMENT_NOT_MET,)
        required = True
    elif (
        _property(planning_input.material, FRPPropertyKind.FT_L) is None
        or _property(planning_input.material, FRPPropertyKind.FSH_LT) is None
    ):
        status = CalculationReadinessStatus.INCOMPLETE_INPUT
        reasons = (ApplicabilityReasonCode.REQUIRED_PROPERTY_MISSING,)
        required = True
    else:
        status = CalculationReadinessStatus.READY
        reasons = _base_ready_reasons()
        required = True
    return _plan(
        planning_input,
        suffix=f"{mapping.physical_element_id}:cleavage",
        limit_state=LimitState.CLEAVAGE,
        component_id=mapping.component_id,
        layer_id=mapping.physical_element_id,
        source_section="8.3.2.6",
        source_equation="8-9a/b",
        status=status,
        reasons=reasons,
        required_property=FRPPropertyKind.FT_L,
        direction=mapping.direction_family,
        theta=mapping.theta_degrees,
        geometry_inputs=("e1", "e2", "hole_diameter", "layer_thickness"),
        include_lap=True,
        qualification_flags=(
            _material_qualification_flags(planning_input.material)
            if status is CalculationReadinessStatus.READY
            else ()
        ),
        unsupported=(
            ("Oblique tensile cleavage has no approved first-slice calculation.",)
            if status is CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
            else ()
        ),
        required=required,
    )


def plan_single_bolt_checks(
    planning_input: SingleBoltPlanningInput,
    *,
    supplied_fixture_results: tuple[SuppliedNumericalFixtureResult, ...] = (),
) -> SingleBoltPlanningResult:
    """Build all first-slice plans without resistance, capacity, or utilization."""

    checks: list[PlannedCheck] = list(_plan_bolt_checks(planning_input))
    for layer in planning_input.layers:
        checks.extend(
            (
                _plan_pull_through(planning_input, layer),
                _plan_bearing(planning_input, layer),
                _plan_net_tension(planning_input, layer),
                _plan_shear_out(planning_input, layer),
                _plan_cleavage(planning_input, layer),
            )
        )
    whole_status = (
        CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
        if planning_input.whole_connection_requires_section_2_3_2
        else CalculationReadinessStatus.READY
    )
    whole_statuses = (whole_status,) if whole_status is not CalculationReadinessStatus.READY else ()
    check_tuple = tuple(checks)
    return SingleBoltPlanningResult(
        checks=check_tuple,
        whole_connection_status=whole_status,
        aggregate_status=aggregate_planning_status(
            check_tuple,
            supplied_fixture_results,
            whole_statuses,
        ),
    )


__all__ = (
    "LayerPlanningInput",
    "SingleBoltPlanningInput",
    "SingleBoltPlanningResult",
    "plan_single_bolt_checks",
)
