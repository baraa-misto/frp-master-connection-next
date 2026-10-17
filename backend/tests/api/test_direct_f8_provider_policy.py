"""Lifecycle/import policy doubles; no test document becomes production evidence."""

from __future__ import annotations

import json
import runpy
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from tests.api.test_direct_f8_records import install_index
from tests.direct_f8_fixtures import qa_design, synthetic_record

import frp_master_connection.application.direct_qualification_statistics as statistics
import frp_master_connection.infrastructure.direct_qualification_records as records
import frp_master_connection.qualification_admin as admin
from frp_master_connection.application.direct_qualification_matching import (
    match_scope,
    scope_fields,
)


@pytest.fixture(scope="module")
def scope() -> dict[str, Any]:
    return qa_design()[2]


def authority_policy_double(scope: dict[str, Any], directory: Path) -> dict[str, Any]:
    """Negative spoof fixture: real evidence validation rejects its synthetic bytes.

    Lifecycle-only tests replace evidence validation explicitly. This is not an
    approved record, not installed in the running app, and not a QA activation.
    """
    payload = synthetic_record(scope, directory)
    payload.update(
        synthetic=False,
        activation_permitted=True,
        evidence_origin="REAL_CONTROLLED_EVIDENCE",
        status="AVAILABLE_FOR_MATCH",
        digest="",
    )
    for document in payload["source_documents"]:
        document["origin"] = "REAL_CONTROLLED_EVIDENCE"
    return payload


