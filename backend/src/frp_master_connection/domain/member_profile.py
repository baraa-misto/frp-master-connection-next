"""Stage 3.2-R2 exact member/profile and selectable-surface contracts.

The contracts in this module retain authoritative engineering dimensions as
``Decimal`` values.  Existing float-based section/placement geometry is an adapter
target only; it is deliberately not part of the member/profile fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.domain.section_topology import (
    FRPComponentOrientation,
    PhysicalSectionElementRole,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
)
from frp_master_connection.domain.values import (
    ComponentMaterialKind,
    CoordinateFrameKind,
    MemberRole,
    PrincipalAxisFamily,
    SectionFamily,
)

MEMBER_PROFILE_SCHEMA_VERSION = "0.1.0-draft"
DIRECT_TEE_CURVED_SURFACE_REASON = "CURVED_SURFACE_REQUIRES_SEPARATELY_DEFINED_INTERFACE_OR_ADAPTER"
INTERNAL_FASTENER_ACCESS_REQUIRED = "INTERNAL_FASTENER_ACCESS_REQUIRED"


class MemberProfileFamily(StrEnum):
    """Owner-controlled structural profile-family identities."""

    ANGLE = "ANGLE"
    CHANNEL = "CHANNEL"
    WIDE_FLANGE_I = "WIDE_FLANGE_I"
    RECTANGULAR_HOLLOW_SECTION = "RECTANGULAR_HOLLOW_SECTION"
    SOLID_RECTANGULAR_SECTION = "SOLID_RECTANGULAR_SECTION"
    FLAT_PLATE = "FLAT_PLATE"
    ROUND_HOLLOW_SECTION = "ROUND_HOLLOW_SECTION"


class MemberProfileSizeBasis(StrEnum):
    """R2 admits custom dimensions without inventing a profile catalog."""

    CUSTOM_DIMENSIONS = "CUSTOM_DIMENSIONS"


class MemberProfileOrientation(StrEnum):
    """Right-hand quarter-turn orientation about member-local positive X."""

    ROTATION_0 = "ROTATION_0"
    ROTATION_90 = "ROTATION_90"
    ROTATION_180 = "ROTATION_180"
    ROTATION_270 = "ROTATION_270"

    @property
    def quarter_turns(self) -> int:
        """Return the exact number of positive quarter turns about local X."""

        return {
            MemberProfileOrientation.ROTATION_0: 0,
            MemberProfileOrientation.ROTATION_90: 1,
            MemberProfileOrientation.ROTATION_180: 2,
            MemberProfileOrientation.ROTATION_270: 3,
        }[self]


class MemberProfileSurfaceId(StrEnum):
    """Stable owner surface IDs shared only where their physical meaning is shared."""

    LEG_Y_OUTER = "LEG_Y_OUTER"
    LEG_Z_OUTER = "LEG_Z_OUTER"
    WEB_OUTER = "WEB_OUTER"
    WEB_POS_FACE = "WEB_POS_FACE"
    WEB_NEG_FACE = "WEB_NEG_FACE"
    FLANGE_POS_OUTER = "FLANGE_POS_OUTER"
    FLANGE_NEG_OUTER = "FLANGE_NEG_OUTER"
    Y_POS_FACE = "Y_POS_FACE"
    Y_NEG_FACE = "Y_NEG_FACE"
    Z_POS_FACE = "Z_POS_FACE"
    Z_NEG_FACE = "Z_NEG_FACE"
    FACE_POS = "FACE_POS"
    FACE_NEG = "FACE_NEG"


class AngleLegBoltPathReason(StrEnum):
    """Fail-closed reasons for exact Angle-leg opposing-boundary resolution."""

    OUTSIDE_SELECTED_LEG_SURFACE = "OUTSIDE_SELECTED_LEG_SURFACE"
    NO_FINITE_EXPOSED_OPPOSING_BROAD_FACE = "NO_FINITE_EXPOSED_OPPOSING_BROAD_FACE"
    AMBIGUOUS_FINITE_EXPOSED_OPPOSING_BROAD_FACE = "AMBIGUOUS_FINITE_EXPOSED_OPPOSING_BROAD_FACE"


class ProfileWallBoltPathReason(StrEnum):
    """Fail-closed reasons for exact non-Angle profile-wall resolution."""

    OUTSIDE_SELECTED_PROFILE_SURFACE = "OUTSIDE_SELECTED_PROFILE_SURFACE"
    NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE = "NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE"


_RECTANGULAR_OPPOSING_SURFACE_IDS = {
    MemberProfileSurfaceId.Y_POS_FACE: MemberProfileSurfaceId.Y_NEG_FACE,
    MemberProfileSurfaceId.Y_NEG_FACE: MemberProfileSurfaceId.Y_POS_FACE,
    MemberProfileSurfaceId.Z_POS_FACE: MemberProfileSurfaceId.Z_NEG_FACE,
    MemberProfileSurfaceId.Z_NEG_FACE: MemberProfileSurfaceId.Z_POS_FACE,
}


def _decimal(value: object, field_name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite.")
    if positive and value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def _validate_dimensions(value: object, names: tuple[str, ...]) -> None:
    for name in names:
        _decimal(getattr(value, name), f"{type(value).__name__}.{name}", positive=True)


@dataclass(frozen=True, slots=True)
class AngleProfileDimensions:
    member_length: Decimal
    leg_y: Decimal
    leg_z: Decimal
    thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(self, ("member_length", "leg_y", "leg_z", "thickness"))
        if self.thickness >= self.leg_y or self.thickness >= self.leg_z:
            raise ValueError("Angle thickness must be less than both leg dimensions.")


@dataclass(frozen=True, slots=True)
class ChannelProfileDimensions:
    member_length: Decimal
    depth: Decimal
    flange_width: Decimal
    web_thickness: Decimal
    flange_thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(
            self,
            (
                "member_length",
                "depth",
                "flange_width",
                "web_thickness",
                "flange_thickness",
            ),
        )
        _validate_flanged_profile(self)


@dataclass(frozen=True, slots=True)
class WideFlangeIProfileDimensions:
    member_length: Decimal
    depth: Decimal
    flange_width: Decimal
    web_thickness: Decimal
    flange_thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(
            self,
            (
                "member_length",
                "depth",
                "flange_width",
                "web_thickness",
                "flange_thickness",
            ),
        )
        _validate_flanged_profile(self)


def _validate_flanged_profile(
    value: ChannelProfileDimensions | WideFlangeIProfileDimensions,
) -> None:
    if Decimal(2) * value.flange_thickness >= value.depth:
        raise ValueError("Flanged profile requires positive clear web depth.")
    if value.web_thickness >= value.flange_width:
        raise ValueError("Flanged profile web thickness must be less than flange width.")


@dataclass(frozen=True, slots=True)
class RectangularHollowProfileDimensions:
    member_length: Decimal
    depth: Decimal
    width: Decimal
    wall_thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(self, ("member_length", "depth", "width", "wall_thickness"))
        twice_wall = Decimal(2) * self.wall_thickness
        if twice_wall >= self.depth or twice_wall >= self.width:
            raise ValueError("Rectangular hollow profile requires positive inside dimensions.")


@dataclass(frozen=True, slots=True)
class SolidRectangularProfileDimensions:
    """Exact dimensions for one continuous solid rectangular member volume."""

    member_length: Decimal
    depth: Decimal
    width: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(self, ("member_length", "depth", "width"))


@dataclass(frozen=True, slots=True)
class FlatPlateProfileDimensions:
    member_length: Decimal
    width: Decimal
    thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(self, ("member_length", "width", "thickness"))


@dataclass(frozen=True, slots=True)
class RoundHollowProfileDimensions:
    member_length: Decimal
    outer_diameter: Decimal
    wall_thickness: Decimal

    def __post_init__(self) -> None:
        _validate_dimensions(self, ("member_length", "outer_diameter", "wall_thickness"))
        if Decimal(2) * self.wall_thickness >= self.outer_diameter:
            raise ValueError("Round hollow profile requires a positive inside diameter.")


type MemberProfileDimensions = (
    AngleProfileDimensions
    | ChannelProfileDimensions
    | WideFlangeIProfileDimensions
    | RectangularHollowProfileDimensions
    | SolidRectangularProfileDimensions
    | FlatPlateProfileDimensions
    | RoundHollowProfileDimensions
)


_DIMENSION_TYPES: dict[MemberProfileFamily, type[MemberProfileDimensions]] = {
    MemberProfileFamily.ANGLE: AngleProfileDimensions,
    MemberProfileFamily.CHANNEL: ChannelProfileDimensions,
    MemberProfileFamily.WIDE_FLANGE_I: WideFlangeIProfileDimensions,
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: RectangularHollowProfileDimensions,
    MemberProfileFamily.SOLID_RECTANGULAR_SECTION: SolidRectangularProfileDimensions,
    MemberProfileFamily.FLAT_PLATE: FlatPlateProfileDimensions,
    MemberProfileFamily.ROUND_HOLLOW_SECTION: RoundHollowProfileDimensions,
}

_SECTION_FAMILIES = {
    MemberProfileFamily.ANGLE: SectionFamily.ANGLE,
    MemberProfileFamily.CHANNEL: SectionFamily.CHANNEL,
    MemberProfileFamily.WIDE_FLANGE_I: SectionFamily.WIDE_FLANGE,
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: SectionFamily.RECTANGULAR_TUBE,
    MemberProfileFamily.SOLID_RECTANGULAR_SECTION: SectionFamily.PLATE,
    MemberProfileFamily.FLAT_PLATE: SectionFamily.PLATE,
    MemberProfileFamily.ROUND_HOLLOW_SECTION: SectionFamily.ROUND_TUBE,
}

_SELECTABLE_SURFACES = {
    MemberProfileFamily.ANGLE: (
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ),
    MemberProfileFamily.CHANNEL: (
        MemberProfileSurfaceId.WEB_OUTER,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ),
    MemberProfileFamily.WIDE_FLANGE_I: (
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ),
    MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: (
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ),
    MemberProfileFamily.SOLID_RECTANGULAR_SECTION: (
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ),
    MemberProfileFamily.FLAT_PLATE: (
        MemberProfileSurfaceId.FACE_POS,
        MemberProfileSurfaceId.FACE_NEG,
    ),
    MemberProfileFamily.ROUND_HOLLOW_SECTION: (),
}


def selectable_profile_surfaces(
    family: MemberProfileFamily,
) -> tuple[MemberProfileSurfaceId, ...]:
    """Return the exact ordered selectable-surface vocabulary for one family."""

    require_enum(family, MemberProfileFamily, "family")
    return _SELECTABLE_SURFACES[family]


def section_family_for_profile(family: MemberProfileFamily) -> SectionFamily:
    """Map an R2 identity to the unchanged standard-section kernel identity."""

    require_enum(family, MemberProfileFamily, "family")
    return _SECTION_FAMILIES[family]


@dataclass(frozen=True, slots=True)
class ExactProfileVector3D:
    """One finite exact vector or point in member-local X-Y-Z coordinates."""

    x: Decimal
    y: Decimal
    z: Decimal

    def __post_init__(self) -> None:
        for name in ("x", "y", "z"):
            _decimal(getattr(self, name), f"ExactProfileVector3D.{name}")


@dataclass(frozen=True, slots=True)
class ProfileLocalBounds3D:
    """Exact axis-aligned finite bounds for one planar profile surface."""

    min_x: Decimal
    max_x: Decimal
    min_y: Decimal
    max_y: Decimal
    min_z: Decimal
    max_z: Decimal

    def __post_init__(self) -> None:
        for name in ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z"):
            _decimal(getattr(self, name), f"ProfileLocalBounds3D.{name}")
        spans = (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
        )
        if any(span < 0 for span in spans):
            raise ValueError("Profile surface bounds must be nondecreasing on every axis.")
        if sum(span == 0 for span in spans) != 1 or sum(span > 0 for span in spans) != 2:
            raise ValueError("Profile surface bounds must describe exactly one finite plane.")

    @property
    def center(self) -> ExactProfileVector3D:
        two = Decimal(2)
        return ExactProfileVector3D(
            (self.min_x + self.max_x) / two,
            (self.min_y + self.max_y) / two,
            (self.min_z + self.max_z) / two,
        )


@dataclass(frozen=True, slots=True)
class ProfileSurfaceDefinition:
    """One owner surface and its safe penetrated-element sub-bounds."""

    surface_id: MemberProfileSurfaceId
    plane_axis: PrincipalAxisFamily
    plane_coordinate: Decimal
    local_outward_normal: ExactProfileVector3D
    contact_bounds: ProfileLocalBounds3D
    penetration_bounds: tuple[ProfileLocalBounds3D, ...]
    physical_element_role: PhysicalSectionElementRole
    outside_patch_id: str
    opposing_patch_ids: tuple[str, ...]
    opposite_plane_coordinate: Decimal

    def __post_init__(self) -> None:
        require_enum(self.surface_id, MemberProfileSurfaceId, "ProfileSurfaceDefinition.surface_id")
        require_enum(self.plane_axis, PrincipalAxisFamily, "ProfileSurfaceDefinition.plane_axis")
        if self.plane_axis is PrincipalAxisFamily.X:
            raise ValueError("Selectable profile surfaces must be longitudinal, not end cuts.")
        coordinate = _decimal(
            self.plane_coordinate,
            "ProfileSurfaceDefinition.plane_coordinate",
        )
        opposite = _decimal(
            self.opposite_plane_coordinate,
            "ProfileSurfaceDefinition.opposite_plane_coordinate",
        )
        if coordinate == opposite:
            raise ValueError("Profile layer faces must have positive through-thickness separation.")
        if not isinstance(self.local_outward_normal, ExactProfileVector3D):
            raise TypeError("ProfileSurfaceDefinition.local_outward_normal must be exact.")
        expected = (
            (Decimal(0), Decimal(1), Decimal(0))
            if self.plane_axis is PrincipalAxisFamily.Y
            else (Decimal(0), Decimal(0), Decimal(1))
        )
        normal = (
            self.local_outward_normal.x,
            abs(self.local_outward_normal.y),
            abs(self.local_outward_normal.z),
        )
        if normal != expected:
            raise ValueError("Profile surface normal must be axis-aligned and unit length.")
        if not isinstance(self.contact_bounds, ProfileLocalBounds3D):
            raise TypeError("ProfileSurfaceDefinition.contact_bounds must be exact bounds.")
        _validate_bounds_plane(self.contact_bounds, self.plane_axis, coordinate)
        require_tuple(self.penetration_bounds, "ProfileSurfaceDefinition.penetration_bounds")
        if not self.penetration_bounds:
            raise ValueError("A selectable surface requires penetrable physical-element bounds.")
        for bounds in self.penetration_bounds:
            if not isinstance(bounds, ProfileLocalBounds3D):
                raise TypeError("Profile penetration bounds must be exact bounds.")
            _validate_bounds_plane(bounds, self.plane_axis, coordinate)
            if not _bounds_within(bounds, self.contact_bounds):
                raise ValueError("Profile penetration bounds must lie within contact bounds.")
        require_enum(
            self.physical_element_role,
            PhysicalSectionElementRole,
            "ProfileSurfaceDefinition.physical_element_role",
        )
        validate_identifier(self.outside_patch_id, "ProfileSurfaceDefinition.outside_patch_id")
        require_tuple(self.opposing_patch_ids, "ProfileSurfaceDefinition.opposing_patch_ids")
        if len(self.opposing_patch_ids) != len(self.penetration_bounds):
            raise ValueError("Each penetration region requires one opposing kernel patch ID.")
        for patch_id in self.opposing_patch_ids:
            validate_identifier(patch_id, "ProfileSurfaceDefinition.opposing_patch_ids item")
        if len(set(self.opposing_patch_ids)) != len(self.opposing_patch_ids):
            raise ValueError("Opposing kernel patch IDs must be unique.")

    @property
    def physical_element_id(self) -> str:
        """Return the unchanged canonical topology element ID."""

        return self.physical_element_role.value

    @property
    def layer_thickness(self) -> Decimal:
        return abs(self.plane_coordinate - self.opposite_plane_coordinate)

    @property
    def center(self) -> ExactProfileVector3D:
        return self.contact_bounds.center


@dataclass(frozen=True, slots=True)
class AngleLegBoltPathResolution:
    """Exact selected-surface-to-opposing-boundary result for one Angle bolt center."""

    selected_surface: MemberProfileSurfaceId
    outer_surface_point_local: ExactProfileVector3D
    valid: bool
    opposing_patch_id: str | None
    opposing_surface_point_local: ExactProfileVector3D | None
    penetrated_thickness: Decimal | None
    reason: AngleLegBoltPathReason | None


@dataclass(frozen=True, slots=True)
class ProfileWallBoltPathResolution:
    """Exact selected-wall-to-opposing-boundary result for one bolt footprint."""

    selected_surface: MemberProfileSurfaceId
    outer_surface_point_local: ExactProfileVector3D
    valid: bool
    opposing_patch_id: str | None
    opposing_surface_point_local: ExactProfileVector3D | None
    penetrated_thickness: Decimal | None
    qualifications: tuple[str, ...]
    reason: ProfileWallBoltPathReason | None


def _validate_bounds_plane(
    bounds: ProfileLocalBounds3D,
    axis: PrincipalAxisFamily,
    coordinate: Decimal,
) -> None:
    minimum, maximum = (
        (bounds.min_y, bounds.max_y)
        if axis is PrincipalAxisFamily.Y
        else (bounds.min_z, bounds.max_z)
    )
    if minimum != coordinate or maximum != coordinate:
        raise ValueError("Profile bounds must lie on the declared plane coordinate.")


def _bounds_within(inner: ProfileLocalBounds3D, outer: ProfileLocalBounds3D) -> bool:
    return (
        outer.min_x <= inner.min_x <= inner.max_x <= outer.max_x
        and outer.min_y <= inner.min_y <= inner.max_y <= outer.max_y
        and outer.min_z <= inner.min_z <= inner.max_z <= outer.max_z
    )


@dataclass(frozen=True, slots=True)
class MemberProfile:
    """Exact member/profile/material/orientation/surface engineering identity."""

    id: str
    member_id: str
    role: MemberRole
    family: MemberProfileFamily
    dimensions: MemberProfileDimensions
    material_kind: ComponentMaterialKind
    material_orientation: FRPComponentOrientation | None
    orientation: MemberProfileOrientation
    selected_surface: MemberProfileSurfaceId | None
    size_basis: MemberProfileSizeBasis = MemberProfileSizeBasis.CUSTOM_DIMENSIONS

    def __post_init__(self) -> None:
        validate_identifier(self.id, "MemberProfile.id")
        validate_identifier(self.member_id, "MemberProfile.member_id")
        require_enum(self.role, MemberRole, "MemberProfile.role")
        require_enum(self.family, MemberProfileFamily, "MemberProfile.family")
        expected = _DIMENSION_TYPES[self.family]
        if not isinstance(self.dimensions, expected):
            raise TypeError(f"{self.family.value} requires {expected.__name__} dimensions.")
        require_enum(self.material_kind, ComponentMaterialKind, "MemberProfile.material_kind")
        self._validate_material_orientation()
        require_enum(self.orientation, MemberProfileOrientation, "MemberProfile.orientation")
        require_enum(self.size_basis, MemberProfileSizeBasis, "MemberProfile.size_basis")
        selectable = selectable_profile_surfaces(self.family)
        if self.family is MemberProfileFamily.ROUND_HOLLOW_SECTION:
            if self.selected_surface is not None:
                raise ValueError("Round hollow profile has no selectable direct flat surface.")
        elif not isinstance(self.selected_surface, MemberProfileSurfaceId):
            raise TypeError("MemberProfile.selected_surface must be a profile surface ID.")
        elif self.selected_surface not in selectable:
            raise ValueError("Selected surface is not exposed by this profile family.")

    def _validate_material_orientation(self) -> None:
        if self.material_kind is ComponentMaterialKind.PULTRUDED_FRP:
            if not isinstance(self.material_orientation, FRPComponentOrientation):
                raise TypeError("Pultruded FRP member profiles require material orientation.")
            frame = self.material_orientation.coordinate_frame
            if (
                frame.kind is not CoordinateFrameKind.MEMBER_LOCAL
                or frame.owner_id != self.member_id
            ):
                raise ValueError(
                    "Member profile material orientation must use its member-local frame."
                )
        elif self.material_orientation is not None:
            raise ValueError("Non-FRP member profiles must not carry FRP material orientation.")

    @property
    def section_family(self) -> SectionFamily:
        return section_family_for_profile(self.family)

    @property
    def member_length(self) -> Decimal:
        return self.dimensions.member_length


def profile_member_axis_reference(profile: MemberProfile) -> ExactProfileVector3D:
    """Return the exact section-centroid member axis in profile-local coordinates.

    The accepted sharp-corner Angle model is the union of two rectangles with the
    square heel overlap removed. Symmetric rectangular and W/I profiles retain the
    established origin-centered member axis. This authority is independent of
    connection placement and presentation geometry.
    """

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    dimensions = profile.dimensions
    if not isinstance(dimensions, AngleProfileDimensions):
        return ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(0))
    leg_y = dimensions.leg_y
    leg_z = dimensions.leg_z
    thickness = dimensions.thickness
    area_y = leg_y * thickness
    area_z = thickness * leg_z
    overlap = thickness * thickness
    total = area_y + area_z - overlap
    centroid_y = (
        area_y * leg_y / Decimal(2)
        + area_z * thickness / Decimal(2)
        - overlap * thickness / Decimal(2)
    ) / total
    centroid_z = (
        area_y * thickness / Decimal(2)
        + area_z * leg_z / Decimal(2)
        - overlap * thickness / Decimal(2)
    ) / total
    y, z = _rotate_yz(centroid_y, centroid_z, profile.orientation.quarter_turns)
    return ExactProfileVector3D(Decimal(0), y, z)


@dataclass(frozen=True, slots=True)
class ProfileSectionGeometryAdapter:
    """Exact values required to call one unchanged standard-section float builder."""

    section_family: SectionFamily
    geometry_factory_name: str
    dimension_values: tuple[tuple[str, Decimal], ...]
    member_length: Decimal
    section_datum_offset_y: Decimal
    section_datum_offset_z: Decimal

    def __post_init__(self) -> None:
        require_enum(
            self.section_family,
            SectionFamily,
            "ProfileSectionGeometryAdapter.section_family",
        )
        validate_identifier(
            self.geometry_factory_name,
            "ProfileSectionGeometryAdapter.geometry_factory_name",
        )
        require_tuple(self.dimension_values, "ProfileSectionGeometryAdapter.dimension_values")
        if not self.dimension_values:
            raise ValueError("A profile geometry adapter requires cross-section dimensions.")
        names: list[str] = []
        for item in self.dimension_values:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("Adapter dimension values must be immutable name/value pairs.")
            name, value = item
            validate_identifier(name, "ProfileSectionGeometryAdapter dimension name")
            _decimal(value, f"ProfileSectionGeometryAdapter.{name}", positive=True)
            names.append(name)
        if len(set(names)) != len(names):
            raise ValueError("Adapter dimension names must be unique.")
        _decimal(self.member_length, "ProfileSectionGeometryAdapter.member_length", positive=True)
        _decimal(
            self.section_datum_offset_y,
            "ProfileSectionGeometryAdapter.section_datum_offset_y",
        )
        _decimal(
            self.section_datum_offset_z,
            "ProfileSectionGeometryAdapter.section_datum_offset_z",
        )


def profile_section_geometry_adapter(profile: MemberProfile) -> ProfileSectionGeometryAdapter:
    """Return a Decimal-preserving recipe for the accepted float geometry boundary."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    dimensions = profile.dimensions
    zero = Decimal(0)
    values: tuple[tuple[str, Decimal], ...]
    if isinstance(dimensions, AngleProfileDimensions):
        factory = "create_angle_geometry"
        values = (
            ("leg_y", dimensions.leg_y),
            ("leg_z", dimensions.leg_z),
            ("thickness", dimensions.thickness),
        )
        offset_y = dimensions.leg_y / Decimal(2)
        offset_z = dimensions.leg_z / Decimal(2)
    elif isinstance(dimensions, ChannelProfileDimensions):
        factory = "create_channel_geometry"
        values = _flanged_adapter_values(dimensions)
        offset_y = dimensions.flange_width / Decimal(2)
        offset_z = zero
    elif isinstance(dimensions, WideFlangeIProfileDimensions):
        factory = "create_wide_flange_geometry"
        values = _flanged_adapter_values(dimensions)
        offset_y = offset_z = zero
    elif isinstance(dimensions, RectangularHollowProfileDimensions):
        factory = "create_rectangular_tube_geometry"
        values = (
            ("outside_width", dimensions.width),
            ("outside_depth", dimensions.depth),
            ("wall_thickness", dimensions.wall_thickness),
        )
        offset_y = offset_z = zero
    elif isinstance(dimensions, SolidRectangularProfileDimensions):
        factory = "create_plate_geometry"
        values = (("width", dimensions.width), ("thickness", dimensions.depth))
        offset_y = offset_z = zero
    elif isinstance(dimensions, FlatPlateProfileDimensions):
        factory = "create_plate_geometry"
        values = (("width", dimensions.width), ("thickness", dimensions.thickness))
        offset_y = offset_z = zero
    elif isinstance(dimensions, RoundHollowProfileDimensions):
        factory = "create_round_tube_geometry"
        values = (
            ("outer_diameter", dimensions.outer_diameter),
            ("wall_thickness", dimensions.wall_thickness),
        )
        offset_y = offset_z = zero
    else:  # pragma: no cover - MemberProfile validates the closed dimensions union
        raise TypeError("Unsupported profile dimensions.")
    return ProfileSectionGeometryAdapter(
        profile.section_family,
        factory,
        values,
        dimensions.member_length,
        offset_y,
        offset_z,
    )


