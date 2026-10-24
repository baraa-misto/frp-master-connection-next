"""Exact presentation successor; reverse only its recorded evidence/count delta."""

from __future__ import annotations

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest
from tests.hyb1_governance import pre_hyb1_workflow

MANIFEST_SHA256 = "69D97DB06183400D9B6355A6B3B8F6B961B7767742031887C99F5A84CD0C31BF"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_SAB2_P1_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "P1_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_p1_workflow(raw: bytes, *, error_message: str = "P1_WORKFLOW_IDENTITY_INVALID") -> bytes:
    governed = authority()
    raw = pre_hyb1_workflow(raw, error_message=error_message)
    if digest(raw) in governed["historical_workflow_sha256"]:
        return raw
    assert digest(raw) == governed["workflow_sha256"], error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == 1
    assert raw.count(count) == 1
    raw = raw.replace(steps, b"").replace(count, b"--expected-tests 8957")
    assert digest(raw) == governed["predecessor_workflow_sha256"]
    return raw
