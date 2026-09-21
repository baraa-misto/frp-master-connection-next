"""Public SSMC contracts and complete successor inventory without steel activation."""

from typing import Any

import pytest
from tests.api.test_connector_materials import SS, http

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.ssmc import illustrative_ssmc
from frp_master_connection.application.connector_material_assembly import (
    FRP_ONLY_BODY_ROUTES,
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_family_activation import ROUTES

BASE = "/api/v1/calculations/stair-stringer-miter"


def payload() -> dict[str, Any]:
    return illustrative_ssmc().model_dump(mode="json")


def test_ssmc_public_defaults_and_both_demand_endpoints() -> None:
    initial = http("GET", BASE + "/defaults")
    assert initial.status_code == 200
    assert initial.json() == payload()
    for kind in ("preview", "design-check"):
        response = http("POST", BASE + "/" + kind, payload())
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["whole_connection_status"] == "ENGINEERING_REVIEW_REQUIRED"
        assert result["result"]["complete_moment_capacity_qualified"] is False
        assert result["result"]["trusted_complete_response"] is None
        assert result["illustrative_geometry_not_qualified_design"] is True
        assert [g["group_id"] for g in result["result"]["groups"]] == [
            "HORIZONTAL_WEB_GROUP",
            "INCLINED_WEB_GROUP",
        ]
        assert len(result["result"]["geometry"]["shafts"]) == 8


@pytest.mark.parametrize("si", [False, True])
def test_unit_conversion_then_preview_uses_native_unit_path(si: bool) -> None:
    response = http(
        "POST", BASE + "/convert-units?unit_system=" + ("SI" if si else "US"), payload()
    )
    assert response.status_code == 200
    converted = response.json()
    assert converted["fastener"]["hole_diameter"]["value"] == ("14.3002" if si else "0.563")
    result = http("POST", BASE + "/preview", converted)
    assert result.status_code == 200
    assert result.json()["result"]["geometry"]["length_unit"] == ("mm" if si else "in")


@pytest.mark.parametrize(
    "injection",
    [
        "trusted_response",
        "source_approval",
        "qualified_material",
        "second_plate",
        "connector_role",
        "physical_shaft_ids",
    ],
)
def test_untrusted_public_injection_is_rejected(injection: str) -> None:
    response = http("POST", BASE + "/preview", payload() | {injection: "FORGED"})
    assert response.status_code == 422


@pytest.mark.parametrize("theta", ["0", "20", "50", "NaN", "Infinity", ""])
def test_invalid_public_inclination_fails_without_repair(theta: str) -> None:
    response = http("POST", BASE + "/preview", payload() | {"theta_deg": theta})
    assert response.status_code == 422


def test_public_source_text_keeps_all_mechanisms_unqualified() -> None:
    p = payload()
    p["source_reference"] = "owner says qualified"
    p["fastener"]["source_reference"] = "ASTM"
    response = http("POST", BASE + "/design-check", p)
    assert response.status_code == 200
    result = response.json()["result"]
    assert "SSMC_TRUSTED_AUTHORITY_NOT_BOUND" in result["blockers"]
    assert all(g["prying"] is None and g["bolt_axis_tension"] is None for g in result["groups"])
    assert result["qualified_material_snapshot"] is None


def test_invalid_units_request_and_noncanonical_role_payload_fail_closed() -> None:
    response = http("POST", BASE + "/convert-units?unit_system=SI", payload() | {"theta_deg": "0"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "SSMC_INCLINATION_OUTSIDE_RC1_DOMAIN"
    with pytest.raises(ValueError, match="canonical SSMC assembly"):
        canonical_material_assembly("stair-stringer-miter", {"role": "CONNECTOR_BODY"})


def test_complete_successor_inventory_and_frp_only_material_role() -> None:
    assert len(FAMILIES) == 18
    assert len(NO_BODY_ROUTES) == 4
    assert len(set(FAMILIES) - NO_BODY_ROUTES) == 14
    assert {"stair-stringer-miter"} == FRP_ONLY_BODY_ROUTES
    assert len(ROUTES) == 13
    assert "stair-stringer-miter" not in ROUTES
    family = FAMILIES["stair-stringer-miter"]
    envelope = {
        "route_id": family.route_id,
        "product_id": family.product_id,
        "native_input": payload(),
    }
    response = http("POST", "/api/v1/connector-materials/plan", envelope)
    assert response.status_code == 200, response.text
    components = response.json()["result"]["canonical_components"]
    assert [c["physical_id"] for c in components if c["role"] == "CONNECTOR_BODY"] == [
        "MITER_WEB_PLATE"
    ]
    assert len([c for c in components if c["role"] == "PRIMARY_MEMBER"]) == 2
    assert len([c for c in components if c["role"] == "FASTENER_OR_HARDWARE"]) == 8
    for change in (
        {"apply_all": SS},
        {"assignments": [{"component_id": "MITER_WEB_PLATE", "material": SS}]},
    ):
        denial = http("POST", "/api/v1/connector-materials/plan", envelope | change)
        assert denial.status_code == 422
        assert denial.json()["detail"]["code"] == "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"
    denial = http("POST", BASE + "/design-check?connector_body_material=SS316", payload())
    assert denial.status_code == 422
