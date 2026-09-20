"""Stage 4.5 native section/bolt composition; no analytical force allocation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from itertools import combinations
from typing import cast

from frp_master_connection.application.angle_column_base_geometry import BaseContactFootprint
from frp_master_connection.application.column_moment_base_profile import (
    column_centroid_in,
    column_parts,
    native_column_profile,
    surface_id,
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
    _bounds,
    _overlap,
    _part,
    grid,
    inch,
    local_to_global,
    vector,
)
from frp_master_connection.calculation.angle_column_base_response import base_fingerprint
from frp_master_connection.calculation.angle_connector_core import AngleConnectorFrame, Decimal3
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.column_moment_base import ColumnMomentBaseRequest, Face
from frp_master_connection.domain.member_profile import (
    ExactProfileVector3D,
    MemberProfile,
    profile_surface_registry,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.domain.rectangular_full_through_bolt import (
    FullThroughBoltHardware,
    FullThroughBoltPath,
    RectangularMaterialBasis,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    compose_external_connector_layers,
    evaluate_full_through_containment,
    external_connector_layer,
    full_through_bolt_hardware,
)
from frp_master_connection.domain.wi_frp_support_moment import FRPMomentAngle

D = Decimal
Z = D(0)
FRAMES: dict[Face, AngleConnectorFrame] = {
    "X_POS": AngleConnectorFrame((Z, D(1), Z), (Z, Z, D(1)), (D(1), Z, Z)),
    "X_NEG": AngleConnectorFrame((Z, D(-1), Z), (Z, Z, D(1)), (D(-1), Z, Z)),
    "Y_POS": AngleConnectorFrame((D(-1), Z, Z), (Z, Z, D(1)), (Z, D(1), Z)),
    "Y_NEG": AngleConnectorFrame((D(1), Z, Z), (Z, Z, D(1)), (Z, D(-1), Z)),
}


@dataclass(frozen=True, slots=True)
class ColumnMomentGeometry:
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
    full_through_paths: tuple[FullThroughBoltPath, ...]
    full_through_hardware: tuple[FullThroughBoltHardware, ...]
    minimum_member_axis_distance_squared_in2: Decimal | None
    fingerprint: str
    column_upper_failure_boundary: str = "NOT_DEFINED_BY_VIEW_EXTENT"
    foundation_capacity: str = "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    symmetry_allocation: str = "NO_AUTOMATIC_LOAD_SHARING_AUTHORITY"


def _xyz(v: ExactQuantityVector3D) -> Decimal3:
    return inch(v.x), inch(v.y), inch(v.z)


def _placed(
    request: ColumnMomentBaseRequest, profile: MemberProfile, face: Face
) -> PlacedWallAngle:
    item = request.physical_connector(face)
    frame = FRAMES[face]
    spec = item.angle
    t, center = inch(spec.geometry.thickness), inch(item.extrusion_center)
    surface = next(
        s
        for s in profile_surface_registry(profile)
        if s.surface_id is surface_id(request.column, face)
    )
    normal = abs(surface.plane_coordinate)
    cx, cy, _ = column_centroid_in(request.column, profile)
    heel = cast(
        Decimal3,
        tuple(
            (cx, cy, t / 2)[i] + frame.a[i] * center + frame.c[i] * (normal + t / 2)
            for i in range(3)
        ),
    )
    member = replace(
        spec.member_pattern,
        center=PhysicalQuantity(inch(spec.member_pattern.center) - t / 2, Unit.IN),
    )
    support = replace(
        spec.support_pattern,
        center=PhysicalQuantity(inch(spec.support_pattern.center) - t / 2, Unit.IN),
    )
    spec = replace(spec, member_pattern=member, support_pattern=support)
    rm, rs = (Z, inch(member.center), -t / 2), (Z, -t / 2, inch(support.center))
    return PlacedWallAngle(
        face,
        spec,
        frame,
        vector(heel),
        vector(rm),
        vector(rs),
        vector(local_to_global(frame, heel, rm)),
        vector(local_to_global(frame, heel, rs)),
    )


def _footprint(part: WallMomentPart, owner: str) -> BaseContactFootprint:
    lo, hi = _bounds(part)
    return BaseContactFootprint(part.part_id + "_CONTACT", owner, (lo[0], hi[0], lo[1], hi[1]))


def _axis_distance_squared(a: WallMomentHardware, b: WallMomentHardware) -> Decimal:
    # For these parallel/perpendicular cardinal finite segments the minimum in each
    # coordinate is simultaneously attainable. No infinite-line shortcut.
    sa, ea, sb, eb = _xyz(a.start), _xyz(a.end), _xyz(b.start), _xyz(b.end)
    return sum(
        (
            max(
                Z,
                max(min(sa[i], ea[i]), min(sb[i], eb[i]))
                - min(max(sa[i], ea[i]), max(sb[i], eb[i])),
            )
            ** 2
            for i in range(3)
        ),
        Z,
    )


def _external_basis(frame: AngleConnectorFrame) -> RectangularMaterialBasis:
    def native(v: Decimal3) -> ExactProfileVector3D:
        return ExactProfileVector3D(v[2], v[0], v[1])

    return RectangularMaterialBasis(native(frame.a), native(frame.b), native(frame.c))


def resolve_column_moment_base_geometry(request: ColumnMomentBaseRequest) -> ColumnMomentGeometry:
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        height = max(
            max(
                inch(request.physical_connector(f).angle.geometry.member_leg),
                inch(request.physical_connector(f).angle.member_pattern.center)
                + D(request.physical_connector(f).angle.member_pattern.along - 1)
                * inch(request.physical_connector(f).angle.member_pattern.pitch)
                / 2
                + inch(request.physical_connector(f).member_hardware.washer_diameter),
            )
            for f in request.active_faces
        )
        profile = native_column_profile(request.column, height)
        centroid = vector(column_centroid_in(request.column, profile))
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        return _resolve(request, profile, centroid)


def _resolve(
    request: ColumnMomentBaseRequest, profile: MemberProfile, centroid: ExactQuantityVector3D
) -> ColumnMomentGeometry:
    wx, wy, depth = (
        inch(v)
        for v in (request.foundation.width_x, request.foundation.width_y, request.foundation.depth)
    )
    columns = column_parts(request.column, profile, profile.member_length)
    concrete = _part("FOUNDATION", "FOUNDATION", "SUPPORT", (Z, Z, -depth / 2), (wx, wy, depth))
    parts = [*columns, concrete]
    footprints = [_footprint(p, "COLUMN") for p in columns]
    angles = tuple(_placed(request, profile, f) for f in request.active_faces)
    by_face = {a.connector_id: a for a in angles}
    reasons: list[str] = []
    bolts: list[WallMomentHardware] = []
    anchors: list[WallMomentHardware] = []
    washers: list[WallMomentHardware] = []
    envelopes: list[HardwareEnvelope] = []
    paths: list[FullThroughBoltPath] = []
    for angle in angles:
        face = cast(Face, angle.connector_id)
        item = request.physical_connector(face)
        spec = angle.specification
        heel = _xyz(angle.heel)
        frame = angle.frame
        t = inch(spec.geometry.thickness)
        leaf_parts = _angle_parts(angle)
        parts.extend(leaf_parts)
        footprints.append(_footprint(leaf_parts[1], face))
        surface = next(
            s
            for s in profile_surface_registry(profile)
            if s.surface_id is surface_id(request.column, face)
        )
        bounds = surface.contact_bounds
        if face.startswith("X"):
            lower, upper = bounds.min_z, bounds.max_z
            tangential_center = heel[1] - inch(request.column.offset_y)
        else:
            lower, upper = bounds.min_y, bounds.max_y
            tangential_center = heel[0] - inch(request.column.offset_x)
        half_length = inch(spec.geometry.length) / 2
        if tangential_center - half_length < lower or tangential_center + half_length > upper:
            reasons.append(face + ":ANGLE_EXTRUSION_OUTSIDE_SELECTED_FACE")
        _hardware_valid(item.member_hardware, spec.fastener.bolt_diameter, reasons)
        if not D(".375") <= inch(spec.fastener.bolt_diameter) <= 1:
            reasons.append(face + ":BOLT_DIAMETER_OUTSIDE_ASCE_8_2_RANGE")
        if any(v.canonical_magnitude != 0 for v in spec.geometry.heel_end_reliefs):
            reasons.append(face + ":HEEL_END_RELIEF_OUTSIDE_4_5_RC1")
        radius = (
            max(inch(item.member_hardware.washer_diameter), inch(spec.fastener.hole_diameter)) / 2
        )
        selected = replace(profile, selected_surface=surface_id(request.column, face))
        member_points = []
        for ident, a, b in grid(spec.member_pattern):
            member_points.append((a, b))
            if not _leg_contained(cast(FRPMomentAngle, spec), a, b, radius, support=False):
                reasons.append(face + ":MEMBER_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            point = local_to_global(frame, heel, (a, b, -t / 2))
            native = ExactProfileVector3D(
                point[2] - profile.member_length / 2,
                point[0] - inch(request.column.offset_x),
                point[1] - inch(request.column.offset_y),
            )
            native_path = (
                resolve_profile_wall_bolt_path(selected, native, radius)
                if request.column.family == "WI"
                else None
            )
            if native_path is not None and not native_path.valid:
                reasons.append(face + ":MEMBER_BOLT_PATH:" + str(native_path.reason))
            shared = request.shared(face)
            layers: tuple[str, ...]
            bindings: tuple[tuple[str, str], ...]
            if shared and face.endswith("NEG"):
                continue
            bolt_id = face + ":MEMBER:" + ident
            near = local_to_global(frame, heel, (a, b, t / 2))
            if shared:
                partner = cast(Face, face[0] + "_NEG")
                other = by_face[partner]
                other_t = inch(other.specification.geometry.thickness)
                partner_point = next(
                    (
                        bid
                        for bid, pa, pb in grid(other.specification.member_pattern)
                        if local_to_global(other.frame, _xyz(other.heel), (pa, pb, -other_t / 2))[
                            1 if face.startswith("X") else 0
                        ]
                        == point[1 if face.startswith("X") else 0]
                        and local_to_global(other.frame, _xyz(other.heel), (pa, pb, -other_t / 2))[
                            2
                        ]
                        == point[2]
                    ),
                    None,
                )
                if partner_point is None:
                    reasons.append(face + ":OPPOSITE_PHYSICAL_GRID_MISMATCH")
                    continue
                axis_index = 0 if face.startswith("X") else 1
                far = list(near)
                far[axis_index] = (
                    _xyz(other.heel)[axis_index] + other.frame.c[axis_index] * other_t / 2
                )
                far_point = cast(Decimal3, tuple(far))
                bindings = ((face, ident), (partner, partner_point))
                if request.column.family == "WI":
                    layers = (face + "_MEMBER_LEG", "COLUMN_WEB", partner + "_MEMBER_LEG")
                else:
                    core = (
                        build_rhs_full_through_core
                        if request.column.family == "RHS"
                        else build_srs_full_through_core
                    )(
                        selected,
                        surface_id(request.column, face),
                        bolt_id=bolt_id,
                        local_uv=(native.x, native.z if face.startswith("X") else native.y),
                        material_region_id="COLUMN",
                    )
                    containment = evaluate_full_through_containment(
                        selected, core.axis, bolt_id=bolt_id, hole_radius=radius
                    )
                    if containment.status.value != "VALID":
                        reasons.append(face + ":FULL_THROUGH_CONTAINMENT")
                    composed = compose_external_connector_layers(
                        core,
                        near_layers=(
                            external_connector_layer(
                                face + "_MEMBER_LEG",
                                t,
                                material_region_id=face + "_MEMBER_LEG",
                                material_basis=_external_basis(frame),
                            ),
                        ),
                        far_layers=(
                            external_connector_layer(
                                partner + "_MEMBER_LEG",
                                other_t,
                                material_region_id=partner + "_MEMBER_LEG",
                                material_basis=_external_basis(other.frame),
                            ),
                        ),
                    )
                    paths.append(composed)
                    layers = tuple(s.identity for s in composed.segments)
            else:
                opposing = (
                    native_path.opposing_surface_point_local if native_path is not None else None
                )
                if opposing is None:
                    far_point = local_to_global(
                        frame, heel, (a, b, -t / 2 - inch(request.column.flange_thickness))
                    )
                else:
                    far_point = (
                        opposing.y + inch(request.column.offset_x),
                        opposing.z + inch(request.column.offset_y),
                        opposing.x + profile.member_length / 2,
                    )
                layers = (face + "_MEMBER_LEG", "COLUMN_" + face + "_FLANGE")
                bindings = ((face, ident),)
            bolt = WallMomentHardware(
                bolt_id,
                face + "_MEMBER_GROUP",
                vector(near),
                vector(far_point),
                spec.fastener.bolt_diameter,
                spec.fastener.hole_diameter,
                layers,
                bindings,
                2,
                False,
            )
            bolts.append(bolt)
            envelopes.append(_envelope(bolt, item.member_hardware))
        if any(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < (2 * radius) ** 2
            for a, b in combinations(member_points, 2)
        ):
            reasons.append(face + ":MEMBER_HOLE_WASHER_ENVELOPES_OVERLAP")
        ar = max(inch(spec.anchors.washer_outside_diameter), inch(spec.anchors.hole_diameter)) / 2
        if inch(spec.anchors.specified_embedment) > depth:
            reasons.append(face + ":GEOMETRIC_EMBEDMENT_EXCEEDS_PEDESTAL_DEPTH")
        anchor_points = []
        for ident, a, c in grid(spec.support_pattern):
            anchor_points.append((a, c))
            if not _leg_contained(cast(FRPMomentAngle, spec), a, c, ar, support=True):
                reasons.append(face + ":FOUNDATION_HOLE_WASHER_FILLET_SEATING_REQUIRED")
            top = local_to_global(frame, heel, (a, t / 2, c))
            if abs(top[0]) + ar > wx / 2 or abs(top[1]) + ar > wy / 2:
                reasons.append(face + ":FOUNDATION_ATTACHMENT_OUTSIDE_PEDESTAL")
            anchor = WallMomentHardware(
                face + ":FOUNDATION:" + ident,
                face + "_FOUNDATION_GROUP",
                vector(top),
                vector((top[0], top[1], -inch(spec.anchors.specified_embedment))),
                spec.anchors.nominal_diameter,
                spec.anchors.hole_diameter,
                (face + "_SUPPORT_LEG", "FOUNDATION"),
                ((face, ident),),
                1,
                True,
            )
            anchors.append(anchor)
            washers.append(
                replace(
                    anchor,
                    hardware_id=anchor.hardware_id + ":WASHER",
                    start=vector((top[0], top[1], top[2] + inch(spec.anchors.washer_thickness))),
                    end=vector(top),
                    diameter=spec.anchors.washer_outside_diameter,
                )
            )
        if any(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < (2 * ar) ** 2
            for a, b in combinations(anchor_points, 2)
        ):
            reasons.append(face + ":FOUNDATION_HOLE_WASHER_ENVELOPES_OVERLAP")
    for footprint in footprints:
        a, b, c, d = footprint.xy_bounds
        if a < -wx / 2 or b > wx / 2 or c < -wy / 2 or d > wy / 2:
            reasons.append(footprint.owner_id + ":FOOTPRINT_OUTSIDE_FOUNDATION")
    for first_part, second_part in combinations(parts, 2):
        if _overlap(first_part, second_part):
            reasons.append("SOLID_INTERFERENCE:" + first_part.part_id + ":" + second_part.part_id)
    for envelope in envelopes:
        reasons.extend(_hardware_collisions(envelope, tuple(parts)))
    distances = []
    for first_bolt, second_bolt in combinations(bolts, 2):
        distance = _axis_distance_squared(first_bolt, second_bolt)
        distances.append(distance)
        radius = (inch(first_bolt.hole_diameter) + inch(second_bolt.hole_diameter)) / 2
        if distance < radius**2:
            reasons.append(
                "PERPENDICULAR_OR_PARALLEL_SHANK_HOLE_COLLISION:"
                + first_bolt.hardware_id
                + ":"
                + second_bolt.hardware_id
            )
    # Distinct foundation shanks may not overlap one another or an adjacent foot.
    for first_anchor, second_anchor in combinations(anchors, 2):
        if (
            _axis_distance_squared(first_anchor, second_anchor)
            < ((inch(first_anchor.hole_diameter) + inch(second_anchor.hole_diameter)) / 2) ** 2
        ):
            reasons.append("FOUNDATION_SHANKS_INTERSECT")
    unique = tuple(dict.fromkeys(reasons))
    fp = base_fingerprint(
        (
            request.engineering_input(),
            profile,
            angles,
            tuple(parts),
            tuple(bolts),
            tuple(anchors),
            tuple(washers),
            tuple(envelopes),
            tuple(footprints),
            tuple(paths),
            unique,
        )
    )
    display = (
        *column_parts(request.column, profile, inch(request.column.view_length)),
        *(p for p in parts if p.box.component_id != "COLUMN"),
    )
    return ColumnMomentGeometry(
        "INVALID_GEOMETRY" if unique else "VALID",
        unique,
        profile,
        centroid,
        angles,
        tuple(parts),
        display,
        tuple(bolts),
        tuple(anchors),
        tuple(washers),
        tuple(envelopes),
        tuple(footprints),
        tuple(paths),
        tuple(full_through_bolt_hardware(p) for p in paths),
        min(distances) if distances else None,
        fp,
    )
