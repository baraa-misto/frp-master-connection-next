"""Framework-independent physical geometry for general multi-row bolt groups."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import StrEnum
from itertools import combinations

from frp_master_connection.domain.validation import require_tuple, validate_identifier


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a non-Boolean real number.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    return float(value)


def _positive(value: object, name: str) -> float:
    result = _finite(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive.")
    return result


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a non-Boolean integer.")
    if value < 1:
        raise ValueError(f"{name} must be positive.")
    return value


@dataclass(frozen=True, slots=True)
class PlanarPoint2D:
    """One exact-known point in an authoritative physical layer plane."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, "PlanarPoint2D.x"))
        object.__setattr__(self, "y", _finite(self.y, "PlanarPoint2D.y"))


class BoundaryObstacleKind(StrEnum):
    """Physical/deferred regions that a rupture path must not cross."""

    VOID = "VOID"
    DEFERRED_HEEL = "DEFERRED_HEEL"
    DEFERRED_JUNCTION = "DEFERRED_JUNCTION"
    DEFERRED_CORNER = "DEFERRED_CORNER"


@dataclass(frozen=True, slots=True)
class RectangularObstacle2D:
    """Conservative bounded obstacle in the authoritative layer plane."""

    id: str
    kind: BoundaryObstacleKind
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def __post_init__(self) -> None:
        validate_identifier(self.id, "RectangularObstacle2D.id")
        if not isinstance(self.kind, BoundaryObstacleKind):
            raise TypeError("RectangularObstacle2D.kind must be BoundaryObstacleKind.")
        for name in ("min_x", "max_x", "min_y", "max_y"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.min_x >= self.max_x or self.min_y >= self.max_y:
            raise ValueError("An obstacle must have positive planar extents.")


@dataclass(frozen=True, slots=True)
class PlanarLayerBoundary:
    """Real rectangular free boundaries and excluded regions for one flat layer."""

    id: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    unloaded_end_is_free: bool = True
    negative_side_is_free: bool = True
    positive_side_is_free: bool = True
    obstacles: tuple[RectangularObstacle2D, ...] = ()

    def __post_init__(self) -> None:
        validate_identifier(self.id, "PlanarLayerBoundary.id")
        for name in ("min_x", "max_x", "min_y", "max_y"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.min_x >= self.max_x or self.min_y >= self.max_y:
            raise ValueError("A layer boundary must have positive planar extents.")
        for name in (
            "unloaded_end_is_free",
            "negative_side_is_free",
            "positive_side_is_free",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be Boolean.")
        require_tuple(self.obstacles, "PlanarLayerBoundary.obstacles")
        if any(not isinstance(item, RectangularObstacle2D) for item in self.obstacles):
            raise TypeError("PlanarLayerBoundary.obstacles contains an invalid item.")
        ids = tuple(item.id for item in self.obstacles)
        if len(set(ids)) != len(ids):
            raise ValueError("Obstacle IDs must be unique.")


@dataclass(frozen=True, slots=True)
class GeneralBolt:
    """One physical bolt center and common-method identity metadata."""

    id: str
    center: PlanarPoint2D
    bolt_diameter: float
    hole_diameter: float
    bolt_identity: str
    logical_connection_id: str

    def __post_init__(self) -> None:
        validate_identifier(self.id, "GeneralBolt.id")
        if not isinstance(self.center, PlanarPoint2D):
            raise TypeError("GeneralBolt.center must be PlanarPoint2D.")
        object.__setattr__(self, "bolt_diameter", _positive(self.bolt_diameter, "bolt_diameter"))
        object.__setattr__(self, "hole_diameter", _positive(self.hole_diameter, "hole_diameter"))
        if self.hole_diameter < self.bolt_diameter:
            raise ValueError("A physical hole cannot be smaller than its bolt.")
        validate_identifier(self.bolt_identity, "GeneralBolt.bolt_identity")
        validate_identifier(self.logical_connection_id, "GeneralBolt.logical_connection_id")


@dataclass(frozen=True, slots=True)
class GeneralBoltGroup:
    """General physical bolt group with no permanent maximum row or bolt count."""

    id: str
    interface_id: str
    declared_row_count: int
    declared_bolt_count: int
    bolts: tuple[GeneralBolt, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.id, "GeneralBoltGroup.id")
        validate_identifier(self.interface_id, "GeneralBoltGroup.interface_id")
        _positive_integer(self.declared_row_count, "declared_row_count")
        _positive_integer(self.declared_bolt_count, "declared_bolt_count")
        require_tuple(self.bolts, "GeneralBoltGroup.bolts")
        if any(not isinstance(item, GeneralBolt) for item in self.bolts):
            raise TypeError("GeneralBoltGroup.bolts contains an invalid item.")
        if len(self.bolts) != self.declared_bolt_count:
            raise ValueError("Declared bolt count must equal the physical bolt tuple length.")
        ids = tuple(item.id for item in self.bolts)
        if len(set(ids)) != len(ids):
            raise ValueError("Physical bolt IDs must be unique.")
        locations = tuple((item.center.x, item.center.y) for item in self.bolts)
        if len(set(locations)) != len(locations):
            raise ValueError("Physical bolt locations must be unique.")


@dataclass(frozen=True, slots=True)
class MultiRowGeometryTolerance:
    """Named dimensional sorting/classification tolerance."""

    distance: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "distance", _positive(self.distance, "distance"))


@dataclass(frozen=True, slots=True)
class ProjectedBolt:
    """A physical bolt retained with raw force-axis projections."""

    bolt: GeneralBolt
    u: float
    v: float

    def __post_init__(self) -> None:
        if not isinstance(self.bolt, GeneralBolt):
            raise TypeError("ProjectedBolt.bolt must be GeneralBolt.")
        object.__setattr__(self, "u", _finite(self.u, "ProjectedBolt.u"))
        object.__setattr__(self, "v", _finite(self.v, "ProjectedBolt.v"))


@dataclass(frozen=True, slots=True)
class BoltRow:
    """Deterministic physical row identity along the signed force direction."""

    id: str
    ordinal: int
    projected_coordinate: float
    raw_deviation: float
    bolts: tuple[ProjectedBolt, ...]


@dataclass(frozen=True, slots=True)
class BoltLine:
    """Deterministic line of bolts parallel to the signed force direction."""

    id: str
    ordinal: int
    projected_coordinate: float
    raw_deviation: float
    bolts: tuple[ProjectedBolt, ...]


@dataclass(frozen=True, slots=True)
class RectangularBoltGroupClassification:
    """Measured direct-method geometry classifications without normalization."""

    equal_bolts_per_row: bool
    constant_pitch: bool
    constant_gauge: bool
    nonstaggered: bool
    same_bolt_identity: bool
    same_hole_identity: bool
    same_logical_connection: bool
    pitches: tuple[float, ...]
    gauges: tuple[float, ...]
    pitch_deviation: float
    gauge_deviation: float

    @property
    def supports_uniform_rectangular_method(self) -> bool:
        return all(
            (
                self.equal_bolts_per_row,
                self.constant_pitch,
                self.constant_gauge,
                self.nonstaggered,
                self.same_bolt_identity,
                self.same_hole_identity,
                self.same_logical_connection,
            )
        )


@dataclass(frozen=True, slots=True)
class MultiRowGeometry:
    """Resolved rows, lines, boundaries, and raw measured deviations."""

    group: GeneralBoltGroup
    boundary: PlanarLayerBoundary
    force_u: tuple[float, float]
    force_v: tuple[float, float]
    rows: tuple[BoltRow, ...]
    bolt_lines: tuple[BoltLine, ...]
    classification: RectangularBoltGroupClassification
    unloaded_free_end_u: float
    loaded_end_u: float
    negative_side_v: float
    positive_side_v: float
    first_row_end_distance: float
    first_row_negative_side_distance: float
    first_row_positive_side_distance: float
    sorting_tolerance: float


def _project(point: PlanarPoint2D, axis: tuple[float, float]) -> float:
    return point.x * axis[0] + point.y * axis[1]


def _groups(
    bolts: tuple[ProjectedBolt, ...],
    *,
    coordinate: str,
    reverse: bool,
    tolerance: float,
) -> tuple[tuple[ProjectedBolt, ...], ...]:
    ordered = sorted(
        bolts,
        key=lambda item: (getattr(item, coordinate), item.bolt.id),
        reverse=reverse,
    )
    grouped: list[list[ProjectedBolt]] = []
    for bolt in ordered:
        if not grouped:
            grouped.append([bolt])
            continue
        anchor = sum(getattr(item, coordinate) for item in grouped[-1]) / len(grouped[-1])
        if abs(getattr(bolt, coordinate) - anchor) <= tolerance:
            grouped[-1].append(bolt)
        else:
            grouped.append([bolt])
    return tuple(tuple(items) for items in grouped)


def _constant(values: tuple[float, ...], tolerance: float) -> tuple[bool, float]:
    if len(values) < 2:
        return True, 0.0
    average = sum(values) / len(values)
    deviation = max(abs(value - average) for value in values)
    return deviation <= tolerance, deviation


def resolve_multirow_geometry(
    group: GeneralBoltGroup,
    boundary: PlanarLayerBoundary,
    signed_force_direction: tuple[float, float],
    tolerance: MultiRowGeometryTolerance,
) -> MultiRowGeometry:
    """Resolve physical rows/lines from force and boundary geometry, never array order."""

    if not isinstance(group, GeneralBoltGroup):
        raise TypeError("group must be GeneralBoltGroup.")
    if not isinstance(boundary, PlanarLayerBoundary):
        raise TypeError("boundary must be PlanarLayerBoundary.")
    if not isinstance(tolerance, MultiRowGeometryTolerance):
        raise TypeError("tolerance must be MultiRowGeometryTolerance.")
    if not isinstance(signed_force_direction, tuple) or len(signed_force_direction) != 2:
        raise TypeError("signed_force_direction must be a two-value tuple.")
    x = _finite(signed_force_direction[0], "signed_force_direction[0]")
    y = _finite(signed_force_direction[1], "signed_force_direction[1]")
    norm = math.hypot(x, y)
    if norm <= 0.0:
        raise ValueError("Signed in-plane force direction must be nonzero.")
    u_axis = (x / norm, y / norm)
    v_axis = (-u_axis[1], u_axis[0])
    projected = tuple(
        ProjectedBolt(bolt, _project(bolt.center, u_axis), _project(bolt.center, v_axis))
        for bolt in group.bolts
    )
    corners = tuple(
        PlanarPoint2D(x_value, y_value)
        for x_value in (boundary.min_x, boundary.max_x)
        for y_value in (boundary.min_y, boundary.max_y)
    )
    boundary_u = tuple(_project(point, u_axis) for point in corners)
    boundary_v = tuple(_project(point, v_axis) for point in corners)
    min_u, max_u = min(boundary_u), max(boundary_u)
    min_v, max_v = min(boundary_v), max(boundary_v)
    for bolt in projected:
        if not (
            min_u - tolerance.distance <= bolt.u <= max_u + tolerance.distance
            and min_v - tolerance.distance <= bolt.v <= max_v + tolerance.distance
        ):
            raise ValueError(f"Bolt {bolt.bolt.id!r} lies outside the physical layer boundary.")

    row_groups = _groups(
        projected,
        coordinate="u",
        reverse=True,
        tolerance=tolerance.distance,
    )
    if len(row_groups) != group.declared_row_count:
        raise ValueError("Declared row count does not match force-axis physical row resolution.")
    rows = tuple(
        BoltRow(
            f"ROW_{index}",
            index,
            coordinate := sum(item.u for item in items) / len(items),
            max(abs(item.u - coordinate) for item in items),
            tuple(sorted(items, key=lambda item: (item.v, item.bolt.id))),
        )
        for index, items in enumerate(row_groups, start=1)
    )
    line_groups = _groups(
        projected,
        coordinate="v",
        reverse=False,
        tolerance=tolerance.distance,
    )
    lines = tuple(
        BoltLine(
            f"BOLT_LINE_{index}",
            index,
            coordinate := sum(item.v for item in items) / len(items),
            max(abs(item.v - coordinate) for item in items),
            tuple(sorted(items, key=lambda item: (-item.u, item.bolt.id))),
        )
        for index, items in enumerate(line_groups, start=1)
    )
    pitches = tuple(
        rows[index].projected_coordinate - rows[index + 1].projected_coordinate
        for index in range(len(rows) - 1)
    )
    gauges = tuple(
        lines[index + 1].projected_coordinate - lines[index].projected_coordinate
        for index in range(len(lines) - 1)
    )
    constant_pitch, pitch_deviation = _constant(pitches, tolerance.distance)
    constant_gauge, gauge_deviation = _constant(gauges, tolerance.distance)
    row_counts = tuple(len(row.bolts) for row in rows)
    equal_counts = len(set(row_counts)) == 1
    nonstaggered = equal_counts and all(
        len(row.bolts) == len(lines)
        and all(
            abs(row.bolts[index].v - lines[index].projected_coordinate) <= tolerance.distance
            for index in range(len(lines))
        )
        for row in rows
    )
    classification = RectangularBoltGroupClassification(
        equal_counts,
        constant_pitch,
        constant_gauge,
        nonstaggered,
        len({item.bolt_identity for item in group.bolts}) == 1,
        len({item.hole_diameter for item in group.bolts}) == 1,
        len({item.logical_connection_id for item in group.bolts}) == 1,
        pitches,
        gauges,
        pitch_deviation,
        gauge_deviation,
    )
    first_row = rows[0]
    first_min_v = min(item.v for item in first_row.bolts)
    first_max_v = max(item.v for item in first_row.bolts)
    return MultiRowGeometry(
        group,
        boundary,
        u_axis,
        v_axis,
        rows,
        lines,
        classification,
        min_u,
        max_u,
        min_v,
        max_v,
        max_u - first_row.projected_coordinate,
        first_min_v - min_v,
        max_v - first_max_v,
        tolerance.distance,
    )


class BlockPathFamily(StrEnum):
    U = "U"
    L_LEFT = "L_LEFT"
    L_RIGHT = "L_RIGHT"


class BlockPathSegmentKind(StrEnum):
    SHEAR = "SHEAR"
    TENSION = "TENSION"


class BlockPathRejectionReason(StrEnum):
    BRIDGING_BOLT = "BRIDGING_BOLT"
    NO_FREE_BOUNDARY_CLOSURE = "NO_FREE_BOUNDARY_CLOSURE"
    VOID_CROSSING = "VOID_CROSSING"
    PHYSICAL_BOUNDARY_CROSSING = "PHYSICAL_BOUNDARY_CROSSING"
    DEFERRED_HEEL_CROSSING = "DEFERRED_HEEL_CROSSING"
    DEFERRED_JUNCTION_CROSSING = "DEFERRED_JUNCTION_CROSSING"
    DEFERRED_CORNER_CROSSING = "DEFERRED_CORNER_CROSSING"
    INTERMEDIATE_ROW_TENSION_PLANE = "INTERMEDIATE_ROW_TENSION_PLANE"
    SELF_INTERSECTION = "SELF_INTERSECTION"
    NONPOSITIVE_NET_LENGTH = "NONPOSITIVE_NET_LENGTH"


@dataclass(frozen=True, slots=True)
class ProjectedPoint2D:
    u: float
    v: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "u", _finite(self.u, "ProjectedPoint2D.u"))
        object.__setattr__(self, "v", _finite(self.v, "ProjectedPoint2D.v"))


@dataclass(frozen=True, slots=True)
class BlockPathSegment:
    kind: BlockPathSegmentKind
    start: ProjectedPoint2D
    end: ProjectedPoint2D

    @property
    def length(self) -> float:
        return math.hypot(self.end.u - self.start.u, self.end.v - self.start.v)


@dataclass(frozen=True, slots=True)
class BlockShearCandidatePath:
    """One deterministic physical path candidate with accepted/rejected trace."""

    id: str
    family: BlockPathFamily
    row_id: str
    segments: tuple[BlockPathSegment, ...]
    shear_full_hole_ids: tuple[str, ...]
    tension_full_hole_ids: tuple[str, ...]
    shared_corner_hole_ids: tuple[str, ...]
    rejection_reasons: tuple[BlockPathRejectionReason, ...] = ()

    @property
    def accepted(self) -> bool:
        return not self.rejection_reasons


@dataclass(frozen=True, slots=True)
class BlockShearPathResolution:
    candidates: tuple[BlockShearCandidatePath, ...]

    @property
    def accepted(self) -> tuple[BlockShearCandidatePath, ...]:
        return tuple(item for item in self.candidates if item.accepted)

    @property
    def rejected(self) -> tuple[BlockShearCandidatePath, ...]:
        return tuple(item for item in self.candidates if not item.accepted)


def _segment_bbox(segment: BlockPathSegment) -> tuple[float, float, float, float]:
    return (
        min(segment.start.u, segment.end.u),
        max(segment.start.u, segment.end.u),
        min(segment.start.v, segment.end.v),
        max(segment.start.v, segment.end.v),
    )


def _obstacle_bbox(
    obstacle: RectangularObstacle2D,
    geometry: MultiRowGeometry,
) -> tuple[float, float, float, float]:
    corners = tuple(
        PlanarPoint2D(x, y)
        for x in (obstacle.min_x, obstacle.max_x)
        for y in (obstacle.min_y, obstacle.max_y)
    )
    us = tuple(_project(point, geometry.force_u) for point in corners)
    vs = tuple(_project(point, geometry.force_v) for point in corners)
    return min(us), max(us), min(vs), max(vs)


def _overlaps(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[1] < second[0] or second[1] < first[0] or first[3] < second[2] or second[3] < first[2]
    )


def _proper_intersection(first: BlockPathSegment, second: BlockPathSegment) -> bool:
    shared = {
        (first.start.u, first.start.v),
        (first.end.u, first.end.v),
    } & {
        (second.start.u, second.start.v),
        (second.end.u, second.end.v),
    }
    if shared:
        return False
    return _overlaps(_segment_bbox(first), _segment_bbox(second))


_OBSTACLE_REASON = {
    BoundaryObstacleKind.VOID: BlockPathRejectionReason.VOID_CROSSING,
    BoundaryObstacleKind.DEFERRED_HEEL: BlockPathRejectionReason.DEFERRED_HEEL_CROSSING,
    BoundaryObstacleKind.DEFERRED_JUNCTION: BlockPathRejectionReason.DEFERRED_JUNCTION_CROSSING,
    BoundaryObstacleKind.DEFERRED_CORNER: BlockPathRejectionReason.DEFERRED_CORNER_CROSSING,
}


def validate_block_shear_candidate(
    candidate: BlockShearCandidatePath,
    geometry: MultiRowGeometry,
) -> BlockShearCandidatePath:
    """Fail one candidate closed against physical boundaries and excluded regions."""

    if not isinstance(candidate, BlockShearCandidatePath):
        raise TypeError("candidate must be BlockShearCandidatePath.")
    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    reasons = list(candidate.rejection_reasons)
    if candidate.row_id != "ROW_1":
        reasons.append(BlockPathRejectionReason.INTERMEDIATE_ROW_TENSION_PLANE)
    if any(segment.length <= 0.0 for segment in candidate.segments):
        reasons.append(BlockPathRejectionReason.NONPOSITIVE_NET_LENGTH)
    for first, second in combinations(candidate.segments, 2):
        if _proper_intersection(first, second):
            reasons.append(BlockPathRejectionReason.SELF_INTERSECTION)
            break
    for segment in candidate.segments:
        for point in (segment.start, segment.end):
            if not (
                geometry.unloaded_free_end_u - geometry.sorting_tolerance
                <= point.u
                <= geometry.loaded_end_u + geometry.sorting_tolerance
                and geometry.negative_side_v - geometry.sorting_tolerance
                <= point.v
                <= geometry.positive_side_v + geometry.sorting_tolerance
            ):
                reasons.append(BlockPathRejectionReason.PHYSICAL_BOUNDARY_CROSSING)
        for obstacle in geometry.boundary.obstacles:
            if _overlaps(_segment_bbox(segment), _obstacle_bbox(obstacle, geometry)):
                reasons.append(_OBSTACLE_REASON[obstacle.kind])
    hole_ids = (
        *candidate.shear_full_hole_ids,
        *candidate.tension_full_hole_ids,
        *candidate.shared_corner_hole_ids,
    )
    if len(set(hole_ids)) != len(hole_ids):
        raise ValueError("A physical hole cannot occur in more than one deduction category.")
    return replace(candidate, rejection_reasons=tuple(dict.fromkeys(reasons)))


def _projected_bolt_at(row: BoltRow, line: BoltLine, tolerance: float) -> ProjectedBolt | None:
    return next(
        (bolt for bolt in row.bolts if abs(bolt.v - line.projected_coordinate) <= tolerance),
        None,
    )


def _shear_holes(
    geometry: MultiRowGeometry,
    line: BoltLine,
    row: BoltRow,
) -> tuple[str, ...]:
    return tuple(
        bolt.bolt.id
        for bolt in line.bolts
        if bolt.u < row.projected_coordinate - geometry.sorting_tolerance
    )


def resolve_block_shear_paths(geometry: MultiRowGeometry) -> BlockShearPathResolution:
    """Construct and retain valid/rejected U and side-closing L path candidates."""

    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    candidates: list[BlockShearCandidatePath] = []
    lines = geometry.bolt_lines
    for row in geometry.rows:
        for left, right in combinations(lines, 2):
            corners = tuple(
                bolt.bolt.id
                for line in (left, right)
                if (bolt := _projected_bolt_at(row, line, geometry.sorting_tolerance)) is not None
            )
            tension_full = tuple(
                bolt.bolt.id
                for bolt in row.bolts
                if left.projected_coordinate + geometry.sorting_tolerance
                < bolt.v
                < right.projected_coordinate - geometry.sorting_tolerance
            )
            reasons: list[BlockPathRejectionReason] = []
            if left is not lines[0] or right is not lines[-1]:
                reasons.append(BlockPathRejectionReason.BRIDGING_BOLT)
            if not geometry.boundary.unloaded_end_is_free:
                reasons.append(BlockPathRejectionReason.NO_FREE_BOUNDARY_CLOSURE)
            candidate = BlockShearCandidatePath(
                f"BLOCK_U_{row.id}_{left.id}_{right.id}",
                BlockPathFamily.U,
                row.id,
                (
                    BlockPathSegment(
                        BlockPathSegmentKind.SHEAR,
                        ProjectedPoint2D(geometry.unloaded_free_end_u, left.projected_coordinate),
                        ProjectedPoint2D(row.projected_coordinate, left.projected_coordinate),
                    ),
                    BlockPathSegment(
                        BlockPathSegmentKind.SHEAR,
                        ProjectedPoint2D(geometry.unloaded_free_end_u, right.projected_coordinate),
                        ProjectedPoint2D(row.projected_coordinate, right.projected_coordinate),
                    ),
                    BlockPathSegment(
                        BlockPathSegmentKind.TENSION,
                        ProjectedPoint2D(row.projected_coordinate, left.projected_coordinate),
                        ProjectedPoint2D(row.projected_coordinate, right.projected_coordinate),
                    ),
                ),
                (*_shear_holes(geometry, left, row), *_shear_holes(geometry, right, row)),
                tension_full,
                corners,
                tuple(reasons),
            )
            candidates.append(validate_block_shear_candidate(candidate, geometry))

        for family, line, side_v, side_is_free in (
            (
                BlockPathFamily.L_LEFT,
                lines[0],
                geometry.negative_side_v,
                geometry.boundary.negative_side_is_free,
            ),
            (
                BlockPathFamily.L_RIGHT,
                lines[-1],
                geometry.positive_side_v,
                geometry.boundary.positive_side_is_free,
            ),
        ):
            corner = _projected_bolt_at(row, line, geometry.sorting_tolerance)
            reasons = []
            if not geometry.boundary.unloaded_end_is_free or not side_is_free:
                reasons.append(BlockPathRejectionReason.NO_FREE_BOUNDARY_CLOSURE)
            low, high = sorted((side_v, line.projected_coordinate))
            tension_full = tuple(
                bolt.bolt.id
                for bolt in row.bolts
                if low + geometry.sorting_tolerance < bolt.v < high - geometry.sorting_tolerance
            )
            candidate = BlockShearCandidatePath(
                f"BLOCK_{family.value}_{row.id}_{line.id}",
                family,
                row.id,
                (
                    BlockPathSegment(
                        BlockPathSegmentKind.SHEAR,
                        ProjectedPoint2D(geometry.unloaded_free_end_u, line.projected_coordinate),
                        ProjectedPoint2D(row.projected_coordinate, line.projected_coordinate),
                    ),
                    BlockPathSegment(
                        BlockPathSegmentKind.TENSION,
                        ProjectedPoint2D(row.projected_coordinate, side_v),
                        ProjectedPoint2D(row.projected_coordinate, line.projected_coordinate),
                    ),
                ),
                _shear_holes(geometry, line, row),
                tension_full,
                () if corner is None else (corner.bolt.id,),
                tuple(reasons),
            )
            candidates.append(validate_block_shear_candidate(candidate, geometry))
    return BlockShearPathResolution(tuple(candidates))


__all__ = (
    "BlockPathFamily",
    "BlockPathRejectionReason",
    "BlockPathSegment",
    "BlockPathSegmentKind",
    "BlockShearCandidatePath",
    "BlockShearPathResolution",
    "BoltLine",
    "BoltRow",
    "BoundaryObstacleKind",
    "GeneralBolt",
    "GeneralBoltGroup",
    "MultiRowGeometry",
    "MultiRowGeometryTolerance",
    "PlanarLayerBoundary",
    "PlanarPoint2D",
    "ProjectedBolt",
    "ProjectedPoint2D",
    "RectangularBoltGroupClassification",
    "RectangularObstacle2D",
    "resolve_block_shear_paths",
    "resolve_multirow_geometry",
    "validate_block_shear_candidate",
)
