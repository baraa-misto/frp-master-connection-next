"""Source, material, fastener, and hardware snapshot tests."""

from dataclasses import replace
from datetime import date

import pytest

from frp_master_connection.calculation import (
    ASCE_74_23_EDITION,
    ASCE_74_23_ERRATUM,
    ASCE_74_23_ERRATUM_EFFECTIVE_DATE,
    ASCE_74_23_STANDARD_NAME,
    TRANSVERSE_ENDPOINT_INTERPRETATION_ID,
    CalculationSourceSnapshot,
    FRPPropertyEntry,
    FRPPropertyKind,
    MaterialPropertySnapshot,
    PhysicalQuantity,
    PropertyBehavior,
    QualificationStatus,
    SourceClassification,
    ThreadStatus,
    ThreadStatusAssignment,
    Unit,
    WasherGeometry,
    asce_74_23_chapter_8_source,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_synthetic_fastener_snapshot,
)


def _entry(kind: FRPPropertyKind = FRPPropertyKind.FT_L) -> FRPPropertyEntry:
    return FRPPropertyEntry(
        kind,
        PhysicalQuantity.of("1", Unit.KSI),
        PropertyBehavior.LONGITUDINAL,
        SourceClassification.USER_DEFINED,
        QualificationStatus.DEVELOPMENT_ONLY,
        "test source",
        "1",
    )


def test_canonical_asce_chapter_8_source_and_interpretation_trace() -> None:
    ordinary = asce_74_23_chapter_8_source(section="8.3.2.3", equation_reference="8-5/8-6")
    interpreted = asce_74_23_chapter_8_source(
        section="8.3.2.3",
        equation_reference="8-6",
        interpretation_id=TRANSVERSE_ENDPOINT_INTERPRETATION_ID,
    )
    assert ordinary.standard_name == ASCE_74_23_STANDARD_NAME
    assert ordinary.edition == ASCE_74_23_EDITION
    assert ordinary.errata_identifier == ASCE_74_23_ERRATUM
    assert ordinary.errata_effective_date == ASCE_74_23_ERRATUM_EFFECTIVE_DATE
    assert not ordinary.chapter_affected_by_errata
    assert ordinary.engineer_approval_authority is None
    assert interpreted.engineer_approval_authority == "Baraa Misto"
    assert interpreted.engineer_approval_date == date(2026, 8, 8)


def test_source_snapshot_rejects_incomplete_or_inconsistent_metadata() -> None:
    source = asce_74_23_chapter_8_source(section="8.1")
    with pytest.raises(ValueError, match="nonempty"):
        replace(source, standard_name=" ")
    with pytest.raises(TypeError, match="must be a date"):
        replace(source, errata_effective_date="2026-01-13")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="SourceClassification"):
        replace(source, source_classification="CODE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must appear together"):
        replace(source, engineer_approval_authority="Engineer")
    with pytest.raises(ValueError, match="must appear together"):
        replace(source, engineer_approval_date=date(2026, 8, 8))


def test_source_and_qualification_vocabularies_are_complete() -> None:
    assert len(SourceClassification) == 7
    assert len(QualificationStatus) == 5
    assert CalculationSourceSnapshot is not None


def test_locked_ice_material_has_exact_values_explicit_fc_t_absence_and_no_fallback() -> None:
    material = create_locked_ice_material_snapshot()
    expected = {
        FRPPropertyKind.FT_L: ("33", Unit.KSI),
        FRPPropertyKind.FT_T: ("7.5", Unit.KSI),
        FRPPropertyKind.ET_L: ("3000", Unit.KSI),
        FRPPropertyKind.ET_T: ("800", Unit.KSI),
        FRPPropertyKind.FC_L: ("33", Unit.KSI),
        FRPPropertyKind.EC_L: ("3000", Unit.KSI),
        FRPPropertyKind.EC_T: ("1000", Unit.KSI),
        FRPPropertyKind.FSH_LT: ("8", Unit.KSI),
        FRPPropertyKind.G_LT: ("420", Unit.KSI),
        FRPPropertyKind.FSH_INT: ("4.5", Unit.KSI),
        FRPPropertyKind.FBR_L: ("30", Unit.KSI),
        FRPPropertyKind.FBR_T: ("18", Unit.KSI),
        FRPPropertyKind.PULL_THROUGH_3_8: ("0.65", Unit.KIP),
        FRPPropertyKind.PULL_THROUGH_1_2: ("0.90", Unit.KIP),
        FRPPropertyKind.PULL_THROUGH_3_4: ("1.25", Unit.KIP),
        FRPPropertyKind.NU_LT: ("0.30", Unit.ONE),
    }
    assert material.id == "ICE_LOCKED_PULTRUDED_FRP"
    assert material.locked
    assert material.basis is SourceClassification.ENGINEER_APPROVED_DEVELOPMENT
    assert material.qualification_statuses == (
        QualificationStatus.DEVELOPMENT_ONLY,
        QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
    )
    assert material.explicitly_missing == (FRPPropertyKind.FC_T,)
    assert material.lookup(FRPPropertyKind.FC_T) is None
    for kind, (value, unit) in expected.items():
        entry = material.lookup(kind)
        assert entry is not None
        assert entry.value == PhysicalQuantity.of(value, unit)
    for kind in (
        FRPPropertyKind.PULL_THROUGH_3_8,
        FRPPropertyKind.PULL_THROUGH_1_2,
        FRPPropertyKind.PULL_THROUGH_3_4,
    ):
        entry = material.lookup(kind)
        assert entry is not None
        assert not entry.use_in_chapter_8_equations
    assert create_locked_ice_material_snapshot() == material


