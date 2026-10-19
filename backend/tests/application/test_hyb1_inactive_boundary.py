"""No public reachability or forged original action transport in the HYB1 candidate."""

from dataclasses import replace
from pathlib import Path

import pytest

from frp_master_connection.calculation.quantities import Unit
from tests.hyb1_fixtures import paired, q


def test_no_existing_public_module_imports_hyb1_or_rhm() -> None:
    root = Path(__file__).parents[2] / "src/frp_master_connection"
    new_names = {
        "hyb1_contract.py",
        "hyb1_mapping.py",
        "hyb1_review.py",
        "rhm_reference.py",
        "rhm_workbook_case.py",
        "rhm_clip_tee_reference.py",
        "rhm_clip_tee_review.py",
        "rhm_direct_reference.py",
        "rhm_direct_corrections.py",
        "rhm_direct_correction_review.py",
        "rhm_direct_review.py",
        "hyb2_direct.py",
        "hyb2_status.py",
        "rhm_direct_r3.py",
        "hyb2_direct_r3.py",
        "rhm_direct_r3_review.py",
    }
    for path in root.rglob("*.py"):
        if path.name not in new_names:
            source = path.read_text(encoding="utf-8")
            assert "hyb1" not in source.lower(), str(path)
            assert "rhm_reference" not in source, str(path)
            assert "rhm_direct_r3" not in source, str(path)
            assert "hyb2_direct_r3" not in source, str(path)
    frontend_files = tuple((root.parents[2] / "frontend/src").rglob("*.tsx"))
    assert frontend_files
    for path in frontend_files:
        assert "HYB1" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("change", ["missing", "source", "moment", "frame"])
def test_audited_original_actions_cannot_be_grafted_or_zeroed(change: str) -> None:
    actions = paired()
    original = actions.lrfd[0]
    trace = {
        "missing": replace(original, case_id="MISSING"),
        "source": replace(original, source_id="OTHER"),
        "moment": replace(original, components=(*original.components[:5], q("1", Unit.KIP_IN))),
        "frame": replace(original, frame="OTHER"),
    }[change]
    with pytest.raises(ValueError, match=r"(Transport audit|Reference transport)"):
        replace(actions, transport_trace=(trace,))
