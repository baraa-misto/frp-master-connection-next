"""Native geometry rejection and R1 zero-gap/unequal-profile regression proof."""

from dataclasses import replace
from decimal import Decimal
from itertools import product
from typing import Any

import pytest

from frp_master_connection.api.ssmc import illustrative_ssmc, map_ssmc_request
from frp_master_connection.application.ssmc import design_ssmc, preview_ssmc
from frp_master_connection.application.ssmc_geometry import geometry_ssmc
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.ssmc import StringerForm
from frp_master_connection.geometry.ssmc_paths import CircularHoleLoop, connected_ligament
from frp_master_connection.geometry.ssmc_polygon import (
    construct_miter_polygon,
    contains_disk,
    distance_squared,
    unit,
    validate_polygon,
)


def inch(value: str) -> Q:
    return Q(Decimal(value), Unit.IN)


@pytest.mark.parametrize(
    ("h", "i", "angle", "gap"),
    list(product(StringerForm, StringerForm, (-45, -35, -30, 30, 35, 45), ("0", "0.125"))),
)
def test_unequal_profiles_and_branch_depths_keep_r1_datum_and_native_solids(
    h: StringerForm, i: StringerForm, angle: int, gap: str
) -> None:
    request = map_ssmc_request(illustrative_ssmc())
    request = replace(
        request,
        theta_deg=Decimal(angle),
        horizontal=replace(request.horizontal, form=h),
        inclined=replace(request.inclined, form=i, depth=inch("8"), web_thickness=inch("0.375")),
        plate=replace(request.plate, normal_gap=inch(gap), inclined_depth=inch("3.5")),
    )
    geometry = geometry_ssmc(request)
    assert geometry.polygon.work_point == (0, 0)
    assert geometry.polygon.gross_neck_width > 0
    assert len(geometry.members) == 2
    assert all(m.trimmed.solids for m in geometry.members)
    assert all(c.qualified_resistance is None for c in geometry.polygon_paths.candidates)
    assert any(c.connected_material for c in geometry.polygon_paths.candidates)
    assert any(not c.connected_material for c in geometry.polygon_paths.candidates)


@pytest.mark.parametrize(
    ("part", "field", "value", "message"),
    [
        ("plate", "corner_radius", "0.1", "CORNER_TREATMENT"),
        ("plate", "chamfer", "0.1", "CORNER_TREATMENT"),
        ("plate", "horizontal_depth", "10", "MEMBER_OVERLAP"),
        ("horizontal", "length", "10", "MEMBER_OVERLAP"),
        ("horizontal_group", "gauge", "10", "MEMBER_HOLE"),
        ("horizontal_group", "gauge", "8.4", "MEMBER_HARDWARE"),
        ("horizontal_group", "first_from_cut", "0.1", "MITER_HARDWARE"),
        ("plate", "horizontal_depth", "2", "POLYGON_HOLE"),
        ("plate", "horizontal_depth", "2.8", "POLYGON_HARDWARE"),
        ("horizontal_group", "pitch", "0.5", "HARDWARE_INTERFERENCE"),
    ],
)
def test_native_containment_rejects_without_geometry_repair(
    part: str, field: str, value: str, message: str
) -> None:
    request = map_ssmc_request(illustrative_ssmc())
    changed = replace(request, **{part: replace(getattr(request, part), **{field: inch(value)})})
    with pytest.raises(ValueError, match=message):
        geometry_ssmc(changed)
    assert getattr(getattr(changed, part), field) == inch(value)


