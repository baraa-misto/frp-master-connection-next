"""Stage 3.3C1 exact rectangular-section full-through bolt architecture.

Physical path segments are deliberately separate from the accepted resistance-layer
stack.  A hollow-section cavity is therefore real shank geometry but can never become
a material, demand, or resistance input.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.domain.member_profile import (
    ExactProfileVector3D,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    ProfileLocalBounds3D,
    ProfileSurfaceDefinition,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    profile_surface_registry,
)
from frp_master_connection.domain.validation import require_enum, require_tuple, validate_identifier
from frp_master_connection.domain.values import PrincipalAxisFamily

RECTANGULAR_FULL_THROUGH_BOLT_SCHEMA_VERSION = "3.3C1-RC1"


class PhysicalBoltPathSegmentKind(StrEnum):
    MATERIAL_LAYER = "MATERIAL_LAYER"
    FREE_SHANK_SPAN = "FREE_SHANK_SPAN"


class RectangularLocalMechanicsLimitation(StrEnum):
    RHS_LOCAL_WALL_RESPONSE = "RHS_LOCAL_WALL_RESPONSE"
    RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT = "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT"
    SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY = (
        "SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY"
    )


class FullThroughHardwareLocation(StrEnum):
    EXTERIOR_NEAR_SIDE = "EXTERIOR_NEAR_SIDE"
    EXTERIOR_FAR_SIDE = "EXTERIOR_FAR_SIDE"


class RectangularContainmentStatus(StrEnum):
    VALID = "VALID"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


def _decimal(value: object, field_name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite.")
    if positive and value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def _canonical_decimal(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


_CARDINAL_VECTORS = {
    (Decimal(1), Decimal(0), Decimal(0)),
    (Decimal(-1), Decimal(0), Decimal(0)),
    (Decimal(0), Decimal(1), Decimal(0)),
    (Decimal(0), Decimal(-1), Decimal(0)),
    (Decimal(0), Decimal(0), Decimal(1)),
    (Decimal(0), Decimal(0), Decimal(-1)),
}


def _vector_tuple(value: ExactProfileVector3D) -> tuple[Decimal, Decimal, Decimal]:
    return (value.x, value.y, value.z)


@dataclass(frozen=True, slots=True)
class RectangularMaterialBasis:
    """Exact orthogonal LW/CW/TT directions in the authoritative member frame."""

    lengthwise: ExactProfileVector3D
    crosswise: ExactProfileVector3D
    through_thickness: ExactProfileVector3D

    def __post_init__(self) -> None:
        values = (self.lengthwise, self.crosswise, self.through_thickness)
        if any(not isinstance(item, ExactProfileVector3D) for item in values):
            raise TypeError("Rectangular material basis axes must be exact profile vectors.")
        vectors = tuple(_vector_tuple(item) for item in values)
        if any(item not in _CARDINAL_VECTORS for item in vectors):
            raise ValueError("Rectangular material basis axes must be signed cardinal vectors.")
        families = tuple(
            next(index for index, value in enumerate(item) if value) for item in vectors
        )
        if len(set(families)) != 3:
            raise ValueError("Rectangular material basis axes must be mutually orthogonal.")


SOLID_RECTANGULAR_MATERIAL_BASIS = RectangularMaterialBasis(
    ExactProfileVector3D(Decimal(1), Decimal(0), Decimal(0)),
    ExactProfileVector3D(Decimal(0), Decimal(1), Decimal(0)),
    ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(1)),
)


def solid_rectangular_material_basis(profile: MemberProfile) -> RectangularMaterialBasis:
    """Return the controlled stable SRS volume basis LW=+X, CW=+Y, TT=+Z."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    if profile.family is not MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        raise ValueError("The solid rectangular volume basis requires an SRS profile.")
    return SOLID_RECTANGULAR_MATERIAL_BASIS


@dataclass(frozen=True, slots=True)
class RectangularFaceLocalFrame:
    """One exact common local in-plane frame shared by opposing faces."""

    origin: ExactProfileVector3D
    normal: ExactProfileVector3D
    u_axis: ExactProfileVector3D
    v_axis: ExactProfileVector3D

    def __post_init__(self) -> None:
        values = (self.origin, self.normal, self.u_axis, self.v_axis)
        if any(not isinstance(item, ExactProfileVector3D) for item in values):
            raise TypeError("Rectangular face-frame values must be exact profile vectors.")
        axes = tuple(_vector_tuple(item) for item in values[1:])
        if any(item not in _CARDINAL_VECTORS for item in axes):
            raise ValueError("Rectangular face-frame axes must be signed cardinal vectors.")
        families = tuple(next(index for index, value in enumerate(item) if value) for item in axes)
        if len(set(families)) != 3:
            raise ValueError("Rectangular face-frame axes must be mutually orthogonal.")


