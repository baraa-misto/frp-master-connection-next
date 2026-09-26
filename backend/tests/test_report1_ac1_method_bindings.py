"""Other executed methods bind real operands, including varied values."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.reporting.method_records import EXECUTED_METHODS, executed_records
from frp_master_connection.reporting.method_substitutions import (
    _BINDINGS,
    _shown,
    native_method_substitution,
)
from frp_master_connection.reporting.units import display_quantity, resolved_display_units
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload
from tests.test_report1_ac1_all_modes import _ssmc_payload


@pytest.fixture(scope="module")
def flange_record() -> dict[str, Any]:
    payload = native_payload("wi-major-axis-moment-splice")

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/calculations/wi-major-axis-moment-splice/design-check", json=payload
            )
            assert response.status_code == 200
            body: dict[str, Any] = response.json()
            return body

    native = asyncio.run(run())
    return executed_records(native["result"])[
        "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
    ][1]


def test_every_reviewed_executed_method_has_a_numerical_binding() -> None:
    assert set(_BINDINGS) == set(EXECUTED_METHODS)


def test_same_unit_native_operand_is_readable_without_losing_exact_appendix_value() -> None:
    source = {"value": "0.083333333333333333333333333333", "unit": "in4"}
    assert display_quantity(source, "US_CUSTOMARY") == "0.0833333333333 in4"
    assert source["value"] == "0.083333333333333333333333333333"


def test_native_method_binding_changes_with_consumed_native_value(
    flange_record: dict[str, Any],
) -> None:
    method = "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
    original = native_method_substitution(method, flange_record, "US_CUSTOMARY")
    changed = deepcopy(flange_record)
    changed["outer_force"]["value"] = "123.456"
    updated = native_method_substitution(method, changed, "US_CUSTOMARY")
    assert original != updated
    assert "F_o = 123.456 kip" in updated
    assert "F_o = 123.456 kip" not in original
    si = native_method_substitution(method, flange_record, "SI")
    assert " kN" in si
    assert " kip" not in si


def test_missing_executed_method_operand_fails_closed(flange_record: dict[str, Any]) -> None:
    method = "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
    missing = deepcopy(flange_record)
    del missing["outer_force"]
    with pytest.raises(ValueError, match="lacks native operand outer_force"):
        native_method_substitution(method, missing, "SI")
    with pytest.raises(ValueError, match="no REPORT1 numerical binding"):
        native_method_substitution("UNMAPPED_EXECUTED_METHOD", flange_record, "SI")


def test_native_operand_and_nested_display_edges(flange_record: dict[str, Any]) -> None:
    method = "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
    missing = deepcopy(flange_record)
    missing["outer_force"] = None
    with pytest.raises(ValueError, match="lacks native operand outer_force"):
        native_method_substitution(method, missing, "SI")
    with pytest.raises(ValueError, match="no physical unit"):
        _shown({"numerator": "1", "denominator": "2"}, "SI")
    assert _shown([{"value": "1000", "unit": "N"}], "SI") == "(1 kN)"


def test_display_units_preserve_malformed_and_dimensionless_native_values() -> None:
    assert resolved_display_units({"source_length_unit": "mm"}, {}, "INHERIT") == "SI"
    assert display_quantity({"value": "0.5", "unit": "1"}, "SI") == "0.5 1"
    assert display_quantity({"value": "bad", "unit": "mm"}, "SI") == "bad mm"


@pytest.fixture(scope="module")
def every_method_record() -> dict[str, dict[str, Any]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []
    for family in FAMILIES:
        if family == "single-bolt":
            payload = build_api_payload("J1-T")
            route = "/api/v1/calculations/single-bolt/evaluate"
        elif family == "stair-stringer-miter":
            payload = _ssmc_payload()
            route = "/api/v1/calculations/stair-stringer-miter/analytical-design-check"
        else:
            payload = native_payload(family)
            route = f"/api/v1/calculations/{family}/design-check"
        cases.append((family, route, payload))

    async def run() -> dict[str, dict[str, Any]]:
        collected: dict[str, dict[str, Any]] = {}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test", timeout=120
        ) as client:
            for family, route, payload in cases:
                response = await client.post(route, json=payload)
                assert response.status_code == 200, family
                body: dict[str, Any] = response.json()
                for method, (_, record) in executed_records(body.get("result", body)).items():
                    collected.setdefault(method, record)
        return collected

    return asyncio.run(run())


@pytest.mark.parametrize("method", tuple(EXECUTED_METHODS))
def test_each_executed_method_substitution_responds_to_a_varied_native_operand(
    every_method_record: dict[str, dict[str, Any]], method: str
) -> None:
    record = every_method_record[method]
    original = native_method_substitution(method, record, "US_CUSTOMARY")
    changed = deepcopy(record)
    first_path = _BINDINGS[method][0][1]
    parts = first_path.replace("[", ".").replace("]", "").split(".")
    owner: Any = changed
    for part in parts[:-1]:
        owner = owner[int(part)] if isinstance(owner, list) else owner[part]
    last = parts[-1]
    target = owner[int(last)] if isinstance(owner, list) else owner[last]
    if isinstance(target, dict) and "value" in target:
        target["value"] = "98765.4321"
    elif isinstance(target, dict) and "numerator" in target:
        target["numerator"] = str(int(target["numerator"]) + int(target["denominator"]) * 12345)
    elif isinstance(target, dict):
        target["x"]["value"] = "98765.4321"
    elif isinstance(owner, list):
        owner[int(last)] = "98765.4321"
    else:
        owner[last] = "98765.4321"
    assert native_method_substitution(method, changed, "US_CUSTOMARY") != original
