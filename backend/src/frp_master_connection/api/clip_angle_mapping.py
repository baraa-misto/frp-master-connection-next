"""Pure Stage 3.3A clip-angle DTO mapping and deterministic serialization."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.api.clip_angle_schemas import (
    CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
    ClipAngleBoltLayoutDTO,
    ClipAngleConnectorRequestDTO,
    ClipAngleDesignResponseDTO,
    ClipAnglePreviewResponseDTO,
)
from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO
from frp_master_connection.api.shared_support_mapping import (
    compatibility_support_dimensions,
    map_shared_support_profile,
)
from frp_master_connection.api.tee_schemas import (
    TeeAngleProfileDimensionsDTO,
    TeeChannelProfileDimensionsDTO,
    TeeFlatPlateProfileDimensionsDTO,
    TeeRectangularHollowProfileDimensionsDTO,
    TeeSolidRectangularProfileDimensionsDTO,
    TeeWideFlangeIProfileDimensionsDTO,
)
from frp_master_connection.application.clip_angle_orchestration import (
    ClipAngleDesignResult,
    ClipAngleOrchestrationRequest,
    ClipAnglePreviewResult,
    ClipAngleVectorInput,
)
from frp_master_connection.calculation import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_from_finite_real,
)
from frp_master_connection.domain import (
    AngleProfileDimensions,
    ChannelProfileDimensions,
    ClipAngleBoltLayout,
    ClipAngleDimensions,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    FlatPlateProfileDimensions,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileSurfaceId,
    PrincipalAxisFamily,
    RectangularHollowProfileDimensions,
    SelectedSupportFlange,
    SharedSupportTargetId,
    SolidRectangularProfileDimensions,
    TeeSupportDimensions,
    WideFlangeIProfileDimensions,
)

_CONNECTED_MEMBER_ID = "clip-angle-connected-member"


def _length(value: QuantityDTO, unit: Unit, *, allow_zero: bool = False) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Clip-angle physical dimensions must be length quantities.")
    result = quantity.to(unit).magnitude
    if result < 0 or (result == 0 and not allow_zero):
        raise ValueError("Clip-angle physical dimensions must be positive.")
    return result


def _signed_length(value: QuantityDTO, unit: Unit) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Clip-angle placement values must be length quantities.")
    return quantity.to(unit).magnitude


def _layout(value: ClipAngleBoltLayoutDTO, unit: Unit) -> ClipAngleBoltLayout:
    return ClipAngleBoltLayout(
        value.row_count,
        value.bolts_per_row,
        _length(value.pitch, unit),
        _length(value.gauge, unit),
        _length(value.heel_edge_distance, unit),
        _length(value.free_edge_distance, unit),
        _length(value.negative_end_distance, unit),
        _length(value.positive_end_distance, unit),
        value.placement_mode,
        None if value.length_offset is None else _signed_length(value.length_offset, unit),
        None if value.width_offset is None else _signed_length(value.width_offset, unit),
    )


def _vector(value: DecimalVector3DTO) -> ClipAngleVectorInput:
    return ClipAngleVectorInput(
        PhysicalQuantity.of(value.x, value.unit),
        PhysicalQuantity.of(value.y, value.unit),
        PhysicalQuantity.of(value.z, value.unit),
    )


def _profile(value: ClipAngleConnectorRequestDTO, unit: Unit) -> MemberProfile:
    profile = value.connected_member_profile
    source = profile.dimensions
    dimensions: MemberProfileDimensions
    if isinstance(source, TeeAngleProfileDimensionsDTO):
        dimensions = AngleProfileDimensions(
            _length(source.member_length, unit),
            _length(source.leg_y, unit),
            _length(source.leg_z, unit),
            _length(source.thickness, unit),
        )
    elif isinstance(source, TeeChannelProfileDimensionsDTO):
        dimensions = ChannelProfileDimensions(
            _length(source.member_length, unit),
            _length(source.depth, unit),
            _length(source.flange_width, unit),
            _length(source.web_thickness, unit),
            _length(source.flange_thickness, unit),
        )
    elif isinstance(source, TeeWideFlangeIProfileDimensionsDTO):
        dimensions = WideFlangeIProfileDimensions(
            _length(source.member_length, unit),
            _length(source.depth, unit),
            _length(source.flange_width, unit),
            _length(source.web_thickness, unit),
            _length(source.flange_thickness, unit),
        )
    elif isinstance(source, TeeRectangularHollowProfileDimensionsDTO):
        dimensions = RectangularHollowProfileDimensions(
            _length(source.member_length, unit),
            _length(source.depth, unit),
            _length(source.width, unit),
            _length(source.wall_thickness, unit),
        )
    elif isinstance(source, TeeSolidRectangularProfileDimensionsDTO):
        dimensions = SolidRectangularProfileDimensions(
            _length(source.member_length, unit),
            _length(source.depth, unit),
            _length(source.width, unit),
        )
    elif isinstance(source, TeeFlatPlateProfileDimensionsDTO):
        dimensions = FlatPlateProfileDimensions(
            _length(source.member_length, unit),
            _length(source.width, unit),
            _length(source.thickness, unit),
        )
    else:
        raise TypeError("Unsupported clip-angle connected profile dimensions.")
    return MemberProfile(
        profile.profile_id,
        _CONNECTED_MEMBER_ID,
        profile.role,
        profile.profile_family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, _CONNECTED_MEMBER_ID),
            PrincipalAxisFamily.X,
        ),
        profile.profile_orientation,
        profile.selected_profile_surface,
        profile.size_basis,
    )


def map_clip_angle_request(
    value: ClipAngleConnectorRequestDTO,
) -> ClipAngleOrchestrationRequest:
    """Map untrusted transport into the immutable backend-owned template."""

    unit = value.source_length_unit
    connector = value.connector_dimensions
    support = value.support_dimensions
    c2_support_profile = (
        None
        if value.support_profile is None
        else map_shared_support_profile(
            value.support_profile,
            unit,
            member_id="clip-angle-support",
        )
    )
    compatibility = (
        None if c2_support_profile is None else compatibility_support_dimensions(c2_support_profile)
    )
    support_dimensions = (
        ClipAngleSupportDimensions(
            _length(support.member_length, unit),
            _length(support.overall_depth, unit),
            _length(support.flange_width, unit),
            _length(support.web_thickness, unit),
            _length(support.flange_thickness, unit),
        )
        if support is not None
        else ClipAngleSupportDimensions(
            cast(TeeSupportDimensions, compatibility).member_length,
            cast(TeeSupportDimensions, compatibility).overall_depth,
            cast(TeeSupportDimensions, compatibility).flange_width,
            cast(TeeSupportDimensions, compatibility).web_thickness,
            cast(TeeSupportDimensions, compatibility).flange_thickness,
        )
    )
    support_role = (
        value.support_role
        if value.support_role is not None
        else (
            ClipAngleSupportRole.W_BEAM_FLANGE
            if value.support_target_id is SharedSupportTargetId.W_BEAM_FLANGE
            else ClipAngleSupportRole.W_COLUMN_FLANGE
        )
    )
    selected_flange = (
        value.selected_support_flange
        if value.selected_support_flange is not None
        else (
            SelectedSupportFlange.NEGATIVE_LOCAL_Z
            if c2_support_profile is not None
            and cast(MemberProfileSurfaceId, c2_support_profile.selected_surface).value
            == "FLANGE_NEG_OUTER"
            else SelectedSupportFlange.POSITIVE_LOCAL_Z
        )
    )
    return ClipAngleOrchestrationRequest(
        value.request_id,
        value.unit_system,
        unit,
        value.hand,
        support_role,
        selected_flange,
        ClipAngleDimensions(
            _length(connector.connected_leg_width, unit),
            _length(connector.support_leg_width, unit),
            _length(connector.thickness, unit),
            _length(connector.connector_length, unit),
        ),
        support_dimensions,
        _profile(value, unit),
        _layout(value.interface_a_layout, unit),
        _layout(value.interface_b_layout, unit),
        PhysicalQuantity.of(value.bolt_diameter.value, value.bolt_diameter.unit),
        PhysicalQuantity.of(value.hole_diameter.value, value.hole_diameter.unit),
        value.hole_basis,
        _vector(value.global_force),
        _vector(value.global_moment),
        _vector(value.global_reference_point),
        Decimal(value.connected_member_inclination_degrees),
        value.connected_member_end_trim_enabled,
        (
            None
            if value.connected_member_end_clearance is None
            else PhysicalQuantity.of(
                _length(value.connected_member_end_clearance, unit, allow_zero=True), unit
            )
        ),
        value.connector_length_anchor,
        (
            None
            if value.connector_length_anchor_position is None
            else PhysicalQuantity.of(
                _signed_length(value.connector_length_anchor_position, unit), unit
            )
        ),
        value.orchestration_contract_version,
        value.support_target_id,
        c2_support_profile,
    )


def _serialize(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {
            "value": canonical_decimal_string(value.magnitude),
            "unit": value.unit.value,
            "canonical_value": value.canonical_string,
            "canonical_unit": value.canonical_unit.value,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value


def serialize_clip_angle_preview(
    value: ClipAnglePreviewResult,
) -> ClipAnglePreviewResponseDTO:
    return ClipAnglePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status.value,
            "geometry_invalid_reasons": value.geometry_invalid_reasons,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "warnings": value.warnings,
            "engineering_fingerprint": value.engineering_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_clip_angle_design(
    value: ClipAngleDesignResult,
) -> ClipAngleDesignResponseDTO:
    return ClipAngleDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "connector_body_status": value.connector_body_status.value,
            "ordinary_pass_allowed": False,
            "supported_interface_failure_present": value.supported_interface_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_clip_angle_request",
    "serialize_clip_angle_design",
    "serialize_clip_angle_preview",
)