def test_available_successor_rollback_withdrawal_and_pins(
    tmp_path: Path,
    scope: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = records.canonical_record(authority_policy_double(scope, tmp_path))
    assert "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN" in records.evidence_blockers(
        first, tmp_path
    )
    # Narrow authority double tests lifecycle mechanics independently of authority.
    monkeypatch.setattr(records, "evidence_blockers", lambda _record, _directory: ())
    provider = records.QualificationRecordProvider(tmp_path, (first,))
    assert provider.read() == ((first,), ())
    revised = first.data
    revised.update(revision=2, supersedes=1, digest="")
    second = records.canonical_record(revised)
    provider.records = (first, second)
    assert provider.read() == ((second,), ())
    provider.records = (first,)
    assert "ROLLBACK" in provider.read()[1][0]
    provider.records = (second, second)
    assert "IMMUTABLE" in provider.read()[1][0]
    changed = second.data
    changed.update(validity_notes="Policy mutation test", digest="")
    provider.records = (records.canonical_record(changed),)
    assert "IMMUTABLE" in provider.read()[1][0]
    broken = second.data
    broken.update(revision=3, supersedes=None, digest="")
    provider.records = (first, records.canonical_record(broken))
    assert "SUCCESSOR" in provider.read()[1][0]
    withdrawn = first.data
    withdrawn.update(withdrawn=True, status="WITHDRAWN", digest="")
    assert (
        records.QualificationRecordProvider(
            tmp_path, (records.canonical_record(withdrawn),)
        ).read()[0]
        == ()
    )


def test_offline_publisher_preserves_status_and_document_identity_under_authority_double(
    tmp_path: Path,
    scope: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    payload = synthetic_record(scope, source)
    package = source / "record.json"
    package.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(admin, "evidence_blockers", lambda _record, _directory: ())
    output = tmp_path / "output"
    assert admin.validate_package(package, output) == 0
    installed = records.canonical_record(
        json.loads(next(output.glob("*.qualification.json")).read_text(encoding="utf-8"))
    )
    assert installed.data["status"] == "RDP_APPROVED"
    assert installed.data["synthetic"] is True
    assert installed.data["activation_permitted"] is False
    assert records.QualificationRecordProvider(output).read()[0] == ()
    payload.update(revision=2, supersedes=1, digest="")
    package.write_text(json.dumps(payload), encoding="utf-8")
    assert admin.validate_package(package, output) == 0
    assert len(list(output.glob("*.qualification.json"))) == 2
    assert json.loads((output / "catalog.qualification-index.json").read_text())["generation"] == 3
    payload.update(revision=3, supersedes=2, digest="")
    package.write_text(json.dumps(payload), encoding="utf-8")
    (output / "LAB.synthetic.txt").write_text("conflicting bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="IMMUTABLE_BYTES_CONFLICT"):
        admin.validate_package(package, output)


@pytest.mark.parametrize("mode", ["invalid", "synthetic", "entrypoint"])
def test_admin_cli_never_approves_evidence(
    tmp_path: Path,
    scope: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    package = tmp_path / "record.json"
    package.write_text(
        json.dumps(synthetic_record(scope, tmp_path)) if mode != "invalid" else "invalid",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["qualification-admin", str(package), "--output", str(tmp_path / "output")]
    )
    if mode == "entrypoint":
        with pytest.raises(SystemExit) as exit_result:
            runpy.run_path(str(Path(admin.__file__)), run_name="__main__")
    else:
        with pytest.raises(SystemExit) as exit_result:
            admin.main()
    assert exit_result.value.code == (2 if mode == "invalid" else 1)
    assert not list((tmp_path / "output").glob("*.qualification.json"))


def test_all_explicit_positive_approval_paths_remain_synthetic(
    tmp_path: Path,
    scope: dict[str, Any],
) -> None:
    payload = synthetic_record(scope, tmp_path, n=11)
    payload["specimens"][-1].update(
        accepted_or_excluded="EXCLUDED",
        exclusion_rationale="SYNTHETIC QA approved anomaly",
        exclusion_approval_document_id="RDP",
    )
    payload["engineer_approval"]["exclusion_document_ids"] = ["RDP"]
    payload["engineer_approval"]["scope_rule_ids"] = ["EXPLICIT"]
    field = "geometry_scope.row_count"
    payload["scope_rules"] = [
        {
            "rule_id": "EXPLICIT",
            "kind": "EXACT",
            "fields": [field],
            "tested_values": [scope_fields(payload)[field]],
            "unit_or_frame": "1",
            "evidence_document_id": "LAB",
            "rdp_approval_document_id": "RDP",
        }
    ]
    project_doc = deepcopy(payload["source_documents"][0])
    project_doc.update(document_id="AHJ", approval_role="AHJ")
    payload["source_documents"].append(project_doc)
    payload["engineer_approval"].update(
        project_or_ahj_acceptance_required=True, project_or_ahj_document_ids=["AHJ"]
    )
    payload["digest"] = ""
    blockers = records.evidence_blockers(records.canonical_record(payload), tmp_path)
    assert set(blockers) == {
        "SYNTHETIC_QA_CANNOT_QUALIFY_PRODUCTION_DESIGN",
        "PRODUCTION_ACTIVATION_NOT_PERMITTED",
    }


@pytest.mark.parametrize("mutation", ["empty-digest", "duplicate-index", "escape-index"])
def test_external_controlled_index_and_sealed_digest_fail_closed(
    tmp_path: Path, scope: dict[str, Any], mutation: str
) -> None:
    record = synthetic_record(scope, tmp_path)
    if mutation == "empty-digest":
        record["digest"] = ""
    path = tmp_path / "qa.qualification.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    install_index(tmp_path)
    index_path = tmp_path / "catalog.qualification-index.json"
    index = json.loads(index_path.read_text())
    if mutation == "duplicate-index":
        index["entries"].append(index["entries"][0])
    elif mutation == "escape-index":
        index["entries"][0]["filename"] = "../qa.qualification.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    available, issues = records.QualificationRecordProvider(tmp_path).read()
    assert not available
    assert issues


def test_quantile_dependency_failure_and_phi_domain_are_fail_closed(
    tmp_path: Path, scope: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from scipy.stats import t  # type: ignore[import-untyped]

    monkeypatch.setattr(t, "ppf", lambda _p, _df: 0.0)
    with pytest.raises(ValueError, match="QUANTILE_AUTHORITY_INVALID"):
        statistics.connection_t(10)
    payload = synthetic_record(scope, tmp_path)
    for i, specimen in enumerate(payload["specimens"]):
        specimen["test_strength"] = str(1000 + i * 100)
    monkeypatch.setattr(statistics, "connection_t", lambda _n: Decimal(-1))
    assert (
        "QUALIFICATION_PHI_OUTSIDE_VALID_DOMAIN"
        in statistics.recompute_statistics(
            payload["specimens"], payload["statistical_protocol"]
        ).blockers
    )


@pytest.mark.parametrize(
    "field", ["geometry_scope.row_count", "geometry_scope.bolts_per_row", "connection_scope.lap"]
)
def test_ranges_never_interpolate_discrete_configuration(
    tmp_path: Path, scope: dict[str, Any], field: str
) -> None:
    payload = synthetic_record(scope, tmp_path)
    expected = scope_fields(payload)[field]
    payload["scope_rules"] = [
        {
            "rule_id": "BAD_RANGE",
            "kind": "INCLUSIVE_RANGE",
            "fields": [field],
            "tested_values": [expected],
            "lower": "1",
            "upper": "10",
            "inclusive": True,
            "unit_or_frame": "mm",
            "correlation_constraints": [],
        }
    ]
    assert match_scope(payload, scope)[0]


def test_correlated_multi_product_equivalence_tuple(tmp_path: Path, scope: dict[str, Any]) -> None:
    payload = synthetic_record(scope, tmp_path)
    fields = [
        "material_identity.member-a.actual_product.product",
        "material_identity.member-b.actual_product.product",
    ]
    values = [scope_fields(payload)[field] for field in fields]
    payload["scope_rules"] = [
        {
            "rule_id": "PRODUCT_PAIR",
            "kind": "APPROVED_PRODUCT_EQUIVALENCE",
            "fields": fields,
            "tested_values": values,
            "approved_values": [values],
            "correlation_constraints": [],
        }
    ]
    assert not match_scope(payload, scope)[0]


def test_invalid_numeric_range_is_a_mismatch(tmp_path: Path, scope: dict[str, Any]) -> None:
    payload = synthetic_record(scope, tmp_path)
    field = "geometry_scope.pitch.value"
    payload["scope_rules"] = [
        {
            "rule_id": "BAD_NUMBER",
            "kind": "INCLUSIVE_RANGE",
            "fields": [field],
            "tested_values": [scope_fields(payload)[field]],
            "lower": "not-a-number",
            "upper": "70",
            "inclusive": True,
            "unit_or_frame": "mm",
            "correlation_constraints": [],
        }
    ]
    assert "GEOMETRY MISMATCH" in match_scope(payload, scope)[0]
