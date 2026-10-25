"""P4 exact workflow and two-path boundary; preserve every inherited gate."""

from pathlib import Path

import pytest

from tests.hybrid_physical_governance import authority, pre_p4_workflow
from tests.hybrid_same_connection_governance import pre_p3_workflow
from tests.hybrid_security_successor import ROOT, digest, pre_s1_workflow


@pytest.mark.parametrize("crlf", [False, True])
def test_p4_workflow_exact_predecessor_and_line_endings(crlf: bool) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    if crlf:
        raw = raw.replace(b"\n", b"\r\n")
    previous = pre_p4_workflow(raw)
    assert digest(previous) == authority()["before_sha256"]
    assert pre_p4_workflow(previous) == previous
    assert pre_s1_workflow(raw) == pre_s1_workflow(previous)
    assert pre_p3_workflow(raw) == pre_p3_workflow(previous)
    assert b"Verify P4-S1 installed pins" in previous
    assert b"Audit all dependencies" in previous
    assert b"Audit runtime dependencies" in previous
    assert b"Generate same-connection Hybrid P3 reports" in previous
    assert b"--expected-tests 9535" in previous
    assert authority()["protected_engineering"] == 53
    assert authority()["historical_controls"] == 173
    assert authority()["dependency_changes"] == []
    assert authority()["coverage_thresholds"] == [100, 100, 100, 100]


def test_p4_authority_is_exact() -> None:
    raw = (ROOT / "docs/governance/HYB2_D3_P4_WORKFLOW_SUCCESSOR.json").read_bytes()
    with pytest.raises(AssertionError, match="P4_WORKFLOW_AUTHORITY_INVALID"):
        authority(raw + b" ")


@pytest.mark.parametrize("change", ["count", "new_report", "old_report", "security"])
def test_actual_p4_workflow_mutations_fail_closed(change: str) -> None:
    raw = (ROOT / ".github/workflows/ci.yml").read_bytes().replace(b"\r\n", b"\n")
    before, after = {
        "count": (
            f"--expected-tests {authority()['backend_tests']}".encode(),
            b"--expected-tests 1",
        ),
        "new_report": (b"hybrid-physical-pdfs/", b"missing-physical-pdfs/"),
        "old_report": (b"hybrid-same-connection-pdfs/", b"missing-predecessor-pdfs/"),
        "security": (b"full security audit", b"missing security audit"),
    }[change]
    assert before in raw
    changed = raw.replace(before, after)
    assert pre_p4_workflow(changed) == changed
    with pytest.raises(AssertionError, match="P3_WORKFLOW_IDENTITY_INVALID"):
        pre_p3_workflow(changed)


@pytest.mark.parametrize("crlf", [False, True])
def test_p4_boundary_reconstructs_exact_immutable_p3_guard(crlf: bool) -> None:
    from tests.hybrid_physical_governance import pre_p4_inactive_boundary

    governed = authority()["inactive_boundary_guard"]
    raw = (ROOT / governed["path"]).read_bytes()
    if crlf:
        raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    original = pre_p4_inactive_boundary(raw)
    assert digest(original) == ("46BCB728E7B2D0A64A28C8BBC105C3D055705BEFCEFA4F890D629FFB4972D33E")
    assert pre_p4_inactive_boundary(original) == original
    assert governed["approved_application_paths"] == [
        "application/hybrid_physical.py",
        "application/hybrid_physical_geometry.py",
    ]
    for assertion in (
        'assert "hyb1" not in source.lower(), str(path)',
        'assert "rhm_reference" not in source, str(path)',
        'assert "rhm_direct_r3" not in source, str(path)',
        'assert "hyb2_direct_r3" not in source, str(path)',
        'assert "hyb2_d2" not in source, str(path)',
        'assert "HYB1" not in path.read_text(encoding="utf-8")',
    ):
        assert original.count(assertion.encode()) == 1
        assert raw.count(assertion.encode()) == 1


