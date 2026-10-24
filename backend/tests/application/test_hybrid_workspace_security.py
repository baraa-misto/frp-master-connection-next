"""Approved pins reconstruct exact P1 locks; all other drift is rejected."""

import pytest

from tests.hybrid_security_successor import pre_s1_dependency
from tests.hybrid_workspace_governance import ROOT, digest
from tests.hybrid_workspace_security import authority, pre_p2_dependency


def test_exact_security_predecessors_and_bounded_version_changes() -> None:
    governed = authority()
    assert governed["other_backend_versions_unchanged"] == 54
    assert len(governed["changed_lock_records"]) == 10
    for path, row in governed["files"].items():
        raw = pre_s1_dependency(path, (ROOT / path).read_bytes()).replace(b"\r\n", b"\n")
        assert digest(raw) == row["after_sha256"]
        before = pre_p2_dependency(path, raw)
        assert digest(before) == row["before_sha256"]
        assert pre_p2_dependency(path, before) == before
    with pytest.raises(AssertionError, match="P2_SECURITY_AUTHORITY_INVALID"):
        authority((ROOT / "docs/governance/HYB2_D3_P2_SECURITY_SUCCESSOR.json").read_bytes() + b" ")


@pytest.mark.parametrize(
    "path",
    [
        "frontend/package.json",
        "frontend/package-lock.json",
        "backend/pyproject.toml",
        "backend/requirements/requirements-dev-py314.lock.txt",
    ],
)
@pytest.mark.parametrize("mutation", ["unapproved_version", "bytes"])
def test_p2_security_reverse_delta_rejects_every_unapproved_identity(
    path: str, mutation: str
) -> None:
    raw = pre_s1_dependency(path, (ROOT / path).read_bytes()).replace(b"\r\n", b"\n")
    if mutation == "bytes":
        changed = raw + b" "
    else:
        before = b"4.1.12" if path.startswith("frontend/") else b"6.21.1"
        assert before in raw
        changed = raw.replace(before, b"0.0.0", 1)
    assert pre_p2_dependency(path, changed) == changed
    assert digest(changed) != authority()["files"][path]["after_sha256"]
