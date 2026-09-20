"""Historical family audit; never treats a successor checkout as the frozen source."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Literal, NamedTuple, cast

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = "docs/governance/STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE_MANIFEST.json"
MANIFEST_SHA = "2C79F811EECFD89C04862359E583A240284872C10A0603E3D6CA276D657CED77"
CONTRACT_SHA = "E01BBD99A63453B9F24E4C0DDBA8D21AF3C4AED4094CE2A510C9B4B420C56638"
IDENTITY_SHA = "B30D1B314A209403009AE7C8722A4DCACD2DA70D621FD8455AD5E19A5A9BB6C1"
FINGERPRINT_SHA = "DEFAADB70F1F53EA7866DA9AF1CC5CF5FCDAE2924231DFEDA1C8EB0A17AB6527"
RECORD_SHA = "6F23188467D83E2105DBADE2BB2179B3C728CD22B3612993EA8474B8E635A664"
BASELINE = "6d953dbef648bd35ab21b5208432579cdeb59902"
SUBJECT = "chore: freeze Stage 4.1 beam moment splice family baseline"
TAG = "stage-4.1-beam-moment-splice-family-freeze"
ANNOTATION = "Freeze accepted Stage 4.1 Beam Moment Splice Family baseline"


class Resolution(NamedTuple):
    revision: str | None
    source: Literal["tag", "object", "manifest_only"]


def _git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(  # noqa: S603 - explicit local Git audit commands, no network
        ["git", *args],  # noqa: S607
        cwd=root,
        input=data,
        capture_output=True,
        check=True,
    ).stdout


def _text(root: Path, *args: str) -> str:
    return _git(root, *args).decode().strip()


def _available(root: Path, name: str) -> bool:
    return (
        subprocess.run(  # noqa: S603 - local object existence only
            ["git", "cat-file", "-e", name],  # noqa: S607
            cwd=root,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _canonical_sha(value: object) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _manifest(root: Path = ROOT) -> tuple[bytes, dict[str, object]]:
    raw = (root / MANIFEST_PATH).read_bytes()
    return raw, cast(dict[str, object], json.loads(raw))


def _assert_bytes(raw: bytes) -> None:
    assert _sha(raw) == MANIFEST_SHA


def _assert_contract(m: dict[str, object]) -> None:
    assert m["schema"] == "frp-master-connection-family-freeze-manifest"
    assert m["schema_version"] == "1.0.0"
    assert m["stage"] == "4.1"
    baseline = cast(dict[str, object], m["accepted_product_baseline"])
    assert baseline["commit"] == BASELINE
    assert baseline["commit_count"] == 102
    assert baseline["subject"] == "fix: restore Channel moment splice workspace rendering"
    assert m["governance_freeze_commit"] == {
        "identity": "SELF",
        "expected_parent": BASELINE,
        "expected_subject": SUBJECT,
        "expected_commit_count": 103,
        "tag": TAG,
        "tag_type": "annotated",
        "tag_annotation": ANNOTATION,
    }
    assert _canonical_sha(m["frozen_contracts"]) == CONTRACT_SHA
    assert _canonical_sha(m["repository_identities"]) == IDENTITY_SHA
    assert _canonical_sha(m["engineering_fingerprints"]) == FINGERPRINT_SHA
    assert (
        _canonical_sha(
            [
                m[key]
                for key in (
                    "controlled_artifacts",
                    "inherited_authorities",
                    "external_control_orders",
                    "existing_immutable_freezes",
                )
            ]
        )
        == RECORD_SHA
    )
    assert m["no_production_change_declaration"] == {
        "production": 0,
        "engineering_methods": 0,
        "controlled_engineering_artifacts": 0,
        "dependencies": 0,
        "workflows": 0,
        "lockfiles": 0,
        "existing_tags": 0,
        "governance_test_only": True,
    }


def _tree_id(entries: list[dict[str, str]]) -> str:
    """Rebuild Git's historical Merkle tree without Git writes or working-tree EOLs."""
    children: dict[str, list[dict[str, str]]] = {}
    leaves: dict[str, tuple[str, str]] = {}
    for entry in entries:
        path = entry["path"].replace("\\", "/")
        assert path
        assert not path.startswith("/")
        assert ".." not in path.split("/")
        if "/" in path:
            head, tail = path.split("/", 1)
            children.setdefault(head, []).append({**entry, "path": tail})
        else:
            assert path not in leaves
            leaves[path] = (entry["mode"], entry["git_blob"])
    assert not set(children).intersection(leaves)
    for name, descendants in children.items():
        leaves[name] = ("40000", _tree_id(descendants))
    names = sorted(leaves, key=lambda name: (name + ("/" if name in children else "")).encode())
    raw = b"".join(
        leaves[name][0].encode() + b" " + name.encode() + b"\0" + bytes.fromhex(leaves[name][1])
        for name in names
    )
    return hashlib.sha1(
        b"tree " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
    ).hexdigest()