@dataclass(frozen=True, slots=True)
class RectangularOpposingFacePair:
    """Exact selected/opposite exterior surfaces for RHS or SRS traversal."""

    profile_family: MemberProfileFamily
    selected_surface: ProfileSurfaceDefinition
    opposite_surface: ProfileSurfaceDefinition
    selected_frame: RectangularFaceLocalFrame
    opposite_frame: RectangularFaceLocalFrame
    separation: Decimal

    def __post_init__(self) -> None:
        if self.profile_family not in {
            MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
            MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
        }:
            raise ValueError("An opposing rectangular face pair requires RHS or SRS.")
        if not isinstance(self.selected_surface, ProfileSurfaceDefinition) or not isinstance(
            self.opposite_surface, ProfileSurfaceDefinition
        ):
            raise TypeError("Opposing rectangular faces must be profile surface definitions.")
        if not isinstance(self.selected_frame, RectangularFaceLocalFrame) or not isinstance(
            self.opposite_frame, RectangularFaceLocalFrame
        ):
            raise TypeError("Opposing rectangular faces require exact local frames.")
        separation = _decimal(self.separation, "separation", positive=True)
        if self.selected_surface.plane_axis is not self.opposite_surface.plane_axis:
            raise ValueError("Opposing rectangular faces must use one exact plane axis.")
        actual = abs(
            self.selected_surface.plane_coordinate - self.opposite_surface.plane_coordinate
        )
        if separation != actual:
            raise ValueError("Opposing rectangular face separation must be exact.")
        selected_normal = _vector_tuple(self.selected_surface.local_outward_normal)
        opposite_normal = _vector_tuple(self.opposite_surface.local_outward_normal)
        if selected_normal != tuple(-item for item in opposite_normal):
            raise ValueError("Opposing rectangular exterior normals must be exact opposites.")
        if (
            self.selected_frame.u_axis != self.opposite_frame.u_axis
            or self.selected_frame.v_axis != self.opposite_frame.v_axis
        ):
            raise ValueError("Opposing faces must share one exact in-plane basis.")


_OPPOSING_RECTANGULAR_FACE = {
    MemberProfileSurfaceId.Y_POS_FACE: MemberProfileSurfaceId.Y_NEG_FACE,
    MemberProfileSurfaceId.Y_NEG_FACE: MemberProfileSurfaceId.Y_POS_FACE,
    MemberProfileSurfaceId.Z_POS_FACE: MemberProfileSurfaceId.Z_NEG_FACE,
    MemberProfileSurfaceId.Z_NEG_FACE: MemberProfileSurfaceId.Z_POS_FACE,
}


def _face_frame(surface: ProfileSurfaceDefinition) -> RectangularFaceLocalFrame:
    if surface.plane_axis is PrincipalAxisFamily.Y:
        v_axis = ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(1))
    else:
        v_axis = ExactProfileVector3D(Decimal(0), Decimal(1), Decimal(0))
    return RectangularFaceLocalFrame(
        surface.center,
        surface.local_outward_normal,
        ExactProfileVector3D(Decimal(1), Decimal(0), Decimal(0)),
        v_axis,
    )


def rectangular_opposing_face_pair(
    profile: MemberProfile,
    selected_surface_id: MemberProfileSurfaceId,
) -> RectangularOpposingFacePair:
    """Resolve an RHS/SRS exterior face and its exact opposite with no tolerance."""

    if not isinstance(profile, MemberProfile):
        raise TypeError("profile must be a MemberProfile.")
    if profile.family not in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        raise ValueError("Rectangular opposing-face resolution requires RHS or SRS.")
    require_enum(selected_surface_id, MemberProfileSurfaceId, "selected_surface_id")
    if selected_surface_id not in _OPPOSING_RECTANGULAR_FACE:
        raise ValueError("Selected surface must be one of the four rectangular exterior faces.")
    registry = {item.surface_id: item for item in profile_surface_registry(profile)}
    selected = registry[selected_surface_id]
    opposite = registry[_OPPOSING_RECTANGULAR_FACE[selected_surface_id]]
    return RectangularOpposingFacePair(
        profile.family,
        selected,
        opposite,
        _face_frame(selected),
        _face_frame(opposite),
        abs(selected.plane_coordinate - opposite.plane_coordinate),
    )


