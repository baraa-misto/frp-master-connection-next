"""Fail-closed PDF adapter and optional-presentation behavior."""

from __future__ import annotations

import asyncio
import io
from copy import deepcopy
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.calculation.multirow_engine import MultiRowEquationMethod
from frp_master_connection.calculation.results import LimitState
from frp_master_connection.reporting.pdf import (
    _MULTIROW_METHODS,
    _SINGLE_BOLT_METHODS,
    MAX_TABLE_ROWS,
    ReportingCoverageError,
    ReportOptions,
    _append_result_unit_equivalents,
    _drawing,
    _factor_substitution,
    _font_setup,
    _multirow_drawing,
    _paragraph,
    _ReportDocument,
    _single_factor_substitutions,
    _styles,
    _table,
    render_multirow_pdf,
    render_single_bolt_pdf,
)
from frp_master_connection.reporting.snapshot import ReportSnapshot
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload


@pytest.fixture(scope="module")
def native_reports() -> tuple[dict[str, Any], dict[str, Any]]:
    async def fetch() -> tuple[dict[str, Any], dict[str, Any]]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            single = await client.post(
                "/api/v1/calculations/single-bolt/evaluate", json=build_api_payload("J1-T")
            )
            multi = await client.post(
                "/api/v1/calculations/multi-row/design-check", json=native_payload("multi-row")
            )
            assert single.status_code == multi.status_code == 200
            return single.json(), multi.json()

    return asyncio.run(fetch())


def _snapshot(family: str, result: dict[str, Any]) -> ReportSnapshot:
    return ReportSnapshot(family, "design", {}, result, 1_000, "0" * 64)


def test_report_registries_cover_every_native_check_method_enum() -> None:
    assert set(_MULTIROW_METHODS) == {method.value for method in MultiRowEquationMethod}
    assert set(_SINGLE_BOLT_METHODS) == {method.value for method in LimitState}


def test_document_page_limit_fails_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    import frp_master_connection.reporting.pdf as pdf_module

    monkeypatch.setattr(pdf_module, "MAX_REPORT_PAGES", 0)
    _font_setup()
    styles = _styles()
    document = _ReportDocument(io.BytesIO(), pagesize=(612, 792), footer="QA")
    with pytest.raises(ReportingCoverageError, match="page export limit"):
        document.build([_paragraph("One page", styles["body"])])


def test_long_status_footer_preserves_the_snapshot_identifier() -> None:
    _font_setup()
    stream = io.BytesIO()
    digest = "abcdef123456"
    document = _ReportDocument(
        stream,
        pagesize=(612, 792),
        footer=f"Connection | No revision | {'LONG_STATUS_' * 20} | {digest}",
    )
    document.build([_paragraph("One page", _styles()["body"])])
    text = PdfReader(io.BytesIO(stream.getvalue())).pages[0].extract_text() or ""
    assert digest in text
    assert "LONG_STATUS_" in text


def test_long_legacy_footer_without_snapshot_separator_is_trimmed() -> None:
    _font_setup()
    stream = io.BytesIO()
    document = _ReportDocument(stream, pagesize=(612, 792), footer="LEGACY" * 100)
    document.build([_paragraph("One page", _styles()["body"])])
    text = PdfReader(io.BytesIO(stream.getvalue())).pages[0].extract_text() or ""
    assert "LEGACY" in text
    assert "..." in text
    assert "LEGACY" * 100 not in text


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("wrong_family", "adapter is missing"),
        ("non_dict_result", "result is unavailable"),
        ("bad_check_inventory", "check inventory is malformed"),
        ("no_visualization", "visualization is missing"),
        ("bad_check", "check record is malformed"),
        ("unknown_method", "no REPORT1 method template"),
        ("missing_trace", "no numerical trace"),
    ],
)
def test_direct_adapter_rejects_malformed_authoritative_records(
    native_reports: tuple[dict[str, Any], dict[str, Any]], fault: str, message: str
) -> None:
    result: Any = deepcopy(native_reports[0])
    family = "single-bolt"
    if fault == "wrong_family":
        family = "clip-angle"
    elif fault == "non_dict_result":
        result = {"client_design": []}
    elif fault == "bad_check_inventory":
        result["results"] = {}
    elif fault == "no_visualization":
        del result["visualization"]
    elif fault == "bad_check":
        result["results"][0] = {}
    elif fault == "unknown_method":
        result["results"][0]["plan"]["limit_state"] = "FUTURE_METHOD"
    elif fault == "missing_trace":
        calculated = next(
            check for check in result["results"] if check["availability"] == "CALCULATED"
        )
        del calculated["equation_trace"]
    with pytest.raises(ReportingCoverageError, match=message):
        render_single_bolt_pdf(_snapshot(family, result), ReportOptions())


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("wrong_family", "adapter is missing"),
        ("non_dict_result", "result is unavailable"),
        ("no_preview", "preview geometry is missing"),
        ("no_calculation", "lacks its native result"),
        ("bad_check_inventory", "check inventory is malformed"),
        ("bad_check", "check record is malformed"),
        ("unknown_method", "no REPORT1 template"),
        ("missing_trace", "no native trace"),
    ],
)
def test_multirow_adapter_rejects_malformed_authoritative_records(
    native_reports: tuple[dict[str, Any], dict[str, Any]], fault: str, message: str
) -> None:
    result: Any = deepcopy(native_reports[1])
    family = "multi-row"
    if fault == "wrong_family":
        family = "single-bolt"
    elif fault == "non_dict_result":
        result = {"client_design": []}
    elif fault == "no_preview":
        result["preview"] = {}
    elif fault == "no_calculation":
        del result["calculation_result"]
    elif fault == "bad_check_inventory":
        result["calculation_result"]["results"] = {}
    elif fault == "bad_check":
        result["calculation_result"]["results"][0] = None
    elif fault == "unknown_method":
        result["calculation_result"]["results"][0]["equation_method"] = "FUTURE_METHOD"
    elif fault == "missing_trace":
        calculated = next(
            check
            for check in result["calculation_result"]["results"]
            if check["availability"] == "CALCULATED"
        )
        del calculated["equation_trace"]
    with pytest.raises(ReportingCoverageError, match=message):
        render_multirow_pdf(_snapshot(family, result), ReportOptions())


