"""Strict stateless Stage 3.6A web-splice API contracts."""

from typing import Literal

from pydantic import JsonValue, StrictBool, StrictInt, StrictStr, field_validator

from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import EngineeringUnitSystem

WEB_SPLICE_API_TRANSPORT_SCHEMA_VERSION = "0.1.0-draft"


class WebSpliceBeamGeometryDTO(_StrictModel):
    profile_family: Literal["WIDE_FLANGE_I"] = "WIDE_FLANGE_I"
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    display_length_each_side: QuantityDTO


class WebSplicePlateGeometryDTO(_StrictModel):
    length: QuantityDTO
    height: QuantityDTO
    thickness: QuantityDTO
    count: StrictInt = 2
    locked_identical: StrictBool = True


class WebSpliceBoltGroupDTO(_StrictModel):
    rows: StrictInt
    bolts_per_row: StrictInt
    vertical_pitch: QuantityDTO
    longitudinal_gauge: QuantityDTO
    centroid_offset: QuantityDTO
    locked_identical_mirror: StrictBool = True


class WebSpliceForceDTO(_StrictModel):
    axial_force: QuantityDTO
    major_shear: QuantityDTO
    minor_shear: QuantityDTO


class WebSpliceRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.6A-RC1", "3.6B-RC2"] = "3.6A-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beam: WebSpliceBeamGeometryDTO
    beam_end_gap: QuantityDTO
    splice_plate: WebSplicePlateGeometryDTO
    bolt_group: WebSpliceBoltGroupDTO
    bolt_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    transfer_force: WebSpliceForceDTO
    user_moment_l_v_t: DecimalVector3DTO
    flange_splice_enabled: StrictBool = False

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


class WebSplicePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.6A-RC1", "3.6B-RC2"]
    preview_schema_version: Literal["0.1.0-draft", "0.2.0-draft"]
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


class WebSpliceDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.6A-RC1", "3.6B-RC2"]
    request_id: StrictStr
    assembly_status: Literal[
        "FAIL",
        "NOT_EVALUATED",
        "INVALID_GEOMETRY",
        "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED",
    ]
    required_check_status: Literal[
        "FAIL", "NOT_EVALUATED", "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"
    ]
    ordinary_pass_allowed: Literal[False]
    supported_local_checks_executed: bool
    supported_local_failure_present: bool
    local_check_ids: tuple[StrictStr, ...]
    failed_local_check_ids: tuple[StrictStr, ...]
    local_resistance_warnings: tuple[StrictStr, ...]
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "WEB_SPLICE_API_TRANSPORT_SCHEMA_VERSION",
    "WebSpliceBeamGeometryDTO",
    "WebSpliceBoltGroupDTO",
    "WebSpliceDesignResponseDTO",
    "WebSpliceForceDTO",
    "WebSplicePlateGeometryDTO",
    "WebSplicePreviewResponseDTO",
    "WebSpliceRequestDTO",
)
