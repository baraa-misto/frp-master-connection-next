"""Controlled package and phase-aware evidence catalogue, not substitute engineering tests."""

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
MATRIX = ROOT / "backend/tests/golden/stage_4_5_acceptance_matrix_rc1.json"
ORDER = (
    ROOT
    / "docs/governance"
    / "FRP_MASTER_CONNECTION_STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_CODEX_ORDER_RC1.md"
)
CATALOGUE = ROOT / "docs/qa/STAGE_4_5_COLUMN_MOMENT_BASES.md"


def test_package_hashes_and_contiguous_matrix() -> None:
    assert hashlib.sha256(ORDER.read_bytes()).hexdigest().upper() == (
        "6D6CCA01C8AE979BF00F369D6D36317AE98E41BC8BF0F2DA4020F429B1614135"
    )
    assert hashlib.sha256(MATRIX.read_bytes()).hexdigest().upper() == (
        "68695DFC75C51E85982ED07E76ED7A4D0B344F1CCE7AE4425A9842260967074D"
    )
    assert (
        ORDER.read_text()
        .strip()
        .endswith(
            "**END OF STAGE 4.5 W/I RHS SRS COLUMN MOMENT BASES ORDER RC1"
            " - DO NOT PROCEED IF THIS LINE IS MISSING**"
        )
    )
    matrix = json.loads(MATRIX.read_text())
    assert [v["id"] for v in matrix["checks"]] == [f"T45-{i:03}" for i in range(1, 121)]
    assert [v["id"] for v in matrix["reference_fixtures"]] == [f"F45-{i:02}" for i in range(1, 25)]
    assert (
        len(matrix["section_presets"])
        * len(matrix["layouts"])
        * len(matrix["load_cases"])
        * len(matrix["units"])
        == 360
    )
    assert len(matrix["qualified_integration_load_ids"]) * 5 * 3 * 2 == 90
    assert set(re.findall(r"F45-\d{2}", json.dumps(matrix))) == {
        f"F45-{i:02}" for i in range(1, 25)
    }
    rows = [v for v in CATALOGUE.read_text().splitlines() if v.startswith("| T45-")]
    assert len(rows) == 120
    assert [v.split("|")[1].strip() for v in rows] == [f"T45-{i:03}" for i in range(1, 121)]


@pytest.mark.parametrize("identifier", [f"T45-{i:03}" for i in range(1, 121)])
def test_requirement_has_resolvable_evidence_and_truthful_phase(identifier: str) -> None:
    rows = [v for v in CATALOGUE.read_text().splitlines() if v.startswith(f"| {identifier} |")]
    assert len(rows) == 1
    row = rows[0]
    for path, function in re.findall(
        r"((?:backend|frontend)/tests/[A-Za-z0-9_/.]+)(?:::([a-z_0-9]+))?", row
    ):
        assert (ROOT / path).is_file(), path
        if function:
            module = ast.parse((ROOT / path).read_text())
            assert function in {
                n.name
                for n in ast.walk(module)
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            }, function
    if identifier in {"T45-100", "T45-115", "T45-116", "T45-117", "T45-118", "T45-119", "T45-120"}:
        assert "PENDING" in row
    assert "http://127.0.0.1" not in row or identifier == "T45-120"
