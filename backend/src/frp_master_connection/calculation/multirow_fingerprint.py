"""Deterministic future Slice 2 plan fingerprinting with presentation exclusions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.calculation.multirow import MultiRowCalculationPlanSet
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    canonical_decimal_string,
    decimal_from_finite_real,
)
from frp_master_connection.geometry.multirow import MultiRowGeometry

type CanonicalPlanValue = (
    str | bool | dict[str, "CanonicalPlanValue"] | list["CanonicalPlanValue"] | None
)


@dataclass(frozen=True, slots=True)
class MultiRowFingerprintInput:
    """Calculation-relevant Stage 2.4A fields for a future Slice 2 fingerprint."""

    standard: str
    edition: str
    errata: str
    specification_id: str
    golden_schema_id: str
    project_schema_version: str
    calculation_contract_version: str
    active_calculation_engine_version: str
    active_engineering_rule_set_version: str
    physical_geometry: MultiRowGeometry
    material_identities: tuple[str, ...]
    plan_set: MultiRowCalculationPlanSet
    block_path_plans: object
    factor_selections: object
    source_metadata: object

    def __post_init__(self) -> None:
        identities = (
            self.standard,
            self.edition,
            self.errata,
            self.specification_id,
            self.golden_schema_id,
            self.project_schema_version,
            self.calculation_contract_version,
            self.active_calculation_engine_version,
            self.active_engineering_rule_set_version,
        )
        if any(not item.strip() for item in identities):
            raise ValueError("Fingerprint source and version identities must be nonempty.")


@dataclass(frozen=True, slots=True)
class MultiRowFingerprintEnvelope:
    """Calculation input plus presentation state that is deliberately excluded."""

    calculation_input: MultiRowFingerprintInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    preview_timing: object | None = None
    request_timestamp: str | None = None


def _geometry_payload(geometry: MultiRowGeometry) -> CanonicalPlanValue:
    return cast(
        CanonicalPlanValue,
        {
            "group_id": geometry.group.id,
            "interface_id": geometry.group.interface_id,
            "declared_row_count": str(geometry.group.declared_row_count),
            "declared_bolt_count": str(geometry.group.declared_bolt_count),
            "bolts": [
                {
                    "id": bolt.id,
                    "x": canonical_decimal_string(decimal_from_finite_real(bolt.center.x)),
                    "y": canonical_decimal_string(decimal_from_finite_real(bolt.center.y)),
                    "bolt_diameter": canonical_decimal_string(
                        decimal_from_finite_real(bolt.bolt_diameter)
                    ),
                    "hole_diameter": canonical_decimal_string(
                        decimal_from_finite_real(bolt.hole_diameter)
                    ),
                    "bolt_identity": bolt.bolt_identity,
                    "logical_connection_id": bolt.logical_connection_id,
                }
                for bolt in sorted(geometry.group.bolts, key=lambda item: item.id)
            ],
            "boundary": _canonical(geometry.boundary),
            "force_u": _canonical(geometry.force_u),
            "force_v": _canonical(geometry.force_v),
            "rows": [
                {
                    "id": row.id,
                    "ordinal": str(row.ordinal),
                    "coordinate": canonical_decimal_string(
                        decimal_from_finite_real(row.projected_coordinate)
                    ),
                    "raw_deviation": canonical_decimal_string(
                        decimal_from_finite_real(row.raw_deviation)
                    ),
                    "bolt_ids": [bolt.bolt.id for bolt in row.bolts],
                }
                for row in geometry.rows
            ],
            "bolt_lines": [
                {
                    "id": line.id,
                    "ordinal": str(line.ordinal),
                    "coordinate": canonical_decimal_string(
                        decimal_from_finite_real(line.projected_coordinate)
                    ),
                    "raw_deviation": canonical_decimal_string(
                        decimal_from_finite_real(line.raw_deviation)
                    ),
                    "bolt_ids": [bolt.bolt.id for bolt in line.bolts],
                }
                for line in geometry.bolt_lines
            ],
            "classification": _canonical(geometry.classification),
            "sorting_tolerance": canonical_decimal_string(
                decimal_from_finite_real(geometry.sorting_tolerance)
            ),
        },
    )


def _canonical(value: object) -> CanonicalPlanValue:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "unit": value.canonical_unit.value,
            "value": value.canonical_string,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, Enum):
        if not isinstance(value.value, str):
            raise TypeError("Fingerprint enum values must be stable strings.")
        return value.value
    if isinstance(value, MultiRowGeometry):
        return _geometry_payload(value)
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Fingerprint object keys must be strings.")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"Unsupported multi-row fingerprint value type: {type(value).__name__}.")


def canonical_multirow_fingerprint_json(
    value: MultiRowFingerprintInput | MultiRowFingerprintEnvelope,
) -> str:
    """Serialize only calculation-authority fields as compact sorted UTF-8 JSON."""

    calculation_input = (
        value.calculation_input if isinstance(value, MultiRowFingerprintEnvelope) else value
    )
    if not isinstance(calculation_input, MultiRowFingerprintInput):
        raise TypeError("Multi-row fingerprinting requires an input or envelope.")
    return json.dumps(
        _canonical(calculation_input),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def multirow_plan_fingerprint(
    value: MultiRowFingerprintInput | MultiRowFingerprintEnvelope,
) -> str:
    """Return lowercase SHA-256 without activating a new engine or rule set."""

    content = canonical_multirow_fingerprint_json(value).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


__all__ = (
    "MultiRowFingerprintEnvelope",
    "MultiRowFingerprintInput",
    "canonical_multirow_fingerprint_json",
    "multirow_plan_fingerprint",
)
