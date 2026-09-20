"""Strict stateless DCTN API: primary FRP and independent hardware, no body selector."""

from dataclasses import fields, is_dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import JsonValue, StrictBool, StrictInt, StrictStr

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.stainless_activation import material_selection
from frp_master_connection.api.wi_frp_support_moment_mapping import _hardware
from frp_master_connection.api.wi_frp_support_moment_schemas import SupportHardwareDTO
from frp_master_connection.api.wi_wall_moment_mapping import _q
from frp_master_connection.application.double_channel_truss_node import (
    DCTNDesign,
    DCTNPreview,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.dctn_sources import EMPTY_SOURCES, DCTNSources
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNChannel,
    DCTNFastener,
    DCTNForm,
    DCTNMember,
    DCTNPattern,
    DCTNRequest,
    DCTNSection,
    default_dctn_request,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


class DCTNSectionDTO(_StrictModel):
    form: DCTNForm
    length: QuantityDTO
    depth: QuantityDTO
    width: QuantityDTO
    wall_or_web: QuantityDTO
    flange_thickness: QuantityDTO


class DCTNPatternDTO(_StrictModel):
    rows: StrictInt
    across: StrictInt
    first_from_start: QuantityDTO
    pitch: QuantityDTO
    wi_offset: QuantityDTO
    staggered: StrictBool = False


class DCTNMemberDTO(_StrictModel):
    slot: Literal["V", "D1", "D2"]
    section: DCTNSectionDTO
    start: tuple[QuantityDTO, QuantityDTO, QuantityDTO]
    inclination_deg: StrictStr
    axial_force: QuantityDTO
    pattern: DCTNPatternDTO
    material_source_reference: StrictStr = ""
    local_path_source_reference: StrictStr = ""
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class DCTNChannelDTO(_StrictModel):
    length: QuantityDTO
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    material_source_reference: StrictStr = ""
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class DCTNFastenerDTO(_StrictModel):
    diameter: QuantityDTO
    hole_diameter: QuantityDTO
    hardware: SupportHardwareDTO
    source_reference: StrictStr = ""
    threads_excluded: StrictBool = True
    snug_tight: StrictBool = True
    product_id: Literal["ASTM_F593_GROUP2_316"] = "ASTM_F593_GROUP2_316"


class DCTNRequestDTO(_StrictModel):
    request_id: StrictStr
    unit_system: Literal["US", "SI"]
    length_unit: Literal["in", "mm"]
    arrangement: DCTNArrangement
    channel: DCTNChannelDTO
    members: tuple[DCTNMemberDTO, ...]
    fastener: DCTNFastenerDTO
    shared_channel_source_reference: StrictStr = ""
    contract: Literal["DCTN-2-RC1"] = "DCTN-2-RC1"


def map_dctn_request(dto: DCTNRequestDTO) -> DCTNRequest:
    members = tuple(
        DCTNMember(
            m.slot,
            DCTNSection(
                m.section.form,
                _q(m.section.length),
                _q(m.section.depth),
                _q(m.section.width),
                _q(m.section.wall_or_web),
                _q(m.section.flange_thickness),
            ),
            (_q(m.start[0]), _q(m.start[1]), _q(m.start[2])),
            Decimal(m.inclination_deg),
            _q(m.axial_force),
            DCTNPattern(
                m.pattern.rows,
                m.pattern.across,
                _q(m.pattern.first_from_start),
                _q(m.pattern.pitch),
                _q(m.pattern.wi_offset),
                m.pattern.staggered,
            ),
            m.material_source_reference,
            m.local_path_source_reference,
            m.material_id,
        )
        for m in dto.members
    )
    c, f = dto.channel, dto.fastener
    return DCTNRequest(
        dto.request_id,
        dto.unit_system,
        Unit(dto.length_unit),
        dto.arrangement,
        DCTNChannel(
            _q(c.length),
            _q(c.depth),
            _q(c.flange_width),
            _q(c.web_thickness),
            _q(c.flange_thickness),
            c.material_source_reference,
            c.material_id,
        ),
        members,
        DCTNFastener(
            _q(f.diameter),
            _q(f.hole_diameter),
            _hardware(f.hardware),
            f.source_reference,
            f.threads_excluded,
            f.snug_tight,
            f.product_id,
        ),
        dto.shared_channel_source_reference,
        dto.contract,
    )


def serialize_dctn_value(value: object) -> JsonValue:
    if isinstance(value, PhysicalQuantity):
        return {"value": str(value.magnitude), "unit": value.unit.value}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Fraction):
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: serialize_dctn_value(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [serialize_dctn_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_dctn_value(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported DCTN transport value: {type(value).__name__}")


def convert_dctn_units(dto: DCTNRequestDTO, si: bool) -> DCTNRequestDTO:
    targets = {
        Dimension.LENGTH: Unit.MM if si else Unit.IN,
        Dimension.FORCE: Unit.KN if si else Unit.KIP,
    }

    def convert(value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            if set(value) == {"value", "unit"}:
                quantity = _q(QuantityDTO.model_validate(value))
                return serialize_dctn_value(quantity.to(targets[quantity.dimension]))
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    payload = cast(dict[str, JsonValue], convert(cast(JsonValue, dto.model_dump(mode="json"))))
    payload["unit_system"], payload["length_unit"] = ("SI", "mm") if si else ("US", "in")
    return DCTNRequestDTO.model_validate(payload)


def dctn_response(value: DCTNPreview | DCTNDesign) -> dict[str, JsonValue]:
    preview = value.preview if isinstance(value, DCTNDesign) else value
    return {
        "api_transport_schema_version": "DCTN-2-API-RC1",
        "request_id": preview.input.request_id,
        "contract": "DCTN-2-RC1",
        "geometry_status": preview.geometry.status,
        "geometry_invalid_reasons": list(preview.geometry.reasons),
        "engineering_fingerprint": preview.fingerprint,
        "whole_connection_status": value.whole_connection_status
        if isinstance(value, DCTNDesign)
        else "NOT_CHECKED",
        "result": {
            "preview": serialize_dctn_value(preview),
            "design": serialize_dctn_value(value) if isinstance(value, DCTNDesign) else None,
        },
    }


def build_dctn_router(
    identity_resolver: TrustedIdentityResolver, sources: DCTNSources = EMPTY_SOURCES
) -> APIRouter:
    # Versioned transport shares the historical strict section/hardware DTOs.
    from frp_master_connection.api.dctn3b import (
        DCTN3BRequestDTO,
        convert_dctn3b_units,
        dctn3b_defaults,
        dctn3b_response,
        map_dctn3b_request,
    )
    from frp_master_connection.application.dctn3b import (
        design_check_dctn3b,
        preview_dctn3b,
    )

    router = APIRouter(prefix="/api/v1/calculations/double-channel-truss-node")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)

    @router.get("/defaults")
    async def defaults(
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        arrangement: DCTNArrangement = DCTNArrangement.VERTICAL_ONLY,
        unit_system: Literal["US", "SI"] = "US",
        contract: Literal["DCTN-2-RC1", "DCTN-3B-RC1"] = "DCTN-3B-RC1",
    ) -> DCTNRequestDTO | DCTN3BRequestDTO:
        if contract == "DCTN-3B-RC1":
            return dctn3b_defaults(arrangement, unit_system == "SI")
        dto = DCTNRequestDTO.model_validate(serialize_dctn_value(default_dctn_request(arrangement)))
        return convert_dctn_units(dto, unit_system == "SI") if unit_system == "SI" else dto

    @router.post("/convert-units")
    async def convert_units(
        request: DCTNRequestDTO | DCTN3BRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        unit_system: Literal["US", "SI"],
    ) -> DCTNRequestDTO | DCTN3BRequestDTO:
        try:
            if isinstance(request, DCTN3BRequestDTO):
                return convert_dctn3b_units(request, unit_system == "SI")
            map_dctn_request(request)
            return convert_dctn_units(request, unit_system == "SI")
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "CANONICAL_DCTN_INPUT_INVALID", "message": str(error)},
            ) from error

    def execute(
        request: DCTNRequestDTO | DCTN3BRequestDTO, material: str, *, design: bool
    ) -> dict[str, JsonValue]:
        if material != "FRP":
            raise HTTPException(
                status_code=422, detail={"code": "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"}
            )
        try:
            if isinstance(request, DCTN3BRequestDTO):
                relative = map_dctn3b_request(request)
                return dctn3b_response(
                    design_check_dctn3b(relative, sources) if design else preview_dctn3b(relative)
                )
            value = map_dctn_request(request)
            return dctn_response(
                design_check_dctn(value, sources) if design else preview_dctn(value)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "CANONICAL_DCTN_INPUT_INVALID", "message": str(error)},
            ) from error

    @router.post("/preview")
    async def preview(
        request: DCTNRequestDTO | DCTN3BRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> dict[str, JsonValue]:
        return execute(request, material, design=False)

    @router.post("/design-check")
    async def design(
        request: DCTNRequestDTO | DCTN3BRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> dict[str, JsonValue]:
        return execute(request, material, design=True)

    return router
