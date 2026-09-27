"""Reader-facing labels and indexes over an unchanged native calculation record."""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from frp_master_connection.reporting.units import DisplayUnits, display_quantity

_KNOWN = {
    "FIRST_ROW_SIMPLIFIED": "First-row net tension",
    "FIRST_ROW": "First-row net tension",
    "INTERROW_ASCE_EQ_8_12": "Inter-row shear-out",
    "INTERROW": "Inter-row shear-out",
    "PIN_BEARING": "Pin bearing",
    "BOLT_SHEAR": "Bolt shear",
    "BOLT_TENSION": "Bolt tension",
    "WIDE_FLANGE_I": "Wide-flange I section",
    "WEB_POS_FACE": "Positive web face",
    "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR": "Externally designed blind embedded anchor",
    "QUALIFIED_ASCE_PRESCRIPTIVE": "ASCE-prescriptive method qualified",
    "ASCE_PRESCRIBED": "ASCE-prescriptive method qualified",
    "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY": "Rational elastic bolt-group eccentricity method",
    "SOURCE_DATA_PENDING": "Source data pending",
    "ENGINEERING_REVIEW_REQUIRED": "Engineering review required",
    "NOT_EVALUATED": "Not evaluated",
    "NOT_APPLICABLE": "Not applicable",
    "CALCULATED": "Calculated",
    "PASS": "PASS",
    "FAIL": "FAIL",
    "SOURCE_REQUIRED": "Source evidence required",
    "SECTION_2_3_2_QUALIFICATION_REQUIRED": "Section 2.3.2 qualification required",
}
_META = {
    "schema_version",
    "contract_version",
    "orchestration_contract_version",
    "request_id",
    "calculation_id",
    "fingerprint",
}


def humanize(value: object) -> str:
    """Use controlled enum translations, otherwise retain a readable exact ID."""

    word = str(value)
    if word in _KNOWN:
        return _KNOWN[word]
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", word):
        return word.replace("_", " ").capitalize()
    return word.replace("_", " ")


def short_number(value: object, *, ratio: bool = False) -> str:
    """Shorten display only; preserve a threshold's exact comparison side."""

    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    if not number.is_finite():
        return str(value)
    digits = 9 if ratio and abs(number - 1) < Decimal("0.001") else 6
    shown = f"{number:.{digits}g}"
    if "e" not in shown.lower() and "." in shown:
        shown = shown.rstrip("0").rstrip(".")
    if ratio and number != 1 and shown == "1":
        shown = format(number.normalize(), "f")
    if ratio:
        side = "exceeds 1.0" if number > 1 else "equals 1.0" if number == 1 else "below 1.0"
        return f"{shown} ({side})"
    return shown


def readable_value(value: object, system: DisplayUnits = "INHERIT") -> str:
    """Render a scalar, quantity, or vector without Python object syntax."""

    if value is None or value == "":
        return "Not supplied"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        if "value" in value and "unit" in value:
            rendered = display_quantity(value, system)
            match = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*(.*)", rendered)
            return f"{short_number(match[1])} {match[2]}" if match else rendered
        if set(value).issubset({"x", "y", "z", "h", "v", "n", "l", "s", "u", "p", "q"}):
            return "; ".join(
                f"{key.upper()} = {readable_value(value[key], system)}"
                for key in ("h", "v", "l", "s", "n", "x", "y", "z", "u", "p", "q")
                if key in value
            )
        return "; ".join(
            f"{humanize(key)}: {readable_value(item, system)}" for key, item in value.items()
        )
    if isinstance(value, list):
        return (
            ", ".join(readable_value(item, system) for item in value) if value else "None recorded"
        )
    if isinstance(value, int | float | Decimal):
        return short_number(value)
    word = str(value)
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", word):
        return short_number(word)
    return humanize(word)


def _group(path: tuple[str, ...]) -> str:
    name = " ".join(path).lower()
    if any(key in name for key in ("force", "moment", "reaction", "action", "load", "wrench")):
        return "Loads and moments"
    if any(key in name for key in ("material", "property", "strength", "modulus")):
        return "Materials"
    if any(
        key in name
        for key in ("environment", "temperature", "humidity", "time effect", "condition")
    ):
        return "Environment and conditions"
    if any(key in name for key in ("bolt", "hole", "fastener", "washer", "nut", "hardware")):
        return "Bolt, hole and hardware"
    if any(
        key in name for key in ("pitch", "gauge", "row", "pattern", "edge distance", "end distance")
    ):
        return "Bolt pattern"
    if any(key in name for key in ("wall", "concrete", "foundation", "support", "anchor")):
        return "Support and external handoff"
    if any(key in name for key in ("connector", "angle", "plate", "tee", "clip")):
        return "Connector"
    if any(key in name for key in ("beam", "member", "profile", "channel", "stringer")):
        return "Connected member"
    return "Connection configuration"


