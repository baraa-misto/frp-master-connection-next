"""Execution-contract, integration, status, and fingerprint tests for Slice 2 RC2."""

from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import date
from decimal import Decimal
from typing import cast
from unittest.mock import patch

import pytest

from frp_master_connection.calculation import (
    BlockPathPlanStatus,
    BlockShearAreaPlan,
    BlockShearEccentricityClassification,
    BlockShearEccentricityContext,
    BlockShearPlanSet,
    ConnectedMaterialPair,
    DeferredExecutionStatus,
    EndUseFactors,
    FastenerSnapshot,
    FirstRowNetTensionPlan,
    FRPPropertyKind,
    GeometryStatus,
    InterrowShearOutPlan,
    MaterialDirection,
    MaterialPropertySnapshot,
    MethodProvenance,
    MultiRowBoltExecutionContext,
    MultiRowBoltLineExecutionContext,
    MultiRowCalculationPlanSet,
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowEquationMethod,
    MultiRowExecutableCheck,
    MultiRowExecutionBundle,
    MultiRowExecutionWarning,
    MultiRowExecutionWarningCode,
    MultiRowFactorContext,
    MultiRowFingerprintMetadataEntry,
    MultiRowLayerExecutionContext,
    MultiRowMethodApplicability,
    MultiRowOverallDisposition,
    MultiRowPhysicalGeometryContext,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    MultiRowSignedDemandContext,
    NetAreaStatus,
    NumericalComparison,
    PhysicalQuantity,
    PitchFactorSource,
    PlanAvailability,
    PultrudedElementClassification,
    QualificationDisposition,
    QualificationStatus,
    RowDistributionBasis,
    Slice2VersionContext,
    SourceClassification,
    ThreadStatus,
    ThreadStatusAssignment,
    Unit,
    WasherGeometry,
    assess_multirow_applicability,
    build_first_row_net_tension_plans,
    build_interrow_shear_out_plans,
    calculate_multirow_connection,
    canonical_multirow_execution_json,
    create_locked_ice_material_snapshot,
    create_synthetic_fastener_snapshot,
    multirow_execution_fingerprint,
    physical_geometry_context,
    plan_row_demands,
    resolve_first_row_geometry,
    resolve_multirow_end_distances,
)
from frp_master_connection.geometry import (
    GeneralBolt,
    GeneralBoltGroup,
    MultiRowGeometry,
    MultiRowGeometryTolerance,
    PlanarLayerBoundary,
    PlanarPoint2D,
    resolve_multirow_geometry,
)


def _provenance(*, confirmed: bool = True) -> MethodProvenance:
    return MethodProvenance(
        "RC2_TEST_METHOD",
        "independent verification ledger",
        "RC2",
        "LC-1",
        "CONNECTION_CENTROID",
        True,
        confirmed,
    )


def _geometry(
    *,
    force: tuple[float, float] = (1.0, 0.0),
    rows: tuple[float, ...] = (2.0, 0.0),
    lines: tuple[float, ...] = (-1.0, 1.0),
    reverse_array: bool = False,
) -> MultiRowGeometry:
    bolts = tuple(
        GeneralBolt(
            f"B_R{row_number}_L{line_number}",
            PlanarPoint2D(row, line),
            0.5,
            0.563,
            "BOLT-SYNTHETIC",
            "CONNECTION-1",
        )
        for row_number, row in enumerate(rows, start=1)
        for line_number, line in enumerate(lines, start=1)
    )
    if reverse_array:
        bolts = tuple(reversed(bolts))
    group = GeneralBoltGroup("BG-1", "INTERFACE-1", len(rows), len(bolts), bolts)
    return resolve_multirow_geometry(
        group,
        PlanarLayerBoundary("LAYER-1", min(rows) - 2, max(rows) + 2, -3, 3),
        force,
        MultiRowGeometryTolerance(1e-6),
    )


def _qualified_material() -> MaterialPropertySnapshot:
    source = create_locked_ice_material_snapshot()
    properties = tuple(
        replace(
            item,
            source_classification=SourceClassification.QUALIFIED_TEST_DATA,
            qualification_status=QualificationStatus.QUALIFIED,
            source_document="RC2 synthetic qualified reference material",
            source_revision="RC2",
        )
        for item in source.properties
    )
    return replace(
        source,
        id="RC2_SYNTHETIC_QUALIFIED",
        display_name="RC2 synthetic qualified reference material",
        locked=False,
        basis=SourceClassification.QUALIFIED_TEST_DATA,
        qualification_statuses=(QualificationStatus.QUALIFIED,),
        properties=properties,
    )


def _fastener() -> FastenerSnapshot:
    source = create_synthetic_fastener_snapshot(
        id="BOLT-SYNTHETIC",
        fnt=PhysicalQuantity.of("100", Unit.KSI),
        source_classification=SourceClassification.USER_DEFINED,
    )
    washer = WasherGeometry(
        PhysicalQuantity.of("1.25", Unit.IN), PhysicalQuantity.of(".08", Unit.IN), True, True
    )
    return replace(
        source,
        shear_plane_thread_statuses=(
            ThreadStatusAssignment("SHEAR_PLANE-1", ThreadStatus.EXCLUDED),
        ),
        bearing_layer_thread_statuses=(ThreadStatusAssignment("LAYER-1", ThreadStatus.EXCLUDED),),
        number_of_shear_planes=1,
        washer_geometry=washer,
    )


def _block_plan() -> BlockShearAreaPlan:
    return BlockShearAreaPlan(
        "BLOCK-U",
        BlockPathPlanStatus.ACCEPTED,
        (),
        PhysicalQuantity.of("5", Unit.IN),
        PhysicalQuantity.of("4.82625", Unit.IN),
        PhysicalQuantity.of("1", Unit.IN),
        PhysicalQuantity.of(".7965", Unit.IN),
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("1.875", Unit.IN2),
        PhysicalQuantity.of("1.80984375", Unit.IN2),
        PhysicalQuantity.of(".375", Unit.IN2),
        PhysicalQuantity.of(".2986875", Unit.IN2),
        Decimal(".96525"),
        Decimal(".7965"),
        NetAreaStatus.SATISFIES_MINIMUM_NET_AREA,
        NetAreaStatus.SATISFIES_MINIMUM_NET_AREA,
        (),
        PlanAvailability.READY,
        (),
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
        DeferredExecutionStatus.DEFERRED_STAGE_2_4B,
    )