def _assert_tree(root: Path, record: dict[str, object]) -> None:
    entries = cast(list[dict[str, str]], record["entries"])
    tree = cast(str, record["git_tree"])
    assert _tree_id(entries) == tree
    if _available(root, tree):
        actual = _text(root, "ls-tree", "-r", tree).splitlines()
        expected = [f"{r['mode']} blob {r['git_blob']}\t{r['path']}" for r in entries]
        assert sorted(actual) == sorted(expected)


def _blob_map(root: Path, ids: list[str]) -> dict[str, bytes]:
    """Batch local immutable object reads; missing history is explicit, not HEAD."""
    output = _git(root, "cat-file", "--batch", data=("\n".join(ids) + "\n").encode())
    cursor = 0
    result: dict[str, bytes] = {}
    for oid in ids:
        end = output.index(b"\n", cursor)
        header = output[cursor:end].decode().split()
        cursor = end + 1
        if header[-1] == "missing":
            continue
        assert header[0] == oid
        assert header[1] == "blob"
        size = int(header[2])
        result[oid] = output[cursor : cursor + size]
        cursor += size + 1
    assert cursor == len(output)
    return result


def _all_records(m: dict[str, object]) -> list[dict[str, str]]:
    identities = cast(dict[str, object], m["repository_identities"])
    records = list(cast(list[dict[str, str]], identities["packages"]))
    for tree in cast(dict[str, dict[str, object]], identities["trees"]).values():
        records.extend(cast(list[dict[str, str]], tree["entries"]))
    for values in cast(dict[str, list[dict[str, str]]], m["controlled_artifacts"]).values():
        records.extend(values)
    records.extend(cast(list[dict[str, str]], m["inherited_authorities"]))
    return records


def _assert_record_blobs(root: Path, records: list[dict[str, str]], *, require_all: bool) -> None:
    blobs = _blob_map(root, sorted({r["git_blob"] for r in records}))
    for record in records:
        raw = blobs.get(record["git_blob"])
        if raw is None:
            assert not require_all
        else:
            assert _sha(raw) == record["sha256"], record["path"]


def _assert_identities(root: Path, m: dict[str, object], revision: str | None = None) -> None:
    identities = cast(dict[str, object], m["repository_identities"])
    for path, tree_record in cast(dict[str, dict[str, object]], identities["trees"]).items():
        _assert_tree(root, tree_record)
        if revision is not None:
            assert _text(root, "rev-parse", f"{revision}:{path}") == tree_record["git_tree"]
    if revision is not None:
        for record in cast(list[dict[str, str]], identities["packages"]):
            assert _text(root, "rev-parse", f"{revision}:{record['path']}") == record["git_blob"]
        for record in [
            *[
                r
                for values in cast(
                    dict[str, list[dict[str, str]]], m["controlled_artifacts"]
                ).values()
                for r in values
            ],
            *cast(list[dict[str, str]], m["inherited_authorities"]),
        ]:
            assert _text(root, "rev-parse", f"{revision}:{record['path']}") == record["git_blob"]
    _assert_record_blobs(root, _all_records(m), require_all=revision is not None)


def _assert_no_alternates(root: Path) -> None:
    assert not os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES")
    location = Path(_text(root, "rev-parse", "--git-path", "objects/info/alternates"))
    assert not (location if location.is_absolute() else root / location).exists()


