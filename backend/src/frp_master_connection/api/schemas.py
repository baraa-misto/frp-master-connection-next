"""Strict transport contracts for process metadata and single-bolt evaluation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

from frp_master_connection.application import (
    AngleConnectedLeg,
    ColumnFlangeConnectionSide,
    OutstandingLegSide,
)
from frp_master_connection.calculation import (
    DemandDistributionStatus,
    DemandSourceKind,
    FRPPropertyKind,
    LapConfiguration,
    LayerLoadingSense,
    PropertyBehavior,
    PublishedCodeUnitBasis,
    PultrudedElementForm,
    QualificationStatus,
    SourceClassification,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
)
from frp_master_connection.domain import (
    ActionConvention,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    CoordinateFrameKind,
    EngineeringUnitSystem,
    LoadInputBasis,
    MemberEnd,
    MemberRole,
    PrincipalAxisFamily,
    ReferencePointKind,
    TransferIntent,
)
from frp_master_connection.geometry import InterfaceTargetSide, SurfacePatchRole

API_TRANSPORT_SCHEMA_VERSION: Literal["0.5.0-draft"] = "0.5.0-draft"

Identifier = Annotated[
    StrictStr,
    Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HealthResponse(_StrictModel):
    """Public process-health response with no engineering meaning."""

    status: Literal["healthy"] = Field(
        description="Service/process health only; never an engineering PASS result."
    )
    product_id: str
    application_version: str


class MetadataResponse(_StrictModel):
    """Controlled product metadata that exposes no trusted identity."""

    product_id: str
    application_version: str
    project_schema_version: str
    calculation_engine_version: str
    engineering_rule_set_version: str
    code_basis: str
    errata_status: str
    engineering_calculations_available: Literal[True]
    report_generation_available: Literal[False]


class QuantityDTO(_StrictModel):
    """One exact decimal-string engineering quantity with a controlled unit."""

    value: StrictStr
    unit: Unit

    @field_validator("value")
    @classmethod
    def validate_decimal_string(cls, value: str) -> str:
        from decimal import Decimal, InvalidOperation

        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("value must be a valid decimal string") from error
        if not parsed.is_finite():
            raise ValueError("value must be finite")
        return value


class DecimalVector3DTO(_StrictModel):
    """Three exact decimal-string components with one explicit unit."""

    x: StrictStr
    y: StrictStr
    z: StrictStr
    unit: Unit

    @field_validator("x", "y", "z")
    @classmethod
    def validate_component(cls, value: str) -> str:
        return QuantityDTO.validate_decimal_string(value)


class DirectionVector3DTO(_StrictModel):
    """A finite dimensionless direction passed through the sole geometry bridge."""

    x: StrictStr
    y: StrictStr
    z: StrictStr

    @field_validator("x", "y", "z")
    @classmethod
    def validate_component(cls, value: str) -> str:
        return QuantityDTO.validate_decimal_string(value)


class FrameDTO(_StrictModel):
    """Declarative frame built server-side from an origin, +x, and +z reference."""

    origin: DecimalVector3DTO
    x_direction: DirectionVector3DTO
    local_z_reference: DirectionVector3DTO


class PlateSectionDTO(_StrictModel):
    kind: Literal["PLATE"]
    width: QuantityDTO
    thickness: QuantityDTO


class AngleSectionDTO(_StrictModel):
    kind: Literal["ANGLE"]
    leg_y: QuantityDTO
    leg_z: QuantityDTO
    thickness: QuantityDTO


class ISectionDTO(_StrictModel):
    kind: Literal["WIDE_FLANGE", "I_SECTION"]
    overall_depth: QuantityDTO
    flange_width: QuantityDTO
    web_thickness: QuantityDTO
    flange_thickness: QuantityDTO


SectionDTO = Annotated[PlateSectionDTO | AngleSectionDTO | ISectionDTO, Field(discriminator="kind")]


class MaterialOrientationDTO(_StrictModel):
    lengthwise_axis: PrincipalAxisFamily
    crosswise_axis: PrincipalAxisFamily
    through_thickness_axis: PrincipalAxisFamily


class MemberDTO(_StrictModel):
    id: Identifier
    label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    role: MemberRole
    connected_end: MemberEnd
    material_kind: ComponentMaterialKind
    material_orientation: MaterialOrientationDTO | None
    section: SectionDTO


class LoadCombinationDTO(_StrictModel):
    id: Identifier
    label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    input_basis: LoadInputBasis


class ReferencePointDTO(_StrictModel):
    kind: ReferencePointKind
    owner_id: Identifier | None = None
    position: DecimalVector3DTO | None = None


class MemberEndActionDTO(_StrictModel):
    id: Identifier
    member_id: Identifier
    member_end: MemberEnd
    load_combination_id: Identifier
    coordinate_frame_kind: CoordinateFrameKind
    coordinate_frame_owner_id: Identifier | None
    reference_point: ReferencePointDTO
    force: DecimalVector3DTO
    moment: DecimalVector3DTO
    convention: ActionConvention


class JointAssemblyDTO(_StrictModel):
    id: Identifier
    label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    design_category: ConnectionDesignCategory
    unit_system: EngineeringUnitSystem
    members: tuple[MemberDTO, ...]
    load_combinations: tuple[LoadCombinationDTO, ...]
    member_end_actions: tuple[MemberEndActionDTO, ...]


class MemberPlacementDTO(_StrictModel):
    member_id: Identifier
    start: DecimalVector3DTO
    end: DecimalVector3DTO
    local_z_reference: DirectionVector3DTO
    section_offset_y: QuantityDTO
    section_offset_z: QuantityDTO


class InterfaceSideDTO(_StrictModel):
    participant_id: Identifier
    physical_element_id: Identifier
    patch_id: Identifier
    face_role: SurfacePatchRole
    zone_id: Identifier
    zone_label: Annotated[StrictStr, Field(min_length=1, max_length=256)]


class ConnectionInterfaceDTO(_StrictModel):
    id: Identifier
    label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    participant_a_id: Identifier
    participant_b_id: Identifier
    transfer_intent: TransferIntent
    first_side: InterfaceSideDTO
    second_side: InterfaceSideDTO
    origin_local_y: QuantityDTO
    origin_local_z: QuantityDTO
    in_plane_reference: DirectionVector3DTO
    distance_tolerance: QuantityDTO
    angular_tolerance: StrictStr

    @field_validator("angular_tolerance")
    @classmethod
    def validate_angular_tolerance(cls, value: str) -> str:
        return QuantityDTO.validate_decimal_string(value)


class BoltLocationDTO(_StrictModel):
    id: Identifier
    local_position: DecimalVector3DTO


class PenetratedLayerDTO(_StrictModel):
    id: Identifier
    participant_id: Identifier
    physical_element_id: Identifier
    entry_patch_id: Identifier
    exit_patch_id: Identifier
    entry_face_role: SurfacePatchRole
    exit_face_role: SurfacePatchRole
    interface_side: InterfaceTargetSide
    zone_id: Identifier
    hole_diameter: QuantityDTO


class BoltPathDTO(_StrictModel):
    bolt_location_id: Identifier
    layers: tuple[PenetratedLayerDTO, ...]


class BoltGroupGeometryDTO(_StrictModel):
    id: Identifier
    label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    primary_interface_id: Identifier
    origin_y: QuantityDTO
    origin_z: QuantityDTO
    in_plane_reference: DirectionVector3DTO
    locations: tuple[BoltLocationDTO, ...]
    paths: tuple[BoltPathDTO, ...]


class GeometryDTO(_StrictModel):
    joint_frame: FrameDTO
    member_placements: tuple[MemberPlacementDTO, ...]
    interface: ConnectionInterfaceDTO
    bolt_group: BoltGroupGeometryDTO


class BraceToColumnFlangeTemplateGeometryDTO(_StrictModel):
    """Narrow backend-owned geometry template for the verified J1 connection slice."""

    kind: Literal["BRACE_TO_COLUMN_FLANGE"]
    brace_to_column_directed_angle_deg: StrictStr
    bolt_to_brace_end_distance: QuantityDTO
    hole_diameter: QuantityDTO
    column_flange_connection_side: ColumnFlangeConnectionSide
    angle_connected_leg: AngleConnectedLeg
    outstanding_leg_side: OutstandingLegSide

    @field_validator("brace_to_column_directed_angle_deg")
    @classmethod
    def validate_angle(cls, value: str) -> str:
        from decimal import Decimal

        parsed = Decimal(QuantityDTO.validate_decimal_string(value))
        if parsed <= 0 or parsed >= 180:
            raise ValueError("directed brace-to-column angle must be between 0 and 180 degrees")
        return value


class ConnectionViewExtentsDTO(_StrictModel):
    """Preview-only finite local context; never engineering target geometry."""

    brace_view_length: QuantityDTO
    column_view_extent_below: QuantityDTO
    column_view_extent_above: QuantityDTO


class FRPPropertyEntryDTO(_StrictModel):
    kind: FRPPropertyKind
    value: QuantityDTO
    behavior: PropertyBehavior
    source_classification: SourceClassification
    qualification_status: QualificationStatus
    source_document: StrictStr
    source_revision: StrictStr
    applicability_metadata: tuple[StrictStr, ...] = ()
    engineer_notes: tuple[StrictStr, ...] = ()
    use_in_chapter_8_equations: StrictBool = True


class MaterialSnapshotDTO(_StrictModel):
    id: Identifier
    display_name: StrictStr
    locked: StrictBool
    basis: SourceClassification
    qualification_statuses: tuple[QualificationStatus, ...]
    properties: tuple[FRPPropertyEntryDTO, ...]
    explicitly_missing: tuple[FRPPropertyKind, ...] = ()


class MaterialAssignmentDTO(_StrictModel):
    participant_id: Identifier
    physical_element_id: Identifier
    material_region_id: Identifier
    material_snapshot_id: Identifier
    bearing_thread_status: ThreadStatus
    element_form: PultrudedElementForm
    potential_perpendicular_element_exemption: StrictBool = False


class ThreadStatusAssignmentDTO(_StrictModel):
    location_id: Identifier
    status: ThreadStatus


class WasherGeometryDTO(_StrictModel):
    outside_diameter: QuantityDTO
    thickness: QuantityDTO
    under_head: StrictBool
    under_nut: StrictBool


class FastenerSnapshotDTO(_StrictModel):
    id: Identifier
    display_name: StrictStr
    locked: StrictBool
    bolt_specification: StrictStr
    alloy_group: StrictStr
    alloys: tuple[StrictStr, ...]
    condition: StrictStr
    nut_specification: StrictStr
    washer_material_basis: StrictStr
    installation_condition: StrictStr
    diameter_min: QuantityDTO
    diameter_max: QuantityDTO
    fnt: QuantityDTO | None
    fnt_source_classification: SourceClassification
    fnt_qualification_status: QualificationStatus
    shear_plane_thread_statuses: tuple[ThreadStatusAssignmentDTO, ...]
    bearing_layer_thread_statuses: tuple[ThreadStatusAssignmentDTO, ...]
    number_of_shear_planes: Annotated[int, Field(strict=True, ge=0)]
    washer_geometry: WasherGeometryDTO | None
    source_notes: tuple[StrictStr, ...] = ()


class PreviewFastenerGeometryDTO(_StrictModel):
    """Non-resistance fastener identity and exact-known display geometry."""

    id: Identifier
    washer_geometry: WasherGeometryDTO | None


class EndUseFactorsDTO(_StrictModel):
    cm: StrictStr
    ct: StrictStr
    cch: StrictStr
    source_reference: StrictStr
    approval_metadata: tuple[StrictStr, ...]

    @field_validator("cm", "ct", "cch")
    @classmethod
    def validate_factor(cls, value: str) -> str:
        return QuantityDTO.validate_decimal_string(value)


class ExplicitResolvedDemandDTO(_StrictModel):
    interface_id: Identifier
    bolt_group_id: Identifier
    bolt_location_id: Identifier
    id: Identifier
    load_combination_id: Identifier
    source_member_id: Identifier
    source_action_id: Identifier
    source_kind: Literal[DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND]
    factored_action_confirmed: StrictBool
    coordinate_frame_reference: StrictStr
    resolved_frame: FrameDTO
    source_reference_point_id: Identifier
    resolved_global_reference_point: DecimalVector3DTO
    in_plane_force_vector: DecimalVector3DTO
    bolt_axis_tensile_demand: QuantityDTO
    externally_supplied_prying_demand: QuantityDTO
    loading_sense: LayerLoadingSense
    provenance: tuple[StrictStr, ...]
    distribution_status: Literal[DemandDistributionStatus.EXPLICITLY_RESOLVED]


class SingleBoltEvaluationRequestDTO(_StrictModel):
    """Complete stateless declarative snapshot for one selected logical bolt."""

    calculation_id: Identifier
    joint_assembly: JointAssemblyDTO
    geometry: GeometryDTO | None = None
    geometry_template: BraceToColumnFlangeTemplateGeometryDTO | None = None
    interface_id: Identifier
    bolt_group_id: Identifier
    bolt_location_id: Identifier
    load_combination_id: Identifier
    source_action_id: Identifier | None = None
    explicit_resolved_demand: ExplicitResolvedDemandDTO | None = None
    material_snapshots: tuple[MaterialSnapshotDTO, ...]
    material_assignments: tuple[MaterialAssignmentDTO, ...]
    fastener_snapshot: FastenerSnapshotDTO
    bolt_diameter: QuantityDTO
    published_code_unit_basis: PublishedCodeUnitBasis
    time_effect_category: TimeEffectCategory
    end_use_factors: EndUseFactorsDTO
    lap_configuration: LapConfiguration
    whole_connection_requires_section_2_3_2: StrictBool = False

    @model_validator(mode="after")
    def validate_geometry_source(self) -> SingleBoltEvaluationRequestDTO:
        if (self.geometry is None) == (self.geometry_template is None):
            raise ValueError("exactly one of geometry or geometry_template is required")
        return self


class SingleBoltPreviewRequestDTO(_StrictModel):
    """Strict canonical-preview input with pure design factors intentionally absent."""

    calculation_id: Identifier
    joint_assembly: JointAssemblyDTO
    geometry: GeometryDTO | None = None
    geometry_template: BraceToColumnFlangeTemplateGeometryDTO | None = None
    view_extents: ConnectionViewExtentsDTO | None = None
    interface_id: Identifier
    bolt_group_id: Identifier
    bolt_location_id: Identifier
    load_combination_id: Identifier
    source_action_id: Identifier | None = None
    explicit_resolved_demand: ExplicitResolvedDemandDTO | None = None
    material_snapshots: tuple[MaterialSnapshotDTO, ...]
    material_assignments: tuple[MaterialAssignmentDTO, ...]
    fastener_snapshot: PreviewFastenerGeometryDTO
    bolt_diameter: QuantityDTO
    lap_configuration: LapConfiguration

    @model_validator(mode="after")
    def validate_geometry_source(self) -> SingleBoltPreviewRequestDTO:
        if (self.geometry is None) == (self.geometry_template is None):
            raise ValueError("exactly one of geometry or geometry_template is required")
        if self.geometry_template is not None and self.view_extents is None:
            raise ValueError("view_extents are required for brace-to-column template preview")
        if self.geometry is not None and self.view_extents is not None:
            raise ValueError("view_extents are supported only with template preview geometry")
        return self


class SourceReferenceDTO(_StrictModel):
    standard_id: str
    edition: str
    errata: str
    section: str
    equation_id: str | None


class OrchestrationIssueDTO(_StrictModel):
    code: str
    message: str
    identities: tuple[str, ...]


class SingleBoltEvaluationResponseDTO(_StrictModel):
    """Deterministic transport view of the authoritative orchestration response."""

    api_transport_schema_version: Literal["0.5.0-draft"]
    project_schema_version: str
    calculation_contract_version: str
    calculation_engine_version: str
    engineering_rule_set_version: str
    calculation_id: str
    assembly_id: str
    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    load_combination_id: str
    unit_system: EngineeringUnitSystem
    calculation_fingerprint: str | None
    material_assignments: tuple[dict[str, JsonValue], ...]
    fastener: dict[str, JsonValue]
    resolved_layers: tuple[dict[str, JsonValue], ...]
    source_action_trace: dict[str, JsonValue] | None
    resolved_demand: dict[str, JsonValue] | None
    plans: tuple[dict[str, JsonValue], ...]
    results: tuple[dict[str, JsonValue], ...]
    aggregate_status: str | None
    governing_check_ids: tuple[str, ...]
    qualification_flags: tuple[str, ...]
    issues: tuple[OrchestrationIssueDTO, ...]
    warnings: tuple[str, ...]
    source_references: tuple[SourceReferenceDTO, ...]
    visualization: dict[str, JsonValue]


class SingleBoltPreviewResponseDTO(_StrictModel):
    """Deterministic zero-resistance canonical model/action preview."""

    preview_schema_version: Literal["0.2.0-draft"]
    project_schema_version: str
    calculation_id: str
    assembly_id: str
    interface_id: str
    bolt_group_id: str
    bolt_location_id: str
    load_combination_id: str
    unit_system: EngineeringUnitSystem
    geometry_status: str
    geometry_issues: tuple[OrchestrationIssueDTO, ...]
    resolved_layers: tuple[dict[str, JsonValue], ...]
    material_relationships: tuple[dict[str, JsonValue], ...]
    source_action_trace: dict[str, JsonValue] | None
    visualization: dict[str, JsonValue] | None
    design_check_ready: StrictBool
    design_check_blocking_reasons: tuple[str, ...]


__all__ = (
    "API_TRANSPORT_SCHEMA_VERSION",
    "BraceToColumnFlangeTemplateGeometryDTO",
    "ConnectionViewExtentsDTO",
    "HealthResponse",
    "MetadataResponse",
    "QuantityDTO",
    "SingleBoltEvaluationRequestDTO",
    "SingleBoltEvaluationResponseDTO",
    "SingleBoltPreviewRequestDTO",
    "SingleBoltPreviewResponseDTO",
)
