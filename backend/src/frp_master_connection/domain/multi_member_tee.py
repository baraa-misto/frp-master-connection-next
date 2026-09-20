"""Immutable Stage 3.4A Multi-Member Tee slot contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.domain.member_profile import MemberProfile, MemberProfileFamily
from frp_master_connection.domain.tee_connector import TeeBoltLayout


class MultiMemberTeeSlotId(StrEnum):
    """Stable semantic identities ordered from top to bottom on the Tee stem."""

    UPPER_BRACE = "UPPER_BRACE"
    MIDDLE_BEAM = "MIDDLE_BEAM"
    LOWER_BRACE = "LOWER_BRACE"


class MultiMemberTeeConnectedRole(StrEnum):
    BRACE = "BRACE"
    BEAM = "BEAM"


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlot:
    """One active connected-member slot; disabled slots are absent from the aggregate."""

    slot_id: MultiMemberTeeSlotId
    profile: MemberProfile
    inclination_degrees: Decimal
    profile_roll_degrees: Decimal
    anchor_h: Decimal
    anchor_v: Decimal
    bolt_layout: TeeBoltLayout
    trim_enabled: bool = False
    trim_clearance: Decimal | None = None
    expanded_profile_allowed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, MultiMemberTeeSlotId):
            raise TypeError("slot_id must be a MultiMemberTeeSlotId.")
        if not isinstance(self.profile, MemberProfile):
            raise TypeError("profile must be a MemberProfile.")
        for name in (
            "inclination_degrees",
            "profile_roll_degrees",
            "anchor_h",
            "anchor_v",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError(f"{name} must be a finite Decimal.")
        if self.profile_roll_degrees % Decimal(90) != 0:
            raise ValueError("profile_roll_degrees must be an exact quarter turn.")
        if not isinstance(self.bolt_layout, TeeBoltLayout):
            raise TypeError("bolt_layout must be a TeeBoltLayout.")
        if not isinstance(self.trim_enabled, bool):
            raise TypeError("trim_enabled must be Boolean.")
        if not isinstance(self.expanded_profile_allowed, bool):
            raise TypeError("expanded_profile_allowed must be Boolean.")
        if self.trim_enabled:
            if self.trim_clearance is None or self.trim_clearance < 0:
                raise ValueError("An enabled trim requires nonnegative trim_clearance.")
        elif self.trim_clearance is not None:
            raise ValueError("A disabled trim must not retain trim_clearance.")
        if self.slot_id is MultiMemberTeeSlotId.MIDDLE_BEAM:
            if (
                not self.expanded_profile_allowed
                and self.profile.family is not MemberProfileFamily.WIDE_FLANGE_I
            ):
                raise ValueError("MIDDLE_BEAM requires a WIDE_FLANGE_I profile.")
            if self.inclination_degrees != 0:
                raise ValueError("MIDDLE_BEAM inclination must be exactly zero.")
        else:
            if (
                not self.expanded_profile_allowed
                and self.profile.family is not MemberProfileFamily.ANGLE
            ):
                raise ValueError("Brace slots require ANGLE profiles.")
            if self.slot_id is MultiMemberTeeSlotId.UPPER_BRACE and not (
                Decimal(0) <= self.inclination_degrees <= Decimal(90)
            ):
                raise ValueError("UPPER_BRACE inclination must be from 0 through 90 degrees.")
            if self.slot_id is MultiMemberTeeSlotId.LOWER_BRACE and not (
                Decimal(-90) <= self.inclination_degrees <= Decimal(0)
            ):
                raise ValueError("LOWER_BRACE inclination must be from -90 through 0 degrees.")

    @property
    def connected_role(self) -> MultiMemberTeeConnectedRole:
        return (
            MultiMemberTeeConnectedRole.BEAM
            if self.slot_id is MultiMemberTeeSlotId.MIDDLE_BEAM
            else MultiMemberTeeConnectedRole.BRACE
        )


@dataclass(frozen=True, slots=True)
class MultiMemberTeeSlotSet:
    """Validated active-slot aggregate with deterministic semantic ordering."""

    slots: tuple[MultiMemberTeeSlot, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple) or not self.slots:
            raise ValueError("At least one Multi-Member Tee slot must be active.")
        if len(self.slots) > 3 or any(
            not isinstance(item, MultiMemberTeeSlot) for item in self.slots
        ):
            raise TypeError("slots must contain one to three MultiMemberTeeSlot values.")
        order = {
            MultiMemberTeeSlotId.UPPER_BRACE: 0,
            MultiMemberTeeSlotId.MIDDLE_BEAM: 1,
            MultiMemberTeeSlotId.LOWER_BRACE: 2,
        }
        identities = tuple(item.slot_id for item in self.slots)
        if len(set(identities)) != len(identities):
            raise ValueError("Active Multi-Member Tee slot identities must be unique.")
        if tuple(sorted(self.slots, key=lambda item: order[item.slot_id])) != self.slots:
            raise ValueError("Active slots must use Upper, Middle, Lower semantic order.")
        by_id = {item.slot_id: item for item in self.slots}
        upper = by_id.get(MultiMemberTeeSlotId.UPPER_BRACE)
        middle = by_id.get(MultiMemberTeeSlotId.MIDDLE_BEAM)
        lower = by_id.get(MultiMemberTeeSlotId.LOWER_BRACE)
        if upper is not None and middle is not None and upper.anchor_v <= middle.anchor_v:
            raise ValueError("UPPER_BRACE anchor must be above MIDDLE_BEAM anchor.")
        if middle is not None and lower is not None and middle.anchor_v <= lower.anchor_v:
            raise ValueError("MIDDLE_BEAM anchor must be above LOWER_BRACE anchor.")
        if (
            upper is not None
            and middle is None
            and lower is not None
            and upper.anchor_v <= lower.anchor_v
        ):
            raise ValueError("UPPER_BRACE anchor must be above LOWER_BRACE anchor.")


__all__ = (
    "MultiMemberTeeConnectedRole",
    "MultiMemberTeeSlot",
    "MultiMemberTeeSlotId",
    "MultiMemberTeeSlotSet",
)
