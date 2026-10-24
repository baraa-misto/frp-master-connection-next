"""Report-only presentation of authenticated owner geometry and incomplete evidence."""

from __future__ import annotations

import io
from copy import deepcopy

import pytest
from pypdf import PdfReader

from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body


@pytest.mark.parametrize("unknown", [False, True])
def test_current_report_preserves_native_snapshot_and_diagnostic_boundary(unknown: bool) -> None:
    body = owner_body(si=unknown)
    if unknown:
        body["assignments"]["default_conditions"].update(moisture="UNKNOWN", chemical="UNKNOWN")
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert response.status_code == 200
    result = response.json()
    signer = SnapshotSigner(b"DIRECT-OR2-REPORT-ONLY-QA-AUTHORITY-32")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="or2"
        ),
        account_id="or2",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions(mode="ENGINEER_REPORT"))
    reader = PdfReader(io.BytesIO(pdf))
    text = " ".join(" ".join(page.extract_text() or "" for page in reader.pages).split())
    assert "NUMERICAL CHECKS" in text
    assert "DESIGN COMPLETENESS" in text
    assert ("14.3002" if unknown else "0.563") in text
    assert "Angle dimensions" in text
    assert "W dimensions" in text
    assert ("leg y: 101.6 mm" if unknown else "leg y: 4 in") in text
    assert ("overall depth: 203.2 mm" if unknown else "overall depth: 8 in") in text
    assert "Washer dimensions / placement" in text
    assert ("thickness: 1.2954 mm" if unknown else "thickness: 0.051 in") in text
    assert "SINGLE_LAP" in text
    assert ("adjusted resistance unavailable" in text) is unknown
    assert (snapshot.request, snapshot.result) == original
    assert len(reader.pages) <= 10


def test_missing_basic_input_report_keeps_actual_conditions_and_no_results() -> None:
    body = owner_body()
    body["assignments"]["default_conditions"]["sustained_temperature"]["value"] = ""
    preview = call("POST", "/api/v1/calculations/multi-row/preview", body["legacy_request"]).json()
    signer = SnapshotSigner(b"DIRECT-OR2-REPORT-ONLY-QA-AUTHORITY-32")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="input_only", request=body, result=preview, account_id="or2"
        ),
        account_id="or2",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions(mode="ENGINEER_REPORT"))
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "no engineering design check performed" in text
    assert "Submitted project conditions" in text
    assert "maximum temperature" in text
    assert "70 degF" in text
    assert "0 supported checks evaluated" in text
    assert "DESIGN COMPLETENESS: not assessed" in text
    assert (snapshot.request, snapshot.result) == original
