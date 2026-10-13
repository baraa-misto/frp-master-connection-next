"""Independent case, currentness, coverage and preserved status controls."""

import io
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from typing import Any, Literal, cast

import pytest
from pypdf import PdfReader

from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    Alignment,
)
from frp_master_connection.application.hyb1_mapping import (
    ADDITIONAL_3D,
    EXISTING_IDS,
    HEEL,
    MISSING_IDS,
    direct_mappings,
)
from frp_master_connection.application.hyb1_review import (
    assess_hybrid,
    calculate_reference_cases,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.reporting.hyb1_review import (
    TITLE,
    canonical_record,
    capture_signed_native,
    render_hyb1_review,
    request_digest,
    review_record,
)
from frp_master_connection.reporting.snapshot import SnapshotError, SnapshotSigner
from tests.hyb1_fixtures import case, complete_fixture, paired, q, row


def test_full_synthetic_case_inventory_and_independent_governing_cases() -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    before = (native, extra, actions)
    review = assess_hybrid(actions, native, extra)
    assert review.analytical_candidate_complete
    assert review.governing_lrfd is not None
    assert review.governing_asd is not None
    assert review.governing_lrfd.case_id == "L2"
    assert review.governing_asd.case_id == "A1"
    assert review.comparison_index == Decimal(".8")
    assert review.evidence_scope == "SYNTHETIC_TEST_ONLY"
    assert review.basis_adoption == "PENDING_OWNER_ENGINEERING_REVIEW"
    assert review.public_activation is False
    assert before == (native, extra, actions)
    with pytest.raises(FrozenInstanceError):
        cast(Any, actions.identity).account = "OTHER"


ERROR_PATTERN = (
    r"(required|must|needs|match|mandatory|duplicate|Duplicate|wrong|basis|Case|Reference|"
    r"Snapshot|positive|finite|Every|cannot|An|No |RHM|Unknown|dimension|convert|original|"
    r"recorded|Retain|excludes)"
)


@pytest.mark.parametrize("field", ["account", "connection", "geometry", "material", "actions"])
def test_physical_identity_required_and_stale_invalidates_every_field(field: str) -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(cast(Any, actions.identity), **{field: ""})
    changed = replace(actions, identity=replace(cast(Any, actions.identity), **{field: "CHANGED"}))
    review = assess_hybrid(changed, native, extra)
    assert not review.current
    assert not review.analytical_candidate_complete


def test_alignment_typed_and_non_synthetic_cannot_install_mock_coverage() -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    with pytest.raises(TypeError):
        replace(actions.identity, alignment=cast(Alignment, "BRACE"))
    actual = paired("ACTUAL_DIRECT")
    native = replace(native, identity=actual.identity, paired_digest=actual.digest)
    extra = replace(extra, identity=actual.identity, paired_digest=actual.digest)
    review = assess_hybrid(actual, native, extra)
    assert review.numerical_outcome == "PASS"
    assert not review.analytical_candidate_complete
    assert set(MISSING_IDS + ADDITIONAL_3D) <= set(review.uncovered)
    with pytest.raises(TypeError):
        cast(Any, assess_hybrid)(actual, native, extra, approved=True, required_checks=[])


@pytest.mark.parametrize("field", ["case_id", "source_id", "scenario_family", "frame"])
def test_case_source_identity_required(field: str) -> None:
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(cast(Any, case()), **{field: ""})


def test_action_basis_dimensions_and_complete_component_inventory() -> None:
    with pytest.raises(TypeError):
        replace(case(), basis=cast(ActionBasis, "LRFD"))
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(case(), components=cast(Any, (q(),)))
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(case(), reference=cast(Any, (q(unit=Unit.IN),)))
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(
            case(),
            components=(
                q(unit=Unit.IN),
                q(),
                q(),
                q(unit=Unit.KIP_IN),
                q(unit=Unit.KIP_IN),
                q(unit=Unit.KIP_IN),
            ),
        )
    unknown = replace(
        case(),
        components=(None, q(), q(), q(unit=Unit.KIP_IN), q(unit=Unit.KIP_IN), q(unit=Unit.KIP_IN)),
    )
    assert not unknown.complete
    assert unknown.digest != case().digest
    assert case(v="0").complete


def test_exact_unit_and_reference_transport_retains_all_moments() -> None:
    original = case(v="2", p="3")
    si = replace(
        cast(Any, original),
        components=tuple(
            q.to(Unit.N if i < 3 else Unit.N_MM)
            for i, q in enumerate(original.components)
            if q is not None
        ),
    )
    assert si.digest == original.digest
    moved = original.transport(
        (q("1", Unit.IN), q(unit=Unit.IN), q(unit=Unit.IN)), frame=original.frame
    )
    assert moved.components[5] == q("-3", Unit.KIP_IN)
    assert (
        moved.transport(original.reference, frame=original.frame).components == original.components
    )
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        original.transport(original.reference, frame="OTHER")
    unknown = replace(original, components=(None, *original.components[1:]))
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        unknown.transport(original.reference, frame=original.frame)
    tiny = replace(
        original,
        reference=(
            q("1.00000000000000000000000000000000001", Unit.IN),
            q(unit=Unit.IN),
            q(unit=Unit.IN),
        ),
    )
    assert tiny.digest != moved.digest


@pytest.mark.parametrize(
    "mutation", ["source", "duplicate", "empty", "wrong_basis", "case_duplicate", "scenario"]
)
def test_invalid_manifest_and_case_set(mutation: str) -> None:
    actions = paired()
    mutations: dict[str, Callable[[], object]] = {
        "source": lambda: replace(actions.manifest, declaration_source=""),
        "duplicate": lambda: replace(actions.manifest, required_asd=("A1", "A1")),
        "empty": lambda: replace(actions.manifest, required_asd=("",)),
        "wrong_basis": lambda: replace(actions, asd=actions.lrfd),
        "case_duplicate": lambda: replace(actions, lrfd=(actions.lrfd[0], actions.lrfd[0])),
        "scenario": lambda: replace(
            actions, asd=(replace(actions.asd[0], scenario_family="OTHER"),)
        ),
    }
    with pytest.raises(
        ValueError, match=r"(provenance|unique|wrong basis|Duplicate|scenario family)"
    ):
        mutations[mutation]()


@pytest.mark.parametrize(
    "mutation", ["no_asd", "not_declared", "empty_required", "missing_case", "unknown"]
)
def test_incomplete_supplied_cases_do_not_infer_or_reassemble_actions(mutation: str) -> None:
    actions = paired()
    if mutation == "no_asd":
        actions = replace(actions, asd=())
    elif mutation == "not_declared":
        actions = replace(actions, manifest=replace(actions.manifest, asd_declared_complete=False))
    elif mutation == "empty_required":
        actions = replace(actions, manifest=replace(actions.manifest, required_asd=()))
    elif mutation == "missing_case":
        actions = replace(actions, lrfd=actions.lrfd[:1])
    else:
        actions = replace(
            actions,
            asd=(
                replace(actions.asd[0], components=(None, *actions.asd[0].components[1:])),
                actions.asd[1],
            ),
        )
    assert not actions.complete


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_row",
        "bad_na",
        "unknown_case",
        "case_digest",
        "basis",
        "duplicate",
        "native_basis",
        "extra_basis",
    ],
)
def test_fixed_requirement_coverage_and_record_binding(mutation: str) -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    first = extra.rows[0]
    if mutation == "missing_row":
        extra = replace(extra, rows=extra.rows[1:])
    elif mutation == "bad_na":
        extra = replace(
            extra, rows=(replace(first, ratio=None, outcome="NOT_APPLICABLE"), *extra.rows[1:])
        )
    elif mutation == "unknown_case":
        extra = replace(extra, rows=(replace(first, case_id="UNDECLARED"), *extra.rows[1:]))
    elif mutation == "case_digest":
        extra = replace(extra, rows=(replace(first, case_digest="STALE"), *extra.rows[1:]))
    elif mutation == "basis":
        extra = replace(extra, rows=(replace(first, basis=ActionBasis.LRFD), *extra.rows[1:]))
    elif mutation == "duplicate":
        extra = replace(extra, rows=(*extra.rows, first))
    elif mutation == "native_basis":
        native = replace(
            native, rows=(replace(native.rows[0], basis=ActionBasis.ASD), *native.rows[1:])
        )
    else:
        extra = replace(
            extra,
            rows=(
                replace(
                    first, basis=ActionBasis.LRFD, case_id="L1", case_digest=actions.lrfd[0].digest
                ),
                *extra.rows[1:],
            ),
        )
    assert not assess_hybrid(actions, native, extra).analytical_candidate_complete


