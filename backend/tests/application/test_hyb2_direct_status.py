"""Execute R1-S01 through S14 against real inactive adapters and rendered PDF text."""

import io
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from typing import Any, cast

import pytest
from pypdf import PdfReader

from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    Alignment,
    CaseManifest,
    PairedActions,
    PhysicalIdentity,
)
from frp_master_connection.application.hyb1_mapping import MISSING_IDS, REQUIRED_IDS
from frp_master_connection.application.hyb1_review import (
    NativeCapture,
    SupplementalSet,
    assess_hybrid,
)
from frp_master_connection.application.hyb2_direct import (
    calculate_direct_references,
    direct_geometry_digest,
    direct_source_mappings,
)
from frp_master_connection.application.hyb2_status import mechanism_name, present_review
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_reference import (
    SOURCE_SHA256,
    DirectGeometry,
    brace_rotation,
    execute_direct_source,
)
from frp_master_connection.calculation.rhm_reference import ReferenceStream
from frp_master_connection.reporting.hyb1_review import render_hyb1_review, review_record
from frp_master_connection.reporting.rhm_direct_review import render_direct_reference
from tests.hyb1_fixtures import case, complete_fixture, paired, q


def actual_fixture() -> tuple[PairedActions, NativeCapture, SupplementalSet]:
    actions = paired("ACTUAL_DIRECT")
    native, extra = complete_fixture(actions)
    return (
        actions,
        replace(
            native,
            rows=tuple(replace(r, evidence_scope="UNCHANGED_NATIVE_ASCE") for r in native.rows),
            status="YELLOW",
        ),
        replace(extra, rows=()),
    )


def source_actions() -> PairedActions:
    g = DirectGeometry()
    action = replace(
        case(ActionBasis.ASD, "SOURCE", p=".0134", v=".09155"), frame="DIRECT_UV_CENTROID"
    )
    identity = PhysicalIdentity(
        "TEST_ACCOUNT",
        "HYB2_DIRECT_REFERENCE",
        direct_geometry_digest(g),
        SOURCE_SHA256,
        "EXPLICIT_SOURCE_ASD",
        Alignment.SUPPORT,
    )
    return PairedActions(
        identity, (), (action,), CaseManifest((), ("SOURCE",), False, True, "SOURCE_SAVED_ASD_ONLY")
    )


def empty_native(actions: PairedActions) -> NativeCapture:
    payload = b'{"scope":"NO_NATIVE_ASCE_FOR_SOURCE"}'
    return NativeCapture(
        actions.identity,
        actions.digest,
        payload,
        sha256(payload).hexdigest(),
        (),
        "NO_NATIVE_ASCE",
        "SOURCE_REFERENCE_ONLY",
    )


def text(pdf: bytes) -> str:
    return " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )


def test_r1_s01_partial_pass_keeps_independent_results_and_visible_omissions() -> None:
    actions, native, extra = actual_fixture()
    extra = replace(
        extra, limitations=("Method review pending for independent receiving-W releases.",)
    )
    review = assess_hybrid(actions, native, extra)
    view = present_review(review)
    assert view.calculated_heading == "Evaluated checks: PASS"
    assert view.calculated_tone == "green"
    assert view.coverage_heading.endswith("PARTIAL")
    assert view.report_permitted
    assert extra.limitations[0] in view.method_notes
    assert "Supporting W first-row net tension" in view.omissions
    assert view.uncovered_count == len(review.uncovered)
    assert "Complete connection verification is not established" in view.executive_limit
    output = text(render_hyb1_review(review, actions))
    assert view.calculated_heading in output
    assert view.executive_limit in output
    assert not view.qualified_complete
    assert review.native_status == "YELLOW"


