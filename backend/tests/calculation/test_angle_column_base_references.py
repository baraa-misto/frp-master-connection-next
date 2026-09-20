"""F44-01..14 independent rational mathematics, never native serialization oracles."""

import json
from fractions import Fraction as R
from pathlib import Path
from typing import Any

import pytest

MATRIX: dict[str, Any] = json.loads(
    (Path(__file__).parents[1] / "golden/stage_4_4_acceptance_matrix_rc1.json").read_text()
)
FIXTURES = {v["id"]: v for v in MATRIX["reference_fixtures"]}
Vector = tuple[R, ...]


def vector(values: list[str | int]) -> Vector:
    return tuple(R(v) for v in values)


def add(a: Vector, b: Vector) -> Vector:
    return tuple(x + y for x, y in zip(a, b, strict=True))


def subtract(a: Vector, b: Vector) -> Vector:
    return tuple(x - y for x, y in zip(a, b, strict=True))


def cross(a: Vector, b: Vector) -> Vector:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def rotate(q: list[list[int]], v: Vector) -> Vector:
    return tuple(sum((R(a) * b for a, b in zip(row, v, strict=True)), R(0)) for row in q)


def connector_math(identifier: str) -> dict[str, Vector]:
    inp = FIXTURES[identifier]["input"]
    q = inp["Q_rows"]
    h, rm, rs, f, m = (
        vector(inp[k])
        for k in (
            "global_heel_origin_in",
            "r_M_local_in",
            "r_S_local_in",
            "F_M_local_kip",
            "M_M_local_kip_in",
        )
    )
    mh = add(m, cross(rm, f))
    ms = add(m, cross(subtract(rm, rs), f))
    gs, gm, gf, gsm = add(h, rotate(q, rs)), add(h, rotate(q, rm)), rotate(q, f), rotate(q, ms)
    return dict(
        zip(
            (
                "M_heel_local_kip_in",
                "M_support_local_kip_in",
                "global_support_reference_in",
                "global_member_reference_in",
                "F_global_kip",
                "M_support_global_kip_in",
                "M_about_foundation_origin_kip_in",
            ),
            (mh, ms, gs, gm, gf, gsm, add(gsm, cross(gs, gf))),
            strict=True,
        )
    )