def test_valid_na_distinct_from_omission_and_zero_capacity() -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    native = replace(
        native,
        rows=tuple(
            replace(r, ratio=None, outcome="NOT_APPLICABLE", na_reason="TEST geometric absence")
            if r.mechanism == HEEL
            else r
            for r in native.rows
        ),
    )
    assert assess_hybrid(actions, native, extra).analytical_candidate_complete
    native = replace(native, rows=tuple(r for r in native.rows if r.mechanism != HEEL))
    assert HEEL in assess_hybrid(actions, native, extra).uncovered


@pytest.mark.parametrize("channel", ["native", "supplemental", "native_status"])
def test_any_failure_retained_no_method_shopping(channel: str) -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    if channel == "native":
        native = replace(
            native,
            rows=(replace(native.rows[0], ratio=Decimal(2), outcome="FAIL"), *native.rows[1:]),
        )
    elif channel == "supplemental":
        extra = replace(
            extra, rows=(replace(extra.rows[0], ratio=Decimal(2), outcome="FAIL"), *extra.rows[1:])
        )
    else:
        native = replace(native, status="RED")
    assert assess_hybrid(actions, native, extra).numerical_outcome == "FAIL"


def test_empty_comparisons_no_evaluation_and_native_authority_digest() -> None:
    actions = paired()
    native, extra = complete_fixture(actions)
    review = assess_hybrid(actions, replace(native, rows=()), replace(extra, rows=()))
    assert review.numerical_outcome == "NOT_EVALUATED"
    assert review.comparison_index is None
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(native, immutable_payload=b"changed")
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(native, provenance="")


