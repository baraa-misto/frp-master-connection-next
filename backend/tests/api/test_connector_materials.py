"""CME-1 native canonical assembly, authorization and all-family adapters."""

from __future__ import annotations

import asyncio
import importlib
from typing import Any, cast

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.connector_materials import (
    MaterialPlanRequestDTO,
    capabilities,
    material_plan,
)
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings

FACTORIES = {
    "single-bolt": ("api_fixtures", "build_j1_preview_api_payload"),
    "multi-row": ("test_multirow_api", "_payload"),
    "tee-connector": ("tee_fixtures", "build_tee_payload"),
    "clip-angle": ("clip_angle_fixtures", "build_clip_angle_payload"),
    "paired-clip-angle": ("paired_clip_angle_fixtures", "build_paired_clip_angle_payload"),
    "multi-member-tee": ("multi_member_tee_fixtures", "build_multi_member_tee_payload"),
    "beam-concrete-paired-angle": (
        "beam_concrete_paired_angle_fixtures",
        "build_beam_concrete_paired_angle_payload",
    ),
    "direct-side-lap-concrete": (
        "direct_side_lap_concrete_fixtures",
        "build_direct_side_lap_concrete_payload",
    ),
    "column-base-web-angles": ("column_base_profile_fixtures", "build_column_base_profile_payload"),
    "beam-web-splice": ("test_stage_3_6a_web_splice", "_dto"),
    "wi-major-axis-moment-splice": ("test_stage_4_1a_wi_moment_splice", "_dto_payload"),
    "channel-major-axis-moment-splice": ("test_stage_4_1b_channel_moment_splice", "_dto_payload"),
    "wi-beam-concrete-wall-moment": ("test_wi_wall_moment_api", "payload"),
    "wi-beam-frp-support-moment": ("test_wi_frp_support_moment_api", "payload"),
}
SS = {
    "family": "SS316",
    "grade": "316",
    "stock_specification": "ASTM_A240_A240M",
    "edition": "26",
    "fabrication": "FORMED_BENT",
    "condition": "UNVERIFIED",
    "method_version": "CME2_PENDING",
}


def http(method: str, path: str, payload: dict[str, Any] | None = None) -> httpx.Response:
    async def run() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(run())


def native_payload(route: str) -> dict[str, Any]:
    if route in FACTORIES:
        module, name = FACTORIES[route]
        result: dict[str, Any] = getattr(importlib.import_module("tests." + module), name)()
        return result
    response = http("GET", f"/api/v1/calculations/{route}/defaults")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def envelope(route: str) -> dict[str, Any]:
    return {
        "route_id": route,
        "product_id": FAMILIES[route].product_id,
        "native_input": native_payload(route),
    }


# Preserve this historical cohort exactly; SSMC's FRP-only successor is tested
# separately in test_ssmc_api, including its mandatory stainless rejection.
@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r != "stair-stringer-miter"))
def test_every_native_family_has_canonical_body_or_explicit_no_body_policy(route: str) -> None:
    request = envelope(route)
    family = FAMILIES[route]
    before = family.preview(request["native_input"])
    assembly = canonical_material_assembly(route, before)
    response = http("POST", "/api/v1/connector-materials/plan", request)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["resistance_evaluated"] is False
    assert value["persisted"] is False
    result = value["result"]
    assert result["native_identity_unchanged"] == assembly.native_identity
    assert result["design_status"] is None
    assert family.preview(request["native_input"]) == before
    assert bool(result["targets"]) == (route not in NO_BODY_ROUTES)
    assert all(c["role"] != "UNCLASSIFIED" for c in result["canonical_components"]), result[
        "canonical_components"
    ]
    request["apply_all"] = SS
    planned = http("POST", "/api/v1/connector-materials/plan", request)
    assert planned.status_code == 200, planned.text
    result = planned.json()["result"]
    assert all(
        t["provider_status"] == "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
        and t["capacity"] is None
        and t["utilization"] is None
        for t in result["targets"]
    )
    assert result["derived_branch_forces"] is None
    for component in result["canonical_components"]:
        if component["role"] != "CONNECTOR_BODY":
            denied = dict(
                request,
                apply_all=None,
                assignments=[{"component_id": component["physical_id"], "material": SS}],
            )
            rejection = material_rejection(denied)
            assert "ROLE_SUBSTITUTION_FORBIDDEN" in rejection


def material_rejection(request: dict[str, Any]) -> str:
    with pytest.raises(ValueError, match="ROLE_SUBSTITUTION_FORBIDDEN") as error:
        material_plan(MaterialPlanRequestDTO.model_validate(request))
    return str(error.value)


@pytest.mark.parametrize(
    "change",
    [
        {"role": "CONNECTOR_BODY"},
        {"source_approval": "QUALIFIED"},
        {"component_roles": []},
        {"geometry_fingerprint": "forged"},
    ],
)
def test_request_cannot_mint_roles_sources_or_trusted_geometry(change: dict[str, Any]) -> None:
    response = http("POST", "/api/v1/connector-materials/plan", envelope("tee-connector") | change)
    assert response.status_code == 422


def test_unknown_product_component_and_invalid_native_geometry_fail_closed() -> None:
    request = envelope("wi-rhs-srs-column-moment-base")
    changes: tuple[dict[str, Any], ...] = (
        {"route_id": "unknown"},
        {"product_id": "unknown"},
        {"native_input": {}},
        {"assignments": [{"component_id": "column-as-connector", "material": SS}]},
    )
    for change in changes:
        response = http("POST", "/api/v1/connector-materials/plan", request | change)
        assert response.status_code == 422
    response = http("GET", "/api/v1/connector-materials/capabilities")
    assert response.status_code == 200
    assert response.json()["result"] == capabilities()


@pytest.mark.parametrize("shape", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", ["TWO_X", "TWO_Y", "FOUR_XY"])
def test_all_column_moment_modes_share_each_physical_body_and_fastener_once(
    shape: str, layout: str
) -> None:
    route = "wi-rhs-srs-column-moment-base"
    response = http("GET", f"/api/v1/calculations/{route}/defaults?preset={shape}&layout={layout}")
    assert response.status_code == 200
    native = response.json()
    result = material_plan(
        MaterialPlanRequestDTO.model_validate(
            {
                "route_id": route,
                "product_id": FAMILIES[route].product_id,
                "native_input": native,
                "apply_all": SS,
            }
        )
    )
    targets = result["targets"]
    assert isinstance(targets, list)
    assert len(targets) == (4 if layout == "FOUR_XY" else 2)
    components = result["canonical_components"]
    assert isinstance(components, list)
    ids = [c["physical_id"] for c in components if isinstance(c, dict)]
    assert len(ids) == len(set(ids))


def test_historical_scope_remains_exact_after_current_additive_material_routes() -> None:
    from tests.calculation.stage_4_5_scope_authority import (
        evidence,
        frozen_stage45_entries,
        stage45_predecessor_entries,
    )

    historical = frozen_stage45_entries()
    assert "connector_materials.py" not in historical
    assert stage45_predecessor_entries(historical) == evidence()["entries"]
    with pytest.raises(AssertionError, match=r"historical Stage 4\.5 manifest"):
        frozen_stage45_entries("{}")
    with pytest.raises(AssertionError, match="protected"):
        stage45_predecessor_entries(
            historical.replace("fbbdebf37e7ef2e411c8fa95df1d96cd3f86a195", "0" * 40)
        )
