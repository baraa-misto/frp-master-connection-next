"""Independent R2 trigonometry/area oracles; no historical golden is rewritten."""

from dataclasses import fields, replace
from decimal import Decimal, localcontext
from math import cos, radians, sin

import pytest

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_corrections import (
    ENDPOINT_QUESTION,
    PhysicalCut,
    PhysicalHole,
    execute_direct_corrections,
    net_cut,
    physical_blocks,
)
from frp_master_connection.calculation.rhm_direct_reference import (
    DirectCandidateStream,
    DirectGeometry,
    execute_direct_source,
    q,
    sincos,
)
from frp_master_connection.calculation.rhm_reference import PRECISION

D = Decimal


def point(x: str, y: str) -> tuple[Decimal, Decimal]:
    return D(x), D(y)


def cut(start: tuple[Decimal, Decimal], end: tuple[Decimal, Decimal]) -> PhysicalCut:
    return PhysicalCut("BRACE", "SURFACE", start, end, q(".5"))


def hole(x: str, y: str, diameter: str = "2", label: str = "H1") -> PhysicalHole:
    return PhysicalHole("BRACE", label, point(x, y), q(diameter))


def test_exact_saved_ltv_and_all_source_dependencies_are_distinct() -> None:
    result = execute_direct_corrections()
    assert float(result.historical_ltv_in) == pytest.approx(1.0270825041163402, rel=1e-15)
    assert float(result.corrected_ltv_in) == pytest.approx(1.716129811447289, rel=1e-15)
    assert float(result.actual_v_perpendicular_spacing_in) == pytest.approx(
        1.1969753071886276, rel=1e-15
    )
    assert result.corrected_ltv_in != result.actual_v_perpendicular_spacing_in
    old, new = dict(result.historical.source_summary), dict(result.corrected.source_summary)
    assert float(old["D121"]) == pytest.approx(0.018108108446212381, rel=1e-14)
    assert float(old["D239"]) == pytest.approx(0.040397678801026446, rel=1e-14)
    assert float(new["D121"]) == pytest.approx(0.016384394079623774, rel=1e-14)
    assert float(new["D239"]) == pytest.approx(0.039229559073420016, rel=1e-14)
    assert {k for k in old if old[k] != new[k]} == {"D121", "D239"}
    before, after = dict(result.historical.paths.lengths), dict(result.corrected.paths.lengths)
    assert {k for k in before if before[k] != after[k]} == {"L64", "L65"}
    assert result.historical.paths.bolt_centers == result.corrected.paths.bolt_centers
    assert result.historical.paths.vertical_spacing == result.corrected.paths.vertical_spacing
    assert result.corrected.stream is DirectCandidateStream.CORRECTED_SOURCE_CANDIDATE
    assert result.corrected.coverage == "NOT_ESTABLISHED"
    assert not result.corrected.public_activation
    assert result.physical_applicability == "NOT_RECONCILED"
    assert result.endpoint_question == ENDPOINT_QUESTION
    assert result.actual_coverage_credited == ()
    assert not result.public_activation
    assert result.qualification == "SECTION_2_3_2_UNRESOLVED"
    assert result.additional_hole_allowance_in == 0
    assert "NOT_ORIGINAL_XLSX" in result.actual_hole_input_provenance


@pytest.mark.parametrize("member", ["BRACE", "COLUMN"])
@pytest.mark.parametrize(
    "variant", ["HISTORICAL_GROSS", "LTV_ONLY", "HOLES_ONLY_CONDITIONAL", "COMBINED_CONDITIONAL"]
)
def test_independent_full_area_stress_capacity_and_utilization_oracle(
    member: str, variant: str
) -> None:
    record = next(
        r
        for r in execute_direct_corrections().variants
        if r.member == member and r.variant == variant
    )
    phi = radians(30.9)
    thickness = 0.5 if member == "BRACE" else 0.375
    ltv = 2 * (cos(phi) if variant in ("LTV_ONLY", "COMBINED_CONDITIONAL") else sin(phi))
    deduction = 0.563 * thickness if "CONDITIONAL" in variant else 0
    expected_ratios = []
    for row in record.branches:
        lv = (
            (1 if member == "BRACE" else 1 / sin(phi))
            if row.branch == "V"
            else (0.4375 if member == "BRACE" else 1) / cos(phi)
        )
        lt = ltv if row.branch == "V" else 2 / cos(phi)
        av, at = 2 * lv * thickness, lt * thickness
        ans, ant = av - deduction, at - deduction
        nominal_s, nominal_t = 4.5, 30 if member == "BRACE" and row.branch == "P" else 10
        afs, aft = nominal_s / 4 * 0.85, nominal_t / 4 * 0.85
        if member == "COLUMN" and row.branch == "V":
            aft *= 0.85
        capacity = ans * afs + ant * aft
        demand = 0.0134 if row.branch == "V" else 0.09155
        expected = demand / capacity
        expected_ratios.append(expected)
        assert float(row.source_shear_area_in2) == pytest.approx(av, rel=1e-14)
        assert float(row.source_tension_area_in2) == pytest.approx(at, rel=1e-14)
        assert float(row.conditional_net_shear_area_in2) == pytest.approx(ans, rel=1e-14)
        assert float(row.conditional_net_tension_area_in2) == pytest.approx(ant, rel=1e-14)
        assert row.allowable_capacity_kip is not None
        assert row.ratio is not None
        assert row.listed_stress_area_sum_kip is not None
        assert float(row.listed_stress_area_sum_kip) == pytest.approx(
            ans * nominal_s + ant * nominal_t, rel=1e-14
        )
        assert float(row.allowable_capacity_kip) == pytest.approx(capacity, rel=1e-14)
        assert float(row.ratio) == pytest.approx(expected, rel=1e-14)
        traced_capacity = dict(row.cell_trace)[row.source_cells[-2]]
        assert traced_capacity is not None
        assert float(traced_capacity) == pytest.approx(capacity, rel=1e-14)
        assert row.available
        assert row.reason == ""
        assert "REFERENCE_ONLY" in row.applicability
    assert record.utilization is not None
    assert float(record.utilization) == pytest.approx(sum(expected_ratios), rel=1e-14)


