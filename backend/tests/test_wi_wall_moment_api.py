"""Stage 4.2 HTTP/engineering separation and strict decimal/source transport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.wi_wall_moment_mapping import (
    map_wi_wall_moment_request,
    serialize_wall_moment_value,
    serialize_wi_wall_moment,
)
from frp_master_connection.api.wi_wall_moment_schemas import WIWallMomentRequestDTO
from frp_master_connection.application.wi_wall_moment_design import evaluate_wi_wall_moment
from frp_master_connection.application.wi_wall_moment_orchestration import preview_wi_wall_moment
from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.wi_wall_moment import default_wi_wall_moment_request

PATH = "/api/v1/calculations/wi-beam-concrete-wall-moment/"


def payload(system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY) -> dict[str, Any]:
    value = default_wi_wall_moment_request(system)
    result = cast(dict[str, Any], serialize_wall_moment_value(value))
    result["wall"] = {
        key: serialize_wall_moment_value(PhysicalQuantity.of(raw, value.source_length_unit))
        for key, raw in result["wall"].items()
    }
    result["actions"] = {
        key: raw
        for key, raw in result["actions"].items()
        if key in {"axial", "major_shear", "structural_major_moment"}
    }
    return result


def post(kind: str, value: dict[str, Any]) -> httpx.Response:
    async def run() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(PATH + kind, json=value)

    return asyncio.run(run())


@pytest.mark.parametrize("system", list(EngineeringUnitSystem))
def test_exact_dto_native_round_trip_and_http_eng_statuses(system: EngineeringUnitSystem) -> None:
    request = map_wi_wall_moment_request(WIWallMomentRequestDTO.model_validate(payload(system)))
    assert request == default_wi_wall_moment_request(system)
    preview = post("preview", payload(system))
    assert preview.status_code == 200
    assert preview.json() == serialize_wi_wall_moment(preview_wi_wall_moment(request)).model_dump(
        mode="json"
    )
    assert preview.json()["resistance_evaluated"] is False
    design = post("design-check", payload(system))
    assert design.status_code == 200
    assert design.json() == serialize_wi_wall_moment(evaluate_wi_wall_moment(request)).model_dump(
        mode="json"
    )
    assert design.json()["assembly_status"] == "FAIL"
    assert design.json()["ordinary_pass_allowed"] is False
    assert design.json()["result"]["native_governing_check_ids"] == ["FIRST_ROW:TOP_FLANGE_ANGLE"]
    assert design.json()["whole_connection_status"] == "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"


@pytest.mark.parametrize("kind", ["preview", "design-check"])
@pytest.mark.parametrize("invalid", ["gap", "web_symmetry", "finite_wall", "top_lock"])
def test_geometry_invalid_is_engineering_200_not_http_error(kind: str, invalid: str) -> None:
    value = payload()
    if invalid == "gap":
        value["gap"]["value"] = "0"
    elif invalid == "web_symmetry":
        value["negative_web"]["connector_source_reference"] = "different"
    elif invalid == "finite_wall":
        value["wall"]["width"]["value"] = "2"
    else:
        value["bottom"]["geometry"]["length"]["value"] = "7"
    result = post(kind, value)
    assert result.status_code == 200
    assert result.json()["design_check_ready"] is False
    assert result.json()["resistance_evaluated"] is False
    assert result.json()["geometry_status"] in {"INVALID_GEOMETRY", "NOT_EVALUATED"}


@pytest.mark.parametrize("kind", ["preview", "design-check"])
@pytest.mark.parametrize(
    "invalid",
    [
        "float",
        "nan",
        "moment",
        "provider",
        "strength",
        "identity",
        "count",
        "unit",
        "profile",
        "source",
    ],
)
def test_strict_transport_rejects_unknown_or_uncontrolled_inputs(kind: str, invalid: str) -> None:
    value = payload()
    if invalid == "float":
        value["actions"]["axial"]["value"] = 20.0
    elif invalid == "nan":
        value["actions"]["axial"]["value"] = "NaN"
    elif invalid == "moment":
        value["actions"]["torsion"] = {"value": "2", "unit": "kip-in"}
    elif invalid == "provider":
        value["top"]["provider_id"] = "316SS"
    elif invalid == "strength":
        value["top"]["fastener"]["nominal_shear_stress"] = {"value": "100", "unit": "ksi"}
    elif invalid == "identity":
        value["owner_id"] = "caller-cannot-supply-trusted-identity"
    elif invalid == "count":
        value["top"]["member_pattern"]["across"] = True
    elif invalid == "unit":
        value["gap"]["unit"] = "kip"
    elif invalid == "profile":
        value["beam"]["profile_family"] = "CHANNEL"
    else:
        value["top"]["qualified_source"] = {"strength": "invented"}
    assert post(kind, value).status_code == 422


def test_exact_scalar_serializer_and_schema_security() -> None:
    assert serialize_wall_moment_value(Fraction(1, 3)) == {"numerator": "1", "denominator": "3"}
    assert serialize_wall_moment_value(Decimal("1E-79")) == "0." + "0" * 78 + "1"
    assert serialize_wall_moment_value(date(2026, 1, 13)) == "2026-01-13"
    assert serialize_wall_moment_value([None, True, 2]) == [None, True, 2]
    assert serialize_wall_moment_value({1: Decimal("2.0")}) == {"1": "2"}
    with pytest.raises(TypeError, match=r"Unsupported Stage 4\.2 transport"):
        serialize_wall_moment_value(1.2)
    app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    schema = app.openapi()
    assert set(schema["paths"][PATH + "preview"]) == {"post"}
    assert set(schema["paths"][PATH + "design-check"]) == {"post"}
    for name in ("WIWallMomentRequestDTO", "WallMomentAngleDTO", "WallMomentActionsDTO"):
        assert schema["components"]["schemas"][name]["additionalProperties"] is False


def test_r7_failure_trace_visibility_and_no_trace_float() -> None:
    value = serialize_wi_wall_moment(
        evaluate_wi_wall_moment(default_wi_wall_moment_request())
    ).model_dump(mode="json")

    def inspect(item: object) -> None:
        assert not isinstance(item, float)
        if isinstance(item, dict):
            for child in item.values():
                inspect(child)
        elif isinstance(item, list):
            for child in item:
                inspect(child)

    inspect(value)
    failed = value["result"]["native_failed_checks"]
    assert {"FIRST_ROW_NET_TENSION", "PIN_BEARING", "INTERROW_SHEAR_OUT"} <= {
        c["limit_state"] for c in failed
    }
    assert value["result"]["missing_sources"]


@pytest.mark.parametrize("pure_shear", [False, True])
def test_frontend_bootstrap_fixture_is_a_native_response_subset(pure_shear: bool) -> None:
    root = Path(__file__).resolve().parents[2]
    filename = "wiWallMomentPureShearWire.json" if pure_shear else "wiWallMomentWire.json"
    reduced = json.loads((root / "frontend/tests/fixtures" / filename).read_text())
    request = replace(default_wi_wall_moment_request(), request_id="stage-4.2-us_customary")
    if pure_shear:
        request = replace(
            request,
            actions=replace(
                request.actions,
                axial=PhysicalQuantity.of("0", request.actions.axial.unit),
                structural_major_moment=PhysicalQuantity.of(
                    "0", request.actions.structural_major_moment.unit
                ),
            ),
        )
    native = serialize_wi_wall_moment(evaluate_wi_wall_moment(request)).model_dump(mode="json")

    def subset(small: object, full: object) -> None:
        if isinstance(small, dict):
            assert isinstance(full, dict)
            for key, child in small.items():
                assert key in full
                subset(child, full[key])
        elif isinstance(small, list):
            assert isinstance(full, list)
            assert len(small) == len(full)
            for child, actual in zip(small, full, strict=True):
                subset(child, actual)
        else:
            assert small == full

    subset(reduced, native)


def test_pure_shear_has_eight_native_bearing_failures_despite_empty_group_mode_selection() -> None:
    value = payload()
    value["actions"]["axial"]["value"] = "0"
    value["actions"]["structural_major_moment"]["value"] = "0"
    response = post("design-check", value).json()
    result = response["result"]
    assert response["assembly_status"] == result["status"] == "FAIL"
    assert result["status_reason"] == "EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE"
    assert result["native_failed_checks"] == result["native_governing_check_ids"] == []
    failures = [
        b for b in result["web_bearing"] if b["comparison"]["numerical_comparison"] == "FAIL"
    ]
    assert [b["check_id"] for b in failures] == [
        "BEARING:POSITIVE_WEB_ANGLE:B_R1_L1",
        "BEARING:POSITIVE_WEB_ANGLE:B_R1_L2",
        "BEARING:NEGATIVE_WEB_ANGLE:B_R1_L1",
        "BEARING:NEGATIVE_WEB_ANGLE:B_R1_L2",
        "BEARING:WI_WEB:COMMON_WEB:B_R1_L1",
        "BEARING:WI_WEB:COMMON_WEB:B_R1_L2",
        "BEARING:WI_WEB:COMMON_WEB:B_R2_L1",
        "BEARING:WI_WEB:COMMON_WEB:B_R2_L2",
    ]
    assert failures[4]["comparison"]["utilization"] == (
        "2.14623947496383496776394125347462861449484568853006270253511"
    )
    assert all(
        b["trace"]["factor_trace"]["design_resistance"]
        == {"value": "9007.6487709025125", "unit": "N"}
        for b in failures
    )
    assert len(result["missing_sources"]) == 4
    assert response["engineering_fingerprint"] == (
        "76ad0f326eacec1c7ae7ddce981e94b235d3ff24fadf548e4f83e84f41be6968"
    )
    assert response["result_fingerprint"] == (
        "dc758641c2f59866c9ccc3f92d1d7bf13dba8fac6a7199b581105ca72534e4f1"
    )
