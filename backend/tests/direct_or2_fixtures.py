"""Owner-approved geometry and explicit demonstration conditions, never product defaults."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from tests.api.test_mat1_routes import call, condition, selection


def owner_request(*, si: bool = False, one_row: bool = False) -> dict[str, Any]:
    payload = cast(
        dict[str, Any],
        json.loads(
            Path(__file__)
            .with_name("fixtures")
            .joinpath("direct_or2_owner_request.json")
            .read_text(encoding="utf-8")
        ),
    )
    if one_row:
        payload["row_count"] = 1
        payload["unloaded_end_e1"]["value"] = "2"
        payload["loaded_boundary_to_row_1_distance"]["value"] = "2"
        payload["physical_connection"]["geometry_template"]["bolt_to_brace_end_distance"][
            "value"
        ] = "2"
        action = payload["physical_connection"]["joint_assembly"]["member_end_actions"][0]
        action["coordinate_frame_kind"] = "BOLT_GROUP_LOCAL"
        action["coordinate_frame_owner_id"] = "bolt-group-1"
        action["force"] = {"x": "0", "y": ".7", "z": "0", "unit": "kip"}
        action["reference_point"] = {
            "kind": "BOLT_GROUP_ORIGIN",
            "owner_id": "bolt-group-1",
            "position": None,
        }
    if si:

        def convert(value: object) -> object:
            if isinstance(value, dict):
                if value.get("unit") == "in" and "value" in value:
                    return {
                        **value,
                        "value": str(Decimal(value["value"]) * Decimal("25.4")),
                        "unit": "mm",
                    }
                return {key: convert(item) for key, item in value.items()}
            if isinstance(value, list):
                return [convert(item) for item in value]
            return value

        payload = cast(dict[str, Any], convert(payload))
        payload["display_unit_system"] = "SI"
        payload["source_length_unit"] = "mm"
        payload["physical_connection"]["joint_assembly"]["unit_system"] = "SI"
    return payload


def owner_body(*, si: bool = False, one_row: bool = False) -> dict[str, Any]:
    legacy = owner_request(si=si, one_row=one_row)
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    conditions = condition("WIND_TORNADO_SEISMIC")
    conditions["sustained_temperature"]["value"] = "70"
    conditions["maximum_temperature"]["value"] = "70"
    conditions["load_case_name"] = "EXAMPLE ONLY - NOT PROJECT CONDITIONS"
    return {
        "contract": "MAT1-MULTI-ROW-RC0",
        "legacy_request": legacy,
        "assignments": {"default_material": selection(record), "default_conditions": conditions},
    }
