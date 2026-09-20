"""Authenticated, stateless Stage 4.4 transport; sources are server-owned only."""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import JsonValue, StrictStr

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.stainless_activation import (
    material_selection,
    stainless_design_response,
)
from frp_master_connection.api.wi_frp_support_moment_mapping import _hardware
from frp_master_connection.api.wi_frp_support_moment_schemas import SupportHardwareDTO
from frp_master_connection.api.wi_wall_moment_mapping import _angle, _q, serialize_wall_moment_value
from frp_master_connection.api.wi_wall_moment_schemas import WallMomentAngleDTO
from frp_master_connection.application.angle_column_base_design import (
    AngleBaseDesign,
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    preview_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_sources import (
    EMPTY_SOURCES,
    AngleBaseSourceRegistry,
)
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseActions,
    AngleBaseColumn,
    AngleBaseConnector,
    AngleBaseFoundation,
    AngleColumnMomentBaseRequest,
)
from frp_master_connection.domain.connection_workspace_defaults import (
    angle_column_workspace_default,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


class AngleBaseColumnDTO(_StrictModel):
    leg_x: QuantityDTO
    leg_y: QuantityDTO
    thickness: QuantityDTO
    view_length: QuantityDTO
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"] = "ICE_LOCKED_PULTRUDED_FRP"


class AngleBaseFoundationDTO(_StrictModel):
    width_x: QuantityDTO
    width_y: QuantityDTO
    depth: QuantityDTO


class AngleBaseConnectorDTO(_StrictModel):
    angle: WallMomentAngleDTO
    extrusion_center: QuantityDTO
    member_hardware: SupportHardwareDTO
    normal_response_source_reference: StrictStr = ""
    fastener_source_reference: StrictStr = ""


class AngleBaseActionsDTO(_StrictModel):
    axial: QuantityDTO
    shear_x: QuantityDTO
    shear_y: QuantityDTO
    moment_x: QuantityDTO
    moment_y: QuantityDTO
    applied_torque_z: QuantityDTO


class AngleBaseRequestDTO(_StrictModel):
    request_id: StrictStr
    contract: Literal["4.4-RC1"] = "4.4-RC1"
    column: AngleBaseColumnDTO
    foundation: AngleBaseFoundationDTO
    leg_1: AngleBaseConnectorDTO
    leg_2: AngleBaseConnectorDTO
    actions: AngleBaseActionsDTO
    response_source_reference: StrictStr = ""
    column_zone_source_reference: StrictStr = ""


class AngleBaseResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["4.4-API-RC1"] = "4.4-API-RC1"
    contract: Literal["4.4-RC1"] = "4.4-RC1"
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


def map_angle_base_request(dto: AngleBaseRequestDTO) -> AngleColumnMomentBaseRequest:
    def connector(c: AngleBaseConnectorDTO) -> AngleBaseConnector:
        return AngleBaseConnector(
            _angle(c.angle),
            _q(c.extrusion_center),
            _hardware(c.member_hardware),
            c.normal_response_source_reference,
            c.fastener_source_reference,
        )

    c, f, a = dto.column, dto.foundation, dto.actions
    return AngleColumnMomentBaseRequest(
        dto.request_id,
        AngleBaseColumn(
            _q(c.leg_x), _q(c.leg_y), _q(c.thickness), _q(c.view_length), c.material_id
        ),
        AngleBaseFoundation(_q(f.width_x), _q(f.width_y), _q(f.depth)),
        connector(dto.leg_1),
        connector(dto.leg_2),
        AngleBaseActions(
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


def serialize_angle_base(value: AngleBasePreview | AngleBaseDesign) -> AngleBaseResponseDTO:
    design = value if isinstance(value, AngleBaseDesign) else None
    p = value.preview if isinstance(value, AngleBaseDesign) else value
    return AngleBaseResponseDTO(
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


def build_angle_base_router(
    identity_resolver: TrustedIdentityResolver, sources: AngleBaseSourceRegistry = EMPTY_SOURCES
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/calculations/angle-column-two-leg-moment-base")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)

    @router.get("/defaults", response_model=AngleBaseRequestDTO)
    async def defaults(
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        unit_system: Literal["US_CUSTOMARY", "SI"] = "US_CUSTOMARY",
        unequal: bool = False,
    ) -> AngleBaseRequestDTO:
        return AngleBaseRequestDTO.model_validate(
            serialize_wall_moment_value(
                angle_column_workspace_default(unequal=unequal, si=unit_system == "SI")
            )
        )

    @router.post("/preview", response_model=AngleBaseResponseDTO)
    async def preview(
        request: AngleBaseRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> AngleBaseResponseDTO:
        try:
            return serialize_angle_base(
                preview_angle_column_moment_base(map_angle_base_request(request), sources)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CANONICAL_ANGLE_COLUMN_MOMENT_BASE_INVALID",
                    "message": str(error),
                },
            ) from error

    @router.post("/design-check", response_model=AngleBaseResponseDTO)
    async def design(
        request: AngleBaseRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> AngleBaseResponseDTO | JSONResponse:
        try:
            response = evaluate_angle_column_moment_base(map_angle_base_request(request), sources)
            if material == "SS316":
                return stainless_design_response("angle-column-two-leg-moment-base", response)
            return serialize_angle_base(response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CANONICAL_ANGLE_COLUMN_MOMENT_BASE_INVALID",
                    "message": str(error),
                },
            ) from error

    return router
