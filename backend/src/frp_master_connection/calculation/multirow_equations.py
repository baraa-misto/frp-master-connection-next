"""High-precision numerical primitives for the Calculation Slice 2 engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation.equations import (
    INTERNAL_DECIMAL_PRECISION,
    EndUsePropertyTrace,
    adjust_frp_property,
)
from frp_master_connection.calculation.inputs import EndUseFactors
from frp_master_connection.calculation.multirow import (
    InterrowShearOutMethod,
    MaterialDirection,
    PultrudedElementClassification,
)
from frp_master_connection.calculation.properties import FRPPropertyEntry
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_value,
)
from frp_master_connection.calculation.results import NumericalComparison


class AppendixThetaBranch(StrEnum):
    """Stable branch identities for the Appendix CA8.3.3 exponent."""

    E1_OVER_W_LE_1 = "E1_OVER_W_LE_1"
    E1_OVER_W_GE_1 = "E1_OVER_W_GE_1"
    E1_OVER_G_LE_1 = "E1_OVER_G_LE_1"
    E1_OVER_G_GE_1 = "E1_OVER_G_GE_1"


class BlockShearEquation(StrEnum):
    """Approved Chapter 8 block-shear equation identities."""

    ASCE_EQ_8_14A = "ASCE_EQ_8_14A"
    ASCE_EQ_8_14B = "ASCE_EQ_8_14B"


class BlockShearEccentricityClassification(StrEnum):
    """Physical eccentricity classification used only for equation selection."""

    CONCENTRIC = "CONCENTRIC"
    ECCENTRIC = "ECCENTRIC"


@dataclass(frozen=True, slots=True)
class MultiRowFactorTrace:
    """Every typed factor and intermediate resistance in application order."""

    property_traces: tuple[EndUsePropertyTrace, ...]
    equation_nominal_resistance: PhysicalQuantity
    lap_factor_c_lap: Decimal
    pitch_factor_c_delta: Decimal
    connection_adjusted_nominal_resistance: PhysicalQuantity
    resistance_factor_phi: Decimal
    time_effect_factor_lambda: Decimal
    design_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class PitchFactorTrace:
    pitch: PhysicalQuantity
    minimum_pitch: PhysicalQuantity
    pitch_factor_c_delta: Decimal
    reduced: bool


@dataclass(frozen=True, slots=True)
class SimplifiedFirstRowTrace:
    direction: MaterialDirection
    width: PhysicalQuantity
    thickness: PhysicalQuantity
    tensile_property: EndUsePropertyTrace
    factor_trace: MultiRowFactorTrace


@dataclass(frozen=True, slots=True)
class FullFirstRowTrace:
    direction: MaterialDirection
    element_classification: PultrudedElementClassification
    bolt_count: int
    width: PhysicalQuantity
    bolt_diameter: PhysicalQuantity
    net_hole_diameter: PhysicalQuantity
    unloaded_end_e1: PhysicalQuantity
    gauge: PhysicalQuantity | None
    lbr: Decimal
    spr: Decimal
    theta_branch: AppendixThetaBranch
    theta: Decimal
    appendix_coefficient_c_i: Decimal
    appendix_open_hole_coefficient_c_op_i: Decimal
    ratio: Decimal
    ratio_power: Decimal
    knt: Decimal
    kop: Decimal
    coefficient_a: Decimal
    coefficient_b: Decimal
    denominator: Decimal
    tensile_property: EndUsePropertyTrace
    factor_trace: MultiRowFactorTrace


@dataclass(frozen=True, slots=True)
class UnknownLbrEnvelopeTrace:
    lbr_0: FullFirstRowTrace
    lbr_1: FullFirstRowTrace
    controlling_endpoint_ids: tuple[str, ...]
    selected_design_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class LowerEnvelopeTrace:
    simplified: SimplifiedFirstRowTrace
    full_unknown_lbr: UnknownLbrEnvelopeTrace
    controlling_method_ids: tuple[str, ...]
    selected_design_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class InterrowShearOutTrace:
    method: InterrowShearOutMethod
    unloaded_end_e1: PhysicalQuantity
    net_hole_diameter: PhysicalQuantity
    pitches: tuple[PhysicalQuantity, ...]
    row_span: PhysicalQuantity
    shear_property: EndUsePropertyTrace
    factor_trace: MultiRowFactorTrace


@dataclass(frozen=True, slots=True)
class BlockShearTrace:
    equation: BlockShearEquation
    net_shear_area: PhysicalQuantity
    net_tension_area: PhysicalQuantity
    shear_property: EndUsePropertyTrace
    tensile_property: EndUsePropertyTrace
    shear_component: PhysicalQuantity
    tension_component: PhysicalQuantity
    factor_trace: MultiRowFactorTrace


@dataclass(frozen=True, slots=True)
class ResistanceComparison:
    numerical_comparison: NumericalComparison
    utilization: Decimal | None
    warnings: tuple[str, ...] = ()


def _magnitude(quantity: PhysicalQuantity, dimension: Dimension, unit: Unit) -> Decimal:
    if not isinstance(quantity, PhysicalQuantity) or quantity.dimension is not dimension:
        raise ValueError(f"Expected a {dimension.value} PhysicalQuantity.")
    return quantity.to(unit).magnitude


def _positive_quantity(
    quantity: PhysicalQuantity,
    dimension: Dimension,
    unit: Unit,
    name: str,
) -> Decimal:
    value = _magnitude(quantity, dimension, unit)
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    return value


def _force(value: Decimal, unit: Unit = Unit.N) -> PhysicalQuantity:
    return PhysicalQuantity(value, unit)


def adjusted_property_trace(
    entry: FRPPropertyEntry,
    factors: EndUseFactors,
) -> EndUsePropertyTrace:
    """Reuse the accepted Slice 1 property adjustment without changing its meaning."""

    if not isinstance(entry, FRPPropertyEntry):
        raise TypeError("entry must be an FRPPropertyEntry.")
    if not isinstance(factors, EndUseFactors):
        raise TypeError("factors must be EndUseFactors.")
    return adjust_frp_property(entry.kind, entry.value, entry.qualification_status, factors)


def assemble_multirow_resistance(
    equation_nominal_resistance: PhysicalQuantity,
    property_traces: tuple[EndUsePropertyTrace, ...],
    *,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    resistance_factor_phi: Decimal,
    time_effect_factor_lambda: Decimal,
) -> MultiRowFactorTrace:
    """Apply connection factors, phi, and lambda exactly once in the RC2 order."""

    if not isinstance(property_traces, tuple) or any(
        not isinstance(item, EndUsePropertyTrace) for item in property_traces
    ):
        raise TypeError("property_traces must be a tuple of EndUsePropertyTrace values.")
    nominal_n = _magnitude(equation_nominal_resistance, Dimension.FORCE, Unit.N)
    factors = tuple(
        decimal_value(item)
        for item in (
            lap_factor_c_lap,
            pitch_factor_c_delta,
            resistance_factor_phi,
            time_effect_factor_lambda,
        )
    )
    if any(item <= 0 for item in factors):
        raise ValueError("Resistance factors must be positive.")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        connection_nominal = nominal_n * factors[0] * factors[1]
        design = connection_nominal * factors[2] * factors[3]
    return MultiRowFactorTrace(
        property_traces,
        equation_nominal_resistance,
        factors[0],
        factors[1],
        _force(connection_nominal),
        factors[2],
        factors[3],
        _force(design),
    )


def constant_pitch_factor(
    pitches: tuple[PhysicalQuantity, ...],
    bolt_diameter: PhysicalQuantity,
) -> PitchFactorTrace:
    """Return C_delta=min(1,s/4d) only for an exact constant-pitch tuple."""

    if not isinstance(pitches, tuple) or not pitches:
        raise ValueError("At least one immutable pitch is required.")
    pitch_values = tuple(
        _positive_quantity(item, Dimension.LENGTH, Unit.MM, "pitch") for item in pitches
    )
    if len(set(pitch_values)) != 1:
        raise ValueError("Automatic pitch factor requires constant physical pitch.")
    diameter = _positive_quantity(bolt_diameter, Dimension.LENGTH, Unit.MM, "bolt_diameter")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        minimum = Decimal(4) * diameter
        factor = min(Decimal(1), pitch_values[0] / minimum)
    source_unit = pitches[0].unit
    return PitchFactorTrace(
        pitches[0],
        PhysicalQuantity(minimum, Unit.MM).to(source_unit),
        factor,
        factor < 1,
    )


def simplified_first_row_resistance(
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    direction: MaterialDirection,
    *,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> SimplifiedFirstRowTrace:
    """Execute ASCE Equations 8-10/8-11 using planning-resolved width."""

    if not isinstance(tensile_property, EndUsePropertyTrace):
        raise TypeError("tensile_property must be an EndUsePropertyTrace.")
    if not isinstance(direction, MaterialDirection):
        raise TypeError("direction must be MaterialDirection.")
    width_mm = _positive_quantity(width, Dimension.LENGTH, Unit.MM, "width")
    thickness_mm = _positive_quantity(thickness, Dimension.LENGTH, Unit.MM, "thickness")
    strength = _positive_quantity(
        tensile_property.adjusted_property, Dimension.STRESS, Unit.MPA, "tensile_property"
    )
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        nominal = Decimal("0.2") * width_mm * thickness_mm * strength
    phi = Decimal("0.50") if direction is MaterialDirection.LONGITUDINAL else Decimal("0.45")
    factor_trace = assemble_multirow_resistance(
        _force(nominal),
        (tensile_property,),
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        resistance_factor_phi=phi,
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    return SimplifiedFirstRowTrace(direction, width, thickness, tensile_property, factor_trace)


def _appendix_coefficients(
    direction: MaterialDirection,
    element_classification: PultrudedElementClassification,
) -> tuple[Decimal, Decimal]:
    if not isinstance(direction, MaterialDirection):
        raise TypeError("direction must be MaterialDirection.")
    if not isinstance(element_classification, PultrudedElementClassification):
        raise TypeError("element_classification must be PultrudedElementClassification.")
    coefficient = (
        Decimal("0.40")
        if direction is MaterialDirection.LONGITUDINAL
        and element_classification is PultrudedElementClassification.PLATE
        else Decimal("0.50")
    )
    return coefficient, Decimal("0.50")


def full_first_row_resistance(
    width: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    net_hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    unloaded_end_e1: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    direction: MaterialDirection,
    element_classification: PultrudedElementClassification,
    bolt_count: int,
    lbr: Decimal,
    *,
    gauge: PhysicalQuantity | None,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> FullFirstRowTrace:
    """Execute the approved Appendix CA8.3.3 full first-row method."""

    if isinstance(bolt_count, bool) or not isinstance(bolt_count, int):
        raise TypeError("bolt_count must be a non-Boolean integer.")
    if bolt_count < 1 or bolt_count > 3:
        raise ValueError("The full first-row method supports one to three bolts per row.")
    lbr_value = decimal_value(lbr)
    if not Decimal(0) <= lbr_value <= Decimal(1):
        raise ValueError("lbr must be in the inclusive range zero to one.")
    width_mm = _positive_quantity(width, Dimension.LENGTH, Unit.MM, "width")
    diameter_mm = _positive_quantity(bolt_diameter, Dimension.LENGTH, Unit.MM, "bolt_diameter")
    hole_mm = _positive_quantity(net_hole_diameter, Dimension.LENGTH, Unit.MM, "net_hole_diameter")
    thickness_mm = _positive_quantity(thickness, Dimension.LENGTH, Unit.MM, "thickness")
    end_mm = _positive_quantity(unloaded_end_e1, Dimension.LENGTH, Unit.MM, "unloaded_end_e1")
    strength = _positive_quantity(
        tensile_property.adjusted_property, Dimension.STRESS, Unit.MPA, "tensile_property"
    )
    if width_mm <= Decimal(bolt_count) * diameter_mm:
        raise ValueError("Full first-row geometry requires w > N_b d.")
    if width_mm <= Decimal(bolt_count) * hole_mm:
        raise ValueError("Full first-row geometry requires w > N_b d_n.")
    if bolt_count == 1:
        spacing = width_mm
        spr = width_mm / diameter_mm
        ratio_for_branch = end_mm / width_mm
        if ratio_for_branch <= 1:
            branch = AppendixThetaBranch.E1_OVER_W_LE_1
            theta = Decimal("1.5") - Decimal("0.5") * (width_mm / end_mm)
        else:
            branch = AppendixThetaBranch.E1_OVER_W_GE_1
            theta = Decimal(1)
    else:
        if gauge is None:
            raise ValueError("Two- or three-bolt full method requires gauge.")
        spacing = _positive_quantity(gauge, Dimension.LENGTH, Unit.MM, "gauge")
        spr = spacing / diameter_mm
        ratio_for_branch = end_mm / spacing
        if ratio_for_branch <= 1:
            branch = AppendixThetaBranch.E1_OVER_G_LE_1
            theta = Decimal("1.5") - Decimal("0.5") * (spacing / end_mm)
        else:
            branch = AppendixThetaBranch.E1_OVER_G_GE_1
            theta = Decimal(1)
    if spr <= 1:
        raise ValueError("Full first-row geometry requires S_pr > 1.")
    ci, cop = _appendix_coefficients(direction, element_classification)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        ratio = (spr - Decimal(1)) / (spr + Decimal(1))
        ratio_power = (theta * ratio.ln()).exp()
        knt_denominator = width_mm / (Decimal(bolt_count) * diameter_mm) - Decimal(1)
        open_hole_denominator = Decimal(1) - Decimal(bolt_count) * hole_mm / width_mm
        if knt_denominator <= 0 or open_hole_denominator <= 0:  # pragma: no cover
            raise ValueError("Full first-row coefficient denominator must be positive.")
        knt = (Decimal(1) + ci * (spr - Decimal("1.5") * ratio_power)) / knt_denominator
        kop = Decimal(1) + cop * (Decimal(1) + (Decimal(1) - Decimal(1) / spr) ** 3)
        coefficient_a = knt * (width_mm / (Decimal(bolt_count) * diameter_mm))
        coefficient_b = kop / open_hole_denominator
        denominator = coefficient_a * lbr_value + coefficient_b * (Decimal(1) - lbr_value)
        if coefficient_a <= 0 or coefficient_b <= 0 or denominator <= 0:  # pragma: no cover
            raise ValueError("Full first-row coefficients and denominator must be positive.")
        nominal = width_mm * thickness_mm * strength / denominator
    phi = Decimal("0.50") if direction is MaterialDirection.LONGITUDINAL else Decimal("0.45")
    factor_trace = assemble_multirow_resistance(
        _force(nominal),
        (tensile_property,),
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        resistance_factor_phi=phi,
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    return FullFirstRowTrace(
        direction,
        element_classification,
        bolt_count,
        width,
        bolt_diameter,
        net_hole_diameter,
        unloaded_end_e1,
        gauge,
        lbr_value,
        spr,
        branch,
        theta,
        ci,
        cop,
        ratio,
        ratio_power,
        knt,
        kop,
        coefficient_a,
        coefficient_b,
        denominator,
        tensile_property,
        factor_trace,
    )


def unknown_lbr_endpoint_envelope(
    width: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    net_hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    unloaded_end_e1: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    direction: MaterialDirection,
    element_classification: PultrudedElementClassification,
    bolt_count: int,
    *,
    gauge: PhysicalQuantity | None,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> UnknownLbrEnvelopeTrace:
    """Calculate both exact L_br endpoints and retain every exact governing tie."""

    first = full_first_row_resistance(
        width,
        bolt_diameter,
        net_hole_diameter,
        thickness,
        unloaded_end_e1,
        tensile_property,
        direction,
        element_classification,
        bolt_count,
        Decimal(0),
        gauge=gauge,
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    second = full_first_row_resistance(
        width,
        bolt_diameter,
        net_hole_diameter,
        thickness,
        unloaded_end_e1,
        tensile_property,
        direction,
        element_classification,
        bolt_count,
        Decimal(1),
        gauge=gauge,
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    first_resistance = first.factor_trace.design_resistance
    second_resistance = second.factor_trace.design_resistance
    minimum = min(first_resistance, second_resistance)
    controlling = tuple(
        identity
        for identity, value in (("LBR_0", first_resistance), ("LBR_1", second_resistance))
        if value == minimum
    )
    return UnknownLbrEnvelopeTrace(first, second, controlling, minimum)


def lower_first_row_envelope(
    simplified: SimplifiedFirstRowTrace,
    full_unknown_lbr: UnknownLbrEnvelopeTrace,
) -> LowerEnvelopeTrace:
    """Select the exact lower more-than-three-row branch while retaining ties."""

    if not isinstance(simplified, SimplifiedFirstRowTrace):
        raise TypeError("simplified must be SimplifiedFirstRowTrace.")
    if not isinstance(full_unknown_lbr, UnknownLbrEnvelopeTrace):
        raise TypeError("full_unknown_lbr must be UnknownLbrEnvelopeTrace.")
    simplified_resistance = simplified.factor_trace.design_resistance
    full_resistance = full_unknown_lbr.selected_design_resistance
    selected = min(simplified_resistance, full_resistance)
    identities = tuple(
        identity
        for identity, value in (
            ("SIMPLIFIED_EXTENSION", simplified_resistance),
            ("FULL_UNKNOWN_LBR_ENVELOPE", full_resistance),
        )
        if value == selected
    )
    return LowerEnvelopeTrace(simplified, full_unknown_lbr, identities, selected)


def interrow_shear_out_resistance(
    method: InterrowShearOutMethod,
    unloaded_end_e1: PhysicalQuantity,
    net_hole_diameter: PhysicalQuantity,
    pitches: tuple[PhysicalQuantity, ...],
    thickness: PhysicalQuantity,
    shear_property: EndUsePropertyTrace,
    *,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> InterrowShearOutTrace:
    """Execute Eq. 8-12, Eq. 8-13, or the approved actual-row-span extension."""

    if not isinstance(method, InterrowShearOutMethod):
        raise TypeError("method must be InterrowShearOutMethod.")
    if not isinstance(pitches, tuple) or not pitches:
        raise ValueError("Inter-row shear-out requires physical pitches.")
    end_mm = _positive_quantity(unloaded_end_e1, Dimension.LENGTH, Unit.MM, "unloaded_end_e1")
    hole_mm = _positive_quantity(net_hole_diameter, Dimension.LENGTH, Unit.MM, "net_hole_diameter")
    thickness_mm = _positive_quantity(thickness, Dimension.LENGTH, Unit.MM, "thickness")
    pitch_mm = tuple(
        _positive_quantity(item, Dimension.LENGTH, Unit.MM, "pitch") for item in pitches
    )
    strength = _positive_quantity(
        shear_property.adjusted_property, Dimension.STRESS, Unit.MPA, "shear_property"
    )
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        row_span_mm = sum(pitch_mm, Decimal(0))
        if method is InterrowShearOutMethod.ASCE_EQ_8_12:
            if len(pitches) != 1:
                raise ValueError("Equation 8-12 requires exactly two rows and one pitch.")
            effective_length = Decimal("1.4") * (end_mm - hole_mm / Decimal(2) + pitch_mm[0])
        elif method is InterrowShearOutMethod.ASCE_EQ_8_13:
            if len(pitches) != 2:
                raise ValueError("Equation 8-13 requires exactly three rows and two pitches.")
            if len(set(pitch_mm)) != 1:
                raise ValueError("Direct Equation 8-13 requires constant pitch.")
            effective_length = Decimal(2) * row_span_mm
        else:
            if len(pitches) < 3:
                raise ValueError("The rational Eq. 8-13 extension requires more than three rows.")
            effective_length = Decimal(2) * row_span_mm
        if effective_length <= 0:
            raise ValueError("Inter-row shear-out effective length must be positive.")
        nominal = effective_length * thickness_mm * strength
    factor_trace = assemble_multirow_resistance(
        _force(nominal),
        (shear_property,),
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        resistance_factor_phi=Decimal("0.45"),
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    return InterrowShearOutTrace(
        method,
        unloaded_end_e1,
        net_hole_diameter,
        pitches,
        PhysicalQuantity(row_span_mm, Unit.MM).to(pitches[0].unit),
        shear_property,
        factor_trace,
    )


def classify_block_shear_eccentricity(
    eccentricity: PhysicalQuantity,
    tolerance: PhysicalQuantity,
) -> BlockShearEccentricityClassification:
    """Classify signed physical eccentricity using one fingerprinted length tolerance."""

    eccentricity_mm = _magnitude(eccentricity, Dimension.LENGTH, Unit.MM)
    tolerance_mm = _positive_quantity(tolerance, Dimension.LENGTH, Unit.MM, "tolerance")
    return (
        BlockShearEccentricityClassification.CONCENTRIC
        if abs(eccentricity_mm) <= tolerance_mm
        else BlockShearEccentricityClassification.ECCENTRIC
    )


def block_shear_resistance(
    equation: BlockShearEquation,
    net_shear_area: PhysicalQuantity,
    net_tension_area: PhysicalQuantity,
    shear_property: EndUsePropertyTrace,
    tensile_property: EndUsePropertyTrace,
    *,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> BlockShearTrace:
    """Execute ASCE Equation 8-14a or 8-14b using raw accepted path areas."""

    if not isinstance(equation, BlockShearEquation):
        raise TypeError("equation must be BlockShearEquation.")
    shear_area = _positive_quantity(net_shear_area, Dimension.AREA, Unit.MM2, "net_shear_area")
    tension_area = _positive_quantity(
        net_tension_area, Dimension.AREA, Unit.MM2, "net_tension_area"
    )
    shear_strength = _positive_quantity(
        shear_property.adjusted_property, Dimension.STRESS, Unit.MPA, "shear_property"
    )
    tensile_strength = _positive_quantity(
        tensile_property.adjusted_property, Dimension.STRESS, Unit.MPA, "tensile_property"
    )
    tension_coefficient = (
        Decimal(1) if equation is BlockShearEquation.ASCE_EQ_8_14A else Decimal("0.5")
    )
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        shear_component = shear_area * shear_strength
        tension_component = tension_coefficient * tension_area * tensile_strength
        nominal = Decimal("0.5") * (shear_component + tension_component)
    factor_trace = assemble_multirow_resistance(
        _force(nominal),
        (shear_property, tensile_property),
        lap_factor_c_lap=lap_factor_c_lap,
        pitch_factor_c_delta=pitch_factor_c_delta,
        resistance_factor_phi=Decimal("0.45"),
        time_effect_factor_lambda=time_effect_factor_lambda,
    )
    return BlockShearTrace(
        equation,
        net_shear_area,
        net_tension_area,
        shear_property,
        tensile_property,
        _force(shear_component),
        _force(tension_component),
        factor_trace,
    )


def compare_resistance(
    demand: PhysicalQuantity,
    design_resistance: PhysicalQuantity,
) -> ResistanceComparison:
    """Compare nonnegative demand and fail closed for nonpositive design resistance."""

    demand_n = _magnitude(demand, Dimension.FORCE, Unit.N)
    design_n = _magnitude(design_resistance, Dimension.FORCE, Unit.N)
    if demand_n < 0:
        raise ValueError("Comparison demand must be nonnegative.")
    if design_n <= 0:
        return ResistanceComparison(
            NumericalComparison.FAIL,
            None,
            ("NONPOSITIVE_DESIGN_RESISTANCE",),
        )
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        utilization = demand_n / design_n
    comparison = NumericalComparison.PASS if demand_n <= design_n else NumericalComparison.FAIL
    return ResistanceComparison(comparison, utilization)


__all__ = (
    "AppendixThetaBranch",
    "BlockShearEccentricityClassification",
    "BlockShearEquation",
    "BlockShearTrace",
    "FullFirstRowTrace",
    "InterrowShearOutTrace",
    "LowerEnvelopeTrace",
    "MultiRowFactorTrace",
    "PitchFactorTrace",
    "ResistanceComparison",
    "SimplifiedFirstRowTrace",
    "UnknownLbrEnvelopeTrace",
    "adjusted_property_trace",
    "assemble_multirow_resistance",
    "block_shear_resistance",
    "classify_block_shear_eccentricity",
    "compare_resistance",
    "constant_pitch_factor",
    "full_first_row_resistance",
    "interrow_shear_out_resistance",
    "lower_first_row_envelope",
    "simplified_first_row_resistance",
    "unknown_lbr_endpoint_envelope",
)
