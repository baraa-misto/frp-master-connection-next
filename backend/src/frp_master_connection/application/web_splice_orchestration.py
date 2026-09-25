"""Stage 3.6A backend-authoritative symmetric double web-splice orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from enum import Enum
from typing import cast

from frp_master_connection.application.multirow_orchestration import (
    MultiRowDemandSource,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.calculation import (
    WEB_SPLICE_QUALIFICATION,
    WEB_SPLICE_RATIONAL_DISCLAIMER,
    WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
    WEB_SPLICE_RATIONAL_METHOD,
    WEB_SPLICE_RATIONAL_PANEL_MODEL,
    WEB_SPLICE_SLICE4_COMMIT,
    WEB_SPLICE_SLICE4_GOLDEN_SHA256,
    ConnectedMaterialPair,
    DoubleShearStatus,
    EndUseFactors,
    EndUsePropertyTrace,
    FirstRowPlanMethod,
    FRPPropertyKind,
    LapConfiguration,
    LayerInPlaneDemandAllocation,
    MultiRowCheckFamily,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    RationalBodyStatus,
    ThreadStatus,
    TimeEffectCategory,
    Unit,
    WebSpliceBodyInteractionResult,
    WebSpliceCriticalSectionAction,
    WebSpliceDoubleShearResult,
    adjusted_property_trace,
    canonical_decimal_string,
    create_locked_ice_material_snapshot,
    create_standard_hole,
    evaluate_double_shear_bolt,
    evaluate_rational_body_interaction,
    plate_in_plane_shear_strength,
    plate_longitudinal_compression_strength,
    plate_longitudinal_tension_strength,
    select_time_effect_factor,
)
from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    EccentricDemandInput,
    EccentricDemandResult,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
    calculate_eccentric_bolt_group_demand,
)
from frp_master_connection.calculation.multirow import (
    MethodProvenance,
    RowDistributionBasis,
    plan_row_demands,
)
from frp_master_connection.domain.web_splice import (
    WEB_SPLICE_CONTRACT_VERSION,
    WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    WebSpliceGroupId,
    WebSpliceRequest,
    WebSpliceStatus,
)

WEB_SPLICE_PREVIEW_SCHEMA_VERSION = "0.1.0-draft"
WEB_SPLICE_API_LIMITATIONS = (
    "WEB_SPLICE_PLATE_INTERGROUP_BODY_TRANSFER",
    "WEB_SPLICE_COMMON_BOLT_DOUBLE_SHEAR",
    "WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER",
)
WEB_SPLICE_RC2_LIMITATIONS = ("WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER",)
WEB_SPLICE_RC2_PREVIEW_SCHEMA_VERSION = "0.2.0-draft"
_ZERO = Decimal(0)
_ONE = Decimal(1)
_HALF = Decimal("0.5")
_SUPPORTED_LOCAL_FRP_FAMILIES = frozenset(
    {
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    }
)


@dataclass(frozen=True, slots=True)
class WebSpliceVector:
    l: PhysicalQuantity  # noqa: E741 - controlled L_S longitudinal axis
    v: PhysicalQuantity
    t: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class WebSpliceWrench:
    reference_l_v_t: WebSpliceVector
    force_l_v_t: WebSpliceVector
    moment_l_v_t: WebSpliceVector
    provenance: str


@dataclass(frozen=True, slots=True)
class WebSpliceBolt:
    bolt_id: str
    group_id: WebSpliceGroupId
    center_l_v_t: WebSpliceVector
    path_layers: tuple[str, str, str]
    stack_start_l_v_t: WebSpliceVector
    stack_end_l_v_t: WebSpliceVector
    shank_length: PhysicalQuantity
    head_location: str = "EXTERIOR_POSITIVE_T_PLATE_FACE"
    nut_location: str = "EXTERIOR_NEGATIVE_T_PLATE_FACE"
    washer_count: int = 2
    internal_hardware_count: int = 0


@dataclass(frozen=True, slots=True)
class WebSpliceMaterialRegion:
    component_id: str
    region_id: str
    lw_axis: tuple[Decimal, Decimal, Decimal]
    cw_axis: tuple[Decimal, Decimal, Decimal]
    tt_axis: tuple[Decimal, Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class WebSpliceBox:
    component_id: str
    role: str
    center_l_v_t: WebSpliceVector
    size_l_v_t: WebSpliceVector


@dataclass(frozen=True, slots=True)
class WebSpliceLayerDemand:
    group_id: WebSpliceGroupId
    layer_id: str
    fraction_of_interface_demand: Decimal
    signed_force_l_v_t: WebSpliceVector
    material_lw_component: PhysicalQuantity
    material_cw_component: PhysicalQuantity
    material_tt_component: PhysicalQuantity
    source_demand_fingerprint: str
    reverse_path_resolved_independently: bool


@dataclass(frozen=True, slots=True)
class WebSpliceGroupResult:
    group_id: WebSpliceGroupId
    centroid_l_v_t: WebSpliceVector
    wrench: WebSpliceWrench
    bolt_coordinates_l_v_t: tuple[WebSpliceVector, ...]
    demand: EccentricDemandResult
    layer_demands: tuple[WebSpliceLayerDemand, ...]
    group_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceSymmetryProof:
    identical_beams: bool
    identical_plates: bool
    mirrored_plate_placement: bool
    mirrored_group_geometry: bool
    paired_action_eligible: bool
    proof_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceVisualization:
    frame_axes: tuple[str, str, str]
    joint_reference_l_v_t: WebSpliceVector
    beam_end_planes_l: tuple[PhysicalQuantity, PhysicalQuantity]
    boxes: tuple[WebSpliceBox, ...]
    bolts: tuple[WebSpliceBolt, ...]
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    material_regions: tuple[WebSpliceMaterialRegion, ...]
    action_reference_l_v_t: WebSpliceVector
    applied_force_l_v_t: WebSpliceVector


@dataclass(frozen=True, slots=True)
class WebSplicePreviewResult:
    request_id: str
    orchestration_contract_version: str
    preview_schema_version: str
    connector_kind: str
    geometry_status: WebSpliceStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: WebSpliceStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    beam_a_group: WebSpliceGroupResult
    beam_b_group: WebSpliceGroupResult
    symmetry_proof: WebSpliceSymmetryProof
    plate_pair_system_fraction: Decimal
    limitations: tuple[str, ...]
    visualization: WebSpliceVisualization
    canonical_input_fingerprint: str
    connector_geometry_fingerprint: str
    engineering_fingerprint: str
    application_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceDesignResult:
    preview: WebSplicePreviewResult
    assembly_status: WebSpliceStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    supported_local_checks_executed: bool
    supported_local_failure_present: bool
    local_check_ids: tuple[str, ...]
    failed_local_check_ids: tuple[str, ...]
    local_resistance_warnings: tuple[str, ...]
    local_resistance_fingerprints: tuple[str, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceClearBodyPlan:
    left_inner_bolt_center: PhysicalQuantity
    right_inner_bolt_center: PhysicalQuantity
    left_clear_boundary: PhysicalQuantity
    right_clear_boundary: PhysicalQuantity
    clear_body_length: PhysicalQuantity
    critical_section_ids: tuple[str, str, str]
    exact_linear_envelope_proven: bool
    rational_method: str
    panel_model: str
    slice4_commit: str
    slice4_golden_sha256: str
    slice4_method_ids: tuple[str, str, str]
    physical_shear_plane_count: int
    bolt_source_authority_id: str
    bolt_source_authorized: bool
    engineering_review_required: bool
    qualification: str
    disclaimer_id: str
    disclaimer_text: str
    future_report_final_disclaimer_section: bool
    plan_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceRC2PreviewResult(WebSplicePreviewResult):
    clear_body_plan: WebSpliceClearBodyPlan


@dataclass(frozen=True, slots=True)
class WebSpliceRC2DesignResult(WebSpliceDesignResult):
    plate_body_interaction: WebSpliceBodyInteractionResult
    double_shear_results: tuple[WebSpliceDoubleShearResult, ...]
    double_shear_governing_bolt_id: str | None
    double_shear_governing_utilization: Decimal | None
    double_shear_status: DoubleShearStatus
    rational_method_engineering_review_required: bool
    connection_element_qualification: str
    disclaimer_id: str
    disclaimer_text: str
    future_report_final_disclaimer_section: bool


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {name: _canonical(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _q(value: Decimal | int | str, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> WebSpliceVector:
    return WebSpliceVector(*(_q(item, unit) for item in values))


def _neg(vector: WebSpliceVector) -> WebSpliceVector:
    return WebSpliceVector(
        *(
            PhysicalQuantity.of(-item.magnitude, item.unit)
            for item in (vector.l, vector.v, vector.t)
        )
    )


def _force(request: WebSpliceRequest) -> WebSpliceVector:
    force_unit = Unit.KIP if request.unit_system.value == "US_CUSTOMARY" else Unit.KN
    return WebSpliceVector(
        *(
            item.to(force_unit)
            for item in (
                request.transfer_force.axial,
                request.transfer_force.major_shear,
                request.transfer_force.minor_shear,
            )
        )
    )


def _zero_vector(unit: Unit) -> WebSpliceVector:
    return _vector((_ZERO, _ZERO, _ZERO), unit)


def _cross_offset_force(
    offset_l: Decimal, force: WebSpliceVector, moment_unit: Unit, length_unit: Unit
) -> WebSpliceVector:
    # r=(offset_l,0,0), F=(L,V,T): cross(r,F)=(0,-r*T,r*V)
    force_unit = force.l.unit
    factor = _q(1, force_unit).canonical_magnitude * _q(1, length_unit).canonical_magnitude
    target_factor = _q(1, moment_unit).canonical_magnitude
    with localcontext() as context:
        context.prec = 100
        scale = factor / target_factor
        return _vector(
            (_ZERO, -offset_l * force.t.magnitude * scale, offset_l * force.v.magnitude * scale),
            moment_unit,
        )


def _bolt_coordinates(
    request: WebSpliceRequest, group: WebSpliceGroupId
) -> tuple[WebSpliceVector, ...]:
    unit = request.source_length_unit
    layout = request.group
    center = (
        -layout.centroid_offset.to(unit).magnitude
        if group is WebSpliceGroupId.BEAM_A
        else layout.centroid_offset.to(unit).magnitude
    )
    line_start = (
        center
        - layout.longitudinal_gauge.to(unit).magnitude * Decimal(layout.bolts_per_row - 1) / 2
    )
    row_start = -layout.vertical_pitch.to(unit).magnitude * Decimal(layout.rows - 1) / 2
    return tuple(
        _vector(
            (
                line_start + Decimal(line) * layout.longitudinal_gauge.to(unit).magnitude,
                row_start + Decimal(row) * layout.vertical_pitch.to(unit).magnitude,
                _ZERO,
            ),
            unit,
        )
        for row in range(layout.rows)
        for line in range(layout.bolts_per_row)
    )


def _clear_body_plan(
    request: WebSpliceRequest,
    coords_a: tuple[WebSpliceVector, ...],
    coords_b: tuple[WebSpliceVector, ...],
) -> WebSpliceClearBodyPlan:
    unit = request.source_length_unit
    left_center = max(item.l.to(unit).magnitude for item in coords_a)
    right_center = min(item.l.to(unit).magnitude for item in coords_b)
    radius = request.hole_diameter.to(unit).magnitude / 2
    left_boundary = left_center + radius
    right_boundary = right_center - radius
    partial = WebSpliceClearBodyPlan(
        _q(left_center, unit),
        _q(right_center, unit),
        _q(left_boundary, unit),
        _q(right_boundary, unit),
        _q(right_boundary - left_boundary, unit),
        (
            "SECTION_A_CLEAR_BOUNDARY",
            "SECTION_JOINT",
            "SECTION_B_CLEAR_BOUNDARY",
        ),
        True,
        WEB_SPLICE_RATIONAL_METHOD,
        WEB_SPLICE_RATIONAL_PANEL_MODEL,
        WEB_SPLICE_SLICE4_COMMIT,
        WEB_SPLICE_SLICE4_GOLDEN_SHA256,
        (
            "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION",
            "ASCE74_EQ_7_15_7_17_LONGITUDINAL_PLATE_COMPRESSION",
            "ASCE74_EQ_7_24_7_25_IN_PLANE_SHEAR",
        ),
        2,
        "ASTM_F593_17_GROUP_2_316_316L",
        False,
        True,
        WEB_SPLICE_QUALIFICATION,
        WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
        WEB_SPLICE_RATIONAL_DISCLAIMER,
        True,
        "",
    )
    return replace(partial, plan_fingerprint=_fingerprint(partial))


def _demand(
    request: WebSpliceRequest,
    group: WebSpliceGroupId,
    force: WebSpliceVector,
    coordinates: tuple[WebSpliceVector, ...],
) -> EccentricDemandResult:
    unit = request.source_length_unit
    moment_unit = Unit.KIP_IN if request.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    center = (
        -request.group.centroid_offset.to(unit).magnitude
        if group is WebSpliceGroupId.BEAM_A
        else request.group.centroid_offset.to(unit).magnitude
    )
    del coordinates  # visualization coordinates share this request's exact mirrored layout
    geometry_force = WebSpliceVector(
        _q(0, force.l.unit),
        _q(
            force.v.magnitude
            if force.v.magnitude != 0
            else (-_ONE if group is WebSpliceGroupId.BEAM_A else _ONE),
            force.v.unit,
        ),
        _q(0, force.t.unit),
    )
    mapping_request = cast(
        MultiRowOrchestrationRequest,
        _layer_resistance_request(
            request,
            group,
            geometry_force,
            "POSITIVE_WEB_SPLICE_PLATE",
            analysis_envelope_only=True,
        ),
    )
    resolved = _resolve(mapping_request)
    bundle = _execution_bundle(mapping_request, resolved)
    magnitude = _q((force.l.magnitude**2 + force.v.magnitude**2).sqrt(), force.l.unit)
    demand_plan = plan_row_demands(
        resolved.geometry,
        magnitude,
        mapping_request.row_distribution_basis,
        mapping_request.provenance,
        connected_materials=(
            ConnectedMaterialPair.FRP_FRP
            if mapping_request.row_distribution_basis is RowDistributionBasis.ASCE_PRESCRIBED
            else None
        ),
    )
    zeros_m = ExactQuantityVector3D(*(_q(0, moment_unit) for _ in range(3)))
    return calculate_eccentric_bolt_group_demand(
        EccentricDemandInput(
            f"STAGE_3_6A_{group.value}_ACTION",
            f"{group.value}_BEAM_WEB",
            ExactQuantityVector3D(force.l, force.v, force.t),
            zeros_m,
            zeros_m,
            ExactQuantityVector3D(*(_q(0, unit) for _ in range(3))),
            ExactInterfaceFrame(
                group.value,
                ExactQuantityVector3D(_q(center, unit), _q(0, unit), _q(0, unit)),
                (_ZERO, _ONE, _ZERO),
                (_ONE, _ZERO, _ZERO),
                (_ZERO, _ZERO, -_ONE),
            ),
            bundle.physical_geometry,
            demand_plan,
            resolved.applicability.method_applicability,
            resolved.applicability.qualification,
            (
                "STAGE_2_5A_DEMAND_ANALYSIS",
                "STAGE_3_6A_DISTINCT_PHYSICAL_GROUP",
                f"SIGNED_GROUP:{group.value}",
            ),
        )
    )


def _geometry_reasons(
    request: WebSpliceRequest,
    groups: tuple[tuple[WebSpliceVector, ...], tuple[WebSpliceVector, ...]],
) -> tuple[str, ...]:
    unit = request.source_length_unit
    radius = request.hole_diameter.to(unit).magnitude / 2
    half_plate_l = request.splice_plate.length.to(unit).magnitude / 2
    half_plate_v = request.splice_plate.height.to(unit).magnitude / 2
    half_clear_web = (
        request.beam.depth.to(unit).magnitude - 2 * request.beam.flange_thickness.to(unit).magnitude
    ) / 2
    reasons: list[str] = []
    if request.splice_plate.height.to(unit).magnitude > 2 * half_clear_web:
        reasons.append("SPLICE_PLATE_FLANGE_POSITIVE_VOLUME_INTERFERENCE")
    for coordinates in groups:
        for item in coordinates:
            if abs(item.v.magnitude) + radius > half_clear_web:
                reasons.append("COMPLETE_HOLE_NOT_CONTAINED_IN_BEAM_WEB")
            if (
                abs(item.l.magnitude) + radius > half_plate_l
                or abs(item.v.magnitude) + radius > half_plate_v
            ):
                reasons.append("COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATE")
    return tuple(dict.fromkeys(reasons))


def _layers(
    group: WebSpliceGroupId, force: WebSpliceVector, demand: EccentricDemandResult, symmetry: str
) -> tuple[WebSpliceLayerDemand, ...]:
    beam = "BEAM_A_WEB" if group is WebSpliceGroupId.BEAM_A else "BEAM_B_WEB"
    independent = group is WebSpliceGroupId.BEAM_B

    def record(layer: str, fraction: Decimal) -> WebSpliceLayerDemand:
        scaled = WebSpliceVector(*(item * fraction for item in (force.l, force.v, force.t)))
        beam_b_web = group is WebSpliceGroupId.BEAM_B and layer == "BEAM_B_WEB"
        lw = PhysicalQuantity.of(
            -scaled.l.magnitude if beam_b_web else scaled.l.magnitude, scaled.l.unit
        )
        tt = PhysicalQuantity.of(
            -scaled.t.magnitude if beam_b_web else scaled.t.magnitude, scaled.t.unit
        )
        return WebSpliceLayerDemand(
            group, layer, fraction, scaled, lw, scaled.v, tt, demand.result_fingerprint, independent
        )

    return (
        record("POSITIVE_WEB_SPLICE_PLATE", _HALF),
        record(beam, _ONE),
        record("NEGATIVE_WEB_SPLICE_PLATE", _HALF),
    )


def _visualization(
    request: WebSpliceRequest,
    force: WebSpliceVector,
    coords_a: tuple[WebSpliceVector, ...],
    coords_b: tuple[WebSpliceVector, ...],
) -> WebSpliceVisualization:
    unit = request.source_length_unit
    gap = request.beam_end_gap.to(unit).magnitude
    beam_len = request.beam.display_length_each_side.to(unit).magnitude
    depth = request.beam.depth.to(unit).magnitude
    flange_width = request.beam.flange_width.to(unit).magnitude
    flange_t = request.beam.flange_thickness.to(unit).magnitude
    plate_l = request.splice_plate.length.to(unit).magnitude
    plate_v = request.splice_plate.height.to(unit).magnitude
    plate_t = request.splice_plate.thickness.to(unit).magnitude
    web_t = request.beam.web_thickness.to(unit).magnitude
    beam_a_l = -(gap + beam_len) / 2
    beam_b_l = (gap + beam_len) / 2
    flange_v = (depth - flange_t) / 2
    boxes = (
        WebSpliceBox(
            "BEAM_A_WEB",
            "FRP_WIDE_FLANGE_WEB",
            _vector((beam_a_l, _ZERO, _ZERO), unit),
            _vector((beam_len, depth - 2 * flange_t, web_t), unit),
        ),
        WebSpliceBox(
            "BEAM_A_TOP_FLANGE",
            "FRP_WIDE_FLANGE_TOP_FLANGE",
            _vector((beam_a_l, flange_v, _ZERO), unit),
            _vector((beam_len, flange_t, flange_width), unit),
        ),
        WebSpliceBox(
            "BEAM_A_BOTTOM_FLANGE",
            "FRP_WIDE_FLANGE_BOTTOM_FLANGE",
            _vector((beam_a_l, -flange_v, _ZERO), unit),
            _vector((beam_len, flange_t, flange_width), unit),
        ),
        WebSpliceBox(
            "BEAM_B_WEB",
            "FRP_WIDE_FLANGE_WEB",
            _vector((beam_b_l, _ZERO, _ZERO), unit),
            _vector((beam_len, depth - 2 * flange_t, web_t), unit),
        ),
        WebSpliceBox(
            "BEAM_B_TOP_FLANGE",
            "FRP_WIDE_FLANGE_TOP_FLANGE",
            _vector((beam_b_l, flange_v, _ZERO), unit),
            _vector((beam_len, flange_t, flange_width), unit),
        ),
        WebSpliceBox(
            "BEAM_B_BOTTOM_FLANGE",
            "FRP_WIDE_FLANGE_BOTTOM_FLANGE",
            _vector((beam_b_l, -flange_v, _ZERO), unit),
            _vector((beam_len, flange_t, flange_width), unit),
        ),
        WebSpliceBox(
            "POSITIVE_WEB_SPLICE_PLATE",
            "FRP_WEB_SPLICE_PLATE",
            _vector((_ZERO, _ZERO, (web_t + plate_t) / 2), unit),
            _vector((plate_l, plate_v, plate_t), unit),
        ),
        WebSpliceBox(
            "NEGATIVE_WEB_SPLICE_PLATE",
            "FRP_WEB_SPLICE_PLATE",
            _vector((_ZERO, _ZERO, -(web_t + plate_t) / 2), unit),
            _vector((plate_l, plate_v, plate_t), unit),
        ),
    )
    shank = _q(web_t + 2 * plate_t, unit)
    start_t, end_t = (web_t / 2 + plate_t), -(web_t / 2 + plate_t)
    bolts = tuple(
        WebSpliceBolt(
            f"{group.value}_B{index + 1}",
            group,
            center,
            (
                "POSITIVE_WEB_SPLICE_PLATE",
                "BEAM_A_WEB" if group is WebSpliceGroupId.BEAM_A else "BEAM_B_WEB",
                "NEGATIVE_WEB_SPLICE_PLATE",
            ),
            _vector((center.l.magnitude, center.v.magnitude, start_t), unit),
            _vector((center.l.magnitude, center.v.magnitude, end_t), unit),
            shank,
        )
        for group, coords in (
            (WebSpliceGroupId.BEAM_A, coords_a),
            (WebSpliceGroupId.BEAM_B, coords_b),
        )
        for index, center in enumerate(coords)
    )
    regions = (
        WebSpliceMaterialRegion(
            "BEAM_A", "BEAM_A_WEB", (_ONE, _ZERO, _ZERO), (_ZERO, _ONE, _ZERO), (_ZERO, _ZERO, _ONE)
        ),
        WebSpliceMaterialRegion(
            "BEAM_A",
            "BEAM_A_TOP_FLANGE",
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, _ONE),
            (_ZERO, -_ONE, _ZERO),
        ),
        WebSpliceMaterialRegion(
            "BEAM_A",
            "BEAM_A_BOTTOM_FLANGE",
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, -_ONE),
            (_ZERO, _ONE, _ZERO),
        ),
        WebSpliceMaterialRegion(
            "BEAM_B",
            "BEAM_B_WEB",
            (-_ONE, _ZERO, _ZERO),
            (_ZERO, _ONE, _ZERO),
            (_ZERO, _ZERO, -_ONE),
        ),
        WebSpliceMaterialRegion(
            "BEAM_B",
            "BEAM_B_TOP_FLANGE",
            (-_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, -_ONE),
            (_ZERO, -_ONE, _ZERO),
        ),
        WebSpliceMaterialRegion(
            "BEAM_B",
            "BEAM_B_BOTTOM_FLANGE",
            (-_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, _ONE),
            (_ZERO, _ONE, _ZERO),
        ),
        WebSpliceMaterialRegion(
            "POSITIVE_WEB_SPLICE_PLATE",
            "POSITIVE_WEB_SPLICE_PLATE",
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ONE, _ZERO),
            (_ZERO, _ZERO, _ONE),
        ),
        WebSpliceMaterialRegion(
            "NEGATIVE_WEB_SPLICE_PLATE",
            "NEGATIVE_WEB_SPLICE_PLATE",
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ONE, _ZERO),
            (_ZERO, _ZERO, _ONE),
        ),
    )
    return WebSpliceVisualization(
        ("L_S", "V_S", "T_S"),
        _zero_vector(unit),
        (_q(-gap / 2, unit), _q(gap / 2, unit)),
        boxes,
        bolts,
        request.bolt_diameter.to(unit),
        request.hole_diameter.to(unit),
        regions,
        _zero_vector(unit),
        force,
    )


def preview_web_splice(request: WebSpliceRequest) -> WebSplicePreviewResult:
    if not isinstance(request, WebSpliceRequest):
        raise TypeError("request must be WebSpliceRequest.")
    force_a = _force(request)
    force_b = _neg(force_a)
    unit = request.source_length_unit
    moment_unit = Unit.KIP_IN if request.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    coords_a = _bolt_coordinates(request, WebSpliceGroupId.BEAM_A)
    coords_b = _bolt_coordinates(request, WebSpliceGroupId.BEAM_B)
    clear_body_plan = _clear_body_plan(request, coords_a, coords_b)
    reasons = _geometry_reasons(request, (coords_a, coords_b))
    if (
        request.orchestration_contract_version == WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION
        and clear_body_plan.clear_body_length.canonical_magnitude <= 0
    ):
        reasons = (*reasons, "WEB_SPLICE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS")
    demand_a = _demand(request, WebSpliceGroupId.BEAM_A, force_a, coords_a)
    demand_b = _demand(request, WebSpliceGroupId.BEAM_B, force_b, coords_b)
    symmetry_payload = (
        request.beam.depth,
        request.beam.flange_width,
        request.beam.web_thickness,
        request.splice_plate,
        request.group,
    )
    symmetry_fp = _fingerprint(symmetry_payload)
    symmetry = WebSpliceSymmetryProof(True, True, True, True, True, symmetry_fp)

    def group_result(
        group: WebSpliceGroupId,
        force: WebSpliceVector,
        coords: tuple[WebSpliceVector, ...],
        demand: EccentricDemandResult,
    ) -> WebSpliceGroupResult:
        center = (
            -request.group.centroid_offset.to(unit).magnitude
            if group is WebSpliceGroupId.BEAM_A
            else request.group.centroid_offset.to(unit).magnitude
        )
        reference = _vector((center, _ZERO, _ZERO), unit)
        moment = _cross_offset_force(-center, force, moment_unit, unit)
        wrench = WebSpliceWrench(
            reference,
            force,
            moment,
            "M_GROUP=cross(r_J-r_GROUP,F_INTERFACE); user moment=0",
        )
        layers = _layers(group, force, demand, symmetry_fp)
        return WebSpliceGroupResult(
            group,
            reference,
            wrench,
            coords,
            demand,
            layers,
            _fingerprint((group, reference, wrench, demand.result_fingerprint, layers)),
        )

    group_a = group_result(WebSpliceGroupId.BEAM_A, force_a, coords_a, demand_a)
    group_b = group_result(WebSpliceGroupId.BEAM_B, force_b, coords_b, demand_b)
    geometry_status = WebSpliceStatus.INVALID_GEOMETRY if reasons else WebSpliceStatus.VALID
    # VALID is a geometry-only transport state; the assembly remains NOT_EVALUATED.
    geometry_payload = (
        request.beam.depth,
        request.beam.flange_width,
        request.beam.web_thickness,
        request.beam.flange_thickness,
        request.beam_end_gap,
        request.splice_plate,
        request.group,
        request.bolt_diameter,
        request.hole_diameter,
    )
    input_payload = (
        request.orchestration_contract_version,
        geometry_payload,
        request.transfer_force,
    )
    geometry_fp = _fingerprint(geometry_payload)
    engineering_fp = _fingerprint(input_payload)
    visualization = _visualization(request, force_a, coords_a, coords_b)
    historical = WebSplicePreviewResult(
        request.request_id,
        request.orchestration_contract_version,
        WEB_SPLICE_PREVIEW_SCHEMA_VERSION,
        "SYMMETRIC_DOUBLE_WEB_SPLICE_PLATES",
        geometry_status,
        reasons,
        WebSpliceStatus.INVALID_GEOMETRY if reasons else WebSpliceStatus.NOT_EVALUATED,
        False,
        False,
        not reasons
        and demand_a.availability is DemandAnalysisAvailability.CALCULATED
        and demand_b.availability is DemandAnalysisAvailability.CALCULATED,
        group_a,
        group_b,
        symmetry,
        _ONE,
        (
            WEB_SPLICE_RC2_LIMITATIONS
            if request.orchestration_contract_version == WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION
            else WEB_SPLICE_API_LIMITATIONS
        )
        + (
            ("WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE",)
            if force_a.t.canonical_magnitude != 0
            else ()
        ),
        visualization,
        _fingerprint(input_payload),
        geometry_fp,
        engineering_fp,
        _fingerprint((engineering_fp, group_a.group_fingerprint, group_b.group_fingerprint)),
    )
    if request.orchestration_contract_version == WEB_SPLICE_CONTRACT_VERSION:
        return historical
    successor_base = replace(
        historical,
        preview_schema_version=WEB_SPLICE_RC2_PREVIEW_SCHEMA_VERSION,
    )
    return WebSpliceRC2PreviewResult(
        request_id=successor_base.request_id,
        orchestration_contract_version=successor_base.orchestration_contract_version,
        preview_schema_version=successor_base.preview_schema_version,
        connector_kind=successor_base.connector_kind,
        geometry_status=successor_base.geometry_status,
        geometry_invalid_reasons=successor_base.geometry_invalid_reasons,
        assembly_status=successor_base.assembly_status,
        ordinary_pass_allowed=successor_base.ordinary_pass_allowed,
        resistance_evaluated=successor_base.resistance_evaluated,
        design_check_ready=successor_base.design_check_ready,
        beam_a_group=successor_base.beam_a_group,
        beam_b_group=successor_base.beam_b_group,
        symmetry_proof=successor_base.symmetry_proof,
        plate_pair_system_fraction=successor_base.plate_pair_system_fraction,
        limitations=successor_base.limitations,
        visualization=successor_base.visualization,
        canonical_input_fingerprint=successor_base.canonical_input_fingerprint,
        connector_geometry_fingerprint=successor_base.connector_geometry_fingerprint,
        engineering_fingerprint=successor_base.engineering_fingerprint,
        application_fingerprint=_fingerprint(
            (
                engineering_fp,
                group_a.group_fingerprint,
                group_b.group_fingerprint,
                clear_body_plan,
            )
        ),
        clear_body_plan=clear_body_plan,
    )


def _layer_resistance_request(
    request: WebSpliceRequest,
    group: WebSpliceGroupId,
    force: WebSpliceVector,
    layer_id: str,
    *,
    analysis_envelope_only: bool = False,
) -> MultiRowOrchestrationRequest | None:
    """Map one physical FRP layer into the accepted Stage 2 resistance contract.

    The accepted multi-row contract resolves rows along its local ``u`` axis.  Stage 3.6A
    binds that axis to ``V_S`` and its ``v`` axis to ``L_S``; this keeps the physical
    row/bolt-line identities and each layer's material basis authoritative in the backend.
    """

    force_u = force.v
    force_v = force.l
    if force_u.canonical_magnitude == 0 and force_v.canonical_magnitude == 0:
        return None
    unit = request.source_length_unit
    row_span = request.group.vertical_pitch.to(unit).magnitude * Decimal(request.group.rows - 1)
    line_span = request.group.longitudinal_gauge.to(unit).magnitude * Decimal(
        request.group.bolts_per_row - 1
    )
    center = (
        -request.group.centroid_offset.to(unit).magnitude
        if group is WebSpliceGroupId.BEAM_A
        else request.group.centroid_offset.to(unit).magnitude
    )
    is_plate = "SPLICE_PLATE" in layer_id
    if is_plate:
        row_half_extent = request.splice_plate.height.to(unit).magnitude / 2
        line_half_extent = request.splice_plate.length.to(unit).magnitude / 2
        negative_side = center + line_half_extent - line_span / 2
        positive_side = line_half_extent - center - line_span / 2
        thickness = request.splice_plate.thickness
        classification = PultrudedElementClassification.PLATE
        component_id = layer_id
    else:
        row_half_extent = (
            request.beam.depth.to(unit).magnitude
            - 2 * request.beam.flange_thickness.to(unit).magnitude
        ) / 2
        # The opposite beam extent is intentionally not inferred from the presentation-only
        # display length.  Only pin bearing is accepted from this one-layer handoff below;
        # end-path checks remain NOT_EVALUATED for the semi-infinite web side.
        unresolved_side = request.bolt_diameter.to(unit).magnitude * 3
        joint_plane = (
            -request.beam_end_gap.to(unit).magnitude / 2
            if group is WebSpliceGroupId.BEAM_A
            else request.beam_end_gap.to(unit).magnitude / 2
        )
        joint_side = abs(joint_plane - center) - line_span / 2
        if group is WebSpliceGroupId.BEAM_A:
            negative_side, positive_side = unresolved_side, joint_side
        else:
            negative_side, positive_side = joint_side, unresolved_side
        thickness = request.beam.web_thickness
        classification = PultrudedElementClassification.SHAPE
        component_id = layer_id
    row_edge = row_half_extent - row_span / 2
    if analysis_envelope_only:
        # Stage 2.5A needs a finite analysis envelope even when the separately reported
        # physical layer containment is invalid.  This does not alter or qualify the
        # physical web/plate geometry and is never used for a resistance handoff.
        analysis_clearance = request.bolt_diameter.to(unit).magnitude * 3
        row_edge = max(row_edge, analysis_clearance)
        negative_side = max(negative_side, analysis_clearance)
        positive_side = max(positive_side, analysis_clearance)
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_3_6A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:{group.value}:{layer_id}",
        f"stage-3.6a:{group.value}:{layer_id}",
        group.value,
        f"STAGE_3_6A_{group.value}_ACTION",
        "Stage 3.6A independently resolved physical Plate/Web/Plate layer demand",
        request.unit_system,
        unit,
        request.group.rows,
        request.group.bolts_per_row,
        request.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        request.group.vertical_pitch,
        request.group.longitudinal_gauge,
        _q(row_edge, unit),
        _q(row_edge, unit),
        _q(negative_side, unit),
        _q(positive_side, unit),
        _q("0.000000001", unit),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                layer_id,
                component_id,
                "ICE_LOCKED_PULTRUDED_FRP",
                thickness,
                classification,
                Decimal(90),
                factors,
                ThreadStatus.EXCLUDED,
            ),
        ),
        force_u,
        force_v,
        "STAGE_3_6A_INTERFACE_LOCAL_VS_LS_TRANSFORM",
        (
            RowDistributionBasis.ASCE_PRESCRIBED
            if request.group.rows in {2, 3}
            else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE
        ),
        None,
        (),
        MethodProvenance(
            "STAGE_3_6A_STAGE_2_5A_RESOLVED_DEMAND",
            "STAGE_3_6A_SYMMETRIC_DOUBLE_WEB_SPLICE_ENGINEERING_SPECIFICATION_RC1",
            "RC1",
            request.request_id,
            group.value,
            True,
            True,
        ),
        False,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.DOUBLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        None,
        _q(0, unit),
        _q("0.000000001", unit),
        demand_source=MultiRowDemandSource.EXPLICIT_RESOLVED_CONNECTION_DEMAND,
        single_row_geometry_preview_authorized=request.group.rows == 1,
    )


def _evaluate_supported_local_resistance(
    request: WebSpliceRequest,
    preview: WebSplicePreviewResult,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Execute accepted local FRP checks without promoting unsupported splice claims."""

    standard_hole = create_standard_hole(
        request.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    ).hole_diameter
    if standard_hole.canonical_magnitude != request.hole_diameter.canonical_magnitude:
        return (
            (),
            (),
            ("LOCAL_RESISTANCE_STANDARD_HOLE_MAPPING_NOT_AVAILABLE",),
            (),
        )
    check_ids: list[str] = []
    failed_ids: list[str] = []
    warnings: list[str] = []
    fingerprints: list[str] = []
    for group_result in (preview.beam_a_group, preview.beam_b_group):
        for layer in group_result.layer_demands:
            local_request = _layer_resistance_request(
                request,
                group_result.group_id,
                group_result.wrench.force_l_v_t,
                layer.layer_id,
            )
            if local_request is None:
                warnings.append(f"LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE:{layer.layer_id}")
                continue
            allocations = tuple(
                LayerInPlaneDemandAllocation(
                    bolt.bolt_id,
                    layer.layer_id,
                    layer.fraction_of_interface_demand,
                    "STAGE_3_6A_EXACT_SYMMETRIC_LAYER_ALLOCATION",
                    group_result.demand.result_fingerprint,
                )
                for bolt in group_result.demand.bolts
            )
            try:
                response = evaluate_multirow_connection_with_resolved_demand(
                    local_request,
                    group_result.demand,
                    allocations,
                )
            except ValueError as error:
                warnings.append(f"LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE:{layer.layer_id}:{error}")
                continue
            accepted_families = (
                {MultiRowCheckFamily.PIN_BEARING}
                if layer.layer_id in {"BEAM_A_WEB", "BEAM_B_WEB"}
                else _SUPPORTED_LOCAL_FRP_FAMILIES
            )
            for handoff in response.automatic_handoff_results:
                fingerprints.append(handoff.result_fingerprint)
                for item in handoff.checks:
                    if item.family not in accepted_families:
                        continue
                    if item.resistance_result is None:
                        continue
                    check_id = f"{group_result.group_id.value}:{layer.layer_id}:{item.check_id}"
                    check_ids.append(check_id)
                    if item.resistance_result.numerical_comparison.value == "FAIL":
                        failed_ids.append(check_id)
            if layer.layer_id in {"BEAM_A_WEB", "BEAM_B_WEB"}:
                warnings.append(
                    f"{layer.layer_id}:REVERSE_OR_REMOTE_EDGE_PATHS_NOT_EVALUATED_IN_RC1"
                )
    return (
        tuple(dict.fromkeys(check_ids)),
        tuple(dict.fromkeys(failed_ids)),
        tuple(dict.fromkeys(warnings)),
        tuple(dict.fromkeys(fingerprints)),
    )


