"""Separate Clip Tee workbook supplement; never an actual Direct calculation.

The fixed saved-example geometry, vinyl-ester table and 316SS groups belong to
this source alone. Resolved normal/sliding operands are saved caches, not a new
eccentric bolt-demand model. Original workbook and public ASCE routes stay intact.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from .quantities import PhysicalQuantity, Unit, decimal_value
from .rhm_reference import (
    PRECISION,
    ReferenceStream,
    RhmComparison,
    RhmOperand,
    additive_comparison,
    bolt_shear_capacity,
    reference_quantity,
)

WORKBOOK_SHA256 = "83caaa73c91953138f333f3b845428c87527690152720f619724cc5700553e2d"
EXTRACTION_SHA256 = "d8ea3ff26765edb116d8e0f767ef20f7041762174a5baf024ec47f3d58064af0"
SOURCE_ID = "RHM_CLIP_TEE_BRACE_CHORD_SUPPLEMENT"
METHOD_VERSION = "RHM-CLIP-TEE-REFERENCE-HYB1-R01"
PREMISES = (
    "Separate W8x3/8 brace and chord, 316SS Clip Tee; not Direct Angle-to-W",
    "Saved resolved normal/sliding force caches; no general eccentric distribution",
    "Six 0.5-in bolts in each distinct brace/stem and Tee/chord group",
    "Source vinyl-ester listed strengths/SF4; statistical basis unestablished",
    "Reference gross path/thickness convention; no invented net-hole or engagement rule",
    "Selected reinforcement credit is workbook-reference only, not qualified transfer",
    "No ASCE replacement, actual coverage, public activation or qualification",
)


def _q(value: Decimal | str, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


@dataclass(frozen=True, slots=True)
class TeeFlangeReference:
    comparison: RhmComparison
    moment: PhysicalQuantity
    section_modulus_in3: Decimal
    bending_stress: PhysicalQuantity
    axial_stress: PhysicalQuantity
    summary: Decimal
    summary_cell: str
    summary_outcome: str


def tee_flange_reference(
    normal: PhysicalQuantity,
    sliding: PhysicalQuantity,
    spacing: PhysicalQuantity,
    length: PhysicalQuantity,
    thickness: PhysicalQuantity,
    width: PhysicalQuantity,
    bending_allowable: PhysicalQuantity,
    axial_allowable: PhysicalQuantity,
    *,
    stream: ReferenceStream,
    operands: tuple[RhmOperand, ...] = (),
) -> TeeFlangeReference:
    """Recorded two-row simple-flange reference; not contact/prying applicability."""
    if not isinstance(stream, ReferenceStream):
        raise TypeError("The Clip Tee reference requires a governed result stream.")
    with localcontext() as context:
        context.prec = PRECISION
        n = reference_quantity(normal, Unit.KIP, zero_allowed=True)
        v = reference_quantity(sliding, Unit.KIP, zero_allowed=True)
        s = reference_quantity(spacing, Unit.IN)
        length_in = reference_quantity(length, Unit.IN)
        t = reference_quantity(thickness, Unit.IN)
        w = reference_quantity(width, Unit.IN)
        fb = reference_quantity(bending_allowable, Unit.KSI)
        fa = reference_quantity(axial_allowable, Unit.KSI)
        moment, modulus = n * s / 4, length_in * t * t / 6
        bending_stress, axial_stress = moment / modulus, v / (w * t)
        comparison = additive_comparison(
            "RHM_CLIP_TEE_FLANGE_COMBINED",
            (normal, sliding),
            (_q(4 * modulus * fb / s, Unit.KIP), _q(w * t * fa, Unit.KIP)),
            cells=("Calcs!D135:D144", "Summary!C14", "Calcs!E144:F144"),
            operands=operands,
            equation="M=N*s/4; S=L*t^2/6; UR=(M/S)/Fb + (V/(w*t))/Fa",
            assumptions=PREMISES,
        )
        historical = stream is ReferenceStream.HISTORICAL_REPLICATION
        summary = comparison.components[0] if historical else comparison.utilization
        return TeeFlangeReference(
            comparison,
            _q(moment, Unit.KIP_IN),
            modulus,
            _q(bending_stress, Unit.KSI),
            _q(axial_stress, Unit.KSI),
            summary,
            "Calcs!D142 (historical Summary C14 and E144/F144)" if historical else "Calcs!D144",
            "PASS" if summary <= 1 else "FAIL",
        )


@dataclass(frozen=True, slots=True)
class ClipTeeWorkbookCase:
    stream: ReferenceStream
    comparisons: tuple[RhmComparison, ...]
    tee_flange: TeeFlangeReference
    operands: tuple[RhmOperand, ...]
    reinforcement_selected: bool
    web_attachment_selected: bool
    web_attachment_state: str
    geometry_identity: str
    source_id: str = SOURCE_ID
    workbook_sha256: str = WORKBOOK_SHA256
    extraction_sha256: str = EXTRACTION_SHA256
    method_version: str = METHOD_VERSION
    source_domain: str = "CLIP_TEE_WORKBOOK_REFERENCE"
    actual_direct_coverage: tuple[str, ...] = ()
    method_adoption: str = "PENDING_OWNER_REVIEW"
    qualification: str = "UNRESOLVED"
    public_activation: bool = False
    original_saved_cache_cells: tuple[tuple[str, str], ...] = (
        ("Calcs!D142", ".40912681878539675"),
        ("Calcs!D144", ".45641351280508674"),
        ("Summary!C14", ".40912681878539675"),
        ("Calcs!D161", "4.6026767113357137"),
        ("Calcs!D177", ".25912324905479034"),
        ("Calcs!D198", "NA"),
        ("Calcs!D213", "NA"),
    )


def execute_clip_tee_reference(
    *,
    stream: ReferenceStream = ReferenceStream.CORRECTED_REFERENCE,
    load_scale: Decimal = Decimal(1),
    reinforcement_selected: bool = True,
    web_attachment_selected: bool = False,
    attachment_transfer_established: bool = False,
) -> ClipTeeWorkbookCase:
    """Execute source arithmetic; optional variants never claim actual method coverage."""
    scale = decimal_value(load_scale)
    if scale < 0:
        raise ValueError("Reference load scale cannot be negative.")
    if any(
        not isinstance(flag, bool)
        for flag in (
            reinforcement_selected,
            web_attachment_selected,
            attachment_transfer_established,
        )
    ):
        raise TypeError("Source reinforcement/attachment predicates must be Boolean.")
    if web_attachment_selected and not reinforcement_selected:
        raise ValueError("Reinforcement-to-web bolts require the selected reinforcing angle.")
    with localcontext() as context:
        context.prec = PRECISION
        force = _q(5 * scale, Unit.KIP)
        normal = _q(Decimal("3.2139380484326963") * scale, Unit.KIP)
        sliding = _q(Decimal("3.83022221559489") * scale, Unit.KIP)
        operands = tuple(
            RhmOperand(name, _q(value, unit), cell, meaning)
            for name, value, unit, cell, meaning in (
                (
                    "brace_force",
                    str(5 * scale),
                    Unit.KIP,
                    "Calcs!D7",
                    "source load, not factored Direct result",
                ),
                (
                    "normal",
                    str(normal.magnitude),
                    Unit.KIP,
                    "Calcs!D8;D131",
                    "saved SIN(40deg) resolution cache scaled explicitly",
                ),
                (
                    "sliding",
                    str(sliding.magnitude),
                    Unit.KIP,
                    "Calcs!D9;D139",
                    "saved COS(40deg) resolution cache scaled explicitly",
                ),
                (
                    "angle",
                    "40",
                    Unit.ONE,
                    "Input!Q28",
                    "degrees; no independent trig recalculation here",
                ),
                ("web_t", ".375", Unit.IN, "Calcs!D21", "W8x3/8 brace; no selected web doubler"),
                ("stem_t", ".375", Unit.IN, "Calcs!D86", "316SS Tee stem"),
                (
                    "flange_t",
                    ".375",
                    Unit.IN,
                    "Calcs!D129;D155",
                    "distinct Tee and chord flange thicknesses",
                ),
                ("spacing", "3.625", Unit.IN, "Calcs!D130", "opposite-side flange bolt rows"),
                ("length", "9", Unit.IN, "Calcs!D132", "source effective flange length only"),
                ("width", "8", Unit.IN, "Calcs!D133", "source Tee flange width"),
                (
                    "reinforcement_t",
                    ".375",
                    Unit.IN,
                    "Calcs!D173",
                    "selected source 316SS angle; no automatic transfer credit",
                ),
                (
                    "reinforcement_arm",
                    "1.25",
                    Unit.IN,
                    "Calcs!D167",
                    "actual source reinforcing-leg moment arm",
                ),
                (
                    "reinforcement_Fb",
                    "33.75",
                    Unit.KSI,
                    "Calcs!D166",
                    "0.75 times source 316SS Fy=45 ksi",
                ),
                (
                    "chord_t",
                    ".375",
                    Unit.IN,
                    "Calcs!D155;D226",
                    "W8x3/8 chord flange, no selected flange doubler",
                ),
                ("edge", "1.5", Unit.IN, "Calcs!D47;D106", "submitted gross reference length"),
                ("brace_Lv", "7", Unit.IN, "Calcs!D56", "two submitted 3.5-in shear lengths"),
                (
                    "brace_Lt",
                    "4",
                    Unit.IN,
                    "Calcs!D57",
                    "global block term; not separate net tension",
                ),
                ("tee_Lv", "8", Unit.IN, "Calcs!D114", "two submitted 4-in shear lengths"),
                ("tee_Lt", "4", Unit.IN, "Calcs!D115", "submitted stem tension length"),
                ("bolt_d", ".5", Unit.IN, "Calcs!D20;D89;D238", "each source attachment group"),
                (
                    "brace_bolts",
                    "6",
                    Unit.ONE,
                    "Input!F42",
                    "brace-to-Tee group; uniform premise only",
                ),
                (
                    "flange_bolts",
                    "6",
                    Unit.ONE,
                    "Input!R22",
                    "Tee-to-chord flange group; separate identity",
                ),
                (
                    "FRP_listed_bearing",
                    "30",
                    Unit.KSI,
                    "Dim & Properties!D95",
                    "vinyl-ester source table, statistical basis unestablished",
                ),
                (
                    "FRP_SF",
                    "4",
                    Unit.ONE,
                    "Dim & Properties!D96",
                    "source factor once; not universal material policy",
                ),
                ("FRP_bearing", "7.5", Unit.KSI, "Dim & Properties!D97", "30/4 source allowable"),
                (
                    "FRP_shear",
                    "1.125",
                    Unit.KSI,
                    "Dim & Properties!D109",
                    "4.5/4 source allowable; D107/D108",
                ),
                (
                    "FRP_tension",
                    "7.5",
                    Unit.KSI,
                    "Dim & Properties!D103",
                    "30/4 source allowable; D101/D102",
                ),
                (
                    "FRP_flange_Fb",
                    "3",
                    Unit.KSI,
                    "Dim & Properties!D94",
                    "12/4 CW source flexural allowable",
                ),
                (
                    "Tee_Fy",
                    "45",
                    Unit.KSI,
                    "Dim & Properties!G53;G54",
                    "316SS source value; not current hardware/catalog authority",
                ),
                ("Tee_Fb", "33.75", Unit.KSI, "Calcs!D134", "0.75 times source Fy"),
                ("Tee_Fa", "27", Unit.KSI, "Calcs!D138", "0.6 times source Fy"),
                ("stem_Fbrg", "40.5", Unit.KSI, "Calcs!D90", "0.9 times source Fy"),
                (
                    "stem_Fv_Ft",
                    "18",
                    Unit.KSI,
                    "Calcs!D108;D118;D121",
                    "0.4 times source Fy, both terms exactly as source",
                ),
                (
                    "bolt_Fu",
                    "75",
                    Unit.KSI,
                    "Dim & Properties!F63;F66",
                    "source 316SS; not F593 catalog replacement",
                ),
                ("bolt_Fv", "12.75", Unit.KSI, "Calcs!F33;F236", "0.17 times source Fu once"),
                ("bolt_Ft", "24.75", Unit.KSI, "Calcs!D243", "0.33 times source Fu once"),
            )
        )

        def compare(
            name: str,
            demands: tuple[PhysicalQuantity, ...],
            capacities: tuple[PhysicalQuantity, ...],
            cells: tuple[str, ...],
            equation: str,
        ) -> RhmComparison:
            return additive_comparison(
                "RHM_CLIP_TEE_" + name,
                demands,
                capacities,
                cells=cells,
                operands=operands,
                equation=equation,
                assumptions=PREMISES,
            )

        shear_capacity = bolt_shear_capacity(6, 1, _q(".5", Unit.IN), _q("12.75", Unit.KSI))
        t = Decimal(".375")
        diameter = Decimal(".5")
        bearing_area = 6 * diameter * t
        comparisons = [
            compare(
                "BRACE_BEARING",
                (force,),
                (_q(bearing_area * Decimal("7.5"), Unit.KIP),),
                ("Calcs!D23:D25",),
                "n*d*t*Fb = 6*.5*.375*7.5",
            ),
            compare(
                "BRACE_BOLT_SHEAR",
                (force,),
                (shear_capacity,),
                ("Calcs!D37:D39",),
                "6*pi*d^2/4*1*Fv",
            ),
            compare(
                "BRACE_LOCAL",
                (_q(force.magnitude / 6, Unit.KIP),),
                (_q(2 * Decimal("1.5") * t * Decimal("1.125"), Unit.KIP),),
                ("Calcs!D46:D52",),
                "(P/6)/(2*e*t*Fs); uniform source-only premise",
            ),
            compare(
                "BRACE_GLOBAL",
                (force,),
                (_q(7 * t * Decimal("1.125") + 4 * t * Decimal("7.5"), Unit.KIP),),
                ("Calcs!D59:D66",),
                "P/(7*.375*1.125 + 4*.375*7.5); no separate net-tension check",
            ),
            compare(
                "STEM_BEARING",
                (force,),
                (_q(bearing_area * Decimal("40.5"), Unit.KIP),),
                ("Calcs!D90:D93",),
                "P/(6*.5*.375*40.5)",
            ),
            compare(
                "STEM_LOCAL",
                (_q(force.magnitude / 6, Unit.KIP),),
                (_q(2 * Decimal("1.5") * t * 18, Unit.KIP),),
                ("Calcs!D105:D110",),
                "(P/6)/(2*1.5*.375*18)",
            ),
            compare(
                "STEM_GLOBAL",
                (force,),
                (_q(8 * t * 18 + 4 * t * 18, Unit.KIP),),
                ("Calcs!D117:D124",),
                "P/(8*.375*18 + 4*.375*18)",
            ),
        ]
        flange = tee_flange_reference(
            normal,
            sliding,
            _q("3.625", Unit.IN),
            _q("9", Unit.IN),
            _q(".375", Unit.IN),
            _q("8", Unit.IN),
            _q("33.75", Unit.KSI),
            _q("27", Unit.KSI),
            stream=stream,
            operands=operands,
        )
        comparisons.append(flange.comparison)
        frp_capacity = Decimal(9) * Decimal(".375") ** 2 / 6 * 3
        if reinforcement_selected:
            reinforcement_capacity = Decimal(9) * Decimal(".375") ** 2 / 6 * Decimal("33.75")
            chord_demand = normal.magnitude / 2 * Decimal("1.25")
            chord_capacity = frp_capacity + reinforcement_capacity
            chord_cells = ("Calcs!D167:D177",)
            chord_equation = (
                "(N/2*1.25)/(FRP_S*3 + reinforcement_S*33.75); selected source reinforcement only"
            )
            sliding_capacity = Decimal(6) * Decimal(".5") * Decimal(".375") * Decimal("40.5")
        else:
            chord_demand = normal.magnitude * Decimal("3.625") / 4
            chord_capacity = frp_capacity
            chord_cells = ("Calcs!D151:D161",)
            chord_equation = (
                "(N*3.625/4)/(FRP_S*3); fresh unreinforced reference, zero reinforcement credit"
            )
            sliding_capacity = Decimal(0)
        chord_ratio = chord_demand / chord_capacity
        comparisons.append(
            RhmComparison(
                "RHM_CLIP_TEE_CHORD_FLANGE",
                chord_cells,
                (
                    *operands,
                    RhmOperand(
                        "chord_moment",
                        _q(chord_demand, Unit.KIP_IN),
                        "Calcs!D158;D171",
                        "source-specific moment; not a force",
                    ),
                ),
                (_q(chord_capacity, Unit.KIP_IN),),
                (chord_ratio,),
                chord_ratio,
                "PASS" if chord_ratio <= 1 else "FAIL",
                chord_equation,
                PREMISES,
            )
        )
        comparisons.append(
            compare(
                "CHORD_SLIDING",
                (sliding,),
                (_q(sliding_capacity + bearing_area * Decimal("7.5"), Unit.KIP),),
                ("Calcs!D217:D231",),
                "V/(selected reinforcing bearing + FRP chord flange bearing)",
            )
        )
        tensile_capacity = bolt_shear_capacity(6, 1, _q(".5", Unit.IN), _q("24.75", Unit.KSI))
        comparisons.append(
            compare(
                "FLANGE_BOLT_COMBINED",
                (sliding, normal),
                (shear_capacity, tensile_capacity),
                ("Calcs!D240:D248",),
                "V/(n*pi*d^2/4*Fv) + N/(n*pi*d^2/4*Ft); distinct Tee-to-chord group",
            )
        )
        if not web_attachment_selected:
            attachment_state = "INACTIVE_SOURCE_OPTION; NO_CHORD_WEB_OR_JUNCTION_COVERAGE"
        elif not attachment_transfer_established:
            attachment_state = "INCOMPLETE; ACTIVE_REINFORCEMENT_TRANSFER_UNESTABLISHED"
        else:
            attachment_state = "REFERENCE_ONLY; DECLARED_SOURCE_TRANSFER_PREMISE_NOT_QUALIFICATION"
            comparisons.append(
                compare(
                    "WEB_ATTACHMENT_BEARING",
                    (normal, sliding),
                    (
                        _q(bearing_area * Decimal("6.6"), Unit.KIP),
                        _q(bearing_area * Decimal("7.5"), Unit.KIP),
                    ),
                    ("Calcs!D186:D198",),
                    "N/(6*.5*.375*6.6) + V/(6*.5*.375*7.5)",
                )
            )
            comparisons.append(
                compare(
                    "WEB_ATTACHMENT_BOLT",
                    (force,),
                    (bolt_shear_capacity(6, 2, _q(".5", Unit.IN), _q("12.75", Unit.KSI)),),
                    ("Calcs!D205:D213",),
                    "P/(6*2*pi*d^2/4*Fv); optional reinforcement-to-web group",
                )
            )
        return ClipTeeWorkbookCase(
            stream,
            tuple(comparisons),
            flange,
            operands,
            reinforcement_selected,
            web_attachment_selected,
            attachment_state,
            "CLIP_TEE_W8_SOURCE_REINFORCED"
            if reinforcement_selected
            else "CLIP_TEE_W8_UNREINFORCED_FRESH_REFERENCE",
        )
