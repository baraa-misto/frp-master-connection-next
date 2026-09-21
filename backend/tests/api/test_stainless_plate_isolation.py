"""CME-2B execution cannot mutate or enter frozen CME-1 family dispatch."""

import ast
from pathlib import Path

import pytest
from tests.api.test_connector_materials import SS, envelope, http
from tests.calculation.test_stainless_plate import evaluate, request

from frp_master_connection.api.connector_material_native import FAMILIES, native_family_providers
from frp_master_connection.api.connector_materials import MaterialPlanRequestDTO, material_plan


# Preserve this historical cohort exactly; SSMC's FRP-only successor is tested
# separately in test_ssmc_api, including its mandatory stainless rejection.
@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r != "stair-stringer-miter"))
def test_isolated_execution_preserves_complete_native_and_public_plans(route: str) -> None:
    payload = envelope(route)
    family = FAMILIES[route]
    native = family.preview(payload["native_input"])
    frp = material_plan(MaterialPlanRequestDTO.model_validate(payload))
    stainless_payload = dict(payload, apply_all=SS)
    stainless = material_plan(MaterialPlanRequestDTO.model_validate(stainless_payload))
    registry = {key: provider.capability for key, provider in native_family_providers().items()}
    capabilities = http("GET", "/api/v1/connector-materials/capabilities").json()
    assert evaluate(request()).numerical_comparison == "ISOLATED_COVERED_CHECKS_PASS"
    assert family.preview(payload["native_input"]) == native
    assert material_plan(MaterialPlanRequestDTO.model_validate(payload)) == frp
    assert material_plan(MaterialPlanRequestDTO.model_validate(stainless_payload)) == stainless
    targets = stainless["targets"]
    assert isinstance(targets, list)
    for target in targets:
        assert isinstance(target, dict)
        assert target["provider_status"] == "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
        assert target["capacity"] is None
        assert target["utilization"] is None
    assert {
        key: provider.capability for key, provider in native_family_providers().items()
    } == registry
    assert http("GET", "/api/v1/connector-materials/capabilities").json() == capabilities


def test_no_existing_production_module_imports_isolated_provider() -> None:
    root = Path(__file__).parents[2] / "src/frp_master_connection"
    for path in root.rglob("*.py"):
        # Owner-authorized CME-3 successor adapter; no package-wide exemption.
        if path.relative_to(root).as_posix() == "application/stainless_family_activation.py":
            continue
        if path.name in {"stainless_plate.py", "stainless_material.py"}:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(
                "stainless_plate" in name or "stainless_material" in name for name in modules
            ), path
