"""Strict stateless transport contracts for the Stage 3.3A clip angle."""

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
from frp_master_connection.api.tee_schemas import (
    TeeAngleProfileDimensionsDTO,
    TeeChannelProfileDimensionsDTO,
    TeeFlatPlateProfileDimensionsDTO,
    TeeRectangularHollowProfileDimensionsDTO,
    TeeSolidRectangularProfileDimensionsDTO,
    TeeSupportDimensionsDTO,
    TeeWideFlangeIProfileDimensionsDTO,
)
from frp_master_connection.calculation import PublishedCodeUnitBasis, Unit
from frp_master_connection.domain import (
    ClipAngleBoltPlacementMode,
    ClipAngleHand,
    ClipAngleLengthAnchor,
    ClipAngleSupportRole,
    EngineeringUnitSystem,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
    SelectedSupportFlange,
    SharedSupportTargetId,
)

CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION: Literal["0.1.0-draft"] = "0.1.0-draft"


class ClipAngleDimensionsDTO(_StrictModel):
    connected_leg_width: QuantityDTO
    support_leg_width: QuantityDTO
    thickness: QuantityDTO
    connector_length: QuantityDTO


class _ClipAngleConnectedProfileBaseDTO(_StrictModel):
    profile_id: StrictStr
    role: Literal[MemberRole.BRACE, MemberRole.BEAM]
    size_basis: Literal[MemberProfileSizeBasis.CUSTOM_DIMENSIONS]
    profile_orientation: MemberProfileOrientation

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("profile_id must be nonempty.")
        return value


class ClipAngleAngleProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.ANGLE]
    dimensions: TeeAngleProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ]


class ClipAngleChannelProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.CHANNEL]
    dimensions: TeeChannelProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_OUTER,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ]


class ClipAngleWideFlangeProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.WIDE_FLANGE_I]
    dimensions: TeeWideFlangeIProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
        MemberProfileSurfaceId.FLANGE_POS_OUTER,
        MemberProfileSurfaceId.FLANGE_NEG_OUTER,
    ]


class ClipAngleRectangularHollowProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION]
    dimensions: TeeRectangularHollowProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class ClipAngleSolidRectangularProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.SOLID_RECTANGULAR_SECTION]
    dimensions: TeeSolidRectangularProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class ClipAngleFlatPlateProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.FLAT_PLATE]
    dimensions: TeeFlatPlateProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.FACE_POS,
        MemberProfileSurfaceId.FACE_NEG,
    ]


ClipAngleConnectedProfileDTO = Annotated[
    ClipAngleAngleProfileDTO
    | ClipAngleChannelProfileDTO
    | ClipAngleWideFlangeProfileDTO
    | ClipAngleRectangularHollowProfileDTO
    | ClipAngleSolidRectangularProfileDTO
    | ClipAngleFlatPlateProfileDTO,
    Field(discriminator="profile_family"),
]


class ClipAngleBoltLayoutDTO(_StrictModel):
    row_count: StrictInt
    bolts_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    heel_edge_distance: QuantityDTO
    free_edge_distance: QuantityDTO
    negative_end_distance: QuantityDTO
    positive_end_distance: QuantityDTO
    placement_mode: ClipAngleBoltPlacementMode = ClipAngleBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
    length_offset: QuantityDTO | None = None
    width_offset: QuantityDTO | None = None

    @model_validator(mode="after")
    def validate_layout(self) -> ClipAngleBoltLayoutDTO:
        if self.row_count < 1 or self.bolts_per_row < 1:
            raise ValueError("Clip-angle layout counts must be positive integers.")
        offsets = (self.length_offset, self.width_offset)
        if self.placement_mode is ClipAngleBoltPlacementMode.EDGE_DISTANCE_CONTROLLED:
            if any(item is not None for item in offsets):
                raise ValueError("Edge-distance placement forbids group offsets.")
        elif any(item is None for item in offsets):
            raise ValueError("Group-offset placement requires length_offset and width_offset.")
        return self


class ClipAngleConnectorRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.3A-RC1", "3.3C2-RC1"] = "3.3A-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    hand: ClipAngleHand
    support_role: ClipAngleSupportRole | None = None
    selected_support_flange: SelectedSupportFlange | None = None
    connector_dimensions: ClipAngleDimensionsDTO
    support_dimensions: TeeSupportDimensionsDTO | None = None
    support_target_id: SharedSupportTargetId | None = None
    support_profile: SharedSupportProfileDTO | None = None
    connected_member_profile: ClipAngleConnectedProfileDTO
    interface_a_layout: ClipAngleBoltLayoutDTO
    interface_b_layout: ClipAngleBoltLayoutDTO
    bolt_diameter: QuantityDTO
    hole_diameter: QuantityDTO
    hole_basis: PublishedCodeUnitBasis
    global_force: DecimalVector3DTO
    global_moment: DecimalVector3DTO
    global_reference_point: DecimalVector3DTO
    connected_member_inclination_degrees: StrictStr = "0"
    connected_member_end_trim_enabled: StrictBool = False
    connected_member_end_clearance: QuantityDTO | None = None
    connector_length_anchor: ClipAngleLengthAnchor = ClipAngleLengthAnchor.CENTER
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

    @field_validator("connected_member_inclination_degrees")
    @classmethod
    def validate_inclination(cls, value: str) -> str:
        try:
            angle = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("Inclination must be an exact decimal string.") from error
        if not angle.is_finite():
            raise ValueError("Inclination must be finite.")
        if not Decimal(-90) <= angle <= Decimal(90):
            raise ValueError("Inclination must be from -90 through 90 degrees.")
        return value

    @model_validator(mode="after")
    def validate_trim(self) -> ClipAngleConnectorRequestDTO:
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
            raise ValueError("Legacy clip-angle requests require W-flange support fields.")
        elif self.support_target_id is not None or self.support_profile is not None:
            raise ValueError("Legacy clip-angle requests forbid C2 support fields.")
        if self.connected_member_end_trim_enabled:
            if self.connected_member_end_clearance is None:
                raise ValueError("Enabled trim requires connected_member_end_clearance.")
        elif self.connected_member_end_clearance is not None:
            raise ValueError("Trim clearance is forbidden while trim is disabled.")
        return self


class ClipAnglePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.3A-RC1", "3.3C2-RC1"]
    preview_schema_version: Literal["0.1.0-draft"]
    request_id: StrictStr
    geometry_status: Literal["VALID", "INVALID_GEOMETRY"]
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    warnings: tuple[StrictStr, ...]
    engineering_fingerprint: StrictStr
    result: dict[str, JsonValue]


class ClipAngleDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.3A-RC1", "3.3C2-RC1"]
    request_id: StrictStr
    assembly_status: StrictStr
    connector_body_status: Literal["NOT_EVALUATED"]
    ordinary_pass_allowed: Literal[False]
    supported_interface_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION",
    "ClipAngleBoltLayoutDTO",
    "ClipAngleConnectorRequestDTO",
    "ClipAngleDesignResponseDTO",
    "ClipAnglePreviewResponseDTO",
)
