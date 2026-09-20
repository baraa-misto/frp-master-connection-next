"""Backend-authoritative half-space trimming for prismatic member solids.

Standard profile builders remain the sole authority for source solids. This
module clips those already-placed wall/leg prisms and never substitutes a
simplified profile.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass

from frp_master_connection.domain import PositionVector3D

from .placement import (
    LocalRectangularPrism3D,
    PlacedComponentGeometry3D,
    PlacedPhysicalElement3D,
)
from .spatial import UnitVector3D, Vector3D


@dataclass(frozen=True, slots=True)
class AuthoritativeCutPlane3D:
    """A global plane whose positive half-space is retained."""

    id: str
    origin: PositionVector3D
    normal: UnitVector3D

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("AuthoritativeCutPlane3D.id must be nonempty.")
        if not isinstance(self.origin, PositionVector3D):
            raise TypeError("AuthoritativeCutPlane3D.origin must be a PositionVector3D.")
        if not isinstance(self.normal, UnitVector3D):
            raise TypeError("AuthoritativeCutPlane3D.normal must be a UnitVector3D.")


@dataclass(frozen=True, slots=True)
class TrimmedPlanarFace3D:
    """One finite planar boundary face of a trimmed solid."""

    id: str
    vertices: tuple[PositionVector3D, ...]
    is_fabricated_cut: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("TrimmedPlanarFace3D.id must be nonempty.")
        if len(self.vertices) < 3:
            raise ValueError("TrimmedPlanarFace3D requires at least three vertices.")


@dataclass(frozen=True, slots=True)
class TrimmedPhysicalSolid3D:
    """One exact-source rectangular prism after half-space clipping."""

    physical_element_id: str
    material_region_id: str
    faces: tuple[TrimmedPlanarFace3D, ...]

    @property
    def vertices(self) -> tuple[PositionVector3D, ...]:
        return _unique_points(point for face in self.faces for point in face.vertices)

    @property
    def triangulated_points(self) -> tuple[PositionVector3D, ...]:
        triangles: list[PositionVector3D] = []
        for face in self.faces:
            first = face.vertices[0]
            for index in range(1, len(face.vertices) - 1):
                triangles.extend((first, face.vertices[index], face.vertices[index + 1]))
        return tuple(triangles)


@dataclass(frozen=True, slots=True)
class TrimmedComponentSolids3D:
    """Trim result for every wall/leg solid of one standard profile."""

    component_id: str
    cut_plane: AuthoritativeCutPlane3D
    solids: tuple[TrimmedPhysicalSolid3D, ...]
    geometry_fingerprint: str

    @property
    def fabricated_face_ids(self) -> tuple[str, ...]:
        return tuple(
            face.id for solid in self.solids for face in solid.faces if face.is_fabricated_cut
        )


_BOX_FACE_INDICES = (
    ("MINIMUM_LOCAL_X", (0, 1, 3, 2)),
    ("MAXIMUM_LOCAL_X", (4, 6, 7, 5)),
    ("MINIMUM_LOCAL_Y", (0, 4, 5, 1)),
    ("MAXIMUM_LOCAL_Y", (2, 3, 7, 6)),
    ("MINIMUM_LOCAL_Z", (0, 2, 6, 4)),
    ("MAXIMUM_LOCAL_Z", (1, 5, 7, 3)),
)


def _delta(first: PositionVector3D, second: PositionVector3D) -> Vector3D:
    return Vector3D(first.x - second.x, first.y - second.y, first.z - second.z)


def signed_distance_to_plane(
    point: PositionVector3D,
    plane: AuthoritativeCutPlane3D,
) -> float:
    """Return positive distance on the retained side of an authoritative plane."""

    return _delta(point, plane.origin).dot(plane.normal)


def _interpolate(
    first: PositionVector3D,
    second: PositionVector3D,
    first_distance: float,
    second_distance: float,
) -> PositionVector3D:
    ratio = first_distance / (first_distance - second_distance)
    return PositionVector3D(
        first.x + ratio * (second.x - first.x),
        first.y + ratio * (second.y - first.y),
        first.z + ratio * (second.z - first.z),
    )


def _same_point(first: PositionVector3D, second: PositionVector3D, tolerance: float) -> bool:
    return (
        abs(first.x - second.x) <= tolerance
        and abs(first.y - second.y) <= tolerance
        and abs(first.z - second.z) <= tolerance
    )


def _unique_points(
    points: Iterable[PositionVector3D],
    tolerance: float = 1e-9,
) -> tuple[PositionVector3D, ...]:
    result: list[PositionVector3D] = []
    for point in points:
        if not any(_same_point(point, existing, tolerance) for existing in result):
            result.append(point)
    return tuple(result)


def _clip_face(
    vertices: tuple[PositionVector3D, ...],
    plane: AuthoritativeCutPlane3D,
    tolerance: float,
) -> tuple[tuple[PositionVector3D, ...], tuple[PositionVector3D, ...]]:
    retained: list[PositionVector3D] = []
    intersections: list[PositionVector3D] = []
    for index, current in enumerate(vertices):
        following = vertices[(index + 1) % len(vertices)]
        current_distance = signed_distance_to_plane(current, plane)
        following_distance = signed_distance_to_plane(following, plane)
        current_inside = current_distance >= -tolerance
        following_inside = following_distance >= -tolerance
        if current_inside:
            retained.append(current)
        if current_inside != following_inside:
            intersection = _interpolate(
                current,
                following,
                current_distance,
                following_distance,
            )
            retained.append(intersection)
            intersections.append(intersection)
    return _unique_points(retained, tolerance), _unique_points(intersections, tolerance)


def _ordered_cut_face(
    points: tuple[PositionVector3D, ...],
    plane: AuthoritativeCutPlane3D,
) -> tuple[PositionVector3D, ...]:
    center = PositionVector3D(
        sum(point.x for point in points) / len(points),
        sum(point.y for point in points) / len(points),
        sum(point.z for point in points) / len(points),
    )
    reference = Vector3D(1.0, 0.0, 0.0)
    if abs(reference.dot(plane.normal)) > 0.9:
        reference = Vector3D(0.0, 1.0, 0.0)
    first_axis = plane.normal.cross(reference).normalized()
    second_axis = plane.normal.cross(first_axis).normalized()
    return tuple(
        sorted(
            points,
            key=lambda point: math.atan2(
                _delta(point, center).dot(second_axis),
                _delta(point, center).dot(first_axis),
            ),
        )
    )


def trim_placed_rectangular_component(
    placed: PlacedComponentGeometry3D,
    plane: AuthoritativeCutPlane3D,
    tolerance: float = 1e-9,
) -> TrimmedComponentSolids3D:
    """Clip every exact rectangular wall/leg extrusion by ``plane``."""

    solids: list[TrimmedPhysicalSolid3D] = []
    for physical in placed.physical_elements:
        for extrusion_index, prism in enumerate(physical.extrusions):
            if not isinstance(prism, LocalRectangularPrism3D):
                raise ValueError("Member end trim does not support round-tube solids.")
            local = tuple(
                PositionVector3D(x, y, z)
                for x in (prism.extent.x_start, prism.extent.x_end)
                for y in (prism.rectangle.min_y, prism.rectangle.max_y)
                for z in (prism.rectangle.min_z, prism.rectangle.max_z)
            )
            global_vertices = tuple(
                physical.global_frame.local_to_parent_point(point) for point in local
            )
            faces: list[TrimmedPlanarFace3D] = []
            cut_points: list[PositionVector3D] = []
            for face_name, indices in _BOX_FACE_INDICES:
                clipped, intersections = _clip_face(
                    tuple(global_vertices[index] for index in indices),
                    plane,
                    tolerance,
                )
                cut_points.extend(intersections)
                if len(clipped) >= 3:
                    faces.append(
                        TrimmedPlanarFace3D(
                            f"{physical.source_element.id}:{extrusion_index}:{face_name}",
                            clipped,
                        )
                    )
            unique_cut = _unique_points(cut_points, tolerance)
            if len(unique_cut) >= 3:
                faces.append(
                    TrimmedPlanarFace3D(
                        f"{physical.source_element.id}:{extrusion_index}:CUT:{plane.id}",
                        _ordered_cut_face(unique_cut, plane),
                        True,
                    )
                )
            if faces:
                solids.append(
                    TrimmedPhysicalSolid3D(
                        physical.source_element.id,
                        physical.source_material_region.id,
                        tuple(faces),
                    )
                )
    if not solids:
        raise ValueError("The member end trim removed every connected-member solid.")
    identity = {
        "component": placed.component.id,
        "plane": plane.id,
        "origin": [
            format(value, ".17g") for value in (plane.origin.x, plane.origin.y, plane.origin.z)
        ],
        "normal": [
            format(value, ".17g") for value in (plane.normal.x, plane.normal.y, plane.normal.z)
        ],
        "faces": [
            [
                face.id,
                [
                    [format(point.x, ".17g"), format(point.y, ".17g"), format(point.z, ".17g")]
                    for point in face.vertices
                ],
            ]
            for solid in solids
            for face in solid.faces
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, separators=(",", ":"), sort_keys=True).encode("ascii")
    ).hexdigest()
    return TrimmedComponentSolids3D(placed.component.id, plane, tuple(solids), fingerprint)


def placed_rectangular_elements_overlap(
    first: PlacedPhysicalElement3D,
    second: PlacedPhysicalElement3D,
    tolerance: float = 1e-9,
) -> bool:
    """Return whether two one-prism physical elements overlap with positive volume."""

    def box(
        element: PlacedPhysicalElement3D,
    ) -> tuple[PositionVector3D, tuple[Vector3D, ...], tuple[float, ...]]:
        if len(element.extrusions) != 1 or not isinstance(
            element.extrusions[0], LocalRectangularPrism3D
        ):
            raise ValueError("Interference requires one rectangular prism per element.")
        prism = element.extrusions[0]
        center = element.global_frame.local_to_parent_point(
            PositionVector3D(
                (prism.extent.x_start + prism.extent.x_end) / 2.0,
                (prism.rectangle.min_y + prism.rectangle.max_y) / 2.0,
                (prism.rectangle.min_z + prism.rectangle.max_z) / 2.0,
            )
        )
        return (
            center,
            (
                element.global_frame.x_axis,
                element.global_frame.y_axis,
                element.global_frame.z_axis,
            ),
            (
                prism.extent.length / 2.0,
                (prism.rectangle.max_y - prism.rectangle.min_y) / 2.0,
                (prism.rectangle.max_z - prism.rectangle.min_z) / 2.0,
            ),
        )

    first_center, first_axes, first_half = box(first)
    second_center, second_axes, second_half = box(second)
    center_delta = _delta(second_center, first_center)
    candidates = [*first_axes, *second_axes]
    candidates.extend(
        first_axis.cross(second_axis) for first_axis in first_axes for second_axis in second_axes
    )
    for candidate in candidates:
        if candidate.norm <= tolerance:
            continue
        axis = candidate.normalized()
        first_radius = sum(
            half * abs(source_axis.dot(axis))
            for half, source_axis in zip(first_half, first_axes, strict=True)
        )
        second_radius = sum(
            half * abs(source_axis.dot(axis))
            for half, source_axis in zip(second_half, second_axes, strict=True)
        )
        if first_radius + second_radius - abs(center_delta.dot(axis)) <= tolerance:
            return False
    return True


__all__ = (
    "AuthoritativeCutPlane3D",
    "TrimmedComponentSolids3D",
    "TrimmedPhysicalSolid3D",
    "TrimmedPlanarFace3D",
    "placed_rectangular_elements_overlap",
    "signed_distance_to_plane",
    "trim_placed_rectangular_component",
)
