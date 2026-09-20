"""Additive ASCE 74-23 Eq. 8-3 interface with independently sourced Fnt AND Fnv.

The historical F593 entry point remains unchanged. This fills only its missing
explicit-Fnv entry seam; it is neither a response solver nor an F593 strength
assignment. Native body area and 60-digit equation convention are retained.
The added stress-only interface works in the source Fnt stress unit. It does
not round-trip a source's exact ksi arithmetic through MPa merely to return
ksi. The force adapter then consumes that result through the existing native
quantity conversion and body-area boundary once.
"""

from __future__ import annotations

from decimal import Decimal, localcontext

from frp_master_connection.calculation.equations import (
    INTERNAL_DECIMAL_PRECISION,
    CombinedBoltTrace,
    bolt_body_area,
)
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit


def sourced_modified_tensile_stress(
    fnt: PhysicalQuantity,
    fnv: PhysicalQuantity,
    required_shear_stress: PhysicalQuantity,
) -> tuple[PhysicalQuantity, PhysicalQuantity]:
    if any(q.dimension is not Dimension.STRESS for q in (fnt, fnv, required_shear_stress)):
        raise ValueError("Eq. 8-3 requires sourced nominal and required stress quantities")
    if (
        fnt.canonical_magnitude <= 0
        or fnv.canonical_magnitude <= 0
        or required_shear_stress.canonical_magnitude < 0
    ):
        raise ValueError("Nominal strengths must be positive; required shear stress is nonnegative")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        ft, fv, vr = (q.to(fnt.unit).magnitude for q in (fnt, fnv, required_shear_stress))
        raw = Decimal("1.3") * ft - ft / (Decimal(".75") * fv) * vr
        modified = min(raw, ft)
    return PhysicalQuantity(raw, fnt.unit), PhysicalQuantity(modified, fnt.unit)


def sourced_combined_bolt_resistance(
    diameter: PhysicalQuantity,
    fnt: PhysicalQuantity,
    fnv: PhysicalQuantity,
    shear_demand: PhysicalQuantity,
) -> CombinedBoltTrace:
    if shear_demand.dimension is not Dimension.FORCE or shear_demand.canonical_magnitude < 0:
        raise ValueError("Required shear demand must be a nonnegative force")
    area_trace = bolt_body_area(diameter)
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        area = area_trace.area.to(Unit.MM2).magnitude
        required = PhysicalQuantity(shear_demand.to(Unit.N).magnitude / area, Unit.MPA)
        raw, modified = sourced_modified_tensile_stress(fnt, fnv, required)
        nominal = PhysicalQuantity(modified.to(Unit.MPA).magnitude * area, Unit.N)
        design = PhysicalQuantity(Decimal(".75") * nominal.magnitude, Unit.N)
    return CombinedBoltTrace(
        area_trace, fnt, fnv, shear_demand, required, Decimal(".75"), raw, modified, nominal, design
    )
