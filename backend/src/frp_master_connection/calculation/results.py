"""Fail-closed planning and immutable numerical result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from frp_master_connection.calculation.properties import FRPPropertyKind
from frp_master_connection.calculation.quantities import PhysicalQuantity, decimal_value
from frp_master_connection.calculation.sources import (
    CalculationSourceSnapshot,
    QualificationStatus,
)

if TYPE_CHECKING:
    from frp_master_connection.calculation.applicability import SingleBoltPlanningResult
    from frp_master_connection.calculation.equations import EquationTrace


GOVERNING_UTILIZATION_TOLERANCE = Decimal("0.000000000001")


class LimitState(StrEnum):
    """Controlled first-slice limit-state identities."""

    BOLT_TENSION = "BOLT_TENSION"
    BOLT_SHEAR = "BOLT_SHEAR"
    BOLT_COMBINED_TENSION_SHEAR = "BOLT_COMBINED_TENSION_SHEAR"
    PULL_THROUGH = "PULL_THROUGH"
    PIN_BEARING = "PIN_BEARING"
    NET_SECTION_TENSION = "NET_SECTION_TENSION"
    SHEAR_OUT = "SHEAR_OUT"
    CLEAVAGE = "CLEAVAGE"


class MaterialDirectionFamily(StrEnum):
    """Approved directional property selection for a flat FRP layer."""

    LONGITUDINAL = "LONGITUDINAL"
    TRANSVERSE = "TRANSVERSE"


class CalculationReadinessStatus(StrEnum):
    """Planning state that never represents a numerical comparison."""

    READY = "READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    SOURCE_DATA_PENDING = "SOURCE_DATA_PENDING"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED = "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"


class FinalResultAvailability(StrEnum):
    """Approved availability vocabulary for future immutable result records."""

    CALCULATED = "CALCULATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    SOURCE_DATA_PENDING = "SOURCE_DATA_PENDING"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED = "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    STALE_RESULT = "STALE_RESULT"


class NumericalComparison(StrEnum):
    """Exact future numerical-comparison vocabulary."""

    PASS = "PASS"  # noqa: S105 - controlled engineering comparison vocabulary
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class ApplicabilityReasonCode(StrEnum):
    """Deterministic reason codes used by first-slice planning."""

    READY_FOR_FUTURE_NUMERICAL_IMPLEMENTATION = "READY_FOR_FUTURE_NUMERICAL_IMPLEMENTATION"
    PHYSICAL_NUMERICAL_EVALUATION_NOT_AUTHORIZED = "PHYSICAL_NUMERICAL_EVALUATION_NOT_AUTHORIZED"
    LOCKED_FASTENER_FNT_SOURCE_PENDING = "LOCKED_FASTENER_FNT_SOURCE_PENDING"
    EXPLICIT_FNT_RETAINED = "EXPLICIT_FNT_RETAINED"
    SHEAR_PLANE_REQUIRED = "SHEAR_PLANE_REQUIRED"
    MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED = "MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED"
    BOLT_AXIS_TENSION_AND_PRYING_ZERO = "BOLT_AXIS_TENSION_AND_PRYING_ZERO"
    POSITIVE_EXPLICIT_BOLT_AXIS_OR_PRYING_DEMAND = "POSITIVE_EXPLICIT_BOLT_AXIS_OR_PRYING_DEMAND"
    REQUIRED_PULL_THROUGH_INPUT_MISSING = "REQUIRED_PULL_THROUGH_INPUT_MISSING"
    ZERO_IN_PLANE_DEMAND = "ZERO_IN_PLANE_DEMAND"
    REQUIRED_PROPERTY_MISSING = "REQUIRED_PROPERTY_MISSING"
    ICE_DEVELOPMENT_PROPERTY_REQUIRES_REVIEW = "ICE_DEVELOPMENT_PROPERTY_REQUIRES_REVIEW"
    COMPRESSION_EXCLUDES_TENSION_LIMIT_STATE = "COMPRESSION_EXCLUDES_TENSION_LIMIT_STATE"
    EFFECTIVE_WIDTH_MAPPING_UNSUPPORTED = "EFFECTIVE_WIDTH_MAPPING_UNSUPPORTED"
    POTENTIAL_PERPENDICULAR_ELEMENT_EXEMPTION_NOT_CREDITED = (
        "POTENTIAL_PERPENDICULAR_ELEMENT_EXEMPTION_NOT_CREDITED"
    )
    TRANSVERSE_TENSION_CLEAVAGE_NOT_APPLICABLE = "TRANSVERSE_TENSION_CLEAVAGE_NOT_APPLICABLE"
    OBLIQUE_TENSION_CLEAVAGE_NOT_SUPPORTED = "OBLIQUE_TENSION_CLEAVAGE_NOT_SUPPORTED"
    MEMBER_END_ACTION_NOT_DISTRIBUTED = "MEMBER_END_ACTION_NOT_DISTRIBUTED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    GEOMETRY_REQUIREMENT_NOT_MET = "GEOMETRY_REQUIREMENT_NOT_MET"
    EXACT_90_TRANSVERSE_INTERPRETATION = "EXACT_90_TRANSVERSE_INTERPRETATION"


@dataclass(frozen=True, slots=True)
class PlannedCheck:
    """Immutable applicability/readiness plan with no resistance or utilization."""

    check_id: str
    limit_state: LimitState
    component_id: str | None
    layer_id: str | None
    bolt_id: str
    source_section: str
    source_equation: str
    readiness_status: CalculationReadinessStatus
    numerical_comparison: NumericalComparison
    applicability_reason_codes: tuple[ApplicabilityReasonCode, ...]
    required_property_kind: FRPPropertyKind | None
    selected_direction_family: MaterialDirectionFamily | None
    theta_degrees: Decimal | None
    required_geometry_inputs: tuple[str, ...]
    factor_metadata: tuple[str, ...]
    qualification_flags: tuple[QualificationStatus, ...]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    unsupported_conditions: tuple[str, ...]
    input_fingerprint: str
    required: bool = True

    def __post_init__(self) -> None:
        if not self.check_id.strip() or not self.bolt_id.strip():
            raise ValueError("Planned-check and bolt identities must be nonempty.")
        if not self.source_section.strip() or not self.source_equation.strip():
            raise ValueError("Planned checks require source section/equation references.")
        if self.numerical_comparison is not NumericalComparison.NOT_EVALUATED:
            raise ValueError("Stage 2.1A physical-input plans must be NOT_EVALUATED.")
        if self.theta_degrees is not None:
            theta = decimal_value(self.theta_degrees)
            if theta < 0 or theta > 90:
                raise ValueError("Material angle must be in the inclusive range 0 to 90 degrees.")
            object.__setattr__(self, "theta_degrees", theta)
        collections = (
            self.applicability_reason_codes,
            self.required_geometry_inputs,
            self.factor_metadata,
            self.qualification_flags,
            self.warnings,
            self.assumptions,
            self.unsupported_conditions,
        )
        if any(not isinstance(collection, tuple) for collection in collections):
            raise TypeError("Planned-check collections must be immutable tuples.")
        if len(self.input_fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in self.input_fingerprint
        ):
            raise ValueError("Planned-check input fingerprint must be lowercase SHA-256 hex.")


@dataclass(frozen=True, slots=True)
class SuppliedNumericalFixtureResult:
    """A supplied expected outcome used only to exercise aggregation precedence."""

    check_id: str
    comparison: NumericalComparison
    required: bool = True

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("Fixture result check identity must be nonempty.")
        if self.comparison is NumericalComparison.NOT_EVALUATED:
            raise ValueError("A supplied numerical fixture result must be PASS or FAIL.")


class AggregatePlanningStatus(StrEnum):
    """Deterministic aggregate outcome without a production numerical calculation."""

    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FAIL = "FAIL"
    FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK = "FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK"
    BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED = "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    SOURCE_DATA_PENDING = "SOURCE_DATA_PENDING"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    READY_FOR_STAGE_2_1B = "READY_FOR_STAGE_2_1B"
    PASS = "PASS"  # noqa: S105 - controlled engineering comparison vocabulary


_READINESS_PRECEDENCE = (
    (
        CalculationReadinessStatus.INVALID_GEOMETRY,
        AggregatePlanningStatus.INVALID_GEOMETRY,
    ),
    (
        CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED,
        AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED,
    ),
    (
        CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    ),
    (
        CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED,
        AggregatePlanningStatus.CALCULATION_NOT_SUPPORTED,
    ),
    (
        CalculationReadinessStatus.INCOMPLETE_INPUT,
        AggregatePlanningStatus.INCOMPLETE_INPUT,
    ),
    (
        CalculationReadinessStatus.SOURCE_DATA_PENDING,
        AggregatePlanningStatus.SOURCE_DATA_PENDING,
    ),
    (
        CalculationReadinessStatus.ENGINEERING_REVIEW_REQUIRED,
        AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED,
    ),
)


def aggregate_planning_status(
    checks: tuple[PlannedCheck, ...],
    supplied_fixture_results: tuple[SuppliedNumericalFixtureResult, ...] = (),
    whole_connection_statuses: tuple[CalculationReadinessStatus, ...] = (),
) -> AggregatePlanningStatus:
    """Aggregate required plans in the approved fail-closed precedence order."""

    required_checks = tuple(check for check in checks if check.required)
    statuses = {check.readiness_status for check in required_checks} | set(
        whole_connection_statuses
    )
    if CalculationReadinessStatus.INVALID_GEOMETRY in statuses:
        return AggregatePlanningStatus.INVALID_GEOMETRY

    known_failure = any(
        result.required and result.comparison is NumericalComparison.FAIL
        for result in supplied_fixture_results
    )
    if known_failure:
        unsupported = CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED in statuses
        return (
            AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK
            if unsupported
            else AggregatePlanningStatus.FAIL
        )

    for readiness, aggregate in _READINESS_PRECEDENCE[1:]:
        if readiness in statuses:
            return aggregate

    qualification_flags = {flag for check in required_checks for flag in check.qualification_flags}
    if QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED in qualification_flags:
        return AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if QualificationStatus.ENGINEERING_REVIEW_REQUIRED in qualification_flags:
        return AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED
    if required_checks and all(
        check.readiness_status is CalculationReadinessStatus.NOT_APPLICABLE
        for check in required_checks
    ):
        return AggregatePlanningStatus.NOT_APPLICABLE
    return AggregatePlanningStatus.READY_FOR_STAGE_2_1B


@dataclass(frozen=True, slots=True)
class FinalCalculationResult:
    """One immutable result that preserves its Stage 2.1A plan and equation trace."""

    plan: PlannedCheck
    availability: FinalResultAvailability
    numerical_comparison: NumericalComparison
    demand: PhysicalQuantity | None
    nominal_resistance: PhysicalQuantity | None
    design_resistance: PhysicalQuantity | None
    utilization: Decimal | None
    equation_trace: EquationTrace | None
    source_snapshot: CalculationSourceSnapshot
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PlannedCheck):
            raise TypeError("FinalCalculationResult.plan must be a PlannedCheck.")
        if not isinstance(self.source_snapshot, CalculationSourceSnapshot):
            raise TypeError("source_snapshot must be a CalculationSourceSnapshot.")
        if not isinstance(self.warnings, tuple):
            raise TypeError("Final calculation warnings must be an immutable tuple.")
        if self.utilization is not None:
            object.__setattr__(self, "utilization", decimal_value(self.utilization))
            if self.utilization < 0:
                raise ValueError("Utilization must be nonnegative when available.")
        calculated = self.availability is FinalResultAvailability.CALCULATED
        numerical_values = (
            self.demand,
            self.nominal_resistance,
            self.design_resistance,
            self.equation_trace,
        )
        if calculated:
            if any(value is None for value in numerical_values):
                raise ValueError("A calculated result requires demand, resistance, and trace data.")
            if self.numerical_comparison is NumericalComparison.NOT_EVALUATED:
                raise ValueError("A calculated result requires a PASS or FAIL comparison.")
            design = self.design_resistance
            if design is not None and design.magnitude > 0 and self.utilization is None:
                raise ValueError("Positive calculated resistance requires utilization.")
            if design is not None and design.magnitude <= 0 and self.utilization is not None:
                raise ValueError("Nonpositive calculated resistance cannot have utilization.")
        elif any(value is not None for value in (*numerical_values, self.utilization)):
            raise ValueError("An unavailable result cannot contain calculated numerical data.")
        elif self.numerical_comparison is not NumericalComparison.NOT_EVALUATED:
            raise ValueError("An unavailable result must remain NOT_EVALUATED.")


@dataclass(frozen=True, slots=True)
class SingleBoltCalculationResult:
    """Deterministic first-slice plans, results, aggregate status, and governing ties."""

    planning_result: SingleBoltPlanningResult
    results: tuple[FinalCalculationResult, ...]
    aggregate_status: AggregatePlanningStatus
    governing_check_ids: tuple[str, ...]
    input_fingerprint: str
    calculation_engine_version: str
    engineering_rule_set_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.results, tuple) or not isinstance(self.governing_check_ids, tuple):
            raise TypeError("Single-bolt result collections must be immutable tuples.")
        if tuple(result.plan for result in self.results) != self.planning_result.checks:
            raise ValueError("Final results must preserve deterministic planning order exactly.")
        if len(self.input_fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in self.input_fingerprint
        ):
            raise ValueError("Calculation result fingerprint must be lowercase SHA-256 hex.")
        if (
            not self.calculation_engine_version.strip()
            or not self.engineering_rule_set_version.strip()
        ):
            raise ValueError("Calculation and engineering rule-set versions are required.")


def aggregate_calculation_status(
    results: tuple[FinalCalculationResult, ...],
    whole_connection_status: CalculationReadinessStatus,
) -> AggregatePlanningStatus:
    """Apply the approved fail-closed precedence to executable numerical results."""

    required = tuple(result for result in results if result.plan.required)
    statuses = {result.plan.readiness_status for result in required}
    if whole_connection_status is not CalculationReadinessStatus.READY:
        statuses.add(whole_connection_status)
    if CalculationReadinessStatus.INVALID_GEOMETRY in statuses:
        return AggregatePlanningStatus.INVALID_GEOMETRY
    known_failure = any(
        result.numerical_comparison is NumericalComparison.FAIL for result in required
    )
    if known_failure:
        return (
            AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK
            if CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED in statuses
            else AggregatePlanningStatus.FAIL
        )
    for readiness, aggregate in _READINESS_PRECEDENCE[1:]:
        if readiness in statuses:
            return aggregate
    qualification_flags = {flag for result in required for flag in result.plan.qualification_flags}
    if QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED in qualification_flags:
        return AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if QualificationStatus.ENGINEERING_REVIEW_REQUIRED in qualification_flags:
        return AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED
    if required and all(
        result.availability is FinalResultAvailability.NOT_APPLICABLE for result in required
    ):
        return AggregatePlanningStatus.NOT_APPLICABLE
    return AggregatePlanningStatus.PASS


def governing_check_ids(
    results: tuple[FinalCalculationResult, ...],
) -> tuple[str, ...]:
    """Return every calculated check co-governing within the one named tolerance."""

    calculated = tuple(result for result in results if result.utilization is not None)
    if not calculated:
        return ()
    maximum = max(result.utilization for result in calculated if result.utilization is not None)
    return tuple(
        result.plan.check_id
        for result in calculated
        if result.utilization is not None
        and maximum - result.utilization <= GOVERNING_UTILIZATION_TOLERANCE
    )


__all__ = (
    "GOVERNING_UTILIZATION_TOLERANCE",
    "AggregatePlanningStatus",
    "ApplicabilityReasonCode",
    "CalculationReadinessStatus",
    "FinalCalculationResult",
    "FinalResultAvailability",
    "LimitState",
    "MaterialDirectionFamily",
    "NumericalComparison",
    "PlannedCheck",
    "SingleBoltCalculationResult",
    "SuppliedNumericalFixtureResult",
    "aggregate_calculation_status",
    "aggregate_planning_status",
    "governing_check_ids",
)
