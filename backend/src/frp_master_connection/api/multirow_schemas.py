"""Strict stateless transport contracts for the Stage 2.4C multi-row workflow."""

from __future__ import annotations

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

from frp_master_connection.api.schemas import (
    Identifier,
    QuantityDTO,
    SingleBoltPreviewRequestDTO,
    _StrictModel,
)
from frp_master_connection.application import EngineerDistributionKind, MultiRowDemandSource
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    FirstRowPlanMethod,
    LapConfiguration,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
)
from frp_master_connection.domain import EngineeringUnitSystem

MULTIROW_API_TRANSPORT_SCHEMA_VERSION: Literal["0.3.0-draft"] = "0.3.0-draft"

PositiveInt = Annotated[StrictInt, Field(ge=1)]


class MultiRowEndUseFactorsDTO(_StrictModel):
    cm: StrictStr
    ct: StrictStr
    cch: StrictStr
    source_reference: Annotated[StrictStr, Field(min_length=1, max_length=512)]
    approval_metadata: tuple[Annotated[StrictStr, Field(min_length=1, max_length=256)], ...]

    @model_validator(mode="after")
    def validate_factors(self) -> MultiRowEndUseFactorsDTO:
        from decimal import Decimal, InvalidOperation

        for value in (self.cm, self.ct, self.cch):
            try:
                parsed = Decimal(value)
            except InvalidOperation as error:
                raise ValueError("End-use factors must be finite decimal strings.") from error
            if not parsed.is_finite() or parsed <= 0:
                raise ValueError("End-use factors must be finite and positive.")
        if not self.approval_metadata:
            raise ValueError("End-use factor approval metadata is required.")
        return self


class MultiRowLayerDTO(_StrictModel):
    layer_id: Identifier
    component_id: Identifier
    material_id: Literal["ICE_LOCKED_PULTRUDED_FRP"]
    thickness: QuantityDTO
    element_classification: PultrudedElementClassification
    material_axis_angle_degrees: StrictStr
    end_use_factors: MultiRowEndUseFactorsDTO
    bearing_thread_status: ThreadStatus

    @field_validator("material_axis_angle_degrees")
    @classmethod
    def validate_material_axis_angle(cls, value: str) -> str:
        from decimal import Decimal, InvalidOperation

        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(
                "material_axis_angle_degrees must be a finite decimal string."
            ) from error
        if not parsed.is_finite() or parsed < 0 or parsed >= 180:
            raise ValueError("material_axis_angle_degrees must be at least 0 and less than 180.")
        return value


class MultiRowMethodProvenanceDTO(_StrictModel):
    source_method: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    source_document_or_calculation: (
        Annotated[StrictStr, Field(min_length=1, max_length=512)] | None
    ) = None
    revision: Annotated[StrictStr, Field(min_length=1, max_length=128)] | None = None
    load_combination: Identifier | None = None
    reference_point: Annotated[StrictStr, Field(min_length=1, max_length=256)] | None = None
    clearance_or_contact_modeled: StrictBool | None = None
    engineer_confirmed: StrictBool = False


class MultiRowEngineerAllocationDTO(_StrictModel):
    row_ordinal: PositiveInt
    fraction: StrictStr | None = None
    direct_force: QuantityDTO | None = None

    @model_validator(mode="after")
    def validate_exactly_one_value(self) -> MultiRowEngineerAllocationDTO:
        if (self.fraction is None) == (self.direct_force is None):
            raise ValueError("Each allocation requires exactly one fraction or direct_force.")
        if self.fraction is not None:
            from decimal import Decimal, InvalidOperation

            try:
                fraction = Decimal(self.fraction)
            except InvalidOperation as error:
                raise ValueError("fraction must be a finite decimal string.") from error
            if not fraction.is_finite() or fraction < 0:
                raise ValueError("fraction must be finite and nonnegative.")
        return self


class MultiRowBoltAxisTensionDTO(_StrictModel):
    bolt_id: Identifier
    demand: QuantityDTO


