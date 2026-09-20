"""Integrity and schema tests for the controlling Calculation Slice 2 RC2 data."""

import hashlib
from pathlib import Path
from types import MappingProxyType

from frp_master_connection.calculation import (
    SLICE_2_CALCULATION_CONTRACT_VERSION,
    SLICE_2_CALCULATION_ENGINE_VERSION,
    SLICE_2_ENGINEERING_RULE_SET_VERSION,
    SLICE_2_EXECUTION_INPUT_SCHEMA,
    SLICE_2_FINGERPRINT_SCHEMA,
    SLICE_2_GOLDEN_SCHEMA,
    SLICE_2_RESULT_SCHEMA,
)
from tests.calculation.golden_loader import (
    SLICE_2_GOLDEN_PATH,
    SLICE_2_RC2_GOLDEN_PATH,
    load_slice_2_rc2_golden_fixture,
)

EXPECTED_RC2_IDS = {
    "RC2_E1_MAPPING_ASYMMETRIC",
    "RC2_APPENDIX_BRANCH_BOUNDARY_NB1",
    "RC2_FULL_NB1_E1_OVER_W_ABOVE_1",
    "RC2_FULL_NB1_E1_OVER_W_BELOW_1",
    "RC2_FULL_NB1_E1_OVER_W_EQUAL_1",
    "RC2_APPENDIX_COEFFICIENT_MATRIX_NB1_LBR_050",
    "RC2_CDELTA_REDUCED_PITCH_SCOPE",
    "RC2_FIRST_ROW_SIMPLIFIED_FULL_FACTOR_STACK",
    "RC2_UNKNOWN_LBR_A_EQUALS_B_TIE",
    "RC2_BLOCK_SHEAR_SINGLE_LAP_CONCENTRIC",
    "RC2_BLOCK_SHEAR_FULL_FACTOR_STACK",
    "RC2_BLOCK_SHEAR_NATIVE_SI_SOURCE",
    "RC2_BLOCK_SHEAR_ECCENTRICITY_TOLERANCE",
    "RC2_FULL_DOMAIN_SPR_EQUALS_1",
    "RC2_FULL_DOMAIN_W_EQUALS_NB_D",
    "RC2_FULL_DOMAIN_W_EQUALS_NB_DN",
    "RC2_FULL_DOMAIN_LBR_BELOW_ZERO",
    "RC2_FULL_DOMAIN_LBR_ABOVE_ONE",
    "RC2_FULL_DOMAIN_UNEXPECTED_ARITHMETIC_FAILURE",
    "RC2_ZERO_REQUIRED_CHECKS",
    "RC2_ZERO_DEMAND_POSITIVE_RESISTANCE",
    "RC2_ZERO_DESIGN_RESISTANCE",
    "RC2_NEGATIVE_DESIGN_RESISTANCE",
    "RC2_MISSING_REQUIRED_BOLT_AXIS_TENSION",
    "RC2_NONUNIFORM_PITCH_NO_AUTOMATIC_CDELTA",
    "RC2_SOURCE_EXEMPT_INTERROW_SHEAROUT",
    "RC2_SOURCE_EXEMPT_FIRST_ROW_NET_TENSION",
    "RC2_STAGGERED_FULLY_RESOLVED_EXTERNAL_PLAN",
    "RC2_UNEQUAL_ROWS_FULLY_RESOLVED_EXTERNAL_PLAN",
    "RC2_ENGINEER_DEFINED_ALL_NUMERICAL_PASS_BUT_QUALIFICATION",
    "RC2_MORE_THAN_THREE_ROWS_KNOWN_FAIL_AND_QUALIFICATION",
    "RC2_TWO_FRP_LAYERS_INDEPENDENT_EVALUATION",
    "RC2_FORCE_REVERSAL_PHYSICAL_ROW_ORDER",
    "RC2_SIMPLIFIED_FULL_ENVELOPE_EQUAL_TIE",
    "RC2_BLOCK_CANDIDATE_EQUAL_TIE",
    "RC2_UTILIZATION_WITHIN_EXISTING_TOLERANCE",
    "RC2_MONOTONIC_DEMAND",
    "RC2_MONOTONIC_THICKNESS",
    "RC2_MONOTONIC_HOLE_SIZE_FULL_METHOD",
    "RC2_MONOTONIC_ROW_FRACTION_BEARING",
}


