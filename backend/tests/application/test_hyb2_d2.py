"""D2 real arithmetic, physical fit, independent coverage and offline adoption guards."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Any

import pytest

from frp_master_connection.application.hyb1_contract import ActionBasis, Alignment, CaseManifest
from frp_master_connection.application.hyb1_mapping import MISSING_IDS, REQUIRED_IDS
from frp_master_connection.application.hyb2_d2 import (
    DEFAULT_AUTHORITY,
    D2Assessment,
    HardwareEvidence,
    SourceConditions,
    assess_d2,
    physical_fit,
)
from frp_master_connection.application.hyb2_d2_registry import (
    TEST_DOMAIN,
    Disposition,
    EvidenceAuthority,
    ReviewedEvidence,
    ReviewState,
    proposals,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest
from frp_master_connection.reporting.hyb2_d2_service import ReviewSource
from tests.application.test_hyb2_direct_status import empty_native
from tests.hyb1_fixtures import q
from tests.hyb2_d2_fixtures import support_source

TODAY = date(2026, 10, 19)


def result(
    source: ReviewSource, *, authority: EvidenceAuthority = DEFAULT_AUTHORITY
) -> D2Assessment:
    return assess_d2(
        source.actions,
        empty_native(source.actions),
        geometry=source.geometry,
        conditions=source.conditions,
        hardware=source.hardware,
        today=TODAY,
        authority=authority,
    )


def synthetic() -> ReviewSource:
    s = support_source()
    a = s.actions
    lrfd = replace(a.asd[0], basis=ActionBasis.LRFD, case_id="EXPLICIT_TEST_LRFD")
    a = replace(
        a,
        identity=replace(a.identity, connection=TEST_DOMAIN),
        lrfd=(lrfd,),
        manifest=CaseManifest(
            (lrfd.case_id,),
            (a.asd[0].case_id,),
            True,
            True,
            "HAND_DEFINED_TEST_ONLY_NOT_A_DESIGN_ENVELOPE",
        ),
    )
    return replace(s, actions=a)


def evidence(s: ReviewSource, **kwargs: object) -> ReviewedEvidence:
    values: dict[str, Any] = {
        "method_id": "TEST_COMBINED_PROOF_NOT_AN_ENGINEERING_LAW",
        "revision": "TEST1",
        "mechanisms": REQUIRED_IDS,
        "comparison_ids": ("DIRECT_BRACE_GLOBAL",),
        "geometry": s.actions.identity.geometry,
        "material": s.actions.identity.material,
        "actions_digest": s.actions.digest,
        "context_sha256": sha256(repr((s.geometry, s.conditions, s.hardware)).encode()).hexdigest(),
        "alignment": s.actions.identity.alignment,
        "physical_path": "TEST_ONLY_ENTIRE_SYNTHETIC_INVENTORY",
        "scope_and_exclusions": "SYNTHETIC ONLY; no structural approval or qualification",
        "engineer": "SYNTHETIC_TEST_ROLE_NOT_A_PERSON_OR_SIGNATURE",
        "reviewed": TODAY,
        "expires": TODAY + timedelta(days=1),
        "evidence_sha256": "a" * 64,
        "signature_document_sha256": "b" * 64,
        "state": ReviewState.APPROVED,
    }
    values.update(kwargs)
    return ReviewedEvidence(**values)


def test_d2_02_05_08_12_13_17_actual_source_arithmetic_and_packet() -> None:
    s = support_source()
    r = result(s)
    assert r.evaluated_outcome == "PASS"
    assert r.tone == "green"
    assert r.coverage_state == "NOT_ESTABLISHED"
    assert not r.analytical_complete
    assert not r.complete_connection_verification
    assert not r.public_activation
    assert len(r.coverage) == 17
    assert len(r.comparisons) == 7
    current = r.r3_records[0][1]
    assert current.vertical_pitch_in == 2
    assert float(current.transverse_ltv_in) == pytest.approx(1.716129811447289)
    assert float(current.longitudinal_stagger_in) == pytest.approx(1.02708250411634)
    assert current.blocks[0].connector_net_area_in2 == Decimal(".7185")
    assert current.blocks[2].connector_net_area_in2 == Decimal(".538875")
    assert all(row.evidence_scope == "HYB2_DIRECT_REFERENCE" for row in r.comparisons)
    assert all(c.disposition is Disposition.PENDING for c in r.coverage)
    pending = {p.native_id: p for p in r.method_packet}
    assert "combined-mode proof" in pending[MISSING_IDS[0]].exact_required_artifact
    assert "3D control volume" in pending[MISSING_IDS[3]].exact_required_artifact
    assert "integral web" in pending[MISSING_IDS[4]].physical_fragment
    assert "field experience" in r.notes[0].lower()
    assert {p.native_id for p in proposals(Alignment.BRACE)} == set(REQUIRED_IDS)
    with pytest.raises(TypeError, match="alignment"):
        proposals("SUPPORT")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "change",
    [
        "overload",
        "missing-asd",
        "moment",
        "fz",
        "unknown",
        "negative",
        "reference",
        "frame",
        "material",
        "resin",
        "hardware",
        "brace",
    ],
)
def test_d2_07_09_10_11_16_17_24_boundaries(change: str) -> None:
    s = support_source()
    a, case = s.actions, s.actions.asd[0]
    if change == "missing-asd":
        s = replace(s, actions=replace(a, asd=()))
    elif change in ("material", "resin", "hardware"):
        condition_changes: dict[str, dict[str, Any]] = {
            "material": {"strength_basis": "MAT1_DO_NOT_BLEND"},
            "resin": {"resin": "VINYL_ESTER"},
            "hardware": {"hardware": "F593_NOT_A_SOURCE_PROVIDER"},
        }
        conditions = replace(s.conditions, **condition_changes[change])
        s = replace(s, conditions=conditions)
    elif change == "brace":
        s = replace(s, actions=replace(a, identity=replace(a.identity, alignment=Alignment.BRACE)))
    else:
        values = list(case.components)
        if change == "overload":
            values[0] = q("60")
        elif change == "moment":
            values[5] = q("1", Unit.KIP_IN)
        elif change == "fz":
            values[2] = q(".1")
        elif change == "unknown":
            values[3] = None
        elif change == "negative":
            values[0] = q("-.09155")
        case = replace(case, components=tuple(values))  # type: ignore[arg-type]
        if change == "reference":
            case = replace(case, reference=(q("1", Unit.IN), *case.reference[1:]))
        if change == "frame":
            case = replace(case, frame="WRONG_POSITIVE_N")
        s = replace(s, actions=replace(a, asd=(case,)))
    r = result(s)
    if change == "overload":
        assert r.evaluated_outcome == "FAIL"
        assert r.tone == "red"
        assert r.governing_asd is not None
        assert r.governing_asd.ratio is not None
        assert r.governing_asd.ratio > 1
    else:
        assert r.evaluated_outcome == "NOT_EVALUATED"
        assert r.withheld
        assert not r.comparisons
    assert not r.analytical_complete
    if change == "brace":
        assert r.fit.state == "NOT_FIT"
        assert r.source_domain == "BRACE_GEOMETRY_ONLY_NO_SUPPORT_SOURCE_MAPPING"
        assert r.fit.conditional_overhang_in is None


@pytest.mark.parametrize(
    ("face", "od", "expected", "overhang"),
    [
        ("UNVERIFIED", None, "PHYSICAL_FIT_UNVERIFIED", None),
        ("R3_BRACE_END_FREE_EDGE", "1", "NOT_FIT", ".0625"),
        ("R3_BRACE_END_FREE_EDGE", ".875", "PHYSICAL_FIT_UNVERIFIED", "0"),
        ("R3_BRACE_END_FREE_EDGE", "1.5", "NOT_FIT", ".3125"),
        ("DIFFERENT_FACE", "1", "PHYSICAL_FIT_UNVERIFIED", None),
    ],
)
def test_d2_15_washer_face_is_not_inferred(
    face: str, od: str | None, expected: str, overhang: str | None
) -> None:
    hw = HardwareEvidence(
        face, q(od, Unit.IN) if od else None, "a" * 64 if face != "UNVERIFIED" else ""
    )
    s = replace(support_source(), hardware=hw)
    r = result(s)
    assert r.fit.state == expected
    assert r.fit.conditional_overhang_in == Decimal(".0625")
    assert r.fit.actual_overhang_in == (Decimal(overhang) if overhang is not None else None)
    assert r.evaluated_outcome == "PASS"  # Independent numerical status, not installable fit.
    test_source = replace(
        s,
        actions=replace(
            s.actions,
            identity=replace(
                s.actions.identity, connection="HYB2_D2_HYPOTHETICAL_HARDWARE_TEST_ONLY"
            ),
        ),
    )
    assert result(test_source).scope.startswith("HYPOTHETICAL_FIT_TEST_ONLY")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bearing_face": "invented"},
        {"washer_od": q("0", Unit.IN)},
        {"bearing_face": "DIFFERENT_FACE"},
        {"bearing_face": "DIFFERENT_FACE", "face_evidence_sha256": "Z" * 64},
    ],
)
def test_hardware_validation(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"(required|digest)"):
        HardwareEvidence(**kwargs)


def test_d2_22_24_geometry_and_fit_fresh_not_stale() -> None:
    s = support_source()
    for g in (
        R3Geometry(hole=q("3", Unit.IN)),
        R3Geometry(xb=q(".8", Unit.IN)),
        R3Geometry(diameter=q(".6", Unit.IN), hole=q(".7", Unit.IN)),
    ):
        updated = replace(
            s,
            geometry=g,
            actions=replace(
                s.actions, identity=replace(s.actions.identity, geometry=geometry_digest(g))
            ),
        )
        r = result(updated)
        assert r.paired_digest != result(s).paired_digest
        if g.hole.to(Unit.IN).magnitude == 3:
            assert r.fit.state == "NOT_FIT"
    assert (
        physical_fit(None, Alignment.BRACE, HardwareEvidence(), None).state
        == "PHYSICAL_FIT_UNVERIFIED"
    )


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "future",
        "revoked",
        "blank",
        "bad-digest",
        "geometry",
        "material",
        "actions",
        "alignment",
        "duplicate",
        "unknown",
        "no-comparison",
        "no-pin",
    ],
)
def test_d2_18_missing_revoked_expired_scope_cannot_adopt(change: str) -> None:
    s = synthetic()
    updates: dict[str, dict[str, Any]] = {
        "expired": {"expires": TODAY - timedelta(days=1)},
        "future": {"reviewed": TODAY + timedelta(days=1)},
        "revoked": {"state": ReviewState.REVOKED},
        "blank": {"engineer": ""},
        "bad-digest": {"evidence_sha256": "z" * 64},
        "geometry": {"geometry": "other"},
        "material": {"material": "other"},
        "actions": {"actions_digest": "other"},
        "alignment": {"alignment": Alignment.BRACE},
        "duplicate": {"mechanisms": (MISSING_IDS[0], MISSING_IDS[0])},
        "unknown": {"mechanisms": ("INVENTED",)},
        "no-comparison": {"comparison_ids": ()},
        "no-pin": {},
    }
    e = evidence(s, **updates[change])
    authority = EvidenceAuthority((e,), () if change == "no-pin" else (e.digest,))
    assert not result(s, authority=authority).analytical_complete


def test_d2_19_20_synthetic_joint_coverage_once_not_qualification() -> None:
    s = synthetic()
    e = evidence(s)
    authority = EvidenceAuthority((e,), (e.digest,))
    r = result(s, authority=authority)
    assert r.analytical_complete
    assert r.coverage_state == "COMPLETE"
    assert len(r.comparisons) == 7  # Same arithmetic rows not duplicated for covered labels.
    assert all(c.evidence_id == e.digest for c in r.coverage)
    assert r.qualification == "NOT_ESTABLISHED_SECTION_2_3_2"
    assert not r.complete_connection_verification
    assert not r.public_activation
    assert r.scope.startswith("SYNTHETIC_TEST_ONLY")
    changed_hardware = replace(s, hardware=HardwareEvidence(washer_od=q("1", Unit.IN)))
    assert not result(changed_hardware, authority=authority).analytical_complete
    with pytest.raises(TypeError, match="Typed"):
        replace(e, state="APPROVED")  # type: ignore[arg-type]
    production = replace(
        s,
        actions=replace(
            s.actions, identity=replace(s.actions.identity, connection="ACTUAL_DIRECT")
        ),
    )
    e2 = evidence(production)
    assert not result(
        production, authority=EvidenceAuthority((e2,), (e2.digest,))
    ).analytical_complete
    wrong_comparison = evidence(s, comparison_ids=("DIRECT_BRACE_GLOBAL", "ABSENT"))
    assert not result(
        s, authority=EvidenceAuthority((wrong_comparison,), (wrong_comparison.digest,))
    ).analytical_complete
    na = evidence(s, comparison_ids=(), physical_na=True)
    assert all(
        c.disposition is Disposition.NA
        for c in result(s, authority=EvidenceAuthority((na,), (na.digest,))).coverage
    )


def test_d2_23_source_unit_frame_permutation_arithmetic() -> None:
    s = support_source()
    original = result(s)
    a = s.actions
    converted_values = tuple(
        x.to(Unit.N if i < 3 else Unit.N_MM) if x is not None else None
        for i, x in enumerate(a.asd[0].components)
    )
    converted = replace(
        a.asd[0],
        components=(
            converted_values[0],
            converted_values[1],
            converted_values[2],
            converted_values[3],
            converted_values[4],
            converted_values[5],
        ),
    )
    same = result(replace(s, actions=replace(a, asd=(converted,))))
    assert original.comparisons == same.comparisons
    assert original.paired_digest == same.paired_digest
    assert s.geometry is not None
    g = replace(
        s.geometry,
        reverse_bolt_order=True,
        frame_rotation_degrees=Decimal(17),
        midpoint=(q("3.7", Unit.IN), q("-4.2", Unit.IN)),
    )
    r = result(
        replace(
            s,
            geometry=g,
            actions=replace(a, identity=replace(a.identity, geometry=geometry_digest(g))),
        )
    )
    # Reuse R3 rigid-frame arithmetic comparison budget, not an engineering tolerance.
    assert [float(r.ratio) for r in r.comparisons if r.ratio is not None] == pytest.approx(
        [float(r.ratio) for r in original.comparisons if r.ratio is not None], rel=1e-13
    )


def test_native_currentness_and_duplicate_guards() -> None:
    s = support_source()
    n = empty_native(s.actions)
    with pytest.raises(ValueError, match="Stale"):
        assess_d2(s.actions, replace(n, paired_digest="stale"), today=TODAY)
    from frp_master_connection.application.hyb1_review import ComparisonRow

    row = ComparisonRow(
        "X",
        "UNKNOWN",
        "bad",
        ActionBasis.LRFD,
        Decimal(".1"),
        "PASS",
        "D/R",
        "R",
        "NATIVE",
        "UNCHANGED_NATIVE_ASCE",
    )
    with pytest.raises(ValueError, match="original LRFD"):
        assess_d2(s.actions, replace(n, rows=(row,)), today=TODAY)
    a = synthetic().actions
    row = replace(row, case_id=a.lrfd[0].case_id, case_digest=a.lrfd[0].digest)
    with pytest.raises(ValueError, match="Duplicate"):
        assess_d2(a, replace(empty_native(a), rows=(row, row)), today=TODAY)
    red = assess_d2(a, replace(empty_native(a), status="RED"), today=TODAY)
    assert red.evaluated_outcome == "FAIL"
    assert red.tone == "red"
    assert not SourceConditions(temperature_f=Decimal(135)).matched
