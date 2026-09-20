"""Stage 3.4A backend-authoritative Multi-Member Tee orchestration.

The service composes existing Tee geometry and Stage 2 demand/resistance seams.  It
adds only slot aggregation, physical cross-slot validation, and exact support-wrench
assembly; it introduces no demand or resistance equation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, localcontext
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.application.calculation_orchestration import (
    SingleBoltOrchestrationRequest,
)
from frp_master_connection.application.connection_preview import (
    preview_single_bolt_connection,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationRequest,
    MultiRowOrchestrationResponse,
    MultiRowPreviewResult,
    preview_multirow_connection,
)
from frp_master_connection.application.tee_orchestration import (
    TEE_R2_VISUALIZATION_SCHEMA_VERSION,
    TeeConnectedMemberProfileTrace,
    TeeConnectorOrchestrationRequest,
    TeeInterfacePlacementTrace,
    TeeLongitudinalPlacementTrace,
    TeeMemberEndTrimTrace,
    TeeResolvedAssembly,
    TeeSupportProfileTrace,
    TeeVectorInput,
    TeeVisualizationSnapshot,
    evaluate_tee_interface,
    expand_tee_bolts,
    resolve_tee_connector_request,
    tee_fixed_grid_geometry_preview,
    tee_interface_failed,
    trim_tee_visualization,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    DemandAnalysisAvailability,
    Dimension,
    EccentricDemandInput,
    EccentricDemandResult,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
    GeometryStatus,
    MethodProvenance,
    MultiRowBoltGeometryContext,
    MultiRowDemandPlan,
    MultiRowMethodApplicability,
    MultiRowPhysicalGeometryContext,
    MultiRowProjectedGroupContext,
    PerBoltDemandPlan,
    PhysicalQuantity,
    PlanAvailability,
    QualificationDisposition,
    RowDemandPlan,
    RowDemandScenario,
    RowDistributionBasis,
    Unit,
    calculate_eccentric_bolt_group_demand,
    canonical_decimal_string,
    create_standard_hole,
    decimal_from_finite_real,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.domain import (
    AngleProfileDimensions,
    EngineeringUnitSystem,
    MemberProfile,
    TeeConnectorDimensions,
    WideFlangeIProfileDimensions,
)
from frp_master_connection.domain.multi_member_tee import (
    MultiMemberTeeSlot,
    MultiMemberTeeSlotId,
    MultiMemberTeeSlotSet,
)

MULTI_MEMBER_TEE_ORCHESTRATION_CONTRACT_VERSION = "3.4A-RC1"
MULTI_MEMBER_TEE_EXPANDED_ORCHESTRATION_CONTRACT_VERSION = "3.4B-RC1"
_SUPPORTED_ORCHESTRATION_CONTRACT_VERSIONS = frozenset(
    {
        MULTI_MEMBER_TEE_ORCHESTRATION_CONTRACT_VERSION,
        MULTI_MEMBER_TEE_EXPANDED_ORCHESTRATION_CONTRACT_VERSION,
    }
)
MULTI_MEMBER_TEE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
MULTI_MEMBER_TEE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"

TEE_CONNECTOR_BODY_RESISTANCE = "TEE_CONNECTOR_BODY_RESISTANCE"
MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY = (
    "MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY"
)
_REQUIRED_LIMITATIONS = (
    TEE_CONNECTOR_BODY_RESISTANCE,
    MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY,
)
RHS_LOCAL_WALL_RESPONSE = "RHS_LOCAL_WALL_RESPONSE"
RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT = "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT"
SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY = (
    "SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY"
)


class MultiMemberTeeAssemblyStatus(StrEnum):
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    NOT_EVALUATED = "NOT_EVALUATED"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class NodeVectorInput:
    """Exact semantic H_T/V_T/N_T vector."""

    h: PhysicalQuantity
    v: PhysicalQuantity
    n: PhysicalQuantity

    def __post_init__(self) -> None:
        if any(not isinstance(item, PhysicalQuantity) for item in (self.h, self.v, self.n)):
            raise TypeError("Node vector components must be PhysicalQuantity values.")
        if len({self.h.dimension, self.v.dimension, self.n.dimension}) != 1:
            raise ValueError("Node vector components must share one dimension.")

    def to(self, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
        return (
            self.h.to(unit).magnitude,
            self.v.to(unit).magnitude,
            self.n.to(unit).magnitude,
        )


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlotAction:
    force: NodeVectorInput
    moment: NodeVectorInput
    reference_point: NodeVectorInput

    def __post_init__(self) -> None:
        if self.force.h.dimension is not Dimension.FORCE:
            raise ValueError("Slot force must contain force quantities.")
        if self.moment.h.dimension is not Dimension.MOMENT:
            raise ValueError("Slot moment must contain moment quantities.")
        if self.reference_point.h.dimension is not Dimension.LENGTH:
            raise ValueError("Slot reference_point must contain length quantities.")


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlotRequest:
    slot: MultiMemberTeeSlot
    action: MultiMemberTeeSlotAction
    tee_request: TeeConnectorOrchestrationRequest

    def __post_init__(self) -> None:
        if not isinstance(self.slot, MultiMemberTeeSlot):
            raise TypeError("slot must be a MultiMemberTeeSlot.")
        if not isinstance(self.action, MultiMemberTeeSlotAction):
            raise TypeError("action must be a MultiMemberTeeSlotAction.")
        if not isinstance(self.tee_request, TeeConnectorOrchestrationRequest):
            raise TypeError("tee_request must be a TeeConnectorOrchestrationRequest.")
        if self.tee_request.connected_member_profile != self.slot.profile:
            raise ValueError("The compatibility Tee request must use the slot profile.")
        if self.tee_request.brace_inclination_degrees != self.slot.inclination_degrees:
            raise ValueError("The compatibility Tee request must use the slot inclination.")


@dataclass(frozen=True, slots=True)
class MultiMemberTeeOrchestrationRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    connector_dimensions: TeeConnectorDimensions
    slots: tuple[MultiMemberTeeSlotRequest, ...]
    support_reference_point: NodeVectorInput
    orchestration_contract_version: str = MULTI_MEMBER_TEE_ORCHESTRATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be nonempty text.")
        if self.orchestration_contract_version not in _SUPPORTED_ORCHESTRATION_CONTRACT_VERSIONS:
            raise ValueError("Unsupported Multi-Member Tee orchestration contract version.")
        if not isinstance(self.unit_system, EngineeringUnitSystem):
            raise TypeError("unit_system must be an EngineeringUnitSystem.")
        expected = Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        if self.source_length_unit is not expected:
            raise ValueError("source_length_unit must match unit_system.")
        if not isinstance(self.connector_dimensions, TeeConnectorDimensions):
            raise TypeError("connector_dimensions must be TeeConnectorDimensions.")
        if not isinstance(self.slots, tuple) or any(
            not isinstance(item, MultiMemberTeeSlotRequest) for item in self.slots
        ):
            raise TypeError("slots must be an immutable tuple of slot requests.")
        MultiMemberTeeSlotSet(tuple(item.slot for item in self.slots))
        if self.support_reference_point.h.dimension is not Dimension.LENGTH:
            raise ValueError("support_reference_point must contain lengths.")
        for item in self.slots:
            source = item.tee_request
            if (
                source.unit_system is not self.unit_system
                or source.source_length_unit is not self.source_length_unit
                or source.connector_dimensions != self.connector_dimensions
            ):
                raise ValueError("Every active slot must share the node unit and Tee geometry.")


@dataclass(frozen=True, slots=True)
class SupportWrenchContribution:
    slot_id: MultiMemberTeeSlotId
    force: NodeVectorInput
    free_moment: NodeVectorInput
    source_reference_point: NodeVectorInput
    support_reference_point: NodeVectorInput
    shift_arm: NodeVectorInput
    shifted_moment: NodeVectorInput
    contribution_moment: NodeVectorInput
    action_fingerprint: str


@dataclass(frozen=True, slots=True)
class AssembledSupportWrench:
    force: NodeVectorInput
    moment: NodeVectorInput
    reference_point: NodeVectorInput
    contributions: tuple[SupportWrenchContribution, ...]
    force_equilibrium: bool
    moment_equilibrium: bool
    wrench_fingerprint: str
    application_provenance_fingerprint: str


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlotVisualization:
    slot_id: MultiMemberTeeSlotId
    connected_member_id: str
    bolt_group_id: str
    visualization: TeeVisualizationSnapshot


@dataclass(frozen=True, slots=True)
class MultiMemberTeeVisualizationSnapshot:
    schema_version: str
    slots: tuple[MultiMemberTeeSlotVisualization, ...]
    semantic_h_axis: tuple[Decimal, Decimal, Decimal]
    semantic_v_axis: tuple[Decimal, Decimal, Decimal]
    semantic_n_axis: tuple[Decimal, Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlotResult:
    slot_id: MultiMemberTeeSlotId
    connected_role: str
    connected_member_id: str
    bolt_group_id: str
    profile: TeeConnectedMemberProfileTrace | None
    trim: TeeMemberEndTrimTrace | None
    placement: TeeInterfacePlacementTrace | None
    preview: MultiRowPreviewResult | None
    design: MultiRowOrchestrationResponse | None
    action: MultiMemberTeeSlotAction
    geometry_fingerprint: str
    interface_fingerprint: str
    action_fingerprint: str
    normal_action_retained: bool
    automatic_axis_tension_generated: bool = False


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSupportResult:
    bolt_group_id: str
    profile: TeeSupportProfileTrace | None
    placement: TeeInterfacePlacementTrace | None
    preview: MultiRowPreviewResult | None
    design: MultiRowOrchestrationResponse | None
    interface_fingerprint: str


@dataclass(frozen=True, slots=True)
class MultiMemberTeePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    assembly_status: MultiMemberTeeAssemblyStatus
    active_slot_ids: tuple[MultiMemberTeeSlotId, ...]
    slots: tuple[MultiMemberTeeSlotResult, ...]
    support: MultiMemberTeeSupportResult
    support_wrench: AssembledSupportWrench
    tee_longitudinal_placement: TeeLongitudinalPlacementTrace | None
    required_limitations: tuple[str, ...]
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    warnings: tuple[str, ...]
    input_fingerprint: str
    engineering_fingerprint: str
    visualization: MultiMemberTeeVisualizationSnapshot | None


@dataclass(frozen=True, slots=True)
class MultiMemberTeeDesignResult:
    preview: MultiMemberTeePreviewResult
    assembly_status: MultiMemberTeeAssemblyStatus
    slots: tuple[MultiMemberTeeSlotResult, ...]
    support: MultiMemberTeeSupportResult
    required_limitations: tuple[str, ...]
    ordinary_pass_allowed: bool
    supported_failure_present: bool
    result_fingerprint: str


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _quantity_vector(
    values: tuple[Decimal, Decimal, Decimal],
    unit: Unit,
) -> NodeVectorInput:
    return NodeVectorInput(*(PhysicalQuantity.of(item, unit) for item in values))


def _cross(
    left: tuple[Decimal, Decimal, Decimal],
    right: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def assemble_support_wrench(
    slots: tuple[MultiMemberTeeSlotRequest, ...],
    support_reference_point: NodeVectorInput,
    unit_system: EngineeringUnitSystem,
) -> AssembledSupportWrench:
    """Shift and sum complete member-on-connection wrenches with Decimal arithmetic."""

    force_unit = Unit.KIP if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = Unit.KIP_IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    length_unit = Unit.IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
    support_reference = support_reference_point.to(length_unit)
    contributions: list[SupportWrenchContribution] = []
    with localcontext() as context:
        context.prec = 50
        force_sum = [Decimal(0), Decimal(0), Decimal(0)]
        moment_sum = [Decimal(0), Decimal(0), Decimal(0)]
        for item in slots:
            force = item.action.force.to(force_unit)
            free_moment = item.action.moment.to(moment_unit)
            source_reference = item.action.reference_point.to(length_unit)
            arm = tuple(
                source - target
                for source, target in zip(source_reference, support_reference, strict=True)
            )
            shifted = _cross(cast(tuple[Decimal, Decimal, Decimal], arm), force)
            contribution = tuple(
                free + shift for free, shift in zip(free_moment, shifted, strict=True)
            )
            for index in range(3):
                force_sum[index] += force[index]
                moment_sum[index] += contribution[index]
            action_fingerprint = _fingerprint(
                (
                    item.slot.slot_id,
                    item.action.force,
                    item.action.moment,
                    item.action.reference_point,
                )
            )
            contributions.append(
                SupportWrenchContribution(
                    item.slot.slot_id,
                    _quantity_vector(force, force_unit),
                    _quantity_vector(free_moment, moment_unit),
                    _quantity_vector(source_reference, length_unit),
                    _quantity_vector(support_reference, length_unit),
                    _quantity_vector(cast(tuple[Decimal, Decimal, Decimal], arm), length_unit),
                    _quantity_vector(shifted, moment_unit),
                    _quantity_vector(
                        cast(tuple[Decimal, Decimal, Decimal], contribution), moment_unit
                    ),
                    action_fingerprint,
                )
            )
    force_result = _quantity_vector(
        cast(tuple[Decimal, Decimal, Decimal], tuple(force_sum)), force_unit
    )
    moment_result = _quantity_vector(
        cast(tuple[Decimal, Decimal, Decimal], tuple(moment_sum)), moment_unit
    )
    wrench_identity = (force_result, moment_result, support_reference_point)
    provenance = tuple(
        (item.slot_id, item.action_fingerprint, item.contribution_moment) for item in contributions
    )
    return AssembledSupportWrench(
        force_result,
        moment_result,
        support_reference_point,
        tuple(contributions),
        True,
        True,
        _fingerprint(wrench_identity),
        _fingerprint((wrench_identity, provenance)),
    )


def _semantic_to_world(value: NodeVectorInput) -> TeeVectorInput:
    """Map H_T/V_T/N_T to the accepted W-column Tee world basis."""

    return TeeVectorInput(value.h, PhysicalQuantity.of(-value.n.magnitude, value.n.unit), value.v)


def _slot_hole_centers(slot: MultiMemberTeeSlot) -> tuple[tuple[Decimal, Decimal], ...]:
    layout = slot.bolt_layout
    return tuple(
        (
            slot.anchor_h - layout.line_span / Decimal(2) + Decimal(line) * layout.gauge,
            slot.anchor_v - layout.row_span / Decimal(2) + Decimal(row) * layout.pitch,
        )
        for row in range(layout.row_count)
        for line in range(layout.bolts_per_row)
    )


def _exact_vector(values: NodeVectorInput, unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity.of(item, unit) for item in values.to(unit)))


def _node_demand(
    *,
    group_id: str,
    interface_id: str,
    slot: MultiMemberTeeSlot,
    action: MultiMemberTeeSlotAction,
    bolt_diameter: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    unit_system: EngineeringUnitSystem,
) -> EccentricDemandResult:
    """Invoke the accepted Stage 2.5A engine on the Tee-fixed semantic H/V grid."""

    length_unit = Unit.IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
    force_unit = Unit.KIP if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = Unit.KIP_IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    centers = _slot_hole_centers(slot)
    bolts = tuple(
        MultiRowBoltGeometryContext(
            f"{group_id}:R{row + 1}:L{line + 1}",
            h,
            v,
            bolt_diameter.to(length_unit).magnitude,
            hole_diameter.to(length_unit).magnitude,
            "ASTM_F593_17_GROUP_2_316_316L",
            "MULTI_MEMBER_TEE_NODE",
        )
        for row in range(slot.bolt_layout.row_count)
        for line in range(slot.bolt_layout.bolts_per_row)
        for h, v in (centers[row * slot.bolt_layout.bolts_per_row + line],)
    )
    rows = tuple(
        MultiRowProjectedGroupContext(
            f"{group_id}:ROW_{row + 1}",
            row + 1,
            slot.anchor_v
            - slot.bolt_layout.row_span / Decimal(2)
            + Decimal(row) * slot.bolt_layout.pitch,
            Decimal(0),
            tuple(
                f"{group_id}:R{row + 1}:L{line + 1}"
                for line in range(slot.bolt_layout.bolts_per_row)
            ),
        )
        for row in range(slot.bolt_layout.row_count)
    )
    lines = tuple(
        MultiRowProjectedGroupContext(
            f"{group_id}:LINE_{line + 1}",
            line + 1,
            slot.anchor_h
            - slot.bolt_layout.line_span / Decimal(2)
            + Decimal(line) * slot.bolt_layout.gauge,
            Decimal(0),
            tuple(
                f"{group_id}:R{row + 1}:L{line + 1}" for row in range(slot.bolt_layout.row_count)
            ),
        )
        for line in range(slot.bolt_layout.bolts_per_row)
    )
    geometry = MultiRowPhysicalGeometryContext(
        group_id,
        interface_id,
        "TEE_STEM_FINITE_BOUNDARY",
        length_unit,
        (Decimal(1), Decimal(0)),
        (Decimal(0), Decimal(1)),
        bolts,
        rows,
        lines,
        min(item[0] for item in centers) - slot.bolt_layout.gauge,
        max(item[0] for item in centers) + slot.bolt_layout.gauge,
        min(item[1] for item in centers) - slot.bolt_layout.pitch,
        max(item[1] for item in centers) + slot.bolt_layout.pitch,
        Decimal("0.000000001"),
    )
    force_h, force_v, _force_n = action.force.to(force_unit)
    total = PhysicalQuantity.of((force_h**2 + force_v**2).sqrt(), force_unit)
    provenance = MethodProvenance(
        "STAGE_3_4A_ASCE_ROW_DISTRIBUTION",
        "STAGE_3_4A_MULTI_MEMBER_TEE_NODE_ENGINEERING_SPECIFICATION_RC1",
        "RC1",
        "MULTI_MEMBER_TEE_ACTION",
        "EXACT_SLOT_REFERENCE_POINT",
        False,
        True,
    )
    prescribed = slot.bolt_layout.row_count in {2, 3}
    fractions = (
        prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, slot.bolt_layout.row_count)
        if prescribed
        else tuple(
            Decimal(1) / Decimal(slot.bolt_layout.row_count)
            for _ in range(slot.bolt_layout.row_count)
        )
    )
    row_plans = tuple(
        RowDemandPlan(
            row.id,
            total * fractions[index],
            fractions[index],
            tuple(
                PerBoltDemandPlan(
                    bolt_id,
                    total * fractions[index] / Decimal(slot.bolt_layout.bolts_per_row),
                )
                for bolt_id in row.bolt_ids
            ),
        )
        for index, row in enumerate(rows)
    )
    basis = (
        RowDistributionBasis.ASCE_PRESCRIBED
        if prescribed
        else RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION
    )
    plan = MultiRowDemandPlan(
        basis,
        total,
        (RowDemandScenario(basis.value, None, row_plans),),
        PlanAvailability.READY,
        provenance,
        (),
    )
    zero_moment = ExactQuantityVector3D(
        PhysicalQuantity.of(Decimal(0), moment_unit),
        PhysicalQuantity.of(Decimal(0), moment_unit),
        PhysicalQuantity.of(Decimal(0), moment_unit),
    )
    return calculate_eccentric_bolt_group_demand(
        EccentricDemandInput(
            f"{group_id}:ACTION",
            f"{group_id}:MEMBER",
            _exact_vector(action.force, force_unit),
            _exact_vector(action.moment, moment_unit),
            zero_moment,
            _exact_vector(action.reference_point, length_unit),
            ExactInterfaceFrame(
                interface_id,
                ExactQuantityVector3D(
                    PhysicalQuantity.of(Decimal(0), length_unit),
                    PhysicalQuantity.of(Decimal(0), length_unit),
                    PhysicalQuantity.of(Decimal(0), length_unit),
                ),
                (Decimal(1), Decimal(0), Decimal(0)),
                (Decimal(0), Decimal(1), Decimal(0)),
                (Decimal(0), Decimal(0), Decimal(1)),
            ),
            geometry,
            plan,
            (
                MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
                if prescribed
                else MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE
            ),
            (
                QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
                if prescribed
                else QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
            ),
            (
                f"slot:{slot.slot_id.value}",
                "Stage 2.5A exact eccentric bolt-group demand",
                "Stage 3.4A Tee-fixed semantic H/V frame",
            ),
        )
    )


def _cross_group_overlap(request: MultiMemberTeeOrchestrationRequest) -> bool:
    first = request.slots[0].tee_request
    hole = create_standard_hole(first.bolt_diameter, first.hole_basis)
    diameter = hole.hole_diameter.to(request.source_length_unit).magnitude
    for left_index, left in enumerate(request.slots):
        for right in request.slots[left_index + 1 :]:
            if any(
                (left_h - right_h) ** 2 + (left_v - right_v) ** 2 < diameter**2
                for left_h, left_v in _slot_hole_centers(left.slot)
                for right_h, right_v in _slot_hole_centers(right.slot)
            ):
                return True
    return False


def _member_polygon(slot: MultiMemberTeeSlot) -> tuple[tuple[float, float], ...]:
    dimensions = slot.profile.dimensions
    if isinstance(dimensions, AngleProfileDimensions):
        width = max(dimensions.leg_y, dimensions.leg_z)
    elif isinstance(dimensions, WideFlangeIProfileDimensions):
        width = max(dimensions.depth, dimensions.flange_width)
    else:
        candidates = tuple(
            value
            for name in ("width", "depth", "flange_width")
            if isinstance((value := getattr(dimensions, name, None)), Decimal)
        )
        if not candidates:  # pragma: no cover - the six-family profile union is closed
            raise TypeError("Unsupported Multi-Member Tee profile dimensions.")
        width = max(candidates)
    length = dimensions.member_length
    sine, cosine = deterministic_sine_cosine_degrees(slot.inclination_degrees)
    tangent = (cosine, sine)
    across = (-sine, cosine)
    anchor = (float(slot.anchor_h), float(slot.anchor_v))
    half = float(width) / 2.0
    end = (anchor[0] + tangent[0] * float(length), anchor[1] + tangent[1] * float(length))
    return (
        (anchor[0] + across[0] * half, anchor[1] + across[1] * half),
        (end[0] + across[0] * half, end[1] + across[1] * half),
        (end[0] - across[0] * half, end[1] - across[1] * half),
        (anchor[0] - across[0] * half, anchor[1] - across[1] * half),
    )


def _positive_polygon_overlap(
    first: tuple[tuple[float, float], ...],
    second: tuple[tuple[float, float], ...],
) -> bool:
    for polygon in (first, second):
        for index, point in enumerate(polygon):
            following = polygon[(index + 1) % len(polygon)]
            axis = (-(following[1] - point[1]), following[0] - point[0])
            first_projection = tuple(x * axis[0] + y * axis[1] for x, y in first)
            second_projection = tuple(x * axis[0] + y * axis[1] for x, y in second)
            overlap = min(max(first_projection), max(second_projection)) - max(
                min(first_projection), min(second_projection)
            )
            if overlap <= 1e-9:
                return False
    return True


def _member_interference(request: MultiMemberTeeOrchestrationRequest) -> bool:
    polygons = tuple((item.slot.slot_id, _member_polygon(item.slot)) for item in request.slots)
    return any(
        _positive_polygon_overlap(left_polygon, right_polygon)
        for left_index, (_left_id, left_polygon) in enumerate(polygons)
        for _right_id, right_polygon in polygons[left_index + 1 :]
    )


def _canonical_lengths(value: object, unit: Unit) -> object:
    if isinstance(value, Decimal):
        return PhysicalQuantity.of(value, unit)
    if is_dataclass(value):
        return tuple(
            (field.name, _canonical_lengths(getattr(value, field.name), unit))
            for field in fields(value)
        )
    if isinstance(value, tuple):
        return tuple(_canonical_lengths(item, unit) for item in value)
    if isinstance(value, Enum):
        return value
    return value


def _slot_input_identity(
    item: MultiMemberTeeSlotRequest,
    unit: Unit,
) -> tuple[object, ...]:
    slot = item.slot
    return (
        slot.slot_id,
        slot.connected_role,
        slot.profile.family,
        slot.profile.orientation,
        slot.profile.selected_surface,
        _canonical_lengths(slot.profile.dimensions, unit),
        slot.inclination_degrees,
        slot.profile_roll_degrees,
        PhysicalQuantity.of(slot.anchor_h, unit),
        PhysicalQuantity.of(slot.anchor_v, unit),
        _canonical_lengths(slot.bolt_layout, unit),
        slot.trim_enabled,
        None if slot.trim_clearance is None else PhysicalQuantity.of(slot.trim_clearance, unit),
        item.action,
    )


def _request_identity(request: MultiMemberTeeOrchestrationRequest) -> tuple[object, ...]:
    first = request.slots[0].tee_request
    return (
        request.orchestration_contract_version,
        _canonical_lengths(request.connector_dimensions, request.source_length_unit),
        _canonical_lengths(cast(object, first.support_profile), request.source_length_unit),
        _canonical_lengths(first.interface_b_layout, request.source_length_unit),
        first.bolt_diameter,
        first.hole_basis,
        tuple(_slot_input_identity(item, request.source_length_unit) for item in request.slots),
        request.support_reference_point,
    )


def _required_limitations(request: MultiMemberTeeOrchestrationRequest) -> tuple[str, ...]:
    if request.orchestration_contract_version == MULTI_MEMBER_TEE_ORCHESTRATION_CONTRACT_VERSION:
        return _REQUIRED_LIMITATIONS
    profiles = tuple(item.slot.profile for item in request.slots)
    support = cast(MemberProfile, request.slots[0].tee_request.support_profile)
    profiles = (*profiles, support)
    families = {item.family.value for item in profiles}
    limitations = [*_REQUIRED_LIMITATIONS]
    if "RECTANGULAR_HOLLOW_SECTION" in families:
        limitations.extend((RHS_LOCAL_WALL_RESPONSE, RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT))
    if "SOLID_RECTANGULAR_SECTION" in families:
        limitations.append(SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY)
    return tuple(limitations)


def _invalid_result(
    request: MultiMemberTeeOrchestrationRequest,
    wrench: AssembledSupportWrench,
    warning: str,
) -> MultiMemberTeePreviewResult:
    required_limitations = _required_limitations(request)
    input_fingerprint = _fingerprint(_request_identity(request))
    slots = tuple(
        MultiMemberTeeSlotResult(
            item.slot.slot_id,
            item.slot.connected_role.value,
            f"multi-member-tee:{item.slot.slot_id.value.lower()}",
            f"{item.slot.slot_id.value}_TO_TEE_STEM",
            None,
            None,
            None,
            None,
            None,
            item.action,
            _fingerprint((_slot_input_identity(item, request.source_length_unit), "GEOMETRY")),
            _fingerprint((_slot_input_identity(item, request.source_length_unit), "INTERFACE")),
            _fingerprint((item.slot.slot_id, item.action)),
            item.action.force.n.magnitude != 0,
        )
        for item in request.slots
    )
    support = MultiMemberTeeSupportResult(
        "TEE_FLANGE_TO_SUPPORT", None, None, None, None, _fingerprint(("SUPPORT", warning))
    )
    return MultiMemberTeePreviewResult(
        request.request_id,
        request.orchestration_contract_version,
        MULTI_MEMBER_TEE_PREVIEW_SCHEMA_VERSION,
        MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY,
        tuple(item.slot.slot_id for item in request.slots),
        slots,
        support,
        wrench,
        None,
        required_limitations,
        False,
        False,
        False,
        (warning,),
        input_fingerprint,
        _fingerprint((input_fingerprint, "INVALID_GEOMETRY", warning)),
        None,
    )


def _resolve_node(
    request: MultiMemberTeeOrchestrationRequest,
) -> tuple[
    tuple[tuple[MultiMemberTeeSlotRequest, TeeResolvedAssembly], ...],
    TeeResolvedAssembly,
    AssembledSupportWrench,
]:
    wrench = assemble_support_wrench(
        request.slots, request.support_reference_point, request.unit_system
    )
    resolved_slots = tuple(
        (
            item,
            resolve_tee_connector_request(
                item.tee_request,
                connected_member_vertical_offset=item.slot.anchor_v,
                connected_member_group_anchor_h=item.slot.anchor_h,
                connected_member_node_roundoff_tolerance=True,
            ),
        )
        for item in request.slots
    )
    first_request = request.slots[0].tee_request
    support_request = replace(
        first_request,
        request_id=f"{request.request_id}:support-transfer",
        global_force=_semantic_to_world(wrench.force),
        global_moment=_semantic_to_world(wrench.moment),
        global_reference_point=_semantic_to_world(request.support_reference_point),
    )
    resolved_support = resolve_tee_connector_request(
        support_request,
        connected_member_vertical_offset=request.slots[0].slot.anchor_v,
        connected_member_group_anchor_h=request.slots[0].slot.anchor_h,
        connected_member_node_roundoff_tolerance=True,
    )
    return resolved_slots, resolved_support, wrench


def _visualization(
    resolved_slots: tuple[tuple[MultiMemberTeeSlotRequest, TeeResolvedAssembly], ...],
    resolved_support: TeeResolvedAssembly,
) -> MultiMemberTeeVisualizationSnapshot | None:
    support_physical = cast(
        SingleBoltOrchestrationRequest,
        resolved_support.interface_b_request.physical_connection_request,
    )
    support_base = preview_single_bolt_connection(support_physical)
    support_visualization = support_base.visualization
    if support_visualization is None:
        return None
    snapshots: list[MultiMemberTeeSlotVisualization] = []
    for slot_request, resolved in resolved_slots:
        physical = cast(
            SingleBoltOrchestrationRequest,
            resolved.interface_a_request.physical_connection_request,
        )
        base = preview_single_bolt_connection(physical)
        base_visualization = base.visualization
        if base_visualization is None:
            return None
        base_visualization = trim_tee_visualization(
            base_visualization,
            resolved.trimmed_connected_member_solids,
        )
        connected_profile = resolved.connected_member_profile
        support_profile = resolved_support.support_profile
        rectangular_paths = tuple(
            item
            for item in resolved.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_STEM"
        ) + tuple(
            item
            for item in resolved_support.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_FLANGE"
        )
        snapshot = TeeVisualizationSnapshot(
            TEE_R2_VISUALIZATION_SCHEMA_VERSION,
            base_visualization,
            support_visualization,
            (*base_visualization.interface_zones, *support_visualization.interface_zones),
            expand_tee_bolts(base, slot_request.slot.bolt_layout, "A"),
            expand_tee_bolts(
                support_base,
                resolved_support.request.interface_b_layout,
                "B",
            ),
            resolved_support.selected_support_surface_id,
            connected_profile,
            connected_profile.selected_profile_surface,
            connected_profile.surface_patch_id,
            resolved_support.support_target_id,
            support_profile,
            rectangular_paths,
        )
        snapshots.append(
            MultiMemberTeeSlotVisualization(
                slot_request.slot.slot_id,
                f"multi-member-tee:{slot_request.slot.slot_id.value.lower()}",
                f"{slot_request.slot.slot_id.value}_TO_TEE_STEM",
                snapshot,
            )
        )
    return MultiMemberTeeVisualizationSnapshot(
        MULTI_MEMBER_TEE_VISUALIZATION_SCHEMA_VERSION,
        tuple(snapshots),
        (Decimal(1), Decimal(0), Decimal(0)),
        (Decimal(0), Decimal(1), Decimal(0)),
        (Decimal(0), Decimal(0), Decimal(1)),
    )


def _preview_with_node_demand(
    *,
    multirow_request: object,
    slot: MultiMemberTeeSlot,
    action: MultiMemberTeeSlotAction,
    bolt_diameter: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    unit_system: EngineeringUnitSystem,
    group_id: str,
    interface_id: str,
    response: MultiRowOrchestrationResponse | None = None,
) -> MultiRowPreviewResult:
    request = cast(MultiRowOrchestrationRequest, multirow_request)
    base = response.preview if response is not None else preview_multirow_connection(request)
    demand = base.automatic_demand_result
    if demand is None:
        demand = _node_demand(
            group_id=group_id,
            interface_id=interface_id,
            slot=slot,
            action=action,
            bolt_diameter=bolt_diameter,
            hole_diameter=hole_diameter,
            unit_system=unit_system,
        )
    geometry = (
        base
        if base.geometry_status is GeometryStatus.VALID and base.visualization is not None
        else tee_fixed_grid_geometry_preview(request, base)
    )
    calculated = demand.availability is DemandAnalysisAvailability.CALCULATED
    return replace(
        geometry,
        geometry_status=(
            GeometryStatus.VALID
            if geometry.visualization is not None
            else GeometryStatus.INVALID_GEOMETRY
        ),
        plan_availability=(
            PlanAvailability.READY if calculated else PlanAvailability.CALCULATION_NOT_SUPPORTED
        ),
        warnings=tuple(
            dict.fromkeys(
                (
                    *(
                        item
                        for item in geometry.warnings
                        if not item.startswith("INVALID_GEOMETRY:")
                    ),
                    "STAGE_3_4A_TEE_FIXED_SEMANTIC_HV_DEMAND",
                )
            )
        ),
        preview_fingerprint=_fingerprint(
            (geometry.preview_fingerprint, demand.input_fingerprint, group_id)
        ),
        design_check_ready=geometry.visualization is not None and calculated,
        automatic_demand_result=demand,
    )


def _build_results(
    request: MultiMemberTeeOrchestrationRequest,
    resolved_slots: tuple[tuple[MultiMemberTeeSlotRequest, TeeResolvedAssembly], ...],
    resolved_support: TeeResolvedAssembly,
    wrench: AssembledSupportWrench,
    *,
    design: bool,
) -> tuple[
    tuple[MultiMemberTeeSlotResult, ...],
    MultiMemberTeeSupportResult,
    tuple[MultiRowOrchestrationResponse, ...],
]:
    slot_results: list[MultiMemberTeeSlotResult] = []
    design_responses: list[MultiRowOrchestrationResponse] = []
    for slot_request, resolved in resolved_slots:
        multirow_request = resolved.interface_a_request
        response = evaluate_tee_interface(multirow_request) if design else None
        source_request = slot_request.tee_request
        preview = _preview_with_node_demand(
            multirow_request=multirow_request,
            slot=slot_request.slot,
            action=slot_request.action,
            bolt_diameter=source_request.bolt_diameter,
            hole_diameter=create_standard_hole(
                source_request.bolt_diameter, source_request.hole_basis
            ).hole_diameter,
            unit_system=request.unit_system,
            group_id=f"{slot_request.slot.slot_id.value}_TO_TEE_STEM",
            interface_id=f"{slot_request.slot.slot_id.value}_TO_TEE_STEM",
            response=response,
        )
        if response is not None:
            design_responses.append(response)
        slot_identity = _slot_input_identity(slot_request, request.source_length_unit)
        slot_results.append(
            MultiMemberTeeSlotResult(
                slot_request.slot.slot_id,
                slot_request.slot.connected_role.value,
                f"multi-member-tee:{slot_request.slot.slot_id.value.lower()}",
                f"{slot_request.slot.slot_id.value}_TO_TEE_STEM",
                resolved.connected_member_profile,
                resolved.connected_member_end_trim,
                resolved.interface_a_placement,
                preview,
                response,
                slot_request.action,
                _fingerprint((slot_identity, "GEOMETRY")),
                _fingerprint((slot_identity, "INTERFACE")),
                _fingerprint((slot_request.slot.slot_id, slot_request.action)),
                slot_request.action.force.n.magnitude != 0,
            )
        )
    support_request = resolved_support.interface_b_request
    support_design = evaluate_tee_interface(support_request) if design else None
    first_source = request.slots[0].tee_request
    support_slot = replace(
        request.slots[0].slot,
        anchor_h=Decimal(0),
        anchor_v=Decimal(0),
        bolt_layout=resolved_support.request.interface_b_layout,
    )
    support_action = MultiMemberTeeSlotAction(
        wrench.force,
        wrench.moment,
        request.support_reference_point,
    )
    support_preview = _preview_with_node_demand(
        multirow_request=support_request,
        slot=support_slot,
        action=support_action,
        bolt_diameter=first_source.bolt_diameter,
        hole_diameter=create_standard_hole(
            first_source.bolt_diameter, first_source.hole_basis
        ).hole_diameter,
        unit_system=request.unit_system,
        group_id="TEE_FLANGE_TO_SUPPORT",
        interface_id="TEE_FLANGE_TO_SUPPORT",
        response=support_design,
    )
    if support_design is not None:
        design_responses.append(support_design)
    support = MultiMemberTeeSupportResult(
        "TEE_FLANGE_TO_SUPPORT",
        resolved_support.support_profile,
        resolved_support.interface_b_placement,
        support_preview,
        support_design,
        _fingerprint(("TEE_FLANGE_TO_SUPPORT", request.support_reference_point)),
    )
    return tuple(slot_results), support, tuple(design_responses)


def _compose_preview(
    request: MultiMemberTeeOrchestrationRequest,
    resolved_support: TeeResolvedAssembly,
    wrench: AssembledSupportWrench,
    slot_results: tuple[MultiMemberTeeSlotResult, ...],
    support: MultiMemberTeeSupportResult,
    visualization: MultiMemberTeeVisualizationSnapshot,
) -> MultiMemberTeePreviewResult:
    required_limitations = _required_limitations(request)
    warnings = [*required_limitations]
    if any(item.normal_action_retained for item in slot_results):
        warnings.append("INTERFACE_NORMAL_ACTION_RETAINED_WITHOUT_AXIS_TENSION_GENERATION")
    input_fingerprint = _fingerprint(_request_identity(request))
    engineering_fingerprint = _fingerprint(
        (
            input_fingerprint,
            tuple(item.geometry_fingerprint for item in slot_results),
            tuple(item.interface_fingerprint for item in slot_results),
            support.interface_fingerprint,
            wrench.wrench_fingerprint,
            wrench.application_provenance_fingerprint,
            MultiMemberTeeAssemblyStatus.NOT_EVALUATED,
        )
    )
    return MultiMemberTeePreviewResult(
        request.request_id,
        request.orchestration_contract_version,
        MULTI_MEMBER_TEE_PREVIEW_SCHEMA_VERSION,
        MultiMemberTeeAssemblyStatus.NOT_EVALUATED,
        tuple(item.slot.slot_id for item in request.slots),
        slot_results,
        support,
        wrench,
        resolved_support.tee_longitudinal_placement,
        required_limitations,
        False,
        False,
        True,
        tuple(warnings),
        input_fingerprint,
        engineering_fingerprint,
        visualization,
    )


def _invalid_trim(
    resolved_slots: tuple[tuple[MultiMemberTeeSlotRequest, TeeResolvedAssembly], ...],
) -> bool:
    return any(
        resolved.connected_member_end_trim is not None
        and resolved.connected_member_end_trim.enabled
        and not resolved.connected_member_end_trim.geometry_valid
        for _slot_request, resolved in resolved_slots
    )


def preview_multi_member_tee(
    request: MultiMemberTeeOrchestrationRequest,
) -> MultiMemberTeePreviewResult:
    """Resolve current geometry/actions and run zero resistance equations."""

    if not isinstance(request, MultiMemberTeeOrchestrationRequest):
        raise TypeError("request must be a MultiMemberTeeOrchestrationRequest.")
    wrench = assemble_support_wrench(
        request.slots, request.support_reference_point, request.unit_system
    )
    if _cross_group_overlap(request):
        return _invalid_result(request, wrench, "CROSS_GROUP_COMPLETE_HOLE_OVERLAP")
    if _member_interference(request):
        return _invalid_result(request, wrench, "CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE")
    resolved_slots, resolved_support, wrench = _resolve_node(request)
    visualization = _visualization(resolved_slots, resolved_support)
    if visualization is None:
        return _invalid_result(request, wrench, "VISUALIZATION_GEOMETRY_UNAVAILABLE")
    if _invalid_trim(resolved_slots):
        return _invalid_result(request, wrench, "CONNECTED_MEMBER_TRIM_INVALID_GEOMETRY")
    slot_results, support, _design = _build_results(
        request, resolved_slots, resolved_support, wrench, design=False
    )
    return _compose_preview(request, resolved_support, wrench, slot_results, support, visualization)


def design_check_multi_member_tee(
    request: MultiMemberTeeOrchestrationRequest,
) -> MultiMemberTeeDesignResult:
    """Run each supported existing interface exactly once and preserve limitations."""

    if not isinstance(request, MultiMemberTeeOrchestrationRequest):
        raise TypeError("request must be a MultiMemberTeeOrchestrationRequest.")
    required_limitations = _required_limitations(request)
    wrench = assemble_support_wrench(
        request.slots, request.support_reference_point, request.unit_system
    )
    invalid_warning: str | None = None
    if _cross_group_overlap(request):
        invalid_warning = "CROSS_GROUP_COMPLETE_HOLE_OVERLAP"
    elif _member_interference(request):
        invalid_warning = "CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE"
    if invalid_warning is not None:
        preview = _invalid_result(request, wrench, invalid_warning)
        return MultiMemberTeeDesignResult(
            preview,
            MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY,
            preview.slots,
            preview.support,
            required_limitations,
            False,
            False,
            _fingerprint((preview.engineering_fingerprint, "INVALID_GEOMETRY")),
        )
    resolved_slots, resolved_support, wrench = _resolve_node(request)
    visualization = _visualization(resolved_slots, resolved_support)
    if visualization is None or _invalid_trim(resolved_slots):
        preview = _invalid_result(
            request,
            wrench,
            (
                "VISUALIZATION_GEOMETRY_UNAVAILABLE"
                if visualization is None
                else "CONNECTED_MEMBER_TRIM_INVALID_GEOMETRY"
            ),
        )
        return MultiMemberTeeDesignResult(
            preview,
            MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY,
            preview.slots,
            preview.support,
            required_limitations,
            False,
            False,
            _fingerprint((preview.engineering_fingerprint, "INVALID_GEOMETRY")),
        )
    slot_results, support, responses = _build_results(
        request, resolved_slots, resolved_support, wrench, design=True
    )
    preview = _compose_preview(
        request, resolved_support, wrench, slot_results, support, visualization
    )
    failed = any(tee_interface_failed(item) for item in responses)
    status = (
        MultiMemberTeeAssemblyStatus.FAIL if failed else MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    )
    result_fingerprint = _fingerprint(
        (
            preview.engineering_fingerprint,
            tuple(
                (
                    item.calculation_result,
                    item.automatic_demand_result,
                    item.automatic_handoff_results,
                    item.automatic_group_mode_integration,
                )
                for item in responses
            ),
            required_limitations,
            status,
        )
    )
    design_preview = replace(preview, slots=slot_results, support=support)
    return MultiMemberTeeDesignResult(
        design_preview,
        status,
        slot_results,
        support,
        required_limitations,
        False,
        failed,
        result_fingerprint,
    )


__all__ = (
    "MULTI_MEMBER_TEE_EXPANDED_ORCHESTRATION_CONTRACT_VERSION",
    "MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY",
    "MULTI_MEMBER_TEE_ORCHESTRATION_CONTRACT_VERSION",
    "MULTI_MEMBER_TEE_PREVIEW_SCHEMA_VERSION",
    "MULTI_MEMBER_TEE_VISUALIZATION_SCHEMA_VERSION",
    "TEE_CONNECTOR_BODY_RESISTANCE",
    "AssembledSupportWrench",
    "MultiMemberTeeAssemblyStatus",
    "MultiMemberTeeDesignResult",
    "MultiMemberTeeOrchestrationRequest",
    "MultiMemberTeePreviewResult",
    "MultiMemberTeeSlotAction",
    "MultiMemberTeeSlotRequest",
    "MultiMemberTeeSlotResult",
    "MultiMemberTeeVisualizationSnapshot",
    "NodeVectorInput",
    "SupportWrenchContribution",
    "assemble_support_wrench",
    "design_check_multi_member_tee",
    "preview_multi_member_tee",
)