def _ids(value: object) -> set[str]:
    result: set[str] = set()
    if isinstance(value, MappingProxyType):
        identity = value.get("id")
        if isinstance(identity, str) and identity.startswith("RC2_"):
            result.add(identity)
        for item in value.values():
            result.update(_ids(item))
    elif isinstance(value, tuple):
        for item in value:
            result.update(_ids(item))
    return result


def test_slice_2_rc2_artifact_hashes_and_schema_are_exact() -> None:
    repository_root = Path(__file__).parents[3]
    fixture = load_slice_2_rc2_golden_fixture()
    artifacts = {
        SLICE_2_RC2_GOLDEN_PATH: "B3A49FB44089E065F7B4659F52AB856288298247504423970C3D19B8FCEA7B0B",
        repository_root / "docs/engineering/CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC2.md": (
            "C296E5FB3B304985A62D49B3F486EF6DB8E5D212EDFE2B83AACB6D68E09B71FD"
        ),
        repository_root / "docs/qa/CALCULATION_SLICE_2_RC2_INDEPENDENT_VERIFICATION_LEDGER.md": (
            "F2E0A253C75503C3F8FA29E5E78A4A8E4DF98204A43CAF4B07000EC65183A7A4"
        ),
    }
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in artifacts
    } == artifacts
    assert fixture["schema_version"] == SLICE_2_GOLDEN_SCHEMA
    assert fixture["document_status"] == (
        "candidate engineering benchmark authority pending Baraa Misto approval; "
        "not authorized for production implementation until approved"
    )
    assert fixture["not_production_output"] is True


def test_slice_2_rc2_versions_and_parent_authority_are_exact() -> None:
    fixture = load_slice_2_rc2_golden_fixture()
    versions = fixture["proposed_slice_2_versions_after_approval_and_implementation"]
    assert isinstance(versions, MappingProxyType)
    assert versions["calculation_contract_version"] == SLICE_2_CALCULATION_CONTRACT_VERSION
    assert versions["calculation_engine_version"] == SLICE_2_CALCULATION_ENGINE_VERSION
    assert versions["engineering_rule_set_version"] == SLICE_2_ENGINEERING_RULE_SET_VERSION
    expected_schemas = {
        "execution_input_schema": (SLICE_2_EXECUTION_INPUT_SCHEMA, "0.1.0-draft"),
        "result_schema": (SLICE_2_RESULT_SCHEMA, "0.1.0-draft"),
        "fingerprint_schema": (SLICE_2_FINGERPRINT_SCHEMA, "0.1.0-draft"),
        "golden_schema": ("frp-master-connection-calculation-slice-2-golden", "RC2"),
    }
    for key, (identity, version) in expected_schemas.items():
        value = versions[key]
        assert isinstance(value, MappingProxyType)
        assert value == {"identity": identity, "version": version}
    assert versions["slice_1_result_identity_unchanged"] is True
    parent = fixture["parent_rc1_authority"]
    assert isinstance(parent, MappingProxyType)
    assert (
        hashlib.sha256(SLICE_2_GOLDEN_PATH.read_bytes()).hexdigest().upper()
        == parent["golden_sha256"]
    )
    assert parent["unchanged_and_still_required_for_regression"] is True


def test_slice_2_rc2_contains_every_approved_case_and_no_binary_floats() -> None:
    fixture = load_slice_2_rc2_golden_fixture()
    assert _ids(fixture) == EXPECTED_RC2_IDS

    def assert_no_float(value: object) -> None:
        assert not isinstance(value, float)
        if isinstance(value, MappingProxyType):
            for item in value.values():
                assert_no_float(item)
        elif isinstance(value, tuple):
            for item in value:
                assert_no_float(item)

    assert_no_float(fixture)
