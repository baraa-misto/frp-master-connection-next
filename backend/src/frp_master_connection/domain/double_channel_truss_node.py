"""DCTN-2 RC1 inputs: primary FRP members, independent hardware, no body material."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from typing import cast

from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.member_profile import (
    ChannelProfileDimensions,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
)
from frp_master_connection.domain.section_topology import FRPComponentOrientation
from frp_master_connection.domain.values import (
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    MemberRole,
    PrincipalAxisFamily,
)
from frp_master_connection.domain.wi_frp_support_moment import SupportHardware

PRODUCT = "DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION"
ROUTE = "double-channel-truss-node"
CONTRACT = "DCTN-2-RC1"
ASSEMBLY_METHOD = "DCTN_DOUBLE_CHANNEL_TRUSS_NODE_ASSEMBLY_RC1"
MATERIAL = "ICE_LOCKED_PULTRUDED_FRP"


class DCTNArrangement(StrEnum):
    VERTICAL_ONLY = "VERTICAL_ONLY"
    ONE_INCLINED = "ONE_INCLINED"
    TWO_INCLINED = "TWO_INCLINED"
    VERTICAL_ONE_INCLINED = "VERTICAL_ONE_INCLINED"
    VERTICAL_TWO_INCLINED = "VERTICAL_TWO_INCLINED"


class DCTNForm(StrEnum):
    RHS = "RHS"
    SOLID_RECTANGLE = "SOLID_RECTANGLE"
    W_I = "W_I"


SLOTS = {
    DCTNArrangement.VERTICAL_ONLY: ("V",),
    DCTNArrangement.ONE_INCLINED: ("D1",),
    DCTNArrangement.TWO_INCLINED: ("D1", "D2"),
    DCTNArrangement.VERTICAL_ONE_INCLINED: ("V", "D1"),
    DCTNArrangement.VERTICAL_TWO_INCLINED: ("V", "D1", "D2"),
}


def require_quantity(value: PhysicalQuantity, dimension: Dimension) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not dimension:
        raise ValueError(f"DCTN requires a {dimension.value} quantity")


@dataclass(frozen=True, slots=True)
class DCTNSection:
    form: DCTNForm
    length: PhysicalQuantity
    depth: PhysicalQuantity
    width: PhysicalQuantity
    wall_or_web: PhysicalQuantity
    flange_thickness: PhysicalQuantity

    def __post_init__(self) -> None:
        if not isinstance(self.form, DCTNForm):
            raise ValueError("DCTN requires RHS, SOLID_RECTANGLE or W_I")
        for value in (self.length, self.depth, self.width, self.wall_or_web, self.flange_thickness):
            require_quantity(value, Dimension.LENGTH)
        self.profile("SECTION_VALIDATION", Unit.MM)

    def profile(self, member_id: str, unit: Unit) -> MemberProfile:
        length, depth, width, web, flange = (
            value.to(unit).magnitude
            for value in (
                self.length,
                self.depth,
                self.width,
                self.wall_or_web,
                self.flange_thickness,
            )
        )
        if self.form is DCTNForm.W_I:
            family = MemberProfileFamily.WIDE_FLANGE_I
            dimensions: (
                WideFlangeIProfileDimensions
                | RectangularHollowProfileDimensions
                | SolidRectangularProfileDimensions
            ) = WideFlangeIProfileDimensions(length, depth, width, web, flange)
            surface = MemberProfileSurfaceId.FLANGE_NEG_OUTER
        elif self.form is DCTNForm.RHS:
            family = MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
            dimensions = RectangularHollowProfileDimensions(length, depth, width, web)
            surface = MemberProfileSurfaceId.Z_NEG_FACE
        else:
            family = MemberProfileFamily.SOLID_RECTANGULAR_SECTION
            dimensions = SolidRectangularProfileDimensions(length, depth, width)
            surface = MemberProfileSurfaceId.Z_NEG_FACE
        return make_profile(member_id, family, dimensions, surface)

    def linked_section(self) -> tuple[object, ...]:
        """Complete cross-section, excluding independent physical longitudinal length."""
        dimensions = self.profile("LINK", Unit.MM).dimensions
        if isinstance(dimensions, SolidRectangularProfileDimensions):
            return self.form, dimensions.depth, dimensions.width
        if isinstance(dimensions, RectangularHollowProfileDimensions):
            return self.form, dimensions.depth, dimensions.width, dimensions.wall_thickness
        dimensions = cast(WideFlangeIProfileDimensions, dimensions)
        return (
            self.form,
            dimensions.depth,
            dimensions.flange_width,
            dimensions.web_thickness,
            dimensions.flange_thickness,
        )


def make_profile(
    member_id: str,
    family: MemberProfileFamily,
    dimensions: (
        ChannelProfileDimensions
        | WideFlangeIProfileDimensions
        | RectangularHollowProfileDimensions
        | SolidRectangularProfileDimensions
    ),
    surface: MemberProfileSurfaceId,
) -> MemberProfile:
    return MemberProfile(
        f"{member_id}_PROFILE",
        member_id,
        MemberRole.BRACE,
        family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        surface,
    )


@dataclass(frozen=True, slots=True)
class DCTNChannel:
    length: PhysicalQuantity
    depth: PhysicalQuantity
    flange_width: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    material_source_reference: str = ""
    material_id: str = MATERIAL

    def __post_init__(self) -> None:
        for value in (
            self.length,
            self.depth,
            self.flange_width,
            self.web_thickness,
            self.flange_thickness,
        ):
            require_quantity(value, Dimension.LENGTH)
        if self.material_id != MATERIAL:
            raise ValueError("DCTN primary members remain FRP-only")
        self.profile("CHANNEL_VALIDATION", Unit.MM)

    def profile(self, member_id: str, unit: Unit) -> MemberProfile:
        return make_profile(
            member_id,
            MemberProfileFamily.CHANNEL,
            ChannelProfileDimensions(
                *(
                    value.to(unit).magnitude
                    for value in (
                        self.length,
                        self.depth,
                        self.flange_width,
                        self.web_thickness,
                        self.flange_thickness,
                    )
                )
            ),
            MemberProfileSurfaceId.WEB_OUTER,
        )


@dataclass(frozen=True, slots=True)
class DCTNPattern:
    rows: int
    across: int
    first_from_start: PhysicalQuantity
    pitch: PhysicalQuantity
    wi_offset: PhysicalQuantity
    staggered: bool = False

    def __post_init__(self) -> None:
        for value in (self.first_from_start, self.pitch, self.wi_offset):
            require_quantity(value, Dimension.LENGTH)
        if type(self.rows) is not int or type(self.across) is not int:
            raise ValueError("DCTN row and across counts require integers, not booleans")
        if type(self.staggered) is not bool:
            raise ValueError("DCTN staggered flag requires a boolean")


@dataclass(frozen=True, slots=True)
class DCTNMember:
    slot: str
    section: DCTNSection
    start: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    inclination_deg: Decimal
    axial_force: PhysicalQuantity
    pattern: DCTNPattern
    material_source_reference: str = ""
    local_path_source_reference: str = ""
    material_id: str = MATERIAL

    def __post_init__(self) -> None:
        if self.slot not in {"V", "D1", "D2"} or self.material_id != MATERIAL:
            raise ValueError("DCTN requires canonical V/D1/D2 primary FRP members")
        for value in self.start:
            require_quantity(value, Dimension.LENGTH)
        require_quantity(self.axial_force, Dimension.FORCE)
        if not self.inclination_deg.is_finite():
            raise ValueError("DCTN requires a finite inclination angle")
        if self.slot == "V" and self.inclination_deg != 90:
            raise ValueError("DCTN vertical slot requires exactly 90 degrees")

    @property
    def derived_direction(self) -> tuple[Decimal, Decimal, Decimal]:
        """Backend-owned X-Z direction; semantic cardinals are exact, not rounded."""
        cardinal = {
            Decimal(0): (Decimal(1), Decimal(0), Decimal(0)),
            Decimal(90): (Decimal(0), Decimal(0), Decimal(1)),
            Decimal(180): (Decimal(-1), Decimal(0), Decimal(0)),
            Decimal(270): (Decimal(0), Decimal(0), Decimal(-1)),
        }
        angle = self.inclination_deg % 360
        if angle < 0:
            angle += 360
        if angle in cardinal:
            return cardinal[angle]
        sine, cosine = deterministic_sine_cosine_degrees(self.inclination_deg)
        return Decimal(str(cosine)), Decimal(0), Decimal(str(sine))


@dataclass(frozen=True, slots=True)
class DCTNFastener:
    diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    hardware: SupportHardware
    source_reference: str = ""
    threads_excluded: bool = True
    snug_tight: bool = True
    product_id: str = "ASTM_F593_GROUP2_316"

    def __post_init__(self) -> None:
        require_quantity(self.diameter, Dimension.LENGTH)
        require_quantity(self.hole_diameter, Dimension.LENGTH)
        if min(self.diameter.canonical_magnitude, self.hole_diameter.canonical_magnitude) <= 0:
            raise ValueError("DCTN bolt and hole diameters must be positive")


@dataclass(frozen=True, slots=True)
class DCTNRequest:
    request_id: str
    unit_system: str
    length_unit: Unit
    arrangement: DCTNArrangement
    channel: DCTNChannel
    members: tuple[DCTNMember, ...]
    fastener: DCTNFastener
    shared_channel_source_reference: str = ""
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT or self.unit_system not in {"US", "SI"}:
            raise ValueError("DCTN requires its RC1 contract and US/SI unit system")
        if self.length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("DCTN geometry requires native in or mm units")
        if tuple(member.slot for member in self.members) != SLOTS[self.arrangement]:
            raise ValueError("DCTN active members must exactly match the selected arrangement")


def default_dctn_request(
    arrangement: DCTNArrangement = DCTNArrangement.VERTICAL_ONLY,
) -> DCTNRequest:
    """Controlled startup only. No geometry repair or material qualification."""

    def q(value: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(value, Unit.IN)

    section = DCTNSection(DCTNForm.RHS, q("24"), q("6"), q("4"), q(".375"), q(".375"))
    pattern = DCTNPattern(2, 1, q("2"), q("2"), q("1"))
    positions = {
        "V": ("0", "90"),
        "D1": ("-16", "126.86989764584402"),
        "D2": ("16", "53.13010235415599"),
    }
    members = tuple(
        DCTNMember(
            slot,
            section,
            (q(positions[slot][0]), q("0"), q("-5")),
            Decimal(positions[slot][1]),
            PhysicalQuantity.of("1", Unit.KIP),
            pattern,
        )
        for slot in SLOTS[arrangement]
    )
    hardware = SupportHardware(
        q("1.25"),
        q(".125"),
        q(".75"),
        q(".3125"),
        q(".75"),
        q(".4375"),
        q(".125"),
        "DCTN_EXPLICIT_STARTUP_GEOMETRY_NOT_STRENGTH_AUTHORITY",
    )
    return DCTNRequest(
        "dctn-preview",
        "US",
        Unit.IN,
        arrangement,
        DCTNChannel(q("72"), q("12"), q("3"), q(".375"), q(".375")),
        members,
        DCTNFastener(q(".5"), q(".563"), hardware),
    )


def change_dctn_arrangement(value: DCTNRequest, arrangement: DCTNArrangement) -> DCTNRequest:
    """Explicit arrangement editing, retaining existing active slots without hidden hardware."""
    existing = {member.slot: member for member in value.members}
    defaults = default_dctn_request(arrangement)
    members = tuple(existing.get(member.slot, member) for member in defaults.members)
    by_slot = {member.slot: member for member in members}
    if "D1" in by_slot and "D2" in by_slot and "D2" not in existing:
        members = tuple(
            replace(member, section=replace(by_slot["D1"].section, length=member.section.length))
            if member.slot == "D2"
            else member
            for member in members
        )
    return replace(
        value,
        arrangement=arrangement,
        members=members,
    )
