"""Successor-safe audit for the accepted Stage 4.1A W/I moment-splice family."""

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

_MANIFEST_PATH = "docs/governance/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F"
_FINGERPRINT_SHA256 = "2C21FAFDC3A706079A8C928516A59C771BBAECB72E6D50EAE84384A09C76FFC8"
_PRODUCT_BASELINE = "59713e53c522a6a301e19e458559986fb114d735"
_SLICE_5_BASELINE = "23813a5c2d015b74591e577fa95715950c34912c"
_TAG = "stage-4.1a-wi-major-axis-moment-splice-freeze"
_TAG_OBJECT = "a265ff394413d8fef16e7012c1de910bf3ece1b7"
_FREEZE_COMMIT = "cc9effad0691d083bb204c44ec3fb6e9dfb3671d"
# Exact snapshot at the frozen tag; only this aggregate register permits appends.
# The byte count and original digest bind every historical byte without requiring
# historical objects in a depth-one checkout or trusting successor HEAD as history.
_SOURCE_REGISTER = "docs/engineering/ENGINEERING_SOURCE_REGISTER.md"
_SOURCE_REGISTER_FROZEN_BYTES = 3742
_SOURCE_REGISTER_SHA256 = "D2F45B4EF8006FF471EBA511D976AB80CE6E663B652F2E38B303E52169D92C17"
_SUBJECT = "chore: freeze Stage 4.1A W/I moment splice baseline"
_COMMIT_COUNT = 99
_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "3c882a9f5877497816acb5592d423d441d7b93f2",
    "accepted_frontend_tree": "d1793de27c13cca41ce881827cf6e42ff4826324",
    "accepted_backend_src_tree": "70dca07ca9fac3bbc45b8363f0d5f21157a1bc52",
    "accepted_frontend_src_tree": "7deabca069f034e7f43f426ba31d7dca0c839419",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "3bcf35139e636ce052f6082a59b4748752e5edda",
    "accepted_golden_tree": "3098c9113af244d04a0930dcecc31e70bc061a9d",
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
    "stage-3.7-column-base-shear-family-freeze": (
        "cbce5bc3e6ab61b550b3848982d6493a32a56bdb",
        "b0a6ecdf03c88768ff6ab29e584a992231812bda",
    ),
}


class _Resolution(NamedTuple):
    revision: str | None
    source: Literal["tag", "object", "manifest_only"]


