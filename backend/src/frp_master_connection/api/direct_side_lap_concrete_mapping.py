"""Pure DTO mapping and deterministic serialization for Stage 3.5B."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

from frp_master_connection.api.beam_concrete_paired_angle_mapping import _quantity_vector
from frp_master_connection.api.clip_angle_mapping import (
    _length,
    _profile,
    _serialize,
    _signed_length,
)
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.direct_side_lap_concrete_schemas import (
    DIRECT_SIDE_LAP_CONCRETE_API_TRANSPORT_SCHEMA_VERSION,
    DirectSideLapConcreteDesignResponseDTO,
    DirectSideLapConcretePreviewResponseDTO,
    DirectSideLapConcreteRequestDTO,
)
from frp_master_connection.application.direct_side_lap_concrete_orchestration import (
    DirectSideLapAnchorPattern,
    DirectSideLapDesignResult,
    DirectSideLapPreviewResult,
    DirectSideLapRequest,
    DirectSideLapWallGeometry,
    SideLapVector,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import ExternalAnchorGeometry, MemberProfile


def _profile_with_authoritative_length(
    value: DirectSideLapConcreteRequestDTO,
    total_length: Decimal,
) -> MemberProfile:
    profile = _profile(
        cast(
            ClipAngleConnectorRequestDTO,
            SimpleNamespace(connected_member_profile=value.connected_profile),
        ),
        value.source_length_unit,
    )
    return replace(profile, dimensions=replace(profile.dimensions, member_length=total_length))


def map_direct_side_lap_concrete_request(
    value: DirectSideLapConcreteRequestDTO,
) -> DirectSideLapRequest:
    unit = value.source_length_unit
    wall = value.wall
    pattern = value.anchor_pattern
    anchor = value.external_anchor
    lap = _length(value.side_lap_length, unit)
    projection = _length(value.member_projection_beyond_wall, unit)
    moment_unit = Unit.KIP_IN if value.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    user_moment = (
        _quantity_vector(value.user_moment_lsn)
        if value.user_moment_lsn is not None
        else SideLapVector(*tuple(PhysicalQuantity.of(0, moment_unit) for _ in range(3)))
    )
    if not isinstance(user_moment, SideLapVector):
        user_moment = SideLapVector(user_moment.h, user_moment.v, user_moment.n)
    return DirectSideLapRequest(
        value.request_id,
        value.unit_system,
        unit,
        DirectSideLapWallGeometry(
            _length(wall.run_length, unit),
            _length(wall.transverse_width, unit),
            _length(wall.thickness, unit),
        ),
        lap,
        projection,
        _profile_with_authoritative_length(value, lap + projection),
        DirectSideLapAnchorPattern(
            pattern.row_count,
            pattern.anchors_per_row,
            _length(pattern.pitch, unit),
            _length(pattern.gauge, unit),
            _length(pattern.centroid_distance_behind_free_end, unit),
            _signed_length(pattern.transverse_offset, unit),
        ),
        ExternalAnchorGeometry(
            PhysicalQuantity.of(anchor.nominal_diameter.value, anchor.nominal_diameter.unit),
            PhysicalQuantity.of(anchor.hole_diameter.value, anchor.hole_diameter.unit),
            PhysicalQuantity.of(anchor.specified_embedment.value, anchor.specified_embedment.unit),
            PhysicalQuantity.of(
                anchor.washer_outside_diameter.value,
                anchor.washer_outside_diameter.unit,
            ),
            PhysicalQuantity.of(anchor.washer_thickness.value, anchor.washer_thickness.unit),
            anchor.system_classification,
        ),
        PhysicalQuantity.of(value.axial_force.value, value.axial_force.unit),
        PhysicalQuantity.of(value.major_shear.value, value.major_shear.unit),
        PhysicalQuantity.of(value.minor_shear.value, value.minor_shear.unit),
        user_moment,
        value.orchestration_contract_version,
    )


def serialize_direct_side_lap_concrete_preview(
    value: DirectSideLapPreviewResult,
) -> DirectSideLapConcretePreviewResponseDTO:
    return DirectSideLapConcretePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": DIRECT_SIDE_LAP_CONCRETE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status,
            "geometry_invalid_reasons": value.geometry_invalid_reasons,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "external_design_required": True,
            "engineering_fingerprint": value.engineering_fingerprint,
            "application_fingerprint": value.application_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_direct_side_lap_concrete_design(
    value: DirectSideLapDesignResult,
) -> DirectSideLapConcreteDesignResponseDTO:
    return DirectSideLapConcreteDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": DIRECT_SIDE_LAP_CONCRETE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "external_design_required": True,
            "supported_local_frp_failure_present": value.supported_local_frp_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_direct_side_lap_concrete_request",
    "serialize_direct_side_lap_concrete_design",
    "serialize_direct_side_lap_concrete_preview",
)
