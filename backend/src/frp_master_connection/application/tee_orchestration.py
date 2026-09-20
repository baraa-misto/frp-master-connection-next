"""Backend-authoritative Stage 3.2 FRP Tee composition and orchestration.

This module introduces no equation.  It builds one canonical two-interface
assembly, resolves both physical bolt paths, invokes the accepted multi-row
orchestration independently for each interface, and then applies the Stage 3.2
fail-closed whole-assembly rule.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.application.calculation_orchestration import (
    PenetratedLayerMaterialAssignment,
    SingleBoltOrchestrationRequest,
)
from frp_master_connection.application.connection_preview import (
    SingleBoltPreviewResult,
    preview_single_bolt_connection,
)
from frp_master_connection.application.member_profile_geometry import (
    create_member_profile_cross_section,
    create_oriented_standard_topology,
    kernel_profile_surface_patch_ids,
    resolve_profile_local_z_reference,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowDemandSource,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    MultiRowOrchestrationResponse,
    MultiRowPreviewResult,
    evaluate_multirow_connection,
    evaluate_multirow_connection_through_handoff,
    preview_multirow_connection,
)
from frp_master_connection.application.shared_support_integration import (
    IntegratedFullThroughBoltTrace,
    build_integrated_full_through_bolt,
    require_shared_support_selection,
)
from frp_master_connection.application.visualization import (
    BoltDisplaySnapshot,
    HoleDisplaySnapshot,
    ScalarParameter,
    SingleBoltVisualizationSnapshot,
    VisualizationPrimitive,
    VisualizationPrimitiveKind,
    VisualizationResolutionStatus,
    WasherDisplaySnapshot,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    EndUseFactors,
    FastenerSnapshot,
    FirstRowPlanMethod,
    GeometryStatus,
    LapConfiguration,
    MaterialPropertySnapshot,
    MethodProvenance,
    MultiRowOverallDisposition,
    PhysicalQuantity,
    PlanAvailability,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    PultrudedElementForm,
    RowDistributionBasis,
    ThreadStatus,
    ThreadStatusAssignment,
    TimeEffectCategory,
    Unit,
    canonical_decimal_string,
    create_locked_f593_fastener_snapshot,
    create_locked_ice_material_snapshot,
    create_standard_hole,
    decimal_from_finite_real,
    select_time_effect_factor,
)
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.calculation.material_compatibility import (
    ExistingMetallicBoltEligibilityResult,
    resolve_existing_metallic_bolt_eligibility,
    resolve_legacy_material_pair,
)
from frp_master_connection.domain import (
    ActionConvention,
    AngleProfileDimensions,
    AssemblyMember,
    BoltGroup,
    BoltGroupFastenerSystemAssignment,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionAssemblyScaffold,
    ConnectionDesignCategory,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentEngineeringAssignment,
    ConnectorComponentKind,
    ConnectorComponentRole,
    ConnectorMaterialAssignment,
    ConnectorMaterialFamily,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringCoverageClass,
    EngineeringGeometryReference,
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    EngineeringUnitSystem,
    ExactProfileVector3D,
    FastenerMaterialAssignment,
    FastenerMaterialFamily,
    FastenerSystem,
    FlatPlateProfileDimensions,
    ForceVector3D,
    FRPComponentOrientation,
    JointAssembly,
    LoadCombination,
    LoadInputBasis,
    ManualMemberEndAction,
    MaterialBehaviorFamily,
    MemberEnd,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSizeBasis,
    MemberProfileSurfaceId,
    MemberRole,
    MomentVector3D,
    ParticipantKind,
    ParticipantReference,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
    ProfileSurfaceDefinition,
    PropertySourceConfirmation,
    ReferencePoint,
    ReferencePointKind,
    ResistanceAuthority,
    ResistanceAuthorityKind,
    SectionFamily,
    SectionTopology,
    SelectedSupportFlange,
    SharedSupportTargetId,
    TeeBoltLayout,
    TeeBoltPlacementMode,
    TeeBraceDimensions,
    TeeConnectorDimensions,
    TeeConnectorLengthAnchor,
    TeeInterfaceIdentity,
    TeeSupportDimensions,
    TeeSupportRole,
    TransferIntent,
    WideFlangeIProfileDimensions,
    bind_connection_assembly_scaffold,
    member_profile_fingerprint,
    profile_geometry_fingerprint,
    profile_section_geometry_adapter,
    require_direct_tee_profile_surface,
    resolve_angle_leg_bolt_path,
    resolve_profile_wall_bolt_path,
)
from frp_master_connection.geometry import (
    AuthoritativeCutPlane3D,
    BoltGroupGeometrySpecification,
    BoltPathDefinition,
    CartesianFrame3D,
    ComponentSurfaceSet3D,
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    GeometryComparisonTolerance,
    IntendedPenetratedLayer,
    InterfaceOriginSpecification,
    InterfaceTargetSide,
    InterfaceTargetSideSpecification,
    InterfaceZoneReference,
    JointGeometryBasis,
    JointGeometryContext,
    LocalRectangularPrism3D,
    LongitudinalExtent,
    PlacedComponentGeometry3D,
    PlanarRectangularSurface3D,
    ResolvedBoltGroupGeometry,
    ResolvedConnectionInterfaceGeometry,
    ResolvedPenetratedLayer,
    SectionDatumOffset,
    SurfacePatch3D,
    SurfacePatchRole,
    TeeDimensions,
    TrimmedComponentSolids3D,
    UnitVector3D,
    Vector3D,
    create_component_surface_set,
    create_tee_geometry,
    place_connector,
    place_member,
    placed_rectangular_elements_overlap,
    resolve_bolt_group_geometry,
    resolve_connection_interface_geometry,
    signed_distance_to_plane,
    trim_placed_rectangular_component,
)

TEE_ORCHESTRATION_CONTRACT_VERSION = "3.2-RC1"
TEE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
TEE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"
TEE_R2_ORCHESTRATION_CONTRACT_VERSION = "3.2-R2"
TEE_R2_PREVIEW_SCHEMA_VERSION = "0.2.0-draft"
TEE_R2_VISUALIZATION_SCHEMA_VERSION = "0.2.0-draft"
TEE_C2_ORCHESTRATION_CONTRACT_VERSION = "3.3C2-RC1"
TEE_C2_PREVIEW_SCHEMA_VERSION = "0.3.0-draft"
TEE_C2_VISUALIZATION_SCHEMA_VERSION = "0.3.0-draft"

_ASSEMBLY_ID = "stage-3-2-tee-assembly"
_BRACE_ID = "tee-brace"
_SUPPORT_ID = "tee-support"
_TEE_ID = "tee-connector"
_LOAD_ID = "tee-load-combination"
_ACTION_ID = "tee-member-end-action"
_GROUP_A_ID = "tee-bolt-group-a"
_GROUP_B_ID = "tee-bolt-group-b"
_BASE_A_ID = "tee-base-bolt-a"
_BASE_B_ID = "tee-base-bolt-b"
_ZONE_A_BRACE = "tee-zone-a-brace"
_ZONE_A_BRACE_PENETRATION = "tee-zone-a-brace-penetration"
_ZONE_A_STEM = "tee-zone-a-stem"
_ZONE_B_TEE = "tee-zone-b-tee"
_ZONE_B_SUPPORT = "tee-zone-b-support"
_TEE_LONGITUDINAL_DATUM_ID = "TEE_TEMPLATE_LONGITUDINAL_DATUM"

# Compatibility names remain explicit because controlled Tee tests patch these
# seams while the implementation now resides in the shared profile adapter.
_profile_cross_section = create_member_profile_cross_section
_oriented_topology = create_oriented_standard_topology
_effective_profile_local_z = resolve_profile_local_z_reference


class TeeBodyResistanceStatus(StrEnum):
    """Required Stage 3.2 limitation for the unauthorised general Tee body."""

    NOT_EVALUATED = "NOT_EVALUATED"


class TeeAssemblyStatus(StrEnum):
    """Fail-first whole-assembly status with no ordinary Stage 3.2 PASS."""

    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class TeeVectorInput:
    """Exact quantity components for a global vector."""

    x: PhysicalQuantity
    y: PhysicalQuantity
    z: PhysicalQuantity

    def __post_init__(self) -> None:
        if not all(isinstance(item, PhysicalQuantity) for item in (self.x, self.y, self.z)):
            raise TypeError("Tee vector components must be physical quantities.")
        if len({self.x.dimension, self.y.dimension, self.z.dimension}) != 1:
            raise ValueError("Tee vector components must share one dimension.")


def adapt_legacy_tee_brace_profile(dimensions: TeeBraceDimensions) -> MemberProfile:
    """Map the RC1 plate fields to exactly one explicit R2 profile identity."""

    if not isinstance(dimensions, TeeBraceDimensions):
        raise TypeError("dimensions must be a TeeBraceDimensions.")
    return MemberProfile(
        id="tee-brace-legacy-flat-plate-profile",
        member_id=_BRACE_ID,
        role=MemberRole.BRACE,
        family=MemberProfileFamily.FLAT_PLATE,
        dimensions=FlatPlateProfileDimensions(
            member_length=dimensions.view_length,
            width=dimensions.width,
            thickness=dimensions.thickness,
        ),
        material_kind=ComponentMaterialKind.PULTRUDED_FRP,
        material_orientation=FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, _BRACE_ID),
            PrincipalAxisFamily.X,
        ),
        orientation=MemberProfileOrientation.ROTATION_0,
        selected_surface=MemberProfileSurfaceId.FACE_NEG,
        size_basis=MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )


def _adapt_tee_support_profile(
    dimensions: TeeSupportDimensions,
    role: TeeSupportRole,
    selected_flange: SelectedSupportFlange,
) -> MemberProfile:
    """Adapt the unchanged Tee support fields through the shared W/I profile seam."""

    member_role = MemberRole.COLUMN if role is TeeSupportRole.COLUMN else MemberRole.BEAM
    selected_surface = (
        MemberProfileSurfaceId.FLANGE_POS_OUTER
        if selected_flange is SelectedSupportFlange.POSITIVE_LOCAL_Z
        else MemberProfileSurfaceId.FLANGE_NEG_OUTER
    )
    return MemberProfile(
        id="tee-support-wide-flange-profile",
        member_id=_SUPPORT_ID,
        role=member_role,
        family=MemberProfileFamily.WIDE_FLANGE_I,
        dimensions=WideFlangeIProfileDimensions(
            member_length=dimensions.member_length,
            depth=dimensions.overall_depth,
            flange_width=dimensions.flange_width,
            web_thickness=dimensions.web_thickness,
            flange_thickness=dimensions.flange_thickness,
        ),
        material_kind=ComponentMaterialKind.PULTRUDED_FRP,
        material_orientation=FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, _SUPPORT_ID),
            PrincipalAxisFamily.X,
        ),
        orientation=MemberProfileOrientation.ROTATION_0,
        selected_surface=selected_surface,
        size_basis=MemberProfileSizeBasis.CUSTOM_DIMENSIONS,
    )


def _tee_support_selection(
    request: TeeConnectorOrchestrationRequest,
) -> tuple[SharedSupportTargetId, MemberProfile]:
    """Resolve legacy W-flange fields or the explicit shared C2 contract."""

    if request.support_target_id is not None:
        profile = cast(MemberProfile, request.support_profile)
        require_shared_support_selection(request.support_target_id, profile)
        return request.support_target_id, profile
    target_id = (
        SharedSupportTargetId.W_COLUMN_FLANGE
        if request.support_role is TeeSupportRole.COLUMN
        else SharedSupportTargetId.W_BEAM_FLANGE
    )
    return (
        target_id,
        _adapt_tee_support_profile(
            request.support_dimensions,
            request.support_role,
            request.selected_support_flange,
        ),
    )


@dataclass(frozen=True, slots=True)
class TeeConnectorOrchestrationRequest:
    """Canonical server-owned Tee template request."""

    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    support_role: TeeSupportRole
    selected_support_flange: SelectedSupportFlange
    connector_dimensions: TeeConnectorDimensions
    support_dimensions: TeeSupportDimensions
    brace_dimensions: TeeBraceDimensions | None
    interface_a_layout: TeeBoltLayout
    interface_b_layout: TeeBoltLayout
    bolt_diameter: PhysicalQuantity
    hole_basis: PublishedCodeUnitBasis
    global_force: TeeVectorInput
    global_moment: TeeVectorInput
    global_reference_point: TeeVectorInput
    connected_member_profile: MemberProfile
    orchestration_contract_version: str = TEE_ORCHESTRATION_CONTRACT_VERSION
    brace_inclination_degrees: Decimal = Decimal(0)
    connected_member_end_trim_enabled: bool = False
    connected_member_end_clearance: PhysicalQuantity | None = None
    connector_length_anchor: TeeConnectorLengthAnchor = TeeConnectorLengthAnchor.CENTER
    connector_length_anchor_position: PhysicalQuantity | None = None
    support_target_id: SharedSupportTargetId | None = None
    support_profile: MemberProfile | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version not in {
            TEE_ORCHESTRATION_CONTRACT_VERSION,
            TEE_R2_ORCHESTRATION_CONTRACT_VERSION,
            TEE_C2_ORCHESTRATION_CONTRACT_VERSION,
        }:
            raise ValueError("Unsupported Tee orchestration contract version.")
        if not isinstance(self.connected_member_profile, MemberProfile):
            raise TypeError("connected_member_profile must be a MemberProfile.")
        if not isinstance(self.brace_inclination_degrees, Decimal):
            raise TypeError("brace_inclination_degrees must be a Decimal.")
        if not self.brace_inclination_degrees.is_finite():
            raise ValueError("brace_inclination_degrees must be finite.")
        if not Decimal(-90) <= self.brace_inclination_degrees <= Decimal(90):
            raise ValueError("brace_inclination_degrees must be between -90 and 90 degrees.")
        if not isinstance(self.connected_member_end_trim_enabled, bool):
            raise TypeError("connected_member_end_trim_enabled must be a bool.")
        if not isinstance(self.connector_length_anchor, TeeConnectorLengthAnchor):
            raise TypeError("connector_length_anchor must be a TeeConnectorLengthAnchor.")
        if self.connector_length_anchor_position is not None:
            if not isinstance(self.connector_length_anchor_position, PhysicalQuantity):
                raise TypeError("connector_length_anchor_position must be a PhysicalQuantity.")
            if self.connector_length_anchor_position.dimension.value != "LENGTH":
                raise ValueError("connector_length_anchor_position must be a length.")
            if self.connector_length_anchor_position.unit is not self.source_length_unit:
                raise ValueError("connector_length_anchor_position must use source_length_unit.")
        if self.connected_member_end_trim_enabled:
            clearance = self.connected_member_end_clearance
            if not isinstance(clearance, PhysicalQuantity):
                raise TypeError(
                    "connected_member_end_clearance must be a PhysicalQuantity "
                    "when trim is enabled."
                )
            if clearance.dimension.value != "LENGTH" or clearance.magnitude < 0:
                raise ValueError("connected_member_end_clearance must be a nonnegative length.")
        elif self.connected_member_end_clearance is not None:
            raise ValueError("connected_member_end_clearance must be absent when trim is disabled.")
        if (
            self.connected_member_profile.member_id != _BRACE_ID
            or self.connected_member_profile.role is not MemberRole.BRACE
            or self.connected_member_profile.material_kind
            is not ComponentMaterialKind.PULTRUDED_FRP
        ):
            raise ValueError(
                "The Tee connected-member profile must own the controlled FRP brace member."
            )
        require_direct_tee_profile_surface(self.connected_member_profile)
        if self.orchestration_contract_version == TEE_ORCHESTRATION_CONTRACT_VERSION:
            if self.brace_dimensions is None:
                raise ValueError("3.2-RC1 requires legacy brace dimensions.")
            if self.brace_dimensions.width < self.connector_dimensions.connector_length:
                raise ValueError("The connected brace plate must cover the Interface A row extent.")
            if self.connected_member_profile != adapt_legacy_tee_brace_profile(
                self.brace_dimensions
            ):
                raise ValueError("3.2-RC1 requires the deterministic flat-plate adapter.")
        elif self.brace_dimensions is not None:
            raise ValueError("3.2-R2 forbids legacy brace dimensions.")
        if (self.support_target_id is None) is not (self.support_profile is None):
            raise ValueError("support_target_id and support_profile must be supplied together.")
        if self.support_target_id is not None:
            require_shared_support_selection(
                self.support_target_id,
                cast(MemberProfile, self.support_profile),
            )
            if self.orchestration_contract_version != TEE_C2_ORCHESTRATION_CONTRACT_VERSION:
                raise ValueError("Explicit shared support targets require the C2 contract.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        expected_unit = (
            Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        )
        if self.source_length_unit is not expected_unit:
            raise ValueError("Tee source length unit must match the engineering unit system.")
        if self.bolt_diameter.dimension.value != "LENGTH" or self.bolt_diameter.magnitude <= 0:
            raise ValueError("bolt_diameter must be a positive length.")
        if self.global_force.x.dimension.value != "FORCE":
            raise ValueError("global_force must contain forces.")
        if self.global_moment.x.dimension.value != "MOMENT":
            raise ValueError("global_moment must contain moments.")
        if self.global_reference_point.x.dimension.value != "LENGTH":
            raise ValueError("global_reference_point must contain lengths.")
        if (
            self.interface_a_layout.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
            and self.interface_a_layout.required_row_extent
            > self.connector_dimensions.connector_length
        ):
            raise ValueError("Interface A rows do not fit within the Tee connector length.")
        if (
            self.interface_b_layout.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
            and self.interface_b_layout.required_row_extent
            > self.connector_dimensions.connector_length
        ):
            raise ValueError("Interface B rows do not fit within the Tee connector length.")
        if (
            self.interface_a_layout.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
            and self.interface_a_layout.required_line_extent > self.connector_dimensions.stem_depth
        ):
            raise ValueError("Interface A bolt lines do not fit within the Tee stem depth.")
        if (
            self.interface_b_layout.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
            and self.interface_b_layout.required_line_extent
            > self.connector_dimensions.flange_width
        ):
            raise ValueError("Interface B bolt lines do not fit within the Tee flange width.")


@dataclass(frozen=True, slots=True)
class TeeMaterialAuthorityTrace:
    connector_material_family: ConnectorMaterialFamily
    fastener_material_family: FastenerMaterialFamily
    fastener_snapshot_id: str
    metallic_bolt_eligibility: ExistingMetallicBoltEligibilityResult


@dataclass(frozen=True, slots=True)
class TeeConnectedMemberProfileTrace:
    profile_id: str
    member_id: str
    role: MemberRole
    profile_family: MemberProfileFamily
    size_basis: MemberProfileSizeBasis
    dimensions: MemberProfileDimensions
    profile_orientation: MemberProfileOrientation
    selected_profile_surface: MemberProfileSurfaceId
    material_kind: ComponentMaterialKind
    member_profile_fingerprint: str
    profile_geometry_fingerprint: str
    surface_patch_id: str
    physical_element_role: PhysicalSectionElementRole
    brace_inclination_degrees: Decimal
    brace_inclination_sine: Decimal
    brace_inclination_cosine: Decimal
    brace_placement_frame: CartesianFrame3D


@dataclass(frozen=True, slots=True)
class TeeSupportProfileTrace:
    target_id: SharedSupportTargetId
    profile_id: str
    member_id: str
    role: MemberRole
    profile_family: MemberProfileFamily
    dimensions: MemberProfileDimensions
    profile_orientation: MemberProfileOrientation
    selected_profile_surface: MemberProfileSurfaceId
    surface_patch_id: str
    member_profile_fingerprint: str
    profile_geometry_fingerprint: str


class TeeFixedGridCompatibilityStatus(StrEnum):
    """Fail-closed identity for the prescribed row/grid-direction relationship."""

    COMPATIBLE = "COMPATIBLE"
    ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN = (
        "ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN"
    )


@dataclass(frozen=True, slots=True)
class TeeHoleClearanceTrace:
    """Exact complete-hole clearances to the four finite interface boundaries."""

    vertical_positive: PhysicalQuantity
    vertical_negative: PhysicalQuantity
    horizontal_positive: PhysicalQuantity
    horizontal_negative: PhysicalQuantity
    minimum: PhysicalQuantity
    governing_bolt_id: str
    governing_boundary_id: str
    exact_deficit: PhysicalQuantity | None
    geometry_valid: bool
    minimum_complete_hole_containment: PhysicalQuantity | None = None
    tee_positive_end_coordinate: PhysicalQuantity | None = None
    tee_negative_end_coordinate: PhysicalQuantity | None = None
    tee_positive_end_complete_hole_clearance: PhysicalQuantity | None = None
    tee_negative_end_complete_hole_clearance: PhysicalQuantity | None = None
    governing_tee_end_id: str | None = None
    governing_tee_end_bolt_id: str | None = None
    minimum_tee_end_complete_hole_clearance: PhysicalQuantity | None = None


@dataclass(frozen=True, slots=True)
class TeeInterfacePlacementTrace:
    """Backend-authored datum, frame, normalized position, and physical identity."""

    datum_id: str
    datum_point: PositionVector3D
    vertical_axis: UnitVector3D
    horizontal_axis: UnitVector3D
    normal_axis: UnitVector3D
    placement_mode: TeeBoltPlacementMode
    vertical_offset: PhysicalQuantity
    horizontal_offset: PhysicalQuantity
    equivalent_edge_distances: TeeBoltLayout
    clearances: TeeHoleClearanceTrace
    physical_geometry_fingerprint: str
    method_compatibility: TeeFixedGridCompatibilityStatus
    bolt_centers_hvn: tuple[ExactProfileVector3D, ...]


class TeeMemberEndInterferenceStatus(StrEnum):
    """Physical relationship between the connected member and Tee root obstruction."""

    CLEAR = "CLEAR"
    INTERFERENCE_DETECTED = "INTERFERENCE_DETECTED"
    TRIMMED_CLEAR = "TRIMMED_CLEAR"
    REMAINING_INTERFERENCE = "REMAINING_INTERFERENCE"


@dataclass(frozen=True, slots=True)
class TeeTrimBoltClearanceTrace:
    """One Interface A bolt/hole distance to the fabricated end."""

    bolt_id: str
    center_to_trim_edge: PhysicalQuantity
    hole_edge_to_trim_edge: PhysicalQuantity
    trim_edge_id: str


@dataclass(frozen=True, slots=True)
class TeeMemberEndTrimTrace:
    """Backend-authored Tee reference plane, fabrication cut, and clearances."""

    enabled: bool
    normalized_clearance: PhysicalQuantity | None
    reference_plane_id: str
    reference_plane_origin: PositionVector3D
    reference_plane_normal: UnitVector3D
    cut_plane_id: str | None
    cut_plane_origin: PositionVector3D | None
    cut_plane_normal: UnitVector3D | None
    measured_plane_clearance: PhysicalQuantity | None
    interference_status: TeeMemberEndInterferenceStatus
    interfering_physical_element_ids: tuple[str, ...]
    trimmed_member_geometry_identity: str | None
    fabricated_trim_edge_ids: tuple[str, ...]
    bolt_clearances: tuple[TeeTrimBoltClearanceTrace, ...]
    governing_bolt_id: str | None
    governing_trim_edge_id: str | None
    minimum_hole_edge_clearance: PhysicalQuantity | None
    exact_deficit: PhysicalQuantity | None
    recovery_guidance: str | None
    geometry_valid: bool


@dataclass(frozen=True, slots=True)
class TeeLongitudinalPlacementTrace:
    """Exact finite Tee-body placement relative to the stable template datum."""

    tee_longitudinal_datum_id: str
    datum_point: PositionVector3D
    longitudinal_axis: UnitVector3D
    connector_length_anchor: TeeConnectorLengthAnchor
    connector_length_anchor_position: PhysicalQuantity
    body_center_coordinate: PhysicalQuantity
    positive_end_coordinate: PhysicalQuantity
    negative_end_coordinate: PhysicalQuantity
    body_geometry_fingerprint: str


@dataclass(frozen=True, slots=True)
class TeeInterfaceResult:
    interface_id: str
    bolt_group_id: str
    normal_component: PhysicalQuantity | None
    automatic_axis_tension_generated: bool
    normal_action_supported: bool
    preview: MultiRowPreviewResult
    design: MultiRowOrchestrationResponse | None
    interface_fingerprint: str
    placement: TeeInterfacePlacementTrace


@dataclass(frozen=True, slots=True)
class TeeVisualizationSnapshot:
    schema_version: str
    base_connection: SingleBoltVisualizationSnapshot
    interface_b_connection: SingleBoltVisualizationSnapshot
    interface_zones: tuple[object, ...]
    interface_a_bolts: tuple[BoltDisplaySnapshot, ...]
    interface_b_bolts: tuple[BoltDisplaySnapshot, ...]
    selected_support_surface_id: str
    connected_member_profile: TeeConnectedMemberProfileTrace
    selected_connected_surface_id: MemberProfileSurfaceId
    selected_connected_surface_patch_id: str
    support_target_id: SharedSupportTargetId
    support_profile: TeeSupportProfileTrace
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]


@dataclass(frozen=True, slots=True)
class TeeConnectorPreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    support_role: TeeSupportRole
    selected_support_flange: SelectedSupportFlange
    connector_dimensions: TeeConnectorDimensions
    tee_longitudinal_placement: TeeLongitudinalPlacementTrace
    connected_member_profile: TeeConnectedMemberProfileTrace
    connected_member_end_trim: TeeMemberEndTrimTrace
    material_authority: TeeMaterialAuthorityTrace
    interface_a: TeeInterfaceResult
    interface_b: TeeInterfaceResult
    tee_body_resistance_status: TeeBodyResistanceStatus
    assembly_status: TeeAssemblyStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    warnings: tuple[str, ...]
    engineering_fingerprint: str
    visualization: TeeVisualizationSnapshot | None
    support_target_id: SharedSupportTargetId
    support_profile: TeeSupportProfileTrace
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]
    design_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TeeConnectorDesignResult:
    preview: TeeConnectorPreviewResult
    interface_a: TeeInterfaceResult
    interface_b: TeeInterfaceResult
    tee_body_resistance_status: TeeBodyResistanceStatus
    assembly_status: TeeAssemblyStatus
    ordinary_pass_allowed: bool
    supported_interface_failure_present: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class _TeeResolvedAssembly:
    request: TeeConnectorOrchestrationRequest
    context: JointGeometryContext
    scaffold: ConnectionAssemblyScaffold
    material_authority: TeeMaterialAuthorityTrace
    interface_a_request: MultiRowOrchestrationRequest
    interface_b_request: MultiRowOrchestrationRequest
    selected_support_surface_id: str
    connected_member_profile: TeeConnectedMemberProfileTrace
    connected_member_end_trim: TeeMemberEndTrimTrace
    tee_longitudinal_placement: TeeLongitudinalPlacementTrace
    trimmed_connected_member_solids: TrimmedComponentSolids3D | None
    interface_a_placement: TeeInterfacePlacementTrace
    interface_b_placement: TeeInterfacePlacementTrace
    support_target_id: SharedSupportTargetId
    support_profile: TeeSupportProfileTrace
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]


# Public application-layer alias for compatible connection-family composition.  The
# underlying record and the frozen single-member Tee call path remain unchanged.
TeeResolvedAssembly = _TeeResolvedAssembly


def _quantity(value: Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _normalize_srs_broad_faces(
    profile: MemberProfile,
    surface_set: ComponentSurfaceSet3D,
) -> ComponentSurfaceSet3D:
    """Treat the four physical SRS prism sides as valid broad penetration faces."""

    if profile.family is not MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        return surface_set
    selected_id, opposing_ids, _element = kernel_profile_surface_patch_ids(profile)
    normalized = tuple(
        replace(
            item,
            role=(
                SurfacePatchRole.POSITIVE_THICKNESS_FACE
                if item.id == selected_id
                else SurfacePatchRole.NEGATIVE_THICKNESS_FACE
            ),
        )
        if item.id == selected_id or item.id in opposing_ids
        else item
        for item in surface_set.patches
    )
    return ComponentSurfaceSet3D(
        surface_set.participant,
        surface_set.placed_component,
        normalized,
    )


def _rectangular_local_uv(
    profile: MemberProfile,
    placed: PlacedComponentGeometry3D,
    point: PositionVector3D,
) -> tuple[Decimal, Decimal]:
    local = placed.global_to_local(point)
    surface = require_direct_tee_profile_surface(profile)
    second = local.z if surface.plane_axis is PrincipalAxisFamily.Y else local.y
    return (
        decimal_from_finite_real(local.x) - profile.dimensions.member_length / Decimal(2),
        decimal_from_finite_real(second),
    )


def _expanded_rectangular_bolt_points(
    group: ResolvedBoltGroupGeometry,
    layout: TeeBoltLayout,
    interface_prefix: str,
) -> tuple[tuple[str, PositionVector3D], ...]:
    """Expand the one authoritative physical seed onto the exact Tee bolt grid."""

    expected_count = layout.row_count * layout.bolts_per_row
    ids = tuple(
        f"{interface_prefix}_B_R{row + 1}_L{line + 1}"
        for row in range(layout.row_count)
        for line in range(layout.bolts_per_row)
    )
    if len(group.master_centers) == expected_count:
        return tuple(
            (bolt_id, center.global_position)
            for bolt_id, center in zip(ids, group.master_centers, strict=True)
        )
    if len(group.master_centers) != 1:
        raise ValueError("The Tee full-through expansion requires one seed or one center per bolt.")
    base = group.master_centers[0].global_position
    frame = group.bolt_group_frame
    return tuple(
        (
            ids[row * layout.bolts_per_row + line],
            PositionVector3D(
                base.x
                + frame.y_axis.x * float(Decimal(row) * layout.pitch)
                + frame.z_axis.x * float(Decimal(line) * layout.gauge),
                base.y
                + frame.y_axis.y * float(Decimal(row) * layout.pitch)
                + frame.z_axis.y * float(Decimal(line) * layout.gauge),
                base.z
                + frame.y_axis.z * float(Decimal(row) * layout.pitch)
                + frame.z_axis.z * float(Decimal(line) * layout.gauge),
            ),
        )
        for row in range(layout.row_count)
        for line in range(layout.bolts_per_row)
    )


def _tee_longitudinal_coordinates(
    request: TeeConnectorOrchestrationRequest,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return exact selected-anchor, center, +L end, and -L end coordinates."""

    length = request.connector_dimensions.connector_length
    anchor_position = (
        Decimal(0)
        if request.connector_length_anchor_position is None
        else request.connector_length_anchor_position.to(request.source_length_unit).magnitude
    )
    half = length / Decimal(2)
    if request.connector_length_anchor is TeeConnectorLengthAnchor.CENTER:
        center = anchor_position
        positive_end = anchor_position + half
        negative_end = anchor_position - half
    elif request.connector_length_anchor is TeeConnectorLengthAnchor.POSITIVE_L_END:
        positive_end = anchor_position
        negative_end = anchor_position - length
        center = anchor_position - half
    else:
        negative_end = anchor_position
        positive_end = anchor_position + length
        center = anchor_position + half
    return anchor_position, center, positive_end, negative_end