def _check(
    check_id: str,
    family: MultiRowCheckFamily,
    method: MultiRowEquationMethod,
    *,
    demand: str = ".1",
    layer_id: str | None = None,
    bolt_id: str | None = None,
    bolt_line_id: str | None = None,
    plan: object | None = None,
    availability: PlanAvailability = PlanAvailability.READY,
    applicability: MultiRowMethodApplicability = MultiRowMethodApplicability.ASCE_PRESCRIPTIVE,
    qualification: QualificationDisposition = QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE,
    geometry: GeometryStatus = GeometryStatus.VALID,
) -> MultiRowExecutableCheck:
    return MultiRowExecutableCheck(
        check_id,
        getattr(plan, "id", check_id),
        family,
        method,
        "ASCE/SEI 74-23 Chapter 8",
        applicability,
        qualification,
        availability,
        geometry,
        PhysicalQuantity.of(demand, Unit.KIP),
        layer_id,
        bolt_id,
        "ROW_1" if family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION else None,
        bolt_line_id,
        "BLOCK-U" if family is MultiRowCheckFamily.BLOCK_SHEAR else None,
        cast(FirstRowNetTensionPlan, plan)
        if family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
        else None,
        cast(InterrowShearOutPlan, plan)
        if family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
        else None,
        cast(BlockShearAreaPlan, plan) if family is MultiRowCheckFamily.BLOCK_SHEAR else None,
        Decimal(".5") if method is MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL else None,
    )


def _bundle(
    *,
    force: tuple[float, float] = (1.0, 0.0),
    checks: tuple[MultiRowExecutableCheck, ...] | None = None,
    required_ids: tuple[str, ...] | None = None,
    include_eccentricity: bool = True,
    confirmed: bool = True,
    reverse_array: bool = False,
    rows: tuple[float, ...] = (2.0, 0.0),
    direction: MaterialDirection = MaterialDirection.LONGITUDINAL,
) -> MultiRowExecutionBundle:
    geometry = _geometry(force=force, reverse_array=reverse_array, rows=rows)
    provenance = _provenance(confirmed=confirmed)
    basis = (
        RowDistributionBasis.ASCE_PRESCRIBED
        if len(rows) in {2, 3}
        else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE
    )
    demand = plan_row_demands(
        geometry,
        PhysicalQuantity.of("2", Unit.KIP),
        basis,
        provenance,
        connected_materials=ConnectedMaterialPair.FRP_FRP
        if basis is RowDistributionBasis.ASCE_PRESCRIBED
        else None,
    )
    first_geometry = resolve_first_row_geometry(
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".5", Unit.IN),
        direction,
        PultrudedElementClassification.SHAPE,
    )
    first_plans = build_first_row_net_tension_plans(
        first_geometry,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("33", Unit.KSI),
        PhysicalQuantity.of(".626", Unit.IN),
        prescribed_lbr=Decimal(".5"),
    )
    interrow = build_interrow_shear_out_plans(
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("8", Unit.KSI),
        PhysicalQuantity.of("2", Unit.KIP),
        (),
    )
    applicability = assess_multirow_applicability(geometry, first_geometry, basis)
    block_plan = _block_plan()
    planning = MultiRowCalculationPlanSet(
        demand, applicability, first_plans, interrow, (block_plan.path_id,)
    )
    fastener = _fastener()
    physical_bolts = sorted(geometry.group.bolts, key=lambda item: item.id)
    per_bolt_demands = {
        item.bolt_id: item.demand
        for scenario in demand.scenarios
        for row in scenario.rows
        for item in row.per_bolt_demands
    }
    bolts = tuple(
        MultiRowBoltExecutionContext(
            item.id,
            PhysicalQuantity.of(".5", Unit.IN),
            fastener,
            ThreadStatus.EXCLUDED,
            per_bolt_demands[item.id],
            PhysicalQuantity.of(".1", Unit.KIP),
            True,
            fastener.washer_geometry,
            ("LAYER-1",),
        )
        for item in physical_bolts
    )
    lines = tuple(
        MultiRowBoltLineExecutionContext(
            item.bolt_line_id, item.per_line_demand, True, "ASCE_LINE_DISTRIBUTION"
        )
        for item in interrow
    )
    layer = MultiRowLayerExecutionContext(
        "LAYER-1",
        "COMPONENT-1",
        _qualified_material(),
        PhysicalQuantity.of(".375", Unit.IN),
        direction,
        PultrudedElementClassification.SHAPE,
        EndUseFactors(Decimal(1), Decimal(1), Decimal(1), "fixture", ("approved",)),
        ThreadStatus.EXCLUDED,
        (geometry.group.id, geometry.boundary.id),
    )
    if checks is None:
        bolt_id = physical_bolts[0].id
        if len(rows) > 3:
            checks = (
                _check(
                    "FIRST_RATIONAL",
                    MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                    MultiRowEquationMethod.FIRST_ROW_RATIONAL_LOWER_ENVELOPE,
                    layer_id="LAYER-1",
                    plan=first_plans[2],
                    applicability=MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
                    qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
                ),
                _check(
                    "INTERROW_RATIONAL",
                    MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                    MultiRowEquationMethod.INTERROW_RATIONAL_EXTENSION_EQ_8_13,
                    layer_id="LAYER-1",
                    bolt_line_id=interrow[0].bolt_line_id,
                    plan=interrow[0],
                    applicability=MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
                    qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
                ),
            )
        else:
            checks = (
                _check(
                    "BOLT_SHEAR",
                    MultiRowCheckFamily.BOLT_SHEAR,
                    MultiRowEquationMethod.BOLT_SHEAR,
                    bolt_id=bolt_id,
                ),
                _check(
                    "BOLT_TENSION",
                    MultiRowCheckFamily.BOLT_TENSION,
                    MultiRowEquationMethod.BOLT_TENSION,
                    bolt_id=bolt_id,
                ),
                _check(
                    "BOLT_COMBINED",
                    MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
                    MultiRowEquationMethod.BOLT_COMBINED_TENSION_SHEAR,
                    bolt_id=bolt_id,
                ),
                _check(
                    "PULL_THROUGH",
                    MultiRowCheckFamily.PULL_THROUGH,
                    MultiRowEquationMethod.PULL_THROUGH,
                    bolt_id=bolt_id,
                    layer_id="LAYER-1",
                ),
                _check(
                    "PIN_BEARING",
                    MultiRowCheckFamily.PIN_BEARING,
                    MultiRowEquationMethod.PIN_BEARING,
                    bolt_id=bolt_id,
                    layer_id="LAYER-1",
                ),
                _check(
                    "FIRST_SIMPLIFIED",
                    MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                    MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED,
                    layer_id="LAYER-1",
                    plan=first_plans[0],
                ),
                _check(
                    "FIRST_FULL",
                    MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                    MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL,
                    layer_id="LAYER-1",
                    plan=first_plans[1],
                ),
                _check(
                    "INTERROW",
                    MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                    MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12,
                    layer_id="LAYER-1",
                    bolt_line_id=interrow[0].bolt_line_id,
                    plan=interrow[0],
                ),
                _check(
                    "BLOCK",
                    MultiRowCheckFamily.BLOCK_SHEAR,
                    MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14A,
                    layer_id="LAYER-1",
                    plan=block_plan,
                ),
            )
    required = tuple(item.check_id for item in checks) if required_ids is None else required_ids
    eccentricity = (
        BlockShearEccentricityContext(
            PhysicalQuantity.of("0", Unit.IN),
            "signed load line to block path centroid",
            PhysicalQuantity.of(".000001", Unit.IN),
            ("BLOCK-U", "LOAD-LINE"),
            BlockShearEccentricityClassification.CONCENTRIC,
        )
        if include_eccentricity
        else None
    )
    return MultiRowExecutionBundle(
        physical_geometry_context(geometry, Unit.IN),
        planning,
        BlockShearPlanSet((block_plan,), DeferredExecutionStatus.DEFERRED_STAGE_2_4B),
        resolve_multirow_end_distances(geometry, Unit.IN),
        (layer,),
        bolts,
        lines,
        MultiRowSignedDemandContext(
            Decimal(str(force[0])),
            Decimal(str(force[1])),
            PhysicalQuantity.of("2", Unit.KIP),
            "LC-1",
        ),
        MultiRowFactorContext(
            Decimal(1), Decimal(1), Decimal(1), PitchFactorSource.AUTOMATIC_CONSTANT_PITCH
        ),
        MultiRowRequiredCheckContract(required),
        checks,
        provenance,
        Slice2VersionContext(),
        (MultiRowFingerprintMetadataEntry("source_package", "RC2"),),
        eccentricity,
    )


