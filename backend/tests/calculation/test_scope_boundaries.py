"""Architecture and prohibited-scope checks for the Stage 2.1B engine."""

import ast
import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

import pytest

from tests.calculation.stage_4_5_scope_authority import frozen_stage45_entries

STAGE_2_3_FROZEN_FRONTEND_SRC_TREE = "df664801ea31a5a33e582e886dc787bf4f9be8aa"
STAGE_2_4C_REJECTED_INTERIM_FRONTEND_SRC_TREE = "cf71cf158afd3525aba0849e207746b6a6842f73"
STAGE_2_4C_R1_HISTORICAL_FRONTEND_SRC_TREE = "8f8b5c65559f162363d3ea2bb58f2e21cf18ba9d"
STAGE_2_4C_R2_HISTORICAL_FRONTEND_SRC_TREE = "f95396ff7ce5604f08f40b04b7b5e216271672c6"
STAGE_2_4C_R3_HISTORICAL_FRONTEND_SRC_TREE = "deb93d01646580ae62c9f90a507446d84019bd87"
STAGE_2_5C_R1_HISTORICAL_FRONTEND_SRC_TREE = "035af7c9c44c49914c63c68edf6ec4eea5521bcf"
STAGE_2_5C_R2_HISTORICAL_FRONTEND_SRC_TREE = "cd25332af05c101aa008934a7b900d8c220938f3"
STAGE_2_6B_HISTORICAL_FRONTEND_SRC_TREE = "b73469788561bebf61262f2211b6e39c3e3a699c"
STAGE_3_2_HISTORICAL_FRONTEND_SRC_TREE = "241dc569cb17aef5bd05eba604962607b730411f"
STAGE_3_2_R2_HISTORICAL_FRONTEND_SRC_TREE = "b7f21b032d2fd075c2428a5cbab9f17530690c3b"
STAGE_3_2_R4_HISTORICAL_FRONTEND_SRC_TREE = "fb936e68a3aaf3c3d38838e40213dff3770dd970"
STAGE_3_2_R6_HISTORICAL_FRONTEND_SRC_TREE = "40956420c22c42910a8a2cbe82c74ed2e6a5f407"
STAGE_3_2_R9_HISTORICAL_FRONTEND_SRC_TREE = "9dec6be5d41dc24894bb3f08bd1652c23b431bbb"
STAGE_3_2_R10_HISTORICAL_FRONTEND_SRC_TREE = "a1ea0c058bd3493db4cf348d0f945e99c79f059f"
STAGE_3_2_R11_HISTORICAL_FRONTEND_SRC_TREE = "3127d32683eb25a4f68bf0b00e75722aa40855e2"
STAGE_3_2_R12_HISTORICAL_FRONTEND_SRC_TREE = "bc847f9b22d371b7ae5256f133c95e452bce39ef"
STAGE_3_2_R13_HISTORICAL_FRONTEND_SRC_TREE = "4809c59244f2bbf0e57bd334931f1b1f06368334"
STAGE_3_2_R14C_HISTORICAL_FRONTEND_SRC_TREE = "fbbf52fa5ad719a6f3e434a19df74c236cd25dfb"
STAGE_3_3A_HISTORICAL_FRONTEND_SRC_TREE = "aec3e7f834b76fdc73454c37f673930542c72cba"
STAGE_3_3A_R1_HISTORICAL_FRONTEND_SRC_TREE = "2aed42f26fafe3434a831336a70c366463ef77eb"
STAGE_3_3A_R3_HISTORICAL_FRONTEND_SRC_TREE = "10f8ed18bc8a571a7e243e3e77df6b4a99f539af"
STAGE_3_3A_R4_HISTORICAL_FRONTEND_SRC_TREE = "c6056618e25c6ff0c6205cdcf6503f3d85a633b9"
STAGE_3_3B_HISTORICAL_FRONTEND_SRC_TREE = "d51bd05103a2530ea3bea9bdb10e020cc18deb57"
STAGE_3_3C2_R1_HISTORICAL_FRONTEND_SRC_TREE = "abf01a3941c320bcf347e05fc9c0cce582767120"
STAGE_3_3C2_HISTORICAL_FRONTEND_SRC_TREE = "592d322a3c3dfd19aa9d5d080f17642293653a30"
STAGE_3_3C3_HISTORICAL_FRONTEND_SRC_TREE = "3a8b4755de77a778641dd5869329321ec2370dcd"
STAGE_3_3C3_R1_HISTORICAL_FRONTEND_SRC_TREE = "ea62799a02b41c30dbc25c9ad250a318aba953ae"
STAGE_3_4A_HISTORICAL_FRONTEND_SRC_TREE = "1783fe6165d89328f8e92bb6a9828906a5f41521"
STAGE_3_4A_R2_HISTORICAL_FRONTEND_SRC_TREE = "6f75da7944281c4e4b78af40934738d9fa5404f2"
STAGE_3_4B_HISTORICAL_FRONTEND_SRC_TREE = "21676d8011c07d804fb334393499cfd42145849d"
STAGE_3_5A_HISTORICAL_FRONTEND_SRC_TREE = "8ce23b8990cb1bc5f682bde92d686c2a1cd4c46e"
STAGE_3_5A_R1_HISTORICAL_FRONTEND_SRC_TREE = "84dd59f2e83f21d2d68bd59addcb0749db7d64eb"
STAGE_3_5A_R2_ACTIVE_FRONTEND_SRC_TREE = "134db42fcb47108fdc619079724f4c046c52dcbd"
STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB = "b753abd55004168eee5844879f0596d435fe4b5a"
STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB = "f2a594dae8c871d5c1c78e69f1023d6e77adf6e6"
STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB = (
    "ae1831268db42005517343bf555f054a673ae520"
)
STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_SHA256 = (
    "43C85D832FEA4DCEA7A35E2D87C4AABDCBE08FEC64A2C2C6B716240FB3C601E4"
)
STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_SHA256 = (
    "20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254"
)

_NANOID_HISTORICAL_METADATA_BLOCK = (
    b'    "node_modules/nanoid": {\n'
    b'      "version": "3.3.17",\n'
    b'      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.17.tgz",\n'
    b'      "integrity": "sha512-xQLf0A3HOMlgHq0n247/LRuAOYmB7dXJ/'
    b'DvAxGvsSBij45XtBSmQycu+F8ODbHwns/XyFZagyL1+J0Offw1E0g==",\n'
)
_NANOID_SUCCESSOR_METADATA_BLOCK = (
    b'    "node_modules/nanoid": {\n'
    b'      "version": "3.3.18",\n'
    b'      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",\n'
    b'      "integrity": "sha512-DTg4MJbGMWkfi6VZFdNt2/caMbQy4Ou+Op/'
    b'hJQvGEWcnVfoA1QA+xzRKAzw9jD6+GVOOeYr/mIcuDSdug6F6+w==",\n'
)
_NANOID_METADATA_FIELDS = ("version", "resolved", "integrity")

_FROZEN_FRONTEND_CORE_GIT_OBJECTS = (
    ("frontend/src", STAGE_2_3_FROZEN_FRONTEND_SRC_TREE),
    ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
)
_ACTIVE_FRONTEND_CORE_GIT_OBJECTS = (
    ("frontend/src", STAGE_3_5A_R2_ACTIVE_FRONTEND_SRC_TREE),
    ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
)
_APPROVED_PACKAGE_LOCK_BLOBS = (
    STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB,
    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
)

