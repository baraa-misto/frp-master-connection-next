"""Strict stateless transport contracts for the Stage 3.5A connection."""

from __future__ import annotations

from typing import Literal

from pydantic import JsonValue, StrictInt, StrictStr, field_validator, model_validator

from frp_master_connection.api.clip_angle_schemas import (
    ClipAngleBoltLayoutDTO,
    ClipAngleDimensionsDTO,
)
from frp_master_connection.api.paired_clip_angle_schemas import PairedConnectedProfileDTO
from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import EngineeringUnitSystem, MemberProfileFamily

BEAM_CONCRETE_PAIRED_ANGLE_API_TRANSPORT_SCHEMA_VERSION = "0.1.0-draft"


class ConcreteWallGeometryDTO(_StrictModel):
    width: QuantityDTO
    height: QuantityDTO
    thickness: QuantityDTO
    connection_origin_h: QuantityDTO
    connection_origin_v: QuantityDTO


class WallAnchorPatternDTO(_StrictModel):
    row_count: StrictInt
    anchors_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    centroid_offset_h: QuantityDTO
    centroid_v: QuantityDTO


class ExternalAnchorGeometryDTO(_StrictModel):
    nominal_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    specified_embedment: QuantityDTO
    washer_outside_diameter: QuantityDTO
    washer_thickness: QuantityDTO
    system_classification: Literal["EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR"] = (
        "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR"
    )


class BeamConcretePairedAngleRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.5A-RC1", "3.5A-R1-RC1", "3.5A-R2-RC1"] = (
        "3.5A-R2-RC1"
    )
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    wall: ConcreteWallGeometryDTO
    beam_profile: PairedConnectedProfileDTO
    beam_end_gap: QuantityDTO
    connector_dimensions: ClipAngleDimensionsDTO
    connector_length_anchor_position: QuantityDTO
    common_beam_layout: ClipAngleBoltLayoutDTO
    wall_anchor_pattern: WallAnchorPatternDTO
    common_bolt_diameter: QuantityDTO
    common_hole_diameter: QuantityDTO
    external_anchor: ExternalAnchorGeometryDTO
    reaction_shear: QuantityDTO | None = None
    user_force_hvn: DecimalVector3DTO | None = None
    user_moment_hvn: DecimalVector3DTO | None = None
    major_shear: QuantityDTO | None = None
    minor_shear: QuantityDTO | None = None
    axial_force: QuantityDTO | None = None

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value

    @model_validator(mode="after")
    def validate_contract_profile_scope(self) -> BeamConcretePairedAngleRequestDTO:
        if (
            self.orchestration_contract_version == "3.5A-RC1"
            and self.beam_profile.profile_family is not MemberProfileFamily.WIDE_FLANGE_I
        ):
            raise ValueError("Historical Stage 3.5A accepts only the W/I connected profile.")
        historical = self.orchestration_contract_version in {"3.5A-RC1", "3.5A-R1-RC1"}
        legacy_values = (self.reaction_shear, self.user_force_hvn, self.user_moment_hvn)
        successor_values = (self.major_shear, self.minor_shear, self.axial_force)
        if historical and (
            any(item is None for item in legacy_values)
            or any(item is not None for item in successor_values)
        ):
            raise ValueError(
                "Historical Stage 3.5A contracts require only reaction_shear and user_force_hvn."
            )
        if not historical and (
            any(item is None for item in successor_values)
            or self.reaction_shear is not None
            or self.user_force_hvn is not None
        ):
            raise ValueError(
                "Stage 3.5A-R2 requires exactly major_shear, minor_shear, and axial_force."
            )
        return self


class BeamConcretePairedAnglePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5A-RC1", "3.5A-R1-RC1", "3.5A-R2-RC1"]
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


class BeamConcretePairedAngleDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5A-RC1", "3.5A-R1-RC1", "3.5A-R2-RC1"]
    request_id: StrictStr
    assembly_status: Literal["FAIL", "NOT_EVALUATED", "INVALID_GEOMETRY"]
    required_check_status: Literal["NOT_EVALUATED"]
    ordinary_pass_allowed: Literal[False]
    external_design_required: Literal[True]
    supported_beam_side_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "BEAM_CONCRETE_PAIRED_ANGLE_API_TRANSPORT_SCHEMA_VERSION",
    "BeamConcretePairedAngleDesignResponseDTO",
    "BeamConcretePairedAnglePreviewResponseDTO",
    "BeamConcretePairedAngleRequestDTO",
    "ConcreteWallGeometryDTO",
    "ExternalAnchorGeometryDTO",
    "WallAnchorPatternDTO",
)
