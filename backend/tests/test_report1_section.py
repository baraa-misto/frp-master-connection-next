"""Physical bolt-axis figure selection and incomplete native stack guards."""

from __future__ import annotations

from typing import Any

import pytest
from reportlab.graphics.shapes import String

from frp_master_connection.reporting.section import native_bolt_sections


def _visual(bolt: object, *, thickness: object = None) -> dict[str, Any]:
    layer = {"layer_id": "L1", "thickness": thickness or {"value": "1", "unit": "in"}}
    return {"visualization": {"layers": [layer], "physical_bolts": [bolt]}}


@pytest.mark.parametrize(
    "bolt",
    [
        "invalid",
        {"bolt_id": "B1"},
        {"bolt_id": "B1", "display": {}, "penetrated_layer_ids": []},
        {"bolt_id": "B1", "display": {}, "penetrated_layer_ids": ["L2"]},
        {"bolt_id": "B1", "display": {"holes": "invalid"}, "penetrated_layer_ids": ["L1"]},
    ],
)
def test_incomplete_native_stack_cannot_be_drawn_as_a_valid_section(bolt: object) -> None:
    assert native_bolt_sections(_visual(bolt)) == []


def test_missing_native_layer_thickness_cannot_be_drawn() -> None:
    bolt = {"bolt_id": "B1", "display": {}, "penetrated_layer_ids": ["L1"]}
    assert native_bolt_sections(_visual(bolt, thickness="not a quantity")) == []


@pytest.mark.parametrize(
    ("holes", "washers", "expected"),
    [
        ([{"diameter": "0.56"}], [{}], "Native washer records: 1"),
        ([], [], "No washer record supplied"),
    ],
)
def test_native_section_reports_actual_holes_and_washer_presence(
    holes: list[dict[str, str]], washers: list[dict[str, str]], expected: str
) -> None:
    bolt = {
        "bolt_id": "B1",
        "penetrated_layer_ids": ["L1"],
        "display": {
            "bolt_group_id": "G1",
            "bolt_diameter": "0.5",
            "holes": holes,
            "washers": washers,
        },
    }
    sections = native_bolt_sections(_visual(bolt))
    assert len(sections) == 1
    identity, figure = sections[0]
    assert identity == "G1 / B1"
    labels = [shape.text for shape in figure.contents if isinstance(shape, String)]
    assert any(expected in label for label in labels)
    assert any("Physical hole diameters" in label for label in labels) == bool(holes)
