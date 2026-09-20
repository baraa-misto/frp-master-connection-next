"""Native DCTN profiles and physical shaft geometry, separate from response authority."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from itertools import combinations
from typing import cast

from frp_master_connection.application.member_profile_geometry import (
    create_member_profile_cross_section,
    create_oriented_standard_topology,
)
from frp_master_connection.calculation.angle_connector_core import (
    Rational3,
    exact_decimal,
)
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.domain.dctn_geometry import (
    DCTNGeometry,
    DCTNHole,
    DCTNPlacedMember,
    DCTNRowGeometry,
    DCTNShaft,
)
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNForm,
    DCTNMember,
    DCTNRequest,
    make_profile,
)
from frp_master_connection.domain.entities import AssemblyMember
from frp_master_connection.domain.member_profile import (
    ExactProfileVector3D,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
    profile_section_geometry_adapter,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.domain.rectangular_full_through_bolt import (
    FullThroughBoltPath,
    RectangularContainmentStatus,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    evaluate_full_through_containment,
)
from frp_master_connection.domain.values import MemberEnd, PositionVector3D
from frp_master_connection.geometry import (
    SectionDatumOffset,
    Vector3D,
    place_member,
    placed_rectangular_elements_overlap,
)
from frp_master_connection.geometry.placement import (
    LocalRectangularPrism3D,
    PlacedComponentGeometry3D,
    PlacedPhysicalElement3D,
)

D = Decimal
F = Fraction
ZERO = F(0)


def _triple(value: Vector3D | PositionVector3D) -> Rational3:
    return F(str(value.x)), F(str(value.y)), F(str(value.z))


def placed(
    profile: MemberProfile, start: Rational3, end: Rational3, z: Vector3D
) -> DCTNPlacedMember:
    topology = create_oriented_standard_topology(profile.section_family)
    member = AssemblyMember(
        profile.member_id,
        profile.member_id,
        profile.role,
        MemberEnd.START,
        profile.section_family,
        profile.material_kind,
        profile.material_orientation,
        topology,
    )
    adapter = profile_section_geometry_adapter(profile)
    placement = place_member(
        member,
        create_member_profile_cross_section(profile, topology),
        PositionVector3D(*(float(x) for x in start)),
        PositionVector3D(*(float(x) for x in end)),
        z,
        SectionDatumOffset(
            float(adapter.section_datum_offset_y), float(adapter.section_datum_offset_z)
        ),
    )
    frame = placement.global_frame
    return DCTNPlacedMember(
        profile.member_id,
        profile,
        placement,
        start,
        _triple(frame.x_axis),
        _triple(frame.y_axis),
        _triple(frame.z_axis),
    )


def local_point(member: DCTNPlacedMember, u: Fraction, v: Fraction, w: Fraction) -> Rational3:
    """Exact transport of the existing native frame components, not a second normalization."""
    return (
        member.start[0] + u * member.u[0] + v * member.v[0] + w * member.w[0],
        member.start[1] + u * member.u[1] + v * member.v[1] + w * member.w[1],
        member.start[2] + u * member.u[2] + v * member.v[2] + w * member.w[2],
    )


def _collision_elements(a: PlacedComponentGeometry3D) -> tuple[PlacedPhysicalElement3D, ...]:
    """Include finite deferred corners without making them resistance regions.

    A native solid-rectangle placement is used ONLY as an exact collision proxy
    for the native deferred rectangle. Zero-thickness junctions are not solids.
    The proxy never enters assembly members, bolt layers or source ownership.
    """
    result = list(a.physical_elements)
    for index, feature in enumerate(a.deferred_features):
        prism = feature.extrusion
        if not isinstance(prism, LocalRectangularPrism3D):
            continue
        extent, rectangle = prism.extent, prism.rectangle
        middle_y = (rectangle.min_y + rectangle.max_y) / 2
        middle_z = (rectangle.min_z + rectangle.max_z) / 2
        start = feature.global_frame.local_to_parent_point(
            PositionVector3D(extent.x_start, middle_y, middle_z)
        )
        end = feature.global_frame.local_to_parent_point(
            PositionVector3D(extent.x_end, middle_y, middle_z)
        )
        profile = make_profile(
            f"{a.component.id}:DEFERRED_COLLISION_ONLY:{index}",
            MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
            SolidRectangularProfileDimensions(
                D(str(extent.length)),
                D(str(rectangle.max_z - rectangle.min_z)),
                D(str(rectangle.max_y - rectangle.min_y)),
            ),
            MemberProfileSurfaceId.Z_NEG_FACE,
        )
        result.extend(
            placed(
                profile, _triple(start), _triple(end), feature.global_frame.z_axis
            ).placement.physical_elements
        )
    return tuple(result)


def _overlap(
    a: tuple[PlacedPhysicalElement3D, ...], b: tuple[PlacedPhysicalElement3D, ...]
) -> bool:
    return any(placed_rectangular_elements_overlap(x, y) for x in a for y in b)


def _shaft_intersects_element(
    shaft: DCTNShaft, element: PlacedPhysicalElement3D, radius: Decimal
) -> bool:
    """Actual finite circular shaft versus a native DCTN rectangular extrusion.

    DCTN shafts are normal to the node plane. Each native prism has exactly
    one axis parallel to that shaft, so this is an interval plus disk/rectangle
    intersection, not a square/cube envelope and not a resistance calculation.
    Native frames and primitive bounds remain the sole geometry authority.
    """
    frame = element.global_frame
    axes = (frame.x_axis, frame.y_axis, frame.z_axis)
    parallel = tuple(i for i, axis in enumerate(axes) if abs(axis.y) == 1)
    if len(parallel) != 1 or any(axis.y != 0 for i, axis in enumerate(axes) if i not in parallel):
        raise ValueError("DCTN shaft intersection requires the native node-plane frame")
    axis = parallel[0]
    entry = frame.parent_to_local_point(PositionVector3D(*(float(v) for v in shaft.start)))
    exit = frame.parent_to_local_point(PositionVector3D(*(float(v) for v in shaft.end)))
    start, end = (entry.x, entry.y, entry.z), (exit.x, exit.y, exit.z)
    for prism in element.extrusions:
        if not isinstance(prism, LocalRectangularPrism3D):
            raise ValueError("DCTN shaft intersection requires native rectangular primitives")
        bounds = (
            (prism.extent.x_start, prism.extent.x_end),
            (prism.rectangle.min_y, prism.rectangle.max_y),
            (prism.rectangle.min_z, prism.rectangle.max_z),
        )
        if min(max(start[axis], end[axis]), bounds[axis][1]) <= max(
            min(start[axis], end[axis]), bounds[axis][0]
        ):
            continue
        distance_squared = sum(
            (start[i] - max(low, min(start[i], high))) ** 2
            for i, (low, high) in enumerate(bounds)
            if i != axis
        )
        if distance_squared < float(radius) ** 2:
            return True
    return False


def _envelope(
    identity: str,
    point: Rational3,
    extension: Decimal,
    radius: Decimal,
    sign: int,
    in_plane_axis: Vector3D,
) -> PlacedComponentGeometry3D:
    # Kernel-only enclosing prism. Never a physical FRP member, resistance layer or material role.
    profile = make_profile(
        identity,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
        SolidRectangularProfileDimensions(extension, 2 * radius, 2 * radius),
        MemberProfileSurfaceId.Z_NEG_FACE,
    )
    end = point[0], point[1] + sign * F(extension), point[2]
    return placed(profile, point, end, in_plane_axis).placement


def _member_hole(
    profile: MemberProfile,
    u: Decimal,
    offset: Decimal,
    sign: int,
    radius: Decimal,
) -> bool:
    if profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        core = build_srs_full_through_core(
            profile,
            MemberProfileSurfaceId.Z_NEG_FACE,
            bolt_id="FOOTPRINT",
            local_uv=(u, offset),
            material_region_id=profile.member_id,
        )
        return (
            evaluate_full_through_containment(
                profile,
                core.axis,
                bolt_id=core.bolt_id,
                hole_radius=radius,
            ).status
            is RectangularContainmentStatus.VALID
        )
    sid = (
        (
            MemberProfileSurfaceId.FLANGE_NEG_OUTER
            if sign < 0
            else MemberProfileSurfaceId.FLANGE_POS_OUTER
        )
        if profile.family is MemberProfileFamily.WIDE_FLANGE_I
        else (MemberProfileSurfaceId.Z_NEG_FACE if sign < 0 else MemberProfileSurfaceId.Z_POS_FACE)
    )
    return resolve_profile_wall_bolt_path(
        replace(profile, selected_surface=sid),
        ExactProfileVector3D(
            u,
            offset,
            sign
            * cast(
                WideFlangeIProfileDimensions | RectangularHollowProfileDimensions,
                profile.dimensions,
            ).depth
            / 2,
        ),
        radius,
    ).valid


def _chord_hole(
    profile: MemberProfile,
    point: Rational3,
    sign: int,
    radius: Decimal,
) -> bool:
    return resolve_profile_wall_bolt_path(
        profile,
        ExactProfileVector3D(exact_decimal(point[0]), D(0), sign * exact_decimal(point[2])),
        radius,
    ).valid


def _shaft(
    value: DCTNRequest,
    member: DCTNMember,
    row: int,
    side: str,
    negative: Rational3,
    positive: Rational3,
    core: FullThroughBoltPath | None,
) -> DCTNShaft:
    unit = value.length_unit
    tw = value.channel.web_thickness.to(unit).magnitude
    depth = member.section.depth.to(unit).magnitude
    wall = member.section.wall_or_web.to(unit).magnitude
    flange = member.section.flange_thickness.to(unit).magnitude
    bolt_id = f"{member.slot}:ROW_{row}:{side}"
    owners: tuple[str, ...]
    lengths: tuple[Decimal, ...]
    if side == "THROUGH":
        start = negative[0], negative[1] - F(tw), negative[2]
        end = positive[0], positive[1] + F(tw), positive[2]
        if member.section.form is DCTNForm.RHS:
            owners = (
                "CHORD_NEG:WEB",
                f"{member.slot}:NEAR_WALL",
                f"{member.slot}:FAR_WALL",
                "CHORD_POS:WEB",
            )
            lengths, free = (tw, wall, wall, tw), depth - 2 * wall
        else:
            owners = ("CHORD_NEG:WEB", f"{member.slot}:FULL_SOLID", "CHORD_POS:WEB")
            lengths, free = (tw, depth, tw), D(0)
        sign = 1
    else:
        sign = 1 if side == "NEG" else -1
        point = negative if side == "NEG" else positive
        start = point[0], point[1] - sign * F(tw), point[2]
        end = point[0], point[1] + sign * F(flange), point[2]
        owners = (f"CHORD_{side}:WEB", f"{member.slot}:FLANGE_{side}")
        lengths, free = (tw, flange), D(0)
    hardware = value.fastener.hardware
    radius = hardware.washer_diameter.to(unit).magnitude / 2
    washer = hardware.washer_thickness.to(unit).magnitude
    head = washer + hardware.head_height.to(unit).magnitude
    nut = (
        washer + hardware.nut_height.to(unit).magnitude + hardware.end_extension.to(unit).magnitude
    )
    # An enclosing square aligned with the incoming face frame still contains the
    # complete circular washer and both hexagons; no fictitious global-square corner
    # is allowed to redefine native circular root/edge containment.
    envelope_axis = Vector3D(*(float(x) for x in member.derived_direction))
    return DCTNShaft(
        bolt_id,
        member.slot,
        row,
        side,
        start,
        end,
        owners,
        lengths,
        free,
        core,
        _envelope(bolt_id + ":HEAD", start, head, radius, -sign, envelope_axis),
        _envelope(bolt_id + ":NUT", end, nut, radius, sign, envelope_axis),
    )


def build_dctn_geometry(value: DCTNRequest) -> DCTNGeometry:
    unit = value.length_unit
    reasons: list[str] = []
    gap = value.members[0].section.depth.to(unit).magnitude
    if any(m.section.depth.to(unit).magnitude != gap for m in value.members):
        reasons.append("DCTN_COMMON_GAP_MISMATCH")
    by_slot = {m.slot: m for m in value.members}
    if (
        "D1" in by_slot
        and "D2" in by_slot
        and (by_slot["D1"].section.linked_section() != by_slot["D2"].section.linked_section())
    ):
        reasons.append("DCTN_DIAGONAL_SECTION_LINK_MISMATCH")
    chord_length = F(value.channel.length.to(unit).magnitude)
    chords = tuple(
        placed(
            value.channel.profile("CHORD_NEG" if sign < 0 else "CHORD_POS", unit),
            (-chord_length / 2, sign * F(gap) / 2, ZERO),
            (chord_length / 2, sign * F(gap) / 2, ZERO),
            Vector3D(0, 0, sign),
        )
        for sign in (-1, 1)
    )
    incoming = []
    for member in value.members:
        start: Rational3 = tuple(F(q.to(unit).magnitude) for q in member.start)  # type: ignore[assignment]
        length = F(member.section.length.to(unit).magnitude)
        # Native placement is the sole frame-normalization authority.
        direction = Vector3D(*(float(x) for x in member.derived_direction)).normalized()
        end = (
            start[0] + length * F(str(direction.x)),
            start[1] + length * F(str(direction.y)),
            start[2] + length * F(str(direction.z)),
        )
        incoming.append(
            placed(member.section.profile(member.slot, unit), start, end, Vector3D(0, 1, 0))
        )
        if start[1] != 0:
            reasons.append("DCTN_CHANNEL_SYMMETRY_RESPONSE_NOT_QUALIFIED")
    all_members = (*chords, *incoming)
    collision_members = {
        member.physical_id: _collision_elements(member.placement) for member in all_members
    }
    for left, right in combinations(all_members, 2):
        if _overlap(collision_members[left.physical_id], collision_members[right.physical_id]):
            reasons.append(
                f"DCTN_INVALID_GEOMETRY:MEMBER_INTERFERENCE:{left.physical_id}:{right.physical_id}"
            )
    holes: list[DCTNHole] = []
    rows: list[DCTNRowGeometry] = []
    shafts: list[DCTNShaft] = []
    radius = value.fastener.hole_diameter.to(unit).magnitude / 2
    hardware = value.fastener.hardware
    footprint = hardware.washer_diameter.to(unit).magnitude / 2
    # The native hardware preset requires both hexagons to fit within this enclosing disk.
    if any(
        q.to(unit).magnitude ** 2 > 3 * footprint**2
        for q in (
            hardware.head_across_flats,
            hardware.nut_across_flats,
        )
    ):
        reasons.append("DCTN_INVALID_GEOMETRY:HEAD_NUT_EXCEED_WASHER_ENVELOPE")
    for member, native in zip(value.members, incoming, strict=True):
        pattern = member.pattern
        if pattern.across != 1:
            reasons.append("DCTN_BOLTS_ACROSS_ROW_OUTSIDE_RC1_SCOPE")
            continue
        if pattern.rows not in (1, 2, 3):
            reasons.append("DCTN_ROW_COUNT_OUTSIDE_RC1_SCOPE")
            continue
        if pattern.staggered:
            reasons.append("DCTN_STAGGERED_BOLTS_NOT_SUPPORTED_IN_RC1")
        for row in range(1, pattern.rows + 1):
            u = (
                pattern.first_from_start.to(unit).magnitude
                + (row - 1) * pattern.pitch.to(unit).magnitude
            )
            offset = (
                pattern.wi_offset.to(unit).magnitude
                if member.section.form is DCTNForm.W_I
                else D(0)
            )
            axis = local_point(native, F(u), ZERO, ZERO)
            negative = local_point(native, F(u), -F(offset), -F(gap) / 2)
            positive = local_point(native, F(u), F(offset), F(gap) / 2)
            core = None
            if member.section.form is not DCTNForm.W_I:
                builder = (
                    build_rhs_full_through_core
                    if member.section.form is DCTNForm.RHS
                    else build_srs_full_through_core
                )
                core = builder(
                    native.profile,
                    MemberProfileSurfaceId.Z_NEG_FACE,
                    bolt_id=f"{member.slot}:ROW_{row}:THROUGH",
                    local_uv=(u - native.profile.dimensions.member_length / 2, D(0)),
                    material_region_id=member.slot,
                )
            sides = ("NEG", "POS") if core is None else ("THROUGH",)
            new_shafts = tuple(
                _shaft(value, member, row, side, negative, positive, core) for side in sides
            )
            shafts.extend(new_shafts)
            rows.append(
                DCTNRowGeometry(
                    member.slot,
                    row,
                    u,
                    axis,
                    negative,
                    positive,
                    tuple(s.bolt_id for s in new_shafts),
                )
            )
            for sign, point, chord in zip((-1, 1), (negative, positive), chords, strict=True):
                side = "NEG" if sign < 0 else "POS"
                shaft_id = f"{member.slot}:ROW_{row}:{side if core is None else 'THROUGH'}"
                local_u = u - native.profile.dimensions.member_length / 2
                for owner, surface, hole_ok, hardware_ok in (
                    (
                        member.slot,
                        f"{side}_MEMBER_FACE",
                        _member_hole(native.profile, local_u, sign * offset, sign, radius),
                        _member_hole(native.profile, local_u, sign * offset, sign, footprint),
                    ),
                    (
                        chord.physical_id,
                        "WEB_OUTER",
                        _chord_hole(chord.profile, point, sign, radius),
                        _chord_hole(chord.profile, point, sign, footprint),
                    ),
                ):
                    identity = f"{shaft_id}:{owner}:{surface}"
                    holes.append(
                        DCTNHole(
                            identity,
                            f"{member.slot}:{side}",
                            owner,
                            shaft_id,
                            surface,
                            point,
                            hole_ok,
                            hardware_ok,
                        )
                    )
                    if not hole_ok or not hardware_ok:
                        reasons.append(
                            f"DCTN_INVALID_GEOMETRY:HOLE_OR_HARDWARE_CONTAINMENT:{identity}"
                        )
    for shaft in shafts:
        for other in incoming:
            if other.physical_id != shaft.member_id and any(
                _shaft_intersects_element(
                    shaft, element, value.fastener.diameter.to(unit).magnitude / 2
                )
                for element in collision_members[other.physical_id]
            ):
                reasons.append(
                    "DCTN_INVALID_GEOMETRY:UNINTENDED_SHAFT_LAYER:"
                    f"{shaft.bolt_id}:{other.physical_id}"
                )
        for envelope in (shaft.head_envelope, shaft.nut_envelope):
            for placed_member in all_members:
                if _overlap(
                    envelope.physical_elements, collision_members[placed_member.physical_id]
                ):
                    reasons.append(
                        "DCTN_INVALID_GEOMETRY:HARDWARE_MEMBER_INTERFERENCE:"
                        f"{shaft.bolt_id}:{placed_member.physical_id}"
                    )
    for left_shaft, right_shaft in combinations(shafts, 2):
        if any(
            _overlap(a.physical_elements, b.physical_elements)
            for a in (left_shaft.head_envelope, left_shaft.nut_envelope)
            for b in (right_shaft.head_envelope, right_shaft.nut_envelope)
        ):
            reasons.append(
                "DCTN_INVALID_GEOMETRY:CROSS_GROUP_HARDWARE_INTERFERENCE:"
                f"{left_shaft.bolt_id}:{right_shaft.bolt_id}"
            )
    unique = tuple(dict.fromkeys(reasons))
    return DCTNGeometry(
        "INVALID_GEOMETRY" if unique else "VALID",
        unique,
        unit,
        gap,
        all_members,
        tuple(rows),
        tuple(holes),
        tuple(shafts),
        dctn_fingerprint((value, all_members, rows, holes, shafts, unique)),
    )
