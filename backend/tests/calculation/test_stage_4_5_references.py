"""F45-01..24 independent mathematics, not native serialized result replacements."""

from fractions import Fraction as R
from typing import Any

import pytest

from tests.application.test_column_moment_base_preview import MATRIX
from tests.calculation.test_angle_column_base_references import add, cross, rotate, subtract, vector

FIXTURES = {v["id"]: v for v in MATRIX["reference_fixtures"]}


def ledger(records: list[dict[str, Any]]) -> dict[str, tuple[R, ...]]:
    force, moment = vector([0, 0, 0]), vector([0, 0, 0])
    for record in records:
        f = vector(record["force_kip"])
        force = add(force, f)
        moment = add(
            moment, add(vector(record["free_moment_kip_in"]), cross(vector(record["point_in"]), f))
        )
    return {"force_O_kip": force, "moment_O_kip_in": moment}


def expected_ledger(value: dict[str, Any]) -> dict[str, tuple[R, ...]]:
    return {k: vector(v) for k, v in value.items()}


@pytest.mark.parametrize("identifier", [f"F45-{i:02}" for i in range(1, 25)])
def test_independent_reference(identifier: str) -> None:
    case = FIXTURES[identifier]
    i, e = case["input"], case["expected"]
    if case["method"] == "SECTION_PROPERTIES":
        b, d = R(i["B_in"]), R(i["D_in"])
        kind = i["kind"]
        if kind == "SRS":
            area, ix, iy = b * d, b * d**3 / 12, d * b**3 / 12
        elif kind == "RHS":
            t = R(i["t_or_tf_in"])
            bi, di = b - 2 * t, d - 2 * t
            area, ix, iy = (
                b * d - bi * di,
                (b * d**3 - bi * di**3) / 12,
                (d * b**3 - di * bi**3) / 12,
            )
        else:
            t, w = R(i["t_or_tf_in"]), R(i["tw_in"])
            area = 2 * b * t + (d - 2 * t) * w
            ix = 2 * (b * t**3 / 12 + b * t * ((d - t) / 2) ** 2) + w * (d - 2 * t) ** 3 / 12
            iy = 2 * t * b**3 / 12 + (d - 2 * t) * w**3 / 12
        assert (area, ix, iy) == tuple(R(e[k]) for k in ("area_in2", "Ixx_in4", "Iyy_in4"))
        assert vector(e["centroid_xy_in"]) == (R(0), R(0))
        assert R(e["Ixy_in4"]) == 0
    elif identifier == "F45-06":
        for name, m in i["matrices_rows"].items():
            assert sum(R(m[0][k]) * cross(vector(m[1]), vector(m[2]))[k] for k in range(3)) == R(
                e[name]["determinant"]
            )
            assert all(
                sum(R(m[k][a]) * R(m[k][b]) for k in range(3)) == int(a == b)
                for a in range(3)
                for b in range(3)
            )
            assert rotate(m, vector(i["local_force_kip"])) == vector(e[name]["global_force_kip"])
            assert rotate(m, vector(i["local_moment_kip_in"])) == vector(
                e[name]["global_moment_kip_in"]
            )
    elif case["method"] == "WRENCH_SHIFT":
        f = vector(i["force_kip"])
        m = add(
            vector(i["moment_R_kip_in"]),
            cross(subtract(vector(i["r_R_in"]), vector(i["r_O_in"])), f),
        )
        assert f == vector(e["force_O_kip"])
        assert m == vector(e["moment_O_kip_in"])
        assert tuple(-v for v in f) == vector(e["opposite_reaction_force_kip"])
        assert tuple(-v for v in m) == vector(e["opposite_reaction_moment_kip_in"])
    elif identifier == "F45-10":
        q = i["Q_rows"]
        r, f, m = (rotate(q, vector(i[k])) for k in ("r_R_in", "force_kip", "moment_R_kip_in"))
        assert r == vector(e["rotated_reference_in"])
        assert f == vector(e["rotated_force_kip"])
        assert m == vector(e["rotated_moment_R_kip_in"])
        assert add(m, cross(r, f)) == vector(e["rotated_moment_O_kip_in"])
    elif identifier == "F45-11":
        r, h, s, f, m = (
            vector(i[k])
            for k in (
                "member_reference_in",
                "heel_reference_in",
                "foot_reference_in",
                "member_force_kip",
                "member_moment_kip_in",
            )
        )
        mh = add(m, cross(subtract(r, h), f))
        ms = add(m, cross(subtract(r, s), f))
        assert f == vector(e["heel_force_kip"]) == vector(e["connector_on_foot_force_kip"])
        assert mh == vector(e["heel_moment_kip_in"])
        assert ms == vector(e["connector_on_foot_moment_kip_in"])
        assert subtract(mh, add(ms, cross(subtract(s, h), f))) == vector(
            e["heel_moment_closure_kip_in"]
        )
        assert subtract(f, f) == vector(e["heel_force_closure_kip"])
    elif case["method"] == "LEDGER_SUM":
        assert ledger(i["records"]) == expected_ledger(e)
    elif identifier == "F45-14":
        assert (
            ledger(i["allocation_A"])
            == ledger(i["allocation_B"])
            == expected_ledger(e["shared_total"])
        )
        assert (i["allocation_A"] != i["allocation_B"]) is e["allocations_are_different"]
        assert e["equilibrium_alone_qualifies_either"] is False
    elif identifier == "F45-15":
        assert ledger(i["net_foot_records"]) == expected_ledger(e["net_feet"])
        assert ledger([i["direct_contact"]]) == expected_ledger(e["direct_contact"])
        assert ledger([*i["net_foot_records"], i["direct_contact"]]) == expected_ledger(e["total"])
    elif identifier == "F45-16":
        assert ledger(i["internal_records"]) == expected_ledger(e["net_foot_wrench"])
        assert e["add_net_plus_breakdown_again"] is False
    elif identifier == "F45-17":
        x0, x1 = vector(i["patch_x_interval_in"])
        y0, y1 = vector(i["patch_y_interval_in"])
        area = (x1 - x0) * (y1 - y0)
        p = ((x0 + x1) / 2, (y0 + y1) / 2, R(0))
        f = tuple(area * R(i["pressure_kip_in2"]) * R(v) for v in i["action_on_foundation_normal"])
        assert area == R(e["patch_area_in2"])
        assert p == vector(e["patch_centroid_in"])
        assert f == vector(e["contact_force_kip"])
        assert cross(p, f) == vector(e["contact_moment_at_O_kip_in"])
        assert (R(i["RHS_B_in"]) / 2 - R(i["wall_t_in"]) <= x0 < x1 <= R(i["RHS_B_in"]) / 2) is e[
            "patch_on_real_material"
        ]
    elif identifier == "F45-18":
        x, y = vector(i["void_patch_x_interval_in"]), vector(i["void_patch_y_interval_in"])
        within_void = all(abs(v) < R(i["RHS_B_in"]) / 2 - R(i["wall_t_in"]) for v in (*x, *y))
        assert (not within_void) is e["void_patch_on_real_material"]
        assert (R(i["negative_pressure_kip_in2"]) >= 0) is e["negative_compressive_pressure_valid"]
        assert e["automatic_abs_or_clipping_permitted"] is False
    elif case["method"] == "IN_PLANE_BOLT_GROUP":
        points = [vector(p) for p in i["points_in"]]
        center = tuple(sum((p[k] for p in points), R(0)) / len(points) for k in range(2))
        relative = [subtract(p, center) for p in points]
        polar = sum(sum(v * v for v in p) for p in relative)
        f = vector(i["force_kip"])
        r = vector(i["reference_in"])
        arm = subtract(r, center)
        mc = R(i["free_moment_kip_in"]) + arm[0] * f[1] - arm[1] * f[0]
        bolts = tuple(
            (f[0] / len(points) - mc * p[1] / polar, f[1] / len(points) + mc * p[0] / polar)
            for p in relative
        )
        assert center == vector(e["centroid_in"])
        assert polar == R(e["J_in2"])
        assert mc == R(e["centroid_moment_kip_in"])
        assert bolts == tuple(vector(v) for v in e["bolt_vectors_kip"])
        assert tuple(sum(b[k] for b in bolts) - f[k] for k in range(2)) == vector(
            e["force_closure_kip"]
        )
        assert sum(
            p[0] * b[1] - p[1] * b[0] for p, b in zip(relative, bolts, strict=True)
        ) - mc == R(e["moment_closure_kip_in"])
    elif identifier == "F45-21":
        cumulative = vector([0, 0])
        cuts = []
        for f in i["external_in_plane_actions_kip"]:
            cumulative = add(cumulative, vector(f))
            cuts.append(cumulative)
        assert cumulative == vector(e["resultant_force_kip"])
        assert cuts == [vector(v) for v in e["cumulative_in_plane_cut_forces_kip"]]
        assert [sum(v * v for v in f) for f in cuts] == [R(v) for v in e["cut_force_squared_kip2"]]
        assert e["physical_shank_count"] == 1
        assert e["automatic_double_capacity"] is False
    elif identifier == "F45-22":
        gap = min(abs(R(x) - R(y)) for x in i["X_set_z_in"] for y in i["Y_set_z_in"])
        assert gap == R(e["minimum_axis_distance_in"])
        assert gap - R(i["nominal_diameter_in"]) == R(e["minimum_shank_surface_clearance_in"])
        assert gap - R(i["hole_diameter_in"]) == R(e["minimum_hole_envelope_clearance_in"])
        assert abs(R(2) - R(2)) == R(e["same_elevation_crossing_axis_distance_in"])
        assert (R(i["hole_diameter_in"]) > 0) is e["same_elevation_crossing_rejected"]
    elif identifier == "F45-23":
        inch, kip = R(i["inch_to_mm"]), R(i["kip_to_kN"])
        assert R(i["hole_in"]) * inch == R(e["hole_mm"])
        assert tuple(v * kip for v in vector(i["force_kip"])) == vector(e["force_kN"])
        moments = tuple(v * kip * inch for v in vector(i["moment_kip_in"]))
        assert moments == vector(e["moment_kN_mm"])
        assert tuple(v / 1000 for v in moments) == vector(e["moment_kN_m"])
        assert inch**2 == R(e["area_1_in2_mm2"])
    else:
        assert identifier == "F45-24"
        for name, q in i["frames_rows"].items():
            qt = [list(row) for row in zip(*q, strict=True)]
            f = rotate(qt, vector(i["global_force_kip"]))
            m = rotate(qt, vector(i["global_moment_kip_in"]))
            assert f == vector(e[name]["local_force_ABC_kip"])
            assert m == vector(e[name]["local_moment_ABC_kip_in"])
            assert rotate(q, f) == vector(i["global_force_kip"])
            assert rotate(q, m) == vector(i["global_moment_kip_in"])
            assert e[name]["discarded_components"] == []
