"""Governance/reproducibility audit for the accepted Stage 3.4 Tee family."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Literal, NamedTuple, cast

import pytest

from frp_master_connection.api.multi_member_tee_mapping import map_multi_member_tee_request
from frp_master_connection.api.multi_member_tee_schemas import MultiMemberTeeRequestDTO
from frp_master_connection.application.multi_member_tee_orchestration import (
    MultiMemberTeePreviewResult,
    preview_multi_member_tee,
)
from tests.multi_member_tee_fixtures import (
    build_expanded_multi_member_tee_payload,
    build_multi_member_tee_payload,
)

_MANIFEST_RELATIVE_PATH = "docs/governance/STAGE_3_4_MULTI_MEMBER_TEE_FAMILY_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "EE4BADFE145B9FA5815D547C079A371C8C907613CB7253E4A12F922CBF9833DD"
_PRODUCT_BASELINE = "b2da06ea04276e2113906d4e7c2b4295496f685f"
_STAGE_3_4_TAG = "stage-3.4-multi-member-tee-family-freeze"
_FREEZE_SUBJECT = "chore: freeze Stage 3.4 multi-member tee family baseline"
_FREEZE_COMMIT_COUNT = 80
_EXPECTED_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "2f0d679488f2414a02b201f9efb5cf0f09d2f177",
    "accepted_frontend_tree": "33000ba7f25108dd3b944b2690c89fe257dcb0b2",
    "accepted_backend_src_tree": "91c91446a9c31440693b37c88195be02e60c98b1",
    "accepted_frontend_src_tree": "21676d8011c07d804fb334393499cfd42145849d",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "15e39a30f7c5e9793941827c61403d4309ac3bf3",
    "accepted_golden_tree": "0ed98af247762493d148284a03819708c472ccff",
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
_EXISTING_TAGS = {
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
}
_ACCEPTANCE_CHAIN = [
    (
        "7154d62f0476d69899d23ee5a27e31362da49f08",
        "feat: add multi-member tee node",
    ),
    (
        "731cc0a31c6ed564681aaa157ee29d37f9e9d177",
        "test: make Stage 3.3 freeze audit successor-safe",
    ),
    (
        "51fd10ffe269fd4b07000eb3dd234411315d7429",
        "fix: render multi-member tee workspace",
    ),
    (
        _PRODUCT_BASELINE,
        "feat: expand multi-member tee profiles and supports",
    ),
]
_EXTERNAL_ORDER_HASHES = {
    "Stage 3.4A": "3C41E877A601690F6B5D1047645B64ACDF75CD3BDACADCB7FD28CD010C93D182",
    "Stage 3.4A-R1": "F0663CF25973CAA7B654DCD60B4F9F09433B1FC8CE9B4905C4F884A453B5A09B",
    "Stage 3.4A-R2": "D8D0DD0D0D3E1B2E5D383C686A2AEEAF8FD896BD686A46D47A99397331173907",
    "Stage 3.4B": "BCA7A0982FA903DACC9ED5DCA59FE48FDBEE06D99B677A227FF42533FB6C106F",
    "Stage 3.4 Freeze": ("93750C4E403DAF36F2B1858154FF2B36D30D128E3A6AF1673F2682EF9B6A2A88"),
}
_SUCCESSOR_POLICY_RULES = {
    "Future stages may reuse or refactor shared infrastructure but may not silently alter "
    "frozen Stage 3.4 contracts.",
    "Historical freeze and tag evidence must be retained.",
    "Successor-safe Stage 3.4 freeze-audit compatibility is required.",
    "The stage-3.4-multi-member-tee-family-freeze tag is immutable and shall never move.",
}


class _FreezeResolution(NamedTuple):
    revision: str | None
    source: Literal["tag", "object", "manifest_only"]


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


def _is_shallow(repository_root: Path) -> bool:
    return _git(repository_root, "rev-parse", "--is-shallow-repository") == "true"


def _manifest() -> tuple[bytes, dict[str, object]]:
    raw = (_repository_root() / _MANIFEST_RELATIVE_PATH).read_bytes()
    return raw, cast(dict[str, object], json.loads(raw))


def _assert_manifest_bytes(raw: bytes) -> None:
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256


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
        actual = hashlib.sha256((repository_root / path).read_bytes()).hexdigest().upper()
        assert actual == expected


def _assert_pinned_freeze_records(manifest: dict[str, object]) -> None:
    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    assert baseline["commit"] == _PRODUCT_BASELINE
    assert baseline["commit_count"] == 79

    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["expected_commit_count"] == _FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _FREEZE_SUBJECT
    assert freeze["freeze_tag"] == _STAGE_3_4_TAG
    assert freeze["tag_type"] == "annotated"

    assert manifest["repository_identities"] == _EXPECTED_REPOSITORY_IDENTITIES
    assert set(cast(list[str], manifest["future_stage_policy"])) >= _SUCCESSOR_POLICY_RULES


def _assert_expected_freeze_target(resolved_target: str, expected_target: str) -> None:
    assert resolved_target == expected_target


def _current_head_is_freeze_commit(repository_root: Path) -> bool:
    return _git(repository_root, "show", "-s", "--format=%s", "HEAD") == _FREEZE_SUBJECT


def _resolve_stage_3_4_freeze(
    repository_root: Path,
    *,
    allow_tag: bool = True,
    allow_external_target: bool = True,
    allow_current_head: bool = True,
) -> _FreezeResolution:
    tag_ref = f"refs/tags/{_STAGE_3_4_TAG}"
    supplied_target = os.environ.get("STAGE_3_4_FREEZE_TARGET")
    if allow_tag and _tag_is_available(repository_root, _STAGE_3_4_TAG):
        assert _git(repository_root, "cat-file", "-t", tag_ref) == "tag"
        resolved_target = _git(repository_root, "rev-parse", f"{tag_ref}^{{}}")
        if supplied_target is not None:
            _assert_expected_freeze_target(resolved_target, supplied_target)
        return _FreezeResolution(resolved_target, "tag")
    if (
        allow_external_target
        and supplied_target is not None
        and _object_is_available(repository_root, f"{supplied_target}^{{commit}}")
    ):
        resolved_target = _git(repository_root, "rev-parse", f"{supplied_target}^{{commit}}")
        _assert_expected_freeze_target(resolved_target, supplied_target)
        return _FreezeResolution(resolved_target, "object")
    if allow_current_head and _current_head_is_freeze_commit(repository_root):
        return _FreezeResolution(_git(repository_root, "rev-parse", "HEAD"), "object")
    return _FreezeResolution(None, "manifest_only")


def _assert_freeze_object(repository_root: Path, revision: str) -> None:
    assert _git(repository_root, "show", "-s", "--format=%s", revision) == _FREEZE_SUBJECT
    if not _is_shallow(repository_root):
        assert int(_git(repository_root, "rev-list", "--count", revision)) == (_FREEZE_COMMIT_COUNT)
        assert _git(repository_root, "rev-parse", f"{revision}^") == _PRODUCT_BASELINE

    identities = _EXPECTED_REPOSITORY_IDENTITIES
    tree_expectations = {
        "backend/src": cast(str, identities["accepted_backend_src_tree"]),
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
            == (package["git_blob"])
        )


def _preview(payload: dict[str, object]) -> MultiMemberTeePreviewResult:
    dto = MultiMemberTeeRequestDTO.model_validate(payload)
    return preview_multi_member_tee(map_multi_member_tee_request(dto))


def _fingerprint_record(result: MultiMemberTeePreviewResult) -> dict[str, str]:
    return {
        "input": result.input_fingerprint,
        "engineering": result.engineering_fingerprint,
        "support_wrench": result.support_wrench.wrench_fingerprint,
    }


def test_stage_3_4_freeze_manifest_is_byte_exact_and_internally_consistent() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.4-multi-member-tee-family-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.4"
    assert manifest["freeze_name"] == "Multi-Member Tee Family Accepted Baseline"

    controlling_order = cast(dict[str, object], manifest["controlling_order"])
    assert controlling_order["sha256"] == (
        "93750C4E403DAF36F2B1858154FF2B36D30D128E3A6AF1673F2682EF9B6A2A88"
    )
    assert str(controlling_order["final_sentinel"]).endswith(
        "DO NOT PROCEED IF THIS LINE IS MISSING"
    )

    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    assert baseline == {
        "commit": _PRODUCT_BASELINE,
        "subject": "feat: expand multi-member tee profiles and supports",
        "commit_count": 79,
        "tracked_file_count": 459,
        "branch": "main",
    }

    controlled = _entries(manifest, "controlled_stage_3_4_repository_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert len(controlled) == 11
    assert len(inherited) == 27
    assert len({cast(str, item["path"]) for item in [*controlled, *inherited]}) == 35
    _assert_sha256_artifacts([*controlled, *inherited])

    orders = _entries(manifest, "external_control_orders")
    assert len(orders) == 5
    assert {cast(str, item["revision"]): cast(str, item["sha256"]) for item in orders} == (
        _EXTERNAL_ORDER_HASHES
    )


def test_stage_3_4_freeze_ci_visual_and_acceptance_evidence_is_exact() -> None:
    _, manifest = _manifest()
    ci = cast(dict[str, dict[str, object]], manifest["ci_evidence"])
    assert ci["superseded_development_run"]["run_number"] == 71
    assert ci["superseded_development_run"]["status"] == "superseded-failure"
    assert (ci["stage_3_4a_r1"]["run_number"], ci["stage_3_4a_r1"]["jobs_green"]) == (
        72,
        4,
    )
    assert (ci["stage_3_4a_r2"]["run_number"], ci["stage_3_4a_r2"]["jobs_green"]) == (
        73,
        4,
    )
    final = ci["stage_3_4b_final"]
    assert (final["run_number"], final["jobs_green"], final["jobs_total"]) == (74, 4, 4)
    assert final["duration"] == "4m53s"
    assert (final["backend_tests_passed"], final["frontend_tests_passed"]) == (2420, 442)
    assert final["frontend_test_files"] == 28
    assert final["dependency_vulnerabilities"] == 0

    visual = cast(dict[str, object], manifest["accepted_visual_evidence"])
    assert visual["status"] == "accepted"
    assert visual["acceptance_date"] == "2026-08-28"
    assert len(cast(list[object], visual["connected_profiles"])) == 3
    assert len(cast(list[object], visual["support_targets"])) == 7
    assert len(cast(list[object], visual["rectangular_behavior"])) == 5


def test_stage_3_4_freeze_acceptance_chain_and_unpublished_candidate_are_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    chain = cast(list[dict[str, object]], manifest["acceptance_chain"])
    assert [(item["commit"], item["subject"]) for item in chain] == _ACCEPTANCE_CHAIN

    if not _is_shallow(repository_root):
        for commit, subject in _ACCEPTANCE_CHAIN:
            assert _git(repository_root, "show", "-s", "--format=%s", commit) == subject
            assert (
                subprocess.run(  # noqa: S603 - fixed ancestry audit
                    ["git", "merge-base", "--is-ancestor", commit, _PRODUCT_BASELINE],  # noqa: S607
                    cwd=repository_root,
                    check=False,
                ).returncode
                == 0
            )
        candidate = cast(dict[str, object], manifest["superseded_unpublished_candidate"])
        candidate_commit = cast(str, candidate["commit"])
        if _object_is_available(repository_root, f"{candidate_commit}^{{commit}}"):
            assert (
                subprocess.run(  # noqa: S603 - fixed non-ancestry audit
                    [  # noqa: S607 - fixed git executable
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        candidate_commit,
                        _PRODUCT_BASELINE,
                    ],
                    cwd=repository_root,
                    check=False,
                ).returncode
                != 0
            )
    candidate = cast(dict[str, object], manifest["superseded_unpublished_candidate"])
    assert candidate["status"] == "superseded-unpublished-not-reachable-from-controlling-main"
    assert candidate["part_of_acceptance_chain"] is False


def test_stage_3_4_freeze_existing_historical_tags_remain_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    freezes = _entries(manifest, "existing_immutable_freezes")
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


def test_stage_3_4_freeze_benchmarks_and_fingerprints_are_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    benchmarks = cast(dict[str, list[str]], manifest["benchmark_identities"])
    golden_paths = {
        "stage_3_4a": (
            "backend/tests/golden/stage_3_4a_multi_member_tee_node_golden_benchmarks_rc1.json"
        ),
        "stage_3_4b": (
            "backend/tests/golden/stage_3_4b_multi_member_tee_profile_support_"
            "expansion_golden_benchmarks_rc1.json"
        ),
    }
    for key, path in golden_paths.items():
        golden = json.loads((repository_root / path).read_text(encoding="utf-8"))
        assert [item["id"] for item in golden["benchmarks"]] == benchmarks[key]

    fingerprints = cast(dict[str, object], manifest["engineering_fingerprints"])
    historical = cast(dict[str, str], fingerprints["historical_stage_3_4a"])
    historical_result = _preview(build_multi_member_tee_payload())
    assert historical_result.engineering_fingerprint == historical["engineering"]
    assert historical_result.support_wrench.wrench_fingerprint == historical["support_wrench"]

    expected = cast(dict[str, dict[str, str]], fingerprints["representative_stage_3_4b"])
    cases = {
        "expanded_default_us": build_expanded_multi_member_tee_payload(),
        "mixed_rhs_us": build_expanded_multi_member_tee_payload(
            profile_families=(
                "RECTANGULAR_HOLLOW_SECTION",
                "FLAT_PLATE",
                "SOLID_RECTANGULAR_SECTION",
            ),
            support_target="RECTANGULAR_HOLLOW_COLUMN_WALL",
        ),
        "mixed_rhs_si": build_expanded_multi_member_tee_payload(
            unit_system="SI",
            profile_families=(
                "RECTANGULAR_HOLLOW_SECTION",
                "FLAT_PLATE",
                "SOLID_RECTANGULAR_SECTION",
            ),
            support_target="RECTANGULAR_HOLLOW_COLUMN_WALL",
        ),
        "all_srs_us": build_expanded_multi_member_tee_payload(
            profile_families=(
                "SOLID_RECTANGULAR_SECTION",
                "SOLID_RECTANGULAR_SECTION",
                "SOLID_RECTANGULAR_SECTION",
            ),
            support_target="SOLID_RECTANGULAR_COLUMN_FACE",
        ),
    }
    actual = {name: _fingerprint_record(_preview(payload)) for name, payload in cases.items()}
    assert actual == expected
    assert actual["mixed_rhs_us"] == actual["mixed_rhs_si"]

    equality = cast(dict[str, object], fingerprints["us_si_equality"])
    assert equality == {
        "fixture": "G22_US_SI_EQUIVALENCE_REPRESENTATIVE_MIXED_NODE",
        "us_case": "mixed_rhs_us",
        "si_case": "mixed_rhs_si",
        "input_equal": True,
        "engineering_equal": True,
        "support_wrench_equal": True,
    }


def test_stage_3_4_frozen_behavior_and_limitation_inventory_is_complete() -> None:
    _, manifest = _manifest()
    contracts = cast(dict[str, object], manifest["frozen_contracts"])
    assert set(contracts) == {
        "topology",
        "connected_profiles",
        "support_matrix",
        "rectangular_sections",
        "joint_equilibrium",
        "geometry_trim_interference",
        "visualization_material_axes",
        "preview_design_error_state",
        "versions",
    }
    topology = cast(dict[str, object], contracts["topology"])
    assert (topology["minimum_active_slots"], topology["maximum_active_slots"]) == (1, 3)
    assert topology["disabled_slots_absent"] is True
    profiles = cast(dict[str, object], contracts["connected_profiles"])
    assert len(cast(list[object], profiles["profiles"])) == 6
    assert profiles["generic_flat_plate_fallback"] is False
    support = cast(dict[str, object], contracts["support_matrix"])
    assert len(cast(list[object], support["targets"])) == 7
    assert support["w_beam_web_present"] is False
    versions = cast(dict[str, object], contracts["versions"])
    assert versions["accepted"] == ["3.4A-RC1", "3.4B-RC1"]
    assert versions["unknown_future_versions_fail_closed"] is True

    limitations = cast(list[str], manifest["deliberate_limitations"])
    assert len(limitations) == 12
    assert "TEE_CONNECTOR_BODY_RESISTANCE = NOT_EVALUATED" in limitations
    assert "MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY = NOT_EVALUATED" in (limitations)
    assert any(value.startswith("RHS_LOCAL_WALL_RESPONSE") for value in limitations)
    assert any(
        value.startswith("SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY")
        for value in limitations
    )


def test_stage_3_4_freeze_resolves_tag_object_or_manifest_only_without_network() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    resolution = _resolve_stage_3_4_freeze(repository_root)
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    assert resolution.source in {"tag", "object"}
    _assert_freeze_object(repository_root, resolution.revision)


def test_stage_3_4_freeze_future_tagless_successor_uses_manifest_only() -> None:
    resolution = _resolve_stage_3_4_freeze(
        _repository_root(),
        allow_tag=False,
        allow_external_target=False,
        allow_current_head=False,
    )
    assert resolution == _FreezeResolution(None, "manifest_only")


def test_stage_3_4_freeze_successor_safe_tamper_guards_remain_strong() -> None:
    raw, manifest = _manifest()

    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")

    tampered_tree = deepcopy(manifest)
    cast(dict[str, object], tampered_tree["repository_identities"])[
        "accepted_frontend_src_tree"
    ] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_tree)

    tampered_package = deepcopy(manifest)
    package = cast(
        dict[str, object],
        cast(dict[str, object], tampered_package["repository_identities"])["frontend_package_lock"],
    )
    package["git_blob"] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered_package)

    tampered_artifact = deepcopy(manifest)
    _entries(tampered_artifact, "controlled_stage_3_4_repository_artifacts")[0]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_sha256_artifacts(
            _entries(tampered_artifact, "controlled_stage_3_4_repository_artifacts")
        )

    tampered_fingerprint = deepcopy(manifest)
    fingerprints = cast(dict[str, object], tampered_fingerprint["engineering_fingerprints"])
    historical = cast(dict[str, str], fingerprints["historical_stage_3_4a"])
    historical["engineering"] = "0" * 64
    assert (
        historical
        != cast(dict[str, object], manifest["engineering_fingerprints"])["historical_stage_3_4a"]
    )

    with pytest.raises(AssertionError):
        _assert_expected_freeze_target("1" * 40, "0" * 40)

    repository_root = _repository_root()
    resolution = _resolve_stage_3_4_freeze(repository_root)
    if resolution.revision is not None:
        with pytest.raises(AssertionError):
            _assert_expected_freeze_target(resolution.revision, "0" * 40)
