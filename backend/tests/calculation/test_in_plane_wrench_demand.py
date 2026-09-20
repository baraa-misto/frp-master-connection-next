"""Slice 8 RC1/R1 G1-G80, independent mechanics, legacy seams and portability."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, fields, replace
from decimal import ROUND_DOWN, Context, Decimal, Inexact, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, cast
from unittest.mock import PropertyMock, patch

import pytest

from frp_master_connection.calculation import eccentric_demand as legacy
from frp_master_connection.calculation import in_plane_wrench_demand as engine
from frp_master_connection.calculation import resistance_handoff as handoff
from frp_master_connection.calculation.in_plane_wrench_demand import (
    COMPATIBILITY,
    CONTRACT,
    METHOD,
    PROJECTION,
    ExactRecovery,
    ExactWrenchProof,
    ExactWrenchSolution,
    InPlaneWrenchRequest,
    InPlaneWrenchResult,
    NumericInput,
    WrenchBolt,
    WrenchInputError,
    calculate_in_plane_wrench_demand,
    project_rational,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    calculate_multirow_connection,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    FlangePlaneDemand,
    evaluate_asymmetric_two_plane_bolt,
)
from tests.calculation.test_eccentric_demand import _input as legacy_input
from tests.calculation.test_resistance_handoff import _handoff_input

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT
    / "backend/tests/golden"
    / "calculation_slice_8_in_plane_bolt_group_wrench_demand_golden_benchmarks_rc1_r1.json"
)
DATA = json.loads(GOLDEN.read_text(encoding="utf-8"))
CASES = DATA["benchmarks"]
COORDS = (("-1.5", "-.75"), ("1.5", "-.75"), ("-1.5", ".75"), ("1.5", ".75"))


def expected(number: int) -> dict[str, Any]:
    return cast(dict[str, Any], CASES[number - 1]["expected"])


def request(number: int = 31) -> InPlaneWrenchRequest:
    e = expected(number)
    reference = e.get("reference_A_B_in", ["0", "0"])
    return InPlaneWrenchRequest(
        tuple(WrenchBolt(f"B{i}", a, b) for i, (a, b) in enumerate(COORDS, 1)),
        (reference[0], reference[1]),
        e["F_A_kip"],
        e["F_B_kip"],
        e.get("M_C_kip_in", e.get("M_C_R_kip_in", "0")),
        Unit.IN,
        Unit.KIP,
        Unit.KIP_IN,
    )


def result(number: int = 31) -> InPlaneWrenchResult:
    return calculate_in_plane_wrench_demand(request(number))


def solution(number: int = 31) -> ExactWrenchSolution:
    return result(number).solution.in_units(Unit.IN, Unit.KIP)


def independent_proof(s: ExactWrenchSolution) -> None:
    assert s.proof is not None
    assert s.proof.passed
    n = len(s.bolts)
    assert s.centroid == tuple(sum(p[i] for _, p in s.coordinates) / n for i in range(2))
    assert s.polar_sum == sum(sum(x * x for x in b.delta) for b in s.bolts)
    mc = (
        s.reference_moment
        + (s.reference[0] - s.centroid[0]) * s.force[1]
        - (s.reference[1] - s.centroid[1]) * s.force[0]
    )
    assert s.centroid_moment == mc
    for b in s.bolts:
        assert b.direct == tuple(v / n for v in s.force)
        correction = (
            (-mc * b.delta[1] / s.polar_sum, mc * b.delta[0] / s.polar_sum) if mc else (0, 0)
        )
        assert b.correction == correction
        assert b.total == tuple(d + m for d, m in zip(b.direct, correction, strict=True))
        assert b.magnitude_squared == sum(q * q for q in b.total)
    assert s.proof.force_a.target == s.proof.force_a.recovered == s.force[0]
    assert s.proof.force_b.target == s.proof.force_b.recovered == s.force[1]
    assert s.proof.centroid_moment.target == s.proof.centroid_moment.recovered == mc
    assert (
        s.proof.reference_moment.target == s.proof.reference_moment.recovered == s.reference_moment
    )


def check_numeric(number: int, s: ExactWrenchSolution, bolt_index: int | None = None) -> None:
    e = expected(number)
    if bolt_index is not None:
        bolt = s.bolts[bolt_index]
        projected = s.projected_bolts()[bolt_index]
        assert bolt.total == (Fraction(e["q_A_exact"]), Fraction(e["q_B_exact"]))
        assert projected.total_force.u.magnitude == Decimal(e["q_A_decimal80"])
        assert projected.total_force.v.magnitude == Decimal(e["q_B_decimal80"])
        if "magnitude_squared_exact" in e:
            assert bolt.magnitude_squared == Fraction(e["magnitude_squared_exact"])
        if "magnitude_decimal80" in e:
            assert projected.total_force_magnitude.magnitude == Decimal(e["magnitude_decimal80"])
    elif "sum_q_A_exact" in e:
        assert s.proof is not None
        assert s.proof.force_a.recovered == Fraction(e["sum_q_A_exact"])
        assert s.proof.force_b.recovered == Fraction(e["sum_q_B_exact"])
    else:
        key = next(k for k in ("exact", "M_Cc_exact", "sum_M_C_exact", "sum_M_Cc_exact") if k in e)
        assert s.centroid_moment == Fraction(e[key])
        if "target_exact" in e:
            assert s.proof is not None
            assert s.proof.centroid_moment.target == Fraction(e["target_exact"])
        if "decimal80" in e:
            assert project_rational(s.centroid_moment) == Decimal(e["decimal80"])
        if "M_Cc_decimal80" in e:
            assert project_rational(s.centroid_moment) == Decimal(e["M_Cc_decimal80"])
    independent_proof(s)


@pytest.mark.parametrize("number", range(1, 81), ids=[c["id"] for c in CASES])
def test_controlled_g1_g80(number: int) -> None:
    e = expected(number)
    s = solution()
    if number == 1:
        assert result().contract == e["contract"] == CONTRACT
        assert result().method == e["method"] == METHOD
    elif number in (2, 3, 4, 9, 10, 11, 12, 13, 14, 17, 18, 19, 20, 61, 71, 77):
        for case in (31, 39, 48, 55, 63):
            independent_proof(solution(case))
        assert result().assumption == "EQUAL_IN_PLANE_TRANSLATIONAL_BOLT_STIFFNESS"
        assert "stiffness_weights" not in {f.name for f in fields(InPlaneWrenchRequest)}
    elif number == 5:
        assert tuple(p for _, p in s.coordinates) == tuple(
            tuple(Fraction(v) for v in p) for p in e["A_B_in"]
        )
    elif number == 6:
        assert s.centroid == (Fraction(e["A_exact"]), Fraction(e["B_exact"]))
    elif number == 7:
        assert tuple(b.delta for b in s.bolts) == tuple(
            tuple(Fraction(v) for v in p) for p in e["A_B_exact"]
        )
    elif number == 8:
        assert s.polar_sum == Fraction(e["exact"])
        assert project_rational(s.polar_sum) == Decimal(e["decimal80"])
    elif number == 15:
        payload = json.loads(result().canonical_json())
        field = payload["solution"]["bolts"][0]["total"][0]
        scalar = result().solution.bolts[0].total[0]
        assert field == {"numerator": str(scalar.numerator), "denominator": str(scalar.denominator)}
        assert scalar.denominator > 0
    elif number == 16:
        test_projection_and_fingerprint_ignore_ambient_context()
    elif number == 21:
        r = calculate_in_plane_wrench_demand(replace(request(), force_a=0, force_b=0, moment_c=0))
        assert r.status == e["status"]
        assert all(b.total == (Fraction(0), Fraction(0)) for b in r.solution.bolts)
        assert all(p.total_force_magnitude.magnitude == 0 for p in r.solution.projected_bolts())
    elif number in (22, 23):
        r = calculate_in_plane_wrench_demand(
            replace(
                request(22), bolts=(WrenchBolt("single", 0, 0),), moment_c=0 if number == 22 else 1
            )
        )
        assert r.status == e["status"]
        v = r.solution.in_units(Unit.IN, Unit.KIP)
        assert v.polar_sum == 0
        if number == 22:
            assert v.bolts[0].total == (Fraction(e["q_A_exact"]), Fraction(e["q_B_exact"]))
            independent_proof(v)
        else:
            assert v.bolts == ()
            assert v.proof is None
            assert v.projected_bolts() == ()
    elif number in (24, 25, 26, 27):
        invalid = {
            24: replace(request(), bolts=()),
            25: replace(request(), bolts=(WrenchBolt("a", 1, 1), WrenchBolt("b", "1.0", "1e0"))),
            26: replace(request(), force_a="NaN"),
            27: replace(request(), force_a=cast(NumericInput, 1.0)),
        }[number]
        with pytest.raises(WrenchInputError) as caught:
            calculate_in_plane_wrench_demand(invalid)
        assert caught.value.status == e["status"]
    elif number == 28 or number == 29:
        test_translation_and_sign_reversal()
    elif number in (30, 78):
        test_fingerprints_bind_physical_order_identity_wrench_and_authority()
    elif number in (31, 39, 48, 55, 63):
        v = solution(number)
        assert v.force == (Fraction(e["F_A_kip"]), Fraction(e["F_B_kip"]))
        assert v.reference_moment == Fraction(e.get("M_C_kip_in", e.get("M_C_R_kip_in", "0")))
        independent_proof(v)
    elif number in (32, 37, 38):
        check_numeric(number, s)
    elif 33 <= number <= 36:
        check_numeric(number, s, number - 33)
    elif number in (40, 45, 46):
        check_numeric(number, solution(39))
    elif 41 <= number <= 44:
        check_numeric(number, solution(39), number - 41)
    elif number == 47:
        test_r1_full_negative_web_is_lossless_exact_mirror()
    elif 49 <= number <= 52:
        check_numeric(number, solution(48), number - 49)
    elif number in (53, 54):
        check_numeric(number, solution(48))
    elif number in (56, 64, 69, 70):
        check_numeric(number, solution(55 if number == 56 else 63))
    elif 57 <= number <= 60:
        check_numeric(number, solution(55), number - 57)
    elif number == 62:
        test_r1_g62_native_mechanics_compatibility_not_decimal_identity()
    elif 65 <= number <= 68:
        check_numeric(number, solution(63), number - 65)
    elif number == 72:
        test_stage25b_consumes_actual_signed_projected_vector_and_magnitude()
    elif number == 73:
        test_common_two_plane_method_consumes_distinct_actual_vectors()
    elif number == 74:
        assert not (
            {"capacity", "resistance", "utilization"}
            & {f.name for f in fields(InPlaneWrenchResult)}
        )
        assert all(
            word not in inspect.getsource(engine)
            for word in (
                "evaluate_asymmetric_two_plane_bolt",
                "calculate_multirow_connection",
                "read_text",
                "golden",
            )
        )
    elif number in (75, 76, 80):
        test_historical_identities_and_successor_safe_scope_record()
    else:
        assert number == 79
        test_exact_us_si_equivalence()


def test_controlled_package_hashes_and_complete_golden_inventory() -> None:
    assert [int(c["id"].split("_")[0][1:]) for c in CASES] == list(range(1, 81))
    assert (
        hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper()
        == "E854CEDB44EC02115014A7139C81BCACA7531E6FE3E789DC509A21BA5B70C48C"
    )
    prefix = "CALCULATION_SLICE_8_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_"
    hashes = {
        "docs/governance/"
        + prefix
        + "DECISION_RC1.md": "DBA6F3EE9B753A29AE6930E9D2FCBEE08E8D0E6CA2523329D828114FCFAA443D",
        "docs/engineering/" + prefix + "ENGINEERING_SPECIFICATION_RC1.md": (
            "BB883A48BC340FCF4012BCBF9B6E240B3C1EDE5BE43EB6F5F7FCC4DCE9D839E6"
        ),
        (
            "docs/engineering/CALCULATION_SLICE_8_NEGATIVE_WEB_AND_"
            "STAGE25A_COMPATIBILITY_CLARIFICATION_R1.md"
        ): "C02DC1CAFB88CD67B2B857C08B7EAD7F4FB257388AB6420409E227C40C89201D",
        "docs/qa/" + prefix + "AUTHORITY_LEDGER_RC1.md": (
            "913629A90E4354990F55FD8CAD3C44476320B0DADC288AC242F8A863B4A39A07"
        ),
    }
    for name, digest in hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() == digest
        assert (
            "**END OF CALCULATION SLICE 8"
            in (ROOT / name).read_text(encoding="utf-8").rstrip().splitlines()[-1]
        )


def test_r1_full_negative_web_is_lossless_exact_mirror() -> None:
    pos, neg = request(), request(39)
    with localcontext(Context(prec=3, rounding=ROUND_DOWN)):
        assert Fraction(Decimal(str(neg.moment_c))) == -Fraction(Decimal(str(pos.moment_c)))
        assert (
            Decimal(str(pos.moment_c)).copy_negate().as_tuple()
            == Decimal(str(neg.moment_c)).as_tuple()
        )
        assert Fraction(Decimal(str(neg.force_a))) == -Fraction(Decimal(str(pos.force_a)))
        assert neg.force_b == pos.force_b
        negative = solution(39)
    assert len(str(neg.moment_c)) == len(str(pos.moment_c)) + 1
    # Mirroring FA and MC retains FB: paired locations exchange magnitudes exactly.
    positive = solution()
    for i, mirror in enumerate((1, 0, 3, 2)):
        assert negative.bolts[i].magnitude_squared == positive.bolts[mirror].magnitude_squared
    check_numeric(40, negative)
    for number in range(41, 45):
        check_numeric(number, negative, number - 41)
    check_numeric(45, negative)
    check_numeric(46, negative)


def test_projection_and_fingerprint_ignore_ambient_context() -> None:
    original = result()
    projected = original.solution.in_units(Unit.IN, Unit.KIP).projected_bolts()
    with localcontext(Context(prec=3, rounding=ROUND_DOWN, Emin=-9, Emax=9)) as ctx:
        ctx.traps[Inexact] = True
        before = ctx.copy()
        actual = result()
        assert actual == original
        assert actual.solution.in_units(Unit.IN, Unit.KIP).projected_bolts() == projected
        assert (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin, ctx.flags, ctx.traps) == (
            before.prec,
            before.rounding,
            before.Emax,
            before.Emin,
            before.flags,
            before.traps,
        )
    assert project_rational(Fraction(1, 3)) == Decimal("0." + "3" * 80)
    assert project_rational(Fraction(2, 3)) == Decimal("0." + "6" * 79 + "7")
    assert project_rational(Fraction(0)) == Decimal(0)


def test_translation_and_sign_reversal() -> None:
    r = request(63)
    shifted = replace(
        r,
        bolts=tuple(replace(b, a=Decimal(str(b.a)) + 10, b=Decimal(str(b.b)) - 7) for b in r.bolts),
        reference=("12", "-6"),
    )
    original, changed = (
        solution(63),
        calculate_in_plane_wrench_demand(shifted).solution.in_units(Unit.IN, Unit.KIP),
    )
    assert original.polar_sum == changed.polar_sum
    assert original.centroid_moment == changed.centroid_moment
    assert tuple((b.delta, b.total) for b in original.bolts) == tuple(
        (b.delta, b.total) for b in changed.bolts
    )
    reverse = replace(
        r,
        force_a=Decimal(str(r.force_a)).copy_negate(),
        force_b=Decimal(str(r.force_b)).copy_negate(),
        moment_c=Decimal(str(r.moment_c)).copy_negate(),
    )
    negated = calculate_in_plane_wrench_demand(reverse).solution.in_units(Unit.IN, Unit.KIP)
    for a, b in zip(original.bolts, negated.bolts, strict=True):
        assert a.total == tuple(-q for q in b.total)
        assert a.magnitude_squared == b.magnitude_squared
    independent_proof(changed)
    independent_proof(negated)


def test_exact_us_si_equivalence() -> None:
    r = request()

    # Finite conversion uses exact input * the existing unit factor, never a projected force.
    def converted(value: NumericInput, unit: Unit) -> Decimal:
        exact = Fraction(Decimal(str(value))) * Fraction(Q.of(1, unit).canonical_magnitude)
        with localcontext(Context(prec=200)):
            return Decimal(exact.numerator) / Decimal(exact.denominator)

    si = replace(
        r,
        bolts=tuple(
            replace(b, a=converted(b.a, Unit.IN), b=converted(b.b, Unit.IN)) for b in r.bolts
        ),
        reference=tuple(converted(v, Unit.IN) for v in r.reference),  # type: ignore[arg-type]
        force_a=converted(r.force_a, Unit.KIP),
        force_b=converted(r.force_b, Unit.KIP),
        moment_c=converted(r.moment_c, Unit.KIP_IN),
        length_unit=Unit.MM,
        force_unit=Unit.N,
        moment_unit=Unit.N_MM,
    )
    assert calculate_in_plane_wrench_demand(si) == result()
    s = result().solution
    assert s.in_units(Unit.IN, Unit.KIP).in_units(Unit.MM, Unit.N) == s
    assert s.bolts[0].total[0] / s.force[0] == solution().bolts[0].total[0] / solution().force[0]


def test_fingerprints_bind_physical_order_identity_wrench_and_authority() -> None:
    r = request()
    original = result()
    for changed in (
        replace(r, bolts=tuple(reversed(r.bolts))),
        replace(r, bolts=(replace(r.bolts[0], bolt_id="other"), *r.bolts[1:])),
        replace(r, reference=("1", "0")),
        replace(r, moment_c="2"),
        replace(r, force_b="3.7"),
        replace(r, bolts=(replace(r.bolts[0], a="-1.6"), *r.bolts[1:])),
    ):
        new = calculate_in_plane_wrench_demand(changed)
        assert new.fingerprint != original.fingerprint
        assert [b.bolt_id for b in new.solution.bolts] == [b.bolt_id for b in changed.bolts]
    for changed_result in (
        replace(original, projection="changed"),
        replace(original, compatibility="changed"),
        replace(original, status="changed"),
    ):
        assert changed_result.canonical_json() != original.canonical_json()
    payload = json.loads(original.canonical_json())
    assert payload["projection"] == PROJECTION
    assert payload["compatibility"] == COMPATIBILITY
    assert "numerator" in original.canonical_json()
    assert "denominator" in original.canonical_json()
    assert original.fingerprint == hashlib.sha256(original.canonical_json().encode()).hexdigest()
    assert not (
        {"camera", "display_rounding", "color"} & {f.name for f in fields(InPlaneWrenchRequest)}
    )


def test_r1_g62_native_mechanics_compatibility_not_decimal_identity() -> None:
    e = expected(62)
    assert e["cross_engine_per_bolt_decimal_identity_required"] is False
    assert not e["tolerance_used"]
    assert not e["legacy_rounding_emulation_in_slice8"]
    with localcontext(Context(prec=80)):
        req = legacy_input(coordinates=COORDS, force=("8", "0", "0"), reference=("0", "2", "0"))
        native = legacy.calculate_eccentric_bolt_group_demand(req)
    scenario = native.scenarios[0]
    s = solution(55)
    assert native.availability == legacy.DemandAnalysisAvailability.CALCULATED
    assert scenario.equilibrium is not None
    assert scenario.equilibrium.satisfied
    assert s.proof is not None
    assert s.proof.passed
    assert (
        tuple((b.bolt_id, (Fraction(b.x), Fraction(b.y))) for b in req.physical_geometry.bolts)
        == s.coordinates
    )
    assert (
        Fraction(req.force_reference_point.x.magnitude),
        Fraction(req.force_reference_point.y.magnitude),
    ) == s.reference
    assert (
        (
            Fraction(native.projected_force.u.to(Unit.KIP).magnitude),
            Fraction(native.projected_force.v.to(Unit.KIP).magnitude),
        )
        == s.force
        == (Fraction(8), Fraction(0))
    )
    assert Fraction(scenario.external_moment.to(Unit.KIP_IN).magnitude) == s.centroid_moment == -16
    assert scenario.direct_distribution_moment.magnitude == 0
    assert Fraction(native.polar_coordinate_sum.to(Unit.IN2).magnitude) == s.polar_sum
    for old, new in zip(scenario.per_bolt, s.bolts, strict=True):
        assert old.direct_share == Decimal(".25")
        assert (
            Fraction(old.direct_force.u.to(Unit.KIP).magnitude),
            Fraction(old.direct_force.v.to(Unit.KIP).magnitude),
        ) == new.direct
        assert (
            Fraction(old.centered_x.to(Unit.IN).magnitude),
            Fraction(old.centered_y.to(Unit.IN).magnitude),
        ) == new.delta
    # Prove the actual legacy formula retains its native context; do not reimplement it here.
    source = inspect.getsource(legacy._calculate_scenario)
    assert "moment_u = -ratio * centered_y" in source
    assert "moment_v = ratio * centered_x" in source
    independent_proof(s)
    assert s.bolts[0].total[0] == Fraction(e["slice8_exact_rational_lower_row_q_A"])
    assert s.bolts[2].total[0] == Fraction(e["slice8_exact_rational_upper_row_q_A"])
    # Evidence only: native last places are deliberately NOT made numerically identical.
    assert (
        scenario.per_bolt[0].total_force.u.to(Unit.KIP).magnitude
        != s.projected_bolts()[0].total_force.u.magnitude
    )
    assert e["projection_difference_classification"] == "EXPECTED_NATIVE_NUMERIC_PATH_DIFFERENCE"


@pytest.mark.parametrize(
    ("force", "reference"),
    [
        (("10", "0", "0"), ("0", "0", "0")),
        (("10", "0", "0"), ("0", "2", "0")),
        (("3", "4", "0"), ("2", "1", "0")),
        (("-10", "0", "0"), ("0", "2", "0")),
    ],
)
def test_existing_stage25a_equal_share_fixture_overlap(
    force: tuple[str, str, str], reference: tuple[str, str, str]
) -> None:
    with localcontext(Context(prec=80)):
        req = legacy_input(force=force, reference=reference)
        old = legacy.calculate_eccentric_bolt_group_demand(req)
    new = calculate_in_plane_wrench_demand(
        InPlaneWrenchRequest(
            tuple(WrenchBolt(b.bolt_id, b.x, b.y) for b in req.physical_geometry.bolts),
            (reference[0], reference[1]),
            force[0],
            force[1],
            0,
            Unit.IN,
            Unit.KIP,
            Unit.KIP_IN,
        )
    ).solution.in_units(Unit.IN, Unit.KIP)
    scenario = old.scenarios[0]
    assert scenario.equilibrium is not None
    assert scenario.equilibrium.satisfied
    assert new.centroid_moment == Fraction(scenario.external_moment.to(Unit.KIP_IN).magnitude)
    assert new.force == (Fraction(force[0]), Fraction(force[1]))
    independent_proof(new)


def test_stage25a_warning_and_pure_moment_scope_remain_native() -> None:
    moment = legacy.ExactQuantityVector3D(*(Q.of(v, Unit.KIP_IN) for v in (0, 0, 9)))
    for force in (("5", "0", "0"), ("0", "0", "0")):
        old = legacy.calculate_eccentric_bolt_group_demand(
            legacy_input(force=force, connection_moments=moment)
        )
        codes = {w.code.value for w in old.warnings}
        assert "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL" in codes
        if all(v == "0" for v in force):
            assert old.availability.value == "CALCULATION_NOT_SUPPORTED"
            assert "PURE_CONNECTION_MOMENT_NOT_SUPPORTED" in codes
            assert old.scenarios == ()
    assert result(48).status == "CALCULATED"


def test_stage25b_consumes_actual_signed_projected_vector_and_magnitude() -> None:
    base = _handoff_input()
    native = base.demand_result.scenarios[0].per_bolt[0]
    projected = solution(39).projected_bolts()[0]
    # Typed consumer seam only, not a counterfeit Stage 2.5A result/proof envelope.
    demand = replace(
        native,
        total_force=projected.total_force,
        total_force_magnitude=projected.total_force_magnitude,
    )
    passed = handoff._handoff_demand(demand)
    assert passed.force == projected.total_force
    assert passed.magnitude == projected.total_force_magnitude
    bundle = handoff._bundle_with_bolt_demand(base.execution_bundle, demand)
    assert bundle.bolts[0].in_plane_demand == projected.total_force_magnitude
    assert bundle.layers == base.execution_bundle.layers
    assert bundle.checks == base.execution_bundle.checks
    calculated = calculate_multirow_connection(bundle)
    assert calculated.results
    axis = handoff._bearing_selection(base, demand, base.layer_axes[0])
    assert axis.force == projected.total_force
    # The executor consumes an explicit check demand as well as the bolt record.
    # Supply both, as the unchanged Stage 2.5B handoff does at its consumer seam.
    check = next(
        c
        for c in bundle.checks
        if c.bolt_id == native.bolt_id and c.family is MultiRowCheckFamily.BOLT_SHEAR
    )
    actual = calculate_multirow_connection(
        replace(
            bundle,
            checks=tuple(
                replace(c, demand=projected.total_force_magnitude) if c is check else c
                for c in bundle.checks
            ),
        )
    )
    checked = next(c for c in actual.results if c.source_plan_id == check.check_id)
    previous = next(c for c in calculated.results if c.source_plan_id == check.check_id)
    assert checked.demand == projected.total_force_magnitude
    assert checked.design_resistance == previous.design_resistance
    assert checked.utilization != previous.utilization


def test_common_two_plane_method_consumes_distinct_actual_vectors() -> None:
    positive, negative = solution().projected_bolts()[0], solution(39).projected_bolts()[0]
    planes = tuple(
        FlangePlaneDemand(p.total_force.u, p.total_force.v, fp, "test-group", "test-bolt")
        for p, fp in ((positive, result().fingerprint), (negative, result(39).fingerprint))
    )
    args = {
        "bolt_id": "test-bolt",
        "physical_path": ("OUTER", "BEAM_FLANGE", "INNER"),
        "outer_plane": planes[0],
        "inner_plane": planes[1],
        "diameter": Q.of(".5", Unit.IN),
        "thread_condition": "EXCLUDED",
        "source_authority_id": "TEST_ONLY_CONTROLLED_FNV",
    }
    checked = evaluate_asymmetric_two_plane_bolt(**args, nominal_shear_stress=Q.of(68, Unit.KSI))  # type: ignore[arg-type]
    assert checked.outer_plane == planes[0]
    assert checked.inner_plane == planes[1]
    assert not checked.planes_equal
    assert checked.inner_utilization != checked.outer_utilization
    assert checked.per_plane_design_capacity is not None
    assert checked.governing_utilization == checked.inner_utilization
    pending = evaluate_asymmetric_two_plane_bolt(**args, nominal_shear_stress=None)  # type: ignore[arg-type]
    assert pending.status.value == "NOT_EVALUATED"
    assert pending.per_plane_design_capacity is None


def test_historical_identities_and_successor_safe_scope_record() -> None:
    # Source identities, line-ending invariant; no dependence on HEAD or local tag refs.
    hashes = {
        "eccentric_demand": "b9a23cbe5a4635d940bb2b96c40da81a87447a2e810d4e4c90c49f7c81485376",
        "resistance_handoff": "38075566db9f4d14af5f3872a75825dacece6d0a158c0484c283507cc02b7b23",
        "wi_moment_resultants": "028cf26c7614490c07a0f699bc66faed83babb175b6ce635332254a4f70c226b",
        "angle_connector_core": "2b36da06e44f50986d7a3078db40d0af66477baeb289be63c0f110f66bef3bb7",
        "angle_connector_providers": (
            "f0a6fe18d2c178bfb964fa16711d8ca827f859b5f3df5584ca2f8f6a9af3bedf"
        ),
        "frp_angle_connector_provider": (
            "f7eb508c7253fbeece2f202eae0740c3574e5be98d6c859a3d5ae43c3a408771"
        ),
        "wi_moment_splice_resistance": (
            "906137e13bbac48831ba69e92edda14160c334b20bd1e26e12ed8995450199f0"
        ),
        "quantities": "e9c290f8239d1bd8b542d8d6b466adacb36a7ee2edb18daf006c35dfeab9d698",
        "fingerprint": "b5827f740231b8447ce95fb31f2abe06fcf7e3e50c8e56d8bcc330d76ddf32e0",
    }
    for name, digest in hashes.items():
        text = (ROOT / f"backend/src/frp_master_connection/calculation/{name}.py").read_text(
            encoding="utf-8"
        )
        assert hashlib.sha256(text.encode()).hexdigest() == digest
    record = json.loads((ROOT / "HANDOFF_MANIFEST.json").read_text())["calculation_slice_8_rc1_r1"]
    assert not record["physical_stage_4_2_begun"]
    assert set(record["change_counts"].values()) == {0}
    assert record["baseline"] == "d940192ea8eecb7e35f9601c38f3ad841f580916"


@pytest.mark.parametrize(
    ("value", "status"),
    [
        (True, "INVALID_NUMERIC_TYPE"),
        (None, "INVALID_NUMERIC_TYPE"),
        (Fraction(1, 2), "INVALID_NUMERIC_TYPE"),
        ("garbage", "INVALID_DECIMAL_INPUT"),
        ("sNaN", "INVALID_NONFINITE_INPUT"),
        ("Infinity", "INVALID_NONFINITE_INPUT"),
        (1.2, "INVALID_NUMERIC_TYPE_BINARY_FLOAT_PROHIBITED"),
    ],
)
def test_invalid_numbers_fail_closed(value: object, status: str) -> None:
    with pytest.raises(WrenchInputError, match=status):
        calculate_in_plane_wrench_demand(replace(request(), force_a=cast(NumericInput, value)))


@pytest.mark.parametrize(
    ("change", "status"),
    [
        ({"bolts": []}, "INVALID_BOLT_COLLECTION"),
        ({"bolts": (None,)}, "INVALID_BOLT_COORDINATE"),
        ({"bolts": (WrenchBolt("", 0, 0),)}, "INVALID_BOLT_ID"),
        ({"bolts": (WrenchBolt("id", 0, 0), WrenchBolt("id", 1, 1))}, "INVALID_DUPLICATE_BOLT_ID"),
        ({"reference": (0,)}, "INVALID_WRENCH_REFERENCE"),
        ({"reference": [0, 0]}, "INVALID_WRENCH_REFERENCE"),
        ({"length_unit": Unit.KIP}, "INVALID_UNIT_DIMENSION"),
        ({"force_unit": "kip"}, "INVALID_UNIT_DIMENSION"),
        ({"moment_unit": Unit.KIP}, "INVALID_UNIT_DIMENSION"),
    ],
)
def test_invalid_structure_and_units(change: dict[str, Any], status: str) -> None:
    with pytest.raises(WrenchInputError, match=status):
        calculate_in_plane_wrench_demand(replace(request(), **change))


def test_immutable_records_and_internal_proof_guard() -> None:
    with pytest.raises(WrenchInputError, match="INVALID_WRENCH_REQUEST"):
        calculate_in_plane_wrench_demand(cast(InPlaneWrenchRequest, None))
    with pytest.raises(FrozenInstanceError):
        result().status = "other"  # type: ignore[misc]
    assert not ExactRecovery(Fraction(0), Fraction(1)).passed
    with (
        patch.object(ExactWrenchProof, "passed", new_callable=PropertyMock, return_value=False),
        pytest.raises(ArithmeticError, match="no residual"),
    ):
        result()
    with pytest.raises(TypeError, match="fingerprint record"):
        engine._record(object())


def test_non_rectangular_collinear_and_single_bolt_reference_cases() -> None:
    for coords in (((0, 0), (1, 0), (4, 0)), ((0, 0), (1, 2), (7, -3))):
        r = replace(
            request(63), bolts=tuple(WrenchBolt(str(i), a, b) for i, (a, b) in enumerate(coords))
        )
        independent_proof(calculate_in_plane_wrench_demand(r).solution)
    # Single bolt at (0,0), force (7,-3), ref (1,0), free M=3: exact MC=0.
    r = replace(request(22), bolts=(WrenchBolt("single", 0, 0),), reference=(1, 0), moment_c=3)
    s = calculate_in_plane_wrench_demand(r).solution.in_units(Unit.IN, Unit.KIP)
    assert s.centroid_moment == 0
    assert s.reference_moment == 3
    independent_proof(s)


def test_lossless_long_input_and_half_even_projection_ties() -> None:
    long_input = "1." + "1234567890" * 20
    one = replace(request(22), bolts=(WrenchBolt("one", 0, 0),), force_a=long_input)
    s = calculate_in_plane_wrench_demand(one).solution.in_units(Unit.IN, Unit.KIP)
    assert s.bolts[0].total[0] == Fraction(long_input)
    independent_proof(s)
    assert project_rational(Fraction("1." + "0" * 79 + "5")) == Decimal(1)
    assert project_rational(Fraction("1." + "0" * 78 + "15")) == Decimal("1." + "0" * 78 + "2")
    # Force and moment can have different unit prefixes; normalize before mechanics.
    req = request(63)
    mixed = replace(req, moment_c=3000, moment_unit=Unit.LBF_IN)
    assert calculate_in_plane_wrench_demand(mixed) == result(63)
