"""MAT1 public data boundary and actual native property consumption."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload
from tests.clip_angle_fixtures import build_clip_angle_payload
from tests.test_multirow_api import _payload as multirow_payload

import frp_master_connection.api.mat1 as mat1_api
from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.ssmc import illustrative_ssmc
from frp_master_connection.application.mat1_scope import MAT1Scope


def call(method: str, route: str, body: dict[str, Any] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, route, json=body)

    return asyncio.run(send())


def selection(record: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "CATALOG",
        "id": record["id"],
        "revision": record["revision"],
        "content_digest": record["content_digest"],
    }


def condition(category: str) -> dict[str, Any]:
    return {
        "sustained_temperature": {"value": "90", "unit": "degF"},
        "maximum_temperature": {"value": "90", "unit": "degF"},
        "glass_transition_temperature": None,
        "moisture": "REFERENCE",
        "chemical": "NONE_DECLARED",
        "load_case_name": "LC-1",
        "time_effect_category": category,
        "source_reference_condition": "UNKNOWN",
    }


def test_catalog_is_exact_source_bound_data_not_a_qualification() -> None:
    response = call("GET", "/api/v1/frp-materials/catalog")
    assert response.status_code == 200
    records = response.json()["records"]
    assert len(records) == 2
    assert {item["company"] for item in records} == {"ICE"}
    assert [item["resin"] for item in records] == [
        "ISOPHTHALIC_POLYESTER",
        "VINYL_ESTER",
    ]
    assert all(len(item["properties"]) == 16 for item in records)
    assert all(item["qualification"] != "QUALIFIED" for item in records)
    assert all(item["missing"] for item in records)
    assert (
        next(
            item["original"]
            for item in records[0]["properties"]
            if item["id"] == "tensile_strength_L"
        )
        == "33"
    )


def test_single_bolt_changes_native_tension_check_and_retains_source_gate() -> None:
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    legacy = cast(dict[str, Any], build_api_payload("P1"))
    output: list[dict[str, Any]] = []
    for record in records:
        body = {
            "contract": "MAT1-SINGLE-BOLT-RC0",
            "legacy_request": legacy,
            "assignments": {
                "default_material": selection(record),
                "default_conditions": condition(legacy["time_effect_category"]),
            },
        }
        response = call("POST", "/api/v1/frp-materials/single-bolt/design-check", body)
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] == "SOURCE_REQUIRED"
        assert result["design_check_performed"] is True
        assert "TG_REQUIRED" in result["material_issues"]
        output.append(result)

    def resistance(result: dict[str, Any], limit: str) -> Decimal:
        checks = result["native_design"]["results"]
        item = next(check for check in checks if check["plan"]["limit_state"] == limit)
        return Decimal(item["design_resistance"]["value"])

    assert resistance(output[1], "NET_SECTION_TENSION") > resistance(
        output[0], "NET_SECTION_TENSION"
    )
    assert resistance(output[1], "PIN_BEARING") == resistance(output[0], "PIN_BEARING")
    assert records[1]["id"] in str(output[1]["native_design"]["material_assignments"])


def test_forged_authority_and_conflicting_legacy_factor_are_rejected() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = cast(dict[str, Any], build_api_payload("P1"))
    base: dict[str, Any] = {
        "contract": "MAT1-SINGLE-BOLT-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition(legacy["time_effect_category"]),
        },
    }
    forged = deepcopy(base)
    forged["assignments"]["default_material"]["qualification"] = "QUALIFIED"
    assert call("POST", "/api/v1/frp-materials/single-bolt/design-check", forged).status_code == 422
    dual = deepcopy(base)
    dual["legacy_request"]["end_use_factors"]["cm"] = "0.75"
    response = call("POST", "/api/v1/frp-materials/single-bolt/design-check", dual)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MAT1_DUAL_END_USE_FACTORS"


def test_multirow_uses_the_new_record_and_rejects_unproved_layer_independence() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][1]
    legacy = cast(dict[str, Any], multirow_payload())
    body: dict[str, Any] = {
        "contract": "MAT1-MULTI-ROW-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition(legacy["time_effect_category"]),
        },
    }
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert response.status_code == 200
    result = response.json()
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert record["id"] in str(result["native_design"])
    other = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    changed = deepcopy(body)
    changed["legacy_request"]["layers"].append(
        {
            **changed["legacy_request"]["layers"][0],
            "layer_id": "LAYER-2",
            "component_id": "COMPONENT-2",
        }
    )
    changed["assignments"]["material_overrides"] = {"COMPONENT-2": selection(other)}
    rejected = call("POST", "/api/v1/frp-materials/multi-row/design-check", changed)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == (
        "MAT1_MULTIROW_LINKED_LAYER_MATERIAL_OR_CONDITIONS_REQUIRED"
    )


def test_native_clip_angle_family_consumes_mat1_properties() -> None:
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    designs: list[dict[str, Any]] = []
    for record in records:
        response = call(
            "POST",
            "/api/v1/frp-materials/family/design-check",
            {
                "contract": "MAT1-FAMILY-RC0",
                "family_id": "clip-angle",
                "legacy_request": build_clip_angle_payload(),
                "assignments": {
                    "default_material": selection(record),
                    "default_conditions": condition("WIND_TORNADO_SEISMIC"),
                },
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["overall_status"] == "SOURCE_REQUIRED"
        assert result["material_ledgers"]
        assert record["id"] in str(result["client_design"])
        designs.append(result)

    def first_row_tension(result: dict[str, Any]) -> Decimal:
        interface = result["client_design"]["result"]["interface_b"]
        checks = interface["resistance"]["calculation_result"]["results"]
        return Decimal(
            next(
                check["design_resistance"]["value"]
                for check in checks
                if check["limit_state"] == "FIRST_ROW_NET_TENSION"
                and check["design_resistance"] is not None
            )
        )

    assert first_row_tension(designs[1]) > first_row_tension(designs[0])


def test_ssmc_material_data_keeps_analytical_source_gates_closed() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = {
        "physical": illustrative_ssmc().model_dump(mode="json"),
        "action": {
            "basis": "FACTORED_LRFD",
            "combination_id": "LC-1",
            "combination_source": "TEST_CASE",
            "already_factored": True,
            "time_effect_category": "OTHER_LIVE",
            "time_effect_reference": "TEST_REFERENCE",
        },
        "single_lap": {
            "external_actions_at_faying_interface": True,
            "independent_normal_force": {"value": "0", "unit": "N"},
            "independent_out_of_plane_moment": {"value": "0", "unit": "N-mm"},
            "imposed_separation": False,
            "non_contact_gap": False,
            "friction_or_preload_credit": False,
            "miter_bearing_credit": False,
        },
    }
    response = call(
        "POST",
        "/api/v1/frp-materials/stair-stringer-miter/analytical-design-check",
        {
            "contract": "MAT1-SSMC-ANALYTICAL-RC0",
            "legacy_request": legacy,
            "assignments": {
                "default_material": selection(record),
                "default_conditions": condition("OTHER_LIVE"),
            },
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert result["client_design"]["whole_connection_status"] == "ENGINEERING_REVIEW_REQUIRED"
    assert {item["component_id"] for item in result["material_ledgers"]} == {
        "HORIZONTAL_STRINGER",
        "INCLINED_STRINGER",
        "MITER_WEB_PLATE",
    }
    assert "SSMC_EXACT_PLATE_AND_MEMBER_PATH_SOURCE_BINDINGS_REQUIRED" in result["material_issues"]


def test_factor_endpoint_distinguishes_catalog_and_session_data_without_design() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    base: dict[str, Any] = {
        "contract": "MAT1-FACTOR-RC0",
        "material": selection(record),
        "conditions": condition("OTHER_LIVE"),
        "component_id": "WEB_PLATE",
        "property_ids": ["tensile_strength_L", "tensile_modulus_L"],
    }
    result = call("POST", "/api/v1/frp-materials/factor-candidates", base)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["design_check_performed"] is False
    assert data["result_status"] == "SOURCE_REQUIRED"
    assert data["ledgers"][0]["original"] == "33"
    assert data["ledgers"][0]["lambda_factor"] == "0.8"
    assert data["ledgers"][1]["lambda_factor"] is None
    custom = deepcopy(base)
    custom["material"] = {
        "kind": "SESSION",
        "id": "SESSION:api-test",
        "revision": "1",
        "display_name": "Synthetic coupon",
        "company": "Test only",
        "resin": "VINYL_ESTER",
        "properties": {
            "tensile_strength_L": {
                "label": "Tension",
                "symbol": "Ft,L",
                "value": "42",
                "unit": "ksi",
                "basis": "CHARACTERISTIC",
            }
        },
    }
    custom["property_ids"] = ["tensile_strength_L"]
    result = call("POST", "/api/v1/frp-materials/factor-candidates", custom)
    assert result.status_code == 200, result.text
    assert result.json()["ledgers"][0]["original"] == "42"
    assert result.json()["ledgers"][0]["record_id"] == "SESSION:api-test"


@pytest.mark.parametrize(
    ("mutation", "status"),
    [
        ("max_below_sustained", 422),
        ("blank_load_case", 422),
        ("blank_component", 422),
        ("no_properties", 422),
        ("duplicate_property", 422),
        ("unknown_property", 422),
        ("forged_catalog_revision", 422),
        ("forged_qualification", 422),
        ("nonfinite_temperature", 422),
    ],
)
def test_factor_endpoint_rejects_invalid_data_and_client_authority(
    mutation: str,
    status: int,
) -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    body: dict[str, Any] = {
        "contract": "MAT1-FACTOR-RC0",
        "material": selection(record),
        "conditions": condition("OTHER_LIVE"),
        "component_id": "PLATE",
        "property_ids": ["tensile_strength_L"],
    }
    if mutation == "max_below_sustained":
        body["conditions"]["maximum_temperature"]["value"] = "89"
    elif mutation == "blank_load_case":
        body["conditions"]["load_case_name"] = " "
    elif mutation == "blank_component":
        body["component_id"] = " "
    elif mutation == "no_properties":
        body["property_ids"] = []
    elif mutation == "duplicate_property":
        body["property_ids"] *= 2
    elif mutation == "unknown_property":
        body["property_ids"] = ["UNSUPPLIED"]
    elif mutation == "forged_catalog_revision":
        body["material"]["revision"] = "FORGED"
    elif mutation == "forged_qualification":
        body["material"]["qualification"] = "QUALIFIED"
    elif mutation == "nonfinite_temperature":
        body["conditions"]["sustained_temperature"]["value"] = "NaN"
    response = call("POST", "/api/v1/frp-materials/factor-candidates", body)
    assert response.status_code == status, (mutation, response.text)


def test_tee_uses_canonical_participant_material_for_both_interfaces() -> None:
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    body: dict[str, Any] = {
        "contract": "MAT1-TEE-RC0",
        "legacy_request": native_payload("tee-connector"),
        "assignments": {
            "default_material": selection(records[0]),
            "default_conditions": condition("WIND_TORNADO_SEISMIC"),
        },
    }
    response = call("POST", "/api/v1/frp-materials/tee-connector/design-check", body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert {item["component_id"] for item in result["material_ledgers"]} == {
        "tee-brace",
        "tee-connector",
        "tee-support",
    }
    brace = next(
        item
        for item in result["material_ledgers"]
        if item["component_id"] == "tee-brace" and item["property_id"] == "tensile_strength_L"
    )
    connector = next(
        item
        for item in result["material_ledgers"]
        if item["component_id"] == "tee-connector" and item["property_id"] == "tensile_strength_L"
    )
    assert brace["original"] == "33"
    assert connector["original"] == "33"
    assert "MAT1_UNMAPPED_PHYSICAL_OWNER" not in str(result)
    incompatible = deepcopy(body)
    incompatible["assignments"]["material_overrides"] = {
        "tee-brace": selection(records[1]),
    }
    linked = call("POST", "/api/v1/frp-materials/tee-connector/design-check", incompatible)
    assert linked.status_code == 422
    assert linked.json()["detail"]["code"] == "MAT1_TEE_LINKED_INTERFACE_LAYER_MATERIAL_REQUIRED"
    invalid = deepcopy(body)
    invalid["assignments"]["material_overrides"] = {"not-a-component": selection(records[1])}
    rejected = call("POST", "/api/v1/frp-materials/tee-connector/design-check", invalid)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "MAT1_UNKNOWN_TEE_PHYSICAL_COMPONENT_OVERRIDE"


def test_owner_discovery_and_design_reject_unknown_family_and_invalid_preview() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    unknown = call(
        "POST",
        "/api/v1/frp-materials/family/owners",
        {
            "contract": "MAT1-OWNER-PREVIEW-RC0",
            "family_id": "not-a-family",
            "legacy_request": {},
        },
    )
    assert unknown.status_code == 422
    bad_preview = call(
        "POST",
        "/api/v1/frp-materials/family/owners",
        {
            "contract": "MAT1-OWNER-PREVIEW-RC0",
            "family_id": "tee-connector",
            "legacy_request": {},
        },
    )
    assert bad_preview.status_code == 422
    body: dict[str, Any] = {
        "contract": "MAT1-FAMILY-RC0",
        "family_id": "single-bolt",
        "legacy_request": native_payload("single-bolt"),
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition("OTHER_LIVE"),
        },
    }
    assert call("POST", "/api/v1/frp-materials/family/design-check", body).status_code == 422
    body["family_id"] = "not-a-family"
    assert call("POST", "/api/v1/frp-materials/family/design-check", body).status_code == 422


def test_single_bolt_rejects_legacy_material_and_case_conflicts() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = cast(dict[str, Any], build_api_payload("P1"))
    base: dict[str, Any] = {
        "contract": "MAT1-SINGLE-BOLT-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition(legacy["time_effect_category"]),
        },
    }
    changed = deepcopy(base)
    changed["legacy_request"]["material_snapshots"][0]["id"] = "FORGED"
    assert (
        call("POST", "/api/v1/frp-materials/single-bolt/design-check", changed).status_code == 422
    )
    changed = deepcopy(base)
    changed["assignments"]["default_conditions"]["time_effect_category"] = "DEAD_ONLY"
    assert (
        call("POST", "/api/v1/frp-materials/single-bolt/design-check", changed).json()["detail"][
            "code"
        ]
        == "MAT1_DUAL_TIME_CATEGORY"
    )
    changed = deepcopy(base)
    changed["assignments"]["material_overrides"] = {"UNKNOWN": selection(record)}
    assert "MAT1_UNKNOWN_PHYSICAL_COMPONENT_OVERRIDE" in str(
        call("POST", "/api/v1/frp-materials/single-bolt/design-check", changed).json()
    )
    owner = legacy["material_assignments"][0]
    key = ":".join(
        (owner["participant_id"], owner["physical_element_id"], owner["material_region_id"])
    )
    changed = deepcopy(base)
    changed["assignments"]["condition_overrides"] = {
        key: condition("DEAD_ONLY"),
    }
    assert "MAT1_ONE_LOAD_CASE_CANNOT_HAVE_CONFLICTING_TIME_CATEGORIES" in str(
        call("POST", "/api/v1/frp-materials/single-bolt/design-check", changed).json()
    )


def test_multirow_rejects_dual_factor_case_and_unknown_layer() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = cast(dict[str, Any], multirow_payload())
    base: dict[str, Any] = {
        "contract": "MAT1-MULTI-ROW-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition(legacy["time_effect_category"]),
        },
    }
    changed = deepcopy(base)
    changed["assignments"]["material_overrides"] = {"UNKNOWN": selection(record)}
    assert "MAT1_UNKNOWN_PHYSICAL_LAYER" in str(
        call("POST", "/api/v1/frp-materials/multi-row/design-check", changed).json()
    )
    changed = deepcopy(base)
    changed["assignments"]["default_conditions"]["time_effect_category"] = "DEAD_ONLY"
    assert "MAT1_DUAL_TIME_CATEGORY" in str(
        call("POST", "/api/v1/frp-materials/multi-row/design-check", changed).json()
    )
    changed = deepcopy(base)
    changed["legacy_request"]["layers"][0]["end_use_factors"]["cm"] = "0.75"
    assert "MAT1_DUAL_END_USE_FACTORS" in str(
        call("POST", "/api/v1/frp-materials/multi-row/design-check", changed).json()
    )


def test_scope_owner_binding_requires_preview_and_one_load_case() -> None:
    from frp_master_connection.application.mat1_materials import predefined_catalog

    record = predefined_catalog()[0]
    resolved = mat1_api.resolve_conditions(
        mat1_api.MaterialConditionsDTO.model_validate(condition("WIND_TORNADO_SEISMIC"))
    )
    scope = MAT1Scope((record, resolved), {})
    with pytest.raises(ValueError, match="PHYSICAL_OWNERS_NOT_BOUND"):
        mat1_api.complete_owner_ledger(scope)
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    body: dict[str, Any] = {
        "contract": "MAT1-TEE-RC0",
        "legacy_request": native_payload("tee-connector"),
        "assignments": {
            "default_material": selection(records[0]),
            "default_conditions": condition("WIND_TORNADO_SEISMIC"),
            "condition_overrides": {"tee-brace": condition("DEAD_ONLY")},
        },
    }
    response = call("POST", "/api/v1/frp-materials/tee-connector/design-check", body)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "MAT1_ONE_LOAD_CASE_CANNOT_HAVE_CONFLICTING_TIME_CATEGORIES"
    )


def test_generic_route_rejects_unknown_assignment_and_missing_numeric_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    body: dict[str, Any] = {
        "contract": "MAT1-FAMILY-RC0",
        "family_id": "clip-angle",
        "legacy_request": build_clip_angle_payload(),
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition("WIND_TORNADO_SEISMIC"),
            "material_overrides": {"not-a-physical-owner": selection(record)},
        },
    }
    unknown = call("POST", "/api/v1/frp-materials/family/design-check", body)
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "MAT1_UNKNOWN_FAMILY_PHYSICAL_COMPONENT_OVERRIDE"

    class SyntheticNative:
        def preview(self, _request: object) -> object:
            return object()

        def design(self, _request: object) -> object:
            return SimpleNamespace(assembly_status="PASS")

    def bind_synthetic(scope: object, _family: str, _preview: object) -> None:
        cast(MAT1Scope, scope).canonical_owners = frozenset({"FRP_OWNER"})

    with monkeypatch.context() as patcher:
        patcher.setattr(mat1_api, "FAMILIES", {"synthetic-missing-adapter": SyntheticNative()})
        patcher.setattr(mat1_api, "bind_physical_owners", bind_synthetic)
        synthetic = deepcopy(body)
        synthetic["family_id"] = "synthetic-missing-adapter"
        synthetic["legacy_request"] = {}
        synthetic["assignments"].pop("material_overrides")
        result = call("POST", "/api/v1/frp-materials/family/design-check", synthetic)
    assert result.status_code == 422
    assert result.json()["detail"]["code"] == "MAT1_FAMILY_MATERIAL_CONSUMER_UNIMPLEMENTED"


def test_ssmc_mat1_case_and_owner_conflicts_keep_method_gates_closed() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    body: dict[str, Any] = {
        "contract": "MAT1-SSMC-ANALYTICAL-RC0",
        "legacy_request": {
            "physical": illustrative_ssmc().model_dump(mode="json"),
            "action": {
                "basis": "FACTORED_LRFD",
                "combination_id": "LC-1",
                "combination_source": "TEST_CASE",
                "already_factored": True,
                "time_effect_category": "OTHER_LIVE",
                "time_effect_reference": "TEST_REFERENCE",
            },
            "single_lap": {
                "external_actions_at_faying_interface": True,
                "independent_normal_force": {"value": "0", "unit": "N"},
                "independent_out_of_plane_moment": {"value": "0", "unit": "N-mm"},
                "imposed_separation": False,
                "non_contact_gap": False,
                "friction_or_preload_credit": False,
                "miter_bearing_credit": False,
            },
        },
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition("OTHER_LIVE"),
        },
    }
    mismatch = deepcopy(body)
    mismatch["assignments"]["default_conditions"]["time_effect_category"] = "DEAD_ONLY"
    response = call(
        "POST", "/api/v1/frp-materials/stair-stringer-miter/analytical-design-check", mismatch
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MAT1_DUAL_TIME_CATEGORY"
    unknown = deepcopy(body)
    unknown["assignments"]["material_overrides"] = {"UNKNOWN": selection(record)}
    response = call(
        "POST", "/api/v1/frp-materials/stair-stringer-miter/analytical-design-check", unknown
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MAT1_UNKNOWN_SSMC_PHYSICAL_COMPONENT_OVERRIDE"


@pytest.mark.parametrize("family", tuple(FAMILIES))
def test_every_family_exposes_physical_owners_without_resistance(family: str) -> None:
    response = call(
        "POST",
        "/api/v1/frp-materials/family/owners",
        {
            "contract": "MAT1-OWNER-PREVIEW-RC0",
            "family_id": family,
            "legacy_request": native_payload(family),
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["contract"] == "MAT1-OWNER-PREVIEW-RC0"
    assert result["family_id"] == family
    assert result["design_check_performed"] is False
    assert result["owners"] == sorted(set(result["owners"]))
    assert result["owners"]


@pytest.mark.parametrize(
    "family",
    tuple(
        family
        for family in FAMILIES
        if family not in {"single-bolt", "multi-row", "tee-connector", "stair-stringer-miter"}
    ),
)
def test_every_generic_family_returns_source_gated_material_trace(family: str) -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    response = call(
        "POST",
        "/api/v1/frp-materials/family/design-check",
        {
            "contract": "MAT1-FAMILY-RC0",
            "family_id": family,
            "legacy_request": native_payload(family),
            "assignments": {
                "default_material": selection(record),
                "default_conditions": condition("WIND_TORNADO_SEISMIC"),
            },
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert result["material_ledgers"]
    assert result["design_check_performed"] is True
    assert result["client_design"]
    if family in {
        "direct-side-lap-concrete",
        "column-base-web-angles",
        "angle-column-two-leg-moment-base",
        "wi-rhs-srs-column-moment-base",
    }:
        assert "MAT1_NATIVE_RESISTANCE_NOT_EVALUATED_FOR_THIS_REQUEST" in result["material_issues"]
    if family == "wi-major-axis-moment-splice":
        other = call("GET", "/api/v1/frp-materials/catalog").json()["records"][1]
        mismatch = call(
            "POST",
            "/api/v1/frp-materials/family/design-check",
            {
                "contract": "MAT1-FAMILY-RC0",
                "family_id": family,
                "legacy_request": native_payload(family),
                "assignments": {
                    "default_material": selection(record),
                    "material_overrides": {
                        "NEGATIVE_WEB_SPLICE_PLATE": selection(other),
                    },
                    "default_conditions": condition("WIND_TORNADO_SEISMIC"),
                },
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["detail"]["code"] == (
            "MAT1_SYMMETRIC_WEB_SPLICE_PLATE_MATERIALS_MUST_MATCH"
        )
