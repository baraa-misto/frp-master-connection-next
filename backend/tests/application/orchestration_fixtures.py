"""Canonical geometry fixtures for Stage 2.2A orchestration verification."""

from dataclasses import dataclass, replace
from decimal import Decimal
from math import cos, radians, sin
from typing import cast

from frp_master_connection.application import (
    ExplicitBoltDemandAssignment,
    PenetratedLayerMaterialAssignment,
    SingleBoltOrchestrationRequest,
)
from frp_master_connection.calculation import (
    DemandDistributionStatus,
    DemandSourceKind,
    EndUseFactors,
    FastenerSnapshot,
    LapConfiguration,
    LayerLoadingSense,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    PultrudedElementForm,
    ResolvedSingleBoltDemand,
    ThreadStatus,
    ThreadStatusAssignment,
    TimeEffectCategory,
    Unit,
    WasherGeometry,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_synthetic_fastener_snapshot,
    select_time_effect_factor,
)
from frp_master_connection.domain import (
    ActionConvention,
    AssemblyMember,
    BoltGroup,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    ConnectionInterface,
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
    IDENTITY_ROTATION,
    AngleDimensions,
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
    ISectionDimensions,
    JointGeometryBasis,
    JointGeometryContext,
    PlanarRectangularSurface3D,
    PlateDimensions,
    Rotation3D,
    SectionDatumOffset,
    SurfacePatch3D,
    SurfacePatchRole,
    UnitVector3D,
    Vector3D,
    create_angle_geometry,
    create_component_surface_set,
    create_plate_geometry,
    create_wide_flange_geometry,
    place_member,
    resolve_bolt_group_geometry,
    resolve_connection_interface_geometry,
)

_SQRT_HALF = 2**-0.5
_ZERO_TRANSLATION = Vector3D(0.0, 0.0, 0.0)
_J1_VERTICAL_ROTATION = Rotation3D(
    UnitVector3D(0.0, -_SQRT_HALF, _SQRT_HALF),
    UnitVector3D(0.0, _SQRT_HALF, _SQRT_HALF),
    UnitVector3D(-1.0, 0.0, 0.0),
)


@dataclass(frozen=True, slots=True)
class CanonicalOrchestrationCase:
    request: SingleBoltOrchestrationRequest
    context: JointGeometryContext


def _scale(value: float, unit_system: EngineeringUnitSystem) -> float:
    return (
        value
        if unit_system is EngineeringUnitSystem.US_CUSTOMARY
        else float(Decimal(str(value)) * Decimal("25.4"))
    )


def _point(
    x: float,
    y: float,
    z: float,
    unit_system: EngineeringUnitSystem,
) -> PositionVector3D:
    return PositionVector3D(
        _scale(x, unit_system),
        _scale(y, unit_system),
        _scale(z, unit_system),
    )


def _oriented_topology(section_family: SectionFamily) -> SectionTopology:
    source = create_standard_section_topology(section_family)
    orientations = {
        region.role: PlanarFixedMaterialOrientation(
            PrincipalAxisFamily.Y,
            PrincipalAxisFamily.Z,
        )
        for region in source.material_regions
    }
    return create_standard_section_topology(section_family, orientations=orientations)


def _broad_faces(
    surfaces: tuple[SurfacePatch3D, ...],
    element_id: str,
) -> tuple[SurfacePatch3D, SurfacePatch3D]:
    negative = next(
        item
        for item in surfaces
        if item.source.physical_element_id == element_id
        and item.role is SurfacePatchRole.NEGATIVE_THICKNESS_FACE
        and isinstance(item.geometry, PlanarRectangularSurface3D)
    )
    positive = next(
        item
        for item in surfaces
        if item.source.physical_element_id == element_id
        and item.role is SurfacePatchRole.POSITIVE_THICKNESS_FACE
        and isinstance(item.geometry, PlanarRectangularSurface3D)
    )
    return negative, positive


