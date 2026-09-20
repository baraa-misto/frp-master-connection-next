"""Strict stateless Stage 4.2 transport; qualified sources are references only."""

from typing import Literal

from pydantic import JsonValue, StrictInt, StrictStr

from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    ConcreteWallGeometryDTO,
    ExternalAnchorGeometryDTO,
)
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.web_splice_schemas import WebSpliceBeamGeometryDTO
from frp_master_connection.api.wi_moment_splice_schemas import WIMomentSpliceFastenerDTO
from frp_master_connection.domain.values import EngineeringUnitSystem


class WallMomentAngleGeometryDTO(_StrictModel):
    length: QuantityDTO
    member_leg: QuantityDTO
    support_leg: QuantityDTO
    thickness: QuantityDTO
    inside_radius: QuantityDTO
    heel_end_reliefs: tuple[QuantityDTO, QuantityDTO]


class WallMomentPatternDTO(_StrictModel):
    across: StrictInt
    along: StrictInt
    gauge: QuantityDTO
    pitch: QuantityDTO
    center: QuantityDTO


class WallMomentAngleDTO(_StrictModel):
    geometry: WallMomentAngleGeometryDTO
    member_pattern: WallMomentPatternDTO
    support_pattern: WallMomentPatternDTO
    fastener: WIMomentSpliceFastenerDTO
    anchors: ExternalAnchorGeometryDTO
    connector_source_reference: StrictStr = ""
    attachment_source_reference: StrictStr = ""
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"
    provider_id: Literal["FRP"] = "FRP"


class WallMomentActionsDTO(_StrictModel):
    axial: QuantityDTO
    major_shear: QuantityDTO
    structural_major_moment: QuantityDTO


class WIWallMomentRequestDTO(_StrictModel):
    contract: Literal["4.2-RC1"] = "4.2-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Literal["in", "mm"]
    beam: WebSpliceBeamGeometryDTO
    gap: QuantityDTO
    wall: ConcreteWallGeometryDTO
    top: WallMomentAngleDTO
    bottom: WallMomentAngleDTO
    positive_web: WallMomentAngleDTO
    negative_web: WallMomentAngleDTO
    actions: WallMomentActionsDTO


class WIWallMomentResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.2-API-RC1"] = "4.2-API-RC1"
    contract: Literal["4.2-RC1"] = "4.2-RC1"
    request_id: StrictStr
    geometry_status: StrictStr
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: StrictStr
    whole_connection_status: Literal["EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"]
    ordinary_pass_allowed: Literal[False] = False
    resistance_evaluated: bool
    design_check_ready: bool
    engineering_fingerprint: StrictStr
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]
