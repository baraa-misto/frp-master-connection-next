"""Independent R3 geometry/area/force oracles; no adopted resistance claims."""

import math
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_corrections import execute_direct_corrections
from frp_master_connection.calculation.rhm_direct_r3 import (
    Edge,
    R3Geometry,
    dot,
    execute_r3,
    execute_r3_review,
    geometry_digest,
    intersect_edge,
    moment_witness_r3,
    signed_force,
)
from frp_master_connection.calculation.rhm_direct_reference import q
from frp_master_connection.calculation.rhm_reference import PRECISION

D = Decimal


def test_r3_01_05_pitch_projections_foot_axes_and_legacy() -> None:
    r = execute_r3()
    assert r.bolt_centers == (("B1", (D(0), D(1))), ("B2", (D(0), D(-1))))
    assert r.vertical_pitch_in == 2
    assert float(r.transverse_ltv_in) == pytest.approx(1.716129811447289, rel=1e-14)
    assert float(r.longitudinal_stagger_in) == pytest.approx(1.027082504116340, rel=1e-14)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        # Existing 60-digit arithmetic budget, not a mechanics/fit tolerance.
        ulp = D(10) ** (-PRECISION + 2)
        assert abs(r.transverse_ltv_in**2 + r.longitudinal_stagger_in**2 - 4) < ulp
        f = r.projection_foot
        assert abs(dot((f[0], f[1] - 1), r.n_axis)) < ulp
        assert abs(dot((f[0], f[1] + 1), r.p_axis)) < ulp
    assert r.p_axis[0] > 0 > r.p_axis[1]
    assert all(v < 0 for v in r.sketch_v_axis)
    assert r.projection_foot not in [p for _, p in r.bolt_centers]
    old = execute_direct_corrections()
    assert float(old.vertical_bolt_spacing_in) == pytest.approx(2.330826009383650)
    assert float(old.actual_v_perpendicular_spacing_in) == pytest.approx(1.196975307188628)
    assert old.physical_applicability == "NOT_RECONCILED"
    assert r.geometry_status == "OWNER_SPACING_AND_AXES_RECONCILED"


@pytest.mark.parametrize("angle", [1, 15, 30.9, 45, 60, 89])
@pytest.mark.parametrize("pitch", [1.5, 2, 2.75])
def test_r3_07_13_15_independent_paths_areas_and_strength_sums(angle: float, pitch: float) -> None:
    g = R3Geometry(phi=D(str(angle)), vertical_bolt_pitch=q(str(pitch)))
    r = execute_r3(geometry=g)
    s, c = math.sin(math.radians(angle)), math.cos(math.radians(angle))
    expected = {
        ("BRACE", "P"): [0.4375 / c, 0.4375 / c],
        ("BRACE", "V"): [1, 1 + pitch * c],
        ("COLUMN", "P"): [1 / c, 1 / c],
        ("COLUMN", "V"): [3 / s, 3 / s],
    }
    for b in r.blocks:
        for path, length in zip(b.paths, expected[b.member, b.branch], strict=True):
            if path.length_in is not None:
                assert float(path.length_in) == pytest.approx(length, rel=1e-12)
                assert path.end is not None
                assert float(dot(b.edge.normal, path.end)) == pytest.approx(
                    float(b.edge.offset_in), abs=1e-12
                )
        if not b.available:
            continue
        t = 0.5 if b.member == "BRACE" else 0.375
        assert float(b.shear_gross_area_in2) == pytest.approx(
            sum(expected[b.member, b.branch]) * t, rel=1e-12
        )
        assert float(b.connector_gross_area_in2) == pytest.approx(pitch * t)
        assert b.connector_gross_area_in2 is not None
        assert b.connector_removed_area_in2 is not None
        assert b.connector_net_area_in2 == b.connector_gross_area_in2 - b.connector_removed_area_in2
        # Actual finite cuts union endpoint and any other circle intersections.
        assert sum((x.removed_area_in2 for x in b.cuts[:-1]), D(0)) == pytest.approx(
            b.shear_removed_area_in2
        )
        for variant in ("R3_ACTUAL_GROSS_ARITHMETIC", "R3_SAME_SURFACE_NET_ARITHMETIC"):
            row = next(
                x
                for x in r.checks
                if x.method_id == f"DIRECT_{b.member}_GLOBAL" and x.variant == variant
            )
            index = 0 if b.branch == "P" else 1
            av = float(
                b.shear_gross_area_in2
                if variant.endswith("GROSS_ARITHMETIC")
                else b.shear_net_area_in2
            )
            at = float(
                b.connector_gross_area_in2
                if variant.endswith("GROSS_ARITHMETIC")
                else b.connector_net_area_in2
            )
            ft = (7.5 if b.member == "BRACE" and b.branch == "P" else 2.5) * 0.85
            if b.member == "COLUMN" and b.branch == "V":
                ft *= 0.85
            assert float(row.capacities_kip[index]) == pytest.approx(
                av * 1.125 * 0.85 + at * ft, rel=1e-12
            )