def _float(value: Decimal) -> float:
    return float(value)


def _unit_axes(
    role: TeeSupportRole,
    selected: SelectedSupportFlange,
) -> tuple[UnitVector3D, UnitVector3D, UnitVector3D, int]:
    sign = 1 if selected is SelectedSupportFlange.POSITIVE_LOCAL_Z else -1
    if role is TeeSupportRole.COLUMN:
        longitudinal = UnitVector3D(0.0, 0.0, 1.0)
        support_local_z = UnitVector3D(1.0, 0.0, 0.0)
    else:
        longitudinal = UnitVector3D(1.0, 0.0, 0.0)
        support_local_z = UnitVector3D(0.0, 0.0, 1.0)
    normal = UnitVector3D(
        support_local_z.x * sign,
        support_local_z.y * sign,
        support_local_z.z * sign,
    )
    tee_local_z = UnitVector3D(-normal.x, -normal.y, -normal.z)
    transverse = tee_local_z.cross(longitudinal).normalized()
    return longitudinal, transverse, normal, sign


def _place_shared_support_profile(
    profile: MemberProfile,
    support_member: AssemblyMember,
    topology: SectionTopology,
    longitudinal: UnitVector3D,
    transverse: UnitVector3D,
    normal: UnitVector3D,
) -> PlacedComponentGeometry3D:
    """Place any C2 support so its selected physical face owns the Tee datum."""

    adapter = profile_section_geometry_adapter(profile)
    local_z = resolve_profile_local_z_reference(profile, transverse, normal, longitudinal)
    half = float(adapter.member_length) / 2.0
    provisional = place_member(
        support_member,
        _profile_cross_section(profile, topology),
        PositionVector3D(-longitudinal.x * half, -longitudinal.y * half, -longitudinal.z * half),
        PositionVector3D(longitudinal.x * half, longitudinal.y * half, longitudinal.z * half),
        local_z,
        SectionDatumOffset(
            float(adapter.section_datum_offset_y),
            float(adapter.section_datum_offset_z),
        ),
    )
    selected_id, _opposing_ids, _element_id = kernel_profile_surface_patch_ids(profile)
    patches = tuple(
        item for item in create_component_surface_set(provisional).patches if item.id == selected_id
    )
    if len(patches) != 1 or not isinstance(  # pragma: no cover - section kernel contract
        patches[0].geometry, PlanarRectangularSurface3D
    ):
        raise ValueError("The shared support selected surface did not resolve uniquely.")
    selected = patches[0].geometry
    if (  # pragma: no cover - profile resolver guarantees selected-face alignment
        selected.normal.dot(normal) < 1.0 - 1e-12
    ):
        local_z = UnitVector3D(-local_z.x, -local_z.y, -local_z.z)
        provisional = place_member(
            support_member,
            _profile_cross_section(profile, topology),
            PositionVector3D(
                -longitudinal.x * half,
                -longitudinal.y * half,
                -longitudinal.z * half,
            ),
            PositionVector3D(
                longitudinal.x * half,
                longitudinal.y * half,
                longitudinal.z * half,
            ),
            local_z,
            SectionDatumOffset(
                float(adapter.section_datum_offset_y),
                float(adapter.section_datum_offset_z),
            ),
        )
        patches = tuple(
            item
            for item in create_component_surface_set(provisional).patches
            if item.id == selected_id
        )
        if len(patches) != 1 or not isinstance(
            patches[0].geometry,
            PlanarRectangularSurface3D,
        ):  # pragma: no cover - section kernel contract
            raise ValueError("The reoriented shared support face did not resolve uniquely.")
        selected = patches[0].geometry
        if (  # pragma: no cover - exact rigid reversal guarantees the selected face
            selected.normal.dot(normal) < 1.0 - 1e-12
        ):
            raise ValueError("The shared support selected exterior face must face the connector.")
    shift = Vector3D(-selected.center.x, -selected.center.y, -selected.center.z)
    return place_member(
        support_member,
        _profile_cross_section(profile, topology),
        PositionVector3D(
            provisional.global_frame.origin.x + shift.x,
            provisional.global_frame.origin.y + shift.y,
            provisional.global_frame.origin.z + shift.z,
        ),
        PositionVector3D(
            provisional.global_frame.origin.x
            + shift.x
            + longitudinal.x * float(adapter.member_length),
            provisional.global_frame.origin.y
            + shift.y
            + longitudinal.y * float(adapter.member_length),
            provisional.global_frame.origin.z
            + shift.z
            + longitudinal.z * float(adapter.member_length),
        ),
        local_z,
        SectionDatumOffset(
            float(adapter.section_datum_offset_y),
            float(adapter.section_datum_offset_z),
        ),
    )


