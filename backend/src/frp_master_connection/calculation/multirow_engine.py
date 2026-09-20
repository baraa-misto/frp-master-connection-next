"""Pure Calculation Slice 2 execution contracts and multi-row numerical engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.calculation.block_shear_planning import (
    BlockPathPlanStatus,
    BlockShearAreaPlan,
    BlockShearPlanSet,
    NetAreaStatus,
)
from frp_master_connection.calculation.equations import (
    BearingTrace,
    BoltResistanceTrace,
    CombinedBoltTrace,
    FactorAssemblyTrace,
    PullThroughTrace,
    bolt_shear_resistance,
    bolt_tension_resistance,
    combined_bolt_tension_shear_resistance,
    pin_bearing_resistance,
    pull_through_resistance,
)
from frp_master_connection.calculation.inputs import EndUseFactors
from frp_master_connection.calculation.multirow import (
    FirstRowNetTensionPlan,
    FirstRowPlanMethod,
    GeometryStatus,
    InterrowShearOutPlan,
    MaterialDirection,
    MethodProvenance,
    MultiRowCalculationPlanSet,
    MultiRowMethodApplicability,
    PlanAvailability,
    PultrudedElementClassification,
    QualificationDisposition,
)
from frp_master_connection.calculation.multirow_equations import (
    BlockShearEccentricityClassification,
    BlockShearEquation,
    BlockShearTrace,
    FullFirstRowTrace,
    InterrowShearOutTrace,
    LowerEnvelopeTrace,
    MultiRowFactorTrace,
    SimplifiedFirstRowTrace,
    UnknownLbrEnvelopeTrace,
    adjusted_property_trace,
    block_shear_resistance,
    classify_block_shear_eccentricity,
    compare_resistance,
    full_first_row_resistance,
    interrow_shear_out_resistance,
    lower_first_row_envelope,
    simplified_first_row_resistance,
    unknown_lbr_endpoint_envelope,
)
from frp_master_connection.calculation.properties import (
    FastenerSnapshot,
    FRPPropertyEntry,
    FRPPropertyKind,
    MaterialPropertySnapshot,
    ThreadStatus,
    WasherGeometry,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_from_finite_real,
    decimal_value,
)
from frp_master_connection.calculation.results import (
    GOVERNING_UTILIZATION_TOLERANCE,
    NumericalComparison,
)
from frp_master_connection.geometry.multirow import MultiRowGeometry

SLICE_2_CALCULATION_CONTRACT_VERSION = "2.4B-RC2"
SLICE_2_CALCULATION_ENGINE_VERSION = "0.2.0.dev1"
SLICE_2_ENGINEERING_RULE_SET_VERSION = "asce74-23-ch8-multirow-rc2.dev1"
SLICE_2_EXECUTION_INPUT_SCHEMA = "frp-master-connection-calculation-slice-2-execution-input"
SLICE_2_EXECUTION_INPUT_SCHEMA_VERSION = "0.1.0-draft"
SLICE_2_RESULT_SCHEMA = "frp-master-connection-calculation-slice-2-result"
SLICE_2_RESULT_SCHEMA_VERSION = "0.1.0-draft"
SLICE_2_FINGERPRINT_SCHEMA = "frp-master-connection-calculation-slice-2-fingerprint"
SLICE_2_FINGERPRINT_SCHEMA_VERSION = "0.1.0-draft"
SLICE_2_GOLDEN_SCHEMA = "frp-master-connection-calculation-slice-2-golden-rc2"


class MultiRowCheckFamily(StrEnum):
    BOLT_SHEAR = "BOLT_SHEAR"
    BOLT_TENSION = "BOLT_TENSION"
    BOLT_COMBINED_TENSION_SHEAR = "BOLT_COMBINED_TENSION_SHEAR"
    PULL_THROUGH = "PULL_THROUGH"
    PIN_BEARING = "PIN_BEARING"
    FIRST_ROW_NET_TENSION = "FIRST_ROW_NET_TENSION"
    INTERROW_SHEAR_OUT = "INTERROW_SHEAR_OUT"
    BLOCK_SHEAR = "BLOCK_SHEAR"
    CODE_GEOMETRY = "CODE_GEOMETRY"
    QUALIFICATION = "QUALIFICATION"
    MATERIAL_SOURCE_REVIEW = "MATERIAL_SOURCE_REVIEW"


class MultiRowEquationMethod(StrEnum):
    BOLT_SHEAR = "BOLT_SHEAR"
    BOLT_TENSION = "BOLT_TENSION"
    BOLT_COMBINED_TENSION_SHEAR = "BOLT_COMBINED_TENSION_SHEAR"
    PULL_THROUGH = "PULL_THROUGH"
    PIN_BEARING = "PIN_BEARING"
    FIRST_ROW_SIMPLIFIED = "FIRST_ROW_SIMPLIFIED"
    FIRST_ROW_COMMENTARY_FULL = "FIRST_ROW_COMMENTARY_FULL"
    FIRST_ROW_RATIONAL_LOWER_ENVELOPE = "FIRST_ROW_RATIONAL_LOWER_ENVELOPE"
    INTERROW_ASCE_EQ_8_12 = "INTERROW_ASCE_EQ_8_12"
    INTERROW_ASCE_EQ_8_13 = "INTERROW_ASCE_EQ_8_13"
    INTERROW_RATIONAL_EXTENSION_EQ_8_13 = "INTERROW_RATIONAL_EXTENSION_EQ_8_13"
    BLOCK_SHEAR_ASCE_EQ_8_14A = "BLOCK_SHEAR_ASCE_EQ_8_14A"
    BLOCK_SHEAR_ASCE_EQ_8_14B = "BLOCK_SHEAR_ASCE_EQ_8_14B"
    STATUS_ONLY = "STATUS_ONLY"


class MultiRowResultAvailability(StrEnum):
    CALCULATED = "CALCULATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    SOURCE_DATA_PENDING = "SOURCE_DATA_PENDING"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class MultiRowOverallDisposition(StrEnum):
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FAIL = "FAIL"
    INCOMPLETE_OR_UNSUPPORTED = "INCOMPLETE_OR_UNSUPPORTED"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    PASS = "PASS"  # noqa: S105 - engineering disposition
    NOT_EVALUATED = "NOT_EVALUATED"


class PitchFactorSource(StrEnum):
    AUTOMATIC_CONSTANT_PITCH = "AUTOMATIC_CONSTANT_PITCH"
    ENGINEER_DEFINED = "ENGINEER_DEFINED"
    UNITY_NOT_APPLICABLE = "UNITY_NOT_APPLICABLE"


class MultiRowExecutionWarningCode(StrEnum):
    ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED = "ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED"
    CONSERVATIVE_FULL_ROW_ENVELOPE_USED = "CONSERVATIVE_FULL_ROW_ENVELOPE_USED"
    RATIONAL_EQ_8_13_EXTENSION_USED = "RATIONAL_EQ_8_13_EXTENSION_USED"
    ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION = (
        "ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION"
    )
    RATIONAL_HALF_HOLE_CORNER_ACCOUNTING = "RATIONAL_HALF_HOLE_CORNER_ACCOUNTING"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    REDUCED_PITCH_FACTOR_APPLIED = "REDUCED_PITCH_FACTOR_APPLIED"
    LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS = "LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS"
    NUMERICAL_DOMAIN_ERROR = "NUMERICAL_DOMAIN_ERROR"
    NONPOSITIVE_DESIGN_RESISTANCE = "NONPOSITIVE_DESIGN_RESISTANCE"
    ENGINEER_DEFINED_METHOD_USED = "ENGINEER_DEFINED_METHOD_USED"
    EXTERNAL_RESOLVED_PLAN_USED = "EXTERNAL_RESOLVED_PLAN_USED"
    MISSING_REQUIRED_BOLT_AXIS_TENSION = "MISSING_REQUIRED_BOLT_AXIS_TENSION"
    RATIONAL_BLOCK_PATH_RESOLVER_USED = "RATIONAL_BLOCK_PATH_RESOLVER_USED"


@dataclass(frozen=True, slots=True)
class MultiRowExecutionWarning:
    code: MultiRowExecutionWarningCode
    trace: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, MultiRowExecutionWarningCode):
            raise TypeError("code must be MultiRowExecutionWarningCode.")
        _require_string_tuple(self.trace, "trace")


@dataclass(frozen=True, slots=True)
class Slice2VersionContext:
    calculation_contract_version: str = SLICE_2_CALCULATION_CONTRACT_VERSION
    calculation_engine_version: str = SLICE_2_CALCULATION_ENGINE_VERSION
    engineering_rule_set_version: str = SLICE_2_ENGINEERING_RULE_SET_VERSION
    execution_input_schema: str = SLICE_2_EXECUTION_INPUT_SCHEMA
    execution_input_schema_version: str = SLICE_2_EXECUTION_INPUT_SCHEMA_VERSION
    result_schema: str = SLICE_2_RESULT_SCHEMA
    result_schema_version: str = SLICE_2_RESULT_SCHEMA_VERSION
    fingerprint_schema: str = SLICE_2_FINGERPRINT_SCHEMA
    fingerprint_schema_version: str = SLICE_2_FINGERPRINT_SCHEMA_VERSION
    golden_schema: str = SLICE_2_GOLDEN_SCHEMA

    def __post_init__(self) -> None:
        expected = (
            SLICE_2_CALCULATION_CONTRACT_VERSION,
            SLICE_2_CALCULATION_ENGINE_VERSION,
            SLICE_2_ENGINEERING_RULE_SET_VERSION,
            SLICE_2_EXECUTION_INPUT_SCHEMA,
            SLICE_2_EXECUTION_INPUT_SCHEMA_VERSION,
            SLICE_2_RESULT_SCHEMA,
            SLICE_2_RESULT_SCHEMA_VERSION,
            SLICE_2_FINGERPRINT_SCHEMA,
            SLICE_2_FINGERPRINT_SCHEMA_VERSION,
            SLICE_2_GOLDEN_SCHEMA,
        )
        if tuple(getattr(self, field.name) for field in fields(self)) != expected:
            raise ValueError("Slice 2 version context must use the approved RC2 identities.")


@dataclass(frozen=True, slots=True)
class MultiRowFingerprintMetadataEntry:
    key: str
    value: str

    def __post_init__(self) -> None:
        _require_text(self.key, "key")
        _require_text(self.value, "value")


@dataclass(frozen=True, slots=True)
class MultiRowBoltGeometryContext:
    bolt_id: str
    x: Decimal
    y: Decimal
    bolt_diameter: Decimal
    hole_diameter: Decimal
    bolt_identity: str
    logical_connection_id: str

    def __post_init__(self) -> None:
        for name in ("bolt_id", "bolt_identity", "logical_connection_id"):
            _require_text(cast(str, getattr(self, name)), name)
        for name in ("x", "y", "bolt_diameter", "hole_diameter"):
            object.__setattr__(self, name, decimal_value(cast(Decimal, getattr(self, name))))
        if self.bolt_diameter <= 0 or self.hole_diameter < self.bolt_diameter:
            raise ValueError("Physical bolt/hole geometry is invalid.")


@dataclass(frozen=True, slots=True)
class MultiRowProjectedGroupContext:
    id: str
    ordinal: int
    projected_coordinate: Decimal
    raw_deviation: Decimal
    bolt_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 1:
            raise ValueError("ordinal must be a positive non-Boolean integer.")
        object.__setattr__(self, "projected_coordinate", decimal_value(self.projected_coordinate))
        object.__setattr__(self, "raw_deviation", decimal_value(self.raw_deviation))
        if self.raw_deviation < 0:
            raise ValueError("raw_deviation cannot be negative.")
        _require_unique_string_tuple(self.bolt_ids, "bolt_ids")


@dataclass(frozen=True, slots=True)
class MultiRowPhysicalGeometryContext:
    group_id: str
    interface_id: str
    boundary_id: str
    source_length_unit: Unit
    force_u: tuple[Decimal, Decimal]
    force_v: tuple[Decimal, Decimal]
    bolts: tuple[MultiRowBoltGeometryContext, ...]
    rows: tuple[MultiRowProjectedGroupContext, ...]
    bolt_lines: tuple[MultiRowProjectedGroupContext, ...]
    unloaded_free_end_u: Decimal
    loaded_end_u: Decimal
    negative_side_v: Decimal
    positive_side_v: Decimal
    sorting_tolerance: Decimal

    def __post_init__(self) -> None:
        for name in ("group_id", "interface_id", "boundary_id"):
            _require_text(cast(str, getattr(self, name)), name)
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be IN or MM.")
        for name in ("force_u", "force_v"):
            vector = getattr(self, name)
            if not isinstance(vector, tuple) or len(vector) != 2:
                raise TypeError(f"{name} must be a two-Decimal tuple.")
            object.__setattr__(self, name, tuple(decimal_value(item) for item in vector))
        _require_typed_tuple(self.bolts, MultiRowBoltGeometryContext, "bolts")
        _require_typed_tuple(self.rows, MultiRowProjectedGroupContext, "rows")
        _require_typed_tuple(self.bolt_lines, MultiRowProjectedGroupContext, "bolt_lines")
        for name in (
            "unloaded_free_end_u",
            "loaded_end_u",
            "negative_side_v",
            "positive_side_v",
            "sorting_tolerance",
        ):
            object.__setattr__(self, name, decimal_value(cast(Decimal, getattr(self, name))))
        if self.sorting_tolerance <= 0:
            raise ValueError("sorting_tolerance must be positive.")
        if not self.bolts or not self.rows or not self.bolt_lines:
            raise ValueError("Physical geometry requires bolts, rows, and bolt lines.")
        _require_unique((item.bolt_id for item in self.bolts), "bolt IDs")
        _require_unique((item.id for item in self.rows), "row IDs")
        _require_unique((item.id for item in self.bolt_lines), "bolt-line IDs")


@dataclass(frozen=True, slots=True)
class MultiRowEndDistanceContext:
    unloaded_end_e1: PhysicalQuantity
    row_1_to_unloaded_end_distance: PhysicalQuantity
    loaded_boundary_to_row_1_distance: PhysicalQuantity
    physical_pitches: tuple[PhysicalQuantity, ...]
    unloaded_boundary_id: str
    nearest_row_id: str
    row_1_id: str
    side_boundary_ids: tuple[str, str]

    def __post_init__(self) -> None:
        quantities = (
            self.unloaded_end_e1,
            self.row_1_to_unloaded_end_distance,
            self.loaded_boundary_to_row_1_distance,
            *self.physical_pitches,
        )
        if any(
            not isinstance(item, PhysicalQuantity)
            or item.dimension is not Dimension.LENGTH
            or item.magnitude < 0
            for item in quantities
        ):
            raise ValueError("End-distance context requires nonnegative length quantities.")
        if not isinstance(self.physical_pitches, tuple) or any(
            item.magnitude <= 0 for item in self.physical_pitches
        ):
            raise ValueError("physical_pitches must be an immutable tuple of positive lengths.")
        for name in ("unloaded_boundary_id", "nearest_row_id", "row_1_id"):
            _require_text(cast(str, getattr(self, name)), name)
        if not isinstance(self.side_boundary_ids, tuple) or len(self.side_boundary_ids) != 2:
            raise TypeError("side_boundary_ids must contain exactly two identities.")
        _require_string_tuple(self.side_boundary_ids, "side_boundary_ids")
        total = self.unloaded_end_e1
        for pitch in self.physical_pitches:
            total += pitch
        if total != self.row_1_to_unloaded_end_distance:
            raise ValueError("Row-1-to-unloaded-end distance must equal e1 plus physical pitches.")


@dataclass(frozen=True, slots=True)
class MultiRowSignedDemandContext:
    force_u: Decimal
    force_v: Decimal
    in_plane_magnitude: PhysicalQuantity
    source_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "force_u", decimal_value(self.force_u))
        object.__setattr__(self, "force_v", decimal_value(self.force_v))
        if self.force_u == 0 and self.force_v == 0:
            raise ValueError("Signed physical force direction cannot be zero.")
        _require_nonnegative_force(self.in_plane_magnitude, "in_plane_magnitude")
        _require_text(self.source_id, "source_id")


@dataclass(frozen=True, slots=True)
class MultiRowFactorContext:
    time_effect_factor_lambda: Decimal
    lap_factor_c_lap: Decimal
    pitch_factor_c_delta: Decimal
    pitch_factor_source: PitchFactorSource
    pitch_factor_provenance: MethodProvenance | None = None

    def __post_init__(self) -> None:
        for name in (
            "time_effect_factor_lambda",
            "lap_factor_c_lap",
            "pitch_factor_c_delta",
        ):
            value = decimal_value(cast(Decimal, getattr(self, name)))
            if value <= 0:
                raise ValueError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        if not isinstance(self.pitch_factor_source, PitchFactorSource):
            raise TypeError("pitch_factor_source must be PitchFactorSource.")
        if self.pitch_factor_source is PitchFactorSource.ENGINEER_DEFINED:
            if (
                self.pitch_factor_provenance is None
                or not self.pitch_factor_provenance.engineer_confirmed
            ):
                raise ValueError("Engineer-defined pitch factor requires confirmed provenance.")
        elif self.pitch_factor_provenance is not None:
            raise ValueError("Pitch-factor provenance is reserved for engineer-defined factors.")


@dataclass(frozen=True, slots=True)
class MultiRowLayerExecutionContext:
    layer_id: str
    component_id: str
    material: MaterialPropertySnapshot
    thickness: PhysicalQuantity
    material_direction: MaterialDirection
    element_classification: PultrudedElementClassification
    end_use_factors: EndUseFactors
    bearing_thread_status: ThreadStatus
    source_geometry_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("layer_id", "component_id"):
            _require_text(cast(str, getattr(self, name)), name)
        if not isinstance(self.material, MaterialPropertySnapshot):
            raise TypeError("material must be MaterialPropertySnapshot.")
        if self.thickness.dimension is not Dimension.LENGTH or self.thickness.magnitude <= 0:
            raise ValueError("Layer thickness must be a positive length.")
        if not isinstance(self.material_direction, MaterialDirection):
            raise TypeError("material_direction must be MaterialDirection.")
        if not isinstance(self.element_classification, PultrudedElementClassification):
            raise TypeError("element_classification must be PultrudedElementClassification.")
        if not isinstance(self.end_use_factors, EndUseFactors):
            raise TypeError("end_use_factors must be EndUseFactors.")
        if not isinstance(self.bearing_thread_status, ThreadStatus):
            raise TypeError("bearing_thread_status must be ThreadStatus.")
        _require_unique_string_tuple(self.source_geometry_ids, "source_geometry_ids")


@dataclass(frozen=True, slots=True)
class MultiRowBoltExecutionContext:
    bolt_id: str
    diameter: PhysicalQuantity
    fastener: FastenerSnapshot
    shear_thread_status: ThreadStatus
    in_plane_demand: PhysicalQuantity
    bolt_axis_tension_demand: PhysicalQuantity | None
    bolt_axis_tension_required: bool
    washer: WasherGeometry | None
    layer_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.bolt_id, "bolt_id")
        if self.diameter.dimension is not Dimension.LENGTH or self.diameter.magnitude <= 0:
            raise ValueError("Bolt diameter must be a positive length.")
        if not isinstance(self.fastener, FastenerSnapshot):
            raise TypeError("fastener must be FastenerSnapshot.")
        if not isinstance(self.shear_thread_status, ThreadStatus):
            raise TypeError("shear_thread_status must be ThreadStatus.")
        _require_nonnegative_force(self.in_plane_demand, "in_plane_demand")
        if self.bolt_axis_tension_demand is not None:
            _require_nonnegative_force(self.bolt_axis_tension_demand, "bolt_axis_tension_demand")
        if not isinstance(self.bolt_axis_tension_required, bool):
            raise TypeError("bolt_axis_tension_required must be Boolean.")
        if self.washer is not None and not isinstance(self.washer, WasherGeometry):
            raise TypeError("washer must be WasherGeometry or None.")
        _require_unique_string_tuple(self.layer_ids, "layer_ids")


@dataclass(frozen=True, slots=True)
class MultiRowBoltLineExecutionContext:
    bolt_line_id: str
    demand: PhysicalQuantity
    equivalent_rectangular_line: bool
    demand_method_id: str

    def __post_init__(self) -> None:
        _require_text(self.bolt_line_id, "bolt_line_id")
        _require_nonnegative_force(self.demand, "demand")
        if not isinstance(self.equivalent_rectangular_line, bool):
            raise TypeError("equivalent_rectangular_line must be Boolean.")
        _require_text(self.demand_method_id, "demand_method_id")


@dataclass(frozen=True, slots=True)
class BlockShearEccentricityContext:
    signed_eccentricity: PhysicalQuantity
    geometric_reference: str
    tolerance: PhysicalQuantity
    source_geometry_ids: tuple[str, ...]
    classification: BlockShearEccentricityClassification

    def __post_init__(self) -> None:
        if self.signed_eccentricity.dimension is not Dimension.LENGTH:
            raise ValueError("signed_eccentricity must be a length.")
        _require_text(self.geometric_reference, "geometric_reference")
        if self.tolerance.dimension is not Dimension.LENGTH or self.tolerance.magnitude <= 0:
            raise ValueError("eccentricity tolerance must be a positive length.")
        _require_unique_string_tuple(self.source_geometry_ids, "source_geometry_ids")
        if self.classification is not classify_block_shear_eccentricity(
            self.signed_eccentricity, self.tolerance
        ):
            raise ValueError("Stored eccentricity classification does not match physical values.")


@dataclass(frozen=True, slots=True)
class MultiRowRequiredCheckContract:
    required_check_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_unique_string_tuple(
            self.required_check_ids, "required_check_ids", allow_empty=True
        )


@dataclass(frozen=True, slots=True)
class MultiRowExecutableCheck:
    check_id: str
    source_plan_id: str
    family: MultiRowCheckFamily
    method: MultiRowEquationMethod
    source_locator: str
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    plan_availability: PlanAvailability
    geometry_status: GeometryStatus
    demand: PhysicalQuantity | None = None
    layer_id: str | None = None
    bolt_id: str | None = None
    row_id: str | None = None
    bolt_line_id: str | None = None
    path_id: str | None = None
    first_row_plan: FirstRowNetTensionPlan | None = None
    interrow_plan: InterrowShearOutPlan | None = None
    block_plan: BlockShearAreaPlan | None = None
    lbr: Decimal | None = None
    warnings: tuple[MultiRowExecutionWarning, ...] = ()

    def __post_init__(self) -> None:
        for name in ("check_id", "source_plan_id", "source_locator"):
            _require_text(cast(str, getattr(self, name)), name)
        for name, expected in (
            ("family", MultiRowCheckFamily),
            ("method", MultiRowEquationMethod),
            ("method_applicability", MultiRowMethodApplicability),
            ("qualification", QualificationDisposition),
            ("plan_availability", PlanAvailability),
            ("geometry_status", GeometryStatus),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TypeError(f"{name} must be {expected.__name__}.")
        if self.demand is not None:
            _require_nonnegative_force(self.demand, "demand")
        for name in ("layer_id", "bolt_id", "row_id", "bolt_line_id", "path_id"):
            value = cast(str | None, getattr(self, name))
            if value is not None:
                _require_text(value, name)
        if self.first_row_plan is not None and not isinstance(
            self.first_row_plan, FirstRowNetTensionPlan
        ):
            raise TypeError("first_row_plan must be FirstRowNetTensionPlan or None.")
        if self.interrow_plan is not None and not isinstance(
            self.interrow_plan, InterrowShearOutPlan
        ):
            raise TypeError("interrow_plan must be InterrowShearOutPlan or None.")
        if self.block_plan is not None and not isinstance(self.block_plan, BlockShearAreaPlan):
            raise TypeError("block_plan must be BlockShearAreaPlan or None.")
        if self.lbr is not None:
            lbr_value = decimal_value(self.lbr)
            if not Decimal(0) <= lbr_value <= Decimal(1):
                raise ValueError("lbr must be in the inclusive range zero to one.")
            object.__setattr__(self, "lbr", lbr_value)
        _require_typed_tuple(self.warnings, MultiRowExecutionWarning, "warnings")
        _validate_check_payload(self)


type MultiRowEquationTrace = (
    BoltResistanceTrace
    | CombinedBoltTrace
    | PullThroughTrace
    | BearingTrace
    | SimplifiedFirstRowTrace
    | FullFirstRowTrace
    | UnknownLbrEnvelopeTrace
    | LowerEnvelopeTrace
    | InterrowShearOutTrace
    | BlockShearTrace
)


type MultiRowResultFactorTrace = MultiRowFactorTrace | FactorAssemblyTrace


@dataclass(frozen=True, slots=True)
class MultiRowCheckResult:
    result_id: str
    source_plan_id: str
    layer_id: str | None
    bolt_id: str | None
    row_id: str | None
    bolt_line_id: str | None
    path_id: str | None
    limit_state: MultiRowCheckFamily
    equation_method: MultiRowEquationMethod
    source_locator: str
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    availability: MultiRowResultAvailability
    geometry_status: GeometryStatus
    equation_nominal_resistance: PhysicalQuantity | None
    connection_adjusted_nominal_resistance: PhysicalQuantity | None
    design_resistance: PhysicalQuantity | None
    demand: PhysicalQuantity | None
    utilization: Decimal | None
    numerical_comparison: NumericalComparison
    factor_trace: MultiRowResultFactorTrace | None
    equation_trace: MultiRowEquationTrace | None
    warnings: tuple[MultiRowExecutionWarning, ...]
    versions: Slice2VersionContext
    input_fingerprint: str

    def __post_init__(self) -> None:
        _require_text(self.result_id, "result_id")
        _require_text(self.source_plan_id, "source_plan_id")
        _require_text(self.source_locator, "source_locator")
        _validate_sha256(self.input_fingerprint, "input_fingerprint")
        _require_typed_tuple(self.warnings, MultiRowExecutionWarning, "warnings")
        if self.utilization is not None:
            value = decimal_value(self.utilization)
            if value < 0:
                raise ValueError("utilization cannot be negative.")
            object.__setattr__(self, "utilization", value)
        numerical_values = (
            self.equation_nominal_resistance,
            self.connection_adjusted_nominal_resistance,
            self.design_resistance,
            self.demand,
            self.equation_trace,
        )
        if self.availability is MultiRowResultAvailability.CALCULATED:
            if any(item is None for item in numerical_values):
                raise ValueError("Calculated result requires resistance, demand, and trace values.")
            if self.numerical_comparison is NumericalComparison.NOT_EVALUATED:
                raise ValueError("Calculated result requires PASS or FAIL.")
            if self.design_resistance is not None and self.design_resistance.magnitude > 0:
                if self.utilization is None:
                    raise ValueError("Positive design resistance requires utilization.")
            elif self.utilization is not None:
                raise ValueError("Nonpositive design resistance cannot have utilization.")
        elif any(item is not None for item in (*numerical_values, self.utilization)):
            raise ValueError("Unavailable result cannot retain calculated numerical fields.")
        elif self.numerical_comparison is not NumericalComparison.NOT_EVALUATED:
            raise ValueError("Unavailable result must be NOT_EVALUATED.")


@dataclass(frozen=True, slots=True)
class MultiRowCalculationResult:
    results: tuple[MultiRowCheckResult, ...]
    required_check_ids: tuple[str, ...]
    calculated_check_ids: tuple[str, ...]
    not_applicable_check_ids: tuple[str, ...]
    incomplete_check_ids: tuple[str, ...]
    unsupported_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    governing_result_ids: tuple[str, ...]
    geometry_status: GeometryStatus
    availability: MultiRowResultAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    numerical_comparison: NumericalComparison
    overall_disposition: MultiRowOverallDisposition
    warnings: tuple[MultiRowExecutionWarning, ...]
    input_fingerprint: str
    result_fingerprint: str
    versions: Slice2VersionContext

    def __post_init__(self) -> None:
        _require_typed_tuple(self.results, MultiRowCheckResult, "results")
        for name in (
            "required_check_ids",
            "calculated_check_ids",
            "not_applicable_check_ids",
            "incomplete_check_ids",
            "unsupported_check_ids",
            "failed_check_ids",
            "governing_result_ids",
        ):
            _require_unique_string_tuple(cast(tuple[str, ...], getattr(self, name)), name, True)
        _require_typed_tuple(self.warnings, MultiRowExecutionWarning, "warnings")
        _validate_sha256(self.input_fingerprint, "input_fingerprint")
        _validate_sha256(self.result_fingerprint, "result_fingerprint")


@dataclass(frozen=True, slots=True)
class MultiRowExecutionBundle:
    physical_geometry: MultiRowPhysicalGeometryContext
    planning_root: MultiRowCalculationPlanSet
    block_shear_plans: BlockShearPlanSet
    end_distances: MultiRowEndDistanceContext
    layers: tuple[MultiRowLayerExecutionContext, ...]
    bolts: tuple[MultiRowBoltExecutionContext, ...]
    bolt_lines: tuple[MultiRowBoltLineExecutionContext, ...]
    signed_demand: MultiRowSignedDemandContext
    factors: MultiRowFactorContext
    required_checks: MultiRowRequiredCheckContract
    checks: tuple[MultiRowExecutableCheck, ...]
    provenance: MethodProvenance
    versions: Slice2VersionContext
    fingerprint_metadata: tuple[MultiRowFingerprintMetadataEntry, ...]
    eccentricity: BlockShearEccentricityContext | None = None

    def __post_init__(self) -> None:
        _require_typed_tuple(self.layers, MultiRowLayerExecutionContext, "layers")
        _require_typed_tuple(self.bolts, MultiRowBoltExecutionContext, "bolts")
        _require_typed_tuple(self.bolt_lines, MultiRowBoltLineExecutionContext, "bolt_lines")
        _require_typed_tuple(self.checks, MultiRowExecutableCheck, "checks")
        _require_typed_tuple(
            self.fingerprint_metadata,
            MultiRowFingerprintMetadataEntry,
            "fingerprint_metadata",
        )
        for name, expected in (
            ("physical_geometry", MultiRowPhysicalGeometryContext),
            ("planning_root", MultiRowCalculationPlanSet),
            ("block_shear_plans", BlockShearPlanSet),
            ("end_distances", MultiRowEndDistanceContext),
            ("signed_demand", MultiRowSignedDemandContext),
            ("factors", MultiRowFactorContext),
            ("required_checks", MultiRowRequiredCheckContract),
            ("provenance", MethodProvenance),
            ("versions", Slice2VersionContext),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TypeError(f"{name} must be {expected.__name__}.")
        if self.eccentricity is not None and not isinstance(
            self.eccentricity, BlockShearEccentricityContext
        ):
            raise TypeError("eccentricity must be BlockShearEccentricityContext or None.")
        _require_unique((item.layer_id for item in self.layers), "layer IDs")
        _require_unique((item.bolt_id for item in self.bolts), "bolt IDs")
        _require_unique((item.bolt_line_id for item in self.bolt_lines), "bolt-line IDs")
        _require_unique((item.check_id for item in self.checks), "check IDs")
        _require_unique((item.key for item in self.fingerprint_metadata), "metadata keys")
        known_checks = {item.check_id for item in self.checks}
        if not set(self.required_checks.required_check_ids) <= known_checks:
            raise ValueError("Every required check ID must identify one executable check.")
        layer_ids = {item.layer_id for item in self.layers}
        bolt_ids = {item.bolt_id for item in self.bolts}
        line_ids = {item.bolt_line_id for item in self.bolt_lines}
        block_ids = {item.path_id for item in self.block_shear_plans.candidates}
        for bolt in self.bolts:
            if not set(bolt.layer_ids) <= layer_ids:
                raise ValueError("Every bolt layer ID must identify an execution layer.")
        for check in self.checks:
            if check.layer_id is not None and check.layer_id not in layer_ids:
                raise ValueError("Check layer ID is absent from the execution bundle.")
            if check.bolt_id is not None and check.bolt_id not in bolt_ids:
                raise ValueError("Check bolt ID is absent from the execution bundle.")
            if check.bolt_line_id is not None and check.bolt_line_id not in line_ids:
                raise ValueError("Check bolt-line ID is absent from the execution bundle.")
            if check.block_plan is not None and check.block_plan.path_id not in block_ids:
                raise ValueError("Check block plan is absent from the complete block plan set.")
        _assert_deeply_immutable(self, "execution_bundle")


def physical_geometry_context(
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
) -> MultiRowPhysicalGeometryContext:
    """Freeze accepted float geometry into exact Decimal calculation/fingerprint input."""

    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    if source_length_unit not in {Unit.IN, Unit.MM}:
        raise ValueError("source_length_unit must be IN or MM.")
    bolts = tuple(
        MultiRowBoltGeometryContext(
            item.id,
            decimal_from_finite_real(item.center.x),
            decimal_from_finite_real(item.center.y),
            decimal_from_finite_real(item.bolt_diameter),
            decimal_from_finite_real(item.hole_diameter),
            item.bolt_identity,
            item.logical_connection_id,
        )
        for item in sorted(geometry.group.bolts, key=lambda value: value.id)
    )
    rows = tuple(
        MultiRowProjectedGroupContext(
            item.id,
            item.ordinal,
            decimal_from_finite_real(item.projected_coordinate),
            decimal_from_finite_real(item.raw_deviation),
            tuple(bolt.bolt.id for bolt in item.bolts),
        )
        for item in geometry.rows
    )
    lines = tuple(
        MultiRowProjectedGroupContext(
            item.id,
            item.ordinal,
            decimal_from_finite_real(item.projected_coordinate),
            decimal_from_finite_real(item.raw_deviation),
            tuple(bolt.bolt.id for bolt in item.bolts),
        )
        for item in geometry.bolt_lines
    )
    return MultiRowPhysicalGeometryContext(
        geometry.group.id,
        geometry.group.interface_id,
        geometry.boundary.id,
        source_length_unit,
        (
            decimal_from_finite_real(geometry.force_u[0]),
            decimal_from_finite_real(geometry.force_u[1]),
        ),
        (
            decimal_from_finite_real(geometry.force_v[0]),
            decimal_from_finite_real(geometry.force_v[1]),
        ),
        bolts,
        rows,
        lines,
        decimal_from_finite_real(geometry.unloaded_free_end_u),
        decimal_from_finite_real(geometry.loaded_end_u),
        decimal_from_finite_real(geometry.negative_side_v),
        decimal_from_finite_real(geometry.positive_side_v),
        decimal_from_finite_real(geometry.sorting_tolerance),
    )


def resolve_multirow_end_distances(
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
    *,
    exact_unloaded_end_e1: PhysicalQuantity | None = None,
    exact_physical_pitches: tuple[PhysicalQuantity, ...] | None = None,
    exact_loaded_boundary_to_row_1_distance: PhysicalQuantity | None = None,
) -> MultiRowEndDistanceContext:
    """Resolve exact distances before validation, never from float arithmetic results."""

    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    if source_length_unit not in {Unit.IN, Unit.MM}:
        raise ValueError("source_length_unit must be IN or MM.")
    if not geometry.rows:
        raise ValueError("Resolved multi-row geometry must contain at least one row.")
    first_row = geometry.rows[0]
    nearest_row = geometry.rows[-1]
    exact_inputs = (
        exact_unloaded_end_e1,
        exact_physical_pitches,
        exact_loaded_boundary_to_row_1_distance,
    )
    if any(item is not None for item in exact_inputs) and not all(
        item is not None for item in exact_inputs
    ):
        raise ValueError("Exact end-distance inputs must be supplied together.")
    if exact_unloaded_end_e1 is not None:
        if not isinstance(exact_physical_pitches, tuple):
            raise TypeError("exact_physical_pitches must be an immutable tuple.")
        if len(exact_physical_pitches) != len(geometry.rows) - 1:
            raise ValueError("Exact physical pitches must match the resolved row count.")
        if exact_loaded_boundary_to_row_1_distance is None:  # pragma: no cover - guarded above
            raise RuntimeError("Exact loaded-boundary distance is required.")
        unloaded_end_e1 = exact_unloaded_end_e1.to(source_length_unit)
        pitches = tuple(item.to(source_length_unit) for item in exact_physical_pitches)
        loaded_boundary_to_row_1_distance = exact_loaded_boundary_to_row_1_distance.to(
            source_length_unit
        )
        row_1_to_unloaded_end_distance = unloaded_end_e1
        for pitch in pitches:
            row_1_to_unloaded_end_distance += pitch
    else:
        # Geometry kernels expose render-compatible floats.  Recover each stored
        # coordinate independently, then perform authoritative subtraction in
        # Decimal space so no binary-float arithmetic result becomes authority.
        row_coordinates = tuple(
            decimal_from_finite_real(row.projected_coordinate) for row in geometry.rows
        )
        unloaded_coordinate = decimal_from_finite_real(geometry.unloaded_free_end_u)
        loaded_coordinate = decimal_from_finite_real(geometry.loaded_end_u)
        pitches = tuple(
            PhysicalQuantity(
                row_coordinates[index] - row_coordinates[index + 1], source_length_unit
            )
            for index in range(len(row_coordinates) - 1)
        )
        unloaded_end_e1 = PhysicalQuantity(
            row_coordinates[-1] - unloaded_coordinate, source_length_unit
        )
        row_1_to_unloaded_end_distance = PhysicalQuantity(
            row_coordinates[0] - unloaded_coordinate, source_length_unit
        )
        loaded_boundary_to_row_1_distance = PhysicalQuantity(
            loaded_coordinate - row_coordinates[0], source_length_unit
        )
    return MultiRowEndDistanceContext(
        unloaded_end_e1,
        row_1_to_unloaded_end_distance,
        loaded_boundary_to_row_1_distance,
        pitches,
        f"{geometry.boundary.id}:UNLOADED_FREE_END",
        nearest_row.id,
        first_row.id,
        (
            f"{geometry.boundary.id}:NEGATIVE_SIDE",
            f"{geometry.boundary.id}:POSITIVE_SIDE",
        ),
    )


def canonical_multirow_execution_json(bundle: MultiRowExecutionBundle) -> str:
    """Serialize the deeply immutable execution input without presentation state."""

    if not isinstance(bundle, MultiRowExecutionBundle):
        raise TypeError("bundle must be MultiRowExecutionBundle.")
    payload = _canonicalize(bundle)
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def multirow_execution_fingerprint(bundle: MultiRowExecutionBundle) -> str:
    return hashlib.sha256(canonical_multirow_execution_json(bundle).encode("utf-8")).hexdigest()


def calculate_multirow_connection(
    execution_bundle: MultiRowExecutionBundle,
) -> MultiRowCalculationResult:
    """Execute one deterministic Slice 2 bundle without framework or external access."""

    if not isinstance(execution_bundle, MultiRowExecutionBundle):
        raise TypeError("execution_bundle must be MultiRowExecutionBundle.")
    input_fingerprint = multirow_execution_fingerprint(execution_bundle)
    results = tuple(
        _execute_check(execution_bundle, check, input_fingerprint)
        for check in execution_bundle.checks
    )
    required_ids = execution_bundle.required_checks.required_check_ids
    required = tuple(item for item in results if item.result_id in required_ids)
    geometry_status = (
        GeometryStatus.INVALID_GEOMETRY
        if any(item.geometry_status is GeometryStatus.INVALID_GEOMETRY for item in required)
        else GeometryStatus.VALID
    )
    numerical = _aggregate_numerical(required)
    availability = _aggregate_availability(required)
    method = _aggregate_method(required)
    qualification = _aggregate_qualification(required)
    disposition = _aggregate_disposition(
        required,
        geometry_status,
        numerical,
        method,
        qualification,
    )
    governing = _governing_result_ids(required)
    warnings = _unique_warnings(tuple(warning for item in results for warning in item.warnings))
    calculated = tuple(
        item.result_id
        for item in results
        if item.availability is MultiRowResultAvailability.CALCULATED
    )
    not_applicable = _ids_with_availability(results, MultiRowResultAvailability.NOT_APPLICABLE)
    incomplete = _ids_with_availability(results, MultiRowResultAvailability.INCOMPLETE_INPUT)
    unsupported = tuple(
        item.result_id
        for item in results
        if item.availability
        in {
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
            MultiRowResultAvailability.SOURCE_DATA_PENDING,
        }
    )
    failed = tuple(
        item.result_id for item in results if item.numerical_comparison is NumericalComparison.FAIL
    )
    result_payload = (
        input_fingerprint,
        results,
        required_ids,
        governing,
        geometry_status,
        availability,
        method,
        qualification,
        numerical,
        disposition,
        warnings,
        execution_bundle.versions,
    )
    result_fingerprint = hashlib.sha256(
        json.dumps(
            _canonicalize(result_payload),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return MultiRowCalculationResult(
        results,
        required_ids,
        calculated,
        not_applicable,
        incomplete,
        unsupported,
        failed,
        governing,
        geometry_status,
        availability,
        method,
        qualification,
        numerical,
        disposition,
        warnings,
        input_fingerprint,
        result_fingerprint,
        execution_bundle.versions,
    )


def _execute_check(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
    fingerprint: str,
) -> MultiRowCheckResult:
    if check.geometry_status is GeometryStatus.INVALID_GEOMETRY:
        return _unavailable_result(check, MultiRowResultAvailability.INVALID_GEOMETRY, fingerprint)
    if check.plan_availability is not PlanAvailability.READY:
        return _unavailable_result(
            check, _result_availability(check.plan_availability), fingerprint
        )
    try:
        return _calculate_check(bundle, check, fingerprint)
    except _MissingBoltAxisDemand as error:
        return _unavailable_result(
            check,
            MultiRowResultAvailability.INCOMPLETE_INPUT,
            fingerprint,
            (*check.warnings, error.warning),
        )
    except _IncompleteEccentricity:
        return _unavailable_result(check, MultiRowResultAvailability.INCOMPLETE_INPUT, fingerprint)
    except ValueError:
        return _unavailable_result(check, MultiRowResultAvailability.INVALID_GEOMETRY, fingerprint)
    except ArithmeticError:
        warning = MultiRowExecutionWarning(
            MultiRowExecutionWarningCode.NUMERICAL_DOMAIN_ERROR,
            (f"check_id:{check.check_id}",),
        )
        return _unavailable_result(
            check,
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
            fingerprint,
            (*check.warnings, warning),
        )


def _calculate_check(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
    fingerprint: str,
) -> MultiRowCheckResult:
    if check.family in {
        MultiRowCheckFamily.CODE_GEOMETRY,
        MultiRowCheckFamily.QUALIFICATION,
        MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW,
    }:
        return _unavailable_result(check, _status_only_availability(check), fingerprint)
    demand = check.demand
    if demand is None:
        return _unavailable_result(check, MultiRowResultAvailability.INCOMPLETE_INPUT, fingerprint)
    warnings = list(check.warnings)
    if bundle.factors.pitch_factor_c_delta < 1:
        warnings.append(
            MultiRowExecutionWarning(
                MultiRowExecutionWarningCode.REDUCED_PITCH_FACTOR_APPLIED,
                (f"c_delta:{canonical_decimal_string(bundle.factors.pitch_factor_c_delta)}",),
            )
        )
    trace: MultiRowEquationTrace
    factor_trace: MultiRowResultFactorTrace | None
    equation_nominal: PhysicalQuantity
    connection_nominal: PhysicalQuantity
    design: PhysicalQuantity
    if check.family in {
        MultiRowCheckFamily.BOLT_SHEAR,
        MultiRowCheckFamily.BOLT_TENSION,
        MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
        MultiRowCheckFamily.PULL_THROUGH,
        MultiRowCheckFamily.PIN_BEARING,
    }:
        trace, factor_trace, equation_nominal, connection_nominal, design, extra = (
            _execute_reused_check(bundle, check)
        )
        warnings.extend(extra)
    elif check.family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION:
        trace, factor_trace = _execute_first_row(bundle, check)
        equation_nominal, connection_nominal, design = _resistances(trace, factor_trace)
    elif check.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT:
        trace = _execute_interrow(bundle, check)
        factor_trace = trace.factor_trace
        equation_nominal, connection_nominal, design = _resistances(trace, factor_trace)
    else:
        trace, extra = _execute_block_shear(bundle, check)
        warnings.extend(extra)
        factor_trace = trace.factor_trace
        equation_nominal, connection_nominal, design = _resistances(trace, factor_trace)
    comparison = compare_resistance(demand, design)
    warnings.extend(
        MultiRowExecutionWarning(MultiRowExecutionWarningCode(item)) for item in comparison.warnings
    )
    return MultiRowCheckResult(
        check.check_id,
        check.source_plan_id,
        check.layer_id,
        check.bolt_id,
        check.row_id,
        check.bolt_line_id,
        check.path_id,
        check.family,
        check.method,
        check.source_locator,
        check.method_applicability,
        check.qualification,
        MultiRowResultAvailability.CALCULATED,
        GeometryStatus.VALID,
        equation_nominal,
        connection_nominal,
        design,
        demand,
        comparison.utilization,
        comparison.numerical_comparison,
        factor_trace,
        trace,
        _unique_warnings(tuple(warnings)),
        bundle.versions,
        fingerprint,
    )


def _execute_reused_check(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
) -> tuple[
    BoltResistanceTrace | CombinedBoltTrace | PullThroughTrace | BearingTrace,
    FactorAssemblyTrace | None,
    PhysicalQuantity,
    PhysicalQuantity,
    PhysicalQuantity,
    tuple[MultiRowExecutionWarning, ...],
]:
    bolt = _bolt(bundle, check.bolt_id)
    fnt = bolt.fastener.fnt
    if (
        check.family
        in {
            MultiRowCheckFamily.BOLT_SHEAR,
            MultiRowCheckFamily.BOLT_TENSION,
            MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
        }
        and fnt is None
    ):
        raise ValueError("Ready bolt checks require explicit Fnt.")
    if check.family is MultiRowCheckFamily.BOLT_SHEAR:
        shear_trace = bolt_shear_resistance(
            bolt.diameter, cast(PhysicalQuantity, fnt), bolt.shear_thread_status
        )
        return (
            shear_trace,
            None,
            shear_trace.nominal_resistance,
            shear_trace.nominal_resistance,
            shear_trace.design_resistance,
            (),
        )
    if (
        check.family
        in {
            MultiRowCheckFamily.BOLT_TENSION,
            MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
            MultiRowCheckFamily.PULL_THROUGH,
        }
        and bolt.bolt_axis_tension_demand is None
    ):
        warning = MultiRowExecutionWarning(
            MultiRowExecutionWarningCode.MISSING_REQUIRED_BOLT_AXIS_TENSION,
            (f"bolt_id:{bolt.bolt_id}",),
        )
        raise _MissingBoltAxisDemand(warning)
    if check.family is MultiRowCheckFamily.BOLT_TENSION:
        tension_trace = bolt_tension_resistance(bolt.diameter, cast(PhysicalQuantity, fnt))
        return (
            tension_trace,
            None,
            tension_trace.nominal_resistance,
            tension_trace.nominal_resistance,
            tension_trace.design_resistance,
            (),
        )
    if check.family is MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR:
        combined_trace = combined_bolt_tension_shear_resistance(
            bolt.diameter,
            cast(PhysicalQuantity, fnt),
            bolt.shear_thread_status,
            bolt.in_plane_demand,
        )
        return (
            combined_trace,
            None,
            combined_trace.nominal_tensile_resistance,
            combined_trace.nominal_tensile_resistance,
            combined_trace.design_tensile_resistance,
            (),
        )
    layer = _layer(bundle, check.layer_id)
    if check.family is MultiRowCheckFamily.PULL_THROUGH:
        if bolt.washer is None:
            raise ValueError("Pull-through requires explicit washer geometry.")
        shear = adjusted_property_trace(
            _property(layer, FRPPropertyKind.FSH_LT), layer.end_use_factors
        )
        interlaminar = adjusted_property_trace(
            _property(layer, FRPPropertyKind.FSH_INT), layer.end_use_factors
        )
        pull_through_trace = pull_through_resistance(
            bolt.washer.outside_diameter,
            layer.thickness,
            shear,
            interlaminar,
            c_delta=Decimal(1),
            lambda_factor=bundle.factors.time_effect_factor_lambda,
        )
        factor_trace = pull_through_trace.factor_trace
        return (
            pull_through_trace,
            factor_trace,
            factor_trace.nominal_resistance,
            factor_trace.nominal_resistance,
            factor_trace.design_resistance,
            (),
        )
    property_kind = (
        FRPPropertyKind.FBR_L
        if layer.material_direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FBR_T
    )
    bearing_property = adjusted_property_trace(
        _property(layer, property_kind), layer.end_use_factors
    )
    bearing_trace = pin_bearing_resistance(
        layer.thickness,
        bolt.diameter,
        bearing_property,
        layer.bearing_thread_status,
        c_delta=bundle.factors.pitch_factor_c_delta,
        c_lap=bundle.factors.lap_factor_c_lap,
        lambda_factor=bundle.factors.time_effect_factor_lambda,
    )
    factor_trace = bearing_trace.factor_trace
    connection_nominal = factor_trace.nominal_resistance * (
        factor_trace.c_delta * factor_trace.c_lap
    )
    return (
        bearing_trace,
        factor_trace,
        factor_trace.nominal_resistance,
        connection_nominal,
        factor_trace.design_resistance,
        (),
    )


class _MissingBoltAxisDemand(ArithmeticError):
    def __init__(self, warning: MultiRowExecutionWarning) -> None:
        super().__init__(warning.code.value)
        self.warning = warning


def _execute_first_row(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
) -> tuple[
    SimplifiedFirstRowTrace | FullFirstRowTrace | LowerEnvelopeTrace,
    MultiRowFactorTrace,
]:
    plan = cast(FirstRowNetTensionPlan, check.first_row_plan)
    layer = _layer(bundle, check.layer_id)
    width = plan.geometry.effective_width
    if width is None:
        raise ValueError("First-row execution requires planning-resolved effective width.")
    property_kind = (
        FRPPropertyKind.FT_L
        if layer.material_direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FT_T
    )
    tensile = adjusted_property_trace(_property(layer, property_kind), layer.end_use_factors)
    common = {
        "lap_factor_c_lap": bundle.factors.lap_factor_c_lap,
        "pitch_factor_c_delta": bundle.factors.pitch_factor_c_delta,
        "time_effect_factor_lambda": bundle.factors.time_effect_factor_lambda,
    }
    if check.method is MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED:
        simplified_trace = simplified_first_row_resistance(
            width, layer.thickness, tensile, layer.material_direction, **common
        )
        return simplified_trace, simplified_trace.factor_trace
    coefficient = plan.coefficient_inputs
    if coefficient is None:
        raise ValueError("Full first-row execution requires coefficient inputs.")
    if check.method is MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL:
        lbr = check.lbr if check.lbr is not None else plan.lbr
        if lbr is None:
            raise ValueError("Selected full first-row execution requires L_br.")
        full_trace = full_first_row_resistance(
            width,
            plan.geometry.bolt_diameter,
            plan.net_hole_diameter,
            layer.thickness,
            bundle.end_distances.unloaded_end_e1,
            tensile,
            layer.material_direction,
            layer.element_classification,
            plan.geometry.bolts_per_row,
            lbr,
            gauge=plan.geometry.gauge,
            **common,
        )
        return full_trace, full_trace.factor_trace
    simplified_trace = simplified_first_row_resistance(
        width, layer.thickness, tensile, layer.material_direction, **common
    )
    endpoints = unknown_lbr_endpoint_envelope(
        width,
        plan.geometry.bolt_diameter,
        plan.net_hole_diameter,
        layer.thickness,
        bundle.end_distances.unloaded_end_e1,
        tensile,
        layer.material_direction,
        layer.element_classification,
        plan.geometry.bolts_per_row,
        gauge=plan.geometry.gauge,
        **common,
    )
    lower_trace = lower_first_row_envelope(simplified_trace, endpoints)
    factor_trace = (
        simplified_trace.factor_trace
        if lower_trace.selected_design_resistance == simplified_trace.factor_trace.design_resistance
        else endpoints.lbr_0.factor_trace
        if lower_trace.selected_design_resistance == endpoints.lbr_0.factor_trace.design_resistance
        else endpoints.lbr_1.factor_trace
    )
    return lower_trace, factor_trace


def _execute_interrow(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
) -> InterrowShearOutTrace:
    plan = cast(InterrowShearOutPlan, check.interrow_plan)
    layer = _layer(bundle, check.layer_id)
    shear = adjusted_property_trace(_property(layer, FRPPropertyKind.FSH_LT), layer.end_use_factors)
    line = _line(bundle, check.bolt_line_id)
    if not line.equivalent_rectangular_line and not bundle.provenance.engineer_confirmed:
        raise ValueError("Nonuniform bolt-line demand requires confirmed explicit provenance.")
    return interrow_shear_out_resistance(
        plan.method,
        bundle.end_distances.unloaded_end_e1,
        plan.hole_diameter,
        bundle.end_distances.physical_pitches,
        layer.thickness,
        shear,
        lap_factor_c_lap=bundle.factors.lap_factor_c_lap,
        pitch_factor_c_delta=bundle.factors.pitch_factor_c_delta,
        time_effect_factor_lambda=bundle.factors.time_effect_factor_lambda,
    )


def _execute_block_shear(
    bundle: MultiRowExecutionBundle,
    check: MultiRowExecutableCheck,
) -> tuple[BlockShearTrace, tuple[MultiRowExecutionWarning, ...]]:
    plan = cast(BlockShearAreaPlan, check.block_plan)
    layer = _layer(bundle, check.layer_id)
    if layer.material_direction is not MaterialDirection.LONGITUDINAL:
        raise ValueError("Automatic block shear is supported only for longitudinal material.")
    if plan.path_status is not BlockPathPlanStatus.ACCEPTED:
        raise ValueError("Rejected block path cannot execute.")
    if (
        plan.shear_net_area_status is NetAreaStatus.INVALID_GEOMETRY
        or plan.tension_net_area_status is NetAreaStatus.INVALID_GEOMETRY
    ):
        raise ValueError("Block path has nonpositive raw net area.")
    if bundle.eccentricity is None:
        raise _IncompleteEccentricity
    equation = (
        BlockShearEquation.ASCE_EQ_8_14A
        if bundle.eccentricity.classification is BlockShearEccentricityClassification.CONCENTRIC
        else BlockShearEquation.ASCE_EQ_8_14B
    )
    shear = adjusted_property_trace(_property(layer, FRPPropertyKind.FSH_LT), layer.end_use_factors)
    tensile = adjusted_property_trace(_property(layer, FRPPropertyKind.FT_L), layer.end_use_factors)
    trace = block_shear_resistance(
        equation,
        plan.net_shear_area,
        plan.net_tension_area,
        shear,
        tensile,
        lap_factor_c_lap=bundle.factors.lap_factor_c_lap,
        pitch_factor_c_delta=bundle.factors.pitch_factor_c_delta,
        time_effect_factor_lambda=bundle.factors.time_effect_factor_lambda,
    )
    warnings = [
        MultiRowExecutionWarning(
            MultiRowExecutionWarningCode.RATIONAL_BLOCK_PATH_RESOLVER_USED,
            (f"path_id:{plan.path_id}",),
        )
    ]
    if equation is BlockShearEquation.ASCE_EQ_8_14B:
        warnings.append(
            MultiRowExecutionWarning(
                MultiRowExecutionWarningCode.LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS,
                (f"path_id:{plan.path_id}",),
            )
        )
    if (
        plan.shear_net_area_status is NetAreaStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
        or plan.tension_net_area_status is NetAreaStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    ):
        warnings.append(
            MultiRowExecutionWarning(
                MultiRowExecutionWarningCode.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
                (f"path_id:{plan.path_id}",),
            )
        )
    return trace, tuple(warnings)


class _IncompleteEccentricity(ValueError):
    pass


def _resistances(
    trace: MultiRowEquationTrace,
    factor_trace: MultiRowFactorTrace,
) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    if isinstance(trace, LowerEnvelopeTrace):
        selected = trace.selected_design_resistance
        candidates = (
            trace.simplified.factor_trace,
            trace.full_unknown_lbr.lbr_0.factor_trace,
            trace.full_unknown_lbr.lbr_1.factor_trace,
        )
        chosen = next(item for item in candidates if item.design_resistance == selected)
        return (
            chosen.equation_nominal_resistance,
            chosen.connection_adjusted_nominal_resistance,
            selected,
        )
    return (
        factor_trace.equation_nominal_resistance,
        factor_trace.connection_adjusted_nominal_resistance,
        factor_trace.design_resistance,
    )


def _unavailable_result(
    check: MultiRowExecutableCheck,
    availability: MultiRowResultAvailability,
    fingerprint: str,
    warnings: tuple[MultiRowExecutionWarning, ...] | None = None,
) -> MultiRowCheckResult:
    return MultiRowCheckResult(
        check.check_id,
        check.source_plan_id,
        check.layer_id,
        check.bolt_id,
        check.row_id,
        check.bolt_line_id,
        check.path_id,
        check.family,
        check.method,
        check.source_locator,
        check.method_applicability,
        check.qualification,
        availability,
        check.geometry_status,
        None,
        None,
        None,
        None,
        None,
        NumericalComparison.NOT_EVALUATED,
        None,
        None,
        check.warnings if warnings is None else warnings,
        Slice2VersionContext(),
        fingerprint,
    )


def _status_only_availability(check: MultiRowExecutableCheck) -> MultiRowResultAvailability:
    if check.family is MultiRowCheckFamily.CODE_GEOMETRY:
        return MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    if check.family is MultiRowCheckFamily.QUALIFICATION:
        return MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED
    return MultiRowResultAvailability.ENGINEERING_REVIEW_REQUIRED


def _result_availability(value: PlanAvailability) -> MultiRowResultAvailability:
    mapping = {
        PlanAvailability.NOT_APPLICABLE: MultiRowResultAvailability.NOT_APPLICABLE,
        PlanAvailability.INCOMPLETE_INPUT: MultiRowResultAvailability.INCOMPLETE_INPUT,
        PlanAvailability.SOURCE_DATA_PENDING: MultiRowResultAvailability.SOURCE_DATA_PENDING,
        PlanAvailability.CALCULATION_NOT_SUPPORTED: (
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED
        ),
        PlanAvailability.ENGINEERING_REVIEW_REQUIRED: (
            MultiRowResultAvailability.ENGINEERING_REVIEW_REQUIRED
        ),
        PlanAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED: (
            MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED
        ),
        PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED: (
            MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
        ),
    }
    return mapping[value]


def _aggregate_numerical(
    required: tuple[MultiRowCheckResult, ...],
) -> NumericalComparison:
    if not required:
        return NumericalComparison.NOT_EVALUATED
    if any(item.numerical_comparison is NumericalComparison.FAIL for item in required):
        return NumericalComparison.FAIL
    if any(item.numerical_comparison is NumericalComparison.NOT_EVALUATED for item in required):
        return NumericalComparison.NOT_EVALUATED
    return NumericalComparison.PASS


def _aggregate_availability(
    required: tuple[MultiRowCheckResult, ...],
) -> MultiRowResultAvailability:
    precedence = (
        MultiRowResultAvailability.INVALID_GEOMETRY,
        MultiRowResultAvailability.INCOMPLETE_INPUT,
        MultiRowResultAvailability.SOURCE_DATA_PENDING,
        MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
        MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
        MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        MultiRowResultAvailability.ENGINEERING_REVIEW_REQUIRED,
        MultiRowResultAvailability.NOT_APPLICABLE,
    )
    for candidate in precedence:
        if any(item.availability is candidate for item in required):
            return candidate
    return (
        MultiRowResultAvailability.CALCULATED
        if required
        else MultiRowResultAvailability.NOT_APPLICABLE
    )


def _aggregate_method(
    required: tuple[MultiRowCheckResult, ...],
) -> MultiRowMethodApplicability:
    precedence = (
        MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE,
        MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
        MultiRowMethodApplicability.ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION,
        MultiRowMethodApplicability.ASCE_COMMENTARY_METHOD,
        MultiRowMethodApplicability.ASCE_PRESCRIPTIVE,
    )
    for candidate in precedence:
        if any(item.method_applicability is candidate for item in required):
            return candidate
    return MultiRowMethodApplicability.ASCE_PRESCRIPTIVE


def _aggregate_qualification(
    required: tuple[MultiRowCheckResult, ...],
) -> QualificationDisposition:
    if any(
        item.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
        for item in required
    ):
        return QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if any(
        item.qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
        for item in required
    ):
        return QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
    return QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE


def _aggregate_disposition(
    required: tuple[MultiRowCheckResult, ...],
    geometry: GeometryStatus,
    numerical: NumericalComparison,
    method: MultiRowMethodApplicability,
    qualification: QualificationDisposition,
) -> MultiRowOverallDisposition:
    if not required:
        return MultiRowOverallDisposition.NOT_EVALUATED
    if geometry is GeometryStatus.INVALID_GEOMETRY:
        return MultiRowOverallDisposition.INVALID_GEOMETRY
    if numerical is NumericalComparison.FAIL:
        return MultiRowOverallDisposition.FAIL
    if any(
        item.availability
        in {
            MultiRowResultAvailability.INCOMPLETE_INPUT,
            MultiRowResultAvailability.SOURCE_DATA_PENDING,
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
        }
        for item in required
    ):
        return MultiRowOverallDisposition.INCOMPLETE_OR_UNSUPPORTED
    if any(
        item.availability is MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
        or any(
            warning.code is MultiRowExecutionWarningCode.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
            for warning in item.warnings
        )
        for item in required
    ):
        return MultiRowOverallDisposition.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    if (
        method
        in {
            MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
            MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE,
        }
        or qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    ):
        return MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED:
        return MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED
    return (
        MultiRowOverallDisposition.PASS
        if numerical is NumericalComparison.PASS
        else MultiRowOverallDisposition.NOT_EVALUATED
    )


def _governing_result_ids(
    required: tuple[MultiRowCheckResult, ...],
) -> tuple[str, ...]:
    calculated = tuple(item for item in required if item.utilization is not None)
    if not calculated:
        return ()
    maximum = max(cast(Decimal, item.utilization) for item in calculated)
    return tuple(
        item.result_id
        for item in calculated
        if maximum - cast(Decimal, item.utilization) <= GOVERNING_UTILIZATION_TOLERANCE
    )


def _ids_with_availability(
    results: tuple[MultiRowCheckResult, ...],
    availability: MultiRowResultAvailability,
) -> tuple[str, ...]:
    return tuple(item.result_id for item in results if item.availability is availability)


def _bolt(
    bundle: MultiRowExecutionBundle,
    identity: str | None,
) -> MultiRowBoltExecutionContext:
    for item in bundle.bolts:
        if item.bolt_id == identity:
            return item
    raise ValueError("Executable check requires a known bolt ID.")


def _layer(
    bundle: MultiRowExecutionBundle,
    identity: str | None,
) -> MultiRowLayerExecutionContext:
    for item in bundle.layers:
        if item.layer_id == identity:
            return item
    raise ValueError("Executable check requires a known layer ID.")


def _line(
    bundle: MultiRowExecutionBundle,
    identity: str | None,
) -> MultiRowBoltLineExecutionContext:
    for item in bundle.bolt_lines:
        if item.bolt_line_id == identity:
            return item
    raise ValueError("Executable check requires a known bolt-line ID.")


def _property(
    layer: MultiRowLayerExecutionContext,
    kind: FRPPropertyKind,
) -> FRPPropertyEntry:
    value = layer.material.lookup(kind)
    if value is None:
        raise ValueError(f"Layer material lacks required property {kind.value}.")
    return value


def _validate_check_payload(check: MultiRowExecutableCheck) -> None:
    first_row = check.family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
    interrow = check.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    block = check.family is MultiRowCheckFamily.BLOCK_SHEAR
    if first_row != (check.first_row_plan is not None):
        raise ValueError("First-row check requires exactly one first-row plan payload.")
    if interrow != (check.interrow_plan is not None):
        raise ValueError("Inter-row check requires exactly one inter-row plan payload.")
    if block != (check.block_plan is not None):
        raise ValueError("Block-shear check requires exactly one block plan payload.")
    if first_row and check.layer_id is None:
        raise ValueError("First-row check requires layer_id.")
    if interrow and (check.layer_id is None or check.bolt_line_id is None):
        raise ValueError("Inter-row check requires layer_id and bolt_line_id.")
    if block and (check.layer_id is None or check.path_id is None):
        raise ValueError("Block-shear check requires layer_id and path_id.")
    bolt_families = {
        MultiRowCheckFamily.BOLT_SHEAR,
        MultiRowCheckFamily.BOLT_TENSION,
        MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
        MultiRowCheckFamily.PULL_THROUGH,
        MultiRowCheckFamily.PIN_BEARING,
    }
    if check.family in bolt_families and check.bolt_id is None:
        raise ValueError("Per-bolt check requires bolt_id.")
    if check.family in {MultiRowCheckFamily.PULL_THROUGH, MultiRowCheckFamily.PIN_BEARING} and (
        check.layer_id is None
    ):
        raise ValueError("Layer-specific per-bolt check requires layer_id.")
    expected_method = {
        MultiRowCheckFamily.BOLT_SHEAR: MultiRowEquationMethod.BOLT_SHEAR,
        MultiRowCheckFamily.BOLT_TENSION: MultiRowEquationMethod.BOLT_TENSION,
        MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR: (
            MultiRowEquationMethod.BOLT_COMBINED_TENSION_SHEAR
        ),
        MultiRowCheckFamily.PULL_THROUGH: MultiRowEquationMethod.PULL_THROUGH,
        MultiRowCheckFamily.PIN_BEARING: MultiRowEquationMethod.PIN_BEARING,
        MultiRowCheckFamily.CODE_GEOMETRY: MultiRowEquationMethod.STATUS_ONLY,
        MultiRowCheckFamily.QUALIFICATION: MultiRowEquationMethod.STATUS_ONLY,
        MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW: MultiRowEquationMethod.STATUS_ONLY,
    }.get(check.family)
    if expected_method is not None and check.method is not expected_method:
        raise ValueError("Check family and equation method are inconsistent.")
    if check.first_row_plan is not None:
        mapping = {
            FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED: (
                MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED
            ),
            FirstRowPlanMethod.ASCE_COMMENTARY_FULL: (
                MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL
            ),
            FirstRowPlanMethod.RATIONAL_MULTIROW_LOWER_ENVELOPE: (
                MultiRowEquationMethod.FIRST_ROW_RATIONAL_LOWER_ENVELOPE
            ),
        }
        if check.method is not mapping[check.first_row_plan.method]:
            raise ValueError("First-row plan method and executable method are inconsistent.")
    if check.interrow_plan is not None:
        expected = {
            "ASCE_EQ_8_12": MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12,
            "ASCE_EQ_8_13": MultiRowEquationMethod.INTERROW_ASCE_EQ_8_13,
            "RATIONAL_EXTENSION_EQ_8_13": (
                MultiRowEquationMethod.INTERROW_RATIONAL_EXTENSION_EQ_8_13
            ),
        }[check.interrow_plan.method.value]
        if check.method is not expected:
            raise ValueError("Inter-row plan method and executable method are inconsistent.")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text.")


def _require_string_tuple(value: tuple[str, ...], name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, str) or not item for item in value):
        raise TypeError(f"{name} must be an immutable tuple of nonempty strings.")


def _require_unique_string_tuple(
    value: tuple[str, ...],
    name: str,
    allow_empty: bool = False,
) -> None:
    _require_string_tuple(value, name)
    if not value and not allow_empty:
        raise ValueError(f"{name} cannot be empty.")
    _require_unique(value, name)


def _require_unique(values: Iterable[str], name: str) -> None:
    sequence = tuple(values)
    if len(sequence) != len(set(sequence)):
        raise ValueError(f"{name} must be unique.")


def _require_typed_tuple(value: object, expected: type[object], name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, expected) for item in value):
        raise TypeError(f"{name} must be an immutable tuple of {expected.__name__} values.")


def _require_nonnegative_force(value: PhysicalQuantity, name: str) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.FORCE:
        raise ValueError(f"{name} must be a force quantity.")
    if value.magnitude < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
        raise ValueError(f"{name} must be lowercase SHA-256 hex.")


def _assert_deeply_immutable(value: object, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int, Decimal, Enum, date)):
        return
    if isinstance(value, float):
        raise TypeError(f"{path} contains an authoritative binary float.")
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            _assert_deeply_immutable(item, f"{path}[{index}]")
        return
    if isinstance(value, (list, dict, set)):
        raise TypeError(f"{path} contains mutable nested state.")
    if is_dataclass(value) and not isinstance(value, type):
        parameters = getattr(type(value), "__dataclass_params__", None)
        if parameters is None or not parameters.frozen:
            raise TypeError(f"{path} contains a non-frozen dataclass.")
        for field in fields(value):
            _assert_deeply_immutable(getattr(value, field.name), f"{path}.{field.name}")
        return
    raise TypeError(f"{path} contains unsupported value type {type(value).__name__}.")


type CanonicalExecutionValue = (
    str | bool | int | list["CanonicalExecutionValue"] | dict[str, "CanonicalExecutionValue"] | None
)


def _canonicalize(value: object) -> CanonicalExecutionValue:
    if isinstance(value, Enum):
        return cast(str, value.value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "canonical_magnitude": value.canonical_string,
            "canonical_unit": value.canonical_unit.value,
        }
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"Unsupported fingerprint value type {type(value).__name__}.")


def _unique_warnings(
    values: tuple[MultiRowExecutionWarning, ...],
) -> tuple[MultiRowExecutionWarning, ...]:
    seen: set[tuple[MultiRowExecutionWarningCode, tuple[str, ...]]] = set()
    result: list[MultiRowExecutionWarning] = []
    for item in values:
        identity = (item.code, item.trace)
        if identity not in seen:
            seen.add(identity)
            result.append(item)
    return tuple(result)


__all__ = (
    "SLICE_2_CALCULATION_CONTRACT_VERSION",
    "SLICE_2_CALCULATION_ENGINE_VERSION",
    "SLICE_2_ENGINEERING_RULE_SET_VERSION",
    "SLICE_2_EXECUTION_INPUT_SCHEMA",
    "SLICE_2_EXECUTION_INPUT_SCHEMA_VERSION",
    "SLICE_2_FINGERPRINT_SCHEMA",
    "SLICE_2_FINGERPRINT_SCHEMA_VERSION",
    "SLICE_2_GOLDEN_SCHEMA",
    "SLICE_2_RESULT_SCHEMA",
    "SLICE_2_RESULT_SCHEMA_VERSION",
    "BlockShearEccentricityContext",
    "MultiRowBoltExecutionContext",
    "MultiRowBoltGeometryContext",
    "MultiRowBoltLineExecutionContext",
    "MultiRowCalculationResult",
    "MultiRowCheckFamily",
    "MultiRowCheckResult",
    "MultiRowEndDistanceContext",
    "MultiRowEquationMethod",
    "MultiRowExecutableCheck",
    "MultiRowExecutionBundle",
    "MultiRowExecutionWarning",
    "MultiRowExecutionWarningCode",
    "MultiRowFactorContext",
    "MultiRowFingerprintMetadataEntry",
    "MultiRowLayerExecutionContext",
    "MultiRowOverallDisposition",
    "MultiRowPhysicalGeometryContext",
    "MultiRowProjectedGroupContext",
    "MultiRowRequiredCheckContract",
    "MultiRowResultAvailability",
    "MultiRowSignedDemandContext",
    "PitchFactorSource",
    "Slice2VersionContext",
    "calculate_multirow_connection",
    "canonical_multirow_execution_json",
    "multirow_execution_fingerprint",
    "physical_geometry_context",
    "resolve_multirow_end_distances",
)
