"""Strict SSMC transport; no public response/provider/material authority injection."""

from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import JsonValue, StrictBool, StrictInt, StrictStr

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.double_channel_truss_node import serialize_dctn_value
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.api.stainless_activation import material_selection
from frp_master_connection.api.wi_frp_support_moment_mapping import _hardware
from frp_master_connection.api.wi_frp_support_moment_schemas import SupportHardwareDTO
from frp_master_connection.api.wi_wall_moment_mapping import _q
from frp_master_connection.application.ssmc import SSMCPreview, preview_ssmc
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.ssmc_analytical import (
    SSMCAnalyticalRequest,
    SSMCDesignAction,
    SSMCSingleLapDeclaration,
    evaluate_ssmc_analytical,
)
from frp_master_connection.domain.ssmc import (
    SSMCFastener,
    SSMCGroup,
    SSMCPlate,
    SSMCRequest,
    StringerForm,
    StringerSection,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


class SSMCSectionDTO(_StrictModel):
    form: StringerForm
    length: QuantityDTO
    depth: QuantityDTO
    width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO


class SSMCGroupDTO(_StrictModel):
    rows: StrictInt
    first_from_cut: QuantityDTO
    pitch: QuantityDTO
    gauge: QuantityDTO
    transverse_offset: QuantityDTO
    ordinary_snug_tight: StrictBool = True
    slots: StrictBool = False
    equal_translational_stiffness: StrictBool = True


class SSMCPlateDTO(_StrictModel):
    side: Literal["NEG_Y", "POS_Y"]
    thickness: QuantityDTO
    horizontal_overlap: QuantityDTO
    inclined_overlap: QuantityDTO
    horizontal_depth: QuantityDTO
    inclined_depth: QuantityDTO
    normal_gap: QuantityDTO
    corner_radius: QuantityDTO
    chamfer: QuantityDTO


class SSMCFastenerDTO(_StrictModel):
    diameter: QuantityDTO
    hole_diameter: QuantityDTO
    hardware: SupportHardwareDTO
    threads: Literal["INCLUDED", "EXCLUDED"]
    source_reference: StrictStr = ""


class SSMCRequestDTO(_StrictModel):
    request_id: StrictStr
    unit_system: Literal["US", "SI"]
    horizontal: SSMCSectionDTO
    inclined: SSMCSectionDTO
    theta_deg: StrictStr
    plate: SSMCPlateDTO
    horizontal_group: SSMCGroupDTO
    inclined_group: SSMCGroupDTO
    fastener: SSMCFastenerDTO
    N: QuantityDTO
    V: QuantityDTO
    M: QuantityDTO
    source_reference: StrictStr = ""
    contract: Literal["SSMC-2-RC1"] = "SSMC-2-RC1"


class SSMCDesignActionDTO(_StrictModel):
    basis: Literal["FACTORED_LRFD"]
    combination_id: StrictStr
    combination_source: StrictStr
    already_factored: StrictBool
    time_effect_category: TimeEffectCategory
    time_effect_reference: StrictStr


class SSMCSingleLapDTO(_StrictModel):
    external_actions_at_faying_interface: StrictBool
    independent_normal_force: QuantityDTO
    independent_out_of_plane_moment: QuantityDTO
    imposed_separation: StrictBool
    non_contact_gap: StrictBool
    friction_or_preload_credit: StrictBool
    miter_bearing_credit: StrictBool


class SSMCAnalyticalRequestDTO(_StrictModel):
    physical: SSMCRequestDTO
    action: SSMCDesignActionDTO
    single_lap: SSMCSingleLapDTO
    contract: Literal["SSMC-3-ANALYTICAL-RC1"] = "SSMC-3-ANALYTICAL-RC1"


def map_ssmc_request(dto: SSMCRequestDTO) -> SSMCRequest:
    def section(value: SSMCSectionDTO) -> StringerSection:
        return StringerSection(
            value.form,
            *(
                _q(getattr(value, k))
                for k in ("length", "depth", "width", "web_thickness", "flange_thickness")
            ),
        )

    def group(value: SSMCGroupDTO) -> SSMCGroup:
        return SSMCGroup(
            value.rows,
            _q(value.first_from_cut),
            _q(value.pitch),
            _q(value.gauge),
            _q(value.transverse_offset),
            value.ordinary_snug_tight,
            value.slots,
            value.equal_translational_stiffness,
        )

    return SSMCRequest(
        dto.request_id,
        dto.unit_system,
        section(dto.horizontal),
        section(dto.inclined),
        Decimal(dto.theta_deg),
        SSMCPlate(
            dto.plate.side,
            *(
                _q(getattr(dto.plate, k))
                for k in (
                    "thickness",
                    "horizontal_overlap",
                    "inclined_overlap",
                    "horizontal_depth",
                    "inclined_depth",
                    "normal_gap",
                    "corner_radius",
                    "chamfer",
                )
            ),
        ),
        group(dto.horizontal_group),
        group(dto.inclined_group),
        SSMCFastener(
            _q(dto.fastener.diameter),
            _q(dto.fastener.hole_diameter),
            _hardware(dto.fastener.hardware),
            dto.fastener.threads,
            dto.fastener.source_reference,
        ),
        _q(dto.N),
        _q(dto.V),
        _q(dto.M),
        dto.source_reference,
        dto.contract,
    )


def illustrative_ssmc() -> SSMCRequestDTO:
    """Explicitly illustrative geometry only; neither material nor design qualification."""

    def q(value: str, unit: str = "in") -> dict[str, str]:
        return {"value": value, "unit": unit}

    section = {
        "form": "CHANNEL",
        **{
            k: q(v)
            for k, v in (
                ("length", "24"),
                ("depth", "10"),
                ("width", "4"),
                ("web_thickness", "0.5"),
                ("flange_thickness", "0.5"),
            )
        },
    }
    group = {
        "rows": 2,
        **{
            k: q(v)
            for k, v in (
                ("first_from_cut", "3"),
                ("pitch", "2"),
                ("gauge", "2"),
                ("transverse_offset", "0"),
            )
        },
    }
    return SSMCRequestDTO.model_validate(
        {
            "request_id": "ssmc-illustrative-unqualified",
            "unit_system": "US",
            "theta_deg": "-35",
            "horizontal": section,
            "inclined": section,
            "horizontal_group": group,
            "inclined_group": group,
            "plate": {
                "side": "NEG_Y",
                **{
                    k: q(v)
                    for k, v in (
                        ("thickness", "0.5"),
                        ("horizontal_overlap", "8"),
                        ("inclined_overlap", "8"),
                        ("horizontal_depth", "4"),
                        ("inclined_depth", "4"),
                        ("normal_gap", "0.125"),
                        ("corner_radius", "0"),
                        ("chamfer", "0"),
                    )
                },
            },
            "fastener": {
                "diameter": q("0.5"),
                "hole_diameter": q("0.563"),
                "threads": "EXCLUDED",
                "hardware": {
                    **{
                        k: q(v)
                        for k, v in (
                            ("washer_diameter", "1.25"),
                            ("washer_thickness", "0.125"),
                            ("head_across_flats", "0.75"),
                            ("head_height", "0.3125"),
                            ("nut_across_flats", "0.75"),
                            ("nut_height", "0.4375"),
                            ("end_extension", "0.125"),
                        )
                    },
                    "geometry_source": "SSMC_ILLUSTRATIVE_GEOMETRY_NOT_STRENGTH_AUTHORITY",
                },
            },
            "N": q("0", "kip"),
            "V": q("0", "kip"),
            "M": q("0", "kip-in"),
        }
    )


def convert_ssmc_units(dto: SSMCRequestDTO, si: bool) -> SSMCRequestDTO:
    targets = {
        Dimension.LENGTH: Unit.MM if si else Unit.IN,
        Dimension.FORCE: Unit.KN if si else Unit.KIP,
        Dimension.MOMENT: Unit.KN_MM if si else Unit.KIP_IN,
    }

    def convert(value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            if set(value) == {"value", "unit"}:
                q = _q(QuantityDTO.model_validate(value))
                return serialize_dctn_value(q.to(targets[q.dimension]))
            return {k: convert(v) for k, v in value.items()}
        return value

    payload = cast(dict[str, JsonValue], convert(cast(JsonValue, dto.model_dump(mode="json"))))
    payload["unit_system"] = "SI" if si else "US"
    result = SSMCRequestDTO.model_validate(payload)
    map_ssmc_request(result)
    return result


def ssmc_response(result: SSMCPreview) -> dict[str, JsonValue]:
    return {
        "contract": "SSMC-2-RC1",
        "request_id": result.input.request_id,
        "geometry_status": "VALID",
        "engineering_fingerprint": result.engineering_fingerprint,
        "whole_connection_status": result.whole_connection_status,
        "illustrative_geometry_not_qualified_design": True,
        "result": serialize_ssmc_value(result),
    }


def serialize_ssmc_value(value: object) -> JsonValue:
    """Preserve native decimal/rational quantity serialization and dated sources."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, PhysicalQuantity):
        return serialize_dctn_value(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: serialize_ssmc_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list, frozenset)):
        items = sorted(value) if isinstance(value, frozenset) else value
        return [serialize_ssmc_value(v) for v in items]
    return serialize_dctn_value(value)


def build_ssmc_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    router = APIRouter(prefix="/api/v1/calculations/stair-stringer-miter")
    identity = build_trusted_identity_dependency(identity_resolver)

    @router.get("/defaults")
    async def defaults(_identity: Annotated[TrustedIdentity, Depends(identity)]) -> SSMCRequestDTO:
        return illustrative_ssmc()

    @router.post("/convert-units")
    async def units(
        request: SSMCRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
        unit_system: Literal["US", "SI"],
    ) -> SSMCRequestDTO:
        try:
            return convert_ssmc_units(request, unit_system == "SI")
        except (ArithmeticError, ValueError) as error:
            raise HTTPException(
                status_code=422, detail={"code": "SSMC_INPUT_INVALID", "message": str(error)}
            ) from error

    @router.post("/preview")
    @router.post("/design-check")
    async def evaluate(
        request: SSMCRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
        material: Annotated[str, Depends(material_selection)],
    ) -> dict[str, JsonValue]:
        if material != "FRP":
            raise HTTPException(
                status_code=422, detail={"code": "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"}
            )
        try:
            return ssmc_response(preview_ssmc(map_ssmc_request(request)))
        except (ArithmeticError, ValueError) as error:
            raise HTTPException(
                status_code=422, detail={"code": "SSMC_INPUT_INVALID", "message": str(error)}
            ) from error

    @router.post("/analytical-design-check")
    async def analytical_design_check(
        request: SSMCAnalyticalRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
        material: Annotated[str, Depends(material_selection)],
    ) -> dict[str, JsonValue]:
        if material != "FRP":
            raise HTTPException(
                status_code=422, detail={"code": "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"}
            )
        try:
            physical = map_ssmc_request(request.physical)
            action = SSMCDesignAction(
                request.action.basis,
                request.action.combination_id,
                request.action.combination_source,
                request.action.already_factored,
                request.action.time_effect_category,
                request.action.time_effect_reference,
            )
            lap = SSMCSingleLapDeclaration(
                request.single_lap.external_actions_at_faying_interface,
                _q(request.single_lap.independent_normal_force),
                _q(request.single_lap.independent_out_of_plane_moment),
                request.single_lap.imposed_separation,
                request.single_lap.non_contact_gap,
                request.single_lap.friction_or_preload_credit,
                request.single_lap.miter_bearing_credit,
            )
            result = evaluate_ssmc_analytical(SSMCAnalyticalRequest(physical, action, lap))
            return {
                "contract": result.contract,
                "method": result.method,
                "whole_connection_status": result.whole_connection_status,
                "result": serialize_ssmc_value(result),
            }
        except (ArithmeticError, ValueError) as error:
            raise HTTPException(
                status_code=422, detail={"code": "SSMC_INPUT_INVALID", "message": str(error)}
            ) from error

    return router
