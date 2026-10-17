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
    assert authority()["new_pdf_count_per_platform"] == 15
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


def test_original_completed_hyb1_workflow_still_reconstructs_exact_p2() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    governed = authority()
    original = raw.replace(
        f"--expected-tests {governed['backend_tests']}".encode(), b"--expected-tests 9085"
    )
    assert digest(original) == governed["supplement_predecessor_workflow_sha256"]
    assert pre_hyb1_workflow(original) == pre_hyb1_workflow(raw)


def test_completed_clip_tee_predecessor_reconstructs_exact_p2() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    governed = authority()
    previous = raw.replace(
        f"--expected-tests {governed['backend_tests']}".encode(), b"--expected-tests 9114"
    )
    assert digest(previous) == governed["direct_predecessor_workflow_sha256"]
    assert pre_hyb1_workflow(previous) == pre_hyb1_workflow(raw)


def test_completed_r1_predecessor_reconstructs_exact_p2() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    governed = authority()
    previous = raw.replace(
        f"--expected-tests {governed['backend_tests']}".encode(), b"--expected-tests 9181"
    )
    assert digest(previous) == governed["r1_predecessor_workflow_sha256"]
    assert pre_hyb1_workflow(previous) == pre_hyb1_workflow(raw)
