"""Reference-point, manual-action, and explicit eccentricity resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from frp_master_connection.actions.transforms import (
    AxialLoadingSense,
    interpret_member_end_axial_sense,
)
from frp_master_connection.domain import (
    AssemblyMember,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ForceVector3D,
    LoadCombination,
    ManualMemberEndAction,
    MomentVector3D,
    PositionVector3D,
    ReferencePoint,
    ReferencePointKind,
)
from frp_master_connection.geometry.joint_context import (
    JointGeometryContext,
    ResolvedFrameBinding,
)
from frp_master_connection.geometry.placement import PhysicalLongitudinalBoundaryPlane3D
from frp_master_connection.geometry.spatial import CartesianFrame3D, Vector3D, vector_between


class ReferencePointResolutionKind(StrEnum):
    """Controlled geometric provenance for a resolved reference point."""

    JOINT_FRAME_ORIGIN = "JOINT_FRAME_ORIGIN"
    MEMBER_CONNECTED_END_SECTION_DATUM = "MEMBER_CONNECTED_END_SECTION_DATUM"
    INTERFACE_FRAME_ORIGIN = "INTERFACE_FRAME_ORIGIN"
    BOLT_GROUP_FRAME_ORIGIN = "BOLT_GROUP_FRAME_ORIGIN"
    EXPLICIT_POINT_IN_DECLARED_FRAME = "EXPLICIT_POINT_IN_DECLARED_FRAME"


@dataclass(frozen=True, slots=True)
class ExplicitPointFrameBinding:
    """Explicit point coordinates bound to an exact symbolic and resolved frame."""

    reference_point: ReferencePoint
    frame_reference: CoordinateFrameReference
    frame: CartesianFrame3D

    def __post_init__(self) -> None:
        if (
            not isinstance(self.reference_point, ReferencePoint)
            or self.reference_point.kind is not ReferencePointKind.EXPLICIT_POINT
        ):
            raise ValueError("ExplicitPointFrameBinding requires an explicit ReferencePoint.")
        if not isinstance(self.frame_reference, CoordinateFrameReference):
            raise TypeError("frame_reference must be CoordinateFrameReference.")
        if not isinstance(self.frame, CartesianFrame3D):
            raise TypeError("frame must be CartesianFrame3D.")


@dataclass(frozen=True, slots=True)
class ResolvedReferencePointGeometry:
    """One original reference point resolved to a global physical position."""

    reference_point: ReferencePoint
    global_position: PositionVector3D
    source_frame_reference: CoordinateFrameReference
    source_frame: CartesianFrame3D
    provenance: ReferencePointResolutionKind
    owner: object
    connected_end_boundary: PhysicalLongitudinalBoundaryPlane3D | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reference_point, ReferencePoint):
            raise TypeError("reference_point must be ReferencePoint.")
        if not isinstance(self.global_position, PositionVector3D):
            raise TypeError("global_position must be PositionVector3D.")
        if not isinstance(self.source_frame_reference, CoordinateFrameReference):
            raise TypeError("source_frame_reference must be CoordinateFrameReference.")
        if not isinstance(self.source_frame, CartesianFrame3D):
            raise TypeError("source_frame must be CartesianFrame3D.")
        if not isinstance(self.provenance, ReferencePointResolutionKind):
            raise TypeError("provenance must be ReferencePointResolutionKind.")
        if (
            self.owner is None
            and self.source_frame_reference.kind is not CoordinateFrameKind.GLOBAL
        ):
            raise ValueError("Resolved reference-point provenance requires an exact owner.")
        if self.connected_end_boundary is not None and not isinstance(
            self.connected_end_boundary, PhysicalLongitudinalBoundaryPlane3D
        ):
            raise TypeError("connected_end_boundary must be a physical boundary plane.")


def _exact_member(context: JointGeometryContext, member_id: str) -> tuple[AssemblyMember, object]:
    for member, placed in zip(context.assembly.members, context.basis.placed_members, strict=True):
        if member.id == member_id:
            return member, placed
    raise KeyError(f"Unresolved member {member_id!r}.")


def resolve_reference_point(
    context: JointGeometryContext,
    reference_point: ReferencePoint,
    explicit_binding: ExplicitPointFrameBinding | None = None,
) -> ResolvedReferencePointGeometry:
    """Resolve a symbolic or explicitly frame-bound point without a fallback frame."""
    if not isinstance(context, JointGeometryContext):
        raise TypeError("context must be JointGeometryContext.")
    if not isinstance(reference_point, ReferencePoint):
        raise TypeError("reference_point must be ReferencePoint.")
    owner_id = reference_point.owner_id
    if reference_point.kind is ReferencePointKind.EXPLICIT_POINT:
        if explicit_binding is None or explicit_binding.reference_point is not reference_point:
            raise ValueError("An explicit point requires its exact ExplicitPointFrameBinding.")
        binding = context.resolve_frame(explicit_binding.frame_reference)
        if binding.frame is not explicit_binding.frame:
            raise ValueError("Explicit point binding must retain the exact context-resolved frame.")
        position = cast(PositionVector3D, reference_point.position)
        return ResolvedReferencePointGeometry(
            reference_point,
            binding.frame.local_to_parent_point(position),
            binding.reference,
            binding.frame,
            ReferencePointResolutionKind.EXPLICIT_POINT_IN_DECLARED_FRAME,
            binding.owner,
        )
    if explicit_binding is not None:
        raise ValueError("ExplicitPointFrameBinding is only valid for an explicit point.")
    if reference_point.kind is ReferencePointKind.JOINT_ORIGIN:
        frame_reference = CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, owner_id)
        binding = context.resolve_frame(frame_reference)
        return ResolvedReferencePointGeometry(
            reference_point,
            binding.frame.origin,
            frame_reference,
            binding.frame,
            ReferencePointResolutionKind.JOINT_FRAME_ORIGIN,
            binding.owner,
        )
    if reference_point.kind is ReferencePointKind.MEMBER_CONNECTED_END:
        member, _placed_object = _exact_member(context, owner_id or "")
        placed = next(item for item in context.basis.placed_members if item.component is member)
        boundary = cast(PhysicalLongitudinalBoundaryPlane3D, placed.connected_end_plane)
        frame_reference = CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member.id)
        return ResolvedReferencePointGeometry(
            reference_point,
            boundary.section_datum_point,
            frame_reference,
            placed.global_frame,
            ReferencePointResolutionKind.MEMBER_CONNECTED_END_SECTION_DATUM,
            member,
            boundary,
        )
    if reference_point.kind is ReferencePointKind.INTERFACE_ORIGIN:
        frame_reference = CoordinateFrameReference(CoordinateFrameKind.INTERFACE_LOCAL, owner_id)
        binding = context.resolve_frame(frame_reference)
        return ResolvedReferencePointGeometry(
            reference_point,
            binding.frame.origin,
            frame_reference,
            binding.frame,
            ReferencePointResolutionKind.INTERFACE_FRAME_ORIGIN,
            binding.owner,
        )
    frame_reference = CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, owner_id)
    binding = context.resolve_frame(frame_reference)
    return ResolvedReferencePointGeometry(
        reference_point,
        binding.frame.origin,
        frame_reference,
        binding.frame,
        ReferencePointResolutionKind.BOLT_GROUP_FRAME_ORIGIN,
        binding.owner,
    )


@dataclass(frozen=True, slots=True)
class ResolvedManualMemberEndAction:
    """One exact stored action rotated to global at its unchanged resolved point."""

    action: ManualMemberEndAction
    member: AssemblyMember
    load_combination: LoadCombination
    original_frame_reference: CoordinateFrameReference
    resolved_frame_binding: ResolvedFrameBinding
    original_reference_point: ReferencePoint
    resolved_reference_point: ResolvedReferencePointGeometry
    global_force: ForceVector3D
    global_moment: MomentVector3D
    axial_loading_sense: AxialLoadingSense | None
    unit_system: EngineeringUnitSystem


def _global_force(frame: CartesianFrame3D, value: ForceVector3D) -> ForceVector3D:
    result = frame.local_to_parent_vector(Vector3D(value.fx, value.fy, value.fz))
    return ForceVector3D(result.x, result.y, result.z)


def _global_moment(frame: CartesianFrame3D, value: MomentVector3D) -> MomentVector3D:
    result = frame.local_to_parent_vector(Vector3D(value.mx, value.my, value.mz))
    return MomentVector3D(result.x, result.y, result.z)


def resolve_manual_member_end_action(
    context: JointGeometryContext,
    action: ManualMemberEndAction,
    explicit_point_binding: ExplicitPointFrameBinding | None = None,
) -> ResolvedManualMemberEndAction:
    """Resolve an assembly-owned manual action without shifting its reference point."""
    if not isinstance(context, JointGeometryContext):
        raise TypeError("context must be JointGeometryContext.")
    if not isinstance(action, ManualMemberEndAction):
        raise TypeError("action must be ManualMemberEndAction.")
    declared_action = next(
        (item for item in context.assembly.member_end_actions if item.id == action.id), None
    )
    if declared_action is not action:
        raise ValueError("Action resolution requires an exact assembly-owned action object.")
    member = next(item for item in context.assembly.members if item.id == action.member_id)
    load = next(
        item for item in context.assembly.load_combinations if item.id == action.load_combination_id
    )
    frame_binding = context.resolve_frame(action.coordinate_frame)
    point = resolve_reference_point(context, action.reference_point, explicit_point_binding)
    axial_sense = None
    if (
        action.coordinate_frame.kind is CoordinateFrameKind.MEMBER_LOCAL
        and action.coordinate_frame.owner_id == member.id
    ):
        axial_sense = interpret_member_end_axial_sense(
            action.member_end,
            action.force.fx,
        )
    return ResolvedManualMemberEndAction(
        action,
        member,
        load,
        action.coordinate_frame,
        frame_binding,
        action.reference_point,
        point,
        _global_force(frame_binding.frame, action.force),
        _global_moment(frame_binding.frame, action.moment),
        axial_sense,
        context.assembly.unit_system,
    )


@dataclass(frozen=True, slots=True)
class ExplicitEccentricityTransform:
    """Complete trace for one caller-requested point shift and output frame."""

    source_action: ResolvedManualMemberEndAction
    source_point: ResolvedReferencePointGeometry
    target_point: ResolvedReferencePointGeometry
    output_frame_reference: CoordinateFrameReference
    output_frame: CartesianFrame3D
    source_position_in_output_frame: PositionVector3D
    target_position_in_output_frame: PositionVector3D
    raw_offset_source_minus_target: Vector3D
    force_in_output_frame: ForceVector3D
    moment_at_source_in_output_frame: MomentVector3D
    eccentricity_moment_in_output_frame: MomentVector3D
    shifted_moment_in_output_frame: MomentVector3D
    unit_system: EngineeringUnitSystem


def shift_resolved_manual_action(
    context: JointGeometryContext,
    source_action: ResolvedManualMemberEndAction,
    target_point: ResolvedReferencePointGeometry,
    output_frame_reference: CoordinateFrameReference,
    output_frame: CartesianFrame3D,
) -> ExplicitEccentricityTransform:
    """Shift an already resolved action to an explicit target in an explicit output frame."""
    if not isinstance(context, JointGeometryContext):
        raise TypeError("context must be JointGeometryContext.")
    if not isinstance(source_action, ResolvedManualMemberEndAction):
        raise TypeError("source_action must be ResolvedManualMemberEndAction.")
    if (
        not any(item is source_action.action for item in context.assembly.member_end_actions)
        or source_action.unit_system is not context.assembly.unit_system
    ):
        raise ValueError("Resolved source action does not belong to this joint context.")
    if not isinstance(target_point, ResolvedReferencePointGeometry):
        raise TypeError("target_point must be ResolvedReferencePointGeometry.")
    if not isinstance(output_frame_reference, CoordinateFrameReference) or not isinstance(
        output_frame, CartesianFrame3D
    ):
        raise TypeError("Output frame reference and exact resolved frame are required.")
    binding = context.resolve_frame(output_frame_reference)
    if binding.frame is not output_frame:
        raise ValueError("Output frame must be the exact frame resolved by its symbolic reference.")

    source_position = output_frame.parent_to_local_point(
        source_action.resolved_reference_point.global_position
    )
    target_position = output_frame.parent_to_local_point(target_point.global_position)
    offset = vector_between(target_position, source_position)
    force = output_frame.parent_to_local_vector(
        Vector3D(
            source_action.global_force.fx,
            source_action.global_force.fy,
            source_action.global_force.fz,
        )
    )
    moment = output_frame.parent_to_local_vector(
        Vector3D(
            source_action.global_moment.mx,
            source_action.global_moment.my,
            source_action.global_moment.mz,
        )
    )
    eccentricity = offset.cross(force)
    shifted = moment + eccentricity
    return ExplicitEccentricityTransform(
        source_action,
        source_action.resolved_reference_point,
        target_point,
        output_frame_reference,
        output_frame,
        source_position,
        target_position,
        offset,
        ForceVector3D(force.x, force.y, force.z),
        MomentVector3D(moment.x, moment.y, moment.z),
        MomentVector3D(eccentricity.x, eccentricity.y, eccentricity.z),
        MomentVector3D(shifted.x, shifted.y, shifted.z),
        context.assembly.unit_system,
    )


__all__ = (
    "ExplicitEccentricityTransform",
    "ExplicitPointFrameBinding",
    "ReferencePointResolutionKind",
    "ResolvedManualMemberEndAction",
    "ResolvedReferencePointGeometry",
    "resolve_manual_member_end_action",
    "resolve_reference_point",
    "shift_resolved_manual_action",
)
