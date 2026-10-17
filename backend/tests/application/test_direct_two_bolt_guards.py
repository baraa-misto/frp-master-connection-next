"""Geometric invariants and exact signed boundaries, without engineering activation."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from frp_master_connection.application.direct_two_bolt_geometry import (
    ONE,
    ZERO,
    Axes,
    Cylinder,
    Obstacle,
    PairInput,
    accessible_strips,
    add,
    bounded_regions,
    circle_box_margin,
    clip_polygon,
    cylinder_obstruction,
    evaluate_pair,
    fit_state,
    global_point,
    local_point,
    polygon_boundaries,
    shifted_moment,
    validate_frame,
)
from tests.direct_sab2_fixtures import controls, study_pair

IDENTITY: Axes = ((ONE, ZERO, ZERO), (ZERO, ONE, ZERO), (ZERO, ZERO, ONE))


def nominal() -> PairInput:
    row = next(
        r
        for r in controls()
        if r["input"]["id"].startswith("D2 nominal")
        and r["input"]["pattern"] == "SUPPORT"
        and r["input"]["pitch"] == "2.25"
    )
    return study_pair(row)


@pytest.mark.parametrize(
    "changes",
    [
        {"midpoint": (Decimal("NaN"), ZERO, ZERO)},
        {"spacing": ZERO},
        {"shaft_radius": ZERO},
        {"hole_radius": Decimal(".1")},
        {"washer_radius": Decimal(".1")},
        {"direction": (ZERO, ZERO, ZERO)},
        {"normal": (ZERO, ZERO, ZERO)},
        {"direction": (ZERO, ONE, ZERO)},
        {"shaft_span": (ONE, ZERO)},
        {"hardware": (Cylinder("HEAD", ONE, ZERO, ONE, ""),)},
        {"hardware": (Cylinder("HEAD", Decimal("NaN"), ZERO, ONE, "Stated"),)},
    ],
)
def test_invalid_pair_geometry_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"finite|positive|conflict|unit|plane|cylinder"):
        evaluate_pair(replace(nominal(), **changes))


@pytest.mark.parametrize("kind", ["one", "duplicate", "normal", "bounds", "strip", "obstacle"])
def test_both_real_members_faces_and_physical_obstacles_are_required(kind: str) -> None:
    pair = nominal()
    if kind == "one":
        pair = replace(pair, faces=pair.faces[:1])
    elif kind == "duplicate":
        pair = replace(pair, faces=(pair.faces[0], pair.faces[0]))
    elif kind == "normal":
        pair = replace(pair, faces=(replace(pair.faces[0], axes=IDENTITY), pair.faces[1]))
    elif kind == "bounds":
        pair = replace(pair, faces=(replace(pair.faces[0], boundaries=()), pair.faces[1]))
    elif kind == "strip":
        pair = replace(
            pair, faces=(pair.faces[0], replace(pair.faces[1], seating_strips=((ZERO, ZERO),)))
        )
    else:
        pair = replace(
            pair,
            obstacles=(
                Obstacle(
                    "bad",
                    (ZERO, ZERO, ZERO),
                    IDENTITY,
                    (ZERO, ZERO, ZERO),
                    (ONE, ZERO, ONE),
                    "Stated",
                ),
            ),
        )
    with pytest.raises(ValueError, match=r"members|normal|boundaries|strip|dimensions"):
        evaluate_pair(pair)


@pytest.mark.parametrize(
    "axes",
    [
        ((Decimal("NaN"), ZERO, ZERO), (ZERO, ONE, ZERO), (ZERO, ZERO, ONE)),
        ((Decimal(2), ZERO, ZERO), (ZERO, ONE, ZERO), (ZERO, ZERO, ONE)),
        ((ONE, ZERO, ZERO), (ONE, ZERO, ZERO), (ZERO, ZERO, ONE)),
        ((ONE, ZERO, ZERO), (ZERO, ONE, ZERO), (ZERO, ZERO, -ONE)),
    ],
)
def test_nonfinite_nonunit_nonorthogonal_and_reflected_frames_are_rejected(axes: Axes) -> None:
    with pytest.raises(ValueError, match="Frame"):
        validate_frame(axes)


def test_proper_rotation_and_origin_recover_exact_local_coordinates() -> None:
    axes: Axes = ((ZERO, ONE, ZERO), (-ONE, ZERO, ZERO), (ZERO, ZERO, ONE))
    validate_frame(axes)
    origin, local = (Decimal(7), Decimal(-4), Decimal(9)), (ONE, Decimal(2), Decimal(3))
    assert local_point(global_point(local, origin, axes), origin, axes) == local


@pytest.mark.parametrize(
    "polygon",
    [
        ((ZERO, ZERO), (ONE, ZERO)),
        ((ZERO, ZERO), (ONE, ZERO), (ONE, ZERO), (ZERO, ONE)),
        ((ZERO, ZERO), (ZERO, ONE), (ONE, ONE), (ONE, ZERO)),
        (
            (ZERO, ZERO),
            (Decimal(2), ZERO),
            (ONE, ONE),
            (Decimal(2), Decimal(2)),
            (ZERO, Decimal(2)),
        ),
    ],
)
def test_invalid_physical_polygons_are_not_reinterpreted(
    polygon: tuple[tuple[Decimal, Decimal], ...],
) -> None:
    with pytest.raises(ValueError, match="polygon"):
        polygon_boundaries(polygon, "Explicit invalid test")


@pytest.mark.parametrize(
    ("low", "high", "root"),
    [
        (ONE, Decimal(2), ZERO),
        (Decimal(-2), Decimal(2), Decimal(-1)),
        (Decimal(-2), Decimal(2), Decimal(2)),
    ],
)
def test_invalid_or_consumed_rear_outstands_are_rejected(
    low: Decimal, high: Decimal, root: Decimal
) -> None:
    with pytest.raises(ValueError, match=r"dimensions|consumes"):
        accessible_strips(low, high, Decimal("-.2"), Decimal(".2"), root, "I")


@pytest.mark.parametrize(
    ("margin", "state"),
    [
        ("-1E-30", "DOES_NOT_FIT"),
        ("0", "CONDITIONAL"),
        ("1E-30", "FIT_FOR_STATED_GEOMETRY"),
    ],
)
def test_signed_boundary_is_never_epsilon_shifted_to_fit(margin: str, state: str) -> None:
    assert fit_state((Decimal(margin),)) == state
    assert fit_state((Decimal("1"),), ("Manufactured dimensions unknown",)) == "CONDITIONAL"
    assert fit_state(()) == "NOT_EVALUATED"


def test_obstruction_includes_axial_contact_but_not_disjoint_solids() -> None:
    obstacle = Obstacle(
        "known",
        (ZERO, ZERO, ZERO),
        IDENTITY,
        (ZERO, ZERO, ZERO),
        (ONE, ONE, ONE),
        "Explicit dimensions",
    )
    shaft = Cylinder("SHAFT", Decimal(".25"), ONE, Decimal(2), "Explicit dimensions")
    point = (Decimal(".5"), Decimal(".5"), ZERO)
    assert cylinder_obstruction(point, IDENTITY[2], shaft, obstacle) == ZERO
    assert (
        cylinder_obstruction((Decimal(2), Decimal(2), ZERO), IDENTITY[2], shaft, obstacle) is None
    )
    assert (
        cylinder_obstruction(point, IDENTITY[2], replace(shaft, start=Decimal("1.001")), obstacle)
        is None
    )
    assert cylinder_obstruction(
        point, IDENTITY[2], replace(shaft, start=ZERO), obstacle
    ) == Decimal("-.75")
    with pytest.raises(ValueError, match="Oblique"):
        cylinder_obstruction(point, IDENTITY[0], shaft, obstacle)
    assert circle_box_margin((Decimal(2), ZERO), Decimal(".25"), (ZERO, ONE, ZERO, ONE)) == Decimal(
        ".75"
    )
    with pytest.raises(ValueError, match="dimensions"):
        circle_box_margin((ZERO, ZERO), ONE, (ZERO, ZERO, ZERO, ONE))
    with pytest.raises(ValueError, match="dimensions"):
        circle_box_margin((ZERO, ZERO), ONE, (ZERO, ONE, ZERO, ZERO))


def test_stated_hardware_tool_and_neighbor_interference_keep_separate_states() -> None:
    pair = nominal()
    result = evaluate_pair(
        replace(
            pair,
            hardware=(
                Cylinder("HEAD", Decimal(".4"), Decimal(-1), Decimal("-.6"), "Stated head"),
                Cylinder("NUT", Decimal(".4"), Decimal(".5"), Decimal(".8"), "Stated nut"),
                Cylinder("TOOL", Decimal(2), Decimal(".5"), Decimal(2), "Stated tool"),
            ),
        )
    )
    assert result.hardware_state == "FIT_FOR_STATED_GEOMETRY"
    assert result.installation_state == "DOES_NOT_FIT"
    assert result.aggregate_state == "DOES_NOT_FIT"
    assert result.obstruction_state == "NOT_EVALUATED"
    head = Cylinder("HEAD", Decimal(".4"), Decimal(-1), Decimal("-.6"), "Stated head")
    nut = Cylinder("NUT", Decimal(".4"), Decimal(".5"), Decimal(".8"), "Stated nut")
    for supplied, missing in (((head,), "nut"), ((nut,), "head")):
        partial = evaluate_pair(replace(pair, hardware=supplied))
        assert partial.hardware_state == "CONDITIONAL"
        assert partial.installation_state == "NOT_EVALUATED"
        assert f"Actual {missing} body not represented" in partial.unknowns
        assert partial.aggregate_state == "CONDITIONAL"
    absent = evaluate_pair(pair)
    assert absent.hardware_state == "NOT_EVALUATED"
    assert "Actual head body not represented" in absent.unknowns
    assert "Actual nut body not represented" in absent.unknowns
    assert "Installation access not evaluated" in absent.unknowns


def test_region_exhaustion_means_only_no_candidate_in_stated_domain() -> None:
    pair = nominal()
    with pytest.raises(ValueError, match="positive rectangular bounds"):
        bounded_regions(pair, (IDENTITY[0], IDENTITY[2]), (ZERO, ZERO, ZERO, ONE))
    assert not bounded_regions(
        pair, (IDENTITY[0], IDENTITY[2]), (Decimal(10), Decimal(11), Decimal(10), Decimal(11))
    )
    assert clip_polygon((), (ONE, ZERO, ONE)) == ()
    assert pair == nominal()


def test_moment_shift_is_signed_reference_identity_only() -> None:
    moment, force = (ONE, Decimal(2), Decimal(3)), (Decimal(4), Decimal(5), Decimal(6))
    p, g = (Decimal(7), Decimal(8), Decimal(9)), (ONE, ONE, ONE)
    expected = (Decimal(3), Decimal(-2), Decimal(5))
    assert shifted_moment(moment, p, g, force) == expected
    assert shifted_moment(moment, p, p, force) == moment
    assert add(force, (ZERO, ZERO, ZERO)) == force
