"""Synthetic evidence only. Never installed in a production qualification provider."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from frp_master_connection.api.direct_qualification import (
    QualificationDesignContext,
    authenticated_scope,
)
from frp_master_connection.api.mat1 import (
    MaterialAssignmentsDTO,
    MaterialConditionsDTO,
    _json_value,
    resolve_conditions,
    resolve_material,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application.direct_qualification_matching import (
    COVERED_RESPONSES,
    REQUIRED_MODES,
    SCOPE_SECTIONS,
)
from frp_master_connection.application.mat1_materials import PropertyLedger, property_ledger
from frp_master_connection.infrastructure.direct_qualification_records import (
    canonical_record,
    content_digest,
)
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design


def qa_context(material_id: str) -> QualificationDesignContext:
    products = {
        member: {
            "mat1_record_id": material_id,
            "manufacturer": "SYNTHETIC QA supplier",
            "product": "SYNTHETIC QA " + member,
            "resin": "ISOPHTHALIC_POLYESTER",
            "fiber_architecture": "SYNTHETIC QA tested continuous glass/mat",
            "profile_product_revision": "SYNTHETIC QA R1",
            "material_qualification_id": "SYNTHETIC QA Q1",
            "profile_kind": "FLAT_L" if member == "member-a" else "WIDE_FLANGE",
            "heel_radius": {"value": "0", "unit": "mm"},
        }
        for member in ("member-a", "member-b")
    }
    return QualificationDesignContext.model_validate(
        {
            "products": products,
            "bolt_length": {"value": "2", "unit": "in"},
            "grip": {"value": "1", "unit": "in"},
            "installation": "SNUG_TIGHT",
            "washer_count": "2",
            "fixture_id": "SYNTHETIC QA FIXTURE",
            "fixture_stiffness": "SYNTHETIC QA measured flexural fixture stiffness",
            "support_restraints": "SYNTHETIC QA W restraint arrangement",
            "member_load_introduction": "SYNTHETIC QA member connected end",
            "loading_type": "WIND",
            "loading_history": "MONOTONIC_STATIC",
            "loading_rate": "SYNTHETIC QA approved loading rate",
            "protocol_id": "SYNTHETIC_QA_PROTOCOL",
        }
    )


def qa_design() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    Decimal,
    list[PropertyLedger],
    QualificationDesignContext,
]:
    body = deepcopy(f6_cases()["owner-135"])
    conditions = MaterialConditionsDTO.model_validate(
        body["assignments"]["default_conditions"]
    ).model_dump(mode="json")
    body["assignments"]["default_conditions"] = conditions
    conditions["glass_transition_temperature"] = {"value": "225", "unit": "degF"}
    conditions["source_reference_condition"] = "REFERENCE"
    for key, value in list(conditions.items()):
        if value == "":
            conditions[key] = "NONE_DECLARED"
    # A live subtype is inapplicable to the current explicit WIND category.
    conditions["live_load_subtype"] = ""
    conditions["fatigue_cycles"] = ""
    result = design(body)
    assignment = MaterialAssignmentsDTO.model_validate(body["assignments"])
    record = resolve_material(assignment.default_material)
    design_conditions = resolve_conditions(assignment.default_conditions)
    context = qa_context(record.id)
    condition_snapshot = cast(dict[str, Any], _json_value(asdict(design_conditions)))
    for field in ("live_load_subtype", "fatigue_cycles"):
        condition_snapshot.pop(field)
    scope, required = authenticated_scope(
        MultiRowConnectionRequestDTO.model_validate(body["legacy_request"]).model_dump(mode="json"),
        {**result["material_sources"], "qualification_conditions": condition_snapshot},
        result["fastener_source"],
        context,
        result["native_design"]["preview"],
    )
    assert required is not None
    ledgers = [property_ledger("member-a", record, "tensile_strength_L", design_conditions)]
    return body, result, scope, required, ledgers, context


def specimen_series(n: int = 10, value: str = "10000") -> list[dict[str, Any]]:
    return [
        {
            "specimen_id": f"SYNTHETIC_QA_{i + 1}",
            "batch_or_lot": "SYNTHETIC QA LOT",
            "test_date": "2026-01-01",
            "test_strength": value,
            "unit": "N",
            "failure_mode": "SYNTHETIC QA WHOLE JOINT",
            "test_condition": "SYNTHETIC QA IDENTICAL POPULATION",
            "fixture_id": "SYNTHETIC QA FIXTURE",
            "protocol_id": "SYNTHETIC_QA_PROTOCOL",
            "accepted_or_excluded": "ACCEPTED",
            "exclusion_rationale": "",
            "exclusion_approval_document_id": "",
            "source_document_locator": "SYNTHETIC QA lab report table 1",
            "source_document_id": "LAB",
            "population_scope_digest": "0" * 64,
        }
        for i in range(n)
    ]


def statistical_protocol(mean: str = "10000", sd: str = "0", cov: str = "0") -> dict[str, Any]:
    return {
        "protocol_id": "SYNTHETIC_QA_PROTOCOL",
        "estimator_convention": "SAMPLE_SD_N_MINUS_1",
        "connection_probability": "0.999",
        "lab_reported_mean": {"value": mean, "unit": "N", "decimal_quantum": "0.000001"},
        "lab_reported_sd": {"value": sd, "unit": "N", "decimal_quantum": "0.000001"},
        "lab_reported_cov": {"value": cov, "unit": "1", "decimal_quantum": "0.000001"},
        "baseline": "REFERENCE_CONDITION_STRENGTH",
        "conditioned_factor_ids": [],
        "baseline_approval_document_id": "RDP",
        "gravity_protocol_approved": False,
    }


def synthetic_record(
    scope: dict[str, Any], directory: Path, *, n: int = 10, strength: str = "10000"
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    documents = []
    for identifier, role in (("LAB", "LABORATORY"), ("ACC", "ACCREDITATION"), ("RDP", "RDP")):
        raw = ("SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN\n" + identifier).encode()
        filename = identifier + ".synthetic.txt"
        (directory / filename).write_bytes(raw)
        import hashlib

        documents.append(
            {
                "document_id": identifier,
                "issuer": {
                    "LAB": "SYNTHETIC QA laboratory",
                    "ACC": "SYNTHETIC QA body",
                    "RDP": "SYNTHETIC QA engineer",
                }[identifier],
                "date": "2026-01-01",
                "revision": "QA1",
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
                "purpose": "SYNTHETIC QA ONLY",
                "approval_role": role,
                "valid_at_testing": True,
                "source_locator": "SYNTHETIC QA " + filename,
                "package_file": filename,
                "origin": "SYNTHETIC_QA",
            }
        )
    specimens = specimen_series(n, strength)
    for specimen in specimens:
        specimen["population_scope_digest"] = content_digest(
            {section: scope[section] for section in SCOPE_SECTIONS}
        )
    payload = {
        "contract": "DIRECT-QUALIFICATION-F8",
        "qualification_record_id": "SYNTHETIC_QA_ONLY",
        "revision": 1,
        "status": "RDP_APPROVED",
        "supersedes": None,
        "withdrawn": False,
        "synthetic": True,
        "activation_permitted": False,
        "evidence_origin": "SYNTHETIC_QA",
        "source_documents": documents,
        "laboratory": {
            "legal_identity": "SYNTHETIC QA laboratory",
            "accreditation_standard": "ISO/IEC 17025",
            "nationally_recognized_accreditation_body": "SYNTHETIC QA body",
            "accreditation_document_id": "ACC",
            "valid_from": "2025-01-01",
            "valid_through": "2027-01-01",
            "test_method_scope": ["SYNTHETIC_QA_PROTOCOL"],
            "rdp_acceptance_document_id": "RDP",
        },
        "engineer_approval": {
            "engineer_identity": "SYNTHETIC QA engineer",
            "license": "SYNTHETIC QA license",
            "jurisdiction": "SYNTHETIC QA jurisdiction",
            "approval_document_id": "RDP",
            "approval_date": "2026-01-02",
            "protocol_ids": ["SYNTHETIC_QA_PROTOCOL"],
            "statistical_conventions": ["SAMPLE_SD_N_MINUS_1"],
            "scope_rule_ids": [],
            "exclusion_document_ids": [],
            "approved_failure_mode_dispositions": [*REQUIRED_MODES, "SYNTHETIC QA WHOLE JOINT"],
            "project_or_ahj_acceptance_required": False,
            "project_or_ahj_document_ids": [],
        },
        **deepcopy(scope),
        "specimens": specimens,
        "failure_modes": dict.fromkeys(
            [*REQUIRED_MODES, "SYNTHETIC QA WHOLE JOINT"],
            "SYNTHETIC QA explicit RDP competing-mode disposition",
        ),
        "statistical_protocol": statistical_protocol(strength),
        "scope_rules": [],
        "coverage_ids": list(COVERED_RESPONSES),
        "validity_notes": "SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN",
        "digest": "",
    }
    return canonical_record(payload).data