def _resolve(root: Path, *, allow_tag: bool = True, supplied: str | None = None) -> Resolution:
    tag = f"refs/tags/{TAG}"
    if allow_tag and _available(root, tag):
        assert _text(root, "cat-file", "-t", tag) == "tag"
        assert _text(root, "cat-file", "-p", tag).split("\n\n", 1)[1].strip() == ANNOTATION
        return Resolution(_text(root, "rev-parse", f"{tag}^{{}}"), "tag")
    if supplied is not None:
        assert re.fullmatch(r"[0-9a-f]{40}", supplied), "explicit full historical SHA required"
        assert _available(root, f"{supplied}^{{commit}}")
        assert _text(root, "rev-parse", f"{supplied}^{{commit}}") == supplied
        return Resolution(supplied, "object")
    return Resolution(None, "manifest_only")


def _assert_freeze_object(root: Path, revision: str) -> None:
    assert _available(root, f"{revision}^{{commit}}"), "historical freeze object is unavailable"
    raw = _text(root, "cat-file", "-p", revision)
    header, message = raw.split("\n\n", 1)
    assert [line[7:] for line in header.splitlines() if line.startswith("parent ")] == [BASELINE]
    assert message.splitlines()[0] == SUBJECT
    if _text(root, "rev-parse", "--is-shallow-repository") == "false":
        assert _text(root, "rev-list", "--count", revision) == "103"
    data = _git(root, "cat-file", "blob", f"{revision}:{MANIFEST_PATH}")
    _assert_bytes(data)
    m = cast(dict[str, object], json.loads(data))
    _assert_contract(m)
    _assert_identities(root, m, revision)


def audit(root: Path = ROOT, *, allow_tag: bool = True, supplied: str | None = None) -> Resolution:
    _assert_no_alternates(root)
    raw, m = _manifest(root)
    _assert_bytes(raw)
    _assert_contract(m)
    resolution = _resolve(root, allow_tag=allow_tag, supplied=supplied)
    if resolution.revision is None:
        _assert_identities(root, m)
    else:
        _assert_freeze_object(root, resolution.revision)
    return resolution


def test_family_resolution_and_explicit_historical_mode() -> None:
    supplied = os.environ.get("STAGE_4_1_FREEZE_TARGET")
    resolution = audit(supplied=supplied)
    expected = os.environ.get("STAGE_4_1_EXPECTED_RESOLUTION_SOURCE")
    if expected is not None:
        assert resolution.source == expected
    if supplied is not None:
        assert audit(allow_tag=False, supplied=supplied) == Resolution(supplied, "object")


def test_accepted_candidate_identities_and_chain() -> None:
    _, m = _manifest()
    current = _text(ROOT, "rev-parse", "HEAD")
    raw = _text(ROOT, "cat-file", "-p", current)
    header, message = raw.split("\n\n", 1)
    parents = [line[7:] for line in header.splitlines() if line.startswith("parent ")]
    # This is an explicit candidate gate, not historical resolution. Later HEADs
    # must not be compared against old source; the immutable object audit handles it.
    if current == BASELINE or (parents == [BASELINE] and message.splitlines()[0] == SUBJECT):
        _assert_identities(ROOT, m, current)
    for record in cast(list[dict[str, str]], m["acceptance_chain"]):
        if _available(ROOT, record["commit"]):
            assert _text(ROOT, "show", "-s", "--format=%s", record["commit"]) == record["subject"]
            if _text(ROOT, "rev-parse", "--is-shallow-repository") == "false":
                _git(ROOT, "merge-base", "--is-ancestor", record["commit"], current)


