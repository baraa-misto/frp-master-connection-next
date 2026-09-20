"""Stage 3.5C column-base web-angle orchestration and external-design handoff."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, localcontext
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from frp_master_connection.application.column_base_profile_orchestration import (
        ColumnBaseProfileDesignResult,
        ColumnBaseProfilePreviewResult,
    )

from frp_master_connection.application.beam_concrete_paired_angle_orchestration import (
    _export_value,
)
from frp_master_connection.application.clip_angle_orchestration import (
    CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
    ClipAngleBoltTrace,
    ClipAngleBoxTrace,
    ClipAngleInterfaceResult,
    ClipAngleMaterialRegionTrace,
    ClipAngleOrchestrationRequest,
    ClipAngleVectorInput,
    _layout_coordinates,
    _multirow_request,
    _placement,
    _resolve_interface,
    _supported_failure,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationResponse,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.application.paired_clip_angle_orchestration import _layer_demands
from frp_master_connection.calculation import (
    EccentricDemandResult,
    LayerInPlaneDemandAllocation,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    canonical_decimal_string,
)
from frp_master_connection.domain import (
    ClipAngleHand,
    ClipAngleInterfaceIdentity,
    ClipAngleLengthAnchor,
    ClipAngleSupportDimensions,
    ClipAngleSupportRole,
    ColumnBaseAssembly,
    ColumnBaseFrame,
    ColumnBaseProfileRequest,
    ColumnBaseRequest,
    ColumnBaseSide,
    ColumnBaseSignedRequest,
    ColumnBaseStatus,
    ColumnBaseVector,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ExternalAnchorGeometry,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    PairedClipAngleLayerIdentity,
    PrincipalAxisFamily,
    SelectedSupportFlange,
    WideFlangeIProfileDimensions,
)

COLUMN_BASE_WEB_ANGLE_CONTRACT_VERSION = "3.5C-RC1"
COLUMN_BASE_WEB_ANGLE_SIGNED_CONTRACT_VERSION = "3.5C-R2-RC1"
COLUMN_BASE_WEB_ANGLE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
COLUMN_BASE_WEB_ANGLE_HANDOFF_SCHEMA_VERSION = "3.5C-RC1"
COLUMN_BASE_WEB_ANGLE_SIGNED_HANDOFF_SCHEMA_VERSION = "3.5C-R2-RC1"

ColumnBaseAnyRequest = ColumnBaseRequest | ColumnBaseSignedRequest

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)
_HALF = Decimal("0.5")


class ColumnBaseGeometryStatus(StrEnum):
    VALID = "VALID"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class ColumnBaseWrench:
    reference_s_t_l: ColumnBaseVector
    force_s_t_l: ColumnBaseVector
    moment_s_t_l: ColumnBaseVector
    provenance: str


@dataclass(frozen=True, slots=True)
class ColumnBaseLayerDirectionTrace:
    layer_id: str
    material_axis: str
    material_axis_angle_degrees: Decimal
    bearing_direction_classification: str
    force_direction_s_l: tuple[PhysicalQuantity, PhysicalQuantity]


@dataclass(frozen=True, slots=True)
class ColumnBaseLayerDemandTrace:
    bolt_id: str
    layer_id: str
    fraction_of_parent: Decimal
    force_s: PhysicalQuantity
    force_l: PhysicalQuantity
    resultant: PhysicalQuantity
    parent_demand_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseComponentTransferTrace:
    column_web_axial_demand: PhysicalQuantity
    column_web_fraction: Decimal
    column_web_material_direction: str
    angle_system_axial_demand: PhysicalQuantity
    angle_system_fraction: Decimal
    angle_vertical_leg_material_direction: str
    positive_angle_axial_demand: PhysicalQuantity | None
    negative_angle_axial_demand: PhysicalQuantity | None
    single_angle_axial_demand: PhysicalQuantity | None
    branch_fraction: Decimal
    foundation_axial_action: PhysicalQuantity
    component_design_demands_summed_for_equilibrium: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBaseSignedComponentTransferTrace:
    axial_mode: str
    column_web_signed_axial_action: PhysicalQuantity
    column_web_design_magnitude: PhysicalQuantity
    column_web_fraction: Decimal
    column_web_material_direction: str
    column_web_signed_material_direction: str
    angle_system_signed_axial_action: PhysicalQuantity
    angle_system_design_magnitude: PhysicalQuantity
    angle_system_fraction: Decimal
    angle_vertical_leg_material_direction: str
    angle_vertical_leg_signed_material_direction: str
    positive_angle_signed_axial_action: PhysicalQuantity | None
    negative_angle_signed_axial_action: PhysicalQuantity | None
    single_angle_signed_axial_action: PhysicalQuantity | None
    branch_fraction: Decimal
    foundation_signed_axial_action: PhysicalQuantity
    component_design_demands_summed_for_equilibrium: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBaseAnchorTrace:
    anchor_id: str
    group_id: str
    coordinate_s_t_l: ColumnBaseVector
    axis_s_t_l: tuple[Decimal, Decimal, Decimal]
    shank_start_s_t_l: ColumnBaseVector
    shank_end_s_t_l: ColumnBaseVector
    exterior_washer_center_s_t_l: ColumnBaseVector
    exterior_nut_reference_s_t_l: ColumnBaseVector
    penetrated_layers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ColumnBaseBearingFootprint:
    footprint_id: str
    angle_id: str
    corners_s_t_l: tuple[ColumnBaseVector, ...]
    capacity_inferred: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBaseAnchorGroupResult:
    group_id: str
    side: ColumnBaseSide
    centroid_s_t_l: ColumnBaseVector
    anchors: tuple[ColumnBaseAnchorTrace, ...]
    bearing_footprint: ColumnBaseBearingFootprint
    branch_wrench: ColumnBaseWrench | None
    capacity_status: str = "EXTERNAL_DESIGN_REQUIRED"


@dataclass(frozen=True, slots=True)
class ColumnBaseExternalHandoff:
    schema_version: str
    request_id: str
    unit_system: str
    base_frame: ColumnBaseFrame
    combined_foundation_wrench: ColumnBaseWrench
    component_transfer: ColumnBaseComponentTransferTrace
    anchor_groups: tuple[ColumnBaseAnchorGroupResult, ...]
    bearing_footprints: tuple[ColumnBaseBearingFootprint, ...]
    limitations: tuple[tuple[str, str], ...]
    demand_method_versions: tuple[str, ...]
    input_fingerprint: str
    handoff_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseSignedExternalHandoff:
    schema_version: str
    request_id: str
    unit_system: str
    base_frame: ColumnBaseFrame
    signed_axial_force: PhysicalQuantity
    axial_mode: str
    column_end_contact_applicability: str
    combined_foundation_wrench: ColumnBaseWrench
    component_transfer: ColumnBaseSignedComponentTransferTrace
    anchor_groups: tuple[ColumnBaseAnchorGroupResult, ...]
    bearing_footprints: tuple[ColumnBaseBearingFootprint, ...]
    limitations: tuple[tuple[str, str], ...]
    demand_method_versions: tuple[str, ...]
    input_fingerprint: str
    handoff_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseVisualizationSnapshot:
    schema_version: str
    base_frame: ColumnBaseFrame
    boxes: tuple[ClipAngleBoxTrace, ...]
    web_bolts: tuple[ClipAngleBoltTrace, ...]
    anchors: tuple[ColumnBaseAnchorTrace, ...]
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    external_anchor_geometry: ExternalAnchorGeometry
    material_regions: tuple[ClipAngleMaterialRegionTrace, ...]
    applied_force_s_t_l: ColumnBaseVector
    action_reference_s_t_l: ColumnBaseVector
    selected_surfaces: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ColumnBasePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    base_frame: ColumnBaseFrame
    assembly: ColumnBaseAssembly
    single_side: ColumnBaseSide
    web_group_demand: EccentricDemandResult
    layer_demands: tuple[ColumnBaseLayerDemandTrace, ...]
    layer_directions: tuple[ColumnBaseLayerDirectionTrace, ...]
    component_transfer: ColumnBaseComponentTransferTrace | ColumnBaseSignedComponentTransferTrace
    combined_foundation_wrench: ColumnBaseWrench
    anchor_groups: tuple[ColumnBaseAnchorGroupResult, ...]
    external_handoff: ColumnBaseExternalHandoff | ColumnBaseSignedExternalHandoff
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
    visualization: ColumnBaseVisualizationSnapshot | None


@dataclass(frozen=True, slots=True)
class ColumnBaseDesignResult:
    preview: ColumnBasePreviewResult
    web_group_resistance: MultiRowOrchestrationResponse | None
    assembly_status: ColumnBaseStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_local_failure_present: bool
    result_fingerprint: str


_LIMITATIONS = (
    ("BASE_ANGLE_CW_BODY_AND_HEEL_COMPRESSION_TRANSFER", "NOT_EVALUATED"),
    ("HORIZONTAL_LEG_BEARING_AND_PRYING", "NOT_EVALUATED"),
    ("CONCRETE_BEARING_CAPACITY", "EXTERNAL_DESIGN_REQUIRED"),
    ("ANCHOR_STEEL_AND_CONCRETE_CAPACITY", "EXTERNAL_DESIGN_REQUIRED"),
    ("COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION", "EXTERNAL_DESIGN_REQUIRED"),
    ("COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE", "NOT_EVALUATED"),
)

_R2_ALWAYS_LIMITATIONS = (
    ("CONCRETE_SUBSTRATE_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("ANCHOR_SYSTEM_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("ANCHOR_STEEL_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("ANCHOR_CONCRETE_LIMIT_STATES", "EXTERNAL_DESIGN_REQUIRED"),
    ("EXTERNAL_ANCHOR_DEMAND_VERIFICATION", "REQUIRED"),
)

_R2_COMPRESSION_LIMITATIONS = (
    ("BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
)

_R2_UPLIFT_LIMITATIONS = (
    ("COLUMN_END_BEARING_FOR_UPLIFT", "NOT_REQUIRED"),
    ("BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER", "NOT_EVALUATED"),
    ("BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING", "NOT_EVALUATED"),
    ("ANCHOR_TENSION_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"),
    ("CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES", "EXTERNAL_DESIGN_REQUIRED"),
    ("REVERSE_LOAD_LOCAL_FAILURE_PATH_APPLICABILITY", "NOT_EVALUATED"),
)


def _quantity(value: Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _export_value(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_export(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {
            "canonical_value": canonical_decimal_string(value.canonical_magnitude),
            "dimension": value.dimension.value,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _canonical_export(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, tuple):
        return [_canonical_export(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical_export(item) for key, item in sorted(value.items())}
    return value


def _canonical_fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonical_export(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> ColumnBaseVector:
    return ColumnBaseVector(*(_quantity(value, unit) for value in values))


def _cross(
    left: tuple[Decimal, Decimal, Decimal], right: tuple[Decimal, Decimal, Decimal]
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
) -> ColumnBaseWrench:
    arm = cast(
        tuple[Decimal, Decimal, Decimal],
        tuple(a - b for a, b in zip(source_reference, reference, strict=True)),
    )
    return ColumnBaseWrench(
        _vector(reference, length_unit),
        _vector(force, force_unit),
        _vector(_cross(arm, force), moment_unit),
        provenance,
    )


def _canonical_quantity(value: PhysicalQuantity) -> Decimal:
    return value.canonical_magnitude


def _signed_axial_force(request: ColumnBaseAnyRequest) -> PhysicalQuantity:
    if isinstance(request, ColumnBaseSignedRequest):
        return request.signed_axial_force
    return request.axial_compression * Decimal(-1)


def _axial_mode(request: ColumnBaseAnyRequest) -> str:
    value = _signed_axial_force(request).canonical_magnitude
    return "UPLIFT" if value > 0 else "COMPRESSION" if value < 0 else "ZERO"


def _request_axial_fingerprint_quantity(request: ColumnBaseAnyRequest) -> PhysicalQuantity:
    if isinstance(request, ColumnBaseSignedRequest):
        return request.signed_axial_force
    return request.axial_compression


def _canonical_request_fingerprint(request: ColumnBaseAnyRequest) -> str:
    return _fingerprint(
        (
            request.contract_version,
            request.assembly,
            request.single_side,
            tuple(
                _canonical_quantity(value)
                for value in (
                    request.concrete.s_dimension,
                    request.concrete.t_dimension,
                    request.concrete.depth,
                    request.column.depth_s,
                    request.column.flange_width_t,
                    request.column.web_thickness,
                    request.column.flange_thickness,
                    request.column.display_height,
                )
            ),
            tuple(
                _quantity(
                    getattr(request.angle, name), request.source_length_unit
                ).canonical_magnitude
                for name in (
                    "connected_leg_width",
                    "support_leg_width",
                    "thickness",
                    "connector_length",
                )
            ),
            request.web_layout.row_count,
            request.web_layout.bolts_per_row,
            tuple(
                (
                    None
                    if getattr(request.web_layout, name) is None
                    else _quantity(
                        cast(Decimal, getattr(request.web_layout, name)), request.source_length_unit
                    ).canonical_magnitude
                )
                for name in ("pitch", "gauge", "length_offset", "width_offset")
            ),
            tuple(
                _canonical_quantity(value)
                for value in (
                    request.web_bolt_diameter,
                    request.web_hole_diameter,
                    request.external_anchor.nominal_diameter,
                    request.external_anchor.hole_diameter,
                    request.external_anchor.specified_embedment,
                    _request_axial_fingerprint_quantity(request),
                    request.web_plane_shear,
                    request.web_normal_shear,
                    request.action_reference.s,
                    request.action_reference.t,
                    request.action_reference.longitudinal,
                )
            ),
        )
    )


def _surrogate_request(
    request: ColumnBaseAnyRequest,
) -> tuple[ClipAngleOrchestrationRequest, ClipAngleInterfaceResult]:
    unit = request.source_length_unit
    column = request.column
    profile = MemberProfile(
        "stage-3-5c-column-web-calculation-profile",
        "clip-angle-connected-member",
        MemberRole.BEAM,
        MemberProfileFamily.WIDE_FLANGE_I,
        WideFlangeIProfileDimensions(
            column.display_height.to(unit).magnitude,
            column.depth_s.to(unit).magnitude,
            column.flange_width_t.to(unit).magnitude,
            column.web_thickness.to(unit).magnitude,
            column.flange_thickness.to(unit).magnitude,
        ),
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(
                CoordinateFrameKind.MEMBER_LOCAL, "clip-angle-connected-member"
            ),
            PrincipalAxisFamily.X,
        ),
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.WEB_POS_FACE,
    )
    support = ClipAngleSupportDimensions(
        column.display_height.to(unit).magnitude,
        column.depth_s.to(unit).magnitude,
        column.flange_width_t.to(unit).magnitude,
        column.web_thickness.to(unit).magnitude,
        column.flange_thickness.to(unit).magnitude,
    )
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    force = ClipAngleVectorInput(
        request.web_normal_shear.to(force_unit),
        request.web_plane_shear.to(force_unit),
        _signed_axial_force(request).to(force_unit),
    )
    zero_moment = ClipAngleVectorInput(*(_quantity(_ZERO, moment_unit) for _ in range(3)))
    widths, lengths = _layout_coordinates(
        request.web_layout, request.angle, request.angle.connected_leg_width
    )
    group_reference = ClipAngleVectorInput(
        _quantity(sum(widths, _ZERO) / Decimal(len(widths)), unit),
        _quantity(_ZERO, unit),
        _quantity(sum(lengths, _ZERO) / Decimal(len(lengths)), unit),
    )
    single = ClipAngleOrchestrationRequest(
        request.request_id,
        request.unit_system,
        unit,
        ClipAngleHand.POSITIVE_S_SIDE,
        ClipAngleSupportRole.W_COLUMN_FLANGE,
        SelectedSupportFlange.POSITIVE_LOCAL_Z,
        request.angle,
        support,
        profile,
        request.web_layout,
        request.web_layout,
        request.web_bolt_diameter,
        request.web_hole_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        force,
        zero_moment,
        group_reference,
        _ZERO,
        False,
        None,
        ClipAngleLengthAnchor.CENTER,
        _quantity(_ZERO, unit),
    )
    half = request.angle.connector_length / _TWO
    placement = _placement(
        single,
        ClipAngleInterfaceIdentity.CONNECTED_MEMBER_TO_CONNECTED_LEG,
        request.web_layout,
        request.angle.connected_leg_width,
        half,
        -half,
    )
    return single, _resolve_interface(single, placement, request.web_layout)


def _material_classification(force_s: Decimal, force_l: Decimal, material_angle: Decimal) -> str:
    if force_s == 0 and force_l == 0:
        return "NO_IN_PLANE_ACTION"
    force_angle = math.degrees(math.atan2(float(force_l), float(force_s))) % 180
    difference = abs(force_angle - float(material_angle)) % 180
    acute = min(difference, 180 - difference)
    return "LONGITUDINAL" if acute <= 45 else "TRANSVERSE"


def _layer_directions(request: ColumnBaseAnyRequest) -> tuple[ColumnBaseLayerDirectionTrace, ...]:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    force_s = request.web_plane_shear.to(force_unit)
    force_l = _signed_axial_force(request).to(force_unit)
    angle_ids = (
        ("POSITIVE_BASE_ANGLE_VERTICAL_LEG", "NEGATIVE_BASE_ANGLE_VERTICAL_LEG")
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
        else (f"{request.single_side.value}_BASE_ANGLE_VERTICAL_LEG",)
    )
    return (
        ColumnBaseLayerDirectionTrace(
            "COLUMN_WEB",
            "LW",
            Decimal(90),
            _material_classification(force_s.magnitude, force_l.magnitude, Decimal(90)),
            (force_s, force_l),
        ),
        *tuple(
            ColumnBaseLayerDirectionTrace(
                layer_id,
                "CW",
                _ZERO,
                _material_classification(force_s.magnitude, force_l.magnitude, _ZERO),
                (force_s, force_l),
            )
            for layer_id in angle_ids
        ),
    )


def _layer_demands_for_request(
    request: ColumnBaseAnyRequest, demand: EccentricDemandResult
) -> tuple[ColumnBaseLayerDemandTrace, ...]:
    if not demand.scenarios:
        return ()
    fractions = (
        (
            ("POSITIVE_BASE_ANGLE_VERTICAL_LEG", _HALF),
            ("COLUMN_WEB", _ONE),
            ("NEGATIVE_BASE_ANGLE_VERTICAL_LEG", _HALF),
        )
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
        else ((f"{request.single_side.value}_BASE_ANGLE_VERTICAL_LEG", _ONE), ("COLUMN_WEB", _ONE))
    )
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN

    def scaled(value: PhysicalQuantity, fraction: Decimal) -> PhysicalQuantity:
        with localcontext() as context:
            context.prec = 100
            converted = value.to(force_unit)
            return PhysicalQuantity.of(converted.magnitude * fraction, force_unit)

    return tuple(
        ColumnBaseLayerDemandTrace(
            bolt.bolt_id,
            layer_id,
            fraction,
            scaled(bolt.total_force.u, fraction),
            scaled(bolt.total_force.v, fraction),
            scaled(bolt.total_force_magnitude, fraction),
            demand.result_fingerprint,
        )
        for bolt in demand.scenarios[0].per_bolt
        for layer_id, fraction in fractions
    )


def _component_transfer(
    request: ColumnBaseAnyRequest,
) -> ColumnBaseComponentTransferTrace | ColumnBaseSignedComponentTransferTrace:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    if isinstance(request, ColumnBaseSignedRequest):
        signed_axial = request.signed_axial_force.to(force_unit)
        magnitude = PhysicalQuantity.of(abs(signed_axial.magnitude), force_unit)
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES:
            positive_signed = signed_axial * _HALF
            negative_signed = signed_axial * _HALF
            single_signed = None
            fraction = _HALF
        else:
            positive_signed = None
            negative_signed = None
            single_signed = signed_axial
            fraction = _ONE
        sign = "+" if signed_axial.magnitude > 0 else "-" if signed_axial.magnitude < 0 else ""
        return ColumnBaseSignedComponentTransferTrace(
            _axial_mode(request),
            signed_axial,
            magnitude,
            _ONE,
            "LW",
            f"{sign}LW" if sign else "LW",
            signed_axial,
            magnitude,
            _ONE,
            "CW",
            f"{sign}CW" if sign else "CW",
            positive_signed,
            negative_signed,
            single_signed,
            fraction,
            signed_axial,
        )
    axial = request.axial_compression.to(force_unit)
    if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES:
        positive = axial * _HALF
        negative = axial * _HALF
        single = None
        fraction = _HALF
    else:
        positive = None
        negative = None
        single = axial
        fraction = _ONE
    return ColumnBaseComponentTransferTrace(
        axial,
        _ONE,
        "LW",
        axial,
        _ONE,
        "CW",
        positive,
        negative,
        single,
        fraction,
        axial,
    )


def _web_bolts(
    request: ColumnBaseAnyRequest,
) -> tuple[ClipAngleBoltTrace, ...]:
    unit = request.source_length_unit
    widths, lengths = _layout_coordinates(
        request.web_layout, request.angle, request.angle.connected_leg_width
    )
    web_half = request.column.web_thickness.to(unit).magnitude / _TWO
    angle_thickness = request.angle.thickness
    double = request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
    side = request.single_side.sign
    layer_ids: tuple[str, ...]
    if double:
        start_t, end_t = web_half + angle_thickness, -web_half - angle_thickness
        layer_ids = (
            "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
            "COLUMN_WEB",
            "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
        )
    elif side > 0:
        start_t, end_t = web_half + angle_thickness, -web_half
        layer_ids = ("POSITIVE_BASE_ANGLE_VERTICAL_LEG", "COLUMN_WEB")
    else:
        start_t, end_t = -web_half - angle_thickness, web_half
        layer_ids = ("NEGATIVE_BASE_ANGLE_VERTICAL_LEG", "COLUMN_WEB")
    return tuple(
        ClipAngleBoltTrace(
            f"COLUMN-WEB-R{row}-B{line}",
            f"ROW_{row}",
            f"BOLT_LINE_{line}",
            _quantity(s, unit),
            _quantity(longitudinal, unit),
            (
                _quantity(s, unit),
                _quantity(_ZERO, unit),
                _quantity(longitudinal, unit),
            ),
            (_ZERO, _ONE, _ZERO),
            layer_ids,
            (_quantity(s, unit), _quantity(start_t, unit), _quantity(longitudinal, unit)),
            (_quantity(s, unit), _quantity(end_t, unit), _quantity(longitudinal, unit)),
        )
        for row, longitudinal in enumerate(lengths, start=1)
        for line, s in enumerate(widths, start=1)
    )


def _angle_sides(request: ColumnBaseAnyRequest) -> tuple[ColumnBaseSide, ...]:
    return (
        (ColumnBaseSide.POSITIVE_T_C, ColumnBaseSide.NEGATIVE_T_C)
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
        else (request.single_side,)
    )


def _anchors(
    request: ColumnBaseAnyRequest, side: ColumnBaseSide
) -> tuple[ColumnBaseAnchorTrace, ...]:
    unit = request.source_length_unit
    pattern = request.anchor_pattern
    row_center = Decimal(pattern.row_count - 1) / _TWO
    line_center = Decimal(pattern.anchors_per_row - 1) / _TWO
    t_center = side.sign * pattern.centroid_offset_t.to(unit).magnitude
    embedment = request.external_anchor.specified_embedment.to(unit).magnitude
    washer_thickness = request.external_anchor.washer_thickness.to(unit).magnitude
    angle_thickness = request.angle.thickness
    group_id = (
        "POSITIVE_BASE_ANCHOR_GROUP"
        if side is ColumnBaseSide.POSITIVE_T_C
        else "NEGATIVE_BASE_ANCHOR_GROUP"
    )
    return tuple(
        ColumnBaseAnchorTrace(
            f"{group_id}-R{row + 1}-A{line + 1}",
            group_id,
            _vector((s, t, _ZERO), unit),
            (_ZERO, _ZERO, Decimal(-1)),
            _vector((s, t, _ZERO), unit),
            _vector((s, t, -embedment), unit),
            _vector((s, t, angle_thickness + washer_thickness / _TWO), unit),
            _vector((s, t, angle_thickness + washer_thickness), unit),
            (f"{side.value}_BASE_ANGLE_HORIZONTAL_LEG", "CONCRETE_BASE"),
        )
        for row in range(pattern.row_count)
        for line in range(pattern.anchors_per_row)
        for s in ((Decimal(row) - row_center) * pattern.pitch.to(unit).magnitude,)
        for t in (
            t_center + side.sign * (Decimal(line) - line_center) * pattern.gauge.to(unit).magnitude,
        )
    )


def _footprint(request: ColumnBaseAnyRequest, side: ColumnBaseSide) -> ColumnBaseBearingFootprint:
    unit = request.source_length_unit
    half_s = request.angle.connector_length / _TWO
    web_face = side.sign * request.column.web_thickness.to(unit).magnitude / _TWO
    outside = web_face + side.sign * request.angle.support_leg_width
    corners = (
        _vector((-half_s, web_face, _ZERO), unit),
        _vector((half_s, web_face, _ZERO), unit),
        _vector((half_s, outside, _ZERO), unit),
        _vector((-half_s, outside, _ZERO), unit),
    )
    prefix = "POSITIVE" if side is ColumnBaseSide.POSITIVE_T_C else "NEGATIVE"
    return ColumnBaseBearingFootprint(
        f"{prefix}_BASE_ANGLE_BEARING_FOOTPRINT",
        f"{prefix}_BASE_ANGLE",
        corners,
    )


def _anchor_groups(
    request: ColumnBaseAnyRequest,
    force: tuple[Decimal, Decimal, Decimal],
    source_reference: tuple[Decimal, Decimal, Decimal],
    branch_resolved: bool,
) -> tuple[ColumnBaseAnchorGroupResult, ...]:
    unit = request.source_length_unit
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    sides = _angle_sides(request)
    groups: list[ColumnBaseAnchorGroupResult] = []
    for side in sides:
        reference = (
            _ZERO,
            side.sign * request.anchor_pattern.centroid_offset_t.to(unit).magnitude,
            _ZERO,
        )
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES:
            branch_force = tuple(value * _HALF for value in force)
            wrench = (
                _wrench(
                    reference,
                    cast(tuple[Decimal, Decimal, Decimal], branch_force),
                    source_reference,
                    unit,
                    force_unit,
                    moment_unit,
                    "EXACT_SYMMETRIC_BRANCH_TRANSLATION_TO_BASE_ANCHOR_GROUP",
                )
                if branch_resolved
                else None
            )
        else:
            wrench = _wrench(
                reference,
                force,
                source_reference,
                unit,
                force_unit,
                moment_unit,
                "EXACT_SINGLE_ANGLE_TRANSLATION_TO_BASE_ANCHOR_GROUP",
            )
        prefix = "POSITIVE" if side is ColumnBaseSide.POSITIVE_T_C else "NEGATIVE"
        groups.append(
            ColumnBaseAnchorGroupResult(
                f"{prefix}_BASE_ANCHOR_GROUP",
                side,
                _vector(reference, unit),
                _anchors(request, side),
                _footprint(request, side),
                wrench,
            )
        )
    return tuple(groups)


def _geometry_reasons(
    request: ColumnBaseAnyRequest,
    bolts: tuple[ClipAngleBoltTrace, ...],
    groups: tuple[ColumnBaseAnchorGroupResult, ...],
) -> tuple[str, ...]:
    unit = request.source_length_unit
    reasons: list[str] = []
    hole_radius = request.web_hole_diameter.to(unit).magnitude / _TWO
    half_angle_s = request.angle.connector_length / _TWO
    vertical_height = request.angle.connected_leg_width
    clear_web_half = (
        request.column.depth_s.to(unit).magnitude
        - _TWO * request.column.flange_thickness.to(unit).magnitude
    ) / _TWO
    for bolt in bolts:
        s = bolt.global_center[0].to(unit).magnitude
        longitudinal = bolt.global_center[2].to(unit).magnitude
        if (
            abs(s) + hole_radius > half_angle_s
            or abs(s) + hole_radius > clear_web_half
            or longitudinal - hole_radius < 0
            or longitudinal + hole_radius > vertical_height
        ):
            reasons.append(f"WEB_BOLT_COMPLETE_HOLE_CONTAINMENT_INVALID:{bolt.bolt_id}")
    anchor_radius = request.external_anchor.hole_diameter.to(unit).magnitude / _TWO
    concrete_s_half = request.concrete.s_dimension.to(unit).magnitude / _TWO
    concrete_t_half = request.concrete.t_dimension.to(unit).magnitude / _TWO
    web_face = request.column.web_thickness.to(unit).magnitude / _TWO
    for group in groups:
        for anchor in group.anchors:
            s = anchor.coordinate_s_t_l.s.to(unit).magnitude
            t = anchor.coordinate_s_t_l.t.to(unit).magnitude
            local_t = abs(t) - web_face
            if abs(s) + anchor_radius > half_angle_s or not (
                anchor_radius <= local_t <= request.angle.support_leg_width - anchor_radius
            ):
                reasons.append(f"ANCHOR_HOLE_OUTSIDE_HORIZONTAL_LEG:{anchor.anchor_id}")
            if abs(s) + anchor_radius > concrete_s_half or abs(t) + anchor_radius > concrete_t_half:
                reasons.append(f"ANCHOR_HOLE_OUTSIDE_CONCRETE_PLAN:{anchor.anchor_id}")
    if (
        request.external_anchor.specified_embedment.to(unit).magnitude
        > request.concrete.depth.to(unit).magnitude
    ):
        reasons.append("ANCHOR_EMBEDMENT_EXCEEDS_CONCRETE_DEPTH")
    return tuple(dict.fromkeys(reasons))


def _boxes(request: ColumnBaseAnyRequest) -> tuple[ClipAngleBoxTrace, ...]:
    unit = request.source_length_unit
    column = request.column
    depth = column.depth_s.to(unit).magnitude
    width = column.flange_width_t.to(unit).magnitude
    web = column.web_thickness.to(unit).magnitude
    flange = column.flange_thickness.to(unit).magnitude
    height = column.display_height.to(unit).magnitude
    concrete_depth = request.concrete.depth.to(unit).magnitude

    # ClipAngleBoxTrace takes a quantity tuple for center; build directly to keep exact units.
    def exact_box(
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
            tuple(_quantity(value, unit) for value in center),  # type: ignore[arg-type]
            _quantity(size[0], unit),
            _quantity(size[1], unit),
            _quantity(size[2], unit),
            physical,
            region,
        )

    values = [
        exact_box(
            "CONCRETE-BASE",
            "concrete-base",
            "CONCRETE_BASE",
            (_ZERO, _ZERO, -concrete_depth / _TWO),
            (
                request.concrete.s_dimension.to(unit).magnitude,
                request.concrete.t_dimension.to(unit).magnitude,
                concrete_depth,
            ),
        ),
        exact_box(
            "COLUMN-WEB",
            "column",
            "COLUMN_WEB",
            (_ZERO, _ZERO, height / _TWO),
            (depth - _TWO * flange, web, height),
            "COLUMN_WEB",
            "COLUMN_WEB_MATERIAL_REGION",
        ),
        exact_box(
            "COLUMN-FLANGE-POS-S",
            "column",
            "COLUMN_FLANGE",
            (depth / _TWO - flange / _TWO, _ZERO, height / _TWO),
            (flange, width, height),
            "COLUMN_POSITIVE_FLANGE",
            "COLUMN_POSITIVE_FLANGE_MATERIAL_REGION",
        ),
        exact_box(
            "COLUMN-FLANGE-NEG-S",
            "column",
            "COLUMN_FLANGE",
            (-depth / _TWO + flange / _TWO, _ZERO, height / _TWO),
            (flange, width, height),
            "COLUMN_NEGATIVE_FLANGE",
            "COLUMN_NEGATIVE_FLANGE_MATERIAL_REGION",
        ),
    ]
    for side in _angle_sides(request):
        prefix = "POSITIVE" if side is ColumnBaseSide.POSITIVE_T_C else "NEGATIVE"
        web_face = side.sign * web / _TWO
        vertical_center_t = web_face + side.sign * request.angle.thickness / _TWO
        horizontal_center_t = web_face + side.sign * request.angle.support_leg_width / _TWO
        values.extend(
            (
                exact_box(
                    f"{prefix}-BASE-ANGLE-VERTICAL",
                    f"{prefix.lower()}-base-angle",
                    "BASE_ANGLE_VERTICAL_LEG",
                    (_ZERO, vertical_center_t, request.angle.connected_leg_width / _TWO),
                    (
                        request.angle.connector_length,
                        request.angle.thickness,
                        request.angle.connected_leg_width,
                    ),
                    f"{prefix}_BASE_ANGLE_VERTICAL_LEG",
                    f"{prefix}_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                ),
                exact_box(
                    f"{prefix}-BASE-ANGLE-HORIZONTAL",
                    f"{prefix.lower()}-base-angle",
                    "BASE_ANGLE_HORIZONTAL_LEG",
                    (_ZERO, horizontal_center_t, request.angle.thickness / _TWO),
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


def _material_regions(request: ColumnBaseAnyRequest) -> tuple[ClipAngleMaterialRegionTrace, ...]:
    values = [
        ClipAngleMaterialRegionTrace(
            "COLUMN_WEB_MATERIAL_REGION",
            "COLUMN_WEB",
            (_ZERO, _ZERO, _ONE),
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ONE, _ZERO),
        ),
        ClipAngleMaterialRegionTrace(
            "COLUMN_POSITIVE_FLANGE_MATERIAL_REGION",
            "COLUMN_POSITIVE_FLANGE",
            (_ZERO, _ZERO, _ONE),
            (_ZERO, -_ONE, _ZERO),
            (_ONE, _ZERO, _ZERO),
        ),
        ClipAngleMaterialRegionTrace(
            "COLUMN_NEGATIVE_FLANGE_MATERIAL_REGION",
            "COLUMN_NEGATIVE_FLANGE",
            (_ZERO, _ZERO, _ONE),
            (_ZERO, _ONE, _ZERO),
            (-_ONE, _ZERO, _ZERO),
        ),
    ]
    for side in _angle_sides(request):
        prefix = "POSITIVE" if side is ColumnBaseSide.POSITIVE_T_C else "NEGATIVE"
        values.extend(
            (
                ClipAngleMaterialRegionTrace(
                    f"{prefix}_BASE_ANGLE_VERTICAL_MATERIAL_REGION",
                    f"{prefix}_BASE_ANGLE_VERTICAL_LEG",
                    (_ONE, _ZERO, _ZERO),
                    (_ZERO, _ZERO, _ONE),
                    (_ZERO, -side.sign, _ZERO),
                ),
                ClipAngleMaterialRegionTrace(
                    f"{prefix}_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION",
                    f"{prefix}_BASE_ANGLE_HORIZONTAL_LEG",
                    (_ONE, _ZERO, _ZERO),
                    (_ZERO, side.sign, _ZERO),
                    (_ZERO, _ZERO, side.sign),
                ),
            )
        )
    return tuple(values)


def _run_resistance(
    request: ColumnBaseAnyRequest,
    single: ClipAngleOrchestrationRequest,
    interface: ClipAngleInterfaceResult,
) -> MultiRowOrchestrationResponse | None:
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    force_u = request.web_plane_shear.to(force_unit)
    force_v = _signed_axial_force(request).to(force_unit)
    if force_u.magnitude != 0 and force_v.magnitude != 0:
        return None
    base = _multirow_request(single, interface.placement, request.web_layout, force_u, force_v)
    if base is None:
        return None
    member_layer, angle_layer = base.layers
    if request.assembly is ColumnBaseAssembly.SINGLE_BASE_ANGLE:
        single_layers = (
            replace(
                member_layer,
                layer_id="COLUMN_WEB",
                component_id="column",
                material_axis_angle_degrees=Decimal(90),
            ),
            replace(
                angle_layer,
                layer_id=f"{request.single_side.value}_BASE_ANGLE_VERTICAL_LEG",
                material_axis_angle_degrees=_ZERO,
            ),
        )
        return evaluate_multirow_connection_with_resolved_demand(
            replace(base, layers=single_layers), interface.demand
        )
    paired = _layer_demands(
        interface.demand,
        _canonical_fingerprint(("STAGE_3_5C_EXACT_SYMMETRY", request.assembly)),
    )
    double_layers = (
        replace(
            angle_layer,
            layer_id=PairedClipAngleLayerIdentity.POSITIVE_CONNECTED_LEG.value,
            component_id="positive-base-angle",
            material_axis_angle_degrees=_ZERO,
        ),
        replace(
            member_layer,
            layer_id=PairedClipAngleLayerIdentity.CONNECTED_MEMBER.value,
            component_id="column",
            material_axis_angle_degrees=Decimal(90),
        ),
        replace(
            angle_layer,
            layer_id=PairedClipAngleLayerIdentity.NEGATIVE_CONNECTED_LEG.value,
            component_id="negative-base-angle",
            material_axis_angle_degrees=_ZERO,
        ),
    )
    allocations = tuple(
        LayerInPlaneDemandAllocation(
            item.bolt_id,
            item.layer_id.value,
            item.fraction_of_total,
            "STAGE_3_5C_CONTROLLED_SYMMETRIC_LAYER_ALLOCATION",
            item.parent_demand_fingerprint,
        )
        for item in paired
    )
    return evaluate_multirow_connection_with_resolved_demand(
        replace(base, layers=double_layers), interface.demand, allocations
    )


def _preview(
    request: ColumnBaseAnyRequest, *, resistance: bool
) -> tuple[ColumnBasePreviewResult, MultiRowOrchestrationResponse | None]:
    unit = request.source_length_unit
    force_unit = Unit.KIP if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN
    moment_unit = (
        Unit.KIP_IN if request.unit_system is EngineeringUnitSystem.US_CUSTOMARY else Unit.KN_MM
    )
    force = (
        request.web_plane_shear.to(force_unit).magnitude,
        request.web_normal_shear.to(force_unit).magnitude,
        _signed_axial_force(request).to(force_unit).magnitude,
    )
    source_reference = (
        request.action_reference.s.to(unit).magnitude,
        request.action_reference.t.to(unit).magnitude,
        request.action_reference.longitudinal.to(unit).magnitude,
    )
    single, interface = _surrogate_request(request)
    bolts = _web_bolts(request)
    branch_resolved = (
        request.assembly is ColumnBaseAssembly.SINGLE_BASE_ANGLE
        or request.web_normal_shear.canonical_magnitude == 0
    )
    groups = _anchor_groups(request, force, source_reference, branch_resolved)
    reasons = _geometry_reasons(request, bolts, groups)
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
    component = _component_transfer(request)
    normal_limitations = (
        (("WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION", "NOT_EVALUATED"),)
        if request.assembly is ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES
        and request.web_normal_shear.canonical_magnitude != 0
        else ()
    )
    signed_axial = _signed_axial_force(request)
    combined_limitations = (
        (("COMBINED_IN_PLANE_LOCAL_RESISTANCE_PATH", "NOT_EVALUATED"),)
        if request.web_plane_shear.canonical_magnitude != 0
        and signed_axial.canonical_magnitude != 0
        else ()
    )
    successor_limitations = (
        (
            *_R2_ALWAYS_LIMITATIONS,
            *(
                _R2_UPLIFT_LIMITATIONS
                if signed_axial.canonical_magnitude > 0
                else _R2_COMPRESSION_LIMITATIONS
                if signed_axial.canonical_magnitude < 0
                else ()
            ),
        )
        if isinstance(request, ColumnBaseSignedRequest)
        else ()
    )
    limitations = (
        *_LIMITATIONS,
        *successor_limitations,
        *normal_limitations,
        *combined_limitations,
    )
    input_fingerprint = _canonical_request_fingerprint(request)
    contract_version = request.contract_version
    handoff_schema_version = (
        COLUMN_BASE_WEB_ANGLE_SIGNED_HANDOFF_SCHEMA_VERSION
        if isinstance(request, ColumnBaseSignedRequest)
        else COLUMN_BASE_WEB_ANGLE_HANDOFF_SCHEMA_VERSION
    )
    handoff_payload = (
        handoff_schema_version,
        input_fingerprint,
        combined,
        component,
        groups,
        limitations,
        ("2.5A-RC1", "2.4B-RC2", "3.3B-RC1", contract_version),
    )
    handoff_fingerprint = _canonical_fingerprint(handoff_payload)
    if isinstance(request, ColumnBaseSignedRequest):
        signed_component = cast(ColumnBaseSignedComponentTransferTrace, component)
        handoff: ColumnBaseExternalHandoff | ColumnBaseSignedExternalHandoff = (
            ColumnBaseSignedExternalHandoff(
                handoff_schema_version,
                request.request_id,
                request.unit_system.value,
                ColumnBaseFrame(),
                signed_axial,
                _axial_mode(request),
                "NOT_REQUIRED" if signed_axial.canonical_magnitude > 0 else "APPLICABLE",
                combined,
                signed_component,
                groups,
                tuple(group.bearing_footprint for group in groups),
                limitations,
                ("2.5A-RC1", "2.4B-RC2", "3.3B-RC1", contract_version),
                input_fingerprint,
                handoff_fingerprint,
            )
        )
    else:
        historical_component = cast(ColumnBaseComponentTransferTrace, component)
        handoff = ColumnBaseExternalHandoff(
            handoff_schema_version,
            request.request_id,
            request.unit_system.value,
            ColumnBaseFrame(),
            combined,
            historical_component,
            groups,
            tuple(group.bearing_footprint for group in groups),
            limitations,
            ("2.5A-RC1", "2.4B-RC2", "3.3B-RC1", contract_version),
            input_fingerprint,
            handoff_fingerprint,
        )
    handoff_json = json.dumps(
        cast(dict[str, object], _export_value(handoff)),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    response = (
        _run_resistance(request, single, interface) if resistance and geometry_valid else None
    )
    failed = response is not None and (
        _supported_failure(replace(interface, resistance=response))
        or any(
            item.overall_disposition.value == "FAIL" for item in response.automatic_handoff_results
        )
    )
    status = (
        ColumnBaseStatus.INVALID_GEOMETRY
        if not geometry_valid
        else ColumnBaseStatus.FAIL
        if failed
        else ColumnBaseStatus.NOT_EVALUATED
    )
    directions = _layer_directions(request)
    layer_demands = _layer_demands_for_request(request, interface.demand)
    application_fingerprint = _canonical_fingerprint(
        (
            input_fingerprint,
            tuple(
                (
                    bolt.bolt_id,
                    bolt.total_force.u,
                    bolt.total_force.v,
                    bolt.total_force_magnitude,
                )
                for scenario in interface.demand.scenarios
                for bolt in scenario.per_bolt
            ),
            tuple((item.layer_id, item.material_axis_angle_degrees) for item in directions),
            handoff_fingerprint,
            reasons,
        )
    )
    engineering_fingerprint = _canonical_fingerprint(
        (application_fingerprint, status, None if response is None else response.calculation_result)
    )
    warnings = tuple(dict.fromkeys((*reasons, *(f"{name}={value}" for name, value in limitations))))
    visualization = (
        None
        if not geometry_valid
        else ColumnBaseVisualizationSnapshot(
            CLIP_ANGLE_PREVIEW_SCHEMA_VERSION,
            ColumnBaseFrame(),
            _boxes(request),
            bolts,
            tuple(anchor for group in groups for anchor in group.anchors),
            request.web_bolt_diameter,
            request.web_hole_diameter,
            request.external_anchor,
            _material_regions(request),
            _vector(force, force_unit),
            request.action_reference,
            tuple(
                (
                    "COLUMN_WEB_POSITIVE_FACE"
                    if side is ColumnBaseSide.POSITIVE_T_C
                    else "COLUMN_WEB_NEGATIVE_FACE"
                )
                for side in _angle_sides(request)
            ),
        )
    )
    preview = ColumnBasePreviewResult(
        request.request_id,
        request.contract_version,
        COLUMN_BASE_WEB_ANGLE_PREVIEW_SCHEMA_VERSION,
        "COLUMN_BASE_USING_SINGLE_OR_DOUBLE_WEB_ANGLES_TO_CONCRETE",
        ColumnBaseFrame(),
        request.assembly,
        request.single_side,
        interface.demand,
        layer_demands,
        directions,
        component,
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
        geometry_valid and any(value != 0 for value in force),
        limitations,
        warnings,
        engineering_fingerprint,
        application_fingerprint,
        visualization,
    )
    return preview, response


@overload
def preview_column_base_web_angles(
    request: ColumnBaseProfileRequest,
) -> ColumnBaseProfilePreviewResult: ...


@overload
def preview_column_base_web_angles(request: ColumnBaseAnyRequest) -> ColumnBasePreviewResult: ...


def preview_column_base_web_angles(
    request: ColumnBaseAnyRequest | ColumnBaseProfileRequest,
) -> ColumnBasePreviewResult | ColumnBaseProfilePreviewResult:
    """Resolve authoritative geometry, demand, equilibrium, and handoff with zero resistance."""

    if isinstance(request, ColumnBaseProfileRequest):
        from frp_master_connection.application.column_base_profile_orchestration import (
            preview_column_base_profiles,
        )

        return preview_column_base_profiles(request)
    return _preview(request, resistance=False)[0]


@overload
def design_check_column_base_web_angles(
    request: ColumnBaseProfileRequest,
) -> ColumnBaseProfileDesignResult: ...


@overload
def design_check_column_base_web_angles(
    request: ColumnBaseAnyRequest,
) -> ColumnBaseDesignResult: ...


def design_check_column_base_web_angles(
    request: ColumnBaseAnyRequest | ColumnBaseProfileRequest,
) -> ColumnBaseDesignResult | ColumnBaseProfileDesignResult:
    """Run only existing supported local FRP/web-bolt resistance seams."""

    if isinstance(request, ColumnBaseProfileRequest):
        from frp_master_connection.application.column_base_profile_orchestration import (
            design_check_column_base_profiles,
        )

        return design_check_column_base_profiles(request)
    preview, response = _preview(request, resistance=True)
    failed = preview.assembly_status is ColumnBaseStatus.FAIL
    return ColumnBaseDesignResult(
        preview,
        response,
        preview.assembly_status,
        "NOT_EVALUATED",
        False,
        failed,
        _canonical_fingerprint(
            (preview.engineering_fingerprint, response, preview.assembly_status)
        ),
    )


__all__ = (
    "COLUMN_BASE_WEB_ANGLE_CONTRACT_VERSION",
    "COLUMN_BASE_WEB_ANGLE_HANDOFF_SCHEMA_VERSION",
    "COLUMN_BASE_WEB_ANGLE_PREVIEW_SCHEMA_VERSION",
    "COLUMN_BASE_WEB_ANGLE_SIGNED_CONTRACT_VERSION",
    "COLUMN_BASE_WEB_ANGLE_SIGNED_HANDOFF_SCHEMA_VERSION",
    "ColumnBaseAnchorGroupResult",
    "ColumnBaseAnchorTrace",
    "ColumnBaseBearingFootprint",
    "ColumnBaseComponentTransferTrace",
    "ColumnBaseDesignResult",
    "ColumnBaseExternalHandoff",
    "ColumnBaseGeometryStatus",
    "ColumnBaseLayerDemandTrace",
    "ColumnBaseLayerDirectionTrace",
    "ColumnBasePreviewResult",
    "ColumnBaseSignedComponentTransferTrace",
    "ColumnBaseSignedExternalHandoff",
    "ColumnBaseVisualizationSnapshot",
    "ColumnBaseWrench",
    "design_check_column_base_web_angles",
    "preview_column_base_web_angles",
)
