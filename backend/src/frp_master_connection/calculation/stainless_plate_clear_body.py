"""C2-P2 isolated clear-strip E3/F9/H2 provider; no public dispatch or response solver.

Owner clarification: consume a trusted pre-resolved C2-M/C2-P1 snapshot, without
importing either frozen module. Do not recompute its thickness or tensile endpoint.
Owner E3 policy: retain the raw value and cap Fn at Fy before resistance comparison.
All mechanics use a private Decimal-100 HALF_EVEN context and native quantities.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import cast

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit, decimal_value

PROVIDER = "C2_P2_AISC_370_25_CLEAR_RECTANGULAR_PLATE_LRFD_RC1"
SOURCE = "A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1"
P1 = "C2_P1_AISC_370_25_FLAT_PLATE_LRFD_RC1_R1"
POLICY = "OWNER_EOR_E3_FY_CAP_TRUSTED_PRE_RESOLVED_C2_SNAPSHOT_2026_09_12"
PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068"
)
D = Decimal
ZERO = D(0)
ONE = D(1)
ZERO_MOMENT = PhysicalQuantity.of(0, Unit.KIP_IN)
ZERO_FORCE = PhysicalQuantity.of(0, Unit.KIP)


@dataclass(frozen=True, slots=True)
class ClearSection:
    id: str
    width: PhysicalQuantity
    nominal_thickness: PhysicalQuantity
    # Physical x_min, x_max, y_min, y_max in the declared local frame.
    bounds: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    frame: str = "PLATE_X_LONGITUDINAL_Y_WIDTH_Z_THICKNESS"
    width_basis: str = "PHYSICAL_CLEAR_WIDTH"
    hole_intersects: bool = False
    local_mechanism: bool = False
    product_form: str = "FLAT_PLATE"
    fabrication: str = "CUT_DRILLED_MACHINED"


@dataclass(frozen=True, slots=True)
class ResolvedClearDemand:
    id: str
    axial: PhysicalQuantity
    moment_z: PhysicalQuantity | None
    reference: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    load_combination: str
    response_method: str
    frame: str = "PLATE_X_LONGITUDINAL_Y_WIDTH_Z_THICKNESS"
    sign_convention: str = "POSITIVE_AXIAL_TENSION_RIGHT_HAND_MOMENTS"
    moment_y: PhysicalQuantity = ZERO_MOMENT
    torsion: PhysicalQuantity = ZERO_MOMENT
    shear: PhysicalQuantity = ZERO_FORCE
    raw_eccentricity: PhysicalQuantity | None = None
    requires_response_generation: bool = False
    response_qualified: bool = True


@dataclass(frozen=True, slots=True)
class EffectiveLength:
    k: Decimal
    length: PhysicalQuantity
    authority: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "k", decimal_value(self.k))


@dataclass(frozen=True, slots=True)
class ClearRequest:
    section: ClearSection
    demand: ResolvedClearDemand
    y_stability: EffectiveLength | None = None
    z_stability: EffectiveLength | None = None
    e4: str = "UNRESOLVED"
    e4_authority: str = ""
    lb: PhysicalQuantity | None = None
    lb_authority: str = ""
    cb: Decimal | None = None
    cb_authority: str = "CONSERVATIVE_DEFAULT"
    csm: bool = False
    family_activation_requested: bool = False

    def __post_init__(self) -> None:
        if self.cb is not None:
            object.__setattr__(self, "cb", decimal_value(self.cb))


@dataclass(frozen=True, slots=True)
class FrozenPlateAuthority:
    """Server-resolved same-section snapshot, never client numerical authority.

    The caller must resolve C2-M/C2-P1 outside this module. The trusted context binds
    these exact values to the complete physical/demand/stability request. A matching
    label or request-side hash alone cannot create a context record.
    """

    section: ClearSection
    material_identity: str
    material_fingerprint: str
    p1_fingerprint: str
    fy: PhysicalQuantity
    fu: PhysicalQuantity
    elastic_modulus: PhysicalQuantity
    design_thickness: PhysicalQuantity
    thickness_rule: str
    tolerance_evidence: str
    available_tension: PhysicalQuantity
    source_sha256: str = SOURCE
    p1_provider: str = P1
    source_system: str = "US_CUSTOMARY"
    direct_transfer: str = "DIRECT_ALL_CROSS_SECTION_ELEMENTS"


@dataclass(frozen=True, slots=True)
class TrustedClearRecord:
    request: ClearRequest
    snapshot: FrozenPlateAuthority
    id: str
    content_sha256: str
    geometry_authority: str
    demand_authority: str


@dataclass(frozen=True, slots=True)
class ClearContext:
    records: tuple[TrustedClearRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class RectangularProperties:
    """Source U.S. units: in, in², in³, in⁴; no display-rounded input values."""

    b: Decimal
    t: Decimal
    area: Decimal
    iy: Decimal
    iz: Decimal
    ry: Decimal
    rz: Decimal
    sy: Decimal
    sz: Decimal
    zy: Decimal
    zz: Decimal


@dataclass(frozen=True, slots=True)
class CompressionAxis:
    axis: str
    lc: PhysicalQuantity
    slenderness: Decimal
    fe: PhysicalQuantity
    fy_over_fe: Decimal
    branch: str
    fn_raw: PhysicalQuantity
    fn: PhysicalQuantity
    cap_applied: bool
    nominal: PhysicalQuantity
    available: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class Flexure:
    q: Decimal
    cb: Decimal
    cb_authority: str
    branch: str
    my: PhysicalQuantity
    mp: PhysicalQuantity
    fcr: PhysicalQuantity | None
    candidate: PhysicalQuantity
    nominal: PhysicalQuantity
    available: PhysicalQuantity
    plastic_cap_applied: bool


@dataclass(frozen=True, slots=True)
class ClearCheck:
    method: str
    utilization: Decimal
    comparison: str


@dataclass(frozen=True, slots=True)
class ClearResult:
    geometry_status: str
    material_source_status: str
    method_status: tuple[str, ...]
    demand_status: tuple[str, ...]
    response_status: tuple[str, ...]
    properties: RectangularProperties | None
    compression_axes: tuple[CompressionAxis, ...]
    compression_governing_axis: str | None
    flexure: Flexure | None
    checks: tuple[ClearCheck, ...]
    governing_check: str | None
    numerical_comparison: str
    fingerprint: str
    resolved_input: ClearRequest
    authority: TrustedClearRecord | None
    source_trace: tuple[str, ...] = (PROVIDER, SOURCE, P1, POLICY, "B4.2a/E3/F9/H2")
    family_activation: bool = False
    external_scopes: tuple[str, ...] = (
        "WHOLE_CONNECTION_NOT_EVALUATED",
        "FRP_MEMBER_NOT_EVALUATED",
        "FASTENER_NOT_EVALUATED",
        "FOUNDATION_ANCHOR_EXTERNAL",
    )


def _value(q: PhysicalQuantity, unit: Unit) -> Decimal:
    return q.to(unit).magnitude


def _hash(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def _record(request: ClearRequest, context: ClearContext) -> TrustedClearRecord | None:
    found = [r for r in context.records if r.request == request]
    if len(found) != 1:
        return None
    record = found[0]
    if not all((record.id, record.geometry_authority, record.demand_authority)) or not _hash(
        record.content_sha256
    ):
        return None
    return record


def _snapshot_valid(s: FrozenPlateAuthority, section: ClearSection) -> bool:
    return (
        s.section == section
        and s.source_sha256 == SOURCE
        and s.p1_provider == P1
        and s.source_system == "US_CUSTOMARY"
        and s.direct_transfer == "DIRECT_ALL_CROSS_SECTION_ELEMENTS"
        and bool(s.material_identity and s.thickness_rule and s.tolerance_evidence)
        and _hash(s.material_fingerprint)
        and _hash(s.p1_fingerprint)
        and _value(s.fy, Unit.KSI) == 25
        and _value(s.fu, Unit.KSI) == 70
        and _value(s.elastic_modulus, Unit.KSI) == 28000
        and 0 < _value(s.design_thickness, Unit.IN) <= _value(section.nominal_thickness, Unit.IN)
        and _value(s.available_tension, Unit.KIP) > 0
    )


def _properties(section: ClearSection, s: FrozenPlateAuthority) -> RectangularProperties | None:
    b, t = _value(section.width, Unit.IN), _value(s.design_thickness, Unit.IN)
    x0, x1, y0, y1 = (_value(q, Unit.IN) for q in section.bounds)
    if (
        not section.id
        or b <= 0
        or x1 <= x0
        or y1 - y0 != b
        or section.width_basis != "PHYSICAL_CLEAR_WIDTH"
        or section.hole_intersects
        or section.local_mechanism
    ):
        return None
    a, iy, iz = b * t, b * t**3 / 12, t * b**3 / 12
    return RectangularProperties(
        b,
        t,
        a,
        iy,
        iz,
        (iy / a).sqrt(),
        (iz / a).sqrt(),
        b * t**2 / 6,
        t * b**2 / 6,
        b * t**2 / 4,
        t * b**2 / 4,
    )


def _length_valid(length: EffectiveLength | None) -> bool:
    return (
        length is not None
        and length.authority not in ("", "UNRESOLVED", "CLIENT")
        and length.k > 0
        and _value(length.length, Unit.IN) > 0
    )


def _axis(axis: str, length: EffectiveLength, radius: Decimal, area: Decimal) -> CompressionAxis:
    lc = length.k * _value(length.length, Unit.IN)
    slenderness = lc / radius
    fe = PI**2 * 28000 / slenderness**2
    ratio = D(25) / fe
    root = (D(28000) / 25).sqrt()
    if slenderness <= D(".76") * root:
        branch, raw = "E3_YIELD_PLATEAU", D(25)
    elif slenderness <= D("5.62") * root:
        branch, raw = "E3_INELASTIC", D("1.2") * D(".41") ** (ratio ** D(".56")) * 25
    else:
        branch, raw = "E3_ELASTIC", D(".69") * fe
    fn = min(D(25), raw)
    return CompressionAxis(
        axis,
        PhysicalQuantity(lc, Unit.IN),
        slenderness,
        PhysicalQuantity(fe, Unit.KSI),
        ratio,
        branch,
        PhysicalQuantity(raw, Unit.KSI),
        PhysicalQuantity(fn, Unit.KSI),
        raw > 25,
        PhysicalQuantity(fn * area, Unit.KIP),
        PhysicalQuantity(D(".9") * fn * area, Unit.KIP),
    )


def _flexure(
    p: RectangularProperties, lb: PhysicalQuantity, cb: Decimal, authority: str
) -> Flexure:
    q = _value(lb, Unit.IN) * p.b / p.t**2
    mp, my = 25 * p.zz, 25 * p.sz
    fcr = None
    if q <= D(".306") * 28000 / 25:
        branch, candidate = "F9_NO_LTB", mp
    elif q <= D(2) * 28000 / 25:
        branch = "F9_INELASTIC_LTB"
        candidate = cb * (D("1.61") - D(".36") * q * 25 / 28000) * my
    else:
        branch = "F9_ELASTIC_LTB"
        fcr = PhysicalQuantity(D("1.78") * 28000 * cb / q, Unit.KSI)
        candidate = fcr.magnitude * p.sz
    nominal = min(candidate, mp)
    return Flexure(
        q,
        cb,
        authority,
        branch,
        PhysicalQuantity(my, Unit.KIP_IN),
        PhysicalQuantity(mp, Unit.KIP_IN),
        fcr,
        PhysicalQuantity(candidate, Unit.KIP_IN),
        PhysicalQuantity(nominal, Unit.KIP_IN),
        PhysicalQuantity(D(".9") * nominal, Unit.KIP_IN),
        candidate > mp,
    )


def _demand_problem(r: ClearRequest) -> str | None:
    d = r.demand
    if d.moment_z is None:
        return (
            "STAINLESS_ECCENTRIC_MOMENT_NOT_RESOLVED"
            if d.raw_eccentricity is not None
            else "STAINLESS_DEMAND_NOT_RESOLVED"
        )
    if (
        not all((d.id, d.load_combination, d.response_method, r.section.frame))
        or d.frame != r.section.frame
        or d.sign_convention != "POSITIVE_AXIAL_TENSION_RIGHT_HAND_MOMENTS"
        or len(d.reference) != 3
    ):
        return "STAINLESS_DEMAND_NOT_RESOLVED"
    for q in d.reference:
        _value(q, Unit.IN)
    return None


def _method_problems(r: ClearRequest, axial: Decimal, moment: Decimal) -> list[str]:
    problems: list[str] = []
    if (
        r.section.product_form not in ("FLAT_PLATE", "FLAT_SHEET", "FLAT_STRIP")
        or r.section.fabrication != "CUT_DRILLED_MACHINED"
    ):
        problems.append("STAINLESS_FORM_NOT_SUPPORTED_IN_C2_P2")
    if r.csm:
        problems.append("STAINLESS_CSM_NOT_SUPPORTED_IN_C2_P2")
    if _value(r.demand.moment_y, Unit.KIP_IN):
        problems.append(
            "STAINLESS_BIAXIAL_FLEXURE_NOT_SUPPORTED_IN_C2_P2"
            if moment
            else "STAINLESS_OUT_OF_PLANE_FLEXURE_NOT_SUPPORTED_IN_C2_P2"
        )
    if _value(r.demand.torsion, Unit.KIP_IN):
        problems.append("STAINLESS_TORSION_NOT_SUPPORTED_IN_C2_P2")
    if _value(r.demand.shear, Unit.KIP):
        problems.append(
            "STAINLESS_COMBINED_NORMAL_SHEAR_NOT_SUPPORTED_IN_C2_P2"
            if axial or moment
            else "STAINLESS_PURE_SHEAR_REMAINS_C2_P1_AUTHORITY"
        )
    if axial < 0:
        if not (_length_valid(r.y_stability) and _length_valid(r.z_stability)):
            problems.append("STAINLESS_COMPRESSION_EFFECTIVE_LENGTH_NOT_RESOLVED")
        if r.e4 == "REQUIRED":
            problems.append("STAINLESS_TORSIONAL_BUCKLING_METHOD_NOT_SUPPORTED_IN_C2_P2")
        elif r.e4 != "QUALIFIED_NOT_CONTROLLING" or not r.e4_authority:
            problems.append("STAINLESS_TORSIONAL_BUCKLING_SCOPE_NOT_RESOLVED")
    if moment:
        if r.lb is None or not r.lb_authority or _value(r.lb, Unit.IN) <= 0:
            problems.append("STAINLESS_FLEXURAL_UNBRACED_LENGTH_NOT_RESOLVED")
        if r.cb is not None:
            if not ONE <= r.cb <= D("1.67"):
                problems.append("STAINLESS_CB_OUTSIDE_APPROVED_RANGE")
            elif r.cb > 1 and not r.cb_authority.startswith("TRUSTED_F1_PROFILE:"):
                problems.append("STAINLESS_CB_CREDIT_NOT_QUALIFIED")
    return problems


def _evaluate(r: ClearRequest, context: ClearContext) -> ClearResult:
    record = _record(r, context)
    source, geometry = "VERIFIED", "NOT_EVALUATED"
    methods: list[str] = []
    demands: list[str] = []
    response: list[str] = []
    props = None
    axes: tuple[CompressionAxis, ...] = ()
    compression_axis = None
    flexure = None
    checks: list[ClearCheck] = []
    if (
        r.family_activation_requested
        or not r.demand.response_qualified
        or r.demand.requires_response_generation
    ):
        response.append("STAINLESS_MATERIAL_DEPENDENT_RESPONSE_NOT_QUALIFIED")
    try:
        if record is None or not _snapshot_valid(record.snapshot, r.section):
            source = "STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED"
        else:
            props = _properties(r.section, record.snapshot)
            geometry = "VALID" if props else "STAINLESS_CLEAR_BODY_SECTION_NOT_QUALIFIED"
            problem = _demand_problem(r)
            if problem:
                demands.append(problem)
            else:
                axial = _value(r.demand.axial, Unit.KIP)
                moment = abs(_value(cast(PhysicalQuantity, r.demand.moment_z), Unit.KIP_IN))
                methods = _method_problems(r, axial, moment)
                if props is not None and not methods and not r.demand.requires_response_generation:
                    ratios: list[tuple[str, Decimal]] = []
                    if axial < 0:
                        axes = (
                            _axis("y", cast(EffectiveLength, r.y_stability), props.ry, props.area),
                            _axis("z", cast(EffectiveLength, r.z_stability), props.rz, props.area),
                        )
                        selected = min(axes, key=lambda a: (a.available.magnitude, a.axis))
                        compression_axis = selected.axis
                        ratios.append(("E3_COMPRESSION", -axial / selected.available.magnitude))
                    if moment:
                        cb = r.cb if r.cb is not None else ONE
                        flexure = _flexure(
                            props,
                            cast(PhysicalQuantity, r.lb),
                            cb,
                            r.cb_authority if cb > 1 else "CONSERVATIVE_DEFAULT",
                        )
                        bending = moment / flexure.available.magnitude
                        if axial < 0:
                            ratios = [("H2_COMPRESSION", ratios[0][1] + bending)]
                        elif axial > 0:
                            tension = axial / _value(record.snapshot.available_tension, Unit.KIP)
                            ratios = [
                                ("H2_TENSION_SIDE", moment / (D(".9") * 25 * props.sz) + tension),
                                ("H2_COMPRESSION_SIDE", bending - tension),
                            ]
                        else:
                            ratios = [("F9_FLEXURE", bending)]
                    elif axial > 0:
                        ratios = [
                            (
                                "FROZEN_C2_P1_TENSION_ENDPOINT",
                                axial / _value(record.snapshot.available_tension, Unit.KIP),
                            )
                        ]
                    checks = [
                        ClearCheck(name, u, "FAIL" if u > 1 else "PASS") for name, u in ratios
                    ]
    except ValueError, TypeError, ArithmeticError:
        # Malformed internal plans fail closed too; no partial numerical outputs.
        methods.append("STAINLESS_INVALID_DIMENSION_OR_NUMERIC_INPUT")
        props, axes, compression_axis, flexure, checks = None, (), None, None, []
    governing = max(checks, key=lambda check: check.utilization).method if checks else None
    comparison = "NOT_EVALUATED"
    if any(check.comparison == "FAIL" for check in checks):
        comparison = "FAIL"
    elif checks:
        comparison = "ISOLATED_COVERED_CHECKS_PASS"
    return ClearResult(
        geometry,
        source,
        tuple(methods),
        tuple(demands),
        tuple(response),
        props,
        axes,
        compression_axis,
        flexure,
        tuple(checks),
        governing,
        comparison,
        angle_fingerprint((PROVIDER, POLICY, r, record)),
        r,
        record,
    )


def evaluate_clear_plate(request: ClearRequest, context: ClearContext) -> ClearResult:
    """Trusted internal catalogue only. No C2-M/P1 imports or request-side approval."""
    with localcontext() as ctx:
        ctx.prec = 100
        ctx.rounding = ROUND_HALF_EVEN
        return _evaluate(request, context)