def test_controlled_bytes_golden_ranges_and_existing_tags() -> None:
    _, m = _manifest()
    ranges = cast(dict[str, int], m["benchmark_ranges"])
    for name, entries in cast(dict[str, list[dict[str, str]]], m["controlled_artifacts"]).items():
        assert len(entries) == 4
        for entry in entries:
            raw = (ROOT / entry["path"]).read_bytes()
            assert _sha(raw) == entry["sha256"]
            if entry["path"].endswith(".json"):
                benchmarks = json.loads(raw)["benchmarks"]
                assert [int(row["id"].split("_", 1)[0][1:]) for row in benchmarks] == list(
                    range(1, ranges[name] + 1)
                )
    for entry in cast(list[dict[str, str]], m["existing_immutable_freezes"]):
        tag = f"refs/tags/{entry['tag']}"
        if _available(ROOT, tag):
            assert _text(ROOT, "cat-file", "-t", tag) == "tag"
            assert _text(ROOT, "rev-parse", tag) == entry["tag_object"]
            assert _text(ROOT, "rev-parse", f"{tag}^{{}}") == entry["peeled_target"]


def test_runtime_default_fingerprints_remain_exact() -> None:
    from frp_master_connection.application.channel_moment_splice_orchestration import (
        design_check_channel_moment_splice,
        preview_channel_moment_splice,
    )
    from frp_master_connection.application.wi_moment_splice_orchestration import (
        design_check_wi_moment_splice,
        preview_wi_moment_splice,
    )
    from frp_master_connection.domain import (
        default_channel_moment_splice_request,
        default_wi_moment_splice_request,
    )

    _, m = _manifest()
    expected = cast(
        dict[str, dict[str, str]],
        cast(dict[str, object], m["engineering_fingerprints"])["backend_default_requests"],
    )
    channel = preview_channel_moment_splice(default_channel_moment_splice_request())
    wi = preview_wi_moment_splice(default_wi_moment_splice_request())
    for key, result in (("channel", channel), ("wi", wi)):
        for name in (
            "canonical_input_fingerprint",
            "geometry_fingerprint",
            "engineering_fingerprint",
            "application_fingerprint",
        ):
            assert getattr(result, name) == expected[key][name]
    assert (
        channel.slice6_result.result_fingerprint
        == expected["channel"]["component_resultant_fingerprint"]
    )
    assert wi.slice5_result.result_fingerprint == expected["wi"]["component_resultant_fingerprint"]
    assert (
        design_check_channel_moment_splice(
            default_channel_moment_splice_request()
        ).result_fingerprint
        == expected["channel"]["design_fingerprint"]
    )
    assert (
        design_check_wi_moment_splice(default_wi_moment_splice_request()).result_fingerprint
        == expected["wi"]["design_fingerprint"]
    )


@pytest.mark.parametrize(
    "path",
    [
        "accepted_product_baseline.commit",
        "frozen_contracts.runtime.r1_baseline",
        "frozen_contracts.wi.topology.total_plates",
        "frozen_contracts.channel.topology.total_plates",
        "frozen_contracts.channel.opening_direction",
        "frozen_contracts.slice5.m_over_z",
        "frozen_contracts.slice6.reference",
        "frozen_contracts.slice6.shear_center_sources",
        "frozen_contracts.slice6.generated_centroidal_torsion",
        "frozen_contracts.slice6.transverse_eccentricity_ledger",
        "frozen_contracts.channel.web.equal_shear_assumption",
        "frozen_contracts.wi.topology.split_inner_per_flange",
        "frozen_contracts.channel.flange.inner_force_line",
        "frozen_contracts.common_bolt.equal_plane_assumption",
        "frozen_contracts.common_bolt.blind_two_times_capacity",
        "frozen_contracts.boundaries.invented_bolt_tension",
        "frozen_contracts.boundaries.invented_prying",
        "frozen_contracts.boundaries.channel_warping_response",
        "frozen_contracts.result.ordinary_pass",
        "frozen_contracts.result.section_2_3_2",
        "frozen_contracts.result.stiffness",
        "frozen_contracts.fastener.f593",
        "frozen_contracts.runtime.blank_root_allowed",
        "frozen_contracts.successor.head_substitution",
        "engineering_fingerprints.backend_default_requests.channel.engineering_fingerprint",
    ],
)
def test_rejects_contract_and_fingerprint_tampering(path: str) -> None:
    _, m = _manifest()
    changed = deepcopy(m)
    target = changed
    keys = path.split(".")
    for key in keys[:-1]:
        target = cast(dict[str, object], target[key])
    target[keys[-1]] = "TAMPERED"
    with pytest.raises(AssertionError):
        _assert_contract(changed)


