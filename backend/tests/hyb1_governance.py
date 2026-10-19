"""HYB1 explicit additive successor; byte-exact predecessor reconstruction."""

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest

MANIFEST_SHA256 = "76EBBE2B70C72BB5C18441411ADD7D9E410410D0AB3C250D6BDD1A926CEC0C7F"


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
    versions = {
        governed["workflow_sha256"]: governed["backend_tests"],
        governed["supplement_predecessor_workflow_sha256"]: governed[
            "supplement_predecessor_backend_tests"
        ],
        governed["direct_predecessor_workflow_sha256"]: governed[
            "direct_predecessor_backend_tests"
        ],
        governed["r1_predecessor_workflow_sha256"]: governed["r1_predecessor_backend_tests"],
        governed["r2_predecessor_workflow_sha256"]: governed["r2_predecessor_backend_tests"],
    }
    assert digest(raw) in versions, error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {versions[digest(raw)]}".encode()
    assert raw.count(steps) == 1
    assert raw.count(count) == 1
    old = raw.replace(steps, b"").replace(count, b"--expected-tests 8980")
    assert digest(old) == governed["predecessor_workflow_sha256"]
    return old
