"""Read-only report representation of signed Direct W end geometry."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def direct_support_view(visual: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    """Move only rendered W box caps to signed real ends; preserve the audit input."""
    rendered = deepcopy(visual)
    physical = rendered["physical_connection"]
    for primitive in (*physical["primitives"], *physical["view_extension_primitives"]):
        if primitive["owner_id"] != authority["component_id"] or primitive["kind"] != "BOX":
            continue
        params = {p["name"]: p for p in primitive["parameters"]}
        old_midpoint = (float(params["x_start"]["value"]) + float(params["x_end"]["value"])) / 2
        for key, field in (
            ("x_start", "negative_end_member_local_station"),
            ("x_end", "positive_end_member_local_station"),
        ):
            if authority[field] is not None:
                params[key]["value"] = authority[field]
        shift = (
            float(params["x_start"]["value"]) + float(params["x_end"]["value"])
        ) / 2 - old_midpoint
        for axis in ("x", "y", "z"):
            primitive["center"][axis] = str(
                float(primitive["center"][axis]) + shift * float(primitive["x_axis"][axis])
            )
        primitive["label"] += " - W ends: " + str(authority["condition"])
    return rendered