@pytest.mark.parametrize("phi", ["5", "25", "45", "60", "80", ".00000001", "89.99999999"])
def test_acute_angle_and_near_singular_projection_and_no_adoption(phi: str) -> None:
    g = DirectGeometry(phi=D(phi))
    result = execute_direct_corrections(geometry=g)
    angle = radians(float(phi))
    assert float(result.corrected_ltv_in) == pytest.approx(2 * cos(angle), abs=1e-14)
    assert result.corrected_ltv_in > 0
    assert result.historical_ltv_in > 0
    with localcontext() as context:
        context.prec = 60
        s, c = sincos(g.phi)
        assert abs(
            result.actual_v_perpendicular_spacing_in - result.vertical_bolt_spacing_in * s
        ) < D("1e-57")
        a, b = result.d_segment_projection_endpoints
        delta = b[0] - a[0], b[1] - a[1]
        # Endpoint subtraction loses digits near the singular angle. Bound
        # arithmetic error by coordinate ULPs at the governed precision;
        # this is not a physical/engineering acceptance tolerance.
        scale = max(abs(x) for p in (a, b) for x in p)
        arithmetic_bound = D(10) ** (max(0, scale.adjusted()) - PRECISION + 2)
        assert abs(delta[0] * s + delta[1] * c - 2) < arithmetic_bound
        assert abs(delta[0] * c - delta[1] * s) < arithmetic_bound
    assert not result.public_activation
    assert not result.actual_coverage_credited


@pytest.mark.parametrize("phi", ["0", "90", "-1", "NaN", "Infinity"])
def test_invalid_angle_contract_is_not_weakened(phi: str) -> None:
    with pytest.raises(
        ValueError, match=r"finite|phi|positive|nonempty|named|unique|Source|temperature"
    ):
        execute_direct_corrections(geometry=DirectGeometry(phi=D(phi)))


def test_xb_is_entered_edge_datum_and_local_shear_is_not_net_ligament() -> None:
    g = DirectGeometry(xb=q(".8"), brace_thickness=q(".6"), column_thickness=q(".4"))
    a = execute_direct_corrections(geometry=g)
    b = execute_direct_corrections(geometry=replace(g, hole=q(".65")))
    assert a.corrected.comparisons[2] == b.corrected.comparisons[2]
    assert a.corrected.comparisons[5] == b.corrected.comparisons[5]
    assert (
        a.corrected.comparisons[2].capacities
        == execute_direct_source(geometry=g).comparisons[2].capacities
    )
    p = next(x for x in a.physical_blocks if x.member == "BRACE" and x.branch == "P")
    assert all(c.cut.end[0] == D("-.8") for c in p.cuts[:2])
    assert float(p.cuts[0].gross_length_in) == pytest.approx(0.8 / cos(radians(30.9)), rel=1e-14)
    assert p.cuts[0].gross_length_in > p.cuts[0].removed_length_in
    assert any("edge-to-bolt-centerline" in x for x in a.corrected.factor_ledger)


