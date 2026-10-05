"""Direct-only engineering edges and represented hardware fit from physical solids.

Contact patches locate penetrations; they do not supply Chapter 8 boundaries.
Camera geometry and view-extension primitives never enter this resolver.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation import PhysicalQuantity, Unit, decimal_from_finite_real
from frp_master_connection.domain import ComponentMaterialKind, PositionVector3D
from frp_master_connection.geometry.spatial import (
    DIMENSIONLESS_MATHEMATICAL_TOLERANCE,
    CartesianFrame3D,
    Vector3D,
)

from .direct_physical import DirectContainmentIssue
from .visualization import (
    BoltDisplaySnapshot,
    SingleBoltVisualizationSnapshot,
    VisualizationPrimitive,
    VisualizationPrimitiveKind,
    VisualizationResolutionStatus,
)

type Coordinates = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class DirectEngineeringBoundary:
    component_id: str
    physical_element_id: str
    boundary_id: str
    role: str
    label: str
    source_geometry_id: str
    start_global: Coordinates
    end_global: Coordinates
    start_local: Coordinates
    end_local: Coordinates
    dimension_end_local: Coordinates
    actual_distance: Decimal
    raw_distance: Decimal
    eligible_e1: bool
    eligible_e2: bool
    hardware_eligible: bool
    computational_only: bool = False


@dataclass(frozen=True, slots=True)
class DirectEngineeringCheck:
    check_kind: str
    component_id: str
    physical_element_id: str
    bolt_id: str
    engineering_boundary_id: str
    engineering_boundary_role: str
    source_geometry_id: str
    actual_distance: Decimal
    required_distance: Decimal
    unit: str
    pass_fail: str
    source_rule: str
    associated_contact_patch_id: str
    boundary_label: str
    contact_patch_boundary_used_as_engineering_edge: bool = False


@dataclass(frozen=True, slots=True)
class DirectEngineeringFace:
    bolt_id: str
    component_id: str
    physical_element_id: str
    source_geometry_id: str
    associated_contact_patch_id: str
    bolt_center_global: Coordinates
    bolt_center_member_local: Coordinates
    raw_bolt_center_member_local: Coordinates
    penetration_point_member_local: Coordinates
    raw_penetration_point_member_local: Coordinates
    coordinate_canonicalization: str
    normal_axis: int
    transverse_axis: int
    face_vertices_local: tuple[Coordinates, ...]
    boundaries: tuple[DirectEngineeringBoundary, ...]
    checks: tuple[DirectEngineeringCheck, ...]
    hole_radius: Decimal
    washer_radius: Decimal
    limitations: tuple[str, ...] = (
        "Nut/head envelope and unresolved heel/fillet geometry are not supplied; "
        "only represented holes, bolt shafts, washers and exact section solids are evaluated.",
    )


def _coordinates(point: PositionVector3D) -> Coordinates:
    return point.x, point.y, point.z


def _box_limits(primitive: VisualizationPrimitive) -> tuple[Coordinates, Coordinates]:
    values = {item.name: item.value for item in primitive.parameters}
    return (
        (values["x_start"], values["min_y"], values["min_z"]),
        (values["x_end"], values["max_y"], values["max_z"]),
    )


def _normal_axis(frame: CartesianFrame3D, bolt: BoltDisplaySnapshot) -> int:
    axis = frame.parent_to_local_vector(Vector3D(bolt.axis.x, bolt.axis.y, bolt.axis.z))
    values = (axis.x, axis.y, axis.z)
    ordinal = max(range(3), key=lambda item: abs(values[item]))
    if ordinal == 0 or abs(abs(values[ordinal]) - 1) > DIMENSIONLESS_MATHEMATICAL_TOLERANCE:
        raise ValueError("Direct penetration normal is not a supported section-thickness axis.")
    return ordinal


def _boundary(
    primitive: VisualizationPrimitive,
    frame: CartesianFrame3D,
    point: Coordinates,
    raw_point: Coordinates,
    axis: int,
    coordinate: float,
    minimum: bool,
    role: str,
    label: str,
    normal: int,
) -> DirectEngineeringBoundary:
    lower, upper = _box_limits(primitive)
    other = 3 - normal - axis
    start, end, foot = list(point), list(point), list(point)
    start[axis] = end[axis] = foot[axis] = coordinate
    start[other], end[other] = lower[other], upper[other]
    a, b, f = tuple(start), tuple(end), tuple(foot)
    sign = 1 if minimum else -1
    return DirectEngineeringBoundary(
        primitive.owner_id,
        str(primitive.physical_element_id),
        f"{primitive.id}:PHYSICAL:{axis}:{'MIN' if minimum else 'MAX'}",
        role,
        label,
        primitive.id,
        _coordinates(frame.local_to_parent_point(PositionVector3D(*a))),
        _coordinates(frame.local_to_parent_point(PositionVector3D(*b))),
        (a[0], a[1], a[2]),
        (b[0], b[1], b[2]),
        (f[0], f[1], f[2]),
        (decimal_from_finite_real(point[axis]) - decimal_from_finite_real(coordinate)) * sign,
        (decimal_from_finite_real(raw_point[axis]) - decimal_from_finite_real(coordinate)) * sign,
        role == "PHYSICAL_LOADED_END",
        role == "PHYSICAL_FREE_SIDE_EDGE",
        True,
    )


def _check(
    kind: str,
    bolt: BoltDisplaySnapshot,
    boundary: DirectEngineeringBoundary,
    required: Decimal,
    unit: Unit,
    patch: str,
    source: str,
    *,
    actual: Decimal | None = None,
) -> DirectEngineeringCheck:
    distance = boundary.actual_distance if actual is None else actual
    return DirectEngineeringCheck(
        kind,
        boundary.component_id,
        boundary.physical_element_id,
        bolt.bolt_location_id,
        boundary.boundary_id,
        boundary.role,
        boundary.source_geometry_id,
        distance,
        required,
        unit.value,
        "PASS" if distance >= required else "FAIL",
        source,
        patch,
        boundary.label,
    )


def _obstruction_clearance(
    primitive: VisualizationPrimitive,
    frame: CartesianFrame3D,
    start: PositionVector3D,
    end: PositionVector3D,
    normal: int,
) -> Decimal | None:
    """Circle-to-box clearance when the finite cylinder overlaps its axial slab."""
    lower, upper = _box_limits(primitive)
    a = _coordinates(frame.parent_to_local_point(start))
    b = _coordinates(frame.parent_to_local_point(end))
    if min(max(a[normal], b[normal]), upper[normal]) <= max(
        min(a[normal], b[normal]), lower[normal]
    ):
        return None
    squared = sum(max(lower[i] - a[i], a[i] - upper[i], 0.0) ** 2 for i in range(3) if i != normal)
    return decimal_from_finite_real(math.sqrt(squared))


def direct_engineering_geometry(
    snapshot: SingleBoltVisualizationSnapshot,
    bolts: Sequence[BoltDisplaySnapshot],
    *,
    row_count: int,
    force_global: Coordinates,
    brace_local_x: Mapping[str, Decimal],
) -> tuple[DirectEngineeringFace, ...]:
    """Evaluate separate physical checks; retain raw coordinates and patch witnesses.

    Direct's template is collinear with the canonical row axis. A supplied native
    brace x can replace inverse-transform residue only within the existing template
    distance precision (1e-9 in). No minimum is relaxed and W coordinates are unsnapped.
    """
    members = {item.id: item for item in snapshot.components}
    frames = {item.id: item.frame for item in snapshot.frames}
    solids = tuple(
        item
        for item in snapshot.primitives
        if item.kind is VisualizationPrimitiveKind.BOX
        and item.resolution_status is VisualizationResolutionStatus.EXACT
    )
    distance_precision = float(
        PhysicalQuantity.of("1e-9", Unit.IN).to(snapshot.length_unit).magnitude
    )
    faces: list[DirectEngineeringFace] = []
    for bolt in bolts:
        if len(bolt.holes) != 2:
            raise ValueError("Direct requires two represented FRP holes.")
        for index, hole in enumerate(bolt.holes):
            member = members.get(hole.participant_id)
            if member is None or member.material_kind is not ComponentMaterialKind.PULTRUDED_FRP:
                raise ValueError("Direct penetrated FRP component is unresolved.")
            primitive = next(
                (
                    s
                    for s in solids
                    if s.owner_id == hole.participant_id
                    and s.physical_element_id == hole.physical_element_id
                ),
                None,
            )
            if primitive is None:
                raise ValueError("Direct penetrated physical solid is unresolved.")
            frame = frames[primitive.frame_id]
            normal = _normal_axis(frame, bolt)
            transverse = 3 - normal
            raw_point = _coordinates(frame.parent_to_local_point(hole.start))
            raw_center = _coordinates(frame.parent_to_local_point(bolt.center))
            center = raw_center
            point = raw_point
            canonicalization = "NONE"
            if member.section_family == "ANGLE":
                native_x = brace_local_x[bolt.bolt_location_id]
                if abs(raw_point[0] - float(native_x)) > distance_precision:
                    raise ValueError(
                        "Direct canonical row and physical brace coordinates disagree."
                    )
                point = (float(native_x), raw_point[1], raw_point[2])
                center = (float(native_x), raw_center[1], raw_center[2])
                canonicalization = "DIRECT_NATIVE_ROW_X_WITHIN_TEMPLATE_FRAME_PRECISION"
            zones = tuple(
                z
                for z in snapshot.interface_zones
                if z.participant_id == hole.participant_id
                and z.patch_id.startswith(f"{hole.physical_element_id}:")
            )
            if len(zones) != 1:
                raise ValueError("Direct selected penetration plane is unresolved.")
            zone = zones[0]
            plane_distance = min(
                abs(
                    zone.normal.x * (p.x - zone.center.x)
                    + zone.normal.y * (p.y - zone.center.y)
                    + zone.normal.z * (p.z - zone.center.z)
                )
                for p in (hole.start, hole.end)
            )
            if plane_distance > distance_precision:
                raise ValueError(
                    "Direct physical hole does not meet the selected penetration plane."
                )
            lower, upper = _box_limits(primitive)
            local_force = frame.parent_to_local_vector(Vector3D(*force_global))
            loaded_max = local_force.x >= 0
            boundaries: list[DirectEngineeringBoundary] = []
            for minimum, bound in ((True, lower[0]), (False, upper[0])):
                loaded = minimum != loaded_max
                boundaries.append(
                    _boundary(
                        primitive,
                        frame,
                        point,
                        raw_point,
                        0,
                        bound,
                        minimum,
                        "PHYSICAL_LOADED_END" if loaded else "PHYSICAL_UNLOADED_END",
                        "loaded physical member end" if loaded else "unloaded physical member end",
                        normal,
                    )
                )
            for minimum, bound in ((True, lower[transverse]), (False, upper[transverse])):
                internal = member.section_family == "ANGLE" and minimum
                boundaries.append(
                    _boundary(
                        primitive,
                        frame,
                        point,
                        raw_point,
                        transverse,
                        bound,
                        minimum,
                        "INTERNAL_SECTION_JUNCTION" if internal else "PHYSICAL_FREE_SIDE_EDGE",
                        "angle heel / perpendicular-leg junction"
                        if internal
                        else (
                            "negative physical free side edge"
                            if minimum
                            else "positive physical free side edge"
                        ),
                        normal,
                    )
                )
            washer = next(
                (
                    w
                    for w in bolt.washers
                    if w.location == ("UNDER_HEAD" if index == 0 else "UNDER_NUT")
                ),
                None,
            )
            if washer is None:
                raise ValueError("Direct required represented washer is missing.")
            diameter = decimal_from_finite_real(bolt.bolt_diameter)
            hole_radius = decimal_from_finite_real(hole.diameter) / 2
            washer_radius = decimal_from_finite_real(washer.outside_diameter) / 2
            checks: list[DirectEngineeringCheck] = []
            for boundary in boundaries:
                if boundary.eligible_e2:
                    checks.append(
                        _check(
                            "CHAPTER_8_EDGE_DISTANCE",
                            bolt,
                            boundary,
                            Decimal("1.5") * diameter,
                            snapshot.length_unit,
                            zone.patch_id,
                            "ASCE/SEI 74-23 8.2.5 / Table 8-1 ordinary e2 = 1.5d",
                        )
                    )
                if boundary.eligible_e1:
                    checks.append(
                        _check(
                            "CHAPTER_8_END_DISTANCE",
                            bolt,
                            boundary,
                            (4 if row_count == 1 and local_force.x >= 0 else 2) * diameter,
                            snapshot.length_unit,
                            zone.patch_id,
                            "ASCE/SEI 74-23 Table 8-1 e1: tension one row 4d; two/three rows "
                            "and compression 2d; "
                            "no perpendicular-wall exemption assumed",
                        )
                    )
                checks.append(
                    _check(
                        "HOLE_PHYSICAL_CONTAINMENT",
                        bolt,
                        boundary,
                        hole_radius,
                        snapshot.length_unit,
                        zone.patch_id,
                        "Hole footprint inside exact penetrated element",
                    )
                )
                checks.append(
                    _check(
                        "WASHER_SEATING",
                        bolt,
                        boundary,
                        washer_radius,
                        snapshot.length_unit,
                        zone.patch_id,
                        "Represented washer footprint on physical FRP face",
                    )
                )
            # Exact other solids may obstruct a washer or the intended penetration.
            # The deferred heel is not promoted to an invented fillet or exact solid.
            for obstruction in solids:
                if obstruction is primitive:
                    continue
                obstruction_frame = frames[obstruction.frame_id]
                obstruction_normal = _normal_axis(obstruction_frame, bolt)
                for kind, start, end, radius in (
                    ("WASHER_SEATING", washer.start, washer.end, washer_radius),
                    ("COMPONENT_INTERFERENCE", hole.start, hole.end, hole_radius),
                ):
                    if kind == "COMPONENT_INTERFERENCE" and any(
                        h.participant_id == obstruction.owner_id
                        and h.physical_element_id == obstruction.physical_element_id
                        for h in bolt.holes
                    ):
                        # These are the declared penetrations, including their
                        # shared interface. They are intended physical holes.
                        continue
                    clearance = _obstruction_clearance(
                        obstruction, obstruction_frame, start, end, obstruction_normal
                    )
                    if clearance is None:
                        continue
                    # Touching is not positive-volume interference. Seating at
                    # the exact radius is permitted; penetration is never erased.
                    obstruction_lower, obstruction_upper = _box_limits(obstruction)
                    obstacle_point = _coordinates(obstruction_frame.parent_to_local_point(start))
                    foot = list(obstacle_point)
                    for ordinal in range(3):
                        if ordinal != obstruction_normal:
                            foot[ordinal] = max(
                                obstruction_lower[ordinal],
                                min(obstruction_upper[ordinal], foot[ordinal]),
                            )
                    distance_axis = max(
                        (i for i in range(3) if i != obstruction_normal),
                        key=lambda i: abs(foot[i] - obstacle_point[i]),
                    )
                    other_axis = 3 - obstruction_normal - distance_axis
                    edge_start, edge_end = list(foot), list(foot)
                    edge_start[other_axis] = obstruction_lower[other_axis]
                    edge_end[other_axis] = obstruction_upper[other_axis]
                    start_global = obstruction_frame.local_to_parent_point(
                        PositionVector3D(*edge_start)
                    )
                    end_global = obstruction_frame.local_to_parent_point(
                        PositionVector3D(*edge_end)
                    )
                    foot_global = obstruction_frame.local_to_parent_point(PositionVector3D(*foot))
                    marker = DirectEngineeringBoundary(
                        primitive.owner_id,
                        str(primitive.physical_element_id),
                        f"{obstruction.id}:OBSTRUCTION",
                        "INTERNAL_SECTION_JUNCTION"
                        if obstruction.owner_id == primitive.owner_id
                        else "OTHER_PHYSICAL_BOUNDARY",
                        f"clearance to {obstruction.owner_id} {obstruction.physical_element_id}",
                        obstruction.id,
                        _coordinates(start_global),
                        _coordinates(end_global),
                        _coordinates(frame.parent_to_local_point(start_global)),
                        _coordinates(frame.parent_to_local_point(end_global)),
                        _coordinates(frame.parent_to_local_point(foot_global)),
                        clearance,
                        clearance,
                        False,
                        False,
                        True,
                    )
                    boundaries.append(marker)
                    checks.append(
                        _check(
                            kind,
                            bolt,
                            marker,
                            radius,
                            snapshot.length_unit,
                            zone.patch_id,
                            "Exact cylinder / represented physical section solid interference",
                        )
                    )
            vertices = []
            for x, cross in (
                (lower[0], lower[transverse]),
                (upper[0], lower[transverse]),
                (upper[0], upper[transverse]),
                (lower[0], upper[transverse]),
            ):
                vertex = list(point)
                vertex[0], vertex[transverse] = x, cross
                vertices.append((vertex[0], vertex[1], vertex[2]))
            faces.append(
                DirectEngineeringFace(
                    bolt.bolt_location_id,
                    hole.participant_id,
                    hole.physical_element_id,
                    primitive.id,
                    zone.patch_id,
                    _coordinates(bolt.center),
                    center,
                    raw_center,
                    point,
                    raw_point,
                    canonicalization,
                    normal,
                    transverse,
                    tuple(vertices),
                    tuple(boundaries),
                    tuple(checks),
                    hole_radius,
                    washer_radius,
                )
            )
    return tuple(faces)


def direct_engineering_issues(
    faces: Sequence[DirectEngineeringFace],
) -> tuple[DirectContainmentIssue, ...]:
    """Friendly failures from evaluated physics; raw IDs stay in the audit records."""
    return tuple(
        DirectContainmentIssue(
            face.bolt_id,
            face.component_id,
            face.physical_element_id,
            f"{check.check_kind} — {check.boundary_label}: "
            f"available={check.actual_distance}; required={check.required_distance}.",
        )
        for face in faces
        for check in face.checks
        if check.actual_distance < check.required_distance
    )
