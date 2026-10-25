"""Real inactive integration, status precedence/currentness and actual PDF records."""

import io
from dataclasses import replace
from hashlib import sha256
from typing import Any

import pytest
from pypdf import PdfReader

from frp_master_connection.application.hyb1_contract import ActionBasis, Alignment, PairedActions
from frp_master_connection.application.hyb1_review import assess_hybrid
from frp_master_connection.application.hyb2_direct_r3 import calculate_r3_references
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_r3 import (
    R3Geometry,
    execute_r3_review,
    geometry_digest,
)
from frp_master_connection.calculation.rhm_direct_reference import q
from frp_master_connection.reporting.rhm_direct_r3_review import (
    OWNER_IMAGE,
    geometry_view,
    render_r3,
)
from tests.application.test_hyb2_direct_status import empty_native, source_actions


def actions_r3() -> PairedActions:
    a = source_actions()
    g = R3Geometry()
    return replace(
        a,
        identity=replace(a.identity, geometry=geometry_digest(g)),
        asd=(replace(a.asd[0], frame="DIRECT_P_SKETCH_V_CENTROID"),),
    )


def test_r3_18_19_23_inactive_status_scoped_reference_not_blanket_yellow() -> None:
    a = actions_r3()
    g = R3Geometry()
    result = calculate_r3_references(a, g)
    assert len(result.records) == 1
    assert len(result.supplemental.rows) == 7
    review = assess_hybrid(a, empty_native(a), result.supplemental)
    assert review.current
    assert review.reference_outcome == "PASS"
    assert review.numerical_outcome == "NOT_EVALUATED"
    assert not review.analytical_candidate_complete
    assert not review.public_activation
    heavy = replace(
        a,
        asd=(
            replace(
                a.asd[0],
                components=(q("60000", Unit.LBF), q("60000", Unit.LBF), *a.asd[0].components[2:]),
            ),
        ),
    )
    heavy_result = calculate_r3_references(heavy, g)
    review = assess_hybrid(heavy, empty_native(heavy), heavy_result.supplemental)
    assert review.reference_outcome == "FAIL"
    stale = assess_hybrid(heavy, empty_native(heavy), result.supplemental)
    assert not stale.current
    assert stale.reference_outcome == "NOT_EVALUATED"
    with pytest.raises(ValueError, match="exact corrected"):
        calculate_r3_references(a, replace(g, vertical_bolt_pitch=q("2.1")))


@pytest.mark.parametrize(
    "kind", ["missing", "basis", "frame", "reference", "moment", "negative", "alignment"]
)
def test_r3_20_missing_or_unsupported_never_zeroed(kind: str) -> None:
    a = actions_r3()
    case = a.asd[0]
    if kind == "basis":
        a = replace(a, asd=(), lrfd=(replace(case, basis=ActionBasis.LRFD),))
    elif kind == "alignment":
        a = replace(a, identity=replace(a.identity, alignment=Alignment.BRACE))
    else:
        updates: dict[str, dict[str, Any]] = {
            "missing": {"components": (None, *case.components[1:])},
            "frame": {"frame": "OLD_POSITIVE_N"},
            "reference": {"reference": (q("1"), *case.reference[1:])},
            "moment": {"components": (*case.components[:5], q("1", Unit.LBF_IN))},
            "negative": {"components": (q("-1", Unit.LBF), *case.components[1:])},
        }
        a = replace(a, asd=(replace(case, **updates[kind]),))
    result = calculate_r3_references(a, R3Geometry())
    assert result.withheld
    assert not result.records
    assert not result.supplemental.rows
    assert "NOT EVALUATED" in " ".join(result.supplemental.limitations) or kind == "basis"


@pytest.mark.parametrize("technical", [False, True])
@pytest.mark.parametrize("kind", ["normal", "overload", "invalid"])
def test_r3_22_real_reports_print_only(technical: bool, kind: str) -> None:
    bundle = execute_r3_review(
        geometry=R3Geometry(hole=q("3")) if kind == "invalid" else R3Geometry(),
        axial=q("60000" if kind == "overload" else "91.55", Unit.LBF),
    )
    before = repr(bundle)
    pdf = render_r3(bundle, technical=technical)
    text = " ".join(
        " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert repr(bundle) == before
    assert pdf.startswith(b"%PDF")
    assert "OWNER_SPACING_AND_AXES_RECONCILED" in text
    assert "Reference calculations - not an adopted design" in text
    if technical:
        assert "Numerical dependency ledger" in text
        assert "HALF_AT_CENTER_ENDPOINT" in text or kind == "invalid"
    else:
        assert "Actual B1-B2: 2.000000 in" in text
        assert "Transverse LTV: 1.716129811 in" in text
        assert "Before / after numerical comparisons" in text
        assert (
            "FAIL" in text
            if kind == "overload"
            else "PASS" in text
            if kind == "normal"
            else "NOT_EVALUATED" in text
        )
    assert sha256(OWNER_IMAGE.read_bytes()).hexdigest() == bundle.current.sketch_sha256
    if kind == "invalid":
        assert geometry_view(bundle, bundle.current.rotation_blocks[0]) is not None


def test_report_withheld_parallel_ray_has_no_invented_endpoint() -> None:
    bundle = execute_r3_review()
    block = bundle.current.blocks[0]
    unavailable = replace(
        block,
        paths=tuple(
            replace(p, end=None, length_in=None, reason="PARALLEL_TO_EDGE") for p in block.paths
        ),
    )
    view = geometry_view(bundle, unavailable)
    assert view is not None
    assert (
        bundle.current.input_digest
        != execute_r3_review(axial=q("92", Unit.LBF)).current.input_digest
    )
    varied = execute_r3_review(geometry=R3Geometry(vertical_bolt_pitch=q("2.1")))
    pdf = render_r3(varied)
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "Actual pitch is 2.100000 in" in text
    assert "connector length=2.100000 in" in text
    assert "Rotated corrected 2.100000-in pair" in text
