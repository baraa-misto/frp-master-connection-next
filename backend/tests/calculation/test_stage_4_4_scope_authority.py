"""Historical tamper detection and explicit current/forward successor boundaries."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from tests.calculation import test_scope_boundaries as scope
from tests.calculation.stage_4_4_scope_authority import (
    BASELINE_COMMIT,
    SECURITY_COMMIT,
    STAGE44_ADDITIONS,
    STAGE44_FREEZE_ADDITIONS,
    STAGE44_GLUE,
    TREES,
    evidence,
    indexed_entries,
    project_registered_successor,
)


def test_actual_historical_objects_match_captured_evidence_when_available() -> None:
    root = Path(__file__).parents[3]
    snapshot = evidence()
    scope._assert_security_protected_entries(snapshot[SECURITY_COMMIT]["entries"])
    for commit, record in snapshot.items():
        found = subprocess.run(  # noqa: S603 - pinned immutable historical commits
            ["git", "cat-file", "-e", commit],  # noqa: S607 - installed Git, pinned object
            cwd=root,
            capture_output=True,
            check=False,
        )
        if found.returncode == 0:
            tree = subprocess.run(  # noqa: S603 - pinned immutable historical commits
                ["git", "rev-parse", f"{commit}^{{tree}}"],  # noqa: S607
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            entries = subprocess.run(  # noqa: S603 - pinned immutable historical commits
                ["git", "ls-tree", "-r", commit],  # noqa: S607
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            assert tree == record["tree"]
            assert entries == record["entries"]
        # Tagless mode still checks the complete pinned original object listing,
        # not successor HEAD and not a skipped identity assertion.
        assert record["tree"] == TREES[commit]
        assert len(indexed_entries(record["entries"])) >= 744


@pytest.mark.parametrize("mutation", ["content", "add", "delete", "rename", "tree", "commit"])
def test_historical_snapshot_changes_never_become_authorized_successors(mutation: str) -> None:
    raw = (
        Path(__file__).parents[1] / "golden/stage_4_4_historical_scope_evidence.json"
    ).read_text()
    if mutation == "content":
        raw = raw.replace("README.md", "tampered.md", 1)
    elif mutation == "add":
        raw += "\n"
    elif mutation == "delete":
        raw = raw[:-2]
    elif mutation == "rename":
        raw = raw.replace("frontend/package.json", "frontend/package-renamed.json", 1)
    elif mutation == "tree":
        raw = raw.replace(TREES[SECURITY_COMMIT], "0" * 40)
    else:
        raw = raw.replace(SECURITY_COMMIT, BASELINE_COMMIT)
    with pytest.raises(AssertionError, match="historical evidence"):
        evidence(raw)


@pytest.mark.parametrize(
    "path",
    [
        "docs/qa/EXPLICIT_FUTURE_GOVERNANCE.md",
        "backend/src/frp_master_connection/application/explicit_future_product.py",
        "frontend/tests/explicit_future_maintenance.test.tsx",
    ],
)
def test_forward_successor_registration_does_not_redefine_history_or_authorize_it_now(
    path: str,
) -> None:
    historical = evidence()[SECURITY_COMMIT]["entries"]
    future = historical + f"100644 blob {'1' * 40}\t{path}\n"
    with pytest.raises(AssertionError, match="protected content"):
        scope._assert_security_protected_entries(future)
    projected = project_registered_successor(future, historical, frozenset({path}), {}, frozenset())
    scope._assert_security_protected_entries(projected)
    assert path not in STAGE44_ADDITIONS
    assert (
        hashlib.sha256(historical.encode()).digest()
        == hashlib.sha256(evidence()[SECURITY_COMMIT]["entries"].encode()).digest()
    )


@pytest.mark.parametrize("path", tuple(STAGE44_GLUE))
def test_shared_glue_has_exact_additive_scope_not_whole_module_permission(path: str) -> None:
    root = Path(__file__).parents[3]
    current = evidence()[BASELINE_COMMIT]["entries"]
    changed = "\n".join(
        f"100644 blob {'9' * 40}\t{path}" if line.endswith(f"\t{path}") else line
        for line in current.splitlines()
    )
    with pytest.raises(AssertionError, match="protected shared glue"):
        scope._assert_security_scope(root, changed)


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/frp_master_connection/calculation/angle_connector_core.py",
        "backend/src/frp_master_connection/calculation/in_plane_wrench_demand.py",
        "backend/src/frp_master_connection/calculation/wi_moment_resultants.py",
        "frontend/vitest.config.ts",
        ".github/workflows/ci.yml",
    ],
)
def test_stage44_registration_does_not_unlock_other_engineering_or_qa(path: str) -> None:
    root = Path(__file__).parents[3]
    current = evidence()[BASELINE_COMMIT]["entries"]
    indexed = indexed_entries(current)
    indexed[path] = f"100644 blob {'9' * 40}\t{path}"
    with pytest.raises(AssertionError, match="protected content"):
        scope._assert_security_scope(root, "\n".join(indexed[k] for k in sorted(indexed)))


def test_registration_cannot_masquerade_as_new_path_to_remove_historical_content() -> None:
    historical = evidence()[SECURITY_COMMIT]["entries"]
    with pytest.raises(AssertionError, match="cannot exempt historical"):
        project_registered_successor(
            historical, historical, frozenset({"README.md"}), {}, frozenset()
        )
    with pytest.raises(AssertionError, match="unsafe new product"):
        project_registered_successor(
            historical + f"120000 blob {'1' * 40}\tfuture.md\n",
            historical,
            frozenset({"future.md"}),
            {},
            frozenset(),
        )


def test_freeze_registration_is_only_the_three_owner_authorized_governance_paths() -> None:
    assert {
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_4_FREEZE_CODEX_ORDER.md",
        "docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json",
        "docs/qa/STAGE_4_4_FREEZE.md",
    } == STAGE44_FREEZE_ADDITIONS
    for record in evidence().values():
        assert not STAGE44_FREEZE_ADDITIONS.intersection(indexed_entries(record["entries"]))


@pytest.mark.parametrize(
    "paths",
    [(p,) for p in sorted(STAGE44_FREEZE_ADDITIONS)] + [tuple(sorted(STAGE44_FREEZE_ADDITIONS))],
)
def test_exact_freeze_governance_additions_preserve_original_security_digest(
    paths: tuple[str, ...],
) -> None:
    root = Path(__file__).parents[3]
    entries = indexed_entries(evidence()[BASELINE_COMMIT]["entries"])
    before = scope._restore_historical_security_scope("\n".join(entries.values()))
    for path in paths:
        entries[path] = f"100644 blob {'1' * 40}\t{path}"
    current = "\n".join(entries[p] for p in sorted(entries))
    assert scope._restore_historical_security_scope(current) == before
    scope._assert_security_scope(root, current)
    scope._assert_security_protected_entries(before)


@pytest.mark.parametrize("path", sorted(STAGE44_FREEZE_ADDITIONS))
def test_freeze_registration_rejects_unsafe_governance_modes(path: str) -> None:
    root = Path(__file__).parents[3]
    entries = indexed_entries(evidence()[BASELINE_COMMIT]["entries"])
    entries[path] = f"120000 blob {'1' * 40}\t{path}"
    with pytest.raises(AssertionError, match="unsafe new product path"):
        scope._assert_security_scope(root, "\n".join(entries[p] for p in sorted(entries)))


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/frp_master_connection/calculation/angle_connector_core.py",
        "frontend/package-lock.json",
        ".github/workflows/ci.yml",
        "backend/tests/calculation/test_in_plane_wrench_demand.py",
        "docs/governance/STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_FREEZE_MANIFEST.json",
        "docs/governance/UNREGISTERED_FUTURE_FREEZE.json",
    ],
)
def test_freeze_additions_do_not_unlock_any_other_protected_content(path: str) -> None:
    root = Path(__file__).parents[3]
    entries = indexed_entries(evidence()[BASELINE_COMMIT]["entries"])
    for new_path in STAGE44_FREEZE_ADDITIONS:
        entries[new_path] = f"100644 blob {'1' * 40}\t{new_path}"
    # Stage 4.3's already-registered aggregate governance is authenticated by its
    # own frozen audit; it is deliberately not a new Stage 4.4 path exemption.
    if path.endswith("STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_FREEZE_MANIFEST.json"):
        assert path not in STAGE44_FREEZE_ADDITIONS
        historical = evidence()[BASELINE_COMMIT]["entries"]
        altered = historical.replace(entries[path], f"100644 blob {'9' * 40}\t{path}")
        assert altered != historical
        raw = (
            Path(__file__).parents[1] / "golden/stage_4_4_historical_scope_evidence.json"
        ).read_text()
        with pytest.raises(AssertionError, match="historical evidence"):
            evidence(raw.replace(entries[path].split()[2], "9" * 40))
        return
    entries[path] = f"100644 blob {'9' * 40}\t{path}"
    with pytest.raises(AssertionError, match="protected"):
        scope._assert_security_scope(root, "\n".join(entries[p] for p in sorted(entries)))
