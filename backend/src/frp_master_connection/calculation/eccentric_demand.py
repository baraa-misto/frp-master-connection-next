"""Pure Slice 3 RC1 eccentric in-plane bolt-group demand analysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal, localcontext
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.calculation.multirow import (
    MethodProvenance,
    MultiRowDemandPlan,
    MultiRowMethodApplicability,
    PlanAvailability,
    QualificationDisposition,
    RowDistributionBasis,
)
from frp_master_connection.calculation.multirow_engine import MultiRowPhysicalGeometryContext
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_value,
)

SLICE_3_CALCULATION_CONTRACT_VERSION = "2.5A-RC1"
SLICE_3_DEMAND_ANALYSIS_ENGINE_VERSION = "0.1.0.dev1"
SLICE_3_DEMAND_ANALYSIS_RULE_SET_VERSION = "asce74-23-s2.9-eccentric-bolt-group-demand-rc1.dev1"
SLICE_3_DEMAND_RESULT_SCHEMA_VERSION = "0.1.0-draft"
SLICE_3_DEMAND_FINGERPRINT_SCHEMA_VERSION = "0.1.0-draft"

DEMAND_DECIMAL_PRECISION = 80
DEMAND_FRAME_TOLERANCE = Decimal("1E-12")
DEMAND_SHARE_TOLERANCE = Decimal("1E-12")
DEMAND_EQUILIBRIUM_RELATIVE_TOLERANCE = Decimal("1E-24")


class DemandAnalysisMethod(StrEnum):
    RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY = "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY"


class DemandAnalysisAvailability(StrEnum):
    CALCULATED = "CALCULATED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    CALCULATION_FAILED = "CALCULATION_FAILED"


class DemandAnalysisWarningCode(StrEnum):
    MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL = (
        "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL"
    )
    OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND = (
        "OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND"
    )
    PURE_CONNECTION_MOMENT_NOT_SUPPORTED = "PURE_CONNECTION_MOMENT_NOT_SUPPORTED"
    DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT = "DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT"
    RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED = "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED"
    DIRECT_DEMAND_PLAN_NOT_READY = "DIRECT_DEMAND_PLAN_NOT_READY"
    UNSUPPORTED_BOLT_GROUP_GEOMETRY = "UNSUPPORTED_BOLT_GROUP_GEOMETRY"
    FRICTION_TRANSFER_NOT_SUPPORTED = "FRICTION_TRANSFER_NOT_SUPPORTED"
    INVALID_DIRECT_DEMAND_SCENARIO = "INVALID_DIRECT_DEMAND_SCENARIO"
    EQUILIBRIUM_VERIFICATION_FAILED = "EQUILIBRIUM_VERIFICATION_FAILED"


class ResistanceHandoffDisposition(StrEnum):
    NOT_AUTHORIZED_IN_RC1 = "NOT_AUTHORIZED_IN_RC1"


@dataclass(frozen=True, slots=True)
class DemandAnalysisWarning:
    code: DemandAnalysisWarningCode
    trace: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, DemandAnalysisWarningCode):
            raise TypeError("code must be DemandAnalysisWarningCode.")
        _require_string_tuple(self.trace, "trace")


@dataclass(frozen=True, slots=True)
class Slice3VersionContext:
    calculation_contract_version: str = SLICE_3_CALCULATION_CONTRACT_VERSION
    demand_analysis_engine_version: str = SLICE_3_DEMAND_ANALYSIS_ENGINE_VERSION
    demand_analysis_rule_set_version: str = SLICE_3_DEMAND_ANALYSIS_RULE_SET_VERSION
    demand_result_schema_version: str = SLICE_3_DEMAND_RESULT_SCHEMA_VERSION
    demand_fingerprint_schema_version: str = SLICE_3_DEMAND_FINGERPRINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        expected = (
            SLICE_3_CALCULATION_CONTRACT_VERSION,
            SLICE_3_DEMAND_ANALYSIS_ENGINE_VERSION,
            SLICE_3_DEMAND_ANALYSIS_RULE_SET_VERSION,
            SLICE_3_DEMAND_RESULT_SCHEMA_VERSION,
            SLICE_3_DEMAND_FINGERPRINT_SCHEMA_VERSION,
        )
        if tuple(getattr(self, field.name) for field in fields(self)) != expected:
            raise ValueError("Slice 3 version context must use the approved RC1 identities.")


@dataclass(frozen=True, slots=True)
class ExactQuantityVector3D:
    x: PhysicalQuantity
    y: PhysicalQuantity
    z: PhysicalQuantity

    def __post_init__(self) -> None:
        if not all(isinstance(item, PhysicalQuantity) for item in (self.x, self.y, self.z)):
            raise TypeError("ExactQuantityVector3D components must be PhysicalQuantity values.")
        dimensions = {self.x.dimension, self.y.dimension, self.z.dimension}
        if len(dimensions) != 1:
            raise ValueError("ExactQuantityVector3D components must share one dimension.")


@dataclass(frozen=True, slots=True)
class ExactInterfaceFrame:
    interface_id: str
    origin: ExactQuantityVector3D
    u: tuple[Decimal, Decimal, Decimal]
    v: tuple[Decimal, Decimal, Decimal]
    n: tuple[Decimal, Decimal, Decimal]

    def __post_init__(self) -> None:
        _require_text(self.interface_id, "interface_id")
        if not isinstance(self.origin, ExactQuantityVector3D):
            raise TypeError("Interface-frame origin must be ExactQuantityVector3D.")
        if self.origin.x.dimension is not Dimension.LENGTH:
            raise ValueError("Interface-frame origin must contain length quantities.")
        for name in ("u", "v", "n"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or len(value) != 3:
                raise TypeError(f"{name} must be an immutable three-Decimal tuple.")
            object.__setattr__(self, name, tuple(decimal_value(item) for item in value))
        products = (
            _dot(self.u, self.u) - Decimal(1),
            _dot(self.v, self.v) - Decimal(1),
            _dot(self.n, self.n) - Decimal(1),
            _dot(self.u, self.v),
            _dot(self.u, self.n),
            _dot(self.v, self.n),
        )
        handedness = tuple(a - b for a, b in zip(_cross(self.u, self.v), self.n, strict=True))
        if any(abs(item) > DEMAND_FRAME_TOLERANCE for item in (*products, *handedness)):
            raise ValueError("Interface basis must be orthonormal and right-handed.")


@dataclass(frozen=True, slots=True)
class InPlaneQuantityVector:
    u: PhysicalQuantity
    v: PhysicalQuantity

    def __post_init__(self) -> None:
        if not isinstance(self.u, PhysicalQuantity) or not isinstance(self.v, PhysicalQuantity):
            raise TypeError("In-plane components must be PhysicalQuantity values.")
        if self.u.dimension is not self.v.dimension:
            raise ValueError("In-plane components must share one dimension.")


@dataclass(frozen=True, slots=True)
class ProjectedForce:
    u: PhysicalQuantity
    v: PhysicalQuantity
    n: PhysicalQuantity

    def __post_init__(self) -> None:
        if any(
            not isinstance(item, PhysicalQuantity) or item.dimension is not Dimension.FORCE
            for item in (self.u, self.v, self.n)
        ):
            raise ValueError("Projected force components must be force quantities.")


@dataclass(frozen=True, slots=True)
class DemandBoltGeometry:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    x: PhysicalQuantity
    y: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class PerBoltDemandResult:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    x: PhysicalQuantity
    y: PhysicalQuantity
    centered_x: PhysicalQuantity
    centered_y: PhysicalQuantity
    direct_share: Decimal
    direct_force: InPlaneQuantityVector
    moment_force: InPlaneQuantityVector
    total_force: InPlaneQuantityVector
    total_force_magnitude: PhysicalQuantity

    def __post_init__(self) -> None:
        object.__setattr__(self, "direct_share", decimal_value(self.direct_share))
        if self.direct_share < 0:
            raise ValueError("direct_share cannot be negative.")


@dataclass(frozen=True, slots=True)
class EquilibriumVerification:
    force_residual: InPlaneQuantityVector
    moment_residual: PhysicalQuantity
    force_tolerance: PhysicalQuantity
    moment_tolerance: PhysicalQuantity
    satisfied: bool

    def __post_init__(self) -> None:
        if not isinstance(self.satisfied, bool):
            raise TypeError("satisfied must be Boolean.")


@dataclass(frozen=True, slots=True)
class DemandScenarioResult:
    scenario_id: str
    controlling_row_id: str | None
    direct_basis: RowDistributionBasis
    direct_provenance: MethodProvenance
    method: DemandAnalysisMethod
    external_moment: PhysicalQuantity
    direct_distribution_moment: PhysicalQuantity
    residual_moment: PhysicalQuantity
    per_bolt: tuple[PerBoltDemandResult, ...]
    equilibrium: EquilibriumVerification | None
    availability: DemandAnalysisAvailability
    warnings: tuple[DemandAnalysisWarning, ...]


@dataclass(frozen=True, slots=True)
class EccentricDemandInput:
    action_source_id: str
    member_component_id: str
    global_force: ExactQuantityVector3D
    member_end_moments: ExactQuantityVector3D
    independent_connection_moments: ExactQuantityVector3D
    force_reference_point: ExactQuantityVector3D
    interface_frame: ExactInterfaceFrame
    physical_geometry: MultiRowPhysicalGeometryContext
    direct_demand_plan: MultiRowDemandPlan
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    source_trace: tuple[str, ...]
    versions: Slice3VersionContext = Slice3VersionContext()

    def __post_init__(self) -> None:
        for name in ("action_source_id", "member_component_id"):
            _require_text(cast(str, getattr(self, name)), name)
        for name in (
            "global_force",
            "member_end_moments",
            "independent_connection_moments",
            "force_reference_point",
        ):
            if not isinstance(getattr(self, name), ExactQuantityVector3D):
                raise TypeError(f"{name} must be ExactQuantityVector3D.")
        if not isinstance(self.interface_frame, ExactInterfaceFrame):
            raise TypeError("interface_frame must be ExactInterfaceFrame.")
        if self.global_force.x.dimension is not Dimension.FORCE:
            raise ValueError("global_force must contain force quantities.")
        if any(
            item.x.dimension is not Dimension.MOMENT
            for item in (self.member_end_moments, self.independent_connection_moments)
        ):
            raise ValueError("Moment vectors must contain moment quantities.")
        if self.force_reference_point.x.dimension is not Dimension.LENGTH:
            raise ValueError("force_reference_point must contain length quantities.")
        if not isinstance(self.physical_geometry, MultiRowPhysicalGeometryContext):
            raise TypeError("physical_geometry must be MultiRowPhysicalGeometryContext.")
        if self.interface_frame.interface_id != self.physical_geometry.interface_id:
            raise ValueError("Interface frame and physical geometry identities must match.")
        if not isinstance(self.direct_demand_plan, MultiRowDemandPlan):
            raise TypeError("direct_demand_plan must be MultiRowDemandPlan.")
        if not isinstance(self.method_applicability, MultiRowMethodApplicability):
            raise TypeError("method_applicability must be MultiRowMethodApplicability.")
        if not isinstance(self.qualification, QualificationDisposition):
            raise TypeError("qualification must be QualificationDisposition.")
        _require_string_tuple(self.source_trace, "source_trace")
        if not isinstance(self.versions, Slice3VersionContext):
            raise TypeError("versions must be Slice3VersionContext.")


@dataclass(frozen=True, slots=True)
class EccentricDemandFingerprintEnvelope:
    calculation_input: EccentricDemandInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    preview_timing: object | None = None
    request_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class EccentricDemandResult:
    action_source_id: str
    member_component_id: str
    original_global_force: ExactQuantityVector3D
    original_member_end_moments: ExactQuantityVector3D
    original_independent_connection_moments: ExactQuantityVector3D
    force_reference_point: ExactQuantityVector3D
    interface_frame: ExactInterfaceFrame
    projected_force: ProjectedForce
    bolts: tuple[DemandBoltGeometry, ...]
    geometric_bolt_centroid: InPlaneQuantityVector
    polar_coordinate_sum: PhysicalQuantity
    scenarios: tuple[DemandScenarioResult, ...]
    availability: DemandAnalysisAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    warnings: tuple[DemandAnalysisWarning, ...]
    source_trace: tuple[str, ...]
    versions: Slice3VersionContext
    input_fingerprint: str
    result_fingerprint: str
    resistance_handoff: ResistanceHandoffDisposition = (
        ResistanceHandoffDisposition.NOT_AUTHORIZED_IN_RC1
    )


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text.")


def _require_string_tuple(value: tuple[str, ...], name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, str) or not item for item in value):
        raise TypeError(f"{name} must be an immutable tuple of nonempty strings.")


def _dot(left: tuple[Decimal, ...], right: tuple[Decimal, ...]) -> Decimal:
    with localcontext() as context:
        context.prec = DEMAND_DECIMAL_PRECISION
        return sum((a * b for a, b in zip(left, right, strict=True)), Decimal(0))


def _cross(
    left: tuple[Decimal, Decimal, Decimal], right: tuple[Decimal, Decimal, Decimal]
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _canonical_components(vector: ExactQuantityVector3D) -> tuple[Decimal, Decimal, Decimal]:
    return (
        vector.x.canonical_magnitude,
        vector.y.canonical_magnitude,
        vector.z.canonical_magnitude,
    )


def _project_force(value: EccentricDemandInput) -> ProjectedForce:
    force = _canonical_components(value.global_force)
    return ProjectedForce(
        PhysicalQuantity.of(_dot(force, value.interface_frame.u), Unit.N),
        PhysicalQuantity.of(_dot(force, value.interface_frame.v), Unit.N),
        PhysicalQuantity.of(_dot(force, value.interface_frame.n), Unit.N),
    )


def _project_reference(value: EccentricDemandInput) -> tuple[Decimal, Decimal]:
    point = _canonical_components(value.force_reference_point)
    origin = _canonical_components(value.interface_frame.origin)
    relative = tuple(a - b for a, b in zip(point, origin, strict=True))
    return _dot(relative, value.interface_frame.u), _dot(relative, value.interface_frame.v)


def _resolved_bolts(
    geometry: MultiRowPhysicalGeometryContext,
) -> tuple[DemandBoltGeometry, ...]:
    row_by_bolt = {bolt_id: row.id for row in geometry.rows for bolt_id in row.bolt_ids}
    line_by_bolt = {bolt_id: line.id for line in geometry.bolt_lines for bolt_id in line.bolt_ids}
    return tuple(
        DemandBoltGeometry(
            bolt.bolt_id,
            row_by_bolt.get(bolt.bolt_id, "UNRESOLVED"),
            line_by_bolt.get(bolt.bolt_id, "UNRESOLVED"),
            PhysicalQuantity.of(bolt.x, geometry.source_length_unit).to_canonical(),
            PhysicalQuantity.of(bolt.y, geometry.source_length_unit).to_canonical(),
        )
        for bolt in sorted(geometry.bolts, key=lambda item: item.bolt_id)
    )


def _supported_geometry(geometry: MultiRowPhysicalGeometryContext) -> bool:
    bolt_ids = {item.bolt_id for item in geometry.bolts}
    row_members = tuple(item for row in geometry.rows for item in row.bolt_ids)
    line_members = tuple(item for line in geometry.bolt_lines for item in line.bolt_ids)
    bolts_per_row = {len(row.bolt_ids) for row in geometry.rows}
    bolts_per_line = {len(line.bolt_ids) for line in geometry.bolt_lines}
    first = geometry.bolts[0]
    identical = all(
        (item.bolt_diameter, item.hole_diameter, item.bolt_identity)
        == (first.bolt_diameter, first.hole_diameter, first.bolt_identity)
        for item in geometry.bolts
    )
    row_set_matches = set(row_members) == bolt_ids
    line_set_matches = set(line_members) == bolt_ids
    rows_unique = len(row_members) == len(bolt_ids)
    lines_unique = len(line_members) == len(bolt_ids)
    uniform_rows = bolts_per_row == {len(geometry.bolt_lines)}
    uniform_lines = bolts_per_line == {len(geometry.rows)}
    complete_grid = len(geometry.rows) * len(geometry.bolt_lines) == len(bolt_ids)
    rows_unstaggered = all(
        item.raw_deviation <= geometry.sorting_tolerance for item in geometry.rows
    )
    lines_unstaggered = all(
        item.raw_deviation <= geometry.sorting_tolerance for item in geometry.bolt_lines
    )
    return (
        row_set_matches
        and line_set_matches
        and rows_unique
        and lines_unique
        and uniform_rows
        and uniform_lines
        and complete_grid
        and rows_unstaggered
        and lines_unstaggered
        and identical
    )


def _centroid_and_polar(
    bolts: tuple[DemandBoltGeometry, ...],
) -> tuple[InPlaneQuantityVector, PhysicalQuantity]:
    with localcontext() as context:
        context.prec = DEMAND_DECIMAL_PRECISION
        count = Decimal(len(bolts))
        x = sum((item.x.canonical_magnitude for item in bolts), Decimal(0)) / count
        y = sum((item.y.canonical_magnitude for item in bolts), Decimal(0)) / count
        polar = sum(
            (
                (item.x.canonical_magnitude - x) ** 2 + (item.y.canonical_magnitude - y) ** 2
                for item in bolts
            ),
            Decimal(0),
        )
    return (
        InPlaneQuantityVector(PhysicalQuantity.of(x, Unit.MM), PhysicalQuantity.of(y, Unit.MM)),
        PhysicalQuantity.of(polar, Unit.MM2),
    )


def _moment_present(vector: ExactQuantityVector3D) -> bool:
    return any(item != 0 for item in _canonical_components(vector))


def _warning(code: DemandAnalysisWarningCode, *trace: str) -> DemandAnalysisWarning:
    return DemandAnalysisWarning(code, trace)


def _base_warnings(
    value: EccentricDemandInput, projected: ProjectedForce
) -> tuple[DemandAnalysisWarning, ...]:
    warnings: list[DemandAnalysisWarning] = []
    member_moment_present = _moment_present(value.member_end_moments)
    connection_moment_present = _moment_present(value.independent_connection_moments)
    if member_moment_present or connection_moment_present:
        trace = tuple(
            item
            for present, item in (
                (member_moment_present, "member_end_moments:trace_only"),
                (connection_moment_present, "independent_connection_moments:trace_only"),
            )
            if present
        )
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL,
                *trace,
            )
        )
    if projected.n.canonical_magnitude != 0:
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND,
                "bolt_axis_tension:not_generated",
                "prying:not_generated",
            )
        )
    return tuple(warnings)


def _direct_shares(
    value: EccentricDemandInput, scenario_index: int
) -> tuple[dict[str, Decimal] | None, DemandAnalysisWarning | None]:
    scenario = value.direct_demand_plan.scenarios[scenario_index]
    shares = {item.bolt_id: Decimal(0) for item in value.physical_geometry.bolts}
    assigned: set[str] = set()
    physical_rows = {
        bolt_id: row.id for row in value.physical_geometry.rows for bolt_id in row.bolt_ids
    }
    total = value.direct_demand_plan.total_in_plane_demand.canonical_magnitude
    for row in scenario.rows:
        for item in row.per_bolt_demands:
            if (
                item.bolt_id not in shares
                or item.bolt_id in assigned
                or physical_rows.get(item.bolt_id) != row.row_id
            ):
                return None, _warning(
                    DemandAnalysisWarningCode.INVALID_DIRECT_DEMAND_SCENARIO,
                    f"scenario:{scenario.id}",
                    f"bolt:{item.bolt_id}",
                )
            if total != 0:
                share = item.demand.canonical_magnitude / total
            elif row.row_fraction is not None and row.per_bolt_demands:
                share = row.row_fraction / Decimal(len(row.per_bolt_demands))
            else:
                return None, _warning(
                    DemandAnalysisWarningCode.INVALID_DIRECT_DEMAND_SCENARIO,
                    f"scenario:{scenario.id}",
                    "zero_total_without_explicit_fraction",
                )
            if share < 0:
                return None, _warning(
                    DemandAnalysisWarningCode.INVALID_DIRECT_DEMAND_SCENARIO,
                    f"scenario:{scenario.id}",
                    "negative_direct_share",
                )
            assigned.add(item.bolt_id)
            shares[item.bolt_id] = share
    if abs(sum(shares.values(), Decimal(0)) - Decimal(1)) > DEMAND_SHARE_TOLERANCE:
        return None, _warning(
            DemandAnalysisWarningCode.INVALID_DIRECT_DEMAND_SCENARIO,
            f"scenario:{scenario.id}",
            "direct_shares_do_not_sum_to_one",
        )
    return shares, None


def verify_eccentric_demand_equilibrium(
    projected_force: ProjectedForce,
    external_moment: PhysicalQuantity,
    centroid: InPlaneQuantityVector,
    per_bolt: tuple[PerBoltDemandResult, ...],
) -> EquilibriumVerification:
    """Verify both force and centroidal moment equilibrium without repairing residuals."""

    if external_moment.dimension is not Dimension.MOMENT:
        raise ValueError("external_moment must be a moment quantity.")
    with localcontext() as context:
        context.prec = DEMAND_DECIMAL_PRECISION
        sum_u = sum((item.total_force.u.canonical_magnitude for item in per_bolt), Decimal(0))
        sum_v = sum((item.total_force.v.canonical_magnitude for item in per_bolt), Decimal(0))
        residual_u = sum_u - projected_force.u.canonical_magnitude
        residual_v = sum_v - projected_force.v.canonical_magnitude
        summed_moment = sum(
            (
                (item.x.canonical_magnitude - centroid.u.canonical_magnitude)
                * item.total_force.v.canonical_magnitude
                - (item.y.canonical_magnitude - centroid.v.canonical_magnitude)
                * item.total_force.u.canonical_magnitude
                for item in per_bolt
            ),
            Decimal(0),
        )
        moment_residual = summed_moment - external_moment.canonical_magnitude
        force_scale = max(
            abs(projected_force.u.canonical_magnitude),
            abs(projected_force.v.canonical_magnitude),
            Decimal(1),
        )
        radius = max(
            (
                max(
                    abs(item.x.canonical_magnitude - centroid.u.canonical_magnitude),
                    abs(item.y.canonical_magnitude - centroid.v.canonical_magnitude),
                )
                for item in per_bolt
            ),
            default=Decimal(1),
        )
        force_tolerance = force_scale * DEMAND_EQUILIBRIUM_RELATIVE_TOLERANCE
        moment_tolerance = (
            max(abs(external_moment.canonical_magnitude), force_scale * radius, Decimal(1))
            * DEMAND_EQUILIBRIUM_RELATIVE_TOLERANCE
        )
    satisfied = (
        abs(residual_u) <= force_tolerance
        and abs(residual_v) <= force_tolerance
        and abs(moment_residual) <= moment_tolerance
    )
    return EquilibriumVerification(
        InPlaneQuantityVector(
            PhysicalQuantity.of(residual_u, Unit.N), PhysicalQuantity.of(residual_v, Unit.N)
        ),
        PhysicalQuantity.of(moment_residual, Unit.N_MM),
        PhysicalQuantity.of(force_tolerance, Unit.N),
        PhysicalQuantity.of(moment_tolerance, Unit.N_MM),
        satisfied,
    )


def _calculate_scenario(
    value: EccentricDemandInput,
    scenario_index: int,
    projected: ProjectedForce,
    reference: tuple[Decimal, Decimal],
    bolts: tuple[DemandBoltGeometry, ...],
    centroid: InPlaneQuantityVector,
    polar: PhysicalQuantity,
) -> DemandScenarioResult:
    scenario = value.direct_demand_plan.scenarios[scenario_index]
    shares, invalid = _direct_shares(value, scenario_index)
    if shares is None:
        return DemandScenarioResult(
            scenario.id,
            scenario.controlling_row_id,
            value.direct_demand_plan.basis,
            value.direct_demand_plan.provenance,
            DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY,
            PhysicalQuantity.of(0, Unit.N_MM),
            PhysicalQuantity.of(0, Unit.N_MM),
            PhysicalQuantity.of(0, Unit.N_MM),
            (),
            None,
            DemandAnalysisAvailability.CALCULATION_FAILED,
            (cast(DemandAnalysisWarning, invalid),),
        )
    fu = projected.u.canonical_magnitude
    fv = projected.v.canonical_magnitude
    cx = centroid.u.canonical_magnitude
    cy = centroid.v.canonical_magnitude
    with localcontext() as context:
        context.prec = DEMAND_DECIMAL_PRECISION
        external = (reference[0] - cx) * fv - (reference[1] - cy) * fu
        direct_vectors = tuple(
            (shares[item.bolt_id] * fu, shares[item.bolt_id] * fv) for item in bolts
        )
        direct_moment = sum(
            (
                (item.x.canonical_magnitude - cx) * direct[1]
                - (item.y.canonical_magnitude - cy) * direct[0]
                for item, direct in zip(bolts, direct_vectors, strict=True)
            ),
            Decimal(0),
        )
        residual = external - direct_moment
    if residual != 0 and polar.canonical_magnitude <= 0:
        warning = _warning(
            DemandAnalysisWarningCode.DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT,
            f"scenario:{scenario.id}",
            "polar_coordinate_sum:nonpositive",
        )
        return DemandScenarioResult(
            scenario.id,
            scenario.controlling_row_id,
            value.direct_demand_plan.basis,
            value.direct_demand_plan.provenance,
            DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY,
            PhysicalQuantity.of(external, Unit.N_MM),
            PhysicalQuantity.of(direct_moment, Unit.N_MM),
            PhysicalQuantity.of(residual, Unit.N_MM),
            (),
            None,
            DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED,
            (warning,),
        )
    per_bolt: list[PerBoltDemandResult] = []
    with localcontext() as context:
        context.prec = DEMAND_DECIMAL_PRECISION
        ratio = Decimal(0) if residual == 0 else residual / polar.canonical_magnitude
        for item, direct in zip(bolts, direct_vectors, strict=True):
            centered_x = item.x.canonical_magnitude - cx
            centered_y = item.y.canonical_magnitude - cy
            moment_u = -ratio * centered_y
            moment_v = ratio * centered_x
            total_u = direct[0] + moment_u
            total_v = direct[1] + moment_v
            magnitude = (total_u**2 + total_v**2).sqrt()
            per_bolt.append(
                PerBoltDemandResult(
                    item.bolt_id,
                    item.row_id,
                    item.bolt_line_id,
                    item.x,
                    item.y,
                    PhysicalQuantity.of(centered_x, Unit.MM),
                    PhysicalQuantity.of(centered_y, Unit.MM),
                    shares[item.bolt_id],
                    InPlaneQuantityVector(
                        PhysicalQuantity.of(direct[0], Unit.N),
                        PhysicalQuantity.of(direct[1], Unit.N),
                    ),
                    InPlaneQuantityVector(
                        PhysicalQuantity.of(moment_u, Unit.N),
                        PhysicalQuantity.of(moment_v, Unit.N),
                    ),
                    InPlaneQuantityVector(
                        PhysicalQuantity.of(total_u, Unit.N),
                        PhysicalQuantity.of(total_v, Unit.N),
                    ),
                    PhysicalQuantity.of(magnitude, Unit.N),
                )
            )
    equilibrium = verify_eccentric_demand_equilibrium(
        projected,
        PhysicalQuantity.of(external, Unit.N_MM),
        centroid,
        tuple(per_bolt),
    )
    warning = _warning(
        DemandAnalysisWarningCode.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED,
        "source:project_rational_extension",
        "equal_bolt_stiffness:true",
    )
    warnings: tuple[DemandAnalysisWarning, ...] = (warning,)
    availability = DemandAnalysisAvailability.CALCULATED
    if not equilibrium.satisfied:
        warnings += (
            _warning(
                DemandAnalysisWarningCode.EQUILIBRIUM_VERIFICATION_FAILED,
                f"scenario:{scenario.id}",
                f"force_residual_u:{equilibrium.force_residual.u.canonical_string}",
                f"force_residual_v:{equilibrium.force_residual.v.canonical_string}",
                f"moment_residual:{equilibrium.moment_residual.canonical_string}",
            ),
        )
        availability = DemandAnalysisAvailability.CALCULATION_FAILED
    return DemandScenarioResult(
        scenario.id,
        scenario.controlling_row_id,
        value.direct_demand_plan.basis,
        value.direct_demand_plan.provenance,
        DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY,
        PhysicalQuantity.of(external, Unit.N_MM),
        PhysicalQuantity.of(direct_moment, Unit.N_MM),
        PhysicalQuantity.of(residual, Unit.N_MM),
        tuple(per_bolt),
        equilibrium,
        availability,
        warnings,
    )


def _physical_geometry_payload(value: MultiRowPhysicalGeometryContext) -> object:
    unit = value.source_length_unit
    return {
        "group_id": value.group_id,
        "interface_id": value.interface_id,
        "bolts": [
            {
                "bolt_id": item.bolt_id,
                "x": PhysicalQuantity.of(item.x, unit).canonical_string,
                "y": PhysicalQuantity.of(item.y, unit).canonical_string,
                "bolt_diameter": PhysicalQuantity.of(item.bolt_diameter, unit).canonical_string,
                "hole_diameter": PhysicalQuantity.of(item.hole_diameter, unit).canonical_string,
                "bolt_identity": item.bolt_identity,
                "logical_connection_id": item.logical_connection_id,
            }
            for item in sorted(value.bolts, key=lambda bolt: bolt.bolt_id)
        ],
        "rows": [
            {"id": item.id, "bolt_ids": sorted(item.bolt_ids)}
            for item in sorted(value.rows, key=lambda row: row.id)
        ],
        "bolt_lines": [
            {"id": item.id, "bolt_ids": sorted(item.bolt_ids)}
            for item in sorted(value.bolt_lines, key=lambda line: line.id)
        ],
    }


def _canonicalize(value: object) -> object:
    if value is None:
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, bool)):
        return value
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "unit": value.canonical_unit.value,
            "value": value.canonical_string,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise TypeError("Demand fingerprints reject authoritative binary floats.")
    if isinstance(value, MultiRowPhysicalGeometryContext):
        return _physical_geometry_payload(value)
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"Unsupported demand fingerprint value type: {type(value).__name__}.")


def canonical_eccentric_demand_input_json(
    value: EccentricDemandInput | EccentricDemandFingerprintEnvelope,
) -> str:
    """Serialize only calculation-authority fields in canonical physical units."""

    calculation_input = (
        value.calculation_input if isinstance(value, EccentricDemandFingerprintEnvelope) else value
    )
    if not isinstance(calculation_input, EccentricDemandInput):
        raise TypeError("Demand fingerprinting requires an input or presentation envelope.")
    return json.dumps(
        _canonicalize(calculation_input), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )


def eccentric_demand_input_fingerprint(
    value: EccentricDemandInput | EccentricDemandFingerprintEnvelope,
) -> str:
    return hashlib.sha256(canonical_eccentric_demand_input_json(value).encode("utf-8")).hexdigest()


def _aggregate_availability(
    scenarios: tuple[DemandScenarioResult, ...],
) -> DemandAnalysisAvailability:
    if any(
        item.availability is DemandAnalysisAvailability.CALCULATION_FAILED for item in scenarios
    ):
        return DemandAnalysisAvailability.CALCULATION_FAILED
    if not scenarios or any(
        item.availability is DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED
        for item in scenarios
    ):
        return DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED
    return DemandAnalysisAvailability.CALCULATED


def _unique_warnings(
    warnings: tuple[DemandAnalysisWarning, ...],
) -> tuple[DemandAnalysisWarning, ...]:
    return tuple(dict.fromkeys(warnings))


def calculate_eccentric_bolt_group_demand(value: EccentricDemandInput) -> EccentricDemandResult:
    """Resolve every accepted direct scenario into an equilibrated force-only demand result."""

    if not isinstance(value, EccentricDemandInput):
        raise TypeError("value must be EccentricDemandInput.")
    input_fingerprint = eccentric_demand_input_fingerprint(value)
    projected = _project_force(value)
    reference = _project_reference(value)
    bolts = _resolved_bolts(value.physical_geometry)
    centroid, polar = _centroid_and_polar(bolts)
    warnings = list(_base_warnings(value, projected))
    in_plane_zero = projected.u.canonical_magnitude == projected.v.canonical_magnitude == 0
    any_independent_moment = _moment_present(value.member_end_moments) or _moment_present(
        value.independent_connection_moments
    )
    scenarios: tuple[DemandScenarioResult, ...] = ()
    if in_plane_zero and any_independent_moment:
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.PURE_CONNECTION_MOMENT_NOT_SUPPORTED,
                "member_and_connection_moments:trace_only",
            )
        )
    elif value.direct_demand_plan.availability is not PlanAvailability.READY:
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.DIRECT_DEMAND_PLAN_NOT_READY,
                f"availability:{value.direct_demand_plan.availability.value}",
            )
        )
    elif value.direct_demand_plan.friction_credit:
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.FRICTION_TRANSFER_NOT_SUPPORTED,
                "friction_credit:true",
            )
        )
    elif not _supported_geometry(value.physical_geometry):
        warnings.append(
            _warning(
                DemandAnalysisWarningCode.UNSUPPORTED_BOLT_GROUP_GEOMETRY,
                "required:planar_rectangular_nonstaggered_identical_bolts",
            )
        )
    else:
        scenarios = tuple(
            _calculate_scenario(value, index, projected, reference, bolts, centroid, polar)
            for index in range(len(value.direct_demand_plan.scenarios))
        )
        warnings.extend(item for scenario in scenarios for item in scenario.warnings)
    availability = _aggregate_availability(scenarios)
    result_payload = (
        value.action_source_id,
        value.member_component_id,
        value.global_force,
        value.member_end_moments,
        value.independent_connection_moments,
        value.force_reference_point,
        value.interface_frame,
        projected,
        bolts,
        centroid,
        polar,
        scenarios,
        availability,
        value.method_applicability,
        value.qualification,
        _unique_warnings(tuple(warnings)),
        value.source_trace,
        value.versions,
        input_fingerprint,
        ResistanceHandoffDisposition.NOT_AUTHORIZED_IN_RC1,
    )
    result_fingerprint = hashlib.sha256(
        json.dumps(
            _canonicalize(result_payload),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return EccentricDemandResult(
        value.action_source_id,
        value.member_component_id,
        value.global_force,
        value.member_end_moments,
        value.independent_connection_moments,
        value.force_reference_point,
        value.interface_frame,
        projected,
        bolts,
        centroid,
        polar,
        scenarios,
        availability,
        value.method_applicability,
        value.qualification,
        _unique_warnings(tuple(warnings)),
        value.source_trace,
        value.versions,
        input_fingerprint,
        result_fingerprint,
    )


__all__ = (
    "DEMAND_DECIMAL_PRECISION",
    "DEMAND_EQUILIBRIUM_RELATIVE_TOLERANCE",
    "DEMAND_FRAME_TOLERANCE",
    "DEMAND_SHARE_TOLERANCE",
    "SLICE_3_CALCULATION_CONTRACT_VERSION",
    "SLICE_3_DEMAND_ANALYSIS_ENGINE_VERSION",
    "SLICE_3_DEMAND_ANALYSIS_RULE_SET_VERSION",
    "SLICE_3_DEMAND_FINGERPRINT_SCHEMA_VERSION",
    "SLICE_3_DEMAND_RESULT_SCHEMA_VERSION",
    "DemandAnalysisAvailability",
    "DemandAnalysisMethod",
    "DemandAnalysisWarning",
    "DemandAnalysisWarningCode",
    "DemandBoltGeometry",
    "DemandScenarioResult",
    "EccentricDemandFingerprintEnvelope",
    "EccentricDemandInput",
    "EccentricDemandResult",
    "EquilibriumVerification",
    "ExactInterfaceFrame",
    "ExactQuantityVector3D",
    "InPlaneQuantityVector",
    "PerBoltDemandResult",
    "ProjectedForce",
    "ResistanceHandoffDisposition",
    "Slice3VersionContext",
    "calculate_eccentric_bolt_group_demand",
    "canonical_eccentric_demand_input_json",
    "eccentric_demand_input_fingerprint",
    "verify_eccentric_demand_equilibrium",
)
