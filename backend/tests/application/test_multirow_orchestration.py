"""Stage 2.4C framework-independent multi-row orchestration tests."""

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast
from unittest.mock import patch

import pytest

from frp_master_connection.api.calculation_mapping import (
    map_connection_view_extents,
    map_single_bolt_preview_request,
)
from frp_master_connection.api.schemas import SingleBoltPreviewRequestDTO
from frp_master_connection.application import (
    AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION,
    AUTOMATIC_GROUP_MODE_TRACE_LAYERS,
    MULTIROW_ORCHESTRATION_CONTRACT_VERSION,
    AutomaticGroupModeIntegrationResult,
    BoltAxisTensionInput,
    EngineerDistributionKind,
    EngineerRowAllocationInput,
    MultiRowDemandSource,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    PreviewGeometryStatus,
    SingleBoltOrchestrationRequest,
    evaluate_multirow_connection,
    evaluate_multirow_connection_through_handoff,
    preview_multirow_connection,
    preview_single_bolt_connection,
)
from frp_master_connection.application import multirow_orchestration as multirow_service
from frp_master_connection.calculation import (
    BlockShearEccentricityClassification,
    ConnectedMaterialPair,
    EccentricDemandResult,
    EccentricFirstRowHandoffStatus,
    EccentricGroupModeCompatibilityInput,
    EccentricGroupModeCompatibilityResult,
    EccentricLineHandoffStatus,
    EndUseFactors,
    FirstRowPlanMethod,
    GeometryStatus,
    LapConfiguration,
    MaterialDirection,
    MethodProvenance,
    MultiRowCheckFamily,
    MultiRowEquationMethod,
    MultiRowExecutionBundle,
    MultiRowOverallDisposition,
    NumericalComparison,
    PhysicalQuantity,
    PlanAvailability,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    QualificationDisposition,
    ResistanceHandoffCoverage,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
    calculate_eccentric_bolt_group_demand,
    calculate_eccentric_group_mode_compatibility,
    calculate_eccentric_resistance_handoff,
    calculate_multirow_connection,
)
from frp_master_connection.domain import EngineeringUnitSystem
from frp_master_connection.geometry import CartesianFrame3D, Vector3D
from tests.api_fixtures import build_j1_preview_api_payload


def _request(
    *,
    rows: int = 2,
    bolts_per_row: int = 2,
    basis: RowDistributionBasis = RowDistributionBasis.ASCE_PRESCRIBED,
    angle: str = "0",
    tolerance: str = ".000001",
    display: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    allocations: tuple[EngineerRowAllocationInput, ...] = (),
    distribution_kind: EngineerDistributionKind | None = None,
    tension_required: bool = False,
) -> MultiRowOrchestrationRequest:
    return MultiRowOrchestrationRequest(
        "REQ-MR-1",
        "CONNECTION-MR-1",
        "INTERFACE-MR-1",
        "LC-1",
        "Stage 2.4C orchestration fixture",
        display,
        Unit.IN,
        rows,
        bolts_per_row,
        PhysicalQuantity.of(".5", Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("1.5", Unit.IN),
        PhysicalQuantity.of("1.5", Unit.IN),
        PhysicalQuantity.of(tolerance, Unit.IN),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                "LAYER-1",
                "COMPONENT-1",
                "ICE_LOCKED_PULTRUDED_FRP",
                PhysicalQuantity.of(".375", Unit.IN),
                PultrudedElementClassification.SHAPE,
                Decimal(angle),
                EndUseFactors(Decimal(1), Decimal(1), Decimal(1), "engineer input", ("approved",)),
                ThreadStatus.EXCLUDED,
            ),
        ),
        PhysicalQuantity.of("10", Unit.KIP),
        PhysicalQuantity.of("0", Unit.KIP),
        "CONNECTION_CENTROID",
        basis,
        distribution_kind,
        allocations,
        MethodProvenance(
            "EXTERNALLY_RESOLVED_CONNECTION_DEMAND",
            "engineer calculation",
            "1",
            "LC-1",
            "CONNECTION_CENTROID",
            True,
            basis is RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
        ),
        tension_required,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.DOUBLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        Decimal(".5"),
        PhysicalQuantity.of("0", Unit.IN),
        PhysicalQuantity.of(".000001", Unit.IN),
    )


def test_preview_is_deterministic_backend_authoritative_and_equation_free() -> None:
    request = _request()
    with patch(
        "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection"
    ) as engine:
        first = preview_multirow_connection(request)
        second = preview_multirow_connection(request)
    engine.assert_not_called()
    assert first == second
    assert first.geometry_status is GeometryStatus.VALID
    assert first.resistance_evaluated is False
    assert first.design_check_ready is True
    assert len(first.preview_fingerprint) == 64
    assert first.visualization is not None
    assert first.visualization.row_ids == ("ROW_1", "ROW_2")
    assert first.visualization.bolt_line_ids == ("BOLT_LINE_1", "BOLT_LINE_2")
    assert len(first.visualization.bolts) == 4
    assert first.visualization.unloaded_end_e1 == PhysicalQuantity.of("2", Unit.IN)
    assert first.visualization.layers[0].material_direction is MaterialDirection.LONGITUDINAL


def test_loaded_boundary_distance_translates_canonical_group_without_changing_layout() -> None:
    baseline_request = _request()
    moved_request = replace(
        baseline_request,
        loaded_boundary_to_row_1_distance=PhysicalQuantity.of("4", Unit.IN),
    )
    baseline = multirow_service._resolve(baseline_request)
    moved = multirow_service._resolve(moved_request)
    baseline_bolts = {item.id: item for item in baseline.geometry.group.bolts}
    moved_bolts = {item.id: item for item in moved.geometry.group.bolts}

    assert tuple(baseline_bolts) == tuple(moved_bolts)
    assert tuple(item.id for item in baseline.geometry.rows) == tuple(
        item.id for item in moved.geometry.rows
    )
    assert (
        baseline.geometry.classification.pitches == moved.geometry.classification.pitches == (2.0,)
    )
    assert baseline.geometry.classification.gauges == moved.geometry.classification.gauges == (2.0,)
    assert baseline.geometry.boundary.max_x == moved.geometry.boundary.max_x == 6.0
    assert moved.geometry.boundary.min_x - baseline.geometry.boundary.min_x == -2.0
    for bolt_id, baseline_bolt in baseline_bolts.items():
        moved_bolt = moved_bolts[bolt_id]
        assert moved_bolt.center.x - baseline_bolt.center.x == -2.0
        assert moved_bolt.center.y == baseline_bolt.center.y
        assert moved_bolt.bolt_diameter == baseline_bolt.bolt_diameter
        assert moved_bolt.hole_diameter == baseline_bolt.hole_diameter

    baseline_row_1 = baseline.geometry.rows[0]
    moved_row_1 = moved.geometry.rows[0]
    assert moved_row_1.projected_coordinate - baseline_row_1.projected_coordinate == -2.0
    assert moved.visualization.loaded_boundary_to_row_1_distance == PhysicalQuantity.of(
        "4", Unit.IN
    )
    assert moved.preview_fingerprint != baseline.preview_fingerprint
    assert tuple(item.path_id for item in baseline.visualization.block_paths) == tuple(
        item.path_id for item in moved.visualization.block_paths
    )


