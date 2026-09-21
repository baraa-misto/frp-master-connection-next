"""Actual polygon/hole geometry candidates, explicitly not resistance paths.

Circular holes retain their analytic authority. The edge and hole separations
below enumerate geometry candidates; qualification of a net/block/shear failure
path and its N/V/M resistance remains a separate, unresolved obligation.
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from frp_master_connection.geometry.ssmc_polygon import (
    GEOMETRY_EPSILON,
    MiterPolygon,
    Point2,
    add,
    cross,
    distance_squared,
    dot,
    pairs,
    scale,
    signed_area,
    subtract,
)


@dataclass(frozen=True, slots=True)
class CircularHoleLoop:
    shaft_id: str
    group_id: str
    center: Point2
    radius: float
    winding: str = "OPPOSITE_OUTER_BOUNDARY"
    authority: str = "ANALYTIC_CIRCLE"


@dataclass(frozen=True, slots=True)
class LigamentCandidate:
    id: str
    kind: str
    from_owner: str
    to_owner: str
    start: Point2
    end: Point2
    clear_length: float
    connected_material: bool
    qualified_resistance: None = None


@dataclass(frozen=True, slots=True)
class PolygonPathLedger:
    holes: tuple[CircularHoleLoop, ...]
    candidates: tuple[LigamentCandidate, ...]
    reentrant_corners: tuple[tuple[str, Point2], ...]
    first_rows: tuple[tuple[str, tuple[str, ...]], ...]
    gross_neck_width: float
    net_area: float
    status: str = "SSMC_POLYGON_RESISTANCE_NOT_QUALIFIED"


def _inside_or_boundary(point: Point2, polygon: MiterPolygon) -> bool:
    inside = False
    for a, b in pairs(polygon.boundary):
        if distance_squared(point, a, b) <= GEOMETRY_EPSILON**2:
            return True
        if (a[1] > point[1]) != (b[1] > point[1]):
            hit = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if hit > point[0]:
                inside = not inside
    return inside


def connected_ligament(
    polygon: MiterPolygon, holes: tuple[CircularHoleLoop, ...], start: Point2, end: Point2
) -> bool:
    """Split at every boundary crossing, then test each open subsegment.

    This is an analytic segment/edge and segment/circle test, not a sampling
    grid or a resistance-path qualification. A diagonal across a concave void
    or another bolt hole is retained in the trace but is NOT connected material.
    """
    delta = subtract(end, start)
    cuts = {0.0, 1.0}
    for a, b in pairs(polygon.boundary):
        edge = subtract(b, a)
        denominator = cross(delta, edge)
        if abs(denominator) > GEOMETRY_EPSILON**2:
            offset = subtract(a, start)
            t, u = cross(offset, edge) / denominator, cross(offset, delta) / denominator
            if 0 < t < 1 and 0 <= u <= 1:
                cuts.add(t)
    ordered = sorted(cuts)
    return all(
        _inside_or_boundary(add(start, scale(delta, (a + b) / 2)), polygon)
        for a, b in pairwise(ordered)
    ) and all(
        distance_squared(h.center, start, end) >= (h.radius - GEOMETRY_EPSILON) ** 2 for h in holes
    )


def discover_polygon_paths(
    polygon: MiterPolygon,
    holes: tuple[CircularHoleLoop, ...],
    first_rows: tuple[tuple[str, tuple[str, ...]], ...],
) -> PolygonPathLedger:
    """Enumerate every actual edge/hole pair without an enclosing rectangle."""
    candidates: list[LigamentCandidate] = []
    for i, hole in enumerate(holes):
        for edge_id, (a, b) in zip(polygon.edge_ids, pairs(polygon.boundary), strict=True):
            edge = subtract(b, a)
            t = max(0.0, min(1.0, dot(subtract(hole.center, a), edge) / dot(edge, edge)))
            foot = add(a, scale(edge, t))
            distance = math.dist(foot, hole.center)
            start = add(hole.center, scale(subtract(foot, hole.center), hole.radius / distance))
            candidates.append(
                LigamentCandidate(
                    f"{hole.shaft_id}->{edge_id}",
                    "HOLE_TO_EDGE",
                    hole.shaft_id,
                    edge_id,
                    start,
                    foot,
                    distance - hole.radius,
                    connected_ligament(polygon, holes, start, foot),
                )
            )
        for other in holes[i + 1 :]:
            delta = subtract(other.center, hole.center)
            distance = math.hypot(*delta)
            direction = scale(delta, 1 / distance)
            candidates.append(
                LigamentCandidate(
                    f"{hole.shaft_id}->{other.shaft_id}",
                    "HOLE_TO_HOLE",
                    hole.shaft_id,
                    other.shaft_id,
                    add(hole.center, scale(direction, hole.radius)),
                    add(other.center, scale(direction, -other.radius)),
                    distance - hole.radius - other.radius,
                    connected_ligament(
                        polygon,
                        holes,
                        add(hole.center, scale(direction, hole.radius)),
                        add(other.center, scale(direction, -other.radius)),
                    ),
                )
            )
    orientation = signed_area(polygon.boundary)
    corners = tuple(
        (polygon.edge_ids[i], point)
        for i, point in enumerate(polygon.boundary)
        if cross(
            subtract(point, polygon.boundary[i - 1]),
            subtract(polygon.boundary[(i + 1) % len(polygon.boundary)], point),
        )
        * orientation
        < 0
    )
    return PolygonPathLedger(
        holes,
        tuple(candidates),
        corners,
        first_rows,
        polygon.gross_neck_width,
        polygon.area - sum(math.pi * h.radius**2 for h in holes),
    )
