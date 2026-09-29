"""One packaged capability contract shared with the browser build."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Literal, cast

from fastapi import APIRouter, Depends

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.security import TrustedIdentityResolver

CapabilityState = Literal["SUPPORTED", "DEFERRED", "NOT_APPLICABLE"]
FEATURE_KEYS = frozenset(
    {
        "frp_material_selection",
        "shared_design_conditions",
        "bolted_metallic_hardware",
        "automatic_physical_demand",
        "externally_resolved_demand",
        "force_only_shear",
        "independent_moment_input",
        "bolt_axis_prying_input",
        "multirow_physical_layout",
        "custom_material",
        "custom_fastener",
        "report_engineer",
        "report_audit",
    }
)


@lru_cache(maxsize=1)
def workspace_capabilities() -> dict[str, object]:
    raw = json.loads(
        files("frp_master_connection")
        .joinpath("data/workspace_capabilities.json")
        .read_text(encoding="utf-8")
    )
    if raw["contract"] != "WORKSPACE-CAPABILITIES-OR1-RC1":
        raise ValueError("Unsupported workspace capability contract.")
    states = frozenset(raw["feature_states"])
    if states != {"SUPPORTED", "DEFERRED", "NOT_APPLICABLE"}:
        raise ValueError("Capability states must be explicit.")
    common = cast(dict[str, CapabilityState], raw["common"])
    profiles = cast(dict[str, dict[str, CapabilityState]], raw["profiles"])
    rows = cast(list[dict[str, str]], raw["families"])
    if {row["route_id"] for row in rows} != set(FAMILIES) or len(rows) != len(FAMILIES):
        raise ValueError("Capability families must exactly match native workspace bindings.")
    resolved: dict[str, object] = {}
    for row in rows:
        family = FAMILIES[row["route_id"]]
        if row["template_id"] != family.product_id:
            raise ValueError(f"Capability template mismatch for {family.route_id}.")
        features = {**common, **profiles[row["profile"]]}
        if set(features) != FEATURE_KEYS or set(features.values()) - states:
            raise ValueError(f"Incomplete capability profile for {family.route_id}.")
        if row["material_assignment_mode"] not in {"LINKED", "PER_COMPONENT"}:
            raise ValueError("Material assignment mode must be explicit.")
        resolved[family.route_id] = {
            "route_id": family.route_id,
            "template_id": family.product_id,
            "category": family.category,
            "material_assignment_mode": row["material_assignment_mode"],
            "features": features,
        }
    return {"contract": raw["contract"], "families": resolved}


def build_workspace_capability_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces")
    identity = build_trusted_identity_dependency(identity_resolver)

    @router.get("/capabilities", dependencies=[Depends(identity)])
    async def capabilities() -> dict[str, object]:
        return workspace_capabilities()

    return router