def test_pitch_gauge_and_one_bolt_line_geometry_remain_independent_of_placement() -> None:
    baseline = multirow_service._resolve(_request())
    changed_pitch = multirow_service._resolve(
        replace(_request(), pitch=PhysicalQuantity.of("3", Unit.IN))
    )
    changed_gauge = multirow_service._resolve(
        replace(_request(), gauge=PhysicalQuantity.of("3", Unit.IN))
    )
    assert changed_pitch.geometry.classification.pitches == (3.0,)
    assert changed_pitch.geometry.classification.gauges == baseline.geometry.classification.gauges
    assert changed_gauge.geometry.classification.pitches == baseline.geometry.classification.pitches
    assert changed_gauge.geometry.classification.gauges == (3.0,)

    one_line = multirow_service._resolve(_request(bolts_per_row=1))
    one_line_changed = multirow_service._resolve(
        replace(_request(bolts_per_row=1), gauge=PhysicalQuantity.of("9", Unit.IN))
    )
    assert tuple(item.center for item in one_line.geometry.group.bolts) == tuple(
        item.center for item in one_line_changed.geometry.group.bolts
    )


def _request_with_physical_connection() -> MultiRowOrchestrationRequest:
    physical_dto = SingleBoltPreviewRequestDTO.model_validate(build_j1_preview_api_payload())
    physical = map_single_bolt_preview_request(physical_dto)
    return replace(
        _request(),
        interface_id=physical.interface_id,
        physical_connection_request=physical,
        connection_view_extents=map_connection_view_extents(physical_dto),
    )


def _automatic_request(
    *,
    force: tuple[str, str, str] | None = None,
    moment: tuple[str, str, str] | None = None,
    group_local: bool = False,
    group_reference: bool = True,
    angle_degrees: str = "45",
    connection_side: str = "EXTERIOR",
) -> MultiRowOrchestrationRequest:
    payload = build_j1_preview_api_payload(
        explicit_demand=False,
        angle_degrees=angle_degrees,
        column_flange_connection_side=connection_side,
    )
    assembly = cast(dict[str, Any], payload["joint_assembly"])
    actions = cast(list[dict[str, Any]], assembly["member_end_actions"])
    action = actions[0]
    if force is not None:
        force_dto = cast(dict[str, str], action["force"])
        force_dto.update(zip(("x", "y", "z"), force, strict=True))
    if moment is not None:
        moment_dto = cast(dict[str, str], action["moment"])
        moment_dto.update(zip(("x", "y", "z"), moment, strict=True))
    if group_local:
        action["coordinate_frame_kind"] = "BOLT_GROUP_LOCAL"
        action["coordinate_frame_owner_id"] = "bolt-group-1"
        if group_reference:
            action["reference_point"] = {
                "kind": "BOLT_GROUP_ORIGIN",
                "owner_id": "bolt-group-1",
                "position": None,
            }
    physical_dto = SingleBoltPreviewRequestDTO.model_validate(payload)
    physical = map_single_bolt_preview_request(physical_dto)
    return replace(
        _request(),
        interface_id=physical.interface_id,
        load_combination_id="LC-1",
        signed_force_x=None,
        signed_force_y=None,
        force_reference=None,
        demand_source=MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE,
        automatic_action_source_id="action-1",
        physical_connection_request=physical,
        connection_view_extents=map_connection_view_extents(physical_dto),
    )


def test_automatic_preview_calls_demand_once_and_zero_resistance() -> None:
    request = _automatic_request()
    with (
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_bolt_group_demand",
            wraps=calculate_eccentric_bolt_group_demand,
        ) as demand_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_resistance_handoff"
        ) as handoff_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_group_mode_compatibility"
        ) as group_mode_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection"
        ) as resistance_engine,
    ):
        preview = preview_multirow_connection(request)
    demand_engine.assert_called_once()
    handoff_engine.assert_not_called()
    group_mode_engine.assert_not_called()
    resistance_engine.assert_not_called()
    assert preview.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE
    assert preview.resistance_evaluated is False
    assert preview.automatic_demand_result is not None
    assert preview.visualization is not None
    assert len(preview.visualization.automatic_bolt_demands) == 4
    assert all(item.total_axis is not None for item in preview.visualization.automatic_bolt_demands)
    assert "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL" in preview.warnings


def test_handoff_only_adapter_rejects_wrong_mode_and_fails_closed_before_execution() -> None:
    with pytest.raises(ValueError, match="requires automatic member-end demand"):
        evaluate_multirow_connection_through_handoff(_request())

    automatic = _automatic_request(moment=("0", "0", "0"))
    with patch.object(multirow_service, "_resolve", side_effect=ValueError("invalid handoff")):
        unresolved = evaluate_multirow_connection_through_handoff(automatic)
    assert unresolved.preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert unresolved.calculation_result is None

    resolved = multirow_service._resolve(automatic)
    bundle = multirow_service._execution_bundle(automatic, resolved)
    demand = multirow_service._automatic_demand(automatic, resolved, bundle)
    invalid_preview = replace(
        multirow_service._preview_from_resolved(automatic, resolved, demand),
        geometry_status=GeometryStatus.INVALID_GEOMETRY,
    )
    with patch.object(
        multirow_service,
        "_preview_from_resolved",
        return_value=invalid_preview,
    ):
        invalid = evaluate_multirow_connection_through_handoff(automatic)
    assert invalid.preview is invalid_preview
    assert invalid.automatic_demand_result is not None
    assert invalid.calculation_result is None


def test_automatic_design_uses_demand_and_handoff_once_without_direct_resistance_call() -> None:
    request = _automatic_request()
    group_inputs: list[EccentricGroupModeCompatibilityInput] = []
    group_outputs: list[EccentricGroupModeCompatibilityResult] = []

    def calculate_group_mode(
        value: EccentricGroupModeCompatibilityInput,
    ) -> EccentricGroupModeCompatibilityResult:
        group_inputs.append(value)
        result = calculate_eccentric_group_mode_compatibility(value)
        group_outputs.append(result)
        return result

    with (
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_bolt_group_demand",
            wraps=calculate_eccentric_bolt_group_demand,
        ) as demand_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_resistance_handoff",
            wraps=calculate_eccentric_resistance_handoff,
        ) as handoff_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration."
            "calculate_eccentric_group_mode_compatibility",
            side_effect=calculate_group_mode,
        ) as group_mode_engine,
        patch(
            "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection"
        ) as direct_resistance,
    ):
        response = evaluate_multirow_connection(request)
    demand_engine.assert_called_once()
    handoff_engine.assert_called_once()
    group_mode_engine.assert_called_once()
    direct_resistance.assert_not_called()
    assert response.calculation_result is None
    assert len(response.automatic_handoff_results) == 1
    handoff = response.automatic_handoff_results[0]
    assert handoff.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    assert handoff.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert handoff.parent_action_transfer_warnings
    integration = response.automatic_group_mode_integration
    assert integration is not None
    assert integration.scenario_results[0] is group_outputs[0]
    assert group_inputs[0].parent_handoff_input.demand_result is response.automatic_demand_result
    assert group_inputs[0].parent_handoff_result is handoff
    assert integration.trace_layers == AUTOMATIC_GROUP_MODE_TRACE_LAYERS
    assert integration.integration_contract_version == (
        AUTOMATIC_GROUP_MODE_INTEGRATION_CONTRACT_VERSION
    )


