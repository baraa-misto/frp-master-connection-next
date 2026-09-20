"""Pure DTO mapping and deterministic serialization for Stage 3.3B."""

from __future__ import annotations

from typing import cast

from frp_master_connection.api.clip_angle_mapping import _serialize, map_clip_angle_request
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.paired_clip_angle_schemas import (
    PAIRED_CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
    PairedClipAngleConnectorRequestDTO,
    PairedClipAngleDesignResponseDTO,
    PairedClipAnglePreviewResponseDTO,
)
from frp_master_connection.application.paired_clip_angle_orchestration import (
    PairedClipAngleDesignResult,
    PairedClipAngleOrchestrationRequest,
    PairedClipAnglePreviewResult,
)


def map_paired_clip_angle_request(
    value: PairedClipAngleConnectorRequestDTO,
) -> PairedClipAngleOrchestrationRequest:
    """Map untrusted paired transport through the accepted single-angle value adapters."""

    payload = value.model_dump(mode="json")
    paired_contract = payload["orchestration_contract_version"]
    payload["orchestration_contract_version"] = (
        "3.3C2-RC1" if paired_contract == "3.3C3-RC1" else "3.3A-RC1"
    )
    payload["hand"] = "POSITIVE_S_SIDE"
    payload["interface_a_layout"] = payload.pop("common_member_layout")
    payload["interface_b_layout"] = payload.pop("mirrored_support_layout")
    payload.pop("pair_symmetry")
    single = map_clip_angle_request(ClipAngleConnectorRequestDTO.model_validate(payload))
    return PairedClipAngleOrchestrationRequest(
        single.request_id,
        single.unit_system,
        single.source_length_unit,
        single.support_role,
        single.selected_support_flange,
        single.connector_dimensions,
        single.support_dimensions,
        single.connected_member_profile,
        single.interface_a_layout,
        single.interface_b_layout,
        single.bolt_diameter,
        single.hole_diameter,
        single.hole_basis,
        single.global_force,
        single.global_moment,
        single.global_reference_point,
        single.connected_member_inclination_degrees,
        single.connected_member_end_trim_enabled,
        single.connected_member_end_clearance,
        single.connector_length_anchor,
        single.connector_length_anchor_position,
        paired_contract,
        single.support_target_id,
        single.support_profile,
    )


def serialize_paired_clip_angle_preview(
    value: PairedClipAnglePreviewResult,
) -> PairedClipAnglePreviewResponseDTO:
    return PairedClipAnglePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": PAIRED_CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status.value,
            "geometry_invalid_reasons": value.geometry_invalid_reasons,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "warnings": value.warnings,
            "engineering_fingerprint": value.engineering_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_paired_clip_angle_design(
    value: PairedClipAngleDesignResult,
) -> PairedClipAngleDesignResponseDTO:
    return PairedClipAngleDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": PAIRED_CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "supported_interface_failure_present": value.supported_interface_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_paired_clip_angle_request",
    "serialize_paired_clip_angle_design",
    "serialize_paired_clip_angle_preview",
)