def test_r3_06_08_12_independent_anchors_local_lengths_and_unchanged_operands() -> None:
    a = execute_r3()
    g = R3Geometry(
        xb=q(".6"),
        xc=q("1.2"),
        brace_near_v_edge_distance=q(".8"),
        brace_thickness=q(".4"),
        column_thickness=q(".3"),
        column_flange=q("4.5"),
    )
    b = execute_r3(geometry=g)
    assert b.edges[0].offset_in == D("-.6")
    assert b.edges[3].offset_in == D("1.2")
    assert b.edges[4].offset_in == D("-3.3")
    assert "independent SOURCE" in b.placement_contract
    for block in b.blocks:
        for path in block.paths:
            assert path.length_in is not None
            row = next(
                x
                for x in b.checks
                if x.method_id == f"{block.member}_LOCAL_{block.branch}_{path.bolt_id}"
            )
            t = 0.4 if block.member == "BRACE" else 0.3
            assert float(row.capacities_kip[0]) == pytest.approx(
                2 * float(path.length_in) * t * 1.125 * 0.85
            )
    assert a.factor_trace == b.factor_trace
    assert a.input_digest != b.input_digest


@pytest.mark.parametrize(
    "kind", ["parallel", "wrong", "negative", "zero", "outside", "finite", "unbounded"]
)
def test_r3_09_directed_member_and_finite_edge_guards(kind: str) -> None:
    edge = Edge("BRACE", "E", (D(1), D(0)), D(2), ((D(2), D(-1)), (D(2), D(1))), "TEST")
    member = "OTHER" if kind == "wrong" else "BRACE"
    start = (
        (D(3), D(0))
        if kind == "negative"
        else (D(2), D(0))
        if kind == "zero"
        else (D(0), D(3))
        if kind == "outside"
        else (D(0), D(0))
    )
    if kind == "unbounded":
        edge = replace(edge, endpoints=None)
    p = intersect_edge(
        member, "P", "B", start, (D(0), D(1)) if kind == "parallel" else (D(1), D(0)), edge
    )
    expected = {
        "parallel": "PARALLEL_TO_EDGE",
        "wrong": "WRONG_MEMBER",
        "negative": "NONPOSITIVE_DIRECTED_EDGE_DISTANCE",
        "zero": "NONPOSITIVE_DIRECTED_EDGE_DISTANCE",
        "outside": "OUTSIDE_FINITE_EDGE",
        "finite": "",
        "unbounded": "",
    }
    assert p.reason == expected[kind]
    assert (p.length_in is not None) == (kind in ("finite", "unbounded"))


