"""Successor-safe audit for the accepted Stage 3.6 W/I web-splice family."""

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

_MANIFEST_RELATIVE_PATH = "docs/governance/STAGE_3_6_WI_WEB_SPLICE_FAMILY_FREEZE_MANIFEST.json"
_MANIFEST_SHA256 = "58AA05F545984EAAC0EDED666B4BA086BA05ADE40E59C39D3B7821BFFEB60658"
_PRODUCT_BASELINE = "5f77abd0eeaf61718756e9962ae3a5a67d6db528"
_STAGE_3_6_TAG = "stage-3.6-wi-web-splice-family-freeze"
_FREEZE_SUBJECT = "chore: freeze Stage 3.6 W/I web-splice family baseline"
_FREEZE_COMMIT_COUNT = 93
_EXPECTED_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "43d0a0dedd9f46ee179329037f811fb0196bd8ee",
    "accepted_frontend_tree": "f10468b8efb111702fd72cc816595510963f8b22",
    "accepted_backend_src_tree": "f75a72280ed8a2ea23cc67de376f5f4474b003a8",
    "accepted_frontend_src_tree": "35d39175e9d781dd723e4900f516c8f00e3ced3d",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "1544f3841c1c0e0e903f992032a3a392f7e05da5",
    "accepted_golden_tree": "a6ba22d044d2d7821078888569c6c312211428cf",
    "accepted_backend_requirements_tree": "d8e1a9f1c2c89a4e50a181db1997c52b3c9bdf58",
    "backend_pyproject": {
        "path": "backend/pyproject.toml",
        "git_blob": "9caa35e74d01bb040369b72fe19294ba6072a786",
        "sha256": "39BEA635FCE709607E1A4AE11D8B31829DFD07B4CADE332E030486BE1456A116",
    },
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
    "stage-3.4-multi-member-tee-family-freeze": (
        "282724c1fe2fbbeea9f742921aba5996028fd60b",
        "2303ec713d6d038b935e076b909c3b639ced0e09",
    ),
    "stage-3.5-concrete-support-shear-family-freeze": (
        "7d9eaa40aa43f29e52fbae78b40057b31eaa8af8",
        "7bb83e5c8814781419c0789b7428bd46572d514c",
    ),
}
_ACCEPTANCE_CHAIN = [
    (
        "80df7524417c752ab3c0f6194348e72aff40767a",
        "feat: add symmetric double web splice connection",
    ),
    (
        "a93aa5d127a51dc81a6c7cd108af15c44d59ff9f",
        "feat: add Chapter 7 plate strength engine",
    ),
    (_PRODUCT_BASELINE, "feat: complete web-splice resistance with rational body interaction"),
]
_EXTERNAL_ORDER_HASHES = {
    "Stage 3.6A": "439AC078467896488B114116385693C3B358848820941C446226AA4834B2520F",
    "Calculation Slice 4": ("B8D74C87C3CCACEC886C5723395EC2D43FEF5197BA6ED34C39FBDBBCFB801D0F"),
    "Stage 3.6B RC2": ("AF801B95EBDE251D4436AFF95027FA7FBD26B35DD077FB095E7B46CE9D989471"),
    "Stage 3.6 Freeze": ("B3D43B7D492A4CD538029EEFD59CC0B86FF318C18B82842464E59E6B89AE8E69"),
}
_EXPECTED_FINGERPRINTS = {
    "3.6A-RC1": {
        "canonical_input": "f2e8b090435e716f952ab6d9dee2a32922f95f9ebd5db854a781724d6a936f88",
        "connector_geometry": ("7ffab47c7069981b876500a013ff01a2ac3decb56e99fa3233d24c5f5002b09c"),
        "engineering": "f2e8b090435e716f952ab6d9dee2a32922f95f9ebd5db854a781724d6a936f88",
        "application": "cc7b920831ddff015aaefe4bd7f882bc3528b61bcf6c977b77a1a1d94944be93",
    },
    "3.6B-RC2": {
        "canonical_input": "020e33b3aea740177196cf1b06d16f13e939817047002a5451efb05253b4794b",
        "connector_geometry": ("7ffab47c7069981b876500a013ff01a2ac3decb56e99fa3233d24c5f5002b09c"),
        "engineering": "020e33b3aea740177196cf1b06d16f13e939817047002a5451efb05253b4794b",
        "application": "a505b2613bcaeb1377417f054432d101b88504be189d7cc43178e11fbaf0015d",
        "clear_body_plan": ("f3126484605c1b6c3d16c221191d782dcf5df01891534183b75c241dd6c78bf9"),
        "default_design_result": (
            "fa966c62efe2ffd0e257215eeec8c2bf49e5bb59803ab5e2d06acaa37a7d2e0a"
        ),
        "default_body_result": ("cb81228bc254a3412586627bc6f04c7b01510bfccec651136f8f72ed2fc509ff"),
    },
}
_EXPECTED_LIMITATIONS = [
    "WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE=NOT_EVALUATED",
    (
        "No bolt-tension distribution, pull-through, prying, or automatic combined bolt "
        "tension/shear is authorized for Minor shear."
    ),
    "WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER=NOT_AUTHORIZED_IN_RC1",
    (
        "Flange splice, single-sided web splice, slip-critical behavior, unequal beams, "
        "and non-W/I expansion are outside the frozen scope."
    ),
    (
        "ASTM F593 nominal shear strength remains source pending unless existing explicit "
        "verified/custom authority supplies it."
    ),
    "No unqualified prescriptive PASS is allowed.",
]


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
    baseline = cast(dict[str, object], manifest["accepted_product_baseline"])
    assert baseline == {
        "commit": _PRODUCT_BASELINE,
        "subject": "feat: complete web-splice resistance with rational body interaction",
        "commit_count": 92,
        "tracked_file_count": 571,
        "branch": "main",
    }
    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["expected_commit_count"] == _FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _FREEZE_SUBJECT
    assert freeze["freeze_tag"] == _STAGE_3_6_TAG
    assert freeze["tag_type"] == "annotated"
    assert manifest["repository_identities"] == _EXPECTED_REPOSITORY_IDENTITIES
    assert manifest["historical_api_contracts"] == ["3.6A-RC1"]
    assert manifest["current_api_contracts"] == ["3.6B-RC2"]
    assert manifest["engineering_fingerprints"] == _EXPECTED_FINGERPRINTS
    assert manifest["deliberate_limitations"] == _EXPECTED_LIMITATIONS

    product = cast(dict[str, object], manifest["frozen_product"])
    assert product["channel_exclusion"] == ("CHANNEL_WEB_SPLICE = NOT_IN_STAGE_3_6_FROZEN_SCOPE")
    assert "offset from its web plane" in cast(str, product["channel_reason"])
    rational = cast(dict[str, object], manifest["rational_body_method"])
    assert rational["method_id"] == (
        "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1"
    )
    assert rational["panel_id"] == "RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1"
    assert rational["disclaimer_id"] == ("WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1")
    assert "not prescribed directly by ASCE/SEI 74-23" in cast(str, rational["disclaimer_meaning"])
    double_shear = cast(dict[str, object], manifest["physical_double_shear_contract"])
    assert "SOURCE_DATA_PENDING" in cast(str, double_shear["fastener_source_boundary"])
    assert manifest["result_precedence"] == [
        "invalid geometry or request -> invalid/rejected",
        "supported local FRP, physical double-shear, or rational body numerical failure -> FAIL",
        "required unavailable, source-pending, or Minor response -> NOT_EVALUATED",
        (
            "all required supported in-plane checks pass with rational review/qualification "
            "only -> PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"
        ),
        "ordinary unqualified PASS is prohibited",
    ]
    declaration = cast(dict[str, bool], manifest["no_production_change_declaration"])
    assert declaration == {
        "backend_src_changed": False,
        "frontend_src_changed": False,
        "calculation_method_changed": False,
        "controlled_engineering_artifact_changed": False,
        "dependency_changed": False,
        "workflow_changed": False,
        "existing_freeze_tag_changed": False,
        "channel_support_started": False,
        "later_stage_started": False,
    }