def test_complete_engine_executes_every_approved_check_family_and_is_deterministic() -> None:
    bundle = _bundle()
    first = calculate_multirow_connection(bundle)
    second = calculate_multirow_connection(bundle)
    assert first == second
    assert first.input_fingerprint == multirow_execution_fingerprint(bundle)
    assert len(first.input_fingerprint) == len(first.result_fingerprint) == 64
    assert first.required_check_ids == tuple(item.check_id for item in bundle.checks)
    assert first.calculated_check_ids == first.required_check_ids
    assert first.not_applicable_check_ids == ()
    assert first.incomplete_check_ids == ()
    assert first.unsupported_check_ids == ()
    assert first.failed_check_ids == ()
    assert first.geometry_status is GeometryStatus.VALID
    assert first.availability is MultiRowResultAvailability.CALCULATED
    assert first.numerical_comparison is NumericalComparison.PASS
    assert first.overall_disposition is MultiRowOverallDisposition.PASS
    assert first.governing_result_ids
    assert {item.limit_state for item in first.results} == {
        MultiRowCheckFamily.BOLT_SHEAR,
        MultiRowCheckFamily.BOLT_TENSION,
        MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR,
        MultiRowCheckFamily.PULL_THROUGH,
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    }
    assert all(item.input_fingerprint == first.input_fingerprint for item in first.results)
    assert all(item.versions is bundle.versions for item in first.results)


def test_execution_fingerprint_is_canonical_array_stable_unit_sensitive_and_directional() -> None:
    canonical = canonical_multirow_execution_json(_bundle())
    assert "camera" not in canonical
    assert "0.2.0.dev1" in canonical
    assert '"x":"0"' in canonical
    assert multirow_execution_fingerprint(_bundle()) == multirow_execution_fingerprint(
        _bundle(reverse_array=True)
    )
    assert multirow_execution_fingerprint(_bundle(force=(1, 0))) != multirow_execution_fingerprint(
        _bundle(force=(-1, 0))
    )


def test_zero_required_checks_are_not_an_ordinary_pass() -> None:
    result = calculate_multirow_connection(_bundle(required_ids=()))
    assert result.numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert result.availability is MultiRowResultAvailability.NOT_APPLICABLE
    assert result.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert result.governing_result_ids == ()


@pytest.mark.parametrize(
    ("family", "availability", "disposition"),
    [
        (
            MultiRowCheckFamily.CODE_GEOMETRY,
            MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
            MultiRowOverallDisposition.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
        ),
        (
            MultiRowCheckFamily.QUALIFICATION,
            MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED,
            MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW,
            MultiRowResultAvailability.ENGINEERING_REVIEW_REQUIRED,
            MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED,
        ),
    ],
)
def test_status_only_required_checks_remain_non_numerical(
    family: MultiRowCheckFamily,
    availability: MultiRowResultAvailability,
    disposition: MultiRowOverallDisposition,
) -> None:
    check = _check(
        family.value,
        family,
        MultiRowEquationMethod.STATUS_ONLY,
        demand="0",
        availability=PlanAvailability.READY,
        qualification=(
            QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
            if family is MultiRowCheckFamily.QUALIFICATION
            else QualificationDisposition.ENGINEERING_REVIEW_REQUIRED
            if family is MultiRowCheckFamily.MATERIAL_SOURCE_REVIEW
            else QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
        ),
    )
    result = calculate_multirow_connection(_bundle(checks=(check,)))
    assert result.results[0].availability is availability
    assert result.results[0].numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert result.overall_disposition is disposition


@pytest.mark.parametrize(
    ("plan_status", "result_status"),
    [
        (PlanAvailability.NOT_APPLICABLE, MultiRowResultAvailability.NOT_APPLICABLE),
        (PlanAvailability.INCOMPLETE_INPUT, MultiRowResultAvailability.INCOMPLETE_INPUT),
        (PlanAvailability.SOURCE_DATA_PENDING, MultiRowResultAvailability.SOURCE_DATA_PENDING),
        (
            PlanAvailability.CALCULATION_NOT_SUPPORTED,
            MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED,
        ),
        (
            PlanAvailability.ENGINEERING_REVIEW_REQUIRED,
            MultiRowResultAvailability.ENGINEERING_REVIEW_REQUIRED,
        ),
        (
            PlanAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED,
            MultiRowResultAvailability.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
            MultiRowResultAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
        ),
    ],
)
def test_plan_availability_maps_without_numerical_leakage(
    plan_status: PlanAvailability,
    result_status: MultiRowResultAvailability,
) -> None:
    base = _bundle().checks[0]
    check = replace(base, check_id=f"STATUS_{plan_status.value}", plan_availability=plan_status)
    result = calculate_multirow_connection(_bundle(checks=(check,)))
    item = result.results[0]
    assert item.availability is result_status
    assert item.design_resistance is None
    assert item.demand is None
    assert item.utilization is None


