"""Transport adapter for the canonical Stage 2.2A single-bolt service."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import cast

from pydantic import JsonValue

from frp_master_connection.api.schemas import (
    API_TRANSPORT_SCHEMA_VERSION,
    AngleSectionDTO,
    DecimalVector3DTO,
    DirectionVector3DTO,
    FastenerSnapshotDTO,
    FrameDTO,
    GeometryDTO,
    ISectionDTO,
    MaterialSnapshotDTO,
    MemberDTO,
    OrchestrationIssueDTO,
    PlateSectionDTO,
    QuantityDTO,
    ReferencePointDTO,
    SectionDTO,
    SingleBoltEvaluationRequestDTO,
    SingleBoltEvaluationResponseDTO,
    SingleBoltPreviewRequestDTO,
    SingleBoltPreviewResponseDTO,
    SourceReferenceDTO,
)
from frp_master_connection.application import (
    BraceToColumnOrientationContext,
    ConnectionViewExtents,
    ExplicitBoltDemandAssignment,
    PenetratedLayerMaterialAssignment,
    SingleBoltOrchestrationRequest,
    SingleBoltOrchestrationResponse,
    SingleBoltPreviewResult,
    SingleBoltVisualizationSnapshot,
    TemplateInterference,
    TemplateInterferenceClassification,
)
from frp_master_connection.calculation import (
    Dimension,
    EndUseFactors,
    FastenerSnapshot,
    FinalCalculationResult,
    FRPPropertyEntry,
    MaterialPropertySnapshot,
    PhysicalQuantity,
    ResolvedSingleBoltDemand,
    ThreadStatusAssignment,
    Unit,
    WasherGeometry,
    canonical_decimal_string,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    decimal_from_finite_real,
    select_time_effect_factor,
)
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.domain import (
    AssemblyMember,
    BoltGroup,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionInterface,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ForceVector3D,
    FRPComponentOrientation,
    JointAssembly,
    LoadCombination,
    ManualMemberEndAction,
    MomentVector3D,
    ParticipantKind,
    ParticipantReference,
    PositionVector3D,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SectionTopology,
    create_region_specific_planar_orientations,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    AngleDimensions,
    BoltGroupGeometrySpecification,
    BoltPathDefinition,
    CartesianFrame3D,
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    CrossSectionGeometry2D,
    GeometryComparisonTolerance,
    IntendedPenetratedLayer,
    InterfaceOriginSpecification,
    InterfaceTargetSideSpecification,
    InterfaceZoneReference,
    ISectionDimensions,
    JointGeometryBasis,
    JointGeometryContext,
    LocalRectangularPrism3D,
    PlacedComponentGeometry3D,
    PlacedPhysicalElement3D,
    PlanarRectangularSurface3D,
    PlateDimensions,
    SectionDatumOffset,
    SurfacePatch3D,
    SurfacePatchRole,
    Vector3D,
    build_cartesian_frame,
    create_angle_geometry,
    create_component_surface_set,
    create_i_section_geometry,
    create_plate_geometry,
    create_wide_flange_geometry,
    place_member,
    resolve_bolt_group_geometry,
    resolve_connection_interface_geometry,
)


def _deterministic_sine_cosine_degrees(angle_degrees: Decimal) -> tuple[float, float]:
    """Retain the accepted private seam while sharing the R5 authority."""

    return deterministic_sine_cosine_degrees(angle_degrees)


def _quantity(value: QuantityDTO, expected: Dimension | None = None) -> PhysicalQuantity:
    result = PhysicalQuantity.of(value.value, value.unit)
    if expected is not None and result.dimension is not expected:
        raise ValueError(f"Expected {expected.value} quantity, received {result.dimension.value}.")
    return result


def _geometry_scalar(value: QuantityDTO, unit: Unit) -> float:
    """Apply the one approved Decimal-to-finite-geometry scalar bridge."""

    return float(_quantity(value, Dimension.LENGTH).to(unit).magnitude)


def _decimal_scalar(value: str) -> Decimal:
    return Decimal(value)


def _direction(value: DirectionVector3DTO) -> Vector3D:
    return Vector3D(
        float(_decimal_scalar(value.x)),
        float(_decimal_scalar(value.y)),
        float(_decimal_scalar(value.z)),
    )


def _point(value: DecimalVector3DTO, length_unit: Unit) -> PositionVector3D:
    if PhysicalQuantity.of(0, value.unit).dimension is not Dimension.LENGTH:
        raise ValueError("A geometry point requires a length unit.")
    source = Unit(value.unit)
    return PositionVector3D(
        float(PhysicalQuantity.of(value.x, source).to(length_unit).magnitude),
        float(PhysicalQuantity.of(value.y, source).to(length_unit).magnitude),
        float(PhysicalQuantity.of(value.z, source).to(length_unit).magnitude),
    )


def _vector_components(value: DecimalVector3DTO, target_unit: Unit) -> tuple[float, float, float]:
    source = Unit(value.unit)
    source_dimension = PhysicalQuantity.of(0, source).dimension
    target_dimension = PhysicalQuantity.of(0, target_unit).dimension
    if source_dimension is not target_dimension:
        raise ValueError(f"Vector unit must have {target_dimension.value} dimension.")
    return (
        float(PhysicalQuantity.of(value.x, source).to(target_unit).magnitude),
        float(PhysicalQuantity.of(value.y, source).to(target_unit).magnitude),
        float(PhysicalQuantity.of(value.z, source).to(target_unit).magnitude),
    )


def _frame(frame: FrameDTO, length_unit: Unit) -> CartesianFrame3D:
    return build_cartesian_frame(
        _point(frame.origin, length_unit),
        _direction(frame.x_direction),
        _direction(frame.local_z_reference),
    )


def _section_family(kind: str) -> SectionFamily:
    return SectionFamily(kind)


def _member(member: MemberDTO) -> AssemblyMember:
    family = _section_family(member.section.kind)
    orientation = member.material_orientation
    topology_orientations = None
    material_orientation = None
    if member.material_kind is ComponentMaterialKind.PULTRUDED_FRP:
        if orientation is None:
            raise ValueError("Pultruded-FRP members require material_orientation.")
        topology_orientations = create_region_specific_planar_orientations(
            family,
            orientation.crosswise_axis,
            orientation.through_thickness_axis,
        )
        material_orientation = FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member.id),
            orientation.lengthwise_axis,
        )
    elif orientation is not None:
        raise ValueError("Non-FRP members cannot declare FRP material orientation.")
    topology = create_standard_section_topology(family, orientations=topology_orientations)
    return AssemblyMember(
        member.id,
        member.label,
        member.role,
        member.connected_end,
        family,
        member.material_kind,
        material_orientation,
        topology,
    )


def _cross_section(
    member: AssemblyMember,
    section: SectionDTO,
    length_unit: Unit,
) -> CrossSectionGeometry2D:
    topology = cast(SectionTopology, member.section_topology)
    if isinstance(section, PlateSectionDTO):
        return create_plate_geometry(
            topology,
            PlateDimensions(
                _geometry_scalar(section.width, length_unit),
                _geometry_scalar(section.thickness, length_unit),
            ),
        )
    if isinstance(section, AngleSectionDTO):
        return create_angle_geometry(
            topology,
            AngleDimensions(
                _geometry_scalar(section.leg_y, length_unit),
                _geometry_scalar(section.leg_z, length_unit),
                _geometry_scalar(section.thickness, length_unit),
            ),
        )
    i_section = section
    dimensions = ISectionDimensions(
        _geometry_scalar(i_section.overall_depth, length_unit),
        _geometry_scalar(i_section.flange_width, length_unit),
        _geometry_scalar(i_section.web_thickness, length_unit),
        _geometry_scalar(i_section.flange_thickness, length_unit),
    )
    if i_section.kind == "WIDE_FLANGE":
        return create_wide_flange_geometry(topology, dimensions)
    return create_i_section_geometry(topology, dimensions)


def _surface(
    surfaces: tuple[SurfacePatch3D, ...],
    participant_id: str,
    physical_element_id: str,
    patch_id: str,
    role: object,
) -> SurfacePatch3D:
    matches = tuple(
        patch
        for patch in surfaces
        if patch.reference.participant.entity_id == participant_id
        and patch.source.physical_element_id == physical_element_id
        and patch.id == patch_id
        and patch.role is role
        and isinstance(patch.geometry, PlanarRectangularSurface3D)
    )
    if len(matches) != 1:
        raise ValueError(
            "A declared planar surface reference must resolve exactly once for "
            f"{participant_id}:{physical_element_id}."
        )
    return matches[0]


def _rectangular_prism(element: PlacedPhysicalElement3D) -> LocalRectangularPrism3D:
    if len(element.extrusions) != 1 or not isinstance(
        element.extrusions[0], LocalRectangularPrism3D
    ):
        raise ValueError("The current template interference check requires rectangular prisms.")
    return element.extrusions[0]


def _prisms_have_positive_volume_overlap(
    first: PlacedPhysicalElement3D,
    second: PlacedPhysicalElement3D,
    tolerance: GeometryComparisonTolerance,
) -> bool:
    """Classify overlap for two current-template rectangular prisms only."""

    def box(
        element: PlacedPhysicalElement3D,
    ) -> tuple[PositionVector3D, tuple[Vector3D, ...], tuple[float, ...]]:
        prism = _rectangular_prism(element)
        local_center = PositionVector3D(
            (prism.extent.x_start + prism.extent.x_end) / 2.0,
            (prism.rectangle.min_y + prism.rectangle.max_y) / 2.0,
            (prism.rectangle.min_z + prism.rectangle.max_z) / 2.0,
        )
        return (
            element.global_frame.local_to_parent_point(local_center),
            (
                element.global_frame.x_axis,
                element.global_frame.y_axis,
                element.global_frame.z_axis,
            ),
            (
                prism.extent.length / 2.0,
                (prism.rectangle.max_y - prism.rectangle.min_y) / 2.0,
                (prism.rectangle.max_z - prism.rectangle.min_z) / 2.0,
            ),
        )

    first_center, first_axes, first_half = box(first)
    second_center, second_axes, second_half = box(second)
    center_delta = Vector3D(
        second_center.x - first_center.x,
        second_center.y - first_center.y,
        second_center.z - first_center.z,
    )
    candidates = [*first_axes, *second_axes]
    candidates.extend(
        first_axis.cross(second_axis) for first_axis in first_axes for second_axis in second_axes
    )
    for candidate in candidates:
        if candidate.norm <= tolerance.angular_tolerance:
            continue
        axis = candidate.normalized()
        first_radius = sum(
            half * abs(source_axis.dot(axis))
            for half, source_axis in zip(first_half, first_axes, strict=True)
        )
        second_radius = sum(
            half * abs(source_axis.dot(axis))
            for half, source_axis in zip(second_half, second_axes, strict=True)
        )
        overlap = first_radius + second_radius - abs(center_delta.dot(axis))
        if overlap <= tolerance.distance_tolerance:
            return False
    return True


def _template_orientation_context(
    dto: SingleBoltEvaluationRequestDTO,
    geometry: GeometryDTO,
    placed_members: tuple[PlacedComponentGeometry3D, ...],
    tolerance: GeometryComparisonTolerance,
) -> BraceToColumnOrientationContext | None:
    template = dto.geometry_template
    if template is None:
        return None
    angle, column = placed_members
    interference = tuple(
        TemplateInterference(
            TemplateInterferenceClassification.ANGLE_W_MEMBER_INTERFERENCE,
            angle.component.id,
            angle_element.source_element.id,
            column.component.id,
            column_element.source_element.id,
            dto.interface_id,
            (
                "Invalid geometry - Angle Brace "
                f"{angle_element.source_element.id} intersects W Column "
                f"{column_element.source_element.id}."
            ),
        )
        for angle_element in angle.physical_elements
        for column_element in column.physical_elements
        if _prisms_have_positive_volume_overlap(angle_element, column_element, tolerance)
    )
    first = geometry.interface.first_side
    second = geometry.interface.second_side
    return BraceToColumnOrientationContext(
        template.column_flange_connection_side,
        template.angle_connected_leg,
        template.outstanding_leg_side,
        second.participant_id,
        second.physical_element_id,
        second.patch_id,
        second.face_role.value,
        first.participant_id,
        first.patch_id,
        first.face_role.value,
        geometry.interface.id,
        Decimal(template.brace_to_column_directed_angle_deg),
        Decimal(0),
        interference,
    )


def _reference_point(point: ReferencePointDTO, length_unit: Unit) -> ReferencePoint:
    position = _point(point.position, length_unit) if point.position is not None else None
    return ReferencePoint(point.kind, point.owner_id, position)


def _material_snapshot(dto: MaterialSnapshotDTO) -> MaterialPropertySnapshot:
    result = MaterialPropertySnapshot(
        dto.id,
        dto.display_name,
        dto.locked,
        dto.basis,
        dto.qualification_statuses,
        tuple(
            FRPPropertyEntry(
                entry.kind,
                _quantity(entry.value),
                entry.behavior,
                entry.source_classification,
                entry.qualification_status,
                entry.source_document,
                entry.source_revision,
                entry.applicability_metadata,
                entry.engineer_notes,
                entry.use_in_chapter_8_equations,
            )
            for entry in dto.properties
        ),
        dto.explicitly_missing,
    )
    if result.locked and result != create_locked_ice_material_snapshot():
        raise ValueError("A locked material snapshot must exactly match the approved ICE snapshot.")
    return result


def _fastener_snapshot(dto: FastenerSnapshotDTO) -> FastenerSnapshot:
    result = FastenerSnapshot(
        dto.id,
        dto.display_name,
        dto.locked,
        dto.bolt_specification,
        dto.alloy_group,
        dto.alloys,
        dto.condition,
        dto.nut_specification,
        dto.washer_material_basis,
        dto.installation_condition,
        _quantity(dto.diameter_min, Dimension.LENGTH),
        _quantity(dto.diameter_max, Dimension.LENGTH),
        None if dto.fnt is None else _quantity(dto.fnt, Dimension.STRESS),
        dto.fnt_source_classification,
        dto.fnt_qualification_status,
        tuple(
            ThreadStatusAssignment(item.location_id, item.status)
            for item in dto.shear_plane_thread_statuses
        ),
        tuple(
            ThreadStatusAssignment(item.location_id, item.status)
            for item in dto.bearing_layer_thread_statuses
        ),
        dto.number_of_shear_planes,
        (
            None
            if dto.washer_geometry is None
            else WasherGeometry(
                _quantity(dto.washer_geometry.outside_diameter, Dimension.LENGTH),
                _quantity(dto.washer_geometry.thickness, Dimension.LENGTH),
                dto.washer_geometry.under_head,
                dto.washer_geometry.under_nut,
            )
        ),
        dto.source_notes,
    )
    if result.locked:
        approved = create_locked_f593_fastener_snapshot()
        source_fields = (
            "id",
            "display_name",
            "bolt_specification",
            "alloy_group",
            "alloys",
            "condition",
            "nut_specification",
            "washer_material_basis",
            "installation_condition",
            "diameter_min",
            "diameter_max",
            "fnt",
            "fnt_source_classification",
            "fnt_qualification_status",
            "source_notes",
        )
        if any(getattr(result, name) != getattr(approved, name) for name in source_fields):
            raise ValueError("A locked fastener snapshot must retain the approved F593 source.")
    return result


def _brace_to_column_template_geometry(
    dto: SingleBoltEvaluationRequestDTO,
    length_unit: Unit,
) -> GeometryDTO:
    """Resolve the one approved brace-to-W-column template on the server."""

    template = dto.geometry_template
    if template is None:
        raise ValueError("Brace-to-column template geometry is required.")
    expected_member_ids = ("member-a", "member-b")
    member_ids = tuple(member.id for member in dto.joint_assembly.members)
    member_kinds = tuple(member.section.kind for member in dto.joint_assembly.members)
    if member_ids != expected_member_ids or member_kinds != ("ANGLE", "WIDE_FLANGE"):
        raise ValueError(
            "The brace-to-column-flange template requires member-a ANGLE and "
            "member-b WIDE_FLANGE in that order."
        )
    if (
        dto.interface_id != "interface-1"
        or dto.bolt_group_id != "bolt-group-1"
        or dto.bolt_location_id != "bolt-1"
    ):
        raise ValueError(
            "The current geometry template requires the verified interface and bolt IDs."
        )

    def length(value: QuantityDTO, name: str) -> float:
        result = _geometry_scalar(value, length_unit)
        if result <= 0.0:
            raise ValueError(f"{name} must be greater than zero.")
        return result

    def us_length(value: str) -> float:
        return float(PhysicalQuantity.of(value, Unit.IN).to(length_unit).magnitude)

    def decimal(value: float) -> str:
        return canonical_decimal_string(decimal_from_finite_real(value))

    def point_value(x: float, y: float, z: float) -> dict[str, str]:
        return {"x": decimal(x), "y": decimal(y), "z": decimal(z), "unit": length_unit.value}

    def direction_value(x: float, y: float, z: float) -> dict[str, str]:
        return {"x": decimal(x), "y": decimal(y), "z": decimal(z)}

    def quantity_value(value: float) -> dict[str, str]:
        return {"value": decimal(value), "unit": length_unit.value}

    angle_degrees = Decimal(template.brace_to_column_directed_angle_deg)
    sine, cosine = _deterministic_sine_cosine_degrees(angle_degrees)
    brace_x = Vector3D(
        0.0,
        -sine,
        cosine if template.column_flange_connection_side.value == "EXTERIOR" else -cosine,
    ).normalized()
    interface_normal = Vector3D(
        1.0 if template.column_flange_connection_side.value == "EXTERIOR" else -1.0,
        0.0,
        0.0,
    ).normalized()
    positive_outstanding = template.outstanding_leg_side.value == "POSITIVE_INTERFACE_Z"
    contact_is_exterior = positive_outstanding
    if template.angle_connected_leg.value == "LEG_1":
        brace_z = (-interface_normal if contact_is_exterior else interface_normal).normalized()
        brace_y = brace_z.cross(brace_x).normalized()
    else:
        brace_y = (-interface_normal if contact_is_exterior else interface_normal).normalized()
        brace_z = brace_x.cross(brace_y).normalized()

    angle_section = cast(AngleSectionDTO, dto.joint_assembly.members[0].section)
    column_section = cast(ISectionDTO, dto.joint_assembly.members[1].section)
    angle_leg_y = _geometry_scalar(angle_section.leg_y, length_unit)
    angle_leg_z = _geometry_scalar(angle_section.leg_z, length_unit)
    angle_thickness = _geometry_scalar(angle_section.thickness, length_unit)
    column_depth = _geometry_scalar(column_section.overall_depth, length_unit)
    column_flange_thickness = _geometry_scalar(column_section.flange_thickness, length_unit)
    angle_heel_y = -angle_leg_y / 2.0 + angle_thickness
    angle_heel_z = -angle_leg_z / 2.0 + angle_thickness
    angle_section_offset_z = -angle_heel_z
    column_section_offset_z = -(column_depth / 2.0 - column_flange_thickness)

    bolt = (
        (
            -column_flange_thickness
            if template.column_flange_connection_side.value == "EXTERIOR"
            else 0.0
        ),
        us_length("-1.1566310409006175"),
        us_length("1.6717960838455723"),
    )
    brace_bolt_x = length(
        template.bolt_to_brace_end_distance,
        "bolt_to_brace_end_distance",
    )
    if template.angle_connected_leg.value == "LEG_1":
        brace_bolt_y = angle_thickness / 2.0
        brace_bolt_z = (
            -angle_leg_z / 2.0 if contact_is_exterior else angle_heel_z
        ) + angle_section_offset_z
    else:
        brace_bolt_y = -angle_leg_y / 2.0 if contact_is_exterior else angle_heel_y
        brace_bolt_z = angle_thickness / 2.0 + angle_section_offset_z
    # The targetable brace patch is engineering geometry, not a view crop.  Keeping
    # the bolt centered in this finite physical patch lets the existing mapper
    # re-derive the entered connected-end distance from canonical boundaries.
    brace_length = 2.0 * brace_bolt_x
    # These approved J1 physical extents retain the existing column connection
    # geometry.  User-controlled column view extents are mapped separately below
    # and never enter this engineering object graph.
    below = us_length("8.7426406871192848")
    above = us_length("1.5")
    hole_diameter = length(template.hole_diameter, "hole_diameter")
    column_bolt_y = us_length(
        "-1.2481601717798212"
        if template.column_flange_connection_side.value == "EXTERIOR"
        else "-2.75"
    )

    brace_start = tuple(
        bolt[index]
        - (brace_x.x, brace_x.y, brace_x.z)[index] * brace_bolt_x
        - (brace_y.x, brace_y.y, brace_y.z)[index] * brace_bolt_y
        - (brace_z.x, brace_z.y, brace_z.z)[index] * brace_bolt_z
        for index in range(3)
    )
    brace_end = tuple(
        brace_start[index] + (brace_x.x, brace_x.y, brace_x.z)[index] * brace_length
        for index in range(3)
    )
    column_start = (0.0, bolt[1] - column_bolt_y, bolt[2] - below)
    column_end = (0.0, bolt[1] - column_bolt_y, bolt[2] + above)
    tolerance = us_length("0.000000001")

    connected_leg = template.angle_connected_leg.value
    contact_suffix = "EXTERIOR_TT_BROAD" if contact_is_exterior else "OPEN_AREA_TT_BROAD"
    opposite_suffix = "OPEN_AREA_TT_BROAD" if contact_is_exterior else "EXTERIOR_TT_BROAD"
    contact_role = (
        SurfacePatchRole.NEGATIVE_THICKNESS_FACE
        if contact_is_exterior
        else SurfacePatchRole.POSITIVE_THICKNESS_FACE
    )
    opposite_role = (
        SurfacePatchRole.POSITIVE_THICKNESS_FACE
        if contact_is_exterior
        else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
    )
    exterior = template.column_flange_connection_side.value == "EXTERIOR"
    flange_contact_suffix = "OUTER_NEGATIVE_CW_STRIP" if exterior else "INNER_NEGATIVE_CW_STRIP"
    flange_opposite_suffix = "INNER_NEGATIVE_CW_STRIP" if exterior else "OUTER_NEGATIVE_CW_STRIP"
    flange_contact_role = (
        SurfacePatchRole.POSITIVE_THICKNESS_FACE
        if exterior
        else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
    )
    flange_opposite_role = (
        SurfacePatchRole.NEGATIVE_THICKNESS_FACE
        if exterior
        else SurfacePatchRole.POSITIVE_THICKNESS_FACE
    )

    result = {
        "joint_frame": {
            "origin": point_value(*brace_start),
            "x_direction": direction_value(brace_x.x, brace_x.y, brace_x.z),
            "local_z_reference": direction_value(brace_z.x, brace_z.y, brace_z.z),
        },
        "member_placements": [
            {
                "member_id": "member-a",
                "start": point_value(*brace_start),
                "end": point_value(*brace_end),
                "local_z_reference": direction_value(brace_z.x, brace_z.y, brace_z.z),
                "section_offset_y": quantity_value(0.0),
                "section_offset_z": quantity_value(angle_section_offset_z),
            },
            {
                "member_id": "member-b",
                "start": point_value(*column_start),
                "end": point_value(*column_end),
                "local_z_reference": direction_value(-1.0, 0.0, 0.0),
                "section_offset_y": quantity_value(0.0),
                "section_offset_z": quantity_value(column_section_offset_z),
            },
        ],
        "interface": {
            "id": "interface-1",
            "label": "Direct member interface",
            "participant_a_id": "member-a",
            "participant_b_id": "member-b",
            "transfer_intent": "SHEAR_ONLY",
            "first_side": {
                "participant_id": "member-a",
                "physical_element_id": connected_leg,
                "patch_id": f"{connected_leg}:{contact_suffix}",
                "face_role": contact_role.value,
                "zone_id": "first-zone",
                "zone_label": "First physical contact zone",
            },
            "second_side": {
                "participant_id": "member-b",
                "physical_element_id": "TOP_FLANGE",
                "patch_id": f"TOP_FLANGE:{flange_contact_suffix}",
                "face_role": flange_contact_role.value,
                "zone_id": "second-zone",
                "zone_label": "Second physical contact zone",
            },
            "origin_local_y": quantity_value(0.0),
            "origin_local_z": quantity_value(0.0),
            "in_plane_reference": direction_value(brace_x.x, brace_x.y, brace_x.z),
            "distance_tolerance": quantity_value(tolerance),
            "angular_tolerance": "0.000000001",
        },
        "bolt_group": {
            "id": "bolt-group-1",
            "label": "One-bolt group",
            "primary_interface_id": "interface-1",
            "origin_y": quantity_value(0.0),
            "origin_z": quantity_value(0.0),
            "in_plane_reference": direction_value(brace_x.x, brace_x.y, brace_x.z),
            "locations": [
                {
                    "id": "bolt-1",
                    "local_position": point_value(0.0, 0.0, 0.0),
                }
            ],
            "paths": [
                {
                    "bolt_location_id": "bolt-1",
                    "layers": [
                        {
                            "id": "layer-A",
                            "participant_id": "member-a",
                            "physical_element_id": connected_leg,
                            "entry_patch_id": f"{connected_leg}:{opposite_suffix}",
                            "exit_patch_id": f"{connected_leg}:{contact_suffix}",
                            "entry_face_role": opposite_role.value,
                            "exit_face_role": contact_role.value,
                            "interface_side": "FIRST",
                            "zone_id": "first-zone",
                            "hole_diameter": quantity_value(hole_diameter),
                        },
                        {
                            "id": "layer-B",
                            "participant_id": "member-b",
                            "physical_element_id": "TOP_FLANGE",
                            "entry_patch_id": f"TOP_FLANGE:{flange_contact_suffix}",
                            "exit_patch_id": f"TOP_FLANGE:{flange_opposite_suffix}",
                            "entry_face_role": flange_contact_role.value,
                            "exit_face_role": flange_opposite_role.value,
                            "interface_side": "SECOND",
                            "zone_id": "second-zone",
                            "hole_diameter": quantity_value(hole_diameter),
                        },
                    ],
                }
            ],
        },
    }
    return GeometryDTO.model_validate(result)


def map_single_bolt_request(dto: SingleBoltEvaluationRequestDTO) -> SingleBoltOrchestrationRequest:
    """Rebuild the canonical object graph from one strict stateless DTO."""

    unit_system = dto.joint_assembly.unit_system
    length_unit = Unit.IN if unit_system.value == "US_CUSTOMARY" else Unit.MM
    force_unit = Unit.KIP if unit_system.value == "US_CUSTOMARY" else Unit.KN
    moment_unit = Unit.KIP_IN if unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    geometry = (
        dto.geometry
        if dto.geometry is not None
        else _brace_to_column_template_geometry(dto, length_unit)
    )
    members = tuple(_member(item) for item in dto.joint_assembly.members)
    members_by_id = {item.id: item for item in members}
    if len(members_by_id) != len(members):
        raise ValueError("Member identities must be unique.")

    interface_dto = geometry.interface
    first_reference = ParticipantReference(ParticipantKind.MEMBER, interface_dto.participant_a_id)
    second_reference = ParticipantReference(ParticipantKind.MEMBER, interface_dto.participant_b_id)
    interface = ConnectionInterface(
        interface_dto.id,
        interface_dto.label,
        first_reference,
        second_reference,
        interface_dto.transfer_intent,
    )
    group_dto = geometry.bolt_group
    locations = tuple(
        BoltLocation(item.id, _point(item.local_position, length_unit))
        for item in group_dto.locations
    )
    group = BoltGroup(
        group_dto.id,
        group_dto.label,
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, group_dto.id),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, group_dto.id),
        (group_dto.primary_interface_id,),
        locations,
    )
    loads = tuple(
        LoadCombination(item.id, item.label, item.input_basis)
        for item in dto.joint_assembly.load_combinations
    )
    actions = []
    for item in dto.joint_assembly.member_end_actions:
        force = _vector_components(item.force, force_unit)
        moment = _vector_components(item.moment, moment_unit)
        actions.append(
            ManualMemberEndAction(
                item.id,
                item.member_id,
                item.member_end,
                item.load_combination_id,
                CoordinateFrameReference(
                    item.coordinate_frame_kind,
                    item.coordinate_frame_owner_id,
                ),
                _reference_point(item.reference_point, length_unit),
                ForceVector3D(*force),
                MomentVector3D(*moment),
                item.convention,
            )
        )
    assembly = JointAssembly(
        dto.joint_assembly.id,
        dto.joint_assembly.label,
        dto.joint_assembly.design_category,
        unit_system,
        members,
        (),
        (),
        (interface,),
        (group,),
        loads,
        tuple(actions),
    )
    assembly.require_valid()

    placement_by_id = {item.member_id: item for item in geometry.member_placements}
    if set(placement_by_id) != set(members_by_id):
        raise ValueError("Member placements must exactly match assembly members.")
    placed_members = tuple(
        place_member(
            member,
            _cross_section(member, dto_member.section, length_unit),
            _point(placement_by_id[member.id].start, length_unit),
            _point(placement_by_id[member.id].end, length_unit),
            _direction(placement_by_id[member.id].local_z_reference),
            SectionDatumOffset(
                _geometry_scalar(placement_by_id[member.id].section_offset_y, length_unit),
                _geometry_scalar(placement_by_id[member.id].section_offset_z, length_unit),
            ),
        )
        for member, dto_member in zip(members, dto.joint_assembly.members, strict=True)
    )
    surface_sets = tuple(create_component_surface_set(item) for item in placed_members)
    surfaces = tuple(patch for surface_set in surface_sets for patch in surface_set.patches)
    first_dto = interface_dto.first_side
    second_dto = interface_dto.second_side
    first_patch = _surface(
        surfaces,
        first_dto.participant_id,
        first_dto.physical_element_id,
        first_dto.patch_id,
        first_dto.face_role,
    )
    second_patch = _surface(
        surfaces,
        second_dto.participant_id,
        second_dto.physical_element_id,
        second_dto.patch_id,
        second_dto.face_role,
    )
    first_zone = ConnectionZoneSpecification(
        first_dto.zone_id,
        first_dto.zone_label,
        first_patch.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    second_zone = ConnectionZoneSpecification(
        second_dto.zone_id,
        second_dto.zone_label,
        second_patch.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    tolerance = GeometryComparisonTolerance(
        _geometry_scalar(interface_dto.distance_tolerance, length_unit),
        float(_decimal_scalar(interface_dto.angular_tolerance)),
    )
    resolved_interface = resolve_connection_interface_geometry(
        ConnectionInterfaceGeometrySpecification(
            interface,
            InterfaceTargetSideSpecification(first_reference, (first_zone,), first_zone.id),
            InterfaceTargetSideSpecification(second_reference, (second_zone,), second_zone.id),
            InterfaceOriginSpecification(
                first_zone.id,
                _geometry_scalar(interface_dto.origin_local_y, length_unit),
                _geometry_scalar(interface_dto.origin_local_z, length_unit),
            ),
            _direction(interface_dto.in_plane_reference),
            tolerance,
        ),
        surfaces,
    )
    basis = JointGeometryBasis(
        assembly,
        _frame(geometry.joint_frame, length_unit),
        placed_members,
        (),
        surface_sets,
        (),
        (resolved_interface,),
    )
    paths = []
    for path in group_dto.paths:
        layers = []
        for layer in path.layers:
            participant = ParticipantReference(ParticipantKind.MEMBER, layer.participant_id)
            entry = _surface(
                surfaces,
                layer.participant_id,
                layer.physical_element_id,
                layer.entry_patch_id,
                layer.entry_face_role,
            )
            exit_surface = _surface(
                surfaces,
                layer.participant_id,
                layer.physical_element_id,
                layer.exit_patch_id,
                layer.exit_face_role,
            )
            layers.append(
                IntendedPenetratedLayer(
                    layer.id,
                    participant,
                    layer.physical_element_id,
                    entry.reference,
                    exit_surface.reference,
                    (
                        InterfaceZoneReference(
                            interface.id,
                            layer.interface_side,
                            layer.zone_id,
                        ),
                    ),
                    _geometry_scalar(layer.hole_diameter, length_unit),
                )
            )
        paths.append(BoltPathDefinition(path.bolt_location_id, tuple(layers)))
    resolved_group = resolve_bolt_group_geometry(
        basis,
        BoltGroupGeometrySpecification(
            group,
            group_dto.primary_interface_id,
            _geometry_scalar(group_dto.origin_y, length_unit),
            _geometry_scalar(group_dto.origin_z, length_unit),
            _direction(group_dto.in_plane_reference),
            tolerance,
            tuple(paths),
        ),
    )
    context = JointGeometryContext(basis, (resolved_group,))

    materials = tuple(_material_snapshot(item) for item in dto.material_snapshots)
    material_by_id = {item.id: item for item in materials}
    if len(material_by_id) != len(materials):
        raise ValueError("Material snapshot identities must be unique.")
    assignments = tuple(
        PenetratedLayerMaterialAssignment(
            item.participant_id,
            item.physical_element_id,
            item.material_region_id,
            material_by_id[item.material_snapshot_id],
            item.bearing_thread_status,
            item.element_form,
            item.potential_perpendicular_element_exemption,
        )
        for item in dto.material_assignments
    )
    demand_assignment = None
    if dto.explicit_resolved_demand is not None:
        demand = dto.explicit_resolved_demand
        in_plane = _vector_components(
            demand.in_plane_force_vector, demand.in_plane_force_vector.unit
        )
        resolved_demand = ResolvedSingleBoltDemand(
            demand.id,
            demand.load_combination_id,
            demand.source_member_id,
            demand.source_action_id,
            demand.source_kind,
            demand.factored_action_confirmed,
            demand.coordinate_frame_reference,
            _frame(
                geometry.joint_frame
                if dto.geometry_template is not None
                else demand.resolved_frame,
                length_unit,
            ),
            demand.source_reference_point_id,
            _point(
                geometry.joint_frame.origin
                if dto.geometry_template is not None
                else demand.resolved_global_reference_point,
                length_unit,
            ),
            Vector3D(*in_plane),
            demand.in_plane_force_vector.unit,
            _quantity(demand.bolt_axis_tensile_demand, Dimension.FORCE),
            _quantity(demand.externally_supplied_prying_demand, Dimension.FORCE),
            demand.loading_sense,
            demand.provenance,
            demand.distribution_status,
        )
        demand_assignment = ExplicitBoltDemandAssignment(
            demand.interface_id,
            demand.bolt_group_id,
            demand.bolt_location_id,
            resolved_demand,
        )
    template_orientation = _template_orientation_context(
        dto,
        geometry,
        placed_members,
        tolerance,
    )
    return SingleBoltOrchestrationRequest(
        dto.calculation_id,
        assembly,
        context,
        dto.interface_id,
        dto.bolt_group_id,
        dto.bolt_location_id,
        dto.load_combination_id,
        assignments,
        _fastener_snapshot(dto.fastener_snapshot),
        _quantity(dto.bolt_diameter, Dimension.LENGTH),
        dto.published_code_unit_basis,
        select_time_effect_factor(dto.time_effect_category),
        EndUseFactors(
            Decimal(dto.end_use_factors.cm),
            Decimal(dto.end_use_factors.ct),
            Decimal(dto.end_use_factors.cch),
            dto.end_use_factors.source_reference,
            dto.end_use_factors.approval_metadata,
        ),
        dto.lap_configuration,
        demand_assignment,
        dto.source_action_id,
        dto.whole_connection_requires_section_2_3_2,
        template_orientation,
    )


def map_single_bolt_preview_request(
    dto: SingleBoltPreviewRequestDTO,
) -> SingleBoltOrchestrationRequest:
    """Reuse the exact design mapper while keeping design-only transport fields absent.

    The injected values satisfy the existing immutable request container only.  The preview
    application service never reads them and never enters fingerprint, planning, or equation
    execution.  Fastener source identity is reconstructed from the trusted server preset;
    only exact-known washer display geometry is accepted from the preview DTO.
    """

    approved = create_locked_f593_fastener_snapshot()
    if dto.fastener_snapshot.id != approved.id:
        raise ValueError("The current preview supports the trusted F593 fastener identity only.")
    payload = dto.model_dump(mode="json")
    payload.pop("view_extents", None)
    fastener = cast(
        dict[str, JsonValue],
        _json_value(approved, dto.joint_assembly.unit_system),
    )
    fastener["washer_geometry"] = cast(
        JsonValue,
        None
        if dto.fastener_snapshot.washer_geometry is None
        else dto.fastener_snapshot.washer_geometry.model_dump(mode="json"),
    )
    payload["fastener_snapshot"] = fastener
    payload.update(
        {
            "published_code_unit_basis": "US_CUSTOMARY_PRINTED",
            "time_effect_category": "WIND_TORNADO_SEISMIC",
            "end_use_factors": {
                "cm": "1",
                "ct": "1",
                "cch": "1",
                "source_reference": "PREVIEW_CONTAINER_ONLY_NOT_EVALUATED",
                "approval_metadata": ["ZERO_RESISTANCE_PREVIEW"],
            },
            "whole_connection_requires_section_2_3_2": False,
        }
    )
    return map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))


def map_connection_view_extents(
    dto: SingleBoltPreviewRequestDTO,
) -> ConnectionViewExtents | None:
    """Map preview-only context lengths without admitting them to design geometry."""

    values = dto.view_extents
    if values is None:
        return None
    length_unit = Unit.IN if dto.joint_assembly.unit_system.value == "US_CUSTOMARY" else Unit.MM

    def positive(value: QuantityDTO, name: str) -> float:
        mapped = _geometry_scalar(value, length_unit)
        if mapped <= 0.0:
            raise ValueError(f"{name} must be greater than zero.")
        return mapped

    return ConnectionViewExtents(
        positive(values.brace_view_length, "brace_view_length"),
        positive(values.column_view_extent_below, "column_view_extent_below"),
        positive(values.column_view_extent_above, "column_view_extent_above"),
    )


def _profile_unit(dimension: Dimension, unit_system: object) -> Unit:
    us = getattr(unit_system, "value", unit_system) == "US_CUSTOMARY"
    return {
        Dimension.LENGTH: Unit.IN if us else Unit.MM,
        Dimension.AREA: Unit.IN2 if us else Unit.MM2,
        Dimension.FORCE: Unit.KIP if us else Unit.KN,
        Dimension.MOMENT: Unit.KIP_IN if us else Unit.KN_MM,
        Dimension.STRESS: Unit.KSI if us else Unit.MPA,
        Dimension.DIMENSIONLESS: Unit.ONE,
    }[dimension]


def _quantity_json(value: PhysicalQuantity, unit_system: object) -> dict[str, JsonValue]:
    rendered = value.to(_profile_unit(value.dimension, unit_system))
    return {"value": canonical_decimal_string(rendered.magnitude), "unit": rendered.unit.value}


def _point_json(value: PositionVector3D, unit_system: object) -> dict[str, JsonValue]:
    unit = _profile_unit(Dimension.LENGTH, unit_system)
    return {
        "x": canonical_decimal_string(decimal_from_finite_real(value.x)),
        "y": canonical_decimal_string(decimal_from_finite_real(value.y)),
        "z": canonical_decimal_string(decimal_from_finite_real(value.z)),
        "unit": unit.value,
    }


def _json_value(value: object, unit_system: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, PhysicalQuantity):
        return _quantity_json(value, unit_system)
    if isinstance(value, PositionVector3D):
        return _point_json(value, unit_system)
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return cast(str, value.value)
    if isinstance(value, tuple | list):
        return [_json_value(item, unit_system) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item, unit_system) for key, item in value.items()}
    if is_dataclass(value):
        result: dict[str, JsonValue] = {}
        for field in fields(value):
            result[field.name] = _json_value(getattr(value, field.name), unit_system)
        return result
    raise TypeError(f"Unsupported response value type {type(value).__name__}.")


def _source_reference(result: FinalCalculationResult) -> SourceReferenceDTO:
    source = result.source_snapshot
    return SourceReferenceDTO(
        standard_id=source.standard_name,
        edition=source.edition,
        errata=source.errata_identifier,
        section=source.section,
        equation_id=source.equation_reference,
    )


def serialize_single_bolt_response(
    response: SingleBoltOrchestrationResponse,
    visualization: SingleBoltVisualizationSnapshot,
) -> SingleBoltEvaluationResponseDTO:
    """Serialize without recalculating any engineering status, result, or governing ID."""

    unit_system = response.unit_system
    calculation = response.calculation_result
    plans = () if calculation is None else calculation.planning_result.checks
    results = () if calculation is None else calculation.results
    source_values: list[SourceReferenceDTO] = []
    source_keys: set[tuple[str, str, str, str, str | None]] = set()
    for item in results:
        source = _source_reference(item)
        key = (
            source.standard_id,
            source.edition,
            source.errata,
            source.section,
            source.equation_id,
        )
        if key not in source_keys:
            source_keys.add(key)
            source_values.append(source)
    sources = tuple(source_values)
    demand_json: dict[str, JsonValue] | None = None
    if response.resolved_demand is not None:
        demand = response.resolved_demand.demand
        demand_json = cast(
            dict[str, JsonValue],
            _json_value(
                {
                    "interface_id": response.resolved_demand.interface_id,
                    "bolt_group_id": response.resolved_demand.bolt_group_id,
                    "bolt_location_id": response.resolved_demand.bolt_location_id,
                    "id": demand.id,
                    "load_combination_id": demand.load_combination_id,
                    "source_member_id": demand.source_member_id,
                    "source_action_id": demand.source_action_id,
                    "source_kind": demand.source_kind,
                    "factored_action_confirmed": demand.factored_action_confirmed,
                    "source_reference_point_id": demand.source_reference_point_id,
                    "resolved_global_reference_point": demand.resolved_global_reference_point,
                    "in_plane_force_magnitude": demand.in_plane_force_magnitude,
                    "bolt_axis_tensile_demand": demand.bolt_axis_tensile_demand,
                    "externally_supplied_prying_demand": (demand.externally_supplied_prying_demand),
                    "loading_sense": demand.loading_sense,
                    "provenance": demand.provenance,
                    "distribution_status": demand.distribution_status,
                },
                unit_system,
            ),
        )
    action_json: dict[str, JsonValue] | None = None
    if response.source_action_trace is not None:
        trace = response.source_action_trace
        action = trace.resolved_action
        force_unit = _profile_unit(Dimension.FORCE, unit_system)
        moment_unit = _profile_unit(Dimension.MOMENT, unit_system)
        length_unit = _profile_unit(Dimension.LENGTH, unit_system)
        action_json = {
            "action_id": action.action.id,
            "member_id": action.member.id,
            "load_combination_id": action.load_combination.id,
            "reference_point": _point_json(
                action.resolved_reference_point.global_position, unit_system
            ),
            "global_force": {
                "x": canonical_decimal_string(decimal_from_finite_real(action.global_force.fx)),
                "y": canonical_decimal_string(decimal_from_finite_real(action.global_force.fy)),
                "z": canonical_decimal_string(decimal_from_finite_real(action.global_force.fz)),
                "unit": force_unit.value,
            },
            "global_moment": {
                "x": canonical_decimal_string(decimal_from_finite_real(action.global_moment.mx)),
                "y": canonical_decimal_string(decimal_from_finite_real(action.global_moment.my)),
                "z": canonical_decimal_string(decimal_from_finite_real(action.global_moment.mz)),
                "unit": moment_unit.value,
            },
            "selected_bolt_center": _point_json(
                trace.selected_bolt_center.global_position, unit_system
            ),
            "raw_source_to_bolt_offset": {
                "x": canonical_decimal_string(
                    decimal_from_finite_real(trace.raw_source_to_bolt_offset.x)
                ),
                "y": canonical_decimal_string(
                    decimal_from_finite_real(trace.raw_source_to_bolt_offset.y)
                ),
                "z": canonical_decimal_string(
                    decimal_from_finite_real(trace.raw_source_to_bolt_offset.z)
                ),
                "unit": length_unit.value,
            },
            "automatic_moment_shift_applied": trace.automatic_moment_shift_applied,
        }
    material_json = tuple(
        cast(
            dict[str, JsonValue],
            _json_value(
                {
                    "participant_id": item.participant_id,
                    "physical_element_id": item.physical_element_id,
                    "material_region_id": item.material_region_id,
                    "snapshot_id": item.material_snapshot.id,
                    "snapshot_name": item.material_snapshot.display_name,
                    "locked": item.material_snapshot.locked,
                    "basis": item.material_snapshot.basis,
                    "qualification_statuses": item.material_snapshot.qualification_statuses,
                    "properties": item.material_snapshot.properties,
                    "explicitly_missing": item.material_snapshot.explicitly_missing,
                    "bearing_thread_status": item.bearing_thread_status,
                    "element_form": item.element_form,
                    "potential_perpendicular_element_exemption": (
                        item.potential_perpendicular_element_exemption
                    ),
                },
                unit_system,
            ),
        )
        for item in response.material_assignments_used
    )
    fastener_json = cast(
        dict[str, JsonValue],
        _json_value(response.fastener_snapshot, unit_system),
    )
    layer_json = tuple(
        cast(
            dict[str, JsonValue],
            _json_value(
                {
                    "layer_id": item.layer_id,
                    "participant_kind": item.participant.kind,
                    "participant_id": item.participant.entity_id,
                    "physical_element_id": item.physical_element_id,
                    "material_region_id": item.material_region_id,
                    "component_material_kind": item.component_material_kind,
                    "entry_surface_patch_id": item.entry_surface_patch_id,
                    "exit_surface_patch_id": item.exit_surface_patch_id,
                    "connection_zone_ids": item.connection_zone_ids,
                    "hole_diameter": item.hole_diameter,
                    "code_mapping": item.code_mapping,
                    "code_geometry_validation": item.code_geometry_validation,
                },
                unit_system,
            ),
        )
        for item in response.resolved_layers
    )
    return SingleBoltEvaluationResponseDTO(
        api_transport_schema_version=API_TRANSPORT_SCHEMA_VERSION,
        project_schema_version=response.project_schema_version,
        calculation_contract_version=response.calculation_contract_version,
        calculation_engine_version=response.calculation_engine_version,
        engineering_rule_set_version=response.engineering_rule_set_version,
        calculation_id=response.calculation_id,
        assembly_id=response.assembly_id,
        interface_id=response.interface_id,
        bolt_group_id=response.bolt_group_id,
        bolt_location_id=response.bolt_location_id,
        load_combination_id=response.load_combination_id,
        unit_system=response.unit_system,
        calculation_fingerprint=response.calculation_fingerprint,
        material_assignments=material_json,
        fastener=fastener_json,
        resolved_layers=layer_json,
        source_action_trace=action_json,
        resolved_demand=demand_json,
        plans=tuple(cast(dict[str, JsonValue], _json_value(item, unit_system)) for item in plans),
        results=tuple(
            cast(dict[str, JsonValue], _json_value(item, unit_system)) for item in results
        ),
        aggregate_status=None
        if response.aggregate_status is None
        else response.aggregate_status.value,
        governing_check_ids=response.governing_check_ids,
        qualification_flags=tuple(item.value for item in response.qualification_flags),
        issues=tuple(
            OrchestrationIssueDTO(
                code=item.code.value,
                message=item.message,
                identities=item.identities,
            )
            for item in response.issues
        ),
        warnings=response.warnings,
        source_references=sources,
        visualization=cast(
            dict[str, JsonValue],
            _json_value(visualization, unit_system),
        ),
    )


def serialize_single_bolt_preview_response(
    result: SingleBoltPreviewResult,
) -> SingleBoltPreviewResponseDTO:
    """Serialize the model-only preview without exposing design-result fields."""

    trace = result.orchestration_trace
    rendered: dict[str, object] = {}
    if result.visualization is not None:
        rendered = serialize_single_bolt_response(
            trace,
            result.visualization,
        ).model_dump(mode="json")
    relationships = tuple(
        cast(
            dict[str, JsonValue],
            _json_value(
                {
                    "layer_id": item.physical_element_id,
                    "theta_degrees": item.theta_degrees,
                    "direction_family": item.direction_family,
                    "direction_interpretation_id": item.direction_interpretation_id,
                },
                trace.unit_system,
            ),
        )
        for item in result.material_relationships
    )
    return SingleBoltPreviewResponseDTO(
        preview_schema_version="0.2.0-draft",
        project_schema_version=trace.project_schema_version,
        calculation_id=trace.calculation_id,
        assembly_id=trace.assembly_id,
        interface_id=trace.interface_id,
        bolt_group_id=trace.bolt_group_id,
        bolt_location_id=trace.bolt_location_id,
        load_combination_id=trace.load_combination_id,
        unit_system=trace.unit_system,
        geometry_status=result.geometry_status.value,
        geometry_issues=tuple(
            OrchestrationIssueDTO(
                code=item.code.value,
                message=item.message,
                identities=item.identities,
            )
            for item in trace.issues
        ),
        resolved_layers=cast(
            tuple[dict[str, JsonValue], ...],
            tuple(
                cast(
                    list[dict[str, JsonValue]],
                    rendered.get("resolved_layers", []),
                )
            ),
        ),
        material_relationships=relationships,
        source_action_trace=cast(
            dict[str, JsonValue] | None,
            rendered.get("source_action_trace"),
        ),
        visualization=cast(
            dict[str, JsonValue] | None,
            rendered.get("visualization"),
        ),
        design_check_ready=result.design_check_ready,
        design_check_blocking_reasons=result.design_check_blocking_reasons,
    )


__all__ = (
    "map_connection_view_extents",
    "map_single_bolt_preview_request",
    "map_single_bolt_request",
    "serialize_single_bolt_preview_response",
    "serialize_single_bolt_response",
)
