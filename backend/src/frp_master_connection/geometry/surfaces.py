"""Exact physical surface patches derived from canonical placed component geometry."""

import math
from dataclasses import dataclass, field
from enum import StrEnum

from frp_master_connection.domain.entities import AssemblySupport, ParticipantReference
from frp_master_connection.domain.section_topology import (
    PhysicalSectionElementRole,
    SectionTopologySource,
)
from frp_master_connection.domain.validation import (
    require_enum,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import ParticipantKind, PositionVector3D, SectionFamily
from frp_master_connection.geometry.placement import (
    LocalAnnularCylinder3D,
    LocalRectangularPrism3D,
    LocalRuledSurface3D,
    LongitudinalExtent,
    PlacedComponentGeometry3D,
    PlacedDeferredFeature3D,
    PlacedPhysicalElement3D,
)
from frp_master_connection.geometry.spatial import (
    CartesianFrame3D,
    UnitVector3D,
    Vector3D,
)


def _require_finite_positive(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
    if value <= 0.0:
        raise ValueError(f"{field_name} must be positive.")


def _require_finite_nonnegative(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
    if value < 0.0:
        raise ValueError(f"{field_name} must be nonnegative.")


class SurfaceGeometryKind(StrEnum):
    """Controlled exact surface-geometry representations."""

    PLANAR_RECTANGLE = "PLANAR_RECTANGLE"
    PLANAR_ANNULUS = "PLANAR_ANNULUS"
    ANALYTIC_CYLINDER = "ANALYTIC_CYLINDER"


class SurfaceExposure(StrEnum):
    """Geometric relationship of a patch to material and adjacent space."""

    EXTERIOR_EXPOSED = "EXTERIOR_EXPOSED"
    VOID_EXPOSED = "VOID_EXPOSED"
    END_CUT = "END_CUT"
    INTERNAL_JUNCTION = "INTERNAL_JUNCTION"


class SurfaceDisposition(StrEnum):
    """Whether a patch is regular physical geometry or explicitly deferred."""

    REGULAR = "REGULAR"
    DEFERRED = "DEFERRED"


class SurfaceSourceKind(StrEnum):
    """Controlled source identities for authoritative surface patches."""

    PHYSICAL_SECTION_ELEMENT = "PHYSICAL_SECTION_ELEMENT"
    DEFERRED_FEATURE = "DEFERRED_FEATURE"
    SUPPORT = "SUPPORT"


class SurfacePatchRole(StrEnum):
    """Controlled physical role used by downstream geometric operations."""

    NEGATIVE_THICKNESS_FACE = "NEGATIVE_THICKNESS_FACE"
    POSITIVE_THICKNESS_FACE = "POSITIVE_THICKNESS_FACE"
    EDGE_FACE = "EDGE_FACE"
    END_CUT_FACE = "END_CUT_FACE"
    OUTER_CYLINDRICAL_FACE = "OUTER_CYLINDRICAL_FACE"
    INNER_CYLINDRICAL_FACE = "INNER_CYLINDRICAL_FACE"
    ANNULAR_END_FACE = "ANNULAR_END_FACE"
    JUNCTION_FACE = "JUNCTION_FACE"
    SUPPORT_FACE = "SUPPORT_FACE"


class RadialNormalSense(StrEnum):
    """Radial normal rule for an analytic cylindrical surface."""

    OUTWARD = "OUTWARD"
    INWARD = "INWARD"


@dataclass(frozen=True, slots=True)
class PlanarRectangularSurface3D:
    """One exact bounded plane with surface-local x as its signed normal."""

    frame: CartesianFrame3D
    extent_y: float
    extent_z: float
    kind: SurfaceGeometryKind = field(default=SurfaceGeometryKind.PLANAR_RECTANGLE, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.frame, CartesianFrame3D):
            raise TypeError("PlanarRectangularSurface3D.frame must be a CartesianFrame3D.")
        _require_finite_positive(self.extent_y, "PlanarRectangularSurface3D.extent_y")
        _require_finite_positive(self.extent_z, "PlanarRectangularSurface3D.extent_z")
        half_y = self.extent_y / 2.0
        half_z = self.extent_z / 2.0
        if half_y <= 0.0 or half_z <= 0.0:
            raise ValueError("Planar surface half-extents must remain exactly representable.")
        _ = self._corners(half_y, half_z)

    @property
    def center(self) -> PositionVector3D:
        """Return the exact global surface center."""
        return self.frame.origin

    @property
    def normal(self) -> UnitVector3D:
        """Return the signed canonical global surface normal."""
        return self.frame.x_axis

    @property
    def corners(self) -> tuple[PositionVector3D, ...]:
        """Return corners counterclockwise in the surface-local y-z plane."""
        return self._corners(self.extent_y / 2.0, self.extent_z / 2.0)

    def _corners(self, half_y: float, half_z: float) -> tuple[PositionVector3D, ...]:
        return tuple(
            self.frame.local_to_parent_point(PositionVector3D(0.0, local_y, local_z))
            for local_y, local_z in (
                (-half_y, -half_z),
                (half_y, -half_z),
                (half_y, half_z),
                (-half_y, half_z),
            )
        )


@dataclass(frozen=True, slots=True)
class PlanarAnnularSurface3D:
    """One exact planar annulus with surface-local x as its signed normal."""

    frame: CartesianFrame3D
    outer_radius: float
    inner_radius: float
    kind: SurfaceGeometryKind = field(default=SurfaceGeometryKind.PLANAR_ANNULUS, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.frame, CartesianFrame3D):
            raise TypeError("PlanarAnnularSurface3D.frame must be a CartesianFrame3D.")
        _require_finite_positive(self.outer_radius, "PlanarAnnularSurface3D.outer_radius")
        _require_finite_nonnegative(self.inner_radius, "PlanarAnnularSurface3D.inner_radius")
        if self.outer_radius <= self.inner_radius:
            raise ValueError("Planar annulus outer_radius must be greater than inner_radius.")

    @property
    def center(self) -> PositionVector3D:
        """Return the exact global annulus center."""
        return self.frame.origin

    @property
    def normal(self) -> UnitVector3D:
        """Return the signed canonical global surface normal."""
        return self.frame.x_axis


@dataclass(frozen=True, slots=True)
class AnalyticCylindricalSurface3D:
    """One exact finite cylinder side without a sampled angle or fixed normal."""

    axis_frame: CartesianFrame3D
    extent: LongitudinalExtent
    radius: float
    radial_normal_sense: RadialNormalSense
    kind: SurfaceGeometryKind = field(default=SurfaceGeometryKind.ANALYTIC_CYLINDER, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.axis_frame, CartesianFrame3D):
            raise TypeError("AnalyticCylindricalSurface3D.axis_frame must be a CartesianFrame3D.")
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("AnalyticCylindricalSurface3D.extent must be a LongitudinalExtent.")
        _require_finite_positive(self.radius, "AnalyticCylindricalSurface3D.radius")
        require_enum(
            self.radial_normal_sense,
            RadialNormalSense,
            "AnalyticCylindricalSurface3D.radial_normal_sense",
        )

    @property
    def minimum_axis_point(self) -> PositionVector3D:
        """Return the exact minimum-x point on the cylinder axis."""
        return self.axis_frame.local_to_parent_point(
            PositionVector3D(self.extent.x_start, 0.0, 0.0)
        )

    @property
    def maximum_axis_point(self) -> PositionVector3D:
        """Return the exact maximum-x point on the cylinder axis."""
        return self.axis_frame.local_to_parent_point(PositionVector3D(self.extent.x_end, 0.0, 0.0))


type ExactSurfaceGeometry3D = (
    PlanarRectangularSurface3D | PlanarAnnularSurface3D | AnalyticCylindricalSurface3D
)


@dataclass(frozen=True, slots=True)
class SurfacePatchSource:
    """Exactly one physical-element, deferred-feature, or support source identity."""

    kind: SurfaceSourceKind
    physical_element_id: str | None = None
    deferred_feature_id: str | None = None
    support_id: str | None = None

    def __post_init__(self) -> None:
        require_enum(self.kind, SurfaceSourceKind, "SurfacePatchSource.kind")
        expected_field = {
            SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT: "physical_element_id",
            SurfaceSourceKind.DEFERRED_FEATURE: "deferred_feature_id",
            SurfaceSourceKind.SUPPORT: "support_id",
        }[self.kind]
        values = {
            "physical_element_id": self.physical_element_id,
            "deferred_feature_id": self.deferred_feature_id,
            "support_id": self.support_id,
        }
        if values[expected_field] is None or any(
            value is not None for name, value in values.items() if name != expected_field
        ):
            raise ValueError(
                "SurfacePatchSource must set exactly the ID corresponding to its source kind."
            )
        validate_identifier(values[expected_field], f"SurfacePatchSource.{expected_field}")

    @classmethod
    def physical_element(cls, element_id: str) -> SurfacePatchSource:
        """Build one physical-element source."""
        return cls(SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT, physical_element_id=element_id)

    @classmethod
    def deferred_feature(cls, feature_id: str) -> SurfacePatchSource:
        """Build one deferred-feature source."""
        return cls(SurfaceSourceKind.DEFERRED_FEATURE, deferred_feature_id=feature_id)

    @classmethod
    def support(cls, support_id: str) -> SurfacePatchSource:
        """Build one support source."""
        return cls(SurfaceSourceKind.SUPPORT, support_id=support_id)

    @property
    def source_id(self) -> str:
        """Return the one populated scoped source ID."""
        if self.physical_element_id is not None:
            return self.physical_element_id
        if self.deferred_feature_id is not None:
            return self.deferred_feature_id
        if self.support_id is not None:
            return self.support_id
        raise RuntimeError("Validated surface source has no source ID.")


@dataclass(frozen=True, slots=True)
class SurfacePatchReference:
    """A participant-scoped immutable reference to one surface patch."""

    participant: ParticipantReference
    patch_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError("SurfacePatchReference.participant must be a ParticipantReference.")
        validate_identifier(self.patch_id, "SurfacePatchReference.patch_id")


@dataclass(frozen=True, slots=True)
class SurfacePatch3D:
    """One exact authoritative surface patch with derived geometric targetability."""

    id: str
    label: str
    participant: ParticipantReference
    source: SurfacePatchSource
    exposure: SurfaceExposure
    disposition: SurfaceDisposition
    role: SurfacePatchRole
    geometry: ExactSurfaceGeometry3D

    def __post_init__(self) -> None:
        validate_identifier(self.id, "SurfacePatch3D.id")
        validate_label(self.label, "SurfacePatch3D.label")
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError("SurfacePatch3D.participant must be a ParticipantReference.")
        if not isinstance(self.source, SurfacePatchSource):
            raise TypeError("SurfacePatch3D.source must be a SurfacePatchSource.")
        require_enum(self.exposure, SurfaceExposure, "SurfacePatch3D.exposure")
        require_enum(self.disposition, SurfaceDisposition, "SurfacePatch3D.disposition")
        require_enum(self.role, SurfacePatchRole, "SurfacePatch3D.role")
        if not isinstance(
            self.geometry,
            (
                PlanarRectangularSurface3D,
                PlanarAnnularSurface3D,
                AnalyticCylindricalSurface3D,
            ),
        ):
            raise TypeError("SurfacePatch3D.geometry must be an exact surface geometry.")
        self._validate_source_ownership()
        self._validate_semantics()

    def _validate_source_ownership(self) -> None:
        if self.source.kind is SurfaceSourceKind.SUPPORT:
            if (
                self.participant.kind is not ParticipantKind.SUPPORT
                or self.source.support_id != self.participant.entity_id
            ):
                raise ValueError("A support patch source must match its support participant.")
        elif self.participant.kind not in {
            ParticipantKind.MEMBER,
            ParticipantKind.CONNECTOR_COMPONENT,
        }:
            raise ValueError("Component patch sources require a member or connector participant.")

    def _validate_semantics(self) -> None:
        if self.source.kind is SurfaceSourceKind.DEFERRED_FEATURE:
            if self.disposition is not SurfaceDisposition.DEFERRED:
                raise ValueError("Deferred-feature patches require DEFERRED disposition.")
        elif self.disposition is not SurfaceDisposition.REGULAR:
            raise ValueError("Physical-element and support patches require REGULAR disposition.")
        if self.source.kind is SurfaceSourceKind.SUPPORT and (
            self.exposure is not SurfaceExposure.EXTERIOR_EXPOSED
            or not isinstance(self.geometry, PlanarRectangularSurface3D)
            or self.role is not SurfacePatchRole.SUPPORT_FACE
        ):
            raise ValueError("Support patches must be exterior planar rectangles.")
        if self.source.kind is SurfaceSourceKind.DEFERRED_FEATURE and (
            self.role is not SurfacePatchRole.JUNCTION_FACE
        ):
            raise ValueError("Deferred-feature patches require JUNCTION_FACE role.")
        if self.source.kind is SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT and self.role in {
            SurfacePatchRole.JUNCTION_FACE,
            SurfacePatchRole.SUPPORT_FACE,
        }:
            raise ValueError("Physical-element patches cannot use junction or support roles.")
        if isinstance(self.geometry, PlanarAnnularSurface3D) and (
            self.exposure is not SurfaceExposure.END_CUT
            or self.role is not SurfacePatchRole.ANNULAR_END_FACE
        ):
            raise ValueError("Planar annular component patches must be end cuts.")
        if isinstance(self.geometry, AnalyticCylindricalSurface3D):
            expected = (
                SurfacePatchRole.OUTER_CYLINDRICAL_FACE
                if self.geometry.radial_normal_sense is RadialNormalSense.OUTWARD
                else SurfacePatchRole.INNER_CYLINDRICAL_FACE
            )
            if (
                self.exposure
                not in {SurfaceExposure.EXTERIOR_EXPOSED, SurfaceExposure.VOID_EXPOSED}
                or self.role is not expected
            ):
                raise ValueError("Analytic cylinder patch role must match its radial normal sense.")
        if (
            self.source.kind is SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT
            and isinstance(self.geometry, PlanarRectangularSurface3D)
            and self.exposure is SurfaceExposure.END_CUT
            and self.role is not SurfacePatchRole.END_CUT_FACE
        ):
            raise ValueError("Physical rectangular end cuts require END_CUT_FACE role.")
        if (
            self.source.kind is SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT
            and isinstance(self.geometry, PlanarRectangularSurface3D)
            and self.exposure is not SurfaceExposure.END_CUT
            and self.role
            not in {
                SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
                SurfacePatchRole.POSITIVE_THICKNESS_FACE,
                SurfacePatchRole.EDGE_FACE,
            }
        ):
            raise ValueError(
                "A regular physical planar rectangle requires an explicit broad- or edge-face role."
            )

    @property
    def is_targetable(self) -> bool:
        """Derive geometric targetability without a caller override."""
        return (
            self.disposition is SurfaceDisposition.REGULAR
            and self.exposure is not SurfaceExposure.INTERNAL_JUNCTION
        )

    @property
    def reference(self) -> SurfacePatchReference:
        """Return this patch's participant-scoped reference."""
        return SurfacePatchReference(self.participant, self.id)


@dataclass(frozen=True, slots=True)
class ComponentSurfaceSet3D:
    """The immutable deterministic authoritative patches for one placed component."""

    participant: ParticipantReference
    placed_component: PlacedComponentGeometry3D
    patches: tuple[SurfacePatch3D, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.participant, ParticipantReference):
            raise TypeError("ComponentSurfaceSet3D.participant must be a ParticipantReference.")
        if not isinstance(self.placed_component, PlacedComponentGeometry3D):
            raise TypeError(
                "ComponentSurfaceSet3D.placed_component must be PlacedComponentGeometry3D."
            )
        if self.participant != self.placed_component.participant:
            raise ValueError("Surface-set participant must match the placed component.")
        if not isinstance(self.patches, tuple):
            raise TypeError("ComponentSurfaceSet3D.patches must be an immutable tuple.")
        if not self.patches:
            raise ValueError("ComponentSurfaceSet3D.patches must not be empty.")
        if any(not isinstance(patch, SurfacePatch3D) for patch in self.patches):
            raise TypeError("ComponentSurfaceSet3D.patches items must be SurfacePatch3D values.")
        if any(patch.participant != self.participant for patch in self.patches):
            raise ValueError("Every patch must be owned by the surface-set participant.")
        patch_ids = tuple(patch.id for patch in self.patches)
        if len(set(patch_ids)) != len(patch_ids):
            raise ValueError("Surface patch IDs must be unique within one participant.")
        if patch_ids != tuple(sorted(patch_ids)):
            raise ValueError("Component surface patches must use deterministic ID ordering.")
        if len({patch.geometry for patch in self.patches}) != len(self.patches):
            raise ValueError("A component surface set cannot duplicate authoritative geometry.")
        self._validate_sources()

    def _validate_sources(self) -> None:
        physical = {
            item.source_element.id: item for item in self.placed_component.physical_elements
        }
        deferred = {
            item.source_feature.id: item for item in self.placed_component.deferred_features
        }
        for patch in self.patches:
            if patch.source.kind is SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT:
                source = physical.get(patch.source.source_id)
                if source is None:
                    raise ValueError("Surface patch references an unknown physical-element ID.")
                self._validate_physical_geometry_kind(patch, source)
            elif patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE:
                source_deferred = deferred.get(patch.source.source_id)
                if source_deferred is None:
                    raise ValueError("Surface patch references an unknown deferred-feature ID.")
                if not isinstance(patch.geometry, PlanarRectangularSurface3D):
                    raise ValueError("Deferred feature patches must use exact planar rectangles.")
            else:
                raise ValueError("A component surface set cannot contain support-owned patches.")

    @staticmethod
    def _validate_physical_geometry_kind(
        patch: SurfacePatch3D,
        source: PlacedPhysicalElement3D,
    ) -> None:
        is_annular = any(
            isinstance(extrusion, LocalAnnularCylinder3D) for extrusion in source.extrusions
        )
        if is_annular != isinstance(
            patch.geometry,
            (PlanarAnnularSurface3D, AnalyticCylindricalSurface3D),
        ):
            raise ValueError("Surface geometry kind does not match its physical extrusion.")

    def resolve(self, reference: SurfacePatchReference) -> SurfacePatch3D:
        """Resolve one reference only within this participant-scoped surface set."""
        if not isinstance(reference, SurfacePatchReference):
            raise TypeError("reference must be a SurfacePatchReference.")
        if reference.participant != self.participant:
            raise KeyError("Surface reference participant does not match this surface set.")
        for patch in self.patches:
            if patch.id == reference.patch_id:
                return patch
        raise KeyError(f"Unknown surface patch ID {reference.patch_id!r} for this participant.")


def _point_in_component(
    placed: PlacedComponentGeometry3D,
    local_x: float,
    local_y: float,
    local_z: float,
) -> PositionVector3D:
    return placed.global_frame.local_to_parent_point(PositionVector3D(local_x, local_y, local_z))


def _surface_frame(
    origin: PositionVector3D,
    normal: UnitVector3D,
    in_plane_y: UnitVector3D,
) -> CartesianFrame3D:
    in_plane_z = normal.cross(in_plane_y).normalized()
    return CartesianFrame3D(origin, normal, in_plane_y, in_plane_z)


def _midpoint(first: float, second: float) -> float:
    midpoint = first + (second - first) / 2.0
    if not math.isfinite(midpoint):
        raise ValueError("Surface midpoint must be finite.")
    return midpoint


def _rectangle_face_y(
    placed: PlacedComponentGeometry3D,
    prism: LocalRectangularPrism3D,
    local_y: float,
    normal_sign: int,
    *,
    min_z: float | None = None,
    max_z: float | None = None,
) -> PlanarRectangularSurface3D:
    z_start = prism.rectangle.min_z if min_z is None else min_z
    z_end = prism.rectangle.max_z if max_z is None else max_z
    normal = placed.global_frame.y_axis if normal_sign > 0 else -placed.global_frame.y_axis
    frame = _surface_frame(
        _point_in_component(
            placed,
            _midpoint(prism.extent.x_start, prism.extent.x_end),
            local_y,
            _midpoint(z_start, z_end),
        ),
        normal,
        placed.global_frame.x_axis,
    )
    return PlanarRectangularSurface3D(frame, prism.extent.length, z_end - z_start)


def _rectangle_face_z(
    placed: PlacedComponentGeometry3D,
    prism: LocalRectangularPrism3D,
    local_z: float,
    normal_sign: int,
    *,
    min_y: float | None = None,
    max_y: float | None = None,
) -> PlanarRectangularSurface3D:
    y_start = prism.rectangle.min_y if min_y is None else min_y
    y_end = prism.rectangle.max_y if max_y is None else max_y
    normal = placed.global_frame.z_axis if normal_sign > 0 else -placed.global_frame.z_axis
    frame = _surface_frame(
        _point_in_component(
            placed,
            _midpoint(prism.extent.x_start, prism.extent.x_end),
            _midpoint(y_start, y_end),
            local_z,
        ),
        normal,
        placed.global_frame.x_axis,
    )
    return PlanarRectangularSurface3D(frame, prism.extent.length, y_end - y_start)


def _rectangle_end_face(
    placed: PlacedComponentGeometry3D,
    prism: LocalRectangularPrism3D,
    *,
    maximum: bool,
) -> PlanarRectangularSurface3D:
    local_x = prism.extent.x_end if maximum else prism.extent.x_start
    normal = placed.global_frame.x_axis if maximum else -placed.global_frame.x_axis
    frame = _surface_frame(
        _point_in_component(
            placed,
            local_x,
            _midpoint(prism.rectangle.min_y, prism.rectangle.max_y),
            _midpoint(prism.rectangle.min_z, prism.rectangle.max_z),
        ),
        normal,
        placed.global_frame.y_axis,
    )
    return PlanarRectangularSurface3D(
        frame,
        prism.rectangle.max_y - prism.rectangle.min_y,
        prism.rectangle.max_z - prism.rectangle.min_z,
    )


def _axis_frame_for_annulus(
    placed: PlacedComponentGeometry3D,
    extrusion: LocalAnnularCylinder3D,
) -> CartesianFrame3D:
    return CartesianFrame3D(
        _point_in_component(
            placed,
            0.0,
            extrusion.annulus.center.y,
            extrusion.annulus.center.z,
        ),
        placed.global_frame.x_axis,
        placed.global_frame.y_axis,
        placed.global_frame.z_axis,
    )


def _annular_end_face(
    placed: PlacedComponentGeometry3D,
    extrusion: LocalAnnularCylinder3D,
    *,
    maximum: bool,
) -> PlanarAnnularSurface3D:
    local_x = extrusion.extent.x_end if maximum else extrusion.extent.x_start
    normal = placed.global_frame.x_axis if maximum else -placed.global_frame.x_axis
    frame = _surface_frame(
        _point_in_component(
            placed,
            local_x,
            extrusion.annulus.center.y,
            extrusion.annulus.center.z,
        ),
        normal,
        placed.global_frame.y_axis,
    )
    return PlanarAnnularSurface3D(
        frame,
        extrusion.annulus.outer_radius,
        extrusion.annulus.inner_radius,
    )


def _ruled_surface_face(
    placed: PlacedComponentGeometry3D,
    extrusion: LocalRuledSurface3D,
) -> PlanarRectangularSurface3D:
    line = extrusion.line
    delta_y = line.end.y - line.start.y
    delta_z = line.end.z - line.start.z
    line_direction_local = Vector3D(0.0, delta_y, delta_z)
    line_length = line_direction_local.norm
    line_direction_global = placed.global_frame.local_to_parent_vector(
        line_direction_local
    ).normalized()
    longitudinal = placed.global_frame.x_axis
    normal = longitudinal.cross(line_direction_global).normalized()
    return PlanarRectangularSurface3D(
        CartesianFrame3D(
            _point_in_component(
                placed,
                _midpoint(extrusion.extent.x_start, extrusion.extent.x_end),
                _midpoint(line.start.y, line.end.y),
                _midpoint(line.start.z, line.end.z),
            ),
            normal,
            longitudinal,
            line_direction_global,
        ),
        extrusion.extent.length,
        line_length,
    )


def _patch(
    source_id: str,
    suffix: str,
    label: str,
    participant: ParticipantReference,
    exposure: SurfaceExposure,
    disposition: SurfaceDisposition,
    role: SurfacePatchRole,
    geometry: ExactSurfaceGeometry3D,
    *,
    deferred: bool = False,
) -> SurfacePatch3D:
    source = (
        SurfacePatchSource.deferred_feature(source_id)
        if deferred
        else SurfacePatchSource.physical_element(source_id)
    )
    return SurfacePatch3D(
        f"{source_id}:{suffix}",
        label,
        participant,
        source,
        exposure,
        disposition,
        role,
        geometry,
    )


def _physical_by_role(
    placed: PlacedComponentGeometry3D,
    role: PhysicalSectionElementRole,
) -> PlacedPhysicalElement3D:
    matches = tuple(item for item in placed.physical_elements if item.source_element.role is role)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one placed physical element with role {role.value}.")
    return matches[0]


def _rectangular_prism(element: PlacedPhysicalElement3D) -> LocalRectangularPrism3D:
    if len(element.extrusions) != 1 or not isinstance(
        element.extrusions[0], LocalRectangularPrism3D
    ):
        raise ValueError("Standard flat physical elements require one rectangular prism.")
    return element.extrusions[0]


def _physical_end_patches(
    placed: PlacedComponentGeometry3D,
    element: PlacedPhysicalElement3D,
    prism: LocalRectangularPrism3D,
) -> list[SurfacePatch3D]:
    return [
        _patch(
            element.source_element.id,
            "MINIMUM_X_END_CUT",
            f"{element.source_element.label} minimum-x end cut",
            placed.participant,
            SurfaceExposure.END_CUT,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.END_CUT_FACE,
            _rectangle_end_face(placed, prism, maximum=False),
        ),
        _patch(
            element.source_element.id,
            "MAXIMUM_X_END_CUT",
            f"{element.source_element.label} maximum-x end cut",
            placed.participant,
            SurfaceExposure.END_CUT,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.END_CUT_FACE,
            _rectangle_end_face(placed, prism, maximum=True),
        ),
    ]


def _wide_flange_or_i_patches(
    placed: PlacedComponentGeometry3D,
) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    web = _physical_by_role(placed, PhysicalSectionElementRole.WEB)
    web_prism = _rectangular_prism(web)
    for suffix, local_y, sign, surface_role in (
        (
            "NEGATIVE_TT_BROAD",
            web_prism.rectangle.min_y,
            -1,
            SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
        ),
        (
            "POSITIVE_TT_BROAD",
            web_prism.rectangle.max_y,
            1,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
        ),
    ):
        patches.append(
            _patch(
                web.source_element.id,
                suffix,
                f"{web.source_element.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                surface_role,
                _rectangle_face_y(placed, web_prism, local_y, sign),
            )
        )
    patches.extend(_physical_end_patches(placed, web, web_prism))

    flange_definitions = (
        (PhysicalSectionElementRole.TOP_FLANGE, True),
        (PhysicalSectionElementRole.BOTTOM_FLANGE, False),
    )
    for element_role, is_top in flange_definitions:
        flange = _physical_by_role(placed, element_role)
        prism = _rectangular_prism(flange)
        outer_z = prism.rectangle.max_z if is_top else prism.rectangle.min_z
        inner_z = prism.rectangle.min_z if is_top else prism.rectangle.max_z
        outer_sign = 1 if is_top else -1
        inner_sign = -outer_sign
        patches.append(
            _patch(
                flange.source_element.id,
                "OUTER_TT_BROAD",
                f"{flange.source_element.label} outer broad surface",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                (
                    SurfacePatchRole.POSITIVE_THICKNESS_FACE
                    if is_top
                    else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                ),
                _rectangle_face_z(placed, prism, outer_z, outer_sign),
            )
        )
        for suffix, min_y, max_y in (
            (
                "OUTER_NEGATIVE_CW_STRIP",
                prism.rectangle.min_y,
                web_prism.rectangle.min_y,
            ),
            (
                "OUTER_POSITIVE_CW_STRIP",
                web_prism.rectangle.max_y,
                prism.rectangle.max_y,
            ),
        ):
            patches.append(
                _patch(
                    flange.source_element.id,
                    suffix,
                    f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                    placed.participant,
                    SurfaceExposure.EXTERIOR_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    (
                        SurfacePatchRole.POSITIVE_THICKNESS_FACE
                        if is_top
                        else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                    ),
                    _rectangle_face_z(
                        placed,
                        prism,
                        outer_z,
                        outer_sign,
                        min_y=min_y,
                        max_y=max_y,
                    ),
                )
            )
        for suffix, min_y, max_y in (
            (
                "INNER_NEGATIVE_CW_STRIP",
                prism.rectangle.min_y,
                web_prism.rectangle.min_y,
            ),
            (
                "INNER_POSITIVE_CW_STRIP",
                web_prism.rectangle.max_y,
                prism.rectangle.max_y,
            ),
        ):
            patches.append(
                _patch(
                    flange.source_element.id,
                    suffix,
                    f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                    placed.participant,
                    SurfaceExposure.VOID_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    (
                        SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                        if is_top
                        else SurfacePatchRole.POSITIVE_THICKNESS_FACE
                    ),
                    _rectangle_face_z(
                        placed,
                        prism,
                        inner_z,
                        inner_sign,
                        min_y=min_y,
                        max_y=max_y,
                    ),
                )
            )
        for suffix, local_y, sign in (
            ("NEGATIVE_CW_EDGE", prism.rectangle.min_y, -1),
            ("POSITIVE_CW_EDGE", prism.rectangle.max_y, 1),
        ):
            patches.append(
                _patch(
                    flange.source_element.id,
                    suffix,
                    f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                    placed.participant,
                    SurfaceExposure.EXTERIOR_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    SurfacePatchRole.EDGE_FACE,
                    _rectangle_face_y(placed, prism, local_y, sign),
                )
            )
        patches.extend(_physical_end_patches(placed, flange, prism))
    patches.extend(_deferred_line_patches(placed))
    return patches


def _channel_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    web = _physical_by_role(placed, PhysicalSectionElementRole.WEB)
    web_prism = _rectangular_prism(web)
    for suffix, local_y, sign, exposure, surface_role in (
        (
            "EXTERIOR_BACK_BROAD",
            web_prism.rectangle.min_y,
            -1,
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
        ),
        (
            "VOID_FACING_INNER_BROAD",
            web_prism.rectangle.max_y,
            1,
            SurfaceExposure.VOID_EXPOSED,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
        ),
    ):
        patches.append(
            _patch(
                web.source_element.id,
                suffix,
                f"{web.source_element.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                exposure,
                SurfaceDisposition.REGULAR,
                surface_role,
                _rectangle_face_y(placed, web_prism, local_y, sign),
            )
        )
    patches.extend(_physical_end_patches(placed, web, web_prism))

    for element_role, is_top in (
        (PhysicalSectionElementRole.TOP_FLANGE, True),
        (PhysicalSectionElementRole.BOTTOM_FLANGE, False),
    ):
        flange = _physical_by_role(placed, element_role)
        prism = _rectangular_prism(flange)
        outer_z = prism.rectangle.max_z if is_top else prism.rectangle.min_z
        inner_z = prism.rectangle.min_z if is_top else prism.rectangle.max_z
        outer_sign = 1 if is_top else -1
        patches.append(
            _patch(
                flange.source_element.id,
                "OUTER_BROAD",
                f"{flange.source_element.label} exterior outer broad surface",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                (
                    SurfacePatchRole.POSITIVE_THICKNESS_FACE
                    if is_top
                    else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                ),
                _rectangle_face_z(placed, prism, outer_z, outer_sign),
            )
        )
        patches.append(
            _patch(
                flange.source_element.id,
                "INNER_VOID_STRIP",
                f"{flange.source_element.label} inner void-facing strip",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                (
                    SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                    if is_top
                    else SurfacePatchRole.POSITIVE_THICKNESS_FACE
                ),
                _rectangle_face_z(
                    placed,
                    prism,
                    inner_z,
                    -outer_sign,
                    min_y=web_prism.rectangle.max_y,
                    max_y=prism.rectangle.max_y,
                ),
            )
        )
        for suffix, local_y, sign in (
            ("NEGATIVE_CW_BACK_EDGE", prism.rectangle.min_y, -1),
            ("POSITIVE_CW_FREE_TIP", prism.rectangle.max_y, 1),
        ):
            patches.append(
                _patch(
                    flange.source_element.id,
                    suffix,
                    f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                    placed.participant,
                    SurfaceExposure.EXTERIOR_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    SurfacePatchRole.EDGE_FACE,
                    _rectangle_face_y(placed, prism, local_y, sign),
                )
            )
        patches.extend(_physical_end_patches(placed, flange, prism))
    patches.extend(_deferred_line_patches(placed))
    return patches


def _tee_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    stem = _physical_by_role(placed, PhysicalSectionElementRole.STEM)
    stem_prism = _rectangular_prism(stem)
    for suffix, local_y, sign, role in (
        (
            "NEGATIVE_TT_BROAD",
            stem_prism.rectangle.min_y,
            -1,
            SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
        ),
        (
            "POSITIVE_TT_BROAD",
            stem_prism.rectangle.max_y,
            1,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
        ),
    ):
        patches.append(
            _patch(
                stem.source_element.id,
                suffix,
                f"{stem.source_element.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                role,
                _rectangle_face_y(placed, stem_prism, local_y, sign),
            )
        )
    patches.append(
        _patch(
            stem.source_element.id,
            "FREE_STEM_EDGE",
            f"{stem.source_element.label} free stem edge",
            placed.participant,
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.EDGE_FACE,
            _rectangle_face_z(placed, stem_prism, stem_prism.rectangle.min_z, -1),
        )
    )
    patches.extend(_physical_end_patches(placed, stem, stem_prism))

    flange = _physical_by_role(placed, PhysicalSectionElementRole.FLANGE)
    flange_prism = _rectangular_prism(flange)
    patches.append(
        _patch(
            flange.source_element.id,
            "OUTER_TT_BROAD",
            f"{flange.source_element.label} exterior outer broad surface",
            placed.participant,
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
            _rectangle_face_z(placed, flange_prism, flange_prism.rectangle.max_z, 1),
        )
    )
    for suffix, min_y, max_y in (
        (
            "INNER_NEGATIVE_CW_STRIP",
            flange_prism.rectangle.min_y,
            stem_prism.rectangle.min_y,
        ),
        (
            "INNER_POSITIVE_CW_STRIP",
            stem_prism.rectangle.max_y,
            flange_prism.rectangle.max_y,
        ),
    ):
        patches.append(
            _patch(
                flange.source_element.id,
                suffix,
                f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
                _rectangle_face_z(
                    placed,
                    flange_prism,
                    flange_prism.rectangle.min_z,
                    -1,
                    min_y=min_y,
                    max_y=max_y,
                ),
            )
        )
    for suffix, local_y, sign in (
        ("NEGATIVE_CW_EDGE", flange_prism.rectangle.min_y, -1),
        ("POSITIVE_CW_EDGE", flange_prism.rectangle.max_y, 1),
    ):
        patches.append(
            _patch(
                flange.source_element.id,
                suffix,
                f"{flange.source_element.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.EDGE_FACE,
                _rectangle_face_y(placed, flange_prism, local_y, sign),
            )
        )
    patches.extend(_physical_end_patches(placed, flange, flange_prism))
    patches.extend(_deferred_line_patches(placed))
    return patches


def _tube_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    wall_definitions = (
        (PhysicalSectionElementRole.TOP_WALL, "z", 1),
        (PhysicalSectionElementRole.BOTTOM_WALL, "z", -1),
        (PhysicalSectionElementRole.SIDE_WALL_1, "y", -1),
        (PhysicalSectionElementRole.SIDE_WALL_2, "y", 1),
    )
    for role, axis, exterior_sign in wall_definitions:
        wall = _physical_by_role(placed, role)
        prism = _rectangular_prism(wall)
        if axis == "z":
            exterior_coordinate = (
                prism.rectangle.max_z if exterior_sign > 0 else prism.rectangle.min_z
            )
            void_coordinate = prism.rectangle.min_z if exterior_sign > 0 else prism.rectangle.max_z
            exterior_geometry = _rectangle_face_z(placed, prism, exterior_coordinate, exterior_sign)
            void_geometry = _rectangle_face_z(placed, prism, void_coordinate, -exterior_sign)
        else:
            exterior_coordinate = (
                prism.rectangle.max_y if exterior_sign > 0 else prism.rectangle.min_y
            )
            void_coordinate = prism.rectangle.min_y if exterior_sign > 0 else prism.rectangle.max_y
            exterior_geometry = _rectangle_face_y(placed, prism, exterior_coordinate, exterior_sign)
            void_geometry = _rectangle_face_y(placed, prism, void_coordinate, -exterior_sign)
        patches.extend(
            (
                _patch(
                    wall.source_element.id,
                    "EXTERIOR_BROAD",
                    f"{wall.source_element.label} exterior broad surface",
                    placed.participant,
                    SurfaceExposure.EXTERIOR_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    (
                        SurfacePatchRole.POSITIVE_THICKNESS_FACE
                        if exterior_sign > 0
                        else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                    ),
                    exterior_geometry,
                ),
                _patch(
                    wall.source_element.id,
                    "VOID_FACING_BROAD",
                    f"{wall.source_element.label} void-facing broad surface",
                    placed.participant,
                    SurfaceExposure.VOID_EXPOSED,
                    SurfaceDisposition.REGULAR,
                    (
                        SurfacePatchRole.NEGATIVE_THICKNESS_FACE
                        if exterior_sign > 0
                        else SurfacePatchRole.POSITIVE_THICKNESS_FACE
                    ),
                    void_geometry,
                ),
            )
        )
        patches.extend(_physical_end_patches(placed, wall, prism))
    for deferred in placed.deferred_features:
        patches.extend(_deferred_prism_patches(placed, deferred))
    return patches


def _angle_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    leg_1 = _physical_by_role(placed, PhysicalSectionElementRole.LEG_1)
    leg_1_prism = _rectangular_prism(leg_1)
    patches.extend(
        (
            _patch(
                leg_1.source_element.id,
                "EXTERIOR_TT_BROAD",
                f"{leg_1.source_element.label} exterior broad surface",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
                _rectangle_face_z(placed, leg_1_prism, leg_1_prism.rectangle.min_z, -1),
            ),
            _patch(
                leg_1.source_element.id,
                "OPEN_AREA_TT_BROAD",
                f"{leg_1.source_element.label} open-area broad surface",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.POSITIVE_THICKNESS_FACE,
                _rectangle_face_z(placed, leg_1_prism, leg_1_prism.rectangle.max_z, 1),
            ),
            _patch(
                leg_1.source_element.id,
                "FREE_EDGE",
                f"{leg_1.source_element.label} free edge",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.EDGE_FACE,
                _rectangle_face_y(placed, leg_1_prism, leg_1_prism.rectangle.max_y, 1),
            ),
        )
    )
    patches.extend(_physical_end_patches(placed, leg_1, leg_1_prism))

    leg_2 = _physical_by_role(placed, PhysicalSectionElementRole.LEG_2)
    leg_2_prism = _rectangular_prism(leg_2)
    patches.extend(
        (
            _patch(
                leg_2.source_element.id,
                "EXTERIOR_TT_BROAD",
                f"{leg_2.source_element.label} exterior broad surface",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
                _rectangle_face_y(placed, leg_2_prism, leg_2_prism.rectangle.min_y, -1),
            ),
            _patch(
                leg_2.source_element.id,
                "OPEN_AREA_TT_BROAD",
                f"{leg_2.source_element.label} open-area broad surface",
                placed.participant,
                SurfaceExposure.VOID_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.POSITIVE_THICKNESS_FACE,
                _rectangle_face_y(placed, leg_2_prism, leg_2_prism.rectangle.max_y, 1),
            ),
            _patch(
                leg_2.source_element.id,
                "FREE_EDGE",
                f"{leg_2.source_element.label} free edge",
                placed.participant,
                SurfaceExposure.EXTERIOR_EXPOSED,
                SurfaceDisposition.REGULAR,
                SurfacePatchRole.EDGE_FACE,
                _rectangle_face_z(placed, leg_2_prism, leg_2_prism.rectangle.max_z, 1),
            ),
        )
    )
    patches.extend(_physical_end_patches(placed, leg_2, leg_2_prism))
    if len(placed.deferred_features) != 1:
        raise ValueError("A standard angle requires exactly one deferred heel.")
    patches.extend(_deferred_prism_patches(placed, placed.deferred_features[0]))
    return patches


def _plate_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    plate = _physical_by_role(placed, PhysicalSectionElementRole.PLATE)
    prism = _rectangular_prism(plate)
    patches = [
        _patch(
            plate.source_element.id,
            suffix,
            f"{plate.source_element.label} {suffix.lower().replace('_', ' ')}",
            placed.participant,
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            role,
            geometry,
        )
        for suffix, role, geometry in (
            (
                "NEGATIVE_TT_BROAD",
                SurfacePatchRole.NEGATIVE_THICKNESS_FACE,
                _rectangle_face_z(placed, prism, prism.rectangle.min_z, -1),
            ),
            (
                "POSITIVE_TT_BROAD",
                SurfacePatchRole.POSITIVE_THICKNESS_FACE,
                _rectangle_face_z(placed, prism, prism.rectangle.max_z, 1),
            ),
            (
                "NEGATIVE_CW_EDGE",
                SurfacePatchRole.EDGE_FACE,
                _rectangle_face_y(placed, prism, prism.rectangle.min_y, -1),
            ),
            (
                "POSITIVE_CW_EDGE",
                SurfacePatchRole.EDGE_FACE,
                _rectangle_face_y(placed, prism, prism.rectangle.max_y, 1),
            ),
        )
    ]
    patches.extend(_physical_end_patches(placed, plate, prism))
    return patches


def _round_tube_patches(placed: PlacedComponentGeometry3D) -> list[SurfacePatch3D]:
    curved = _physical_by_role(placed, PhysicalSectionElementRole.CURVED_WALL)
    if len(curved.extrusions) != 1 or not isinstance(curved.extrusions[0], LocalAnnularCylinder3D):
        raise ValueError("A standard round tube requires one analytic annular cylinder.")
    extrusion = curved.extrusions[0]
    axis_frame = _axis_frame_for_annulus(placed, extrusion)
    source_id = curved.source_element.id
    return [
        _patch(
            source_id,
            "OUTER_CYLINDER",
            f"{curved.source_element.label} outer cylinder",
            placed.participant,
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.OUTER_CYLINDRICAL_FACE,
            AnalyticCylindricalSurface3D(
                axis_frame,
                extrusion.extent,
                extrusion.annulus.outer_radius,
                RadialNormalSense.OUTWARD,
            ),
        ),
        _patch(
            source_id,
            "INNER_CYLINDER",
            f"{curved.source_element.label} inner cylinder",
            placed.participant,
            SurfaceExposure.VOID_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.INNER_CYLINDRICAL_FACE,
            AnalyticCylindricalSurface3D(
                axis_frame,
                extrusion.extent,
                extrusion.annulus.inner_radius,
                RadialNormalSense.INWARD,
            ),
        ),
        _patch(
            source_id,
            "MINIMUM_X_END_CUT",
            f"{curved.source_element.label} minimum-x annular end cut",
            placed.participant,
            SurfaceExposure.END_CUT,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.ANNULAR_END_FACE,
            _annular_end_face(placed, extrusion, maximum=False),
        ),
        _patch(
            source_id,
            "MAXIMUM_X_END_CUT",
            f"{curved.source_element.label} maximum-x annular end cut",
            placed.participant,
            SurfaceExposure.END_CUT,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.ANNULAR_END_FACE,
            _annular_end_face(placed, extrusion, maximum=True),
        ),
    ]


def _deferred_line_patches(
    placed: PlacedComponentGeometry3D,
) -> list[SurfacePatch3D]:
    patches: list[SurfacePatch3D] = []
    for deferred in placed.deferred_features:
        if not isinstance(deferred.extrusion, LocalRuledSurface3D):
            raise ValueError("This standard family requires deferred ruled surfaces.")
        patches.append(
            _patch(
                deferred.source_feature.id,
                "INTERNAL_JUNCTION",
                deferred.source_feature.label,
                placed.participant,
                SurfaceExposure.INTERNAL_JUNCTION,
                SurfaceDisposition.DEFERRED,
                SurfacePatchRole.JUNCTION_FACE,
                _ruled_surface_face(placed, deferred.extrusion),
                deferred=True,
            )
        )
    return patches


def _deferred_prism_patches(
    placed: PlacedComponentGeometry3D,
    deferred: PlacedDeferredFeature3D,
) -> list[SurfacePatch3D]:
    if not isinstance(deferred.extrusion, LocalRectangularPrism3D):
        raise ValueError("Deferred heel/corner features require rectangular prisms.")
    prism = deferred.extrusion
    bounds = placed.outside_bounds.shifted_section_bounds
    source_id = deferred.source_feature.id
    side_definitions: list[tuple[str, SurfaceExposure, PlanarRectangularSurface3D]] = []
    for axis, coordinate, sign, is_exterior in (
        ("Y", prism.rectangle.min_y, -1, prism.rectangle.min_y == bounds.min_y),
        ("Y", prism.rectangle.max_y, 1, prism.rectangle.max_y == bounds.max_y),
        ("Z", prism.rectangle.min_z, -1, prism.rectangle.min_z == bounds.min_z),
        ("Z", prism.rectangle.max_z, 1, prism.rectangle.max_z == bounds.max_z),
    ):
        exposure = (
            SurfaceExposure.EXTERIOR_EXPOSED if is_exterior else SurfaceExposure.INTERNAL_JUNCTION
        )
        geometry = (
            _rectangle_face_y(placed, prism, coordinate, sign)
            if axis == "Y"
            else _rectangle_face_z(placed, prism, coordinate, sign)
        )
        sign_name = "POSITIVE" if sign > 0 else "NEGATIVE"
        suffix = f"{sign_name}_{axis}_{'EXTERIOR' if is_exterior else 'INTERNAL_JUNCTION'}"
        side_definitions.append((suffix, exposure, geometry))
    patches = [
        _patch(
            source_id,
            suffix,
            f"{deferred.source_feature.label} {suffix.lower().replace('_', ' ')}",
            placed.participant,
            exposure,
            SurfaceDisposition.DEFERRED,
            SurfacePatchRole.JUNCTION_FACE,
            geometry,
            deferred=True,
        )
        for suffix, exposure, geometry in side_definitions
    ]
    for maximum, suffix in (
        (False, "MINIMUM_X_DEFERRED_END_CUT"),
        (True, "MAXIMUM_X_DEFERRED_END_CUT"),
    ):
        patches.append(
            _patch(
                source_id,
                suffix,
                f"{deferred.source_feature.label} {suffix.lower().replace('_', ' ')}",
                placed.participant,
                SurfaceExposure.END_CUT,
                SurfaceDisposition.DEFERRED,
                SurfacePatchRole.JUNCTION_FACE,
                _rectangle_end_face(placed, prism, maximum=maximum),
                deferred=True,
            )
        )
    if (
        sum(patch.exposure is SurfaceExposure.EXTERIOR_EXPOSED for patch in patches) != 2
        or sum(patch.exposure is SurfaceExposure.INTERNAL_JUNCTION for patch in patches) != 2
    ):
        raise ValueError("Deferred heel/corner prisms require two exterior and two junction sides.")
    return patches


def create_component_surface_set(
    placed_component: PlacedComponentGeometry3D,
) -> ComponentSurfaceSet3D:
    """Create exact deterministic patches for one supported standard placed component."""
    if not isinstance(placed_component, PlacedComponentGeometry3D):
        raise TypeError("placed_component must be a PlacedComponentGeometry3D.")
    topology = placed_component.component.section_topology
    if topology is None or topology.source is not SectionTopologySource.STANDARD:
        raise ValueError("Surface generation supports only explicit standard section topology.")
    family = placed_component.cross_section.section_family
    if topology.standard_family is not family:
        raise ValueError("Placed component topology and source section family must match.")
    if family in {SectionFamily.WIDE_FLANGE, SectionFamily.I_SECTION}:
        patches = _wide_flange_or_i_patches(placed_component)
    elif family is SectionFamily.CHANNEL:
        patches = _channel_patches(placed_component)
    elif family is SectionFamily.TEE:
        patches = _tee_patches(placed_component)
    elif family is SectionFamily.RECTANGULAR_TUBE:
        patches = _tube_patches(placed_component)
    elif family is SectionFamily.ANGLE:
        patches = _angle_patches(placed_component)
    elif family is SectionFamily.PLATE:
        patches = _plate_patches(placed_component)
    elif family is SectionFamily.ROUND_TUBE:
        patches = _round_tube_patches(placed_component)
    else:
        raise ValueError(f"Surface generation is unsupported for {family.value} geometry.")
    return ComponentSurfaceSet3D(
        placed_component.participant,
        placed_component,
        tuple(sorted(patches, key=lambda patch: patch.id)),
    )


def create_bounded_support_surface(
    support: AssemblySupport,
    surface_id: str,
    label: str,
    frame: CartesianFrame3D,
    extent_y: float,
    extent_z: float,
) -> SurfacePatch3D:
    """Create one explicit bounded support plane without inferring a support body."""
    if not isinstance(support, AssemblySupport):
        raise TypeError("support must be an AssemblySupport.")
    geometry = PlanarRectangularSurface3D(frame, extent_y, extent_z)
    participant = ParticipantReference(ParticipantKind.SUPPORT, support.id)
    return SurfacePatch3D(
        surface_id,
        label,
        participant,
        SurfacePatchSource.support(support.id),
        SurfaceExposure.EXTERIOR_EXPOSED,
        SurfaceDisposition.REGULAR,
        SurfacePatchRole.SUPPORT_FACE,
        geometry,
    )


__all__ = (
    "AnalyticCylindricalSurface3D",
    "ComponentSurfaceSet3D",
    "ExactSurfaceGeometry3D",
    "PlanarAnnularSurface3D",
    "PlanarRectangularSurface3D",
    "RadialNormalSense",
    "SurfaceDisposition",
    "SurfaceExposure",
    "SurfaceGeometryKind",
    "SurfacePatch3D",
    "SurfacePatchReference",
    "SurfacePatchSource",
    "SurfaceSourceKind",
    "create_bounded_support_surface",
    "create_component_surface_set",
)