# Stage 4.3 security successor: old authority is never replaced by the new hashes.
# The exact reverse delta below reconstructs the already-controlled historical
# Git bytes in depth-one/no-tags clones; both SHA-256 and Git blob must match.
_SECURITY_FILES = (
    "frontend/package.json",
    "frontend/package-lock.json",
    "backend/tests/calculation/test_scope_boundaries.py",
    "backend/tests/calculation/test_stage_3_2_freeze_manifest.py",
    "backend/tests/application/test_wi_wall_moment.py",
    "backend/tests/calculation/test_stage_3_5_freeze_manifest.py",
    "backend/tests/calculation/test_stage_3_6_freeze_manifest.py",
    "backend/tests/calculation/test_stage_3_7_freeze_manifest.py",
    "backend/tests/calculation/test_stage_4_1a_freeze_manifest.py",
)
_SECURITY_PROTECTED_SHA256 = "968847BF52C927427D5D71F31FD1395E04892697BB109BECDADD2070AF1BDD2E"
_SECURITY_COMMIT = "513e1c9150e63206e432a8d2f971617b6ed9c203"
# Owner-authorized Windows maintenance: two exact whole-file reverse deltas.
# Each successor differs only at its one named test's closing timeout argument.
# These are not open-ended frontend-test exceptions; historical pins stay fixed.
_TIMEOUT_SUCCESSOR_BLOBS = {
    "frontend/tests/wiFrpSupportMomentFrontend.test.tsx": (
        "b46edf306ead012316729d2e74cadb664d8f34ff",
        "9f1253edcd49c04d410be9077bfd02648d0bd9f7",
    ),
    "frontend/tests/ClipAngleConnectorWorkspace.test.tsx": (
        "31efccd09548fd4807585c6ac2791d0ace1d39ed",
        "78e1443ff8254db8f3bb52f8aa8eafbf361b504f",
    ),
}
# Owner-authorized Stage 4.3 freeze successor: exact paths, never a docs/** exemption.
# These immutable historical Git entries restore the original scope digest even
# in depth-one/no-tags clones. Current governance bytes are not historical bytes.
_SECURITY_GOVERNANCE_BLOBS = {
    "HANDOFF_MANIFEST.json": "2bee04efb9ea1f092c7ce6400be64d252c1bb77a",
    "README.md": "2d1fdc3a3a97f1086ae789f477f30a562ff50650",
    "docs/architecture/DATA_VERSIONING_AND_REPRODUCIBILITY.md": (
        "0d047e3e121e3719e278e3542c0ea359414d8334"
    ),
    "docs/governance/ARTIFACT_AND_VERSION_REGISTER.md": "b3b7961b10bca5787de9fa4bbc84569a466c2060",
    "docs/governance/DECISION_REGISTER.md": "5e894b81add64a4bea8c6f116bd62a6677b3b361",
    "docs/product/DEVELOPMENT_ROADMAP.md": "fbbaa5aadbf46dcd2df77fef10c6ca85293d0f5b",
    "docs/qa/INTEGRATED_QA_AND_CI.md": "90b5842b579238ef414403f5f80c189adf8cff85",
    "docs/qa/VALIDATION_AND_QA_PLAN.md": "15affd33bb4730fb5a502c5dd55efb7b22255703",
}
_FREEZE_NEW_GOVERNANCE = (
    "docs/governance/STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_FREEZE_MANIFEST.json",
    "docs/qa/STAGE_4_3_FREEZE.md",
)
# Earlier security exceptions are not open-ended permission to modify them again.
# Only this test file has new tests-only successor authorization.
_SECURITY_SUCCESSOR_PROTECTED_BLOBS = {
    "frontend/package.json": "a54eedc3d61d8d822ebd1a9a0c2ca52a463eafc2",
    "frontend/package-lock.json": "d0e5604e9d2295475574b08b5cc99b0055b08827",
    "backend/tests/application/test_wi_wall_moment.py": "48e21b86e03e7fc82aac04d9d806638ab503c855",
    "backend/tests/calculation/test_stage_3_2_freeze_manifest.py": (
        "2f3b41faa734e5f9d4c3fe1ff06f3b350f18ea55"
    ),
    "backend/tests/calculation/test_stage_3_5_freeze_manifest.py": (
        "17271206f55ca80d771175362f06e9a56cb21d29"
    ),
    "backend/tests/calculation/test_stage_3_6_freeze_manifest.py": (
        "f98a7767d1d99064ebe1d3243ccd8e27f6529f0a"
    ),
    "backend/tests/calculation/test_stage_3_7_freeze_manifest.py": (
        "ddd539851eccda4c82ba964c8df73de7dde78fd5"
    ),
    "backend/tests/calculation/test_stage_4_1a_freeze_manifest.py": (
        "0598900a4a5f10caac6a9db67f732bcd4df00966"
    ),
}
_SECURITY_HISTORICAL_TEST_PATHS = (
    "backend/tests/calculation/test_stage_3_2_freeze_manifest.py",
    "backend/tests/calculation/test_stage_3_5_freeze_manifest.py",
    "backend/tests/calculation/test_stage_3_6_freeze_manifest.py",
    "backend/tests/calculation/test_stage_3_7_freeze_manifest.py",
)
_FROZEN_DEPENDENCIES = {
    "frontend/package.json": (
        STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB,
        "1085F25B94819ED98EEE10739CF4B419F39BD626CC654699B0380B26341F4359",
    ),
    "frontend/package-lock.json": (
        STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
        STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_SHA256,
    ),
}
_SECURITY_DEPENDENCY_SHA256 = {
    "frontend/package.json": "1F885516E47D988B495E01C7E29BC49B254FED681A9B9911501DA7581900E4BF",
    "frontend/package-lock.json": (
        "5F195B77E2749DBDD78C8D94718EA5A794E566AD123D83EDCCBF3EEA9B15F766"
    ),
}
_SECURITY_REVERSE_DELTA = (
    (b"4.1.11", b"4.1.10"),
    (
        b'"node_modules/js-yaml": {\n      "version": "4.3.2"',
        b'"node_modules/js-yaml": {\n      "version": "4.3.1"',
    ),
    (
        b"https://registry.npmjs.org/js-yaml/-/js-yaml-4.3.2.tgz",
        b"https://registry.npmjs.org/js-yaml/-/js-yaml-4.3.1.tgz",
    ),
    (
        b"sha512-8MVGEFnJIcdGjcbfKmeq8z0pZHH0JlVtoVZH9Q/qwUp6wyFnEJUBMrw9DCaj+ra3vShGmhavjalMIhPNxZAUcw==",
        b"sha512-IM49HmthevbgAO4anp1hwtoT9wYe59w0LR00gr+eagHE+ZJ5lK4sLPeO0ubgoJcwLk6dehU3R24N+FbEEKDc8g==",
    ),
    (
        b"sha512-VX2x5vNJXET47KAFzwERI+KRMtTTCSWTfSMKsW7JsUsXV4psq++e3DvZpuTDOpHcxytiDs6p2nhVb2tVDiiUYw==",
        b"sha512-YsCn+qAk1GWjQOWFEsEcL2gNQ0zmVmQu3T03qP6UyjhtmdtwtbuI+DASn/7iQB3HGTXkdBwGddzxPlmiql5vlA==",
    ),
    (
        b"sha512-2XJVD55d1o5AZous5CCGKS74g/riOj9odEt2bQpCVZeblHyHdnMeFl4jl0XjU21stf4mbjUkew2eXQZt65g5CQ==",
        b"sha512-v0xaezt+DKEmKfaxg133ldzADrwLGd7Ze1MfQQTYfvs8OqZIwbxyxaYURivwV7sWy5fqn3rH5uOrSp07bp44Ow==",
    ),
    (
        b"sha512-yiZzPbGTS9Sr/JpFl8zHrcIkAofNbFV6k21vIgQN/cY/oxZeXhJv5sc/MBJ5jFKWmWs+oJHw0UXLZjmf931+Vw==",
        b"sha512-W1HsjSH4MXQ9YfmmhLAoIYf1HRfekQCGngeIgcei6MP5QQGWUe0gkopdZQaVCFO+JDJMrAJGwa5pRpNpvy4P8Q==",
    ),
    (
        b"sha512-LztvUgdwMNJMIkj3hQnnxiC2Xy1zNxq928W/xhjCLaNCzqTZOudjwbQf6v9IntZGPw132i2Lq2rgTRZHD3JHNw==",
        b"sha512-IKI6kpIH+LmpROplyLwBBaCfMgOZOMsygVa6BARD6ahA04VRuJSa6OaVG7kRvSEMD870Vd91rSSw0eegtWyLGg==",
    ),
    (
        b"sha512-pN7ikn1ON7h8ee4gIAp4AzyK+zBtJPzVbqOgu5LCEh4VaJVbPQcgYQYJIMGQPXVeJJq1fnfazis7a5pFNPahog==",
        b"sha512-xRkfOT1qpTAi/Ti4Y1LtfRc3kEuqxGw59eN2jN9pRWMtS/XDevekhcFSqvQqjUNGksfjMJu3Y+oJ+4Ypn2OaJw==",
    ),
    (
        b"sha512-apNa/prQy2qCeywhnixOHPRCgGNhvg7T4Dapfl1GahLp/R+uhBm5cPyFoNVyqsNd2h1nJxL6BqqdIjiABL60YA==",
        b"sha512-PLf/Ugvoq5wO/b4rwYCR1h2PSIdXz7wnkQFMiUpLdtM7l6pqVFcQIBEHyT1+l+cj7mNwAfZHzqXqDyjvOuwbDw==",
    ),
    (
        b"sha512-zTCVGpyFsGWBhllOyKlTw/vnr6D9qxsfSDyfbyZmTyjHw5N/VuvzHpHoQjm2ZJzn4RJgx5w4r7V0er69CmLgPQ==",
        b"sha512-fy9am/HWxbaGt/Sawrp90vt6Y6jQwf1RX77cz3uwoJwJVMli/e1IEwRPnMNJ7vKfPTwo0diXifkpPvwH9v7nGA==",
    ),
    (
        b"sha512-SFNOvSJ+Dgf/9An904Yx+CgSlIPCkIpao4qo51lpee25TIRejdH3rhR4EZMGoNx3/TP3O+wzWuiTFl4sqbltzA==",
        b"sha512-CY6crGq313MX8GkwvB7tzgp99vjQxY1++5y10/BKN/GUfHqWaOGQMNZkBvqSzsZKWk/ijwHlWzzkLulsGHhjWQ==",
    ),
    (
        b"sha512-fhACrNXUidIbGSBr5FlbuBkO7VWC1ZyLl0DO4CU2DrQoAPxX84Ysxs+HeGQpii5lZWV1Q4gBZTTu49mF+A6Edw==",
        b"sha512-R9jUTe5S4Qb0HCd4TNqpC7oGcrMssMRGXLW80ubjWsW9VH5GF8y1Y0SFLY9AbqSk6nt0PnOx4H4WNJYZ13GUPw==",
    ),
)


