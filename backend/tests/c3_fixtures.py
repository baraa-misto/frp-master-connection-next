"""Integrated Stage 1.3C3 geometry fixture shared by focused tests."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from frp_master_connection.domain import (
    ActionConvention,
    AssemblyMember,
    BoltGroup,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ForceVector3D,
    FRPComponentOrientation,
    JointAssembly,
    LoadCombination,
    LoadInputBasis,
    ManualMemberEndAction,
    MemberEnd,
    MemberRole,
    MomentVector3D,
    ParticipantKind,
    ParticipantReference,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SectionTopology,
    TransferIntent,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    BoltGroupGeometrySpecification,
    BoltPathDefinition,
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    CrossSectionGeometry2D,
    GeometryComparisonTolerance,
    IntendedPenetratedLayer,
    InterfaceOriginSpecification,
    InterfaceTargetSide,
    InterfaceTargetSideSpecification,
    InterfaceZoneReference,
    JointGeometryBasis,
    JointGeometryContext,
    LongitudinalExtent,
    PlanarRectangularSurface3D,
    PlateDimensions,
    ResolvedBoltGroupGeometry,
    SectionDatumOffset,
    SurfacePatch3D,
    SurfacePatchRole,
    Vector3D,
    create_component_surface_set,
    create_plate_geometry,
    place_connector,
    place_member,
    resolve_bolt_group_geometry,
    resolve_connection_interface_geometry,
    translate_point,
    vector_between,
)


@dataclass(frozen=True, slots=True)
class C3Case:
    assembly: JointAssembly
    basis: JointGeometryBasis
    context: JointGeometryContext
    bolt_specification: BoltGroupGeometrySpecification
    resolved_bolt_group: ResolvedBoltGroupGeometry


def _broad_face_pair(
    surfaces: tuple[SurfacePatch3D, ...],
    physical_element_id: str,
) -> tuple[SurfacePatch3D, SurfacePatch3D, PositionVector3D]:
    negative = tuple(
        patch
        for patch in surfaces
        if patch.source.physical_element_id == physical_element_id
        and patch.role is SurfacePatchRole.NEGATIVE_THICKNESS_FACE
        and isinstance(patch.geometry, PlanarRectangularSurface3D)
    )
    positive = tuple(
        patch
        for patch in surfaces
        if patch.source.physical_element_id == physical_element_id
        and patch.role is SurfacePatchRole.POSITIVE_THICKNESS_FACE
        and isinstance(patch.geometry, PlanarRectangularSurface3D)
    )
    for entry in negative:
        for exit_ in positive:
            entry_geometry = cast(PlanarRectangularSurface3D, entry.geometry)
            exit_geometry = cast(PlanarRectangularSurface3D, exit_.geometry)
            displacement = vector_between(entry_geometry.center, exit_geometry.center)
            thickness = displacement.dot(exit_geometry.normal)
            if entry_geometry.normal != -exit_geometry.normal or thickness <= 0.0:
                continue
            center = translate_point(entry_geometry.center, exit_geometry.normal * thickness)
            entry_local = entry_geometry.frame.parent_to_local_point(entry_geometry.center)
            exit_local = exit_geometry.frame.parent_to_local_point(center)
            entry_clearance = min(
                entry_geometry.extent_y / 2.0 - abs(entry_local.y),
                entry_geometry.extent_z / 2.0 - abs(entry_local.z),
            )
            exit_clearance = min(
                exit_geometry.extent_y / 2.0 - abs(exit_local.y),
                exit_geometry.extent_z / 2.0 - abs(exit_local.z),
            )
            if min(entry_clearance, exit_clearance) >= 0.5:
                return entry, exit_, center
    raise AssertionError(f"No opposing broad-face pair for {physical_element_id!r}.")


def build_c3_case(
    section_family: SectionFamily = SectionFamily.PLATE,
    geometry_factory: Callable[[SectionTopology], CrossSectionGeometry2D] | None = None,
    physical_element_id: str = "PLATE",
    member_offset: SectionDatumOffset | None = None,
    interlayer_gap: float = 0.0,
    pultruded_frp: bool = False,
) -> C3Case:
    if member_offset is None:
        member_offset = SectionDatumOffset(0.0, -1.0)
    if geometry_factory is None:
        if section_family is not SectionFamily.PLATE:
            raise ValueError("A non-plate C3 fixture requires an explicit geometry factory.")

        def plate_factory(topology: SectionTopology) -> CrossSectionGeometry2D:
            return create_plate_geometry(topology, PlateDimensions(4.0, 1.0))

        geometry_factory = plate_factory
    member_topology = create_standard_section_topology(section_family)
    connector_topology = create_standard_section_topology(section_family)
    if pultruded_frp:
        orientations = {
            region.role: PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.Y,
                PrincipalAxisFamily.Z,
            )
            for region in member_topology.material_regions
        }
        member_topology = create_standard_section_topology(
            section_family,
            orientations=orientations,
        )
        connector_topology = create_standard_section_topology(
            section_family,
            orientations=orientations,
        )
    member_frame_reference = CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1")
    connector_frame_reference = CoordinateFrameReference(
        CoordinateFrameKind.CONNECTOR_LOCAL, "connector-1"
    )
    member = AssemblyMember(
        "member-1",
        "Plate member",
        MemberRole.BEAM,
        MemberEnd.START,
        section_family,
        ComponentMaterialKind.PULTRUDED_FRP if pultruded_frp else ComponentMaterialKind.STEEL,
        material_orientation=(
            FRPComponentOrientation(member_frame_reference, PrincipalAxisFamily.X)
            if pultruded_frp
            else None
        ),
        section_topology=member_topology,
    )
    connector = ConnectorComponent(
        "connector-1",
        "Connector plate",
        ConnectorComponentKind.PLATE,
        ComponentMaterialKind.PULTRUDED_FRP if pultruded_frp else ComponentMaterialKind.STEEL,
        material_orientation=(
            FRPComponentOrientation(connector_frame_reference, PrincipalAxisFamily.X)
            if pultruded_frp
            else None
        ),
        section_topology=connector_topology,
    )
    member_ref = ParticipantReference(ParticipantKind.MEMBER, member.id)
    connector_ref = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, connector.id)
    interface = ConnectionInterface(
        "interface-1",
        "Plate-to-plate interface",
        member_ref,
        connector_ref,
        TransferIntent.SHEAR_ONLY,
    )
    bolt_group = BoltGroup(
        "bolt-group-1",
        "Bolt group",
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, "bolt-group-1"),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, "bolt-group-1"),
        (interface.id,),
        (BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0)),),
    )
    load = LoadCombination("load-1", "Factored load", LoadInputBasis.FACTORED_STRENGTH)
    action = ManualMemberEndAction(
        "action-1",
        member.id,
        MemberEnd.START,
        load.id,
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member.id),
        ReferencePoint(ReferencePointKind.MEMBER_CONNECTED_END, member.id),
        ForceVector3D(2.0, 3.0, 5.0),
        MomentVector3D(7.0, 11.0, 13.0),
        ActionConvention.MEMBER_ON_JOINT,
    )
    assembly = JointAssembly(
        "assembly-1",
        "C3 fixture",
        ConnectionDesignCategory.SHEAR,
        EngineeringUnitSystem.SI,
        (member,),
        (connector,),
        (),
        (interface,),
        (bolt_group,),
        (load,),
        (action,),
    )
    member_section = geometry_factory(member_topology)
    connector_section = geometry_factory(connector_topology)
    placed_member = place_member(
        member,
        member_section,
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(0.0, 0.0, 10.0),
        Vector3D(1.0, 0.0, 0.0),
        member_offset,
    )
    member_surfaces = create_component_surface_set(placed_member)
    member_negative, member_positive, bolt_center = _broad_face_pair(
        member_surfaces.patches,
        physical_element_id,
    )
    member_positive_geometry = cast(PlanarRectangularSurface3D, member_positive.geometry)
    thickness = vector_between(
        cast(PlanarRectangularSurface3D, member_negative.geometry).center,
        member_positive_geometry.center,
    ).dot(member_positive_geometry.normal)
    thickness_vector = member_positive_geometry.normal * (thickness + interlayer_gap)
    connector_offset = SectionDatumOffset(
        member_offset.offset_y + thickness_vector.dot(placed_member.global_frame.y_axis),
        member_offset.offset_z + thickness_vector.dot(placed_member.global_frame.z_axis),
    )
    placed_connector = place_connector(
        connector,
        connector_section,
        placed_member.global_frame,
        LongitudinalExtent(0.0, 10.0),
        connector_offset,
    )
    connector_surfaces = create_component_surface_set(placed_connector)
    connector_negative, connector_positive, _connector_bolt_center = _broad_face_pair(
        connector_surfaces.patches,
        physical_element_id,
    )
    first_zone = ConnectionZoneSpecification(
        "first-zone",
        "Member interface zone",
        member_positive.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    second_zone = ConnectionZoneSpecification(
        "second-zone",
        "Connector interface zone",
        connector_negative.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    tolerance = GeometryComparisonTolerance(1.0e-9, 1.0e-9)
    interface_specification = ConnectionInterfaceGeometrySpecification(
        interface,
        InterfaceTargetSideSpecification(member_ref, (first_zone,), first_zone.id),
        InterfaceTargetSideSpecification(connector_ref, (second_zone,), second_zone.id),
        InterfaceOriginSpecification(
            first_zone.id,
            member_positive_geometry.frame.parent_to_local_point(bolt_center).y,
            member_positive_geometry.frame.parent_to_local_point(bolt_center).z,
        ),
        Vector3D(0.0, 0.0, 1.0),
        tolerance,
    )
    resolved_interface = resolve_connection_interface_geometry(
        interface_specification,
        (*member_surfaces.patches, *connector_surfaces.patches),
    )
    basis = JointGeometryBasis(
        assembly,
        placed_member.global_frame,
        (placed_member,),
        (placed_connector,),
        (member_surfaces, connector_surfaces),
        (),
        (resolved_interface,),
    )
    bolt_specification = BoltGroupGeometrySpecification(
        bolt_group,
        interface.id,
        0.0,
        0.0,
        Vector3D(0.0, 0.0, 1.0),
        tolerance,
        (
            BoltPathDefinition(
                "bolt-1",
                (
                    IntendedPenetratedLayer(
                        "member-layer",
                        member_ref,
                        physical_element_id,
                        member_negative.reference,
                        member_positive.reference,
                        (
                            InterfaceZoneReference(
                                interface.id,
                                InterfaceTargetSide.FIRST,
                                first_zone.id,
                            ),
                        ),
                        1.0,
                    ),
                    IntendedPenetratedLayer(
                        "connector-layer",
                        connector_ref,
                        physical_element_id,
                        connector_negative.reference,
                        connector_positive.reference,
                        (
                            InterfaceZoneReference(
                                interface.id,
                                InterfaceTargetSide.SECOND,
                                second_zone.id,
                            ),
                        ),
                        1.0,
                    ),
                ),
            ),
        ),
    )
    resolved_bolt_group = resolve_bolt_group_geometry(basis, bolt_specification)
    context = JointGeometryContext(basis, (resolved_bolt_group,))
    return C3Case(assembly, basis, context, bolt_specification, resolved_bolt_group)


__all__ = ("C3Case", "build_c3_case")
