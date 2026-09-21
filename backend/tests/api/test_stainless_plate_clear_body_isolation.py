"""C2-P2 never activates public capacity or mutates existing native dispatch."""

import ast
from pathlib import Path

import pytest
from tests.api.test_connector_materials import SS, envelope, http
from tests.calculation.test_stainless_plate_clear_body import evaluate, request

from frp_master_connection.api.connector_material_native import FAMILIES, native_family_providers
from frp_master_connection.api.connector_materials import MaterialPlanRequestDTO, material_plan


# Preserve this historical cohort exactly; SSMC's FRP-only successor is tested
# separately in test_ssmc_api, including its mandatory stainless rejection.
@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r != "stair-stringer-miter"))
def test_p2_preserves_native_preview_frp_and_ss_plans(route: str) -> None:
    payload = envelope(route)
    family = FAMILIES[route]
    native = family.preview(payload["native_input"])
    frp = material_plan(MaterialPlanRequestDTO.model_validate(payload))
    ss_request = MaterialPlanRequestDTO.model_validate(dict(payload, apply_all=SS))
    ss = material_plan(ss_request)
    registry = {k: p.capability for k, p in native_family_providers().items()}
    capabilities = http("GET", "/api/v1/connector-materials/capabilities").json()
    assert evaluate(request("-10", "15")).numerical_comparison == "ISOLATED_COVERED_CHECKS_PASS"
    assert family.preview(payload["native_input"]) == native
    assert material_plan(MaterialPlanRequestDTO.model_validate(payload)) == frp
    assert material_plan(ss_request) == ss
    targets = ss["targets"]
    assert isinstance(targets, list)
    for target in targets:
        assert isinstance(target, dict)
        assert target["provider_status"] == "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
        assert target["capacity"] is None
        assert target["utilization"] is None
    assert {k: p.capability for k, p in native_family_providers().items()} == registry
    assert http("GET", "/api/v1/connector-materials/capabilities").json() == capabilities


def test_no_public_import_and_no_frozen_provider_import_or_dynamic_import() -> None:
    root = Path(__file__).parents[2] / "src/frp_master_connection"
    isolated = root / "calculation/stainless_plate_clear_body.py"
    for path in root.rglob("*.py"):
        # Owner-authorized CME-3 successor adapter; no package-wide exemption.
        if path.relative_to(root).as_posix() == "application/stainless_family_activation.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            if path == isolated:
                assert not any(
                    "stainless_material" in m or "stainless_plate" in m or "importlib" in m
                    for m in modules
                )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in ("__import__", "exec", "eval")
            else:
                assert not any("stainless_plate_clear_body" in m for m in modules)


def test_route_count_and_missing_public_endpoint() -> None:
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
    assert http("GET", "/api/v1/stainless-plate-clear-body").status_code == 404