@dataclass(frozen=True, slots=True)
class PhysicalBoltPathSegment:
    """One ordered physical interval along a continuous bolt shank."""

    kind: PhysicalBoltPathSegmentKind
    identity: str
    length: Decimal
    entry_plane_id: str
    exit_plane_id: str
    material_region_id: str | None = None
    material_basis: RectangularMaterialBasis | None = None

    def __post_init__(self) -> None:
        require_enum(self.kind, PhysicalBoltPathSegmentKind, "PhysicalBoltPathSegment.kind")
        validate_identifier(self.identity, "PhysicalBoltPathSegment.identity")
        _decimal(self.length, "PhysicalBoltPathSegment.length", positive=True)
        validate_identifier(self.entry_plane_id, "PhysicalBoltPathSegment.entry_plane_id")
        validate_identifier(self.exit_plane_id, "PhysicalBoltPathSegment.exit_plane_id")
        if self.entry_plane_id == self.exit_plane_id:
            raise ValueError("A physical bolt-path segment requires distinct entry/exit planes.")
        if self.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER:
            if self.material_region_id is None:
                raise ValueError("A material-layer segment requires a material-region identity.")
            validate_identifier(
                self.material_region_id,
                "PhysicalBoltPathSegment.material_region_id",
            )
            if not isinstance(self.material_basis, RectangularMaterialBasis):
                raise TypeError("A material-layer segment requires an exact material basis.")
        elif self.material_region_id is not None or self.material_basis is not None:
            raise ValueError("A free shank span cannot carry material identity or axes.")

    @property
    def receives_bearing_demand(self) -> bool:
        return self.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER

    @property
    def receives_resistance_check(self) -> bool:
        return self.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER


@dataclass(frozen=True, slots=True)
class RectangularBoltAxis:
    """One authoritative bolt axis represented by one common opposing-face UV pair."""

    selected_face: MemberProfileSurfaceId
    opposite_face: MemberProfileSurfaceId
    local_u: Decimal
    local_v: Decimal

    def __post_init__(self) -> None:
        require_enum(self.selected_face, MemberProfileSurfaceId, "selected_face")
        require_enum(self.opposite_face, MemberProfileSurfaceId, "opposite_face")
        if _OPPOSING_RECTANGULAR_FACE.get(self.selected_face) is not self.opposite_face:
            raise ValueError("Bolt-axis faces must be an exact registered opposing pair.")
        _decimal(self.local_u, "local_u")
        _decimal(self.local_v, "local_v")

    @property
    def near_local_uv(self) -> tuple[Decimal, Decimal]:
        return (self.local_u, self.local_v)

    @property
    def far_local_uv(self) -> tuple[Decimal, Decimal]:
        return (self.local_u, self.local_v)


@dataclass(frozen=True, slots=True)
class FullThroughBoltPath:
    """One physical bolt, one axis, and an ordered material/free-span traversal."""

    bolt_id: str
    axis: RectangularBoltAxis
    segments: tuple[PhysicalBoltPathSegment, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.bolt_id, "FullThroughBoltPath.bolt_id")
        if not isinstance(self.axis, RectangularBoltAxis):
            raise TypeError("FullThroughBoltPath.axis must be a RectangularBoltAxis.")
        require_tuple(self.segments, "FullThroughBoltPath.segments")
        if not self.segments:
            raise ValueError("A full-through bolt path requires at least one physical segment.")
        if any(not isinstance(item, PhysicalBoltPathSegment) for item in self.segments):
            raise TypeError("Full-through path segments must be PhysicalBoltPathSegment values.")

    @property
    def shank_length(self) -> Decimal:
        return sum((item.length for item in self.segments), start=Decimal(0))

    @property
    def material_layers(self) -> tuple[PhysicalBoltPathSegment, ...]:
        """Return only engineering material layers for compatible resistance handoff."""

        return tuple(
            item
            for item in self.segments
            if item.kind is PhysicalBoltPathSegmentKind.MATERIAL_LAYER
        )

    @property
    def free_shank_spans(self) -> tuple[PhysicalBoltPathSegment, ...]:
        return tuple(
            item
            for item in self.segments
            if item.kind is PhysicalBoltPathSegmentKind.FREE_SHANK_SPAN
        )

    @property
    def physical_bolt_count(self) -> int:
        return 1

    @property
    def continuous_shank_count(self) -> int:
        return 1


