"""Pure Stage 2.6A RC1 eccentric group-mode compatibility engine."""

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
    DemandScenarioResult,
    InPlaneQuantityVector,
    PerBoltDemandResult,
    Slice3VersionContext,
)
from frp_master_connection.calculation.multirow import QualificationDisposition
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowExecutableCheck,
    MultiRowExecutionBundle,
    MultiRowExecutionWarning,
    MultiRowOverallDisposition,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    Slice2VersionContext,
    calculate_multirow_connection,
    multirow_execution_fingerprint,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_value,
)
from frp_master_connection.calculation.resistance_handoff import (
    EccentricResistanceHandoffInput,
    EccentricResistanceHandoffResult,
    ResistanceCheckHandoff,
    ResistanceHandoffCoverage,
    ResistanceHandoffVersionContext,
    ResistanceHandoffWarning,
    resistance_handoff_input_fingerprint,
)
from frp_master_connection.calculation.results import (
    GOVERNING_UTILIZATION_TOLERANCE,
    NumericalComparison,
)

ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION = "2.6A-RC1"
ECCENTRIC_GROUP_MODE_ENGINE_VERSION = "0.1.0.dev1"
ECCENTRIC_GROUP_MODE_RULE_SET_VERSION = "asce74-23-ch8-eccentric-group-modes-rc1.dev1"
ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION = "0.1.0-draft"
ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION = "0.1.0-draft"
ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION = 80
RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF = "RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF"


class EccentricLineHandoffStatus(StrEnum):
    NOT_REQUIRED_ZERO_LINE_DEMAND = "NOT_REQUIRED_ZERO_LINE_DEMAND"
    AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT = "AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    INHERITED_LEGACY_STAGE_2_4B = "INHERITED_LEGACY_STAGE_2_4B"
    NOT_REQUIRED_PARENT_EXEMPTION = "NOT_REQUIRED_PARENT_EXEMPTION"


class EccentricFirstRowHandoffStatus(StrEnum):
    INHERITED_LEGACY_STAGE_2_4B = "INHERITED_LEGACY_STAGE_2_4B"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    NOT_REQUIRED_PARENT_EXEMPTION = "NOT_REQUIRED_PARENT_EXEMPTION"


class EccentricGroupModeWarningCode(StrEnum):
    ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE = (
        "ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE"
    )
    ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED = (
        "ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED"
    )
    ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1 = (
        "ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1"
    )
    ECCENTRIC_SHEAROUT_ZERO_CONNECTION_FORCE_NOT_SUPPORTED = (
        "ECCENTRIC_SHEAROUT_ZERO_CONNECTION_FORCE_NOT_SUPPORTED"
    )
    PARENT_RESISTANCE_HANDOFF_NOT_AVAILABLE = "PARENT_RESISTANCE_HANDOFF_NOT_AVAILABLE"


class EccentricGroupModeTraceStage(StrEnum):
    DEMAND_ANALYSIS = "DEMAND_ANALYSIS"
    RESISTANCE_HANDOFF = "RESISTANCE_HANDOFF"
    ECCENTRIC_GROUP_MODE_COMPATIBILITY = "ECCENTRIC_GROUP_MODE_COMPATIBILITY"
    RESISTANCE_CALCULATION = "RESISTANCE_CALCULATION"


@dataclass(frozen=True, slots=True)
class EccentricGroupModeVersionContext:
    calculation_contract_version: str = ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION
    eccentric_group_mode_engine_version: str = ECCENTRIC_GROUP_MODE_ENGINE_VERSION
    eccentric_group_mode_rule_set_version: str = ECCENTRIC_GROUP_MODE_RULE_SET_VERSION
    eccentric_group_mode_result_schema_version: str = ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION
    eccentric_group_mode_fingerprint_schema_version: str = (
        ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        expected = (
            ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION,
            ECCENTRIC_GROUP_MODE_ENGINE_VERSION,
            ECCENTRIC_GROUP_MODE_RULE_SET_VERSION,
            ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION,
            ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION,
        )
        if tuple(getattr(self, item.name) for item in fields(self)) != expected:
            raise ValueError("Eccentric group-mode versions must use the approved RC1 identities.")


@dataclass(frozen=True, slots=True)
class EccentricGroupModeWarning:
    code: EccentricGroupModeWarningCode
    trace: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, EccentricGroupModeWarningCode):
            raise TypeError("code must be EccentricGroupModeWarningCode.")
        _require_text_tuple(self.trace, "trace", allow_empty=True)


