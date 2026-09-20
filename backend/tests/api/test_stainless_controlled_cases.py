"""Immutable CME-3 case identities and exact public role-boundary channels."""

import hashlib
import json
from pathlib import Path

import pytest
from tests.api.test_connector_materials import SS, envelope, http

from frp_master_connection.application.stainless_family_activation import public_role_denial

GOLDEN = (
    Path(__file__).parents[1]
    / "golden/FRP_MASTER_CONNECTION_CME_3_316SS_PUBLIC_ACTIVATION_GOLDEN_BENCHMARKS_RC1.json"
)
DATA = json.loads(GOLDEN.read_bytes())


def test_controlled_case_counts_and_hash_remain_exact_with_i11_superseded_only() -> None:
    assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper() == (
        "F0D1520638E8A0B5EE58C1F9F9A7A1B7AD2B6086FB7FD7D8394C6E7220F32EA4"
    )
    assert len(DATA["positive_cases"]) == 20
    assert len(DATA["negative_cases"]) == 18
    assert [case["id"] for case in DATA["invariants"]] == [f"I{i:02}" for i in range(1, 19)]
    # The approved artifact is not rewritten. Owner/EOR I11 supersession is
    # exercised by exact US and SI parent oracles in test_stainless_native_units.
    assert DATA["invariants"][10]["id"] == "I11"
    assert "Display-unit changes" in DATA["invariants"][10]["text"]


@pytest.mark.parametrize(
    ("case_id", "role"),
    [
        ("N02_PRIMARY_MEMBER_SS316_REQUEST", "PRIMARY_MEMBER"),
        ("N03_FASTENER_BODY_AUTHORITY_SUBSTITUTION", "FASTENER_OR_HARDWARE"),
        ("N04_FOUNDATION_BODY_AUTHORITY_SUBSTITUTION", "FOUNDATION"),
    ],
)
def test_controlled_public_ss_role_denial_keeps_native_error_and_specific_code(
    case_id: str, role: str
) -> None:
    payload = envelope("beam-concrete-paired-angle")
    current = http("POST", "/api/v1/connector-materials/plan", payload).json()["result"]
    component = next(c for c in current["canonical_components"] if c["role"] == role)
    payload["assignments"] = [{"component_id": component["physical_id"], "material": SS}]
    response = http("POST", "/api/v1/connector-materials/plan", payload)
    expected = next(c["expected_status"] for c in DATA["negative_cases"] if c["id"] == case_id)
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": expected,
        "message": f"ROLE_SUBSTITUTION_FORBIDDEN:{role}",
    }
    # Explicit FRP denial is not a CME-3 delta.
    payload["assignments"][0]["material"] = {"family": "FRP"}
    historical = http("POST", "/api/v1/connector-materials/plan", payload)
    assert historical.status_code == 422
    assert historical.json()["detail"] == {
        "code": "CONNECTOR_MATERIAL_PLAN_INVALID",
        "message": f"ROLE_SUBSTITUTION_FORBIDDEN:{role}",
    }


def test_unrecognized_native_error_is_not_reclassified_as_an_approved_role_status() -> None:
    error = ValueError("Unknown physical component: forged")
    assert public_role_denial(error) is error
    payload = envelope("clip-angle")
    payload["assignments"] = [{"component_id": "forged", "material": SS}]
    response = http("POST", "/api/v1/connector-materials/plan", payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CONNECTOR_MATERIAL_PLAN_INVALID"
