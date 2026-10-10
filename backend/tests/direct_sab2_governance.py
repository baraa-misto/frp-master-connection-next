"""Exact SAB2 workflow successor; retain every predecessor gate and identity."""

from __future__ import annotations

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest

MANIFEST_SHA256 = "634F811BB621FA1A4FCC8E98DA4E3558193F01ECFEF8215BB6CDD390789920BA"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_SAB2_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "SAB2_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_sab2_workflow(
    raw: bytes, *, error_message: str = "SAB2_WORKFLOW_IDENTITY_INVALID"
) -> bytes:
    governed = authority()
    raw = raw.replace(b"\r\n", b"\n")
    if digest(raw) == governed["predecessor_workflow_sha256"]:
        return raw
    assert digest(raw) == governed["workflow_sha256"], error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == 1
    assert raw.count(count) == 1
    raw = raw.replace(steps, b"").replace(count, b"--expected-tests 8729")
    assert digest(raw) == governed["predecessor_workflow_sha256"]
    return raw