class MultiRowConnectionRequestDTO(_StrictModel):
    orchestration_contract_version: Literal["2.5C-RC1"] = "2.5C-RC1"
    request_id: Identifier
    connection_id: Identifier
    interface_id: Identifier
    load_combination_id: Identifier
    source_reference: Annotated[StrictStr, Field(min_length=1, max_length=512)]
    display_unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    row_count: PositiveInt
    bolts_per_row: PositiveInt
    bolt_diameter: QuantityDTO
    hole_basis: PublishedCodeUnitBasis
    pitch: QuantityDTO
    gauge: QuantityDTO
    unloaded_end_e1: QuantityDTO
    loaded_boundary_to_row_1_distance: QuantityDTO
    negative_side_distance: QuantityDTO
    positive_side_distance: QuantityDTO
    geometry_tolerance: QuantityDTO
    material_pair: ConnectedMaterialPair
    layers: tuple[MultiRowLayerDTO, ...]
    demand_source: MultiRowDemandSource = MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND
    signed_force_x: QuantityDTO | None = None
    signed_force_y: QuantityDTO | None = None
    force_reference: Annotated[StrictStr, Field(min_length=1, max_length=256)] | None = None
    automatic_action_source_id: Identifier | None = None
    row_distribution_basis: RowDistributionBasis
    engineer_distribution_kind: EngineerDistributionKind | None = None
    engineer_allocations: tuple[MultiRowEngineerAllocationDTO, ...] = ()
    provenance: MultiRowMethodProvenanceDTO
    bolt_axis_tension_required: StrictBool = False
    bolt_axis_tensions: tuple[MultiRowBoltAxisTensionDTO, ...] = ()
    time_effect_category: TimeEffectCategory
    lap_configuration: LapConfiguration
    first_row_method: FirstRowPlanMethod
    prescribed_lbr: StrictStr | None = None
    force_line_offset: QuantityDTO
    eccentricity_tolerance: QuantityDTO
    physical_connection: SingleBoltPreviewRequestDTO | None = None

    @model_validator(mode="after")
    def validate_public_shape(self) -> MultiRowConnectionRequestDTO:
        if self.row_count < 2:
            raise ValueError("row_count must be at least two.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        automatic = self.demand_source is MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE
        explicit_fields = (self.signed_force_x, self.signed_force_y, self.force_reference)
        if automatic:
            if any(item is not None for item in explicit_fields):
                raise ValueError("Automatic demand cannot include explicit demand fields.")
            if self.automatic_action_source_id is None or self.physical_connection is None:
                raise ValueError(
                    "Automatic demand requires canonical member-end action and physical context."
                )
            if self.physical_connection.source_action_id != self.automatic_action_source_id:
                raise ValueError("Automatic action source must match the physical request.")
        elif any(item is None for item in explicit_fields):
            raise ValueError("Explicit demand requires signed forces and force_reference.")
        elif self.automatic_action_source_id is not None:
            raise ValueError("Explicit demand cannot include automatic action-source fields.")
        layer_ids = tuple(item.layer_id for item in self.layers)
        if not layer_ids or len(layer_ids) != len(set(layer_ids)):
            raise ValueError("Layer identities must be present and unique.")
        tension_ids = tuple(item.bolt_id for item in self.bolt_axis_tensions)
        if len(tension_ids) != len(set(tension_ids)):
            raise ValueError("Bolt-axis tension identities must be unique.")
        ordinals = tuple(item.row_ordinal for item in self.engineer_allocations)
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("Engineer allocation ordinals must be unique.")
        engineer_defined = (
            self.row_distribution_basis is RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION
        )
        if engineer_defined:
            if self.engineer_distribution_kind is None:
                raise ValueError("Engineer-defined distribution kind is required.")
            if set(ordinals) != set(range(1, self.row_count + 1)):
                raise ValueError("Engineer allocations must cover every row exactly once.")
            if not self.provenance.engineer_confirmed:
                raise ValueError("Engineer-defined distribution requires confirmed provenance.")
            fractions = all(item.fraction is not None for item in self.engineer_allocations)
            forces = all(item.direct_force is not None for item in self.engineer_allocations)
            if (
                self.engineer_distribution_kind is EngineerDistributionKind.FRACTIONS
                and not fractions
            ):
                raise ValueError("FRACTIONS requires a fraction for every row.")
            if (
                self.engineer_distribution_kind is EngineerDistributionKind.DIRECT_ROW_FORCES
                and not forces
            ):
                raise ValueError("DIRECT_ROW_FORCES requires a force for every row.")
        elif self.engineer_distribution_kind is not None or self.engineer_allocations:
            raise ValueError("Engineer allocations are reserved for the engineer-defined method.")
        if self.prescribed_lbr is not None:
            QuantityDTO.validate_decimal_string(self.prescribed_lbr)
        return self


class MultiRowPreviewResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.3.0-draft"]
    orchestration_contract_version: Literal["2.5C-RC1"]
    preview_schema_version: Literal["0.2.0-draft"]
    visualization_schema_version: Literal["0.2.0-draft"]
    request_id: str
    connection_id: str
    geometry_status: str
    plan_availability: str
    method_applicability: str
    qualification: str
    warnings: tuple[str, ...]
    preview_fingerprint: str
    resistance_evaluated: Literal[False]
    design_check_ready: bool
    visualization: dict[str, JsonValue] | None
    demand_source: MultiRowDemandSource
    automatic_demand_result: dict[str, JsonValue] | None


class MultiRowDesignResponseDTO(_StrictModel):
    api_transport_schema_version: Literal["0.3.0-draft"]
    orchestration_contract_version: Literal["2.5C-RC1"]
    preview_schema_version: Literal["0.2.0-draft"]
    visualization_schema_version: Literal["0.2.0-draft"]
    request_id: str
    connection_id: str
    preview: dict[str, JsonValue]
    calculation_result: dict[str, JsonValue] | None
    demand_source: MultiRowDemandSource
    automatic_demand_result: dict[str, JsonValue] | None
    automatic_handoff_results: tuple[dict[str, JsonValue], ...]
    automatic_group_mode_integration: dict[str, JsonValue] | None


__all__ = (
    "MULTIROW_API_TRANSPORT_SCHEMA_VERSION",
    "MultiRowBoltAxisTensionDTO",
    "MultiRowConnectionRequestDTO",
    "MultiRowDesignResponseDTO",
    "MultiRowEndUseFactorsDTO",
    "MultiRowEngineerAllocationDTO",
    "MultiRowLayerDTO",
    "MultiRowMethodProvenanceDTO",
    "MultiRowPreviewResponseDTO",
)
