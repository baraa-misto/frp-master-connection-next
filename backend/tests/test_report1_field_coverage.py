"""Every actual family request field must have a printable REPORT1 schedule path."""

from __future__ import annotations

from typing import Any

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.reporting.flatten import flatten_unique
from frp_master_connection.reporting.generic import _native_box_unit
from frp_master_connection.reporting.pdf import ReportingCoverageError
from frp_master_connection.reporting.units import DisplayUnits
from tests.api.test_connector_materials import native_payload


def _leaves(value: Any, path: str) -> list[tuple[str, object]]:  # noqa: ANN401
    if isinstance(value, dict):
        return [leaf for key, child in value.items() for leaf in _leaves(child, f"{path}.{key}")]
    if isinstance(value, list):
        return [
            leaf for index, child in enumerate(value) for leaf in _leaves(child, f"{path}[{index}]")
        ]
    return [(path, value)]


@pytest.mark.parametrize("family", tuple(FAMILIES))
def test_every_native_family_request_leaf_has_a_printed_or_aliased_path(family: str) -> None:
    request = native_payload(family)
    rows = flatten_unique("request", request, minimum_alias_leaves=1)
    assert rows
    for leaf_path, value in _leaves(request, "request"):
        matches = [
            (path, printed)
            for path, printed in rows
            if leaf_path == path or leaf_path.startswith((f"{path}.", f"{path}["))
        ]
        assert matches, f"{family}: missing report field {leaf_path}"
        assert any(
            str(value) in printed
            or printed.startswith("Identical native record at ")
            or (value is None and printed == "Not supplied")
            or (isinstance(value, bool) and printed in {"Yes", "No"})
            for _, printed in matches
        ), f"{family}: report field has no native value {leaf_path}"


def test_nested_native_geometry_design_and_visual_survive_complete_schedule() -> None:
    native = {
        "preview": {
            "geometry": {"actual_hole_diameter": {"value": "14.3", "unit": "mm"}},
            "interface": {
                "design": {"check_id": "B-1", "design_resistance": {"value": "4.7", "unit": "kip"}}
            },
            "visualization": {"display_only": True},
        }
    }
    rows = dict(flatten_unique("result", native, minimum_alias_leaves=1))
    assert rows["result.preview.geometry.actual_hole_diameter"] == "14.3 mm"
    assert rows["result.preview.interface.design.design_resistance"] == "4.7 kip"
    assert rows["result.preview.visualization.display_only"] == "Yes"


@pytest.mark.parametrize(
    ("system", "equivalent"),
    [("US_CUSTOMARY", "1 in"), ("SI", "25.4 mm")],
)
def test_quantity_schedule_retains_native_and_selected_equivalent_units(
    system: DisplayUnits, equivalent: str
) -> None:
    quantity = {"value": "25.4", "unit": "mm"}
    if system == "SI":
        quantity = {"value": "1", "unit": "in"}
    rows = flatten_unique("dimension", quantity, display_units=system)
    assert len(rows) == 1
    assert equivalent in rows[0][1]
    assert f"{system} equivalent" in rows[0][1]


def test_figure_dimension_unit_requires_uniform_native_box_coordinates() -> None:
    visual = {
        "parts": [
            {
                "box": {
                    "center_l_v_t": {"l": {"value": "1", "unit": "in"}},
                    "size_l_v_t": {"l": {"value": "2", "unit": "in"}},
                }
            }
        ]
    }
    assert _native_box_unit(visual) == "in"
    visual["parts"].append(
        {
            "box": {
                "center_l_v_t": {"l": {"value": "25.4", "unit": "mm"}},
                "size_l_v_t": {"l": {"value": "50.8", "unit": "mm"}},
            }
        }
    )
    with pytest.raises(ReportingCoverageError, match="mixed length units"):
        _native_box_unit(visual)
