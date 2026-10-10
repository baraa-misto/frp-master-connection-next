"""Actual immutable signed reports expose MC1 factor provenance and limits."""

import io
from copy import deepcopy
from decimal import Decimal

import pytest
from pypdf import PdfReader
from tests.api.test_f593_f4 import design
from tests.direct_mc1_fixtures import mc1_body, mc1_other_resin_body

from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


@pytest.mark.parametrize("chemical", ["NONE_DECLARED", "SPECIFIED"])
def test_signed_engineer_report_reads_factors_and_preserves_snapshot(chemical: str) -> None:
    body = mc1_body(
        chemical=chemical,
        **({"chemical_strength_factor": ".80"} if chemical == "SPECIFIED" else {}),
    )
    result = design(body)
    signer = SnapshotSigner(b"MC1-AUTHENTIC-REPORT-QA-KEY-LOCAL-ONLY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="mc1-qa"
        ),
        account_id="mc1-qa",
    )
    before = deepcopy((snapshot.request, snapshot.result, snapshot.input_provenance))
    pdf = render_report_pdf(snapshot, ReportOptions())
    text = " ".join(
        " ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(pdf)).pages
    )
    assert "Design Temperature" in text
    assert "conservatively assumed sustained" in text
    assert "actual product Tg not measured" in text
    assert "YELLOW" in text
    if chemical == "SPECIFIED":
        assert "Engineer-specified strength-only CCH=.80" in text
        assert "UNEVALUATED (chemical modulus)" in text
        assert "No chemical-modulus" in text
        modulus = [item for item in result["material_ledgers"] if "modulus" in item["property_id"]]
        assert all(item["adjusted_candidate"] is None for item in modulus)
        assert all(
            Decimal(item["independent_moisture_temperature_candidate"]) > 0 for item in modulus
        )
    else:
        assert "None declared; no chemical adjustment." in text
    assert before == (snapshot.request, snapshot.result, snapshot.input_provenance)


@pytest.mark.parametrize("source", ["over-140", "other-resin"])
def test_temperature_blocked_reports_keep_frp_unevaluated_and_raw_audit_evidence(
    source: str,
) -> None:
    body = mc1_body("140.0001") if source == "over-140" else mc1_other_resin_body()
    result = design(body)
    signer = SnapshotSigner(b"MC1-AUTHENTIC-REPORT-QA-KEY-LOCAL-ONLY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="mc1-qa"
        ),
        account_id="mc1-qa",
    )
    before = deepcopy((snapshot.request, snapshot.result, snapshot.input_provenance))
    for mode in ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"):
        pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
        text = " ".join(
            " ".join((page.extract_text() or "").split())
            for page in PdfReader(io.BytesIO(pdf)).pages
        )
        assert (
            "Test-based temperature factor required above 140"
            if source == "over-140"
            else "Temperature adjustment model required for the selected resin."
        ) in text
        assert text.count("SOURCE REQUIRED — NOT EVALUATED.") == 6
        if mode == "FULL_TECHNICAL_AUDIT":
            assert "raw_engine_diagnostic_field_changes" in "".join(text.split())
    assert result["final_decision"]["analytical_check_summary"]["evaluated"] == 2
    assert before == (snapshot.request, snapshot.result, snapshot.input_provenance)
