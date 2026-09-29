"""The shared capability contract binds every native family explicitly."""

from __future__ import annotations

from typing import Any, cast

from tests.api.test_mat1_routes import call

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.workspace_capabilities import workspace_capabilities


def test_all_native_families_have_one_controlled_capability_record() -> None:
    response = call("GET", "/api/v1/workspaces/capabilities")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == workspace_capabilities()
    assert body["contract"] == "WORKSPACE-CAPABILITIES-OR1-RC1"
    assert set(body["families"]) == set(FAMILIES)
    assert len(body["families"]) == 18
    for route_id, family in FAMILIES.items():
        record = body["families"][route_id]
        assert record["template_id"] == family.product_id
        assert record["category"] == family.category
        assert len(record["features"]) == 13


def test_direct_controls_and_moment_family_boundaries_are_explicit() -> None:
    families = cast(dict[str, dict[str, Any]], workspace_capabilities()["families"])
    direct = families["multi-row"]
    assert direct["material_assignment_mode"] == "LINKED"
    assert direct["features"]["automatic_physical_demand"] == "SUPPORTED"
    assert direct["features"]["force_only_shear"] == "SUPPORTED"
    assert direct["features"]["independent_moment_input"] == "NOT_APPLICABLE"
    assert direct["features"]["custom_fastener"] == "SUPPORTED"
    assert direct["features"]["report_audit"] == "SUPPORTED"
    moment = families["wi-major-axis-moment-splice"]
    assert moment["features"]["independent_moment_input"] == "SUPPORTED"
    assert moment["features"]["custom_fastener"] == "DEFERRED"
    assert moment["features"]["force_only_shear"] == "NOT_APPLICABLE"
