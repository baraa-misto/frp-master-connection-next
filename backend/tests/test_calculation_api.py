"""Stage 2.2B mapper, HTTP, serialization, OpenAPI, and security contracts."""

from __future__ import annotations

import asyncio
import copy
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import Enum
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from fastapi import FastAPI

import frp_master_connection.api.routes as routes_module
from frp_master_connection.api import calculation_mapping
from frp_master_connection.api.app import create_app
from frp_master_connection.api.calculation_mapping import (
    map_single_bolt_request,
    serialize_single_bolt_response,
)
from frp_master_connection.api.schemas import (
    API_TRANSPORT_SCHEMA_VERSION,
    QuantityDTO,
    SingleBoltEvaluationRequestDTO,
)
from frp_master_connection.application import (
    BraceToColumnOrientationContext,
    SingleBoltOrchestrationRequest,
    build_single_bolt_visualization_snapshot,
    evaluate_single_bolt_connection,
)
from frp_master_connection.calculation import KIP_TO_KN, Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import EngineeringUnitSystem
from frp_master_connection.geometry import (
    DIMENSIONLESS_MATHEMATICAL_TOLERANCE,
    PlacedPhysicalElement3D,
)
from frp_master_connection.security import TrustedIdentity
from tests.api_fixtures import (
    build_api_payload,
    build_j1_template_api_payload,
    build_j1_visual_api_payload,
)
from tests.application.orchestration_fixtures import build_plate_case


def test_r5_semantic_angle_trigonometry_is_deterministic_without_libm() -> None:
    diagonal = float.fromhex("0x1.6a09e667f3bcdp-1")
    assert calculation_mapping._deterministic_sine_cosine_degrees(Decimal(45)) == (
        diagonal,
        diagonal,
    )
    assert calculation_mapping._deterministic_sine_cosine_degrees(Decimal(135)) == (
        diagonal,
        -float.fromhex("0x1.6a09e667f3bccp-1"),
    )
    assert calculation_mapping._deterministic_sine_cosine_degrees(Decimal(30)) == (
        float.fromhex("0x1.fffffffffffffp-2"),
        float.fromhex("0x1.bb67ae8584cabp-1"),
    )


ROUTE = "/api/v1/calculations/single-bolt/evaluate"


@dataclass(slots=True)
class CountingIdentityResolver:
    production_capable: bool = True
    calls: int = 0

    async def resolve(self) -> TrustedIdentity:
        self.calls += 1
        return TrustedIdentity("api-test-account", None, frozenset({"tester"}), "test")


def _application(resolver: CountingIdentityResolver | None = None) -> FastAPI:
    return create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )


def _post(
    payload: dict[str, object],
    *,
    application: FastAPI | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        selected = _application() if application is None else application
        transport = httpx.ASGITransport(app=selected)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(ROUTE, json=payload)

    return asyncio.run(send())


def _result(
    body: dict[str, object],
    limit_state: str,
    layer_id: str | None,
) -> dict[str, object]:
    results = cast(list[dict[str, object]], body["results"])
    return next(
        item
        for item in results
        if cast(dict[str, object], item["plan"])["limit_state"] == limit_state
        and cast(dict[str, object], item["plan"])["layer_id"] == layer_id
    )


def _no_float(value: object) -> bool:
    if isinstance(value, float):
        return False
    if isinstance(value, dict):
        return all(_no_float(item) for item in value.values())
    if isinstance(value, list):
        return all(_no_float(item) for item in value)
    return True


def _within_dimensionless_geometry_tolerance(value: str, expected: float) -> bool:
    return math.isclose(
        float(value),
        expected,
        rel_tol=0.0,
        abs_tol=DIMENSIONLESS_MATHEMATICAL_TOLERANCE,
    )


_SERIALIZED_POSITION_COMPONENTS = ("x", "y", "z")
_SERIALIZED_POSITION_KEYS = {*_SERIALIZED_POSITION_COMPONENTS, "unit"}
_SERIALIZED_POSITION_ROUNDOFF_MULTIPLIER = 16.0
_J1_TEMPLATE_BOLT_CENTER_US = {
    "x": "-0.5",
    "y": "-1.1566310409006175",
    "z": "1.6717960838455723",
    "unit": "in",
}


def _assert_serialized_position_within_float_roundoff(
    actual: object,
    expected: dict[str, str],
) -> None:
    """Compare cross-platform finite-float serialization in tests only.

    This is not a dimensional engineering, geometry, or fabrication tolerance.
    """

    assert isinstance(actual, dict)
    assert set(actual) == set(expected) == _SERIALIZED_POSITION_KEYS
    assert actual["unit"] == expected["unit"]

    actual_values: dict[str, float] = {}
    expected_values: dict[str, float] = {}
    for component in _SERIALIZED_POSITION_COMPONENTS:
        actual_text = actual[component]
        expected_text = expected[component]
        assert isinstance(actual_text, str)
        actual_values[component] = float(actual_text)
        expected_values[component] = float(expected_text)
        assert math.isfinite(actual_values[component])
        assert math.isfinite(expected_values[component])

    scale = max(
        1.0,
        *(abs(value) for value in (*actual_values.values(), *expected_values.values())),
    )
    roundoff_limit = _SERIALIZED_POSITION_ROUNDOFF_MULTIPLIER * sys.float_info.epsilon * scale
    for component in _SERIALIZED_POSITION_COMPONENTS:
        assert abs(actual_values[component] - expected_values[component]) <= roundoff_limit


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", True),
        ("0.00000000000000001839226599442302", True),
        ("-0.00000000000000001839226599442302", True),
        ("0.00000000001", False),
        ("-0.00000000001", False),
    ],
)
def test_dimensionless_geometry_comparison_uses_the_governed_tolerance(
    value: str,
    expected: bool,
) -> None:
    assert _within_dimensionless_geometry_tolerance(value, 0.0) is expected


