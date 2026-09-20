"""Stage 2.4A block-shear path area planning without resistance execution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation.multirow import (
    DeferredExecutionStatus,
    MultiRowWarning,
    MultiRowWarningCode,
    PlanAvailability,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    StandardHoleDefinition,
    Unit,
    decimal_from_finite_real,
)
from frp_master_connection.geometry.multirow import (
    BlockPathSegmentKind,
    BlockShearCandidatePath,
    BlockShearPathResolution,
    MultiRowGeometry,
)


class NetAreaStatus(StrEnum):
    """Independent Section 2.10 disposition for one path-area component."""

    SATISFIES_MINIMUM_NET_AREA = "SATISFIES_MINIMUM_NET_AREA"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class BlockPathPlanStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class HoleDeductionPlane(StrEnum):
    SHEAR = "SHEAR"
    TENSION = "TENSION"


@dataclass(frozen=True, slots=True)
class BoltHoleSource:
    """Authoritative ordinary-hole definition assigned to one physical bolt."""

    bolt_id: str
    definition: StandardHoleDefinition

    def __post_init__(self) -> None:
        if not self.bolt_id.strip():
            raise ValueError("bolt_id must be nonempty.")
        if not isinstance(self.definition, StandardHoleDefinition):
            raise TypeError("definition must be StandardHoleDefinition.")


@dataclass(frozen=True, slots=True)
class HoleDeductionAllocation:
    bolt_id: str
    plane: HoleDeductionPlane
    fraction: Decimal
    physical_hole_diameter: PhysicalQuantity
    net_area_hole_diameter: PhysicalQuantity
    deduction: PhysicalQuantity
    source_basis: str


@dataclass(frozen=True, slots=True)
class BlockShearAreaPlan:
    """Raw L/U path lengths and areas; it intentionally has no resistance fields."""

    path_id: str
    path_status: BlockPathPlanStatus
    rejection_reasons: tuple[str, ...]
    gross_shear_length: PhysicalQuantity
    net_shear_length: PhysicalQuantity
    gross_tension_length: PhysicalQuantity
    net_tension_length: PhysicalQuantity
    thickness: PhysicalQuantity
    gross_shear_area: PhysicalQuantity
    net_shear_area: PhysicalQuantity
    gross_tension_area: PhysicalQuantity
    net_tension_area: PhysicalQuantity
    shear_net_to_gross: Decimal | None
    tension_net_to_gross: Decimal | None
    shear_net_area_status: NetAreaStatus
    tension_net_area_status: NetAreaStatus
    deductions: tuple[HoleDeductionAllocation, ...]
    availability: PlanAvailability
    warnings: tuple[MultiRowWarning, ...]
    minimum_selection_status: DeferredExecutionStatus
    execution_status: DeferredExecutionStatus


@dataclass(frozen=True, slots=True)
class BlockShearPlanSet:
    candidates: tuple[BlockShearAreaPlan, ...]
    minimum_selection_status: DeferredExecutionStatus


def _length(value: float | Decimal, unit: Unit) -> PhysicalQuantity:
    magnitude = value if isinstance(value, Decimal) else decimal_from_finite_real(value)
    return PhysicalQuantity(magnitude, unit)


def _area(length: PhysicalQuantity, thickness: PhysicalQuantity) -> PhysicalQuantity:
    source_unit = length.unit
    same_unit_thickness = thickness.to(source_unit)
    area_unit = Unit.IN2 if source_unit is Unit.IN else Unit.MM2
    with localcontext() as context:
        context.prec = 100
        magnitude = length.magnitude * same_unit_thickness.magnitude
    return PhysicalQuantity(magnitude, area_unit)


def _ratio(net: PhysicalQuantity, gross: PhysicalQuantity) -> Decimal | None:
    if gross.magnitude <= 0:
        return None
    with localcontext() as context:
        context.prec = 100
        return net.canonical_magnitude / gross.canonical_magnitude


def _net_area_status(
    net_area: PhysicalQuantity,
    ratio: Decimal | None,
) -> NetAreaStatus:
    if net_area.magnitude <= 0 or ratio is None:
        return NetAreaStatus.INVALID_GEOMETRY
    if ratio < Decimal("0.75"):
        return NetAreaStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    return NetAreaStatus.SATISFIES_MINIMUM_NET_AREA


def _deduction(
    source: BoltHoleSource,
    plane: HoleDeductionPlane,
    fraction: Decimal,
    source_length_unit: Unit,
) -> HoleDeductionAllocation:
    physical_hole = source.definition.hole_diameter.to(source_length_unit)
    net_hole = (source.definition.hole_diameter + source.definition.published_increment).to(
        source_length_unit
    )
    return HoleDeductionAllocation(
        source.bolt_id,
        plane,
        fraction,
        physical_hole,
        net_hole,
        net_hole * fraction,
        source.definition.published_source_basis.value,
    )


def _validate_hole_sources(
    geometry: MultiRowGeometry,
    sources: tuple[BoltHoleSource, ...],
    source_length_unit: Unit,
) -> dict[str, BoltHoleSource]:
    identities = tuple(item.bolt_id for item in sources)
    if len(set(identities)) != len(identities):
        raise ValueError("Bolt-hole source identities must be unique.")
    lookup = {item.bolt_id: item for item in sources}
    tolerance = Decimal(str(geometry.sorting_tolerance))
    for bolt in geometry.group.bolts:
        if bolt.id not in lookup:
            raise ValueError("Every physical bolt requires one ordinary-hole source.")
        physical = lookup[bolt.id].definition.hole_diameter.to(source_length_unit).magnitude
        if abs(physical - Decimal(str(bolt.hole_diameter))) > tolerance:
            raise ValueError("Hole source must match the unchanged physical hole geometry.")
    return lookup


def _build_candidate_area_plan(
    candidate: BlockShearCandidatePath,
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
    thickness: PhysicalQuantity,
    lookup: dict[str, BoltHoleSource],
) -> BlockShearAreaPlan:
    shear_length = sum(
        (
            _length(segment.length, source_length_unit)
            for segment in candidate.segments
            if segment.kind is BlockPathSegmentKind.SHEAR
        ),
        PhysicalQuantity.of(0, source_length_unit),
    )
    tension_length = sum(
        (
            _length(segment.length, source_length_unit)
            for segment in candidate.segments
            if segment.kind is BlockPathSegmentKind.TENSION
        ),
        PhysicalQuantity.of(0, source_length_unit),
    )
    deductions = (
        *(
            _deduction(lookup[bolt_id], HoleDeductionPlane.SHEAR, Decimal(1), source_length_unit)
            for bolt_id in candidate.shear_full_hole_ids
        ),
        *(
            _deduction(lookup[bolt_id], HoleDeductionPlane.TENSION, Decimal(1), source_length_unit)
            for bolt_id in candidate.tension_full_hole_ids
        ),
        *(
            _deduction(
                lookup[bolt_id], HoleDeductionPlane.SHEAR, Decimal("0.5"), source_length_unit
            )
            for bolt_id in candidate.shared_corner_hole_ids
        ),
        *(
            _deduction(
                lookup[bolt_id], HoleDeductionPlane.TENSION, Decimal("0.5"), source_length_unit
            )
            for bolt_id in candidate.shared_corner_hole_ids
        ),
    )
    physical_totals: dict[str, Decimal] = {}
    for item in deductions:
        physical_totals[item.bolt_id] = (
            physical_totals.get(item.bolt_id, Decimal(0)) + item.fraction
        )
    if any(value > Decimal(1) for value in physical_totals.values()):
        raise ValueError("A physical hole cannot exceed one total combined-path deduction.")
    shear_deduction = sum(
        (item.deduction for item in deductions if item.plane is HoleDeductionPlane.SHEAR),
        PhysicalQuantity.of(0, source_length_unit),
    )
    tension_deduction = sum(
        (item.deduction for item in deductions if item.plane is HoleDeductionPlane.TENSION),
        PhysicalQuantity.of(0, source_length_unit),
    )
    net_shear_length = shear_length - shear_deduction
    net_tension_length = tension_length - tension_deduction
    gross_shear_area = _area(shear_length, thickness)
    net_shear_area = _area(net_shear_length, thickness)
    gross_tension_area = _area(tension_length, thickness)
    net_tension_area = _area(net_tension_length, thickness)
    shear_ratio = _ratio(net_shear_area, gross_shear_area)
    tension_ratio = _ratio(net_tension_area, gross_tension_area)
    shear_status = _net_area_status(net_shear_area, shear_ratio)
    tension_status = _net_area_status(net_tension_area, tension_ratio)
    path_status = (
        BlockPathPlanStatus.ACCEPTED if candidate.accepted else BlockPathPlanStatus.REJECTED
    )
    if NetAreaStatus.INVALID_GEOMETRY in {shear_status, tension_status}:
        availability = PlanAvailability.CALCULATION_NOT_SUPPORTED
    elif NetAreaStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED in {
        shear_status,
        tension_status,
    }:
        availability = PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    elif path_status is BlockPathPlanStatus.REJECTED:
        availability = PlanAvailability.NOT_APPLICABLE
    else:
        availability = PlanAvailability.READY
    warnings: list[MultiRowWarning] = []
    if candidate.shared_corner_hole_ids:
        warnings.append(
            MultiRowWarning(
                MultiRowWarningCode.RATIONAL_HALF_HOLE_CORNER_ACCOUNTING,
                "Shared corner holes use one half deduction in each perpendicular plane.",
                tuple(f"shared_corner:{item}" for item in candidate.shared_corner_hole_ids),
            )
        )
    if availability is PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED:
        warnings.append(
            MultiRowWarning(
                MultiRowWarningCode.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
                "A raw net-to-gross area ratio is below 0.75; no area floor was applied.",
                (
                    f"shear_ratio:{shear_ratio}",
                    f"tension_ratio:{tension_ratio}",
                ),
            )
        )
    return BlockShearAreaPlan(
        candidate.id,
        path_status,
        tuple(reason.value for reason in candidate.rejection_reasons),
        shear_length,
        net_shear_length,
        tension_length,
        net_tension_length,
        thickness,
        gross_shear_area,
        net_shear_area,
        gross_tension_area,
        net_tension_area,
        shear_ratio,
        tension_ratio,
        shear_status,
        tension_status,
        deductions,
        availability,
        tuple(warnings),
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )


def build_block_shear_area_plans(
    resolution: BlockShearPathResolution,
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
    thickness: PhysicalQuantity,
    hole_sources: tuple[BoltHoleSource, ...],
) -> BlockShearPlanSet:
    """Plan raw areas for all retained candidates without selecting resistance."""

    if not isinstance(resolution, BlockShearPathResolution):
        raise TypeError("resolution must be BlockShearPathResolution.")
    if source_length_unit not in {Unit.IN, Unit.MM}:
        raise ValueError("source_length_unit must be IN or MM.")
    if thickness.dimension is not Dimension.LENGTH or thickness.magnitude <= 0:
        raise ValueError("thickness must be a positive length.")
    lookup = _validate_hole_sources(geometry, hole_sources, source_length_unit)
    candidates = tuple(
        _build_candidate_area_plan(candidate, geometry, source_length_unit, thickness, lookup)
        for candidate in resolution.candidates
    )
    return BlockShearPlanSet(candidates, DeferredExecutionStatus.DEFERRED_STAGE_2_4B)


__all__ = (
    "BlockPathPlanStatus",
    "BlockShearAreaPlan",
    "BlockShearPlanSet",
    "BoltHoleSource",
    "HoleDeductionAllocation",
    "HoleDeductionPlane",
    "NetAreaStatus",
    "build_block_shear_area_plans",
)
