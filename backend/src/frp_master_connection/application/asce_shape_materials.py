"""F5 immutable code-minimum shape specification, separate from ICE RC0 data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from decimal import Decimal
from functools import cache
from importlib.resources import files
from typing import Any, cast

from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    MaterialRecord,
    _record,
    predefined_catalog,
    temperature_applicability,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit

SHAPE_SOURCE = "ASCE_74_23_MINIMUM_CHARACTERISTIC_SHAPE_SPECIFICATION"
SHAPE_BASIS = "ASCE_74_23_MINIMUM_CHARACTERISTIC"
SHAPE_CATALOG_DIGEST = "B4AD7A73D9E7B3CB704792B845A05C709F2B9BAA91643868726E25FAED2A0D73"
SHAPE_IDS = frozenset(
    {
        "ICE_ISOPHTHALIC_POLYESTER_ASCE74_23_MIN_SHAPE_RC1",
        "ICE_VINYL_ESTER_ASCE74_23_MIN_SHAPE_RC1",
    }
)


@cache
def shape_catalog_data() -> dict[str, Any]:
    """Authenticate the complete immutable property and specification record."""

    raw: dict[str, Any] = json.loads(
        files("frp_master_connection")
        .joinpath("data/asce74_shape_minimum_rc1.json")
        .read_text(encoding="utf-8")
    )
    digest = (
        hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        )
        .hexdigest()
        .upper()
    )
    if digest != SHAPE_CATALOG_DIGEST:
        raise ValueError("F5_ASCE_SHAPE_CATALOG_DIGEST_MISMATCH")
    return raw


@cache
def production_shape_catalog() -> tuple[MaterialRecord, ...]:
    return tuple(_record(raw, SHAPE_SOURCE) for raw in shape_catalog_data()["records"])


def is_shape_basis(record: MaterialRecord) -> bool:
    """Only an authenticated predefined record can carry the code basis."""

    return record in production_shape_catalog()


def shape_reference_conditions(
    record: MaterialRecord, conditions: DesignConditions
) -> DesignConditions:
    return (
        replace(conditions, source_reference_condition="REFERENCE")
        if is_shape_basis(record)
        else conditions
    )


def required_tg_f(maximum_f: Decimal) -> Decimal:
    """A furnished-product specification threshold, never a measured catalog Tg."""

    return max(Decimal(180), maximum_f + Decimal(40))


def shape_temperature_state(record: MaterialRecord, conditions: DesignConditions) -> str:
    if is_shape_basis(record):
        return "SPECIFICATION_REQUIREMENT_SATISFIED_BY_PROJECT_CONFORMANCE"
    return temperature_applicability(conditions)


def shape_project_issues(conditions: DesignConditions) -> tuple[str, ...]:
    """Extraordinary/unknown project exposure is separate from catalog authority."""

    issues = []
    for name, state in (
        ("UV_WEATHERING", conditions.uv_weathering),
        ("FREEZE_THAW", conditions.freeze_thaw),
    ):
        if state == "UNKNOWN":
            issues.append(f"{name}_PROJECT_CONDITION_REQUIRED")
        elif state == "SPECIFIED":
            issues.append(f"EXTRAORDINARY_{name}_REVIEW_REQUIRED")
    if conditions.protective_measures.strip():
        issues.append("PROTECTIVE_SYSTEM_REVIEW_REQUIRED")
    if conditions.exposure_notes.strip():
        issues.append("PROJECT_EXPOSURE_REVIEW_REQUIRED")
    return tuple(issues)


def shape_source_metadata(record: MaterialRecord) -> dict[str, object]:
    """Return detached provenance so consumers cannot rewrite the cached catalog."""

    if not is_shape_basis(record):
        return {}
    specification = cast(
        dict[str, object], json.loads(json.dumps(shape_catalog_data()["specification"]))
    )
    legacy = next(r for r in predefined_catalog() if r.resin == record.resin)
    return {
        **specification,
        "catalog_digest": SHAPE_CATALOG_DIGEST,
        "legacy_development_record": asdict(legacy),
    }


def material_condition_basis(
    record: MaterialRecord, conditions: DesignConditions
) -> dict[str, object]:
    """Resolve specification versus actual Tg without changing user declarations."""

    threshold = required_tg_f(conditions.maximum_f)
    code_basis = is_shape_basis(record)
    return {
        "status": shape_temperature_state(record, conditions),
        "required_tg": {"value": str(threshold), "unit": "degF"},
        "required_tg_degC": str((threshold - Decimal(32)) * Decimal(5) / Decimal(9)),
        "threshold_derivation": "max(180 degF, Tmax + 40 degF)",
        "maximum_f": str(conditions.maximum_f),
        "sustained_f": str(conditions.sustained_f),
        "actual_tg_f": None if code_basis or conditions.tg_f is None else str(conditions.tg_f),
        "tg_evidence": "PROJECT_CONFORMANCE_SPECIFICATION"
        if code_basis
        else "USER_SUPPLIED"
        if conditions.tg_f is not None
        else "MISSING",
        "reference_condition": "REFERENCE" if code_basis else conditions.source_reference_condition,
        "project_issues": shape_project_issues(conditions) if code_basis else (),
    }


def pull_through_for_frp_thickness(
    record: MaterialRecord, thickness: PhysicalQuantity
) -> PhysicalQuantity | None:
    """Select only an exact Table 1-2 thickness row; no bolt-diameter mapping."""

    if not is_shape_basis(record):
        raise ValueError("F5_PULL_THROUGH_REQUIRES_PRODUCTION_SHAPE_BASIS")
    for prop in record.properties:
        for locator in prop.applicability:
            if locator.startswith("FRP_THICKNESS_IN=") and thickness == PhysicalQuantity.of(
                locator.split("=", 1)[1], Unit.IN
            ):
                return PhysicalQuantity.of(prop.original, Unit(prop.unit))
    return None
