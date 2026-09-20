"""Planar connection zones and resolved interface-local geometry."""

import math
from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.domain.entities import (
    ConnectionInterface,
    ParticipantReference,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import PositionVector3D
from frp_master_connection.geometry.spatial import (
    CartesianFrame3D,
    UnitVector3D,
    Vector3D,
    vector_between,
)
from frp_master_connection.geometry.surfaces import (
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    SurfaceDisposition,
    SurfaceExposure,
    SurfacePatch3D,
    SurfacePatchReference,
)


def _require_finite_real(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
    return value


def _require_positive(value: object, field_name: str) -> None:
    numeric_value = _require_finite_real(value, field_name)
    if numeric_value <= 0.0:
        raise ValueError(f"{field_name} must be strictly positive.")


@dataclass(frozen=True, slots=True)
class GeometryComparisonTolerance:
    """Explicit geometric-comparison values supplied in the caller's unit basis."""

    distance_tolerance: float
    angular_tolerance: float

    def __post_init__(self) -> None:
        _require_positive(
            self.distance_tolerance,
            "GeometryComparisonTolerance.distance_tolerance",
        )
        _require_positive(
            self.angular_tolerance,
            "GeometryComparisonTolerance.angular_tolerance",
        )


class ConnectionZoneKind(StrEnum):
    """Controlled bounded selections supported on targetable planar patches."""

    WHOLE_PATCH = "WHOLE_PATCH"
    RECTANGULAR_SUBZONE = "RECTANGULAR_SUBZONE"


@dataclass(frozen=True, slots=True)
class RectangularSubzoneBounds:
    """Exact bounds in one planar rectangle's local in-plane coordinates."""

    min_y: float
    max_y: float
    min_z: float
    max_z: float

    def __post_init__(self) -> None:
        for name, value in (
            ("min_y", self.min_y),
            ("max_y", self.max_y),
            ("min_z", self.min_z),
            ("max_z", self.max_z),
        ):
            _require_finite_real(value, f"RectangularSubzoneBounds.{name}")
        if self.min_y >= self.max_y:
            raise ValueError("RectangularSubzoneBounds requires min_y < max_y.")
        if self.min_z >= self.max_z:
            raise ValueError("RectangularSubzoneBounds requires min_z < max_z.")


@dataclass(frozen=True, slots=True)
class ConnectionZoneSpecification:
    """One immutable participant-scoped surface selection."""

    id: str
    label: str
    surface_reference: SurfacePatchReference
    kind: ConnectionZoneKind
    rectangular_bounds: RectangularSubzoneBounds | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.id, "ConnectionZoneSpecification.id")
        validate_label(self.label, "ConnectionZoneSpecification.label")
        if not isinstance(self.surface_reference, SurfacePatchReference):
            raise TypeError(
                "ConnectionZoneSpecification.surface_reference must be a SurfacePatchReference."
            )
        require_enum(self.kind, ConnectionZoneKind, "ConnectionZoneSpecification.kind")
        if self.kind is ConnectionZoneKind.WHOLE_PATCH:
            if self.rectangular_bounds is not None:
                raise ValueError("A whole-patch zone cannot define rectangular bounds.")
        elif not isinstance(self.rectangular_bounds, RectangularSubzoneBounds):
            raise TypeError("A rectangular-subzone zone requires RectangularSubzoneBounds.")


@dataclass(frozen=True, slots=True)
class InterfaceTargetSideSpecification:
    """One participant's nonempty, canonically ordered target-zone selection."""

    participant: ParticipantReference
    zones: tuple[ConnectionZoneSpecification, ...]
    primary_zone_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError(
                "InterfaceTargetSideSpecification.participant must be a ParticipantReference."
            )
        require_tuple(self.zones, "InterfaceTargetSideSpecification.zones")
        if not self.zones:
            raise ValueError("InterfaceTargetSideSpecification.zones must not be empty.")
        if any(not isinstance(zone, ConnectionZoneSpecification) for zone in self.zones):
            raise TypeError(
                "InterfaceTargetSideSpecification.zones items must be "
                "ConnectionZoneSpecification values."
            )
        zone_ids = tuple(zone.id for zone in self.zones)
        if len(set(zone_ids)) != len(zone_ids):
            raise ValueError("Connection-zone IDs must be unique within one target side.")
        validate_identifier(
            self.primary_zone_id,
            "InterfaceTargetSideSpecification.primary_zone_id",
        )
        if zone_ids.count(self.primary_zone_id) != 1:
            raise ValueError("The primary zone ID must resolve exactly once within its side.")
        if any(zone.surface_reference.participant != self.participant for zone in self.zones):
            raise ValueError("Every connection zone must reference its target-side participant.")
        object.__setattr__(self, "zones", tuple(sorted(self.zones, key=lambda zone: zone.id)))


@dataclass(frozen=True, slots=True)
class InterfaceOriginSpecification:
    """Explicit interface datum in the primary first-side surface's local plane."""

    primary_zone_id: str
    local_y: float
    local_z: float

    def __post_init__(self) -> None:
        validate_identifier(self.primary_zone_id, "InterfaceOriginSpecification.primary_zone_id")
        _require_finite_real(self.local_y, "InterfaceOriginSpecification.local_y")
        _require_finite_real(self.local_z, "InterfaceOriginSpecification.local_z")


@dataclass(frozen=True, slots=True)
class ConnectionInterfaceGeometrySpecification:
    """Geometry targeting associated with one exact logical connection interface."""

    interface: ConnectionInterface
    first_side: InterfaceTargetSideSpecification
    second_side: InterfaceTargetSideSpecification
    origin: InterfaceOriginSpecification
    in_plane_reference: Vector3D
    tolerance: GeometryComparisonTolerance

    def __post_init__(self) -> None:
        if not isinstance(self.interface, ConnectionInterface):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.interface must be a ConnectionInterface."
            )
        if not isinstance(self.first_side, InterfaceTargetSideSpecification):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.first_side must be an "
                "InterfaceTargetSideSpecification."
            )
        if not isinstance(self.second_side, InterfaceTargetSideSpecification):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.second_side must be an "
                "InterfaceTargetSideSpecification."
            )
        if self.first_side.participant != self.interface.participant_a:
            raise ValueError("The first target side must match interface participant_a.")
        if self.second_side.participant != self.interface.participant_b:
            raise ValueError("The second target side must match interface participant_b.")
        if not isinstance(self.origin, InterfaceOriginSpecification):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.origin must be an "
                "InterfaceOriginSpecification."
            )
        if self.origin.primary_zone_id != self.first_side.primary_zone_id:
            raise ValueError("The interface origin must name the primary first-side zone.")
        if not isinstance(self.in_plane_reference, Vector3D):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.in_plane_reference must be a Vector3D."
            )
        if not isinstance(self.tolerance, GeometryComparisonTolerance):
            raise TypeError(
                "ConnectionInterfaceGeometrySpecification.tolerance must be a "
                "GeometryComparisonTolerance."
            )


