"""Pure transport mapping for Stage 2.4C multi-row operations."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.api.calculation_mapping import (
    map_connection_view_extents,
    map_single_bolt_preview_request,
)
from frp_master_connection.api.multirow_schemas import (
    MULTIROW_API_TRANSPORT_SCHEMA_VERSION,
    MultiRowConnectionRequestDTO,
    MultiRowDesignResponseDTO,
    MultiRowPreviewResponseDTO,
)
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application import (
    BoltAxisTensionInput,
    EngineerRowAllocationInput,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    MultiRowOrchestrationResponse,
    MultiRowPreviewResult,
)
from frp_master_connection.calculation import (
    EndUseFactors,
    MethodProvenance,
    PhysicalQuantity,
    canonical_decimal_string,
    decimal_from_finite_real,
)


def _quantity(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


def map_multirow_request(request: MultiRowConnectionRequestDTO) -> MultiRowOrchestrationRequest:
    """Map strict untrusted transport data to the immutable application contract."""

    layers = tuple(
        MultiRowLayerInput(
            item.layer_id,
            item.component_id,
            item.material_id,
            _quantity(item.thickness),
            item.element_classification,
            Decimal(item.material_axis_angle_degrees),
            EndUseFactors(
                Decimal(item.end_use_factors.cm),
                Decimal(item.end_use_factors.ct),
                Decimal(item.end_use_factors.cch),
                item.end_use_factors.source_reference,
                item.end_use_factors.approval_metadata,
            ),
            item.bearing_thread_status,
        )
        for item in request.layers
    )
    allocations = tuple(
        EngineerRowAllocationInput(
            item.row_ordinal,
            None if item.fraction is None else Decimal(item.fraction),
            None if item.direct_force is None else _quantity(item.direct_force),
        )
        for item in request.engineer_allocations
    )
    tensions = tuple(
        BoltAxisTensionInput(item.bolt_id, _quantity(item.demand))
        for item in request.bolt_axis_tensions
    )
    provenance = MethodProvenance(
        request.provenance.source_method,
        request.provenance.source_document_or_calculation,
        request.provenance.revision,
        request.provenance.load_combination,
        request.provenance.reference_point,
        request.provenance.clearance_or_contact_modeled,
        request.provenance.engineer_confirmed,
    )
    physical_request = (
        None
        if request.physical_connection is None
        else map_single_bolt_preview_request(request.physical_connection)
    )
    view_extents = (
        None
        if request.physical_connection is None
        else map_connection_view_extents(request.physical_connection)
    )
    return MultiRowOrchestrationRequest(
        request.request_id,
        request.connection_id,
        request.interface_id,
        request.load_combination_id,
        request.source_reference,
        request.display_unit_system,
        request.source_length_unit,
        request.row_count,
        request.bolts_per_row,
        _quantity(request.bolt_diameter),
        request.hole_basis,
        _quantity(request.pitch),
        _quantity(request.gauge),
        _quantity(request.unloaded_end_e1),
        _quantity(request.loaded_boundary_to_row_1_distance),
        _quantity(request.negative_side_distance),
        _quantity(request.positive_side_distance),
        _quantity(request.geometry_tolerance),
        request.material_pair,
        layers,
        None if request.signed_force_x is None else _quantity(request.signed_force_x),
        None if request.signed_force_y is None else _quantity(request.signed_force_y),
        request.force_reference,
        request.row_distribution_basis,
        request.engineer_distribution_kind,
        allocations,
        provenance,
        request.bolt_axis_tension_required,
        tensions,
        request.time_effect_category,
        request.lap_configuration,
        request.first_row_method,
        None if request.prescribed_lbr is None else Decimal(request.prescribed_lbr),
        _quantity(request.force_line_offset),
        _quantity(request.eccentricity_tolerance),
        request.orchestration_contract_version,
        physical_request,
        view_extents,
        request.demand_source,
        request.automatic_action_source_id,
    )


def _serialize(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {
            "value": canonical_decimal_string(value.magnitude),
            "unit": value.unit.value,
            "canonical_value": value.canonical_string,
            "canonical_unit": value.canonical_unit.value,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    return value


def serialize_multirow_preview(
    response: MultiRowPreviewResult,
) -> MultiRowPreviewResponseDTO:
    visualization = (
        None
        if response.visualization is None
        else cast(dict[str, object], _serialize(response.visualization))
    )
    return MultiRowPreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": MULTIROW_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": response.orchestration_contract_version,
            "preview_schema_version": response.preview_schema_version,
            "visualization_schema_version": response.visualization_schema_version,
            "request_id": response.request_id,
            "connection_id": response.connection_id,
            "geometry_status": response.geometry_status.value,
            "plan_availability": response.plan_availability.value,
            "method_applicability": response.method_applicability.value,
            "qualification": response.qualification.value,
            "warnings": response.warnings,
            "preview_fingerprint": response.preview_fingerprint,
            "resistance_evaluated": False,
            "design_check_ready": response.design_check_ready,
            "visualization": visualization,
            "demand_source": response.demand_source,
            "automatic_demand_result": (
                None
                if response.automatic_demand_result is None
                else _serialize(response.automatic_demand_result)
            ),
        }
    )


def serialize_multirow_design(
    response: MultiRowOrchestrationResponse,
) -> MultiRowDesignResponseDTO:
    return MultiRowDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": MULTIROW_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": response.orchestration_contract_version,
            "preview_schema_version": response.preview.preview_schema_version,
            "visualization_schema_version": response.preview.visualization_schema_version,
            "request_id": response.request_id,
            "connection_id": response.connection_id,
            "preview": cast(dict[str, object], _serialize(response.preview)),
            "calculation_result": (
                None
                if response.calculation_result is None
                else cast(dict[str, object], _serialize(response.calculation_result))
            ),
            "demand_source": response.demand_source,
            "automatic_demand_result": (
                None
                if response.automatic_demand_result is None
                else _serialize(response.automatic_demand_result)
            ),
            "automatic_handoff_results": tuple(
                cast(dict[str, object], _serialize(item))
                for item in response.automatic_handoff_results
            ),
            "automatic_group_mode_integration": (
                None
                if response.automatic_group_mode_integration is None
                else cast(
                    dict[str, object],
                    _serialize(response.automatic_group_mode_integration),
                )
            ),
        }
    )


__all__ = (
    "map_multirow_request",
    "serialize_multirow_design",
    "serialize_multirow_preview",
)
