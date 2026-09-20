"""Zero-resistance canonical geometry/action preview application service."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from frp_master_connection.calculation import GeometryToCodeMapping
from frp_master_connection.calculation.geometry_mapping import (
    GeometryToCodeMappingRequest,
    resolve_geometry_to_code_mapping,
)
from frp_master_connection.domain import ComponentMaterialKind
from frp_master_connection.geometry import Vector3D

from .calculation_orchestration import (
    OrchestrationIssue,
    OrchestrationIssueCode,
    SingleBoltOrchestrationRequest,
    SingleBoltOrchestrationResponse,
    _base_response,
    _deduplicate_issues,
    _issue,
    _layer_key,
    _length_unit,
    _participant,
    _raw_layer_trace,
    _resolve_layer_assignments,
    _resolve_source_action,
    _resolve_target,
    _validate_demand,
)
from .visualization import (
    ConnectionViewExtents,
    SingleBoltVisualizationSnapshot,
    build_single_bolt_visualization_snapshot,
)

PREVIEW_SCHEMA_VERSION = "0.2.0-draft"


class PreviewGeometryStatus(StrEnum):
    """Model-only status with no resistance or design-outcome meaning."""

    VALID = "PREVIEW_VALID"
    INVALID_GEOMETRY = "PREVIEW_INVALID_GEOMETRY"
    INCOMPLETE_INPUT = "PREVIEW_INCOMPLETE_INPUT"
    UNSUPPORTED = "PREVIEW_UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class SingleBoltPreviewResult:
    """Authoritative current-model preview, deliberately separate from design results."""

    geometry_status: PreviewGeometryStatus
    orchestration_trace: SingleBoltOrchestrationResponse
    material_relationships: tuple[GeometryToCodeMapping, ...]
    visualization: SingleBoltVisualizationSnapshot | None
    design_check_ready: bool
    design_check_blocking_reasons: tuple[str, ...]


_INVALID_CODES = frozenset(
    {
        OrchestrationIssueCode.INVALID_GEOMETRY,
        OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND,
        OrchestrationIssueCode.MATERIAL_REGION_NOT_FOUND,
        OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISMATCH,
    }
)

_INCOMPLETE_CODES = frozenset(
    {
        OrchestrationIssueCode.JOINT_CONTEXT_MISMATCH,
        OrchestrationIssueCode.INTERFACE_NOT_FOUND,
        OrchestrationIssueCode.BOLT_GROUP_NOT_FOUND,
        OrchestrationIssueCode.BOLT_LOCATION_NOT_FOUND,
        OrchestrationIssueCode.BOLT_PATH_NOT_FOUND,
        OrchestrationIssueCode.LOAD_COMBINATION_NOT_FOUND,
        OrchestrationIssueCode.SOURCE_ACTION_NOT_FOUND,
        OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT,
        OrchestrationIssueCode.PARTICIPANT_NOT_FOUND,
        OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISSING,
        OrchestrationIssueCode.DUPLICATE_MATERIAL_ASSIGNMENT,
    }
)


def _status(issues: tuple[OrchestrationIssue, ...], *, supported: bool) -> PreviewGeometryStatus:
    codes = {item.code for item in issues}
    if codes & _INVALID_CODES:
        return PreviewGeometryStatus.INVALID_GEOMETRY
    if codes & _INCOMPLETE_CODES:
        return PreviewGeometryStatus.INCOMPLETE_INPUT
    if not supported:
        return PreviewGeometryStatus.UNSUPPORTED
    return PreviewGeometryStatus.VALID


def _design_blockers(
    status: PreviewGeometryStatus,
    issues: tuple[OrchestrationIssue, ...],
    *,
    has_explicit_demand: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if status is not PreviewGeometryStatus.VALID:
        blockers.extend(item.code.value for item in issues)
        if not blockers:
            blockers.append(status.value)
    if not has_explicit_demand:
        blockers.append("EXPLICIT_RESOLVED_BOLT_DEMAND_REQUIRED")
    return tuple(dict.fromkeys(blockers))


def preview_single_bolt_connection(
    request: SingleBoltOrchestrationRequest,
    view_extents: ConnectionViewExtents | None = None,
) -> SingleBoltPreviewResult:
    """Resolve canonical geometry/actions and stop before design planning or equations."""

    if not isinstance(request, SingleBoltOrchestrationRequest):
        raise TypeError("request must be a SingleBoltOrchestrationRequest.")
    if view_extents is not None and not isinstance(view_extents, ConnectionViewExtents):
        raise TypeError("view_extents must be ConnectionViewExtents or None.")
    issues: list[OrchestrationIssue] = []
    if request.template_orientation is not None:
        issues.extend(
            _issue(
                OrchestrationIssueCode.INVALID_GEOMETRY,
                item.message,
                item.classification.value,
                item.interface_id,
                item.first_participant_id,
                item.first_physical_element_id,
                item.second_participant_id,
                item.second_physical_element_id,
            )
            for item in request.template_orientation.interference
        )

    target = _resolve_target(request, issues)
    if target is None:
        resolved_issues = _deduplicate_issues(issues)
        status = _status(resolved_issues, supported=False)
        blockers = _design_blockers(
            status,
            resolved_issues,
            has_explicit_demand=request.resolved_demand is not None,
        )
        return SingleBoltPreviewResult(
            status,
            _base_response(
                request,
                load=None,
                source_action=None,
                issues=resolved_issues,
            ),
            (),
            None,
            False,
            blockers,
        )

    source_action = _resolve_source_action(request, target, issues)
    demand = _validate_demand(request, issues)
    frp_layers, assignments = _resolve_layer_assignments(request, target, issues)
    unit = _length_unit(request.assembly.unit_system)
    assignment_by_key = {item.key: item for item in assignments}
    mappings: list[GeometryToCodeMapping] = []
    signed_force: Vector3D | None = None
    if demand is not None:
        signed_force = demand.resolved_frame.local_to_parent_vector(demand.in_plane_force_vector)
    elif source_action is not None:
        force = source_action.resolved_action.global_force
        signed_force = Vector3D(force.fx, force.fy, force.fz)

    if signed_force is not None and not any(item.code in _INVALID_CODES for item in issues):
        for layer in frp_layers:
            component = _participant(request.assembly, layer.definition.participant)
            if component is None or component.material_orientation is None:
                issues.append(
                    _issue(
                        OrchestrationIssueCode.INVALID_GEOMETRY,
                        "An FRP layer lacks a resolved component lengthwise orientation.",
                        layer.definition.participant.entity_id,
                    )
                )
                continue
            try:
                mapping = resolve_geometry_to_code_mapping(
                    GeometryToCodeMappingRequest(
                        resolved_bolt_group=target.group,
                        bolt_location_id=request.bolt_location_id,
                        layer_id=layer.definition.id,
                        bolt_diameter=request.bolt_diameter,
                        signed_in_plane_force=signed_force,
                        component_lengthwise_axis=component.material_orientation.lengthwise_axis,
                        source_length_unit=unit,
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                issues.append(
                    _issue(
                        OrchestrationIssueCode.INVALID_GEOMETRY,
                        str(error),
                        layer.definition.id,
                    )
                )
                continue
            mappings.append(replace(mapping, physical_element_id=layer.definition.id))

    mapping_by_layer = {item.physical_element_id: item for item in mappings}
    traces = tuple(
        _raw_layer_trace(
            layer,
            unit,
            (
                component.material_kind
                if (component := _participant(request.assembly, layer.definition.participant))
                is not None
                else ComponentMaterialKind.OTHER
            ),
            assignment_by_key.get(_layer_key(layer)),
            mapping_by_layer.get(layer.definition.id),
            None,
        )
        for layer in target.path.layers
    )
    resolved_issues = _deduplicate_issues(issues)
    supported = bool(frp_layers and assignments and signed_force is not None)
    status = _status(resolved_issues, supported=supported)
    blockers = _design_blockers(
        status,
        resolved_issues,
        has_explicit_demand=demand is not None,
    )
    trace = _base_response(
        request,
        load=target.load_combination,
        source_action=source_action,
        layers=traces,
        assignments=assignments,
        issues=resolved_issues,
    )
    visualization = build_single_bolt_visualization_snapshot(request, trace, view_extents)
    return SingleBoltPreviewResult(
        status,
        trace,
        tuple(mappings),
        visualization,
        not blockers,
        blockers,
    )


__all__ = (
    "PREVIEW_SCHEMA_VERSION",
    "PreviewGeometryStatus",
    "SingleBoltPreviewResult",
    "preview_single_bolt_connection",
)
