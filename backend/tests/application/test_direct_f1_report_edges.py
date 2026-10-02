"""Report-only boundary and signed-snapshot coverage for Direct F1."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import pytest

from frp_master_connection.api.multirow_mapping import serialize_multirow_design
from frp_master_connection.application import evaluate_multirow_connection
from frp_master_connection.reporting.pdf import (
    ReportingCoverageError,
    ReportOptions,
    _direct_reader_engineering_sections,
    _font_setup,
    _styles,
    render_multirow_pdf,
)
from frp_master_connection.reporting.reader_views import multirow_physical_geometry
from frp_master_connection.reporting.snapshot import ReportSnapshot, SnapshotSigner
from tests.application.test_direct_f1_safety import _one_row_payload, _request


@pytest.fixture(scope="module")
def direct_native() -> tuple[dict[str, object], dict[str, Any]]:
    payload = _one_row_payload(2)
    native = serialize_multirow_design(evaluate_multirow_connection(_request(payload))).model_dump()
    return payload, native


def _signed(payload: dict[str, object], native: dict[str, Any]) -> ReportSnapshot:
    signer = SnapshotSigner(b"direct-f1-report-edge-authority-key-32")
    token = signer.issue(
        family="multi-row", kind="design", request=payload, result=native, account_id="edge"
    )
    return signer.verify(token, account_id="edge")


def _sections(snapshot: ReportSnapshot) -> object:
    _font_setup()
    native = snapshot.result
    visual = native["preview"]["visualization"]
    return _direct_reader_engineering_sections(snapshot, native, visual, "US_CUSTOMARY", _styles())


def _governing(native: dict[str, Any]) -> dict[str, Any]:
    checks = native["automatic_group_mode_integration"]["direct_single_row_result"]["checks"]
    return next(item for item in checks if item["result_id"] == "SINGLE_ROW_CLEAVAGE:layer-A")


def test_direct_report_requires_signed_row_counts(
    direct_native: tuple[dict[str, object], dict[str, Any]],
) -> None:
    payload, native = direct_native
    invalid = dict(payload)
    invalid.pop("row_count")
    snapshot = _signed(invalid, native)
    with pytest.raises(ReportingCoverageError, match="row and bolt counts"):
        render_multirow_pdf(snapshot, ReportOptions())


def test_direct_report_fails_closed_for_unadapted_or_missing_native_trace(
    direct_native: tuple[dict[str, object], dict[str, Any]],
) -> None:
    payload, original = direct_native
    unknown = deepcopy(original)
    _governing(unknown)["equation_method"] = "UNADAPTED_METHOD"
    with pytest.raises(ReportingCoverageError, match="lacks a report adapter"):
        _sections(_signed(payload, unknown))
    missing = deepcopy(original)
    _governing(missing)["equation_trace"] = None
    with pytest.raises(ReportingCoverageError, match="lacks a native trace"):
        _sections(_signed(payload, missing))


def test_direct_report_reads_nested_trace_without_changing_results(
    direct_native: tuple[dict[str, object], dict[str, Any]],
) -> None:
    payload, original = direct_native
    nested = deepcopy(original)
    trace = _governing(nested)["equation_trace"]
    factors = trace.pop("factor_trace")
    trace["native"] = {
        "knt": "1.1",
        "governing_branches": ["A"],
        "factor_trace": factors,
        "tensile_property": {"adjusted_property": "12"},
        "shear_property": {"adjusted_property": "5"},
    }
    snapshot = _signed(payload, nested)
    original_result = deepcopy(snapshot.result)
    assert _sections(snapshot)
    assert snapshot.result == original_result
    sparse = deepcopy(original)
    sparse_trace = _governing(sparse)["equation_trace"]
    sparse_trace["native"] = {}
    sparse_trace["tensile_property"] = "not-a-property-trace"
    sparse_trace["shear_property"] = "not-a-property-trace"
    sparse_trace["factor_trace"] = "not-a-factor-trace"
    assert _sections(_signed(payload, sparse))
    no_native = deepcopy(original)
    no_native["automatic_group_mode_integration"]["direct_single_row_result"]["checks"] = []
    no_native["automatic_handoff_results"] = []
    no_native["direct_required_check_inventory"] = [
        {
            "result_id": "SYNTHETIC:layer-A",
            "availability": "CALCULATED",
            "utilization": "99",
            "required": True,
        }
    ]
    no_native["preview"]["warnings"] = []
    assert _sections(_signed(payload, no_native))


def test_direct_report_inventory_and_blocker_fallbacks(
    direct_native: tuple[dict[str, object], dict[str, Any]],
) -> None:
    payload, original = direct_native
    native = deepcopy(original)
    integration = native["automatic_group_mode_integration"]
    integration["required_check_ids"].extend(["SOURCE_NOT_REQUIRED", "SOURCE_UNCLASSIFIED"])
    integration["not_required_check_ids"].append("SOURCE_NOT_REQUIRED")
    assert render_multirow_pdf(_signed(payload, native), ReportOptions()).startswith(b"%PDF")
    residual = deepcopy(original)
    checks = residual["automatic_group_mode_integration"]["direct_single_row_result"]["checks"]
    checks[0]["reason"] = "Required section demand under residual moment is unresolved"
    assert render_multirow_pdf(_signed(payload, residual), ReportOptions()).startswith(b"%PDF")
    no_integration = deepcopy(original)
    no_integration["automatic_group_mode_integration"] = None
    assert render_multirow_pdf(_signed(payload, no_integration), ReportOptions()).startswith(
        b"%PDF"
    )


def test_direct_geometry_report_rejects_missing_physical_bolt_paths(
    direct_native: tuple[dict[str, object], dict[str, Any]],
) -> None:
    _, original = direct_native
    visual = deepcopy(original["preview"]["visualization"])
    physical_bolts = cast(list[dict[str, object]], visual["physical_bolts"])
    physical_bolts[0] = {"row_id": "ROW_1", "bolt_line_id": "BOLT_LINE_1"}
    with pytest.raises(ValueError, match="every physical member and bolt path"):
        multirow_physical_geometry(visual)
    visual = deepcopy(original["preview"]["visualization"])
    visual["physical_bolts"] = [{}]
    with pytest.raises(ValueError, match="every physical member and bolt path"):
        multirow_physical_geometry(visual)