def _assert_frozen_dependency_bytes(path: str, raw: bytes) -> None:
    expected_blob, expected_sha = _FROZEN_DEPENDENCIES[path]
    assert hashlib.sha256(raw).hexdigest().upper() == expected_sha, "historical SHA-256"
    assert (
        hashlib.sha1(  # noqa: S324 - Git object identity, not security hashing
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        == expected_blob
    ), "historical Git blob"


def _restore_frozen_dependency_bytes(path: str, raw: bytes) -> bytes:
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != _FROZEN_DEPENDENCIES[path][1]:
        assert digest == _SECURITY_DEPENDENCY_SHA256[path], "unauthorized dependency successor"
        for successor, historical in _SECURITY_REVERSE_DELTA:
            raw = raw.replace(successor, historical)
    _assert_frozen_dependency_bytes(path, raw)
    return raw


def _historical_dependency_bytes(repository_root: Path, path: str) -> bytes:
    blob = _FROZEN_DEPENDENCIES[path][0]
    available = (
        subprocess.run(  # noqa: S603 - immutable blob selected from fixed identity map
            ["git", "cat-file", "-e", blob],  # noqa: S607
            cwd=repository_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )
    command = ["git", "cat-file", "blob", blob] if available else ["git", "show", f"HEAD:{path}"]
    raw = subprocess.run(  # noqa: S603 - fixed path/immutable identity map above
        command, cwd=repository_root, check=True, capture_output=True
    ).stdout
    if not available:
        raw = _restore_frozen_dependency_bytes(path, raw)
    _assert_frozen_dependency_bytes(path, raw)
    return raw


def _assert_security_dependencies(repository_root: Path) -> None:
    for path in _FROZEN_DEPENDENCIES:
        # Git-aware text checkout normalization; the authoritative pins are LF blobs.
        raw = (repository_root / path).read_text(encoding="utf-8").encode()
        assert hashlib.sha256(raw).hexdigest().upper() == _SECURITY_DEPENDENCY_SHA256[path]
        _restore_frozen_dependency_bytes(path, raw)


def _assert_security_protected_entries(entries: str) -> None:
    retained = [line for line in entries.splitlines() if line.split("\t")[1] not in _SECURITY_FILES]
    digest = hashlib.sha256(("\n".join(retained) + "\n").encode()).hexdigest().upper()
    assert digest == _SECURITY_PROTECTED_SHA256, "protected content outside nine authorized files"


def _restore_historical_security_scope(entries: str) -> str:
    """Separate registered candidate scope from immutable historical security scope."""
    from tests.calculation.stage_4_4_scope_authority import stage44_predecessor_entries
    from tests.calculation.stage_4_5_scope_authority import stage45_predecessor_entries

    entries = stage45_predecessor_entries(entries)
    entries = stage44_predecessor_entries(entries)
    lines = entries.splitlines()
    indexed = {line.split("\t")[1]: line for line in lines}
    assert len(indexed) == len(lines), "duplicate scope path"
    for path, blob in _SECURITY_SUCCESSOR_PROTECTED_BLOBS.items():
        assert indexed.get(path) == f"100644 blob {blob}\t{path}", "protected security successor"
    for path, (historical_blob, timeout_blob) in _TIMEOUT_SUCCESSOR_BLOBS.items():
        assert indexed.get(path) in {
            f"100644 blob {historical_blob}\t{path}",
            f"100644 blob {timeout_blob}\t{path}",
        }, "protected test: only the exact timeout successor is authorized"
        indexed[path] = f"100644 blob {historical_blob}\t{path}"
    for path, blob in _SECURITY_GOVERNANCE_BLOBS.items():
        assert indexed.get(path, "").startswith("100644 blob "), "missing/unsafe governance path"
        indexed[path] = f"100644 blob {blob}\t{path}"
    for path in _FREEZE_NEW_GOVERNANCE:
        if path in indexed:
            assert indexed[path].startswith("100644 blob "), "unsafe new governance path"
            del indexed[path]
    historical = "\n".join(indexed[path] for path in sorted(indexed)) + "\n"
    _assert_security_protected_entries(historical)
    return historical


def _available_historical_security_entries(repository_root: Path) -> str | None:
    available = subprocess.run(  # noqa: S603 - immutable accepted commit, read-only Git query
        ["git", "cat-file", "-e", f"{_SECURITY_COMMIT}^{{commit}}"],  # noqa: S607
        cwd=repository_root,
        capture_output=True,
        check=False,
    )
    if available.returncode != 0:
        return None
    return subprocess.run(  # noqa: S603 - immutable accepted commit, read-only Git query
        ["git", "ls-tree", "-r", _SECURITY_COMMIT],  # noqa: S607
        cwd=repository_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout


def _assert_security_scope(repository_root: Path, current_entries: str) -> str:
    restored = _restore_historical_security_scope(current_entries)
    historical = _available_historical_security_entries(repository_root)
    if historical is None:
        from tests.calculation.stage_4_4_scope_authority import SECURITY_COMMIT, evidence

        # Actual pre-maintenance historical snapshot plus original digest; never HEAD.
        _assert_security_protected_entries(evidence()[SECURITY_COMMIT]["entries"])
        _assert_security_protected_entries(restored)
        return "reconstructed_historical_scope"
    _assert_security_protected_entries(historical)
    return "historical_object"


def _assert_historical_test_record(repository_root: Path, path: str, expected_sha: str) -> str:
    """Verify inherited test identity, never the authorized successor test bytes.

    The already-frozen Stage 4.1 manifest retains these exact earlier SHA/blob
    records. Its pinned whole-file and record hashes authenticate manifest-only
    shallow resolution; available historical objects additionally require exact
    bytes. This is the existing family audit's object/manifest-only contract.
    """
    from tests.calculation import (
        test_stage_4_1_beam_moment_splice_family_freeze_manifest as history,
    )

    assert path in _SECURITY_HISTORICAL_TEST_PATHS, "not an authorized historical test"
    raw, manifest = history._manifest(repository_root)
    history._assert_bytes(raw)
    history._assert_contract(manifest)
    records = [record for record in history._all_records(manifest) if record["path"] == path]
    assert len(records) == 1
    record = records[0]
    assert record["sha256"] == expected_sha, "historical expected SHA-256"
    blobs = history._blob_map(repository_root, [record["git_blob"]])
    if record["git_blob"] not in blobs:
        return "manifest_only"
    frozen = blobs[record["git_blob"]]
    assert hashlib.sha256(frozen).hexdigest().upper() == expected_sha, "historical object SHA-256"
    assert (
        hashlib.sha1(
            b"blob " + str(len(frozen)).encode() + b"\0" + frozen, usedforsecurity=False
        ).hexdigest()
        == record["git_blob"]
    ), "historical object Git blob"
    return "object"


def _security_working_tree_entries(repository_root: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="frp-security-index-") as temporary_directory:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(temporary_directory) / "index")
        for command in (["git", "read-tree", "HEAD"], ["git", "add", "-A"]):
            subprocess.run(  # noqa: S603 - fixed Git commands, temporary index only
                command, cwd=repository_root, check=True, env=environment, capture_output=True
            )
        tree = subprocess.run(
            ["git", "write-tree"],  # noqa: S607
            cwd=repository_root,
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return subprocess.run(  # noqa: S603 - tree returned by the fixed Git write-tree command
            ["git", "ls-tree", "-r", tree],  # noqa: S607
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout


def test_stage_4_3_security_successor_changes_only_authorized_files() -> None:
    root = Path(__file__).parents[3]
    _assert_security_dependencies(root)
    _assert_security_scope(root, frozen_stage45_entries())


@pytest.mark.parametrize("frp_timeout", [False, True])
@pytest.mark.parametrize("clip_timeout", [False, True])
def test_only_exact_timeout_successors_preserve_original_scope_digest(
    frp_timeout: bool, clip_timeout: bool
) -> None:
    root = Path(__file__).parents[3]
    from tests.calculation.stage_4_4_scope_authority import BASELINE_COMMIT, evidence

    # Counterfactual timeout variants belong to the historical maintenance scope,
    # not today's product. The current successor inventory is checked separately.
    entries = evidence()[BASELINE_COMMIT]["entries"]
    replacements = {
        path: f"100644 blob {blobs[int(enabled)]}\t{path}"
        for (path, blobs), enabled in zip(
            _TIMEOUT_SUCCESSOR_BLOBS.items(), (frp_timeout, clip_timeout), strict=True
        )
    }
    projected = "\n".join(
        replacements.get(line.split("\t")[1], line) for line in entries.splitlines()
    )
    historical = _restore_historical_security_scope(projected)
    _assert_security_protected_entries(historical)
    _assert_security_scope(root, projected)


@pytest.mark.parametrize("path", tuple(_TIMEOUT_SUCCESSOR_BLOBS))
def test_timeout_successor_bytes_are_exactly_one_local_argument(path: str) -> None:
    root = Path(__file__).parents[3]
    raw = (root / path).read_text(encoding="utf-8").encode()
    historical_blob, timeout_blob = _TIMEOUT_SUCCESSOR_BLOBS[path]
    # A full-file pin plus the unique closing-line replacement proves that no
    # assertion, interaction, expected value or other timeout was changed.
    marker = b"\n  }, 15000);"
    assert raw.count(marker) == 1
    assert _git_blob_id(root, raw) == timeout_blob
    restored = raw.replace(marker, b"\n  });", 1)
    assert _git_blob_id(root, restored) == historical_blob


@pytest.mark.parametrize("path", tuple(_TIMEOUT_SUCCESSOR_BLOBS))
@pytest.mark.parametrize("mutation", ["assertion", "other_content", "timeout", "delete", "mode"])
def test_timeout_allowance_rejects_every_other_test_change(path: str, mutation: str) -> None:
    root = Path(__file__).parents[3]
    raw = (root / path).read_text(encoding="utf-8").encode()
    if mutation == "assertion":
        assert b"expect(" in raw
        raw = raw.replace(b"expect(", b"notAnAssertion(", 1)
    elif mutation == "timeout":
        raw = raw.replace(b"\n  }, 15000);", b"\n  }, 16000);", 1)
    else:
        raw += b"\n// unapproved content\n"
    entries = frozen_stage45_entries()
    lines = [line for line in entries.splitlines() if line.split("\t")[1] != path]
    if mutation != "delete":
        mode = "100755" if mutation == "mode" else "100644"
        lines.append(f"{mode} blob {_git_blob_id(root, raw)}\t{path}")
    with pytest.raises(AssertionError, match="protected test"):
        _assert_security_scope(root, "\n".join(lines))


@pytest.mark.parametrize("path", tuple(_FROZEN_DEPENDENCIES))
def test_security_successor_preserves_exact_historical_dependency_bytes(path: str) -> None:
    root = Path(__file__).parents[3]
    raw = (root / path).read_text(encoding="utf-8").encode()
    assert raw != _historical_dependency_bytes(root, path)
    assert _restore_frozen_dependency_bytes(path, raw) == _historical_dependency_bytes(root, path)
    with pytest.raises(AssertionError, match="unauthorized dependency successor"):
        _restore_frozen_dependency_bytes(path, raw + b" ")


@pytest.mark.parametrize("path", tuple(_FROZEN_DEPENDENCIES))
@pytest.mark.parametrize("mutation", ["append", "truncate", "replace"])
def test_frozen_dependency_tampering_still_fails(path: str, mutation: str) -> None:
    raw = _historical_dependency_bytes(Path(__file__).parents[3], path)
    changed = raw + b" " if mutation == "append" else raw[:-1] if mutation == "truncate" else b"{}"
    with pytest.raises(AssertionError, match="historical SHA-256"):
        _assert_frozen_dependency_bytes(path, changed)


@pytest.mark.parametrize("mutation", ["content", "delete", "rename", "add"])
def test_security_scope_rejects_unrelated_changes(mutation: str) -> None:
    entries = _restore_historical_security_scope(frozen_stage45_entries())
    lines = entries.splitlines()
    index = next(i for i, line in enumerate(lines) if line.endswith("\tREADME.md"))
    if mutation == "content":
        lines[index] = "100644 blob " + "0" * 40 + "\tREADME.md"
    elif mutation == "delete":
        del lines[index]
    elif mutation == "rename":
        lines[index] = lines[index].replace("README.md", "README-renamed.md")
    else:
        lines.append("100644 blob " + "0" * 40 + "\tunapproved.txt")
    with pytest.raises(AssertionError, match="protected content"):
        _assert_security_protected_entries("\n".join(lines))


@pytest.mark.parametrize("mode", ["object", "tagless", "tampered_historical_object"])
def test_security_scope_historical_authority_is_exact_and_tagless_portable(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[3]
    entries = frozen_stage45_entries()
    historical = _restore_historical_security_scope(entries)
    assert _SECURITY_PROTECTED_SHA256 == (
        "968847BF52C927427D5D71F31FD1395E04892697BB109BECDADD2070AF1BDD2E"
    )
    if mode == "tampered_historical_object":
        historical = historical.replace(_SECURITY_GOVERNANCE_BLOBS["README.md"], "0" * 40)
    monkeypatch.setattr(
        "tests.calculation.test_scope_boundaries._available_historical_security_entries",
        lambda _root: None if mode == "tagless" else historical,
    )
    if mode == "tampered_historical_object":
        with pytest.raises(AssertionError, match="protected content"):
            _assert_security_scope(root, entries)
    else:
        assert _assert_security_scope(root, entries) == (
            "reconstructed_historical_scope" if mode == "tagless" else "historical_object"
        )


@pytest.mark.parametrize("path", [*_SECURITY_GOVERNANCE_BLOBS, *_FREEZE_NEW_GOVERNANCE])
def test_only_authorized_freeze_governance_can_succeed_historical_security_scope(path: str) -> None:
    from tests.calculation.stage_4_4_scope_authority import BASELINE_COMMIT, evidence

    root = Path(__file__).parents[3]
    # This is the original governance counterfactual, not permission to mutate
    # previously frozen governance in the current Stage 4.5 candidate.
    entries = evidence()[BASELINE_COMMIT]["entries"]
    lines = [line for line in entries.splitlines() if line.split("\t")[1] != path]
    lines.append(f"100644 blob {'1' * 40}\t{path}")
    _assert_security_scope(root, "\n".join(lines))


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/frp_master_connection/__init__.py",
        "frontend/src/main.tsx",
        "frontend/package.json",
        "frontend/package-lock.json",
        "backend/tests/calculation/test_stage_3_2_freeze_manifest.py",
        "frontend/tests/multiRowWorkspace.test.tsx",
        ".github/workflows/ci.yml",
        "docs/governance/unapproved.json",
        "docs/engineering/unapproved.md",
    ],
)
@pytest.mark.parametrize("mutation", ["content", "delete", "rename", "add"])
def test_governance_successor_does_not_exempt_other_current_scope(path: str, mutation: str) -> None:
    root = Path(__file__).parents[3]
    entries = frozen_stage45_entries()
    lines = entries.splitlines()
    existing = next((line for line in lines if line.split("\t")[1] == path), None)
    if existing is not None:
        lines.remove(existing)
    if mutation != "delete" or existing is None:
        target = f"{path}.unapproved" if mutation in {"rename", "add"} else path
        lines.append(f"100644 blob {'0' * 40}\t{target}")
    with pytest.raises(AssertionError, match="protected"):
        _assert_security_scope(root, "\n".join(lines))


def test_governance_scope_cannot_hide_missing_or_duplicate_records() -> None:
    from tests.calculation.stage_4_4_scope_authority import BASELINE_COMMIT, evidence

    entries = evidence()[BASELINE_COMMIT]["entries"]
    lines = entries.splitlines()
    readme = next(line for line in lines if line.endswith("\tREADME.md"))
    with pytest.raises(AssertionError, match="duplicate"):
        _restore_historical_security_scope(entries + readme + "\n")
    with pytest.raises(AssertionError, match="missing/unsafe"):
        _restore_historical_security_scope("\n".join(line for line in lines if line != readme))
    with pytest.raises(AssertionError, match="unsafe new"):
        _restore_historical_security_scope(
            "\n".join(line for line in lines if not line.endswith(f"\t{_FREEZE_NEW_GOVERNANCE[0]}"))
            + f"\n120000 blob {'0' * 40}\t{_FREEZE_NEW_GOVERNANCE[0]}\n"
        )


@pytest.mark.parametrize("path", _SECURITY_HISTORICAL_TEST_PATHS)
@pytest.mark.parametrize(
    "mode", ["available", "manifest_only", "corrupt_object", "corrupt_manifest"]
)
def test_inherited_test_identity_is_exact_and_tagless_portable(
    path: str, mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.calculation import (
        test_stage_4_1_beam_moment_splice_family_freeze_manifest as history,
    )

    root = Path(__file__).parents[3]
    raw, manifest = history._manifest(root)
    record = next(record for record in history._all_records(manifest) if record["path"] == path)
    expected = record["sha256"]
    # The actual authorized successor differs; its bytes cannot become history.
    assert hashlib.sha256((root / path).read_bytes()).hexdigest().upper() != expected
    if mode == "manifest_only":
        monkeypatch.setattr(history, "_blob_map", lambda _root, _ids: {})
    elif mode == "corrupt_object":
        monkeypatch.setattr(
            history,
            "_blob_map",
            lambda _root, _ids: {record["git_blob"]: b"tampered historical content"},
        )
    elif mode == "corrupt_manifest":
        monkeypatch.setattr(history, "_manifest", lambda _root: (raw + b"\n", manifest))
    if mode.startswith("corrupt"):
        with pytest.raises(AssertionError):
            _assert_historical_test_record(root, path, expected)
    else:
        resolution = _assert_historical_test_record(root, path, expected)
        assert resolution in {"object", "manifest_only"}
        if mode == "manifest_only":
            assert resolution == "manifest_only"
        with pytest.raises(AssertionError, match="historical expected SHA-256"):
            _assert_historical_test_record(root, path, "0" * 64)


def test_historical_test_resolution_cannot_exempt_unrelated_current_files() -> None:
    with pytest.raises(AssertionError, match="not an authorized historical test"):
        _assert_historical_test_record(Path(__file__).parents[3], "README.md", "0" * 64)


def _calculation_sources() -> tuple[Path, ...]:
    root = Path(__file__).parents[2] / "src" / "frp_master_connection" / "calculation"
    return tuple(sorted(root.glob("*.py")))


def test_stage_2_4a_modules_contain_plans_but_no_multirow_resistance_executor() -> None:
    prohibited_names: list[str] = []
    stage_2_4a_sources = {
        "block_shear_planning.py",
        "multirow.py",
        "multirow_fingerprint.py",
    }
    for source in (item for item in _calculation_sources() if item.name in stage_2_4a_sources):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                ("calculate_", "evaluate_", "execute_")
            ):
                prohibited_names.append(f"{source.name}:{node.lineno}:{node.name}")
    assert prohibited_names == []


def test_calculation_package_does_not_use_binary_math_pi() -> None:
    prohibited_math: list[str] = []
    for source in _calculation_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "math"
                and node.attr == "pi"
            ):
                prohibited_math.append(f"{source.name}:{node.lineno}:math.pi")
    assert prohibited_math == []


def test_production_calculation_package_has_no_golden_fixture_dependency() -> None:
    references = {
        source.name: source.read_text(encoding="utf-8")
        for source in _calculation_sources()
        if "calculation_slice_1_rc2.json" in source.read_text(encoding="utf-8")
        or "calculation_slice_2_rc1.json" in source.read_text(encoding="utf-8")
        or "tests.golden" in source.read_text(encoding="utf-8")
    }
    assert references == {}


def test_production_calculation_package_has_no_framework_or_persistence_dependency() -> None:
    prohibited_import_roots = {
        "fastapi",
        "sqlalchemy",
        "alembic",
        "pydantic",
        "starlette",
    }
    imports: list[str] = []
    for source in _calculation_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(
                    f"{source.name}:{node.lineno}:{alias.name}"
                    for alias in node.names
                    if alias.name.split(".")[0] in prohibited_import_roots
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.split(".")[0] in prohibited_import_roots
            ):
                imports.append(f"{source.name}:{node.lineno}:{node.module}")
    assert imports == []


def test_no_pdf_is_tracked_as_backend_calculation_source() -> None:
    repository_root = Path(__file__).parents[3]
    assert tuple(repository_root.rglob("*.pdf")) == ()


def _canonical_git_object_manifest(
    entries: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    canonical: list[tuple[str, str]] = []
    for raw_path, object_id in entries:
        path = PurePosixPath(raw_path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Frozen Git object paths must be repository-relative.")
        canonical.append((path.as_posix(), object_id.lower()))
    return tuple(sorted(canonical))


def _repository_authoritative_frontend_src_tree(repository_root: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="frp-freeze-index-") as temporary_directory:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(temporary_directory) / "index")
        subprocess.run(
            ["git", "read-tree", "HEAD"],  # noqa: S607
            cwd=repository_root,
            check=True,
            env=environment,
        )
        subprocess.run(
            ["git", "add", "-A", "--", "frontend/src"],  # noqa: S607
            cwd=repository_root,
            check=True,
            env=environment,
        )
        revision = subprocess.run(
            ["git", "write-tree"],  # noqa: S607
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
        return subprocess.run(  # noqa: S603 - controlled repository object query
            ["git", "rev-parse", f"{revision}:frontend/src"],  # noqa: S607
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()


def _current_frontend_git_objects(repository_root: Path) -> tuple[tuple[str, str], ...]:
    paths = ("frontend/package.json", "frontend/package-lock.json")
    completed = subprocess.run(  # noqa: S603 - controlled repository governance query
        ["git", "rev-parse", *(f"HEAD:{path}" for path in paths)],  # noqa: S607
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    object_ids = tuple(line.strip() for line in completed.stdout.splitlines())
    if len(object_ids) != len(paths):
        raise RuntimeError("Git returned an incomplete frontend source identity.")
    return _canonical_git_object_manifest(
        (
            ("frontend/src", _repository_authoritative_frontend_src_tree(repository_root)),
            *zip(paths, object_ids, strict=True),
        )
    )


def _matches_frozen_frontend_git_objects(entries: Iterable[tuple[str, str]]) -> bool:
    canonical = _canonical_git_object_manifest(entries)
    approved = (
        _canonical_git_object_manifest(
            (
                *_FROZEN_FRONTEND_CORE_GIT_OBJECTS,
                ("frontend/package-lock.json", STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB),
            )
        ),
        _canonical_git_object_manifest(
            (
                *_FROZEN_FRONTEND_CORE_GIT_OBJECTS,
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        ),
        _canonical_git_object_manifest(
            (
                ("frontend/src", STAGE_3_4B_HISTORICAL_FRONTEND_SRC_TREE),
                ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        ),
        _canonical_git_object_manifest(
            (
                ("frontend/src", STAGE_3_5A_HISTORICAL_FRONTEND_SRC_TREE),
                ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        ),
        _canonical_git_object_manifest(
            (
                ("frontend/src", STAGE_3_5A_R1_HISTORICAL_FRONTEND_SRC_TREE),
                ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        ),
        _canonical_git_object_manifest(
            (
                *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        ),
    )
    return canonical in approved


def _working_tree_git_blob(repository_root: Path, path: str) -> str:
    completed = subprocess.run(  # noqa: S603 - controlled repository governance query
        ["git", "hash-object", f"--path={path}", path],  # noqa: S607
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _reachable_successor_package_lock_bytes(repository_root: Path) -> bytes:
    """Resolve the immutable Nano ID successor, never reinterpret current HEAD as it."""
    return _historical_dependency_bytes(repository_root, "frontend/package-lock.json")


def _git_blob_id(repository_root: Path, content: bytes) -> str:
    return (
        subprocess.run(
            ["git", "hash-object", "--stdin"],  # noqa: S607
            cwd=repository_root,
            check=True,
            input=content,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )


def _reconstruct_historical_package_lock(successor_bytes: bytes) -> bytes:
    assert successor_bytes.count(_NANOID_SUCCESSOR_METADATA_BLOCK) == 1, (
        "The exact successor Nano ID metadata block must occur once."
    )
    assert successor_bytes.count(_NANOID_HISTORICAL_METADATA_BLOCK) == 0, (
        "Historical Nano ID metadata must not occur in the successor."
    )
    historical_bytes = successor_bytes.replace(
        _NANOID_SUCCESSOR_METADATA_BLOCK,
        _NANOID_HISTORICAL_METADATA_BLOCK,
        1,
    )
    assert historical_bytes.count(_NANOID_HISTORICAL_METADATA_BLOCK) == 1
    assert (
        historical_bytes.replace(
            _NANOID_HISTORICAL_METADATA_BLOCK,
            _NANOID_SUCCESSOR_METADATA_BLOCK,
            1,
        )
        == successor_bytes
    )
    return historical_bytes


def _verify_nanoid_security_successor_transition(
    repository_root: Path,
    successor_bytes: bytes,
) -> bytes:
    assert hashlib.sha256(successor_bytes).hexdigest().upper() == (
        STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_SHA256
    ), "The successor SHA-256 must remain exact."
    assert _git_blob_id(repository_root, successor_bytes) == (
        STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB
    )
    historical_bytes = _reconstruct_historical_package_lock(successor_bytes)
    assert hashlib.sha256(historical_bytes).hexdigest().upper() == (
        STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_SHA256
    )
    assert _git_blob_id(repository_root, historical_bytes) == STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB

    successor = json.loads(successor_bytes)
    historical = json.loads(historical_bytes)
    successor_nanoid = successor["packages"]["node_modules/nanoid"]
    historical_nanoid = historical["packages"]["node_modules/nanoid"]
    assert tuple(historical_nanoid[field] for field in _NANOID_METADATA_FIELDS) == (
        "3.3.17",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.17.tgz",
        "sha512-xQLf0A3HOMlgHq0n247/LRuAOYmB7dXJ/DvAxGvsSBij45XtBSmQycu+F8ODbHwns/"
        "XyFZagyL1+J0Offw1E0g==",
    )
    assert tuple(successor_nanoid[field] for field in _NANOID_METADATA_FIELDS) == (
        "3.3.18",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
        "sha512-DTg4MJbGMWkfi6VZFdNt2/caMbQy4Ou+Op/hJQvGEWcnVfoA1QA+xzRKAzw9jD6+"
        "GVOOeYr/mIcuDSdug6F6+w==",
    )
    for field in _NANOID_METADATA_FIELDS:
        historical_nanoid[field] = successor_nanoid[field]
    assert historical == successor
    return historical_bytes


def _active_nanoid_versions(package_lock: dict[str, object]) -> tuple[str, ...]:
    packages = package_lock.get("packages")
    if not isinstance(packages, dict):
        return ()
    versions: list[str] = []
    for path, package in packages.items():
        if not isinstance(path, str) or not (
            path == "node_modules/nanoid" or path.endswith("/node_modules/nanoid")
        ):
            continue
        if not isinstance(package, dict) or not isinstance(package.get("version"), str):
            return ()
        versions.append(package["version"])
    return tuple(sorted(versions))


def _is_active_nanoid_security_successor(
    package_lock_blob: str,
    nanoid_versions: tuple[str, ...],
) -> bool:
    return (
        package_lock_blob == STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB
        and nanoid_versions == ("3.3.18",)
    )


def test_stage_3_5a_r2_frontend_identity_remains_registered_as_predecessor() -> None:
    repository_root = Path(__file__).parents[3]
    current = _current_frontend_git_objects(repository_root)
    predecessor = _canonical_git_object_manifest(
        (
            *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )
    assert _matches_frozen_frontend_git_objects(predecessor)
    current_by_path = dict(current)
    for path, (blob, _) in _FROZEN_DEPENDENCIES.items():
        assert dict(predecessor)[path] == blob
        _assert_frozen_dependency_bytes(path, _historical_dependency_bytes(repository_root, path))
    _assert_security_dependencies(repository_root)
    assert len(current_by_path["frontend/src"]) == 40
    assert current_by_path["frontend/src"] != dict(predecessor)["frontend/src"]


def test_stage_3_4a_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_4A_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_4a_r2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_4A_R2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_3c3_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_3C3_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_3c2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_3C2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_3b_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_3B_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_3a_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_3A_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_3a_r4_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_3A_R4_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_original_and_security_successor_package_locks_are_the_only_approved_identities() -> None:
    assert _APPROVED_PACKAGE_LOCK_BLOBS == (
        "f2a594dae8c871d5c1c78e69f1023d6e77adf6e6",
        "ae1831268db42005517343bf555f054a673ae520",
    )
    for package_lock_blob in _APPROVED_PACKAGE_LOCK_BLOBS:
        assert _matches_frozen_frontend_git_objects(
            (
                *_FROZEN_FRONTEND_CORE_GIT_OBJECTS,
                ("frontend/package-lock.json", package_lock_blob),
            )
        )
    assert _matches_frozen_frontend_git_objects(
        (
            *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )
    assert not _matches_frozen_frontend_git_objects(
        (
            *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
            ("frontend/package-lock.json", STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB),
        )
    )
    assert not _matches_frozen_frontend_git_objects(
        (*_FROZEN_FRONTEND_CORE_GIT_OBJECTS, ("frontend/package-lock.json", "9" * 40))
    )


def test_visually_rejected_interim_frontend_tree_is_not_an_active_successor() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_4C_REJECTED_INTERIM_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_2_4c_r1_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_4C_R1_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_2_4c_r2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_4C_R2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_2_4c_r3_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_4C_R3_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_2_5c_r1_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_5C_R1_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_2_5c_r2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_2_5C_R2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_2_r2_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_2_R2_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_2_r4_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_2_R4_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_2_r9_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_2_R9_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_stage_3_2_r10_frontend_tree_is_historical_predecessor_not_active() -> None:
    assert not _matches_frozen_frontend_git_objects(
        (
            ("frontend/src", STAGE_3_2_R10_HISTORICAL_FRONTEND_SRC_TREE),
            ("frontend/package.json", STAGE_2_3_FROZEN_PACKAGE_JSON_BLOB),
            (
                "frontend/package-lock.json",
                STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ),
        )
    )


def test_active_package_lock_is_exact_nanoid_security_successor() -> None:
    repository_root = Path(__file__).parents[3]
    frozen = _reachable_successor_package_lock_bytes(repository_root)
    assert _is_active_nanoid_security_successor(
        _git_blob_id(repository_root, frozen), _active_nanoid_versions(json.loads(frozen))
    )
    _assert_security_dependencies(repository_root)
    active = json.loads(
        (repository_root / "frontend/package-lock.json").read_text(encoding="utf-8")
    )
    assert _active_nanoid_versions(active) == ("3.3.18",)


@pytest.mark.parametrize(
    ("package_lock_blob", "nanoid_versions"),
    [
        pytest.param(
            STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB,
            ("3.3.17",),
            id="historical-vulnerable-lock-is-not-active",
        ),
        pytest.param("8" * 40, ("3.3.18",), id="arbitrary-third-lock"),
        pytest.param(
            STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            ("3.3.17",),
            id="vulnerable-version-under-successor-identity",
        ),
        pytest.param(
            STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
            (),
            id="missing-nanoid",
        ),
    ],
)
def test_active_package_lock_rejects_historical_arbitrary_or_vulnerable_state(
    package_lock_blob: str,
    nanoid_versions: tuple[str, ...],
) -> None:
    assert not _is_active_nanoid_security_successor(package_lock_blob, nanoid_versions)


def test_security_successor_lock_diff_is_exactly_nanoid_metadata() -> None:
    repository_root = Path(__file__).parents[3]
    successor_bytes = _reachable_successor_package_lock_bytes(repository_root)
    historical_bytes = _verify_nanoid_security_successor_transition(
        repository_root,
        successor_bytes,
    )
    assert successor_bytes.count(_NANOID_SUCCESSOR_METADATA_BLOCK) == 1
    assert successor_bytes.count(_NANOID_HISTORICAL_METADATA_BLOCK) == 0
    assert historical_bytes.count(_NANOID_HISTORICAL_METADATA_BLOCK) == 1


def test_security_successor_transition_rejects_unrelated_byte_mutation() -> None:
    repository_root = Path(__file__).parents[3]
    successor_bytes = _reachable_successor_package_lock_bytes(repository_root)
    with pytest.raises(AssertionError, match="successor SHA-256"):
        _verify_nanoid_security_successor_transition(repository_root, successor_bytes + b" ")


@pytest.mark.parametrize(
    ("expected", "wrong"),
    [
        pytest.param(b'"version": "3.3.18"', b'"version": "3.3.19"', id="wrong-version"),
        pytest.param(
            b"https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
            b"https://registry.npmjs.org/nanoid/-/nanoid-3.3.19.tgz",
            id="wrong-url",
        ),
        pytest.param(
            b"sha512-DTg4MJbGMWkfi6VZFdNt2/caMbQy4Ou+Op/hJQvGEWcnVfoA1QA+xzRKAzw9jD6+"
            b"GVOOeYr/mIcuDSdug6F6+w==",
            b"sha512-wrong-integrity",
            id="wrong-integrity",
        ),
    ],
)
def test_security_successor_transition_rejects_wrong_nanoid_metadata(
    expected: bytes,
    wrong: bytes,
) -> None:
    repository_root = Path(__file__).parents[3]
    successor_bytes = _reachable_successor_package_lock_bytes(repository_root)
    assert successor_bytes.count(expected) == 1
    with pytest.raises(AssertionError, match="successor Nano ID metadata block"):
        _reconstruct_historical_package_lock(successor_bytes.replace(expected, wrong, 1))


@pytest.mark.parametrize("mutation", ["missing", "duplicated", "historical-present"])
def test_security_successor_transition_rejects_missing_or_ambiguous_block(mutation: str) -> None:
    repository_root = Path(__file__).parents[3]
    successor_bytes = _reachable_successor_package_lock_bytes(repository_root)
    if mutation == "missing":
        mutated = successor_bytes.replace(_NANOID_SUCCESSOR_METADATA_BLOCK, b"", 1)
    elif mutation == "duplicated":
        mutated = successor_bytes.replace(
            _NANOID_SUCCESSOR_METADATA_BLOCK,
            _NANOID_SUCCESSOR_METADATA_BLOCK * 2,
            1,
        )
    else:
        mutated = successor_bytes.replace(
            _NANOID_SUCCESSOR_METADATA_BLOCK,
            _NANOID_SUCCESSOR_METADATA_BLOCK + _NANOID_HISTORICAL_METADATA_BLOCK,
            1,
        )
    with pytest.raises(AssertionError):
        _reconstruct_historical_package_lock(mutated)


def test_dependency_freeze_audit_reads_only_the_reachable_successor_blob() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=__file__)
    resolver = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_historical_dependency_bytes"
    )
    # Resolution is restricted to the pinned historical identity map. Fallback
    # must reconstruct and verify frozen bytes, not trust current bytes as history.
    body = ast.unparse(resolver)
    assert "_FROZEN_DEPENDENCIES[path][0]" in body
    assert "_restore_frozen_dependency_bytes(path, raw)" in body
    assert "_assert_frozen_dependency_bytes(path, raw)" in body
    for path in _FROZEN_DEPENDENCIES:
        _assert_frozen_dependency_bytes(
            path, _historical_dependency_bytes(Path(__file__).parents[3], path)
        )


@pytest.mark.parametrize(
    "mutated",
    [
        pytest.param(
            (
                ("frontend/src", "0" * 40),
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[1],
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            ),
            id="changed-source",
        ),
        pytest.param(
            (
                ("frontend/src", "1" * 40),
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[1],
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            ),
            id="added-source",
        ),
        pytest.param(
            (
                ("frontend/src", "2" * 40),
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[1],
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            ),
            id="deleted-source",
        ),
        pytest.param(
            (
                ("frontend/src", "3" * 40),
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[1],
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            ),
            id="renamed-source",
        ),
        pytest.param(
            (
                ("frontend/src", "6" * 40),
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[1],
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            ),
            id="arbitrary-third-source",
        ),
        pytest.param(
            (
                _ACTIVE_FRONTEND_CORE_GIT_OBJECTS[0],
                ("frontend/package.json", "4" * 40),
                ("frontend/package-lock.json", STAGE_2_3_R8_FROZEN_PACKAGE_LOCK_BLOB),
            ),
            id="changed-package-json",
        ),
        pytest.param(
            (
                *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
                ("frontend/package-lock.json", "5" * 40),
            ),
            id="changed-package-lock",
        ),
    ],
)
def test_frontend_freeze_git_identity_detects_every_controlled_mutation(
    mutated: tuple[tuple[str, str], ...],
) -> None:
    assert not _matches_frozen_frontend_git_objects(mutated)


def test_frontend_freeze_manifest_is_separator_and_order_invariant() -> None:
    windows_reversed = tuple(
        (path.replace("/", "\\"), object_id)
        for path, object_id in reversed(
            (
                *_ACTIVE_FRONTEND_CORE_GIT_OBJECTS,
                (
                    "frontend/package-lock.json",
                    STAGE_2_3_APPROVED_NANOID_SECURITY_SUCCESSOR_PACKAGE_LOCK_BLOB,
                ),
            )
        )
    )
    assert _matches_frozen_frontend_git_objects(windows_reversed)


def test_frontend_freeze_git_identity_does_not_read_checkout_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_checkout_bytes_are_read(_path: Path) -> bytes:
        raise AssertionError("The freeze audit must use Git objects, not checkout bytes.")

    monkeypatch.setattr(Path, "read_bytes", fail_if_checkout_bytes_are_read)
    repository_root = Path(__file__).parents[3]
    current = dict(_current_frontend_git_objects(repository_root))
    assert len(current["frontend/src"]) == 40
    for path in _FROZEN_DEPENDENCIES:
        committed = subprocess.run(  # noqa: S603 - fixed dependency path map
            ["git", "rev-parse", f"HEAD:{path}"],  # noqa: S607
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert current[path] == committed
        _assert_frozen_dependency_bytes(path, _historical_dependency_bytes(repository_root, path))


def test_frontend_freeze_git_identity_does_not_mutate_real_index() -> None:
    repository_root = Path(__file__).parents[3]
    command = ["git", "write-tree"]
    before = subprocess.run(  # noqa: S603 - controlled repository index query
        command,
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _current_frontend_git_objects(repository_root)
    after = subprocess.run(  # noqa: S603 - controlled repository index query
        command,
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert after == before


def test_frontend_freeze_manifest_rejects_unsafe_or_incomplete_paths() -> None:
    with pytest.raises(ValueError, match="repository-relative"):
        _canonical_git_object_manifest((("../frontend/src", "0" * 40),))
    assert not _matches_frozen_frontend_git_objects(_FROZEN_FRONTEND_CORE_GIT_OBJECTS)


def test_stage_2_4c_api_source_does_not_import_engine_equations_or_golden() -> None:
    repository_root = Path(__file__).parents[3]
    files = tuple(
        (repository_root / "backend" / "src" / "frp_master_connection" / "api").rglob("*.py")
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "multirow_engine" not in combined
    assert "multirow_equations" not in combined
    assert "tests/golden" not in combined


def test_stage_2_4c_r1_frontend_has_one_connection_workspace() -> None:
    repository_root = Path(__file__).parents[3]
    workspace_root = repository_root / "frontend" / "src" / "workspace"
    assert not (workspace_root / "MultiRowEngineeringWorkspace.tsx").exists()
    source = (workspace_root / "ShearConnectionsWorkspace.tsx").read_text(encoding="utf-8")
    assert "SingleBoltEngineeringWorkspace" in source
    assert "MultiRowEngineeringWorkspace" not in source
    assert "workspace-mode" not in source


def test_stage_2_4a_pure_modules_have_no_io_time_or_randomness_imports() -> None:
    prohibited_roots = {"pathlib", "random", "secrets", "socket", "time", "urllib"}
    findings: list[str] = []
    for source in _calculation_sources():
        if source.name not in {
            "block_shear_planning.py",
            "multirow.py",
            "multirow_fingerprint.py",
        }:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings.extend(
                    f"{source.name}:{node.lineno}:{alias.name}"
                    for alias in node.names
                    if alias.name.split(".")[0] in prohibited_roots
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.split(".")[0] in prohibited_roots
            ):
                findings.append(f"{source.name}:{node.lineno}:{node.module}")
    assert findings == []
