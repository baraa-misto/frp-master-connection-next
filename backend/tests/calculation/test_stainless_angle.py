"""C2-core immutable goldens and adversarial source/native-boundary checks.

Synthetic trusted records in this file are test fixtures, not product qualification.
Benchmark comparisons follow the approved twelve-place reporting precision only;
production traces retain their full private-context values.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.stainless_angle import ShapeResult, evaluate_stainless_angle
from frp_master_connection.calculation.stainless_tee import evaluate_stainless_tee
from frp_master_connection.domain.stainless_shape import (
    SOURCE,
    LocalShapeSnapshot,
    ShapeAxis,
    ShapeContext,
    ShapeDemand,
    ShapeElement,
    ShapeProduct,
    ShapeRequest,
    ShapeSection,
    ShapeStability,
    ShearLag,
    TrustedShapeRecord,
)

D = Decimal
ROOT = Path(__file__).resolve().parents[3]
G = json.loads(
    (
        ROOT
        / "backend/tests/golden/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_GOLDEN_BENCHMARKS_RC1.json"
    ).read_bytes()
)


def q(x: str | int | Decimal, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(x, unit)


def request(form: str = "ANGLE", checks: tuple[str, ...] = ("TENSION",)) -> ShapeRequest:
    origin = (q(0), q(0), q(0))
    tee = form == "TEE"
    section = ShapeSection(
        "TEST_SECTION",
        form,
        "b" * 64,
        "TEST_ONLY_ANALYTICAL_GEOMETRY",
        q("2.625" if tee else "2.859375", Unit.IN2),
        origin,
        (
            ShapeElement("LEG1", q(4), q(".375"), "TEST_UNSTIFFENED"),
            ShapeElement("LEG2", q(4), q(".375"), "TEST_UNSTIFFENED"),
        ),
        (
            ShapeAxis("w", q(1), D("1.2" if tee else ".8"), D("1.2" if tee else ".8")),
            ShapeAxis("z", q(1), D(".6"), D(".6")),
        ),
        net_area=q("2.2" if tee else "2.5", Unit.IN2),
        net_area_source="TEST_NET_AREA",
    )
    demand = ShapeDemand(
        "LOAD",
        "TEST_ROUTE",
        "BODY",
        "REGION",
        "LRFD",
        section.principal_frame,
        origin,
        q(0, Unit.KIP),
        q(0, Unit.KIP_IN),
        q(0, Unit.KIP_IN),
        q(0, Unit.KIP),
        q(0, Unit.KIP_IN),
    )
    return ShapeRequest(
        ShapeProduct("TEST_PRODUCT", "TEST_ONLY_NOT_PRODUCTION_QUALIFICATION", "a" * 64),
        section,
        demand,
        checks,
        ShearLag(
            "CASE2" if tee else "CASE8",
            "TEST_TRANSFER",
            x=q(".4") if tee else None,
            length=q(4) if tee else None,
            fasteners_per_line=4,
        ),
        (ShapeElement("SHEAR", q(3 if tee else 4), q(".375"), "TEST_SHEAR_BOUNDARY"),),
        (
            ShapeStability("w", q(40 if tee else 50), "TEST_STABILITY", q(10), q(20), q(60)),
            ShapeStability(
                "z",
                q(25 if tee else "33.3333333333333333333333333333"),
                "TEST_STABILITY",
                q(10),
                q(20),
                q(60),
            ),
        ),
        q(12 if tee else 15, Unit.KSI),
        "TEST_E4_ANALYSIS",
    )


def record(r: ShapeRequest) -> TrustedShapeRecord:
    return TrustedShapeRecord(
        r,
        "TEST_TRUSTED",
        "c" * 64,
        "TEST_SECTION_CERTIFICATE",
        "d" * 64,
        r.demand,
        "TEST_RESOLVED_C2_R_RESPONSE",
    )


def evaluate(r: ShapeRequest, rec: TrustedShapeRecord | None = None) -> ShapeResult:
    evaluator = evaluate_stainless_tee if r.section.form == "TEE" else evaluate_stainless_angle
    return evaluator(r, ShapeContext((record(r) if rec is None else rec,)))


def values(result: ShapeResult, name: str) -> dict[str, Decimal]:
    return dict(next(t.values for t in result.traces if t.method == name))


def fixture(case: dict[str, Any]) -> ShapeRequest:
    identity, i = case["id"], case["input"]
    check = next(c for c in ("H2", "TENSION", "SHEAR", "FLEXURE", "COMPRESSION") if c in identity)
    r = request("TEE" if case["kind"] == "C2_T" else "ANGLE", (check,))
    if identity == "A_TENSION_D3_CASE2":
        r = replace(r, shear_lag=ShearLag("CASE2", "TEST", x=q(i["x_in"]), length=q(i["l_in"])))
    if check == "SHEAR" and "d_in" not in i and "lambda" in i:
        with localcontext() as c:
            c.prec = 100
            # Independent full physical element dimensions, not a prescribed Cv value.
            thickness = D(".375")
            r = replace(
                r,
                shear_elements=(replace(r.shear_elements[0], width=q(D(i["lambda"]) * thickness)),),
            )
    if check == "FLEXURE":
        axis = replace(r.section.axes[0], smin_in3=D(i["Smin_in3"]))
        st = replace(
            r.stability[0],
            lb=q(i["Lb_in"]),
            ly=q(i["Ly_in"]),
            lr=q(i["Lr_in"]),
            fcr=q(i["Fcr_ksi"], Unit.KSI) if "Fcr_ksi" in i else None,
        )
        r = replace(
            r,
            section=replace(r.section, axes=(axis, r.section.axes[1])),
            stability=(st, r.stability[1]),
        )
    if check == "H2":
        axial = D(i["Pr_kip"])
        if "COMPRESSION" in identity:
            axial = -axial
        r = replace(
            r,
            demand=replace(
                r.demand,
                axial=q(axial, Unit.KIP),
                moment_w=q(i["Mrw_kip_in"], Unit.KIP_IN),
                moment_z=q(i["Mrz_kip_in"], Unit.KIP_IN),
            ),
        )
    return r


def actual_values(result: ShapeResult) -> dict[str, str]:
    actual: dict[str, str] = {}
    for t in result.traces:
        v = dict(t.values)
        if t.method == "D2_D3":
            actual.update(
                U=format(v["U"], ".12f"),
                gross_yield_design_kip=format(v["gross_yield"], ".12f"),
                net_rupture_design_kip=format(v["net_rupture"], ".12f"),
                available_tension_kip=format(v["available"], ".12f"),
                governing=t.governing,
            )
        elif t.method.startswith("G6:"):
            actual.update(
                Cv2=format(v["Cv2"], ".12f"),
                branch=t.governing,
                available_shear_kip=format(v["available"], ".12f"),
            )
        elif t.method == "F10:w":
            actual.update(
                alpha_LT=format(v["alpha_LT"], ".12f"),
                Mn_kip_in=format(v["nominal"], ".12f"),
                Mc_kip_in=format(v["available"], ".12f"),
                branch=t.governing,
            )
        elif t.method in ("E3:w", "E3:z", "E4"):
            actual["Pc_" + t.method.replace("E3:", "") + "_kip"] = format(v["available"], ".12f")
        elif t.method == "COMPRESSION":
            actual.update(
                available_compression_kip=format(v["available"], ".12f"),
                governing="E4_FLEXURAL_TORSIONAL_BUCKLING" if t.governing == "E4" else t.governing,
            )
        elif t.method == "H2":
            actual.update({k: format(x, ".12f") for k, x in v.items()})
            actual.update(governing=t.governing, status="FAIL" if v["interaction"] > 1 else "PASS")
    return actual


@pytest.mark.parametrize(
    "case", [c for c in G["positive_cases"] if c["kind"] != "C2_R"], ids=lambda c: c["id"]
)
def test_shape_positive_goldens(case: dict[str, Any]) -> None:
    result = evaluate(fixture(case))
    assert result.traces, result
    actual = actual_values(result)
    for key, expected in case["expected"].items():
        assert actual[key] == expected, (case["id"], key, actual[key], expected)


def negative(identity: str) -> tuple[ShapeRequest, TrustedShapeRecord]:
    r = request(checks=("H2",))
    r = replace(r, demand=replace(r.demand, axial=q(-10, Unit.KIP)))
    changes = {
        "NEG_PRODUCT_A479_NOT_SELECTED": replace(
            r, product=replace(r.product, specification="ASTM A479/A479M")
        ),
        "NEG_PRODUCT_COLD_FINISHED": replace(
            r, product=replace(r.product, condition="COLD_FINISHED")
        ),
        "NEG_PRODUCT_FORMED_BENT": replace(r, product=replace(r.product, processing="FORMED_BENT")),
        "NEG_PRODUCT_LASER_FUSED": replace(r, product=replace(r.product, processing="LASER_FUSED")),
        "NEG_PRODUCT_WELDED_BUILT_UP": replace(r, product=replace(r.product, welded=True)),
        "NEG_ANGLE_UNEQUAL_LEG_COMPRESSION": replace(
            r, section=replace(r.section, equal_leg=False)
        ),
        "NEG_SHAPE_SLENDER_ELEMENT": replace(
            r, section=replace(r.section, elements=(replace(r.section.elements[0], width=q(100)),))
        ),
        "NEG_COMPRESSION_E4_RECORD_MISSING": replace(r, e4_fe=None),
        "NEG_F10_STABILITY_MISSING": replace(r, checks=("FLEXURE",), stability=()),
        "NEG_TORSION_NONZERO": replace(r, demand=replace(r.demand, torsion=q(1, Unit.KIP_IN))),
        "NEG_COMBINED_NORMAL_SHEAR": replace(r, demand=replace(r.demand, shear=q(1, Unit.KIP))),
        "NEG_NET_AREA_NOT_RESOLVED": replace(
            r, checks=("TENSION",), section=replace(r.section, net_area=None)
        ),
        "NEG_SHEAR_LAG_NOT_RESOLVED": replace(r, checks=("TENSION",), shear_lag=None),
        "NEG_TEE_D3_CASE7_ATTEMPT": replace(request("TEE"), shear_lag=ShearLag("CASE7", "TEST")),
        "NEG_TEE_JUNCTION_LOCAL_METHOD_REQUIRED": replace(
            request("TEE"), local_mechanism_required=True
        ),
        "NEG_ANGLE_HEEL_PRYING_LOCAL_METHOD_REQUIRED": replace(r, local_mechanism_required=True),
        "NEG_PUBLIC_FAMILY_ACTIVATION": replace(r, family_activation_requested=True),
    }
    r = changes.get(identity, r)
    rec = record(r)
    if identity == "NEG_SECTION_PROPERTIES_UNTRUSTED":
        rec = replace(rec, section_qualification="")
    if identity == "NEG_LOCAL_REGION_SNAPSHOT_MISMATCH":
        rec = replace(
            rec,
            local_snapshots=(
                LocalShapeSnapshot(
                    "C2_P1_AISC_370_25_FLAT_PLATE_LRFD_RC1_R1",
                    "OTHER",
                    r.demand.region,
                    angle_fingerprint(r),
                    "e" * 64,
                    SOURCE,
                    "TEST_LOCAL",
                    "PASS",
                ),
            ),
        )
    return r, rec


SHAPE_NEGATIVES = [
    c
    for c in G["negative_cases"]
    if c["id"]
    not in {
        "NEG_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED",
        "NEG_RESPONSE_REFERENCE_MISMATCH",
        "NEG_ASCE_ROW_COUNT_4",
        "NEG_NATIVE_SYMMETRY_NOT_QUALIFIED",
        "NEG_COMMON_SHAFT_NOT_CLOSED",
        "NEG_DUPLICATE_SHAFT_LAYER",
        "NEG_PRYING_REQUIRED_UNQUALIFIED",
        "NEG_PRYING_DOUBLE_ADD",
    }
]


@pytest.mark.parametrize("case", SHAPE_NEGATIVES, ids=lambda c: c["id"])
def test_shape_negative_goldens(case: dict[str, str]) -> None:
    r, rec = negative(case["id"])
    result = evaluate(r, rec)
    assert result.status == case["expected_status"]
    assert not result.traces
    assert not result.family_activation


def test_i11_owner_supersedes_original_without_changing_artifact() -> None:
    r = request(checks=("H2",))
    # Compression is monotone independently in each positive demand magnitude.
    r = replace(
        r,
        demand=replace(
            r.demand, axial=q(-1, Unit.KIP), moment_w=q(1, Unit.KIP_IN), moment_z=q(1, Unit.KIP_IN)
        ),
    )
    base = values(evaluate(r), "H2")["interaction"]
    for d in (
        replace(r.demand, axial=q(-2, Unit.KIP)),
        replace(r.demand, moment_w=q(2, Unit.KIP_IN)),
        replace(r.demand, moment_z=q(2, Unit.KIP_IN)),
    ):
        assert values(evaluate(replace(r, demand=d)), "H2")["interaction"] > base
    # Supplied tensile counterexample uses inelastic F10 capacity, not Mct.
    r = replace(
        r,
        stability=(replace(r.stability[0], lb=q(40)), r.stability[1]),
        demand=replace(
            r.demand, axial=q(1, Unit.KIP), moment_w=q(4, Unit.KIP_IN), moment_z=q(0, Unit.KIP_IN)
        ),
    )
    first = values(evaluate(r), "H2")
    second = values(evaluate(replace(r, demand=replace(r.demand, axial=q(2, Unit.KIP)))), "H2")
    assert first["H2_1"] < second["H2_1"]
    assert first["H2_2"] > second["H2_2"]
    assert first["interaction"] == max(first["H2_1"], first["H2_2"])
    assert second["interaction"] == max(second["H2_1"], second["H2_2"])
    assert format(first["interaction"], ".12f") == "0.457774159751"
    assert format(second["interaction"], ".12f") == "0.442230747487"


def test_ambient_decimal_context_does_not_change_result() -> None:
    r = request(checks=("COMPRESSION", "FLEXURE", "TENSION", "SHEAR"))
    baseline = evaluate(r)
    with localcontext() as c:
        c.prec, c.rounding = 6, ROUND_DOWN
        assert evaluate(r) == baseline


@pytest.mark.parametrize(
    "kind",
    [
        "product",
        "section",
        "empty-shear",
        "bad-shear",
        "f10-length",
        "f10-elastic-missing",
        "frame",
        "magnitude",
        "plan",
    ],
)
def test_additional_invalid_inputs_return_no_capacity(kind: str) -> None:
    r = request()
    choices = {
        "product": replace(r, product=replace(r.product, strength_credit=True)),
        "section": replace(r, section=replace(r.section, area=q(0, Unit.IN2))),
        "empty-shear": replace(r, checks=("SHEAR",), shear_elements=()),
        "bad-shear": replace(
            r, checks=("SHEAR",), shear_elements=(replace(r.shear_elements[0], thickness=q(0)),)
        ),
        "f10-length": replace(
            r, checks=("FLEXURE",), stability=(replace(r.stability[0], ly=q(-1)), r.stability[1])
        ),
        "f10-elastic-missing": replace(
            r, checks=("FLEXURE",), stability=(replace(r.stability[0], lb=q(80)), r.stability[1])
        ),
        "frame": replace(r, demand=replace(r.demand, frame="OTHER")),
        "magnitude": replace(r, demand=replace(r.demand, moment_w=q(-1, Unit.KIP_IN))),
        "plan": replace(r, checks=("INVENTED",)),
    }
    assert not evaluate(choices[kind]).traces


def test_shear_lag_case1_and_invalid_case2_and_rupture_governs() -> None:
    r = request()
    lag = ShearLag("CASE1", "TEST", all_elements_direct=True)
    assert values(evaluate(replace(r, shear_lag=lag)), "D2_D3")["U"] == 1
    bad = ShearLag("CASE2", "TEST", x=q(4), length=q(2))
    assert not evaluate(replace(r, shear_lag=bad)).traces
    small = replace(r, section=replace(r.section, net_area=q(".1", Unit.IN2)))
    assert evaluate(small).traces[0].governing == "D2_NET_RUPTURE"


def test_local_snapshot_binding_never_replaces_whole_body_authority() -> None:
    r = replace(request(), local_mechanism_required=True)
    snapshot = LocalShapeSnapshot(
        "C2_P2_AISC_370_25_CLEAR_RECTANGULAR_PLATE_LRFD_RC1",
        r.demand.body,
        r.demand.region,
        angle_fingerprint(r),
        "e" * 64,
        SOURCE,
        "TEST_EXPLICIT_LOCAL_MECHANISM",
        "PASS",
    )
    rec = replace(
        record(r), local_snapshots=(snapshot,), local_qualification="TEST_EOR_LOCAL_COVERAGE"
    )
    assert evaluate(r, rec).local_status == "QUALIFIED"
    assert evaluate(r, rec).traces[0].method == "D2_D3"
    bad = replace(rec, local_snapshots=(replace(snapshot, status="FAIL"),))
    assert not evaluate(r, bad).traces


def test_shape_context_mismatch_and_qualification_fail_closed() -> None:
    r = request()
    assert not evaluate_stainless_angle(r, ShapeContext()).traces
    assert not evaluate_stainless_angle(r, ShapeContext((record(r), record(r)))).traces
    assert not evaluate(r, replace(record(r), response_authority="")).traces
    assert not evaluate(replace(r, product=replace(r.product, id="OTHER")), record(r)).traces


def test_h2_tensile_relief_is_not_overridden_by_standalone_flexural_ratio() -> None:
    r = request(checks=("H2",))
    r = replace(
        r,
        stability=(replace(r.stability[0], lb=q(40)), r.stability[1]),
        demand=replace(r.demand, axial=q(20, Unit.KIP), moment_w=q(10, Unit.KIP_IN)),
    )
    result = evaluate(r)
    assert values(result, "F10:w")["available"] < 10
    assert values(result, "H2")["interaction"] < 1
    assert result.status == "ISOLATED_COVERED_CHECKS_PASS"
