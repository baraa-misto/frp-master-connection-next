"""Exact P2 CI/count successor; reconstruct the accepted P1 authority first."""

import hashlib
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = "74BFCF055DF4B7C36E6800A0FE9206D45F11AE4773D0754368385B04F9C8538C"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/HYB2_D3_P2_WORKSPACE_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "P2_WORKSPACE_AUTHORITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_p2_workflow(raw: bytes, *, error_message: str = "P2_WORKFLOW_IDENTITY_INVALID") -> bytes:
    raw = raw.replace(b"\r\n", b"\n")
    if b"hybrid-workflow-pdfs" not in raw:
        return raw
    governed = authority()
    if digest(raw) == governed["predecessor_workflow_sha256"]:
        return raw
    assert digest(raw) == governed["workflow_sha256"], error_message
    current = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(current) == 1
    previous = raw.replace(current, b"--expected-tests 9430")
    assert digest(previous) == governed["predecessor_workflow_sha256"]
    return previous