def test_same_actual_holes_unequal_brace_v_lengths_and_distinct_area_meanings() -> None:
    result = execute_direct_corrections()
    assert len(result.physical_blocks) == 4
    for block in result.physical_blocks:
        assert len(block.cuts) == 3
        for surface in block.cuts:
            assert {h.hole_id for h in surface.intersections} == {"B1", "B2"}
            assert surface.net_area_in2 > 0
        expected = 0.2815 if block.member == "BRACE" else 0.211125
        assert float(block.removed_shear_area_in2) == pytest.approx(expected, rel=1e-14)
        assert float(block.removed_tension_area_in2) == pytest.approx(expected, rel=1e-14)
    bv = next(x for x in result.physical_blocks if x.member == "BRACE" and x.branch == "V")
    assert float(bv.cuts[0].gross_length_in) == pytest.approx(1)
    assert float(bv.cuts[1].gross_length_in) == pytest.approx(3)
    source = next(
        x for x in result.variants if x.member == "BRACE" and x.variant == "LTV_ONLY"
    ).branches[0]
    assert source.source_shear_area_in2 == 1
    assert float(bv.actual_shear_gross_area_in2) == pytest.approx(2)
    assert source.source_tension_area_in2 != bv.actual_tension_gross_area_in2
    assert "CONDITIONAL" in result.net_sensitivity_scope


@pytest.mark.parametrize(("start", "end"), [(("-2", "0"), ("2", "0")), (("2", "0"), ("-2", "0"))])
def test_full_centerline_hole_and_reversed_endpoint_geometry(
    start: tuple[str, str], end: tuple[str, str]
) -> None:
    result = net_cut(cut(point(*start), point(*end)), (hole("0", "0"),))
    assert result.gross_length_in == 4
    assert result.removed_length_in == 2
    assert result.net_area_in2 == 1
    assert result.available
    assert result.intersections[0].disposition == "FULL_CENTERLINE_DIAMETER"


@pytest.mark.parametrize("center", ["0", "4"])
def test_half_hole_is_from_actual_center_terminated_surface(center: str) -> None:
    result = net_cut(cut(point("0", "0"), point("4", "0")), (hole(center, "0"),))
    assert result.removed_length_in == 1
    assert result.intersections[0].diameter_fraction == D(".5")
    assert result.intersections[0].disposition == "HALF_AT_CENTER_ENDPOINT"


@pytest.mark.parametrize(
    ("offset", "intersects"), [("0.99999999", True), ("1", False), ("1.00000001", False)]
)
def test_exact_tangency_and_both_sides_without_engineering_tolerance(
    offset: str, intersects: bool
) -> None:
    result = net_cut(cut(point("-2", offset), point("2", offset)), (hole("0", "0"),))
    assert (result.removed_length_in > 0) is intersects


def test_partial_chord_missing_far_hole_and_nonpositive_surface_are_explicit() -> None:
    result = net_cut(
        cut(point("-2", ".6"), point("2", ".6")), (hole("0", "0"), hole("9", "0", label="FAR"))
    )
    assert result.removed_length_in == D("1.6")
    assert result.intersections[0].disposition == "PARTIAL_CHORD"
    assert result.intersections[1].disposition == "OUTSIDE_SEGMENT"
    covered = net_cut(cut(point("0", "0"), point(".1", "0")), (hole("0", "0"),))
    assert covered.net_area_in2 == 0
    assert not covered.available


def test_hole_intervals_are_unioned_once_and_member_labels_do_not_double_count() -> None:
    surface = cut(point("-2", "0"), point("3", "0"))
    holes = (hole("0", "0"), hole("1", "0", label="H2"))
    result = net_cut(surface, holes)
    assert result.removed_length_in == 3
    assert result.net_area_in2 == 1
    foreign = replace(holes[0], member="COLUMN")
    assert net_cut(surface, (*holes, foreign)) == result
    assert net_cut(surface, tuple(reversed(holes))).net_area_in2 == result.net_area_in2
    renamed = tuple(
        replace(h, hole_id="RENAMED" + str(i), member="RENAMED_MEMBER") for i, h in enumerate(holes)
    )
    assert (
        net_cut(replace(surface, member="RENAMED_MEMBER"), renamed).net_area_in2
        == result.net_area_in2
    )


@pytest.mark.parametrize(
    "bad", ["member", "cut_id", "end", "nonfinite", "hole_id", "duplicate", "diameter"]
)
def test_invalid_actual_surface_or_inventory_is_not_silently_accepted(bad: str) -> None:
    surface = cut(point("-2", "0"), point("3", "0"))
    holes: tuple[PhysicalHole, ...] = (hole("0", "0"),)
    if bad in ("member", "cut_id"):
        surface = replace(surface, member="") if bad == "member" else replace(surface, cut_id="")
    elif bad == "end":
        surface = replace(surface, end=surface.start)
    elif bad == "nonfinite":
        surface = replace(surface, start=point("NaN", "0"))
    elif bad == "hole_id":
        holes = (replace(holes[0], hole_id=""),)
    elif bad == "duplicate":
        holes = (*holes, holes[0])
    else:
        holes = (replace(holes[0], diameter=q("0")),)
    with pytest.raises(ValueError, match=r"finite|positive|nonempty|named|unique"):
        net_cut(surface, holes)