def _fastener(
    *,
    synthetic: bool,
    layer_ids: tuple[str, ...],
    unit_system: EngineeringUnitSystem,
    shear_planes: int = 1,
) -> FastenerSnapshot:
    length_unit = Unit.IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
    washer = WasherGeometry(
        PhysicalQuantity.of("1", Unit.IN).to(length_unit),
        PhysicalQuantity.of("0.051", Unit.IN).to(length_unit),
        True,
        True,
    )
    if synthetic:
        source = create_synthetic_fastener_snapshot(
            id="B1_SYNTHETIC",
            fnt=PhysicalQuantity.of("100", Unit.KSI),
        )
    else:
        source = create_locked_f593_fastener_snapshot()
    statuses = tuple(
        ThreadStatusAssignment(f"shear-plane-{index + 1}", ThreadStatus.EXCLUDED)
        for index in range(shear_planes)
    )
    return replace(
        source,
        shear_plane_thread_statuses=statuses,
        bearing_layer_thread_statuses=tuple(
            ThreadStatusAssignment(layer_id, ThreadStatus.EXCLUDED) for layer_id in layer_ids
        ),
        number_of_shear_planes=shear_planes,
        washer_geometry=washer,
    )


def _request(
    *,
    assembly: JointAssembly,
    context: JointGeometryContext,
    layer_ids: tuple[str, ...],
    demand_kip: str,
    axial_kip: str = "0",
    loading_sense: LayerLoadingSense = LayerLoadingSense.TENSION,
    lap: LapConfiguration = LapConfiguration.DOUBLE_LAP,
    synthetic: bool = False,
    qualification: bool = False,
    explicit_demand: bool = True,
    bearing_statuses: tuple[ThreadStatus, ...] | None = None,
    element_forms: tuple[PultrudedElementForm, ...] | None = None,
    shear_planes: int = 1,
) -> SingleBoltOrchestrationRequest:
    group = context.resolved_bolt_groups[0]
    path = group.paths[0]
    material = create_locked_ice_material_snapshot()
    statuses = bearing_statuses or tuple(ThreadStatus.EXCLUDED for _ in layer_ids)
    forms = element_forms or tuple(PultrudedElementForm.SHAPE_ELEMENT for _ in layer_ids)
    selected_layers = tuple(layer for layer in path.layers if layer.definition.id in layer_ids)
    assignment_by_layer = {
        layer.definition.id: PenetratedLayerMaterialAssignment(
            layer.definition.participant.entity_id,
            layer.definition.physical_element_id,
            layer.physical_element.source_material_region.id,
            material,
            status,
            form,
            layer.definition.physical_element_id not in {"PLATE", "LEG_1"},
        )
        for layer, status, form in zip(selected_layers, statuses, forms, strict=True)
    }
    force_unit = Unit.KIP if assembly.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    demand_value = PhysicalQuantity.of(demand_kip, Unit.KIP).to(force_unit)
    axial_value = PhysicalQuantity.of(axial_kip, Unit.KIP).to(force_unit)
    global_force_direction = path.layers[0].physical_element.global_frame.x_axis
    resolved_force_direction = context.basis.joint_frame.parent_to_local_vector(
        global_force_direction
    )
    demand = ResolvedSingleBoltDemand(
        id="demand-1",
        load_combination_id="LC-1",
        source_member_id="member-a",
        source_action_id="action-1",
        source_kind=DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND,
        factored_action_confirmed=True,
        coordinate_frame_reference="GLOBAL",
        resolved_frame=context.basis.joint_frame,
        source_reference_point_id="member-a:connected-end",
        resolved_global_reference_point=context.basis.placed_members[0].global_frame.origin,
        in_plane_force_vector=Vector3D(
            resolved_force_direction.x * float(demand_value.magnitude),
            resolved_force_direction.y * float(demand_value.magnitude),
            resolved_force_direction.z * float(demand_value.magnitude),
        ),
        force_vector_unit=force_unit,
        bolt_axis_tensile_demand=axial_value,
        externally_supplied_prying_demand=PhysicalQuantity.of("0", force_unit),
        loading_sense=loading_sense,
        provenance=("RC2 explicit resolved per-bolt demand",),
        distribution_status=DemandDistributionStatus.EXPLICITLY_RESOLVED,
    )
    return SingleBoltOrchestrationRequest(
        calculation_id=f"{assembly.id}:calculation",
        assembly=assembly,
        geometry_context=context,
        interface_id="interface-1",
        bolt_group_id="bolt-group-1",
        bolt_location_id="bolt-1",
        load_combination_id="LC-1",
        material_assignments=tuple(assignment_by_layer[layer_id] for layer_id in layer_ids),
        fastener_snapshot=_fastener(
            synthetic=synthetic,
            layer_ids=layer_ids,
            unit_system=assembly.unit_system,
            shear_planes=shear_planes,
        ),
        bolt_diameter=PhysicalQuantity.of("0.500", Unit.IN),
        published_code_unit_basis=PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        time_effect=select_time_effect_factor(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        end_use_factors=EndUseFactors(
            Decimal("1"),
            Decimal("1"),
            Decimal("1"),
            "ASCE/SEI 74-23 Section 2.4.4",
            ("RC2 explicit unity factors",),
        ),
        lap_configuration=lap,
        resolved_demand=(
            ExplicitBoltDemandAssignment(
                "interface-1",
                "bolt-group-1",
                "bolt-1",
                demand,
            )
            if explicit_demand
            else None
        ),
        source_action_id="action-1",
        whole_connection_requires_section_2_3_2=qualification,
    )


def _assembly(
    *,
    unit_system: EngineeringUnitSystem,
    first: AssemblyMember,
    second: AssemblyMember,
    interface: ConnectionInterface,
    bolt_group: BoltGroup,
) -> JointAssembly:
    load = LoadCombination("LC-1", "Factored benchmark", LoadInputBasis.FACTORED_STRENGTH)
    action = ManualMemberEndAction(
        "action-1",
        first.id,
        MemberEnd.START,
        load.id,
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, first.id),
        ReferencePoint(ReferencePointKind.MEMBER_CONNECTED_END, first.id),
        ForceVector3D(0.7, 0.0, 0.0),
        MomentVector3D(0.0, 0.0, 1.0),
        ActionConvention.MEMBER_ON_JOINT,
    )
    return JointAssembly(
        "benchmark-assembly",
        "Canonical orchestration benchmark",
        ConnectionDesignCategory.SHEAR,
        unit_system,
        (first, second),
        (),
        (),
        (interface,),
        (bolt_group,),
        (load,),
        (action,),
    )


