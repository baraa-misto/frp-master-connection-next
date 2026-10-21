"""P1 adds evidence without relaxing any predecessor workflow gate."""

import pytest

from tests.direct_f8_g1_governance import ROOT, digest
from tests.direct_p1_governance import authority, pre_p1_workflow
from tests.direct_sab2_governance import authority as sab2_authority
from tests.direct_sab2_governance import pre_sab2_workflow
from tests.hyb1_governance import authority as hyb1_authority
from tests.hybrid_workflow_governance import pre_d3_workflow


def test_p1_reconstructs_the_exact_predecessor_and_preserves_historical_chain() -> None:
    raw = pre_d3_workflow((ROOT / ".github/workflows/ci.yml").read_bytes())
    previous = pre_p1_workflow(raw)
    assert digest(previous) == sab2_authority()["workflow_sha256"]
    assert pre_sab2_workflow(previous) == pre_sab2_workflow(raw)
    assert authority()["new_pdf_count_per_platform"] == 4
    assert authority()["protected_engineering_identities"] == 53
    assert authority()["new_resistance_or_demand_methods"] is False
    assert authority()["unchanged_c13_partial_rows"] == ["C13-05", "C13-06", "C13-07", "C13-08"]
    assert pre_p1_workflow(previous) == previous
    assert pre_p1_workflow(pre_sab2_workflow(previous)) == pre_sab2_workflow(previous)


@pytest.mark.parametrize("mutation", ["count", "p1-pdf", "sab2-pdf", "historical", "security"])
def test_p1_rejects_new_count_or_report_and_historical_gate_drift(mutation: str) -> None:
    raw = pre_d3_workflow((ROOT / ".github/workflows/ci.yml").read_bytes())
    old, new = {
        "count": (
            f"--expected-tests {hyb1_authority()['backend_tests']}".encode(),
            b"--expected-tests 1",
        ),
        "p1-pdf": (b"direct-p1-review-pdfs", b"direct-p1-missing-pdfs"),
        "sab2-pdf": (b"direct-sab2-review-pdfs", b"direct-sab2-missing-pdfs"),
        "historical": (b"direct-mc1-review-pdfs", b"direct-mc1-missing-pdfs"),
        "security": (b"Verify exact F8-G1 dependencies and full security audit", b"Missing audit"),
    }[mutation]
    assert old in raw
    with pytest.raises(AssertionError, match="P1_WORKFLOW_IDENTITY"):
        pre_p1_workflow(raw.replace(old, new))


def test_p1_authority_rejects_even_whitespace_mutation() -> None:
    raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_SAB2_P1_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="P1_AUTHORITY_IDENTITY"):
        authority(raw + b" ")
