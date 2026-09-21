"""CME-3 successor integration: historical equations remain separate and frozen."""

from dataclasses import replace

import pytest
from tests.api.test_connector_materials import SS, envelope

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.connector_materials import MaterialPlanRequestDTO, material_plan
from frp_master_connection.application.stainless_family_activation import (
    AUTHORITY,
    AVAILABLE,
    ROUTES,
    STACKS,
    RequiredCheck,
    activate_plan,
    canonical_material,
    connection_summary,
)
from frp_master_connection.calculation.connector_material_plan import (
    ConnectorMaterialPlan,
    plan_connector_materials,
)
from frp_master_connection.domain.connector_materials import (
    CanonicalComponent,
    ComponentRole,
    ConnectorMaterial,
    Fabrication,
    MaterialDescriptor,
)


@pytest.mark.parametrize(
    "alias",
    ["SS316", "316 Stainless Steel", "316SS", "316 SS", "316", "316L", "316L SS", "316/316L"],
)
def test_approved_aliases_are_selection_not_certification(alias: str) -> None:
    assert canonical_material(alias) == "SS316"


@pytest.mark.parametrize("value", [None, "FRP"])
def test_missing_and_explicit_frp(value: str | None) -> None:
    assert canonical_material(value) == "FRP"


@pytest.mark.parametrize("value", ["304", "unknown", "", "STEEL"])
def test_unknown_selection_fails_closed(value: str) -> None:
    with pytest.raises(ValueError, match="CONNECTOR_BODY_MATERIAL_NOT_SUPPORTED"):
        canonical_material(value)


# Preserve this historical cohort exactly; SSMC's FRP-only successor is tested
# separately in test_ssmc_api, including its mandatory stainless rejection.
@pytest.mark.parametrize("route", tuple(r for r in FAMILIES if r != "stair-stringer-miter"))
def test_public_planning_inventory_is_noncalculating(route: str) -> None:
    payload = envelope(route)
    steel = material_plan(MaterialPlanRequestDTO.model_validate(dict(payload, apply_all=SS)))
    targets = steel["targets"]
    assert isinstance(targets, list)
    assert bool(targets) == (route in ROUTES)
    assert steel["resistance_evaluated"] is False
    assert steel["derived_branch_forces"] is None
    for target in targets:
        assert isinstance(target, dict)
        assert target["provider_status"] == AVAILABLE
        assert target["activation_authority"] == AUTHORITY
        assert target["required_provider_stack"] == list(STACKS[ROUTES[route]])
        assert target["capacity"] is None
        assert target["utilization"] is None


def native_plan() -> ConnectorMaterialPlan:
    return plan_connector_materials(
        "PRODUCT",
        "clip-angle",
        (CanonicalComponent("body", ComponentRole.CONNECTOR_BODY, "ANGLE"),),
        (),
        geometry_identity="geometry",
    )


def test_exact_frp_plan_identity_and_mixed_body_defense() -> None:
    plan = native_plan()
    assert activate_plan(plan) is plan
    ss = MaterialDescriptor(
        family=ConnectorMaterial.SS316, grade="316", fabrication=Fabrication.HOT_FINISHED
    )
    steel = replace(plan.targets[0], material=ss)
    with pytest.raises(ValueError, match="MIXED_CONNECTOR_BODY"):
        activate_plan(replace(plan, targets=(plan.targets[0], steel)))
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        activate_plan(replace(plan, mode="single-bolt", targets=(steel,)))
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        activate_plan(replace(plan, targets=(replace(steel, body_form="TEE"),)))
    active = activate_plan(replace(plan, targets=(steel,)))
    assert active.fingerprint != plan.fingerprint
    assert active.targets[0].provider_status == AVAILABLE


@pytest.mark.parametrize("domain", ["BODY", "MEMBER", "HARDWARE", "FOUNDATION"])
def test_known_failure_outranks_blockers_in_every_domain(domain: str) -> None:
    check = RequiredCheck("check", domain, "FAIL", "a" * 64)
    assert connection_summary((check,), ("SOURCE_REQUIRED",), complete=False) == "FAIL"


def test_pass_requires_complete_supported_coverage_and_no_blocker() -> None:
    check = RequiredCheck("check", "BODY", "PASS", "a" * 64)
    assert connection_summary((check,), (), complete=True) == "PASS"
    assert connection_summary((check,), (), complete=False) == "ENGINEERING_REVIEW_REQUIRED"
    assert connection_summary((), (), complete=True) == "ENGINEERING_REVIEW_REQUIRED"
    assert (
        connection_summary((check,), ("SOURCE_REQUIRED",), complete=True)
        == "ENGINEERING_REVIEW_REQUIRED"
    )
    with pytest.raises(ValueError, match="DUPLICATE_REQUIRED_CHECK"):
        connection_summary((check, check), (), complete=True)
    with pytest.raises(ValueError, match="UNEVALUATED_CHECK"):
        connection_summary((replace(check, comparison="NOT_EVALUATED"),), (), complete=True)