def _rhs_wall_basis(axis: PrincipalAxisFamily) -> RectangularMaterialBasis:
    if axis is PrincipalAxisFamily.Y:
        crosswise = ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(1))
        through = ExactProfileVector3D(Decimal(0), Decimal(1), Decimal(0))
    else:
        crosswise = ExactProfileVector3D(Decimal(0), Decimal(1), Decimal(0))
        through = ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(1))
    return RectangularMaterialBasis(
        ExactProfileVector3D(Decimal(1), Decimal(0), Decimal(0)),
        crosswise,
        through,
    )


def _axis_for_pair(
    pair: RectangularOpposingFacePair,
    local_uv: tuple[Decimal, Decimal],
) -> RectangularBoltAxis:
    if not isinstance(local_uv, tuple) or len(local_uv) != 2:
        raise TypeError("local_uv must be an exact two-item tuple.")
    return RectangularBoltAxis(
        pair.selected_surface.surface_id,
        pair.opposite_surface.surface_id,
        _decimal(local_uv[0], "local_uv[0]"),
        _decimal(local_uv[1], "local_uv[1]"),
    )


def build_rhs_full_through_core(
    profile: MemberProfile,
    selected_surface_id: MemberProfileSurfaceId,
    *,
    bolt_id: str,
    local_uv: tuple[Decimal, Decimal],
    material_region_id: str,
) -> FullThroughBoltPath:
    """Build exact near-wall/cavity/far-wall RHS traversal for one bolt."""

    if not isinstance(profile, MemberProfile) or not isinstance(
        profile.dimensions, RectangularHollowProfileDimensions
    ):
        raise ValueError("RHS full-through construction requires an RHS member profile.")
    validate_identifier(material_region_id, "material_region_id")
    pair = rectangular_opposing_face_pair(profile, selected_surface_id)
    wall = profile.dimensions.wall_thickness
    cavity = pair.separation - Decimal(2) * wall
    if cavity <= 0:  # pragma: no cover - RHS dimensions already prove 2t < D
        raise ValueError("RHS full-through construction requires positive cavity depth.")
    selected = pair.selected_surface.surface_id.value
    opposite = pair.opposite_surface.surface_id.value
    near_inner = f"{selected}:INNER"
    far_inner = f"{opposite}:INNER"
    basis = _rhs_wall_basis(pair.selected_surface.plane_axis)
    segments = (
        PhysicalBoltPathSegment(
            PhysicalBoltPathSegmentKind.MATERIAL_LAYER,
            "NEAR_WALL",
            wall,
            selected,
            near_inner,
            material_region_id,
            basis,
        ),
        PhysicalBoltPathSegment(
            PhysicalBoltPathSegmentKind.FREE_SHANK_SPAN,
            "CAVITY",
            cavity,
            near_inner,
            far_inner,
        ),
        PhysicalBoltPathSegment(
            PhysicalBoltPathSegmentKind.MATERIAL_LAYER,
            "FAR_WALL",
            wall,
            far_inner,
            opposite,
            material_region_id,
            basis,
        ),
    )
    if (
        sum((item.length for item in segments), start=Decimal(0)) != pair.separation
    ):  # pragma: no cover
        raise AssertionError("RHS exact segment sum must equal exterior face separation.")
    return FullThroughBoltPath(bolt_id, _axis_for_pair(pair, local_uv), segments)


def build_srs_full_through_core(
    profile: MemberProfile,
    selected_surface_id: MemberProfileSurfaceId,
    *,
    bolt_id: str,
    local_uv: tuple[Decimal, Decimal],
    material_region_id: str,
) -> FullThroughBoltPath:
    """Build one continuous exact material segment through an SRS volume."""

    if not isinstance(profile, MemberProfile) or not isinstance(
        profile.dimensions, SolidRectangularProfileDimensions
    ):
        raise ValueError("SRS full-through construction requires an SRS member profile.")
    validate_identifier(material_region_id, "material_region_id")
    pair = rectangular_opposing_face_pair(profile, selected_surface_id)
    segment = PhysicalBoltPathSegment(
        PhysicalBoltPathSegmentKind.MATERIAL_LAYER,
        "SOLID_RECTANGULAR_SECTION",
        pair.separation,
        pair.selected_surface.surface_id.value,
        pair.opposite_surface.surface_id.value,
        material_region_id,
        solid_rectangular_material_basis(profile),
    )
    return FullThroughBoltPath(bolt_id, _axis_for_pair(pair, local_uv), (segment,))


