"""Declarative HTTP payload fixtures derived from committed Stage 2.2A cases."""

from __future__ import annotations

from typing import Any, cast

from frp_master_connection.application import SingleBoltOrchestrationRequest
from frp_master_connection.calculation import (
    FastenerSnapshot,
    MaterialPropertySnapshot,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_from_finite_real,
)
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    ReferencePointKind,
    SectionFamily,
)
from frp_master_connection.geometry import (
    AxisAlignedRectangle2D,
    CartesianFrame3D,
    CrossSectionGeometry2D,
    PlanarRectangularSurface3D,
    UnitVector3D,
    Vector3D,
)
from tests.application.orchestration_fixtures import (
    build_j1_case,
    build_j1_visual_case,
    build_plate_case,
)


def _decimal(value: float) -> str:
    return canonical_decimal_string(decimal_from_finite_real(value))


def _quantity(value: PhysicalQuantity, unit: Unit | None = None) -> dict[str, str]:
    selected = value if unit is None else value.to(unit)
    return {"value": canonical_decimal_string(selected.magnitude), "unit": selected.unit.value}


def _scalar(value: float, unit: Unit) -> dict[str, str]:
    return {"value": _decimal(value), "unit": unit.value}


def _point(value: PositionVector3D, unit: Unit) -> dict[str, str]:
    return {
        "x": _decimal(value.x),
        "y": _decimal(value.y),
        "z": _decimal(value.z),
        "unit": unit.value,
    }


def _direction(value: Vector3D | UnitVector3D) -> dict[str, str]:
    return {
        "x": _decimal(value.x),
        "y": _decimal(value.y),
        "z": _decimal(value.z),
    }


def _frame(value: CartesianFrame3D, unit: Unit) -> dict[str, object]:
    return {
        "origin": _point(value.origin, unit),
        "x_direction": _direction(value.x_axis),
        "local_z_reference": _direction(value.z_axis),
    }


def _rectangle(section: CrossSectionGeometry2D, element_id: str) -> AxisAlignedRectangle2D:
    primitive = next(
        item.geometry[0] for item in section.physical_elements if item.element_id == element_id
    )
    return cast(AxisAlignedRectangle2D, primitive)


def _section(section: CrossSectionGeometry2D, unit: Unit) -> dict[str, object]:
    bounds = section.outside_bounds
    width = bounds.max_y - bounds.min_y
    depth = bounds.max_z - bounds.min_z
    if section.section_family is SectionFamily.PLATE:
        return {
            "kind": "PLATE",
            "width": _scalar(width, unit),
            "thickness": _scalar(depth, unit),
        }
    if section.section_family is SectionFamily.ANGLE:
        leg = _rectangle(section, "LEG_1")
        return {
            "kind": "ANGLE",
            "leg_y": _scalar(width, unit),
            "leg_z": _scalar(depth, unit),
            "thickness": _scalar(leg.max_z - leg.min_z, unit),
        }
    web = _rectangle(section, "WEB")
    flange = _rectangle(section, "TOP_FLANGE")
    return {
        "kind": section.section_family.value,
        "overall_depth": _scalar(depth, unit),
        "flange_width": _scalar(width, unit),
        "web_thickness": _scalar(web.max_y - web.min_y, unit),
        "flange_thickness": _scalar(flange.max_z - flange.min_z, unit),
    }


def _material(snapshot: MaterialPropertySnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "display_name": snapshot.display_name,
        "locked": snapshot.locked,
        "basis": snapshot.basis.value,
        "qualification_statuses": [item.value for item in snapshot.qualification_statuses],
        "properties": [
            {
                "kind": item.kind.value,
                "value": _quantity(item.value),
                "behavior": item.behavior.value,
                "source_classification": item.source_classification.value,
                "qualification_status": item.qualification_status.value,
                "source_document": item.source_document,
                "source_revision": item.source_revision,
                "applicability_metadata": list(item.applicability_metadata),
                "engineer_notes": list(item.engineer_notes),
                "use_in_chapter_8_equations": item.use_in_chapter_8_equations,
            }
            for item in snapshot.properties
        ],
        "explicitly_missing": [item.value for item in snapshot.explicitly_missing],
    }


