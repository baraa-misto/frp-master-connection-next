"""Presentation preserves signed calculations, exact attachment data and raw fit states."""

from __future__ import annotations

import io
from copy import deepcopy
from typing import Any

import pytest
from pypdf import PdfReader
from reportlab.graphics.shapes import Polygon

from frp_master_connection.reporting.direct_presentation import (
    audit_index_rows,
    moment_rows,
    signed_number,
    source_stop_rows,
)
from frp_master_connection.reporting.geometry import BoltPoint, BoxFigure
from frp_master_connection.reporting.pdf import ReportOptions, _flatten, render_report_pdf
from frp_master_connection.reporting.reader_views import colored_view, native_component_legend
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_f593_f4 import design
from tests.direct_mc1_fixtures import mc1_body


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-1e-88", "-1e-88"),
        ("1e-88", "+1e-88"),
        ("-.00000001", "-1e-8"),
        (".00000001", "+1e-8"),
        ("0E-88", "0 (exact)"),
        ("-0", "0 (exact)"),
        ("1.23456789", "+1.23457"),
        ("not supplied", "not supplied"),
        ("Infinity", "Infinity"),
    ],
)
def test_signed_display_never_converts_a_negative_or_nonzero_margin_into_zero(
    raw: str, expected: str
) -> None:
    assert signed_number(raw) == expected


def test_reference_transport_is_existing_component_data_only() -> None:
    diagnostic: dict[str, Any] = {
        "equation": "M_G = M_P + (P-G) x F",
        "F_global_kip": ["0", "-0.6", "-0.36"],
        "P_global_in": ["-2.375", "3.262078800732147", "4.024986117705513"],
        "G_global_in": ["-.375", "1.09152913087920367", "2.8716155643717897"],
        "M_P_global_kip_in": ["0", "0", "0"],
        "M_G_global_kip_in": ["-.0875", "-.72", "1.2"],
        "state": "REFERENCE_TRANSPORT_DIAGNOSTIC_ONLY",
        "per_bolt_demand_evaluated": False,
        "resistance_center_established": False,
    }
    before = deepcopy(diagnostic)
    rows = dict(moment_rows(diagnostic))
    assert (
        rows["M_G — transported moment at G"]
        == "X = -0.0875 kip·in; Y = -0.72 kip·in; Z = +1.2 kip·in"
    )
    assert rows["Per-bolt demand evaluated"] == "False"
    assert rows["Resistance center established"] == "False"
    assert before == diagnostic


def test_source_stop_uses_actual_gate_and_counts_without_changing_status() -> None:
    assert source_stop_rows({}) == []
    assert source_stop_rows({"direct_material_applicability": {"blocked_check_ids": []}}) == []
    assert source_stop_rows({"direct_material_applicability": {"blocked_check_ids": ["A"]}}) == []
    result: dict[str, Any] = {
        "direct_material_applicability": {
            "blocked_check_ids": ["FRP1", "FRP2"],
            "reason": "Actual source authority unavailable",
        },
        "final_decision": {
            "final_status": "RED",
            "schedule": [
                {"check_id": "BOLT_SHEAR:B1", "category": "ANALYTICALLY_EVALUATED"},
                {"check_id": "OTHER", "category": "ANALYTICALLY_EVALUATED"},
                {"check_id": "FRP1", "category": "REQUIRED_UNRESOLVED"},
            ],
        },
    }
    before = deepcopy(result)
    rows = dict(source_stop_rows(result))
    assert rows["FRP SOURCE-DATA STOP"].endswith("Actual source authority unavailable")
    assert "1 independent bolt shear" in rows["Independent evaluated checks"]
    assert "1 other independent" in rows["Independent evaluated checks"]
    assert rows["Source-blocked FRP checks"].startswith("2;")
    assert before == result


