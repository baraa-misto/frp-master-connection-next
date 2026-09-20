"""Exact C2-R trust, material dependence, conservation and source-total regressions."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    angle_fingerprint,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.stainless_response import (
    MODES,
    ContactRecord,
    NativeResponseEvidence,
    PryingRecord,
    ResponseContext,
    ResponseRequest,
    ResponseResult,
    ResponseShaft,
    ShaftLayer,
    TrustedResponseRecord,
    evaluate_stainless_response,
)
from tests.calculation.test_stainless_angle import G, q

D = Decimal


def vector(
    x: str | int = 0, y: str | int = 0, z: str | int = 0, unit: Unit = Unit.KIP
) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(q(x, unit), q(y, unit), q(z, unit))


def wrench(f: str | int = 0, m: str | int = 0) -> AngleWrench:
    return AngleWrench(vector(unit=Unit.IN), vector(f), vector(m, unit=Unit.KIP_IN))


def request(mode: str = MODES[4]) -> ResponseRequest:
    return ResponseRequest(
        "TEST_NATIVE_ROUTE",
        ("BODY",),
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "ACTION",
        "LRFD",
        "GLOBAL_RIGHT_HAND",
        wrench(11, 7),
        (wrench(11, 7),),
        mode,
    )


def shaft() -> ResponseShaft:
    return ResponseShaft(
        "SHAFT",
        (
            ShaftLayer("L1", "P1", vector(5), vector(5)),
            ShaftLayer("L2", "P2", vector(-3), vector(2)),
            ShaftLayer("L3", "P3", vector(-2), vector(0)),
        ),
        vector(0),
        vector(unit=Unit.IN),
        vector(1, unit=Unit.IN),
        "TEST_HARDWARE_SOURCE",
        "GLOBAL_RIGHT_HAND",
        vector(unit=Unit.IN),
    )


def record(r: ResponseRequest) -> TrustedResponseRecord:
    native = None
    if r.mode in MODES[1:4]:
        method = {
            MODES[1]: "ASCE74_FRP_STEEL_PRESCRIBED_ROWS_NATIVE_GEOMETRY_VALIDATED",
            MODES[2]: "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1",
            MODES[3]: "NATIVE_EXACT_SYMMETRY_PREDICATE",
        }[r.mode]
        fractions = {2: (D(".6"), D(".4")), 3: (D(".5"), D(".3"), D(".2"))}.get(
            len(r.output_wrenches), ()
        )
        native = NativeResponseEvidence(
            method,
            angle_fingerprint(r),
            "d" * 64,
            "TEST_NATIVE_GEOMETRY_AND_LOAD_APPLICABILITY",
            r.output_wrenches,
            fractions,
            tuple("e" * 64 for _ in r.output_wrenches),
            True,
            True,
            "NATIVE_VERIFIED_EQUILIBRIUM",
        )
    return TrustedResponseRecord(
        r,
        "TEST_RESPONSE_NOT_PRODUCTION_QUALIFICATION",
        "f" * 64,
        "TEST_MODEL_RC1",
        "2026-09-13",
        "TEST_FIXTURE",
        "TEST_BOUND_LOAD_DOMAIN",
        "NATIVE_EXACT",
        True,
        native,
    )


def evaluate(r: ResponseRequest, rec: TrustedResponseRecord | None = None) -> ResponseResult:
    return evaluate_stainless_response(r, ResponseContext((record(r) if rec is None else rec,)))


def fixture(identity: str) -> ResponseRequest:
    r = request()
    if identity == "R_ROW_FRP_STEEL_2":
        r = replace(
            r, mode=MODES[1], input_wrench=wrench(10), output_wrenches=(wrench(6), wrench(4))
        )
    elif identity == "R_ROW_FRP_STEEL_3":
        r = replace(
            r,
            mode=MODES[1],
            input_wrench=wrench(20),
            output_wrenches=(wrench(10), wrench(6), wrench(4)),
        )
    elif identity == "R_COMMON_SHAFT_CONSERVATION":
        r = replace(r, shafts=(shaft(),))
    elif identity == "R_PRYING_TOTAL_TENSION_NO_DOUBLE_ADD":
        p = PryingRecord(
            "SHAFT", q(9, Unit.KIP), q(3, Unit.KIP), q(12, Unit.KIP), "TEST_QUALIFIED_PRYING"
        )
        r = replace(r, shafts=(shaft(),), prying=(p,), contact_prying_required=True)
    elif identity == "R_LOCKED_NATIVE_SYMMETRY":
        r = replace(
            r, mode=MODES[3], input_wrench=wrench(18), output_wrenches=(wrench(9), wrench(9))
        )
    return r


@pytest.mark.parametrize(
    "case", [c for c in G["positive_cases"] if c["kind"] == "C2_R"], ids=lambda c: c["id"]
)
def test_response_positive_goldens(case: dict[str, Any]) -> None:
    r = fixture(case["id"])
    result = evaluate(r)
    assert result.status == "QUALIFIED_RESPONSE"
    assert result.demands == r.output_wrenches
    actual: dict[str, Any] = {"status": result.status}
    if "ROW" in case["id"]:
        actual["row_forces_kip"] = [
            format(w.force.x.to(Unit.KIP).magnitude, ".12f") for w in result.demands
        ]
    elif "SYMMETRY" in case["id"]:
        actual["branch_forces_kip"] = [
            format(w.force.x.to(Unit.KIP).magnitude, ".12f") for w in result.demands
        ]
    elif "SHAFT" in case["id"]:
        assert result.authority is not None
        s = result.authority.request.shafts[0]
        actual["cumulative_cuts_kip"] = [
            format(x.cut.x.to(Unit.KIP).magnitude, ".12f") for x in s.layers
        ]
        actual["closure_kip"] = format(s.terminal_reaction.x.to(Unit.KIP).magnitude, ".12f")
    elif "PRYING" in case["id"]:
        assert result.authority is not None
        actual.update(
            design_demand_kip=format(
                result.authority.request.prying[0].total.to(Unit.KIP).magnitude, ".12f"
            ),
            extra_prying_factor=None,
        )
    else:
        actual.update(
            force_kip=format(result.demands[0].force.x.to(Unit.KIP).magnitude, ".12f"),
            moment_kip_in=format(result.demands[0].moment.x.to(Unit.KIP_IN).magnitude, ".12f"),
        )
    for key, expected in case["expected"].items():
        assert actual[key] == expected


IDS = {
    "NEG_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED",
    "NEG_RESPONSE_REFERENCE_MISMATCH",
    "NEG_ASCE_ROW_COUNT_4",
    "NEG_NATIVE_SYMMETRY_NOT_QUALIFIED",
    "NEG_COMMON_SHAFT_NOT_CLOSED",
    "NEG_DUPLICATE_SHAFT_LAYER",
    "NEG_PRYING_REQUIRED_UNQUALIFIED",
    "NEG_PRYING_DOUBLE_ADD",
}


def negative(identity: str) -> tuple[ResponseRequest, TrustedResponseRecord]:
    r = fixture("R_PRYING_TOTAL_TENSION_NO_DOUBLE_ADD")
    if identity == "NEG_RESPONSE_REFERENCE_MISMATCH":
        r = replace(r, shafts=(replace(shaft(), frame="OTHER"),))
    elif identity == "NEG_ASCE_ROW_COUNT_4":
        r = replace(request(MODES[1]), input_wrench=wrench(4), output_wrenches=(wrench(1),) * 4)
    elif identity == "NEG_NATIVE_SYMMETRY_NOT_QUALIFIED":
        r = fixture("R_LOCKED_NATIVE_SYMMETRY")
    elif identity == "NEG_COMMON_SHAFT_NOT_CLOSED":
        r = replace(r, shafts=(replace(shaft(), terminal_reaction=vector(1)),))
    elif identity == "NEG_DUPLICATE_SHAFT_LAYER":
        r = replace(r, shafts=(replace(shaft(), layers=(shaft().layers[0],) * 2),))
    elif identity == "NEG_PRYING_REQUIRED_UNQUALIFIED":
        r = replace(r, prying=())
    elif identity == "NEG_PRYING_DOUBLE_ADD":
        r = replace(r, prying=(replace(r.prying[0], extra_multiplier=D(2)),))
    rec = record(r)
    if identity == "NEG_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED":
        rec = replace(rec, material_dependence_resolved=False)
    elif identity == "NEG_NATIVE_SYMMETRY_NOT_QUALIFIED":
        assert rec.native is not None
        rec = replace(rec, native=replace(rec.native, branch_identities=("a" * 64, "b" * 64)))
    return r, rec


@pytest.mark.parametrize(
    "case", [c for c in G["negative_cases"] if c["id"] in IDS], ids=lambda c: c["id"]
)
def test_response_negative_goldens(case: dict[str, str]) -> None:
    r, rec = negative(case["id"])
    result = evaluate(r, rec)
    assert result.status == case["expected_status"]
    assert not result.demands
    assert not result.family_activation


def test_native_transport_exact_offset_moment_and_no_reallocation() -> None:
    r = request(MODES[0])
    target = vector(0, 2, 0, Unit.IN)
    moved = shift_angle_wrench(r.input_wrench, target)
    r = replace(r, output_wrenches=(moved,))
    assert evaluate(r).status == "QUALIFIED_RESPONSE"
    assert moved.moment.z.to(Unit.KIP_IN).magnitude == 22
    assert evaluate(replace(r, bodies=("BODY", "OTHER"))).status != "QUALIFIED_RESPONSE"


def test_native_equal_stiffness_consumed_verbatim_and_fail_closed() -> None:
    r = request(MODES[2])
    rec = record(r)
    assert rec.native is not None
    result = evaluate(r, rec)
    assert result.demands is r.output_wrenches
    bad = replace(rec, native=replace(rec.native, equal_translation_stiffness=False))
    assert not evaluate(r, bad).demands


def test_context_is_not_established_by_request_hash_or_client_flag() -> None:
    r = request()
    assert not evaluate_stainless_response(r, ResponseContext()).demands
    assert not evaluate_stainless_response(r, ResponseContext((record(r), record(r)))).demands
    changed = replace(r, geometry_sha256="9" * 64)
    assert not evaluate(changed, record(r)).demands


def test_contact_trace_and_source_binding() -> None:
    r = request()
    contact = ContactRecord(
        "PATCH", "a" * 64, True, q(5, Unit.KIP), wrench(5), "TEST_CONTACT_MODEL", r.frame
    )
    r = replace(r, contacts=(contact,), contact_prying_required=True)
    assert evaluate(r).contact_prying_status == "QUALIFIED"
    bad = replace(r, contacts=(replace(contact, compression=q(-5, Unit.KIP)),))
    assert not evaluate(bad).demands


@pytest.mark.parametrize(
    "kind",
    [
        "native-missing",
        "native-method",
        "rows-wrong",
        "empty-shaft",
        "shaft-cut",
        "double-prying",
        "unknown-shaft",
        "public",
        "unbalanced",
    ],
)
def test_response_additional_fail_closed_boundaries(kind: str) -> None:
    r = fixture("R_ROW_FRP_STEEL_2")
    if kind == "rows-wrong":
        r = replace(r, output_wrenches=(wrench(5), wrench(5)))
    elif kind == "empty-shaft":
        r = replace(r, shafts=(replace(shaft(), layers=()),))
    elif kind == "shaft-cut":
        s = shaft()
        r = replace(
            r, shafts=(replace(s, layers=(replace(s.layers[0], cut=vector(4)), *s.layers[1:])),)
        )
    elif kind in ("double-prying", "unknown-shaft"):
        r = fixture("R_PRYING_TOTAL_TENSION_NO_DOUBLE_ADD")
        r = replace(
            r,
            prying=r.prying * 2
            if kind == "double-prying"
            else (replace(r.prying[0], shaft_id="UNKNOWN"),),
        )
    elif kind == "public":
        r = replace(r, family_activation_requested=True)
    elif kind == "unbalanced":
        r = replace(request(), output_wrenches=(wrench(10),))
    rec = record(r)
    if kind == "native-missing":
        rec = replace(rec, native=None)
    elif kind == "native-method":
        assert rec.native is not None
        rec = replace(rec, native=replace(rec.native, method="INVENTED"))
    assert not evaluate(r, rec).demands


def test_inactive_contact_requires_zero_force_and_moment() -> None:
    r = request()
    contact = ContactRecord(
        "PATCH", "a" * 64, False, q(0, Unit.KIP), wrench(), "TEST_MODEL", r.frame
    )
    assert evaluate(replace(r, contacts=(contact,))).status == "QUALIFIED_RESPONSE"
    for bad in (
        replace(contact, compression=q(1, Unit.KIP)),
        replace(contact, wrench=wrench(1)),
        replace(contact, wrench=wrench(0, 1)),
    ):
        assert not evaluate(replace(r, contacts=(bad,))).demands


def test_actual_slice8_projection_and_native_proof_consumed_verbatim() -> None:
    from frp_master_connection.calculation.in_plane_wrench_demand import (
        InPlaneWrenchRequest,
        WrenchBolt,
        calculate_in_plane_wrench_demand,
        project_rational,
    )

    native = calculate_in_plane_wrench_demand(
        InPlaneWrenchRequest(
            (WrenchBolt("B1", "0", "0"), WrenchBolt("B2", "2", "0"), WrenchBolt("B3", "0", "3")),
            ("0", "0"),
            "7",
            "5",
            "11",
            Unit.IN,
            Unit.KIP,
            Unit.KIP_IN,
        )
    )
    solution = native.solution.in_units(Unit.IN, Unit.KIP)
    assert solution.proof is not None
    assert solution.proof.passed
    output = tuple(
        AngleWrench(
            ExactQuantityVector3D(
                q(project_rational(b.coordinate[0])), q(project_rational(b.coordinate[1])), q(0)
            ),
            ExactQuantityVector3D(p.total_force.u, p.total_force.v, q(0, Unit.KIP)),
            vector(unit=Unit.KIP_IN),
        )
        for b, p in zip(solution.bolts, solution.projected_bolts(), strict=True)
    )
    r = replace(
        request(MODES[2]),
        input_wrench=AngleWrench(vector(unit=Unit.IN), vector(7, 5), vector(0, 0, 11, Unit.KIP_IN)),
        output_wrenches=output,
    )
    rec = record(r)
    assert rec.native is not None
    rec = replace(rec, native=replace(rec.native, result_sha256=native.fingerprint))
    result = evaluate(r, rec)
    assert result.status == "QUALIFIED_RESPONSE"
    assert result.demands is output
    for w, p in zip(result.demands, solution.projected_bolts(), strict=True):
        assert w.force.x == p.total_force.u
        assert w.force.y == p.total_force.v
    assert rec.native is not None
    bad = replace(rec, native=replace(rec.native, native_equilibrium_proof="FAILED"))
    assert not evaluate(r, bad).demands
