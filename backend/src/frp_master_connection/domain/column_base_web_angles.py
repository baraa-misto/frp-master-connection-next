"""Canonical Stage 3.5C column-base component and request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
else:
    PhysicalQuantity = Any
    Unit = Any

from .beam_concrete_paired_angle import ExternalAnchorGeometry
from .clip_angle import ClipAngleBoltLayout, ClipAngleDimensions
from .member_profile import MemberProfile, MemberProfileFamily, MemberProfileSurfaceId
from .values import ComponentMaterialKind, EngineeringUnitSystem, MemberRole


def _dimension(value: object) -> str | None:
    return getattr(getattr(value, "dimension", None), "value", None)


class ColumnBaseAssembly(StrEnum):
    SINGLE_BASE_ANGLE = "SINGLE_BASE_ANGLE"
    SYMMETRIC_DOUBLE_BASE_ANGLES = "SYMMETRIC_DOUBLE_BASE_ANGLES"
    DOUBLE_BASE_ANGLES = "DOUBLE_BASE_ANGLES"


class ColumnBaseSide(StrEnum):
    POSITIVE_T_C = "+T_C"
    NEGATIVE_T_C = "-T_C"

    @property
    def sign(self) -> Decimal:
        return Decimal(1) if self is ColumnBaseSide.POSITIVE_T_C else Decimal(-1)


class ColumnBaseStatus(StrEnum):
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class ColumnBaseFrame:
    s_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(1),
        Decimal(0),
        Decimal(0),
    )
    t_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(0),
        Decimal(1),
        Decimal(0),
    )
    l_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(0),
        Decimal(0),
        Decimal(1),
    )
    handedness: str = "S_C cross T_C = L_C"
    concrete_top: str = "L_C=0"


@dataclass(frozen=True, slots=True)
class ColumnBaseConcreteGeometry:
    s_dimension: PhysicalQuantity
    t_dimension: PhysicalQuantity
    depth: PhysicalQuantity

    def __post_init__(self) -> None:
        for value in (self.s_dimension, self.t_dimension, self.depth):
            if _dimension(value) != "LENGTH" or value.magnitude <= 0:
                raise ValueError("Concrete dimensions must be positive lengths.")


@dataclass(frozen=True, slots=True)
class ColumnBaseWideFlangeGeometry:
    depth_s: PhysicalQuantity
    flange_width_t: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    display_height: PhysicalQuantity
    profile_family: str = "WIDE_FLANGE_I"

    def __post_init__(self) -> None:
        values = (
            self.depth_s,
            self.flange_width_t,
            self.web_thickness,
            self.flange_thickness,
            self.display_height,
        )
        if any(_dimension(value) != "LENGTH" or value.magnitude <= 0 for value in values):
            raise ValueError("W/I dimensions must be positive lengths.")
        if self.web_thickness.canonical_magnitude >= self.flange_width_t.canonical_magnitude:
            raise ValueError("The W/I web must be thinner than the flange width.")
        if self.flange_thickness.canonical_magnitude * 2 >= self.depth_s.canonical_magnitude:
            raise ValueError("The W/I flanges must leave a positive web depth.")
        if self.profile_family != "WIDE_FLANGE_I":
            raise ValueError("Stage 3.5C supports only a W/I column.")


@dataclass(frozen=True, slots=True)
class ColumnBaseAnchorPattern:
    row_count: int
    anchors_per_row: int
    pitch: PhysicalQuantity
    gauge: PhysicalQuantity
    centroid_offset_t: PhysicalQuantity

    def __post_init__(self) -> None:
        if self.row_count < 1 or self.anchors_per_row < 1:
            raise ValueError("Anchor row and line counts must be positive.")
        for value in (self.pitch, self.gauge, self.centroid_offset_t):
            if _dimension(value) != "LENGTH" or value.magnitude < 0:
                raise ValueError("Anchor pattern dimensions must be nonnegative lengths.")


@dataclass(frozen=True, slots=True)
class ColumnBaseVector:
    s: PhysicalQuantity
    t: PhysicalQuantity
    longitudinal: PhysicalQuantity

    def __post_init__(self) -> None:
        if len({value.dimension for value in (self.s, self.t, self.longitudinal)}) != 1:
            raise ValueError("Column-base vector components must share one dimension.")


@dataclass(frozen=True, slots=True)
class ColumnBaseRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometry
    column: ColumnBaseWideFlangeGeometry
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide
    angle: ClipAngleDimensions
    web_layout: ClipAngleBoltLayout
    anchor_pattern: ColumnBaseAnchorPattern
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    external_anchor: ExternalAnchorGeometry
    axial_compression: PhysicalQuantity
    web_plane_shear: PhysicalQuantity
    web_normal_shear: PhysicalQuantity
    user_moment: ColumnBaseVector
    action_reference: ColumnBaseVector
    contract_version: str = "3.5C-RC1"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.contract_version != "3.5C-RC1":
            raise ValueError("Unsupported Stage 3.5C contract version.")
        expected = "in" if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else "mm"
        if getattr(self.source_length_unit, "value", None) != expected:
            raise ValueError("Source length unit must match the engineering unit system.")
        for value in (self.web_bolt_diameter, self.web_hole_diameter):
            if _dimension(value) != "LENGTH" or value.magnitude <= 0:
                raise ValueError("Web bolt and hole diameters must be positive lengths.")
        if self.web_hole_diameter.canonical_magnitude < self.web_bolt_diameter.canonical_magnitude:
            raise ValueError("The web hole cannot be smaller than its bolt.")
        for value in (self.axial_compression, self.web_plane_shear, self.web_normal_shear):
            if _dimension(value) != "FORCE":
                raise ValueError("Stage 3.5C actions must be force quantities.")
        if self.axial_compression.magnitude < 0:
            raise ValueError("STAGE_3_5C_AXIAL_TENSION_UPLIFT_NOT_AUTHORIZED")
        if _dimension(self.user_moment.s) != "MOMENT":
            raise ValueError("user_moment must contain moment quantities.")
        if any(value.canonical_magnitude != 0 for value in self.user_moment_tuple):
            raise ValueError("STAGE_3_5C_USER_APPLIED_MOMENT_NOT_ALLOWED")
        if _dimension(self.action_reference.s) != "LENGTH":
            raise ValueError("action_reference must contain length quantities.")

    @property
    def user_moment_tuple(self) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
        return (self.user_moment.s, self.user_moment.t, self.user_moment.longitudinal)


@dataclass(frozen=True, slots=True)
class ColumnBaseSignedRequest:
    """Successor request with signed axial force (+uplift / -compression)."""

    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometry
    column: ColumnBaseWideFlangeGeometry
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide
    angle: ClipAngleDimensions
    web_layout: ClipAngleBoltLayout
    anchor_pattern: ColumnBaseAnchorPattern
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    external_anchor: ExternalAnchorGeometry
    signed_axial_force: PhysicalQuantity
    web_plane_shear: PhysicalQuantity
    web_normal_shear: PhysicalQuantity
    user_moment: ColumnBaseVector
    action_reference: ColumnBaseVector
    contract_version: str = "3.5C-R2-RC1"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.contract_version != "3.5C-R2-RC1":
            raise ValueError("Unsupported Stage 3.5C-R2 contract version.")
        expected = "in" if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else "mm"
        if getattr(self.source_length_unit, "value", None) != expected:
            raise ValueError("Source length unit must match the engineering unit system.")
        for value in (self.web_bolt_diameter, self.web_hole_diameter):
            if _dimension(value) != "LENGTH" or value.magnitude <= 0:
                raise ValueError("Web bolt and hole diameters must be positive lengths.")
        if self.web_hole_diameter.canonical_magnitude < self.web_bolt_diameter.canonical_magnitude:
            raise ValueError("The web hole cannot be smaller than its bolt.")
        for value in (self.signed_axial_force, self.web_plane_shear, self.web_normal_shear):
            if _dimension(value) != "FORCE":
                raise ValueError("Stage 3.5C-R2 actions must be force quantities.")
        if _dimension(self.user_moment.s) != "MOMENT":
            raise ValueError("user_moment must contain moment quantities.")
        if any(value.canonical_magnitude != 0 for value in self.user_moment_tuple):
            raise ValueError("STAGE_3_5C_USER_APPLIED_MOMENT_NOT_ALLOWED")
        if _dimension(self.action_reference.s) != "LENGTH":
            raise ValueError("action_reference must contain length quantities.")

    @property
    def user_moment_tuple(self) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
        return (self.user_moment.s, self.user_moment.t, self.user_moment.longitudinal)


_STAGE_3_7A_PROFILE_SURFACES = {
    MemberProfileFamily.WIDE_FLANGE_I: {
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    },
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: {
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    },
    MemberProfileFamily.SOLID_RECTANGULAR_SECTION: {
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    },
    MemberProfileFamily.ANGLE: {
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    },
}


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileRequest:
    """Stage 3.7A additive profile-matrix request.

    Unlike the historical contracts, the member-end action reference is resolved
    from ``column_profile`` by the backend and is therefore not user transport.
    """

    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometry
    column_profile: MemberProfile
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide
    angle: ClipAngleDimensions
    web_layout: ClipAngleBoltLayout
    anchor_pattern: ColumnBaseAnchorPattern
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    external_anchor: ExternalAnchorGeometry
    signed_axial_force: PhysicalQuantity
    connection_plane_shear: PhysicalQuantity
    connection_normal_shear: PhysicalQuantity
    user_moment: ColumnBaseVector
    angle_double_topology: str = "SAME_SELECTED_LEG_OPPOSITE_FACES"
    contract_version: str = "3.7A-RC1"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.contract_version != "3.7A-RC1":
            raise ValueError("Unsupported Stage 3.7A contract version.")
        expected = "in" if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else "mm"
        if getattr(self.source_length_unit, "value", None) != expected:
            raise ValueError("Source length unit must match the engineering unit system.")
        profile = self.column_profile
        if not isinstance(profile, MemberProfile):
            raise TypeError("column_profile must be a MemberProfile.")
        if (
            profile.role is not MemberRole.COLUMN
            or profile.material_kind is not ComponentMaterialKind.PULTRUDED_FRP
        ):
            raise ValueError("Stage 3.7A requires one pultruded FRP column profile.")
        allowed = _STAGE_3_7A_PROFILE_SURFACES.get(profile.family)
        if allowed is None or profile.selected_surface not in allowed:
            raise ValueError("Unsupported Stage 3.7A column profile or selected surface.")
        if self.assembly not in {
            ColumnBaseAssembly.SINGLE_BASE_ANGLE,
            ColumnBaseAssembly.DOUBLE_BASE_ANGLES,
        }:
            raise ValueError("Stage 3.7A accepts only Single or Double base angles.")
        if (
            profile.family is MemberProfileFamily.ANGLE
            and self.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
            and self.angle_double_topology != "SAME_SELECTED_LEG_OPPOSITE_FACES"
        ):
            raise ValueError("ANGLE_COLUMN_TWO_DIFFERENT_LEGS_MOMENT_BASE_NOT_IN_STAGE_3_7A_SCOPE")
        for value in (self.web_bolt_diameter, self.web_hole_diameter):
            if _dimension(value) != "LENGTH" or value.magnitude <= 0:
                raise ValueError("Column bolt and hole diameters must be positive lengths.")
        if self.web_hole_diameter.canonical_magnitude < self.web_bolt_diameter.canonical_magnitude:
            raise ValueError("The column hole cannot be smaller than its bolt.")
        for value in (
            self.signed_axial_force,
            self.connection_plane_shear,
            self.connection_normal_shear,
        ):
            if _dimension(value) != "FORCE":
                raise ValueError("Stage 3.7A actions must be force quantities.")
        if _dimension(self.user_moment.s) != "MOMENT" or any(
            value.canonical_magnitude != 0 for value in self.user_moment_tuple
        ):
            raise ValueError("STAGE_3_7A_USER_APPLIED_MOMENT_NOT_ALLOWED")

    @property
    def user_moment_tuple(self) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
        return (self.user_moment.s, self.user_moment.t, self.user_moment.longitudinal)


__all__ = (
    "ColumnBaseAnchorPattern",
    "ColumnBaseAssembly",
    "ColumnBaseConcreteGeometry",
    "ColumnBaseFrame",
    "ColumnBaseProfileRequest",
    "ColumnBaseRequest",
    "ColumnBaseSide",
    "ColumnBaseSignedRequest",
    "ColumnBaseStatus",
    "ColumnBaseVector",
    "ColumnBaseWideFlangeGeometry",
)