type PlanarTargetSurface3D = PlanarRectangularSurface3D | PlanarAnnularSurface3D


@dataclass(frozen=True, slots=True)
class ResolvedConnectionZone:
    """One exact zone resolved to its authoritative Stage 1.3C2A surface patch."""

    specification: ConnectionZoneSpecification
    surface: SurfacePatch3D

    def __post_init__(self) -> None:
        if not isinstance(self.specification, ConnectionZoneSpecification):
            raise TypeError(
                "ResolvedConnectionZone.specification must be a ConnectionZoneSpecification."
            )
        if not isinstance(self.surface, SurfacePatch3D):
            raise TypeError("ResolvedConnectionZone.surface must be a SurfacePatch3D.")
        if self.surface.reference != self.specification.surface_reference:
            raise ValueError("Resolved zone surface must match its exact surface reference.")
        geometry = _validate_targetable_planar_surface(self.surface)
        _validate_zone_geometry(self.specification, geometry)

    @property
    def id(self) -> str:
        return self.specification.id

    @property
    def geometry(self) -> PlanarTargetSurface3D:
        geometry = self.surface.geometry
        if not isinstance(geometry, (PlanarRectangularSurface3D, PlanarAnnularSurface3D)):
            raise RuntimeError("A validated resolved zone lost its planar geometry.")
        return geometry

    @property
    def normal(self) -> UnitVector3D:
        return self.geometry.normal

    @property
    def plane_point(self) -> PositionVector3D:
        return self.geometry.center


