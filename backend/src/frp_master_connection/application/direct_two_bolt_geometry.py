"""SAB2 shared geometry kernel. No engineering demand, resistance or qualification.

All lengths are canonical inches. Signed geometric margins are never clamped by
an engineering tolerance. Proper frame validation uses the existing dimensionless
representation contract. Physical ends, internal junctions and view crops remain
distinct. Unknown manufactured geometry does not become a favorable dimension.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import product
from typing import Literal

from frp_master_connection.geometry.spatial import DIMENSIONLESS_MATHEMATICAL_TOLERANCE

type V3 = tuple[Decimal, Decimal, Decimal]
type P2 = tuple[Decimal, Decimal]
type Axes = tuple[V3, V3, V3]
type FitState = Literal["FIT_FOR_STATED_GEOMETRY", "CONDITIONAL", "DOES_NOT_FIT", "NOT_EVALUATED"]

ZERO = Decimal(0)
ONE = Decimal(1)
FRAME_PRECISION = Decimal(str(DIMENSIONLESS_MATHEMATICAL_TOLERANCE))
GEOMETRY_BANNER = "GEOMETRY / CONSTRUCTABILITY ONLY — NOT A STRUCTURAL DESIGN APPROVAL"


def add(a: V3, b: V3) -> V3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def subtract(a: V3, b: V3) -> V3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def scale(a: V3, value: Decimal) -> V3:
    return a[0] * value, a[1] * value, a[2] * value


def dot(a: V3, b: V3) -> Decimal:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: V3, b: V3) -> V3:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def length(a: V3) -> Decimal:
    return dot(a, a).sqrt()


def validate_frame(axes: Axes) -> None:
    if any(not value.is_finite() for axis in axes for value in axis):
        raise ValueError("Frame coordinates must be finite.")
    if any(abs(length(a) - ONE) > FRAME_PRECISION for a in axes):
        raise ValueError("Frame axes must have unit length.")
    if any(abs(dot(axes[i], axes[j])) > FRAME_PRECISION for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Frame axes must be orthogonal.")
    if abs(dot(cross(axes[0], axes[1]), axes[2]) - ONE) > FRAME_PRECISION:
        raise ValueError("Frame must be proper and right handed; reflections are forbidden.")


def local_point(point: V3, origin: V3, axes: Axes) -> V3:
    difference = subtract(point, origin)
    return dot(difference, axes[0]), dot(difference, axes[1]), dot(difference, axes[2])


def global_point(point: V3, origin: V3, axes: Axes) -> V3:
    return add(
        origin,
        add(add(scale(axes[0], point[0]), scale(axes[1], point[1])), scale(axes[2], point[2])),
    )


def fit_state(margins: tuple[Decimal, ...], unknowns: tuple[str, ...] = ()) -> FitState:
    if not margins:
        return "NOT_EVALUATED"
    if min(margins) < ZERO:
        return "DOES_NOT_FIT"
    if min(margins) == ZERO or unknowns:
        return "CONDITIONAL"
    return "FIT_FOR_STATED_GEOMETRY"


@dataclass(frozen=True, slots=True)
class Boundary:
    """Unit half-plane a*u+b*v <= limit; a true edge or stated exclusion."""

    id: str
    a: Decimal
    b: Decimal
    limit: Decimal
    role: str
    source: str
    planning_minimum: Decimal = ZERO

    def margin(self, point: P2, radius: Decimal) -> Decimal:
        return self.limit - self.a * point[0] - self.b * point[1] - radius


def polygon_boundaries(polygon: tuple[P2, ...], source: str) -> tuple[Boundary, ...]:
    if len(polygon) < 3:
        raise ValueError("A finite convex counterclockwise physical polygon is required.")
    result: list[Boundary] = []
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        du, dv = end[0] - start[0], end[1] - start[1]
        size = (du * du + dv * dv).sqrt()
        if size == ZERO:
            raise ValueError("Physical polygon contains a zero-length edge.")
        if any(du * (p[1] - start[1]) - dv * (p[0] - start[0]) < ZERO for p in polygon):
            raise ValueError("Physical polygon must be convex and counterclockwise.")
        a, b = dv / size, -du / size
        result.append(
            Boundary(
                f"{source}:EDGE:{index}",
                a,
                b,
                a * start[0] + b * start[1],
                "PHYSICAL_END_OR_SIDE",
                source,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class Face:
    id: str
    member_id: str
    origin: V3
    axes: Axes
    boundaries: tuple[Boundary, ...]
    seating_strips: tuple[tuple[Decimal, Decimal], ...]
    unknowns: tuple[str, ...]
    source: str


@dataclass(frozen=True, slots=True)
class Obstacle:
    id: str
    origin: V3
    axes: Axes
    lower: V3
    upper: V3
    source: str


@dataclass(frozen=True, slots=True)
class Cylinder:
    name: str
    radius: Decimal
    start: Decimal
    end: Decimal
    source: str


@dataclass(frozen=True, slots=True)
class PairInput:
    midpoint: V3
    direction: V3
    normal: V3
    spacing: Decimal
    shaft_radius: Decimal
    hole_radius: Decimal
    washer_radius: Decimal
    shaft_span: tuple[Decimal, Decimal]
    washer_spans: tuple[tuple[Decimal, Decimal], ...]
    faces: tuple[Face, ...]
    obstacles: tuple[Obstacle, ...] = ()
    hardware: tuple[Cylinder, ...] = ()


@dataclass(frozen=True, slots=True)
class Margin:
    station: str
    owner: str
    role: str
    boundary: str
    value: Decimal
    source: str


@dataclass(frozen=True, slots=True)
class FacePoint:
    station: str
    member_id: str
    face_id: str
    global_center: V3
    local_center: V3
    face_point_global: V3


@dataclass(frozen=True, slots=True)
class PairResult:
    centers: tuple[V3, V3]
    face_points: tuple[FacePoint, ...]
    margins: tuple[Margin, ...]
    hole_state: FitState
    shaft_state: FitState
    washer_state: FitState
    obstruction_state: FitState
    hardware_state: FitState
    installation_state: FitState
    aggregate_state: FitState
    unknowns: tuple[str, ...]
    pair_polar_sum: Decimal


def circle_box_margin(
    point: P2, radius: Decimal, bounds: tuple[Decimal, Decimal, Decimal, Decimal]
) -> Decimal:
    u, v = point
    u0, u1, v0, v1 = bounds
    if not u0 < u1 or not v0 < v1:
        raise ValueError("Obstruction dimensions must be positive.")
    du, dv = max(u0 - u, ZERO, u - u1), max(v0 - v, ZERO, v - v1)
    if du == ZERO and dv == ZERO:
        return -min(u - u0, u1 - u, v - v0, v1 - v) - radius
    return (du * du + dv * dv).sqrt() - radius


def accessible_strips(
    low: Decimal,
    high: Decimal,
    web_low: Decimal,
    web_high: Decimal,
    root: Decimal,
    family: Literal["I", "CHANNEL"],
) -> tuple[tuple[Decimal, Decimal], ...]:
    """Actual rear seating domains; a Channel has one web and one open outstand."""
    if root < ZERO or not low <= web_low < web_high < high:
        raise ValueError("Physical flange/web/root dimensions are inconsistent.")
    strips = (
        ((low, web_low - root), (web_high + root, high))
        if family == "I"
        else ((web_high + root, high),)
    )
    if any(a >= b for a, b in strips):
        raise ValueError("Root geometry consumes an accessible outstand.")
    return strips


def cylinder_obstruction(
    point: V3, normal: V3, cylinder: Cylinder, obstacle: Obstacle
) -> Decimal | None:
    local = local_point(point, obstacle.origin, obstacle.axes)
    axis = dot(normal, obstacle.axes[2])
    if abs(abs(axis) - ONE) > FRAME_PRECISION:
        raise ValueError(
            "Oblique cylinder/obstacle mapping needs an independently supported geometry contract."
        )
    ends = sorted((local[2] + cylinder.start * axis, local[2] + cylinder.end * axis))
    overlap = min(ends[1], obstacle.upper[2]) - max(ends[0], obstacle.lower[2])
    if overlap < ZERO:
        return None
    planar = circle_box_margin(
        (local[0], local[1]),
        cylinder.radius,
        (obstacle.lower[0], obstacle.upper[0], obstacle.lower[1], obstacle.upper[1]),
    )
    if overlap == ZERO:
        return ZERO if planar <= ZERO else None
    return planar


def evaluate_pair(request: PairInput) -> PairResult:
    """Resolve one shared pair on every face, retaining every signed witness."""
    with localcontext() as context:
        context.prec = 64
        return _evaluate_pair(request)


def _evaluate_pair(request: PairInput) -> PairResult:
    p = request.spacing
    numbers = (
        *request.midpoint,
        *request.direction,
        *request.normal,
        p,
        request.shaft_radius,
        request.hole_radius,
        request.washer_radius,
    )
    if (
        any(not value.is_finite() for value in numbers)
        or min(p, request.shaft_radius, request.hole_radius, request.washer_radius) <= ZERO
    ):
        raise ValueError("Pair geometry requires finite coordinates and positive dimensions.")
    if request.hole_radius < request.shaft_radius or request.washer_radius <= request.shaft_radius:
        raise ValueError("Hole and washer dimensions conflict with the shaft.")
    if (
        abs(length(request.direction) - ONE) > FRAME_PRECISION
        or abs(length(request.normal) - ONE) > FRAME_PRECISION
    ):
        raise ValueError("Pair direction and shaft normal must be unit vectors.")
    if abs(dot(request.direction, request.normal)) > FRAME_PRECISION:
        raise ValueError("Pair direction must lie in the interface plane; it is never projected.")
    if len(request.faces) != 2 or len({f.member_id for f in request.faces}) != 2:
        raise ValueError("The same two centers must be evaluated on both connected members.")
    for face in request.faces:
        validate_frame(face.axes)
        if abs(abs(dot(face.axes[2], request.normal)) - ONE) > FRAME_PRECISION:
            raise ValueError("Selected faces and physical shaft normal disagree.")
        if not face.boundaries:
            raise ValueError("Selected physical face boundaries are unresolved.")
        if any(lo >= hi for lo, hi in face.seating_strips):
            raise ValueError("Each accessible seating strip must have positive width.")
    for obstacle in request.obstacles:
        validate_frame(obstacle.axes)
        if any(a >= b for a, b in zip(obstacle.lower, obstacle.upper, strict=True)):
            raise ValueError("Represented obstruction must have positive physical dimensions.")
    cylinders = (
        Cylinder(
            "SHAFT", request.shaft_radius, *request.shaft_span, "Submitted shaft and physical stack"
        ),
        *(
            Cylinder(
                "WASHER",
                request.washer_radius,
                *span,
                "Submitted actual washer OD/thickness and seat",
            )
            for span in request.washer_spans
        ),
        *request.hardware,
    )
    if any(
        not all(v.is_finite() for v in (c.radius, c.start, c.end))
        or c.radius <= ZERO
        or c.start >= c.end
        or not c.source.strip()
        for c in cylinders
    ):
        raise ValueError(
            "A represented cylinder requires positive sourced dimensions and axial span."
        )
    offset = scale(request.direction, p / 2)
    centers = subtract(request.midpoint, offset), add(request.midpoint, offset)
    margins: list[Margin] = []
    points: list[FacePoint] = []
    for station, point in zip(("B1", "B2"), centers, strict=True):
        for face in request.faces:
            local = local_point(point, face.origin, face.axes)
            projected = global_point((local[0], local[1], ZERO), face.origin, face.axes)
            points.append(FacePoint(station, face.member_id, face.id, point, local, projected))
            for boundary in face.boundaries:
                for role, radius in (
                    ("HOLE", request.hole_radius),
                    ("WASHER", request.washer_radius),
                ):
                    margins.append(
                        Margin(
                            station,
                            face.member_id,
                            role,
                            boundary.id,
                            boundary.margin((local[0], local[1]), radius),
                            f"{boundary.role}: {boundary.source}",
                        )
                    )
            if face.seating_strips:
                for role, radius in (
                    ("SHAFT", request.shaft_radius),
                    ("WASHER", request.washer_radius),
                ):
                    best = max(
                        min(local[1] - lo - radius, hi - local[1] - radius)
                        for lo, hi in face.seating_strips
                    )
                    margins.append(
                        Margin(
                            station,
                            face.member_id,
                            role,
                            "ACCESSIBLE_OUTSTAND_STRIPS",
                            best,
                            face.source,
                        )
                    )
        for obstacle in request.obstacles:
            for cylinder in cylinders:
                margin = cylinder_obstruction(point, request.normal, cylinder, obstacle)
                if margin is not None:
                    margins.append(
                        Margin(
                            station,
                            obstacle.id,
                            f"{cylinder.name}_OBSTRUCTION",
                            "PHYSICAL_OBSTRUCTION",
                            margin,
                            obstacle.source,
                        )
                    )
    distance = length(subtract(centers[1], centers[0]))
    for role, radius in (("HOLE", request.hole_radius), ("WASHER", request.washer_radius)):
        margins.append(
            Margin(
                "B1 / B2",
                "PAIR",
                role,
                "SAME_FACE_OVERLAP",
                distance - 2 * radius,
                "Same two stations and actual circular envelope",
            )
        )
    for cylinder in request.hardware:
        margins.append(
            Margin(
                "B1 / B2",
                "PAIR",
                cylinder.name,
                "SAME_AXIAL_SPAN_OVERLAP",
                distance - 2 * cylinder.radius,
                cylinder.source,
            )
        )
    unknowns = tuple(dict.fromkeys(u for face in request.faces for u in face.unknowns))

    def values(role: str) -> tuple[Decimal, ...]:
        return tuple(m.value for m in margins if m.role == role)

    hole, shaft, washer = (
        fit_state(values("HOLE")),
        fit_state(values("SHAFT")),
        fit_state(values("WASHER"), unknowns),
    )
    obstruction = fit_state(tuple(m.value for m in margins if m.boundary == "PHYSICAL_OBSTRUCTION"))
    represented_hardware = {cylinder.name for cylinder in request.hardware}
    missing_hardware = tuple(
        f"Actual {role.lower()} body not represented"
        for role in ("HEAD", "NUT")
        if role not in represented_hardware
    )
    hardware = fit_state(
        tuple(
            m.value
            for m in margins
            if m.role in {"HEAD", "NUT", "HEAD_OBSTRUCTION", "NUT_OBSTRUCTION"}
        ),
        missing_hardware,
    )
    installation = fit_state(
        tuple(m.value for m in margins if m.role in {"TOOL", "TOOL_OBSTRUCTION"})
    )
    all_values = tuple(m.value for m in margins)
    missing_installation = (
        ("Installation access not evaluated",) if installation == "NOT_EVALUATED" else ()
    )
    aggregate = fit_state(all_values, (*unknowns, *missing_hardware, *missing_installation))
    polar = sum(
        (
            dot(subtract(point, request.midpoint), subtract(point, request.midpoint))
            for point in centers
        ),
        ZERO,
    )
    return PairResult(
        centers,
        tuple(points),
        tuple(margins),
        hole,
        shaft,
        washer,
        obstruction,
        hardware,
        installation,
        aggregate,
        (*unknowns, *missing_hardware, *missing_installation),
        polar,
    )


def clip_polygon(
    polygon: tuple[P2, ...], constraint: tuple[Decimal, Decimal, Decimal]
) -> tuple[P2, ...]:
    if not polygon:
        return ()
    a, b, c = constraint
    result: list[P2] = []
    previous = polygon[-1]
    previous_value = a * previous[0] + b * previous[1] - c
    for point in polygon:
        value = a * point[0] + b * point[1] - c
        if (value <= ZERO) != (previous_value <= ZERO):
            ratio = previous_value / (previous_value - value)
            result.append(
                (
                    previous[0] + ratio * (point[0] - previous[0]),
                    previous[1] + ratio * (point[1] - previous[1]),
                )
            )
        if value <= ZERO:
            result.append(point)
        previous, previous_value = point, value
    return tuple(result)


@dataclass(frozen=True, slots=True)
class MidpointRegion:
    assigned_strips: tuple[int, ...]
    polygon: tuple[P2, ...]
    proposed_offset: P2


def bounded_regions(
    request: PairInput, plane_axes: tuple[V3, V3], bounds: tuple[Decimal, Decimal, Decimal, Decimal]
) -> tuple[MidpointRegion, ...]:
    with localcontext() as context:
        context.prec = 64
        return _bounded_regions(request, plane_axes, bounds)


def _bounded_regions(
    request: PairInput, plane_axes: tuple[V3, V3], bounds: tuple[Decimal, Decimal, Decimal, Decimal]
) -> tuple[MidpointRegion, ...]:
    """Explicit bounded feasible seating regions; vertices' centroid is a proposal.

    This is not a global maximum-clearance optimizer, installation proof, or a
    modification of the submitted layout. Each disconnected strip assignment is
    retained, including brace patterns spanning opposite support outstands.
    """
    u0, u1, v0, v1 = bounds
    if not u0 < u1 or not v0 < v1:
        raise ValueError("Midpoint search requires explicit positive rectangular bounds.")
    offsets = (
        scale(request.direction, -request.spacing / 2),
        scale(request.direction, request.spacing / 2),
    )
    strips = [(face, index) for face in request.faces for index in (0, 1) if face.seating_strips]
    assignments = product(*(range(len(face.seating_strips)) for face, _ in strips))
    regions: list[MidpointRegion] = []
    for assignment in assignments:
        constraints: list[tuple[Decimal, Decimal, Decimal]] = []
        for face in request.faces:
            for offset in offsets:
                point = local_point(add(request.midpoint, offset), face.origin, face.axes)
                for boundary in face.boundaries:
                    normal = add(scale(face.axes[0], boundary.a), scale(face.axes[1], boundary.b))
                    constraints.append(
                        (
                            dot(normal, plane_axes[0]),
                            dot(normal, plane_axes[1]),
                            boundary.margin(
                                (point[0], point[1]),
                                max(request.washer_radius, boundary.planning_minimum),
                            ),
                        )
                    )
        for (face, index), strip in zip(strips, assignment, strict=True):
            point = local_point(add(request.midpoint, offsets[index]), face.origin, face.axes)
            lo, hi = face.seating_strips[strip]
            a, b = dot(face.axes[1], plane_axes[0]), dot(face.axes[1], plane_axes[1])
            constraints.extend(
                (
                    (-a, -b, point[1] - lo - request.washer_radius),
                    (a, b, hi - point[1] - request.washer_radius),
                )
            )
        polygon: tuple[P2, ...] = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        for constraint in constraints:
            polygon = clip_polygon(polygon, constraint)
        if polygon:
            proposed = (
                sum((point[0] for point in polygon), ZERO) / len(polygon),
                sum((point[1] for point in polygon), ZERO) / len(polygon),
            )
            regions.append(MidpointRegion(assignment, polygon, proposed))
    return tuple(regions)


def shifted_moment(moment: V3, reference: V3, midpoint: V3, force: V3) -> V3:
    """Reference identity M_G=M_P+(r_P-r_G)xF, never per-bolt demand."""
    return add(moment, cross(subtract(reference, midpoint), force))
