"""Original historical pins, twelve tags, bounded successors and tamper rejection."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from tests.calculation import test_scope_boundaries as security
from tests.calculation.stage_4_4_scope_authority import (
    indexed_entries,
    project_registered_successor,
)
from tests.calculation.stage_4_5_scope_authority import (
    ADDITIONS,
    BASELINE_COMMIT,
    FREEZE_ADDITIONS,
    GLUE,
    evidence,
    frozen_stage45_entries,
    stage45_predecessor_entries,
)

ROOT = Path(__file__).parents[3]


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)  # noqa: S603,S607 - fixed read-only test commands


def test_original_snapshot_and_available_objects_tags_are_exact() -> None:
    snapshot = evidence()
    if git("cat-file", "-e", BASELINE_COMMIT).returncode == 0:
        assert git("ls-tree", "-r", BASELINE_COMMIT).stdout == snapshot["entries"]
        assert git("rev-parse", BASELINE_COMMIT + "^{tree}").stdout.strip() == snapshot["tree"]
    # Manifest-only mode is explicitly supported; no tag/object is fetched.
    for name, obj, commit in snapshot["tags"]:
        actual = git("rev-parse", "--verify", "refs/tags/" + name)
        if actual.returncode == 0:
            assert actual.stdout.strip() == obj
            assert git("rev-parse", "refs/tags/" + name + "^{}").stdout.strip() == commit
    historical = security._restore_historical_security_scope(snapshot["entries"])
    security._assert_security_protected_entries(historical)
    assert len(indexed_entries(snapshot["entries"])) == 781


@pytest.mark.parametrize("mutation", ["content", "add", "delete", "rename", "tree", "tag"])
def test_historical_snapshot_tampering_fails(mutation: str) -> None:
    raw = (ROOT / "backend/tests/golden/stage_4_5_historical_scope_evidence.json").read_text()
    changed = (
        raw + "\n"
        if mutation == "add"
        else raw[:-1]
        if mutation == "delete"
        else raw.replace(
            "README.md"
            if mutation in {"content", "rename"}
            else str(evidence()["tree"])
            if mutation == "tree"
            else str(evidence()["tags"][0][1]),
            "tampered",
            1,
        )
    )
    with pytest.raises(AssertionError, match="historical evidence"):
        evidence(changed)


def test_current_candidate_has_only_authorized_paths_and_retains_original_digest() -> None:
    entries = frozen_stage45_entries()
    assert stage45_predecessor_entries(entries) == evidence()["entries"]
    security._assert_security_scope(ROOT, entries)
    for path in ADDITIONS:
        assert (ROOT / path).is_file(), path


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/frp_master_connection/calculation/angle_connector_core.py",
        "backend/src/frp_master_connection/calculation/in_plane_wrench_demand.py",
        "frontend/package-lock.json",
        "frontend/vitest.config.ts",
        ".github/workflows/ci.yml",
        "backend/src/frp_master_connection/application/angle_column_base_design.py",
        "frontend/tests/angleColumnMomentBase.test.tsx",
        "docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json",
        "docs/qa/UNREGISTERED_FUTURE.md",
    ],
)
def test_no_unrelated_current_content_becomes_mutable(path: str) -> None:
    entries = indexed_entries(frozen_stage45_entries())
    entries[path] = f"100644 blob {'9' * 40}\t{path}"
    with pytest.raises(AssertionError, match="protected"):
        stage45_predecessor_entries("\n".join(entries.values()))


@pytest.mark.parametrize("path", tuple(GLUE))
def test_shared_glue_is_exact_not_module_wide_permission(path: str) -> None:
    entries = indexed_entries(frozen_stage45_entries())
    entries[path] = f"100644 blob {'8' * 40}\t{path}"
    with pytest.raises(AssertionError, match="protected shared glue"):
        stage45_predecessor_entries("\n".join(entries.values()))


def test_separately_registered_forward_probe_preserves_history_without_authorizing_it_now() -> None:
    old = str(evidence()["entries"])
    path = "docs/qa/EXPLICIT_FUTURE_PROBE.md"
    new = old + f"100644 blob {'1' * 40}\t{path}\n"
    projected = project_registered_successor(new, old, frozenset({path}), {}, frozenset())
    assert indexed_entries(projected) == indexed_entries(old)
    assert path not in ADDITIONS
    assert (
        hashlib.sha256(old.encode()).digest()
        == hashlib.sha256(str(evidence()["entries"]).encode()).digest()
    )


def test_freeze_registration_has_only_seven_exact_new_governance_paths() -> None:
    assert {
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_FREEZE_CODEX_ORDER.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_UI_DEFAULTS_AND_ACTION_RENDERING_CORRECTION_ORDER_R1.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_CENTERED_ANGLES_AND_TWO_BOLT_DEFAULT_CORRECTION_ORDER_R2.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_WINDOWS_FRONTEND_TIMING_CORRECTION_ORDER_R3.md",
        "docs/governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json",
        "docs/governance/STAGE_4_5_FREEZE_ARTIFACT_REGISTER.md",
        "docs/qa/STAGE_4_5_FREEZE.md",
    } == FREEZE_ADDITIONS
    assert not FREEZE_ADDITIONS.intersection(indexed_entries(str(evidence()["entries"])))
    assert not FREEZE_ADDITIONS.intersection(ADDITIONS)


@pytest.mark.parametrize(
    "paths", [(p,) for p in sorted(FREEZE_ADDITIONS)] + [tuple(sorted(FREEZE_ADDITIONS))]
)
def test_exact_freeze_additions_preserve_original_historical_digest(paths: tuple[str, ...]) -> None:
    entries = indexed_entries(frozen_stage45_entries())
    before = stage45_predecessor_entries("\n".join(entries.values()))
    for path in paths:
        entries[path] = f"100644 blob {'1' * 40}\t{path}"
    current = "\n".join(entries[p] for p in sorted(entries))
    assert stage45_predecessor_entries(current) == before == evidence()["entries"]
    security._assert_security_scope(ROOT, current)


@pytest.mark.parametrize("path", sorted(FREEZE_ADDITIONS))
def test_freeze_additions_reject_nonregular_file_modes(path: str) -> None:
    entries = indexed_entries(frozen_stage45_entries())
    entries[path] = f"120000 blob {'1' * 40}\t{path}"
    with pytest.raises(AssertionError, match="unsafe new product path"):
        stage45_predecessor_entries("\n".join(entries.values()))


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/frp_master_connection/calculation/angle_connector_core.py",
        "frontend/package-lock.json",
        ".github/workflows/ci.yml",
        "backend/tests/calculation/test_in_plane_wrench_demand.py",
        "frontend/tests/angleColumnMomentBase.test.tsx",
        "docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json",
        "docs/governance/UNREGISTERED_FUTURE_FREEZE.json",
        "docs/governance/ARTIFACT_AND_VERSION_REGISTER.md",
    ],
)
def test_freeze_registration_never_unlocks_other_content(path: str) -> None:
    entries = indexed_entries(frozen_stage45_entries())
    for new_path in FREEZE_ADDITIONS:
        entries[new_path] = f"100644 blob {'1' * 40}\t{new_path}"
    entries[path] = f"100644 blob {'9' * 40}\t{path}"
    with pytest.raises(AssertionError, match="protected"):
        stage45_predecessor_entries("\n".join(entries.values()))
