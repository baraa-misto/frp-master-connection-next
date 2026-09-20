"""Approved P2 goldens plus independent boundary, snapshot and adversarial proofs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.stainless_plate import (
    PlateCheckPlan,
    PlateContext,
    PlateGeometry,
    PlateRequest,
    ResolvedPlateDemand,
    TrustedPlateRecord,
    evaluate_stainless_plate,
)
from frp_master_connection.calculation.stainless_plate_clear_body import (
    PI,
    ClearContext,
    ClearRequest,
    ClearResult,
    ClearSection,
    EffectiveLength,
    FrozenPlateAuthority,
    ResolvedClearDemand,
    TrustedClearRecord,
    evaluate_clear_plate,
)
from frp_master_connection.domain.stainless_material import stainless_material

D = Decimal
ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "backend/tests/golden/FRP_MASTER_CONNECTION_CME_2_C2_P2_GOLDEN_BENCHMARKS_RC1.json"
G = json.loads(PATH.read_bytes())


def q(v: str | int | Decimal, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(v, unit)


def request(
    axial: str = "-10", moment: str = "0", length: str = "2", lb: str = "10"
) -> ClearRequest:
    section = ClearSection("CLEAR_S1", q(4), q(".375"), (q(0), q(4), q(-2), q(2)))
    demand = ResolvedClearDemand(
        "D1",
        q(axial, Unit.KIP),
        q(moment, Unit.KIP_IN),
        (q(0), q(0), q(0)),
        "LRFD_1",
        "TEST_RESOLVED_NOT_PRODUCTION_QUALIFICATION",
    )
    stability = EffectiveLength(D(1), q(length), "TEST_RESOLVED_STABILITY")
    return ClearRequest(
        section,
        demand,
        stability,
        stability,
        "QUALIFIED_NOT_CONTROLLING",
        "TEST_E4_QUALIFICATION",
        q(lb),
        "TEST_LB",
    )


def snapshot(r: ClearRequest, credit: bool = False) -> FrozenPlateAuthority:
    """Import frozen provider here, never in P2 production. No duplicate thickness logic."""
    s = r.section
    geometry = PlateGeometry(s.id, s.width, q(4), s.nominal_thickness)
    pd = ResolvedPlateDemand(
        "PCT", "ENDPOINT", q(1, Unit.KIP), (q(0), q(0), q(0)), s.frame, "+X", "TEST_DIRECT_SECTION"
    )
    plan = PlateCheckPlan(
        "T", "DIRECT", "TENSION", pd, (), s.width, s.width, "DIRECT_ALL_CROSS_SECTION_ELEMENTS"
    )
    pr = PlateRequest(geometry, stainless_material("316SS"), (plan,))
    authority = TrustedPlateRecord(
        pr,
        "TEST_ONLY",
        "a" * 64,
        "TEST_GEOMETRY",
        "TEST_DEMAND",
        (q(".001"), q(2)),
        D(".04") if credit else None,
        "TEST_TOLERANCE" if credit else None,
    )
    result = evaluate_stainless_plate(pr, PlateContext((authority,)))
    assert result.material_source_status == "VERIFIED"
    return FrozenPlateAuthority(
        s,
        pr.material.snapshot,
        angle_fingerprint(pr.material),
        result.fingerprint,
        pr.material.fy,
        pr.material.fu,
        q(28000, Unit.KSI),
        result.design_thickness,
        result.thickness_rule,
        "TEST_TOLERANCE" if credit else "NO_NOMINAL_CREDIT",
        min(c.resistance for c in result.checks),
    )


def record(r: ClearRequest, s: FrozenPlateAuthority | None = None) -> TrustedClearRecord:
    return TrustedClearRecord(
        r,
        snapshot(r) if s is None else s,
        "TEST_ONLY_NEVER_PRODUCTION",
        "b" * 64,
        "TEST_CLEAR_GEOMETRY",
        "TEST_RESOLVED_DEMAND",
    )


def evaluate(r: ClearRequest) -> ClearResult:
    return evaluate_clear_plate(r, ClearContext((record(r),)))


def rounded(v: Decimal) -> str:
    with localcontext() as c:
        c.prec = 100
        return format(v, ".12f")


def result_values(result: ClearResult) -> dict[str, str]:
    values: dict[str, str] = {}
    p = result.properties
    if p is not None:
        for name, value in (
            ("t_design_in", p.t),
            ("A_in2", p.area),
            ("Iy_in4", p.iy),
            ("Iz_in4", p.iz),
            ("ry_in", p.ry),
            ("rz_in", p.rz),
            ("Sy_in3", p.sy),
            ("Sz_in3", p.sz),
            ("Zy_in3", p.zy),
            ("Zz_in3", p.zz),
        ):
            values[name] = rounded(value)
    if result.compression_axes:
        a = result.compression_axes[0]
        values.update(
            governing_axis=str(result.compression_governing_axis),
            slenderness_y=rounded(a.slenderness),
            Fe_y_ksi=rounded(a.fe.magnitude),
            Fn_y_ksi=rounded(a.fn.magnitude),
            Fy_over_Fe_y=rounded(a.fy_over_fe),
            branch_y=a.branch,
            Pc_kip=rounded(min(x.available.magnitude for x in result.compression_axes)),
        )
    f = result.flexure
    if f is not None:
        values.update(
            q=rounded(f.q),
            branch=f.branch,
            Mn_kip_in=rounded(f.nominal.magnitude),
            Mc_kip_in=rounded(f.available.magnitude),
        )
        if f.fcr is not None:
            values["Fcr_ksi"] = rounded(f.fcr.magnitude)
    if result.checks:
        values.update(
            utilization=rounded(result.checks[0].utilization),
            interaction=rounded(result.checks[0].utilization),
            status="FAIL" if result.numerical_comparison == "FAIL" else "PASS",
            governing=str(result.governing_check),
        )
        if len(result.checks) == 2:
            values.update(
                interaction_tension_side=rounded(result.checks[0].utilization),
                interaction_compression_side=rounded(result.checks[1].utilization),
            )
    return values


@pytest.mark.parametrize("case", G["positive_cases"], ids=lambda c: c["id"])
def test_positive_goldens(case: dict[str, Any]) -> None:
    i, identity = case["inputs"], case["id"]
    axial = "0"
    if "Pr_kip" in i or "Pr_compression_kip" in i:
        axial = "-" + i.get("Pr_kip", i.get("Pr_compression_kip", "0"))
    if "Pr_tension_kip" in i:
        axial = i["Pr_tension_kip"]
    r = request(axial, i.get("Mr_kip_in", "0"), i.get("Lc_y_in", "2"), i.get("Lb_in", "10"))
    if "t_nom_in" in i:
        r = replace(r, section=replace(r.section, nominal_thickness=q(i["t_nom_in"])))
    if i.get("Cb_authority") == "TRUSTED_F1_PROFILE":
        r = replace(r, cb=D(i["Cb"]), cb_authority="TRUSTED_F1_PROFILE:TEST_F1_MOMENT_DIAGRAM")
    result = evaluate(r)
    actual = result_values(result)
    if identity == "P2_US_SOURCE_SI_DISPLAY":
        comp, flex = evaluate(request()), evaluate(request("0", "20"))
        assert flex.flexure is not None
        actual = {
            "Pc_kN": str(comp.compression_axes[0].available.to(Unit.KN).magnitude),
            "Mc_kN_mm": str(flex.flexure.available.to(Unit.KN_MM).magnitude),
            "source_property_system_remains": snapshot(r).source_system,
        }
    for key, expected in case["expected"].items():
        if key in ("Pc_kN", "Mc_kN_mm"):
            assert D(actual[key]) == D(expected)
        else:
            assert actual[key] == expected, (identity, key, actual.get(key), expected)


def negative_request(identity: str) -> ClearRequest:
    r = request("-10", "15")
    d, s = r.demand, r.section
    replacements: dict[str, ClearRequest] = {
        "CLEAR_SECTION_CONTAINS_HOLE": replace(r, section=replace(s, hole_intersects=True)),
        "LOCAL_BEARING_PRYING_ZONE": replace(r, section=replace(s, local_mechanism=True)),
        "COMPRESSION_EFFECTIVE_LENGTH_MISSING": replace(r, y_stability=None),
        "COMPRESSION_K_UNTRUSTED": replace(r, y_stability=EffectiveLength(D(1), q(2), "CLIENT")),
        "E4_DISPOSITION_UNKNOWN": replace(r, e4="UNRESOLVED"),
        "E4_REQUIRED": replace(r, e4="REQUIRED"),
        "FLEXURAL_LB_MISSING": replace(r, lb=None),
        "FAVORABLE_CB_UNTRUSTED": replace(r, cb=D("1.1"), cb_authority="CLIENT"),
        "CB_ABOVE_1_67": replace(r, cb=D("1.68"), cb_authority="TRUSTED_F1_PROFILE:TEST"),
        "OUT_OF_PLANE_MOMENT": replace(
            r, demand=replace(d, moment_z=q(0, Unit.KIP_IN), moment_y=q(1, Unit.KIP_IN))
        ),
        "BIAXIAL_MOMENT": replace(r, demand=replace(d, moment_y=q(1, Unit.KIP_IN))),
        "NONZERO_TORSION": replace(r, demand=replace(d, torsion=q(1, Unit.KIP_IN))),
        "COMBINED_NORMAL_SHEAR": replace(r, demand=replace(d, shear=q(1, Unit.KIP))),
        "RAW_ECCENTRICITY_WITHOUT_RESOLVED_MOMENT": replace(
            r, demand=replace(d, moment_z=None, raw_eccentricity=q(2))
        ),
        "CSM_REQUESTED": replace(r, csm=True),
        "ANGLE_TEE_OR_WELDED_FORM": replace(r, section=replace(s, product_form="ANGLE")),
        "FAMILY_ACTIVATION_WITHOUT_RESPONSE_AUTHORITY": replace(
            r, family_activation_requested=True, demand=replace(d, response_qualified=False)
        ),
    }
    return replacements[identity.removeprefix("P2_NEG_")]


@pytest.mark.parametrize("case", G["negative_cases"], ids=lambda c: c["id"])
def test_negative_goldens(case: dict[str, str]) -> None:
    result = evaluate(negative_request(case["id"]))
    assert case["expected_status"] in (
        result.geometry_status,
        *result.method_status,
        *result.demand_status,
        *result.response_status,
    )
    assert not result.family_activation
    if "FAMILY_ACTIVATION" not in case["id"]:
        assert not result.checks
        assert not result.compression_axes
        assert result.flexure is None


@pytest.mark.parametrize("invariant", G["invariants"], ids=lambda i: i["id"])
def test_invariants(invariant: dict[str, str]) -> None:
    identity = invariant["id"]
    if identity == "I01":
        assert (
            evaluate(request("-11", "16")).checks[0].utilization
            > evaluate(request("-10", "15")).checks[0].utilization
        )
    elif identity == "I02":
        lengths = [
            "1",
            "2",
            "2.75335456625186578965590507677481000811",
            "2.75336539156941309513898962331444441981",
            "3",
            "12",
            "20.36",
            "21",
            "100",
        ]
        strengths = [
            min(a.available.magnitude for a in evaluate(request(length=x)).compression_axes)
            for x in lengths
        ]
        assert strengths == sorted(strengths, reverse=True)
    elif identity == "I03":
        r = replace(request(), z_stability=EffectiveLength(D(1), q(500), "TEST"))
        result = evaluate(r)
        assert [a.axis for a in result.compression_axes] == ["y", "z"]
        assert result.compression_governing_axis == "z"
    elif identity in ("I04", "I05", "I06"):
        results = [
            evaluate(
                replace(request("0", "10", lb=lb), cb=D(cb), cb_authority="TRUSTED_F1_PROFILE:TEST")
            )
            for lb, cb in [
                ("10", "1"),
                ("30", "1"),
                ("50", "1"),
                ("100", "1"),
                ("100", "1.1"),
                ("100", "1.67"),
                ("30", "1.67"),
            ]
        ]
        flexures = [x.flexure for x in results if x.flexure is not None]
        assert len(flexures) == 7
        if identity == "I04":
            assert [f.available for f in flexures[:4]] == sorted(
                [f.available for f in flexures[:4]], reverse=True
            )
        elif identity == "I05":
            assert flexures[3].available <= flexures[4].available <= flexures[5].available
        else:
            assert all(f.nominal <= f.mp for f in flexures)
            assert flexures[-1].plastic_cap_applied
    elif identity == "I07":
        r = request("-10", "15")
        record_us = record(r)
        result = evaluate_clear_plate(r, ClearContext((record_us,)))
        si = replace(
            r,
            demand=replace(
                r.demand,
                axial=r.demand.axial.to(Unit.KN),
                moment_z=q(15, Unit.KIP_IN).to(Unit.KN_MM),
            ),
            lb=q(10).to(Unit.MM),
        )
        record_si = replace(record_us, request=si)
        with localcontext() as c:
            c.prec = 6
            c.rounding = ROUND_DOWN
            other = evaluate_clear_plate(si, ClearContext((record_si,)))
        assert result.fingerprint == other.fingerprint
        assert result.checks == other.checks
        assert result.flexure == other.flexure
    elif identity == "I08":
        assert not evaluate(
            negative_request("P2_NEG_RAW_ECCENTRICITY_WITHOUT_RESOLVED_MOMENT")
        ).checks
        r = request()
        assert (
            evaluate(replace(r, demand=replace(r.demand, raw_eccentricity=q(99)))).checks
            == evaluate(r).checks
        )
    elif identity == "I09":
        assert not evaluate(replace(request(), e4="UNKNOWN")).compression_axes
    elif identity == "I10":
        a = evaluate(request("0", "20"))
        assert a.flexure is not None
        assert a.flexure.cb == 1
        assert (
            "STAINLESS_CB_CREDIT_NOT_QUALIFIED"
            in evaluate(replace(request("0", "20"), cb=D("1.1"))).method_status
        )
    elif identity == "I11":
        assert not evaluate(negative_request("P2_NEG_NONZERO_TORSION")).checks
        assert not evaluate(negative_request("P2_NEG_COMBINED_NORMAL_SHEAR")).checks
    elif identity == "I12":
        assert not evaluate(replace(request(), csm=True)).checks
    else:
        assert identity == "I13"
        before = snapshot(request())
        result = evaluate(request())
        assert before == snapshot(request())
        assert not result.family_activation
        assert "FASTENER_NOT_EVALUATED" in result.external_scopes


def test_golden_and_artifact_hashes() -> None:
    assert (
        hashlib.sha256(PATH.read_bytes()).hexdigest().upper()
        == "2A7082F9D4E7B03A62B8E74B96D06F0C843437C2A02746DF3A0B1EBF78C8935B"
    )
    assert tuple(len(G[k]) for k in ("positive_cases", "negative_cases", "invariants")) == (
        14,
        17,
        13,
    )


@pytest.mark.parametrize("s", ["25.4344", "25.4345", "25.44", "25.45", "25.46"])
def test_owner_cap_both_axes_boundary_retains_raw(s: str) -> None:
    with localcontext() as c:
        c.prec = 100
        ry, rz = D(".375") / D(12).sqrt(), D(4) / D(12).sqrt()
        r = replace(
            request(),
            y_stability=EffectiveLength(D(1), q(D(s) * ry), "TEST"),
            z_stability=EffectiveLength(D(1), q(D(s) * rz), "TEST"),
        )
    result = evaluate(r)
    for axis in result.compression_axes:
        assert axis.fn.magnitude <= 25
        assert axis.fn.magnitude == min(D(25), axis.fn_raw.magnitude)
        assert axis.cap_applied == (axis.fn_raw.magnitude > 25)
    if s == "25.4345":
        assert all(a.cap_applied for a in result.compression_axes)
        assert min(a.available.magnitude for a in result.compression_axes) == D("33.75")


@pytest.mark.parametrize(
    ("nominal", "credit"), [(".1875", False), (".1875", True), (".1876", False), (".1", False)]
)
def test_snapshot_native_thickness_and_tension_are_consumed_verbatim(
    nominal: str, credit: bool
) -> None:
    r = request("1")
    r = replace(r, section=replace(r.section, nominal_thickness=q(nominal)))
    s = snapshot(r, credit)
    result = evaluate_clear_plate(r, ClearContext((record(r, s),)))
    assert result.properties is not None
    assert result.properties.t == s.design_thickness.to(Unit.IN).magnitude
    assert result.authority is not None
    assert result.authority.snapshot == s
    assert result.checks[0].method == "FROZEN_C2_P1_TENSION_ENDPOINT"


@pytest.mark.parametrize(
    "kind",
    ["empty", "duplicate", "mismatch", "id", "hash_length", "hash_content", "geometry", "demand"],
)
def test_untrusted_catalogue_never_produces_resistance(kind: str) -> None:
    r = request()
    rec = record(r)
    records: tuple[TrustedClearRecord, ...] = (rec,)
    if kind == "empty":
        records = ()
    elif kind == "duplicate":
        records = (rec, rec)
    elif kind == "mismatch":
        records = (replace(rec, request=request("-11")),)
    else:
        field, value = {
            "id": ("id", ""),
            "hash_length": ("content_sha256", "a"),
            "hash_content": ("content_sha256", "z" * 64),
            "geometry": ("geometry_authority", ""),
            "demand": ("demand_authority", ""),
        }[kind]
        records = (replace(rec, **cast(dict[str, Any], {field: value})),)
    result = evaluate_clear_plate(r, ClearContext(records))
    assert result.material_source_status == "STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED"
    assert not result.checks


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_sha256", "a" * 64),
        ("p1_provider", "OTHER"),
        ("source_system", "SI"),
        ("direct_transfer", "PARTIAL"),
        ("material_identity", ""),
        ("material_fingerprint", "x"),
        ("p1_fingerprint", "x"),
        ("fy", q(30, Unit.KSI)),
        ("fu", q(80, Unit.KSI)),
        ("elastic_modulus", q(29000, Unit.KSI)),
        ("design_thickness", q(1)),
        ("available_tension", q(0, Unit.KIP)),
    ],
)
def test_invalid_snapshot_binding_fails(field: str, value: object) -> None:
    r = request()
    s = replace(snapshot(r), **cast(dict[str, Any], {field: value}))
    result = evaluate_clear_plate(r, ClearContext((record(r, s),)))
    assert not result.checks
    assert result.material_source_status != "VERIFIED"


@pytest.mark.parametrize(
    "kind",
    [
        "width",
        "bounds",
        "basis",
        "id",
        "fabrication",
        "missing_m",
        "frame",
        "sign",
        "reference",
        "zero_k",
        "negative_l",
        "z_missing",
        "e4_source",
        "lb_zero",
        "lb_source",
        "cb_low",
        "pure_shear",
        "response",
        "bad_unit",
        "zero",
    ],
)
def test_additional_fail_closed_and_zero_paths(kind: str) -> None:
    r = request("-10", "15")
    if kind in ("width", "bounds", "basis", "id", "fabrication"):
        edits: Any = {
            "width": {"width": q(-1)},
            "bounds": {"bounds": (q(0), q(0), q(-2), q(2))},
            "basis": {"width_basis": "WHITMORE"},
            "id": {"id": ""},
            "fabrication": {"fabrication": "WELDED"},
        }[kind]
        r = replace(r, section=replace(r.section, **edits))
    elif kind in (
        "missing_m",
        "frame",
        "sign",
        "reference",
        "response",
        "bad_unit",
        "pure_shear",
        "zero",
    ):
        de: Any = {
            "missing_m": {"moment_z": None},
            "frame": {"frame": "OTHER"},
            "sign": {"sign_convention": "UNKNOWN"},
            "reference": {"reference": (q(0, Unit.KIP), q(0), q(0))},
            "response": {"requires_response_generation": True},
            "bad_unit": {"axial": q(1)},
            "pure_shear": {
                "axial": q(0, Unit.KIP),
                "moment_z": q(0, Unit.KIP_IN),
                "shear": q(1, Unit.KIP),
            },
            "zero": {"axial": q(0, Unit.KIP), "moment_z": q(0, Unit.KIP_IN)},
        }[kind]
        r = replace(r, demand=replace(r.demand, **de))
    else:
        edits = {
            "zero_k": {"y_stability": EffectiveLength(D(0), q(2), "TEST")},
            "negative_l": {"y_stability": EffectiveLength(D(1), q(-2), "TEST")},
            "z_missing": {"z_stability": None},
            "e4_source": {"e4_authority": ""},
            "lb_zero": {"lb": q(0)},
            "lb_source": {"lb_authority": ""},
            "cb_low": {"cb": D(".9")},
        }[kind]
        r = replace(r, **edits)
    # Deliberately corrupt a previously valid snapshot/section binding to exercise
    # P2 rejection. The frozen provider correctly refuses to originate bad geometry.
    s = replace(snapshot(request()), section=r.section)
    result = evaluate_clear_plate(r, ClearContext((record(r, s),)))
    assert not result.checks
    assert result.numerical_comparison == "NOT_EVALUATED"


def test_failure_visible_despite_external_response_and_tension_second_check_governs() -> None:
    r = request("-100", "100")
    result = evaluate(
        replace(
            r, family_activation_requested=True, demand=replace(r.demand, response_qualified=False)
        )
    )
    assert result.numerical_comparison == "FAIL"
    assert result.response_status
    assert not result.family_activation
    second = evaluate(request("1", "30", lb="200"))
    assert second.governing_check == "H2_COMPRESSION_SIDE"
    assert second.numerical_comparison == "FAIL"


def test_pi_and_independent_e3_boundary_values() -> None:
    with localcontext() as c:
        c.prec = 100
        r = request(length="12")
        a = evaluate(r).compression_axes[0]
        expected_fe = PI**2 * D(28000) * (D(".375") ** 2 / 12) / 12**2
        assert rounded(a.fe.magnitude) == rounded(expected_fe)
        assert a.fn_raw.magnitude == a.fn.magnitude


@pytest.mark.parametrize(
    "field",
    ["load", "reference", "method", "sign", "length", "e4", "lb", "cb", "snapshot", "tolerance"],
)
def test_every_result_affecting_authority_changes_fingerprint(field: str) -> None:
    r = request("-10", "15")
    original = record(r)
    changed = {
        "load": replace(r, demand=replace(r.demand, load_combination="LRFD_2")),
        "reference": replace(r, demand=replace(r.demand, reference=(q(1), q(0), q(0)))),
        "method": replace(r, demand=replace(r.demand, response_method="OTHER_RESOLVED_METHOD")),
        "sign": replace(r, demand=replace(r.demand, moment_z=q(-15, Unit.KIP_IN))),
        "length": replace(r, y_stability=EffectiveLength(D(2), q(2), "TEST")),
        "e4": replace(r, e4_authority="OTHER_E4_RECORD"),
        "lb": replace(r, lb=q(11)),
        "cb": replace(r, cb=D("1.1"), cb_authority="TRUSTED_F1_PROFILE:TEST"),
        "snapshot": r,
        "tolerance": r,
    }[field]
    rec = replace(original, request=changed)
    if field == "snapshot":
        rec = replace(rec, snapshot=replace(rec.snapshot, p1_fingerprint="c" * 64))
    if field == "tolerance":
        rec = replace(rec, snapshot=replace(rec.snapshot, tolerance_evidence="OTHER_EVIDENCE"))
    first = evaluate_clear_plate(r, ClearContext((original,)))
    second = evaluate_clear_plate(changed, ClearContext((rec,)))
    assert first.fingerprint != second.fingerprint
    if field == "sign":
        assert first.checks == second.checks


def test_monotonic_both_axes_across_capped_e3_junctions() -> None:
    with localcontext() as c:
        c.prec = 100
        lower, upper = D(".76") * (D(28000) / 25).sqrt(), D("5.62") * (D(28000) / 25).sqrt()
        slendernesses = [lower + D(i) / 10000 for i in range(-20, 200)] + [
            upper + D(i) / 10000 for i in range(-20, 21)
        ]
        strengths = []
        for s in slendernesses:
            r = replace(
                request(),
                y_stability=EffectiveLength(D(1), q(s * D(".375") / D(12).sqrt()), "TEST"),
                z_stability=EffectiveLength(D(1), q(s * 4 / D(12).sqrt()), "TEST"),
            )
            strengths.append(min(a.available.magnitude for a in evaluate(r).compression_axes))
        assert strengths == sorted(strengths, reverse=True)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_plan_scalars_rejected_before_fingerprinting(value: str) -> None:
    with pytest.raises(ValueError, match="finite"):
        replace(request(), cb=D(value))
    with pytest.raises(ValueError, match="finite"):
        EffectiveLength(D(value), q(2), "TEST")
