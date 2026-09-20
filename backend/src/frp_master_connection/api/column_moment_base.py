"""Authenticated stateless Stage 4.5 API. Clients cannot install qualified sources."""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import JsonValue, StrictStr

from frp_master_connection.api.angle_column_moment_base import (
    AngleBaseActionsDTO,
    AngleBaseConnectorDTO,
    AngleBaseFoundationDTO,
)
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.stainless_activation import (
    material_selection,
    stainless_design_response,
)
from frp_master_connection.api.wi_frp_support_moment_mapping import _hardware
from frp_master_connection.api.wi_wall_moment_mapping import _angle, _q, serialize_wall_moment_value
from frp_master_connection.application.column_moment_base_design import (
    ColumnMomentDesign,
    evaluate_column_moment_base,
)
from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    preview_column_moment_base,
)
from frp_master_connection.application.column_moment_base_sources import (
    EMPTY_SOURCES,
    ColumnMomentSourceRegistry,
)
from frp_master_connection.calculation.quantities import Dimension, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseConnector,
    AngleBaseFoundation,
)
from frp_master_connection.domain.column_moment_base import (
    ColumnMomentActions,
    ColumnMomentBaseRequest,
    MomentBaseColumn,
    default_column_moment_base_request,
    default_column_moment_base_ui_request,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


def convert_column_units(dto: ColumnMomentBaseRequestDTO, si: bool) -> ColumnMomentBaseRequestDTO:
    """Native quantity conversion only. No hole regeneration, geometry or source inference."""
    targets = {
        Dimension.LENGTH: Unit.MM if si else Unit.IN,
        Dimension.FORCE: Unit.KN if si else Unit.KIP,
        Dimension.MOMENT: Unit.KN_MM if si else Unit.KIP_IN,
    }

    def convert(value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            if set(value) == {"value", "unit"}:
                native = _q(QuantityDTO.model_validate(value))
                return serialize_wall_moment_value(native.to(targets[native.dimension]))
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    return ColumnMomentBaseRequestDTO.model_validate(
        convert(cast(JsonValue, dto.model_dump(mode="json")))
    )


class MomentBaseColumnDTO(_StrictModel):
    family: Literal["WI", "RHS", "SRS"]
    width: QuantityDTO
    depth: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    wall_thickness: QuantityDTO
    view_length: QuantityDTO
    offset_x: QuantityDTO
    offset_y: QuantityDTO
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class ColumnMomentBaseRequestDTO(_StrictModel):
    request_id: StrictStr
    contract: Literal["4.5-RC1"] = "4.5-RC1"
    column: MomentBaseColumnDTO
    layout: Literal["TWO_X", "TWO_Y", "FOUR_XY"]
    foundation: AngleBaseFoundationDTO
    x_positive: AngleBaseConnectorDTO
    x_negative: AngleBaseConnectorDTO
    y_positive: AngleBaseConnectorDTO
    y_negative: AngleBaseConnectorDTO
    actions: AngleBaseActionsDTO
    response_source_reference: StrictStr = ""
    column_zone_source_reference: StrictStr = ""


class ColumnMomentBaseResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.5-API-RC1"] = "4.5-API-RC1"
    contract: Literal["4.5-RC1"] = "4.5-RC1"
    request_id: StrictStr
    geometry_status: StrictStr
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: StrictStr
    whole_connection_status: Literal["EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"] = (
        "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    )
    ordinary_pass_allowed: Literal[False] = False
    resistance_evaluated: bool
    design_check_ready: bool
    engineering_fingerprint: StrictStr
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


def map_column_moment_base_request(dto: ColumnMomentBaseRequestDTO) -> ColumnMomentBaseRequest:
    def connector(c: AngleBaseConnectorDTO) -> AngleBaseConnector:
        return AngleBaseConnector(
            _angle(c.angle),
            _q(c.extrusion_center),
            _hardware(c.member_hardware),
            c.normal_response_source_reference,
            c.fastener_source_reference,
        )

    c, f, a = dto.column, dto.foundation, dto.actions
    return ColumnMomentBaseRequest(
        dto.request_id,
        MomentBaseColumn(
            c.family,
            _q(c.width),
            _q(c.depth),
            _q(c.web_thickness),
            _q(c.flange_thickness),
            _q(c.wall_thickness),
            _q(c.view_length),
            _q(c.offset_x),
            _q(c.offset_y),
            c.material_id,
        ),
        dto.layout,
        AngleBaseFoundation(_q(f.width_x), _q(f.width_y), _q(f.depth)),
        connector(dto.x_positive),
        connector(dto.x_negative),
        connector(dto.y_positive),
        connector(dto.y_negative),
        ColumnMomentActions(
            _q(a.axial),
            _q(a.shear_x),
            _q(a.shear_y),
            _q(a.moment_x),
            _q(a.moment_y),
            _q(a.applied_torque_z),
        ),
        dto.response_source_reference,
        dto.column_zone_source_reference,
        dto.contract,
    )


def serialize_column_moment_base(
    value: ColumnMomentPreview | ColumnMomentDesign,
) -> ColumnMomentBaseResponseDTO:
    design = value if isinstance(value, ColumnMomentDesign) else None
    p = value.preview if isinstance(value, ColumnMomentDesign) else value
    return ColumnMomentBaseResponseDTO(
        request_id=p.request_id,
        geometry_status=p.geometry.status,
        geometry_invalid_reasons=p.geometry.reasons,
        assembly_status=p.branch_allocation_status if design is None else design.status,
        resistance_evaluated=False if design is None else design.resistance_evaluated,
        design_check_ready=p.design_check_ready,
        engineering_fingerprint=p.engineering_fingerprint,
        result_fingerprint=p.engineering_fingerprint
        if design is None
        else design.result_fingerprint,
        result={
            "preview": cast(dict[str, JsonValue], serialize_wall_moment_value(p)),
            "design": None
            if design is None
            else cast(dict[str, JsonValue], serialize_wall_moment_value(design)),
        },
    )


def build_column_moment_base_router(
    identity_resolver: TrustedIdentityResolver, sources: ColumnMomentSourceRegistry = EMPTY_SOURCES
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/calculations/wi-rhs-srs-column-moment-base")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)

    @router.post("/convert-units", response_model=ColumnMomentBaseRequestDTO)
    async def convert_units(
        request: ColumnMomentBaseRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        unit_system: Literal["US_CUSTOMARY", "SI"],
    ) -> ColumnMomentBaseRequestDTO:
        return convert_column_units(request, unit_system == "SI")

    @router.get("/defaults", response_model=ColumnMomentBaseRequestDTO)
    async def defaults(
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        unit_system: Literal["US_CUSTOMARY", "SI"] = "US_CUSTOMARY",
        preset: Literal["WI", "RHS", "SRS", "WI12", "RHS8", "RHS10X8", "SRS8", "SRS10X8"] = "WI",
        layout: Literal["TWO_X", "TWO_Y", "FOUR_XY"] = "FOUR_XY",
    ) -> ColumnMomentBaseRequestDTO:
        return ColumnMomentBaseRequestDTO.model_validate(
            serialize_wall_moment_value(
                default_column_moment_base_ui_request(preset, layout, si=unit_system == "SI")
                if preset in ("WI", "RHS", "SRS")
                else default_column_moment_base_request(preset, layout, si=unit_system == "SI")
            )
        )

    @router.post("/preview", response_model=ColumnMomentBaseResponseDTO)
    async def preview(
        request: ColumnMomentBaseRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> ColumnMomentBaseResponseDTO:
        try:
            return serialize_column_moment_base(
                preview_column_moment_base(map_column_moment_base_request(request), sources)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CANONICAL_COLUMN_MOMENT_BASE_INVALID",
                    "message": str(error),
                },
            ) from error

    @router.post("/design-check", response_model=ColumnMomentBaseResponseDTO)
    async def design(
        request: ColumnMomentBaseRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> ColumnMomentBaseResponseDTO | JSONResponse:
        try:
            response = evaluate_column_moment_base(map_column_moment_base_request(request), sources)
            if material == "SS316":
                return stainless_design_response("wi-rhs-srs-column-moment-base", response)
            return serialize_column_moment_base(response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CANONICAL_COLUMN_MOMENT_BASE_INVALID",
                    "message": str(error),
                },
            ) from error

    return router
