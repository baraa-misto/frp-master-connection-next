"""Independent C2-M/P1 authority, arithmetic, scope and adversarial plan tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.stainless_plate import (
    GEOMETRY_FAILURE,
    PlateCheckPlan,
    PlateContext,
    PlateGeometry,
    PlateHole,
    PlateRequest,
    PlateResult,
    ResolvedPlateDemand,
    TrustedPlateRecord,
    evaluate_stainless_plate,
    standard_hole,
)
from frp_master_connection.domain.stainless_material import StainlessGrade, stainless_material

ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = (
    ROOT / "backend/tests/golden/FRP_MASTER_CONNECTION_CME_2_C2_P1_GOLDEN_BENCHMARKS_RC1_R1.json"
)
GOLDEN = json.loads(GOLDEN_PATH.read_bytes())
CASES = {item["id"]: item for item in GOLDEN["cases"]}


def q(value: str | int, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def demand(force: str = "20") -> ResolvedPlateDemand:
    return ResolvedPlateDemand(
        "D1",
        "LRFD_1",
        q(force, Unit.KIP),
        (q(0), q(0), q(0)),
        "PLATE_LOCAL_X_Y_Z",
        "+Y",
        "INDEPENDENT_RESOLVED_FIXTURE",
    )


def request(kind: str = "TENSION", thickness: str = "0.375") -> PlateRequest:
    hole = PlateHole("H1", q(2), q(1), q("0.5"), q("0.5625"))
    geometry = PlateGeometry("P1", q(4), q(4), q(thickness), (hole,))
    plan = PlateCheckPlan(
        "SECTION",
        "PURE_TENSION",
        kind,
        demand(),
        ("H1",),
        q(4),
        q(4),
        "DIRECT_ALL_CROSS_SECTION_ELEMENTS",
    )
    if kind == "SHEAR":
        plan = replace(
            plan, family="PURE_SHEAR", demand=demand("10"), gross_length=q(2), net_length=q(2)
        )
    elif kind == "BLOCK":
        plan = replace(
            plan,
            family="BLOCK",
            demand=demand("30"),
            distribution="UNIFORM",
            agv=q("1.5", Unit.IN2),
            anv=q("1.1", Unit.IN2),
            ant=q("0.45", Unit.IN2),
        )
    elif kind == "HOLE":
        plan = replace(
            plan,
            family="H1_BEARING",
            demand=demand("8"),
            l1=q(1),
            l1_basis="EDGE_IN_FORCE_DIRECTION",
        )
    return PlateRequest(geometry, stainless_material("316SS"), (plan,))


def record(r: PlateRequest) -> TrustedPlateRecord:
    # Synthetic internal numerical plans never enter the production source registry.
    return TrustedPlateRecord(
        r,
        "TEST_ONLY_NOT_PRODUCTION_QUALIFICATION",
        "a" * 64,
        "INDEPENDENT_CANONICAL_GEOMETRY",
        "RESOLVED_DEMAND_FIXTURE",
        (q("0.001"), q(2)),
    )


def evaluate(r: PlateRequest) -> PlateResult:
    return evaluate_stainless_plate(r, PlateContext((record(r),)))


def rounded(value: Decimal) -> str:
    # Oracle's repeating values are printed to 12 places; exact ratios tested separately.
    with localcontext() as ctx:
        ctx.prec = 100
        return format(value, ".12f")


def test_golden_integrity_and_counts() -> None:
    assert (
        hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest().upper()
        == "C0A63BB1DD20CC3985671CCEC2406FD928AC0A1541EC91D4F2E8922937D5C492"
    )
    assert (
        len(CASES),
        len(GOLDEN["required_negative_cases"]),
        len(GOLDEN["required_invariants"]),
    ) == (11, 14, 11)


@pytest.mark.parametrize(
    "alias", ["316 Stainless Steel", *GOLDEN["material_policy"]["accepted_aliases"]]
)
@pytest.mark.parametrize("grade", [None, *StainlessGrade])
def test_aliases_and_certification_never_increase_strength(
    alias: str, grade: StainlessGrade | None
) -> None:
    m = stainless_material(alias, grade)
    assert m.commercial_label == "316 Stainless Steel"
    assert m.fy == q(25, Unit.KSI)
    assert m.fu == q(70, Unit.KSI)
    assert not m.mtr_strength_credit
    assert not m.cold_work_credit
    assert m.fy.to(Unit.MPA).magnitude == Decimal(
        GOLDEN["material_policy"]["Fy_display_MPa_exact_from_us_source"]
    )
    assert m.fu.to(Unit.MPA).magnitude == Decimal(
        GOLDEN["material_policy"]["Fu_display_MPa_exact_from_us_source"]
    )
    assert m.product_specification == "ASTM A240/A240M-24"
    assert m.general_requirements == "ASTM A480/A480M-24"
    assert ("FUTURE" in m.future_welding_eligibility) == (
        grade in (StainlessGrade.S31603, StainlessGrade.DUAL)
    )


@pytest.mark.parametrize("alias", ["", "304", "F593", "UNKNOWN"])
def test_unknown_material_fails(alias: str) -> None:
    with pytest.raises(ValueError, match="GRADE_IDENTITY"):
        stainless_material(alias)


@pytest.mark.parametrize("diameter", list(GOLDEN["initial_us_standard_hole_geometry"]["rows"]))
def test_all_standard_rows_and_native_conversion(diameter: str) -> None:
    row = GOLDEN["initial_us_standard_hole_geometry"]["rows"][diameter]
    hole, edge = standard_hole(q(diameter))
    assert hole.magnitude == Decimal(row["standard_hole_diameter_in"])
    assert edge.magnitude == Decimal(row["minimum_edge_distance_in"])
    assert hole.magnitude + Decimal("0.0625") == Decimal(row["net_area_deduction_width_in"])
    fraction = row["minimum_center_spacing_exact_fraction_in"]
    assert Fraction(diameter) * Fraction(8, 3) == Fraction(
        int(fraction["numerator"]), int(fraction["denominator"])
    )
    assert standard_hole(q(diameter).to(Unit.MM)) == (hole, edge)


@pytest.mark.parametrize("diameter", ["0.375", "0.6", "1.125"])
def test_no_table_extrapolation(diameter: str) -> None:
    with pytest.raises(ValueError, match="OUTSIDE_AUTOMATIC"):
        standard_hole(q(diameter))


@pytest.mark.parametrize(
    ("case_id", "kind"),
    [
        ("P1_TENSION_GEOMETRY_DERIVED_ONE_STANDARD_HOLE_U1", "TENSION"),
        ("P1_SHEAR_PURE_SECTION_NO_HOLES", "SHEAR"),
    ],
)
def test_section_goldens(case_id: str, kind: str) -> None:
    result = evaluate(request(kind))
    expected = CASES[case_id]["expected"]
    yielding, rupture = result.checks
    for check, prefix in [(yielding, "yield"), (rupture, "rupture")]:
        assert check.nominal.magnitude == Decimal(expected[prefix + "_nominal_kip"])
        assert check.resistance.magnitude == Decimal(expected[prefix + "_design_kip"])
        assert rounded(check.utilization) == expected[prefix + "_utilization"]
        assert Fraction(*check.rational_utilization) == Fraction(check.demand.magnitude) / Fraction(
            *check.rational_resistance
        )
    assert result.governing == ((yielding.family, yielding.id),)
    assert yielding.method == expected["governing"]
    assert result.numerical_comparison == "ISOLATED_COVERED_CHECKS_PASS"
    assert not result.family_activation
    assert len(result.external_scopes) == 6


@pytest.mark.parametrize("distribution", ["UNIFORM", "NONUNIFORM"])
def test_block_goldens(distribution: str) -> None:
    r = request("BLOCK")
    r = replace(r, checks=(replace(r.checks[0], distribution=distribution),))
    result = evaluate(r)
    e = CASES[f"P1_BLOCK_SHEAR_{distribution}_RESOLVED_PATH"]["expected"]
    rupture, cap = result.checks
    assert rupture.nominal.magnitude == Decimal(e["rupture_branch_nominal_kip"])
    assert cap.nominal.magnitude == Decimal(e["yield_cap_branch_nominal_kip"])
    assert cap.resistance.magnitude == Decimal(e["design_kip"])
    assert rounded(cap.utilization) == e["utilization"]
    assert result.governing == ((cap.family, cap.id),)


@pytest.mark.parametrize(
    ("edge", "force", "case"),
    [
        ("1", "8", "P1_STANDARD_HOLE_BEARING_TEAROUT_EDGE_1_0"),
        ("0.75", "6", "P1_STANDARD_HOLE_TEAROUT_AT_TABLE_MIN_EDGE"),
    ],
)
def test_hole_goldens(edge: str, force: str, case: str) -> None:
    r = request("HOLE")
    r = replace(r, checks=(replace(r.checks[0], l1=q(edge), demand=demand(force)),))
    result = evaluate(r)
    bearing, tearout = result.checks
    e = CASES[case]["expected"]
    assert bearing.resistance.magnitude == Decimal(e["bearing_design_kip"])
    assert tearout.resistance.magnitude == Decimal(e["tearout_design_kip"])
    assert rounded(tearout.utilization) == e["utilization"]
    assert result.governing == ((tearout.family, tearout.id),)
    assert r.geometry.holes[0].diameter == q("0.5625")


@pytest.mark.parametrize(
    ("nominal", "design"), [("0.375", "0.375"), ("0.1875", "0.178125"), ("0.125", "0.11875")]
)
def test_thickness_boundary(nominal: str, design: str) -> None:
    result = evaluate(request(thickness=nominal))
    assert result.design_thickness == q(design)
    if nominal == "0.1875":
        assert result.checks[0].resistance == q("16.03125", Unit.KIP)


@pytest.mark.parametrize(
    ("tolerance", "source", "allowed"),
    [
        ("0.05", "APPROVED", True),
        ("0.01", "APPROVED", True),
        ("0.051", "APPROVED", False),
        ("-0.1", "APPROVED", False),
        ("0.05", None, False),
    ],
)
def test_tolerance_credit_is_trusted_bound_provenance(
    tolerance: str, source: str | None, allowed: bool
) -> None:
    r = replace(request(thickness="0.1875"), nominal_credit_requested=True)
    bound = replace(record(r), tolerance_fraction=Decimal(tolerance), tolerance_source=source)
    result = evaluate_stainless_plate(r, PlateContext((bound,)))
    assert result.design_thickness == q("0.1875" if allowed else "0.178125")
    assert bool(result.method_status) is not allowed


@pytest.mark.parametrize("kind", ["TENSION", "SHEAR", "BLOCK", "HOLE"])
def test_monotonic_demand_and_fail_with_unqualified_response(kind: str) -> None:
    r = request(kind)
    low = evaluate(r)
    high = replace(
        r, checks=(replace(r.checks[0], demand=replace(demand("1000"), material_dependent=True)),)
    )
    actual = evaluate(high)
    assert actual.numerical_comparison == "FAIL"
    assert actual.response_status == ("STAINLESS_MATERIAL_DEPENDENT_RESPONSE_NOT_QUALIFIED",)
    assert all(
        a.utilization > b.utilization for a, b in zip(actual.checks, low.checks, strict=True)
    )


@pytest.mark.parametrize("kind", ["TENSION", "SHEAR", "HOLE"])
def test_thickness_monotonicity(kind: str) -> None:
    low = evaluate(request(kind, "0.25"))
    high = evaluate(request(kind, "0.5"))
    assert all(a.resistance > b.resistance for a, b in zip(high.checks, low.checks, strict=True))


def test_cannot_mint_authority_or_mutate_a_bound_plan() -> None:
    r = request()
    bound = record(r)
    assert (
        evaluate_stainless_plate(r, PlateContext()).material_source_status
        == "STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED"
    )
    mutated = replace(r, checks=(replace(r.checks[0], demand=demand("100")),))
    assert not evaluate_stainless_plate(mutated, PlateContext((bound,))).checks
    assert not evaluate_stainless_plate(r, PlateContext((bound, bound))).checks
    for bad in [
        replace(bound, source_id=""),
        replace(bound, content_sha256="z" * 64),
        replace(bound, content_sha256="a"),
    ]:
        assert not evaluate_stainless_plate(r, PlateContext((bad,))).checks
    assert (
        evaluate_stainless_plate(r, PlateContext((bound,), None)).material_source_status
        == "STAINLESS_SOURCE_AUTHORITY_NOT_LOCKED"
    )
    assert (
        evaluate_stainless_plate(
            r, PlateContext((replace(bound, property_domain=(q(1), q(2))),))
        ).material_source_status
        == "STAINLESS_PROPERTY_DOMAIN_NOT_APPLICABLE"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fy", q(30, Unit.KSI)),
        ("fu", q(75, Unit.KSI)),
        ("cold_work_credit", True),
        ("mtr_strength_credit", True),
        ("source_sha256", "0" * 64),
    ],
)
def test_client_property_overrides_are_not_material_authority(field: str, value: object) -> None:
    r = request()
    r = replace(r, material=replace(r.material, **{field: cast(Any, value)}))
    assert evaluate(r).material_source_status == "STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED"
    assert not evaluate(r).checks


@pytest.mark.parametrize(
    ("field", "value", "status"),
    [
        ("product_form", "ANGLE", "STAINLESS_PRODUCT_FORM_NOT_SUPPORTED"),
        ("product_form", "TEE", "STAINLESS_PRODUCT_FORM_NOT_SUPPORTED"),
        ("fabrication", "WELDED", "STAINLESS_FABRICATION_METHOD_NOT_SUPPORTED"),
        ("welding_required", True, "STAINLESS_WELDING_AUTHORITY_NOT_AVAILABLE"),
    ],
)
def test_excluded_forms(field: str, value: object, status: str) -> None:
    r = replace(request(), **{field: cast(Any, value)})
    result = evaluate(r)
    assert status in result.method_status
    assert not result.checks


@pytest.mark.parametrize(
    ("kind", "field", "value", "status"),
    [
        ("TENSION", "distribution", "UNRESOLVED", "STAINLESS_SHEAR_LAG_METHOD_NOT_AVAILABLE"),
        (
            "TENSION",
            "path_kind",
            "STAGGERED",
            "STAINLESS_STAGGERED_NET_PATH_NOT_SUPPORTED_IN_C2_P1",
        ),
        ("TENSION", "gross_length", None, GEOMETRY_FAILURE),
        ("TENSION", "physical_ids", ("MISSING",), GEOMETRY_FAILURE),
        ("TENSION", "gross_length", q("0.1"), GEOMETRY_FAILURE),
        ("SHEAR", "net_length", None, GEOMETRY_FAILURE),
        ("SHEAR", "net_length", q(5), GEOMETRY_FAILURE),
        ("BLOCK", "distribution", "UNKNOWN", "STAINLESS_BLOCK_PATH_NOT_RESOLVED"),
        ("BLOCK", "agv", None, "STAINLESS_BLOCK_PATH_NOT_RESOLVED"),
        ("BLOCK", "ant", q(0, Unit.IN2), GEOMETRY_FAILURE),
        ("HOLE", "l1", None, GEOMETRY_FAILURE),
        ("HOLE", "l1", q(0), GEOMETRY_FAILURE),
        (
            "HOLE",
            "deformation_considered",
            False,
            "STAINLESS_SERVICE_DEFORMATION_NOT_CONSIDERED_METHOD_NOT_AVAILABLE",
        ),
        ("HOLE", "demand", None, "STAINLESS_PER_HOLE_DEMAND_NOT_RESOLVED"),
        ("TENSION", "demand", None, "STAINLESS_DEMAND_NOT_RESOLVED"),
        ("TENSION", "kind", "FLEXURE", "STAINLESS_METHOD_NOT_SUPPORTED_IN_C2_P1"),
    ],
)
def test_method_fail_closed(kind: str, field: str, value: object, status: str) -> None:
    r = request(kind)
    r = replace(r, checks=(replace(r.checks[0], **{field: cast(Any, value)}),))
    result = evaluate(r)
    assert status in (*result.method_status, *result.demand_status)
    assert not result.checks
    assert result.numerical_comparison == "NOT_EVALUATED"


@pytest.mark.parametrize(
    ("field", "value", "status"),
    [
        ("kind", "OVERSIZED", "STAINLESS_HOLE_TYPE_NOT_SUPPORTED_IN_C2_P1"),
        ("bolt_diameter", q("0.375"), "STAINLESS_BOLT_DIAMETER_OUTSIDE_AUTOMATIC_J3_TABLE_SCOPE"),
        ("diameter", q("0.75"), GEOMETRY_FAILURE),
        ("x", q("0.1"), GEOMETRY_FAILURE),
        ("x", q("0.7"), GEOMETRY_FAILURE),
        ("id", "", GEOMETRY_FAILURE),
    ],
)
def test_hole_detail_fail_closed(field: str, value: object, status: str) -> None:
    r = request()
    g = replace(r.geometry, holes=(replace(r.geometry.holes[0], **{field: cast(Any, value)}),))
    result = evaluate(replace(r, geometry=g))
    assert result.geometry_status == status
    assert not result.checks


def test_geometry_spacing_contact_and_edge_rules() -> None:
    r = request()
    h = r.geometry.holes[0]
    for spacing in ["1", "1.0624"]:
        g = replace(r.geometry, holes=(h, replace(h, id="H2", y=q(str(1 + Decimal(spacing))))))
        assert evaluate(replace(r, geometry=g)).geometry_status == GEOMETRY_FAILURE
    g = replace(r.geometry, holes=(h, replace(h, id="H2", y=q("2.4"))))
    assert evaluate(replace(r, geometry=g)).warnings == ("PREFERRED_3D_SPACING_NOT_PROVIDED",)
    g = replace(g, continuous_contact=True, thinner_contact_thickness=None)
    assert evaluate(replace(r, geometry=g)).geometry_status == GEOMETRY_FAILURE
    g = replace(g, thinner_contact_thickness=q("0.01"))
    assert evaluate(replace(r, geometry=g)).geometry_status == GEOMETRY_FAILURE
    g = replace(g, thinner_contact_thickness=q("0.375"))
    assert evaluate(replace(r, geometry=g)).geometry_status == "VALID"
    g = replace(r.geometry, holes=(replace(h, x=q("0.7")),), reduced_edge_exception=True)
    assert (
        evaluate(replace(r, geometry=g)).geometry_status == "STAINLESS_ENGINEERING_REVIEW_REQUIRED"
    )
    g = replace(
        r.geometry,
        width=q(20),
        length=q(20),
        elements_in_contact=True,
        holes=(replace(h, x=q(10), y=q(10)),),
    )
    assert evaluate(replace(r, geometry=g)).geometry_status == GEOMETRY_FAILURE


def test_fingerprint_complete_identity_and_unit_independence() -> None:
    r = request()
    before = evaluate(r)
    assert before.fingerprint == evaluate(r).fingerprint
    for changed in [
        replace(r, material=stainless_material("316", StainlessGrade.S31600)),
        replace(r, checks=(replace(r.checks[0], demand=demand("21")),)),
        replace(r, geometry=replace(r.geometry, nominal_thickness=q("0.5"))),
    ]:
        assert evaluate(changed).fingerprint != before.fingerprint
    h = r.geometry.holes[0]
    g = replace(
        r.geometry,
        width=r.geometry.width.to(Unit.MM),
        length=r.geometry.length.to(Unit.MM),
        nominal_thickness=r.geometry.nominal_thickness.to(Unit.MM),
        holes=(
            replace(
                h,
                x=h.x.to(Unit.MM),
                y=h.y.to(Unit.MM),
                bolt_diameter=h.bolt_diameter.to(Unit.MM),
                diameter=h.diameter.to(Unit.MM),
            ),
        ),
    )
    assert evaluate(replace(r, geometry=g)).fingerprint == before.fingerprint


def test_force_and_geometry_display_goldens() -> None:
    e = CASES["P1_US_SOURCE_RESISTANCE_SI_DISPLAY"]["expected"]
    assert q("33.75", Unit.KIP).to(Unit.KN).magnitude == Decimal(e["tension_design_resistance_kN"])
    assert q("12.3046875", Unit.KIP).to(Unit.KN).magnitude == Decimal(
        e["bearing_design_resistance_kN"]
    )
    e = CASES["P1_GEOMETRY_US_1_2_SI_DISPLAY_DOES_NOT_REGENERATE_SOURCE"]["expected"]
    for v, k in [
        ("0.5", "bolt_diameter_mm"),
        ("0.5625", "standard_hole_diameter_mm"),
        ("0.625", "net_area_deduction_width_mm"),
        ("0.75", "minimum_edge_distance_mm"),
        ("4.5", "maximum_center_to_edge_mm"),
        ("9", "maximum_longitudinal_spacing_mm"),
    ]:
        assert q(v).to(Unit.MM).magnitude == Decimal(e[k])


def test_invalid_grade_and_geometry_and_plan_identity() -> None:
    with pytest.raises(ValueError, match="GRADE_IDENTITY"):
        stainless_material("316", cast(StainlessGrade, "CLIENT_UNKNOWN"))
    r = request()
    assert (
        evaluate(replace(r, geometry=replace(r.geometry, width=q(0)))).geometry_status
        == GEOMETRY_FAILURE
    )
    assert evaluate(replace(r, checks=())).method_status == ("STAINLESS_CHECK_PLAN_NOT_RESOLVED",)
    assert evaluate(replace(r, checks=r.checks + r.checks)).method_status == (
        "STAINLESS_CHECK_PLAN_NOT_RESOLVED",
    )
    for d in [replace(demand(), id=""), replace(demand(), reference=(q(0, Unit.KIP), q(0), q(0)))]:
        actual = evaluate(replace(r, checks=(replace(r.checks[0], demand=d),)))
        assert actual.demand_status == ("STAINLESS_DEMAND_NOT_RESOLVED",)
    compression = replace(r, checks=(replace(r.checks[0], demand=demand("-1")),))
    assert evaluate(compression).method_status == ("STAINLESS_COMPRESSION_NOT_SUPPORTED_IN_C2_P1",)


def test_non_longitudinal_pair_and_qualified_material_response() -> None:
    r = request()
    h = r.geometry.holes[0]
    g = replace(
        r.geometry, width=q(6), continuous_contact=True, holes=(h, replace(h, id="H2", x=q(4)))
    )
    assert evaluate(replace(r, geometry=g)).geometry_status == "VALID"
    p = replace(
        r.checks[0], demand=replace(demand(), material_dependent=True, response_qualified=True)
    )
    assert evaluate(replace(r, checks=(p,))).response_status == ()


def test_complete_plan_retains_failure_and_unavailable_check() -> None:
    r = request()
    failing = replace(r.checks[0], demand=demand("100"))
    missing = replace(failing, id="MISSING", kind="HOLE", demand=None)
    actual = evaluate(replace(r, checks=(failing, missing)))
    assert actual.numerical_comparison == "FAIL"
    assert actual.demand_status == ("STAINLESS_PER_HOLE_DEMAND_NOT_RESOLVED",)
    assert len(actual.checks) == 2
    partial = evaluate(replace(r, checks=(r.checks[0], missing)))
    assert partial.numerical_comparison == "NOT_EVALUATED"


def test_multiple_block_candidates_keep_deterministic_unrounded_governing() -> None:
    r = request("BLOCK")
    weaker = replace(r.checks[0], id="NONUNIFORM", distribution="NONUNIFORM")
    actual = evaluate(replace(r, checks=(*r.checks, weaker)))
    assert len(actual.checks) == 4
    assert actual.governing == (("BLOCK", "NONUNIFORM:SHEAR_YIELD_CAP"),)
    assert actual.governing == evaluate(replace(r, checks=(weaker, *r.checks))).governing


def test_hole_l1_and_net_deduction_monotonicity() -> None:
    r = request("HOLE")
    first = evaluate(r)
    closer = replace(
        r.checks[0], l1=q("0.75"), l1_basis="HALF_ADJACENT_CENTER_SPACING_IN_FORCE_DIRECTION"
    )
    assert evaluate(replace(r, checks=(closer,))).checks[1].resistance < first.checks[1].resistance
    r = request()
    wider = replace(r.geometry.holes[0], bolt_diameter=q("0.75"), diameter=q("0.8125"))
    assert (
        evaluate(replace(r, geometry=replace(r.geometry, holes=(wider,)))).checks[1].resistance
        < evaluate(r).checks[1].resistance
    )


def test_arithmetic_and_fingerprint_independent_of_ambient_decimal_context() -> None:
    r = request("HOLE")
    expected = evaluate(r)
    from decimal import ROUND_DOWN

    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        assert evaluate(r) == expected


def test_result_retains_complete_trusted_demand_path_and_thickness_provenance() -> None:
    r = request("HOLE")
    actual = evaluate(r)
    assert actual.resolved_input == r
    assert actual.resolved_authority == record(r)
    assert actual.resolved_input.checks[0].demand == demand("8")
    assert actual.resolved_input.checks[0].l1_basis == "EDGE_IN_FORCE_DIRECTION"
    assert actual.resolved_input.geometry.holes[0].diameter == q("0.5625")
    absent = evaluate_stainless_plate(r, PlateContext())
    assert absent.resolved_authority is None
    assert absent.checks == ()


@pytest.mark.parametrize(
    ("folder", "filename", "expected"),
    [
        (
            "docs/engineering",
            "FRP_MASTER_CONNECTION_CME_2_C2_SOURCE_RECONCILIATION_RC1.md",
            "DB5EFC55F469A0A02C491552142845E9BEA1CC22CA97B6BB8BD08CD9DAB65296",
        ),
        (
            "docs/engineering",
            "FRP_MASTER_CONNECTION_CME_2_C2_M_ENGINEERING_SPECIFICATION_RC1.md",
            "D7364C080B983CA7830177DE278DD30826D17770D196A72664BDD02C02DCB0A0",
        ),
        (
            "docs/engineering",
            "FRP_MASTER_CONNECTION_CME_2_C2_P1_ENGINEERING_SPECIFICATION_RC1_R1.md",
            "1A40C852DA4AB2A7E9BE434E65CA519B5074B8D5C7433FD1BCF6DC3BE6ACB165",
        ),
        (
            "docs/qa",
            "FRP_MASTER_CONNECTION_CME_2_C2_P1_RC1_R1_INDEPENDENT_VALIDATION.md",
            "DED957C3D1CE665588BE4E8F32F85AD85C886B58D754E14FDD4F95090474A328",
        ),
        (
            "docs/governance",
            "FRP_MASTER_CONNECTION_CME_2_C2_OWNER_APPROVAL_RECORD_2026-09-12.md",
            "5BAD9131E6052DA30FC1BF9729F3D4FADC88E2FCCAC570770D5C63CA8D5DF5C1",
        ),
    ],
)
def test_controlled_artifact_bytes_are_exact(folder: str, filename: str, expected: str) -> None:
    raw = (ROOT / folder / filename).read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == expected
    assert hashlib.sha256(raw + b"tamper").hexdigest().upper() != expected


def test_continuous_contact_limit_applies_to_adjacent_longitudinal_centers() -> None:
    r = request()
    holes = tuple(
        replace(r.geometry.holes[0], id=f"H{i}", y=q(y)) for i, y in enumerate((1, 4, 7, 10))
    )
    geometry = replace(
        r.geometry,
        length=q(11),
        holes=holes,
        continuous_contact=True,
        thinner_contact_thickness=q("0.25"),
    )
    r = replace(r, geometry=geometry, checks=(replace(r.checks[0], physical_ids=("H0",)),))
    assert evaluate(r).geometry_status == "VALID"
    # The full span exceeds 6 in, but every consecutive spacing is 3 in.
    assert holes[-1].y.to(Unit.IN).magnitude - holes[0].y.to(Unit.IN).magnitude == 9
    too_far = replace(geometry, holes=(holes[0], holes[-1]))
    assert evaluate(replace(r, geometry=too_far)).geometry_status == GEOMETRY_FAILURE