def _root() -> Path:
    return Path(__file__).parents[3]


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed governance queries
        ["git", *arguments],  # noqa: S607 - fixed governance queries
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_bytes(root: Path, *arguments: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed governance queries
        ["git", *arguments],  # noqa: S607 - fixed governance queries
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _tag_available(root: Path, tag: str) -> bool:
    return (
        subprocess.run(  # noqa: S603 - fixed governance query
            ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"],  # noqa: S607
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _object_available(root: Path, name: str) -> bool:
    return (
        subprocess.run(  # noqa: S603 - fixed governance query
            ["git", "cat-file", "-e", name],  # noqa: S607
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _is_shallow(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-shallow-repository") == "true"


def _manifest() -> tuple[bytes, dict[str, object]]:
    raw = (_root() / _MANIFEST_PATH).read_bytes()
    return raw, cast(dict[str, object], json.loads(raw))


def _manifest_at(root: Path, revision: str) -> tuple[bytes, dict[str, object]]:
    raw = _git_bytes(root, "cat-file", "blob", f"{revision}:{_MANIFEST_PATH}")
    return raw, cast(dict[str, object], json.loads(raw))


def _entries(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    value = manifest[key]
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return cast(list[dict[str, object]], value)


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def _assert_manifest_bytes(raw: bytes) -> None:
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256


def _assert_artifact_bytes(entry: dict[str, object], raw: bytes, *, successor: bool) -> None:
    expected = cast(str, entry["sha256"])
    if entry["path"] == _SOURCE_REGISTER:
        assert expected == _SOURCE_REGISTER_SHA256
        if successor:
            assert len(raw) >= _SOURCE_REGISTER_FROZEN_BYTES
            raw = raw[:_SOURCE_REGISTER_FROZEN_BYTES]
    assert hashlib.sha256(raw).hexdigest().upper() == expected


def _assert_artifacts(entries: list[dict[str, object]], *, revision: str | None = None) -> None:
    root = _root()
    for entry in entries:
        path = cast(str, entry["path"])
        if revision is None and path in _SECURITY_HISTORICAL_TEST_PATHS:
            _assert_historical_test_record(root, path, cast(str, entry["sha256"]))
            continue
        raw = (
            (root / path).read_bytes()
            if revision is None
            else _git_bytes(root, "cat-file", "blob", f"{revision}:{path}")
        )
        _assert_artifact_bytes(entry, raw, successor=revision is None)


def test_security_successor_preserves_inherited_test_authority_and_tamper_detection() -> None:
    _, manifest = _manifest()
    records = [
        entry
        for entry in _entries(manifest, "inherited_authorities")
        if entry["path"] in _SECURITY_HISTORICAL_TEST_PATHS
    ]
    assert records
    _assert_artifacts(records)
    for record in records:
        with pytest.raises(AssertionError, match="historical expected SHA-256"):
            _assert_artifacts([{**record, "sha256": "0" * 64}])


def _assert_target(actual: str, expected: str) -> None:
    assert actual == expected


def _assert_contract(manifest: dict[str, object]) -> None:
    assert manifest["accepted_product_baseline"] == {
        "commit": _PRODUCT_BASELINE,
        "subject": "feat: add W/I major-axis moment splice connection",
        "commit_count": 98,
        "tracked_file_count": 611,
        "branch": "main",
    }
    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze == {
        "identity": "SELF",
        "expected_parent": _PRODUCT_BASELINE,
        "expected_subject": _SUBJECT,
        "expected_commit_count": _COMMIT_COUNT,
        "tag": _TAG,
        "tag_type": "annotated",
        "tag_annotation": "Freeze accepted Stage 4.1A W/I Major-Axis Moment Splice baseline",
    }
    assert manifest["repository_identities"] == _REPOSITORY_IDENTITIES
    assert _canonical_sha256(manifest["engineering_fingerprints"]) == _FINGERPRINT_SHA256

    product = cast(dict[str, object], manifest["frozen_product"])
    assert product["product_id"] == "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
    assert product["contract"] == "4.1A-RC1"
    assert product["supported_profiles"] == ["WIDE_FLANGE_I"]
    assert product["excluded_successor"] == "Stage 4.1B Channel Moment Splice"
    slice_5 = cast(dict[str, object], manifest["slice_5_component_decomposition"])
    assert slice_5["method"] == "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1"
    assert slice_5["web_moment_participation"] == "REQUIRED"
    assert slice_5["local_flange_region_moments"] == "RETAINED"
    assert slice_5["m_over_z"] == "REFERENCE_ONLY_NOT_SOLE_CONTROLLING_DEMAND"
    topology = cast(dict[str, object], manifest["physical_topology"])
    assert topology["total_frp_splice_plates"] == 8
    assert topology["outer_only_flange_splice"] == "PROHIBITED"
    bolt_path = cast(dict[str, object], manifest["flange_bolt_path"])
    assert bolt_path["ordered_layers"] == [
        "OUTER_FLANGE_SPLICE_PLATE",
        "BEAM_FLANGE",
        "CORRESPONDING_INNER_FLANGE_SPLICE_PLATE",
    ]
    assert bolt_path["continuous_shank"] is True
    assert bolt_path["physical_shear_planes"] == 2
    assert bolt_path["duplicate_physical_bolt"] is False
    web = cast(dict[str, object], manifest["web_subsystem"])
    assert "Slice 5 web local/free major-axis moment" in cast(list[str], web["receives"])
    branch = cast(dict[str, object], manifest["flange_branch"])
    assert branch["method"] == "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
    assert branch["discarded_residual_moment"] is False
    inner = cast(dict[str, object], manifest["inner_strip_allocation"])
    assert inner["rule"] == "F_i,+ = F_i/2 and F_i,- = F_i/2"
    assert "Channel" in cast(list[str], inner["not_authority_for"])
    sublayer = cast(dict[str, object], manifest["beam_flange_face_transfer"])
    assert sublayer["method"] == "RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1"
    assert sublayer["outer_effective_thickness"] == sublayer["inner_effective_thickness"] == "t_f/2"
    assert sublayer["physical_delamination_planes"] is False
    bolt = cast(dict[str, object], manifest["unequal_two_plane_bolt"])
    assert bolt["method"] == "RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1"
    assert bolt["equal_plane_assumption"] is False
    assert bolt["blind_two_times_capacity"] is False
    local = cast(dict[str, object], manifest["flange_body_and_local_checks"])
    assert local["new_strength_equation"] is False
    boundary = cast(dict[str, object], manifest["bolt_axis_and_prying_boundary"])
    assert boundary["authoritative_bolt_axis_force"] == "0"
    assert boundary["invented_numerical_prying_force"] is False
    assert manifest["ordinary_unqualified_pass"] == "PROHIBITED"  # noqa: S105
    assert cast(list[str], manifest["result_precedence"])[-1].endswith(
        "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"
    )
    qualification = cast(dict[str, object], manifest["qualification"])
    assert qualification["RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED"] is True
    assert qualification["WI_MOMENT_SPLICE_CONNECTION_QUALIFICATION"] == "REQUIRED_2_3_2"
    assert qualification["MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION"] == "NOT_EVALUATED"
    assert qualification["MOMENT_ROTATION_CAPACITY"] == "NOT_EVALUATED"
    assert qualification["FULL_STRENGTH_CLASSIFICATION"] == "NOT_EVALUATED"
    disclaimer = cast(dict[str, object], manifest["disclaimer"])
    assert disclaimer["id"] == "WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1"
    preview = cast(dict[str, object], manifest["preview_and_design"])
    assert preview["preview_resistance_calls"] == 0
    assert preview["design_check"] == "EXPLICIT_USER_ACTION_ONLY"
    visualization = cast(dict[str, object], manifest["visualization_and_request_state"])
    assert visualization["geometry_and_endpoints"] == "BACKEND_AUTHORITATIVE"
    assert visualization["blank_workspace"] is False
    source = cast(dict[str, object], manifest["source_pending_behavior"])
    assert cast(str, source["astm_f593_numerical_bolt_resistance"]).startswith("SOURCE_PENDING")
    assert source["invented_strength"] is False
    assert manifest["no_production_change_declaration"] == {
        "production_source_changes": 0,
        "engineering_method_changes": 0,
        "controlled_engineering_artifact_changes": 0,
        "dependency_changes": 0,
        "workflow_changes": 0,
        "freeze_tag_changes": 0,
        "governance_and_test_only": True,
    }


def _resolve(
    root: Path,
    *,
    allow_tag: bool = True,
    allow_object: bool = True,
    supplied_target: str | None = None,
) -> _Resolution:
    tag_ref = f"refs/tags/{_TAG}"
    if allow_tag and _tag_available(root, _TAG):
        assert _git(root, "cat-file", "-t", tag_ref) == "tag"
        assert _git(root, "rev-parse", tag_ref) == _TAG_OBJECT
        revision = _git(root, "rev-parse", f"{tag_ref}^{{}}")
        _assert_target(revision, _FREEZE_COMMIT)
        return _Resolution(revision, "tag")
    target = supplied_target or os.environ.get("STAGE_4_1A_FREEZE_TARGET")
    if allow_object and target is not None:
        assert _object_available(root, f"{target}^{{commit}}")
        resolved = _git(root, "rev-parse", f"{target}^{{commit}}")
        _assert_target(resolved, target)
        return _Resolution(resolved, "object")
    return _Resolution(None, "manifest_only")


def _assert_source_identities(root: Path, revision: str) -> None:
    trees = {
        "backend/src": "accepted_backend_src_tree",
        "frontend/src": "accepted_frontend_src_tree",
        ".github/workflows": "accepted_workflow_tree",
        "docs/engineering": "accepted_engineering_tree",
        "backend/tests/golden": "accepted_golden_tree",
        "backend/requirements": "accepted_backend_requirements_tree",
    }
    for path, key in trees.items():
        assert _git(root, "rev-parse", f"{revision}:{path}") == _REPOSITORY_IDENTITIES[key]
    for key in (
        "backend_pyproject",
        "backend_requirements_readme",
        "backend_requirements_lock",
        "frontend_package_json",
        "frontend_package_lock",
    ):
        record = cast(dict[str, str], _REPOSITORY_IDENTITIES[key])
        assert _git(root, "rev-parse", f"{revision}:{record['path']}") == record["git_blob"]


def _assert_freeze_object(root: Path, revision: str) -> None:
    _assert_target(revision, _FREEZE_COMMIT)
    assert _git(root, "show", "-s", "--format=%s", revision) == _SUBJECT
    raw_commit = _git(root, "cat-file", "-p", revision)
    parents = [line[7:] for line in raw_commit.splitlines() if line.startswith("parent ")]
    assert parents == [_PRODUCT_BASELINE]
    if not _is_shallow(root):
        assert int(_git(root, "rev-list", "--count", revision)) == _COMMIT_COUNT
    raw, manifest = _manifest_at(root, revision)
    _assert_manifest_bytes(raw)
    _assert_contract(manifest)
    _assert_source_identities(root, revision)
    _assert_artifacts(
        [
            *_entries(manifest, "controlled_stage_4_1a_repository_artifacts"),
            *_entries(manifest, "controlled_slice_5_repository_artifacts"),
            *_entries(manifest, "inherited_authorities"),
        ],
        revision=revision,
    )


def test_stage_4_1a_freeze_manifest_is_byte_exact_complete_and_parseable() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_contract(manifest)
    assert manifest["schema"] == "frp-master-connection-family-freeze-manifest"
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "4.1A"
    order = cast(dict[str, object], manifest["controlling_order"])
    assert order["sha256"] == "0646F456A035C0A2C09492AFF4A59B4A4A8D8E665B346F1DC7B16443D79A3290"
    assert str(order["sentinel"]).endswith("DO NOT PROCEED IF THIS LINE IS MISSING")
    stage = _entries(manifest, "controlled_stage_4_1a_repository_artifacts")
    slice_5 = _entries(manifest, "controlled_slice_5_repository_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert (len(stage), len(slice_5), len(inherited)) == (4, 4, 38)
    assert len({cast(str, item["path"]) for item in [*stage, *slice_5, *inherited]}) == 46
    _assert_artifacts([*stage, *slice_5, *inherited])


def test_stage_4_1a_chain_ci_owner_and_golden_ranges_are_exact() -> None:
    root = _root()
    _, manifest = _manifest()
    chain = cast(list[dict[str, object]], manifest["acceptance_chain"])
    assert [item["commit"] for item in chain] == [_SLICE_5_BASELINE, _PRODUCT_BASELINE]
    assert chain[1]["parent"] == _SLICE_5_BASELINE
    if not _is_shallow(root):
        assert _git(root, "rev-parse", f"{_PRODUCT_BASELINE}^") == _SLICE_5_BASELINE
    ci = cast(dict[str, object], manifest["ci_evidence"])
    assert cast(dict[str, object], ci["calculation_slice_5"])["run_number"] == 92
    assert cast(dict[str, object], ci["stage_4_1a"])["run_number"] == 93
    assert ci["governance_freeze_commit"] == "PENDING_DIRECT_EVIDENCE_AFTER_PUSH"
    owner = cast(dict[str, object], manifest["accepted_owner_evidence"])
    assert owner["status"] == "COMPLETE"
    benchmark = cast(dict[str, object], manifest["benchmark_identity"])
    for key, path in (
        (
            "stage_4_1a",
            "backend/tests/golden/stage_4_1a_wi_major_axis_moment_splice_golden_benchmarks_rc1.json",
        ),
        (
            "calculation_slice_5",
            "backend/tests/golden/calculation_slice_5_wi_moment_component_resultants_golden_benchmarks_rc1.json",
        ),
    ):
        record = cast(dict[str, object], benchmark[key])
        golden = json.loads((root / path).read_text(encoding="utf-8"))
        ids = [item["id"] for item in golden["benchmarks"]]
        assert (len(ids), ids[0], ids[-1]) == (record["count"], record["first"], record["last"])


def test_stage_4_1a_existing_tags_are_exact_when_available() -> None:
    root = _root()
    _, manifest = _manifest()
    entries = _entries(manifest, "existing_immutable_freezes")
    assert {cast(str, item["tag"]) for item in entries} == set(_EXISTING_TAGS)
    for item in entries:
        tag = cast(str, item["tag"])
        tag_object, peeled = _EXISTING_TAGS[tag]
        assert (item["tag_object"], item["peeled_target"]) == (tag_object, peeled)
        if _tag_available(root, tag):
            assert _git(root, "cat-file", "-t", f"refs/tags/{tag}") == "tag"
            assert _git(root, "rev-parse", f"refs/tags/{tag}") == tag_object
            assert _git(root, "rev-parse", f"refs/tags/{tag}^{{}}") == peeled


def test_stage_4_1a_resolves_tag_object_or_manifest_only_without_network() -> None:
    root = _root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_contract(manifest)
    resolution = _resolve(root)
    expected = os.environ.get("STAGE_4_1A_EXPECTED_RESOLUTION_SOURCE")
    if expected is not None:
        assert resolution.source == expected
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    _assert_freeze_object(root, resolution.revision)


def test_stage_4_1a_explicit_object_mode_when_supplied() -> None:
    root = _root()
    supplied = os.environ.get("STAGE_4_1A_FREEZE_TARGET")
    if supplied is None:
        assert _resolve(root, allow_tag=False, allow_object=False) == _Resolution(
            None, "manifest_only"
        )
        return
    resolution = _resolve(root, allow_tag=False, supplied_target=supplied)
    assert resolution == _Resolution(supplied, "object")
    _assert_freeze_object(root, supplied)


def test_stage_4_1a_tagless_successor_never_substitutes_head() -> None:
    root = _root()
    resolution = _resolve(root, allow_tag=False, allow_object=False)
    assert resolution == _Resolution(None, "manifest_only")
    assert resolution.revision != _git(root, "rev-parse", "HEAD")


def _tamper(manifest: dict[str, object], kind: str) -> None:
    identities = cast(dict[str, object], manifest["repository_identities"])
    if kind in {"backend", "frontend", "workflow", "engineering", "golden"}:
        key = {
            "backend": "accepted_backend_src_tree",
            "frontend": "accepted_frontend_src_tree",
            "workflow": "accepted_workflow_tree",
            "engineering": "accepted_engineering_tree",
            "golden": "accepted_golden_tree",
        }[kind]
        identities[key] = "0" * 40
    elif kind in {"package", "lock", "backend_lock"}:
        key = {
            "package": "frontend_package_json",
            "lock": "frontend_package_lock",
            "backend_lock": "backend_requirements_lock",
        }[kind]
        cast(dict[str, object], identities[key])["git_blob"] = "0" * 40
    elif kind == "baseline":
        cast(dict[str, object], manifest["accepted_product_baseline"])["commit"] = "0" * 40
    elif kind == "scope":
        cast(dict[str, object], manifest["frozen_product"])["supported_profiles"] = ["CHANNEL"]
    elif kind == "topology":
        cast(dict[str, object], manifest["physical_topology"])["total_frp_splice_plates"] = 2
    elif kind == "bolt_path":
        cast(dict[str, object], manifest["flange_bolt_path"])["ordered_layers"] = []
    elif kind == "m_over_z":
        cast(dict[str, object], manifest["slice_5_component_decomposition"])["m_over_z"] = "SOLE"
    elif kind == "web_moment":
        cast(dict[str, object], manifest["web_subsystem"])["receives"] = []
    elif kind == "branch":
        cast(dict[str, object], manifest["flange_branch"])["discarded_residual_moment"] = True
    elif kind == "symmetry":
        cast(dict[str, object], manifest["inner_strip_allocation"])["not_authority_for"] = []
    elif kind == "sublayer":
        cast(dict[str, object], manifest["beam_flange_face_transfer"])[
            "physical_delamination_planes"
        ] = True
    elif kind == "unequal_planes":
        cast(dict[str, object], manifest["unequal_two_plane_bolt"])["equal_plane_assumption"] = True
    elif kind == "blind_capacity":
        cast(dict[str, object], manifest["unequal_two_plane_bolt"])["blind_two_times_capacity"] = (
            True
        )
    elif kind == "prying":
        cast(dict[str, object], manifest["bolt_axis_and_prying_boundary"])[
            "invented_numerical_prying_force"
        ] = True
    elif kind == "ordinary_pass":
        manifest["ordinary_unqualified_pass"] = "ALLOWED"  # noqa: S105
    elif kind == "status":
        cast(list[str], manifest["result_precedence"])[-1] = "PASS"
    elif kind == "qualification":
        cast(dict[str, object], manifest["qualification"])[
            "WI_MOMENT_SPLICE_CONNECTION_QUALIFICATION"
        ] = "NONE"
    elif kind == "f593":
        cast(dict[str, object], manifest["source_pending_behavior"])["invented_strength"] = True
    elif kind == "fingerprint":
        cast(dict[str, object], manifest["engineering_fingerprints"])["default_engineering"] = (
            "0" * 64
        )
    else:
        raise AssertionError(f"unsupported tamper: {kind}")


@pytest.mark.parametrize(
    "kind",
    [
        "backend",
        "frontend",
        "workflow",
        "engineering",
        "golden",
        "package",
        "lock",
        "backend_lock",
        "baseline",
        "scope",
        "topology",
        "bolt_path",
        "m_over_z",
        "web_moment",
        "branch",
        "symmetry",
        "sublayer",
        "unequal_planes",
        "blind_capacity",
        "prying",
        "ordinary_pass",
        "status",
        "qualification",
        "f593",
        "fingerprint",
    ],
)
def test_stage_4_1a_rejects_pinned_record_tampering(kind: str) -> None:
    _, manifest = _manifest()
    changed = deepcopy(manifest)
    _tamper(changed, kind)
    with pytest.raises(AssertionError):
        _assert_contract(changed)


def test_stage_4_1a_rejects_controlled_artifact_tampering() -> None:
    _, manifest = _manifest()
    entries = _entries(deepcopy(manifest), "controlled_stage_4_1a_repository_artifacts")
    entries[0]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_artifacts([entries[0]])


def _source_register_entry() -> dict[str, object]:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    return next(
        entry
        for entry in _entries(manifest, "inherited_authorities")
        if entry["path"] == _SOURCE_REGISTER
    )


def test_stage_4_1a_register_snapshot_allows_only_successor_appends() -> None:
    entry = _source_register_entry()
    current = (_root() / _SOURCE_REGISTER).read_bytes()
    frozen = current[:_SOURCE_REGISTER_FROZEN_BYTES]
    _assert_artifact_bytes(entry, frozen, successor=False)
    _assert_artifact_bytes(entry, current, successor=True)
    _assert_artifact_bytes(entry, current + b"\nFuture source entry.\n", successor=True)
    # A frozen Git object may not contain even an append: it remains byte-exact.
    with pytest.raises(AssertionError):
        _assert_artifact_bytes(entry, frozen + b"\nFuture source entry.\n", successor=False)


@pytest.mark.parametrize("successor", [False, True])
@pytest.mark.parametrize("change", ["first_byte", "last_byte", "truncated", "line_endings"])
def test_stage_4_1a_rejects_changed_historical_register_content(
    successor: bool, change: str
) -> None:
    entry = _source_register_entry()
    frozen = (_root() / _SOURCE_REGISTER).read_bytes()[:_SOURCE_REGISTER_FROZEN_BYTES]
    if change == "first_byte":
        changed = bytes([frozen[0] ^ 1]) + frozen[1:]
    elif change == "last_byte":
        changed = frozen[:-1] + bytes([frozen[-1] ^ 1])
    elif change == "truncated":
        changed = frozen[:-1]
    else:
        changed = frozen.replace(b"\n", b"\r\n")
    with pytest.raises(AssertionError):
        _assert_artifact_bytes(entry, changed, successor=successor)


def test_stage_4_1a_rejects_register_hash_replacement() -> None:
    entry = dict(_source_register_entry())
    changed = b"Replacement historical source data"
    entry["sha256"] = hashlib.sha256(changed).hexdigest().upper()
    with pytest.raises(AssertionError):
        _assert_artifact_bytes(entry, changed, successor=False)


def test_stage_4_1a_other_artifacts_still_reject_appends() -> None:
    _, manifest = _manifest()
    entry = _entries(manifest, "controlled_stage_4_1a_repository_artifacts")[0]
    raw = (_root() / cast(str, entry["path"])).read_bytes()
    with pytest.raises(AssertionError):
        _assert_artifact_bytes(entry, raw + b"\nUnauthorized append.\n", successor=True)


def test_stage_4_1a_rejects_modified_manifest_bytes() -> None:
    raw, _ = _manifest()
    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")


def test_stage_4_1a_rejects_wrong_supplied_object() -> None:
    with pytest.raises(AssertionError):
        _resolve(_root(), allow_tag=False, supplied_target="0" * 40)


def test_stage_4_1a_rejects_wrong_tag_peeled_target() -> None:
    with pytest.raises(AssertionError):
        _assert_target("1" * 40, "0" * 40)
