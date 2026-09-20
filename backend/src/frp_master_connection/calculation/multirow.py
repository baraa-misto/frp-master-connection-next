"""Immutable Stage 2.4A contracts and plans for general multi-row bolt groups."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_from_finite_real,
    decimal_value,
)
from frp_master_connection.geometry.multirow import BoltRow, MultiRowGeometry


class RowDistributionBasis(StrEnum):
    """Approved source for allocating total in-plane demand to physical rows."""

    ASCE_PRESCRIBED = "ASCE_PRESCRIBED"
    CONSERVATIVE_FULL_ROW_ENVELOPE = "CONSERVATIVE_FULL_ROW_ENVELOPE"
    ENGINEER_DEFINED_ROW_DISTRIBUTION = "ENGINEER_DEFINED_ROW_DISTRIBUTION"


class ConnectedMaterialPair(StrEnum):
    """Connected-material identity used by prescribed row fractions."""

    FRP_FRP = "FRP_FRP"
    FRP_STEEL = "FRP_STEEL"


class PlanAvailability(StrEnum):
    """Whether a Stage 2.4A calculation-input plan can be formed."""

    READY = "READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    SOURCE_DATA_PENDING = "SOURCE_DATA_PENDING"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"


class GeometryStatus(StrEnum):
    VALID = "VALID"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class MultiRowMethodApplicability(StrEnum):
    ASCE_PRESCRIPTIVE = "ASCE_PRESCRIPTIVE"
    ASCE_COMMENTARY_METHOD = "ASCE_COMMENTARY_METHOD"
    CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE = "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE"
    ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE = (
        "ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE"
    )
    ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION = (
        "ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION"
    )


class QualificationDisposition(StrEnum):
    QUALIFIED_ASCE_PRESCRIPTIVE = "QUALIFIED_ASCE_PRESCRIPTIVE"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"


class MultiRowNumericalComparison(StrEnum):
    PASS = "PASS"  # noqa: S105 - engineering status, not a credential
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class MultiRowWarningCode(StrEnum):
    ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED = "ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED"
    CONSERVATIVE_FULL_ROW_ENVELOPE_USED = "CONSERVATIVE_FULL_ROW_ENVELOPE_USED"
    RATIONAL_EQ_8_13_EXTENSION_USED = "RATIONAL_EQ_8_13_EXTENSION_USED"
    ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION = (
        "ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION"
    )
    RATIONAL_HALF_HOLE_CORNER_ACCOUNTING = "RATIONAL_HALF_HOLE_CORNER_ACCOUNTING"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"


@dataclass(frozen=True, slots=True)
class MultiRowWarning:
    """Stable warning identity with safe trace metadata."""

    code: MultiRowWarningCode
    label: str
    trace: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, MultiRowWarningCode):
            raise TypeError("code must be MultiRowWarningCode.")
        if not self.label.strip():
            raise ValueError("A warning label must be nonempty.")


@dataclass(frozen=True, slots=True)
class MethodProvenance:
    """Traceable source for a selected distribution or rational method."""

    source_method: str
    source_document_or_calculation: str | None = None
    revision: str | None = None
    load_combination: str | None = None
    reference_point: str | None = None
    clearance_or_contact_modeled: bool | None = None
    engineer_confirmed: bool = False

    def __post_init__(self) -> None:
        if not self.source_method.strip():
            raise ValueError("source_method must be nonempty.")
        if not isinstance(self.engineer_confirmed, bool):
            raise TypeError("engineer_confirmed must be Boolean.")
        if self.clearance_or_contact_modeled is not None and not isinstance(
            self.clearance_or_contact_modeled, bool
        ):
            raise TypeError("clearance_or_contact_modeled must be Boolean or None.")

    @property
    def support_reference_trace(self) -> str:
        if self.source_document_or_calculation is None:
            return "OPTIONAL_SUPPORT_REFERENCE_NOT_SUPPLIED"
        return f"support_reference:{self.source_document_or_calculation}"


@dataclass(frozen=True, slots=True)
class EngineerRowFraction:
    row_id: str
    fraction: Decimal

    def __post_init__(self) -> None:
        if not self.row_id.strip():
            raise ValueError("row_id must be nonempty.")
        value = decimal_value(self.fraction)
        if value < 0:
            raise ValueError("An engineer-defined row fraction cannot be negative.")
        object.__setattr__(self, "fraction", value)


@dataclass(frozen=True, slots=True)
class EngineerRowForce:
    row_id: str
    force: PhysicalQuantity

    def __post_init__(self) -> None:
        if not self.row_id.strip():
            raise ValueError("row_id must be nonempty.")
        _require_force(self.force, "force")
        if self.force.magnitude < 0:
            raise ValueError("An engineer-defined row force cannot be negative.")


@dataclass(frozen=True, slots=True)
class PerBoltDemandPlan:
    bolt_id: str
    demand: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class RowDemandPlan:
    row_id: str
    row_demand: PhysicalQuantity
    row_fraction: Decimal | None
    per_bolt_demands: tuple[PerBoltDemandPlan, ...]


@dataclass(frozen=True, slots=True)
class RowDemandScenario:
    id: str
    controlling_row_id: str | None
    rows: tuple[RowDemandPlan, ...]


@dataclass(frozen=True, slots=True)
class MultiRowDemandPlan:
    basis: RowDistributionBasis
    total_in_plane_demand: PhysicalQuantity
    scenarios: tuple[RowDemandScenario, ...]
    availability: PlanAvailability
    provenance: MethodProvenance
    warnings: tuple[MultiRowWarning, ...]
    row_sharing_credit: bool = False
    friction_credit: bool = False


_PRESCRIBED_FRACTIONS: dict[tuple[ConnectedMaterialPair, int], tuple[Decimal, ...]] = {
    (ConnectedMaterialPair.FRP_FRP, 2): (Decimal("0.50"), Decimal("0.50")),
    (ConnectedMaterialPair.FRP_STEEL, 2): (Decimal("0.60"), Decimal("0.40")),
    (ConnectedMaterialPair.FRP_FRP, 3): (
        Decimal("0.40"),
        Decimal("0.20"),
        Decimal("0.40"),
    ),
    (ConnectedMaterialPair.FRP_STEEL, 3): (
        Decimal("0.50"),
        Decimal("0.30"),
        Decimal("0.20"),
    ),
}


def prescribed_row_fractions(
    material_pair: ConnectedMaterialPair,
    row_count: int,
) -> tuple[Decimal, ...]:
    """Return the exact immutable RC1 distribution when it exists."""

    if not isinstance(material_pair, ConnectedMaterialPair):
        raise TypeError("material_pair must be ConnectedMaterialPair.")
    if isinstance(row_count, bool) or not isinstance(row_count, int):
        raise TypeError("row_count must be a non-Boolean integer.")
    try:
        return _PRESCRIBED_FRACTIONS[(material_pair, row_count)]
    except KeyError as error:
        raise ValueError("No prescribed distribution exists for this row count.") from error


def _require_force(value: PhysicalQuantity, name: str) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.FORCE:
        raise ValueError(f"{name} must be a force quantity.")


def _per_bolt(row: BoltRow, force: PhysicalQuantity) -> tuple[PerBoltDemandPlan, ...]:
    bolts = row.bolts
    share = force / len(bolts)
    return tuple(PerBoltDemandPlan(item.bolt.id, share) for item in bolts)


def _allocated_rows(
    geometry: MultiRowGeometry,
    forces: tuple[PhysicalQuantity, ...],
    fractions: tuple[Decimal, ...] | None,
) -> tuple[RowDemandPlan, ...]:
    return tuple(
        RowDemandPlan(
            row.id,
            force,
            None if fractions is None else fractions[index],
            _per_bolt(row, force),
        )
        for index, (row, force) in enumerate(zip(geometry.rows, forces, strict=True))
    )


def _validate_row_coverage(
    geometry: MultiRowGeometry,
    identities: tuple[str, ...],
) -> None:
    if len(set(identities)) != len(identities):
        raise ValueError("Engineer-defined row identities must be unique.")
    expected = {row.id for row in geometry.rows}
    if set(identities) != expected:
        raise ValueError("Engineer-defined values must cover every physical row exactly once.")


def plan_row_demands(
    geometry: MultiRowGeometry,
    total_in_plane_demand: PhysicalQuantity,
    basis: RowDistributionBasis,
    provenance: MethodProvenance,
    *,
    connected_materials: ConnectedMaterialPair | None = None,
    engineer_fractions: tuple[EngineerRowFraction, ...] = (),
    engineer_forces: tuple[EngineerRowForce, ...] = (),
    fraction_tolerance: Decimal = Decimal("0.000000000001"),
    force_tolerance: PhysicalQuantity | None = None,
) -> MultiRowDemandPlan:
    """Create deterministic allocation scenarios without running a resistance equation."""

    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    _require_force(total_in_plane_demand, "total_in_plane_demand")
    if total_in_plane_demand.magnitude < 0:
        raise ValueError("total_in_plane_demand cannot be negative.")
    if not isinstance(basis, RowDistributionBasis):
        raise TypeError("basis must be RowDistributionBasis.")
    if not isinstance(provenance, MethodProvenance):
        raise TypeError("provenance must be MethodProvenance.")
    fraction_tolerance = decimal_value(fraction_tolerance)
    if fraction_tolerance <= 0:
        raise ValueError("fraction_tolerance must be positive.")
    if force_tolerance is None:
        force_tolerance = PhysicalQuantity.of("0.000001", Unit.N)
    _require_force(force_tolerance, "force_tolerance")
    if force_tolerance.magnitude < 0:
        raise ValueError("force_tolerance cannot be negative.")

    if basis is RowDistributionBasis.ASCE_PRESCRIBED:
        if engineer_fractions or engineer_forces:
            raise ValueError("Engineer-defined values cannot be mixed with a prescribed method.")
        if connected_materials is None:
            raise ValueError("connected_materials is required for a prescribed distribution.")
        prerequisites = geometry.classification.supports_uniform_rectangular_method and len(
            geometry.rows
        ) in {2, 3}
        if not prerequisites:
            return MultiRowDemandPlan(
                basis,
                total_in_plane_demand,
                (),
                PlanAvailability.CALCULATION_NOT_SUPPORTED,
                provenance,
                (),
            )
        fractions = prescribed_row_fractions(connected_materials, len(geometry.rows))
        forces: tuple[PhysicalQuantity, ...] = tuple(
            total_in_plane_demand * fraction for fraction in fractions
        )
        rows = _allocated_rows(geometry, forces, fractions)
        return MultiRowDemandPlan(
            basis,
            total_in_plane_demand,
            (RowDemandScenario("ASCE_PRESCRIBED", None, rows),),
            PlanAvailability.READY,
            provenance,
            (),
        )

    if connected_materials is not None:
        raise ValueError("connected_materials is only used by the prescribed method.")
    if basis is RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE:
        if engineer_fractions or engineer_forces:
            raise ValueError("Engineer-defined values cannot be mixed with the row envelope.")
        scenarios = tuple(
            RowDemandScenario(
                f"FULL_ROW_{row.id}",
                row.id,
                (
                    RowDemandPlan(
                        row.id,
                        total_in_plane_demand,
                        Decimal(1),
                        _per_bolt(row, total_in_plane_demand),
                    ),
                ),
            )
            for row in geometry.rows
        )
        warning = MultiRowWarning(
            MultiRowWarningCode.CONSERVATIVE_FULL_ROW_ENVELOPE_USED,
            "Every physical row is independently assigned the full in-plane demand.",
            ("row_sharing_credit:false", "friction_credit:false"),
        )
        return MultiRowDemandPlan(
            basis,
            total_in_plane_demand,
            scenarios,
            PlanAvailability.READY,
            provenance,
            (warning,),
        )

    if bool(engineer_fractions) == bool(engineer_forces):
        raise ValueError("Supply exactly one engineer-defined allocation representation.")
    if engineer_fractions:
        identities = tuple(item.row_id for item in engineer_fractions)
        _validate_row_coverage(geometry, identities)
        lookup = {item.row_id: item.fraction for item in engineer_fractions}
        fractions = tuple(lookup[row.id] for row in geometry.rows)
        if abs(sum(fractions, Decimal(0)) - Decimal(1)) > fraction_tolerance:
            raise ValueError("Engineer-defined row fractions do not balance to one.")
        forces = tuple(total_in_plane_demand * fraction for fraction in fractions)
        resolved_fractions: tuple[Decimal, ...] | None = fractions
    else:
        identities = tuple(item.row_id for item in engineer_forces)
        _validate_row_coverage(geometry, identities)
        lookup_force = {item.row_id: item.force for item in engineer_forces}
        forces = tuple(lookup_force[row.id].to(total_in_plane_demand.unit) for row in geometry.rows)
        total_force = sum(
            forces,
            PhysicalQuantity.of(0, total_in_plane_demand.unit),
        )
        if abs(total_force.canonical_magnitude - total_in_plane_demand.canonical_magnitude) > (
            force_tolerance.canonical_magnitude
        ):
            raise ValueError("Engineer-defined row forces do not balance the total demand.")
        resolved_fractions = None
    rows = _allocated_rows(geometry, forces, resolved_fractions)
    scenario = RowDemandScenario("ENGINEER_DEFINED", None, rows)
    return MultiRowDemandPlan(
        basis,
        total_in_plane_demand,
        (scenario,),
        PlanAvailability.READY,
        provenance,
        (),
    )


class MaterialDirection(StrEnum):
    LONGITUDINAL = "LONGITUDINAL"
    TRANSVERSE = "TRANSVERSE"


class PultrudedElementClassification(StrEnum):
    SHAPE = "SHAPE"
    PLATE = "PLATE"


class EffectiveWidthStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CALCULATION_NOT_SUPPORTED = "CALCULATION_NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class FirstRowGeometryMapping:
    """Code inputs derived only from the canonical physical multi-row geometry."""

    row_id: str
    row_count: int
    bolts_per_row: int
    bolt_diameter: PhysicalQuantity
    e1: PhysicalQuantity
    raw_e3: PhysicalQuantity
    raw_e4: PhysicalQuantity
    e3_cap: PhysicalQuantity
    e4_cap: PhysicalQuantity
    effective_e3: PhysicalQuantity | None
    effective_e4: PhysicalQuantity | None
    gauge: PhysicalQuantity | None
    effective_width: PhysicalQuantity | None
    material_direction: MaterialDirection
    element_classification: PultrudedElementClassification
    width_status: EffectiveWidthStatus
    source_authority: str
    source_geometry_ids: tuple[str, ...]


def _length(value: float, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity(decimal_from_finite_real(value), unit)


def resolve_first_row_geometry(
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
    bolt_diameter: PhysicalQuantity,
    material_direction: MaterialDirection,
    element_classification: PultrudedElementClassification,
) -> FirstRowGeometryMapping:
    """Map Row 1, physical boundaries, side caps, gauge, and width without UI authority."""

    if not isinstance(geometry, MultiRowGeometry):
        raise TypeError("geometry must be MultiRowGeometry.")
    if source_length_unit not in {Unit.IN, Unit.MM}:
        raise ValueError("source_length_unit must be IN or MM.")
    if bolt_diameter.dimension is not Dimension.LENGTH or bolt_diameter.magnitude <= 0:
        raise ValueError("bolt_diameter must be a positive length.")
    if not isinstance(material_direction, MaterialDirection):
        raise TypeError("material_direction must be MaterialDirection.")
    if not isinstance(element_classification, PultrudedElementClassification):
        raise TypeError("element_classification must be PultrudedElementClassification.")

    row = geometry.rows[0]
    raw_e3 = _length(geometry.first_row_negative_side_distance, source_length_unit)
    raw_e4 = _length(geometry.first_row_positive_side_distance, source_length_unit)
    cap = (bolt_diameter * Decimal(3)).to(source_length_unit)
    tolerance = _length(geometry.sorting_tolerance, source_length_unit)
    equal = abs(raw_e3.magnitude - raw_e4.magnitude) <= tolerance.magnitude
    if equal:
        effective_e3, effective_e4 = raw_e3, raw_e4
    elif (raw_e3 <= cap < raw_e4) or (raw_e4 <= cap < raw_e3):
        effective_e3 = raw_e3 if raw_e3 <= cap else cap
        effective_e4 = raw_e4 if raw_e4 <= cap else cap
    elif raw_e3 > cap and raw_e4 > cap:
        effective_e3 = cap
        effective_e4 = cap
    else:
        effective_e3 = None
        effective_e4 = None

    bolts_per_row = len(row.bolts)
    gauge = None
    if bolts_per_row > 1 and geometry.classification.constant_gauge:
        gauge = _length(geometry.classification.gauges[0], source_length_unit)
    width_supported = (
        effective_e3 is not None
        and effective_e4 is not None
        and (bolts_per_row == 1 or gauge is not None)
        and bolts_per_row <= 3
    )
    effective_width = None
    if width_supported:
        # The predicate above establishes both operands; this explicit construction
        # keeps the branch-free mapping auditable.
        effective_width = effective_e3 + effective_e4  # type: ignore[operator]
        if gauge is not None:
            effective_width += gauge * (bolts_per_row - 1)
    return FirstRowGeometryMapping(
        row.id,
        len(geometry.rows),
        bolts_per_row,
        bolt_diameter.to(source_length_unit),
        _length(geometry.first_row_end_distance, source_length_unit),
        raw_e3,
        raw_e4,
        cap,
        cap,
        effective_e3,
        effective_e4,
        gauge,
        effective_width,
        material_direction,
        element_classification,
        EffectiveWidthStatus.SUPPORTED
        if width_supported
        else EffectiveWidthStatus.CALCULATION_NOT_SUPPORTED,
        "CANONICAL_PHYSICAL_GEOMETRY",
        (geometry.group.id, geometry.boundary.id, row.id),
    )


class FirstRowPlanMethod(StrEnum):
    ASCE_STANDARD_SIMPLIFIED = "ASCE_STANDARD_SIMPLIFIED"
    ASCE_COMMENTARY_FULL = "ASCE_COMMENTARY_FULL"
    RATIONAL_MULTIROW_LOWER_ENVELOPE = "RATIONAL_MULTIROW_LOWER_ENVELOPE"


class DeferredExecutionStatus(StrEnum):
    DEFERRED_STAGE_2_4B = "DEFERRED_STAGE_2_4B"


@dataclass(frozen=True, slots=True)
class CommentaryCoefficientInputPlan:
    """Raw inputs for A/B coefficient evaluation; arithmetic is intentionally absent."""

    a_term_id: str
    b_term_id: str
    coefficient_c_i: Decimal
    coefficient_c_op_i: Decimal
    width: PhysicalQuantity
    bolt_count: int
    bolt_diameter: PhysicalQuantity
    net_hole_diameter: PhysicalQuantity
    e1: PhysicalQuantity
    gauge: PhysicalQuantity | None
    execution_status: DeferredExecutionStatus
    source_locators: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnknownLbrEnvelopePlan:
    simplified_extension_plan_id: str
    full_envelope_plan_id: str
    lower_envelope_selection_contract: str
    endpoint_selection_contract: str
    execution_status: DeferredExecutionStatus


@dataclass(frozen=True, slots=True)
class FirstRowNetTensionPlan:
    id: str
    method: FirstRowPlanMethod
    direction: MaterialDirection
    equation_locator: str
    geometry: FirstRowGeometryMapping
    thickness: PhysicalQuantity
    tensile_strength: PhysicalQuantity
    net_hole_diameter: PhysicalQuantity
    phi: Decimal
    coefficient_inputs: CommentaryCoefficientInputPlan | None
    lbr: Decimal | None
    unknown_lbr_envelope: UnknownLbrEnvelopePlan | None
    availability: PlanAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    warnings: tuple[MultiRowWarning, ...]
    execution_status: DeferredExecutionStatus


def _first_row_coefficient(
    geometry: FirstRowGeometryMapping,
) -> tuple[Decimal, tuple[MultiRowWarning, ...], tuple[str, ...]]:
    direction = geometry.material_direction
    element = geometry.element_classification
    warning: tuple[MultiRowWarning, ...] = ()
    locators: tuple[str, ...] = ("ASCE/SEI 74-23 Appendix CA8.3.3",)
    if direction is MaterialDirection.LONGITUDINAL:
        value = (
            Decimal("0.50") if element is PultrudedElementClassification.SHAPE else Decimal("0.40")
        )
    else:
        value = Decimal("0.50")
        if element is PultrudedElementClassification.PLATE:
            locators = (
                "ASCE/SEI 74-23 Appendix CA8.3.3 printed coefficient table",
                "ASCE/SEI 74-23 Appendix CA8.3.3 commentary coefficient discussion",
            )
            warning = (
                MultiRowWarning(
                    MultiRowWarningCode.ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION,
                    "The controlled pultruded-plate transverse coefficient is 0.50.",
                    ("printed_conflict:0.40", "commentary_conflict:0.50", "adopted:0.50"),
                ),
            )
    return value, warning, locators


def build_first_row_net_tension_plans(
    geometry: FirstRowGeometryMapping,
    thickness: PhysicalQuantity,
    tensile_strength: PhysicalQuantity,
    net_hole_diameter: PhysicalQuantity,
    *,
    prescribed_lbr: Decimal | None = None,
) -> tuple[FirstRowNetTensionPlan, ...]:
    """Build simplified, commentary, and rational input plans without resistance output."""

    if not isinstance(geometry, FirstRowGeometryMapping):
        raise TypeError("geometry must be FirstRowGeometryMapping.")
    if thickness.dimension is not Dimension.LENGTH or thickness.magnitude <= 0:
        raise ValueError("thickness must be a positive length.")
    if tensile_strength.dimension is not Dimension.STRESS or tensile_strength.magnitude <= 0:
        raise ValueError("tensile_strength must be a positive stress.")
    if net_hole_diameter.dimension is not Dimension.LENGTH or net_hole_diameter.magnitude <= 0:
        raise ValueError("net_hole_diameter must be a positive length.")
    if prescribed_lbr is not None:
        prescribed_lbr = decimal_value(prescribed_lbr)
        if not Decimal(0) <= prescribed_lbr <= Decimal(1):
            raise ValueError("prescribed_lbr must be between zero and one.")

    supported = geometry.width_status is EffectiveWidthStatus.SUPPORTED
    prescriptive = geometry.row_count in {2, 3} and supported
    qualification = (
        QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
        if prescriptive
        else QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    base_availability = (
        PlanAvailability.READY if supported else PlanAvailability.CALCULATION_NOT_SUPPORTED
    )
    base_applicability = (
        MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
        if prescriptive
        else MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    )
    row_warning: tuple[MultiRowWarning, ...] = ()
    if geometry.row_count > 3:
        row_warning = (
            MultiRowWarning(
                MultiRowWarningCode.ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED,
                "The physical row count exceeds the prescriptive method scope.",
                (f"row_count:{geometry.row_count}",),
            ),
        )
    phi = (
        Decimal("0.50")
        if geometry.material_direction is MaterialDirection.LONGITUDINAL
        else Decimal("0.45")
    )
    simplified = FirstRowNetTensionPlan(
        "FIRST_ROW_SIMPLIFIED",
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        geometry.material_direction,
        "ASCE/SEI 74-23 Eq. 8-10 or 8-11",
        geometry,
        thickness,
        tensile_strength,
        net_hole_diameter,
        phi,
        None,
        None,
        None,
        base_availability,
        base_applicability,
        qualification,
        row_warning,
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )
    coefficient, conflict_warnings, locators = _first_row_coefficient(geometry)
    coefficient_inputs = None
    if geometry.effective_width is not None:
        coefficient_inputs = CommentaryCoefficientInputPlan(
            "A",
            "B",
            coefficient,
            Decimal("0.50"),
            geometry.effective_width,
            geometry.bolts_per_row,
            geometry.bolt_diameter,
            net_hole_diameter,
            geometry.e1,
            geometry.gauge,
            DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
            locators,
        )
    commentary = FirstRowNetTensionPlan(
        "FIRST_ROW_COMMENTARY_FULL",
        FirstRowPlanMethod.ASCE_COMMENTARY_FULL,
        geometry.material_direction,
        "ASCE/SEI 74-23 Appendix CA8.3.3",
        geometry,
        thickness,
        tensile_strength,
        net_hole_diameter,
        phi,
        coefficient_inputs,
        prescribed_lbr,
        None,
        base_availability,
        MultiRowMethodApplicability.ASCE_COMMENTARY_METHOD if prescriptive else base_applicability,
        qualification,
        (*row_warning, *conflict_warnings),
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )
    rational_availability = (
        PlanAvailability.READY
        if geometry.row_count > 3 and supported
        else PlanAvailability.NOT_APPLICABLE
    )
    envelope = UnknownLbrEnvelopePlan(
        simplified.id,
        commentary.id,
        "Select the lower future resistance after both plans are executed.",
        "Select LBR_0 or LBR_1 from the larger future A/B denominator.",
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )
    rational = FirstRowNetTensionPlan(
        "FIRST_ROW_RATIONAL_LOWER_ENVELOPE",
        FirstRowPlanMethod.RATIONAL_MULTIROW_LOWER_ENVELOPE,
        geometry.material_direction,
        "Approved RC1 rational extension of Eq. 8-10/8-11 and Appendix CA8.3.3",
        geometry,
        thickness,
        tensile_strength,
        net_hole_diameter,
        phi,
        coefficient_inputs,
        None,
        envelope,
        rational_availability,
        MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
        QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        row_warning,
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )
    return simplified, commentary, rational


class InterrowShearOutMethod(StrEnum):
    ASCE_EQ_8_12 = "ASCE_EQ_8_12"
    ASCE_EQ_8_13 = "ASCE_EQ_8_13"
    RATIONAL_EXTENSION_EQ_8_13 = "RATIONAL_EXTENSION_EQ_8_13"


@dataclass(frozen=True, slots=True)
class InterrowShearOutPlan:
    id: str
    method: InterrowShearOutMethod
    bolt_line_id: str
    e1: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    pitches: tuple[PhysicalQuantity, ...]
    row_span: PhysicalQuantity
    thickness: PhysicalQuantity
    shear_strength: PhysicalQuantity
    phi: Decimal
    factor_metadata: tuple[str, ...]
    per_line_demand: PhysicalQuantity
    availability: PlanAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    warnings: tuple[MultiRowWarning, ...]
    execution_status: DeferredExecutionStatus


def build_interrow_shear_out_plans(
    geometry: MultiRowGeometry,
    source_length_unit: Unit,
    thickness: PhysicalQuantity,
    shear_strength: PhysicalQuantity,
    total_line_demand: PhysicalQuantity,
    factor_metadata: tuple[str, ...],
) -> tuple[InterrowShearOutPlan, ...]:
    """Create one raw-input shear-out plan per physical bolt line."""

    if source_length_unit not in {Unit.IN, Unit.MM}:
        raise ValueError("source_length_unit must be IN or MM.")
    if thickness.dimension is not Dimension.LENGTH or thickness.magnitude <= 0:
        raise ValueError("thickness must be a positive length.")
    if shear_strength.dimension is not Dimension.STRESS or shear_strength.magnitude <= 0:
        raise ValueError("shear_strength must be a positive stress.")
    _require_force(total_line_demand, "total_line_demand")
    if total_line_demand.magnitude < 0:
        raise ValueError("total_line_demand cannot be negative.")
    if not geometry.bolt_lines:
        return ()
    row_count = len(geometry.rows)
    pitches = tuple(_length(value, source_length_unit) for value in geometry.classification.pitches)
    row_span = PhysicalQuantity.of(0, source_length_unit)
    for pitch in pitches:
        row_span += pitch
    if row_count == 2:
        method = InterrowShearOutMethod.ASCE_EQ_8_12
    elif row_count == 3:
        method = InterrowShearOutMethod.ASCE_EQ_8_13
    else:
        method = InterrowShearOutMethod.RATIONAL_EXTENSION_EQ_8_13
    direct = row_count in {2, 3}
    variable_direct = direct and not geometry.classification.constant_pitch
    availability = (
        PlanAvailability.CALCULATION_NOT_SUPPORTED
        if row_count < 2 or variable_direct
        else PlanAvailability.READY
    )
    applicability = (
        MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
        if direct
        else MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    )
    qualification = (
        QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
        if direct and not variable_direct
        else QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    warnings: tuple[MultiRowWarning, ...] = ()
    if row_count > 3:
        warnings = (
            MultiRowWarning(
                MultiRowWarningCode.RATIONAL_EQ_8_13_EXTENSION_USED,
                "The plan retains the actual row span for a rational Eq. 8-13 extension.",
                (f"row_span:{row_span.canonical_string}",),
            ),
        )
    line_demand = total_line_demand / len(geometry.bolt_lines)
    return tuple(
        InterrowShearOutPlan(
            f"SHEAR_OUT_{line.id}",
            method,
            line.id,
            _length(geometry.first_row_end_distance, source_length_unit),
            _length(line.bolts[0].bolt.hole_diameter, source_length_unit),
            pitches,
            row_span,
            thickness,
            shear_strength,
            Decimal("0.45"),
            factor_metadata,
            line_demand,
            availability,
            applicability,
            qualification,
            warnings,
            DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
        )
        for line in geometry.bolt_lines
    )


@dataclass(frozen=True, slots=True)
class MultiRowApplicability:
    geometry_status: GeometryStatus
    availability: PlanAvailability
    first_row_availability: PlanAvailability
    method_applicability: MultiRowMethodApplicability
    qualification: QualificationDisposition
    numerical_comparison: MultiRowNumericalComparison
    warnings: tuple[MultiRowWarning, ...]


def assess_multirow_applicability(
    geometry: MultiRowGeometry,
    first_row: FirstRowGeometryMapping,
    demand_basis: RowDistributionBasis,
) -> MultiRowApplicability:
    """Resolve independent geometry, availability, method, and qualification states."""

    if not isinstance(demand_basis, RowDistributionBasis):
        raise TypeError("demand_basis must be RowDistributionBasis.")
    row_count = len(geometry.rows)
    bolts_per_row = max(len(row.bolts) for row in geometry.rows)
    prescriptive = (
        row_count in {2, 3}
        and bolts_per_row <= 3
        and geometry.classification.supports_uniform_rectangular_method
    )
    qualification = (
        QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
        if prescriptive
        else QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    if demand_basis is RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION:
        method = MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE
    elif prescriptive:
        method = MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
    else:
        method = MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    availability = (
        PlanAvailability.CALCULATION_NOT_SUPPORTED
        if not geometry.classification.nonstaggered
        else PlanAvailability.READY
    )
    first_row_availability = (
        PlanAvailability.READY
        if first_row.width_status is EffectiveWidthStatus.SUPPORTED
        else PlanAvailability.CALCULATION_NOT_SUPPORTED
    )
    warnings: tuple[MultiRowWarning, ...] = ()
    if row_count > 3:
        warnings = (
            MultiRowWarning(
                MultiRowWarningCode.ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED,
                "The physical row count exceeds the prescriptive method scope.",
                (f"row_count:{row_count}",),
            ),
        )
    return MultiRowApplicability(
        GeometryStatus.VALID,
        availability,
        first_row_availability,
        method,
        qualification,
        MultiRowNumericalComparison.NOT_EVALUATED,
        warnings,
    )


class MultiRowAggregateStatus(StrEnum):
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FAIL = "FAIL"
    INCOMPLETE_OR_UNSUPPORTED = "INCOMPLETE_OR_UNSUPPORTED"
    CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED = "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    PASS = "PASS"  # noqa: S105 - engineering status, not a credential
    NOT_EVALUATED = "NOT_EVALUATED"


def aggregate_multirow_status(
    statuses: tuple[MultiRowApplicability, ...],
) -> MultiRowAggregateStatus:
    """Apply the approved deterministic hierarchy without inventing numerical results."""

    if not statuses:
        return MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED
    if any(item.geometry_status is GeometryStatus.INVALID_GEOMETRY for item in statuses):
        return MultiRowAggregateStatus.INVALID_GEOMETRY
    if any(item.numerical_comparison is MultiRowNumericalComparison.FAIL for item in statuses):
        return MultiRowAggregateStatus.FAIL
    incomplete = {
        PlanAvailability.INCOMPLETE_INPUT,
        PlanAvailability.SOURCE_DATA_PENDING,
        PlanAvailability.CALCULATION_NOT_SUPPORTED,
    }
    if any(item.availability in incomplete for item in statuses):
        return MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED
    if any(
        item.availability is PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
        for item in statuses
    ):
        return MultiRowAggregateStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    if any(
        item.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
        for item in statuses
    ):
        return MultiRowAggregateStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    if any(
        item.qualification is QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
        for item in statuses
    ):
        return MultiRowAggregateStatus.ENGINEERING_REVIEW_REQUIRED
    if all(item.numerical_comparison is MultiRowNumericalComparison.PASS for item in statuses):
        return MultiRowAggregateStatus.PASS
    return MultiRowAggregateStatus.NOT_EVALUATED


@dataclass(frozen=True, slots=True)
class MultiRowCalculationPlanSet:
    """One immutable plan bundle; it intentionally has no resistance/result fields."""

    demand: MultiRowDemandPlan
    applicability: MultiRowApplicability
    first_row_net_tension: tuple[FirstRowNetTensionPlan, ...]
    interrow_shear_out: tuple[InterrowShearOutPlan, ...]
    block_shear_plan_ids: tuple[str, ...]
    planned_specification_id: str = (
        "FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1"
    )
    planned_golden_id: str = "frp-master-connection-calculation-slice-2-golden-rc1"
    execution_status: DeferredExecutionStatus = DeferredExecutionStatus.DEFERRED_STAGE_2_4B


__all__ = (
    "CommentaryCoefficientInputPlan",
    "ConnectedMaterialPair",
    "DeferredExecutionStatus",
    "EffectiveWidthStatus",
    "EngineerRowForce",
    "EngineerRowFraction",
    "FirstRowGeometryMapping",
    "FirstRowNetTensionPlan",
    "FirstRowPlanMethod",
    "GeometryStatus",
    "InterrowShearOutMethod",
    "InterrowShearOutPlan",
    "MaterialDirection",
    "MethodProvenance",
    "MultiRowAggregateStatus",
    "MultiRowApplicability",
    "MultiRowCalculationPlanSet",
    "MultiRowDemandPlan",
    "MultiRowMethodApplicability",
    "MultiRowNumericalComparison",
    "MultiRowWarning",
    "MultiRowWarningCode",
    "PerBoltDemandPlan",
    "PlanAvailability",
    "PultrudedElementClassification",
    "QualificationDisposition",
    "RowDemandPlan",
    "RowDemandScenario",
    "RowDistributionBasis",
    "UnknownLbrEnvelopePlan",
    "aggregate_multirow_status",
    "assess_multirow_applicability",
    "build_first_row_net_tension_plans",
    "build_interrow_shear_out_plans",
    "plan_row_demands",
    "prescribed_row_fractions",
    "resolve_first_row_geometry",
)
