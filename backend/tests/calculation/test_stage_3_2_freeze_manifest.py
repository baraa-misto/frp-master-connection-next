"""Governance/reproducibility audit for the accepted Stage 3.2 Tee baseline."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

from tests.calculation.test_scope_boundaries import (
    _FROZEN_DEPENDENCIES,
    _assert_frozen_dependency_bytes,
    _historical_dependency_bytes,
    _restore_frozen_dependency_bytes,
)

_MANIFEST_RELATIVE_PATH = "docs/governance/STAGE_3_2_TEE_CONNECTION_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "25A244EBFBC3AC7990B45657025FD6A1FD0C59544BE2ECB13738DFBCC34C9E7E"
_PRODUCT_BASELINE = "9aa5706e89639e990a701de965b04fa448d09c26"
_STAGE_2_3_FREEZE_TARGET = "5bc545ab8251f9bd49dedc776962937ed5e822a2"
_STAGE_2_3_FREEZE_TAG = "stage-2.3-interface-geometry-freeze"
_STAGE_3_2_FREEZE_TAG = "stage-3.2-tee-connection-freeze"
_STAGE_3_2_FREEZE_TARGET = "d16b354732c90bf3bf7847c62be652c230a9f91e"
_STAGE_3_2_REVISIONS = {
    "Stage 3.2",
    "Stage 3.2-R2",
    "Stage 3.2-R4",
    "Stage 3.2-R7",
    "Stage 3.2-R8",
    "Stage 3.2-R9",
    "Stage 3.2-R10",
    "Stage 3.2-R12",
    "Stage 3.2-R13",
    "Stage 3.2-R14B",
}


def _repository_root() -> Path:
    return Path(__file__).parents[3]


def _git(repository_root: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed repository-governance queries
        ["git", *arguments],  # noqa: S607 - fixed repository-governance queries
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tag_is_available(repository_root: Path, tag: str) -> bool:
    tag_ref = repository_root / ".git" / "refs" / "tags" / tag
    packed_refs = repository_root / ".git" / "packed-refs"
    return tag_ref.exists() or (
        packed_refs.exists() and tag in packed_refs.read_text(encoding="utf-8")
    )


def _manifest() -> tuple[bytes, dict[str, object]]:
    raw = (_repository_root() / _MANIFEST_RELATIVE_PATH).read_bytes()
    return raw, cast(dict[str, object], json.loads(raw))


def _artifact_entries(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    entries = manifest[key]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return cast(list[dict[str, object]], entries)


def _assert_sha256_artifacts(entries: list[dict[str, object]]) -> None:
    repository_root = _repository_root()
    for entry in entries:
        path = entry["path"]
        expected = entry["sha256"]
        assert isinstance(path, str)
        assert isinstance(expected, str)
        assert hashlib.sha256((repository_root / path).read_bytes()).hexdigest().upper() == expected


def test_stage_3_2_freeze_manifest_is_byte_exact_and_internally_consistent() -> None:
    raw, manifest = _manifest()
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.2-tee-connection-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.2"

    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    freeze_commit = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert baseline == {
        "commit": _PRODUCT_BASELINE,
        "subject": "feat: embed material axes on profile regions",
        "commit_count": 61,
        "branch": "main",
    }
    assert freeze_commit["identity"] == "SELF"
    assert "commit" not in freeze_commit
    assert freeze_commit["expected_commit_count"] == 62
    assert freeze_commit["tag"] == _STAGE_3_2_FREEZE_TAG

    stage_3_2 = _artifact_entries(manifest, "accepted_stage_3_2_controlled_artifacts")
    inherited = _artifact_entries(manifest, "inherited_stage_2_controlled_artifacts")
    assert len(stage_3_2) == 30
    assert len(inherited) == 15
    assert {cast(str, item["revision"]) for item in stage_3_2} == _STAGE_3_2_REVISIONS
    assert {cast(str, item["kind"]) for item in stage_3_2} == {
        "engineering-specification",
        "golden-benchmark",
        "authority-ledger",
    }
    all_entries = [*stage_3_2, *inherited]
    paths = [cast(str, item["path"]) for item in all_entries]
    artifact_ids = [cast(str, item["artifact_id"]) for item in all_entries]
    assert len(paths) == len(set(paths)) == 45
    assert len(artifact_ids) == len(set(artifact_ids)) == 45
    _assert_sha256_artifacts(all_entries)

    ci = cast(dict[str, object], manifest["accepted_ci_evidence"])
    assert ci["baseline_commit"] == _PRODUCT_BASELINE
    assert (ci["run_number"], ci["jobs_green"], ci["jobs_total"]) == (56, 4, 4)
    assert (ci["frontend_tests_passed"], ci["frontend_tests_total"]) == (288, 288)
    assert ci["frontend_test_files"] == 21

    fingerprints = cast(dict[str, object], manifest["controlled_r4_fingerprints"])
    assert set(fingerprints) == {
        "us_execution",
        "us_preview",
        "si_execution",
        "si_preview",
        "deprecated_si_execution",
        "deprecated_si_preview",
    }
    assert all(isinstance(value, str) and len(value) == 64 for value in fingerprints.values())

    r10 = cast(dict[str, object], manifest["r10_fixed_grid_transition_provenance"])
    assert r10["historical_r9_commit"] == "cc336f6a7161200656f1f4689c8b72585e6627d1"
    assert r10["controlled_r10_commit"] == "a447ff8f384914b9c466ebd4241f3b195188926a"
    assert r10["r10a_tests_only_commit"] == "865b08b2a4d52c8bb17b35ef06faf2486e6346e5"
    transitions = r10["nonzero_transitions"]
    assert isinstance(transitions, list)
    assert [cast(dict[str, object], item)["brace_inclination_degrees"] for item in transitions] == [
        "30",
        "-30",
        "27.5",
    ]

    assert len(cast(list[object], manifest["accepted_behavioral_contracts"])) >= 12
    assert len(cast(list[object], manifest["deliberate_limitations"])) >= 8


def test_stage_3_2_freeze_git_objects_and_transition_register_remain_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    source_trees = cast(dict[str, object], manifest["source_trees"])
    dependencies = cast(dict[str, object], manifest["frontend_dependency_identities"])
    package = cast(dict[str, object], dependencies["package_json"])
    lock = cast(dict[str, object], dependencies["package_lock"])

    if _tag_is_available(repository_root, _STAGE_3_2_FREEZE_TAG):
        assert (
            _git(repository_root, "rev-parse", f"{_STAGE_3_2_FREEZE_TAG}:frontend/src")
            == source_trees["frontend_src"]
        )
        assert (
            _git(repository_root, "rev-parse", f"{_STAGE_3_2_FREEZE_TAG}:backend/src")
            == source_trees["backend_src"]
        )
    for record in (package, lock):
        path = cast(str, record["path"])
        frozen = _historical_dependency_bytes(repository_root, path)
        _assert_frozen_dependency_bytes(path, frozen)
        assert _FROZEN_DEPENDENCIES[path][0] == record["git_blob"]
    assert _FROZEN_DEPENDENCIES[cast(str, lock["path"])][1] == lock["sha256"]

    transition = cast(dict[str, object], manifest["r14b_fingerprint_transition_register"])
    assert transition["identity"] == "Stage 3.2-R14B material-basis fingerprint transitions"
    transition_path = repository_root / cast(str, transition["path"])
    assert hashlib.sha256(transition_path.read_bytes()).hexdigest().upper() == transition["sha256"]


def test_stage_2_3_freeze_target_and_stage_3_2_self_resolution_remain_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    inherited_freeze = cast(dict[str, object], manifest["existing_stage_2_3_freeze"])
    assert inherited_freeze["tag"] == _STAGE_2_3_FREEZE_TAG
    assert inherited_freeze["tag_type"] == "annotated"
    assert inherited_freeze["target"] == _STAGE_2_3_FREEZE_TARGET
    record_path = repository_root / cast(str, inherited_freeze["record_path"])
    assert (
        hashlib.sha256(record_path.read_bytes()).hexdigest().upper()
        == inherited_freeze["record_sha256"]
    )
    record = record_path.read_text(encoding="utf-8")
    assert _STAGE_2_3_FREEZE_TAG in record
    assert _STAGE_2_3_FREEZE_TARGET in record

    if _tag_is_available(repository_root, _STAGE_2_3_FREEZE_TAG):
        assert _git(repository_root, "rev-list", "-n", "1", _STAGE_2_3_FREEZE_TAG) == (
            _STAGE_2_3_FREEZE_TARGET
        )

    if _tag_is_available(repository_root, _STAGE_3_2_FREEZE_TAG):
        assert _git(repository_root, "rev-list", "-n", "1", _STAGE_3_2_FREEZE_TAG) == (
            _STAGE_3_2_FREEZE_TARGET
        )

    shallow_file = repository_root / ".git" / "shallow"
    if shallow_file.exists():
        assert (
            _git(repository_root, "rev-parse", "HEAD")
            in shallow_file.read_text(encoding="utf-8").splitlines()
        )
    else:
        _git(repository_root, "cat-file", "-e", f"{_PRODUCT_BASELINE}^{{commit}}")


# All ten pre-security annotated tags, independently retained from the accepted
# 2e4416a baseline. A missing shallow ref is not interpreted as successor history.
_EXISTING_TAG_IDENTITIES = {
    "stage-2.3-interface-geometry-freeze": (
        "0296c360101fccbeac0cf321fddb5f0e9f37a3dd",
        "5bc545ab8251f9bd49dedc776962937ed5e822a2",
    ),
    "stage-3.2-tee-connection-freeze": (
        "17aaec64e72131a7030780f3c581e8c4dc1d19c0",
        "d16b354732c90bf3bf7847c62be652c230a9f91e",
    ),
    "stage-3.3-clip-angle-family-freeze": (
        "c22433084106a4da3006b610cc90429aba1660ce",
        "a4d21506d45d2d21d3f5039b662ea56ec6c5da9f",
    ),
    "stage-3.4-multi-member-tee-family-freeze": (
        "282724c1fe2fbbeea9f742921aba5996028fd60b",
        "2303ec713d6d038b935e076b909c3b639ced0e09",
    ),
    "stage-3.5-concrete-support-shear-family-freeze": (
        "7d9eaa40aa43f29e52fbae78b40057b31eaa8af8",
        "7bb83e5c8814781419c0789b7428bd46572d514c",
    ),
    "stage-3.6-wi-web-splice-family-freeze": (
        "748d684ae08d86d6335fc26c9bff1e6c0389aa25",
        "031e8367b25765652447fb358e54dd5facd1238b",
    ),
    "stage-3.7-column-base-shear-family-freeze": (
        "cbce5bc3e6ab61b550b3848982d6493a32a56bdb",
        "b0a6ecdf03c88768ff6ab29e584a992231812bda",
    ),
    "stage-4.1-beam-moment-splice-family-freeze": (
        "5dd3e25ac1e55f3304e802e931dab90a0f3cd767",
        "18419606f4143f27240a39374b25e294a9f39253",
    ),
    "stage-4.1a-wi-major-axis-moment-splice-freeze": (
        "a265ff394413d8fef16e7012c1de910bf3ece1b7",
        "cc9effad0691d083bb204c44ec3fb6e9dfb3671d",
    ),
    "stage-4.2-wi-beam-concrete-wall-moment-connection-freeze": (
        "5ad81fe69c1ea17bc0a76daf34cf27f44963cecf",
        "c8094293e6da49aa830b5801f49aae537cccae2b",
    ),
}


def test_all_ten_pre_security_freeze_tags_remain_immutable() -> None:
    root = _repository_root()
    assert len(_EXISTING_TAG_IDENTITIES) == 10
    for tag, (expected_object, expected_target) in _EXISTING_TAG_IDENTITIES.items():
        if _tag_is_available(root, tag):
            assert _git(root, "cat-file", "-t", tag) == "tag"
            assert _git(root, "rev-parse", tag) == expected_object
            assert _git(root, "rev-parse", tag + "^{}") == expected_target


@pytest.mark.parametrize("path", tuple(_FROZEN_DEPENDENCIES))
def test_stage_3_2_historical_dependency_survives_security_successor(path: str) -> None:
    root = _repository_root()
    current = (root / path).read_text(encoding="utf-8").encode()
    historical = _historical_dependency_bytes(root, path)
    assert current != historical
    assert _restore_frozen_dependency_bytes(path, current) == historical
    _assert_frozen_dependency_bytes(path, historical)


@pytest.mark.parametrize("path", tuple(_FROZEN_DEPENDENCIES))
def test_stage_3_2_missing_objects_use_exact_reconstruction(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository_root()
    expected = _historical_dependency_bytes(root, path)
    original_run = subprocess.run

    def without_historical_object(
        args: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "cat-file", "-e"]:
            return subprocess.CompletedProcess(args, 1, b"", b"object absent")
        # Fixed resolver calls use only cwd/check/capture_output.
        return original_run(
            args,
            cwd=cast(Path, kwargs["cwd"]),
            check=True,
            capture_output=True,
        )

    monkeypatch.setattr(subprocess, "run", without_historical_object)
    assert _historical_dependency_bytes(root, path) == expected


@pytest.mark.parametrize("path", tuple(_FROZEN_DEPENDENCIES))
def test_stage_3_2_corrupted_historical_object_fails_closed(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_run = subprocess.run

    def corrupt_object(
        args: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "cat-file", "-e"]:
            return subprocess.CompletedProcess(args, 0, b"", b"")
        if args[:3] == ["git", "cat-file", "blob"]:
            return subprocess.CompletedProcess(args, 0, b"corrupted historical bytes", b"")
        return original_run(
            args,
            cwd=cast(Path, kwargs["cwd"]),
            check=True,
            capture_output=True,
        )

    monkeypatch.setattr(subprocess, "run", corrupt_object)
    with pytest.raises(AssertionError, match="historical SHA-256"):
        _historical_dependency_bytes(_repository_root(), path)