def test_r1_s02_failure_is_red_despite_unrelated_method_notes() -> None:
    actions, native, extra = actual_fixture()
    native = replace(
        native,
        rows=(replace(native.rows[0], ratio=Decimal(2), outcome="FAIL"), *native.rows[1:]),
        status="RED",
    )
    review = assess_hybrid(actions, native, extra)
    view = present_review(review)
    assert view.calculated_heading == "Evaluated checks: FAIL"
    assert view.calculated_tone == "red"
    assert review.governing_lrfd is not None
    assert review.governing_lrfd.ratio == 2
    assert view.report_permitted
    pdf = render_hyb1_review(review, actions)
    assert "Evaluated checks: FAIL" in text(pdf)
    # The current applicable failure heading uses a red PDF fill operator.
    stream = PdfReader(io.BytesIO(pdf)).pages[0].get_contents()
    assert stream is not None
    assert b"1 0 0 rg" in stream.get_data()
    assert "utilization=2" in view.failure_details[0]
    assert view.failure_details[0] in text(pdf)
    fallback = assess_hybrid(
        actions,
        replace(
            native, rows=tuple(replace(r, ratio=Decimal(".5"), outcome="PASS") for r in native.rows)
        ),
        extra,
    )
    assert "governing numerical row is unavailable" in present_review(fallback).failure_details[0]
    synthetic = paired()
    syn_native, syn_extra = complete_fixture(synthetic)
    syn_extra = replace(
        syn_extra,
        rows=(replace(syn_extra.rows[0], ratio=Decimal(2), outcome="FAIL"), *syn_extra.rows[1:]),
    )
    syn_review = assess_hybrid(synthetic, syn_native, syn_extra)
    assert present_review(syn_review).failure_details[0].startswith("ASD /")
    assert view.qualification == review.qualification
    source = source_actions()
    case0 = replace(source.asd[0], components=(q("6"), *source.asd[0].components[1:]))
    source = replace(source, asd=(case0,))
    integration = calculate_direct_references(source, DirectGeometry())
    reference = assess_hybrid(source, empty_native(source), integration.supplemental)
    assert reference.reference_outcome == "FAIL"
    assert reference.numerical_outcome == "NOT_EVALUATED"
    assert present_review(reference).calculated_tone == "neutral"


def test_r1_s03_reference_only_cannot_create_actual_pass_or_design_ur() -> None:
    actions = source_actions()
    integration = calculate_direct_references(actions, DirectGeometry())
    review = assess_hybrid(actions, empty_native(actions), integration.supplemental)
    view = present_review(review)
    assert view.calculated_heading == "Reference calculations - not an adopted design"
    assert view.calculated_tone == "neutral"
    assert view.coverage_heading == "Coverage not established"
    assert review.numerical_outcome == "NOT_EVALUATED"
    assert review.comparison_index is None
    assert review.reference_outcome == "PASS"
    assert review.reference_governing_asd is not None
    assert not review.analytical_candidate_complete
    assert not review.public_activation
    assert len(integration.records) == 1
    assert len(integration.supplemental.rows) == 7
    assert all(r.reference_stream == "CORRECTED_REFERENCE" for r in integration.supplemental.rows)
    assert all(r.reference_source_sha256 == SOURCE_SHA256 for r in integration.supplemental.rows)
    assert view.reference_streams == ("CORRECTED_REFERENCE",)
    content = text(render_hyb1_review(review, actions))
    assert "Reference calculations - not an adopted design" in content
    assert "reference numerical comparisons: PASS" in content
    assert "Executed reference streams: CORRECTED_REFERENCE" in content


def test_r1_s04_empty_set_never_passes() -> None:
    actions = source_actions()
    native = empty_native(actions)
    review = assess_hybrid(actions, native, SupplementalSet(actions.identity, actions.digest, ()))
    assert present_review(review).calculated_heading == "No structural checks evaluated"
    assert review.comparison_index is None
    assert review.governing_asd is None


def test_r1_s05_missing_asd_does_not_disable_valid_lrfd_or_convert_actions() -> None:
    actions, native, _ = actual_fixture()
    actions = replace(actions, asd=())
    native = replace(native, paired_digest=actions.digest)
    review = assess_hybrid(actions, native, SupplementalSet(actions.identity, actions.digest, ()))
    assert review.numerical_outcome == "PASS"
    assert not review.case_sets_complete
    assert "Missing input" in present_review(review).method_notes[-1]
    source = replace(source_actions(), asd=())
    result = calculate_direct_references(source, DirectGeometry())
    assert not result.records
    assert not result.supplemental.rows
    assert "no LRFD conversion" in result.withheld[0][1]