def _flanged_adapter_values(
    dimensions: ChannelProfileDimensions | WideFlangeIProfileDimensions,
) -> tuple[tuple[str, Decimal], ...]:
    return (
        ("overall_depth", dimensions.depth),
        ("flange_width", dimensions.flange_width),
        ("web_thickness", dimensions.web_thickness),
        ("flange_thickness", dimensions.flange_thickness),
    )


def profile_surface_registry(profile: MemberProfile) -> tuple[ProfileSurfaceDefinition, ...]:
    """Derive every selectable exact local surface for one validated profile."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    definitions = _base_surface_registry(profile.dimensions)
    return tuple(_rotate_surface(item, profile.orientation) for item in definitions)


def resolve_profile_surface(profile: MemberProfile) -> ProfileSurfaceDefinition:
    """Resolve the profile's selected surface without a family fallback."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    if profile.selected_surface is None:
        raise ValueError(DIRECT_TEE_CURVED_SURFACE_REASON)
    return next(
        item
        for item in profile_surface_registry(profile)
        if item.surface_id is profile.selected_surface
    )


def require_direct_tee_profile_surface(profile: MemberProfile) -> ProfileSurfaceDefinition:
    """Return a real flat Tee-stem surface or reject curved/unsupported contact."""

    return resolve_profile_surface(profile)


