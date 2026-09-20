"""Pure Stage 3.4A Multi-Member Tee DTO mapping and serialization."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.api.multi_member_tee_schemas import (
    MULTI_MEMBER_TEE_API_TRANSPORT_SCHEMA_VERSION,
    MultiMemberTeeDesignResponseDTO,
    MultiMemberTeeExpandedSlotDTO,
    MultiMemberTeeLowerBraceDTO,
    MultiMemberTeeMiddleBeamDTO,
    MultiMemberTeePreviewResponseDTO,
    MultiMemberTeeRequestDTO,
    MultiMemberTeeUpperBraceDTO,
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
from frp_master_connection.application.multi_member_tee_orchestration import (
    MultiMemberTeeDesignResult,
    MultiMemberTeeOrchestrationRequest,
    MultiMemberTeePreviewResult,
    MultiMemberTeeSlotAction,
    MultiMemberTeeSlotRequest,
    NodeVectorInput,
)
from frp_master_connection.application.tee_orchestration import (
    TEE_C2_ORCHESTRATION_CONTRACT_VERSION,
    TeeConnectorOrchestrationRequest,
    TeeVectorInput,
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
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
    PrincipalAxisFamily,
    RectangularHollowProfileDimensions,
    SelectedSupportFlange,
    SharedSupportTargetId,
    SolidRectangularProfileDimensions,
    TeeBoltLayout,
    TeeBoltPlacementMode,
    TeeConnectorDimensions,
    TeeSupportDimensions,
    TeeSupportRole,
    WideFlangeIProfileDimensions,
)
from frp_master_connection.domain.multi_member_tee import MultiMemberTeeSlot


def _length(value: QuantityDTO, unit: Unit, *, positive: bool = True) -> Decimal:
    quantity = PhysicalQuantity.of(value.value, value.unit)
    if quantity.dimension is not Dimension.LENGTH:
        raise ValueError("Multi-Member Tee geometry values must be lengths.")
    result = quantity.to(unit).magnitude
    if positive and result <= 0:
        raise ValueError("Multi-Member Tee physical dimensions must be positive.")
    return result


def _node_vector(value: DecimalVector3DTO) -> NodeVectorInput:
    return NodeVectorInput(
        PhysicalQuantity.of(value.x, value.unit),
        PhysicalQuantity.of(value.y, value.unit),
        PhysicalQuantity.of(value.z, value.unit),
    )


def _world_vector(value: NodeVectorInput) -> TeeVectorInput:
    return TeeVectorInput(
        value.h,
        PhysicalQuantity.of(-value.n.magnitude, value.n.unit),
        value.v,
    )


def _orientation(value: str) -> MemberProfileOrientation:
    quarter_turn = (int(Decimal(value) / Decimal(90))) % 4
    return (
        MemberProfileOrientation.ROTATION_0,
        MemberProfileOrientation.ROTATION_90,
        MemberProfileOrientation.ROTATION_180,
        MemberProfileOrientation.ROTATION_270,
    )[quarter_turn]


def _group_layout(
    *,
    row_count: int,
    bolts_per_row: int,
    pitch: Decimal,
    gauge: Decimal,
    vertical_offset: Decimal,
    horizontal_offset: Decimal,
    vertical_extent: Decimal,
    horizontal_extent: Decimal,
) -> TeeBoltLayout:
    row_span = Decimal(row_count - 1) * pitch
    line_span = Decimal(bolts_per_row - 1) * gauge
    return TeeBoltLayout(
        row_count,
        bolts_per_row,
        pitch,
        gauge,
        vertical_extent / Decimal(2) + vertical_offset - row_span / Decimal(2),
        vertical_extent / Decimal(2) - vertical_offset - row_span / Decimal(2),
        horizontal_extent / Decimal(2) + horizontal_offset - line_span / Decimal(2),
        horizontal_extent / Decimal(2) - horizontal_offset - line_span / Decimal(2),
        TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
        vertical_offset,
        horizontal_offset,
    )


def _support_profile(value: MultiMemberTeeRequestDTO, unit: Unit) -> MemberProfile:
    source = value.support_dimensions
    if source is None:  # guarded by the strict 3.4A transport validator
        raise ValueError("3.4A-RC1 requires support_dimensions.")
    member_id = "tee-support"
    return MemberProfile(
        "multi-member-tee-support-profile",
        member_id,
        MemberRole.COLUMN,
        MemberProfileFamily.WIDE_FLANGE_I,
        WideFlangeIProfileDimensions(
            _length(source.member_length, unit),
            _length(source.depth, unit),
            _length(source.flange_width, unit),
            _length(source.web_thickness, unit),
            _length(source.flange_thickness, unit),
        ),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )


def _profile(
    value: MultiMemberTeeUpperBraceDTO
    | MultiMemberTeeMiddleBeamDTO
    | MultiMemberTeeLowerBraceDTO
    | MultiMemberTeeExpandedSlotDTO,
    unit: Unit,
) -> MemberProfile:
    member_id = "tee-brace"
    dimensions: MemberProfileDimensions
    if isinstance(value, MultiMemberTeeExpandedSlotDTO):
        source = value.profile.dimensions
        if isinstance(source, TeeFlatPlateProfileDimensionsDTO):
            dimensions = FlatPlateProfileDimensions(
                _length(source.member_length, unit),
                _length(source.width, unit),
                _length(source.thickness, unit),
            )
        elif isinstance(source, TeeAngleProfileDimensionsDTO):
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
        else:  # pragma: no cover - the discriminated transport union is closed
            raise TypeError("Unsupported Multi-Member Tee connected profile.")
        family = value.profile.profile_family
        orientation = value.profile.profile_orientation
        selected_surface = value.profile.selected_profile_surface
        profile_id = value.profile.profile_id
    elif isinstance(value, MultiMemberTeeMiddleBeamDTO):
        family = MemberProfileFamily.WIDE_FLANGE_I
        dimensions = WideFlangeIProfileDimensions(
            _length(value.member_length, unit),
            _length(value.depth, unit),
            _length(value.flange_width, unit),
            _length(value.web_thickness, unit),
            _length(value.flange_thickness, unit),
        )
        orientation = _orientation(value.profile_roll_degrees)
        selected_surface = value.selected_profile_surface
        profile_id = f"multi-member-tee-{value.slot_id.value.lower()}-profile"
    else:
        family = MemberProfileFamily.ANGLE
        dimensions = AngleProfileDimensions(
            _length(value.member_length, unit),
            _length(value.leg_y, unit),
            _length(value.leg_z, unit),
            _length(value.thickness, unit),
        )
        orientation = _orientation(value.profile_roll_degrees)
        selected_surface = value.selected_profile_surface
        profile_id = f"multi-member-tee-{value.slot_id.value.lower()}-profile"
    return MemberProfile(
        profile_id,
        member_id,
        MemberRole.BRACE,
        family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        orientation,
        selected_surface,
        MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )


def _slot_request(
    value: MultiMemberTeeUpperBraceDTO
    | MultiMemberTeeMiddleBeamDTO
    | MultiMemberTeeLowerBraceDTO
    | MultiMemberTeeExpandedSlotDTO,
    source: MultiMemberTeeRequestDTO,
    connector: TeeConnectorDimensions,
    support: TeeSupportDimensions,
    support_profile: MemberProfile,
    support_layout: TeeBoltLayout,
) -> MultiMemberTeeSlotRequest:
    unit = source.source_length_unit
    profile = _profile(value, unit)
    anchor_h = _length(value.anchor_h, unit, positive=False)
    anchor_v = _length(value.anchor_v, unit, positive=False)
    pitch = _length(value.bolt_group.pitch, unit)
    gauge = _length(value.bolt_group.gauge, unit)
    layout = _group_layout(
        row_count=value.bolt_group.row_count,
        bolts_per_row=value.bolt_group.bolts_per_row,
        pitch=pitch,
        gauge=gauge,
        vertical_offset=anchor_v,
        horizontal_offset=anchor_h - connector.stem_depth / Decimal(2),
        vertical_extent=connector.connector_length,
        horizontal_extent=connector.stem_depth,
    )
    trim_clearance = (
        None
        if value.trim_clearance is None
        else _length(value.trim_clearance, unit, positive=False)
    )
    slot = MultiMemberTeeSlot(
        value.slot_id,
        profile,
        Decimal(value.inclination_degrees),
        Decimal(value.profile_roll_degrees),
        anchor_h,
        anchor_v,
        layout,
        value.trim_enabled,
        trim_clearance,
        isinstance(value, MultiMemberTeeExpandedSlotDTO),
    )
    action = MultiMemberTeeSlotAction(
        _node_vector(value.action.force_hvn),
        _node_vector(value.action.moment_hvn),
        _node_vector(value.action.reference_hvn),
    )
    tee_request = TeeConnectorOrchestrationRequest(
        request_id=f"{source.request_id}:{value.slot_id.value}",
        unit_system=source.unit_system,
        source_length_unit=unit,
        support_role=(
            TeeSupportRole.BEAM
            if source.support_target_id is SharedSupportTargetId.W_BEAM_FLANGE
            else TeeSupportRole.COLUMN
        ),
        selected_support_flange=(
            SelectedSupportFlange.NEGATIVE_LOCAL_Z
            if support_profile.selected_surface is MemberProfileSurfaceId.FLANGE_NEG_OUTER
            else SelectedSupportFlange.POSITIVE_LOCAL_Z
        ),
        connector_dimensions=connector,
        support_dimensions=support,
        brace_dimensions=None,
        interface_a_layout=layout,
        interface_b_layout=support_layout,
        bolt_diameter=PhysicalQuantity.of(source.bolt_diameter.value, source.bolt_diameter.unit),
        hole_basis=source.hole_basis,
        global_force=_world_vector(action.force),
        global_moment=_world_vector(action.moment),
        global_reference_point=_world_vector(action.reference_point),
        connected_member_profile=profile,
        orchestration_contract_version=TEE_C2_ORCHESTRATION_CONTRACT_VERSION,
        brace_inclination_degrees=slot.inclination_degrees,
        connected_member_end_trim_enabled=slot.trim_enabled,
        connected_member_end_clearance=(
            None if trim_clearance is None else PhysicalQuantity.of(trim_clearance, unit)
        ),
        connector_length_anchor=source.connector_length_anchor,
        connector_length_anchor_position=(
            None
            if source.connector_length_anchor_position is None
            else PhysicalQuantity.of(
                source.connector_length_anchor_position.value,
                source.connector_length_anchor_position.unit,
            )
        ),
        support_target_id=(
            SharedSupportTargetId.W_COLUMN_FLANGE
            if source.orchestration_contract_version == "3.4A-RC1"
            else cast(SharedSupportTargetId, source.support_target_id)
        ),
        support_profile=support_profile,
    )
    return MultiMemberTeeSlotRequest(slot, action, tee_request)


def map_multi_member_tee_request(
    value: MultiMemberTeeRequestDTO,
) -> MultiMemberTeeOrchestrationRequest:
    """Map untrusted transport into server-owned slot, member, and group identities."""

    unit = value.source_length_unit
    connector_source = value.connector_dimensions
    connector = TeeConnectorDimensions(
        _length(connector_source.connector_length, unit),
        _length(connector_source.flange_width, unit),
        _length(connector_source.flange_thickness, unit),
        _length(connector_source.stem_depth, unit),
        _length(connector_source.stem_thickness, unit),
    )
    if value.orchestration_contract_version == "3.4A-RC1":
        support_source = value.support_dimensions
        if support_source is None:
            raise ValueError("3.4A-RC1 requires support_dimensions.")
        support = TeeSupportDimensions(
            _length(support_source.member_length, unit),
            _length(support_source.depth, unit),
            _length(support_source.flange_width, unit),
            _length(support_source.web_thickness, unit),
            _length(support_source.flange_thickness, unit),
        )
        profile = _support_profile(value, unit)
    else:
        if value.support_profile is None:
            raise ValueError("3.4B-RC1 requires support_profile.")
        profile = map_shared_support_profile(value.support_profile, unit, member_id="tee-support")
        support = compatibility_support_dimensions(profile)
    support_layout = _group_layout(
        row_count=value.support_group.row_count,
        bolts_per_row=value.support_group.bolts_per_row,
        pitch=_length(value.support_group.pitch, unit),
        gauge=_length(value.support_group.gauge, unit),
        vertical_offset=Decimal(0),
        horizontal_offset=Decimal(0),
        vertical_extent=connector.connector_length,
        horizontal_extent=connector.flange_width,
    )
    active = tuple(
        item
        for item in (value.upper_brace, value.middle_beam, value.lower_brace)
        if item is not None
    )
    slots = tuple(
        _slot_request(item, value, connector, support, profile, support_layout) for item in active
    )
    return MultiMemberTeeOrchestrationRequest(
        value.request_id,
        value.unit_system,
        unit,
        connector,
        slots,
        _node_vector(value.support_reference_hvn),
        value.orchestration_contract_version,
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


def serialize_multi_member_tee_preview(
    value: MultiMemberTeePreviewResult,
) -> MultiMemberTeePreviewResponseDTO:
    return MultiMemberTeePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": MULTI_MEMBER_TEE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "engineering_fingerprint": value.engineering_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_multi_member_tee_design(
    value: MultiMemberTeeDesignResult,
) -> MultiMemberTeeDesignResponseDTO:
    return MultiMemberTeeDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": MULTI_MEMBER_TEE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "supported_failure_present": value.supported_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_multi_member_tee_request",
    "serialize_multi_member_tee_design",
    "serialize_multi_member_tee_preview",
)
