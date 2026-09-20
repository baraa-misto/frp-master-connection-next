"""Strict stateless Stage 3.4A Multi-Member Tee transport contracts."""

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
    TeeAngleConnectedMemberProfileDTO,
    TeeChannelConnectedMemberProfileDTO,
    TeeConnectorDimensionsDTO,
    TeeFlatPlateConnectedMemberProfileDTO,
    TeeRectangularHollowConnectedMemberProfileDTO,
    TeeSolidRectangularConnectedMemberProfileDTO,
    TeeWideFlangeIConnectedMemberProfileDTO,
)
from frp_master_connection.calculation import PublishedCodeUnitBasis, Unit
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    MemberProfileSurfaceId,
    SharedSupportTargetId,
    TeeConnectorLengthAnchor,
)
from frp_master_connection.domain.multi_member_tee import MultiMemberTeeSlotId

MULTI_MEMBER_TEE_API_TRANSPORT_SCHEMA_VERSION: Literal["0.1.0-draft"] = "0.1.0-draft"

MultiMemberTeeConnectedProfileDTO = Annotated[
    TeeFlatPlateConnectedMemberProfileDTO
    | TeeAngleConnectedMemberProfileDTO
    | TeeChannelConnectedMemberProfileDTO
    | TeeWideFlangeIConnectedMemberProfileDTO
    | TeeRectangularHollowConnectedMemberProfileDTO
    | TeeSolidRectangularConnectedMemberProfileDTO,
    Field(discriminator="profile_family"),
]


def _finite_decimal(value: str, field_name: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{field_name} must be an exact decimal string.") from error
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite.")
    return result


class MultiMemberTeeSupportDimensionsDTO(_StrictModel):
    member_length: QuantityDTO
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO


class MultiMemberTeeBoltGroupDTO(_StrictModel):
    row_count: StrictInt
    bolts_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO

    @model_validator(mode="after")
    def positive_counts(self) -> MultiMemberTeeBoltGroupDTO:
        if self.row_count < 1 or self.bolts_per_row < 1:
            raise ValueError("Bolt-group counts must be positive integers.")
        return self


class MultiMemberTeeActionDTO(_StrictModel):
    force_hvn: DecimalVector3DTO
    moment_hvn: DecimalVector3DTO
    reference_hvn: DecimalVector3DTO


class _MultiMemberTeeSlotBaseDTO(_StrictModel):
    anchor_h: QuantityDTO
    anchor_v: QuantityDTO
    bolt_group: MultiMemberTeeBoltGroupDTO
    action: MultiMemberTeeActionDTO
    profile_roll_degrees: StrictStr = "0"
    trim_enabled: StrictBool = False
    trim_clearance: QuantityDTO | None = None

    @field_validator("profile_roll_degrees")
    @classmethod
    def exact_quarter_turn(cls, value: str) -> str:
        angle = _finite_decimal(value, "profile_roll_degrees")
        if angle % Decimal(90) != 0:
            raise ValueError("profile_roll_degrees must be an exact quarter turn.")
        return value

    @model_validator(mode="after")
    def trim_contract(self) -> _MultiMemberTeeSlotBaseDTO:
        if self.trim_enabled:
            if self.trim_clearance is None or Decimal(self.trim_clearance.value) < 0:
                raise ValueError("Enabled trim requires nonnegative trim_clearance.")
        elif self.trim_clearance is not None:
            raise ValueError("Disabled trim forbids trim_clearance.")
        return self


class MultiMemberTeeUpperBraceDTO(_MultiMemberTeeSlotBaseDTO):
    slot_id: Literal[MultiMemberTeeSlotId.UPPER_BRACE] = MultiMemberTeeSlotId.UPPER_BRACE
    leg_y: QuantityDTO
    leg_z: QuantityDTO
    thickness: QuantityDTO
    member_length: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ] = MemberProfileSurfaceId.LEG_Y_OUTER
    inclination_degrees: StrictStr = "30"

    @field_validator("inclination_degrees")
    @classmethod
    def upper_angle_domain(cls, value: str) -> str:
        angle = _finite_decimal(value, "inclination_degrees")
        if not Decimal(0) <= angle <= Decimal(90):
            raise ValueError("UPPER_BRACE inclination must be from 0 through 90 degrees.")
        return value


