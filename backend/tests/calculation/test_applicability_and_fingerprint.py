"""First-slice applicability/readiness and canonical fingerprint tests."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from enum import Enum

import pytest

from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    CalculationFingerprintInput,
    CalculationReadinessStatus,
    CodeGeometryValidation,
    DemandDistributionStatus,
    DemandSourceKind,
    EffectiveWidthMappingStatus,
    EndUseFactors,
    FastenerSnapshot,
    FingerprintEnvelope,
    FRPPropertyKind,
    GeometryToCodeMapping,
    LapConfiguration,
    LayerLoadingSense,
    LayerPlanningInput,
    LimitState,
    MaterialDirectionFamily,
    MaterialPropertySnapshot,
    NumericalComparison,
    PhysicalQuantity,
    PlannedCheck,
    PublishedCodeUnitBasis,
    QualificationStatus,
    ResolvedSingleBoltDemand,
    SingleBoltPlanningInput,
    SingleBoltPlanningResult,
    SourceClassification,
    SuppliedNumericalFixtureResult,
    ThreadStatus,
    ThreadStatusAssignment,
    Unit,
    UnorderedFingerprintCollection,
    WasherGeometry,
    asce_74_23_chapter_8_source,
    calculation_fingerprint,
    canonical_fingerprint_json,
    create_lap_factor_plan,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_single_bolt_geometry_factor_plan,
    create_standard_hole,
    create_synthetic_fastener_snapshot,
    plan_single_bolt_checks,
    resolve_geometry_to_code_mapping,
    select_time_effect_factor,
)
from frp_master_connection.calculation.geometry_mapping import GeometryToCodeMappingRequest
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.domain import PositionVector3D, PrincipalAxisFamily
from frp_master_connection.geometry import GLOBAL_FRAME, Vector3D
from tests.c3_fixtures import build_c3_case

HASH = "a" * 64


def _mapping(*, angle: float = 0.0, offset: float = 0.0) -> GeometryToCodeMapping:
    from math import cos, radians, sin

    case = build_c3_case(pultruded_frp=True)
    group = case.resolved_bolt_group
    if offset:
        from frp_master_connection.geometry import resolve_bolt_group_geometry

        group = resolve_bolt_group_geometry(
            case.basis,
            replace(case.bolt_specification, origin_z=offset),
        )
    layer = group.paths[0].layers[0]
    x_axis = layer.physical_element.global_frame.x_axis
    y_axis = layer.physical_element.global_frame.y_axis
    force = Vector3D(
        x_axis.x * cos(radians(angle)) + y_axis.x * sin(radians(angle)),
        x_axis.y * cos(radians(angle)) + y_axis.y * sin(radians(angle)),
        x_axis.z * cos(radians(angle)) + y_axis.z * sin(radians(angle)),
    )
    return resolve_geometry_to_code_mapping(
        GeometryToCodeMappingRequest(
            group,
            "bolt-1",
            "member-layer",
            PhysicalQuantity.of("0.5", Unit.MM),
            force,
            PrincipalAxisFamily.X,
            Unit.MM,
        )
    )


def _demand(
    *,
    in_plane: float = 3.0,
    axial: str = "0",
    prying: str = "0",
    sense: LayerLoadingSense = LayerLoadingSense.TENSION,
    source_kind: DemandSourceKind = DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND,
    factored: bool = True,
) -> ResolvedSingleBoltDemand:
    distribution = {
        DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND: (
            DemandDistributionStatus.EXPLICITLY_RESOLVED
        ),
        DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED: (DemandDistributionStatus.UNRESOLVED),
        DemandSourceKind.EXTERNAL_APPROVED_METHOD: (
            DemandDistributionStatus.EXTERNAL_METHOD_APPROVED
        ),
    }[source_kind]
    return ResolvedSingleBoltDemand(
        "demand-1",
        "LC-1",
        "member-1",
        "action-1",
        source_kind,
        factored,
        "GLOBAL",
        GLOBAL_FRAME,
        "point-1",
        PositionVector3D(0.0, 0.0, 0.0),
        Vector3D(0.0, 0.0, in_plane),
        Unit.KIP,
        PhysicalQuantity.of(axial, Unit.KIP),
        PhysicalQuantity.of(prying, Unit.KIP),
        sense,
        ("explicit source",),
        distribution,
    )


def _planning_input(
    *,
    mapping: GeometryToCodeMapping | None = None,
    demand: ResolvedSingleBoltDemand | None = None,
    fastener: FastenerSnapshot | None = None,
    washer: WasherGeometry | None = None,
    material: MaterialPropertySnapshot | None = None,
    geometry_status: CalculationReadinessStatus = CalculationReadinessStatus.READY,
    qualification: bool = False,
    potential_return: bool = False,
) -> SingleBoltPlanningInput:
    selected_mapping = mapping or _mapping()
    selected_washer = washer or WasherGeometry(
        PhysicalQuantity.of("1", Unit.IN),
        PhysicalQuantity.of("0.051", Unit.IN),
        True,
        True,
    )
    return SingleBoltPlanningInput(
        connection_id="connection-1",
        bolt_id="bolt-1",
        demand=demand or _demand(),
        layers=(
            LayerPlanningInput(
                selected_mapping,
                CodeGeometryValidation(geometry_status, ()),
                ThreadStatus.EXCLUDED,
                potential_return,
            ),
        ),
        material=material or create_locked_ice_material_snapshot(),
        fastener=fastener or create_locked_f593_fastener_snapshot(),
        washer=selected_washer,
        time_effect=select_time_effect_factor(TimeEffectCategory.OTHER_LIVE),
        end_use_factors=EndUseFactors(
            Decimal(1),
            Decimal(1),
            Decimal(1),
            "ASCE/SEI 74-23 Section 2.4.4",
            ("explicit unity fixture",),
        ),
        lap_factor=create_lap_factor_plan(LapConfiguration.DOUBLE_LAP),
        geometry_factor=create_single_bolt_geometry_factor_plan(),
        input_fingerprint=HASH,
        whole_connection_requires_section_2_3_2=qualification,
    )


def _by_limit(
    result: SingleBoltPlanningResult,
    limit_state: LimitState,
) -> tuple[PlannedCheck, ...]:
    return tuple(check for check in result.checks if check.limit_state is limit_state)


def test_p1_readiness_is_nonexecuting_and_engineering_review_required() -> None:
    result = plan_single_bolt_checks(_planning_input())
    assert len(result.checks) == 8
    assert all(
        check.numerical_comparison is NumericalComparison.NOT_EVALUATED for check in result.checks
    )
    assert _by_limit(result, LimitState.BOLT_SHEAR)[0].readiness_status is (
        CalculationReadinessStatus.SOURCE_DATA_PENDING
    )
    assert not _by_limit(result, LimitState.BOLT_SHEAR)[0].required
    assert _by_limit(result, LimitState.BOLT_TENSION)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    assert _by_limit(result, LimitState.PULL_THROUGH)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    for state in (
        LimitState.PIN_BEARING,
        LimitState.NET_SECTION_TENSION,
        LimitState.SHEAR_OUT,
        LimitState.CLEAVAGE,
    ):
        check = _by_limit(result, state)[0]
        assert check.readiness_status is CalculationReadinessStatus.READY
        assert QualificationStatus.ENGINEERING_REVIEW_REQUIRED in check.qualification_flags
    assert result.aggregate_status is AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED


def test_pull_through_activation_requires_explicit_demand_washer_and_material() -> None:
    active = plan_single_bolt_checks(_planning_input(demand=_demand(axial="0.5")))
    pull = _by_limit(active, LimitState.PULL_THROUGH)[0]
    assert pull.readiness_status is CalculationReadinessStatus.READY
    assert not any(metadata.startswith("lap:") for metadata in pull.factor_metadata)
    missing_washer_input = _planning_input(demand=_demand(prying="0.25"))
    missing_washer_input = replace(missing_washer_input, washer=None)
    missing_washer = plan_single_bolt_checks(missing_washer_input)
    assert _by_limit(missing_washer, LimitState.PULL_THROUGH)[0].readiness_status is (
        CalculationReadinessStatus.INCOMPLETE_INPUT
    )
    material = create_locked_ice_material_snapshot()
    filtered = tuple(
        entry for entry in material.properties if entry.kind is not FRPPropertyKind.FSH_INT
    )
    missing_material = replace(
        material,
        properties=filtered,
        explicitly_missing=tuple(
            sorted(
                (*material.explicitly_missing, FRPPropertyKind.FSH_INT),
                key=lambda kind: kind.value,
            )
        ),
    )
    incomplete = plan_single_bolt_checks(
        _planning_input(demand=_demand(axial="0.5"), material=missing_material)
    )
    assert _by_limit(incomplete, LimitState.PULL_THROUGH)[0].readiness_status is (
        CalculationReadinessStatus.INCOMPLETE_INPUT
    )


def test_p2b_directional_selection_cleavage_and_known_fail_precedence() -> None:
    mapping = _mapping(angle=45.0)
    fixture_failure = (SuppliedNumericalFixtureResult("P2B:net", NumericalComparison.FAIL),)
    result = plan_single_bolt_checks(
        _planning_input(mapping=mapping),
        supplied_fixture_results=fixture_failure,
    )
    bearing = _by_limit(result, LimitState.PIN_BEARING)[0]
    net = _by_limit(result, LimitState.NET_SECTION_TENSION)[0]
    shear = _by_limit(result, LimitState.SHEAR_OUT)[0]
    cleavage = _by_limit(result, LimitState.CLEAVAGE)[0]
    assert bearing.required_property_kind is FRPPropertyKind.FBR_T
    assert net.required_property_kind is FRPPropertyKind.FT_T
    assert shear.readiness_status is CalculationReadinessStatus.READY
    assert cleavage.readiness_status is CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
    assert result.aggregate_status is AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK


def test_exact_90_and_compression_make_cleavage_or_tension_checks_not_applicable() -> None:
    transverse = plan_single_bolt_checks(_planning_input(mapping=_mapping(angle=90.0)))
    assert _by_limit(transverse, LimitState.PIN_BEARING)[0].required_property_kind is (
        FRPPropertyKind.FBR_T
    )
    assert _by_limit(transverse, LimitState.NET_SECTION_TENSION)[0].required_property_kind is (
        FRPPropertyKind.FT_T
    )
    assert _by_limit(transverse, LimitState.CLEAVAGE)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    compression = plan_single_bolt_checks(
        _planning_input(demand=_demand(sense=LayerLoadingSense.COMPRESSION))
    )
    assert _by_limit(compression, LimitState.PIN_BEARING)[0].readiness_status is (
        CalculationReadinessStatus.READY
    )
    assert _by_limit(compression, LimitState.SHEAR_OUT)[0].readiness_status is (
        CalculationReadinessStatus.READY
    )
    assert _by_limit(compression, LimitState.NET_SECTION_TENSION)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    assert _by_limit(compression, LimitState.CLEAVAGE)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )


def test_b1_explicit_fnt_makes_applicable_bolt_plans_ready_without_calculation() -> None:
    synthetic = replace(
        create_synthetic_fastener_snapshot(
            id="B1_SYNTHETIC",
            fnt=PhysicalQuantity.of("100", Unit.KSI),
        ),
        shear_plane_thread_statuses=(
            ThreadStatusAssignment("shear-plane-1", ThreadStatus.EXCLUDED),
        ),
        number_of_shear_planes=1,
    )
    result = plan_single_bolt_checks(_planning_input(demand=_demand(axial="2"), fastener=synthetic))
    for state in (
        LimitState.BOLT_TENSION,
        LimitState.BOLT_SHEAR,
        LimitState.BOLT_COMBINED_TENSION_SHEAR,
    ):
        check = _by_limit(result, state)[0]
        assert check.readiness_status is CalculationReadinessStatus.READY
        assert check.required
        assert check.numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert create_locked_f593_fastener_snapshot().fnt is None


def test_undistributed_demand_and_j1_whole_connection_qualification_fail_closed() -> None:
    undistributed = plan_single_bolt_checks(
        _planning_input(
            demand=_demand(source_kind=DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED)
        )
    )
    assert undistributed.aggregate_status is (
        AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    )
    resolved_j1 = plan_single_bolt_checks(_planning_input(qualification=True))
    assert resolved_j1.whole_connection_status is (
        CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert resolved_j1.aggregate_status is (
        AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    positive_undistributed = plan_single_bolt_checks(
        _planning_input(
            demand=_demand(
                axial="0.5",
                source_kind=DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED,
            )
        )
    )
    assert _by_limit(
        positive_undistributed,
        LimitState.PULL_THROUGH,
    )[0].readiness_status is (
        CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED
    )
    invalid_pull = plan_single_bolt_checks(
        _planning_input(
            demand=_demand(axial="0.5"),
            geometry_status=CalculationReadinessStatus.INVALID_GEOMETRY,
        )
    )
    assert _by_limit(invalid_pull, LimitState.PULL_THROUGH)[0].readiness_status is (
        CalculationReadinessStatus.INVALID_GEOMETRY
    )


def test_geometry_missing_property_zero_demand_and_return_exemption_paths() -> None:
    invalid = plan_single_bolt_checks(
        _planning_input(geometry_status=CalculationReadinessStatus.INVALID_GEOMETRY)
    )
    assert invalid.aggregate_status is AggregatePlanningStatus.INVALID_GEOMETRY
    not_factored = plan_single_bolt_checks(_planning_input(demand=_demand(factored=False)))
    assert not_factored.aggregate_status is AggregatePlanningStatus.INCOMPLETE_INPUT
    zero = plan_single_bolt_checks(_planning_input(demand=_demand(in_plane=0.0)))
    assert _by_limit(zero, LimitState.PIN_BEARING)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    assert _by_limit(zero, LimitState.SHEAR_OUT)[0].readiness_status is (
        CalculationReadinessStatus.NOT_APPLICABLE
    )
    return_case = plan_single_bolt_checks(_planning_input(potential_return=True))
    shear = _by_limit(return_case, LimitState.SHEAR_OUT)[0]
    assert any("not credited" in warning for warning in shear.warnings)
    unsupported_width = replace(
        _mapping(offset=0.5),
        effective_width_status=EffectiveWidthMappingStatus.CALCULATION_NOT_SUPPORTED,
        effective_e3=None,
        effective_e4=None,
        effective_width=None,
    )
    unsupported = plan_single_bolt_checks(_planning_input(mapping=unsupported_width))
    assert _by_limit(unsupported, LimitState.NET_SECTION_TENSION)[0].readiness_status is (
        CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED
    )
    material = create_locked_ice_material_snapshot()
    filtered = tuple(
        entry for entry in material.properties if entry.kind is not FRPPropertyKind.FBR_L
    )
    missing_bearing = replace(
        material,
        properties=filtered,
        explicitly_missing=tuple(
            sorted(
                (*material.explicitly_missing, FRPPropertyKind.FBR_L),
                key=lambda kind: kind.value,
            )
        ),
    )
    missing = plan_single_bolt_checks(_planning_input(material=missing_bearing))
    assert _by_limit(missing, LimitState.PIN_BEARING)[0].readiness_status is (
        CalculationReadinessStatus.INCOMPLETE_INPUT
    )
    undeclared_properties = tuple(
        entry
        for entry in material.properties
        if entry.kind not in {FRPPropertyKind.FT_L, FRPPropertyKind.FSH_LT}
    )
    undeclared = replace(material, properties=undeclared_properties)
    undeclared_result = plan_single_bolt_checks(_planning_input(material=undeclared))
    assert (
        _by_limit(
            undeclared_result,
            LimitState.NET_SECTION_TENSION,
        )[0].readiness_status
        is CalculationReadinessStatus.INCOMPLETE_INPUT
    )
    assert (
        _by_limit(
            undeclared_result,
            LimitState.SHEAR_OUT,
        )[0].readiness_status
        is CalculationReadinessStatus.INCOMPLETE_INPUT
    )
    assert (
        _by_limit(
            undeclared_result,
            LimitState.CLEAVAGE,
        )[0].readiness_status
        is CalculationReadinessStatus.INCOMPLETE_INPUT
    )


def test_planning_input_contracts_require_exact_immutable_layer_identity() -> None:
    valid = _planning_input()
    with pytest.raises(ValueError, match="identities must be nonempty"):
        replace(valid, connection_id="")
    with pytest.raises(ValueError, match="at least one"):
        replace(valid, layers=())
    with pytest.raises(ValueError, match="only once"):
        replace(valid, layers=(valid.layers[0], valid.layers[0]))
    with pytest.raises(TypeError, match="GeometryToCodeMapping"):
        replace(valid.layers[0], mapping=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="CodeGeometryValidation"):
        replace(valid.layers[0], geometry_validation=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ThreadStatus"):
        replace(valid.layers[0], bearing_thread_status="EXCLUDED")  # type: ignore[arg-type]


def _fingerprint_input(
    *,
    physical_hole: PhysicalQuantity | None = None,
    source_basis: PublishedCodeUnitBasis = PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    material: MaterialPropertySnapshot | None = None,
    fastener: FastenerSnapshot | None = None,
    demand: ResolvedSingleBoltDemand | None = None,
) -> CalculationFingerprintInput:
    return CalculationFingerprintInput(
        standard="ASCE/SEI 74-23",
        edition="2023",
        errata="Erratum 1:2026-01-13:CH8_UNAFFECTED",
        interpretation_ids=("TRANSVERSE_ENDPOINT_INCLUDED",),
        project_schema_version="0.1.0-draft",
        calculation_contract_version="2.1A-RC2",
        calculation_engine_version="not-implemented",
        material_snapshot=material or create_locked_ice_material_snapshot(),
        fastener_snapshot=fastener or create_locked_f593_fastener_snapshot(),
        physical_geometry={
            "id": "layer-1",
            "hole": physical_hole or PhysicalQuantity.of("0.563", Unit.IN),
            "thickness": PhysicalQuantity.of("0.375", Unit.IN),
        },
        code_variable_mapping={
            "e1": PhysicalQuantity.of("2", Unit.IN),
            "direction": MaterialDirectionFamily.LONGITUDINAL,
        },
        demand=demand or _demand(),
        factor_selections={"lambda": Decimal("0.8"), "CM": Decimal(1)},
        lap_configuration=LapConfiguration.DOUBLE_LAP,
        thread_statuses=(ThreadStatus.EXCLUDED,),
        published_code_unit_bases=(source_basis,),
        readiness_decisions=(CalculationReadinessStatus.READY,),
    )


def test_fingerprint_is_canonical_display_independent_and_deterministic() -> None:
    engineering = _fingerprint_input()
    first = FingerprintEnvelope(
        engineering,
        display_unit_profile="US",
        display_rounding="0.001",
        camera={"azimuth": 45.0},
        color="blue",
        visibility=True,
        selected_ui_tab="results",
        project_owner="owner-a",
        billing="paid",
    )
    second = FingerprintEnvelope(
        engineering,
        display_unit_profile="SI",
        display_rounding="1",
        camera={"azimuth": 0.0},
        color="red",
        visibility=False,
        selected_ui_tab="geometry",
        project_owner="owner-b",
        billing="trial",
    )
    assert calculation_fingerprint(first) == calculation_fingerprint(second)
    assert calculation_fingerprint(engineering) == calculation_fingerprint(_fingerprint_input())
    canonical = canonical_fingerprint_json(engineering)
    assert '"value":"14.3002"' in canonical
    assert ":0.563" not in canonical
    assert "not-implemented" in canonical


def test_fingerprint_physical_and_source_changes_are_visible_but_labels_are_not() -> None:
    base = _fingerprint_input()
    base_hash = calculation_fingerprint(base)
    exact_display = _fingerprint_input(physical_hole=PhysicalQuantity.of("14.3002", Unit.MM))
    assert calculation_fingerprint(exact_display) == base_hash
    si_source = _fingerprint_input(
        physical_hole=PhysicalQuantity.of("14.3", Unit.MM),
        source_basis=PublishedCodeUnitBasis.SI_PRINTED,
    )
    assert calculation_fingerprint(si_source) != base_hash
    changed_geometry = {
        "id": "layer-1",
        "hole": PhysicalQuantity.of("0.563", Unit.IN),
        "thickness": PhysicalQuantity.of("0.5", Unit.IN),
    }
    assert calculation_fingerprint(replace(base, physical_geometry=changed_geometry)) != base_hash
    material = replace(create_locked_ice_material_snapshot(), display_name="Localized label")
    assert calculation_fingerprint(_fingerprint_input(material=material)) == base_hash
    changed_basis = replace(
        material,
        basis=SourceClassification.MANUFACTURER_NOMINAL,
    )
    assert calculation_fingerprint(_fingerprint_input(material=changed_basis)) != base_hash
    fastener_label = replace(create_locked_f593_fastener_snapshot(), display_name="Localized")
    assert calculation_fingerprint(_fingerprint_input(fastener=fastener_label)) == base_hash
    synthetic = create_synthetic_fastener_snapshot(
        id="custom",
        fnt=PhysicalQuantity.of("100", Unit.KSI),
    )
    assert calculation_fingerprint(_fingerprint_input(fastener=synthetic)) != base_hash
    changed_demand = replace(
        _demand(),
        in_plane_force_vector=Vector3D(0.0, 0.0, 4.0),
    )
    assert calculation_fingerprint(_fingerprint_input(demand=changed_demand)) != base_hash


def test_fingerprint_ordered_and_unordered_collection_rules() -> None:
    base = _fingerprint_input()
    unordered_a = UnorderedFingerprintCollection(
        ({"id": "b", "v": Decimal(2)}, {"id": "a", "v": Decimal(1)})
    )
    unordered_b = UnorderedFingerprintCollection(
        ({"id": "a", "v": Decimal(1)}, {"id": "b", "v": Decimal(2)})
    )
    assert calculation_fingerprint(replace(base, physical_geometry=unordered_a)) == (
        calculation_fingerprint(replace(base, physical_geometry=unordered_b))
    )
    ordered_a = replace(base, readiness_decisions=("first", "second"))
    ordered_b = replace(base, readiness_decisions=("second", "first"))
    assert calculation_fingerprint(ordered_a) != calculation_fingerprint(ordered_b)
    object_items = UnorderedFingerprintCollection(
        (
            replace(base.material_snapshot, id="b"),
            replace(base.material_snapshot, id="a"),
        )
    )
    assert '"id":"a"' in canonical_fingerprint_json(replace(base, physical_geometry=object_items))
    with pytest.raises(ValueError, match="requires a nonempty string ID"):
        UnorderedFingerprintCollection(({"value": "missing"},))
    with pytest.raises(ValueError, match="must be unique"):
        UnorderedFingerprintCollection(({"id": "same"}, {"id": "same"}))
    with pytest.raises(TypeError, match="immutable tuple"):
        UnorderedFingerprintCollection([])  # type: ignore[arg-type]


def test_fingerprint_rejects_raw_floats_invalid_keys_and_unsupported_values() -> None:
    base = _fingerprint_input()
    with pytest.raises(TypeError, match="Raw floating-point"):
        calculation_fingerprint(replace(base, physical_geometry={"x": 1.0}))
    with pytest.raises(TypeError, match="keys must be strings"):
        calculation_fingerprint(replace(base, physical_geometry={1: "x"}))
    with pytest.raises(TypeError, match="Unsupported fingerprint value"):
        calculation_fingerprint(replace(base, physical_geometry=object()))
    with pytest.raises(TypeError, match="CalculationFingerprintInput or envelope"):
        canonical_fingerprint_json(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be nonempty"):
        replace(base, standard="")
    negative_zero = replace(base, factor_selections={"factor": Decimal("-0.00")})
    assert '"factor":"0"' in canonical_fingerprint_json(negative_zero)


def test_fingerprint_canonicalizer_covers_dates_frames_vectors_lists_ints_and_enum_guard() -> None:
    base = _fingerprint_input()
    source = asce_74_23_chapter_8_source(section="8.3.2.3")
    payload = {
        "active": True,
        "absent": None,
        "count": 1,
        "date": date(2026, 1, 13),
        "frame": GLOBAL_FRAME,
        "vector": Vector3D(1.0, 0.0, 0.0),
        "sequence": [Decimal("1.0"), "two"],
        "source": source,
    }
    rendered = canonical_fingerprint_json(replace(base, physical_geometry=payload))
    assert '"count":"1"' in rendered
    assert '"date":"2026-01-13"' in rendered
    assert '"sequence":["1","two"]' in rendered
    assert '"chapter_affected_by_errata":false' in rendered

    class InvalidFingerprintEnum(Enum):
        VALUE = 1

    class ValidFingerprintEnum(Enum):
        VALUE = "VALUE"

    assert '"enum":"VALUE"' in canonical_fingerprint_json(
        replace(base, physical_geometry={"enum": ValidFingerprintEnum.VALUE})
    )
    with pytest.raises(TypeError, match="enum values must be stable strings"):
        calculation_fingerprint(
            replace(base, physical_geometry={"enum": InvalidFingerprintEnum.VALUE})
        )
    with pytest.raises(TypeError, match="keys must be strings"):
        calculation_fingerprint(replace(base, physical_geometry={"valid": "first", 1: "invalid"}))


def test_standard_hole_source_basis_is_fingerprint_relevant_but_display_conversion_is_not() -> None:
    us = create_standard_hole(
        PhysicalQuantity.of("0.500", Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    same_physical = _fingerprint_input(physical_hole=us.hole_diameter.to(Unit.MM))
    assert calculation_fingerprint(same_physical) == calculation_fingerprint(
        _fingerprint_input(physical_hole=us.hole_diameter)
    )