def _fastener(snapshot: FastenerSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "display_name": snapshot.display_name,
        "locked": snapshot.locked,
        "bolt_specification": snapshot.bolt_specification,
        "alloy_group": snapshot.alloy_group,
        "alloys": list(snapshot.alloys),
        "condition": snapshot.condition,
        "nut_specification": snapshot.nut_specification,
        "washer_material_basis": snapshot.washer_material_basis,
        "installation_condition": snapshot.installation_condition,
        "diameter_min": _quantity(snapshot.diameter_min),
        "diameter_max": _quantity(snapshot.diameter_max),
        "fnt": None if snapshot.fnt is None else _quantity(snapshot.fnt),
        "fnt_source_classification": snapshot.fnt_source_classification.value,
        "fnt_qualification_status": snapshot.fnt_qualification_status.value,
        "shear_plane_thread_statuses": [
            {"location_id": item.location_id, "status": item.status.value}
            for item in snapshot.shear_plane_thread_statuses
        ],
        "bearing_layer_thread_statuses": [
            {"location_id": item.location_id, "status": item.status.value}
            for item in snapshot.bearing_layer_thread_statuses
        ],
        "number_of_shear_planes": snapshot.number_of_shear_planes,
        "washer_geometry": (
            None
            if snapshot.washer_geometry is None
            else {
                "outside_diameter": _quantity(snapshot.washer_geometry.outside_diameter),
                "thickness": _quantity(snapshot.washer_geometry.thickness),
                "under_head": snapshot.washer_geometry.under_head,
                "under_nut": snapshot.washer_geometry.under_nut,
            }
        ),
        "source_notes": list(snapshot.source_notes),
    }


