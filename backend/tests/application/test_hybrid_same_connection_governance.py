"""P3 changes counts/reports, never protected engineering or prior CI gates."""

import pytest

from tests.hybrid_physical_governance import pre_p4_inactive_boundary
from tests.hybrid_same_connection_governance import ROOT, authority, digest, pre_p3_workflow
from tests.hybrid_security_successor import pre_s1_workflow
from tests.hybrid_workspace_governance import authority as p2_authority
from tests.hybrid_workspace_governance import pre_p2_workflow
from tests.hybrid_workspace_security import pre_p2_dependency


def test_exact_p2_predecessor_and_all_preserved_engineering_identities() -> None:
    governed = authority()
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    previous = pre_p3_workflow(raw)
    assert digest(previous) == governed["predecessor_workflow_sha256"]
    assert pre_p3_workflow(previous) == previous
    assert pre_p2_workflow(raw) == pre_p2_workflow(previous)
    assert governed["protected_engineering_count"] == 53
    assert governed["historical_controls"] == 173
    for group in ("protected_engineering", "historical_controls"):
        for row in p2_authority()[group]:
            assert (
                digest(pre_p2_dependency(row["path"], (ROOT / row["path"]).read_bytes()))
                in row["accepted_checkout_sha256"]
            )
    assert governed["qualification_installed"] is False
    assert governed["method_approval_installed"] is False
    assert governed["dependency_changes"] == []
    assert governed["coverage_thresholds"] == [100, 100, 100, 100]
    guard = governed["inactive_boundary_guard"]
    current = pre_p4_inactive_boundary((ROOT / guard["path"]).read_bytes())
    assert digest(current) == guard["after_sha256"]
    added = guard["exact_added_line"].encode()
    assert current.count(added) == 1
    assert digest(current.replace(added, b"")) == guard["before_sha256"]


def test_successor_manifest_is_exact() -> None:
    raw = (ROOT / "docs/governance/HYB2_D3_P3_SAME_CONNECTION_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="P3_AUTHORITY_IDENTITY_INVALID"):
        authority(raw + b" ")


@pytest.mark.parametrize("mutation", ["count", "inherited_reports", "security"])
def test_p3_successor_rejects_unapproved_workflow_drift(mutation: str) -> None:
    raw = pre_s1_workflow((ROOT / ".github/workflows/ci.yml").read_bytes())
    before, after = {
        "count": (
            f"--expected-tests {authority()['backend_tests']}".encode(),
            b"--expected-tests 1",
        ),
        "inherited_reports": (b"hyb1-review-pdfs/", b"missing-review-pdfs/"),
        "security": (b"full security audit", b"missing security audit"),
    }[mutation]
    assert before in raw
    with pytest.raises(AssertionError, match="P3_WORKFLOW_IDENTITY_INVALID"):
        pre_p3_workflow(raw.replace(before, after))
