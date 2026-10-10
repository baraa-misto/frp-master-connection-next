"""Exact security successors reject every mutation and restore accepted history."""

from __future__ import annotations

import json
from importlib.metadata import distributions, version

import pytest

from tests.direct_f8_g1_governance import (
    F7_LOCK_SHA256,
    PRE_G1_LOCK_SHA256,
    ROOT,
    authority,
    digest,
    f7_lock,
    package_blocks,
    pre_g1_bootstrap,
    pre_g1_lock,
    pre_g1_workflow,
)
from tests.direct_f9_governance import pre_f9_workflow


def test_exact_security_chain_reconstructs_both_predecessors() -> None:
    raw = (ROOT / "backend/requirements/requirements-dev-py314.lock.txt").read_bytes()
    assert digest(pre_g1_lock(raw)) == PRE_G1_LOCK_SHA256
    assert digest(f7_lock(raw)) == F7_LOCK_SHA256
    assert package_blocks(pre_g1_lock(raw))["mako"].startswith(b"mako==1.3.12 ")
    assert package_blocks(pre_g1_lock(raw))["pip"].startswith(b"pip==26.1.2 ")
    assert digest(
        pre_g1_workflow(pre_f9_workflow((ROOT / ".github/workflows/ci.yml").read_bytes()))
    ) == ("C6B56ED836C0BAD48ECC66B489E73A46CA59B94E4354E475F732809EE1DFCC74")


@pytest.mark.parametrize(
    "mutation",
    [
        "mako-version",
        "mako-url",
        "mako-hash",
        "mako-missing",
        "mako-duplicated",
        "pip-version",
        "pip-url",
        "pip-hash",
        "pip-missing",
        "pip-duplicated",
        "unrelated",
        "extra-bytes",
        "truncation",
        "header",
    ],
)
def test_security_lock_mutations_fail_closed(mutation: str) -> None:
    raw = (ROOT / "backend/requirements/requirements-dev-py314.lock.txt").read_bytes()
    blocks = package_blocks(raw)
    if mutation.startswith(("mako-", "pip-")):
        name, operation = mutation.split("-", 1)
        block = blocks[name]
        if operation == "version":
            changed = (
                block.replace(b"1.4.2", b"1.4.3")
                if name == "mako"
                else block.replace(b"26.2.0", b"26.2.1")
            )
        elif operation == "url":
            changed = block + b"    # https://unapproved.invalid/security-wheel.whl\n"
        elif operation == "hash":
            changed = block.replace(b"--hash=sha256:", b"--hash=sha256:0", 1)
        elif operation == "missing":
            changed = b""
        else:
            changed = block * 2
            with pytest.raises(AssertionError, match="DUPLICATE"):
                package_blocks(raw.replace(block, changed))
        raw = raw.replace(block, changed)
    elif mutation == "unrelated":
        raw = raw.replace(b"alembic==1.18.5", b"alembic==1.18.6")
    elif mutation == "extra-bytes":
        raw += b"\n# EXTRA AUTHORITY\n"
    elif mutation == "truncation":
        raw = raw[:-1]
    else:
        raw = raw.replace(b"--upgrade-package mako==1.4.2", b"--upgrade")
    with pytest.raises(AssertionError, match="LOCK_IDENTITY"):
        pre_g1_lock(raw)


@pytest.mark.parametrize("field", ["predecessor", "artifact-url"])
def test_security_authority_mutation_cannot_repin_history(field: str) -> None:
    manifest = authority()
    if field == "predecessor":
        manifest["security_successor"]["pre_g1_lock_sha256"] = "0" * 64
    else:
        manifest["security_successor"]["packages"]["mako"]["artifacts"][0]["url"] = (
            "https://unapproved.invalid/mako.whl"
        )
    mutated = (json.dumps(manifest, indent=2) + "\n").encode()
    with pytest.raises(AssertionError, match="AUTHORITY_IDENTITY"):
        authority(mutated)


def test_governed_environment_has_only_the_authorized_versions() -> None:
    # PyPI's pip 26.2 distribution is the exact zero-patch 26.2.0 release.
    assert version("pip") in {"26.2", "26.2.0"}
    expected = {"mako": "1.4.2", "scipy": "1.18.1", "numpy": "2.5.3"}
    for name, required in expected.items():
        assert version(name) == required
    installed = [
        (item.metadata["Name"].lower().replace("_", "-"), item.version) for item in distributions()
    ]
    for name in ("mako", "pip"):
        matches = [v for n, v in installed if n == name]
        assert len(matches) == 1
        assert matches[0] in ({"26.2", "26.2.0"} if name == "pip" else {"1.4.2"})


def test_bootstrap_successor_is_exact_and_preserves_historical_seed() -> None:
    raw = (ROOT / "scripts/backend-bootstrap.ps1").read_bytes()
    predecessor = pre_g1_bootstrap(raw)
    assert b"environment-provided pip 26.1.2" in predecessor
    assert b"Exact F8-G1 installed security and statistical successors" in raw
    with pytest.raises(AssertionError):
        pre_g1_bootstrap(raw + b"\n# unauthorized\n")