def _resolve_stage_3_6_freeze(
    repository_root: Path,
    *,
    allow_tag: bool = True,
    allow_external_target: bool = True,
    supplied_target: str | None = None,
) -> _FreezeResolution:
    tag_ref = f"refs/tags/{_STAGE_3_6_TAG}"
    if allow_tag and _tag_is_available(repository_root, _STAGE_3_6_TAG):
        assert _git(repository_root, "cat-file", "-t", tag_ref) == "tag"
        return _FreezeResolution(_git(repository_root, "rev-parse", f"{tag_ref}^{{}}"), "tag")
    target = supplied_target
    if target is None:
        target = os.environ.get("STAGE_3_6_FREEZE_TARGET")
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
    for key in ("backend_pyproject", "frontend_package_json", "frontend_package_lock"):
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
            *_entries(manifest, "controlled_stage_3_6_repository_artifacts"),
            *_entries(manifest, "inherited_authorities"),
        ],
        revision=revision,
    )


def test_stage_3_6_freeze_manifest_is_byte_exact_and_complete() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.6-wi-web-splice-family-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.6"
    order = cast(dict[str, object], manifest["controlling_order"])
    assert order["sha256"] == _EXTERNAL_ORDER_HASHES["Stage 3.6 Freeze"]
    assert str(order["final_sentinel"]).endswith("DO NOT PROCEED IF THIS LINE IS MISSING")

    controlled = _entries(manifest, "controlled_stage_3_6_repository_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert len(controlled) == 12
    assert len(inherited) == 38
    assert len({cast(str, item["path"]) for item in [*controlled, *inherited]}) == 50
    _assert_sha256_artifacts([*controlled, *inherited])

    orders = _entries(manifest, "external_control_orders")
    actual_orders = {cast(str, item["revision"]): cast(str, item["sha256"]) for item in orders}
    assert actual_orders == _EXTERNAL_ORDER_HASHES


def test_stage_3_6_acceptance_chain_ci_owner_and_benchmarks_are_exact() -> None:
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
    assert [
        cast(dict[str, object], ci[key])["run_number"]
        for key in ("stage_3_6a", "calculation_slice_4", "stage_3_6b_rc2")
    ] == [85, 86, 87]
    assert all(
        cast(dict[str, object], ci[key])["jobs_green"]
        == cast(dict[str, object], ci[key])["jobs_total"]
        == 4
        for key in ("stage_3_6a", "calculation_slice_4", "stage_3_6b_rc2")
    )
    owner = cast(dict[str, object], manifest["accepted_owner_evidence"])
    assert owner["status"] == "accepted"
    assert owner["acceptance_date"] == "2026-08-30"

    benchmark_paths = {
        "stage_3_6a": (
            "backend/tests/golden/stage_3_6a_symmetric_double_web_splice_golden_benchmarks_rc1.json"
        ),
        "calculation_slice_4": (
            "backend/tests/golden/"
            "calculation_slice_4_chapter_7_plate_strength_engine_golden_benchmarks_rc1.json"
        ),
        "stage_3_6b_rc2": (
            "backend/tests/golden/"
            "stage_3_6b_web_splice_resistance_authority_expansion_golden_benchmarks_rc2.json"
        ),
    }
    expected = cast(dict[str, dict[str, object]], manifest["benchmark_identities"])
    for key, path in benchmark_paths.items():
        golden = json.loads((repository_root / path).read_text(encoding="utf-8"))
        ids = [item["id"] for item in golden["benchmarks"]]
        assert (len(ids), ids[0], ids[-1]) == (
            expected[key]["count"],
            expected[key]["first"],
            expected[key]["last"],
        )


def test_stage_3_6_existing_historical_tags_remain_exact_when_available() -> None:
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


def test_stage_3_6_freeze_resolves_tag_object_or_manifest_only_without_network() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    resolution = _resolve_stage_3_6_freeze(repository_root)
    expected_source = os.environ.get("STAGE_3_6_EXPECTED_RESOLUTION_SOURCE")
    if expected_source is not None:
        assert resolution.source == expected_source
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    assert resolution.source in {"tag", "object"}
    _assert_freeze_object(repository_root, resolution.revision)


def test_stage_3_6_freeze_explicit_object_mode_when_supplied() -> None:
    repository_root = _repository_root()
    supplied_target = os.environ.get("STAGE_3_6_FREEZE_TARGET")
    if supplied_target is None:
        assert _resolve_stage_3_6_freeze(
            repository_root, allow_tag=False, allow_external_target=False
        ) == _FreezeResolution(None, "manifest_only")
        return
    resolution = _resolve_stage_3_6_freeze(
        repository_root,
        allow_tag=False,
        supplied_target=supplied_target,
    )
    assert resolution == _FreezeResolution(supplied_target, "object")
    _assert_freeze_object(repository_root, supplied_target)


def test_stage_3_6_freeze_future_tagless_successor_never_substitutes_head() -> None:
    repository_root = _repository_root()
    resolution = _resolve_stage_3_6_freeze(
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
        cast(
            dict[str, object],
            cast(dict[str, object], manifest["repository_identities"])[key],
        )["git_blob"] = "0" * 40
    elif kind == "baseline":
        cast(dict[str, object], manifest["accepted_product_baseline"])["commit"] = "0" * 40
    elif kind in {"method", "panel", "disclaimer_id", "disclaimer_meaning"}:
        key = {
            "method": "method_id",
            "panel": "panel_id",
            "disclaimer_id": "disclaimer_id",
            "disclaimer_meaning": "disclaimer_meaning",
        }[kind]
        cast(dict[str, object], manifest["rational_body_method"])[key] = "TAMPERED"
    elif kind == "fastener":
        cast(dict[str, object], manifest["physical_double_shear_contract"])[
            "fastener_source_boundary"
        ] = "F593_ASSUMED"
    elif kind == "minor":
        cast(list[str], manifest["deliberate_limitations"])[0] = "MINOR_EVALUATED"
    elif kind == "moment":
        cast(list[str], manifest["deliberate_limitations"])[2] = "MOMENT_AUTHORIZED"
    elif kind == "channel":
        cast(dict[str, object], manifest["frozen_product"])["channel_exclusion"] = (
            "CHANNEL_WEB_SPLICE = INCLUDED"
        )
    elif kind == "fingerprint":
        cast(dict[str, dict[str, str]], manifest["engineering_fingerprints"])["3.6B-RC2"][
            "engineering"
        ] = "0" * 64
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
        "method",
        "panel",
        "disclaimer_id",
        "disclaimer_meaning",
        "fastener",
        "minor",
        "moment",
        "channel",
        "fingerprint",
    ],
)
def test_stage_3_6_freeze_rejects_pinned_record_tampering(kind: str) -> None:
    _, manifest = _manifest()
    tampered = deepcopy(manifest)
    _tamper_pinned_record(tampered, kind)
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered)


@pytest.mark.parametrize(
    ("index", "label"),
    [(0, "Stage 3.6A"), (4, "Calculation Slice 4"), (8, "Stage 3.6B RC2")],
)
def test_stage_3_6_freeze_rejects_controlled_artifact_tampering(index: int, label: str) -> None:
    _, manifest = _manifest()
    controlled = _entries(deepcopy(manifest), "controlled_stage_3_6_repository_artifacts")
    controlled[index]["sha256"] = "0" * 64
    assert label in {"Stage 3.6A", "Calculation Slice 4", "Stage 3.6B RC2"}
    with pytest.raises(AssertionError):
        _assert_sha256_artifacts([controlled[index]])


def test_stage_3_6_freeze_rejects_modified_manifest_bytes() -> None:
    raw, _ = _manifest()
    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")


def test_stage_3_6_freeze_rejects_wrong_supplied_historical_target() -> None:
    with pytest.raises(AssertionError):
        _resolve_stage_3_6_freeze(
            _repository_root(),
            allow_tag=False,
            supplied_target="0" * 40,
        )


def test_stage_3_6_freeze_rejects_wrong_tag_peeled_target() -> None:
    with pytest.raises(AssertionError):
        _assert_expected_freeze_target("1" * 40, "0" * 40)
