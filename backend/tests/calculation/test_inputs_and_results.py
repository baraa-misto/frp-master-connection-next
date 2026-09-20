"""Factor, demand, status, check-plan, and aggregation contract tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.calculation import (
    AggregatePlanningStatus,
    ApplicabilityReasonCode,
    CalculationReadinessStatus,
    DemandDistributionStatus,
    DemandSourceKind,
    EndUseFactors,
    FinalResultAvailability,
    GeometryFactorPlan,
    LapConfiguration,
    LayerLoadingSense,
    LimitState,
    MaterialDirectionFamily,
    NumericalComparison,
    PhysicalQuantity,
    PlannedCheck,
    QualificationStatus,
    ResolvedSingleBoltDemand,
    SuppliedNumericalFixtureResult,
    TimeEffectCategory,
    Unit,
    aggregate_planning_status,
    create_lap_factor_plan,
    create_single_bolt_geometry_factor_plan,
    select_time_effect_factor,
)
from frp_master_connection.domain import PositionVector3D
from frp_master_connection.geometry import GLOBAL_FRAME, Vector3D

HASH = "0" * 64


def _demand(
    *,
    source_kind: DemandSourceKind = DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND,
    distribution: DemandDistributionStatus = DemandDistributionStatus.EXPLICITLY_RESOLVED,
) -> ResolvedSingleBoltDemand:
    return ResolvedSingleBoltDemand(
        id="demand-1",
        load_combination_id="LC-1",
        source_member_id="member-1",
        source_action_id="action-1",
        source_kind=source_kind,
        factored_action_confirmed=True,
        coordinate_frame_reference="GLOBAL",
        resolved_frame=GLOBAL_FRAME,
        source_reference_point_id="point-1",
        resolved_global_reference_point=PositionVector3D(1.0, 2.0, 3.0),
        in_plane_force_vector=Vector3D(3.0, 4.0, 0.0),
        force_vector_unit=Unit.KIP,
        bolt_axis_tensile_demand=PhysicalQuantity.of("0.5", Unit.KIP),
        externally_supplied_prying_demand=PhysicalQuantity.of("0", Unit.KIP),
        loading_sense=LayerLoadingSense.TENSION,
        provenance=("explicit per-bolt demand", "point retained"),
        distribution_status=distribution,
    )


def _check(
    status: CalculationReadinessStatus,
    *,
    check_id: str = "check-1",
    required: bool = True,
    flags: tuple[QualificationStatus, ...] = (),
) -> PlannedCheck:
    return PlannedCheck(
        check_id=check_id,
        limit_state=LimitState.PIN_BEARING,
        component_id="component-1",
        layer_id="layer-1",
        bolt_id="bolt-1",
        source_section="8.3.2.3",
        source_equation="8-5/8-6",
        readiness_status=status,
        numerical_comparison=NumericalComparison.NOT_EVALUATED,
        applicability_reason_codes=(
            ApplicabilityReasonCode.PHYSICAL_NUMERICAL_EVALUATION_NOT_AUTHORIZED,
        ),
        required_property_kind=None,
        selected_direction_family=MaterialDirectionFamily.LONGITUDINAL,
        theta_degrees=Decimal("0"),
        required_geometry_inputs=("d", "t"),
        factor_metadata=("not applied",),
        qualification_flags=flags,
        warnings=(),
        assumptions=(),
        unsupported_conditions=(),
        input_fingerprint=HASH,
        required=required,
    )


def test_time_effect_categories_have_exact_values_and_no_name_inference() -> None:
    expected = {
        TimeEffectCategory.DEAD_ONLY: "0.4",
        TimeEffectCategory.IMPACT: "1.0",
        TimeEffectCategory.STORAGE: "0.6",
        TimeEffectCategory.LONG_TERM_OPERATING: "0.4",
        TimeEffectCategory.OTHER_LIVE: "0.8",
        TimeEffectCategory.SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE: "0.75",
        TimeEffectCategory.WIND_TORNADO_SEISMIC: "1.0",
    }
    for category, value in expected.items():
        selected = select_time_effect_factor(category)
        assert selected.value == Decimal(value)
        assert selected.category is category
        assert selected.approved_override_id is None
    with pytest.raises(TypeError, match="TimeEffectCategory"):
        select_time_effect_factor("WIND")  # type: ignore[arg-type]


def test_time_effect_factor_requires_controlled_positive_sourced_selection() -> None:
    valid = select_time_effect_factor(TimeEffectCategory.OTHER_LIVE)
    with pytest.raises(TypeError, match="TimeEffectCategory"):
        replace(valid, category="OTHER")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="strictly positive"):
        replace(valid, value=Decimal(0))
    with pytest.raises(ValueError, match="source reference"):
        replace(valid, source_reference="")
    with pytest.raises(TypeError, match="notes"):
        replace(valid, notes=[])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires approved override"):
        replace(valid, value=Decimal("0.7"))
    override = replace(valid, value=Decimal("0.7"), approved_override_id="APPROVED-1")
    assert override.value == Decimal("0.7")


def test_end_use_factors_are_explicit_positive_and_approved() -> None:
    factors = EndUseFactors(
        "1.0",  # type: ignore[arg-type]
        Decimal("1"),
        Decimal(1),
        "ASCE/SEI 74-23 Section 2.4.4",
        ("Golden fixture explicit unity",),
    )
    assert (factors.cm, factors.ct, factors.cch) == (Decimal(1),) * 3
    with pytest.raises(ValueError, match="strictly positive"):
        replace(factors, cm=Decimal(0))
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(factors, approval_metadata=["approval"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="require source and approval"):
        replace(factors, approval_metadata=())


def test_lap_and_geometry_factor_plans_store_metadata_without_application() -> None:
    double = create_lap_factor_plan(LapConfiguration.DOUBLE_LAP)
    single = create_lap_factor_plan(LapConfiguration.SINGLE_LAP)
    assert double.applicable_in_plane_frp_factor == Decimal("1.0")
    assert single.applicable_in_plane_frp_factor == Decimal("0.60")
    assert not single.applies_to_metallic_bolt
    assert not single.applies_to_pull_through
    with pytest.raises(TypeError, match="LapConfiguration"):
        create_lap_factor_plan("SINGLE")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="configuration"):
        replace(single, configuration="SINGLE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="does not match"):
        replace(single, applicable_in_plane_frp_factor=Decimal(1))
    with pytest.raises(ValueError, match="excludes bolt"):
        replace(single, applies_to_metallic_bolt=True)
    geometry = create_single_bolt_geometry_factor_plan()
    assert geometry.pitch is None
    assert geometry.planning_value == Decimal("1.0")
    assert not geometry.applied_to_resistance
    with pytest.raises(TypeError, match="must be an integer"):
        GeometryFactorPlan(True, 1, None, Decimal(1))
    with pytest.raises(TypeError, match="must be an integer"):
        GeometryFactorPlan(1, 1.5, None, Decimal(1))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be positive"):
        GeometryFactorPlan(0, 1, None, Decimal(1))
    with pytest.raises(ValueError, match="pitch must be a length"):
        GeometryFactorPlan(2, 1, PhysicalQuantity.of("1", Unit.N), Decimal(1))
    with pytest.raises(ValueError, match="requires no pitch"):
        GeometryFactorPlan(1, 1, PhysicalQuantity.of("1", Unit.IN), Decimal(1))
    with pytest.raises(ValueError, match="cannot apply"):
        replace(geometry, applied_to_resistance=True)
    multi = GeometryFactorPlan(
        2,
        1,
        PhysicalQuantity.of("2", Unit.IN),
        Decimal("0.8"),
    )
    assert multi.pitch == PhysicalQuantity.of("2", Unit.IN)


def test_resolved_demand_derives_magnitude_and_retains_explicit_provenance() -> None:
    demand = _demand()
    assert demand.in_plane_force_magnitude == PhysicalQuantity.of("5.0", Unit.KIP)
    assert demand.bolt_axis_tensile_demand == PhysicalQuantity.of("0.5", Unit.KIP)
    assert demand.externally_supplied_prying_demand == PhysicalQuantity.of("0", Unit.KIP)
    assert demand.distribution_status is DemandDistributionStatus.EXPLICITLY_RESOLVED
    external = _demand(
        source_kind=DemandSourceKind.EXTERNAL_APPROVED_METHOD,
        distribution=DemandDistributionStatus.EXTERNAL_METHOD_APPROVED,
    )
    assert external.source_kind is DemandSourceKind.EXTERNAL_APPROVED_METHOD
    undistributed = _demand(
        source_kind=DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED,
        distribution=DemandDistributionStatus.UNRESOLVED,
    )
    assert undistributed.distribution_status is DemandDistributionStatus.UNRESOLVED


def test_resolved_demand_validation_fails_closed_for_every_required_field() -> None:
    demand = _demand()
    with pytest.raises(ValueError, match="must be nonempty"):
        replace(demand, id="")
    with pytest.raises(TypeError, match="CartesianFrame3D"):
        replace(demand, resolved_frame=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="PositionVector3D"):
        replace(demand, resolved_global_reference_point=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Vector3D"):
        replace(demand, in_plane_force_vector=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="DemandSourceKind"):
        replace(demand, source_kind="EXPLICIT")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be Boolean"):
        replace(demand, factored_action_confirmed=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="LayerLoadingSense"):
        replace(demand, loading_sense="TENSION")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="DemandDistributionStatus"):
        replace(demand, distribution_status="RESOLVED")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="force dimension"):
        replace(demand, force_vector_unit=Unit.MM)
    with pytest.raises(ValueError, match="must be forces"):
        replace(demand, bolt_axis_tensile_demand=PhysicalQuantity.of("1", Unit.IN))
    with pytest.raises(ValueError, match="must be nonnegative"):
        replace(demand, bolt_axis_tensile_demand=PhysicalQuantity.of("-1", Unit.KIP))
    with pytest.raises(ValueError, match="inconsistent"):
        replace(demand, distribution_status=DemandDistributionStatus.UNRESOLVED)
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(demand, provenance=["source"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="provenance is required"):
        replace(demand, provenance=())


def test_controlled_limit_state_readiness_availability_and_comparison_vocabularies() -> None:
    assert len(LimitState) == 8
    assert len(CalculationReadinessStatus) == 9
    assert len(FinalResultAvailability) == 10
    assert tuple(NumericalComparison) == (
        NumericalComparison.PASS,
        NumericalComparison.FAIL,
        NumericalComparison.NOT_EVALUATED,
    )
    assert str(CalculationReadinessStatus.READY.value) != str(NumericalComparison.PASS.value)


def test_planned_check_enforces_nonexecuting_physical_input_schema() -> None:
    check = _check(CalculationReadinessStatus.READY)
    assert check.numerical_comparison is NumericalComparison.NOT_EVALUATED
    with pytest.raises(ValueError, match="identities must be nonempty"):
        replace(check, check_id="")
    with pytest.raises(ValueError, match="source section"):
        replace(check, source_equation="")
    with pytest.raises(ValueError, match="must be NOT_EVALUATED"):
        replace(check, numerical_comparison=NumericalComparison.PASS)
    with pytest.raises(ValueError, match="inclusive range"):
        replace(check, theta_degrees=Decimal("91"))
    without_theta = replace(check, theta_degrees=None)
    assert without_theta.theta_degrees is None
    with pytest.raises(TypeError, match="immutable tuples"):
        replace(check, warnings=[])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(check, input_fingerprint="not-a-hash")
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(check, input_fingerprint="A" * 64)


def test_supplied_fixture_result_is_separate_from_physical_plans() -> None:
    result = SuppliedNumericalFixtureResult("fixture-check", NumericalComparison.FAIL)
    assert result.comparison is NumericalComparison.FAIL
    with pytest.raises(ValueError, match="identity"):
        replace(result, check_id="")
    with pytest.raises(ValueError, match="PASS or FAIL"):
        replace(result, comparison=NumericalComparison.NOT_EVALUATED)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CalculationReadinessStatus.INVALID_GEOMETRY, AggregatePlanningStatus.INVALID_GEOMETRY),
        (
            CalculationReadinessStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED,
            AggregatePlanningStatus.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED,
        ),
        (
            CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
            AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED,
            AggregatePlanningStatus.CALCULATION_NOT_SUPPORTED,
        ),
        (CalculationReadinessStatus.INCOMPLETE_INPUT, AggregatePlanningStatus.INCOMPLETE_INPUT),
        (
            CalculationReadinessStatus.SOURCE_DATA_PENDING,
            AggregatePlanningStatus.SOURCE_DATA_PENDING,
        ),
        (
            CalculationReadinessStatus.ENGINEERING_REVIEW_REQUIRED,
            AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED,
        ),
    ],
)
def test_aggregate_readiness_precedence(
    status: CalculationReadinessStatus, expected: AggregatePlanningStatus
) -> None:
    checks = (
        _check(CalculationReadinessStatus.READY),
        _check(status, check_id="governing"),
    )
    assert aggregate_planning_status(checks) is expected


def test_aggregate_known_fail_precedence_and_p2b_special_status() -> None:
    failure = (SuppliedNumericalFixtureResult("known", NumericalComparison.FAIL),)
    assert aggregate_planning_status((_check(CalculationReadinessStatus.READY),), failure) is (
        AggregatePlanningStatus.FAIL
    )
    assert (
        aggregate_planning_status(
            (_check(CalculationReadinessStatus.CALCULATION_NOT_SUPPORTED),), failure
        )
        is AggregatePlanningStatus.FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK
    )
    assert (
        aggregate_planning_status((_check(CalculationReadinessStatus.INVALID_GEOMETRY),), failure)
        is AggregatePlanningStatus.INVALID_GEOMETRY
    )
    passing_fixture = (SuppliedNumericalFixtureResult("known", NumericalComparison.PASS),)
    assert (
        aggregate_planning_status((_check(CalculationReadinessStatus.READY),), passing_fixture)
        is AggregatePlanningStatus.READY_FOR_STAGE_2_1B
    )


def test_aggregate_qualification_flags_not_applicable_and_optional_checks() -> None:
    engineering_review = _check(
        CalculationReadinessStatus.READY,
        flags=(QualificationStatus.ENGINEERING_REVIEW_REQUIRED,),
    )
    assert aggregate_planning_status((engineering_review,)) is (
        AggregatePlanningStatus.ENGINEERING_REVIEW_REQUIRED
    )
    section = replace(
        engineering_review,
        qualification_flags=(QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,),
    )
    assert aggregate_planning_status((section,)) is (
        AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    not_applicable = _check(CalculationReadinessStatus.NOT_APPLICABLE)
    assert aggregate_planning_status((not_applicable,)) is AggregatePlanningStatus.NOT_APPLICABLE
    optional_invalid = _check(
        CalculationReadinessStatus.INVALID_GEOMETRY,
        check_id="optional",
        required=False,
    )
    assert aggregate_planning_status((not_applicable, optional_invalid)) is (
        AggregatePlanningStatus.NOT_APPLICABLE
    )
    assert (
        aggregate_planning_status(
            (),
            whole_connection_statuses=(
                CalculationReadinessStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
            ),
        )
        is AggregatePlanningStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert aggregate_planning_status(()) is AggregatePlanningStatus.READY_FOR_STAGE_2_1B
