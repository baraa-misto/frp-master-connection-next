"""Pure mapping for the one Stage 3.3C2 supporting-member DTO contract."""

from __future__ import annotations

from decimal import Decimal

from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.api.shared_support_schemas import (
    SharedAngleSupportDTO,
    SharedChannelSupportDTO,
    SharedRectangularHollowSupportDTO,
    SharedSolidRectangularSupportDTO,
    SharedSupportProfileDTO,
    SharedWideFlangeSupportDTO,
)
from frp_master_connection.calculation import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain import (
    AngleProfileDimensions,
    ChannelProfileDimensions,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileSizeBasis,
    PrincipalAxisFamily,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    TeeSupportDimensions,
    WideFlangeIProfileDimensions,
    require_direct_tee_profile_surface,
)


def _length(value: QuantityDTO, unit: Unit) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Support dimensions must be length quantities.")
    result = quantity.to(unit).magnitude
    if result <= 0:
        raise ValueError("Support dimensions must be positive.")
    return result


def map_shared_support_profile(
    value: SharedSupportProfileDTO,
    unit: Unit,
    *,
    member_id: str,
) -> MemberProfile:
    dimensions: MemberProfileDimensions
    if isinstance(value, SharedWideFlangeSupportDTO):
        dimensions = WideFlangeIProfileDimensions(
            _length(value.member_length, unit),
            _length(value.depth, unit),
            _length(value.flange_width, unit),
            _length(value.web_thickness, unit),
            _length(value.flange_thickness, unit),
        )
    elif isinstance(value, SharedChannelSupportDTO):
        dimensions = ChannelProfileDimensions(
            _length(value.member_length, unit),
            _length(value.depth, unit),
            _length(value.flange_width, unit),
            _length(value.web_thickness, unit),
            _length(value.flange_thickness, unit),
        )
    elif isinstance(value, SharedAngleSupportDTO):
        dimensions = AngleProfileDimensions(
            _length(value.member_length, unit),
            _length(value.leg_y, unit),
            _length(value.leg_z, unit),
            _length(value.thickness, unit),
        )
    elif isinstance(value, SharedRectangularHollowSupportDTO):
        dimensions = RectangularHollowProfileDimensions(
            _length(value.member_length, unit),
            _length(value.depth, unit),
            _length(value.width, unit),
            _length(value.wall_thickness, unit),
        )
    elif isinstance(value, SharedSolidRectangularSupportDTO):
        dimensions = SolidRectangularProfileDimensions(
            _length(value.member_length, unit),
            _length(value.depth, unit),
            _length(value.width, unit),
        )
    else:  # pragma: no cover - discriminated union is closed
        raise TypeError("Unsupported shared support profile.")
    return MemberProfile(
        value.profile_id,
        member_id,
        value.role,
        value.profile_family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        value.profile_orientation,
        value.selected_profile_surface,
        MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )


def compatibility_support_dimensions(profile: MemberProfile) -> TeeSupportDimensions:
    """Populate the legacy internal slot without exposing stale W-only transport fields."""

    dimensions = profile.dimensions
    if isinstance(dimensions, WideFlangeIProfileDimensions):
        return TeeSupportDimensions(
            dimensions.member_length,
            dimensions.depth,
            dimensions.flange_width,
            dimensions.web_thickness,
            dimensions.flange_thickness,
        )
    surface = require_direct_tee_profile_surface(profile)
    thickness = surface.layer_thickness
    depth = getattr(dimensions, "depth", getattr(dimensions, "leg_z", Decimal(4) * thickness))
    width = getattr(dimensions, "width", getattr(dimensions, "leg_y", Decimal(4) * thickness))
    return TeeSupportDimensions(
        dimensions.member_length,
        max(depth, Decimal(4) * thickness),
        max(width, Decimal(4) * thickness),
        thickness,
        thickness,
    )


__all__ = ("compatibility_support_dimensions", "map_shared_support_profile")