def _body_actions(
    request: WebSpliceRequest,
    preview: WebSpliceRC2PreviewResult,
) -> tuple[WebSpliceCriticalSectionAction, ...]:
    plan = preview.clear_body_plan
    force = preview.beam_a_group.wrench.force_l_v_t
    length_unit = request.source_length_unit
    moment_unit = Unit.KIP_IN if request.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    force_unit = Unit.KIP if request.unit_system.value == "US_CUSTOMARY" else Unit.KN
    sections = (
        (plan.critical_section_ids[0], plan.left_clear_boundary),
        (plan.critical_section_ids[1], _q(0, length_unit)),
        (plan.critical_section_ids[2], plan.right_clear_boundary),
    )
    return tuple(
        WebSpliceCriticalSectionAction(
            section_id,
            coordinate,
            force.l.to(force_unit),
            force.v.to(force_unit),
            _q(
                coordinate.to(length_unit).magnitude * force.v.to(force_unit).magnitude,
                moment_unit,
            ),
        )
        for section_id, coordinate in sections
    )


def _adjusted_ice_property(
    kind: FRPPropertyKind,
    factors: EndUseFactors,
    owner_id: str = "POSITIVE_WEB_SPLICE_PLATE",
) -> EndUsePropertyTrace:
    from frp_master_connection.application.mat1_scope import material_for_owner

    material = material_for_owner(owner_id, create_locked_ice_material_snapshot())
    entry = material.lookup(kind)
    if entry is None:  # pragma: no cover - RC2 calls only declared ICE properties
        raise ValueError(f"Controlled ICE material lacks required property {kind.value}.")
    return adjusted_property_trace(entry, factors)


