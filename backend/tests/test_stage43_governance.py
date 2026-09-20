"""Tagless-portable authority/catalogue identity and historical object proofs."""

import hashlib
import json
from pathlib import Path

import pytest

from frp_master_connection.domain.wi_frp_support_moment import SupportMode
from tests.application.wi_frp_support_fixture_views import frontend_fixture
from tests.calculation.test_stage_4_1_beam_moment_splice_family_freeze_manifest import (
    _available,
    _text,
)

ROOT = Path(__file__).resolve().parents[2]
HASHES = {
    "docs/qa/STAGE_4_3_NATIVE_FIXTURE_CATALOGUE.json": (
        "F8A15BEBD6351045C311341D40A4F97331DB31BE59F49BE9C005F2796A981D8E"
    ),
    "docs/qa/STAGE_4_3_INHERITED_IDENTITIES.json": (
        "061081B63B21960DD3501C28EE667499B4D03794ED936AE11E29AACA08A7E471"
    ),
    "frontend/tests/fixtures/wiFrpSupportMoment_CHANNEL_WEB.json": (
        "3FB70AA3597A71163BDE2DC87AAE614BE095C355A6528A33C345DA8A3AB22E05"
    ),
    "frontend/tests/fixtures/wiFrpSupportMoment_HOLLOW_SQUARE.json": (
        "683DAFD1710F34D83B8E9855F9BFBD913AADE3A58EF075C60B82F99BA6AFE02B"
    ),
    "frontend/tests/fixtures/wiFrpSupportMoment_SOLID_SQUARE.json": (
        "2B6711E61C408D99635C22797D389CB4CD2823A9E1D4DA5156C06B04B86323A6"
    ),
    "frontend/tests/fixtures/wiFrpSupportMoment_WI_FLANGE.json": (
        "69544066756D52F16F95407AC4964E7A40E2876EB824B4BAA7706E8C95ACF81E"
    ),
    "frontend/tests/fixtures/wiFrpSupportMoment_WI_WEB.json": (
        "672B4902F12A269EC445CB5D81097AA09A9E78CC630D1CC11ADD506E8B736A49"
    ),
}


def test_t43_085_087_sealed_catalogue_and_historical_identity_record() -> None:
    matrix = json.loads(
        (ROOT / "backend/tests/golden/stage_4_3_acceptance_matrix_rc1.json").read_text(
            encoding="utf-8"
        )
    )
    coverage = json.loads(
        (ROOT / "docs/qa/STAGE_4_3_ACCEPTANCE_COVERAGE.json").read_text(encoding="utf-8")
    )
    assert [row["id"] for row in coverage["requirements"]] == [
        row["id"] for row in matrix["acceptance_checks"]
    ]
    assert len(coverage["requirements"]) == 90
    for requirement, proof in zip(
        matrix["acceptance_checks"], coverage["requirements"], strict=True
    ):
        assert proof["fixture_ids"] == requirement.get("fixture_ids", [])
        assert all((ROOT / path).is_file() for path in proof["evidence_paths"])
    handoff = json.loads((ROOT / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    assert handoff["stage_4_3_rc1"]["contract"] == "4.3-RC1"
    assert handoff["stage_4_3_rc1"]["owner_final_visual_result_acceptance"] == "PENDING"
    assert handoff["stage_4_3_rc1"]["new_tag_authorized"] is False
    for path, expected in HASHES.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == expected
    manifest = json.loads(
        (ROOT / "docs/qa/STAGE_4_3_INHERITED_IDENTITIES.json").read_text(encoding="utf-8")
    )
    assert len(manifest["tags"]) == 10
    assert len(manifest["files"]) == 446
    assert len({entry["path"] for entry in manifest["files"]}) == 446
    baseline = manifest["baseline"]
    assert baseline == "c8094293e6da49aa830b5801f49aae537cccae2b"
    if _available(ROOT, f"{baseline}^{{commit}}"):
        historical = _text(ROOT, "ls-tree", "-r", baseline)
        blobs = {line.split("\t", 1)[1]: line.split()[2] for line in historical.splitlines()}
        assert all(blobs[row["path"]] == row["blob"] for row in manifest["files"])
    # Otherwise the hash-sealed historical manifest is the only allowed fallback.
    # Never compare a legitimate successor HEAD tree with a historical source tree.
    refs = _text(
        ROOT, "for-each-ref", "--format=%(refname:short) %(objectname) %(*objectname)", "refs/tags"
    )
    existing = {line.split()[0]: tuple(line.split()[1:]) for line in refs.splitlines()}
    for tag in manifest["tags"]:
        if tag["name"] in existing:
            assert existing[tag["name"]] == (tag["object"], tag["peeled"])


@pytest.mark.parametrize("mode", list(SupportMode))
def test_t43_native_frontend_projection_is_reproducible_not_a_second_numeric_engine(
    mode: SupportMode,
) -> None:
    path = ROOT / f"frontend/tests/fixtures/wiFrpSupportMoment_{mode.value}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == frontend_fixture(mode)
