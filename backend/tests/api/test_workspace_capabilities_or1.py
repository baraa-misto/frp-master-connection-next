"""The shared capability contract binds every native family explicitly."""

from __future__ import annotations

import json
from copy import deepcopy
from importlib.resources import files as resource_files
from typing import Any, cast

import pytest
from tests.api.test_mat1_routes import call

import frp_master_connection.api.workspace_capabilities as capability_module
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


def test_packaged_capability_contract_rejects_incomplete_or_mismatched_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Package:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def joinpath(self, _name: str) -> Package:
            return self

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            return json.dumps(self.payload)

    source = resource_files("frp_master_connection").joinpath("data/workspace_capabilities.json")
    valid = cast(dict[str, Any], json.loads(source.read_text(encoding="utf-8")))
    cases: list[tuple[dict[str, Any], str]] = []

    bad = deepcopy(valid)
    bad["contract"] = "UNREVIEWED"
    cases.append((bad, "Unsupported workspace capability contract"))
    bad = deepcopy(valid)
    bad["feature_states"] = ["SUPPORTED"]
    cases.append((bad, "Capability states must be explicit"))
    bad = deepcopy(valid)
    bad["families"].pop()
    cases.append((bad, "families must exactly match"))
    bad = deepcopy(valid)
    bad["families"][0]["template_id"] = "WRONG_TEMPLATE"
    cases.append((bad, "Capability template mismatch"))
    bad = deepcopy(valid)
    bad["profiles"]["direct"].pop("custom_fastener")
    cases.append((bad, "Incomplete capability profile"))
    bad = deepcopy(valid)
    bad["families"][0]["material_assignment_mode"] = "UNDEFINED"
    cases.append((bad, "Material assignment mode must be explicit"))

    for payload, message in cases:
        with monkeypatch.context() as patch:
            patch.setattr(
                capability_module, "files", lambda _package, current=payload: Package(current)
            )
            workspace_capabilities.cache_clear()
            with pytest.raises(ValueError, match=message):
                workspace_capabilities()
    workspace_capabilities.cache_clear()
    assert workspace_capabilities()["contract"] == "WORKSPACE-CAPABILITIES-OR1-RC1"
