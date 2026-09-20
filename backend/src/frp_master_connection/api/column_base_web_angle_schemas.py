"""Strict stateless Stage 3.5C API transport contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, JsonValue, StrictInt, StrictStr, field_validator

from frp_master_connection.api.beam_concrete_paired_angle_schemas import ExternalAnchorGeometryDTO
from frp_master_connection.api.clip_angle_schemas import ClipAngleDimensionsDTO
from frp_master_connection.api.schemas import DecimalVector3DTO, QuantityDTO, _StrictModel
from frp_master_connection.api.tee_schemas import (
    TeeAngleProfileDimensionsDTO,
    TeeRectangularHollowProfileDimensionsDTO,
    TeeSolidRectangularProfileDimensionsDTO,
    TeeWideFlangeIProfileDimensionsDTO,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    ColumnBaseAssembly,
    ColumnBaseSide,
    ComponentMaterialKind,
    EngineeringUnitSystem,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
)

COLUMN_BASE_WEB_ANGLE_API_TRANSPORT_SCHEMA_VERSION = "0.1.0-draft"


class ColumnBaseConcreteGeometryDTO(_StrictModel):
    s_dimension: QuantityDTO
    t_dimension: QuantityDTO
    depth: QuantityDTO


class ColumnBaseWideFlangeGeometryDTO(_StrictModel):
    profile_family: Literal["WIDE_FLANGE_I"] = "WIDE_FLANGE_I"
    depth_s: QuantityDTO
    flange_width_t: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO
    display_height: QuantityDTO


class ColumnBaseWebGroupDTO(_StrictModel):
    row_count: StrictInt
    bolts_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    centroid_height_l: QuantityDTO


class ColumnBaseAnchorPatternDTO(_StrictModel):
    row_count: StrictInt
    anchors_per_row: StrictInt
    pitch: QuantityDTO
    gauge: QuantityDTO
    centroid_offset_t: QuantityDTO


class ColumnBaseWebAngleRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.5C-RC1"] = "3.5C-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometryDTO
    column: ColumnBaseWideFlangeGeometryDTO
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide = ColumnBaseSide.POSITIVE_T_C
    angle: ClipAngleDimensionsDTO
    web_group: ColumnBaseWebGroupDTO
    anchor_pattern: ColumnBaseAnchorPatternDTO
    web_bolt_diameter: QuantityDTO
    web_hole_diameter: QuantityDTO
    external_anchor: ExternalAnchorGeometryDTO
    axial_compression: QuantityDTO
    web_plane_shear: QuantityDTO
    web_normal_shear: QuantityDTO
    action_reference_s_t_l: DecimalVector3DTO

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


class ColumnBaseWebAngleSignedRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.5C-R2-RC1"] = "3.5C-R2-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometryDTO
    column: ColumnBaseWideFlangeGeometryDTO
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide = ColumnBaseSide.POSITIVE_T_C
    angle: ClipAngleDimensionsDTO
    web_group: ColumnBaseWebGroupDTO
    anchor_pattern: ColumnBaseAnchorPatternDTO
    web_bolt_diameter: QuantityDTO
    web_hole_diameter: QuantityDTO
    external_anchor: ExternalAnchorGeometryDTO
    signed_axial_force: QuantityDTO
    web_plane_shear: QuantityDTO
    web_normal_shear: QuantityDTO
    action_reference_s_t_l: DecimalVector3DTO

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


class _ColumnBaseProfileDTO(_StrictModel):
    profile_id: StrictStr
    role: Literal[MemberRole.COLUMN] = MemberRole.COLUMN
    size_basis: Literal[MemberProfileSizeBasis.CUSTOM_DIMENSIONS] = (
        MemberProfileSizeBasis.CUSTOM_DIMENSIONS
    )
    profile_orientation: MemberProfileOrientation = MemberProfileOrientation.ROTATION_0
    material_kind: Literal[ComponentMaterialKind.PULTRUDED_FRP] = (
        ComponentMaterialKind.PULTRUDED_FRP
    )

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("profile_id must be nonempty.")
        return value


class ColumnBaseWideFlangeProfileDTO(_ColumnBaseProfileDTO):
    profile_family: Literal[MemberProfileFamily.WIDE_FLANGE_I]
    dimensions: TeeWideFlangeIProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.WEB_POS_FACE,
        MemberProfileSurfaceId.WEB_NEG_FACE,
    ]


class ColumnBaseRectangularHollowProfileDTO(_ColumnBaseProfileDTO):
    profile_family: Literal[MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION]
    dimensions: TeeRectangularHollowProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class ColumnBaseSolidRectangularProfileDTO(_ColumnBaseProfileDTO):
    profile_family: Literal[MemberProfileFamily.SOLID_RECTANGULAR_SECTION]
    dimensions: TeeSolidRectangularProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.Y_POS_FACE,
        MemberProfileSurfaceId.Y_NEG_FACE,
        MemberProfileSurfaceId.Z_POS_FACE,
        MemberProfileSurfaceId.Z_NEG_FACE,
    ]


class ColumnBaseAngleProfileDTO(_ColumnBaseProfileDTO):
    profile_family: Literal[MemberProfileFamily.ANGLE]
    dimensions: TeeAngleProfileDimensionsDTO
    selected_profile_surface: Literal[
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    ]


ColumnBaseProfileDTO = Annotated[
    ColumnBaseWideFlangeProfileDTO
    | ColumnBaseRectangularHollowProfileDTO
    | ColumnBaseSolidRectangularProfileDTO
    | ColumnBaseAngleProfileDTO,
    Field(discriminator="profile_family"),
]


class ColumnBaseProfileRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["3.7A-RC1"] = "3.7A-RC1"
    request_id: StrictStr
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    concrete: ColumnBaseConcreteGeometryDTO
    column_profile: ColumnBaseProfileDTO
    assembly: Literal[
        ColumnBaseAssembly.SINGLE_BASE_ANGLE,
        ColumnBaseAssembly.DOUBLE_BASE_ANGLES,
    ]
    single_side: ColumnBaseSide = ColumnBaseSide.POSITIVE_T_C
    angle: ClipAngleDimensionsDTO
    web_group: ColumnBaseWebGroupDTO
    anchor_pattern: ColumnBaseAnchorPatternDTO
    web_bolt_diameter: QuantityDTO
    web_hole_diameter: QuantityDTO
    external_anchor: ExternalAnchorGeometryDTO
    signed_axial_force: QuantityDTO
    connection_plane_shear: QuantityDTO
    connection_normal_shear: QuantityDTO
    angle_double_topology: Literal["SAME_SELECTED_LEG_OPPOSITE_FACES"] = (
        "SAME_SELECTED_LEG_OPPOSITE_FACES"
    )

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must be nonempty.")
        return value


ColumnBaseWebAngleAnyRequestDTO = Annotated[
    ColumnBaseWebAngleRequestDTO | ColumnBaseWebAngleSignedRequestDTO | ColumnBaseProfileRequestDTO,
    Field(discriminator="orchestration_contract_version"),
]


class ColumnBaseWebAnglePreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5C-RC1", "3.5C-R2-RC1", "3.7A-RC1"]
    preview_schema_version: Literal["0.1.0-draft"]
    request_id: StrictStr
    geometry_status: Literal["VALID", "INVALID_GEOMETRY"]
    geometry_invalid_reasons: tuple[StrictStr, ...]
    assembly_status: Literal["FAIL", "NOT_EVALUATED", "INVALID_GEOMETRY"]
    ordinary_pass_allowed: Literal[False]
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    external_design_required: Literal[True]
    engineering_fingerprint: StrictStr
    application_fingerprint: StrictStr
    result: dict[str, JsonValue]


class ColumnBaseWebAngleDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.1.0-draft"]
    orchestration_contract_version: Literal["3.5C-RC1", "3.5C-R2-RC1", "3.7A-RC1"]
    request_id: StrictStr
    assembly_status: Literal["FAIL", "NOT_EVALUATED", "INVALID_GEOMETRY"]
    required_check_status: Literal["NOT_EVALUATED"]
    ordinary_pass_allowed: Literal[False]
    external_design_required: Literal[True]
    supported_local_failure_present: bool
    result_fingerprint: StrictStr
    result: dict[str, JsonValue]


__all__ = (
    "COLUMN_BASE_WEB_ANGLE_API_TRANSPORT_SCHEMA_VERSION",
    "ColumnBaseAnchorPatternDTO",
    "ColumnBaseConcreteGeometryDTO",
    "ColumnBaseProfileRequestDTO",
    "ColumnBaseWebAngleAnyRequestDTO",
    "ColumnBaseWebAngleDesignResponseDTO",
    "ColumnBaseWebAnglePreviewResponseDTO",
    "ColumnBaseWebAngleRequestDTO",
    "ColumnBaseWebAngleSignedRequestDTO",
    "ColumnBaseWebGroupDTO",
    "ColumnBaseWideFlangeGeometryDTO",
)
