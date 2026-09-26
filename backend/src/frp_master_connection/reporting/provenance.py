"""Identify fields defaulted by the validated API request model.

An explicitly submitted field can have originated from a workspace's initial
values or a user edit. The server cannot infer that distinction from the wire.
"""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute
from pydantic import BaseModel, TypeAdapter, ValidationError


def server_defaulted_fields(route: object, submitted: dict[str, Any]) -> dict[str, Any]:
    """Return accepted defaults absent from the submitted JSON, by exact field path."""

    if not isinstance(route, APIRoute) or route.body_field is None:
        return {}
    annotation = route.body_field.field_info.annotation
    if annotation is None:
        return {}
    try:
        validated = TypeAdapter(annotation).validate_python(submitted)
    except ValidationError:
        return {}
    if not isinstance(validated, BaseModel):
        return {}
    resolved = validated.model_dump(mode="json", by_alias=True)
    defaults: dict[str, Any] = {}

    def visit(accepted: Any, provided: Any, path: str) -> None:  # noqa: ANN401
        if isinstance(accepted, dict):
            explicit_items = provided if isinstance(provided, dict) else {}
            for key, child in accepted.items():
                child_path = f"{path}.{key}" if path else key
                if key in explicit_items:
                    visit(child, explicit_items[key], child_path)
                else:
                    defaults[child_path] = child
        elif isinstance(accepted, list) and isinstance(provided, list):
            for index, child in enumerate(accepted):
                if index < len(provided):
                    visit(child, provided[index], f"{path}[{index}]")
                else:
                    defaults[f"{path}[{index}]"] = child

    visit(resolved, submitted, "")
    return defaults


__all__ = ("server_defaulted_fields",)