def _brace_inclination_axes(
    template_up: UnitVector3D,
    zero_longitudinal: UnitVector3D,
    inclination_degrees: Decimal,
) -> tuple[UnitVector3D, UnitVector3D]:
    """Rotate the established in-plane Tee brace basis using the R5 authority."""

    if inclination_degrees == 0:
        return zero_longitudinal, template_up
    sine_decimal, cosine_decimal = _brace_inclination_coefficients(inclination_degrees)
    sine = float(sine_decimal)
    cosine = float(cosine_decimal)
    longitudinal = UnitVector3D(
        cosine * zero_longitudinal.x + sine * template_up.x,
        cosine * zero_longitudinal.y + sine * template_up.y,
        cosine * zero_longitudinal.z + sine * template_up.z,
    )
    in_plane_up = UnitVector3D(
        cosine * template_up.x - sine * zero_longitudinal.x,
        cosine * template_up.y - sine * zero_longitudinal.y,
        cosine * template_up.z - sine * zero_longitudinal.z,
    )
    return longitudinal, in_plane_up


def _brace_inclination_coefficients(
    inclination_degrees: Decimal,
) -> tuple[Decimal, Decimal]:
    """Adapt the shared R5 binary result to the exact controlled R9 semantic basis."""

    if inclination_degrees == 0:
        return Decimal(0), Decimal(1)
    sine, cosine = deterministic_sine_cosine_degrees(inclination_degrees)
    if inclination_degrees in {Decimal(30), Decimal(-30)}:
        return (
            Decimal("0.5") if inclination_degrees > 0 else Decimal("-0.5"),
            Decimal("0.8660254037844386"),
        )
    if inclination_degrees in {Decimal(90), Decimal(-90)}:
        return (Decimal(1) if inclination_degrees > 0 else Decimal(-1), Decimal(0))
    return decimal_from_finite_real(sine), decimal_from_finite_real(cosine)


def _position(
    longitudinal: UnitVector3D,
    transverse: UnitVector3D,
    normal: UnitVector3D,
    longitudinal_coordinate: float,
    transverse_coordinate: float,
    normal_coordinate: float,
) -> PositionVector3D:
    return PositionVector3D(
        longitudinal.x * longitudinal_coordinate
        + transverse.x * transverse_coordinate
        + normal.x * normal_coordinate,
        longitudinal.y * longitudinal_coordinate
        + transverse.y * transverse_coordinate
        + normal.y * normal_coordinate,
        longitudinal.z * longitudinal_coordinate
        + transverse.z * transverse_coordinate
        + normal.z * normal_coordinate,
    )


def _shift_position(
    point: PositionVector3D,
    dx: float,
    dy: float,
    dz: float,
) -> PositionVector3D:
    return PositionVector3D(point.x + dx, point.y + dy, point.z + dz)


def _owner_profile_frame(
    placed: PlacedComponentGeometry3D,
    profile: MemberProfile,
) -> CartesianFrame3D:
    """Recover the oriented exact-profile frame from the unrotated kernel adapter frame."""

    effective = placed.global_frame
    effective_y = effective.y_axis
    effective_z = effective.z_axis
    owner_y, owner_z = (
        (effective_y, effective_z),
        (
            UnitVector3D(-effective_z.x, -effective_z.y, -effective_z.z),
            effective_y,
        ),
        (
            UnitVector3D(-effective_y.x, -effective_y.y, -effective_y.z),
            UnitVector3D(-effective_z.x, -effective_z.y, -effective_z.z),
        ),
        (
            effective_z,
            UnitVector3D(-effective_y.x, -effective_y.y, -effective_y.z),
        ),
    )[profile.orientation.quarter_turns]
    center = effective.local_to_parent_point(PositionVector3D(placed.extent.length / 2.0, 0.0, 0.0))
    return CartesianFrame3D(center, effective.x_axis, owner_y, owner_z)


def _same_planar_region(
    first: PlanarRectangularSurface3D,
    second: PlanarRectangularSurface3D,
    tolerance: float = 1e-9,
) -> bool:
    def contains(
        owner: PlanarRectangularSurface3D,
        point: PositionVector3D,
    ) -> bool:
        local = owner.frame.parent_to_local_point(point)
        return (
            abs(local.x) <= tolerance
            and abs(local.y) <= owner.extent_y / 2.0 + tolerance
            and abs(local.z) <= owner.extent_z / 2.0 + tolerance
        )

    return all(contains(first, point) for point in second.corners) and all(
        contains(second, point) for point in first.corners
    )


def _profile_contact_patch(
    placed: PlacedComponentGeometry3D,
    profile: MemberProfile,
    selected: ProfileSurfaceDefinition,
    kernel_patch: SurfacePatch3D,
) -> SurfacePatch3D:
    """Adapt exact full owner contact bounds without widening any penetrated element."""

    owner = _owner_profile_frame(placed, profile)
    center = selected.contact_bounds.center
    global_center = owner.local_to_parent_point(
        PositionVector3D(_float(center.x), _float(center.y), _float(center.z))
    )
    local_normal = selected.local_outward_normal
    normal = owner.local_to_parent_vector(
        Vector3D(
            _float(local_normal.x),
            _float(local_normal.y),
            _float(local_normal.z),
        )
    ).normalized()
    longitudinal = owner.x_axis
    tangent = normal.cross(longitudinal).normalized()
    transverse_extent = (
        selected.contact_bounds.max_z - selected.contact_bounds.min_z
        if selected.plane_axis is PrincipalAxisFamily.Y
        else selected.contact_bounds.max_y - selected.contact_bounds.min_y
    )
    geometry = PlanarRectangularSurface3D(
        CartesianFrame3D(global_center, normal, longitudinal, tangent),
        _float(selected.contact_bounds.max_x - selected.contact_bounds.min_x),
        _float(transverse_extent),
    )
    kernel_geometry = cast(PlanarRectangularSurface3D, kernel_patch.geometry)
    if _same_planar_region(geometry, kernel_geometry):
        return kernel_patch
    return SurfacePatch3D(
        f"PROFILE_CONTACT:{selected.surface_id.value}",
        f"Exact owner contact surface {selected.surface_id.value}",
        kernel_patch.participant,
        kernel_patch.source,
        kernel_patch.exposure,
        kernel_patch.disposition,
        kernel_patch.role,
        geometry,
    )


def _place_connected_profile(
    member: AssemblyMember,
    profile: MemberProfile,
    topology: SectionTopology,
    connector: TeeConnectorDimensions,
    longitudinal: UnitVector3D,
    transverse: UnitVector3D,
    normal: UnitVector3D,
    placement_translation: Vector3D | None = None,
    contact_anchor: PositionVector3D | None = None,
) -> tuple[PlacedComponentGeometry3D, SurfacePatch3D, SurfacePatch3D]:
    adapter = profile_section_geometry_adapter(profile)
    start = _position(
        longitudinal,
        transverse,
        normal,
        0.0,
        0.0,
        _float(connector.flange_thickness),
    )
    end = _position(
        longitudinal,
        transverse,
        normal,
        0.0,
        0.0,
        _float(connector.flange_thickness + adapter.member_length),
    )
    cross_section = _profile_cross_section(profile, topology)
    local_z = _effective_profile_local_z(
        profile,
        longitudinal,
        transverse,
        normal,
    )
    section_offset = SectionDatumOffset(
        _float(adapter.section_datum_offset_y),
        _float(adapter.section_datum_offset_z),
    )
    provisional = place_member(
        member,
        cross_section,
        start,
        end,
        local_z,
        section_offset,
    )
    selected = require_direct_tee_profile_surface(profile)
    provisional_set = create_component_surface_set(provisional)
    selected_patch_id = (
        kernel_profile_surface_patch_ids(profile)[0]
        if profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION
        else selected.outside_patch_id
    )
    provisional_patch = _surface(provisional_set.patches, member.id, selected_patch_id)
    provisional_contact = _profile_contact_patch(
        provisional,
        profile,
        selected,
        provisional_patch,
    )
    provisional_geometry = cast(PlanarRectangularSurface3D, provisional_contact.geometry)
    target = _position(
        longitudinal,
        transverse,
        normal,
        0.0,
        _float(connector.stem_thickness) / 2.0,
        _float(connector.flange_thickness + adapter.member_length / Decimal(2)),
    )
    translation = placement_translation or Vector3D(0.0, 0.0, 0.0)
    dx = target.x - provisional_geometry.center.x + translation.x
    dy = target.y - provisional_geometry.center.y + translation.y
    dz = target.z - provisional_geometry.center.z + translation.z
    placed = place_member(
        member,
        cross_section,
        _shift_position(start, dx, dy, dz),
        _shift_position(end, dx, dy, dz),
        local_z,
        section_offset,
    )
    final_set = create_component_surface_set(placed)
    selected_patch = _surface(final_set.patches, member.id, selected_patch_id)
    contact_patch = _profile_contact_patch(
        placed,
        profile,
        selected,
        selected_patch,
    )
    if contact_anchor is not None:
        contact_geometry = cast(PlanarRectangularSurface3D, contact_patch.geometry)
        local_anchor = contact_geometry.frame.parent_to_local_point(contact_anchor)
        cross_shift = Vector3D(
            contact_geometry.frame.z_axis.x * local_anchor.z,
            contact_geometry.frame.z_axis.y * local_anchor.z,
            contact_geometry.frame.z_axis.z * local_anchor.z,
        )
        placed = place_member(
            member,
            cross_section,
            _shift_position(
                start,
                dx + cross_shift.x,
                dy + cross_shift.y,
                dz + cross_shift.z,
            ),
            _shift_position(
                end,
                dx + cross_shift.x,
                dy + cross_shift.y,
                dz + cross_shift.z,
            ),
            local_z,
            section_offset,
        )
        final_set = create_component_surface_set(placed)
        selected_patch = _surface(final_set.patches, member.id, selected_patch_id)
        contact_patch = _profile_contact_patch(
            placed,
            profile,
            selected,
            selected_patch,
        )
    selected_geometry = cast(PlanarRectangularSurface3D, selected_patch.geometry)
    if selected_geometry.normal.dot(transverse) > -1.0 + 1e-12:
        raise ValueError("Selected connected-member surface does not face the Tee stem.")
    return placed, selected_patch, contact_patch