@pytest.mark.parametrize("mutation", ["basis", "negative", "contradiction", "absent_ratio", "nan"])
def test_comparison_refuses_invalid_basis_outcome_or_ratio(mutation: str) -> None:
    changes: dict[str, object] = {
        "basis": cast(ActionBasis, "ASD"),
        "negative": Decimal(-1),
        "contradiction": "FAIL",
        "absent_ratio": None,
        "nan": Decimal("NaN"),
    }
    key = {
        "negative": "ratio",
        "contradiction": "outcome",
        "absent_ratio": "ratio",
        "nan": "ratio",
    }.get(mutation, mutation)
    with pytest.raises((ValueError, TypeError)):
        replace(cast(Any, row()), **{key: changes[mutation]})


def test_reference_cases_evaluate_each_explicit_asd_combination_only() -> None:
    actions = paired("HYB1_WORKBOOK_REFERENCE")
    result = calculate_reference_cases(actions)
    assert len(result.rows) == 10
    assert all(r.mapping == "REFERENCE_ONLY" for r in result.rows)
    assert {r.case_id for r in result.rows} == {"A1", "A2"}
    assert not calculate_reference_cases(replace(actions, asd=())).rows
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        calculate_reference_cases(paired("ACTUAL_DIRECT"))
    for changed in [
        replace(actions.asd[0], frame="GLOBAL"),
        replace(actions.asd[0], components=(None, *actions.asd[0].components[1:])),
        replace(actions.asd[0], components=(*actions.asd[0].components[:5], q("1", Unit.KIP_IN))),
    ]:
        with pytest.raises(
            ValueError,
            match=ERROR_PATTERN,
        ):
            calculate_reference_cases(replace(actions, asd=(changed,)))


@pytest.mark.parametrize("alignment", list(Alignment))
def test_both_physical_mapping_inventories_keep_real_ends_holes_and_3d(
    alignment: Alignment,
) -> None:
    rows = direct_mappings(alignment)
    assert {r.native_id for r in rows} >= set(MISSING_IDS + ADDITIONAL_3D)
    assert not any(r.disposition == "MAPPED_CANDIDATE" for r in rows)
    assert "display crop" in next(r.exclusion for r in rows if r.native_id == MISSING_IDS[4])
    assert all("Q" in r.decision_id for r in rows)
    if alignment is Alignment.SUPPORT:
        assert HEEL in {r.native_id for r in rows}
    with pytest.raises(TypeError):
        direct_mappings(cast(Alignment, "BRACE"))


