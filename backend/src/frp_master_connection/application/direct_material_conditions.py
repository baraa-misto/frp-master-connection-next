"""MC1 Direct input policy and audit metadata; no resistance equations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from frp_master_connection.application.direct_qualification_records import content_digest
from frp_master_connection.application.mat1_materials import (
    MODULUS_IDS,
    DesignConditions,
    DirectDesignConditions,
    PropertyLedger,
)

DIRECT_MATERIAL_POLICY = "SHEAR01-DIRECT-MC1"


def conditions_audit(conditions: DesignConditions) -> dict[str, Any]:
    """Preserve the exact historical environment schema for old signed requests."""
    return asdict(conditions)


def modulus_cm_ct_candidate(ledger: PropertyLedger) -> Decimal | None:
    """Independent established adjustments; no assumed chemical-modulus factor."""
    if (
        ledger.property_id in MODULUS_IDS
        and "CHEMICAL_MODULUS_APPLICABILITY_UNRESOLVED" in ledger.issues
        and ledger.cm is not None
        and ledger.ct is not None
    ):
        return ledger.original * ledger.cm * ledger.ct
    return None


def ledger_audit(ledger: PropertyLedger, conditions: DesignConditions) -> dict[str, Any]:
    """Only new MC1 evidence adds explicit factor origin and partial modulus state."""
    result = asdict(ledger)
    if isinstance(conditions, DirectDesignConditions):
        result["direct_policy"] = conditions.direct_policy
        result["chemical_factor_origin"] = (
            "ENGINEER_SPECIFIED_STRENGTH_FACTOR_NOT_CERTIFIED_TEST_DATA"
            if conditions.chemical == "SPECIFIED" and ledger.cch is not None
            else "CHEMICAL_MODULUS_APPLICABILITY_UNRESOLVED"
            if conditions.chemical == "SPECIFIED"
            else "NO_CHEMICAL_ADJUSTMENT_DECLARED"
        )
        if ledger.property_id in MODULUS_IDS and conditions.chemical == "SPECIFIED":
            result["independent_moisture_temperature_candidate"] = modulus_cm_ct_candidate(ledger)
            result["chemical_modulus_applicability"] = "UNEVALUATED"
            result["definitive_chemical_adjusted_modulus"] = None
    return result


def gate_direct_temperature_result(result: dict[str, Any]) -> dict[str, Any]:
    """New MC1 source availability projection; raw engine evidence is retained.

    The inherited engine can calculate diagnostics using an original property
    when C_T is unavailable. Those diagnostics cannot become MC1 design passes.
    This boundary adds no equation, substitute factor or qualification authority.
    """
    ledgers = result["material_ledgers"]
    source_issues = {
        issue
        for ledger in ledgers
        if ledger.get("direct_policy") == DIRECT_MATERIAL_POLICY
        for issue in ledger["issues"]
    }
    if not source_issues.intersection(
        {"TEST_BASED_TEMPERATURE_FACTOR_REQUIRED", "RESIN_TEMPERATURE_MODEL_REQUIRED"}
    ):
        return result
    source_reason = (
        "Test-based temperature factor required above 140°F."
        if "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED" in source_issues
        else "Temperature adjustment model required for the selected resin."
    )
    native = deepcopy(result["native_design"])
    blocked: set[str] = set()
    changes: list[dict[str, Any]] = []

    def project(
        value: dict[str, Any], key: str, replacement: object, path: tuple[str | int, ...]
    ) -> None:
        present = key in value
        if not present or value[key] != replacement:
            changes.append(
                {
                    "path": [*path, key],
                    "original_present": present,
                    "original_value": deepcopy(value.get(key)),
                }
            )
            value[key] = replacement

    def visit(value: object, path: tuple[str | int, ...] = ()) -> None:
        if isinstance(value, dict):
            identity = value.get("result_id", "")
            if (
                isinstance(identity, str)
                and identity.startswith(
                    ("PIN_BEARING:", "INTERROW:", "FIRST_ROW:", "BLOCK_SHEAR:", "SINGLE_ROW_")
                )
                and value.get("availability") == "CALCULATED"
            ):
                blocked.add(identity)
                project(value, "availability", "SOURCE_DATA_PENDING", path)
                project(value, "numerical_comparison", "NOT_EVALUATED", path)
                project(value, "reason", source_reason, path)
                for key in (
                    "utilization",
                    "design_resistance",
                    "resistance",
                    "equation_nominal_resistance",
                    "connection_adjusted_nominal_resistance",
                    "equation_trace",
                ):
                    if key in value:
                        project(value, key, None, path)
            for key, child in value.items():
                visit(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, index))

    visit(native)

    def summaries(value: object, path: tuple[str | int, ...] = ()) -> None:
        if isinstance(value, dict):
            for key in ("failed_check_ids", "governing_supported_check_ids"):
                if key in value:
                    project(
                        value,
                        key,
                        [identity for identity in value[key] if identity not in blocked],
                        path,
                    )
            if (
                "supported_results" in value
                or "scenario_results" in value
                or ("checks" in value and "required_check_ids" in value)
            ):
                project(
                    value,
                    "numerical_comparison",
                    "FAIL" if value.get("failed_check_ids") else "NOT_EVALUATED",
                    path,
                )
                project(
                    value,
                    "overall_disposition",
                    "FAIL" if value.get("failed_check_ids") else "INCOMPLETE_OR_UNSUPPORTED",
                    path,
                )
            for key, child in value.items():
                summaries(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                summaries(child, (*path, index))

    summaries(native)
    integration = native.get("automatic_group_mode_integration") or {}
    failed = bool(integration.get("failed_check_ids")) or bool(
        (integration.get("direct_single_row_result") or {}).get("failed_check_ids")
    )
    return {
        **result,
        "native_design": native,
        "overall_status": "FAIL" if failed else "ENGINEERING_REVIEW_REQUIRED",
        "direct_material_applicability": {
            "contract": "SHEAR01-DIRECT-MC1-TEMPERATURE-SOURCE-GATE",
            "reason": source_reason + " FRP diagnostics are not design passes.",
            "blocked_check_ids": sorted(blocked),
            "raw_engine_diagnostic_field_changes": changes,
            "raw_engine_diagnostic_native_digest": content_digest(result["native_design"]),
            "raw_engine_reconstruction": (
                "Reverse these field changes on native_design; "
                "all unchanged native evidence is retained there."
            ),
            "raw_engine_fingerprints_are_diagnostic_only": True,
        },
    }
