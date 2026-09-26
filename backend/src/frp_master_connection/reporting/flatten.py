"""Lossless path schedules with exact references for repeated native subrecords."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from frp_master_connection.reporting.units import DisplayUnits, converted_quantity_rows


def _fingerprint(value: Any, memo: dict[int, tuple[str, int]]) -> tuple[str, int]:  # noqa: ANN401
    if isinstance(value, dict):
        cached = memo.get(id(value))
        if cached is not None:
            return cached
        children = [(str(key), _fingerprint(child, memo)) for key, child in value.items()]
        payload = json.dumps(
            sorted((key, fingerprint) for key, (fingerprint, _) in children),
            separators=(",", ":"),
        ).encode()
        result = (
            hashlib.sha256(b"D" + payload).hexdigest(),
            sum(count for _, (_, count) in children),
        )
        memo[id(value)] = result
        return result
    if isinstance(value, list):
        cached = memo.get(id(value))
        if cached is not None:
            return cached
        list_children = [_fingerprint(child, memo) for child in value]
        payload = json.dumps(
            [fingerprint for fingerprint, _ in list_children], separators=(",", ":")
        ).encode()
        result = (
            hashlib.sha256(b"L" + payload).hexdigest(),
            sum(count for _, count in list_children),
        )
        memo[id(value)] = result
        return result
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(b"S" + payload).hexdigest(), 1


def flatten_unique(
    prefix: str,
    value: Any,  # noqa: ANN401
    *,
    minimum_alias_leaves: int = 40,
    display_units: DisplayUnits = "INHERIT",
) -> list[tuple[str, str]]:
    """Print every unique native leaf and path; repeat records point to identical paths."""

    memo: dict[int, tuple[str, int]] = {}
    _fingerprint(value, memo)
    first_path: dict[str, str] = {}
    rows: list[tuple[str, str]] = []

    def visit(path: str, item: Any) -> None:  # noqa: ANN401
        if isinstance(item, (dict, list)):
            fingerprint, leaves = memo[id(item)]
            if leaves >= minimum_alias_leaves:
                previous = first_path.get(fingerprint)
                if previous is not None:
                    rows.append((path, f"Identical native record at {previous}"))
                    return
                first_path[fingerprint] = path
            if isinstance(item, dict):
                if {"value", "unit"} <= item.keys() and item.keys() <= {
                    "value",
                    "unit",
                    "canonical_value",
                    "canonical_unit",
                }:
                    native = f"{item['value']} {item['unit']}"
                    if "canonical_value" in item and "canonical_unit" in item:
                        native += f"; canonical {item['canonical_value']} {item['canonical_unit']}"
                    if display_units != "INHERIT":
                        equivalent_rows = converted_quantity_rows(item, display_units)
                        if equivalent_rows:
                            equivalent = equivalent_rows[0][1].split(" = ", 1)[-1]
                            native += f"; {display_units} equivalent {equivalent}"
                    rows.append((path, native))
                    return
                for key, child in item.items():
                    visit(f"{path}.{key}" if path else str(key), child)
            else:
                for index, child in enumerate(item):
                    visit(f"{path}[{index}]", child)
            if not item:
                rows.append((path, "Empty native collection"))
            return
        if item is None:
            text = "Not supplied"
        elif isinstance(item, bool):
            text = "Yes" if item else "No"
        else:
            text = str(item)
        rows.append((path, text))

    visit(prefix, value)
    return rows


__all__ = ("flatten_unique",)
