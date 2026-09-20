"""Strict stateless transport contracts for Stage 3.5B."""

from __future__ import annotations

from typing import Literal

from pydantic import JsonValue, StrictInt, StrictStr, field_validator, model_validator

from frp_master_connection.api.beam_concrete_paired_angle_schemas import ExternalAnchorGeometryDTO
from frp_master_connection.api.paired_clip_angle_schemas import PairedConnectedProfileDTO
from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    MemberProfileFamily,
    MemberProfileSurfaceId,
)

DIRECT_SIDE_LAP_CONCRETE_API_TRANSPORT_SCHEMA_VERSION = "0.1.0-draft"


class DirectSideLapWallGeometryDTO(_StrictModel):
    run_length: QuantityDTO
    transverse_width: QuantityDTO
    thickness: QuantityDTO


class DirectSideLapAnchorPatternDTO(_StrictModel):
    row_count: StrictInt
    anchors_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    centroid_distance_behind_free_end: QuantityDTO
    transverse_offset: QuantityDTO


class DirectSideLapConcreteRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.5B-RC1"] = "3.5B-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    wall: DirectSideLapWallGeometryDTO
    side_lap_length: QuantityDTO
    member_projection_beyond_wall: QuantityDTO
    connected_profile: PairedConnectedProfileDTO
    anchor_pattern: DirectSideLapAnchorPatternDTO
    external_anchor: ExternalAnchorGeometryDTO
    axial_force: QuantityDTO
    major_shear: QuantityDTO
    minor_shear: QuantityDTO
    user_moment_lsn: DecimalVector3DTO | None = None

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value

    @model_validator(mode="after")
    def validate_profile_scope(self) -> DirectSideLapConcreteRequestDTO:
        family = self.connected_profile.profile_family
        surface = self.connected_profile.selected_profile_surface
        if family not in {MemberProfileFamily.ANGLE, MemberProfileFamily.CHANNEL}:
            raise ValueError("Stage 3.5B accepts only Angle or Channel profiles.")
        if (
            family is MemberProfileFamily.CHANNEL
            and surface is not MemberProfileSurfaceId.WEB_OUTER
        ):
            raise ValueError("CHANNEL_WEB_CONTACT_ONLY")
        if family is MemberProfileFamily.ANGLE and surface not in {
            MemberProfileSurfaceId.LEG_Y_OUTER,
            MemberProfileSurfaceId.LEG_Z_OUTER,
        }:
            raise ValueError("ANGLE_SELECTED_LEG_CONTACT_REQUIRED")
        return self


class DirectSideLapConcretePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5B-RC1"]
    preview_schema_version: Literal["0.1.0-draft"]
    request_id: StrictStr
    geometry_status: Literal["VALID", "INVALID_GEOMETRY"]
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: Literal["FAIL", "NOT_EVALUATED", "INVALID_GEOMETRY"]
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    external_design_required: Literal[True]
    engineering_fingerprint: StrictStr
    application_fingerprint: StrictStr
    result: dict[str, JsonValue]


class DirectSideLapConcreteDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5B-RC1"]
    request_id: StrictStr
    assembly_status: Literal["FAIL", "NOT_EVALUATED", "INVALID_GEOMETRY"]
    required_check_status: Literal["NOT_EVALUATED"]
    ordinary_pass_allowed: Literal[False]
    external_design_required: Literal[True]
    supported_local_frp_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "DIRECT_SIDE_LAP_CONCRETE_API_TRANSPORT_SCHEMA_VERSION",
    "DirectSideLapConcreteDesignResponseDTO",
    "DirectSideLapConcretePreviewResponseDTO",
    "DirectSideLapConcreteRequestDTO",
)
