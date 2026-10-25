"""Controlled immutable Direct evidence; normal users have no approval/write API."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

from frp_master_connection.application.direct_qualification_records import (
    ImmutableQualificationRecord,
    canonical_json,
    content_digest,
)
from frp_master_connection.application.direct_qualification_statistics import recompute_statistics

Text = Annotated[StrictStr, Field(min_length=1)]
Sha256 = Annotated[StrictStr, Field(pattern=r"^[A-Fa-f0-9]{64}$")]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceDocument(EvidenceModel):
    document_id: Text
    issuer: Text
    date: Text
    revision: Text
    sha256: Sha256
    purpose: Text
    approval_role: Literal["LABORATORY", "ACCREDITATION", "RDP", "AHJ", "PROJECT"]
    valid_at_testing: StrictBool
    source_locator: Text
    package_file: Text
    origin: Literal["REAL_CONTROLLED_EVIDENCE", "SYNTHETIC_QA"]


class Specimen(EvidenceModel):
    specimen_id: Text
    batch_or_lot: Text
    test_date: Text
    test_strength: StrictStr
    unit: StrictStr
    failure_mode: Text
    test_condition: Text
    fixture_id: Text
    protocol_id: Text
    accepted_or_excluded: Literal["ACCEPTED", "EXCLUDED"]
    exclusion_rationale: StrictStr
    exclusion_approval_document_id: StrictStr
    source_document_locator: Text
    source_document_id: Text
    population_scope_digest: Sha256


class Laboratory(EvidenceModel):
    legal_identity: Text
    accreditation_standard: Text
    nationally_recognized_accreditation_body: Text
    accreditation_document_id: Text
    valid_from: Text
    valid_through: Text
    test_method_scope: tuple[Text, ...]
    rdp_acceptance_document_id: Text


class EngineerApproval(EvidenceModel):
    engineer_identity: Text
    license: Text
    jurisdiction: Text
    approval_document_id: Text
    approval_date: Text
    protocol_ids: tuple[Text, ...]
    statistical_conventions: tuple[Text, ...]
    scope_rule_ids: tuple[Text, ...]
    exclusion_document_ids: tuple[Text, ...]
    approved_failure_mode_dispositions: tuple[Text, ...]
    project_or_ahj_acceptance_required: StrictBool
    project_or_ahj_document_ids: tuple[Text, ...]


class ReportedStatistic(EvidenceModel):
    value: StrictStr
    unit: StrictStr = "1"
    decimal_quantum: StrictStr | None = None


class StatisticalProtocol(EvidenceModel):
    protocol_id: Text
    estimator_convention: Text
    connection_probability: StrictStr
    lab_reported_mean: ReportedStatistic | None
    lab_reported_sd: ReportedStatistic | None
    lab_reported_cov: ReportedStatistic | None
    baseline: Literal["REFERENCE_CONDITION_STRENGTH", "ALREADY_CONDITIONED_STRENGTH", "UNKNOWN"]
    conditioned_factor_ids: tuple[Literal["CM", "CT", "CCH"], ...]
    baseline_approval_document_id: Text
    gravity_protocol_approved: StrictBool


class ScopeRule(EvidenceModel):
    rule_id: Text
    kind: Text
    fields: tuple[Text, ...]
    tested_values: tuple[JsonValue, ...]
    approved_values: tuple[JsonValue, ...] = ()
    lower: StrictStr | None = None
    upper: StrictStr | None = None
    inclusive: StrictBool = True
    unit_or_frame: Text
    evidence_document_id: Text
    rdp_approval_document_id: Text
    correlation_constraints: tuple[tuple[JsonValue, ...], ...] = ()


class ProviderIndexEntry(EvidenceModel):
    filename: Text
    file_sha256: Sha256


class ProviderIndex(EvidenceModel):
    contract: Literal["DIRECT-QUALIFICATION-INDEX-F8"]
    generation: Annotated[StrictInt, Field(ge=1)]
    entries: tuple[ProviderIndexEntry, ...]


class QualificationRecordSchema(EvidenceModel):
    contract: Literal["DIRECT-QUALIFICATION-F8"]
    qualification_record_id: Annotated[Text, Field(pattern=r"^[A-Za-z0-9_.-]+$")]
    revision: Annotated[StrictInt, Field(ge=1)]
    status: Literal[
        "DRAFT",
        "EVIDENCE_COMPLETE",
        "RDP_APPROVED",
        "AVAILABLE_FOR_MATCH",
        "SUPERSEDED",
        "WITHDRAWN",
        "INVALID",
    ]
    supersedes: StrictInt | None
    withdrawn: StrictBool
    synthetic: StrictBool
    activation_permitted: StrictBool
    evidence_origin: Literal["REAL_CONTROLLED_EVIDENCE", "SYNTHETIC_QA"]
    source_documents: tuple[EvidenceDocument, ...]
    laboratory: Laboratory
    engineer_approval: EngineerApproval
    connection_scope: dict[str, JsonValue]
    material_identity: dict[str, JsonValue]
    fastener_identity: dict[str, JsonValue]
    geometry_scope: dict[str, JsonValue]
    action_scope: dict[str, JsonValue]
    environmental_scope: dict[str, JsonValue]
    support_scope: dict[str, JsonValue]
    specimens: tuple[Specimen, ...]
    failure_modes: dict[str, StrictStr]
    statistical_protocol: StatisticalProtocol
    scope_rules: tuple[ScopeRule, ...]
    coverage_ids: tuple[Text, ...]
    validity_notes: Text
    digest: StrictStr = ""

    @model_validator(mode="after")
    def synthetic_origin_cannot_activate(self) -> QualificationRecordSchema:
        synthetic = (
            self.synthetic
            or self.evidence_origin == "SYNTHETIC_QA"
            or any(document.origin == "SYNTHETIC_QA" for document in self.source_documents)
        )
        if synthetic and (self.activation_permitted or self.status == "AVAILABLE_FOR_MATCH"):
            raise ValueError("SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN")
        return self


def canonical_record(payload: dict[str, Any]) -> ImmutableQualificationRecord:
    data = QualificationRecordSchema.model_validate(payload).model_dump(mode="json")
    supplied = data.pop("digest")
    digest = content_digest(data)
    if supplied and supplied.upper() != digest:
        raise ValueError("QUALIFICATION_RECORD_DIGEST_MISMATCH")
    data["digest"] = digest
    return ImmutableQualificationRecord(canonical_json(data))


def evidence_blockers(record: ImmutableQualificationRecord, directory: Path) -> tuple[str, ...]:
    """Check controlled document bytes and declared authority, not a professional seal."""
    data = record.data
    issues: list[str] = []
    docs = {doc["document_id"]: doc for doc in data["source_documents"]}
    if len(docs) != len(data["source_documents"]) or not docs:
        issues.append("SOURCE_DOCUMENT_IDENTITIES_REQUIRED")
    for doc in docs.values():
        path = (directory / doc["package_file"]).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            issues.append("EVIDENCE_DOCUMENT_BYTES_UNAVAILABLE:" + doc["document_id"])
        else:
            source_bytes = path.read_bytes()
            if hashlib.sha256(source_bytes).hexdigest().upper() != doc["sha256"].upper():
                issues.append("SOURCE_DOCUMENT_DIGEST_MISMATCH:" + doc["document_id"])
            if b"SYNTHETIC QA" in source_bytes.upper():
                issues.append("SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN")
        if not doc["valid_at_testing"]:
            issues.append("SOURCE_DOCUMENT_NOT_VALID_AT_TESTING:" + doc["document_id"])
    lab = data["laboratory"]
    rdp = data["engineer_approval"]
    protocol = data["statistical_protocol"]
    issuers = {
        "LABORATORY": lab["legal_identity"],
        "ACCREDITATION": lab["nationally_recognized_accreditation_body"],
        "RDP": rdp["engineer_identity"],
    }
    for document in docs.values():
        if (
            document["approval_role"] in issuers
            and document["issuer"] != issuers[document["approval_role"]]
        ):
            issues.append("CONTROLLING_DOCUMENT_ISSUER_IDENTITY_MISMATCH")
        try:
            date.fromisoformat(document["date"])
        except ValueError:
            issues.append("CONTROLLING_DOCUMENT_DATE_INVALID")
    try:
        approval_date = date.fromisoformat(rdp["approval_date"])
        if any(
            date.fromisoformat(specimen["test_date"]) > approval_date
            for specimen in data["specimens"]
        ):
            issues.append("RDP_APPROVAL_PRECEDES_TEST_POPULATION")
    except ValueError:
        issues.append("RDP_APPROVAL_OR_TEST_DATE_INVALID")
    scope_sections = (
        "connection_scope",
        "material_identity",
        "fastener_identity",
        "geometry_scope",
        "action_scope",
        "environmental_scope",
        "support_scope",
    )
    population_digest = content_digest({section: data[section] for section in scope_sections})
    if any(not data[section] for section in scope_sections):
        issues.append("COMPLETE_TESTED_SCOPE_REQUIRED")
    role_references = [
        (lab["accreditation_document_id"], "ACCREDITATION"),
        (lab["rdp_acceptance_document_id"], "RDP"),
        (rdp["approval_document_id"], "RDP"),
        (protocol["baseline_approval_document_id"], "RDP"),
    ]
    for rule in data["scope_rules"]:
        role_references.extend(
            (
                (rule["evidence_document_id"], "LABORATORY"),
                (rule["rdp_approval_document_id"], "RDP"),
            )
        )
        if rule["rule_id"] not in rdp["scope_rule_ids"]:
            issues.append("SCOPE_RULE_RDP_APPROVAL_REQUIRED:" + rule["rule_id"])
    for doc_id, role in role_references:
        if doc_id not in docs or docs[doc_id]["approval_role"] != role:
            issues.append("CONTROLLED_APPROVAL_DOCUMENT_REQUIRED:" + doc_id)
    if lab["accreditation_standard"] != "ISO/IEC 17025":
        issues.append("LABORATORY_ACCREDITATION_AUTHORITY_REQUIRED")
    if (
        protocol["protocol_id"] not in lab["test_method_scope"]
        or protocol["protocol_id"] not in rdp["protocol_ids"]
    ):
        issues.append("SPECIFIC_LAB_TEST_METHOD_AND_RDP_ACCEPTANCE_REQUIRED")
    if protocol["estimator_convention"] not in rdp["statistical_conventions"]:
        issues.append("RDP_APPROVED_STATISTICAL_CONVENTION_REQUIRED")
    if rdp["project_or_ahj_acceptance_required"] and not rdp["project_or_ahj_document_ids"]:
        issues.append("PROJECT_OR_AHJ_ACCEPTANCE_EVIDENCE_REQUIRED")
    for identifier in rdp["project_or_ahj_document_ids"]:
        if identifier not in docs or docs[identifier]["approval_role"] not in {"PROJECT", "AHJ"}:
            issues.append("PROJECT_OR_AHJ_ACCEPTANCE_DOCUMENT_INVALID")
    for specimen in data["specimens"]:
        if (
            specimen["failure_mode"] not in data["failure_modes"]
            or specimen["failure_mode"] not in rdp["approved_failure_mode_dispositions"]
        ):
            issues.append("OBSERVED_FAILURE_MODE_RDP_DISPOSITION_REQUIRED")
        if specimen["population_scope_digest"].upper() != population_digest:
            issues.append("IDENTICAL_TESTED_POPULATION_SCOPE_REQUIRED")
        try:
            tested = date.fromisoformat(specimen["test_date"])
            if (
                not date.fromisoformat(lab["valid_from"])
                <= tested
                <= date.fromisoformat(lab["valid_through"])
            ):
                issues.append("ACCREDITATION_NOT_VALID_AT_TESTING")
        except ValueError:
            issues.append("EVIDENCE_TEST_OR_ACCREDITATION_DATE_INVALID")
        if (
            specimen["source_document_id"] not in docs
            or docs[specimen["source_document_id"]]["approval_role"] != "LABORATORY"
        ):
            issues.append("RAW_SPECIMEN_DOCUMENT_REQUIRED")
        if specimen["protocol_id"] != protocol["protocol_id"]:
            issues.append("IDENTICAL_APPROVED_TEST_PROTOCOL_REQUIRED")
        if specimen["accepted_or_excluded"] == "EXCLUDED":
            exclusion = specimen["exclusion_approval_document_id"]
            if (
                exclusion not in rdp["exclusion_document_ids"]
                or exclusion not in docs
                or docs[exclusion]["approval_role"] != "RDP"
            ):
                issues.append("RDP_APPROVED_EXCLUSION_EVIDENCE_REQUIRED")
    for mode, disposition in data["failure_modes"].items():
        if not disposition or mode not in rdp["approved_failure_mode_dispositions"]:
            issues.append("FAILURE_MODE_RDP_DISPOSITION_REQUIRED:" + mode)
    issues.extend(recompute_statistics(data["specimens"], protocol).blockers)
    if (
        data["synthetic"]
        or data["evidence_origin"] == "SYNTHETIC_QA"
        or any(d["origin"] == "SYNTHETIC_QA" for d in docs.values())
    ):
        issues.append("SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN")
    if not data["activation_permitted"]:
        issues.append("PRODUCTION_ACTIVATION_NOT_PERMITTED")
    return tuple(dict.fromkeys(issues))


class QualificationRecordProvider:
    """Server-only controlled static records plus a read-only administrator directory.

    Every read rechecks bytes and revisions. In-process identity pins also reject
    replacement of the contents of an existing record revision.
    """

    def __init__(
        self, directory: Path | None = None, records: tuple[ImmutableQualificationRecord, ...] = ()
    ) -> None:
        self.directory = directory
        self.records = records
        self._revision_pins: dict[tuple[str, int], str] = {}
        self._latest_revisions: dict[str, int] = {}
        self._index_generation = 0

    def read(self) -> tuple[tuple[ImmutableQualificationRecord, ...], tuple[str, ...]]:
        records = list(self.records)
        issues: list[str] = []
        if self.directory is not None:
            if not self.directory.is_dir():
                return (), ("CONTROLLED_QUALIFICATION_DIRECTORY_UNAVAILABLE",)
            paths = sorted(self.directory.glob("*.qualification.json"))
            index_path = self.directory / "catalog.qualification-index.json"
            if paths or index_path.exists():
                try:
                    index = ProviderIndex.model_validate(
                        json.loads(index_path.read_text(encoding="utf-8"))
                    )
                    if index.generation < self._index_generation:
                        raise ValueError("INDEX_GENERATION_ROLLBACK")
                    self._index_generation = index.generation
                    filenames = [entry.filename for entry in index.entries]
                    if len(set(filenames)) != len(filenames) or set(filenames) != {
                        path.name for path in paths
                    }:
                        raise ValueError("INDEX_FILE_SET_MISMATCH")
                    for entry in index.entries:
                        path = (self.directory / entry.filename).resolve()
                        if (
                            path.parent != self.directory.resolve()
                            or hashlib.sha256(path.read_bytes()).hexdigest().upper()
                            != entry.file_sha256.upper()
                        ):
                            raise ValueError("INDEX_RECORD_BYTES_MISMATCH")
                except OSError, ValueError:
                    return (), ("CONTROLLED_QUALIFICATION_INDEX_INVALID_OR_RECORD_BYTES_CHANGED",)
            for path in paths:
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict) or not payload.get("digest"):
                        raise ValueError("INSTALLED_RECORD_DIGEST_REQUIRED")
                    records.append(canonical_record(payload))
                except OSError, ValueError:
                    issues.append("QUALIFICATION_RECORD_SCHEMA_OR_DIGEST_INVALID:" + path.name)
            if issues:
                return (), tuple(issues)
        if self.directory is None and records:
            return (), ("CONTROLLED_EVIDENCE_DIRECTORY_REQUIRED",)
        grouped: dict[str, list[ImmutableQualificationRecord]] = {}
        for record in records:
            data = record.data
            if (
                data["synthetic"]
                or data["evidence_origin"] == "SYNTHETIC_QA"
                or any(
                    document["origin"] == "SYNTHETIC_QA" for document in data["source_documents"]
                )
            ):
                issues.append("SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN")
                continue
            grouped.setdefault(data["qualification_record_id"], []).append(record)
        available: list[ImmutableQualificationRecord] = []
        for identifier, revisions in sorted(grouped.items()):
            ordered = sorted(revisions, key=lambda r: r.data["revision"])
            last = ordered[-1]
            data = last.data
            revision_numbers = [r.data["revision"] for r in ordered]
            key = (identifier, data["revision"])
            previous_latest = self._latest_revisions.get(identifier, 0)
            self._latest_revisions[identifier] = max(previous_latest, data["revision"])
            if data["revision"] < previous_latest:
                issues.append("QUALIFICATION_RECORD_REVISION_ROLLBACK:" + identifier)
                continue
            pin = self._revision_pins.setdefault(key, last.digest)
            if len(set(revision_numbers)) != len(revision_numbers) or pin != last.digest:
                issues.append("IMMUTABLE_RECORD_REVISION_VIOLATION:" + identifier)
                continue
            if len(ordered) > 1 and data["supersedes"] != ordered[-2].data["revision"]:
                issues.append("RECORD_REVISION_SUCCESSOR_REQUIRED:" + identifier)
                continue
            if data["withdrawn"] or data["status"] != "AVAILABLE_FOR_MATCH":
                continue
            blockers = evidence_blockers(last, cast(Path, self.directory))
            if blockers:
                issues.extend(identifier + ":" + reason for reason in blockers)
            else:
                available.append(last)
        return tuple(available), tuple(issues)


_PROVIDER: QualificationRecordProvider | None = None


def production_provider() -> QualificationRecordProvider:
    global _PROVIDER
    configured = os.environ.get("FRP_QUALIFICATION_RECORD_DIR")
    directory = Path(configured).resolve() if configured else None
    if _PROVIDER is None or _PROVIDER.directory != directory:
        _PROVIDER = QualificationRecordProvider(directory)
    return _PROVIDER


__all__ = (
    "ImmutableQualificationRecord",
    "QualificationRecordProvider",
    "QualificationRecordSchema",
    "canonical_json",
    "canonical_record",
    "content_digest",
    "evidence_blockers",
    "production_provider",
)