def test_geometry_renderers_reject_absent_native_shapes() -> None:
    with pytest.raises(ReportingCoverageError, match="box geometry"):
        _drawing({"primitives": []}, "plan")
    with pytest.raises(ReportingCoverageError, match="multi-row geometry"):
        _multirow_drawing({"boundary": [0, 1, 0, 1], "bolts": [], "layers": []}, "plan")


def test_report_table_limit_rejects_unbounded_native_rows() -> None:
    with pytest.raises(ReportingCoverageError, match="row limit"):
        _table([("x", "y")] * (MAX_TABLE_ROWS + 1), _styles())


def test_direct_optional_metadata_and_display_units_are_searchable(
    native_reports: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    result = native_reports[0]
    pdf = render_single_bolt_pdf(
        _snapshot("single-bolt", result),
        ReportOptions(notes="Reviewed locality", display_units="SI"),
    )
    extracted = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Reviewed locality" in extracted
    assert "display-unit equivalents" in extracted


def test_embedded_font_keeps_common_unicode_metadata_searchable(
    native_reports: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    pdf = render_single_bolt_pdf(
        _snapshot("single-bolt", native_reports[0]),
        ReportOptions(project_name="Façade Δ Ω"),
    )
    extracted = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Façade Δ Ω" in extracted


def test_empty_result_display_conversion_adds_no_section() -> None:
    story: list[Any] = []
    snapshot = _snapshot("single-bolt", {"native": "no quantities"})
    _append_result_unit_equivalents(story, snapshot, ReportOptions(display_units="SI"), _styles())
    assert story == []


def test_direct_bolt_factor_substitution_uses_native_values() -> None:
    check = {
        "nominal_resistance": {"value": "100", "unit": "N"},
        "design_resistance": {"value": "80", "unit": "N"},
        "equation_trace": {"resistance_factor": "0.8"},
    }
    rows = _single_factor_substitutions(check)
    assert "phi(0.8)" in rows[0][1]
    assert "80 N" in rows[0][1]


def test_absent_factor_trace_has_no_substitution() -> None:
    assert _single_factor_substitutions({"equation_trace": {}}) == []
    assert _factor_substitution(None) == "No native factor-stage trace supplied"


@pytest.mark.parametrize("bolt", [None, {}])
def test_direct_projection_allows_missing_bolt_geometry(
    native_reports: tuple[dict[str, Any], dict[str, Any]], bolt: object
) -> None:
    visual = deepcopy(native_reports[0]["visualization"])
    if bolt is None:
        visual.pop("bolt", None)
    else:
        visual["bolt"] = bolt
    assert _drawing(visual, "elevation").width == 455


def test_synthetic_native_pass_status_has_no_incomplete_banner(
    native_reports: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    result = deepcopy(native_reports[0])
    wrapped = {"client_design": result, "overall_status": "PASS"}
    pdf = render_single_bolt_pdf(_snapshot("single-bolt", wrapped), ReportOptions())
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Status: PASS" in text
    assert "Incomplete design -" not in text


def test_direct_summary_does_not_round_a_small_exceedance_to_100_percent(
    native_reports: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    result = deepcopy(native_reports[0])
    calculated = next(check for check in result["results"] if check["availability"] == "CALCULATED")
    calculated["utilization"] = "1.0000000000001"
    pdf = render_single_bolt_pdf(_snapshot("single-bolt", result), ReportOptions())
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "100.000% (above 1.0; exact native U in check detail)" in text.replace("\n", "")
    assert "1.0000000000001" in text.replace("\n", "")


def test_multirow_si_and_mat1_wrapper_are_printed(
    native_reports: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    wrapped = {
        "client_design": native_reports[1],
        "material_ledgers": [{"record_id": "SYNTHETIC-MAT1-ROW"}],
    }
    pdf = render_multirow_pdf(_snapshot("multi-row", wrapped), ReportOptions(display_units="SI"))
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Alternate display-unit equivalents" in text
    assert "MAT1 material and condition authority" in text
    assert "SYNTHETIC-MAT1-ROW" in text


def test_empty_renderer_output_is_rejected(
    native_reports: tuple[dict[str, Any], dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_ReportDocument, "build", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="did not produce a PDF"):
        render_single_bolt_pdf(_snapshot("single-bolt", native_reports[0]), ReportOptions())
