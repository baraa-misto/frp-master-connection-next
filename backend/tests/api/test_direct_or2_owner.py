"""OR2 owner geometry, source-pending execution, and strict run boundaries."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body, owner_request

PREVIEW = "/api/v1/calculations/multi-row/preview"
DESIGN = "/api/v1/frp-materials/multi-row/design-check"


@pytest.mark.parametrize("si", [False, True])
def test_owner_all_physical_bolts_holes_washers_and_faces_are_valid(si: bool) -> None:
    payload = owner_request(si=si)
    response = call("POST", PREVIEW, payload)
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["geometry_status"] == "VALID"
    assert preview["design_check_ready"] is True
    assert not any("CONTAINMENT" in item for item in preview["warnings"])
    visual = preview["visualization"]
    scale = Decimal("25.4") if si else Decimal(1)
    assert len(visual["physical_bolts"]) == 2
    centers = []
    for bolt in visual["physical_bolts"]:
        assert bolt["penetrated_layer_ids"] == ["layer-A", "layer-B"]
        display = bolt["display"]
        centers.append(display["center"])
        assert Decimal(display["bolt_diameter"]) == Decimal(".5") * scale
        assert {hole["physical_element_id"] for hole in display["holes"]} == {"LEG_1", "TOP_FLANGE"}
        assert len(display["holes"]) == 2
        assert all(
            Decimal(hole["diameter"]) == Decimal(".563") * scale for hole in display["holes"]
        )
        assert len(display["washers"]) == 2
        for washer in display["washers"]:
            assert Decimal(washer["outside_diameter"]) == scale
            thickness = abs(Decimal(washer["end"]["x"]) - Decimal(washer["start"]["x"]))
            assert abs(thickness - Decimal(".051") * scale) < Decimal("1e-12")
    distance_squared = sum(
        ((Decimal(centers[1][axis]) - Decimal(centers[0][axis])) ** 2 for axis in ("x", "y", "z")),
        Decimal(0),
    )
    assert abs(distance_squared.sqrt() - 2 * scale) < Decimal("1e-12")
    for name, value in [
        ("pitch", "2"),
        ("unloaded_end_e1", "3"),
        ("loaded_boundary_to_row_1_distance", "3"),
        ("negative_side_distance", "1"),
        ("positive_side_distance", "1"),
    ]:
        assert Decimal(visual[name]["value"]) == Decimal(value) * scale


@pytest.mark.parametrize("exposure", [None, "moisture", "chemical"])
def test_owner_source_pending_keeps_final_bearing_and_interrow_checks(exposure: str | None) -> None:
    body = owner_body()
    if exposure is not None:
        body["assignments"]["default_conditions"][exposure] = "UNKNOWN"
    response = call("POST", DESIGN, body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["design_check_performed"] is True
    assert result["overall_status"] == "SOURCE_REQUIRED"
    native = result["native_design"]
    integration = native["automatic_group_mode_integration"]
    checks = [
        check
        for scenario in integration["scenario_results"]
        for check in scenario["supported_results"]
    ]
    assert len(checks) == 6
    assert sum(check["limit_state"] == "PIN_BEARING" for check in checks) == 4
    assert sum("INTERROW" in check["result_id"] for check in checks) == 2
    assert all(check["availability"] == "CALCULATED" for check in checks)
    assert any("FIRST_ROW" in item for item in integration["unsupported_required_check_ids"])
    assert any("BLOCK_SHEAR" in item for item in integration["unsupported_required_check_ids"])
    assert integration["incomplete_required_check_ids"]
    assert result["fastener_source"]["fnt"] is None
    if exposure:
        assert any(
            item["adjusted_candidate"] is None and "strength" in item["property_id"]
            for item in result["material_ledgers"]
        )


@pytest.mark.parametrize(
    "field",
    ["sustained_temperature", "maximum_temperature", "time_effect_category", "load_case_name"],
)
def test_missing_basic_conditions_reject_before_design(field: str) -> None:
    body = owner_body()
    conditions = body["assignments"]["default_conditions"]
    if "temperature" in field:
        conditions[field]["value"] = ""
    else:
        conditions[field] = ""
    assert call("POST", DESIGN, body).status_code == 422


@pytest.mark.parametrize("case", ["geometry", "moment", "bolt-axis"])
def test_actual_run_boundaries_remain_closed(case: str) -> None:
    payload = owner_request()
    action = payload["physical_connection"]["joint_assembly"]["member_end_actions"][0]
    if case == "geometry":
        payload["unloaded_end_e1"]["value"] = "6"
        payload["physical_connection"]["geometry_template"]["bolt_to_brace_end_distance"][
            "value"
        ] = "6"
    elif case == "moment":
        action["moment"]["z"] = "1"
    else:
        action["coordinate_frame_kind"] = "BOLT_GROUP_LOCAL"
        action["coordinate_frame_owner_id"] = "bolt-group-1"
        action["force"]["z"] = "1"
    preview = call("POST", PREVIEW, payload).json()
    assert preview["design_check_ready"] is False
    assert preview["warnings"]


def test_owner_one_row_fail_outranks_source_requirements() -> None:
    body = owner_body(one_row=True)
    response = call("POST", DESIGN, body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["overall_status"] == "FAIL"
    single = result["native_design"]["automatic_group_mode_integration"]["direct_single_row_result"]
    assert single["failed_check_ids"]
    assert single["incomplete_required_check_ids"]
    assert any(
        check["limit_state"] == "SINGLE_ROW_NET_TENSION" and check["numerical_comparison"] == "FAIL"
        for check in single["checks"]
    )


def test_only_reviewed_angle_w_surface_is_advertised() -> None:
    response = call("GET", "/api/v1/workspaces/direct-shapes")
    assert response.status_code == 200
    body = response.json()
    assert len(body["enabled"]) == 1
    assert body["enabled"][0] == {
        "state": "ENABLED",
        "brace_shape": "ANGLE",
        "support_shape": "WIDE_FLANGE",
        "brace_element": "LEG_1",
        "support_element": "TOP_FLANGE",
        "support_face": "EXTERIOR",
        "lap": "SINGLE_LAP",
        "physical_frp_layers": 2,
    }


def test_si_native_utilizations_are_same_physical_design() -> None:
    results: list[dict[str, Any]] = []
    for si in (False, True):
        response = call("POST", DESIGN, owner_body(si=si))
        assert response.status_code == 200, response.text
        results.append(
            deepcopy(response.json()["native_design"]["automatic_group_mode_integration"])
        )
    for index in range(2):
        left = results[0]["scenario_results"][index]["supported_results"]
        right = results[1]["scenario_results"][index]["supported_results"]
        assert len(left) == len(right) == 3
        for us, metric in zip(left, right, strict=True):
            assert us["result_id"] == metric["result_id"]
            assert abs(Decimal(us["utilization"]) - Decimal(metric["utilization"])) < Decimal(
                "1e-15"
            )
    for si in (False, True):
        native = call("POST", DESIGN, owner_body(si=si)).json()["native_design"]
        assert "DIRECT-AXIAL-FRAME-CANONICALIZATION-OR2-F1" in str(native)