def test_invalid_geometry_missing_demand_and_missing_axis_tension_fail_closed() -> None:
    base_bundle = _bundle()
    invalid = replace(
        base_bundle.checks[0], check_id="INVALID", geometry_status=GeometryStatus.INVALID_GEOMETRY
    )
    missing_demand = replace(base_bundle.checks[0], check_id="MISSING_DEMAND", demand=None)
    tension = next(
        item for item in base_bundle.checks if item.family is MultiRowCheckFamily.BOLT_TENSION
    )
    bolts = tuple(replace(item, bolt_axis_tension_demand=None) for item in base_bundle.bolts)
    axis_bundle = replace(
        base_bundle,
        checks=(tension,),
        required_checks=MultiRowRequiredCheckContract((tension.check_id,)),
        bolts=bolts,
    )
    invalid_result = calculate_multirow_connection(_bundle(checks=(invalid,))).results[0]
    missing_result = calculate_multirow_connection(_bundle(checks=(missing_demand,))).results[0]
    axis_result = calculate_multirow_connection(axis_bundle).results[0]
    assert invalid_result.availability is MultiRowResultAvailability.INVALID_GEOMETRY
    assert missing_result.availability is MultiRowResultAvailability.INCOMPLETE_INPUT
    assert axis_result.availability is MultiRowResultAvailability.INCOMPLETE_INPUT
    assert (
        axis_result.warnings[0].code
        is MultiRowExecutionWarningCode.MISSING_REQUIRED_BOLT_AXIS_TENSION
    )


def test_missing_eccentricity_and_unexpected_arithmetic_are_not_exceptions() -> None:
    block = next(
        item for item in _bundle().checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR
    )
    missing = calculate_multirow_connection(
        _bundle(checks=(block,), include_eccentricity=False)
    ).results[0]
    assert missing.availability is MultiRowResultAvailability.INCOMPLETE_INPUT
    base = _bundle(checks=(block,))
    with patch(
        "frp_master_connection.calculation.multirow_engine.block_shear_resistance",
        side_effect=ArithmeticError,
    ):
        unsupported = calculate_multirow_connection(base).results[0]
    assert unsupported.availability is MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED
    assert unsupported.warnings[-1].code is MultiRowExecutionWarningCode.NUMERICAL_DOMAIN_ERROR


def test_qualification_and_failure_precedence_preserve_both_facts() -> None:
    base = _bundle().checks[0]
    failed = replace(
        base,
        check_id="FAIL_OUTSIDE_SCOPE",
        demand=PhysicalQuantity.of("1000", Unit.KIP),
        method_applicability=MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
        qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    )
    result = calculate_multirow_connection(_bundle(checks=(failed,)))
    assert result.numerical_comparison is NumericalComparison.FAIL
    assert result.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    assert result.overall_disposition is MultiRowOverallDisposition.FAIL
    assert result.failed_check_ids == (failed.check_id,)


def test_engineer_defined_pass_never_becomes_ordinary_asce_pass() -> None:
    base = _bundle().checks[0]
    engineer = replace(
        base,
        check_id="ENGINEER_DEFINED",
        method_applicability=MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE,
        qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        warnings=(
            MultiRowExecutionWarning(MultiRowExecutionWarningCode.ENGINEER_DEFINED_METHOD_USED),
        ),
    )
    result = calculate_multirow_connection(_bundle(checks=(engineer,)))
    assert result.numerical_comparison is NumericalComparison.PASS
    assert (
        result.overall_disposition
        is MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert result.warnings[0].code is MultiRowExecutionWarningCode.ENGINEER_DEFINED_METHOD_USED


def test_execution_bundle_is_deeply_immutable_and_rejects_mutable_or_float_authority() -> None:
    bundle = _bundle()
    with pytest.raises(FrozenInstanceError):
        bundle.eccentricity = None  # type: ignore[misc]
    mutable = MultiRowFingerprintMetadataEntry("mutable", "value")
    object.__setattr__(mutable, "value", cast(str, []))
    with pytest.raises(TypeError, match="mutable nested state"):
        replace(bundle, fingerprint_metadata=(mutable,))
    physical = bundle.physical_geometry
    object.__setattr__(physical.bolts[0], "x", cast(Decimal, 1.0))
    with pytest.raises(TypeError, match="authoritative binary float"):
        replace(bundle, physical_geometry=physical)


def test_versions_are_slice_2_specific_and_cannot_be_substituted() -> None:
    versions = Slice2VersionContext()
    assert versions.calculation_engine_version == "0.2.0.dev1"
    assert versions.engineering_rule_set_version == "asce74-23-ch8-multirow-rc2.dev1"
    with pytest.raises(ValueError, match="approved RC2 identities"):
        replace(versions, calculation_engine_version="0.1.0.dev1")


def test_end_distance_contract_distinguishes_all_three_physical_distances() -> None:
    geometry = _geometry()
    context = resolve_multirow_end_distances(geometry, Unit.IN)
    assert context.unloaded_end_e1 == PhysicalQuantity.of("2", Unit.IN)
    assert context.row_1_to_unloaded_end_distance == PhysicalQuantity.of("4", Unit.IN)
    assert context.loaded_boundary_to_row_1_distance == PhysicalQuantity.of("2", Unit.IN)
    assert context.physical_pitches == (PhysicalQuantity.of("2", Unit.IN),)
    with pytest.raises(ValueError, match="must equal e1"):
        replace(context, row_1_to_unloaded_end_distance=PhysicalQuantity.of("2", Unit.IN))


def test_r4_end_distance_recovery_performs_exact_arithmetic_before_subtraction() -> None:
    geometry = replace(
        _geometry(rows=(76.2, 25.4)),
        unloaded_free_end_u=0.0,
        loaded_end_u=101.6,
    )

    recovered = resolve_multirow_end_distances(geometry, Unit.MM)
    sourced = resolve_multirow_end_distances(
        geometry,
        Unit.MM,
        exact_unloaded_end_e1=PhysicalQuantity.of("25.4", Unit.MM),
        exact_physical_pitches=(PhysicalQuantity.of("50.8", Unit.MM),),
        exact_loaded_boundary_to_row_1_distance=PhysicalQuantity.of("25.4", Unit.MM),
    )

    assert geometry.classification.pitches == (50.800000000000004,)
    assert recovered == sourced
    assert recovered.unloaded_end_e1 == PhysicalQuantity.of("25.4", Unit.MM)
    assert recovered.physical_pitches == (PhysicalQuantity.of("50.8", Unit.MM),)
    assert recovered.row_1_to_unloaded_end_distance == PhysicalQuantity.of("76.2", Unit.MM)
    assert recovered.loaded_boundary_to_row_1_distance == PhysicalQuantity.of("25.4", Unit.MM)


def test_r4_exact_end_distance_source_is_complete_and_matches_resolved_rows() -> None:
    geometry = _geometry()
    with pytest.raises(ValueError, match="supplied together"):
        resolve_multirow_end_distances(
            geometry,
            Unit.IN,
            exact_unloaded_end_e1=PhysicalQuantity.of("2", Unit.IN),
        )
    with pytest.raises(TypeError, match="immutable tuple"):
        resolve_multirow_end_distances(
            geometry,
            Unit.IN,
            exact_unloaded_end_e1=PhysicalQuantity.of("2", Unit.IN),
            exact_physical_pitches=cast(
                tuple[PhysicalQuantity, ...], [PhysicalQuantity.of("2", Unit.IN)]
            ),
            exact_loaded_boundary_to_row_1_distance=PhysicalQuantity.of("2", Unit.IN),
        )
    with pytest.raises(ValueError, match="resolved row count"):
        resolve_multirow_end_distances(
            geometry,
            Unit.IN,
            exact_unloaded_end_e1=PhysicalQuantity.of("2", Unit.IN),
            exact_physical_pitches=(),
            exact_loaded_boundary_to_row_1_distance=PhysicalQuantity.of("2", Unit.IN),
        )


def test_required_check_tie_ordering_uses_declared_result_order_and_existing_tolerance() -> None:
    first = replace(
        _bundle().checks[0], check_id="CHECK_A", demand=PhysicalQuantity.of("1", Unit.KIP)
    )
    second = replace(first, check_id="CHECK_B")
    result = calculate_multirow_connection(_bundle(checks=(first, second)))
    assert result.governing_result_ids == ("CHECK_A", "CHECK_B")


def test_contract_rejects_wrong_root_types_and_unknown_required_references() -> None:
    with pytest.raises(TypeError, match="MultiRowExecutionBundle"):
        calculate_multirow_connection(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="MultiRowExecutionBundle"):
        canonical_multirow_execution_json(object())  # type: ignore[arg-type]
    bundle = _bundle()
    with pytest.raises(ValueError, match="required check ID"):
        replace(bundle, required_checks=MultiRowRequiredCheckContract(("UNKNOWN",)))


def test_physical_geometry_helpers_reject_wrong_types_and_units() -> None:
    geometry = _geometry()
    with pytest.raises(TypeError, match="MultiRowGeometry"):
        physical_geometry_context(object(), Unit.IN)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="IN or MM"):
        physical_geometry_context(geometry, Unit.KIP)
    with pytest.raises(TypeError, match="MultiRowGeometry"):
        resolve_multirow_end_distances(object(), Unit.IN)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="IN or MM"):
        resolve_multirow_end_distances(geometry, Unit.KIP)


