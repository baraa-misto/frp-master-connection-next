"""Strict shared Stage 3.3C2 supporting-member transport contract."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StrictStr, field_validator

from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.domain import (
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    SharedSupportTargetId,
)


class _SupportProfileBaseDTO(_StrictModel):
    profile_id: StrictStr
    role: Literal[MemberRole.COLUMN, MemberRole.BEAM]
    profile_orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0

    @field_validator("profile_id")
    @classmethod
    def nonempty_profile_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("profile_id must be nonempty.")
        return value


class SharedWideFlangeSupportDTO(_SupportProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.WIDE_FLANGE_I]
    member_length: QuantityDTO
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    ]


class SharedChannelSupportDTO(_SupportProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.CHANNEL]
    role: Literal[MemberRole.COLUMN]
    member_length: QuantityDTO
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    selected_profile_surface: Literal[MemberProfileSurfaceId.WEB_OUTER]


class SharedAngleSupportDTO(_SupportProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.ANGLE]
    role: Literal[MemberRole.COLUMN]
    member_length: QuantityDTO
    leg_y: QuantityDTO
    leg_z: QuantityDTO
    thickness: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ]


class SharedRectangularHollowSupportDTO(_SupportProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION]
    role: Literal[MemberRole.COLUMN]
    member_length: QuantityDTO
    width: QuantityDTO
    depth: QuantityDTO
    wall_thickness: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class SharedSolidRectangularSupportDTO(_SupportProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.SOLID_RECTANGULAR_SECTION]
    role: Literal[MemberRole.COLUMN]
    member_length: QuantityDTO
    width: QuantityDTO
    depth: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


SharedSupportProfileDTO = Annotated[
    SharedWideFlangeSupportDTO
    | SharedChannelSupportDTO
    | SharedAngleSupportDTO
    | SharedRectangularHollowSupportDTO
    | SharedSolidRectangularSupportDTO,
    Field(discriminator="profile_family"),
]


_TARGET_FAMILY_ROLE = {
    SharedSupportTargetId.W_COLUMN_FLANGE: (
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberRole.COLUMN,
    ),
    SharedSupportTargetId.W_BEAM_FLANGE: (
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberRole.BEAM,
    ),
    SharedSupportTargetId.W_COLUMN_WEB: (
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberRole.COLUMN,
    ),
    SharedSupportTargetId.CHANNEL_COLUMN_WEB: (
        MemberProfileFamily.CHANNEL,
        MemberRole.COLUMN,
    ),
    SharedSupportTargetId.ANGLE_COLUMN_LEG: (
        MemberProfileFamily.ANGLE,
        MemberRole.COLUMN,
    ),
    SharedSupportTargetId.RECTANGULAR_HOLLOW_COLUMN_WALL: (
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberRole.COLUMN,
    ),
    SharedSupportTargetId.SOLID_RECTANGULAR_COLUMN_FACE: (
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
        MemberRole.COLUMN,
    ),
}


def validate_shared_support_pair(
    target_id: SharedSupportTargetId,
    profile: SharedSupportProfileDTO,
) -> None:
    family, role = _TARGET_FAMILY_ROLE[target_id]
    if profile.profile_family is not family or profile.role is not role:
        raise ValueError("support_profile is inconsistent with support_target_id.")
    surface = profile.selected_profile_surface
    if target_id in {
        SharedSupportTargetId.W_COLUMN_FLANGE,
        SharedSupportTargetId.W_BEAM_FLANGE,
    } and surface not in {
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    }:
        raise ValueError("A W-flange target requires a selected exterior flange.")
    if target_id is SharedSupportTargetId.W_COLUMN_WEB and surface not in {
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    }:
        raise ValueError("A W-web target requires a selected web broad face.")


__all__ = (
    "SharedAngleSupportDTO",
    "SharedChannelSupportDTO",
    "SharedRectangularHollowSupportDTO",
    "SharedSolidRectangularSupportDTO",
    "SharedSupportProfileDTO",
    "SharedWideFlangeSupportDTO",
    "validate_shared_support_pair",
)
