"""Successor-safe audit for the accepted Stage 3.5 concrete-support family."""

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

_MANIFEST_RELATIVE_PATH = (
    "docs/governance/STAGE_3_5_CONCRETE_SUPPORT_SHEAR_FAMILY_FREEZE_MANIFEST.json"
)
_MANIFEST_SHA256 = "671DF6992BC35AFED3C7CE9CB0230F7778C74CE8E7F412C16A9467F080AB7258"
_PRODUCT_BASELINE = "4c154b9d31e2a0100fd9f8c5cc90243e838a19c7"
_STAGE_3_5_TAG = "stage-3.5-concrete-support-shear-family-freeze"
_FREEZE_SUBJECT = "chore: freeze Stage 3.5 concrete-support shear family baseline"
_FREEZE_COMMIT_COUNT = 89
_EXPECTED_REPOSITORY_IDENTITIES: dict[str, object] = {
    "accepted_backend_tree": "42f063a1154cc99198b598470b9d2fb47c0f2c3f",
    "accepted_frontend_tree": "b14b0e506226962904d0e12902fd295dce6919de",
    "accepted_backend_src_tree": "e493b512d59e6218b61a2dc43bf0aed8c00cce16",
    "accepted_frontend_src_tree": "bf2f82d8d5f2b274feab64c674a75270eca3d497",
    "accepted_workflow_tree": "20edd491455e6329c4565bc72cd7b88e29d3f7b1",
    "accepted_engineering_tree": "3b9864403c77710868e97a22d5a4d24ca0e15b22",
    "accepted_golden_tree": "c79e27cd7e3d69b72c47dc80b46a0a4602786cfb",
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
}
_ACCEPTANCE_CHAIN = [
    (
        "454f3ae9090f51d45d8efe17ebaf8cd155ec9542",
        "feat: add paired clip-angle concrete-wall connection",
    ),
    (
        "23129f4cba11fb8e12001b0f450b83f9cf24dc08",
        "fix: complete concrete-wall paired-angle connection",
    ),
    (
        "e0534a8da4b7ce3d74cf1bed3d4be4e0c7fcbd12",
        "feat: expand concrete-wall forces and correct axes",
    ),
    (
        "b17d4adf4cefcd981aef344fc313d7b18c492f54",
        "feat: add direct side-lap concrete-wall connection",
    ),
    (
        "f72663a54700d84ac03a06e82a0e5fd39b4a0120",
        "fix: correct side-lap presentation and axes",
    ),
    (
        "af12eafd5b97696ae4272ba13a2933eefaac36d9",
        "feat: add column web-angle concrete-base connection",
    ),
    (
        "58a89c52220fd8878b330206b209910008df84e4",
        "fix: correct column-base force presentation",
    ),
    (_PRODUCT_BASELINE, "feat: add signed axial uplift to column base"),
]
_EXTERNAL_ORDER_HASHES = {
    "Stage 3.5A": "BEE47833030B54AD9EC2D7EEF7156B5D7E67561541C0BFC4EA111384AB3AA3B4",
    "Stage 3.5A-R1": "98D46D9C0A2E51537B0F7858EB6C58C6A14D24CFD8FBA5BF5975B610F40D0B7C",
    "Stage 3.5A-R2": "2439FC7E45A6644F127C7DEEC23859AB99DC71E39D9837466026EE093DD2C753",
    "Stage 3.5B": "6D89A60096B5943EF3BA31E65F8F2172B5165833383887D49905E322F5DDD77C",
    "Stage 3.5B-R1": "9F4BE503F8615663D2DCBF299DE8D755A5F88100EF5D60E3995EA4EC2D5141CB",
    "Stage 3.5C": "0217CE08BFEF09FE37419AC19C716DE4A3972AB208015F976C3901D69EC4DBC9",
    "Stage 3.5C-R1": "181345321788B4D4F8632B17B720B35CB63886AB6A91DD02B8DCEF16772DB1DA",
    "Stage 3.5C-R2": "681E643A3F5E008F85704C83CABBAD2648B522CD3EE12D6F5811536BB0588052",
    "Stage 3.5 Freeze": "5D090E262730AC5353CF157353E19C9F40787EA1661750FA6D50F5465E5D425D",
}
_EXPECTED_CURRENT_CONTRACTS = ["3.5A-R2-RC1", "3.5B-RC1", "3.5C-R2-RC1"]
_EXPECTED_HISTORICAL_CONTRACTS = ["3.5A-RC1", "3.5A-R1-RC1", "3.5C-RC1"]
_EXPECTED_FINGERPRINTS = {
    "3.5A-RC1": {
        "input": "09c2c297de51109472ec71712fcd7075e1458e1ab0edc0c39e2a0a1b4b5d2491",
        "application": "1cf31db46be8a5114f0fcd1fb58562792813cbb99a1b0a2ac184511023e9877c",
        "engineering": "2e1f9dca79aa4af75238f27d7ae7e96232da1ca6083a613d9c6d00d75ae66e98",
        "handoff": "592aa3c34d176688909c4dbb01d7171719e60776dfd72faa68be9595d820b353",
    },
    "3.5A-R1-RC1": {
        "input": "ac029264e8403f1f64a12266ba8dbe21cdfe69d407c1bd5ef9e9b11ec6f6bbbc",
        "application": "6792e177eb1849335cd98826b8ac43f4caa1ad8fae06365032744eaa956adbe9",
        "engineering": "e472fb281c358aa86c2ed22ab4da69dc6dc5fa9a51cbf8d5df9b6c782af06fa7",
        "handoff": "a19b526a3c99cdfe011109419ec2dd966b0a6499ab0f4de35ff26e97ec02ed91",
    },
    "3.5A-R2-RC1": {
        "input": "6291389f95478f5684318505e9f5a59cea01069baed55d4e613ee0836e546802",
        "application": "5db30ce792c807c8de3de3b073b1c7ba593f45cf2881fcad60def403e187c357",
        "engineering": "23d003ddc8d8832b203dea3561e5f8759e7d630365f30643e0fc11df5f99dc65",
        "handoff": "fbcc94cd4da3e173370f0a4c0600af64f8e63f8c680ed591ebd0fbf4527fac2a",
    },
    "3.5B-RC1": {
        "geometry": "ca3d5464ce07828547c60cfe0cf4d2378d17ff56443e1347660a4fdce3fe9aa7",
        "application": "7d5d165b41a54d27e7c24790e3465b15a24228080b2e2fa69d74c16b6b01fa34",
        "engineering": "222e86d3cb53ab435de83286d3eb248c1a93a5dc167bca2870244f78970dcd78",
        "handoff": "091077c9c1a4a5a5740c316258ca28b60d2be3f7c929057418bd6e417e7e7d5e",
    },
    "3.5C-RC1": {
        "application": "031efa1743015eaea2d2f93e36de656553e1f6bfe1678be47501b722d1ec48f4",
        "engineering": "60fd4257515ac1ef82415b3e9de0dac07980f32970385665bb808b3edfaa8c3d",
        "handoff": "b8bdc968006c30b4b7e91b46aa936efe1989cc3798e2678cb8d5a6fb607ce433",
    },
    "3.5C-R2-RC1": {
        "application": "748c22a67decfe576c6dc8a6f55d2fbf9c8885750cca62c98cfc92e62c3fa402",
        "engineering": "d5f15ca70f2cde2d439c5bfd0ec9c22da4f4f162c5d3021ed0c6525f4eab1f1f",
        "handoff": "a7d29f3935d227341957243a8506d1ccafa3bc5b52280abe66d19b8d513d8bf6",
    },
}
_EXPECTED_LIMITATIONS = [
    "Concrete and anchor-system capacities are not calculated.",
    "User-applied moments are not accepted by Stage 3.5 products.",
    "Exact eccentricity-generated transfer moments are retained.",
    "Stage 3.5A Minor-shear paired-branch allocation is not evaluated.",
    "One-anchor wall groups do not receive a fabricated moment-equilibrating force distribution.",
    (
        "Wall-leg, angle-body, and horizontal-leg prying are not evaluated where not "
        "explicitly authorized."
    ),
    "Direct side-lap pull-through and out-of-plane response remain not evaluated.",
    "Column-base angle-body and heel uplift transfer remain not evaluated.",
    "Column-base anchor tension and concrete uplift remain external-design-required.",
    "Unsupported bolt-axis tension and web-normal prying are not invented.",
    "Serial component-design demands are not additive physical reactions.",
    "No ordinary whole-connection PASS is issued across required unevaluated or external checks.",
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


def _entries(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    entries = manifest[key]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return cast(list[dict[str, object]], entries)


def _assert_manifest_bytes(raw: bytes) -> None:
    assert hashlib.sha256(raw).hexdigest().upper() == _MANIFEST_SHA256


def _assert_sha256_artifacts(entries: list[dict[str, object]]) -> None:
    repository_root = _repository_root()
    for entry in entries:
        path = cast(str, entry["path"])
        expected = cast(str, entry["sha256"])
        if path in _SECURITY_HISTORICAL_TEST_PATHS:
            _assert_historical_test_record(repository_root, path, cast(str, entry["sha256"]))
            continue
        actual = hashlib.sha256((repository_root / path).read_bytes()).hexdigest().upper()
        assert actual == expected


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
        "subject": "feat: add signed axial uplift to column base",
        "commit_count": 88,
        "tracked_file_count": 539,
        "branch": "main",
    }

    freeze = cast(dict[str, object], manifest["governance_freeze_commit"])
    assert freeze["identity"] == "SELF"
    assert freeze["expected_commit_count"] == _FREEZE_COMMIT_COUNT
    assert freeze["expected_subject"] == _FREEZE_SUBJECT
    assert freeze["freeze_tag"] == _STAGE_3_5_TAG
    assert freeze["tag_type"] == "annotated"
    assert manifest["repository_identities"] == _EXPECTED_REPOSITORY_IDENTITIES
    assert manifest["historical_contract_versions"] == _EXPECTED_HISTORICAL_CONTRACTS
    assert manifest["current_contract_versions"] == _EXPECTED_CURRENT_CONTRACTS
    assert manifest["engineering_fingerprints"] == _EXPECTED_FINGERPRINTS
    assert manifest["deliberate_limitations"] == _EXPECTED_LIMITATIONS
    declaration = cast(dict[str, bool], manifest["no_production_change_declaration"])
    assert declaration == {
        "backend_src_changed": False,
        "frontend_src_changed": False,
        "calculation_method_changed": False,
        "controlled_engineering_artifact_changed": False,
        "dependency_changed": False,
        "workflow_changed": False,
        "existing_freeze_tag_changed": False,
        "new_connection_family_started": False,
    }


def _resolve_stage_3_5_freeze(
    repository_root: Path,
    *,
    allow_tag: bool = True,
    allow_external_target: bool = True,
    supplied_target: str | None = None,
) -> _FreezeResolution:
    tag_ref = f"refs/tags/{_STAGE_3_5_TAG}"
    target = supplied_target
    if target is None:
        target = os.environ.get("STAGE_3_5_FREEZE_TARGET")
    if allow_tag and _tag_is_available(repository_root, _STAGE_3_5_TAG):
        assert _git(repository_root, "cat-file", "-t", tag_ref) == "tag"
        resolved_target = _git(repository_root, "rev-parse", f"{tag_ref}^{{}}")
        if target is not None:
            _assert_expected_freeze_target(resolved_target, target)
        return _FreezeResolution(resolved_target, "tag")
    if allow_external_target and target is not None:
        assert _object_is_available(repository_root, f"{target}^{{commit}}")
        resolved_target = _git(repository_root, "rev-parse", f"{target}^{{commit}}")
        _assert_expected_freeze_target(resolved_target, target)
        return _FreezeResolution(resolved_target, "object")
    return _FreezeResolution(None, "manifest_only")


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


def test_stage_3_5_freeze_manifest_is_byte_exact_and_complete() -> None:
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    assert manifest["schema"] == (
        "frp-master-connection-stage-3.5-concrete-support-shear-family-freeze-manifest-v1"
    )
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "3.5"
    order = cast(dict[str, object], manifest["controlling_order"])
    assert order["sha256"] == _EXTERNAL_ORDER_HASHES["Stage 3.5 Freeze"]
    assert str(order["final_sentinel"]).endswith("DO NOT PROCEED IF THIS LINE IS MISSING")

    controlled = _entries(manifest, "controlled_stage_3_5_repository_artifacts")
    inherited = _entries(manifest, "inherited_authorities")
    assert len(controlled) == 28
    assert len(inherited) == 47
    assert len({cast(str, item["path"]) for item in [*controlled, *inherited]}) == 75
    _assert_sha256_artifacts([*controlled, *inherited])

    orders = _entries(manifest, "external_control_orders")
    actual_orders = {cast(str, item["revision"]): cast(str, item["sha256"]) for item in orders}
    assert actual_orders == _EXTERNAL_ORDER_HASHES


def test_stage_3_5_acceptance_chain_ci_and_visual_evidence_are_exact() -> None:
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

    ci = cast(dict[str, dict[str, object]], manifest["ci_evidence"])
    assert [ci[key]["run_number"] for key in ci if key != "provider"] == list(range(76, 84))
    assert all(
        ci[key]["jobs_green"] == ci[key]["jobs_total"] == 4 for key in ci if key != "provider"
    )
    assert ci["stage_3_5a"]["attempt"] == 2
    assert ci["stage_3_5c_r2"]["duration"] == "approximately 5m43s"
    visual = cast(dict[str, object], manifest["accepted_visual_evidence"])
    assert visual["status"] == "accepted"
    assert visual["acceptance_date"] == "2026-08-29"
    assert visual["stage_3_5c_final_successor"] == "3.5C-R2-RC1"


def test_stage_3_5_existing_historical_tags_remain_exact_when_available() -> None:
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


def test_stage_3_5_benchmark_and_contract_inventory_is_exact() -> None:
    repository_root = _repository_root()
    _, manifest = _manifest()
    benchmark_paths = {
        "stage_3_5a": (
            "backend/tests/golden/stage_3_5a_beam_to_concrete_paired_clip_angle_"
            "golden_benchmarks_rc1.json"
        ),
        "stage_3_5a_r1": (
            "backend/tests/golden/stage_3_5a_r1_concrete_wall_paired_angle_completion_"
            "golden_benchmarks_rc1.json"
        ),
        "stage_3_5a_r2": (
            "backend/tests/golden/stage_3_5a_r2_material_axes_three_component_force_"
            "golden_benchmarks_rc1.json"
        ),
        "stage_3_5b": (
            "backend/tests/golden/stage_3_5b_direct_side_lap_angle_channel_concrete_wall_"
            "golden_benchmarks_rc1.json"
        ),
        "stage_3_5c": (
            "backend/tests/golden/stage_3_5c_column_base_web_angles_concrete_"
            "golden_benchmarks_rc1.json"
        ),
        "stage_3_5c_r2": (
            "backend/tests/golden/stage_3_5c_r2_signed_axial_uplift_expansion_"
            "golden_benchmarks_rc1.json"
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

    products = cast(dict[str, dict[str, object]], manifest["frozen_products"])
    assert set(products) == {"stage_3_5a", "stage_3_5b", "stage_3_5c"}
    assert len(cast(list[str], products["stage_3_5a"]["connected_profiles"])) == 6
    assert len(cast(list[str], products["stage_3_5b"]["profiles"])) == 2
    assert len(cast(list[str], products["stage_3_5c"]["component_demands"])) == 5
    boundary = cast(dict[str, object], manifest["external_design_boundary"])
    assert len(cast(list[str], boundary["required"])) == 5
    assert boundary["ordinary_whole_connection_pass_prohibited"] is True


def test_stage_3_5_freeze_resolves_tag_object_or_manifest_only_without_network() -> None:
    repository_root = _repository_root()
    raw, manifest = _manifest()
    _assert_manifest_bytes(raw)
    _assert_pinned_freeze_records(manifest)
    resolution = _resolve_stage_3_5_freeze(repository_root)
    if resolution.revision is None:
        assert resolution.source == "manifest_only"
        return
    assert resolution.source in {"tag", "object"}
    _assert_freeze_object(repository_root, resolution.revision)


def test_stage_3_5_freeze_explicit_object_mode_when_supplied() -> None:
    repository_root = _repository_root()
    supplied_target = os.environ.get("STAGE_3_5_FREEZE_TARGET")
    if supplied_target is None:
        assert _resolve_stage_3_5_freeze(
            repository_root, allow_tag=False, allow_external_target=False
        ) == _FreezeResolution(None, "manifest_only")
        return
    resolution = _resolve_stage_3_5_freeze(
        repository_root,
        allow_tag=False,
        supplied_target=supplied_target,
    )
    assert resolution == _FreezeResolution(supplied_target, "object")
    _assert_freeze_object(repository_root, supplied_target)


def test_stage_3_5_freeze_future_tagless_successor_never_substitutes_head() -> None:
    repository_root = _repository_root()
    resolution = _resolve_stage_3_5_freeze(
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
        record = cast(
            dict[str, object],
            cast(dict[str, object], manifest["repository_identities"])[key],
        )
        record["git_blob"] = "0" * 40
    elif kind == "baseline":
        cast(dict[str, object], manifest["accepted_product_baseline"])["commit"] = "0" * 40
    elif kind == "contract":
        cast(list[str], manifest["current_contract_versions"])[-1] = "3.5C-R3-DRAFT"
    elif kind == "fingerprint":
        fingerprints = cast(dict[str, dict[str, str]], manifest["engineering_fingerprints"])
        fingerprints["3.5C-R2-RC1"]["engineering"] = "0" * 64
    elif kind == "limitation":
        cast(list[str], manifest["deliberate_limitations"])[0] = "Concrete capacity added."
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
        "contract",
        "fingerprint",
        "limitation",
    ],
)
def test_stage_3_5_freeze_rejects_pinned_record_tampering(kind: str) -> None:
    _, manifest = _manifest()
    tampered = deepcopy(manifest)
    _tamper_pinned_record(tampered, kind)
    with pytest.raises(AssertionError):
        _assert_pinned_freeze_records(tampered)


def test_stage_3_5_freeze_rejects_manifest_and_artifact_tampering() -> None:
    raw, manifest = _manifest()
    with pytest.raises(AssertionError):
        _assert_manifest_bytes(raw + b"\n")

    tampered = deepcopy(manifest)
    _entries(tampered, "controlled_stage_3_5_repository_artifacts")[0]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_sha256_artifacts(_entries(tampered, "controlled_stage_3_5_repository_artifacts"))


def test_stage_3_5_freeze_rejects_wrong_supplied_historical_target() -> None:
    with pytest.raises(AssertionError):
        _resolve_stage_3_5_freeze(
            _repository_root(),
            allow_tag=False,
            supplied_target="0" * 40,
        )


def test_stage_3_5_freeze_rejects_wrong_tag_peeled_target() -> None:
    with pytest.raises(AssertionError):
        _assert_expected_freeze_target("1" * 40, "0" * 40)