def _point_within_bounds(point: ExactProfileVector3D, bounds: ProfileLocalBounds3D) -> bool:
    return (
        bounds.min_x <= point.x <= bounds.max_x
        and bounds.min_y <= point.y <= bounds.max_y
        and bounds.min_z <= point.z <= bounds.max_z
    )


def resolve_angle_leg_bolt_path(
    profile: MemberProfile,
    outer_surface_point_local: ExactProfileVector3D,
) -> AngleLegBoltPathResolution:
    """Resolve one exact Angle outer-face point to its finite exposed opposing face."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    if profile.family is not MemberProfileFamily.ANGLE:
        raise ValueError("Angle leg bolt-path resolution requires an Angle profile.")
    if not isinstance(outer_surface_point_local, ExactProfileVector3D):
        raise TypeError("outer_surface_point_local must be an ExactProfileVector3D.")
    surface = resolve_profile_surface(profile)
    if not _point_within_bounds(outer_surface_point_local, surface.contact_bounds):
        return AngleLegBoltPathResolution(
            surface.surface_id,
            outer_surface_point_local,
            False,
            None,
            None,
            None,
            AngleLegBoltPathReason.OUTSIDE_SELECTED_LEG_SURFACE,
        )
    matches = tuple(
        (bounds, opposing_patch_id)
        for bounds, opposing_patch_id in zip(
            surface.penetration_bounds,
            surface.opposing_patch_ids,
            strict=True,
        )
        if _point_within_bounds(outer_surface_point_local, bounds)
    )
    if not matches:
        return AngleLegBoltPathResolution(
            surface.surface_id,
            outer_surface_point_local,
            False,
            None,
            None,
            None,
            AngleLegBoltPathReason.NO_FINITE_EXPOSED_OPPOSING_BROAD_FACE,
        )
    if len(matches) != 1:
        return AngleLegBoltPathResolution(
            surface.surface_id,
            outer_surface_point_local,
            False,
            None,
            None,
            None,
            AngleLegBoltPathReason.AMBIGUOUS_FINITE_EXPOSED_OPPOSING_BROAD_FACE,
        )
    _, opposing_patch_id = matches[0]
    opposing_point = (
        ExactProfileVector3D(
            outer_surface_point_local.x,
            surface.opposite_plane_coordinate,
            outer_surface_point_local.z,
        )
        if surface.plane_axis is PrincipalAxisFamily.Y
        else ExactProfileVector3D(
            outer_surface_point_local.x,
            outer_surface_point_local.y,
            surface.opposite_plane_coordinate,
        )
    )
    return AngleLegBoltPathResolution(
        surface.surface_id,
        outer_surface_point_local,
        True,
        opposing_patch_id,
        opposing_point,
        surface.layer_thickness,
        None,
    )


def _complete_disk_within_bounds(
    point: ExactProfileVector3D,
    bounds: ProfileLocalBounds3D,
    plane_axis: PrincipalAxisFamily,
    radius: Decimal,
) -> bool:
    if plane_axis is PrincipalAxisFamily.Y:
        ranges = ((bounds.min_x, point.x, bounds.max_x), (bounds.min_z, point.z, bounds.max_z))
    else:
        ranges = ((bounds.min_x, point.x, bounds.max_x), (bounds.min_y, point.y, bounds.max_y))
    return all(
        minimum + radius <= coordinate <= maximum - radius
        for minimum, coordinate, maximum in ranges
    )


def resolve_profile_wall_bolt_path(
    profile: MemberProfile,
    outer_surface_point_local: ExactProfileVector3D,
    hole_radius: Decimal,
) -> ProfileWallBoltPathResolution:
    """Resolve one exact Channel, W/I, or RHS wall footprint to its exposed inner face."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    supported = {
        MemberProfileFamily.CHANNEL,
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
    }
    if profile.family not in supported:
        raise ValueError("Profile wall bolt-path resolution requires Channel, W/I, or RHS.")
    if not isinstance(outer_surface_point_local, ExactProfileVector3D):
        raise TypeError("outer_surface_point_local must be an ExactProfileVector3D.")
    radius = _decimal(hole_radius, "hole_radius")
    if radius < 0:
        raise ValueError("hole_radius must be nonnegative.")
    surface = resolve_profile_surface(profile)
    qualifications = (
        (INTERNAL_FASTENER_ACCESS_REQUIRED,)
        if profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
        else ()
    )
    if not _point_within_bounds(outer_surface_point_local, surface.contact_bounds):
        return ProfileWallBoltPathResolution(
            surface.surface_id,
            outer_surface_point_local,
            False,
            None,
            None,
            None,
            qualifications,
            ProfileWallBoltPathReason.OUTSIDE_SELECTED_PROFILE_SURFACE,
        )
    matches = tuple(
        (bounds, opposing_patch_id)
        for bounds, opposing_patch_id in zip(
            surface.penetration_bounds,
            surface.opposing_patch_ids,
            strict=True,
        )
        if _complete_disk_within_bounds(
            outer_surface_point_local,
            bounds,
            surface.plane_axis,
            radius,
        )
    )
    if len(matches) != 1:
        return ProfileWallBoltPathResolution(
            surface.surface_id,
            outer_surface_point_local,
            False,
            None,
            None,
            None,
            qualifications,
            ProfileWallBoltPathReason.NO_UNIQUE_EXPOSED_OPPOSING_BROAD_FACE,
        )
    _, opposing_patch_id = matches[0]
    opposing_point = (
        ExactProfileVector3D(
            outer_surface_point_local.x,
            surface.opposite_plane_coordinate,
            outer_surface_point_local.z,
        )
        if surface.plane_axis is PrincipalAxisFamily.Y
        else ExactProfileVector3D(
            outer_surface_point_local.x,
            outer_surface_point_local.y,
            surface.opposite_plane_coordinate,
        )
    )
    return ProfileWallBoltPathResolution(
        surface.surface_id,
        outer_surface_point_local,
        True,
        opposing_patch_id,
        opposing_point,
        surface.layer_thickness,
        qualifications,
        None,
    )