@pytest.mark.parametrize("mutation", ["broad", "third_path", "assertion", "note", "path"])
def test_p4_boundary_mutations_fail_closed(mutation: str) -> None:
    from tests.hybrid_physical_governance import pre_p4_inactive_boundary

    governed = authority()["inactive_boundary_guard"]
    raw = (ROOT / governed["path"]).read_bytes().replace(b"\r\n", b"\n")
    before, after = {
        "broad": (
            b"path not in approved_p4_paths",
            b'path.name != "hybrid_physical.py"',
        ),
        "third_path": (
            b'root / "application/hybrid_physical.py",',
            b'root / "api/hybrid_physical.py",',
        ),
        "assertion": (
            b'assert "rhm_reference" not in source, str(path)',
            b"assert True",
        ),
        "note": (b"P4 candidate-only adapters", b"P4 any adapters"),
        "path": (
            b"application/hybrid_physical_geometry.py",
            b"application/extra/hybrid_physical_geometry.py",
        ),
    }[mutation]
    assert raw.count(before) == 1
    with pytest.raises(AssertionError, match="P4_INACTIVE_BOUNDARY_IDENTITY_INVALID"):
        pre_p4_inactive_boundary(raw.replace(before, after))


@pytest.mark.parametrize(
    "relative",
    [
        "api/hybrid_physical.py",
        "api/p4_native_import_probe.py",
        "reporting/hybrid_physical_geometry.py",
        "application/nested/hybrid_physical.py",
        "application/hybrid_physical_alias.py",
    ],
)
@pytest.mark.parametrize(
    "prohibited",
    ["hyb1_contract", "rhm_reference", "rhm_direct_r3", "hyb2_direct_r3", "hyb2_d2"],
)
def test_actual_p4_boundary_rejects_unapproved_full_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
    prohibited: str,
) -> None:
    from tests.application import test_hyb1_inactive_boundary as boundary

    root = tmp_path / "backend/src/frp_master_connection"
    target = root / relative
    target.parent.mkdir(parents=True)
    target.write_text(f"import {prohibited}\n", encoding="utf8")
    frontend = tmp_path / "frontend/src/example.tsx"
    frontend.parent.mkdir(parents=True)
    frontend.write_text("export const example = 1;\n", encoding="utf8")
    monkeypatch.setattr(
        boundary, "__file__", str(tmp_path / "backend/tests/application/boundary.py")
    )
    with pytest.raises(AssertionError) as rejected:
        boundary.test_no_existing_public_module_imports_hyb1_or_rhm()
    assert str(target) in str(rejected.value)


def test_actual_p4_boundary_accepts_only_approved_application_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.application import test_hyb1_inactive_boundary as boundary

    root = tmp_path / "backend/src/frp_master_connection"
    for relative in authority()["inactive_boundary_guard"]["approved_application_paths"]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("from hyb1_contract import Alignment\nimport rhm_direct_r3\n")
    frontend = tmp_path / "frontend/src/example.tsx"
    frontend.parent.mkdir(parents=True)
    frontend.write_text("export const example = 1;\n")
    monkeypatch.setattr(
        boundary, "__file__", str(tmp_path / "backend/tests/application/boundary.py")
    )
    boundary.test_no_existing_public_module_imports_hyb1_or_rhm()


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (
            "application/hybrid_physical.py",
            {
                "frp_master_connection.application.hyb1_contract": {
                    "ActionBasis",
                    "Alignment",
                    "PairedActions",
                },
                "frp_master_connection.application.hyb1_review": {"ComparisonRow"},
                "frp_master_connection.application.hyb2_d2": {"D2Assessment"},
                "frp_master_connection.calculation.rhm_direct_r3": {
                    "R3Geometry",
                    "geometry_digest",
                },
            },
        ),
        (
            "application/hybrid_physical_geometry.py",
            {
                "frp_master_connection.calculation.rhm_direct_corrections": {"Point"},
                "frp_master_connection.calculation.rhm_direct_r3": {
                    "Edge",
                    "R3Geometry",
                    "_edges",
                    "_fit",
                    "_frame",
                },
                "frp_master_connection.calculation.rhm_direct_reference": {"sincos"},
                "frp_master_connection.calculation.rhm_reference": {"PRECISION"},
            },
        ),
    ],
)
def test_p4_exceptions_import_only_existing_contracts_and_geometry_helpers(
    relative: str, expected: dict[str, set[str]]
) -> None:
    import ast

    source = (ROOT / "backend/src/frp_master_connection" / relative).read_text()
    tree = ast.parse(source)
    actual = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if any(token in node.module for token in ("hyb1", "hyb2", "rhm_")):
                actual[node.module] = {alias.name for alias in node.names}
        elif isinstance(node, ast.Import):
            assert not any(
                any(token in alias.name for token in ("hyb1", "hyb2", "rhm_"))
                for alias in node.names
            )
    assert actual == expected