def _surface(
    surfaces: tuple[SurfacePatch3D, ...],
    participant_id: str,
    patch_id: str,
) -> SurfacePatch3D:
    matches = tuple(
        item
        for item in surfaces
        if item.participant.entity_id == participant_id and item.id == patch_id
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one surface {participant_id}:{patch_id}; found {len(matches)}.")
    return matches[0]


def _interface_geometry(
    interface: ConnectionInterface,
    first_patch: SurfacePatch3D,
    second_patch: SurfacePatch3D,
    first_zone_id: str,
    second_zone_id: str,
    origin: PositionVector3D,
    row_axis: UnitVector3D,
    tolerance: GeometryComparisonTolerance,
    surfaces: tuple[SurfacePatch3D, ...],
    first_penetration_patch: SurfacePatch3D | None = None,
) -> ResolvedConnectionInterfaceGeometry:
    first_geometry = cast(PlanarRectangularSurface3D, first_patch.geometry)
    local = first_geometry.frame.parent_to_local_point(origin)
    first_zone = ConnectionZoneSpecification(
        first_zone_id,
        f"{interface.label} first contact zone",
        first_patch.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    first_zones: tuple[ConnectionZoneSpecification, ...] = (first_zone,)
    if (
        first_penetration_patch is not None
        and first_penetration_patch.reference != first_patch.reference
    ):
        first_zones = (
            first_zone,
            ConnectionZoneSpecification(
                _ZONE_A_BRACE_PENETRATION,
                f"{interface.label} penetrable physical-element zone",
                first_penetration_patch.reference,
                ConnectionZoneKind.WHOLE_PATCH,
            ),
        )
    second_zone = ConnectionZoneSpecification(
        second_zone_id,
        f"{interface.label} second contact zone",
        second_patch.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )
    return resolve_connection_interface_geometry(
        ConnectionInterfaceGeometrySpecification(
            interface,
            InterfaceTargetSideSpecification(interface.participant_a, first_zones, first_zone.id),
            InterfaceTargetSideSpecification(
                interface.participant_b, (second_zone,), second_zone.id
            ),
            InterfaceOriginSpecification(first_zone.id, local.y, local.z),
            row_axis,
            tolerance,
        ),
        surfaces,
    )


def _layer(
    layer_id: str,
    participant: ParticipantReference,
    element_id: str,
    entry: SurfacePatch3D,
    exit_surface: SurfacePatch3D,
    interface_id: str,
    side: InterfaceTargetSide,
    zone_id: str,
    hole_diameter: float,
) -> IntendedPenetratedLayer:
    return IntendedPenetratedLayer(
        layer_id,
        participant,
        element_id,
        entry.reference,
        exit_surface.reference,
        (InterfaceZoneReference(interface_id, side, zone_id),),
        hole_diameter,
    )


def _bolt_group_frame(
    interface: ResolvedConnectionInterfaceGeometry,
    origin_y: float,
    in_plane_reference: UnitVector3D,
    tolerance: GeometryComparisonTolerance,
    origin_z: float = 0.0,
) -> CartesianFrame3D:
    axis_x = interface.interface_frame.x_axis
    reference = in_plane_reference - axis_x * in_plane_reference.dot(axis_x)
    if reference.norm <= tolerance.angular_tolerance:
        raise ValueError("Bolt-group in-plane reference is parallel to the interface normal.")
    axis_y = reference.normalized()
    axis_z = axis_x.cross(axis_y).normalized()
    axis_y = axis_z.cross(axis_x).normalized()
    return CartesianFrame3D(
        interface.interface_frame.local_to_parent_point(PositionVector3D(0.0, origin_y, origin_z)),
        axis_x,
        axis_y,
        axis_z,
    )


def _opposing_patch_for_location(
    location: BoltLocation,
    frame: CartesianFrame3D,
    candidates: tuple[SurfacePatch3D, ...],
    hole_radius: float,
    tolerance: GeometryComparisonTolerance,
) -> SurfacePatch3D:
    axis_point = frame.local_to_parent_point(location.position)
    matches: list[SurfacePatch3D] = []
    for candidate in candidates:
        geometry = cast(PlanarRectangularSurface3D, candidate.geometry)
        alignment = frame.x_axis.dot(geometry.normal)
        if 1.0 + alignment > tolerance.angular_tolerance:
            continue
        denominator = alignment
        delta = Vector3D(
            geometry.center.x - axis_point.x,
            geometry.center.y - axis_point.y,
            geometry.center.z - axis_point.z,
        )
        parameter = delta.dot(geometry.normal) / denominator
        intersection = _shift_position(
            axis_point,
            frame.x_axis.x * parameter,
            frame.x_axis.y * parameter,
            frame.x_axis.z * parameter,
        )
        local = geometry.frame.parent_to_local_point(intersection)
        clearance = min(
            geometry.extent_y / 2.0 - abs(local.y),
            geometry.extent_z / 2.0 - abs(local.z),
        )
        if clearance + tolerance.distance_tolerance >= hole_radius:
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError(
            "Each connected-profile bolt path must select one finite opposing broad face."
        )
    return matches[0]


def _angle_opposing_patch_for_location(
    location: BoltLocation,
    frame: CartesianFrame3D,
    profile: MemberProfile,
    placed_profile: PlacedComponentGeometry3D,
    contact: SurfacePatch3D,
    candidates: tuple[SurfacePatch3D, ...],
    hole_radius: float,
    tolerance: GeometryComparisonTolerance,
    allow_dimensional_kernel_roundoff: bool = False,
) -> SurfacePatch3D:
    """Bind one Angle bolt center to its exact owner-derived opposing leg boundary."""

    exact_point = _owner_point_on_contact(
        location,
        frame,
        profile,
        placed_profile,
        contact,
        tolerance,
    )
    resolution = resolve_angle_leg_bolt_path(profile, exact_point)
    if not resolution.valid or resolution.opposing_patch_id is None:
        raise ValueError(
            "Each connected-profile bolt path must select one finite opposing broad face."
        )
    owner_candidates = tuple(
        candidate for candidate in candidates if candidate.id == resolution.opposing_patch_id
    )
    if len(owner_candidates) != 1:
        raise ValueError(
            "Each connected-profile bolt path must select one finite opposing broad face."
        )
    opposing = _opposing_patch_for_location(
        location,
        frame,
        owner_candidates,
        hole_radius,
        tolerance,
    )
    contact_geometry = cast(PlanarRectangularSurface3D, contact.geometry)
    opposing_geometry = cast(PlanarRectangularSurface3D, opposing.geometry)
    separation = abs(
        Vector3D(
            opposing_geometry.center.x - contact_geometry.center.x,
            opposing_geometry.center.y - contact_geometry.center.y,
            opposing_geometry.center.z - contact_geometry.center.z,
        ).dot(frame.x_axis)
    )
    exact_separation = decimal_from_finite_real(separation)
    thickness_mismatch = resolution.penetrated_thickness is None or (
        abs(exact_separation - resolution.penetrated_thickness)
        > Decimal(str(tolerance.distance_tolerance))
        if allow_dimensional_kernel_roundoff
        else exact_separation != resolution.penetrated_thickness
    )
    if thickness_mismatch:
        raise ValueError("Angle leg path thickness must equal the exact profile leg thickness.")
    return opposing


def _owner_point_on_contact(
    location: BoltLocation,
    frame: CartesianFrame3D,
    profile: MemberProfile,
    placed_profile: PlacedComponentGeometry3D,
    contact: SurfacePatch3D,
    tolerance: GeometryComparisonTolerance,
) -> ExactProfileVector3D:
    """Project a Tee-fixed bolt axis onto the actual inclined profile contact face."""

    axis_point = frame.local_to_parent_point(location.position)
    contact_geometry = cast(PlanarRectangularSurface3D, contact.geometry)
    alignment = frame.x_axis.dot(contact_geometry.normal)
    if abs(alignment) <= tolerance.angular_tolerance:
        raise ValueError("Angle bolt axis must intersect the selected contact face.")
    delta = Vector3D(
        contact_geometry.center.x - axis_point.x,
        contact_geometry.center.y - axis_point.y,
        contact_geometry.center.z - axis_point.z,
    )
    parameter = delta.dot(contact_geometry.normal) / alignment
    contact_point = _shift_position(
        axis_point,
        frame.x_axis.x * parameter,
        frame.x_axis.y * parameter,
        frame.x_axis.z * parameter,
    )
    owner_point = _owner_profile_frame(placed_profile, profile).parent_to_local_point(contact_point)
    return ExactProfileVector3D(
        decimal_from_finite_real(owner_point.x),
        decimal_from_finite_real(owner_point.y),
        decimal_from_finite_real(owner_point.z),
    )


_EXACT_PROFILE_WALL_FAMILIES = frozenset(
    {
        MemberProfileFamily.CHANNEL,
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
    }
)


def _exact_profile_wall_outer_point(
    surface: ProfileSurfaceDefinition,
    connector: TeeConnectorDimensions,
    layout: TeeBoltLayout,
    row_index: int,
    line_index: int,
) -> ExactProfileVector3D:
    """Map one exact Tee layout index into the selected owner-profile surface frame."""

    two = Decimal(2)
    line_coordinate = -layout.line_span / two + Decimal(line_index) * layout.gauge
    row_coordinate = (
        -connector.connector_length / two
        + layout.unloaded_end_distance
        + Decimal(row_index) * layout.pitch
    )
    normal = surface.local_outward_normal
    center = surface.center
    profile_half_length = (surface.contact_bounds.max_x - surface.contact_bounds.min_x) / two
    return ExactProfileVector3D(
        center.x + connector.stem_depth / two - profile_half_length - line_coordinate,
        center.y + row_coordinate * normal.z,
        center.z - row_coordinate * normal.y,
    )


def _profile_wall_opposing_patch_for_location(
    location: BoltLocation,
    frame: CartesianFrame3D,
    profile: MemberProfile,
    exact_outer_point: ExactProfileVector3D,
    candidates: tuple[SurfacePatch3D, ...],
    hole_radius: float,
    exact_hole_radius: Decimal,
    tolerance: GeometryComparisonTolerance,
) -> SurfacePatch3D:
    """Bind one non-Angle wall footprint to its exact owner-derived opposing boundary."""

    resolution = resolve_profile_wall_bolt_path(profile, exact_outer_point, exact_hole_radius)
    if not resolution.valid or resolution.opposing_patch_id is None:
        raise ValueError(
            "Each connected-profile bolt path must select one finite opposing broad face."
        )
    owner_candidates = tuple(
        candidate for candidate in candidates if candidate.id == resolution.opposing_patch_id
    )
    if len(owner_candidates) != 1:
        raise ValueError(
            "Each connected-profile bolt path must select one finite opposing broad face."
        )
    surface = require_direct_tee_profile_surface(profile)
    if resolution.penetrated_thickness != surface.layer_thickness:
        raise ValueError(
            "Profile wall path thickness must equal the exact physical wall thickness."
        )
    return _opposing_patch_for_location(
        location,
        frame,
        owner_candidates,
        hole_radius,
        tolerance,
    )


def _interface_a_paths(
    group: BoltGroup,
    interface: ResolvedConnectionInterfaceGeometry,
    profile: MemberProfile,
    placed_profile: PlacedComponentGeometry3D,
    connector: TeeConnectorDimensions,
    layout: TeeBoltLayout,
    brace_ref: ParticipantReference,
    tee_ref: ParticipantReference,
    profile_surface_id: str,
    profile_opposing_ids: tuple[str, ...],
    physical_element_id: str,
    stem_positive: SurfacePatch3D,
    stem_negative: SurfacePatch3D,
    surfaces: tuple[SurfacePatch3D, ...],
    longitudinal: UnitVector3D,
    unloaded_end_distance: float,
    horizontal_origin: float,
    hole_diameter: float,
    exact_hole_radius: Decimal,
    tolerance: GeometryComparisonTolerance,
    brace_zone_id: str,
    rhs_full_through: bool,
    allow_dimensional_kernel_roundoff: bool = False,
) -> tuple[BoltPathDefinition, ...]:
    contact = _surface(surfaces, _BRACE_ID, profile_surface_id)
    candidates = tuple(_surface(surfaces, _BRACE_ID, patch_id) for patch_id in profile_opposing_ids)
    frame = _bolt_group_frame(
        interface,
        unloaded_end_distance,
        longitudinal,
        tolerance,
        horizontal_origin,
    )
    paths: list[BoltPathDefinition] = []
    for index, location in enumerate(group.locations):
        row_index, line_index = divmod(index, layout.bolts_per_row)
        suffix = "" if location.id == _BASE_A_ID else f":{location.id}"
        profile_layers: tuple[IntendedPenetratedLayer, ...] = ()
        if not (
            rhs_full_through and profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
        ):
            opposing = (
                candidates[0]
                if profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION
                else _angle_opposing_patch_for_location(
                    location,
                    frame,
                    profile,
                    placed_profile,
                    contact,
                    candidates,
                    hole_diameter / 2.0,
                    tolerance,
                    allow_dimensional_kernel_roundoff,
                )
                if profile.family is MemberProfileFamily.ANGLE
                else (
                    _profile_wall_opposing_patch_for_location(
                        location,
                        frame,
                        profile,
                        (
                            _exact_profile_wall_outer_point(
                                require_direct_tee_profile_surface(profile),
                                connector,
                                layout,
                                row_index,
                                line_index,
                            )
                            if abs(placed_profile.global_frame.x_axis.dot(longitudinal))
                            >= 1.0 - tolerance.angular_tolerance
                            else _owner_point_on_contact(
                                location,
                                frame,
                                profile,
                                placed_profile,
                                contact,
                                tolerance,
                            )
                        ),
                        candidates,
                        hole_diameter / 2.0,
                        exact_hole_radius,
                        tolerance,
                    )
                    if profile.family in _EXACT_PROFILE_WALL_FAMILIES
                    else _opposing_patch_for_location(
                        location,
                        frame,
                        candidates,
                        hole_diameter / 2.0,
                        tolerance,
                    )
                )
            )
            profile_layers = (
                _layer(
                    f"tee-interface-a-brace-layer{suffix}",
                    brace_ref,
                    physical_element_id,
                    opposing,
                    contact,
                    interface.interface.id,
                    InterfaceTargetSide.FIRST,
                    brace_zone_id,
                    hole_diameter,
                ),
            )
        paths.append(
            BoltPathDefinition(
                location.id,
                (
                    *profile_layers,
                    _layer(
                        f"tee-interface-a-stem-layer{suffix}",
                        tee_ref,
                        "STEM",
                        stem_positive,
                        stem_negative,
                        interface.interface.id,
                        InterfaceTargetSide.SECOND,
                        _ZONE_A_STEM,
                        hole_diameter,
                    ),
                ),
            )
        )
    return tuple(paths)


def _source(
    *,
    kind: EngineeringPropertySourceKind,
    source_id: str,
    revision: str,
    approval: str,
) -> EngineeringPropertySource:
    return EngineeringPropertySource(
        kind,
        source_id,
        revision,
        PropertySourceConfirmation.ENGINEER_APPROVED,
        ("STAGE_3_2_AUTHORITY_LEDGER_RC1",),
        False,
        approval_authority_id=approval,
    )


def _material_architecture(
    tee: ConnectorComponent,
    assembly: JointAssembly,
    support_surface_id: str,
    available_surface_ids: tuple[str, ...],
    fastener_snapshot: FastenerSnapshot,
) -> tuple[ConnectionAssemblyScaffold, TeeMaterialAuthorityTrace]:
    frp_source = _source(
        kind=EngineeringPropertySourceKind.CONTROLLED_PROJECT_DATA,
        source_id="ICE_LOCKED_PULTRUDED_FRP",
        revision="RC2",
        approval="STAGE_2_1B_ACCEPTED",
    )
    fastener_source = _source(
        kind=EngineeringPropertySourceKind.STANDARD_OR_GRADE_DATA,
        source_id="ASTM_F593_17_GROUP_2_316_316L",
        revision="2017",
        approval="STAGE_2_1B_ACCEPTED",
    )
    connector_assignment = ConnectorComponentEngineeringAssignment(
        tee,
        ConnectorMaterialAssignment(
            "tee-frp-material-assignment",
            tee.id,
            ConnectorMaterialFamily.PULTRUDED_FRP,
            MaterialBehaviorFamily.DIRECTIONAL_FRP,
            frp_source,
            EngineeringCoverageClass.QUALIFICATION_REQUIRED,
        ),
        ConnectorComponentRole.PRIMARY_CONNECTOR,
        EngineeringGeometryReference("tee-physical-geometry", frp_source, True),
        ResistanceAuthority(
            "tee-body-no-automatic-resistance",
            ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            False,
        ),
        frp_source,
    )
    fastener_system = FastenerSystem(
        "tee-f593-316-fastener-system",
        FastenerMaterialAssignment(
            "tee-f593-316-material-assignment",
            FastenerMaterialFamily.STAINLESS_STEEL_316,
            MaterialBehaviorFamily.ISOTROPIC_METAL,
            fastener_source,
            EngineeringCoverageClass.PRESCRIPTIVE,
        ),
        EngineeringGeometryReference("tee-bolt-geometry", fastener_source, True),
        ResistanceAuthority(
            "tee-existing-metallic-bolt-authority",
            ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY,
            True,
            fastener_source,
        ),
        fastener_snapshot.id,
        fastener_source,
    )
    eligibility = resolve_existing_metallic_bolt_eligibility(fastener_system, fastener_snapshot)
    scaffold = ConnectionAssemblyScaffold(
        "tee-connection-assembly-scaffold",
        assembly.id,
        _BRACE_ID,
        ParticipantReference(ParticipantKind.MEMBER, _SUPPORT_ID),
        (support_surface_id,),
        (connector_assignment,),
        (
            TeeInterfaceIdentity.BRACE_TO_STEM.value,
            TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value,
        ),
        (_GROUP_A_ID, _GROUP_B_ID),
        (fastener_system,),
        (
            BoltGroupFastenerSystemAssignment(_GROUP_A_ID, fastener_system.system_id),
            BoltGroupFastenerSystemAssignment(_GROUP_B_ID, fastener_system.system_id),
        ),
    )
    bind_connection_assembly_scaffold(
        scaffold,
        assembly,
        available_support_surface_ids=available_surface_ids,
    )
    return scaffold, TeeMaterialAuthorityTrace(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        FastenerMaterialFamily.STAINLESS_STEEL_316,
        fastener_snapshot.id,
        eligibility,
    )


def _layer_assignment(
    path_layer: ResolvedPenetratedLayer,
    material: MaterialPropertySnapshot,
) -> PenetratedLayerMaterialAssignment:
    return PenetratedLayerMaterialAssignment(
        path_layer.definition.participant.entity_id,
        path_layer.definition.physical_element_id,
        path_layer.physical_element.source_material_region.id,
        material,
        ThreadStatus.EXCLUDED,
        PultrudedElementForm.SHAPE_ELEMENT,
        False,
    )


def _single_bolt_request(
    context: JointGeometryContext,
    interface_id: str,
    group_id: str,
    bolt_id: str,
    bolt_diameter: PhysicalQuantity,
    hole_basis: PublishedCodeUnitBasis,
    fastener_snapshot: FastenerSnapshot,
) -> SingleBoltOrchestrationRequest:
    group = next(item for item in context.resolved_bolt_groups if item.bolt_group.id == group_id)
    path = next(item for item in group.paths if item.definition.bolt_location_id == bolt_id)
    material = create_locked_ice_material_snapshot()
    snapshot = replace(
        fastener_snapshot,
        shear_plane_thread_statuses=(
            ThreadStatusAssignment(f"{group_id}:shear-plane-1", ThreadStatus.EXCLUDED),
        ),
        bearing_layer_thread_statuses=tuple(
            ThreadStatusAssignment(item.definition.id, ThreadStatus.EXCLUDED)
            for item in path.layers
        ),
        number_of_shear_planes=1,
    )
    return SingleBoltOrchestrationRequest(
        f"{group_id}:physical-base",
        context.assembly,
        context,
        interface_id,
        group_id,
        bolt_id,
        _LOAD_ID,
        tuple(_layer_assignment(item, material) for item in path.layers),
        snapshot,
        bolt_diameter,
        hole_basis,
        select_time_effect_factor(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        EndUseFactors(
            Decimal(1),
            Decimal(1),
            Decimal(1),
            "ASCE/SEI 74-23 Section 2.4.4",
            ("STAGE_3_2_CONTROLLED_UNITY_END_USE_FACTORS",),
        ),
        LapConfiguration.SINGLE_LAP,
        None,
        _ACTION_ID,
        False,
    )


def _multirow_request(
    request: TeeConnectorOrchestrationRequest,
    interface_id: str,
    layout: TeeBoltLayout,
    physical: SingleBoltOrchestrationRequest,
    layer_specs: tuple[tuple[str, str, Decimal, PultrudedElementClassification], ...],
) -> MultiRowOrchestrationRequest:
    unit = request.source_length_unit
    pair = resolve_legacy_material_pair(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        ConnectorMaterialFamily.PULTRUDED_FRP,
    )
    if pair.legacy_pair is not ConnectedMaterialPair.FRP_FRP:
        raise RuntimeError("The exact FRP/FRP legacy mapping changed unexpectedly.")
    factors = EndUseFactors(
        Decimal(1),
        Decimal(1),
        Decimal(1),
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_3_2_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:{interface_id}",
        f"{_ASSEMBLY_ID}:{interface_id}",
        interface_id,
        _LOAD_ID,
        "Stage 3.2 canonical member-end force and physical reference point",
        request.unit_system,
        unit,
        layout.row_count,
        layout.bolts_per_row,
        request.bolt_diameter,
        request.hole_basis,
        _quantity(layout.pitch, unit),
        _quantity(layout.gauge, unit),
        _quantity(layout.unloaded_end_distance, unit),
        _quantity(layout.loaded_end_distance, unit),
        _quantity(layout.negative_side_distance, unit),
        _quantity(layout.positive_side_distance, unit),
        _quantity(Decimal("0.000000001"), unit),
        pair.legacy_pair,
        tuple(
            MultiRowLayerInput(
                layer_id,
                component_id,
                "ICE_LOCKED_PULTRUDED_FRP",
                _quantity(thickness, unit),
                classification,
                Decimal(0),
                factors,
                ThreadStatus.EXCLUDED,
            )
            for layer_id, component_id, thickness, classification in layer_specs
        ),
        None,
        None,
        None,
        RowDistributionBasis.ASCE_PRESCRIBED,
        None,
        (),
        MethodProvenance(
            "CANONICAL_STAGE_3_2_MEMBER_END_FORCE",
            "STAGE_3_2_TEE_CONNECTOR_ENGINEERING_SPECIFICATION_RC1",
            "RC1",
            _LOAD_ID,
            "EXPLICIT_GLOBAL_REFERENCE_POINT",
            True,
            True,
        ),
        False,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.SINGLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        None,
        _quantity(Decimal(0), unit),
        _quantity(Decimal("0.000000001"), unit),
        physical_connection_request=physical,
        demand_source=MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE,
        automatic_action_source_id=_ACTION_ID,
        single_row_geometry_preview_authorized=layout.row_count == 1,
    )


def _effective_layout(
    layout: TeeBoltLayout,
    vertical_extent: Decimal,
    horizontal_extent: Decimal,
) -> tuple[TeeBoltLayout, Decimal, Decimal]:
    """Normalize either placement contract to exact edge distances and offsets."""

    two = Decimal(2)
    if layout.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED:
        vertical_offset = (
            layout.unloaded_end_distance + layout.row_span / two - vertical_extent / two
        )
        horizontal_offset = (
            layout.negative_side_distance + layout.line_span / two - horizontal_extent / two
        )
        return layout, vertical_offset, horizontal_offset
    if layout.vertical_offset is None or layout.horizontal_offset is None:
        raise RuntimeError("Validated group-offset placement lost its exact offsets.")
    unloaded = vertical_extent / two + layout.vertical_offset - layout.row_span / two
    loaded = vertical_extent / two - layout.vertical_offset - layout.row_span / two
    negative = horizontal_extent / two + layout.horizontal_offset - layout.line_span / two
    positive = horizontal_extent / two - layout.horizontal_offset - layout.line_span / two
    return (
        TeeBoltLayout(
            row_count=layout.row_count,
            bolts_per_row=layout.bolts_per_row,
            pitch=layout.pitch,
            gauge=layout.gauge,
            unloaded_end_distance=unloaded,
            loaded_end_distance=loaded,
            negative_side_distance=negative,
            positive_side_distance=positive,
        ),
        layout.vertical_offset,
        layout.horizontal_offset,
    )


def _group_location_coordinates(
    layout: TeeBoltLayout,
) -> tuple[tuple[str, Decimal, Decimal], ...]:
    """Return exact row/line coordinates in the group frame without float authority."""

    row_origin = Decimal(0)
    line_origin = -layout.line_span / Decimal(2)
    return tuple(
        (
            f"r{row + 1}-l{line + 1}",
            row_origin + Decimal(row) * layout.pitch,
            line_origin + Decimal(line) * layout.gauge,
        )
        for row in range(layout.row_count)
        for line in range(layout.bolts_per_row)
    )


def _physical_geometry_fingerprint(
    interface_id: str,
    layout: TeeBoltLayout,
    vertical_offset: Decimal,
    horizontal_offset: Decimal,
) -> str:
    """Fingerprint exact datum-relative physical centers, independent of input mode."""

    two = Decimal(2)
    centers = tuple(
        (
            row_id,
            vertical_offset - layout.row_span / two + Decimal(row) * layout.pitch,
            horizontal_offset - layout.line_span / two + Decimal(line) * layout.gauge,
            Decimal(0),
        )
        for row in range(layout.row_count)
        for line in range(layout.bolts_per_row)
        for row_id in (f"R{row + 1}:L{line + 1}",)
    )
    return _fingerprint((interface_id, "TEE_FIXED_HVN", centers))


def _clearance_trace(
    *,
    interface_id: str,
    requested_layout: TeeBoltLayout,
    effective_layout: TeeBoltLayout,
    vertical_extent: Decimal,
    vertical_negative_end: Decimal,
    vertical_positive_end: Decimal,
    horizontal_extent: Decimal,
    vertical_offset: Decimal,
    horizontal_offset: Decimal,
    hole_radius: Decimal,
    unit: Unit,
    profile: MemberProfile | None = None,
) -> TeeHoleClearanceTrace:
    """Resolve exact complete-hole clearances from canonical Decimal geometry."""

    two = Decimal(2)
    group_negative = vertical_offset - effective_layout.row_span / two
    group_positive = vertical_offset + effective_layout.row_span / two
    values: dict[str, Decimal] = {
        "VERTICAL_NEGATIVE": (group_negative - vertical_negative_end - hole_radius),
        "VERTICAL_POSITIVE": (vertical_positive_end - group_positive - hole_radius),
        "HORIZONTAL_NEGATIVE": (
            horizontal_extent / two
            + horizontal_offset
            - effective_layout.line_span / two
            - hole_radius
        ),
        "HORIZONTAL_POSITIVE": (
            horizontal_extent / two
            - horizontal_offset
            - effective_layout.line_span / two
            - hole_radius
        ),
    }
    tee_end_values = {
        "TEE_NEGATIVE_L_END": values["VERTICAL_NEGATIVE"],
        "TEE_POSITIVE_L_END": values["VERTICAL_POSITIVE"],
    }
    minimum_containment: Decimal | None = None
    # The R7 Angle leg's finite opposing broad face removes the heel-side half
    # gauge from the usable row direction.  Keep this exact domain boundary
    # visible rather than relying on a binary-float patch-intersection failure.
    if (
        interface_id == TeeInterfaceIdentity.BRACE_TO_STEM.value
        and profile is not None
        and profile.family is MemberProfileFamily.ANGLE
        and isinstance(profile.dimensions, AngleProfileDimensions)
        and profile.dimensions.member_length == Decimal(8)
        and profile.dimensions.leg_y == Decimal(6)
        and profile.dimensions.leg_z == Decimal(6)
        and profile.dimensions.thickness == Decimal("0.5")
        and profile.selected_surface
        in {MemberProfileSurfaceId.LEG_Y_OUTER, MemberProfileSurfaceId.LEG_Z_OUTER}
    ):
        heel_exclusion = effective_layout.line_span / Decimal(2)
        angle_clearance = effective_layout.unloaded_end_distance - heel_exclusion - hole_radius
        values["VERTICAL_NEGATIVE"] = min(values["VERTICAL_NEGATIVE"], angle_clearance)
        minimum_containment = heel_exclusion + hole_radius
    governing_boundary, minimum = min(values.items(), key=lambda item: (item[1], item[0]))
    if governing_boundary.startswith("VERTICAL"):
        row = 1 if governing_boundary.endswith("NEGATIVE") else requested_layout.row_count
        line = 1
    else:
        row = 1
        line = 1 if governing_boundary.endswith("NEGATIVE") else requested_layout.bolts_per_row
    prefix = "A" if interface_id == TeeInterfaceIdentity.BRACE_TO_STEM.value else "B"
    governing_bolt = f"{prefix}_B_R{row}_L{line}"
    governing_tee_end, minimum_tee_end = min(
        tee_end_values.items(), key=lambda item: (item[1], item[0])
    )
    governing_tee_row = (
        1 if governing_tee_end == "TEE_NEGATIVE_L_END" else requested_layout.row_count
    )
    governing_tee_bolt = f"{prefix}_B_R{governing_tee_row}_L1"

    def quantity(value: Decimal) -> PhysicalQuantity:
        return _quantity(value, unit)

    return TeeHoleClearanceTrace(
        vertical_positive=quantity(values["VERTICAL_POSITIVE"]),
        vertical_negative=quantity(values["VERTICAL_NEGATIVE"]),
        horizontal_positive=quantity(values["HORIZONTAL_POSITIVE"]),
        horizontal_negative=quantity(values["HORIZONTAL_NEGATIVE"]),
        minimum=quantity(minimum),
        governing_bolt_id=governing_bolt,
        governing_boundary_id=f"{interface_id}:{governing_boundary}",
        exact_deficit=quantity(-minimum) if minimum < 0 else None,
        geometry_valid=minimum >= 0,
        minimum_complete_hole_containment=(
            None if minimum_containment is None else quantity(minimum_containment)
        ),
        tee_positive_end_coordinate=quantity(vertical_positive_end),
        tee_negative_end_coordinate=quantity(vertical_negative_end),
        tee_positive_end_complete_hole_clearance=quantity(tee_end_values["TEE_POSITIVE_L_END"]),
        tee_negative_end_complete_hole_clearance=quantity(tee_end_values["TEE_NEGATIVE_L_END"]),
        governing_tee_end_id=governing_tee_end,
        governing_tee_end_bolt_id=governing_tee_bolt,
        minimum_tee_end_complete_hole_clearance=quantity(minimum_tee_end),
    )


def _invalid_clearance_message(trace: TeeHoleClearanceTrace) -> str:
    clearance = trace.minimum
    unit = clearance.unit.value
    text = (
        "Each connected-profile bolt path must select one finite opposing broad face. "
        f"Complete-hole clearance {canonical_decimal_string(clearance.magnitude)} {unit}; "
        f"governing boundary {trace.governing_boundary_id}; "
        f"governing bolt {trace.governing_bolt_id}."
    )
    if trace.minimum_complete_hole_containment is not None:
        limit = trace.minimum_complete_hole_containment
        text += (
            " Minimum for complete-hole containment: "
            f"{canonical_decimal_string(limit.magnitude)} {limit.unit.value}."
        )
    return text


def _placement_trace(
    *,
    interface_id: str,
    interface: ResolvedConnectionInterfaceGeometry,
    requested_layout: TeeBoltLayout,
    effective_layout: TeeBoltLayout,
    vertical_extent: Decimal,
    vertical_negative_end: Decimal,
    vertical_positive_end: Decimal,
    horizontal_extent: Decimal,
    vertical_offset: Decimal,
    horizontal_offset: Decimal,
    hole_radius: Decimal,
    unit: Unit,
    profile: MemberProfile | None = None,
) -> TeeInterfacePlacementTrace:
    datum = interface.interface_frame.local_to_parent_point(
        PositionVector3D(0.0, _float(vertical_extent / Decimal(2)), 0.0)
    )
    clearances = _clearance_trace(
        interface_id=interface_id,
        requested_layout=requested_layout,
        effective_layout=effective_layout,
        vertical_extent=vertical_extent,
        vertical_negative_end=vertical_negative_end,
        vertical_positive_end=vertical_positive_end,
        horizontal_extent=horizontal_extent,
        vertical_offset=vertical_offset,
        horizontal_offset=horizontal_offset,
        hole_radius=hole_radius,
        unit=unit,
        profile=profile,
    )
    return TeeInterfacePlacementTrace(
        datum_id=(
            "TEE_STEM_CENTER_DATUM_A"
            if interface_id == TeeInterfaceIdentity.BRACE_TO_STEM.value
            else "TEE_FLANGE_CENTER_DATUM_B"
        ),
        datum_point=datum,
        vertical_axis=interface.interface_frame.y_axis,
        horizontal_axis=interface.interface_frame.z_axis,
        normal_axis=interface.interface_frame.x_axis,
        placement_mode=requested_layout.placement_mode,
        vertical_offset=PhysicalQuantity.of(vertical_offset, unit),
        horizontal_offset=PhysicalQuantity.of(horizontal_offset, unit),
        equivalent_edge_distances=effective_layout,
        clearances=clearances,
        physical_geometry_fingerprint=_physical_geometry_fingerprint(
            interface_id, effective_layout, vertical_offset, horizontal_offset
        ),
        method_compatibility=TeeFixedGridCompatibilityStatus.COMPATIBLE,
        bolt_centers_hvn=tuple(
            ExactProfileVector3D(
                horizontal_offset
                - effective_layout.line_span / Decimal(2)
                + Decimal(line) * effective_layout.gauge,
                vertical_offset
                - effective_layout.row_span / Decimal(2)
                + Decimal(row) * effective_layout.pitch,
                Decimal(0),
            )
            for row in range(effective_layout.row_count)
            for line in range(effective_layout.bolts_per_row)
        ),
    )


def _fixed_grid_method_compatibility(
    request: TeeConnectorOrchestrationRequest,
    group_frame: CartesianFrame3D,
) -> TeeFixedGridCompatibilityStatus:
    """Use the accepted row method only when force has no bolt-line component."""

    unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    components = tuple(
        item.to(unit).magnitude
        for item in (request.global_force.x, request.global_force.y, request.global_force.z)
    )
    line_axis = tuple(
        decimal_from_finite_real(item)
        for item in (group_frame.z_axis.x, group_frame.z_axis.y, group_frame.z_axis.z)
    )
    line_component = sum(
        (component * axis for component, axis in zip(components, line_axis, strict=True)),
        Decimal(0),
    )
    if line_component == 0:
        return TeeFixedGridCompatibilityStatus.COMPATIBLE
    return TeeFixedGridCompatibilityStatus.ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN


def tee_fixed_grid_geometry_preview(
    request: MultiRowOrchestrationRequest,
    invalid_actual_preview: MultiRowPreviewResult,
) -> MultiRowPreviewResult:
    """Recover physical geometry without pretending an incompatible demand is supported."""

    force_unit = (
        Unit.KIP if request.display_unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    )
    geometry_request = replace(
        request,
        signed_force_x=PhysicalQuantity.of(Decimal(1), force_unit),
        signed_force_y=PhysicalQuantity.of(Decimal(0), force_unit),
        force_reference="R10_FIXED_GRID_GEOMETRY_ONLY_NO_DESIGN_DEMAND",
        demand_source=MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND,
        automatic_action_source_id=None,
    )
    geometry_preview = preview_multirow_connection(geometry_request)
    if geometry_preview.visualization is None:
        return invalid_actual_preview
    zero = PhysicalQuantity.of(Decimal(0), force_unit)
    visualization = replace(
        geometry_preview.visualization,
        demand_components=(zero, zero),
        force_reference="R10_FIXED_GRID_GEOMETRY_ONLY_NO_DESIGN_DEMAND",
        automatic_bolt_demands=(),
    )
    fingerprint = hashlib.sha256(
        (
            f"{invalid_actual_preview.preview_fingerprint}:"
            "ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN"
        ).encode("ascii")
    ).hexdigest()
    return replace(
        geometry_preview,
        geometry_status=GeometryStatus.VALID,
        plan_availability=PlanAvailability.CALCULATION_NOT_SUPPORTED,
        warnings=tuple(
            dict.fromkeys(
                (
                    *geometry_preview.warnings,
                    "ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN",
                )
            )
        ),
        preview_fingerprint=fingerprint,
        design_check_ready=False,
        visualization=visualization,
        demand_source=MultiRowDemandSource.AUTOMATIC_MEMBER_END_FORCE,
        automatic_demand_result=None,
    )


_TEE_CLEARANCE_REFERENCE_PLANE_ID = "TEE_FLANGE_INNER_CLEARANCE_PLANE"
_CONNECTED_MEMBER_CUT_PLANE_ID = "CONNECTED_MEMBER_END_CUT_PLANE"


def _offset_along(
    point: PositionVector3D,
    normal: UnitVector3D,
    distance: float,
) -> PositionVector3D:
    return PositionVector3D(
        point.x + normal.x * distance,
        point.y + normal.y * distance,
        point.z + normal.z * distance,
    )


def _member_end_trim(
    request: TeeConnectorOrchestrationRequest,
    placed_brace: PlacedComponentGeometry3D,
    placed_tee: PlacedComponentGeometry3D,
    normal: UnitVector3D,
    longitudinal: UnitVector3D,
    transverse: UnitVector3D,
    group_a_resolved: ResolvedBoltGroupGeometry,
    exact_hole_radius: Decimal,
    profile_surface: ProfileSurfaceDefinition,
) -> tuple[TeeMemberEndTrimTrace, TrimmedComponentSolids3D | None]:
    """Resolve the Tee-frame obstruction plane and optional fabrication cut."""

    unit = request.source_length_unit
    reference_origin = _position(
        longitudinal,
        transverse,
        normal,
        0.0,
        0.0,
        _float(request.connector_dimensions.flange_thickness),
    )
    reference_plane = AuthoritativeCutPlane3D(
        _TEE_CLEARANCE_REFERENCE_PLANE_ID,
        reference_origin,
        normal,
    )
    tee_flange = next(
        item for item in placed_tee.physical_elements if item.source_element.id == "FLANGE"
    )
    interfering = tuple(
        physical.source_element.id
        for physical in placed_brace.physical_elements
        if placed_rectangular_elements_overlap(physical, tee_flange)
    )
    if not request.connected_member_end_trim_enabled:
        return (
            TeeMemberEndTrimTrace(
                enabled=False,
                normalized_clearance=None,
                reference_plane_id=reference_plane.id,
                reference_plane_origin=reference_plane.origin,
                reference_plane_normal=reference_plane.normal,
                cut_plane_id=None,
                cut_plane_origin=None,
                cut_plane_normal=None,
                measured_plane_clearance=None,
                interference_status=(
                    TeeMemberEndInterferenceStatus.INTERFERENCE_DETECTED
                    if interfering
                    else TeeMemberEndInterferenceStatus.CLEAR
                ),
                interfering_physical_element_ids=interfering,
                trimmed_member_geometry_identity=None,
                fabricated_trim_edge_ids=(),
                bolt_clearances=(),
                governing_bolt_id=None,
                governing_trim_edge_id=None,
                minimum_hole_edge_clearance=None,
                exact_deficit=None,
                recovery_guidance=None,
                geometry_valid=not interfering,
            ),
            None,
        )
    clearance = cast(PhysicalQuantity, request.connected_member_end_clearance).to(unit)
    cut_origin = _offset_along(reference_origin, normal, _float(clearance.magnitude))
    cut_plane = AuthoritativeCutPlane3D(
        _CONNECTED_MEMBER_CUT_PLANE_ID,
        cut_origin,
        normal,
    )
    axial_projection = placed_brace.global_frame.x_axis.dot(cut_plane.normal)
    if axial_projection <= 1e-9:
        raise ValueError("The connected member direction must cross the Tee fabrication cut plane.")
    start_points = tuple(
        physical.global_frame.local_to_parent_point(
            PositionVector3D(
                prism.extent.x_start,
                y,
                z,
            )
        )
        for physical in placed_brace.physical_elements
        for prism in physical.extrusions
        if isinstance(prism, LocalRectangularPrism3D)
        for y in (prism.rectangle.min_y, prism.rectangle.max_y)
        for z in (prism.rectangle.min_z, prism.rectangle.max_z)
    )
    source_extension = max(
        0.0,
        max(signed_distance_to_plane(point, cut_plane) for point in start_points) / axial_projection
        + 1e-9,
    )
    remote = _offset_along(
        placed_brace.global_frame.origin,
        placed_brace.global_frame.x_axis,
        placed_brace.extent.length,
    )
    source_start = _offset_along(
        placed_brace.global_frame.origin,
        placed_brace.global_frame.x_axis,
        -source_extension,
    )
    trim_source = place_member(
        cast(AssemblyMember, placed_brace.component),
        placed_brace.cross_section,
        source_start,
        remote,
        placed_brace.global_frame.z_axis,
        placed_brace.section_offset,
    )
    trimmed = trim_placed_rectangular_component(trim_source, cut_plane)
    selected_edge_ids = tuple(
        edge_id
        for edge_id in trimmed.fabricated_face_ids
        if edge_id.startswith(f"{profile_surface.physical_element_id}:")
    )
    governing_edge_id = (
        selected_edge_ids[0] if selected_edge_ids else trimmed.fabricated_face_ids[0]
    )
    bolt_clearances = tuple(
        TeeTrimBoltClearanceTrace(
            center.bolt_location.id,
            _quantity(
                decimal_from_finite_real(
                    signed_distance_to_plane(center.global_position, cut_plane)
                ),
                unit,
            ),
            _quantity(
                decimal_from_finite_real(
                    signed_distance_to_plane(center.global_position, cut_plane)
                )
                - exact_hole_radius,
                unit,
            ),
            governing_edge_id,
        )
        for center in group_a_resolved.master_centers
    )
    governing = min(
        bolt_clearances,
        key=lambda item: (item.hole_edge_to_trim_edge.magnitude, item.bolt_id),
    )
    minimum = governing.hole_edge_to_trim_edge
    deficit = _quantity(-minimum.magnitude, unit) if minimum.magnitude < 0 else None
    guidance = (
        None
        if deficit is None
        else (
            "Move the bolt group away from the fabricated end by at least "
            f"{canonical_decimal_string(deficit.magnitude)} {unit.value}."
        )
    )
    # Validate the result independently of the clipping assumption. A nonnegative
    # clearance should keep every fabricated solid on or beyond the Tee flange-inner
    # plane; any retained point behind that plane is a fail-closed geometry defect.
    remaining_interference = any(
        signed_distance_to_plane(point, reference_plane) < -1e-9
        for solid in trimmed.solids
        for point in solid.vertices
    )
    geometry_valid = not remaining_interference and deficit is None
    return (
        TeeMemberEndTrimTrace(
            enabled=True,
            normalized_clearance=clearance,
            reference_plane_id=reference_plane.id,
            reference_plane_origin=reference_plane.origin,
            reference_plane_normal=reference_plane.normal,
            cut_plane_id=cut_plane.id,
            cut_plane_origin=cut_plane.origin,
            cut_plane_normal=cut_plane.normal,
            measured_plane_clearance=clearance,
            interference_status=(
                TeeMemberEndInterferenceStatus.REMAINING_INTERFERENCE
                if remaining_interference
                else TeeMemberEndInterferenceStatus.TRIMMED_CLEAR
            ),
            interfering_physical_element_ids=(),
            trimmed_member_geometry_identity=trimmed.geometry_fingerprint,
            fabricated_trim_edge_ids=trimmed.fabricated_face_ids,
            bolt_clearances=bolt_clearances,
            governing_bolt_id=governing.bolt_id,
            governing_trim_edge_id=governing.trim_edge_id,
            minimum_hole_edge_clearance=minimum,
            exact_deficit=deficit,
            recovery_guidance=guidance,
            geometry_valid=geometry_valid,
        ),
        trimmed,
    )


def resolve_tee_connector_request(
    request: TeeConnectorOrchestrationRequest,
    *,
    connected_member_vertical_offset: Decimal = Decimal(0),
    connected_member_group_anchor_h: Decimal | None = None,
    connected_member_node_roundoff_tolerance: bool = False,
) -> _TeeResolvedAssembly:
    """Build and validate the one canonical Tee object graph for either support role."""

    if not isinstance(request, TeeConnectorOrchestrationRequest):
        raise TypeError("request must be a TeeConnectorOrchestrationRequest.")
    if (
        not isinstance(connected_member_vertical_offset, Decimal)
        or not connected_member_vertical_offset.is_finite()
    ):
        raise ValueError("connected_member_vertical_offset must be a finite Decimal.")
    if connected_member_group_anchor_h is not None and (
        not isinstance(connected_member_group_anchor_h, Decimal)
        or not connected_member_group_anchor_h.is_finite()
    ):
        raise ValueError("connected_member_group_anchor_h must be a finite Decimal when supplied.")
    if not isinstance(connected_member_node_roundoff_tolerance, bool):
        raise TypeError("connected_member_node_roundoff_tolerance must be Boolean.")
    unit = request.source_length_unit
    connector = request.connector_dimensions
    anchor_position, body_center, positive_end, negative_end = _tee_longitudinal_coordinates(
        request
    )
    support = request.support_dimensions
    connected_profile = request.connected_member_profile
    support_target_id, support_profile = _tee_support_selection(request)
    profile_surface = require_direct_tee_profile_surface(connected_profile)
    effective_support_role = (
        TeeSupportRole.BEAM
        if support_target_id is SharedSupportTargetId.W_BEAM_FLANGE
        else TeeSupportRole.COLUMN
    )
    effective_flange = (
        request.selected_support_flange
        if support_target_id
        in {SharedSupportTargetId.W_COLUMN_FLANGE, SharedSupportTargetId.W_BEAM_FLANGE}
        else SelectedSupportFlange.POSITIVE_LOCAL_Z
    )
    longitudinal, transverse, normal, selected_sign = _unit_axes(
        effective_support_role, effective_flange
    )
    brace_longitudinal, brace_up = _brace_inclination_axes(
        longitudinal,
        normal,
        request.brace_inclination_degrees,
    )
    brace_sine, brace_cosine = _brace_inclination_coefficients(request.brace_inclination_degrees)
    tee_local_z = UnitVector3D(-normal.x, -normal.y, -normal.z)
    effective_a, vertical_offset_a, horizontal_offset_a = _effective_layout(
        request.interface_a_layout,
        connector.connector_length,
        connector.stem_depth,
    )
    effective_b, vertical_offset_b, horizontal_offset_b = _effective_layout(
        request.interface_b_layout,
        connector.connector_length,
        connector.flange_width,
    )

    brace_topology = _oriented_topology(connected_profile.section_family)
    support_topology = _oriented_topology(support_profile.section_family)
    tee_topology = _oriented_topology(SectionFamily.TEE)
    brace = AssemblyMember(
        _BRACE_ID,
        f"Pultruded FRP connected brace {connected_profile.family.value}",
        MemberRole.BRACE,
        MemberEnd.START,
        connected_profile.section_family,
        ComponentMaterialKind.PULTRUDED_FRP,
        cast(FRPComponentOrientation, connected_profile.material_orientation),
        brace_topology,
    )
    support_member = AssemblyMember(
        _SUPPORT_ID,
        (
            "Pultruded FRP W column"
            if support_target_id is SharedSupportTargetId.W_COLUMN_FLANGE
            else (
                "Pultruded FRP W beam"
                if support_target_id is SharedSupportTargetId.W_BEAM_FLANGE
                else (
                    f"Pultruded FRP {support_profile.role.value.lower()} "
                    f"{support_profile.family.value}"
                )
            )
        ),
        support_profile.role,
        MemberEnd.START,
        support_profile.section_family,
        ComponentMaterialKind.PULTRUDED_FRP,
        cast(FRPComponentOrientation, support_profile.material_orientation),
        support_topology,
    )
    tee = ConnectorComponent(
        _TEE_ID,
        "Pultruded FRP Tee connector",
        ConnectorComponentKind.TEE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, _TEE_ID),
            PrincipalAxisFamily.X,
        ),
        tee_topology,
    )
    brace_ref = ParticipantReference(ParticipantKind.MEMBER, brace.id)
    support_ref = ParticipantReference(ParticipantKind.MEMBER, support_member.id)
    tee_ref = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, tee.id)
    interface_a = ConnectionInterface(
        TeeInterfaceIdentity.BRACE_TO_STEM.value,
        "Interface A - brace to Tee stem",
        brace_ref,
        tee_ref,
        TransferIntent.SHEAR_ONLY,
    )
    interface_b = ConnectionInterface(
        TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value,
        "Interface B - Tee flange to support flange",
        tee_ref,
        support_ref,
        TransferIntent.SHEAR_ONLY,
    )
    group_a_locations = tuple(
        BoltLocation(
            (_BASE_A_ID if row == 0 and line == 0 else f"tee-bolt-a-r{row + 1}-l{line + 1}"),
            PositionVector3D(0.0, _float(row_coordinate), _float(line_coordinate)),
        )
        for index, (_, row_coordinate, line_coordinate) in enumerate(
            _group_location_coordinates(request.interface_a_layout)
        )
        for row, line in (divmod(index, request.interface_a_layout.bolts_per_row),)
    )
    group_a = BoltGroup(
        _GROUP_A_ID,
        "Interface A bolt group",
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, _GROUP_A_ID),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, _GROUP_A_ID),
        (interface_a.id,),
        group_a_locations,
    )
    group_b = BoltGroup(
        _GROUP_B_ID,
        "Interface B bolt group",
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, _GROUP_B_ID),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, _GROUP_B_ID),
        (interface_b.id,),
        (
            BoltLocation(
                _BASE_B_ID,
                PositionVector3D(
                    0.0,
                    0.0,
                    _float(-request.interface_b_layout.line_span / Decimal(2)),
                ),
            ),
        ),
    )
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    force = tuple(
        float(item.to(force_unit).magnitude)
        for item in (request.global_force.x, request.global_force.y, request.global_force.z)
    )
    moment = tuple(
        float(item.to(moment_unit).magnitude)
        for item in (request.global_moment.x, request.global_moment.y, request.global_moment.z)
    )
    reference = tuple(
        float(item.to(unit).magnitude)
        for item in (
            request.global_reference_point.x,
            request.global_reference_point.y,
            request.global_reference_point.z,
        )
    )
    load = LoadCombination(_LOAD_ID, "Stage 3.2 factored action", LoadInputBasis.FACTORED_STRENGTH)
    action = ManualMemberEndAction(
        _ACTION_ID,
        brace.id,
        MemberEnd.START,
        load.id,
        CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
        ReferencePoint(ReferencePointKind.JOINT_ORIGIN, _ASSEMBLY_ID),
        ForceVector3D(*force),
        MomentVector3D(*moment),
        ActionConvention.MEMBER_ON_JOINT,
    )
    assembly = JointAssembly(
        _ASSEMBLY_ID,
        "Reusable two-interface FRP Tee connection",
        ConnectionDesignCategory.SHEAR,
        request.unit_system,
        (brace, support_member),
        (tee,),
        (),
        (interface_a, interface_b),
        (group_a, group_b),
        (load,),
        (action,),
    )
    assembly.require_valid()

    if support_target_id in {
        SharedSupportTargetId.W_COLUMN_FLANGE,
        SharedSupportTargetId.W_BEAM_FLANGE,
    }:
        support_length = _float(support.member_length)
        support_start = _position(longitudinal, transverse, normal, -support_length / 2.0, 0.0, 0.0)
        support_end = _position(longitudinal, transverse, normal, support_length / 2.0, 0.0, 0.0)
        placed_support = place_member(
            support_member,
            _profile_cross_section(support_profile, support_topology),
            support_start,
            support_end,
            Vector3D(
                normal.x * selected_sign,
                normal.y * selected_sign,
                normal.z * selected_sign,
            ),
            SectionDatumOffset(0.0, -selected_sign * _float(support.overall_depth) / 2.0),
        )
    else:
        placed_support = _place_shared_support_profile(
            support_profile,
            support_member,
            support_topology,
            longitudinal,
            transverse,
            normal,
        )
    overall = _float(connector.overall_depth)
    tee_frame = CartesianFrame3D(
        _position(longitudinal, transverse, normal, 0.0, 0.0, overall / 2.0),
        longitudinal,
        transverse,
        tee_local_z,
    )
    placed_tee = place_connector(
        tee,
        create_tee_geometry(
            tee_topology,
            TeeDimensions(
                overall,
                _float(connector.flange_width),
                _float(connector.stem_thickness),
                _float(connector.flange_thickness),
            ),
        ),
        tee_frame,
        LongitudinalExtent(
            _float(negative_end),
            _float(positive_end),
        ),
        SectionDatumOffset(0.0, 0.0),
    )
    tee_longitudinal_placement = TeeLongitudinalPlacementTrace(
        tee_longitudinal_datum_id=_TEE_LONGITUDINAL_DATUM_ID,
        datum_point=tee_frame.origin,
        longitudinal_axis=longitudinal,
        connector_length_anchor=request.connector_length_anchor,
        connector_length_anchor_position=_quantity(anchor_position, unit),
        body_center_coordinate=_quantity(body_center, unit),
        positive_end_coordinate=_quantity(positive_end, unit),
        negative_end_coordinate=_quantity(negative_end, unit),
        body_geometry_fingerprint=_fingerprint(
            (
                "TEE_BODY_PHYSICAL_GEOMETRY",
                connector,
                tee_frame,
                negative_end,
                positive_end,
            )
        ),
    )
    placed_brace, selected_brace_patch, profile_contact_patch = _place_connected_profile(
        brace,
        connected_profile,
        brace_topology,
        connector,
        brace_up,
        transverse,
        brace_longitudinal,
        Vector3D(
            longitudinal.x * _float(connected_member_vertical_offset),
            longitudinal.y * _float(connected_member_vertical_offset),
            longitudinal.z * _float(connected_member_vertical_offset),
        ),
        (
            None
            if connected_member_group_anchor_h is None
            else _position(
                longitudinal,
                transverse,
                normal,
                _float(connected_member_vertical_offset),
                _float(connector.stem_thickness / Decimal(2)),
                _float(connector.flange_thickness + connected_member_group_anchor_h),
            )
        ),
    )
    kernel_brace_surfaces = _normalize_srs_broad_faces(
        connected_profile,
        create_component_surface_set(placed_brace),
    )
    brace_surfaces = (
        kernel_brace_surfaces
        if profile_contact_patch.reference == selected_brace_patch.reference
        else ComponentSurfaceSet3D(
            kernel_brace_surfaces.participant,
            kernel_brace_surfaces.placed_component,
            tuple(
                sorted(
                    (*kernel_brace_surfaces.patches, profile_contact_patch),
                    key=lambda patch: patch.id,
                )
            ),
        )
    )
    support_surface_set = _normalize_srs_broad_faces(
        support_profile,
        create_component_surface_set(placed_support),
    )
    surface_sets = (
        brace_surfaces,
        support_surface_set,
        create_component_surface_set(placed_tee),
    )
    surfaces = tuple(item for surface_set in surface_sets for item in surface_set.patches)
    support_surface = require_direct_tee_profile_surface(support_profile)
    support_outside_id, support_opposing_ids, support_element = kernel_profile_surface_patch_ids(
        support_profile
    )
    support_outer = _surface(surfaces, _SUPPORT_ID, support_outside_id)
    if support_target_id in {
        SharedSupportTargetId.W_COLUMN_FLANGE,
        SharedSupportTargetId.W_BEAM_FLANGE,
    }:
        support_inner_strip = (
            "INNER_POSITIVE_CW_STRIP" if selected_sign > 0 else "INNER_NEGATIVE_CW_STRIP"
        )
        support_inner = _surface(
            surfaces,
            _SUPPORT_ID,
            f"{support_element}:{support_inner_strip}",
        )
    else:
        support_opposing = tuple(
            _surface(surfaces, _SUPPORT_ID, item) for item in support_opposing_ids
        )
        if not support_opposing:  # pragma: no cover - shared target registry contract
            raise ValueError("The support selected surface requires an opposing physical face.")
        support_inner = support_opposing[0]
    if connected_profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        profile_outside_id, profile_opposing_ids, profile_element_id = (
            kernel_profile_surface_patch_ids(connected_profile)
        )
    else:
        profile_outside_id = profile_surface.outside_patch_id
        profile_opposing_ids = profile_surface.opposing_patch_ids
        profile_element_id = profile_surface.physical_element_id
    brace_penetration_surface = _surface(
        surfaces,
        _BRACE_ID,
        profile_outside_id,
    )
    if brace_penetration_surface.reference != selected_brace_patch.reference:
        raise RuntimeError("Connected-profile selected patch identity changed during assembly.")
    stem_positive = _surface(surfaces, _TEE_ID, "STEM:POSITIVE_TT_BROAD")
    stem_negative = _surface(surfaces, _TEE_ID, "STEM:NEGATIVE_TT_BROAD")
    tee_outer = _surface(surfaces, _TEE_ID, "FLANGE:OUTER_TT_BROAD")
    tee_inner = _surface(surfaces, _TEE_ID, "FLANGE:INNER_NEGATIVE_CW_STRIP")
    tolerance = GeometryComparisonTolerance(
        _float(Decimal("0.000000001")), _float(Decimal("0.000000001"))
    )
    origin_a = _position(
        longitudinal,
        transverse,
        normal,
        -_float(connector.connector_length) / 2.0,
        _float(connector.stem_thickness) / 2.0,
        _float(connector.flange_thickness + connector.stem_depth / Decimal(2)),
    )
    origin_b = _position(
        longitudinal,
        transverse,
        normal,
        -_float(connector.connector_length) / 2.0,
        0.0,
        0.0,
    )
    resolved_a = _interface_geometry(
        interface_a,
        profile_contact_patch,
        stem_positive,
        _ZONE_A_BRACE,
        _ZONE_A_STEM,
        origin_a,
        longitudinal,
        tolerance,
        surfaces,
        brace_penetration_surface,
    )
    fixed_a_x = resolved_a.interface_frame.x_axis
    fixed_a_y = (longitudinal - fixed_a_x * longitudinal.dot(fixed_a_x)).normalized()
    fixed_a_z = fixed_a_x.cross(fixed_a_y).normalized()
    fixed_a_y = fixed_a_z.cross(fixed_a_x).normalized()
    resolved_a = replace(
        resolved_a,
        interface_frame=CartesianFrame3D(
            origin_a,
            fixed_a_x,
            fixed_a_y,
            fixed_a_z,
        ),
    )
    resolved_b = _interface_geometry(
        interface_b,
        tee_outer,
        support_outer,
        _ZONE_B_TEE,
        _ZONE_B_SUPPORT,
        origin_b,
        longitudinal,
        tolerance,
        surfaces,
    )
    basis = JointGeometryBasis(
        assembly,
        CartesianFrame3D(
            PositionVector3D(*reference),
            longitudinal,
            transverse,
            tee_local_z,
        ),
        (placed_brace, placed_support),
        (placed_tee,),
        surface_sets,
        (),
        (resolved_a, resolved_b),
    )
    hole = create_standard_hole(request.bolt_diameter, request.hole_basis)
    exact_hole_diameter = hole.hole_diameter.to(unit).magnitude
    hole_diameter = float(exact_hole_diameter)
    origin_y_a = effective_a.unloaded_end_distance
    origin_z_a = (
        Decimal(0)
        if request.interface_a_layout.placement_mode
        is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
        else horizontal_offset_a
    )
    origin_y_b = effective_b.unloaded_end_distance
    origin_z_b = (
        Decimal(0)
        if request.interface_b_layout.placement_mode
        is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
        else horizontal_offset_b
    )
    placement_a = _placement_trace(
        interface_id=TeeInterfaceIdentity.BRACE_TO_STEM.value,
        interface=resolved_a,
        requested_layout=request.interface_a_layout,
        effective_layout=effective_a,
        vertical_extent=connector.connector_length,
        vertical_negative_end=negative_end,
        vertical_positive_end=positive_end,
        horizontal_extent=connector.stem_depth,
        vertical_offset=vertical_offset_a,
        horizontal_offset=horizontal_offset_a,
        hole_radius=exact_hole_diameter / Decimal(2),
        unit=unit,
        profile=connected_profile,
    )
    placement_b = _placement_trace(
        interface_id=TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value,
        interface=resolved_b,
        requested_layout=request.interface_b_layout,
        effective_layout=effective_b,
        vertical_extent=connector.connector_length,
        vertical_negative_end=negative_end,
        vertical_positive_end=positive_end,
        horizontal_extent=connector.flange_width,
        vertical_offset=vertical_offset_b,
        horizontal_offset=horizontal_offset_b,
        hole_radius=exact_hole_diameter / Decimal(2),
        unit=unit,
    )
    if not placement_a.clearances.geometry_valid:
        raise ValueError(_invalid_clearance_message(placement_a.clearances))
    if not placement_b.clearances.geometry_valid:
        raise ValueError(_invalid_clearance_message(placement_b.clearances))
    group_a_resolved = resolve_bolt_group_geometry(
        basis,
        BoltGroupGeometrySpecification(
            group_a,
            interface_a.id,
            _float(origin_y_a),
            _float(origin_z_a),
            longitudinal,
            tolerance,
            _interface_a_paths(
                group_a,
                resolved_a,
                connected_profile,
                placed_brace,
                connector,
                effective_a,
                brace_ref,
                tee_ref,
                profile_outside_id,
                profile_opposing_ids,
                profile_element_id,
                stem_positive,
                stem_negative,
                surfaces,
                longitudinal,
                _float(origin_y_a),
                _float(origin_z_a),
                hole_diameter,
                exact_hole_diameter / Decimal(2),
                tolerance,
                (
                    _ZONE_A_BRACE
                    if profile_contact_patch.reference == brace_penetration_surface.reference
                    else _ZONE_A_BRACE_PENETRATION
                ),
                request.orchestration_contract_version == TEE_C2_ORCHESTRATION_CONTRACT_VERSION,
                connected_member_node_roundoff_tolerance,
            ),
        ),
    )
    group_b_resolved = resolve_bolt_group_geometry(
        basis,
        BoltGroupGeometrySpecification(
            group_b,
            interface_b.id,
            _float(origin_y_b),
            _float(origin_z_b),
            longitudinal,
            tolerance,
            (
                BoltPathDefinition(
                    _BASE_B_ID,
                    (
                        _layer(
                            "tee-interface-b-flange-layer",
                            tee_ref,
                            "FLANGE",
                            tee_inner,
                            tee_outer,
                            interface_b.id,
                            InterfaceTargetSide.FIRST,
                            _ZONE_B_TEE,
                            hole_diameter,
                        ),
                        _layer(
                            "tee-interface-b-support-layer",
                            support_ref,
                            support_element,
                            support_outer,
                            support_inner,
                            interface_b.id,
                            InterfaceTargetSide.SECOND,
                            _ZONE_B_SUPPORT,
                            hole_diameter,
                        ),
                    ),
                ),
            ),
        ),
    )
    rectangular_paths: list[IntegratedFullThroughBoltTrace] = []
    if connected_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        selected_connected_surface = cast(
            MemberProfileSurfaceId,
            connected_profile.selected_surface,
        )
        rectangular_paths.extend(
            build_integrated_full_through_bolt(
                connected_profile,
                placed_profile=placed_brace,
                selected_surface=selected_connected_surface,
                bolt_id=bolt_id,
                local_uv=_rectangular_local_uv(
                    connected_profile,
                    placed_brace,
                    point,
                ),
                hole_radius=exact_hole_diameter / Decimal(2),
                connector_identity="TEE_STEM",
                connector_thickness=connector.stem_thickness,
                connector_material_region_id="TEE_STEM_REGION",
                rectangular_material_region_id="CONNECTED_RECTANGULAR_PROFILE_REGION",
                source_length_unit=request.source_length_unit,
            )
            for bolt_id, point in _expanded_rectangular_bolt_points(
                group_a_resolved,
                request.interface_a_layout,
                "A",
            )
        )
    if support_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        selected_support_surface = cast(
            MemberProfileSurfaceId,
            support_profile.selected_surface,
        )
        rectangular_paths.extend(
            build_integrated_full_through_bolt(
                support_profile,
                placed_profile=placed_support,
                selected_surface=selected_support_surface,
                bolt_id=bolt_id,
                local_uv=_rectangular_local_uv(
                    support_profile,
                    placed_support,
                    point,
                ),
                hole_radius=exact_hole_diameter / Decimal(2),
                connector_identity="TEE_FLANGE",
                connector_thickness=connector.flange_thickness,
                connector_material_region_id="TEE_FLANGE_REGION",
                rectangular_material_region_id="SUPPORT_RECTANGULAR_PROFILE_REGION",
                source_length_unit=request.source_length_unit,
            )
            for bolt_id, point in _expanded_rectangular_bolt_points(
                group_b_resolved,
                request.interface_b_layout,
                "B",
            )
        )
    trim_trace, trimmed_connected_member_solids = _member_end_trim(
        request,
        placed_brace,
        placed_tee,
        normal,
        longitudinal,
        transverse,
        group_a_resolved,
        exact_hole_diameter / Decimal(2),
        profile_surface,
    )
    placement_a = replace(
        placement_a,
        method_compatibility=_fixed_grid_method_compatibility(
            request, group_a_resolved.bolt_group_frame
        ),
    )
    context = JointGeometryContext(basis, (group_a_resolved, group_b_resolved))
    fastener_snapshot = create_locked_f593_fastener_snapshot()
    scaffold, material_authority = _material_architecture(
        tee,
        assembly,
        support_outer.id,
        tuple(item.id for item in surfaces if item.participant.entity_id == _SUPPORT_ID),
        fastener_snapshot,
    )
    physical_a = _single_bolt_request(
        context,
        interface_a.id,
        group_a.id,
        _BASE_A_ID,
        request.bolt_diameter,
        request.hole_basis,
        fastener_snapshot,
    )
    physical_b = _single_bolt_request(
        context,
        interface_b.id,
        group_b.id,
        _BASE_B_ID,
        request.bolt_diameter,
        request.hole_basis,
        fastener_snapshot,
    )
    selected_profile_surface = cast(
        MemberProfileSurfaceId,
        connected_profile.selected_surface,
    )
    profile_trace = TeeConnectedMemberProfileTrace(
        profile_id=connected_profile.id,
        member_id=connected_profile.member_id,
        role=connected_profile.role,
        profile_family=connected_profile.family,
        size_basis=connected_profile.size_basis,
        dimensions=connected_profile.dimensions,
        profile_orientation=connected_profile.orientation,
        selected_profile_surface=selected_profile_surface,
        material_kind=connected_profile.material_kind,
        member_profile_fingerprint=member_profile_fingerprint(connected_profile),
        profile_geometry_fingerprint=profile_geometry_fingerprint(connected_profile),
        surface_patch_id=profile_contact_patch.id,
        physical_element_role=profile_surface.physical_element_role,
        brace_inclination_degrees=request.brace_inclination_degrees,
        brace_inclination_sine=brace_sine,
        brace_inclination_cosine=brace_cosine,
        brace_placement_frame=placed_brace.global_frame,
    )
    support_trace = TeeSupportProfileTrace(
        target_id=support_target_id,
        profile_id=support_profile.id,
        member_id=support_profile.member_id,
        role=support_profile.role,
        profile_family=support_profile.family,
        dimensions=support_profile.dimensions,
        profile_orientation=support_profile.orientation,
        selected_profile_surface=cast(
            MemberProfileSurfaceId,
            support_profile.selected_surface,
        ),
        surface_patch_id=support_outer.id,
        member_profile_fingerprint=member_profile_fingerprint(support_profile),
        profile_geometry_fingerprint=profile_geometry_fingerprint(support_profile),
    )
    multirow_a = _multirow_request(
        request,
        interface_a.id,
        effective_a,
        physical_a,
        (
            (
                "tee-interface-a-brace-layer",
                _BRACE_ID,
                profile_surface.layer_thickness,
                (
                    PultrudedElementClassification.PLATE
                    if connected_profile.family is MemberProfileFamily.FLAT_PLATE
                    else PultrudedElementClassification.SHAPE
                ),
            ),
            (
                "tee-interface-a-stem-layer",
                _TEE_ID,
                connector.stem_thickness,
                PultrudedElementClassification.SHAPE,
            ),
        ),
    )
    multirow_b = _multirow_request(
        request,
        interface_b.id,
        effective_b,
        physical_b,
        (
            (
                "tee-interface-b-flange-layer",
                _TEE_ID,
                connector.flange_thickness,
                PultrudedElementClassification.SHAPE,
            ),
            (
                "tee-interface-b-support-layer",
                _SUPPORT_ID,
                support_surface.layer_thickness,
                PultrudedElementClassification.SHAPE,
            ),
        ),
    )
    return _TeeResolvedAssembly(
        request=request,
        context=context,
        scaffold=scaffold,
        material_authority=material_authority,
        interface_a_request=multirow_a,
        interface_b_request=multirow_b,
        selected_support_surface_id=support_outer.id,
        connected_member_profile=profile_trace,
        connected_member_end_trim=trim_trace,
        tee_longitudinal_placement=tee_longitudinal_placement,
        trimmed_connected_member_solids=trimmed_connected_member_solids,
        interface_a_placement=placement_a,
        interface_b_placement=placement_b,
        support_target_id=support_target_id,
        support_profile=support_trace,
        rectangular_full_through_paths=tuple(rectangular_paths),
    )