def external_connector_layer(
    identity: str,
    length: Decimal,
    *,
    material_region_id: str,
    material_basis: RectangularMaterialBasis,
) -> PhysicalBoltPathSegment:
    """Create one explicit external connector material layer for later composition."""

    validate_identifier(identity, "identity")
    return PhysicalBoltPathSegment(
        PhysicalBoltPathSegmentKind.MATERIAL_LAYER,
        identity,
        length,
        f"{identity}:ENTRY",
        f"{identity}:EXIT",
        material_region_id,
        material_basis,
    )


def compose_external_connector_layers(
    core: FullThroughBoltPath,
    *,
    near_layers: tuple[PhysicalBoltPathSegment, ...] = (),
    far_layers: tuple[PhysicalBoltPathSegment, ...] = (),
) -> FullThroughBoltPath:
    """Prepend/append external material layers without duplicating bolt identity."""

    if not isinstance(core, FullThroughBoltPath):
        raise TypeError("core must be a FullThroughBoltPath.")
    require_tuple(near_layers, "near_layers")
    require_tuple(far_layers, "far_layers")
    external = (*near_layers, *far_layers)
    if any(not isinstance(item, PhysicalBoltPathSegment) for item in external):
        raise TypeError("External connector layers must be physical path segments.")
    if any(item.kind is not PhysicalBoltPathSegmentKind.MATERIAL_LAYER for item in external):
        raise ValueError("External connector composition accepts material layers only.")
    return FullThroughBoltPath(core.bolt_id, core.axis, (*near_layers, *core.segments, *far_layers))


@dataclass(frozen=True, slots=True)
class FullThroughBoltHardware:
    """External-only hardware and one continuous shank for a composed physical path."""

    bolt_id: str
    shank_length: Decimal
    head_location: FullThroughHardwareLocation
    nut_location: FullThroughHardwareLocation
    washer_locations: tuple[FullThroughHardwareLocation, ...]
    physical_bolt_count: int = 1
    continuous_shank_count: int = 1
    internal_hardware_count: int = 0

    def __post_init__(self) -> None:
        validate_identifier(self.bolt_id, "FullThroughBoltHardware.bolt_id")
        _decimal(self.shank_length, "FullThroughBoltHardware.shank_length", positive=True)
        require_enum(self.head_location, FullThroughHardwareLocation, "head_location")
        require_enum(self.nut_location, FullThroughHardwareLocation, "nut_location")
        require_tuple(self.washer_locations, "washer_locations")
        if self.head_location is not FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE:
            raise ValueError("The normal full-through bolt head must be on the near exterior.")
        if self.nut_location is not FullThroughHardwareLocation.EXTERIOR_FAR_SIDE:
            raise ValueError("The normal full-through nut must be on the far exterior.")
        if self.washer_locations != (
            FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,
            FullThroughHardwareLocation.EXTERIOR_FAR_SIDE,
        ):
            raise ValueError("Normal full-through washers must be on both exterior ends.")
        if (
            self.physical_bolt_count,
            self.continuous_shank_count,
            self.internal_hardware_count,
        ) != (
            1,
            1,
            0,
        ):
            raise ValueError(
                "A C1 full-through path requires one bolt/shank and no internal hardware."
            )


def full_through_bolt_hardware(path: FullThroughBoltPath) -> FullThroughBoltHardware:
    if not isinstance(path, FullThroughBoltPath):
        raise TypeError("path must be a FullThroughBoltPath.")
    return FullThroughBoltHardware(
        path.bolt_id,
        path.shank_length,
        FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,
        FullThroughHardwareLocation.EXTERIOR_FAR_SIDE,
        (
            FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,
            FullThroughHardwareLocation.EXTERIOR_FAR_SIDE,
        ),
    )


