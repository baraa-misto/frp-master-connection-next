"""Schema and immutability checks for the approved RC2 golden JSON."""

import json
from types import MappingProxyType
from unittest.mock import patch

import pytest

from tests.calculation.golden_loader import (
    EXPECTED_BENCHMARKS,
    GOLDEN_PATH,
    decimal_strings,
    load_golden_fixture,
)


def test_golden_fixture_root_source_units_snapshots_and_benchmark_ids() -> None:
    fixture = load_golden_fixture()
    assert fixture["document_status"] == "ENGINEERING_SPECIFICATION_RC2_APPROVED_FOR_STAGE_2_1A"
    assert fixture["calculation_family"] == "ASCE74_23_CH8_SINGLE_BOLT_SINGLE_ROW_FRP"
    standard = fixture["standard"]
    assert isinstance(standard, MappingProxyType)
    assert standard["name"] == "ASCE/SEI 74-23"
    assert standard["errata"] == "Erratum 1"
    assert standard["errata_effective_date"] == "2026-01-13"
    assert standard["chapter_8_affected_by_errata"] is False
    constants = fixture["unit_constants"]
    assert isinstance(constants, MappingProxyType)
    assert constants["inch_to_mm_exact"] == "25.4"
    assert constants["lbf_to_N_exact"] == "4.4482216152605"
    benchmarks = fixture["benchmarks"]
    assert isinstance(benchmarks, MappingProxyType)
    assert set(benchmarks) == EXPECTED_BENCHMARKS
    material = fixture["initial_material_snapshot"]
    assert isinstance(material, MappingProxyType)
    assert material["id"] == "ICE_LOCKED_PULTRUDED_FRP"
    assert material["known_missing_property"] == "FC_T"
    fastener = fixture["default_fastener_snapshot"]
    assert isinstance(fastener, MappingProxyType)
    assert fastener["id"] == "ASTM_F593_17_GROUP_2_316_316L"
    assert fastener["Fnt_status"] == "SOURCE_DATA_PENDING"
    assert fastener["Fnt_value"] is None


def test_golden_expected_results_remain_data_and_decimal_strings_parse() -> None:
    fixture = load_golden_fixture()
    values = decimal_strings(fixture)
    assert values
    assert all(value.is_finite() for value in values)
    benchmarks = fixture["benchmarks"]
    assert isinstance(benchmarks, MappingProxyType)
    p2b = benchmarks["P2B"]
    assert isinstance(p2b, MappingProxyType)
    assert p2b["known_numerical_outcome"] == "FAIL"
    assert p2b["aggregate"] == "FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK"
    expectations = fixture["stage_2_1a_expectations"]
    assert isinstance(expectations, MappingProxyType)
    assert expectations["no_executable_resistance_equations"] is True
    assert expectations["golden_expected_results_are_fixture_data_only"] is True


def test_golden_loading_is_deterministic_recursive_and_immutable() -> None:
    first = load_golden_fixture()
    second = load_golden_fixture()
    assert first == second
    with pytest.raises(TypeError):
        first["document_status"] = "changed"  # type: ignore[index]
    benchmarks = first["benchmarks"]
    assert isinstance(benchmarks, MappingProxyType)
    with pytest.raises(TypeError):
        benchmarks["P1"] = "changed"  # type: ignore[index]


def test_golden_loader_rejects_duplicate_keys_nonobject_roots_and_numeric_json() -> None:
    with (
        patch.object(type(GOLDEN_PATH), "read_text", return_value='{"a": 1, "a": 2}'),
        pytest.raises(ValueError, match="Duplicate JSON object key"),
    ):
        load_golden_fixture()
    with (
        patch.object(type(GOLDEN_PATH), "read_text", return_value="[]"),
        pytest.raises(ValueError, match="root must be an object"),
    ):
        load_golden_fixture()
    with (
        patch.object(type(GOLDEN_PATH), "read_text", return_value='{"value": 1.5}'),
        pytest.raises(TypeError, match="unsupported value type float"),
    ):
        load_golden_fixture()
    assert json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["approved_by"] == "Baraa Misto"


def test_decimal_string_loader_ignores_text_booleans_and_nulls() -> None:
    assert decimal_strings("not-a-number") == ()
    assert decimal_strings(True) == ()
    assert decimal_strings(None) == ()
    assert decimal_strings(("1.5", "text"))[0].is_finite()