@pytest.mark.parametrize("identifier", [f"F44-{n:02}" for n in range(1, 15)])
def test_independent_exact_reference_fixture(identifier: str) -> None:
    case = FIXTURES[identifier]
    inp, expected = case["input"], case["expected"]
    zero = vector([0, 0, 0])
    if identifier in {"F44-01", "F44-14"}:
        for key, q in inp.items():
            if key.endswith("_rows"):
                assert sum(R(q[0][j]) * cross(vector(q[1]), vector(q[2]))[j] for j in range(3)) == 1
                assert all(
                    sum(R(q[k][i]) * R(q[k][j]) for k in range(3)) == int(i == j)
                    for i in range(3)
                    for j in range(3)
                )
        if identifier == "F44-01":
            assert rotate(inp["Q1_rows"], vector([4, -6, -2])) == vector(
                expected["Q1_global_force"]
            )
            assert rotate(inp["Q2_rows"], vector([4, -6, -2])) == vector(
                expected["Q2_global_force"]
            )
        else:
            assert rotate(inp["Q_rows"], vector(inp["F_kip"])) == vector(
                expected["rotated_force_kip"]
            )
            assert rotate(inp["Q_rows"], vector(inp["M_O_kip_in"])) == vector(
                expected["rotated_moment_kip_in"]
            )
    elif identifier in {"F44-02", "F44-03"}:
        bx, by, t = (R(inp[k]) for k in ("leg_x_in", "leg_y_in", "uniform_thickness_in"))
        rectangles = [(bx, t, R(1)), (t, by, R(1)), (t, t, R(-1))]
        area = sum(w * h * s for w, h, s in rectangles)
        x = sum(w * h * s * w / 2 for w, h, s in rectangles) / area
        y = sum(w * h * s * h / 2 for w, h, s in rectangles) / area
        values = [
            area,
            x,
            y,
            sum(s * w * h**3 / 3 for w, h, s in rectangles) - area * y * y,
            sum(s * h * w**3 / 3 for w, h, s in rectangles) - area * x * x,
            sum(s * w * w * h * h / 4 for w, h, s in rectangles) - area * x * y,
        ]
        keys = [
            "area_in2",
            "centroid_x_in",
            "centroid_y_in",
            "Ixx_centroid_in4",
            "Iyy_centroid_in4",
            "Ixy_centroid_in4",
        ]
        assert values == [R(expected[k]) for k in keys]
    elif identifier == "F44-04":
        f = vector(inp["F_kip"])
        shifted = add(
            vector(inp["M_R_kip_in"]),
            cross(subtract(vector(inp["r_R_in"]), vector(inp["r_O_in"])), f),
        )
        assert f == vector(expected["F_O_kip"])
        assert shifted == vector(expected["M_O_kip_in"])
    elif identifier in {"F44-05", "F44-06"}:
        for key, value in connector_math(identifier).items():
            assert value == vector(expected[key])
    elif identifier in {"F44-07", "F44-08"}:
        source = FIXTURES["F44-07"]["input"]
        cf = vector(source["direct_contact_force_on_foundation_kip"])
        cm = add(
            vector(source["direct_contact_free_moment_kip_in"]),
            cross(vector(source["direct_contact_reference_in"]), cf),
        )
        if identifier == "F44-08":
            assert subtract(zero, cf) == vector(expected["computed_minus_required_force_kip"])
            assert subtract(zero, cm) == vector(expected["computed_minus_required_moment_kip_in"])
        else:
            one, two = connector_math("F44-05"), connector_math("F44-06")
            force = add(add(one["F_global_kip"], two["F_global_kip"]), cf)
            moment = add(
                add(
                    one["M_about_foundation_origin_kip_in"], two["M_about_foundation_origin_kip_in"]
                ),
                cm,
            )
            assert force == vector(expected["foundation_force_kip"])
            assert moment == vector(expected["foundation_moment_at_O_kip_in"])
            assert moment == add(
                vector(inp["applied_moment_at_R_kip_in"]),
                cross(vector(inp["applied_reference_R_in"]), vector(inp["applied_force_kip"])),
            )
    elif identifier in {"F44-09", "F44-10"}:
        source = FIXTURES["F44-09"]["input"]
        points = [vector(p) for p in source["coordinates_A_B_in"]]
        center = tuple(sum((p[k] for p in points), R(0)) / len(points) for k in range(2))
        assert center == (R(0), R(3))
        polar = sum((sum((v * v for v in subtract(p, center)), R(0)) for p in points), R(0))
        assert polar == 13
        fa, fb = vector(source["F_A_B_kip"])
        mc = R(source["M_C_kip_in"])
        if identifier == "F44-10":
            centroid_moment = mc - center[0] * fb + center[1] * fa
            assert centroid_moment == R(expected["centroid_M_C_kip_in"])
            assert centroid_moment - mc == R(expected["additional_centroid_M_C_kip_in"])
            assert (centroid_moment == mc) is expected["equal_to_original_vectors"]
        else:
            forces = [
                (fa / 4 - mc * (p[1] - center[1]) / polar, fb / 4 + mc * (p[0] - center[0]) / polar)
                for p in points
            ]
            assert forces == [vector(p) for p in expected["per_bolt_A_B_kip"]]
            assert [sum(v * v for v in p) for p in forces] == [
                R(v) for v in expected["squared_magnitudes_kip2"]
            ]
            assert (
                sum(
                    (p[0] - center[0]) * f[1] - (p[1] - center[1]) * f[0]
                    for p, f in zip(points, forces, strict=True)
                )
                == mc
            )
    elif identifier == "F44-11":
        xb, yb = (vector(v) for v in inp["rectangle_xy_bounds_in"])
        cf = (
            R(0),
            R(0),
            -R(inp["uniform_pressure_kip_per_in2"]) * (xb[1] - xb[0]) * (yb[1] - yb[0]),
        )
        cm = cross(((xb[1] + xb[0]) / 2, (yb[1] + yb[0]) / 2, R(0)), cf)
        assert cf == vector(expected["force_kip"])
        assert cm == vector(expected["moment_about_O_kip_in"])
    elif identifier == "F44-12":
        df1 = vector(inp["delta_force_at_member_reference_1_global_kip"])
        df2 = vector(inp["delta_force_at_member_reference_2_global_kip"])
        dm = vector(inp["delta_free_moment_at_member_reference_2_global_kip_in"])
        assert add(df1, df2) == zero
        assert (
            add(
                add(
                    cross(connector_math("F44-05")["global_member_reference_in"], df1),
                    cross(connector_math("F44-06")["global_member_reference_in"], df2),
                ),
                dm,
            )
            == zero
        )
    else:
        assert identifier == "F44-13"
        assert R(inp["length_in"]) * R(inp["inch_to_mm"]) == R(expected["length_mm"])
        assert R(inp["force_kip"]) * R(inp["kip_to_kN"]) == R(expected["force_kN"])
        assert R(inp["moment_kip_in"]) * R(inp["kip_to_kN"]) * R(inp["inch_to_mm"]) == R(
            expected["moment_kN_mm"]
        )
