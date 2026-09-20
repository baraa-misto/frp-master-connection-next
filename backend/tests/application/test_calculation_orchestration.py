"""Focused contracts for canonical single-bolt calculation orchestration."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from frp_master_connection.application import (
    ExplicitBoltDemandAssignment,
    OrchestrationIssueCode,
    PenetratedLayerMaterialAssignment,
    SingleBoltOrchestrationRequest,
    evaluate_single_bolt_connection,
)
from frp_master_connection.calculation import (
    DemandDistributionStatus,
    DemandSourceKind,
    EndUseFactors,
    LapConfiguration,
    LayerLoadingSense,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    PultrudedElementForm,
    ResolvedSingleBoltDemand,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
    WasherGeometry,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    select_time_effect_factor,
)
from frp_master_connection.domain import PositionVector3D
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    JointGeometryContext,
    Vector3D,
    resolve_bolt_group_geometry,
)
from tests.c3_fixtures import C3Case, build_c3_case


def _case() -> C3Case:
    source = build_c3_case(pultruded_frp=True)
    paths = tuple(
        replace(
            path,
            layers=tuple(replace(layer, hole_diameter=2.1) for layer in path.layers),
        )
        for path in source.bolt_specification.paths
    )
    specification = replace(source.bolt_specification, paths=paths)
    group = resolve_bolt_group_geometry(source.basis, specification)
    context = JointGeometryContext(source.basis, (group,))
    return C3Case(source.assembly, source.basis, context, specification, group)


def _request(*, with_demand: bool = True) -> SingleBoltOrchestrationRequest:
    case = _case()
    material = create_locked_ice_material_snapshot()
    assignments = tuple(
        PenetratedLayerMaterialAssignment(
            layer.definition.participant.entity_id,
            layer.definition.physical_element_id,
            layer.physical_element.source_material_region.id,
            material,
            ThreadStatus.EXCLUDED,
            PultrudedElementForm.PLATE,
        )
        for layer in case.resolved_bolt_group.paths[0].layers
    )
    fastener = replace(
        create_locked_f593_fastener_snapshot(),
        washer_geometry=WasherGeometry(
            PhysicalQuantity.of("4", Unit.MM),
            PhysicalQuantity.of("1.3", Unit.MM),
            True,
            True,
        ),
    )
    demand = ResolvedSingleBoltDemand(
        id="demand-1",
        load_combination_id="load-1",
        source_member_id="member-1",
        source_action_id="action-1",
        source_kind=DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND,
        factored_action_confirmed=True,
        coordinate_frame_reference="GLOBAL",
        resolved_frame=GLOBAL_FRAME,
        source_reference_point_id="member-1:connected-end",
        resolved_global_reference_point=PositionVector3D(0.0, 0.0, 0.0),
        in_plane_force_vector=Vector3D(0.0, 0.0, 3.0),
        force_vector_unit=Unit.KN,
        bolt_axis_tensile_demand=PhysicalQuantity.of("0", Unit.KN),
        externally_supplied_prying_demand=PhysicalQuantity.of("0", Unit.KN),
        loading_sense=LayerLoadingSense.TENSION,
        provenance=("Explicit fixture demand for bolt-1.",),
        distribution_status=DemandDistributionStatus.EXPLICITLY_RESOLVED,
    )
    return SingleBoltOrchestrationRequest(
        calculation_id="orchestration-1",
        assembly=case.assembly,
        geometry_context=case.context,
        interface_id="interface-1",
        bolt_group_id="bolt-group-1",
        bolt_location_id="bolt-1",
        load_combination_id="load-1",
        material_assignments=assignments,
        fastener_snapshot=fastener,
        bolt_diameter=PhysicalQuantity.of("0.5", Unit.MM),
        published_code_unit_basis=PublishedCodeUnitBasis.SI_PRINTED,
        time_effect=select_time_effect_factor(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        end_use_factors=EndUseFactors(
            Decimal("1"),
            Decimal("1"),
            Decimal("1"),
            "Approved fixture factors",
            ("Stage 2.2A fixture",),
        ),
        lap_configuration=LapConfiguration.DOUBLE_LAP,
        resolved_demand=(
            ExplicitBoltDemandAssignment(
                "interface-1",
                "bolt-group-1",
                "bolt-1",
                demand,
            )
            if with_demand
            else None
        ),
        source_action_id="action-1",
    )


def test_orchestration_is_immutable_deterministic_and_delegates_to_engine() -> None:
    request = _request()
    first = evaluate_single_bolt_connection(request)
    second = evaluate_single_bolt_connection(request)

    assert first == second
    assert first.calculation_result is not None
    assert first.calculation_fingerprint == first.calculation_result.input_fingerprint
    assert tuple(item.layer_id for item in first.resolved_layers) == (
        "member-layer",
        "connector-layer",
    )
    assert all(item.code_mapping is not None for item in first.resolved_layers)
    assert OrchestrationIssueCode.FASTENER_SOURCE_PENDING in {issue.code for issue in first.issues}
    with pytest.raises(FrozenInstanceError):
        request.interface_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.assembly_id = "changed"  # type: ignore[misc]


def test_member_end_action_without_resolved_bolt_demand_fails_closed() -> None:
    response = evaluate_single_bolt_connection(_request(with_demand=False))

    assert response.calculation_result is None
    assert response.aggregate_status is not None
    assert response.aggregate_status.value == "BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED"
    assert response.source_action_trace is not None
    assert response.source_action_trace.automatic_moment_shift_applied is False
    assert response.calculation_fingerprint is not None
    assert OrchestrationIssueCode.BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED in {
        issue.code for issue in response.issues
    }