@dataclass(frozen=True, slots=True)
class EccentricLineBoltVector:
    bolt_id: str
    force: InPlaneQuantityVector

    def __post_init__(self) -> None:
        _require_text(self.bolt_id, "bolt_id")
        _require_force_vector(self.force, "force")


@dataclass(frozen=True, slots=True)
class EccentricBoltLineResult:
    bolt_line_id: str
    check_id: str | None
    contributing_bolt_ids: tuple[str, ...]
    bolt_vectors: tuple[EccentricLineBoltVector, ...]
    line_resultant: InPlaneQuantityVector
    parallel_scalar: PhysicalQuantity
    transverse_scalar: PhysicalQuantity
    handoff_status: EccentricLineHandoffStatus
    required_line_demand: PhysicalQuantity | None
    shear_out_result: MultiRowCheckResult | None
    warnings: tuple[EccentricGroupModeWarning, ...]
    method_id: str

    def __post_init__(self) -> None:
        _require_text(self.bolt_line_id, "bolt_line_id")
        if self.check_id is not None:
            _require_text(self.check_id, "check_id")
        _require_text_tuple(self.contributing_bolt_ids, "contributing_bolt_ids")
        _require_typed_tuple(self.bolt_vectors, EccentricLineBoltVector, "bolt_vectors")
        if tuple(item.bolt_id for item in self.bolt_vectors) != self.contributing_bolt_ids:
            raise ValueError("Bolt-vector identities must match contributing_bolt_ids exactly.")
        _require_force_vector(self.line_resultant, "line_resultant")
        _require_force(self.parallel_scalar, "parallel_scalar", allow_negative=True)
        _require_force(self.transverse_scalar, "transverse_scalar", allow_negative=True)
        if not isinstance(self.handoff_status, EccentricLineHandoffStatus):
            raise TypeError("handoff_status must be EccentricLineHandoffStatus.")
        if self.required_line_demand is not None:
            _require_force(self.required_line_demand, "required_line_demand")
        if self.shear_out_result is not None:
            if not isinstance(self.shear_out_result, MultiRowCheckResult):
                raise TypeError("shear_out_result must be MultiRowCheckResult or None.")
            if (
                self.shear_out_result.limit_state is not MultiRowCheckFamily.INTERROW_SHEAR_OUT
                or self.shear_out_result.bolt_line_id != self.bolt_line_id
            ):
                raise ValueError("Shear-out result must identify this physical bolt line.")
        _require_typed_tuple(self.warnings, EccentricGroupModeWarning, "warnings")
        _require_text(self.method_id, "method_id")
        if self.handoff_status in {
            EccentricLineHandoffStatus.AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT,
            EccentricLineHandoffStatus.INHERITED_LEGACY_STAGE_2_4B,
        }:
            if self.required_line_demand is None or self.check_id is None:
                raise ValueError(
                    "Authorized or inherited line handoff requires demand and check ID."
                )
        elif self.required_line_demand is not None or self.shear_out_result is not None:
            raise ValueError("Unsupported or exempt line state cannot retain resistance numerics.")


@dataclass(frozen=True, slots=True)
class EccentricFirstRowCompatibility:
    status: EccentricFirstRowHandoffStatus
    required_check_ids: tuple[str, ...]
    warnings: tuple[EccentricGroupModeWarning, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, EccentricFirstRowHandoffStatus):
            raise TypeError("status must be EccentricFirstRowHandoffStatus.")
        _require_text_tuple(self.required_check_ids, "required_check_ids", allow_empty=True)
        _require_typed_tuple(self.warnings, EccentricGroupModeWarning, "warnings")
        if (
            self.status is EccentricFirstRowHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION
            and self.required_check_ids
        ):
            raise ValueError("A parent-exempt first-row state cannot retain required check IDs.")


