"""Stage 4.5 adapter of native physical profiles and R14B material regions."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import cast

from frp_master_connection.application.member_profile_geometry import (
    create_oriented_standard_topology,
)
from frp_master_connection.application.wi_wall_moment_geometry import WallMomentPart, _part, inch
from frp_master_connection.calculation.angle_connector_core import Decimal3
from frp_master_connection.domain.column_moment_base import Face, MomentBaseColumn
from frp_master_connection.domain.member_profile import (
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
    profile_member_axis_reference,
    profile_surface_registry,
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
)

D = Decimal
Z = D(0)
ENGINEERING_HEIGHT = D(8)


def native_column_profile(
    column: MomentBaseColumn, height: Decimal = ENGINEERING_HEIGHT
) -> MemberProfile:
    """Inspection extrusion is fixed: the lower physical end is zero, not view clipping."""
    width, depth = inch(column.width), inch(column.depth)
    dimensions: (
        WideFlangeIProfileDimensions
        | RectangularHollowProfileDimensions
        | SolidRectangularProfileDimensions
    )
    if column.family == "WI":
        family = MemberProfileFamily.WIDE_FLANGE_I
        dimensions = WideFlangeIProfileDimensions(
            height, depth, width, inch(column.web_thickness), inch(column.flange_thickness)
        )
        surface = MemberProfileSurfaceId.WEB_POS_FACE
    elif column.family == "RHS":
        family = MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
        dimensions = RectangularHollowProfileDimensions(
            height, depth, width, inch(column.wall_thickness)
        )
        surface = MemberProfileSurfaceId.Y_POS_FACE
    else:
        family = MemberProfileFamily.SOLID_RECTANGULAR_SECTION
        dimensions = SolidRectangularProfileDimensions(height, depth, width)
        surface = MemberProfileSurfaceId.Y_POS_FACE
    return MemberProfile(
        "STAGE_4_5_COLUMN_PROFILE",
        "COLUMN",
        MemberRole.COLUMN,
        family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "COLUMN"),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        surface,
    )


def surface_id(column: MomentBaseColumn, face: Face) -> MemberProfileSurfaceId:
    if column.family == "WI":
        return {
            "X_POS": MemberProfileSurfaceId.WEB_POS_FACE,
            "X_NEG": MemberProfileSurfaceId.WEB_NEG_FACE,
            "Y_POS": MemberProfileSurfaceId.FLANGE_POS_OUTER,
            "Y_NEG": MemberProfileSurfaceId.FLANGE_NEG_OUTER,
        }[face]
    return {
        "X_POS": MemberProfileSurfaceId.Y_POS_FACE,
        "X_NEG": MemberProfileSurfaceId.Y_NEG_FACE,
        "Y_POS": MemberProfileSurfaceId.Z_POS_FACE,
        "Y_NEG": MemberProfileSurfaceId.Z_NEG_FACE,
    }[face]


def map_vector(values: Decimal3) -> Decimal3:
    """Proper native extrusion/width/depth to global Z/X/Y rotation."""
    return values[1], values[2], values[0]


def column_centroid_in(column: MomentBaseColumn, profile: MemberProfile) -> Decimal3:
    # Preserve this resolver's accepted context; do not change an inherited equation.
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        center = profile_member_axis_reference(profile)
    return (center.y + inch(column.offset_x), center.z + inch(column.offset_y), Z)


def column_parts(
    column: MomentBaseColumn, profile: MemberProfile, height: Decimal = ENGINEERING_HEIGHT
) -> tuple[WallMomentPart, ...]:
    topology = create_oriented_standard_topology(profile.section_family)
    surfaces = profile_surface_registry(profile)
    if column.family == "SRS":
        surfaces = tuple(s for s in surfaces if s.surface_id is MemberProfileSurfaceId.Z_POS_FACE)
    result: list[WallMomentPart] = []
    seen = set()
    for surface in surfaces:
        if surface.physical_element_role in seen:
            continue
        seen.add(surface.physical_element_role)
        bounds = (
            surface.penetration_bounds[0]
            if column.family == "RHS" and surface.plane_axis is PrincipalAxisFamily.Y
            else surface.contact_bounds
        )
        lo = [bounds.min_x, bounds.min_y, bounds.min_z]
        hi = [bounds.max_x, bounds.max_y, bounds.max_z]
        axis_index = 1 if surface.plane_axis is PrincipalAxisFamily.Y else 2
        lo[axis_index], hi[axis_index] = sorted(
            (surface.plane_coordinate, surface.opposite_plane_coordinate)
        )
        center = map_vector(cast(Decimal3, tuple((a + b) / 2 for a, b in zip(lo, hi, strict=True))))
        center = (center[0] + inch(column.offset_x), center[1] + inch(column.offset_y), height / 2)
        size = map_vector(cast(Decimal3, tuple(b - a for a, b in zip(lo, hi, strict=True))))
        size = (size[0], size[1], height)
        element = next(e for e in topology.elements if e.role is surface.physical_element_role)
        region = next(r for r in topology.material_regions if r.id == element.material_region_id)
        orientation = cast(PlanarFixedMaterialOrientation, region.orientation)

        def axis(value: PrincipalAxisFamily, sign: int = 1) -> Decimal3:
            return map_vector(
                cast(Decimal3, tuple(D(sign if a is value else 0) for a in PrincipalAxisFamily))
            )

        axes = (
            axis(PrincipalAxisFamily.X),
            axis(orientation.crosswise_axis, orientation.crosswise_sign),
            axis(orientation.through_thickness_axis, orientation.through_thickness_sign),
        )
        result.append(
            _part(
                "COLUMN_" + surface.physical_element_role.value,
                "COLUMN",
                "MEMBER",
                center,
                size,
                axes,
            )
        )
    return tuple(result)