def test_property_entry_validates_dimension_source_and_immutable_metadata() -> None:
    with pytest.raises(ValueError, match="must have dimension FORCE"):
        FRPPropertyEntry(
            FRPPropertyKind.PULL_THROUGH_1_2,
            PhysicalQuantity.of("1", Unit.KSI),
            PropertyBehavior.DISCRETE_PULL_THROUGH,
            SourceClassification.USER_DEFINED,
            QualificationStatus.DEVELOPMENT_ONLY,
            "source",
            "1",
        )
    with pytest.raises(ValueError, match="must have dimension DIMENSIONLESS"):
        replace(_entry(), kind=FRPPropertyKind.NU_LT)
    with pytest.raises(ValueError, match="must have dimension STRESS"):
        replace(_entry(), value=PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="must be nonempty"):
        replace(_entry(), source_document="")
    with pytest.raises(TypeError, match="must be tuples"):
        replace(_entry(), engineer_notes=[])  # type: ignore[arg-type]


def test_material_snapshot_rejects_duplicates_overlap_and_nondeterministic_order() -> None:
    entry = _entry()
    valid = MaterialPropertySnapshot(
        "custom",
        "Custom",
        False,
        SourceClassification.USER_DEFINED,
        (QualificationStatus.DEVELOPMENT_ONLY,),
        (entry,),
        (FRPPropertyKind.FC_T,),
    )
    assert valid.lookup(FRPPropertyKind.FT_L) is entry
    with pytest.raises(KeyError, match="not declared"):
        valid.lookup(FRPPropertyKind.ET_L)
    with pytest.raises(ValueError, match="identity"):
        replace(valid, id="")
    with pytest.raises(TypeError, match="must be tuples"):
        replace(valid, properties=[entry])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be unique"):
        replace(valid, properties=(entry, entry))
    with pytest.raises(ValueError, match="must be unique"):
        replace(valid, explicitly_missing=(FRPPropertyKind.FC_T, FRPPropertyKind.FC_T))
    with pytest.raises(ValueError, match="present and explicitly missing"):
        replace(valid, explicitly_missing=(FRPPropertyKind.FT_L,))
    unsorted_entry = replace(entry, kind=FRPPropertyKind.EC_L)
    with pytest.raises(ValueError, match="deterministic kind order"):
        replace(valid, properties=(entry, unsorted_entry), explicitly_missing=())
    with pytest.raises(ValueError, match="deterministic order"):
        replace(
            valid,
            explicitly_missing=(FRPPropertyKind.FT_T, FRPPropertyKind.FC_T),
        )


def test_locked_f593_preset_retains_source_pending_fnt_without_substitution() -> None:
    fastener = create_locked_f593_fastener_snapshot()
    assert fastener.id == "ASTM_F593_17_GROUP_2_316_316L"
    assert fastener.bolt_specification == "ASTM F593-17"
    assert fastener.alloy_group == "2"
    assert fastener.alloys == ("316", "316L")
    assert fastener.condition == "COLD_WORKED_FASTENER_BASIS"
    assert fastener.nut_specification == "ASTM F594-15"
    assert fastener.installation_condition == "SNUG_TIGHT"
    assert fastener.diameter_min == PhysicalQuantity.of("0.375", Unit.IN)
    assert fastener.diameter_max == PhysicalQuantity.of("1.0", Unit.IN)
    assert fastener.fnt is None
    assert fastener.fnt_source_classification is SourceClassification.SOURCE_PENDING
    assert fastener.fnt_qualification_status is QualificationStatus.SOURCE_PENDING
    assert "No generic tensile strength" in fastener.source_notes[0]


