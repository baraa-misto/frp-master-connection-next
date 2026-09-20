"""Stage 3.3A backend-authoritative single clip-angle vertical slice."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum, StrEnum
from typing import cast

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
    MultiRowVisualizationSnapshot,
    evaluate_multirow_connection_with_resolved_demand,
    preview_multirow_connection,
)
from frp_master_connection.application.shared_support_integration import (
    IntegratedFullThroughBoltTrace,
    build_integrated_full_through_bolt,
    require_shared_support_selection,
)
from frp_master_connection.application.visualization import (
    MaterialDirectionSet,
    VisualizationPrimitive,
    VisualizationPrimitiveKind,
    build_placed_component_visualization_snapshots,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    EndUseFactors,
    FirstRowPlanMethod,
    LapConfiguration,
    MethodProvenance,
    MultiRowMethodApplicability,
    PerBoltDemandPlan,
    PhysicalQuantity,
    PlanAvailability,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    QualificationDisposition,
    RowDemandPlan,
    RowDemandScenario,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
    calculate_eccentric_bolt_group_demand,
    canonical_decimal_string,
    decimal_from_finite_real,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    EccentricDemandInput,
    EccentricDemandResult,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
)
from frp_master_connection.calculation.multirow import MultiRowDemandPlan
from frp_master_connection.calculation.multirow_engine import (
    MultiRowBoltGeometryContext,
    MultiRowOverallDisposition,
    MultiRowPhysicalGeometryContext,
    MultiRowProjectedGroupContext,
)
from frp_master_connection.domain import (
    AssemblyMember,
    ClipAngleBoltLayout,
    ClipAngleBoltPlacementMode,
    ClipAngleDimensions,
    ClipAngleHand,
    ClipAngleInterfaceIdentity,
    ClipAngleLengthAnchor,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    FRPComponentOrientation,
    MemberEnd,
    MemberProfile,
    MemberProfileDimensions,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PositionVector3D,
    PrincipalAxisFamily,
    SelectedSupportFlange,
    SharedSupportTargetId,
    WideFlangeIProfileDimensions,
    profile_section_geometry_adapter,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import (
    AuthoritativeCutPlane3D,
    LocalRectangularPrism3D,
    PlacedComponentGeometry3D,
    PlanarRectangularSurface3D,
    SectionDatumOffset,
    TrimmedComponentSolids3D,
    TrimmedPhysicalSolid3D,
    UnitVector3D,
    Vector3D,
    create_component_surface_set,
    place_member,
    signed_distance_to_plane,
    trim_placed_rectangular_component,
)

CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION = "3.3A-RC1"
CLIP_ANGLE_C2_ORCHESTRATION_CONTRACT_VERSION = "3.3C2-RC1"
CLIP_ANGLE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"
CLIP_ANGLE_BODY_CHECK_ID = "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE"
CLIP_ANGLE_TRIM_PLANE_ID = "CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE"

_CONNECTOR_ID = "single-clip-angle-connector"
_CONNECTED_MEMBER_ID = "clip-angle-connected-member"
_SUPPORT_ID = "clip-angle-support"
_GROUP_A_ID = "clip-angle-bolt-group-a"
_GROUP_B_ID = "clip-angle-bolt-group-b"
_ACTION_ID = "clip-angle-member-end-action"
_LOAD_ID = "clip-angle-load-combination"
_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)


class ClipAngleBodyResistanceStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"


class ClipAngleAssemblyStatus(StrEnum):
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class ClipAngleGeometryStatus(StrEnum):
    VALID = "VALID"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class ClipAngleInterferenceStatus(StrEnum):
    CLEAR = "CLEAR"
    INTERFERENCE_DETECTED = "INTERFERENCE_DETECTED"
    TRIMMED_CLEAR = "TRIMMED_CLEAR"
    REMAINING_INTERFERENCE = "REMAINING_INTERFERENCE"


@dataclass(frozen=True, slots=True)
class ClipAngleVectorInput:
    x: PhysicalQuantity
    y: PhysicalQuantity
    z: PhysicalQuantity

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.z)
        if any(not isinstance(item, PhysicalQuantity) for item in values):
            raise TypeError("Clip-angle vector components must be physical quantities.")
        if len({item.dimension for item in values}) != 1:
            raise ValueError("Clip-angle vector components must share one dimension.")


@dataclass(frozen=True, slots=True)
class ClipAngleOrchestrationRequest:
    """Canonical server-owned request for one single-angle connection."""

    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    hand: ClipAngleHand
    support_role: ClipAngleSupportRole
    selected_support_flange: SelectedSupportFlange
    connector_dimensions: ClipAngleDimensions
    support_dimensions: ClipAngleSupportDimensions
    connected_member_profile: MemberProfile
    interface_a_layout: ClipAngleBoltLayout
    interface_b_layout: ClipAngleBoltLayout
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    hole_basis: PublishedCodeUnitBasis
    global_force: ClipAngleVectorInput
    global_moment: ClipAngleVectorInput
    global_reference_point: ClipAngleVectorInput
    connected_member_inclination_degrees: Decimal = _ZERO
    connected_member_end_trim_enabled: bool = False
    connected_member_end_clearance: PhysicalQuantity | None = None
    connector_length_anchor: ClipAngleLengthAnchor = ClipAngleLengthAnchor.CENTER
    connector_length_anchor_position: PhysicalQuantity | None = None
    orchestration_contract_version: str = CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION
    support_target_id: SharedSupportTargetId | None = None
    support_profile: MemberProfile | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version not in {
            CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION,
            CLIP_ANGLE_C2_ORCHESTRATION_CONTRACT_VERSION,
        }:
            raise ValueError("Unsupported clip-angle orchestration contract version.")
        expected_unit = (
            Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        )
        if self.source_length_unit is not expected_unit:
            raise ValueError("Source length unit must match the engineering unit system.")
        if not isinstance(self.connected_member_profile, MemberProfile):
            raise TypeError("connected_member_profile must be a MemberProfile.")
        profile = self.connected_member_profile
        if (
            profile.member_id != _CONNECTED_MEMBER_ID
            or profile.role not in {MemberRole.BRACE, MemberRole.BEAM}
            or profile.material_kind is not ComponentMaterialKind.PULTRUDED_FRP
        ):
            raise ValueError("The connected profile must own the authorized FRP Brace/Beam.")
        if profile.family is MemberProfileFamily.ROUND_HOLLOW_SECTION:
            raise ValueError("Round profiles have no authorized planar clip-angle interface.")
        require_direct_tee_profile_surface(profile)
        if (self.support_target_id is None) is not (self.support_profile is None):
            raise ValueError("support_target_id and support_profile must be supplied together.")
        if self.support_target_id is not None:
            require_shared_support_selection(
                self.support_target_id,
                cast(MemberProfile, self.support_profile),
            )
            if self.orchestration_contract_version != CLIP_ANGLE_C2_ORCHESTRATION_CONTRACT_VERSION:
                raise ValueError("Explicit shared support targets require the C2 contract.")
        if not isinstance(self.connected_member_inclination_degrees, Decimal):
            raise TypeError("connected_member_inclination_degrees must be a Decimal.")
        if not self.connected_member_inclination_degrees.is_finite() or not (
            Decimal(-90) <= self.connected_member_inclination_degrees <= Decimal(90)
        ):
            raise ValueError("Connected-member inclination must be from -90 through 90 degrees.")
        if not isinstance(self.connected_member_end_trim_enabled, bool):
            raise TypeError("connected_member_end_trim_enabled must be Boolean.")
        if self.connected_member_end_trim_enabled:
            clearance = self.connected_member_end_clearance
            if (
                not isinstance(clearance, PhysicalQuantity)
                or clearance.dimension.value != "LENGTH"
                or clearance.magnitude < 0
            ):
                raise ValueError("Enabled trim requires one nonnegative length clearance.")
        elif self.connected_member_end_clearance is not None:
            raise ValueError("Trim clearance is forbidden while end trim is disabled.")
        if self.connector_length_anchor_position is not None:
            position = self.connector_length_anchor_position
            if position.dimension.value != "LENGTH" or position.unit is not self.source_length_unit:
                raise ValueError("Connector anchor position must use the source length unit.")
        for name in ("bolt_diameter", "hole_diameter"):
            quantity = cast(PhysicalQuantity, getattr(self, name))
            if quantity.dimension.value != "LENGTH" or quantity.magnitude <= 0:
                raise ValueError(f"{name} must be a positive length.")
        if self.hole_diameter.canonical_magnitude < self.bolt_diameter.canonical_magnitude:
            raise ValueError("The physical hole cannot be smaller than its bolt.")
        if self.global_force.x.dimension.value != "FORCE":
            raise ValueError("global_force must contain force quantities.")
        if self.global_moment.x.dimension.value != "MOMENT":
            raise ValueError("global_moment must contain moment quantities.")
        if self.global_reference_point.x.dimension.value != "LENGTH":
            raise ValueError("global_reference_point must contain length quantities.")


@dataclass(frozen=True, slots=True)
class ClipAngleSemanticFrameTrace:
    s_axis: tuple[Decimal, Decimal, Decimal]
    p_axis: tuple[Decimal, Decimal, Decimal]
    l_axis: tuple[Decimal, Decimal, Decimal]
    handedness: str = "S_C cross P_C = L_C"


@dataclass(frozen=True, slots=True)
class ClipAngleClearanceTrace:
    heel: PhysicalQuantity
    free_edge: PhysicalQuantity
    positive_length_end: PhysicalQuantity
    negative_length_end: PhysicalQuantity
    minimum: PhysicalQuantity
    governing_bolt_id: str
    governing_boundary_id: str
    exact_deficit: PhysicalQuantity | None
    geometry_valid: bool


@dataclass(frozen=True, slots=True)
class ClipAngleBoltTrace:
    bolt_id: str
    row_id: str
    bolt_line_id: str
    width_coordinate: PhysicalQuantity
    length_coordinate: PhysicalQuantity
    global_center: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    axis: tuple[Decimal, Decimal, Decimal]
    layer_ids: tuple[str, ...]
    stack_start: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    stack_end: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]


@dataclass(frozen=True, slots=True)
class ClipAngleInterfacePlacementTrace:
    interface_id: ClipAngleInterfaceIdentity
    bolt_group_id: str
    width_axis: tuple[Decimal, Decimal, Decimal]
    length_axis: tuple[Decimal, Decimal, Decimal]
    normal_axis: tuple[Decimal, Decimal, Decimal]
    width_coordinates: tuple[PhysicalQuantity, ...]
    length_coordinates: tuple[PhysicalQuantity, ...]
    bolts: tuple[ClipAngleBoltTrace, ...]
    clearances: ClipAngleClearanceTrace
    geometry_fingerprint: str


@dataclass(frozen=True, slots=True)
class ClipAngleLongitudinalPlacementTrace:
    datum_id: str
    connector_length_anchor: ClipAngleLengthAnchor
    selected_anchor_coordinate: PhysicalQuantity
    body_center_coordinate: PhysicalQuantity
    positive_end_coordinate: PhysicalQuantity
    negative_end_coordinate: PhysicalQuantity
    body_geometry_fingerprint: str


@dataclass(frozen=True, slots=True)
class ClipAngleMaterialRegionTrace:
    region_id: str
    physical_element_id: str
    lw: tuple[Decimal, Decimal, Decimal]
    cw: tuple[Decimal, Decimal, Decimal]
    tt: tuple[Decimal, Decimal, Decimal]
    source_id: str = "ICE_LOCKED_PULTRUDED_FRP"
    source_revision: str = "RC2"


@dataclass(frozen=True, slots=True)
class ClipAngleTrimBoltClearanceTrace:
    bolt_id: str
    center_to_trim_edge: PhysicalQuantity
    hole_edge_to_trim_edge: PhysicalQuantity
    trim_edge_id: str


@dataclass(frozen=True, slots=True)
class ClipAngleTrimTrace:
    enabled: bool
    reference_plane_id: str
    reference_plane_origin: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    reference_plane_normal: tuple[Decimal, Decimal, Decimal]
    cut_plane_id: str | None
    cut_plane_origin: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity] | None
    cut_plane_normal: tuple[Decimal, Decimal, Decimal] | None
    measured_plane_clearance: PhysicalQuantity | None
    interference_status: ClipAngleInterferenceStatus
    geometry_valid: bool
    trimmed_member_geometry_identity: str | None
    fabricated_trim_edge_ids: tuple[str, ...]
    fabricated_trim_edge_id: str | None
    bolt_clearances: tuple[ClipAngleTrimBoltClearanceTrace, ...]
    governing_bolt_id: str | None
    governing_trim_edge_id: str | None
    minimum_hole_edge_clearance: PhysicalQuantity | None
    exact_deficit: PhysicalQuantity | None


@dataclass(frozen=True, slots=True)
class ClipAngleBoxTrace:
    id: str
    owner_id: str
    role: str
    center: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    size_s: PhysicalQuantity
    size_p: PhysicalQuantity
    size_l: PhysicalQuantity
    physical_element_id: str | None = None
    material_region_id: str | None = None
    basis: tuple[
        tuple[Decimal, Decimal, Decimal],
        tuple[Decimal, Decimal, Decimal],
        tuple[Decimal, Decimal, Decimal],
    ] = (
        (_ONE, _ZERO, _ZERO),
        (_ZERO, _ONE, _ZERO),
        (_ZERO, _ZERO, _ONE),
    )


@dataclass(frozen=True, slots=True)
class ClipAngleProfileMaterialRegionTrace:
    id: str
    physical_element_id: str
    material_region_id: str
    origin: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    lw: tuple[Decimal, Decimal, Decimal]
    cw: tuple[Decimal, Decimal, Decimal]
    tt: tuple[Decimal, Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class ClipAngleSupportProfileTrace:
    target_id: SharedSupportTargetId
    profile_id: str
    profile_family: MemberProfileFamily
    role: MemberRole
    dimensions: MemberProfileDimensions
    orientation: MemberProfileOrientation
    selected_surface: MemberProfileSurfaceId


@dataclass(frozen=True, slots=True)
class ClipAngleTriangleMeshTrace:
    id: str
    owner_id: str
    role: str
    physical_element_id: str
    material_region_id: str
    points: tuple[
        tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
        ...,
    ]


@dataclass(frozen=True, slots=True)
class ClipAngleVisualizationSnapshot:
    schema_version: str
    semantic_frame: ClipAngleSemanticFrameTrace
    connected_member_profile_id: str
    connected_member_role: MemberRole
    connected_member_profile_family: MemberProfileFamily
    connected_member_profile_orientation: MemberProfileOrientation
    boxes: tuple[ClipAngleBoxTrace, ...]
    meshes: tuple[ClipAngleTriangleMeshTrace, ...]
    interface_a_bolts: tuple[ClipAngleBoltTrace, ...]
    interface_b_bolts: tuple[ClipAngleBoltTrace, ...]
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    connected_member_material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    selected_support_surface_id: str
    selected_connected_surface_id: str
    trim: ClipAngleTrimTrace
    global_force: ClipAngleVectorInput
    global_moment: ClipAngleVectorInput
    global_reference_point: ClipAngleVectorInput
    support_target_id: SharedSupportTargetId
    support_profile: ClipAngleSupportProfileTrace
    support_material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]


@dataclass(frozen=True, slots=True)
class ClipAngleInterfaceResult:
    interface_id: ClipAngleInterfaceIdentity
    physical_name: str
    bolt_group_id: str
    normal_component: PhysicalQuantity
    normal_action_supported: bool
    automatic_axis_tension_generated: bool
    prying_generated: bool
    demand: EccentricDemandResult
    resistance: MultiRowOrchestrationResponse | None
    placement: ClipAngleInterfacePlacementTrace
    interface_fingerprint: str


@dataclass(frozen=True, slots=True)
class ClipAnglePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    semantic_frame: ClipAngleSemanticFrameTrace
    hand: ClipAngleHand
    support_role: ClipAngleSupportRole
    selected_support_flange: SelectedSupportFlange
    longitudinal_placement: ClipAngleLongitudinalPlacementTrace
    interface_a: ClipAngleInterfaceResult
    interface_b: ClipAngleInterfaceResult
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    trim: ClipAngleTrimTrace
    connector_body_required_check: str
    connector_body_status: ClipAngleBodyResistanceStatus
    geometry_status: ClipAngleGeometryStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: ClipAngleAssemblyStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    warnings: tuple[str, ...]
    canonical_input_fingerprint: str
    connector_geometry_fingerprint: str
    engineering_fingerprint: str
    visualization: ClipAngleVisualizationSnapshot | None
    support_target_id: SharedSupportTargetId
    support_profile: ClipAngleSupportProfileTrace
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]
    design_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClipAngleDesignResult:
    preview: ClipAnglePreviewResult
    interface_a: ClipAngleInterfaceResult
    interface_b: ClipAngleInterfaceResult
    connector_body_required_check: str
    connector_body_status: ClipAngleBodyResistanceStatus
    assembly_status: ClipAngleAssemblyStatus
    ordinary_pass_allowed: bool
    supported_interface_failure_present: bool
    result_fingerprint: str


def _quantity(value: Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _legacy_support_profile(request: ClipAngleOrchestrationRequest) -> MemberProfile:
    dimensions = request.support_dimensions
    role = (
        MemberRole.COLUMN
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else MemberRole.BEAM
    )
    surface = (
        MemberProfileSurfaceId.FLANGE_POS_OUTER
        if request.selected_support_flange is SelectedSupportFlange.POSITIVE_LOCAL_Z
        else MemberProfileSurfaceId.FLANGE_NEG_OUTER
    )
    return MemberProfile(
        "clip-angle-support-wide-flange-profile",
        _SUPPORT_ID,
        role,
        MemberProfileFamily.WIDE_FLANGE_I,
        WideFlangeIProfileDimensions(
            dimensions.member_length,
            dimensions.overall_depth,
            dimensions.flange_width,
            dimensions.web_thickness,
            dimensions.flange_thickness,
        ),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, _SUPPORT_ID),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        surface,
    )


def _support_selection(
    request: ClipAngleOrchestrationRequest,
) -> tuple[SharedSupportTargetId, MemberProfile]:
    if request.support_target_id is not None:
        profile = cast(MemberProfile, request.support_profile)
        require_shared_support_selection(request.support_target_id, profile)
        return request.support_target_id, profile
    target = (
        SharedSupportTargetId.W_COLUMN_FLANGE
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else SharedSupportTargetId.W_BEAM_FLANGE
    )
    return target, _legacy_support_profile(request)


def _support_layer_thickness(request: ClipAngleOrchestrationRequest) -> Decimal:
    _target, profile = _support_selection(request)
    return require_direct_tee_profile_surface(profile).layer_thickness


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return (value.dimension.value, canonical_decimal_string(value.canonical_magnitude))
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return tuple(_canonical(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    return value


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonical(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _length_fields(
    value: ClipAngleDimensions | ClipAngleSupportDimensions | MemberProfileDimensions,
    unit: Unit,
) -> dict[str, PhysicalQuantity]:
    return {
        field.name: _quantity(cast(Decimal, getattr(value, field.name)), unit)
        for field in fields(value)
    }


def _layout_fingerprint_value(
    value: ClipAngleBoltLayout,
    unit: Unit,
) -> tuple[object, ...]:
    return (
        value.row_count,
        value.bolts_per_row,
        value.placement_mode,
        *(
            _quantity(cast(Decimal, getattr(value, name)), unit)
            for name in (
                "pitch",
                "gauge",
                "heel_edge_distance",
                "free_edge_distance",
                "negative_end_distance",
                "positive_end_distance",
            )
        ),
        None if value.length_offset is None else _quantity(value.length_offset, unit),
        None if value.width_offset is None else _quantity(value.width_offset, unit),
    )


def _anchor_coordinates(
    request: ClipAngleOrchestrationRequest,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    selected = (
        _ZERO
        if request.connector_length_anchor_position is None
        else request.connector_length_anchor_position.to(request.source_length_unit).magnitude
    )
    half = request.connector_dimensions.connector_length / _TWO
    if request.connector_length_anchor is ClipAngleLengthAnchor.CENTER:
        return selected, selected, selected + half, selected - half
    if request.connector_length_anchor is ClipAngleLengthAnchor.POSITIVE_L_END:
        return selected, selected - half, selected, selected - _TWO * half
    return selected, selected + half, selected + _TWO * half, selected


def _layout_coordinates(
    layout: ClipAngleBoltLayout,
    dimensions: ClipAngleDimensions,
    leg_width: Decimal,
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    flat_center = (dimensions.thickness + leg_width) / _TWO
    if layout.placement_mode is ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED:
        width_center = flat_center + cast(Decimal, layout.width_offset)
        length_center = cast(Decimal, layout.length_offset)
        widths = tuple(
            width_center - layout.line_span / _TWO + Decimal(index) * layout.gauge
            for index in range(layout.bolts_per_row)
        )
        lengths = tuple(
            length_center - layout.row_span / _TWO + Decimal(index) * layout.pitch
            for index in range(layout.row_count)
        )
        return widths, lengths
    widths = tuple(
        dimensions.thickness + layout.heel_edge_distance + Decimal(index) * layout.gauge
        for index in range(layout.bolts_per_row)
    )
    lengths = tuple(
        -dimensions.connector_length / _TWO
        + layout.negative_end_distance
        + Decimal(index) * layout.pitch
        for index in range(layout.row_count)
    )
    return widths, lengths


def _clearances(
    request: ClipAngleOrchestrationRequest,
    interface_letter: str,
    widths: tuple[Decimal, ...],
    lengths: tuple[Decimal, ...],
    leg_width: Decimal,
    positive_end: Decimal,
    negative_end: Decimal,
) -> ClipAngleClearanceTrace:
    unit = request.source_length_unit
    radius = request.hole_diameter.to(unit).magnitude / _TWO
    candidates: list[tuple[Decimal, str, str]] = []
    for row_index, length in enumerate(lengths, start=1):
        for line_index, width in enumerate(widths, start=1):
            bolt_id = f"CLIP-{interface_letter}-R{row_index}-B{line_index}"
            candidates.extend(
                (
                    (width - request.connector_dimensions.thickness - radius, "HEEL", bolt_id),
                    (leg_width - width - radius, "FREE_EDGE", bolt_id),
                    (positive_end - length - radius, "POSITIVE_L_END", bolt_id),
                    (length - negative_end - radius, "NEGATIVE_L_END", bolt_id),
                )
            )
    minimum, boundary, bolt = min(candidates, key=lambda item: (item[0], item[1], item[2]))
    by_boundary = {
        name: min(value for value, key, _ in candidates if key == name)
        for name in ("HEEL", "FREE_EDGE", "POSITIVE_L_END", "NEGATIVE_L_END")
    }
    return ClipAngleClearanceTrace(
        _quantity(by_boundary["HEEL"], unit),
        _quantity(by_boundary["FREE_EDGE"], unit),
        _quantity(by_boundary["POSITIVE_L_END"], unit),
        _quantity(by_boundary["NEGATIVE_L_END"], unit),
        _quantity(minimum, unit),
        bolt,
        boundary,
        None if minimum >= 0 else _quantity(-minimum, unit),
        minimum >= 0,
    )


def _profile_thickness(profile: MemberProfile) -> Decimal:
    return require_direct_tee_profile_surface(profile).layer_thickness


def _rectangular_layer_ids(
    connector_layer: str,
    profile: MemberProfile,
) -> tuple[str, ...] | None:
    if profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION:
        return (connector_layer, "RHS_NEAR_WALL", "RHS_FAR_WALL")
    if profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        return (connector_layer, "SOLID_RECTANGULAR_SECTION")
    return None


def _support_layer_identity(request: ClipAngleOrchestrationRequest) -> str:
    identities = {
        SharedSupportTargetId.W_COLUMN_WEB: "W_WEB",
        SharedSupportTargetId.CHANNEL_COLUMN_WEB: "CHANNEL_WEB",
        SharedSupportTargetId.ANGLE_COLUMN_LEG: "ANGLE_SELECTED_LEG",
    }
    if request.support_target_id is None:
        return f"{_SUPPORT_ID}:SELECTED_W_FLANGE"
    return identities.get(request.support_target_id, f"{_SUPPORT_ID}:SELECTED_PROFILE_REGION")


def _bolt_trace(
    request: ClipAngleOrchestrationRequest,
    interface_letter: str,
    row_index: int,
    line_index: int,
    width: Decimal,
    length: Decimal,
) -> ClipAngleBoltTrace:
    unit = request.source_length_unit
    hand = request.hand.sign
    thickness = request.connector_dimensions.thickness
    if interface_letter == "A":
        center = (
            _quantity(_ZERO, unit),
            _quantity(width, unit),
            _quantity(hand * length, unit),
        )
        axis = (hand, _ZERO, _ZERO)
        member_thickness = _profile_thickness(request.connected_member_profile)
        start = (
            _quantity(-hand * member_thickness, unit),
            _quantity(width, unit),
            _quantity(hand * length, unit),
        )
        end = (
            _quantity(hand * thickness, unit),
            _quantity(width, unit),
            _quantity(hand * length, unit),
        )
        layers = _rectangular_layer_ids(
            "CLIP_ANGLE_CONNECTED_LEG",
            request.connected_member_profile,
        ) or (
            f"{_CONNECTED_MEMBER_ID}:SELECTED_PROFILE_REGION",
            f"{_CONNECTOR_ID}:CONNECTED_MEMBER_LEG",
        )
    else:
        center = (
            _quantity(hand * width, unit),
            _quantity(_ZERO, unit),
            _quantity(hand * length, unit),
        )
        axis = (_ZERO, Decimal(-1), _ZERO)
        start = (
            _quantity(hand * width, unit),
            _quantity(thickness, unit),
            _quantity(hand * length, unit),
        )
        end = (
            _quantity(hand * width, unit),
            _quantity(-_support_layer_thickness(request), unit),
            _quantity(hand * length, unit),
        )
        support_profile = _support_selection(request)[1]
        layers = _rectangular_layer_ids(
            "CLIP_ANGLE_SUPPORT_LEG",
            support_profile,
        ) or (f"{_CONNECTOR_ID}:SUPPORT_LEG", _support_layer_identity(request))
    return ClipAngleBoltTrace(
        f"CLIP-{interface_letter}-R{row_index}-B{line_index}",
        f"ROW_{row_index}",
        f"BOLT_LINE_{line_index}",
        _quantity(width, unit),
        _quantity(length, unit),
        center,
        axis,
        layers,
        start,
        end,
    )


def _placement(
    request: ClipAngleOrchestrationRequest,
    interface: ClipAngleInterfaceIdentity,
    layout: ClipAngleBoltLayout,
    leg_width: Decimal,
    positive_end: Decimal,
    negative_end: Decimal,
) -> ClipAngleInterfacePlacementTrace:
    letter = (
        "A" if interface is ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG else "B"
    )
    widths, lengths = _layout_coordinates(layout, request.connector_dimensions, leg_width)
    bolts = tuple(
        _bolt_trace(request, letter, row_index, line_index, width, length)
        for row_index, length in enumerate(lengths, start=1)
        for line_index, width in enumerate(widths, start=1)
    )
    hand = request.hand.sign
    width_axis = (_ZERO, _ONE, _ZERO) if letter == "A" else (hand, _ZERO, _ZERO)
    normal = (hand, _ZERO, _ZERO) if letter == "A" else (_ZERO, Decimal(-1), _ZERO)
    geometry_payload = (
        interface,
        request.hand,
        _length_fields(request.connector_dimensions, request.source_length_unit),
        tuple(_quantity(item, request.source_length_unit) for item in widths),
        tuple(_quantity(item, request.source_length_unit) for item in lengths),
        request.bolt_diameter,
        request.hole_diameter,
    )
    return ClipAngleInterfacePlacementTrace(
        interface,
        _GROUP_A_ID if letter == "A" else _GROUP_B_ID,
        width_axis,
        (_ZERO, _ZERO, hand),
        normal,
        tuple(_quantity(item, request.source_length_unit) for item in widths),
        tuple(_quantity(item, request.source_length_unit) for item in lengths),
        bolts,
        _clearances(request, letter, widths, lengths, leg_width, positive_end, negative_end),
        _fingerprint(geometry_payload),
    )


def _dot_force(
    vector: ClipAngleVectorInput,
    axis: tuple[Decimal, Decimal, Decimal],
    unit: Unit,
) -> PhysicalQuantity:
    values = tuple(item.to(unit).magnitude for item in (vector.x, vector.y, vector.z))
    return PhysicalQuantity.of(sum((a * b for a, b in zip(values, axis, strict=True)), _ZERO), unit)


def _physical_geometry(
    placement: ClipAngleInterfacePlacementTrace,
    request: ClipAngleOrchestrationRequest,
    force_u: PhysicalQuantity,
    force_v: PhysicalQuantity,
    calculation_preview: MultiRowPreviewResult | None,
) -> MultiRowPhysicalGeometryContext:
    unit = request.source_length_unit
    width_center = sum((item.magnitude for item in placement.width_coordinates), _ZERO) / Decimal(
        len(placement.width_coordinates)
    )
    length_center = sum((item.magnitude for item in placement.length_coordinates), _ZERO) / Decimal(
        len(placement.length_coordinates)
    )
    hole = request.hole_diameter.to(unit).magnitude
    bolt = request.bolt_diameter.to(unit).magnitude

    def calculation_bolt_id(item: ClipAngleBoltTrace) -> str:
        return (
            f"B_R{item.row_id.removeprefix('ROW_')}_L{item.bolt_line_id.removeprefix('BOLT_LINE_')}"
        )

    preview_bolts = (
        {}
        if calculation_preview is None or calculation_preview.visualization is None
        else {item.bolt_id: item for item in calculation_preview.visualization.bolts}
    )
    bolts = tuple(
        MultiRowBoltGeometryContext(
            calculation_bolt_id(item),
            item.width_coordinate.magnitude - width_center,
            item.length_coordinate.magnitude - length_center,
            bolt,
            hole,
            "ASTM_F593_17_GROUP_2_316_316L",
            placement.interface_id.value,
        )
        for item in placement.bolts
    )
    by_row = tuple(dict.fromkeys(item.row_id for item in placement.bolts))
    by_line = tuple(dict.fromkeys(item.bolt_line_id for item in placement.bolts))
    if preview_bolts:
        snapshot = cast(
            MultiRowVisualizationSnapshot,
            cast(MultiRowPreviewResult, calculation_preview).visualization,
        )
        by_row = snapshot.row_ids
        by_line = snapshot.bolt_line_ids
    bolt_coordinates = {item.bolt_id: (item.x, item.y) for item in bolts}

    def resolved_row_id(item: ClipAngleBoltTrace) -> str:
        calculation_id = calculation_bolt_id(item)
        return item.row_id if not preview_bolts else preview_bolts[calculation_id].row_id

    def resolved_line_id(item: ClipAngleBoltTrace) -> str:
        calculation_id = calculation_bolt_id(item)
        return (
            item.bolt_line_id if not preview_bolts else preview_bolts[calculation_id].bolt_line_id
        )

    magnitude = (
        force_u.magnitude * force_u.magnitude + force_v.magnitude * force_v.magnitude
    ).sqrt()
    direction = (
        (_ZERO, _ONE)
        if magnitude == 0
        else (force_u.magnitude / magnitude, force_v.magnitude / magnitude)
    )
    transverse = (-direction[1], direction[0])

    def projected(bolt_ids: tuple[str, ...], axis: tuple[Decimal, Decimal]) -> Decimal:
        return sum(
            (
                bolt_coordinates[bolt_id][0] * axis[0] + bolt_coordinates[bolt_id][1] * axis[1]
                for bolt_id in bolt_ids
            ),
            _ZERO,
        ) / Decimal(len(bolt_ids))

    rows = tuple(
        MultiRowProjectedGroupContext(
            row_name,
            index,
            projected(
                tuple(
                    calculation_bolt_id(item)
                    for item in placement.bolts
                    if resolved_row_id(item) == row_name
                ),
                direction,
            ),
            _ZERO,
            tuple(
                calculation_bolt_id(item)
                for item in placement.bolts
                if resolved_row_id(item) == row_name
            ),
        )
        for index, row_name in enumerate(by_row, start=1)
    )
    lines = tuple(
        MultiRowProjectedGroupContext(
            line_name,
            index,
            projected(
                tuple(
                    calculation_bolt_id(item)
                    for item in placement.bolts
                    if resolved_line_id(item) == line_name
                ),
                transverse,
            ),
            _ZERO,
            tuple(
                calculation_bolt_id(item)
                for item in placement.bolts
                if resolved_line_id(item) == line_name
            ),
        )
        for index, line_name in enumerate(by_line, start=1)
    )
    return MultiRowPhysicalGeometryContext(
        placement.bolt_group_id,
        placement.interface_id.value,
        f"{placement.interface_id.value}:FINITE_FLAT_LEG",
        unit,
        direction,
        transverse,
        bolts,
        rows,
        lines,
        min(item.x for item in bolts) - _ONE,
        max(item.x for item in bolts) + _ONE,
        min(item.y for item in bolts) - _ONE,
        max(item.y for item in bolts) + _ONE,
        Decimal("0.000000001"),
    )


def _demand_plan(
    geometry: MultiRowPhysicalGeometryContext,
    total: PhysicalQuantity,
) -> tuple[MultiRowDemandPlan, MultiRowMethodApplicability, QualificationDisposition]:
    row_count = len(geometry.rows)
    if row_count in {2, 3}:
        fractions = prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, row_count)
        basis = RowDistributionBasis.ASCE_PRESCRIBED
        applicability = MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
        qualification = QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
    else:
        fractions = tuple(_ONE / Decimal(row_count) for _ in geometry.rows)
        basis = RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION
        applicability = MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
        qualification = QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    rows = tuple(
        RowDemandPlan(
            row.id,
            total * fractions[index],
            fractions[index],
            tuple(
                PerBoltDemandPlan(bolt_id, total * fractions[index] / Decimal(len(row.bolt_ids)))
                for bolt_id in row.bolt_ids
            ),
        )
        for index, row in enumerate(geometry.rows)
    )
    provenance = MethodProvenance(
        "STAGE_3_3A_CANONICAL_MEMBER_END_ACTION",
        "STAGE_3_3A_SINGLE_CLIP_ANGLE_ENGINEERING_SPECIFICATION_RC1",
        "RC1",
        _LOAD_ID,
        "EXPLICIT_GLOBAL_REFERENCE_POINT",
        True,
        True,
    )
    plan = MultiRowDemandPlan(
        basis,
        total,
        (RowDemandScenario(basis.value, None, rows),),
        PlanAvailability.READY,
        provenance,
        (),
    )
    return plan, applicability, qualification


def _exact_vector(value: ClipAngleVectorInput) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(value.x, value.y, value.z)


def _physical_hand_vector(
    request: ClipAngleOrchestrationRequest,
    value: ClipAngleVectorInput,
) -> ClipAngleVectorInput:
    """Rotate semantic S/P/L components into the selected physical hand."""

    hand = request.hand.sign
    return ClipAngleVectorInput(
        PhysicalQuantity.of(hand * value.x.magnitude, value.x.unit),
        value.y,
        PhysicalQuantity.of(hand * value.z.magnitude, value.z.unit),
    )


def _demand(
    request: ClipAngleOrchestrationRequest,
    placement: ClipAngleInterfacePlacementTrace,
    multirow_request: MultiRowOrchestrationRequest | None,
) -> tuple[EccentricDemandResult, PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    origin_width = sum((item.magnitude for item in placement.width_coordinates), _ZERO) / Decimal(
        len(placement.width_coordinates)
    )
    origin_length = sum((item.magnitude for item in placement.length_coordinates), _ZERO) / Decimal(
        len(placement.length_coordinates)
    )
    if placement.interface_id is ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG:
        origin_values = (_ZERO, origin_width, origin_length)
    else:
        origin_values = (request.hand.sign * origin_width, _ZERO, origin_length)
    frame = ExactInterfaceFrame(
        placement.interface_id.value,
        ExactQuantityVector3D(
            *(_quantity(item, request.source_length_unit) for item in origin_values)
        ),
        placement.width_axis,
        placement.length_axis,
        placement.normal_axis,
    )
    physical_force = _physical_hand_vector(request, request.global_force)
    physical_moment = _physical_hand_vector(request, request.global_moment)
    physical_reference = _physical_hand_vector(request, request.global_reference_point)
    force_u = _dot_force(physical_force, placement.width_axis, force_unit)
    force_v = _dot_force(physical_force, placement.length_axis, force_unit)
    force_n = _dot_force(physical_force, placement.normal_axis, force_unit)
    magnitude = (
        force_u.magnitude * force_u.magnitude + force_v.magnitude * force_v.magnitude
    ).sqrt()
    calculation_preview = (
        None if multirow_request is None else preview_multirow_connection(multirow_request)
    )
    geometry = _physical_geometry(
        placement,
        request,
        force_u,
        force_v,
        calculation_preview,
    )
    plan, applicability, qualification = _demand_plan(
        geometry,
        PhysicalQuantity.of(magnitude, force_unit),
    )
    zeros = ExactQuantityVector3D(*(PhysicalQuantity.of(_ZERO, moment_unit) for _ in range(3)))
    demand = calculate_eccentric_bolt_group_demand(
        EccentricDemandInput(
            _ACTION_ID,
            _CONNECTED_MEMBER_ID,
            _exact_vector(physical_force),
            _exact_vector(physical_moment),
            zeros,
            _exact_vector(physical_reference),
            frame,
            geometry,
            plan,
            applicability,
            qualification,
            (
                "STAGE_2_5A_DEMAND_ANALYSIS",
                "STAGE_3_3A_SINGLE_CANONICAL_ACTION",
                placement.interface_id.value,
            ),
        )
    )
    return demand, force_u, force_v, force_n


def _multirow_request(
    request: ClipAngleOrchestrationRequest,
    placement: ClipAngleInterfacePlacementTrace,
    layout: ClipAngleBoltLayout,
    force_u: PhysicalQuantity,
    force_v: PhysicalQuantity,
) -> MultiRowOrchestrationRequest | None:
    if force_u.magnitude == 0 and force_v.magnitude == 0:
        return None
    unit = request.source_length_unit
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_3_3A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    if placement.interface_id is ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG:
        layer_specs = (
            (
                "CLIP_ANGLE_INTERFACE_A_CONNECTED_MEMBER_LAYER",
                _CONNECTED_MEMBER_ID,
                _profile_thickness(request.connected_member_profile),
            ),
            (
                "CLIP_ANGLE_INTERFACE_A_CONNECTED_LEG_LAYER",
                _CONNECTOR_ID,
                request.connector_dimensions.thickness,
            ),
        )
    else:
        layer_specs = (
            (
                "CLIP_ANGLE_INTERFACE_B_SUPPORT_LEG_LAYER",
                _CONNECTOR_ID,
                request.connector_dimensions.thickness,
            ),
            (
                (
                    "CLIP_ANGLE_INTERFACE_B_SUPPORT_FLANGE_LAYER"
                    if request.support_target_id is None
                    else "CLIP_ANGLE_INTERFACE_B_SUPPORT_PROFILE_LAYER"
                ),
                _SUPPORT_ID,
                _support_layer_thickness(request),
            ),
        )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:{placement.interface_id.value}",
        f"stage-3-3a:{placement.interface_id.value}",
        placement.interface_id.value,
        _LOAD_ID,
        "Stage 3.3A canonical action resolved into this interface",
        request.unit_system,
        unit,
        layout.row_count,
        layout.bolts_per_row,
        request.bolt_diameter,
        request.hole_basis,
        _quantity(layout.pitch, unit),
        _quantity(layout.gauge, unit),
        _quantity(layout.negative_end_distance, unit),
        _quantity(layout.positive_end_distance, unit),
        _quantity(layout.heel_edge_distance, unit),
        _quantity(layout.free_edge_distance, unit),
        _quantity(Decimal("0.000000001"), unit),
        ConnectedMaterialPair.FRP_FRP,
        tuple(
            MultiRowLayerInput(
                layer_id,
                component_id,
                "ICE_LOCKED_PULTRUDED_FRP",
                _quantity(thickness, unit),
                PultrudedElementClassification.SHAPE,
                _ZERO,
                factors,
                ThreadStatus.EXCLUDED,
            )
            for layer_id, component_id, thickness in layer_specs
        ),
        force_u,
        force_v,
        "STAGE_3_3A_INTERFACE_LOCAL_TRANSFORM",
        RowDistributionBasis.ASCE_PRESCRIBED,
        None,
        (),
        MethodProvenance(
            "STAGE_3_3A_STAGE_2_5A_RESOLVED_DEMAND",
            "STAGE_3_3A_SINGLE_CLIP_ANGLE_ENGINEERING_SPECIFICATION_RC1",
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
        _quantity(_ZERO, unit),
        _quantity(Decimal("0.000000001"), unit),
        demand_source=MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND,
        single_row_geometry_preview_authorized=layout.row_count == 1,
    )


def _material_regions(
    request: ClipAngleOrchestrationRequest,
) -> tuple[ClipAngleMaterialRegionTrace, ...]:
    hand = request.hand.sign
    return (
        ClipAngleMaterialRegionTrace(
            "CLIP_ANGLE_CONNECTED_MEMBER_LEG_REGION",
            "CONNECTED_MEMBER_LEG",
            (_ZERO, _ZERO, hand),
            (_ZERO, Decimal(-1), _ZERO),
            (hand, _ZERO, _ZERO),
        ),
        ClipAngleMaterialRegionTrace(
            "CLIP_ANGLE_SUPPORT_LEG_REGION",
            "SUPPORT_LEG",
            (_ZERO, _ZERO, hand),
            (-hand, _ZERO, _ZERO),
            (_ZERO, Decimal(-1), _ZERO),
        ),
    )


_CLIP_ANGLE_MEMBER_CUT_PLANE_ID = "CLIP_ANGLE_CONNECTED_MEMBER_END_CUT_PLANE"


def _offset_point(
    point: PositionVector3D,
    direction: UnitVector3D,
    distance: float,
) -> PositionVector3D:
    return PositionVector3D(
        point.x + direction.x * distance,
        point.y + direction.y * distance,
        point.z + direction.z * distance,
    )


def _extended_trim_source(
    placed: PlacedComponentGeometry3D,
    cut_plane: AuthoritativeCutPlane3D,
) -> PlacedComponentGeometry3D:
    """Extend only the source end so a coincident cut still owns fabricated faces."""

    axial_projection = placed.global_frame.x_axis.dot(cut_plane.normal)
    if axial_projection <= 1e-9:
        raise ValueError("The connected member direction must cross the clip-angle cut plane.")
    start_points = tuple(
        physical.global_frame.local_to_parent_point(PositionVector3D(prism.extent.x_start, y, z))
        for physical in placed.physical_elements
        for prism in physical.extrusions
        if isinstance(prism, LocalRectangularPrism3D)
        for y in (prism.rectangle.min_y, prism.rectangle.max_y)
        for z in (prism.rectangle.min_z, prism.rectangle.max_z)
    )
    extension = max(
        0.0,
        max(signed_distance_to_plane(point, cut_plane) for point in start_points) / axial_projection
        + 1e-9,
    )
    remote = _offset_point(
        placed.global_frame.origin,
        placed.global_frame.x_axis,
        placed.extent.length,
    )
    source_start = _offset_point(
        placed.global_frame.origin,
        placed.global_frame.x_axis,
        -extension,
    )
    return place_member(
        cast(AssemblyMember, placed.component),
        placed.cross_section,
        source_start,
        remote,
        placed.global_frame.z_axis,
        placed.section_offset,
    )


def _box_vertices(
    value: ClipAngleBoxTrace,
    unit: Unit,
) -> tuple[PositionVector3D, ...]:
    center = tuple(float(item.to(unit).magnitude) for item in value.center)
    half = (
        float(value.size_s.to(unit).magnitude) / 2.0,
        float(value.size_p.to(unit).magnitude) / 2.0,
        float(value.size_l.to(unit).magnitude) / 2.0,
    )
    axes = tuple(tuple(float(component) for component in axis) for axis in value.basis)
    return tuple(
        PositionVector3D(
            center[0]
            + first * half[0] * axes[0][0]
            + second * half[1] * axes[1][0]
            + third * half[2] * axes[2][0],
            center[1]
            + first * half[0] * axes[0][1]
            + second * half[1] * axes[1][1]
            + third * half[2] * axes[2][1],
            center[2]
            + first * half[0] * axes[0][2]
            + second * half[1] * axes[1][2]
            + third * half[2] * axes[2][2],
        )
        for first in (-1.0, 1.0)
        for second in (-1.0, 1.0)
        for third in (-1.0, 1.0)
    )


def _point_delta(first: PositionVector3D, second: PositionVector3D) -> Vector3D:
    return Vector3D(first.x - second.x, first.y - second.y, first.z - second.z)


def _face_normal(points: tuple[PositionVector3D, ...]) -> Vector3D | None:
    first = points[0]
    for index in range(1, len(points) - 1):
        normal = _point_delta(points[index], first).cross(_point_delta(points[index + 1], first))
        if normal.norm > 1e-9:
            return normal.normalized()
    return None


def _solid_box_positive_overlap(
    solid: TrimmedPhysicalSolid3D,
    box: ClipAngleBoxTrace,
    unit: Unit,
) -> bool:
    """Apply the convex-polyhedron/OBB separating-axis test after trim."""

    solid_vertices = solid.vertices
    box_vertices = _box_vertices(box, unit)
    box_axes = tuple(Vector3D(*(float(component) for component in axis)) for axis in box.basis)
    solid_edges = tuple(
        _point_delta(face.vertices[(index + 1) % len(face.vertices)], face.vertices[index])
        for face in solid.faces
        for index in range(len(face.vertices))
    )
    face_normals = tuple(
        normal for face in solid.faces if (normal := _face_normal(face.vertices)) is not None
    )
    candidates = [*face_normals, *box_axes]
    candidates.extend(edge.cross(axis) for edge in solid_edges for axis in box_axes)
    for candidate in candidates:
        if candidate.norm <= 1e-9:
            continue
        axis = candidate.normalized()
        solid_projection = tuple(
            point.x * axis.x + point.y * axis.y + point.z * axis.z for point in solid_vertices
        )
        box_projection = tuple(
            point.x * axis.x + point.y * axis.y + point.z * axis.z for point in box_vertices
        )
        overlap = min(max(solid_projection), max(box_projection)) - max(
            min(solid_projection), min(box_projection)
        )
        if overlap <= 1e-9:
            return False
    return True


def _trim(
    request: ClipAngleOrchestrationRequest,
    placed_profile: PlacedComponentGeometry3D,
    boxes: tuple[ClipAngleBoxTrace, ...],
    interface_a_bolts: tuple[ClipAngleBoltTrace, ...],
) -> tuple[ClipAngleTrimTrace, TrimmedComponentSolids3D | None]:
    unit = request.source_length_unit
    reference_origin_quantities = (
        _quantity(_ZERO, unit),
        _quantity(request.connector_dimensions.thickness, unit),
        _quantity(_ZERO, unit),
    )
    reference_origin = PositionVector3D(
        0.0,
        float(request.connector_dimensions.thickness),
        0.0,
    )
    normal = UnitVector3D(0.0, 1.0, 0.0)
    contact_clear = _profile_contact_is_clear(request, boxes)
    if not request.connected_member_end_trim_enabled:
        interference = not contact_clear or (
            request.connected_member_inclination_degrees != 0
            and request.connected_member_profile.family is not MemberProfileFamily.FLAT_PLATE
        )
        return (
            ClipAngleTrimTrace(
                False,
                CLIP_ANGLE_TRIM_PLANE_ID,
                reference_origin_quantities,
                (_ZERO, _ONE, _ZERO),
                None,
                None,
                None,
                None,
                (
                    ClipAngleInterferenceStatus.INTERFERENCE_DETECTED
                    if interference
                    else ClipAngleInterferenceStatus.CLEAR
                ),
                not interference,
                None,
                (),
                None,
                (),
                None,
                None,
                None,
                None,
            ),
            None,
        )

    clearance = cast(PhysicalQuantity, request.connected_member_end_clearance).to(unit)
    cut_origin_quantities = (
        _quantity(_ZERO, unit),
        _quantity(request.connector_dimensions.thickness + clearance.magnitude, unit),
        _quantity(_ZERO, unit),
    )
    cut_plane = AuthoritativeCutPlane3D(
        _CLIP_ANGLE_MEMBER_CUT_PLANE_ID,
        _offset_point(reference_origin, normal, float(clearance.magnitude)),
        normal,
    )
    trimmed = trim_placed_rectangular_component(
        _extended_trim_source(placed_profile, cut_plane),
        cut_plane,
    )
    connected_leg = next(item for item in boxes if item.id == "clip-angle-connected-leg-solid")
    support_leg = next(item for item in boxes if item.id == "clip-angle-support-leg-solid")
    remaining_interference = any(
        _solid_box_positive_overlap(solid, obstruction, unit)
        for solid in trimmed.solids
        for obstruction in (connected_leg, support_leg)
    )
    _outside_id, _opposing_ids, selected_element = kernel_profile_surface_patch_ids(
        request.connected_member_profile
    )
    selected_edges = tuple(
        edge_id
        for edge_id in trimmed.fabricated_face_ids
        if edge_id.startswith(f"{selected_element}:")
    )
    governing_edge = selected_edges[0] if selected_edges else trimmed.fabricated_face_ids[0]
    hole_radius = request.hole_diameter.to(unit).magnitude / _TWO
    bolt_clearances = tuple(
        ClipAngleTrimBoltClearanceTrace(
            bolt.bolt_id,
            _quantity(
                bolt.global_center[1].to(unit).magnitude - cut_origin_quantities[1].magnitude,
                unit,
            ),
            _quantity(
                bolt.global_center[1].to(unit).magnitude
                - cut_origin_quantities[1].magnitude
                - hole_radius,
                unit,
            ),
            governing_edge,
        )
        for bolt in interface_a_bolts
    )
    governing = min(
        bolt_clearances,
        key=lambda item: (item.hole_edge_to_trim_edge.magnitude, item.bolt_id),
    )
    minimum = governing.hole_edge_to_trim_edge
    deficit = _quantity(-minimum.magnitude, unit) if minimum.magnitude < 0 else None
    geometry_valid = not remaining_interference and deficit is None
    return (
        ClipAngleTrimTrace(
            True,
            CLIP_ANGLE_TRIM_PLANE_ID,
            reference_origin_quantities,
            (_ZERO, _ONE, _ZERO),
            cut_plane.id,
            cut_origin_quantities,
            (_ZERO, _ONE, _ZERO),
            clearance,
            (
                ClipAngleInterferenceStatus.REMAINING_INTERFERENCE
                if remaining_interference
                else ClipAngleInterferenceStatus.TRIMMED_CLEAR
            ),
            geometry_valid,
            trimmed.geometry_fingerprint,
            trimmed.fabricated_face_ids,
            governing_edge,
            bolt_clearances,
            governing.bolt_id,
            governing.trim_edge_id,
            minimum,
            deficit,
        ),
        trimmed,
    )


def _vector_decimals(value: UnitVector3D) -> tuple[Decimal, Decimal, Decimal]:
    return (
        decimal_from_finite_real(value.x),
        decimal_from_finite_real(value.y),
        decimal_from_finite_real(value.z),
    )


def _point_quantities(
    value: PositionVector3D,
    unit: Unit,
) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    return (
        _quantity(decimal_from_finite_real(value.x), unit),
        _quantity(decimal_from_finite_real(value.y), unit),
        _quantity(decimal_from_finite_real(value.z), unit),
    )


def _quantity_point(
    value: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
    unit: Unit,
) -> PositionVector3D:
    return PositionVector3D(*(float(item.to(unit).magnitude) for item in value))


def _rectangular_local_uv(
    profile: MemberProfile,
    placed: PlacedComponentGeometry3D,
    point: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
    unit: Unit,
) -> tuple[Decimal, Decimal]:
    local = placed.global_to_local(_quantity_point(point, unit))
    surface = require_direct_tee_profile_surface(profile)
    second = local.z if surface.plane_axis is PrincipalAxisFamily.Y else local.y
    return (
        decimal_from_finite_real(local.x) - profile.dimensions.member_length / Decimal(2),
        decimal_from_finite_real(second),
    )


def _profile_placement_axes(
    request: ClipAngleOrchestrationRequest,
) -> tuple[UnitVector3D, UnitVector3D, UnitVector3D]:
    inclination = request.connected_member_inclination_degrees
    if inclination == 0:
        sine, cosine = 0.0, 1.0
    else:
        sine, cosine = deterministic_sine_cosine_degrees(inclination)
    hand = float(request.hand.sign)
    member_longitudinal = UnitVector3D(0.0, cosine, hand * sine)
    in_plane_up = UnitVector3D(0.0, -sine, hand * cosine)
    contact_transverse = UnitVector3D(hand, 0.0, 0.0)
    return member_longitudinal, in_plane_up, contact_transverse


def _placed_connected_profile(
    request: ClipAngleOrchestrationRequest,
) -> PlacedComponentGeometry3D:
    profile = request.connected_member_profile
    topology = create_oriented_standard_topology(profile.section_family)
    member = AssemblyMember(
        _CONNECTED_MEMBER_ID,
        f"Pultruded FRP connected {profile.role.value.lower()} {profile.family.value}",
        profile.role,
        MemberEnd.START,
        profile.section_family,
        ComponentMaterialKind.PULTRUDED_FRP,
        cast(FRPComponentOrientation, profile.material_orientation),
        topology,
    )
    cross_section = create_member_profile_cross_section(profile, topology)
    adapter = profile_section_geometry_adapter(profile)
    member_longitudinal, in_plane_up, contact_transverse = _profile_placement_axes(request)
    local_z = resolve_profile_local_z_reference(
        profile,
        in_plane_up,
        contact_transverse,
        member_longitudinal,
    )
    section_offset = SectionDatumOffset(
        float(adapter.section_datum_offset_y),
        float(adapter.section_datum_offset_z),
    )
    start = PositionVector3D(0.0, float(request.connector_dimensions.thickness), 0.0)
    member_length = float(adapter.member_length)
    end = PositionVector3D(
        start.x + member_longitudinal.x * member_length,
        start.y + member_longitudinal.y * member_length,
        start.z + member_longitudinal.z * member_length,
    )
    provisional = place_member(member, cross_section, start, end, local_z, section_offset)
    selected_patch_id, _opposing_ids, _element_id = kernel_profile_surface_patch_ids(profile)
    selected_patches = tuple(
        patch
        for patch in create_component_surface_set(provisional).patches
        if patch.id == selected_patch_id
    )
    if len(selected_patches) != 1:
        raise ValueError("Selected connected-profile surface did not resolve uniquely.")
    geometry = selected_patches[0].geometry
    if not isinstance(geometry, PlanarRectangularSurface3D):
        raise TypeError("Connected clip-angle profile requires one planar selected surface.")
    if geometry.normal.dot(contact_transverse) < 1.0 - 1e-12:
        if geometry.normal.dot(contact_transverse) > -1.0 + 1e-12:
            raise ValueError("Selected connected-profile surface is not contact-parallel.")
        local_z = UnitVector3D(-local_z.x, -local_z.y, -local_z.z)
        provisional = place_member(member, cross_section, start, end, local_z, section_offset)
        selected_patches = tuple(
            patch
            for patch in create_component_surface_set(provisional).patches
            if patch.id == selected_patch_id
        )
        if len(selected_patches) != 1:
            raise ValueError("Reoriented connected-profile surface did not resolve uniquely.")
        geometry = selected_patches[0].geometry
        if not isinstance(geometry, PlanarRectangularSurface3D):
            raise TypeError("Reoriented connected-profile surface must remain planar.")
        if geometry.normal.dot(contact_transverse) < 1.0 - 1e-12:
            raise ValueError("Selected connected-profile surface cannot face the clip angle.")
    target = PositionVector3D(
        start.x + member_longitudinal.x * member_length / 2.0,
        start.y + member_longitudinal.y * member_length / 2.0,
        start.z + member_longitudinal.z * member_length / 2.0,
    )
    shift = (
        target.x - geometry.center.x,
        target.y - geometry.center.y,
        target.z - geometry.center.z,
    )
    placed = place_member(
        member,
        cross_section,
        PositionVector3D(start.x + shift[0], start.y + shift[1], start.z + shift[2]),
        PositionVector3D(end.x + shift[0], end.y + shift[1], end.z + shift[2]),
        local_z,
        section_offset,
    )
    final_patches = tuple(
        patch
        for patch in create_component_surface_set(placed).patches
        if patch.id == selected_patch_id
    )
    if len(final_patches) != 1:
        raise ValueError("Placed connected-profile surface did not resolve uniquely.")
    final_geometry = final_patches[0].geometry
    if not isinstance(final_geometry, PlanarRectangularSurface3D):
        raise TypeError("Placed connected-profile surface must remain planar.")
    if final_geometry.normal.dot(contact_transverse) < 1.0 - 1e-12:
        raise ValueError("Selected connected-profile surface does not face the clip angle.")
    return placed


def _placed_support_profile(
    request: ClipAngleOrchestrationRequest,
    profile: MemberProfile,
) -> PlacedComponentGeometry3D:
    """Place the selected support face at the backend clip-angle contact datum."""

    target_id, _ = _support_selection(request)
    longitudinal = (
        UnitVector3D(1.0, 0.0, 0.0)
        if target_id is SharedSupportTargetId.W_BEAM_FLANGE
        else UnitVector3D(0.0, 0.0, 1.0)
    )
    in_plane_up = (
        UnitVector3D(0.0, 0.0, 1.0)
        if target_id is SharedSupportTargetId.W_BEAM_FLANGE
        else UnitVector3D(1.0, 0.0, 0.0)
    )
    contact_normal = UnitVector3D(0.0, 1.0, 0.0)
    topology = create_oriented_standard_topology(profile.section_family)
    member = AssemblyMember(
        _SUPPORT_ID,
        f"Pultruded FRP support {profile.family.value}",
        profile.role,
        MemberEnd.START,
        profile.section_family,
        ComponentMaterialKind.PULTRUDED_FRP,
        cast(FRPComponentOrientation, profile.material_orientation),
        topology,
    )
    cross_section = create_member_profile_cross_section(profile, topology)
    adapter = profile_section_geometry_adapter(profile)
    local_z = resolve_profile_local_z_reference(
        profile,
        in_plane_up,
        contact_normal,
        longitudinal,
    )
    half = float(adapter.member_length) / 2.0
    start = PositionVector3D(
        -longitudinal.x * half,
        -longitudinal.y * half,
        -longitudinal.z * half,
    )
    end = PositionVector3D(
        longitudinal.x * half,
        longitudinal.y * half,
        longitudinal.z * half,
    )
    offset = SectionDatumOffset(
        float(adapter.section_datum_offset_y),
        float(adapter.section_datum_offset_z),
    )
    provisional = place_member(member, cross_section, start, end, local_z, offset)
    selected_id, _opposing_ids, _element_id = kernel_profile_surface_patch_ids(profile)
    patches = tuple(
        item for item in create_component_surface_set(provisional).patches if item.id == selected_id
    )
    if len(patches) != 1 or not isinstance(  # pragma: no cover - section kernel contract
        patches[0].geometry, PlanarRectangularSurface3D
    ):
        raise ValueError("Selected support surface did not resolve uniquely.")
    surface = patches[0].geometry
    if surface.normal.dot(contact_normal) < 1.0 - 1e-12:
        local_z = UnitVector3D(-local_z.x, -local_z.y, -local_z.z)
        provisional = place_member(member, cross_section, start, end, local_z, offset)
        patches = tuple(
            item
            for item in create_component_surface_set(provisional).patches
            if item.id == selected_id
        )
        if len(patches) != 1 or not isinstance(
            patches[0].geometry,
            PlanarRectangularSurface3D,
        ):  # pragma: no cover - section kernel contract
            raise ValueError("Reoriented support surface did not resolve uniquely.")
        surface = patches[0].geometry
        if (  # pragma: no cover - exact rigid reversal guarantees the selected face
            surface.normal.dot(contact_normal) < 1.0 - 1e-12
        ):
            raise ValueError("Selected support exterior face must face the clip angle.")
    shift = Vector3D(-surface.center.x, -surface.center.y, -surface.center.z)
    return place_member(
        member,
        cross_section,
        PositionVector3D(start.x + shift.x, start.y + shift.y, start.z + shift.z),
        PositionVector3D(end.x + shift.x, end.y + shift.y, end.z + shift.z),
        local_z,
        offset,
    )


def _profile_visualization(
    request: ClipAngleOrchestrationRequest,
    placed: PlacedComponentGeometry3D | None = None,
) -> tuple[tuple[ClipAngleBoxTrace, ...], tuple[ClipAngleProfileMaterialRegionTrace, ...]]:
    unit = request.source_length_unit
    placed = _placed_connected_profile(request) if placed is None else placed
    _components, primitives, directions = build_placed_component_visualization_snapshots((placed,))

    def parameter(primitive: VisualizationPrimitive, name: str) -> Decimal:
        matches = tuple(item.value for item in primitive.parameters if item.name == name)
        if len(matches) != 1:
            raise ValueError(f"Connected-profile primitive lacks exact {name}.")
        return decimal_from_finite_real(matches[0])

    boxes: list[ClipAngleBoxTrace] = []
    for primitive in primitives:
        if primitive.kind is not VisualizationPrimitiveKind.BOX:
            continue
        if (
            primitive.center is None
            or primitive.x_axis is None
            or primitive.y_axis is None
            or primitive.z_axis is None
            or primitive.physical_element_id is None
            or primitive.material_region_id is None
        ):
            raise ValueError("Connected-profile box lacks exact physical ownership or placement.")
        boxes.append(
            ClipAngleBoxTrace(
                primitive.id,
                primitive.owner_id,
                primitive.physical_element_id,
                _point_quantities(primitive.center, unit),
                _quantity(parameter(primitive, "x_end") - parameter(primitive, "x_start"), unit),
                _quantity(parameter(primitive, "max_y") - parameter(primitive, "min_y"), unit),
                _quantity(parameter(primitive, "max_z") - parameter(primitive, "min_z"), unit),
                primitive.physical_element_id,
                primitive.material_region_id,
                (
                    _vector_decimals(primitive.x_axis),
                    _vector_decimals(primitive.y_axis),
                    _vector_decimals(primitive.z_axis),
                ),
            )
        )

    material_regions: list[ClipAngleProfileMaterialRegionTrace] = []
    for direction in directions:
        material_regions.append(_profile_material_region_trace(direction, unit))
    return tuple(boxes), tuple(material_regions)


def _trimmed_profile_meshes(
    trimmed: TrimmedComponentSolids3D | None,
    unit: Unit,
) -> tuple[ClipAngleTriangleMeshTrace, ...]:
    if trimmed is None:
        return ()
    return tuple(
        ClipAngleTriangleMeshTrace(
            f"TRIMMED:MEMBER:{trimmed.component_id}:{solid.physical_element_id}:{index}",
            trimmed.component_id,
            solid.physical_element_id,
            solid.physical_element_id,
            solid.material_region_id,
            tuple(_point_quantities(point, unit) for point in solid.triangulated_points),
        )
        for index, solid in enumerate(trimmed.solids)
    )


def _profile_material_region_trace(
    direction: MaterialDirectionSet,
    unit: Unit,
) -> ClipAngleProfileMaterialRegionTrace:
    if (
        direction.lengthwise is None
        or direction.crosswise is None
        or direction.through_thickness is None
    ):
        raise ValueError("Pultruded connected-profile regions require exact material axes.")
    return ClipAngleProfileMaterialRegionTrace(
        direction.id,
        direction.physical_element_id,
        direction.material_region_id,
        _point_quantities(direction.origin, unit),
        _vector_decimals(direction.lengthwise),
        _vector_decimals(direction.crosswise),
        _vector_decimals(direction.through_thickness),
    )


def _dot_decimal(
    first: tuple[Decimal, Decimal, Decimal],
    second: tuple[Decimal, Decimal, Decimal],
) -> Decimal:
    return sum((left * right for left, right in zip(first, second, strict=True)), _ZERO)


def _cross_decimal(
    first: tuple[Decimal, Decimal, Decimal],
    second: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _box_geometry(
    value: ClipAngleBoxTrace,
    unit: Unit,
) -> tuple[
    tuple[Decimal, Decimal, Decimal],
    tuple[tuple[Decimal, Decimal, Decimal], ...],
    tuple[Decimal, Decimal, Decimal],
]:
    center = value.center
    return (
        (
            center[0].to(unit).magnitude,
            center[1].to(unit).magnitude,
            center[2].to(unit).magnitude,
        ),
        value.basis,
        (
            value.size_s.to(unit).magnitude / _TWO,
            value.size_p.to(unit).magnitude / _TWO,
            value.size_l.to(unit).magnitude / _TWO,
        ),
    )


def _boxes_have_positive_volume_overlap(
    first: ClipAngleBoxTrace,
    second: ClipAngleBoxTrace,
    unit: Unit,
) -> bool:
    """Classify exact positive-volume overlap for two backend-authored boxes."""

    # Profile placement is authored through the geometry kernel's IEEE-754
    # coordinates before it is serialized back into Decimal quantities.  Use
    # one physical comparison tolerance in every source unit so contact is not
    # misclassified as penetration solely because, for example, 0.5 in is
    # returned as 12.700000000000006 mm.  This does not alter or quantize the
    # production geometry.
    overlap_tolerance = _quantity(Decimal("1e-9"), Unit.IN).to(unit).magnitude
    first_center, first_axes, first_half = _box_geometry(first, unit)
    second_center, second_axes, second_half = _box_geometry(second, unit)
    center_delta = (
        second_center[0] - first_center[0],
        second_center[1] - first_center[1],
        second_center[2] - first_center[2],
    )
    candidates = [*first_axes, *second_axes]
    candidates.extend(
        _cross_decimal(first_axis, second_axis)
        for first_axis in first_axes
        for second_axis in second_axes
    )
    for candidate in candidates:
        if candidate == (_ZERO, _ZERO, _ZERO):
            continue
        first_radius = sum(
            (
                half * abs(_dot_decimal(source_axis, candidate))
                for half, source_axis in zip(first_half, first_axes, strict=True)
            ),
            _ZERO,
        )
        second_radius = sum(
            (
                half * abs(_dot_decimal(source_axis, candidate))
                for half, source_axis in zip(second_half, second_axes, strict=True)
            ),
            _ZERO,
        )
        if (
            first_radius + second_radius - abs(_dot_decimal(center_delta, candidate))
            <= overlap_tolerance
        ):
            return False
    return True


def _profile_contact_is_clear(
    request: ClipAngleOrchestrationRequest,
    boxes: tuple[ClipAngleBoxTrace, ...],
) -> bool:
    """Require surface contact without positive-volume member/connector overlap."""

    profile_boxes = tuple(item for item in boxes if item.owner_id == _CONNECTED_MEMBER_ID)
    connected_leg = next(item for item in boxes if item.id == "clip-angle-connected-leg-solid")
    support_leg = next(item for item in boxes if item.id == "clip-angle-support-leg-solid")
    if any(
        _boxes_have_positive_volume_overlap(item, connected_leg, request.source_length_unit)
        for item in profile_boxes
    ):
        return False
    return not any(
        _boxes_have_positive_volume_overlap(item, support_leg, request.source_length_unit)
        for item in profile_boxes
    )


def _boxes(
    request: ClipAngleOrchestrationRequest,
    center: Decimal,
    profile_boxes: tuple[ClipAngleBoxTrace, ...],
    support_profile_boxes: tuple[ClipAngleBoxTrace, ...] = (),
) -> tuple[ClipAngleBoxTrace, ...]:
    unit = request.source_length_unit
    dims = request.connector_dimensions
    support = request.support_dimensions
    hand = request.hand.sign
    support_s = (
        support.flange_width
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else support.member_length
    )
    support_l = (
        support.member_length
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else support.flange_width
    )
    web_s = (
        support.web_thickness
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else support.member_length
    )
    web_l = (
        support.member_length
        if request.support_role is ClipAngleSupportRole.W_COLUMN_FLANGE
        else support.web_thickness
    )
    connector_boxes = (
        ClipAngleBoxTrace(
            "clip-angle-connected-leg-solid",
            _CONNECTOR_ID,
            "CONNECTED_MEMBER_LEG",
            (
                _quantity(hand * dims.thickness / _TWO, unit),
                _quantity(dims.connected_leg_width / _TWO, unit),
                _quantity(hand * center, unit),
            ),
            _quantity(dims.thickness, unit),
            _quantity(dims.connected_leg_width, unit),
            _quantity(dims.connector_length, unit),
        ),
        ClipAngleBoxTrace(
            "clip-angle-support-leg-solid",
            _CONNECTOR_ID,
            "SUPPORT_LEG",
            (
                _quantity(hand * dims.support_leg_width / _TWO, unit),
                _quantity(dims.thickness / _TWO, unit),
                _quantity(hand * center, unit),
            ),
            _quantity(dims.support_leg_width, unit),
            _quantity(dims.thickness, unit),
            _quantity(dims.connector_length, unit),
        ),
    )
    if request.support_target_id is not None:
        return (*connector_boxes, *support_profile_boxes, *profile_boxes)
    return (
        *connector_boxes,
        ClipAngleBoxTrace(
            "clip-angle-support-selected-flange",
            _SUPPORT_ID,
            "SELECTED_W_FLANGE",
            (
                _quantity(_ZERO, unit),
                _quantity(-support.flange_thickness / _TWO, unit),
                _quantity(_ZERO, unit),
            ),
            _quantity(support_s, unit),
            _quantity(support.flange_thickness, unit),
            _quantity(support_l, unit),
        ),
        ClipAngleBoxTrace(
            "clip-angle-support-web",
            _SUPPORT_ID,
            "W_WEB",
            (
                _quantity(_ZERO, unit),
                _quantity(-support.overall_depth / _TWO, unit),
                _quantity(_ZERO, unit),
            ),
            _quantity(web_s, unit),
            _quantity(support.overall_depth - _TWO * support.flange_thickness, unit),
            _quantity(web_l, unit),
        ),
        ClipAngleBoxTrace(
            "clip-angle-support-opposite-flange",
            _SUPPORT_ID,
            "OPPOSITE_W_FLANGE",
            (
                _quantity(_ZERO, unit),
                _quantity(-support.overall_depth + support.flange_thickness / _TWO, unit),
                _quantity(_ZERO, unit),
            ),
            _quantity(support_s, unit),
            _quantity(support.flange_thickness, unit),
            _quantity(support_l, unit),
        ),
        *profile_boxes,
    )


def _input_fingerprint(request: ClipAngleOrchestrationRequest) -> str:
    profile = request.connected_member_profile
    return _fingerprint(
        (
            CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION,
            request.hand,
            request.support_role,
            request.selected_support_flange,
            _length_fields(request.connector_dimensions, request.source_length_unit),
            _length_fields(request.support_dimensions, request.source_length_unit),
            *(
                (
                    request.support_target_id,
                    cast(MemberProfile, request.support_profile).role,
                    cast(MemberProfile, request.support_profile).family,
                    _length_fields(
                        cast(MemberProfile, request.support_profile).dimensions,
                        request.source_length_unit,
                    ),
                    cast(MemberProfile, request.support_profile).orientation,
                    cast(MemberProfile, request.support_profile).selected_surface,
                )
                if request.support_target_id
                not in {
                    None,
                    SharedSupportTargetId.W_COLUMN_FLANGE,
                    SharedSupportTargetId.W_BEAM_FLANGE,
                }
                else ()
            ),
            profile.role,
            profile.family,
            _length_fields(profile.dimensions, request.source_length_unit),
            profile.orientation,
            profile.selected_surface,
            _layout_fingerprint_value(request.interface_a_layout, request.source_length_unit),
            _layout_fingerprint_value(request.interface_b_layout, request.source_length_unit),
            request.bolt_diameter,
            request.hole_diameter,
            _physical_hand_vector(request, request.global_force),
            _physical_hand_vector(request, request.global_moment),
            _physical_hand_vector(request, request.global_reference_point),
            request.connected_member_inclination_degrees,
            request.connected_member_end_trim_enabled,
            request.connected_member_end_clearance,
            request.connector_length_anchor,
            request.connector_length_anchor_position,
            "ICE_LOCKED_PULTRUDED_FRP:RC2",
            "ASTM_F593_17_GROUP_2_316_316L",
            "2.5A-RC1",
            "2.5B-RC1",
            "2.6A-RC1",
            "2.4B-RC2",
        )
    )


def _resolve_interface(
    request: ClipAngleOrchestrationRequest,
    placement: ClipAngleInterfacePlacementTrace,
    layout: ClipAngleBoltLayout,
) -> ClipAngleInterfaceResult:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    force_u = _dot_force(request.global_force, placement.width_axis, force_unit)
    force_v = _dot_force(request.global_force, placement.length_axis, force_unit)
    multirow_request = _multirow_request(request, placement, layout, force_u, force_v)
    demand, _, _, force_n = _demand(request, placement, multirow_request)
    normal = PhysicalQuantity.of(abs(force_n.magnitude), force_n.unit)
    physical_name = (
        "Connected Member ↔ Clip-Angle Connected Leg"
        if placement.interface_id is ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG
        else "Clip-Angle Support Leg ↔ Support"
    )
    return ClipAngleInterfaceResult(
        placement.interface_id,
        physical_name,
        placement.bolt_group_id,
        normal,
        normal.magnitude == 0,
        False,
        False,
        demand,
        None,
        placement,
        _fingerprint((placement.geometry_fingerprint, demand.input_fingerprint)),
    )


def _with_resistance(
    request: ClipAngleOrchestrationRequest,
    result: ClipAngleInterfaceResult,
    layout: ClipAngleBoltLayout,
) -> ClipAngleInterfaceResult:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    force_u = _dot_force(request.global_force, result.placement.width_axis, force_unit)
    force_v = _dot_force(request.global_force, result.placement.length_axis, force_unit)
    multirow_request = _multirow_request(request, result.placement, layout, force_u, force_v)
    resistance = (
        None
        if multirow_request is None
        else evaluate_multirow_connection_with_resolved_demand(multirow_request, result.demand)
    )
    return replace(result, resistance=resistance)


def _interface_design_ready(result: ClipAngleInterfaceResult) -> bool:
    return (
        result.normal_action_supported
        and result.demand.availability is DemandAnalysisAvailability.CALCULATED
        and result.demand.method_applicability is MultiRowMethodApplicability.ASCE_PRESCRIPTIVE
        and result.demand.qualification is QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE
    )


def _supported_failure(result: ClipAngleInterfaceResult) -> bool:
    resistance = result.resistance
    if resistance is None:
        return False
    integration = resistance.automatic_group_mode_integration
    if integration is not None:
        return integration.overall_disposition is MultiRowOverallDisposition.FAIL
    calculation = resistance.calculation_result
    return (
        calculation is not None
        and calculation.overall_disposition is MultiRowOverallDisposition.FAIL
    )


def _preview(
    request: ClipAngleOrchestrationRequest,
    *,
    resistance: bool,
) -> ClipAnglePreviewResult:
    selected, center, positive_end, negative_end = _anchor_coordinates(request)
    longitudinal = ClipAngleLongitudinalPlacementTrace(
        "CLIP_ANGLE_TEMPLATE_LONGITUDINAL_DATUM",
        request.connector_length_anchor,
        _quantity(selected, request.source_length_unit),
        _quantity(center, request.source_length_unit),
        _quantity(positive_end, request.source_length_unit),
        _quantity(negative_end, request.source_length_unit),
        _fingerprint(
            (
                _length_fields(request.connector_dimensions, request.source_length_unit),
                request.hand,
                _quantity(center, request.source_length_unit),
            )
        ),
    )
    placement_a = _placement(
        request,
        ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG,
        request.interface_a_layout,
        request.connector_dimensions.connected_leg_width,
        positive_end,
        negative_end,
    )
    placement_b = _placement(
        request,
        ClipAngleInterfaceIdentity.SUPPORT_LEG_TO_SUPPORT,
        request.interface_b_layout,
        request.connector_dimensions.support_leg_width,
        positive_end,
        negative_end,
    )
    interface_a = _resolve_interface(request, placement_a, request.interface_a_layout)
    interface_b = _resolve_interface(request, placement_b, request.interface_b_layout)
    placed_profile = _placed_connected_profile(request)
    profile_boxes, profile_material_regions = _profile_visualization(request, placed_profile)
    support_target_id, support_profile = _support_selection(request)
    placed_support_profile = _placed_support_profile(request, support_profile)
    support_profile_boxes, support_material_regions = _profile_visualization(
        request,
        placed_support_profile,
    )
    source_boxes = _boxes(
        request,
        center,
        profile_boxes,
        support_profile_boxes,
    )
    rectangular_paths: list[IntegratedFullThroughBoltTrace] = []
    if request.connected_member_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        rectangular_paths.extend(
            build_integrated_full_through_bolt(
                request.connected_member_profile,
                placed_profile=placed_profile,
                selected_surface=cast(
                    MemberProfileSurfaceId,
                    request.connected_member_profile.selected_surface,
                ),
                bolt_id=item.bolt_id,
                local_uv=_rectangular_local_uv(
                    request.connected_member_profile,
                    placed_profile,
                    item.global_center,
                    request.source_length_unit,
                ),
                hole_radius=request.hole_diameter.to(request.source_length_unit).magnitude / _TWO,
                connector_identity="CLIP_ANGLE_CONNECTED_LEG",
                connector_thickness=request.connector_dimensions.thickness,
                connector_material_region_id="CLIP_ANGLE_CONNECTED_LEG_REGION",
                rectangular_material_region_id="CONNECTED_RECTANGULAR_PROFILE_REGION",
                source_length_unit=request.source_length_unit,
            )
            for item in placement_a.bolts
        )
    if support_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        rectangular_paths.extend(
            build_integrated_full_through_bolt(
                support_profile,
                placed_profile=placed_support_profile,
                selected_surface=cast(MemberProfileSurfaceId, support_profile.selected_surface),
                bolt_id=item.bolt_id,
                local_uv=(
                    item.length_coordinate.to(request.source_length_unit).magnitude,
                    item.width_coordinate.to(request.source_length_unit).magnitude,
                ),
                hole_radius=request.hole_diameter.to(request.source_length_unit).magnitude / _TWO,
                connector_identity="CLIP_ANGLE_SUPPORT_LEG",
                connector_thickness=request.connector_dimensions.thickness,
                connector_material_region_id="CLIP_ANGLE_SUPPORT_LEG_REGION",
                rectangular_material_region_id="SUPPORT_RECTANGULAR_PROFILE_REGION",
                source_length_unit=request.source_length_unit,
            )
            for item in placement_b.bolts
        )
    trim, trimmed_profile = _trim(
        request,
        placed_profile,
        source_boxes,
        placement_a.bolts,
    )
    visualization_boxes = (
        tuple(item for item in source_boxes if item.owner_id != _CONNECTED_MEMBER_ID)
        if trimmed_profile is not None
        else source_boxes
    )
    visualization_meshes = _trimmed_profile_meshes(trimmed_profile, request.source_length_unit)
    valid = (
        placement_a.clearances.geometry_valid
        and placement_b.clearances.geometry_valid
        and trim.geometry_valid
        and all(item.geometry_valid for item in rectangular_paths)
    )
    design_ready = (
        valid
        and not rectangular_paths
        and all(_interface_design_ready(result) for result in (interface_a, interface_b))
    )
    resistance_evaluated = resistance and design_ready
    if resistance_evaluated:
        interface_a = _with_resistance(request, interface_a, request.interface_a_layout)
        interface_b = _with_resistance(request, interface_b, request.interface_b_layout)
    supported_failure = _supported_failure(interface_a) or _supported_failure(interface_b)
    status = (
        ClipAngleAssemblyStatus.INVALID_GEOMETRY
        if not valid
        else (
            ClipAngleAssemblyStatus.FAIL
            if supported_failure
            else ClipAngleAssemblyStatus.NOT_EVALUATED
        )
    )
    geometry_invalid_reasons: list[str] = []
    if not placement_a.clearances.geometry_valid:
        geometry_invalid_reasons.append("INTERFACE_A_COMPLETE_HOLE_CONTAINMENT_INVALID")
    if not placement_b.clearances.geometry_valid:
        geometry_invalid_reasons.append("INTERFACE_B_COMPLETE_HOLE_CONTAINMENT_INVALID")
    if not trim.geometry_valid:
        if trim.interference_status in {
            ClipAngleInterferenceStatus.INTERFERENCE_DETECTED,
            ClipAngleInterferenceStatus.REMAINING_INTERFERENCE,
        }:
            geometry_invalid_reasons.append("CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE")
        if trim.exact_deficit is not None:
            geometry_invalid_reasons.append("HOLE_EDGE_CLEARANCE_TO_FABRICATED_END_IS_NEGATIVE")
    if any(not item.geometry_valid for item in rectangular_paths):
        geometry_invalid_reasons.append("RECTANGULAR_OPPOSING_FACE_HOLE_CONTAINMENT_INVALID")
    warnings = [
        "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED",
        *geometry_invalid_reasons,
    ]
    limitations = tuple(
        dict.fromkeys(
            limitation.value for item in rectangular_paths for limitation in item.limitations
        )
    )
    warnings.extend(f"{item}:NOT_EVALUATED" for item in limitations)
    for result in (interface_a, interface_b):
        if not result.normal_action_supported:
            warnings.append(f"{result.interface_id.value}:INTERFACE_NORMAL_ACTION_NOT_SUPPORTED")
        if result.demand.availability is not DemandAnalysisAvailability.CALCULATED:
            warnings.append(f"{result.interface_id.value}:DEMAND_CALCULATION_NOT_SUPPORTED")
    material_regions = _material_regions(request)
    canonical_input = _input_fingerprint(request)
    connector_geometry = _fingerprint(
        (
            longitudinal.body_geometry_fingerprint,
            placement_a.geometry_fingerprint,
            placement_b.geometry_fingerprint,
        )
    )
    engineering = _fingerprint(
        (
            canonical_input,
            connector_geometry,
            interface_a.interface_fingerprint,
            interface_b.interface_fingerprint,
            *(item.path_fingerprint for item in rectangular_paths),
        )
    )
    visualization = None
    if valid:
        connected_surface = cast(
            MemberProfileSurfaceId,
            request.connected_member_profile.selected_surface,
        )
        visualization = ClipAngleVisualizationSnapshot(
            CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION,
            ClipAngleSemanticFrameTrace(
                (request.hand.sign, _ZERO, _ZERO),
                (_ZERO, _ONE, _ZERO),
                (_ZERO, _ZERO, request.hand.sign),
            ),
            request.connected_member_profile.id,
            request.connected_member_profile.role,
            request.connected_member_profile.family,
            request.connected_member_profile.orientation,
            visualization_boxes,
            visualization_meshes,
            placement_a.bolts,
            placement_b.bolts,
            request.bolt_diameter,
            request.hole_diameter,
            material_regions,
            profile_material_regions,
            f"{_SUPPORT_ID}:{request.selected_support_flange.value}",
            f"{_CONNECTED_MEMBER_ID}:{connected_surface.value}",
            trim,
            request.global_force,
            request.global_moment,
            request.global_reference_point,
            support_target_id,
            ClipAngleSupportProfileTrace(
                support_target_id,
                support_profile.id,
                support_profile.family,
                support_profile.role,
                support_profile.dimensions,
                support_profile.orientation,
                cast(MemberProfileSurfaceId, support_profile.selected_surface),
            ),
            support_material_regions,
            tuple(rectangular_paths),
        )
    return ClipAnglePreviewResult(
        request.request_id,
        request.orchestration_contract_version,
        CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
        "SINGLE_CLIP_ANGLE",
        ClipAngleSemanticFrameTrace(
            (request.hand.sign, _ZERO, _ZERO),
            (_ZERO, _ONE, _ZERO),
            (_ZERO, _ZERO, request.hand.sign),
        ),
        request.hand,
        request.support_role,
        request.selected_support_flange,
        longitudinal,
        interface_a,
        interface_b,
        material_regions,
        trim,
        CLIP_ANGLE_BODY_CHECK_ID,
        ClipAngleBodyResistanceStatus.NOT_EVALUATED,
        (ClipAngleGeometryStatus.VALID if valid else ClipAngleGeometryStatus.INVALID_GEOMETRY),
        tuple(geometry_invalid_reasons),
        status,
        False,
        resistance_evaluated,
        design_ready,
        tuple(warnings),
        canonical_input,
        connector_geometry,
        engineering,
        visualization,
        support_target_id,
        ClipAngleSupportProfileTrace(
            support_target_id,
            support_profile.id,
            support_profile.family,
            support_profile.role,
            support_profile.dimensions,
            support_profile.orientation,
            cast(MemberProfileSurfaceId, support_profile.selected_surface),
        ),
        tuple(rectangular_paths),
        limitations,
    )


def preview_clip_angle(
    request: ClipAngleOrchestrationRequest,
) -> ClipAnglePreviewResult:
    """Resolve geometry/actions and Stage 2.5A demand while executing zero resistance."""

    return _preview(request, resistance=False)


def design_check_clip_angle(
    request: ClipAngleOrchestrationRequest,
) -> ClipAngleDesignResult:
    """Run each eligible interface and retain the mandatory connector-body limitation."""

    preview = _preview(request, resistance=True)
    supported_failure = _supported_failure(preview.interface_a) or _supported_failure(
        preview.interface_b
    )
    status = (
        ClipAngleAssemblyStatus.INVALID_GEOMETRY
        if preview.assembly_status is ClipAngleAssemblyStatus.INVALID_GEOMETRY
        else (
            ClipAngleAssemblyStatus.FAIL
            if supported_failure
            else ClipAngleAssemblyStatus.NOT_EVALUATED
        )
    )
    result_fingerprint = _fingerprint(
        (
            preview.engineering_fingerprint,
            None if preview.interface_a.resistance is None else preview.interface_a.resistance,
            None if preview.interface_b.resistance is None else preview.interface_b.resistance,
            CLIP_ANGLE_BODY_CHECK_ID,
            status,
        )
    )
    return ClipAngleDesignResult(
        replace(preview, assembly_status=status),
        preview.interface_a,
        preview.interface_b,
        CLIP_ANGLE_BODY_CHECK_ID,
        ClipAngleBodyResistanceStatus.NOT_EVALUATED,
        status,
        False,
        supported_failure,
        result_fingerprint,
    )


__all__ = (
    "CLIP_ANGLE_BODY_CHECK_ID",
    "CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION",
    "CLIP_ANGLE_PREVIEW_SCHEMA_VERSION",
    "CLIP_ANGLE_TRIM_PLANE_ID",
    "CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION",
    "ClipAngleAssemblyStatus",
    "ClipAngleBodyResistanceStatus",
    "ClipAngleDesignResult",
    "ClipAngleGeometryStatus",
    "ClipAngleInterfaceResult",
    "ClipAngleOrchestrationRequest",
    "ClipAnglePreviewResult",
    "ClipAngleVectorInput",
    "design_check_clip_angle",
    "preview_clip_angle",
)
