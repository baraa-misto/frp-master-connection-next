"""Canonical-object orchestration for the verified single-bolt calculation engine.

This module is an application boundary only.  It resolves exact domain and
geometry identities, adapts finite geometry scalars through the calculation
quantity bridge, builds the existing Stage 2.1A planning input, and delegates
all executable equations to the Stage 2.1B evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.actions import (
    ResolvedManualMemberEndAction,
    resolve_manual_member_end_action,
)
from frp_master_connection.calculation import (
    ASCE_74_23_EDITION,
    ASCE_74_23_ERRATUM,
    ASCE_74_23_STANDARD_NAME,
    CALCULATION_ENGINE_VERSION,
    ENGINEERING_RULE_SET_VERSION,
    AggregatePlanningStatus,
    ApplicabilityReasonCode,
    CalculationFingerprintInput,
    CalculationReadinessStatus,
    CodeGeometryValidation,
    DemandSourceKind,
    EndUseFactors,
    FastenerSnapshot,
    LapConfiguration,
    LayerPlanningInput,
    MaterialPropertySnapshot,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    PultrudedElementForm,
    QualificationStatus,
    ResolvedSingleBoltDemand,
    SingleBoltCalculationResult,
    SingleBoltPlanningInput,
    StandardHoleDefinition,
    ThreadStatus,
    TimeEffectFactor,
    Unit,
    calculate_single_bolt,
    calculation_fingerprint,
    create_lap_factor_plan,
    create_single_bolt_geometry_factor_plan,
    create_standard_hole,
    decimal_from_finite_real,
    resolve_geometry_to_code_mapping,
    validate_code_geometry,
)
from frp_master_connection.calculation.geometry_mapping import (
    GeometryToCodeMapping,
    GeometryToCodeMappingRequest,
)
from frp_master_connection.domain import (
    AssemblyMember,
    ComponentMaterialKind,
    ConnectorComponent,
    EngineeringUnitSystem,
    JointAssembly,
    LoadCombination,
    ParticipantKind,
    ParticipantReference,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
)
from frp_master_connection.geometry import (
    CartesianFrame3D,
    JointGeometryContext,
    MasterBoltCenter3D,
    ResolvedBoltGroupGeometry,
    ResolvedBoltPath,
    ResolvedPenetratedLayer,
    Vector3D,
    vector_between,
)
from frp_master_connection.version import PROJECT_SCHEMA_VERSION

CALCULATION_CONTRACT_VERSION = "2.1A-RC2"


class OrchestrationIssueCode(StrEnum):
    """Stable fail-closed issue identities emitted by the application service."""

    JOINT_CONTEXT_MISMATCH = "JOINT_CONTEXT_MISMATCH"
    INTERFACE_NOT_FOUND = "INTERFACE_NOT_FOUND"
    BOLT_GROUP_NOT_FOUND = "BOLT_GROUP_NOT_FOUND"
    BOLT_LOCATION_NOT_FOUND = "BOLT_LOCATION_NOT_FOUND"
    BOLT_PATH_NOT_FOUND = "BOLT_PATH_NOT_FOUND"
    LOAD_COMBINATION_NOT_FOUND = "LOAD_COMBINATION_NOT_FOUND"
    SOURCE_ACTION_NOT_FOUND = "SOURCE_ACTION_NOT_FOUND"
    RESOLVED_DEMAND_REQUIRED = "RESOLVED_DEMAND_REQUIRED"
    RESOLVED_DEMAND_CONFLICT = "RESOLVED_DEMAND_CONFLICT"
    PARTICIPANT_NOT_FOUND = "PARTICIPANT_NOT_FOUND"
    PHYSICAL_ELEMENT_NOT_FOUND = "PHYSICAL_ELEMENT_NOT_FOUND"
    MATERIAL_REGION_NOT_FOUND = "MATERIAL_REGION_NOT_FOUND"
    MATERIAL_ASSIGNMENT_MISSING = "MATERIAL_ASSIGNMENT_MISSING"
    MATERIAL_ASSIGNMENT_MISMATCH = "MATERIAL_ASSIGNMENT_MISMATCH"
    DUPLICATE_MATERIAL_ASSIGNMENT = "DUPLICATE_MATERIAL_ASSIGNMENT"
    MULTIPLE_MATERIAL_SNAPSHOTS_NOT_SUPPORTED = "MULTIPLE_MATERIAL_SNAPSHOTS_NOT_SUPPORTED"
    UNSUPPORTED_MATERIAL_KIND = "UNSUPPORTED_MATERIAL_KIND"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FASTENER_SOURCE_PENDING = "FASTENER_SOURCE_PENDING"
    BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED = "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED = "MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"


class ColumnFlangeConnectionSide(StrEnum):
    """Semantic side of the selected W-flange broad face."""

    EXTERIOR = "EXTERIOR"
    WEB_SIDE = "WEB_SIDE"


class AngleConnectedLeg(StrEnum):
    """Stable physical angle-leg identity selected for direct contact."""

    LEG_1 = "LEG_1"
    LEG_2 = "LEG_2"


class OutstandingLegSide(StrEnum):
    """Sign-stable outstanding-leg side in the resolved interface frame."""

    POSITIVE_INTERFACE_Z = "POSITIVE_INTERFACE_Z"
    NEGATIVE_INTERFACE_Z = "NEGATIVE_INTERFACE_Z"


class TemplateInterferenceClassification(StrEnum):
    """Narrow brace-to-W template interference classifications."""

    ANGLE_W_MEMBER_INTERFERENCE = "ANGLE_W_MEMBER_INTERFERENCE"


@dataclass(frozen=True, slots=True)
class TemplateInterference:
    """One canonical positive-volume overlap found by the template validator."""

    classification: TemplateInterferenceClassification
    first_participant_id: str
    first_physical_element_id: str
    second_participant_id: str
    second_physical_element_id: str
    interface_id: str
    message: str


@dataclass(frozen=True, slots=True)
class BraceToColumnOrientationContext:
    """Backend-resolved semantic orientation and selected physical contact identities."""

    connection_side: ColumnFlangeConnectionSide
    connected_leg: AngleConnectedLeg
    outstanding_leg_side: OutstandingLegSide
    flange_participant_id: str
    flange_physical_element_id: str
    flange_surface_id: str
    flange_surface_role: str
    angle_participant_id: str
    angle_surface_id: str
    angle_surface_role: str
    interface_id: str
    brace_to_column_angle_degrees: Decimal
    plan_angle_degrees: Decimal = Decimal(0)
    interference: tuple[TemplateInterference, ...] = ()


@dataclass(frozen=True, slots=True)
class OrchestrationIssue:
    """One deterministic engineering-resolution or readiness issue."""

    code: OrchestrationIssueCode
    message: str
    identities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, OrchestrationIssueCode):
            raise TypeError("OrchestrationIssue.code must be an OrchestrationIssueCode.")
        if not self.message.strip():
            raise ValueError("An orchestration issue requires a factual message.")
        if not isinstance(self.identities, tuple):
            raise TypeError("Orchestration issue identities must be an immutable tuple.")


@dataclass(frozen=True, slots=True)
class PenetratedLayerMaterialAssignment:
    """Explicit FRP snapshot and layer-specific metadata for one physical layer."""

    participant_id: str
    physical_element_id: str
    material_region_id: str
    material_snapshot: MaterialPropertySnapshot
    bearing_thread_status: ThreadStatus
    element_form: PultrudedElementForm
    potential_perpendicular_element_exemption: bool = False

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (
                self.participant_id,
                self.physical_element_id,
                self.material_region_id,
            )
        ):
            raise ValueError("Layer material-assignment identities must be nonempty.")
        if not isinstance(self.material_snapshot, MaterialPropertySnapshot):
            raise TypeError("material_snapshot must be a MaterialPropertySnapshot.")
        if not isinstance(self.bearing_thread_status, ThreadStatus):
            raise TypeError("bearing_thread_status must be a ThreadStatus.")
        if not isinstance(self.element_form, PultrudedElementForm):
            raise TypeError("element_form must be a PultrudedElementForm.")
        if not isinstance(self.potential_perpendicular_element_exemption, bool):
            raise TypeError("The perpendicular-element flag must be Boolean.")

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the exact participant/element/region assignment identity."""

        return (self.participant_id, self.physical_element_id, self.material_region_id)