@dataclass(frozen=True, slots=True)
class EccentricGroupModeCompatibilityInput:
    parent_handoff_input: EccentricResistanceHandoffInput
    parent_handoff_result: EccentricResistanceHandoffResult
    source_trace: tuple[str, ...]
    versions: EccentricGroupModeVersionContext = EccentricGroupModeVersionContext()

    def __post_init__(self) -> None:
        if not isinstance(self.parent_handoff_input, EccentricResistanceHandoffInput):
            raise TypeError("parent_handoff_input must be EccentricResistanceHandoffInput.")
        if not isinstance(self.parent_handoff_result, EccentricResistanceHandoffResult):
            raise TypeError("parent_handoff_result must be EccentricResistanceHandoffResult.")
        _require_text_tuple(self.source_trace, "source_trace", allow_empty=True)
        if not isinstance(self.versions, EccentricGroupModeVersionContext):
            raise TypeError("versions must be EccentricGroupModeVersionContext.")
        parent_input = self.parent_handoff_input
        parent_result = self.parent_handoff_result
        if (
            parent_result.parent_demand_input_fingerprint
            != parent_input.demand_result.input_fingerprint
        ):
            raise ValueError("Parent demand input fingerprints must match.")
        if (
            parent_result.parent_demand_result_fingerprint
            != parent_input.demand_result.result_fingerprint
        ):
            raise ValueError("Parent demand result fingerprints must match.")
        if parent_result.parent_demand_versions != parent_input.demand_result.versions:
            raise ValueError("Parent demand versions must match.")
        if parent_result.parent_resistance_input_fingerprint != multirow_execution_fingerprint(
            parent_input.execution_bundle
        ):
            raise ValueError("Parent resistance fingerprints must match.")
        if parent_result.parent_resistance_versions != parent_input.execution_bundle.versions:
            raise ValueError("Parent resistance versions must match.")
        if parent_result.versions != parent_input.versions:
            raise ValueError("Parent handoff versions must match.")
        if tuple(item.check_id for item in parent_result.checks) != tuple(
            item.check_id for item in parent_input.execution_bundle.checks
        ):
            raise ValueError("Parent handoff checks must match the accepted execution bundle.")


@dataclass(frozen=True, slots=True)
class EccentricGroupModeFingerprintEnvelope:
    calculation_input: EccentricGroupModeCompatibilityInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    request_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class EccentricGroupModeCompatibilityResult:
    parent_demand_input_fingerprint: str
    parent_demand_result_fingerprint: str
    parent_demand_versions: Slice3VersionContext
    parent_handoff_input_fingerprint: str
    parent_handoff_result_fingerprint: str
    parent_handoff_versions: ResistanceHandoffVersionContext
    parent_resistance_input_fingerprint: str
    parent_resistance_versions: Slice2VersionContext
    versions: EccentricGroupModeVersionContext
    scenario_id: str
    connection_force_unit_direction: tuple[Decimal, Decimal] | None
    line_results: tuple[EccentricBoltLineResult, ...]
    first_row_compatibility: EccentricFirstRowCompatibility
    supported_results: tuple[MultiRowCheckResult, ...]
    required_check_ids: tuple[str, ...]
    not_required_check_ids: tuple[str, ...]
    unsupported_required_check_ids: tuple[str, ...]
    incomplete_required_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    qualification: QualificationDisposition
    warnings: tuple[EccentricGroupModeWarning, ...]
    parent_handoff_warnings: tuple[ResistanceHandoffWarning, ...]
    resistance_warnings: tuple[MultiRowExecutionWarning, ...]
    numerical_comparison: NumericalComparison
    governing_supported_check_ids: tuple[str, ...]
    overall_disposition: MultiRowOverallDisposition
    trace_stages: tuple[EccentricGroupModeTraceStage, ...]
    source_trace: tuple[str, ...]
    input_fingerprint: str
    result_fingerprint: str

    def __post_init__(self) -> None:
        for name in (
            "parent_demand_input_fingerprint",
            "parent_demand_result_fingerprint",
            "parent_handoff_input_fingerprint",
            "parent_handoff_result_fingerprint",
            "parent_resistance_input_fingerprint",
            "input_fingerprint",
            "result_fingerprint",
        ):
            _require_sha256(cast(str, getattr(self, name)), name)
        _require_text(self.scenario_id, "scenario_id")
        if self.connection_force_unit_direction is not None:
            if (
                not isinstance(self.connection_force_unit_direction, tuple)
                or len(self.connection_force_unit_direction) != 2
            ):
                raise TypeError(
                    "connection_force_unit_direction must be a two-Decimal tuple or None."
                )
            object.__setattr__(
                self,
                "connection_force_unit_direction",
                tuple(decimal_value(item) for item in self.connection_force_unit_direction),
            )
        _require_typed_tuple(self.line_results, EccentricBoltLineResult, "line_results")
        if not isinstance(self.first_row_compatibility, EccentricFirstRowCompatibility):
            raise TypeError("first_row_compatibility must be EccentricFirstRowCompatibility.")
        _require_typed_tuple(self.supported_results, MultiRowCheckResult, "supported_results")
        for name in (
            "required_check_ids",
            "not_required_check_ids",
            "unsupported_required_check_ids",
            "incomplete_required_check_ids",
            "failed_check_ids",
            "governing_supported_check_ids",
        ):
            _require_text_tuple(cast(tuple[str, ...], getattr(self, name)), name, allow_empty=True)
        _require_typed_tuple(self.warnings, EccentricGroupModeWarning, "warnings")
        _require_typed_tuple(
            self.parent_handoff_warnings, ResistanceHandoffWarning, "parent_handoff_warnings"
        )
        _require_typed_tuple(
            self.resistance_warnings, MultiRowExecutionWarning, "resistance_warnings"
        )
        _require_typed_tuple(self.trace_stages, EccentricGroupModeTraceStage, "trace_stages")
        _require_text_tuple(self.source_trace, "source_trace", allow_empty=True)