@pytest.mark.parametrize(
    ("normal", "direction"), [((D(0), D(0)), (D(1), D(0))), ((D(1), D(0)), (D(0), D(0)))]
)
def test_r3_09_nonzero_rays(
    normal: tuple[Decimal, Decimal], direction: tuple[Decimal, Decimal]
) -> None:
    with pytest.raises(ValueError, match="Nonzero"):
        intersect_edge(
            "B", "P", "1", (D(0), D(0)), direction, Edge("B", "E", normal, D(1), None, "TEST")
        )


def test_r3_10_11_coherent_same_surface_projection_not_old_effective_area() -> None:
    r = execute_r3()
    for b in r.blocks:
        connector = b.cuts[-1]
        t = D(".5") if b.member == "BRACE" else D(".375")
        assert connector.gross_length_in == 2
        assert connector.removed_length_in == D(".563")
        assert connector.net_area_in2 == D("1.437") * t
        assert all(h.disposition == "HALF_AT_CENTER_ENDPOINT" for h in connector.intersections)
        with localcontext() as ctx:
            ctx.prec = PRECISION
            scale = (r.transverse_ltv_in if b.branch == "P" else r.longitudinal_stagger_in) / 2
            assert abs(b.perpendicular_projected_net_area_in2 - connector.net_area_in2 * scale) < D(
                10
            ) ** (-PRECISION + 2)
        assert "OBLIQUE" in connector.cut.cut_id
        assert b.available
    # All generic full/half/partial/tangent/overlap/member-isolation cases are also
    # exercised on the reused net_cut kernel by test_hyb2_direct_corrections.py.


@pytest.mark.parametrize("moment", ["12", "-12", "0"])
def test_r3_14_equilibrium_new_lever_arm(moment: str) -> None:
    w = moment_witness_r3(
        R3Geometry(), q("30", Unit.LBF), q("-5", Unit.LBF), q(moment, Unit.LBF_IN)
    )
    assert w.actual_lever_arm_in == 2
    assert w.sum_force_lbf == (D(30), D(-5))
    assert w.reconstructed_moment_lbf_in == D(moment)
    assert w.forces_lbf[0][0] == D(15) - D(moment) / 2
    assert "NOT_ADOPTED" in w.applicability


@pytest.mark.parametrize("rotation", ["0", "17", "73"])
def test_r3_16_units_rigid_frames_order_and_signed_basis(rotation: str) -> None:
    base = execute_r3()
    g = R3Geometry(
        frame_rotation_degrees=D(rotation), midpoint=(q("3.7"), q("-4.2")), reverse_bolt_order=True
    )
    changed = execute_r3(geometry=g)
    si = replace(g, vertical_bolt_pitch=q("50.8", Unit.MM), xb=q("11.1125", Unit.MM))
    assert execute_r3(geometry=si).transverse_ltv_in == changed.transverse_ltv_in
    for a, b in zip(base.blocks, changed.blocks, strict=True):
        assert float(a.shear_gross_area_in2) == pytest.approx(
            float(b.shear_gross_area_in2), rel=1e-13
        )
        assert float(a.shear_net_area_in2) == pytest.approx(float(b.shear_net_area_in2), rel=1e-13)
    sketch, cart = signed_force(g, q("91.55", Unit.LBF), q("13.4", Unit.LBF))
    plus, cart2 = signed_force(g, q("91.55", Unit.LBF), q("13.4", Unit.LBF), positive_n_basis=True)
    assert sketch == (D("91.55"), D("13.4"))
    assert plus == (D("91.55"), D("-13.4"))
    assert cart == cart2
    reverse, _ = signed_force(g, q("-2", Unit.LBF), q("-3", Unit.LBF))
    assert reverse == (D(-2), D(-3))


def test_r3_17_recomputed_rotation_fixed_edges_is_geometry_only() -> None:
    r = execute_r3()
    assert not r.rotation_fit
    assert float(r.rotation_centers[0][1][0]) == pytest.approx(-math.cos(math.radians(30.9)))
    assert r.rotation_blocks[0].paths[0].reason == "NONPOSITIVE_DIRECTED_EDGE_DISTANCE"
    assert all(not b.available for b in r.rotation_blocks)
    assert all(b.edge in r.edges for b in r.rotation_blocks)