@dataclass(frozen=True, slots=True)
class ResolvedInterfaceTargetSide:
    """One validated participant side with exact canonical resolved zones."""

    participant: ParticipantReference
    zones: tuple[ResolvedConnectionZone, ...]
    primary_zone_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError(
                "ResolvedInterfaceTargetSide.participant must be a ParticipantReference."
            )
        require_tuple(self.zones, "ResolvedInterfaceTargetSide.zones")
        if not self.zones or any(
            not isinstance(zone, ResolvedConnectionZone) for zone in self.zones
        ):
            raise ValueError(
                "ResolvedInterfaceTargetSide.zones must be a nonempty tuple of resolved zones."
            )
        if any(zone.surface.participant != self.participant for zone in self.zones):
            raise ValueError("Every resolved zone must belong to the target-side participant.")
        zone_ids = tuple(zone.id for zone in self.zones)
        if len(set(zone_ids)) != len(zone_ids) or zone_ids.count(self.primary_zone_id) != 1:
            raise ValueError("Resolved target-side zone and primary IDs must be unambiguous.")
        if zone_ids != tuple(sorted(zone_ids)):
            raise ValueError("Resolved target-side zones must use deterministic ID ordering.")

    @property
    def primary_zone(self) -> ResolvedConnectionZone:
        for zone in self.zones:
            if zone.id == self.primary_zone_id:
                return zone
        raise RuntimeError("A validated resolved side lost its primary zone.")

    @property
    def normal(self) -> UnitVector3D:
        return self.primary_zone.normal

    @property
    def surface_references(self) -> tuple[SurfacePatchReference, ...]:
        return tuple(zone.specification.surface_reference for zone in self.zones)


@dataclass(frozen=True, slots=True)
class ResolvedConnectionInterfaceGeometry:
    """Resolved planar interface geometry with no engineering-calculation status."""

    interface: ConnectionInterface
    first_participant: ParticipantReference
    second_participant: ParticipantReference
    first_side: ResolvedInterfaceTargetSide
    second_side: ResolvedInterfaceTargetSide
    interface_frame: CartesianFrame3D
    signed_plane_separation: float
    tolerance: GeometryComparisonTolerance

    def __post_init__(self) -> None:
        if not isinstance(self.interface, ConnectionInterface):
            raise TypeError("Resolved interface geometry requires a ConnectionInterface.")
        if (
            self.first_participant != self.interface.participant_a
            or self.second_participant != self.interface.participant_b
        ):
            raise ValueError("Resolved participant order must equal the logical interface order.")
        if not isinstance(self.first_side, ResolvedInterfaceTargetSide) or not isinstance(
            self.second_side, ResolvedInterfaceTargetSide
        ):
            raise TypeError("Resolved interface geometry requires two resolved target sides.")
        if (
            self.first_side.participant != self.first_participant
            or self.second_side.participant != self.second_participant
        ):
            raise ValueError("Resolved target sides must match their retained participants.")
        if not isinstance(self.interface_frame, CartesianFrame3D):
            raise TypeError("Resolved interface geometry requires a CartesianFrame3D.")
        _require_finite_real(
            self.signed_plane_separation,
            "ResolvedConnectionInterfaceGeometry.signed_plane_separation",
        )
        if not isinstance(self.tolerance, GeometryComparisonTolerance):
            raise TypeError("Resolved interface geometry requires a comparison tolerance.")

    @property
    def interface_origin(self) -> PositionVector3D:
        return self.interface_frame.origin

    @property
    def first_side_normal(self) -> UnitVector3D:
        return self.first_side.normal

    @property
    def second_side_normal(self) -> UnitVector3D:
        return self.second_side.normal

    @property
    def is_coincident_within_tolerance(self) -> bool:
        return abs(self.signed_plane_separation) <= self.tolerance.distance_tolerance


def _validate_targetable_planar_surface(surface: SurfacePatch3D) -> PlanarTargetSurface3D:
    if surface.disposition is not SurfaceDisposition.REGULAR:
        raise ValueError("A deferred surface patch cannot receive a connection zone.")
    if surface.exposure is SurfaceExposure.INTERNAL_JUNCTION:
        raise ValueError("An internal-junction patch cannot receive a connection zone.")
    if not isinstance(surface.geometry, (PlanarRectangularSurface3D, PlanarAnnularSurface3D)):
        raise ValueError("Stage 1.3C2B targets only planar rectangles and planar annuli.")
    return surface.geometry


