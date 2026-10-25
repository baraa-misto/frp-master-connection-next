"""Independent geometry boundaries and exact accepted-view preservation."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.hyb1_contract import Alignment
from frp_master_connection.application.hybrid_physical_geometry import (
    EndCondition,
    ReceivingEnd,
    ReceivingEnds,
    r3_scene_geometry,
)
from frp_master_connection.application.hybrid_workflow import source_scene
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, execute_r3


def q(value: str) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, Unit.IN)


@pytest.mark.parametrize("angle", ["30.9", "45", "70"])
@pytest.mark.parametrize("alignment", [Alignment.SUPPORT, Alignment.BRACE])
def test_geometry_only_scene_exactly_preserves_accepted_scene(
    angle: str, alignment: Alignment
) -> None:
    g = R3Geometry(phi=Decimal(angle))
    accepted = execute_r3(geometry=g)
    pure = r3_scene_geometry(g)
    assert pure.bolt_centers == accepted.bolt_centers
    assert pure.rotation_centers == accepted.rotation_centers
    assert pure.edges == accepted.edges
    assert pure.hole_fit == accepted.hole_fit
    assert pure.rotation_fit == accepted.rotation_fit
    assert source_scene(g, pure, alignment) == source_scene(g, accepted, alignment)


@pytest.mark.parametrize(
    ("end", "expected"),
    [("1.281499999999", (("B1", "positive"),)), ("1.2815", ()), ("1.281500000001", ())],
)
def test_real_end_hole_containment_has_exact_boundary(
    end: str, expected: tuple[tuple[str, str], ...]
) -> None:
    physical = r3_scene_geometry(
        R3Geometry(), ReceivingEnds(ReceivingEnd(EndCondition.FREE, q(end)))
    )
    assert physical.end_failures == expected
    assert physical.hole_fit is (not expected)


def test_real_negative_end_and_order_are_not_positive_end_or_display_crops() -> None:
    g = replace(R3Geometry(), reverse_bolt_order=True)
    geometry = r3_scene_geometry(
        g, ReceivingEnds(negative=ReceivingEnd(EndCondition.FREE, q("1.2")))
    )
    assert geometry.end_failures == (("B2", "negative"),)
    assert not geometry.hole_fit
    assert r3_scene_geometry(g).hole_fit


@pytest.mark.parametrize("condition", [EndCondition.UNKNOWN, EndCondition.CONTINUOUS])
def test_no_fabricated_distance_on_unknown_or_continuous_end(condition: EndCondition) -> None:
    with pytest.raises(ValueError, match="fabricated"):
        ReceivingEnd(condition, q("6"))


@pytest.mark.parametrize("distance", [None, q("-1")])
def test_free_end_needs_actual_nonnegative_distance(
    distance: PhysicalQuantity | None,
) -> None:
    with pytest.raises(ValueError, match="real free end"):
        ReceivingEnd(EndCondition.FREE, distance)


def test_declared_gap_translates_each_surface_once_without_resistance() -> None:
    g = R3Geometry()
    model = r3_scene_geometry(g)
    original = source_scene(g, model, Alignment.SUPPORT)
    actual = source_scene(g, model, Alignment.SUPPORT, interface_gap=q(".25"))
    for before, after in zip(
        original["meshes"][0]["points"], actual["meshes"][0]["points"], strict=True
    ):
        assert after["y"] == before["y"] - 0.25
    assert actual["cylinders"][0]["start"]["y"] == original["cylinders"][0]["start"]["y"] - 0.25
    assert actual["boxes"][3]["center"]["y"] == original["boxes"][3]["center"]["y"] - 0.25
    assert actual["boxes"][:3] == original["boxes"][:3]


def test_zero_extent_cannot_be_drawn_as_a_valid_member() -> None:
    ends = ReceivingEnds(
        ReceivingEnd(EndCondition.FREE, q("0")), ReceivingEnd(EndCondition.FREE, q("0"))
    )
    g = R3Geometry()
    with pytest.raises(ValueError, match="positive longitudinal extent"):
        source_scene(g, r3_scene_geometry(g, ends), Alignment.SUPPORT, receiving_ends=ends)
