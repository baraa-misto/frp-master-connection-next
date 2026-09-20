"""Stage 3.7A additive column-base profile-matrix orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.application.clip_angle_orchestration import (
    CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
    ClipAngleBoltTrace,
    ClipAngleBoxTrace,
    ClipAngleMaterialRegionTrace,
    _layout_coordinates,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    ColumnBaseAnchorGroupResult,
    ColumnBaseAnchorTrace,
    ColumnBaseBearingFootprint,
    ColumnBaseDesignResult,
    ColumnBaseGeometryStatus,
    ColumnBaseLayerDemandTrace,
    ColumnBaseLayerDirectionTrace,
    ColumnBasePreviewResult,
    ColumnBaseWrench,
    _canonical_export,
    _canonical_fingerprint,
    _geometry_reasons,
    _layer_demands_for_request,
    _layer_directions,
    _material_regions,
    _preview,
    _quantity,
    _surrogate_request,
    _vector,
    _wrench,
)
from frp_master_connection.application.member_profile_geometry import (
    create_oriented_standard_topology,
)
from frp_master_connection.calculation import EccentricDemandResult, PhysicalQuantity, Unit
from frp_master_connection.domain import (
    AngleProfileDimensions,
    ColumnBaseAssembly,
    ColumnBaseFrame,
    ColumnBaseProfileRequest,
    ColumnBaseSide,
    ColumnBaseSignedRequest,
    ColumnBaseStatus,
    ColumnBaseVector,
    ColumnBaseWideFlangeGeometry,
    EngineeringUnitSystem,
    ExactProfileVector3D,
    FullThroughBoltPath,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    PhysicalBoltPathSegmentKind,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    RectangularHollowProfileDimensions,
    RectangularMaterialBasis,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    compose_external_connector_layers,
    evaluate_full_through_containment,
    external_connector_layer,
    full_through_bolt_hardware,
    profile_member_axis_reference,
    rectangular_opposing_face_pair,
    resolve_angle_leg_bolt_path,
    resolve_profile_surface,
)

COLUMN_BASE_PROFILE_CONTRACT_VERSION = "3.7A-RC1"
COLUMN_BASE_PROFILE_HANDOFF_SCHEMA_VERSION = "3.7A-RC1"

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)
_HALF = Decimal("0.5")
_FINGERPRINT_QUANTUM = Decimal("1e-18")


def _fingerprint_normalize(value: object) -> object:
    """Normalize only fingerprint transport noise; production geometry is unchanged."""

    if isinstance(value, PhysicalQuantity):
        return (
            value.dimension.value,
            value.canonical_magnitude.quantize(_FINGERPRINT_QUANTUM),
        )
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (item.name, _fingerprint_normalize(getattr(value, item.name)))
                for item in fields(value)
            ),
        )
    if isinstance(value, tuple):
        return tuple(_fingerprint_normalize(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            (str(key), _fingerprint_normalize(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    return value


def _successor_fingerprint(value: object) -> str:
    return _canonical_fingerprint(_fingerprint_normalize(value))


@dataclass(frozen=True, slots=True)
class ColumnBaseConnectionFrameTrace:
    selected_surface: str
    origin_profile_xyz: tuple[Decimal, Decimal, Decimal]
    s_axis_profile_xyz: tuple[Decimal, Decimal, Decimal]
    t_axis_profile_xyz: tuple[Decimal, Decimal, Decimal]
    l_axis_profile_xyz: tuple[Decimal, Decimal, Decimal]
    handedness: str = "S_C cross T_C = L_C"


@dataclass(frozen=True, slots=True)
class ColumnBasePhysicalPathSegmentTrace:
    kind: str
    identity: str
    length: PhysicalQuantity
    material_region_id: str | None
    has_material_axes: bool


@dataclass(frozen=True, slots=True)
class ColumnBasePhysicalBoltPathTrace:
    bolt_id: str
    selected_surface: str
    opposite_surface: str
    segments: tuple[ColumnBasePhysicalPathSegmentTrace, ...]
    stack_start_s_t_l: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    stack_end_s_t_l: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    physical_bolt_count: int
    continuous_shank_count: int
    internal_hardware_count: int
    head_location: str
    nut_location: str
    washer_locations: tuple[str, ...]
    containment_status: str
    path_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileComponentTransferTrace:
    axial_mode: str
    column_signed_axial_action: PhysicalQuantity
    column_design_magnitude: PhysicalQuantity
    column_fraction: Decimal
    column_material_direction: str
    column_signed_material_direction: str
    base_angle_system_signed_axial_action: PhysicalQuantity
    base_angle_system_design_magnitude: PhysicalQuantity
    base_angle_system_fraction: Decimal
    base_angle_vertical_leg_material_direction: str
    base_angle_vertical_leg_signed_material_direction: str
    positive_angle_signed_axial_action: PhysicalQuantity | None
    negative_angle_signed_axial_action: PhysicalQuantity | None
    single_angle_signed_axial_action: PhysicalQuantity | None
    branch_fraction: Decimal
    complete_branch_allocation: str
    foundation_signed_axial_action: PhysicalQuantity
    component_design_demands_summed_for_equilibrium: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileSymmetryProof:
    geometry_mirrored: bool
    connectors_identical: bool
    anchors_mirrored: bool
    member_reference_on_midplane: bool
    connection_normal_shear_zero: bool
    user_moment_zero: bool
    complete_branch_half_sharing_eligible: bool
    angle_local_common_group_half_sharing_eligible: bool
    complete_branch_allocation: str


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileExternalHandoff:
    schema_version: str
    request_id: str
    unit_system: str
    profile_family: str
    selected_surface: str
    connection_frame: ColumnBaseConnectionFrameTrace
    member_action_reference_s_t_l: ColumnBaseVector
    combined_foundation_wrench: ColumnBaseWrench
    component_transfer: ColumnBaseProfileComponentTransferTrace
    symmetry_proof: ColumnBaseProfileSymmetryProof
    anchor_groups: tuple[ColumnBaseAnchorGroupResult, ...]
    physical_bolt_paths: tuple[ColumnBasePhysicalBoltPathTrace, ...]
    limitations: tuple[tuple[str, str], ...]
    demand_method_versions: tuple[str, ...]
    input_fingerprint: str
    handoff_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileVisualizationSnapshot:
    schema_version: str
    base_frame: ColumnBaseFrame
    connection_frame: ColumnBaseConnectionFrameTrace
    profile_family: str
    selected_surface: str
    boxes: tuple[ClipAngleBoxTrace, ...]
    web_bolts: tuple[ClipAngleBoltTrace, ...]
    physical_bolt_paths: tuple[ColumnBasePhysicalBoltPathTrace, ...]
    anchors: tuple[ColumnBaseAnchorTrace, ...]
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    external_anchor_geometry: object
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    applied_force_s_t_l: ColumnBaseVector
    action_reference_s_t_l: ColumnBaseVector
    selected_surfaces: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ColumnBaseProfilePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    base_frame: ColumnBaseFrame
    connection_frame: ColumnBaseConnectionFrameTrace
    profile_family: str
    selected_surface: str
    member_action_reference_s_t_l: ColumnBaseVector
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide
    web_group_demand: EccentricDemandResult
    layer_demands: tuple[ColumnBaseLayerDemandTrace, ...]
    layer_directions: tuple[ColumnBaseLayerDirectionTrace, ...]
    component_transfer: ColumnBaseProfileComponentTransferTrace
    symmetry_proof: ColumnBaseProfileSymmetryProof
    physical_bolt_paths: tuple[ColumnBasePhysicalBoltPathTrace, ...]
    combined_foundation_wrench: ColumnBaseWrench
    anchor_groups: tuple[ColumnBaseAnchorGroupResult, ...]
    external_handoff: ColumnBaseProfileExternalHandoff
    external_handoff_json: str
    geometry_status: ColumnBaseGeometryStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: ColumnBaseStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    limitations: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]
    engineering_fingerprint: str
    application_fingerprint: str
    visualization: ColumnBaseProfileVisualizationSnapshot | None


@dataclass(frozen=True, slots=True)
class ColumnBaseProfileDesignResult:
    preview: ColumnBaseProfilePreviewResult
    web_group_resistance: object | None
    assembly_status: ColumnBaseStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_local_failure_present: bool
    result_fingerprint: str


_PROFILE_LIMITATIONS = (
    ("BASE_ANGLE_BODY_AND_HEEL_TRANSFER", "NOT_EVALUATED"),
    ("BASE_ANGLE_HORIZONTAL_LEG_PRYING", "NOT_EVALUATED"),
    ("CONCRETE_SUBSTRATE_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("ANCHOR_SYSTEM_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("CONNECTION_NORMAL_BOLT_AXIS_RESPONSE", "NOT_EVALUATED"),
)


def _tuple(value: ExactProfileVector3D) -> tuple[Decimal, Decimal, Decimal]:
    return (value.x, value.y, value.z)


def _dot(a: tuple[Decimal, Decimal, Decimal], b: tuple[Decimal, Decimal, Decimal]) -> Decimal:
    return sum((left * right for left, right in zip(a, b, strict=True)), start=_ZERO)


def _profile_frame(
    profile: MemberProfile,
) -> tuple[
    ColumnBaseConnectionFrameTrace,
    tuple[Decimal, Decimal],
    tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
]:
    surface = resolve_profile_surface(profile)
    normal = _tuple(surface.local_outward_normal)
    s_axis = (_ZERO, normal[2], -normal[1])
    l_axis = (_ONE, _ZERO, _ZERO)
    origin_yz = (
        (surface.center.y, surface.center.z)
        if profile.family is MemberProfileFamily.ANGLE
        else (_ZERO, _ZERO)
    )
    frame = ColumnBaseConnectionFrameTrace(
        surface.surface_id.value,
        (_ZERO, *origin_yz),
        s_axis,
        normal,
        l_axis,
    )
    return frame, origin_yz, ((s_axis[1], s_axis[2]), (normal[1], normal[2]))


def _to_st(
    y: Decimal,
    z: Decimal,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> tuple[Decimal, Decimal]:
    vector = (_ZERO, y - origin[0], z - origin[1])
    return (
        _dot(vector, (_ZERO, *basis[0])),
        _dot(vector, (_ZERO, *basis[1])),
    )


def _member_reference(
    request: ColumnBaseProfileRequest,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> ColumnBaseVector:
    reference = profile_member_axis_reference(request.column_profile)
    s, t = _to_st(reference.y, reference.z, origin, basis)
    return _vector((s, t, _ZERO), request.source_length_unit)


def _legacy_request(
    request: ColumnBaseProfileRequest, action_reference: ColumnBaseVector
) -> ColumnBaseSignedRequest:
    unit = request.source_length_unit
    dimensions = request.column_profile.dimensions
    if isinstance(dimensions, WideFlangeIProfileDimensions):
        depth = dimensions.depth
        width = dimensions.flange_width
        web = dimensions.web_thickness
        flange = dimensions.flange_thickness
    elif isinstance(dimensions, RectangularHollowProfileDimensions):
        depth = dimensions.depth
        width = dimensions.width
        web = dimensions.wall_thickness
        flange = dimensions.wall_thickness
    elif isinstance(dimensions, SolidRectangularProfileDimensions):
        depth = dimensions.depth
        width = dimensions.width
        web = min(dimensions.depth, dimensions.width) / Decimal(10)
        flange = web
    elif isinstance(dimensions, AngleProfileDimensions):
        depth = dimensions.leg_y
        width = dimensions.leg_z
        web = dimensions.thickness
        flange = dimensions.thickness
    else:  # pragma: no cover - Stage 3.7A closes the profile union
        raise TypeError("Unsupported Stage 3.7A profile dimensions.")
    return ColumnBaseSignedRequest(
        request.request_id,
        request.unit_system,
        unit,
        request.concrete,
        ColumnBaseWideFlangeGeometry(
            _quantity(depth, unit),
            _quantity(width, unit),
            _quantity(web, unit),
            _quantity(flange, unit),
            _quantity(dimensions.member_length, unit),
        ),
        (
            ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
            if request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
            else ColumnBaseAssembly.SINGLE_BASE_ANGLE
        ),
        request.single_side,
        request.angle,
        request.web_layout,
        request.anchor_pattern,
        request.web_bolt_diameter,
        request.web_hole_diameter,
        request.external_anchor,
        request.signed_axial_force,
        request.connection_plane_shear,
        request.connection_normal_shear,
        request.user_moment,
        action_reference,
    )


def _face_positions(
    request: ColumnBaseProfileRequest,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> tuple[Decimal, Decimal]:
    surface = resolve_profile_surface(request.column_profile)
    selected = _to_st(surface.center.y, surface.center.z, origin, basis)[1]
    if request.column_profile.family in (
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    ):
        pair = rectangular_opposing_face_pair(
            request.column_profile,
            cast(MemberProfileSurfaceId, request.column_profile.selected_surface),
        )
        opposite = _to_st(
            pair.opposite_surface.center.y,
            pair.opposite_surface.center.z,
            origin,
            basis,
        )[1]
        return selected, opposite
    if surface.plane_axis is PrincipalAxisFamily.Y:
        opposite = _to_st(
            surface.opposite_plane_coordinate,
            surface.center.z,
            origin,
            basis,
        )[1]
    else:
        opposite = _to_st(
            surface.center.y,
            surface.opposite_plane_coordinate,
            origin,
            basis,
        )[1]
    return selected, opposite


def _box(
    unit: Unit,
    identity: str,
    owner: str,
    role: str,
    center: tuple[Decimal, Decimal, Decimal],
    size: tuple[Decimal, Decimal, Decimal],
    physical: str | None = None,
    region: str | None = None,
) -> ClipAngleBoxTrace:
    return ClipAngleBoxTrace(
        identity,
        owner,
        role,
        cast(
            tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
            tuple(_quantity(item, unit) for item in center),
        ),
        _quantity(size[0], unit),
        _quantity(size[1], unit),
        _quantity(size[2], unit),
        physical,
        region,
    )


def _rotate_yz(y: Decimal, z: Decimal, turns: int) -> tuple[Decimal, Decimal]:
    for _ in range(turns % 4):
        y, z = -z, y
    return y, z


def _element_box(
    request: ColumnBaseProfileRequest,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
    identity: str,
    role: str,
    y_bounds: tuple[Decimal, Decimal],
    z_bounds: tuple[Decimal, Decimal],
) -> ClipAngleBoxTrace:
    points = tuple(
        _to_st(
            *_rotate_yz(y, z, request.column_profile.orientation.quarter_turns),
            origin,
            basis,
        )
        for y in y_bounds
        for z in z_bounds
    )
    s_min, s_max = min(item[0] for item in points), max(item[0] for item in points)
    t_min, t_max = min(item[1] for item in points), max(item[1] for item in points)
    physical = f"COLUMN_{identity}"
    region = f"{physical}_MATERIAL_REGION"
    visual_id = {
        "WEB": "COLUMN-WEB",
        "POSITIVE_FLANGE": "COLUMN-FLANGE-POS-S",
        "NEGATIVE_FLANGE": "COLUMN-FLANGE-NEG-S",
    }.get(identity, physical)
    return _box(
        request.source_length_unit,
        visual_id,
        "column",
        role,
        (
            (s_min + s_max) / _TWO,
            (t_min + t_max) / _TWO,
            request.column_profile.member_length / _TWO,
        ),
        (s_max - s_min, t_max - t_min, request.column_profile.member_length),
        physical,
        region,
    )


def _column_boxes(
    request: ColumnBaseProfileRequest,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> tuple[ClipAngleBoxTrace, ...]:
    dimensions = request.column_profile.dimensions
    definitions: tuple[tuple[str, str, tuple[Decimal, Decimal], tuple[Decimal, Decimal]], ...]
    if isinstance(dimensions, WideFlangeIProfileDimensions):
        half_depth = dimensions.depth / _TWO
        half_width = dimensions.flange_width / _TWO
        clear = half_depth - dimensions.flange_thickness
        half_web = dimensions.web_thickness / _TWO
        definitions = (
            ("WEB", "COLUMN_WEB", (-half_web, half_web), (-clear, clear)),
            ("POSITIVE_FLANGE", "COLUMN_FLANGE", (-half_width, half_width), (-half_depth, -clear)),
            ("NEGATIVE_FLANGE", "COLUMN_FLANGE", (-half_width, half_width), (clear, half_depth)),
        )
    elif isinstance(dimensions, RectangularHollowProfileDimensions):
        half_y, half_z = dimensions.width / _TWO, dimensions.depth / _TWO
        wall = dimensions.wall_thickness
        definitions = (
            ("Y_POS_WALL", "RHS_WALL", (half_y - wall, half_y), (-half_z, half_z)),
            ("Y_NEG_WALL", "RHS_WALL", (-half_y, -half_y + wall), (-half_z, half_z)),
            ("Z_POS_WALL", "RHS_WALL", (-half_y + wall, half_y - wall), (half_z - wall, half_z)),
            ("Z_NEG_WALL", "RHS_WALL", (-half_y + wall, half_y - wall), (-half_z, -half_z + wall)),
        )
    elif isinstance(dimensions, SolidRectangularProfileDimensions):
        definitions = (
            (
                "SOLID_RECTANGULAR_SECTION",
                "SOLID_RECTANGULAR_COLUMN",
                (-dimensions.width / _TWO, dimensions.width / _TWO),
                (-dimensions.depth / _TWO, dimensions.depth / _TWO),
            ),
        )
    elif isinstance(dimensions, AngleProfileDimensions):
        definitions = (
            ("LEG_1", "ANGLE_COLUMN_LEG", (_ZERO, dimensions.leg_y), (_ZERO, dimensions.thickness)),
            (
                "LEG_2",
                "ANGLE_COLUMN_LEG",
                (_ZERO, dimensions.thickness),
                (dimensions.thickness, dimensions.leg_z),
            ),
        )
    else:  # pragma: no cover
        raise TypeError("Unsupported Stage 3.7A column profile.")
    return tuple(
        _element_box(request, origin, basis, identity, role, y_bounds, z_bounds)
        for identity, role, y_bounds, z_bounds in definitions
    )


def _active_faces(
    request: ColumnBaseProfileRequest, selected: Decimal, opposite: Decimal
) -> tuple[tuple[str, Decimal, Decimal], ...]:
    if request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES:
        return (("POSITIVE", selected, _ONE), ("NEGATIVE", opposite, -_ONE))
    if (
        request.column_profile.family is MemberProfileFamily.ANGLE
        and request.single_side is ColumnBaseSide.NEGATIVE_T_C
    ):
        return (("NEGATIVE", opposite, -_ONE),)
    return (("POSITIVE", selected, _ONE),)


def _connector_boxes(
    request: ColumnBaseProfileRequest, selected: Decimal, opposite: Decimal
) -> tuple[ClipAngleBoxTrace, ...]:
    values: list[ClipAngleBoxTrace] = []
    for prefix, face, outward in _active_faces(request, selected, opposite):
        owner = f"{prefix.lower()}-base-angle"
        values.extend(
            (
                _box(
                    request.source_length_unit,
                    f"{prefix}-BASE-ANGLE-VERTICAL",
                    owner,
                    "BASE_ANGLE_VERTICAL_LEG",
                    (
                        _ZERO,
                        face + outward * request.angle.thickness / _TWO,
                        request.angle.connected_leg_width / _TWO,
                    ),
                    (
                        request.angle.connector_length,
                        request.angle.thickness,
                        request.angle.connected_leg_width,
                    ),
                    f"{prefix}_BASE_ANGLE_VERTICAL_LEG",
                    f"{prefix}_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                ),
                _box(
                    request.source_length_unit,
                    f"{prefix}-BASE-ANGLE-HORIZONTAL",
                    owner,
                    "BASE_ANGLE_HORIZONTAL_LEG",
                    (
                        _ZERO,
                        face + outward * request.angle.support_leg_width / _TWO,
                        request.angle.thickness / _TWO,
                    ),
                    (
                        request.angle.connector_length,
                        request.angle.support_leg_width,
                        request.angle.thickness,
                    ),
                    f"{prefix}_BASE_ANGLE_HORIZONTAL_LEG",
                    f"{prefix}_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION",
                ),
            )
        )
    return tuple(values)


def _concrete_box(request: ColumnBaseProfileRequest) -> ClipAngleBoxTrace:
    unit = request.source_length_unit
    depth = request.concrete.depth.to(unit).magnitude
    return _box(
        unit,
        "CONCRETE-BASE",
        "concrete-base",
        "CONCRETE_BASE",
        (_ZERO, _ZERO, -depth / _TWO),
        (
            request.concrete.s_dimension.to(unit).magnitude,
            request.concrete.t_dimension.to(unit).magnitude,
            depth,
        ),
    )


def _connector_basis(outward: Decimal) -> RectangularMaterialBasis:
    return RectangularMaterialBasis(
        ExactProfileVector3D(_ONE, _ZERO, _ZERO),
        ExactProfileVector3D(_ZERO, _ZERO, _ONE),
        ExactProfileVector3D(_ZERO, -outward, _ZERO),
    )


def _path_trace(
    request: ColumnBaseProfileRequest,
    path: FullThroughBoltPath,
    start: tuple[Decimal, Decimal, Decimal],
    end: tuple[Decimal, Decimal, Decimal],
    containment: str,
) -> ColumnBasePhysicalBoltPathTrace:
    hardware = full_through_bolt_hardware(path)
    return ColumnBasePhysicalBoltPathTrace(
        path.bolt_id,
        path.axis.selected_face.value,
        path.axis.opposite_face.value,
        tuple(
            ColumnBasePhysicalPathSegmentTrace(
                item.kind.value,
                item.identity,
                _quantity(item.length, request.source_length_unit),
                item.material_region_id,
                item.material_basis is not None,
            )
            for item in path.segments
        ),
        cast(
            tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
            tuple(_quantity(item, request.source_length_unit) for item in start),
        ),
        cast(
            tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
            tuple(_quantity(item, request.source_length_unit) for item in end),
        ),
        hardware.physical_bolt_count,
        hardware.continuous_shank_count,
        hardware.internal_hardware_count,
        hardware.head_location.value,
        hardware.nut_location.value,
        tuple(item.value for item in hardware.washer_locations),
        containment,
        _successor_fingerprint(
            (
                path.bolt_id,
                path.axis.selected_face,
                path.axis.opposite_face,
                _quantity(path.axis.local_u, request.source_length_unit),
                _quantity(path.axis.local_v, request.source_length_unit),
                tuple(
                    (
                        item.kind,
                        item.identity,
                        _quantity(item.length, request.source_length_unit),
                        item.material_region_id,
                        item.material_basis,
                    )
                    for item in path.segments
                ),
            )
        ),
    )


def _rectangular_paths(
    request: ColumnBaseProfileRequest,
    selected: Decimal,
    opposite: Decimal,
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> tuple[
    tuple[ColumnBasePhysicalBoltPathTrace, ...], tuple[ClipAngleBoltTrace, ...], tuple[str, ...]
]:
    profile = request.column_profile
    unit = request.source_length_unit
    widths, lengths = _layout_coordinates(
        request.web_layout, request.angle, request.angle.connected_leg_width
    )
    pair = rectangular_opposing_face_pair(
        profile, cast(MemberProfileSurfaceId, profile.selected_surface)
    )
    v_axis = _tuple(pair.selected_frame.v_axis)
    s_axis = (_ZERO, *basis[0])
    v_sign = _dot(s_axis, v_axis)
    identities = {
        "NEAR_WALL": "RHS_NEAR_WALL",
        "CAVITY": "FREE_SHANK_CAVITY",
        "FAR_WALL": "RHS_FAR_WALL",
        "SOLID_RECTANGULAR_SECTION": "SOLID_RECTANGULAR_COLUMN",
    }
    traces: list[ColumnBasePhysicalBoltPathTrace] = []
    bolts: list[ClipAngleBoltTrace] = []
    reasons: list[str] = []
    double = request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
    for row, longitudinal in enumerate(lengths, start=1):
        for line, s in enumerate(widths, start=1):
            bolt_id = f"COLUMN-PROFILE-R{row}-B{line}"
            local_uv = (longitudinal - profile.member_length / _TWO, s * v_sign)
            core = (
                build_rhs_full_through_core(
                    profile,
                    cast(MemberProfileSurfaceId, profile.selected_surface),
                    bolt_id=bolt_id,
                    local_uv=local_uv,
                    material_region_id="COLUMN_RECTANGULAR_MATERIAL_REGION",
                )
                if profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION
                else build_srs_full_through_core(
                    profile,
                    cast(MemberProfileSurfaceId, profile.selected_surface),
                    bolt_id=bolt_id,
                    local_uv=local_uv,
                    material_region_id="COLUMN_SOLID_RECTANGULAR_MATERIAL_REGION",
                )
            )
            core = replace(
                core,
                segments=tuple(
                    replace(item, identity=identities.get(item.identity, item.identity))
                    for item in core.segments
                ),
            )
            near = external_connector_layer(
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                request.angle.thickness,
                material_region_id="POSITIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                material_basis=_connector_basis(_ONE),
            )
            far = (
                (
                    external_connector_layer(
                        "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
                        request.angle.thickness,
                        material_region_id="NEGATIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                        material_basis=_connector_basis(-_ONE),
                    ),
                )
                if double
                else ()
            )
            path = compose_external_connector_layers(core, near_layers=(near,), far_layers=far)
            containment = evaluate_full_through_containment(
                profile,
                path.axis,
                bolt_id=bolt_id,
                hole_radius=request.web_hole_diameter.to(unit).magnitude / _TWO,
            )
            if containment.status.value != "VALID":
                reasons.append(f"FULL_THROUGH_HOLE_CONTAINMENT_INVALID:{bolt_id}")
            start_t = selected + request.angle.thickness
            end_t = opposite - (request.angle.thickness if double else _ZERO)
            trace = _path_trace(
                request,
                path,
                (s, start_t, longitudinal),
                (s, end_t, longitudinal),
                containment.status.value,
            )
            traces.append(trace)
            bolts.append(
                ClipAngleBoltTrace(
                    bolt_id,
                    f"ROW_{row}",
                    f"BOLT_LINE_{line}",
                    _quantity(s, unit),
                    _quantity(longitudinal, unit),
                    (
                        _quantity(s, unit),
                        _quantity((selected + opposite) / _TWO, unit),
                        _quantity(longitudinal, unit),
                    ),
                    (_ZERO, -_ONE, _ZERO),
                    tuple(item.identity for item in path.segments),
                    trace.stack_start_s_t_l,
                    trace.stack_end_s_t_l,
                )
            )
    return tuple(traces), tuple(bolts), tuple(reasons)


def _open_profile_paths(
    request: ColumnBaseProfileRequest,
    legacy: ColumnBaseSignedRequest,
    selected: Decimal,
    opposite: Decimal,
    origin: tuple[Decimal, Decimal],
    basis: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]],
) -> tuple[
    tuple[ColumnBasePhysicalBoltPathTrace, ...], tuple[ClipAngleBoltTrace, ...], tuple[str, ...]
]:
    unit = request.source_length_unit
    widths, lengths = _layout_coordinates(
        request.web_layout, request.angle, request.angle.connected_leg_width
    )
    double = request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
    traces: list[ColumnBasePhysicalBoltPathTrace] = []
    bolts: list[ClipAngleBoltTrace] = []
    reasons: list[str] = []
    profile = request.column_profile
    surface = resolve_profile_surface(profile)
    negative_angle_single = (
        profile.family is MemberProfileFamily.ANGLE
        and not double
        and request.single_side is ColumnBaseSide.NEGATIVE_T_C
    )
    if profile.family is MemberProfileFamily.WIDE_FLANGE_I:
        thickness = cast(WideFlangeIProfileDimensions, profile.dimensions).web_thickness
        column_identity = "COLUMN_WEB"
    else:
        thickness = cast(AngleProfileDimensions, profile.dimensions).thickness
        column_identity = "SELECTED_ANGLE_COLUMN_LEG"
    for row, longitudinal in enumerate(lengths, start=1):
        for line, s in enumerate(widths, start=1):
            bolt_id = f"COLUMN-PROFILE-R{row}-B{line}"
            prefix = (
                "NEGATIVE_BASE_ANGLE_VERTICAL_LEG"
                if negative_angle_single
                else "POSITIVE_BASE_ANGLE_VERTICAL_LEG"
            )
            segment_data = [
                (
                    PhysicalBoltPathSegmentKind.MATERIAL_LAYER.value,
                    prefix,
                    request.angle.thickness,
                    f"{prefix}_MATERIAL_REGION",
                    True,
                ),
                (
                    PhysicalBoltPathSegmentKind.MATERIAL_LAYER.value,
                    column_identity,
                    thickness,
                    f"{column_identity}_MATERIAL_REGION",
                    True,
                ),
            ]
            if double:
                segment_data.append(
                    (
                        PhysicalBoltPathSegmentKind.MATERIAL_LAYER.value,
                        "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
                        request.angle.thickness,
                        "NEGATIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                        True,
                    )
                )
            containment_status = "VALID"
            if profile.family is MemberProfileFamily.ANGLE:
                local_x = longitudinal - profile.member_length / _TWO
                s_axis = basis[0]
                local_y = origin[0] + s * s_axis[0]
                local_z = origin[1] + s * s_axis[1]
                if surface.plane_axis is PrincipalAxisFamily.Y:
                    point = ExactProfileVector3D(local_x, surface.plane_coordinate, local_z)
                else:
                    point = ExactProfileVector3D(local_x, local_y, surface.plane_coordinate)
                resolution = resolve_angle_leg_bolt_path(profile, point)
                if not resolution.valid:
                    containment_status = "INVALID_GEOMETRY"
                    reasons.append(f"ANGLE_BOLT_PATH_INVALID:{bolt_id}:{resolution.reason}")
            if negative_angle_single:
                start = (s, opposite - request.angle.thickness, longitudinal)
                end = (s, selected, longitudinal)
                bolt_axis = (_ZERO, _ONE, _ZERO)
            else:
                start = (s, selected + request.angle.thickness, longitudinal)
                end = (
                    s,
                    opposite - (request.angle.thickness if double else _ZERO),
                    longitudinal,
                )
                bolt_axis = (_ZERO, -_ONE, _ZERO)
            segments = tuple(
                ColumnBasePhysicalPathSegmentTrace(
                    kind,
                    identity,
                    _quantity(length, unit),
                    region,
                    axes,
                )
                for kind, identity, length, region, axes in segment_data
            )
            fingerprint = _successor_fingerprint(
                (
                    bolt_id,
                    tuple(
                        (
                            kind,
                            identity,
                            _quantity(length, unit),
                            region,
                            axes,
                        )
                        for kind, identity, length, region, axes in segment_data
                    ),
                    tuple(_quantity(item, unit) for item in start),
                    tuple(_quantity(item, unit) for item in end),
                )
            )
            trace = ColumnBasePhysicalBoltPathTrace(
                bolt_id,
                cast(MemberProfileSurfaceId, profile.selected_surface).value,
                surface.opposing_patch_ids[0],
                segments,
                cast(
                    tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
                    tuple(_quantity(item, unit) for item in start),
                ),
                cast(
                    tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
                    tuple(_quantity(item, unit) for item in end),
                ),
                1,
                1,
                0,
                "EXTERIOR_NEAR_SIDE",
                "EXTERIOR_FAR_SIDE",
                ("EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"),
                containment_status,
                fingerprint,
            )
            traces.append(trace)
            bolts.append(
                ClipAngleBoltTrace(
                    bolt_id,
                    f"ROW_{row}",
                    f"BOLT_LINE_{line}",
                    _quantity(s, unit),
                    _quantity(longitudinal, unit),
                    (
                        _quantity(s, unit),
                        _quantity((selected + opposite) / _TWO, unit),
                        _quantity(longitudinal, unit),
                    ),
                    bolt_axis,
                    tuple(item.identity for item in segments),
                    trace.stack_start_s_t_l,
                    trace.stack_end_s_t_l,
                )
            )
    if profile.family is MemberProfileFamily.WIDE_FLANGE_I:
        historical_bolts = _preview(legacy, resistance=False)[0].visualization
        if historical_bolts is not None:
            bolts = list(historical_bolts.web_bolts)
    return tuple(traces), tuple(bolts), tuple(reasons)


def _anchors(
    request: ColumnBaseProfileRequest,
    prefix: str,
    face: Decimal,
    outward: Decimal,
) -> tuple[ColumnBaseAnchorTrace, ...]:
    unit = request.source_length_unit
    pattern = request.anchor_pattern
    row_center = Decimal(pattern.row_count - 1) / _TWO
    line_center = Decimal(pattern.anchors_per_row - 1) / _TWO
    offset = pattern.centroid_offset_t.to(unit).magnitude
    center_t = (
        outward * offset
        if request.column_profile.family is not MemberProfileFamily.ANGLE
        else face + outward * offset
    )
    group_id = f"{prefix}_BASE_ANCHOR_GROUP"
    embedment = request.external_anchor.specified_embedment.to(unit).magnitude
    washer = request.external_anchor.washer_thickness.to(unit).magnitude
    return tuple(
        ColumnBaseAnchorTrace(
            f"{group_id}-R{row + 1}-A{line + 1}",
            group_id,
            _vector((s, t, _ZERO), unit),
            (_ZERO, _ZERO, Decimal(-1)),
            _vector((s, t, _ZERO), unit),
            _vector((s, t, -embedment), unit),
            _vector((s, t, request.angle.thickness + washer / _TWO), unit),
            _vector((s, t, request.angle.thickness + washer), unit),
            (f"{prefix}_BASE_ANGLE_HORIZONTAL_LEG", "CONCRETE_BASE"),
        )
        for row in range(pattern.row_count)
        for line in range(pattern.anchors_per_row)
        for s in ((Decimal(row) - row_center) * pattern.pitch.to(unit).magnitude,)
        for t in (
            center_t + outward * (Decimal(line) - line_center) * pattern.gauge.to(unit).magnitude,
        )
    )


def _anchor_groups(
    request: ColumnBaseProfileRequest,
    selected: Decimal,
    opposite: Decimal,
    force: tuple[Decimal, Decimal, Decimal],
    source_reference: tuple[Decimal, Decimal, Decimal],
    proof: ColumnBaseProfileSymmetryProof,
) -> tuple[ColumnBaseAnchorGroupResult, ...]:
    unit = request.source_length_unit
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    values: list[ColumnBaseAnchorGroupResult] = []
    for prefix, face, outward in _active_faces(request, selected, opposite):
        anchors = _anchors(request, prefix, face, outward)
        reference = (
            _ZERO,
            anchors[0].coordinate_s_t_l.t.to(unit).magnitude
            if len(anchors) == 1
            else sum((item.coordinate_s_t_l.t.to(unit).magnitude for item in anchors), start=_ZERO)
            / Decimal(len(anchors)),
            _ZERO,
        )
        if request.assembly is ColumnBaseAssembly.SINGLE_BASE_ANGLE:
            branch_force = force
            wrench = _wrench(
                reference,
                branch_force,
                source_reference,
                unit,
                force_unit,
                moment_unit,
                "EXACT_SINGLE_ANGLE_TRANSLATION_TO_BASE_ANCHOR_GROUP",
            )
        elif proof.complete_branch_half_sharing_eligible:
            branch_force = cast(
                tuple[Decimal, Decimal, Decimal], tuple(item * _HALF for item in force)
            )
            wrench = _wrench(
                reference,
                branch_force,
                source_reference,
                unit,
                force_unit,
                moment_unit,
                "EXACT_PROVEN_SYMMETRIC_BRANCH_TRANSLATION_TO_BASE_ANCHOR_GROUP",
            )
        else:
            wrench = None
        corners = (
            _vector((-request.angle.connector_length / _TWO, face, _ZERO), unit),
            _vector((request.angle.connector_length / _TWO, face, _ZERO), unit),
            _vector(
                (
                    request.angle.connector_length / _TWO,
                    face + outward * request.angle.support_leg_width,
                    _ZERO,
                ),
                unit,
            ),
            _vector(
                (
                    -request.angle.connector_length / _TWO,
                    face + outward * request.angle.support_leg_width,
                    _ZERO,
                ),
                unit,
            ),
        )
        footprint = ColumnBaseBearingFootprint(
            f"{prefix}_BASE_ANGLE_BEARING_FOOTPRINT",
            f"{prefix}_BASE_ANGLE",
            corners,
        )
        values.append(
            ColumnBaseAnchorGroupResult(
                f"{prefix}_BASE_ANCHOR_GROUP",
                ColumnBaseSide.POSITIVE_T_C if outward > 0 else ColumnBaseSide.NEGATIVE_T_C,
                _vector(reference, unit),
                anchors,
                footprint,
                wrench,
            )
        )
    return tuple(values)


def _symmetry_proof(
    request: ColumnBaseProfileRequest,
    action_reference: ColumnBaseVector,
) -> ColumnBaseProfileSymmetryProof:
    double = request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
    rectangular = request.column_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
        MemberProfileFamily.WIDE_FLANGE_I,
    }
    member_midplane = action_reference.t.canonical_magnitude == 0
    normal_zero = request.connection_normal_shear.canonical_magnitude == 0
    user_zero = all(item.canonical_magnitude == 0 for item in request.user_moment_tuple)
    complete = double and rectangular and member_midplane and normal_zero and user_zero
    angle_local = double and request.column_profile.family is MemberProfileFamily.ANGLE
    return ColumnBaseProfileSymmetryProof(
        double,
        double,
        double,
        member_midplane,
        normal_zero,
        user_zero,
        complete,
        angle_local,
        "EXACT_HALF_SHARING" if complete else "NOT_EVALUATED",
    )


def _component_transfer(
    request: ColumnBaseProfileRequest,
    proof: ColumnBaseProfileSymmetryProof,
) -> ColumnBaseProfileComponentTransferTrace:
    force = request.signed_axial_force
    canonical = force.canonical_magnitude
    zero_like = PhysicalQuantity.of(0, force.unit)
    mode = "UPLIFT" if canonical > 0 else "COMPRESSION" if canonical < 0 else "ZERO"
    signed_lw = "+LW" if canonical > 0 else "-LW" if canonical < 0 else "LW"
    signed_cw = "+CW" if canonical > 0 else "-CW" if canonical < 0 else "CW"
    design = PhysicalQuantity.of(abs(force.magnitude), force.unit)
    if request.assembly is ColumnBaseAssembly.SINGLE_BASE_ANGLE:
        positive = force if request.single_side is ColumnBaseSide.POSITIVE_T_C else None
        negative = force if request.single_side is ColumnBaseSide.NEGATIVE_T_C else None
        single = force
        fraction = _ONE
        allocation = "FULL_SINGLE_BRANCH"
    else:
        fraction = _HALF
        positive = PhysicalQuantity.of(force.magnitude * _HALF, force.unit)
        negative = PhysicalQuantity.of(force.magnitude * _HALF, force.unit)
        single = None
        allocation = proof.complete_branch_allocation
        if request.column_profile.family is MemberProfileFamily.ANGLE:
            positive = negative = None
    return ColumnBaseProfileComponentTransferTrace(
        mode,
        force,
        design,
        _ONE,
        "LW",
        signed_lw,
        force,
        design,
        _ONE,
        "CW",
        signed_cw,
        positive,
        negative,
        single,
        fraction,
        allocation,
        force if canonical != 0 else zero_like,
    )


def _renamed_demands(
    request: ColumnBaseProfileRequest,
    legacy: ColumnBaseSignedRequest,
    demand: EccentricDemandResult,
) -> tuple[tuple[ColumnBaseLayerDemandTrace, ...], tuple[ColumnBaseLayerDirectionTrace, ...]]:
    column_id = {
        MemberProfileFamily.WIDE_FLANGE_I: "COLUMN_WEB",
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION: "COLUMN_RECTANGULAR_SECTION",
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION: "COLUMN_SOLID_RECTANGULAR_SECTION",
        MemberProfileFamily.ANGLE: "SELECTED_ANGLE_COLUMN_LEG",
    }[request.column_profile.family]
    rename = {"COLUMN_WEB": column_id}
    demands = tuple(
        replace(item, layer_id=rename.get(item.layer_id, item.layer_id))
        for item in _layer_demands_for_request(legacy, demand)
    )
    directions = tuple(
        replace(item, layer_id=rename.get(item.layer_id, item.layer_id))
        for item in _layer_directions(legacy)
    )
    return demands, directions


def _material_regions_for_profile(
    request: ColumnBaseProfileRequest,
    legacy: ColumnBaseSignedRequest,
    boxes: tuple[ClipAngleBoxTrace, ...],
) -> tuple[ClipAngleMaterialRegionTrace, ...]:
    if request.column_profile.family is MemberProfileFamily.WIDE_FLANGE_I:
        return _material_regions(legacy)
    connector_regions = tuple(
        item for item in _material_regions(legacy) if "BASE_ANGLE" in item.region_id
    )
    topology = create_oriented_standard_topology(request.column_profile.section_family)
    role_by_identity = {
        "COLUMN_WEB": PhysicalSectionElementRole.WEB,
        "COLUMN_POSITIVE_FLANGE": PhysicalSectionElementRole.TOP_FLANGE,
        "COLUMN_NEGATIVE_FLANGE": PhysicalSectionElementRole.BOTTOM_FLANGE,
        "COLUMN_Y_POS_WALL": PhysicalSectionElementRole.SIDE_WALL_2,
        "COLUMN_Y_NEG_WALL": PhysicalSectionElementRole.SIDE_WALL_1,
        "COLUMN_Z_POS_WALL": PhysicalSectionElementRole.TOP_WALL,
        "COLUMN_Z_NEG_WALL": PhysicalSectionElementRole.BOTTOM_WALL,
        "COLUMN_SOLID_RECTANGULAR_SECTION": PhysicalSectionElementRole.PLATE,
        "COLUMN_LEG_1": PhysicalSectionElementRole.LEG_1,
        "COLUMN_LEG_2": PhysicalSectionElementRole.LEG_2,
    }
    regions = {item.id: item for item in topology.material_regions}
    elements = {item.role: item for item in topology.elements}

    def profile_axis(axis: PrincipalAxisFamily, sign: int) -> tuple[Decimal, Decimal, Decimal]:
        raw = {
            PrincipalAxisFamily.X: (_ONE, _ZERO, _ZERO),
            PrincipalAxisFamily.Y: (_ZERO, _ONE, _ZERO),
            PrincipalAxisFamily.Z: (_ZERO, _ZERO, _ONE),
        }[axis]
        rotated_y, rotated_z = _rotate_yz(
            raw[1], raw[2], request.column_profile.orientation.quarter_turns
        )
        rotated = (raw[0], rotated_y, rotated_z)
        surface = resolve_profile_surface(request.column_profile)
        normal = _tuple(surface.local_outward_normal)
        s_axis = (_ZERO, normal[2], -normal[1])
        return (
            Decimal(sign) * _dot(rotated, s_axis),
            Decimal(sign) * _dot(rotated, normal),
            Decimal(sign) * rotated[0],
        )

    values: list[ClipAngleMaterialRegionTrace] = []
    for box in boxes:
        if (
            box.owner_id != "column"
            or box.material_region_id is None
            or box.physical_element_id is None
        ):
            continue
        element = elements[role_by_identity[box.physical_element_id]]
        orientation = regions[element.material_region_id].orientation
        if not isinstance(orientation, PlanarFixedMaterialOrientation):  # pragma: no cover
            raise ValueError("Stage 3.7A planar FRP regions require exact material axes.")
        values.append(
            ClipAngleMaterialRegionTrace(
                box.material_region_id,
                box.physical_element_id,
                profile_axis(PrincipalAxisFamily.X, 1),
                profile_axis(orientation.crosswise_axis, orientation.crosswise_sign),
                profile_axis(
                    orientation.through_thickness_axis,
                    orientation.through_thickness_sign,
                ),
            )
        )
    return (*values, *connector_regions)


def _geometry_reasons_for_profile(
    request: ColumnBaseProfileRequest,
    legacy: ColumnBaseSignedRequest,
    paths: tuple[ColumnBasePhysicalBoltPathTrace, ...],
    groups: tuple[ColumnBaseAnchorGroupResult, ...],
) -> tuple[str, ...]:
    reasons = [
        f"PHYSICAL_BOLT_PATH_INVALID:{item.bolt_id}"
        for item in paths
        if item.containment_status != "VALID"
    ]
    if request.column_profile.family is MemberProfileFamily.WIDE_FLANGE_I:
        reasons.extend(_geometry_reasons(legacy, (), groups))
    if request.column_profile.family is MemberProfileFamily.ANGLE:
        dimensions = cast(AngleProfileDimensions, request.column_profile.dimensions)
        clear_selected_leg = (
            dimensions.leg_y - dimensions.thickness
            if request.column_profile.selected_surface is MemberProfileSurfaceId.LEG_Y_OUTER
            else dimensions.leg_z - dimensions.thickness
        )
        if request.angle.connector_length > clear_selected_leg:
            reasons.append("ANGLE_CONNECTOR_HEEL_OR_PERPENDICULAR_LEG_INTERFERENCE")
    if (
        request.external_anchor.specified_embedment.canonical_magnitude
        > request.concrete.depth.canonical_magnitude
    ):
        reasons.append("ANCHOR_EMBEDMENT_EXCEEDS_CONCRETE_DEPTH")
    return tuple(dict.fromkeys(reasons))


def _canonical_profile_identity(request: ColumnBaseProfileRequest) -> tuple[object, ...]:
    dimensions = request.column_profile.dimensions
    dimension_values = tuple(
        (
            item.name,
            _quantity(cast(Decimal, getattr(dimensions, item.name)), request.source_length_unit),
        )
        for item in fields(dimensions)
    )
    return (
        request.column_profile.family,
        request.column_profile.orientation,
        request.column_profile.selected_surface,
        dimension_values,
    )


def _canonical_frame_identity(
    frame: ColumnBaseConnectionFrameTrace, unit: Unit
) -> tuple[object, ...]:
    return (
        frame.selected_surface,
        tuple(_quantity(item, unit) for item in frame.origin_profile_xyz),
        frame.s_axis_profile_xyz,
        frame.t_axis_profile_xyz,
        frame.l_axis_profile_xyz,
        frame.handedness,
    )


def _canonical_connector_identity(request: ColumnBaseProfileRequest) -> tuple[object, ...]:
    unit = request.source_length_unit
    layout = request.web_layout
    return (
        tuple(
            _quantity(cast(Decimal, getattr(request.angle, name)), unit)
            for name in (
                "connected_leg_width",
                "support_leg_width",
                "thickness",
                "connector_length",
            )
        ),
        layout.row_count,
        layout.bolts_per_row,
        tuple(
            None
            if getattr(layout, name) is None
            else _quantity(cast(Decimal, getattr(layout, name)), unit)
            for name in (
                "pitch",
                "gauge",
                "heel_edge_distance",
                "free_edge_distance",
                "negative_end_distance",
                "positive_end_distance",
                "length_offset",
                "width_offset",
            )
        ),
        layout.placement_mode,
    )


def _preview_profile(
    request: ColumnBaseProfileRequest, *, resistance: bool
) -> tuple[ColumnBaseProfilePreviewResult, object | None]:
    unit = request.source_length_unit
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    frame_trace, origin, basis = _profile_frame(request.column_profile)
    action_reference = _member_reference(request, origin, basis)
    legacy = _legacy_request(request, action_reference)
    _, interface = _surrogate_request(legacy)
    force = (
        request.connection_plane_shear.to(force_unit).magnitude,
        request.connection_normal_shear.to(force_unit).magnitude,
        request.signed_axial_force.to(force_unit).magnitude,
    )
    source_reference = (
        action_reference.s.to(unit).magnitude,
        action_reference.t.to(unit).magnitude,
        action_reference.longitudinal.to(unit).magnitude,
    )
    selected, opposite = _face_positions(request, origin, basis)
    proof = _symmetry_proof(request, action_reference)
    groups = _anchor_groups(request, selected, opposite, force, source_reference, proof)
    if request.column_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        paths, bolts, path_reasons = _rectangular_paths(request, selected, opposite, basis)
    else:
        paths, bolts, path_reasons = _open_profile_paths(
            request, legacy, selected, opposite, origin, basis
        )
    reasons = (*path_reasons, *_geometry_reasons_for_profile(request, legacy, paths, groups))
    reasons = tuple(dict.fromkeys(reasons))
    geometry_valid = not reasons
    combined = _wrench(
        (_ZERO, _ZERO, _ZERO),
        force,
        source_reference,
        unit,
        force_unit,
        moment_unit,
        "EXACT_COLUMN_ACTION_TRANSLATION_TO_FOUNDATION_BASE_REFERENCE_COUNTED_ONCE",
    )
    component = _component_transfer(request, proof)
    axial = request.signed_axial_force.canonical_magnitude
    limitations = (
        *_PROFILE_LIMITATIONS,
        *(
            (("COLUMN_END_BEARING_FOR_UPLIFT", "NOT_REQUIRED"),)
            if axial > 0
            else (("COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION", "EXTERNAL_DESIGN_REQUIRED"),)
            if axial < 0
            else ()
        ),
        *(
            (("DOUBLE_BASE_ANGLE_BRANCH_WRENCH_ALLOCATION", "NOT_EVALUATED"),)
            if request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
            and not proof.complete_branch_half_sharing_eligible
            else ()
        ),
        *(
            (("ANGLE_COLUMN_BASE_ANGLE_BRANCH_WRENCH_ALLOCATION", "NOT_EVALUATED"),)
            if request.column_profile.family is MemberProfileFamily.ANGLE
            and request.assembly is ColumnBaseAssembly.DOUBLE_BASE_ANGLES
            else ()
        ),
    )
    input_fingerprint = _successor_fingerprint(
        (
            request.contract_version,
            _canonical_profile_identity(request),
            request.assembly,
            request.single_side,
            _canonical_connector_identity(request),
            request.anchor_pattern,
            request.concrete,
            request.web_bolt_diameter,
            request.web_hole_diameter,
            request.external_anchor,
            request.signed_axial_force,
            request.connection_plane_shear,
            request.connection_normal_shear,
            action_reference,
        )
    )
    handoff_payload = (
        input_fingerprint,
        _canonical_frame_identity(frame_trace, unit),
        action_reference,
        combined,
        component,
        proof,
        groups,
        paths,
        limitations,
    )
    handoff_fingerprint = _successor_fingerprint(handoff_payload)
    handoff = ColumnBaseProfileExternalHandoff(
        COLUMN_BASE_PROFILE_HANDOFF_SCHEMA_VERSION,
        request.request_id,
        request.unit_system.value,
        request.column_profile.family.value,
        cast(MemberProfileSurfaceId, request.column_profile.selected_surface).value,
        frame_trace,
        action_reference,
        combined,
        component,
        proof,
        groups,
        paths,
        limitations,
        ("2.5A-RC1", "2.4B-RC2", "3.3C1-RC1", request.contract_version),
        input_fingerprint,
        handoff_fingerprint,
    )
    handoff_json = json.dumps(
        cast(dict[str, object], _canonical_export(handoff)),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    response = None
    if (
        resistance
        and geometry_valid
        and request.column_profile.family is MemberProfileFamily.WIDE_FLANGE_I
    ):
        response = _preview(legacy, resistance=True)[1]
    failed = response is not None and any(
        item.overall_disposition.value == "FAIL" for item in response.automatic_handoff_results
    )
    status = (
        ColumnBaseStatus.INVALID_GEOMETRY
        if not geometry_valid
        else ColumnBaseStatus.FAIL
        if failed
        else ColumnBaseStatus.NOT_EVALUATED
    )
    layer_demands, directions = _renamed_demands(request, legacy, interface.demand)
    boxes = (
        _concrete_box(request),
        *_column_boxes(request, origin, basis),
        *_connector_boxes(request, selected, opposite),
    )
    regions = _material_regions_for_profile(request, legacy, boxes)
    demand_identity = tuple(
        (
            item.bolt_id,
            item.total_force.u,
            item.total_force.v,
            item.total_force_magnitude,
        )
        for scenario in interface.demand.scenarios
        for item in scenario.per_bolt
    )
    application_fingerprint = _successor_fingerprint(
        (input_fingerprint, demand_identity, paths, groups, handoff_fingerprint, reasons)
    )
    engineering_fingerprint = _successor_fingerprint(
        (application_fingerprint, status, None if response is None else response.calculation_result)
    )
    warnings = tuple(dict.fromkeys((*reasons, *(f"{name}={value}" for name, value in limitations))))
    visualization = (
        None
        if not geometry_valid
        else ColumnBaseProfileVisualizationSnapshot(
            CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
            ColumnBaseFrame(),
            frame_trace,
            request.column_profile.family.value,
            cast(MemberProfileSurfaceId, request.column_profile.selected_surface).value,
            boxes,
            bolts,
            paths,
            tuple(anchor for group in groups for anchor in group.anchors),
            request.web_bolt_diameter,
            request.web_hole_diameter,
            request.external_anchor,
            regions,
            _vector(force, force_unit),
            action_reference,
            tuple(item[0] for item in _active_faces(request, selected, opposite)),
        )
    )
    preview = ColumnBaseProfilePreviewResult(
        request.request_id,
        request.contract_version,
        CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
        "COLUMN_BASE_USING_SINGLE_OR_DOUBLE_BASE_ANGLES_TO_CONCRETE",
        ColumnBaseFrame(),
        frame_trace,
        request.column_profile.family.value,
        cast(MemberProfileSurfaceId, request.column_profile.selected_surface).value,
        action_reference,
        request.assembly,
        request.single_side,
        interface.demand,
        layer_demands,
        directions,
        component,
        proof,
        paths,
        combined,
        groups,
        handoff,
        handoff_json,
        ColumnBaseGeometryStatus.VALID
        if geometry_valid
        else ColumnBaseGeometryStatus.INVALID_GEOMETRY,
        reasons,
        status,
        False,
        response is not None,
        geometry_valid and any(item != 0 for item in force),
        limitations,
        warnings,
        engineering_fingerprint,
        application_fingerprint,
        visualization,
    )
    return preview, response


def preview_column_base_profiles(request: ColumnBaseProfileRequest) -> ColumnBasePreviewResult:
    """Resolve Stage 3.7A geometry/demand/handoff with zero resistance calls."""

    return cast(ColumnBasePreviewResult, _preview_profile(request, resistance=False)[0])


def design_check_column_base_profiles(request: ColumnBaseProfileRequest) -> ColumnBaseDesignResult:
    """Run only established W/I local resistance; new profile paths fail closed."""

    preview, response = _preview_profile(request, resistance=True)
    failed = preview.assembly_status is ColumnBaseStatus.FAIL
    return cast(
        ColumnBaseDesignResult,
        ColumnBaseProfileDesignResult(
            preview,
            response,
            preview.assembly_status,
            "NOT_EVALUATED",
            False,
            failed,
            _successor_fingerprint(
                (preview.engineering_fingerprint, response, preview.assembly_status)
            ),
        ),
    )


__all__ = (
    "COLUMN_BASE_PROFILE_CONTRACT_VERSION",
    "COLUMN_BASE_PROFILE_HANDOFF_SCHEMA_VERSION",
    "ColumnBaseConnectionFrameTrace",
    "ColumnBasePhysicalBoltPathTrace",
    "ColumnBasePhysicalPathSegmentTrace",
    "ColumnBaseProfileComponentTransferTrace",
    "ColumnBaseProfileDesignResult",
    "ColumnBaseProfileExternalHandoff",
    "ColumnBaseProfilePreviewResult",
    "ColumnBaseProfileSymmetryProof",
    "ColumnBaseProfileVisualizationSnapshot",
    "design_check_column_base_profiles",
    "preview_column_base_profiles",
)
