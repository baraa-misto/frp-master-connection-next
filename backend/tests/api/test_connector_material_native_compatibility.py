"""Real native provider and shared-physical-identity compatibility, not golden replay."""

import pytest
from tests.api.test_connector_materials import SS, envelope, http, native_payload

from frp_master_connection.api.connector_material_native import (
    FAMILIES,
    NativeFamilyInput,
    native_family_providers,
)
from frp_master_connection.api.connector_materials import MaterialPlanRequestDTO, material_plan
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.calculation.connector_material_provider import (
    dispatch_connector_provider,
)
from frp_master_connection.domain.connector_materials import ComponentRole


def test_direct_no_body_family_retains_native_member_and_fastener_design() -> None:
    from typing import cast

    from pydantic import JsonValue
    from tests.api_fixtures import build_api_payload

    from frp_master_connection.api.calculation_mapping import map_single_bolt_request
    from frp_master_connection.api.schemas import SingleBoltEvaluationRequestDTO
    from frp_master_connection.application.calculation_orchestration import (
        evaluate_single_bolt_connection,
    )

    payload = build_api_payload("J1-T")
    expected = evaluate_single_bolt_connection(
        map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))
    )
    assert FAMILIES["single-bolt"].design(cast(dict[str, JsonValue], payload)) == expected


@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r not in NO_BODY_ROUTES))
def test_real_family_provider_is_exact_native_frp_result_not_recomputed(route: str) -> None:
    family = FAMILIES[route]
    payload = native_payload(route)
    component = next(
        c
        for c in canonical_material_assembly(route, family.preview(payload)).components
        if c.role is ComponentRole.CONNECTOR_BODY
    )
    registry = native_family_providers()
    provider = registry["NATIVE_FRP:" + route]
    expected = family.design(payload)
    actual = dispatch_connector_provider(
        component,
        component.material,
        provider.capability.provider_id,
        provider.capability.method,
        NativeFamilyInput(route, payload),
        registry,
    )
    assert actual.native_result == expected
    assert actual.status == "NATIVE_RESULT_UNMODIFIED"
    with pytest.raises(ValueError, match="another family"):
        provider.evaluate(NativeFamilyInput("unregistered", payload))


@pytest.mark.parametrize(
    "route", ["angle-column-two-leg-moment-base", "wi-rhs-srs-column-moment-base"]
)
def test_display_units_preserve_physical_material_plan_identity(route: str) -> None:
    plans = []
    for unit in ("US_CUSTOMARY", "SI"):
        payload = http("GET", f"/api/v1/calculations/{route}/defaults?unit_system={unit}").json()
        plans.append(
            material_plan(
                MaterialPlanRequestDTO.model_validate(
                    {
                        "route_id": route,
                        "product_id": FAMILIES[route].product_id,
                        "native_input": payload,
                    }
                )
            )
        )
    assert plans[0]["fingerprint"] == plans[1]["fingerprint"]


def test_shared_multi_member_tee_has_one_body_and_distinct_slot_bolt_groups() -> None:
    route = "multi-member-tee"
    preview = FAMILIES[route].preview(native_payload(route))
    assembly = canonical_material_assembly(route, preview)
    bodies = [c for c in assembly.components if c.role is ComponentRole.CONNECTOR_BODY]
    hardware = [c for c in assembly.components if c.role is ComponentRole.FASTENER_OR_HARDWARE]
    assert len(bodies) == 1
    assert len(hardware) == 16
    request = envelope(route)
    request["assignments"] = [
        {"component_id": "UPPER_BRACE:tee-connector", "material": SS},
        {"component_id": "LOWER_BRACE:tee-connector", "material": {}},
    ]
    response = http("POST", "/api/v1/connector-materials/plan", request)
    assert response.status_code == 422
    assert "CONFLICTING_SHARED" in response.text