class MultiMemberTeeMiddleBeamDTO(_MultiMemberTeeSlotBaseDTO):
    slot_id: Literal[MultiMemberTeeSlotId.MIDDLE_BEAM] = MultiMemberTeeSlotId.MIDDLE_BEAM
    depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    member_length: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    ] = MemberProfileSurfaceId.WEB_POS_FACE
    inclination_degrees: Literal["0"] = "0"


class MultiMemberTeeLowerBraceDTO(_MultiMemberTeeSlotBaseDTO):
    slot_id: Literal[MultiMemberTeeSlotId.LOWER_BRACE] = MultiMemberTeeSlotId.LOWER_BRACE
    leg_y: QuantityDTO
    leg_z: QuantityDTO
    thickness: QuantityDTO
    member_length: QuantityDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ] = MemberProfileSurfaceId.LEG_Y_OUTER
    inclination_degrees: StrictStr = "-30"

    @field_validator("inclination_degrees")
    @classmethod
    def lower_angle_domain(cls, value: str) -> str:
        angle = _finite_decimal(value, "inclination_degrees")
        if not Decimal(-90) <= angle <= Decimal(0):
            raise ValueError("LOWER_BRACE inclination must be from -90 through 0 degrees.")
        return value


class MultiMemberTeeExpandedSlotDTO(_MultiMemberTeeSlotBaseDTO):
    """One 3.4B semantic slot wrapped around the shared six-family profile union."""

    slot_id: MultiMemberTeeSlotId
    profile: MultiMemberTeeConnectedProfileDTO
    inclination_degrees: StrictStr

    @field_validator("inclination_degrees")
    @classmethod
    def inclination_domain(cls, value: str) -> str:
        _finite_decimal(value, "inclination_degrees")
        return value

    @model_validator(mode="after")
    def semantic_inclination_domain(self) -> MultiMemberTeeExpandedSlotDTO:
        angle = Decimal(self.inclination_degrees)
        if self.slot_id is MultiMemberTeeSlotId.MIDDLE_BEAM and angle != 0:
            raise ValueError("MIDDLE_BEAM inclination must be exactly zero.")
        if self.slot_id is MultiMemberTeeSlotId.UPPER_BRACE and not (
            Decimal(0) <= angle <= Decimal(90)
        ):
            raise ValueError("UPPER_BRACE inclination must be from 0 through 90 degrees.")
        if self.slot_id is MultiMemberTeeSlotId.LOWER_BRACE and not (
            Decimal(-90) <= angle <= Decimal(0)
        ):
            raise ValueError("LOWER_BRACE inclination must be from -90 through 0 degrees.")
        expected_roll = {
            "ROTATION_0": Decimal(0),
            "ROTATION_90": Decimal(90),
            "ROTATION_180": Decimal(180),
            "ROTATION_270": Decimal(270),
        }[self.profile.profile_orientation.value]
        if Decimal(self.profile_roll_degrees) % Decimal(360) != expected_roll:
            raise ValueError("profile_roll_degrees must match profile.profile_orientation.")
        return self


class MultiMemberTeeRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.4A-RC1", "3.4B-RC1"] = "3.4A-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    connector_dimensions: TeeConnectorDimensionsDTO
    connector_length_anchor: TeeConnectorLengthAnchor = TeeConnectorLengthAnchor.CENTER
    connector_length_anchor_position: QuantityDTO | None = None
    support_dimensions: MultiMemberTeeSupportDimensionsDTO | None = None
    support_target_id: SharedSupportTargetId | None = None
    support_profile: SharedSupportProfileDTO | None = None
    support_group: MultiMemberTeeBoltGroupDTO
    upper_brace: MultiMemberTeeUpperBraceDTO | MultiMemberTeeExpandedSlotDTO | None = None
    middle_beam: MultiMemberTeeMiddleBeamDTO | MultiMemberTeeExpandedSlotDTO | None = None
    lower_brace: MultiMemberTeeLowerBraceDTO | MultiMemberTeeExpandedSlotDTO | None = None
    support_reference_hvn: DecimalVector3DTO
    bolt_diameter: QuantityDTO
    hole_basis: PublishedCodeUnitBasis
    connector_material: Literal["PULTRUDED_FRP"] = "PULTRUDED_FRP"
    fastener_material: Literal["STAINLESS_STEEL_316"] = "STAINLESS_STEEL_316"
    fastener_snapshot_id: Literal["ASTM_F593_17_GROUP_2_316_316L"] = "ASTM_F593_17_GROUP_2_316_316L"

    @field_validator("request_id")
    @classmethod
    def nonempty_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty text.")
        return value

    @model_validator(mode="after")
    def active_slots_and_units(self) -> MultiMemberTeeRequestDTO:
        active = tuple(
            item
            for item in (self.upper_brace, self.middle_beam, self.lower_brace)
            if item is not None
        )
        if not active:
            raise ValueError("At least one Multi-Member Tee slot must be active.")
        expected = Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        if self.source_length_unit is not expected:
            raise ValueError("source_length_unit must match unit_system.")
        if (
            self.connector_length_anchor_position is not None
            and self.connector_length_anchor_position.unit is not self.source_length_unit
        ):
            raise ValueError("connector_length_anchor_position must use source_length_unit.")
        if self.orchestration_contract_version == "3.4A-RC1":
            if self.support_dimensions is None:
                raise ValueError("3.4A-RC1 requires support_dimensions.")
            if self.support_target_id is not None or self.support_profile is not None:
                raise ValueError("3.4A-RC1 forbids expanded shared-support fields.")
            expected_types = (
                (self.upper_brace, MultiMemberTeeUpperBraceDTO, MultiMemberTeeSlotId.UPPER_BRACE),
                (self.middle_beam, MultiMemberTeeMiddleBeamDTO, MultiMemberTeeSlotId.MIDDLE_BEAM),
                (self.lower_brace, MultiMemberTeeLowerBraceDTO, MultiMemberTeeSlotId.LOWER_BRACE),
            )
            if any(
                item is not None and not isinstance(item, expected)
                for item, expected, _slot in expected_types
            ):
                raise ValueError("3.4A-RC1 requires its historical role-specific slot contracts.")
        else:
            if self.support_dimensions is not None:
                raise ValueError("3.4B-RC1 forbids legacy support_dimensions.")
            if self.support_target_id is None or self.support_profile is None:
                raise ValueError("3.4B-RC1 requires support_target_id and support_profile.")
            validate_shared_support_pair(self.support_target_id, self.support_profile)
            expected_slots = (
                (self.upper_brace, MultiMemberTeeSlotId.UPPER_BRACE),
                (self.middle_beam, MultiMemberTeeSlotId.MIDDLE_BEAM),
                (self.lower_brace, MultiMemberTeeSlotId.LOWER_BRACE),
            )
            if any(
                item is not None
                and (
                    not isinstance(item, MultiMemberTeeExpandedSlotDTO)
                    or item.slot_id is not expected
                )
                for item, expected in expected_slots
            ):
                raise ValueError(
                    "3.4B-RC1 slots must use matching shared-profile semantic wrappers."
                )
        return self


class MultiMemberTeePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.4A-RC1", "3.4B-RC1"]
    preview_schema_version: Literal["0.1.0-draft"]
    request_id: StrictStr
    assembly_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    engineering_fingerprint: StrictStr
    result: dict[str, JsonValue]


class MultiMemberTeeDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.4A-RC1", "3.4B-RC1"]
    request_id: StrictStr
    assembly_status: StrictStr
    ordinary_pass_allowed: Literal[False]
    supported_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "MULTI_MEMBER_TEE_API_TRANSPORT_SCHEMA_VERSION",
    "MultiMemberTeeActionDTO",
    "MultiMemberTeeBoltGroupDTO",
    "MultiMemberTeeConnectedProfileDTO",
    "MultiMemberTeeDesignResponseDTO",
    "MultiMemberTeeExpandedSlotDTO",
    "MultiMemberTeeLowerBraceDTO",
    "MultiMemberTeeMiddleBeamDTO",
    "MultiMemberTeePreviewResponseDTO",
    "MultiMemberTeeRequestDTO",
    "MultiMemberTeeSupportDimensionsDTO",
    "MultiMemberTeeUpperBraceDTO",
)