def test_synthetic_explicit_fnt_is_separate_and_not_f593_qualified() -> None:
    locked = create_locked_f593_fastener_snapshot()
    synthetic = create_synthetic_fastener_snapshot(
        id="B1_SYNTHETIC",
        fnt=PhysicalQuantity.of("100", Unit.KSI),
    )
    assert synthetic.fnt == PhysicalQuantity.of("100", Unit.KSI)
    assert synthetic.bolt_specification == "SYNTHETIC_NOT_ASTMF593_QUALIFIED"
    assert not synthetic.locked
    assert locked.fnt is None
    development = create_synthetic_fastener_snapshot(
        id="DEV",
        fnt=PhysicalQuantity.of("90", Unit.KSI),
        source_classification=SourceClassification.ENGINEER_APPROVED_DEVELOPMENT,
    )
    assert (
        development.fnt_source_classification is SourceClassification.ENGINEER_APPROVED_DEVELOPMENT
    )
    with pytest.raises(ValueError, match="user-defined or engineer-approved"):
        create_synthetic_fastener_snapshot(
            id="bad",
            fnt=PhysicalQuantity.of("100", Unit.KSI),
            source_classification=SourceClassification.QUALIFIED_TEST_DATA,
        )


def test_thread_assignments_and_washer_geometry_are_explicit_and_independent() -> None:
    shear = ThreadStatusAssignment("plane-1", ThreadStatus.EXCLUDED)
    bearing = ThreadStatusAssignment("layer-1", ThreadStatus.INCLUDED)
    washer = WasherGeometry(
        PhysicalQuantity.of("1.0", Unit.IN),
        PhysicalQuantity.of("0.051", Unit.IN),
        True,
        True,
    )
    fastener = replace(
        create_locked_f593_fastener_snapshot(),
        shear_plane_thread_statuses=(shear,),
        bearing_layer_thread_statuses=(bearing,),
        number_of_shear_planes=1,
        washer_geometry=washer,
    )
    assert fastener.shear_plane_thread_statuses[0].status is ThreadStatus.EXCLUDED
    assert fastener.bearing_layer_thread_statuses[0].status is ThreadStatus.INCLUDED
    with pytest.raises(ValueError, match="identity"):
        ThreadStatusAssignment("", ThreadStatus.INCLUDED)
    with pytest.raises(TypeError, match="ThreadStatus"):
        ThreadStatusAssignment("x", "INCLUDED")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be lengths"):
        WasherGeometry(
            PhysicalQuantity.of("1", Unit.N),
            PhysicalQuantity.of("1", Unit.MM),
            True,
            True,
        )
    with pytest.raises(ValueError, match="strictly positive"):
        WasherGeometry(
            PhysicalQuantity.of("1", Unit.IN),
            PhysicalQuantity.of("0", Unit.IN),
            True,
            True,
        )


def test_fastener_snapshot_fail_closed_validation_branches() -> None:
    fastener = create_locked_f593_fastener_snapshot()
    with pytest.raises(ValueError, match="must be nonempty"):
        replace(fastener, display_name="")
    with pytest.raises(ValueError, match="must be lengths"):
        replace(fastener, diameter_min=PhysicalQuantity.of("1", Unit.N))
    with pytest.raises(ValueError, match="minimum diameter must be positive"):
        replace(fastener, diameter_min=PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(ValueError, match="range must be ordered"):
        replace(
            fastener,
            diameter_min=PhysicalQuantity.of("2", Unit.IN),
            diameter_max=PhysicalQuantity.of("1", Unit.IN),
        )
    with pytest.raises(ValueError, match="Fnt must be a stress"):
        replace(
            fastener,
            fnt=PhysicalQuantity.of("1", Unit.KIP),
            fnt_source_classification=SourceClassification.USER_DEFINED,
        )
    with pytest.raises(TypeError, match="must be an integer"):
        replace(fastener, number_of_shear_planes=1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be nonnegative"):
        replace(fastener, number_of_shear_planes=-1)
    with pytest.raises(ValueError, match="requires a separate thread status"):
        replace(fastener, number_of_shear_planes=1)
    duplicate = ThreadStatusAssignment("same", ThreadStatus.INCLUDED)
    with pytest.raises(ValueError, match="must be unique"):
        replace(
            fastener,
            bearing_layer_thread_statuses=(duplicate, duplicate),
        )
    with pytest.raises(ValueError, match="SOURCE_PENDING"):
        replace(fastener, fnt_source_classification=SourceClassification.USER_DEFINED)