@pytest.mark.parametrize("temperature", ["100", "140.0001"])
def test_actual_signed_report_preserves_every_native_field_and_adds_exact_navigation(
    temperature: str,
) -> None:
    body = mc1_body(temperature)
    result = design(body)
    signer = SnapshotSigner(b"P1-LOCAL-REPORT-TEST-KEY-ONLY-32-BYTES")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="p1-test"
        ),
        account_id="p1-test",
    )
    before = deepcopy((snapshot.request, snapshot.result, snapshot.input_provenance))
    reader = PdfReader(
        io.BytesIO(render_report_pdf(snapshot, ReportOptions(mode="FULL_TECHNICAL_AUDIT")))
    )
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    searchable = "".join(text.split())
    assert "Audit field/check index" in text
    assert "template quantities" in text
    assert "inactive — one bolt line" in text
    assert "Adjusted-property/native-factorboundary" in searchable
    assert "notasecondadjustment" in searchable
    for path, value in _flatten("result", result["native_design"]):
        assert "".join(path.split()) in searchable, path
        assert "".join(value.split()) in searchable, path
    decision = result["final_decision"]
    for row in decision["schedule"]:
        assert row["check_id"] in dict(audit_index_rows(decision))
    w_paths = [
        row["check_id"]
        for row in decision["schedule"]
        if row["check_id"].startswith("BLOCK_SHEAR:layer-B:")
    ]
    assert len(w_paths) == 2
    assert all(identity in searchable for identity in w_paths)

    def bookmark_titles(items: list[Any]) -> set[str]:
        titles: set[str] = set()
        for item in items:
            if isinstance(item, list):
                titles.update(bookmark_titles(item))
            else:
                titles.add(str(item["/Title"]))
        return titles

    assert {
        "1 Executive engineering summary",
        "2 Physical connection model",
        "Connection qualification",
        "Materials, conditions and design basis",
        "Canonical bolt layout diagnostic",
        "3 Direct assembly and design basis",
        "4 Applied action and load path",
        "5 Required checks and numerical results",
        "6 Governing worked calculation",
        "Catalog-resolved native bolt shear calculations",
        "7 Active design limits",
        "Angle physical free-side block shear",
        "TECHNICAL AUDIT APPENDIX — COMPLETE NATIVE RECORD",
        "Appendix A — Submitted request and provenance",
        "F6 first-row authority context",
        "Appendix B — Complete native result",
        "MAT1 material and condition authority",
        "Calculation identity",
        "Audit field/check index — exact native locators",
    } <= bookmark_titles(reader.outline)
    if temperature == "140.0001":
        first = reader.pages[0].extract_text() or ""
        assert "FRP SOURCE-DATA STOP" in first
        assert "2 independent bolt shear checks evaluated only" in first
        assert "14 required checks/evidence items unresolved" in text
        assert decision["final_status"] == "YELLOW"
    assert before == (snapshot.request, snapshot.result, snapshot.input_provenance)


@pytest.mark.parametrize("view", ["isometric", "elevation", "plan"])
def test_native_tags_add_only_keyed_leaders_and_retain_exact_solid_projection(view: str) -> None:
    box = BoxFigure(
        "MEMBER:member-a:LEG_1",
        tuple((x, y, z) for x in (-2.0, 2.0) for y in (-1.0, 1.0) for z in (-0.5, 0.5)),
    )
    bolt = BoltPoint("B_R1_L1", (0, 0, 0))
    untagged = colored_view([box, box], [], [bolt], view)
    tagged = colored_view([box, box], [], [bolt], view, native_tags=True)
    assert [shape.points for shape in untagged.contents if isinstance(shape, Polygon)] == [
        shape.points for shape in tagged.contents if isinstance(shape, Polygon)
    ]
    keys = native_component_legend([box, box], [], [bolt])
    assert len(keys) == 2
    assert "MEMBER:member-a:LEG_1" in keys[0][1]
    assert "B_R1_L1" in keys[1][1]
    assert all(
        any(getattr(shape, "text", None) == key for shape in tagged.contents) for key, _ in keys
    )
