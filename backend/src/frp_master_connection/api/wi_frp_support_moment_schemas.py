"""Strict decimal-string Stage 4.3 DTOs; no client-supplied qualification/strength."""

from typing import Literal

from pydantic import JsonValue, StrictStr

from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.web_splice_schemas import WebSpliceBeamGeometryDTO
from frp_master_connection.api.wi_wall_moment_schemas import (
    WallMomentActionsDTO,
    WallMomentAngleGeometryDTO,
    WallMomentPatternDTO,
)
from frp_master_connection.domain.wi_frp_support_moment import SupportMode


class SupportHardwareDTO(_StrictModel):
    washer_diameter: QuantityDTO
    washer_thickness: QuantityDTO
    head_across_flats: QuantityDTO
    head_height: QuantityDTO
    nut_across_flats: QuantityDTO
    nut_height: QuantityDTO
    end_extension: QuantityDTO
    geometry_source: StrictStr


class FRPSupportFastenerDTO(_StrictModel):
    bolt_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    source_authority_id: StrictStr
    thread_condition: Literal["INCLUDED", "EXCLUDED"]


class FRPMomentAngleDTO(_StrictModel):
    geometry: WallMomentAngleGeometryDTO
    member_pattern: WallMomentPatternDTO
    support_pattern: WallMomentPatternDTO
    fastener: FRPSupportFastenerDTO
    support_fastener: FRPSupportFastenerDTO
    member_hardware: SupportHardwareDTO
    support_hardware: SupportHardwareDTO
    connector_source_reference: StrictStr = ""
    attachment_source_reference: StrictStr = ""
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"
    provider_id: Literal["FRP"] = "FRP"


class ReceivingSupportDTO(_StrictModel):
    mode: SupportMode
    face: StrictStr
    depth: QuantityDTO
    width: QuantityDTO
    web_or_wall_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    physical_length: QuantityDTO
    connection_height: QuantityDTO
    connection_transverse: QuantityDTO
    view_length: QuantityDTO
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class WIFrpSupportMomentRequestDTO(_StrictModel):
    contract: Literal["4.3-RC1"] = "4.3-RC1"
    request_id: StrictStr
    beam: WebSpliceBeamGeometryDTO
    beam_physical_length: QuantityDTO
    gap: QuantityDTO
    support: ReceivingSupportDTO
    top: FRPMomentAngleDTO
    bottom: FRPMomentAngleDTO
    positive_web: FRPMomentAngleDTO
    negative_web: FRPMomentAngleDTO
    actions: WallMomentActionsDTO
    response_source_reference: StrictStr = ""
    local_zone_source_reference: StrictStr = ""
    beam_material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class WIFrpSupportMomentResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.3-API-RC1"] = "4.3-API-RC1"
    contract: Literal["4.3-RC1"] = "4.3-RC1"
    request_id: StrictStr
    geometry_status: StrictStr
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: StrictStr
    whole_connection_status: Literal[
        "LOCAL_SUPPORT_COMPLETENESS_AND_OVERALL_MEMBER_ANALYSIS_REQUIRED"
    ] = "LOCAL_SUPPORT_COMPLETENESS_AND_OVERALL_MEMBER_ANALYSIS_REQUIRED"
    ordinary_pass_allowed: Literal[False] = False
    resistance_evaluated: bool
    design_check_ready: bool
    engineering_fingerprint: StrictStr
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]