def grouped_inputs(
    request: dict[str, Any], system: DisplayUnits
) -> dict[str, list[tuple[str, str]]]:
    """List every submitted engineering scalar by a human label and group."""

    grouped: dict[str, list[tuple[str, str]]] = OrderedDict()

    def visit(value: object, path: tuple[str, ...]) -> None:
        if isinstance(value, dict) and not ("value" in value and "unit" in value):
            for key, item in value.items():
                if key not in _META and not key.endswith("_fingerprint"):
                    visit(item, (*path, key))
            return
        if isinstance(value, list):
            for index, item in enumerate(value, start=1):
                visit(item, (*path, str(index)))
            return
        suffix = path[-3:]
        if suffix == ("beam_profile", "dimensions", "flange_thickness"):
            label = "Beam flange thickness"
        elif path[-2:] == ("common_beam_layout", "gauge"):
            label = "Bolt gauge"
        else:
            label = " / ".join(humanize(piece) for piece in suffix)
        grouped.setdefault(_group(path), []).append((label, readable_value(value, system)))

    visit(request, ())
    return grouped


@dataclass(frozen=True, slots=True)
class CheckView:
    identity: str
    name: str
    component: str
    location: str
    demand: object
    resistance: object
    utilization: Decimal | None
    outcome: str
    availability: str
    qualification: str
    reason: str
    required: bool


def collect_checks(result: dict[str, Any]) -> list[CheckView]:
    """Index each physical native check once, never changing its disposition."""

    checks: OrderedDict[str, CheckView] = OrderedDict()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            plan = value.get("plan")
            plan = plan if isinstance(plan, dict) else {}
            identity = value.get("result_id") or value.get("check_id") or plan.get("check_id")
            if isinstance(identity, str) and ("availability" in value or "utilization" in value):
                raw_ratio = value.get("utilization")
                try:
                    ratio = Decimal(str(raw_ratio)) if raw_ratio is not None else None
                except InvalidOperation:
                    ratio = None
                method = (
                    value.get("limit_state")
                    or value.get("equation_method")
                    or plan.get("limit_state")
                    or identity.split(":")[0]
                )
                component = (
                    value.get("component_id")
                    or value.get("layer_id")
                    or plan.get("component_id")
                    or plan.get("layer_id")
                )
                location = (
                    value.get("bolt_id")
                    or value.get("row_id")
                    or value.get("bolt_line_id")
                    or value.get("path_id")
                    or plan.get("bolt_id")
                )
                if location is None and identity.rsplit(":", 1)[-1].startswith(("B_", "ROW_")):
                    location = identity.rsplit(":", 1)[-1]
                reason = (
                    value.get("reason")
                    or value.get("reason_codes")
                    or plan.get("applicability_reason_codes")
                    or value.get("warnings")
                )
                availability = str(value.get("availability") or "NOT_EVALUATED")
                if reason:
                    reader_reason = readable_value(reason)
                elif availability == "SOURCE_DATA_PENDING":
                    reader_reason = "Required resistance source data pending"
                elif availability == "ENGINEERING_REVIEW_REQUIRED":
                    reader_reason = "Native engineering review required"
                else:
                    reader_reason = "No native reason stated"
                qualification = value.get("qualification") or plan.get("readiness_status")
                if qualification is None and availability in {
                    "SOURCE_DATA_PENDING",
                    "ENGINEERING_REVIEW_REQUIRED",
                }:
                    qualification = availability
                candidate = CheckView(
                    identity,
                    humanize(method),
                    humanize(component) if component else "Connection",
                    humanize(location) if location else "—",
                    value.get("demand"),
                    value.get("design_resistance") or value.get("resistance"),
                    ratio,
                    str(
                        value.get("numerical_comparison") or value.get("status") or "NOT_EVALUATED"
                    ),
                    availability,
                    str(qualification or "Not stated"),
                    reader_reason,
                    bool(plan.get("required", value.get("required", True))),
                )
                previous = checks.get(identity)
                if previous is None or (previous.utilization is None and ratio is not None):
                    checks[identity] = candidate
            for key, item in value.items():
                if key not in {"visualization", "geometry", "request"}:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(result)
    return list(checks.values())


def governing(checks: list[CheckView]) -> CheckView | None:
    selected: CheckView | None = None
    maximum: Decimal | None = None
    for check in checks:
        if check.utilization is not None and (maximum is None or check.utilization > maximum):
            selected, maximum = check, check.utilization
    return selected


def load_inputs(request: dict[str, Any], system: DisplayUnits) -> list[tuple[str, str]]:
    return grouped_inputs(request, system).get("Loads and moments", [])


def load_vectors(request: dict[str, Any], system: DisplayUnits) -> list[tuple[str, str, str, str]]:
    """Extract submitted three-axis forces, moments and reference points."""

    rows: list[tuple[str, str, str, str]] = []

    def visit(value: object, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            axes = ("h", "v", "n") if {"h", "v"}.issubset(value) else ("x", "y", "z")
            native_quantities = all(
                axis in value and isinstance(value[axis], dict) and "value" in value[axis]
                for axis in axes
            )
            scalar_components = all(axis in value for axis in axes) and isinstance(
                value.get("unit"), str
            )
            if native_quantities or scalar_components:
                name = " / ".join(humanize(part) for part in path[-2:])
                first, second, third = (
                    readable_value(
                        value[axis]
                        if native_quantities
                        else {"value": value[axis], "unit": value["unit"]},
                        system,
                    )
                    for axis in axes
                )
                rows.append((name, first, second, third))
                return
            for key, item in value.items():
                visit(item, (*path, key))
        elif isinstance(value, list):
            for index, item in enumerate(value, start=1):
                visit(item, (*path, str(index)))

    visit(request, ())
    return rows
