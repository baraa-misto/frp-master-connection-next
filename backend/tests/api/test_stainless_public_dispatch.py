"""Public CME-3 conditional dispatch uses existing authenticated design routes."""

import pytest
from tests.api.test_connector_materials import http, native_payload

from frp_master_connection.application.stainless_family_activation import AUTHORITY, ROUTES, STACKS


@pytest.mark.parametrize("route", tuple(ROUTES))
def test_existing_design_route_reaches_conditional_material_dispatch(route: str) -> None:
    payload = native_payload(route)
    response = http(
        "POST", f"/api/v1/calculations/{route}/design-check?connector_body_material=SS316", payload
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["activation_authority"] == AUTHORITY
    assert result["connector_body_material"] == "SS316"
    failed_fixtures = {
        "beam-web-splice",
        "wi-major-axis-moment-splice",
        "channel-major-axis-moment-splice",
        "clip-angle",
        "paired-clip-angle",
        "beam-concrete-paired-angle",
        "wi-beam-concrete-wall-moment",
        "wi-beam-frp-support-moment",
    }
    assert result["status"] == (
        "FAIL" if route in failed_fixtures else "ENGINEERING_REVIEW_REQUIRED"
    )
    retained = result["trace"]["activation"]["checks"]
    assert any(c["comparison"] == "FAIL" for c in retained) == (route in failed_fixtures)
    assert len({(c["domain"], c["id"]) for c in retained}) == len(retained)
    assert result["blockers"]
    for body in result["bodies"]:
        assert body["material"] == "SS316"
        assert body["required_provider_stack"] == list(STACKS[ROUTES[route]])
        assert body["frp_body_resistance_used"] is False
    assert result["trace"]["primary_members"] == "FRP_ONLY"
    assert result["trace"]["hardware"] == "INDEPENDENT"
    assert result["trace"]["foundation"] == "EXTERNAL_NOT_EVALUATED"


@pytest.mark.parametrize("route", tuple(ROUTES))
def test_frp_selection_keeps_original_endpoint_response(route: str) -> None:
    payload = native_payload(route)
    endpoint = f"/api/v1/calculations/{route}/design-check"
    a = http("POST", endpoint, payload)
    b = http("POST", endpoint + "?connector_body_material=FRP", payload)
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


@pytest.mark.parametrize(
    "injection",
    ["source_hash", "provider_fingerprint", "trusted_response", "E4_Fe", "Fy", "local_snapshot"],
)
def test_public_body_cannot_supply_qualification(injection: str) -> None:
    payload = native_payload("clip-angle") | {injection: "forged"}
    result = http(
        "POST",
        "/api/v1/calculations/clip-angle/design-check?connector_body_material=SS316",
        payload,
    )
    assert result.status_code == 422


def test_public_mixed_and_unknown_material_are_rejected() -> None:
    endpoint = "/api/v1/calculations/clip-angle/design-check?"
    for query, reason in [
        (
            "connector_body_material=FRP&connector_body_material=SS316",
            "STAINLESS_MIXED_CONNECTOR_BODY_MATERIALS_NOT_SUPPORTED_IN_CME3_RC1",
        ),
        ("connector_body_material=unknown", "CONNECTOR_BODY_MATERIAL_NOT_SUPPORTED"),
    ]:
        response = http("POST", endpoint + query, native_payload("clip-angle"))
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == reason
