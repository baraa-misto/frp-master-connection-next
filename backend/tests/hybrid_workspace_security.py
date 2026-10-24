"""Reverse only the exact owner-approved P2 security successor."""

import json
from typing import Any, cast

from tests.hybrid_workspace_governance import ROOT, digest

MANIFEST_SHA256 = "0EBDBA12FE00A9CF857575E1542F7C222B30FC9AA573EB2AFEC56DF135DB525B"


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (
            (ROOT / "docs/governance/HYB2_D3_P2_SECURITY_SUCCESSOR.json")
            .read_text(encoding="utf8")
            .encode()
        )
    assert digest(raw) == MANIFEST_SHA256, "P2_SECURITY_AUTHORITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def pre_p2_dependency(path: str, raw: bytes) -> bytes:
    from tests.hybrid_security_successor import pre_s1_dependency

    raw = pre_s1_dependency(path, raw)
    raw = raw.replace(b"\r\n", b"\n")
    governed = authority()
    identity = governed["files"].get(path)
    if identity is None or digest(raw) != identity["after_sha256"]:
        # The original guard still rejects every unapproved byte or pin change.
        return raw
    if path.endswith(".json"):
        previous = json.loads(raw)
        if path.endswith("package-lock.json"):
            for row in governed["changed_lock_records"]:
                assert previous["packages"][row["path"]] == row["after"]
                previous["packages"][row["path"]] = row["before"]
        else:
            for name, row in governed["frontend_direct_pins"].items():
                assert previous["devDependencies"][name] == row["after"]
                previous["devDependencies"][name] = row["before"]
        raw = (json.dumps(previous, indent=2) + "\n").encode()
    elif path.endswith("pyproject.toml"):
        assert raw.count(b"pypdf==6.21.1") == 1
        raw = raw.replace(b"pypdf==6.21.1", b"pypdf==6.19.0")
    else:
        row = governed["pypdf"]
        assert raw.count(row["after_block"].encode()) == 1
        raw = raw.replace(row["after_block"].encode(), row["before_block"].encode(), 1)
    assert digest(raw) == identity["before_sha256"], "P2_SECURITY_PREDECESSOR_INVALID"
    return raw
