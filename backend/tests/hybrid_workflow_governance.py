"""Bounded live-workflow successor; retain the exact D2 and older CI authorities."""

import json
from typing import Any, cast

from tests.direct_f8_g1_governance import ROOT, digest

MANIFEST_SHA256 = "940A9D2252F334B8F578C5E8F17BA5C7435C18D54082DA4B28C2142C0F2C32EF"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/HYB2_D3_P1_WORKFLOW_SUCCESSOR.json").read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "D3_WORKFLOW_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_d3_workflow(raw: bytes, *, error_message: str = "D3_WORKFLOW_IDENTITY_INVALID") -> bytes:
    from tests.hybrid_workspace_governance import pre_p2_workflow

    raw = pre_p2_workflow(raw, error_message=error_message)
    raw = raw.replace(b"\r\n", b"\n")
    governed = authority()
    if b"hybrid-workflow-pdfs" not in raw:
        # The caller still validates the unchanged older workflow's exact hash.
        return raw
    assert digest(raw) == governed["workflow_sha256"], error_message
    steps = governed["added_steps"].encode()
    count = f"--expected-tests {governed['backend_tests']}".encode()
    assert raw.count(steps) == raw.count(count) == 1
    old = raw.replace(steps, b"").replace(count, b"--expected-tests 9369")
    assert digest(old) == governed["predecessor_workflow_sha256"]
    return old


def pre_d3_dependency(path: str, raw: bytes) -> bytes:
    """Reverse only the exact approved security successor, then retain old guards."""
    from tests.hybrid_workspace_security import pre_p2_dependency

    raw = pre_p2_dependency(path, raw)
    manifest = (
        (ROOT / "docs/governance/HYB2_D3_P1_SECURITY_SUCCESSOR.json")
        .read_text(encoding="utf8")
        .encode()
    )
    assert digest(manifest) == "F4E1B80932AEB9DF8295C72E8BED4920F83B442525CF52B1B3CF7E9699078EA6", (
        "D3_SECURITY_AUTHORITY_INVALID"
    )
    security = json.loads(manifest)
    identity = security["files"][path]
    if digest(raw) != identity["after_sha256"].upper():
        # Predecessors and mutations still meet the caller's original exact guard.
        return raw
    previous = json.loads(raw)
    if path.endswith("package-lock.json"):
        for row in security["changed_lock_records"]:
            current = previous["packages"][row["path"]]
            assert (
                digest(json.dumps(current, sort_keys=True, separators=(",", ":")).encode())
                == row["after_sha256"].upper()
            )
            previous["packages"][row["path"]] = row["before"]
    else:
        previous["devDependencies"]["vite"] = security["previous_vite"]
    old = (json.dumps(previous, indent=2) + "\n").encode()
    assert digest(old) == identity["before_sha256"].upper(), "D3_SECURITY_PREDECESSOR_INVALID"
    return old


def backend_security_authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (ROOT / "docs/governance/HYB2_D3_P1_BACKEND_SECURITY_SUCCESSOR.json").read_bytes()
    assert digest(raw) == "755E66EC4F5184639801FAC867BF08B7545A9944D87523908D6636EE08822332", (
        "D3_BACKEND_SECURITY_AUTHORITY_INVALID"
    )
    return cast(dict[str, Any], json.loads(raw))


def pre_d3_backend_dependency(raw: bytes) -> bytes:
    """Restore only the exact owner-approved Certifi/Pillow lock successor."""
    from tests.hybrid_workspace_security import pre_p2_dependency

    raw = pre_p2_dependency("backend/requirements/requirements-dev-py314.lock.txt", raw)
    raw = raw.replace(b"\r\n", b"\n")
    governed = backend_security_authority()
    if digest(raw) != governed["after_sha256"]:
        # All predecessor and mutated bytes still face the unchanged F8/F7 guards.
        return raw
    for record in governed["packages"].values():
        after, before = record["after_block"].encode(), record["before_block"].encode()
        assert digest(after) == record["after_block_sha256"].upper()
        assert digest(before) == record["before_block_sha256"].upper()
        assert raw.count(after) == 1
        raw = raw.replace(after, before, 1)
    after, before = governed["header_after"].encode(), governed["header_before"].encode()
    assert raw.count(after) == 1
    old = raw.replace(after, before, 1)
    assert digest(old) == governed["before_sha256"], "D3_BACKEND_SECURITY_PREDECESSOR_INVALID"
    return old
