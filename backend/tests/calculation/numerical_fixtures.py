"""Deterministic physical inputs for Stage 2.1B numerical tests."""

from dataclasses import replace
from decimal import Decimal

from frp_master_connection.calculation import (
    CalculationReadinessStatus,
    CodeGeometryValidation,
    DemandDistributionStatus,
    DemandSourceKind,
    Dimension,
    EffectiveWidthMappingStatus,
    EndUseFactors,
    GeometryMappingIssue,
    GeometryToCodeMapping,
    LapConfiguration,
    LayerLoadingSense,
    LayerPlanningInput,
    MaterialDirectionFamily,
    PhysicalQuantity,
    PultrudedElementForm,
    ResolvedSingleBoltDemand,
    SingleBoltPlanningInput,
    ThreadStatus,
    ThreadStatusAssignment,
    TimeEffectCategory,
    Unit,
    WasherGeometry,
    create_lap_factor_plan,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_single_bolt_geometry_factor_plan,
    create_synthetic_fastener_snapshot,
    select_time_effect_factor,
)
from frp_master_connection.domain import PositionVector3D
from frp_master_connection.geometry import GLOBAL_FRAME, Vector3D

HASH = "2" * 64


def mapping(
    layer_id: str,
    *,
    thickness: str = "0.375",
    e1: str = "2.000",
    e2: str = "2.000",
    width: str = "4.000",
    theta: str = "0",
    direction: MaterialDirectionFamily = MaterialDirectionFamily.LONGITUDINAL,
) -> GeometryToCodeMapping:
    interpretation = "TRANSVERSE_ENDPOINT_INCLUDED" if Decimal(theta) == Decimal(90) else None
    issues: tuple[GeometryMappingIssue, ...] = (
        GeometryMappingIssue.HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3,
    )
    if interpretation is not None:
        issues = (*issues, GeometryMappingIssue.EXACT_90_TRANSVERSE_INTERPRETATION)
    half_width = PhysicalQuantity.of(Decimal(width) / Decimal(2), Unit.IN)
    return GeometryToCodeMapping(
        participant_id=f"participant-{layer_id}",
        component_id=f"component-{layer_id}",
        physical_element_id=layer_id,
        material_region_id=f"region-{layer_id}",
        bolt_location_id="bolt-1",
        source_surface_patch_ids=(f"{layer_id}-entry", f"{layer_id}-exit"),
        bolt_diameter=PhysicalQuantity.of("0.500", Unit.IN),
        hole_diameter=PhysicalQuantity.of("0.563", Unit.IN),
        layer_thickness=PhysicalQuantity.of(thickness, Unit.IN),
        signed_in_plane_force_direction=(Decimal(1), Decimal(0), Decimal(0)),
        theta_degrees=Decimal(theta),
        direction_family=direction,
        direction_interpretation_id=interpretation,
        loaded_end_forward_intersection=PositionVector3D(float(e1), 0.0, 0.0),
        forward_e1=PhysicalQuantity.of(e1, Unit.IN),
        reverse_end_intersection=PositionVector3D(-float(e1), 0.0, 0.0),
        reverse_end_distance=PhysicalQuantity.of(e1, Unit.IN),
        raw_side_distance_1=PhysicalQuantity.of(e2, Unit.IN),
        raw_side_distance_2=PhysicalQuantity.of(e2, Unit.IN),
        e2_min=PhysicalQuantity.of("0.750", Unit.IN),
        effective_e3=half_width,
        effective_e4=half_width,
        effective_width=PhysicalQuantity.of(width, Unit.IN),
        effective_width_status=EffectiveWidthMappingStatus.SUPPORTED,
        hole_containment_provenance=("Stage 1.3C3 exact containment",),
        source_unit_identity=Unit.IN,
        issues=issues,
    )


def demand(
    in_plane_kip: str,
    *,
    axial_kip: str = "0",
    prying_kip: str = "0",
    sense: LayerLoadingSense = LayerLoadingSense.TENSION,
    force_unit: Unit = Unit.KIP,
) -> ResolvedSingleBoltDemand:
    magnitude = PhysicalQuantity.of(in_plane_kip, Unit.KIP).to(force_unit).magnitude
    return ResolvedSingleBoltDemand(
        id="demand-1",
        load_combination_id="LC-1",
        source_member_id="member-1",
        source_action_id="action-1",
        source_kind=DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND,
        factored_action_confirmed=True,
        coordinate_frame_reference="GLOBAL",
        resolved_frame=GLOBAL_FRAME,
        source_reference_point_id="point-1",
        resolved_global_reference_point=PositionVector3D(0.0, 0.0, 0.0),
        in_plane_force_vector=Vector3D(float(magnitude), 0.0, 0.0),
        force_vector_unit=force_unit,
        bolt_axis_tensile_demand=PhysicalQuantity.of(axial_kip, Unit.KIP).to(force_unit),
        externally_supplied_prying_demand=PhysicalQuantity.of(prying_kip, Unit.KIP).to(force_unit),
        loading_sense=sense,
        provenance=("RC2 explicit resolved per-bolt demand",),
        distribution_status=DemandDistributionStatus.EXPLICITLY_RESOLVED,
    )


