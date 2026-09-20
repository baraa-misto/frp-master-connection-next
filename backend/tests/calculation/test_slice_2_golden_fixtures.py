"""Integrity, schema, and controlled-identity tests for the Slice 2 RC1 golden."""

import hashlib
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import pytest

from frp_master_connection.calculation import (
    CALCULATION_ENGINE_VERSION,
    ENGINEERING_RULE_SET_VERSION,
    ConnectedMaterialPair,
    prescribed_row_fractions,
)
from tests.calculation.golden_loader import (
    GOLDEN_PATH,
    SLICE_2_GOLDEN_PATH,
    load_slice_2_golden_fixture,
)

EXPECTED_SLICE_2_CASE_IDS = {
    "MR2_FRP_FRP_NB1_L",
    "MR2_FRP_STEEL_NB1_L_FAIL",
    "MR3_FRP_FRP_NB1_L",
    "MR3_FRP_STEEL_NB1_L",
    "MR2_FRP_FRP_NB2_T",
    "MR5_NB2_AUTO_L",
    "MR6_NB3_AUTO_T_FAIL",
    "MR5_NB2_ENGINEER_DEFINED_L",
    "MR2_FRP_FRP_NB1_L_SINGLE_LAP",
    "BS_U3_CONCENTRIC",
    "BS_U3_ECCENTRIC",
    "BS_L3_CONCENTRIC",
    "BS_U5_CONCENTRIC",
    "BS_L5_CONCENTRIC",
    "BS_U3_NET_AREA_BELOW_75_PERCENT",
    "CT_PLATE_CONFLICT_NB1_LBR_050",
    "GEOM_4_ROWS_VALID",
    "GEOM_4_BOLTS_PER_ROW",
    "UNEVEN_ROW_BOLT_COUNTS",
    "STAGGERED_GROUP",
    "ROW_FRACTIONS_DO_NOT_SUM_TO_ONE",
}


def _case_ids(value: object) -> set[str]:
    identities: set[str] = set()
    if isinstance(value, MappingProxyType):
        for key, item in value.items():
            if key in {"id", "case_id"} and isinstance(item, str):
                identities.add(item)
            identities.update(_case_ids(item))
    elif isinstance(value, tuple):
        for item in value:
            identities.update(_case_ids(item))
    return identities


def test_slice_2_golden_hash_schema_identity_and_active_versions() -> None:
    fixture = load_slice_2_golden_fixture()
    digest = hashlib.sha256(SLICE_2_GOLDEN_PATH.read_bytes()).hexdigest().upper()

    assert digest == "C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610"
    assert fixture["schema_version"] == "frp-master-connection-calculation-slice-2-golden-rc1"
    assert fixture["not_production_output"] is True
    assert fixture["specification_id"] == (
        "FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1"
    )
    assert fixture["active_engine_version_before_implementation"] == CALCULATION_ENGINE_VERSION
    assert fixture["active_rule_set_before_implementation"] == ENGINEERING_RULE_SET_VERSION
    assert fixture["existing_rc2_golden_sha256"] == (
        "39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392"
    )


def test_slice_2_golden_contains_every_controlled_benchmark_id() -> None:
    fixture = load_slice_2_golden_fixture()
    assert _case_ids(fixture) == EXPECTED_SLICE_2_CASE_IDS
    distributions = fixture["prescribed_row_distributions"]
    assert isinstance(distributions, MappingProxyType)
    assert set(distributions) == {"FRP_FRP_2", "FRP_STEEL_2", "FRP_FRP_3", "FRP_STEEL_3"}


@pytest.mark.parametrize(
    ("golden_id", "material_pair", "row_count"),
    [
        ("FRP_FRP_2", ConnectedMaterialPair.FRP_FRP, 2),
        ("FRP_STEEL_2", ConnectedMaterialPair.FRP_STEEL, 2),
        ("FRP_FRP_3", ConnectedMaterialPair.FRP_FRP, 3),
        ("FRP_STEEL_3", ConnectedMaterialPair.FRP_STEEL, 3),
    ],
)
def test_production_prescribed_distributions_match_unchanged_slice_2_golden(
    golden_id: str,
    material_pair: ConnectedMaterialPair,
    row_count: int,
) -> None:
    fixture = load_slice_2_golden_fixture()
    distributions = fixture["prescribed_row_distributions"]
    assert isinstance(distributions, MappingProxyType)
    values = distributions[golden_id]
    assert isinstance(values, tuple)
    expected: list[Decimal] = []
    for value in values:
        assert isinstance(value, str)
        expected.append(Decimal(value))

    actual = prescribed_row_fractions(material_pair, row_count)
    assert actual == tuple(expected)
    assert sum(actual, Decimal(0)) == Decimal(1)


def test_slice_2_golden_exact_conversions_and_unit_source_policy() -> None:
    fixture = load_slice_2_golden_fixture()
    conversions = fixture["exact_conversions"]
    assert isinstance(conversions, MappingProxyType)
    assert conversions["inch_to_mm"] == "25.400000000000"
    assert conversions["kip_to_kN"] == "4.4482216152605"
    assert conversions["ksi_to_MPa"] == "6.8947572931683613"
    unit_policy = fixture["unit_equivalence_policy"]
    assert isinstance(unit_policy, MappingProxyType)
    assert unit_policy["basis"] == (
        "Convert stored physical values; do not regenerate the ordinary hole from the "
        "alternate printed unit representation."
    )


def test_slice_2_loader_is_recursive_immutable_and_accepts_integer_geometry_counts() -> None:
    first = load_slice_2_golden_fixture()
    second = load_slice_2_golden_fixture()
    assert first == second
    cases = first["prescriptive_cases"]
    assert isinstance(cases, tuple)
    first_case = cases[0]
    assert isinstance(first_case, MappingProxyType)
    geometry = first_case["geometry"]
    assert isinstance(geometry, MappingProxyType)
    assert geometry["row_count"] == 2
    with pytest.raises(TypeError):
        geometry["row_count"] = 3  # type: ignore[index]


def test_slice_2_loader_rejects_duplicate_keys_nonobject_roots_and_floats() -> None:
    with (
        patch.object(type(SLICE_2_GOLDEN_PATH), "read_text", return_value='{"a": 1, "a": 2}'),
        pytest.raises(ValueError, match="Duplicate JSON object key"),
    ):
        load_slice_2_golden_fixture()
    with (
        patch.object(type(SLICE_2_GOLDEN_PATH), "read_text", return_value="[]"),
        pytest.raises(ValueError, match="root must be an object"),
    ):
        load_slice_2_golden_fixture()
    with (
        patch.object(type(SLICE_2_GOLDEN_PATH), "read_text", return_value='{"value": 1.5}'),
        pytest.raises(TypeError, match="unsupported value type float"),
    ):
        load_slice_2_golden_fixture()


def test_existing_rc2_fixture_and_slice_2_specification_hashes_are_unchanged() -> None:
    repository_root = Path(__file__).parents[3]
    rc2_hash = hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest().upper()
    specification = (
        repository_root
        / "docs"
        / "engineering"
        / "CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1.md"
    )
    specification_hash = hashlib.sha256(specification.read_bytes()).hexdigest().upper()

    assert rc2_hash == "39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392"
    assert specification_hash == "44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99"