def calculate_eccentric_group_mode_compatibility(
    value: EccentricGroupModeCompatibilityInput,
) -> EccentricGroupModeCompatibilityResult:
    """Classify actual bolt-line resultants and reuse supported Slice 2 resistance checks."""

    if not isinstance(value, EccentricGroupModeCompatibilityInput):
        raise TypeError("value must be EccentricGroupModeCompatibilityInput.")
    input_fingerprint = eccentric_group_mode_input_fingerprint(value)
    parent_input = value.parent_handoff_input
    parent = value.parent_handoff_result
    bundle = parent_input.execution_bundle
    scenario = _scenario(parent_input)
    demand_by_id = _validated_line_membership(bundle, scenario)
    direction = _connection_force_direction(parent_input)
    residual_is_zero = scenario.residual_moment.canonical_magnitude == 0
    required_ids = bundle.required_checks.required_check_ids
    required_set = set(required_ids)
    line_checks = _line_checks(bundle)
    parent_checks = {item.check_id: item for item in parent.checks}
    line_results = tuple(
        _line_result(
            line.id,
            line.bolt_ids,
            line_checks.get(line.id),
            required_set,
            demand_by_id,
            direction,
            residual_is_zero,
            parent.coverage,
            bundle,
            parent_checks,
        )
        for line in bundle.physical_geometry.bolt_lines
    )
    first_row = _first_row_compatibility(bundle, residual_is_zero)
    interrow_ids = {
        item.check_id
        for item in bundle.checks
        if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    }
    supported = _supported_results(parent, line_results, interrow_ids)
    not_required = _not_required_ids(parent, line_results, required_ids)
    unsupported = _unsupported_ids(parent, line_results, interrow_ids, required_ids)
    incomplete = _incomplete_ids(parent, line_results, interrow_ids, required_ids)
    failed = tuple(
        item.result_id
        for item in supported
        if item.result_id in required_set and item.numerical_comparison is NumericalComparison.FAIL
    )
    numerical = _numerical(required_ids, supported, unsupported, incomplete, failed)
    overall = _overall(parent, line_results, numerical, unsupported, incomplete, required_set)
    warnings = _unique(
        tuple(item for line in line_results for item in line.warnings) + first_row.warnings
    )
    resistance_warnings = _unique(tuple(warning for item in supported for warning in item.warnings))
    governing = _governing(supported, required_set)
    trace_stages = (
        EccentricGroupModeTraceStage.DEMAND_ANALYSIS,
        EccentricGroupModeTraceStage.RESISTANCE_HANDOFF,
        EccentricGroupModeTraceStage.ECCENTRIC_GROUP_MODE_COMPATIBILITY,
        EccentricGroupModeTraceStage.RESISTANCE_CALCULATION,
    )
    parent_handoff_input_fingerprint = resistance_handoff_input_fingerprint(parent_input)
    payload = (
        parent_input.demand_result.result_fingerprint,
        parent_handoff_input_fingerprint,
        parent.result_fingerprint,
        parent.parent_resistance_input_fingerprint,
        value.versions,
        parent_input.scenario_id,
        direction,
        line_results,
        first_row,
        supported,
        required_ids,
        not_required,
        unsupported,
        incomplete,
        failed,
        parent.qualification,
        warnings,
        parent.warnings,
        resistance_warnings,
        numerical,
        governing,
        overall,
        trace_stages,
        value.source_trace,
    )
    result_fingerprint = _sha256(payload)
    return EccentricGroupModeCompatibilityResult(
        parent_input.demand_result.input_fingerprint,
        parent_input.demand_result.result_fingerprint,
        parent_input.demand_result.versions,
        parent_handoff_input_fingerprint,
        parent.result_fingerprint,
        parent.versions,
        parent.parent_resistance_input_fingerprint,
        parent.parent_resistance_versions,
        value.versions,
        parent_input.scenario_id,
        direction,
        line_results,
        first_row,
        supported,
        required_ids,
        not_required,
        unsupported,
        incomplete,
        failed,
        parent.qualification,
        warnings,
        parent.warnings,
        resistance_warnings,
        numerical,
        governing,
        overall,
        trace_stages,
        value.source_trace,
        input_fingerprint,
        result_fingerprint,
    )