def test_r1_s06_stale_result_has_no_current_pass_or_ur_and_refuses_export() -> None:
    actions, native, extra = actual_fixture()
    changed = replace(actions, identity=replace(actions.identity, geometry="CHANGED"))
    review = assess_hybrid(changed, native, extra)
    assert not review.current
    assert review.numerical_outcome == "NOT_EVALUATED"
    assert review.comparison_index is None
    assert not present_review(review).report_permitted
    with pytest.raises(ValueError, match="Stale"):
        render_hyb1_review(review, changed)
    with pytest.raises(ValueError, match="different"):
        review_record(review, actions)


def test_r1_s07_invalid_physical_input_cannot_become_a_neutral_override() -> None:
    with pytest.raises(ValueError, match="outside"):
        execute_direct_source(geometry=DirectGeometry(xb=q(".1", Unit.IN)))
    with pytest.raises(ValueError, match="positive"):
        DirectGeometry(column_thickness=q("0", Unit.IN))
    actions, native, extra = actual_fixture()
    assert assess_hybrid(actions, native, extra).numerical_outcome == "PASS"


@pytest.mark.parametrize(
    "kind",
    [
        "moment",
        "out_of_plane",
        "negative_p",
        "negative_v",
        "unknown",
        "wrong_frame",
        "off_centroid",
        "brace_alignment",
    ],
)
def test_r1_s08_unsupported_actions_are_retained_not_zeroed(kind: str) -> None:
    actions = source_actions()
    case0 = actions.asd[0]
    components = list(case0.components)
    if kind in ("moment", "out_of_plane", "negative_p", "negative_v", "unknown"):
        index, value = {
            "moment": (5, q(".01", Unit.KIP_IN)),
            "out_of_plane": (2, q(".1")),
            "negative_p": (0, q("-.1")),
            "negative_v": (1, q("-.1")),
            "unknown": (0, None),
        }[kind]
        components[index] = value
        case0 = replace(case0, components=cast(Any, tuple(components)))
    elif kind == "wrong_frame":
        case0 = replace(case0, frame="GLOBAL")
    elif kind == "off_centroid":
        case0 = replace(case0, reference=(q("1", Unit.IN), q(unit=Unit.IN), q(unit=Unit.IN)))
    else:
        actions = replace(actions, identity=replace(actions.identity, alignment=Alignment.BRACE))
    actions = replace(actions, asd=(case0,))
    before = repr(actions)
    result = calculate_direct_references(actions, DirectGeometry())
    assert not result.records
    assert result.withheld
    assert not result.supplemental.rows
    assert repr(actions) == before
    assert actions.asd[0] == case0
    review = assess_hybrid(actions, empty_native(actions), result.supplemental)
    assert result.withheld[0][1] in present_review(review).method_notes[-1]
    assert "NOT EVALUATED" in review.limitations[0]
    if kind == "moment":
        report = render_hyb1_review(review, actions)
        assert result.withheld[0][1] in text(report)


def test_r1_s09_complete_analytical_test_domain_does_not_install_qualification() -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    review = assess_hybrid(actions, native, extra)
    view = present_review(review)
    assert view.coverage_heading.endswith("COMPLETE")
    assert review.evidence_scope == "SYNTHETIC_TEST_ONLY"
    assert not view.qualified_complete
    assert not review.public_activation
    assert "qualification" in view.executive_limit


