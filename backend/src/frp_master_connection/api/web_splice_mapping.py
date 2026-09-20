"""Pure Stage 3.6A DTO mapping and deterministic serialization."""

from typing import cast

from frp_master_connection.api.clip_angle_mapping import _serialize
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.api.web_splice_schemas import (
    WEB_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
    WebSpliceDesignResponseDTO,
    WebSplicePreviewResponseDTO,
    WebSpliceRequestDTO,
)
from frp_master_connection.application.web_splice_orchestration import (
    WebSpliceDesignResult,
    WebSplicePreviewResult,
)
from frp_master_connection.calculation import PhysicalQuantity
from frp_master_connection.domain import (
    WebSpliceBeamGeometry,
    WebSpliceBoltGroupLayout,
    WebSpliceForce,
    WebSplicePlateGeometry,
    WebSpliceRequest,
)


def _q(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


def map_web_splice_request(value: WebSpliceRequestDTO) -> WebSpliceRequest:
    beam, plate, group, force = (
        value.beam,
        value.splice_plate,
        value.bolt_group,
        value.transfer_force,
    )
    moment = value.user_moment_l_v_t
    return WebSpliceRequest(
        value.request_id,
        value.unit_system,
        value.source_length_unit,
        WebSpliceBeamGeometry(
            _q(beam.depth),
            _q(beam.flange_width),
            _q(beam.web_thickness),
            _q(beam.flange_thickness),
            _q(beam.display_length_each_side),
            beam.profile_family,
        ),
        _q(value.beam_end_gap),
        WebSplicePlateGeometry(
            _q(plate.length),
            _q(plate.height),
            _q(plate.thickness),
            plate.count,
            plate.locked_identical,
        ),
        WebSpliceBoltGroupLayout(
            group.rows,
            group.bolts_per_row,
            _q(group.vertical_pitch),
            _q(group.longitudinal_gauge),
            _q(group.centroid_offset),
            group.locked_identical_mirror,
        ),
        _q(value.bolt_diameter),
        _q(value.hole_diameter),
        WebSpliceForce(_q(force.axial_force), _q(force.major_shear), _q(force.minor_shear)),
        (
            PhysicalQuantity.of(moment.x, moment.unit),
            PhysicalQuantity.of(moment.y, moment.unit),
            PhysicalQuantity.of(moment.z, moment.unit),
        ),
        value.flange_splice_enabled,
        value.orchestration_contract_version,
    )


def serialize_web_splice_preview(value: WebSplicePreviewResult) -> WebSplicePreviewResponseDTO:
    return WebSplicePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": WEB_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status.value,
            "geometry_invalid_reasons": value.geometry_invalid_reasons,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "engineering_fingerprint": value.engineering_fingerprint,
            "application_fingerprint": value.application_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_web_splice_design(value: WebSpliceDesignResult) -> WebSpliceDesignResponseDTO:
    return WebSpliceDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": WEB_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "supported_local_checks_executed": value.supported_local_checks_executed,
            "supported_local_failure_present": value.supported_local_failure_present,
            "local_check_ids": value.local_check_ids,
            "failed_local_check_ids": value.failed_local_check_ids,
            "local_resistance_warnings": value.local_resistance_warnings,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = ("map_web_splice_request", "serialize_web_splice_design", "serialize_web_splice_preview")
