"""Bolt-group placement, round-hole paths, and ordered penetrated-layer geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise
from typing import cast

from frp_master_connection.domain import (
    BoltGroup,
    BoltLocation,
    EngineeringUnitSystem,
    ParticipantKind,
    ParticipantReference,
    ReferencePointKind,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
)
from frp_master_connection.domain.values import CoordinateFrameKind, PositionVector3D
from frp_master_connection.geometry.interface_targeting import (
    ConnectionZoneKind,
    GeometryComparisonTolerance,
    RectangularSubzoneBounds,
    ResolvedConnectionInterfaceGeometry,
    ResolvedConnectionZone,
)
from frp_master_connection.geometry.joint_context import JointGeometryBasis
from frp_master_connection.geometry.placement import PlacedPhysicalElement3D
from frp_master_connection.geometry.spatial import (
    CartesianFrame3D,
    UnitVector3D,
    Vector3D,
    translate_point,
    vector_between,
)
from frp_master_connection.geometry.surfaces import (
    PlanarRectangularSurface3D,
    SurfaceDisposition,
    SurfacePatch3D,
    SurfacePatchReference,
    SurfacePatchRole,
    SurfaceSourceKind,
)


def _positive(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{field_name} must be finite and positive.")
    return float(value)


def _finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
    return float(value)


class InterfaceTargetSide(StrEnum):
    """Canonical participant side of a resolved logical interface."""

    FIRST = "FIRST"
    SECOND = "SECOND"


@dataclass(frozen=True, slots=True)
class InterfaceZoneReference:
    """Stable reference to one connection zone on one resolved interface side."""

    interface_id: str
    side: InterfaceTargetSide
    zone_id: str

    def __post_init__(self) -> None:
        validate_identifier(self.interface_id, "InterfaceZoneReference.interface_id")
        require_enum(self.side, InterfaceTargetSide, "InterfaceZoneReference.side")
        validate_identifier(self.zone_id, "InterfaceZoneReference.zone_id")


@dataclass(frozen=True, slots=True)
class IntendedPenetratedLayer:
    """One explicitly intended physical-element layer and its hole constraints."""

    id: str
    participant: ParticipantReference
    physical_element_id: str
    entry_surface: SurfacePatchReference
    exit_surface: SurfacePatchReference
    connection_zones: tuple[InterfaceZoneReference, ...]
    hole_diameter: float

    def __post_init__(self) -> None:
        validate_identifier(self.id, "IntendedPenetratedLayer.id")
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError("IntendedPenetratedLayer.participant must be ParticipantReference.")
        if self.participant.kind is ParticipantKind.SUPPORT:
            raise ValueError("A support surface cannot be an intended penetrated layer.")
        validate_identifier(
            self.physical_element_id,
            "IntendedPenetratedLayer.physical_element_id",
        )
        if not isinstance(self.entry_surface, SurfacePatchReference) or not isinstance(
            self.exit_surface, SurfacePatchReference
        ):
            raise TypeError("Layer entry and exit must be SurfacePatchReference values.")
        if (
            self.entry_surface.participant != self.participant
            or self.exit_surface.participant != self.participant
            or self.entry_surface == self.exit_surface
        ):
            raise ValueError("Layer entry/exit references must be distinct and match participant.")
        require_tuple(self.connection_zones, "IntendedPenetratedLayer.connection_zones")
        if not self.connection_zones or any(
            not isinstance(item, InterfaceZoneReference) for item in self.connection_zones
        ):
            raise ValueError("A penetrated layer requires connection-zone references.")
        if len(set(self.connection_zones)) != len(self.connection_zones):
            raise ValueError("A penetrated layer cannot repeat a connection-zone reference.")
        _positive(self.hole_diameter, "IntendedPenetratedLayer.hole_diameter")


@dataclass(frozen=True, slots=True)
class BoltPathDefinition:
    """Declared, ordered penetrated layers for one logical bolt location."""

    bolt_location_id: str
    layers: tuple[IntendedPenetratedLayer, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.bolt_location_id, "BoltPathDefinition.bolt_location_id")
        require_tuple(self.layers, "BoltPathDefinition.layers")
        if not self.layers or any(
            not isinstance(item, IntendedPenetratedLayer) for item in self.layers
        ):
            raise ValueError("BoltPathDefinition.layers must be a nonempty layer tuple.")
        ids = tuple(item.id for item in self.layers)
        if len(set(ids)) != len(ids):
            raise ValueError("Penetrated-layer IDs must be unique within a bolt path.")
        hosts = tuple((item.participant, item.physical_element_id) for item in self.layers)
        if len(set(hosts)) != len(hosts):
            raise ValueError("A physical-element host cannot occur twice within one bolt path.")


@dataclass(frozen=True, slots=True)
class BoltGroupGeometrySpecification:
    """Explicit placement and path specification for one logical bolt group."""

    bolt_group: BoltGroup
    primary_interface_id: str
    origin_y: float
    origin_z: float
    in_plane_reference: Vector3D
    tolerance: GeometryComparisonTolerance
    paths: tuple[BoltPathDefinition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.bolt_group, BoltGroup):
            raise TypeError("BoltGroupGeometrySpecification.bolt_group must be BoltGroup.")
        if (
            self.bolt_group.coordinate_frame.kind is not CoordinateFrameKind.BOLT_GROUP_LOCAL
            or self.bolt_group.coordinate_frame.owner_id != self.bolt_group.id
            or self.bolt_group.reference_point.kind is not ReferencePointKind.BOLT_GROUP_ORIGIN
            or self.bolt_group.reference_point.owner_id != self.bolt_group.id
        ):
            raise ValueError(
                "Bolt geometry requires matching logical local frame and group origin."
            )
        validate_identifier(
            self.primary_interface_id,
            "BoltGroupGeometrySpecification.primary_interface_id",
        )
        if self.primary_interface_id not in self.bolt_group.interface_ids:
            raise ValueError("The primary interface must be declared by the logical bolt group.")
        _finite(self.origin_y, "BoltGroupGeometrySpecification.origin_y")
        _finite(self.origin_z, "BoltGroupGeometrySpecification.origin_z")
        if not isinstance(self.in_plane_reference, Vector3D):
            raise TypeError("in_plane_reference must be Vector3D.")
        if not isinstance(self.tolerance, GeometryComparisonTolerance):
            raise TypeError("tolerance must be GeometryComparisonTolerance.")
        require_tuple(self.paths, "BoltGroupGeometrySpecification.paths")
        if any(not isinstance(item, BoltPathDefinition) for item in self.paths):
            raise TypeError("BoltGroupGeometrySpecification.paths contains an invalid item.")
        if tuple(item.bolt_location_id for item in self.paths) != tuple(
            item.id for item in self.bolt_group.locations
        ):
            raise ValueError(
                "Bolt paths must cover logical locations exactly in declaration order."
            )


@dataclass(frozen=True, slots=True)
class MasterBoltCenter3D:
    bolt_group: BoltGroup
    bolt_location: BoltLocation
    bolt_group_frame: CartesianFrame3D
    local_position: PositionVector3D
    global_position: PositionVector3D

    def __post_init__(self) -> None:
        if not isinstance(self.bolt_group, BoltGroup):
            raise TypeError("MasterBoltCenter3D.bolt_group must be BoltGroup.")
        if not isinstance(self.bolt_location, BoltLocation):
            raise TypeError("MasterBoltCenter3D.bolt_location must be BoltLocation.")
        if not any(item is self.bolt_location for item in self.bolt_group.locations):
            raise ValueError("Master center must retain an exact bolt-group location.")
        if not isinstance(self.bolt_group_frame, CartesianFrame3D):
            raise TypeError("MasterBoltCenter3D.bolt_group_frame must be CartesianFrame3D.")
        if self.local_position is not self.bolt_location.position:
            raise ValueError("Master center must retain the exact logical local position.")
        if not isinstance(self.global_position, PositionVector3D):
            raise TypeError("MasterBoltCenter3D.global_position must be PositionVector3D.")
        if self.global_position != self.bolt_group_frame.local_to_parent_point(self.local_position):
            raise ValueError(
                "Master center global position must be the exact group-frame transform."
            )


@dataclass(frozen=True, slots=True)
class AuthoritativeBoltAxis3D:
    bolt_group: BoltGroup
    bolt_location: BoltLocation
    bolt_group_frame: CartesianFrame3D
    point: PositionVector3D
    direction: UnitVector3D

    def __post_init__(self) -> None:
        if not isinstance(self.bolt_group, BoltGroup):
            raise TypeError("AuthoritativeBoltAxis3D.bolt_group must be BoltGroup.")
        if not isinstance(self.bolt_location, BoltLocation):
            raise TypeError("AuthoritativeBoltAxis3D.bolt_location must be BoltLocation.")
        if not any(item is self.bolt_location for item in self.bolt_group.locations):
            raise ValueError("Bolt axis must retain an exact bolt-group location.")
        if not isinstance(self.bolt_group_frame, CartesianFrame3D):
            raise TypeError("AuthoritativeBoltAxis3D.bolt_group_frame must be CartesianFrame3D.")
        if not isinstance(self.point, PositionVector3D) or not isinstance(
            self.direction, UnitVector3D
        ):
            raise TypeError("A bolt axis requires a position and unit direction.")
        if self.point != self.bolt_group_frame.local_to_parent_point(self.bolt_location.position):
            raise ValueError("Bolt axis point must equal the transformed master center.")
        if self.direction is not self.bolt_group_frame.x_axis:
            raise ValueError("Bolt axis direction must be the exact bolt-group +x axis.")


@dataclass(frozen=True, slots=True)
class SurfaceHoleIntersection3D:
    surface: SurfacePatch3D
    point: PositionVector3D
    axis_parameter: float
    raw_patch_clearance: float

    def __post_init__(self) -> None:
        if not isinstance(self.surface, SurfacePatch3D):
            raise TypeError("SurfaceHoleIntersection3D.surface must be SurfacePatch3D.")
        if not isinstance(self.point, PositionVector3D):
            raise TypeError("SurfaceHoleIntersection3D.point must be PositionVector3D.")
        _finite(self.axis_parameter, "SurfaceHoleIntersection3D.axis_parameter")
        _finite(self.raw_patch_clearance, "SurfaceHoleIntersection3D.raw_patch_clearance")


@dataclass(frozen=True, slots=True)
class ResolvedRoundHoleCylinder3D:
    id: str
    participant: ParticipantReference
    physical_element_id: str
    axis: AuthoritativeBoltAxis3D
    start_point: PositionVector3D
    end_point: PositionVector3D
    radius: float

    def __post_init__(self) -> None:
        validate_identifier(self.id, "ResolvedRoundHoleCylinder3D.id")
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError("ResolvedRoundHoleCylinder3D.participant must be ParticipantReference.")
        validate_identifier(
            self.physical_element_id, "ResolvedRoundHoleCylinder3D.physical_element_id"
        )
        if not isinstance(self.axis, AuthoritativeBoltAxis3D):
            raise TypeError("ResolvedRoundHoleCylinder3D.axis must be AuthoritativeBoltAxis3D.")
        if not isinstance(self.start_point, PositionVector3D) or not isinstance(
            self.end_point, PositionVector3D
        ):
            raise TypeError("Round-hole endpoints must be PositionVector3D values.")
        _positive(self.radius, "ResolvedRoundHoleCylinder3D.radius")


@dataclass(frozen=True, slots=True)
class ResolvedPenetratedLayer:
    definition: IntendedPenetratedLayer
    physical_element: PlacedPhysicalElement3D
    entry: SurfaceHoleIntersection3D
    exit: SurfaceHoleIntersection3D
    zones: tuple[ResolvedConnectionZone, ...]
    raw_zone_clearances: tuple[float, ...]
    hole: ResolvedRoundHoleCylinder3D
    tolerance: GeometryComparisonTolerance

    @property
    def raw_minimum_patch_clearance(self) -> float:
        return min(self.entry.raw_patch_clearance, self.exit.raw_patch_clearance)

    @property
    def raw_minimum_zone_clearance(self) -> float:
        return min(self.raw_zone_clearances)

    @property
    def raw_thickness(self) -> float:
        return self.exit.axis_parameter - self.entry.axis_parameter


@dataclass(frozen=True, slots=True)
class ResolvedBoltPath:
    definition: BoltPathDefinition
    center: MasterBoltCenter3D
    axis: AuthoritativeBoltAxis3D
    layers: tuple[ResolvedPenetratedLayer, ...]
    raw_interlayer_gaps: tuple[float, ...]
    geometric_stack_span: float

    @property
    def first_entry_point(self) -> PositionVector3D:
        return self.layers[0].entry.point

    @property
    def last_exit_point(self) -> PositionVector3D:
        return self.layers[-1].exit.point


@dataclass(frozen=True, slots=True)
class BoltGroupInterfaceRepresentation3D:
    """One declared interface retained with its raw orientation and plane offset."""

    interface: ResolvedConnectionInterfaceGeometry
    normal_alignment: float
    signed_plane_offset: float

    def __post_init__(self) -> None:
        if not isinstance(self.interface, ResolvedConnectionInterfaceGeometry):
            raise TypeError("interface must be ResolvedConnectionInterfaceGeometry.")
        _finite(self.normal_alignment, "normal_alignment")
        _finite(self.signed_plane_offset, "signed_plane_offset")


@dataclass(frozen=True, slots=True)
class ResolvedBoltGroupGeometry:
    specification: BoltGroupGeometrySpecification
    bolt_group: BoltGroup
    primary_interface: ResolvedConnectionInterfaceGeometry
    participating_interfaces: tuple[ResolvedConnectionInterfaceGeometry, ...]
    interface_representations: tuple[BoltGroupInterfaceRepresentation3D, ...]
    bolt_group_frame: CartesianFrame3D
    origin: PositionVector3D
    master_centers: tuple[MasterBoltCenter3D, ...]
    bolt_axes: tuple[AuthoritativeBoltAxis3D, ...]
    paths: tuple[ResolvedBoltPath, ...]
    tolerance: GeometryComparisonTolerance
    unit_system: EngineeringUnitSystem
    is_geometry_only: bool = field(default=True, init=False)


def _interface(basis: JointGeometryBasis, interface_id: str) -> ResolvedConnectionInterfaceGeometry:
    return {resolved.interface.id: resolved for resolved in basis.resolved_interfaces}[interface_id]


def _zone(
    basis: JointGeometryBasis, reference: InterfaceZoneReference
) -> tuple[ResolvedConnectionInterfaceGeometry, ResolvedConnectionZone]:
    interface = _interface(basis, reference.interface_id)
    side = (
        interface.first_side
        if reference.side is InterfaceTargetSide.FIRST
        else interface.second_side
    )
    for zone in side.zones:
        if zone.id == reference.zone_id:
            return interface, zone
    raise KeyError(f"Unresolved connection zone {reference.zone_id!r}.")


def _build_group_frame(
    specification: BoltGroupGeometrySpecification,
    primary: ResolvedConnectionInterfaceGeometry,
) -> CartesianFrame3D:
    primary_frame = primary.interface_frame
    origin = primary_frame.local_to_parent_point(
        PositionVector3D(0.0, specification.origin_y, specification.origin_z)
    )
    axis_x = primary_frame.x_axis
    reference = specification.in_plane_reference.normalized()
    projected = reference - axis_x * reference.dot(axis_x)
    if projected.norm <= specification.tolerance.angular_tolerance:
        raise ValueError(
            "Bolt-group in-plane reference is parallel or nearly parallel to its axis."
        )
    axis_y = projected.normalized()
    axis_z = axis_x.cross(axis_y).normalized()
    axis_y = axis_z.cross(axis_x).normalized()
    return CartesianFrame3D(origin, axis_x, axis_y, axis_z)


def _surface(
    basis: JointGeometryBasis,
    reference: SurfacePatchReference,
    physical_element_id: str,
) -> SurfacePatch3D:
    surface_set = basis.component_surface_set(
        reference.participant.kind, reference.participant.entity_id
    )
    surface = surface_set.resolve(reference)
    if (
        surface.source.kind is not SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT
        or surface.source.physical_element_id != physical_element_id
        or surface.disposition is not SurfaceDisposition.REGULAR
        or surface.role
        not in {
            SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
        }
        or not surface.is_targetable
        or not isinstance(surface.geometry, PlanarRectangularSurface3D)
    ):
        raise ValueError("A hole layer requires the matching regular physical broad face.")
    return surface


def _physical_element(
    basis: JointGeometryBasis,
    participant: ParticipantReference,
    physical_element_id: str,
) -> PlacedPhysicalElement3D:
    surface_set = basis.component_surface_set(participant.kind, participant.entity_id)
    for physical_element in surface_set.placed_component.physical_elements:
        if physical_element.source_element.id == physical_element_id:
            return physical_element
    raise KeyError(
        f"No placed physical element {physical_element_id!r} exists for {participant.entity_id!r}."
    )


def _intersection(
    axis: AuthoritativeBoltAxis3D,
    surface: SurfacePatch3D,
    radius: float,
    tolerance: GeometryComparisonTolerance,
    *,
    entry: bool,
) -> SurfaceHoleIntersection3D:
    geometry = cast(PlanarRectangularSurface3D, surface.geometry)
    alignment = axis.direction.dot(geometry.normal)
    mismatch = 1.0 + alignment if entry else 1.0 - alignment
    if mismatch > tolerance.angular_tolerance:
        raise ValueError("Layer broad-face normal is not aligned with the authoritative bolt axis.")
    denominator = axis.direction.dot(geometry.normal)
    parameter = vector_between(axis.point, geometry.center).dot(geometry.normal) / denominator
    point = translate_point(axis.point, axis.direction * parameter)
    local = geometry.frame.parent_to_local_point(point)
    clearance = min(geometry.extent_y / 2.0 - abs(local.y), geometry.extent_z / 2.0 - abs(local.z))
    if clearance + tolerance.distance_tolerance < radius:
        raise ValueError("The complete round hole disk is not contained in its source patch.")
    return SurfaceHoleIntersection3D(surface, point, parameter, clearance)


def _zone_clearance(
    zone: ResolvedConnectionZone,
    point: PositionVector3D,
) -> float:
    geometry = cast(PlanarRectangularSurface3D, zone.geometry)
    local = geometry.frame.parent_to_local_point(point)
    if zone.specification.kind is ConnectionZoneKind.WHOLE_PATCH:
        min_y = -geometry.extent_y / 2.0
        max_y = geometry.extent_y / 2.0
        min_z = -geometry.extent_z / 2.0
        max_z = geometry.extent_z / 2.0
    else:
        bounds = cast(RectangularSubzoneBounds, zone.specification.rectangular_bounds)
        min_y, max_y, min_z, max_z = bounds.min_y, bounds.max_y, bounds.min_z, bounds.max_z
    return min(local.y - min_y, max_y - local.y, local.z - min_z, max_z - local.z)


def _resolve_layer(
    basis: JointGeometryBasis,
    group: BoltGroup,
    definition: IntendedPenetratedLayer,
    axis: AuthoritativeBoltAxis3D,
    tolerance: GeometryComparisonTolerance,
) -> ResolvedPenetratedLayer:
    physical_element = _physical_element(
        basis,
        definition.participant,
        definition.physical_element_id,
    )
    entry_surface = _surface(
        basis,
        definition.entry_surface,
        definition.physical_element_id,
    )
    exit_surface = _surface(
        basis,
        definition.exit_surface,
        definition.physical_element_id,
    )
    if entry_surface.role is exit_surface.role:
        raise ValueError("Layer entry and exit must use opposing signed broad-face roles.")
    radius = definition.hole_diameter / 2.0
    if radius <= 0.0:
        raise ValueError("Hole radius must remain exactly representable.")
    entry = _intersection(axis, entry_surface, radius, tolerance, entry=True)
    exit = _intersection(axis, exit_surface, radius, tolerance, entry=False)
    if exit.axis_parameter <= entry.axis_parameter:
        raise ValueError("A penetrated layer requires positive entry-to-exit separation.")

    zones: list[ResolvedConnectionZone] = []
    clearances: list[float] = []
    for reference in definition.connection_zones:
        if reference.interface_id not in group.interface_ids:
            raise ValueError("A penetrated layer references an unrelated interface.")
        _, zone = _zone(basis, reference)
        if zone.surface.reference not in {definition.entry_surface, definition.exit_surface}:
            raise ValueError("Every layer connection zone must use its entry or exit surface.")
        point = entry.point if zone.surface.reference == definition.entry_surface else exit.point
        clearance = _zone_clearance(zone, point)
        if clearance + tolerance.distance_tolerance < radius:
            raise ValueError("The complete round hole disk is not contained in a connection zone.")
        zones.append(zone)
        clearances.append(clearance)
    hole = ResolvedRoundHoleCylinder3D(
        f"{group.id}:{axis.bolt_location.id}:{definition.id}:HOLE",
        definition.participant,
        definition.physical_element_id,
        axis,
        entry.point,
        exit.point,
        radius,
    )
    return ResolvedPenetratedLayer(
        definition,
        physical_element,
        entry,
        exit,
        tuple(zones),
        tuple(clearances),
        hole,
        tolerance,
    )


def resolve_bolt_group_geometry(
    basis: JointGeometryBasis,
    specification: BoltGroupGeometrySpecification,
) -> ResolvedBoltGroupGeometry:
    """Resolve one logical bolt group into authoritative centers, axes, holes, and layers."""
    if not isinstance(basis, JointGeometryBasis):
        raise TypeError("basis must be JointGeometryBasis.")
    if not isinstance(specification, BoltGroupGeometrySpecification):
        raise TypeError("specification must be BoltGroupGeometrySpecification.")
    group = specification.bolt_group
    declared = next((item for item in basis.assembly.bolt_groups if item.id == group.id), None)
    if declared is not group:
        raise ValueError("Bolt-group specification must retain an exact assembly-owned object.")
    primary = _interface(basis, specification.primary_interface_id)
    participating = tuple(_interface(basis, item) for item in group.interface_ids)
    frame = _build_group_frame(specification, primary)
    interface_representations = tuple(
        BoltGroupInterfaceRepresentation3D(
            interface,
            frame.x_axis.dot(interface.interface_frame.x_axis),
            vector_between(frame.origin, interface.interface_frame.origin).dot(frame.x_axis),
        )
        for interface in participating
    )
    if any(
        1.0 - abs(item.normal_alignment) > specification.tolerance.angular_tolerance
        for item in interface_representations
    ):
        raise ValueError(
            "Every additional interface normal must be parallel or antiparallel to the "
            "primary bolt axis."
        )

    if any(location.position.x != 0.0 for location in group.locations):
        raise ValueError(
            "Every logical bolt location must lie exactly in the group local y-z plane."
        )
    local_pairs = tuple((item.position.y, item.position.z) for item in group.locations)
    if len(set(local_pairs)) != len(local_pairs):
        raise ValueError("Bolt locations cannot duplicate a local y-z master center.")
    centers = tuple(
        MasterBoltCenter3D(
            group,
            location,
            frame,
            location.position,
            frame.local_to_parent_point(location.position),
        )
        for location in group.locations
    )
    axes = tuple(
        AuthoritativeBoltAxis3D(
            group,
            center.bolt_location,
            frame,
            center.global_position,
            frame.x_axis,
        )
        for center in centers
    )

    paths: list[ResolvedBoltPath] = []
    represented: set[str] = set()
    for definition, center, axis in zip(specification.paths, centers, axes, strict=True):
        layers = tuple(
            _resolve_layer(basis, group, layer, axis, specification.tolerance)
            for layer in definition.layers
        )
        referenced = {
            reference.interface_id
            for layer in definition.layers
            for reference in layer.connection_zones
        }
        if specification.primary_interface_id not in referenced:
            raise ValueError("Every bolt path must represent the primary interface.")
        represented.update(referenced)
        gaps = tuple(
            following.entry.axis_parameter - preceding.exit.axis_parameter
            for preceding, following in pairwise(layers)
        )
        if any(gap < -specification.tolerance.distance_tolerance for gap in gaps):
            raise ValueError(
                "Declared penetrated-layer order contains an overlap beyond tolerance."
            )
        span = layers[-1].exit.axis_parameter - layers[0].entry.axis_parameter
        paths.append(ResolvedBoltPath(definition, center, axis, layers, gaps, span))
    if represented != set(group.interface_ids):
        raise ValueError("Resolved bolt paths must represent every and only declared interface.")
    return ResolvedBoltGroupGeometry(
        specification,
        group,
        primary,
        participating,
        interface_representations,
        frame,
        frame.origin,
        centers,
        axes,
        tuple(paths),
        specification.tolerance,
        basis.assembly.unit_system,
    )


__all__ = (
    "AuthoritativeBoltAxis3D",
    "BoltGroupGeometrySpecification",
    "BoltGroupInterfaceRepresentation3D",
    "BoltPathDefinition",
    "IntendedPenetratedLayer",
    "InterfaceTargetSide",
    "InterfaceZoneReference",
    "MasterBoltCenter3D",
    "ResolvedBoltGroupGeometry",
    "ResolvedBoltPath",
    "ResolvedPenetratedLayer",
    "ResolvedRoundHoleCylinder3D",
    "SurfaceHoleIntersection3D",
    "resolve_bolt_group_geometry",
)
