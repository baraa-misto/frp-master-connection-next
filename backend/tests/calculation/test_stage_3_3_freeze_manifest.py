"""Governance/reproducibility audit for the accepted Stage 3.3 Clip-Angle family."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Literal, NamedTuple, cast

import pytest

from tests.application.test_stage_3_3c3_r1_material_axes_coverage import (
    PAIRED_PROFILE_FINGERPRINTS,
    PAIRED_SUPPORT_FINGERPRINTS,
    SINGLE_PROFILE_FINGERPRINTS,
    SINGLE_SUPPORT_FINGERPRINTS,
)

_MANIFEST_RELATIVE_PATH = "docs/governance/STAGE_3_3_CLIP_ANGLE_FAMILY_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "74E7180E37E223E8EC6550A46F316A344FF29C6496C25D0A01916AC5B4174CC4"
_PRODUCT_BASELINE = "a15f6f9bc820bc7e2d466db8519bcb9582b96e55"
_STAGE_3_3_TAG = "stage-3.3-clip-angle-family-freeze"
_STAGE_3_3_FREEZE_TARGET = "a4d21506d45d2d21d3f5039b662ea56ec6c5da9f"
_STAGE_3_3_FREEZE_SUBJECT = "chore: freeze Stage 3.3 clip-angle family baseline"
_STAGE_3_3_FREEZE_COMMIT_COUNT = 75
_EXPECTED_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "6f727b3b1ed71992cee652ec6a688d23e0031ba9",
    "accepted_frontend_tree": "3a03a88baa84c2208e6249c70bb89e29ca6ed476",
    "accepted_backend_src_tree": "35f8d93f48cc340c75cf26860d297bc920ddfd49",
    "accepted_frontend_src_tree": "ea62799a02b41c30dbc25c9ad250a318aba953ae",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "51d046f0cdc720c6ed9fb9ad5b27e6d36512462c",
    "accepted_golden_tree": "d62e968dbacc50cc95d351c0bba101e4ce23bdb4",
    "frontend_package_json": {
        "path": "frontend/package.json",
        "git_blob": "b753abd55004168eee5844879f0596d435fe4b5a",
    },
    "frontend_package_lock": {
        "path": "frontend/package-lock.json",
        "git_blob": "ae1831268db42005517343bf555f054a673ae520",
        "sha256": "20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254",
    },
}
_SUCCESSOR_POLICY_RULES = {
    "Future stages may reuse or refactor shared infrastructure but may not silently alter "
    "frozen Stage 3.3 contracts.",
    "Any intentional change must identify the frozen behavior being superseded.",
    "Historical freeze and tag evidence must be retained.",
    "The stage-3.3-clip-angle-family-freeze tag is immutable.",
}
_EXISTING_TAGS = {
    "stage-2.3-interface-geometry-freeze": (
        "0296c360101fccbeac0cf321fddb5f0e9f37a3dd",
        "5bc545ab8251f9bd49dedc776962937ed5e822a2",
    ),
    "stage-3.2-tee-connection-freeze": (
        "17aaec64e72131a7030780f3c581e8c4dc1d19c0",
        "d16b354732c90bf3bf7847c62be652c230a9f91e",
    ),
}


class _FreezeResolution(NamedTuple):
    revision: str | None
    source: Literal["tag", "object", "manifest_only"]


_PROFILE_KEY_MAP = {
    "WIDE_FLANGE": "WIDE_FLANGE_I",
    "RHS": "RECTANGULAR_HOLLOW_SECTION",
    "SRS": "SOLID_RECTANGULAR_SECTION",
}
_SUPPORT_KEY_MAP = {
    "RHS_COLUMN_WALL": "RECTANGULAR_HOLLOW_COLUMN_WALL",
    "SRS_COLUMN_FACE": "SOLID_RECTANGULAR_COLUMN_FACE",
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
    return (
        subprocess.run(  # noqa: S603 - fixed repository-governance query
            ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"],  # noqa: S607
            cwd=repository_root,
            check=False,
        ).returncode
        == 0
    )


def _object_is_available(repository_root: Path, object_name: str) -> bool:
    return (
        subprocess.run(  # noqa: S603 - fixed repository-governance query
            ["git", "cat-file", "-e", object_name],  # noqa: S607
            cwd=repository_root,
            check=False,
        ).returncode
        == 0
    )


def _manifest() -> tuple[bytes, dict[str, object]]:
    raw = (_repository_root() / _MANIFEST_RELATIVE_PATH).read_bytes()
    return raw, cast(dict[str, object], json.loads(raw))


def _assert_manifest_bytes(raw: bytes) -> None:
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256


def _assert_pinned_freeze_records(manifest: dict[str, object]) -> None:
    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    assert baseline["commit"] == _PRODUCT_BASELINE

    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["expected_commit_count"] == _STAGE_3_3_FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _STAGE_3_3_FREEZE_SUBJECT
    assert freeze["tag"] == _STAGE_3_3_TAG
    assert freeze["tag_type"] == "annotated"

    identities = cast(dict[str, object], manifest["repository_identities"])
    assert identities == _EXPECTED_REPOSITORY_IDENTITIES

    successor_policy = cast(list[str], manifest["future_stage_policy"])
    assert set(successor_policy) >= _SUCCESSOR_POLICY_RULES


def _assert_expected_freeze_target(resolved_target: str) -> None:
    assert resolved_target == _STAGE_3_3_FREEZE_TARGET


def _resolve_historical_freeze(repository_root: Path) -> _FreezeResolution:
    tag_ref = f"refs/tags/{_STAGE_3_3_TAG}"
    if _tag_is_available(repository_root, _STAGE_3_3_TAG):
        assert _git(repository_root, "cat-file", "-t", tag_ref) == "tag"
        resolved_target = _git(repository_root, "rev-parse", f"{tag_ref}^{{}}")
        _assert_expected_freeze_target(resolved_target)
        return _FreezeResolution(resolved_target, "tag")
    if _object_is_available(repository_root, f"{_STAGE_3_3_FREEZE_TARGET}^{{commit}}"):
        resolved_target = _git(
            repository_root, "rev-parse", f"{_STAGE_3_3_FREEZE_TARGET}^{{commit}}"
        )
        _assert_expected_freeze_target(resolved_target)
        return _FreezeResolution(resolved_target, "object")
    return _FreezeResolution(None, "manifest_only")


def _assert_historical_freeze_object(
    repository_root: Path,
    revision: str,
    *,
    expected_subject: str = _STAGE_3_3_FREEZE_SUBJECT,
    expected_backend_src_tree: str = "35f8d93f48cc340c75cf26860d297bc920ddfd49",
) -> None:
    _assert_expected_freeze_target(_git(repository_root, "rev-parse", f"{revision}^{{commit}}"))
    assert _git(repository_root, "show", "-s", "--format=%s", revision) == expected_subject
    assert int(_git(repository_root, "rev-list", "--count", revision)) == (
        _STAGE_3_3_FREEZE_COMMIT_COUNT
    )

    identities = _EXPECTED_REPOSITORY_IDENTITIES
    tree_expectations = {
        "backend/src": expected_backend_src_tree,
        "frontend/src": cast(str, identities["accepted_frontend_src_tree"]),
        ".github/workflows": cast(str, identities["accepted_workflow_tree"]),
        "docs/engineering": cast(str, identities["accepted_engineering_tree"]),
        "backend/tests/golden": cast(str, identities["accepted_golden_tree"]),
    }
    for path, expected in tree_expectations.items():
        assert _git(repository_root, "rev-parse", f"{revision}:{path}") == expected

    for key in ("frontend_package_json", "frontend_package_lock"):
        package = cast(dict[str, str], identities[key])
        assert (
            _git(repository_root, "rev-parse", f"{revision}:{package['path']}")
            == package["git_blob"]
        )

    if _object_is_available(repository_root, f"{_PRODUCT_BASELINE}^{{commit}}"):
        assert (
            _git(repository_root, "rev-parse", f"{_PRODUCT_BASELINE}:backend")
            == identities["accepted_backend_tree"]
        )
        assert (
            _git(repository_root, "rev-parse", f"{_PRODUCT_BASELINE}:frontend")
            == identities["accepted_frontend_tree"]
        )


def _entries(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    entries = manifest[key]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return cast(list[dict[str, object]], entries)


def _assert_sha256_artifacts(entries: list[dict[str, object]]) -> None:
    repository_root = _repository_root()
    for entry in entries:
        path = cast(str, entry["path"])
        expected = cast(str, entry["sha256"])
        assert hashlib.sha256((repository_root / path).read_bytes()).hexdigest().upper() == (
            expected
        )


def _translate_keys(values: dict[str, str], aliases: dict[str, str]) -> dict[str, str]:
    return {aliases.get(key, key): value for key, value in values.items()}


def test_stage_3_3_freeze_manifest_is_byte_exact_and_internally_consistent() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.3-clip-angle-family-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.3"
    assert manifest["name"] == "Clip-Angle Family Accepted Baseline"

    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    assert baseline == {
        "commit": _PRODUCT_BASELINE,
        "subject": "fix: restore material axes across clip-angle scenes",
        "commit_count": 74,
        "tracked_file_count": 430,
        "branch": "main",
    }
    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert "commit" not in freeze
    assert freeze["expected_commit_count"] == _STAGE_3_3_FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _STAGE_3_3_FREEZE_SUBJECT
    assert freeze["tag"] == _STAGE_3_3_TAG
    assert freeze["tag_type"] == "annotated"

    controlled = _entries(manifest, "controlled_stage_3_3_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert len(controlled) == 15
    assert len(inherited) == 22
    assert len({cast(str, entry["path"]) for entry in [*controlled, *inherited]}) == 37
    assert len({cast(str, entry["artifact_id"]) for entry in controlled}) == 15
    assert {cast(str, entry["revision"]) for entry in controlled} == {
        "Stage 3.3A",
        "Stage 3.3B",
        "Stage 3.3C1",
        "Stage 3.3C2",
        "Stage 3.3C3",
    }
    _assert_sha256_artifacts([*controlled, *inherited])

    ci = cast(dict[str, object], manifest["accepted_ci_evidence"])
    assert ci["baseline_commit"] == _PRODUCT_BASELINE
    assert (ci["run_number"], ci["jobs_green"], ci["jobs_total"]) == (69, 4, 4)
    assert ci["duration"] == "4m35s"
    assert (ci["backend_tests_passed"], ci["frontend_tests_passed"]) == (2342, 408)
    assert ci["frontend_test_files"] == 26
    assert ci["dependency_vulnerabilities"] == 0

    visual = cast(dict[str, object], manifest["accepted_visual_evidence"])
    assert visual["status"] == "accepted"
    assert visual["acceptance_date"] == "2026-08-27"
    assert len(cast(list[object], visual["single_clip_angle"])) == 7
    assert len(cast(list[object], visual["symmetric_paired_clip_angles"])) == 7
    assert len(cast(list[object], visual["rectangular_architecture"])) == 4

    contracts = cast(dict[str, object], manifest["accepted_behavioral_contracts"])
    assert set(contracts) == {
        "single_clip_angle",
        "symmetric_paired_clip_angles",
        "shared_rectangular_core",
        "visualization_and_state",
    }
    assert len(cast(list[object], manifest["deliberate_limitations"])) == 15
    assert len(cast(list[object], manifest["future_stage_policy"])) == 7


def test_stage_3_3_freeze_repository_and_dependency_identities_remain_exact() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    resolution = _resolve_historical_freeze(repository_root)
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    _assert_historical_freeze_object(repository_root, resolution.revision)


def test_stage_3_3_freeze_acceptance_chain_and_existing_tags_remain_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    chain = cast(list[dict[str, object]], manifest["acceptance_chain"])
    assert len(chain) == 12
    assert cast(str, chain[-1]["commit"]) == _PRODUCT_BASELINE

    shallow = (repository_root / ".git" / "shallow").exists()
    if not shallow:
        for entry in chain:
            commit = cast(str, entry["commit"])
            subject = cast(str, entry["subject"])
            assert _git(repository_root, "show", "-s", "--format=%s", commit) == subject
            assert (
                subprocess.run(  # noqa: S603 - fixed ancestry audit
                    ["git", "merge-base", "--is-ancestor", commit, _PRODUCT_BASELINE],  # noqa: S607
                    cwd=repository_root,
                    check=False,
                ).returncode
                == 0
            )

    freezes = cast(list[dict[str, object]], manifest["existing_immutable_freezes"])
    assert {cast(str, entry["tag"]) for entry in freezes} == set(_EXISTING_TAGS)
    for entry in freezes:
        tag = cast(str, entry["tag"])
        tag_object, peeled_target = _EXISTING_TAGS[tag]
        assert entry["tag_type"] == "annotated"
        assert entry["tag_object"] == tag_object
        assert entry["peeled_target"] == peeled_target
        if _tag_is_available(repository_root, tag):
            assert _git(repository_root, "rev-parse", f"refs/tags/{tag}") == tag_object
            assert _git(repository_root, "rev-parse", f"refs/tags/{tag}^{{}}") == peeled_target


def test_stage_3_3_freeze_benchmark_and_current_fingerprint_identities_are_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    benchmarks = cast(dict[str, list[str]], manifest["benchmark_identities"])
    paths = {
        "stage_3_3c1": (
            "backend/tests/golden/stage_3_3c1_shared_rectangular_section_"
            "full_through_bolt_golden_benchmarks_rc1.json"
        ),
        "stage_3_3c2": (
            "backend/tests/golden/stage_3_3c2_tee_single_clip_support_"
            "rectangular_expansion_golden_benchmarks_rc1.json"
        ),
        "stage_3_3c3": (
            "backend/tests/golden/stage_3_3c3_paired_clip_angle_profile_"
            "support_expansion_golden_benchmarks_rc1.json"
        ),
    }
    for key, path in paths.items():
        golden = json.loads((repository_root / path).read_text(encoding="utf-8"))
        assert [entry["id"] for entry in golden["benchmarks"]] == benchmarks[key]

    fingerprints = cast(dict[str, object], manifest["regression_fingerprints"])
    single_profiles = cast(dict[str, str], fingerprints["current_single_profiles"])
    paired_profiles = cast(dict[str, str], fingerprints["current_paired_profiles"])
    single_supports = cast(dict[str, str], fingerprints["current_single_supports"])
    paired_supports = cast(dict[str, str], fingerprints["current_paired_supports"])
    assert _translate_keys(single_profiles, _PROFILE_KEY_MAP) == SINGLE_PROFILE_FINGERPRINTS
    assert _translate_keys(paired_profiles, _PROFILE_KEY_MAP) == PAIRED_PROFILE_FINGERPRINTS
    assert _translate_keys(single_supports, _SUPPORT_KEY_MAP) == SINGLE_SUPPORT_FINGERPRINTS
    assert _translate_keys(paired_supports, _SUPPORT_KEY_MAP) == PAIRED_SUPPORT_FINGERPRINTS
    assert fingerprints["c3_r1_material_axis_transition_count"] == 0
    assert fingerprints["c3_r1_material_basis_transition_count"] == 0

    stage_3_3b = cast(dict[str, str], fingerprints["stage_3_3b"])
    assert stage_3_3b == {
        "canonical": "1a1967aa0ed47593b5c33fbdef82ae0a4e18dc082500f8d794962b831fd16b5e",
        "engineering": "67fbf413b78f57f73eebb63c467d12c9e299f3edf603edc7f51eeab6a68e1db8",
    }


def test_stage_3_3_freeze_successor_and_zero_transition_records_remain_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    fingerprints = cast(dict[str, object], manifest["regression_fingerprints"])
    successors = cast(dict[str, str], fingerprints["c2_rhs_successor_transitions"])
    assert len(successors) == 10
    assert successors["tee_c2_current"] == (
        "a089c44a4652b207ff1145d8a5790154855c1078cf006a6022c8d649f947a6f9"
    )
    assert successors["single_brace_c2_current"] == (
        "16ae7ce854c5b5b4d34da713373bcf5924f5fc411687e5dc0a765928e5db3288"
    )
    assert successors["single_beam_c2_current"] == (
        "1c995ab0e90b76cd405bff1c5f4990bef2fdbba83e12daac47dffd9fbace7c51"
    )

    inherited = _entries(manifest, "inherited_authorities")
    expected_records = {
        "docs/governance/STAGE_3_3C2_STAGE_3_2_TEE_RHS_FULL_THROUGH_SUCCESSOR.md",
        "docs/governance/STAGE_3_3C2_STAGE_3_3A_SINGLE_ANGLE_RHS_FULL_THROUGH_SUCCESSOR.md",
        "docs/qa/STAGE_3_3C3_R1_MATERIAL_AXES_COVERAGE_BINDING_CORRECTION.md",
    }
    inherited_paths = {cast(str, entry["path"]) for entry in inherited}
    assert expected_records <= inherited_paths
    for path in expected_records:
        assert (repository_root / path).is_file()


def test_stage_3_3_freeze_historical_commit_is_verified_only_when_available() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["tag"] == _STAGE_3_3_TAG
    resolution = _resolve_historical_freeze(repository_root)
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        assert not _tag_is_available(repository_root, _STAGE_3_3_TAG)
        assert not _object_is_available(repository_root, f"{_STAGE_3_3_FREEZE_TARGET}^{{commit}}")
        return
    assert resolution.source in {"tag", "object"}
    _assert_historical_freeze_object(repository_root, resolution.revision)


def test_stage_3_3_freeze_successor_safe_tamper_guards_remain_strong() -> None:
    raw, manifest = _manifest()

    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")

    tampered_backend = deepcopy(manifest)
    cast(dict[str, object], tampered_backend["repository_identities"])[
        "accepted_backend_src_tree"
    ] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_backend)

    tampered_frontend = deepcopy(manifest)
    cast(dict[str, object], tampered_frontend["repository_identities"])[
        "accepted_frontend_src_tree"
    ] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_frontend)

    tampered_package = deepcopy(manifest)
    package = cast(
        dict[str, object],
        cast(dict[str, object], tampered_package["repository_identities"])["frontend_package_json"],
    )
    package["git_blob"] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_package)

    tampered_lock = deepcopy(manifest)
    lock = cast(
        dict[str, object],
        cast(dict[str, object], tampered_lock["repository_identities"])["frontend_package_lock"],
    )
    lock["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_lock)

    with pytest.raises(AssertionError):
        _assert_expected_freeze_target("0" * 40)

    repository_root = _repository_root()
    resolution = _resolve_historical_freeze(repository_root)
    if resolution.revision is not None:
        with pytest.raises(AssertionError):
            _assert_historical_freeze_object(
                repository_root,
                resolution.revision,
                expected_subject="wrong freeze subject",
            )
        with pytest.raises(AssertionError):
            _assert_historical_freeze_object(
                repository_root,
                resolution.revision,
                expected_backend_src_tree="0" * 40,
            )
