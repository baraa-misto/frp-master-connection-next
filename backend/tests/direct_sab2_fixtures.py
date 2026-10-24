"""Explicit SAB1 study coordinates, never production geometry defaults."""

from __future__ import annotations

import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Literal, cast

from frp_master_connection.application.direct_two_bolt_geometry import (
    ONE,
    V3,
    ZERO,
    Axes,
    Boundary,
    Face,
    Obstacle,
    PairInput,
    accessible_strips,
    polygon_boundaries,
)


def controls() -> list[dict[str, Any]]:
    path = Path(__file__).parent / "data/direct_sab2_sab1_controls.json"
    return cast(list[dict[str, Any]], json.loads(path.read_text())["cases"])


def vector(values: list[str]) -> V3:
    return Decimal(values[0]), Decimal(values[1]), Decimal(values[2])


def study_pair(row: dict[str, Any]) -> PairInput:
    """Adapt explicit original study datums by proper frames into the shared kernel."""
    with localcontext() as context:
        context.prec = 64
        return _study_pair(row)


def _study_pair(row: dict[str, Any]) -> PairInput:
    case, expected = row["input"], row["expected"]
    axes = cast(Axes, tuple(vector(a) for a in expected["axes"]))
    angle_polygon = tuple((Decimal(p[0]), Decimal(p[1])) for p in case["angle_polygon"])
    boundaries = polygon_boundaries(angle_polygon, "SAB1 explicit illustrative Angle polygon")
    boundaries = tuple(
        Boundary(
            b.id,
            b.a,
            b.b,
            b.limit,
            b.role,
            b.source,
            Decimal(case["free_edge_target"]) if b.a == ZERO and b.b == ONE else ZERO,
        )
        for b in boundaries
    )
    angle = Face(
        "Angle",
        "Angle",
        vector(case["angle_origin"]),
        axes,
        boundaries,
        (),
        tuple(case["unknowns"]),
        "Explicit illustrative SAB1 Angle placement",
    )
    width, web, root = (
        Decimal(case["flange_width"]),
        Decimal(case["web_thickness"]),
        Decimal(case["support_root"]),
    )
    half = width / 2
    family: Literal["I", "CHANNEL"] = "I" if case["support_kind"] == "I" else "CHANNEL"
    web_low, web_high = (-web / 2, web / 2) if family == "I" else (-half, -half + web)
    strips = accessible_strips(-half, half, web_low, web_high, root, family)
    support_axes: Axes = ((ZERO, ZERO, ONE), (ONE, ZERO, ZERO), (ZERO, ONE, ZERO))
    support_boundaries = [
        Boundary(
            "support:left toe",
            ZERO,
            -ONE,
            half,
            "PHYSICAL_FREE_EDGE",
            "SAB1 flange width",
            Decimal(case["free_edge_target"]),
        ),
        Boundary(
            "support:right toe",
            ZERO,
            ONE,
            half,
            "PHYSICAL_FREE_EDGE",
            "SAB1 flange width",
            Decimal(case["free_edge_target"]),
        ),
    ]
    if "support_ends" in case:
        support_boundaries.extend(
            (
                Boundary(
                    "support:negative end",
                    -ONE,
                    ZERO,
                    -Decimal(case["support_ends"][0]),
                    "EXPLICIT_STUDY_END",
                    "SAB1 stated finite cut",
                ),
                Boundary(
                    "support:positive end",
                    ONE,
                    ZERO,
                    Decimal(case["support_ends"][1]),
                    "EXPLICIT_STUDY_END",
                    "SAB1 stated finite cut",
                ),
            )
        )
    support = Face(
        "support",
        "support",
        (half, ZERO, ZERO),
        support_axes,
        tuple(support_boundaries),
        strips,
        tuple(case["unknowns"]),
        "SAB1 explicit support strip dimensions",
    )
    obstacles: list[Obstacle] = []
    for obstacle in case.get("obstacles", []):
        u0, u1, v0, v1 = (Decimal(v) for v in obstacle["bounds_xz"])
        n0, n1 = (
            (Decimal(".1"), Decimal(".2"))
            if obstacle["envelope"] == "shaft"
            else (Decimal(".375"), Decimal(".426"))
        )
        obstacles.append(
            Obstacle(
                obstacle["id"],
                (half, ZERO, ZERO),
                support_axes,
                (v0, u0 - half, n0),
                (v1, u1 - half, n1),
                "Explicit illustrative SAB1 footprint and stated test axial interval; "
                "not actual neighboring hardware",
            )
        )
    return PairInput(
        vector(case["midpoint"]),
        axes[0] if case["pattern"] == "BRACE" else (ZERO, ZERO, ONE),
        (ZERO, ONE, ZERO),
        Decimal(case["pitch"]),
        Decimal(case["bolt_diameter"]) / 2,
        Decimal(case["hole_diameter"]) / 2,
        Decimal(case["washer_diameter"]) / 2,
        (Decimal("-.5"), Decimal(".375")),
        ((Decimal("-.551"), Decimal("-.5")), (Decimal(".375"), Decimal(".426"))),
        (angle, support),
        tuple(obstacles),
    )
