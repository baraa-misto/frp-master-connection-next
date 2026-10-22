"""P2 changes presentation and coordinated input ownership, not engineering identities."""

import pytest

from tests.hybrid_workflow_governance import pre_d3_workflow
from tests.hybrid_workspace_governance import ROOT, authority, digest, pre_p2_workflow
from tests.hybrid_workspace_security import pre_p2_dependency


def test_exact_p1_predecessor_and_all_preserved_engineering_identities() -> None:
    governed = authority()
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    previous = pre_p2_workflow(raw)
    assert digest(previous) == governed["predecessor_workflow_sha256"]
    assert pre_p2_workflow(previous) == previous
    assert pre_d3_workflow(raw) == pre_d3_workflow(previous)
    for group, count in (("protected_engineering", 53), ("historical_controls", 173)):
        assert len(governed[group]) == count
        for row in governed[group]:
            assert (
                digest(pre_p2_dependency(row["path"], (ROOT / row["path"]).read_bytes()))
                in row["accepted_checkout_sha256"]
            )
    assert governed["structural_method_activation"] is False
    assert governed["dependency_changes"] == [
        "Vitest 4.1.12 and seven matching internals",
        "pypdf 6.21.1",
    ]
    assert governed["coverage_thresholds"] == [100, 100, 100, 100]
    with pytest.raises(AssertionError, match="P2_WORKSPACE_AUTHORITY_INVALID"):
        authority(
            (ROOT / "docs/governance/HYB2_D3_P2_WORKSPACE_SUCCESSOR.json").read_bytes() + b" "
        )


@pytest.mark.parametrize("mutation", ["count", "inherited_reports", "security"])
def test_p2_successor_rejects_unapproved_workflow_drift(mutation: str) -> None:
    from tests.hybrid_same_connection_governance import pre_p3_workflow

    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    raw = pre_p3_workflow(raw)
    before, after = {
        "count": (b"--expected-tests 9455", b"--expected-tests 1"),
        "inherited_reports": (b"hyb1-review-pdfs/", b"missing-review-pdfs/"),
        "security": (b"full security audit", b"missing security audit"),
    }[mutation]
    assert before in raw
    with pytest.raises(AssertionError, match="P2_WORKFLOW_IDENTITY_INVALID"):
        pre_p2_workflow(raw.replace(before, after))
