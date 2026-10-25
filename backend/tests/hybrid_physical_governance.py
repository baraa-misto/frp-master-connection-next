"""Exact P4 workflow successor; retain the complete S1 security predecessor."""

import json
from typing import Any, cast

from tests.hybrid_security_successor import ROOT, digest

MANIFEST_SHA256 = "5C89338C766D2E96AB888473E43EFCBA18A3C48AE2BBB8C2FF3FF1B9623BE5AA"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/HYB2_D3_P4_WORKFLOW_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "P4_WORKFLOW_AUTHORITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_p4_workflow(raw: bytes) -> bytes:
    governed = authority()
    raw = raw.replace(b"\r\n", b"\n")
    if digest(raw) != governed["after_sha256"]:
        return raw
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == raw.count(count) == 1
    previous = raw.replace(steps, b"").replace(count, b"--expected-tests 9535")
    assert digest(previous) == governed["before_sha256"], "P4_WORKFLOW_PREDECESSOR_INVALID"
    return previous


def pre_p4_inactive_boundary(raw: bytes) -> bytes:
    """Accept only the approved two-path successor or its exact P3 predecessor."""
    governed = authority()["inactive_boundary_guard"]
    raw = raw.replace(b"\r\n", b"\n")
    if digest(raw) == governed["before_sha256"]:
        return raw
    assert digest(raw) == governed["after_sha256"], "P4_INACTIVE_BOUNDARY_IDENTITY_INVALID"
    added = governed["exact_added_block"].encode()
    replacement = governed["new_condition"].encode()
    assert raw.count(added) == raw.count(replacement) == 1
    previous = raw.replace(added, b"").replace(replacement, governed["old_condition"].encode())
    assert digest(previous) == governed["before_sha256"], "P4_INACTIVE_BOUNDARY_PREDECESSOR_INVALID"
    return previous