def _resolve_pair(
    *,
    unit_system: EngineeringUnitSystem,
    first: AssemblyMember,
    second: AssemblyMember,
    first_geometry: CrossSectionGeometry2D,
    second_geometry: CrossSectionGeometry2D,
    first_element_id: str,
    second_element_id: str,
    first_length: float,
    second_length: float,
    second_angle_degrees: float,
    bolt_first_x: float,
    bolt_first_y: float,
    bolt_second_x: float,
    bolt_second_y: float,
    first_offset_z: float,
    second_offset_z: float,
    hole_diameter: float,
    include_second_layer: bool = True,
    rigid_rotation: Rotation3D = IDENTITY_ROTATION,
    rigid_translation: Vector3D = _ZERO_TRANSLATION,
) -> tuple[JointAssembly, JointGeometryContext]:
    scale = 1.0 if unit_system is EngineeringUnitSystem.US_CUSTOMARY else 25.4
    angle = radians(second_angle_degrees)
    first_x = rigid_rotation.apply(Vector3D(1.0, 0.0, 0.0))
    first_y = rigid_rotation.apply(Vector3D(0.0, 1.0, 0.0))
    local_z_reference = rigid_rotation.apply(Vector3D(0.0, 0.0, 1.0))
    second_x = rigid_rotation.apply(Vector3D(cos(angle), sin(angle), 0.0))
    second_y = rigid_rotation.apply(Vector3D(-sin(angle), cos(angle), 0.0))
    rotated_bolt = rigid_rotation.apply(
        Vector3D(
            _scale(bolt_first_x, unit_system),
            _scale(bolt_first_y, unit_system),
            0.0,
        )
    )
    bolt = PositionVector3D(
        rotated_bolt.x + rigid_translation.x,
        rotated_bolt.y + rigid_translation.y,
        rotated_bolt.z + rigid_translation.z,
    )
    first_start = PositionVector3D(
        bolt.x
        - first_x.x * _scale(bolt_first_x, unit_system)
        - first_y.x * _scale(bolt_first_y, unit_system),
        bolt.y
        - first_x.y * _scale(bolt_first_x, unit_system)
        - first_y.y * _scale(bolt_first_y, unit_system),
        bolt.z
        - first_x.z * _scale(bolt_first_x, unit_system)
        - first_y.z * _scale(bolt_first_y, unit_system),
    )
    second_start = PositionVector3D(
        bolt.x
        - second_x.x * _scale(bolt_second_x, unit_system)
        - second_y.x * _scale(bolt_second_y, unit_system),
        bolt.y
        - second_x.y * _scale(bolt_second_x, unit_system)
        - second_y.y * _scale(bolt_second_y, unit_system),
        bolt.z
        - second_x.z * _scale(bolt_second_x, unit_system)
        - second_y.z * _scale(bolt_second_y, unit_system),
    )
    placed_first = place_member(
        first,
        first_geometry,
        first_start,
        PositionVector3D(
            first_start.x + first_x.x * _scale(first_length, unit_system),
            first_start.y + first_x.y * _scale(first_length, unit_system),
            first_start.z + first_x.z * _scale(first_length, unit_system),
        ),
        local_z_reference,
        SectionDatumOffset(0.0, _scale(first_offset_z, unit_system)),
    )
    placed_second = place_member(
        second,
        second_geometry,
        second_start,
        PositionVector3D(
            second_start.x + second_x.x * _scale(second_length, unit_system),
            second_start.y + second_x.y * _scale(second_length, unit_system),
            second_start.z + second_x.z * _scale(second_length, unit_system),
        ),
        local_z_reference,
        SectionDatumOffset(0.0, _scale(second_offset_z, unit_system)),
    )
    first_surfaces = create_component_surface_set(placed_first)
    second_surfaces = create_component_surface_set(placed_second)
    first_negative, first_positive = _broad_faces(first_surfaces.patches, first_element_id)
    second_negative, second_positive = _broad_faces(second_surfaces.patches, second_element_id)
    first_ref = ParticipantReference(ParticipantKind.MEMBER, first.id)
    second_ref = ParticipantReference(ParticipantKind.MEMBER, second.id)
    interface = ConnectionInterface(
        "interface-1",
        "Direct member interface",
        first_ref,
        second_ref,
        TransferIntent.SHEAR_ONLY,
    )
    bolt_group = BoltGroup(
        "bolt-group-1",
        "One-bolt group",
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, "bolt-group-1"),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, "bolt-group-1"),
        (interface.id,),
        (BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0)),),
    )
    assembly = _assembly(
        unit_system=unit_system,
        first=first,
        second=second,
        interface=interface,
        bolt_group=bolt_group,
    )
    first_zone = ConnectionZoneSpecification(
        "first-zone",
        "First physical contact zone",
        first_positive.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    second_zone = ConnectionZoneSpecification(
        "second-zone",
        "Second physical contact zone",
        second_negative.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    tolerance = GeometryComparisonTolerance(1.0e-9 * scale, 1.0e-9)
    first_geometry_3d = cast(PlanarRectangularSurface3D, first_positive.geometry)
    bolt_on_interface = PositionVector3D(bolt.x, bolt.y, first_geometry_3d.center.z)
    bolt_local = first_geometry_3d.frame.parent_to_local_point(bolt_on_interface)
    interface_specification = ConnectionInterfaceGeometrySpecification(
        interface,
        InterfaceTargetSideSpecification(first_ref, (first_zone,), first_zone.id),
        InterfaceTargetSideSpecification(second_ref, (second_zone,), second_zone.id),
        InterfaceOriginSpecification(first_zone.id, bolt_local.y, bolt_local.z),
        first_x,
        tolerance,
    )
    resolved_interface = resolve_connection_interface_geometry(
        interface_specification,
        (*first_surfaces.patches, *second_surfaces.patches),
    )
    basis = JointGeometryBasis(
        assembly,
        placed_first.global_frame,
        (placed_first, placed_second),
        (),
        (first_surfaces, second_surfaces),
        (),
        (resolved_interface,),
    )
    bolt_specification = BoltGroupGeometrySpecification(
        bolt_group,
        interface.id,
        0.0,
        0.0,
        first_x,
        tolerance,
        (
            BoltPathDefinition(
                "bolt-1",
                (
                    IntendedPenetratedLayer(
                        "layer-A",
                        first_ref,
                        first_element_id,
                        first_negative.reference,
                        first_positive.reference,
                        (
                            InterfaceZoneReference(
                                interface.id,
                                InterfaceTargetSide.FIRST,
                                first_zone.id,
                            ),
                        ),
                        _scale(hole_diameter, unit_system),
                    ),
                    *(
                        (
                            IntendedPenetratedLayer(
                                "layer-B",
                                second_ref,
                                second_element_id,
                                second_negative.reference,
                                second_positive.reference,
                                (
                                    InterfaceZoneReference(
                                        interface.id,
                                        InterfaceTargetSide.SECOND,
                                        second_zone.id,
                                    ),
                                ),
                                _scale(hole_diameter, unit_system),
                            ),
                        )
                        if include_second_layer
                        else ()
                    ),
                ),
            ),
        ),
    )
    group = resolve_bolt_group_geometry(basis, bolt_specification)
    return assembly, JointGeometryContext(basis, (group,))


def build_plate_case(
    fixture_id: str,
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
) -> CanonicalOrchestrationCase:
    first_topology = _oriented_topology(SectionFamily.PLATE)
    second_frp = fixture_id not in {"P1", "PT1", "B1"}
    second_topology = (
        _oriented_topology(SectionFamily.PLATE)
        if second_frp
        else create_standard_section_topology(SectionFamily.PLATE)
    )
    first = AssemblyMember(
        "member-a",
        "FRP plate A",
        MemberRole.BRACE,
        MemberEnd.START,
        SectionFamily.PLATE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-a"),
            PrincipalAxisFamily.X,
        ),
        first_topology,
    )
    second = AssemblyMember(
        "member-b",
        "Second plate",
        MemberRole.COLUMN,
        MemberEnd.START,
        SectionFamily.PLATE,
        (ComponentMaterialKind.PULTRUDED_FRP if second_frp else ComponentMaterialKind.STEEL),
        (
            FRPComponentOrientation(
                CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-b"),
                PrincipalAxisFamily.X,
            )
            if second_frp
            else None
        ),
        second_topology,
    )
    direction_case = fixture_id == "P2B"
    second_length = 2.4748737341529163 if direction_case else 4.0
    second_width = 3.0 if fixture_id in {"P2A", "P2B"} else 4.0
    second_thickness = 0.5 if fixture_id in {"P2A", "P2B"} else 0.375
    bolt_second_x = 1.0606601717798212 if direction_case else 2.0
    bolt_second_y = 0.4393398282201788 if direction_case else 0.0
    first_geometry = create_plate_geometry(
        first_topology,
        PlateDimensions(
            _scale(4.0, unit_system),
            _scale(0.375, unit_system),
        ),
    )
    second_geometry = create_plate_geometry(
        second_topology,
        PlateDimensions(
            _scale(second_width, unit_system),
            _scale(second_thickness, unit_system),
        ),
    )
    assembly, context = _resolve_pair(
        unit_system=unit_system,
        first=first,
        second=second,
        first_geometry=first_geometry,
        second_geometry=second_geometry,
        first_element_id="PLATE",
        second_element_id="PLATE",
        first_length=4.0,
        second_length=second_length,
        second_angle_degrees=45.0 if direction_case else 0.0,
        bolt_first_x=2.0,
        bolt_first_y=0.0,
        bolt_second_x=bolt_second_x,
        bolt_second_y=bolt_second_y,
        first_offset_z=0.0,
        second_offset_z=0.1875 + second_thickness / 2.0,
        hole_diameter=0.563,
        include_second_layer=second_frp,
    )
    layer_ids = ("layer-A", "layer-B") if second_frp else ("layer-A",)
    demand = {
        "P1": "3.000",
        "PT1": "3.000",
        "P2A": "2.000",
        "P2B": "2.000",
        "B1": "5.000",
    }[fixture_id]
    request = _request(
        assembly=assembly,
        context=context,
        layer_ids=layer_ids,
        demand_kip=demand,
        axial_kip="0.500" if fixture_id == "PT1" else "2.000" if fixture_id == "B1" else "0",
        lap=(
            LapConfiguration.SINGLE_LAP
            if fixture_id in {"P2A", "P2B"}
            else LapConfiguration.DOUBLE_LAP
        ),
        synthetic=fixture_id == "B1",
        explicit_demand=explicit_demand,
        element_forms=tuple(PultrudedElementForm.SHAPE_ELEMENT for _ in layer_ids),
    )
    return CanonicalOrchestrationCase(request, context)


def build_j1_case(
    *,
    compression: bool = False,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
) -> CanonicalOrchestrationCase:
    angle_topology = _oriented_topology(SectionFamily.ANGLE)
    w_topology = _oriented_topology(SectionFamily.WIDE_FLANGE)
    angle = AssemblyMember(
        "member-a",
        "Pultruded FRP angle brace",
        MemberRole.BRACE,
        MemberEnd.START,
        SectionFamily.ANGLE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-a"),
            PrincipalAxisFamily.X,
        ),
        angle_topology,
    )
    column = AssemblyMember(
        "member-b",
        "Pultruded FRP W column",
        MemberRole.COLUMN,
        MemberEnd.START,
        SectionFamily.WIDE_FLANGE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-b"),
            PrincipalAxisFamily.X,
        ),
        w_topology,
    )
    angle_geometry = create_angle_geometry(
        angle_topology,
        AngleDimensions(
            _scale(3.375, unit_system),
            _scale(3.0, unit_system),
            _scale(0.375, unit_system),
        ),
    )
    w_geometry = create_wide_flange_geometry(
        w_topology,
        ISectionDimensions(
            _scale(4.0, unit_system),
            _scale(6.375, unit_system),
            _scale(0.375, unit_system),
            _scale(0.5, unit_system),
        ),
    )
    side_gap = 1.0606601717798212
    assembly, context = _resolve_pair(
        unit_system=unit_system,
        first=angle,
        second=column,
        first_geometry=angle_geometry,
        second_geometry=w_geometry,
        first_element_id="LEG_1",
        second_element_id="TOP_FLANGE",
        first_length=4.0,
        second_length=side_gap + 1.5,
        second_angle_degrees=45.0,
        bolt_first_x=2.0,
        bolt_first_y=0.1875,
        bolt_second_x=side_gap,
        bolt_second_y=-1.6875 + (1.5 - side_gap),
        first_offset_z=1.125,
        second_offset_z=-1.5,
        hole_diameter=0.563,
    )
    request = _request(
        assembly=assembly,
        context=context,
        layer_ids=("layer-A", "layer-B"),
        demand_kip="0.700",
        loading_sense=(LayerLoadingSense.COMPRESSION if compression else LayerLoadingSense.TENSION),
        lap=LapConfiguration.SINGLE_LAP,
        qualification=True,
        explicit_demand=explicit_demand,
    )
    return CanonicalOrchestrationCase(request, context)