def _validate_zone_geometry(
    specification: ConnectionZoneSpecification,
    geometry: PlanarTargetSurface3D,
) -> None:
    if specification.kind is ConnectionZoneKind.WHOLE_PATCH:
        return
    if not isinstance(geometry, PlanarRectangularSurface3D):
        raise ValueError("Rectangular subzones require a planar rectangular surface.")
    bounds = specification.rectangular_bounds
    if bounds is None:
        raise RuntimeError("A validated rectangular subzone lost its bounds.")
    half_y = geometry.extent_y / 2.0
    half_z = geometry.extent_z / 2.0
    if not (
        bounds.min_y >= -half_y
        and bounds.max_y <= half_y
        and bounds.min_z >= -half_z
        and bounds.max_z <= half_z
    ):
        raise ValueError("Rectangular subzone bounds must lie within the source patch.")


def _resolve_surface(
    reference: SurfacePatchReference,
    surfaces: tuple[SurfacePatch3D, ...],
) -> SurfacePatch3D:
    matches = tuple(surface for surface in surfaces if surface.reference == reference)
    if not matches:
        raise KeyError(
            f"Unresolved surface patch {reference.patch_id!r} for participant "
            f"{reference.participant.entity_id!r}."
        )
    if len(matches) != 1:
        raise ValueError("A surface reference must resolve to exactly one authoritative patch.")
    return matches[0]


def _rectangle_bounds(zone: ResolvedConnectionZone) -> RectangularSubzoneBounds:
    geometry = zone.geometry
    if not isinstance(geometry, PlanarRectangularSurface3D):
        raise TypeError("Rectangular overlap checks require rectangular source patches.")
    if zone.specification.kind is ConnectionZoneKind.WHOLE_PATCH:
        return RectangularSubzoneBounds(
            -geometry.extent_y / 2.0,
            geometry.extent_y / 2.0,
            -geometry.extent_z / 2.0,
            geometry.extent_z / 2.0,
        )
    bounds = zone.specification.rectangular_bounds
    if bounds is None:
        raise RuntimeError("A validated rectangular subzone lost its bounds.")
    return bounds


def _zones_have_duplicate_geometry(
    first: ResolvedConnectionZone,
    second: ResolvedConnectionZone,
) -> bool:
    if first.surface.reference == second.surface.reference:
        if isinstance(first.geometry, PlanarAnnularSurface3D):
            return True
        return _rectangle_bounds(first) == _rectangle_bounds(second)
    return (
        first.geometry == second.geometry
        and first.specification.kind == second.specification.kind
        and first.specification.rectangular_bounds == second.specification.rectangular_bounds
    )


def _validate_same_patch_pair(
    first: ResolvedConnectionZone,
    second: ResolvedConnectionZone,
) -> None:
    if first.surface.reference != second.surface.reference:
        return
    if (
        first.specification.kind is ConnectionZoneKind.WHOLE_PATCH
        or second.specification.kind is ConnectionZoneKind.WHOLE_PATCH
    ):
        raise ValueError("A whole-patch zone must be exclusive on its source patch.")
    first_bounds = _rectangle_bounds(first)
    second_bounds = _rectangle_bounds(second)
    positive_area_overlap = max(first_bounds.min_y, second_bounds.min_y) < min(
        first_bounds.max_y, second_bounds.max_y
    ) and max(first_bounds.min_z, second_bounds.min_z) < min(
        first_bounds.max_z, second_bounds.max_z
    )
    if positive_area_overlap:
        raise ValueError("Rectangular subzone interiors cannot overlap with positive area.")