@dataclass(frozen=True, slots=True)
class ExplicitBoltDemandAssignment:
    """Bind an approved resolved demand to one exact canonical bolt target."""

    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    demand: ResolvedSingleBoltDemand

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (self.interface_id, self.bolt_group_id, self.bolt_location_id)
        ):
            raise ValueError("Resolved-demand target identities must be nonempty.")
        if not isinstance(self.demand, ResolvedSingleBoltDemand):
            raise TypeError("demand must be a ResolvedSingleBoltDemand.")


@dataclass(frozen=True, slots=True)
class SingleBoltOrchestrationRequest:
    """Immutable canonical request for one selected logical bolt location."""

    calculation_id: str
    assembly: JointAssembly
    geometry_context: JointGeometryContext
    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    load_combination_id: str
    material_assignments: tuple[PenetratedLayerMaterialAssignment, ...]
    fastener_snapshot: FastenerSnapshot
    bolt_diameter: PhysicalQuantity
    published_code_unit_basis: PublishedCodeUnitBasis
    time_effect: TimeEffectFactor
    end_use_factors: EndUseFactors
    lap_configuration: LapConfiguration
    resolved_demand: ExplicitBoltDemandAssignment | None = None
    source_action_id: str | None = None
    whole_connection_requires_section_2_3_2: bool = False
    template_orientation: BraceToColumnOrientationContext | None = None
    calculation_contract_version: str = CALCULATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        identities = (
            self.calculation_id,
            self.interface_id,
            self.bolt_group_id,
            self.bolt_location_id,
            self.load_combination_id,
            self.calculation_contract_version,
        )
        if any(not value.strip() for value in identities):
            raise ValueError("Orchestration request identities must be nonempty.")
        if not isinstance(self.assembly, JointAssembly):
            raise TypeError("assembly must be a JointAssembly.")
        if not isinstance(self.geometry_context, JointGeometryContext):
            raise TypeError("geometry_context must be a JointGeometryContext.")
        if not isinstance(self.material_assignments, tuple):
            raise TypeError("material_assignments must be an immutable tuple.")
        if any(
            not isinstance(item, PenetratedLayerMaterialAssignment)
            for item in self.material_assignments
        ):
            raise TypeError("material_assignments contains an invalid item.")
        if not isinstance(self.fastener_snapshot, FastenerSnapshot):
            raise TypeError("fastener_snapshot must be a FastenerSnapshot.")
        if not isinstance(self.bolt_diameter, PhysicalQuantity):
            raise TypeError("bolt_diameter must be a PhysicalQuantity.")
        if self.bolt_diameter.dimension.value != "LENGTH" or self.bolt_diameter.magnitude <= 0:
            raise ValueError("bolt_diameter must be a positive length.")
        if not isinstance(self.published_code_unit_basis, PublishedCodeUnitBasis):
            raise TypeError("published_code_unit_basis must be a PublishedCodeUnitBasis.")
        if not isinstance(self.time_effect, TimeEffectFactor):
            raise TypeError("time_effect must be a TimeEffectFactor.")
        if not isinstance(self.end_use_factors, EndUseFactors):
            raise TypeError("end_use_factors must be EndUseFactors.")
        if not isinstance(self.lap_configuration, LapConfiguration):
            raise TypeError("lap_configuration must be a LapConfiguration.")
        if self.resolved_demand is not None and not isinstance(
            self.resolved_demand, ExplicitBoltDemandAssignment
        ):
            raise TypeError("resolved_demand must be an ExplicitBoltDemandAssignment.")
        if self.source_action_id is not None and not self.source_action_id.strip():
            raise ValueError("source_action_id must be nonempty when supplied.")
        if not isinstance(self.whole_connection_requires_section_2_3_2, bool):
            raise TypeError("The Section 2.3.2 qualification flag must be Boolean.")
        if self.template_orientation is not None and not isinstance(
            self.template_orientation, BraceToColumnOrientationContext
        ):
            raise TypeError("template_orientation must be a BraceToColumnOrientationContext.")


