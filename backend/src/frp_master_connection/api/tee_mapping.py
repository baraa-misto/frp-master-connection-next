"""Pure Stage 3.2 Tee DTO mapping and deterministic transport serialization."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO
from frp_master_connection.api.shared_support_mapping import (
    compatibility_support_dimensions,
    map_shared_support_profile,
)
from frp_master_connection.api.tee_schemas import (
    TEE_API_TRANSPORT_SCHEMA_VERSION,
    TeeAngleProfileDimensionsDTO,
    TeeBoltLayoutDTO,
    TeeChannelProfileDimensionsDTO,
    TeeConnectorDesignResponseDTO,
    TeeConnectorPreviewResponseDTO,
    TeeConnectorRequestDTO,
    TeeFlatPlateProfileDimensionsDTO,
    TeeRectangularHollowProfileDimensionsDTO,
    TeeRoundHollowProfileDimensionsDTO,
    TeeSolidRectangularProfileDimensionsDTO,
    TeeWideFlangeIProfileDimensionsDTO,
)
from frp_master_connection.application.tee_orchestration import (
    TeeConnectorDesignResult,
    TeeConnectorOrchestrationRequest,
    TeeConnectorPreviewResult,
    TeeVectorInput,
    adapt_legacy_tee_brace_profile,
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
    RoundHollowProfileDimensions,
    SelectedSupportFlange,
    SharedSupportTargetId,
    SolidRectangularProfileDimensions,
    TeeBoltLayout,
    TeeBraceDimensions,
    TeeConnectorDimensions,
    TeeSupportDimensions,
    TeeSupportRole,
    WideFlangeIProfileDimensions,
)


def _length(value: QuantityDTO, unit: Unit) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Tee physical dimensions must be length quantities.")
    result = quantity.to(unit)
    if result.magnitude <= 0:
        raise ValueError("Tee physical dimensions must be positive.")
    return result.magnitude


def _signed_length(value: QuantityDTO, unit: Unit) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Tee placement offsets must be length quantities.")
    return quantity.to(unit).magnitude


def _layout(value: TeeBoltLayoutDTO, unit: Unit) -> TeeBoltLayout:
    vertical_offset = (
        None if value.vertical_offset is None else _signed_length(value.vertical_offset, unit)
    )
    horizontal_offset = (
        None if value.horizontal_offset is None else _signed_length(value.horizontal_offset, unit)
    )
    return TeeBoltLayout(
        row_count=value.row_count,
        bolts_per_row=value.bolts_per_row,
        pitch=_length(value.pitch, unit),
        gauge=_length(value.gauge, unit),
        unloaded_end_distance=_length(value.unloaded_end_distance, unit),
        loaded_end_distance=_length(value.loaded_end_distance, unit),
        negative_side_distance=_length(value.negative_side_distance, unit),
        positive_side_distance=_length(value.positive_side_distance, unit),
        placement_mode=value.placement_mode,
        vertical_offset=vertical_offset,
        horizontal_offset=horizontal_offset,
    )


def _vector(value: DecimalVector3DTO) -> TeeVectorInput:
    return TeeVectorInput(
        x=PhysicalQuantity.of(value.x, value.unit),
        y=PhysicalQuantity.of(value.y, value.unit),
        z=PhysicalQuantity.of(value.z, value.unit),
    )


def _connected_member_profile(value: TeeConnectorRequestDTO, unit: Unit) -> MemberProfile:
    profile = value.connected_member_profile
    if profile is None:
        if value.brace_dimensions is None:
            raise ValueError("Legacy Tee mapping requires brace_dimensions.")
        legacy_dimensions = TeeBraceDimensions(
            width=_length(value.brace_dimensions.width, unit),
            thickness=_length(value.brace_dimensions.thickness, unit),
            view_length=_length(value.brace_dimensions.view_length, unit),
        )
        return adapt_legacy_tee_brace_profile(legacy_dimensions)

    source = profile.dimensions
    dimensions: MemberProfileDimensions
    if isinstance(source, TeeAngleProfileDimensionsDTO):
        dimensions = AngleProfileDimensions(
            member_length=_length(source.member_length, unit),
            leg_y=_length(source.leg_y, unit),
            leg_z=_length(source.leg_z, unit),
            thickness=_length(source.thickness, unit),
        )
    elif isinstance(source, TeeChannelProfileDimensionsDTO):
        dimensions = ChannelProfileDimensions(
            member_length=_length(source.member_length, unit),
            depth=_length(source.depth, unit),
            flange_width=_length(source.flange_width, unit),
            web_thickness=_length(source.web_thickness, unit),
            flange_thickness=_length(source.flange_thickness, unit),
        )
    elif isinstance(source, TeeWideFlangeIProfileDimensionsDTO):
        dimensions = WideFlangeIProfileDimensions(
            member_length=_length(source.member_length, unit),
            depth=_length(source.depth, unit),
            flange_width=_length(source.flange_width, unit),
            web_thickness=_length(source.web_thickness, unit),
            flange_thickness=_length(source.flange_thickness, unit),
        )
    elif isinstance(source, TeeRectangularHollowProfileDimensionsDTO):
        dimensions = RectangularHollowProfileDimensions(
            member_length=_length(source.member_length, unit),
            depth=_length(source.depth, unit),
            width=_length(source.width, unit),
            wall_thickness=_length(source.wall_thickness, unit),
        )
    elif isinstance(source, TeeSolidRectangularProfileDimensionsDTO):
        dimensions = SolidRectangularProfileDimensions(
            member_length=_length(source.member_length, unit),
            depth=_length(source.depth, unit),
            width=_length(source.width, unit),
        )
    elif isinstance(source, TeeFlatPlateProfileDimensionsDTO):
        dimensions = FlatPlateProfileDimensions(
            member_length=_length(source.member_length, unit),
            width=_length(source.width, unit),
            thickness=_length(source.thickness, unit),
        )
    elif isinstance(source, TeeRoundHollowProfileDimensionsDTO):
        dimensions = RoundHollowProfileDimensions(
            member_length=_length(source.member_length, unit),
            outer_diameter=_length(source.outer_diameter, unit),
            wall_thickness=_length(source.wall_thickness, unit),
        )
    else:  # pragma: no cover - discriminated DTO union is closed
        raise TypeError("Unsupported connected-member profile dimensions.")
    member_id = "tee-brace"
    return MemberProfile(
        id=profile.profile_id,
        member_id=member_id,
        role=profile.role,
        family=profile.profile_family,
        dimensions=dimensions,
        material_kind=ComponentMaterialKind.PULTRUDED_FRP,
        material_orientation=FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        orientation=profile.profile_orientation,
        selected_surface=profile.selected_profile_surface,
        size_basis=profile.size_basis,
    )


def map_tee_connector_request(
    value: TeeConnectorRequestDTO,
) -> TeeConnectorOrchestrationRequest:
    """Map untrusted transport to the immutable backend-owned Tee template."""

    unit = value.source_length_unit
    connector = value.connector_dimensions
    support = value.support_dimensions
    c2_support_profile = (
        None
        if value.support_profile is None
        else map_shared_support_profile(value.support_profile, unit, member_id="tee-support")
    )
    support_dimensions = (
        TeeSupportDimensions(
            member_length=_length(support.member_length, unit),
            overall_depth=_length(support.overall_depth, unit),
            flange_width=_length(support.flange_width, unit),
            web_thickness=_length(support.web_thickness, unit),
            flange_thickness=_length(support.flange_thickness, unit),
        )
        if support is not None
        else compatibility_support_dimensions(cast(MemberProfile, c2_support_profile))
    )
    support_role = (
        value.support_role
        if value.support_role is not None
        else (
            TeeSupportRole.BEAM
            if value.support_target_id is SharedSupportTargetId.W_BEAM_FLANGE
            else TeeSupportRole.COLUMN
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
    brace = value.brace_dimensions
    legacy_brace = (
        None
        if brace is None
        else TeeBraceDimensions(
            width=_length(brace.width, unit),
            thickness=_length(brace.thickness, unit),
            view_length=_length(brace.view_length, unit),
        )
    )
    return TeeConnectorOrchestrationRequest(
        request_id=value.request_id,
        unit_system=value.unit_system,
        source_length_unit=unit,
        support_role=support_role,
        selected_support_flange=selected_flange,
        connector_dimensions=TeeConnectorDimensions(
            connector_length=_length(connector.connector_length, unit),
            flange_width=_length(connector.flange_width, unit),
            flange_thickness=_length(connector.flange_thickness, unit),
            stem_depth=_length(connector.stem_depth, unit),
            stem_thickness=_length(connector.stem_thickness, unit),
        ),
        support_dimensions=support_dimensions,
        brace_dimensions=legacy_brace,
        interface_a_layout=_layout(value.interface_a_layout, unit),
        interface_b_layout=_layout(value.interface_b_layout, unit),
        bolt_diameter=PhysicalQuantity.of(value.bolt_diameter.value, value.bolt_diameter.unit),
        hole_basis=value.hole_basis,
        global_force=_vector(value.global_force),
        global_moment=_vector(value.global_moment),
        global_reference_point=_vector(value.global_reference_point),
        connected_member_profile=_connected_member_profile(value, unit),
        orchestration_contract_version=value.orchestration_contract_version,
        brace_inclination_degrees=Decimal(value.brace_inclination_degrees),
        connected_member_end_trim_enabled=value.connected_member_end_trim_enabled,
        connected_member_end_clearance=(
            None
            if value.connected_member_end_clearance is None
            else PhysicalQuantity.of(
                value.connected_member_end_clearance.value,
                value.connected_member_end_clearance.unit,
            )
        ),
        connector_length_anchor=value.connector_length_anchor,
        connector_length_anchor_position=(
            None
            if value.connector_length_anchor_position is None
            else PhysicalQuantity.of(
                value.connector_length_anchor_position.value,
                value.connector_length_anchor_position.unit,
            )
        ),
        support_target_id=value.support_target_id,
        support_profile=c2_support_profile,
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
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value


def serialize_tee_connector_preview(
    value: TeeConnectorPreviewResult,
) -> TeeConnectorPreviewResponseDTO:
    return TeeConnectorPreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": TEE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "support_role": value.support_role,
            "selected_support_flange": value.selected_support_flange,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "warnings": value.warnings,
            "engineering_fingerprint": value.engineering_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_tee_connector_design(
    value: TeeConnectorDesignResult,
) -> TeeConnectorDesignResponseDTO:
    return TeeConnectorDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": TEE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "tee_body_resistance_status": value.tee_body_resistance_status.value,
            "ordinary_pass_allowed": False,
            "supported_interface_failure_present": value.supported_interface_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_tee_connector_request",
    "serialize_tee_connector_design",
    "serialize_tee_connector_preview",
)
