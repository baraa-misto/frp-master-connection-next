"""Backend-authoritative two-exterior-leg geometry, references and real bolt paths."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from itertools import combinations
from typing import cast

from frp_master_connection.application.member_profile_geometry import (
    create_oriented_standard_topology,
)
from frp_master_connection.application.wi_frp_support_moment_geometry import (
    HardwareEnvelope,
    _envelope,
    _hardware_collisions,
    _hardware_valid,
    _leg_contained,
)
from frp_master_connection.application.wi_wall_moment_geometry import (
    PlacedWallAngle,
    WallMomentHardware,
    WallMomentPart,
    _angle_parts,
    _overlap,
    _part,
    grid,
    inch,
    local_to_global,
    vector,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    Decimal3,
    angle_fingerprint,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    CONNECTORS,
    AngleColumnMomentBaseRequest,
)
from frp_master_connection.domain.member_profile import (
    AngleProfileDimensions,
    ExactProfileVector3D,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    profile_member_axis_reference,
    resolve_angle_leg_bolt_path,
)
from frp_master_connection.domain.section_topology import (
    FRPComponentOrientation,
    PlanarFixedMaterialOrientation,
)
from frp_master_connection.domain.values import (
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    MemberRole,
    PrincipalAxisFamily,
    SectionFamily,
)
from frp_master_connection.domain.wi_frp_support_moment import FRPMomentAngle

D = Decimal
Z = D(0)
ONE = D(1)
FRAMES = (
    AngleConnectorFrame((ONE, Z, Z), (Z, Z, ONE), (Z, -ONE, Z)),
    AngleConnectorFrame((Z, -ONE, Z), (Z, Z, ONE), (-ONE, Z, Z)),
)


@dataclass(frozen=True, slots=True)
class BaseContactFootprint:
    patch_id: str
    owner_id: str
    xy_bounds: tuple[Decimal, Decimal, Decimal, Decimal]
    normal_on_foundation: Decimal3 = (Z, Z, -ONE)


@dataclass(frozen=True, slots=True)
class AngleBaseGeometry:
    status: str
    reasons: tuple[str, ...]
    native_column_profile: MemberProfile
    column_centroid: ExactQuantityVector3D
    angles: tuple[PlacedWallAngle, ...]
    parts: tuple[WallMomentPart, ...]
    display_parts: tuple[WallMomentPart, ...]
    member_bolts: tuple[WallMomentHardware, ...]
    foundation_attachments: tuple[WallMomentHardware, ...]
    foundation_washers: tuple[WallMomentHardware, ...]
    member_hardware_envelopes: tuple[HardwareEnvelope, ...]
    footprints: tuple[BaseContactFootprint, ...]
    fingerprint: str
    column_upper_failure_boundary: str = "NOT_DEFINED_BY_VIEW_EXTENT"
    foundation_capacity: str = "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    symmetry_allocation: str = "NO_AUTOMATIC_LOAD_SHARING_AUTHORITY"


def native_column_profile(request: AngleColumnMomentBaseRequest) -> MemberProfile:
    """Canonical local inspection extent; never an engineering upper failure plane."""
    c = request.column
    local_height = max(
        max(
            inch(v.angle.geometry.member_leg),
            inch(v.angle.member_pattern.center)
            + D(v.angle.member_pattern.along - 1) * inch(v.angle.member_pattern.pitch) / 2
            + inch(v.member_hardware.washer_diameter),
        )
        for v in request.connectors
    )
    return MemberProfile(
        "ANGLE_COLUMN_PROFILE",
        "ANGLE_COLUMN",
        MemberRole.COLUMN,
        MemberProfileFamily.ANGLE,
        AngleProfileDimensions(local_height, inch(c.leg_x), inch(c.leg_y), inch(c.thickness)),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "ANGLE_COLUMN"),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.LEG_Y_OUTER,
    )


def _column_parts(
    request: AngleColumnMomentBaseRequest, height: Decimal
) -> tuple[WallMomentPart, ...]:
    bx, by, t = (
        inch(v) for v in (request.column.leg_x, request.column.leg_y, request.column.thickness)
    )
    # R14B owns the region bases. Proper cyclic map: member (x,y,z) -> base (Z,X,Y).
    topology = create_oriented_standard_topology(SectionFamily.ANGLE)
    mapped = {
        PrincipalAxisFamily.X: (Z, Z, ONE),
        PrincipalAxisFamily.Y: (ONE, Z, Z),
        PrincipalAxisFamily.Z: (Z, ONE, Z),
    }
    regions = []
    for i, (center, size) in enumerate(
        (
            ((bx / 2, t / 2, height / 2), (bx, t, height)),
            ((t / 2, (by + t) / 2, height / 2), (t, by - t, height)),
        )
    ):
        orientation = cast(PlanarFixedMaterialOrientation, topology.material_regions[i].orientation)
        cw = cast(
            Decimal3,
            tuple(v * orientation.crosswise_sign for v in mapped[orientation.crosswise_axis]),
        )
        tt = cast(
            Decimal3,
            tuple(
                v * orientation.through_thickness_sign
                for v in mapped[orientation.through_thickness_axis]
            ),
        )
        regions.append(
            _part(
                f"COLUMN_LEG_{i + 1}", "ANGLE_COLUMN", "MEMBER", center, size, ((Z, Z, ONE), cw, tt)
            )
        )
    return tuple(regions)


def _placed(request: AngleColumnMomentBaseRequest, index: int) -> PlacedWallAngle:
    item = request.connectors[index]
    spec = item.angle
    t, center = inch(spec.geometry.thickness), inch(item.extrusion_center)
    # Native heel is the intersection of leaf midsurfaces, NOT the concrete corner.
    # Both leaf bottoms are exactly at Z=0; outside member face is exactly X/Y=0.
    heel = (center, -t / 2, t / 2) if index == 0 else (-t / 2, center, t / 2)
    member = replace(
        spec.member_pattern,
        center=PhysicalQuantity(inch(spec.member_pattern.center) - t / 2, Unit.IN),
    )
    support = replace(
        spec.support_pattern,
        center=PhysicalQuantity(inch(spec.support_pattern.center) - t / 2, Unit.IN),
    )
    native = replace(spec, member_pattern=member, support_pattern=support)
    rm, rs = (Z, inch(member.center), -t / 2), (Z, -t / 2, inch(support.center))
    frame = FRAMES[index]
    return PlacedWallAngle(
        CONNECTORS[index],
        native,
        frame,
        vector(heel),
        vector(rm),
        vector(rs),
        vector(local_to_global(frame, heel, rm)),
        vector(local_to_global(frame, heel, rs)),
    )


def resolve_angle_base_geometry(request: AngleColumnMomentBaseRequest) -> AngleBaseGeometry:
    # Stage 3.7 native profile arithmetic is Decimal-28 HALF_EVEN, not a Slice-5 oracle.
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        profile = native_column_profile(request)
        native = profile_member_axis_reference(profile)
    centroid = vector((native.y, native.z, Z))
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        return _resolve(request, profile, centroid)


def _resolve(
    request: AngleColumnMomentBaseRequest, profile: MemberProfile, centroid: ExactQuantityVector3D
) -> AngleBaseGeometry:
    foundation = request.foundation
    wx, wy, depth = (inch(v) for v in (foundation.width_x, foundation.width_y, foundation.depth))
    concrete = _part("FOUNDATION", "FOUNDATION", "SUPPORT", (Z, Z, -depth / 2), (wx, wy, depth))
    parts = [*_column_parts(request, profile.member_length), concrete]
    reasons: list[str] = []
    angles, bolts, anchors, envelopes = [], [], [], []
    washers = []
    bx, by, tcol = (
        inch(v) for v in (request.column.leg_x, request.column.leg_y, request.column.thickness)
    )
    footprints = [
        BaseContactFootprint("COLUMN_LEG_1_CONTACT", "ANGLE_COLUMN", (Z, bx, Z, tcol)),
        BaseContactFootprint("COLUMN_LEG_2_CONTACT", "ANGLE_COLUMN", (Z, tcol, tcol, by)),
    ]
    if bx > wx / 2 or by > wy / 2:
        reasons.append("COLUMN_END_NOT_CONTAINED_IN_FOUNDATION")
    for i, item in enumerate(request.connectors):
        angle = _placed(request, i)
        angles.append(angle)
        parts.extend(_angle_parts(angle))
        spec = angle.specification
        frame = angle.frame
        heel = cast(Decimal3, tuple(inch(v) for v in (angle.heel.x, angle.heel.y, angle.heel.z)))
        t = inch(spec.geometry.thickness)
        _hardware_valid(item.member_hardware, spec.fastener.bolt_diameter, reasons)
        if not D(".375") <= inch(spec.fastener.bolt_diameter) <= 1:
            reasons.append("BOLT_DIAMETER_OUTSIDE_ASCE_8_2_RANGE")
        if any(q.canonical_magnitude != 0 for q in spec.geometry.heel_end_reliefs):
            reasons.append("HEEL_END_RELIEF_OUTSIDE_4_4_PRESET_DOMAIN")
        radius = (
            max(inch(item.member_hardware.washer_diameter), inch(spec.fastener.hole_diameter)) / 2
        )
        p = replace(
            profile,
            selected_surface=MemberProfileSurfaceId.LEG_Y_OUTER
            if i == 0
            else MemberProfileSurfaceId.LEG_Z_OUTER,
        )
        member_points = []
        for ident, a, b in grid(spec.member_pattern):
            point = local_to_global(frame, heel, (a, b, -t / 2))
            # Native profile extrusions are centered about local x=0. The physical
            # lower end of this local inspection segment is global Z=0.
            path = resolve_angle_leg_bolt_path(
                p, ExactProfileVector3D(point[2] - profile.member_length / 2, point[0], point[1])
            )
            if not path.valid:
                reasons.append(f"MEMBER_BOLT_PATH:{path.reason}")
            coordinate = point[0] if i == 0 else point[1]
            if coordinate - radius < tcol or coordinate + radius > (bx if i == 0 else by):
                reasons.append("COLUMN_HOLE_WASHER_NOT_ON_EXPOSED_MATCHING_LEG")
            # This accepted leaf helper reads only the shared AngleConnectorGeometry.
            # The cast is structural reuse, not a fabricated Stage 4.3 product input.
            if not _leg_contained(cast(FRPMomentAngle, spec), a, b, radius, support=False):
                reasons.append("MEMBER_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            near = local_to_global(frame, heel, (a, b, t / 2))
            opposing = path.opposing_surface_point_local
            far = (
                (opposing.y, opposing.z, opposing.x + profile.member_length / 2)
                if opposing is not None
                else local_to_global(frame, heel, (a, b, -t / 2 - tcol))
            )
            bolt = WallMomentHardware(
                f"{CONNECTORS[i]}:{ident}",
                f"{CONNECTORS[i]}_MEMBER_GROUP",
                vector(near),
                vector(far),
                spec.fastener.bolt_diameter,
                spec.fastener.hole_diameter,
                (f"{CONNECTORS[i]}_MEMBER_LEG", f"COLUMN_LEG_{i + 1}"),
                ((CONNECTORS[i], ident),),
                2,
                False,
            )
            bolts.append(bolt)
            envelopes.append(_envelope(bolt, item.member_hardware))
            member_points.append((a, b))
        if any(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < (2 * radius) ** 2
            for a, b in combinations(member_points, 2)
        ):
            reasons.append("MEMBER_HOLE_WASHER_ENVELOPES_OVERLAP")
        anchor_radius = (
            max(inch(spec.anchors.washer_outside_diameter), inch(spec.anchors.hole_diameter)) / 2
        )
        if inch(spec.anchors.specified_embedment) > depth:
            reasons.append("GEOMETRIC_EMBEDMENT_EXCEEDS_PEDESTAL_DEPTH")
        anchor_points = []
        for ident, a, c in grid(spec.support_pattern):
            if not _leg_contained(cast(FRPMomentAngle, spec), a, c, anchor_radius, support=True):
                reasons.append("FOUNDATION_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            top = local_to_global(frame, heel, (a, t / 2, c))
            end = (top[0], top[1], -inch(spec.anchors.specified_embedment))
            if abs(top[0]) + anchor_radius > wx / 2 or abs(top[1]) + anchor_radius > wy / 2:
                reasons.append("FOUNDATION_ATTACHMENT_OUTSIDE_PEDESTAL")
            anchors.append(
                WallMomentHardware(
                    f"{CONNECTORS[i]}:FOUNDATION:{ident}",
                    f"{CONNECTORS[i]}_FOUNDATION_GROUP",
                    vector(top),
                    vector(end),
                    spec.anchors.nominal_diameter,
                    spec.anchors.hole_diameter,
                    (f"{CONNECTORS[i]}_SUPPORT_LEG", "FOUNDATION"),
                    ((CONNECTORS[i], ident),),
                    1,
                    True,
                )
            )
            washers.append(
                replace(
                    anchors[-1],
                    hardware_id=f"{anchors[-1].hardware_id}:WASHER",
                    start=vector((top[0], top[1], top[2] + inch(spec.anchors.washer_thickness))),
                    end=vector(top),
                    diameter=spec.anchors.washer_outside_diameter,
                )
            )
            anchor_points.append((a, c))
        if any(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < (2 * anchor_radius) ** 2
            for a, b in combinations(anchor_points, 2)
        ):
            reasons.append("FOUNDATION_HOLE_WASHER_ENVELOPES_OVERLAP")
        half = inch(spec.geometry.length) / 2
        foot = inch(spec.geometry.support_leg)
        center = inch(item.extrusion_center)
        bounds = (
            (center - half, center + half, -foot, Z)
            if i == 0
            else (-foot, Z, center - half, center + half)
        )
        footprints.append(
            BaseContactFootprint(f"{CONNECTORS[i]}_FOOT_CONTACT", CONNECTORS[i], bounds)
        )
        if bounds[0] < -wx / 2 or bounds[1] > wx / 2 or bounds[2] < -wy / 2 or bounds[3] > wy / 2:
            reasons.append("CONNECTOR_FOOT_NOT_CONTAINED_IN_FOUNDATION")
    if any(_overlap(a, b) for a, b in combinations(parts, 2)):
        reasons.append("COLUMN_CONNECTOR_FOUNDATION_SOLID_INTERFERENCE")
    for envelope in envelopes:
        reasons.extend(_hardware_collisions(envelope, tuple(parts)))
    unique = tuple(dict.fromkeys(reasons))
    fingerprint = angle_fingerprint(
        (
            request.engineering_input(),
            profile,
            tuple(angles),
            tuple(parts),
            tuple(bolts),
            tuple(anchors),
            tuple(washers),
            tuple(envelopes),
            tuple(footprints),
            unique,
        )
    )
    display = (
        *_column_parts(request, inch(request.column.view_length)),
        *(p for p in parts if p.box.component_id != "ANGLE_COLUMN"),
    )
    return AngleBaseGeometry(
        "INVALID_GEOMETRY" if unique else "VALID",
        unique,
        profile,
        centroid,
        tuple(angles),
        tuple(parts),
        display,
        tuple(bolts),
        tuple(anchors),
        tuple(washers),
        tuple(envelopes),
        tuple(footprints),
        fingerprint,
    )
