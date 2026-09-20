"""Calculation Slice 4 ASCE/SEI 74-23 Chapter 7 plate strengths."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation.equations import EndUsePropertyTrace
from frp_master_connection.calculation.inputs import TimeEffectFactor
from frp_master_connection.calculation.properties import FRPPropertyKind
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_value,
)
from frp_master_connection.calculation.sources import (
    CalculationSourceSnapshot,
    asce_74_23_chapter_7_source,
)

PLATE_STRENGTH_ENGINE_VERSION = "calculation-slice-4-rc1"
PLATE_INTERNAL_DECIMAL_PRECISION = 60
PLATE_PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286")
PLATE_TENSION_PHI = Decimal("0.65")
PLATE_COMPRESSION_PHI = Decimal("0.70")
PLATE_SHEAR_PHI = Decimal("0.70")
PLATE_LONGITUDINAL_K_CR = Decimal("1.0")


class PlateStrengthMethod(StrEnum):
    LONGITUDINAL_TENSION = "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION"
    TRANSVERSE_TENSION = "ASCE74_EQ_7_13_TRANSVERSE_PLATE_TENSION"
    LONGITUDINAL_COMPRESSION_RUPTURE = "ASCE74_EQ_7_15_LONGITUDINAL_COMPRESSION_RUPTURE"
    TRANSVERSE_COMPRESSION_RUPTURE = "ASCE74_EQ_7_16_TRANSVERSE_COMPRESSION_RUPTURE"
    LONGITUDINAL_BUCKLING_STRENGTH = "ASCE74_EQ_7_17_LONGITUDINAL_PLATE_BUCKLING_STRENGTH"
    LONGITUDINAL_BUCKLING_STRESS = "ASCE74_EQ_7_18_LONGITUDINAL_PLATE_BUCKLING_STRESS"
    LONGITUDINAL_KCR = "ASCE74_EQ_7_19_KCR"
    COMBINED_COMPRESSION_BUCKLING_STRENGTH = "ASCE74_EQ_7_20_COMBINED_COMPRESSION_BUCKLING_STRENGTH"
    COMBINED_COMPRESSION_BUCKLING_STRESS = "ASCE74_EQ_7_21_COMBINED_COMPRESSION_BUCKLING_STRESS"
    COMBINED_COMPRESSION_XI_RANGE = "ASCE74_EQ_7_22_COMBINED_COMPRESSION_XI_RANGE"
    SHEAR_RUPTURE = "ASCE74_EQ_7_24_IN_PLANE_SHEAR_RUPTURE"
    SHEAR_BUCKLING_STRENGTH = "ASCE74_EQ_7_25_IN_PLANE_SHEAR_BUCKLING_STRENGTH"
    SHEAR_BUCKLING_STRESS = "ASCE74_EQ_7_26_IN_PLANE_SHEAR_BUCKLING_STRESS"
    SHEAR_BUCKLING_ETA = "ASCE74_EQ_7_27_SHEAR_BUCKLING_ETA"


class PlateStrengthStatus(StrEnum):
    COMPLETE = "COMPLETE"
    REQUIRES_SECTION_2_3_2 = "REQUIRES_SECTION_2_3_2"


class PlateGoverningMode(StrEnum):
    MATERIAL_RUPTURE = "MATERIAL_RUPTURE"
    ORTHOTROPIC_PLATE_BUCKLING = "ORTHOTROPIC_PLATE_BUCKLING"
    ORTHOTROPIC_SHEAR_BUCKLING = "ORTHOTROPIC_SHEAR_BUCKLING"


class PlateStrengthAdvisory(StrEnum):
    NARROW_PLATE = "C7_6_3_NARROW_PLATE_VALIDATION_CAUTION"
    SHORT_COMPRESSION_PLATE = "C7_6_3_SHORT_PLATE_CONSERVATIVE_APPROXIMATION"
    SHORT_SHEAR_PLATE = "C7_7_3_LONG_PLATE_EQUATION_CONSERVATIVE_FOR_A_LT_B"


class ShearEtaBranch(StrEnum):
    ZERO_LT_ETA_LE_ONE = "0_LT_ETA_LE_1"
    ETA_GT_ONE = "ETA_GT_1"


@dataclass(frozen=True, slots=True)
class PlateTensionStrengthResult:
    method: PlateStrengthMethod
    source: CalculationSourceSnapshot
    effective_net_area_per_unit_width: PhysicalQuantity
    adjusted_property: EndUsePropertyTrace
    nominal_strength: PhysicalQuantity
    resistance_factor: Decimal
    time_effect_factor: TimeEffectFactor
    design_strength: PhysicalQuantity
    governing_mode: PlateGoverningMode
    property_adjustment_applied_by_engine: bool
    advisories: tuple[PlateStrengthAdvisory, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class PlateCompressionStrengthResult:
    methods: tuple[PlateStrengthMethod, ...]
    sources: tuple[CalculationSourceSnapshot, ...]
    thickness: PhysicalQuantity
    transverse_span: PhysicalQuantity
    longitudinal_span: PhysicalQuantity | None
    adjusted_compressive_property: EndUsePropertyTrace
    adjusted_moduli: tuple[EndUsePropertyTrace, ...]
    k_cr: Decimal
    rupture_nominal_strength: PhysicalQuantity
    buckling_stress: PhysicalQuantity
    buckling_nominal_strength: PhysicalQuantity
    nominal_strength: PhysicalQuantity
    resistance_factor: Decimal
    time_effect_factor: TimeEffectFactor
    design_strength: PhysicalQuantity
    governing_mode: PlateGoverningMode
    b_over_t: Decimal
    a_over_b: Decimal | None
    property_adjustment_applied_by_engine: bool
    advisories: tuple[PlateStrengthAdvisory, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class TransverseCompressionReferenceResult:
    method: PlateStrengthMethod
    source: CalculationSourceSnapshot
    thickness: PhysicalQuantity
    adjusted_compressive_property: EndUsePropertyTrace
    rupture_nominal_strength: PhysicalQuantity
    resistance_factor: Decimal
    time_effect_factor: TimeEffectFactor
    rupture_design_reference: PhysicalQuantity
    complete_stability_status: PlateStrengthStatus
    governing_mode: PlateGoverningMode
    property_adjustment_applied_by_engine: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class CombinedCompressionBucklingResult:
    methods: tuple[PlateStrengthMethod, ...]
    sources: tuple[CalculationSourceSnapshot, ...]
    status: PlateStrengthStatus
    thickness: PhysicalQuantity
    longitudinal_span: PhysicalQuantity
    transverse_span: PhysicalQuantity
    xi_lt: Decimal
    span_ratio_b_over_a: Decimal
    adjusted_moduli: tuple[EndUsePropertyTrace, ...]
    buckling_stress: PhysicalQuantity | None
    buckling_nominal_strength: PhysicalQuantity | None
    resistance_factor: Decimal
    time_effect_factor: TimeEffectFactor
    design_strength_reference: PhysicalQuantity | None
    property_adjustment_applied_by_engine: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class PlateShearStrengthResult:
    methods: tuple[PlateStrengthMethod, ...]
    sources: tuple[CalculationSourceSnapshot, ...]
    thickness: PhysicalQuantity
    transverse_span: PhysicalQuantity
    longitudinal_span: PhysicalQuantity | None
    adjusted_shear_property: EndUsePropertyTrace
    adjusted_moduli: tuple[EndUsePropertyTrace, ...]
    eta_lt: Decimal
    eta_branch: ShearEtaBranch
    rupture_nominal_strength: PhysicalQuantity
    buckling_stress: PhysicalQuantity
    buckling_nominal_strength: PhysicalQuantity
    nominal_strength: PhysicalQuantity
    resistance_factor: Decimal
    time_effect_factor: TimeEffectFactor
    design_strength: PhysicalQuantity
    governing_mode: PlateGoverningMode
    property_adjustment_applied_by_engine: bool
    advisories: tuple[PlateStrengthAdvisory, ...]
    result_fingerprint: str


def _quantity_payload(value: PhysicalQuantity | None) -> object:
    if value is None:
        return None
    return {"dimension": value.dimension.value, "canonical": value.canonical_string}


def _property_payload(value: EndUsePropertyTrace) -> object:
    return {
        "kind": value.property_kind.value,
        "source": _quantity_payload(value.source_property),
        "adjusted": _quantity_payload(value.adjusted_property),
        "qualification": value.qualification_status.value,
        "cm": canonical_decimal_string(value.cm),
        "ct": canonical_decimal_string(value.ct),
        "cch": canonical_decimal_string(value.cch),
    }


def _time_payload(value: TimeEffectFactor) -> object:
    return {
        "category": value.category.value,
        "value": canonical_decimal_string(value.value),
        "source": value.source_reference,
        "notes": value.notes,
        "override": value.approved_override_id,
    }


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _require_length(value: PhysicalQuantity, name: str, *, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.LENGTH:
        raise TypeError(f"{name} must be a length quantity.")
    magnitude = value.to(Unit.IN).magnitude
    if magnitude < 0 or (not allow_zero and magnitude == 0):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}.")
    return magnitude


def _require_property(
    value: EndUsePropertyTrace,
    kind: FRPPropertyKind,
    *,
    dimension: Dimension = Dimension.STRESS,
) -> Decimal:
    if not isinstance(value, EndUsePropertyTrace):
        raise TypeError(f"{kind.value} must be an adjusted EndUsePropertyTrace.")
    if value.property_kind is not kind:
        raise ValueError(f"Expected adjusted property {kind.value}.")
    if value.adjusted_property.dimension is not dimension:
        raise ValueError(f"Adjusted property {kind.value} must have dimension {dimension.value}.")
    unit = Unit.ONE if dimension is Dimension.DIMENSIONLESS else Unit.KSI
    magnitude = value.adjusted_property.to(unit).magnitude
    if kind is FRPPropertyKind.NU_LT:
        if magnitude < 0 or magnitude >= 1:
            raise ValueError("nu_LT must be nonnegative and less than one.")
    elif magnitude <= 0:
        raise ValueError(f"Adjusted property {kind.value} must be positive.")
    return magnitude


def _require_time(value: TimeEffectFactor) -> Decimal:
    if not isinstance(value, TimeEffectFactor):
        raise TypeError("time_effect_factor must be a TimeEffectFactor.")
    factor = decimal_value(value.value)
    if factor <= 0:
        raise ValueError("lambda_time must be positive.")
    return factor


def _force_per_length(stress_ksi: Decimal, length_in: Decimal) -> PhysicalQuantity:
    return PhysicalQuantity.of(stress_ksi * length_in, Unit.KIP_PER_IN)


def _design(
    nominal: PhysicalQuantity, phi: Decimal, time_effect_factor: TimeEffectFactor
) -> PhysicalQuantity:
    return nominal * (_require_time(time_effect_factor) * phi)


def _tension_strength(
    *,
    effective_net_area_per_unit_width: PhysicalQuantity,
    adjusted_property: EndUsePropertyTrace,
    expected_kind: FRPPropertyKind,
    coefficient: Decimal,
    method: PlateStrengthMethod,
    section: str,
    equation: str,
    time_effect_factor: TimeEffectFactor,
) -> PlateTensionStrengthResult:
    area = _require_length(
        effective_net_area_per_unit_width,
        "effective_net_area_per_unit_width",
        allow_zero=True,
    )
    strength = _require_property(adjusted_property, expected_kind)
    _require_time(time_effect_factor)
    with localcontext() as context:
        context.prec = PLATE_INTERNAL_DECIMAL_PRECISION
        nominal = _force_per_length(coefficient * strength, area)
        design = _design(nominal, PLATE_TENSION_PHI, time_effect_factor)
    source = asce_74_23_chapter_7_source(section=section, equation_reference=equation)
    payload = {
        "engine": PLATE_STRENGTH_ENGINE_VERSION,
        "method": method.value,
        "geometry": _quantity_payload(effective_net_area_per_unit_width),
        "property": _property_payload(adjusted_property),
        "time": _time_payload(time_effect_factor),
        "phi": canonical_decimal_string(PLATE_TENSION_PHI),
        "nominal": _quantity_payload(nominal),
        "design": _quantity_payload(design),
        "governing": PlateGoverningMode.MATERIAL_RUPTURE.value,
        "property_adjustment_applied_by_engine": False,
    }
    return PlateTensionStrengthResult(
        method,
        source,
        effective_net_area_per_unit_width,
        adjusted_property,
        nominal,
        PLATE_TENSION_PHI,
        time_effect_factor,
        design,
        PlateGoverningMode.MATERIAL_RUPTURE,
        False,
        (),
        _fingerprint(payload),
    )


def plate_longitudinal_tension_strength(
    effective_net_area_per_unit_width: PhysicalQuantity,
    adjusted_ft_l: EndUsePropertyTrace,
    time_effect_factor: TimeEffectFactor,
) -> PlateTensionStrengthResult:
    return _tension_strength(
        effective_net_area_per_unit_width=effective_net_area_per_unit_width,
        adjusted_property=adjusted_ft_l,
        expected_kind=FRPPropertyKind.FT_L,
        coefficient=Decimal("0.7"),
        method=PlateStrengthMethod.LONGITUDINAL_TENSION,
        section="7.5.2",
        equation="7-12",
        time_effect_factor=time_effect_factor,
    )


def plate_transverse_tension_strength(
    effective_net_area_per_unit_width: PhysicalQuantity,
    adjusted_ft_t: EndUsePropertyTrace,
    time_effect_factor: TimeEffectFactor,
) -> PlateTensionStrengthResult:
    return _tension_strength(
        effective_net_area_per_unit_width=effective_net_area_per_unit_width,
        adjusted_property=adjusted_ft_t,
        expected_kind=FRPPropertyKind.FT_T,
        coefficient=Decimal("0.85"),
        method=PlateStrengthMethod.TRANSVERSE_TENSION,
        section="7.5.3",
        equation="7-13",
        time_effect_factor=time_effect_factor,
    )


def _moduli(
    adjusted_e_l: EndUsePropertyTrace,
    adjusted_e_t: EndUsePropertyTrace,
    adjusted_g_lt: EndUsePropertyTrace,
    adjusted_nu_lt: EndUsePropertyTrace,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    return (
        _require_property(adjusted_e_l, FRPPropertyKind.ET_L),
        _require_property(adjusted_e_t, FRPPropertyKind.ET_T),
        _require_property(adjusted_g_lt, FRPPropertyKind.G_LT),
        _require_property(
            adjusted_nu_lt,
            FRPPropertyKind.NU_LT,
            dimension=Dimension.DIMENSIONLESS,
        ),
    )


def plate_longitudinal_compression_strength(
    thickness: PhysicalQuantity,
    transverse_span: PhysicalQuantity,
    adjusted_fc_l: EndUsePropertyTrace,
    adjusted_e_l: EndUsePropertyTrace,
    adjusted_e_t: EndUsePropertyTrace,
    adjusted_g_lt: EndUsePropertyTrace,
    adjusted_nu_lt: EndUsePropertyTrace,
    time_effect_factor: TimeEffectFactor,
    *,
    longitudinal_span: PhysicalQuantity | None = None,
) -> PlateCompressionStrengthResult:
    t = _require_length(thickness, "thickness")
    b = _require_length(transverse_span, "transverse_span")
    a = (
        None
        if longitudinal_span is None
        else _require_length(longitudinal_span, "longitudinal_span")
    )
    fc_l = _require_property(adjusted_fc_l, FRPPropertyKind.FC_L)
    e_l, e_t, g_lt, nu_lt = _moduli(adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt)
    _require_time(time_effect_factor)
    with localcontext() as context:
        context.prec = PLATE_INTERNAL_DECIMAL_PRECISION
        bracket = (
            (Decimal(4) * PLATE_LONGITUDINAL_K_CR - Decimal(3)) * (e_l * e_t).sqrt()
            + PLATE_LONGITUDINAL_K_CR * e_t * nu_lt
            + Decimal(2) * PLATE_LONGITUDINAL_K_CR * g_lt
        )
        buckling_stress_ksi = PLATE_PI**2 / Decimal(6) * (t / b) ** 2 * bracket
        rupture = _force_per_length(fc_l, t)
        buckling = _force_per_length(buckling_stress_ksi, t)
        nominal = min(rupture, buckling)
        governing = (
            PlateGoverningMode.MATERIAL_RUPTURE
            if rupture <= buckling
            else PlateGoverningMode.ORTHOTROPIC_PLATE_BUCKLING
        )
        design = _design(nominal, PLATE_COMPRESSION_PHI, time_effect_factor)
        b_over_t = b / t
        a_over_b = None if a is None else a / b
    advisories = tuple(
        advisory
        for advisory, applies in (
            (PlateStrengthAdvisory.NARROW_PLATE, b_over_t < Decimal(20)),
            (
                PlateStrengthAdvisory.SHORT_COMPRESSION_PLATE,
                a_over_b is not None and a_over_b <= Decimal(4),
            ),
        )
        if applies
    )
    methods = (
        PlateStrengthMethod.LONGITUDINAL_COMPRESSION_RUPTURE,
        PlateStrengthMethod.LONGITUDINAL_BUCKLING_STRENGTH,
        PlateStrengthMethod.LONGITUDINAL_BUCKLING_STRESS,
        PlateStrengthMethod.LONGITUDINAL_KCR,
    )
    sources = tuple(
        asce_74_23_chapter_7_source(section=section, equation_reference=equation)
        for section, equation in (
            ("7.6.2", "7-15"),
            ("7.6.3", "7-17"),
            ("7.6.3", "7-18"),
            ("7.6.3", "7-19"),
        )
    )
    payload = {
        "engine": PLATE_STRENGTH_ENGINE_VERSION,
        "methods": [item.value for item in methods],
        "geometry": {
            "t": _quantity_payload(thickness),
            "b": _quantity_payload(transverse_span),
            "a": _quantity_payload(longitudinal_span),
        },
        "properties": [
            _property_payload(item)
            for item in (
                adjusted_fc_l,
                adjusted_e_l,
                adjusted_e_t,
                adjusted_g_lt,
                adjusted_nu_lt,
            )
        ],
        "k_cr": canonical_decimal_string(PLATE_LONGITUDINAL_K_CR),
        "time": _time_payload(time_effect_factor),
        "phi": canonical_decimal_string(PLATE_COMPRESSION_PHI),
        "rupture": _quantity_payload(rupture),
        "buckling_stress": _quantity_payload(PhysicalQuantity.of(buckling_stress_ksi, Unit.KSI)),
        "buckling": _quantity_payload(buckling),
        "nominal": _quantity_payload(nominal),
        "design": _quantity_payload(design),
        "governing": governing.value,
        "advisories": [item.value for item in advisories],
        "property_adjustment_applied_by_engine": False,
    }
    return PlateCompressionStrengthResult(
        methods,
        sources,
        thickness,
        transverse_span,
        longitudinal_span,
        adjusted_fc_l,
        (adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt),
        PLATE_LONGITUDINAL_K_CR,
        rupture,
        PhysicalQuantity.of(buckling_stress_ksi, Unit.KSI),
        buckling,
        nominal,
        PLATE_COMPRESSION_PHI,
        time_effect_factor,
        design,
        governing,
        b_over_t,
        a_over_b,
        False,
        advisories,
        _fingerprint(payload),
    )


def plate_transverse_compression_rupture_reference(
    thickness: PhysicalQuantity,
    adjusted_fc_t: EndUsePropertyTrace,
    time_effect_factor: TimeEffectFactor,
    *,
    complete_stability_requested: bool = True,
) -> TransverseCompressionReferenceResult:
    if not isinstance(complete_stability_requested, bool):
        raise TypeError("complete_stability_requested must be Boolean.")
    t = _require_length(thickness, "thickness")
    fc_t = _require_property(adjusted_fc_t, FRPPropertyKind.FC_T)
    _require_time(time_effect_factor)
    with localcontext() as context:
        context.prec = PLATE_INTERNAL_DECIMAL_PRECISION
        rupture = _force_per_length(fc_t, t)
        design = _design(rupture, PLATE_COMPRESSION_PHI, time_effect_factor)
    status = (
        PlateStrengthStatus.REQUIRES_SECTION_2_3_2
        if complete_stability_requested
        else PlateStrengthStatus.COMPLETE
    )
    method = PlateStrengthMethod.TRANSVERSE_COMPRESSION_RUPTURE
    source = asce_74_23_chapter_7_source(section="7.6.2", equation_reference="7-16")
    payload = {
        "engine": PLATE_STRENGTH_ENGINE_VERSION,
        "method": method.value,
        "geometry": _quantity_payload(thickness),
        "property": _property_payload(adjusted_fc_t),
        "time": _time_payload(time_effect_factor),
        "phi": canonical_decimal_string(PLATE_COMPRESSION_PHI),
        "rupture": _quantity_payload(rupture),
        "design_reference": _quantity_payload(design),
        "status": status.value,
        "property_adjustment_applied_by_engine": False,
    }
    return TransverseCompressionReferenceResult(
        method,
        source,
        thickness,
        adjusted_fc_t,
        rupture,
        PLATE_COMPRESSION_PHI,
        time_effect_factor,
        design,
        status,
        PlateGoverningMode.MATERIAL_RUPTURE,
        False,
        _fingerprint(payload),
    )


def plate_combined_compression_buckling_strength(
    thickness: PhysicalQuantity,
    longitudinal_span: PhysicalQuantity,
    transverse_span: PhysicalQuantity,
    adjusted_e_l: EndUsePropertyTrace,
    adjusted_e_t: EndUsePropertyTrace,
    adjusted_g_lt: EndUsePropertyTrace,
    adjusted_nu_lt: EndUsePropertyTrace,
    xi_lt: Decimal | int | str,
    time_effect_factor: TimeEffectFactor,
) -> CombinedCompressionBucklingResult:
    t = _require_length(thickness, "thickness")
    a = _require_length(longitudinal_span, "longitudinal_span")
    b = _require_length(transverse_span, "transverse_span")
    xi = decimal_value(xi_lt)
    e_l, e_t, g_lt, nu_lt = _moduli(adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt)
    _require_time(time_effect_factor)
    methods = (
        PlateStrengthMethod.COMBINED_COMPRESSION_BUCKLING_STRENGTH,
        PlateStrengthMethod.COMBINED_COMPRESSION_BUCKLING_STRESS,
        PlateStrengthMethod.COMBINED_COMPRESSION_XI_RANGE,
    )
    sources = tuple(
        asce_74_23_chapter_7_source(section="7.6.4", equation_reference=equation)
        for equation in ("7-20", "7-21", "7-22")
    )
    with localcontext() as context:
        context.prec = PLATE_INTERNAL_DECIMAL_PRECISION
        ratio = b / a
        applicable = Decimal("0.3") <= xi <= Decimal("1.0")
        stress_ksi = None
        nominal = None
        design = None
        if applicable:
            numerator = (
                e_l * ratio**4 + Decimal(2) * (e_t * nu_lt + Decimal(2) * g_lt) * ratio**2 + e_t
            )
            stress_ksi = PLATE_PI**2 / Decimal(12) * (t / b) ** 2 * numerator / (ratio**2 + xi)
            nominal = _force_per_length(stress_ksi, t)
            design = _design(nominal, PLATE_COMPRESSION_PHI, time_effect_factor)
    status = (
        PlateStrengthStatus.COMPLETE if applicable else PlateStrengthStatus.REQUIRES_SECTION_2_3_2
    )
    stress = None if stress_ksi is None else PhysicalQuantity.of(stress_ksi, Unit.KSI)
    payload = {
        "engine": PLATE_STRENGTH_ENGINE_VERSION,
        "methods": [item.value for item in methods],
        "geometry": {
            "t": _quantity_payload(thickness),
            "a": _quantity_payload(longitudinal_span),
            "b": _quantity_payload(transverse_span),
        },
        "xi": canonical_decimal_string(xi),
        "properties": [
            _property_payload(item)
            for item in (adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt)
        ],
        "time": _time_payload(time_effect_factor),
        "phi": canonical_decimal_string(PLATE_COMPRESSION_PHI),
        "status": status.value,
        "stress": _quantity_payload(stress),
        "nominal": _quantity_payload(nominal),
        "design": _quantity_payload(design),
        "property_adjustment_applied_by_engine": False,
    }
    return CombinedCompressionBucklingResult(
        methods,
        sources,
        status,
        thickness,
        longitudinal_span,
        transverse_span,
        xi,
        ratio,
        (adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt),
        stress,
        nominal,
        PLATE_COMPRESSION_PHI,
        time_effect_factor,
        design,
        False,
        _fingerprint(payload),
    )


def plate_in_plane_shear_strength(
    thickness: PhysicalQuantity,
    transverse_span: PhysicalQuantity,
    adjusted_fv_lt: EndUsePropertyTrace,
    adjusted_e_l: EndUsePropertyTrace,
    adjusted_e_t: EndUsePropertyTrace,
    adjusted_g_lt: EndUsePropertyTrace,
    adjusted_nu_lt: EndUsePropertyTrace,
    time_effect_factor: TimeEffectFactor,
    *,
    longitudinal_span: PhysicalQuantity | None = None,
) -> PlateShearStrengthResult:
    t = _require_length(thickness, "thickness")
    b = _require_length(transverse_span, "transverse_span")
    a = (
        None
        if longitudinal_span is None
        else _require_length(longitudinal_span, "longitudinal_span")
    )
    fv_lt = _require_property(adjusted_fv_lt, FRPPropertyKind.FSH_LT)
    e_l, e_t, g_lt, nu_lt = _moduli(adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt)
    _require_time(time_effect_factor)
    with localcontext() as context:
        context.prec = PLATE_INTERNAL_DECIMAL_PRECISION
        eta = (Decimal(2) * g_lt + e_t * nu_lt) / (e_l * e_t).sqrt()
        if eta <= 1:
            branch = ShearEtaBranch.ZERO_LT_ETA_LE_ONE
            buckling_stress_ksi = (
                (Decimal("2.7") + Decimal("1.7") * eta)
                * (t / b) ** 2
                * (e_l * e_t**3).sqrt().sqrt()
            )
        else:
            branch = ShearEtaBranch.ETA_GT_ONE
            buckling_stress_ksi = (
                (Decimal("3.9") + Decimal("0.47") / eta**2)
                * (t / b) ** 2
                * (e_t * (e_t * nu_lt + Decimal(2) * g_lt)).sqrt()
            )
        rupture = _force_per_length(fv_lt, t)
        buckling = _force_per_length(buckling_stress_ksi, t)
        nominal = min(rupture, buckling)
        governing = (
            PlateGoverningMode.MATERIAL_RUPTURE
            if rupture <= buckling
            else PlateGoverningMode.ORTHOTROPIC_SHEAR_BUCKLING
        )
        design = _design(nominal, PLATE_SHEAR_PHI, time_effect_factor)
    advisories = (PlateStrengthAdvisory.SHORT_SHEAR_PLATE,) if a is not None and a < b else ()
    methods = (
        PlateStrengthMethod.SHEAR_RUPTURE,
        PlateStrengthMethod.SHEAR_BUCKLING_STRENGTH,
        PlateStrengthMethod.SHEAR_BUCKLING_STRESS,
        PlateStrengthMethod.SHEAR_BUCKLING_ETA,
    )
    sources = tuple(
        asce_74_23_chapter_7_source(section=section, equation_reference=equation)
        for section, equation in (
            ("7.7.2", "7-24"),
            ("7.7.3", "7-25"),
            ("7.7.3", "7-26"),
            ("7.7.3", "7-27"),
        )
    )
    stress = PhysicalQuantity.of(buckling_stress_ksi, Unit.KSI)
    payload = {
        "engine": PLATE_STRENGTH_ENGINE_VERSION,
        "methods": [item.value for item in methods],
        "geometry": {
            "t": _quantity_payload(thickness),
            "b": _quantity_payload(transverse_span),
            "a": _quantity_payload(longitudinal_span),
        },
        "properties": [
            _property_payload(item)
            for item in (
                adjusted_fv_lt,
                adjusted_e_l,
                adjusted_e_t,
                adjusted_g_lt,
                adjusted_nu_lt,
            )
        ],
        "time": _time_payload(time_effect_factor),
        "phi": canonical_decimal_string(PLATE_SHEAR_PHI),
        "eta": canonical_decimal_string(eta),
        "branch": branch.value,
        "rupture": _quantity_payload(rupture),
        "buckling_stress": _quantity_payload(stress),
        "buckling": _quantity_payload(buckling),
        "nominal": _quantity_payload(nominal),
        "design": _quantity_payload(design),
        "governing": governing.value,
        "advisories": [item.value for item in advisories],
        "property_adjustment_applied_by_engine": False,
    }
    return PlateShearStrengthResult(
        methods,
        sources,
        thickness,
        transverse_span,
        longitudinal_span,
        adjusted_fv_lt,
        (adjusted_e_l, adjusted_e_t, adjusted_g_lt, adjusted_nu_lt),
        eta,
        branch,
        rupture,
        stress,
        buckling,
        nominal,
        PLATE_SHEAR_PHI,
        time_effect_factor,
        design,
        governing,
        False,
        advisories,
        _fingerprint(payload),
    )


__all__ = (
    "PLATE_COMPRESSION_PHI",
    "PLATE_INTERNAL_DECIMAL_PRECISION",
    "PLATE_LONGITUDINAL_K_CR",
    "PLATE_PI",
    "PLATE_SHEAR_PHI",
    "PLATE_STRENGTH_ENGINE_VERSION",
    "PLATE_TENSION_PHI",
    "CombinedCompressionBucklingResult",
    "PlateCompressionStrengthResult",
    "PlateGoverningMode",
    "PlateShearStrengthResult",
    "PlateStrengthAdvisory",
    "PlateStrengthMethod",
    "PlateStrengthStatus",
    "PlateTensionStrengthResult",
    "ShearEtaBranch",
    "TransverseCompressionReferenceResult",
    "plate_combined_compression_buckling_strength",
    "plate_in_plane_shear_strength",
    "plate_longitudinal_compression_strength",
    "plate_longitudinal_tension_strength",
    "plate_transverse_compression_rupture_reference",
    "plate_transverse_tension_strength",
)