def _payload(request: SingleBoltOrchestrationRequest) -> dict[str, object]:
    context = request.geometry_context
    unit_system = request.assembly.unit_system
    length_unit = Unit.IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
    force_unit = Unit.KIP if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = Unit.KIP_IN if unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    member_dtos: list[dict[str, object]] = []
    placement_dtos: list[dict[str, object]] = []
    for member, placed in zip(
        request.assembly.members,
        context.basis.placed_members,
        strict=True,
    ):
        orientation = member.material_orientation
        region_orientation = (
            None
            if member.section_topology is None
            else member.section_topology.material_regions[0].orientation
        )
        member_dtos.append(
            {
                "id": member.id,
                "label": member.label,
                "role": member.role.value,
                "connected_end": member.connected_end.value,
                "material_kind": member.material_kind.value,
                "material_orientation": (
                    None
                    if orientation is None
                    else {
                        "lengthwise_axis": orientation.lengthwise_axis.value,
                        "crosswise_axis": cast(
                            PlanarFixedMaterialOrientation, region_orientation
                        ).crosswise_axis.value,
                        "through_thickness_axis": cast(
                            PlanarFixedMaterialOrientation, region_orientation
                        ).through_thickness_axis.value,
                    }
                ),
                "section": _section(placed.cross_section, length_unit),
            }
        )
        end = placed.global_frame.local_to_parent_point(
            PositionVector3D(placed.extent.x_end, 0.0, 0.0)
        )
        placement_dtos.append(
            {
                "member_id": member.id,
                "start": _point(placed.global_frame.origin, length_unit),
                "end": _point(end, length_unit),
                "local_z_reference": _direction(placed.global_frame.z_axis),
                "section_offset_y": _scalar(placed.section_offset.offset_y, length_unit),
                "section_offset_z": _scalar(placed.section_offset.offset_z, length_unit),
            }
        )

    resolved_interface = context.basis.resolved_interfaces[0]
    first_zone = resolved_interface.first_side.primary_zone
    second_zone = resolved_interface.second_side.primary_zone
    first_geometry = cast(PlanarRectangularSurface3D, first_zone.surface.geometry)
    origin_local = first_geometry.frame.parent_to_local_point(resolved_interface.interface_origin)
    resolved_group = context.resolved_bolt_groups[0]
    specification = resolved_group.specification
    resolved_layers = {
        item.definition.id: item for path in resolved_group.paths for item in path.layers
    }
    action_dtos = []
    for action in request.assembly.member_end_actions:
        reference = action.reference_point
        action_dtos.append(
            {
                "id": action.id,
                "member_id": action.member_id,
                "member_end": action.member_end.value,
                "load_combination_id": action.load_combination_id,
                "coordinate_frame_kind": action.coordinate_frame.kind.value,
                "coordinate_frame_owner_id": action.coordinate_frame.owner_id,
                "reference_point": {
                    "kind": reference.kind.value,
                    "owner_id": reference.owner_id,
                    "position": (
                        _point(cast(PositionVector3D, reference.position), length_unit)
                        if reference.kind is ReferencePointKind.EXPLICIT_POINT
                        else None
                    ),
                },
                "force": {
                    "x": _decimal(action.force.fx),
                    "y": _decimal(action.force.fy),
                    "z": _decimal(action.force.fz),
                    "unit": force_unit.value,
                },
                "moment": {
                    "x": _decimal(action.moment.mx),
                    "y": _decimal(action.moment.my),
                    "z": _decimal(action.moment.mz),
                    "unit": moment_unit.value,
                },
                "convention": action.convention.value,
            }
        )
    material_by_id = {
        assignment.material_snapshot.id: assignment.material_snapshot
        for assignment in request.material_assignments
    }
    demand_dto = None
    if request.resolved_demand is not None:
        assignment = request.resolved_demand
        demand = assignment.demand
        demand_dto = {
            "interface_id": assignment.interface_id,
            "bolt_group_id": assignment.bolt_group_id,
            "bolt_location_id": assignment.bolt_location_id,
            "id": demand.id,
            "load_combination_id": demand.load_combination_id,
            "source_member_id": demand.source_member_id,
            "source_action_id": demand.source_action_id,
            "source_kind": demand.source_kind.value,
            "factored_action_confirmed": demand.factored_action_confirmed,
            "coordinate_frame_reference": demand.coordinate_frame_reference,
            "resolved_frame": _frame(demand.resolved_frame, length_unit),
            "source_reference_point_id": demand.source_reference_point_id,
            "resolved_global_reference_point": _point(
                demand.resolved_global_reference_point, length_unit
            ),
            "in_plane_force_vector": {
                "x": _decimal(demand.in_plane_force_vector.x),
                "y": _decimal(demand.in_plane_force_vector.y),
                "z": _decimal(demand.in_plane_force_vector.z),
                "unit": demand.force_vector_unit.value,
            },
            "bolt_axis_tensile_demand": _quantity(demand.bolt_axis_tensile_demand),
            "externally_supplied_prying_demand": _quantity(
                demand.externally_supplied_prying_demand
            ),
            "loading_sense": demand.loading_sense.value,
            "provenance": list(demand.provenance),
            "distribution_status": demand.distribution_status.value,
        }
    return {
        "calculation_id": request.calculation_id,
        "joint_assembly": {
            "id": request.assembly.id,
            "label": request.assembly.label,
            "design_category": request.assembly.design_category.value,
            "unit_system": unit_system.value,
            "members": member_dtos,
            "load_combinations": [
                {"id": item.id, "label": item.label, "input_basis": item.input_basis.value}
                for item in request.assembly.load_combinations
            ],
            "member_end_actions": action_dtos,
        },
        "geometry": {
            "joint_frame": _frame(context.basis.joint_frame, length_unit),
            "member_placements": placement_dtos,
            "interface": {
                "id": resolved_interface.interface.id,
                "label": resolved_interface.interface.label,
                "participant_a_id": resolved_interface.first_participant.entity_id,
                "participant_b_id": resolved_interface.second_participant.entity_id,
                "transfer_intent": resolved_interface.interface.transfer_intent.value,
                "first_side": {
                    "participant_id": resolved_interface.first_participant.entity_id,
                    "physical_element_id": first_zone.surface.source.physical_element_id,
                    "patch_id": first_zone.surface.id,
                    "face_role": first_zone.surface.role.value,
                    "zone_id": first_zone.id,
                    "zone_label": first_zone.specification.label,
                },
                "second_side": {
                    "participant_id": resolved_interface.second_participant.entity_id,
                    "physical_element_id": second_zone.surface.source.physical_element_id,
                    "patch_id": second_zone.surface.id,
                    "face_role": second_zone.surface.role.value,
                    "zone_id": second_zone.id,
                    "zone_label": second_zone.specification.label,
                },
                "origin_local_y": _scalar(origin_local.y, length_unit),
                "origin_local_z": _scalar(origin_local.z, length_unit),
                "in_plane_reference": _direction(resolved_interface.interface_frame.y_axis),
                "distance_tolerance": _scalar(
                    resolved_interface.tolerance.distance_tolerance, length_unit
                ),
                "angular_tolerance": _decimal(resolved_interface.tolerance.angular_tolerance),
            },
            "bolt_group": {
                "id": specification.bolt_group.id,
                "label": specification.bolt_group.label,
                "primary_interface_id": specification.primary_interface_id,
                "origin_y": _scalar(specification.origin_y, length_unit),
                "origin_z": _scalar(specification.origin_z, length_unit),
                "in_plane_reference": _direction(resolved_group.bolt_group_frame.y_axis),
                "locations": [
                    {"id": item.id, "local_position": _point(item.position, length_unit)}
                    for item in specification.bolt_group.locations
                ],
                "paths": [
                    {
                        "bolt_location_id": path.bolt_location_id,
                        "layers": [
                            {
                                "id": layer.id,
                                "participant_id": layer.participant.entity_id,
                                "physical_element_id": layer.physical_element_id,
                                "entry_patch_id": layer.entry_surface.patch_id,
                                "exit_patch_id": layer.exit_surface.patch_id,
                                "entry_face_role": (
                                    resolved_layers[layer.id].entry.surface.role.value
                                ),
                                "exit_face_role": (
                                    resolved_layers[layer.id].exit.surface.role.value
                                ),
                                "interface_side": layer.connection_zones[0].side.value,
                                "zone_id": layer.connection_zones[0].zone_id,
                                "hole_diameter": _scalar(layer.hole_diameter, length_unit),
                            }
                            for layer in path.layers
                        ],
                    }
                    for path in specification.paths
                ],
            },
        },
        "interface_id": request.interface_id,
        "bolt_group_id": request.bolt_group_id,
        "bolt_location_id": request.bolt_location_id,
        "load_combination_id": request.load_combination_id,
        "source_action_id": request.source_action_id,
        "explicit_resolved_demand": demand_dto,
        "material_snapshots": [_material(item) for item in material_by_id.values()],
        "material_assignments": [
            {
                "participant_id": item.participant_id,
                "physical_element_id": item.physical_element_id,
                "material_region_id": item.material_region_id,
                "material_snapshot_id": item.material_snapshot.id,
                "bearing_thread_status": item.bearing_thread_status.value,
                "element_form": item.element_form.value,
                "potential_perpendicular_element_exemption": (
                    item.potential_perpendicular_element_exemption
                ),
            }
            for item in request.material_assignments
        ],
        "fastener_snapshot": _fastener(request.fastener_snapshot),
        "bolt_diameter": _quantity(request.bolt_diameter),
        "published_code_unit_basis": request.published_code_unit_basis.value,
        "time_effect_category": request.time_effect.category.value,
        "end_use_factors": {
            "cm": canonical_decimal_string(request.end_use_factors.cm),
            "ct": canonical_decimal_string(request.end_use_factors.ct),
            "cch": canonical_decimal_string(request.end_use_factors.cch),
            "source_reference": request.end_use_factors.source_reference,
            "approval_metadata": list(request.end_use_factors.approval_metadata),
        },
        "lap_configuration": request.lap_configuration.value,
        "whole_connection_requires_section_2_3_2": (
            request.whole_connection_requires_section_2_3_2
        ),
    }