def test_extra_hole_intersection_on_other_source_shear_ray_is_not_assumed_half_only() -> None:
    blocks = physical_blocks(DirectGeometry(phi=D("5")))
    brace = next(x for x in blocks if x.member == "BRACE" and x.branch == "V")
    assert brace.cuts[1].removed_length_in > D(".563") / 2
    assert any(i.disposition == "PARTIAL_CHORD" for i in brace.cuts[1].intersections)


def test_invalid_residual_withholds_only_affected_reference_comparison() -> None:
    result = execute_direct_corrections(geometry=DirectGeometry(phi=D("5")))
    for member in ("BRACE", "COLUMN"):
        holes = next(
            x
            for x in result.variants
            if x.member == member and x.variant == "HOLES_ONLY_CONDITIONAL"
        )
        assert holes.utilization is None
        assert holes.numerical_outcome == "NOT_EVALUATED"
        assert holes.branches[0].conditional_net_tension_area_in2 < 0
        assert holes.branches[0].ratio is None
        assert holes.branches[0].allowable_capacity_kip is None
        assert "Nonpositive" in holes.branches[0].reason
        assert holes.branches[1].available
        assert (
            next(
                x for x in result.variants if x.member == member and x.variant == "LTV_ONLY"
            ).utilization
            is not None
        )
    assert len(result.corrected.comparisons) == 7


def test_nonpositive_shear_residual_and_hole_overlap_do_not_become_pass() -> None:
    # Explicitly huge input holes at a near-zero source path fail physical fit.
    with pytest.raises(ValueError, match=r"contained"):
        physical_blocks(DirectGeometry(d_span=q(".1")))
    with pytest.raises(ValueError, match=r"outside"):
        execute_direct_corrections(geometry=DirectGeometry(xb=q(".1")))


@pytest.mark.parametrize("temperature", [75, 90, 100, 125, 135, 150])
def test_temperature_variations_keep_original_double_ts_column_v(temperature: int) -> None:
    result = execute_direct_corrections(temperature_f=temperature)
    ts = {75: 1, 90: 0.91, 100: 0.85, 125: 0.7, 135: 0.62, 150: 0.5}[temperature]
    cv = next(
        x for x in result.variants if x.member == "COLUMN" and x.variant == "LTV_ONLY"
    ).branches[0]
    assert float(cv.allowable_tension_stress_ksi) == pytest.approx(2.5 * ts * ts, rel=1e-14)
    assert float(dict(cv.cell_trace)["D220"]) == pytest.approx(2500 * ts, rel=1e-14)  # type: ignore[arg-type]
    assert dict(cv.cell_trace)["D221"] is not None


def test_us_si_same_geometry_actions_and_hole_areas() -> None:
    g = DirectGeometry()
    values = {f.name: getattr(g, f.name).to(Unit.MM) for f in fields(g) if f.name != "phi"}
    si = replace(g, **values)
    a = execute_direct_corrections()
    b = execute_direct_corrections(
        geometry=si, axial=q("91.55", Unit.LBF).to(Unit.N), shear=q("13.4", Unit.LBF).to(Unit.N)
    )
    assert a.corrected.source_summary == b.corrected.source_summary
    assert a.corrected_ltv_in == b.corrected_ltv_in
    assert a.variants == b.variants
    assert a.physical_blocks == b.physical_blocks


@pytest.mark.parametrize("load", ["0", "60000"])
def test_zero_and_failure_are_calculated_without_qualification_promotion(load: str) -> None:
    result = execute_direct_corrections(axial=q(load, Unit.LBF), shear=q("0", Unit.LBF))
    expected = "PASS" if load == "0" else "FAIL"
    assert all(x.numerical_outcome == expected for x in result.variants)
    assert result.corrected.bolt_status == expected
    assert result.historical.original_literal_e46 == "OK"
    assert not result.actual_coverage_credited
    assert result.qualification == "SECTION_2_3_2_UNRESOLVED"


def test_source_negative_actions_and_non_table_temperature_stay_invalid() -> None:
    with pytest.raises(ValueError, match=r"positive|negative|nonnegative"):
        execute_direct_corrections(axial=q("-1", Unit.LBF))
    with pytest.raises(ValueError, match=r"temperature|table|supplied"):
        execute_direct_corrections(temperature_f=101)
    with pytest.raises(TypeError, match=r"stream|Stream"):
        execute_direct_source(stream=DirectCandidateStream.CORRECTED_SOURCE_CANDIDATE)  # type: ignore[arg-type]