def build_j1_visual_case(
    *,
    compression: bool = False,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
) -> CanonicalOrchestrationCase:
    """Build the Stage 2.3R J1 view by one proper rotation of the historical case."""

    angle_topology = _oriented_topology(SectionFamily.ANGLE)
    w_topology = _oriented_topology(SectionFamily.WIDE_FLANGE)
    angle = AssemblyMember(
        "member-a",
        "Pultruded FRP angle brace",
        MemberRole.BRACE,
        MemberEnd.START,
        SectionFamily.ANGLE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-a"),
            PrincipalAxisFamily.X,
        ),
        angle_topology,
    )
    column = AssemblyMember(
        "member-b",
        "Pultruded FRP W column",
        MemberRole.COLUMN,
        MemberEnd.START,
        SectionFamily.WIDE_FLANGE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-b"),
            PrincipalAxisFamily.X,
        ),
        w_topology,
    )
    angle_geometry = create_angle_geometry(
        angle_topology,
        AngleDimensions(
            _scale(3.375, unit_system),
            _scale(3.0, unit_system),
            _scale(0.375, unit_system),
        ),
    )
    w_geometry = create_wide_flange_geometry(
        w_topology,
        ISectionDimensions(
            _scale(4.0, unit_system),
            _scale(6.375, unit_system),
            _scale(0.375, unit_system),
            _scale(0.5, unit_system),
        ),
    )
    side_gap = 1.0606601717798212
    assembly, context = _resolve_pair(
        unit_system=unit_system,
        first=angle,
        second=column,
        first_geometry=angle_geometry,
        second_geometry=w_geometry,
        first_element_id="LEG_1",
        second_element_id="TOP_FLANGE",
        first_length=4.0,
        second_length=side_gap + 1.5,
        second_angle_degrees=45.0,
        bolt_first_x=2.0,
        bolt_first_y=0.1875,
        bolt_second_x=side_gap,
        bolt_second_y=-1.6875 + (1.5 - side_gap),
        first_offset_z=1.125,
        second_offset_z=-1.5,
        hole_diameter=0.563,
        rigid_rotation=_J1_VERTICAL_ROTATION,
        rigid_translation=Vector3D(
            0.0,
            _scale(0.125, unit_system),
            _scale(0.125, unit_system),
        ),
    )
    request = _request(
        assembly=assembly,
        context=context,
        layer_ids=("layer-A", "layer-B"),
        demand_kip="0.700",
        loading_sense=(LayerLoadingSense.COMPRESSION if compression else LayerLoadingSense.TENSION),
        lap=LapConfiguration.SINGLE_LAP,
        qualification=True,
        explicit_demand=explicit_demand,
    )
    return CanonicalOrchestrationCase(request, context)


__all__ = (
    "CanonicalOrchestrationCase",
    "build_j1_case",
    "build_j1_visual_case",
    "build_plate_case",
)