def build_api_payload(
    fixture_id: str,
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
) -> dict[str, object]:
    """Build one strict declarative payload without bypassing the production mapper."""

    if fixture_id in {"J1-T", "J1-C"}:
        case = build_j1_case(
            compression=fixture_id == "J1-C",
            unit_system=unit_system,
            explicit_demand=explicit_demand,
        )
    else:
        case = build_plate_case(
            fixture_id,
            unit_system=unit_system,
            explicit_demand=explicit_demand,
        )
    return _payload(case.request)


def build_j1_visual_api_payload(
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
) -> dict[str, object]:
    """Build the properly rotated Stage 2.3R J1 request without replacing RC2 J1."""

    return _payload(
        build_j1_visual_case(
            unit_system=unit_system,
            explicit_demand=explicit_demand,
        ).request
    )


def build_j1_template_api_payload(
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
    angle_degrees: str = "45",
    bolt_to_brace_end_distance: str | None = None,
    column_flange_connection_side: str = "EXTERIOR",
    angle_connected_leg: str = "LEG_1",
    outstanding_leg_side: str = "POSITIVE_INTERFACE_Z",
) -> dict[str, object]:
    """Build the strict backend-owned Stage 2.3R2 J1 template request."""

    payload = build_j1_visual_api_payload(
        unit_system=unit_system,
        explicit_demand=explicit_demand,
    )
    payload.pop("geometry")
    if unit_system is EngineeringUnitSystem.US_CUSTOMARY:
        unit = "in"
        default_end_distance = "2"
        hole_diameter = "0.563"
    else:
        unit = "mm"
        default_end_distance = "50.8"
        hole_diameter = "14.3002"
    payload["geometry_template"] = {
        "kind": "BRACE_TO_COLUMN_FLANGE",
        "brace_to_column_directed_angle_deg": angle_degrees,
        "bolt_to_brace_end_distance": {
            "value": bolt_to_brace_end_distance or default_end_distance,
            "unit": unit,
        },
        "hole_diameter": {"value": hole_diameter, "unit": unit},
        "column_flange_connection_side": column_flange_connection_side,
        "angle_connected_leg": angle_connected_leg,
        "outstanding_leg_side": outstanding_leg_side,
    }
    if angle_connected_leg == "LEG_2":
        assignment = cast(list[dict[str, object]], payload["material_assignments"])[0]
        assignment["physical_element_id"] = "LEG_2"
        assignment["material_region_id"] = "LEG_2"
    return payload