def _half_length(dimensions: MemberProfileDimensions) -> Decimal:
    return dimensions.member_length / Decimal(2)


def _bounds(
    dimensions: MemberProfileDimensions,
    *,
    min_y: Decimal,
    max_y: Decimal,
    min_z: Decimal,
    max_z: Decimal,
) -> ProfileLocalBounds3D:
    half = _half_length(dimensions)
    return ProfileLocalBounds3D(-half, half, min_y, max_y, min_z, max_z)


def _surface(
    surface_id: MemberProfileSurfaceId,
    axis: PrincipalAxisFamily,
    coordinate: Decimal,
    normal_y: int,
    normal_z: int,
    contact: ProfileLocalBounds3D,
    penetration: tuple[ProfileLocalBounds3D, ...],
    role: PhysicalSectionElementRole,
    outside_patch_id: str,
    opposing_patch_ids: tuple[str, ...],
    opposite: Decimal,
) -> ProfileSurfaceDefinition:
    return ProfileSurfaceDefinition(
        surface_id,
        axis,
        coordinate,
        ExactProfileVector3D(Decimal(0), Decimal(normal_y), Decimal(normal_z)),
        contact,
        penetration,
        role,
        outside_patch_id,
        opposing_patch_ids,
        opposite,
    )


def _base_surface_registry(
    dimensions: MemberProfileDimensions,
) -> tuple[ProfileSurfaceDefinition, ...]:
    zero = Decimal(0)
    two = Decimal(2)
    if isinstance(dimensions, AngleProfileDimensions):
        return (
            _surface(
                MemberProfileSurfaceId.LEG_Y_OUTER,
                PrincipalAxisFamily.Z,
                zero,
                0,
                -1,
                _bounds(dimensions, min_y=zero, max_y=dimensions.leg_y, min_z=zero, max_z=zero),
                (
                    _bounds(
                        dimensions,
                        min_y=dimensions.thickness,
                        max_y=dimensions.leg_y,
                        min_z=zero,
                        max_z=zero,
                    ),
                ),
                PhysicalSectionElementRole.LEG_1,
                "LEG_1:EXTERIOR_TT_BROAD",
                ("LEG_1:OPEN_AREA_TT_BROAD",),
                dimensions.thickness,
            ),
            _surface(
                MemberProfileSurfaceId.LEG_Z_OUTER,
                PrincipalAxisFamily.Y,
                zero,
                -1,
                0,
                _bounds(dimensions, min_y=zero, max_y=zero, min_z=zero, max_z=dimensions.leg_z),
                (
                    _bounds(
                        dimensions,
                        min_y=zero,
                        max_y=zero,
                        min_z=dimensions.thickness,
                        max_z=dimensions.leg_z,
                    ),
                ),
                PhysicalSectionElementRole.LEG_2,
                "LEG_2:EXTERIOR_TT_BROAD",
                ("LEG_2:OPEN_AREA_TT_BROAD",),
                dimensions.thickness,
            ),
        )
    if isinstance(dimensions, ChannelProfileDimensions):
        half_depth = dimensions.depth / two
        clear = half_depth - dimensions.flange_thickness
        return (
            _surface(
                MemberProfileSurfaceId.WEB_OUTER,
                PrincipalAxisFamily.Y,
                zero,
                -1,
                0,
                _bounds(dimensions, min_y=zero, max_y=zero, min_z=-half_depth, max_z=half_depth),
                (_bounds(dimensions, min_y=zero, max_y=zero, min_z=-clear, max_z=clear),),
                PhysicalSectionElementRole.WEB,
                "WEB:EXTERIOR_BACK_BROAD",
                ("WEB:VOID_FACING_INNER_BROAD",),
                dimensions.web_thickness,
            ),
            _surface(
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
                PrincipalAxisFamily.Z,
                half_depth,
                0,
                1,
                _bounds(
                    dimensions,
                    min_y=zero,
                    max_y=dimensions.flange_width,
                    min_z=half_depth,
                    max_z=half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=dimensions.web_thickness,
                        max_y=dimensions.flange_width,
                        min_z=half_depth,
                        max_z=half_depth,
                    ),
                ),
                PhysicalSectionElementRole.TOP_FLANGE,
                "TOP_FLANGE:OUTER_BROAD",
                ("TOP_FLANGE:INNER_VOID_STRIP",),
                clear,
            ),
            _surface(
                MemberProfileSurfaceId.FLANGE_NEG_OUTER,
                PrincipalAxisFamily.Z,
                -half_depth,
                0,
                -1,
                _bounds(
                    dimensions,
                    min_y=zero,
                    max_y=dimensions.flange_width,
                    min_z=-half_depth,
                    max_z=-half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=dimensions.web_thickness,
                        max_y=dimensions.flange_width,
                        min_z=-half_depth,
                        max_z=-half_depth,
                    ),
                ),
                PhysicalSectionElementRole.BOTTOM_FLANGE,
                "BOTTOM_FLANGE:OUTER_BROAD",
                ("BOTTOM_FLANGE:INNER_VOID_STRIP",),
                -clear,
            ),
        )
    if isinstance(dimensions, WideFlangeIProfileDimensions):
        half_depth = dimensions.depth / two
        half_width = dimensions.flange_width / two
        half_web = dimensions.web_thickness / two
        clear = half_depth - dimensions.flange_thickness
        common = (
            _surface(
                MemberProfileSurfaceId.WEB_POS_FACE,
                PrincipalAxisFamily.Y,
                half_web,
                1,
                0,
                _bounds(dimensions, min_y=half_web, max_y=half_web, min_z=-clear, max_z=clear),
                (_bounds(dimensions, min_y=half_web, max_y=half_web, min_z=-clear, max_z=clear),),
                PhysicalSectionElementRole.WEB,
                "WEB:POSITIVE_TT_BROAD",
                ("WEB:NEGATIVE_TT_BROAD",),
                -half_web,
            ),
            _surface(
                MemberProfileSurfaceId.WEB_NEG_FACE,
                PrincipalAxisFamily.Y,
                -half_web,
                -1,
                0,
                _bounds(dimensions, min_y=-half_web, max_y=-half_web, min_z=-clear, max_z=clear),
                (_bounds(dimensions, min_y=-half_web, max_y=-half_web, min_z=-clear, max_z=clear),),
                PhysicalSectionElementRole.WEB,
                "WEB:NEGATIVE_TT_BROAD",
                ("WEB:POSITIVE_TT_BROAD",),
                half_web,
            ),
        )

        def flange_surface(
            surface_id: MemberProfileSurfaceId,
            coordinate: Decimal,
            sign: int,
            role: PhysicalSectionElementRole,
            element_id: str,
            opposite: Decimal,
        ) -> ProfileSurfaceDefinition:
            contact = _bounds(
                dimensions,
                min_y=-half_width,
                max_y=half_width,
                min_z=coordinate,
                max_z=coordinate,
            )
            penetration = (
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=-half_web,
                    min_z=coordinate,
                    max_z=coordinate,
                ),
                _bounds(
                    dimensions,
                    min_y=half_web,
                    max_y=half_width,
                    min_z=coordinate,
                    max_z=coordinate,
                ),
            )
            return _surface(
                surface_id,
                PrincipalAxisFamily.Z,
                coordinate,
                0,
                sign,
                contact,
                penetration,
                role,
                f"{element_id}:OUTER_TT_BROAD",
                (
                    f"{element_id}:INNER_NEGATIVE_CW_STRIP",
                    f"{element_id}:INNER_POSITIVE_CW_STRIP",
                ),
                opposite,
            )

        return (
            *common,
            flange_surface(
                MemberProfileSurfaceId.FLANGE_POS_OUTER,
                half_depth,
                1,
                PhysicalSectionElementRole.TOP_FLANGE,
                "TOP_FLANGE",
                clear,
            ),
            flange_surface(
                MemberProfileSurfaceId.FLANGE_NEG_OUTER,
                -half_depth,
                -1,
                PhysicalSectionElementRole.BOTTOM_FLANGE,
                "BOTTOM_FLANGE",
                -clear,
            ),
        )
    if isinstance(dimensions, RectangularHollowProfileDimensions):
        half_depth = dimensions.depth / two
        half_width = dimensions.width / two
        clear_z = half_depth - dimensions.wall_thickness
        clear_y = half_width - dimensions.wall_thickness
        return (
            _surface(
                MemberProfileSurfaceId.Y_POS_FACE,
                PrincipalAxisFamily.Y,
                half_width,
                1,
                0,
                _bounds(
                    dimensions,
                    min_y=half_width,
                    max_y=half_width,
                    min_z=-half_depth,
                    max_z=half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=half_width,
                        max_y=half_width,
                        min_z=-clear_z,
                        max_z=clear_z,
                    ),
                ),
                PhysicalSectionElementRole.SIDE_WALL_2,
                "SIDE_WALL_2:EXTERIOR_BROAD",
                ("SIDE_WALL_2:VOID_FACING_BROAD",),
                clear_y,
            ),
            _surface(
                MemberProfileSurfaceId.Y_NEG_FACE,
                PrincipalAxisFamily.Y,
                -half_width,
                -1,
                0,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=-half_width,
                    min_z=-half_depth,
                    max_z=half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=-half_width,
                        max_y=-half_width,
                        min_z=-clear_z,
                        max_z=clear_z,
                    ),
                ),
                PhysicalSectionElementRole.SIDE_WALL_1,
                "SIDE_WALL_1:EXTERIOR_BROAD",
                ("SIDE_WALL_1:VOID_FACING_BROAD",),
                -clear_y,
            ),
            _surface(
                MemberProfileSurfaceId.Z_POS_FACE,
                PrincipalAxisFamily.Z,
                half_depth,
                0,
                1,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=half_width,
                    min_z=half_depth,
                    max_z=half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=-clear_y,
                        max_y=clear_y,
                        min_z=half_depth,
                        max_z=half_depth,
                    ),
                ),
                PhysicalSectionElementRole.TOP_WALL,
                "TOP_WALL:EXTERIOR_BROAD",
                ("TOP_WALL:VOID_FACING_BROAD",),
                clear_z,
            ),
            _surface(
                MemberProfileSurfaceId.Z_NEG_FACE,
                PrincipalAxisFamily.Z,
                -half_depth,
                0,
                -1,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=half_width,
                    min_z=-half_depth,
                    max_z=-half_depth,
                ),
                (
                    _bounds(
                        dimensions,
                        min_y=-clear_y,
                        max_y=clear_y,
                        min_z=-half_depth,
                        max_z=-half_depth,
                    ),
                ),
                PhysicalSectionElementRole.BOTTOM_WALL,
                "BOTTOM_WALL:EXTERIOR_BROAD",
                ("BOTTOM_WALL:VOID_FACING_BROAD",),
                -clear_z,
            ),
        )
    if isinstance(dimensions, SolidRectangularProfileDimensions):
        half_depth = dimensions.depth / two
        half_width = dimensions.width / two

        def solid_surface(
            surface_id: MemberProfileSurfaceId,
            axis: PrincipalAxisFamily,
            coordinate: Decimal,
            normal_y: int,
            normal_z: int,
            contact: ProfileLocalBounds3D,
            opposite: Decimal,
        ) -> ProfileSurfaceDefinition:
            return _surface(
                surface_id,
                axis,
                coordinate,
                normal_y,
                normal_z,
                contact,
                (contact,),
                PhysicalSectionElementRole.PLATE,
                f"SOLID_RECTANGULAR_SECTION:{surface_id.value}",
                (
                    "SOLID_RECTANGULAR_SECTION:"
                    f"{_RECTANGULAR_OPPOSING_SURFACE_IDS[surface_id].value}",
                ),
                opposite,
            )

        return (
            solid_surface(
                MemberProfileSurfaceId.Y_POS_FACE,
                PrincipalAxisFamily.Y,
                half_width,
                1,
                0,
                _bounds(
                    dimensions,
                    min_y=half_width,
                    max_y=half_width,
                    min_z=-half_depth,
                    max_z=half_depth,
                ),
                -half_width,
            ),
            solid_surface(
                MemberProfileSurfaceId.Y_NEG_FACE,
                PrincipalAxisFamily.Y,
                -half_width,
                -1,
                0,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=-half_width,
                    min_z=-half_depth,
                    max_z=half_depth,
                ),
                half_width,
            ),
            solid_surface(
                MemberProfileSurfaceId.Z_POS_FACE,
                PrincipalAxisFamily.Z,
                half_depth,
                0,
                1,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=half_width,
                    min_z=half_depth,
                    max_z=half_depth,
                ),
                -half_depth,
            ),
            solid_surface(
                MemberProfileSurfaceId.Z_NEG_FACE,
                PrincipalAxisFamily.Z,
                -half_depth,
                0,
                -1,
                _bounds(
                    dimensions,
                    min_y=-half_width,
                    max_y=half_width,
                    min_z=-half_depth,
                    max_z=-half_depth,
                ),
                half_depth,
            ),
        )
    if isinstance(dimensions, FlatPlateProfileDimensions):
        half_width = dimensions.width / two
        half_thickness = dimensions.thickness / two
        contact_pos = _bounds(
            dimensions,
            min_y=-half_width,
            max_y=half_width,
            min_z=half_thickness,
            max_z=half_thickness,
        )
        contact_neg = _bounds(
            dimensions,
            min_y=-half_width,
            max_y=half_width,
            min_z=-half_thickness,
            max_z=-half_thickness,
        )
        return (
            _surface(
                MemberProfileSurfaceId.FACE_POS,
                PrincipalAxisFamily.Z,
                half_thickness,
                0,
                1,
                contact_pos,
                (contact_pos,),
                PhysicalSectionElementRole.PLATE,
                "PLATE:POSITIVE_TT_BROAD",
                ("PLATE:NEGATIVE_TT_BROAD",),
                -half_thickness,
            ),
            _surface(
                MemberProfileSurfaceId.FACE_NEG,
                PrincipalAxisFamily.Z,
                -half_thickness,
                0,
                -1,
                contact_neg,
                (contact_neg,),
                PhysicalSectionElementRole.PLATE,
                "PLATE:NEGATIVE_TT_BROAD",
                ("PLATE:POSITIVE_TT_BROAD",),
                half_thickness,
            ),
        )
    if isinstance(dimensions, RoundHollowProfileDimensions):
        return ()
    raise TypeError("Unsupported profile dimensions.")


