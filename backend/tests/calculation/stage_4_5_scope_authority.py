"""Exact historical authority and explicitly bounded Stage 4.5 candidate scope."""

import hashlib
import json
from pathlib import Path
from typing import Any

from tests.calculation.stage_4_4_scope_authority import (
    indexed_entries,
    project_registered_successor,
)

BASELINE_COMMIT = "99befa9780e7c7abf72c8a33e5eb45b9e368d916"
BASELINE_TREE = "28ec1c7ad92a4ea364c6f47885869a2c63cfd359"
EVIDENCE_SHA256 = "228C2FED59159D1D673D343523EC068FA9793FF57FFBD81232B578AF1B462236"
ADDITIONS = frozenset(
    {
        "backend/src/frp_master_connection/api/column_moment_base.py",
        "backend/src/frp_master_connection/application/column_moment_base_design.py",
        "backend/src/frp_master_connection/application/column_moment_base_geometry.py",
        "backend/src/frp_master_connection/application/column_moment_base_local.py",
        "backend/src/frp_master_connection/application/column_moment_base_paths.py",
        "backend/src/frp_master_connection/application/column_moment_base_preview.py",
        "backend/src/frp_master_connection/application/column_moment_base_profile.py",
        "backend/src/frp_master_connection/application/column_moment_base_qualification.py",
        "backend/src/frp_master_connection/application/column_moment_base_sources.py",
        "backend/src/frp_master_connection/calculation/column_moment_base_response.py",
        "backend/src/frp_master_connection/domain/column_moment_base.py",
        "backend/tests/api/test_column_moment_base_api.py",
        "backend/tests/application/column_moment_base_fixtures.py",
        "backend/tests/application/test_column_moment_base_native_local.py",
        "backend/tests/application/test_column_moment_base_negative.py",
        "backend/tests/application/test_column_moment_base_preview.py",
        "backend/tests/application/test_column_moment_base_qualified.py",
        "backend/tests/calculation/stage_4_5_scope_authority.py",
        "backend/tests/calculation/test_stage_4_5_acceptance.py",
        "backend/tests/calculation/test_stage_4_5_references.py",
        "backend/tests/calculation/test_stage_4_5_scope_authority.py",
        "backend/tests/golden/stage_4_5_acceptance_matrix_rc1.json",
        "backend/tests/golden/stage_4_5_historical_scope_evidence.json",
        "docs/engineering/STAGE_4_5_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_CODEX_ORDER_RC1.md",
        "docs/qa/STAGE_4_5_COLUMN_MOMENT_BASES.md",
        "frontend/src/api/columnMomentBaseClient.ts",
        "frontend/src/api/columnMomentBaseContracts.ts",
        "frontend/src/visualization/columnMomentBaseSceneModel.ts",
        "frontend/src/workspace/ColumnMomentBaseWorkspace.tsx",
        "frontend/src/workspace/columnMomentBaseWorkflow.ts",
        "frontend/src/workspace/columnMomentBaseWorkspace.css",
        "frontend/tests/columnMomentBase.test.tsx",
        "frontend/tests/columnMomentBaseClient.test.ts",
        "frontend/tests/columnMomentBaseNegative.test.tsx",
        "frontend/tests/columnMomentBaseR1.test.tsx",
        "frontend/tests/fixtures/columnMomentBase.json",
    }
)
GLUE = {
    "backend/src/frp_master_connection/api/routes.py": (
        "95c0d1b7f897bf87085f0234f6ec6c55bee7954c",
        "fbbdebf37e7ef2e411c8fa95df1d96cd3f86a195",
    ),
    "backend/tests/calculation/test_scope_boundaries.py": (
        "3115e6936f0ab26c0c332bb49e65cff1e11889f8",
        "db2b0ea955a354e902a3e0f4844ef422c5be9f47",
    ),
    "backend/tests/calculation/test_stage_4_4_scope_authority.py": (
        "95b4b11d7c778e4fb52d703241adaa877857194b",
        "133580ef6df87a0acedd140d4bdcb6d3c16c43b6",
    ),
    "backend/tests/test_api.py": (
        "6600dcc4d125a26d2d50707fe72b0de9c84f76a6",
        "d7874d92917a57167e13ba1de06ab7caf2efb0c2",
    ),
    "backend/tests/test_calculation_api.py": (
        "29288b96b5368a320ff3297a0f8bc74a2e6fcd52",
        "876185b43929c5e0b10c24fe79a9afc2ae2eca83",
    ),
    "docs/engineering/ENGINEERING_SOURCE_REGISTER.md": (
        "937f8b12ca6ffb94fa93c1175f31da3dfc5ab185",
        "20e4d85d83623610269fab85d5e21a96f580b9c8",
    ),
    "frontend/src/workspace/MomentConnectionsWorkspace.tsx": (
        "8f5c176c8e0201d06c6c264c1e1632148a7e5d9d",
        "eeab07e020e49484f8e6819998bda96d1f5ab9e4",
    ),
}