def test_rational_more_than_three_row_equations_execute_but_require_qualification() -> None:
    result = calculate_multirow_connection(_bundle(rows=(6.0, 4.0, 2.0, 0.0)))
    assert result.calculated_check_ids == ("FIRST_RATIONAL", "INTERROW_RATIONAL")
    assert result.numerical_comparison is NumericalComparison.PASS
    assert (
        result.method_applicability
        is MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    )
    assert result.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    assert (
        result.overall_disposition
        is MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )


def test_reduced_pitch_eccentric_block_and_net_area_warning_traces_are_explicit() -> None:
    base = _bundle()
    block = next(item for item in base.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR)
    warned_plan = replace(
        cast(BlockShearAreaPlan, block.block_plan),
        shear_net_area_status=NetAreaStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
    )
    warned_check = replace(block, block_plan=warned_plan)
    eccentricity = replace(
        cast(BlockShearEccentricityContext, base.eccentricity),
        signed_eccentricity=PhysicalQuantity.of(".001", Unit.IN),
        classification=BlockShearEccentricityClassification.ECCENTRIC,
    )
    bundle = replace(
        base,
        checks=(warned_check,),
        required_checks=MultiRowRequiredCheckContract((warned_check.check_id,)),
        block_shear_plans=BlockShearPlanSet(
            (warned_plan,), DeferredExecutionStatus.DEFERRED_STAGE_2_4B
        ),
        eccentricity=eccentricity,
        factors=MultiRowFactorContext(
            Decimal(1), Decimal(1), Decimal(".75"), PitchFactorSource.AUTOMATIC_CONSTANT_PITCH
        ),
    )
    result = calculate_multirow_connection(bundle)
    codes = tuple(item.code for item in result.warnings)
    assert MultiRowExecutionWarningCode.REDUCED_PITCH_FACTOR_APPLIED in codes
    assert MultiRowExecutionWarningCode.LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS in codes
    assert MultiRowExecutionWarningCode.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED in codes
    assert (
        result.overall_disposition
        is MultiRowOverallDisposition.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    )


def test_engine_converts_known_calculation_input_errors_to_invalid_geometry() -> None:
    base = _bundle()
    bolt_bundle = _bundle(checks=(base.checks[0],))
    object.__setattr__(bolt_bundle.checks[0], "bolt_id", "UNKNOWN")
    unknown_line = next(
        item for item in base.checks if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    )
    line_bundle = _bundle(checks=(unknown_line,))
    object.__setattr__(line_bundle.checks[0], "bolt_line_id", "UNKNOWN")
    bearing = next(item for item in base.checks if item.family is MultiRowCheckFamily.PIN_BEARING)
    layer_bundle = _bundle(checks=(bearing,))
    object.__setattr__(layer_bundle.checks[0], "layer_id", "UNKNOWN")
    for execution_bundle in (bolt_bundle, line_bundle, layer_bundle):
        result = calculate_multirow_connection(execution_bundle)
        assert result.results[0].availability is MultiRowResultAvailability.INVALID_GEOMETRY


