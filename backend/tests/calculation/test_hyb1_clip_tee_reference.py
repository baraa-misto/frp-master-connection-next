"""Second-source oracles stay separate from Direct; corrected combined status is mandatory."""

import io
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import cast

import pytest
from pypdf import PdfReader

from frp_master_connection.application.hyb1_contract import Alignment
from frp_master_connection.application.hyb1_mapping import clip_tee_reference_uses, direct_mappings
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_clip_tee_reference import (
    SOURCE_ID,
    WORKBOOK_SHA256,
    execute_clip_tee_reference,
    tee_flange_reference,
)
from frp_master_connection.calculation.rhm_reference import ReferenceStream
from frp_master_connection.calculation.rhm_workbook_case import execute_workbook_case
from frp_master_connection.reporting.rhm_clip_tee_review import render_clip_tee_reference
from tests.hyb1_fixtures import q


@pytest.mark.parametrize(
    ("index", "oracle"),
    [
        (0, Fraction(16, 27)),
        (2, Fraction(160, 243)),
        (3, Fraction(320, 909)),
        (4, Fraction(80, 729)),
        (5, Fraction(10, 243)),
        (6, Fraction(5, 81)),
    ],
)
def test_supplement_components_match_independent_rational_oracles(
    index: int, oracle: Fraction
) -> None:
    case = execute_clip_tee_reference()
    with localcontext() as context:
        context.prec = 60
        expected = Decimal(oracle.numerator) / Decimal(oracle.denominator)
    assert abs(case.comparisons[index].utilization - expected) < Decimal("1e-58")
    assert case.source_id == SOURCE_ID
    assert case.workbook_sha256 == WORKBOOK_SHA256
    assert case.actual_direct_coverage == ()
    assert not case.public_activation


@pytest.mark.parametrize("stream", list(ReferenceStream))
def test_historical_and_corrected_streams_keep_separate_summary_authority(
    stream: ReferenceStream,
) -> None:
    case = execute_clip_tee_reference(stream=stream)
    flange = case.tee_flange
    assert abs(flange.comparison.components[0] - Decimal(".40912681878539675")) < Decimal("1e-15")
    assert abs(flange.comparison.utilization - Decimal(".45641351280508674")) < Decimal("1e-15")
    assert ("D142" in flange.summary_cell) is (stream is ReferenceStream.HISTORICAL_REPLICATION)
    assert flange.summary == (
        flange.comparison.components[0]
        if stream is ReferenceStream.HISTORICAL_REPLICATION
        else flange.comparison.utilization
    )
    assert dict(case.original_saved_cache_cells)["Summary!C14"] == ".40912681878539675"


def test_bending_pass_does_not_hide_combined_failure_in_corrected_summary_or_status() -> None:
    historical = execute_clip_tee_reference(
        stream=ReferenceStream.HISTORICAL_REPLICATION, load_scale=Decimal("2.3")
    )
    corrected = execute_clip_tee_reference(load_scale=Decimal("2.3"))
    assert historical.tee_flange.summary < 1 < corrected.tee_flange.summary
    assert historical.tee_flange.summary_outcome == "PASS"
    assert corrected.tee_flange.summary_outcome == "FAIL"
    assert corrected.tee_flange.comparison.numerical_outcome == "FAIL"


@pytest.mark.parametrize("reinforced", [True, False])
def test_reinforcement_is_explicit_and_never_transferred_to_unreinforced_case(
    reinforced: bool,
) -> None:
    result = execute_clip_tee_reference(reinforcement_selected=reinforced)
    flange = next(r for r in result.comparisons if r.method_id == "RHM_CLIP_TEE_CHORD_FLANGE")
    target = Decimal(".25912324905479034") if reinforced else Decimal("4.6026767113357137")
    assert abs(flange.utilization - target) < Decimal("1e-14")
    assert flange.capacities[0].unit is Unit.KIP_IN
    assert flange.numerical_outcome == ("PASS" if reinforced else "FAIL")
    assert result.actual_direct_coverage == ()


@pytest.mark.parametrize(
    ("selected", "transfer", "count"), [(False, False, 11), (True, False, 11), (True, True, 13)]
)
def test_optional_web_attachment_never_claims_junction_or_net_tension_coverage(
    selected: bool, transfer: bool, count: int
) -> None:
    result = execute_clip_tee_reference(
        web_attachment_selected=selected, attachment_transfer_established=transfer
    )
    assert len(result.comparisons) == count
    if not selected:
        assert "NO_CHORD_WEB_OR_JUNCTION_COVERAGE" in result.web_attachment_state
    elif not transfer:
        assert "INCOMPLETE" in result.web_attachment_state
    else:
        assert "NOT_QUALIFICATION" in result.web_attachment_state
    assert result.actual_direct_coverage == ()
    assert all("NET_TENSION" not in row.method_id for row in result.comparisons)


