"""F9 CI delta restores exact accepted history and rejects unrelated mutations."""

from __future__ import annotations

import pytest

from tests.direct_f8_g1_governance import CI_SHA256, ROOT, digest, pre_g1_workflow
from tests.direct_f9_governance import authority, pre_f9_workflow


def test_f9_workflow_restores_exact_f8_g1_and_earlier_history() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    assert digest(pre_f9_workflow(raw)) == CI_SHA256
    assert digest(pre_g1_workflow(pre_f9_workflow(raw))) == (
        "C6B56ED836C0BAD48ECC66B489E73A46CA59B94E4354E475F732809EE1DFCC74"
    )


@pytest.mark.parametrize(
    "mutation", ["count", "timeout", "steps", "runtime", "hash-lock", "duplicate", "extra"]
)
def test_f9_workflow_mutation_fails_closed(mutation: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    governed = authority()
    replacements = {
        "count": (f"--expected-tests {governed['backend_tests']}".encode(), b"--expected-tests 1"),
        "timeout": (b"timeout-minutes: 60", b"timeout-minutes: 61"),
        "steps": (governed["added_steps"].encode(), b""),
        "runtime": (b"python-version: 3.14.6", b"python-version: 3.14.7"),
        "hash-lock": (b"--require-hashes", b"--no-deps"),
        "duplicate": (governed["added_steps"].encode(), governed["added_steps"].encode() * 2),
        "extra": (b"name: CI", b"name: CI\n# EXTRA"),
    }
    before, after = replacements[mutation]
    with pytest.raises(AssertionError, match="F9_WORKFLOW_IDENTITY"):
        pre_f9_workflow(raw.replace(before, after))


def test_f9_authority_cannot_repin_history() -> None:
    raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_F9_STATUS_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="F9_AUTHORITY_IDENTITY"):
        authority(raw + b" ")