def canonical_eccentric_group_mode_input_json(
    value: EccentricGroupModeCompatibilityInput | EccentricGroupModeFingerprintEnvelope,
) -> str:
    """Serialize calculation-authority input while excluding presentation-only state."""

    calculation_input = (
        value.calculation_input
        if isinstance(value, EccentricGroupModeFingerprintEnvelope)
        else value
    )
    if not isinstance(calculation_input, EccentricGroupModeCompatibilityInput):
        raise TypeError("Group-mode fingerprinting requires an input or presentation envelope.")
    return json.dumps(
        _canonicalize(calculation_input), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )


def eccentric_group_mode_input_fingerprint(
    value: EccentricGroupModeCompatibilityInput | EccentricGroupModeFingerprintEnvelope,
) -> str:
    return hashlib.sha256(
        canonical_eccentric_group_mode_input_json(value).encode("utf-8")
    ).hexdigest()


def _scenario(value: EccentricResistanceHandoffInput) -> DemandScenarioResult:
    for scenario in value.demand_result.scenarios:
        if scenario.scenario_id == value.scenario_id:
            if scenario.availability is not DemandAnalysisAvailability.CALCULATED:
                raise ValueError("Stage 2.6A requires a calculated parent demand scenario.")
            return scenario
    raise ValueError("scenario_id must identify an accepted parent demand scenario.")


def _validated_line_membership(
    bundle: MultiRowExecutionBundle, scenario: DemandScenarioResult
) -> dict[str, PerBoltDemandResult]:
    physical_ids = tuple(item.bolt_id for item in bundle.physical_geometry.bolts)
    demand_ids = tuple(item.bolt_id for item in scenario.per_bolt)
    if len(demand_ids) != len(set(demand_ids)):
        raise ValueError("Parent demand bolt IDs must be unique.")
    if set(demand_ids) != set(physical_ids):
        raise ValueError("Parent demand must contain all and only physical bolt IDs.")
    line_members = tuple(
        bolt_id for line in bundle.physical_geometry.bolt_lines for bolt_id in line.bolt_ids
    )
    if len(line_members) != len(set(line_members)) or set(line_members) != set(physical_ids):
        raise ValueError("Physical bolt-line membership must contain every bolt exactly once.")
    demand_by_id = {item.bolt_id: item for item in scenario.per_bolt}
    line_by_id = {
        bolt_id: line.id
        for line in bundle.physical_geometry.bolt_lines
        for bolt_id in line.bolt_ids
    }
    for bolt_id, item in demand_by_id.items():
        if item.bolt_line_id != line_by_id[bolt_id]:
            raise ValueError(
                "Parent demand bolt-line identities must match canonical physical geometry."
            )
    return demand_by_id


def _connection_force_direction(
    value: EccentricResistanceHandoffInput,
) -> tuple[Decimal, Decimal] | None:
    u = value.demand_result.projected_force.u.canonical_magnitude
    v = value.demand_result.projected_force.v.canonical_magnitude
    with localcontext() as context:
        context.prec = ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION
        magnitude = (u * u + v * v).sqrt()
        if magnitude == 0:
            return None
        return (u / magnitude, v / magnitude)


def _line_checks(bundle: MultiRowExecutionBundle) -> dict[str, MultiRowExecutableCheck]:
    result: dict[str, MultiRowExecutableCheck] = {}
    for check in bundle.checks:
        if check.family is not MultiRowCheckFamily.INTERROW_SHEAR_OUT:
            continue
        if check.bolt_line_id is None or check.bolt_line_id in result:
            raise ValueError("Each inter-row check must identify one unique physical bolt line.")
        result[check.bolt_line_id] = check
    physical = {item.id for item in bundle.physical_geometry.bolt_lines}
    if not set(result) <= physical:
        raise ValueError("Inter-row checks must use canonical physical bolt-line IDs.")
    return result