def test_serialized_position_roundoff_comparison_is_platform_neutral_and_narrow() -> None:
    expected = {
        "x": "0",
        "y": "-1.1566310490966173",
        "z": "1.67179608345572",
        "unit": "in",
    }
    ubuntu = {
        "x": "0",
        "y": "-1.1566310490966175",
        "z": "1.671796083455723",
        "unit": "in",
    }

    _assert_serialized_position_within_float_roundoff(expected, expected)
    _assert_serialized_position_within_float_roundoff(ubuntu, expected)

    materially_shifted = {**ubuntu, "z": "1.671796083456723"}
    with pytest.raises(AssertionError):
        _assert_serialized_position_within_float_roundoff(materially_shifted, expected)
    with pytest.raises(AssertionError):
        _assert_serialized_position_within_float_roundoff({**ubuntu, "unit": "mm"}, expected)
    with pytest.raises(AssertionError):
        _assert_serialized_position_within_float_roundoff({**ubuntu, "extra": "0"}, expected)
    with pytest.raises(AssertionError):
        _assert_serialized_position_within_float_roundoff({**ubuntu, "z": "NaN"}, expected)


def test_template_transport_requires_exactly_one_strict_geometry_source() -> None:
    neither = build_j1_template_api_payload()
    neither.pop("geometry_template")
    assert _post(neither).status_code == 422

    both = build_j1_template_api_payload()
    both["geometry"] = build_j1_visual_api_payload()["geometry"]
    assert _post(both).status_code == 422

    extra = build_j1_template_api_payload()
    cast(dict[str, object], extra["geometry_template"])["unexpected"] = "rejected"
    assert _post(extra).status_code == 422


def test_template_mapper_rejects_wrong_shape_identity_ids_and_lengths() -> None:
    explicit = SingleBoltEvaluationRequestDTO.model_validate(build_j1_visual_api_payload())
    with pytest.raises(ValueError, match="template geometry is required"):
        calculation_mapping._brace_to_column_template_geometry(explicit, Unit.IN)

    wrong_member = build_j1_template_api_payload()
    members = cast(
        list[dict[str, object]],
        cast(dict[str, object], wrong_member["joint_assembly"])["members"],
    )
    members[0]["id"] = "wrong-member"
    response = _post(wrong_member)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_MAPPING_INVALID"

    wrong_kind = build_j1_template_api_payload()
    members = cast(
        list[dict[str, object]],
        cast(dict[str, object], wrong_kind["joint_assembly"])["members"],
    )
    members[1]["section"] = copy.deepcopy(members[0]["section"])
    assert _post(wrong_kind).status_code == 422

    wrong_ids = build_j1_template_api_payload()
    wrong_ids["interface_id"] = "other-interface"
    assert _post(wrong_ids).status_code == 422

    nonpositive = build_j1_template_api_payload()
    template = cast(dict[str, object], nonpositive["geometry_template"])
    cast(dict[str, object], template["bolt_to_brace_end_distance"])["value"] = "0"
    assert _post(nonpositive).status_code == 422


def test_decimal_transport_is_exact_strict_and_finite() -> None:
    assert QuantityDTO(value="12.700", unit=Unit.MM).value == "12.700"
    for value in (12.7, True, "NaN", "Infinity", "-Infinity", "not-a-decimal"):
        with pytest.raises(ValueError, match=r"."):
            QuantityDTO(value=value, unit="mm")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"."):
        QuantityDTO(value="1", unit="feet")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("mutation", "expected_location"),
    [
        (lambda payload: payload.update({"trusted_identity": "spoof"}), "trusted_identity"),
        (
            lambda payload: payload.update({"calculation_fingerprint": "0" * 64}),
            "calculation_fingerprint",
        ),
        (lambda payload: payload.update({"result": "PASS"}), "result"),
        (
            lambda payload: cast(dict[str, object], payload["bolt_diameter"]).__setitem__(
                "value", 0.5
            ),
            "value",
        ),
        (
            lambda payload: cast(dict[str, object], payload["bolt_diameter"]).__setitem__(
                "value", "NaN"
            ),
            "value",
        ),
        (
            lambda payload: cast(dict[str, object], payload["bolt_diameter"]).__setitem__(
                "unit", "feet"
            ),
            "unit",
        ),
        (lambda payload: payload.pop("joint_assembly"), "joint_assembly"),
        (lambda payload: payload.update({"lap_configuration": "TRIPLE_LAP"}), "lap_configuration"),
    ],
)
def test_malformed_or_spoofed_transport_is_422(
    mutation: Callable[[dict[str, object]], object],
    expected_location: str,
) -> None:
    payload = build_api_payload("P1")
    mutation(payload)
    response = _post(payload)
    assert response.status_code == 422
    assert expected_location in response.text


def test_mapper_rebuilds_actual_canonical_objects_and_preserves_p1_result() -> None:
    dto = SingleBoltEvaluationRequestDTO.model_validate(build_api_payload("P1"))
    mapped = map_single_bolt_request(dto)
    direct = build_plate_case("P1").request
    assert isinstance(mapped, SingleBoltOrchestrationRequest)
    assert mapped.assembly is mapped.geometry_context.assembly
    assert (
        mapped.geometry_context.basis.resolved_interfaces[0].interface
        is mapped.assembly.interfaces[0]
    )
    assert (
        mapped.geometry_context.resolved_bolt_groups[0].bolt_group is mapped.assembly.bolt_groups[0]
    )
    assert (
        mapped.material_assignments[0].material_snapshot
        == direct.material_assignments[0].material_snapshot
    )
    assert mapped.fastener_snapshot == direct.fastener_snapshot
    assert mapped.resolved_demand == direct.resolved_demand
    assert evaluate_single_bolt_connection(mapped) == evaluate_single_bolt_connection(direct)


