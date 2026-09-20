"""Test-only immutable evidence and explicitly registered successor scope.

The evidence was captured from the two actual original commit objects before
changing the historical assertion. It is not a digest of today's working tree.
Registration defines a candidate change scope, not engineering acceptance.
"""

import hashlib
import json
from pathlib import Path

EVIDENCE_SHA256 = "0A2CAC24EA9FA064097056E731CDFF9294D3CF872B8FE132850F9E51B5017540"
SECURITY_COMMIT = "513e1c9150e63206e432a8d2f971617b6ed9c203"
BASELINE_COMMIT = "1faa1ff522d0e0a39a42e2dc2d3974b5dba98479"
TREES = {
    SECURITY_COMMIT: "d91d0e294cdf6f5232f28d7581ec4f5aa53c210d",
    BASELINE_COMMIT: "7a7d30d489fa39a6c9ea5f44bebfa1779924ceec",
}

# Exact authorized new-product, test/evidence and governance paths; no globs.
STAGE44_ADDITIONS = frozenset(
    {
        "backend/src/frp_master_connection/api/angle_column_moment_base.py",
        "backend/src/frp_master_connection/domain/angle_column_moment_base.py",
        "backend/src/frp_master_connection/application/angle_column_base_design.py",
        "backend/src/frp_master_connection/application/angle_column_base_geometry.py",
        "backend/src/frp_master_connection/application/angle_column_base_local.py",
        "backend/src/frp_master_connection/application/angle_column_base_preview.py",
        "backend/src/frp_master_connection/application/angle_column_base_qualification.py",
        "backend/src/frp_master_connection/application/angle_column_base_sources.py",
        "backend/src/frp_master_connection/calculation/angle_column_base_response.py",
        "backend/tests/api/test_angle_column_moment_base_api.py",
        "backend/tests/application/angle_column_base_fixture.py",
        "backend/tests/application/test_angle_column_base_qualified.py",
        "backend/tests/application/test_angle_column_moment_base.py",
        "backend/tests/application/test_angle_column_base_negative.py",
        "backend/tests/calculation/test_angle_column_base_references.py",
        "backend/tests/calculation/test_stage_4_4_acceptance.py",
        "backend/tests/calculation/test_stage_4_4_scope_authority.py",
        "backend/tests/calculation/stage_4_4_scope_authority.py",
        "backend/tests/golden/stage_4_4_acceptance_matrix_rc1.json",
        "backend/tests/golden/stage_4_4_historical_scope_evidence.json",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CODEX_ORDER_RC1.md",
        "docs/engineering/STAGE_4_4_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md",
        "docs/qa/STAGE_4_4_ANGLE_COLUMN_MOMENT_BASE.md",
        "frontend/src/api/angleColumnMomentBaseClient.ts",
        "frontend/src/api/angleColumnMomentBaseContracts.ts",
        "frontend/src/visualization/angleColumnMomentBaseSceneModel.ts",
        "frontend/src/workspace/AngleColumnMomentBaseWorkspace.tsx",
        "frontend/src/workspace/angleColumnMomentBaseWorkflow.ts",
        "frontend/src/workspace/angleColumnMomentBaseWorkspace.css",
        "frontend/tests/angleColumnMomentBase.test.tsx",
        "frontend/tests/angleColumnMomentBaseNegative.test.tsx",
        "frontend/tests/fixtures/angleColumnMomentBase.json",
    }
)
STAGE44_GLUE = {
    # Add only the three new route names to each exact inventory. No existing
    # endpoint, client-authority assertion or engineering expectation changes.
    "backend/tests/test_api.py": (
        "f47c9511754993a162a618903ebf8e351e9b3b27",
        "6600dcc4d125a26d2d50707fe72b0de9c84f76a6",
    ),
    "backend/tests/test_calculation_api.py": (
        "547a1f1b79d59ec400657ba64d776a314ea942d1",
        "29288b96b5368a320ff3297a0f8bc74a2e6fcd52",
    ),
    "backend/src/frp_master_connection/api/routes.py": (
        "db00017d76ec555fb5edabef686ef20f1926c992",
        "95c0d1b7f897bf87085f0234f6ec6c55bee7954c",
    ),
    "frontend/src/workspace/MomentConnectionsWorkspace.tsx": (
        "51f80030b44ae6318cc17a529cfde2cb9a1cb025",
        "8f5c176c8e0201d06c6c264c1e1632148a7e5d9d",
    ),
}
STAGE44_GOVERNANCE = frozenset({"docs/engineering/ENGINEERING_SOURCE_REGISTER.md"})

# Freeze Order SHA-256 21FA8D17DCBBDE6ED6BA2C93892D5343347E5FE521EB2ACB98578E89F86A8836,
# sections 7 and 12: these three exact new governance paths only. Existing
# historical evidence, production registrations and shared-glue pins stay fixed.
STAGE44_FREEZE_ADDITIONS = frozenset(
    {
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_4_FREEZE_CODEX_ORDER.md",
        "docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json",
        "docs/qa/STAGE_4_4_FREEZE.md",
    }
)


def evidence(raw: str | None = None) -> dict[str, dict[str, str]]:
    if raw is None:
        raw = (
            Path(__file__).parents[1] / "golden/stage_4_4_historical_scope_evidence.json"
        ).read_text(encoding="utf-8")
    # Pins canonical Git text, independent of Windows checkout CRLF conversion.
    assert hashlib.sha256(raw.encode()).hexdigest().upper() == EVIDENCE_SHA256, (
        "historical evidence SHA-256"
    )
    parsed: dict[str, dict[str, str]] = json.loads(raw)
    assert {key: value["tree"] for key, value in parsed.items()} == TREES, (
        "historical tree identity"
    )
    return parsed


def indexed_entries(entries: str) -> dict[str, str]:
    lines = entries.splitlines()
    indexed = {line.split("\t")[1]: line for line in lines}
    assert len(indexed) == len(lines), "duplicate scope path"
    return indexed


def project_registered_successor(
    entries: str,
    historical_entries: str,
    additions: frozenset[str],
    glue: dict[str, tuple[str, str]],
    governance: frozenset[str],
) -> str:
    """Remove only an explicit registration; caller verifies every remaining pin.

    A future test-only registration can be passed independently of historical
    evidence. It does not silently register a future production path today.
    """
    indexed = indexed_entries(entries)
    old = indexed_entries(historical_entries)
    assert not additions.intersection(old), "new registration cannot exempt historical content"
    for path in additions:
        if path in indexed:
            assert indexed[path].startswith("100644 blob "), "unsafe new product path"
            del indexed[path]
    for path, (historical, successor) in glue.items():
        assert old.get(path) == f"100644 blob {historical}\t{path}", "historical glue identity"
        assert indexed.get(path) in {
            f"100644 blob {historical}\t{path}",
            f"100644 blob {successor}\t{path}",
        }, "protected shared glue"
        indexed[path] = old[path]
    for path in governance:
        assert path in old, "governance must have historical authority"
        assert indexed.get(path, "").startswith("100644 blob "), "missing/unsafe governance path"
        indexed[path] = old[path]
    return "\n".join(indexed[path] for path in sorted(indexed)) + "\n"


def stage44_predecessor_entries(entries: str) -> str:
    return project_registered_successor(
        entries,
        evidence()[SECURITY_COMMIT]["entries"],
        STAGE44_ADDITIONS | STAGE44_FREEZE_ADDITIONS,
        STAGE44_GLUE,
        STAGE44_GOVERNANCE,
    )
