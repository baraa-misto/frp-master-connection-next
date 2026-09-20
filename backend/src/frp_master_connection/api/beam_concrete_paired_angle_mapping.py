"""Pure DTO mapping and deterministic serialization for Stage 3.5A."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BEAM_CONCRETE_PAIRED_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
    BeamConcretePairedAngleDesignResponseDTO,
    BeamConcretePairedAnglePreviewResponseDTO,
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.api.clip_angle_mapping import (
    _layout,
    _length,
    _profile,
    _serialize,
    _signed_length,
)
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.schemas import DecimalVector3DTO
from frp_master_connection.application.beam_concrete_paired_angle_orchestration import (
    BeamConcretePairedAngleDesignResult,
    BeamConcretePairedAnglePreviewResult,
    BeamConcretePairedAngleRequest,
)
from frp_master_connection.calculation import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ClipAngleDimensions,
    ConcreteWallGeometry,
    ExternalAnchorGeometry,
    WallAnchorPattern,
    WallQuantityVector,
)


def _quantity_vector(value: DecimalVector3DTO) -> WallQuantityVector:
    return WallQuantityVector(
        PhysicalQuantity.of(value.x, value.unit),
        PhysicalQuantity.of(value.y, value.unit),
        PhysicalQuantity.of(value.z, value.unit),
    )


def map_beam_concrete_paired_angle_request(
    value: BeamConcretePairedAngleRequestDTO,
) -> BeamConcretePairedAngleRequest:
    unit = value.source_length_unit
    wall = value.wall
    connector = value.connector_dimensions
    anchor = value.external_anchor
    is_r2 = value.orchestration_contract_version == "3.5A-R2-RC1"
    if is_r2:
        if value.major_shear is None or value.minor_shear is None or value.axial_force is None:
            raise ValueError("Stage 3.5A-R2 force components are incomplete.")
        reaction = PhysicalQuantity.of(value.major_shear.value, value.major_shear.unit)
        user_force = WallQuantityVector(
            PhysicalQuantity.of(value.minor_shear.value, value.minor_shear.unit),
            reaction,
            PhysicalQuantity.of(value.axial_force.value, value.axial_force.unit),
        )
        moment_unit = Unit.KIP_IN if value.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
        user_moment = (
            _quantity_vector(value.user_moment_hvn)
            if value.user_moment_hvn is not None
            else WallQuantityVector(*tuple(PhysicalQuantity.of(0, moment_unit) for _ in range(3)))
        )
    else:
        if value.reaction_shear is None or value.user_force_hvn is None:
            raise ValueError("Historical Stage 3.5A force fields are incomplete.")
        reaction = PhysicalQuantity.of(value.reaction_shear.value, value.reaction_shear.unit)
        user_force = _quantity_vector(value.user_force_hvn)
        if value.user_moment_hvn is None:
            raise ValueError("Historical Stage 3.5A user moment field is required.")
        user_moment = _quantity_vector(value.user_moment_hvn)
    if reaction.dimension is not Dimension.FORCE:
        raise ValueError("Reaction shear must be a force quantity.")
    beam_profile = _profile(
        cast(
            ClipAngleConnectorRequestDTO,
            SimpleNamespace(connected_member_profile=value.beam_profile),
        ),
        unit,
    )
    return BeamConcretePairedAngleRequest(
        value.request_id,
        value.unit_system,
        unit,
        ConcreteWallGeometry(
            _length(wall.width, unit),
            _length(wall.height, unit),
            _length(wall.thickness, unit),
            _signed_length(wall.connection_origin_h, unit),
            _signed_length(wall.connection_origin_v, unit),
        ),
        beam_profile,
        PhysicalQuantity.of(value.beam_end_gap.value, value.beam_end_gap.unit),
        ClipAngleDimensions(
            _length(connector.connected_leg_width, unit),
            _length(connector.support_leg_width, unit),
            _length(connector.thickness, unit),
            _length(connector.connector_length, unit),
        ),
        PhysicalQuantity.of(
            value.connector_length_anchor_position.value,
            value.connector_length_anchor_position.unit,
        ),
        _layout(value.common_beam_layout, unit),
        WallAnchorPattern(
            value.wall_anchor_pattern.row_count,
            value.wall_anchor_pattern.anchors_per_row,
            _length(value.wall_anchor_pattern.pitch, unit),
            _length(value.wall_anchor_pattern.gauge, unit),
            _length(value.wall_anchor_pattern.centroid_offset_h, unit),
            _signed_length(value.wall_anchor_pattern.centroid_v, unit),
        ),
        PhysicalQuantity.of(value.common_bolt_diameter.value, value.common_bolt_diameter.unit),
        PhysicalQuantity.of(value.common_hole_diameter.value, value.common_hole_diameter.unit),
        ExternalAnchorGeometry(
            PhysicalQuantity.of(anchor.nominal_diameter.value, anchor.nominal_diameter.unit),
            PhysicalQuantity.of(anchor.hole_diameter.value, anchor.hole_diameter.unit),
            PhysicalQuantity.of(anchor.specified_embedment.value, anchor.specified_embedment.unit),
            PhysicalQuantity.of(
                anchor.washer_outside_diameter.value, anchor.washer_outside_diameter.unit
            ),
            PhysicalQuantity.of(anchor.washer_thickness.value, anchor.washer_thickness.unit),
            anchor.system_classification,
        ),
        reaction,
        user_force,
        user_moment,
        value.orchestration_contract_version,
    )


def serialize_beam_concrete_paired_angle_preview(
    value: BeamConcretePairedAnglePreviewResult,
) -> BeamConcretePairedAnglePreviewResponseDTO:
    return BeamConcretePairedAnglePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": BEAM_CONCRETE_PAIRED_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status.value,
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


def serialize_beam_concrete_paired_angle_design(
    value: BeamConcretePairedAngleDesignResult,
) -> BeamConcretePairedAngleDesignResponseDTO:
    return BeamConcretePairedAngleDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": BEAM_CONCRETE_PAIRED_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "external_design_required": True,
            "supported_beam_side_failure_present": value.supported_beam_side_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_beam_concrete_paired_angle_request",
    "serialize_beam_concrete_paired_angle_design",
    "serialize_beam_concrete_paired_angle_preview",
)
