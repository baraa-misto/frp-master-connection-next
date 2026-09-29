"""OR1-10 default and session fastener identity through the Direct MAT1 route."""

from __future__ import annotations

import io
from copy import deepcopy
from decimal import Decimal
from typing import Any, cast

from pypdf import PdfReader
from tests.api.test_mat1_routes import call, condition, selection
from tests.api_fixtures import build_api_payload
from tests.application.test_direct_f1_safety import _direct_payload, _one_row_payload

from frp_master_connection.reporting.multirow_substitutions import multirow_native_substitution
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def _body() -> dict[str, Any]:
    record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][0]
    legacy = cast(dict[str, Any], _direct_payload())
    return {
        "contract": "MAT1-MULTI-ROW-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": selection(record),
            "default_conditions": condition(legacy["time_effect_category"]),
        },
    }


def _session() -> dict[str, Any]:
    snapshot = deepcopy(cast(dict[str, Any], build_api_payload("P1"))["fastener_snapshot"])
    snapshot.update(
        id="USER_FASTENER_QA_1",
        display_name="QA explicit-Fnt fastener",
        locked=False,
        bolt_specification="USER_DEFINED_QA_ONLY",
        alloy_group="USER_DEFINED",
        alloys=["USER_DEFINED"],
        condition="QA_ONLY",
        nut_specification="QA_NUT",
        washer_material_basis="QA_WASHER",
        installation_condition="SNUG_TIGHT",
        fnt={"value": "75", "unit": "ksi"},
        fnt_source_classification="USER_DEFINED",
        fnt_qualification_status="DEVELOPMENT_ONLY",
        shear_plane_thread_statuses=[{"location_id": "SHEAR_PLANE_1", "status": "EXCLUDED"}],
        number_of_shear_planes=1,
    )
    return {
        "kind": "SESSION",
        "contract": "FASTENER-OR1-RC1",
        "revision": "1",
        "source_label": "QA synthetic user input",
        "fnt_source_basis": "QA-only declared Fnt",
        "snapshot": snapshot,
    }


def test_default_fastener_catalog_and_direct_source_gate() -> None:
    catalog = call("GET", "/api/v1/fasteners/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["contract"] == "FASTENER-OR1-RC1"
    preset = catalog.json()["records"][0]
    assert preset["id"] == "ASTM_F593_17_GROUP_2_316_316L"
    assert preset["fnt"] is None
    assert preset["fnt_state"] == "SOURCE_PENDING"
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", _body())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["fastener_source"]["kind"] == "DEFAULT"
    assert "F593_TENSILE_SOURCE_DATA_PENDING" in str(result["native_design"])
    checks = result["native_design"]["automatic_handoff_results"][0]["checks"]
    assert all(
        item["availability"] == "SOURCE_DATA_PENDING"
        for item in checks
        if item["family"] == "BOLT_SHEAR"
    )


def test_custom_fnt_changes_direct_bolt_numerics_without_qualification() -> None:
    body = _body()
    body["fastener"] = _session()
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert result["fastener_source"]["snapshot"]["id"] == "USER_FASTENER_QA_1"
    assert result["fastener_source"]["fnt_source_basis"] == "QA-only declared Fnt"
    native = result["native_design"]
    bolt_shear = [
        item
        for item in native["automatic_handoff_results"][0]["checks"]
        if item["family"] == "BOLT_SHEAR"
    ]
    assert bolt_shear
    assert all(item["availability"] == "CALCULATED" for item in bolt_shear)
    assert all(item["resistance_result"]["design_resistance"] is not None for item in bolt_shear)
    first = Decimal(bolt_shear[0]["resistance_result"]["design_resistance"]["value"])
    assert first > 0
    body["fastener"]["snapshot"]["fnt"]["value"] = "60"
    lower = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert lower.status_code == 200, lower.text
    lower_checks = lower.json()["native_design"]["automatic_handoff_results"][0]["checks"]
    lower_first = next(item for item in lower_checks if item["family"] == "BOLT_SHEAR")
    assert Decimal(lower_first["resistance_result"]["design_resistance"]["value"]) < first
    assert "CUSTOM_FASTENER_FNT_IS_NUMERICAL_USER_DATA_NOT_QUALIFIED_F593" in str(native)
    assert "F593_TENSILE_SOURCE_DATA_PENDING" not in str(native)


def test_executed_custom_bolt_shear_has_a_faithful_report_substitution() -> None:
    body = _body()
    body["legacy_request"] = _one_row_payload(3, force="70")
    body["fastener"] = _session()
    result = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert result.status_code == 200, result.text
    native = result.json()["native_design"]
    check = next(
        item["resistance_result"]
        for item in native["automatic_handoff_results"][0]["checks"]
        if item["family"] == "BOLT_SHEAR"
    )
    rendered = multirow_native_substitution(
        check, native["preview"]["visualization"], "US_CUSTOMARY"
    )
    assert "A_b(" in rendered
    assert "F_nv(" in rendered
    assert "phi = 0.75" in rendered
    assert "lambda = 1" in rendered
    assert "R_d =" in rendered


def test_custom_cannot_impersonate_f593_or_claim_qualification() -> None:
    body = _body()
    session = _session()
    body["fastener"] = session
    session["snapshot"]["id"] = "ASTM_F593_17_GROUP_2_316_316L"
    assert call("POST", "/api/v1/frp-materials/multi-row/design-check", body).status_code == 422
    session["snapshot"]["id"] = "USER_FASTENER_QA_1"
    session["snapshot"]["fnt_qualification_status"] = "SOURCE_QUALIFIED"
    assert call("POST", "/api/v1/frp-materials/multi-row/design-check", body).status_code == 422
    session["snapshot"]["fnt_qualification_status"] = "DEVELOPMENT_ONLY"
    session["fnt_source_basis"] = ""
    assert call("POST", "/api/v1/frp-materials/multi-row/design-check", body).status_code == 422


def test_direct_engineer_pdf_uses_signed_selected_material_and_fastener() -> None:
    body = _body()
    body["fastener"] = _session()
    result = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert result.status_code == 200, result.text
    signer = SnapshotSigner(b"or1-fastener-report-test-authority-key-32")
    token = signer.issue(
        family="multi-row", kind="design", request=body, result=result.json(), account_id="or1"
    )
    pdf = render_report_pdf(signer.verify(token, account_id="or1"), ReportOptions())
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "ICE — Isophthalic polyester" in text
    assert "QA explicit-Fnt fastener" in text
    assert "QA-only declared Fnt" in text or "75 ksi" in text
    assert "ICE Locked Pultruded FRP" not in text
    assert "lambda=source required" not in text
    audit = render_report_pdf(
        signer.verify(token, account_id="or1"), ReportOptions(mode="FULL_TECHNICAL_AUDIT")
    )
    audit_text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(audit)).pages)
    source = result.json()["material_sources"]["default"]
    assert source["id"] in audit_text
    assert source["content_digest"] in "".join(audit_text.split())
    assert "USER_FASTENER_QA_1" in audit_text
    assert "internal compatibility adapter" in " ".join(audit_text.split())
