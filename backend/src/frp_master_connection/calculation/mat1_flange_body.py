"""Material-parameterized successor for the frozen flange-body calculation."""

from dataclasses import replace
from decimal import Decimal

from frp_master_connection.calculation.equations import EndUsePropertyTrace
from frp_master_connection.calculation.inputs import (
    EndUseFactors,
    TimeEffectCategory,
    select_time_effect_factor,
)
from frp_master_connection.calculation.multirow_equations import adjusted_property_trace
from frp_master_connection.calculation.plate_strength import (
    plate_longitudinal_compression_strength,
    plate_longitudinal_tension_strength,
)
from frp_master_connection.calculation.properties import FRPPropertyKind, MaterialPropertySnapshot
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    WI_MOMENT_SPLICE_PANEL_METHOD,
    FlangeBodyStatus,
    FlangePlateBodyResult,
    _fingerprint,
    evaluate_flange_plate_body,
)


def evaluate_material_flange_plate_body(
    *,
    component_id: str,
    signed_force: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    clear_body_length: PhysicalQuantity,
    material_snapshot: MaterialPropertySnapshot | None,
    time_effect_category: TimeEffectCategory,
) -> FlangePlateBodyResult:
    """Reuse native strength primitives with one exact material snapshot."""

    if material_snapshot is None or signed_force.canonical_magnitude == 0:
        return evaluate_flange_plate_body(
            component_id=component_id,
            signed_force=signed_force,
            width=width,
            thickness=thickness,
            clear_body_length=clear_body_length,
        )
    factors = EndUseFactors(
        Decimal(1),
        Decimal(1),
        Decimal(1),
        "ASCE/SEI 74-23 Section 2.4.4",
        ("MAT1_ADJUSTED_PROPERTY_INPUT_NO_SECOND_END_USE_FACTOR",),
    )
    time_effect = select_time_effect_factor(time_effect_category)

    def prop(kind: FRPPropertyKind) -> EndUsePropertyTrace:
        entry = material_snapshot.lookup(kind)
        if entry is None:
            raise ValueError(f"MAT1 flange body requires {kind.value}.")
        return adjusted_property_trace(entry, factors)

    tension = None
    compression = None
    if signed_force.canonical_magnitude > 0:
        tension = plate_longitudinal_tension_strength(
            thickness, prop(FRPPropertyKind.FT_L), time_effect
        )
        design = tension.design_strength
        mode = "TENSION"
        advisories: tuple[str, ...] = ()
    else:
        compression = plate_longitudinal_compression_strength(
            thickness,
            width,
            prop(FRPPropertyKind.FC_L),
            prop(FRPPropertyKind.ET_L),
            prop(FRPPropertyKind.ET_T),
            prop(FRPPropertyKind.G_LT),
            prop(FRPPropertyKind.NU_LT),
            time_effect,
            longitudinal_span=clear_body_length,
        )
        design = compression.design_strength
        mode = "COMPRESSION"
        advisories = tuple(item.value for item in compression.advisories)
    capacity = PhysicalQuantity.of(
        design.to(Unit.KIP_PER_IN).magnitude * width.to(Unit.IN).magnitude,
        Unit.KIP,
    )
    utilization = abs(signed_force.canonical_magnitude) / capacity.canonical_magnitude
    status = FlangeBodyStatus.PASS if utilization <= 1 else FlangeBodyStatus.FAIL
    partial = FlangePlateBodyResult(
        component_id,
        signed_force,
        width,
        thickness,
        clear_body_length,
        mode,
        capacity,
        utilization,
        status,
        tension,
        compression,
        advisories,
        WI_MOMENT_SPLICE_PANEL_METHOD,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))