@pytest.mark.parametrize(
    ("part", "changes", "message"),
    [
        ("horizontal", {"form": "CHANNEL"}, "TOPOLOGY"),
        ("horizontal", {"length": inch("0")}, "POSITIVE_DIMENSION"),
        ("horizontal", {"width": Q(Decimal(1), Unit.KIP)}, "QUANTITY_DIMENSION"),
        ("horizontal_group", {"rows": 1}, "GROUP_TOPOLOGY"),
        ("horizontal_group", {"rows": 4}, "GROUP_TOPOLOGY"),
        ("horizontal_group", {"ordinary_snug_tight": "yes"}, "GROUP_ASSUMPTION"),
        ("plate", {"side": "BOTH"}, "TOPOLOGY"),
        ("plate", {"normal_gap": inch("-1")}, "REFERENCE_GEOMETRY"),
        ("fastener", {"hole_diameter": inch("0.5")}, "HOLE_GEOMETRY"),
        ("fastener", {"hole_diameter": inch("2")}, "HARDWARE_GEOMETRY"),
        ("fastener", {"threads": "INVENTED"}, "HARDWARE_GEOMETRY"),
        ("request", {"contract": "FUTURE"}, "CONTRACT"),
        ("request", {"unit_system": "OTHER"}, "CONTRACT"),
        ("request", {"request_id": " "}, "REQUEST_ID"),
    ],
)
def test_invalid_domain_contracts_fail_closed(
    part: str, changes: dict[str, Any], message: str
) -> None:
    request = map_ssmc_request(illustrative_ssmc())
    with pytest.raises(ValueError, match=message):
        replace(request if part == "request" else getattr(request, part), **changes)


@pytest.mark.parametrize("flag", ["slots", "ordinary_snug_tight", "equal_translational_stiffness"])
def test_ineligible_planar_component_does_not_erase_full_wrench(flag: str) -> None:
    request = map_ssmc_request(illustrative_ssmc())
    request = replace(request, N=Q(Decimal(8), Unit.KIP), M=Q(Decimal(20), Unit.KIP_IN))
    eligible = preview_ssmc(request)
    assumptions: dict[str, Any] = {flag: flag == "slots"}
    changed = replace(request, horizontal_group=replace(request.horizontal_group, **assumptions))
    ineligible = design_ssmc(changed)
    assert ineligible.groups[0].native_slice8 is None
    assert ineligible.groups[0].plate_wrench == eligible.groups[0].plate_wrench
    assert ineligible.groups[1].native_slice8 == eligible.groups[1].native_slice8
    assert "SSMC_PLANAR_GROUP_RESPONSE_NOT_QUALIFIED" in ineligible.blockers
    assert ineligible.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"


@pytest.mark.parametrize(
    "polygon",
    [
        (),
        ((0, 0), (1, 0)),
        ((0, 0), (float("nan"), 1), (1, 0)),
        ((0, 0), (1, 0), (2, 0)),
        ((0, 0), (0, 0), (1, 1), (1, 0)),
        ((0, 0), (3, 2), (0, 2), (2, 0)),
        ((0, 0), (3, 0), (3, 3), (1, 0), (0, 3)),
    ],
)
def test_polygon_kernel_rejects_degenerate_and_crossing_boundaries(
    polygon: tuple[tuple[float, float], ...],
) -> None:
    with pytest.raises(ValueError, match="SSMC_POLYGON_INVALID"):
        validate_polygon(polygon)


def test_geometry_kernel_degeneracy_and_actual_concave_ligament_authority() -> None:
    with pytest.raises(ValueError, match="REFERENCE_GEOMETRY"):
        unit((0, 0))
    assert distance_squared((2, 0), (0, 0), (0, 0)) == 4
    polygon = construct_miter_polygon(-35, 0.125, (4, 4), (8, 8))
    assert not contains_disk(polygon.boundary, (0, 0), 0)
    hole = CircularHoleLoop("test", "test", (-4, 0), 0.5)
    assert not connected_ligament(polygon, (hole,), (-6, 0), (-2, 0))
    assert connected_ligament(polygon, (), (-6, 0), (-2, 0))
    with pytest.raises(ValueError, match="INCLINATION"):
        construct_miter_polygon(0, 0, (4, 4), (8, 8))
    with pytest.raises(ValueError, match="REFERENCE_GEOMETRY"):
        construct_miter_polygon(35, -1, (4, 4), (8, 8))
    with pytest.raises(ValueError, match="POLYGON_INVALID"):
        construct_miter_polygon(35, 0, (0, 4), (8, 8))
    with pytest.raises(ValueError, match="TRANSITION_GEOMETRY"):
        construct_miter_polygon(35, 0, (1e-12, 1e-12), (8, 8))