def _rotate_yz(y: Decimal, z: Decimal, quarter_turns: int) -> tuple[Decimal, Decimal]:
    return (
        (y, z),
        (-z, y),
        (-y, -z),
        (z, -y),
    )[quarter_turns]


def _rotate_vector(
    value: ExactProfileVector3D,
    orientation: MemberProfileOrientation,
) -> ExactProfileVector3D:
    y, z = _rotate_yz(value.y, value.z, orientation.quarter_turns)
    return ExactProfileVector3D(value.x, y, z)


def _rotate_bounds(
    bounds: ProfileLocalBounds3D,
    orientation: MemberProfileOrientation,
) -> ProfileLocalBounds3D:
    points = tuple(
        _rotate_yz(y, z, orientation.quarter_turns)
        for y in (bounds.min_y, bounds.max_y)
        for z in (bounds.min_z, bounds.max_z)
    )
    ys = tuple(point[0] for point in points)
    zs = tuple(point[1] for point in points)
    return ProfileLocalBounds3D(
        bounds.min_x,
        bounds.max_x,
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


def _rotate_surface(
    surface: ProfileSurfaceDefinition,
    orientation: MemberProfileOrientation,
) -> ProfileSurfaceDefinition:
    require_enum(orientation, MemberProfileOrientation, "orientation")
    if orientation is MemberProfileOrientation.ROTATION_0:
        return surface
    normal = _rotate_vector(surface.local_outward_normal, orientation)
    contact = _rotate_bounds(surface.contact_bounds, orientation)
    penetration = tuple(_rotate_bounds(item, orientation) for item in surface.penetration_bounds)
    axis = PrincipalAxisFamily.Y if normal.y != 0 else PrincipalAxisFamily.Z
    coordinate = contact.min_y if axis is PrincipalAxisFamily.Y else contact.min_z
    if surface.plane_axis is PrincipalAxisFamily.Y:
        opposite_y, opposite_z = _rotate_yz(
            surface.opposite_plane_coordinate,
            Decimal(0),
            orientation.quarter_turns,
        )
    else:
        opposite_y, opposite_z = _rotate_yz(
            Decimal(0),
            surface.opposite_plane_coordinate,
            orientation.quarter_turns,
        )
    opposite = opposite_y if axis is PrincipalAxisFamily.Y else opposite_z
    return ProfileSurfaceDefinition(
        surface.surface_id,
        axis,
        coordinate,
        normal,
        contact,
        penetration,
        surface.physical_element_role,
        surface.outside_patch_id,
        surface.opposing_patch_ids,
        opposite,
    )


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _dimensions_payload(dimensions: MemberProfileDimensions) -> dict[str, str]:
    return {
        field.name: _canonical_decimal(getattr(dimensions, field.name))
        for field in fields(dimensions)
    }


def _geometry_identity_payload(profile: MemberProfile) -> object:
    return {
        "schema_version": MEMBER_PROFILE_SCHEMA_VERSION,
        "family": profile.family.value,
        "size_basis": profile.size_basis.value,
        "dimensions": _dimensions_payload(profile.dimensions),
        "orientation": profile.orientation.value,
    }


def canonical_profile_geometry_json(profile: MemberProfile) -> str:
    """Return canonical exact profile geometry, independent from member role."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    return json.dumps(
        _geometry_identity_payload(profile),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def profile_geometry_fingerprint(profile: MemberProfile) -> str:
    return hashlib.sha256(canonical_profile_geometry_json(profile).encode("utf-8")).hexdigest()


def canonical_member_profile_json(profile: MemberProfile) -> str:
    """Return canonical full engineering identity with no display-only state."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    material_orientation = profile.material_orientation
    payload = {
        "schema_version": MEMBER_PROFILE_SCHEMA_VERSION,
        "id": profile.id,
        "member_id": profile.member_id,
        "role": profile.role.value,
        "geometry": _geometry_identity_payload(profile),
        "material_kind": profile.material_kind.value,
        "material_orientation": (
            None
            if material_orientation is None
            else {
                "frame_kind": material_orientation.coordinate_frame.kind.value,
                "frame_owner_id": material_orientation.coordinate_frame.owner_id,
                "lengthwise_axis": material_orientation.lengthwise_axis.value,
            }
        ),
        "selected_surface": (
            None if profile.selected_surface is None else profile.selected_surface.value
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def member_profile_fingerprint(profile: MemberProfile) -> str:
    return hashlib.sha256(canonical_member_profile_json(profile).encode("utf-8")).hexdigest()


__all__ = (
    "DIRECT_TEE_CURVED_SURFACE_REASON",
    "INTERNAL_FASTENER_ACCESS_REQUIRED",
    "MEMBER_PROFILE_SCHEMA_VERSION",
    "AngleLegBoltPathReason",
    "AngleLegBoltPathResolution",
    "AngleProfileDimensions",
    "ChannelProfileDimensions",
    "ExactProfileVector3D",
    "FlatPlateProfileDimensions",
    "MemberProfile",
    "MemberProfileDimensions",
    "MemberProfileFamily",
    "MemberProfileOrientation",
    "MemberProfileSizeBasis",
    "MemberProfileSurfaceId",
    "ProfileLocalBounds3D",
    "ProfileSectionGeometryAdapter",
    "ProfileSurfaceDefinition",
    "ProfileWallBoltPathReason",
    "ProfileWallBoltPathResolution",
    "RectangularHollowProfileDimensions",
    "RoundHollowProfileDimensions",
    "SolidRectangularProfileDimensions",
    "WideFlangeIProfileDimensions",
    "canonical_member_profile_json",
    "canonical_profile_geometry_json",
    "member_profile_fingerprint",
    "profile_geometry_fingerprint",
    "profile_member_axis_reference",
    "profile_section_geometry_adapter",
    "profile_surface_registry",
    "require_direct_tee_profile_surface",
    "resolve_angle_leg_bolt_path",
    "resolve_profile_surface",
    "resolve_profile_wall_bolt_path",
    "section_family_for_profile",
    "selectable_profile_surfaces",
)
