"""New count/PDF gate is exact and additive; prior governance remains authoritative."""

import pytest

from tests.direct_f8_g1_governance import ROOT, digest
from tests.direct_p1_governance import pre_p1_workflow
from tests.hyb1_governance import authority, pre_hyb1_workflow


def test_hyb1_exact_predecessor_reconstruction() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    old = pre_hyb1_workflow(raw)
    assert digest(old) == authority()["predecessor_workflow_sha256"]
    assert pre_hyb1_workflow(old) == old
    assert pre_p1_workflow(raw) == pre_p1_workflow(old)
    assert authority()["new_pdf_count_per_platform"] == 6
    assert authority()["public_method_activation"] is False
    assert authority()["protected_engineering_identities"] == 53
    assert authority()["historical_controls"] == 173


@pytest.mark.parametrize("mutation", ["count", "hyb1-pdf", "historical", "security"])
def test_hyb1_rejects_gate_drift(mutation: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    old, new = {
        "count": (
            f"--expected-tests {authority()['backend_tests']}".encode(),
            b"--expected-tests 1",
        ),
        "hyb1-pdf": (b"hyb1-review-pdfs", b"missing-hyb1-pdfs"),
        "historical": (b"direct-p1-review-pdfs", b"missing-p1-pdfs"),
        "security": (b"Verify exact F8-G1 dependencies and full security audit", b"Missing audit"),
    }[mutation]
    assert old in raw
    with pytest.raises(AssertionError, match="HYB1_WORKFLOW_IDENTITY"):
        pre_hyb1_workflow(raw.replace(old, new))


def test_hyb1_manifest_cannot_change_silently() -> None:
    raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_HYB1_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="HYB1_AUTHORITY_IDENTITY"):
        authority(raw + b" ")