@dataclass(frozen=True, slots=True)
class FaceHoleContainment:
    """Independent exact complete-hole containment result for one exterior face."""

    face_id: MemberProfileSurfaceId
    bolt_id: str
    valid: bool
    minimum_clearance: Decimal
    exact_deficit: Decimal

    def __post_init__(self) -> None:
        require_enum(self.face_id, MemberProfileSurfaceId, "FaceHoleContainment.face_id")
        validate_identifier(self.bolt_id, "FaceHoleContainment.bolt_id")
        if not isinstance(self.valid, bool):
            raise TypeError("FaceHoleContainment.valid must be a bool.")
        clearance = _decimal(self.minimum_clearance, "minimum_clearance")
        deficit = _decimal(self.exact_deficit, "exact_deficit")
        if deficit < 0 or deficit != max(Decimal(0), -clearance):
            raise ValueError("Containment deficit must be the exact negative-clearance deficit.")
        if self.valid is not (clearance >= 0):
            raise ValueError("Containment validity must follow the exact signed clearance.")


def _bounds_clearance(
    bounds: ProfileLocalBounds3D,
    axis: PrincipalAxisFamily,
    local_uv: tuple[Decimal, Decimal],
    radius: Decimal,
) -> Decimal:
    u, v = local_uv
    v_min, v_max = (
        (bounds.min_z, bounds.max_z)
        if axis is PrincipalAxisFamily.Y
        else (bounds.min_y, bounds.max_y)
    )
    return min(
        u - bounds.min_x - radius, bounds.max_x - u - radius, v - v_min - radius, v_max - v - radius
    )


def evaluate_face_hole_containment(
    surface: ProfileSurfaceDefinition,
    *,
    bolt_id: str,
    local_uv: tuple[Decimal, Decimal],
    hole_radius: Decimal,
) -> FaceHoleContainment:
    """Evaluate a complete circular hole against one face's finite safe patches."""

    if not isinstance(surface, ProfileSurfaceDefinition):
        raise TypeError("surface must be a ProfileSurfaceDefinition.")
    validate_identifier(bolt_id, "bolt_id")
    if not isinstance(local_uv, tuple) or len(local_uv) != 2:
        raise TypeError("local_uv must be an exact two-item tuple.")
    uv = (_decimal(local_uv[0], "local_uv[0]"), _decimal(local_uv[1], "local_uv[1]"))
    radius = _decimal(hole_radius, "hole_radius")
    if radius < 0:
        raise ValueError("hole_radius must be nonnegative.")
    clearance = max(
        _bounds_clearance(bounds, surface.plane_axis, uv, radius)
        for bounds in surface.penetration_bounds
    )
    return FaceHoleContainment(
        surface.surface_id,
        bolt_id,
        clearance >= 0,
        clearance,
        max(Decimal(0), -clearance),
    )


@dataclass(frozen=True, slots=True)
class FullThroughContainment:
    """Fail-closed aggregate requiring independent entry and exit containment."""

    status: RectangularContainmentStatus
    face_results: tuple[FaceHoleContainment, ...]
    governing_face: MemberProfileSurfaceId
    governing_bolt: str
    exact_deficit: Decimal

    def __post_init__(self) -> None:
        require_enum(self.status, RectangularContainmentStatus, "status")
        require_tuple(self.face_results, "face_results")
        if len(self.face_results) != 2 or any(
            not isinstance(item, FaceHoleContainment) for item in self.face_results
        ):
            raise ValueError("Full-through containment requires exactly two face results.")
        if self.face_results[0].face_id is self.face_results[1].face_id:
            raise ValueError("Full-through containment requires two distinct faces.")
        if self.face_results[0].bolt_id != self.face_results[1].bolt_id:
            raise ValueError(
                "Full-through containment must resolve both faces for one physical bolt."
            )
        governing = min(self.face_results, key=lambda item: item.minimum_clearance)
        if (
            self.governing_face is not governing.face_id
            or self.governing_bolt != governing.bolt_id
            or self.exact_deficit != governing.exact_deficit
        ):
            raise ValueError("Full-through governing containment evidence must be exact.")
        expected = (
            RectangularContainmentStatus.VALID
            if all(item.valid for item in self.face_results)
            else RectangularContainmentStatus.INVALID_GEOMETRY
        )
        if self.status is not expected:
            raise ValueError("Full-through containment status must require both faces.")


