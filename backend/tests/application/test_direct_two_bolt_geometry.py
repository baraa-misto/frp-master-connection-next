"""Numerical geometry controls; these tests confer no structural or fabrication approval."""

from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from frp_master_connection.application.direct_two_bolt_geometry import (
    ONE,
    ZERO,
    bounded_regions,
    evaluate_pair,
    fit_state,
)
from tests.direct_sab2_fixtures import controls, study_pair


@pytest.mark.parametrize("row", controls(), ids=lambda row: row["expected"]["case_id"])
def test_all_118_same_source_study_controls(row: dict[str, object]) -> None:
    pair = study_pair(row)
    result = evaluate_pair(pair)
    expected = row["expected"]
    assert isinstance(expected, dict)
    # Exact same mathematical input and Decimal precision: no numerical waiver.
    holes = min(m.value for m in result.margins if m.role in {"HOLE", "SHAFT"})
    washers = min(m.value for m in result.margins if m.role == "WASHER")
    assert holes == Decimal(str(expected["minimum_hole_margin"]))
    assert washers == Decimal(str(expected["minimum_washer_margin"]))
    assert result.pair_polar_sum == Decimal(str(expected["pair_polar_sum"]))
    assert (
        fit_state(tuple(m.value for m in result.margins if m.role in {"HOLE", "SHAFT"}))
        == expected["hole_containment_and_unintended_web_path"]
    )
    assert result.washer_state == expected["circular_washer_seating"]
    assert result.obstruction_state == expected["known_obstruction_clearance"]


@pytest.mark.parametrize("alignment", ["SUPPORT", "BRACE"])
def test_coupled_regions_keep_split_outstand_assignments(alignment: str) -> None:
    row = next(
        r
        for r in controls()
        if r["input"]["pattern"] == alignment
        and r["input"]["theta"] == "30.9"
        and r["input"]["pitch"] == "2.25"
        and r["input"]["id"].startswith("D2 nominal")
    )
    pair = study_pair(row)
    with localcontext() as context:
        context.prec = 64
        regions = bounded_regions(
            pair,
            ((ONE, ZERO, ZERO), (ZERO, ZERO, ONE)),
            (Decimal(-1), Decimal(1), Decimal(-1), Decimal(1)),
        )
    assert regions
    if alignment == "BRACE":
        assert any(r.assigned_strips[0] != r.assigned_strips[1] for r in regions)
    for region in regions:
        midpoint = (
            pair.midpoint[0] + region.proposed_offset[0],
            ZERO,
            pair.midpoint[2] + region.proposed_offset[1],
        )
        proposed = evaluate_pair(replace(pair, midpoint=midpoint))
        assert proposed.washer_state != "DOES_NOT_FIT"
    assert pair.midpoint == (Decimal(3), ZERO, ZERO)
