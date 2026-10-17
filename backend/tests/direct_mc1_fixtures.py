"""New input controls; old owner requests remain untouched."""

from copy import deepcopy
from decimal import Decimal
from typing import Any, cast

from frp_master_connection.application.asce_shape_materials import production_shape_catalog
from frp_master_connection.application.mat1_materials import PROPERTY_IDS
from tests.api.test_direct_f6_first_row import f6_cases


def raw_mc1_native(result: dict[str, Any]) -> dict[str, Any]:
    """Recover every original engine field from signed MC1 source-gate evidence."""
    native = cast(dict[str, Any], deepcopy(result["native_design"]))
    evidence = result["direct_material_applicability"]
    for change in reversed(evidence["raw_engine_diagnostic_field_changes"]):
        parent: Any = native
        for step in change["path"][:-1]:
            parent = parent[step]
        key = change["path"][-1]
        if change["original_present"]:
            parent[key] = deepcopy(change["original_value"])
        else:
            del parent[key]
    return native


def mc1_body(temperature: str = "100", unit: str = "degF", **changes: object) -> dict[str, Any]:
    body = deepcopy(f6_cases()["owner-135"])
    body["assignments"]["default_conditions"].update(
        direct_policy="SHEAR01-DIRECT-MC1",
        design_temperature={"value": temperature, "unit": unit},
        sustained_temperature={"value": temperature, "unit": unit},
        maximum_temperature={"value": temperature, "unit": unit},
        moisture="REFERENCE",
        chemical="NONE_DECLARED",
        load_case_name="DIRECT-FACTORED-ACTION",
        time_effect_category="WIND_TORNADO_SEISMIC",
        live_load_subtype="",
        full_amplitude_duration="",
        uv_weathering="UNKNOWN",
        freeze_thaw="UNKNOWN",
    )
    body["assignments"]["default_conditions"].update(changes)
    return body


def mc1_other_resin_body() -> dict[str, Any]:
    """Existing editable session resin with no invented temperature authority."""
    body = mc1_body()
    material = production_shape_catalog()[0]
    body["assignments"]["default_material"] = {
        "kind": "SESSION",
        "id": "SESSION:mc1-other-resin-qa",
        "revision": "1",
        "display_name": "Other resin QA",
        "company": "LOCAL QA",
        "resin": "OTHER",
        "copied_from": material.id,
        "properties": {
            item.id: {
                "label": item.label,
                "symbol": item.symbol,
                "value": str(item.original),
                "unit": item.unit,
                "basis": "CHARACTERISTIC",
            }
            for item in material.properties
            if item.id in PROPERTY_IDS
        },
    }
    return body


def mc1_cases() -> dict[str, dict[str, Any]]:
    cases = {
        "dry-none": mc1_body("90"),
        "sustained-moisture": mc1_body(moisture="SUSTAINED_MOISTURE"),
        "custom-chemical": mc1_body(
            moisture="SUSTAINED_MOISTURE", chemical="SPECIFIED", chemical_strength_factor=".80"
        ),
        "new-design-temperature": mc1_body(),
        "over-140-blocked": mc1_body("140.0001"),
        "owner-yellow": deepcopy(f6_cases()["owner-135"]),
        "analytical-red": mc1_body(chemical="SPECIFIED", chemical_strength_factor=".80"),
    }
    force = cases["analytical-red"]["legacy_request"]["physical_connection"]["joint_assembly"][
        "member_end_actions"
    ][0]["force"]
    for axis in ("x", "y", "z"):
        force[axis] = str(Decimal(force[axis]) * 10)
    return cases
