"""Exact four-package boundary, immutable history and intentional mutation checks."""

import json
import re
from importlib.metadata import version

import pytest

from tests.direct_f8_g1_governance import f7_lock, package_blocks
from tests.hybrid_same_connection_governance import pre_p3_workflow
from tests.hybrid_security_successor import (
    DEPENDENCIES,
    ROOT,
    authority,
    digest,
    installed_python_versions,
    pre_s1_dependency,
    pre_s1_workflow,
    require_successor,
)


def test_four_package_scope_and_unchanged_parent_records() -> None:
    governed = authority()
    assert governed["starting_sha"] == "866df344a4f62cd909edd01ae851a5c9d7bb156e"
    assert governed["other_backend_versions_unchanged"] == 53
    assert set(governed["python_records"]) == {"pypdf", "setuptools"}
    assert {row["path"] for row in governed["npm_records"]} == {
        "node_modules/undici",
        "node_modules/zod",
    }
    path = "backend/requirements/requirements-dev-py314.lock.txt"
    current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
    previous = require_successor(path, current)
    assert len(package_blocks(current)) == len(package_blocks(previous)) == 55
    assert {
        name
        for name in package_blocks(current)
        if package_blocks(current)[name] != package_blocks(previous)[name]
    } == {"pypdf", "setuptools"}
    assert f7_lock(current) == f7_lock(previous)
    path = "frontend/package-lock.json"
    current_lock = json.loads((ROOT / path).read_bytes())
    previous_lock = json.loads(require_successor(path, (ROOT / path).read_bytes()))
    assert current_lock.keys() == previous_lock.keys()
    assert current_lock["packages"].keys() == previous_lock["packages"].keys()
    assert {
        key
        for key in current_lock["packages"]
        if current_lock["packages"][key] != previous_lock["packages"][key]
    } == {"node_modules/undici", "node_modules/zod"}
    for child, parent, expected in (
        ("undici", "jsdom", "30.0.1"),
        ("zod", "eslint-plugin-react-hooks", "7.1.1"),
    ):
        assert current_lock["packages"][f"node_modules/{child}"]["dev"] is True
        row = current_lock["packages"][f"node_modules/{parent}"]
        assert row["version"] == expected
        assert child in row["dependencies"]
    assert (
        digest((ROOT / "frontend/package.json").read_bytes())
        == governed["unchanged_frontend_package_normalized_sha256"]
    )


@pytest.mark.parametrize("path", DEPENDENCIES)
def test_each_dependency_reconstructs_its_exact_predecessor(path: str) -> None:
    raw = (ROOT / path).read_bytes()
    previous = require_successor(path, raw)
    row = authority()["files"][path]
    assert digest(previous) == row["before_normalized_sha256"]
    assert digest(raw) == row["after_normalized_sha256"]
    assert pre_s1_dependency(path, previous) == previous
    assert require_successor(path, raw.replace(b"\r\n", b"\n")) == previous


@pytest.mark.parametrize("package", ["pypdf", "setuptools", "undici", "zod"])
@pytest.mark.parametrize(
    "mutation", ["version", "hash", "metadata", "missing", "duplicate", "extra"]
)
def test_changed_package_or_artifact_never_crosses_successor_boundary(
    package: str,
    mutation: str,
) -> None:
    governed = authority()
    if package in governed["python_records"]:
        path = "backend/requirements/requirements-dev-py314.lock.txt"
        raw = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        block = governed["python_records"][package]["after_block"].encode()
        if mutation == "version":
            changed = re.sub(rb"==[^ \n]+", b"==0.0.0", block, count=1)
        elif mutation == "hash":
            changed = block.replace(b"--hash=sha256:", b"--hash=sha256:0", 1)
        elif mutation == "metadata":
            changed = block + b"    # unapproved artifact provenance\n"
        elif mutation == "missing":
            changed = b""
        elif mutation == "duplicate":
            changed = block * 2
        else:
            changed = block + b"\n# unauthorized bytes\n"
        mutated = raw.replace(block, changed, 1)
    else:
        path = "frontend/package-lock.json"
        raw = (ROOT / path).read_bytes()
        data = json.loads(raw)
        key = "node_modules/" + package
        row = data["packages"][key]
        if mutation == "version":
            row["version"] = "0.0.0"
        elif mutation == "hash":
            row["integrity"] += "0"
        elif mutation == "metadata":
            row["dev"] = False
        elif mutation == "missing":
            del data["packages"][key]
        elif mutation == "duplicate":
            data["packages"][key + "/unapproved"] = dict(row)
        else:
            data["packages"]["node_modules/jsdom"]["version"] = "0.0.0"
        mutated = (json.dumps(data, indent=2) + "\n").encode()
    assert mutated != raw
    with pytest.raises(AssertionError, match="S1_SECURITY_SUCCESSOR_INVALID"):
        require_successor(path, mutated)
    # No mutation is normalized into an accepted predecessor.
    assert pre_s1_dependency(path, mutated) == mutated