# Freeze order section 14 and the owner's byte-preserving archive clarification.
# Only these new governance records are registered; no existing historical
# content, production module, test family, dependency or workflow is exempted.
FREEZE_ADDITIONS = frozenset(
    {
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_FREEZE_CODEX_ORDER.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_UI_DEFAULTS_AND_ACTION_RENDERING_CORRECTION_ORDER_R1.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_CENTERED_ANGLES_AND_TWO_BOLT_DEFAULT_CORRECTION_ORDER_R2.md",
        "docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_WINDOWS_FRONTEND_TIMING_CORRECTION_ORDER_R3.md",
        "docs/governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json",
        "docs/governance/STAGE_4_5_FREEZE_ARTIFACT_REGISTER.md",
        "docs/qa/STAGE_4_5_FREEZE.md",
    }
)


def evidence(raw: str | None = None) -> dict[str, Any]:
    if raw is None:
        raw = (
            Path(__file__).parents[1] / "golden/stage_4_5_historical_scope_evidence.json"
        ).read_text(encoding="utf-8")
    assert hashlib.sha256(raw.encode()).hexdigest().upper() == EVIDENCE_SHA256, (
        "historical evidence SHA-256"
    )
    value: dict[str, Any] = json.loads(raw)
    assert value["commit"] == BASELINE_COMMIT
    assert value["tree"] == BASELINE_TREE
    assert len(value["tags"]) == 12
    return value


def stage45_predecessor_entries(entries: str) -> str:
    indexed = indexed_entries(entries)
    # Original-scope counterfactual probes remain original-scope checks. Real
    # Stage 4.5 candidates necessarily include the separately tested product files.
    if not ADDITIONS.intersection(indexed):
        return entries
    historical = str(evidence()["entries"])
    projected = project_registered_successor(
        entries, historical, ADDITIONS | FREEZE_ADDITIONS, GLUE, frozenset()
    )
    assert indexed_entries(projected) == indexed_entries(historical), (
        "protected content / protected test outside exact Stage 4.5 candidate inventory"
    )
    return historical


def frozen_stage45_entries(raw: str | None = None) -> str:
    """Resolve the historical candidate from its already-frozen offline authority.

    Past task allowlists are not perpetual current-tree restrictions. Counterfactual
    tamper probes still pass through the original exact predecessor/digest checks.
    Current CME scope is reviewed separately against its explicit task path list.
    """
    if raw is None:
        raw = (
            Path(__file__).parents[3]
            / "docs/governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json"
        ).read_text(encoding="utf-8")
    assert (
        hashlib.sha256(raw.encode()).hexdigest()
        == "4acf09e480ff843e7700fd580efff347611dcd523e93c523381e8d51a5eb1b4e"
    ), "historical Stage 4.5 manifest identity"
    manifest = json.loads(raw)
    entries: str = manifest["historical_git_entries"]
    assert (
        hashlib.sha256(entries.encode()).hexdigest().upper()
        == "2A7ECAD5640A22478D1A98A6668BFCA97408C8694E176058C860188417B9C5E5"
    ), "historical Stage 4.5 tree identity"
    return entries
