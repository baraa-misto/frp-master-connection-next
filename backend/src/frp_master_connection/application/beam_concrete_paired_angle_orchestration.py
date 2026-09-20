"""Stage 3.5A beam-to-concrete-wall paired clip-angle orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum, StrEnum
from typing import cast

from frp_master_connection.application.clip_angle_orchestration import (
    ClipAngleBoltTrace,
    ClipAngleBoxTrace,
    ClipAngleClearanceTrace,
    ClipAngleGeometryStatus,
    ClipAngleInterfacePlacementTrace,
    ClipAngleMaterialRegionTrace,
    ClipAngleProfileMaterialRegionTrace,
    ClipAngleTriangleMeshTrace,
    ClipAngleVectorInput,
    _fingerprint,
    _layout_coordinates,
    _quantity,
    _resolve_interface,
)
from frp_master_connection.application.paired_clip_angle_orchestration import (
    PAIRED_CLIP_ANGLE_REQUIRED_CHECKS,
    PairedBoltGroupResult,
    PairedClipAngleOrchestrationRequest,
    _common_supported_failure,
    _layer_demands,
    _paired_placements,
    _single_request,
    _with_common_resistance,
    preview_paired_clip_angle,
)
from frp_master_connection.calculation import (
    Dimension,
    EccentricDemandResult,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    canonical_decimal_string,
)
from frp_master_connection.domain import (
    EXTERNAL_DESIGN_LIMITATIONS,
    ClipAngleBoltLayout,
    ClipAngleDimensions,
    ClipAngleHand,
    ClipAngleInterfaceIdentity,
    ClipAngleLengthAnchor,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    ComponentMaterialKind,
    ConcreteWallFrame,
    ConcreteWallGeometry,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ExternalAnchorGeometry,
    ExternalAnchorTrace,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PairedClipAngleSymmetryProof,
    PrincipalAxisFamily,
    SelectedSupportFlange,
    SharedSupportTargetId,
    WallAnchorGroupIdentity,
    WallAnchorPattern,
    WallEdgeDistances,
    WallQuantityVector,
    WallWrench,
    WideFlangeIProfileDimensions,
)

BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION = "3.5A-RC1"
BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION = "3.5A-R1-RC1"
BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION = "3.5A-R2-RC1"
BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
BEAM_CONCRETE_PAIRED_ANGLE_VISUALIZATION_SCHEMA_VERSION = "0.1.0-draft"
EXTERNAL_ANCHOR_HANDOFF_SCHEMA_VERSION = "3.5A-RC1"
WALL_GROUP_DEMAND_LABEL = "COORDINATION / FRP-SIDE DEMAND — EXTERNAL ANCHOR SOFTWARE GOVERNS"
EXTERNAL_ANCHOR_PRESENTATION_LABEL = "External anchor — capacity designed elsewhere"
_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)
_HALF = Decimal("0.5")
_R1_PROFILE_FAMILIES = frozenset(
    {
        MemberProfileFamily.FLAT_PLATE,
        MemberProfileFamily.ANGLE,
        MemberProfileFamily.CHANNEL,
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    }
)


class BeamConcretePairedAngleStatus(StrEnum):
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class ExternalAnchorHandoffMode(StrEnum):
    BRANCH_RESOLVED = "BRANCH_RESOLVED"
    COMBINED_LAYOUT = "COMBINED_LAYOUT"


@dataclass(frozen=True, slots=True)
class BeamConcretePairedAngleRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    wall: ConcreteWallGeometry
    beam_profile: MemberProfile
    beam_end_gap: PhysicalQuantity
    connector_dimensions: ClipAngleDimensions
    connector_length_anchor_position: PhysicalQuantity
    common_beam_layout: ClipAngleBoltLayout
    wall_anchor_pattern: WallAnchorPattern
    common_bolt_diameter: PhysicalQuantity
    common_hole_diameter: PhysicalQuantity
    external_anchor: ExternalAnchorGeometry
    reaction_shear: PhysicalQuantity
    user_force_hvn: WallQuantityVector
    user_moment_hvn: WallQuantityVector
    contract_version: str = BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION
    connector_material_source: str = "ICE_LOCKED_PULTRUDED_FRP:RC2"
    common_fastener_source: str = "ASTM_F593_17_GROUP_2_316_316L"
    anchor_design_authority: str = "EXTERNAL_SPECIALTY_ANCHOR_SOFTWARE"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.contract_version not in {
            BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION,
            BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION,
            BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
        }:
            raise ValueError("Unsupported beam-to-concrete paired-angle contract version.")
        expected_unit = (
            Unit.IN if self.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.MM
        )
        if self.source_length_unit is not expected_unit:
            raise ValueError("Source length unit must match the engineering unit system.")
        if self.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION and (
            self.beam_profile.family is not MemberProfileFamily.WIDE_FLANGE_I
            or self.beam_profile.role is not MemberRole.BEAM
            or self.beam_profile.member_id != "clip-angle-connected-member"
        ):
            raise ValueError("Historical Stage 3.5A requires the controlled FRP W/I beam profile.")
        if (
            self.beam_profile.role is not MemberRole.BEAM
            or self.beam_profile.member_id != "clip-angle-connected-member"
        ):
            raise ValueError(
                "Stage 3.5A-R1 requires the controlled connected-member identity and beam role."
            )
        if (
            self.contract_version
            in {
                BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION,
                BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
            }
            and self.beam_profile.family not in _R1_PROFILE_FAMILIES
        ):
            raise ValueError(
                "Stage 3.5A-R1/R2 requires one of the six authorized connected profiles."
            )
        if self.beam_end_gap.dimension is not Dimension.LENGTH or self.beam_end_gap.magnitude < 0:
            raise ValueError("beam_end_gap must be a nonnegative length.")
        if self.connector_length_anchor_position.dimension is not Dimension.LENGTH:
            raise ValueError("Connector position must be a length.")
        if self.reaction_shear.dimension is not Dimension.FORCE:
            raise ValueError("Reaction shear must be a force quantity.")
        if self.user_force_hvn.h.dimension is not Dimension.FORCE:
            raise ValueError("User force must contain force quantities.")
        if self.user_moment_hvn.h.dimension is not Dimension.MOMENT:
            raise ValueError("User moment must contain moment quantities.")
        force_unit = self.reaction_shear.unit
        expected_force = (
            self.user_force_hvn.h.to(force_unit).magnitude,
            self.user_force_hvn.v.to(force_unit).magnitude,
            self.user_force_hvn.n.to(force_unit).magnitude,
        )
        allowed_force = (
            expected_force
            if self.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
            else (_ZERO, self.reaction_shear.magnitude, _ZERO)
        )
        if self.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION:
            if expected_force[1] != self.reaction_shear.magnitude:
                raise ValueError("R2 Major shear must equal the wall-frame V force component.")
        elif expected_force != allowed_force:
            raise ValueError("STAGE_3_5A_ONLY_VERTICAL_REACTION_SHEAR_ALLOWED")
        if any(
            item.canonical_magnitude != 0
            for item in (
                self.user_moment_hvn.h,
                self.user_moment_hvn.v,
                self.user_moment_hvn.n,
            )
        ):
            raise ValueError("STAGE_3_5A_USER_APPLIED_MOMENT_NOT_ALLOWED")
        if self.common_bolt_diameter.dimension is not Dimension.LENGTH:
            raise ValueError("Common bolt diameter must be a length.")
        if (
            self.common_hole_diameter.canonical_magnitude
            < self.common_bolt_diameter.canonical_magnitude
        ):
            raise ValueError("Common beam hole cannot be smaller than the bolt.")
        if self.connector_material_source != "ICE_LOCKED_PULTRUDED_FRP:RC2":
            raise ValueError("Stage 3.5A requires the accepted FRP material source.")
        if self.common_fastener_source != "ASTM_F593_17_GROUP_2_316_316L":
            raise ValueError("Stage 3.5A requires the accepted ASTM F593 fastener source.")
        if self.anchor_design_authority != "EXTERNAL_SPECIALTY_ANCHOR_SOFTWARE":
            raise ValueError("Anchor design authority must remain external.")


@dataclass(frozen=True, slots=True)
class WallAnchorGroupResult:
    group_id: WallAnchorGroupIdentity
    centroid_hvn: WallQuantityVector
    anchors: tuple[ExternalAnchorTrace, ...]
    wrench: WallWrench | None = field(metadata={"omit_none": True})
    nominal_demand: EccentricDemandResult | None
    demand_label: str
    force_equilibrium: bool
    moment_equilibrium: bool
    geometry_fingerprint: str
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class ExternalAnchorDesignHandoff:
    schema_version: str
    load_case_id: str
    load_status: str
    unit_system: str
    connection_application_fingerprint: str
    wall_frame: ConcreteWallFrame
    wall_dimensions: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    connection_origin_hvn: WallQuantityVector
    wall_reference_hvn: WallQuantityVector
    combined_wall_wrench: WallWrench
    positive_group: WallAnchorGroupResult
    negative_group: WallAnchorGroupResult
    external_anchor_geometry: ExternalAnchorGeometry
    clip_angle_wall_leg_thickness: PhysicalQuantity
    sign_convention: str
    demand_method_versions: tuple[str, ...]
    input_fingerprint: str
    wall_geometry_fingerprint: str
    anchor_geometry_fingerprint: str
    limitations: tuple[tuple[str, str], ...]
    handoff_fingerprint: str
    handoff_mode: ExternalAnchorHandoffMode | None = field(
        default=None, metadata={"omit_none": True}
    )
    branch_allocation_status: str | None = field(default=None, metadata={"omit_none": True})
    all_anchors: tuple[ExternalAnchorTrace, ...] | None = field(
        default=None, metadata={"omit_none": True}
    )


@dataclass(frozen=True, slots=True)
class BeamConcretePairedAngleVisualizationSnapshot:
    schema_version: str
    wall_frame: ConcreteWallFrame
    boxes: tuple[ClipAngleBoxTrace, ...]
    meshes: tuple[ClipAngleTriangleMeshTrace, ...]
    common_beam_bolts: tuple[ClipAngleBoltTrace, ...]
    external_anchors: tuple[ExternalAnchorTrace, ...]
    common_bolt_diameter: PhysicalQuantity
    common_hole_diameter: PhysicalQuantity
    external_anchor_geometry: ExternalAnchorGeometry
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    beam_material_regions: tuple[ClipAngleProfileMaterialRegionTrace, ...]
    reaction_shear: PhysicalQuantity
    beam_reference_hvn: WallQuantityVector
    wall_reference_hvn: WallQuantityVector
    positive_branch_wrench: WallWrench | None = field(metadata={"omit_none": True})
    negative_branch_wrench: WallWrench | None = field(metadata={"omit_none": True})
    combined_wall_wrench: WallWrench
    selected_wall_surface_id: str = "CONCRETE_WALL:EXTERIOR_FACE"
    user_force_hvn: WallQuantityVector | None = field(default=None, metadata={"omit_none": True})
    user_moment_hvn: WallQuantityVector | None = field(default=None, metadata={"omit_none": True})


@dataclass(frozen=True, slots=True)
class BeamConcretePairedAnglePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    wall_frame: ConcreteWallFrame
    symmetry_proof: PairedClipAngleSymmetryProof
    common_beam_group: PairedBoltGroupResult
    positive_wall_group: WallAnchorGroupResult
    negative_wall_group: WallAnchorGroupResult
    combined_wall_wrench: WallWrench
    external_anchor_handoff: ExternalAnchorDesignHandoff
    external_anchor_handoff_json: str
    geometry_status: ClipAngleGeometryStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: BeamConcretePairedAngleStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    external_design_required: bool
    limitations: tuple[tuple[str, str], ...]
    paired_limitations: tuple[str, ...]
    warnings: tuple[str, ...]
    canonical_input_fingerprint: str
    wall_geometry_fingerprint: str
    beam_geometry_fingerprint: str
    paired_connector_geometry_fingerprint: str
    combined_wall_handoff_fingerprint: str
    engineering_fingerprint: str
    application_fingerprint: str
    visualization: BeamConcretePairedAngleVisualizationSnapshot | None
    handoff_mode: ExternalAnchorHandoffMode | None = field(
        default=None, metadata={"omit_none": True}
    )
    branch_allocation_status: str | None = field(default=None, metadata={"omit_none": True})
    common_group_normal_action: PhysicalQuantity | None = field(
        default=None, metadata={"omit_none": True}
    )
    action_reference_hvn: WallQuantityVector | None = field(
        default=None, metadata={"omit_none": True}
    )


@dataclass(frozen=True, slots=True)
class BeamConcretePairedAngleDesignResult:
    preview: BeamConcretePairedAnglePreviewResult
    assembly_status: BeamConcretePairedAngleStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_beam_side_failure_present: bool
    result_fingerprint: str


def _wall_vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> WallQuantityVector:
    return WallQuantityVector(*(_quantity(value, unit) for value in values))


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
    reference: tuple[Decimal, Decimal, Decimal],
    force: tuple[Decimal, Decimal, Decimal],
    source_reference: tuple[Decimal, Decimal, Decimal],
    length_unit: Unit,
    force_unit: Unit,
    moment_unit: Unit,
    provenance: str,
) -> WallWrench:
    arm = tuple(a - b for a, b in zip(source_reference, reference, strict=True))
    generated = _cross(cast(tuple[Decimal, Decimal, Decimal], arm), force)
    return WallWrench(
        _wall_vector(reference, length_unit),
        _wall_vector(force, force_unit),
        _wall_vector(generated, moment_unit),
        provenance,
    )


def _base_paired_request(
    request: BeamConcretePairedAngleRequest,
) -> PairedClipAngleOrchestrationRequest:
    unit = request.source_length_unit
    dims = request.connector_dimensions
    dummy_gauge = dims.support_leg_width / _TWO
    dummy_heel = (dims.support_leg_width - dims.thickness - dummy_gauge) / _TWO
    dummy_pitch = dims.connector_length / Decimal(4)
    dummy_end = (dims.connector_length - dummy_pitch) / _TWO
    support_layout = ClipAngleBoltLayout(
        2,
        2,
        dummy_pitch,
        dummy_gauge,
        dummy_heel,
        dummy_heel,
        dummy_end,
        dummy_end,
    )
    support = ClipAngleSupportDimensions(
        dims.connector_length * Decimal(4),
        dims.support_leg_width * Decimal(4),
        dims.connector_length * _TWO,
        dims.thickness,
        dims.thickness,
    )
    common_widths, _lengths = _layout_coordinates(
        request.common_beam_layout,
        dims,
        dims.connected_leg_width,
    )
    common_center = sum(common_widths, _ZERO) / Decimal(len(common_widths))
    axial_force = (
        request.user_force_hvn.n.to(request.reaction_shear.unit)
        if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
        else _quantity(_ZERO, request.reaction_shear.unit)
    )
    force = ClipAngleVectorInput(
        _quantity(_ZERO, request.reaction_shear.unit),
        axial_force,
        request.reaction_shear,
    )
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    moment = ClipAngleVectorInput(*(_quantity(_ZERO, moment_unit) for _ in range(3)))
    reference = ClipAngleVectorInput(
        _quantity(_ZERO, unit),
        _quantity(common_center, unit),
        _quantity(_ZERO, unit),
    )
    successor = request.contract_version in {
        BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION,
        BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
    }
    support_profile = (
        MemberProfile(
            "beam-concrete-dummy-wall-support-profile",
            "clip-angle-support",
            MemberRole.COLUMN,
            MemberProfileFamily.WIDE_FLANGE_I,
            WideFlangeIProfileDimensions(
                support.member_length,
                support.overall_depth,
                support.flange_width,
                support.web_thickness,
                support.flange_thickness,
            ),
            ComponentMaterialKind.PULTRUDED_FRP,
            FRPComponentOrientation(
                CoordinateFrameReference(
                    CoordinateFrameKind.MEMBER_LOCAL,
                    "clip-angle-support",
                ),
                PrincipalAxisFamily.X,
            ),
            MemberProfileOrientation.ROTATION_0,
            MemberProfileSurfaceId.FLANGE_POS_OUTER,
        )
        if successor
        else None
    )
    return PairedClipAngleOrchestrationRequest(
        request.request_id,
        request.unit_system,
        unit,
        ClipAngleSupportRole.W_COLUMN_FLANGE,
        SelectedSupportFlange.POSITIVE_LOCAL_Z,
        request.connector_dimensions,
        support,
        request.beam_profile,
        request.common_beam_layout,
        support_layout,
        request.common_bolt_diameter,
        request.common_hole_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        force,
        moment,
        reference,
        _ZERO,
        False,
        None,
        ClipAngleLengthAnchor.CENTER,
        request.connector_length_anchor_position,
        "3.3C3-RC1" if successor else "3.3B-RC1",
        SharedSupportTargetId.W_COLUMN_FLANGE if successor else None,
        support_profile,
    )


def _anchor_coordinates(
    request: BeamConcretePairedAngleRequest,
    group_id: WallAnchorGroupIdentity,
) -> tuple[tuple[Decimal, Decimal], ...]:
    pattern = request.wall_anchor_pattern
    sign = _ONE if group_id is WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP else -_ONE
    center_h = sign * pattern.centroid_offset_h
    first_h = center_h - pattern.gauge * Decimal(pattern.anchors_per_row - 1) / _TWO
    first_v = pattern.centroid_v - pattern.pitch * Decimal(pattern.row_count - 1) / _TWO
    return tuple(
        (
            first_h + Decimal(line) * pattern.gauge,
            first_v + Decimal(row) * pattern.pitch,
        )
        for row in range(pattern.row_count)
        for line in range(pattern.anchors_per_row)
    )


def _edge_distances(
    request: BeamConcretePairedAngleRequest,
    h: Decimal,
    v: Decimal,
) -> WallEdgeDistances:
    unit = request.source_length_unit
    wall = request.wall
    h_min = wall.connection_origin_h - wall.width / _TWO
    h_max = wall.connection_origin_h + wall.width / _TWO
    v_min = wall.connection_origin_v - wall.height / _TWO
    v_max = wall.connection_origin_v + wall.height / _TWO
    return WallEdgeDistances(
        _quantity(h - h_min, unit),
        _quantity(h_max - h, unit),
        _quantity(v - v_min, unit),
        _quantity(v_max - v, unit),
    )


def _anchor_traces(
    request: BeamConcretePairedAngleRequest,
    group_id: WallAnchorGroupIdentity,
) -> tuple[ExternalAnchorTrace, ...]:
    unit = request.source_length_unit
    embedment = request.external_anchor.specified_embedment.to(unit).magnitude
    outside = request.connector_dimensions.thickness
    prefix = (
        "POS-ANCHOR"
        if group_id is WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP
        else "NEG-ANCHOR"
    )
    return tuple(
        ExternalAnchorTrace(
            f"{prefix}-R{row}-A{line}",
            group_id,
            _wall_vector((h, v, _ZERO), unit),
            _edge_distances(request, h, v),
            _wall_vector((h, v, outside), unit),
            _wall_vector((h, v, -embedment), unit),
        )
        for index, (h, v) in enumerate(_anchor_coordinates(request, group_id))
        for row, line in (
            (
                index // request.wall_anchor_pattern.anchors_per_row + 1,
                index % request.wall_anchor_pattern.anchors_per_row + 1,
            ),
        )
    )


def _group_placement(
    request: BeamConcretePairedAngleRequest,
    group_id: WallAnchorGroupIdentity,
    anchors: tuple[ExternalAnchorTrace, ...],
) -> ClipAngleInterfacePlacementTrace:
    unit = request.source_length_unit
    coordinates = _anchor_coordinates(request, group_id)
    widths = tuple(dict.fromkeys(item[0] for item in coordinates))
    lengths = tuple(dict.fromkeys(item[1] for item in coordinates))
    hole_radius = request.external_anchor.hole_diameter.to(unit).magnitude / _TWO
    center_h = (
        request.wall_anchor_pattern.centroid_offset_h
        if group_id is WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP
        else -request.wall_anchor_pattern.centroid_offset_h
    )
    half_leg = request.connector_dimensions.support_leg_width / _TWO
    half_length = request.connector_dimensions.connector_length / _TWO
    leg_candidates = tuple(
        min(
            h - (center_h - half_leg),
            center_h + half_leg - h,
            v - (request.wall_anchor_pattern.centroid_v - half_length),
            request.wall_anchor_pattern.centroid_v + half_length - v,
        )
        - hole_radius
        for h, v in coordinates
    )
    minimum = min(leg_candidates)
    clearance = ClipAngleClearanceTrace(
        _quantity(minimum, unit),
        _quantity(minimum, unit),
        _quantity(minimum, unit),
        _quantity(minimum, unit),
        _quantity(minimum, unit),
        anchors[leg_candidates.index(minimum)].anchor_id,
        "FINITE_FRP_WALL_LEG",
        None if minimum >= 0 else _quantity(-minimum, unit),
        minimum >= 0,
    )
    bolts = tuple(
        ClipAngleBoltTrace(
            anchor.anchor_id,
            f"ROW_{index // request.wall_anchor_pattern.anchors_per_row + 1}",
            f"BOLT_LINE_{index % request.wall_anchor_pattern.anchors_per_row + 1}",
            anchor.coordinate_hvn.h,
            anchor.coordinate_hvn.v,
            (
                anchor.coordinate_hvn.h,
                _quantity(_ZERO, unit),
                anchor.coordinate_hvn.v,
            ),
            (_ZERO, Decimal(-1), _ZERO),
            ("FRP_CLIP_ANGLE_WALL_LEG", "EXTERNAL_CONCRETE_ANCHOR_COORDINATION"),
            (
                anchor.shank_start_hvn.h,
                _quantity(-anchor.shank_start_hvn.n.magnitude, unit),
                anchor.shank_start_hvn.v,
            ),
            (
                anchor.shank_end_hvn.h,
                _quantity(-anchor.shank_end_hvn.n.magnitude, unit),
                anchor.shank_end_hvn.v,
            ),
        )
        for index, anchor in enumerate(anchors)
    )
    return ClipAngleInterfacePlacementTrace(
        ClipAngleInterfaceIdentity.SUPPORT_LEG_TO_SUPPORT,
        group_id.value,
        (_ONE, _ZERO, _ZERO),
        (_ZERO, _ZERO, _ONE),
        (_ZERO, Decimal(-1), _ZERO),
        tuple(_quantity(item, unit) for item in widths),
        tuple(_quantity(item, unit) for item in lengths),
        bolts,
        clearance,
        _fingerprint(
            (group_id, tuple((item[0], item[1]) for item in coordinates), request.external_anchor)
        ),
    )


def _wall_group(
    request: BeamConcretePairedAngleRequest,
    base: PairedClipAngleOrchestrationRequest,
    group_id: WallAnchorGroupIdentity,
    wrench: WallWrench | None,
) -> WallAnchorGroupResult:
    anchors = _anchor_traces(request, group_id)
    placement = _group_placement(request, group_id, anchors)
    if wrench is None:
        centroid_h = (
            request.wall_anchor_pattern.centroid_offset_h
            if group_id is WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP
            else -request.wall_anchor_pattern.centroid_offset_h
        )
        centroid = _wall_vector(
            (centroid_h, request.wall_anchor_pattern.centroid_v, _ZERO),
            request.source_length_unit,
        )
        geometry_fingerprint = _fingerprint((group_id, anchors, request.external_anchor))
        return WallAnchorGroupResult(
            group_id,
            centroid,
            anchors,
            None,
            None,
            WALL_GROUP_DEMAND_LABEL,
            False,
            False,
            geometry_fingerprint,
            _fingerprint(
                (
                    group_id,
                    geometry_fingerprint,
                    "MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION:NOT_EVALUATED",
                )
            ),
        )
    force = ClipAngleVectorInput(
        wrench.force_hvn.h,
        _quantity(_ZERO, wrench.force_hvn.h.unit),
        wrench.force_hvn.v,
    )
    moment = ClipAngleVectorInput(
        wrench.moment_hvn.h,
        PhysicalQuantity.of(-wrench.moment_hvn.n.magnitude, wrench.moment_hvn.n.unit),
        wrench.moment_hvn.v,
    )
    reference = ClipAngleVectorInput(
        _quantity(_ZERO, request.source_length_unit),
        _quantity(-wrench.reference_hvn.n.magnitude, request.source_length_unit),
        _quantity(_ZERO, request.source_length_unit),
    )
    single = replace(
        _single_request(base, ClipAngleHand.POSITIVE_S_SIDE, force=force, reference=reference),
        global_moment=moment,
    )
    pattern = request.wall_anchor_pattern
    heel = (
        request.connector_dimensions.support_leg_width
        - Decimal(pattern.anchors_per_row - 1) * pattern.gauge
    ) / _TWO
    end = (
        request.connector_dimensions.connector_length
        - Decimal(pattern.row_count - 1) * pattern.pitch
    ) / _TWO
    wall_layout = ClipAngleBoltLayout(
        pattern.row_count,
        pattern.anchors_per_row,
        pattern.pitch,
        pattern.gauge,
        max(Decimal("1e-18"), heel),
        max(Decimal("1e-18"), heel),
        max(Decimal("1e-18"), end),
        max(Decimal("1e-18"), end),
    )
    interface = _resolve_interface(single, placement, wall_layout)
    force_equilibrium = all(
        scenario.equilibrium is not None and scenario.equilibrium.satisfied
        for scenario in interface.demand.scenarios
    )
    moment_equilibrium = force_equilibrium
    axial_force = request.user_force_hvn.n.to(wrench.force_hvn.n.unit).magnitude
    nominal_demand = (
        None
        if (
            request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION
            and not (force_equilibrium and moment_equilibrium)
        )
        or (
            request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
            and (axial_force != 0 or not (force_equilibrium and moment_equilibrium))
        )
        else interface.demand
    )
    centroid = wrench.reference_hvn
    geometry_fingerprint = _fingerprint((group_id, anchors, request.external_anchor))
    result_fingerprint = _fingerprint(
        (
            group_id,
            geometry_fingerprint,
            wrench,
            (
                nominal_demand.result_fingerprint
                if nominal_demand is not None
                else "WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION:EXTERNAL_DESIGN_REQUIRED"
            ),
        )
    )
    return WallAnchorGroupResult(
        group_id,
        centroid,
        anchors,
        wrench,
        nominal_demand,
        WALL_GROUP_DEMAND_LABEL,
        force_equilibrium,
        moment_equilibrium,
        geometry_fingerprint,
        result_fingerprint,
    )


def _geometry_reasons(
    request: BeamConcretePairedAngleRequest,
    base_geometry_valid: bool,
    positive: WallAnchorGroupResult,
    negative: WallAnchorGroupResult,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not base_geometry_valid:
        reasons.append("PAIRED_BEAM_CONNECTOR_GEOMETRY_INVALID")
    unit = request.source_length_unit
    if request.external_anchor.specified_embedment.to(unit).magnitude > request.wall.thickness:
        reasons.append("ANCHOR_EMBEDMENT_EXCEEDS_WALL_THICKNESS")
    all_anchors = positive.anchors + negative.anchors
    outside = tuple(
        item.anchor_id
        for item in all_anchors
        if min(
            item.wall_edge_distances.negative_h.magnitude,
            item.wall_edge_distances.positive_h.magnitude,
            item.wall_edge_distances.negative_v.magnitude,
            item.wall_edge_distances.positive_v.magnitude,
        )
        < 0
    )
    if outside:
        reasons.append(f"ANCHOR_CENTER_OUTSIDE_FINITE_WALL:{','.join(outside)}")
    positive_coords = {
        (item.coordinate_hvn.h.magnitude, item.coordinate_hvn.v.magnitude)
        for item in positive.anchors
    }
    negative_coords = {
        (item.coordinate_hvn.h.magnitude, item.coordinate_hvn.v.magnitude)
        for item in negative.anchors
    }
    if positive_coords & negative_coords:
        reasons.append("DUPLICATE_OR_OVERLAPPING_WALL_ANCHOR_AXES")
    for group in (positive, negative):
        placement = _group_placement(request, group.group_id, group.anchors)
        if not placement.clearances.geometry_valid:
            reasons.append(f"{group.group_id.value}:FRP_WALL_LEG_COMPLETE_HOLE_CONTAINMENT_INVALID")
    return tuple(reasons)


def _reflect_point(
    point: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
) -> tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]:
    return (point[0], PhysicalQuantity.of(-point[1].magnitude, point[1].unit), point[2])


def _reflect_direction(
    value: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (value[0], -value[1], value[2])


def _visualization(
    request: BeamConcretePairedAngleRequest,
    base_visualization: object,
    positive: WallAnchorGroupResult,
    negative: WallAnchorGroupResult,
    combined: WallWrench,
    beam_reference: WallQuantityVector,
) -> BeamConcretePairedAngleVisualizationSnapshot:
    from frp_master_connection.application.paired_clip_angle_orchestration import (
        PairedClipAngleVisualizationSnapshot,
    )

    source = cast(PairedClipAngleVisualizationSnapshot, base_visualization)
    unit = request.source_length_unit
    wall = request.wall
    wall_box = ClipAngleBoxTrace(
        "concrete-wall-solid",
        "concrete-wall",
        "CONCRETE_WALL",
        (
            _quantity(wall.connection_origin_h, unit),
            _quantity(wall.thickness / _TWO, unit),
            _quantity(wall.connection_origin_v, unit),
        ),
        _quantity(wall.width, unit),
        _quantity(wall.thickness, unit),
        _quantity(wall.height, unit),
    )
    default_gap = request.connector_dimensions.thickness
    gap_shift = request.beam_end_gap.to(unit).magnitude - default_gap
    boxes = (
        *(
            replace(
                item,
                center=(
                    _reflect_point(item.center)[0],
                    _quantity(
                        _reflect_point(item.center)[1].magnitude
                        - (gap_shift if item.owner_id == "clip-angle-connected-member" else _ZERO),
                        unit,
                    ),
                    _reflect_point(item.center)[2],
                ),
                basis=cast(
                    tuple[
                        tuple[Decimal, Decimal, Decimal],
                        tuple[Decimal, Decimal, Decimal],
                        tuple[Decimal, Decimal, Decimal],
                    ],
                    tuple(_reflect_direction(axis) for axis in item.basis),
                ),
            )
            for item in source.boxes
            if item.owner_id != "clip-angle-support"
        ),
        wall_box,
    )
    meshes = tuple(
        replace(
            item,
            points=tuple(
                (
                    _reflect_point(point)[0],
                    _quantity(
                        _reflect_point(point)[1].magnitude
                        - (gap_shift if item.owner_id == "clip-angle-connected-member" else _ZERO),
                        unit,
                    ),
                    _reflect_point(point)[2],
                )
                for point in item.points
            ),
        )
        for item in source.meshes
        if item.owner_id != "clip-angle-support"
    )
    bolts = tuple(
        replace(
            item,
            global_center=_reflect_point(item.global_center),
            axis=_reflect_direction(item.axis),
            stack_start=_reflect_point(item.stack_start),
            stack_end=_reflect_point(item.stack_end),
        )
        for item in source.common_member_bolts
    )
    material_regions = tuple(
        replace(
            item,
            lw=_reflect_direction(item.lw),
            cw=_reflect_direction(item.cw),
            tt=_reflect_direction(item.tt),
        )
        for item in source.material_regions
    )
    beam_regions = tuple(
        replace(
            item,
            origin=(
                _reflect_point(item.origin)[0],
                _quantity(_reflect_point(item.origin)[1].magnitude - gap_shift, unit),
                _reflect_point(item.origin)[2],
            ),
            lw=_reflect_direction(item.lw),
            cw=_reflect_direction(item.cw),
            tt=_reflect_direction(item.tt),
        )
        for item in source.connected_member_material_regions
    )
    return BeamConcretePairedAngleVisualizationSnapshot(
        BEAM_CONCRETE_PAIRED_ANGLE_VISUALIZATION_SCHEMA_VERSION,
        ConcreteWallFrame(),
        boxes,
        meshes,
        bolts,
        positive.anchors + negative.anchors,
        request.common_bolt_diameter,
        request.common_hole_diameter,
        request.external_anchor,
        material_regions,
        beam_regions,
        request.reaction_shear,
        beam_reference,
        _wall_vector((_ZERO, _ZERO, _ZERO), unit),
        positive.wrench,
        negative.wrench,
        combined,
        "CONCRETE_WALL:EXTERIOR_FACE",
        request.user_force_hvn
        if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
        else None,
        request.user_moment_hvn
        if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
        else None,
    )


def _export_value(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"value": canonical_decimal_string(value.magnitude), "unit": value.unit.value}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            item.name: _export_value(getattr(value, item.name))
            for item in fields(value)
            if not (item.metadata.get("omit_none", False) and getattr(value, item.name) is None)
        }
    if isinstance(value, tuple):
        return [_export_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _export_value(item) for key, item in sorted(value.items())}
    return value


def _input_fingerprint(request: BeamConcretePairedAngleRequest) -> str:
    unit = request.source_length_unit
    beam = request.beam_profile.dimensions
    if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION:
        profile_dimensions = tuple(
            (item.name, _quantity(getattr(beam, item.name), unit)) for item in fields(beam)
        )
        beam_reference_n = (
            request.beam_end_gap.to(unit).magnitude
            + request.connector_dimensions.connected_leg_width
            - request.connector_dimensions.thickness
        )
        handoff_mode = (
            ExternalAnchorHandoffMode.BRANCH_RESOLVED
            if request.user_force_hvn.h.canonical_magnitude == 0
            else ExternalAnchorHandoffMode.COMBINED_LAYOUT
        )
        return _fingerprint(
            (
                request.contract_version,
                tuple(
                    _quantity(getattr(request.wall, name), unit)
                    for name in ("width", "height", "thickness")
                ),
                _quantity(request.wall.connection_origin_h, unit),
                _quantity(request.wall.connection_origin_v, unit),
                request.beam_profile.family,
                request.beam_profile.orientation,
                request.beam_profile.selected_surface,
                profile_dimensions,
                request.beam_end_gap,
                tuple(
                    _quantity(getattr(request.connector_dimensions, item.name), unit)
                    for item in fields(request.connector_dimensions)
                ),
                request.connector_length_anchor_position,
                request.common_beam_layout.row_count,
                request.common_beam_layout.bolts_per_row,
                tuple(
                    _quantity(getattr(request.common_beam_layout, name), unit)
                    for name in (
                        "pitch",
                        "gauge",
                        "heel_edge_distance",
                        "free_edge_distance",
                        "negative_end_distance",
                        "positive_end_distance",
                    )
                ),
                request.wall_anchor_pattern.row_count,
                request.wall_anchor_pattern.anchors_per_row,
                tuple(
                    _quantity(getattr(request.wall_anchor_pattern, name), unit)
                    for name in ("pitch", "gauge", "centroid_offset_h", "centroid_v")
                ),
                request.common_bolt_diameter,
                request.common_hole_diameter,
                request.external_anchor,
                request.user_force_hvn,
                request.user_moment_hvn,
                _wall_vector((_ZERO, _ZERO, beam_reference_n), unit),
                handoff_mode,
                request.connector_material_source,
                request.common_fastener_source,
                request.anchor_design_authority,
                "2.5A-RC1",
                "2.5B-RC1",
                "2.6A-RC1",
                BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
            )
        )
    if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION:
        profile_dimensions = tuple(
            (field.name, _quantity(getattr(beam, field.name), unit)) for field in fields(beam)
        )
        return _fingerprint(
            (
                request.contract_version,
                tuple(
                    _quantity(getattr(request.wall, name), unit)
                    for name in ("width", "height", "thickness")
                ),
                _quantity(request.wall.connection_origin_h, unit),
                _quantity(request.wall.connection_origin_v, unit),
                request.beam_profile.family,
                request.beam_profile.orientation,
                request.beam_profile.selected_surface,
                profile_dimensions,
                request.beam_end_gap,
                tuple(
                    _quantity(getattr(request.connector_dimensions, field.name), unit)
                    for field in fields(request.connector_dimensions)
                ),
                request.connector_length_anchor_position,
                request.common_beam_layout.row_count,
                request.common_beam_layout.bolts_per_row,
                tuple(
                    _quantity(getattr(request.common_beam_layout, name), unit)
                    for name in (
                        "pitch",
                        "gauge",
                        "heel_edge_distance",
                        "free_edge_distance",
                        "negative_end_distance",
                        "positive_end_distance",
                    )
                ),
                request.wall_anchor_pattern.row_count,
                request.wall_anchor_pattern.anchors_per_row,
                tuple(
                    _quantity(getattr(request.wall_anchor_pattern, name), unit)
                    for name in ("pitch", "gauge", "centroid_offset_h", "centroid_v")
                ),
                request.common_bolt_diameter,
                request.common_hole_diameter,
                request.external_anchor,
                request.reaction_shear,
                request.connector_material_source,
                request.common_fastener_source,
                request.anchor_design_authority,
            )
        )
    return _fingerprint(
        (
            BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION,
            tuple(
                _quantity(getattr(request.wall, name), unit)
                for name in ("width", "height", "thickness")
            ),
            _quantity(request.wall.connection_origin_h, unit),
            _quantity(request.wall.connection_origin_v, unit),
            tuple(
                _quantity(getattr(beam, name), unit)
                for name in (
                    "member_length",
                    "depth",
                    "flange_width",
                    "web_thickness",
                    "flange_thickness",
                )
            ),
            request.beam_end_gap,
            tuple(
                _quantity(getattr(request.connector_dimensions, field.name), unit)
                for field in fields(request.connector_dimensions)
            ),
            request.connector_length_anchor_position,
            request.common_beam_layout.row_count,
            request.common_beam_layout.bolts_per_row,
            tuple(
                _quantity(getattr(request.common_beam_layout, name), unit)
                for name in (
                    "pitch",
                    "gauge",
                    "heel_edge_distance",
                    "free_edge_distance",
                    "negative_end_distance",
                    "positive_end_distance",
                )
            ),
            request.wall_anchor_pattern.row_count,
            request.wall_anchor_pattern.anchors_per_row,
            tuple(
                _quantity(getattr(request.wall_anchor_pattern, name), unit)
                for name in ("pitch", "gauge", "centroid_offset_h", "centroid_v")
            ),
            request.common_bolt_diameter,
            request.common_hole_diameter,
            request.external_anchor,
            request.reaction_shear,
            request.connector_material_source,
            request.common_fastener_source,
            request.anchor_design_authority,
        )
    )


def _preview(
    request: BeamConcretePairedAngleRequest,
    *,
    resistance: bool,
) -> BeamConcretePairedAnglePreviewResult:
    base_request = _base_paired_request(request)
    base_preview = preview_paired_clip_angle(base_request)
    unit = request.source_length_unit
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    reaction = request.reaction_shear.to(force_unit).magnitude
    is_r2 = request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
    minor = request.user_force_hvn.h.to(force_unit).magnitude if is_r2 else _ZERO
    major = reaction
    axial = request.user_force_hvn.n.to(force_unit).magnitude if is_r2 else _ZERO
    branch_resolved = not is_r2 or minor == 0
    half_force = (_ZERO, major / _TWO, axial / _TWO)
    beam_reference_n = (
        request.beam_end_gap.to(unit).magnitude
        + request.connector_dimensions.connected_leg_width
        - request.connector_dimensions.thickness
    )
    beam_reference_values = (_ZERO, _ZERO, beam_reference_n)
    positive_reference = (
        request.wall_anchor_pattern.centroid_offset_h,
        request.wall_anchor_pattern.centroid_v,
        _ZERO,
    )
    negative_reference = (
        -request.wall_anchor_pattern.centroid_offset_h,
        request.wall_anchor_pattern.centroid_v,
        _ZERO,
    )
    positive_wrench = (
        _wrench(
            positive_reference,
            half_force,
            beam_reference_values,
            unit,
            force_unit,
            moment_unit,
            "EXACT_REFERENCE_TRANSLATION_FROM_BEAM_GROUP_TO_POSITIVE_WALL_GROUP",
        )
        if branch_resolved
        else None
    )
    negative_wrench = (
        _wrench(
            negative_reference,
            half_force,
            beam_reference_values,
            unit,
            force_unit,
            moment_unit,
            "EXACT_REFERENCE_TRANSLATION_FROM_BEAM_GROUP_TO_NEGATIVE_WALL_GROUP",
        )
        if branch_resolved
        else None
    )
    wall_reference_values = (_ZERO, _ZERO, _ZERO)
    combined_force = (minor, major, axial)
    combined_wrench = _wrench(
        wall_reference_values,
        combined_force,
        beam_reference_values,
        unit,
        force_unit,
        moment_unit,
        "EXACT_WALL_FRAME_FORCE_TRANSLATION_TO_WALL_ORIGIN"
        if is_r2
        else "EXACT_SUM_OF_SHIFTED_MIRRORED_BRANCH_WRENCHES_AT_WALL_ORIGIN",
    )
    positive = _wall_group(
        request, base_request, WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP, positive_wrench
    )
    negative = _wall_group(
        request, base_request, WallAnchorGroupIdentity.NEGATIVE_WALL_ANCHOR_GROUP, negative_wrench
    )
    reasons = _geometry_reasons(
        request,
        base_preview.geometry_status is ClipAngleGeometryStatus.VALID,
        positive,
        negative,
    )
    geometry_valid = not reasons
    proof = PairedClipAngleSymmetryProof(
        geometry_valid,
        branch_resolved,
        geometry_valid and branch_resolved,
        ()
        if geometry_valid and branch_resolved
        else tuple(
            reason
            for condition, reason in (
                (not geometry_valid, "PAIR_GEOMETRY_SYMMETRY_NOT_PROVEN"),
                (not branch_resolved, "NONZERO_MINOR_SHEAR_BREAKS_ACTION_SYMMETRY"),
            )
            if condition
        ),
    )
    common_group = base_preview.common_member_group
    supported_failure = False
    in_plane_force_present = major != 0 or axial != 0
    in_plane_path_applicable = major == 0 or axial == 0
    resistance_evaluated = False
    if resistance and geometry_valid and in_plane_force_present and in_plane_path_applicable:
        single = _single_request(base_request, ClipAngleHand.POSITIVE_S_SIDE)
        common_place = _paired_placements(base_request)[0]
        interface = _resolve_interface(single, common_place, request.common_beam_layout)
        layers = _layer_demands(interface.demand, _fingerprint(proof))
        interface = _with_common_resistance(base_request, single, interface, layers)
        supported_failure = _common_supported_failure(interface)
        common_group = replace(
            common_group,
            resistance=interface.resistance,
            layer_demands=layers,
            result_fingerprint=_fingerprint(
                (common_group.result_fingerprint, interface.resistance, layers)
            ),
        )
        resistance_evaluated = True
    status = (
        BeamConcretePairedAngleStatus.INVALID_GEOMETRY
        if not geometry_valid
        else BeamConcretePairedAngleStatus.FAIL
        if supported_failure
        else BeamConcretePairedAngleStatus.NOT_EVALUATED
    )
    input_fingerprint = _input_fingerprint(request)
    wall_geometry_fingerprint = _fingerprint(
        (
            ConcreteWallFrame(),
            tuple(
                _quantity(getattr(request.wall, name), unit)
                for name in ("width", "height", "thickness")
            ),
            _quantity(request.wall.connection_origin_h, unit),
            _quantity(request.wall.connection_origin_v, unit),
        )
    )
    beam = request.beam_profile.dimensions
    beam_geometry_fingerprint = (
        _fingerprint(
            (
                request.beam_profile.family,
                tuple(
                    _quantity(getattr(beam, name), unit)
                    for name in (
                        "member_length",
                        "depth",
                        "flange_width",
                        "web_thickness",
                        "flange_thickness",
                    )
                ),
                request.beam_end_gap,
            )
        )
        if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION
        else _fingerprint(
            (
                request.contract_version,
                request.beam_profile.family,
                request.beam_profile.orientation,
                request.beam_profile.selected_surface,
                tuple(
                    (field.name, _quantity(getattr(beam, field.name), unit))
                    for field in fields(beam)
                ),
                request.beam_end_gap,
            )
        )
    )
    paired_connector_geometry_fingerprint = _fingerprint(
        (
            tuple(
                _quantity(getattr(request.connector_dimensions, field.name), unit)
                for field in fields(request.connector_dimensions)
            ),
            request.connector_length_anchor_position,
            request.common_beam_layout.row_count,
            request.common_beam_layout.bolts_per_row,
            tuple(
                _quantity(getattr(request.common_beam_layout, name), unit)
                for name in (
                    "pitch",
                    "gauge",
                    "heel_edge_distance",
                    "free_edge_distance",
                    "negative_end_distance",
                    "positive_end_distance",
                )
            ),
        )
    )
    handoff_mode = (
        ExternalAnchorHandoffMode.BRANCH_RESOLVED
        if branch_resolved
        else ExternalAnchorHandoffMode.COMBINED_LAYOUT
    )
    combined_handoff_fingerprint = _fingerprint(
        (
            combined_wrench,
            positive.result_fingerprint,
            negative.result_fingerprint,
            *(
                (handoff_mode, "2.5A-RC1", BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION)
                if is_r2
                else ()
            ),
        )
    )
    anchor_geometry_fingerprint = _fingerprint(
        (request.external_anchor, positive.anchors, negative.anchors)
    )
    application_fingerprint = _fingerprint(
        (
            input_fingerprint,
            wall_geometry_fingerprint,
            beam_geometry_fingerprint,
            paired_connector_geometry_fingerprint,
            common_group.result_fingerprint,
            positive.result_fingerprint,
            negative.result_fingerprint,
            combined_handoff_fingerprint,
            "2.5A-RC1",
            "2.5B-RC1",
            "2.6A-RC1",
            *(
                (
                    handoff_mode,
                    _wall_vector((minor, _ZERO, _ZERO), force_unit),
                    _wall_vector(beam_reference_values, unit),
                    BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
                )
                if is_r2
                else ()
            ),
        )
    )
    limitation_values = tuple(
        (name, status_value.value) for name, status_value in EXTERNAL_DESIGN_LIMITATIONS
    )
    if request.contract_version in {
        BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION,
        BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION,
    } and (positive.nominal_demand is None or negative.nominal_demand is None):
        limitation_values = (
            *limitation_values,
            ("WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION", "EXTERNAL_DESIGN_REQUIRED"),
        )
    if is_r2 and minor != 0:
        limitation_values = (
            *limitation_values,
            ("MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION", "NOT_EVALUATED"),
            ("COMMON_MEMBER_GROUP_BOLT_AXIS_RESPONSE", "NOT_EVALUATED"),
        )
    if is_r2 and axial != 0:
        limitation_values = (
            *limitation_values,
            ("CLIP_ANGLE_WALL_LEG_AXIAL_TRANSFER_AND_PRYING", "NOT_EVALUATED"),
            ("WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION", "EXTERNAL_DESIGN_REQUIRED"),
        )
    if is_r2 and (minor != 0 or axial != 0):
        limitation_values = (
            *limitation_values,
            ("NONMAJOR_FORCE_CONNECTION_QUALIFICATION", "NOT_EVALUATED"),
        )
    demand_method_versions = (
        ("2.5A-RC1", "2.5B-RC1", "2.6A-RC1", "3.3B-RC1", "3.5A-RC1")
        if request.contract_version == BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION
        else (
            "2.5A-RC1",
            "2.5B-RC1",
            "2.6A-RC1",
            "3.3C3-RC1",
            request.contract_version,
        )
    )
    handoff_schema_version = (
        BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION
        if is_r2
        else EXTERNAL_ANCHOR_HANDOFF_SCHEMA_VERSION
    )
    handoff_without_fp = (
        handoff_schema_version,
        "FACTORED",
        "CANONICAL_EXACT_WITH_DECLARED_QUANTITY_UNITS",
        application_fingerprint,
        ConcreteWallFrame(),
        (
            _quantity(request.wall.width, unit),
            _quantity(request.wall.height, unit),
            _quantity(request.wall.thickness, unit),
        ),
        _wall_vector(
            (request.wall.connection_origin_h, request.wall.connection_origin_v, _ZERO), unit
        ),
        _wall_vector(wall_reference_values, unit),
        combined_wrench,
        positive.result_fingerprint,
        negative.result_fingerprint,
        request.external_anchor,
        _quantity(request.connector_dimensions.thickness, unit),
        "H_W cross V_W = N_W; negative V is downward; moments use right-hand rule",
        demand_method_versions,
        input_fingerprint,
        wall_geometry_fingerprint,
        anchor_geometry_fingerprint,
        limitation_values,
        *((handoff_mode, "NOT_EVALUATED" if not branch_resolved else "RESOLVED") if is_r2 else ()),
    )
    handoff_fingerprint = _fingerprint(handoff_without_fp)
    handoff = ExternalAnchorDesignHandoff(
        handoff_schema_version,
        request.request_id,
        "FACTORED",
        request.unit_system.value,
        application_fingerprint,
        ConcreteWallFrame(),
        (
            _quantity(request.wall.width, unit),
            _quantity(request.wall.height, unit),
            _quantity(request.wall.thickness, unit),
        ),
        _wall_vector(
            (request.wall.connection_origin_h, request.wall.connection_origin_v, _ZERO), unit
        ),
        _wall_vector(wall_reference_values, unit),
        combined_wrench,
        positive,
        negative,
        request.external_anchor,
        _quantity(request.connector_dimensions.thickness, unit),
        "H_W cross V_W = N_W; negative V is downward; moments use right-hand rule",
        demand_method_versions,
        input_fingerprint,
        wall_geometry_fingerprint,
        anchor_geometry_fingerprint,
        limitation_values,
        handoff_fingerprint,
        handoff_mode if is_r2 else None,
        "NOT_EVALUATED" if is_r2 and not branch_resolved else "RESOLVED" if is_r2 else None,
        positive.anchors + negative.anchors if is_r2 else None,
    )
    handoff_json = json.dumps(
        cast(dict[str, object], _export_value(handoff)),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    engineering_fingerprint = _fingerprint(
        (application_fingerprint, handoff_fingerprint, status, common_group.resistance)
    )
    warnings = tuple(
        dict.fromkeys(
            (
                *reasons,
                *(f"{item}=NOT_EVALUATED" for item in PAIRED_CLIP_ANGLE_REQUIRED_CHECKS),
                *(f"{name}={value}" for name, value in limitation_values),
            )
        )
    )
    visualization = (
        None
        if not geometry_valid or base_preview.visualization is None
        else _visualization(
            request,
            base_preview.visualization,
            positive,
            negative,
            combined_wrench,
            _wall_vector(beam_reference_values, unit),
        )
    )
    return BeamConcretePairedAnglePreviewResult(
        request.request_id,
        request.contract_version,
        BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_SCHEMA_VERSION,
        "BEAM_TO_CONCRETE_WALL_SYMMETRIC_PAIRED_CLIP_ANGLES",
        ConcreteWallFrame(),
        proof,
        common_group,
        positive,
        negative,
        combined_wrench,
        handoff,
        handoff_json,
        ClipAngleGeometryStatus.VALID
        if geometry_valid
        else ClipAngleGeometryStatus.INVALID_GEOMETRY,
        reasons,
        status,
        False,
        resistance_evaluated,
        geometry_valid and (minor != 0 or major != 0 or axial != 0),
        True,
        limitation_values,
        PAIRED_CLIP_ANGLE_REQUIRED_CHECKS,
        warnings,
        input_fingerprint,
        wall_geometry_fingerprint,
        beam_geometry_fingerprint,
        paired_connector_geometry_fingerprint,
        combined_handoff_fingerprint,
        engineering_fingerprint,
        application_fingerprint,
        visualization,
        handoff_mode if is_r2 else None,
        "NOT_EVALUATED" if is_r2 and not branch_resolved else "RESOLVED" if is_r2 else None,
        _quantity(minor, force_unit) if is_r2 else None,
        _wall_vector(beam_reference_values, unit) if is_r2 else None,
    )


def preview_beam_concrete_paired_angle(
    request: BeamConcretePairedAngleRequest,
) -> BeamConcretePairedAnglePreviewResult:
    """Resolve exact geometry, demand, wrenches, and handoff with zero resistance."""

    return _preview(request, resistance=False)


def design_check_beam_concrete_paired_angle(
    request: BeamConcretePairedAngleRequest,
) -> BeamConcretePairedAngleDesignResult:
    """Run only the accepted beam/FRP-side design seam; anchors remain external."""

    preview = _preview(request, resistance=True)
    failed = preview.assembly_status is BeamConcretePairedAngleStatus.FAIL
    return BeamConcretePairedAngleDesignResult(
        preview,
        preview.assembly_status,
        "NOT_EVALUATED",
        False,
        failed,
        _fingerprint(
            (
                preview.engineering_fingerprint,
                preview.common_beam_group.resistance,
                preview.assembly_status,
            )
        ),
    )


__all__ = (
    "BEAM_CONCRETE_PAIRED_ANGLE_CONTRACT_VERSION",
    "BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_SCHEMA_VERSION",
    "BEAM_CONCRETE_PAIRED_ANGLE_R1_CONTRACT_VERSION",
    "BEAM_CONCRETE_PAIRED_ANGLE_R2_CONTRACT_VERSION",
    "BEAM_CONCRETE_PAIRED_ANGLE_VISUALIZATION_SCHEMA_VERSION",
    "EXTERNAL_ANCHOR_HANDOFF_SCHEMA_VERSION",
    "EXTERNAL_ANCHOR_PRESENTATION_LABEL",
    "WALL_GROUP_DEMAND_LABEL",
    "BeamConcretePairedAngleDesignResult",
    "BeamConcretePairedAnglePreviewResult",
    "BeamConcretePairedAngleRequest",
    "BeamConcretePairedAngleStatus",
    "BeamConcretePairedAngleVisualizationSnapshot",
    "ExternalAnchorDesignHandoff",
    "ExternalAnchorHandoffMode",
    "WallAnchorGroupResult",
    "design_check_beam_concrete_paired_angle",
    "preview_beam_concrete_paired_angle",
)
