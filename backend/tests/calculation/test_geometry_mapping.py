"""Geometry-to-code mapping and non-numerical code-geometry validation tests."""

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest

from frp_master_connection.calculation import (
    CalculationReadinessStatus,
    CodeGeometryIssue,
    EffectiveWidthMappingStatus,
    GeometryMappingIssue,
    GeometryToCodeMapping,
    GeometryToCodeMappingRequest,
    LayerLoadingSense,
    MaterialDirectionFamily,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    WasherGeometry,
    create_locked_f593_fastener_snapshot,
    create_standard_hole,
    resolve_geometry_to_code_mapping,
    validate_code_geometry,
)
from frp_master_connection.calculation.geometry_mapping import _ray_to_rectangle
from frp_master_connection.domain import PositionVector3D, PrincipalAxisFamily
from frp_master_connection.geometry import (
    Annulus2D,
    PhysicalElementGeometry2D,
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    SectionPoint2D,
    Vector3D,
)
from tests.c3_fixtures import build_c3_case


def _request(
    *,
    offset_y: float = 0.0,
    offset_z: float = 0.0,
    bolt_diameter: str = "0.5",
    force: Vector3D | None = None,
    lengthwise: PrincipalAxisFamily = PrincipalAxisFamily.X,
) -> GeometryToCodeMappingRequest:
    case = build_c3_case(pultruded_frp=True)
    group = case.resolved_bolt_group
    if offset_y or offset_z:
        specification = replace(case.bolt_specification, origin_y=offset_y, origin_z=offset_z)
        from frp_master_connection.geometry import resolve_bolt_group_geometry

        group = resolve_bolt_group_geometry(case.basis, specification)
    layer = group.paths[0].layers[0]
    selected_force = force or Vector3D(
        layer.physical_element.global_frame.x_axis.x,
        layer.physical_element.global_frame.x_axis.y,
        layer.physical_element.global_frame.x_axis.z,
    )
    return GeometryToCodeMappingRequest(
        resolved_bolt_group=group,
        bolt_location_id="bolt-1",
        layer_id="member-layer",
        bolt_diameter=PhysicalQuantity.of(bolt_diameter, Unit.MM),
        signed_in_plane_force=selected_force,
        component_lengthwise_axis=lengthwise,
        source_length_unit=Unit.MM,
    )


def _ready_mapping() -> GeometryToCodeMapping:
    return GeometryToCodeMapping(
        participant_id="member-1",
        component_id="member-1",
        physical_element_id="PLATE",
        material_region_id="PLATE",
        bolt_location_id="bolt-1",
        source_surface_patch_ids=("entry", "exit"),
        bolt_diameter=PhysicalQuantity.of("0.500", Unit.IN),
        hole_diameter=PhysicalQuantity.of("0.563", Unit.IN),
        layer_thickness=PhysicalQuantity.of("0.375", Unit.IN),
        signed_in_plane_force_direction=(Decimal(1), Decimal(0), Decimal(0)),
        theta_degrees=Decimal(0),
        direction_family=MaterialDirectionFamily.LONGITUDINAL,
        direction_interpretation_id=None,
        loaded_end_forward_intersection=PositionVector3D(2.0, 0.0, 0.0),
        forward_e1=PhysicalQuantity.of("2.000", Unit.IN),
        reverse_end_intersection=PositionVector3D(-2.0, 0.0, 0.0),
        reverse_end_distance=PhysicalQuantity.of("2.000", Unit.IN),
        raw_side_distance_1=PhysicalQuantity.of("2.000", Unit.IN),
        raw_side_distance_2=PhysicalQuantity.of("2.000", Unit.IN),
        e2_min=PhysicalQuantity.of("0.750", Unit.IN),
        effective_e3=PhysicalQuantity.of("2.000", Unit.IN),
        effective_e4=PhysicalQuantity.of("2.000", Unit.IN),
        effective_width=PhysicalQuantity.of("4.000", Unit.IN),
        effective_width_status=EffectiveWidthMappingStatus.SUPPORTED,
        hole_containment_provenance=("Stage 1.3C3",),
        source_unit_identity=Unit.IN,
        issues=(GeometryMappingIssue.HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3,),
    )


