"""The new access permission changes neither engineering nor predecessor gates."""

import json

import pytest

from tests.direct_f8_g1_governance import ROOT, digest, pre_g1_lock
from tests.hyb1_governance import pre_hyb1_workflow
from tests.hybrid_workflow_governance import (
    authority,
    backend_security_authority,
    pre_d3_backend_dependency,
    pre_d3_dependency,
    pre_d3_workflow,
)
from tests.hybrid_workspace_security import pre_p2_dependency


def test_exact_d2_predecessor_and_separate_workflow_access() -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes()
    old = pre_d3_workflow(raw)
    assert digest(old) == authority()["predecessor_workflow_sha256"]
    assert pre_d3_workflow(old) == old
    assert pre_hyb1_workflow(raw) == pre_hyb1_workflow(old)
    assert authority()["workflow_available"] is True
    assert authority()["structural_method_activation"] is False
    assert authority()["protected_engineering_identities"] == 53
    assert authority()["historical_controls"] == 173
    assert authority()["new_pdf_count_per_platform"] == 14
    security_raw = (ROOT / "docs/governance/HYB2_D3_P1_SECURITY_SUCCESSOR.json").read_bytes()
    assert digest(security_raw) == authority()["security_successor_sha256"]
    security = json.loads(security_raw)
    for name, identities in security["files"].items():
        current = pre_p2_dependency(name, (ROOT / name).read_bytes())
        assert digest(current) == identities["after_sha256"].upper()
        assert digest(pre_d3_dependency(name, current)) == identities["before_sha256"].upper()
        assert pre_d3_dependency(name, current + b" ") == current + b" "
        previous = json.loads(current)
        if name.endswith("package-lock.json"):
            for row in security["changed_lock_records"]:
                record = previous["packages"][row["path"]]
                assert (
                    digest(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
                    == row["after_sha256"].upper()
                )
                previous["packages"][row["path"]] = row["before"]
        else:
            previous["devDependencies"]["vite"] = security["previous_vite"]
        assert (
            digest((json.dumps(previous, indent=2) + "\n").encode())
            == identities["before_sha256"].upper()
        )
    assert security["approved_vite"] == "8.2.4"
    assert security["retained_nanoid"] == "3.3.18"
    assert security["unrelated_changed_records"] == []
    backend = backend_security_authority()
    current_lock = pre_p2_dependency(backend["file"], (ROOT / backend["file"]).read_bytes())
    old_lock = pre_d3_backend_dependency(current_lock)
    assert digest(current_lock) == backend["after_sha256"]
    assert digest(old_lock) == backend["before_sha256"]
    assert pre_d3_backend_dependency(old_lock) == old_lock
    assert pre_g1_lock(current_lock) == pre_g1_lock(old_lock)
    assert backend["unchanged_package_records"] == 53
    assert set(backend["packages"]) == {"certifi", "pillow"}


@pytest.mark.parametrize("package", ["certifi", "pillow"])
@pytest.mark.parametrize("mutation", ["version", "hash"])
def test_backend_security_successor_mutations_retain_original_guard(
    package: str, mutation: str
) -> None:
    governed = backend_security_authority()
    raw = (ROOT / governed["file"]).read_bytes().replace(b"\r\n", b"\n")
    row = governed["packages"][package]
    after = row["after_block"].encode()
    changed = (
        after.replace(row["proposed_version"].encode(), b"0.0.0", 1)
        if mutation == "version"
        else after.replace(b"--hash=sha256:", b"--hash=sha256:0", 1)
    )
    mutated = raw.replace(after, changed, 1)
    assert pre_d3_backend_dependency(mutated) == mutated
    with pytest.raises(AssertionError, match="F8_G1_LOCK_IDENTITY_INVALID"):
        pre_g1_lock(mutated)


@pytest.mark.parametrize("mutation", ["count", "new-pdf", "old-pdf", "security"])
def test_bounded_successor_rejects_workflow_drift(mutation: str) -> None:
    from tests.hybrid_workspace_governance import pre_p2_workflow

    raw = pre_p2_workflow((ROOT / ".github/workflows/ci.yml").read_bytes())
    before, after = {
        "count": (
            f"--expected-tests {authority()['backend_tests']}".encode(),
            b"--expected-tests 1",
        ),
        "new-pdf": (b"hybrid-workflow-pdfs/", b"missing-workflow-pdfs/"),
        "old-pdf": (b"hyb1-review-pdfs/", b"missing-d2-pdfs/"),
        "security": (b"full security audit", b"missing security audit"),
    }[mutation]
    with pytest.raises(AssertionError, match="D3_WORKFLOW_IDENTITY"):
        pre_d3_workflow(raw.replace(before, after))


def test_successor_manifest_is_exact() -> None:
    raw = (ROOT / "docs/governance/HYB2_D3_P1_WORKFLOW_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="D3_WORKFLOW_AUTHORITY_IDENTITY"):
        authority(raw + b" ")
    raw = (ROOT / "docs/governance/HYB2_D3_P1_BACKEND_SECURITY_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="D3_BACKEND_SECURITY_AUTHORITY_INVALID"):
        backend_security_authority(raw + b" ")