@pytest.mark.parametrize(
    "path",
    ["frontend/package.json", "../frontend/package-lock.json", "unknown", "backend/other.lock"],
)
def test_no_path_alias_or_extra_dependency_file_is_authorized(path: str) -> None:
    raw = (ROOT / "frontend/package-lock.json").read_bytes()
    with pytest.raises(AssertionError, match="S1_SECURITY_PATH_INVALID"):
        require_successor(path, raw)
    assert pre_s1_dependency(path, raw) == raw


def test_new_authority_is_immutable() -> None:
    raw = (ROOT / "docs/governance/HYB2_D3_P4_S1_SECURITY_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="S1_SECURITY_AUTHORITY_INVALID"):
        authority(raw + b" ")


def test_exact_workflow_restores_all_previous_gates_and_count() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    previous = pre_s1_workflow(raw)
    assert digest(previous) == authority()["workflow"]["before_sha256"]
    assert pre_s1_workflow(previous) == previous
    assert pre_p3_workflow(raw) == pre_p3_workflow(previous)
    assert previous.count(b"--expected-tests 9495") == 1
    assert b"Audit all dependencies" in previous
    assert b"Audit runtime dependencies" in previous


@pytest.mark.parametrize("mutation", ["count", "security", "pdf", "upload"])
def test_workflow_mutation_cannot_bypass_previous_authority(mutation: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    before, after = {
        "count": (b"--expected-tests 9535", b"--expected-tests 1"),
        "security": (b"full security audit", b"missing security audit"),
        "pdf": (b"hybrid-same-connection-pdfs/", b"missing-pdfs/"),
        "upload": (b"p4-s1-security-qa/", b"missing-security-qa/"),
    }[mutation]
    assert before in raw
    changed = raw.replace(before, after)
    assert pre_s1_workflow(changed) == changed
    with pytest.raises(AssertionError, match="P3_WORKFLOW_IDENTITY_INVALID"):
        pre_p3_workflow(changed)


def test_installed_fixed_versions_and_all_other_runtime_pins() -> None:
    assert installed_python_versions() == {"pypdf": "6.21.2", "setuptools": "84.1.0"}
    lock = (ROOT / "backend/requirements/requirements-dev-py314.lock.txt").read_text()
    for name, expected in re.findall(r"(?m)^([a-z][a-z0-9-]+)==([^ \\\n]+)", lock):
        actual = version(name)
        assert actual == expected or (name == "pip" and actual == "26.2" and expected == "26.2.0")


def test_engineering_and_historical_identities_survive_exact_two_lock_reversal() -> None:
    governed = authority()
    assert len(governed["protected_engineering"]) == 53
    assert len(governed["historical_controls"]) == 173
    exceptions = {row["path"] for row in governed["historical_controls"]} & set(DEPENDENCIES)
    assert exceptions == {
        "backend/requirements/requirements-dev-py314.lock.txt",
        "frontend/package-lock.json",
    }
    for group in ("protected_engineering", "historical_controls"):
        for row in governed[group]:
            current = (ROOT / row["path"]).read_bytes()
            assert digest(pre_s1_dependency(row["path"], current)) == row["normalized_sha256"]