def _evaluate_body_interaction(
    request: WebSpliceRequest,
    preview: WebSpliceRC2PreviewResult,
) -> WebSpliceBodyInteractionResult:
    from frp_master_connection.application.mat1_scope import current_scope

    scope = current_scope()
    if scope is not None and scope.material("POSITIVE_WEB_SPLICE_PLATE") != scope.material(
        "NEGATIVE_WEB_SPLICE_PLATE"
    ):
        raise ValueError("MAT1_SYMMETRIC_WEB_SPLICE_PLATE_MATERIALS_MUST_MATCH")
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_3_6A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    from frp_master_connection.application.mat1_scope import time_category_for_case

    time_effect = select_time_effect_factor(
        time_category_for_case(TimeEffectCategory.WIND_TORNADO_SEISMIC)
    )
    thickness = request.splice_plate.thickness
    height = request.splice_plate.height
    length = preview.clear_body_plan.clear_body_length
    tension = plate_longitudinal_tension_strength(
        thickness,
        _adjusted_ice_property(FRPPropertyKind.FT_L, factors),
        time_effect,
    )
    compression = plate_longitudinal_compression_strength(
        thickness,
        height,
        _adjusted_ice_property(FRPPropertyKind.FC_L, factors),
        _adjusted_ice_property(FRPPropertyKind.ET_L, factors),
        _adjusted_ice_property(FRPPropertyKind.ET_T, factors),
        _adjusted_ice_property(FRPPropertyKind.G_LT, factors),
        _adjusted_ice_property(FRPPropertyKind.NU_LT, factors),
        time_effect,
        longitudinal_span=length,
    )
    shear = plate_in_plane_shear_strength(
        thickness,
        height,
        _adjusted_ice_property(FRPPropertyKind.FSH_LT, factors),
        _adjusted_ice_property(FRPPropertyKind.ET_L, factors),
        _adjusted_ice_property(FRPPropertyKind.ET_T, factors),
        _adjusted_ice_property(FRPPropertyKind.G_LT, factors),
        _adjusted_ice_property(FRPPropertyKind.NU_LT, factors),
        time_effect,
        longitudinal_span=length,
    )
    return evaluate_rational_body_interaction(
        plate_height=height,
        plate_thickness=thickness,
        actions=_body_actions(request, preview),
        symmetry_proven=preview.symmetry_proof.paired_action_eligible,
        tension_strength=tension,
        compression_strength=compression,
        shear_strength=shear,
    )


