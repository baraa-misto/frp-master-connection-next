"""Owner-corrected I11: each native unit path has its own immutable parent oracle."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pydantic import JsonValue
from tests.api.test_connector_materials import http, native_payload

from frp_master_connection.api.angle_column_moment_base import AngleBaseRequestDTO
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.wi_wall_moment_mapping import serialize_wall_moment_value
from frp_master_connection.application.multi_member_tee_orchestration import (
    MultiMemberTeePreviewResult,
)
from frp_master_connection.application.stainless_connection_design import (
    evaluate_stainless_connection,
)
from frp_master_connection.application.stainless_family_activation import ROUTES, STACKS
from frp_master_connection.application.tee_orchestration import TeeConnectorPreviewResult
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    default_angle_column_moment_base_request,
)

ORACLE = Path(__file__).parents[1] / "golden/cme3_native_unit_parent_oracles.json"
UNITS = {"in": "mm", "kip": "kN", "kip-in": "kN-mm", "ksi": "MPa"}


def equivalent_si(value: JsonValue) -> JsonValue:
    """Re-author only with the accepted native conversion helper, not rounded floats."""
    if isinstance(value, list):
        return [equivalent_si(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {k: equivalent_si(v) for k, v in value.items()}
    unit = value.get("unit")
    if isinstance(unit, str) and unit in UNITS:
        for key in ("value", "x", "y", "z", "l", "v", "t"):
            scalar = value.get(key)
            if isinstance(scalar, str):
                result[key] = str(
                    PhysicalQuantity.of(Decimal(scalar), Unit(unit)).to(Unit(UNITS[unit])).magnitude
                )
        result["unit"] = UNITS[unit]
    if result.get("unit_system") == "US_CUSTOMARY":
        result["unit_system"] = "SI"
    if result.get("source_length_unit") == "in":
        result["source_length_unit"] = "mm"
    return result


def exact_json_digest(value: object) -> str:
    # Only object key order is ignored. No Decimal/numeric/string normalization.
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@pytest.mark.parametrize("route", tuple(ROUTES))
@pytest.mark.parametrize("units", ["US", "SI"])
def test_i11_each_native_path_matches_its_exact_frozen_parent(route: str, units: str) -> None:
    oracle = json.loads(ORACLE.read_text())
    assert oracle["parent"] == "2e33c562fe131cef4526390c151be024a8a734a8"
    # This frozen builder still defines the original input. The current /defaults
    # endpoint intentionally serves a separately authorized startup configuration.
    payload = (
        AngleBaseRequestDTO.model_validate(
            serialize_wall_moment_value(default_angle_column_moment_base_request())
        ).model_dump(mode="json")
        if route == "angle-column-two-leg-moment-base"
        else native_payload(route)
    )
    if units == "SI":
        payload = cast(dict[str, JsonValue], equivalent_si(payload))
    row = oracle["paths"][route][units]
    assert exact_json_digest(payload) == row["input"]
    for operation in ("preview", "design-check"):
        response = http("POST", f"/api/v1/calculations/{route}/{operation}", payload)
        assert response.status_code == row[operation]["http"]
        assert exact_json_digest(response.json()) == row[operation]["sha256"]
    native = FAMILIES[route].preview(payload)
    first = evaluate_stainless_connection(route, native)
    assert first == evaluate_stainless_connection(route, native)
    assert {b.binding.form for b in first.bodies} == {ROUTES[route]}
    # A display formatter has no write/execute path into activation state.
    for unit in (Unit.IN, Unit.MM):
        PhysicalQuantity.of("1", Unit.IN).to(unit)
        assert evaluate_stainless_connection(route, native) == first
        assert list(STACKS[ROUTES[route]]) == row["stack"]


def test_i11_exact_inherited_tee_differences_are_not_erased() -> None:
    us = native_payload("tee-connector")
    si = cast(dict[str, JsonValue], equivalent_si(us))
    a = FAMILIES["tee-connector"].preview(us)
    b = FAMILIES["tee-connector"].preview(si)
    ar = evaluate_stainless_connection("tee-connector", a)
    br = evaluate_stainless_connection("tee-connector", b)
    assert (
        ar.assembly.native_identity
        == "b30c12b1eb16143ba1823d434c0d400b0b5275b4ffd88a77a350d109d1d99821"
    )
    assert (
        br.assembly.native_identity
        == "c00e25b07e55591d12c5a36e1cd534e8920dde9df011e0c968acf268ed9ddaa3"
    )
    assert ar.fingerprint != br.fingerprint
    # These are independently authored engineering paths, not display formatting.
    for preview, expected in ((a, "-101.60"), (b, "-101.59999999999999")):
        assert isinstance(preview, TeeConnectorPreviewResult)
        assert preview.interface_a.preview.automatic_demand_result is not None
        assert (
            preview.interface_a.preview.automatic_demand_result.interface_frame.origin.z.canonical_magnitude
            == Decimal(expected)
        )
    multi = native_payload("multi-member-tee")
    for payload, expected in ((multi, "0"), (equivalent_si(multi), "6.1385458290594900000E-10")):
        preview = FAMILIES["multi-member-tee"].preview(cast(dict[str, JsonValue], payload))
        assert isinstance(preview, MultiMemberTeePreviewResult)
        assert preview.slots[1].preview is not None
        assert preview.slots[1].preview.automatic_demand_result is not None
        assert preview.slots[1].preview.automatic_demand_result.scenarios[
            0
        ].residual_moment.canonical_magnitude == Decimal(expected)