def test_missing_fastener_washer_material_property_and_first_row_inputs_fail_closed() -> None:
    base = _bundle()
    bolt_check = base.checks[0]
    pending_fastener = replace(
        base.bolts[0].fastener,
        fnt=None,
        fnt_source_classification=SourceClassification.SOURCE_PENDING,
        fnt_qualification_status=QualificationStatus.SOURCE_PENDING,
    )
    bolts = tuple(replace(item, fastener=pending_fastener) for item in base.bolts)
    pending = calculate_multirow_connection(
        replace(
            base,
            checks=(bolt_check,),
            required_checks=MultiRowRequiredCheckContract((bolt_check.check_id,)),
            bolts=bolts,
        )
    )
    assert pending.results[0].availability is MultiRowResultAvailability.INVALID_GEOMETRY

    pull = next(item for item in base.checks if item.family is MultiRowCheckFamily.PULL_THROUGH)
    no_washer_bolts = tuple(replace(item, washer=None) for item in base.bolts)
    no_washer = calculate_multirow_connection(
        replace(
            base,
            checks=(pull,),
            required_checks=MultiRowRequiredCheckContract((pull.check_id,)),
            bolts=no_washer_bolts,
        )
    )
    assert no_washer.results[0].availability is MultiRowResultAvailability.INVALID_GEOMETRY

    bearing = next(item for item in base.checks if item.family is MultiRowCheckFamily.PIN_BEARING)
    material = base.layers[0].material
    properties = tuple(item for item in material.properties if item.kind.value != "FBR_L")
    missing_material = replace(
        material,
        properties=properties,
        explicitly_missing=tuple(
            sorted(
                (*material.explicitly_missing, FRPPropertyKind.FBR_L), key=lambda item: item.value
            )
        ),
    )
    missing_layers = (replace(base.layers[0], material=missing_material),)
    invalid_material = calculate_multirow_connection(
        replace(
            base,
            checks=(bearing,),
            required_checks=MultiRowRequiredCheckContract((bearing.check_id,)),
            layers=missing_layers,
        )
    )
    assert invalid_material.results[0].availability is MultiRowResultAvailability.INVALID_GEOMETRY

    first = next(
        item
        for item in base.checks
        if item.method is MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL
    )
    no_lbr = replace(
        first,
        lbr=None,
        first_row_plan=replace(cast(FirstRowNetTensionPlan, first.first_row_plan), lbr=None),
    )
    assert (
        calculate_multirow_connection(_bundle(checks=(no_lbr,))).results[0].availability
        is MultiRowResultAvailability.INVALID_GEOMETRY
    )


def test_nonuniform_line_without_confirmed_provenance_and_block_path_domains_fail_closed() -> None:
    base = _bundle(confirmed=False)
    interrow = next(
        item for item in base.checks if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    )
    lines = tuple(replace(item, equivalent_rectangular_line=False) for item in base.bolt_lines)
    result = calculate_multirow_connection(
        replace(
            base,
            checks=(interrow,),
            required_checks=MultiRowRequiredCheckContract((interrow.check_id,)),
            bolt_lines=lines,
        )
    )
    assert result.results[0].availability is MultiRowResultAvailability.INVALID_GEOMETRY

    block = next(item for item in base.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR)
    plan = cast(BlockShearAreaPlan, block.block_plan)
    variants = (
        replace(plan, path_status=BlockPathPlanStatus.REJECTED),
        replace(plan, shear_net_area_status=NetAreaStatus.INVALID_GEOMETRY),
    )
    for variant in variants:
        check = replace(block, block_plan=variant)
        bundle = replace(
            base,
            checks=(check,),
            required_checks=MultiRowRequiredCheckContract((check.check_id,)),
            block_shear_plans=BlockShearPlanSet(
                (variant,), DeferredExecutionStatus.DEFERRED_STAGE_2_4B
            ),
        )
        assert (
            calculate_multirow_connection(bundle).results[0].availability
            is MultiRowResultAvailability.INVALID_GEOMETRY
        )

    transverse = _bundle(direction=MaterialDirection.TRANSVERSE)
    transverse_block = next(
        item for item in transverse.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR
    )
    assert (
        calculate_multirow_connection(
            replace(
                transverse,
                checks=(transverse_block,),
                required_checks=MultiRowRequiredCheckContract((transverse_block.check_id,)),
            )
        )
        .results[0]
        .availability
        is MultiRowResultAvailability.INVALID_GEOMETRY
    )


def test_warning_deduplication_retains_first_declared_order() -> None:
    base = _bundle()
    warning = MultiRowExecutionWarning(
        MultiRowExecutionWarningCode.EXTERNAL_RESOLVED_PLAN_USED, ("source:external",)
    )
    check = replace(base.checks[0], warnings=(warning, warning))
    result = calculate_multirow_connection(_bundle(checks=(check,)))
    assert result.warnings == (warning,)
    assert result.results[0].warnings == (warning,)


def test_factor_context_engineer_defined_provenance_rules() -> None:
    confirmed = _provenance()
    value = MultiRowFactorContext(
        Decimal(1), Decimal(1), Decimal(".8"), PitchFactorSource.ENGINEER_DEFINED, confirmed
    )
    assert value.pitch_factor_provenance is confirmed
    for provenance in (None, _provenance(confirmed=False)):
        with pytest.raises(ValueError, match="confirmed provenance"):
            MultiRowFactorContext(
                Decimal(1),
                Decimal(1),
                Decimal(1),
                PitchFactorSource.ENGINEER_DEFINED,
                provenance,
            )
    with pytest.raises(ValueError, match="reserved"):
        MultiRowFactorContext(
            Decimal(1),
            Decimal(1),
            Decimal(1),
            PitchFactorSource.AUTOMATIC_CONSTANT_PITCH,
            confirmed,
        )


