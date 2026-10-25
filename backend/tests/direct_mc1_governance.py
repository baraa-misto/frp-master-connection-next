"""Narrow MC1 workflow successor; reverse to the immutable accepted F9 workflow."""

from __future__ import annotations

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest

MANIFEST_SHA256 = "D18F2759ACE671A26B04D3AB805067346DF085549AFBA3035367261311A32714"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_F9_MC1_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "MC1_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_mc1_workflow(raw: bytes) -> bytes:
    governed = authority()
    raw = raw.replace(b"\r\n", b"\n")
    from tests.direct_sab2_governance import pre_sab2_workflow

    raw = pre_sab2_workflow(raw, error_message="MC1_WORKFLOW_IDENTITY_INVALID")
    assert digest(raw) == governed["workflow_sha256"], "MC1_WORKFLOW_IDENTITY_INVALID"
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == 1
    assert raw.count(count) == 1
    raw = raw.replace(steps, b"").replace(count, b"--expected-tests 8658")
    assert digest(raw) == governed["predecessor_workflow_sha256"]
    return raw
