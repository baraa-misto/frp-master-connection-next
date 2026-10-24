"""Exact S1 security-only reversal before all unchanged historical authorities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = "45D1B472F8645439DB43F19A5894CB78201592AB431857FD35F323B7CBF45243"
DEPENDENCIES = (
    "backend/pyproject.toml",
    "backend/requirements/requirements-dev-py314.lock.txt",
    "frontend/package-lock.json",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest().upper()


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (
            (ROOT / "docs/governance/HYB2_D3_P4_S1_SECURITY_SUCCESSOR.json")
            .read_text(encoding="utf8")
            .encode()
        )
    assert digest(raw) == MANIFEST_SHA256, "S1_SECURITY_AUTHORITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def require_successor(path: str, raw: bytes) -> bytes:
    """Reject any changed path, pin, hash, record or metadata outside this successor."""
    governed = authority()
    assert path in DEPENDENCIES, "S1_SECURITY_PATH_INVALID"
    assert digest(raw) == governed["files"][path]["after_normalized_sha256"], (
        "S1_SECURITY_SUCCESSOR_INVALID"
    )
    previous = pre_s1_dependency(path, raw)
    assert digest(previous) == governed["files"][path]["before_normalized_sha256"]
    return previous


def pre_s1_dependency(path: str, raw: bytes) -> bytes:
    """Recognize exact current bytes only; all other bytes retain older strict guards."""
    governed = authority()
    row = governed["files"].get(path)
    if row is None or digest(raw) != row["after_normalized_sha256"]:
        return raw
    raw = raw.replace(b"\r\n", b"\n")
    if path.endswith("package-lock.json"):
        data = json.loads(raw)
        for record in governed["npm_records"]:
            assert data["packages"][record["path"]] == record["after"]
            data["packages"][record["path"]] = record["before"]
        previous = (json.dumps(data, indent=2) + "\n").encode()
    elif path.endswith("pyproject.toml"):
        for record in governed["pyproject_replacements"]:
            after, before = record["after"].encode(), record["before"].encode()
            assert raw.count(after) == record["occurrences"]
            raw = raw.replace(after, before)
        previous = raw
    else:
        for record in governed["python_records"].values():
            after, before = record["after_block"].encode(), record["before_block"].encode()
            assert digest(after) == record["after_sha256"]
            assert digest(before) == record["before_sha256"]
            assert raw.count(after) == 1
            raw = raw.replace(after, before, 1)
        header = governed["header_added"].encode()
        assert raw.count(header) == 1
        previous = raw.replace(header, b"", 1)
    assert digest(previous) == row["before_normalized_sha256"], "S1_PREDECESSOR_INVALID"
    return previous


def pre_s1_workflow(raw: bytes) -> bytes:
    governed = authority()["workflow"]
    raw = raw.replace(b"\r\n", b"\n")
    if digest(raw) != governed["after_sha256"]:
        return raw
    added = governed["added_steps"].encode()
    current = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(added) == raw.count(current) == 1
    previous = raw.replace(added, b"").replace(current, b"--expected-tests 9495")
    assert digest(previous) == governed["before_sha256"], "S1_WORKFLOW_PREDECESSOR_INVALID"
    return previous


def installed_python_versions() -> dict[str, str]:
    from importlib.metadata import version

    actual = {name: version(name) for name in ("pypdf", "setuptools")}
    assert actual == {"pypdf": "6.21.2", "setuptools": "84.1.0"}, "S1_INSTALLED_VERSION_INVALID"
    return actual
