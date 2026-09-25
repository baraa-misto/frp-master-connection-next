"""MAT1 owner-supplied material records and code-coefficient candidates.

This module keeps original data separate from numerical end-use candidates.
Neither a catalog entry nor a calculable coefficient establishes qualification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import cache
from importlib.resources import files
from typing import Any, Literal, cast

from frp_master_connection.calculation.inputs import (
    TimeEffectCategory,
    select_time_effect_factor,
)

SEED_SHA256 = "4F6EA6F26F407B2DD30510980E5BEDF34807F4DB0EE2978C061703CE47C171C1"
SEED_PATH = "data/ICE_PREDEFINED_MATERIAL_SEED_INPUTS_RC0.json"
CATALOG_REVISION = "RC0"
STRENGTH_IDS = frozenset(
    {
        "tensile_strength_L",
        "tensile_strength_T",
        "compressive_strength_L",
        "in_plane_shear_strength_LT",
        "interlaminar_shear_strength",
        "bearing_strength_L",
        "bearing_strength_T",
    }
)
MODULUS_IDS = frozenset(
    {
        "tensile_modulus_L",
        "tensile_modulus_T",
        "compressive_modulus_L",
        "compressive_modulus_T",
        "in_plane_shear_modulus_LT",
    }
)
PULL_THROUGH_IDS = frozenset(
    {
        "pull_through_3_8_as_labeled",
        "pull_through_1_2_as_labeled",
        "pull_through_3_4_as_labeled",
    }
)
PROPERTY_IDS = STRENGTH_IDS | MODULUS_IDS | PULL_THROUGH_IDS | {"major_poisson_ratio_LT"}
Moisture = Literal["REFERENCE", "SUSTAINED_MOISTURE", "OTHER", "UNKNOWN"]
Exposure = Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"]
Resin = Literal["ISOPHTHALIC_POLYESTER", "VINYL_ESTER", "OTHER"]


def decimal_input(value: str) -> Decimal:
    """Parse an exact finite decimal without accepting Boolean or float input."""

    if not isinstance(value, str):
        raise ValueError("MAT1 decimal values must be strings.")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("MAT1 value must be an exact decimal string.") from error
    if not result.is_finite():
        raise ValueError("MAT1 value must be finite.")
    return result


@dataclass(frozen=True, slots=True)
class MaterialProperty:
    id: str
    label: str
    symbol: str
    original: Decimal
    unit: str
    basis: str
    source_locator: str
    applicability: tuple[str, ...]
    source_bolt_diameter_in: Decimal | None = None


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    id: str
    revision: str
    content_digest: str
    display_name: str
    company: str
    resin: Resin
    source_kind: str
    properties: tuple[MaterialProperty, ...]
    missing: tuple[str, ...]

    def property(self, property_id: str) -> MaterialProperty | None:
        return next((item for item in self.properties if item.id == property_id), None)


def _record(raw: dict[str, Any], source_kind: str) -> MaterialRecord:
    identifier = raw.get("id", raw.get("proposed_record_id"))
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("MAT1 catalog record requires a stable ID.")
    resin = cast(
        Resin,
        {
            "Vinyl ester": "VINYL_ESTER",
            "Isophthalic polyester": "ISOPHTHALIC_POLYESTER",
        }.get(raw["resin"], "OTHER"),
    )
    properties = tuple(
        MaterialProperty(
            id=key,
            label=item["label"],
            symbol=item["symbol"],
            original=decimal_input(item["value"]),
            unit=item["unit"],
            basis=item.get(
                "basis",
                "NOMINAL_AS_SUPPLIED" if key not in MODULUS_IDS else "BASIS_UNSPECIFIED",
            ),
            source_locator=item.get("source_locator", "ICE owner material table, MAT1 seed RC0"),
            applicability=("BOLT_SIZE_LABEL_ONLY; TESTED_FRP_THICKNESS_AND_WASHER_UNKNOWN",)
            if key in PULL_THROUGH_IDS
            else (),
            source_bolt_diameter_in=(
                decimal_input(item["source_bolt_diameter_in"]) if key in PULL_THROUGH_IDS else None
            ),
        )
        for key, item in sorted(raw["properties"].items())
    )
    if (
        source_kind == "OWNER_SUPPLIED_NOMINAL_DATASET"
        and {item.id for item in properties} != PROPERTY_IDS
    ):
        raise ValueError("MAT1 owner record does not contain the exact 16 source fields.")
    if any(item.original <= 0 for item in properties):
        raise ValueError("MAT1 predefined properties must be positive.")
    digest = (
        hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        )
        .hexdigest()
        .upper()
    )
    return MaterialRecord(
        identifier,
        raw.get("revision", CATALOG_REVISION),
        digest,
        raw["display_name"],
        raw["company"],
        resin,
        source_kind,
        properties,
        tuple(
            raw.get(
                "explicitly_missing",
                (
                    "GLASS_TRANSITION_TEMPERATURE",
                    "TRANSVERSE_COMPRESSIVE_STRENGTH",
                    "DIRECTIONAL_FLEXURAL_PROPERTIES",
                    "MEAN_VS_CHARACTERISTIC_MODULUS",
                    "MANUFACTURER_PRODUCT_REVISION",
                    "REFERENCE_CONDITION",
                ),
            )
        ),
    )


@cache
def predefined_catalog() -> tuple[MaterialRecord, ...]:
    """Load immutable, versioned catalog data; source file is never rewritten."""

    raw_bytes = files("frp_master_connection").joinpath(SEED_PATH).read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest().upper() != SEED_SHA256:
        raise ValueError("MAT1 owner seed checksum mismatch.")
    source = json.loads(raw_bytes)
    owner_records = tuple(
        _record(item, "OWNER_SUPPLIED_NOMINAL_DATASET") for item in source["records"]
    )
    if len(owner_records) != 2 or {item.id for item in owner_records} != {
        "ICE_ISOPHTHALIC_POLYESTER_OWNER_SEED_RC0",
        "ICE_VINYL_ESTER_OWNER_SEED_RC0",
    }:
        raise ValueError("MAT1 initial catalog identity mismatch.")
    first, second = owner_records
    other_properties = {item.id: item for item in second.properties}
    differing = {
        item.id for item in first.properties if item.original != other_properties[item.id].original
    }
    if differing != {"tensile_strength_L", "tensile_strength_T"}:
        raise ValueError("MAT1 vinyl ester must differ in only two tensile strengths.")
    additional = json.loads(
        files("frp_master_connection")
        .joinpath("data/mat1_catalog_records.json")
        .read_text(encoding="utf-8")
    )
    if additional.get("format") != "MAT1_CATALOG_ADDITIONS_RC0":
        raise ValueError("MAT1 additional catalog format mismatch.")
    extra = tuple(
        _record(item, "CONTROLLED_CATALOG_DATA_UNQUALIFIED") for item in additional["records"]
    )
    records = owner_records + extra
    if len({item.id for item in records}) != len(records):
        raise ValueError("MAT1 catalog IDs must be unique.")
    return records


def catalog_record(identifier: str, revision: str, digest: str) -> MaterialRecord:
    """Require exact revision and content binding for a predefined selection."""

    for record in predefined_catalog():
        if (record.id, record.revision, record.content_digest) == (
            identifier,
            revision,
            digest,
        ):
            return record
    raise ValueError("MAT1_CATALOG_IDENTITY_OR_REVISION_MISMATCH")


def session_record(
    identifier: str,
    revision: str,
    display_name: str,
    company: str,
    resin: Resin,
    properties: dict[str, dict[str, str]],
    copied_from: str | None = None,
) -> MaterialRecord:
    """Validate transient user data without inheriting catalog authority."""

    if not identifier.startswith("SESSION:") or identifier in {
        item.id for item in predefined_catalog()
    }:
        raise ValueError("MAT1 session IDs must use their distinct namespace.")
    if not revision.strip() or not display_name.strip() or not company.strip():
        raise ValueError("MAT1 session identity fields must be nonempty.")
    if resin not in {"ISOPHTHALIC_POLYESTER", "VINYL_ESTER", "OTHER"}:
        raise ValueError("MAT1 session resin is invalid.")
    if not properties or not set(properties).issubset(PROPERTY_IDS):
        raise ValueError("MAT1 session properties contain unknown or no fields.")
    entries: list[MaterialProperty] = []
    for key, raw in sorted(properties.items()):
        if set(raw) != {"label", "symbol", "value", "unit", "basis"}:
            raise ValueError("MAT1 session property fields are invalid.")
        unit = raw["unit"]
        allowed_units = (
            {"dimensionless", "1"}
            if key == "major_poisson_ratio_LT"
            else {"lbf", "kip", "N", "kN"}
            if key in PULL_THROUGH_IDS
            else {"psi", "ksi", "MPa"}
        )
        if unit not in allowed_units:
            raise ValueError(f"MAT1 unit for {key} is incompatible with its property dimension.")
        value = decimal_input(raw["value"])
        if value <= 0:
            raise ValueError("MAT1 property values must be positive.")
        if raw["basis"] not in {
            "NOMINAL_AS_SUPPLIED",
            "MEAN",
            "CHARACTERISTIC",
            "ALLOWABLE",
            "ALREADY_ADJUSTED",
            "UNKNOWN",
            "BASIS_UNSPECIFIED",
        }:
            raise ValueError("MAT1 source basis is invalid.")
        if not raw["label"].strip() or not raw["symbol"].strip():
            raise ValueError("MAT1 property labels and symbols must be nonempty.")
        entries.append(
            MaterialProperty(
                key,
                raw["label"],
                raw["symbol"],
                value,
                unit,
                raw["basis"],
                "User-supplied session data",
                ("BOLT_SIZE_LABEL_ONLY; TESTED_FRP_THICKNESS_AND_WASHER_UNKNOWN",)
                if key in PULL_THROUGH_IDS
                else (),
            )
        )
    content = {
        "id": identifier,
        "revision": revision,
        "display_name": display_name,
        "company": company,
        "resin": resin,
        "properties": properties,
        "copied_from": copied_from,
    }
    digest = (
        hashlib.sha256(
            json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        )
        .hexdigest()
        .upper()
    )
    return MaterialRecord(
        identifier,
        revision,
        digest,
        display_name,
        company,
        resin,
        "USER_SUPPLIED_SESSION_DATA",
        tuple(entries),
        tuple(sorted(PROPERTY_IDS - set(properties))),
    )


def temperature_fahrenheit(value: str, unit: Literal["degF", "degC"]) -> Decimal:
    temperature = decimal_input(value)
    if unit == "degF":
        return temperature
    if unit == "degC":
        return temperature * Decimal(9) / Decimal(5) + Decimal(32)
    raise ValueError("MAT1 temperature unit must be degF or degC.")


@dataclass(frozen=True, slots=True)
class TemperatureCandidates:
    strength: Decimal | None
    modulus: Decimal | None
    rule: str


def temperature_candidates(resin: Resin, temperature_f: Decimal) -> TemperatureCandidates:
    """Exact Table 2-2 arithmetic candidates, with no extrapolation."""

    if resin == "OTHER":
        return TemperatureCandidates(None, None, "RESIN_TEMPERATURE_MODEL_REQUIRED")
    if temperature_f <= 90:
        return TemperatureCandidates(Decimal(1), Decimal(1), "REFERENCE_COEFFICIENT_POLICY")
    if temperature_f > 140:
        return TemperatureCandidates(None, None, "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED")
    if resin == "VINYL_ESTER":
        return TemperatureCandidates(
            Decimal("1.7") - Decimal("0.008") * temperature_f,
            Decimal("1.5") - Decimal("0.006") * temperature_f,
            "TABLE_2_2_COEFFICIENT_CANDIDATE",
        )
    if resin == "ISOPHTHALIC_POLYESTER":
        return TemperatureCandidates(
            Decimal("1.9") - Decimal("0.010") * temperature_f,
            Decimal("1.7") - Decimal("0.008") * temperature_f,
            "TABLE_2_2_COEFFICIENT_CANDIDATE",
        )
    raise ValueError("MAT1 resin is invalid.")


def moisture_candidates(moisture: Moisture) -> tuple[Decimal | None, Decimal | None]:
    if moisture == "REFERENCE":
        return Decimal(1), Decimal(1)
    if moisture == "SUSTAINED_MOISTURE":
        return Decimal("0.75"), Decimal("0.90")
    if moisture in {"OTHER", "UNKNOWN"}:
        return None, None
    raise ValueError("MAT1 moisture state is invalid.")


def thermal_gate(sustained_f: Decimal, maximum_f: Decimal, tg_f: Decimal | None) -> str:
    if maximum_f < sustained_f:
        raise ValueError("Maximum material temperature cannot be below sustained temperature.")
    if sustained_f > 140:
        return "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED"
    if tg_f is None:
        return "TG_REQUIRED"
    limit = tg_f - Decimal(40)
    if maximum_f > limit:
        return "MAX_SERVICE_TEMPERATURE_EXCEEDED"
    if sustained_f > 90 and sustained_f == limit:
        return "TEMPERATURE_FACTOR_BOUNDARY_REVIEW"
    return "WITHIN_NUMERICAL_THERMAL_DOMAIN_ONLY"


@dataclass(frozen=True, slots=True)
class DesignConditions:
    sustained_f: Decimal
    maximum_f: Decimal
    tg_f: Decimal | None
    moisture: Moisture
    chemical: Exposure
    load_case_name: str
    time_category: TimeEffectCategory
    source_reference_condition: Literal["REFERENCE", "ALREADY_ADJUSTED", "UNKNOWN"]
    chemical_substance: str = ""
    chemical_concentration: str = ""
    chemical_contact_form: str = ""
    chemical_duration: str = ""
    uv_weathering: Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"] = "UNKNOWN"
    freeze_thaw: Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"] = "UNKNOWN"
    protective_measures: str = ""
    exposure_notes: str = ""
    action_provenance: str = ""
    live_load_subtype: str = ""
    full_amplitude_duration: str = ""
    design_period: str = ""
    service_period: str = ""
    fatigue_cycles: str = ""


@dataclass(frozen=True, slots=True)
class PropertyLedger:
    component_id: str
    record_id: str
    record_revision: str
    property_id: str
    original: Decimal
    unit: str
    basis: str
    cm: Decimal | None
    ct: Decimal | None
    cch: Decimal | None
    adjusted_candidate: Decimal | None
    lambda_factor: Decimal | None
    issues: tuple[str, ...]
    content_digest: str


def property_ledger(
    component_id: str,
    record: MaterialRecord,
    property_id: str,
    conditions: DesignConditions,
) -> PropertyLedger:
    """Resolve a numerical candidate and explicitly keep source gates visible."""

    prop = record.property(property_id)
    if prop is None:
        raise ValueError(f"MAT1_PROPERTY_REQUIRED:{property_id}")
    issues: list[str] = []
    if prop.id in PULL_THROUGH_IDS:
        issues.append("PULL_THROUGH_TEST_THICKNESS_AND_WASHER_APPLICABILITY_REQUIRED")
    if prop.id in STRENGTH_IDS:
        role = "STRENGTH"
    elif prop.id in MODULUS_IDS:
        role = "MODULUS"
    else:
        role = "OTHER"
    temp = temperature_candidates(record.resin, conditions.sustained_f)
    moisture_strength, moisture_modulus = moisture_candidates(conditions.moisture)
    ct = temp.strength if role == "STRENGTH" else temp.modulus if role == "MODULUS" else None
    cm = (
        moisture_strength if role == "STRENGTH" else moisture_modulus if role == "MODULUS" else None
    )
    if role == "OTHER":
        issues.append("PROPERTY_SPECIFIC_ADJUSTMENT_APPLICABILITY_REQUIRED")
    if ct is None and role != "OTHER":
        issues.append(temp.rule)
    if cm is None and role != "OTHER":
        issues.append("MOISTURE_ADJUSTMENT_SOURCE_REQUIRED")
    gate = thermal_gate(conditions.sustained_f, conditions.maximum_f, conditions.tg_f)
    if gate != "WITHIN_NUMERICAL_THERMAL_DOMAIN_ONLY":
        issues.append(gate)
    if conditions.source_reference_condition == "UNKNOWN":
        issues.append("SOURCE_REFERENCE_CONDITION_REQUIRED")
    elif conditions.source_reference_condition == "ALREADY_ADJUSTED":
        issues.append("ALREADY_ADJUSTED_SOURCE_FACTOR_DUPLICATION_REVIEW")
    if prop.basis == "ALREADY_ADJUSTED":
        issues.append("ALREADY_ADJUSTED_PROPERTY_FACTOR_DUPLICATION_REVIEW")
    if prop.basis != "CHARACTERISTIC" and role == "STRENGTH":
        issues.append("STRENGTH_CHARACTERISTIC_BASIS_NOT_ESTABLISHED")
    if conditions.chemical == "SPECIFIED":
        issues.append("CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED")
    elif conditions.chemical == "UNKNOWN":
        issues.append("CHEMICAL_EXPOSURE_UNRESOLVED")
    if record.source_kind == "OWNER_SUPPLIED_NOMINAL_DATASET":
        issues.append("OWNER_NOMINAL_SOURCE_QUALIFICATION_REQUIRED")
    if conditions.uv_weathering != "NONE_DECLARED":
        issues.append("UV_WEATHERING_APPLICABILITY_SOURCE_REQUIRED")
    if conditions.freeze_thaw != "NONE_DECLARED":
        issues.append("FREEZE_THAW_APPLICABILITY_SOURCE_REQUIRED")
    if conditions.fatigue_cycles:
        issues.append("FATIGUE_RECORDED_ONLY_APPLICABILITY_REQUIRED")
    cch = Decimal(1) if conditions.chemical == "NONE_DECLARED" else None
    adjusted = (
        prop.original * cm * ct * cch
        if (
            cm is not None
            and ct is not None
            and cch is not None
            and role != "OTHER"
            and conditions.source_reference_condition != "ALREADY_ADJUSTED"
            and prop.basis != "ALREADY_ADJUSTED"
        )
        else None
    )
    time_factor = (
        select_time_effect_factor(conditions.time_category).value if role == "STRENGTH" else None
    )
    return PropertyLedger(
        component_id,
        record.id,
        record.revision,
        property_id,
        prop.original,
        prop.unit,
        prop.basis,
        cm,
        ct,
        cch,
        adjusted,
        time_factor,
        tuple(dict.fromkeys(issues)),
        record.content_digest,
    )
