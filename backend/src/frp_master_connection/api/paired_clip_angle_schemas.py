"""Strict stateless transport contracts for Stage 3.3B paired clip angles."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import Field, JsonValue, StrictBool, StrictStr, field_validator, model_validator

from frp_master_connection.api.clip_angle_schemas import (
    ClipAngleAngleProfileDTO,
    ClipAngleBoltLayoutDTO,
    ClipAngleDimensionsDTO,
    ClipAngleRectangularHollowProfileDTO,
    ClipAngleSolidRectangularProfileDTO,
    _ClipAngleConnectedProfileBaseDTO,
)
from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.api.shared_support_schemas import (
    SharedSupportProfileDTO,
    validate_shared_support_pair,
)
from frp_master_connection.api.tee_schemas import (
    TeeChannelProfileDimensionsDTO,
    TeeFlatPlateProfileDimensionsDTO,
    TeeSupportDimensionsDTO,
    TeeWideFlangeIProfileDimensionsDTO,
)
from frp_master_connection.calculation import PublishedCodeUnitBasis, Unit
from frp_master_connection.domain import (
    ClipAngleLengthAnchor,
    ClipAngleSupportRole,
    EngineeringUnitSystem,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    SelectedSupportFlange,
    SharedSupportTargetId,
)

PAIRED_CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION = "0.1.0-draft"


class PairedFlatPlateProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.FLAT_PLATE]
    dimensions: TeeFlatPlateProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.FACE_POS,
        MemberProfileSurfaceId.FACE_NEG,
    ]


class PairedWideFlangeProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.WIDE_FLANGE_I]
    dimensions: TeeWideFlangeIProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    ]


class PairedChannelProfileDTO(_ClipAngleConnectedProfileBaseDTO):
    profile_family: Literal[MemberProfileFamily.CHANNEL]
    dimensions: TeeChannelProfileDimensionsDTO
    selected_profile_surface: Literal[MemberProfileSurfaceId.WEB_OUTER]


PairedConnectedProfileDTO = Annotated[
    PairedFlatPlateProfileDTO
    | PairedWideFlangeProfileDTO
    | PairedChannelProfileDTO
    | ClipAngleAngleProfileDTO
    | ClipAngleRectangularHollowProfileDTO
    | ClipAngleSolidRectangularProfileDTO,
    Field(discriminator="profile_family"),
]


class PairedClipAngleConnectorRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.3B-RC1", "3.3C3-RC1"] = "3.3B-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    support_role: ClipAngleSupportRole | None = None
    selected_support_flange: SelectedSupportFlange | None = None
    connector_dimensions: ClipAngleDimensionsDTO
    support_dimensions: TeeSupportDimensionsDTO | None = None
    support_target_id: SharedSupportTargetId | None = None
    support_profile: SharedSupportProfileDTO | None = None
    connected_member_profile: PairedConnectedProfileDTO
    common_member_layout: ClipAngleBoltLayoutDTO
    mirrored_support_layout: ClipAngleBoltLayoutDTO
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
    pair_symmetry: Literal["LOCKED_IDENTICAL_MIRROR"] = "LOCKED_IDENTICAL_MIRROR"

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
        if not angle.is_finite() or not Decimal(-90) <= angle <= Decimal(90):
            raise ValueError("Inclination must be finite and from -90 through 90 degrees.")
        return value

    @model_validator(mode="after")
    def validate_trim(self) -> PairedClipAngleConnectorRequestDTO:
        is_c3 = self.orchestration_contract_version == "3.3C3-RC1"
        if is_c3:
            if self.support_target_id is None or self.support_profile is None:
                raise ValueError("C3 requires support_target_id and support_profile.")
            if any(
                item is not None
                for item in (
                    self.support_role,
                    self.selected_support_flange,
                    self.support_dimensions,
                )
            ):
                raise ValueError("C3 forbids stale legacy W-flange support fields.")
            validate_shared_support_pair(self.support_target_id, self.support_profile)
        else:
            if (
                self.support_role is None
                or self.selected_support_flange is None
                or self.support_dimensions is None
            ):
                raise ValueError("Legacy paired requests require W-flange support fields.")
            if self.support_target_id is not None or self.support_profile is not None:
                raise ValueError("Legacy paired requests forbid C3 support fields.")
            allowed = {
                MemberProfileFamily.FLAT_PLATE: {
                    MemberProfileSurfaceId.FACE_POS,
                    MemberProfileSurfaceId.FACE_NEG,
                },
                MemberProfileFamily.WIDE_FLANGE_I: {
                    MemberProfileSurfaceId.WEB_POS_FACE,
                    MemberProfileSurfaceId.WEB_NEG_FACE,
                },
                MemberProfileFamily.CHANNEL: {MemberProfileSurfaceId.WEB_OUTER},
            }
            profile = self.connected_member_profile
            if (
                profile.profile_family not in allowed
                or profile.selected_profile_surface not in allowed[profile.profile_family]
            ):
                raise ValueError(
                    "Legacy paired requests require Flat Plate, W/I Web, or Channel Web."
                )
        if self.connected_member_end_trim_enabled != (
            self.connected_member_end_clearance is not None
        ):
            raise ValueError("Trim enablement and clearance must be supplied together.")
        return self


class PairedClipAnglePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.3B-RC1", "3.3C3-RC1"]
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


class PairedClipAngleDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.3B-RC1", "3.3C3-RC1"]
    request_id: StrictStr
    assembly_status: StrictStr
    required_check_status: Literal["NOT_EVALUATED"]
    ordinary_pass_allowed: Literal[False]
    supported_interface_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "PAIRED_CLIP_ANGLE_API_TRANSPORT_SCHEMA_VERSION",
    "PairedClipAngleConnectorRequestDTO",
    "PairedClipAngleDesignResponseDTO",
    "PairedClipAnglePreviewResponseDTO",
)
