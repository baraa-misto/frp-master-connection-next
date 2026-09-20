"""Immutable Stage 3.3B contracts for one symmetric paired clip-angle assembly."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PairedClipAngleAssemblyIdentity(StrEnum):
    SYMMETRIC_PAIRED_CLIP_ANGLES = "SYMMETRIC_PAIRED_CLIP_ANGLES"


class PairedClipAngleInstanceIdentity(StrEnum):
    POSITIVE_CLIP_ANGLE = "POSITIVE_CLIP_ANGLE"
    NEGATIVE_CLIP_ANGLE = "NEGATIVE_CLIP_ANGLE"


class PairedClipAngleGroupIdentity(StrEnum):
    COMMON_MEMBER_THROUGH_BOLT_GROUP = "COMMON_MEMBER_THROUGH_BOLT_GROUP"
    POSITIVE_SUPPORT_BOLT_GROUP = "POSITIVE_SUPPORT_BOLT_GROUP"
    NEGATIVE_SUPPORT_BOLT_GROUP = "NEGATIVE_SUPPORT_BOLT_GROUP"


class PairedClipAngleLayerIdentity(StrEnum):
    POSITIVE_CONNECTED_LEG = "POSITIVE_CONNECTED_LEG"
    CONNECTED_MEMBER = "CONNECTED_MEMBER"
    NEGATIVE_CONNECTED_LEG = "NEGATIVE_CONNECTED_LEG"


@dataclass(frozen=True, slots=True)
class PairedClipAngleFrame:
    """The controlled right-handed pair frame and exact symmetry plane."""

    s_axis: tuple[Decimal, Decimal, Decimal] = (Decimal(1), Decimal(0), Decimal(0))
    p_axis: tuple[Decimal, Decimal, Decimal] = (Decimal(0), Decimal(1), Decimal(0))
    l_axis: tuple[Decimal, Decimal, Decimal] = (Decimal(0), Decimal(0), Decimal(1))
    symmetry_plane: str = "S_P = 0"
    handedness: str = "S_P cross P_P = L_P"

    def __post_init__(self) -> None:
        if self.s_axis != (Decimal(1), Decimal(0), Decimal(0)):
            raise ValueError("Stage 3.3B fixes S_P to positive global X.")
        if self.p_axis != (Decimal(0), Decimal(1), Decimal(0)):
            raise ValueError("Stage 3.3B fixes P_P to positive global Y.")
        if self.l_axis != (Decimal(0), Decimal(0), Decimal(1)):
            raise ValueError("Stage 3.3B fixes L_P to positive global Z.")
        if self.symmetry_plane != "S_P = 0" or self.handedness != "S_P cross P_P = L_P":
            raise ValueError("Stage 3.3B requires the controlled pair frame provenance.")


@dataclass(frozen=True, slots=True)
class PairedClipAngleSymmetryProof:
    geometry_proven: bool
    action_proven: bool
    equal_sharing_eligible: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.equal_sharing_eligible != (self.geometry_proven and self.action_proven):
            raise ValueError("Equal sharing requires both geometry and action symmetry.")
        if self.equal_sharing_eligible and self.reasons:
            raise ValueError("A proven symmetry result cannot contain ineligibility reasons.")
        if not self.equal_sharing_eligible and not self.reasons:
            raise ValueError("An unproven symmetry result requires an explicit reason.")


__all__ = (
    "PairedClipAngleAssemblyIdentity",
    "PairedClipAngleFrame",
    "PairedClipAngleGroupIdentity",
    "PairedClipAngleInstanceIdentity",
    "PairedClipAngleLayerIdentity",
    "PairedClipAngleSymmetryProof",
)