def _line_result(
    line_id: str,
    bolt_ids: tuple[str, ...],
    check: MultiRowExecutableCheck | None,
    required_ids: set[str],
    demands: dict[str, PerBoltDemandResult],
    direction: tuple[Decimal, Decimal] | None,
    residual_is_zero: bool,
    parent_coverage: ResistanceHandoffCoverage,
    bundle: MultiRowExecutionBundle,
    parent_checks: dict[str, ResistanceCheckHandoff],
) -> EccentricBoltLineResult:
    vectors = tuple(
        EccentricLineBoltVector(bolt_id, demands[bolt_id].total_force) for bolt_id in bolt_ids
    )
    with localcontext() as context:
        context.prec = ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION
        resultant_u = sum((item.force.u.canonical_magnitude for item in vectors), Decimal(0))
        resultant_v = sum((item.force.v.canonical_magnitude for item in vectors), Decimal(0))
        parallel = (
            Decimal(0)
            if direction is None
            else resultant_u * direction[0] + resultant_v * direction[1]
        )
        transverse = (
            Decimal(0)
            if direction is None
            else direction[0] * resultant_v - direction[1] * resultant_u
        )
    resultant = InPlaneQuantityVector(
        PhysicalQuantity.of(resultant_u, Unit.N), PhysicalQuantity.of(resultant_v, Unit.N)
    )
    parallel_quantity = PhysicalQuantity.of(parallel, Unit.N)
    transverse_quantity = PhysicalQuantity.of(transverse, Unit.N)
    check_id = None if check is None else check.check_id
    if check is None or check.check_id not in required_ids:
        return _line_contract(
            line_id,
            check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION,
        )
    if residual_is_zero:
        parent_check = parent_checks.get(check.check_id)
        resistance = None if parent_check is None else parent_check.resistance_result
        demand = check.demand
        if demand is None:
            raise ValueError("Inherited inter-row check requires its accepted legacy demand.")
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.INHERITED_LEGACY_STAGE_2_4B,
            demand,
            resistance,
        )
    if resultant_u == 0 and resultant_v == 0:
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.NOT_REQUIRED_ZERO_LINE_DEMAND,
        )
    if parent_coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER:
        warning = _warning(
            EccentricGroupModeWarningCode.PARENT_RESISTANCE_HANDOFF_NOT_AVAILABLE,
            f"bolt_line_id:{line_id}",
        )
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
            warnings=(warning,),
        )
    if direction is None:
        warning = _warning(
            EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_ZERO_CONNECTION_FORCE_NOT_SUPPORTED,
            f"bolt_line_id:{line_id}",
        )
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
            warnings=(warning,),
        )
    if transverse != 0:
        warning = _warning(
            EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE,
            f"bolt_line_id:{line_id}",
            f"transverse_n:{canonical_decimal_string(transverse)}",
        )
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
            warnings=(warning,),
        )
    if parallel < 0:
        warning = _warning(
            EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED,
            f"bolt_line_id:{line_id}",
            f"parallel_n:{canonical_decimal_string(parallel)}",
        )
        return _line_contract(
            line_id,
            check.check_id,
            bolt_ids,
            vectors,
            resultant,
            parallel_quantity,
            transverse_quantity,
            EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
            warnings=(warning,),
        )
    demand = PhysicalQuantity.of(parallel, Unit.N)
    resistance = _execute_line(bundle, check, demand)
    return _line_contract(
        line_id,
        check.check_id,
        bolt_ids,
        vectors,
        resultant,
        parallel_quantity,
        transverse_quantity,
        EccentricLineHandoffStatus.AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT,
        demand,
        resistance,
    )


def _line_contract(
    line_id: str,
    check_id: str | None,
    bolt_ids: tuple[str, ...],
    vectors: tuple[EccentricLineBoltVector, ...],
    resultant: InPlaneQuantityVector,
    parallel: PhysicalQuantity,
    transverse: PhysicalQuantity,
    status: EccentricLineHandoffStatus,
    demand: PhysicalQuantity | None = None,
    resistance: MultiRowCheckResult | None = None,
    warnings: tuple[EccentricGroupModeWarning, ...] = (),
) -> EccentricBoltLineResult:
    return EccentricBoltLineResult(
        line_id,
        check_id,
        bolt_ids,
        vectors,
        resultant,
        parallel,
        transverse,
        status,
        demand,
        resistance,
        warnings,
        RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF,
    )