def test_low_level_execution_contract_validation_rejects_invalid_state() -> None:
    bundle = _bundle()
    physical = bundle.physical_geometry
    bolt_geometry = physical.bolts[0]
    projected = physical.rows[0]
    end = bundle.end_distances
    layer = bundle.layers[0]
    bolt = bundle.bolts[0]
    line = bundle.bolt_lines[0]
    eccentricity = cast(BlockShearEccentricityContext, bundle.eccentricity)

    with pytest.raises(TypeError, match="MultiRowExecutionWarningCode"):
        MultiRowExecutionWarning(cast(MultiRowExecutionWarningCode, "BAD"))
    with pytest.raises(ValueError, match="Physical bolt/hole geometry"):
        replace(bolt_geometry, bolt_diameter=Decimal(0))
    with pytest.raises(ValueError, match="positive non-Boolean"):
        replace(projected, ordinal=0)
    with pytest.raises(ValueError, match="cannot be negative"):
        replace(projected, raw_deviation=Decimal(-1))
    with pytest.raises(ValueError, match="IN or MM"):
        replace(physical, source_length_unit=Unit.KIP)
    with pytest.raises(TypeError, match="two-Decimal tuple"):
        replace(physical, force_u=cast(tuple[Decimal, Decimal], (Decimal(1),)))
    with pytest.raises(ValueError, match="sorting_tolerance"):
        replace(physical, sorting_tolerance=Decimal(0))
    with pytest.raises(ValueError, match="requires bolts"):
        replace(physical, bolts=())
    with pytest.raises(ValueError, match="nonnegative length"):
        replace(end, unloaded_end_e1=PhysicalQuantity.of("-1", Unit.IN))
    with pytest.raises(ValueError, match="positive lengths"):
        replace(end, physical_pitches=(PhysicalQuantity.of("0", Unit.IN),))
    with pytest.raises(TypeError, match="exactly two"):
        replace(end, side_boundary_ids=cast(tuple[str, str], ("ONE",)))
    with pytest.raises(ValueError, match="cannot be zero"):
        MultiRowSignedDemandContext(
            Decimal(0), Decimal(0), PhysicalQuantity.of("1", Unit.KIP), "LC"
        )
    with pytest.raises(ValueError, match="must be positive"):
        MultiRowFactorContext(
            Decimal(0), Decimal(1), Decimal(1), PitchFactorSource.UNITY_NOT_APPLICABLE
        )
    with pytest.raises(TypeError, match="PitchFactorSource"):
        MultiRowFactorContext(Decimal(1), Decimal(1), Decimal(1), cast(PitchFactorSource, "BAD"))
    with pytest.raises(TypeError, match="MaterialPropertySnapshot"):
        replace(layer, material=cast(MaterialPropertySnapshot, object()))
    with pytest.raises(ValueError, match="positive length"):
        replace(layer, thickness=PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(TypeError, match="MaterialDirection"):
        replace(layer, material_direction=cast(MaterialDirection, "BAD"))
    with pytest.raises(TypeError, match="PultrudedElementClassification"):
        replace(layer, element_classification=cast(PultrudedElementClassification, "BAD"))
    with pytest.raises(TypeError, match="EndUseFactors"):
        replace(layer, end_use_factors=cast(EndUseFactors, object()))
    with pytest.raises(TypeError, match="ThreadStatus"):
        replace(layer, bearing_thread_status=cast(ThreadStatus, "BAD"))
    with pytest.raises(ValueError, match="Bolt diameter"):
        replace(bolt, diameter=PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(TypeError, match="FastenerSnapshot"):
        replace(bolt, fastener=cast(FastenerSnapshot, object()))
    with pytest.raises(TypeError, match="ThreadStatus"):
        replace(bolt, shear_thread_status=cast(ThreadStatus, "BAD"))
    with pytest.raises(TypeError, match="Boolean"):
        replace(bolt, bolt_axis_tension_required=cast(bool, 1))
    with pytest.raises(TypeError, match="WasherGeometry"):
        replace(bolt, washer=cast(WasherGeometry, object()))
    with pytest.raises(TypeError, match="Boolean"):
        replace(line, equivalent_rectangular_line=cast(bool, 1))
    with pytest.raises(ValueError, match="signed_eccentricity"):
        replace(eccentricity, signed_eccentricity=PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="positive length"):
        replace(eccentricity, tolerance=PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(ValueError, match="classification"):
        replace(eccentricity, classification=BlockShearEccentricityClassification.ECCENTRIC)


def test_check_contract_payload_and_enum_validation_is_fail_closed() -> None:
    bundle = _bundle()
    bolt = bundle.checks[0]
    first = next(
        item for item in bundle.checks if item.family is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
    )
    interrow = next(
        item for item in bundle.checks if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    )
    block = next(item for item in bundle.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR)
    with pytest.raises(TypeError, match="must be MultiRowCheckFamily"):
        replace(bolt, family=cast(MultiRowCheckFamily, "BAD"))
    with pytest.raises(TypeError, match="FirstRowNetTensionPlan"):
        replace(first, first_row_plan=cast(FirstRowNetTensionPlan, object()))
    with pytest.raises(TypeError, match="InterrowShearOutPlan"):
        replace(interrow, interrow_plan=cast(InterrowShearOutPlan, object()))
    with pytest.raises(TypeError, match="BlockShearAreaPlan"):
        replace(block, block_plan=cast(BlockShearAreaPlan, object()))
    with pytest.raises(ValueError, match="inclusive range"):
        replace(first, lbr=Decimal("1.1"))
    for family in (
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    ):
        with pytest.raises(ValueError, match="requires exactly one"):
            replace(bolt, family=family)
    with pytest.raises(ValueError, match="requires layer_id"):
        replace(first, layer_id=None)
    with pytest.raises(ValueError, match="requires layer_id and bolt_line_id"):
        replace(interrow, bolt_line_id=None)
    with pytest.raises(ValueError, match="requires layer_id and path_id"):
        replace(block, path_id=None)
    with pytest.raises(ValueError, match="Per-bolt check"):
        replace(bolt, bolt_id=None)
    pull = next(item for item in bundle.checks if item.family is MultiRowCheckFamily.PULL_THROUGH)
    with pytest.raises(ValueError, match="Layer-specific"):
        replace(pull, layer_id=None)
    with pytest.raises(ValueError, match="inconsistent"):
        replace(bolt, method=MultiRowEquationMethod.BOLT_TENSION)
    with pytest.raises(ValueError, match="First-row plan method"):
        replace(first, method=MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL)
    with pytest.raises(ValueError, match="Inter-row plan method"):
        replace(interrow, method=MultiRowEquationMethod.INTERROW_ASCE_EQ_8_13)


def test_result_contract_rejects_partial_or_contradictory_numerical_state() -> None:
    calculated = calculate_multirow_connection(_bundle()).results[0]
    unavailable = calculate_multirow_connection(
        _bundle(
            checks=(
                replace(_bundle().checks[0], plan_availability=PlanAvailability.INCOMPLETE_INPUT),
            )
        )
    ).results[0]
    with pytest.raises(ValueError, match="utilization cannot be negative"):
        replace(calculated, utilization=Decimal(-1))
    with pytest.raises(ValueError, match="requires resistance"):
        replace(calculated, equation_trace=None)
    with pytest.raises(ValueError, match="requires PASS or FAIL"):
        replace(calculated, numerical_comparison=NumericalComparison.NOT_EVALUATED)
    with pytest.raises(ValueError, match="requires utilization"):
        replace(calculated, utilization=None)
    with pytest.raises(ValueError, match="cannot have utilization"):
        replace(calculated, design_resistance=PhysicalQuantity.of("0", Unit.KIP))
    zero_without_utilization = replace(
        calculated,
        design_resistance=PhysicalQuantity.of("0", Unit.KIP),
        utilization=None,
    )
    assert zero_without_utilization.design_resistance == PhysicalQuantity.of("0", Unit.KIP)
    with pytest.raises(ValueError, match="cannot retain calculated"):
        replace(calculated, availability=MultiRowResultAvailability.INCOMPLETE_INPUT)
    with pytest.raises(ValueError, match="must be NOT_EVALUATED"):
        replace(unavailable, numerical_comparison=NumericalComparison.PASS)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(calculated, input_fingerprint="BAD")

    aggregate = calculate_multirow_connection(_bundle())
    with pytest.raises(TypeError, match="MultiRowCheckResult"):
        replace(aggregate, results=cast(tuple[MultiRowCheckResult, ...], (object(),)))
    with pytest.raises(ValueError, match="must be unique"):
        replace(aggregate, required_check_ids=("A", "A"))
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(aggregate, result_fingerprint="BAD")


def test_bundle_reference_and_root_contract_validation() -> None:
    bundle = _bundle()
    with pytest.raises(TypeError, match="MultiRowPhysicalGeometryContext"):
        replace(bundle, physical_geometry=cast(MultiRowPhysicalGeometryContext, object()))
    with pytest.raises(TypeError, match="MultiRowCalculationPlanSet"):
        replace(bundle, planning_root=cast(MultiRowCalculationPlanSet, object()))
    with pytest.raises(TypeError, match="BlockShearEccentricityContext"):
        replace(bundle, eccentricity=cast(BlockShearEccentricityContext, object()))
    with pytest.raises(ValueError, match="layer ID"):
        replace(bundle, bolts=(replace(bundle.bolts[0], layer_ids=("UNKNOWN",)),))
    layer_check = replace(bundle.checks[0], layer_id="UNKNOWN")
    with pytest.raises(ValueError, match="layer ID"):
        replace(
            bundle,
            checks=(layer_check,),
            required_checks=MultiRowRequiredCheckContract((layer_check.check_id,)),
        )
    bolt_check = replace(bundle.checks[0], bolt_id="UNKNOWN")
    with pytest.raises(ValueError, match="bolt ID"):
        replace(
            bundle,
            checks=(bolt_check,),
            required_checks=MultiRowRequiredCheckContract((bolt_check.check_id,)),
        )
    interrow = next(
        item for item in bundle.checks if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    )
    bad_line = replace(interrow, bolt_line_id="UNKNOWN")
    with pytest.raises(ValueError, match="bolt-line ID"):
        replace(
            bundle,
            checks=(bad_line,),
            required_checks=MultiRowRequiredCheckContract((bad_line.check_id,)),
        )
    block = next(item for item in bundle.checks if item.family is MultiRowCheckFamily.BLOCK_SHEAR)
    with pytest.raises(ValueError, match="complete block plan"):
        replace(
            bundle,
            checks=(block,),
            required_checks=MultiRowRequiredCheckContract((block.check_id,)),
            block_shear_plans=BlockShearPlanSet((), DeferredExecutionStatus.DEFERRED_STAGE_2_4B),
        )


def test_string_uniqueness_force_hash_and_deep_immutability_guards() -> None:
    bundle = _bundle()
    with pytest.raises(ValueError, match="nonempty text"):
        MultiRowFingerprintMetadataEntry("", "value")
    with pytest.raises(TypeError, match="tuple of nonempty strings"):
        replace(bundle.layers[0], source_geometry_ids=cast(tuple[str, ...], ["A"]))
    with pytest.raises(ValueError, match="cannot be empty"):
        replace(bundle.layers[0], source_geometry_ids=())
    with pytest.raises(ValueError, match="must be unique"):
        replace(bundle.layers[0], source_geometry_ids=("A", "A"))
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(bundle, layers=cast(tuple[MultiRowLayerExecutionContext, ...], []))
    with pytest.raises(ValueError, match="force quantity"):
        replace(bundle.signed_demand, in_plane_magnitude=PhysicalQuantity.of("1", Unit.IN))
    with pytest.raises(ValueError, match="cannot be negative"):
        replace(bundle.signed_demand, in_plane_magnitude=PhysicalQuantity.of("-1", Unit.KIP))

    @dataclass
    class MutablePayload:
        value: str

    for payload, message in ((MutablePayload("x"), "non-frozen"), (object(), "unsupported")):
        metadata = MultiRowFingerprintMetadataEntry("payload", "value")
        object.__setattr__(metadata, "value", cast(str, payload))
        with pytest.raises(TypeError, match=message):
            replace(bundle, fingerprint_metadata=(metadata,))


def test_canonical_serializer_handles_dates_and_rejects_post_validation_unknown_types() -> None:
    bundle = _bundle()
    metadata = MultiRowFingerprintMetadataEntry("date", "value")
    object.__setattr__(metadata, "value", cast(str, date(2026, 1, 13)))
    object.__setattr__(bundle, "fingerprint_metadata", (metadata,))
    assert "2026-01-13" in canonical_multirow_execution_json(bundle)
    object.__setattr__(metadata, "value", cast(str, object()))
    with pytest.raises(TypeError, match="Unsupported fingerprint"):
        canonical_multirow_execution_json(bundle)


def test_resolve_end_distance_rejects_malicious_empty_row_geometry() -> None:
    geometry = _geometry()
    object.__setattr__(geometry, "rows", ())
    with pytest.raises(ValueError, match="at least one row"):
        resolve_multirow_end_distances(geometry, Unit.IN)


def test_first_row_missing_width_and_coefficient_are_invalid_geometry() -> None:
    base = _bundle()
    simplified = next(
        item for item in base.checks if item.method is MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED
    )
    simplified_plan = cast(FirstRowNetTensionPlan, simplified.first_row_plan)
    no_width_geometry = replace(simplified_plan.geometry, effective_width=None)
    no_width_plan = replace(simplified_plan, geometry=no_width_geometry)
    no_width_check = replace(simplified, first_row_plan=no_width_plan)
    assert (
        calculate_multirow_connection(_bundle(checks=(no_width_check,))).results[0].availability
        is MultiRowResultAvailability.INVALID_GEOMETRY
    )

    full = next(
        item
        for item in base.checks
        if item.method is MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL
    )
    no_coefficient_plan = replace(
        cast(FirstRowNetTensionPlan, full.first_row_plan), coefficient_inputs=None
    )
    no_coefficient_check = replace(full, first_row_plan=no_coefficient_plan)
    assert (
        calculate_multirow_connection(_bundle(checks=(no_coefficient_check,)))
        .results[0]
        .availability
        is MultiRowResultAvailability.INVALID_GEOMETRY
    )
