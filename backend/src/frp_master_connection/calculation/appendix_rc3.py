"""Inactive Slice 2 Appendix RC3 successor: printed Theta multiplication only.

No production adapter imports this module. RC2 remains historical authority for
all existing routes pending separate, family-specific migration approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from frp_master_connection.calculation.equations import (
    INTERNAL_DECIMAL_PRECISION,
    EndUsePropertyTrace,
)
from frp_master_connection.calculation.multirow import (
    MaterialDirection,
    PultrudedElementClassification,
)
from frp_master_connection.calculation.multirow_equations import (
    AppendixThetaBranch,
    MultiRowFactorTrace,
    assemble_multirow_resistance,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_value,
)

ENGINE_ID = "asce74-23-ch8-multirow-appendix-corrected-rc3.dev1"
SPEC_ID = "CS2-APPENDIX-RC3"
GOLDEN_ID = "calculation-slice-2-appendix-golden-rc3"
PREDECESSOR_ID = "asce74-23-ch8-multirow-rc2.dev1"
METHOD_ID = "FIRST_ROW_COMMENTARY_FULL_PRINTED_THETA_RC3"


@dataclass(frozen=True, slots=True)
class AppendixRC3Trace:
    """Distinct operator/authority metadata and all executed coefficient values."""

    engine_id: str
    spec_id: str
    golden_id: str
    predecessor_id: str
    method_id: str
    source_equation: str
    source_page: int
    row_count: int
    bolts_per_row: int
    direction: MaterialDirection
    element_classification: PultrudedElementClassification
    width: PhysicalQuantity
    bolt_diameter: PhysicalQuantity
    nominal_hole_diameter: PhysicalQuantity
    thickness: PhysicalQuantity
    unloaded_end_e1: PhysicalQuantity
    gauge: PhysicalQuantity | None
    lbr: Decimal
    spr: Decimal
    theta_branch: AppendixThetaBranch
    theta: Decimal
    c_i: Decimal
    c_op_i: Decimal
    ratio: Decimal
    ratio_times_theta: Decimal
    knt: Decimal
    kop: Decimal
    coefficient_a: Decimal
    coefficient_b: Decimal
    denominator: Decimal
    factor_trace: MultiRowFactorTrace
    retained_policy_notices: tuple[str, ...]


def _positive(quantity: PhysicalQuantity, dimension: Dimension, unit: Unit) -> Decimal:
    if not isinstance(quantity, PhysicalQuantity) or quantity.dimension is not dimension:
        raise ValueError(f"Expected a {dimension.value} PhysicalQuantity.")
    value = quantity.to(unit).magnitude
    if value <= 0:
        raise ValueError("Appendix inputs must be positive.")
    return value


def full_first_row_resistance_rc3(
    width: PhysicalQuantity,
    bolt_diameter: PhysicalQuantity,
    nominal_hole_diameter: PhysicalQuantity,
    thickness: PhysicalQuantity,
    unloaded_end_e1: PhysicalQuantity,
    tensile_property: EndUsePropertyTrace,
    direction: MaterialDirection,
    element_classification: PultrudedElementClassification,
    bolts_per_row: int,
    lbr: Decimal,
    *,
    row_count: int,
    gauge: PhysicalQuantity | None,
    lap_factor_c_lap: Decimal,
    pitch_factor_c_delta: Decimal,
    time_effect_factor_lambda: Decimal,
) -> AppendixRC3Trace:
    """Execute typed QA/explicit successor inputs; infer no geometry or demand.

    Source-valid physical geometry and stress applicability are the caller's
    responsibility. This primitive neither calculates demand nor qualifies a
    design. It cannot execute >3-row extensions or migrate existing adapters.
    """

    for value, allowed in ((row_count, (2, 3)), (bolts_per_row, (1, 2, 3))):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Row and bolt counts must be non-Boolean integers.")
        if value not in allowed:
            raise ValueError("Appendix RC3 supports 2/3 rows and 1/2/3 bolts across width.")
    if not isinstance(direction, MaterialDirection):
        raise TypeError("direction must be MaterialDirection.")
    if not isinstance(element_classification, PultrudedElementClassification):
        raise TypeError("element_classification must be PultrudedElementClassification.")
    if not isinstance(tensile_property, EndUsePropertyTrace):
        raise TypeError("tensile_property must be EndUsePropertyTrace.")
    lbr_value = decimal_value(lbr)
    if not Decimal(0) <= lbr_value <= Decimal(1):
        raise ValueError("Lbr must lie in the inclusive range zero to one.")

    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        w = _positive(width, Dimension.LENGTH, Unit.MM)
        d = _positive(bolt_diameter, Dimension.LENGTH, Unit.MM)
        dn = _positive(nominal_hole_diameter, Dimension.LENGTH, Unit.MM)
        t = _positive(thickness, Dimension.LENGTH, Unit.MM)
        e1 = _positive(unloaded_end_e1, Dimension.LENGTH, Unit.MM)
        ft = _positive(tensile_property.adjusted_property, Dimension.STRESS, Unit.MPA)
        if w <= bolts_per_row * d or w <= bolts_per_row * dn:
            raise ValueError("Full Appendix geometry requires w > n*d and w > n*dn.")
        if bolts_per_row == 1:
            spacing = w
            branch = (
                AppendixThetaBranch.E1_OVER_W_LE_1
                if e1 <= spacing
                else AppendixThetaBranch.E1_OVER_W_GE_1
            )
        else:
            if gauge is None:
                raise ValueError("Two/three bolts across width require gauge.")
            spacing = _positive(gauge, Dimension.LENGTH, Unit.MM)
            branch = (
                AppendixThetaBranch.E1_OVER_G_LE_1
                if e1 <= spacing
                else AppendixThetaBranch.E1_OVER_G_GE_1
            )
        spr = spacing / d
        if spr <= 1:
            raise ValueError("Full Appendix geometry requires Spr > 1.")
        theta = Decimal("1.5") - Decimal("0.5") * spacing / e1 if e1 <= spacing else Decimal(1)
        # Preserve RC2's accepted coefficients, including its documented plate policy.
        c_i = (
            Decimal("0.40")
            if direction is MaterialDirection.LONGITUDINAL
            and element_classification is PultrudedElementClassification.PLATE
            else Decimal("0.50")
        )
        c_op = Decimal("0.50")
        ratio = (spr - 1) / (spr + 1)
        ratio_theta = ratio * theta
        knt = (1 + c_i * (spr - Decimal("1.5") * ratio_theta)) / (w / (bolts_per_row * d) - 1)
        kop = 1 + c_op * (1 + (1 - 1 / spr) ** 3)
        a = knt * w / (bolts_per_row * d)
        b = kop / (1 - bolts_per_row * dn / w)
        denominator = a * lbr_value + b * (1 - lbr_value)
        nominal = w * t * ft / denominator
        phi = Decimal("0.50") if direction is MaterialDirection.LONGITUDINAL else Decimal("0.45")
        factors = assemble_multirow_resistance(
            PhysicalQuantity(nominal, Unit.N),
            (tensile_property,),
            lap_factor_c_lap=lap_factor_c_lap,
            pitch_factor_c_delta=pitch_factor_c_delta,
            resistance_factor_phi=phi,
            time_effect_factor_lambda=time_effect_factor_lambda,
        )
    longitudinal = direction is MaterialDirection.LONGITUDINAL
    equation = (
        ("CA8-2" if longitudinal else "CA8-7")
        if bolts_per_row == 1
        else ("CA8-4" if longitudinal else "CA8-9")
    )
    notices = (
        ("RC2_TRANSVERSE_PLATE_C_T_0_50_CONSERVATIVE_POLICY_RETAINED",)
        if not longitudinal and element_classification is PultrudedElementClassification.PLATE
        else ()
    )
    return AppendixRC3Trace(
        ENGINE_ID,
        SPEC_ID,
        GOLDEN_ID,
        PREDECESSOR_ID,
        METHOD_ID,
        equation,
        112 if equation == "CA8-2" else 113,
        row_count,
        bolts_per_row,
        direction,
        element_classification,
        width,
        bolt_diameter,
        nominal_hole_diameter,
        thickness,
        unloaded_end_e1,
        gauge,
        lbr_value,
        spr,
        branch,
        theta,
        c_i,
        c_op,
        ratio,
        ratio_theta,
        knt,
        kop,
        a,
        b,
        denominator,
        factors,
        notices,
    )