def _washer() -> WasherGeometry:
    return WasherGeometry(
        PhysicalQuantity.of("1.000", Unit.IN),
        PhysicalQuantity.of("0.051", Unit.IN),
        True,
        True,
    )


def test_mapping_reuses_c3_geometry_and_returns_raw_physical_boundaries() -> None:
    mapping = resolve_geometry_to_code_mapping(_request())
    assert mapping.participant_id == "member-1"
    assert mapping.physical_element_id == "PLATE"
    assert mapping.material_region_id == "PLATE"
    assert mapping.bolt_location_id == "bolt-1"
    assert mapping.source_surface_patch_ids[0] != mapping.source_surface_patch_ids[1]
    assert mapping.hole_diameter == PhysicalQuantity.of("1.0", Unit.MM)
    assert mapping.layer_thickness == PhysicalQuantity.of("1.0", Unit.MM)
    assert mapping.forward_e1 == PhysicalQuantity.of("5.0", Unit.MM)
    assert mapping.reverse_end_distance == PhysicalQuantity.of("5.0", Unit.MM)
    assert mapping.raw_side_distance_1 == PhysicalQuantity.of("2.0", Unit.MM)
    assert mapping.raw_side_distance_2 == PhysicalQuantity.of("2.0", Unit.MM)
    assert mapping.effective_e3 == mapping.raw_side_distance_1
    assert mapping.effective_e4 == mapping.raw_side_distance_2
    assert mapping.effective_width == PhysicalQuantity.of("4.0", Unit.MM)
    assert mapping.theta_degrees == Decimal(0)
    assert mapping.direction_family is MaterialDirectionFamily.LONGITUDINAL
    assert mapping.direction_interpretation_id is None
    assert mapping.effective_width_status is EffectiveWidthMappingStatus.SUPPORTED
    assert mapping.source_unit_identity is Unit.MM
    assert mapping.issues == (GeometryMappingIssue.HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3,)
    assert mapping.hole_containment_provenance[0].startswith("entry_patch:")
    assert any(item.startswith("zone:") for item in mapping.hole_containment_provenance)


def test_force_reversal_swaps_loaded_and_reverse_ends_without_changing_material_angle() -> None:
    forward_request = _request(offset_y=1.0)
    forward = resolve_geometry_to_code_mapping(forward_request)
    reversed_force = -forward_request.signed_in_plane_force
    reverse = resolve_geometry_to_code_mapping(
        replace(forward_request, signed_in_plane_force=reversed_force)
    )
    assert forward.forward_e1 == reverse.reverse_end_distance
    assert forward.reverse_end_distance == reverse.forward_e1
    assert forward.loaded_end_forward_intersection == reverse.reverse_end_intersection
    assert forward.theta_degrees == reverse.theta_degrees
    assert forward.direction_family is reverse.direction_family


def test_side_distance_cases_preserve_printed_mapping_boundaries() -> None:
    equal = resolve_geometry_to_code_mapping(_request())
    assert equal.effective_e3 == equal.raw_side_distance_1
    one_near = resolve_geometry_to_code_mapping(_request(offset_z=0.5, bolt_diameter="0.5"))
    assert one_near.raw_side_distance_1 != one_near.raw_side_distance_2
    assert {one_near.effective_e3, one_near.effective_e4} == {
        PhysicalQuantity.of("1.5", Unit.MM),
    }
    both_far = resolve_geometry_to_code_mapping(_request(offset_z=0.5, bolt_diameter="0.25"))
    assert both_far.effective_e3 == PhysicalQuantity.of("0.75", Unit.MM)
    assert both_far.effective_e4 == PhysicalQuantity.of("0.75", Unit.MM)
    unsupported = resolve_geometry_to_code_mapping(_request(offset_z=0.5, bolt_diameter="1.0"))
    assert unsupported.effective_width_status is (
        EffectiveWidthMappingStatus.CALCULATION_NOT_SUPPORTED
    )
    assert unsupported.effective_e3 is None
    assert unsupported.effective_e4 is None
    assert unsupported.effective_width is None
    assert GeometryMappingIssue.UNEQUAL_UNCAPPED_SIDE_DISTANCES_NOT_SUPPORTED in (
        unsupported.issues
    )


