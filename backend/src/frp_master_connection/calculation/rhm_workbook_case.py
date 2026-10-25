"""Executed positive workbook case with separate historical and corrected streams."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from .quantities import PhysicalQuantity, Unit
from .rhm_reference import (
    PRECISION,
    OptionalComparison,
    ReferenceStream,
    RhmComparison,
    RhmOperand,
    RhmShape,
    StormSetting,
    additive_comparison,
    area_from_reference_lengths,
    bearing_capacity,
    bolt_shear_capacity,
    global_block_capacity,
    local_shear_capacity,
    optional_part_comparison,
    reference_quantity,
    validate_reference_storm,
    workbook_allowable,
)

PRODUCT = "RHM_WORKBOOK_POLYESTER_TABLE"
SAVED_SHEAR = PhysicalQuantity.of("1.048", Unit.KIP)
SAVED_AXIAL = PhysicalQuantity.of("0.566", Unit.KIP)
PREMISES = (
    "Positive V/P, uniform direct loading; no eccentric distribution established",
    "Submitted path lengths: net/gross hole semantics unresolved",
    "Column effective thickness 0.75 in includes selected 0.375-in doubler",
    "Recorded workbook safety factors only; no ASCE or environmental factor inherited",
    "WORKBOOK_REFERENCE only; not actual Angle-to-W coverage or qualification",
)


@dataclass(frozen=True, slots=True)
class WorkbookCase:
    stream: ReferenceStream
    comparisons: tuple[RhmComparison, ...]
    column_summary: Decimal
    summary_cell: str
    optional: tuple[OptionalComparison, ...]
    storm_multiplier: Decimal
    discrepancies: tuple[str, ...]


def execute_workbook_case(
    *,
    stream: ReferenceStream = ReferenceStream.CORRECTED_REFERENCE,
    shear: PhysicalQuantity = SAVED_SHEAR,
    axial: PhysicalQuantity = SAVED_AXIAL,
    storm: StormSetting = StormSetting.NONE,
) -> WorkbookCase:
    """No actions inferred: arguments are declared standalone reference magnitudes."""
    multiplier = validate_reference_storm(stream, storm)
    with localcontext() as context:
        context.prec = PRECISION
        v = reference_quantity(shear, Unit.KIP, zero_allowed=True) * multiplier
        p = reference_quantity(axial, Unit.KIP, zero_allowed=True) * multiplier
        vq, pq = PhysicalQuantity.of(v, Unit.KIP), PhysicalQuantity.of(p, Unit.KIP)
        d, tb, tc = (PhysicalQuantity.of(x, Unit.IN) for x in (".5", ".5", ".75"))
        shape = RhmShape.W_I
        properties = {
            key: workbook_allowable(shape, key, product_id=PRODUCT)
            for key in (
                "WEB_BEARING_CW",
                "WEB_BEARING_LW",
                "WEB_SHEAR_CW",
                "WEB_SHEAR_LW",
                "WEB_TENSION_CW",
                "WEB_TENSION_LW",
                "FLANGE_BEARING_LW",
                "FLANGE_BEARING_CW",
            )
        }
        inputs = (
            RhmOperand("V", vq, "Input!L8; Calcs!D6", "positive transverse reference magnitude"),
            RhmOperand("P", pq, "Input!P19; Calcs!D7", "positive axial reference magnitude"),
            RhmOperand("d", d, "Calcs!D47", "bolt diameter; n=3, one shear plane"),
            RhmOperand("beam_t", tb, "Calcs!D21", "reference effective web thickness"),
            RhmOperand("column_t", tc, "Calcs!D144;D161", "selected doubler included"),
            *tuple(
                RhmOperand(name, PhysicalQuantity.of(value, unit), cell, meaning)
                for name, value, unit, cell, meaning in (
                    ("n", "3", Unit.ONE, "Calcs!D46", "bolt count"),
                    ("bolt_planes", "1", Unit.ONE, "Calcs!D48", "single shear"),
                    ("bolt_Fu", "75", Unit.KSI, "Calcs!F45", "workbook hardware only"),
                    ("bolt_factor", ".17", Unit.ONE, "Calcs!F45", "own explicit factor once"),
                    ("local_planes", "2", Unit.ONE, "Calcs!D59;D70", "shear plane count"),
                    ("local_Lv", "2", Unit.IN, "Calcs!D62", "submitted path: unresolved net/gross"),
                    (
                        "local_Lp",
                        "12",
                        Unit.IN,
                        "Calcs!D73",
                        "submitted path: unresolved net/gross",
                    ),
                    ("global_Lv_V", "8", Unit.IN, "Calcs!D87", "submitted two-shear-length sum"),
                    ("global_Lt_V", "2", Unit.IN, "Calcs!D88", "submitted tension length"),
                    ("global_Lv_P", "24", Unit.IN, "Calcs!D100", "submitted two-shear-length sum"),
                    ("global_Lt_P", "2", Unit.IN, "Calcs!D101", "submitted tension length"),
                )
            ),
            *tuple(
                RhmOperand(
                    key + "_listed",
                    value.listed_stress,
                    value.source_cell,
                    "Original listed stress; not ASCE characteristic or allowable",
                )
                for key, value in properties.items()
            ),
            *tuple(
                RhmOperand(
                    key,
                    value.stress,
                    value.source_cell + ";" + value.factor_cell,
                    "listed stress / own SF=4, exactly once; statistical basis unestablished",
                )
                for key, value in properties.items()
            ),
        )

        def compare(
            method: str,
            demands: tuple[PhysicalQuantity, ...],
            capacities: tuple[PhysicalQuantity, ...],
            cells: tuple[str, ...],
            equation: str,
        ) -> RhmComparison:
            return additive_comparison(
                method,
                demands,
                capacities,
                cells=cells,
                operands=inputs,
                equation=equation,
                assumptions=PREMISES,
            )

        bearing = compare(
            "BEAM_BEARING",
            (vq, pq),
            tuple(
                bearing_capacity(3, d, tb, properties[key])
                for key in ("WEB_BEARING_CW", "WEB_BEARING_LW")
            ),
            ("Calcs!D25", "Calcs!D36", "Calcs!D38"),
            "V/(n d t Fb_CW) + P/(n d t Fb_LW)",
        )
        bolt = compare(
            "BOLT_SHEAR",
            (PhysicalQuantity.of((v * v + p * p).sqrt(), Unit.KIP),),
            (bolt_shear_capacity(3, 1, d, PhysicalQuantity.of("12.75", Unit.KSI)),),
            ("Calcs!F45", "Calcs!D50", "Calcs!D51"),
            "sqrt(V^2+P^2)/(n planes pi d^2/4 Fv); Fv=75 ksi x 0.17",
        )
        local = compare(
            "BEAM_LOCAL",
            tuple(PhysicalQuantity.of(x / 3, Unit.KIP) for x in (v, p)),
            tuple(
                local_shear_capacity(2, PhysicalQuantity.of(length, Unit.IN), tb, properties[key])
                for length, key in (("2", "WEB_SHEAR_CW"), ("12", "WEB_SHEAR_LW"))
            ),
            ("Calcs!D62", "Calcs!D73", "Calcs!D80"),
            "(V/n)/(2 Lv t Fs_CW) + (P/n)/(2 Lp t Fs_LW); uniform reference only",
        )
        global_block = compare(
            "BEAM_GLOBAL",
            (vq, pq),
            tuple(
                global_block_capacity(
                    area_from_reference_lengths(PhysicalQuantity.of(length, Unit.IN), tb),
                    area_from_reference_lengths(PhysicalQuantity.of("2", Unit.IN), tb),
                    properties[skey],
                    properties[tkey],
                )
                for length, skey, tkey in (
                    ("8", "WEB_SHEAR_CW", "WEB_TENSION_CW"),
                    ("24", "WEB_SHEAR_LW", "WEB_TENSION_LW"),
                )
            ),
            ("Calcs!D87", "Calcs!D88", "Calcs!D100", "Calcs!D101", "Calcs!D112"),
            "V/(As_v Fs_CW + At_v Ft_CW) + P/(As_p Fs_LW + At_p Ft_LW)",
        )
        column = compare(
            "COLUMN_BEARING",
            (vq, pq),
            tuple(
                bearing_capacity(3, d, tc, properties[key])
                for key in ("FLANGE_BEARING_LW", "FLANGE_BEARING_CW")
            ),
            ("Calcs!D149", "Calcs!D166", "Calcs!D168"),
            "V/(n d t_eff Fb_LW) + P/(n d t_eff Fb_CW)",
        )
    historical = stream is ReferenceStream.HISTORICAL_REPLICATION
    return WorkbookCase(
        stream,
        (bearing, bolt, local, global_block, column),
        column.components[0] if historical else column.utilization,
        "Summary!C11 -> Calcs!D149" if historical else "Calcs!D168",
        tuple(
            optional_part_comparison(
                key, present=False, transfer_established=False, demand=None, capacity=None
            )
            for key in ("REINFORCING_ANGLE_FASTENERS", "BEAM_DOUBLER_ADHESIVE")
        ),
        multiplier,
        (
            "RHM-01: Summary C11 points to D149, omitting D166",
            "RHM-02: historic 2/3 demand differs from one-third allowable increase explanation",
            "RHM-04: absent angles produced D181 division error and contradictory F195 text",
            "RHM-05: print area ends at row153; corrected review includes D168 and optional rows",
            "RHM-06: unused Dim & Properties H95 #REF is not an engine dependency",
        ),
    )
