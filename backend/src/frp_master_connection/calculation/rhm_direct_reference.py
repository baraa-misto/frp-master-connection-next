"""Source-specific Direct L4/I8 reference, inactive and independent of public engines.

Geometry is in the connection plane: x right, y up, brace u=(cos(phi),-sin(phi)).
All source lengths remain center-derived, with unresolved gross/effective convention.
No first-row, opposite-side or junction coverage is inferred from these equations.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from .quantities import PhysicalQuantity, Unit, decimal_value
from .rhm_reference import (
    PI,
    PRECISION,
    ReferenceStream,
    RhmComparison,
    RhmOperand,
    additive_comparison,
    bolt_shear_capacity,
    reference_quantity,
)

SOURCE_SHA256 = "1dcfa90eb1e33101e350b41760b13f6d2f7f87225191e11145362c35f8121e83"
SOURCE_ID = "RHM_DIRECT_L4_I8_ONE_SIDED"
METHOD_VERSION = "HYB2-D1-R1-REFERENCE"


class DirectCandidateStream(StrEnum):
    """Direct-only owner correction; the historical/beam/Tee streams stay distinct."""

    CORRECTED_SOURCE_CANDIDATE = "CORRECTED_SOURCE_CANDIDATE"


def q(value: Decimal | str, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def sincos(phi: Decimal) -> tuple[Decimal, Decimal]:
    """Deterministic Decimal trigonometry; precision is arithmetic, not a fit tolerance."""
    phi = decimal_value(phi)
    if not 0 < phi < 90:
        raise ValueError("Direct reference requires 0 < phi < 90 degrees.")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        x = phi * PI / 180
        sine = ts = x
        cosine = tc = Decimal(1)
        for k in range(1, 90):
            ts *= -x * x / (2 * k * (2 * k + 1))
            tc *= -x * x / ((2 * k - 1) * 2 * k)
            sine += ts
            cosine += tc
        return +sine, +cosine


_LENGTH_DEFAULTS = {value: q(value) for value in ("2", ".4375", "1", ".5", ".375", ".563", "4")}


@dataclass(frozen=True, slots=True)
class DirectGeometry:
    phi: Decimal = Decimal("30.9")
    d_span: PhysicalQuantity = _LENGTH_DEFAULTS["2"]
    xb: PhysicalQuantity = _LENGTH_DEFAULTS[".4375"]
    xc: PhysicalQuantity = _LENGTH_DEFAULTS["1"]
    brace_thickness: PhysicalQuantity = _LENGTH_DEFAULTS[".5"]
    column_thickness: PhysicalQuantity = _LENGTH_DEFAULTS[".375"]
    diameter: PhysicalQuantity = _LENGTH_DEFAULTS[".5"]
    # A report-side explicit hole inventory, NOT an original workbook operand.
    hole: PhysicalQuantity = _LENGTH_DEFAULTS[".563"]
    brace_v_length: PhysicalQuantity = _LENGTH_DEFAULTS["1"]
    brace_leg: PhysicalQuantity = _LENGTH_DEFAULTS["4"]
    column_flange: PhysicalQuantity = _LENGTH_DEFAULTS["4"]

    def __post_init__(self) -> None:
        sincos(self.phi)
        for value in (
            self.d_span,
            self.xb,
            self.xc,
            self.brace_thickness,
            self.column_thickness,
            self.diameter,
            self.hole,
            self.brace_v_length,
            self.brace_leg,
            self.column_flange,
        ):
            reference_quantity(value, Unit.IN)
        if self.hole.to(Unit.IN).magnitude < self.diameter.to(Unit.IN).magnitude:
            raise ValueError("Physical hole cannot be smaller than bolt diameter.")
        if self.brace_thickness >= self.brace_leg or self.column_thickness >= self.column_flange:
            raise ValueError("Invalid physical section thickness exceeds its outer dimension.")


@dataclass(frozen=True, slots=True)
class DirectPathGeometry:
    vertical_spacing: PhysicalQuantity
    bolt_centers: tuple[tuple[Decimal, Decimal], ...]
    lengths: tuple[tuple[str, PhysicalQuantity], ...]
    hole_inventory: tuple[str, ...]
    minimum_center_edge: PhysicalQuantity
    fit: bool
    interpretation: str = "CENTER_DERIVED_SOURCE_LENGTHS_NOT_ESTABLISHED_NET_AREAS"


def source_paths(g: DirectGeometry) -> DirectPathGeometry:
    """Fresh support-aligned source lengths and nominal hole containment in both members.

    x=-Xb is the candidate brace cut datum; x=Xc is the near column free edge.
    Xb's fabrication datum needs review: its source recipe contains 0.375 even though
    the actual brace thickness is 0.5. No thickness or datum substitution is made.
    """
    with localcontext() as ctx:
        ctx.prec = PRECISION
        s, c = sincos(g.phi)
        span, xb, xc = (a.to(Unit.IN).magnitude for a in (g.d_span, g.xb, g.xc))
        spacing, lp_b, lp_c, lv_c, lt_v = span / c, xb / c, xc / c, xc / s, span * s
        pairs = (spacing, spacing, lp_c, lp_b, lp_c, lp_b, lv_c, lv_c, lt_v, lt_v)
        lengths = tuple(
            (cell, q(v))
            for cell, v in zip(
                ("L52", "L53", "L54", "L55", "L56", "L57", "L60", "L63", "L64", "L65"),
                pairs,
                strict=True,
            )
        )
        edge = min(
            xb,
            xc,
            g.column_flange.to(Unit.IN).magnitude - xc,
            g.brace_leg.to(Unit.IN).magnitude - span - g.brace_v_length.to(Unit.IN).magnitude,
            g.brace_v_length.to(Unit.IN).magnitude,
        )
        return DirectPathGeometry(
            q(spacing),
            ((Decimal(0), spacing / 2), (Decimal(0), -spacing / 2)),
            lengths,
            ("BRACE:B1", "BRACE:B2", "COLUMN:B1", "COLUMN:B2"),
            q(edge),
            edge >= g.hole.to(Unit.IN).magnitude / 2 and spacing >= g.hole.to(Unit.IN).magnitude,
        )


@dataclass(frozen=True, slots=True)
class RotationComparison:
    bolt_centers: tuple[tuple[Decimal, Decimal], ...]
    brace_cut_distances_x: tuple[Decimal, ...]
    column_edge_distances_x: tuple[Decimal, ...]
    brace_p_paths: tuple[Decimal, ...]
    column_p_paths: tuple[Decimal, ...]
    column_v_paths: tuple[Decimal, ...]
    nominal_fit: bool
    disposition: str = "SEPARATELY_DERIVED_GEOMETRY_ONLY_NO_INHERITED_RESULTS"


def brace_rotation(g: DirectGeometry) -> RotationComparison:
    """Rotate the pair about its centroid, preserving spacing and source boundary datums.

    A changed pair is not the source structural contract. Negative paths are retained
    as no-fit evidence, never converted to capacities or hidden with abs().
    """
    with localcontext() as ctx:
        ctx.prec = PRECISION
        s, c = sincos(g.phi)
        spacing = source_paths(g).vertical_spacing.to(Unit.IN).magnitude
        h = spacing / 2
        # spacing*cos(phi)=d_span exactly by definition. Retain that exact datum.
        half_span = g.d_span.to(Unit.IN).magnitude / 2
        bolts = ((-half_span, h * s), (half_span, -h * s))
        xb, xc, width = (v.to(Unit.IN).magnitude for v in (g.xb, g.xc, g.column_flange))
        b = tuple(x + xb for x, _ in bolts)
        col = tuple(xc - x for x, _ in bolts)
        far = tuple(x - (xc - width) for x, _ in bolts)
        lvb = g.brace_v_length.to(Unit.IN).magnitude
        fit = (
            min(
                *b, *col, *far, half_span + lvb, g.brace_leg.to(Unit.IN).magnitude - half_span - lvb
            )
            >= g.hole.to(Unit.IN).magnitude / 2
            and spacing >= g.hole.to(Unit.IN).magnitude
        )
        return RotationComparison(
            bolts,
            b,
            col,
            tuple(v / c for v in b),
            tuple(v / c for v in col),
            tuple(v / s for v in col),
            fit,
        )


@dataclass(frozen=True, slots=True)
class MomentWitness:
    moment_in_lb: Decimal
    historical_v_addition_lb: Decimal
    historical_p_addition_lb: Decimal
    corrected_link_p_addition_lb: Decimal
    equilibrium_bolt_forces_lb: tuple[tuple[Decimal, Decimal], ...]
    reconstructed_force_lb: tuple[Decimal, Decimal]
    reconstructed_moment_in_lb: Decimal
    applicability: str = "REFERENCE_EQUILIBRIUM_ONLY_SCALAR_SOURCE_ENVELOPE_NOT_ADOPTED"


def moment_witness(
    geometry: DirectGeometry, fx: PhysicalQuantity, fy: PhysicalQuantity, moment: PhysicalQuantity
) -> MomentWitness:
    """Independent equal-stiffness planar pair equilibrium, not a FRP stress-transfer law.

    At y=+/-h, qx=Fx/2-M*y/(2h^2), qy=Fy/2. Sum r cross q=M.
    The workbook's simultaneous scalar P/V additions are not this vector solution.
    """
    with localcontext() as ctx:
        ctx.prec = PRECISION
        x, y, m = (
            fx.to(Unit.LBF).magnitude,
            fy.to(Unit.LBF).magnitude,
            moment.to(Unit.LBF_IN).magnitude,
        )
        spacing = source_paths(geometry).vertical_spacing.to(Unit.IN).magnitude
        forces = ((x / 2 - m / spacing, y / 2), (x / 2 + m / spacing, y / 2))
        return MomentWitness(
            m,
            2 * m / spacing,
            Decimal(0),
            2 * m / spacing,
            forces,
            (forces[0][0] + forces[1][0], forces[0][1] + forces[1][1]),
            spacing / 2 * (forces[1][0] - forces[0][0]),
        )


@dataclass(frozen=True, slots=True)
class DirectSourceCase:
    stream: ReferenceStream | DirectCandidateStream
    geometry: DirectGeometry
    paths: DirectPathGeometry
    comparisons: tuple[RhmComparison, ...]
    source_summary: tuple[tuple[str, Decimal], ...]
    factor_ledger: tuple[str, ...]
    bolt_status: str
    original_literal_e46: str
    optional_state: str
    source_hash: str = SOURCE_SHA256
    basis: str = "ASD_SOURCE_REFERENCE_ONLY"
    coverage: str = "NOT_ESTABLISHED"
    qualification: str = "SECTION_2_3_2_UNRESOLVED"
    public_activation: bool = False


_SAVED_GEOMETRY = DirectGeometry()
_SAVED_SHEAR = q("13.4", Unit.LBF)
_SAVED_AXIAL = q("91.55", Unit.LBF)


def execute_direct_source(
    *,
    geometry: DirectGeometry = _SAVED_GEOMETRY,
    shear: PhysicalQuantity = _SAVED_SHEAR,
    axial: PhysicalQuantity = _SAVED_AXIAL,
    stream: ReferenceStream = ReferenceStream.CORRECTED_REFERENCE,
    temperature_f: int = 100,
    reinforcement: bool = False,
) -> DirectSourceCase:
    """Seven unique comparisons, eight historical summary locators, one physical bolt group.

    Bounded reference variations: acute angle, positive center-derived paths/thicknesses,
    two contained holes, polyester table temperatures. No reinforcement branch exists.
    Finite moments/sign reversal require separate demand/path adoption and are not inputs.
    """
    if not isinstance(stream, ReferenceStream) or not isinstance(reinforcement, bool):
        raise TypeError("Typed reference stream and Boolean reinforcement state required.")
    if reinforcement:
        raise ValueError("Active reinforcement is unsupported; missing transfer is not N/A.")
    temperatures = {75: "1", 90: ".91", 100: ".85", 125: ".7", 135: ".62", 150: ".5"}
    if isinstance(temperature_f, bool) or temperature_f not in temperatures:
        raise ValueError(
            "Use a positive supplied polyester temperature-table point, no interpolation."
        )
    paths = source_paths(geometry)
    if not paths.fit:
        raise ValueError(
            "Invalid physical geometry: holes overlap or a source hole is outside "
            "a real member boundary."
        )
    with localcontext() as ctx:
        ctx.prec = PRECISION
        v, p = (reference_quantity(a, Unit.KIP, zero_allowed=True) for a in (shear, axial))
        t = Decimal(temperatures[temperature_f])
        tb, tc, db, lvb = (
            a.to(Unit.IN).magnitude
            for a in (
                geometry.brace_thickness,
                geometry.column_thickness,
                geometry.diameter,
                geometry.brace_v_length,
            )
        )
        lengths = {k: val.to(Unit.IN).magnitude for k, val in paths.lengths}
        # Source listed strengths/SF4, then its own temperature factor. No ASCE factors.
        fs, fl, ft, bcw, blw = (Decimal(x) / 4 * t for x in ("4.5", "30", "10", "18", "30"))
        r_bv, r_bp = 2 * lvb * tb * fs, 2 * lengths["L55"] * tb * fs
        r_cv, r_cp = 2 * lengths["L60"] * tc * fs, 2 * lengths["L54"] * tc * fs
        bolt = bolt_shear_capacity(2, 1, geometry.diameter, q("12.75", Unit.KSI))
        ledger = (
            "Dim & Properties: listed stresses / SF4; statistical/product adoption unestablished",
            f"Calcs!D10: POLYESTER {temperature_f}F Ts={t}; no storm relief",
            "Calcs!D31: LW brace bearing Ts applied twice; preserved source policy",
            "Calcs!D221: CW column tensile term Ts applied twice; preserved source policy",
            "Calcs!F13: receiving flange CW bearing/shear choice retained as source assumption",
            "Calcs!F40/F153=12.75 ksi 316SS included-thread fixed reference, one group",
            (
                "Center-derived lengths; gross/net/effective/hole convention "
                "unresolved; no net-area claim"
            ),
            "Xb=1-.1875-.375=.4375 source recipe; actual brace thickness remains .5",
        )
        operands = tuple(
            RhmOperand(name, val, cell, meaning)
            for name, val, cell, meaning in (
                ("V", shear, "Input!L49", "positive shear magnitude in supplied source direction"),
                ("P", axial, "Input!L48", "positive tension in supplied source direction"),
                (
                    "t_brace",
                    geometry.brace_thickness,
                    "Dim & Properties!G66",
                    "actual Angle .5, not Xb's .375 term",
                ),
                (
                    "t_column",
                    geometry.column_thickness,
                    "Dim & Properties!G61",
                    "unreinforced flange",
                ),
                ("bolt_d", geometry.diameter, "Input!S24", "two single-shear bolts, shared group"),
                ("n", q("2", Unit.ONE), "Input!S23", "one shared physical group"),
                ("shear_planes", q("1", Unit.ONE), "Calcs!D43", "single shear"),
                (
                    "Ts",
                    q(t, Unit.ONE),
                    "Calcs!D10",
                    "source polyester table, independent of ASCE CT",
                ),
                ("SF", q("4", Unit.ONE), "Dim & Properties!D83;D92;D101;F104", "source listed / 4"),
                (
                    "brace_bearing_CW_allowable_before_Ts",
                    q("4.5", Unit.KSI),
                    "Dim & Properties!F105",
                    "18000 psi / 4",
                ),
                (
                    "brace_bearing_LW_allowable_before_Ts",
                    q("7.5", Unit.KSI),
                    "Dim & Properties!D102",
                    "30000 psi / 4; D31 Ts twice",
                ),
                (
                    "brace_tension_LW_allowable_before_Ts",
                    q("7.5", Unit.KSI),
                    "Dim & Properties!F108",
                    "30000 psi / 4",
                ),
                (
                    "brace_tension_CW_allowable_before_Ts",
                    q("2.5", Unit.KSI),
                    "Dim & Properties!F111",
                    "10000 psi / 4; stale LW label corrected",
                ),
                (
                    "brace_shear_LW_CW_allowable_before_Ts",
                    q("1.125", Unit.KSI),
                    "Dim & Properties!D114;F114;F117",
                    "4500 psi / 4; source values equal, distinct axes retained",
                ),
                (
                    "column_bearing_CW_allowable_before_Ts",
                    q("4.5", Unit.KSI),
                    "Dim & Properties!D84",
                    "18000 psi / 4; F13 source simplification",
                ),
                (
                    "column_shear_CW_allowable_before_Ts",
                    q("1.125", Unit.KSI),
                    "Dim & Properties!D93",
                    "4500 psi / 4",
                ),
                (
                    "column_tension_CW_allowable_before_Ts",
                    q("2.5", Unit.KSI),
                    "Dim & Properties!D111",
                    "10000 psi / 4; D221 Ts twice",
                ),
                (
                    "bolt_allowable",
                    q("12.75", Unit.KSI),
                    "Calcs!F40;F153",
                    "source 316SS fixed included-thread allowable; no F593 substitution",
                ),
            )
        )

        def compare(
            key: str,
            cell: str,
            demands: tuple[Decimal, ...],
            capacities: tuple[Decimal, ...],
            equation: str,
        ) -> RhmComparison:
            return additive_comparison(
                key,
                tuple(q(a, Unit.KIP) for a in demands),
                tuple(q(a, Unit.KIP) for a in capacities),
                cells=(cell,),
                operands=operands,
                equation=equation,
                assumptions=ledger,
            )

        checks = (
            compare(
                "DIRECT_BRACE_BEARING",
                "Calcs!D34",
                (v, p),
                (2 * db * tb * bcw, 2 * db * tb * blw * t),
                "V/(n*d*t*FbCW*Ts)+P/(n*d*t*FbLW*Ts^2)",
            ),
            compare(
                "DIRECT_SHARED_BOLTS",
                "Calcs!D46;D159",
                ((v * v + p * p).sqrt(),),
                (bolt.to(Unit.KIP).magnitude,),
                "sqrt(P^2+V^2)/(n*pi*d^2/4*12.75 ksi); same group once",
            ),
            compare(
                "DIRECT_BRACE_LOCAL",
                "Calcs!D53:D75",
                (v / 2, p / 2),
                (r_bv, r_bp),
                "(V/n)/(2*LvV*t*FsCW*Ts)+(P/n)/(2*LvP*t*FsLW*Ts)",
            ),
            compare(
                "DIRECT_BRACE_GLOBAL",
                "Calcs!D93:D121",
                (v, p),
                (r_bv + lengths["L64"] * tb * ft, r_bp + lengths["L53"] * tb * fl),
                "V/(2*LvV*t*FsCW*Ts+LtV*t*FtCW*Ts)+P/(2*LvP*t*FsLW*Ts+LtP*t*FtLW*Ts)",
            ),
            compare(
                "DIRECT_COLUMN_BEARING",
                "Calcs!D146",
                (v, p),
                (2 * db * tc * bcw, 2 * db * tc * bcw),
                "(V+P)/(n*d*t_column*FbCW*Ts)",
            ),
            compare(
                "DIRECT_COLUMN_LOCAL",
                "Calcs!D183:D205",
                (v / 2, p / 2),
                (r_cv, r_cp),
                "(V/n)/(2*LvV*t*FsCW*Ts)+(P/n)/(2*LvP*t*FsCW*Ts)",
            ),
            compare(
                "DIRECT_COLUMN_GLOBAL",
                "Calcs!D211:D239",
                (v, p),
                (r_cv + lengths["L65"] * tc * ft * t, r_cp + lengths["L52"] * tc * ft),
                "V/(2*LvV*t*FsCW*Ts+LtV*t*FtCW*Ts^2)+P/(2*LvP*t*FsCW*Ts+LtP*t*FtCW*Ts)",
            ),
        )
        summary = tuple(
            (cell, checks[i].utilization)
            for cell, i in (
                ("D34", 0),
                ("D46", 1),
                ("D75", 2),
                ("D121", 3),
                ("D146", 4),
                ("D159", 1),
                ("D205", 5),
                ("D239", 6),
            )
        )
        return DirectSourceCase(
            stream,
            geometry,
            paths,
            checks,
            summary,
            ledger,
            "OK"
            if stream is ReferenceStream.HISTORICAL_REPLICATION
            else checks[1].numerical_outcome,
            "OK",
            "OWN_REINFORCEMENT_ABSENT_RECEIVING_CHECKS_STILL_REQUIRED",
        )