@pytest.mark.parametrize("change", ["pitch", "phi", "hole", "xb", "section"])
def test_r3_18_input_binding(change: str) -> None:
    g = R3Geometry()
    new = {
        "pitch": replace(g, vertical_bolt_pitch=q("2.1")),
        "phi": replace(g, phi=D(32)),
        "hole": replace(g, hole=q(".6")),
        "xb": replace(g, xb=q(".5")),
        "section": replace(g, brace_leg=q("4.5")),
    }[change]
    assert geometry_digest(g) != geometry_digest(new)
    assert execute_r3(geometry=new).input_digest != execute_r3(geometry=g).input_digest


@pytest.mark.parametrize(
    ("temperature", "ts"),
    [(75, "1"), (90, ".91"), (100, ".85"), (125, ".7"), (135, ".62"), (150, ".5")],
)
def test_r3_21_preserved_factors(temperature: int, ts: str) -> None:
    r = execute_r3(temperature_f=temperature)
    f = dict(r.factor_trace)
    assert f["Ts"] == D(ts)
    assert f["SF"] == 4
    assert f["FtColumnV_extra_Ts"] == D("2.5") * D(ts) ** 2
    assert f["FbBraceLW_Ts_twice"] == D("7.5") * D(ts) ** 2
    assert not r.public_activation
    assert r.actual_coverage_credited == ()


def test_r3_19_20_overload_true_zero_and_invalid_net_keep_distinct() -> None:
    heavy = execute_r3(axial=q("60000", Unit.LBF), shear=q("60000", Unit.LBF))
    assert all(row.numerical_outcome == "FAIL" for row in heavy.checks)
    zero = execute_r3(axial=q("0", Unit.LBF), shear=q("0", Unit.LBF))
    assert all(row.utilization == 0 and row.numerical_outcome == "PASS" for row in zero.checks)
    invalid = execute_r3(geometry=R3Geometry(hole=q("3")))
    assert all(row.numerical_outcome == "NOT_EVALUATED" for row in invalid.checks)
    partial = execute_r3(geometry=R3Geometry(phi=D(89)))
    assert any(row.numerical_outcome == "PASS" for row in partial.checks)
    assert "STRUCTURAL_METHOD_COVERAGE_PENDING" in partial.limitations[0]


@pytest.mark.parametrize("kind", ["pitch", "angle", "rotation", "order", "hole", "section"])
def test_r3_15_invalid_inputs(kind: str) -> None:
    with pytest.raises(ValueError, match=r"(positive|phi|rotation|hole|thickness)"):
        {
            "pitch": lambda: R3Geometry(vertical_bolt_pitch=q("0")),
            "angle": lambda: R3Geometry(phi=D(90)),
            "rotation": lambda: R3Geometry(frame_rotation_degrees=D(90)),
            "order": lambda: R3Geometry(reverse_bolt_order=1),  # type: ignore[arg-type]
            "hole": lambda: R3Geometry(hole=q(".4")),
            "section": lambda: R3Geometry(brace_thickness=q("4")),
        }[kind]()


def test_r3_complete_dependency_ledger_closes_old_spacing_only() -> None:
    b = execute_r3_review()
    assert b.current.stream == "OWNER_CONFIRMED_GEOMETRY_R3"
    assert b.predecessor.physical_applicability == "NOT_RECONCILED"
    assert {"D121", "D239", "L52/L53", "L64/L65", "moment lever arm"} <= {
        x.quantity for x in b.dependency_ledger
    }
    assert not any("which segment" in x.lower() for x in b.current.limitations)
    assert "STRUCTURAL_METHOD_COVERAGE_PENDING" in b.current.limitations[0]
