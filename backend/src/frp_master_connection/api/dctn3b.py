"""Strict DCTN-3B transport; trusted responses are never request fields."""

from decimal import Decimal
from typing import Literal

from pydantic import JsonValue, StrictStr, model_validator

from frp_master_connection.api.double_channel_truss_node import (
    DCTNChannelDTO,
    DCTNFastenerDTO,
    DCTNPatternDTO,
    DCTNRequestDTO,
    DCTNSectionDTO,
    convert_dctn_units,
    map_dctn_request,
    serialize_dctn_value,
)
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.wi_wall_moment_mapping import _q
from frp_master_connection.application.dctn3b import (
    DCTN3BDesign,
    DCTN3BPreview,
    design_check_dctn3b,
    preview_dctn3b,
)
from frp_master_connection.application.double_channel_truss_node import (
    DCTNDesign,
    DCTNPreview,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.dctn3b import (
    CONTRACT,
    DATUM,
    DCTN3BMember,
    DCTN3BRequest,
    default_dctn3b_request,
    migrate_dctn2,
)
from frp_master_connection.domain.double_channel_truss_node import DCTNArrangement, DCTNRequest


class DCTN3BMemberDTO(_StrictModel):
    slot: Literal["V", "D1", "D2"]
    section: DCTNSectionDTO
    chord_station: QuantityDTO
    end_center_above_lower_web: QuantityDTO
    inclination_deg: StrictStr
    P: QuantityDTO
    Qp: QuantityDTO
    Qq: QuantityDTO
    pattern: DCTNPatternDTO
    material_source_reference: StrictStr = ""
    local_path_source_reference: StrictStr = ""
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"

    @model_validator(mode="before")
    @classmethod
    def reject_other_authorities(cls, value: object) -> object:
        if isinstance(value, dict):
            if any(
                k in value
                for k in (
                    "start",
                    "global_start",
                    "global_start_x",
                    "global_start_y",
                    "global_start_z",
                )
            ):
                raise ValueError("DCTN_PLACEMENT_CONTRACT_CONFLICT")
            if any(k in value for k in ("direction", "derived_direction", "dx", "dy", "dz")):
                raise ValueError("DCTN_DIRECTION_COMPONENTS_NOT_ACCEPTED")
            if any(k in value for k in ("moment", "free_moment", "Mx", "My", "Mz")):
                raise ValueError("DCTN_FREE_MOMENT_INPUT_NOT_SUPPORTED")
        return value


class DCTN3BRequestDTO(_StrictModel):
    request_id: StrictStr
    unit_system: Literal["US", "SI"]
    length_unit: Literal["in", "mm"]
    arrangement: DCTNArrangement
    channel: DCTNChannelDTO
    members: tuple[DCTN3BMemberDTO, ...]
    fastener: DCTNFastenerDTO
    shared_channel_source_reference: StrictStr = ""
    placement_datum: StrictStr = DATUM
    contract: Literal["DCTN-3B-RC1"]


def map_dctn3b_request(dto: DCTN3BRequestDTO) -> DCTN3BRequest:
    # Use the historical strict mapping for unchanged section/pattern/hardware fields.
    raw = dto.model_dump(mode="json")
    raw.pop("placement_datum")
    raw["contract"] = "DCTN-2-RC1"
    raw["members"] = [
        {
            **{
                k: v
                for k, v in m.model_dump(mode="json").items()
                if k not in {"chord_station", "end_center_above_lower_web", "P", "Qp", "Qq"}
            },
            "start": [{"value": "0", "unit": dto.length_unit}] * 3,
            "axial_force": m.P.model_dump(mode="json"),
        }
        for m in dto.members
    ]
    old = map_dctn_request(DCTNRequestDTO.model_validate(raw))
    members = tuple(
        DCTN3BMember(
            m.slot,
            inherited.section,
            _q(m.chord_station),
            _q(m.end_center_above_lower_web),
            Decimal(m.inclination_deg),
            _q(m.P),
            _q(m.Qp),
            _q(m.Qq),
            inherited.pattern,
            m.material_source_reference,
            m.local_path_source_reference,
            m.material_id,
        )
        for m, inherited in zip(dto.members, old.members, strict=True)
    )
    return DCTN3BRequest(
        old.request_id,
        old.unit_system,
        old.length_unit,
        old.arrangement,
        old.channel,
        members,
        old.fastener,
        old.shared_channel_source_reference,
        dto.placement_datum,
        dto.contract,
    )


def migrate_dctn2_dto(dto: DCTNRequestDTO) -> DCTN3BRequestDTO:
    return DCTN3BRequestDTO.model_validate(
        serialize_dctn_value(migrate_dctn2(map_dctn_request(dto)))
    )


def dctn3b_defaults(arrangement: DCTNArrangement, si: bool) -> DCTN3BRequestDTO:
    dto = DCTN3BRequestDTO.model_validate(serialize_dctn_value(default_dctn3b_request(arrangement)))
    return convert_dctn3b_units(dto, si) if si else dto


def convert_dctn3b_units(dto: DCTN3BRequestDTO, si: bool) -> DCTN3BRequestDTO:
    native = map_dctn3b_request(dto)
    legacy = DCTNRequestDTO.model_validate(serialize_dctn_value(native.legacy_geometry_request()))
    converted = migrate_dctn2_dto(convert_dctn_units(legacy, si))
    target_length = Unit(converted.members[0].chord_station.unit)
    target_force = Unit(converted.members[0].P.unit)
    payload = converted.model_dump(mode="json")
    # Relative coordinates, not converted global positions, remain input authority.
    for target, source in zip(payload["members"], dto.members, strict=True):
        for name in ("chord_station", "end_center_above_lower_web"):
            target[name] = serialize_dctn_value(_q(getattr(source, name)).to(target_length))
        for name in ("P", "Qp", "Qq"):
            target[name] = serialize_dctn_value(_q(getattr(source, name)).to(target_force))
    return DCTN3BRequestDTO.model_validate(payload)


def map_versioned_dctn(dto: DCTNRequestDTO | DCTN3BRequestDTO) -> DCTNRequest | DCTN3BRequest:
    return map_dctn3b_request(dto) if isinstance(dto, DCTN3BRequestDTO) else map_dctn_request(dto)


def preview_versioned_dctn(value: DCTNRequest | DCTN3BRequest) -> DCTNPreview | DCTN3BPreview:
    return preview_dctn3b(value) if isinstance(value, DCTN3BRequest) else preview_dctn(value)


def design_versioned_dctn(value: DCTNRequest | DCTN3BRequest) -> DCTNDesign | DCTN3BDesign:
    return (
        design_check_dctn3b(value) if isinstance(value, DCTN3BRequest) else design_check_dctn(value)
    )


def dctn3b_response(value: DCTN3BPreview | DCTN3BDesign) -> dict[str, JsonValue]:
    design = value if isinstance(value, DCTN3BDesign) else None
    preview = value.preview if isinstance(value, DCTN3BDesign) else value
    return {
        "api_transport_schema_version": "DCTN-3B-API-RC1",
        "request_id": preview.input.request_id,
        "contract": CONTRACT,
        "geometry_status": preview.geometry_status,
        "geometry_invalid_reasons": list(preview.geometry.reasons),
        "demand_status": preview.demand_status,
        "response_status": preview.response_status,
        "qualification_status": preview.qualification_status
        if design is None
        else ("REQUIRED_QUALIFICATION_MISSING" if design.blockers else "EVALUATED"),
        "design_status": preview.design_status
        if design is None
        else design.whole_connection_status,
        "whole_connection_status": preview.design_status
        if design is None
        else design.whole_connection_status,
        "engineering_fingerprint": preview.fingerprint,
        "result": {
            "preview": serialize_dctn_value(preview),
            "design": serialize_dctn_value(design),
        },
    }