@pytest.mark.parametrize("scale", ["0", "3"])
def test_zero_true_load_and_overload_keep_real_capacities(scale: str) -> None:
    case = execute_clip_tee_reference(load_scale=Decimal(scale))
    assert all(r.capacities[0].magnitude > 0 for r in case.comparisons)
    assert case.tee_flange.summary_outcome == ("PASS" if scale == "0" else "FAIL")


@pytest.mark.parametrize("scale", ["-1", "NaN", "Infinity"])
def test_invalid_reference_scale_refused(scale: str) -> None:
    with pytest.raises(ValueError, match=r"negative|finite"):
        execute_clip_tee_reference(load_scale=Decimal(scale))


@pytest.mark.parametrize("flag", ["reinforcement", "attachment", "transfer"])
def test_flags_cannot_be_numeric_or_unknown(flag: str) -> None:
    with pytest.raises(TypeError, match="Boolean"):
        execute_clip_tee_reference(
            reinforcement_selected=cast(bool, 1) if flag == "reinforcement" else True,
            web_attachment_selected=cast(bool, None) if flag == "attachment" else False,
            attachment_transfer_established=cast(bool, "yes") if flag == "transfer" else False,
        )


def test_web_bolts_without_reinforcing_angle_refused() -> None:
    with pytest.raises(ValueError, match="require"):
        execute_clip_tee_reference(reinforcement_selected=False, web_attachment_selected=True)


def test_wrong_stream_and_invalid_flange_dimensions_refused() -> None:
    for stream, spacing in [
        (cast(ReferenceStream, "CORRECTED"), q("1", Unit.IN)),
        (ReferenceStream.CORRECTED_REFERENCE, q("0", Unit.IN)),
    ]:
        with pytest.raises((TypeError, ValueError)):
            tee_flange_reference(
                q("1"),
                q("1"),
                spacing,
                q("9", Unit.IN),
                q(".375", Unit.IN),
                q("8", Unit.IN),
                q("33.75", Unit.KSI),
                q("27", Unit.KSI),
                stream=stream,
            )


def test_flange_us_si_parity_and_exact_threshold_boundaries() -> None:
    args = (
        q("3"),
        q("4"),
        q("3.625", Unit.IN),
        q("9", Unit.IN),
        q(".375", Unit.IN),
        q("8", Unit.IN),
        q("33.75", Unit.KSI),
        q("27", Unit.KSI),
    )
    us = tee_flange_reference(*args, stream=ReferenceStream.CORRECTED_REFERENCE)
    si = tuple(
        value.to(unit)
        for value, unit in zip(
            args,
            (Unit.N, Unit.N, Unit.MM, Unit.MM, Unit.MM, Unit.MM, Unit.MPA, Unit.MPA),
            strict=True,
        )
    )
    assert tee_flange_reference(*si, stream=ReferenceStream.CORRECTED_REFERENCE) == us
    for demand, outcome in [
        (".999999999999999999", "PASS"),
        ("1", "PASS"),
        ("1.000000000000000001", "FAIL"),
    ]:
        result = tee_flange_reference(
            q(demand),
            q("0"),
            q("4", Unit.IN),
            q("6", Unit.IN),
            q("1", Unit.IN),
            q("1", Unit.IN),
            q("1", Unit.KSI),
            q("1", Unit.KSI),
            stream=ReferenceStream.CORRECTED_REFERENCE,
        )
        assert result.summary == Decimal(demand)
        assert result.summary_outcome == outcome


@pytest.mark.parametrize("alignment", list(Alignment))
def test_each_proposed_supplement_use_names_existing_actual_mechanism_without_closing_it(
    alignment: Alignment,
) -> None:
    original = direct_mappings(alignment)
    additional = clip_tee_reference_uses(alignment)
    assert tuple(r.native_id for r in additional) == tuple(r.native_id for r in original)
    assert all(r.equation_locator and r.disposition == "REFERENCE_ONLY" for r in additional)
    assert all("no actual Direct mechanism discharged" in r.exclusion for r in additional)
    assert execute_workbook_case().summary_cell == "Calcs!D168"


def test_supplement_report_is_print_only_and_preserves_original_caches_separately() -> None:
    case = execute_clip_tee_reference(load_scale=Decimal("2.3"))
    before = repr(case)
    pdf = render_clip_tee_reference(case)
    text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert repr(case) == before
    assert case.tee_flange.summary_cell in text
    assert "summary outcome: FAIL" in text
    assert ".40912681878539675" in text
    assert str(case.tee_flange.summary) in text
    assert "REFERENCE_ONLY" in text
    assert "NO_CHORD_WEB_OR_JUNCTION_COVERAGE" in text
    assert "Source vinyl-ester" in text
