"""Framework-independent automatic/explicit multi-row orchestration."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.actions import (
    ResolvedManualMemberEndAction,
    resolve_manual_member_end_action,
)
from frp_master_connection.calculation import (
    DEMAND_FRAME_TOLERANCE,
    BlockPathPlanStatus,
    BlockShearAreaPlan,
    BlockShearCompatibilityEvidence,
    BlockShearCompatibilityStatus,
    BlockShearEccentricityClassification,
    BlockShearEccentricityContext,
    BlockShearPlanSet,
    BoltHoleSource,
    ConnectedMaterialPair,
    DeferredExecutionStatus,
    DemandAnalysisAvailability,
    DemandScenarioResult,
    EccentricDemandInput,
    EccentricDemandResult,
    EccentricGroupModeCompatibilityInput,
    EccentricGroupModeCompatibilityResult,
    EccentricResistanceHandoffInput,
    EccentricResistanceHandoffResult,
    EndUseFactors,
    EngineerRowForce,
    EngineerRowFraction,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
    ExplicitBoltAxisDemand,
    FirstRowNetTensionPlan,
    FirstRowPlanMethod,
    FRPPropertyKind,
    GeometryStatus,
    InterrowShearOutPlan,
    LapConfiguration,
    LayerBearingAxisContext,
    LayerInPlaneDemandAllocation,
    MaterialDirection,
    MaterialPropertySnapshot,
    MethodProvenance,
    MultiRowApplicability,
    MultiRowBoltExecutionContext,
    MultiRowBoltLineExecutionContext,
    MultiRowCalculationPlanSet,
    MultiRowCalculationResult,
    MultiRowCheckFamily,
    MultiRowDemandPlan,
    MultiRowEndDistanceContext,
    MultiRowEquationMethod,
    MultiRowExecutableCheck,
    MultiRowExecutionBundle,
    MultiRowFactorContext,
    MultiRowFingerprintMetadataEntry,
    MultiRowLayerExecutionContext,
    MultiRowMethodApplicability,
    MultiRowOverallDisposition,
    MultiRowRequiredCheckContract,
    MultiRowSignedDemandContext,
    NumericalComparison,
    PhysicalQuantity,
    PitchFactorSource,
    PitchFactorTrace,
    PlanAvailability,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    QualificationDisposition,
    RowDistributionBasis,
    Slice2VersionContext,
    StandardHoleDefinition,
    ThreadStatus,
    ThreadStatusAssignment,
    TimeEffectCategory,
    Unit,
    assess_multirow_applicability,
    build_block_shear_area_plans,
    build_first_row_net_tension_plans,
    build_interrow_shear_out_plans,
    calculate_eccentric_bolt_group_demand,
    calculate_eccentric_group_mode_compatibility,
    calculate_eccentric_resistance_handoff,
    calculate_multirow_connection,
    canonical_decimal_string,
    classify_block_shear_eccentricity,
    constant_pitch_factor,
    create_lap_factor_plan,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_standard_hole,
    decimal_from_finite_real,
    decimal_value,
    physical_geometry_context,
    plan_row_demands,
    resolve_first_row_geometry,
    resolve_multirow_end_distances,
    select_time_effect_factor,
)
from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    ReferencePointKind,
)
from frp_master_connection.geometry import (
    CartesianFrame3D,
    GeneralBolt,
    GeneralBoltGroup,
    MultiRowGeometry,
    MultiRowGeometryTolerance,
    PlanarLayerBoundary,
    PlanarPoint2D,
    UnitVector3D,
    resolve_block_shear_paths,
    resolve_multirow_geometry,
)

from .calculation_orchestration import (
    ColumnFlangeConnectionSide,
    SingleBoltOrchestrationRequest,
)
from .connection_preview import PreviewGeometryStatus, preview_single_bolt_connection
from .visualization import (
    BoltDisplaySnapshot,
    ConnectionViewExtents,
    HoleDisplaySnapshot,
    SingleBoltVisualizationSnapshot,
    WasherDisplaySnapshot,
)

MULTIROW_ORCHESTRATION_CONTRACT_VERSION = "2.5C-RC1"
MULTIROW_PREVIEW_SCHEMA_VERSION = "0.2.0-draft"
MULTIROW_VISUALIZATION_SCHEMA_VERSION = "0.2.0-draft"
AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION = "2.6B-RC1"
AUTOMATIC_GROUP_MODE_TRACE_LAYERS = (
    "DEMAND_ANALYSIS",
    "RESISTANCE_HANDOFF",
    "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
    "RESISTANCE_CALCULATION",
    "APPLICATION_INTEGRATION",
)
_DECIMAL_PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286"
)
# Direction coordinates retain twice the accepted frame-resolution digits.  This is a
# deterministic representation precision, not a physical coincidence or residual tolerance.
_CANONICAL_DIRECTION_QUANTUM = DEMAND_FRAME_TOLERANCE * DEMAND_FRAME_TOLERANCE


class MultiRowDemandSource(StrEnum):
    AUTOMATIC_MEMBER_END_FORCE = "AUTOMATIC_MEMBER_END_FORCE"
    EXPLICIT_RESOLVED_CONNECTION_DEMAND = "EXPLICIT_RESOLVED_CONNECTION_DEMAND"


class EngineerDistributionKind(StrEnum):
    FRACTIONS = "FRACTIONS"
    DIRECT_ROW_FORCES = "DIRECT_ROW_FORCES"


@dataclass(frozen=True, slots=True)
class MultiRowLayerInput:
    layer_id: str
    component_id: str
    material_id: str
    thickness: PhysicalQuantity
    element_classification: PultrudedElementClassification
    material_axis_angle_degrees: Decimal
    end_use_factors: EndUseFactors
    bearing_thread_status: ThreadStatus

    def __post_init__(self) -> None:
        for value in (self.layer_id, self.component_id, self.material_id):
            if not value.strip():
                raise ValueError("Layer identities must be nonempty.")
        if self.thickness.magnitude <= 0:
            raise ValueError("Layer thickness must be positive.")
        angle = decimal_value(self.material_axis_angle_degrees)
        if angle < 0 or angle >= 180:
            raise ValueError("Material-axis angle must be at least 0 and less than 180 degrees.")
        object.__setattr__(self, "material_axis_angle_degrees", angle)


@dataclass(frozen=True, slots=True)
class EngineerRowAllocationInput:
    row_ordinal: int
    fraction: Decimal | None = None
    direct_force: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        if isinstance(self.row_ordinal, bool) or self.row_ordinal < 1:
            raise ValueError("row_ordinal must be a positive non-Boolean integer.")
        if (self.fraction is None) == (self.direct_force is None):
            raise ValueError("Each row allocation requires exactly one fraction or direct force.")
        if self.fraction is not None:
            value = decimal_value(self.fraction)
            if value < 0:
                raise ValueError("Row fractions cannot be negative.")
            object.__setattr__(self, "fraction", value)
        if self.direct_force is not None and self.direct_force.magnitude < 0:
            raise ValueError("Direct row forces cannot be negative.")


@dataclass(frozen=True, slots=True)
class BoltAxisTensionInput:
    bolt_id: str
    demand: PhysicalQuantity

    def __post_init__(self) -> None:
        if not self.bolt_id.strip() or self.demand.magnitude < 0:
            raise ValueError("Bolt-axis tension requires an identity and nonnegative demand.")


@dataclass(frozen=True, slots=True)
class MultiRowOrchestrationRequest:
    request_id: str
    connection_id: str
    interface_id: str
    load_combination_id: str
    source_reference: str
    display_unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    row_count: int
    bolts_per_row: int
    bolt_diameter: PhysicalQuantity
    hole_basis: PublishedCodeUnitBasis
    pitch: PhysicalQuantity
    gauge: PhysicalQuantity
    unloaded_end_e1: PhysicalQuantity
    loaded_boundary_to_row_1_distance: PhysicalQuantity
    negative_side_distance: PhysicalQuantity
    positive_side_distance: PhysicalQuantity
    geometry_tolerance: PhysicalQuantity
    material_pair: ConnectedMaterialPair
    layers: tuple[MultiRowLayerInput, ...]
    signed_force_x: PhysicalQuantity | None
    signed_force_y: PhysicalQuantity | None
    force_reference: str | None
    row_distribution_basis: RowDistributionBasis
    engineer_distribution_kind: EngineerDistributionKind | None
    engineer_allocations: tuple[EngineerRowAllocationInput, ...]
    provenance: MethodProvenance
    bolt_axis_tension_required: bool
    bolt_axis_tensions: tuple[BoltAxisTensionInput, ...]
    time_effect_category: TimeEffectCategory
    lap_configuration: LapConfiguration
    first_row_method: FirstRowPlanMethod
    prescribed_lbr: Decimal | None
    force_line_offset: PhysicalQuantity
    eccentricity_tolerance: PhysicalQuantity
    orchestration_contract_version: str = MULTIROW_ORCHESTRATION_CONTRACT_VERSION
    physical_connection_request: SingleBoltOrchestrationRequest | None = None
    connection_view_extents: ConnectionViewExtents | None = None
    demand_source: MultiRowDemandSource = MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND
    automatic_action_source_id: str | None = None
    single_row_geometry_preview_authorized: bool = False

    def __post_init__(self) -> None:
        identities = (
            self.request_id,
            self.connection_id,
            self.interface_id,
            self.load_combination_id,
            self.source_reference,
        )
        if any(not value.strip() for value in identities):
            raise ValueError("Request identities and source/reference metadata must be nonempty.")
        if self.orchestration_contract_version != MULTIROW_ORCHESTRATION_CONTRACT_VERSION:
            raise ValueError("Unsupported multi-row orchestration contract version.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        for name in ("row_count", "bolts_per_row"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive non-Boolean integer.")
        if not isinstance(self.single_row_geometry_preview_authorized, bool):
            raise TypeError("single_row_geometry_preview_authorized must be Boolean.")
        if self.row_count < 2 and not self.single_row_geometry_preview_authorized:
            raise ValueError("The public multi-row workflow requires at least two rows.")
        positive_lengths = (
            self.bolt_diameter,
            self.pitch,
            self.gauge,
            self.unloaded_end_e1,
            self.loaded_boundary_to_row_1_distance,
            self.negative_side_distance,
            self.positive_side_distance,
            self.geometry_tolerance,
            self.eccentricity_tolerance,
        )
        if any(item.magnitude <= 0 for item in positive_lengths):
            raise ValueError("Physical dimensions and tolerances must be positive.")
        if self.force_line_offset.dimension != self.unloaded_end_e1.dimension:
            raise ValueError("force_line_offset must be a length.")
        if not isinstance(self.demand_source, MultiRowDemandSource):
            raise TypeError("demand_source must be MultiRowDemandSource.")
        automatic = self.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE
        explicit_fields = (self.signed_force_x, self.signed_force_y, self.force_reference)
        if automatic:
            if any(item is not None for item in explicit_fields):
                raise ValueError("Automatic demand cannot include explicit resolved-demand fields.")
            if self.physical_connection_request is None:
                raise ValueError("Automatic demand requires canonical physical connection context.")
            if (
                self.automatic_action_source_id is None
                or not self.automatic_action_source_id.strip()
            ):
                raise ValueError("Automatic demand requires an action-source identity.")
            if self.physical_connection_request.source_action_id != self.automatic_action_source_id:
                raise ValueError("Automatic action-source identity must match physical context.")
        else:
            if any(item is None for item in explicit_fields):
                raise ValueError("Explicit demand requires both force components and a reference.")
            if self.automatic_action_source_id is not None:
                raise ValueError("Explicit demand cannot include automatic action-source fields.")
            force_x = cast(PhysicalQuantity, self.signed_force_x)
            force_y = cast(PhysicalQuantity, self.signed_force_y)
            if force_x.dimension != force_y.dimension:
                raise ValueError("Signed in-plane force components must use force units.")
            if force_x.dimension.value != "FORCE":
                raise ValueError("Signed in-plane components must be forces.")
            if force_x.magnitude == 0 and force_y.magnitude == 0:
                raise ValueError("Signed in-plane connection demand cannot be zero in both axes.")
        if not self.layers:
            raise ValueError("At least one penetrated FRP layer is required.")
        layer_ids = tuple(item.layer_id for item in self.layers)
        if len(set(layer_ids)) != len(layer_ids):
            raise ValueError("Layer identities must be unique.")
        tension_ids = tuple(item.bolt_id for item in self.bolt_axis_tensions)
        if len(set(tension_ids)) != len(tension_ids):
            raise ValueError("Bolt-axis tension identities must be unique.")
        allocation_rows = tuple(item.row_ordinal for item in self.engineer_allocations)
        if len(set(allocation_rows)) != len(allocation_rows):
            raise ValueError("Engineer-defined row ordinals must be unique.")
        engineer_defined = (
            self.row_distribution_basis is RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION
        )
        if engineer_defined:
            if self.engineer_distribution_kind is None or not self.engineer_allocations:
                raise ValueError("Engineer-defined distribution requires a kind and all rows.")
            if not self.provenance.engineer_confirmed:
                raise ValueError("Engineer-defined distribution requires confirmed provenance.")
        elif self.engineer_distribution_kind is not None or self.engineer_allocations:
            raise ValueError("Engineer-defined values cannot accompany another demand method.")
        if self.prescribed_lbr is not None:
            value = decimal_value(self.prescribed_lbr)
            if value < 0 or value > 1:
                raise ValueError("prescribed_lbr must be between zero and one.")
            object.__setattr__(self, "prescribed_lbr", value)
        if self.physical_connection_request is not None:
            physical = self.physical_connection_request
            if physical.interface_id != self.interface_id:
                raise ValueError(
                    "Physical connection context must use the multi-row interface identity."
                )
            expected_unit = (
                Unit.IN
                if physical.assembly.unit_system is EngineeringUnitSystem.US_CUSTOMARY
                else Unit.MM
            )
            if expected_unit is not self.source_length_unit:
                raise ValueError(
                    "Physical connection context and multi-row source units must agree."
                )
            if physical.bolt_diameter.canonical_magnitude != self.bolt_diameter.canonical_magnitude:
                raise ValueError(
                    "Physical connection context and multi-row bolt diameter must agree."
                )


@dataclass(frozen=True, slots=True)
class MultiRowBoltVisualization:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    x: Decimal
    y: Decimal
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class MultiRowPathVisualization:
    path_id: str
    family: str
    accepted: bool
    points: tuple[tuple[Decimal, Decimal], ...]


@dataclass(frozen=True, slots=True)
class MultiRowLayerVisualization:
    layer_id: str
    component_id: str
    material_id: str
    material_axis_angle_degrees: Decimal
    material_direction: MaterialDirection
    thickness: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class MultiRowPhysicalBoltVisualization:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    penetrated_layer_ids: tuple[str, ...]
    display: BoltDisplaySnapshot


@dataclass(frozen=True, slots=True)
class MultiRowConnectionDemandVisualization:
    reference_point_id: str
    origin: PositionVector3D
    axis: UnitVector3D
    resultant: PhysicalQuantity
    frame_id: str


@dataclass(frozen=True, slots=True)
class MultiRowPerBoltDemandVisualization:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    origin: PositionVector3D
    direct_u: PhysicalQuantity
    direct_v: PhysicalQuantity
    moment_u: PhysicalQuantity
    moment_v: PhysicalQuantity
    total_u: PhysicalQuantity
    total_v: PhysicalQuantity
    total_magnitude: PhysicalQuantity
    total_axis: UnitVector3D | None


@dataclass(frozen=True, slots=True)
class MultiRowVisualizationSnapshot:
    schema_version: str
    coordinate_system: str
    source_length_unit: Unit
    boundary: tuple[Decimal, Decimal, Decimal, Decimal]
    bolts: tuple[MultiRowBoltVisualization, ...]
    row_ids: tuple[str, ...]
    bolt_line_ids: tuple[str, ...]
    unloaded_free_end_id: str
    row_1_id: str
    pitch: PhysicalQuantity
    gauge: PhysicalQuantity
    unloaded_end_e1: PhysicalQuantity
    loaded_boundary_to_row_1_distance: PhysicalQuantity
    negative_side_distance: PhysicalQuantity
    positive_side_distance: PhysicalQuantity
    demand_components: tuple[PhysicalQuantity, PhysicalQuantity]
    force_reference: str
    global_axes: tuple[tuple[str, tuple[Decimal, Decimal]], ...]
    local_axes: tuple[tuple[str, tuple[Decimal, Decimal]], ...]
    layers: tuple[MultiRowLayerVisualization, ...]
    block_paths: tuple[MultiRowPathVisualization, ...]
    physical_connection: SingleBoltVisualizationSnapshot | None
    physical_bolts: tuple[MultiRowPhysicalBoltVisualization, ...]
    connection_demand: MultiRowConnectionDemandVisualization | None
    automatic_bolt_demands: tuple[MultiRowPerBoltDemandVisualization, ...] = ()


@dataclass(frozen=True, slots=True)
class MultiRowPreviewResult:
    request_id: str
    connection_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    visualization_schema_version: str
    geometry_status: GeometryStatus
    plan_availability: PlanAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    warnings: tuple[str, ...]
    preview_fingerprint: str
    resistance_evaluated: bool
    design_check_ready: bool
    visualization: MultiRowVisualizationSnapshot | None
    demand_source: MultiRowDemandSource
    automatic_demand_result: EccentricDemandResult | None = None


@dataclass(frozen=True, slots=True)
class AutomaticGroupModeIntegrationResult:
    integration_contract_version: str
    scenario_results: tuple[EccentricGroupModeCompatibilityResult, ...]
    required_check_ids: tuple[str, ...]
    not_required_check_ids: tuple[str, ...]
    unsupported_required_check_ids: tuple[str, ...]
    incomplete_required_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    qualification: QualificationDisposition
    numerical_comparison: NumericalComparison
    governing_supported_check_ids: tuple[str, ...]
    overall_disposition: MultiRowOverallDisposition
    trace_layers: tuple[str, ...]
    result_fingerprint: str

    def __post_init__(self) -> None:
        if self.integration_contract_version != AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION:
            raise ValueError("Automatic group-mode integration must use the approved identity.")
        if not self.scenario_results:
            raise ValueError("Automatic group-mode integration requires at least one scenario.")
        scenario_ids = tuple(item.scenario_id for item in self.scenario_results)
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("Automatic group-mode scenario identities must be unique.")
        for name in (
            "required_check_ids",
            "not_required_check_ids",
            "unsupported_required_check_ids",
            "incomplete_required_check_ids",
            "failed_check_ids",
            "governing_supported_check_ids",
        ):
            values = cast(tuple[str, ...], getattr(self, name))
            if len(values) != len(set(values)) or any(not item.strip() for item in values):
                raise ValueError(f"{name} must contain unique nonblank identities.")
        if self.trace_layers != AUTOMATIC_GROUP_MODE_TRACE_LAYERS:
            raise ValueError("Automatic group-mode trace layers must remain complete and ordered.")
        if len(self.result_fingerprint) != 64 or any(
            item not in "0123456789abcdef" for item in self.result_fingerprint
        ):
            raise ValueError("Automatic group-mode result fingerprint must be lowercase SHA-256.")


@dataclass(frozen=True, slots=True)
class MultiRowOrchestrationResponse:
    request_id: str
    connection_id: str
    orchestration_contract_version: str
    preview: MultiRowPreviewResult
    calculation_result: MultiRowCalculationResult | None
    demand_source: MultiRowDemandSource
    automatic_demand_result: EccentricDemandResult | None = None
    automatic_handoff_results: tuple[EccentricResistanceHandoffResult, ...] = ()
    automatic_group_mode_integration: AutomaticGroupModeIntegrationResult | None = None


@dataclass(frozen=True, slots=True)
class _DemandAuthority:
    force_u: PhysicalQuantity
    force_v: PhysicalQuantity
    force_reference: str
    force_n: PhysicalQuantity | None = None
    resolved_action: ResolvedManualMemberEndAction | None = None
    group_frame: CartesianFrame3D | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedMultiRow:
    geometry: MultiRowGeometry
    end_distances: MultiRowEndDistanceContext
    total_demand: PhysicalQuantity
    hole_definition: StandardHoleDefinition
    demand_plan: MultiRowDemandPlan
    first_plans_by_layer: tuple[tuple[FirstRowNetTensionPlan, ...], ...]
    interrow_plans: tuple[InterrowShearOutPlan, ...]
    block_plan_set: BlockShearPlanSet
    applicability: MultiRowApplicability
    layer_contexts: tuple[MultiRowLayerExecutionContext, ...]
    bolt_contexts: tuple[MultiRowBoltExecutionContext, ...]
    line_contexts: tuple[MultiRowBoltLineExecutionContext, ...]
    factors: MultiRowFactorContext
    eccentricity: BlockShearEccentricityContext
    visualization: MultiRowVisualizationSnapshot
    preview_fingerprint: str
    warnings: tuple[str, ...]
    authority: _DemandAuthority


def _force_units(unit_system: EngineeringUnitSystem) -> tuple[Unit, Unit, Unit]:
    return (
        (Unit.IN, Unit.KIP, Unit.KIP_IN)
        if unit_system is EngineeringUnitSystem.US_CUSTOMARY
        else (Unit.MM, Unit.KN, Unit.KN_MM)
    )


def _resolve_demand_authority(request: MultiRowOrchestrationRequest) -> _DemandAuthority:
    if request.demand_source is MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND:
        return _DemandAuthority(
            cast(PhysicalQuantity, request.signed_force_x),
            cast(PhysicalQuantity, request.signed_force_y),
            cast(str, request.force_reference),
        )
    physical = cast(SingleBoltOrchestrationRequest, request.physical_connection_request)
    action_id = cast(str, request.automatic_action_source_id)
    action = next(
        (item for item in physical.assembly.member_end_actions if item.id == action_id),
        None,
    )
    if action is None:
        raise ValueError("Automatic action source does not exist in the canonical assembly.")
    if action.load_combination_id != request.load_combination_id:
        raise ValueError("Automatic action source and load combination identities conflict.")
    resolved_action = resolve_manual_member_end_action(physical.geometry_context, action)
    group_frame = physical.geometry_context.resolve_frame(
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, physical.bolt_group_id)
    ).frame
    force_unit = _force_units(physical.assembly.unit_system)[1]
    group_local = action.coordinate_frame == CoordinateFrameReference(
        CoordinateFrameKind.BOLT_GROUP_LOCAL, physical.bolt_group_id
    )
    if group_local:
        force_n = decimal_from_finite_real(action.force.fx)
        force_u = decimal_from_finite_real(action.force.fy)
        force_v = decimal_from_finite_real(action.force.fz)
    else:
        global_force = resolved_action.global_force
        components = (global_force.fx, global_force.fy, global_force.fz)
        force_u = sum(
            (
                decimal_from_finite_real(item) * decimal_from_finite_real(axis)
                for item, axis in zip(
                    components,
                    (group_frame.y_axis.x, group_frame.y_axis.y, group_frame.y_axis.z),
                    strict=True,
                )
            ),
            Decimal(0),
        )
        force_v = sum(
            (
                decimal_from_finite_real(item) * decimal_from_finite_real(axis)
                for item, axis in zip(
                    components,
                    (group_frame.z_axis.x, group_frame.z_axis.y, group_frame.z_axis.z),
                    strict=True,
                )
            ),
            Decimal(0),
        )
        force_n = sum(
            (
                decimal_from_finite_real(item) * decimal_from_finite_real(axis)
                for item, axis in zip(
                    components,
                    (group_frame.x_axis.x, group_frame.x_axis.y, group_frame.x_axis.z),
                    strict=True,
                )
            ),
            Decimal(0),
        )
    if force_u == 0 and force_v == 0:
        raise ValueError(
            "Automatic member-end force has no resolvable in-plane component for row planning."
        )
    return _DemandAuthority(
        PhysicalQuantity.of(force_u, force_unit),
        PhysicalQuantity.of(force_v, force_unit),
        f"{action.reference_point.kind.value}:{action.reference_point.owner_id or action.id}",
        PhysicalQuantity.of(force_n, force_unit),
        resolved_action,
        group_frame,
    )


def _force_magnitude(authority: _DemandAuthority) -> PhysicalQuantity:
    x = authority.force_u.canonical_magnitude
    y = authority.force_v.canonical_magnitude
    with localcontext() as context:
        context.prec = 100
        magnitude = (x * x + y * y).sqrt()
    return PhysicalQuantity(magnitude, Unit.N).to(authority.force_u.unit)


def _material_direction(layer_angle: Decimal, authority: _DemandAuthority) -> MaterialDirection:
    x = float(authority.force_u.canonical_magnitude)
    y = float(authority.force_v.canonical_magnitude)
    force_angle = math.degrees(math.atan2(y, x)) % 180.0
    difference = abs(force_angle - float(layer_angle)) % 180.0
    acute = min(difference, 180.0 - difference)
    return MaterialDirection.LONGITUDINAL if acute <= 45.0 else MaterialDirection.TRANSVERSE


def _build_geometry(
    request: MultiRowOrchestrationRequest,
    authority: _DemandAuthority,
) -> tuple[MultiRowGeometry, StandardHoleDefinition]:
    unit = request.source_length_unit
    bolt = request.bolt_diameter.to(unit)
    pitch = request.pitch.to(unit)
    gauge = request.gauge.to(unit)
    unloaded = request.unloaded_end_e1.to(unit)
    loaded = request.loaded_boundary_to_row_1_distance.to(unit)
    negative = request.negative_side_distance.to(unit)
    positive = request.positive_side_distance.to(unit)
    tolerance = request.geometry_tolerance.to(unit)
    hole = create_standard_hole(request.bolt_diameter, request.hole_basis)
    hole_diameter = hole.hole_diameter.to(unit)
    line_center = Decimal(request.bolts_per_row - 1) * gauge.magnitude / Decimal(2)
    row_span = Decimal(request.row_count - 1) * pitch.magnitude
    # Keep the accepted physical loaded boundary fixed while the independent
    # loaded-boundary distance places the complete group back from that plane.
    loaded_boundary_x = Decimal(2) * unloaded.magnitude + row_span
    first_generated_row_x = loaded_boundary_x - loaded.magnitude - row_span
    bolts = tuple(
        GeneralBolt(
            f"B_R{row + 1}_L{line + 1}",
            PlanarPoint2D(
                float(first_generated_row_x + Decimal(row) * pitch.magnitude),
                float(Decimal(line) * gauge.magnitude - line_center),
            ),
            float(bolt.magnitude),
            float(hole_diameter.magnitude),
            "ASTM_F593_17_GROUP_2_316_316L",
            request.connection_id,
        )
        for row in range(request.row_count)
        for line in range(request.bolts_per_row)
    )
    boundary = PlanarLayerBoundary(
        "MULTIROW_BOUNDARY",
        float(first_generated_row_x - unloaded.magnitude),
        float(loaded_boundary_x),
        float(-line_center - negative.magnitude),
        float(line_center + positive.magnitude),
    )
    group = GeneralBoltGroup(
        "MULTIROW_BOLT_GROUP",
        request.interface_id,
        request.row_count,
        request.row_count * request.bolts_per_row,
        tuple(reversed(bolts)),
    )
    force_vector = (
        float(authority.force_u.canonical_magnitude),
        float(authority.force_v.canonical_magnitude),
    )
    geometry = resolve_multirow_geometry(
        group,
        boundary,
        force_vector,
        MultiRowGeometryTolerance(float(tolerance.magnitude)),
    )
    return geometry, hole


def _demand_plan(
    request: MultiRowOrchestrationRequest,
    geometry: MultiRowGeometry,
    total: PhysicalQuantity,
) -> MultiRowDemandPlan:
    fractions: tuple[EngineerRowFraction, ...] = ()
    forces: tuple[EngineerRowForce, ...] = ()
    if request.row_distribution_basis is RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION:
        by_ordinal = {item.row_ordinal: item for item in request.engineer_allocations}
        expected = set(range(1, request.row_count + 1))
        if set(by_ordinal) != expected:
            raise ValueError("Engineer-defined values must cover every resolved row exactly once.")
        if request.engineer_distribution_kind is EngineerDistributionKind.FRACTIONS:
            fractions = tuple(
                EngineerRowFraction(row.id, cast(Decimal, by_ordinal[row.ordinal].fraction))
                for row in geometry.rows
            )
        else:
            forces = tuple(
                EngineerRowForce(
                    row.id,
                    cast(PhysicalQuantity, by_ordinal[row.ordinal].direct_force),
                )
                for row in geometry.rows
            )
    return plan_row_demands(
        geometry,
        total,
        request.row_distribution_basis,
        request.provenance,
        connected_materials=(
            request.material_pair
            if request.row_distribution_basis is RowDistributionBasis.ASCE_PRESCRIBED
            else None
        ),
        engineer_fractions=fractions,
        engineer_forces=forces,
    )


def _demand_lookup(demand_plan: MultiRowDemandPlan) -> dict[str, PhysicalQuantity]:
    result: dict[str, PhysicalQuantity] = {}
    for scenario in demand_plan.scenarios:
        for row in scenario.rows:
            for bolt in row.per_bolt_demands:
                zero = PhysicalQuantity.of(0, bolt.demand.unit)
                result[bolt.bolt_id] = max(result.get(bolt.bolt_id, zero), bolt.demand)
    return result


def _translated_position(
    point: PositionVector3D,
    row_axis: UnitVector3D,
    line_axis: UnitVector3D,
    row_offset: float,
    line_offset: float,
) -> PositionVector3D:
    return PositionVector3D(
        point.x + row_axis.x * row_offset + line_axis.x * line_offset,
        point.y + row_axis.y * row_offset + line_axis.y * line_offset,
        point.z + row_axis.z * row_offset + line_axis.z * line_offset,
    )


def _physical_connection_snapshot(
    request: MultiRowOrchestrationRequest,
    geometry: MultiRowGeometry,
    authority: _DemandAuthority,
) -> tuple[
    SingleBoltVisualizationSnapshot | None,
    tuple[MultiRowPhysicalBoltVisualization, ...],
    MultiRowConnectionDemandVisualization | None,
]:
    physical_request = request.physical_connection_request
    if physical_request is None:
        return None, (), None
    extents = request.connection_view_extents
    if extents is not None:
        boundary_length = float(geometry.boundary.max_x)
        extents = replace(
            extents,
            brace_view_length=max(extents.brace_view_length, boundary_length),
        )
    preview = preview_single_bolt_connection(physical_request, extents)
    base = preview.visualization
    if base is None:
        raise ValueError("Physical connection preview did not resolve a visualization snapshot.")
    if preview.geometry_status not in {
        PreviewGeometryStatus.VALID,
        PreviewGeometryStatus.INVALID_GEOMETRY,
    }:
        raise ValueError(f"Physical connection preview is {preview.geometry_status.value}.")
    physical_hole = create_standard_hole(request.bolt_diameter, request.hole_basis)
    physical_hole_diameter = float(
        physical_hole.hole_diameter.to(request.source_length_unit).magnitude
    )
    base = replace(
        base,
        bolt=replace(
            base.bolt,
            holes=tuple(replace(hole, diameter=physical_hole_diameter) for hole in base.bolt.holes),
        ),
    )
    group_frame = next(
        (
            frame.frame
            for frame in base.frames
            if frame.kind.value == "BOLT_GROUP_LOCAL" and frame.owner_id == base.bolt_group_id
        ),
        None,
    )
    if group_frame is None:
        raise ValueError("Physical connection preview lacks the selected bolt-group frame.")
    single_bolt_x = float(request.unloaded_end_e1.to(request.source_length_unit).magnitude)
    result: list[MultiRowPhysicalBoltVisualization] = []
    row_by_bolt = {bolt.bolt.id: row.id for row in geometry.rows for bolt in row.bolts}
    line_by_bolt = {bolt.bolt.id: line.id for line in geometry.bolt_lines for bolt in line.bolts}
    penetrated_layer_ids = tuple(
        layer.layer_id for layer in preview.orchestration_trace.resolved_layers
    )
    for item in sorted(geometry.group.bolts, key=lambda value: value.id):
        row_offset = item.center.x - single_bolt_x
        line_offset = item.center.y

        def translated(
            point: PositionVector3D,
            row_delta: float = row_offset,
            line_delta: float = line_offset,
        ) -> PositionVector3D:
            return _translated_position(
                point,
                group_frame.y_axis,
                group_frame.z_axis,
                row_delta,
                line_delta,
            )

        display = BoltDisplaySnapshot(
            base.bolt.bolt_group_id,
            item.id,
            translated(base.bolt.center),
            base.bolt.axis,
            translated(base.bolt.stack_start),
            translated(base.bolt.stack_end),
            base.bolt.bolt_diameter,
            tuple(
                HoleDisplaySnapshot(
                    f"{item.id}:{hole.id}",
                    hole.participant_id,
                    hole.physical_element_id,
                    translated(hole.start),
                    translated(hole.end),
                    hole.diameter,
                )
                for hole in base.bolt.holes
            ),
            tuple(
                WasherDisplaySnapshot(
                    f"{item.id}:{washer.id}",
                    washer.location,
                    translated(washer.start),
                    translated(washer.end),
                    washer.outside_diameter,
                )
                for washer in base.bolt.washers
            ),
        )
        result.append(
            MultiRowPhysicalBoltVisualization(
                item.id,
                row_by_bolt[item.id],
                line_by_bolt[item.id],
                penetrated_layer_ids,
                display,
            )
        )
    force_x = float(authority.force_u.canonical_magnitude)
    force_y = float(authority.force_v.canonical_magnitude)
    force_magnitude = math.hypot(force_x, force_y)
    axis = UnitVector3D(
        (group_frame.y_axis.x * force_x + group_frame.z_axis.x * force_y) / force_magnitude,
        (group_frame.y_axis.y * force_x + group_frame.z_axis.y * force_y) / force_magnitude,
        (group_frame.y_axis.z * force_x + group_frame.z_axis.z * force_y) / force_magnitude,
    )
    row_offset = sum(item.center.x - single_bolt_x for item in geometry.group.bolts) / len(
        geometry.group.bolts
    )
    line_offset = sum(item.center.y for item in geometry.group.bolts) / len(geometry.group.bolts)
    origin = _translated_position(
        base.bolt.center,
        group_frame.y_axis,
        group_frame.z_axis,
        row_offset,
        line_offset,
    )
    if authority.resolved_action is not None:
        origin = authority.resolved_action.resolved_reference_point.global_position
    demand = MultiRowConnectionDemandVisualization(
        (
            authority.force_reference
            if authority.resolved_action is not None
            else "MULTIROW_CONNECTION_DEMAND_REFERENCE"
        ),
        origin,
        axis,
        _force_magnitude(authority),
        next(
            frame.id
            for frame in base.frames
            if frame.kind.value == "BOLT_GROUP_LOCAL" and frame.owner_id == base.bolt_group_id
        ),
    )
    return base, tuple(result), demand


def _snapshot(
    request: MultiRowOrchestrationRequest,
    geometry: MultiRowGeometry,
    end_distances: MultiRowEndDistanceContext,
    layer_contexts: tuple[MultiRowLayerExecutionContext, ...],
    authority: _DemandAuthority,
) -> MultiRowVisualizationSnapshot:
    row_by_bolt = {bolt.bolt.id: row.id for row in geometry.rows for bolt in row.bolts}
    line_by_bolt = {bolt.bolt.id: line.id for line in geometry.bolt_lines for bolt in line.bolts}
    holes = create_standard_hole(request.bolt_diameter, request.hole_basis)
    bolts = tuple(
        MultiRowBoltVisualization(
            item.id,
            row_by_bolt[item.id],
            line_by_bolt[item.id],
            Decimal(str(item.center.x)),
            Decimal(str(item.center.y)),
            request.bolt_diameter,
            holes.hole_diameter,
        )
        for item in sorted(geometry.group.bolts, key=lambda value: value.id)
    )
    paths = resolve_block_shear_paths(geometry)
    path_snapshots = tuple(
        MultiRowPathVisualization(
            candidate.id,
            candidate.family.value,
            candidate.accepted,
            tuple(
                (Decimal(str(point.u)), Decimal(str(point.v)))
                for segment in candidate.segments
                for point in (segment.start, segment.end)
            ),
        )
        for candidate in paths.candidates
    )
    layers = tuple(
        MultiRowLayerVisualization(
            source.layer_id,
            source.component_id,
            source.material_id,
            source.material_axis_angle_degrees,
            context.material_direction,
            source.thickness,
        )
        for source, context in zip(request.layers, layer_contexts, strict=True)
    )
    boundary = geometry.boundary
    boundary_values = cast(
        tuple[Decimal, Decimal, Decimal, Decimal],
        tuple(
            Decimal(str(value))
            for value in (boundary.min_x, boundary.max_x, boundary.min_y, boundary.max_y)
        ),
    )
    physical_connection, physical_bolts, connection_demand = _physical_connection_snapshot(
        request, geometry, authority
    )
    return MultiRowVisualizationSnapshot(
        MULTIROW_VISUALIZATION_SCHEMA_VERSION,
        "INTERFACE_XY_WITH_SIGNED_FORCE_UV",
        request.source_length_unit,
        boundary_values,
        bolts,
        tuple(item.id for item in geometry.rows),
        tuple(item.id for item in geometry.bolt_lines),
        f"{boundary.id}:UNLOADED_FREE_END",
        geometry.rows[0].id,
        request.pitch,
        request.gauge,
        end_distances.unloaded_end_e1,
        end_distances.loaded_boundary_to_row_1_distance,
        request.negative_side_distance,
        request.positive_side_distance,
        (authority.force_u, authority.force_v),
        authority.force_reference,
        (("X", (Decimal(1), Decimal(0))), ("Y", (Decimal(0), Decimal(1)))),
        (
            (
                "u",
                (Decimal(str(geometry.force_u[0])), Decimal(str(geometry.force_u[1]))),
            ),
            (
                "v",
                (Decimal(str(geometry.force_v[0])), Decimal(str(geometry.force_v[1]))),
            ),
        ),
        layers,
        path_snapshots,
        physical_connection,
        physical_bolts,
        connection_demand,
    )


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PlanarFixedMaterialOrientation):
        return {
            "crosswise_axis": value.crosswise_axis.value,
            "through_thickness_axis": value.through_thickness_axis.value,
            **({"crosswise_sign": value.crosswise_sign} if value.crosswise_sign != 1 else {}),
            **(
                {"through_thickness_sign": value.through_thickness_sign}
                if value.through_thickness_sign != 1
                else {}
            ),
        }
    if is_dataclass(value):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
            if field.name != "display_unit_system"
            and not (
                field.name == "single_row_geometry_preview_authorized"
                and not getattr(value, field.name)
            )
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _preview_fingerprint(
    request: MultiRowOrchestrationRequest,
    snapshot: MultiRowVisualizationSnapshot,
) -> str:
    encoded = _canonical_multirow_preview_json(request, snapshot)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical_multirow_preview_json(
    request: MultiRowOrchestrationRequest,
    snapshot: MultiRowVisualizationSnapshot,
) -> str:
    """Expose deterministic pre-hash content to focused internal tests."""

    payload = {"request": _canonical(request), "visualization": _canonical(snapshot)}
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _property_value(material: MaterialPropertySnapshot, kind: FRPPropertyKind) -> PhysicalQuantity:
    entry = material.lookup(kind)
    if entry is None:  # pragma: no cover - controlled ICE snapshot is complete by construction
        raise ValueError(f"Controlled material lacks required property {kind.value}.")
    return entry.value


def _resolve(request: MultiRowOrchestrationRequest) -> _ResolvedMultiRow:
    authority = _resolve_demand_authority(request)
    geometry, hole = _build_geometry(request, authority)
    end_distances = resolve_multirow_end_distances(
        geometry,
        request.source_length_unit,
        exact_unloaded_end_e1=request.unloaded_end_e1,
        exact_physical_pitches=tuple(request.pitch for _ in range(request.row_count - 1)),
        exact_loaded_boundary_to_row_1_distance=(request.loaded_boundary_to_row_1_distance),
    )
    total = _force_magnitude(authority)
    demand_plan = _demand_plan(request, geometry, total)
    material = create_locked_ice_material_snapshot()
    layer_contexts = tuple(
        MultiRowLayerExecutionContext(
            layer.layer_id,
            layer.component_id,
            material,
            layer.thickness,
            _material_direction(layer.material_axis_angle_degrees, authority),
            layer.element_classification,
            layer.end_use_factors,
            layer.bearing_thread_status,
            (geometry.group.id, geometry.boundary.id),
        )
        for layer in request.layers
    )
    if any(layer.material_id != material.id for layer in request.layers):
        raise ValueError(
            "The public Stage 2.4C workflow supports the controlled ICE material only."
        )
    first_geometries = tuple(
        resolve_first_row_geometry(
            geometry,
            request.source_length_unit,
            request.bolt_diameter,
            layer.material_direction,
            layer.element_classification,
        )
        for layer in layer_contexts
    )
    first_plans_by_layer = tuple(
        build_first_row_net_tension_plans(
            first_geometry,
            layer.thickness,
            _property_value(
                layer.material,
                FRPPropertyKind.FT_L
                if layer.material_direction is MaterialDirection.LONGITUDINAL
                else FRPPropertyKind.FT_T,
            ),
            hole.hole_diameter + hole.published_increment,
            prescribed_lbr=request.prescribed_lbr,
        )
        for first_geometry, layer in zip(first_geometries, layer_contexts, strict=True)
    )
    first_applicability = assess_multirow_applicability(
        geometry, first_geometries[0], request.row_distribution_basis
    )
    interrow_plans = build_interrow_shear_out_plans(
        geometry,
        request.source_length_unit,
        layer_contexts[0].thickness,
        _property_value(material, FRPPropertyKind.FSH_LT),
        total,
        ("EQUIVALENT_RECTANGULAR_LINE_RULE",),
    )
    holes = tuple(BoltHoleSource(item.id, hole) for item in geometry.group.bolts)
    path_resolution = resolve_block_shear_paths(geometry)
    all_block_plans: list[BlockShearAreaPlan] = []
    for layer in layer_contexts:
        plans = build_block_shear_area_plans(
            path_resolution, geometry, request.source_length_unit, layer.thickness, holes
        )
        all_block_plans.extend(
            replace(plan, path_id=f"{layer.layer_id}:{plan.path_id}") for plan in plans.candidates
        )
    block_plan_set = BlockShearPlanSet(
        tuple(all_block_plans), DeferredExecutionStatus.DEFERRED_STAGE_2_4B
    )
    fastener_source = create_locked_f593_fastener_snapshot()
    fastener = replace(
        fastener_source,
        shear_plane_thread_statuses=(
            ThreadStatusAssignment("SHEAR_PLANE_1", ThreadStatus.EXCLUDED),
        ),
        bearing_layer_thread_statuses=tuple(
            ThreadStatusAssignment(layer.layer_id, layer.bearing_thread_status)
            for layer in layer_contexts
        ),
        number_of_shear_planes=1,
    )
    if not fastener.diameter_min <= request.bolt_diameter <= fastener.diameter_max:
        raise ValueError("Bolt diameter is outside the controlled F593 preset range.")
    demand_lookup = _demand_lookup(demand_plan)
    tension_lookup = {item.bolt_id: item.demand for item in request.bolt_axis_tensions}
    physical_ids = {item.id for item in geometry.group.bolts}
    if not set(tension_lookup) <= physical_ids:
        raise ValueError("Every bolt-axis tension identity must identify a resolved physical bolt.")
    zero_force = PhysicalQuantity.of(0, total.unit)
    automatic_axis_required = (
        request.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE
        and authority.force_n is not None
        and authority.force_n.magnitude != 0
    )
    axis_demand_required = request.bolt_axis_tension_required or automatic_axis_required
    bolt_contexts = tuple(
        MultiRowBoltExecutionContext(
            bolt.id,
            request.bolt_diameter,
            fastener,
            ThreadStatus.EXCLUDED,
            demand_lookup.get(bolt.id, zero_force),
            tension_lookup.get(bolt.id),
            axis_demand_required,
            fastener.washer_geometry,
            tuple(layer.layer_id for layer in layer_contexts),
        )
        for bolt in sorted(geometry.group.bolts, key=lambda item: item.id)
    )
    line_contexts = tuple(
        MultiRowBoltLineExecutionContext(
            plan.bolt_line_id,
            plan.per_line_demand,
            True,
            "EQUIVALENT_RECTANGULAR_LINE_RULE",
        )
        for plan in interrow_plans
    )
    pitch_trace = (
        constant_pitch_factor(
            tuple(request.pitch for _ in range(request.row_count - 1)), request.bolt_diameter
        )
        if request.row_count > 1
        else PitchFactorTrace(
            request.pitch,
            request.bolt_diameter * Decimal(4),
            Decimal(1),
            False,
        )
    )
    factors = MultiRowFactorContext(
        select_time_effect_factor(request.time_effect_category).value,
        create_lap_factor_plan(request.lap_configuration).applicable_in_plane_frp_factor,
        pitch_trace.pitch_factor_c_delta,
        PitchFactorSource.AUTOMATIC_CONSTANT_PITCH,
    )
    eccentricity = BlockShearEccentricityContext(
        request.force_line_offset,
        authority.force_reference,
        request.eccentricity_tolerance,
        (geometry.group.id, geometry.boundary.id),
        classify_block_shear_eccentricity(
            request.force_line_offset, request.eccentricity_tolerance
        ),
    )
    visualization = _snapshot(request, geometry, end_distances, layer_contexts, authority)
    fingerprint = _preview_fingerprint(request, visualization)
    warning_values = [
        *(item.code.value for item in first_applicability.warnings),
        *(item.code.value for item in demand_plan.warnings),
    ]
    if request.bolts_per_row > 3:
        warning_values.append("MORE_THAN_THREE_BOLTS_PER_ROW_FIRST_ROW_CHECK_UNSUPPORTED")
    warning_values.extend(
        (
            "CONTROLLED_ICE_DEVELOPMENT_MATERIAL_REQUIRES_ENGINEERING_REVIEW",
            "F593_TENSILE_SOURCE_DATA_PENDING",
        )
    )
    warnings = tuple(dict.fromkeys(warning_values))
    return _ResolvedMultiRow(
        geometry,
        end_distances,
        total,
        hole,
        demand_plan,
        first_plans_by_layer,
        interrow_plans,
        block_plan_set,
        first_applicability,
        layer_contexts,
        bolt_contexts,
        line_contexts,
        factors,
        eccentricity,
        visualization,
        fingerprint,
        warnings,
        authority,
    )


def _invalid_preview(request: MultiRowOrchestrationRequest, message: str) -> MultiRowPreviewResult:
    payload = json.dumps(
        {"request": _canonical(request), "invalid_geometry": message},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return MultiRowPreviewResult(
        request.request_id,
        request.connection_id,
        MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
        MULTIROW_PREVIEW_SCHEMA_VERSION,
        MULTIROW_VISUALIZATION_SCHEMA_VERSION,
        GeometryStatus.INVALID_GEOMETRY,
        PlanAvailability.CALCULATION_NOT_SUPPORTED,
        MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
        QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        (f"INVALID_GEOMETRY:{message}",),
        hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        False,
        False,
        None,
        request.demand_source,
    )


def _preview_from_resolved(
    request: MultiRowOrchestrationRequest,
    resolved: _ResolvedMultiRow,
    automatic_demand: EccentricDemandResult | None,
) -> MultiRowPreviewResult:
    applicability = resolved.applicability
    visualization = resolved.visualization
    warnings = list(resolved.warnings)
    if automatic_demand is not None:
        visualization = replace(
            visualization,
            automatic_bolt_demands=_automatic_bolt_visualization(resolved, automatic_demand),
        )
        warnings.extend(item.code.value for item in automatic_demand.warnings)
        warnings.extend(
            item.code.value for scenario in automatic_demand.scenarios for item in scenario.warnings
        )
    preview_fingerprint = resolved.preview_fingerprint
    if automatic_demand is not None:
        preview_fingerprint = hashlib.sha256(
            f"{resolved.preview_fingerprint}:{automatic_demand.input_fingerprint}:"
            f"{automatic_demand.result_fingerprint}".encode("ascii")
        ).hexdigest()
    physical = visualization.physical_connection
    physical_orientation = None if physical is None else physical.connection_orientation
    physical_geometry_valid = physical_orientation is None or physical_orientation.geometry_valid
    physical_warnings = tuple(dict.fromkeys(warnings))
    if physical_orientation is not None and not physical_orientation.geometry_valid:
        participants = ",".join(physical_orientation.interference_participant_ids)
        physical_warnings = (
            *physical_warnings,
            f"INVALID_PHYSICAL_CONNECTION_GEOMETRY:{participants}",
        )
    return MultiRowPreviewResult(
        request.request_id,
        request.connection_id,
        MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
        MULTIROW_PREVIEW_SCHEMA_VERSION,
        MULTIROW_VISUALIZATION_SCHEMA_VERSION,
        GeometryStatus.VALID if physical_geometry_valid else GeometryStatus.INVALID_GEOMETRY,
        (
            PlanAvailability.CALCULATION_NOT_SUPPORTED
            if request.single_row_geometry_preview_authorized
            else (
                applicability.availability
                if physical_geometry_valid
                else PlanAvailability.CALCULATION_NOT_SUPPORTED
            )
        ),
        applicability.method_applicability,
        applicability.qualification,
        physical_warnings,
        preview_fingerprint,
        False,
        physical_geometry_valid
        and resolved.demand_plan.availability is PlanAvailability.READY
        and (
            automatic_demand is None
            or automatic_demand.availability is DemandAnalysisAvailability.CALCULATED
        ),
        visualization,
        request.demand_source,
        automatic_demand,
    )


def preview_multirow_connection(request: MultiRowOrchestrationRequest) -> MultiRowPreviewResult:
    """Resolve geometry and optional automatic demand while executing zero resistance."""

    try:
        resolved = _resolve(request)
        automatic = None
        if request.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE:
            automatic = _automatic_demand(request, resolved, _execution_bundle(request, resolved))
        return _preview_from_resolved(request, resolved, automatic)
    except (ArithmeticError, TypeError, ValueError) as error:
        return _invalid_preview(request, str(error))


def _check(
    check_id: str,
    family: MultiRowCheckFamily,
    method: MultiRowEquationMethod,
    demand: PhysicalQuantity | None,
    applicability: MultiRowMethodApplicability,
    qualification: QualificationDisposition,
    availability: PlanAvailability = PlanAvailability.READY,
    *,
    layer_id: str | None = None,
    bolt_id: str | None = None,
    row_id: str | None = None,
    line_id: str | None = None,
    path_id: str | None = None,
    first_plan: FirstRowNetTensionPlan | None = None,
    interrow_plan: InterrowShearOutPlan | None = None,
    block_plan: BlockShearAreaPlan | None = None,
    lbr: Decimal | None = None,
) -> MultiRowExecutableCheck:
    return MultiRowExecutableCheck(
        check_id,
        getattr(first_plan or interrow_plan or block_plan, "id", None)
        or getattr(block_plan, "path_id", None)
        or check_id,
        family,
        method,
        "ASCE/SEI 74-23 Chapter 8 / controlled Slice 2 RC2 method",
        applicability,
        qualification,
        availability,
        GeometryStatus.VALID,
        demand,
        layer_id,
        bolt_id,
        row_id,
        line_id,
        path_id,
        first_plan,
        interrow_plan,
        block_plan,
        lbr,
    )


def _execution_bundle(
    request: MultiRowOrchestrationRequest, resolved: _ResolvedMultiRow
) -> MultiRowExecutionBundle:
    applicability = resolved.applicability
    method = applicability.method_applicability
    qualification = applicability.qualification
    checks: list[MultiRowExecutableCheck] = []
    for bolt in resolved.bolt_contexts:
        checks.append(
            _check(
                f"BOLT_SHEAR:{bolt.bolt_id}",
                MultiRowCheckFamily.BOLT_SHEAR,
                MultiRowEquationMethod.BOLT_SHEAR,
                bolt.in_plane_demand,
                method,
                qualification,
                PlanAvailability.SOURCE_DATA_PENDING,
                bolt_id=bolt.bolt_id,
            )
        )
        if bolt.bolt_axis_tension_required:
            tension_availability = (
                PlanAvailability.SOURCE_DATA_PENDING
                if bolt.bolt_axis_tension_demand is not None
                else PlanAvailability.INCOMPLETE_INPUT
            )
            for family, equation in (
                (MultiRowCheckFamily.BOLT_TENSION, MultiRowEquationMethod.BOLT_TENSION),
                (
                    MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
                    MultiRowEquationMethod.BOLT_COMBINED_TENSION_SHEAR,
                ),
            ):
                checks.append(
                    _check(
                        f"{family.value}:{bolt.bolt_id}",
                        family,
                        equation,
                        bolt.bolt_axis_tension_demand,
                        method,
                        qualification,
                        tension_availability,
                        bolt_id=bolt.bolt_id,
                    )
                )
            for layer in resolved.layer_contexts:
                checks.append(
                    _check(
                        f"PULL_THROUGH:{layer.layer_id}:{bolt.bolt_id}",
                        MultiRowCheckFamily.PULL_THROUGH,
                        MultiRowEquationMethod.PULL_THROUGH,
                        bolt.bolt_axis_tension_demand,
                        method,
                        qualification,
                        PlanAvailability.SOURCE_DATA_PENDING,
                        layer_id=layer.layer_id,
                        bolt_id=bolt.bolt_id,
                    )
                )
        for layer in resolved.layer_contexts:
            checks.append(
                _check(
                    f"PIN_BEARING:{layer.layer_id}:{bolt.bolt_id}",
                    MultiRowCheckFamily.PIN_BEARING,
                    MultiRowEquationMethod.PIN_BEARING,
                    bolt.in_plane_demand,
                    method,
                    qualification,
                    layer_id=layer.layer_id,
                    bolt_id=bolt.bolt_id,
                )
            )
    row_1_demand = max(
        (
            row.row_demand
            for scenario in resolved.demand_plan.scenarios
            for row in scenario.rows
            if row.row_id == resolved.geometry.rows[0].id
        ),
        default=PhysicalQuantity.of(0, resolved.total_demand.unit),
    )
    for layer, plans in zip(resolved.layer_contexts, resolved.first_plans_by_layer, strict=True):
        if request.row_count > 3:
            selected = plans[2]
        elif request.first_row_method is FirstRowPlanMethod.ASCE_COMMENTARY_FULL:
            selected = plans[1]
        else:
            selected = plans[0]
        equation = {
            FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED: (
                MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED
            ),
            FirstRowPlanMethod.ASCE_COMMENTARY_FULL: (
                MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL
            ),
            FirstRowPlanMethod.RATIONAL_MULTIROW_LOWER_ENVELOPE: (
                MultiRowEquationMethod.FIRST_ROW_RATIONAL_LOWER_ENVELOPE
            ),
        }[selected.method]
        checks.append(
            _check(
                f"FIRST_ROW:{layer.layer_id}",
                MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                equation,
                row_1_demand,
                selected.method_applicability,
                selected.qualification,
                selected.availability,
                layer_id=layer.layer_id,
                row_id=resolved.geometry.rows[0].id,
                first_plan=selected,
                lbr=request.prescribed_lbr,
            )
        )
        for plan in resolved.interrow_plans:
            equation = {
                "ASCE_EQ_8_12": MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12,
                "ASCE_EQ_8_13": MultiRowEquationMethod.INTERROW_ASCE_EQ_8_13,
                "RATIONAL_EXTENSION_EQ_8_13": (
                    MultiRowEquationMethod.INTERROW_RATIONAL_EXTENSION_EQ_8_13
                ),
            }[plan.method.value]
            checks.append(
                _check(
                    f"INTERROW:{layer.layer_id}:{plan.bolt_line_id}",
                    MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                    equation,
                    plan.per_line_demand,
                    plan.method_applicability,
                    plan.qualification,
                    plan.availability,
                    layer_id=layer.layer_id,
                    line_id=plan.bolt_line_id,
                    interrow_plan=plan,
                )
            )
        checks.append(
            _check(
                f"MATERIAL_SOURCE_REVIEW:{layer.layer_id}",
                MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW,
                MultiRowEquationMethod.STATUS_ONLY,
                None,
                method,
                QualificationDisposition.ENGINEERING_REVIEW_REQUIRED,
                layer_id=layer.layer_id,
            )
        )
    for block_plan in resolved.block_plan_set.candidates:
        layer_id = block_plan.path_id.split(":", 1)[0]
        layer = next(item for item in resolved.layer_contexts if item.layer_id == layer_id)
        if block_plan.path_status is BlockPathPlanStatus.ACCEPTED and (
            layer.material_direction is MaterialDirection.LONGITUDINAL
        ):
            block_method = (
                MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14A
                if resolved.eccentricity.classification
                is BlockShearEccentricityClassification.CONCENTRIC
                else MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14B
            )
            checks.append(
                _check(
                    f"BLOCK_SHEAR:{block_plan.path_id}",
                    MultiRowCheckFamily.BLOCK_SHEAR,
                    block_method,
                    resolved.total_demand,
                    method,
                    qualification,
                    block_plan.availability,
                    layer_id=layer_id,
                    path_id=block_plan.path_id,
                    block_plan=block_plan,
                )
            )
    planning = MultiRowCalculationPlanSet(
        resolved.demand_plan,
        resolved.applicability,
        tuple(plan for group in resolved.first_plans_by_layer for plan in group),
        tuple(resolved.interrow_plans),
        tuple(plan.path_id for plan in resolved.block_plan_set.candidates),
    )
    required = tuple(item.check_id for item in checks)
    return MultiRowExecutionBundle(
        physical_geometry_context(resolved.geometry, request.source_length_unit),
        planning,
        resolved.block_plan_set,
        resolved.end_distances,
        resolved.layer_contexts,
        resolved.bolt_contexts,
        resolved.line_contexts,
        MultiRowSignedDemandContext(
            resolved.authority.force_u.canonical_magnitude,
            resolved.authority.force_v.canonical_magnitude,
            resolved.total_demand,
            request.load_combination_id,
        ),
        resolved.factors,
        MultiRowRequiredCheckContract(required),
        tuple(checks),
        request.provenance,
        Slice2VersionContext(),
        (
            MultiRowFingerprintMetadataEntry(
                "application_contract", MULTIROW_ORCHESTRATION_CONTRACT_VERSION
            ),
            MultiRowFingerprintMetadataEntry("connection_id", request.connection_id),
            MultiRowFingerprintMetadataEntry("source_reference", request.source_reference),
        ),
        resolved.eccentricity,
    )


def _exact_vector(values: tuple[float, float, float], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(
        *(PhysicalQuantity.of(decimal_from_finite_real(item), unit) for item in values)
    )


def _exact_axis(values: tuple[float, float, float]) -> tuple[Decimal, Decimal, Decimal]:
    return (
        decimal_from_finite_real(values[0]),
        decimal_from_finite_real(values[1]),
        decimal_from_finite_real(values[2]),
    )


def _exact_decimal_vector(
    values: tuple[Decimal, Decimal, Decimal], unit: Unit
) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity.of(item, unit) for item in values))


def _decimal_sine_cosine_degrees(angle_degrees: Decimal) -> tuple[Decimal, Decimal]:
    """Return deterministic Decimal trigonometry for canonical template directions."""

    normalized = decimal_value(angle_degrees) % Decimal(360)
    cardinal = {
        Decimal(0): (Decimal(0), Decimal(1)),
        Decimal(90): (Decimal(1), Decimal(0)),
        Decimal(180): (Decimal(0), Decimal(-1)),
        Decimal(270): (Decimal(-1), Decimal(0)),
    }
    if normalized in cardinal:
        return cardinal[normalized]
    with localcontext() as context:
        context.prec = 100
        radians = normalized * _DECIMAL_PI / Decimal(180)
        if radians > _DECIMAL_PI:
            radians -= Decimal(2) * _DECIMAL_PI
        squared = radians * radians

        sine_term = radians
        sine = radians
        index = 1
        while True:
            sine_term *= -squared / (Decimal(2 * index) * Decimal(2 * index + 1))
            updated = sine + sine_term
            if updated == sine:
                break
            sine = updated
            index += 1

        cosine_term = Decimal(1)
        cosine = Decimal(1)
        index = 1
        while True:
            cosine_term *= -squared / (Decimal(2 * index - 1) * Decimal(2 * index))
            updated = cosine + cosine_term
            if updated == cosine:
                break
            cosine = updated
            index += 1
        return +sine, +cosine


def _decimal_cross(
    left: tuple[Decimal, Decimal, Decimal],
    right: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _exact_template_group_axes(
    physical: SingleBoltOrchestrationRequest,
) -> (
    tuple[
        tuple[Decimal, Decimal, Decimal],
        tuple[Decimal, Decimal, Decimal],
        tuple[Decimal, Decimal, Decimal],
    ]
    | None
):
    """Rebuild the template group basis from its exact semantic angle, without libm."""

    orientation = physical.template_orientation
    if orientation is None or orientation.plan_angle_degrees != 0:
        return None
    sine, cosine = _decimal_sine_cosine_degrees(orientation.brace_to_column_angle_degrees)
    with localcontext() as context:
        context.prec = 100
        sine = sine.quantize(_CANONICAL_DIRECTION_QUANTUM, rounding=ROUND_HALF_EVEN)
        cosine = cosine.quantize(_CANONICAL_DIRECTION_QUANTUM, rounding=ROUND_HALF_EVEN)
        exterior = orientation.connection_side is ColumnFlangeConnectionSide.EXTERIOR
        normal = (Decimal(1) if exterior else Decimal(-1), Decimal(0), Decimal(0))
        row = (Decimal(0), -sine, cosine if exterior else -cosine)
        line = _decimal_cross(normal, row)
        return (
            cast(tuple[Decimal, Decimal, Decimal], tuple(+item for item in row)),
            cast(tuple[Decimal, Decimal, Decimal], tuple(+item for item in line)),
            normal,
        )


def _automatic_demand_input(
    request: MultiRowOrchestrationRequest,
    resolved: _ResolvedMultiRow,
    bundle: MultiRowExecutionBundle,
) -> EccentricDemandInput:
    action = resolved.authority.resolved_action
    frame = resolved.authority.group_frame
    if action is None or frame is None:
        raise ValueError("Automatic demand requires resolved canonical action and frame authority.")
    length_unit, force_unit, moment_unit = _force_units(action.unit_system)
    physical = cast(SingleBoltOrchestrationRequest, request.physical_connection_request)
    exact_group_local = action.action.coordinate_frame == CoordinateFrameReference(
        CoordinateFrameKind.BOLT_GROUP_LOCAL, physical.bolt_group_id
    )
    template_axes = _exact_template_group_axes(physical) if exact_group_local else None
    if template_axes is None:
        row_axis = _exact_axis((frame.y_axis.x, frame.y_axis.y, frame.y_axis.z))
        line_axis = _exact_axis((frame.z_axis.x, frame.z_axis.y, frame.z_axis.z))
        normal_axis = _exact_axis((frame.x_axis.x, frame.x_axis.y, frame.x_axis.z))
    else:
        row_axis, line_axis, normal_axis = template_axes
    anchor_decimal = request.unloaded_end_e1.to(length_unit).magnitude
    if exact_group_local:
        with localcontext() as context:
            context.prec = 100
            origin = tuple(-direction * anchor_decimal for direction in row_axis)
    else:
        frame_origin = _exact_axis((frame.origin.x, frame.origin.y, frame.origin.z))
        origin = tuple(
            value - direction * anchor_decimal
            for value, direction in zip(frame_origin, row_axis, strict=True)
        )
    exact_frame = ExactInterfaceFrame(
        request.interface_id,
        _exact_decimal_vector(cast(tuple[Decimal, Decimal, Decimal], origin), length_unit),
        row_axis,
        line_axis,
        normal_axis,
    )
    global_force = action.global_force
    global_moment = action.global_moment
    point = action.resolved_reference_point.global_position
    force_vector = _exact_vector((global_force.fx, global_force.fy, global_force.fz), force_unit)
    moment_vector = _exact_vector(
        (global_moment.mx, global_moment.my, global_moment.mz), moment_unit
    )
    point_vector = _exact_vector((point.x, point.y, point.z), length_unit)
    if exact_group_local:
        source_force = (
            cast(PhysicalQuantity, resolved.authority.force_n).canonical_magnitude,
            resolved.authority.force_u.canonical_magnitude,
            resolved.authority.force_v.canonical_magnitude,
        )
        source_moment = tuple(
            PhysicalQuantity.of(decimal_from_finite_real(item), moment_unit).canonical_magnitude
            for item in (action.action.moment.mx, action.action.moment.my, action.action.moment.mz)
        )
        axes = (normal_axis, row_axis, line_axis)
        with localcontext() as context:
            context.prec = 100
            canonical_force = cast(
                tuple[Decimal, Decimal, Decimal],
                tuple(
                    sum(
                        (
                            component * axis[index]
                            for component, axis in zip(source_force, axes, strict=True)
                        ),
                        Decimal(0),
                    )
                    for index in range(3)
                ),
            )
            canonical_moment = cast(
                tuple[Decimal, Decimal, Decimal],
                tuple(
                    sum(
                        (
                            component * axis[index]
                            for component, axis in zip(source_moment, axes, strict=True)
                        ),
                        Decimal(0),
                    )
                    for index in range(3)
                ),
            )
        force_vector = _exact_decimal_vector(canonical_force, Unit.N)
        moment_vector = _exact_decimal_vector(canonical_moment, Unit.N_MM)
        if action.action.reference_point.kind is ReferencePointKind.BOLT_GROUP_ORIGIN:
            point_vector = _exact_decimal_vector((Decimal(0), Decimal(0), Decimal(0)), length_unit)
    zero_moment = _exact_vector((0.0, 0.0, 0.0), moment_unit)
    return EccentricDemandInput(
        action.action.id,
        action.member.id,
        force_vector,
        moment_vector,
        zero_moment,
        point_vector,
        exact_frame,
        bundle.physical_geometry,
        resolved.demand_plan,
        resolved.applicability.method_applicability,
        resolved.applicability.qualification,
        (
            f"action_source:{action.action.id}",
            f"member:{action.member.id}",
            f"reference:{resolved.authority.force_reference}",
            "Stage 2.4A direct row-demand plan",
        ),
    )


def _layer_axis(angle_degrees: Decimal) -> tuple[Decimal, Decimal]:
    normalized = angle_degrees % Decimal(180)
    if normalized == 0:
        return Decimal(1), Decimal(0)
    if normalized == 90:
        return Decimal(0), Decimal(1)
    radians = math.radians(float(normalized))
    return Decimal(str(math.cos(radians))), Decimal(str(math.sin(radians)))


def _block_shear_compatibility(
    request: MultiRowOrchestrationRequest,
    resolved: _ResolvedMultiRow,
    bundle: MultiRowExecutionBundle,
    demand: EccentricDemandResult,
    scenario: DemandScenarioResult,
) -> BlockShearCompatibilityEvidence | None:
    total = resolved.total_demand.canonical_magnitude
    if total == 0 or bundle.eccentricity is None:
        return None
    actual_offset = abs(scenario.external_moment.canonical_magnitude / total)
    declared_offset = abs(request.force_line_offset.canonical_magnitude)
    if abs(actual_offset - declared_offset) > request.eccentricity_tolerance.canonical_magnitude:
        return None
    compatible_ids = tuple(
        item.check_id for item in bundle.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR
    )
    return BlockShearCompatibilityEvidence(
        BlockShearCompatibilityStatus.MATCHED,
        f"{request.connection_id}:BLOCK_SHEAR_FORCE_LINE",
        demand.action_source_id,
        demand.interface_frame.interface_id,
        bundle.signed_demand.source_id,
        bundle.physical_geometry.interface_id,
        bundle.eccentricity.geometric_reference,
        bundle.eccentricity.source_geometry_ids,
        compatible_ids,
    )


def _automatic_bolt_visualization(
    resolved: _ResolvedMultiRow,
    demand: EccentricDemandResult,
) -> tuple[MultiRowPerBoltDemandVisualization, ...]:
    snapshot = resolved.visualization
    physical = {item.bolt_id: item for item in snapshot.physical_bolts}
    frame = resolved.authority.group_frame
    if frame is None or not demand.scenarios:
        return ()
    scenario = demand.scenarios[0]
    result: list[MultiRowPerBoltDemandVisualization] = []
    for item in scenario.per_bolt:
        physical_bolt = physical.get(item.bolt_id)
        if physical_bolt is None:
            continue
        u = float(item.total_force.u.canonical_magnitude)
        v = float(item.total_force.v.canonical_magnitude)
        magnitude = math.hypot(u, v)
        axis = None
        if magnitude != 0:
            axis = UnitVector3D(
                (frame.y_axis.x * u + frame.z_axis.x * v) / magnitude,
                (frame.y_axis.y * u + frame.z_axis.y * v) / magnitude,
                (frame.y_axis.z * u + frame.z_axis.z * v) / magnitude,
            )
        result.append(
            MultiRowPerBoltDemandVisualization(
                item.bolt_id,
                item.row_id,
                item.bolt_line_id,
                physical_bolt.display.center,
                item.direct_force.u,
                item.direct_force.v,
                item.moment_force.u,
                item.moment_force.v,
                item.total_force.u,
                item.total_force.v,
                item.total_force_magnitude,
                axis,
            )
        )
    return tuple(result)


def _automatic_demand(
    request: MultiRowOrchestrationRequest,
    resolved: _ResolvedMultiRow,
    bundle: MultiRowExecutionBundle,
) -> EccentricDemandResult:
    return calculate_eccentric_bolt_group_demand(_automatic_demand_input(request, resolved, bundle))


def _handoff_bundle_for_scenario(
    bundle: MultiRowExecutionBundle, scenario: DemandScenarioResult
) -> MultiRowExecutionBundle:
    """Use exact accepted parent magnitudes for the full-legacy execution path."""

    if scenario.residual_moment.magnitude != 0:
        return bundle
    by_bolt = {item.bolt_id: item.total_force_magnitude for item in scenario.per_bolt}
    return replace(
        bundle,
        bolts=tuple(replace(item, in_plane_demand=by_bolt[item.bolt_id]) for item in bundle.bolts),
    )


def _merged_group_mode_ids(
    results: tuple[EccentricGroupModeCompatibilityResult, ...], attribute: str
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            check_id
            for result in results
            for check_id in cast(tuple[str, ...], getattr(result, attribute))
        )
    )


def _group_mode_qualification(
    results: tuple[EccentricGroupModeCompatibilityResult, ...],
) -> QualificationDisposition:
    qualifications = {item.qualification for item in results}
    if QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED in qualifications:
        return QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if QualificationDisposition.ENGINEERING_REVIEW_REQUIRED in qualifications:
        return QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
    return QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE


def _integrate_group_mode_results(
    results: tuple[EccentricGroupModeCompatibilityResult, ...],
) -> AutomaticGroupModeIntegrationResult:
    if not results:
        raise ValueError("Automatic design requires at least one Stage 2.6A scenario result.")
    required = _merged_group_mode_ids(results, "required_check_ids")
    not_required = _merged_group_mode_ids(results, "not_required_check_ids")
    unsupported = _merged_group_mode_ids(results, "unsupported_required_check_ids")
    incomplete = _merged_group_mode_ids(results, "incomplete_required_check_ids")
    failed = _merged_group_mode_ids(results, "failed_check_ids")
    governing = _merged_group_mode_ids(results, "governing_supported_check_ids")
    qualification = _group_mode_qualification(results)
    if failed:
        numerical = NumericalComparison.FAIL
        overall = MultiRowOverallDisposition.FAIL
    elif any(
        item.overall_disposition is MultiRowOverallDisposition.INVALID_GEOMETRY for item in results
    ):
        numerical = NumericalComparison.NOT_EVALUATED
        overall = MultiRowOverallDisposition.INVALID_GEOMETRY
    elif (
        unsupported
        or incomplete
        or any(item.numerical_comparison is NumericalComparison.NOT_EVALUATED for item in results)
    ):
        numerical = NumericalComparison.NOT_EVALUATED
        overall = MultiRowOverallDisposition.NOT_EVALUATED
    elif qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED:
        numerical = NumericalComparison.PASS
        overall = MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    elif qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED:
        numerical = NumericalComparison.PASS
        overall = MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED
    else:
        numerical = NumericalComparison.PASS
        overall = MultiRowOverallDisposition.PASS
    payload = json.dumps(
        {
            "integration_contract_version": AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION,
            "scenario_results": [
                {
                    "scenario_id": item.scenario_id,
                    "input_fingerprint": item.input_fingerprint,
                    "result_fingerprint": item.result_fingerprint,
                }
                for item in results
            ],
            "required_check_ids": required,
            "not_required_check_ids": not_required,
            "unsupported_required_check_ids": unsupported,
            "incomplete_required_check_ids": incomplete,
            "failed_check_ids": failed,
            "qualification": qualification.value,
            "numerical_comparison": numerical.value,
            "governing_supported_check_ids": governing,
            "overall_disposition": overall.value,
            "trace_layers": AUTOMATIC_GROUP_MODE_TRACE_LAYERS,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return AutomaticGroupModeIntegrationResult(
        AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION,
        results,
        required,
        not_required,
        unsupported,
        incomplete,
        failed,
        qualification,
        numerical,
        governing,
        overall,
        AUTOMATIC_GROUP_MODE_TRACE_LAYERS,
        hashlib.sha256(payload.encode("ascii")).hexdigest(),
    )


def evaluate_multirow_connection(
    request: MultiRowOrchestrationRequest,
) -> MultiRowOrchestrationResponse:
    """Evaluate explicit demand or the accepted automatic 2.5A/2.5B/2.6A chain."""

    if request.single_row_geometry_preview_authorized:
        preview = preview_multirow_connection(request)
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
            preview.automatic_demand_result,
        )
    try:
        resolved = _resolve(request)
    except (ArithmeticError, TypeError, ValueError) as error:
        preview = _invalid_preview(request, str(error))
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
        )
    bundle = _execution_bundle(request, resolved)
    if request.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE:
        demand = _automatic_demand(request, resolved, bundle)
        preview = _preview_from_resolved(request, resolved, demand)
        if preview.geometry_status is GeometryStatus.INVALID_GEOMETRY:
            return MultiRowOrchestrationResponse(
                request.request_id,
                request.connection_id,
                MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
                preview,
                None,
                request.demand_source,
                demand,
            )
        axes = tuple(
            LayerBearingAxisContext(
                layer.layer_id,
                _layer_axis(source.material_axis_angle_degrees),
                layer.source_geometry_ids,
            )
            for source, layer in zip(request.layers, bundle.layers, strict=True)
        )
        explicit_axis = tuple(
            ExplicitBoltAxisDemand(
                item.bolt_id,
                item.demand,
                request.source_reference,
                "EXPLICIT_ACCEPTED_BOLT_AXIS_DEMAND",
                True,
            )
            for item in request.bolt_axis_tensions
        )
        handoff_inputs = tuple(
            EccentricResistanceHandoffInput(
                demand,
                scenario.scenario_id,
                _handoff_bundle_for_scenario(bundle, scenario),
                axes,
                explicit_axis,
                _block_shear_compatibility(request, resolved, bundle, demand, scenario),
                (
                    "DEMAND_ANALYSIS",
                    "COMPATIBILITY_HANDOFF",
                    "RESISTANCE_CALCULATION",
                ),
            )
            for scenario in demand.scenarios
        )
        handoffs = tuple(calculate_eccentric_resistance_handoff(item) for item in handoff_inputs)
        group_modes = tuple(
            calculate_eccentric_group_mode_compatibility(
                EccentricGroupModeCompatibilityInput(
                    handoff_input,
                    handoff_result,
                    AUTOMATIC_GROUP_MODE_TRACE_LAYERS,
                )
            )
            for handoff_input, handoff_result in zip(handoff_inputs, handoffs, strict=True)
        )
        integration = _integrate_group_mode_results(group_modes)
        legacy = next(
            (item.legacy_result for item in handoffs if item.legacy_result is not None),
            None,
        )
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            legacy,
            request.demand_source,
            demand,
            handoffs,
            integration,
        )
    preview = _preview_from_resolved(request, resolved, None)
    if preview.geometry_status is GeometryStatus.INVALID_GEOMETRY:
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
        )
    result = calculate_multirow_connection(bundle)
    return MultiRowOrchestrationResponse(
        request.request_id,
        request.connection_id,
        MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
        preview,
        result,
        request.demand_source,
    )


def evaluate_multirow_connection_with_resolved_demand(
    request: MultiRowOrchestrationRequest,
    demand: EccentricDemandResult,
    layer_demand_allocations: tuple[LayerInPlaneDemandAllocation, ...] = (),
) -> MultiRowOrchestrationResponse:
    """Run the accepted handoff/group-mode chain for an already resolved Stage 2.5A demand.

    Connector-family orchestration owns the physical interface frame and one canonical action.
    This shared seam prevents a family adapter from redistributing demand or duplicating the
    Stage 2.5B/2.6A integration while preserving the unchanged multi-row resistance engine.
    """

    if request.demand_source is not MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND:
        raise ValueError("Resolved-demand integration requires the explicit interface request.")
    if not isinstance(demand, EccentricDemandResult):
        raise TypeError("demand must be an EccentricDemandResult.")
    if demand.interface_frame.interface_id != request.interface_id:
        raise ValueError("Resolved demand and resistance request must identify one interface.")
    resolved = _resolve(request)
    bundle = _execution_bundle(request, resolved)
    preview = _preview_from_resolved(request, resolved, demand)
    axes = tuple(
        LayerBearingAxisContext(
            layer.layer_id,
            _layer_axis(source.material_axis_angle_degrees),
            layer.source_geometry_ids,
        )
        for source, layer in zip(request.layers, bundle.layers, strict=True)
    )
    handoff_inputs = tuple(
        EccentricResistanceHandoffInput(
            demand,
            scenario.scenario_id,
            _handoff_bundle_for_scenario(bundle, scenario),
            axes,
            (),
            _block_shear_compatibility(request, resolved, bundle, demand, scenario),
            (
                "DEMAND_ANALYSIS",
                "COMPATIBILITY_HANDOFF",
                "RESISTANCE_CALCULATION",
            ),
            layer_demand_allocations=layer_demand_allocations,
        )
        for scenario in demand.scenarios
    )
    handoffs = tuple(calculate_eccentric_resistance_handoff(item) for item in handoff_inputs)
    try:
        group_modes = tuple(
            calculate_eccentric_group_mode_compatibility(
                EccentricGroupModeCompatibilityInput(
                    handoff_input,
                    handoff_result,
                    AUTOMATIC_GROUP_MODE_TRACE_LAYERS,
                )
            )
            for handoff_input, handoff_result in zip(handoff_inputs, handoffs, strict=True)
        )
    except ValueError as error:
        if str(error) != "Each inter-row check must identify one unique physical bolt line.":
            raise
        integration = None
    else:
        integration = _integrate_group_mode_results(group_modes)
    legacy = next((item.legacy_result for item in handoffs if item.legacy_result is not None), None)
    return MultiRowOrchestrationResponse(
        request.request_id,
        request.connection_id,
        MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
        preview,
        legacy,
        request.demand_source,
        demand,
        handoffs,
        integration,
    )


def evaluate_multirow_connection_through_handoff(
    request: MultiRowOrchestrationRequest,
) -> MultiRowOrchestrationResponse:
    """Stop after the accepted Stage 2.5B handoff without claiming Stage 2.6A.

    Stage 3.2 uses this narrow fallback only when a physical two-layer interface
    does not satisfy the unchanged Stage 2.6A one-check-per-bolt-line contract.
    Existing evaluation routes and their result semantics are untouched.
    """

    if request.demand_source is not MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE:
        raise ValueError("Handoff-only evaluation requires automatic member-end demand.")
    if request.single_row_geometry_preview_authorized:
        preview = preview_multirow_connection(request)
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
            preview.automatic_demand_result,
        )
    try:
        resolved = _resolve(request)
    except (ArithmeticError, TypeError, ValueError) as error:
        preview = _invalid_preview(request, str(error))
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
        )
    bundle = _execution_bundle(request, resolved)
    demand = _automatic_demand(request, resolved, bundle)
    preview = _preview_from_resolved(request, resolved, demand)
    if preview.geometry_status is GeometryStatus.INVALID_GEOMETRY:
        return MultiRowOrchestrationResponse(
            request.request_id,
            request.connection_id,
            MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
            preview,
            None,
            request.demand_source,
            demand,
        )
    axes = tuple(
        LayerBearingAxisContext(
            layer.layer_id,
            _layer_axis(source.material_axis_angle_degrees),
            layer.source_geometry_ids,
        )
        for source, layer in zip(request.layers, bundle.layers, strict=True)
    )
    explicit_axis = tuple(
        ExplicitBoltAxisDemand(
            item.bolt_id,
            item.demand,
            request.source_reference,
            "EXPLICIT_ACCEPTED_BOLT_AXIS_DEMAND",
            True,
        )
        for item in request.bolt_axis_tensions
    )
    handoff_inputs = tuple(
        EccentricResistanceHandoffInput(
            demand,
            scenario.scenario_id,
            _handoff_bundle_for_scenario(bundle, scenario),
            axes,
            explicit_axis,
            _block_shear_compatibility(request, resolved, bundle, demand, scenario),
            (
                "DEMAND_ANALYSIS",
                "COMPATIBILITY_HANDOFF",
                "RESISTANCE_CALCULATION",
            ),
        )
        for scenario in demand.scenarios
    )
    handoffs = tuple(calculate_eccentric_resistance_handoff(item) for item in handoff_inputs)
    legacy = next((item.legacy_result for item in handoffs if item.legacy_result is not None), None)
    return MultiRowOrchestrationResponse(
        request.request_id,
        request.connection_id,
        MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
        preview,
        legacy,
        request.demand_source,
        demand,
        handoffs,
        None,
    )


__all__ = (
    "AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION",
    "AUTOMATIC_GROUP_MODE_TRACE_LAYERS",
    "MULTIROW_ORCHESTRATION_CONTRACT_VERSION",
    "MULTIROW_PREVIEW_SCHEMA_VERSION",
    "MULTIROW_VISUALIZATION_SCHEMA_VERSION",
    "AutomaticGroupModeIntegrationResult",
    "BoltAxisTensionInput",
    "EngineerDistributionKind",
    "EngineerRowAllocationInput",
    "MultiRowBoltVisualization",
    "MultiRowConnectionDemandVisualization",
    "MultiRowDemandSource",
    "MultiRowLayerInput",
    "MultiRowLayerVisualization",
    "MultiRowOrchestrationRequest",
    "MultiRowOrchestrationResponse",
    "MultiRowPathVisualization",
    "MultiRowPerBoltDemandVisualization",
    "MultiRowPhysicalBoltVisualization",
    "MultiRowPreviewResult",
    "MultiRowVisualizationSnapshot",
    "evaluate_multirow_connection",
    "evaluate_multirow_connection_through_handoff",
    "evaluate_multirow_connection_with_resolved_demand",
    "preview_multirow_connection",
)