def _resolve_side(
    specification: InterfaceTargetSideSpecification,
    surfaces: tuple[SurfacePatch3D, ...],
    tolerance: GeometryComparisonTolerance,
) -> ResolvedInterfaceTargetSide:
    zones = tuple(
        ResolvedConnectionZone(zone, _resolve_surface(zone.surface_reference, surfaces))
        for zone in specification.zones
    )
    for index, first in enumerate(zones):
        for second in zones[index + 1 :]:
            if _zones_have_duplicate_geometry(first, second):
                raise ValueError("A target side cannot contain duplicate zone geometry.")
            _validate_same_patch_pair(first, second)
    primary = next(zone for zone in zones if zone.id == specification.primary_zone_id)
    for zone in zones:
        if 1.0 - primary.normal.dot(zone.normal) > tolerance.angular_tolerance:
            raise ValueError("All target-side surface normals must have the same signed direction.")
        plane_offset = primary.normal.dot(vector_between(primary.plane_point, zone.plane_point))
        if abs(plane_offset) > tolerance.distance_tolerance:
            raise ValueError("All target-side zones must be coplanar with the primary zone.")
    return ResolvedInterfaceTargetSide(
        specification.participant,
        zones,
        specification.primary_zone_id,
    )


def _resolve_origin(
    specification: InterfaceOriginSpecification,
    first_side: ResolvedInterfaceTargetSide,
) -> PositionVector3D:
    if specification.primary_zone_id != first_side.primary_zone_id:
        raise ValueError("The origin must resolve through the primary first-side zone.")
    return first_side.primary_zone.geometry.frame.local_to_parent_point(
        PositionVector3D(0.0, specification.local_y, specification.local_z)
    )


def _build_interface_frame(
    origin: PositionVector3D,
    normal: UnitVector3D,
    reference: Vector3D,
    angular_tolerance: float,
) -> CartesianFrame3D:
    reference_norm = reference.norm
    if reference_norm == 0.0:
        raise ValueError("The interface in-plane reference direction must be nonzero.")
    alignment = abs(reference.dot(normal)) / reference_norm
    if 1.0 - alignment <= angular_tolerance:
        raise ValueError(
            "The interface in-plane reference cannot be parallel, antiparallel, or near parallel."
        )
    projected = reference - normal * reference.dot(normal)
    local_y = projected.normalized()
    local_z = normal.cross(local_y).normalized()
    local_y = local_z.cross(normal).normalized()
    return CartesianFrame3D(origin, normal, local_y, local_z)


def resolve_connection_interface_geometry(
    specification: ConnectionInterfaceGeometrySpecification,
    surfaces: tuple[SurfacePatch3D, ...],
) -> ResolvedConnectionInterfaceGeometry:
    """Resolve one logical interface against an explicit authoritative surface tuple."""
    if not isinstance(specification, ConnectionInterfaceGeometrySpecification):
        raise TypeError("specification must be a ConnectionInterfaceGeometrySpecification.")
    require_tuple(surfaces, "surfaces")
    if any(not isinstance(surface, SurfacePatch3D) for surface in surfaces):
        raise TypeError("surfaces items must be SurfacePatch3D values.")
    first_side = _resolve_side(
        specification.first_side,
        surfaces,
        specification.tolerance,
    )
    second_side = _resolve_side(
        specification.second_side,
        surfaces,
        specification.tolerance,
    )
    if 1.0 + first_side.normal.dot(second_side.normal) > specification.tolerance.angular_tolerance:
        raise ValueError("The second target-side normal must oppose the first target-side normal.")
    signed_separation = first_side.normal.dot(
        vector_between(
            first_side.primary_zone.plane_point,
            second_side.primary_zone.plane_point,
        )
    )
    if signed_separation < -specification.tolerance.distance_tolerance:
        raise ValueError("The first target-side normal points away from the second target plane.")
    origin = _resolve_origin(specification.origin, first_side)
    frame = _build_interface_frame(
        origin,
        first_side.normal,
        specification.in_plane_reference,
        specification.tolerance.angular_tolerance,
    )
    return ResolvedConnectionInterfaceGeometry(
        specification.interface,
        specification.interface.participant_a,
        specification.interface.participant_b,
        first_side,
        second_side,
        frame,
        signed_separation,
        specification.tolerance,
    )


__all__ = (
    "ConnectionInterfaceGeometrySpecification",
    "ConnectionZoneKind",
    "ConnectionZoneSpecification",
    "GeometryComparisonTolerance",
    "InterfaceOriginSpecification",
    "InterfaceTargetSideSpecification",
    "PlanarTargetSurface3D",
    "RectangularSubzoneBounds",
    "ResolvedConnectionInterfaceGeometry",
    "ResolvedConnectionZone",
    "ResolvedInterfaceTargetSide",
    "resolve_connection_interface_geometry",
)
