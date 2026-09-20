"""Strict stateless transport contracts for the Stage 3.2 Tee vertical slice."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import (
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.api.shared_support_schemas import (
    SharedSupportProfileDTO,
    validate_shared_support_pair,
)
from frp_master_connection.calculation import PublishedCodeUnitBasis, Unit
from frp_master_connection.domain import (
    ComponentMaterialKind,
    EngineeringUnitSystem,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
    SelectedSupportFlange,
    SharedSupportTargetId,
    TeeBoltPlacementMode,
    TeeConnectorLengthAnchor,
    TeeSupportRole,
)

TEE_API_TRANSPORT_SCHEMA_VERSION: Literal["0.1.0-draft"] = "0.1.0-draft"


class TeeConnectorDimensionsDTO(_StrictModel):
    connector_length: QuantityDTO
    flange_width: QuantityDTO
    flange_thickness: QuantityDTO
    stem_depth: QuantityDTO
    stem_thickness: QuantityDTO


class TeeSupportDimensionsDTO(_StrictModel):
    member_length: QuantityDTO
    overall_depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO


class TeeBraceDimensionsDTO(_StrictModel):
    width: QuantityDTO
    thickness: QuantityDTO
    view_length: QuantityDTO


class TeeAngleProfileDimensionsDTO(_StrictModel):
    leg_y: QuantityDTO
    leg_z: QuantityDTO
    thickness: QuantityDTO
    member_length: QuantityDTO


class TeeChannelProfileDimensionsDTO(_StrictModel):
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    member_length: QuantityDTO


class TeeWideFlangeIProfileDimensionsDTO(_StrictModel):
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    member_length: QuantityDTO


class TeeRectangularHollowProfileDimensionsDTO(_StrictModel):
    depth: QuantityDTO
    width: QuantityDTO
    wall_thickness: QuantityDTO
    member_length: QuantityDTO


class TeeSolidRectangularProfileDimensionsDTO(_StrictModel):
    depth: QuantityDTO
    width: QuantityDTO
    member_length: QuantityDTO


class TeeFlatPlateProfileDimensionsDTO(_StrictModel):
    width: QuantityDTO
    thickness: QuantityDTO
    member_length: QuantityDTO


class TeeRoundHollowProfileDimensionsDTO(_StrictModel):
    outer_diameter: QuantityDTO
    wall_thickness: QuantityDTO
    member_length: QuantityDTO


class _TeeConnectedMemberProfileBaseDTO(_StrictModel):
    profile_id: StrictStr
    role: Literal[MemberRole.BRACE]
    size_basis: Literal[MemberProfileSizeBasis.CUSTOM_DIMENSIONS]
    profile_orientation: MemberProfileOrientation
    material_kind: Literal[ComponentMaterialKind.PULTRUDED_FRP]

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("profile_id must be nonempty.")
        return value


class TeeAngleConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.ANGLE]
    dimensions: TeeAngleProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ]


class TeeChannelConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.CHANNEL]
    dimensions: TeeChannelProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_OUTER,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ]


class TeeWideFlangeIConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.WIDE_FLANGE_I]
    dimensions: TeeWideFlangeIProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ]


class TeeRectangularHollowConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION]
    dimensions: TeeRectangularHollowProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class TeeSolidRectangularConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.SOLID_RECTANGULAR_SECTION]
    dimensions: TeeSolidRectangularProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class TeeFlatPlateConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.FLAT_PLATE]
    dimensions: TeeFlatPlateProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.FACE_POS,
        MemberProfileSurfaceId.FACE_NEG,
    ]


class TeeRoundHollowConnectedMemberProfileDTO(_TeeConnectedMemberProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.ROUND_HOLLOW_SECTION]
    dimensions: TeeRoundHollowProfileDimensionsDTO
    selected_profile_surface: None = None


TeeConnectedMemberProfileDTO = Annotated[
    TeeAngleConnectedMemberProfileDTO
    | TeeChannelConnectedMemberProfileDTO
    | TeeWideFlangeIConnectedMemberProfileDTO
    | TeeRectangularHollowConnectedMemberProfileDTO
    | TeeSolidRectangularConnectedMemberProfileDTO
    | TeeFlatPlateConnectedMemberProfileDTO
    | TeeRoundHollowConnectedMemberProfileDTO,
    Field(discriminator="profile_family"),
]


class TeeBoltLayoutDTO(_StrictModel):
    row_count: StrictInt
    bolts_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    unloaded_end_distance: QuantityDTO
    loaded_end_distance: QuantityDTO
    negative_side_distance: QuantityDTO
    positive_side_distance: QuantityDTO
    placement_mode: TeeBoltPlacementMode = TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
    vertical_offset: QuantityDTO | None = None
    horizontal_offset: QuantityDTO | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> TeeBoltLayoutDTO:
        if self.row_count < 1 or self.bolts_per_row < 1:
            raise ValueError("Tee layout counts must be positive integers.")
        offsets = (self.vertical_offset, self.horizontal_offset)
        if self.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED:
            if any(value is not None for value in offsets):
                raise ValueError("Edge-distance placement forbids group offsets.")
        elif any(value is None for value in offsets):
            raise ValueError(
                "Group-offset placement requires vertical_offset and horizontal_offset."
            )
        return self


class TeeConnectorRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.2-RC1", "3.2-R2", "3.3C2-RC1"] = "3.2-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    support_role: TeeSupportRole | None = None
    selected_support_flange: SelectedSupportFlange | None = None
    connector_dimensions: TeeConnectorDimensionsDTO
    support_dimensions: TeeSupportDimensionsDTO | None = None
    support_target_id: SharedSupportTargetId | None = None
    support_profile: SharedSupportProfileDTO | None = None
    brace_dimensions: TeeBraceDimensionsDTO | None = None
    connected_member_profile: TeeConnectedMemberProfileDTO | None = None
    interface_a_layout: TeeBoltLayoutDTO
    interface_b_layout: TeeBoltLayoutDTO
    bolt_diameter: QuantityDTO
    hole_basis: PublishedCodeUnitBasis
    global_force: DecimalVector3DTO
    global_moment: DecimalVector3DTO
    global_reference_point: DecimalVector3DTO
    brace_inclination_degrees: StrictStr = "0"
    connected_member_end_trim_enabled: StrictBool = False
    connected_member_end_clearance: QuantityDTO | None = None
    connector_length_anchor: TeeConnectorLengthAnchor = TeeConnectorLengthAnchor.CENTER
    connector_length_anchor_position: QuantityDTO | None = None
    connector_material: Literal["PULTRUDED_FRP"] = "PULTRUDED_FRP"
    fastener_material: Literal["STAINLESS_STEEL_316"] = "STAINLESS_STEEL_316"
    fastener_snapshot_id: Literal["ASTM_F593_17_GROUP_2_316_316L"] = "ASTM_F593_17_GROUP_2_316_316L"

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value

    @field_validator("brace_inclination_degrees")
    @classmethod
    def validate_brace_inclination(cls, value: str) -> str:
        try:
            angle = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(
                "brace_inclination_degrees must be an exact decimal string."
            ) from error
        if not angle.is_finite() or not Decimal(-90) <= angle <= Decimal(90):
            raise ValueError("brace_inclination_degrees must be from -90 through 90.")
        return value

    @model_validator(mode="after")
    def validate_versioned_profile_contract(self) -> TeeConnectorRequestDTO:
        if self.orchestration_contract_version == "3.2-RC1":
            if self.brace_dimensions is None or self.connected_member_profile is not None:
                raise ValueError(
                    "3.2-RC1 requires brace_dimensions and forbids connected_member_profile."
                )
        elif self.orchestration_contract_version == "3.2-R2" and (
            self.brace_dimensions is not None or self.connected_member_profile is None
        ):
            raise ValueError(
                "3.2-R2 requires connected_member_profile and forbids brace_dimensions."
            )
        elif self.orchestration_contract_version == "3.3C2-RC1" and (
            self.brace_dimensions is not None or self.connected_member_profile is None
        ):
            raise ValueError(
                "3.3C2-RC1 requires connected_member_profile and forbids brace_dimensions."
            )
        is_c2 = self.orchestration_contract_version == "3.3C2-RC1"
        if is_c2:
            if self.support_target_id is None or self.support_profile is None:
                raise ValueError("C2 requires support_target_id and support_profile.")
            if any(
                item is not None
                for item in (
                    self.support_role,
                    self.selected_support_flange,
                    self.support_dimensions,
                )
            ):
                raise ValueError("C2 forbids stale legacy W-flange support fields.")
            validate_shared_support_pair(self.support_target_id, self.support_profile)
        elif (
            self.support_role is None
            or self.selected_support_flange is None
            or self.support_dimensions is None
        ):
            raise ValueError("Legacy Tee requests require the W-flange support fields.")
        elif self.support_target_id is not None or self.support_profile is not None:
            raise ValueError("Legacy Tee requests forbid C2 support fields.")
        if self.connected_member_end_trim_enabled:
            clearance = self.connected_member_end_clearance
            if clearance is None:
                raise ValueError(
                    "connected_member_end_clearance is required when end trim is enabled."
                )
            if Decimal(clearance.value) < 0:
                raise ValueError("connected_member_end_clearance must be nonnegative.")
            if clearance.unit is not self.source_length_unit:
                raise ValueError("connected_member_end_clearance must use source_length_unit.")
        elif self.connected_member_end_clearance is not None:
            raise ValueError(
                "connected_member_end_clearance is not authoritative when end trim is disabled."
            )
        if (
            self.connector_length_anchor_position is not None
            and self.connector_length_anchor_position.unit is not self.source_length_unit
        ):
            raise ValueError("connector_length_anchor_position must use source_length_unit.")
        return self


class TeeConnectorPreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.2-RC1", "3.2-R2", "3.3C2-RC1"]
    preview_schema_version: Literal["0.1.0-draft", "0.2.0-draft", "0.3.0-draft"]
    request_id: StrictStr
    support_role: TeeSupportRole
    selected_support_flange: SelectedSupportFlange
    assembly_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    warnings: tuple[StrictStr, ...]
    engineering_fingerprint: StrictStr
    result: dict[str, JsonValue]


class TeeConnectorDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.2-RC1", "3.2-R2", "3.3C2-RC1"]
    request_id: StrictStr
    assembly_status: StrictStr
    tee_body_resistance_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    supported_interface_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "TEE_API_TRANSPORT_SCHEMA_VERSION",
    "TeeAngleConnectedMemberProfileDTO",
    "TeeAngleProfileDimensionsDTO",
    "TeeBoltLayoutDTO",
    "TeeBoltPlacementMode",
    "TeeBraceDimensionsDTO",
    "TeeChannelConnectedMemberProfileDTO",
    "TeeChannelProfileDimensionsDTO",
    "TeeConnectedMemberProfileDTO",
    "TeeConnectorDesignResponseDTO",
    "TeeConnectorDimensionsDTO",
    "TeeConnectorLengthAnchor",
    "TeeConnectorPreviewResponseDTO",
    "TeeConnectorRequestDTO",
    "TeeFlatPlateConnectedMemberProfileDTO",
    "TeeFlatPlateProfileDimensionsDTO",
    "TeeRectangularHollowConnectedMemberProfileDTO",
    "TeeRectangularHollowProfileDimensionsDTO",
    "TeeRoundHollowConnectedMemberProfileDTO",
    "TeeRoundHollowProfileDimensionsDTO",
    "TeeSolidRectangularConnectedMemberProfileDTO",
    "TeeSolidRectangularProfileDimensionsDTO",
    "TeeSupportDimensionsDTO",
    "TeeWideFlangeIConnectedMemberProfileDTO",
    "TeeWideFlangeIProfileDimensionsDTO",
)
