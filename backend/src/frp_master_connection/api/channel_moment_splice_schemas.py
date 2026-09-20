"""Strict stateless Stage 4.1B Channel moment-splice API contracts."""

from typing import Literal

from pydantic import JsonValue, StrictBool, StrictInt, StrictStr, field_validator

from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.web_splice_schemas import (
    WebSpliceBoltGroupDTO,
    WebSplicePlateGeometryDTO,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import EngineeringUnitSystem

CHANNEL_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION = "4.1B-API-RC1"


class ChannelMomentSpliceBeamGeometryDTO(_StrictModel):
    profile_family: Literal["CHANNEL"] = "CHANNEL"
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    display_length_each_side: QuantityDTO
    equal_flange: StrictBool = True
    lipped: StrictBool = False
    back_to_back: StrictBool = False


class ChannelMomentSpliceActionsDTO(_StrictModel):
    axial_force_l: QuantityDTO
    major_shear_v: QuantityDTO
    major_moment_t: QuantityDTO


class ChannelMomentSpliceShearCenterDTO(_StrictModel):
    method: Literal[
        "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1",
        "EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1",
    ]
    explicit_coordinate_t: QuantityDTO | None = None
    explicit_provenance: StrictStr | None = None
    include_rational_comparison: StrictBool = False


class ChannelMomentSpliceFlangeGeometryDTO(_StrictModel):
    plate_length: QuantityDTO
    plate_thickness: QuantityDTO
    inner_plate_width: QuantityDTO
    transverse_gauge: QuantityDTO
    bolts_per_transverse_line: StrictInt
    longitudinal_pitch: QuantityDTO
    group_centroid_distance: QuantityDTO
    outer_plate_count_per_flange: StrictInt = 1
    inner_plate_count_per_flange: StrictInt = 1
    locked_top_bottom_identical: StrictBool = True


class ChannelMomentSpliceFastenerDTO(_StrictModel):
    bolt_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    source_authority_id: StrictStr
    thread_condition: Literal["INCLUDED", "EXCLUDED"]
    nominal_shear_stress: QuantityDTO | None = None


class ChannelMomentSpliceRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["4.1B-RC1"] = "4.1B-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beams_locked_identical: StrictBool = True
    beams_same_orientation: StrictBool = True
    opening_direction: Literal["+T_CH"] = "+T_CH"
    beam: ChannelMomentSpliceBeamGeometryDTO
    beam_end_gap: QuantityDTO
    web_splice_plate: WebSplicePlateGeometryDTO
    web_bolt_group: WebSpliceBoltGroupDTO
    web_fastener: ChannelMomentSpliceFastenerDTO
    flange_geometry: ChannelMomentSpliceFlangeGeometryDTO
    flange_fastener: ChannelMomentSpliceFastenerDTO
    actions: ChannelMomentSpliceActionsDTO
    shear_center: ChannelMomentSpliceShearCenterDTO

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


class ChannelMomentSplicePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.1B-API-RC1"]
    orchestration_contract_version: Literal["4.1B-RC1"]
    preview_schema_version: Literal["4.1B-PREVIEW-RC1"]
    request_id: StrictStr
    geometry_status: Literal["VALID", "INVALID_GEOMETRY"]
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: Literal["NOT_EVALUATED", "INVALID_GEOMETRY"]
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    engineering_fingerprint: StrictStr
    application_fingerprint: StrictStr
    result: dict[str, JsonValue]


class ChannelMomentSpliceDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.1B-API-RC1"]
    orchestration_contract_version: Literal["4.1B-RC1"]
    request_id: StrictStr
    assembly_status: Literal[
        "FAIL",
        "NOT_EVALUATED",
        "INVALID_GEOMETRY",
        "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED",
    ]
    required_check_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    failed_check_ids: tuple[StrictStr, ...]
    unavailable_check_ids: tuple[StrictStr, ...]
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "CHANNEL_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION",
    "ChannelMomentSpliceActionsDTO",
    "ChannelMomentSpliceBeamGeometryDTO",
    "ChannelMomentSpliceDesignResponseDTO",
    "ChannelMomentSpliceFastenerDTO",
    "ChannelMomentSpliceFlangeGeometryDTO",
    "ChannelMomentSplicePreviewResponseDTO",
    "ChannelMomentSpliceRequestDTO",
    "ChannelMomentSpliceShearCenterDTO",
)
