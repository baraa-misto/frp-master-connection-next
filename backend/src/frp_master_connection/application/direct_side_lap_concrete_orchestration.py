"""Stage 3.5B direct side-lap Angle/Channel to concrete-wall orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.application.clip_angle_orchestration import (
    ClipAngleBoxTrace,
    ClipAngleOrchestrationRequest,
    ClipAngleProfileMaterialRegionTrace,
    _fingerprint,
    _profile_visualization,
    _quantity,
)
from frp_master_connection.application.member_profile_geometry import (
    create_member_profile_cross_section,
    create_oriented_standard_topology,
    kernel_profile_surface_patch_ids,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowDemandSource,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    Dimension,
    EndUseFactors,
    FirstRowPlanMethod,
    LapConfiguration,
    MethodProvenance,
    MultiRowCheckFamily,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
    calculate_eccentric_bolt_group_demand,
    canonical_decimal_string,
    decimal_from_finite_real,
)
from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    EccentricDemandInput,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
)
from frp_master_connection.domain import (
    AngleProfileDimensions,
    AssemblyMember,
    ChannelProfileDimensions,
    ComponentMaterialKind,
    EngineeringUnitSystem,
    ExactProfileVector3D,
    ExternalAnchorGeometry,
    FRPComponentOrientation,
    MemberEnd,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    PositionVector3D,
    PrincipalAxisFamily,
    ProfileLocalBounds3D,
    profile_member_axis_reference,
    profile_section_geometry_adapter,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import (
    PlacedComponentGeometry3D,
    PlanarRectangularSurface3D,
    SectionDatumOffset,
    UnitVector3D,
    create_component_surface_set,
    place_member,
)

DIRECT_SIDE_LAP_CONCRETE_CONTRACT_VERSION = "3.5B-RC1"
DIRECT_SIDE_LAP_CONCRETE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
DIRECT_SIDE_LAP_CONCRETE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"
DIRECT_SIDE_LAP_EXTERNAL_HANDOFF_SCHEMA_VERSION = "3.5B-RC1"
DIRECT_SIDE_LAP_GROUP_ID = "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP"

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)
_SUPPORTED_LOCAL_FRP_FAMILIES = frozenset(
    {
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    }
)


class DirectSideLapStatus(StrEnum):
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class SideLapFrame:
    origin_lsn: tuple[Decimal, Decimal, Decimal] = (_ZERO, _ZERO, _ZERO)
    l_axis: tuple[Decimal, Decimal, Decimal] = (_ONE, _ZERO, _ZERO)
    s_axis: tuple[Decimal, Decimal, Decimal] = (_ZERO, _ONE, _ZERO)
    n_axis: tuple[Decimal, Decimal, Decimal] = (_ZERO, _ZERO, _ONE)
    handedness: str = "L_LAP cross S_LAP = N_W"

    def __post_init__(self) -> None:
        cross = (
            self.l_axis[1] * self.s_axis[2] - self.l_axis[2] * self.s_axis[1],
            self.l_axis[2] * self.s_axis[0] - self.l_axis[0] * self.s_axis[2],
            self.l_axis[0] * self.s_axis[1] - self.l_axis[1] * self.s_axis[0],
        )
        if cross != self.n_axis or self.handedness != "L_LAP cross S_LAP = N_W":
            raise ValueError("Side-lap frame must remain the controlled right-handed L/S/N frame.")


@dataclass(frozen=True, slots=True)
class SideLapVector:
    l: PhysicalQuantity  # noqa: E741 - controlled L_LAP engineering-axis name
    s: PhysicalQuantity
    n: PhysicalQuantity

    def __post_init__(self) -> None:
        if len({self.l.dimension, self.s.dimension, self.n.dimension}) != 1:
            raise ValueError("Side-lap vector components must share one physical dimension.")


@dataclass(frozen=True, slots=True)
class SideLapWrench:
    reference_lsn: SideLapVector
    force_lsn: SideLapVector
    moment_lsn: SideLapVector
    provenance: str


@dataclass(frozen=True, slots=True)
class DirectSideLapWallGeometry:
    run_length: Decimal
    transverse_width: Decimal
    thickness: Decimal

    def __post_init__(self) -> None:
        if any(
            value <= 0 or not value.is_finite()
            for value in (self.run_length, self.transverse_width, self.thickness)
        ):
            raise ValueError("Finite concrete-wall dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class DirectSideLapAnchorPattern:
    row_count: int
    anchors_per_row: int
    pitch: Decimal
    gauge: Decimal
    centroid_distance_behind_free_end: Decimal
    transverse_offset: Decimal = _ZERO

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or value < 1 for value in (self.row_count, self.anchors_per_row)
        ):
            raise ValueError("Anchor row and line counts must be positive non-Boolean integers.")
        if self.pitch <= 0 or self.gauge <= 0:
            raise ValueError("Anchor pitch and gauge must be positive.")
        if self.centroid_distance_behind_free_end <= 0:
            raise ValueError("Anchor group distance behind wall free end must be positive.")
        if not self.transverse_offset.is_finite():
            raise ValueError("Anchor transverse offset must be finite.")


@dataclass(frozen=True, slots=True)
class DirectSideLapRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    wall: DirectSideLapWallGeometry
    side_lap_length: Decimal
    member_projection_beyond_wall: Decimal
    connected_profile: MemberProfile
    anchor_pattern: DirectSideLapAnchorPattern
    external_anchor: ExternalAnchorGeometry
    axial_force: PhysicalQuantity
    major_shear: PhysicalQuantity
    minor_shear: PhysicalQuantity
    user_moment_lsn: SideLapVector
    contract_version: str = DIRECT_SIDE_LAP_CONCRETE_CONTRACT_VERSION
    connected_material_source: str = "ICE_LOCKED_PULTRUDED_FRP:RC2"
    anchor_design_authority: str = "EXTERNAL_SPECIALTY_ANCHOR_SOFTWARE"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.contract_version != DIRECT_SIDE_LAP_CONCRETE_CONTRACT_VERSION:
            raise ValueError("Unsupported direct side-lap contract version.")
        expected = Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        if self.source_length_unit is not expected:
            raise ValueError("Source length unit must match the engineering unit system.")
        if self.side_lap_length <= 0 or self.member_projection_beyond_wall <= 0:
            raise ValueError("Side-lap length and member projection must be positive.")
        if self.connected_profile.family not in {
            MemberProfileFamily.ANGLE,
            MemberProfileFamily.CHANNEL,
        }:
            raise ValueError("Stage 3.5B accepts only Angle or Channel connected profiles.")
        if self.connected_profile.family is MemberProfileFamily.CHANNEL and (
            self.connected_profile.selected_surface is not MemberProfileSurfaceId.WEB_OUTER
        ):
            raise ValueError("CHANNEL_WEB_CONTACT_ONLY")
        if self.connected_profile.family is MemberProfileFamily.ANGLE and (
            self.connected_profile.selected_surface
            not in {MemberProfileSurfaceId.LEG_Y_OUTER, MemberProfileSurfaceId.LEG_Z_OUTER}
        ):
            raise ValueError("ANGLE_SELECTED_LEG_CONTACT_REQUIRED")
        for value in (self.axial_force, self.major_shear, self.minor_shear):
            if value.dimension is not Dimension.FORCE:
                raise ValueError("Axial, Major shear, and Minor shear inputs must be forces.")
        if any(
            item.canonical_magnitude != 0
            for item in (
                self.user_moment_lsn.l,
                self.user_moment_lsn.s,
                self.user_moment_lsn.n,
            )
        ):
            raise ValueError("STAGE_3_5B_USER_APPLIED_MOMENT_NOT_ALLOWED")
        if self.external_anchor.specified_embedment.dimension is not Dimension.LENGTH:
            raise ValueError("External-anchor embedment must be a length.")
        if self.connected_material_source != "ICE_LOCKED_PULTRUDED_FRP:RC2":
            raise ValueError("Stage 3.5B requires the accepted ICE FRP material source.")
        if self.anchor_design_authority != "EXTERNAL_SPECIALTY_ANCHOR_SOFTWARE":
            raise ValueError("Concrete and anchor design authority must remain external.")


@dataclass(frozen=True, slots=True)
class SideLapEdgeDistances:
    behind_wall_free_end: PhysicalQuantity
    behind_wall_back_end: PhysicalQuantity
    negative_transverse_wall_edge: PhysicalQuantity
    positive_transverse_wall_edge: PhysicalQuantity
    negative_overlap_edge: PhysicalQuantity
    positive_overlap_edge: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class DirectSideLapAnchorTrace:
    anchor_id: str
    group_id: str
    coordinate_lsn: SideLapVector
    edge_distances: SideLapEdgeDistances
    shank_start_lsn: SideLapVector
    shank_end_lsn: SideLapVector
    penetrated_layers: tuple[str, str]
    hardware_configuration: str = "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK"
    capacity_status: str = "EXTERNAL_DESIGN_REQUIRED"


@dataclass(frozen=True, slots=True)
class DirectSideLapVisualizationSnapshot:
    schema_version: str
    side_lap_frame: SideLapFrame
    boxes: tuple[ClipAngleBoxTrace, ...]
    material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    external_anchors: tuple[DirectSideLapAnchorTrace, ...]
    external_anchor_geometry: ExternalAnchorGeometry
    connected_profile_family: MemberProfileFamily
    selected_profile_surface: MemberProfileSurfaceId
    member_start_l: PhysicalQuantity
    member_end_l: PhysicalQuantity
    wall_free_end_l: PhysicalQuantity
    overlap_interval_l: tuple[PhysicalQuantity, PhysicalQuantity]
    action_reference_lsn: SideLapVector
    anchor_group_reference_lsn: SideLapVector
    user_force_lsn: SideLapVector
    user_moment_lsn: SideLapVector
    selected_wall_surface_id: str = "CONCRETE_WALL:FINITE_EXTERIOR_FACE"


@dataclass(frozen=True, slots=True)
class DirectSideLapExternalHandoff:
    schema_version: str
    request_id: str
    unit_system: str
    side_lap_frame: SideLapFrame
    wall_free_end_l: PhysicalQuantity
    wall_dimensions: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    side_lap_length: PhysicalQuantity
    member_projection_beyond_wall: PhysicalQuantity
    connected_profile_family: MemberProfileFamily
    selected_profile_surface: MemberProfileSurfaceId
    action_reference_lsn: SideLapVector
    applied_force_lsn: SideLapVector
    user_applied_moment_lsn: SideLapVector
    anchor_group_centroid_lsn: SideLapVector
    anchor_group_wrench: SideLapWrench
    anchors: tuple[DirectSideLapAnchorTrace, ...]
    external_anchor_geometry: ExternalAnchorGeometry
    limitations: tuple[tuple[str, str], ...]
    canonical_input_fingerprint: str
    geometry_fingerprint: str
    handoff_fingerprint: str


@dataclass(frozen=True, slots=True)
class DirectSideLapPreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    geometry_status: str
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: DirectSideLapStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    external_design_required: bool
    anchor_group_id: str
    anchor_group_centroid_lsn: SideLapVector
    anchor_group_wrench: SideLapWrench
    nominal_in_plane_demand_status: str
    supported_local_frp_failure_present: bool
    limitations: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]
    external_anchor_handoff: DirectSideLapExternalHandoff
    external_anchor_handoff_json: str
    canonical_input_fingerprint: str
    geometry_fingerprint: str
    engineering_fingerprint: str
    application_fingerprint: str
    visualization: DirectSideLapVisualizationSnapshot | None


@dataclass(frozen=True, slots=True)
class DirectSideLapDesignResult:
    preview: DirectSideLapPreviewResult
    assembly_status: DirectSideLapStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_local_frp_failure_present: bool
    result_fingerprint: str


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> SideLapVector:
    return SideLapVector(*(_quantity(value, unit) for value in values))


def _exact_vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity.of(value, unit) for value in values))


def _cross(
    left: tuple[Decimal, Decimal, Decimal],
    right: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _wrench(
    request: DirectSideLapRequest,
    source: SideLapVector,
    reference: SideLapVector,
) -> SideLapWrench:
    force = (
        request.axial_force.canonical_magnitude,
        request.major_shear.canonical_magnitude,
        request.minor_shear.canonical_magnitude,
    )
    arm = (
        source.l.canonical_magnitude - reference.l.canonical_magnitude,
        source.s.canonical_magnitude - reference.s.canonical_magnitude,
        source.n.canonical_magnitude - reference.n.canonical_magnitude,
    )
    return SideLapWrench(
        _vector(
            (
                reference.l.canonical_magnitude,
                reference.s.canonical_magnitude,
                reference.n.canonical_magnitude,
            ),
            Unit.MM,
        ),
        _vector(force, Unit.N),
        _vector(_cross(arm, force), Unit.N_MM),
        "M_anchor = 0 + (r_member-r_anchor) cross F_member; exact Decimal translation",
    )


def _profile_centroid_lsn(request: DirectSideLapRequest) -> tuple[Decimal, Decimal, Decimal]:
    profile = _effective_profile(request)
    dimensions = profile.dimensions
    if isinstance(dimensions, ChannelProfileDimensions):
        unit = request.source_length_unit
        depth = _quantity(dimensions.depth, unit).canonical_magnitude
        flange_width = _quantity(dimensions.flange_width, unit).canonical_magnitude
        web_thickness = _quantity(dimensions.web_thickness, unit).canonical_magnitude
        flange_thickness = _quantity(dimensions.flange_thickness, unit).canonical_magnitude
        web_area = web_thickness * depth
        outstand = flange_width - web_thickness
        flange_area = outstand * flange_thickness
        n = (
            web_area * web_thickness / _TWO + _TWO * flange_area * (web_thickness + outstand / _TWO)
        ) / (web_area + _TWO * flange_area)
        return (_ZERO, _ZERO, n)
    if not isinstance(  # pragma: no cover - DirectSideLapRequest closes the profile union
        dimensions, AngleProfileDimensions
    ):
        raise TypeError("Direct side-lap centroid requires an Angle or Channel profile.")
    unit = request.source_length_unit
    reference = profile_member_axis_reference(profile)
    scale = _quantity(Decimal(1), unit).canonical_magnitude
    centroid_y = reference.y * scale
    centroid_z = reference.z * scale
    if profile.selected_surface is MemberProfileSurfaceId.LEG_Y_OUTER:
        return (_ZERO, centroid_y, centroid_z)
    return (_ZERO, -centroid_z, centroid_y)


def _effective_profile(request: DirectSideLapRequest) -> MemberProfile:
    """Bind the section to the authoritative overlap-plus-projection member extent."""

    return replace(
        request.connected_profile,
        dimensions=replace(
            request.connected_profile.dimensions,
            member_length=request.side_lap_length + request.member_projection_beyond_wall,
        ),
    )


def _placed_profile(request: DirectSideLapRequest) -> PlacedComponentGeometry3D:
    profile = _effective_profile(request)
    topology = create_oriented_standard_topology(profile.section_family)
    member = AssemblyMember(
        profile.member_id,
        f"Pultruded FRP direct side-lap {profile.family.value}",
        profile.role,
        MemberEnd.START,
        profile.section_family,
        ComponentMaterialKind.PULTRUDED_FRP,
        cast(FRPComponentOrientation, profile.material_orientation),
        topology,
    )
    cross_section = create_member_profile_cross_section(profile, topology)
    adapter = profile_section_geometry_adapter(profile)
    local_z = (
        UnitVector3D(0.0, -1.0, 0.0)
        if profile.selected_surface is MemberProfileSurfaceId.LEG_Y_OUTER
        else UnitVector3D(0.0, 0.0, -1.0)
    )
    start = PositionVector3D(-float(request.side_lap_length), 0.0, 0.0)
    end = PositionVector3D(float(request.member_projection_beyond_wall), 0.0, 0.0)
    offset = SectionDatumOffset(
        float(adapter.section_datum_offset_y),
        float(adapter.section_datum_offset_z),
    )
    provisional = place_member(member, cross_section, start, end, local_z, offset)
    selected_id, _opposing, _element = kernel_profile_surface_patch_ids(profile)
    patches = tuple(
        item for item in create_component_surface_set(provisional).patches if item.id == selected_id
    )
    if len(patches) != 1 or not isinstance(  # pragma: no cover - section kernel contract
        patches[0].geometry, PlanarRectangularSurface3D
    ):
        raise ValueError("Selected direct side-lap surface did not resolve uniquely.")
    surface = patches[0].geometry
    if (  # pragma: no cover - placed selected-face alignment is a kernel invariant
        surface.normal.dot(UnitVector3D(0.0, 1.0, 0.0)) < 1.0 - 1e-12
    ):
        raise ValueError("ANGLE_FREE_LEG_OR_CHANNEL_FLANGE_EMBEDDED_IN_CONCRETE")
    target_l = (float(request.member_projection_beyond_wall) - float(request.side_lap_length)) / 2
    shift = (target_l - surface.center.x, -surface.center.y, -surface.center.z)
    return place_member(
        member,
        cross_section,
        PositionVector3D(start.x + shift[0], start.y + shift[1], start.z + shift[2]),
        PositionVector3D(end.x + shift[0], end.y + shift[1], end.z + shift[2]),
        local_z,
        offset,
    )


def _anchor_coordinates(request: DirectSideLapRequest) -> tuple[tuple[Decimal, Decimal], ...]:
    pattern = request.anchor_pattern
    first_l = (
        -pattern.centroid_distance_behind_free_end
        - pattern.pitch * Decimal(pattern.row_count - 1) / _TWO
    )
    first_s = (
        pattern.transverse_offset - pattern.gauge * Decimal(pattern.anchors_per_row - 1) / _TWO
    )
    return tuple(
        (first_l + Decimal(row) * pattern.pitch, first_s + Decimal(line) * pattern.gauge)
        for row in range(pattern.row_count)
        for line in range(pattern.anchors_per_row)
    )


def _disk_within(
    bounds: ProfileLocalBounds3D,
    point: ExactProfileVector3D,
    axis: PrincipalAxisFamily,
    radius: Decimal,
) -> bool:
    ranges = (
        ((bounds.min_x, point.x, bounds.max_x), (bounds.min_z, point.z, bounds.max_z))
        if axis is PrincipalAxisFamily.Y
        else ((bounds.min_x, point.x, bounds.max_x), (bounds.min_y, point.y, bounds.max_y))
    )
    return all(low + radius <= coordinate <= high - radius for low, coordinate, high in ranges)


def _local_anchor_point(
    placed: PlacedComponentGeometry3D,
    coordinate_l: Decimal,
    coordinate_s: Decimal,
) -> ExactProfileVector3D:
    local = placed.global_to_local(PositionVector3D(float(coordinate_l), 0.0, float(coordinate_s)))
    return ExactProfileVector3D(
        decimal_from_finite_real(local.x),
        decimal_from_finite_real(local.y),
        decimal_from_finite_real(local.z),
    )


def _anchor_traces(request: DirectSideLapRequest) -> tuple[DirectSideLapAnchorTrace, ...]:
    unit = request.source_length_unit
    selected = require_direct_tee_profile_surface(_effective_profile(request))
    layer = selected.physical_element_id
    embedment = request.external_anchor.specified_embedment.to(unit).magnitude
    thickness = selected.layer_thickness
    half_wall = request.wall.transverse_width / _TWO
    return tuple(
        DirectSideLapAnchorTrace(
            (
                f"DIRECT-LAP-R{index // request.anchor_pattern.anchors_per_row + 1}"
                f"-A{index % request.anchor_pattern.anchors_per_row + 1}"
            ),
            DIRECT_SIDE_LAP_GROUP_ID,
            _vector((coordinate_l, coordinate_s, _ZERO), unit),
            SideLapEdgeDistances(
                _quantity(-coordinate_l, unit),
                _quantity(request.wall.run_length + coordinate_l, unit),
                _quantity(coordinate_s + half_wall, unit),
                _quantity(half_wall - coordinate_s, unit),
                _quantity(coordinate_l + request.side_lap_length, unit),
                _quantity(-coordinate_l, unit),
            ),
            _vector((coordinate_l, coordinate_s, thickness), unit),
            _vector((coordinate_l, coordinate_s, -embedment), unit),
            (f"{request.connected_profile.family.value}_{layer}", "CONCRETE_EMBEDMENT"),
        )
        for index, (coordinate_l, coordinate_s) in enumerate(_anchor_coordinates(request))
    )


def _geometry_reasons(
    request: DirectSideLapRequest,
    placed: PlacedComponentGeometry3D,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if request.connected_profile.orientation is not MemberProfileOrientation.ROTATION_0:
        reasons.append("ANGLE_FREE_LEG_OR_CHANNEL_FLANGE_EMBEDDED_IN_CONCRETE")
    if (
        request.external_anchor.specified_embedment.to(request.source_length_unit).magnitude
        > request.wall.thickness
    ):
        reasons.append("ANCHOR_EMBEDMENT_EXCEEDS_WALL_THICKNESS")
    surface = require_direct_tee_profile_surface(_effective_profile(request))
    radius = request.external_anchor.hole_diameter.to(request.source_length_unit).magnitude / _TWO
    half_wall = request.wall.transverse_width / _TWO
    for index, (coordinate_l, coordinate_s) in enumerate(_anchor_coordinates(request), start=1):
        anchor_id = f"DIRECT-LAP-{index}"
        if not (-request.side_lap_length <= coordinate_l <= _ZERO):
            reasons.append(f"ANCHOR_OUTSIDE_PHYSICAL_SIDE_LAP_OVERLAP:{anchor_id}")
        if not (
            -request.wall.run_length <= coordinate_l <= _ZERO
            and -half_wall <= coordinate_s <= half_wall
        ):
            reasons.append(f"ANCHOR_CENTER_OUTSIDE_FINITE_WALL_FACE:{anchor_id}")
        local = _local_anchor_point(placed, coordinate_l, coordinate_s)
        matches = tuple(
            bounds
            for bounds in surface.penetration_bounds
            if _disk_within(bounds, local, surface.plane_axis, radius)
        )
        if len(matches) != 1:
            reasons.append(f"FRP_SELECTED_REGION_COMPLETE_HOLE_CONTAINMENT_INVALID:{anchor_id}")
    return tuple(reasons)


def _limitations(
    request: DirectSideLapRequest, wrench: SideLapWrench
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = [
        ("DIRECT_SIDE_LAP_CONNECTION_QUALIFICATION", "NOT_EVALUATED"),
        ("CONCRETE_SUBSTRATE_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
        ("ANCHOR_SYSTEM_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
        ("ANCHOR_STEEL_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
        ("ANCHOR_CONCRETE_LIMIT_STATES", "EXTERNAL_DESIGN_REQUIRED"),
        ("EXTERNAL_ANCHOR_DEMAND_VERIFICATION", "REQUIRED"),
    ]
    if request.minor_shear.canonical_magnitude != 0:
        result.extend(
            (
                ("DIRECT_SIDE_LAP_BOLT_AXIS_RESPONSE", "NOT_EVALUATED"),
                ("DIRECT_SIDE_LAP_FRP_PULL_THROUGH", "NOT_EVALUATED"),
                ("WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION", "EXTERNAL_DESIGN_REQUIRED"),
            )
        )
    moment = wrench.moment_lsn
    if moment.l.canonical_magnitude != 0 or moment.s.canonical_magnitude != 0:
        result.append(("DIRECT_SIDE_LAP_OUT_OF_PLANE_RESPONSE", "NOT_EVALUATED"))
    return tuple(result)


def _export(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"value": canonical_decimal_string(value.magnitude), "unit": value.unit.value}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _export(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, tuple):
        return [_export(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _export(item) for key, item in sorted(value.items())}
    return value


def _input_fingerprint(request: DirectSideLapRequest) -> str:
    unit = request.source_length_unit
    dimensions = tuple(
        (
            item.name,
            _quantity(
                cast(Decimal, getattr(request.connected_profile.dimensions, item.name)),
                unit,
            ),
        )
        for item in fields(request.connected_profile.dimensions)
        if item.name != "member_length"
    )
    return _fingerprint(
        (
            request.contract_version,
            tuple(
                _quantity(value, unit)
                for value in (
                    request.wall.run_length,
                    request.wall.transverse_width,
                    request.wall.thickness,
                )
            ),
            _quantity(request.side_lap_length, unit),
            _quantity(request.member_projection_beyond_wall, unit),
            request.connected_profile.family,
            request.connected_profile.selected_surface,
            request.connected_profile.orientation,
            dimensions,
            request.anchor_pattern.row_count,
            request.anchor_pattern.anchors_per_row,
            _quantity(request.anchor_pattern.pitch, unit),
            _quantity(request.anchor_pattern.gauge, unit),
            _quantity(request.anchor_pattern.centroid_distance_behind_free_end, unit),
            _quantity(request.anchor_pattern.transverse_offset, unit),
            request.external_anchor,
            request.axial_force,
            request.major_shear,
            request.minor_shear,
            request.user_moment_lsn,
        )
    )


def _visualization(
    request: DirectSideLapRequest,
    placed: PlacedComponentGeometry3D,
    anchors: tuple[DirectSideLapAnchorTrace, ...],
    action_reference: SideLapVector,
    group_reference: SideLapVector,
) -> DirectSideLapVisualizationSnapshot:
    unit = request.source_length_unit
    profile_boxes, material_regions = _profile_visualization(
        cast(ClipAngleOrchestrationRequest, request), placed
    )
    # The wall occupies negative L, negative N; the profile continues through L=0 at N>=0.
    wall_box = ClipAngleBoxTrace(
        "direct-side-lap-concrete-wall",
        "direct-side-lap-concrete-wall",
        "CONCRETE_WALL",
        (
            _quantity(-request.wall.run_length / _TWO, unit),
            _quantity(request.wall.thickness / _TWO, unit),
            _quantity(_ZERO, unit),
        ),
        _quantity(request.wall.run_length, unit),
        _quantity(request.wall.thickness, unit),
        _quantity(request.wall.transverse_width, unit),
    )
    force_unit = request.axial_force.unit
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    return DirectSideLapVisualizationSnapshot(
        DIRECT_SIDE_LAP_CONCRETE_VISUALIZATION_SCHEMA_VERSION,
        SideLapFrame(),
        (*profile_boxes, wall_box),
        material_regions,
        anchors,
        request.external_anchor,
        request.connected_profile.family,
        cast(MemberProfileSurfaceId, request.connected_profile.selected_surface),
        _quantity(-request.side_lap_length, unit),
        _quantity(request.member_projection_beyond_wall, unit),
        _quantity(_ZERO, unit),
        (_quantity(-request.side_lap_length, unit), _quantity(_ZERO, unit)),
        action_reference,
        group_reference,
        _vector(
            (
                request.axial_force.to(force_unit).magnitude,
                request.major_shear.to(force_unit).magnitude,
                request.minor_shear.to(force_unit).magnitude,
            ),
            force_unit,
        ),
        _vector((_ZERO, _ZERO, _ZERO), moment_unit),
    )


def _contact_width_and_thickness(request: DirectSideLapRequest) -> tuple[Decimal, Decimal]:
    dimensions = request.connected_profile.dimensions
    if isinstance(dimensions, ChannelProfileDimensions):
        return dimensions.depth, dimensions.web_thickness
    if not isinstance(  # pragma: no cover - DirectSideLapRequest closes the profile union
        dimensions, AngleProfileDimensions
    ):
        raise TypeError("Direct side-lap resistance requires an Angle or Channel profile.")
    width = (
        dimensions.leg_y
        if request.connected_profile.selected_surface is MemberProfileSurfaceId.LEG_Y_OUTER
        else dimensions.leg_z
    )
    return width, dimensions.thickness


def _local_resistance_request(
    request: DirectSideLapRequest,
    wrench: SideLapWrench,
) -> MultiRowOrchestrationRequest | None:
    """Adapt the real direct anchor layout to the accepted FRP-local multi-row seam."""

    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    axial = request.axial_force.to(force_unit)
    major = request.major_shear.to(force_unit)
    # The accepted physical-row resolver requires rows to be normal to the applied
    # in-plane force. RC1 can therefore reuse it directly only for the controlled
    # longitudinal row axis. Transverse or combined action remains in the exact
    # handoff without inventing a rotated row-distribution method.
    if axial.magnitude == 0 or major.magnitude != 0:
        return None
    unit = request.source_length_unit
    coordinates = _anchor_coordinates(request)
    first_l = min(item[0] for item in coordinates)
    last_l = max(item[0] for item in coordinates)
    first_s = min(item[1] for item in coordinates)
    last_s = max(item[1] for item in coordinates)
    contact_width, layer_thickness = _contact_width_and_thickness(request)
    resultant = (axial.magnitude * axial.magnitude + major.magnitude * major.magnitude).sqrt()
    moment_n = abs(wrench.moment_lsn.n.canonical_magnitude)
    offset = PhysicalQuantity.of(
        moment_n / PhysicalQuantity.of(resultant, force_unit).canonical_magnitude,
        Unit.MM,
    )
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_3_5B_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:DIRECT_SIDE_LAP_FRP",
        "stage-3-5b:direct-side-lap",
        DIRECT_SIDE_LAP_GROUP_ID,
        request.request_id,
        "Stage 3.5B exact direct side-lap anchor-group wrench",
        request.unit_system,
        unit,
        request.anchor_pattern.row_count,
        request.anchor_pattern.anchors_per_row,
        request.external_anchor.nominal_diameter.to(unit),
        (
            PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
            if unit is Unit.IN
            else PublishedCodeUnitBasis.SI_PRINTED
        ),
        _quantity(request.anchor_pattern.pitch, unit),
        _quantity(request.anchor_pattern.gauge, unit),
        _quantity(request.side_lap_length + first_l, unit),
        _quantity(-last_l, unit),
        _quantity(contact_width / _TWO + first_s, unit),
        _quantity(contact_width / _TWO - last_s, unit),
        _quantity(Decimal("0.000000001"), unit),
        ConnectedMaterialPair.FRP_STEEL,
        (
            MultiRowLayerInput(
                "DIRECT_SIDE_LAP_SELECTED_FRP_LAYER",
                request.connected_profile.member_id,
                "ICE_LOCKED_PULTRUDED_FRP",
                _quantity(layer_thickness, unit),
                PultrudedElementClassification.SHAPE,
                _ZERO,
                factors,
                ThreadStatus.EXCLUDED,
            ),
        ),
        axial,
        major,
        "BACKEND_AUTHORITATIVE_MEMBER_REFERENCE_AND_ANCHOR_COORDINATES",
        RowDistributionBasis.ASCE_PRESCRIBED,
        None,
        (),
        MethodProvenance(
            "STAGE_3_5B_STAGE_2_5A_RESOLVED_DEMAND",
            "STAGE_3_5B_DIRECT_SIDE_LAP_ENGINEERING_SPECIFICATION_RC1",
            "RC1",
            request.request_id,
            "BACKEND_AUTHORITATIVE_MEMBER_ACTION_REFERENCE",
            True,
            True,
        ),
        False,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.SINGLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        None,
        offset.to(unit),
        _quantity(Decimal("0.000000001"), unit),
        demand_source=MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND,
        single_row_geometry_preview_authorized=request.anchor_pattern.row_count == 1,
    )


def _evaluate_local_frp_resistance(
    request: DirectSideLapRequest,
    preview: DirectSideLapPreviewResult,
) -> tuple[bool, bool, tuple[str, ...], str | None]:
    """Execute only accepted in-plane FRP checks for the explicit design action."""

    multirow = _local_resistance_request(request, preview.anchor_group_wrench)
    if multirow is None or multirow.single_row_geometry_preview_authorized:
        return False, False, (), None
    resolved = _resolve(multirow)
    bundle = _execution_bundle(multirow, resolved)
    zero_moment = _exact_vector((_ZERO, _ZERO, _ZERO), Unit.N_MM)
    action_reference = preview.external_anchor_handoff.action_reference_lsn
    demand = calculate_eccentric_bolt_group_demand(
        EccentricDemandInput(
            f"{request.request_id}:DIRECT_SIDE_LAP_ACTION",
            request.connected_profile.member_id,
            _exact_vector(
                (
                    request.axial_force.canonical_magnitude,
                    request.major_shear.canonical_magnitude,
                    request.minor_shear.canonical_magnitude,
                ),
                Unit.N,
            ),
            zero_moment,
            zero_moment,
            _exact_vector(
                (
                    action_reference.l.canonical_magnitude,
                    action_reference.s.canonical_magnitude,
                    action_reference.n.canonical_magnitude,
                ),
                Unit.MM,
            ),
            ExactInterfaceFrame(
                DIRECT_SIDE_LAP_GROUP_ID,
                _exact_vector(
                    (
                        -_quantity(
                            request.side_lap_length,
                            request.source_length_unit,
                        ).canonical_magnitude,
                        _ZERO,
                        _ZERO,
                    ),
                    Unit.MM,
                ),
                (_ONE, _ZERO, _ZERO),
                (_ZERO, _ONE, _ZERO),
                (_ZERO, _ZERO, _ONE),
            ),
            bundle.physical_geometry,
            resolved.demand_plan,
            resolved.applicability.method_applicability,
            resolved.applicability.qualification,
            (
                "STAGE_2_5A_DEMAND_ANALYSIS",
                "STAGE_3_5B_BACKEND_AUTHORITATIVE_DIRECT_SIDE_LAP_ACTION",
                DIRECT_SIDE_LAP_GROUP_ID,
            ),
        )
    )
    if demand.availability is not DemandAnalysisAvailability.CALCULATED:
        return (
            False,
            False,
            tuple(item.code.value for item in demand.warnings),
            demand.result_fingerprint,
        )
    response = evaluate_multirow_connection_with_resolved_demand(multirow, demand)
    checks = tuple(
        check
        for handoff in response.automatic_handoff_results
        for check in handoff.checks
        if check.family in _SUPPORTED_LOCAL_FRP_FAMILIES
    )
    failures = tuple(
        check.check_id
        for check in checks
        if check.resistance_result is not None
        and check.resistance_result.numerical_comparison.value == "FAIL"
    )
    warnings = tuple(f"SUPPORTED_LOCAL_FRP_FAILURE:{item}" for item in failures)
    fingerprint = _fingerprint(
        (
            demand.result_fingerprint,
            tuple(handoff.result_fingerprint for handoff in response.automatic_handoff_results),
            failures,
        )
    )
    return bool(checks), bool(failures), warnings, fingerprint


def preview_direct_side_lap_concrete(request: DirectSideLapRequest) -> DirectSideLapPreviewResult:
    """Resolve exact geometry, action, wrench, and handoff with zero resistance."""

    placed = _placed_profile(request)
    centroid = _profile_centroid_lsn(request)
    action_reference = _vector(centroid, Unit.MM)
    unit = request.source_length_unit
    group_reference = _vector(
        (
            _quantity(
                -request.anchor_pattern.centroid_distance_behind_free_end, unit
            ).canonical_magnitude,
            _quantity(request.anchor_pattern.transverse_offset, unit).canonical_magnitude,
            _ZERO,
        ),
        Unit.MM,
    )
    wrench = _wrench(request, action_reference, group_reference)
    anchors = _anchor_traces(request)
    reasons = _geometry_reasons(request, placed)
    geometry_valid = not reasons
    limitations = _limitations(request, wrench)
    canonical_input = _input_fingerprint(request)
    geometry_fingerprint = _fingerprint(
        (
            request.contract_version,
            tuple(
                _quantity(value, unit)
                for value in (
                    request.wall.run_length,
                    request.wall.transverse_width,
                    request.wall.thickness,
                )
            ),
            _quantity(request.side_lap_length, unit),
            _quantity(request.member_projection_beyond_wall, unit),
            request.connected_profile.family,
            request.connected_profile.selected_surface,
            tuple(_quantity(value, unit) for value in _anchor_coordinates(request)[0])
            if len(_anchor_coordinates(request)) == 1
            else tuple(
                tuple(_quantity(value, unit) for value in item)
                for item in _anchor_coordinates(request)
            ),
            request.external_anchor,
        )
    )
    handoff_base = (
        request.contract_version,
        SideLapFrame(),
        _quantity(_ZERO, unit),
        tuple(
            _quantity(value, unit)
            for value in (
                request.wall.run_length,
                request.wall.transverse_width,
                request.wall.thickness,
            )
        ),
        _quantity(request.side_lap_length, unit),
        _quantity(request.member_projection_beyond_wall, unit),
        request.connected_profile.family,
        request.connected_profile.selected_surface,
        action_reference,
        _vector(
            (
                request.axial_force.to(request.axial_force.unit).magnitude,
                request.major_shear.to(request.axial_force.unit).magnitude,
                request.minor_shear.to(request.axial_force.unit).magnitude,
            ),
            request.axial_force.unit,
        ),
        request.user_moment_lsn,
        group_reference,
        wrench,
        anchors,
        request.external_anchor,
        limitations,
        canonical_input,
        geometry_fingerprint,
    )
    handoff_fingerprint = _fingerprint(handoff_base)
    handoff = DirectSideLapExternalHandoff(
        DIRECT_SIDE_LAP_EXTERNAL_HANDOFF_SCHEMA_VERSION,
        request.request_id,
        request.unit_system.value,
        SideLapFrame(),
        _quantity(_ZERO, unit),
        (
            _quantity(request.wall.run_length, unit),
            _quantity(request.wall.transverse_width, unit),
            _quantity(request.wall.thickness, unit),
        ),
        _quantity(request.side_lap_length, unit),
        _quantity(request.member_projection_beyond_wall, unit),
        request.connected_profile.family,
        cast(MemberProfileSurfaceId, request.connected_profile.selected_surface),
        action_reference,
        _vector(
            (
                request.axial_force.to(request.axial_force.unit).magnitude,
                request.major_shear.to(request.axial_force.unit).magnitude,
                request.minor_shear.to(request.axial_force.unit).magnitude,
            ),
            request.axial_force.unit,
        ),
        request.user_moment_lsn,
        group_reference,
        wrench,
        anchors,
        request.external_anchor,
        limitations,
        canonical_input,
        geometry_fingerprint,
        handoff_fingerprint,
    )
    handoff_json = json.dumps(
        cast(dict[str, object], _export(handoff)),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    engineering_fingerprint = _fingerprint(
        (canonical_input, geometry_fingerprint, wrench, limitations, handoff_fingerprint)
    )
    application_fingerprint = _fingerprint(
        (engineering_fingerprint, "PREVIEW_ZERO_RESISTANCE", geometry_valid)
    )
    status = (
        DirectSideLapStatus.NOT_EVALUATED
        if geometry_valid
        else DirectSideLapStatus.INVALID_GEOMETRY
    )
    return DirectSideLapPreviewResult(
        request.request_id,
        request.contract_version,
        DIRECT_SIDE_LAP_CONCRETE_PREVIEW_SCHEMA_VERSION,
        "DIRECT_SIDE_LAP_ANGLE_CHANNEL_TO_CONCRETE_WALL",
        "VALID" if geometry_valid else "INVALID_GEOMETRY",
        reasons,
        status,
        False,
        False,
        geometry_valid,
        True,
        DIRECT_SIDE_LAP_GROUP_ID,
        group_reference,
        wrench,
        "AVAILABLE_WITH_EXISTING_METHODS"
        if request.minor_shear.canonical_magnitude == 0
        else "PARTIALLY_NOT_EVALUATED",
        False,
        limitations,
        (),
        handoff,
        handoff_json,
        canonical_input,
        geometry_fingerprint,
        engineering_fingerprint,
        application_fingerprint,
        _visualization(request, placed, anchors, action_reference, group_reference)
        if geometry_valid
        else None,
    )


def design_check_direct_side_lap_concrete(
    request: DirectSideLapRequest,
) -> DirectSideLapDesignResult:
    """Run the explicit design workflow while retaining unsupported methods as limitations."""

    preview = preview_direct_side_lap_concrete(request)
    resistance_evaluated = False
    supported_failure = False
    resistance_warnings: tuple[str, ...] = ()
    resistance_fingerprint: str | None = None
    if preview.design_check_ready:
        (
            resistance_evaluated,
            supported_failure,
            resistance_warnings,
            resistance_fingerprint,
        ) = _evaluate_local_frp_resistance(request, preview)
    status = (
        DirectSideLapStatus.INVALID_GEOMETRY
        if not preview.design_check_ready
        else DirectSideLapStatus.FAIL
        if supported_failure
        else DirectSideLapStatus.NOT_EVALUATED
    )
    preview = replace(
        preview,
        assembly_status=status,
        resistance_evaluated=resistance_evaluated,
        supported_local_frp_failure_present=supported_failure,
        warnings=(*preview.warnings, *resistance_warnings),
        application_fingerprint=_fingerprint(
            (
                preview.engineering_fingerprint,
                "EXPLICIT_SUPPORTED_LOCAL_FRP_DESIGN",
                resistance_fingerprint,
                supported_failure,
            )
        ),
    )
    result_fingerprint = _fingerprint(
        (
            preview.application_fingerprint,
            status,
            supported_failure,
        )
    )
    return DirectSideLapDesignResult(
        preview,
        status,
        "NOT_EVALUATED",
        False,
        supported_failure,
        result_fingerprint,
    )


__all__ = (
    "DIRECT_SIDE_LAP_CONCRETE_CONTRACT_VERSION",
    "DIRECT_SIDE_LAP_CONCRETE_PREVIEW_SCHEMA_VERSION",
    "DIRECT_SIDE_LAP_GROUP_ID",
    "DirectSideLapAnchorPattern",
    "DirectSideLapDesignResult",
    "DirectSideLapPreviewResult",
    "DirectSideLapRequest",
    "DirectSideLapStatus",
    "DirectSideLapWallGeometry",
    "SideLapVector",
    "design_check_direct_side_lap_concrete",
    "preview_direct_side_lap_concrete",
)