def test_mapper_preserves_p2a_order_angle_w_topology_and_no_demand_action() -> None:
    p2a = map_single_bolt_request(
        SingleBoltEvaluationRequestDTO.model_validate(build_api_payload("P2A"))
    )
    assert tuple(
        item.definition.id for item in p2a.geometry_context.resolved_bolt_groups[0].paths[0].layers
    ) == ("layer-A", "layer-B")
    j1 = map_single_bolt_request(
        SingleBoltEvaluationRequestDTO.model_validate(build_api_payload("J1-T"))
    )
    assert tuple(member.section_family.value for member in j1.assembly.members) == (
        "ANGLE",
        "WIDE_FLANGE",
    )
    assert tuple(
        item.definition.physical_element_id
        for item in j1.geometry_context.resolved_bolt_groups[0].paths[0].layers
    ) == ("LEG_1", "TOP_FLANGE")
    no_demand = map_single_bolt_request(
        SingleBoltEvaluationRequestDTO.model_validate(
            build_api_payload("J1-T", explicit_demand=False)
        )
    )
    assert no_demand.resolved_demand is None
    assert no_demand.source_action_id == "action-1"


def test_p1_http_is_deterministic_review_required_and_preserves_q12_values() -> None:
    payload = build_api_payload("P1")
    first = _post(payload)
    second = _post(payload)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    body = first.json()
    assert body["api_transport_schema_version"] == API_TRANSPORT_SCHEMA_VERSION
    assert body["calculation_engine_version"] == "0.1.0.dev1"
    assert body["engineering_rule_set_version"] == "asce74-23-ch8-single-bolt-rc2.dev1"
    assert body["aggregate_status"] == "ENGINEERING_REVIEW_REQUIRED"
    assert body["governing_check_ids"] == [
        "interface-1:bolt-1:layer-A:pin_bearing",
        "interface-1:bolt-1:layer-A:cleavage",
    ]
    bearing = _result(body, "PIN_BEARING", "layer-A")
    assert bearing["numerical_comparison"] == "PASS"
    assert cast(dict[str, str], bearing["design_resistance"])["value"] == "3.375"
    assert Decimal(cast(str, bearing["utilization"])).quantize(
        Decimal("0.000000000001")
    ) == Decimal("0.888888888889")
    assert "ASCE/SEI 74-23" in {item["standard_id"] for item in body["source_references"]}
    assert "Copyright" not in first.text


def test_p2b_engineering_fail_and_unsupported_are_http_200() -> None:
    response = _post(build_api_payload("P2B"))
    body = response.json()
    assert response.status_code == 200
    assert body["aggregate_status"] == "FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK"
    assert _result(body, "PIN_BEARING", "layer-B")["numerical_comparison"] == "FAIL"
    assert _result(body, "NET_SECTION_TENSION", "layer-B")["numerical_comparison"] == "FAIL"
    assert _result(body, "SHEAR_OUT", "layer-B")["numerical_comparison"] == "PASS"
    assert _result(body, "CLEAVAGE", "layer-B")["availability"] == "CALCULATION_NOT_SUPPORTED"


@pytest.mark.parametrize("fixture", ["J1-T", "J1-C"])
def test_j1_http_preserves_angle_w_direction_and_qualification(fixture: str) -> None:
    response = _post(build_api_payload(fixture))
    body = response.json()
    assert response.status_code == 200
    assert body["aggregate_status"] == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    assert [item["physical_element_id"] for item in body["resolved_layers"]] == [
        "LEG_1",
        "TOP_FLANGE",
    ]
    assert body["resolved_layers"][1]["code_mapping"]["direction_family"] == "TRANSVERSE"
    if fixture == "J1-T":
        assert body["governing_check_ids"] == ["interface-1:bolt-1:layer-B:net_tension"]
        assert _result(body, "CLEAVAGE", "layer-B")["availability"] == "CALCULATION_NOT_SUPPORTED"
    else:
        assert _result(body, "PIN_BEARING", "layer-B")["numerical_comparison"] == "PASS"
        assert _result(body, "SHEAR_OUT", "layer-B")["numerical_comparison"] == "PASS"
        assert _result(body, "NET_SECTION_TENSION", "layer-B")["availability"] == "NOT_APPLICABLE"


def test_stage_2_3r_j1_visual_api_case_keeps_results_and_exposes_vertical_column() -> None:
    historical = _post(build_api_payload("J1-T")).json()
    visual = _post(build_j1_visual_api_payload()).json()
    assert visual["aggregate_status"] == historical["aggregate_status"]
    assert visual["governing_check_ids"] == historical["governing_check_ids"]
    assert [item["numerical_comparison"] for item in visual["results"]] == [
        item["numerical_comparison"] for item in historical["results"]
    ]
    assert [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in visual["results"]
    ] == [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in historical["results"]
    ]
    frames = {
        item["owner_id"]: item
        for item in visual["visualization"]["frames"]
        if item["owner_id"] is not None
    }
    column_x = frames["member-b"]["frame"]["x_axis"]
    assert _within_dimensionless_geometry_tolerance(column_x["x"], 0.0)
    assert _within_dimensionless_geometry_tolerance(column_x["y"], 0.0)
    assert _within_dimensionless_geometry_tolerance(column_x["z"], 1.0)
    inspection = frames["member-b"]["inspection"]
    assert inspection["orthonormal"] is True
    assert inspection["right_handed"] is True
    assert _within_dimensionless_geometry_tolerance(inspection["x_norm"], 1.0)
    assert _within_dimensionless_geometry_tolerance(inspection["y_norm"], 1.0)
    assert _within_dimensionless_geometry_tolerance(inspection["z_norm"], 1.0)
    assert _within_dimensionless_geometry_tolerance(inspection["determinant"], 1.0)
    assert _within_dimensionless_geometry_tolerance(
        frames["member-a"]["frame"]["x_axis"]["z"],
        2**-0.5,
    )


