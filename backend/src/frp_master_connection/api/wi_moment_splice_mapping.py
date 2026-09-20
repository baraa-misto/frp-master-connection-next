"""Pure Stage 4.1A DTO mapping and deterministic serialization."""

from typing import cast

from frp_master_connection.api.clip_angle_mapping import _serialize
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.api.wi_moment_splice_schemas import (
    WI_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
    WIMomentSpliceDesignResponseDTO,
    WIMomentSpliceFastenerDTO,
    WIMomentSplicePreviewResponseDTO,
    WIMomentSpliceRequestDTO,
)
from frp_master_connection.application.wi_moment_splice_orchestration import (
    WIMomentSpliceDesignResult,
    WIMomentSplicePreviewResult,
)
from frp_master_connection.calculation import PhysicalQuantity
from frp_master_connection.domain.web_splice import (
    WebSpliceBeamGeometry,
    WebSpliceBoltGroupLayout,
    WebSplicePlateGeometry,
)
from frp_master_connection.domain.wi_moment_splice import (
    WIMomentSpliceActions,
    WIMomentSpliceFastener,
    WIMomentSpliceFlangeGeometry,
    WIMomentSpliceRequest,
)


def _q(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


def map_wi_moment_splice_request(value: WIMomentSpliceRequestDTO) -> WIMomentSpliceRequest:
    beam = value.beam
    web_plate = value.web_splice_plate
    web_group = value.web_bolt_group
    flange = value.flange_geometry
    actions = value.actions

    def fastener(item: WIMomentSpliceFastenerDTO) -> WIMomentSpliceFastener:
        return WIMomentSpliceFastener(
            _q(item.bolt_diameter),
            _q(item.hole_diameter),
            item.source_authority_id,
            item.thread_condition,
            None if item.nominal_shear_stress is None else _q(item.nominal_shear_stress),
        )

    force_unit = actions.axial_force_l.unit
    moment_unit = actions.major_moment_t.unit
    return WIMomentSpliceRequest(
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
            _q(web_plate.length),
            _q(web_plate.height),
            _q(web_plate.thickness),
            web_plate.count,
            web_plate.locked_identical,
        ),
        WebSpliceBoltGroupLayout(
            web_group.rows,
            web_group.bolts_per_row,
            _q(web_group.vertical_pitch),
            _q(web_group.longitudinal_gauge),
            _q(web_group.centroid_offset),
            web_group.locked_identical_mirror,
        ),
        fastener(value.web_fastener),
        WIMomentSpliceFlangeGeometry(
            _q(flange.plate_length),
            _q(flange.plate_thickness),
            _q(flange.inner_strip_width),
            flange.bolts_per_line,
            _q(flange.longitudinal_pitch),
            _q(flange.group_centroid_distance),
            flange.outer_plate_count_per_flange,
            flange.inner_strip_count_per_flange,
            flange.locked_top_bottom_identical,
            flange.locked_inner_symmetric,
        ),
        fastener(value.flange_fastener),
        WIMomentSpliceActions(
            _q(actions.axial_force_l),
            _q(actions.major_shear_v),
            _q(actions.major_moment_t),
            PhysicalQuantity.of(0, force_unit),
            PhysicalQuantity.of(0, moment_unit),
            PhysicalQuantity.of(0, moment_unit),
        ),
        value.profile_family,
        value.beams_locked_identical,
        value.orchestration_contract_version,
    )


def serialize_wi_moment_splice_preview(
    value: WIMomentSplicePreviewResult,
) -> WIMomentSplicePreviewResponseDTO:
    return WIMomentSplicePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": WI_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.contract_version,
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


def serialize_wi_moment_splice_design(
    value: WIMomentSpliceDesignResult,
) -> WIMomentSpliceDesignResponseDTO:
    return WIMomentSpliceDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": WI_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "failed_check_ids": value.failed_check_ids,
            "unavailable_check_ids": value.unavailable_check_ids,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_wi_moment_splice_request",
    "serialize_wi_moment_splice_design",
    "serialize_wi_moment_splice_preview",
)
