"""Evidence provenance, synthetic origin, lifecycle and controlled provider contracts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from tests.direct_f8_fixtures import qa_design, synthetic_record

from frp_master_connection.infrastructure.direct_qualification_records import (
    QualificationRecordProvider,
    canonical_record,
    evidence_blockers,
    production_provider,
)
from frp_master_connection.qualification_admin import validate_package


@pytest.fixture(scope="module")
def scope() -> dict[str, Any]:
    return qa_design()[2]


def install_index(directory: Path, generation: int = 1) -> None:
    files = sorted(directory.glob("*.qualification.json"))
    data = {
        "contract": "DIRECT-QUALIFICATION-INDEX-F8",
        "generation": generation,
        "entries": [
            {
                "filename": file.name,
                "file_sha256": hashlib.sha256(file.read_bytes()).hexdigest().upper(),
            }
            for file in files
        ],
    }
    (directory / "catalog.qualification-index.json").write_text(json.dumps(data), encoding="utf-8")


def test_immutable_record_and_digest_invalidate_mutation(
    tmp_path: Path, scope: dict[str, Any]
) -> None:
    record = canonical_record(synthetic_record(scope, tmp_path))
    detached = record.data
    detached["specimens"][0]["test_strength"] = "1"
    assert record.data["specimens"][0]["test_strength"] == "10000"
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        canonical_record(detached)
    revised = record.data
    revised.update(revision=2, supersedes=1, digest="")
    revised["specimens"][0].update(
        accepted_or_excluded="EXCLUDED",
        exclusion_rationale="SYNTHETIC QA exclusion",
        exclusion_approval_document_id="RDP",
    )
    assert canonical_record(revised).digest != record.digest
    assert record.data["revision"] == 1


@pytest.mark.parametrize(
    ("status", "activation"),
    [("AVAILABLE_FOR_MATCH", False), ("RDP_APPROVED", True), ("AVAILABLE_FOR_MATCH", True)],
)
@pytest.mark.parametrize("renamed", [False, True])
def test_synthetic_record_cannot_be_available_even_when_renamed(
    tmp_path: Path, scope: dict[str, Any], status: str, activation: bool, renamed: bool
) -> None:
    record = synthetic_record(scope, tmp_path)
    record.update(status=status, activation_permitted=activation, digest="")
    if renamed:
        record["qualification_record_id"] = "LOOKS_REAL"
        record["synthetic"] = False
        record["evidence_origin"] = "REAL_CONTROLLED_EVIDENCE"
    with pytest.raises(ValueError, match="SYNTHETIC"):
        canonical_record(record)


def test_synthetic_provider_empty_and_source_bytes_keep_origin(
    tmp_path: Path, scope: dict[str, Any]
) -> None:
    payload = synthetic_record(scope, tmp_path)
    record = canonical_record(payload)
    assert evidence_blockers(record, tmp_path) == (
        "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN",
        "PRODUCTION_ACTIVATION_NOT_PERMITTED",
    )
    provider = QualificationRecordProvider(tmp_path, (record,))
    records, reasons = provider.read()
    assert not records
    assert "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN" in reasons
    # Deliberate origin-spoof attempt: the original bytes still carry the marker.
    payload.update(
        synthetic=False,
        evidence_origin="REAL_CONTROLLED_EVIDENCE",
        activation_permitted=True,
        status="AVAILABLE_FOR_MATCH",
        digest="",
    )
    for document in payload["source_documents"]:
        document["origin"] = "REAL_CONTROLLED_EVIDENCE"
    spoofed = canonical_record(payload)
    assert "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN" in evidence_blockers(spoofed, tmp_path)
    assert not QualificationRecordProvider(tmp_path, (spoofed,)).read()[0]


@pytest.mark.parametrize(
    "change",
    [
        "missing-file",
        "source-bytes",
        "outside-path",
        "duplicate-document",
        "no-documents",
        "invalid-date",
        "invalid-issuer",
        "invalid-at-testing",
        "lab-standard",
        "lab-date",
        "lab-validity",
        "lab-method",
        "rdp-protocol",
        "rdp-convention",
        "rdp-missing-doc",
        "rdp-date",
        "rdp-before-tests",
        "scope-rule",
        "unknown-baseline-doc",
        "raw-source",
        "raw-protocol",
        "population-scope",
        "exclusion",
        "mode-disposition",
        "observed-mode",
        "ahj-missing",
        "ahj-wrong-role",
        "scope-empty",
    ],
)
def test_evidence_metadata_and_bytes_fail_closed(
    tmp_path: Path, scope: dict[str, Any], change: str
) -> None:
    payload = synthetic_record(scope, tmp_path)
    if change == "missing-file":
        (tmp_path / "LAB.synthetic.txt").unlink()
    elif change == "source-bytes":
        (tmp_path / "LAB.synthetic.txt").write_text("changed", encoding="utf-8")
    elif change == "outside-path":
        payload["source_documents"][0]["package_file"] = "../outside.txt"
    elif change == "duplicate-document":
        payload["source_documents"].append(deepcopy(payload["source_documents"][0]))
    elif change == "no-documents":
        payload["source_documents"] = []
    elif change == "invalid-date":
        payload["source_documents"][0]["date"] = "bad-date"
    elif change == "invalid-issuer":
        payload["source_documents"][0]["issuer"] = "another-laboratory"
    elif change == "invalid-at-testing":
        payload["source_documents"][0]["valid_at_testing"] = False
    elif change == "lab-standard":
        payload["laboratory"]["accreditation_standard"] = "UNKNOWN"
    elif change == "lab-date":
        payload["laboratory"]["valid_from"] = "not-a-date"
    elif change == "lab-validity":
        payload["laboratory"]["valid_through"] = "2025-01-01"
    elif change == "lab-method":
        payload["laboratory"]["test_method_scope"] = []
    elif change == "rdp-protocol":
        payload["engineer_approval"]["protocol_ids"] = []
    elif change == "rdp-convention":
        payload["engineer_approval"]["statistical_conventions"] = []
    elif change == "rdp-missing-doc":
        payload["engineer_approval"]["approval_document_id"] = "missing"
    elif change == "rdp-date":
        payload["engineer_approval"]["approval_date"] = "bad-date"
    elif change == "rdp-before-tests":
        payload["engineer_approval"]["approval_date"] = "2025-01-01"
    elif change == "scope-rule":
        payload["scope_rules"] = [
            {
                "rule_id": "UNAPPROVED",
                "kind": "EXACT",
                "fields": ["geometry_scope.row_count"],
                "tested_values": [2],
                "unit_or_frame": "1",
                "evidence_document_id": "missing",
                "rdp_approval_document_id": "missing",
            }
        ]
    elif change == "unknown-baseline-doc":
        payload["statistical_protocol"]["baseline_approval_document_id"] = "missing"
    elif change == "raw-source":
        payload["specimens"][0]["source_document_id"] = "missing"
    elif change == "raw-protocol":
        payload["specimens"][0]["protocol_id"] = "different"
    elif change == "population-scope":
        payload["specimens"][0]["population_scope_digest"] = "F" * 64
    elif change == "exclusion":
        payload["specimens"][0].update(
            accepted_or_excluded="EXCLUDED",
            exclusion_rationale="SYNTHETIC QA exclusion",
            exclusion_approval_document_id="missing",
        )
    elif change == "mode-disposition":
        payload["engineer_approval"]["approved_failure_mode_dispositions"] = []
    elif change == "observed-mode":
        payload["specimens"][0]["failure_mode"] = "unreviewed competing mode"
    elif change == "ahj-missing":
        payload["engineer_approval"]["project_or_ahj_acceptance_required"] = True
    elif change == "ahj-wrong-role":
        payload["engineer_approval"]["project_or_ahj_document_ids"] = ["LAB"]
    else:
        payload["geometry_scope"] = {}
    payload["digest"] = ""
    blockers = evidence_blockers(canonical_record(payload), tmp_path)
    assert set(blockers) - {
        "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN",
        "PRODUCTION_ACTIVATION_NOT_PERMITTED",
    }


@pytest.mark.parametrize(
    "status", ["DRAFT", "EVIDENCE_COMPLETE", "RDP_APPROVED", "SUPERSEDED", "WITHDRAWN", "INVALID"]
)
def test_nonavailable_lifecycle_never_matches(
    tmp_path: Path, scope: dict[str, Any], status: str
) -> None:
    payload = synthetic_record(scope, tmp_path)
    payload.update(status=status, digest="")
    assert not QualificationRecordProvider(tmp_path, (canonical_record(payload),)).read()[0]


def test_external_provider_requires_controlled_index(tmp_path: Path, scope: dict[str, Any]) -> None:
    record = canonical_record(synthetic_record(scope, tmp_path))
    filename = tmp_path / "qa.qualification.json"
    filename.write_text(record.canonical, encoding="utf-8")
    provider = QualificationRecordProvider(tmp_path)
    assert "INDEX" in provider.read()[1][0]
    install_index(tmp_path)
    assert "SYNTHETIC" in provider.read()[1][0]
    filename.write_text("changed bytes", encoding="utf-8")
    assert "INDEX" in provider.read()[1][0]
    install_index(tmp_path, 2)
    assert "SCHEMA" in provider.read()[1][0]
    filename.unlink()
    assert "INDEX" in provider.read()[1][0]
    install_index(tmp_path, 1)
    assert "INDEX" in provider.read()[1][0]


def test_provider_empty_missing_directory_and_no_directory_record(
    tmp_path: Path, scope: dict[str, Any]
) -> None:
    assert QualificationRecordProvider().read() == ((), ())
    assert QualificationRecordProvider(tmp_path).read() == ((), ())
    assert QualificationRecordProvider(tmp_path / "missing").read()[1]
    record = canonical_record(synthetic_record(scope, tmp_path))
    assert QualificationRecordProvider(records=(record,)).read()[1] == (
        "CONTROLLED_EVIDENCE_DIRECTORY_REQUIRED",
    )


def test_configured_provider_persists_and_rechecks_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("FRP_QUALIFICATION_RECORD_DIR", raising=False)
    empty = production_provider()
    assert production_provider() is empty
    monkeypatch.setenv("FRP_QUALIFICATION_RECORD_DIR", str(tmp_path))
    configured = production_provider()
    assert configured is not empty
    assert production_provider() is configured
    assert configured.read() == ((), ())


def test_admin_validator_cannot_publish_synthetic_approval(
    tmp_path: Path, scope: dict[str, Any]
) -> None:
    payload = synthetic_record(scope, tmp_path / "source")
    package = tmp_path / "source" / "evidence.json"
    package.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "out"
    assert validate_package(package, output) == 1
    receipt = json.loads(next(output.glob("*.validation-receipt.json")).read_text())
    assert receipt["statistics"]["accepted_n"] == 10
    assert receipt["configured_status"] == "RDP_APPROVED"
    assert "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN" in receipt["blockers"]
    assert not list(output.glob("*.qualification.json"))
    with pytest.raises(FileExistsError):
        validate_package(package, output)