def test_stage_2_3r3_template_preserves_default_j1_results_and_fixed_connection() -> None:
    historical = _post(build_api_payload("J1-T")).json()
    template = _post(build_j1_template_api_payload()).json()
    assert template["aggregate_status"] == historical["aggregate_status"]
    assert template["governing_check_ids"] == historical["governing_check_ids"]
    assert [item["numerical_comparison"] for item in template["results"]] == [
        item["numerical_comparison"] for item in historical["results"]
    ]
    assert [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in template["results"]
    ] == [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in historical["results"]
    ]
    frames = {
        item["owner_id"]: item
        for item in template["visualization"]["frames"]
        if item["owner_id"] is not None
    }
    column_x = frames["member-b"]["frame"]["x_axis"]
    assert set(column_x) == {"x", "y", "z"}
    assert _within_dimensionless_geometry_tolerance(column_x["x"], 0.0)
    assert _within_dimensionless_geometry_tolerance(column_x["y"], 0.0)
    assert _within_dimensionless_geometry_tolerance(column_x["z"], 1.0)
    column_primitives = [
        item
        for item in template["visualization"]["primitives"]
        if item["owner_id"] == "member-b" and item["kind"] == "BOX"
    ]
    lengths = {
        Decimal(next(p["value"] for p in item["parameters"] if p["name"] == "x_end"))
        - Decimal(next(p["value"] for p in item["parameters"] if p["name"] == "x_start"))
        for item in column_primitives
    }
    assert len(lengths) == 1
    assert float(next(iter(lengths))) == pytest.approx(10.242640687119285, abs=1e-12)
    bolt = template["visualization"]["bolt"]
    assert bolt["bolt_group_id"] == "bolt-group-1"
    assert bolt["bolt_location_id"] == "bolt-1"
    _assert_serialized_position_within_float_roundoff(
        bolt["center"],
        _J1_TEMPLATE_BOLT_CENTER_US,
    )


def test_engineering_e1_is_rederived_from_canonical_geometry_and_changes_design() -> None:
    baseline = _post(build_j1_template_api_payload(bolt_to_brace_end_distance="2")).json()
    changed = _post(build_j1_template_api_payload(bolt_to_brace_end_distance="2.5")).json()
    baseline_layer = next(
        item for item in baseline["resolved_layers"] if item["layer_id"] == "layer-A"
    )
    changed_layer = next(
        item for item in changed["resolved_layers"] if item["layer_id"] == "layer-A"
    )
    baseline_connected_end = next(
        item
        for item in baseline["visualization"]["reference_points"]
        if item["id"] == "member-a:start"
    )
    changed_connected_end = next(
        item
        for item in changed["visualization"]["reference_points"]
        if item["id"] == "member-a:start"
    )

    assert float(baseline_layer["code_mapping"]["forward_e1"]["value"]) == pytest.approx(
        2.0,
        abs=1e-12,
    )
    assert float(changed_layer["code_mapping"]["forward_e1"]["value"]) == pytest.approx(
        2.5,
        abs=1e-12,
    )
    for coordinate in ("x", "y", "z"):
        assert float(baseline["visualization"]["bolt"]["center"][coordinate]) == pytest.approx(
            float(changed["visualization"]["bolt"]["center"][coordinate]),
            abs=1e-12,
        )
    assert baseline_connected_end["position"] != changed_connected_end["position"]
    assert baseline["calculation_fingerprint"] != changed["calculation_fingerprint"]
    assert [item["nominal_resistance"] for item in baseline["results"]] != [
        item["nominal_resistance"] for item in changed["results"]
    ]
    assert baseline["governing_check_ids"] == changed["governing_check_ids"]


def test_stage_2_3r3_default_orientation_maps_exact_contact_faces_and_bolt_path() -> None:
    body = _post(build_j1_template_api_payload()).json()
    orientation = body["visualization"]["connection_orientation"]
    assert body["api_transport_schema_version"] == "0.5.0-draft"
    assert body["visualization"]["snapshot_version"] == "1.3.0-draft"
    assert orientation == {
        "connection_side": "EXTERIOR",
        "connected_leg": "LEG_1",
        "outstanding_leg_side": "POSITIVE_INTERFACE_Z",
        "supporting_member_id": "member-b",
        "selected_flange_element_id": "TOP_FLANGE",
        "selected_flange_surface_id": "TOP_FLANGE:OUTER_NEGATIVE_CW_STRIP",
        "selected_flange_surface_role": "POSITIVE_THICKNESS_FACE",
        "connected_member_id": "member-a",
        "selected_angle_surface_id": "LEG_1:EXTERIOR_TT_BROAD",
        "selected_angle_surface_role": "NEGATIVE_THICKNESS_FACE",
        "selected_contact_normal": {"x": "-1", "y": "0", "z": "0"},
        "brace_to_column_directed_angle_degrees": "45",
        "plan_angle_degrees": "0",
        "interference_classifications": [],
        "interference_participant_ids": [],
        "interference_physical_element_ids": [],
        "geometry_valid": True,
    }
    assert [item["physical_element_id"] for item in body["resolved_layers"]] == [
        "LEG_1",
        "TOP_FLANGE",
    ]
    assert all(
        frame["inspection"]["right_handed"] is True for frame in body["visualization"]["frames"]
    )


def test_stage_2_3r3_valid_web_side_uses_inner_face_and_excludes_web_from_path() -> None:
    body = _post(
        build_j1_template_api_payload(
            column_flange_connection_side="WEB_SIDE",
            angle_connected_leg="LEG_1",
            outstanding_leg_side="POSITIVE_INTERFACE_Z",
        )
    ).json()
    orientation = body["visualization"]["connection_orientation"]
    assert body["aggregate_status"] != "INVALID_GEOMETRY"
    assert orientation["geometry_valid"] is True
    assert orientation["selected_flange_surface_id"] == ("TOP_FLANGE:INNER_NEGATIVE_CW_STRIP")
    assert orientation["selected_flange_surface_role"] == "NEGATIVE_THICKNESS_FACE"
    assert [item["physical_element_id"] for item in body["resolved_layers"]] == [
        "LEG_1",
        "TOP_FLANGE",
    ]
    assert "WEB" not in {item["physical_element_id"] for item in body["resolved_layers"]}


