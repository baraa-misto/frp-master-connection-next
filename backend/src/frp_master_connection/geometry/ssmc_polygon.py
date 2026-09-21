"""SSMC R1 sharp-corner Boolean boundary in the native floating geometry domain.

The three pieces occupy disjoint miter-normal slabs. Their shared cut edges
are internal, leaving the ordered exterior chain below. No convex hull, fitted
rectangle, resistance equation or renderer triangulation determines this region.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

type Point2 = tuple[float, float]
type Polygon2 = tuple[Point2, ...]

GEOMETRY_EPSILON = 1e-9


def add(a: Point2, b: Point2) -> Point2:
    return a[0] + b[0], a[1] + b[1]


def subtract(a: Point2, b: Point2) -> Point2:
    return a[0] - b[0], a[1] - b[1]


def scale(a: Point2, factor: float) -> Point2:
    return a[0] * factor, a[1] * factor


def dot(a: Point2, b: Point2) -> float:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: Point2, b: Point2) -> float:
    return a[0] * b[1] - a[1] * b[0]


def unit(a: Point2) -> Point2:
    norm = math.hypot(*a)
    if not math.isfinite(norm) or norm <= GEOMETRY_EPSILON:
        raise ValueError("SSMC_MEMBER_REFERENCE_GEOMETRY_INVALID")
    return scale(a, 1 / norm)


def pairs(poly: Polygon2) -> tuple[tuple[Point2, Point2], ...]:
    return tuple(zip(poly, (*poly[1:], poly[0]), strict=True))


def signed_area(poly: Polygon2) -> float:
    return sum(cross(a, b) for a, b in pairs(poly)) / 2


def distance_squared(point: Point2, a: Point2, b: Point2) -> float:
    edge = subtract(b, a)
    denominator = dot(edge, edge)
    if denominator == 0:
        return dot(subtract(point, a), subtract(point, a))
    parameter = max(0.0, min(1.0, dot(subtract(point, a), edge) / denominator))
    delta = subtract(point, add(a, scale(edge, parameter)))
    return dot(delta, delta)


def _intersects(a: Point2, b: Point2, c: Point2, d: Point2) -> bool:
    directions = (
        cross(subtract(b, a), subtract(c, a)),
        cross(subtract(b, a), subtract(d, a)),
        cross(subtract(d, c), subtract(a, c)),
        cross(subtract(d, c), subtract(b, c)),
    )
    if directions[0] * directions[1] < 0 and directions[2] * directions[3] < 0:
        return True
    return any(
        distance_squared(point, left, right) <= GEOMETRY_EPSILON**2
        for point, left, right in ((a, c, d), (b, c, d), (c, a, b), (d, a, b))
    )


def validate_polygon(poly: Polygon2) -> None:
    if len(poly) < 3 or any(not math.isfinite(v) for p in poly for v in p):
        raise ValueError("SSMC_POLYGON_INVALID")
    edges = pairs(poly)
    if abs(signed_area(poly)) <= GEOMETRY_EPSILON**2:
        raise ValueError("SSMC_POLYGON_INVALID")
    for i, (a, b) in enumerate(edges):
        if math.dist(a, b) <= GEOMETRY_EPSILON:
            raise ValueError("SSMC_POLYGON_INVALID")
        for j in range(i + 1, len(edges)):
            if j in {i + 1, len(edges) - 1 if i == 0 else i}:
                continue
            if _intersects(a, b, *edges[j]):
                raise ValueError("SSMC_POLYGON_INVALID")


def contains_disk(poly: Polygon2, center: Point2, radius: float) -> bool:
    """Actual outer boundary distance; holes are checked separately by the assembly."""
    if not math.isfinite(radius) or radius <= 0:
        return False
    inside = False
    x, z = center
    for a, b in pairs(poly):
        if (a[1] > z) != (b[1] > z):
            hit = a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if hit > x:
                inside = not inside
    return inside and all(
        distance_squared(center, a, b) >= radius**2 - GEOMETRY_EPSILON**2 for a, b in pairs(poly)
    )


@dataclass(frozen=True, slots=True)
class MiterBranch:
    owner: str
    axis: Point2
    transverse: Point2
    depth: float
    overlap: float
    cut_delta: float
    cut_points: tuple[Point2, Point2]
    far_points: tuple[Point2, Point2]


@dataclass(frozen=True, slots=True)
class MiterPolygon:
    work_point: Point2
    normal: Point2
    gap: float
    branches: tuple[MiterBranch, MiterBranch]
    transition: Polygon2
    boundary: Polygon2
    edge_ids: tuple[str, ...]
    edge_owners: tuple[str, ...]
    gross_neck_width: float
    area: float


def construct_miter_polygon(
    theta_degrees: float,
    gap: float,
    depths: tuple[float, float],
    overlaps: tuple[float, float],
) -> MiterPolygon:
    """Owner R1 sections 1-12; O is the unique datum-line intersection."""
    if not math.isfinite(theta_degrees) or not 30 <= abs(theta_degrees) <= 45:
        raise ValueError("SSMC_INCLINATION_OUTSIDE_RC1_DOMAIN")
    if not math.isfinite(gap) or gap < 0:
        raise ValueError("SSMC_MEMBER_REFERENCE_GEOMETRY_INVALID")
    if any(not math.isfinite(v) or v <= 0 for v in (*depths, *overlaps)):
        raise ValueError("SSMC_POLYGON_INVALID")
    theta = math.radians(theta_degrees)
    axes: tuple[Point2, Point2] = ((-1.0, 0.0), (math.cos(theta), math.sin(theta)))
    normal = unit(subtract(axes[1], axes[0]))
    first_b: Point2 = (0.0, 1.0)
    raw_b: Point2 = (axes[1][1], -axes[1][0])
    second_b = raw_b if dot(first_b, raw_b) >= 0 else scale(raw_b, -1)
    branches: list[MiterBranch] = []
    for owner, axis, b, depth, overlap, delta in zip(
        ("HORIZONTAL_STRINGER", "INCLINED_STRINGER"),
        axes,
        (first_b, second_b),
        depths,
        overlaps,
        (-gap / 2, gap / 2),
        strict=True,
    ):
        points = tuple(
            add(
                scale(b, sign * depth / 2),
                scale(axis, (delta - sign * depth / 2 * dot(normal, b)) / dot(normal, axis)),
            )
            for sign in (-1, 1)
        )
        q = (points[0], points[1])
        far = (add(q[0], scale(axis, overlap)), add(q[1], scale(axis, overlap)))
        branches.append(MiterBranch(owner, axis, b, depth, overlap, delta, q, far))
    h, i = branches
    tangent = (normal[1], -normal[0])
    intervals = tuple(sorted(dot(p, tangent) for p in b.cut_points) for b in branches)
    transition: Polygon2
    if gap > 0:
        transition = (h.cut_points[0], h.cut_points[1], i.cut_points[1], i.cut_points[0])
        validate_polygon(transition)
        neck = min(high - low for low, high in intervals)
    else:
        transition = ()
        neck = min(v[1] for v in intervals) - max(v[0] for v in intervals)
    if neck <= GEOMETRY_EPSILON:
        raise ValueError("SSMC_TRANSITION_GEOMETRY_INVALID")
    chain = (
        (h.cut_points[0], "H_MINUS"),
        (h.far_points[0], "H_FAR"),
        (h.far_points[1], "H_PLUS"),
        (h.cut_points[1], "TRANSITION_PLUS"),
        (i.cut_points[1], "I_PLUS"),
        (i.far_points[1], "I_FAR"),
        (i.far_points[0], "I_MINUS"),
        (i.cut_points[0], "TRANSITION_MINUS"),
    )
    # At zero gap equal endpoints are the SAME native point, not an auto-fit.
    retained = tuple(
        (point, name)
        for index, (point, name) in enumerate(chain)
        if math.dist(point, chain[(index + 1) % len(chain)][0]) > GEOMETRY_EPSILON
    )
    boundary = tuple(p for p, _ in retained)
    validate_polygon(boundary)
    edge_ids = tuple("MITER_WEB_PLATE:" + name for _, name in retained)
    owners = tuple(
        "HORIZONTAL_BRANCH"
        if name.startswith("H_")
        else "INCLINED_BRANCH"
        if name.startswith("I_")
        else "TRANSITION"
        for _, name in retained
    )
    return MiterPolygon(
        (0.0, 0.0),
        normal,
        gap,
        (h, i),
        transition,
        boundary,
        edge_ids,
        owners,
        neck,
        abs(signed_area(boundary)),
    )
