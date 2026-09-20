"""Exact Stage 4.2 physical placement and shared wall/profile/bolt scene contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import combinations
from typing import cast

from frp_master_connection.application.web_splice_orchestration import (
    WebSpliceBox,
    WebSpliceMaterialRegion,
    WebSpliceVector,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    Decimal3,
    angle_fingerprint,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.wi_wall_moment import (
    CONNECTORS,
    WallMomentAngle,
    WallMomentPattern,
    WIWallMomentRequest,
)

D = Decimal
ZERO = D(0)
HALF = D(".5")
FRAMES = tuple(
    AngleConnectorFrame(*(cast(Decimal3, tuple(D(v) for v in axis)) for axis in axes))
    for axes in (
        ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
        ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
        ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
        ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    )
)


def inch(value: PhysicalQuantity) -> Decimal:
    return value.to(Unit.IN).magnitude


def q(value: Decimal | str | int, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def vector(values: tuple[Decimal, ...], unit: Unit = Unit.IN) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(q(v, unit) for v in values))


def xyz(value: ExactQuantityVector3D, unit: Unit = Unit.IN) -> Decimal3:
    return cast(Decimal3, tuple(v.to(unit).magnitude for v in (value.x, value.y, value.z)))


def _scene_vector(values: Decimal3) -> WebSpliceVector:
    return WebSpliceVector(*(q(v) for v in values))


def local_to_global(frame: AngleConnectorFrame, heel: Decimal3, point: Decimal3) -> Decimal3:
    return cast(
        Decimal3,
        tuple(
            heel[j]
            + sum((point[k] * axis[j] for k, axis in enumerate((frame.a, frame.b, frame.c))), ZERO)
            for j in range(3)
        ),
    )


def grid(pattern: WallMomentPattern) -> tuple[tuple[str, Decimal, Decimal], ...]:
    gauge, pitch, center = (inch(v) for v in (pattern.gauge, pattern.pitch, pattern.center))
    return tuple(
        (
            f"B_R{row + 1}_L{line + 1}",
            (D(line) - D(pattern.across - 1) / 2) * gauge,
            center + (D(row) - D(pattern.along - 1) / 2) * pitch,
        )
        for row in range(pattern.along)
        for line in range(pattern.across)
    )


@dataclass(frozen=True, slots=True)
class PlacedWallAngle:
    connector_id: str
    specification: WallMomentAngle
    frame: AngleConnectorFrame
    heel: ExactQuantityVector3D
    member_reference: ExactQuantityVector3D
    support_reference: ExactQuantityVector3D
    member_reference_global: ExactQuantityVector3D
    support_reference_global: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class WallMomentPart:
    part_id: str
    box: WebSpliceBox
    material_region: WebSpliceMaterialRegion | None


@dataclass(frozen=True, slots=True)
class WallMomentHardware:
    hardware_id: str
    group_id: str
    start: ExactQuantityVector3D
    end: ExactQuantityVector3D
    diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    layers: tuple[str, ...]
    connector_bolt_ids: tuple[tuple[str, str], ...]
    exterior_washer_count: int
    blind: bool
    individual_force: None = None
    capacity: None = None


@dataclass(frozen=True, slots=True)
class WallMomentGeometry:
    status: str
    reasons: tuple[str, ...]
    symmetry_proven: bool
    angles: tuple[PlacedWallAngle, ...]
    parts: tuple[WallMomentPart, ...]
    member_bolts: tuple[WallMomentHardware, ...]
    wall_anchors: tuple[WallMomentHardware, ...]
    fingerprint: str


def _part(
    name: str,
    component: str,
    role: str,
    center: Decimal3,
    size: Decimal3,
    axes: tuple[Decimal3, Decimal3, Decimal3] | None = None,
) -> WallMomentPart:
    material = None if axes is None else WebSpliceMaterialRegion(component, name, *axes)
    return WallMomentPart(
        name, WebSpliceBox(component, role, _scene_vector(center), _scene_vector(size)), material
    )


def _bounds(part: WallMomentPart) -> tuple[Decimal3, Decimal3]:
    b = part.box
    centers = tuple(inch(v) for v in (b.center_l_v_t.l, b.center_l_v_t.v, b.center_l_v_t.t))
    sizes = tuple(inch(v) for v in (b.size_l_v_t.l, b.size_l_v_t.v, b.size_l_v_t.t))
    return cast(Decimal3, tuple(c - s / 2 for c, s in zip(centers, sizes, strict=True))), cast(
        Decimal3, tuple(c + s / 2 for c, s in zip(centers, sizes, strict=True))
    )


def _overlap(first: WallMomentPart, second: WallMomentPart) -> bool:
    alo, ahi = _bounds(first)
    blo, bhi = _bounds(second)
    return all(min(ahi[i], bhi[i]) > max(alo[i], blo[i]) for i in range(3))


def _angle_parts(placed: PlacedWallAngle) -> tuple[WallMomentPart, WallMomentPart]:
    g = placed.specification.geometry
    length, member, support, t = (
        inch(v) for v in (g.length, g.member_leg, g.support_leg, g.thickness)
    )
    frame, heel = placed.frame, xyz(placed.heel)
    # Same orthogonal-leg solids as the accepted profile adapter. The corner belongs
    # to the member leg once; the support leg starts at its outside face.
    result = []
    for region, center, size, axes in (
        (
            "MEMBER_LEG",
            (ZERO, (member - t) / 2, ZERO),
            (length, member, t),
            (frame.a, frame.b, frame.c),
        ),
        (
            "SUPPORT_LEG",
            (ZERO, ZERO, support / 2),
            (length, t, support - t),
            (frame.a, frame.c, cast(Decimal3, tuple(-v for v in frame.b))),
        ),
    ):
        global_size = tuple(
            sum(
                (abs(axis[j]) * size[k] for k, axis in enumerate((frame.a, frame.b, frame.c))), ZERO
            )
            for j in range(3)
        )
        result.append(
            _part(
                f"{placed.connector_id}_{region}",
                placed.connector_id,
                "CONNECTOR",
                local_to_global(frame, heel, center),
                cast(Decimal3, global_size),
                axes,
            )
        )
    return result[0], result[1]


def _symmetry_key(angle: WallMomentAngle) -> tuple[object, ...]:
    return (
        angle.geometry,
        angle.member_pattern,
        angle.support_pattern,
        angle.fastener,
        angle.anchors,
        angle.material_id,
        angle.provider_id,
        angle.connector_source_reference,
        angle.attachment_source_reference,
    )


def resolve_wall_moment_geometry(request: WIWallMomentRequest) -> WallMomentGeometry:
    """Resolve all physical solids/endpoints in the exact L/V/T frame, in inches."""
    with localcontext() as context:
        context.prec = 80
        return _resolve_geometry(request)


def _resolve_geometry(request: WIWallMomentRequest) -> WallMomentGeometry:
    d, bf, tw, tf, length = (
        inch(v)
        for v in (
            request.beam.depth,
            request.beam.flange_width,
            request.beam.web_thickness,
            request.beam.flange_thickness,
            request.beam.display_length_each_side,
        )
    )
    gap = inch(request.gap)
    wall = request.wall
    width, height, depth, h, v = (
        inch(q(value, request.source_length_unit))
        for value in (
            wall.width,
            wall.height,
            wall.thickness,
            wall.connection_origin_h,
            wall.connection_origin_v,
        )
    )
    reasons: list[str] = []
    if gap <= 0:
        reasons.append("POSITIVE_BEAM_WALL_GAP_REQUIRED")
    if request.top.geometry != request.bottom.geometry:
        reasons.append("LOCKED_TOP_BOTTOM_FLANGE_ANGLE_GEOMETRY_REQUIRED")
    if any(
        getattr(request.top, key) != getattr(request.bottom, key)
        for key in ("member_pattern", "support_pattern", "fastener", "anchors")
    ):
        reasons.append("LOCKED_TOP_BOTTOM_FLANGE_ATTACHMENT_GEOMETRY_REQUIRED")
    symmetric = _symmetry_key(request.positive_web) == _symmetry_key(request.negative_web)
    placed: list[PlacedWallAngle] = []
    parts = [
        _part(
            "CONCRETE_WALL",
            "CONCRETE_WALL",
            "SUPPORT",
            (-depth / 2, -v, -h),
            (depth, height, width),
        ),
        _part(
            "WI_TOP_FLANGE",
            "WI_BEAM",
            "MEMBER",
            (gap + length / 2, (d - tf) / 2, ZERO),
            (length, tf, bf),
            ((D(1), ZERO, ZERO), (ZERO, ZERO, D(1)), (ZERO, D(-1), ZERO)),
        ),
        _part(
            "WI_WEB",
            "WI_BEAM",
            "MEMBER",
            (gap + length / 2, ZERO, ZERO),
            (length, d - 2 * tf, tw),
            ((D(1), ZERO, ZERO), (ZERO, D(1), ZERO), (ZERO, ZERO, D(1))),
        ),
        _part(
            "WI_BOTTOM_FLANGE",
            "WI_BEAM",
            "MEMBER",
            (gap + length / 2, -(d - tf) / 2, ZERO),
            (length, tf, bf),
            ((D(1), ZERO, ZERO), (ZERO, ZERO, D(1)), (ZERO, D(-1), ZERO)),
        ),
    ]
    bolts: list[WallMomentHardware] = []
    anchors: list[WallMomentHardware] = []
    for i, (name, spec, frame) in enumerate(zip(CONNECTORS, request.angles, FRAMES, strict=True)):
        t = inch(spec.geometry.thickness)
        heel: Decimal3 = (
            t / 2,
            (d + t) / 2 if i == 0 else -(d + t) / 2 if i == 1 else ZERO,
            (tw + t) / 2 if i == 2 else -(tw + t) / 2 if i == 3 else ZERO,
        )
        rm: Decimal3 = (ZERO, inch(spec.member_pattern.center), -t / 2)
        rs: Decimal3 = (ZERO, -t / 2, inch(spec.support_pattern.center))
        item = PlacedWallAngle(
            name,
            spec,
            frame,
            vector(heel),
            vector(rm),
            vector(rs),
            vector(local_to_global(frame, heel, rm)),
            vector(local_to_global(frame, heel, rs)),
        )
        placed.append(item)
        parts.extend(_angle_parts(item))
        span = inch(spec.geometry.length)
        radius = inch(spec.fastener.hole_diameter) / 2
        if (spec.member_pattern.across > 1 and inch(spec.member_pattern.gauge) < 2 * radius) or (
            spec.member_pattern.along > 1 and inch(spec.member_pattern.pitch) < 2 * radius
        ):
            reasons.append("MEMBER_HOLES_MUST_NOT_OVERLAP")
        for bolt_id, a, b in grid(spec.member_pattern):
            center = local_to_global(frame, heel, (a, b, -t / 2))
            if (
                abs(a) + radius > span / 2
                or b - radius < t / 2 + inch(spec.geometry.inside_radius)
                or b + radius > inch(spec.geometry.member_leg) - t / 2
                or center[0] - radius < gap
                or center[0] + radius > gap + length
                or abs(a) + radius > (bf / 2 if i < 2 else (d - 2 * tf) / 2)
            ):
                reasons.append("COMPLETE_MEMBER_HOLE_CONTAINMENT_REQUIRED")
            if i == 2:
                continue  # The negative-side grid creates each common physical shank once.
            start = local_to_global(frame, heel, (a, b, t / 2))
            if i < 2:
                end = local_to_global(frame, heel, (a, b, -t / 2 - tf))
                layers: tuple[str, ...] = (
                    f"{name}_MEMBER_LEG",
                    "WI_TOP_FLANGE" if i == 0 else "WI_BOTTOM_FLANGE",
                )
                identities: tuple[tuple[str, str], ...] = ((name, bolt_id),)
                group = name
            else:
                end = (start[0], start[1], tw / 2 + inch(request.positive_web.geometry.thickness))
                layers = (
                    "NEGATIVE_WEB_CLIP_ANGLE_MEMBER_LEG",
                    "WI_WEB",
                    "POSITIVE_WEB_CLIP_ANGLE_MEMBER_LEG",
                )
                partner = next(
                    (
                        ident
                        for ident, pa, pb in grid(request.positive_web.member_pattern)
                        if pa == -a and pb == b
                    ),
                    "UNRESOLVED",
                )
                identities = ((name, bolt_id), (CONNECTORS[2], partner))
                group = "COMMON_WEB"
            bolts.append(
                WallMomentHardware(
                    f"{group}:{bolt_id}",
                    group,
                    vector(start),
                    vector(end),
                    spec.fastener.bolt_diameter,
                    spec.fastener.hole_diameter,
                    layers,
                    identities,
                    2,
                    False,
                )
            )
        anchor_radius = inch(spec.anchors.hole_diameter) / 2
        if (
            spec.support_pattern.across > 1 and inch(spec.support_pattern.gauge) < 2 * anchor_radius
        ) or (
            spec.support_pattern.along > 1 and inch(spec.support_pattern.pitch) < 2 * anchor_radius
        ):
            reasons.append("ANCHOR_HOLES_MUST_NOT_OVERLAP")
        embedment = inch(spec.anchors.specified_embedment)
        for anchor_id, a, c in grid(spec.support_pattern):
            front = local_to_global(frame, heel, (a, -t / 2, c))
            if (
                abs(a) + anchor_radius > span / 2
                or c - anchor_radius < t / 2 + inch(spec.geometry.inside_radius)
                or c + anchor_radius > inch(spec.geometry.support_leg) - t / 2
            ):
                reasons.append("COMPLETE_SUPPORT_LEG_HOLE_CONTAINMENT_REQUIRED")
            if (
                abs(front[1] + v) + anchor_radius > height / 2
                or abs(front[2] + h) + anchor_radius > width / 2
                or embedment > depth
            ):
                reasons.append("COMPLETE_ANCHOR_HOLE_WALL_CONTAINMENT_REQUIRED")
            start = (t, front[1], front[2])
            end = (-embedment, front[1], front[2])
            anchors.append(
                WallMomentHardware(
                    f"{name}:ANCHOR:{anchor_id}",
                    f"{name}_WALL_GROUP",
                    vector(start),
                    vector(end),
                    spec.anchors.nominal_diameter,
                    spec.anchors.hole_diameter,
                    (f"{name}_SUPPORT_LEG", "CONCRETE_WALL"),
                    (),
                    1,
                    True,
                )
            )
    if any(_overlap(a, b) for a, b in combinations(parts, 2)):
        reasons.append("ANGLE_OR_SUPPORT_LEG_INTERFERENCE")
    unique = tuple(dict.fromkeys(reasons))
    status = "INVALID_GEOMETRY" if unique else "VALID" if symmetric else "NOT_EVALUATED"
    if not symmetric:
        unique += ("EXACT_WEB_PAIR_SYMMETRY_REQUIRED",)
    fingerprint = angle_fingerprint(
        (tuple(parts), tuple(bolts), tuple(anchors), tuple(placed), unique, symmetric)
    )
    return WallMomentGeometry(
        status,
        unique,
        symmetric,
        tuple(placed),
        tuple(parts),
        tuple(bolts),
        tuple(anchors),
        fingerprint,
    )
