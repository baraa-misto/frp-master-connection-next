"""Executed immutable R2 evidence and reference-only status in actual PDFs."""

import io

from pypdf import PdfReader

from frp_master_connection.calculation.rhm_direct_corrections import execute_direct_corrections
from frp_master_connection.calculation.rhm_direct_reference import DirectGeometry
from frp_master_connection.reporting.rhm_direct_correction_review import (
    TITLE,
    render_direct_corrections,
)


def test_r2_prints_full_numerical_and_actual_surface_evidence_without_mutation() -> None:
    record = execute_direct_corrections()
    before = repr(record)
    output = render_direct_corrections(record)
    reader = PdfReader(io.BytesIO(output))
    text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
    compact = "".join(text.split())
    assert TITLE in text
    assert "Material limitations" in (reader.pages[0].extract_text() or "")
    assert record.endpoint_question in text
    assert "Section 2.3.2 unresolved" in text
    assert "Public activation: false" in text
    for group in record.variants:
        assert group.variant in text
        assert str(group.utilization) in text
        for row in group.branches:
            assert str(row.allowable_capacity_kip) in compact
            assert str(row.ratio) in compact
            assert str(row.listed_stress_area_sum_kip) in compact
            for cell, value in row.cell_trace:
                assert f"Calcs!{cell}={value}" in compact
    for block in record.physical_blocks:
        assert str(block.actual_shear_net_area_in2) in text
        for surface in block.cuts:
            assert str(surface.net_area_in2) in text
            for hole in surface.intersections:
                assert hole.disposition in text
                assert str(hole.diameter_fraction) in text
    assert before == repr(record)
    assert all(word not in text for word in ("password", "report_handle", "private_source.xlsx"))


def test_r2_unavailable_conditional_area_is_visible_and_not_pass() -> None:
    from decimal import Decimal

    record = execute_direct_corrections(geometry=DirectGeometry(phi=Decimal("5")))
    text = " ".join(
        " ".join(
            p.extract_text() or ""
            for p in PdfReader(io.BytesIO(render_direct_corrections(record))).pages
        ).split()
    )
    assert "Nonpositive residual reference material area" in text
    assert "NOT_EVALUATED" in text
    assert "None" in text
