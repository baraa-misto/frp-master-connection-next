"""No public integration or frozen authority change from isolated core execution."""

import ast
from pathlib import Path

import pytest
from tests.api.test_connector_materials import SS, envelope, http
from tests.calculation.test_stainless_angle import evaluate, request
from tests.calculation.test_stainless_response import evaluate as response_evaluate
from tests.calculation.test_stainless_response import request as response_request

from frp_master_connection.api.connector_material_native import FAMILIES, native_family_providers
from frp_master_connection.api.connector_materials import MaterialPlanRequestDTO, material_plan


# Preserve this historical cohort exactly; SSMC's FRP-only successor is tested
# separately in test_ssmc_api, including its mandatory stainless rejection.
@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r != "stair-stringer-miter"))
def test_native_public_and_hardware_foundation_unchanged(route: str) -> None:
    payload = envelope(route)
    family = FAMILIES[route]
    before = family.preview(payload["native_input"])
    frp = material_plan(MaterialPlanRequestDTO.model_validate(payload))
    steel = material_plan(MaterialPlanRequestDTO.model_validate(dict(payload, apply_all=SS)))
    registry = {k: p.capability for k, p in native_family_providers().items()}
    assert evaluate(request()).status == "ISOLATED_COVERED_CHECKS_PASS"
    assert evaluate(request("TEE")).status == "ISOLATED_COVERED_CHECKS_PASS"
    assert response_evaluate(response_request()).status == "QUALIFIED_RESPONSE"
    assert family.preview(payload["native_input"]) == before
    assert material_plan(MaterialPlanRequestDTO.model_validate(payload)) == frp
    assert (
        material_plan(MaterialPlanRequestDTO.model_validate(dict(payload, apply_all=SS))) == steel
    )
    assert {k: p.capability for k, p in native_family_providers().items()} == registry
    targets = steel["targets"]
    assert isinstance(targets, list)
    for target in targets:
        assert isinstance(target, dict)
        assert target["provider_status"] == "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
        assert target["capacity"] is None
        assert target["utilization"] is None


def test_all_isolated_import_boundaries_and_no_public_route() -> None:
    root = Path(__file__).parents[2] / "src/frp_master_connection"
    names = {"stainless_shape", "stainless_response", "stainless_angle", "stainless_tee"}
    for path in root.rglob("*.py"):
        # Owner-authorized CME-3 successor adapter; no package-wide exemption.
        if path.relative_to(root).as_posix() == "application/stainless_family_activation.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            if path.stem in names:
                assert not any(
                    "stainless_plate" in m or "stainless_material" in m or "importlib" in m
                    for m in modules
                )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in ("__import__", "exec", "eval")
            else:
                assert not any(m.split(".")[-1] in names for m in modules), path
    # Historical core authority still has exactly its original sixteen routes.
    # DCTN is the one explicitly authorized no-body successor, not a C2 endpoint.
    historical_routes = set(FAMILIES) - {"double-channel-truss-node", "stair-stringer-miter"}
    assert historical_routes == {
        "single-bolt",
        "multi-row",
        "tee-connector",
        "clip-angle",
        "paired-clip-angle",
        "multi-member-tee",
        "beam-concrete-paired-angle",
        "direct-side-lap-concrete",
        "column-base-web-angles",
        "beam-web-splice",
        "wi-major-axis-moment-splice",
        "channel-major-axis-moment-splice",
        "wi-beam-concrete-wall-moment",
        "wi-beam-frp-support-moment",
        "angle-column-two-leg-moment-base",
        "wi-rhs-srs-column-moment-base",
    }
    assert len(historical_routes) == 16
    assert "double-channel-truss-node" in FAMILIES
    for route in ("stainless-response", "stainless-angle", "stainless-tee"):
        assert http("GET", "/api/v1/" + route).status_code == 404
