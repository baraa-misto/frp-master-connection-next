"""Canonical four-angle geometry and physical support hardware for Stage 4.3."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import combinations
from typing import cast

from frp_master_connection.application.wi_frp_support_profile import (
    SupportCrossing,
    SupportPlacement,
    receiving_support_geometry,
    support_crossing,
)
from frp_master_connection.application.wi_wall_moment_geometry import (
    FRAMES,
    PlacedWallAngle,
    WallMomentHardware,
    WallMomentPart,
    _angle_parts,
    _bounds,
    _overlap,
    _part,
    grid,
    inch,
    local_to_global,
    vector,
)
from frp_master_connection.calculation.angle_connector_core import Decimal3, angle_fingerprint
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.domain.wi_frp_support_moment import (
    CONNECTORS,
    FRPMomentAngle,
    SupportHardware,
    WIFrpSupportMomentRequest,
)
from frp_master_connection.domain.wi_wall_moment import WallMomentAngle

D = Decimal
ZERO = D(0)


@dataclass(frozen=True, slots=True)
class SupportBolt:
    hardware: WallMomentHardware
    crossing: SupportCrossing
    support_point: ExactQuantityVector3D
    geometry: SupportHardware
    loaded_planes_status: str = "SOURCE_REQUIRED_ACTUAL_LOADED_INTERFACE_OR_SHAFT_SECTION"


@dataclass(frozen=True, slots=True)
class HardwareEnvelope:
    bolt_id: str
    start: ExactQuantityVector3D
    end: ExactQuantityVector3D
    washer_diameter: PhysicalQuantity
    washer_thickness: PhysicalQuantity
    head_across_flats: PhysicalQuantity
    head_height: PhysicalQuantity
    nut_across_flats: PhysicalQuantity
    nut_height: PhysicalQuantity
    end_extension: PhysicalQuantity
    source: str
    head_start: ExactQuantityVector3D
    head_end: ExactQuantityVector3D
    head_washer_start: ExactQuantityVector3D
    head_washer_end: ExactQuantityVector3D
    nut_washer_start: ExactQuantityVector3D
    nut_washer_end: ExactQuantityVector3D
    nut_start: ExactQuantityVector3D
    nut_end: ExactQuantityVector3D
    shank_start: ExactQuantityVector3D
    shank_end: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class SupportContactPatch:
    patch_id: str
    group_id: str
    face_id: str
    corners: tuple[ExactQuantityVector3D, ...]


@dataclass(frozen=True, slots=True)
class FRPSupportMomentGeometry:
    status: str
    reasons: tuple[str, ...]
    symmetry_proven: bool
    support: SupportPlacement
    angles: tuple[PlacedWallAngle, ...]
    parts: tuple[WallMomentPart, ...]
    member_bolts: tuple[WallMomentHardware, ...]
    support_bolts: tuple[SupportBolt, ...]
    hardware_envelopes: tuple[HardwareEnvelope, ...]
    fingerprint: str
    display_parts: tuple[WallMomentPart, ...]
    support_contact_patches: tuple[SupportContactPatch, ...]
    installation_access: str = (
        "EXPLICIT_PRESET_ENVELOPE_CLEARANCE_NOT_CONSTRUCTION_METHOD_CERTIFICATION"
    )


def _beam_parts(request: WIFrpSupportMomentRequest) -> tuple[WallMomentPart, ...]:
    b = request.beam
    d, bf, tw, tf, length, gap = (
        inch(v)
        for v in (
            b.depth,
            b.flange_width,
            b.web_thickness,
            b.flange_thickness,
            request.beam_physical_length,
            request.gap,
        )
    )
    # Identical accepted W/I three-region slab adapter; physical length, not view clipping.
    return (
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
    )


def _hardware_valid(g: SupportHardware, diameter: PhysicalQuantity, reasons: list[str]) -> None:
    washer = inch(g.washer_diameter)
    # Circumscribed hex diameter squared = 4 AF^2 / 3; no floating sqrt needed.
    if washer < 2 * inch(diameter) or inch(g.washer_thickness) < D(".051"):
        reasons.append("WASHER_DIMENSIONS_BELOW_ASCE_8_2_DETAIL")
    if any(4 * inch(x) ** 2 > 3 * washer**2 for x in (g.head_across_flats, g.nut_across_flats)):
        reasons.append("HEAD_OR_NUT_ENVELOPE_EXCEEDS_CHECKED_WASHER_FOOTPRINT")


def _envelope(b: WallMomentHardware, g: SupportHardware) -> HardwareEnvelope:
    start = cast(Decimal3, tuple(inch(v) for v in (b.start.x, b.start.y, b.start.z)))
    end = cast(Decimal3, tuple(inch(v) for v in (b.end.x, b.end.y, b.end.z)))
    axis = cast(
        Decimal3,
        tuple(D(1) if e > s else D(-1) if e < s else D(0) for s, e in zip(start, end, strict=True)),
    )

    def shift(point: Decimal3, amount: Decimal) -> ExactQuantityVector3D:
        return vector(
            cast(Decimal3, tuple(p + a * amount for p, a in zip(point, axis, strict=True)))
        )

    washer, head, nut, extension = (
        inch(v) for v in (g.washer_thickness, g.head_height, g.nut_height, g.end_extension)
    )
    return HardwareEnvelope(
        b.hardware_id,
        b.start,
        b.end,
        g.washer_diameter,
        g.washer_thickness,
        g.head_across_flats,
        g.head_height,
        g.nut_across_flats,
        g.nut_height,
        g.end_extension,
        g.geometry_source,
        shift(start, -washer - head),
        shift(start, -washer),
        shift(start, -washer),
        b.start,
        b.end,
        shift(end, washer),
        shift(end, washer),
        shift(end, washer + nut),
        shift(start, -washer),
        shift(end, washer + nut + extension),
    )


def _placed(request: WIFrpSupportMomentRequest, i: int, spec: FRPMomentAngle) -> PlacedWallAngle:
    d, tw, t = (
        inch(v) for v in (request.beam.depth, request.beam.web_thickness, spec.geometry.thickness)
    )
    heel = (
        t / 2,
        (d + t) / 2 if i == 0 else -(d + t) / 2 if i == 1 else ZERO,
        (tw + t) / 2 if i == 2 else -(tw + t) / 2 if i == 3 else ZERO,
    )
    rm = (ZERO, inch(spec.member_pattern.center), -t / 2)
    rs = (ZERO, -t / 2, inch(spec.support_pattern.center))
    frame = FRAMES[i]
    # Audited read-only structural seam: the shared part/wrench helpers consume
    # geometry/pattern/fastener/material fields only. No concrete/anchor object exists.
    return PlacedWallAngle(
        CONNECTORS[i],
        cast(WallMomentAngle, spec),
        frame,
        vector(heel),
        vector(rm),
        vector(rs),
        vector(local_to_global(frame, heel, rm)),
        vector(local_to_global(frame, heel, rs)),
    )


def _leg_contained(
    spec: FRPMomentAngle, a: Decimal, b: Decimal, radius: Decimal, *, support: bool
) -> bool:
    g = spec.geometry
    return (
        abs(a) + radius <= inch(g.length) / 2
        and b - radius >= inch(g.thickness) / 2 + inch(g.inside_radius)
        and b + radius <= inch(g.support_leg if support else g.member_leg) - inch(g.thickness) / 2
    )


def resolve_frp_support_moment_geometry(
    request: WIFrpSupportMomentRequest,
) -> FRPSupportMomentGeometry:
    with localcontext() as context:
        context.prec = 100
        return _resolve(request)


def _resolve(request: WIFrpSupportMomentRequest) -> FRPSupportMomentGeometry:
    support = receiving_support_geometry(request.support)
    parts = [*support.parts, *_beam_parts(request)]
    reasons: list[str] = []
    if not ZERO < inch(request.gap) <= D(".5"):
        reasons.append("RC1_REQUIRES_POSITIVE_GAP_AT_MOST_HALF_INCH")
    if request.top != request.bottom:
        reasons.append("LOCKED_TOP_BOTTOM_GEOMETRY_FASTENERS_AND_SOURCE_INPUTS_REQUIRED")
    symmetric = request.positive_web == request.negative_web
    if not symmetric:
        reasons.append("EXACT_WEB_PAIR_SYMMETRY_REQUIRED")
    placed, members, bolts, envelopes = [], [], [], []
    support_points: list[tuple[Decimal3, Decimal]] = []
    for i, spec in enumerate(request.angles):
        angle = _placed(request, i, spec)
        placed.append(angle)
        parts.extend(_angle_parts(angle))
        heel = cast(Decimal3, tuple(inch(v) for v in (angle.heel.x, angle.heel.y, angle.heel.z)))
        frame, name, t = angle.frame, angle.connector_id, inch(spec.geometry.thickness)
        for f, g in (
            (spec.fastener, spec.member_hardware),
            (spec.support_fastener, spec.support_hardware),
        ):
            _hardware_valid(g, f.bolt_diameter, reasons)
            if not D(".375") <= inch(f.bolt_diameter) <= 1:
                reasons.append("BOLT_DIAMETER_OUTSIDE_ASCE_8_2_RANGE")
        radius = (
            max(inch(spec.fastener.hole_diameter), inch(spec.member_hardware.washer_diameter)) / 2
        )
        member_points: list[Decimal3] = []
        for ident, a, b in grid(spec.member_pattern):
            point = local_to_global(frame, heel, (a, b, -t / 2))
            member_points.append(point)
            width = (
                inch(request.beam.flange_width)
                if i < 2
                else inch(request.beam.depth) - 2 * inch(request.beam.flange_thickness)
            )
            if not _leg_contained(spec, a, b, radius, support=False) or not (
                point[0] - radius >= inch(request.gap)
                and point[0] + radius <= inch(request.gap) + inch(request.beam_physical_length)
                and abs(a) + radius <= width / 2
            ):
                reasons.append("COMPLETE_MEMBER_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            if i == 2:
                continue
            start = local_to_global(frame, heel, (a, b, t / 2))
            if i < 2:
                end = local_to_global(
                    frame, heel, (a, b, -t / 2 - inch(request.beam.flange_thickness))
                )
                layers: tuple[str, ...] = (
                    f"{name}_MEMBER_LEG",
                    "WI_TOP_FLANGE" if i == 0 else "WI_BOTTOM_FLANGE",
                )
                bindings: tuple[tuple[str, str], ...] = ((name, ident),)
                group = name
            else:
                end = (
                    start[0],
                    start[1],
                    inch(request.beam.web_thickness) / 2
                    + inch(request.positive_web.geometry.thickness),
                )
                partner = next(
                    (
                        key
                        for key, pa, pb in grid(request.positive_web.member_pattern)
                        if pa == -a and pb == b
                    ),
                    "UNRESOLVED",
                )
                layers = (
                    "NEGATIVE_WEB_ANGLE_MEMBER_LEG",
                    "WI_WEB",
                    "POSITIVE_WEB_ANGLE_MEMBER_LEG",
                )
                bindings = ((name, ident), (CONNECTORS[2], partner))
                group = "COMMON_WEB"
            f = spec.fastener
            hardware = WallMomentHardware(
                f"{group}:{ident}",
                group,
                vector(start),
                vector(end),
                f.bolt_diameter,
                f.hole_diameter,
                layers,
                bindings,
                2,
                False,
            )
            members.append(hardware)
            envelopes.append(_envelope(hardware, spec.member_hardware))
        if any(
            sum((a[j] - b[j]) ** 2 for j in range(3)) < (2 * radius) ** 2
            for a, b in combinations(member_points, 2)
        ):
            reasons.append("MEMBER_HOLE_OR_WASHER_ENVELOPES_OVERLAP")
        radius = (
            max(
                inch(spec.support_fastener.hole_diameter),
                inch(spec.support_hardware.washer_diameter),
            )
            / 2
        )
        for ident, a, c in grid(spec.support_pattern):
            point = local_to_global(frame, heel, (a, -t / 2, c))
            support_points.append((point, radius))
            if not _leg_contained(spec, a, c, radius, support=True):
                reasons.append("COMPLETE_SUPPORT_LEG_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            crossing = support_crossing(
                support, f"{name}:SUPPORT:{ident}", point[1], point[2], radius
            )
            if not crossing.valid:
                reasons.append(f"SUPPORT_HOLE_WASHER_PATH:{crossing.reason}")
            f = spec.support_fastener
            hardware = WallMomentHardware(
                f"{name}:SUPPORT:{ident}",
                f"{name}_SUPPORT_GROUP",
                vector((t, point[1], point[2])),
                vector((-crossing.depth, point[1], point[2])),
                f.bolt_diameter,
                f.hole_diameter,
                (f"{name}_SUPPORT_LEG", *crossing.layer_ids),
                ((name, ident),),
                2,
                False,
            )
            bolts.append(SupportBolt(hardware, crossing, vector(point), spec.support_hardware))
            envelopes.append(_envelope(hardware, spec.support_hardware))
    if any(
        sum((a[0][j] - b[0][j]) ** 2 for j in range(3)) < (a[1] + b[1]) ** 2
        for a, b in combinations(support_points, 2)
    ):
        reasons.append("SUPPORT_GROUP_HOLE_WASHER_ENVELOPES_OVERLAP")
    if any(_overlap(a, b) for a, b in combinations(parts, 2)):
        reasons.append("BEAM_ANGLE_OR_SUPPORT_INTERFERENCE")
    for envelope in envelopes:
        reasons.extend(_hardware_collisions(envelope, tuple(parts)))
    unique = tuple(dict.fromkeys(reasons))
    fingerprint = angle_fingerprint(
        (
            request.engineering_input(),
            support.profile,
            tuple(placed),
            tuple(parts),
            tuple(members),
            tuple(bolts),
            tuple(envelopes),
            unique,
        )
    )
    return FRPSupportMomentGeometry(
        "INVALID_GEOMETRY" if unique else "VALID",
        unique,
        symmetric,
        support,
        tuple(placed),
        tuple(parts),
        tuple(members),
        tuple(bolts),
        tuple(envelopes),
        fingerprint,
        _display_parts(request, tuple(parts)),
        _contact_patches(request, tuple(parts)),
    )


def _contact_patches(
    request: WIFrpSupportMomentRequest, parts: tuple[WallMomentPart, ...]
) -> tuple[SupportContactPatch, ...]:
    patches = []
    for connector in CONNECTORS:
        part = next(p for p in parts if p.part_id == f"{connector}_SUPPORT_LEG")
        lo, hi = _bounds(part)
        patches.append(
            SupportContactPatch(
                f"{connector}:SUPPORT_CONTACT",
                f"{connector}_SUPPORT_GROUP",
                request.support.face,
                tuple(
                    vector((D(0), u, v))
                    for u, v in ((lo[1], lo[2]), (hi[1], lo[2]), (hi[1], hi[2]), (lo[1], hi[2]))
                ),
            )
        )
    return tuple(patches)


def _display_parts(
    request: WIFrpSupportMomentRequest, parts: tuple[WallMomentPart, ...]
) -> tuple[WallMomentPart, ...]:
    """Backend-only viewer clipping, never a code distance, source domain or strength."""
    result = []
    for part in parts:
        lo_tuple, hi_tuple = _bounds(part)
        lo, hi = list(lo_tuple), list(hi_tuple)
        if part.box.component_id == "FRP_SUPPORT":
            half = inch(request.support.view_length) / 2
            lo[1], hi[1] = max(lo[1], -half), min(hi[1], half)
        elif part.box.component_id == "WI_BEAM":
            hi[0] = min(hi[0], inch(request.gap) + inch(request.beam.display_length_each_side))
        if any(a >= b for a, b in zip(lo, hi, strict=True)):
            continue
        region = part.material_region
        axes = None if region is None else (region.lw_axis, region.cw_axis, region.tt_axis)
        result.append(
            _part(
                part.part_id,
                part.box.component_id,
                part.box.role,
                cast(Decimal3, tuple((a + b) / 2 for a, b in zip(lo, hi, strict=True))),
                cast(Decimal3, tuple(b - a for a, b in zip(lo, hi, strict=True))),
                axes,
            )
        )
    return tuple(result)


def _hardware_collisions(
    envelope: HardwareEnvelope, parts: tuple[WallMomentPart, ...]
) -> tuple[str, ...]:
    """Conservative seated-washer/head/nut envelope, exact cardinal bolt direction."""
    start = tuple(inch(v) for v in (envelope.start.x, envelope.start.y, envelope.start.z))
    end = tuple(inch(v) for v in (envelope.end.x, envelope.end.y, envelope.end.z))
    axis = next(i for i in range(3) if start[i] != end[i])
    sign = D(1) if end[axis] > start[axis] else D(-1)
    radius = inch(envelope.washer_diameter) / 2
    for point, extension, direction in (
        (start, inch(envelope.washer_thickness) + inch(envelope.head_height), -sign),
        (
            end,
            inch(envelope.washer_thickness)
            + inch(envelope.nut_height)
            + inch(envelope.end_extension),
            sign,
        ),
    ):
        lo = [point[i] - radius for i in range(3)]
        hi = [point[i] + radius for i in range(3)]
        lo[axis], hi[axis] = sorted((point[axis], point[axis] + direction * extension))
        for part in parts:
            other_lo, other_hi = _bounds(part)
            if all(min(hi[i], other_hi[i]) > max(lo[i], other_lo[i]) for i in range(3)):
                return (
                    f"HARDWARE_INSTALLATION_ENVELOPE_INTERFERENCE:{envelope.bolt_id}:{part.part_id}",
                )
    return ()