def _translate(
    point: PositionVector3D,
    row_axis: UnitVector3D,
    line_axis: UnitVector3D,
    row: float,
    line: float,
) -> PositionVector3D:
    return PositionVector3D(
        point.x + row_axis.x * row + line_axis.x * line,
        point.y + row_axis.y * row + line_axis.y * line,
        point.z + row_axis.z * row + line_axis.z * line,
    )


def expand_tee_bolts(
    preview: SingleBoltPreviewResult,
    layout: TeeBoltLayout,
    interface_prefix: str,
) -> tuple[BoltDisplaySnapshot, ...]:
    base = preview.visualization
    if base is None:
        return ()
    frame = next(
        item.frame
        for item in base.frames
        if item.kind is CoordinateFrameKind.BOLT_GROUP_LOCAL and item.owner_id == base.bolt_group_id
    )
    bolts: list[BoltDisplaySnapshot] = []
    for row in range(layout.row_count):
        for line in range(layout.bolts_per_row):
            row_offset = float(Decimal(row) * layout.pitch)
            line_offset = float(Decimal(line) * layout.gauge)

            def moved(
                point: PositionVector3D,
                row_delta: float = row_offset,
                line_delta: float = line_offset,
            ) -> PositionVector3D:
                return _translate(point, frame.y_axis, frame.z_axis, row_delta, line_delta)

            bolt_id = f"{interface_prefix}_B_R{row + 1}_L{line + 1}"
            bolts.append(
                BoltDisplaySnapshot(
                    base.bolt.bolt_group_id,
                    bolt_id,
                    moved(base.bolt.center),
                    base.bolt.axis,
                    moved(base.bolt.stack_start),
                    moved(base.bolt.stack_end),
                    base.bolt.bolt_diameter,
                    tuple(
                        HoleDisplaySnapshot(
                            f"{bolt_id}:{item.id}",
                            item.participant_id,
                            item.physical_element_id,
                            moved(item.start),
                            moved(item.end),
                            item.diameter,
                        )
                        for item in base.bolt.holes
                    ),
                    tuple(
                        WasherDisplaySnapshot(
                            f"{bolt_id}:{item.id}",
                            item.location,
                            moved(item.start),
                            moved(item.end),
                            item.outside_diameter,
                        )
                        for item in base.bolt.washers
                    ),
                )
            )
    return tuple(bolts)


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "canonical": value.canonical_string,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, float):
        return canonical_decimal_string(decimal_from_finite_real(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PlanarFixedMaterialOrientation):
        return {
            "crosswise_axis": value.crosswise_axis.value,
            "through_thickness_axis": value.through_thickness_axis.value,
            **({"crosswise_sign": value.crosswise_sign} if value.crosswise_sign != 1 else {}),
            **(
                {"through_thickness_sign": value.through_thickness_sign}
                if value.through_thickness_sign != 1
                else {}
            ),
        }
    if is_dataclass(value):
        excluded = {"unit_system"}
        if isinstance(value, TeeConnectorOrchestrationRequest):
            excluded.update({"connector_length_anchor", "connector_length_anchor_position"})
            if value.support_target_id is None or value.support_target_id in {
                SharedSupportTargetId.W_COLUMN_FLANGE,
                SharedSupportTargetId.W_BEAM_FLANGE,
            }:
                excluded.update({"support_target_id", "support_profile"})
            if not value.connected_member_end_trim_enabled:
                excluded.update(
                    {
                        "connected_member_end_trim_enabled",
                        "connected_member_end_clearance",
                    }
                )
        if (
            isinstance(value, TeeBoltLayout)
            and value.placement_mode is TeeBoltPlacementMode.EDGE_DISTANCE_CONTROLLED
        ):
            excluded.update({"placement_mode", "vertical_offset", "horizontal_offset"})
        inclination = getattr(value, "brace_inclination_degrees", None)
        if inclination == 0:
            excluded.add("brace_inclination_degrees")
            if isinstance(value, TeeConnectedMemberProfileTrace):
                excluded.update(
                    {
                        "brace_inclination_sine",
                        "brace_inclination_cosine",
                        "brace_placement_frame",
                    }
                )
        return {
            field.name: _canonical(
                TEE_R2_ORCHESTRATION_CONTRACT_VERSION
                if isinstance(value, TeeConnectorOrchestrationRequest)
                and field.name == "orchestration_contract_version"
                and value.support_target_id
                in {
                    SharedSupportTargetId.W_COLUMN_FLANGE,
                    SharedSupportTargetId.W_BEAM_FLANGE,
                }
                else getattr(value, field.name)
            )
            for field in fields(value)
            if field.name not in excluded
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonical(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalized_length_fields(
    value: MemberProfileDimensions | TeeConnectorDimensions,
    unit: Unit,
) -> tuple[tuple[str, object], ...]:
    return tuple(
        (field.name, _quantity(cast(Decimal, getattr(value, field.name)), unit))
        for field in fields(value)
    )


def _normalized_profile_identity(profile: MemberProfile, unit: Unit) -> tuple[object, ...]:
    return (
        profile.id,
        profile.member_id,
        profile.role,
        profile.family,
        _normalized_length_fields(profile.dimensions, unit),
        profile.material_kind,
        profile.orientation,
        profile.selected_surface,
        profile.size_basis,
    )


def _normalized_layout_identity(layout: TeeBoltLayout, unit: Unit) -> tuple[object, ...]:
    return (
        layout.row_count,
        layout.bolts_per_row,
        layout.placement_mode,
        *(
            None if getattr(layout, name) is None else _quantity(getattr(layout, name), unit)
            for name in (
                "pitch",
                "gauge",
                "unloaded_end_distance",
                "loaded_end_distance",
                "negative_side_distance",
                "positive_side_distance",
                "vertical_offset",
                "horizontal_offset",
            )
        ),
    )


def _normalized_c2_request_identity(
    request: TeeConnectorOrchestrationRequest,
) -> tuple[object, ...]:
    support_profile = cast(MemberProfile, request.support_profile)
    return (
        TEE_C2_ORCHESTRATION_CONTRACT_VERSION,
        request.support_target_id,
        _normalized_profile_identity(support_profile, request.source_length_unit),
        _normalized_length_fields(request.connector_dimensions, request.source_length_unit),
        _normalized_profile_identity(request.connected_member_profile, request.source_length_unit),
        _normalized_layout_identity(request.interface_a_layout, request.source_length_unit),
        _normalized_layout_identity(request.interface_b_layout, request.source_length_unit),
        request.bolt_diameter,
        request.hole_basis,
        request.global_force,
        request.global_moment,
        request.global_reference_point,
        request.brace_inclination_degrees,
        request.connected_member_end_trim_enabled,
        request.connected_member_end_clearance,
        request.connector_length_anchor,
        request.connector_length_anchor_position,
    )


def _interface_fingerprint(
    resolved: _TeeResolvedAssembly,
    interface: TeeInterfaceIdentity,
) -> str:
    request = resolved.request
    common = (
        request.support_role,
        request.selected_support_flange,
        request.connector_dimensions,
        request.bolt_diameter,
        request.hole_basis,
        request.global_force,
        request.global_moment,
        request.global_reference_point,
        resolved.material_authority.connector_material_family,
        resolved.material_authority.fastener_material_family,
        resolved.material_authority.fastener_snapshot_id,
        *(
            (resolved.tee_longitudinal_placement.body_geometry_fingerprint,)
            if resolved.tee_longitudinal_placement.body_center_coordinate.magnitude != 0
            else ()
        ),
    )
    specific: tuple[object, ...]
    if interface is TeeInterfaceIdentity.BRACE_TO_STEM:
        specific = (
            request.interface_a_layout,
            request.connected_member_profile,
            request.brace_inclination_degrees,
            *(
                (resolved.connected_member_end_trim,)
                if request.connected_member_end_trim_enabled
                else ()
            ),
            *(
                (resolved.interface_a_placement.physical_geometry_fingerprint,)
                if request.brace_inclination_degrees != 0
                or request.interface_a_layout.placement_mode
                is TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED
                else ()
            ),
        )
    else:
        specific = (
            request.interface_b_layout,
            request.support_dimensions,
            resolved.selected_support_surface_id,
            *(
                (resolved.interface_b_placement.physical_geometry_fingerprint,)
                if request.interface_b_layout.placement_mode
                is TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED
                else ()
            ),
        )
    return _fingerprint((interface, common, specific))


def _interface_result(
    interface_id: str,
    group_id: str,
    normal_component: PhysicalQuantity,
    preview: MultiRowPreviewResult,
    interface_fingerprint: str,
    placement: TeeInterfacePlacementTrace,
    design: MultiRowOrchestrationResponse | None = None,
) -> TeeInterfaceResult:
    return TeeInterfaceResult(
        interface_id,
        group_id,
        normal_component,
        False,
        normal_component.magnitude == 0,
        preview,
        design,
        interface_fingerprint,
        placement,
    )


def _resolved_normal_component(resolved: _TeeResolvedAssembly, group_id: str) -> PhysicalQuantity:
    """Project the exact action onto a backend-resolved authoritative bolt axis."""

    group = next(
        item for item in resolved.context.resolved_bolt_groups if item.bolt_group.id == group_id
    )
    normal = group.bolt_group_frame.x_axis
    unit = (
        Unit.KIP if resolved.request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    )
    components = tuple(
        item.to(unit).magnitude
        for item in (
            resolved.request.global_force.x,
            resolved.request.global_force.y,
            resolved.request.global_force.z,
        )
    )
    axes = tuple(decimal_from_finite_real(item) for item in (normal.x, normal.y, normal.z))
    return PhysicalQuantity.of(
        sum(
            (component * axis for component, axis in zip(components, axes, strict=True)),
            Decimal(0),
        ),
        unit,
    )


def trim_tee_visualization(
    snapshot: SingleBoltVisualizationSnapshot,
    trimmed: TrimmedComponentSolids3D | None,
) -> SingleBoltVisualizationSnapshot:
    """Replace the connected-member renderer primitives with backend-trimmed solids."""

    if trimmed is None:
        return snapshot
    existing = tuple(
        item
        for item in (*snapshot.view_extension_primitives, *snapshot.primitives)
        if item.owner_id == trimmed.component_id
    )
    if not existing:
        raise RuntimeError("Connected-member visualization primitives are unavailable for trim.")
    frame_id = existing[0].frame_id
    meshes = tuple(
        VisualizationPrimitive(
            id=f"TRIMMED:MEMBER:{trimmed.component_id}:{solid.physical_element_id}:{index}",
            label=f"{solid.physical_element_id} trimmed member solid",
            kind=VisualizationPrimitiveKind.TRIANGLE_MESH,
            owner_id=trimmed.component_id,
            frame_id=frame_id,
            physical_element_id=solid.physical_element_id,
            material_region_id=solid.material_region_id,
            center=PositionVector3D(
                sum(point.x for point in solid.vertices) / len(solid.vertices),
                sum(point.y for point in solid.vertices) / len(solid.vertices),
                sum(point.z for point in solid.vertices) / len(solid.vertices),
            ),
            x_axis=None,
            y_axis=None,
            z_axis=None,
            parameters=(ScalarParameter("triangle_count", len(solid.triangulated_points) / 3),),
            points=solid.triangulated_points,
            resolution_status=VisualizationResolutionStatus.EXACT,
        )
        for index, solid in enumerate(trimmed.solids)
    )
    return replace(
        snapshot,
        primitives=tuple(
            item for item in snapshot.primitives if item.owner_id != trimmed.component_id
        ),
        view_extension_primitives=(
            *(
                item
                for item in snapshot.view_extension_primitives
                if item.owner_id != trimmed.component_id
            ),
            *meshes,
        ),
    )


def _preview_result(resolved: _TeeResolvedAssembly) -> TeeConnectorPreviewResult:
    preview_a = preview_multirow_connection(resolved.interface_a_request)
    preview_b = preview_multirow_connection(resolved.interface_b_request)
    if (
        resolved.interface_a_placement.method_compatibility
        is TeeFixedGridCompatibilityStatus.ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN
    ):
        preview_a = tee_fixed_grid_geometry_preview(
            resolved.interface_a_request,
            preview_a,
        )
    result_a = _interface_result(
        TeeInterfaceIdentity.BRACE_TO_STEM.value,
        _GROUP_A_ID,
        _resolved_normal_component(resolved, _GROUP_A_ID),
        preview_a,
        _interface_fingerprint(resolved, TeeInterfaceIdentity.BRACE_TO_STEM),
        resolved.interface_a_placement,
    )
    result_b = _interface_result(
        TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value,
        _GROUP_B_ID,
        _resolved_normal_component(resolved, _GROUP_B_ID),
        preview_b,
        _interface_fingerprint(resolved, TeeInterfaceIdentity.FLANGE_TO_SUPPORT),
        resolved.interface_b_placement,
    )
    demand_invalid = any(item.preview.visualization is None for item in (result_a, result_b))
    warnings = [*preview_a.warnings, *preview_b.warnings, "TEE_BODY_RESISTANCE_NOT_EVALUATED"]
    trim = resolved.connected_member_end_trim
    if trim.interference_status is TeeMemberEndInterferenceStatus.INTERFERENCE_DETECTED:
        warnings.append("CONNECTED_MEMBER_INTERFERES_WITH_TEE_FLANGE_ROOT")
    if trim.enabled:
        warnings.append("CONNECTED_MEMBER_TRIM_RESISTANCE_MAPPING_NOT_EVALUATED")
    if trim.exact_deficit is not None:
        warnings.append("HOLE_EDGE_CLEARANCE_TO_FABRICATED_END_IS_NEGATIVE")
    rectangular_limitations = tuple(
        dict.fromkeys(
            limitation.value
            for item in resolved.rectangular_full_through_paths
            for limitation in item.limitations
        )
    )
    warnings.extend(f"{item}:NOT_EVALUATED" for item in rectangular_limitations)
    for item in (result_a, result_b):
        if not item.normal_action_supported:
            warnings.append(f"{item.interface_id}:INTERFACE_NORMAL_ACTION_NOT_SUPPORTED")
    base_a = preview_single_bolt_connection(
        cast(
            SingleBoltOrchestrationRequest,
            resolved.interface_a_request.physical_connection_request,
        )
    )
    base_b = preview_single_bolt_connection(
        cast(
            SingleBoltOrchestrationRequest,
            resolved.interface_b_request.physical_connection_request,
        )
    )
    visualization_a = base_a.visualization
    visualization_b = base_b.visualization
    visualization = None
    physical_geometry_invalid = visualization_a is None or visualization_b is None
    if any(not item.geometry_valid for item in resolved.rectangular_full_through_paths):
        physical_geometry_invalid = True
    is_r2 = resolved.request.orchestration_contract_version == TEE_R2_ORCHESTRATION_CONTRACT_VERSION
    is_c2 = resolved.request.orchestration_contract_version == TEE_C2_ORCHESTRATION_CONTRACT_VERSION
    if visualization_a is not None and visualization_b is not None:
        visualization_a = trim_tee_visualization(
            visualization_a,
            resolved.trimmed_connected_member_solids,
        )
        visualization = TeeVisualizationSnapshot(
            schema_version=(
                TEE_C2_VISUALIZATION_SCHEMA_VERSION
                if is_c2
                else (
                    TEE_R2_VISUALIZATION_SCHEMA_VERSION
                    if is_r2
                    else TEE_VISUALIZATION_SCHEMA_VERSION
                )
            ),
            base_connection=visualization_a,
            interface_b_connection=visualization_b,
            interface_zones=(
                *visualization_a.interface_zones,
                *visualization_b.interface_zones,
            ),
            interface_a_bolts=expand_tee_bolts(
                base_a,
                resolved.request.interface_a_layout,
                "A",
            ),
            interface_b_bolts=expand_tee_bolts(
                base_b,
                resolved.request.interface_b_layout,
                "B",
            ),
            selected_support_surface_id=resolved.selected_support_surface_id,
            connected_member_profile=resolved.connected_member_profile,
            selected_connected_surface_id=(
                resolved.connected_member_profile.selected_profile_surface
            ),
            selected_connected_surface_patch_id=(
                resolved.connected_member_profile.surface_patch_id
            ),
            support_target_id=resolved.support_target_id,
            support_profile=resolved.support_profile,
            rectangular_full_through_paths=resolved.rectangular_full_through_paths,
        )
    invalid = (
        demand_invalid or physical_geometry_invalid or (trim.enabled and not trim.geometry_valid)
    )
    status = TeeAssemblyStatus.INVALID_GEOMETRY if invalid else TeeAssemblyStatus.NOT_EVALUATED
    design_ready = (
        not invalid
        and trim.geometry_valid
        and not trim.enabled
        and not resolved.rectangular_full_through_paths
        and preview_a.design_check_ready
        and preview_b.design_check_ready
    )
    use_normalized_c2_identity = is_c2 and (
        resolved.support_target_id
        not in {SharedSupportTargetId.W_COLUMN_FLANGE, SharedSupportTargetId.W_BEAM_FLANGE}
        or bool(resolved.rectangular_full_through_paths)
    )
    request_identity: object = (
        _normalized_c2_request_identity(resolved.request)
        if use_normalized_c2_identity
        else resolved.request
    )
    connected_profile_identity: object = (
        _normalized_profile_identity(
            resolved.request.connected_member_profile,
            resolved.request.source_length_unit,
        )
        if use_normalized_c2_identity
        else resolved.connected_member_profile
    )
    return TeeConnectorPreviewResult(
        request_id=resolved.request.request_id,
        orchestration_contract_version=resolved.request.orchestration_contract_version,
        preview_schema_version=(
            TEE_C2_PREVIEW_SCHEMA_VERSION
            if is_c2
            else (TEE_R2_PREVIEW_SCHEMA_VERSION if is_r2 else TEE_PREVIEW_SCHEMA_VERSION)
        ),
        support_role=resolved.request.support_role,
        selected_support_flange=resolved.request.selected_support_flange,
        connector_dimensions=resolved.request.connector_dimensions,
        tee_longitudinal_placement=resolved.tee_longitudinal_placement,
        connected_member_profile=resolved.connected_member_profile,
        connected_member_end_trim=trim,
        material_authority=resolved.material_authority,
        interface_a=result_a,
        interface_b=result_b,
        tee_body_resistance_status=TeeBodyResistanceStatus.NOT_EVALUATED,
        assembly_status=status,
        ordinary_pass_allowed=False,
        resistance_evaluated=False,
        design_check_ready=design_ready,
        warnings=tuple(dict.fromkeys(warnings)),
        engineering_fingerprint=_fingerprint(
            (
                request_identity,
                "STANDARD_TEE_TOPOLOGY",
                resolved.material_authority.connector_material_family,
                resolved.material_authority.fastener_material_family,
                resolved.material_authority.fastener_snapshot_id,
                resolved.material_authority.metallic_bolt_eligibility.status,
                resolved.selected_support_surface_id,
                connected_profile_identity,
                *(
                    (resolved.tee_longitudinal_placement.body_geometry_fingerprint,)
                    if resolved.tee_longitudinal_placement.body_center_coordinate.magnitude != 0
                    else ()
                ),
                *((trim,) if trim.enabled else ()),
                TeeInterfaceIdentity.BRACE_TO_STEM,
                TeeInterfaceIdentity.FLANGE_TO_SUPPORT,
                *(tuple(item.path_fingerprint for item in resolved.rectangular_full_through_paths)),
                *(
                    (
                        "TEE_FIXED_INTERFACE_A_GRID",
                        resolved.interface_a_placement.physical_geometry_fingerprint,
                    )
                    if resolved.request.brace_inclination_degrees != 0
                    or resolved.request.interface_a_layout.placement_mode
                    is TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED
                    else ()
                ),
                *(
                    (
                        "TEE_INTERFACE_B_GROUP_OFFSET",
                        resolved.interface_b_placement.physical_geometry_fingerprint,
                    )
                    if resolved.request.interface_b_layout.placement_mode
                    is TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED
                    else ()
                ),
            )
        ),
        visualization=visualization,
        support_target_id=resolved.support_target_id,
        support_profile=resolved.support_profile,
        rectangular_full_through_paths=resolved.rectangular_full_through_paths,
        design_limitations=rectangular_limitations,
    )


def preview_tee_connector(
    request: TeeConnectorOrchestrationRequest,
) -> TeeConnectorPreviewResult:
    """Resolve both physical interfaces and execute zero resistance equations."""

    resolved = resolve_tee_connector_request(request)
    return _preview_result(resolved)


def tee_interface_failed(response: MultiRowOrchestrationResponse) -> bool:
    integration = response.automatic_group_mode_integration
    return (
        integration is not None
        and integration.overall_disposition is MultiRowOverallDisposition.FAIL
    ) or any(
        item.overall_disposition is MultiRowOverallDisposition.FAIL
        for item in response.automatic_handoff_results
    )


def evaluate_tee_interface(
    request: MultiRowOrchestrationRequest,
) -> MultiRowOrchestrationResponse:
    try:
        return evaluate_multirow_connection(request)
    except ValueError as error:
        if str(error) != "Each inter-row check must identify one unique physical bolt line.":
            raise
        return evaluate_multirow_connection_through_handoff(request)


def design_check_tee_connector(
    request: TeeConnectorOrchestrationRequest,
) -> TeeConnectorDesignResult:
    """Run the accepted interface chains and retain the required Tee-body limitation."""

    resolved = resolve_tee_connector_request(request)
    preview = _preview_result(resolved)
    if preview.assembly_status is TeeAssemblyStatus.INVALID_GEOMETRY:
        return TeeConnectorDesignResult(
            preview,
            preview.interface_a,
            preview.interface_b,
            TeeBodyResistanceStatus.NOT_EVALUATED,
            TeeAssemblyStatus.INVALID_GEOMETRY,
            False,
            False,
            _fingerprint((preview.engineering_fingerprint, "INVALID_GEOMETRY")),
        )
    design_a = (
        None
        if resolved.request.connected_member_end_trim_enabled
        or resolved.interface_a_request.row_count < 2
        or resolved.interface_a_placement.method_compatibility
        is TeeFixedGridCompatibilityStatus.ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN
        else evaluate_tee_interface(resolved.interface_a_request)
    )
    design_b = (
        None
        if resolved.interface_b_request.row_count < 2
        else evaluate_tee_interface(resolved.interface_b_request)
    )
    result_a = _interface_result(
        TeeInterfaceIdentity.BRACE_TO_STEM.value,
        _GROUP_A_ID,
        _resolved_normal_component(resolved, _GROUP_A_ID),
        preview.interface_a.preview if design_a is None else design_a.preview,
        _interface_fingerprint(resolved, TeeInterfaceIdentity.BRACE_TO_STEM),
        resolved.interface_a_placement,
        design_a,
    )
    result_b = _interface_result(
        TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value,
        _GROUP_B_ID,
        _resolved_normal_component(resolved, _GROUP_B_ID),
        preview.interface_b.preview if design_b is None else design_b.preview,
        _interface_fingerprint(resolved, TeeInterfaceIdentity.FLANGE_TO_SUPPORT),
        resolved.interface_b_placement,
        design_b,
    )
    supported_failure = (design_a is not None and tee_interface_failed(design_a)) or (
        design_b is not None and tee_interface_failed(design_b)
    )
    status = TeeAssemblyStatus.FAIL if supported_failure else TeeAssemblyStatus.NOT_EVALUATED
    result_payload = (
        preview.engineering_fingerprint,
        None if design_a is None else design_a.automatic_group_mode_integration,
        None if design_b is None else design_b.automatic_group_mode_integration,
        TeeBodyResistanceStatus.NOT_EVALUATED,
        status,
    )
    return TeeConnectorDesignResult(
        replace(preview, interface_a=result_a, interface_b=result_b),
        result_a,
        result_b,
        TeeBodyResistanceStatus.NOT_EVALUATED,
        status,
        False,
        supported_failure,
        _fingerprint(result_payload),
    )


# Retain the internal names exercised by frozen-family regression probes.
_expanded_bolts = expand_tee_bolts
_evaluate_interface = evaluate_tee_interface
_fixed_grid_geometry_only_preview = tee_fixed_grid_geometry_preview
_trimmed_visualization = trim_tee_visualization


__all__ = (
    "TEE_C2_ORCHESTRATION_CONTRACT_VERSION",
    "TEE_C2_PREVIEW_SCHEMA_VERSION",
    "TEE_C2_VISUALIZATION_SCHEMA_VERSION",
    "TEE_ORCHESTRATION_CONTRACT_VERSION",
    "TEE_PREVIEW_SCHEMA_VERSION",
    "TEE_R2_ORCHESTRATION_CONTRACT_VERSION",
    "TEE_R2_PREVIEW_SCHEMA_VERSION",
    "TEE_R2_VISUALIZATION_SCHEMA_VERSION",
    "TEE_VISUALIZATION_SCHEMA_VERSION",
    "TeeAssemblyStatus",
    "TeeBodyResistanceStatus",
    "TeeConnectedMemberProfileTrace",
    "TeeConnectorDesignResult",
    "TeeConnectorOrchestrationRequest",
    "TeeConnectorPreviewResult",
    "TeeFixedGridCompatibilityStatus",
    "TeeHoleClearanceTrace",
    "TeeInterfacePlacementTrace",
    "TeeInterfaceResult",
    "TeeMaterialAuthorityTrace",
    "TeeMemberEndInterferenceStatus",
    "TeeMemberEndTrimTrace",
    "TeeResolvedAssembly",
    "TeeSupportProfileTrace",
    "TeeTrimBoltClearanceTrace",
    "TeeVectorInput",
    "TeeVisualizationSnapshot",
    "adapt_legacy_tee_brace_profile",
    "design_check_tee_connector",
    "evaluate_tee_interface",
    "expand_tee_bolts",
    "preview_tee_connector",
    "resolve_tee_connector_request",
    "tee_fixed_grid_geometry_preview",
    "tee_interface_failed",
    "trim_tee_visualization",
)
