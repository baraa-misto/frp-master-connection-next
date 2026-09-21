"""Native Channel/W-I cuts and one R1 polygon; independent physical bolt shafts."""

import math
from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.application.member_profile_geometry import (
    create_member_profile_cross_section,
    create_oriented_standard_topology,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain import AssemblyMember, MemberEnd, PositionVector3D
from frp_master_connection.domain.member_profile import (
    ExactProfileVector3D,
    MemberProfile,
    profile_section_geometry_adapter,
    resolve_profile_surface,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.domain.ssmc import GROUPS, MEMBERS, SSMCRequest
from frp_master_connection.geometry import (
    AuthoritativeCutPlane3D,
    TrimmedComponentSolids3D,
    UnitVector3D,
    Vector3D,
    place_member,
    trim_placed_rectangular_component,
)
from frp_master_connection.geometry.ssmc_paths import (
    CircularHoleLoop,
    PolygonPathLedger,
    discover_polygon_paths,
)
from frp_master_connection.geometry.ssmc_polygon import (
    GEOMETRY_EPSILON,
    MiterPolygon,
    Point2,
    add,
    construct_miter_polygon,
    contains_disk,
    dot,
    scale,
)


@dataclass(frozen=True, slots=True)
class SSMCMemberGeometry:
    owner: str
    profile: MemberProfile
    cut: AuthoritativeCutPlane3D
    trimmed: TrimmedComponentSolids3D
    end_reference: PositionVector3D
    web_reference_y: float
    material_longitudinal: Vector3D
    material_depth: Vector3D


@dataclass(frozen=True, slots=True)
class SSMCShaft:
    id: str
    group: str
    member: str
    row: int
    line: int
    center: Point2
    plate_midpoint: PositionVector3D
    start: PositionVector3D
    end: PositionVector3D
    layer_owners: tuple[str, str]
    hole_radius: float
    hardware_envelope_radius: float
    edge_clearances: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class SSMCGeometry:
    length_unit: Unit
    polygon: MiterPolygon
    plate_side: str
    plate_y_interval: tuple[float, float]
    members: tuple[SSMCMemberGeometry, ...]
    shafts: tuple[SSMCShaft, ...]
    polygon_paths: PolygonPathLedger
    gross_neck_only_not_resistance: bool = True


def geometry_ssmc(request: SSMCRequest) -> SSMCGeometry:
    unit = request.length_unit

    def length(q: PhysicalQuantity) -> float:
        return float(q.to(unit).magnitude)

    plate = request.plate
    if plate.corner_radius.magnitude != 0 or plate.chamfer.magnitude != 0:
        raise ValueError("SSMC_CORNER_TREATMENT_NOT_REPRESENTABLE")
    polygon = construct_miter_polygon(
        float(request.theta_deg),
        length(plate.normal_gap),
        (length(plate.horizontal_depth), length(plate.inclined_depth)),
        (length(plate.horizontal_overlap), length(plate.inclined_overlap)),
    )
    side = 1 if plate.side == "POS_Y" else -1
    thickness = length(plate.thickness)
    hole_radius = length(request.fastener.hole_diameter) / 2
    hardware = request.fastener.hardware
    envelope = max(
        length(hardware.washer_diameter) / 2,
        length(hardware.head_across_flats) / math.sqrt(3),
        length(hardware.nut_across_flats) / math.sqrt(3),
    )
    members: list[SSMCMemberGeometry] = []
    shafts: list[SSMCShaft] = []
    for index, (section, group, branch) in enumerate(
        zip(
            (request.horizontal, request.inclined),
            (request.horizontal_group, request.inclined_group),
            polygon.branches,
            strict=True,
        )
    ):
        owner = MEMBERS[index]
        profile = section.profile(owner, unit)
        surface = resolve_profile_surface(profile)
        adapter = profile_section_geometry_adapter(profile)
        orientation = side * float(surface.local_outward_normal.y)
        axis = (1.0, 0.0) if index == 0 else branch.axis
        depth_axis = (-axis[1], axis[0])
        y_shift = orientation * float(adapter.section_datum_offset_y - surface.plane_coordinate)
        extent = length(section.length)
        topology = create_oriented_standard_topology(profile.section_family)
        member = AssemblyMember(
            id=owner,
            label=owner,
            role=profile.role,
            connected_end=MemberEnd.END if index == 0 else MemberEnd.START,
            section_family=profile.section_family,
            material_kind=profile.material_kind,
            section_topology=topology,
            material_orientation=profile.material_orientation,
        )
        placed = place_member(
            member,
            create_member_profile_cross_section(profile, topology),
            PositionVector3D(-axis[0] * extent / 2, y_shift, -axis[1] * extent / 2),
            PositionVector3D(axis[0] * extent / 2, y_shift, axis[1] * extent / 2),
            Vector3D(orientation * depth_axis[0], 0, orientation * depth_axis[1]),
        )
        sign = -1 if index == 0 else 1
        n = polygon.normal
        cut = AuthoritativeCutPlane3D(
            owner + ":MITER",
            PositionVector3D(n[0] * branch.cut_delta, 0, n[1] * branch.cut_delta),
            UnitVector3D(sign * n[0], 0, sign * n[1]),
        )
        trimmed = trim_placed_rectangular_component(placed, cut)
        web = length(section.web_thickness)
        clear_depth = length(section.depth) - 2 * length(section.flange_thickness)
        if branch.depth > clear_depth:
            raise ValueError("SSMC_MEMBER_OVERLAP_INVALID")
        # Far branch corners must remain on the physical native member surface.
        for point in (*branch.cut_points, *branch.far_points):
            if abs(dot(point, axis)) > extent / 2 + GEOMETRY_EPSILON:
                raise ValueError("SSMC_MEMBER_OVERLAP_INVALID")
        end_station = branch.cut_delta / dot(n, branch.axis)
        end_xz = scale(branch.axis, end_station)
        members.append(
            SSMCMemberGeometry(
                owner,
                profile,
                cut,
                trimmed,
                PositionVector3D(end_xz[0], -side * web / 2, end_xz[1]),
                -side * web / 2,
                Vector3D(axis[0], 0, axis[1]),
                Vector3D(orientation * depth_axis[0], 0, orientation * depth_axis[1]),
            )
        )
        for row in range(group.rows):
            for line in (-1, 1):
                height = length(group.transverse_offset) + line * length(group.gauge) / 2
                cut_station = (branch.cut_delta - height * dot(n, branch.transverse)) / dot(
                    n, branch.axis
                )
                station = cut_station + length(group.first_from_cut) + row * length(group.pitch)
                point = add(scale(branch.axis, station), scale(branch.transverse, height))
                native_point = ExactProfileVector3D(
                    Decimal(str(dot(point, axis))),
                    surface.plane_coordinate,
                    Decimal(str(height / orientation)),
                )
                if not resolve_profile_wall_bolt_path(
                    profile, native_point, Decimal(str(hole_radius))
                ).valid:
                    raise ValueError("SSMC_MEMBER_HOLE_CONTAINMENT_INVALID")
                if not resolve_profile_wall_bolt_path(
                    profile, native_point, Decimal(str(envelope))
                ).valid:
                    raise ValueError("SSMC_MEMBER_HARDWARE_CONTAINMENT_INVALID")
                if sign * (dot(n, point) - branch.cut_delta) < envelope:
                    raise ValueError("SSMC_MITER_HARDWARE_CONTAINMENT_INVALID")
                if not contains_disk(polygon.boundary, point, hole_radius):
                    raise ValueError("SSMC_POLYGON_HOLE_CONTAINMENT_INVALID")
                if not contains_disk(polygon.boundary, point, envelope):
                    raise ValueError("SSMC_POLYGON_HARDWARE_CONTAINMENT_INVALID")
                from frp_master_connection.geometry.ssmc_polygon import distance_squared, pairs

                clearances = tuple(
                    (edge_id, math.sqrt(distance_squared(point, *edge)) - hole_radius)
                    for edge_id, edge in zip(polygon.edge_ids, pairs(polygon.boundary), strict=True)
                )
                shaft_id = GROUPS[index] + f":ROW_{row + 1}:LINE_{line}"
                shafts.append(
                    SSMCShaft(
                        shaft_id,
                        GROUPS[index],
                        owner,
                        row + 1,
                        line,
                        point,
                        PositionVector3D(point[0], side * thickness / 2, point[1]),
                        PositionVector3D(point[0], side * thickness, point[1]),
                        PositionVector3D(point[0], -side * web, point[1]),
                        ("MITER_WEB_PLATE", owner),
                        hole_radius,
                        envelope,
                        clearances,
                    )
                )
    for i, a in enumerate(shafts):
        for b in shafts[i + 1 :]:
            if (
                math.dist(a.center, b.center)
                < a.hardware_envelope_radius + b.hardware_envelope_radius
            ):
                raise ValueError("SSMC_HARDWARE_INTERFERENCE")
    return SSMCGeometry(
        unit,
        polygon,
        plate.side,
        (min(0.0, side * thickness), max(0.0, side * thickness)),
        tuple(members),
        tuple(shafts),
        discover_polygon_paths(
            polygon,
            tuple(CircularHoleLoop(b.id, b.group, b.center, b.hole_radius) for b in shafts),
            tuple((g, tuple(b.id for b in shafts if b.group == g and b.row == 1)) for g in GROUPS),
        ),
    )
