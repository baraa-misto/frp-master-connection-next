"""HYB1 explicit additive successor; byte-exact predecessor reconstruction."""

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest

MANIFEST_SHA256 = "BAD809F418E670F8AF44D11E842A5F026858AFD892719D0A2FD6283C943C2452"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_HYB1_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "HYB1_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_hyb1_workflow(
    raw: bytes, *, error_message: str = "HYB1_WORKFLOW_IDENTITY_INVALID"
) -> bytes:
    governed = authority()
    raw = raw.replace(b"\r\n", b"\n")
    if digest(raw) in governed["accepted_pre_hyb1_sha256"]:
        return raw
    assert digest(raw) == governed["workflow_sha256"], error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == 1
    assert raw.count(count) == 1
    old = raw.replace(steps, b"").replace(count, b"--expected-tests 8980")
    assert digest(old) == governed["predecessor_workflow_sha256"]
    return old
