"""SSMC-2 physical inputs; no qualified resistance is supplied by these records."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    MemberRole,
    PrincipalAxisFamily,
)
from frp_master_connection.domain.member_profile import (
    ChannelProfileDimensions,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    WideFlangeIProfileDimensions,
)
from frp_master_connection.domain.section_topology import FRPComponentOrientation
from frp_master_connection.domain.wi_frp_support_moment import SupportHardware

CONTRACT = "SSMC-2-RC1"
PRODUCT = "STAIR_STRINGER_MITER_CONNECTION"
ROUTE = "stair-stringer-miter"
PLATE_POLICY = "MITER_PLATE_CW_BASIS_UNKNOWN_CUT"
MEMBERS = ("HORIZONTAL_STRINGER", "INCLINED_STRINGER")
GROUPS = ("HORIZONTAL_WEB_GROUP", "INCLINED_WEB_GROUP")


@dataclass(frozen=True, slots=True)
class SSMCMethodPolicy:
    """Server-owned bounded-method declaration; never a public tuning input."""

    connector_body_count: int = 1
    serial_action_factor: Decimal = Decimal(1)
    planar_method: str = "CALCULATION_SLICE_8_RC1"
    axial_row_fraction_mixing: bool = False
    polygon_authority: str = "SSMC_R1_BRANCH_TRANSITION_UNION"
    miter_contact_credit: bool = False
    hardware_shear_capacity_multiplier: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        if self.connector_body_count != 1:
            raise ValueError("SSMC_TOPOLOGY_NOT_SUPPORTED")
        if self.serial_action_factor != 1:
            raise ValueError("SSMC_SERIAL_ACTION_MISMATCH")
        if self.planar_method != "CALCULATION_SLICE_8_RC1" or self.axial_row_fraction_mixing:
            raise ValueError("SSMC_PLANAR_GROUP_METHOD_CONFLICT")
        if self.polygon_authority != "SSMC_R1_BRANCH_TRANSITION_UNION":
            raise ValueError("SSMC_POLYGON_AUTHORITY_INVALID")
        if self.miter_contact_credit:
            raise ValueError("SSMC_CONTACT_NOT_QUALIFIED")
        if self.hardware_shear_capacity_multiplier != 1:
            raise ValueError("SSMC_HARDWARE_RESPONSE_INVALID")


SSMC_METHOD_POLICY = SSMCMethodPolicy()


class StringerForm(StrEnum):
    CHANNEL = "CHANNEL"
    W_I = "W_I"


def require(value: PhysicalQuantity, dimension: Dimension, *, positive: bool = False) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not dimension:
        raise ValueError("SSMC_QUANTITY_DIMENSION_INVALID")
    if positive and value.magnitude <= 0:
        raise ValueError("SSMC_POSITIVE_DIMENSION_REQUIRED")


@dataclass(frozen=True, slots=True)
class StringerSection:
    form: StringerForm
    length: PhysicalQuantity
    depth: PhysicalQuantity
    width: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity

    def __post_init__(self) -> None:
        if not isinstance(self.form, StringerForm):
            raise ValueError("SSMC_TOPOLOGY_NOT_SUPPORTED")
        for q in (self.length, self.depth, self.width, self.web_thickness, self.flange_thickness):
            require(q, Dimension.LENGTH, positive=True)
        self.profile("VALIDATION", Unit.MM)

    def profile(self, owner: str, unit: Unit) -> MemberProfile:
        dimensions = tuple(
            q.to(unit).magnitude
            for q in (
                self.length,
                self.depth,
                self.width,
                self.web_thickness,
                self.flange_thickness,
            )
        )
        channel = self.form is StringerForm.CHANNEL
        return MemberProfile(
            owner + ":PROFILE",
            owner,
            MemberRole.BRACE,
            MemberProfileFamily.CHANNEL if channel else MemberProfileFamily.WIDE_FLANGE_I,
            ChannelProfileDimensions(*dimensions)
            if channel
            else WideFlangeIProfileDimensions(*dimensions),
            ComponentMaterialKind.PULTRUDED_FRP,
            FRPComponentOrientation(
                CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, owner),
                PrincipalAxisFamily.X,
            ),
            MemberProfileOrientation.ROTATION_0,
            MemberProfileSurfaceId.WEB_OUTER if channel else MemberProfileSurfaceId.WEB_POS_FACE,
        )


@dataclass(frozen=True, slots=True)
class SSMCGroup:
    rows: int
    first_from_cut: PhysicalQuantity
    pitch: PhysicalQuantity
    gauge: PhysicalQuantity
    transverse_offset: PhysicalQuantity
    ordinary_snug_tight: bool = True
    slots: bool = False
    equal_translational_stiffness: bool = True

    def __post_init__(self) -> None:
        if type(self.rows) is not int or self.rows not in {2, 3}:
            raise ValueError("SSMC_GROUP_TOPOLOGY_NOT_SUPPORTED")
        for q in (self.first_from_cut, self.pitch, self.gauge):
            require(q, Dimension.LENGTH, positive=True)
        require(self.transverse_offset, Dimension.LENGTH)
        if any(
            type(v) is not bool
            for v in (self.ordinary_snug_tight, self.slots, self.equal_translational_stiffness)
        ):
            raise ValueError("SSMC_GROUP_ASSUMPTION_INVALID")

    @property
    def planar_eligible(self) -> bool:
        return self.ordinary_snug_tight and not self.slots and self.equal_translational_stiffness


@dataclass(frozen=True, slots=True)
class SSMCPlate:
    side: str
    thickness: PhysicalQuantity
    horizontal_overlap: PhysicalQuantity
    inclined_overlap: PhysicalQuantity
    horizontal_depth: PhysicalQuantity
    inclined_depth: PhysicalQuantity
    normal_gap: PhysicalQuantity
    corner_radius: PhysicalQuantity
    chamfer: PhysicalQuantity

    def __post_init__(self) -> None:
        if self.side not in {"NEG_Y", "POS_Y"}:
            raise ValueError("SSMC_TOPOLOGY_NOT_SUPPORTED")
        for q in (
            self.thickness,
            self.horizontal_overlap,
            self.inclined_overlap,
            self.horizontal_depth,
            self.inclined_depth,
        ):
            require(q, Dimension.LENGTH, positive=True)
        for q in (self.normal_gap, self.corner_radius, self.chamfer):
            require(q, Dimension.LENGTH)
            if q.magnitude < 0:
                raise ValueError("SSMC_MEMBER_REFERENCE_GEOMETRY_INVALID")


@dataclass(frozen=True, slots=True)
class SSMCFastener:
    diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    hardware: SupportHardware
    threads: str
    source_reference: str = ""

    def __post_init__(self) -> None:
        for q in (self.diameter, self.hole_diameter):
            require(q, Dimension.LENGTH, positive=True)
        if self.hole_diameter.canonical_magnitude <= self.diameter.canonical_magnitude:
            raise ValueError("SSMC_HOLE_GEOMETRY_INVALID")
        if (
            self.hardware.washer_diameter.canonical_magnitude
            <= self.hole_diameter.canonical_magnitude
        ):
            raise ValueError("SSMC_HARDWARE_GEOMETRY_INVALID")
        if self.threads not in {"INCLUDED", "EXCLUDED"}:
            raise ValueError("SSMC_HARDWARE_GEOMETRY_INVALID")


@dataclass(frozen=True, slots=True)
class SSMCRequest:
    request_id: str
    unit_system: str
    horizontal: StringerSection
    inclined: StringerSection
    theta_deg: Decimal
    plate: SSMCPlate
    horizontal_group: SSMCGroup
    inclined_group: SSMCGroup
    fastener: SSMCFastener
    N: PhysicalQuantity
    V: PhysicalQuantity
    M: PhysicalQuantity
    source_reference: str = ""
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT or self.unit_system not in {"US", "SI"}:
            raise ValueError("SSMC_CONTRACT_INVALID")
        if not self.request_id.strip():
            raise ValueError("SSMC_REQUEST_ID_REQUIRED")
        if not self.theta_deg.is_finite() or not Decimal(30) <= abs(self.theta_deg) <= Decimal(45):
            raise ValueError("SSMC_INCLINATION_OUTSIDE_RC1_DOMAIN")
        require(self.N, Dimension.FORCE)
        require(self.V, Dimension.FORCE)
        require(self.M, Dimension.MOMENT)

    @property
    def length_unit(self) -> Unit:
        return Unit.IN if self.unit_system == "US" else Unit.MM
