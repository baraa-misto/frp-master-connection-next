"""Wire samples are runtime regression data, not new engineering authority/goldens."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.config import ApplicationEnvironment, AppSettings

ROOT = Path(__file__).resolve().parents[2]
WIRE = json.loads(
    (ROOT / "frontend/tests/fixtures/channelMomentSpliceWire.json").read_text(encoding="utf-8")
)
PREVIEW = "/api/v1/calculations/channel-major-axis-moment-splice/preview"
DESIGN = "/api/v1/calculations/channel-major-axis-moment-splice/design-check"


def assert_wire_subset(expected: object, actual: object) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        assert expected.keys() <= actual.keys()
        for key, value in expected.items():
            assert_wire_subset(value, actual[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(expected) == len(actual)
        for expected_item, actual_item in zip(expected, actual, strict=True):
            assert_wire_subset(expected_item, actual_item)
    else:
        assert expected == actual


def post(path: str, payload: dict[str, Any]) -> httpx.Response:
    async def send() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


@pytest.mark.parametrize("system", ["US_CUSTOMARY", "SI"])
def test_browser_wire_fixture_is_an_exact_projection_of_real_preview(system: str) -> None:
    fixture = WIRE[system]
    response = post(PREVIEW, fixture["request"])
    assert response.status_code == 200
    assert_wire_subset(fixture["response"], response.json())
    assert response.content == post(PREVIEW, fixture["request"]).content
    result = response.json()["result"]
    visualization = result["visualization"]
    assert "shear_center_l_v_t" not in visualization
    assert (
        visualization["channel_shear_center_l_v_t"]["t"]["canonical_value"]
        == (result["slice6_result"]["shear_center"]["absolute_coordinate_t"]["canonical_value"])
    )
    assert result["equilibrium"]["whole_connection_six_component_exact"]
    assert result["equilibrium"]["beam_a_b_equal_opposite_complete_wrenches"]
    assert len(visualization["boxes"]) == 12
    assert len(visualization["bolts"]) == 24
    assert all(len(bolt["path_layers"]) == 3 for bolt in visualization["bolts"])
    if system == "US_CUSTOMARY":
        assert result["web_faces"]["back_major_shear"]["value"] == "-19.0625"
        assert result["web_faces"]["opening_major_shear"]["value"] == "9.0625"


def test_invalid_geometry_and_source_pending_remain_controlled_not_runtime_failures() -> None:
    request = WIRE["US_CUSTOMARY"]["request"]
    invalid = {**request, "beam_end_gap": {"value": "100", "unit": "in"}}
    response = post(PREVIEW, invalid)
    assert response.status_code == 200
    assert response.json()["geometry_status"] == "INVALID_GEOMETRY"
    assert response.json()["design_check_ready"] is False
    design = post(DESIGN, request)
    assert design.status_code == 200
    assert design.json()["assembly_status"] == "FAIL"
    assert design.json()["ordinary_pass_allowed"] is False
    assert design.json()["unavailable_check_ids"]
    assert "channel_shear_center_l_v_t" in design.json()["result"]["preview"]["visualization"]
