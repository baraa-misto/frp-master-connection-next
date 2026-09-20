"""Independent declared inventory versus actual native routes, selectors and modes."""

import copy
import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.connector_materials import mode_contract
from frp_master_connection.config import ApplicationEnvironment, AppSettings

ROOT = Path(__file__).parents[3]


def inventory() -> list[dict[str, Any]]:
    return cast(
        list[dict[str, Any]],
        json.loads(
            (ROOT / "docs/engineering/CME_1_FAMILY_PROVIDER_MIGRATION_INVENTORY.json").read_text()
        )["families"],
    )


def check_inventory(rows: list[dict[str, Any]], actual: dict[str, dict[str, Any]]) -> None:
    declared = {r["route_id"]: r for r in rows}
    assert len(declared) == len(rows), "duplicate material policy"
    assert declared.keys() == actual.keys(), "undeclared product material policy"
    for route, spec in actual.items():
        assert declared[route]["product_id"] == spec["product_id"]
        assert declared[route]["declared_native_modes"] == spec["modes"], (
            "undeclared mode material policy"
        )
        assert declared[route]["primary_member_policy"] == "FRP_ONLY_NATIVE_REGION_LW_CW_TT"
        assert declared[route]["qualification_policy"]
        assert declared[route]["rollout_wave"]


def actual_contracts() -> dict[str, dict[str, Any]]:
    return {
        route: {"product_id": family.product_id, "modes": mode_contract(family.schema)}
        for route, family in FAMILIES.items()
    }


def test_every_runtime_product_and_finite_mode_has_a_declared_material_policy() -> None:
    check_inventory(inventory(), actual_contracts())
    app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    actual_routes = {
        p.split("/")[-2]
        for p in app.openapi()["paths"]
        if p.startswith("/api/v1/calculations/") and p.endswith("/preview")
    }
    assert actual_routes == set(FAMILIES)
    selectors = "\n".join(
        (ROOT / f"frontend/src/workspace/{name}ConnectionsWorkspace.tsx").read_text()
        for name in ("Shear", "Moment")
    )
    product_ids = set(re.findall(r'<option value="([A-Z_]+)"', selectors))
    assert product_ids == {f.product_id for f in FAMILIES.values()}


@pytest.mark.parametrize(
    "mutation", ["new_product", "new_mode", "removed_policy", "duplicate", "wrong_product"]
)
def test_future_product_or_mode_without_policy_fails(mutation: str) -> None:
    actual = actual_contracts()
    rows = copy.deepcopy(inventory())
    if mutation == "new_product":
        actual["future"] = {"product_id": "FUTURE", "modes": {}}
    elif mutation == "new_mode":
        actual["tee-connector"]["modes"]["future_mode"] = "UNDECLARED"
    elif mutation == "removed_policy":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(rows[0])
    else:
        rows[0]["product_id"] = "WRONG"
    with pytest.raises(AssertionError):
        check_inventory(rows, actual)