def planning_input(
    layers: tuple[GeometryToCodeMapping, ...],
    resolved_demand: ResolvedSingleBoltDemand,
    *,
    single_lap: bool = False,
    qualification: bool = False,
    synthetic_bolt: bool = False,
    element_forms: tuple[PultrudedElementForm, ...] | None = None,
) -> SingleBoltPlanningInput:
    forms = element_forms or tuple(PultrudedElementForm.SHAPE_ELEMENT for _ in layers)
    layer_inputs = tuple(
        LayerPlanningInput(
            layer,
            CodeGeometryValidation(CalculationReadinessStatus.READY, ()),
            ThreadStatus.EXCLUDED,
            False,
            form,
        )
        for layer, form in zip(layers, forms, strict=True)
    )
    if synthetic_bolt:
        fastener = replace(
            create_synthetic_fastener_snapshot(
                id="B1_SYNTHETIC",
                fnt=PhysicalQuantity.of("100", Unit.KSI),
            ),
            shear_plane_thread_statuses=(
                ThreadStatusAssignment("shear-plane-1", ThreadStatus.EXCLUDED),
            ),
            bearing_layer_thread_statuses=tuple(
                ThreadStatusAssignment(layer.physical_element_id, ThreadStatus.EXCLUDED)
                for layer in layers
            ),
            number_of_shear_planes=1,
        )
    else:
        fastener = create_locked_f593_fastener_snapshot()
    return SingleBoltPlanningInput(
        connection_id="connection-1",
        bolt_id="bolt-1",
        demand=resolved_demand,
        layers=layer_inputs,
        material=create_locked_ice_material_snapshot(),
        fastener=fastener,
        washer=WasherGeometry(
            PhysicalQuantity.of("1.000", Unit.IN),
            PhysicalQuantity.of("0.051", Unit.IN),
            True,
            True,
        ),
        time_effect=select_time_effect_factor(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        end_use_factors=EndUseFactors(
            Decimal("1.0"),
            Decimal("1.0"),
            Decimal("1.0"),
            "ASCE/SEI 74-23 Section 2.4.4",
            ("RC2 explicit unity factors",),
        ),
        lap_factor=create_lap_factor_plan(
            LapConfiguration.SINGLE_LAP if single_lap else LapConfiguration.DOUBLE_LAP
        ),
        geometry_factor=create_single_bolt_geometry_factor_plan(),
        input_fingerprint=HASH,
        whole_connection_requires_section_2_3_2=qualification,
    )


def p1_input(*, force_unit: Unit = Unit.KIP) -> SingleBoltPlanningInput:
    return planning_input((mapping("P1"),), demand("3.000", force_unit=force_unit))


def pt1_input(*, force_unit: Unit = Unit.KIP) -> SingleBoltPlanningInput:
    return planning_input(
        (mapping("P1"),),
        demand("3.000", axial_kip="0.500", force_unit=force_unit),
    )


def p2a_input(*, force_unit: Unit = Unit.KIP) -> SingleBoltPlanningInput:
    return planning_input(
        (
            mapping("layer_A"),
            mapping("layer_B", thickness="0.500", e2="1.500", width="3.000"),
        ),
        demand("2.000", force_unit=force_unit),
        single_lap=True,
    )


def p2b_input(*, force_unit: Unit = Unit.KIP) -> SingleBoltPlanningInput:
    return planning_input(
        (
            mapping("layer_A"),
            mapping(
                "layer_B",
                thickness="0.500",
                e2="1.500",
                width="3.000",
                theta="45",
                direction=MaterialDirectionFamily.TRANSVERSE,
            ),
        ),
        demand("2.000", force_unit=force_unit),
        single_lap=True,
    )


def j1_input(
    *,
    compression: bool = False,
    force_unit: Unit = Unit.KIP,
) -> SingleBoltPlanningInput:
    return planning_input(
        (
            mapping("angle_leg", e2="1.500", width="3.000"),
            mapping(
                "w_flange",
                thickness="0.500",
                # Stage 1.3C3 geometry retains the exact projected physical
                # distance; the golden file prints this input at 12 decimals.
                e1="2.1213203435596425732025330863145471178545078130654",
                e2="1.500",
                width="3.000",
                theta="45",
                direction=MaterialDirectionFamily.TRANSVERSE,
            ),
        ),
        demand(
            "0.700",
            sense=(LayerLoadingSense.COMPRESSION if compression else LayerLoadingSense.TENSION),
            force_unit=force_unit,
        ),
        single_lap=True,
        qualification=True,
    )


def b1_input(*, force_unit: Unit = Unit.KIP) -> SingleBoltPlanningInput:
    return planning_input(
        (mapping("B1"),),
        demand("5.0", axial_kip="2.0", force_unit=force_unit),
        synthetic_bolt=True,
    )


def direction_90_input() -> SingleBoltPlanningInput:
    return planning_input(
        (
            mapping(
                "DIRECTION_90",
                theta="90",
                direction=MaterialDirectionFamily.TRANSVERSE,
            ),
        ),
        demand("3.0"),
    )


def _si_quantity(quantity: PhysicalQuantity) -> PhysicalQuantity:
    target = {
        Dimension.LENGTH: Unit.MM,
        Dimension.AREA: Unit.MM2,
        Dimension.FORCE: Unit.KN,
        Dimension.STRESS: Unit.MPA,
        Dimension.DIMENSIONLESS: Unit.ONE,
    }.get(quantity.dimension)
    return quantity if target is None else quantity.to(target)


def _optional_si_quantity(quantity: PhysicalQuantity | None) -> PhysicalQuantity | None:
    return None if quantity is None else _si_quantity(quantity)


def _si_position(position: PositionVector3D) -> PositionVector3D:
    return PositionVector3D(position.x * 25.4, position.y * 25.4, position.z * 25.4)


def to_si(source: SingleBoltPlanningInput) -> SingleBoltPlanningInput:
    """Return one exact physical conversion, never a regenerated SI hole fixture."""

    converted_layers = tuple(
        replace(
            layer,
            mapping=replace(
                layer.mapping,
                bolt_diameter=_si_quantity(layer.mapping.bolt_diameter),
                hole_diameter=_si_quantity(layer.mapping.hole_diameter),
                layer_thickness=_si_quantity(layer.mapping.layer_thickness),
                loaded_end_forward_intersection=_si_position(
                    layer.mapping.loaded_end_forward_intersection
                ),
                forward_e1=_si_quantity(layer.mapping.forward_e1),
                reverse_end_intersection=_si_position(layer.mapping.reverse_end_intersection),
                reverse_end_distance=_si_quantity(layer.mapping.reverse_end_distance),
                raw_side_distance_1=_si_quantity(layer.mapping.raw_side_distance_1),
                raw_side_distance_2=_si_quantity(layer.mapping.raw_side_distance_2),
                e2_min=_si_quantity(layer.mapping.e2_min),
                effective_e3=_optional_si_quantity(layer.mapping.effective_e3),
                effective_e4=_optional_si_quantity(layer.mapping.effective_e4),
                effective_width=_optional_si_quantity(layer.mapping.effective_width),
                source_unit_identity=Unit.MM,
            ),
        )
        for layer in source.layers
    )
    demand_force = source.demand.in_plane_force_magnitude.to(Unit.KN).magnitude
    converted_demand = replace(
        source.demand,
        in_plane_force_vector=Vector3D(float(demand_force), 0.0, 0.0),
        force_vector_unit=Unit.KN,
        bolt_axis_tensile_demand=source.demand.bolt_axis_tensile_demand.to(Unit.KN),
        externally_supplied_prying_demand=(
            source.demand.externally_supplied_prying_demand.to(Unit.KN)
        ),
        resolved_global_reference_point=_si_position(source.demand.resolved_global_reference_point),
    )
    converted_material = replace(
        source.material,
        properties=tuple(
            replace(entry, value=_si_quantity(entry.value)) for entry in source.material.properties
        ),
    )
    converted_fastener = replace(
        source.fastener,
        diameter_min=source.fastener.diameter_min.to(Unit.MM),
        diameter_max=source.fastener.diameter_max.to(Unit.MM),
        fnt=None if source.fastener.fnt is None else source.fastener.fnt.to(Unit.MPA),
        washer_geometry=(
            None
            if source.fastener.washer_geometry is None
            else replace(
                source.fastener.washer_geometry,
                outside_diameter=source.fastener.washer_geometry.outside_diameter.to(Unit.MM),
                thickness=source.fastener.washer_geometry.thickness.to(Unit.MM),
            )
        ),
    )
    converted_washer = (
        None
        if source.washer is None
        else replace(
            source.washer,
            outside_diameter=source.washer.outside_diameter.to(Unit.MM),
            thickness=source.washer.thickness.to(Unit.MM),
        )
    )
    return replace(
        source,
        demand=converted_demand,
        layers=converted_layers,
        material=converted_material,
        fastener=converted_fastener,
        washer=converted_washer,
    )


__all__ = (
    "HASH",
    "b1_input",
    "demand",
    "direction_90_input",
    "j1_input",
    "mapping",
    "p1_input",
    "p2a_input",
    "p2b_input",
    "planning_input",
    "pt1_input",
    "to_si",
)
