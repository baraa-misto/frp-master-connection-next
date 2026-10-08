"""Fail-closed exact scope and bounded proportional-ray comparison for Direct."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from frp_master_connection.application.direct_qualification_records import canonical_json
from frp_master_connection.calculation.quantities import decimal_value

SCOPE_SECTIONS = (
    "connection_scope",
    "material_identity",
    "fastener_identity",
    "geometry_scope",
    "action_scope",
    "environmental_scope",
    "support_scope",
)
COVERED_RESPONSES = (
    "FIRST_ROW:layer-A",
    "FIRST_ROW:layer-B",
    "INTERROW:layer-B:BOLT_LINE_1",
    "BLOCK_SHEAR:layer-B:BLOCK_L_LEFT_ROW_1_BOLT_LINE_1",
    "BLOCK_SHEAR:layer-B:BLOCK_L_RIGHT_ROW_1_BOLT_LINE_1",
)
REQUIRED_MODES = (
    "ANGLE_HEEL_LEG2_JUNCTION",
    "DELAMINATION",
    "LOCAL_BENDING",
    "THROUGH_THICKNESS",
    "PRYING_AND_AXIS_TENSION",
    "THREE_DIMENSIONAL_ECCENTRICITY",
    "ANGLE_FREE_SIDE_BLOCK",
    "SERVICEABILITY_AND_DAMAGE",
)
ACTION_FIELDS = tuple(
    "action_scope." + component for component in ("Fx", "Fy", "Fz", "Mx", "My", "Mz")
)
_CATEGORIES = {
    "connection_scope": "GEOMETRY MISMATCH",
    "geometry_scope": "GEOMETRY MISMATCH",
    "material_identity": "PRODUCT MISMATCH",
    "fastener_identity": "HARDWARE MISMATCH",
    "action_scope": "ACTION / ECCENTRICITY MISMATCH",
    "support_scope": "SUPPORT / FIXTURE MISMATCH",
    "environmental_scope": "ENVIRONMENT MISMATCH",
}


def scope_fields(scope: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def visit(prefix: str, value: object) -> None:
        if isinstance(value, dict) and value:
            for key, child in sorted(value.items()):
                visit(prefix + "." + key, child)
        elif isinstance(value, list) and value:
            for i, child in enumerate(value):
                visit(prefix + "." + str(i), child)
        else:
            result[prefix] = value

    for section in SCOPE_SECTIONS:
        visit(section, scope[section])
    return result


def _rule_matches(rule: dict[str, Any], actual: tuple[Any, ...]) -> bool:
    kind = rule["kind"]
    if kind == "EXACT":
        return actual == tuple(rule["tested_values"])
    if kind in {"ENUM_SET", "APPROVED_PRODUCT_EQUIVALENCE"}:
        if kind == "APPROVED_PRODUCT_EQUIVALENCE" and any(
            not field.startswith("material_identity.") for field in rule["fields"]
        ):
            return False
        if len(actual) == 1:
            return actual[0] in rule["approved_values"]
        return list(actual) in rule["approved_values"]
    if kind == "INCLUSIVE_RANGE":
        if (
            len(actual) != 1
            or not rule["fields"][0].startswith("geometry_scope.")
            or not rule["fields"][0].endswith(".value")
            or rule["unit_or_frame"] != "mm"
            or rule["lower"] is None
            or rule["upper"] is None
            or not rule["inclusive"]
        ):
            return False
        low, high = decimal_value(rule["lower"]), decimal_value(rule["upper"])
        return low <= decimal_value(actual[0]) <= high
    if kind == "PROPORTIONAL_ACTION_RAY":
        if (
            tuple(rule["fields"]) != ACTION_FIELDS
            or rule["unit_or_frame"] != "N,N-mm; same authenticated frame/reference"
            or rule["lower"] is None
            or rule["upper"] is None
        ):
            return False
        tested = tuple(Fraction(decimal_value(value)) for value in rule["tested_values"])
        current = tuple(Fraction(decimal_value(value)) for value in actual)
        pivot = next((i for i, value in enumerate(tested) if value != 0), None)
        if pivot is None:
            return False
        # Exact rational cross-products and bounds cannot round away a real action.
        # No projection, force/moment tolerance or near-zero normalization occurs.
        if any(current[i] * tested[pivot] != tested[i] * current[pivot] for i in range(6)):
            return False
        scale = current[pivot] / tested[pivot]
        return (
            0
            <= Fraction(decimal_value(rule["lower"]))
            <= scale
            <= Fraction(decimal_value(rule["upper"]))
            <= 1
        )
    return False


def match_scope(
    record: dict[str, Any], current: dict[str, Any]
) -> tuple[tuple[str, ...], list[dict[str, Any]]]:
    tested = scope_fields(record)
    actual = scope_fields(current)
    blockers: list[str] = []
    trace: list[dict[str, Any]] = []
    rules: dict[str, dict[str, Any]] = {}
    range_rules = [r for r in record["scope_rules"] if r["kind"] == "INCLUSIVE_RANGE"]
    if len(range_rules) > 1:
        blockers.append("CORRELATED_MULTIDIMENSIONAL_RANGE_AUTHORITY_REQUIRED")
    for rule in record["scope_rules"]:
        fields = rule["fields"]
        if (
            not fields
            or len(set(fields)) != len(fields)
            or len(rule["tested_values"]) != len(fields)
        ):
            blockers.append("SCOPE_RULE_FIELD_CONTRACT_INVALID")
            continue
        if any(
            field not in tested
            or field not in actual
            or tested[field] != rule["tested_values"][i]
            or field in rules
            for i, field in enumerate(fields)
        ):
            blockers.append("SCOPE_RULE_TESTED_IDENTITY_OR_OVERLAP_INVALID")
            continue
        try:
            matched = _rule_matches(rule, tuple(actual[field] for field in fields))
        except ArithmeticError, ValueError, TypeError:
            matched = False
        if rule["correlation_constraints"] and tuple(
            actual[field] for field in fields
        ) not in tuple(tuple(row) for row in rule["correlation_constraints"]):
            matched = False
        for field in fields:
            rules[field] = {"rule_id": rule["rule_id"], "matched": matched, "kind": rule["kind"]}
    for field in sorted(set(tested) | set(actual)):
        expected, observed = tested.get(field), actual.get(field)
        unknown = observed is None or observed in ("UNKNOWN", "UNSPECIFIED", "", {}, [])
        matched = (
            not unknown
            and field in tested
            and field in actual
            and (
                rules[field]["matched"]
                if field in rules
                else canonical_json(expected) == canonical_json(observed)
            )
        )
        trace.append(
            {
                "field": field,
                "tested": expected,
                "current": observed,
                "matched": matched,
                "rule": rules.get(field, {"kind": "EXACT_DEFAULT"}),
            }
        )
        if not matched:
            blockers.append(_CATEGORIES[field.split(".", 1)[0]])
    return tuple(dict.fromkeys(blockers)), trace


def response_coverage(record: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    covered = tuple(
        identifier for identifier in COVERED_RESPONSES if identifier in record["coverage_ids"]
    )
    blockers = []
    if len(covered) != len(COVERED_RESPONSES):
        blockers.append("RESPONSE COVERAGE INCOMPLETE")
    if any(
        mode not in record["failure_modes"]
        or mode not in record["engineer_approval"]["approved_failure_mode_dispositions"]
        for mode in REQUIRED_MODES
    ):
        blockers.append("WHOLE_CONNECTION_COMPETING_MODE_DISPOSITION_REQUIRED")
    return covered, tuple(blockers)


__all__ = (
    "ACTION_FIELDS",
    "COVERED_RESPONSES",
    "REQUIRED_MODES",
    "SCOPE_SECTIONS",
    "match_scope",
    "response_coverage",
    "scope_fields",
)