def _execute_line(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
    demand: PhysicalQuantity,
) -> MultiRowCheckResult:
    if check.interrow_plan is None or check.bolt_line_id is None:
        raise ValueError("Authorized eccentric shear-out requires an accepted inter-row plan.")
    updated_plan = replace(check.interrow_plan, per_line_demand=demand)
    updated_check = replace(check, demand=demand, interrow_plan=updated_plan)
    updated_lines = tuple(
        replace(
            item,
            demand=demand,
            demand_method_id=RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF,
        )
        if item.bolt_line_id == check.bolt_line_id
        else item
        for item in bundle.bolt_lines
    )
    single = replace(
        bundle,
        bolt_lines=updated_lines,
        required_checks=MultiRowRequiredCheckContract((check.check_id,)),
        checks=(updated_check,),
    )
    return calculate_multirow_connection(single).results[0]


def _first_row_compatibility(
    bundle: MultiRowExecutionBundle, residual_is_zero: bool
) -> EccentricFirstRowCompatibility:
    required = tuple(
        item.check_id
        for item in bundle.checks
        if item.family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
        and item.check_id in bundle.required_checks.required_check_ids
    )
    if not required:
        return EccentricFirstRowCompatibility(
            EccentricFirstRowHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION, ()
        )
    if residual_is_zero:
        return EccentricFirstRowCompatibility(
            EccentricFirstRowHandoffStatus.INHERITED_LEGACY_STAGE_2_4B, required
        )
    return EccentricFirstRowCompatibility(
        EccentricFirstRowHandoffStatus.CALCULATION_NOT_SUPPORTED,
        required,
        (
            _warning(
                EccentricGroupModeWarningCode.ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1,
                *(f"check_id:{item}" for item in required),
            ),
        ),
    )


def _supported_results(
    parent: EccentricResistanceHandoffResult,
    lines: tuple[EccentricBoltLineResult, ...],
    interrow_ids: set[str],
) -> tuple[MultiRowCheckResult, ...]:
    retained = tuple(
        item for item in parent.supported_results if item.result_id not in interrow_ids
    )
    replacements = tuple(
        item.shear_out_result
        for item in lines
        if item.shear_out_result is not None
        and item.shear_out_result.availability is MultiRowResultAvailability.CALCULATED
    )
    by_id = {item.result_id: item for item in (*retained, *replacements)}
    return tuple(by_id[item.check_id] for item in parent.checks if item.check_id in by_id)


def _not_required_ids(
    parent: EccentricResistanceHandoffResult,
    lines: tuple[EccentricBoltLineResult, ...],
    required_ids: tuple[str, ...],
) -> tuple[str, ...]:
    candidates = {
        item.check_id
        for item in parent.checks
        if item.availability is MultiRowResultAvailability.NOT_APPLICABLE
    }
    candidates.update(
        item.check_id
        for item in lines
        if item.check_id is not None
        and item.handoff_status
        in {
            EccentricLineHandoffStatus.NOT_REQUIRED_ZERO_LINE_DEMAND,
            EccentricLineHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION,
        }
    )
    return tuple(item for item in required_ids if item in candidates)


def _unsupported_ids(
    parent: EccentricResistanceHandoffResult,
    lines: tuple[EccentricBoltLineResult, ...],
    interrow_ids: set[str],
    required_ids: tuple[str, ...],
) -> tuple[str, ...]:
    candidates = set(parent.unsupported_required_check_ids) - interrow_ids
    for line in lines:
        if line.check_id is None:
            continue
        if line.handoff_status is EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED or (
            line.shear_out_result is not None
            and line.shear_out_result.availability
            in {
                MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
                MultiRowResultAvailability.SOURCE_DATA_PENDING,
            }
        ):
            candidates.add(line.check_id)
    return tuple(item for item in required_ids if item in candidates)


def _incomplete_ids(
    parent: EccentricResistanceHandoffResult,
    lines: tuple[EccentricBoltLineResult, ...],
    interrow_ids: set[str],
    required_ids: tuple[str, ...],
) -> tuple[str, ...]:
    candidates = set(parent.incomplete_required_check_ids) - interrow_ids
    candidates.update(
        item.check_id
        for item in lines
        if item.check_id is not None
        and item.shear_out_result is not None
        and item.shear_out_result.availability is MultiRowResultAvailability.INCOMPLETE_INPUT
    )
    return tuple(item for item in required_ids if item in candidates)


