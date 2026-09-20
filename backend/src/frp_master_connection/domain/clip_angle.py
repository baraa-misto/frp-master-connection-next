"""Stage 3.3A immutable contracts for one pultruded-FRP clip angle."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ClipAngleHand(StrEnum):
    """The side of the connected member occupied by the single angle."""

    POSITIVE_S_SIDE = "POSITIVE_S_SIDE"
    NEGATIVE_S_SIDE = "NEGATIVE_S_SIDE"

    @property
    def sign(self) -> Decimal:
        return Decimal(1) if self is ClipAngleHand.POSITIVE_S_SIDE else Decimal(-1)


class ClipAngleSupportRole(StrEnum):
    """Supported W/I placement templates."""

    W_COLUMN_FLANGE = "W_COLUMN_FLANGE"
    W_BEAM_FLANGE = "W_BEAM_FLANGE"


class ClipAngleConnectedRole(StrEnum):
    """Connected-member roles authorized by the first vertical slice."""

    BRACE = "BRACE"
    BEAM = "BEAM"


class ClipAngleInterfaceIdentity(StrEnum):
    """Stable identities for the two physical transfer interfaces."""

    CONNECTED_MEMBER_TO_CONNECTED_LEG = "CLIP_ANGLE_INTERFACE_A_CONNECTED_MEMBER_TO_CONNECTED_LEG"
    SUPPORT_LEG_TO_SUPPORT = "CLIP_ANGLE_INTERFACE_B_SUPPORT_LEG_TO_SUPPORT"


class ClipAngleLengthAnchor(StrEnum):
    CENTER = "CENTER"
    POSITIVE_L_END = "POSITIVE_L_END"
    NEGATIVE_L_END = "NEGATIVE_L_END"


class ClipAngleBoltPlacementMode(StrEnum):
    EDGE_DISTANCE_CONTROLLED = "EDGE_DISTANCE_CONTROLLED"
    GROUP_OFFSET_CONTROLLED = "GROUP_OFFSET_CONTROLLED"


def _positive_decimal(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal.")
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero.")
    return value


@dataclass(frozen=True, slots=True)
class ClipAngleDimensions:
    """Exact nominal sharp-corner Angle dimensions in one source unit."""

    connected_leg_width: Decimal
    support_leg_width: Decimal
    thickness: Decimal
    connector_length: Decimal

    def __post_init__(self) -> None:
        for name in (
            "connected_leg_width",
            "support_leg_width",
            "thickness",
            "connector_length",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        if self.thickness >= min(self.connected_leg_width, self.support_leg_width):
            raise ValueError("Clip-angle thickness must be less than both leg widths.")


@dataclass(frozen=True, slots=True)
class ClipAngleSupportDimensions:
    """Exact finite W/I support dimensions used by the connection template."""

    member_length: Decimal
    overall_depth: Decimal
    flange_width: Decimal
    web_thickness: Decimal
    flange_thickness: Decimal

    def __post_init__(self) -> None:
        for name in (
            "member_length",
            "overall_depth",
            "flange_width",
            "web_thickness",
            "flange_thickness",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        if self.overall_depth <= Decimal(2) * self.flange_thickness:
            raise ValueError("The supporting W/I profile requires positive clear web depth.")
        if self.flange_width <= self.web_thickness:
            raise ValueError("The supporting W/I flange must be wider than its web.")


@dataclass(frozen=True, slots=True)
class ClipAngleBoltLayout:
    """One independent fixed rectangular group on one finite Angle leg."""

    row_count: int
    bolts_per_row: int
    pitch: Decimal
    gauge: Decimal
    heel_edge_distance: Decimal
    free_edge_distance: Decimal
    negative_end_distance: Decimal
    positive_end_distance: Decimal
    placement_mode: ClipAngleBoltPlacementMode = ClipAngleBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
    length_offset: Decimal | None = None
    width_offset: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("row_count", "bolts_per_row"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive non-Boolean integer.")
        for name in (
            "pitch",
            "gauge",
            "heel_edge_distance",
            "free_edge_distance",
            "negative_end_distance",
            "positive_end_distance",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        if not isinstance(self.placement_mode, ClipAngleBoltPlacementMode):
            raise TypeError("placement_mode must be a ClipAngleBoltPlacementMode.")
        offsets = (self.length_offset, self.width_offset)
        if self.placement_mode is ClipAngleBoltPlacementMode.EDGE_DISTANCE_CONTROLLED:
            if any(item is not None for item in offsets):
                raise ValueError("Edge-distance placement forbids group offsets.")
        elif any(item is None for item in offsets):
            raise ValueError("Group-offset placement requires length and width offsets.")
        else:
            for name in ("length_offset", "width_offset"):
                value = getattr(self, name)
                if not isinstance(value, Decimal):
                    raise TypeError(f"{name} must be a Decimal.")
                if not value.is_finite():
                    raise ValueError(f"{name} must be finite.")

    @property
    def row_span(self) -> Decimal:
        return Decimal(self.row_count - 1) * self.pitch

    @property
    def line_span(self) -> Decimal:
        return Decimal(self.bolts_per_row - 1) * self.gauge


__all__ = (
    "ClipAngleBoltLayout",
    "ClipAngleBoltPlacementMode",
    "ClipAngleConnectedRole",
    "ClipAngleDimensions",
    "ClipAngleHand",
    "ClipAngleInterfaceIdentity",
    "ClipAngleLengthAnchor",
    "ClipAngleSupportDimensions",
    "ClipAngleSupportRole",
)
