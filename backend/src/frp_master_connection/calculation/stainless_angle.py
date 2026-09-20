"""Isolated C2-A and shared hot-shape D/E/F/G/H mechanics; no frozen-provider imports.

Source-native US section records and private Decimal-100 arithmetic are used.
I11 is superseded by the owner/EOR clarification: tension H2-2 decreases with Pr;
both equations remain intact and max(H2-1,H2-2), not monotonic repair, governs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.stainless_response import valid_hash
from frp_master_connection.domain.stainless_shape import (
    GRADES,
    PRODUCT,
    SOURCE,
    ShapeContext,
    ShapeRequest,
    TrustedShapeRecord,
)

PROVIDER = "C2_A_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1"
D = Decimal
PI = D(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068"
)
FY, FU, E = D(25), D(70), D(28000)


@dataclass(frozen=True, slots=True)
class ShapeTrace:
    method: str
    values: tuple[tuple[str, Decimal], ...]
    unit: str
    governing: str = ""


@dataclass(frozen=True, slots=True)
class ShapeResult:
    provider: str
    status: str
    source_status: str
    response_status: str
    local_status: str
    traces: tuple[ShapeTrace, ...]
    fingerprint: str
    authority: TrustedShapeRecord | None
    family_activation: bool = False
    external_scopes: tuple[str, ...] = (
        "WHOLE_CONNECTION_NOT_EVALUATED",
        "FRP_MEMBER_NOT_EVALUATED",
        "FASTENER_NOT_EVALUATED",
        "FOUNDATION_ANCHOR_EXTERNAL",
    )


def value(q: PhysicalQuantity, unit: Unit) -> Decimal:
    return q.to(unit).magnitude


def _trace(method: str, unit: str, governing: str = "", **values: Decimal) -> ShapeTrace:
    return ShapeTrace(method, tuple(values.items()), unit, governing)


def _product(r: ShapeRequest, form: str) -> str | None:
    p = r.product
    if (
        p.route != PRODUCT
        or p.specification != "ASTM A276/A276M"
        or p.general_requirements != "ASTM A484/A484M"
        or p.welded
        or p.processing not in ("HOT_ROLLED", "EXTRUDED")
        or r.section.form != form
    ):
        return "STAINLESS_SHAPE_PRODUCT_ROUTE_NOT_SUPPORTED"
    if p.condition not in ("A", "HF"):
        return "STAINLESS_SHAPE_CONDITION_NOT_SUPPORTED"
    if (
        not p.id
        or not p.source
        or not valid_hash(p.content_sha256)
        or p.grade not in GRADES
        or p.source_sha256 != SOURCE
        or p.source_system != "US_CUSTOMARY"
        or p.strength_credit
        or tuple(value(q, Unit.KSI) for q in (p.fy, p.fu, p.elastic_modulus, p.shear_modulus))
        != (FY, FU, E, D(10800))
    ):
        return "STAINLESS_SHAPE_PRODUCT_SOURCE_NOT_QUALIFIED"
    return None


def _section(r: ShapeRequest) -> str | None:
    s = r.section
    if (
        not s.id
        or not s.geometry_source
        or not valid_hash(s.geometry_sha256)
        or value(s.area, Unit.IN2) <= 0
        or not s.elements
        or len(s.axes) != 2
        or tuple(a.id for a in s.axes) != ("w", "z")
        or not s.principal_frame
        or any(value(a.radius, Unit.IN) <= 0 or min(a.smin_in3, a.sft_in3) <= 0 for a in s.axes)
        or any(
            not x.id
            or not x.boundary_source
            or value(x.width, Unit.IN) <= 0
            or value(x.thickness, Unit.IN) <= 0
            for x in s.elements
        )
    ):
        return "STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED"
    if any(c in r.checks for c in ("COMPRESSION", "FLEXURE", "H2")) and any(
        value(x.width, Unit.IN) / value(x.thickness, Unit.IN) > D(".41") * (E / FY).sqrt()
        for x in s.elements
    ):
        return "STAINLESS_SHAPE_SLENDER_ELEMENT_NOT_SUPPORTED_IN_C2_CORE"
    return None


def _tension(r: ShapeRequest) -> tuple[ShapeTrace | None, str | None]:
    area = r.section.net_area
    if (
        area is None
        or not r.section.net_area_source
        or not 0 < value(area, Unit.IN2) <= value(r.section.area, Unit.IN2)
    ):
        return None, "STAINLESS_SHAPE_NET_AREA_NOT_RESOLVED"
    lag = r.shear_lag
    if lag is None or not lag.source:
        return None, "STAINLESS_SHAPE_SHEAR_LAG_NOT_RESOLVED"
    if r.section.form == "TEE" and lag.case == "CASE7":
        return None, "STAINLESS_TEE_D3_CASE7_NOT_APPLICABLE_TO_HOT_ROLLED_EXTRUDED_TEE"
    u: Decimal | None = None
    if lag.case == "CASE1" and lag.all_elements_direct:
        u = D(1)
    if lag.case in ("CASE2", "CASE8") and lag.x is not None and lag.length is not None:
        x, length = value(lag.x, Unit.IN), value(lag.length, Unit.IN)
        if 0 <= x < length:
            u = 1 - x / length
    if lag.case == "CASE8" and r.section.form == "ANGLE":
        if lag.fasteners_per_line >= 3:
            u = max(u or D(0), D(".8") if lag.fasteners_per_line >= 4 else D(".6"))
    elif lag.case not in ("CASE1", "CASE2"):
        u = None
    if u is None or not 0 < u <= 1:
        return None, "STAINLESS_SHAPE_SHEAR_LAG_NOT_RESOLVED"
    yielding = D(".9") * FY * value(r.section.area, Unit.IN2)
    rupture = D(".75") * FU * value(area, Unit.IN2) * u
    return _trace(
        "D2_D3",
        "kip",
        "D2_GROSS_YIELDING" if yielding <= rupture else "D2_NET_RUPTURE",
        U=u,
        gross_yield=yielding,
        net_rupture=rupture,
        available=min(yielding, rupture),
    ), None


def _shear(r: ShapeRequest) -> tuple[list[ShapeTrace], str | None]:
    traces: list[ShapeTrace] = []
    if not r.shear_elements:
        return traces, "STAINLESS_SHAPE_SHEAR_ELEMENT_NOT_QUALIFIED"
    for element in r.shear_elements:
        d, t = value(element.width, Unit.IN), value(element.thickness, Unit.IN)
        if d <= 0 or t <= 0 or not element.boundary_source:
            return [], "STAINLESS_SHAPE_SHEAR_ELEMENT_NOT_QUALIFIED"
        kv = D(5) if element.stiffened else D("1.2")
        lam, q = d / t, (kv * E / FY).sqrt()
        if lam <= D(".33") * q:
            branch, cv = "G2_CV2_ZONE_1", D("1.2")
        elif lam <= D(".97") * q:
            branch, cv = "G2_CV2_ZONE_2", D("1.2") - D(".62") * (lam / q - D(".33"))
        elif lam <= D("2.68") * q:
            branch, cv = "G2_CV2_ZONE_3", (D("5.02") * q - lam) / (D("1.62") * q + D("3.55") * lam)
        else:
            branch, cv = "G2_CV2_ZONE_4", D("1.51") * kv * E / (lam**2 * FY)
        traces.append(
            _trace(
                "G6:" + element.id,
                "kip",
                branch,
                slenderness=lam,
                kv=kv,
                q=q,
                Cv2=cv,
                area=d * t,
                nominal=D(".6") * cv * FY * d * t,
                available=D(".9") * D(".6") * cv * FY * d * t,
            )
        )
    return traces, None


def _curve(fe: Decimal, area: Decimal, name: str) -> ShapeTrace:
    ratio = FY / fe
    if ratio <= (D(".76") / PI) ** 2:
        branch, raw = "E3_YIELD_PLATEAU", FY
    elif ratio <= D("5.62") ** 2 / PI**2:
        branch, raw = "E3_INELASTIC", D("1.2") * D(".41") ** (ratio ** D(".56")) * FY
    else:
        branch, raw = "E3_ELASTIC", D(".69") * fe
    used = min(FY, raw)
    return _trace(
        name,
        "kip",
        branch,
        Fe=fe,
        ratio=ratio,
        Fn_raw=raw,
        Fn_used=used,
        nominal=used * area,
        available=D(".9") * used * area,
    )


def _compression(r: ShapeRequest) -> tuple[list[ShapeTrace], str | None]:
    if r.section.form == "ANGLE" and not r.section.equal_leg:
        return [], "STAINLESS_ANGLE_COMPRESSION_UNEQUAL_LEG_NOT_SUPPORTED"
    if (
        r.e4_fe is None
        or value(r.e4_fe, Unit.KSI) <= 0
        or not r.e4_source
        or tuple(x.axis for x in r.stability) != ("w", "z")
        or any(not x.source or value(x.effective_length, Unit.IN) <= 0 for x in r.stability)
    ):
        return [], "STAINLESS_SHAPE_COMPRESSION_STABILITY_NOT_RESOLVED"
    area = value(r.section.area, Unit.IN2)
    traces = [
        _curve(
            PI**2 * E / (value(st.effective_length, Unit.IN) / value(ax.radius, Unit.IN)) ** 2,
            area,
            "E3:" + ax.id,
        )
        for st, ax in zip(r.stability, r.section.axes, strict=True)
    ]
    traces.append(_curve(value(r.e4_fe, Unit.KSI), area, "E4"))
    governing = min(traces, key=lambda x: dict(x.values)["available"])
    traces.append(
        _trace(
            "COMPRESSION", "kip", governing.method, available=dict(governing.values)["available"]
        )
    )
    return traces, None


def _flexure(r: ShapeRequest) -> tuple[list[ShapeTrace], str | None]:
    if tuple(x.axis for x in r.stability) != ("w", "z"):
        return [], "STAINLESS_SHAPE_F10_STABILITY_NOT_RESOLVED"
    traces: list[ShapeTrace] = []
    for st, ax in zip(r.stability, r.section.axes, strict=True):
        lb, ly, lr = (value(q, Unit.IN) for q in (st.lb, st.ly, st.lr))
        if not st.source or lb < 0 or ly <= 0 or lr <= ly:
            return [], "STAINLESS_SHAPE_F10_STABILITY_NOT_RESOLVED"
        my = FY * ax.smin_in3
        x, alpha = D(0), D(0)
        if lb <= ly:
            branch, candidate = "F10_NO_LTB", my
        elif lb <= lr:
            x = (lb - ly) / (lr - ly)
            alpha = D(".6") - D(".4") * x
            branch, candidate = "F10_INELASTIC_LTB", my - (my - D(".3") * my) * x**alpha
        elif st.fcr is not None and value(st.fcr, Unit.KSI) > 0:
            branch, candidate = "F10_ELASTIC_LTB", D(".82") * value(st.fcr, Unit.KSI) * ax.smin_in3
        else:
            return [], "STAINLESS_SHAPE_F10_STABILITY_NOT_RESOLVED"
        traces.append(
            _trace(
                "F10:" + ax.id,
                "kip-in",
                branch,
                My=my,
                x=x,
                alpha_LT=alpha,
                candidate=candidate,
                nominal=min(my, candidate),
                available=D(".9") * min(my, candidate),
                Mct=D(".9") * FY * ax.sft_in3,
            )
        )
    return traces, None


def _local(r: ShapeRequest, record: TrustedShapeRecord) -> str:
    for s in record.local_snapshots:
        if (
            s.provider
            not in (
                "C2_P1_AISC_370_25_FLAT_PLATE_LRFD_RC1_R1",
                "C2_P2_AISC_370_25_CLEAR_RECTANGULAR_PLATE_LRFD_RC1",
            )
            or s.body != r.demand.body
            or s.region != r.demand.region
            or s.request_sha256 != angle_fingerprint(r)
            or not valid_hash(s.result_sha256)
            or s.source_sha256 != SOURCE
            or not s.covered_mechanism
        ):
            return "STAINLESS_LOCAL_REGION_SNAPSHOT_MISMATCH"
    if r.local_mechanism_required and (
        not record.local_snapshots or not record.local_qualification
    ):
        return (
            "STAINLESS_ANGLE_LOCAL_HEEL_PRYING_METHOD_NOT_AVAILABLE"
            if r.section.form == "ANGLE"
            else "STAINLESS_TEE_LOCAL_JUNCTION_METHOD_NOT_AVAILABLE"
        )
    if any(s.status != "PASS" for s in record.local_snapshots):
        return "STAINLESS_LOCAL_REGION_NOT_PASSED"
    return "QUALIFIED" if record.local_snapshots else "NOT_REQUIRED"


def evaluate_shape(r: ShapeRequest, context: ShapeContext, form: str, provider: str) -> ShapeResult:
    """Complete trusted request matching, fail-closed boundaries and source-native mechanics."""
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 100, ROUND_HALF_EVEN
        matches = [x for x in context.records if x.request == r]
        record = matches[0] if len(matches) == 1 else None
        source = _product(r, form) or _section(r) or "QUALIFIED"
        if record is None or not all(
            (record.id, valid_hash(record.source_sha256), record.section_qualification)
        ):
            source = "STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED"
        response = "QUALIFIED"
        if (
            record is None
            or record.response_demand != r.demand
            or not record.response_authority
            or not valid_hash(record.response_fingerprint)
        ):
            response = "STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED"
        local = _local(r, record) if record is not None else "NOT_EVALUATED"
        traces: list[ShapeTrace] = []
        errors = [s for s in (source, response, local) if s not in ("QUALIFIED", "NOT_REQUIRED")]
        d = r.demand
        if (
            not all((d.id, d.route, d.body, d.region, d.load_combination))
            or d.frame != r.section.principal_frame
            or d.sign_convention != "POSITIVE_AXIAL_TENSION_PRINCIPAL_MOMENT_MAGNITUDES"
        ):
            errors.append("STAINLESS_RESPONSE_REFERENCE_FRAME_MISMATCH")
        axial, mw, mz = (
            value(d.axial, Unit.KIP),
            value(d.moment_w, Unit.KIP_IN),
            value(d.moment_z, Unit.KIP_IN),
        )
        shear, torsion = value(d.shear, Unit.KIP), value(d.torsion, Unit.KIP_IN)
        if min(mw, mz) < 0:
            errors.append("STAINLESS_SHAPE_DEMAND_MAGNITUDE_INVALID")
        if torsion != 0:
            errors.append("STAINLESS_SHAPE_TORSION_NOT_SUPPORTED")
        if shear != 0 and (axial != 0 or mw != 0 or mz != 0):
            errors.append("STAINLESS_SHAPE_COMBINED_NORMAL_SHEAR_NOT_SUPPORTED")
        if not r.checks or set(r.checks) - {"TENSION", "COMPRESSION", "FLEXURE", "SHEAR", "H2"}:
            errors.append("STAINLESS_SHAPE_CHECK_PLAN_NOT_SUPPORTED")
        if r.family_activation_requested:
            errors.insert(0, "STAINLESS_PUBLIC_FAMILY_ACTIVATION_NOT_AUTHORIZED")
        if not errors:
            needed = set(r.checks)
            if "H2" in needed:
                needed.update(("FLEXURE", "TENSION" if axial >= 0 else "COMPRESSION"))
            for check in ("TENSION", "SHEAR", "COMPRESSION", "FLEXURE"):
                if check not in needed:
                    continue
                if check == "TENSION":
                    trace, error = _tension(r)
                    results = [trace] if trace is not None else []
                elif check == "SHEAR":
                    results, error = _shear(r)
                elif check == "COMPRESSION":
                    results, error = _compression(r)
                else:
                    results, error = _flexure(r)
                traces.extend(results)
                if error:
                    errors.append(error)
            if "H2" in needed and not errors:
                maps = {t.method: dict(t.values) for t in traces}
                bending = mw / maps["F10:w"]["available"] + mz / maps["F10:z"]["available"]
                if axial < 0:
                    ir = -axial / maps["COMPRESSION"]["available"] + bending
                    traces.append(_trace("H2", "1", "H2_3", H2_3=ir, interaction=ir))
                else:
                    tension = axial / maps["D2_D3"]["available"]
                    ir1 = mw / maps["F10:w"]["Mct"] + mz / maps["F10:z"]["Mct"] + tension
                    ir2 = bending - tension
                    traces.append(
                        _trace(
                            "H2",
                            "1",
                            "H2_1" if ir1 >= ir2 else "H2_2",
                            H2_1=ir1,
                            H2_2=ir2,
                            interaction=max(ir1, ir2),
                        )
                    )
        status = errors[0] if errors else "ISOLATED_COVERED_CHECKS_PASS"
        if not errors:
            limits = {t.method: dict(t.values) for t in traces}
            checks = [v["interaction"] for k, v in limits.items() if k == "H2"]
            if "D2_D3" in limits:
                checks.append(max(axial, D(0)) / limits["D2_D3"]["available"])
            if "COMPRESSION" in limits:
                checks.append(max(-axial, D(0)) / limits["COMPRESSION"]["available"])
            for name, moment in (("F10:w", mw), ("F10:z", mz)):
                if name in limits and "H2" not in limits:
                    checks.append(moment / limits[name]["available"])
            capacities = [v["available"] for k, v in limits.items() if k.startswith("G6:")]
            if capacities:
                checks.append(abs(shear) / sum(capacities))
            if any(x > 1 for x in checks):
                status = "FAIL"
        if errors:
            traces = []
        return ShapeResult(
            provider,
            status,
            source,
            response,
            local,
            tuple(traces),
            angle_fingerprint((provider, SOURCE, r, record, tuple(traces), status)),
            record,
        )


def evaluate_stainless_angle(r: ShapeRequest, context: ShapeContext) -> ShapeResult:
    return evaluate_shape(r, context, "ANGLE", PROVIDER)
