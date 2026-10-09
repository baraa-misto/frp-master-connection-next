"""MC1 publication gates preserve every accepted historical PDF and freeze authority."""

import pytest

from tests.direct_f8_g1_governance import ROOT, digest
from tests.direct_f9_governance import authority as f9_authority
from tests.direct_mc1_governance import authority, pre_mc1_workflow


def test_mc1_workflow_reverses_exactly_to_f9_predecessor() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    assert digest(pre_mc1_workflow(raw)) == f9_authority()["workflow_sha256"]


@pytest.mark.parametrize(
    "mutation", ["count", "steps", "duplicate", "runtime", "hash-lock", "timeout", "extra"]
)
def test_mc1_workflow_fails_closed_on_every_unrelated_change(mutation: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    governed = authority()
    replacements = {
        "count": (f"--expected-tests {governed['backend_tests']}".encode(), b"--expected-tests 1"),
        "steps": (governed["added_steps"].encode(), b""),
        "duplicate": (governed["added_steps"].encode(), governed["added_steps"].encode() * 2),
        "runtime": (b"python-version: 3.14.6", b"python-version: 3.14.7"),
        "hash-lock": (b"--require-hashes", b"--no-deps"),
        "timeout": (b"timeout-minutes: 60", b"timeout-minutes: 61"),
        "extra": (b"name: CI", b"name: CI\n# EXTRA"),
    }
    before, after = replacements[mutation]
    assert before in raw
    with pytest.raises(AssertionError, match="MC1_WORKFLOW_IDENTITY"):
        pre_mc1_workflow(raw.replace(before, after))


def test_mc1_authority_cannot_repin_history() -> None:
    raw = (ROOT / "docs/governance/SHEAR01_DIRECT_OR2_F9_MC1_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="MC1_AUTHORITY_IDENTITY"):
        authority(raw + b" ")
