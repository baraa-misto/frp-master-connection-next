"""Dormant Stage 3.3C1 shared supporting-member target architecture.

The registry describes physical targets only.  It intentionally does not expand any
production connection-family selector; later controlled stages own that integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.domain.member_profile import (
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
)
from frp_master_connection.domain.validation import require_enum, require_tuple
from frp_master_connection.domain.values import MemberRole


class SharedSupportTargetId(StrEnum):
    """Exactly the seven owner-confirmed shared target identities."""

    W_COLUMN_FLANGE = "W_COLUMN_FLANGE"
    W_BEAM_FLANGE = "W_BEAM_FLANGE"
    W_COLUMN_WEB = "W_COLUMN_WEB"
    CHANNEL_COLUMN_WEB = "CHANNEL_COLUMN_WEB"
    ANGLE_COLUMN_LEG = "ANGLE_COLUMN_LEG"
    RECTANGULAR_HOLLOW_COLUMN_WALL = "RECTANGULAR_HOLLOW_COLUMN_WALL"
    SOLID_RECTANGULAR_COLUMN_FACE = "SOLID_RECTANGULAR_COLUMN_FACE"


class SupportPhysicalRegion(StrEnum):
    FLANGE = "FLANGE"
    WEB = "WEB"
    ANGLE_LEG = "ANGLE_LEG"
    RECTANGULAR_WALL = "RECTANGULAR_WALL"
    SOLID_RECTANGULAR_VOLUME = "SOLID_RECTANGULAR_VOLUME"


class SupportSurfaceClass(StrEnum):
    W_FLANGE_OUTER_BROAD = "W_FLANGE_OUTER_BROAD"
    W_WEB_BROAD = "W_WEB_BROAD"
    CHANNEL_WEB_OUTER_BROAD = "CHANNEL_WEB_OUTER_BROAD"
    ANGLE_LEG_OUTER_BROAD = "ANGLE_LEG_OUTER_BROAD"
    RECTANGULAR_EXTERIOR_WALL = "RECTANGULAR_EXTERIOR_WALL"
    SOLID_RECTANGULAR_EXTERIOR_FACE = "SOLID_RECTANGULAR_EXTERIOR_FACE"


class OppositeSurfaceBehavior(StrEnum):
    SINGLE_MATERIAL_LAYER = "SINGLE_MATERIAL_LAYER_TO_OPPOSING_BROAD_FACE"
    RECTANGULAR_FULL_THROUGH = "RECTANGULAR_FULL_THROUGH_TO_OPPOSITE_EXTERIOR_FACE"


class SupportBoltPathClass(StrEnum):
    W_FLANGE_LAYER = "W_FLANGE_LAYER"
    W_WEB_LAYER = "W_WEB_LAYER"
    CHANNEL_WEB_LAYER = "CHANNEL_WEB_LAYER"
    ANGLE_LEG_LAYER = "ANGLE_LEG_LAYER"
    RHS_FULL_THROUGH = "RHS_FULL_THROUGH"
    SRS_FULL_THROUGH = "SRS_FULL_THROUGH"


class SupportAccessQualification(StrEnum):
    EXISTING_W_FLANGE_ACCESS = "EXISTING_W_FLANGE_ACCESS"
    OPEN_SECTION_EXTERNAL_ACCESS = "OPEN_SECTION_EXTERNAL_ACCESS"
    EXTERNAL_BOTH_ENDS_REQUIRED = "EXTERNAL_BOTH_ENDS_REQUIRED"


class FiniteBoundaryValidatorId(StrEnum):
    W_FLANGE_OUTER_BOUNDS = "W_FLANGE_OUTER_BOUNDS"
    W_CLEAR_WEB_BOUNDS = "W_CLEAR_WEB_BOUNDS"
    CHANNEL_CLEAR_WEB_BOUNDS = "CHANNEL_CLEAR_WEB_BOUNDS"
    ANGLE_EXPOSED_LEG_R7 = "ANGLE_EXPOSED_LEG_R7"
    RHS_BOTH_WALLS_R8 = "RHS_BOTH_WALLS_R8"
    SRS_BOTH_FACES = "SRS_BOTH_FACES"


@dataclass(frozen=True, slots=True)
class SharedSupportTarget:
    """One immutable physical-target descriptor for future family integration."""

    target_id: SharedSupportTargetId
    support_role: MemberRole
    profile_family: MemberProfileFamily
    physical_region: SupportPhysicalRegion
    surface_class: SupportSurfaceClass
    selectable_surface_ids: tuple[MemberProfileSurfaceId, ...]
    opposite_surface_behavior: OppositeSurfaceBehavior
    bolt_path_class: SupportBoltPathClass
    access_qualification: SupportAccessQualification
    finite_boundary_validator_id: FiniteBoundaryValidatorId

    def __post_init__(self) -> None:
        require_enum(self.target_id, SharedSupportTargetId, "SharedSupportTarget.target_id")
        require_enum(self.support_role, MemberRole, "SharedSupportTarget.support_role")
        if self.support_role not in {MemberRole.COLUMN, MemberRole.BEAM}:
            raise ValueError("A shared supporting-member target must be a column or beam.")
        require_enum(self.profile_family, MemberProfileFamily, "SharedSupportTarget.profile_family")
        require_enum(self.physical_region, SupportPhysicalRegion, "physical_region")
        require_enum(self.surface_class, SupportSurfaceClass, "surface_class")
        require_tuple(self.selectable_surface_ids, "selectable_surface_ids")
        if not self.selectable_surface_ids:
            raise ValueError("A shared support target requires at least one selectable surface.")
        if any(
            not isinstance(item, MemberProfileSurfaceId) for item in self.selectable_surface_ids
        ):
            raise TypeError("Selectable support surfaces must be MemberProfileSurfaceId values.")
        if len(set(self.selectable_surface_ids)) != len(self.selectable_surface_ids):
            raise ValueError("Selectable support surface IDs must be unique.")
        require_enum(
            self.opposite_surface_behavior,
            OppositeSurfaceBehavior,
            "opposite_surface_behavior",
        )
        require_enum(self.bolt_path_class, SupportBoltPathClass, "bolt_path_class")
        require_enum(
            self.access_qualification,
            SupportAccessQualification,
            "access_qualification",
        )
        require_enum(
            self.finite_boundary_validator_id,
            FiniteBoundaryValidatorId,
            "finite_boundary_validator_id",
        )


@dataclass(frozen=True, slots=True)
class SharedSupportSelection:
    """One target/profile pair consumed unchanged by every integrated family."""

    target_id: SharedSupportTargetId
    profile: MemberProfile

    def __post_init__(self) -> None:
        require_enum(self.target_id, SharedSupportTargetId, "target_id")
        if not isinstance(self.profile, MemberProfile):
            raise TypeError("profile must be a MemberProfile.")
        target = shared_support_target(self.target_id)
        if self.profile.member_id not in {"tee-support", "clip-angle-support"}:
            raise ValueError("A shared support profile must own an integrated support member.")
        if self.profile.role is not target.support_role:
            raise ValueError("Support profile role is inconsistent with the selected target.")
        if self.profile.family is not target.profile_family:
            raise ValueError("Support profile family is inconsistent with the selected target.")
        if self.profile.selected_surface not in target.selectable_surface_ids:
            raise ValueError("Support surface is inconsistent with the selected target.")


_FLANGES = (
    MemberProfileSurfaceId.FLANGE_POS_OUTER,
    MemberProfileSurfaceId.FLANGE_NEG_OUTER,
)
_W_WEBS = (MemberProfileSurfaceId.WEB_POS_FACE, MemberProfileSurfaceId.WEB_NEG_FACE)
_ANGLE_LEGS = (MemberProfileSurfaceId.LEG_Y_OUTER, MemberProfileSurfaceId.LEG_Z_OUTER)
_RECTANGULAR_FACES = (
    MemberProfileSurfaceId.Y_POS_FACE,
    MemberProfileSurfaceId.Y_NEG_FACE,
    MemberProfileSurfaceId.Z_POS_FACE,
    MemberProfileSurfaceId.Z_NEG_FACE,
)


SHARED_SUPPORT_TARGET_REGISTRY = (
    SharedSupportTarget(
        SharedSupportTargetId.W_COLUMN_FLANGE,
        MemberRole.COLUMN,
        MemberProfileFamily.WIDE_FLANGE_I,
        SupportPhysicalRegion.FLANGE,
        SupportSurfaceClass.W_FLANGE_OUTER_BROAD,
        _FLANGES,
        OppositeSurfaceBehavior.SINGLE_MATERIAL_LAYER,
        SupportBoltPathClass.W_FLANGE_LAYER,
        SupportAccessQualification.EXISTING_W_FLANGE_ACCESS,
        FiniteBoundaryValidatorId.W_FLANGE_OUTER_BOUNDS,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.W_BEAM_FLANGE,
        MemberRole.BEAM,
        MemberProfileFamily.WIDE_FLANGE_I,
        SupportPhysicalRegion.FLANGE,
        SupportSurfaceClass.W_FLANGE_OUTER_BROAD,
        _FLANGES,
        OppositeSurfaceBehavior.SINGLE_MATERIAL_LAYER,
        SupportBoltPathClass.W_FLANGE_LAYER,
        SupportAccessQualification.EXISTING_W_FLANGE_ACCESS,
        FiniteBoundaryValidatorId.W_FLANGE_OUTER_BOUNDS,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.W_COLUMN_WEB,
        MemberRole.COLUMN,
        MemberProfileFamily.WIDE_FLANGE_I,
        SupportPhysicalRegion.WEB,
        SupportSurfaceClass.W_WEB_BROAD,
        _W_WEBS,
        OppositeSurfaceBehavior.SINGLE_MATERIAL_LAYER,
        SupportBoltPathClass.W_WEB_LAYER,
        SupportAccessQualification.OPEN_SECTION_EXTERNAL_ACCESS,
        FiniteBoundaryValidatorId.W_CLEAR_WEB_BOUNDS,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.CHANNEL_COLUMN_WEB,
        MemberRole.COLUMN,
        MemberProfileFamily.CHANNEL,
        SupportPhysicalRegion.WEB,
        SupportSurfaceClass.CHANNEL_WEB_OUTER_BROAD,
        (MemberProfileSurfaceId.WEB_OUTER,),
        OppositeSurfaceBehavior.SINGLE_MATERIAL_LAYER,
        SupportBoltPathClass.CHANNEL_WEB_LAYER,
        SupportAccessQualification.OPEN_SECTION_EXTERNAL_ACCESS,
        FiniteBoundaryValidatorId.CHANNEL_CLEAR_WEB_BOUNDS,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.ANGLE_COLUMN_LEG,
        MemberRole.COLUMN,
        MemberProfileFamily.ANGLE,
        SupportPhysicalRegion.ANGLE_LEG,
        SupportSurfaceClass.ANGLE_LEG_OUTER_BROAD,
        _ANGLE_LEGS,
        OppositeSurfaceBehavior.SINGLE_MATERIAL_LAYER,
        SupportBoltPathClass.ANGLE_LEG_LAYER,
        SupportAccessQualification.OPEN_SECTION_EXTERNAL_ACCESS,
        FiniteBoundaryValidatorId.ANGLE_EXPOSED_LEG_R7,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.RECTANGULAR_HOLLOW_COLUMN_WALL,
        MemberRole.COLUMN,
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        SupportPhysicalRegion.RECTANGULAR_WALL,
        SupportSurfaceClass.RECTANGULAR_EXTERIOR_WALL,
        _RECTANGULAR_FACES,
        OppositeSurfaceBehavior.RECTANGULAR_FULL_THROUGH,
        SupportBoltPathClass.RHS_FULL_THROUGH,
        SupportAccessQualification.EXTERNAL_BOTH_ENDS_REQUIRED,
        FiniteBoundaryValidatorId.RHS_BOTH_WALLS_R8,
    ),
    SharedSupportTarget(
        SharedSupportTargetId.SOLID_RECTANGULAR_COLUMN_FACE,
        MemberRole.COLUMN,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
        SupportPhysicalRegion.SOLID_RECTANGULAR_VOLUME,
        SupportSurfaceClass.SOLID_RECTANGULAR_EXTERIOR_FACE,
        _RECTANGULAR_FACES,
        OppositeSurfaceBehavior.RECTANGULAR_FULL_THROUGH,
        SupportBoltPathClass.SRS_FULL_THROUGH,
        SupportAccessQualification.EXTERNAL_BOTH_ENDS_REQUIRED,
        FiniteBoundaryValidatorId.SRS_BOTH_FACES,
    ),
)


def shared_support_target_registry() -> tuple[SharedSupportTarget, ...]:
    """Return the immutable seven-entry registry without enabling UI options."""

    return SHARED_SUPPORT_TARGET_REGISTRY


def shared_support_target(target_id: SharedSupportTargetId) -> SharedSupportTarget:
    """Resolve one exact target identity without aliases or family fallbacks."""

    require_enum(target_id, SharedSupportTargetId, "target_id")
    return next(item for item in SHARED_SUPPORT_TARGET_REGISTRY if item.target_id is target_id)


__all__ = (
    "SHARED_SUPPORT_TARGET_REGISTRY",
    "FiniteBoundaryValidatorId",
    "OppositeSurfaceBehavior",
    "SharedSupportSelection",
    "SharedSupportTarget",
    "SharedSupportTargetId",
    "SupportAccessQualification",
    "SupportBoltPathClass",
    "SupportPhysicalRegion",
    "SupportSurfaceClass",
    "shared_support_target",
    "shared_support_target_registry",
)