@dataclass(frozen=True, slots=True)
class SourceActionOrchestrationTrace:
    """Unshifted source-action provenance retained at the application boundary."""

    resolved_action: ResolvedManualMemberEndAction
    selected_bolt_center: MasterBoltCenter3D
    raw_source_to_bolt_offset: Vector3D
    automatic_moment_shift_applied: bool = False

    def __post_init__(self) -> None:
        if self.automatic_moment_shift_applied:
            raise ValueError("Stage 2.2A cannot apply an automatic moment shift.")


@dataclass(frozen=True, slots=True)
class ResolvedLayerOrchestrationTrace:
    """Ordered physical-layer identity and calculation mapping provenance."""

    layer_id: str
    participant: ParticipantReference
    physical_element_id: str
    material_region_id: str
    component_material_kind: ComponentMaterialKind
    entry_surface_patch_id: str
    exit_surface_patch_id: str
    connection_zone_ids: tuple[str, ...]
    hole_diameter: PhysicalQuantity
    material_assignment: PenetratedLayerMaterialAssignment | None
    code_mapping: GeometryToCodeMapping | None
    code_geometry_validation: CodeGeometryValidation | None


@dataclass(frozen=True, slots=True)
class SingleBoltOrchestrationResponse:
    """Deterministic application response suitable for a future serialization layer."""

    calculation_id: str
    assembly_id: str
    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    load_combination_id: str
    unit_system: EngineeringUnitSystem
    project_schema_version: str
    calculation_contract_version: str
    calculation_engine_version: str
    engineering_rule_set_version: str
    calculation_fingerprint: str | None
    load_combination: LoadCombination | None
    source_action_trace: SourceActionOrchestrationTrace | None
    resolved_demand: ExplicitBoltDemandAssignment | None
    resolved_layers: tuple[ResolvedLayerOrchestrationTrace, ...]
    material_assignments_used: tuple[PenetratedLayerMaterialAssignment, ...]
    fastener_snapshot: FastenerSnapshot
    calculation_result: SingleBoltCalculationResult | None
    aggregate_status: AggregatePlanningStatus | None
    governing_check_ids: tuple[str, ...]
    qualification_flags: tuple[QualificationStatus, ...]
    issues: tuple[OrchestrationIssue, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ResolvedTarget:
    interface_id: str
    group: ResolvedBoltGroupGeometry
    path: ResolvedBoltPath
    center: MasterBoltCenter3D
    load_combination: LoadCombination


def _issue(
    code: OrchestrationIssueCode,
    message: str,
    *identities: str,
) -> OrchestrationIssue:
    return OrchestrationIssue(code, message, tuple(identities))


def _deduplicate_issues(
    issues: list[OrchestrationIssue],
) -> tuple[OrchestrationIssue, ...]:
    seen: set[tuple[OrchestrationIssueCode, tuple[str, ...]]] = set()
    result: list[OrchestrationIssue] = []
    for issue in issues:
        key = (issue.code, issue.identities)
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return tuple(result)


def _length_unit(unit_system: EngineeringUnitSystem) -> Unit:
    return Unit.IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM


def _participant(
    assembly: JointAssembly,
    reference: ParticipantReference,
) -> AssemblyMember | ConnectorComponent | None:
    collection: tuple[AssemblyMember | ConnectorComponent, ...]
    if reference.kind is ParticipantKind.MEMBER:
        collection = assembly.members
    elif reference.kind is ParticipantKind.CONNECTOR_COMPONENT:
        collection = assembly.connector_components
    else:
        return None
    return next((item for item in collection if item.id == reference.entity_id), None)


def _resolve_target(
    request: SingleBoltOrchestrationRequest,
    issues: list[OrchestrationIssue],
) -> _ResolvedTarget | None:
    context = request.geometry_context
    if context.assembly is not request.assembly:
        issues.append(
            _issue(
                OrchestrationIssueCode.JOINT_CONTEXT_MISMATCH,
                "The supplied geometry context does not retain the exact supplied assembly.",
                request.assembly.id,
                context.assembly.id,
            )
        )
        return None
    interface = next(
        (item for item in request.assembly.interfaces if item.id == request.interface_id),
        None,
    )
    resolved_interface = next(
        (
            item
            for item in context.basis.resolved_interfaces
            if item.interface.id == request.interface_id
        ),
        None,
    )
    if (
        interface is None
        or resolved_interface is None
        or resolved_interface.interface is not interface
    ):
        issues.append(
            _issue(
                OrchestrationIssueCode.INTERFACE_NOT_FOUND,
                "The selected interface is not resolved by the supplied assembly context.",
                request.interface_id,
            )
        )
    logical_group = next(
        (item for item in request.assembly.bolt_groups if item.id == request.bolt_group_id),
        None,
    )
    resolved_group = next(
        (
            item
            for item in context.resolved_bolt_groups
            if item.bolt_group.id == request.bolt_group_id
        ),
        None,
    )
    if (
        logical_group is None
        or resolved_group is None
        or resolved_group.bolt_group is not logical_group
    ):
        issues.append(
            _issue(
                OrchestrationIssueCode.BOLT_GROUP_NOT_FOUND,
                "The selected bolt group is not resolved by the supplied assembly context.",
                request.bolt_group_id,
            )
        )
        return None
    logical_location = next(
        (item for item in logical_group.locations if item.id == request.bolt_location_id),
        None,
    )
    center = next(
        (
            item
            for item in resolved_group.master_centers
            if item.bolt_location.id == request.bolt_location_id
        ),
        None,
    )
    if logical_location is None or center is None or center.bolt_location is not logical_location:
        issues.append(
            _issue(
                OrchestrationIssueCode.BOLT_LOCATION_NOT_FOUND,
                "The selected bolt location does not belong to the selected bolt group.",
                request.bolt_location_id,
            )
        )
    path = next(
        (
            item
            for item in resolved_group.paths
            if item.definition.bolt_location_id == request.bolt_location_id
        ),
        None,
    )
    represented_interfaces = {
        zone.interface_id
        for candidate in resolved_group.paths
        if candidate.definition.bolt_location_id == request.bolt_location_id
        for layer in candidate.definition.layers
        for zone in layer.connection_zones
    }
    if path is None or request.interface_id not in represented_interfaces:
        issues.append(
            _issue(
                OrchestrationIssueCode.BOLT_PATH_NOT_FOUND,
                "The selected bolt path does not represent the selected interface.",
                request.bolt_location_id,
                request.interface_id,
            )
        )
    load = next(
        (
            item
            for item in request.assembly.load_combinations
            if item.id == request.load_combination_id
        ),
        None,
    )
    if load is None:
        issues.append(
            _issue(
                OrchestrationIssueCode.LOAD_COMBINATION_NOT_FOUND,
                "The selected load combination does not exist in the supplied assembly.",
                request.load_combination_id,
            )
        )
    if interface is None or center is None or path is None or load is None:
        return None
    return _ResolvedTarget(request.interface_id, resolved_group, path, center, load)


def _resolve_source_action(
    request: SingleBoltOrchestrationRequest,
    target: _ResolvedTarget,
    issues: list[OrchestrationIssue],
) -> SourceActionOrchestrationTrace | None:
    action_id = request.source_action_id
    if request.resolved_demand is not None:
        demand_action_id = request.resolved_demand.demand.source_action_id
        if action_id is None:
            action_id = demand_action_id
        elif action_id != demand_action_id:
            issues.append(
                _issue(
                    OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT,
                    "The declared source action conflicts with resolved-demand provenance.",
                    action_id,
                    demand_action_id,
                )
            )
            return None
    if action_id is None:
        return None
    action = next(
        (item for item in request.assembly.member_end_actions if item.id == action_id),
        None,
    )
    if action is None:
        issues.append(
            _issue(
                OrchestrationIssueCode.SOURCE_ACTION_NOT_FOUND,
                "The declared source action does not exist in the supplied assembly.",
                action_id,
            )
        )
        return None
    if action.load_combination_id != request.load_combination_id:
        issues.append(
            _issue(
                OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT,
                "The source action and selected load combination identities conflict.",
                action.id,
                request.load_combination_id,
            )
        )
        return None
    resolved = resolve_manual_member_end_action(request.geometry_context, action)
    return SourceActionOrchestrationTrace(
        resolved,
        target.center,
        vector_between(
            resolved.resolved_reference_point.global_position,
            target.center.global_position,
        ),
    )


def _validate_demand(
    request: SingleBoltOrchestrationRequest,
    issues: list[OrchestrationIssue],
) -> ResolvedSingleBoltDemand | None:
    assignment = request.resolved_demand
    if assignment is None:
        if request.source_action_id is None:
            issues.append(
                _issue(
                    OrchestrationIssueCode.RESOLVED_DEMAND_REQUIRED,
                    "Executable resistance requires an explicit resolved one-bolt demand.",
                    request.bolt_location_id,
                )
            )
        return None
    target_ids = (
        assignment.interface_id,
        assignment.bolt_group_id,
        assignment.bolt_location_id,
    )
    expected_ids = (request.interface_id, request.bolt_group_id, request.bolt_location_id)
    demand = assignment.demand
    action = next(
        (
            item
            for item in request.assembly.member_end_actions
            if item.id == demand.source_action_id
        ),
        None,
    )
    conflicts = (
        target_ids != expected_ids
        or demand.load_combination_id != request.load_combination_id
        or demand.source_kind is DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED
        or action is None
        or (action is not None and action.member_id != demand.source_member_id)
        or (action is not None and action.load_combination_id != demand.load_combination_id)
    )
    if conflicts:
        issues.append(
            _issue(
                OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT,
                "Resolved-demand target or source identities conflict with the canonical request.",
                demand.id,
            )
        )
        return None
    return demand


def _layer_key(layer: ResolvedPenetratedLayer) -> tuple[str, str, str]:
    return (
        layer.definition.participant.entity_id,
        layer.definition.physical_element_id,
        layer.physical_element.source_material_region.id,
    )


def _resolve_layer_assignments(
    request: SingleBoltOrchestrationRequest,
    target: _ResolvedTarget,
    issues: list[OrchestrationIssue],
) -> tuple[
    tuple[ResolvedPenetratedLayer, ...],
    tuple[PenetratedLayerMaterialAssignment, ...],
]:
    assignment_by_key: dict[tuple[str, str, str], PenetratedLayerMaterialAssignment] = {}
    for assignment in request.material_assignments:
        if assignment.key in assignment_by_key:
            issues.append(
                _issue(
                    OrchestrationIssueCode.DUPLICATE_MATERIAL_ASSIGNMENT,
                    "A penetrated-layer material assignment key is duplicated.",
                    *assignment.key,
                )
            )
        else:
            assignment_by_key[assignment.key] = assignment

    frp_layers: list[ResolvedPenetratedLayer] = []
    used: list[PenetratedLayerMaterialAssignment] = []
    used_keys: set[tuple[str, str, str]] = set()
    for layer in target.path.layers:
        definition = layer.definition
        component = _participant(request.assembly, definition.participant)
        if component is None:
            issues.append(
                _issue(
                    OrchestrationIssueCode.PARTICIPANT_NOT_FOUND,
                    "A penetrated-layer participant does not exist in the supplied assembly.",
                    definition.participant.entity_id,
                )
            )
            continue
        topology = component.section_topology
        if topology is None:
            issues.append(
                _issue(
                    OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND,
                    "A penetrated participant has no physical section topology.",
                    component.id,
                    definition.physical_element_id,
                )
            )
            continue
        element = next(
            (item for item in topology.elements if item.id == definition.physical_element_id),
            None,
        )
        if element is None or layer.physical_element.source_element is not element:
            issues.append(
                _issue(
                    OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND,
                    "A penetrated physical element does not resolve to the participant topology.",
                    component.id,
                    definition.physical_element_id,
                )
            )
            continue
        region = next(
            (item for item in topology.material_regions if item.id == element.material_region_id),
            None,
        )
        if region is None or layer.physical_element.source_material_region is not region:
            issues.append(
                _issue(
                    OrchestrationIssueCode.MATERIAL_REGION_NOT_FOUND,
                    "A penetrated physical element has no exact resolved material region.",
                    component.id,
                    element.id,
                )
            )
            continue
        if component.material_kind is ComponentMaterialKind.STEEL:
            continue
        if component.material_kind is not ComponentMaterialKind.PULTRUDED_FRP:
            issues.append(
                _issue(
                    OrchestrationIssueCode.UNSUPPORTED_MATERIAL_KIND,
                    "The penetrated layer material kind is not supported for FRP checks.",
                    component.id,
                    component.material_kind.value,
                )
            )
            continue
        key = _layer_key(layer)
        found_assignment = assignment_by_key.get(key)
        if found_assignment is None:
            issues.append(
                _issue(
                    OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISSING,
                    "An FRP penetrated layer lacks an explicit material assignment.",
                    *key,
                )
            )
            continue
        if not isinstance(region.orientation, PlanarFixedMaterialOrientation):
            issues.append(
                _issue(
                    OrchestrationIssueCode.INVALID_GEOMETRY,
                    "The initial orchestration release requires a planar fixed material region.",
                    component.id,
                    region.id,
                )
            )
            continue
        frp_layers.append(layer)
        used.append(found_assignment)
        used_keys.add(key)
    for assignment in request.material_assignments:
        if assignment.key not in used_keys:
            issues.append(
                _issue(
                    OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISMATCH,
                    "A material assignment does not match an FRP layer in the selected bolt path.",
                    *assignment.key,
                )
            )
    if used and any(item.material_snapshot != used[0].material_snapshot for item in used[1:]):
        issues.append(
            _issue(
                OrchestrationIssueCode.MULTIPLE_MATERIAL_SNAPSHOTS_NOT_SUPPORTED,
                "The verified Stage 2.1 engine accepts one material snapshot per invocation.",
                *(item.material_snapshot.id for item in used),
            )
        )
    return tuple(frp_layers), tuple(used)


def _raw_layer_trace(
    layer: ResolvedPenetratedLayer,
    unit: Unit,
    component_kind: ComponentMaterialKind,
    assignment: PenetratedLayerMaterialAssignment | None,
    mapping: GeometryToCodeMapping | None = None,
    validation: CodeGeometryValidation | None = None,
) -> ResolvedLayerOrchestrationTrace:
    return ResolvedLayerOrchestrationTrace(
        layer.definition.id,
        layer.definition.participant,
        layer.definition.physical_element_id,
        layer.physical_element.source_material_region.id,
        component_kind,
        layer.entry.surface.reference.patch_id,
        layer.exit.surface.reference.patch_id,
        tuple(zone.id for zone in layer.zones),
        PhysicalQuantity.from_finite_real(layer.definition.hole_diameter, unit),
        assignment,
        mapping,
        validation,
    )


def _fingerprint_physical_geometry(
    request: SingleBoltOrchestrationRequest,
    target: _ResolvedTarget,
    unit: Unit,
) -> object:
    return {
        "assembly_id": request.assembly.id,
        "interface_id": request.interface_id,
        "bolt_group_id": request.bolt_group_id,
        "bolt_location_id": request.bolt_location_id,
        "bolt_diameter": request.bolt_diameter,
        "ordered_layers": tuple(
            {
                "id": layer.definition.id,
                "participant_kind": layer.definition.participant.kind,
                "participant_id": layer.definition.participant.entity_id,
                "physical_element_id": layer.definition.physical_element_id,
                "material_region_id": layer.physical_element.source_material_region.id,
                "entry_surface_patch_id": layer.entry.surface.reference.patch_id,
                "exit_surface_patch_id": layer.exit.surface.reference.patch_id,
                "hole_diameter": PhysicalQuantity.from_finite_real(
                    layer.definition.hole_diameter, unit
                ),
                "raw_thickness": PhysicalQuantity.from_finite_real(layer.raw_thickness, unit),
            }
            for layer in target.path.layers
        ),
    }


def _fingerprint_code_mapping(mappings: tuple[GeometryToCodeMapping, ...]) -> object:
    return tuple(
        {
            "id": mapping.physical_element_id,
            "participant_id": mapping.participant_id,
            "material_region_id": mapping.material_region_id,
            "hole_diameter": mapping.hole_diameter,
            "layer_thickness": mapping.layer_thickness,
            "forward_e1": mapping.forward_e1,
            "reverse_end_distance": mapping.reverse_end_distance,
            "raw_side_distance_1": mapping.raw_side_distance_1,
            "raw_side_distance_2": mapping.raw_side_distance_2,
            "effective_width": mapping.effective_width,
            "theta_degrees": mapping.theta_degrees,
            "direction_family": mapping.direction_family,
            "direction_interpretation_id": mapping.direction_interpretation_id,
        }
        for mapping in mappings
    )


def _calculation_fingerprint(
    request: SingleBoltOrchestrationRequest,
    target: _ResolvedTarget,
    material: MaterialPropertySnapshot,
    demand: ResolvedSingleBoltDemand | object,
    mappings: tuple[GeometryToCodeMapping, ...],
    validations: tuple[CodeGeometryValidation, ...],
    assignments: tuple[PenetratedLayerMaterialAssignment, ...],
) -> str:
    unit = _length_unit(request.assembly.unit_system)
    interpretation_ids = tuple(
        sorted(
            {
                mapping.direction_interpretation_id
                for mapping in mappings
                if mapping.direction_interpretation_id is not None
            }
        )
    )
    geometry_factor = create_single_bolt_geometry_factor_plan()
    lap_factor = create_lap_factor_plan(request.lap_configuration)
    fingerprint_demand = (
        _canonical_fingerprint_demand(demand, request.assembly.unit_system)
        if isinstance(demand, ResolvedSingleBoltDemand)
        else demand
    )
    value = CalculationFingerprintInput(
        standard=ASCE_74_23_STANDARD_NAME,
        edition=ASCE_74_23_EDITION,
        errata=ASCE_74_23_ERRATUM,
        interpretation_ids=interpretation_ids,
        project_schema_version=PROJECT_SCHEMA_VERSION,
        calculation_contract_version=request.calculation_contract_version,
        calculation_engine_version=CALCULATION_ENGINE_VERSION,
        material_snapshot=material,
        fastener_snapshot=request.fastener_snapshot,
        physical_geometry=_fingerprint_physical_geometry(request, target, unit),
        code_variable_mapping=_fingerprint_code_mapping(mappings),
        demand=fingerprint_demand,
        factor_selections=(request.time_effect, request.end_use_factors, geometry_factor),
        lap_configuration=lap_factor,
        thread_statuses=(
            tuple(item.bearing_thread_status for item in assignments),
            request.fastener_snapshot.shear_plane_thread_statuses,
        ),
        published_code_unit_bases=(request.published_code_unit_basis,),
        readiness_decisions=(
            validations,
            request.whole_connection_requires_section_2_3_2,
        ),
    )
    return calculation_fingerprint(value)


def _canonical_fingerprint_demand(
    demand: ResolvedSingleBoltDemand,
    unit_system: EngineeringUnitSystem,
) -> ResolvedSingleBoltDemand:
    """Express exact demand vectors/points in canonical units for fingerprint equality."""

    length_unit = _length_unit(unit_system)

    def canonical_force(value: float) -> float:
        return float(
            PhysicalQuantity.from_finite_real(value, demand.force_vector_unit).to(Unit.N).magnitude
        )

    def canonical_length(value: float) -> float:
        return float(PhysicalQuantity.from_finite_real(value, length_unit).to(Unit.MM).magnitude)

    source_frame = demand.resolved_frame
    canonical_frame = CartesianFrame3D(
        PositionVector3D(
            canonical_length(source_frame.origin.x),
            canonical_length(source_frame.origin.y),
            canonical_length(source_frame.origin.z),
        ),
        source_frame.x_axis,
        source_frame.y_axis,
        source_frame.z_axis,
    )
    point = demand.resolved_global_reference_point
    return replace(
        demand,
        resolved_frame=canonical_frame,
        resolved_global_reference_point=PositionVector3D(
            canonical_length(point.x),
            canonical_length(point.y),
            canonical_length(point.z),
        ),
        in_plane_force_vector=Vector3D(
            canonical_force(demand.in_plane_force_vector.x),
            canonical_force(demand.in_plane_force_vector.y),
            canonical_force(demand.in_plane_force_vector.z),
        ),
        force_vector_unit=Unit.N,
        bolt_axis_tensile_demand=demand.bolt_axis_tensile_demand.to(Unit.N),
        externally_supplied_prying_demand=(demand.externally_supplied_prying_demand.to(Unit.N)),
    )


def _undistributed_action_payload(trace: SourceActionOrchestrationTrace) -> object:
    action = trace.resolved_action
    return {
        "id": action.action.id,
        "source_kind": "MEMBER_END_ACTION_UNDISTRIBUTED",
        "load_combination_id": action.load_combination.id,
        "member_id": action.member.id,
        "reference_point_kind": action.original_reference_point.kind,
        "reference_point_owner": action.original_reference_point.owner_id,
        "reference_point": {
            "x": decimal_from_finite_real(action.resolved_reference_point.global_position.x),
            "y": decimal_from_finite_real(action.resolved_reference_point.global_position.y),
            "z": decimal_from_finite_real(action.resolved_reference_point.global_position.z),
        },
        "global_force": {
            "x": decimal_from_finite_real(action.global_force.fx),
            "y": decimal_from_finite_real(action.global_force.fy),
            "z": decimal_from_finite_real(action.global_force.fz),
        },
        "global_moment": {
            "x": decimal_from_finite_real(action.global_moment.mx),
            "y": decimal_from_finite_real(action.global_moment.my),
            "z": decimal_from_finite_real(action.global_moment.mz),
        },
        "distribution_status": "UNRESOLVED",
        "automatic_moment_shift_applied": False,
    }


def _base_response(
    request: SingleBoltOrchestrationRequest,
    *,
    load: LoadCombination | None,
    source_action: SourceActionOrchestrationTrace | None,
    layers: tuple[ResolvedLayerOrchestrationTrace, ...] = (),
    assignments: tuple[PenetratedLayerMaterialAssignment, ...] = (),
    fingerprint: str | None = None,
    calculation: SingleBoltCalculationResult | None = None,
    aggregate: AggregatePlanningStatus | None = None,
    qualifications: tuple[QualificationStatus, ...] = (),
    issues: tuple[OrchestrationIssue, ...] = (),
) -> SingleBoltOrchestrationResponse:
    return SingleBoltOrchestrationResponse(
        calculation_id=request.calculation_id,
        assembly_id=request.assembly.id,
        interface_id=request.interface_id,
        bolt_group_id=request.bolt_group_id,
        bolt_location_id=request.bolt_location_id,
        load_combination_id=request.load_combination_id,
        unit_system=request.assembly.unit_system,
        project_schema_version=PROJECT_SCHEMA_VERSION,
        calculation_contract_version=request.calculation_contract_version,
        calculation_engine_version=CALCULATION_ENGINE_VERSION,
        engineering_rule_set_version=ENGINEERING_RULE_SET_VERSION,
        calculation_fingerprint=fingerprint,
        load_combination=load,
        source_action_trace=source_action,
        resolved_demand=request.resolved_demand,
        resolved_layers=layers,
        material_assignments_used=assignments,
        fastener_snapshot=request.fastener_snapshot,
        calculation_result=calculation,
        aggregate_status=aggregate,
        governing_check_ids=() if calculation is None else calculation.governing_check_ids,
        qualification_flags=qualifications,
        issues=issues,
        warnings=tuple(item.message for item in issues),
    )


def _result_issues(calculation: SingleBoltCalculationResult) -> tuple[OrchestrationIssue, ...]:
    issues: list[OrchestrationIssue] = []
    plans = calculation.planning_result.checks
    statuses = {plan.readiness_status for plan in plans}
    reasons = {reason for plan in plans for reason in plan.applicability_reason_codes}
    if CalculationReadinessStatus.INVALID_GEOMETRY in statuses:
        issues.append(_issue(OrchestrationIssueCode.INVALID_GEOMETRY, "Code geometry is invalid."))
    if CalculationReadinessStatus.SOURCE_DATA_PENDING in statuses:
        issues.append(
            _issue(
                OrchestrationIssueCode.FASTENER_SOURCE_PENDING,
                "The selected fastener snapshot lacks eligible bolt-strength source data.",
                calculation.results[0].plan.bolt_id,
            )
        )
    if ApplicabilityReasonCode.MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED in reasons:
        issues.append(
            _issue(
                OrchestrationIssueCode.MULTIPLE_SHEAR_PLANES_NOT_SUPPORTED,
                "The verified engine supports exactly one executable shear plane.",
            )
        )
    if CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED in statuses:
        issues.append(
            _issue(
                OrchestrationIssueCode.CALCULATION_NOT_SUPPORTED,
                "At least one required check is outside the verified calculation slice.",
            )
        )
    qualifications = {flag for plan in plans for flag in plan.qualification_flags}
    if (
        calculation.planning_result.whole_connection_status
        is CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
        or QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED in qualifications
    ):
        issues.append(
            _issue(
                OrchestrationIssueCode.SECTION_2_3_2_QUALIFICATION_REQUIRED,
                "Whole-connection Section 2.3.2 qualification remains required.",
            )
        )
    if QualificationStatus.ENGINEERING_REVIEW_REQUIRED in qualifications:
        issues.append(
            _issue(
                OrchestrationIssueCode.ENGINEERING_REVIEW_REQUIRED,
                "At least one selected engineering input remains review-required.",
            )
        )
    return _deduplicate_issues(issues)


def evaluate_single_bolt_connection(
    request: SingleBoltOrchestrationRequest,
) -> SingleBoltOrchestrationResponse:
    """Resolve one canonical bolt target and call the verified single-bolt engine."""

    if not isinstance(request, SingleBoltOrchestrationRequest):
        raise TypeError("request must be a SingleBoltOrchestrationRequest.")
    issues: list[OrchestrationIssue] = []
    if request.template_orientation is not None:
        issues.extend(
            _issue(
                OrchestrationIssueCode.INVALID_GEOMETRY,
                item.message,
                item.classification.value,
                item.interface_id,
                item.first_participant_id,
                item.first_physical_element_id,
                item.second_participant_id,
                item.second_physical_element_id,
            )
            for item in request.template_orientation.interference
        )
    target = _resolve_target(request, issues)
    if target is None:
        return _base_response(
            request,
            load=None,
            source_action=None,
            issues=_deduplicate_issues(issues),
        )
    source_action = _resolve_source_action(request, target, issues)
    demand = _validate_demand(request, issues)
    frp_layers, assignments = _resolve_layer_assignments(request, target, issues)
    fatal_codes = {
        OrchestrationIssueCode.JOINT_CONTEXT_MISMATCH,
        OrchestrationIssueCode.INTERFACE_NOT_FOUND,
        OrchestrationIssueCode.BOLT_GROUP_NOT_FOUND,
        OrchestrationIssueCode.BOLT_LOCATION_NOT_FOUND,
        OrchestrationIssueCode.BOLT_PATH_NOT_FOUND,
        OrchestrationIssueCode.LOAD_COMBINATION_NOT_FOUND,
        OrchestrationIssueCode.SOURCE_ACTION_NOT_FOUND,
        OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT,
        OrchestrationIssueCode.PARTICIPANT_NOT_FOUND,
        OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND,
        OrchestrationIssueCode.MATERIAL_REGION_NOT_FOUND,
        OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISSING,
        OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISMATCH,
        OrchestrationIssueCode.DUPLICATE_MATERIAL_ASSIGNMENT,
        OrchestrationIssueCode.MULTIPLE_MATERIAL_SNAPSHOTS_NOT_SUPPORTED,
        OrchestrationIssueCode.UNSUPPORTED_MATERIAL_KIND,
        OrchestrationIssueCode.INVALID_GEOMETRY,
    }
    unit = _length_unit(request.assembly.unit_system)
    assignment_by_key = {item.key: item for item in assignments}
    raw_traces = tuple(
        _raw_layer_trace(
            layer,
            unit,
            (
                component.material_kind
                if (component := _participant(request.assembly, layer.definition.participant))
                is not None
                else ComponentMaterialKind.OTHER
            ),
            assignment_by_key.get(_layer_key(layer)),
        )
        for layer in target.path.layers
    )
    if any(item.code in fatal_codes for item in issues):
        return _base_response(
            request,
            load=target.load_combination,
            source_action=source_action,
            layers=raw_traces,
            assignments=assignments,
            aggregate=(
                AggregatePlanningStatus.INVALID_GEOMETRY
                if any(item.code is OrchestrationIssueCode.INVALID_GEOMETRY for item in issues)
                else None
            ),
            issues=_deduplicate_issues(issues),
        )
    if not frp_layers or not assignments:
        issues.append(
            _issue(
                OrchestrationIssueCode.CALCULATION_NOT_SUPPORTED,
                "The selected bolt path contains no supported FRP calculation layer.",
            )
        )
        return _base_response(
            request,
            load=target.load_combination,
            source_action=source_action,
            layers=raw_traces,
            assignments=assignments,
            aggregate=AggregatePlanningStatus.CALCULATION_NOT_SUPPORTED,
            issues=_deduplicate_issues(issues),
        )
    material = assignments[0].material_snapshot
    if demand is None:
        if source_action is None:
            return _base_response(
                request,
                load=target.load_combination,
                source_action=None,
                layers=raw_traces,
                assignments=assignments,
                issues=_deduplicate_issues(issues),
            )
        issues.append(
            _issue(
                OrchestrationIssueCode.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED,
                "The member-end action remains undistributed and no resistance equation ran.",
                source_action.resolved_action.action.id,
                request.bolt_location_id,
            )
        )
        fingerprint = _calculation_fingerprint(
            request,
            target,
            material,
            _undistributed_action_payload(source_action),
            (),
            (),
            assignments,
        )
        return _base_response(
            request,
            load=target.load_combination,
            source_action=source_action,
            layers=raw_traces,
            assignments=assignments,
            fingerprint=fingerprint,
            aggregate=(AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED),
            issues=_deduplicate_issues(issues),
        )

    global_force = demand.resolved_frame.local_to_parent_vector(demand.in_plane_force_vector)
    mappings: list[GeometryToCodeMapping] = []
    validations: list[CodeGeometryValidation] = []
    planned_layers: list[LayerPlanningInput] = []
    all_holes = tuple(
        PhysicalQuantity.from_finite_real(layer.definition.hole_diameter, unit)
        for layer in target.path.layers
    )
    standard_hole: StandardHoleDefinition = create_standard_hole(
        request.bolt_diameter,
        request.published_code_unit_basis,
    )
    for layer, assignment in zip(frp_layers, assignments, strict=True):
        component = _participant(request.assembly, layer.definition.participant)
        if component is None or component.material_orientation is None:
            issues.append(
                _issue(
                    OrchestrationIssueCode.INVALID_GEOMETRY,
                    "An FRP layer lacks a resolved component lengthwise orientation.",
                    layer.definition.participant.entity_id,
                )
            )
            continue
        try:
            mapping = resolve_geometry_to_code_mapping(
                GeometryToCodeMappingRequest(
                    resolved_bolt_group=target.group,
                    bolt_location_id=request.bolt_location_id,
                    layer_id=layer.definition.id,
                    bolt_diameter=request.bolt_diameter,
                    signed_in_plane_force=global_force,
                    component_lengthwise_axis=component.material_orientation.lengthwise_axis,
                    source_length_unit=unit,
                )
            )
            # Stage 2.1 uses ``physical_element_id`` as its calculation-layer key.
            # Canonical paths can contain the same topology element ID on different
            # participants, so the authoritative path-layer ID is the collision-free
            # calculation key; the physical element ID remains unchanged in the
            # orchestration trace above.
            mapping = replace(mapping, physical_element_id=layer.definition.id)
            validation = validate_code_geometry(
                mapping=mapping,
                standard_hole=standard_hole,
                fastener=request.fastener_snapshot,
                washer=request.fastener_snapshot.washer_geometry,
                loading_sense=demand.loading_sense,
                connection_hole_diameters=all_holes,
                logical_bolt_count=1,
                row_count=1,
            )
        except (KeyError, TypeError, ValueError) as error:
            issues.append(
                _issue(
                    OrchestrationIssueCode.INVALID_GEOMETRY,
                    str(error),
                    layer.definition.id,
                )
            )
            continue
        mappings.append(mapping)
        validations.append(validation)
        planned_layers.append(
            LayerPlanningInput(
                mapping,
                validation,
                assignment.bearing_thread_status,
                assignment.potential_perpendicular_element_exemption,
                assignment.element_form,
            )
        )
    if len(planned_layers) != len(frp_layers):
        return _base_response(
            request,
            load=target.load_combination,
            source_action=source_action,
            layers=raw_traces,
            assignments=assignments,
            issues=_deduplicate_issues(issues),
        )
    mapping_tuple = tuple(mappings)
    validation_tuple = tuple(validations)
    fingerprint = _calculation_fingerprint(
        request,
        target,
        material,
        demand,
        mapping_tuple,
        validation_tuple,
        assignments,
    )
    planning_input = SingleBoltPlanningInput(
        connection_id=request.interface_id,
        bolt_id=request.bolt_location_id,
        demand=demand,
        layers=tuple(planned_layers),
        material=material,
        fastener=request.fastener_snapshot,
        washer=request.fastener_snapshot.washer_geometry,
        time_effect=request.time_effect,
        end_use_factors=request.end_use_factors,
        lap_factor=create_lap_factor_plan(request.lap_configuration),
        geometry_factor=create_single_bolt_geometry_factor_plan(),
        input_fingerprint=fingerprint,
        whole_connection_requires_section_2_3_2=(request.whole_connection_requires_section_2_3_2),
    )
    calculation = calculate_single_bolt(planning_input)
    result_issues = _result_issues(calculation)
    qualifications = tuple(
        sorted(
            {
                flag
                for plan in calculation.planning_result.checks
                for flag in plan.qualification_flags
            },
            key=lambda item: item.value,
        )
    )
    trace_by_key = {
        _layer_key(layer): (mapping, validation)
        for layer, mapping, validation in zip(
            frp_layers,
            mapping_tuple,
            validation_tuple,
            strict=True,
        )
    }
    final_traces = tuple(
        _raw_layer_trace(
            layer,
            unit,
            (
                component.material_kind
                if (component := _participant(request.assembly, layer.definition.participant))
                is not None
                else ComponentMaterialKind.OTHER
            ),
            assignment_by_key.get(_layer_key(layer)),
            *(trace_by_key.get(_layer_key(layer), (None, None))),
        )
        for layer in target.path.layers
    )
    return _base_response(
        request,
        load=target.load_combination,
        source_action=source_action,
        layers=final_traces,
        assignments=assignments,
        fingerprint=fingerprint,
        calculation=calculation,
        aggregate=calculation.aggregate_status,
        qualifications=qualifications,
        issues=_deduplicate_issues([*issues, *result_issues]),
    )


__all__ = (
    "CALCULATION_CONTRACT_VERSION",
    "ExplicitBoltDemandAssignment",
    "OrchestrationIssue",
    "OrchestrationIssueCode",
    "PenetratedLayerMaterialAssignment",
    "ResolvedLayerOrchestrationTrace",
    "SingleBoltOrchestrationRequest",
    "SingleBoltOrchestrationResponse",
    "SourceActionOrchestrationTrace",
    "evaluate_single_bolt_connection",
)
