"""Successor-safe audit for the accepted Stage 3.7 column-base shear family."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Literal, NamedTuple, cast

import pytest

from tests.calculation.test_scope_boundaries import (
    _SECURITY_HISTORICAL_TEST_PATHS,
    _assert_historical_test_record,
)

_MANIFEST_RELATIVE_PATH = "docs/governance/STAGE_3_7_COLUMN_BASE_SHEAR_FAMILY_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "8C7CD0238C7A95E54E4B6DC987E4A558AE2910DA80342137C7772B7FCF6EC9AE"
_FINGERPRINT_BLOCK_SHA256 = "A594F99085506FDAC341472788EFCF355033B87D68D19D0CE3F03C7B49B22F6B"
_PRODUCT_BASELINE = "0403bc8a4ace0df95b45a84a55832c17b18d6008"
_STAGE_3_7_TAG = "stage-3.7-column-base-shear-family-freeze"
_FREEZE_SUBJECT = "chore: freeze Stage 3.7 column-base shear family baseline"
_FREEZE_COMMIT_COUNT = 96
_EXPECTED_MATRIX = [
    "WIDE_FLANGE_I:SINGLE_BASE_ANGLE",
    "WIDE_FLANGE_I:DOUBLE_BASE_ANGLES",
    "RECTANGULAR_HOLLOW_SECTION:SINGLE_BASE_ANGLE",
    "RECTANGULAR_HOLLOW_SECTION:DOUBLE_BASE_ANGLES",
    "SOLID_RECTANGULAR_SECTION:SINGLE_BASE_ANGLE",
    "SOLID_RECTANGULAR_SECTION:DOUBLE_BASE_ANGLES",
    "ANGLE:SINGLE_BASE_ANGLE",
    "ANGLE:DOUBLE_BASE_ANGLES",
]
_EXPECTED_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "1dadfa386c999031249048ae75889d1a90d7ad3d",
    "accepted_frontend_tree": "329b142aa8aeb04be5439f7ef37c822e0494e3b1",
    "accepted_backend_src_tree": "4de4c4dbdb15f8725e8164958fda35558a09acb7",
    "accepted_frontend_src_tree": "4ca442c7c68cb1658f030c36a21c36353d5d3aa1",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "75187a9d8a29b0c1dade5b26c607d4edd44d77f2",
    "accepted_golden_tree": "5bdf7a833084e3e65b7ce2903f842b5471e7df85",
    "accepted_backend_requirements_tree": "d8e1a9f1c2c89a4e50a181db1997c52b3c9bdf58",
    "backend_pyproject": {
        "path": "backend/pyproject.toml",
        "git_blob": "9caa35e74d01bb040369b72fe19294ba6072a786",
        "sha256": "39BEA635FCE709607E1A4AE11D8B31829DFD07B4CADE332E030486BE1456A116",
    },
    "backend_requirements_readme": {
        "path": "backend/requirements/README.md",
        "git_blob": "f91d715e0446ebd1598ed6accac32d7000fe1b9d",
        "sha256": "6C010A608E4D1076D3384F95A19E21A02B4A782B008046336084EA7D07E91BAD",
    },
    "backend_requirements_lock": {
        "path": "backend/requirements/requirements-dev-py314.lock.txt",
        "git_blob": "e2f9e4051ebff96954e88c6d6a4fc0b8cf3460cc",
        "sha256": "953E6D3F6879CBAA6037AA4E8BA0D41B48380761983DCA4CDABFE54576670E0E",
    },
    "frontend_package_json": {
        "path": "frontend/package.json",
        "git_blob": "b753abd55004168eee5844879f0596d435fe4b5a",
        "sha256": "1085F25B94819ED98EEE10739CF4B419F39BD626CC654699B0380B26341F4359",
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
}
_ACCEPTANCE_CHAIN = [
    (
        "e906ba6faad2e4a85f08cf954c8c95a49a0c6c9f",
        "feat: expand column-base profiles and assemblies",
    ),
    (_PRODUCT_BASELINE, "fix: correct angle-column single bolt path"),
]
_EXTERNAL_ORDER_HASHES = {
    "Stage 3.7A": "81B653E82F44F8E97D2C3587A8266B0C6000C7F730EF60BA49B2199AAC865508",
    "Stage 3.7A-R1": "A57E3BECB55FD8A560BA26745D3147DFD5A6448038113BDF85DE40074EC8BAC3",
    "Stage 3.7 Freeze": "924F001299FD93FDE585B8B6AADBBC1EBDAACAA693264EC5A6048EE77C3270A2",
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


def _git_bytes(repository_root: Path, *arguments: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed repository-governance queries
        ["git", *arguments],  # noqa: S607 - fixed repository-governance queries
        cwd=repository_root,
        check=True,
        capture_output=True,
    ).stdout


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


def _manifest_at_revision(repository_root: Path, revision: str) -> tuple[bytes, dict[str, object]]:
    raw = _git_bytes(repository_root, "cat-file", "blob", f"{revision}:{_MANIFEST_RELATIVE_PATH}")
    return raw, cast(dict[str, object], json.loads(raw))


def _entries(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    entries = manifest[key]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return cast(list[dict[str, object]], entries)


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def _assert_manifest_bytes(raw: bytes) -> None:
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256


def _assert_sha256_artifacts(
    entries: list[dict[str, object]], *, revision: str | None = None
) -> None:
    repository_root = _repository_root()
    for entry in entries:
        path = cast(str, entry["path"])
        expected = cast(str, entry["sha256"])
        if revision is None and path in _SECURITY_HISTORICAL_TEST_PATHS:
            _assert_historical_test_record(repository_root, path, cast(str, entry["sha256"]))
            continue
        raw = (
            (repository_root / path).read_bytes()
            if revision is None
            else _git_bytes(repository_root, "cat-file", "blob", f"{revision}:{path}")
        )
        assert hashlib.sha256(raw).hexdigest().upper() == expected


def test_security_successor_preserves_inherited_test_authority_and_tamper_detection() -> None:
    _, manifest = _manifest()
    records = [
        entry
        for entry in _entries(manifest, "inherited_authorities")
        if entry["path"] in _SECURITY_HISTORICAL_TEST_PATHS
    ]
    assert records
    _assert_sha256_artifacts(records)
    for record in records:
        with pytest.raises(AssertionError, match="historical expected SHA-256"):
            _assert_sha256_artifacts([{**record, "sha256": "0" * 64}])


def _assert_expected_freeze_target(resolved_target: str, expected_target: str) -> None:
    assert resolved_target == expected_target


def _assert_pinned_freeze_records(manifest: dict[str, object]) -> None:
    assert manifest["accepted_product_baseline"] == {
        "commit": _PRODUCT_BASELINE,
        "subject": "fix: correct angle-column single bolt path",
        "commit_count": 95,
        "tracked_file_count": 584,
        "branch": "main",
    }
    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["expected_parent"] == _PRODUCT_BASELINE
    assert freeze["expected_commit_count"] == _FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _FREEZE_SUBJECT
    assert freeze["freeze_tag"] == _STAGE_3_7_TAG
    assert freeze["tag_type"] == "annotated"
    assert manifest["repository_identities"] == _EXPECTED_REPOSITORY_IDENTITIES
    assert manifest["supported_profile_assembly_matrix"] == _EXPECTED_MATRIX
    assert manifest["historical_api_contracts"] == ["3.5C-RC1", "3.5C-R2-RC1"]
    assert manifest["current_api_contracts"] == ["3.7A-RC1"]
    assert _canonical_sha256(manifest["engineering_fingerprints"]) == (_FINGERPRINT_BLOCK_SHA256)

    product = cast(dict[str, object], manifest["frozen_product"])
    assert product["future_angle_moment_topology"] == (
        "ANGLE_COLUMN_TWO_DIFFERENT_LEGS_MOMENT_BASE = NOT_IN_STAGE_3_7_SCOPE"
    )
    topologies = cast(dict[str, object], manifest["physical_bolt_topologies"])
    assert topologies["angle_single"] == [
        "BASE_ANGLE_VERTICAL_LEG",
        "SELECTED_ANGLE_COLUMN_LEG",
    ]
    assert topologies["angle_double_meaning"] == (
        "opposite broad faces of the same selected Angle-column leg"
    )
    assert topologies["angle_r1_negative_face"] == (
        "negative connector exterior to selected-leg opposite exterior along +T_C with "
        "exterior hardware only"
    )
    reference = cast(dict[str, object], manifest["member_reference_and_frame"])
    assert reference["angle_reference"] == "actual backend Angle centroid/member reference"
    assert reference["frontend_engineering_authority"] is False
    demand = cast(dict[str, object], manifest["component_demand_and_foundation"])
    assert cast(dict[str, object], demand["column"])["fraction"] == "1.0"
    assert cast(dict[str, object], demand["base_angle_system"])["system_fraction"] == "1.0"
    assert demand["foundation"] == (
        "physical action counted once with exact reference translation and generated moments"
    )
    material = cast(dict[str, object], manifest["material_and_resistance"])
    assert material["selected_wall_or_leg"] == "actual backend LW/CW/TT"
    connection_normal = cast(
        dict[str, object], manifest["compression_uplift_and_connection_normal"]
    )["connection_normal"]
    assert connection_normal == [
        "V_T is bolt-axis action",
        "no automatic bolt-axis tension resistance",
        "no automatic prying closure",
        "no unsupported complete Double branch split",
        "exact total foundation wrench retained",
    ]
    external = cast(dict[str, object], manifest["external_design_boundary"])
    assert external["concrete_capacity"] == external["anchor_capacity"] == "NOT_CALCULATED"
    assert manifest["no_production_change_declaration"] == {
        "backend_src_changed": False,
        "frontend_src_changed": False,
        "engineering_method_changed": False,
        "controlled_engineering_artifact_changed": False,
        "dependency_changed": False,
        "workflow_changed": False,
        "existing_freeze_tag_changed": False,
        "future_angle_moment_topology_started": False,
        "later_stage_started": False,
    }


def _resolve_stage_3_7_freeze(
    repository_root: Path,
    *,
    allow_tag: bool = True,
    allow_external_target: bool = True,
    supplied_target: str | None = None,
) -> _FreezeResolution:
    tag_ref = f"refs/tags/{_STAGE_3_7_TAG}"
    if allow_tag and _tag_is_available(repository_root, _STAGE_3_7_TAG):
        assert _git(repository_root, "cat-file", "-t", tag_ref) == "tag"
        return _FreezeResolution(_git(repository_root, "rev-parse", f"{tag_ref}^{{}}"), "tag")
    target = supplied_target
    if target is None:
        target = os.environ.get("STAGE_3_7_FREEZE_TARGET")
    if allow_external_target and target is not None:
        assert _object_is_available(repository_root, f"{target}^{{commit}}")
        resolved_target = _git(repository_root, "rev-parse", f"{target}^{{commit}}")
        _assert_expected_freeze_target(resolved_target, target)
        return _FreezeResolution(resolved_target, "object")
    return _FreezeResolution(None, "manifest_only")


def _assert_frozen_git_identities(repository_root: Path, revision: str) -> None:
    identities = _EXPECTED_REPOSITORY_IDENTITIES
    tree_expectations = {
        "backend/src": cast(str, identities["accepted_backend_src_tree"]),
        "frontend/src": cast(str, identities["accepted_frontend_src_tree"]),
        ".github/workflows": cast(str, identities["accepted_workflow_tree"]),
        "docs/engineering": cast(str, identities["accepted_engineering_tree"]),
        "backend/tests/golden": cast(str, identities["accepted_golden_tree"]),
        "backend/requirements": cast(str, identities["accepted_backend_requirements_tree"]),
    }
    for path, expected in tree_expectations.items():
        assert _git(repository_root, "rev-parse", f"{revision}:{path}") == expected
    for key in (
        "backend_pyproject",
        "backend_requirements_readme",
        "backend_requirements_lock",
        "frontend_package_json",
        "frontend_package_lock",
    ):
        record = cast(dict[str, str], identities[key])
        assert (
            _git(repository_root, "rev-parse", f"{revision}:{record['path']}") == record["git_blob"]
        )


def _assert_freeze_object(repository_root: Path, revision: str) -> None:
    assert _git(repository_root, "show", "-s", "--format=%s", revision) == _FREEZE_SUBJECT
    raw_commit = _git(repository_root, "cat-file", "-p", revision)
    parents = [
        line.removeprefix("parent ")
        for line in raw_commit.splitlines()
        if line.startswith("parent ")
    ]
    assert parents == [_PRODUCT_BASELINE]
    if not _is_shallow(repository_root):
        assert int(_git(repository_root, "rev-list", "--count", revision)) == _FREEZE_COMMIT_COUNT

    raw, manifest = _manifest_at_revision(repository_root, revision)
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    _assert_frozen_git_identities(repository_root, revision)
    _assert_sha256_artifacts(
        [
            *_entries(manifest, "controlled_stage_3_7_repository_artifacts"),
            *_entries(manifest, "inherited_authorities"),
        ],
        revision=revision,
    )


def test_stage_3_7_freeze_manifest_is_byte_exact_and_complete() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.7-column-base-shear-family-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.7"
    order = cast(dict[str, object], manifest["controlling_order"])
    assert order["sha256"] == _EXTERNAL_ORDER_HASHES["Stage 3.7 Freeze"]
    assert str(order["final_sentinel"]).endswith("DO NOT PROCEED IF THIS LINE IS MISSING")

    controlled = _entries(manifest, "controlled_stage_3_7_repository_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert len(controlled) == 4
    assert len(inherited) == 34
    assert len({cast(str, item["path"]) for item in [*controlled, *inherited]}) == 38
    _assert_sha256_artifacts([*controlled, *inherited])

    orders = _entries(manifest, "external_control_orders")
    actual_orders = {cast(str, item["revision"]): cast(str, item["sha256"]) for item in orders}
    assert actual_orders == _EXTERNAL_ORDER_HASHES


def test_stage_3_7_acceptance_chain_ci_owner_and_benchmarks_are_exact() -> None:
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

    ci = cast(dict[str, object], manifest["ci_evidence"])
    assert [cast(dict[str, object], ci[key])["run_number"] for key in ci if key != "provider"] == [
        89,
        90,
    ]
    assert all(
        cast(dict[str, object], ci[key])["jobs_green"]
        == cast(dict[str, object], ci[key])["jobs_total"]
        == 4
        for key in ("stage_3_7a", "stage_3_7a_r1")
    )
    owner = cast(dict[str, object], manifest["accepted_owner_evidence"])
    assert owner["status"] == "accepted"
    assert owner["acceptance_date"] == "2026-08-31"

    benchmark = cast(dict[str, object], manifest["benchmark_identity"])
    golden = json.loads(
        (repository_root / cast(str, benchmark["path"])).read_text(encoding="utf-8")
    )
    identifiers = [item["id"] for item in golden["benchmarks"]]
    assert (len(identifiers), identifiers[0], identifiers[-1]) == (
        benchmark["count"],
        benchmark["first"],
        benchmark["last"],
    )


def test_stage_3_7_existing_historical_tags_remain_exact_when_available() -> None:
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


def test_stage_3_7_freeze_resolves_tag_object_or_manifest_only_without_network() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    resolution = _resolve_stage_3_7_freeze(repository_root)
    expected_source = os.environ.get("STAGE_3_7_EXPECTED_RESOLUTION_SOURCE")
    if expected_source is not None:
        assert resolution.source == expected_source
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    assert resolution.source in {"tag", "object"}
    _assert_freeze_object(repository_root, resolution.revision)


def test_stage_3_7_freeze_explicit_object_mode_when_supplied() -> None:
    repository_root = _repository_root()
    supplied_target = os.environ.get("STAGE_3_7_FREEZE_TARGET")
    if supplied_target is None:
        assert _resolve_stage_3_7_freeze(
            repository_root, allow_tag=False, allow_external_target=False
        ) == _FreezeResolution(None, "manifest_only")
        return
    resolution = _resolve_stage_3_7_freeze(
        repository_root,
        allow_tag=False,
        supplied_target=supplied_target,
    )
    assert resolution == _FreezeResolution(supplied_target, "object")
    _assert_freeze_object(repository_root, supplied_target)


def test_stage_3_7_freeze_future_tagless_successor_never_substitutes_head() -> None:
    repository_root = _repository_root()
    resolution = _resolve_stage_3_7_freeze(
        repository_root,
        allow_tag=False,
        allow_external_target=False,
        supplied_target=None,
    )
    assert resolution == _FreezeResolution(None, "manifest_only")
    assert resolution.revision != _git(repository_root, "rev-parse", "HEAD")


def _tamper_pinned_record(manifest: dict[str, object], kind: str) -> None:
    if kind in {"backend", "frontend", "workflow"}:
        key = {
            "backend": "accepted_backend_src_tree",
            "frontend": "accepted_frontend_src_tree",
            "workflow": "accepted_workflow_tree",
        }[kind]
        cast(dict[str, object], manifest["repository_identities"])[key] = "0" * 40
    elif kind in {"package", "lock"}:
        key = "frontend_package_json" if kind == "package" else "frontend_package_lock"
        cast(dict[str, object], cast(dict[str, object], manifest["repository_identities"])[key])[
            "git_blob"
        ] = "0" * 40
    elif kind == "baseline":
        cast(dict[str, object], manifest["accepted_product_baseline"])["commit"] = "0" * 40
    elif kind == "matrix":
        cast(list[str], manifest["supported_profile_assembly_matrix"]).pop()
    elif kind == "single_topology":
        cast(dict[str, object], manifest["physical_bolt_topologies"])["angle_single"] = []
    elif kind == "double_topology":
        cast(dict[str, object], manifest["physical_bolt_topologies"])["angle_double_meaning"] = (
            "different legs"
        )
    elif kind == "future_moment":
        cast(dict[str, object], manifest["frozen_product"])["future_angle_moment_topology"] = (
            "INCLUDED"
        )
    elif kind == "centroid":
        cast(dict[str, object], manifest["member_reference_and_frame"])["angle_reference"] = (
            "selected leg"
        )
    elif kind == "r1_negative":
        cast(dict[str, object], manifest["physical_bolt_topologies"])["angle_r1_negative_face"] = (
            "positive-face path"
        )
    elif kind == "demand":
        demand = cast(dict[str, object], manifest["component_demand_and_foundation"])
        cast(dict[str, object], demand["column"])["fraction"] = "2.0"
    elif kind == "foundation":
        cast(dict[str, object], manifest["component_demand_and_foundation"])["foundation"] = (
            "counted twice"
        )
    elif kind == "material":
        cast(dict[str, object], manifest["material_and_resistance"])["selected_wall_or_leg"] = (
            "global axes"
        )
    elif kind == "connection_normal":
        boundary = cast(dict[str, object], manifest["compression_uplift_and_connection_normal"])
        cast(list[str], boundary["connection_normal"])[1] = "automatic tension resistance"
    elif kind == "external":
        cast(dict[str, object], manifest["external_design_boundary"])["anchor_capacity"] = (
            "CALCULATED"
        )
    elif kind == "fingerprint":
        fingerprints = cast(dict[str, object], manifest["engineering_fingerprints"])
        matrix = cast(dict[str, dict[str, str]], fingerprints["default_profile_assembly_matrix"])
        matrix["WIDE_FLANGE_I:SINGLE_BASE_ANGLE"]["engineering"] = "0" * 64
    else:
        raise AssertionError(f"Unsupported tamper kind: {kind}")


@pytest.mark.parametrize(
    "kind",
    [
        "backend",
        "frontend",
        "workflow",
        "package",
        "lock",
        "baseline",
        "matrix",
        "single_topology",
        "double_topology",
        "future_moment",
        "centroid",
        "r1_negative",
        "demand",
        "foundation",
        "material",
        "connection_normal",
        "external",
        "fingerprint",
    ],
)
def test_stage_3_7_freeze_rejects_pinned_record_tampering(kind: str) -> None:
    _, manifest = _manifest()
    tampered = deepcopy(manifest)
    _tamper_pinned_record(tampered, kind)
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered)


def test_stage_3_7_freeze_rejects_controlled_artifact_tampering() -> None:
    _, manifest = _manifest()
    controlled = _entries(deepcopy(manifest), "controlled_stage_3_7_repository_artifacts")
    controlled[0]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_sha256_artifacts([controlled[0]])


def test_stage_3_7_freeze_rejects_modified_manifest_bytes() -> None:
    raw, _ = _manifest()
    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")


def test_stage_3_7_freeze_rejects_wrong_supplied_historical_target() -> None:
    with pytest.raises(AssertionError):
        _resolve_stage_3_7_freeze(
            _repository_root(),
            allow_tag=False,
            supplied_target="0" * 40,
        )


def test_stage_3_7_freeze_rejects_wrong_tag_peeled_target() -> None:
    with pytest.raises(AssertionError):
        _assert_expected_freeze_target("1" * 40, "0" * 40)