def test_stage_2_3r3_unintended_interference_fails_closed_with_diagnostics() -> None:
    response = _post(build_j1_template_api_payload(outstanding_leg_side="NEGATIVE_INTERFACE_Z"))
    body = response.json()
    invalid = [item for item in body["issues"] if item["code"] == "INVALID_GEOMETRY"]
    orientation = body["visualization"]["connection_orientation"]
    assert response.status_code == 200
    assert body["aggregate_status"] == "INVALID_GEOMETRY"
    assert body["plans"] == []
    assert body["results"] == []
    assert body["governing_check_ids"] == []
    assert body["calculation_fingerprint"] is None
    assert invalid
    assert all("ANGLE_W_MEMBER_INTERFERENCE" in item["identities"] for item in invalid)
    assert orientation["geometry_valid"] is False
    assert orientation["interference_classifications"] == [
        "ANGLE_W_MEMBER_INTERFERENCE",
        "ANGLE_W_MEMBER_INTERFERENCE",
    ]


@pytest.mark.parametrize("angle", ["45", "60", "90", "120", "135", "150", "175"])
def test_stage_2_3r3_exterior_angle_regression_keeps_orientation_and_frames(
    angle: str,
) -> None:
    body = _post(build_j1_template_api_payload(angle_degrees=angle)).json()
    orientation = body["visualization"]["connection_orientation"]
    assert body["aggregate_status"] != "INVALID_GEOMETRY"
    assert orientation["connection_side"] == "EXTERIOR"
    assert orientation["connected_leg"] == "LEG_1"
    assert orientation["outstanding_leg_side"] == "POSITIVE_INTERFACE_Z"
    assert orientation["brace_to_column_directed_angle_degrees"] == angle
    member_frame = next(
        item for item in body["visualization"]["frames"] if item["owner_id"] == "member-a"
    )
    assert member_frame["inspection"]["right_handed"] is True
    assert float(member_frame["inspection"]["determinant"]) == pytest.approx(1.0)


def test_stage_2_3r3_orientation_inputs_are_strict_and_change_fingerprint() -> None:
    baseline_payload = build_j1_template_api_payload()
    missing = copy.deepcopy(baseline_payload)
    cast(dict[str, object], missing["geometry_template"]).pop("angle_connected_leg")
    assert _post(missing).status_code == 422
    extra = copy.deepcopy(baseline_payload)
    cast(dict[str, object], extra["geometry_template"])["derived_roll_degrees"] = "90"
    assert _post(extra).status_code == 422
    first = _post(baseline_payload).json()
    second = _post(build_j1_template_api_payload(angle_connected_leg="LEG_2")).json()
    assert first["calculation_fingerprint"] != second["calculation_fingerprint"]
    assert second["resolved_layers"][0]["physical_element_id"] == "LEG_2"


def test_stage_2_3r3_us_si_preserve_orientation_and_engineering_results() -> None:
    us = _post(build_j1_template_api_payload()).json()
    si = _post(build_j1_template_api_payload(unit_system=EngineeringUnitSystem.SI)).json()
    for field in ("connection_side", "connected_leg", "outstanding_leg_side"):
        assert (
            us["visualization"]["connection_orientation"][field]
            == (si["visualization"]["connection_orientation"][field])
        )
    assert us["aggregate_status"] == si["aggregate_status"]
    assert us["governing_check_ids"] == si["governing_check_ids"]
    assert [item["numerical_comparison"] for item in us["results"]] == [
        item["numerical_comparison"] for item in si["results"]
    ]


def test_stage_2_3r3_narrow_interference_helper_rejects_non_prismatic_elements() -> None:
    invalid = cast(PlacedPhysicalElement3D, SimpleNamespace(extrusions=()))
    with pytest.raises(ValueError, match="requires rectangular prisms"):
        calculation_mapping._rectangular_prism(invalid)


def test_stage_2_3r3_orientation_context_type_is_fail_closed() -> None:
    dto = SingleBoltEvaluationRequestDTO.model_validate(build_j1_template_api_payload())
    request = map_single_bolt_request(dto)
    with pytest.raises(TypeError, match="BraceToColumnOrientationContext"):
        replace(
            request,
            template_orientation=cast(BraceToColumnOrientationContext, object()),
        )


def test_stage_2_3r3_bolt_layer_rejects_same_signed_broad_faces() -> None:
    payload = build_api_payload("J1-T")
    geometry = cast(dict[str, object], payload["geometry"])
    bolt_group = cast(dict[str, object], geometry["bolt_group"])
    path = cast(list[dict[str, object]], bolt_group["paths"])[0]
    layer = cast(list[dict[str, object]], path["layers"])[1]
    layer["exit_patch_id"] = "TOP_FLANGE:INNER_POSITIVE_CW_STRIP"
    layer["exit_face_role"] = "NEGATIVE_THICKNESS_FACE"
    response = _post(payload)
    assert response.status_code == 422
    assert "opposing signed broad-face roles" in response.text


@pytest.mark.parametrize(
    ("angle", "expected_y", "expected_z", "expected_direction"),
    [
        ("90", -1.0, 0.0, "TRANSVERSE"),
        ("5", -0.0871557427476582, 0.9961946980917455, "LONGITUDINAL"),
    ],
)
def test_stage_2_3r2_template_resolves_90_and_near_longitudinal_geometry(
    angle: str,
    expected_y: float,
    expected_z: float,
    expected_direction: str,
) -> None:
    response = _post(build_j1_template_api_payload(angle_degrees=angle))
    assert response.status_code == 200
    body = response.json()
    frames = {
        item["owner_id"]: item
        for item in body["visualization"]["frames"]
        if item["owner_id"] is not None
    }
    brace_x = frames["member-a"]["frame"]["x_axis"]
    assert _within_dimensionless_geometry_tolerance(brace_x["y"], expected_y)
    assert _within_dimensionless_geometry_tolerance(brace_x["z"], expected_z)
    assert frames["member-a"]["inspection"]["orthonormal"] is True
    assert frames["member-a"]["inspection"]["right_handed"] is True
    _assert_serialized_position_within_float_roundoff(
        body["visualization"]["bolt"]["center"],
        _J1_TEMPLATE_BOLT_CENTER_US,
    )
    w_mapping = next(
        item["code_mapping"] for item in body["resolved_layers"] if item["layer_id"] == "layer-B"
    )
    assert float(w_mapping["theta_degrees"]) == pytest.approx(float(angle), abs=1e-12)
    assert w_mapping["direction_family"] == expected_direction


