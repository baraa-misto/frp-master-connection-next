"""OR1-03/04/07: material authority, numerical changes, and exact-once factors."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any, cast

from tests.api.test_mat1_routes import call, condition, selection
from tests.application.test_direct_f1_safety import _direct_payload, _one_row_payload


def _session(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "SESSION",
        "id": "SESSION:OR1-CUSTOM-COUPON",
        "revision": "1",
        "display_name": "OR1 custom coupon",
        "company": "Owner laboratory",
        "resin": "OTHER",
        "properties": {
            item["id"]: {
                "label": item["label"],
                "symbol": item["symbol"],
                "value": "41" if item["id"] == "tensile_strength_L" else item["original"],
                "unit": item["unit"],
                "basis": item["basis"],
            }
            for item in record["properties"]
        },
        "copied_from": record["id"],
    }


def test_ice_resins_and_custom_change_executed_direct_net_tension_only() -> None:
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    legacy = cast(dict[str, Any], _one_row_payload(1))
    source_selections = [selection(records[0]), selection(records[1]), _session(records[0])]
    measured: list[tuple[Decimal, Decimal, Decimal, Decimal, str]] = []
    for selected in source_selections:
        body = {
            "contract": "MAT1-MULTI-ROW-RC0",
            "legacy_request": legacy,
            "assignments": {
                "default_material": selected,
                "default_conditions": condition(legacy["time_effect_category"]),
            },
        }
        response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["overall_status"] == "SOURCE_REQUIRED"
        source = result["material_sources"]["default"]
        assert source["id"] == selected["id"]
        assert source["resin"] == (
            selected["resin"] if selected["kind"] == "SESSION" else records[len(measured)]["resin"]
        )
        native = result["native_design"]
        single = native["automatic_group_mode_integration"]["direct_single_row_result"]
        checks = single["checks"]
        net = next(
            item
            for item in checks
            if item["limit_state"] == "SINGLE_ROW_NET_TENSION" and item["layer_id"] == "layer-A"
        )
        bearing = next(
            item
            for item in native["automatic_handoff_results"][0]["checks"]
            if item["family"] == "PIN_BEARING"
        )
        assert net["numerical_comparison"] == "PASS"
        ledger = next(
            item
            for item in result["material_ledgers"]
            if item["property_id"] == "tensile_strength_L"
        )
        assert ledger["record_id"] == selected["id"]
        measured.append(
            (
                Decimal(net["design_resistance"]["value"]),
                Decimal(net["demand"]["value"]),
                Decimal(net["utilization"]),
                Decimal(bearing["resistance_result"]["design_resistance"]["value"]),
                source["content_digest"],
            )
        )
    iso, vinyl, custom = measured
    assert iso[0] < vinyl[0] < custom[0]
    assert iso[1] == vinyl[1] == custom[1]
    assert iso[2] > vinyl[2] > custom[2]
    assert iso[3] == vinyl[3] == custom[3]
    assert len({iso[4], vinyl[4], custom[4]}) == 3


def test_multirow_direct_adjusts_bearing_once_and_keeps_fnt_source_pending() -> None:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = cast(dict[str, Any], _direct_payload())
    ordinary = condition(legacy["time_effect_category"])
    wet = deepcopy(ordinary)
    wet["moisture"] = "SUSTAINED_MOISTURE"
    measured: list[tuple[Decimal, dict[str, Any], dict[str, Any]]] = []
    for conditions in (ordinary, wet):
        body = {
            "contract": "MAT1-MULTI-ROW-RC0",
            "legacy_request": legacy,
            "assignments": {
                "default_material": selection(record),
                "default_conditions": conditions,
            },
        }
        response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["fastener_source"]["fnt_state"] == "SOURCE_PENDING"
        ledger = next(
            item
            for item in result["material_ledgers"]
            if item["component_id"] == "member-a" and item["property_id"] == "bearing_strength_L"
        )
        checks = result["native_design"]["automatic_handoff_results"][0]["checks"]
        bearing = next(
            item
            for item in checks
            if item["family"] == "PIN_BEARING" and item["availability"] == "CALCULATED"
        )
        assert any(
            item["availability"] == "SOURCE_DATA_PENDING"
            for item in checks
            if item["family"] == "BOLT_SHEAR"
        )
        trace = bearing["resistance_result"]["factor_trace"]
        assert trace["property_traces"][0]["cm"] == "1"
        assert trace["property_traces"][0]["ct"] == "1"
        assert trace["property_traces"][0]["cch"] == "1"
        assert Decimal(ledger["adjusted_candidate"]) == (
            Decimal(ledger["original"])
            * Decimal(ledger["cm"])
            * Decimal(ledger["ct"])
            * Decimal(ledger["cch"])
        )
        resistance = Decimal(bearing["resistance_result"]["design_resistance"]["value"])
        measured.append((resistance, ledger, trace))
    assert measured[0][1]["cm"] == "1"
    assert measured[1][1]["cm"] == "0.75"
    assert measured[1][0] == measured[0][0] * Decimal("0.75")
    assert measured[1][2]["c_lap"] == "0.6"
    assert measured[1][2]["phi"] == "0.6"
    assert measured[1][2]["lambda_factor"] == "1"