def _evaluate_double_shear(
    request: WebSpliceRequest,
    preview: WebSpliceRC2PreviewResult,
) -> tuple[WebSpliceDoubleShearResult, ...]:
    records: list[WebSpliceDoubleShearResult] = []
    for group in (preview.beam_a_group, preview.beam_b_group):
        demands: dict[str, PhysicalQuantity] = {}
        for scenario in group.demand.scenarios:
            for item in scenario.per_bolt:
                previous = demands.get(item.bolt_id)
                if previous is None or item.total_force_magnitude > previous:
                    demands[item.bolt_id] = item.total_force_magnitude
        displays = tuple(
            item for item in preview.visualization.bolts if item.group_id is group.group_id
        )
        for demand_id, display in zip(sorted(demands), displays, strict=True):
            records.append(
                evaluate_double_shear_bolt(
                    group_id=group.group_id.value,
                    bolt_id=display.bolt_id,
                    physical_path=display.path_layers,
                    physical_in_plane_demand=demands[demand_id],
                    symmetry_proven=preview.symmetry_proof.paired_action_eligible,
                    plate_fraction=_HALF,
                    diameter=request.bolt_diameter,
                    thread_condition=ThreadStatus.EXCLUDED.value,
                    source_authority_id="ASTM_F593_17_GROUP_2_316_316L",
                    nominal_shear_stress=None,
                )
            )
    return tuple(records)


