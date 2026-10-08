"""Exact owner-authorized F8-G1 dependency reverse deltas; no engineering scope."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = "FA85C43240EF214E2E46B7F5C93D2DF91D13F5BF1B92CF01569D898DCD239B23"
LOCK_SHA256 = "510B445D24DD060629282B65D2ECDFE00EFABF362717EDFC5462C55D6BCF9A35"
PRE_G1_LOCK_SHA256 = "FA0A6A2C49C73E484969DE546F4A569925FA071EB9C4011A8764CC320FFBA63A"
F7_LOCK_SHA256 = "C1A1B1428B11F0A817653B29E3539DC2CBC06AD63385AA20A602C0B03CF5F3D8"
CI_SHA256 = "FA310105AFA01E48440E354D1324716E1DAC245A0BC8540185F272DA5FF02010"
BOOTSTRAP_SHA256 = "7D5B6B5583BA2FBF1FB8BA3E5A8F03D3CBF03B8FF9CD6B2321DAACBE11615B08"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest().upper()


def authority(raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (
            ROOT / "docs/governance/SHEAR01_DIRECT_OR2_F8_DEPENDENCY_SUCCESSOR.json"
        ).read_bytes()
    assert digest(raw) == MANIFEST_SHA256, "F8_G1_AUTHORITY_IDENTITY_INVALID"
    return cast(dict[str, Any], json.loads(raw))


def package_blocks(raw: bytes) -> dict[str, bytes]:
    headers = list(re.finditer(rb"(?m)^([a-z][a-z0-9-]+)==[^\n]*\n", raw))
    assert len({m.group(1) for m in headers}) == len(headers), "DUPLICATE_PACKAGE_BLOCK"
    return {
        m.group(1).decode(): raw[
            m.start() : headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        ]
        for i, m in enumerate(headers)
    }


def pre_g1_lock(raw: bytes, manifest: bytes | None = None) -> bytes:
    governed = authority(manifest)["security_successor"]
    raw = raw.replace(b"\r\n", b"\n")
    assert digest(raw) == LOCK_SHA256, "F8_G1_LOCK_IDENTITY_INVALID"
    blocks = package_blocks(raw)
    for name, record in governed["packages"].items():
        after, before = record["after_block"].encode(), record["before_block"].encode()
        assert blocks[name] == after
        assert raw.count(after) == 1
        assert digest(after) == record["after_block_sha256"]
        assert digest(before) == record["before_block_sha256"]
        raw = raw.replace(after, before)
    after, before = governed["header_after"].encode(), governed["header_before"].encode()
    assert raw.count(after) == 1
    raw = raw.replace(after, before)
    assert digest(raw) == PRE_G1_LOCK_SHA256
    return raw


def f7_lock(raw: bytes) -> bytes:
    raw = pre_g1_lock(raw)
    blocks = package_blocks(raw)
    additions = authority()["files"]["backend/requirements/requirements-dev-py314.lock.txt"][
        "added_package_blocks"
    ]
    for name, expected in additions.items():
        assert digest(blocks[name]) == expected
        assert raw.count(blocks[name]) == 1
        raw = raw.replace(blocks[name], b"")
    assert digest(raw) == F7_LOCK_SHA256
    return raw


def pre_g1_workflow(raw: bytes) -> bytes:
    governed = authority()["security_successor"]
    raw = raw.replace(b"\r\n", b"\n")
    assert digest(raw) == CI_SHA256
    steps = governed["ci_added_steps"].encode()
    assert raw.count(steps) == 1
    assert raw.count(b"--expected-tests 8568") == 1
    raw = raw.replace(steps, b"").replace(b"--expected-tests 8568", b"--expected-tests 8549")
    assert digest(raw) == governed["pre_g1_ci_sha256"]
    return raw


def pre_g1_bootstrap(raw: bytes) -> bytes:
    governed = authority()["security_successor"]["bootstrap"]
    raw = raw.replace(b"\r\n", b"\n")
    assert digest(raw) == BOOTSTRAP_SHA256
    for record in governed["replacements"]:
        after, before = record["after"].encode(), record["before"].encode()
        assert raw.count(after) == 1
        raw = raw.replace(after, before)
    assert digest(raw) == governed["before_sha256"]
    return raw