@pytest.mark.parametrize("angle", ["0", "-1", "180", "180.0001", "NaN", "Infinity", True])
def test_stage_2_3r2_template_rejects_invalid_angles(angle: object) -> None:
    payload = build_j1_template_api_payload()
    cast(dict[str, object], payload["geometry_template"])["brace_to_column_directed_angle_deg"] = (
        angle
    )
    response = _post(payload)
    assert response.status_code == 422


def test_b1_executes_synthetic_bolt_checks_without_f593_claim() -> None:
    response = _post(build_api_payload("B1"))
    body = response.json()
    assert response.status_code == 200
    assert body["fastener"]["id"] == "B1_SYNTHETIC"
    assert body["fastener"]["locked"] is False
    assert body["fastener"]["fnt_source_classification"] == "USER_DEFINED"
    assert _result(body, "BOLT_SHEAR", None)["availability"] == "CALCULATED"
    assert "ASTM F593-17" not in body["fastener"]["bolt_specification"]


def test_locked_f593_stays_source_pending_with_http_200() -> None:
    response = _post(build_api_payload("P1"))
    body = response.json()
    assert response.status_code == 200
    assert body["fastener"]["fnt"] is None
    assert _result(body, "BOLT_SHEAR", None)["availability"] == "SOURCE_DATA_PENDING"
    assert "FASTENER_SOURCE_PENDING" in {item["code"] for item in body["issues"]}
    assert body["aggregate_status"] != "PASS"


def test_member_action_without_demand_is_http_200_and_runs_no_equations() -> None:
    response = _post(build_api_payload("J1-T", explicit_demand=False))
    body = response.json()
    assert response.status_code == 200
    assert body["aggregate_status"] == "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    assert body["plans"] == []
    assert body["results"] == []
    assert body["governing_check_ids"] == []
    assert body["source_action_trace"]["automatic_moment_shift_applied"] is False
    assert "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED" in {
        item["code"] for item in body["issues"]
    }
    assert "equal sharing" not in response.text.lower()
    assert "prying" not in response.text.lower()


@pytest.mark.parametrize("fixture", ["P1", "P2A"])
def test_us_si_http_equivalence_and_required_fingerprint_policy(fixture: str) -> None:
    us = _post(build_api_payload(fixture, unit_system=EngineeringUnitSystem.US_CUSTOMARY)).json()
    si = _post(build_api_payload(fixture, unit_system=EngineeringUnitSystem.SI)).json()
    assert us["aggregate_status"] == si["aggregate_status"]
    assert us["governing_check_ids"] == si["governing_check_ids"]
    assert us["calculation_fingerprint"] == si["calculation_fingerprint"]
    for us_result, si_result in zip(us["results"], si["results"], strict=True):
        assert us_result["numerical_comparison"] == si_result["numerical_comparison"]
        assert us_result["availability"] == si_result["availability"]
        if us_result["design_resistance"] is not None:
            us_force = Decimal(us_result["design_resistance"]["value"])
            si_force = Decimal(si_result["design_resistance"]["value"])
            assert si_force.quantize(Decimal("1e-12")) == (us_force * KIP_TO_KN).quantize(
                Decimal("1e-12")
            )


def test_j1_us_si_preserves_q12_result_status_without_new_fingerprint_requirement() -> None:
    us = _post(build_api_payload("J1-T")).json()
    si = _post(build_api_payload("J1-T", unit_system=EngineeringUnitSystem.SI)).json()
    assert us["aggregate_status"] == si["aggregate_status"]
    assert us["governing_check_ids"] == si["governing_check_ids"]
    assert [item["numerical_comparison"] for item in us["results"]] == [
        item["numerical_comparison"] for item in si["results"]
    ]
    assert [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in us["results"]
    ] == [
        None
        if item["utilization"] is None
        else Decimal(item["utilization"]).quantize(Decimal("1e-12"))
        for item in si["results"]
    ]


def test_exact_90_degree_transport_selects_transverse_endpoint_and_na_cleavage() -> None:
    payload = build_api_payload("P2A")
    placements = cast(
        list[dict[str, object]], cast(dict[str, object], payload["geometry"])["member_placements"]
    )
    second = placements[1]
    second["start"] = {"x": "2", "y": "-2", "z": "0", "unit": "in"}
    second["end"] = {"x": "2", "y": "2", "z": "0", "unit": "in"}
    response = _post(payload)
    body = response.json()
    assert response.status_code == 200
    mapping = body["resolved_layers"][1]["code_mapping"]
    assert mapping["theta_degrees"] == "90"
    assert mapping["direction_family"] == "TRANSVERSE"
    assert mapping["direction_interpretation_id"] == "TRANSVERSE_ENDPOINT_INCLUDED"
    assert _result(body, "CLEAVAGE", "layer-B")["availability"] == "NOT_APPLICABLE"


def test_serializer_emits_decimal_strings_units_sources_and_no_internal_leakage() -> None:
    canonical = map_single_bolt_request(
        SingleBoltEvaluationRequestDTO.model_validate(build_api_payload("P1"))
    )
    response = evaluate_single_bolt_connection(canonical)
    serialized = serialize_single_bolt_response(
        response,
        build_single_bolt_visualization_snapshot(canonical, response),
    )
    body = serialized.model_dump(mode="json")
    assert _no_float(body)
    bearing = _result(body, "PIN_BEARING", "layer-A")
    assert cast(dict[str, str], bearing["design_resistance"])["unit"] == "kip"
    assert isinstance(bearing["utilization"], str)
    assert body["source_references"]
    rendered = json.dumps(body, sort_keys=True)
    for prohibited in ("C:\\\\", "/home/", ".pdf", "Traceback", "repr(", "api-test-account"):
        assert prohibited not in rendered