def design_check_web_splice(request: WebSpliceRequest) -> WebSpliceDesignResult:
    preview = preview_web_splice(request)
    checks, failures, warnings, fingerprints = (
        ((), (), (), ())
        if preview.geometry_invalid_reasons
        else _evaluate_supported_local_resistance(request, preview)
    )
    failure = bool(failures)
    status = (
        WebSpliceStatus.INVALID_GEOMETRY
        if preview.geometry_invalid_reasons
        else WebSpliceStatus.FAIL
        if failure
        else WebSpliceStatus.NOT_EVALUATED
    )
    historical = WebSpliceDesignResult(
        preview,
        status,
        "FAIL" if failure else "NOT_EVALUATED",
        False,
        bool(checks),
        failure,
        checks,
        failures,
        warnings,
        fingerprints,
        _fingerprint(
            (
                preview.application_fingerprint,
                status,
                checks,
                failures,
                warnings,
                fingerprints,
            )
        ),
    )
    if request.orchestration_contract_version == WEB_SPLICE_CONTRACT_VERSION:
        return historical

    if not isinstance(preview, WebSpliceRC2PreviewResult):  # pragma: no cover - version invariant
        raise TypeError("Stage 3.6B requires the RC2 preview contract.")
    body = (
        evaluate_rational_body_interaction(
            plate_height=request.splice_plate.height,
            plate_thickness=request.splice_plate.thickness,
            actions=(),
            symmetry_proven=False,
        )
        if preview.geometry_invalid_reasons
        else _evaluate_body_interaction(request, preview)
    )
    double_shear = (
        () if preview.geometry_invalid_reasons else _evaluate_double_shear(request, preview)
    )
    numerical_double = tuple(item for item in double_shear if item.utilization is not None)
    governing_double = (
        None
        if not numerical_double
        else max(numerical_double, key=lambda item: cast(Decimal, item.utilization))
    )
    double_status = (
        DoubleShearStatus.FAIL
        if any(item.status is DoubleShearStatus.FAIL for item in double_shear)
        else DoubleShearStatus.PASS
        if double_shear and all(item.status is DoubleShearStatus.PASS for item in double_shear)
        else DoubleShearStatus.NOT_EVALUATED
    )
    rc2_failure = (
        failure
        or body.status is RationalBodyStatus.FAIL_RATIONAL_METHOD
        or double_status is DoubleShearStatus.FAIL
    )
    minor_response_required = request.transfer_force.minor_shear.canonical_magnitude != 0
    rc2_status = (
        WebSpliceStatus.INVALID_GEOMETRY
        if preview.geometry_invalid_reasons
        else WebSpliceStatus.FAIL
        if rc2_failure
        else WebSpliceStatus.NOT_EVALUATED
        if body.status is RationalBodyStatus.NOT_EVALUATED
        or double_status is DoubleShearStatus.NOT_EVALUATED
        or minor_response_required
        else WebSpliceStatus.PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED
    )
    required_status = (
        "FAIL"
        if rc2_status is WebSpliceStatus.FAIL
        else "NOT_EVALUATED"
        if rc2_status in {WebSpliceStatus.NOT_EVALUATED, WebSpliceStatus.INVALID_GEOMETRY}
        else "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"
    )
    successor_payload = (
        preview.application_fingerprint,
        rc2_status,
        checks,
        failures,
        warnings,
        fingerprints,
        body.result_fingerprint,
        tuple(item.result_fingerprint for item in double_shear),
        WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
        WEB_SPLICE_QUALIFICATION,
    )
    return WebSpliceRC2DesignResult(
        preview,
        rc2_status,
        required_status,
        False,
        bool(checks),
        failure,
        checks,
        failures,
        warnings,
        fingerprints,
        _fingerprint(successor_payload),
        body,
        double_shear,
        None if governing_double is None else governing_double.bolt_id,
        None if governing_double is None else governing_double.utilization,
        double_status,
        body.engineering_review_required,
        WEB_SPLICE_QUALIFICATION,
        WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
        WEB_SPLICE_RATIONAL_DISCLAIMER,
        True,
    )


__all__ = (
    "WEB_SPLICE_API_LIMITATIONS",
    "WEB_SPLICE_PREVIEW_SCHEMA_VERSION",
    "WebSpliceDesignResult",
    "WebSplicePreviewResult",
    "WebSpliceRC2DesignResult",
    "WebSpliceRC2PreviewResult",
    "design_check_web_splice",
    "preview_web_splice",
)
