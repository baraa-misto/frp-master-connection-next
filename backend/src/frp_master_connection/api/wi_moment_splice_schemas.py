"""Strict stateless Stage 4.1A moment-splice API contracts."""

from typing import Literal

from pydantic import JsonValue, StrictBool, StrictInt, StrictStr, field_validator

from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.web_splice_schemas import (
    WebSpliceBeamGeometryDTO,
    WebSpliceBoltGroupDTO,
    WebSplicePlateGeometryDTO,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import EngineeringUnitSystem

WI_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION = "4.1A-API-RC1"


class WIMomentSpliceActionsDTO(_StrictModel):
    axial_force_l: QuantityDTO
    major_shear_v: QuantityDTO
    major_moment_t: QuantityDTO


class WIMomentSpliceFlangeGeometryDTO(_StrictModel):
    plate_length: QuantityDTO
    plate_thickness: QuantityDTO
    inner_strip_width: QuantityDTO
    bolts_per_line: StrictInt
    longitudinal_pitch: QuantityDTO
    group_centroid_distance: QuantityDTO
    outer_plate_count_per_flange: StrictInt = 1
    inner_strip_count_per_flange: StrictInt = 2
    locked_top_bottom_identical: StrictBool = True
    locked_inner_symmetric: StrictBool = True


class WIMomentSpliceFastenerDTO(_StrictModel):
    bolt_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    source_authority_id: StrictStr
    thread_condition: Literal["INCLUDED", "EXCLUDED"]
    nominal_shear_stress: QuantityDTO | None = None


class WIMomentSpliceRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["4.1A-RC1"] = "4.1A-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    profile_family: Literal["WIDE_FLANGE_I"] = "WIDE_FLANGE_I"
    beams_locked_identical: StrictBool = True
    beam: WebSpliceBeamGeometryDTO
    beam_end_gap: QuantityDTO
    web_splice_plate: WebSplicePlateGeometryDTO
    web_bolt_group: WebSpliceBoltGroupDTO
    web_fastener: WIMomentSpliceFastenerDTO
    flange_geometry: WIMomentSpliceFlangeGeometryDTO
    flange_fastener: WIMomentSpliceFastenerDTO
    actions: WIMomentSpliceActionsDTO

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


class WIMomentSplicePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.1A-API-RC1"]
    orchestration_contract_version: Literal["4.1A-RC1"]
    preview_schema_version: Literal["4.1A-PREVIEW-RC1"]
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


class WIMomentSpliceDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.1A-API-RC1"]
    orchestration_contract_version: Literal["4.1A-RC1"]
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
    "WI_MOMENT_SPLICE_API_TRANSPORT_SCHEMA_VERSION",
    "WIMomentSpliceActionsDTO",
    "WIMomentSpliceDesignResponseDTO",
    "WIMomentSpliceFastenerDTO",
    "WIMomentSpliceFlangeGeometryDTO",
    "WIMomentSplicePreviewResponseDTO",
    "WIMomentSpliceRequestDTO",
)
