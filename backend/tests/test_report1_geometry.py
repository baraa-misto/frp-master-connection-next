"""Native geometry figure adapters reject malformed or duplicated source shapes."""

from __future__ import annotations

from typing import Any

import pytest

from frp_master_connection.reporting.geometry import (
    canonical_boxes,
    canonical_faces,
    canonical_visual,
)


def test_fractional_native_box_coordinate_is_projected_without_rounding() -> None:
    boxes = canonical_boxes(
        {
            "part": {
                "component_id": "P1",
                "center_l_v_t": {"l": "1/2", "v": "0", "t": "0"},
                "size_l_v_t": {"l": "1", "v": "2", "t": "3"},
            }
        }
    )
    assert len(boxes) == 1
    assert {vertex[0] for vertex in boxes[0].vertices} == {0.0, 1.0}


def test_incomplete_basis_box_is_not_drawn_as_physical_geometry() -> None:
    visual = {
        "center": ["0", "0"],
        "size_s": "1",
        "size_p": "2",
        "size_l": "3",
        "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }
    assert canonical_boxes(visual) == []


def test_identical_native_extrusion_is_drawn_once() -> None:
    def xyz(x: str, y: str, z: str) -> dict[str, str]:
        return {"x": x, "y": y, "z": z}

    extrusion = {
        "extent": {"x_start": "0", "x_end": "2"},
        "rectangle": {"min_y": "0", "max_y": "1", "min_z": "0", "max_z": "1"},
    }
    visual = {
        "global_frame": {
            "origin": xyz("0", "0", "0"),
            "x_axis": xyz("1", "0", "0"),
            "y_axis": xyz("0", "1", "0"),
            "z_axis": xyz("0", "0", "1"),
        },
        "extrusions": [extrusion, extrusion],
        "source_element": {"id": "member"},
    }
    boxes = canonical_boxes(visual)
    assert len(boxes) == 1
    assert boxes[0].identity == "member"


@pytest.mark.parametrize(
    "visual",
    [
        {"members": "invalid"},
        {"members": ["invalid"]},
        {"members": [{"trimmed": {"solids": [{"faces": [{"vertices": [{"x": 0}]}]}]}}]},
    ],
)
def test_invalid_native_faces_are_not_drawn(visual: dict[str, Any]) -> None:
    assert canonical_faces(visual) == []


@pytest.mark.parametrize(
    "response",
    [
        {"client_design": []},
        {"client_design": {"result": []}},
        {"client_design": {"result": {"preview": []}}},
    ],
)
def test_invalid_native_visual_wrapper_has_no_figure(response: dict[str, Any]) -> None:
    assert canonical_visual(response) is None
