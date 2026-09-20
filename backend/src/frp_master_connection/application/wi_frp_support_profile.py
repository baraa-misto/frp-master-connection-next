"""Exact Stage 4.3 placement of the shared receiving-profile/through-bolt contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import cast

from frp_master_connection.application.member_profile_geometry import (
    create_oriented_standard_topology,
)
from frp_master_connection.application.wi_wall_moment_geometry import (
    WallMomentPart,
    _part,
    inch,
    q,
    vector,
)
from frp_master_connection.calculation.angle_connector_core import Decimal3
from frp_master_connection.calculation.channel_moment_resultants import (
    ChannelMomentActionInput,
    ChannelMomentCalculationInput,
    ChannelMomentSectionInput,
    calculate_channel_moment_component_resultants,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain import (
    ChannelProfileDimensions,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ExactProfileVector3D,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    ProfileSurfaceDefinition,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
    profile_surface_registry,
    resolve_profile_surface,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.domain.rectangular_full_through_bolt import (
    FullThroughBoltPath,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    evaluate_full_through_containment,
)
from frp_master_connection.domain.wi_frp_support_moment import ReceivingSupport, SupportMode

D = Decimal
ZERO = D(0)


@dataclass(frozen=True, slots=True)
class SupportPlacement:
    profile: MemberProfile
    surface: ProfileSurfaceDefinition
    selection: ReceivingSupport
    normal_y: Decimal
    normal_z: Decimal
    face_normal_coordinate: Decimal
    centroid: ExactQuantityVector3D
    centroid_authority: str
    parts: tuple[WallMomentPart, ...]

    def direction(self, p: Decimal3) -> Decimal3:
        return (
            self.normal_y * p[1] + self.normal_z * p[2],
            p[0],
            self.normal_z * p[1] - self.normal_y * p[2],
        )

    def point(self, p: Decimal3) -> Decimal3:
        x, y, z = self.direction(p)
        return (
            x - self.face_normal_coordinate,
            y - inch(self.selection.connection_height),
            z - inch(self.selection.connection_transverse),
        )

    def local_point(self, u: Decimal, v: Decimal) -> ExactProfileVector3D:
        transverse = v + inch(self.selection.connection_transverse)
        normal = self.face_normal_coordinate
        return ExactProfileVector3D(
            u + inch(self.selection.connection_height),
            self.normal_y * normal + self.normal_z * transverse,
            self.normal_z * normal - self.normal_y * transverse,
        )


def _profile(s: ReceivingSupport) -> MemberProfile:
    physical, depth, width, tw, tf = (
        inch(x)
        for x in (s.physical_length, s.depth, s.width, s.web_or_wall_thickness, s.flange_thickness)
    )
    dims: MemberProfileDimensions
    if s.mode in {SupportMode.WI_FLANGE, SupportMode.WI_WEB}:
        family, dims = (
            MemberProfileFamily.WIDE_FLANGE_I,
            WideFlangeIProfileDimensions(physical, depth, width, tw, tf),
        )
    elif s.mode is SupportMode.CHANNEL_WEB:
        family, dims = (
            MemberProfileFamily.CHANNEL,
            ChannelProfileDimensions(physical, depth, width, tw, tf),
        )
    elif s.mode is SupportMode.HOLLOW_SQUARE:
        family, dims = (
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            RectangularHollowProfileDimensions(physical, depth, width, tw),
        )
    else:
        family, dims = (
            MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
            SolidRectangularProfileDimensions(physical, depth, width),
        )
    return MemberProfile(
        "STAGE43_SUPPORT_PROFILE",
        "FRP_SUPPORT",
        MemberRole.COLUMN,
        family,
        dims,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "FRP_SUPPORT"),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.WEB_OUTER
        if s.face == "WEB_INNER"
        else MemberProfileSurfaceId(s.face),
    )


def receiving_support_geometry(s: ReceivingSupport) -> SupportPlacement:
    """Place exact native surface-derived slabs, retaining all physical elements."""
    with localcontext() as context:
        context.prec = 100
        profile = _profile(s)
        surface = resolve_profile_surface(profile)
        ny, nz = surface.local_outward_normal.y, surface.local_outward_normal.z
        coordinate = surface.plane_coordinate
        if s.face == "WEB_INNER":
            ny, nz = -ny, -nz
            coordinate = surface.opposite_plane_coordinate
        normal_coordinate = coordinate * (ny if surface.plane_axis is PrincipalAxisFamily.Y else nz)
        temporary = SupportPlacement(
            profile,
            surface,
            s,
            ny,
            nz,
            normal_coordinate,
            vector((ZERO, ZERO, ZERO)),
            "EXACT_NATIVE_PROFILE_SYMMETRY",
            (),
        )
        centroid_y = ZERO
        authority = "EXACT_NATIVE_PROFILE_SYMMETRY"
        if s.mode is SupportMode.CHANNEL_WEB:
            section = calculate_channel_moment_component_resultants(
                ChannelMomentCalculationInput(
                    ChannelMomentSectionInput(
                        s.depth.to(Unit.IN),
                        s.width.to(Unit.IN),
                        s.web_or_wall_thickness.to(Unit.IN),
                        s.flange_thickness.to(Unit.IN),
                    ),
                    ChannelMomentActionInput(
                        q(0, Unit.KIP),
                        q(0, Unit.KIP),
                        q(0, Unit.KIP_IN),
                        q(0, Unit.KIP),
                        q(0, Unit.KIP_IN),
                        q(0, Unit.KIP_IN),
                    ),
                )
            )
            centroid_y = section.section_properties.channel_centroid_t_absolute.magnitude
            authority = "NATIVE_SLICE6_DECIMAL90_CHANNEL_CENTROID_VERBATIM"
        centroid = vector(temporary.point((inch(s.connection_height), centroid_y, ZERO)))
        parts = _surface_solids(temporary)
        return SupportPlacement(
            profile, surface, s, ny, nz, normal_coordinate, centroid, authority, parts
        )


def _surface_solids(placement: SupportPlacement) -> tuple[WallMomentPart, ...]:
    profile = placement.profile
    topology = create_oriented_standard_topology(profile.section_family)
    surfaces = profile_surface_registry(profile)
    if placement.selection.mode is SupportMode.SOLID_SQUARE:
        surfaces = tuple(s for s in surfaces if s.surface_id is MemberProfileSurfaceId.Z_POS_FACE)
    seen: set[PhysicalSectionElementRole] = set()
    parts = []
    for surface in surfaces:
        role = surface.physical_element_role
        if role in seen:
            continue
        seen.add(role)
        bounds = surface.contact_bounds
        if (
            placement.selection.mode is SupportMode.HOLLOW_SQUARE
            and surface.plane_axis is PrincipalAxisFamily.Y
        ) or (
            placement.selection.mode is SupportMode.CHANNEL_WEB
            and role is PhysicalSectionElementRole.WEB
        ):
            bounds = surface.penetration_bounds[
                0
            ]  # Native side walls stop at the top/bottom wall interior.
        lo = [bounds.min_x, bounds.min_y, bounds.min_z]
        hi = [bounds.max_x, bounds.max_y, bounds.max_z]
        axis = 1 if surface.plane_axis is PrincipalAxisFamily.Y else 2
        lo[axis], hi[axis] = sorted((surface.plane_coordinate, surface.opposite_plane_coordinate))
        center = cast(Decimal3, tuple((a + b) / 2 for a, b in zip(lo, hi, strict=True)))
        size = cast(Decimal3, tuple(b - a for a, b in zip(lo, hi, strict=True)))
        element = next(e for e in topology.elements if e.role is role)
        material = next(r for r in topology.material_regions if r.id == element.material_region_id)
        orientation = cast(PlanarFixedMaterialOrientation, material.orientation)

        def basis(axis: PrincipalAxisFamily, sign: int = 1) -> Decimal3:
            return placement.direction(
                cast(
                    Decimal3, tuple(D(sign if item is axis else 0) for item in PrincipalAxisFamily)
                )
            )

        material_axes = (
            basis(PrincipalAxisFamily.X),
            basis(orientation.crosswise_axis, orientation.crosswise_sign),
            basis(orientation.through_thickness_axis, orientation.through_thickness_sign),
        )
        global_size = placement.direction(size)
        parts.append(
            _part(
                f"FRP_SUPPORT_{role.value}",
                "FRP_SUPPORT",
                "SUPPORT",
                placement.point(center),
                cast(Decimal3, tuple(abs(x) for x in global_size)),
                material_axes,
            )
        )
    return tuple(parts)


@dataclass(frozen=True, slots=True)
class SupportCrossing:
    valid: bool
    reason: str
    depth: Decimal
    layer_ids: tuple[str, ...]
    material_thicknesses: tuple[Decimal, ...]
    core_path: FullThroughBoltPath | None
    physical_face: str
    local_point: ExactProfileVector3D


def support_crossing(
    placement: SupportPlacement,
    bolt_id: str,
    u: Decimal,
    v: Decimal,
    footprint_radius: Decimal,
) -> SupportCrossing:
    """Use the accepted complete-disk or full-through engine, never a wall-count heuristic."""
    p = placement.local_point(u, v)
    mode = placement.selection.mode
    if mode in {SupportMode.HOLLOW_SQUARE, SupportMode.SOLID_SQUARE}:
        local_v = p.z if placement.surface.plane_axis is PrincipalAxisFamily.Y else p.y
        core = (
            build_rhs_full_through_core
            if mode is SupportMode.HOLLOW_SQUARE
            else build_srs_full_through_core
        )(
            placement.profile,
            placement.surface.surface_id,
            bolt_id=bolt_id,
            local_uv=(p.x, local_v),
            material_region_id="FRP_SUPPORT",
        )
        containment = evaluate_full_through_containment(
            placement.profile, core.axis, bolt_id=bolt_id, hole_radius=footprint_radius
        )
        return SupportCrossing(
            containment.status.value == "VALID",
            containment.status.value,
            core.shank_length,
            tuple(s.identity for s in core.material_layers),
            tuple(s.length for s in core.material_layers),
            core,
            placement.selection.face,
            p,
        )
    # The native Channel registry exposes its outside web. The inverse uses exactly
    # that same validated footprint and opposing pair, with a distinct physical face.
    native_point = (
        ExactProfileVector3D(p.x, placement.surface.plane_coordinate, p.z)
        if placement.selection.face == "WEB_INNER"
        else p
    )
    path = resolve_profile_wall_bolt_path(placement.profile, native_point, footprint_radius)
    return SupportCrossing(
        path.valid,
        "VALID" if path.reason is None else path.reason.value,
        placement.surface.layer_thickness,
        (placement.surface.physical_element_role.value,),
        (placement.surface.layer_thickness,),
        None,
        placement.selection.face,
        p,
    )