def test_directional_boundaries_include_exact_90_transverse_interpretation() -> None:
    request = _request()
    layer = request.resolved_bolt_group.paths[0].layers[0]
    transverse_axis = layer.physical_element.global_frame.y_axis
    transverse = resolve_geometry_to_code_mapping(
        replace(
            request,
            signed_in_plane_force=Vector3D(
                transverse_axis.x,
                transverse_axis.y,
                transverse_axis.z,
            ),
        )
    )
    assert transverse.theta_degrees == Decimal("90")
    assert transverse.direction_family is MaterialDirectionFamily.TRANSVERSE
    assert transverse.direction_interpretation_id == "TRANSVERSE_ENDPOINT_INCLUDED"
    assert GeometryMappingIssue.EXACT_90_TRANSVERSE_INTERPRETATION in transverse.issues
    z_lengthwise = resolve_geometry_to_code_mapping(
        replace(request, component_lengthwise_axis=PrincipalAxisFamily.Z)
    )
    assert z_lengthwise.direction_family is MaterialDirectionFamily.TRANSVERSE
    y_lengthwise = resolve_geometry_to_code_mapping(
        replace(request, component_lengthwise_axis=PrincipalAxisFamily.Y)
    )
    assert y_lengthwise.direction_family is MaterialDirectionFamily.TRANSVERSE
    angle_five = 5.0
    from math import cos, radians, sin

    x_axis = layer.physical_element.global_frame.x_axis
    y_axis = layer.physical_element.global_frame.y_axis
    force_five = Vector3D(
        x_axis.x * cos(radians(angle_five)) + y_axis.x * sin(radians(angle_five)),
        x_axis.y * cos(radians(angle_five)) + y_axis.y * sin(radians(angle_five)),
        x_axis.z * cos(radians(angle_five)) + y_axis.z * sin(radians(angle_five)),
    )
    at_five = resolve_geometry_to_code_mapping(replace(request, signed_in_plane_force=force_five))
    above_five = resolve_geometry_to_code_mapping(
        replace(
            request,
            signed_in_plane_force=Vector3D(
                x_axis.x * cos(radians(5.1)) + y_axis.x * sin(radians(5.1)),
                x_axis.y * cos(radians(5.1)) + y_axis.y * sin(radians(5.1)),
                x_axis.z * cos(radians(5.1)) + y_axis.z * sin(radians(5.1)),
            ),
        )
    )
    assert at_five.direction_family is MaterialDirectionFamily.LONGITUDINAL
    assert above_five.direction_family is MaterialDirectionFamily.TRANSVERSE


