"""Canonical renderer-neutral visualization snapshots for one-bolt workspaces.

The objects in this module are presentation inputs, not calculation inputs.  They
are derived only from the already-resolved joint geometry context and action
contracts.  No renderer, camera, color, pixel, or UI state is admitted here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.actions import (
    ActionComponent,
    applied_action_direction,
    positive_action_direction,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    AssemblyMember,
    ComponentMaterialKind,
    CoordinateFrameKind,
    EngineeringUnitSystem,
    MemberEnd,
    MemberRole,
    ParticipantKind,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    CartesianFrame3D,
    FrameInspection3D,
    LocalAnnularCylinder3D,
    LocalRectangularPrism3D,
    LocalRuledSurface3D,
    PlacedComponentGeometry3D,
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    ResolvedConnectionInterfaceGeometry,
    ResolvedConnectionZone,
    UnitVector3D,
)

from .calculation_orchestration import (
    SingleBoltOrchestrationRequest,
    SingleBoltOrchestrationResponse,
)

VISUALIZATION_SNAPSHOT_VERSION = "1.3.0-draft"


class VisualizationPrimitiveKind(StrEnum):
    """Exact renderer-neutral primitive kinds admitted by Stage 2.3."""

    BOX = "BOX"
    ANNULAR_CYLINDER = "ANNULAR_CYLINDER"
    PLANAR_RECTANGLE = "PLANAR_RECTANGLE"
    PLANAR_ANNULUS = "PLANAR_ANNULUS"
    DEFERRED_RECTANGLE = "DEFERRED_RECTANGLE"
    DEFERRED_RULED_SURFACE = "DEFERRED_RULED_SURFACE"
    SUPPORT_RECTANGLE = "SUPPORT_RECTANGLE"
    TRIANGLE_MESH = "TRIANGLE_MESH"


class VisualizationResolutionStatus(StrEnum):
    EXACT = "EXACT"
    DEFERRED = "DEFERRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class ScalarParameter:
    name: str
    value: float


@dataclass(frozen=True, slots=True)
class VisualizationFrame:
    id: str
    label: str
    kind: CoordinateFrameKind
    owner_id: str | None
    frame: CartesianFrame3D
    inspection: FrameInspection3D


@dataclass(frozen=True, slots=True)
class VisualizationPrimitive:
    id: str
    label: str
    kind: VisualizationPrimitiveKind
    owner_id: str
    frame_id: str
    physical_element_id: str | None
    material_region_id: str | None
    center: PositionVector3D | None
    x_axis: UnitVector3D | None
    y_axis: UnitVector3D | None
    z_axis: UnitVector3D | None
    parameters: tuple[ScalarParameter, ...]
    points: tuple[PositionVector3D, ...]
    resolution_status: VisualizationResolutionStatus


@dataclass(frozen=True, slots=True)
class VisualizationElement:
    id: str
    label: str
    role: str
    material_region_id: str
    primitive_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisualizationComponent:
    id: str
    label: str
    participant_kind: ParticipantKind
    material_kind: ComponentMaterialKind
    section_family: str
    frame_id: str
    connected_end: MemberEnd | None
    elements: tuple[VisualizationElement, ...]
    deferred_primitive_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MaterialDirectionSet:
    id: str
    component_id: str
    physical_element_id: str
    material_region_id: str
    origin: PositionVector3D
    lengthwise: UnitVector3D | None
    crosswise: UnitVector3D | None
    through_thickness: UnitVector3D | None
    resolution_status: VisualizationResolutionStatus
    reason: str | None


@dataclass(frozen=True, slots=True)
class SurfaceZoneSnapshot:
    id: str
    label: str
    interface_id: str
    side: str
    participant_kind: ParticipantKind
    participant_id: str
    patch_id: str
    geometry_kind: str
    center: PositionVector3D
    normal: UnitVector3D
    corners: tuple[PositionVector3D, ...]
    parameters: tuple[ScalarParameter, ...]


@dataclass(frozen=True, slots=True)
class ConnectionOrientationSnapshot:
    """Backend-authoritative orientation and selected contact-surface semantics."""

    connection_side: str
    connected_leg: str
    outstanding_leg_side: str
    supporting_member_id: str
    selected_flange_element_id: str
    selected_flange_surface_id: str
    selected_flange_surface_role: str
    connected_member_id: str
    selected_angle_surface_id: str
    selected_angle_surface_role: str
    selected_contact_normal: UnitVector3D
    brace_to_column_directed_angle_degrees: float
    plan_angle_degrees: float
    interference_classifications: tuple[str, ...]
    interference_participant_ids: tuple[str, ...]
    interference_physical_element_ids: tuple[str, ...]
    geometry_valid: bool


@dataclass(frozen=True, slots=True)
class HoleDisplaySnapshot:
    id: str
    participant_id: str
    physical_element_id: str
    start: PositionVector3D
    end: PositionVector3D
    diameter: float


@dataclass(frozen=True, slots=True)
class WasherDisplaySnapshot:
    id: str
    location: str
    start: PositionVector3D
    end: PositionVector3D
    outside_diameter: float


@dataclass(frozen=True, slots=True)
class BoltDisplaySnapshot:
    bolt_group_id: str
    bolt_location_id: str
    center: PositionVector3D
    axis: UnitVector3D
    stack_start: PositionVector3D
    stack_end: PositionVector3D
    bolt_diameter: float
    holes: tuple[HoleDisplaySnapshot, ...]
    washers: tuple[WasherDisplaySnapshot, ...]


@dataclass(frozen=True, slots=True)
class ReferencePointSnapshot:
    id: str
    label: str
    kind: str
    owner_id: str | None
    position: PositionVector3D
    frame_id: str
    member_end: MemberEnd | None = None
    connected: bool | None = None
    provenance: str | None = None


@dataclass(frozen=True, slots=True)
class ActionDirectionSnapshot:
    component: ActionComponent
    kind: str
    axis: UnitVector3D
    reference_point_id: str
    frame_id: str
    signed_value: float | None
    unit: Unit | None
    sense: str | None
    is_zero: bool
    member_end: MemberEnd | None
    axial_loading_sense: str | None


@dataclass(frozen=True, slots=True)
class ConnectionViewExtents:
    """Non-targetable member context requested only by the preview presentation."""

    brace_view_length: float
    column_view_extent_below: float
    column_view_extent_above: float

    def __post_init__(self) -> None:
        for name, value in (
            ("brace_view_length", self.brace_view_length),
            ("column_view_extent_below", self.column_view_extent_below),
            ("column_view_extent_above", self.column_view_extent_above),
        ):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise TypeError(f"{name} must be a real number.")
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and greater than zero.")


@dataclass(frozen=True, slots=True)
class SingleBoltVisualizationSnapshot:
    snapshot_version: str
    assembly_id: str
    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    unit_system: EngineeringUnitSystem
    length_unit: Unit
    force_unit: Unit
    moment_unit: Unit
    frames: tuple[VisualizationFrame, ...]
    components: tuple[VisualizationComponent, ...]
    primitives: tuple[VisualizationPrimitive, ...]
    view_extension_primitives: tuple[VisualizationPrimitive, ...]
    material_directions: tuple[MaterialDirectionSet, ...]
    interface_zones: tuple[SurfaceZoneSnapshot, ...]
    connection_orientation: ConnectionOrientationSnapshot | None
    bolt: BoltDisplaySnapshot
    reference_points: tuple[ReferencePointSnapshot, ...]
    positive_action_directions: tuple[ActionDirectionSnapshot, ...]
    applied_action_directions: tuple[ActionDirectionSnapshot, ...]


def _units(unit_system: EngineeringUnitSystem) -> tuple[Unit, Unit, Unit]:
    if unit_system is EngineeringUnitSystem.US_CUSTOMARY:
        return Unit.IN, Unit.KIP, Unit.KIP_IN
    return Unit.MM, Unit.KN, Unit.KN_MM


def _frame_id(kind: CoordinateFrameKind, owner_id: str | None) -> str:
    return kind.value if owner_id is None else f"{kind.value}:{owner_id}"


def _frame_snapshot(
    kind: CoordinateFrameKind,
    owner_id: str | None,
    label: str,
    frame: CartesianFrame3D,
) -> VisualizationFrame:
    return VisualizationFrame(
        _frame_id(kind, owner_id), label, kind, owner_id, frame, frame.inspect()
    )


def _axis(frame: CartesianFrame3D, family: PrincipalAxisFamily) -> UnitVector3D:
    return {
        PrincipalAxisFamily.X: frame.x_axis,
        PrincipalAxisFamily.Y: frame.y_axis,
        PrincipalAxisFamily.Z: frame.z_axis,
    }[family]


def _signed_axis(
    frame: CartesianFrame3D,
    family: PrincipalAxisFamily,
    sign: int,
) -> UnitVector3D:
    axis = _axis(frame, family)
    return UnitVector3D(axis.x * sign, axis.y * sign, axis.z * sign)


def build_placed_component_visualization_snapshots(
    placed_components: tuple[PlacedComponentGeometry3D, ...],
) -> tuple[
    tuple[VisualizationComponent, ...],
    tuple[VisualizationPrimitive, ...],
    tuple[MaterialDirectionSet, ...],
]:
    components: list[VisualizationComponent] = []
    primitives: list[VisualizationPrimitive] = []
    material_directions: list[MaterialDirectionSet] = []
    for placed in placed_components:
        component = placed.component
        participant = placed.participant
        kind = (
            CoordinateFrameKind.MEMBER_LOCAL
            if participant.kind is ParticipantKind.MEMBER
            else CoordinateFrameKind.CONNECTOR_LOCAL
        )
        frame_id = _frame_id(kind, component.id)
        primitive_ids_by_element: dict[str, list[str]] = {}
        for physical in placed.physical_elements:
            owned_ids = primitive_ids_by_element.setdefault(physical.source_element.id, [])
            for index, extrusion in enumerate(physical.extrusions):
                primitive_id = (
                    f"{participant.kind.value}:{component.id}:{physical.source_element.id}:{index}"
                )
                parameters: tuple[ScalarParameter, ...]
                if isinstance(extrusion, LocalRectangularPrism3D):
                    rectangle = extrusion.rectangle
                    primitive_kind = VisualizationPrimitiveKind.BOX
                    local_center = PositionVector3D(
                        (extrusion.extent.x_start + extrusion.extent.x_end) / 2.0,
                        (rectangle.min_y + rectangle.max_y) / 2.0,
                        (rectangle.min_z + rectangle.max_z) / 2.0,
                    )
                    center = placed.global_frame.local_to_parent_point(local_center)
                    parameters = (
                        ScalarParameter("x_start", extrusion.extent.x_start),
                        ScalarParameter("x_end", extrusion.extent.x_end),
                        ScalarParameter("min_y", rectangle.min_y),
                        ScalarParameter("max_y", rectangle.max_y),
                        ScalarParameter("min_z", rectangle.min_z),
                        ScalarParameter("max_z", rectangle.max_z),
                    )
                elif isinstance(extrusion, LocalAnnularCylinder3D):
                    primitive_kind = VisualizationPrimitiveKind.ANNULAR_CYLINDER
                    center = placed.global_frame.local_to_parent_point(
                        PositionVector3D(
                            (extrusion.extent.x_start + extrusion.extent.x_end) / 2.0,
                            extrusion.annulus.center.y,
                            extrusion.annulus.center.z,
                        )
                    )
                    parameters = (
                        ScalarParameter("x_start", extrusion.extent.x_start),
                        ScalarParameter("x_end", extrusion.extent.x_end),
                        ScalarParameter("outer_radius", extrusion.annulus.outer_radius),
                        ScalarParameter("inner_radius", extrusion.annulus.inner_radius),
                    )
                else:  # pragma: no cover - exact type union protects this boundary
                    raise TypeError("Unsupported placed physical extrusion.")
                primitives.append(
                    VisualizationPrimitive(
                        primitive_id,
                        physical.source_element.label,
                        primitive_kind,
                        component.id,
                        frame_id,
                        physical.source_element.id,
                        physical.source_material_region.id,
                        center,
                        placed.global_frame.x_axis,
                        placed.global_frame.y_axis,
                        placed.global_frame.z_axis,
                        parameters,
                        (),
                        VisualizationResolutionStatus.EXACT,
                    )
                )
                owned_ids.append(primitive_id)

            component_orientation = getattr(component, "material_orientation", None)
            region_orientation = physical.source_material_region.orientation
            if component_orientation is not None and isinstance(
                region_orientation, PlanarFixedMaterialOrientation
            ):
                material_directions.append(
                    MaterialDirectionSet(
                        f"{component.id}:{physical.source_element.id}:material-axes",
                        component.id,
                        physical.source_element.id,
                        physical.source_material_region.id,
                        placed.section_datum_line_point(
                            (placed.extent.x_start + placed.extent.x_end) / 2.0
                        ),
                        _axis(placed.global_frame, component_orientation.lengthwise_axis),
                        _signed_axis(
                            placed.global_frame,
                            region_orientation.crosswise_axis,
                            region_orientation.crosswise_sign,
                        ),
                        _signed_axis(
                            placed.global_frame,
                            region_orientation.through_thickness_axis,
                            region_orientation.through_thickness_sign,
                        ),
                        VisualizationResolutionStatus.EXACT,
                        None,
                    )
                )
            else:
                material_directions.append(
                    MaterialDirectionSet(
                        f"{component.id}:{physical.source_element.id}:material-axes",
                        component.id,
                        physical.source_element.id,
                        physical.source_material_region.id,
                        placed.section_datum_line_point(
                            (placed.extent.x_start + placed.extent.x_end) / 2.0
                        ),
                        None,
                        None,
                        None,
                        VisualizationResolutionStatus.NOT_APPLICABLE,
                        "No fixed planar material-direction triad is resolved for this region.",
                    )
                )

        deferred_ids: list[str] = []
        for index, deferred in enumerate(placed.deferred_features):
            primitive_id = (
                f"{participant.kind.value}:{component.id}:deferred:"
                f"{deferred.source_feature.id}:{index}"
            )
            deferred_extrusion = deferred.extrusion
            if isinstance(deferred_extrusion, LocalRectangularPrism3D):
                rectangle = deferred_extrusion.rectangle
                primitive_kind = VisualizationPrimitiveKind.DEFERRED_RECTANGLE
                deferred_center: PositionVector3D | None = (
                    placed.global_frame.local_to_parent_point(
                        PositionVector3D(
                            (deferred_extrusion.extent.x_start + deferred_extrusion.extent.x_end)
                            / 2.0,
                            (rectangle.min_y + rectangle.max_y) / 2.0,
                            (rectangle.min_z + rectangle.max_z) / 2.0,
                        )
                    )
                )
                parameters = (
                    ScalarParameter("x_start", deferred_extrusion.extent.x_start),
                    ScalarParameter("x_end", deferred_extrusion.extent.x_end),
                    ScalarParameter("min_y", rectangle.min_y),
                    ScalarParameter("max_y", rectangle.max_y),
                    ScalarParameter("min_z", rectangle.min_z),
                    ScalarParameter("max_z", rectangle.max_z),
                )
                points: tuple[PositionVector3D, ...] = ()
            elif isinstance(deferred_extrusion, LocalRuledSurface3D):
                primitive_kind = VisualizationPrimitiveKind.DEFERRED_RULED_SURFACE
                deferred_center = None
                line = deferred_extrusion.line
                parameters = (
                    ScalarParameter("x_start", deferred_extrusion.extent.x_start),
                    ScalarParameter("x_end", deferred_extrusion.extent.x_end),
                )
                points = (
                    placed.section_point_to_global(deferred_extrusion.extent.x_start, line.start),
                    placed.section_point_to_global(deferred_extrusion.extent.x_start, line.end),
                    placed.section_point_to_global(deferred_extrusion.extent.x_end, line.start),
                    placed.section_point_to_global(deferred_extrusion.extent.x_end, line.end),
                )
            else:  # pragma: no cover
                raise TypeError("Unsupported deferred extrusion.")
            primitives.append(
                VisualizationPrimitive(
                    primitive_id,
                    deferred.source_feature.label,
                    primitive_kind,
                    component.id,
                    frame_id,
                    None,
                    None,
                    deferred_center,
                    placed.global_frame.x_axis,
                    placed.global_frame.y_axis,
                    placed.global_frame.z_axis,
                    parameters,
                    points,
                    VisualizationResolutionStatus.DEFERRED,
                )
            )
            deferred_ids.append(primitive_id)

        topology = component.section_topology
        if topology is None:  # pragma: no cover - placement validates exact topology
            raise ValueError("Placed visualization components require section topology.")
        elements = tuple(
            VisualizationElement(
                item.id,
                item.label,
                item.role.value,
                item.material_region_id,
                tuple(primitive_ids_by_element.get(item.id, ())),
            )
            for item in topology.elements
        )
        section_family = (
            component.section_family.value
            if isinstance(component, AssemblyMember)
            else component.kind.value
        )
        components.append(
            VisualizationComponent(
                component.id,
                component.label,
                participant.kind,
                component.material_kind,
                section_family,
                frame_id,
                getattr(component, "connected_end", None),
                elements,
                tuple(deferred_ids),
            )
        )

    return tuple(components), tuple(primitives), tuple(material_directions)


def _component_snapshots(
    request: SingleBoltOrchestrationRequest,
) -> tuple[
    tuple[VisualizationComponent, ...],
    tuple[VisualizationPrimitive, ...],
    tuple[MaterialDirectionSet, ...],
]:
    context = request.geometry_context
    components, placed_primitives, material_directions = (
        build_placed_component_visualization_snapshots(
            (*context.basis.placed_members, *context.basis.placed_connectors)
        )
    )
    primitives = list(placed_primitives)
    for support_surface in context.basis.support_surfaces:
        geometry = support_surface.geometry
        if isinstance(geometry, PlanarRectangularSurface3D):
            primitives.append(
                VisualizationPrimitive(
                    f"SUPPORT:{support_surface.participant.entity_id}:{support_surface.id}",
                    support_surface.label,
                    VisualizationPrimitiveKind.SUPPORT_RECTANGLE,
                    support_surface.participant.entity_id,
                    _frame_id(CoordinateFrameKind.GLOBAL, None),
                    None,
                    None,
                    geometry.center,
                    geometry.frame.x_axis,
                    geometry.frame.y_axis,
                    geometry.frame.z_axis,
                    (),
                    geometry.corners,
                    VisualizationResolutionStatus.EXACT,
                )
            )
        else:  # pragma: no cover - bounded support surfaces validate as planar rectangles
            raise TypeError("Bounded support visualization requires a planar rectangle.")
    return components, tuple(primitives), material_directions


def _view_extension_primitives(
    request: SingleBoltOrchestrationRequest,
    selected_interface: ResolvedConnectionInterfaceGeometry,
    view_extents: ConnectionViewExtents | None,
) -> tuple[VisualizationPrimitive, ...]:
    """Build renderer-neutral context solids without changing targetable geometry."""

    if view_extents is None:
        return ()
    interface_origin = selected_interface.interface_origin
    result: list[VisualizationPrimitive] = []
    for placed in request.geometry_context.basis.placed_members:
        member = placed.component
        if not isinstance(member, AssemblyMember):  # pragma: no cover - basis collection contract
            continue
        if member.role is MemberRole.BRACE:
            boundary = placed.connected_end_plane
            if boundary is None:  # pragma: no cover - members always expose their selected end
                raise ValueError("Brace view context requires an authoritative connected end.")
            connected_x = boundary.local_x
            direction = {
                MemberEnd.START: 1.0,
                MemberEnd.END: -1.0,
            }[member.connected_end]
            remote_x = connected_x + direction * view_extents.brace_view_length
            x_start, x_end = min(connected_x, remote_x), max(connected_x, remote_x)
        elif member.role is MemberRole.COLUMN:
            station = placed.global_to_local(interface_origin).x
            x_start = station - view_extents.column_view_extent_below
            x_end = station + view_extents.column_view_extent_above
        else:
            continue

        frame_id = _frame_id(CoordinateFrameKind.MEMBER_LOCAL, member.id)
        for physical in placed.physical_elements:
            for index, extrusion in enumerate(physical.extrusions):
                primitive_id = (
                    f"VIEW_EXTENSION:MEMBER:{member.id}:{physical.source_element.id}:{index}"
                )
                if isinstance(extrusion, LocalRectangularPrism3D):
                    rectangle = extrusion.rectangle
                    kind = VisualizationPrimitiveKind.BOX
                    center = placed.global_frame.local_to_parent_point(
                        PositionVector3D(
                            (x_start + x_end) / 2.0,
                            (rectangle.min_y + rectangle.max_y) / 2.0,
                            (rectangle.min_z + rectangle.max_z) / 2.0,
                        )
                    )
                    parameters = (
                        ScalarParameter("x_start", x_start),
                        ScalarParameter("x_end", x_end),
                        ScalarParameter("min_y", rectangle.min_y),
                        ScalarParameter("max_y", rectangle.max_y),
                        ScalarParameter("min_z", rectangle.min_z),
                        ScalarParameter("max_z", rectangle.max_z),
                    )
                else:  # pragma: no cover - current angle/W template is rectangular only
                    raise TypeError("Current view-extension geometry requires rectangular solids.")
                result.append(
                    VisualizationPrimitive(
                        primitive_id,
                        f"{physical.source_element.label} view context",
                        kind,
                        member.id,
                        frame_id,
                        physical.source_element.id,
                        physical.source_material_region.id,
                        center,
                        placed.global_frame.x_axis,
                        placed.global_frame.y_axis,
                        placed.global_frame.z_axis,
                        parameters,
                        (),
                        VisualizationResolutionStatus.EXACT,
                    )
                )
    return tuple(result)


def _zone_snapshot(
    interface_id: str,
    side: str,
    zone: ResolvedConnectionZone,
) -> SurfaceZoneSnapshot:
    geometry = zone.geometry
    if isinstance(geometry, PlanarRectangularSurface3D):
        kind = VisualizationPrimitiveKind.PLANAR_RECTANGLE.value
        corners = geometry.corners
        parameters = (
            ScalarParameter("extent_y", geometry.extent_y),
            ScalarParameter("extent_z", geometry.extent_z),
        )
    elif isinstance(geometry, PlanarAnnularSurface3D):
        kind = VisualizationPrimitiveKind.PLANAR_ANNULUS.value
        corners = ()
        parameters = (
            ScalarParameter("outer_radius", geometry.outer_radius),
            ScalarParameter("inner_radius", geometry.inner_radius),
        )
    else:  # pragma: no cover
        raise TypeError("Connection zones must resolve to planar surfaces.")
    return SurfaceZoneSnapshot(
        zone.id,
        zone.specification.label,
        interface_id,
        side,
        zone.surface.participant.kind,
        zone.surface.participant.entity_id,
        zone.surface.id,
        kind,
        geometry.center,
        geometry.normal,
        corners,
        parameters,
    )


def _reference_points(
    request: SingleBoltOrchestrationRequest,
    response: SingleBoltOrchestrationResponse,
) -> tuple[ReferencePointSnapshot, ...]:
    context = request.geometry_context
    points: list[ReferencePointSnapshot] = [
        ReferencePointSnapshot(
            "joint-origin",
            "Joint origin",
            "JOINT_ORIGIN",
            request.assembly.id,
            context.basis.joint_frame.origin,
            _frame_id(CoordinateFrameKind.JOINT_LOCAL, request.assembly.id),
        )
    ]
    for placed in context.basis.placed_members:
        for boundary in (placed.minimum_x_boundary, placed.maximum_x_boundary):
            member_end = boundary.member_end
            if member_end is None:  # pragma: no cover - member boundary contract
                raise ValueError("Placed member boundaries require START/END identity.")
            points.append(
                ReferencePointSnapshot(
                    f"{placed.component.id}:{member_end.value.lower()}",
                    f"{placed.component.label} {member_end.value}",
                    "MEMBER_END",
                    placed.component.id,
                    boundary.section_datum_point,
                    _frame_id(CoordinateFrameKind.MEMBER_LOCAL, placed.component.id),
                    member_end,
                    boundary.is_connected_member_end,
                    "PHYSICAL_LONGITUDINAL_BOUNDARY_PLANE",
                )
            )
    interface = next(
        item
        for item in context.basis.resolved_interfaces
        if item.interface.id == request.interface_id
    )
    group = next(
        item for item in context.resolved_bolt_groups if item.bolt_group.id == request.bolt_group_id
    )
    center = next(
        (
            item
            for item in group.master_centers
            if item.bolt_location.id == request.bolt_location_id
        ),
        None,
    )
    points.extend(
        (
            ReferencePointSnapshot(
                f"interface:{interface.interface.id}:origin",
                "Interface origin",
                "INTERFACE_ORIGIN",
                interface.interface.id,
                interface.interface_origin,
                _frame_id(CoordinateFrameKind.INTERFACE_LOCAL, interface.interface.id),
            ),
            ReferencePointSnapshot(
                f"bolt-group:{group.bolt_group.id}:origin",
                "Bolt-group origin",
                "BOLT_GROUP_ORIGIN",
                group.bolt_group.id,
                group.origin,
                _frame_id(CoordinateFrameKind.BOLT_GROUP_LOCAL, group.bolt_group.id),
            ),
        )
    )
    if center is not None:
        points.append(
            ReferencePointSnapshot(
                f"bolt:{center.bolt_location.id}:center",
                "Selected bolt center",
                "BOLT_CENTER",
                center.bolt_location.id,
                center.global_position,
                _frame_id(CoordinateFrameKind.BOLT_GROUP_LOCAL, group.bolt_group.id),
            )
        )
    if response.source_action_trace is not None:
        action = response.source_action_trace.resolved_action
        points.append(
            ReferencePointSnapshot(
                f"action:{action.action.id}:reference",
                "Applied action reference",
                action.original_reference_point.kind.value,
                action.original_reference_point.owner_id,
                action.resolved_reference_point.global_position,
                _frame_id(
                    action.resolved_frame_binding.reference.kind,
                    action.resolved_frame_binding.reference.owner_id,
                ),
                action.action.member_end,
                True,
                action.resolved_reference_point.provenance.value,
            )
        )
    return tuple(points)


def _action_directions(
    response: SingleBoltOrchestrationResponse,
    force_unit: Unit,
    moment_unit: Unit,
) -> tuple[tuple[ActionDirectionSnapshot, ...], tuple[ActionDirectionSnapshot, ...]]:
    if response.source_action_trace is None:
        return (), ()
    action = response.source_action_trace.resolved_action
    frame_binding = action.resolved_frame_binding
    frame_id = _frame_id(frame_binding.reference.kind, frame_binding.reference.owner_id)
    reference_id = f"action:{action.action.id}:reference"
    axial_sense = None if action.axial_loading_sense is None else action.axial_loading_sense.value
    values = {
        ActionComponent.FX: action.action.force.fx,
        ActionComponent.FY: action.action.force.fy,
        ActionComponent.FZ: action.action.force.fz,
        ActionComponent.MX: action.action.moment.mx,
        ActionComponent.MY: action.action.moment.my,
        ActionComponent.MZ: action.action.moment.mz,
    }
    positives: list[ActionDirectionSnapshot] = []
    applied: list[ActionDirectionSnapshot] = []
    for component in ActionComponent:
        positive = positive_action_direction(component, frame_binding.frame)
        direction = applied_action_direction(component, values[component], frame_binding.frame)
        unit = force_unit if positive.kind.value == "LINEAR" else moment_unit
        common = (
            component,
            positive.kind.value,
            reference_id,
            frame_id,
            action.action.member_end,
            axial_sense if component is ActionComponent.FX else None,
        )
        positives.append(
            ActionDirectionSnapshot(
                common[0],
                common[1],
                positive.axis,
                common[2],
                common[3],
                None,
                None,
                None,
                False,
                common[4],
                common[5],
            )
        )
        applied.append(
            ActionDirectionSnapshot(
                common[0],
                common[1],
                direction.axis,
                common[2],
                common[3],
                direction.signed_value,
                unit,
                direction.sense.value,
                direction.is_zero,
                common[4],
                common[5],
            )
        )
    return tuple(positives), tuple(applied)


def _axis_offset(
    point: PositionVector3D,
    axis: UnitVector3D,
    distance: float,
) -> PositionVector3D:
    return PositionVector3D(
        point.x + axis.x * distance,
        point.y + axis.y * distance,
        point.z + axis.z * distance,
    )


def build_single_bolt_visualization_snapshot(
    request: SingleBoltOrchestrationRequest,
    response: SingleBoltOrchestrationResponse,
    view_extents: ConnectionViewExtents | None = None,
) -> SingleBoltVisualizationSnapshot:
    """Build one immutable snapshot from the same canonical context used for evaluation."""

    if not isinstance(request, SingleBoltOrchestrationRequest):
        raise TypeError("request must be a SingleBoltOrchestrationRequest.")
    if not isinstance(response, SingleBoltOrchestrationResponse):
        raise TypeError("response must be a SingleBoltOrchestrationResponse.")
    if response.calculation_id != request.calculation_id:
        raise ValueError("Visualization request and response identities must match.")
    context = request.geometry_context
    length_unit, force_unit, moment_unit = _units(request.assembly.unit_system)
    frames: list[VisualizationFrame] = [
        _frame_snapshot(CoordinateFrameKind.GLOBAL, None, "Global", GLOBAL_FRAME),
        _frame_snapshot(
            CoordinateFrameKind.JOINT_LOCAL,
            request.assembly.id,
            "Joint local",
            context.basis.joint_frame,
        ),
    ]
    frames.extend(
        _frame_snapshot(
            CoordinateFrameKind.MEMBER_LOCAL,
            item.component.id,
            f"{item.component.label} local",
            item.global_frame,
        )
        for item in context.basis.placed_members
    )
    frames.extend(
        _frame_snapshot(
            CoordinateFrameKind.CONNECTOR_LOCAL,
            item.component.id,
            f"{item.component.label} local",
            item.global_frame,
        )
        for item in context.basis.placed_connectors
    )
    selected_interface = next(
        item
        for item in context.basis.resolved_interfaces
        if item.interface.id == request.interface_id
    )
    selected_group = next(
        item for item in context.resolved_bolt_groups if item.bolt_group.id == request.bolt_group_id
    )
    selected_path = next(
        (
            item
            for item in selected_group.paths
            if item.definition.bolt_location_id == request.bolt_location_id
        ),
        None,
    )
    frames.extend(
        (
            _frame_snapshot(
                CoordinateFrameKind.INTERFACE_LOCAL,
                selected_interface.interface.id,
                "Selected interface local",
                selected_interface.interface_frame,
            ),
            _frame_snapshot(
                CoordinateFrameKind.BOLT_GROUP_LOCAL,
                selected_group.bolt_group.id,
                "Selected bolt-group local",
                selected_group.bolt_group_frame,
            ),
        )
    )
    components, primitives, material_directions = _component_snapshots(request)
    view_extension_primitives = _view_extension_primitives(
        request,
        selected_interface,
        view_extents,
    )
    zones = tuple(
        [
            _zone_snapshot(selected_interface.interface.id, "FIRST", zone)
            for zone in selected_interface.first_side.zones
        ]
        + [
            _zone_snapshot(selected_interface.interface.id, "SECOND", zone)
            for zone in selected_interface.second_side.zones
        ]
    )
    bolt_diameter = float(request.bolt_diameter.to(length_unit).magnitude)
    if selected_path is None:
        bolt = BoltDisplaySnapshot(
            selected_group.bolt_group.id,
            request.bolt_location_id,
            selected_group.origin,
            selected_group.bolt_group_frame.x_axis,
            selected_group.origin,
            selected_group.origin,
            bolt_diameter,
            (),
            (),
        )
    else:
        washers: list[WasherDisplaySnapshot] = []
        washer_geometry = request.fastener_snapshot.washer_geometry
        if washer_geometry is not None:
            washer_thickness = float(washer_geometry.thickness.to(length_unit).magnitude)
            washer_diameter = float(washer_geometry.outside_diameter.to(length_unit).magnitude)
            if washer_geometry.under_head:
                washers.append(
                    WasherDisplaySnapshot(
                        f"{selected_group.bolt_group.id}:{request.bolt_location_id}:under-head-washer",
                        "UNDER_HEAD",
                        _axis_offset(
                            selected_path.first_entry_point,
                            selected_path.axis.direction,
                            -washer_thickness,
                        ),
                        selected_path.first_entry_point,
                        washer_diameter,
                    )
                )
            if washer_geometry.under_nut:
                washers.append(
                    WasherDisplaySnapshot(
                        f"{selected_group.bolt_group.id}:{request.bolt_location_id}:under-nut-washer",
                        "UNDER_NUT",
                        selected_path.last_exit_point,
                        _axis_offset(
                            selected_path.last_exit_point,
                            selected_path.axis.direction,
                            washer_thickness,
                        ),
                        washer_diameter,
                    )
                )
        bolt = BoltDisplaySnapshot(
            selected_group.bolt_group.id,
            request.bolt_location_id,
            selected_path.center.global_position,
            selected_path.axis.direction,
            selected_path.first_entry_point,
            selected_path.last_exit_point,
            bolt_diameter,
            tuple(
                HoleDisplaySnapshot(
                    layer.hole.id,
                    layer.hole.participant.entity_id,
                    layer.hole.physical_element_id,
                    layer.hole.start_point,
                    layer.hole.end_point,
                    2.0 * layer.hole.radius,
                )
                for layer in selected_path.layers
            ),
            tuple(washers),
        )
    positive, applied = _action_directions(response, force_unit, moment_unit)
    orientation = request.template_orientation
    orientation_snapshot = (
        None
        if orientation is None
        else ConnectionOrientationSnapshot(
            orientation.connection_side.value,
            orientation.connected_leg.value,
            orientation.outstanding_leg_side.value,
            orientation.flange_participant_id,
            orientation.flange_physical_element_id,
            orientation.flange_surface_id,
            orientation.flange_surface_role,
            orientation.angle_participant_id,
            orientation.angle_surface_id,
            orientation.angle_surface_role,
            selected_interface.second_side.primary_zone.normal,
            float(orientation.brace_to_column_angle_degrees),
            float(orientation.plan_angle_degrees),
            tuple(item.classification.value for item in orientation.interference),
            tuple(
                dict.fromkeys(
                    participant_id
                    for item in orientation.interference
                    for participant_id in (
                        item.first_participant_id,
                        item.second_participant_id,
                    )
                )
            ),
            tuple(
                dict.fromkeys(
                    element_id
                    for item in orientation.interference
                    for element_id in (
                        item.first_physical_element_id,
                        item.second_physical_element_id,
                    )
                )
            ),
            not orientation.interference,
        )
    )
    return SingleBoltVisualizationSnapshot(
        VISUALIZATION_SNAPSHOT_VERSION,
        request.assembly.id,
        request.interface_id,
        request.bolt_group_id,
        request.bolt_location_id,
        request.assembly.unit_system,
        length_unit,
        force_unit,
        moment_unit,
        tuple(frames),
        components,
        primitives,
        view_extension_primitives,
        material_directions,
        zones,
        orientation_snapshot,
        bolt,
        _reference_points(request, response),
        positive,
        applied,
    )


__all__ = (
    "VISUALIZATION_SNAPSHOT_VERSION",
    "ActionDirectionSnapshot",
    "BoltDisplaySnapshot",
    "ConnectionOrientationSnapshot",
    "ConnectionViewExtents",
    "HoleDisplaySnapshot",
    "MaterialDirectionSet",
    "ReferencePointSnapshot",
    "ScalarParameter",
    "SingleBoltVisualizationSnapshot",
    "SurfaceZoneSnapshot",
    "VisualizationComponent",
    "VisualizationElement",
    "VisualizationFrame",
    "VisualizationPrimitive",
    "VisualizationPrimitiveKind",
    "VisualizationResolutionStatus",
    "WasherDisplaySnapshot",
    "build_placed_component_visualization_snapshots",
    "build_single_bolt_visualization_snapshot",
)