def test_r1_s10_shared_group_has_one_capacity_and_every_mechanism_has_a_source_record() -> None:
    for alignment in Alignment:
        mappings = direct_source_mappings(alignment)
        assert {m.native_id for m in mappings} == set(REQUIRED_IDS)
        assert all(m.disposition == "REFERENCE_ONLY" for m in mappings)
        assert any("D183:D205" in m.equation_locator for m in mappings)
        assert any("D211:D239" in m.equation_locator for m in mappings)
    book = execute_direct_source()
    assert len([r for r in book.comparisons if "BOLTS" in r.method_id]) == 1
    assert len(book.source_summary) == 8
    assert len(book.comparisons) == 7
    with pytest.raises(TypeError):
        direct_source_mappings(cast(Alignment, "SUPPORT"))
    actions = paired()
    native, extra = complete_fixture(actions)
    # A fixed synthetic compound release covers two test mechanisms with one ratio.
    joint = tuple(
        replace(
            r,
            mechanism="TEST_JOINT_RELEASE",
            joint_mechanisms=MISSING_IDS[:2],
            joint_coverage_evidence="SYNTHETIC_JOINT_RELEASE_TEST_ONLY",
        )
        for r in extra.rows
        if r.mechanism == MISSING_IDS[0]
    )
    rest = tuple(r for r in extra.rows if r.mechanism not in MISSING_IDS[:2])
    compound = replace(extra, rows=(*joint, *rest))
    assert assess_hybrid(actions, native, compound).analytical_candidate_complete
    assert len(compound.rows) == len(extra.rows) - len(actions.asd)
    with pytest.raises(ValueError, match="Joint coverage"):
        replace(joint[0], joint_coverage_evidence="CALLER_APPROVED")
    with pytest.raises(ValueError, match="Joint coverage"):
        replace(joint[0], joint_mechanisms=(MISSING_IDS[0], MISSING_IDS[0]))
    with pytest.raises(ValueError, match="Joint coverage"):
        replace(joint[0], joint_mechanisms=("UNKNOWN",))


def test_r1_s11_method_decisions_do_not_instruct_user_to_resize_or_hide_requirements() -> None:
    actions, native, extra = actual_fixture()
    review = assess_hybrid(actions, native, extra)
    view = present_review(review)
    assert "method developer/reviewer" in " ".join(view.method_notes).lower()
    assert "resize" not in str(view).lower()
    assert review.uncovered
    assert mechanism_name("FIRST_ROW:layer-A") == "Angle first-row net tension"
    assert mechanism_name("INTERROW:layer-B:BOLT_LINE_1") == "Supporting W inter-row shear-out"
    assert mechanism_name("BLOCK_SHEAR:layer-A:RIGHT") == "Angle right block-shear release"
    assert mechanism_name("CUSTOM_ID") == "CUSTOM ID"


def test_r1_s12_corrected_reference_does_not_inherit_literal_ok_or_ref_defect() -> None:
    source = execute_direct_source(axial=q("6", Unit.KIP))
    assert source.bolt_status == "FAIL"
    assert source.stream is ReferenceStream.CORRECTED_REFERENCE
    assert source.original_literal_e46 == "OK"


def test_r1_s13_export_has_limits_in_summary_full_evidence_and_no_private_fields() -> None:
    book = execute_direct_source()
    before = repr(book)
    pdf = render_direct_reference(book)
    reader = PdfReader(io.BytesIO(pdf))
    first = reader.pages[0].extract_text() or ""
    assert "Reference calculations" in first
    assert "first-row" in first
    assert "Material limitations" in first
    assert "Qualification" in first
    content = text(pdf)
    for row in book.comparisons:
        assert row.method_id in content
        assert str(row.utilization) in content
    assert "D46 and D159" in content
    assert "R50" in content
    assert all(word not in content for word in ("report_handle", "password", "private_source.xlsx"))
    assert before == repr(book)


def test_r1_s14_native_payload_and_activation_boundary_remain_unchanged() -> None:
    actions, native, extra = actual_fixture()
    before = repr((actions, native, extra))
    review = assess_hybrid(actions, native, extra)
    assert before == repr((actions, native, extra))
    assert review.native_payload_sha256 == native.payload_sha256
    assert not review.public_activation
    assert not present_review(review).qualified_complete
    assert not brace_rotation(DirectGeometry()).nominal_fit


@pytest.mark.parametrize("field", ["geometry", "material"])
def test_direct_source_binding_rejects_wrong_revision(field: str) -> None:
    actions = source_actions()
    actions = replace(actions, identity=replace(cast(Any, actions.identity), **{field: "WRONG"}))
    with pytest.raises(ValueError, match="exact geometry"):
        calculate_direct_references(actions, DirectGeometry())
