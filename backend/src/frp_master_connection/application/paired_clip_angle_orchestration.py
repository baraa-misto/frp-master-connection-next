"""Stage 3.3B backend-authoritative symmetric paired clip-angle vertical slice."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from typing import cast

from frp_master_connection.application.clip_angle_orchestration import (
    ClipAngleBoltTrace,
    ClipAngleBoxTrace,
    ClipAngleGeometryStatus,
    ClipAngleInterfacePlacementTrace,
    ClipAngleInterfaceResult,
    ClipAngleMaterialRegionTrace,
    ClipAngleOrchestrationRequest,
    ClipAngleProfileMaterialRegionTrace,
    ClipAngleSupportProfileTrace,
    ClipAngleTriangleMeshTrace,
    ClipAngleTrimTrace,
    ClipAngleVectorInput,
    _anchor_coordinates,
    _boxes,
    _dot_force,
    _fingerprint,
    _interface_design_ready,
    _layout_fingerprint_value,
    _length_fields,
    _material_regions,
    _multirow_request,
    _placed_connected_profile,
    _placed_support_profile,
    _placement,
    _point_quantities,
    _profile_thickness,
    _profile_visualization,
    _quantity,
    _quantity_point,
    _rectangular_local_uv,
    _resolve_interface,
    _support_selection,
    _supported_failure,
    _trim,
    _trimmed_profile_meshes,
    _with_resistance,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationResponse,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.application.shared_support_integration import (
    IntegratedFullThroughBoltTrace,
    build_integrated_full_through_bolt,
    require_shared_support_selection,
)
from frp_master_connection.calculation import (
    LayerInPlaneDemandAllocation,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    decimal_from_finite_real,
)
from frp_master_connection.calculation.eccentric_demand import (
    EccentricDemandResult,
    InPlaneQuantityVector,
)
from frp_master_connection.domain import (
    ClipAngleBoltLayout,
    ClipAngleDimensions,
    ClipAngleHand,
    ClipAngleInterfaceIdentity,
    ClipAngleLengthAnchor,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    EngineeringUnitSystem,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    PairedClipAngleAssemblyIdentity,
    PairedClipAngleFrame,
    PairedClipAngleGroupIdentity,
    PairedClipAngleInstanceIdentity,
    PairedClipAngleLayerIdentity,
    PairedClipAngleSymmetryProof,
    PositionVector3D,
    PrincipalAxisFamily,
    SelectedSupportFlange,
    SharedSupportTargetId,
    rectangular_opposing_face_pair,
    require_direct_tee_profile_surface,
)
from frp_master_connection.geometry import PlacedComponentGeometry3D

PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION = "3.3B-RC1"
PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION = "3.3C3-RC1"
PAIRED_CLIP_ANGLE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
PAIRED_CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"
PAIRED_CLIP_ANGLE_TRIM_PLANE_ID = "PAIRED_CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE"
PAIRED_CLIP_ANGLE_EQUAL_SHARING_REASON = "PAIRED_CLIP_ANGLE_EQUAL_SHARING_NOT_PROVEN"
PAIRED_CLIP_ANGLE_REQUIRED_CHECKS = (
    "PAIRED_CLIP_ANGLE_BODY_RESISTANCE",
    "COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE",
    "PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY",
    "PAIRED_FRP_CLIP_ANGLE_QUALIFICATION",
)

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HALF = Decimal("0.5")
_PAIR_ID = PairedClipAngleAssemblyIdentity.SYMMETRIC_PAIRED_CLIP_ANGLES.value
_POSITIVE_ID = PairedClipAngleInstanceIdentity.POSITIVE_CLIP_ANGLE.value
_NEGATIVE_ID = PairedClipAngleInstanceIdentity.NEGATIVE_CLIP_ANGLE.value
_MEMBER_ID = "clip-angle-connected-member"


class PairedClipAngleDesignStatus(StrEnum):
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class PairedClipAngleOrchestrationRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    support_role: ClipAngleSupportRole
    selected_support_flange: SelectedSupportFlange
    connector_dimensions: ClipAngleDimensions
    support_dimensions: ClipAngleSupportDimensions
    connected_member_profile: MemberProfile
    common_member_layout: ClipAngleBoltLayout
    mirrored_support_layout: ClipAngleBoltLayout
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
    orchestration_contract_version: str = PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION
    support_target_id: SharedSupportTargetId | None = None
    support_profile: MemberProfile | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version not in {
            PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION,
            PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION,
        }:
            raise ValueError("Unsupported paired clip-angle orchestration contract version.")
        legacy_allowed = {
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
        if self.orchestration_contract_version == PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION:
            if (
                self.connected_member_profile.family not in legacy_allowed
                or self.connected_member_profile.selected_surface
                not in legacy_allowed[self.connected_member_profile.family]
            ):
                raise ValueError(
                    "The legacy paired slice requires Flat Plate, W/I Web, or Channel Web."
                )
            if self.support_target_id is not None or self.support_profile is not None:
                raise ValueError("Legacy paired requests forbid C3 support fields.")
        else:
            if self.connected_member_profile.family not in {
                MemberProfileFamily.FLAT_PLATE,
                MemberProfileFamily.WIDE_FLANGE_I,
                MemberProfileFamily.CHANNEL,
                MemberProfileFamily.ANGLE,
                MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
                MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
            }:
                raise ValueError("C3 requires one of the six authorized planar connected profiles.")
            if self.support_target_id is None or self.support_profile is None:
                raise ValueError("C3 requires one shared support target/profile pair.")
            require_shared_support_selection(self.support_target_id, self.support_profile)
        _single_request(self, ClipAngleHand.POSITIVE_S_SIDE)


@dataclass(frozen=True, slots=True)
class PairedBranchActionTrace:
    branch_id: PairedClipAngleInstanceIdentity
    force: ClipAngleVectorInput
    moment: ClipAngleVectorInput
    reference_point: ClipAngleVectorInput
    parent_action_id: str


@dataclass(frozen=True, slots=True)
class PairedLayerDemandTrace:
    bolt_id: str
    layer_id: PairedClipAngleLayerIdentity
    parent_total_force: InPlaneQuantityVector
    fraction_of_total: Decimal
    force_u: PhysicalQuantity
    force_v: PhysicalQuantity
    total_force_magnitude: PhysicalQuantity
    parent_demand_fingerprint: str
    symmetry_proof_fingerprint: str


@dataclass(frozen=True, slots=True)
class PairedBoltGroupResult:
    group_id: PairedClipAngleGroupIdentity
    physical_name: str
    placement: ClipAngleInterfacePlacementTrace
    demand: EccentricDemandResult | None
    resistance: MultiRowOrchestrationResponse | None
    layer_demands: tuple[PairedLayerDemandTrace, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class PairedClipAngleVisualizationSnapshot:
    schema_version: str
    semantic_frame: PairedClipAngleFrame
    symmetry_plane: str
    connected_member_profile_id: str
    connected_member_profile_family: MemberProfileFamily
    boxes: tuple[ClipAngleBoxTrace, ...]
    meshes: tuple[ClipAngleTriangleMeshTrace, ...]
    common_member_bolts: tuple[ClipAngleBoltTrace, ...]
    positive_support_bolts: tuple[ClipAngleBoltTrace, ...]
    negative_support_bolts: tuple[ClipAngleBoltTrace, ...]
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    connected_member_material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    selected_support_surface_id: str
    selected_connected_surface_id: str
    trim: ClipAngleTrimTrace
    parent_force: ClipAngleVectorInput
    parent_moment: ClipAngleVectorInput
    parent_reference_point: ClipAngleVectorInput
    branch_actions: tuple[PairedBranchActionTrace, ...]
    support_target_id: SharedSupportTargetId
    support_profile: ClipAngleSupportProfileTrace
    support_material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]


@dataclass(frozen=True, slots=True)
class PairedClipAnglePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    assembly_identity: PairedClipAngleAssemblyIdentity
    semantic_frame: PairedClipAngleFrame
    support_role: ClipAngleSupportRole
    selected_support_flange: SelectedSupportFlange
    symmetry_proof: PairedClipAngleSymmetryProof
    symmetry_proof_fingerprint: str
    branch_actions: tuple[PairedBranchActionTrace, ...]
    common_member_group: PairedBoltGroupResult
    positive_support_group: PairedBoltGroupResult
    negative_support_group: PairedBoltGroupResult
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    trim: ClipAngleTrimTrace
    required_checks: tuple[str, ...]
    required_check_status: str
    geometry_status: ClipAngleGeometryStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: PairedClipAngleDesignStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    warnings: tuple[str, ...]
    canonical_input_fingerprint: str
    connector_geometry_fingerprint: str
    engineering_fingerprint: str
    visualization: PairedClipAngleVisualizationSnapshot | None
    rectangular_full_through_paths: tuple[IntegratedFullThroughBoltTrace, ...]
    limitations: tuple[str, ...]
    support_target_id: SharedSupportTargetId
    support_profile: ClipAngleSupportProfileTrace


@dataclass(frozen=True, slots=True)
class PairedClipAngleDesignResult:
    preview: PairedClipAnglePreviewResult
    assembly_status: PairedClipAngleDesignStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_interface_failure_present: bool
    result_fingerprint: str


def _single_request(
    request: PairedClipAngleOrchestrationRequest,
    hand: ClipAngleHand,
    *,
    force: ClipAngleVectorInput | None = None,
    reference: ClipAngleVectorInput | None = None,
) -> ClipAngleOrchestrationRequest:
    return ClipAngleOrchestrationRequest(
        request.request_id,
        request.unit_system,
        request.source_length_unit,
        hand,
        request.support_role,
        request.selected_support_flange,
        request.connector_dimensions,
        request.support_dimensions,
        request.connected_member_profile,
        request.common_member_layout,
        request.mirrored_support_layout,
        request.bolt_diameter,
        request.hole_diameter,
        request.hole_basis,
        request.global_force if force is None else force,
        request.global_moment,
        request.global_reference_point if reference is None else reference,
        request.connected_member_inclination_degrees,
        request.connected_member_end_trim_enabled,
        request.connected_member_end_clearance,
        request.connector_length_anchor,
        request.connector_length_anchor_position,
        (
            "3.3C2-RC1"
            if request.orchestration_contract_version
            == PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION
            else "3.3A-RC1"
        ),
        request.support_target_id,
        request.support_profile,
    )


def _vector_scaled(value: ClipAngleVectorInput, factor: Decimal) -> ClipAngleVectorInput:
    return ClipAngleVectorInput(value.x * factor, value.y * factor, value.z * factor)


def _vector_zero_like(value: ClipAngleVectorInput) -> ClipAngleVectorInput:
    return _vector_scaled(value, _ZERO)


def _shift_point_s(
    point: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity], shift: Decimal
) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    return (point[0] + PhysicalQuantity.of(shift, point[0].unit), point[1], point[2])


def _mirror_point_s(
    point: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    return (PhysicalQuantity.of(-point[0].magnitude, point[0].unit), point[1], point[2])


def _rename_bolt(
    value: ClipAngleBoltTrace,
    prefix: str,
    *,
    shift_s: Decimal = _ZERO,
    mirror: bool = False,
    common: bool = False,
    member_thickness: Decimal = _ZERO,
    angle_thickness: Decimal = _ZERO,
) -> ClipAngleBoltTrace:
    center = _shift_point_s(value.global_center, shift_s)
    center = _mirror_point_s(center) if mirror else center
    start = _shift_point_s(value.stack_start, shift_s)
    end = _shift_point_s(value.stack_end, shift_s)
    if mirror:
        start, end = _mirror_point_s(start), _mirror_point_s(end)
    if common:
        unit = value.global_center[0].unit
        center = (_quantity(_ZERO, unit), value.global_center[1], value.global_center[2])
        start = (
            _quantity(member_thickness / Decimal(2) + angle_thickness, unit),
            center[1],
            center[2],
        )
        end = (
            _quantity(-member_thickness / Decimal(2) - angle_thickness, unit),
            center[1],
            center[2],
        )
        axis = (Decimal(-1), _ZERO, _ZERO)
        layers = tuple(item.value for item in PairedClipAngleLayerIdentity)
    else:
        axis = value.axis
        layers = value.layer_ids
    width_coordinate = value.width_coordinate
    if not common and value.bolt_id.startswith("CLIP-B"):
        width_coordinate = width_coordinate + PhysicalQuantity.of(shift_s, width_coordinate.unit)
        if mirror:
            width_coordinate = PhysicalQuantity.of(
                -width_coordinate.magnitude, width_coordinate.unit
            )
    return replace(
        value,
        bolt_id=value.bolt_id.replace("CLIP-A", prefix).replace("CLIP-B", prefix),
        width_coordinate=width_coordinate,
        global_center=center,
        axis=axis,
        layer_ids=layers,
        stack_start=start,
        stack_end=end,
    )


def _connected_profile_span(profile: MemberProfile) -> Decimal:
    if profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        faces = rectangular_opposing_face_pair(
            profile,
            cast(MemberProfileSurfaceId, profile.selected_surface),
        )
        return abs(
            faces.selected_surface.plane_coordinate - faces.opposite_surface.plane_coordinate
        )
    return _profile_thickness(profile)


def _paired_placements(
    request: PairedClipAngleOrchestrationRequest,
) -> tuple[
    ClipAngleInterfacePlacementTrace,
    ClipAngleInterfacePlacementTrace,
    ClipAngleInterfacePlacementTrace,
    Decimal,
    Decimal,
    Decimal,
]:
    single = _single_request(request, ClipAngleHand.POSITIVE_S_SIDE)
    _selected, center, positive_end, negative_end = _anchor_coordinates(single)
    base_common = _placement(
        single,
        ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG,
        request.common_member_layout,
        request.connector_dimensions.connected_leg_width,
        positive_end,
        negative_end,
    )
    base_support = _placement(
        single,
        ClipAngleInterfaceIdentity.SUPPORT_LEG_TO_SUPPORT,
        request.mirrored_support_layout,
        request.connector_dimensions.support_leg_width,
        positive_end,
        negative_end,
    )
    member_span = _connected_profile_span(request.connected_member_profile)
    member_half = member_span / Decimal(2)
    common_bolts = tuple(
        _rename_bolt(
            item,
            "COMMON",
            common=True,
            member_thickness=member_span,
            angle_thickness=request.connector_dimensions.thickness,
        )
        for item in base_common.bolts
    )
    common = replace(
        base_common,
        bolt_group_id=PairedClipAngleGroupIdentity.COMMON_MEMBER_THROUGH_BOLT_GROUP.value,
        bolts=common_bolts,
        geometry_fingerprint=_fingerprint((base_common.geometry_fingerprint, common_bolts)),
    )
    positive_bolts = tuple(
        _rename_bolt(item, "POS-SUPPORT", shift_s=member_half) for item in base_support.bolts
    )
    positive_widths = tuple(
        item + PhysicalQuantity.of(member_half, item.unit)
        for item in base_support.width_coordinates
    )
    positive = replace(
        base_support,
        bolt_group_id=PairedClipAngleGroupIdentity.POSITIVE_SUPPORT_BOLT_GROUP.value,
        width_coordinates=positive_widths,
        bolts=positive_bolts,
        geometry_fingerprint=_fingerprint((base_support.geometry_fingerprint, positive_bolts)),
    )
    negative_bolts = tuple(
        _rename_bolt(item, "NEG-SUPPORT", shift_s=member_half, mirror=True)
        for item in base_support.bolts
    )
    negative_widths = tuple(
        PhysicalQuantity.of(-item.magnitude, item.unit) for item in positive_widths
    )
    negative = replace(
        base_support,
        bolt_group_id=PairedClipAngleGroupIdentity.NEGATIVE_SUPPORT_BOLT_GROUP.value,
        width_axis=(Decimal(-1), _ZERO, _ZERO),
        normal_axis=(_ZERO, _ONE, _ZERO),
        width_coordinates=negative_widths,
        bolts=negative_bolts,
        geometry_fingerprint=_fingerprint((base_support.geometry_fingerprint, negative_bolts)),
    )
    support_centroid = sum((item.magnitude for item in positive_widths), _ZERO) / Decimal(
        len(positive_widths)
    )
    return common, positive, negative, center, member_half, support_centroid


def _shift_position_s(value: PositionVector3D, shift: Decimal) -> PositionVector3D:
    return PositionVector3D(value.x + float(shift), value.y, value.z)


def _placement_with_full_through_paths(
    placement: ClipAngleInterfacePlacementTrace,
    paths: tuple[IntegratedFullThroughBoltTrace, ...],
    unit: Unit,
) -> ClipAngleInterfacePlacementTrace:
    if not paths:
        return placement
    by_id = {item.path.bolt_id: item for item in paths}
    if set(by_id) != {item.bolt_id for item in placement.bolts}:
        raise ValueError("Full-through paths must resolve exactly one path per placement bolt.")
    bolts = tuple(
        replace(
            item,
            layer_ids=tuple(segment.identity for segment in by_id[item.bolt_id].path.segments),
            stack_start=_point_quantities(by_id[item.bolt_id].physical_start_point, unit),
            stack_end=_point_quantities(by_id[item.bolt_id].physical_end_point, unit),
        )
        for item in placement.bolts
    )
    return replace(
        placement,
        bolts=bolts,
        geometry_fingerprint=_fingerprint(
            (placement.geometry_fingerprint, tuple(item.path_fingerprint for item in paths))
        ),
    )


def _c3_open_profile_layers(
    request: PairedClipAngleOrchestrationRequest,
    common: ClipAngleInterfacePlacementTrace,
    positive: ClipAngleInterfacePlacementTrace,
    negative: ClipAngleInterfacePlacementTrace,
) -> tuple[
    ClipAngleInterfacePlacementTrace,
    ClipAngleInterfacePlacementTrace,
    ClipAngleInterfacePlacementTrace,
]:
    connected_identity = {
        MemberProfileFamily.ANGLE: "MEMBER_ANGLE_SELECTED_LEG",
        MemberProfileFamily.FLAT_PLATE: "MEMBER_FLAT_PLATE",
        MemberProfileFamily.WIDE_FLANGE_I: "MEMBER_W_I_SELECTED_REGION",
        MemberProfileFamily.CHANNEL: "MEMBER_CHANNEL_SELECTED_REGION",
    }.get(request.connected_member_profile.family)
    if connected_identity is not None:
        bolts = tuple(
            replace(
                item,
                layer_ids=(
                    "POSITIVE_CLIP_CONNECTED_LEG",
                    connected_identity,
                    "NEGATIVE_CLIP_CONNECTED_LEG",
                ),
            )
            for item in common.bolts
        )
        common = replace(
            common,
            bolts=bolts,
            geometry_fingerprint=_fingerprint((common.geometry_fingerprint, bolts)),
        )
    support_identity = {
        SharedSupportTargetId.W_COLUMN_FLANGE: "W_FLANGE",
        SharedSupportTargetId.W_BEAM_FLANGE: "W_FLANGE",
        SharedSupportTargetId.W_COLUMN_WEB: "W_WEB",
        SharedSupportTargetId.CHANNEL_COLUMN_WEB: "CHANNEL_WEB",
        SharedSupportTargetId.ANGLE_COLUMN_LEG: "ANGLE_SELECTED_LEG",
    }.get(cast(SharedSupportTargetId, request.support_target_id))
    if support_identity is not None:
        positive_bolts = tuple(
            replace(
                item,
                layer_ids=("POSITIVE_CLIP_SUPPORT_LEG", support_identity),
            )
            for item in positive.bolts
        )
        negative_bolts = tuple(
            replace(
                item,
                layer_ids=("NEGATIVE_CLIP_SUPPORT_LEG", support_identity),
            )
            for item in negative.bolts
        )
        positive = replace(
            positive,
            bolts=positive_bolts,
            geometry_fingerprint=_fingerprint((positive.geometry_fingerprint, positive_bolts)),
        )
        negative = replace(
            negative,
            bolts=negative_bolts,
            geometry_fingerprint=_fingerprint((negative.geometry_fingerprint, negative_bolts)),
        )
    return common, positive, negative


def _open_profile_holes_contained(
    profile: MemberProfile,
    placed: PlacedComponentGeometry3D,
    bolts: tuple[ClipAngleBoltTrace, ...],
    hole_radius: Decimal,
    unit: Unit,
) -> bool:
    if profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        return True
    surface = require_direct_tee_profile_surface(profile)
    for bolt in bolts:
        coordinates = (
            decimal_from_finite_real(
                placed.global_to_local(_quantity_point(bolt.global_center, unit)).x
            )
            - profile.dimensions.member_length / Decimal(2),
            decimal_from_finite_real(
                placed.global_to_local(_quantity_point(bolt.global_center, unit)).y
            ),
            decimal_from_finite_real(
                placed.global_to_local(_quantity_point(bolt.global_center, unit)).z
            ),
        )
        contained = False
        for bounds in surface.penetration_bounds:
            minimums = (bounds.min_x, bounds.min_y, bounds.min_z)
            maximums = (bounds.max_x, bounds.max_y, bounds.max_z)
            in_plane_clearances = tuple(
                min(value - low, high - value) - hole_radius
                for axis, value, low, high in zip(
                    (PrincipalAxisFamily.X, PrincipalAxisFamily.Y, PrincipalAxisFamily.Z),
                    coordinates,
                    minimums,
                    maximums,
                    strict=True,
                )
                if axis is not surface.plane_axis
            )
            if all(item >= 0 for item in in_plane_clearances):
                contained = True
                break
        if not contained:
            return False
    return True


def _paired_rectangular_paths(
    request: PairedClipAngleOrchestrationRequest,
    placed_profile: PlacedComponentGeometry3D,
    placed_support_profile: PlacedComponentGeometry3D,
    common: ClipAngleInterfacePlacementTrace,
    positive: ClipAngleInterfacePlacementTrace,
    negative: ClipAngleInterfacePlacementTrace,
    member_half: Decimal,
) -> tuple[
    tuple[IntegratedFullThroughBoltTrace, ...],
    tuple[IntegratedFullThroughBoltTrace, ...],
    tuple[IntegratedFullThroughBoltTrace, ...],
]:
    connected_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    if request.connected_member_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:
        connected_paths = tuple(
            replace(
                trace,
                physical_start_point=_shift_position_s(trace.physical_start_point, member_half),
                physical_end_point=_shift_position_s(trace.physical_end_point, member_half),
            )
            for trace in (
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
                    hole_radius=request.hole_diameter.to(request.source_length_unit).magnitude
                    / Decimal(2),
                    connector_identity="POSITIVE_CLIP_CONNECTED_LEG",
                    connector_thickness=request.connector_dimensions.thickness,
                    connector_material_region_id="POSITIVE_CLIP_CONNECTED_LEG_REGION",
                    rectangular_material_region_id="CONNECTED_RECTANGULAR_PROFILE_REGION",
                    source_length_unit=request.source_length_unit,
                    far_connector_identity="NEGATIVE_CLIP_CONNECTED_LEG",
                    far_connector_thickness=request.connector_dimensions.thickness,
                    far_connector_material_region_id="NEGATIVE_CLIP_CONNECTED_LEG_REGION",
                )
                for item in common.bolts
            )
        )
    support_profile = cast(MemberProfile, request.support_profile)
    positive_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    negative_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    if support_profile.family in {
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }:

        def support_path(item: ClipAngleBoltTrace, identity: str) -> IntegratedFullThroughBoltTrace:
            return build_integrated_full_through_bolt(
                support_profile,
                placed_profile=placed_support_profile,
                selected_surface=cast(MemberProfileSurfaceId, support_profile.selected_surface),
                bolt_id=item.bolt_id,
                local_uv=(
                    item.length_coordinate.to(request.source_length_unit).magnitude,
                    item.width_coordinate.to(request.source_length_unit).magnitude,
                ),
                hole_radius=request.hole_diameter.to(request.source_length_unit).magnitude
                / Decimal(2),
                connector_identity=identity,
                connector_thickness=request.connector_dimensions.thickness,
                connector_material_region_id=f"{identity}_REGION",
                rectangular_material_region_id="SUPPORT_RECTANGULAR_PROFILE_REGION",
                source_length_unit=request.source_length_unit,
            )

        positive_paths = tuple(
            support_path(item, "POSITIVE_CLIP_SUPPORT_LEG") for item in positive.bolts
        )
        negative_paths = tuple(
            support_path(item, "NEGATIVE_CLIP_SUPPORT_LEG") for item in negative.bolts
        )
    return connected_paths, positive_paths, negative_paths


def _branch_actions(
    request: PairedClipAngleOrchestrationRequest,
    support_centroid: Decimal,
    eligible: bool,
) -> tuple[PairedBranchActionTrace, ...]:
    if not eligible:
        return ()
    unit = request.source_length_unit
    half_force = _vector_scaled(request.global_force, _HALF)
    zero_moment = _vector_zero_like(request.global_moment)
    base_reference = request.global_reference_point
    positive_reference = replace(base_reference, x=_quantity(support_centroid, unit))
    negative_reference = replace(base_reference, x=_quantity(-support_centroid, unit))
    return (
        PairedBranchActionTrace(
            PairedClipAngleInstanceIdentity.POSITIVE_CLIP_ANGLE,
            half_force,
            zero_moment,
            positive_reference,
            "PAIRED_CLIP_ANGLE_PARENT_ACTION",
        ),
        PairedBranchActionTrace(
            PairedClipAngleInstanceIdentity.NEGATIVE_CLIP_ANGLE,
            half_force,
            zero_moment,
            negative_reference,
            "PAIRED_CLIP_ANGLE_PARENT_ACTION",
        ),
    )


def _action_is_symmetric(request: PairedClipAngleOrchestrationRequest) -> bool:
    return (
        request.global_force.x.magnitude == 0
        and request.global_force.y.magnitude == 0
        and all(
            item.magnitude == 0
            for item in (request.global_moment.x, request.global_moment.y, request.global_moment.z)
        )
        and request.global_reference_point.x.magnitude == 0
    )


def _layer_demands(
    demand: EccentricDemandResult,
    symmetry_fingerprint: str,
) -> tuple[PairedLayerDemandTrace, ...]:
    if not demand.scenarios:
        return ()
    records: list[PairedLayerDemandTrace] = []
    for item in demand.scenarios[0].per_bolt:
        for layer, fraction in (
            (PairedClipAngleLayerIdentity.POSITIVE_CONNECTED_LEG, _HALF),
            (PairedClipAngleLayerIdentity.CONNECTED_MEMBER, _ONE),
            (PairedClipAngleLayerIdentity.NEGATIVE_CONNECTED_LEG, _HALF),
        ):
            records.append(
                PairedLayerDemandTrace(
                    item.bolt_id,
                    layer,
                    item.total_force,
                    fraction,
                    item.total_force.u * fraction,
                    item.total_force.v * fraction,
                    item.total_force_magnitude * fraction,
                    demand.result_fingerprint,
                    symmetry_fingerprint,
                )
            )
    return tuple(records)


def _group(
    identity: PairedClipAngleGroupIdentity,
    name: str,
    placement: ClipAngleInterfacePlacementTrace,
    interface: ClipAngleInterfaceResult | None,
    layer_demands: tuple[PairedLayerDemandTrace, ...] = (),
    *,
    c3_fingerprint: bool = False,
) -> PairedBoltGroupResult:
    fingerprint_payload = (
        (
            identity,
            placement.geometry_fingerprint,
            None if interface is None else interface.interface_fingerprint,
            None if interface is None else interface.demand.result_fingerprint,
            None if interface is None else interface.resistance,
            layer_demands,
        )
        if c3_fingerprint
        else (identity, placement.geometry_fingerprint, interface, layer_demands)
    )
    return PairedBoltGroupResult(
        identity,
        name,
        placement,
        None if interface is None else interface.demand,
        None if interface is None else interface.resistance,
        layer_demands,
        _fingerprint(fingerprint_payload),
    )


def _with_common_resistance(
    request: PairedClipAngleOrchestrationRequest,
    single: ClipAngleOrchestrationRequest,
    result: ClipAngleInterfaceResult,
    layer_demands: tuple[PairedLayerDemandTrace, ...],
) -> ClipAngleInterfaceResult:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    force_u = _dot_force(single.global_force, result.placement.width_axis, force_unit)
    force_v = _dot_force(single.global_force, result.placement.length_axis, force_unit)
    base = _multirow_request(
        single,
        result.placement,
        request.common_member_layout,
        force_u,
        force_v,
    )
    if base is None:
        raise ValueError("A design-ready common group must have nonzero in-plane demand.")
    member_layer, angle_layer = base.layers
    layers = (
        replace(
            angle_layer,
            layer_id=PairedClipAngleLayerIdentity.POSITIVE_CONNECTED_LEG.value,
            component_id=_POSITIVE_ID,
        ),
        replace(
            member_layer,
            layer_id=PairedClipAngleLayerIdentity.CONNECTED_MEMBER.value,
            component_id=_MEMBER_ID,
        ),
        replace(
            angle_layer,
            layer_id=PairedClipAngleLayerIdentity.NEGATIVE_CONNECTED_LEG.value,
            component_id=_NEGATIVE_ID,
        ),
    )
    allocations = tuple(
        LayerInPlaneDemandAllocation(
            item.bolt_id,
            item.layer_id.value,
            item.fraction_of_total,
            "STAGE_3_3B_CONTROLLED_SYMMETRIC_SHEAR_PLANE_ALLOCATION",
            item.parent_demand_fingerprint,
        )
        for item in layer_demands
    )
    response = evaluate_multirow_connection_with_resolved_demand(
        replace(base, layers=layers),
        result.demand,
        allocations,
    )
    return replace(result, resistance=response)


def _box_shifted(value: ClipAngleBoxTrace, shift: Decimal, prefix: str) -> ClipAngleBoxTrace:
    return replace(
        value,
        id=f"{prefix}:{value.id}",
        owner_id=prefix if value.owner_id == "single-clip-angle-connector" else value.owner_id,
        center=_shift_point_s(value.center, shift),
        physical_element_id=(
            None if value.physical_element_id is None else f"{prefix}:{value.physical_element_id}"
        ),
        material_region_id=(
            None if value.material_region_id is None else f"{prefix}:{value.material_region_id}"
        ),
    )


def _box_mirrored(value: ClipAngleBoxTrace, prefix: str) -> ClipAngleBoxTrace:
    basis_values = tuple(
        ((-axis[0], axis[1], axis[2]) if index != 2 else (axis[0], -axis[1], -axis[2]))
        for index, axis in enumerate(value.basis)
    )
    basis = cast(
        tuple[
            tuple[Decimal, Decimal, Decimal],
            tuple[Decimal, Decimal, Decimal],
            tuple[Decimal, Decimal, Decimal],
        ],
        basis_values,
    )
    return replace(
        value,
        id=value.id.replace(_POSITIVE_ID, prefix),
        owner_id=prefix,
        center=_mirror_point_s(value.center),
        basis=basis,
        physical_element_id=(
            None
            if value.physical_element_id is None
            else value.physical_element_id.replace(_POSITIVE_ID, prefix)
        ),
        material_region_id=(
            None
            if value.material_region_id is None
            else value.material_region_id.replace(_POSITIVE_ID, prefix)
        ),
    )


def _material_region_pair(
    request: PairedClipAngleOrchestrationRequest,
) -> tuple[ClipAngleMaterialRegionTrace, ...]:
    positive = tuple(
        replace(
            item,
            region_id=f"{_POSITIVE_ID}:{item.region_id}",
            physical_element_id=f"{_POSITIVE_ID}:{item.physical_element_id}",
        )
        for item in _material_regions(_single_request(request, ClipAngleHand.POSITIVE_S_SIDE))
    )
    negative_source = _material_regions(_single_request(request, ClipAngleHand.NEGATIVE_S_SIDE))
    negative = tuple(
        replace(
            item,
            region_id=f"{_NEGATIVE_ID}:{item.region_id}",
            physical_element_id=f"{_NEGATIVE_ID}:{item.physical_element_id}",
        )
        for item in negative_source
    )
    return positive + negative


def _input_fingerprint(request: PairedClipAngleOrchestrationRequest) -> str:
    if (
        request.orchestration_contract_version
        == PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION
    ):
        support = cast(MemberProfile, request.support_profile)
        return _fingerprint(
            (
                PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION,
                _length_fields(request.connector_dimensions, request.source_length_unit),
                request.connected_member_profile.role,
                request.connected_member_profile.family,
                _length_fields(
                    request.connected_member_profile.dimensions,
                    request.source_length_unit,
                ),
                request.connected_member_profile.orientation,
                request.connected_member_profile.selected_surface,
                request.support_target_id,
                support.role,
                support.family,
                _length_fields(support.dimensions, request.source_length_unit),
                support.orientation,
                support.selected_surface,
                _layout_fingerprint_value(
                    request.common_member_layout,
                    request.source_length_unit,
                ),
                _layout_fingerprint_value(
                    request.mirrored_support_layout,
                    request.source_length_unit,
                ),
                request.bolt_diameter,
                request.hole_diameter,
                request.global_force,
                request.global_moment,
                request.global_reference_point,
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
    return _fingerprint(
        (
            PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION,
            request.support_role,
            request.selected_support_flange,
            _length_fields(request.connector_dimensions, request.source_length_unit),
            _length_fields(request.support_dimensions, request.source_length_unit),
            request.connected_member_profile.role,
            request.connected_member_profile.family,
            _length_fields(
                request.connected_member_profile.dimensions,
                request.source_length_unit,
            ),
            request.connected_member_profile.orientation,
            request.connected_member_profile.selected_surface,
            _layout_fingerprint_value(
                request.common_member_layout,
                request.source_length_unit,
            ),
            _layout_fingerprint_value(
                request.mirrored_support_layout,
                request.source_length_unit,
            ),
            request.bolt_diameter,
            request.hole_diameter,
            request.global_force,
            request.global_moment,
            request.global_reference_point,
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


def _common_supported_failure(result: ClipAngleInterfaceResult) -> bool:
    resistance = result.resistance
    if resistance is None:
        return False
    return any(
        check.resistance_result is not None
        and check.resistance_result.numerical_comparison.value == "FAIL"
        for handoff in resistance.automatic_handoff_results
        for check in handoff.checks
    )


def _preview(
    request: PairedClipAngleOrchestrationRequest,
    *,
    resistance: bool,
) -> PairedClipAnglePreviewResult:
    single = _single_request(request, ClipAngleHand.POSITIVE_S_SIDE)
    common_place, positive_place, negative_place, center, member_half, support_centroid = (
        _paired_placements(request)
    )
    placed_profile = _placed_connected_profile(single)
    base_profile_boxes, profile_regions = _profile_visualization(single, placed_profile)
    support_target_id, support_profile = _support_selection(single)
    is_c3 = (
        request.orchestration_contract_version
        == PAIRED_CLIP_ANGLE_C3_ORCHESTRATION_CONTRACT_VERSION
    )
    placed_support_profile = _placed_support_profile(single, support_profile) if is_c3 else None
    support_profile_boxes, support_regions = (
        _profile_visualization(single, placed_support_profile)
        if placed_support_profile is not None
        else ((), ())
    )
    common_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    positive_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    negative_paths: tuple[IntegratedFullThroughBoltTrace, ...] = ()
    if is_c3:
        common_place, positive_place, negative_place = _c3_open_profile_layers(
            request,
            common_place,
            positive_place,
            negative_place,
        )
        common_paths, positive_paths, negative_paths = _paired_rectangular_paths(
            request,
            placed_profile,
            cast(PlacedComponentGeometry3D, placed_support_profile),
            common_place,
            positive_place,
            negative_place,
            member_half,
        )
        common_place = _placement_with_full_through_paths(
            common_place,
            common_paths,
            request.source_length_unit,
        )
        positive_place = _placement_with_full_through_paths(
            positive_place,
            positive_paths,
            request.source_length_unit,
        )
        negative_place = _placement_with_full_through_paths(
            negative_place,
            negative_paths,
            request.source_length_unit,
        )
    rectangular_paths = common_paths + positive_paths + negative_paths
    base_boxes = _boxes(
        single,
        center,
        base_profile_boxes,
        support_profile_boxes if is_c3 else (),
    )
    base_trim, trimmed = _trim(single, placed_profile, base_boxes, common_place.bolts)
    trim = replace(base_trim, reference_plane_id=PAIRED_CLIP_ANGLE_TRIM_PLANE_ID)
    profile_boxes = tuple(
        _box_shifted(item, member_half, _MEMBER_ID) for item in base_profile_boxes
    )
    profile_regions = tuple(
        replace(item, origin=_shift_point_s(item.origin, member_half)) for item in profile_regions
    )
    profile_meshes = tuple(
        replace(
            item,
            points=tuple(_shift_point_s(point, member_half) for point in item.points),
        )
        for item in _trimmed_profile_meshes(trimmed, request.source_length_unit)
    )
    positive_source = tuple(
        item for item in base_boxes if item.owner_id == "single-clip-angle-connector"
    )
    positive_boxes = tuple(
        _box_shifted(item, member_half, _POSITIVE_ID) for item in positive_source
    )
    negative_boxes = tuple(_box_mirrored(item, _NEGATIVE_ID) for item in positive_boxes)
    support_boxes = tuple(item for item in base_boxes if item.owner_id == "clip-angle-support")
    display_profile_boxes = () if trimmed is not None else profile_boxes
    boxes = positive_boxes + negative_boxes + support_boxes + display_profile_boxes

    geometry_reasons: list[str] = []
    for label, placement in (
        ("COMMON_MEMBER_THROUGH_BOLT_GROUP", common_place),
        ("POSITIVE_SUPPORT_BOLT_GROUP", positive_place),
        ("NEGATIVE_SUPPORT_BOLT_GROUP", negative_place),
    ):
        if not placement.clearances.geometry_valid:
            geometry_reasons.append(f"{label}:COMPLETE_HOLE_CONTAINMENT_INVALID")
    if any(not item.geometry_valid for item in rectangular_paths):
        geometry_reasons.append("RECTANGULAR_OPPOSING_FACE_HOLE_CONTAINMENT_INVALID")
    hole_radius = request.hole_diameter.to(request.source_length_unit).magnitude / Decimal(2)
    if is_c3 and not _open_profile_holes_contained(
        request.connected_member_profile,
        placed_profile,
        common_place.bolts,
        hole_radius,
        request.source_length_unit,
    ):
        geometry_reasons.append("CONNECTED_PROFILE_SELECTED_SURFACE_HOLE_CONTAINMENT_INVALID")
    if is_c3 and not _open_profile_holes_contained(
        support_profile,
        cast(PlacedComponentGeometry3D, placed_support_profile),
        positive_place.bolts + negative_place.bolts,
        hole_radius,
        request.source_length_unit,
    ):
        geometry_reasons.append("SUPPORT_PROFILE_SELECTED_SURFACE_HOLE_CONTAINMENT_INVALID")
    if not trim.geometry_valid:
        geometry_reasons.append("CONNECTED_MEMBER_PAIRED_CLIP_ANGLE_INTERFERENCE")
    geometry_valid = not geometry_reasons
    action_proven = _action_is_symmetric(request)
    profile_geometry_symmetric = not is_c3 or (
        request.connected_member_profile.family is not MemberProfileFamily.ANGLE
        and support_target_id
        not in {
            SharedSupportTargetId.CHANNEL_COLUMN_WEB,
            SharedSupportTargetId.ANGLE_COLUMN_LEG,
        }
    )
    geometry_symmetry_proven = geometry_valid and profile_geometry_symmetric
    proof_reasons = (
        ()
        if geometry_symmetry_proven and action_proven
        else tuple(
            item
            for item, present in (
                ("PAIR_GEOMETRY_SYMMETRY_NOT_PROVEN", not geometry_symmetry_proven),
                (PAIRED_CLIP_ANGLE_EQUAL_SHARING_REASON, not action_proven),
            )
            if present
        )
    )
    proof = PairedClipAngleSymmetryProof(
        geometry_symmetry_proven,
        action_proven,
        geometry_symmetry_proven and action_proven,
        proof_reasons,
    )
    proof_fingerprint = _fingerprint(proof)
    branches = _branch_actions(request, support_centroid, proof.equal_sharing_eligible)

    common_interface = _resolve_interface(single, common_place, request.common_member_layout)
    positive_interface: ClipAngleInterfaceResult | None = None
    negative_interface: ClipAngleInterfaceResult | None = None
    if branches:
        positive_request = _single_request(
            request,
            ClipAngleHand.POSITIVE_S_SIDE,
            force=branches[0].force,
            reference=branches[0].reference_point,
        )
        negative_request = _single_request(
            request,
            ClipAngleHand.POSITIVE_S_SIDE,
            force=branches[1].force,
            reference=branches[1].reference_point,
        )
        positive_interface = _resolve_interface(
            positive_request, positive_place, request.mirrored_support_layout
        )
        negative_interface = _resolve_interface(
            negative_request, negative_place, request.mirrored_support_layout
        )
    design_ready = (
        geometry_valid
        and proof.equal_sharing_eligible
        and not rectangular_paths
        and _interface_design_ready(common_interface)
        and positive_interface is not None
        and negative_interface is not None
        and _interface_design_ready(positive_interface)
        and _interface_design_ready(negative_interface)
    )
    common_layers = _layer_demands(common_interface.demand, proof_fingerprint)
    if resistance and design_ready:
        common_interface = _with_common_resistance(
            request,
            single,
            common_interface,
            common_layers,
        )
        positive_interface = _with_resistance(
            positive_request,
            cast(ClipAngleInterfaceResult, positive_interface),
            request.mirrored_support_layout,
        )
        negative_interface = _with_resistance(
            negative_request,
            cast(ClipAngleInterfaceResult, negative_interface),
            request.mirrored_support_layout,
        )
    common_group = _group(
        PairedClipAngleGroupIdentity.COMMON_MEMBER_THROUGH_BOLT_GROUP,
        "Positive Clip-Angle Connected Leg ↔ Connected Member ↔ Negative Clip-Angle Connected Leg",
        common_place,
        common_interface,
        common_layers,
        c3_fingerprint=is_c3,
    )
    positive_group = _group(
        PairedClipAngleGroupIdentity.POSITIVE_SUPPORT_BOLT_GROUP,
        "Positive Clip-Angle Support Leg ↔ Support",
        positive_place,
        positive_interface,
        c3_fingerprint=is_c3,
    )
    negative_group = _group(
        PairedClipAngleGroupIdentity.NEGATIVE_SUPPORT_BOLT_GROUP,
        "Negative Clip-Angle Support Leg ↔ Support",
        negative_place,
        negative_interface,
        c3_fingerprint=is_c3,
    )
    supported_failure = _common_supported_failure(common_interface) or any(
        result is not None and _supported_failure(result)
        for result in (positive_interface, negative_interface)
    )
    status = (
        PairedClipAngleDesignStatus.INVALID_GEOMETRY
        if not geometry_valid
        else (
            PairedClipAngleDesignStatus.FAIL
            if supported_failure
            else PairedClipAngleDesignStatus.NOT_EVALUATED
        )
    )
    warnings = [f"{item}_NOT_EVALUATED" for item in PAIRED_CLIP_ANGLE_REQUIRED_CHECKS]
    warnings.extend(proof.reasons)
    warnings.extend(geometry_reasons)
    limitations = tuple(
        dict.fromkeys(
            limitation.value for item in rectangular_paths for limitation in item.limitations
        )
    )
    warnings.extend(f"{item}:NOT_EVALUATED" for item in limitations)
    materials = _material_region_pair(request)
    canonical_input = _input_fingerprint(request)
    connector_geometry = (
        _fingerprint(
            (
                common_place.geometry_fingerprint,
                positive_place.geometry_fingerprint,
                negative_place.geometry_fingerprint,
                trim,
                *(item.path_fingerprint for item in rectangular_paths),
            )
        )
        if is_c3
        else _fingerprint((common_place, positive_place, negative_place, boxes, trim))
    )
    engineering = (
        _fingerprint(
            (
                canonical_input,
                connector_geometry,
                proof,
                common_group.result_fingerprint,
                positive_group.result_fingerprint,
                negative_group.result_fingerprint,
                *(item.path_fingerprint for item in rectangular_paths),
            )
        )
        if is_c3
        else _fingerprint(
            (
                canonical_input,
                connector_geometry,
                proof,
                common_group,
                positive_group,
                negative_group,
            )
        )
    )
    visualization = None
    if geometry_valid:
        selected_surface = cast(
            MemberProfileSurfaceId,
            request.connected_member_profile.selected_surface,
        )
        visualization = PairedClipAngleVisualizationSnapshot(
            PAIRED_CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION,
            PairedClipAngleFrame(),
            "S_P = 0",
            request.connected_member_profile.id,
            request.connected_member_profile.family,
            boxes,
            profile_meshes,
            common_place.bolts,
            positive_place.bolts,
            negative_place.bolts,
            request.bolt_diameter,
            request.hole_diameter,
            materials,
            profile_regions,
            (
                "clip-angle-support:"
                f"{cast(MemberProfileSurfaceId, support_profile.selected_surface).value}"
                if is_c3
                else f"clip-angle-support:{request.selected_support_flange.value}"
            ),
            f"{_MEMBER_ID}:{selected_surface.value}",
            trim,
            request.global_force,
            request.global_moment,
            request.global_reference_point,
            branches,
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
            support_regions if is_c3 else (),
            rectangular_paths,
        )
    return PairedClipAnglePreviewResult(
        request.request_id,
        request.orchestration_contract_version,
        PAIRED_CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
        "SYMMETRIC_PAIRED_CLIP_ANGLES",
        PairedClipAngleAssemblyIdentity.SYMMETRIC_PAIRED_CLIP_ANGLES,
        PairedClipAngleFrame(),
        request.support_role,
        request.selected_support_flange,
        proof,
        proof_fingerprint,
        branches,
        common_group,
        positive_group,
        negative_group,
        materials,
        trim,
        PAIRED_CLIP_ANGLE_REQUIRED_CHECKS,
        "NOT_EVALUATED",
        ClipAngleGeometryStatus.VALID
        if geometry_valid
        else ClipAngleGeometryStatus.INVALID_GEOMETRY,
        tuple(geometry_reasons),
        status,
        False,
        resistance and design_ready,
        design_ready,
        tuple(dict.fromkeys(warnings)),
        canonical_input,
        connector_geometry,
        engineering,
        visualization,
        rectangular_paths,
        limitations,
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
    )


def preview_paired_clip_angle(
    request: PairedClipAngleOrchestrationRequest,
) -> PairedClipAnglePreviewResult:
    """Resolve pair geometry, symmetry, and Stage 2.5A demands with zero resistance."""

    return _preview(request, resistance=False)


def design_check_paired_clip_angle(
    request: PairedClipAngleOrchestrationRequest,
) -> PairedClipAngleDesignResult:
    """Run only supported branch checks while retaining all required limitations."""

    preview = _preview(request, resistance=True)
    supported_failure = preview.assembly_status is PairedClipAngleDesignStatus.FAIL
    return PairedClipAngleDesignResult(
        preview,
        preview.assembly_status,
        "NOT_EVALUATED",
        False,
        supported_failure,
        _fingerprint(
            (
                preview.engineering_fingerprint,
                preview.common_member_group.resistance,
                preview.positive_support_group.resistance,
                preview.negative_support_group.resistance,
                PAIRED_CLIP_ANGLE_REQUIRED_CHECKS,
                preview.assembly_status,
            )
        ),
    )


__all__ = (
    "PAIRED_CLIP_ANGLE_EQUAL_SHARING_REASON",
    "PAIRED_CLIP_ANGLE_ORCHESTRATION_CONTRACT_VERSION",
    "PAIRED_CLIP_ANGLE_PREVIEW_SCHEMA_VERSION",
    "PAIRED_CLIP_ANGLE_REQUIRED_CHECKS",
    "PAIRED_CLIP_ANGLE_TRIM_PLANE_ID",
    "PAIRED_CLIP_ANGLE_VISUALIZATION_SCHEMA_VERSION",
    "PairedBoltGroupResult",
    "PairedBranchActionTrace",
    "PairedClipAngleDesignResult",
    "PairedClipAngleDesignStatus",
    "PairedClipAngleOrchestrationRequest",
    "PairedClipAnglePreviewResult",
    "PairedClipAngleVisualizationSnapshot",
    "PairedLayerDemandTrace",
    "design_check_paired_clip_angle",
    "preview_paired_clip_angle",
)
