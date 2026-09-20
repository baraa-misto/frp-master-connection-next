"""Pure mapping from authoritative C3 bolt geometry to Chapter 8 variables."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import cast

from frp_master_connection.calculation.inputs import LayerLoadingSense
from frp_master_connection.calculation.properties import FastenerSnapshot, WasherGeometry
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    StandardHoleDefinition,
    Unit,
    decimal_from_finite_real,
)
from frp_master_connection.calculation.results import (
    CalculationReadinessStatus,
    MaterialDirectionFamily,
)
from frp_master_connection.calculation.sources import (
    TRANSVERSE_ENDPOINT_INTERPRETATION_ID,
)
from frp_master_connection.domain.section_topology import PlanarFixedMaterialOrientation
from frp_master_connection.domain.values import (
    EngineeringUnitSystem,
    PositionVector3D,
    PrincipalAxisFamily,
)
from frp_master_connection.geometry.bolt_paths import (
    ResolvedBoltGroupGeometry,
    ResolvedPenetratedLayer,
)
from frp_master_connection.geometry.section import AxisAlignedRectangle2D
from frp_master_connection.geometry.spatial import (
    DIMENSIONLESS_MATHEMATICAL_TOLERANCE,
    UnitVector3D,
    Vector3D,
)
from frp_master_connection.geometry.surfaces import PlanarRectangularSurface3D


class EffectiveWidthMappingStatus(StrEnum):
    """Whether the physical side distances match an approved printed case."""

    SUPPORTED = "SUPPORTED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"


class GeometryMappingIssue(StrEnum):
    """Controlled mapping observations retained without inventing geometry."""

    EXACT_90_TRANSVERSE_INTERPRETATION = "EXACT_90_TRANSVERSE_INTERPRETATION"
    UNEQUAL_UNCAPPED_SIDE_DISTANCES_NOT_SUPPORTED = "UNEQUAL_UNCAPPED_SIDE_DISTANCES_NOT_SUPPORTED"
    HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3 = "HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3"


@dataclass(frozen=True, slots=True)
class GeometryToCodeMappingRequest:
    """Explicit selection of one C3 bolt path/layer and signed layer force."""

    resolved_bolt_group: ResolvedBoltGroupGeometry
    bolt_location_id: str
    layer_id: str
    bolt_diameter: PhysicalQuantity
    signed_in_plane_force: Vector3D
    component_lengthwise_axis: PrincipalAxisFamily
    source_length_unit: Unit

    def __post_init__(self) -> None:
        if not isinstance(self.resolved_bolt_group, ResolvedBoltGroupGeometry):
            raise TypeError("resolved_bolt_group must be a ResolvedBoltGroupGeometry.")
        if not self.bolt_location_id.strip() or not self.layer_id.strip():
            raise ValueError("Bolt-location and layer identities must be nonempty.")
        if (
            self.bolt_diameter.dimension is not Dimension.LENGTH
            or self.bolt_diameter.magnitude <= 0
        ):
            raise ValueError("Bolt diameter must be a positive length.")
        if not isinstance(self.signed_in_plane_force, Vector3D):
            raise TypeError("signed_in_plane_force must be a Vector3D.")
        if self.signed_in_plane_force.norm <= 0:
            raise ValueError("Geometry mapping requires a nonzero in-plane force.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be IN or MM.")
        expected_system = (
            EngineeringUnitSystem.US_CUSTOMARY
            if self.source_length_unit is Unit.IN
            else EngineeringUnitSystem.SI
        )
        if self.resolved_bolt_group.unit_system is not expected_system:
            raise ValueError("Source length unit must match the authoritative C3 unit system.")


@dataclass(frozen=True, slots=True)
class GeometryToCodeMapping:
    """Immutable raw geometry and supported effective-width mapping for one layer."""

    participant_id: str
    component_id: str
    physical_element_id: str
    material_region_id: str
    bolt_location_id: str
    source_surface_patch_ids: tuple[str, str]
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    layer_thickness: PhysicalQuantity
    signed_in_plane_force_direction: tuple[Decimal, Decimal, Decimal]
    theta_degrees: Decimal
    direction_family: MaterialDirectionFamily
    direction_interpretation_id: str | None
    loaded_end_forward_intersection: PositionVector3D
    forward_e1: PhysicalQuantity
    reverse_end_intersection: PositionVector3D
    reverse_end_distance: PhysicalQuantity
    raw_side_distance_1: PhysicalQuantity
    raw_side_distance_2: PhysicalQuantity
    e2_min: PhysicalQuantity
    effective_e3: PhysicalQuantity | None
    effective_e4: PhysicalQuantity | None
    effective_width: PhysicalQuantity | None
    effective_width_status: EffectiveWidthMappingStatus
    hole_containment_provenance: tuple[str, ...]
    source_unit_identity: Unit
    issues: tuple[GeometryMappingIssue, ...]


def _find_layer(
    group: ResolvedBoltGroupGeometry,
    bolt_location_id: str,
    layer_id: str,
) -> ResolvedPenetratedLayer:
    paths = [path for path in group.paths if path.definition.bolt_location_id == bolt_location_id]
    if len(paths) != 1:
        raise KeyError(f"Expected one resolved path for bolt location {bolt_location_id!r}.")
    layers = [layer for layer in paths[0].layers if layer.definition.id == layer_id]
    if len(layers) != 1:
        raise KeyError(f"Expected one resolved penetrated layer {layer_id!r}.")
    return layers[0]


def _axis_vector(
    family: PrincipalAxisFamily,
    layer: ResolvedPenetratedLayer,
) -> UnitVector3D:
    frame = layer.physical_element.global_frame
    return {
        PrincipalAxisFamily.X: frame.x_axis,
        PrincipalAxisFamily.Y: frame.y_axis,
        PrincipalAxisFamily.Z: frame.z_axis,
    }[family]


def _ray_to_rectangle(
    origin_y: float,
    origin_z: float,
    direction_y: float,
    direction_z: float,
    half_y: float,
    half_z: float,
) -> float:
    distances: list[float] = []
    if direction_y > 0:
        distances.append((half_y - origin_y) / direction_y)
    elif direction_y < 0:
        distances.append((-half_y - origin_y) / direction_y)
    if direction_z > 0:
        distances.append((half_z - origin_z) / direction_z)
    elif direction_z < 0:
        distances.append((-half_z - origin_z) / direction_z)
    positive = [distance for distance in distances if distance >= 0]
    if not positive:
        raise ValueError("Ray from bolt center does not intersect the physical rectangle boundary.")
    return min(positive)


def _point_along(
    origin: PositionVector3D,
    direction: UnitVector3D,
    distance: float,
) -> PositionVector3D:
    return PositionVector3D(
        origin.x + direction.x * distance,
        origin.y + direction.y * distance,
        origin.z + direction.z * distance,
    )


def _length_quantity(value: float, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.from_finite_real(value, unit)


def resolve_geometry_to_code_mapping(
    request: GeometryToCodeMappingRequest,
) -> GeometryToCodeMapping:
    """Resolve raw physical boundaries and directional selection without strength math."""

    layer = _find_layer(
        request.resolved_bolt_group,
        request.bolt_location_id,
        request.layer_id,
    )
    if len(layer.physical_element.source_geometry.geometry) != 1 or not isinstance(
        layer.physical_element.source_geometry.geometry[0], AxisAlignedRectangle2D
    ):
        raise ValueError("Initial code mapping supports one flat rectangular physical element.")
    if not isinstance(
        layer.physical_element.source_material_region.orientation, PlanarFixedMaterialOrientation
    ):
        raise ValueError("Initial code mapping requires a planar fixed material region.")
    entry_geometry = layer.entry.surface.geometry
    if not isinstance(entry_geometry, PlanarRectangularSurface3D):
        raise ValueError("Initial code mapping requires a regular planar rectangular broad face.")

    force_direction = request.signed_in_plane_force.normalized()
    force_normal_ratio = abs(force_direction.dot(entry_geometry.normal))
    if force_normal_ratio > request.resolved_bolt_group.tolerance.angular_tolerance:
        raise ValueError("The signed checked-layer force must lie in the physical element plane.")

    local_force = entry_geometry.frame.parent_to_local_vector(force_direction)
    local_center = entry_geometry.frame.parent_to_local_point(layer.entry.point)
    forward_distance = _ray_to_rectangle(
        local_center.y,
        local_center.z,
        local_force.y,
        local_force.z,
        entry_geometry.extent_y / 2,
        entry_geometry.extent_z / 2,
    )
    reverse_distance = _ray_to_rectangle(
        local_center.y,
        local_center.z,
        -local_force.y,
        -local_force.z,
        entry_geometry.extent_y / 2,
        entry_geometry.extent_z / 2,
    )
    side_direction_y = -local_force.z
    side_direction_z = local_force.y
    side_1 = _ray_to_rectangle(
        local_center.y,
        local_center.z,
        side_direction_y,
        side_direction_z,
        entry_geometry.extent_y / 2,
        entry_geometry.extent_z / 2,
    )
    side_2 = _ray_to_rectangle(
        local_center.y,
        local_center.z,
        -side_direction_y,
        -side_direction_z,
        entry_geometry.extent_y / 2,
        entry_geometry.extent_z / 2,
    )

    lengthwise = _axis_vector(request.component_lengthwise_axis, layer)
    cosine = abs(force_direction.dot(lengthwise))
    cosine = max(0.0, min(1.0, cosine))
    theta_float = math.degrees(math.acos(cosine))
    interpretation_id: str | None = None
    issues = [GeometryMappingIssue.HOLE_CONTAINMENT_REUSED_FROM_STAGE_1_3C3]
    if cosine <= DIMENSIONLESS_MATHEMATICAL_TOLERANCE:
        theta = Decimal("90")
        direction_family = MaterialDirectionFamily.TRANSVERSE
        interpretation_id = TRANSVERSE_ENDPOINT_INTERPRETATION_ID
        issues.append(GeometryMappingIssue.EXACT_90_TRANSVERSE_INTERPRETATION)
    else:
        theta = decimal_from_finite_real(theta_float)
        direction_family = (
            MaterialDirectionFamily.LONGITUDINAL
            if theta_float <= 5.0 + DIMENSIONLESS_MATHEMATICAL_TOLERANCE
            else MaterialDirectionFamily.TRANSVERSE
        )

    diameter = _length_quantity(layer.definition.hole_diameter, request.source_length_unit)
    thickness = _length_quantity(layer.raw_thickness, request.source_length_unit)
    e2_min = request.bolt_diameter * Decimal("1.5")
    cap = e2_min * Decimal(2)
    raw_1 = _length_quantity(side_1, request.source_length_unit)
    raw_2 = _length_quantity(side_2, request.source_length_unit)
    distance_tolerance = _length_quantity(
        request.resolved_bolt_group.tolerance.distance_tolerance,
        request.source_length_unit,
    )
    equal = abs(
        raw_1.to(request.source_length_unit).magnitude
        - raw_2.to(request.source_length_unit).magnitude
    ) <= (distance_tolerance.magnitude)
    if equal:
        effective_3, effective_4 = raw_1, raw_2
        width_status = EffectiveWidthMappingStatus.SUPPORTED
    elif (raw_1 <= cap < raw_2) or (raw_2 <= cap < raw_1):
        effective_3 = raw_1 if raw_1 <= cap else cap
        effective_4 = raw_2 if raw_2 <= cap else cap
        width_status = EffectiveWidthMappingStatus.SUPPORTED
    elif raw_1 > cap and raw_2 > cap:
        effective_3 = cap.to(request.source_length_unit)
        effective_4 = cap.to(request.source_length_unit)
        width_status = EffectiveWidthMappingStatus.SUPPORTED
    else:
        effective_3 = None
        effective_4 = None
        width_status = EffectiveWidthMappingStatus.CALCULATION_NOT_SUPPORTED
        issues.append(GeometryMappingIssue.UNEQUAL_UNCAPPED_SIDE_DISTANCES_NOT_SUPPORTED)
    effective_width = (
        effective_3 + cast(PhysicalQuantity, effective_4) if effective_3 is not None else None
    )

    provenance = (
        f"entry_patch:{layer.entry.surface.reference.patch_id}",
        f"exit_patch:{layer.exit.surface.reference.patch_id}",
        f"entry_raw_clearance:{layer.entry.raw_patch_clearance}",
        f"exit_raw_clearance:{layer.exit.raw_patch_clearance}",
        *(f"zone:{zone.id}" for zone in layer.zones),
        *(f"zone_raw_clearance:{value}" for value in layer.raw_zone_clearances),
    )
    return GeometryToCodeMapping(
        participant_id=layer.definition.participant.entity_id,
        component_id=layer.definition.participant.entity_id,
        physical_element_id=layer.definition.physical_element_id,
        material_region_id=layer.physical_element.source_material_region.id,
        bolt_location_id=request.bolt_location_id,
        source_surface_patch_ids=(
            layer.entry.surface.reference.patch_id,
            layer.exit.surface.reference.patch_id,
        ),
        bolt_diameter=request.bolt_diameter,
        hole_diameter=diameter,
        layer_thickness=thickness,
        signed_in_plane_force_direction=(
            decimal_from_finite_real(force_direction.x),
            decimal_from_finite_real(force_direction.y),
            decimal_from_finite_real(force_direction.z),
        ),
        theta_degrees=theta,
        direction_family=direction_family,
        direction_interpretation_id=interpretation_id,
        loaded_end_forward_intersection=_point_along(
            layer.entry.point, force_direction, forward_distance
        ),
        forward_e1=_length_quantity(forward_distance, request.source_length_unit),
        reverse_end_intersection=_point_along(
            layer.entry.point, -force_direction, reverse_distance
        ),
        reverse_end_distance=_length_quantity(reverse_distance, request.source_length_unit),
        raw_side_distance_1=raw_1,
        raw_side_distance_2=raw_2,
        e2_min=e2_min,
        effective_e3=effective_3,
        effective_e4=effective_4,
        effective_width=effective_width,
        effective_width_status=width_status,
        hole_containment_provenance=provenance,
        source_unit_identity=request.source_length_unit,
        issues=tuple(issues),
    )


class CodeGeometryIssue(StrEnum):
    """Chapter 8 geometry/hardware readiness observations."""

    BOLT_DIAMETER_OUTSIDE_CHAPTER_8_RANGE = "BOLT_DIAMETER_OUTSIDE_CHAPTER_8_RANGE"
    FASTENER_METADATA_MISSING = "FASTENER_METADATA_MISSING"
    STANDARD_ROUND_HOLE_REQUIRED = "STANDARD_ROUND_HOLE_REQUIRED"
    COMMON_PHYSICAL_HOLE_REQUIRED = "COMMON_PHYSICAL_HOLE_REQUIRED"
    FRP_THICKNESS_BELOW_MINIMUM = "FRP_THICKNESS_BELOW_MINIMUM"
    TENSION_END_DISTANCE_BELOW_4D = "TENSION_END_DISTANCE_BELOW_4D"
    COMPRESSION_END_DISTANCE_BELOW_2D = "COMPRESSION_END_DISTANCE_BELOW_2D"
    EDGE_DISTANCE_BELOW_1_5D = "EDGE_DISTANCE_BELOW_1_5D"
    WASHER_OUTSIDE_DIAMETER_BELOW_2D = "WASHER_OUTSIDE_DIAMETER_BELOW_2D"
    WASHER_THICKNESS_BELOW_0_051_IN = "WASHER_THICKNESS_BELOW_0_051_IN"
    WASHER_REQUIRED_UNDER_HEAD_AND_NUT = "WASHER_REQUIRED_UNDER_HEAD_AND_NUT"
    ARRANGEMENT_REQUIRES_SECTION_2_3_2 = "ARRANGEMENT_REQUIRES_SECTION_2_3_2"
    STAGE_2_1A_SUPPORTS_ONE_BOLT_ONE_ROW = "STAGE_2_1A_SUPPORTS_ONE_BOLT_ONE_ROW"


@dataclass(frozen=True, slots=True)
class CodeGeometryValidation:
    """Readiness result for code geometry; no design strength is evaluated."""

    status: CalculationReadinessStatus
    issues: tuple[CodeGeometryIssue, ...]


def validate_code_geometry(
    *,
    mapping: GeometryToCodeMapping,
    standard_hole: StandardHoleDefinition | None,
    fastener: FastenerSnapshot | None,
    washer: WasherGeometry | None,
    loading_sense: LayerLoadingSense,
    connection_hole_diameters: tuple[PhysicalQuantity, ...],
    logical_bolt_count: int,
    row_count: int,
) -> CodeGeometryValidation:
    """Validate first-slice Chapter 8 prerequisites without calculating resistance."""

    issues: list[CodeGeometryIssue] = []
    qualification = False
    unsupported = False
    diameter = mapping.bolt_diameter
    if diameter < PhysicalQuantity.of("0.375", Unit.IN) or diameter > PhysicalQuantity.of(
        "1.0", Unit.IN
    ):
        issues.append(CodeGeometryIssue.BOLT_DIAMETER_OUTSIDE_CHAPTER_8_RANGE)
        qualification = True
    if fastener is None or not fastener.bolt_specification.strip():
        issues.append(CodeGeometryIssue.FASTENER_METADATA_MISSING)
        qualification = True
    if standard_hole is None or standard_hole.hole_diameter != mapping.hole_diameter:
        issues.append(CodeGeometryIssue.STANDARD_ROUND_HOLE_REQUIRED)
        qualification = True
    if not connection_hole_diameters or any(
        hole != mapping.hole_diameter for hole in connection_hole_diameters
    ):
        issues.append(CodeGeometryIssue.COMMON_PHYSICAL_HOLE_REQUIRED)
        return CodeGeometryValidation(CalculationReadinessStatus.INVALID_GEOMETRY, tuple(issues))
    if mapping.layer_thickness < PhysicalQuantity.of("0.188", Unit.IN):
        issues.append(CodeGeometryIssue.FRP_THICKNESS_BELOW_MINIMUM)
        qualification = True
    end_limit = diameter * (
        Decimal(4) if loading_sense is LayerLoadingSense.TENSION else Decimal(2)
    )
    if mapping.forward_e1 < end_limit:
        issues.append(
            CodeGeometryIssue.TENSION_END_DISTANCE_BELOW_4D
            if loading_sense is LayerLoadingSense.TENSION
            else CodeGeometryIssue.COMPRESSION_END_DISTANCE_BELOW_2D
        )
        qualification = True
    edge_limit = diameter * Decimal("1.5")
    if mapping.raw_side_distance_1 < edge_limit or mapping.raw_side_distance_2 < edge_limit:
        issues.append(CodeGeometryIssue.EDGE_DISTANCE_BELOW_1_5D)
        qualification = True
    if washer is None:
        issues.append(CodeGeometryIssue.WASHER_REQUIRED_UNDER_HEAD_AND_NUT)
        qualification = True
    else:
        if washer.outside_diameter < diameter * Decimal(2):
            issues.append(CodeGeometryIssue.WASHER_OUTSIDE_DIAMETER_BELOW_2D)
            qualification = True
        if washer.thickness < PhysicalQuantity.of("0.051", Unit.IN):
            issues.append(CodeGeometryIssue.WASHER_THICKNESS_BELOW_0_051_IN)
            qualification = True
        if not washer.under_head or not washer.under_nut:
            issues.append(CodeGeometryIssue.WASHER_REQUIRED_UNDER_HEAD_AND_NUT)
            qualification = True
    if logical_bolt_count > 3 or row_count > 3:
        issues.append(CodeGeometryIssue.ARRANGEMENT_REQUIRES_SECTION_2_3_2)
        qualification = True
    elif logical_bolt_count != 1 or row_count != 1:
        issues.append(CodeGeometryIssue.STAGE_2_1A_SUPPORTS_ONE_BOLT_ONE_ROW)
        unsupported = True
    status = (
        CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
        if qualification
        else CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
        if unsupported
        else CalculationReadinessStatus.READY
    )
    return CodeGeometryValidation(status, tuple(issues))


__all__ = (
    "CodeGeometryIssue",
    "CodeGeometryValidation",
    "EffectiveWidthMappingStatus",
    "GeometryMappingIssue",
    "GeometryToCodeMapping",
    "GeometryToCodeMappingRequest",
    "resolve_geometry_to_code_mapping",
    "validate_code_geometry",
)
