"""Stateless mapping of the separate FRP-support product, no concrete adapter."""

from typing import cast

from pydantic import JsonValue

from frp_master_connection.api.wi_frp_support_moment_schemas import (
    FRPMomentAngleDTO,
    FRPSupportFastenerDTO,
    SupportHardwareDTO,
    WIFrpSupportMomentRequestDTO,
    WIFrpSupportMomentResponseDTO,
)
from frp_master_connection.api.wi_wall_moment_mapping import (
    _pattern,
    _q,
    serialize_wall_moment_value,
)
from frp_master_connection.application.wi_frp_support_moment_design import FRPSupportMomentDesign
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    FRPSupportMomentPreview,
)
from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.web_splice import WebSpliceBeamGeometry
from frp_master_connection.domain.wi_frp_support_moment import (
    FRPMomentAngle,
    ReceivingSupport,
    SupportHardware,
    WIFrpSupportMomentRequest,
)
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener
from frp_master_connection.domain.wi_wall_moment import WallMomentActions


def _hardware(g: SupportHardwareDTO) -> SupportHardware:
    return SupportHardware(
        _q(g.washer_diameter),
        _q(g.washer_thickness),
        _q(g.head_across_flats),
        _q(g.head_height),
        _q(g.nut_across_flats),
        _q(g.nut_height),
        _q(g.end_extension),
        g.geometry_source,
    )


def _fastener(f: FRPSupportFastenerDTO) -> WIMomentSpliceFastener:
    return WIMomentSpliceFastener(
        _q(f.bolt_diameter), _q(f.hole_diameter), f.source_authority_id, f.thread_condition
    )


def _angle(value: FRPMomentAngleDTO) -> FRPMomentAngle:
    g = value.geometry
    return FRPMomentAngle(
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
        _fastener(value.fastener),
        _fastener(value.support_fastener),
        _hardware(value.member_hardware),
        _hardware(value.support_hardware),
        value.connector_source_reference,
        value.attachment_source_reference,
        value.material_id,
        value.provider_id,
    )


def map_wi_frp_support_moment_request(
    value: WIFrpSupportMomentRequestDTO,
) -> WIFrpSupportMomentRequest:
    b, s, a = value.beam, value.support, value.actions
    return WIFrpSupportMomentRequest(
        value.request_id,
        WebSpliceBeamGeometry(
            _q(b.depth),
            _q(b.flange_width),
            _q(b.web_thickness),
            _q(b.flange_thickness),
            _q(b.display_length_each_side),
            b.profile_family,
        ),
        _q(value.beam_physical_length),
        _q(value.gap),
        ReceivingSupport(
            s.mode,
            s.face,
            _q(s.depth),
            _q(s.width),
            _q(s.web_or_wall_thickness),
            _q(s.flange_thickness),
            _q(s.physical_length),
            _q(s.connection_height),
            _q(s.connection_transverse),
            _q(s.view_length),
            s.material_id,
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
        value.response_source_reference,
        value.local_zone_source_reference,
        value.beam_material_id,
        value.contract,
    )


def serialize_wi_frp_support_moment(
    value: FRPSupportMomentPreview | FRPSupportMomentDesign,
) -> WIFrpSupportMomentResponseDTO:
    preview = value.preview if isinstance(value, FRPSupportMomentDesign) else value
    return WIFrpSupportMomentResponseDTO(
        request_id=preview.request_id,
        geometry_status=preview.geometry.status,
        geometry_invalid_reasons=preview.geometry.reasons,
        assembly_status=value.status
        if isinstance(value, FRPSupportMomentDesign)
        else "NOT_EVALUATED",
        resistance_evaluated=value.resistance_evaluated,
        design_check_ready=preview.design_check_ready,
        engineering_fingerprint=preview.engineering_fingerprint,
        result_fingerprint=value.result_fingerprint
        if isinstance(value, FRPSupportMomentDesign)
        else preview.engineering_fingerprint,
        result=cast(dict[str, JsonValue], serialize_wall_moment_value(value)),
    )
