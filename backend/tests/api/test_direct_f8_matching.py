"""Exact scopes, approved bounds, six-action rays and one qualified capacity."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from tests.direct_f8_fixtures import qa_design, synthetic_record

from frp_master_connection.api.direct_qualification import evaluate_record, qualification_capacity
from frp_master_connection.application.direct_qualification_matching import (
    ACTION_FIELDS,
    COVERED_RESPONSES,
    match_scope,
    response_coverage,
    scope_fields,
)
from frp_master_connection.infrastructure.direct_qualification_records import canonical_record


@pytest.fixture(scope="module")
def qa() -> tuple[Any, ...]:
    return qa_design()


def rule(
    record: dict[str, Any], fields: list[str], kind: str = "EXACT", **kwargs: object
) -> dict[str, Any]:
    tested = scope_fields(record)
    return {
        "rule_id": "SYNTHETIC_QA_RULE",
        "kind": kind,
        "fields": fields,
        "tested_values": [tested[field] for field in fields],
        "approved_values": [],
        "lower": None,
        "upper": None,
        "inclusive": True,
        "unit_or_frame": "mm",
        "evidence_document_id": "LAB",
        "rdp_approval_document_id": "RDP",
        "correlation_constraints": [],
        **kwargs,
    }


def test_exact_synthetic_evaluation_never_activates(tmp_path: Path, qa: tuple[Any, ...]) -> None:
    _, native, scope, required, ledgers, context = qa
    record = canonical_record(synthetic_record(scope, tmp_path))
    before = deepcopy(native)
    evaluation, audit = evaluate_record(record, scope, required, ledgers, context, qa_preview=True)
    assert evaluation["scope_match_state"] == "MATCHED"
    assert evaluation["capacity_state"] == "CAPACITY_PASS"
    assert evaluation["coverage_state"] == "COVERED_BY_QUALIFICATION"
    assert evaluation["covered_response_ids"] == list(COVERED_RESPONSES)
    assert evaluation["activation_permitted"] is False
    assert evaluation["ordinary_pass_allowed"] is False
    assert len([entry for entry in audit["factor_trace"] if entry["factor"] == "Rn"]) == 1
    assert native == before
    rejected, _ = evaluate_record(record, scope, required, ledgers, context)
    assert rejected["capacity_state"] == "UNEVALUATED"
    assert "APPROVED_AVAILABLE_RECORD_REQUIRED" in rejected["mismatch_reasons"]


@pytest.mark.parametrize(
    ("section", "field", "value", "category"),
    [
        ("geometry_scope", "row_count", 3, "GEOMETRY MISMATCH"),
        ("geometry_scope", "pitch", {"value": "80", "unit": "mm"}, "GEOMETRY MISMATCH"),
        ("connection_scope", "lap", "DOUBLE_LAP", "GEOMETRY MISMATCH"),
        ("material_identity", "member-a", {"manufacturer": "different"}, "PRODUCT MISMATCH"),
        ("fastener_identity", "installation", "PRETENSIONED", "HARDWARE MISMATCH"),
        ("action_scope", "Mx", "100", "ACTION / ECCENTRICITY MISMATCH"),
        ("action_scope", "loading_history", "CYCLIC", "ACTION / ECCENTRICITY MISMATCH"),
        ("action_scope", "loading_type", "SEISMIC", "ACTION / ECCENTRICITY MISMATCH"),
        (
            "action_scope",
            "reference_point",
            {"kind": "BOLT_GROUP_ORIGIN"},
            "ACTION / ECCENTRICITY MISMATCH",
        ),
        ("support_scope", "fixture_stiffness", "UNKNOWN", "SUPPORT / FIXTURE MISMATCH"),
        (
            "support_scope",
            "longitudinal_ends",
            {"condition": "FINITE_BOTH_ENDS"},
            "SUPPORT / FIXTURE MISMATCH",
        ),
        (
            "environmental_scope",
            "conditions",
            {"moisture": "SUSTAINED_MOISTURE"},
            "ENVIRONMENT MISMATCH",
        ),
    ],
)
def test_scope_categories_fail_closed(
    tmp_path: Path, qa: tuple[Any, ...], section: str, field: str, value: object, category: str
) -> None:
    scope = qa[2]
    record = synthetic_record(scope, tmp_path)
    current = deepcopy(scope)
    current[section][field] = value
    reasons, comparison = match_scope(record, current)
    assert category in reasons
    assert any(not row["matched"] for row in comparison)


@pytest.mark.parametrize("unknown", [None, "UNKNOWN", "UNSPECIFIED", "", {}, []])
def test_unknown_is_never_an_exact_wildcard(
    tmp_path: Path, qa: tuple[Any, ...], unknown: object
) -> None:
    scope = deepcopy(qa[2])
    scope["support_scope"]["fixture_id"] = unknown
    assert "SUPPORT / FIXTURE MISMATCH" in match_scope(synthetic_record(scope, tmp_path), scope)[0]


@pytest.mark.parametrize("kind", ["EXACT", "ENUM_SET", "APPROVED_PRODUCT_EQUIVALENCE"])
def test_approved_exact_and_enumerated_product_rules(
    tmp_path: Path, qa: tuple[Any, ...], kind: str
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    field = "material_identity.member-a.actual_product.product"
    item = rule(record, [field], kind)
    item["approved_values"] = [scope_fields(record)[field], "SYNTHETIC QA equivalent"]
    record["scope_rules"] = [item]
    current = deepcopy(qa[2])
    if kind != "EXACT":
        current["material_identity"]["member-a"]["actual_product"]["product"] = (
            "SYNTHETIC QA equivalent"
        )
    assert not match_scope(record, current)[0]


@pytest.mark.parametrize(
    ("value", "matched"),
    [("50.799999", False), ("50.8", True), ("60", True), ("70", True), ("70.000001", False)],
)
def test_approved_inclusive_range_boundaries(
    tmp_path: Path, qa: tuple[Any, ...], value: str, matched: bool
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    record["scope_rules"] = [
        rule(record, ["geometry_scope.pitch.value"], "INCLUSIVE_RANGE", lower="50.8", upper="70")
    ]
    current = deepcopy(qa[2])
    current["geometry_scope"]["pitch"]["value"] = value
    assert (not match_scope(record, current)[0]) is matched


@pytest.mark.parametrize(
    ("scale", "matched"),
    [("-.1", False), ("0", True), (".1", True), (".5", True), ("1", True), ("1.0000001", False)],
)
def test_full_action_ray_with_same_reference(
    tmp_path: Path, qa: tuple[Any, ...], scale: str, matched: bool
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    record["scope_rules"] = [
        rule(
            record,
            list(ACTION_FIELDS),
            "PROPORTIONAL_ACTION_RAY",
            lower="0",
            upper="1",
            unit_or_frame="N,N-mm; same authenticated frame/reference",
        )
    ]
    current = deepcopy(qa[2])
    for field in ACTION_FIELDS:
        key = field.split(".")[1]
        current["action_scope"][key] = str(Decimal(current["action_scope"][key]) * Decimal(scale))
    assert (not match_scope(record, current)[0]) is matched
    current["action_scope"]["Mz"] = "0.000001"
    assert "ACTION / ECCENTRICITY MISMATCH" in match_scope(record, current)[0]


def test_action_ray_cannot_change_reference_or_discard_moment(
    tmp_path: Path, qa: tuple[Any, ...]
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    record["scope_rules"] = [
        rule(
            record,
            list(ACTION_FIELDS),
            "PROPORTIONAL_ACTION_RAY",
            lower="0",
            upper="1",
            unit_or_frame="N,N-mm; same authenticated frame/reference",
        )
    ]
    current = deepcopy(qa[2])
    current["action_scope"]["reference_point"]["owner_id"] = "another-reference"
    assert match_scope(record, current)[0]
    current = deepcopy(qa[2])
    current["action_scope"]["Mx"] = "1"
    assert match_scope(record, current)[0]
    # The exact cross-products differ by one despite their 158-digit scale.
    # Fixed Decimal precision must not erase a genuinely nonproportional action.
    magnitude = 10**79
    record["action_scope"].update(Fx=str(magnitude - 1), Fy=str(magnitude - 2))
    record["scope_rules"][0]["tested_values"] = [
        record["action_scope"][field.split(".")[1]] for field in ACTION_FIELDS
    ]
    current = deepcopy(qa[2])
    current["action_scope"].update(Fx=str(magnitude - 2), Fy=str(magnitude - 3))
    assert "ACTION / ECCENTRICITY MISMATCH" in match_scope(record, current)[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown-rule",
        "overlap",
        "empty",
        "wrong-field",
        "wrong-tested",
        "wrong-size",
        "invalid-bound",
        "noninclusive",
        "wrong-ray-fields",
        "wrong-ray-frame",
        "zero-ray",
        "independent-ranges",
        "correlation",
        "product-rule-on-geometry",
    ],
)
def test_malformed_or_unapproved_scope_rules_fail_closed(
    tmp_path: Path, qa: tuple[Any, ...], mutation: str
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    item = rule(record, ["geometry_scope.row_count"])
    record["scope_rules"] = [item]
    if mutation == "unknown-rule":
        item["kind"] = "INTERPOLATE_ANYTHING"
    elif mutation == "overlap":
        record["scope_rules"].append(deepcopy(item))
    elif mutation == "empty":
        item["fields"] = []
    elif mutation == "wrong-field":
        item["fields"] = ["geometry_scope.nonexistent"]
    elif mutation == "wrong-tested":
        item["tested_values"] = [100]
    elif mutation == "wrong-size":
        item["tested_values"] = []
    elif mutation == "invalid-bound":
        item.update(kind="INCLUSIVE_RANGE", lower="NaN", upper="3")
    elif mutation == "noninclusive":
        item.update(kind="INCLUSIVE_RANGE", lower="1", upper="3", inclusive=False)
    elif mutation == "wrong-ray-fields":
        item.update(kind="PROPORTIONAL_ACTION_RAY", lower="0", upper="1")
    elif mutation in {"wrong-ray-frame", "zero-ray"}:
        item = rule(
            record,
            list(ACTION_FIELDS),
            "PROPORTIONAL_ACTION_RAY",
            lower="0",
            upper="1",
            unit_or_frame="wrong"
            if mutation == "wrong-ray-frame"
            else "N,N-mm; same authenticated frame/reference",
        )
        if mutation == "zero-ray":
            for field in ACTION_FIELDS:
                record["action_scope"][field.split(".")[1]] = "0"
            item["tested_values"] = ["0"] * 6
        record["scope_rules"] = [item]
    elif mutation == "independent-ranges":
        item.update(kind="INCLUSIVE_RANGE", lower="1", upper="3")
        record["scope_rules"].append(
            rule(record, ["geometry_scope.bolts_per_row"], "INCLUSIVE_RANGE", lower="1", upper="2")
        )
    elif mutation == "correlation":
        item["correlation_constraints"] = [[100]]
    else:
        item.update(kind="APPROVED_PRODUCT_EQUIVALENCE", approved_values=[2])
    assert match_scope(record, {section: record[section] for section in qa[2]})[0]


@pytest.mark.parametrize(
    "removed", [*COVERED_RESPONSES, "ANGLE_HEEL_LEG2_JUNCTION", "SERVICEABILITY_AND_DAMAGE"]
)
def test_complete_response_and_competing_mode_coverage(
    tmp_path: Path, qa: tuple[Any, ...], removed: str
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    if removed in COVERED_RESPONSES:
        record["coverage_ids"].remove(removed)
    else:
        record["failure_modes"].pop(removed)
    assert response_coverage(record)[1]


@pytest.mark.parametrize("factor", ["CM", "CT", "CCH"])
@pytest.mark.parametrize("conditioned", [False, True])
def test_existing_mat1_factors_once(
    tmp_path: Path, qa: tuple[Any, ...], factor: str, conditioned: bool
) -> None:
    record = synthetic_record(qa[2], tmp_path)
    ledger = replace(qa[4][0], **{factor.lower(): Decimal(".8"), "lambda_factor": Decimal(".4")})
    if conditioned:
        record["statistical_protocol"].update(
            baseline="ALREADY_CONDITIONED_STRENGTH", conditioned_factor_ids=[factor]
        )
    design, trace, blockers = qualification_capacity(
        record, qa[2], [ledger], Decimal(10000), Decimal(".5")
    )
    assert not blockers
    assert design == (Decimal(2000) if conditioned else Decimal(1600))
    assert not any(item["factor"] in {"C_lap", "C_delta", "block_phi", "pin_phi"} for item in trace)


@pytest.mark.parametrize(
    "case",
    [
        "no-ledger",
        "no-lambda",
        "unknown-baseline",
        "contradictory-baseline",
        "conditioned-mismatch",
        "chemical-source",
    ],
)
def test_factor_authority_failures(tmp_path: Path, qa: tuple[Any, ...], case: str) -> None:
    record = synthetic_record(qa[2], tmp_path)
    scope = deepcopy(qa[2])
    ledgers = [qa[4][0]]
    if case == "no-ledger":
        ledgers = []
    elif case == "no-lambda":
        ledgers = [replace(ledgers[0], lambda_factor=None)]
    elif case == "unknown-baseline":
        record["statistical_protocol"]["baseline"] = "UNKNOWN"
    elif case == "contradictory-baseline":
        record["statistical_protocol"]["conditioned_factor_ids"] = ["CM"]
    elif case == "chemical-source":
        ledgers = [replace(ledgers[0], cch=None)]
    else:
        record["statistical_protocol"].update(
            baseline="ALREADY_CONDITIONED_STRENGTH", conditioned_factor_ids=["CM"]
        )
        scope["environmental_scope"]["conditions"]["moisture"] = "SUSTAINED_MOISTURE"
    design, _, blockers = qualification_capacity(
        record, scope, ledgers, Decimal(10000), Decimal(".5")
    )
    assert design is None
    assert blockers


def test_capacity_failure_and_invalid_statistics_remain_nonactivating(
    tmp_path: Path, qa: tuple[Any, ...]
) -> None:
    for n, expected in ((10, "CAPACITY_FAIL"), (9, "UNEVALUATED")):
        record = canonical_record(synthetic_record(qa[2], tmp_path, n=n, strength="100"))
        public, _ = evaluate_record(record, qa[2], qa[3], qa[4], qa[5], qa_preview=True)
        assert public["capacity_state"] == expected
        assert public["ordinary_pass_allowed"] is False
        if n == 9:
            assert "STATISTICS INVALID" in public["mismatch_reasons"]