def test_signed_native_capture_and_actual_report_consistency() -> None:
    actions = paired()
    request = {"fixture": "SYNTHETIC_CAPTURE_NOT_ACTUAL_ENGINEERING"}
    digest = request_digest(request)
    actions = replace(actions, identity=replace(actions.identity, geometry=digest, material=digest))
    signer = SnapshotSigner(b"HYB1-ISOLATED-TEST-KEY-NOT-DEPLOYED-32")
    result: dict[str, Any] = {
        "final_decision": {
            "final_status": "YELLOW",
            "schedule": [
                {
                    "check_id": EXISTING_IDS[0],
                    "utilization": ".5",
                    "outcome": "PASS",
                    "demand": "1 N",
                    "design_resistance": "2 N",
                    "reason": "SYNTHETIC CAPTURE TEST",
                },
                {
                    "check_id": HEEL,
                    "utilization": None,
                    "outcome": "NOT_APPLICABLE",
                    "demand": None,
                    "design_resistance": None,
                    "reason": "BOUNDED TEST N/A",
                },
            ],
        }
    }

    def issue(
        *,
        kind: Literal["design", "input_only"] = "design",
        result: dict[str, Any] = result,
        provenance: dict[str, Any] | None = None,
    ) -> str:
        return signer.issue(
            family="multi-row",
            kind=kind,
            request=request,
            result=result,
            account_id=actions.identity.account,
            input_provenance=(
                {"hyb1_lrfd_action_digest": actions.lrfd[0].digest}
                if provenance is None
                else provenance
            ),
        )

    token = issue()
    native = capture_signed_native(signer, token, actions, "L1")
    _, extra = complete_fixture(actions)
    review = assess_hybrid(actions, native, extra)
    reference = calculate_reference_cases(paired("HYB1_WORKBOOK_REFERENCE"))
    data = render_hyb1_review(review, actions, workbooks=reference.workbooks)
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert TITLE in " ".join(text.split())
    assert "Calcs!D168" in text
    assert "0.75" in text
    assert "SYNTHETIC" in text
    assert token not in text
    assert actions.identity.account not in text
    assert all(r.mechanism in text for r in review.rows)
    assert "WORKBOOK_REFERENCE" in text
    empty = replace(actions, asd=(), transport_trace=(actions.lrfd[0],))
    empty_review = assess_hybrid(
        empty,
        replace(native, paired_digest=empty.digest),
        replace(extra, rows=(), paired_digest=empty.digest),
    )
    assert b"%PDF" in render_hyb1_review(empty_review, empty)
    assert native.immutable_payload == canonical_record(result)
    for capacity_outcome, ratio, status in (
        ("CAPACITY_PASS", ".5", "GREEN"),
        ("CAPACITY_FAIL", "1.5", "RED"),
    ):
        qualified = {
            "final_decision": {
                **result["final_decision"],
                "final_status": status,
                "qualification_scope_state": "SYNTHETIC_MATCH_TEST_ONLY",
                "qualification_coverage_state": "COVERED_BY_QUALIFICATION",
                "qualification_capacity_state": capacity_outcome,
                "schedule": [
                    {
                        **result["final_decision"]["schedule"][0],
                        "outcome": capacity_outcome,
                        "utilization": ratio,
                    },
                    {
                        **result["final_decision"]["schedule"][1],
                        "outcome": "COVERED_BY_QUALIFICATION",
                    },
                ],
            }
        }
        qualified_native = capture_signed_native(signer, issue(result=qualified), actions, "L1")
        assert qualified_native.immutable_payload == canonical_record(qualified)
        assert qualified_native.status == status
        qualified_review = assess_hybrid(actions, qualified_native, extra)
        assert capacity_outcome in qualified_review.qualification
        assert qualified_native.rows[1].native_outcome == "COVERED_BY_QUALIFICATION"
        assert qualified_review.public_activation is False
        assert qualified_review.evidence_scope == "SYNTHETIC_TEST_ONLY"
    for changed, case_id, handle in [
        (replace(actions, identity=replace(actions.identity, geometry="STALE")), "L1", token),
        (actions, "MISSING", token),
        (actions, "L1", issue(provenance={})),
        (actions, "L1", issue(kind="input_only")),
        (actions, "L1", issue(result={})),
    ]:
        with pytest.raises(
            ValueError,
            match=ERROR_PATTERN,
        ):
            capture_signed_native(signer, handle, changed, case_id)
    with pytest.raises(SnapshotError):
        capture_signed_native(
            signer,
            token,
            replace(actions, identity=replace(actions.identity, account="OTHER")),
            "L1",
        )
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        review_record(review, paired())
    bad = replace(review, rows=(replace(review.rows[0], resistance_trace=cast(str, object())),))
    with pytest.raises(TypeError):
        review_record(bad, actions)