def test_trusted_identity_is_resolved_once_but_cannot_change_result() -> None:
    resolver = CountingIdentityResolver()
    application = _application(resolver)
    payload = build_api_payload("P1")
    response = _post(payload, application=application)
    spoofed = _post(
        payload,
        application=application,
    )
    assert response.status_code == spoofed.status_code == 200
    assert response.content == spoofed.content
    assert resolver.calls == 2
    assert "api-test-account" not in response.text


def test_route_invokes_orchestration_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = evaluate_single_bolt_connection

    def tracked(request: SingleBoltOrchestrationRequest) -> object:
        nonlocal calls
        calls += 1
        return original(request)

    monkeypatch.setattr(routes_module, "evaluate_single_bolt_connection", tracked)
    response = _post(build_api_payload("P1"))
    assert response.status_code == 200
    assert calls == 1


def test_openapi_registers_one_post_and_excludes_client_authority() -> None:
    schema = _application().openapi()
    assert set(schema["paths"]) == {
        "/api/v1/connector-materials/capabilities",
        "/api/v1/connector-materials/plan",
        "/health",
        "/api/v1/meta",
        "/api/v1/calculations/single-bolt/preview",
        "/api/v1/calculations/multi-row/preview",
        "/api/v1/calculations/multi-row/design-check",
        "/api/v1/calculations/tee-connector/preview",
        "/api/v1/calculations/tee-connector/design-check",
        "/api/v1/calculations/clip-angle/preview",
        "/api/v1/calculations/clip-angle/design-check",
        "/api/v1/calculations/paired-clip-angle/preview",
        "/api/v1/calculations/paired-clip-angle/design-check",
        "/api/v1/calculations/multi-member-tee/preview",
        "/api/v1/calculations/multi-member-tee/design-check",
        "/api/v1/calculations/beam-concrete-paired-angle/preview",
        "/api/v1/calculations/beam-concrete-paired-angle/design-check",
        "/api/v1/calculations/direct-side-lap-concrete/preview",
        "/api/v1/calculations/direct-side-lap-concrete/design-check",
        "/api/v1/calculations/column-base-web-angles/preview",
        "/api/v1/calculations/column-base-web-angles/design-check",
        "/api/v1/calculations/beam-web-splice/preview",
        "/api/v1/calculations/beam-web-splice/design-check",
        "/api/v1/calculations/wi-major-axis-moment-splice/preview",
        "/api/v1/calculations/wi-major-axis-moment-splice/design-check",
        "/api/v1/calculations/channel-major-axis-moment-splice/preview",
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check",
        "/api/v1/calculations/wi-beam-concrete-wall-moment/preview",
        "/api/v1/calculations/wi-beam-concrete-wall-moment/design-check",
        "/api/v1/calculations/wi-beam-frp-support-moment/preview",
        "/api/v1/calculations/wi-beam-frp-support-moment/design-check",
        "/api/v1/calculations/angle-column-two-leg-moment-base/defaults",
        "/api/v1/calculations/angle-column-two-leg-moment-base/preview",
        "/api/v1/calculations/angle-column-two-leg-moment-base/design-check",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/defaults",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/preview",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/design-check",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/convert-units",
        "/api/v1/calculations/double-channel-truss-node/defaults",
        "/api/v1/calculations/double-channel-truss-node/preview",
        "/api/v1/calculations/double-channel-truss-node/design-check",
        "/api/v1/calculations/double-channel-truss-node/convert-units",
        ROUTE,
    }
    assert set(schema["paths"][ROUTE]) == {"post"}
    operation = schema["paths"][ROUTE]["post"]
    request_reference = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_name = request_reference.rsplit("/", 1)[1]
    request_schema = json.dumps(schema["components"]["schemas"][request_name], sort_keys=True)
    for prohibited in (
        "trusted_identity",
        "role",
        "organization",
        "entitlement",
        "engine_version",
        "rule_set_version",
        "fingerprint",
        '"result"',
        "capacity",
        "utilization",
    ):
        assert prohibited not in request_schema
    response_schema = json.dumps(operation["responses"]["200"], sort_keys=True)
    assert "SingleBoltEvaluationResponseDTO" in response_schema


