"""Shared exact member-profile geometry adapters for connection applications.

The domain member-profile contract retains authoritative ``Decimal`` dimensions.
This module is the single application boundary that adapts those dimensions to the
existing float geometry kernel.  Connection families own their placement targets;
they do not own separate profile-shape builders.
"""

from __future__ import annotations

from frp_master_connection.domain import (
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    PrincipalAxisFamily,
    SectionFamily,
    SectionTopology,
    create_region_specific_planar_orientations,
    create_standard_section_topology,
    profile_section_geometry_adapter,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import (
    AngleDimensions,
    ChannelDimensions,
    CrossSectionGeometry2D,
    ISectionDimensions,
    PlateDimensions,
    RectangularTubeDimensions,
    UnitVector3D,
    create_angle_geometry,
    create_channel_geometry,
    create_plate_geometry,
    create_rectangular_tube_geometry,
    create_wide_flange_geometry,
)

_SRS_KERNEL_SURFACES = {
    MemberProfileSurfaceId.Y_POS_FACE: "PLATE:POSITIVE_CW_EDGE",
    MemberProfileSurfaceId.Y_NEG_FACE: "PLATE:NEGATIVE_CW_EDGE",
    MemberProfileSurfaceId.Z_POS_FACE: "PLATE:POSITIVE_TT_BROAD",
    MemberProfileSurfaceId.Z_NEG_FACE: "PLATE:NEGATIVE_TT_BROAD",
}


def create_oriented_standard_topology(
    family: SectionFamily,
    lengthwise: PrincipalAxisFamily = PrincipalAxisFamily.X,
) -> SectionTopology:
    """Build the accepted region-specific planar topology for one standard shape."""

    remaining = [item for item in PrincipalAxisFamily if item is not lengthwise]
    orientations = create_region_specific_planar_orientations(
        family,
        remaining[0],
        remaining[1],
    )
    return create_standard_section_topology(family, orientations=orientations)


def create_member_profile_cross_section(
    profile: MemberProfile,
    topology: SectionTopology,
) -> CrossSectionGeometry2D:
    """Call only the existing standard-section builders through the domain adapter."""

    adapter = profile_section_geometry_adapter(profile)
    values = {name: float(value) for name, value in adapter.dimension_values}
    if profile.family is MemberProfileFamily.ANGLE:
        return create_angle_geometry(
            topology,
            AngleDimensions(
                leg_y=values["leg_y"],
                leg_z=values["leg_z"],
                thickness=values["thickness"],
            ),
        )
    if profile.family is MemberProfileFamily.CHANNEL:
        return create_channel_geometry(
            topology,
            ChannelDimensions(
                overall_depth=values["overall_depth"],
                flange_width=values["flange_width"],
                web_thickness=values["web_thickness"],
                flange_thickness=values["flange_thickness"],
            ),
        )
    if profile.family is MemberProfileFamily.WIDE_FLANGE_I:
        return create_wide_flange_geometry(
            topology,
            ISectionDimensions(
                overall_depth=values["overall_depth"],
                flange_width=values["flange_width"],
                web_thickness=values["web_thickness"],
                flange_thickness=values["flange_thickness"],
            ),
        )
    if profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION:
        return create_rectangular_tube_geometry(
            topology,
            RectangularTubeDimensions(
                outside_width=values["outside_width"],
                outside_depth=values["outside_depth"],
                wall_thickness=values["wall_thickness"],
            ),
        )
    if profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        return create_plate_geometry(
            topology,
            PlateDimensions(
                width=values["width"],
                thickness=values["thickness"],
            ),
        )
    if profile.family is MemberProfileFamily.FLAT_PLATE:
        return create_plate_geometry(
            topology,
            PlateDimensions(
                width=values["width"],
                thickness=values["thickness"],
            ),
        )
    raise ValueError("Round hollow profiles have no authorized direct planar interface.")


def resolve_profile_local_z_reference(
    profile: MemberProfile,
    in_plane_up: UnitVector3D,
    contact_transverse: UnitVector3D,
    member_longitudinal: UnitVector3D,
) -> UnitVector3D:
    """Map the selected oriented owner surface to the connection contact normal."""

    selected = require_direct_tee_profile_surface(profile)
    local_ny = float(selected.local_outward_normal.y)
    local_nz = float(selected.local_outward_normal.z)
    base_y = UnitVector3D(
        local_nz * in_plane_up.x - local_ny * contact_transverse.x,
        local_nz * in_plane_up.y - local_ny * contact_transverse.y,
        local_nz * in_plane_up.z - local_ny * contact_transverse.z,
    )
    base_z = UnitVector3D(
        -local_ny * in_plane_up.x - local_nz * contact_transverse.x,
        -local_ny * in_plane_up.y - local_nz * contact_transverse.y,
        -local_ny * in_plane_up.z - local_nz * contact_transverse.z,
    )
    effective_z = (
        base_z,
        UnitVector3D(-base_y.x, -base_y.y, -base_y.z),
        UnitVector3D(-base_z.x, -base_z.y, -base_z.z),
        base_y,
    )[profile.orientation.quarter_turns]
    if abs(member_longitudinal.dot(effective_z)) > 1e-12:
        raise ValueError("Connected-profile orientation did not remain transverse to its member.")
    return effective_z


def kernel_profile_surface_patch_ids(
    profile: MemberProfile,
) -> tuple[str, tuple[str, ...], str]:
    """Adapt profile-surface identity to the shared geometry kernel's physical IDs."""

    selected = require_direct_tee_profile_surface(profile)
    if profile.family is not MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        return (
            selected.outside_patch_id,
            selected.opposing_patch_ids,
            selected.physical_element_id,
        )
    selected_id = profile.selected_surface
    if not isinstance(selected_id, MemberProfileSurfaceId):  # pragma: no cover
        raise TypeError("SRS requires an exact selected exterior face.")
    opposite = {
        MemberProfileSurfaceId.Y_POS_FACE: MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE: MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Z_POS_FACE: MemberProfileSurfaceId.Z_NEG_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE: MemberProfileSurfaceId.Z_POS_FACE,
    }[selected_id]
    return _SRS_KERNEL_SURFACES[selected_id], (_SRS_KERNEL_SURFACES[opposite],), "PLATE"


__all__ = (
    "create_member_profile_cross_section",
    "create_oriented_standard_topology",
    "kernel_profile_surface_patch_ids",
    "resolve_profile_local_z_reference",
)
