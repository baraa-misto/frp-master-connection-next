"""Reject successor drift while retaining exact historical reconstruction."""

import pytest

from tests.direct_f8_g1_governance import ROOT, digest
from tests.direct_mc1_governance import authority as mc1_authority
from tests.direct_mc1_governance import pre_mc1_workflow
from tests.direct_sab2_governance import authority, pre_sab2_workflow


def test_current_workflow_preserves_all_historical_pdf_and_security_gates() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    old = pre_sab2_workflow(raw)
    assert digest(old) == mc1_authority()["workflow_sha256"]
    assert authority()["backend_tests"] == 8957
    assert authority()["frontend_tests"] == 1357
    assert pre_mc1_workflow(raw) == pre_mc1_workflow(old)


@pytest.mark.parametrize("mutation", ["count", "pdf", "historical"])
def test_successor_rejects_count_report_or_historical_drift(mutation: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    old, new = {
        "count": (b"--expected-tests 8957", b"--expected-tests 8956"),
        "pdf": (b"direct-sab2-review-pdfs", b"direct-sab2-missing-pdfs"),
        "historical": (b"direct-mc1-review-pdfs", b"direct-mc1-missing-pdfs"),
    }[mutation]
    with pytest.raises(AssertionError, match="SAB2_WORKFLOW_IDENTITY"):
        pre_sab2_workflow(raw.replace(old, new))


def test_authority_identity_rejects_mutation() -> None:
    raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_SAB2_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="SAB2_AUTHORITY_IDENTITY"):
        authority(raw + b" ")


def test_predecessor_bytes_remain_accepted_for_historical_reconstruction() -> None:
    old = pre_sab2_workflow((ROOT / ".github/workflows/ci.yml").read_bytes())
    assert pre_sab2_workflow(old) == old
