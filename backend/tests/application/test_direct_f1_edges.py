"""Fail-closed edge tests for Direct physical and one-row source adapters."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest

import frp_master_connection.application.multirow_orchestration as orchestration
from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import preview_multirow_connection
from frp_master_connection.application.connection_preview import preview_single_bolt_connection
from frp_master_connection.application.direct_group_mode import evaluate_direct_layered_group_modes
from frp_master_connection.application.direct_physical import (
    _edge_clearance,
    direct_bolt_containment_issues,
    direct_material_axis_angle,
    direct_material_force_angle,
    is_direct_angle_w,
)
from frp_master_connection.application.direct_single_row import (
    DirectSingleRowResult,
    evaluate_direct_single_row,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationRequest,
    _ResolvedMultiRow,
)
from frp_master_connection.application.visualization import (
    BoltDisplaySnapshot,
    SingleBoltVisualizationSnapshot,
)
from frp_master_connection.calculation import (
    EccentricDemandResult,
    EccentricResistanceHandoffInput,
    FRPPropertyKind,
    PhysicalQuantity,
    Unit,
)
from frp_master_connection.domain import ComponentMaterialKind
from tests.application.test_direct_f1_safety import (
    _direct_payload,
    _one_row_payload,
    _request,
)


def _physical() -> tuple[SingleBoltVisualizationSnapshot, BoltDisplaySnapshot]:
    preview = preview_multirow_connection(_request(_direct_payload()))
    assert preview.visualization is not None
    physical = preview.visualization.physical_connection
    assert physical is not None
    return physical, preview.visualization.physical_bolts[0].display


def test_direct_physical_adapter_rejects_missing_members_faces_holes_and_washers() -> None:
    physical, bolt = _physical()
    assert not is_direct_angle_w(None)
    short_bolt = replace(bolt, holes=bolt.holes[:1])
    assert "Two FRP holes" in direct_bolt_containment_issues(physical, (short_bolt,))[0].detail
    missing_member = replace(
        bolt, holes=(replace(bolt.holes[0], participant_id="unknown"), *bolt.holes[1:])
    )
    assert (
        "FRP component is missing"
        in direct_bolt_containment_issues(physical, (missing_member,))[0].detail
    )
    steel = replace(
        physical,
        components=(
            replace(physical.components[0], material_kind=ComponentMaterialKind.STEEL),
            *physical.components[1:],
        ),
    )
    assert "FRP component is missing" in direct_bolt_containment_issues(steel, (bolt,))[0].detail
    no_face = replace(physical, interface_zones=())
    assert (
        "penetrated face is unresolved"
        in direct_bolt_containment_issues(no_face, (bolt,))[0].detail
    )
    no_washer = replace(bolt, washers=())
    assert (
        "required washer is missing"
        in direct_bolt_containment_issues(physical, (no_washer,))[0].detail
    )


def test_direct_planar_face_and_material_axes_fail_closed() -> None:
    physical, bolt = _physical()
    hole = bolt.holes[0]
    zone = next(
        item
        for item in physical.interface_zones
        if item.participant_id == hole.participant_id
        and item.patch_id.startswith(f"{hole.physical_element_id}:")
    )
    with pytest.raises(ValueError, match="authoritative planar rectangle"):
        _edge_clearance(replace(zone, geometry_kind="INVALID"), hole.start)
    collapsed = replace(zone, corners=(zone.corners[0], zone.corners[0], *zone.corners[2:]))
    with pytest.raises(ValueError, match="zero-length edge"):
        _edge_clearance(collapsed, hole.start)
    with pytest.raises(ValueError, match="no resolved interior"):
        _edge_clearance(replace(zone, center=zone.corners[0]), hole.start)
    no_direction = replace(physical, material_directions=())
    with pytest.raises(ValueError, match="DIRECT_MATERIAL_AXIS_UNRESOLVED"):
        direct_material_force_angle(
            no_direction, hole.participant_id, hole.physical_element_id, (1, 0, 0)
        )
    with pytest.raises(ValueError, match="DIRECT_MATERIAL_AXIS_UNRESOLVED"):
        direct_material_axis_angle(no_direction, hole.participant_id, hole.physical_element_id)
    with pytest.raises(ValueError, match="DIRECT_IN_PLANE_FORCE_REQUIRED"):
        direct_material_force_angle(
            physical, hole.participant_id, hole.physical_element_id, (0, 0, 0)
        )
    frame = next(
        item.frame
        for item in physical.frames
        if item.kind.value == "BOLT_GROUP_LOCAL" and item.owner_id == physical.bolt_group_id
    )
    direction = next(
        item
        for item in physical.material_directions
        if item.component_id == hole.participant_id
        and item.physical_element_id == hole.physical_element_id
    )
    tilted = replace(direction, lengthwise=frame.x_axis)
    altered = replace(
        physical,
        material_directions=tuple(
            tilted if item is direction else item for item in physical.material_directions
        ),
    )
    with pytest.raises(ValueError, match="DIRECT_MATERIAL_AXIS_NOT_IN_BOLT_PLANE"):
        direct_material_axis_angle(altered, hole.participant_id, hole.physical_element_id)


def _row_context(
    count: int = 2,
) -> tuple[MultiRowOrchestrationRequest, _ResolvedMultiRow, EccentricDemandResult]:
    request = _request(_one_row_payload(count))
    resolved = orchestration._resolve(request)
    demand = orchestration._automatic_demand(
        request, resolved, orchestration._execution_bundle(request, resolved)
    )
    return request, resolved, demand


def _row_result(
    resolved: _ResolvedMultiRow, demand: EccentricDemandResult
) -> DirectSingleRowResult:
    return evaluate_direct_single_row(
        resolved.geometry,
        resolved.first_plans_by_layer,
        resolved.layer_contexts,
        resolved.factors,
        demand,
        resolved.hole_definition.bolt_diameter,
        resolved.hole_definition.hole_diameter,
        resolved.total_demand,
        (),
        (),
        (),
        "f" * 64,
    )


def _replace_first_mapping(resolved: _ResolvedMultiRow, **changes: object) -> _ResolvedMultiRow:
    first = resolved.first_plans_by_layer[0][0]
    updated = replace(first, geometry=replace(cast(Any, first.geometry), **changes))
    return replace(
        resolved,
        first_plans_by_layer=((updated,), *resolved.first_plans_by_layer[1:]),
    )


def _without_property(resolved: _ResolvedMultiRow, kind: FRPPropertyKind) -> _ResolvedMultiRow:
    layer = resolved.layer_contexts[0]
    material = layer.material
    missing = tuple(sorted((*material.explicitly_missing, kind), key=lambda value: value.value))
    material = replace(
        material,
        properties=tuple(item for item in material.properties if item.kind is not kind),
        explicitly_missing=missing,
    )
    return replace(
        resolved,
        layer_contexts=(replace(layer, material=material), *resolved.layer_contexts[1:]),
    )


def test_direct_one_row_adapter_rejects_invalid_shapes_and_demand() -> None:
    _, resolved, demand = _row_context()
    with pytest.raises(ValueError, match="one row and two FRP layers"):
        _row_result(replace(resolved, layer_contexts=resolved.layer_contexts[:1]), demand)
    with pytest.raises(ValueError, match="one accepted demand scenario"):
        _row_result(resolved, cast(Any, type("EmptyDemand", (), {"scenarios": ()})()))
    excess = replace(
        resolved.geometry,
        group=cast(Any, type("FourBolts", (), {"bolts": (1, 2, 3, 4)})()),
    )
    with pytest.raises(ValueError, match="one through three bolts"):
        _row_result(replace(resolved, geometry=excess), demand)
    bad = cast(Any, type("BadPlan", (), {"geometry": object()})())
    with pytest.raises(TypeError, match="accepted first-row mapping"):
        _row_result(
            replace(resolved, first_plans_by_layer=((bad,), *resolved.first_plans_by_layer[1:])),
            demand,
        )


def test_direct_one_row_blocks_residual_and_missing_controlled_properties() -> None:
    _, resolved, demand = _row_context(1)
    scenario = replace(demand.scenarios[0], residual_moment=PhysicalQuantity.of("1", Unit.N_MM))
    residual = replace(demand, scenarios=(scenario,))
    checks = _row_result(resolved, residual).checks
    assert all(
        check.availability.value == "CALCULATION_NOT_SUPPORTED"
        for check in checks
        if check.layer_id == "layer-A"
    )
    for kind, expected in (
        (FRPPropertyKind.FT_L, "Controlled longitudinal tensile or shear"),
        (FRPPropertyKind.FSH_LT, "Controlled in-plane shear property"),
        (FRPPropertyKind.FBR_L, "Controlled longitudinal bearing property"),
    ):
        checks = _row_result(_without_property(resolved, kind), demand).checks
        assert any(expected in item.reason for item in checks)


def test_direct_one_row_source_geometry_limits_are_visibly_blocked() -> None:
    _, resolved, demand = _row_context(2)
    width_missing = _replace_first_mapping(resolved, effective_width=None)
    assert any(
        "Effective width" in check.reason for check in _row_result(width_missing, demand).checks
    )
    high_gauge = _replace_first_mapping(resolved, gauge=PhysicalQuantity.of("3", Unit.IN))
    assert any(
        "exceeds the source limit" in check.reason
        for check in _row_result(high_gauge, demand).checks
    )
    narrow = _replace_first_mapping(resolved, effective_width=PhysicalQuantity.of("0.5", Unit.IN))
    assert any(
        "Net section is nonpositive" in check.reason for check in _row_result(narrow, demand).checks
    )
    asymmetric = _replace_first_mapping(resolved, raw_e4=PhysicalQuantity.of("2", Unit.IN))
    assert any(
        "symmetric side-distance" in check.reason
        for check in _row_result(asymmetric, demand).checks
    )
    negative_cleavage = _replace_first_mapping(
        resolved,
        raw_e3=PhysicalQuantity.of("-100", Unit.IN),
        raw_e4=PhysicalQuantity.of("-100", Unit.IN),
    )
    assert any(
        "Cleavage nominal resistance is nonpositive" in check.reason
        for check in _row_result(negative_cleavage, demand).checks
    )


def test_direct_request_and_transport_reject_wrong_family_and_mode_type() -> None:
    request = _request(_direct_payload())
    with pytest.raises(TypeError, match="direct_finalization_mode must be Boolean"):
        replace(request, direct_finalization_mode=cast(Any, "yes"))
    with pytest.raises(ValueError, match="physical FRP angle/W family"):
        replace(request, physical_connection_request=None)
    dto = MultiRowConnectionRequestDTO.model_validate(_direct_payload())
    with pytest.raises(ValueError, match="physical FRP angle/W family"):
        map_multirow_request(dto.model_copy(update={"physical_connection": None}))


def test_direct_layered_group_guard_requires_two_physical_layers() -> None:
    _, resolved, _ = _row_context()
    malformed = cast(
        EccentricResistanceHandoffInput,
        SimpleNamespace(execution_bundle=SimpleNamespace(layers=resolved.layer_contexts[:1])),
    )
    with pytest.raises(ValueError, match="exactly two physical layers"):
        evaluate_direct_layered_group_modes(malformed, ())


def test_direct_axis_binding_fails_closed_for_missing_physical_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, resolved, _ = _row_context()
    physical_request = request.physical_connection_request
    assert physical_request is not None
    baseline = preview_single_bolt_connection(physical_request, request.connection_view_extents)
    snapshot = baseline.visualization
    assert snapshot is not None
    authority = resolved.authority
    with monkeypatch.context() as patch:
        patch.setattr(
            orchestration,
            "preview_single_bolt_connection",
            lambda *_: replace(
                baseline, visualization=replace(snapshot, bolt=replace(snapshot.bolt, holes=()))
            ),
        )
        with pytest.raises(ValueError, match="DIRECT_TWO_PHYSICAL_FRP_LAYERS_REQUIRED"):
            orchestration._direct_physical_axes(request, authority)
    with monkeypatch.context() as patch:
        patch.setattr(
            orchestration,
            "preview_single_bolt_connection",
            lambda *_: replace(baseline, visualization=replace(snapshot, frames=())),
        )
        with pytest.raises(ValueError, match="DIRECT_BOLT_GROUP_FRAME_UNRESOLVED"):
            orchestration._direct_physical_axes(request, authority)
    mismatched = replace(
        request,
        layers=(
            replace(request.layers[0], thickness=PhysicalQuantity.of("0.7", Unit.IN)),
            request.layers[1],
        ),
    )
    with pytest.raises(ValueError, match="DIRECT_LAYER_THICKNESS_MISMATCH"):
        orchestration._direct_physical_axes(mismatched, authority)


def test_direct_load_and_preview_guards_reject_unresolved_physical_state() -> None:
    request, resolved, _ = _row_context()
    axial = replace(resolved.authority, force_n=PhysicalQuantity.of("1", Unit.KIP))
    assert "DIRECT_BOLT_AXIS_FORCE_OR_PRYING_NOT_SUPPORTED" in orchestration._direct_load_blockers(
        request, axial
    )
    with_tension = replace(request, bolt_axis_tension_required=True)
    assert (
        "DIRECT_BOLT_AXIS_TENSION_OR_PRYING_NOT_SUPPORTED"
        in orchestration._direct_load_blockers(with_tension, resolved.authority)
    )
    missing = replace(
        resolved,
        visualization=replace(resolved.visualization, physical_connection=None),
    )
    with pytest.raises(ValueError, match="DIRECT_PHYSICAL_SNAPSHOT_REQUIRED"):
        orchestration._preview_from_resolved(request, missing, None)


def test_direct_duplicate_layer_scenario_identity_is_rejected() -> None:
    request = _request(_direct_payload())
    integration = orchestration.evaluate_multirow_connection(
        request
    ).automatic_group_mode_integration
    assert integration is not None
    first = integration.scenario_results[0]
    with pytest.raises(ValueError, match="scenario/layer identities must be unique"):
        replace(integration, scenario_results=(first, first))
