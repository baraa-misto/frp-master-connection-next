"""Completeness of the evidence index is distinct from passing its referenced gates."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[3]


def test_all_80_requirements_have_real_test_or_direct_evidence_paths() -> None:
    source = json.loads(
        (
            ROOT
            / "backend/tests/golden"
            / "FRP_MASTER_CONNECTION_CME_1_ACCEPTANCE_AND_REFERENCE_FIXTURES_RC1.json"
        ).read_text()
    )
    mapped = json.loads((ROOT / "docs/engineering/CME_1_ACCEPTANCE_EVIDENCE_MAP.json").read_text())
    assert [r["id"] for r in mapped["requirements"]] == [r["id"] for r in source["requirements"]]
    assert len(mapped["requirements"]) == 80
    for original, row in zip(source["requirements"], mapped["requirements"], strict=True):
        assert row["requirement"] == original["requirement"]
        assert row["reference_fixture_ids"] == original["reference_fixture_ids"]
        assert row["evidence"]
        for path in row["evidence"]:
            assert (ROOT / path).is_file(), path
