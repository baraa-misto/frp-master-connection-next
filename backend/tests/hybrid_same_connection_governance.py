"""Exact P3 additive CI/report successor; reconstruct P2 before inherited guards."""

import hashlib
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = "ACCD408BD99B871FA32CEC104B83081A49195432E86CC75D1180DC3D81C43CAB"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/HYB2_D3_P3_SAME_CONNECTION_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "P3_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_p3_workflow(raw: bytes, *, error_message: str = "P3_WORKFLOW_IDENTITY_INVALID") -> bytes:
    from tests.hybrid_security_successor import pre_s1_workflow

    raw = pre_s1_workflow(raw)
    raw = raw.replace(b"\r\n", b"\n")
    if b"hybrid-same-connection-pdfs" not in raw:
        return raw
    governed = authority()
    assert digest(raw) == governed["workflow_sha256"], error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == raw.count(count) == 1
    previous = raw.replace(steps, b"").replace(count, b"--expected-tests 9455")
    assert digest(previous) == governed["predecessor_workflow_sha256"]
    return previous
