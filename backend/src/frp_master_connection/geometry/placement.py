"""Exact renderer-neutral placement and longitudinal extrusion geometry."""

import math
from dataclasses import InitVar, dataclass, field
from enum import StrEnum

from frp_master_connection.domain.entities import (
    AssemblyMember,
    ConnectorComponent,
    ParticipantReference,
)
from frp_master_connection.domain.section_topology import (
    MaterialRegion,
    PhysicalSectionElement,
    SectionTopology,
    SectionTopologySource,
)
from frp_master_connection.domain.values import (
    MemberEnd,
    ParticipantKind,
    PositionVector3D,
)
from frp_master_connection.geometry.section import (
    Annulus2D,
    AxisAlignedRectangle2D,
    CrossSectionGeometry2D,
    DeferredSectionFeature2D,
    PhysicalElementGeometry2D,
    ProfileRepresentationKind,
    SectionBoundingBox2D,
    SectionLineSegment2D,
    SectionPoint2D,
    SectionVoid2D,
)
from frp_master_connection.geometry.spatial import (
    CartesianFrame3D,
    UnitVector3D,
    Vector3D,
    build_member_frame,
    vector_between,
)

_CONTROLLED_CONSTRUCTION_KEY = object()


def _require_finite_real(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


def _require_placeable_reference(reference: object, field_name: str) -> ParticipantReference:
    if not isinstance(reference, ParticipantReference):
        raise TypeError(f"{field_name} must be a ParticipantReference.")
    if reference.kind not in {ParticipantKind.MEMBER, ParticipantKind.CONNECTOR_COMPONENT}:
        raise ValueError(f"{field_name} must identify a member or connector component.")
    return reference


def _require_controlled_construction(value: object, type_name: str) -> None:
    if value is not _CONTROLLED_CONSTRUCTION_KEY:
        raise TypeError(f"{type_name} must be derived by a controlled placement builder.")


@dataclass(frozen=True, slots=True)
class LongitudinalExtent:
    """One exact finite increasing interval along component-local x."""

    x_start: float
    x_end: float

    def __post_init__(self) -> None:
        _require_finite_real(self.x_start, "LongitudinalExtent.x_start")
        _require_finite_real(self.x_end, "LongitudinalExtent.x_end")
        if self.x_end <= self.x_start:
            raise ValueError("LongitudinalExtent requires x_end greater than x_start.")
        if not math.isfinite(self.x_end - self.x_start):
            raise ValueError("LongitudinalExtent length must remain finite.")

    @property
    def length(self) -> float:
        """Return the exact longitudinal span."""
        return self.x_end - self.x_start


@dataclass(frozen=True, slots=True)
class SectionDatumOffset:
    """Explicit location of the section construction datum from the reference line."""

    offset_y: float = 0.0
    offset_z: float = 0.0

    def __post_init__(self) -> None:
        _require_finite_real(self.offset_y, "SectionDatumOffset.offset_y")
        _require_finite_real(self.offset_z, "SectionDatumOffset.offset_z")


ZERO_SECTION_DATUM_OFFSET = SectionDatumOffset()


@dataclass(frozen=True, slots=True)
class SectionCoordinates3D:
    """One inverse-mapped local x and unshifted section y-z coordinate."""

    local_x: float
    section_y: float
    section_z: float

    def __post_init__(self) -> None:
        _require_finite_real(self.local_x, "SectionCoordinates3D.local_x")
        _require_finite_real(self.section_y, "SectionCoordinates3D.section_y")
        _require_finite_real(self.section_z, "SectionCoordinates3D.section_z")


class LongitudinalBoundaryKind(StrEnum):
    """Neutral identities for the two physical local-x boundary planes."""

    MINIMUM_LOCAL_X = "MINIMUM_LOCAL_X"
    MAXIMUM_LOCAL_X = "MAXIMUM_LOCAL_X"


@dataclass(frozen=True, slots=True)
class LocalRectangularPrism3D:
    """An exact local rectangular prism without tessellation or solid topology."""

    extent: LongitudinalExtent
    rectangle: AxisAlignedRectangle2D

    def __post_init__(self) -> None:
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("LocalRectangularPrism3D.extent must be a LongitudinalExtent.")
        if not isinstance(self.rectangle, AxisAlignedRectangle2D):
            raise TypeError("LocalRectangularPrism3D.rectangle must be an AxisAlignedRectangle2D.")


@dataclass(frozen=True, slots=True)
class LocalAnnularCylinder3D:
    """An exact finite local annular cylinder without polygonization."""

    extent: LongitudinalExtent
    annulus: Annulus2D

    def __post_init__(self) -> None:
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("LocalAnnularCylinder3D.extent must be a LongitudinalExtent.")
        if not isinstance(self.annulus, Annulus2D):
            raise TypeError("LocalAnnularCylinder3D.annulus must be an Annulus2D.")


@dataclass(frozen=True, slots=True)
class LocalRuledSurface3D:
    """An exact zero-thickness surface from a local line extruded along x."""

    extent: LongitudinalExtent
    line: SectionLineSegment2D
    is_zero_thickness: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("LocalRuledSurface3D.extent must be a LongitudinalExtent.")
        if not isinstance(self.line, SectionLineSegment2D):
            raise TypeError("LocalRuledSurface3D.line must be a SectionLineSegment2D.")


type LocalPhysicalExtrusion3D = LocalRectangularPrism3D | LocalAnnularCylinder3D
type LocalDeferredExtrusion3D = LocalRectangularPrism3D | LocalRuledSurface3D


@dataclass(frozen=True, slots=True)
class PlacedPhysicalElement3D:
    """Placed exact extrusion(s) for one topology physical-element occurrence."""

    component: ParticipantReference
    source_element: PhysicalSectionElement
    source_material_region: MaterialRegion
    source_geometry: PhysicalElementGeometry2D
    global_frame: CartesianFrame3D
    extrusions: tuple[LocalPhysicalExtrusion3D, ...]
    _construction_key: InitVar[object] = None
    is_targetable: bool = field(default=True, init=False)

    def __post_init__(self, _construction_key: object) -> None:
        _require_placeable_reference(self.component, "PlacedPhysicalElement3D.component")
        if not isinstance(self.source_element, PhysicalSectionElement):
            raise TypeError(
                "PlacedPhysicalElement3D.source_element must be a PhysicalSectionElement."
            )
        if not isinstance(self.source_material_region, MaterialRegion):
            raise TypeError(
                "PlacedPhysicalElement3D.source_material_region must be a MaterialRegion."
            )
        if self.source_element.material_region_id != self.source_material_region.id:
            raise ValueError("Placed physical element and material-region identities must match.")
        if not isinstance(self.source_geometry, PhysicalElementGeometry2D):
            raise TypeError(
                "PlacedPhysicalElement3D.source_geometry must be PhysicalElementGeometry2D."
            )
        if self.source_element.id != self.source_geometry.element_id:
            raise ValueError("Placed physical element and source geometry IDs must match.")
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("PlacedPhysicalElement3D.global_frame must be a CartesianFrame3D.")
        if not isinstance(self.extrusions, tuple):
            raise TypeError("PlacedPhysicalElement3D.extrusions must be a tuple.")
        if not self.extrusions:
            raise ValueError("PlacedPhysicalElement3D.extrusions must not be empty.")
        if any(
            not isinstance(extrusion, (LocalRectangularPrism3D, LocalAnnularCylinder3D))
            for extrusion in self.extrusions
        ):
            raise TypeError("Placed physical extrusions must be exact supported primitives.")
        _require_controlled_construction(_construction_key, "PlacedPhysicalElement3D")


@dataclass(frozen=True, slots=True)
class PlacedDeferredFeature3D:
    """One extruded deferred feature with no targetability or material ownership."""

    component: ParticipantReference
    source_feature: DeferredSectionFeature2D
    global_frame: CartesianFrame3D
    extrusion: LocalDeferredExtrusion3D
    _construction_key: InitVar[object] = None
    is_deferred: bool = field(default=True, init=False)
    is_targetable: bool = field(default=False, init=False)

    def __post_init__(self, _construction_key: object) -> None:
        _require_placeable_reference(self.component, "PlacedDeferredFeature3D.component")
        if not isinstance(self.source_feature, DeferredSectionFeature2D):
            raise TypeError(
                "PlacedDeferredFeature3D.source_feature must be DeferredSectionFeature2D."
            )
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("PlacedDeferredFeature3D.global_frame must be a CartesianFrame3D.")
        if isinstance(self.source_feature.geometry, AxisAlignedRectangle2D):
            if not isinstance(self.extrusion, LocalRectangularPrism3D):
                raise TypeError("A deferred rectangle requires a rectangular-prism extrusion.")
        elif not isinstance(self.extrusion, LocalRuledSurface3D):
            raise TypeError("A deferred line requires a ruled-surface extrusion.")
        _require_controlled_construction(_construction_key, "PlacedDeferredFeature3D")


@dataclass(frozen=True, slots=True)
class PlacedSectionVoid3D:
    """One exact local void prism, retained without Boolean subtraction."""

    component: ParticipantReference
    source_void: SectionVoid2D
    global_frame: CartesianFrame3D
    extrusion: LocalRectangularPrism3D
    _construction_key: InitVar[object] = None
    is_material: bool = field(default=False, init=False)
    is_physical_element: bool = field(default=False, init=False)
    is_targetable: bool = field(default=False, init=False)

    def __post_init__(self, _construction_key: object) -> None:
        _require_placeable_reference(self.component, "PlacedSectionVoid3D.component")
        if not isinstance(self.source_void, SectionVoid2D):
            raise TypeError("PlacedSectionVoid3D.source_void must be a SectionVoid2D.")
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("PlacedSectionVoid3D.global_frame must be a CartesianFrame3D.")
        if not isinstance(self.extrusion, LocalRectangularPrism3D):
            raise TypeError("PlacedSectionVoid3D.extrusion must be a LocalRectangularPrism3D.")
        _require_controlled_construction(_construction_key, "PlacedSectionVoid3D")


@dataclass(frozen=True, slots=True)
class PhysicalLongitudinalBoundaryPlane3D:
    """One physical component boundary plane with a signed outward global normal."""

    component: ParticipantReference
    boundary: LongitudinalBoundaryKind
    local_x: float
    reference_line_point: PositionVector3D
    section_datum_point: PositionVector3D
    outward_normal: UnitVector3D
    global_frame: CartesianFrame3D
    member_end: MemberEnd | None
    is_connected_member_end: bool | None
    _construction_key: InitVar[object] = None
    is_targetable: bool = field(default=False, init=False)

    def __post_init__(self, _construction_key: object) -> None:
        component = _require_placeable_reference(
            self.component, "PhysicalLongitudinalBoundaryPlane3D.component"
        )
        if not isinstance(self.boundary, LongitudinalBoundaryKind):
            raise TypeError("PhysicalLongitudinalBoundaryPlane3D.boundary must be a boundary kind.")
        _require_finite_real(self.local_x, "PhysicalLongitudinalBoundaryPlane3D.local_x")
        if not isinstance(self.reference_line_point, PositionVector3D):
            raise TypeError("Boundary reference_line_point must be a PositionVector3D.")
        if not isinstance(self.section_datum_point, PositionVector3D):
            raise TypeError("Boundary section_datum_point must be a PositionVector3D.")
        if not isinstance(self.outward_normal, UnitVector3D):
            raise TypeError("Boundary outward_normal must be a UnitVector3D.")
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("Boundary global_frame must be a CartesianFrame3D.")
        expected_normal = (
            -self.global_frame.x_axis
            if self.boundary is LongitudinalBoundaryKind.MINIMUM_LOCAL_X
            else self.global_frame.x_axis
        )
        if self.outward_normal != expected_normal:
            raise ValueError("Boundary outward normal must follow the local-x sign convention.")
        if component.kind is ParticipantKind.MEMBER:
            if not isinstance(self.member_end, MemberEnd):
                raise TypeError("A member boundary requires a MemberEnd identity.")
            expected_end = (
                MemberEnd.START
                if self.boundary is LongitudinalBoundaryKind.MINIMUM_LOCAL_X
                else MemberEnd.END
            )
            if self.member_end is not expected_end:
                raise ValueError("Member START/END must map to minimum/maximum local x.")
            if not isinstance(self.is_connected_member_end, bool):
                raise TypeError("A member boundary requires connected-end status.")
        elif self.member_end is not None or self.is_connected_member_end is not None:
            raise ValueError("A connector boundary has no member START/END semantics.")
        _require_controlled_construction(
            _construction_key,
            "PhysicalLongitudinalBoundaryPlane3D",
        )


@dataclass(frozen=True, slots=True)
class PlacedOutsideBounds3D:
    """Renderer-neutral extruded nominal outside bounds in the global placement frame."""

    global_frame: CartesianFrame3D
    extent: LongitudinalExtent
    shifted_section_bounds: SectionBoundingBox2D
    profile_kind: ProfileRepresentationKind

    def __post_init__(self) -> None:
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("PlacedOutsideBounds3D.global_frame must be a CartesianFrame3D.")
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("PlacedOutsideBounds3D.extent must be a LongitudinalExtent.")
        if not isinstance(self.shifted_section_bounds, SectionBoundingBox2D):
            raise TypeError(
                "PlacedOutsideBounds3D.shifted_section_bounds must be a SectionBoundingBox2D."
            )
        if not isinstance(self.profile_kind, ProfileRepresentationKind):
            raise TypeError("PlacedOutsideBounds3D.profile_kind must be a profile kind.")

    @property
    def global_corners(self) -> tuple[PositionVector3D, ...]:
        """Return eight deterministic corners of the extruded nominal outside box."""
        bounds = self.shifted_section_bounds
        local_corners = (
            PositionVector3D(self.extent.x_start, bounds.min_y, bounds.min_z),
            PositionVector3D(self.extent.x_start, bounds.min_y, bounds.max_z),
            PositionVector3D(self.extent.x_start, bounds.max_y, bounds.min_z),
            PositionVector3D(self.extent.x_start, bounds.max_y, bounds.max_z),
            PositionVector3D(self.extent.x_end, bounds.min_y, bounds.min_z),
            PositionVector3D(self.extent.x_end, bounds.min_y, bounds.max_z),
            PositionVector3D(self.extent.x_end, bounds.max_y, bounds.min_z),
            PositionVector3D(self.extent.x_end, bounds.max_y, bounds.max_z),
        )
        return tuple(self.global_frame.local_to_parent_point(point) for point in local_corners)


def _component_topology(
    component: AssemblyMember | ConnectorComponent,
) -> SectionTopology:
    topology = component.section_topology
    if topology is None:
        raise ValueError("Placement requires explicit component section topology.")
    if topology.validate():
        raise ValueError("Placement requires valid component section topology.")
    return topology


def _validate_geometry_compatibility(
    component: AssemblyMember | ConnectorComponent,
    cross_section: CrossSectionGeometry2D,
) -> SectionTopology:
    topology = _component_topology(component)
    if (
        isinstance(component, AssemblyMember)
        and cross_section.section_family is not component.section_family
    ):
        raise ValueError("Member cross-section family must match AssemblyMember.section_family.")
    if (
        topology.source is SectionTopologySource.STANDARD
        and topology.standard_family is not cross_section.section_family
    ):
        raise ValueError("Cross-section family must match the component's standard topology.")
    topology_ids = tuple(element.id for element in topology.elements)
    geometry_ids = tuple(mapping.element_id for mapping in cross_section.physical_elements)
    if len(topology_ids) != len(geometry_ids) or set(topology_ids) != set(geometry_ids):
        raise ValueError("Cross-section geometry must map every topology element exactly once.")
    return topology


def _shift_point(point: SectionPoint2D, offset: SectionDatumOffset) -> SectionPoint2D:
    return SectionPoint2D(point.y + offset.offset_y, point.z + offset.offset_z)


def _shift_rectangle(
    rectangle: AxisAlignedRectangle2D,
    offset: SectionDatumOffset,
) -> AxisAlignedRectangle2D:
    return AxisAlignedRectangle2D(
        rectangle.min_y + offset.offset_y,
        rectangle.max_y + offset.offset_y,
        rectangle.min_z + offset.offset_z,
        rectangle.max_z + offset.offset_z,
    )


def _shift_line(
    line: SectionLineSegment2D,
    offset: SectionDatumOffset,
) -> SectionLineSegment2D:
    return SectionLineSegment2D(
        _shift_point(line.start, offset),
        _shift_point(line.end, offset),
    )


def _shift_annulus(annulus: Annulus2D, offset: SectionDatumOffset) -> Annulus2D:
    return Annulus2D(
        _shift_point(annulus.center, offset),
        annulus.outer_radius,
        annulus.inner_radius,
    )


def _map_local_point(
    frame: CartesianFrame3D,
    local_x: float,
    local_y: float,
    local_z: float,
) -> PositionVector3D:
    return frame.local_to_parent_point(PositionVector3D(local_x, local_y, local_z))


def _physical_extrusions(
    source: PhysicalElementGeometry2D,
    extent: LongitudinalExtent,
    offset: SectionDatumOffset,
) -> tuple[LocalPhysicalExtrusion3D, ...]:
    extrusions: list[LocalPhysicalExtrusion3D] = []
    for primitive in source.geometry:
        if isinstance(primitive, AxisAlignedRectangle2D):
            extrusions.append(LocalRectangularPrism3D(extent, _shift_rectangle(primitive, offset)))
        else:
            extrusions.append(LocalAnnularCylinder3D(extent, _shift_annulus(primitive, offset)))
    return tuple(extrusions)


def _deferred_extrusion(
    source: DeferredSectionFeature2D,
    extent: LongitudinalExtent,
    offset: SectionDatumOffset,
) -> LocalDeferredExtrusion3D:
    if isinstance(source.geometry, AxisAlignedRectangle2D):
        return LocalRectangularPrism3D(extent, _shift_rectangle(source.geometry, offset))
    return LocalRuledSurface3D(extent, _shift_line(source.geometry, offset))


@dataclass(frozen=True, slots=True)
class PlacedComponentGeometry3D:
    """One authoritative, already-resolved member or connector global placement.

    Use :func:`place_member` when the authoritative inputs are physical START/END points.
    """

    component: AssemblyMember | ConnectorComponent
    global_frame: CartesianFrame3D
    extent: LongitudinalExtent
    section_offset: SectionDatumOffset
    cross_section: CrossSectionGeometry2D
    _construction_key: InitVar[object] = None
    participant: ParticipantReference = field(init=False)
    physical_elements: tuple[PlacedPhysicalElement3D, ...] = field(init=False)
    deferred_features: tuple[PlacedDeferredFeature3D, ...] = field(init=False)
    nominal_voids: tuple[PlacedSectionVoid3D, ...] = field(init=False)
    minimum_x_boundary: PhysicalLongitudinalBoundaryPlane3D = field(init=False)
    maximum_x_boundary: PhysicalLongitudinalBoundaryPlane3D = field(init=False)
    outside_bounds: PlacedOutsideBounds3D = field(init=False)

    def __post_init__(self, _construction_key: object) -> None:
        if not isinstance(self.component, (AssemblyMember, ConnectorComponent)):
            raise TypeError("PlacedComponentGeometry3D.component must be a member or connector.")
        if not isinstance(self.global_frame, CartesianFrame3D):
            raise TypeError("PlacedComponentGeometry3D.global_frame must be a CartesianFrame3D.")
        if not isinstance(self.extent, LongitudinalExtent):
            raise TypeError("PlacedComponentGeometry3D.extent must be a LongitudinalExtent.")
        if not isinstance(self.section_offset, SectionDatumOffset):
            raise TypeError(
                "PlacedComponentGeometry3D.section_offset must be a SectionDatumOffset."
            )
        if not isinstance(self.cross_section, CrossSectionGeometry2D):
            raise TypeError(
                "PlacedComponentGeometry3D.cross_section must be CrossSectionGeometry2D."
            )
        if isinstance(self.component, AssemblyMember) and self.extent.x_start != 0.0:
            raise ValueError("A placed member extent must start at local x = 0.")

        topology = _validate_geometry_compatibility(self.component, self.cross_section)
        _require_controlled_construction(_construction_key, "PlacedComponentGeometry3D")
        participant_kind = (
            ParticipantKind.MEMBER
            if isinstance(self.component, AssemblyMember)
            else ParticipantKind.CONNECTOR_COMPONENT
        )
        participant = ParticipantReference(participant_kind, self.component.id)
        elements_by_id = {element.id: element for element in topology.elements}
        regions_by_id = {region.id: region for region in topology.material_regions}
        placed_elements = tuple(
            PlacedPhysicalElement3D(
                participant,
                elements_by_id[source.element_id],
                regions_by_id[elements_by_id[source.element_id].material_region_id],
                source,
                self.global_frame,
                _physical_extrusions(source, self.extent, self.section_offset),
                _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
            )
            for source in self.cross_section.physical_elements
        )
        deferred_features = tuple(
            PlacedDeferredFeature3D(
                participant,
                source,
                self.global_frame,
                _deferred_extrusion(source, self.extent, self.section_offset),
                _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
            )
            for source in self.cross_section.deferred_features
        )
        nominal_voids = tuple(
            PlacedSectionVoid3D(
                participant,
                source,
                self.global_frame,
                LocalRectangularPrism3D(
                    self.extent,
                    _shift_rectangle(source.geometry, self.section_offset),
                ),
                _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
            )
            for source in self.cross_section.nominal_voids
        )

        member = self.component if isinstance(self.component, AssemblyMember) else None
        minimum_member_end = MemberEnd.START if member is not None else None
        maximum_member_end = MemberEnd.END if member is not None else None
        minimum_connected = member.connected_end is MemberEnd.START if member is not None else None
        maximum_connected = member.connected_end is MemberEnd.END if member is not None else None
        minimum_boundary = self._make_boundary(
            participant,
            LongitudinalBoundaryKind.MINIMUM_LOCAL_X,
            self.extent.x_start,
            minimum_member_end,
            minimum_connected,
        )
        maximum_boundary = self._make_boundary(
            participant,
            LongitudinalBoundaryKind.MAXIMUM_LOCAL_X,
            self.extent.x_end,
            maximum_member_end,
            maximum_connected,
        )
        source_bounds = self.cross_section.outside_bounds
        shifted_bounds = SectionBoundingBox2D(
            source_bounds.min_y + self.section_offset.offset_y,
            source_bounds.max_y + self.section_offset.offset_y,
            source_bounds.min_z + self.section_offset.offset_z,
            source_bounds.max_z + self.section_offset.offset_z,
        )

        object.__setattr__(self, "participant", participant)
        object.__setattr__(self, "physical_elements", placed_elements)
        object.__setattr__(self, "deferred_features", deferred_features)
        object.__setattr__(self, "nominal_voids", nominal_voids)
        object.__setattr__(self, "minimum_x_boundary", minimum_boundary)
        object.__setattr__(self, "maximum_x_boundary", maximum_boundary)
        object.__setattr__(
            self,
            "outside_bounds",
            PlacedOutsideBounds3D(
                self.global_frame,
                self.extent,
                shifted_bounds,
                self.cross_section.profile_kind,
            ),
        )

    def _make_boundary(
        self,
        participant: ParticipantReference,
        boundary: LongitudinalBoundaryKind,
        local_x: float,
        member_end: MemberEnd | None,
        connected: bool | None,
    ) -> PhysicalLongitudinalBoundaryPlane3D:
        outward_normal = (
            -self.global_frame.x_axis
            if boundary is LongitudinalBoundaryKind.MINIMUM_LOCAL_X
            else self.global_frame.x_axis
        )
        return PhysicalLongitudinalBoundaryPlane3D(
            participant,
            boundary,
            local_x,
            _map_local_point(self.global_frame, local_x, 0.0, 0.0),
            _map_local_point(
                self.global_frame,
                local_x,
                self.section_offset.offset_y,
                self.section_offset.offset_z,
            ),
            outward_normal,
            self.global_frame,
            member_end,
            connected,
            _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
        )

    def section_point_to_local(
        self,
        local_x: float,
        section_point: SectionPoint2D,
    ) -> PositionVector3D:
        """Map one source section point into component-local coordinates without clamping."""
        _require_finite_real(local_x, "local_x")
        if not isinstance(section_point, SectionPoint2D):
            raise TypeError("section_point must be a SectionPoint2D.")
        return PositionVector3D(
            local_x,
            section_point.y + self.section_offset.offset_y,
            section_point.z + self.section_offset.offset_z,
        )

    def section_point_to_global(
        self,
        local_x: float,
        section_point: SectionPoint2D,
    ) -> PositionVector3D:
        """Map one source section point directly into canonical global coordinates."""
        return self.global_frame.local_to_parent_point(
            self.section_point_to_local(local_x, section_point)
        )

    def global_to_local(self, point: PositionVector3D) -> PositionVector3D:
        """Inverse-map a global point without projection or extent clamping."""
        return self.global_frame.parent_to_local_point(point)

    def global_to_section_coordinates(self, point: PositionVector3D) -> SectionCoordinates3D:
        """Inverse-map a global point and remove the explicit section offset."""
        local = self.global_to_local(point)
        return SectionCoordinates3D(
            local.x,
            local.y - self.section_offset.offset_y,
            local.z - self.section_offset.offset_z,
        )

    def reference_line_point(self, local_x: float) -> PositionVector3D:
        """Return the global component reference-line point at the supplied local x."""
        _require_finite_real(local_x, "local_x")
        return _map_local_point(self.global_frame, local_x, 0.0, 0.0)

    def section_datum_line_point(self, local_x: float) -> PositionVector3D:
        """Return the global shifted section-datum-line point at the supplied local x."""
        _require_finite_real(local_x, "local_x")
        return _map_local_point(
            self.global_frame,
            local_x,
            self.section_offset.offset_y,
            self.section_offset.offset_z,
        )

    def boundary_for_member_end(
        self,
        member_end: MemberEnd,
    ) -> PhysicalLongitudinalBoundaryPlane3D:
        """Return the exact START or END physical plane for a placed member."""
        if not isinstance(self.component, AssemblyMember):
            raise ValueError("Connector placements have no member START/END semantics.")
        if not isinstance(member_end, MemberEnd):
            raise TypeError("member_end must be a MemberEnd.")
        if member_end is MemberEnd.START:
            return self.minimum_x_boundary
        return self.maximum_x_boundary

    @property
    def connected_end_plane(self) -> PhysicalLongitudinalBoundaryPlane3D | None:
        """Return the authoritative connected-end plane, or None for a connector."""
        if not isinstance(self.component, AssemblyMember):
            return None
        return self.boundary_for_member_end(self.component.connected_end)


def place_member(
    member: AssemblyMember,
    cross_section: CrossSectionGeometry2D,
    start: PositionVector3D,
    end: PositionVector3D,
    local_z_reference: Vector3D,
    section_offset: SectionDatumOffset = ZERO_SECTION_DATUM_OFFSET,
) -> PlacedComponentGeometry3D:
    """Place a member with local +x fixed from physical START to physical END."""
    if not isinstance(member, AssemblyMember):
        raise TypeError("member must be an AssemblyMember.")
    if not isinstance(start, PositionVector3D):
        raise TypeError("start must be a PositionVector3D.")
    if not isinstance(end, PositionVector3D):
        raise TypeError("end must be a PositionVector3D.")
    displacement = vector_between(start, end)
    length = displacement.norm
    if length == 0.0:
        raise ValueError("Member START and END must be distinct.")
    frame = build_member_frame(start, end, local_z_reference)
    return PlacedComponentGeometry3D(
        member,
        frame,
        LongitudinalExtent(0.0, length),
        section_offset,
        cross_section,
        _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
    )


def place_connector(
    connector: ConnectorComponent,
    cross_section: CrossSectionGeometry2D,
    global_frame: CartesianFrame3D,
    extent: LongitudinalExtent,
    section_offset: SectionDatumOffset,
) -> PlacedComponentGeometry3D:
    """Place a connector with one explicit proper global frame and local-x extent."""
    if not isinstance(connector, ConnectorComponent):
        raise TypeError("connector must be a ConnectorComponent.")
    return PlacedComponentGeometry3D(
        connector,
        global_frame,
        extent,
        section_offset,
        cross_section,
        _construction_key=_CONTROLLED_CONSTRUCTION_KEY,
    )


__all__ = (
    "ZERO_SECTION_DATUM_OFFSET",
    "LocalAnnularCylinder3D",
    "LocalDeferredExtrusion3D",
    "LocalPhysicalExtrusion3D",
    "LocalRectangularPrism3D",
    "LocalRuledSurface3D",
    "LongitudinalBoundaryKind",
    "LongitudinalExtent",
    "PhysicalLongitudinalBoundaryPlane3D",
    "PlacedComponentGeometry3D",
    "PlacedDeferredFeature3D",
    "PlacedOutsideBounds3D",
    "PlacedPhysicalElement3D",
    "PlacedSectionVoid3D",
    "SectionCoordinates3D",
    "SectionDatumOffset",
    "place_connector",
    "place_member",
)
