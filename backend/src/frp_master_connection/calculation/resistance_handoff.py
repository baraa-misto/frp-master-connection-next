"""Pure Slice 3 RC1 compatibility handoff into the accepted Slice 2 resistance engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, localcontext
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    DemandAnalysisWarning,
    DemandAnalysisWarningCode,
    DemandScenarioResult,
    EccentricDemandResult,
    InPlaneQuantityVector,
    PerBoltDemandResult,
    Slice3VersionContext,
)
from frp_master_connection.calculation.multirow import (
    MaterialDirection,
    QualificationDisposition,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowBoltExecutionContext,
    MultiRowCalculationResult,
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowExecutableCheck,
    MultiRowExecutionBundle,
    MultiRowExecutionWarning,
    MultiRowLayerExecutionContext,
    MultiRowOverallDisposition,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    Slice2VersionContext,
    calculate_multirow_connection,
    multirow_execution_fingerprint,
)
from frp_master_connection.calculation.properties import FRPPropertyKind
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    canonical_decimal_string,
    decimal_value,
)
from frp_master_connection.calculation.results import (
    GOVERNING_UTILIZATION_TOLERANCE,
    NumericalComparison,
)

RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION = "2.5B-RC1"
RESISTANCE_HANDOFF_ENGINE_VERSION = "0.1.0.dev1"
RESISTANCE_HANDOFF_RULE_SET_VERSION = "asce74-23-ch8-eccentric-demand-resistance-handoff-rc1.dev1"
RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION = "0.1.0-draft"
RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION = "0.1.0-draft"
RESISTANCE_HANDOFF_DECIMAL_PRECISION = 80
BEARING_DIRECTION_BOUNDARY_DEGREES = Decimal("5")
BEARING_DIRECTION_RATIO_TOLERANCE = Decimal("1E-11")
_TAN_FIVE_DEGREES = Decimal("0.08748866352592400522201866943496145809171807993715822094670624")
_DECIMAL_PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286"
)


class ResistanceHandoffCoverage(StrEnum):
    FULL_LEGACY_COLLINEAR = "FULL_LEGACY_COLLINEAR"
    PARTIAL_ECCENTRIC = "PARTIAL_ECCENTRIC"
    BLOCKED_INCOMPLETE_ACTION_TRANSFER = "BLOCKED_INCOMPLETE_ACTION_TRANSFER"


class BearingForceDirection(StrEnum):
    DEFINED = "DEFINED"
    UNDEFINED_ZERO_DEMAND = "UNDEFINED_ZERO_DEMAND"


class ResistanceHandoffDemandSource(StrEnum):
    STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE = "STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE"
    EXPLICIT_BOLT_AXIS_TENSION = "EXPLICIT_BOLT_AXIS_TENSION"
    STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE = (
        "STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE"
    )
    STAGE_2_4B_LEGACY_DIRECT = "STAGE_2_4B_LEGACY_DIRECT"
    STAGE_2_4B_CONNECTION_RESULTANT = "STAGE_2_4B_CONNECTION_RESULTANT"
    STATUS_ONLY = "STATUS_ONLY"


class ResistanceHandoffTraceStage(StrEnum):
    DEMAND_ANALYSIS = "DEMAND_ANALYSIS"
    COMPATIBILITY_HANDOFF = "COMPATIBILITY_HANDOFF"
    RESISTANCE_CALCULATION = "RESISTANCE_CALCULATION"


class BlockShearCompatibilityStatus(StrEnum):
    MATCHED = "MATCHED"
    UNPROVEN = "UNPROVEN"


class ResistanceHandoffWarningCode(StrEnum):
    ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1 = (
        "ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1"
    )
    ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1 = (
        "ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1"
    )
    BLOCK_SHEAR_FORCE_LINE_COMPATIBILITY_NOT_PROVEN = (
        "BLOCK_SHEAR_FORCE_LINE_COMPATIBILITY_NOT_PROVEN"
    )
    REQUIRED_EXPLICIT_BOLT_AXIS_DEMAND_MISSING = "REQUIRED_EXPLICIT_BOLT_AXIS_DEMAND_MISSING"
    EXPLICIT_BOLT_AXIS_DEMAND_CONSUMED_NOT_GENERATED = (
        "EXPLICIT_BOLT_AXIS_DEMAND_CONSUMED_NOT_GENERATED"
    )
    PARENT_DEMAND_RESULT_NOT_CALCULATED = "PARENT_DEMAND_RESULT_NOT_CALCULATED"


@dataclass(frozen=True, slots=True)
class ResistanceHandoffVersionContext:
    calculation_contract_version: str = RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION
    resistance_handoff_engine_version: str = RESISTANCE_HANDOFF_ENGINE_VERSION
    resistance_handoff_rule_set_version: str = RESISTANCE_HANDOFF_RULE_SET_VERSION
    resistance_handoff_result_schema_version: str = RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION
    resistance_handoff_fingerprint_schema_version: str = (
        RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        expected = (
            RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION,
            RESISTANCE_HANDOFF_ENGINE_VERSION,
            RESISTANCE_HANDOFF_RULE_SET_VERSION,
            RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION,
            RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION,
        )
        if tuple(getattr(self, item.name) for item in fields(self)) != expected:
            raise ValueError("Resistance-handoff versions must use the approved RC1 identities.")


@dataclass(frozen=True, slots=True)
class ResistanceHandoffWarning:
    code: ResistanceHandoffWarningCode
    trace: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LayerBearingAxisContext:
    layer_id: str
    lw_axis: tuple[Decimal, Decimal]
    source_geometry_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.layer_id, "layer_id")
        if not isinstance(self.lw_axis, tuple) or len(self.lw_axis) != 2:
            raise TypeError("lw_axis must be an immutable two-Decimal tuple.")
        axis = tuple(decimal_value(item) for item in self.lw_axis)
        with localcontext() as context:
            context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
            length = (axis[0] * axis[0] + axis[1] * axis[1]).sqrt()
        if length.is_zero():
            raise ValueError("lw_axis cannot be zero.")
        with localcontext() as context:
            context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
            object.__setattr__(self, "lw_axis", (axis[0] / length, axis[1] / length))
        _require_unique_text_tuple(self.source_geometry_ids, "source_geometry_ids")


@dataclass(frozen=True, slots=True)
class ExplicitBoltAxisDemand:
    bolt_id: str
    demand: PhysicalQuantity
    source_id: str
    basis: str
    accepted: bool

    def __post_init__(self) -> None:
        for name in ("bolt_id", "source_id", "basis"):
            _require_text(cast(str, getattr(self, name)), name)
        if self.demand.dimension is not Dimension.FORCE or self.demand.magnitude < 0:
            raise ValueError("Explicit bolt-axis demand must be a nonnegative force.")
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be Boolean.")


@dataclass(frozen=True, slots=True)
class LayerInPlaneDemandAllocation:
    """A controlled layer fraction of one unchanged parent Stage 2.5A bolt vector."""

    bolt_id: str
    layer_id: str
    fraction: Decimal
    source_id: str
    parent_demand_fingerprint: str

    def __post_init__(self) -> None:
        for name in ("bolt_id", "layer_id", "source_id"):
            _require_text(cast(str, getattr(self, name)), name)
        fraction = decimal_value(self.fraction)
        if fraction <= 0 or fraction > 1:
            raise ValueError(
                "A layer in-plane demand fraction must be greater than zero and at most one."
            )
        object.__setattr__(self, "fraction", fraction)
        if len(self.parent_demand_fingerprint) != 64 or any(
            item not in "0123456789abcdef" for item in self.parent_demand_fingerprint
        ):
            raise ValueError("parent_demand_fingerprint must be lowercase SHA-256.")


@dataclass(frozen=True, slots=True)
class BlockShearCompatibilityEvidence:
    status: BlockShearCompatibilityStatus
    compatibility_id: str
    action_source_id: str
    demand_interface_id: str
    resistance_source_id: str
    resistance_interface_id: str
    eccentricity_reference: str
    source_geometry_ids: tuple[str, ...]
    compatible_check_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, BlockShearCompatibilityStatus):
            raise TypeError("status must be BlockShearCompatibilityStatus.")
        for name in (
            "compatibility_id",
            "action_source_id",
            "demand_interface_id",
            "resistance_source_id",
            "resistance_interface_id",
            "eccentricity_reference",
        ):
            _require_text(cast(str, getattr(self, name)), name)
        _require_unique_text_tuple(self.source_geometry_ids, "source_geometry_ids")
        _require_unique_text_tuple(self.compatible_check_ids, "compatible_check_ids", True)


@dataclass(frozen=True, slots=True)
class EccentricResistanceHandoffInput:
    demand_result: EccentricDemandResult
    scenario_id: str
    execution_bundle: MultiRowExecutionBundle
    layer_axes: tuple[LayerBearingAxisContext, ...]
    explicit_axis_demands: tuple[ExplicitBoltAxisDemand, ...] = ()
    block_shear_compatibility: BlockShearCompatibilityEvidence | None = None
    source_trace: tuple[str, ...] = ()
    versions: ResistanceHandoffVersionContext = ResistanceHandoffVersionContext()
    layer_demand_allocations: tuple[LayerInPlaneDemandAllocation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.demand_result, EccentricDemandResult):
            raise TypeError("demand_result must be EccentricDemandResult.")
        if not isinstance(self.execution_bundle, MultiRowExecutionBundle):
            raise TypeError("execution_bundle must be MultiRowExecutionBundle.")
        _require_text(self.scenario_id, "scenario_id")
        _require_typed_tuple(self.layer_axes, LayerBearingAxisContext, "layer_axes")
        _require_typed_tuple(
            self.explicit_axis_demands, ExplicitBoltAxisDemand, "explicit_axis_demands"
        )
        _require_unique((item.layer_id for item in self.layer_axes), "layer-axis IDs")
        _require_unique((item.bolt_id for item in self.explicit_axis_demands), "axis-demand IDs")
        if self.block_shear_compatibility is not None and not isinstance(
            self.block_shear_compatibility, BlockShearCompatibilityEvidence
        ):
            raise TypeError(
                "block_shear_compatibility must be BlockShearCompatibilityEvidence or None."
            )
        _require_unique_text_tuple(self.source_trace, "source_trace", True)
        if not isinstance(self.versions, ResistanceHandoffVersionContext):
            raise TypeError("versions must be ResistanceHandoffVersionContext.")
        _require_typed_tuple(
            self.layer_demand_allocations,
            LayerInPlaneDemandAllocation,
            "layer_demand_allocations",
        )
        if self.demand_result.interface_frame.interface_id != (
            self.execution_bundle.physical_geometry.interface_id
        ):
            raise ValueError("Parent demand and resistance interface identities must match.")
        demand_bolts = {item.bolt_id for item in self.demand_result.bolts}
        resistance_bolts = {item.bolt_id for item in self.execution_bundle.bolts}
        if demand_bolts != resistance_bolts:
            raise ValueError("Parent demand and resistance bolt identities must match.")
        if not {item.bolt_id for item in self.explicit_axis_demands} <= resistance_bolts:
            raise ValueError("Every explicit axis demand must identify a physical bolt.")
        resistance_layers = {item.layer_id for item in self.execution_bundle.layers}
        if {item.layer_id for item in self.layer_axes} != resistance_layers:
            raise ValueError("Every resistance layer requires exactly one authoritative LW axis.")
        allocation_keys = tuple(
            (item.bolt_id, item.layer_id) for item in self.layer_demand_allocations
        )
        _require_unique(allocation_keys, "layer-demand allocation keys")
        if not {item.bolt_id for item in self.layer_demand_allocations} <= resistance_bolts:
            raise ValueError("Every layer-demand allocation must identify a physical bolt.")
        if not {item.layer_id for item in self.layer_demand_allocations} <= resistance_layers:
            raise ValueError("Every layer-demand allocation must identify a penetrated layer.")
        if any(
            item.parent_demand_fingerprint != self.demand_result.result_fingerprint
            for item in self.layer_demand_allocations
        ):
            raise ValueError("Layer allocations must preserve the parent demand fingerprint.")
        if self.layer_demand_allocations:
            expected_allocation_keys = {
                (bolt.bolt_id, layer_id)
                for bolt in self.execution_bundle.bolts
                for layer_id in bolt.layer_ids
            }
            if set(allocation_keys) != expected_allocation_keys:
                raise ValueError(
                    "Layer-demand allocations must cover every penetrated bolt layer exactly."
                )
            for layer_id in resistance_layers:
                fractions = {
                    item.fraction
                    for item in self.layer_demand_allocations
                    if item.layer_id == layer_id
                }
                if len(fractions) != 1:
                    raise ValueError(
                        "Group-level FRP checks require one controlled fraction per layer."
                    )


@dataclass(frozen=True, slots=True)
class ResistanceHandoffFingerprintEnvelope:
    calculation_input: EccentricResistanceHandoffInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    request_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class PerBoltHandoffDemand:
    bolt_id: str
    force: InPlaneQuantityVector
    magnitude: PhysicalQuantity
    bearing_force_direction: BearingForceDirection


@dataclass(frozen=True, slots=True)
class BearingDirectionSelection:
    bolt_id: str
    layer_id: str
    force: InPlaneQuantityVector
    lw_axis: tuple[Decimal, Decimal]
    angle_degrees: Decimal | None
    direction: BearingForceDirection
    material_direction: MaterialDirection | None
    property_kind: FRPPropertyKind | None
    property_entry_id: str | None
    property_source_document: str | None


@dataclass(frozen=True, slots=True)
class ResistanceCheckHandoff:
    check_id: str
    family: MultiRowCheckFamily
    availability: MultiRowResultAvailability
    demand_source: ResistanceHandoffDemandSource
    resistance_result: MultiRowCheckResult | None
    warnings: tuple[ResistanceHandoffWarning, ...]
    axis_demand_source: ResistanceHandoffDemandSource | None = None


@dataclass(frozen=True, slots=True)
class EccentricResistanceHandoffResult:
    parent_demand_input_fingerprint: str
    parent_demand_result_fingerprint: str
    parent_demand_versions: Slice3VersionContext
    parent_resistance_input_fingerprint: str
    parent_resistance_versions: Slice2VersionContext
    versions: ResistanceHandoffVersionContext
    coverage: ResistanceHandoffCoverage
    parent_action_transfer_warnings: tuple[DemandAnalysisWarning, ...]
    per_bolt_demands: tuple[PerBoltHandoffDemand, ...]
    bearing_selections: tuple[BearingDirectionSelection, ...]
    checks: tuple[ResistanceCheckHandoff, ...]
    supported_results: tuple[MultiRowCheckResult, ...]
    unsupported_required_check_ids: tuple[str, ...]
    incomplete_required_check_ids: tuple[str, ...]
    block_shear_compatibility: BlockShearCompatibilityEvidence | None
    qualification: QualificationDisposition
    warnings: tuple[ResistanceHandoffWarning, ...]
    resistance_warnings: tuple[MultiRowExecutionWarning, ...]
    numerical_comparison: NumericalComparison
    governing_supported_check_ids: tuple[str, ...]
    overall_disposition: MultiRowOverallDisposition
    trace_stages: tuple[ResistanceHandoffTraceStage, ...]
    source_trace: tuple[str, ...]
    result_fingerprint: str
    legacy_result: MultiRowCalculationResult | None = None


def calculate_eccentric_resistance_handoff(
    handoff_input: EccentricResistanceHandoffInput,
) -> EccentricResistanceHandoffResult:
    """Evaluate the verified RC1 demand-to-resistance compatibility boundary."""

    if not isinstance(handoff_input, EccentricResistanceHandoffInput):
        raise TypeError("handoff_input must be EccentricResistanceHandoffInput.")
    scenario = _scenario(handoff_input)
    coverage = _coverage(handoff_input, scenario)
    per_bolt = tuple(_handoff_demand(item) for item in scenario.per_bolt)
    selections = tuple(
        _bearing_selection(handoff_input, item, axis)
        for item in scenario.per_bolt
        for axis in handoff_input.layer_axes
        if axis.layer_id in _bundle_bolt(handoff_input.execution_bundle, item.bolt_id).layer_ids
    )
    legacy_result: MultiRowCalculationResult | None = None
    if coverage is ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR:
        _validate_legacy_demands(handoff_input.execution_bundle, scenario, selections)
        legacy_result = calculate_multirow_connection(handoff_input.execution_bundle)
        checks = tuple(
            ResistanceCheckHandoff(
                item.result_id,
                item.limit_state,
                item.availability,
                ResistanceHandoffDemandSource.STAGE_2_4B_LEGACY_DIRECT,
                item if item.availability is MultiRowResultAvailability.CALCULATED else None,
                (),
            )
            for item in legacy_result.results
        )
    else:
        checks = tuple(
            _handoff_check(handoff_input, scenario, check, selections)
            for check in handoff_input.execution_bundle.checks
        )
    required_ids = set(handoff_input.execution_bundle.required_checks.required_check_ids)
    required = tuple(item for item in checks if item.check_id in required_ids)
    supported = tuple(
        item.resistance_result for item in checks if item.resistance_result is not None
    )
    unsupported = tuple(
        item.check_id
        for item in required
        if item.availability is MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED
    )
    incomplete = tuple(
        item.check_id
        for item in required
        if item.availability is MultiRowResultAvailability.INCOMPLETE_INPUT
    )
    numerical = _numerical(required)
    qualification = _qualification(handoff_input)
    overall = _overall(coverage, required, numerical, qualification)
    warnings = _unique_handoff_warnings(
        tuple(warning for item in checks for warning in item.warnings)
    )
    resistance_warnings = tuple(
        dict.fromkeys(warning for item in supported for warning in item.warnings)
    )
    governing = _governing(supported, required_ids)
    trace_stages = (
        ResistanceHandoffTraceStage.DEMAND_ANALYSIS,
        ResistanceHandoffTraceStage.COMPATIBILITY_HANDOFF,
        ResistanceHandoffTraceStage.RESISTANCE_CALCULATION,
    )
    payload = (
        handoff_input.demand_result.result_fingerprint,
        multirow_execution_fingerprint(handoff_input.execution_bundle),
        coverage,
        per_bolt,
        selections,
        checks,
        unsupported,
        incomplete,
        handoff_input.block_shear_compatibility,
        qualification,
        warnings,
        resistance_warnings,
        numerical,
        governing,
        overall,
        trace_stages,
        handoff_input.source_trace,
        handoff_input.versions,
    )
    result_fingerprint = _sha256(payload)
    return EccentricResistanceHandoffResult(
        handoff_input.demand_result.input_fingerprint,
        handoff_input.demand_result.result_fingerprint,
        handoff_input.demand_result.versions,
        multirow_execution_fingerprint(handoff_input.execution_bundle),
        handoff_input.execution_bundle.versions,
        handoff_input.versions,
        coverage,
        handoff_input.demand_result.warnings,
        per_bolt,
        selections,
        checks,
        supported,
        unsupported,
        incomplete,
        handoff_input.block_shear_compatibility,
        qualification,
        warnings,
        resistance_warnings,
        numerical,
        governing,
        overall,
        trace_stages,
        handoff_input.source_trace,
        result_fingerprint,
        legacy_result,
    )


def resistance_handoff_input_fingerprint(value: EccentricResistanceHandoffInput) -> str:
    if not isinstance(value, EccentricResistanceHandoffInput):
        raise TypeError("value must be EccentricResistanceHandoffInput.")
    return _sha256(value)


def canonical_resistance_handoff_input_json(value: EccentricResistanceHandoffInput) -> str:
    if not isinstance(value, EccentricResistanceHandoffInput):
        raise TypeError("value must be EccentricResistanceHandoffInput.")
    return json.dumps(
        _canonicalize(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )


def _scenario(value: EccentricResistanceHandoffInput) -> DemandScenarioResult:
    for scenario in value.demand_result.scenarios:
        if scenario.scenario_id == value.scenario_id:
            return scenario
    raise ValueError("scenario_id must identify an accepted parent demand scenario.")


def _coverage(
    value: EccentricResistanceHandoffInput, scenario: DemandScenarioResult
) -> ResistanceHandoffCoverage:
    warnings = {item.code for item in value.demand_result.warnings}
    if scenario.availability is not DemandAnalysisAvailability.CALCULATED:
        return ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    if (
        DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL
        in warnings
    ):
        return ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    required_axis_bolts = {
        item.bolt_id
        for item in value.execution_bundle.checks
        if item.check_id in value.execution_bundle.required_checks.required_check_ids
        and item.family
        in {
            MultiRowCheckFamily.BOLT_TENSION,
            MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
            MultiRowCheckFamily.PULL_THROUGH,
        }
        and item.bolt_id is not None
    }
    explicit = {item.bolt_id for item in value.explicit_axis_demands if item.accepted}
    if value.demand_result.projected_force.n.magnitude != 0 and not required_axis_bolts <= explicit:
        return ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    if value.layer_demand_allocations:
        return ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    return (
        ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR
        if scenario.residual_moment.magnitude == 0
        else ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    )


def _handoff_demand(item: PerBoltDemandResult) -> PerBoltHandoffDemand:
    direction = (
        BearingForceDirection.UNDEFINED_ZERO_DEMAND
        if item.total_force_magnitude.magnitude == 0
        else BearingForceDirection.DEFINED
    )
    return PerBoltHandoffDemand(
        item.bolt_id, item.total_force, item.total_force_magnitude, direction
    )


def _bearing_selection(
    value: EccentricResistanceHandoffInput,
    demand: PerBoltDemandResult,
    axis: LayerBearingAxisContext,
) -> BearingDirectionSelection:
    if demand.total_force_magnitude.magnitude == 0:
        return BearingDirectionSelection(
            demand.bolt_id,
            axis.layer_id,
            demand.total_force,
            axis.lw_axis,
            None,
            BearingForceDirection.UNDEFINED_ZERO_DEMAND,
            None,
            None,
            None,
            None,
        )
    u = demand.total_force.u.to_canonical().magnitude
    v = demand.total_force.v.to_canonical().magnitude
    angle = _acute_angle_degrees((u, v), axis.lw_axis)
    direction = _material_direction((u, v), axis.lw_axis)
    kind = (
        FRPPropertyKind.FBR_L
        if direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FBR_T
    )
    layer = _bundle_layer(value.execution_bundle, axis.layer_id)
    entry = next(item for item in layer.material.properties if item.kind is kind)
    return BearingDirectionSelection(
        demand.bolt_id,
        axis.layer_id,
        demand.total_force,
        axis.lw_axis,
        angle,
        BearingForceDirection.DEFINED,
        direction,
        kind,
        f"{layer.material.id}:{entry.kind.value}",
        entry.source_document,
    )


def _material_direction(
    force: tuple[Decimal, Decimal], axis: tuple[Decimal, Decimal]
) -> MaterialDirection:
    dot = abs(force[0] * axis[0] + force[1] * axis[1])
    cross = abs(force[0] * axis[1] - force[1] * axis[0])
    if dot == 0:
        return MaterialDirection.TRANSVERSE
    ratio = cross / dot
    return (
        MaterialDirection.LONGITUDINAL
        if ratio <= _TAN_FIVE_DEGREES + BEARING_DIRECTION_RATIO_TOLERANCE
        else MaterialDirection.TRANSVERSE
    )


def _acute_angle_degrees(force: tuple[Decimal, Decimal], axis: tuple[Decimal, Decimal]) -> Decimal:
    dot = abs(force[0] * axis[0] + force[1] * axis[1])
    cross = abs(force[0] * axis[1] - force[1] * axis[0])
    if dot == 0:
        return Decimal(90)
    return _atan(cross / dot) * Decimal(180) / _DECIMAL_PI


def _atan(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION + 8
        inverse = value > 1
        current = Decimal(1) / value if inverse else value
        multiplier = Decimal(1)
        while current > Decimal("0.1"):
            current = current / (Decimal(1) + (Decimal(1) + current * current).sqrt())
            multiplier *= 2
        total = Decimal(0)
        power = current
        sign = Decimal(1)
        denominator = 1
        threshold = Decimal(1).scaleb(-(RESISTANCE_HANDOFF_DECIMAL_PRECISION + 4))
        while True:
            term = sign * power / denominator
            total += term
            if abs(term) <= threshold:
                break
            power *= current * current
            sign = -sign
            denominator += 2
        angle = multiplier * total
        return +(_DECIMAL_PI / 2 - angle if inverse else angle)


def _handoff_check(
    value: EccentricResistanceHandoffInput,
    scenario: DemandScenarioResult,
    check: MultiRowExecutableCheck,
    selections: tuple[BearingDirectionSelection, ...],
) -> ResistanceCheckHandoff:
    if scenario.availability is not DemandAnalysisAvailability.CALCULATED:
        return _unavailable(
            check,
            MultiRowResultAvailability.INCOMPLETE_INPUT,
            ResistanceHandoffDemandSource.STATUS_ONLY,
            ResistanceHandoffWarningCode.PARENT_DEMAND_RESULT_NOT_CALCULATED,
        )
    if check.family in {
        MultiRowCheckFamily.CODE_GEOMETRY,
        MultiRowCheckFamily.QUALIFICATION,
        MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW,
    }:
        return _execute_one(
            value.execution_bundle, check, ResistanceHandoffDemandSource.STATUS_ONLY
        )
    if (
        check.family
        in {
            MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
            MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        }
        and scenario.residual_moment.magnitude != 0
    ):
        code = (
            ResistanceHandoffWarningCode.ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1
            if check.family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
            else ResistanceHandoffWarningCode.ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1
        )
        return _unavailable(
            check,
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
            ResistanceHandoffDemandSource.STATUS_ONLY,
            code,
        )
    if check.family in {
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
    }:
        allocation = _group_layer_allocation(value, check.layer_id)
        fraction = Decimal(1) if allocation is None else allocation.fraction
        return _execute_one(
            value.execution_bundle,
            replace(
                check,
                demand=None if check.demand is None else check.demand * fraction,
            ),
            (
                ResistanceHandoffDemandSource.STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE
                if allocation is not None
                else ResistanceHandoffDemandSource.STAGE_2_4B_CONNECTION_RESULTANT
            ),
        )
    if check.family is MultiRowCheckFamily.BLOCK_SHEAR:
        allocation = _group_layer_allocation(value, check.layer_id)
        fraction = Decimal(1) if allocation is None else allocation.fraction
        source = (
            ResistanceHandoffDemandSource.STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE
            if allocation is not None
            else ResistanceHandoffDemandSource.STAGE_2_4B_CONNECTION_RESULTANT
        )
        if not _block_compatible(value, check):
            return _unavailable(
                check,
                MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
                source,
                ResistanceHandoffWarningCode.BLOCK_SHEAR_FORCE_LINE_COMPATIBILITY_NOT_PROVEN,
            )
        return _execute_one(
            value.execution_bundle,
            replace(
                check,
                demand=value.execution_bundle.signed_demand.in_plane_magnitude * fraction,
            ),
            source,
        )
    demand = _scenario_bolt(scenario, check.bolt_id)
    if check.family in {MultiRowCheckFamily.BOLT_SHEAR, MultiRowCheckFamily.PIN_BEARING}:
        allocation = _layer_allocation(value, check.bolt_id, check.layer_id)
        fraction = Decimal(1) if allocation is None else allocation.fraction
        allocated = _scaled_demand(demand, fraction)
        if allocated.total_force_magnitude.magnitude == 0:
            return ResistanceCheckHandoff(
                check.check_id,
                check.family,
                MultiRowResultAvailability.NOT_APPLICABLE,
                ResistanceHandoffDemandSource.STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE,
                None,
                (),
            )
        bundle = _bundle_with_bolt_demand(value.execution_bundle, allocated)
        if check.family is MultiRowCheckFamily.PIN_BEARING:
            selection = next(
                item
                for item in selections
                if item.bolt_id == check.bolt_id and item.layer_id == check.layer_id
            )
            bundle = _bundle_with_layer_direction(
                bundle,
                cast(str, check.layer_id),
                cast(MaterialDirection, selection.material_direction),
            )
        return _execute_one(
            bundle,
            replace(check, demand=allocated.total_force_magnitude),
            (
                ResistanceHandoffDemandSource.STAGE_3_3B_LAYER_ALLOCATED_TOTAL_VECTOR_MAGNITUDE
                if allocation is not None
                else ResistanceHandoffDemandSource.STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE
            ),
        )
    explicit = _explicit_axis_demand(value, check.bolt_id)
    if explicit is None:
        return _unavailable(
            check,
            MultiRowResultAvailability.INCOMPLETE_INPUT,
            ResistanceHandoffDemandSource.EXPLICIT_BOLT_AXIS_TENSION,
            ResistanceHandoffWarningCode.REQUIRED_EXPLICIT_BOLT_AXIS_DEMAND_MISSING,
        )
    bundle = _bundle_with_axis_demand(value.execution_bundle, demand, explicit)
    check_demand = explicit.demand
    executed = _execute_one(
        bundle,
        replace(check, demand=check_demand),
        ResistanceHandoffDemandSource.EXPLICIT_BOLT_AXIS_TENSION,
    )
    return replace(
        executed,
        demand_source=(
            ResistanceHandoffDemandSource.STAGE_2_5A_TOTAL_VECTOR_MAGNITUDE
            if check.family is MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR
            else ResistanceHandoffDemandSource.EXPLICIT_BOLT_AXIS_TENSION
        ),
        warnings=(
            ResistanceHandoffWarning(
                ResistanceHandoffWarningCode.EXPLICIT_BOLT_AXIS_DEMAND_CONSUMED_NOT_GENERATED,
                (f"bolt_id:{explicit.bolt_id}", f"source_id:{explicit.source_id}"),
            ),
        ),
        axis_demand_source=ResistanceHandoffDemandSource.EXPLICIT_BOLT_AXIS_TENSION,
    )


def _execute_one(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
    source: ResistanceHandoffDemandSource,
) -> ResistanceCheckHandoff:
    single = replace(
        bundle, required_checks=MultiRowRequiredCheckContract((check.check_id,)), checks=(check,)
    )
    result = calculate_multirow_connection(single).results[0]
    return ResistanceCheckHandoff(
        check.check_id,
        check.family,
        result.availability,
        source,
        result if result.availability is MultiRowResultAvailability.CALCULATED else None,
        (),
    )


def _unavailable(
    check: MultiRowExecutableCheck,
    availability: MultiRowResultAvailability,
    source: ResistanceHandoffDemandSource,
    warning: ResistanceHandoffWarningCode,
) -> ResistanceCheckHandoff:
    return ResistanceCheckHandoff(
        check.check_id,
        check.family,
        availability,
        source,
        None,
        (ResistanceHandoffWarning(warning, (f"check_id:{check.check_id}",)),),
    )


def _bundle_with_bolt_demand(
    bundle: MultiRowExecutionBundle, demand: PerBoltDemandResult
) -> MultiRowExecutionBundle:
    bolts = tuple(
        replace(item, in_plane_demand=demand.total_force_magnitude)
        if item.bolt_id == demand.bolt_id
        else item
        for item in bundle.bolts
    )
    return replace(bundle, bolts=bolts)


def _layer_allocation(
    value: EccentricResistanceHandoffInput,
    bolt_id: str | None,
    layer_id: str | None,
) -> LayerInPlaneDemandAllocation | None:
    if bolt_id is None or layer_id is None:
        return None
    return next(
        (
            item
            for item in value.layer_demand_allocations
            if item.bolt_id == bolt_id and item.layer_id == layer_id
        ),
        None,
    )


def _group_layer_allocation(
    value: EccentricResistanceHandoffInput,
    layer_id: str | None,
) -> LayerInPlaneDemandAllocation | None:
    if layer_id is None:
        return None
    return next(
        (item for item in value.layer_demand_allocations if item.layer_id == layer_id),
        None,
    )


def _scaled_demand(value: PerBoltDemandResult, fraction: Decimal) -> PerBoltDemandResult:
    if fraction == Decimal(1):
        return value
    return replace(
        value,
        total_force=InPlaneQuantityVector(
            value.total_force.u * fraction,
            value.total_force.v * fraction,
        ),
        total_force_magnitude=value.total_force_magnitude * fraction,
    )


def _bundle_with_axis_demand(
    bundle: MultiRowExecutionBundle,
    demand: PerBoltDemandResult,
    explicit: ExplicitBoltAxisDemand,
) -> MultiRowExecutionBundle:
    base = _bundle_with_bolt_demand(bundle, demand)
    bolts = tuple(
        replace(
            item,
            bolt_axis_tension_demand=explicit.demand,
            bolt_axis_tension_required=True,
        )
        if item.bolt_id == demand.bolt_id
        else item
        for item in base.bolts
    )
    return replace(base, bolts=bolts)


def _bundle_with_layer_direction(
    bundle: MultiRowExecutionBundle, layer_id: str, direction: MaterialDirection
) -> MultiRowExecutionBundle:
    layers = tuple(
        replace(item, material_direction=direction) if item.layer_id == layer_id else item
        for item in bundle.layers
    )
    return replace(bundle, layers=layers)


def _block_compatible(
    value: EccentricResistanceHandoffInput, check: MultiRowExecutableCheck
) -> bool:
    evidence = value.block_shear_compatibility
    eccentricity = value.execution_bundle.eccentricity
    return bool(
        evidence is not None
        and evidence.status is BlockShearCompatibilityStatus.MATCHED
        and check.check_id in evidence.compatible_check_ids
        and evidence.action_source_id == value.demand_result.action_source_id
        and evidence.demand_interface_id == value.demand_result.interface_frame.interface_id
        and evidence.resistance_source_id == value.execution_bundle.signed_demand.source_id
        and evidence.resistance_interface_id
        == value.execution_bundle.physical_geometry.interface_id
        and eccentricity is not None
        and evidence.eccentricity_reference == eccentricity.geometric_reference
        and evidence.source_geometry_ids == eccentricity.source_geometry_ids
    )


def _validate_legacy_demands(
    bundle: MultiRowExecutionBundle,
    scenario: DemandScenarioResult,
    selections: tuple[BearingDirectionSelection, ...],
) -> None:
    parent = {item.bolt_id: item.total_force_magnitude for item in scenario.per_bolt}
    if any(item.in_plane_demand != parent[item.bolt_id] for item in bundle.bolts):
        raise ValueError("Full legacy handoff requires identical inherited direct bolt demands.")
    layers = {item.layer_id: item.material_direction for item in bundle.layers}
    if any(
        item.material_direction is not None and item.material_direction is not layers[item.layer_id]
        for item in selections
    ):
        raise ValueError("Full legacy handoff requires identical accepted material direction.")


def _scenario_bolt(scenario: DemandScenarioResult, bolt_id: str | None) -> PerBoltDemandResult:
    for item in scenario.per_bolt:
        if item.bolt_id == bolt_id:
            return item
    raise ValueError("A bolt-level handoff check requires an accepted parent bolt ID.")


def _explicit_axis_demand(
    value: EccentricResistanceHandoffInput, bolt_id: str | None
) -> ExplicitBoltAxisDemand | None:
    return next(
        (item for item in value.explicit_axis_demands if item.bolt_id == bolt_id and item.accepted),
        None,
    )


def _bundle_bolt(bundle: MultiRowExecutionBundle, bolt_id: str) -> MultiRowBoltExecutionContext:
    return next(item for item in bundle.bolts if item.bolt_id == bolt_id)


def _bundle_layer(bundle: MultiRowExecutionBundle, layer_id: str) -> MultiRowLayerExecutionContext:
    return next(item for item in bundle.layers if item.layer_id == layer_id)


def _numerical(required: tuple[ResistanceCheckHandoff, ...]) -> NumericalComparison:
    comparisons = tuple(
        item.resistance_result.numerical_comparison
        for item in required
        if item.resistance_result is not None
    )
    if NumericalComparison.FAIL in comparisons:
        return NumericalComparison.FAIL
    if any(
        item.availability
        not in {MultiRowResultAvailability.CALCULATED, MultiRowResultAvailability.NOT_APPLICABLE}
        for item in required
    ):
        return NumericalComparison.NOT_EVALUATED
    return NumericalComparison.PASS if comparisons else NumericalComparison.NOT_EVALUATED


def _qualification(
    value: EccentricResistanceHandoffInput,
) -> QualificationDisposition:
    values = (
        value.demand_result.qualification,
        *(item.qualification for item in value.execution_bundle.checks),
    )
    if QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED in values:
        return QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if QualificationDisposition.ENGINEERING_REVIEW_REQUIRED in values:
        return QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
    return QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE


def _overall(
    coverage: ResistanceHandoffCoverage,
    required: tuple[ResistanceCheckHandoff, ...],
    numerical: NumericalComparison,
    qualification: QualificationDisposition,
) -> MultiRowOverallDisposition:
    if numerical is NumericalComparison.FAIL:
        return MultiRowOverallDisposition.FAIL
    if coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER:
        return MultiRowOverallDisposition.NOT_EVALUATED
    if any(item.availability is MultiRowResultAvailability.INVALID_GEOMETRY for item in required):
        return MultiRowOverallDisposition.INVALID_GEOMETRY
    if any(
        item.availability
        in {
            MultiRowResultAvailability.INCOMPLETE_INPUT,
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
        }
        for item in required
    ):
        return MultiRowOverallDisposition.NOT_EVALUATED
    if qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED:
        return MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED:
        return MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED
    return MultiRowOverallDisposition.PASS


def _governing(
    supported: tuple[MultiRowCheckResult, ...], required_ids: set[str]
) -> tuple[str, ...]:
    candidates = tuple(
        item
        for item in supported
        if item.result_id in required_ids and item.utilization is not None
    )
    if not candidates:
        return ()
    maximum = max(cast(Decimal, item.utilization) for item in candidates)
    return tuple(
        item.result_id
        for item in candidates
        if maximum - cast(Decimal, item.utilization) <= GOVERNING_UTILIZATION_TOLERANCE
    )


def _unique_handoff_warnings(
    warnings: tuple[ResistanceHandoffWarning, ...],
) -> tuple[ResistanceHandoffWarning, ...]:
    return tuple(dict.fromkeys(warnings))


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonicalize(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonicalize(value: object) -> object:
    if isinstance(value, ResistanceHandoffFingerprintEnvelope):
        return _canonicalize(value.calculation_input)
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "magnitude": value.canonical_string,
            "unit": value.canonical_unit.value,
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise TypeError("Resistance-handoff fingerprints reject authoritative binary floats.")
    raise TypeError(f"Unsupported resistance-handoff fingerprint value {type(value).__name__}.")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text.")


def _require_unique(values: Iterable[object], name: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"{name} must be unique.")


def _require_unique_text_tuple(
    value: tuple[str, ...], name: str, allow_empty: bool = False
) -> None:
    if not isinstance(value, tuple) or (not value and not allow_empty):
        raise ValueError(f"{name} must be an immutable nonempty tuple.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must contain nonempty text.")
    _require_unique(value, name)


def _require_typed_tuple(value: tuple[object, ...], expected: type, name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, expected) for item in value):
        raise TypeError(f"{name} must be an immutable tuple of {expected.__name__} values.")


__all__ = (
    "BEARING_DIRECTION_BOUNDARY_DEGREES",
    "BEARING_DIRECTION_RATIO_TOLERANCE",
    "RESISTANCE_HANDOFF_CALCULATION_CONTRACT_VERSION",
    "RESISTANCE_HANDOFF_DECIMAL_PRECISION",
    "RESISTANCE_HANDOFF_ENGINE_VERSION",
    "RESISTANCE_HANDOFF_FINGERPRINT_SCHEMA_VERSION",
    "RESISTANCE_HANDOFF_RESULT_SCHEMA_VERSION",
    "RESISTANCE_HANDOFF_RULE_SET_VERSION",
    "BearingDirectionSelection",
    "BearingForceDirection",
    "BlockShearCompatibilityEvidence",
    "BlockShearCompatibilityStatus",
    "EccentricResistanceHandoffInput",
    "EccentricResistanceHandoffResult",
    "ExplicitBoltAxisDemand",
    "LayerBearingAxisContext",
    "LayerInPlaneDemandAllocation",
    "PerBoltHandoffDemand",
    "ResistanceCheckHandoff",
    "ResistanceHandoffCoverage",
    "ResistanceHandoffDemandSource",
    "ResistanceHandoffFingerprintEnvelope",
    "ResistanceHandoffTraceStage",
    "ResistanceHandoffVersionContext",
    "ResistanceHandoffWarning",
    "ResistanceHandoffWarningCode",
    "calculate_eccentric_resistance_handoff",
    "canonical_resistance_handoff_input_json",
    "resistance_handoff_input_fingerprint",
)