def test_mapping_request_and_resolution_reject_unsupported_or_inconsistent_geometry() -> None:
    valid = _request()
    with pytest.raises(TypeError, match="ResolvedBoltGroupGeometry"):
        replace(valid, resolved_bolt_group=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="identities must be nonempty"):
        replace(valid, layer_id="")
    with pytest.raises(ValueError, match="positive length"):
        replace(valid, bolt_diameter=PhysicalQuantity.of("0", Unit.MM))
    with pytest.raises(ValueError, match="positive length"):
        replace(valid, bolt_diameter=PhysicalQuantity.of("1", Unit.N))
    with pytest.raises(TypeError, match="Vector3D"):
        replace(valid, signed_in_plane_force=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonzero"):
        replace(valid, signed_in_plane_force=Vector3D(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="IN or MM"):
        replace(valid, source_length_unit=Unit.N)
    with pytest.raises(ValueError, match="must match"):
        replace(valid, source_length_unit=Unit.IN)
    with pytest.raises(KeyError, match="resolved path"):
        resolve_geometry_to_code_mapping(replace(valid, bolt_location_id="missing"))
    with pytest.raises(KeyError, match="penetrated layer"):
        resolve_geometry_to_code_mapping(replace(valid, layer_id="missing"))
    source_surface = cast(
        PlanarRectangularSurface3D,
        valid.resolved_bolt_group.paths[0].layers[0].entry.surface.geometry,
    )
    normal = source_surface.normal
    with pytest.raises(ValueError, match="must lie"):
        resolve_geometry_to_code_mapping(
            replace(valid, signed_in_plane_force=Vector3D(normal.x, normal.y, normal.z))
        )
    steel_case = build_c3_case()
    steel_request = replace(
        valid,
        resolved_bolt_group=steel_case.resolved_bolt_group,
    )
    with pytest.raises(ValueError, match="planar fixed material"):
        resolve_geometry_to_code_mapping(steel_request)
    path = valid.resolved_bolt_group.paths[0]
    layer = path.layers[0]
    nonrectangular_element = SimpleNamespace(
        source_geometry=PhysicalElementGeometry2D(
            "PLATE",
            (Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, 1.0),),
        )
    )
    corrupt_layer = replace(
        layer,
        physical_element=nonrectangular_element,  # type: ignore[arg-type]
    )
    corrupt_path = replace(path, layers=(corrupt_layer, *path.layers[1:]))
    corrupt_group = replace(valid.resolved_bolt_group, paths=(corrupt_path,))
    with pytest.raises(ValueError, match="flat rectangular"):
        resolve_geometry_to_code_mapping(replace(valid, resolved_bolt_group=corrupt_group))
    annular_surface = PlanarAnnularSurface3D(
        cast(PlanarRectangularSurface3D, layer.entry.surface.geometry).frame,
        2.0,
        1.0,
    )
    corrupt_surface = SimpleNamespace(geometry=annular_surface)
    corrupt_entry = SimpleNamespace(
        surface=corrupt_surface,
        point=layer.entry.point,
        raw_patch_clearance=layer.entry.raw_patch_clearance,
    )
    corrupt_surface_layer = replace(
        layer,
        entry=corrupt_entry,  # type: ignore[arg-type]
    )
    corrupt_surface_path = replace(path, layers=(corrupt_surface_layer, *path.layers[1:]))
    corrupt_surface_group = replace(
        valid.resolved_bolt_group,
        paths=(corrupt_surface_path,),
    )
    with pytest.raises(ValueError, match="planar rectangular broad face"):
        resolve_geometry_to_code_mapping(replace(valid, resolved_bolt_group=corrupt_surface_group))
    with pytest.raises(ValueError, match="does not intersect"):
        _ray_to_rectangle(0.0, 0.0, 0.0, 0.0, 1.0, 1.0)


def test_ready_code_geometry_plan_checks_no_strength() -> None:
    mapping = _ready_mapping()
    hole = create_standard_hole(
        mapping.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    result = validate_code_geometry(
        mapping=mapping,
        standard_hole=hole,
        fastener=create_locked_f593_fastener_snapshot(),
        washer=_washer(),
        loading_sense=LayerLoadingSense.TENSION,
        connection_hole_diameters=(mapping.hole_diameter, mapping.hole_diameter),
        logical_bolt_count=1,
        row_count=1,
    )
    assert result.status is CalculationReadinessStatus.READY
    assert result.issues == ()


@pytest.mark.parametrize(
    ("mapping", "sense", "washer", "hole", "bolt_count", "rows", "issue", "status"),
    [
        (
            replace(_ready_mapping(), bolt_diameter=PhysicalQuantity.of("0.25", Unit.IN)),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            1,
            1,
            CodeGeometryIssue.BOLT_DIAMETER_OUTSIDE_CHAPTER_8_RANGE,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            replace(_ready_mapping(), layer_thickness=PhysicalQuantity.of("0.1", Unit.IN)),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            1,
            1,
            CodeGeometryIssue.FRP_THICKNESS_BELOW_MINIMUM,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            replace(_ready_mapping(), forward_e1=PhysicalQuantity.of("1.9", Unit.IN)),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            1,
            1,
            CodeGeometryIssue.TENSION_END_DISTANCE_BELOW_4D,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            replace(_ready_mapping(), forward_e1=PhysicalQuantity.of("0.9", Unit.IN)),
            LayerLoadingSense.COMPRESSION,
            _washer(),
            None,
            1,
            1,
            CodeGeometryIssue.COMPRESSION_END_DISTANCE_BELOW_2D,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            replace(_ready_mapping(), raw_side_distance_1=PhysicalQuantity.of("0.7", Unit.IN)),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            1,
            1,
            CodeGeometryIssue.EDGE_DISTANCE_BELOW_1_5D,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            None,
            None,
            1,
            1,
            CodeGeometryIssue.WASHER_REQUIRED_UNDER_HEAD_AND_NUT,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            replace(_washer(), outside_diameter=PhysicalQuantity.of("0.9", Unit.IN)),
            None,
            1,
            1,
            CodeGeometryIssue.WASHER_OUTSIDE_DIAMETER_BELOW_2D,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            replace(_washer(), thickness=PhysicalQuantity.of("0.05", Unit.IN)),
            None,
            1,
            1,
            CodeGeometryIssue.WASHER_THICKNESS_BELOW_0_051_IN,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            replace(_washer(), under_nut=False),
            None,
            1,
            1,
            CodeGeometryIssue.WASHER_REQUIRED_UNDER_HEAD_AND_NUT,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            4,
            1,
            CodeGeometryIssue.ARRANGEMENT_REQUIRES_SECTION_2_3_2,
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            _ready_mapping(),
            LayerLoadingSense.TENSION,
            _washer(),
            None,
            2,
            1,
            CodeGeometryIssue.STAGE_2_1A_SUPPORTS_ONE_BOLT_ONE_ROW,
            CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED,
        ),
    ],
)
def test_code_geometry_qualification_and_unsupported_boundaries(
    mapping: GeometryToCodeMapping,
    sense: LayerLoadingSense,
    washer: WasherGeometry | None,
    hole: object | None,
    bolt_count: int,
    rows: int,
    issue: CodeGeometryIssue,
    status: CalculationReadinessStatus,
) -> None:
    del hole
    standard_hole = create_standard_hole(
        mapping.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    result = validate_code_geometry(
        mapping=mapping,
        standard_hole=standard_hole,
        fastener=create_locked_f593_fastener_snapshot(),
        washer=washer,
        loading_sense=sense,
        connection_hole_diameters=(mapping.hole_diameter,),
        logical_bolt_count=bolt_count,
        row_count=rows,
    )
    assert issue in result.issues
    assert result.status is status


def test_code_geometry_rejects_noncommon_holes_and_flags_missing_sources() -> None:
    mapping = _ready_mapping()
    invalid_common = validate_code_geometry(
        mapping=mapping,
        standard_hole=None,
        fastener=None,
        washer=_washer(),
        loading_sense=LayerLoadingSense.TENSION,
        connection_hole_diameters=(),
        logical_bolt_count=1,
        row_count=1,
    )
    assert invalid_common.status is CalculationReadinessStatus.INVALID_GEOMETRY
    assert CodeGeometryIssue.FASTENER_METADATA_MISSING in invalid_common.issues
    assert CodeGeometryIssue.STANDARD_ROUND_HOLE_REQUIRED in invalid_common.issues
    assert CodeGeometryIssue.COMMON_PHYSICAL_HOLE_REQUIRED in invalid_common.issues
    mismatch = validate_code_geometry(
        mapping=mapping,
        standard_hole=create_standard_hole(
            PhysicalQuantity.of("12.7", Unit.MM),
            PublishedCodeUnitBasis.SI_PRINTED,
        ),
        fastener=create_locked_f593_fastener_snapshot(),
        washer=_washer(),
        loading_sense=LayerLoadingSense.TENSION,
        connection_hole_diameters=(PhysicalQuantity.of("0.600", Unit.IN),),
        logical_bolt_count=1,
        row_count=4,
    )
    assert mismatch.status is CalculationReadinessStatus.INVALID_GEOMETRY
    assert CodeGeometryIssue.STANDARD_ROUND_HOLE_REQUIRED in mismatch.issues
