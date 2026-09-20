"""Native DCTN API sweep and exact unchanged pre-DCTN route identities."""

import hashlib
import json
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any

import pytest
from tests.api.test_angle_column_moment_base_api import TestClient
from tests.api.test_connector_materials import http, native_payload

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.double_channel_truss_node import (
    DCTNRequestDTO,
    convert_dctn_units,
    dctn_response,
    map_dctn_request,
    serialize_dctn_value,
)
from frp_master_connection.api.wi_wall_moment_mapping import serialize_wall_moment_value
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.double_channel_truss_node import (
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    default_dctn_request,
)

BASE = "/api/v1/calculations/double-channel-truss-node"
PARENT_PATH = Path(__file__).parents[1] / "golden/dctn_2_parent_response_identities.json"
PARENT = json.loads(PARENT_PATH.read_bytes())
COMBINATIONS = [
    (arrangement, vertical, diagonal)
    for arrangement in DCTNArrangement
    for vertical, diagonal in (
        ((form, form) for form in DCTNForm)
        if arrangement
        in {
            DCTNArrangement.VERTICAL_ONLY,
            DCTNArrangement.ONE_INCLINED,
            DCTNArrangement.TWO_INCLINED,
        }
        else product(DCTNForm, repeat=2)
    )
]


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_parent_evidence_is_frozen_and_all_27_combinations_are_explicit() -> None:
    assert (
        hashlib.sha256(PARENT_PATH.read_bytes()).hexdigest()
        == "d660b24e7d188ff991c570a78deaab92246f4c3ce2b56cda54330a112072b57e"
    )
    assert PARENT["baseline"] == "28b1273bc85ef71f468a18a7b97b69c27867df66"
    assert len(PARENT["routes"]) == 16
    assert len(COMBINATIONS) == len(set(COMBINATIONS)) == 27


@pytest.mark.parametrize("route", tuple(PARENT["routes"]))
def test_exact_old_preview_design_geometry_defaults_and_material_plan(route: str) -> None:
    item = PARENT["routes"][route]
    family = FAMILIES[route]
    # Reproduce the original fixture insertion order too: native Pydantic error
    # text includes dict repr for the historical unsupported preview-as-design
    # input. Sorted JSON storage must not re-author that original request.
    data = native_payload(route)
    assert data == item["input"]
    actual: dict[str, Any] = {}
    for name in ("preview", "design"):
        try:
            actual[name] = {"value": serialize_wall_moment_value(getattr(family, name)(data))}
        except Exception as error:
            actual[name] = {"exception": type(error).__name__, "message": str(error)}
    actual["assembly"] = serialize_wall_moment_value(
        canonical_material_assembly(route, family.preview(data))
    )
    response = http("GET", f"/api/v1/calculations/{route}/defaults")
    actual["defaults"] = {"status": response.status_code, "json": response.json()}
    response = http(
        "POST",
        "/api/v1/connector-materials/plan",
        {"route_id": route, "product_id": family.product_id, "native_input": data},
    )
    actual["material_plan"] = {"status": response.status_code, "json": response.json()}
    assert {key: digest(value) for key, value in actual.items()} == item["hashes"]


def test_capability_delta_is_exactly_the_one_new_no_body_route() -> None:
    current = http("GET", "/api/v1/connector-materials/capabilities").json()
    added = [
        f for f in current["result"]["families"] if f["route_id"] == "double-channel-truss-node"
    ]
    assert len(added) == 1
    assert added[0]["disposition"] == "NO_CONNECTOR_BODY"
    assert added[0]["stainless"] == "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"
    current["result"]["families"] = [
        f for f in current["result"]["families"] if f["route_id"] != "double-channel-truss-node"
    ]
    assert current == PARENT["capabilities"]


@pytest.mark.parametrize(("arrangement", "vertical", "diagonal"), COMBINATIONS)
@pytest.mark.parametrize("si", [False, True])
def test_all_27_contract_modes_both_native_unit_paths(
    arrangement: DCTNArrangement, vertical: DCTNForm, diagonal: DCTNForm, si: bool
) -> None:
    value = default_dctn_request(arrangement)
    value = replace(
        value,
        members=tuple(
            replace(m, section=replace(m.section, form=vertical if m.slot == "V" else diagonal))
            for m in value.members
        ),
    )
    dto = DCTNRequestDTO.model_validate(serialize_dctn_value(value))
    if si:
        dto = convert_dctn_units(dto, True)
    native = map_dctn_request(dto)
    client = TestClient(create_app())
    for endpoint, direct in (
        ("preview", preview_dctn(native)),
        ("design-check", design_check_dctn(native)),
    ):
        response = client.post(BASE + "/" + endpoint, json=dto.model_dump(mode="json"))
        assert response.status_code == 200, response.text
        assert response.json() == dctn_response(direct)
        assert response.json()["geometry_status"] == "VALID"
        p = response.json()["result"]["preview"]
        assert p["response"]["status"] == "QUALIFIED"
        assert p["connector_body_count"] == 0
        assert all(
            r["member_force_closes"] and r["member_moment_closes"] for r in p["response"]["rows"]
        )
        assert all(
            s["physical_bolt_count"] == 1 and s["cavity_hardware_count"] == 0
            for s in p["geometry"]["shafts"]
        )
        if endpoint == "design-check":
            assert response.json()["whole_connection_status"] == "ENGINEERING_REVIEW_REQUIRED"
            assert not response.json()["result"]["design"]["global_chord_design_evaluated"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("qualified_source", {"approved": True}),
        ("global_chord_design", True),
        ("role", "CONNECTOR_BODY"),
        ("provider", "C2_R"),
        ("capacity", "100"),
        ("side_hardware", {}),
        ("shaft_topology", "THROUGH_WI"),
        ("free_moment", "1"),
        ("torsion", "1"),
        ("transverse_force", "1"),
    ],
)
@pytest.mark.parametrize("endpoint", ["preview", "design-check"])
def test_public_request_cannot_inject_scope_or_source_authority(
    field: str, value: object, endpoint: str
) -> None:
    payload = serialize_dctn_value(default_dctn_request())
    assert isinstance(payload, dict)
    payload[field] = serialize_dctn_value(value)
    response = TestClient(create_app()).post(BASE + "/" + endpoint, json=payload)
    assert response.status_code == 422