def _numerical(
    required_ids: tuple[str, ...],
    supported: tuple[MultiRowCheckResult, ...],
    unsupported: tuple[str, ...],
    incomplete: tuple[str, ...],
    failed: tuple[str, ...],
) -> NumericalComparison:
    if failed:
        return NumericalComparison.FAIL
    if unsupported or incomplete:
        return NumericalComparison.NOT_EVALUATED
    calculated = {item.result_id for item in supported if item.result_id in required_ids}
    nonnumerical = set(required_ids) - calculated
    if nonnumerical:
        return NumericalComparison.NOT_EVALUATED
    return NumericalComparison.PASS if calculated else NumericalComparison.NOT_EVALUATED


def _overall(
    parent: EccentricResistanceHandoffResult,
    lines: tuple[EccentricBoltLineResult, ...],
    numerical: NumericalComparison,
    unsupported: tuple[str, ...],
    incomplete: tuple[str, ...],
    required_ids: set[str],
) -> MultiRowOverallDisposition:
    if numerical is NumericalComparison.FAIL:
        return MultiRowOverallDisposition.FAIL
    if any(
        item.shear_out_result is not None
        and item.shear_out_result.availability is MultiRowResultAvailability.INVALID_GEOMETRY
        for item in lines
    ) or any(
        item.availability is MultiRowResultAvailability.INVALID_GEOMETRY
        for item in parent.checks
        if item.check_id in required_ids
    ):
        return MultiRowOverallDisposition.INVALID_GEOMETRY
    if (
        parent.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
        or unsupported
        or incomplete
        or numerical is NumericalComparison.NOT_EVALUATED
    ):
        return MultiRowOverallDisposition.NOT_EVALUATED
    if parent.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED:
        return MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if parent.qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED:
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


def _warning(code: EccentricGroupModeWarningCode, *trace: str) -> EccentricGroupModeWarning:
    return EccentricGroupModeWarning(code, trace)


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonicalize(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonicalize(value: object) -> object:
    if isinstance(value, EccentricGroupModeFingerprintEnvelope):
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
        raise TypeError("Group-mode fingerprints reject authoritative binary floats.")
    raise TypeError(f"Unsupported group-mode fingerprint value {type(value).__name__}.")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text.")


def _require_text_tuple(value: tuple[str, ...], name: str, allow_empty: bool = False) -> None:
    if not isinstance(value, tuple) or (not value and not allow_empty):
        raise ValueError(f"{name} must be an immutable nonempty tuple.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must contain nonempty text.")
    _require_unique(value, name)


def _require_typed_tuple(value: tuple[object, ...], expected: type, name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, expected) for item in value):
        raise TypeError(f"{name} must be an immutable tuple of {expected.__name__} values.")


def _require_unique(values: Iterable[object], name: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"{name} must be unique.")


def _require_force(value: PhysicalQuantity, name: str, *, allow_negative: bool = False) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.FORCE:
        raise ValueError(f"{name} must be a force quantity.")
    if not allow_negative and value.canonical_magnitude < 0:
        raise ValueError(f"{name} cannot be negative.")


def _require_force_vector(value: InPlaneQuantityVector, name: str) -> None:
    if not isinstance(value, InPlaneQuantityVector) or value.u.dimension is not Dimension.FORCE:
        raise ValueError(f"{name} must be an in-plane force vector.")


def _require_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")


def _unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    return tuple(dict.fromkeys(values))


__all__ = (
    "ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION",
    "ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION",
    "ECCENTRIC_GROUP_MODE_ENGINE_VERSION",
    "ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION",
    "ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION",
    "ECCENTRIC_GROUP_MODE_RULE_SET_VERSION",
    "RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF",
    "EccentricBoltLineResult",
    "EccentricFirstRowCompatibility",
    "EccentricFirstRowHandoffStatus",
    "EccentricGroupModeCompatibilityInput",
    "EccentricGroupModeCompatibilityResult",
    "EccentricGroupModeFingerprintEnvelope",
    "EccentricGroupModeTraceStage",
    "EccentricGroupModeVersionContext",
    "EccentricGroupModeWarning",
    "EccentricGroupModeWarningCode",
    "EccentricLineBoltVector",
    "EccentricLineHandoffStatus",
    "calculate_eccentric_group_mode_compatibility",
    "canonical_eccentric_group_mode_input_json",
    "eccentric_group_mode_input_fingerprint",
)