def test_mapping_failures_are_safe_422_without_stack_or_path() -> None:
    payload = build_api_payload("P1")
    geometry = cast(dict[str, object], payload["geometry"])
    placements = cast(list[dict[str, object]], geometry["member_placements"])
    placements.pop()
    response = _post(payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_MAPPING_INVALID"
    assert "Traceback" not in response.text
    assert "C:\\" not in response.text


def test_mapper_rejects_wrong_dimensions_orientations_and_spoofed_locked_sources() -> None:
    mutations: list[tuple[Callable[[dict[str, object]], None], str]] = []

    def wrong_bolt_dimension(payload: dict[str, object]) -> None:
        cast(dict[str, object], payload["bolt_diameter"])["unit"] = "kip"

    def wrong_point_dimension(payload: dict[str, object]) -> None:
        geometry = cast(dict[str, object], payload["geometry"])
        frame = cast(dict[str, object], geometry["joint_frame"])
        cast(dict[str, object], frame["origin"])["unit"] = "kip"

    def wrong_action_dimension(payload: dict[str, object]) -> None:
        assembly = cast(dict[str, object], payload["joint_assembly"])
        action = cast(list[dict[str, object]], assembly["member_end_actions"])[0]
        cast(dict[str, object], action["force"])["unit"] = "in"

    def missing_frp_orientation(payload: dict[str, object]) -> None:
        assembly = cast(dict[str, object], payload["joint_assembly"])
        cast(list[dict[str, object]], assembly["members"])[0]["material_orientation"] = None

    def steel_with_orientation(payload: dict[str, object]) -> None:
        assembly = cast(dict[str, object], payload["joint_assembly"])
        members = cast(list[dict[str, object]], assembly["members"])
        members[1]["material_orientation"] = copy.deepcopy(members[0]["material_orientation"])

    def missing_patch(payload: dict[str, object]) -> None:
        geometry = cast(dict[str, object], payload["geometry"])
        interface = cast(dict[str, object], geometry["interface"])
        cast(dict[str, object], interface["first_side"])["patch_id"] = "missing-patch"

    def spoofed_material(payload: dict[str, object]) -> None:
        cast(list[dict[str, object]], payload["material_snapshots"])[0]["display_name"] = "Spoof"

    def spoofed_fastener(payload: dict[str, object]) -> None:
        cast(dict[str, object], payload["fastener_snapshot"])["display_name"] = "Spoof"

    def duplicate_members(payload: dict[str, object]) -> None:
        assembly = cast(dict[str, object], payload["joint_assembly"])
        members = cast(list[dict[str, object]], assembly["members"])
        members[1] = copy.deepcopy(members[0])

    def duplicate_materials(payload: dict[str, object]) -> None:
        materials = cast(list[dict[str, object]], payload["material_snapshots"])
        materials.append(copy.deepcopy(materials[0]))

    mutations.extend(
        [
            (wrong_bolt_dimension, "Expected LENGTH"),
            (wrong_point_dimension, "geometry point"),
            (wrong_action_dimension, "Vector unit"),
            (missing_frp_orientation, "require material_orientation"),
            (steel_with_orientation, "cannot declare FRP"),
            (missing_patch, "resolve exactly once"),
            (spoofed_material, "approved ICE"),
            (spoofed_fastener, "approved F593"),
            (duplicate_members, "Member identities"),
            (duplicate_materials, "Material snapshot identities"),
        ]
    )
    for mutation, expected in mutations:
        payload = build_api_payload("P1")
        mutation(payload)
        dto = SingleBoltEvaluationRequestDTO.model_validate(payload)
        with pytest.raises(ValueError, match=expected):
            map_single_bolt_request(dto)


def test_i_section_factory_and_defensive_serializer_branches() -> None:
    class ExampleEnum(Enum):
        VALUE = "VALUE"

    payload = build_api_payload("J1-T")
    assembly = cast(dict[str, object], payload["joint_assembly"])
    section = cast(
        dict[str, object], cast(list[dict[str, object]], assembly["members"])[1]["section"]
    )
    section["kind"] = "I_SECTION"
    request = map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))
    assert request.assembly.members[1].section_family.value == "I_SECTION"
    assert calculation_mapping._json_value(1.25, EngineeringUnitSystem.US_CUSTOMARY) == "1.25"
    assert (
        calculation_mapping._json_value(date(2026, 1, 13), EngineeringUnitSystem.US_CUSTOMARY)
        == "2026-01-13"
    )
    assert (
        calculation_mapping._json_value(ExampleEnum.VALUE, EngineeringUnitSystem.US_CUSTOMARY)
        == "VALUE"
    )
    assert calculation_mapping._json_value([Decimal("1")], EngineeringUnitSystem.US_CUSTOMARY) == [
        "1"
    ]
    with pytest.raises(TypeError, match="Unsupported response value type"):
        calculation_mapping._json_value(object(), EngineeringUnitSystem.US_CUSTOMARY)


def test_valid_conflicting_target_identity_is_engineering_http_200() -> None:
    payload = build_api_payload("P1")
    payload["bolt_location_id"] = "other-bolt"
    response = _post(payload)
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert "BOLT_LOCATION_NOT_FOUND" in {item["code"] for item in response.json()["issues"]}


def test_request_payload_is_not_mutated_by_mapping_or_http() -> None:
    payload = build_api_payload("P1")
    before = copy.deepcopy(payload)
    assert _post(payload).status_code == 200
    assert payload == before


@pytest.mark.parametrize("fixture_id", ["P1", "J1-T"])
def test_http_response_contains_canonical_visualization_snapshot(fixture_id: str) -> None:
    response = _post(build_api_payload(fixture_id))
    assert response.status_code == 200
    body = response.json()
    snapshot = body["visualization"]
    assert snapshot["snapshot_version"] == "1.3.0-draft"
    assert snapshot["assembly_id"] == body["assembly_id"]
    assert snapshot["bolt_group_id"] == body["bolt_group_id"]
    assert snapshot["frames"][0]["id"] == "GLOBAL"
    assert snapshot["bolt"]["bolt_location_id"] == "bolt-1"
    assert "camera" not in repr(snapshot).lower()


def test_j1_http_visualization_has_geometry_material_axes_and_action_reference() -> None:
    body = _post(build_api_payload("J1-T")).json()
    snapshot = body["visualization"]
    assert [item["section_family"] for item in snapshot["components"]] == [
        "ANGLE",
        "WIDE_FLANGE",
    ]
    assert {item["physical_element_id"] for item in snapshot["material_directions"]} >= {
        "LEG_1",
        "TOP_FLANGE",
    }
    assert "action:action-1:reference" in {item["id"] for item in snapshot["reference_points"]}
    assert len(snapshot["positive_action_directions"]) == 6


def test_j1_compression_http_visualization_retains_server_applied_directions() -> None:
    body = _post(build_api_payload("J1-C")).json()
    applied = body["visualization"]["applied_action_directions"]
    assert applied[0]["component"] == "FX"
    assert applied[0]["axis"] == {"x": "1", "y": "0", "z": "0"}
    assert applied[1]["is_zero"] is True


def test_member_end_no_distribution_http_response_still_contains_visualization() -> None:
    body = _post(build_api_payload("J1-T", explicit_demand=False)).json()
    assert body["aggregate_status"] == "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    assert body["results"] == []
    assert body["visualization"]["bolt"]["holes"]
    assert len(body["visualization"]["applied_action_directions"]) == 6
