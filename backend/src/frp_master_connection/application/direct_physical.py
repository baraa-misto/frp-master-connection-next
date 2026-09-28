"""Physical checks specific to the Direct FRP angle-to-W member family."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from frp_master_connection.domain import ComponentMaterialKind, PositionVector3D, SectionFamily

from .calculation_orchestration import SingleBoltOrchestrationRequest
from .visualization import BoltDisplaySnapshot, SingleBoltVisualizationSnapshot, SurfaceZoneSnapshot


def is_direct_angle_w(request: SingleBoltOrchestrationRequest | None) -> bool:
    """Recognize the typed physical family, never a client label or material-pair enum."""

    if request is None or request.template_orientation is None:
        return False
    members = request.assembly.members
    return (
        len(members) == 2
        and members[0].section_family is SectionFamily.ANGLE
        and members[1].section_family is SectionFamily.WIDE_FLANGE
        and all(member.material_kind is ComponentMaterialKind.PULTRUDED_FRP for member in members)
    )


@dataclass(frozen=True, slots=True)
class DirectContainmentIssue:
    bolt_id: str
    component_id: str
    physical_element_id: str
    detail: str


def _coords(point: PositionVector3D) -> tuple[float, float, float]:
    return point.x, point.y, point.z


def _subtract(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return left[0] - right[0], left[1] - right[1], left[2] - right[2]


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _edge_clearance(zone: SurfaceZoneSnapshot, point: PositionVector3D) -> tuple[float, float]:
    """Return distance to plane and smallest signed interior edge distance."""

    corners = tuple(_coords(item) for item in zone.corners)
    if len(corners) != 4 or zone.geometry_kind != "PLANAR_RECTANGLE":
        raise ValueError("Direct contact region must be an authoritative planar rectangle.")
    normal = (zone.normal.x, zone.normal.y, zone.normal.z)
    actual = _coords(point)
    origin = corners[0]
    plane = abs(_dot(_subtract(actual, origin), normal))
    center = _coords(zone.center)
    clearances: list[float] = []
    for index, start in enumerate(corners):
        end = corners[(index + 1) % 4]
        edge = _subtract(end, start)
        length = math.sqrt(_dot(edge, edge))
        if length <= 0:
            raise ValueError("Direct contact region contains a zero-length edge.")
        center_side = _dot(_cross(edge, _subtract(center, start)), normal)
        actual_side = _dot(_cross(edge, _subtract(actual, start)), normal)
        if center_side == 0:
            raise ValueError("Direct contact region has no resolved interior.")
        clearances.append(actual_side / length * (1 if center_side > 0 else -1))
    return plane, min(clearances)


def direct_bolt_containment_issues(
    snapshot: SingleBoltVisualizationSnapshot,
    bolts: Sequence[BoltDisplaySnapshot],
) -> tuple[DirectContainmentIssue, ...]:
    """Check every actual hole and washer footprint against its penetrated FRP face."""

    issues: list[DirectContainmentIssue] = []
    members = {component.id: component for component in snapshot.components}
    for bolt in bolts:
        if len(bolt.holes) != 2:
            issues.append(
                DirectContainmentIssue(bolt.bolt_location_id, "", "", "Two FRP holes are required.")
            )
            continue
        for index, hole in enumerate(bolt.holes):
            component = members.get(hole.participant_id)
            if (
                component is None
                or component.material_kind is not ComponentMaterialKind.PULTRUDED_FRP
            ):
                issues.append(
                    DirectContainmentIssue(
                        bolt.bolt_location_id,
                        hole.participant_id,
                        hole.physical_element_id,
                        "A penetrated FRP component is missing.",
                    )
                )
                continue
            zones = tuple(
                zone
                for zone in snapshot.interface_zones
                if zone.participant_id == hole.participant_id
                and zone.patch_id.startswith(f"{hole.physical_element_id}:")
            )
            if len(zones) != 1:
                issues.append(
                    DirectContainmentIssue(
                        bolt.bolt_location_id,
                        hole.participant_id,
                        hole.physical_element_id,
                        "The actual penetrated face is unresolved.",
                    )
                )
                continue
            zone = zones[0]
            start_plane, start_clearance = _edge_clearance(zone, hole.start)
            end_plane, end_clearance = _edge_clearance(zone, hole.end)
            plane, clearance = min(
                ((start_plane, start_clearance), (end_plane, end_clearance)),
                key=lambda value: value[0],
            )
            washer = next(
                (
                    item
                    for item in bolt.washers
                    if item.location == ("UNDER_HEAD" if index == 0 else "UNDER_NUT")
                ),
                None,
            )
            if washer is None:
                issues.append(
                    DirectContainmentIssue(
                        bolt.bolt_location_id,
                        hole.participant_id,
                        hole.physical_element_id,
                        "The required washer is missing.",
                    )
                )
                continue
            minimum = max(
                1.5 * bolt.bolt_diameter,
                hole.diameter / 2,
                washer.outside_diameter / 2,
            )
            if plane > 1e-6 or clearance + 1e-9 < minimum:
                issues.append(
                    DirectContainmentIssue(
                        bolt.bolt_location_id,
                        hole.participant_id,
                        hole.physical_element_id,
                        f"Physical hole/washer or Chapter 8 side clearance outside face: "
                        f"available={clearance:.6g}; required={minimum:.6g}; plane={plane:.6g}.",
                    )
                )
    return tuple(issues)


def direct_material_force_angle(
    snapshot: SingleBoltVisualizationSnapshot,
    component_id: str,
    physical_element_id: str,
    force_global: tuple[float, float, float],
) -> float:
    """Resolve the acute material/force angle from physical axes in one snapshot."""

    direction = next(
        (
            item
            for item in snapshot.material_directions
            if item.component_id == component_id and item.physical_element_id == physical_element_id
        ),
        None,
    )
    if direction is None or direction.lengthwise is None:
        raise ValueError("DIRECT_MATERIAL_AXIS_UNRESOLVED")
    vector = direction.lengthwise
    axis = (vector.x, vector.y, vector.z)
    magnitude = math.sqrt(_dot(force_global, force_global))
    if magnitude <= 0:
        raise ValueError("DIRECT_IN_PLANE_FORCE_REQUIRED")
    cosine = abs(_dot(force_global, axis)) / magnitude
    return math.degrees(math.acos(min(1.0, max(0.0, cosine))))


def direct_material_axis_angle(
    snapshot: SingleBoltVisualizationSnapshot,
    component_id: str,
    physical_element_id: str,
) -> float:
    """Return the physical material axis in the canonical bolt-group plane."""

    direction = next(
        (
            item
            for item in snapshot.material_directions
            if item.component_id == component_id and item.physical_element_id == physical_element_id
        ),
        None,
    )
    frame = next(
        (
            item.frame
            for item in snapshot.frames
            if item.kind.value == "BOLT_GROUP_LOCAL" and item.owner_id == snapshot.bolt_group_id
        ),
        None,
    )
    if direction is None or direction.lengthwise is None or frame is None:
        raise ValueError("DIRECT_MATERIAL_AXIS_UNRESOLVED")
    axis = direction.lengthwise
    normal = _dot(
        (axis.x, axis.y, axis.z),
        (frame.x_axis.x, frame.x_axis.y, frame.x_axis.z),
    )
    if abs(normal) > 1e-6:
        raise ValueError("DIRECT_MATERIAL_AXIS_NOT_IN_BOLT_PLANE")
    u = _dot((axis.x, axis.y, axis.z), (frame.y_axis.x, frame.y_axis.y, frame.y_axis.z))
    v = _dot((axis.x, axis.y, axis.z), (frame.z_axis.x, frame.z_axis.y, frame.z_axis.z))
    return math.degrees(math.atan2(v, u)) % 180.0