def build_j1_preview_api_payload(
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    explicit_demand: bool = True,
    angle_degrees: str = "45",
    bolt_to_brace_end_distance: str | None = None,
    column_view_extent_below: str | None = None,
    column_view_extent_above: str | None = None,
    brace_view_length: str | None = None,
    column_flange_connection_side: str = "EXTERIOR",
    angle_connected_leg: str = "LEG_1",
    outstanding_leg_side: str = "POSITIVE_INTERFACE_Z",
) -> dict[str, Any]:
    """Build the strict zero-resistance preview view of the J1 template request."""

    payload = cast(
        dict[str, Any],
        build_j1_template_api_payload(
            unit_system=unit_system,
            explicit_demand=explicit_demand,
            angle_degrees=angle_degrees,
            bolt_to_brace_end_distance=bolt_to_brace_end_distance,
            column_flange_connection_side=column_flange_connection_side,
            angle_connected_leg=angle_connected_leg,
            outstanding_leg_side=outstanding_leg_side,
        ),
    )
    if unit_system is EngineeringUnitSystem.US_CUSTOMARY:
        unit = "in"
        default_below = "8.7426406871192848"
        default_above = "1.5"
        default_brace_length = "4"
    else:
        unit = "mm"
        default_below = "222.06307345282983392"
        default_above = "38.1"
        default_brace_length = "101.6"
    payload["view_extents"] = {
        "brace_view_length": {
            "value": brace_view_length or default_brace_length,
            "unit": unit,
        },
        "column_view_extent_below": {
            "value": column_view_extent_below or default_below,
            "unit": unit,
        },
        "column_view_extent_above": {
            "value": column_view_extent_above or default_above,
            "unit": unit,
        },
    }
    for field in (
        "end_use_factors",
        "published_code_unit_basis",
        "time_effect_category",
        "whole_connection_requires_section_2_3_2",
    ):
        payload.pop(field)
    fastener = cast(dict[str, object], payload["fastener_snapshot"])
    payload["fastener_snapshot"] = {
        "id": fastener["id"],
        "washer_geometry": fastener["washer_geometry"],
    }
    return payload


__all__ = (
    "build_api_payload",
    "build_j1_preview_api_payload",
    "build_j1_template_api_payload",
    "build_j1_visual_api_payload",
)
