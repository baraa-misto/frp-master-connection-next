"""Authorized high-precision Stage 2.1B single-bolt equation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation.inputs import EndUseFactors, PultrudedElementForm
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    ThreadStatus,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_value,
)
from frp_master_connection.calculation.sources import QualificationStatus

CALCULATION_ENGINE_VERSION = "0.1.0.dev1"
ENGINEERING_RULE_SET_VERSION = "asce74-23-ch8-single-bolt-rc2.dev1"
DECIMAL_PI = Decimal("3.1415926535897932384626433832795028841971693993751")
INTERNAL_DECIMAL_PRECISION = 60


class GoverningEquationBranch(StrEnum):
    """Stable branch identities retained by minimum/tie calculations."""

    PULL_THROUGH_8_4A = "PULL_THROUGH_8_4A"
    PULL_THROUGH_8_4B = "PULL_THROUGH_8_4B"
    CLEAVAGE_A = "CLEAVAGE_A"
    CLEAVAGE_B = "CLEAVAGE_B"


@dataclass(frozen=True, slots=True)
class EndUsePropertyTrace:
    property_kind: FRPPropertyKind
    source_property: PhysicalQuantity
    qualification_status: QualificationStatus
    cm: Decimal
    ct: Decimal
    cch: Decimal
    adjusted_property: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class FactorAssemblyTrace:
    property_traces: tuple[EndUsePropertyTrace, ...]
    nominal_resistance: PhysicalQuantity
    c_delta: Decimal
    c_lap: Decimal
    phi: Decimal
    lambda_factor: Decimal
    design_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class BoltAreaTrace:
    diameter: PhysicalQuantity
    area: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class BoltResistanceTrace:
    area_trace: BoltAreaTrace
    nominal_stress: PhysicalQuantity
    phi: Decimal
    lambda_factor: Decimal
    nominal_resistance: PhysicalQuantity
    design_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class CombinedBoltTrace:
    area_trace: BoltAreaTrace
    fnt: PhysicalQuantity
    fnv: PhysicalQuantity
    shear_demand: PhysicalQuantity
    required_shear_stress: PhysicalQuantity
    phi: Decimal
    modified_tensile_stress_raw: PhysicalQuantity
    modified_tensile_stress: PhysicalQuantity
    nominal_tensile_resistance: PhysicalQuantity
    design_tensile_resistance: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class PullThroughTrace:
    through_thickness_property: EndUsePropertyTrace
    interlaminar_property: EndUsePropertyTrace
    branch_8_4a_nominal: PhysicalQuantity
    branch_8_4b_nominal: PhysicalQuantity
    governing_branches: tuple[GoverningEquationBranch, ...]
    factor_trace: FactorAssemblyTrace


@dataclass(frozen=True, slots=True)
class BearingTrace:
    bearing_property: EndUsePropertyTrace
    thread_factor: Decimal
    factor_trace: FactorAssemblyTrace


@dataclass(frozen=True, slots=True)
class NetTensionTrace:
    tensile_property: EndUsePropertyTrace
    element_form: PultrudedElementForm
    spr: Decimal
    theta: Decimal
    ci: Decimal
    logarithm_ratio: Decimal
    ratio_power: Decimal
    knt: Decimal
    factor_trace: FactorAssemblyTrace


@dataclass(frozen=True, slots=True)
class ShearOutTrace:
    shear_property: EndUsePropertyTrace
    factor_trace: FactorAssemblyTrace


@dataclass(frozen=True, slots=True)
class CleavageTrace:
    tensile_property: EndUsePropertyTrace
    shear_property: EndUsePropertyTrace
    bearing_trace: BearingTrace
    branch_a_factor_trace: FactorAssemblyTrace
    branch_b_condition_e1_over_d: Decimal
    branch_b_coefficient: Decimal
    branch_b_factor_trace: FactorAssemblyTrace
    governing_branches: tuple[GoverningEquationBranch, ...]
    selected_nominal_resistance: PhysicalQuantity
    selected_design_resistance: PhysicalQuantity


type EquationTrace = (
    BoltResistanceTrace
    | CombinedBoltTrace
    | PullThroughTrace
    | BearingTrace
    | NetTensionTrace
    | ShearOutTrace
    | CleavageTrace
)


def _magnitude(quantity: PhysicalQuantity, dimension: Dimension, unit: Unit) -> Decimal:
    if quantity.dimension is not dimension:
        raise ValueError(f"Expected {dimension.value}, received {quantity.dimension.value}.")
    return quantity.to(unit).magnitude


def _force_from_length_length_stress(
    first_length: PhysicalQuantity,
    second_length: PhysicalQuantity,
    stress: PhysicalQuantity,
    coefficient: Decimal = Decimal(1),
) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        value = (
            _magnitude(first_length, Dimension.LENGTH, Unit.MM)
            * _magnitude(second_length, Dimension.LENGTH, Unit.MM)
            * _magnitude(stress, Dimension.STRESS, Unit.MPA)
            * coefficient
        )
    return PhysicalQuantity(value, Unit.N)


def bolt_body_area(diameter: PhysicalQuantity) -> BoltAreaTrace:
    """Return nominal unthreaded body area using high-precision Decimal pi."""

    diameter_mm = _magnitude(diameter, Dimension.LENGTH, Unit.MM)
    if diameter_mm <= 0:
        raise ValueError("Bolt diameter must be positive.")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        area = DECIMAL_PI * diameter_mm * diameter_mm / Decimal(4)
    return BoltAreaTrace(diameter, PhysicalQuantity(area, Unit.MM2))


def f593_nominal_shear_stress(
    fnt: PhysicalQuantity,
    thread_status: ThreadStatus,
) -> PhysicalQuantity:
    """Apply the authorized single-plane F593 thread multiplier to explicit Fnt."""

    if not isinstance(thread_status, ThreadStatus):
        raise TypeError("thread_status must be a ThreadStatus.")
    fnt_mpa = _magnitude(fnt, Dimension.STRESS, Unit.MPA)
    if fnt_mpa <= 0:
        raise ValueError("Fnt must be positive.")
    multiplier = Decimal("0.60") if thread_status is ThreadStatus.EXCLUDED else Decimal("0.50")
    return PhysicalQuantity(fnt_mpa * multiplier, Unit.MPA)


def _bolt_resistance(
    diameter: PhysicalQuantity,
    nominal_stress: PhysicalQuantity,
) -> BoltResistanceTrace:
    area_trace = bolt_body_area(diameter)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        nominal = area_trace.area.to(Unit.MM2).magnitude * _magnitude(
            nominal_stress, Dimension.STRESS, Unit.MPA
        )
        design = Decimal("0.75") * nominal
    return BoltResistanceTrace(
        area_trace,
        nominal_stress,
        Decimal("0.75"),
        Decimal("1.0"),
        PhysicalQuantity(nominal, Unit.N),
        PhysicalQuantity(design, Unit.N),
    )


def bolt_tension_resistance(
    diameter: PhysicalQuantity,
    fnt: PhysicalQuantity,
) -> BoltResistanceTrace:
    return _bolt_resistance(diameter, fnt)


def bolt_shear_resistance(
    diameter: PhysicalQuantity,
    fnt: PhysicalQuantity,
    thread_status: ThreadStatus,
) -> BoltResistanceTrace:
    return _bolt_resistance(diameter, f593_nominal_shear_stress(fnt, thread_status))


def bolt_shear_resistance_from_nominal_stress(
    diameter: PhysicalQuantity,
    nominal_shear_stress: PhysicalQuantity,
) -> BoltResistanceTrace:
    """Apply the accepted Eq. 8-2 resistance assembly to source-authorized ``F_nv``."""

    if nominal_shear_stress.dimension is not Dimension.STRESS:
        raise ValueError("Nominal bolt shear stress must be a stress quantity.")
    if nominal_shear_stress.canonical_magnitude <= 0:
        raise ValueError("Nominal bolt shear stress must be positive.")
    area_trace = bolt_body_area(diameter)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        if nominal_shear_stress.unit in {Unit.KSI, Unit.PSI}:
            area = area_trace.area.to(Unit.IN2).magnitude
            stress = nominal_shear_stress.to(Unit.KSI).magnitude
            nominal = PhysicalQuantity.of(area * stress, Unit.KIP)
        else:
            area = area_trace.area.to(Unit.MM2).magnitude
            stress = nominal_shear_stress.to(Unit.MPA).magnitude
            nominal = PhysicalQuantity.of(area * stress, Unit.N)
        design = PhysicalQuantity.of(nominal.magnitude * Decimal("0.75"), nominal.unit)
    return BoltResistanceTrace(
        area_trace,
        nominal_shear_stress,
        Decimal("0.75"),
        Decimal("1.0"),
        nominal,
        design,
    )


def combined_bolt_tension_shear_resistance(
    diameter: PhysicalQuantity,
    fnt: PhysicalQuantity,
    thread_status: ThreadStatus,
    shear_demand: PhysicalQuantity,
) -> CombinedBoltTrace:
    area_trace = bolt_body_area(diameter)
    fnv = f593_nominal_shear_stress(fnt, thread_status)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        area = area_trace.area.to(Unit.MM2).magnitude
        shear = _magnitude(shear_demand, Dimension.FORCE, Unit.N)
        required_shear = shear / area
        fnt_mpa = fnt.to(Unit.MPA).magnitude
        fnv_mpa = fnv.to(Unit.MPA).magnitude
        phi = Decimal("0.75")
        modified_raw = Decimal("1.3") * fnt_mpa - (fnt_mpa / (phi * fnv_mpa)) * required_shear
        modified = min(modified_raw, fnt_mpa)
        nominal = modified * area
        design = phi * nominal
    return CombinedBoltTrace(
        area_trace,
        fnt,
        fnv,
        shear_demand,
        PhysicalQuantity(required_shear, Unit.MPA),
        phi,
        PhysicalQuantity(modified_raw, Unit.MPA),
        PhysicalQuantity(modified, Unit.MPA),
        PhysicalQuantity(nominal, Unit.N),
        PhysicalQuantity(design, Unit.N),
    )


def adjust_frp_property(
    property_kind: FRPPropertyKind,
    source_property: PhysicalQuantity,
    qualification_status: QualificationStatus,
    factors: EndUseFactors,
) -> EndUsePropertyTrace:
    is_ratio = property_kind is FRPPropertyKind.NU_LT
    source_value = _magnitude(
        source_property,
        Dimension.DIMENSIONLESS if is_ratio else Dimension.STRESS,
        Unit.ONE if is_ratio else Unit.MPA,
    )
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        adjusted = source_value * factors.cm * factors.ct * factors.cch
    return EndUsePropertyTrace(
        property_kind,
        source_property,
        qualification_status,
        factors.cm,
        factors.ct,
        factors.cch,
        PhysicalQuantity(adjusted, Unit.ONE if is_ratio else Unit.MPA),
    )


def assemble_frp_design_resistance(
    nominal_resistance: PhysicalQuantity,
    property_traces: tuple[EndUsePropertyTrace, ...],
    *,
    c_delta: Decimal,
    c_lap: Decimal,
    phi: Decimal,
    lambda_factor: Decimal,
) -> FactorAssemblyTrace:
    factors = tuple(decimal_value(value) for value in (c_delta, c_lap, phi, lambda_factor))
    if any(value <= 0 for value in factors):
        raise ValueError("Resistance factors must be positive.")
    nominal_n = _magnitude(nominal_resistance, Dimension.FORCE, Unit.N)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        design = nominal_n
        for factor in factors:
            design *= factor
    return FactorAssemblyTrace(
        property_traces,
        nominal_resistance,
        factors[0],
        factors[1],
        factors[2],
        factors[3],
        PhysicalQuantity(design, Unit.N),
    )


def pull_through_resistance(
    washer_outside_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    through_thickness_property: EndUsePropertyTrace,
    interlaminar_property: EndUsePropertyTrace,
    *,
    c_delta: Decimal,
    lambda_factor: Decimal,
) -> PullThroughTrace:
    branch_a = _force_from_length_length_stress(
        washer_outside_diameter,
        thickness,
        through_thickness_property.adjusted_property,
        Decimal("0.5") * DECIMAL_PI,
    )
    branch_b = _force_from_length_length_stress(
        washer_outside_diameter,
        thickness,
        interlaminar_property.adjusted_property,
        Decimal("0.4") * DECIMAL_PI,
    )
    governing = min(branch_a, branch_b)
    through = through_thickness_property.adjusted_property.canonical_magnitude
    interlaminar = interlaminar_property.adjusted_property.canonical_magnitude
    exact_symbolic_tie = Decimal(5) * through == Decimal(4) * interlaminar
    branches = (
        (
            GoverningEquationBranch.PULL_THROUGH_8_4A,
            GoverningEquationBranch.PULL_THROUGH_8_4B,
        )
        if exact_symbolic_tie
        else tuple(
            branch
            for branch, value in (
                (GoverningEquationBranch.PULL_THROUGH_8_4A, branch_a),
                (GoverningEquationBranch.PULL_THROUGH_8_4B, branch_b),
            )
            if value == governing
        )
    )
    factor_trace = assemble_frp_design_resistance(
        governing,
        (through_thickness_property, interlaminar_property),
        c_delta=c_delta,
        c_lap=Decimal("1.0"),
        phi=Decimal("0.50"),
        lambda_factor=lambda_factor,
    )
    return PullThroughTrace(
        through_thickness_property,
        interlaminar_property,
        branch_a,
        branch_b,
        branches,
        factor_trace,
    )


def pin_bearing_resistance(
    thickness: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    bearing_property: EndUsePropertyTrace,
    thread_status: ThreadStatus,
    *,
    c_delta: Decimal,
    c_lap: Decimal,
    lambda_factor: Decimal,
) -> BearingTrace:
    if not isinstance(thread_status, ThreadStatus):
        raise TypeError("thread_status must be a ThreadStatus.")
    thread_factor = Decimal("1.0") if thread_status is ThreadStatus.EXCLUDED else Decimal("0.60")
    nominal = _force_from_length_length_stress(
        thickness,
        bolt_diameter,
        bearing_property.adjusted_property,
        thread_factor,
    )
    return BearingTrace(
        bearing_property,
        thread_factor,
        assemble_frp_design_resistance(
            nominal,
            (bearing_property,),
            c_delta=c_delta,
            c_lap=c_lap,
            phi=Decimal("0.60"),
            lambda_factor=lambda_factor,
        ),
    )


def net_tension_resistance(
    width: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    e1: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    element_form: PultrudedElementForm,
    direction_longitudinal: bool,
    *,
    c_delta: Decimal,
    c_lap: Decimal,
    lambda_factor: Decimal,
) -> NetTensionTrace:
    if not isinstance(element_form, PultrudedElementForm):
        raise TypeError("element_form must be a PultrudedElementForm.")
    if not isinstance(direction_longitudinal, bool):
        raise TypeError("direction_longitudinal must be Boolean.")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        w = _magnitude(width, Dimension.LENGTH, Unit.MM)
        d = _magnitude(bolt_diameter, Dimension.LENGTH, Unit.MM)
        dn = _magnitude(hole_diameter, Dimension.LENGTH, Unit.MM)
        end_distance = _magnitude(e1, Dimension.LENGTH, Unit.MM)
        if d <= 0 or end_distance <= 0:
            raise ValueError("Net tension requires positive bolt diameter and end distance.")
        if w <= dn:
            raise ValueError("Net tension requires width greater than the hole diameter.")
        spr = w / d
        ratio = (spr - Decimal(1)) / (spr + Decimal(1))
        if spr <= 1:
            raise ValueError(
                "Net tension requires a positive logarithm ratio and Spr greater than one."
            )
        theta = (
            Decimal("1.5") - Decimal("0.5") * (w / end_distance)
            if end_distance / w <= 1
            else Decimal("1.0")
        )
        ratio_power = (theta * ratio.ln()).exp()
        ci = (
            Decimal("0.40")
            if element_form is PultrudedElementForm.PLATE and direction_longitudinal
            else Decimal("0.50")
        )
        knt = ci * (spr - Decimal("1.5") * ratio_power) + Decimal(1)
        nominal = (
            (w - dn)
            * _magnitude(thickness, Dimension.LENGTH, Unit.MM)
            * tensile_property.adjusted_property.to(Unit.MPA).magnitude
            / knt
        )
    factor_trace = assemble_frp_design_resistance(
        PhysicalQuantity(nominal, Unit.N),
        (tensile_property,),
        c_delta=c_delta,
        c_lap=c_lap,
        phi=Decimal("0.45"),
        lambda_factor=lambda_factor,
    )
    return NetTensionTrace(
        tensile_property,
        element_form,
        spr,
        theta,
        ci,
        ratio,
        ratio_power,
        knt,
        factor_trace,
    )


def shear_out_resistance(
    e1: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    shear_property: EndUsePropertyTrace,
    *,
    c_delta: Decimal,
    c_lap: Decimal,
    lambda_factor: Decimal,
) -> ShearOutTrace:
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        net_end = _magnitude(e1, Dimension.LENGTH, Unit.MM) - (
            _magnitude(hole_diameter, Dimension.LENGTH, Unit.MM) / Decimal(2)
        )
    nominal = _force_from_length_length_stress(
        PhysicalQuantity(net_end, Unit.MM),
        thickness,
        shear_property.adjusted_property,
        Decimal("1.4"),
    )
    return ShearOutTrace(
        shear_property,
        assemble_frp_design_resistance(
            nominal,
            (shear_property,),
            c_delta=c_delta,
            c_lap=c_lap,
            phi=Decimal("0.50"),
            lambda_factor=lambda_factor,
        ),
    )


def cleavage_resistance(
    e1: PhysicalQuantity,
    e2: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    shear_property: EndUsePropertyTrace,
    bearing_trace: BearingTrace,
    *,
    c_delta: Decimal,
    c_lap: Decimal,
    lambda_factor: Decimal,
) -> CleavageTrace:
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        end_distance = _magnitude(e1, Dimension.LENGTH, Unit.MM)
        side_distance = _magnitude(e2, Dimension.LENGTH, Unit.MM)
        diameter = _magnitude(bolt_diameter, Dimension.LENGTH, Unit.MM)
        hole = _magnitude(hole_diameter, Dimension.LENGTH, Unit.MM)
        layer_thickness = _magnitude(thickness, Dimension.LENGTH, Unit.MM)
        tensile = tensile_property.adjusted_property.to(Unit.MPA).magnitude
        shear = shear_property.adjusted_property.to(Unit.MPA).magnitude
        nominal_a = (
            Decimal("0.15")
            * (
                ((Decimal(2) * side_distance - hole) * tensile)
                + (Decimal(2) * end_distance * shear)
            )
            * layer_thickness
        )
        ratio = end_distance / diameter
        if ratio < 4:
            coefficient = (
                Decimal(10) / Decimal(9) - (Decimal(4) * hole) / (Decimal(9) * end_distance)
            ) ** 2
            nominal_b = bearing_trace.factor_trace.nominal_resistance * coefficient
            phi_b = Decimal("0.50")
        else:
            coefficient = Decimal(1)
            nominal_b = bearing_trace.factor_trace.nominal_resistance
            phi_b = Decimal("0.60")
    branch_a = assemble_frp_design_resistance(
        PhysicalQuantity(nominal_a, Unit.N),
        (tensile_property, shear_property),
        c_delta=c_delta,
        c_lap=c_lap,
        phi=Decimal("0.50"),
        lambda_factor=lambda_factor,
    )
    branch_b = assemble_frp_design_resistance(
        nominal_b,
        bearing_trace.factor_trace.property_traces,
        c_delta=c_delta,
        c_lap=c_lap,
        phi=phi_b,
        lambda_factor=lambda_factor,
    )
    governing_design = min(branch_a.design_resistance, branch_b.design_resistance)
    governing = tuple(
        branch
        for branch, value in (
            (GoverningEquationBranch.CLEAVAGE_A, branch_a.design_resistance),
            (GoverningEquationBranch.CLEAVAGE_B, branch_b.design_resistance),
        )
        if value == governing_design
    )
    selected_nominal = (
        branch_a.nominal_resistance
        if branch_a.design_resistance == governing_design
        else branch_b.nominal_resistance
    )
    return CleavageTrace(
        tensile_property,
        shear_property,
        bearing_trace,
        branch_a,
        ratio,
        coefficient,
        branch_b,
        governing,
        selected_nominal,
        governing_design,
    )


__all__ = (
    "CALCULATION_ENGINE_VERSION",
    "DECIMAL_PI",
    "ENGINEERING_RULE_SET_VERSION",
    "INTERNAL_DECIMAL_PRECISION",
    "BearingTrace",
    "BoltAreaTrace",
    "BoltResistanceTrace",
    "CleavageTrace",
    "CombinedBoltTrace",
    "EndUsePropertyTrace",
    "EquationTrace",
    "FactorAssemblyTrace",
    "GoverningEquationBranch",
    "NetTensionTrace",
    "PullThroughTrace",
    "ShearOutTrace",
    "adjust_frp_property",
    "assemble_frp_design_resistance",
    "bolt_body_area",
    "bolt_shear_resistance",
    "bolt_shear_resistance_from_nominal_stress",
    "bolt_tension_resistance",
    "cleavage_resistance",
    "combined_bolt_tension_shear_resistance",
    "f593_nominal_shear_stress",
    "net_tension_resistance",
    "pin_bearing_resistance",
    "pull_through_resistance",
    "shear_out_resistance",
)
