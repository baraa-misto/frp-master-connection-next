"""Strict Stage 4.3 request, transport and preview/design separation."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.wi_frp_support_moment_mapping import (
    map_wi_frp_support_moment_request,
    serialize_wi_frp_support_moment,
)
from frp_master_connection.api.wi_frp_support_moment_schemas import WIFrpSupportMomentRequestDTO
from frp_master_connection.api.wi_wall_moment_mapping import serialize_wall_moment_value
from frp_master_connection.application.wi_frp_support_moment_design import (
    evaluate_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    preview_wi_frp_support_moment,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain.wi_frp_support_moment import (
    SupportMode,
    default_frp_support_moment_request,
)

PATH = "/api/v1/calculations/wi-beam-frp-support-moment/"


def payload(mode: SupportMode = SupportMode.WI_FLANGE, *, si: bool = False) -> dict[str, Any]:
    result = cast(
        dict[str, Any], serialize_wall_moment_value(default_frp_support_moment_request(mode, si=si))
    )
    for key in ("minor_shear", "minor_moment", "torsion"):
        del result["actions"][key]
    for name in ("top", "bottom", "positive_web", "negative_web"):
        for fastener in ("fastener", "support_fastener"):
            del result[name][fastener]["nominal_shear_stress"]
    return result


def post(kind: str, value: dict[str, Any]) -> httpx.Response:
    async def run() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(PATH + kind, json=value)

    return asyncio.run(run())


@pytest.mark.parametrize("mode", list(SupportMode))
@pytest.mark.parametrize("si", [False, True])
def test_t43_073_native_api_roundtrip_and_both_explicit_routes(mode: SupportMode, si: bool) -> None:
    wire = payload(mode, si=si)
    r = map_wi_frp_support_moment_request(WIFrpSupportMomentRequestDTO.model_validate(wire))
    assert r == default_frp_support_moment_request(mode, si=si)
    for kind, result in (
        ("preview", preview_wi_frp_support_moment(r)),
        ("design-check", evaluate_wi_frp_support_moment(r)),
    ):
        response = post(kind, wire)
        assert response.status_code == 200
        body = response.json()
        assert body == serialize_wi_frp_support_moment(result).model_dump(mode="json")
        assert body["ordinary_pass_allowed"] is False
        assert body["resistance_evaluated"] is (kind == "design-check")
        assert "ANCHOR" not in body["whole_connection_status"]


@pytest.mark.parametrize("kind", ["preview", "design-check"])
@pytest.mark.parametrize(
    "bad",
    [
        "identity",
        "product",
        "scalar",
        "nan",
        "forceunit",
        "moment",
        "316ss",
        "strength",
        "qualified",
        "anchor",
        "face",
        "square",
        "count",
        "material",
    ],
)
def test_t43_strict_non_authorized_transport_never_grants_authority(kind: str, bad: str) -> None:
    value = payload()
    if bad == "identity":
        value["owner_id"] = "CLIENT_OWNER"
    elif bad == "product":
        value["contract"] = "4.2-RC1"
    elif bad == "scalar":
        value["gap"]["value"] = 0.5
    elif bad == "nan":
        value["gap"]["value"] = "NaN"
    elif bad == "forceunit":
        value["gap"]["unit"] = "kip"
    elif bad == "moment":
        value["actions"]["torsion"] = {"value": "1", "unit": "kip-in"}
    elif bad == "316ss":
        value["top"]["provider_id"] = "316SS"
    elif bad == "strength":
        value["top"]["support_fastener"]["nominal_shear_stress"] = {"value": "40", "unit": "ksi"}
    elif bad == "qualified":
        value["qualified"] = True
    elif bad == "anchor":
        value["top"]["anchor_embedment"] = {"value": "4", "unit": "in"}
    elif bad == "face":
        value["support"]["face"] = "CHANNEL_FLANGE"
    elif bad == "square":
        value = payload(SupportMode.HOLLOW_SQUARE)
        value["support"]["width"]["value"] = "10"
    elif bad == "count":
        value["top"]["support_pattern"]["across"] = True
    else:
        value["support"]["material_id"] = "UNREGISTERED"
    assert post(kind, value).status_code == 422


@pytest.mark.parametrize("kind", ["preview", "design-check"])
def test_invalid_geometry_has_structured_engineering_status_and_no_resistance(kind: str) -> None:
    value = payload()
    value["gap"]["value"] = "0"
    response = post(kind, value)
    assert response.status_code == 200
    body = response.json()
    assert not body["resistance_evaluated"]
    assert not body["design_check_ready"]
    assert body["geometry_status"] == "INVALID_GEOMETRY"
    assert body["geometry_invalid_reasons"]


def test_typed_unregistered_response_ref_remains_source_required_in_preview_and_design() -> None:
    value = payload()
    value["response_source_reference"] = "TEST_QUALIFIED_TRUE_IS_NOT_AUTHORITY"
    preview = post("preview", value).json()
    assert any(
        item[0] == "COMPLETE_SUPPORT_RESPONSE" and item[2].startswith("SOURCE_REQUIRED")
        for item in preview["result"]["source_availability"]
    )
    design = post("design-check", value).json()
    assert design["result"]["support_response"]["status"] == "SOURCE_REQUIRED"
    assert design["assembly_status"] == "FAIL"


def test_new_routes_retain_the_trusted_server_identity_dependency() -> None:
    app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    schema = app.openapi()
    for suffix in ("preview", "design-check"):
        operation = schema["paths"][PATH + suffix]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "WIFrpSupportMomentRequestDTO"
        )
        assert "owner_id" not in str(operation)
