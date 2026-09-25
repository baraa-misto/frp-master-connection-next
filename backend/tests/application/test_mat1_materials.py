"""Independent MAT1 source, arithmetic, and fail-closed boundary checks."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from importlib.resources import files
from typing import Any, Literal, cast

import pytest

import frp_master_connection.application.mat1_materials as mat1
from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    Resin,
    catalog_record,
    decimal_input,
    moisture_candidates,
    predefined_catalog,
    property_ledger,
    session_record,
    temperature_candidates,
    temperature_fahrenheit,
    thermal_gate,
)
from frp_master_connection.calculation.inputs import TimeEffectCategory


def conditions(
    *,
    moisture: Literal["REFERENCE", "SUSTAINED_MOISTURE", "OTHER", "UNKNOWN"] = (
        "SUSTAINED_MOISTURE"
    ),
    source_reference_condition: Literal["REFERENCE", "ALREADY_ADJUSTED", "UNKNOWN"] = ("UNKNOWN"),
) -> DesignConditions:
    return DesignConditions(
        sustained_f=Decimal(120),
        maximum_f=Decimal(130),
        tg_f=None,
        moisture=moisture,
        chemical="NONE_DECLARED",
        load_case_name="LC-1",
        time_category=TimeEffectCategory.OTHER_LIVE,
        source_reference_condition=source_reference_condition,
    )


def test_exact_owner_seed_and_revision_binding() -> None:
    poly, vinyl = predefined_catalog()
    assert len(poly.properties) == len(vinyl.properties) == 16
    differing = {
        item.id
        for item in poly.properties
        if item.original != vinyl.property(item.id).original  # type: ignore[union-attr]
    }
    assert differing == {"tensile_strength_L", "tensile_strength_T"}
    assert poly.property("tensile_strength_L").original == Decimal(33)  # type: ignore[union-attr]
    assert vinyl.property("tensile_strength_L").original == Decimal("37.5")  # type: ignore[union-attr]
    assert poly.property("compressive_strength_L").original == Decimal(33)  # type: ignore[union-attr]
    assert catalog_record(poly.id, poly.revision, poly.content_digest) == poly
    with pytest.raises(ValueError, match="MISMATCH"):
        catalog_record(poly.id, poly.revision, vinyl.content_digest)
    for record in (poly, vinyl):
        for size in ("3_8", "1_2", "3_4"):
            prop = record.property(f"pull_through_{size}_as_labeled")
            assert prop is not None
            assert "BOLT_SIZE_LABEL_ONLY" in prop.applicability[0]


@pytest.mark.parametrize(
    ("resin", "temperature", "strength", "modulus"),
    [
        ("VINYL_ESTER", "90", "1", "1"),
        ("VINYL_ESTER", "90.001", "0.979992", "0.959994"),
        ("VINYL_ESTER", "120", "0.74", "0.78"),
        ("ISOPHTHALIC_POLYESTER", "120", "0.7", "0.74"),
        ("ISOPHTHALIC_POLYESTER", "140", "0.5", "0.58"),
    ],
)
def test_temperature_coefficients(
    resin: str, temperature: str, strength: str, modulus: str
) -> None:
    result = temperature_candidates(resin, Decimal(temperature))  # type: ignore[arg-type]
    assert result.strength == Decimal(strength)
    assert result.modulus == Decimal(modulus)


def test_temperature_units_table_limit_and_tg_boundaries() -> None:
    assert temperature_fahrenheit("60", "degC") == Decimal(140)
    assert temperature_candidates("VINYL_ESTER", Decimal("140.001")).strength is None
    assert temperature_candidates("OTHER", Decimal(100)).modulus is None
    assert thermal_gate(Decimal(120), Decimal(160), Decimal(200)) == (
        "WITHIN_NUMERICAL_THERMAL_DOMAIN_ONLY"
    )
    assert thermal_gate(Decimal(140), Decimal(140), Decimal(180)) == (
        "TEMPERATURE_FACTOR_BOUNDARY_REVIEW"
    )
    assert thermal_gate(Decimal(120), Decimal(170), Decimal(200)) == (
        "MAX_SERVICE_TEMPERATURE_EXCEEDED"
    )
    with pytest.raises(ValueError, match="below sustained"):
        thermal_gate(Decimal(120), Decimal(110), None)


def test_moisture_and_source_gates_are_separate_from_arithmetic() -> None:
    poly = predefined_catalog()[0]
    assert moisture_candidates("SUSTAINED_MOISTURE") == (
        Decimal("0.75"),
        Decimal("0.90"),
    )
    assert moisture_candidates("UNKNOWN") == (None, None)
    strength = property_ledger("PLATE", poly, "tensile_strength_L", conditions())
    modulus = property_ledger("PLATE", poly, "tensile_modulus_L", conditions())
    assert strength.adjusted_candidate == Decimal("17.325")
    assert strength.lambda_factor == Decimal("0.8")
    assert modulus.adjusted_candidate == Decimal("1998")
    assert modulus.lambda_factor is None
    assert "TG_REQUIRED" in strength.issues
    assert "SOURCE_REFERENCE_CONDITION_REQUIRED" in strength.issues
    assert "OWNER_NOMINAL_SOURCE_QUALIFICATION_REQUIRED" in strength.issues
    assert (
        property_ledger(
            "PLATE", poly, "tensile_strength_L", conditions(moisture="UNKNOWN")
        ).adjusted_candidate
        is None
    )
    already = property_ledger(
        "PLATE",
        poly,
        "tensile_strength_L",
        conditions(source_reference_condition="ALREADY_ADJUSTED"),
    )
    assert already.adjusted_candidate is None
    assert "ALREADY_ADJUSTED_SOURCE_FACTOR_DUPLICATION_REVIEW" in already.issues


def test_session_data_cannot_impersonate_catalog_and_stays_unqualified() -> None:
    source = predefined_catalog()[0]
    values = {
        "tensile_strength_L": {
            "label": "Longitudinal tensile strength",
            "symbol": "Ft,L",
            "value": "44",
            "unit": "ksi",
            "basis": "NOMINAL_AS_SUPPLIED",
        }
    }
    custom = session_record(
        "SESSION:one", "rev-1", "My material", "User", "VINYL_ESTER", values, source.id
    )
    assert custom.property("tensile_strength_L").original == Decimal(44)  # type: ignore[union-attr]
    assert custom.source_kind == "USER_SUPPLIED_SESSION_DATA"
    values["tensile_strength_L"]["value"] = "66"
    assert custom.property("tensile_strength_L").original == Decimal(44)  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="namespace"):
        session_record(source.id, "rev-1", "Forged", "User", "VINYL_ESTER", values)
    values["tensile_strength_L"]["qualification"] = "QUALIFIED"
    with pytest.raises(ValueError, match="fields"):
        session_record("SESSION:two", "rev-1", "Forged", "User", "VINYL_ESTER", values)


@pytest.mark.parametrize(
    "raw",
    [12, True, 1.5, "NaN", "Infinity", "-Infinity", "not a number"],
)
def test_material_numeric_inputs_reject_implicit_and_nonfinite_values(raw: object) -> None:
    with pytest.raises(ValueError, match="MAT1"):
        decimal_input(cast(Any, raw))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "ICE:FORGED"}, "namespace"),
        ({"revision": ""}, "identity fields"),
        ({"display_name": ""}, "identity fields"),
        ({"company": ""}, "identity fields"),
        ({"resin": "UNLISTED"}, "resin"),
        ({"properties": {}}, "unknown or no fields"),
        (
            {
                "properties": {
                    "unknown": {
                        "label": "x",
                        "symbol": "x",
                        "value": "1",
                        "unit": "ksi",
                        "basis": "MEAN",
                    }
                }
            },
            "unknown or no fields",
        ),
        ({"property_extra": "QUALIFIED"}, "fields"),
        ({"unit": "lbf"}, "incompatible"),
        ({"value": "0"}, "positive"),
        ({"value": "-2"}, "positive"),
        ({"basis": "QUALIFIED"}, "basis"),
        ({"label": ""}, "nonempty"),
        ({"symbol": ""}, "nonempty"),
    ],
)
def test_session_validation_never_promotes_user_data(
    change: dict[str, object], message: str
) -> None:
    source: dict[str, object] = {
        "id": "SESSION:validated",
        "revision": "1",
        "display_name": "Synthetic coupon",
        "company": "Test only",
        "resin": "VINYL_ESTER",
        "properties": {
            "tensile_strength_L": {
                "label": "Longitudinal tension",
                "symbol": "Ft,L",
                "value": "40",
                "unit": "ksi",
                "basis": "NOMINAL_AS_SUPPLIED",
            }
        },
    }
    for key, value in change.items():
        if key == "property_extra":
            cast(dict[str, dict[str, str]], source["properties"])["tensile_strength_L"][
                str(value)
            ] = "yes"
        elif key in {"unit", "value", "basis", "label", "symbol"}:
            cast(dict[str, dict[str, str]], source["properties"])["tensile_strength_L"][key] = str(
                value
            )
        else:
            source[key] = value
    with pytest.raises(ValueError, match=message):
        session_record(
            cast(str, source["id"]),
            cast(str, source["revision"]),
            cast(str, source["display_name"]),
            cast(str, source["company"]),
            cast(Resin, source["resin"]),
            cast(dict[str, dict[str, str]], source["properties"]),
        )


def test_session_dimensions_preserve_pull_through_labels_and_ratio() -> None:
    record = session_record(
        "SESSION:mixed",
        "1",
        "Synthetic coupon",
        "Test only",
        "OTHER",
        {
            "pull_through_1_2_as_labeled": {
                "label": "Pull-through as labeled",
                "symbol": "Ppt,1/2",
                "value": "100",
                "unit": "lbf",
                "basis": "NOMINAL_AS_SUPPLIED",
            },
            "major_poisson_ratio_LT": {
                "label": "Poisson ratio",
                "symbol": "nuLT",
                "value": "0.2",
                "unit": "dimensionless",
                "basis": "MEAN",
            },
        },
    )
    pull = record.property("pull_through_1_2_as_labeled")
    assert pull is not None
    assert pull.applicability == ("BOLT_SIZE_LABEL_ONLY; TESTED_FRP_THICKNESS_AND_WASHER_UNKNOWN",)
    assert pull.source_bolt_diameter_in is None
    ratio = property_ledger("MEMBER", record, "major_poisson_ratio_LT", conditions())
    assert ratio.adjusted_candidate is None
    assert ratio.lambda_factor is None
    assert "PROPERTY_SPECIFIC_ADJUSTMENT_APPLICABILITY_REQUIRED" in ratio.issues


def test_distinct_exposure_and_source_gates_are_visible_in_factor_ledger() -> None:
    poly = predefined_catalog()[0]
    base = conditions(source_reference_condition="REFERENCE", moisture="REFERENCE")
    base = replace(
        base,
        sustained_f=Decimal(100),
        maximum_f=Decimal(100),
        tg_f=Decimal(180),
        chemical="NONE_DECLARED",
        uv_weathering="NONE_DECLARED",
        freeze_thaw="NONE_DECLARED",
    )
    clean = property_ledger("MEMBER", poly, "tensile_strength_L", base)
    assert clean.adjusted_candidate == Decimal("29.70")
    assert clean.lambda_factor == Decimal("0.8")
    assert "SOURCE_REFERENCE_CONDITION_REQUIRED" not in clean.issues
    assert "OWNER_NOMINAL_SOURCE_QUALIFICATION_REQUIRED" in clean.issues
    exposed = property_ledger(
        "MEMBER",
        poly,
        "tensile_strength_L",
        replace(
            base,
            chemical="SPECIFIED",
            uv_weathering="SPECIFIED",
            freeze_thaw="SPECIFIED",
            fatigue_cycles="10000",
        ),
    )
    assert exposed.adjusted_candidate is None
    assert {
        "CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED",
        "UV_WEATHERING_APPLICABILITY_SOURCE_REQUIRED",
        "FREEZE_THAW_APPLICABILITY_SOURCE_REQUIRED",
        "FATIGUE_RECORDED_ONLY_APPLICABILITY_REQUIRED",
    }.issubset(exposed.issues)
    unknown = property_ledger(
        "MEMBER", poly, "tensile_modulus_L", replace(base, chemical="UNKNOWN", moisture="OTHER")
    )
    assert unknown.adjusted_candidate is None
    assert "CHEMICAL_EXPOSURE_UNRESOLVED" in unknown.issues
    assert "MOISTURE_ADJUSTMENT_SOURCE_REQUIRED" in unknown.issues
    assert unknown.lambda_factor is None


def test_temperature_and_adjusted_source_boundaries_are_fail_closed() -> None:
    poly = predefined_catalog()[0]
    base = conditions(source_reference_condition="REFERENCE", moisture="REFERENCE")
    assert temperature_fahrenheit("90", "degF") == Decimal(90)
    with pytest.raises(ValueError, match="unit"):
        temperature_fahrenheit("90", cast(Any, "K"))
    assert moisture_candidates("REFERENCE") == (Decimal(1), Decimal(1))
    assert moisture_candidates("OTHER") == (None, None)
    with pytest.raises(ValueError, match="state"):
        moisture_candidates(cast(Any, "WET_UNKNOWN"))
    assert (
        thermal_gate(Decimal(141), Decimal(141), Decimal(200))
        == "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED"
    )
    assert thermal_gate(Decimal(90), Decimal(90), None) == "TG_REQUIRED"
    assert temperature_candidates("OTHER", Decimal(90)).strength is None
    with pytest.raises(ValueError, match="resin"):
        temperature_candidates(cast(Any, "BAD"), Decimal(100))
    with pytest.raises(ValueError, match="MAT1_PROPERTY_REQUIRED"):
        property_ledger("MEMBER", poly, "transverse_compression_missing", base)
    pull = property_ledger("PLATE", poly, "pull_through_1_2_as_labeled", base)
    assert pull.adjusted_candidate is None
    assert pull.lambda_factor is None
    assert "PULL_THROUGH_TEST_THICKNESS_AND_WASHER_APPLICABILITY_REQUIRED" in pull.issues
    tensile = poly.property("tensile_strength_L")
    assert tensile is not None
    preadjusted = replace(tensile, basis="ALREADY_ADJUSTED")
    record = replace(poly, properties=(preadjusted,))
    ledger = property_ledger("MEMBER", record, "tensile_strength_L", base)
    assert ledger.adjusted_candidate is None
    assert "ALREADY_ADJUSTED_PROPERTY_FACTOR_DUPLICATION_REVIEW" in ledger.issues
    unknown_resin = property_ledger(
        "MEMBER",
        replace(poly, resin="OTHER"),
        "tensile_strength_L",
        replace(base, sustained_f=Decimal(100), maximum_f=Decimal(100)),
    )
    assert unknown_resin.adjusted_candidate is None
    assert "RESIN_TEMPERATURE_MODEL_REQUIRED" in unknown_resin.issues


def test_catalog_rejects_tampering_and_accepts_data_only_addition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_bytes = files("frp_master_connection").joinpath(mat1.SEED_PATH).read_bytes()
    original = json.loads(seed_bytes)
    assert isinstance(original, dict)
    additional: dict[str, Any] = {"format": "MAT1_CATALOG_ADDITIONS_RC0", "records": []}

    class Resource:
        def __init__(self, name: str, seed: bytes, extras: dict[str, Any]) -> None:
            self.name, self.seed, self.extras = name, seed, extras

        def read_bytes(self) -> bytes:
            assert self.name == mat1.SEED_PATH
            return self.seed

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            assert self.name == "data/mat1_catalog_records.json"
            return json.dumps(self.extras)

    class Root:
        def __init__(self, seed: bytes, extras: dict[str, Any]) -> None:
            self.seed, self.extras = seed, extras

        def joinpath(self, name: str) -> Resource:
            return Resource(name, self.seed, self.extras)

    def load_changed(
        seed: dict[str, Any],
        extras: dict[str, Any],
        *,
        wrong_hash: bool = False,
    ) -> tuple[mat1.MaterialRecord, ...]:
        raw = json.dumps(seed).encode()
        digest = "0" * 64 if wrong_hash else hashlib.sha256(raw).hexdigest().upper()
        with monkeypatch.context() as patcher:
            patcher.setattr(mat1, "files", lambda _package: Root(raw, extras))
            patcher.setattr(mat1, "SEED_SHA256", digest)
            mat1.predefined_catalog.cache_clear()
            try:
                return mat1.predefined_catalog()
            finally:
                mat1.predefined_catalog.cache_clear()

    with pytest.raises(ValueError, match="checksum"):
        load_changed(original, additional, wrong_hash=True)
    bad_identity = deepcopy(original)
    bad_identity["records"][0]["proposed_record_id"] = "OTHER_ID"
    with pytest.raises(ValueError, match="identity"):
        load_changed(bad_identity, additional)
    bad_difference = deepcopy(original)
    bad_difference["records"][1]["properties"]["compressive_strength_L"]["value"] = "35"
    with pytest.raises(ValueError, match="only two tensile"):
        load_changed(bad_difference, additional)
    with pytest.raises(ValueError, match="format"):
        load_changed(original, {"format": "UNKNOWN", "records": []})
    duplicate = deepcopy(original["records"][0])
    with pytest.raises(ValueError, match="unique"):
        load_changed(original, {"format": "MAT1_CATALOG_ADDITIONS_RC0", "records": [duplicate]})
    new_company = deepcopy(duplicate)
    new_company["proposed_record_id"] = "SYNTHETIC_COMPANY_TEST_ONLY"
    new_company["company"] = "Synthetic test data"
    new_company["resin"] = "Other"
    records = load_changed(
        original, {"format": "MAT1_CATALOG_ADDITIONS_RC0", "records": [new_company]}
    )
    assert len(records) == 3
    assert records[2].source_kind == "CONTROLLED_CATALOG_DATA_UNQUALIFIED"
    assert records[2].resin == "OTHER"


def test_catalog_record_rejects_incomplete_or_nonpositive_data() -> None:
    raw = json.loads(files("frp_master_connection").joinpath(mat1.SEED_PATH).read_bytes())
    source = raw["records"][0]
    no_id = deepcopy(source)
    no_id["proposed_record_id"] = ""
    with pytest.raises(ValueError, match="stable ID"):
        mat1._record(no_id, "OWNER_SUPPLIED_NOMINAL_DATASET")
    incomplete = deepcopy(source)
    incomplete["properties"].pop("bearing_strength_L")
    with pytest.raises(ValueError, match="exact 16"):
        mat1._record(incomplete, "OWNER_SUPPLIED_NOMINAL_DATASET")
    negative = deepcopy(source)
    negative["properties"]["tensile_strength_L"]["value"] = "-1"
    with pytest.raises(ValueError, match="positive"):
        mat1._record(negative, "OWNER_SUPPLIED_NOMINAL_DATASET")
