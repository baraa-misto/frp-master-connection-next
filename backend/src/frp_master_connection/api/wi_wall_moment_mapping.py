"""Pure Stage 4.2 DTO mapping and exact, deterministic native trace transport."""

from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Literal, cast

from pydantic import JsonValue

from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.api.wi_wall_moment_schemas import (
    WallMomentAngleDTO,
    WallMomentPatternDTO,
    WIWallMomentRequestDTO,
    WIWallMomentResponseDTO,
)
from frp_master_connection.application.wi_wall_moment_design import WIWallMomentDesign
from frp_master_connection.application.wi_wall_moment_orchestration import WIWallMomentPreview
from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
)
from frp_master_connection.domain.beam_concrete_paired_angle import (
    ConcreteWallGeometry,
    ExternalAnchorGeometry,
)
from frp_master_connection.domain.web_splice import WebSpliceBeamGeometry
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener
from frp_master_connection.domain.wi_wall_moment import (
    WallMomentActions,
    WallMomentAngle,
    WallMomentPattern,
    WIWallMomentRequest,
)


def _q(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


def _pattern(value: WallMomentPatternDTO) -> WallMomentPattern:
    return WallMomentPattern(
        value.across, value.along, _q(value.gauge), _q(value.pitch), _q(value.center)
    )


def _angle(value: WallMomentAngleDTO) -> WallMomentAngle:
    g, f, a = value.geometry, value.fastener, value.anchors
    return WallMomentAngle(
        AngleConnectorGeometry(
            _q(g.length),
            _q(g.member_leg),
            _q(g.support_leg),
            _q(g.thickness),
            _q(g.inside_radius),
            (_q(g.heel_end_reliefs[0]), _q(g.heel_end_reliefs[1])),
        ),
        _pattern(value.member_pattern),
        _pattern(value.support_pattern),
        WIMomentSpliceFastener(
            _q(f.bolt_diameter),
            _q(f.hole_diameter),
            f.source_authority_id,
            f.thread_condition,
            None if f.nominal_shear_stress is None else _q(f.nominal_shear_stress),
        ),
        ExternalAnchorGeometry(
            _q(a.nominal_diameter),
            _q(a.hole_diameter),
            _q(a.specified_embedment),
            _q(a.washer_outside_diameter),
            _q(a.washer_thickness),
        ),
        value.connector_source_reference,
        value.attachment_source_reference,
        value.material_id,
        value.provider_id,
    )


def map_wi_wall_moment_request(value: WIWallMomentRequestDTO) -> WIWallMomentRequest:
    b, w, a = value.beam, value.wall, value.actions
    lu = Unit(value.source_length_unit)
    return WIWallMomentRequest(
        value.request_id,
        value.unit_system,
        lu,
        WebSpliceBeamGeometry(
            _q(b.depth),
            _q(b.flange_width),
            _q(b.web_thickness),
            _q(b.flange_thickness),
            _q(b.display_length_each_side),
            b.profile_family,
        ),
        _q(value.gap),
        ConcreteWallGeometry(
            *(
                _q(x).to(lu).magnitude
                for x in (
                    w.width,
                    w.height,
                    w.thickness,
                    w.connection_origin_h,
                    w.connection_origin_v,
                )
            )
        ),
        _angle(value.top),
        _angle(value.bottom),
        _angle(value.positive_web),
        _angle(value.negative_web),
        WallMomentActions(
            _q(a.axial),
            _q(a.major_shear),
            _q(a.structural_major_moment),
            PhysicalQuantity.of(0, Unit.KIP),
            PhysicalQuantity.of(0, Unit.KIP_IN),
            PhysicalQuantity.of(0, Unit.KIP_IN),
        ),
        value.contract,
    )


def serialize_wall_moment_value(value: object) -> JsonValue:
    if isinstance(value, PhysicalQuantity):
        return {"value": canonical_decimal_string(value.magnitude), "unit": value.unit.value}
    if isinstance(value, Fraction):
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: serialize_wall_moment_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [serialize_wall_moment_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): serialize_wall_moment_value(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise TypeError(f"Unsupported Stage 4.2 transport value {type(value).__name__}")


def serialize_wi_wall_moment(
    value: WIWallMomentPreview | WIWallMomentDesign,
) -> WIWallMomentResponseDTO:
    preview = value.preview if isinstance(value, WIWallMomentDesign) else value
    return WIWallMomentResponseDTO(
        request_id=preview.request_id,
        geometry_status=preview.geometry.status,
        geometry_invalid_reasons=preview.geometry.reasons,
        assembly_status=value.status if isinstance(value, WIWallMomentDesign) else "NOT_EVALUATED",
        whole_connection_status=cast(
            Literal["EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"], preview.whole_connection_status
        ),
        resistance_evaluated=value.resistance_evaluated,
        design_check_ready=preview.design_check_ready,
        engineering_fingerprint=preview.engineering_fingerprint,
        result_fingerprint=value.result_fingerprint
        if isinstance(value, WIWallMomentDesign)
        else preview.engineering_fingerprint,
        result=cast(dict[str, JsonValue], serialize_wall_moment_value(value)),
    )
