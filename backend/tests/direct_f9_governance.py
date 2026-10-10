"""Narrow F9 workflow successor, preserving the accepted F8-G1 predecessor."""

from __future__ import annotations

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import CI_SHA256, ROOT, digest

MANIFEST_SHA256 = "3941F15C9EC609088DC511318201560AF4CE5B6E50C25CBF69BE662634E6D07F"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_F9_STATUS_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "F9_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_f9_workflow(raw: bytes) -> bytes:
    if b"Generate authenticated Direct MC1" in raw:
        from tests.direct_mc1_governance import pre_mc1_workflow

        try:
            raw = pre_mc1_workflow(raw)
        except AssertionError as error:
            raise AssertionError("F9_WORKFLOW_IDENTITY_INVALID_MC1_SUCCESSOR") from error
    governed = authority()
    raw = raw.replace(b"\r\n", b"\n")
    assert digest(raw) == governed["workflow_sha256"], "F9_WORKFLOW_IDENTITY_INVALID"
    steps = governed["added_steps"].encode()
    assert raw.count(steps) == 1
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(count) == 1
    assert raw.count(b"timeout-minutes: 60") == 1
    raw = raw.replace(steps, b"").replace(count, b"--expected-tests 8568")
    raw = raw.replace(b"timeout-minutes: 60", b"timeout-minutes: 40")
    assert digest(raw) == governed["predecessor_workflow_sha256"] == CI_SHA256
    return raw