def test_automatic_collinear_action_reaches_full_legacy_handoff() -> None:
    request = _automatic_request(
        force=("0", ".7", "0"),
        moment=("0", "0", "0"),
        group_local=True,
    )
    response = evaluate_multirow_connection(request)
    assert response.automatic_demand_result is not None
    scenario = response.automatic_demand_result.scenarios[0]
    assert scenario.external_moment.magnitude == 0
    assert scenario.direct_distribution_moment.magnitude == 0
    assert scenario.residual_moment.magnitude == 0
    handoff = response.automatic_handoff_results[0]
    assert handoff.coverage is ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR
    assert handoff.legacy_result is not None
    assert response.calculation_result == handoff.legacy_result
    integration = response.automatic_group_mode_integration
    assert integration is not None
    group_mode = integration.scenario_results[0]
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.INHERITED_LEGACY_STAGE_2_4B
        for item in group_mode.line_results
    )
    assert (
        group_mode.first_row_compatibility.status
        is EccentricFirstRowHandoffStatus.INHERITED_LEGACY_STAGE_2_4B
    )


def test_small_eccentric_lines_pass_but_unsupported_first_row_blocks_ordinary_pass() -> None:
    response = evaluate_multirow_connection(
        _automatic_request(
            force=("0", ".7", "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    )
    integration = response.automatic_group_mode_integration
    assert integration is not None
    group_mode = integration.scenario_results[0]
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT
        for item in group_mode.line_results
    )
    assert all(
        item.shear_out_result is not None
        and item.shear_out_result.numerical_comparison is NumericalComparison.PASS
        for item in group_mode.line_results
    )
    assert (
        group_mode.first_row_compatibility.status
        is EccentricFirstRowHandoffStatus.CALCULATION_NOT_SUPPORTED
    )
    assert integration.numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert integration.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert not integration.failed_check_ids


def test_large_eccentric_known_shear_out_failure_controls_whole_result() -> None:
    response = evaluate_multirow_connection(
        _automatic_request(
            force=("0", "20", "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    )
    integration = response.automatic_group_mode_integration
    assert integration is not None
    assert integration.failed_check_ids
    assert integration.numerical_comparison is NumericalComparison.FAIL
    assert integration.overall_disposition is MultiRowOverallDisposition.FAIL
    assert any(
        item.shear_out_result is not None
        and item.shear_out_result.numerical_comparison is NumericalComparison.FAIL
        for item in integration.scenario_results[0].line_results
    )


def test_reversed_eccentric_line_state_remains_structured_and_without_resistance() -> None:
    request = replace(
        _automatic_request(
            force=("0", "0", ".7"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        ),
        loaded_boundary_to_row_1_distance=PhysicalQuantity.of("1", Unit.IN),
    )
    integration = evaluate_multirow_connection(request).automatic_group_mode_integration
    assert integration is not None
    reversed_line = integration.scenario_results[0].line_results[0]
    assert reversed_line.handoff_status is EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED
    assert reversed_line.required_line_demand is None
    assert reversed_line.shear_out_result is None
    assert [item.code.value for item in reversed_line.warnings] == [
        "ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED"
    ]


def test_group_mode_integration_fingerprint_is_stable_unit_invariant_and_sensitive() -> None:
    request = _automatic_request(
        force=("0", ".7", "0"),
        moment=("0", "0", "0"),
        group_local=True,
        group_reference=False,
    )
    first = evaluate_multirow_connection(request).automatic_group_mode_integration
    second = evaluate_multirow_connection(request).automatic_group_mode_integration
    display_si = evaluate_multirow_connection(
        replace(request, display_unit_system=EngineeringUnitSystem.SI)
    ).automatic_group_mode_integration
    changed = evaluate_multirow_connection(
        _automatic_request(
            force=("0", ".8", "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    ).automatic_group_mode_integration
    assert first is not None
    assert second is not None
    assert display_si is not None
    assert changed is not None
    assert first.result_fingerprint == second.result_fingerprint == display_si.result_fingerprint
    assert first.result_fingerprint != changed.result_fingerprint


def test_automatic_more_than_three_row_qualification_reaches_group_mode_integration() -> None:
    response = evaluate_multirow_connection(
        replace(
            _automatic_request(
                force=("0", ".7", "0"),
                moment=("0", "0", "0"),
                group_local=True,
                group_reference=False,
            ),
            row_count=4,
            row_distribution_basis=RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        )
    )
    integration = response.automatic_group_mode_integration
    assert integration is not None
    assert integration.qualification.value == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    assert integration.overall_disposition in {
        MultiRowOverallDisposition.FAIL,
        MultiRowOverallDisposition.NOT_EVALUATED,
    }


def _group_mode_result_for_merge() -> EccentricGroupModeCompatibilityResult:
    response = evaluate_multirow_connection(
        _automatic_request(
            force=("0", ".7", "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    )
    integration = response.automatic_group_mode_integration
    assert integration is not None
    return integration.scenario_results[0]


def test_group_mode_application_merge_status_precedence_and_qualification_paths() -> None:
    source = _group_mode_result_for_merge()
    clean = replace(
        source,
        required_check_ids=(),
        not_required_check_ids=(),
        unsupported_required_check_ids=(),
        incomplete_required_check_ids=(),
        failed_check_ids=(),
        qualification=QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE,
        numerical_comparison=NumericalComparison.PASS,
        governing_supported_check_ids=(),
        overall_disposition=MultiRowOverallDisposition.PASS,
    )
    passed = multirow_service._integrate_group_mode_results((clean,))
    assert passed.overall_disposition is MultiRowOverallDisposition.PASS

    review = multirow_service._integrate_group_mode_results(
        (
            replace(
                clean,
                qualification=QualificationDisposition.ENGINEERING_REVIEW_REQUIRED,
                overall_disposition=MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED,
            ),
        )
    )
    assert review.overall_disposition is MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED

    qualification = multirow_service._integrate_group_mode_results(
        (
            replace(
                clean,
                qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
                overall_disposition=(
                    MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
                ),
            ),
        )
    )
    assert qualification.overall_disposition is (
        MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )

    invalid = multirow_service._integrate_group_mode_results(
        (
            replace(
                clean,
                numerical_comparison=NumericalComparison.NOT_EVALUATED,
                overall_disposition=MultiRowOverallDisposition.INVALID_GEOMETRY,
            ),
        )
    )
    assert invalid.overall_disposition is MultiRowOverallDisposition.INVALID_GEOMETRY

    unevaluated = multirow_service._integrate_group_mode_results(
        (replace(clean, numerical_comparison=NumericalComparison.NOT_EVALUATED),)
    )
    assert unevaluated.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    with pytest.raises(ValueError, match="at least one"):
        multirow_service._integrate_group_mode_results(())


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("integration_contract_version", "wrong", "approved identity"),
        ("scenario_results", (), "at least one scenario"),
        ("required_check_ids", ("",), "unique nonblank"),
        ("not_required_check_ids", ("CHECK", "CHECK"), "unique nonblank"),
        ("unsupported_required_check_ids", ("",), "unique nonblank"),
        ("incomplete_required_check_ids", ("",), "unique nonblank"),
        ("failed_check_ids", ("",), "unique nonblank"),
        ("governing_supported_check_ids", ("",), "unique nonblank"),
        ("trace_layers", (), "complete and ordered"),
        ("result_fingerprint", "not-a-sha", "lowercase SHA-256"),
    ],
)
def test_group_mode_integration_contract_rejects_invalid_internal_state(
    field_name: str, value: object, message: str
) -> None:
    integration = multirow_service._integrate_group_mode_results((_group_mode_result_for_merge(),))
    with pytest.raises(ValueError, match=message):
        replace(integration, **{field_name: value})  # type: ignore[arg-type]


def test_group_mode_integration_contract_rejects_duplicate_scenario_ids() -> None:
    integration = multirow_service._integrate_group_mode_results((_group_mode_result_for_merge(),))
    scenario = integration.scenario_results[0]
    with pytest.raises(ValueError, match="scenario identities"):
        AutomaticGroupModeIntegrationResult(
            integration.integration_contract_version,
            (scenario, scenario),
            integration.required_check_ids,
            integration.not_required_check_ids,
            integration.unsupported_required_check_ids,
            integration.incomplete_required_check_ids,
            integration.failed_check_ids,
            integration.qualification,
            integration.numerical_comparison,
            integration.governing_supported_check_ids,
            integration.overall_disposition,
            integration.trace_layers,
            integration.result_fingerprint,
        )


@pytest.mark.parametrize(("force_u", "sign"), [(".7", 1), ("-.7", -1)])
def test_automatic_positive_and_negative_eccentricity_remain_partial(
    force_u: str, sign: int
) -> None:
    response = evaluate_multirow_connection(
        _automatic_request(
            force=("0", force_u, "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    )
    demand = cast(EccentricDemandResult, response.automatic_demand_result)
    assert demand.scenarios[0].residual_moment.magnitude * sign > 0
    assert (
        response.automatic_handoff_results[0].coverage
        is ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    )


def test_automatic_tiny_real_reference_eccentricity_is_not_discarded() -> None:
    request = _automatic_request(
        force=("0", ".7", "0"),
        moment=("0", "0", "0"),
        group_local=True,
    )
    resolved = multirow_service._resolve(request)
    value = multirow_service._automatic_demand_input(
        request,
        resolved,
        multirow_service._execution_bundle(request, resolved),
    )
    tiny = Decimal(".000000000001")
    offset_point = multirow_service._exact_decimal_vector(
        cast(
            tuple[Decimal, Decimal, Decimal],
            tuple(tiny * component for component in value.interface_frame.v),
        ),
        Unit.IN,
    )
    eccentric = calculate_eccentric_bolt_group_demand(
        replace(value, force_reference_point=offset_point)
    )
    assert eccentric.scenarios[0].residual_moment.magnitude != 0


@pytest.mark.parametrize(
    ("force", "angle_degrees", "connection_side"),
    [
        (("0", "-.7", "0"), "45", "EXTERIOR"),
        (("0", ".7", "0"), "135", "EXTERIOR"),
        (("0", ".7", "0"), "45", "WEB_SIDE"),
    ],
)
def test_automatic_collinear_force_reversal_and_basis_variants_are_deterministic(
    force: tuple[str, str, str], angle_degrees: str, connection_side: str
) -> None:
    request = _automatic_request(
        force=force,
        moment=("0", "0", "0"),
        group_local=True,
        angle_degrees=angle_degrees,
        connection_side=connection_side,
    )
    first = evaluate_multirow_connection(request)
    second = evaluate_multirow_connection(request)
    demand = cast(EccentricDemandResult, first.automatic_demand_result)
    assert demand.scenarios[0].residual_moment.magnitude == 0
    assert (
        first.automatic_handoff_results[0].coverage
        is ResistanceHandoffCoverage.FULL_LEGACY_COLLINEAR
    )
    assert first == second


def test_automatic_template_input_ignores_platform_float_basis_reconstruction() -> None:
    request = _automatic_request(
        force=("0", ".7", "0"),
        moment=("0", "0", "0"),
        group_local=True,
    )
    resolved = multirow_service._resolve(request)
    bundle = multirow_service._execution_bundle(request, resolved)
    frame = cast(CartesianFrame3D, resolved.authority.group_frame)
    perturbed_row = Vector3D(0.0, -0.7071067811865476, 0.7071067811865475).normalized()
    perturbed_line = frame.x_axis.cross(perturbed_row).normalized()
    perturbed_row = perturbed_line.cross(frame.x_axis).normalized()
    perturbed = CartesianFrame3D(
        frame.origin,
        frame.x_axis,
        perturbed_row,
        perturbed_line,
    )
    alternate = replace(
        resolved,
        authority=replace(resolved.authority, group_frame=perturbed),
    )
    with patch.object(
        multirow_service,
        "_exact_axis",
        side_effect=AssertionError("template-local calculation must not adapt float axes"),
    ):
        first_input = multirow_service._automatic_demand_input(request, resolved, bundle)
        alternate_input = multirow_service._automatic_demand_input(request, alternate, bundle)
    assert first_input == alternate_input
    first = calculate_eccentric_bolt_group_demand(first_input)
    second = calculate_eccentric_bolt_group_demand(alternate_input)
    assert first == second
    assert first.scenarios[0].residual_moment.magnitude == 0


def test_decimal_template_basis_covers_cardinal_wrapped_and_fallback_inputs() -> None:
    assert multirow_service._decimal_sine_cosine_degrees(Decimal(0)) == (
        Decimal(0),
        Decimal(1),
    )
    assert multirow_service._decimal_sine_cosine_degrees(Decimal(90)) == (
        Decimal(1),
        Decimal(0),
    )
    assert multirow_service._decimal_sine_cosine_degrees(Decimal(180)) == (
        Decimal(0),
        Decimal(-1),
    )
    assert multirow_service._decimal_sine_cosine_degrees(Decimal(270)) == (
        Decimal(-1),
        Decimal(0),
    )
    wrapped_sine, wrapped_cosine = multirow_service._decimal_sine_cosine_degrees(Decimal(225))
    assert wrapped_sine < 0
    assert wrapped_cosine < 0

    physical = cast(
        SingleBoltOrchestrationRequest,
        _automatic_request().physical_connection_request,
    )
    assert (
        multirow_service._exact_template_group_axes(replace(physical, template_orientation=None))
        is None
    )
    orientation = physical.template_orientation
    assert orientation is not None
    assert (
        multirow_service._exact_template_group_axes(
            replace(
                physical,
                template_orientation=replace(
                    orientation,
                    plan_angle_degrees=Decimal(1),
                ),
            )
        )
        is None
    )


def test_automatic_eccentric_action_is_partial_and_group_checks_fail_closed() -> None:
    request = _automatic_request(moment=("0", "0", "0"))
    response = evaluate_multirow_connection(request)
    assert response.automatic_demand_result is not None
    handoff = response.automatic_handoff_results[0]
    assert handoff.coverage is ResistanceHandoffCoverage.PARTIAL_ECCENTRIC
    assert handoff.supported_results
    assert handoff.unsupported_required_check_ids
    assert handoff.overall_disposition in {
        MultiRowOverallDisposition.FAIL,
        MultiRowOverallDisposition.NOT_EVALUATED,
    }


def test_automatic_normal_force_requires_explicit_axis_demand_without_generation() -> None:
    request = _automatic_request(
        force=("1", ".7", "0"),
        moment=("0", "0", "0"),
        group_local=True,
    )
    response = evaluate_multirow_connection(request)
    demand = response.automatic_demand_result
    assert demand is not None
    assert demand.projected_force.n.magnitude != 0
    assert any(
        item.code.value == "OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND"
        for item in demand.warnings
    )
    handoff = response.automatic_handoff_results[0]
    assert handoff.coverage is ResistanceHandoffCoverage.BLOCKED_INCOMPLETE_ACTION_TRANSFER
    assert handoff.incomplete_required_check_ids
    axis_checks = [
        item for item in handoff.checks if item.demand_source.value == "EXPLICIT_BOLT_AXIS_TENSION"
    ]
    assert axis_checks
    assert all(item.resistance_result is None for item in axis_checks)


def test_automatic_fingerprints_are_deterministic_and_action_sensitive() -> None:
    request = _automatic_request(moment=("0", "0", "0"))
    first = evaluate_multirow_connection(request)
    second = evaluate_multirow_connection(request)
    changed = evaluate_multirow_connection(
        _automatic_request(force=(".8", "0", "0"), moment=("0", "0", "0"))
    )
    assert first == second
    assert first.automatic_demand_result is not None
    assert changed.automatic_demand_result is not None
    assert first.preview.preview_fingerprint == second.preview.preview_fingerprint
    assert (
        first.automatic_demand_result.input_fingerprint
        != changed.automatic_demand_result.input_fingerprint
    )


def test_demand_source_contract_rejects_every_ambiguous_application_shape() -> None:
    explicit = _request()
    with pytest.raises(TypeError, match="demand_source"):
        replace(explicit, demand_source=cast(Any, "AUTOMATIC_MEMBER_END_FORCE"))
    with pytest.raises(ValueError, match="Explicit demand requires"):
        replace(explicit, signed_force_x=None)
    with pytest.raises(ValueError, match="cannot include automatic"):
        replace(explicit, automatic_action_source_id="action-1")
    with pytest.raises(ValueError, match="physical connection context"):
        replace(
            explicit,
            demand_source=MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE,
            signed_force_x=None,
            signed_force_y=None,
            force_reference=None,
        )

    automatic = _automatic_request()
    with pytest.raises(ValueError, match="cannot include explicit"):
        replace(automatic, signed_force_x=PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="action-source identity"):
        replace(automatic, automatic_action_source_id=" ")
    with pytest.raises(ValueError, match="must match physical"):
        replace(automatic, automatic_action_source_id="other-action")


def test_automatic_action_resolution_fails_closed_for_invalid_sources() -> None:
    automatic = _automatic_request()
    physical = automatic.physical_connection_request
    assert physical is not None
    missing_source = replace(physical, source_action_id="missing-action")
    missing = replace(
        automatic,
        automatic_action_source_id="missing-action",
        physical_connection_request=missing_source,
    )
    assert "does not exist" in preview_multirow_connection(missing).warnings[0]
    assert (
        "load combination"
        in preview_multirow_connection(replace(automatic, load_combination_id="OTHER-LC")).warnings[
            0
        ]
    )
    normal_only = _automatic_request(
        force=("1", "0", "0"),
        moment=("0", "0", "0"),
        group_local=True,
    )
    assert (
        "no resolvable in-plane component" in preview_multirow_connection(normal_only).warnings[0]
    )


def test_automatic_layer_axes_block_compatibility_and_defensive_visualization_paths() -> None:
    automatic = _automatic_request(moment=("0", "0", "0"))
    layers = automatic.layers
    perpendicular = replace(layers[0], material_axis_angle_degrees=Decimal("90"))
    oblique = replace(layers[0], material_axis_angle_degrees=Decimal("30"))
    assert evaluate_multirow_connection(
        replace(automatic, layers=(perpendicular,))
    ).automatic_handoff_results
    assert evaluate_multirow_connection(
        replace(automatic, layers=(oblique,))
    ).automatic_handoff_results
    assert evaluate_multirow_connection(
        _automatic_request(
            force=("0", ".7", "0"),
            moment=("0", "0", "0"),
            group_local=True,
            group_reference=False,
        )
    ).automatic_handoff_results

    resolved = multirow_service._resolve(automatic)
    bundle = multirow_service._execution_bundle(automatic, resolved)
    demand = multirow_service._automatic_demand(automatic, resolved, bundle)
    scenario = demand.scenarios[0]
    assert (
        multirow_service._block_shear_compatibility(
            automatic,
            resolved,
            replace(bundle, eccentricity=None),
            demand,
            scenario,
        )
        is None
    )
    actual_offset = abs(
        scenario.external_moment.canonical_magnitude / resolved.total_demand.canonical_magnitude
    )
    matched_request = replace(
        automatic,
        force_line_offset=PhysicalQuantity.of(actual_offset, Unit.MM).to(Unit.IN),
    )
    assert (
        multirow_service._block_shear_compatibility(
            matched_request, resolved, bundle, demand, scenario
        )
        is not None
    )

    without_frame = replace(resolved, authority=replace(resolved.authority, group_frame=None))
    assert multirow_service._automatic_bolt_visualization(without_frame, demand) == ()
    first = scenario.per_bolt[0]
    zero_force = replace(
        first.total_force,
        u=PhysicalQuantity.of(0, first.total_force.u.unit),
        v=PhysicalQuantity.of(0, first.total_force.v.unit),
    )
    zero_bolt = replace(
        first,
        total_force=zero_force,
        total_force_magnitude=PhysicalQuantity.of(0, first.total_force_magnitude.unit),
    )
    missing_bolt = replace(scenario.per_bolt[1], bolt_id="missing-bolt")
    modified_demand = replace(
        demand,
        scenarios=(replace(scenario, per_bolt=(zero_bolt, missing_bolt, *scenario.per_bolt[2:])),),
    )
    vectors = multirow_service._automatic_bolt_visualization(resolved, modified_demand)
    assert len(vectors) == 3
    assert vectors[0].total_axis is None

    no_action = replace(resolved, authority=replace(resolved.authority, resolved_action=None))
    with pytest.raises(ValueError, match="resolved canonical action"):
        multirow_service._automatic_demand_input(automatic, no_action, bundle)


def test_physical_connection_context_must_match_multirow_identity_and_units() -> None:
    request = _request_with_physical_connection()
    with pytest.raises(ValueError, match="interface identity"):
        replace(request, interface_id="OTHER-INTERFACE")
    with pytest.raises(ValueError, match="source units"):
        replace(request, source_length_unit=Unit.MM)
    with pytest.raises(ValueError, match="bolt diameter"):
        replace(request, bolt_diameter=PhysicalQuantity.of("0.75", Unit.IN))


def test_preview_places_every_multirow_bolt_on_the_canonical_physical_connection() -> None:
    request = _request_with_physical_connection()
    with patch(
        "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection"
    ) as engine:
        preview = preview_multirow_connection(request)
    engine.assert_not_called()
    assert preview.geometry_status is GeometryStatus.VALID
    assert preview.resistance_evaluated is False
    assert preview.visualization is not None
    assert preview.visualization.physical_connection is not None
    bolts = preview.visualization.physical_bolts
    assert tuple(item.bolt_id for item in bolts) == (
        "B_R1_L1",
        "B_R1_L2",
        "B_R2_L1",
        "B_R2_L2",
    )
    assert len({item.display.center for item in bolts}) == 4
    assert all(item.penetrated_layer_ids == ("layer-A", "layer-B") for item in bolts)
    assert all(len(item.display.holes) == 2 for item in bolts)
    assert all(len(item.display.washers) == 2 for item in bolts)
    demand = preview.visualization.connection_demand
    assert demand is not None
    assert demand.reference_point_id == "MULTIROW_CONNECTION_DEMAND_REFERENCE"
    assert demand.resultant == PhysicalQuantity.of("10", Unit.KIP)
    assert demand.axis.norm == pytest.approx(1.0)


def test_loaded_boundary_translation_reaches_every_physical_bolt_and_hardware_surface() -> None:
    request = _request_with_physical_connection()
    baseline = preview_multirow_connection(request)
    moved = preview_multirow_connection(
        replace(
            request,
            loaded_boundary_to_row_1_distance=PhysicalQuantity.of("4", Unit.IN),
        )
    )
    assert baseline.visualization is not None
    assert moved.visualization is not None
    assert baseline.visualization.physical_connection is not None
    assert moved.visualization.physical_connection is not None
    assert baseline.visualization.physical_connection == moved.visualization.physical_connection
    baseline_bolts = {item.bolt_id: item for item in baseline.visualization.physical_bolts}
    moved_bolts = {item.bolt_id: item for item in moved.visualization.physical_bolts}
    assert tuple(baseline_bolts) == tuple(moved_bolts)
    frame = next(
        item.frame
        for item in baseline.visualization.physical_connection.frames
        if item.kind.value == "BOLT_GROUP_LOCAL"
    )
    expected = tuple(-2.0 * value for value in (frame.y_axis.x, frame.y_axis.y, frame.y_axis.z))
    for bolt_id, baseline_bolt in baseline_bolts.items():
        moved_bolt = moved_bolts[bolt_id]
        actual = tuple(
            getattr(moved_bolt.display.center, axis) - getattr(baseline_bolt.display.center, axis)
            for axis in ("x", "y", "z")
        )
        assert actual == pytest.approx(expected)
        assert moved_bolt.display.bolt_diameter == baseline_bolt.display.bolt_diameter
        assert tuple(item.diameter for item in moved_bolt.display.holes) == tuple(
            item.diameter for item in baseline_bolt.display.holes
        )
        assert tuple(item.outside_diameter for item in moved_bolt.display.washers) == tuple(
            item.outside_diameter for item in baseline_bolt.display.washers
        )
        for baseline_hole, moved_hole in zip(
            baseline_bolt.display.holes, moved_bolt.display.holes, strict=True
        ):
            for point_name in ("start", "end"):
                baseline_point = getattr(baseline_hole, point_name)
                moved_point = getattr(moved_hole, point_name)
                assert tuple(
                    getattr(moved_point, axis) - getattr(baseline_point, axis)
                    for axis in ("x", "y", "z")
                ) == pytest.approx(expected)
        for baseline_washer, moved_washer in zip(
            baseline_bolt.display.washers, moved_bolt.display.washers, strict=True
        ):
            for point_name in ("start", "end"):
                baseline_point = getattr(baseline_washer, point_name)
                moved_point = getattr(moved_washer, point_name)
                assert tuple(
                    getattr(moved_point, axis) - getattr(baseline_point, axis)
                    for axis in ("x", "y", "z")
                ) == pytest.approx(expected)


def test_loaded_boundary_translation_reaches_automatic_centroid_and_fingerprints() -> None:
    request = _automatic_request(moment=("0", "0", "0"))
    baseline = preview_multirow_connection(request)
    moved = preview_multirow_connection(
        replace(
            request,
            loaded_boundary_to_row_1_distance=PhysicalQuantity.of("4", Unit.IN),
        )
    )
    baseline_demand = cast(EccentricDemandResult, baseline.automatic_demand_result)
    moved_demand = cast(EccentricDemandResult, moved.automatic_demand_result)
    assert moved_demand.geometric_bolt_centroid.u.to(
        Unit.IN
    ).magnitude - baseline_demand.geometric_bolt_centroid.u.to(Unit.IN).magnitude == Decimal("-2")
    assert moved_demand.geometric_bolt_centroid.v == baseline_demand.geometric_bolt_centroid.v
    assert moved_demand.input_fingerprint != baseline_demand.input_fingerprint
    assert moved.preview_fingerprint != baseline.preview_fingerprint


def test_physical_connection_snapshot_supports_absent_or_short_view_extents() -> None:
    request = _request_with_physical_connection()
    without_extents = preview_multirow_connection(replace(request, connection_view_extents=None))
    assert without_extents.geometry_status is GeometryStatus.VALID
    extents = request.connection_view_extents
    assert extents is not None
    short_extents = preview_multirow_connection(
        replace(request, connection_view_extents=replace(extents, brace_view_length=1.0))
    )
    assert short_extents.geometry_status is GeometryStatus.VALID


@pytest.mark.parametrize("failure", ["missing-visualization", "unsupported", "missing-frame"])
def test_physical_connection_snapshot_fails_closed_on_incomplete_context(failure: str) -> None:
    request = _request_with_physical_connection()
    physical_request = request.physical_connection_request
    assert physical_request is not None
    physical = preview_single_bolt_connection(physical_request)
    visualization = physical.visualization
    assert visualization is not None
    if failure == "missing-visualization":
        returned = replace(physical, visualization=None)
    elif failure == "unsupported":
        returned = replace(physical, geometry_status=PreviewGeometryStatus.UNSUPPORTED)
    else:
        returned = replace(
            physical,
            visualization=replace(
                visualization,
                frames=tuple(
                    frame
                    for frame in visualization.frames
                    if not (
                        frame.kind.value == "BOLT_GROUP_LOCAL"
                        and frame.owner_id == visualization.bolt_group_id
                    )
                ),
            ),
        )
    with patch(
        "frp_master_connection.application.multirow_orchestration.preview_single_bolt_connection",
        return_value=returned,
    ):
        response = preview_multirow_connection(request)
    assert response.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert response.design_check_ready is False


def test_invalid_physical_connection_blocks_multirow_design_without_equations() -> None:
    request = _request_with_physical_connection()
    physical_request = request.physical_connection_request
    assert physical_request is not None
    physical = preview_single_bolt_connection(physical_request)
    visualization = physical.visualization
    assert visualization is not None
    orientation = visualization.connection_orientation
    assert orientation is not None
    invalid_visualization = replace(
        visualization,
        connection_orientation=replace(
            orientation,
            geometry_valid=False,
            interference_participant_ids=("member-a", "member-b"),
        ),
    )
    invalid_physical = replace(
        physical,
        geometry_status=PreviewGeometryStatus.INVALID_GEOMETRY,
        visualization=invalid_visualization,
    )
    with (
        patch(
            "frp_master_connection.application.multirow_orchestration.preview_single_bolt_connection",
            return_value=invalid_physical,
        ),
        patch(
            "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection"
        ) as engine,
    ):
        response = evaluate_multirow_connection(request)
    engine.assert_not_called()
    assert response.preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert response.preview.visualization is not None
    assert response.preview.design_check_ready is False
    assert response.calculation_result is None
    assert "INVALID_PHYSICAL_CONNECTION_GEOMETRY:member-a,member-b" in response.preview.warnings


def test_invalid_physical_connection_blocks_automatic_resistance_after_demand_preview() -> None:
    request = _automatic_request(moment=("0", "0", "0"))
    physical_request = request.physical_connection_request
    assert physical_request is not None
    physical = preview_single_bolt_connection(physical_request)
    visualization = physical.visualization
    assert visualization is not None
    orientation = visualization.connection_orientation
    assert orientation is not None
    invalid_physical = replace(
        physical,
        geometry_status=PreviewGeometryStatus.INVALID_GEOMETRY,
        visualization=replace(
            visualization,
            connection_orientation=replace(
                orientation,
                geometry_valid=False,
                interference_participant_ids=("member-a", "member-b"),
            ),
        ),
    )
    with patch(
        "frp_master_connection.application.multirow_orchestration.preview_single_bolt_connection",
        return_value=invalid_physical,
    ):
        response = evaluate_multirow_connection(request)
    assert response.preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert response.automatic_demand_result is not None
    assert response.automatic_handoff_results == ()
    assert response.calculation_result is None


def test_design_calls_verified_engine_once_and_returns_complete_result() -> None:
    with patch(
        "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection",
        wraps=calculate_multirow_connection,
    ) as engine:
        response = evaluate_multirow_connection(_request())
    engine.assert_called_once()
    assert response.orchestration_contract_version == MULTIROW_ORCHESTRATION_CONTRACT_VERSION
    assert response.calculation_result is not None
    result = response.calculation_result
    assert result.overall_disposition in {
        MultiRowOverallDisposition.FAIL,
        MultiRowOverallDisposition.INCOMPLETE_OR_UNSUPPORTED,
    }
    assert result.input_fingerprint
    assert result.result_fingerprint
    assert any(item.limit_state is MultiRowCheckFamily.PIN_BEARING for item in result.results)
    assert any(item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR for item in result.results)
    assert any(
        item.limit_state is MultiRowCheckFamily.FIRST_ROW_NET_TENSION for item in result.results
    )


@pytest.mark.parametrize("rows", [2, 3])
def test_prescribed_two_and_three_row_cases_are_supported(rows: int) -> None:
    preview = preview_multirow_connection(_request(rows=rows))
    assert preview.geometry_status is GeometryStatus.VALID
    assert preview.design_check_ready is True
    assert preview.visualization is not None
    assert len(preview.visualization.row_ids) == rows


def test_three_row_frp_steel_prescribed_case_is_supported() -> None:
    request = replace(_request(rows=3), material_pair=ConnectedMaterialPair.FRP_STEEL)
    response = evaluate_multirow_connection(request)
    assert response.calculation_result is not None
    assert response.calculation_result.method_applicability.value == "ASCE_PRESCRIPTIVE"


def test_four_row_rational_extension_and_more_than_three_bolts_are_fail_closed() -> None:
    four_rows = evaluate_multirow_connection(
        _request(rows=4, basis=RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE)
    )
    assert four_rows.calculation_result is not None
    assert four_rows.calculation_result.qualification.value == (
        "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    )
    assert any("ROW_LIMIT" in item for item in four_rows.preview.warnings)
    wide = evaluate_multirow_connection(_request(bolts_per_row=4))
    assert wide.calculation_result is not None
    assert "MORE_THAN_THREE_BOLTS_PER_ROW_FIRST_ROW_CHECK_UNSUPPORTED" in wide.preview.warnings
    first = next(
        item
        for item in wide.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
    )
    assert first.availability.value == "CALCULATION_NOT_SUPPORTED"


@pytest.mark.parametrize(
    ("kind", "allocations"),
    [
        (
            EngineerDistributionKind.FRACTIONS,
            (
                EngineerRowAllocationInput(1, Decimal(".7")),
                EngineerRowAllocationInput(2, Decimal(".3")),
            ),
        ),
        (
            EngineerDistributionKind.DIRECT_ROW_FORCES,
            (
                EngineerRowAllocationInput(1, direct_force=PhysicalQuantity.of("7", Unit.KIP)),
                EngineerRowAllocationInput(2, direct_force=PhysicalQuantity.of("3", Unit.KIP)),
            ),
        ),
    ],
)
def test_engineer_defined_distributions_preserve_qualification(
    kind: EngineerDistributionKind,
    allocations: tuple[EngineerRowAllocationInput, ...],
) -> None:
    response = evaluate_multirow_connection(
        _request(
            basis=RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            distribution_kind=kind,
            allocations=allocations,
        )
    )
    assert response.calculation_result is not None
    assert response.calculation_result.method_applicability.value.startswith("ENGINEER_DEFINED")


def test_material_direction_display_only_units_and_invalid_geometry_are_separate() -> None:
    transverse = preview_multirow_connection(_request(angle="90"))
    assert transverse.visualization is not None
    assert transverse.visualization.layers[0].material_direction is MaterialDirection.TRANSVERSE
    us = preview_multirow_connection(_request(display=EngineeringUnitSystem.US_CUSTOMARY))
    si = preview_multirow_connection(_request(display=EngineeringUnitSystem.SI))
    assert us.preview_fingerprint == si.preview_fingerprint
    invalid = preview_multirow_connection(_request(tolerance="3"))
    assert invalid.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert invalid.plan_availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    assert invalid.visualization is None
    without_lbr = evaluate_multirow_connection(replace(_request(), prescribed_lbr=None))
    assert without_lbr.calculation_result is not None


def test_missing_required_bolt_axis_tension_remains_incomplete() -> None:
    response = evaluate_multirow_connection(_request(tension_required=True))
    assert response.calculation_result is not None
    tension = next(
        item
        for item in response.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.BOLT_TENSION
    )
    assert tension.availability.value == "INCOMPLETE_INPUT"
    partial = evaluate_multirow_connection(
        replace(
            _request(tension_required=True),
            bolt_axis_tensions=(
                BoltAxisTensionInput("B_R1_L1", PhysicalQuantity.of("1", Unit.KIP)),
            ),
        )
    )
    assert partial.calculation_result is not None
    provided = next(
        item
        for item in partial.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.BOLT_TENSION and item.bolt_id == "B_R1_L1"
    )
    assert provided.availability.value == "SOURCE_DATA_PENDING"


def test_request_rejects_invalid_public_contracts() -> None:
    with pytest.raises(ValueError, match="at least two"):
        replace(_request(), row_count=1)
    with pytest.raises(ValueError, match="confirmed provenance"):
        replace(
            _request(),
            row_distribution_basis=RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            engineer_distribution_kind=EngineerDistributionKind.FRACTIONS,
            engineer_allocations=(
                EngineerRowAllocationInput(1, Decimal(".5")),
                EngineerRowAllocationInput(2, Decimal(".5")),
            ),
        )


def test_nested_public_contracts_reject_invalid_values() -> None:
    layer = _request().layers[0]
    with pytest.raises(ValueError, match="nonempty"):
        replace(layer, layer_id=" ")
    with pytest.raises(ValueError, match="positive"):
        replace(layer, thickness=PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(ValueError, match="at least 0"):
        replace(layer, material_axis_angle_degrees=Decimal("180"))
    with pytest.raises(ValueError, match="positive non-Boolean"):
        EngineerRowAllocationInput(True, Decimal("1"))
    with pytest.raises(ValueError, match="exactly one"):
        EngineerRowAllocationInput(1)
    with pytest.raises(ValueError, match="exactly one"):
        EngineerRowAllocationInput(1, Decimal("1"), PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="cannot be negative"):
        EngineerRowAllocationInput(1, Decimal("-0.1"))
    with pytest.raises(ValueError, match="cannot be negative"):
        EngineerRowAllocationInput(1, direct_force=PhysicalQuantity.of("-1", Unit.KIP))
    with pytest.raises(ValueError, match="identity"):
        BoltAxisTensionInput(" ", PhysicalQuantity.of("1", Unit.KIP))


def test_request_contract_rejects_dimension_identity_and_method_conflicts() -> None:
    request = _request()
    other_layer = replace(request.layers[0], component_id="COMPONENT-2")
    tension = BoltAxisTensionInput("B_R1_L1", PhysicalQuantity.of("1", Unit.KIP))
    allocation = EngineerRowAllocationInput(1, Decimal("1"))
    invalid_cases: list[tuple[dict[str, Any], str]] = [
        ({"request_id": " "}, "nonempty"),
        ({"orchestration_contract_version": "wrong"}, "Unsupported"),
        ({"source_length_unit": Unit.KIP}, "source_length_unit"),
        ({"row_count": True}, "positive non-Boolean"),
        ({"pitch": PhysicalQuantity.of("0", Unit.IN)}, "must be positive"),
        ({"force_line_offset": PhysicalQuantity.of("1", Unit.KIP)}, "must be a length"),
        (
            {
                "signed_force_x": PhysicalQuantity.of("1", Unit.IN),
                "signed_force_y": PhysicalQuantity.of("1", Unit.KIP),
            },
            "force units",
        ),
        (
            {
                "signed_force_x": PhysicalQuantity.of("1", Unit.IN),
                "signed_force_y": PhysicalQuantity.of("1", Unit.IN),
            },
            "must be forces",
        ),
        (
            {
                "signed_force_x": PhysicalQuantity.of("0", Unit.KIP),
                "signed_force_y": PhysicalQuantity.of("0", Unit.KIP),
            },
            "cannot be zero",
        ),
        ({"layers": ()}, "At least one"),
        ({"layers": (request.layers[0], other_layer)}, "Layer identities must be unique"),
        ({"bolt_axis_tensions": (tension, tension)}, "tension identities must be unique"),
        (
            {"engineer_allocations": (allocation, allocation)},
            "row ordinals must be unique",
        ),
        (
            {
                "row_distribution_basis": (RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION),
                "engineer_distribution_kind": EngineerDistributionKind.FRACTIONS,
                "engineer_allocations": (),
            },
            "requires a kind and all rows",
        ),
        (
            {
                "engineer_distribution_kind": EngineerDistributionKind.FRACTIONS,
                "engineer_allocations": (allocation,),
            },
            "cannot accompany",
        ),
        ({"prescribed_lbr": Decimal("1.1")}, "between zero and one"),
    ]
    for changes, message in invalid_cases:
        with pytest.raises(ValueError, match=message):
            replace(request, **changes)


def test_application_fails_closed_for_resolved_identity_and_preset_errors() -> None:
    request = _request()
    unsupported_material = replace(request.layers[0], material_id="UNSUPPORTED")
    cases = [
        replace(
            request,
            row_distribution_basis=RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            engineer_distribution_kind=EngineerDistributionKind.FRACTIONS,
            engineer_allocations=(
                EngineerRowAllocationInput(1, Decimal(".5")),
                EngineerRowAllocationInput(3, Decimal(".5")),
            ),
            provenance=replace(request.provenance, engineer_confirmed=True),
        ),
        replace(request, layers=(unsupported_material,)),
        replace(request, bolt_diameter=PhysicalQuantity.of("2", Unit.IN)),
        replace(
            request,
            bolt_axis_tensions=(
                BoltAxisTensionInput("UNKNOWN", PhysicalQuantity.of("1", Unit.KIP)),
            ),
        ),
    ]
    for case in cases:
        preview = preview_multirow_connection(case)
        assert preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
        assert preview.design_check_ready is False


@pytest.mark.parametrize("bolts_per_row", [1, 2, 3])
def test_public_rectangular_bolt_counts_execute(bolts_per_row: int) -> None:
    response = evaluate_multirow_connection(_request(bolts_per_row=bolts_per_row))
    assert response.calculation_result is not None
    assert response.preview.visualization is not None
    assert len(response.preview.visualization.bolts) == 2 * bolts_per_row
    assert response.calculation_result.required_check_ids


def test_signed_force_reversal_rebuilds_row_order_and_fingerprint() -> None:
    forward_request = _request()
    reverse_request = replace(
        forward_request,
        signed_force_x=PhysicalQuantity.of("-10", Unit.KIP),
    )
    forward = evaluate_multirow_connection(forward_request)
    reverse = evaluate_multirow_connection(reverse_request)
    assert forward.calculation_result is not None
    assert reverse.calculation_result is not None
    assert forward.preview.visualization is not None
    assert reverse.preview.visualization is not None
    forward_rows = {item.bolt_id: item.row_id for item in forward.preview.visualization.bolts}
    reverse_rows = {item.bolt_id: item.row_id for item in reverse.preview.visualization.bolts}
    assert forward_rows["B_R1_L1"] == "ROW_2"
    assert reverse_rows["B_R1_L1"] == "ROW_1"
    assert (
        forward.calculation_result.input_fingerprint != reverse.calculation_result.input_fingerprint
    )
    assert all(
        item.demand is None or item.demand.magnitude >= 0
        for item in reverse.calculation_result.results
    )


def test_bundle_preserves_distinct_ends_factors_layers_and_eccentricity() -> None:
    request = _request()
    second_layer = replace(
        request.layers[0],
        layer_id="LAYER-2",
        component_id="COMPONENT-2",
    )
    request = replace(
        request,
        material_pair=ConnectedMaterialPair.FRP_STEEL,
        layers=(request.layers[0], second_layer),
        unloaded_end_e1=PhysicalQuantity.of("1.75", Unit.IN),
        loaded_boundary_to_row_1_distance=PhysicalQuantity.of("3.25", Unit.IN),
        pitch=PhysicalQuantity.of(".75", Unit.IN),
        lap_configuration=LapConfiguration.SINGLE_LAP,
        first_row_method=FirstRowPlanMethod.ASCE_COMMENTARY_FULL,
        force_line_offset=PhysicalQuantity.of(".25", Unit.IN),
    )
    with patch(
        "frp_master_connection.application.multirow_orchestration.calculate_multirow_connection",
        wraps=calculate_multirow_connection,
    ) as engine:
        response = evaluate_multirow_connection(request)
    bundle = cast(MultiRowExecutionBundle, engine.call_args.args[0])
    assert bundle.end_distances.unloaded_end_e1 == PhysicalQuantity.of("1.75", Unit.IN)
    assert bundle.end_distances.loaded_boundary_to_row_1_distance == PhysicalQuantity.of(
        "3.25", Unit.IN
    )
    assert bundle.factors.lap_factor_c_lap == Decimal(".60")
    assert bundle.factors.pitch_factor_c_delta < 1
    assert bundle.eccentricity is not None
    assert bundle.eccentricity.classification is BlockShearEccentricityClassification.ECCENTRIC
    assert response.calculation_result is not None
    pin_checks = [
        item
        for item in response.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.PIN_BEARING
    ]
    assert {item.layer_id for item in pin_checks} == {"LAYER-1", "LAYER-2"}
    first = next(
        item
        for item in response.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.FIRST_ROW_NET_TENSION
    )
    assert first.equation_method is MultiRowEquationMethod.FIRST_ROW_COMMENTARY_FULL
    blocks = [
        item
        for item in response.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR
    ]
    assert blocks
    assert all(
        item.equation_method is MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14B for item in blocks
    )
    default = evaluate_multirow_connection(_request())
    assert default.calculation_result is not None
    concentric_blocks = [
        item
        for item in default.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR
    ]
    assert concentric_blocks
    assert all(
        item.equation_method is MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14A
        for item in concentric_blocks
    )


def test_conservative_envelope_and_net_area_status_remain_explicit() -> None:
    conservative = evaluate_multirow_connection(
        _request(basis=RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE)
    )
    assert conservative.calculation_result is not None
    assert any("CONSERVATIVE" in item for item in conservative.preview.warnings)
    narrow = evaluate_multirow_connection(
        replace(
            _request(bolts_per_row=3),
            gauge=PhysicalQuantity.of(".65", Unit.IN),
            negative_side_distance=PhysicalQuantity.of(".3", Unit.IN),
            positive_side_distance=PhysicalQuantity.of(".3", Unit.IN),
        )
    )
    assert narrow.calculation_result is not None
    block = next(
        item
        for item in narrow.calculation_result.results
        if item.limit_state is MultiRowCheckFamily.BLOCK_SHEAR
        and item.availability.value == "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    )
    assert block.availability.value == "CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
    assert narrow.calculation_result.required_check_ids
    assert any(
        item.numerical_comparison.value == "FAIL" for item in narrow.calculation_result.results
    )
