"""Stage 3.2 contracts for the reusable two-interface FRP Tee assembly.

The values here are engineering inputs, not renderer dimensions.  Decimal values
are expressed in the request's declared source-length unit and remain exact until
the existing geometry kernel boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TeeSupportRole(StrEnum):
    """Supported W-shape role; both values reuse the same Tee implementation."""

    COLUMN = "COLUMN"
    BEAM = "BEAM"


class SelectedSupportFlange(StrEnum):
    """Explicit physical W-shape flange selected for the Tee contact."""

    POSITIVE_LOCAL_Z = "POSITIVE_LOCAL_Z"
    NEGATIVE_LOCAL_Z = "NEGATIVE_LOCAL_Z"


class TeeInterfaceIdentity(StrEnum):
    """Stable identities for the two real bolted transfer interfaces."""

    BRACE_TO_STEM = "TEE_INTERFACE_A_BRACE_TO_STEM"
    FLANGE_TO_SUPPORT = "TEE_INTERFACE_B_FLANGE_TO_SUPPORT"


class TeeBoltPlacementMode(StrEnum):
    """Authoritative in-plane placement representation for one Tee bolt group."""

    EDGE_DISTANCE_CONTROLLED = "EDGE_DISTANCE_CONTROLLED"
    GROUP_OFFSET_CONTROLLED = "GROUP_OFFSET_CONTROLLED"


class TeeConnectorLengthAnchor(StrEnum):
    """Selected exact datum used to edit the finite Tee length."""

    CENTER = "CENTER"
    POSITIVE_L_END = "POSITIVE_L_END"
    NEGATIVE_L_END = "NEGATIVE_L_END"


def _positive_decimal(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite.")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


@dataclass(frozen=True, slots=True)
class TeeConnectorDimensions:
    """Exact physical Tee dimensions in one declared source-length unit."""

    connector_length: Decimal
    flange_width: Decimal
    flange_thickness: Decimal
    stem_depth: Decimal
    stem_thickness: Decimal

    def __post_init__(self) -> None:
        for name in (
            "connector_length",
            "flange_width",
            "flange_thickness",
            "stem_depth",
            "stem_thickness",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        if self.stem_thickness >= self.flange_width:
            raise ValueError("stem_thickness must be less than flange_width.")

    @property
    def overall_depth(self) -> Decimal:
        """Return the standard-section depth without replacing the explicit inputs."""

        return self.flange_thickness + self.stem_depth


@dataclass(frozen=True, slots=True)
class TeeSupportDimensions:
    """Exact W-shape and finite engineering placement dimensions."""

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
            raise ValueError("The support W-shape requires positive clear web depth.")
        if self.flange_width <= self.web_thickness:
            raise ValueError("The support flange must be wider than its web.")


@dataclass(frozen=True, slots=True)
class TeeBraceDimensions:
    """Connected FRP plate dimensions used by the controlled vertical slice."""

    width: Decimal
    thickness: Decimal
    view_length: Decimal

    def __post_init__(self) -> None:
        for name in ("width", "thickness", "view_length"):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class TeeBoltLayout:
    """One independent rectangular layout and its physical edge distances."""

    row_count: int
    bolts_per_row: int
    pitch: Decimal
    gauge: Decimal
    unloaded_end_distance: Decimal
    loaded_end_distance: Decimal
    negative_side_distance: Decimal
    positive_side_distance: Decimal
    placement_mode: TeeBoltPlacementMode = TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
    vertical_offset: Decimal | None = None
    horizontal_offset: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("row_count", "bolts_per_row"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive non-Boolean integer.")
        for name in (
            "pitch",
            "gauge",
            "unloaded_end_distance",
            "loaded_end_distance",
            "negative_side_distance",
            "positive_side_distance",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        if not isinstance(self.placement_mode, TeeBoltPlacementMode):
            raise TypeError("placement_mode must be a TeeBoltPlacementMode.")
        offsets = (self.vertical_offset, self.horizontal_offset)
        if self.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED:
            if any(value is not None for value in offsets):
                raise ValueError("Edge-distance placement forbids group offsets.")
        elif any(value is None for value in offsets):
            raise ValueError("Group-offset placement requires vertical and horizontal offsets.")
        else:
            for name in ("vertical_offset", "horizontal_offset"):
                value = getattr(self, name)
                if not isinstance(value, Decimal):
                    raise TypeError(f"{name} must be a Decimal in group-offset mode.")
                if not value.is_finite():
                    raise ValueError(f"{name} must be finite.")

    @property
    def row_span(self) -> Decimal:
        return Decimal(self.row_count - 1) * self.pitch

    @property
    def line_span(self) -> Decimal:
        return Decimal(self.bolts_per_row - 1) * self.gauge

    @property
    def required_row_extent(self) -> Decimal:
        return self.unloaded_end_distance + self.row_span + self.loaded_end_distance

    @property
    def required_line_extent(self) -> Decimal:
        return self.negative_side_distance + self.line_span + self.positive_side_distance


__all__ = (
    "SelectedSupportFlange",
    "TeeBoltLayout",
    "TeeBoltPlacementMode",
    "TeeBraceDimensions",
    "TeeConnectorDimensions",
    "TeeConnectorLengthAnchor",
    "TeeInterfaceIdentity",
    "TeeSupportDimensions",
    "TeeSupportRole",
)