def aggregate_full_through_containment(
    near: FaceHoleContainment,
    far: FaceHoleContainment,
) -> FullThroughContainment:
    if not isinstance(near, FaceHoleContainment) or not isinstance(far, FaceHoleContainment):
        raise TypeError("near and far must be FaceHoleContainment values.")
    governing = min((near, far), key=lambda item: item.minimum_clearance)
    status = (
        RectangularContainmentStatus.VALID
        if near.valid and far.valid
        else RectangularContainmentStatus.INVALID_GEOMETRY
    )
    return FullThroughContainment(
        status,
        (near, far),
        governing.face_id,
        governing.bolt_id,
        governing.exact_deficit,
    )


def evaluate_full_through_containment(
    profile: MemberProfile,
    axis: RectangularBoltAxis,
    *,
    bolt_id: str,
    hole_radius: Decimal,
) -> FullThroughContainment:
    """Independently evaluate the same authoritative axis on both exterior faces."""

    if not isinstance(axis, RectangularBoltAxis):
        raise TypeError("axis must be a RectangularBoltAxis.")
    pair = rectangular_opposing_face_pair(profile, axis.selected_face)
    near = evaluate_face_hole_containment(
        pair.selected_surface,
        bolt_id=bolt_id,
        local_uv=axis.near_local_uv,
        hole_radius=hole_radius,
    )
    far = evaluate_face_hole_containment(
        pair.opposite_surface,
        bolt_id=bolt_id,
        local_uv=axis.far_local_uv,
        hole_radius=hole_radius,
    )
    return aggregate_full_through_containment(near, far)


def _basis_payload(basis: RectangularMaterialBasis | None) -> object:
    if basis is None:
        return None
    return {
        "LW": [_canonical_decimal(item) for item in _vector_tuple(basis.lengthwise)],
        "CW": [_canonical_decimal(item) for item in _vector_tuple(basis.crosswise)],
        "TT": [_canonical_decimal(item) for item in _vector_tuple(basis.through_thickness)],
    }


def canonical_full_through_bolt_json(path: FullThroughBoltPath) -> str:
    """Return deterministic unit-free canonical physical-path identity."""

    if not isinstance(path, FullThroughBoltPath):
        raise TypeError("path must be a FullThroughBoltPath.")
    payload = {
        "schema_version": RECTANGULAR_FULL_THROUGH_BOLT_SCHEMA_VERSION,
        "bolt_id": path.bolt_id,
        "axis": {
            "selected_face": path.axis.selected_face.value,
            "opposite_face": path.axis.opposite_face.value,
            "local_u": _canonical_decimal(path.axis.local_u),
            "local_v": _canonical_decimal(path.axis.local_v),
        },
        "segments": [
            {
                "kind": item.kind.value,
                "identity": item.identity,
                "length": _canonical_decimal(item.length),
                "entry_plane_id": item.entry_plane_id,
                "exit_plane_id": item.exit_plane_id,
                "material_region_id": item.material_region_id,
                "material_basis": _basis_payload(item.material_basis),
            }
            for item in path.segments
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def full_through_bolt_fingerprint(path: FullThroughBoltPath) -> str:
    return hashlib.sha256(canonical_full_through_bolt_json(path).encode("utf-8")).hexdigest()


RECTANGULAR_LOCAL_MECHANICS_LIMITATIONS = tuple(RectangularLocalMechanicsLimitation)


__all__ = (
    "RECTANGULAR_FULL_THROUGH_BOLT_SCHEMA_VERSION",
    "RECTANGULAR_LOCAL_MECHANICS_LIMITATIONS",
    "SOLID_RECTANGULAR_MATERIAL_BASIS",
    "FaceHoleContainment",
    "FullThroughBoltHardware",
    "FullThroughBoltPath",
    "FullThroughContainment",
    "FullThroughHardwareLocation",
    "PhysicalBoltPathSegment",
    "PhysicalBoltPathSegmentKind",
    "RectangularBoltAxis",
    "RectangularContainmentStatus",
    "RectangularFaceLocalFrame",
    "RectangularLocalMechanicsLimitation",
    "RectangularMaterialBasis",
    "RectangularOpposingFacePair",
    "aggregate_full_through_containment",
    "build_rhs_full_through_core",
    "build_srs_full_through_core",
    "canonical_full_through_bolt_json",
    "compose_external_connector_layers",
    "evaluate_face_hole_containment",
    "evaluate_full_through_containment",
    "external_connector_layer",
    "full_through_bolt_fingerprint",
    "full_through_bolt_hardware",
    "rectangular_opposing_face_pair",
    "solid_rectangular_material_basis",
)