@pytest.mark.parametrize("path", ["backend/src", "frontend/src", ".github/workflows"])
@pytest.mark.parametrize("change", ["modify", "add", "delete", "rename"])
def test_rejects_source_tree_tampering(path: str, change: str) -> None:
    _, m = _manifest()
    identities = cast(dict[str, object], m["repository_identities"])
    tree = deepcopy(cast(dict[str, dict[str, object]], identities["trees"])[path])
    entries = cast(list[dict[str, str]], tree["entries"])
    if change == "modify":
        entries[0]["git_blob"] = "0" * 40
    elif change == "add":
        entries.append({**entries[0], "path": "ADDED"})
    elif change == "delete":
        entries.pop()
    else:
        entries[0]["path"] = "RENAMED"
    with pytest.raises(AssertionError):
        _assert_tree(ROOT, tree)


@pytest.mark.parametrize(
    "group",
    [
        "calculation_slice_5",
        "stage_4_1a",
        "calculation_slice_6",
        "stage_4_1b",
        "package",
        "lockfile",
    ],
)
def test_rejects_artifact_package_and_lock_bytes(group: str) -> None:
    _, m = _manifest()
    if group in {"package", "lockfile"}:
        entries = cast(
            list[dict[str, str]], cast(dict[str, object], m["repository_identities"])["packages"]
        )
        entry = deepcopy(entries[0 if group == "package" else 1])
    else:
        entry = deepcopy(cast(dict[str, list[dict[str, str]]], m["controlled_artifacts"])[group][0])
    entry["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _assert_record_blobs(ROOT, [entry], require_all=True)


def test_rejects_manifest_byte_mutation() -> None:
    raw, _ = _manifest()
    with pytest.raises(AssertionError):
        _assert_bytes(raw + b"\n")


@pytest.mark.parametrize("target", ["HEAD", "0" * 40, BASELINE])
def test_rejects_wrong_explicit_historical_target(target: str) -> None:
    with pytest.raises(AssertionError):
        audit(ROOT, allow_tag=False, supplied=target)


def test_rejects_wrong_peeled_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    original = _text
    originally_available = _available

    def wrong_tag(root: Path, *args: str) -> str:
        if args == ("cat-file", "-t", f"refs/tags/{TAG}"):
            return "tag"
        if args == ("cat-file", "-p", f"refs/tags/{TAG}"):
            return "object " + BASELINE + "\n\n" + ANNOTATION
        if args == ("rev-parse", f"refs/tags/{TAG}^{{}}"):
            return BASELINE
        return original(root, *args)

    monkeypatch.setitem(globals(), "_text", wrong_tag)
    monkeypatch.setitem(
        globals(),
        "_available",
        lambda root, name: name == f"refs/tags/{TAG}" or originally_available(root, name),
    )
    with pytest.raises(AssertionError):
        audit()


def test_tagless_successor_and_missing_history_never_query_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_history_git(_root: Path, *args: str, data: bytes | None = None) -> bytes:
        if args == ("rev-parse", "--git-path", "objects/info/alternates"):
            return b".git/objects/info/alternates\n"
        if args == ("cat-file", "--batch"):
            assert data is not None
            return b"".join(oid + b" missing\n" for oid in data.splitlines())
        raise AssertionError("No successor HEAD, source lookup, or network is permitted")

    monkeypatch.setitem(globals(), "_git", missing_history_git)
    monkeypatch.setitem(globals(), "_available", lambda _root, _name: False)
    assert audit(ROOT, allow_tag=False) == Resolution(None, "manifest_only")


def test_tree_identity_is_enumeration_and_path_separator_invariant() -> None:
    _, m = _manifest()
    trees = cast(
        dict[str, dict[str, object]], cast(dict[str, object], m["repository_identities"])["trees"]
    )
    for tree in trees.values():
        entries = cast(list[dict[str, str]], tree["entries"])
        reversed_windows = [{**r, "path": r["path"].replace("/", "\\")} for r in reversed(entries)]
        assert _tree_id(reversed_windows) == tree["git_tree"]
