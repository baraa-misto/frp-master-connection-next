"""Backend-authoritative Stage 4.1B Channel major-axis moment-splice orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, localcontext
from enum import Enum
from typing import cast

from frp_master_connection.application.mat1_scope import (
    material_for_owner,
    time_category_for_case,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowDemandSource,
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.application.web_splice_orchestration import (
    WebSpliceBox,
    WebSpliceMaterialRegion,
    WebSpliceVector,
    _adjusted_ice_property,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    EndUseFactors,
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
    calculate_channel_moment_component_resultants,
    calculate_eccentric_bolt_group_demand,
    canonical_decimal_string,
    evaluate_rational_body_interaction,
    plan_row_demands,
    plate_in_plane_shear_strength,
    plate_longitudinal_compression_strength,
    plate_longitudinal_tension_strength,
    select_time_effect_factor,
)
from frp_master_connection.calculation.channel_moment_resultants import (
    ChannelMomentActionInput,
    ChannelMomentCalculationInput,
    ChannelMomentComponentResultants,
    ChannelMomentRegionId,
    ChannelMomentSectionInput,
    ChannelShearCenterInput,
    ChannelShearCenterMethod,
)
from frp_master_connection.calculation.channel_moment_splice_resistance import (
    CHANNEL_MOMENT_SPLICE_DISCLAIMER,
    CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
    CHANNEL_MOMENT_SPLICE_QUALIFICATION,
    CHANNEL_WEB_SUBLAYER_METHOD,
    AsymmetricBoltStatus,
    AsymmetricTwoPlaneBoltResult,
    ChannelWebFaceDecomposition,
    FlangeBodyStatus,
    FlangeBranchDecomposition,
    FlangePlaneDemand,
    FlangePlateBodyResult,
    decompose_channel_web_wrench,
    decompose_flange_wrench,
    evaluate_channel_two_plane_bolt,
)
from frp_master_connection.calculation.eccentric_demand import (
    DemandAnalysisAvailability,
    EccentricDemandInput,
    EccentricDemandResult,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
)
from frp_master_connection.calculation.mat1_flange_body import (
    evaluate_material_flange_plate_body as evaluate_flange_plate_body,
)
from frp_master_connection.calculation.multirow import MethodProvenance, RowDistributionBasis
from frp_master_connection.calculation.properties import create_locked_ice_material_snapshot
from frp_master_connection.domain.channel_moment_splice import (
    CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION,
    CHANNEL_MOMENT_SPLICE_PRODUCT_ID,
    ChannelMomentSpliceFastener,
    ChannelMomentSpliceRequest,
    ChannelMomentSpliceStatus,
)

CHANNEL_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION = "4.1B-PREVIEW-RC1"
CHANNEL_MOMENT_SPLICE_RESULT_SCHEMA_VERSION = "4.1B-RESULT-RC1"
CHANNEL_MOMENT_SPLICE_CONTROLLED_HASHES = (
    ("decision", "3DD77B42FDB3A9799B7C1E380AA2116F6CC1DBBFABCEE9BBF7E9DFB295C0E83E"),
    (
        "engineering_specification_rc1",
        "3207CAB2F90FE6E3494BEE89297E16D53AE29F67DF6A1FD0D6371408B7C574AF",
    ),
    ("golden_benchmarks_rc1", "ED636AE37A062768EC3A45D4ED234B9363D0CDD8A49DCCCEA02543ADC50D123A"),
    ("authority_ledger_rc1", "144A7A86759422CCD88BE7A36FF3483843801A243C9DBFDFF751CE2D8177B519"),
    ("codex_order", "1AF9E327C74A5866FD3F11CD2E719D24AF2979B6A3406276B8BD63EEFB7131C8"),
    ("ASCE_SEI_74_23", "A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC"),
    (
        "ERRATUM_1_EFFECTIVE_2026_01_13",
        "5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550",
    ),
)

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)
_LOCAL_FAMILIES = frozenset(
    {
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    }
)


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceBolt:
    bolt_id: str
    group_id: str
    center_l_v_t: WebSpliceVector
    path_layers: tuple[str, str, str]
    stack_start_l_v_t: WebSpliceVector
    stack_end_l_v_t: WebSpliceVector
    shank_length: PhysicalQuantity
    head_location: str
    nut_location: str
    washer_count: int = 2
    internal_hardware_count: int = 0


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceVisualization:
    frame_axes: tuple[str, str, str]
    joint_reference_l_v_t: WebSpliceVector
    channel_centroid_l_v_t: WebSpliceVector
    channel_shear_center_l_v_t: WebSpliceVector
    beam_end_planes_l: tuple[PhysicalQuantity, PhysicalQuantity]
    boxes: tuple[WebSpliceBox, ...]
    bolts: tuple[ChannelMomentSpliceBolt, ...]
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    flange_bolt_diameter: PhysicalQuantity
    flange_hole_diameter: PhysicalQuantity
    material_regions: tuple[WebSpliceMaterialRegion, ...]
    action_reference_l_v_t: WebSpliceVector
    applied_force_l_v_t: WebSpliceVector
    applied_moment_l_v_t: WebSpliceVector
    generated_centroidal_torsion: PhysicalQuantity
    xray_inner_components: bool


@dataclass(frozen=True, slots=True)
class ChannelGroupDemand:
    group_id: str
    beam_id: str
    component_id: str
    branch_id: str
    physical_coordinates_first_second: tuple[tuple[PhysicalQuantity, PhysicalQuantity], ...]
    demand: EccentricDemandResult | None
    per_bolt_plane_demands: tuple[FlangePlaneDemand, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class ChannelLocalCheckSummary:
    component_id: str
    required_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    result_fingerprints: tuple[str, ...]
    not_required_zero_force: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceEquilibrium:
    slice6_six_component_exact: bool
    top_flange_exact: bool
    web_face_exact: bool
    bottom_flange_exact: bool
    whole_connection_six_component_exact: bool
    beam_a_b_equal_opposite_complete_wrenches: bool
    axial_residual: PhysicalQuantity
    major_shear_residual: PhysicalQuantity
    major_moment_residual: PhysicalQuantity
    transverse_moment_residual: PhysicalQuantity
    torsion_residual: PhysicalQuantity
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class ChannelMomentSplicePreviewResult:
    request_id: str
    product_id: str
    contract_version: str
    preview_schema_version: str
    geometry_status: ChannelMomentSpliceStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: ChannelMomentSpliceStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    slice6_result: ChannelMomentComponentResultants
    top_flange: FlangeBranchDecomposition
    web_faces: ChannelWebFaceDecomposition
    bottom_flange: FlangeBranchDecomposition
    web_group_demands: tuple[ChannelGroupDemand, ...]
    flange_group_demands: tuple[ChannelGroupDemand, ...]
    web_clear_body_length: PhysicalQuantity
    flange_clear_body_length: PhysicalQuantity
    rational_web_face_sublayer_thickness: PhysicalQuantity
    rational_flange_face_sublayer_thickness: PhysicalQuantity
    equilibrium: ChannelMomentSpliceEquilibrium
    visualization: ChannelMomentSpliceVisualization
    rational_method_engineering_review_required: bool
    connection_element_qualification: str
    moment_connection_stiffness_classification: str
    moment_rotation_capacity: str
    full_strength_classification: str
    warping_connection_response: str
    disclaimer_id: str
    disclaimer_text: str
    limitations: tuple[str, ...]
    controlled_artifact_hashes: tuple[tuple[str, str], ...]
    canonical_input_fingerprint: str
    geometry_fingerprint: str
    engineering_fingerprint: str
    application_fingerprint: str


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceDesignResult:
    preview: ChannelMomentSplicePreviewResult
    assembly_status: ChannelMomentSpliceStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    local_checks: tuple[ChannelLocalCheckSummary, ...]
    flange_plate_bodies: tuple[FlangePlateBodyResult, ...]
    web_plate_bodies: tuple[WebSpliceBodyInteractionResult, ...]
    flange_bolts: tuple[AsymmetricTwoPlaneBoltResult, ...]
    web_bolts: tuple[AsymmetricTwoPlaneBoltResult, ...]
    failed_check_ids: tuple[str, ...]
    unavailable_check_ids: tuple[str, ...]
    governing_utilization: Decimal | None
    governing_check_id: str | None
    disclaimer_id: str
    disclaimer_text: str
    rational_method_engineering_review_required: bool
    result_fingerprint: str


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {name: _canonical(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _q(value: Decimal | int | str, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> WebSpliceVector:
    return WebSpliceVector(*(_q(value, unit) for value in values))


def _zero_vector(unit: Unit) -> WebSpliceVector:
    return _vector((_ZERO, _ZERO, _ZERO), unit)


def _signed(value: PhysicalQuantity, sign: Decimal) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = 100
        return PhysicalQuantity.of(value.magnitude * sign, value.unit)


def _slice6(request: ChannelMomentSpliceRequest) -> ChannelMomentComponentResultants:
    return calculate_channel_moment_component_resultants(
        ChannelMomentCalculationInput(
            ChannelMomentSectionInput(
                request.beam.depth,
                request.beam.flange_width,
                request.beam.web_thickness,
                request.beam.flange_thickness,
            ),
            ChannelMomentActionInput(
                request.actions.axial_force_l,
                request.actions.major_shear_v,
                request.actions.major_moment_t,
                request.actions.minor_shear_t,
                request.actions.minor_moment_v,
                request.actions.user_torsion_l,
            ),
            ChannelShearCenterInput(
                ChannelShearCenterMethod(request.shear_center.method.value),
                request.shear_center.explicit_coordinate_t,
                request.shear_center.explicit_provenance,
                request.shear_center.include_rational_comparison,
            ),
        )
    )


def _branches(
    request: ChannelMomentSpliceRequest,
    slice6: ChannelMomentComponentResultants,
) -> tuple[FlangeBranchDecomposition, ChannelWebFaceDecomposition, FlangeBranchDecomposition]:
    # Resolve the controlled mechanics in the printed U.S. basis used by Slice 6;
    # source/display units remain independent transport concerns.
    unit = Unit.IN
    d = request.beam.depth.to(unit).magnitude
    tf = request.beam.flange_thickness.to(unit).magnitude
    tw = request.beam.web_thickness.to(unit).magnitude
    tp = request.flange_geometry.plate_thickness.to(unit).magnitude
    top = slice6.component(ChannelMomentRegionId.TOP_FLANGE)
    web = slice6.component(ChannelMomentRegionId.WEB)
    bottom = slice6.component(ChannelMomentRegionId.BOTTOM_FLANGE)
    top_branch = decompose_flange_wrench(
        flange_id="TOP",
        flange_reference_v=_q((d - tf) / 2, unit),
        outer_reference_v=_q(d / 2 + tp / 2, unit),
        inner_reference_v=_q(d / 2 - tf - tp / 2, unit),
        flange_force=top.wrench.force_lvt.l,
        flange_local_moment=top.wrench.moment_lvt.t,
    )
    bottom_branch = decompose_flange_wrench(
        flange_id="BOTTOM",
        flange_reference_v=_q(-(d - tf) / 2, unit),
        outer_reference_v=_q(-d / 2 - tp / 2, unit),
        inner_reference_v=_q(-d / 2 + tf + tp / 2, unit),
        flange_force=bottom.wrench.force_lvt.l,
        flange_local_moment=bottom.wrench.moment_lvt.t,
    )
    web_branch = decompose_channel_web_wrench(
        web_reference_t=_q(tw / 2, unit),
        back_reference_t=_q(-request.web_splice_plate.thickness.to(unit).magnitude / 2, unit),
        opening_reference_t=_q(
            tw + request.web_splice_plate.thickness.to(unit).magnitude / 2, unit
        ),
        web_normal_force=web.wrench.force_lvt.l,
        web_major_shear=web.wrench.force_lvt.v,
        web_local_major_moment=web.wrench.moment_lvt.t,
        web_free_torsion=web.wrench.moment_lvt.l,
    )
    return top_branch, web_branch, bottom_branch


def _mapping_request(
    request: ChannelMomentSpliceRequest,
    *,
    group_id: str,
    force_magnitude: PhysicalQuantity,
    plate_length: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    longitudinal_pitch: PhysicalQuantity,
    transverse_gauge: PhysicalQuantity,
    group_centroid_distance: PhysicalQuantity,
    fastener: ChannelMomentSpliceFastener,
) -> MultiRowOrchestrationRequest | None:
    if force_magnitude.canonical_magnitude == 0:
        return None
    unit = request.source_length_unit
    pitch = longitudinal_pitch.to(unit).magnitude
    span = pitch * Decimal(1)
    end = (
        plate_length.to(unit).magnitude / 2 - group_centroid_distance.to(unit).magnitude - span / 2
    )
    side = width.to(unit).magnitude / 2 - transverse_gauge.to(unit).magnitude / 2
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_4_1B_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:{group_id}",
        f"stage-4.1b:{group_id}",
        group_id,
        "STAGE_4_1B_SLICE6_COMPONENT_BRANCH",
        "Stage 4.1B component branch mapped to one physical bolt group",
        request.unit_system,
        unit,
        2,
        2,
        fastener.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        longitudinal_pitch,
        transverse_gauge,
        _q(max(end, Decimal("0.000000001")), unit),
        _q(max(end, Decimal("0.000000001")), unit),
        _q(max(side, Decimal("0.000000001")), unit),
        _q(max(side, Decimal("0.000000001")), unit),
        _q("0.000000001", unit),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                group_id,
                group_id,
                "ICE_LOCKED_PULTRUDED_FRP",
                thickness,
                PultrudedElementClassification.PLATE,
                _ZERO,
                factors,
                ThreadStatus(fastener.thread_condition),
            ),
        ),
        force_magnitude,
        _q(0, force_magnitude.unit),
        "STAGE_4_1B_GROUP_CENTROID",
        RowDistributionBasis.ASCE_PRESCRIBED,
        None,
        (),
        MethodProvenance(
            "STAGE_4_1B_STAGE_2_5A_RESOLVED_DEMAND",
            "STAGE_4_1B_CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_ENGINEERING_SPECIFICATION_RC1",
            "RC1",
            request.request_id,
            group_id,
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
    )


def _group_demand(
    request: ChannelMomentSpliceRequest,
    *,
    group_id: str,
    beam_id: str,
    component_id: str,
    branch_id: str,
    force_l: PhysicalQuantity,
    force_second: PhysicalQuantity,
    free_moment_normal: PhysicalQuantity,
    plate_length: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    longitudinal_pitch: PhysicalQuantity,
    transverse_gauge: PhysicalQuantity,
    group_centroid_distance: PhysicalQuantity,
    fastener: ChannelMomentSpliceFastener,
    coordinate_center_second: PhysicalQuantity,
    interface_offset: PhysicalQuantity,
    interface_kind: str,
) -> ChannelGroupDemand:
    unit = request.source_length_unit
    center_l = group_centroid_distance.to(unit).magnitude * (-_ONE if beam_id == "BEAM_A" else _ONE)
    pitch = longitudinal_pitch.to(unit).magnitude
    gauge = transverse_gauge.to(unit).magnitude
    center_second = coordinate_center_second.to(unit).magnitude
    coordinates = tuple(
        (
            _q(center_l + longitudinal * pitch / 2, unit),
            _q(center_second + transverse * gauge / 2, unit),
        )
        for transverse in (-_ONE, _ONE)
        for longitudinal in (-_ONE, _ONE)
    )
    with localcontext() as context:
        context.prec = 100
        magnitude = _q(
            (force_l.magnitude**2 + force_second.to(force_l.unit).magnitude ** 2).sqrt(),
            force_l.unit,
        )
    mapping = _mapping_request(
        request,
        group_id=group_id,
        force_magnitude=magnitude,
        plate_length=plate_length,
        width=width,
        thickness=thickness,
        longitudinal_pitch=longitudinal_pitch,
        transverse_gauge=transverse_gauge,
        group_centroid_distance=group_centroid_distance,
        fastener=fastener,
    )
    if mapping is None:
        return ChannelGroupDemand(
            group_id,
            beam_id,
            component_id,
            branch_id,
            coordinates,
            None,
            (),
            _fingerprint((group_id, coordinates, "ZERO_FORCE")),
        )
    resolved = _resolve(mapping)
    bundle = _execution_bundle(mapping, resolved)
    with localcontext() as context:
        context.prec = 100
        plan = plan_row_demands(
            resolved.geometry,
            magnitude,
            mapping.row_distribution_basis,
            mapping.provenance,
            connected_materials=ConnectedMaterialPair.FRP_FRP,
        )
    moment_unit = Unit.KIP_IN if request.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    zero_moments = ExactQuantityVector3D(*(_q(0, moment_unit) for _ in range(3)))
    if interface_kind == "WEB":
        global_force = ExactQuantityVector3D(force_l, force_second, _q(0, force_l.unit))
        frame = ExactInterfaceFrame(
            group_id,
            ExactQuantityVector3D(_q(center_l, unit), _q(0, unit), interface_offset.to(unit)),
            (_ZERO, _ONE, _ZERO),
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, -_ONE),
        )
        independent = ExactQuantityVector3D(
            _q(0, moment_unit), _q(0, moment_unit), free_moment_normal
        )
        force_reference = ExactQuantityVector3D(_q(0, unit), _q(0, unit), interface_offset.to(unit))
    else:
        global_force = ExactQuantityVector3D(force_l, _q(0, force_l.unit), force_second)
        frame = ExactInterfaceFrame(
            group_id,
            ExactQuantityVector3D(_q(center_l, unit), interface_offset.to(unit), _q(0, unit)),
            (_ONE, _ZERO, _ZERO),
            (_ZERO, _ZERO, _ONE),
            (_ZERO, -_ONE, _ZERO),
        )
        independent = zero_moments
        force_reference = frame.origin
    demand = calculate_eccentric_bolt_group_demand(
        EccentricDemandInput(
            f"{group_id}_ACTION",
            component_id,
            global_force,
            zero_moments,
            independent,
            force_reference,
            frame,
            bundle.physical_geometry,
            plan,
            resolved.applicability.method_applicability,
            resolved.applicability.qualification,
            ("STAGE_2_5A_DEMAND_ANALYSIS", "STAGE_4_1B_COMPONENT_BRANCH", group_id),
        )
    )
    per_bolt: dict[str, FlangePlaneDemand] = {}
    for scenario in demand.scenarios:
        for item in scenario.per_bolt:
            with localcontext() as context:
                context.prec = 100
                if interface_kind == "WEB":
                    first = item.total_force.v.to(force_l.unit)
                    second = item.total_force.u.to(force_l.unit)
                else:
                    # The flange force passes through the group centroid; the Stage 2.5A
                    # total therefore equals this exact controlled direct share.
                    first = PhysicalQuantity.of(force_l.magnitude * item.direct_share, force_l.unit)
                    second = item.total_force.v.to(force_l.unit)
            candidate = FlangePlaneDemand(
                first,
                second,
                demand.result_fingerprint,
                group_id,
                item.bolt_id,
            )
            current = per_bolt.get(item.bolt_id)
            if (
                current is None
                or candidate.magnitude.canonical_magnitude > current.magnitude.canonical_magnitude
            ):
                per_bolt[item.bolt_id] = candidate
    plane_demands = tuple(per_bolt[key] for key in sorted(per_bolt))
    return ChannelGroupDemand(
        group_id,
        beam_id,
        component_id,
        branch_id,
        coordinates,
        demand,
        plane_demands,
        _fingerprint((group_id, coordinates, demand.result_fingerprint, plane_demands)),
    )


def _demands(
    request: ChannelMomentSpliceRequest,
    top: FlangeBranchDecomposition,
    web: ChannelWebFaceDecomposition,
    bottom: FlangeBranchDecomposition,
) -> tuple[tuple[ChannelGroupDemand, ...], tuple[ChannelGroupDemand, ...]]:
    zero_force = _q(0, request.actions.axial_force_l.unit)
    web_groups: list[ChannelGroupDemand] = []
    flange_groups: list[ChannelGroupDemand] = []
    for beam_id, sign in (("BEAM_A", _ONE), ("BEAM_B", -_ONE)):
        for branch_id, normal, shear, moment, t_reference in (
            (
                "BACK",
                web.back_normal_force,
                web.back_major_shear,
                web.back_local_major_moment,
                web.back_reference_t,
            ),
            (
                "OPENING",
                web.opening_normal_force,
                web.opening_major_shear,
                web.opening_local_major_moment,
                web.opening_reference_t,
            ),
        ):
            web_groups.append(
                _group_demand(
                    request,
                    group_id=f"{beam_id}_WEB_{branch_id}",
                    beam_id=beam_id,
                    component_id=f"{branch_id}_WEB_FACE",
                    branch_id=branch_id,
                    force_l=_signed(normal, sign),
                    force_second=_signed(shear, sign),
                    free_moment_normal=_signed(moment, sign),
                    plate_length=request.web_splice_plate.length,
                    width=request.web_splice_plate.height,
                    thickness=request.web_splice_plate.thickness,
                    longitudinal_pitch=request.web_bolt_group.longitudinal_gauge,
                    transverse_gauge=request.web_bolt_group.vertical_pitch,
                    group_centroid_distance=request.web_bolt_group.centroid_offset,
                    fastener=request.web_fastener,
                    coordinate_center_second=_q(0, request.source_length_unit),
                    interface_offset=t_reference,
                    interface_kind="WEB",
                )
            )
        for branch in (top, bottom):
            for branch_id, force in (
                ("OUTER", branch.outer_force),
                ("INNER", branch.inner_total_force),
            ):
                flange_groups.append(
                    _group_demand(
                        request,
                        group_id=f"{beam_id}_{branch.flange_id}_{branch_id}",
                        beam_id=beam_id,
                        component_id=f"{branch.flange_id}_{branch_id}_FLANGE_FACE",
                        branch_id=branch_id,
                        force_l=_signed(force, sign),
                        force_second=zero_force,
                        free_moment_normal=_q(0, request.actions.major_moment_t.unit),
                        plate_length=request.flange_geometry.plate_length,
                        width=(
                            request.beam.flange_width
                            if branch_id == "OUTER"
                            else request.flange_geometry.inner_plate_width
                        ),
                        thickness=request.flange_geometry.plate_thickness,
                        longitudinal_pitch=request.flange_geometry.longitudinal_pitch,
                        transverse_gauge=request.flange_geometry.transverse_gauge,
                        group_centroid_distance=request.flange_geometry.group_centroid_distance,
                        fastener=request.flange_fastener,
                        coordinate_center_second=request.beam.flange_width / 2,
                        interface_offset=(
                            branch.outer_reference_v
                            if branch_id == "OUTER"
                            else branch.inner_reference_v
                        ),
                        interface_kind="FLANGE",
                    )
                )
    return tuple(web_groups), tuple(flange_groups)


def _clear_body(
    group_centroid: PhysicalQuantity,
    pitch: PhysicalQuantity,
    hole: PhysicalQuantity,
    unit: Unit,
) -> PhysicalQuantity:
    nearest = group_centroid.to(unit).magnitude - pitch.to(unit).magnitude / 2
    return _q(2 * (nearest - hole.to(unit).magnitude / 2), unit)


def _geometry_reasons(request: ChannelMomentSpliceRequest) -> tuple[str, ...]:
    unit = request.source_length_unit
    reasons: list[str] = []
    d = request.beam.depth.to(unit).magnitude
    bf = request.beam.flange_width.to(unit).magnitude
    tw = request.beam.web_thickness.to(unit).magnitude
    tf = request.beam.flange_thickness.to(unit).magnitude
    tp = request.flange_geometry.plate_thickness.to(unit).magnitude
    inner = request.flange_geometry.inner_plate_width.to(unit).magnitude
    if request.beam_end_gap.canonical_magnitude <= 0:
        reasons.append("POSITIVE_BEAM_END_GAP_REQUIRED")
    if request.web_splice_plate.count != 2 or not request.web_splice_plate.locked_identical:
        reasons.append("IDENTICAL_BACK_AND_OPENING_WEB_PLATES_REQUIRED")
    if (
        request.flange_geometry.outer_plate_count_per_flange != 1
        or request.flange_geometry.inner_plate_count_per_flange != 1
    ):
        reasons.append("ONE_OUTER_AND_ONE_INNER_PLATE_PER_FLANGE_REQUIRED")
    if not request.flange_geometry.locked_top_bottom_identical:
        reasons.append("IDENTICAL_TOP_BOTTOM_FLANGE_TOPOLOGY_REQUIRED")
    if inner > bf - 2 * tw:
        reasons.append("INNER_FLANGE_PLATE_MUST_NOT_OVERLAP_WEB")
    inner_face_v = d / 2 - tf - tp
    if request.web_splice_plate.height.to(unit).magnitude / 2 > inner_face_v:
        reasons.append("WEB_PLATE_MUST_CLEAR_INNER_FLANGE_PLATES")
    web_radius = request.web_fastener.hole_diameter.to(unit).magnitude / 2
    web_half_h = request.web_splice_plate.height.to(unit).magnitude / 2
    web_half_l = request.web_splice_plate.length.to(unit).magnitude / 2
    gap = request.beam_end_gap.to(unit).magnitude
    web_center = request.web_bolt_group.centroid_offset.to(unit).magnitude
    web_pitch_l = request.web_bolt_group.longitudinal_gauge.to(unit).magnitude
    web_pitch_v = request.web_bolt_group.vertical_pitch.to(unit).magnitude
    for beam_sign in (-_ONE, _ONE):
        center_l = beam_sign * web_center
        for dl in (-web_pitch_l / 2, web_pitch_l / 2):
            for v in (-web_pitch_v / 2, web_pitch_v / 2):
                l_coordinate = center_l + dl
                if abs(l_coordinate) + web_radius > web_half_l or abs(v) + web_radius > web_half_h:
                    reasons.append("WEB_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATES")
                if beam_sign < 0 and l_coordinate + web_radius > -gap / 2:
                    reasons.append("WEB_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END")
                if beam_sign > 0 and l_coordinate - web_radius < gap / 2:
                    reasons.append("WEB_HOLE_NOT_CONTAINED_AFTER_BEAM_B_END")
    fg = request.flange_geometry
    flange_radius = request.flange_fastener.hole_diameter.to(unit).magnitude / 2
    flange_half_l = fg.plate_length.to(unit).magnitude / 2
    group_l = fg.group_centroid_distance.to(unit).magnitude
    pitch_l = fg.longitudinal_pitch.to(unit).magnitude
    center_t = bf / 2
    gauge_t = fg.transverse_gauge.to(unit).magnitude
    for beam_sign in (-_ONE, _ONE):
        for dl in (-pitch_l / 2, pitch_l / 2):
            l_coordinate = beam_sign * group_l + dl
            for t in (center_t - gauge_t / 2, center_t + gauge_t / 2):
                if abs(l_coordinate) + flange_radius > flange_half_l:
                    reasons.append("FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATES")
                if t - flange_radius < tw or t + flange_radius > bf:
                    reasons.append("FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_INNER_PLATE")
                if beam_sign < 0 and l_coordinate + flange_radius > -gap / 2:
                    reasons.append("FLANGE_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END")
                if beam_sign > 0 and l_coordinate - flange_radius < gap / 2:
                    reasons.append("FLANGE_HOLE_NOT_CONTAINED_AFTER_BEAM_B_END")
    if fg.longitudinal_pitch < request.flange_fastener.hole_diameter:
        reasons.append("FLANGE_BOLT_PITCH_INSUFFICIENT")
    if request.web_bolt_group.longitudinal_gauge < request.web_fastener.hole_diameter:
        reasons.append("WEB_BOLT_PITCH_INSUFFICIENT")
    if (
        _clear_body(
            fg.group_centroid_distance,
            fg.longitudinal_pitch,
            request.flange_fastener.hole_diameter,
            unit,
        ).canonical_magnitude
        <= 0
    ):
        reasons.append("FLANGE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS")
    if (
        _clear_body(
            request.web_bolt_group.centroid_offset,
            request.web_bolt_group.longitudinal_gauge,
            request.web_fastener.hole_diameter,
            unit,
        ).canonical_magnitude
        <= 0
    ):
        reasons.append("WEB_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS")
    return tuple(dict.fromkeys(reasons))


def _equilibrium(
    request: ChannelMomentSpliceRequest,
    slice6: ChannelMomentComponentResultants,
    top: FlangeBranchDecomposition,
    web: ChannelWebFaceDecomposition,
    bottom: FlangeBranchDecomposition,
) -> ChannelMomentSpliceEquilibrium:
    slice_exact = all(
        (
            slice6.equilibrium.axial_equilibrium_exact,
            slice6.equilibrium.major_shear_equilibrium_exact,
            slice6.equilibrium.zero_minor_shear_exact,
            slice6.equilibrium.major_moment_equilibrium_exact,
            slice6.equilibrium.zero_minor_moment_exact,
            slice6.equilibrium.torsion_equilibrium_exact,
        )
    )
    top_exact = top.exact_force_equilibrium and top.exact_local_moment_equilibrium
    bottom_exact = bottom.exact_force_equilibrium and bottom.exact_local_moment_equilibrium
    web_exact = all(
        (
            web.exact_normal_force_recovery,
            web.exact_major_shear_recovery,
            web.exact_local_major_moment_recovery,
            web.exact_free_torsion_recovery,
        )
    )
    whole = slice_exact and top_exact and web_exact and bottom_exact
    force_unit = request.actions.axial_force_l.unit
    moment_unit = request.actions.major_moment_t.unit
    zero_f = _q(0, force_unit)
    zero_m = _q(0, moment_unit)
    partial = ChannelMomentSpliceEquilibrium(
        slice_exact,
        top_exact,
        web_exact,
        bottom_exact,
        whole,
        True,
        zero_f,
        zero_f,
        zero_m,
        zero_m,
        zero_m,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def _visualization(
    request: ChannelMomentSpliceRequest,
    slice6: ChannelMomentComponentResultants,
    web_groups: tuple[ChannelGroupDemand, ...],
    flange_groups: tuple[ChannelGroupDemand, ...],
) -> ChannelMomentSpliceVisualization:
    unit = request.source_length_unit
    d = request.beam.depth.to(unit).magnitude
    bf = request.beam.flange_width.to(unit).magnitude
    tw = request.beam.web_thickness.to(unit).magnitude
    tf = request.beam.flange_thickness.to(unit).magnitude
    hw = d - 2 * tf
    display = request.beam.display_length_each_side.to(unit).magnitude
    gap = request.beam_end_gap.to(unit).magnitude
    beam_centers = (("BEAM_A", -gap / 2 - display / 2), ("BEAM_B", gap / 2 + display / 2))
    boxes: list[WebSpliceBox] = []
    regions: list[WebSpliceMaterialRegion] = []
    for beam_id, center_l in beam_centers:
        components = (
            (
                f"{beam_id}_TOP_FLANGE",
                "CHANNEL_TOP_FLANGE",
                (center_l, (d - tf) / 2, bf / 2),
                (display, tf, bf),
            ),
            (f"{beam_id}_WEB", "CHANNEL_WEB", (center_l, _ZERO, tw / 2), (display, hw, tw)),
            (
                f"{beam_id}_BOTTOM_FLANGE",
                "CHANNEL_BOTTOM_FLANGE",
                (center_l, -(d - tf) / 2, bf / 2),
                (display, tf, bf),
            ),
        )
        for component, role, center, size in components:
            boxes.append(WebSpliceBox(component, role, _vector(center, unit), _vector(size, unit)))
            if "WEB" in component:
                axes = ((_ONE, _ZERO, _ZERO), (_ZERO, _ONE, _ZERO), (_ZERO, _ZERO, _ONE))
            elif "TOP" in component:
                axes = ((_ONE, _ZERO, _ZERO), (_ZERO, _ZERO, _ONE), (_ZERO, -_ONE, _ZERO))
            else:
                axes = ((_ONE, _ZERO, _ZERO), (_ZERO, _ZERO, -_ONE), (_ZERO, _ONE, _ZERO))
            regions.append(WebSpliceMaterialRegion(component, component, *axes))
    wp = request.web_splice_plate
    wpt = wp.thickness.to(unit).magnitude
    web_plate_positions = (
        ("BACK_WEB_SPLICE_PLATE", -wpt / 2, -_ONE),
        ("OPENING_WEB_SPLICE_PLATE", tw + wpt / 2, _ONE),
    )
    for component, t, tt_sign in web_plate_positions:
        boxes.append(
            WebSpliceBox(
                component,
                "FRP_CHANNEL_WEB_SPLICE_PLATE",
                _vector((_ZERO, _ZERO, t), unit),
                _vector((wp.length.to(unit).magnitude, wp.height.to(unit).magnitude, wpt), unit),
            )
        )
        regions.append(
            WebSpliceMaterialRegion(
                component,
                component,
                (_ONE, _ZERO, _ZERO),
                (_ZERO, _ONE, _ZERO),
                (_ZERO, _ZERO, tt_sign),
            )
        )
    fp = request.flange_geometry
    fpt = fp.plate_thickness.to(unit).magnitude
    inner_w = fp.inner_plate_width.to(unit).magnitude
    plate_positions = (
        ("TOP_OUTER_FLANGE_SPLICE_PLATE", "TOP_OUTER", d / 2 + fpt / 2, bf, _ONE),
        ("TOP_INNER_FLANGE_SPLICE_PLATE", "TOP_INNER", d / 2 - tf - fpt / 2, inner_w, -_ONE),
        ("BOTTOM_OUTER_FLANGE_SPLICE_PLATE", "BOTTOM_OUTER", -d / 2 - fpt / 2, bf, -_ONE),
        ("BOTTOM_INNER_FLANGE_SPLICE_PLATE", "BOTTOM_INNER", -d / 2 + tf + fpt / 2, inner_w, _ONE),
    )
    for component, role, v, width, tt_sign in plate_positions:
        boxes.append(
            WebSpliceBox(
                component,
                f"FRP_CHANNEL_FLANGE_SPLICE_PLATE_{role}",
                _vector((_ZERO, v, bf / 2), unit),
                _vector((fp.plate_length.to(unit).magnitude, fpt, width), unit),
            )
        )
        regions.append(
            WebSpliceMaterialRegion(
                component,
                component,
                (_ONE, _ZERO, _ZERO),
                (_ZERO, _ZERO, _ONE),
                (_ZERO, tt_sign, _ZERO),
            )
        )
    bolts: list[ChannelMomentSpliceBolt] = []
    web_lookup = {item.group_id: item for item in web_groups}
    for beam_id in ("BEAM_A", "BEAM_B"):
        group = web_lookup[f"{beam_id}_WEB_BACK"]
        for index, (l_coordinate, v_coordinate) in enumerate(
            group.physical_coordinates_first_second, 1
        ):
            bolt_id = f"{beam_id}_WEB_B{index}"
            path = ("BACK_WEB_SPLICE_PLATE", "CHANNEL_WEB", "OPENING_WEB_SPLICE_PLATE")
            bolts.append(
                ChannelMomentSpliceBolt(
                    bolt_id,
                    group.group_id,
                    WebSpliceVector(l_coordinate, v_coordinate, _q(tw / 2, unit)),
                    path,
                    WebSpliceVector(l_coordinate, v_coordinate, _q(-wpt, unit)),
                    WebSpliceVector(l_coordinate, v_coordinate, _q(tw + wpt, unit)),
                    _q(tw + 2 * wpt, unit),
                    "EXTERIOR_BACK_WEB_SPLICE_PLATE_FACE",
                    "EXTERIOR_OPENING_WEB_SPLICE_PLATE_FACE",
                )
            )
    flange_lookup = {item.group_id: item for item in flange_groups}
    for beam_id in ("BEAM_A", "BEAM_B"):
        for flange_id, v_center in (("TOP", (d - tf) / 2), ("BOTTOM", -(d - tf) / 2)):
            group = flange_lookup[f"{beam_id}_{flange_id}_OUTER"]
            outer_v = d / 2 + fpt if flange_id == "TOP" else -d / 2 - fpt
            inner_v = d / 2 - tf - fpt if flange_id == "TOP" else -d / 2 + tf + fpt
            for index, (l_coordinate, t_coordinate) in enumerate(
                group.physical_coordinates_first_second, 1
            ):
                path = (
                    f"{flange_id}_OUTER_FLANGE_SPLICE_PLATE",
                    f"{flange_id}_CHANNEL_FLANGE",
                    f"{flange_id}_INNER_FLANGE_SPLICE_PLATE",
                )
                bolts.append(
                    ChannelMomentSpliceBolt(
                        f"{beam_id}_{flange_id}_B{index}",
                        group.group_id,
                        WebSpliceVector(l_coordinate, _q(v_center, unit), t_coordinate),
                        path,
                        WebSpliceVector(l_coordinate, _q(outer_v, unit), t_coordinate),
                        WebSpliceVector(l_coordinate, _q(inner_v, unit), t_coordinate),
                        _q(tf + 2 * fpt, unit),
                        "EXTERIOR_OUTER_FLANGE_SPLICE_PLATE_FACE",
                        "EXTERIOR_INNER_FLANGE_SPLICE_PLATE_FACE",
                    )
                )
    properties = slice6.section_properties
    centroid_t = properties.channel_centroid_t_absolute.to(unit)
    shear_center_t = slice6.shear_center.absolute_coordinate_t.to(unit)
    force = request.actions
    return ChannelMomentSpliceVisualization(
        ("L_CH", "V_CH", "T_CH"),
        _zero_vector(unit),
        WebSpliceVector(_q(0, unit), _q(0, unit), centroid_t),
        WebSpliceVector(_q(0, unit), _q(0, unit), shear_center_t),
        (_q(-gap / 2, unit), _q(gap / 2, unit)),
        tuple(boxes),
        tuple(bolts),
        request.web_fastener.bolt_diameter,
        request.web_fastener.hole_diameter,
        request.flange_fastener.bolt_diameter,
        request.flange_fastener.hole_diameter,
        tuple(regions),
        WebSpliceVector(_q(0, unit), _q(0, unit), centroid_t),
        WebSpliceVector(force.axial_force_l, force.major_shear_v, force.minor_shear_t),
        WebSpliceVector(
            slice6.torsion_diagnostics.generated_centroidal_torsion,
            force.minor_moment_v,
            force.major_moment_t,
        ),
        slice6.torsion_diagnostics.generated_centroidal_torsion,
        True,
    )


def preview_channel_moment_splice(
    request: ChannelMomentSpliceRequest,
) -> ChannelMomentSplicePreviewResult:
    if not isinstance(request, ChannelMomentSpliceRequest):
        raise TypeError("request must be ChannelMomentSpliceRequest.")
    slice6 = _slice6(request)
    slice_exact = all(
        (
            slice6.equilibrium.axial_equilibrium_exact,
            slice6.equilibrium.major_shear_equilibrium_exact,
            slice6.equilibrium.zero_minor_shear_exact,
            slice6.equilibrium.major_moment_equilibrium_exact,
            slice6.equilibrium.zero_minor_moment_exact,
            slice6.equilibrium.torsion_equilibrium_exact,
        )
    )
    if not slice_exact:
        raise ValueError("SLICE6_EXACT_SIX_COMPONENT_EQUILIBRIUM_REQUIRED")
    top, web, bottom = _branches(request, slice6)
    web_groups, flange_groups = _demands(request, top, web, bottom)
    reasons = _geometry_reasons(request)
    equilibrium = _equilibrium(request, slice6, top, web, bottom)
    if not equilibrium.whole_connection_six_component_exact:
        raise ValueError("STAGE_4_1B_EXACT_WHOLE_CONNECTION_EQUILIBRIUM_REQUIRED")
    visualization = _visualization(request, slice6, web_groups, flange_groups)
    web_clear = _clear_body(
        request.web_bolt_group.centroid_offset,
        request.web_bolt_group.longitudinal_gauge,
        request.web_fastener.hole_diameter,
        request.source_length_unit,
    )
    flange_clear = _clear_body(
        request.flange_geometry.group_centroid_distance,
        request.flange_geometry.longitudinal_pitch,
        request.flange_fastener.hole_diameter,
        request.source_length_unit,
    )
    geometry_payload = (
        request.beam.depth,
        request.beam.flange_width,
        request.beam.web_thickness,
        request.beam.flange_thickness,
        request.beam.profile_family,
        request.beam.equal_flange,
        request.beam.lipped,
        request.beam.back_to_back,
        request.beam_end_gap,
        request.web_splice_plate,
        request.web_bolt_group,
        request.flange_geometry,
        request.web_fastener.bolt_diameter,
        request.web_fastener.hole_diameter,
        request.flange_fastener.bolt_diameter,
        request.flange_fastener.hole_diameter,
        visualization.bolts,
        visualization.material_regions,
    )
    engineering_payload = (
        CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION,
        geometry_payload,
        request.actions,
        request.shear_center,
        request.web_fastener,
        request.flange_fastener,
        slice6.result_fingerprint,
        top,
        web,
        bottom,
        web_groups,
        flange_groups,
        equilibrium,
        CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
        CHANNEL_MOMENT_SPLICE_QUALIFICATION,
    )
    valid = not reasons
    demands = (*web_groups, *flange_groups)
    return ChannelMomentSplicePreviewResult(
        request.request_id,
        CHANNEL_MOMENT_SPLICE_PRODUCT_ID,
        CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION,
        CHANNEL_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION,
        ChannelMomentSpliceStatus.VALID if valid else ChannelMomentSpliceStatus.INVALID_GEOMETRY,
        reasons,
        ChannelMomentSpliceStatus.NOT_EVALUATED
        if valid
        else ChannelMomentSpliceStatus.INVALID_GEOMETRY,
        False,
        False,
        valid
        and all(
            item.demand is None or item.demand.availability is DemandAnalysisAvailability.CALCULATED
            for item in demands
        ),
        slice6,
        top,
        web,
        bottom,
        web_groups,
        flange_groups,
        web_clear,
        flange_clear,
        request.beam.web_thickness / 2,
        request.beam.flange_thickness / 2,
        equilibrium,
        visualization,
        True,
        CHANNEL_MOMENT_SPLICE_QUALIFICATION,
        "NOT_EVALUATED",
        "NOT_EVALUATED",
        "NOT_EVALUATED",
        "NOT_EVALUATED",
        CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
        CHANNEL_MOMENT_SPLICE_DISCLAIMER,
        (
            "USER_TORSION_AND_OPEN_SECTION_WARPING_RESISTANCE_NOT_EVALUATED",
            "BOLT_AXIS_TENSION_AND_PRYING_NOT_EVALUATED",
            "UNEQUAL_PLANE_SECONDARY_BOLT_BENDING_REQUIRES_ENGINEERING_REVIEW",
            "MOMENT_CONNECTION_STIFFNESS_ROTATION_AND_FULL_STRENGTH_NOT_EVALUATED",
        ),
        CHANNEL_MOMENT_SPLICE_CONTROLLED_HASHES,
        _fingerprint(
            (
                CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION,
                geometry_payload,
                request.actions,
                request.shear_center,
                request.web_fastener,
                request.flange_fastener,
            )
        ),
        _fingerprint(geometry_payload),
        _fingerprint(engineering_payload),
        _fingerprint((engineering_payload, visualization)),
    )


def _local_summary(
    request: ChannelMomentSpliceRequest,
    group: ChannelGroupDemand,
    *,
    component_id: str,
    force_magnitude: PhysicalQuantity,
    plate_length: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    pitch: PhysicalQuantity,
    gauge: PhysicalQuantity,
    centroid: PhysicalQuantity,
    fastener: ChannelMomentSpliceFastener,
) -> ChannelLocalCheckSummary:
    if group.demand is None or force_magnitude.canonical_magnitude == 0:
        partial = ChannelLocalCheckSummary(component_id, (), (), (), (), True, "")
        return replace(partial, result_fingerprint=_fingerprint(partial))
    with localcontext() as context:
        context.prec = 100
        unsigned_force = PhysicalQuantity.of(abs(force_magnitude.magnitude), force_magnitude.unit)
    mapping = cast(
        MultiRowOrchestrationRequest,
        _mapping_request(
            request,
            group_id=group.group_id,
            force_magnitude=unsigned_force,
            plate_length=plate_length,
            width=width,
            thickness=thickness,
            longitudinal_pitch=pitch,
            transverse_gauge=gauge,
            group_centroid_distance=centroid,
            fastener=fastener,
        ),
    )
    allocations = tuple(
        {
            item.bolt_id: LayerInPlaneDemandAllocation(
                item.bolt_id,
                group.group_id,
                _ONE,
                "STAGE_4_1B_EXACT_LAYER_ALLOCATION",
                group.demand.result_fingerprint,
            )
            for scenario in group.demand.scenarios
            for item in scenario.per_bolt
        }.values()
    )
    try:
        response = evaluate_multirow_connection_with_resolved_demand(
            mapping, group.demand, allocations
        )
    except ValueError as error:
        partial = ChannelLocalCheckSummary(
            component_id,
            (),
            (),
            (f"LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE:{error}",),
            (),
            False,
            "",
        )
        return replace(partial, result_fingerprint=_fingerprint(partial))
    checks: list[str] = []
    failures: list[str] = []
    fingerprints: list[str] = []
    for handoff in response.automatic_handoff_results:
        fingerprints.append(handoff.result_fingerprint)
        for item in handoff.checks:
            if item.family not in _LOCAL_FAMILIES or item.resistance_result is None:
                continue
            check_id = f"{component_id}:{item.check_id}"
            checks.append(check_id)
            if item.resistance_result.numerical_comparison.value == "FAIL":
                failures.append(check_id)
    partial = ChannelLocalCheckSummary(
        component_id,
        tuple(dict.fromkeys(checks)),
        tuple(dict.fromkeys(failures)),
        (),
        tuple(dict.fromkeys(fingerprints)),
        False,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def _web_body(
    request: ChannelMomentSpliceRequest,
    preview: ChannelMomentSplicePreviewResult,
    branch_id: str,
) -> WebSpliceBodyInteractionResult:
    branch = preview.web_faces
    normal, shear, local_moment = (
        (branch.back_normal_force, branch.back_major_shear, branch.back_local_major_moment)
        if branch_id == "BACK"
        else (
            branch.opening_normal_force,
            branch.opening_major_shear,
            branch.opening_local_major_moment,
        )
    )
    half = preview.web_clear_body_length / 2
    with localcontext() as context:
        context.prec = 100
        actions = tuple(
            WebSpliceCriticalSectionAction(
                f"{branch_id}_{section}",
                coordinate,
                PhysicalQuantity.of(normal.magnitude * 2, normal.unit),
                PhysicalQuantity.of(shear.magnitude * 2, shear.unit),
                PhysicalQuantity.of(
                    (
                        local_moment.magnitude
                        - coordinate.to(request.source_length_unit).magnitude * shear.magnitude
                    )
                    * 2,
                    local_moment.unit,
                ),
            )
            for section, coordinate in (
                (
                    "LEFT_CLEAR_BOUNDARY",
                    PhysicalQuantity.of(-half.magnitude, half.unit),
                ),
                ("JOINT_CENTER", _q(0, request.source_length_unit)),
                ("RIGHT_CLEAR_BOUNDARY", half),
            )
        )
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_4_1B_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    from frp_master_connection.application.mat1_scope import time_category_for_case

    time_effect = select_time_effect_factor(
        time_category_for_case(TimeEffectCategory.WIND_TORNADO_SEISMIC)
    )
    thickness = request.web_splice_plate.thickness
    height = request.web_splice_plate.height
    length = preview.web_clear_body_length
    tension = plate_longitudinal_tension_strength(
        thickness,
        _adjusted_ice_property(FRPPropertyKind.FT_L, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        time_effect,
    )
    compression = plate_longitudinal_compression_strength(
        thickness,
        height,
        _adjusted_ice_property(FRPPropertyKind.FC_L, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.ET_L, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.ET_T, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.G_LT, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.NU_LT, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        time_effect,
        longitudinal_span=length,
    )
    shear_strength = plate_in_plane_shear_strength(
        thickness,
        height,
        _adjusted_ice_property(FRPPropertyKind.FSH_LT, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.ET_L, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.ET_T, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.G_LT, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        _adjusted_ice_property(FRPPropertyKind.NU_LT, factors, f"{branch_id}_WEB_SPLICE_PLATE"),
        time_effect,
        longitudinal_span=length,
    )
    return evaluate_rational_body_interaction(
        plate_height=height,
        plate_thickness=thickness,
        actions=actions,
        symmetry_proven=True,
        tension_strength=tension,
        compression_strength=compression,
        shear_strength=shear_strength,
    )


def _common_bolts(
    request: ChannelMomentSpliceRequest,
    preview: ChannelMomentSplicePreviewResult,
    *,
    web: bool,
) -> tuple[AsymmetricTwoPlaneBoltResult, ...]:
    groups = {
        item.group_id: item
        for item in (preview.web_group_demands if web else preview.flange_group_demands)
    }
    results: list[AsymmetricTwoPlaneBoltResult] = []
    for bolt in preview.visualization.bolts:
        is_web_bolt = "CHANNEL_WEB" in bolt.path_layers[1]
        if is_web_bolt != web:
            continue
        first_id = bolt.group_id
        second_id = (
            first_id.replace("_BACK", "_OPENING") if web else first_id.replace("_OUTER", "_INNER")
        )
        first = groups[first_id]
        second = groups[second_id]
        index = int(bolt.bolt_id.rsplit("B", 1)[1]) - 1
        zero = FlangePlaneDemand(
            _q(0, request.actions.axial_force_l.unit),
            _q(0, request.actions.axial_force_l.unit),
            _fingerprint((bolt.bolt_id, "ZERO_PLANE_DEMAND")),
            first_id,
            bolt.bolt_id,
        )
        first_plane = (
            zero if not first.per_bolt_plane_demands else first.per_bolt_plane_demands[index]
        )
        second_plane = (
            zero if not second.per_bolt_plane_demands else second.per_bolt_plane_demands[index]
        )
        fastener = request.web_fastener if web else request.flange_fastener
        results.append(
            evaluate_channel_two_plane_bolt(
                bolt_id=bolt.bolt_id,
                physical_path=bolt.path_layers,
                outer_plane=first_plane,
                inner_plane=second_plane,
                diameter=fastener.bolt_diameter,
                thread_condition=fastener.thread_condition,
                source_authority_id=fastener.source_authority_id,
                nominal_shear_stress=fastener.nominal_shear_stress,
            )
        )
    return tuple(results)


def design_check_channel_moment_splice(
    request: ChannelMomentSpliceRequest,
) -> ChannelMomentSpliceDesignResult:
    preview = preview_channel_moment_splice(request)
    if preview.geometry_invalid_reasons:
        return ChannelMomentSpliceDesignResult(
            preview,
            ChannelMomentSpliceStatus.INVALID_GEOMETRY,
            "NOT_EVALUATED",
            False,
            (),
            (),
            (),
            (),
            (),
            ("INVALID_GEOMETRY",),
            (),
            None,
            None,
            CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
            CHANNEL_MOMENT_SPLICE_DISCLAIMER,
            True,
            _fingerprint((preview.application_fingerprint, "INVALID_GEOMETRY")),
        )
    local: list[ChannelLocalCheckSummary] = []
    web_groups = {item.group_id: item for item in preview.web_group_demands}
    flange_groups = {item.group_id: item for item in preview.flange_group_demands}
    for beam_id, sign in (("BEAM_A", _ONE), ("BEAM_B", -_ONE)):
        for branch_id, normal, shear in (
            ("BACK", preview.web_faces.back_normal_force, preview.web_faces.back_major_shear),
            (
                "OPENING",
                preview.web_faces.opening_normal_force,
                preview.web_faces.opening_major_shear,
            ),
        ):
            group = web_groups[f"{beam_id}_WEB_{branch_id}"]
            with localcontext() as context:
                context.prec = 100
                magnitude = _q(
                    (normal.magnitude**2 + shear.to(normal.unit).magnitude ** 2).sqrt(), normal.unit
                )
            for target, thickness in (
                (f"{branch_id}_WEB_SPLICE_PLATE", request.web_splice_plate.thickness),
                (
                    f"{beam_id}_{branch_id}_CHANNEL_WEB_FACE:{CHANNEL_WEB_SUBLAYER_METHOD}",
                    request.beam.web_thickness / 2,
                ),
            ):
                local.append(
                    _local_summary(
                        request,
                        group,
                        component_id=target,
                        force_magnitude=_signed(magnitude, sign),
                        plate_length=request.web_splice_plate.length,
                        width=request.web_splice_plate.height,
                        thickness=thickness,
                        pitch=request.web_bolt_group.longitudinal_gauge,
                        gauge=request.web_bolt_group.vertical_pitch,
                        centroid=request.web_bolt_group.centroid_offset,
                        fastener=request.web_fastener,
                    )
                )
        for branch in (preview.top_flange, preview.bottom_flange):
            for branch_id, force, width in (
                ("OUTER", branch.outer_force, request.beam.flange_width),
                ("INNER", branch.inner_total_force, request.flange_geometry.inner_plate_width),
            ):
                group = flange_groups[f"{beam_id}_{branch.flange_id}_{branch_id}"]
                for target, thickness in (
                    (
                        f"{branch.flange_id}_{branch_id}_FLANGE_SPLICE_PLATE",
                        request.flange_geometry.plate_thickness,
                    ),
                    (
                        f"{beam_id}_{branch.flange_id}_{branch_id}_CHANNEL_FLANGE_FACE",
                        request.beam.flange_thickness / 2,
                    ),
                ):
                    local.append(
                        _local_summary(
                            request,
                            group,
                            component_id=target,
                            force_magnitude=_signed(force, sign),
                            plate_length=request.flange_geometry.plate_length,
                            width=width,
                            thickness=thickness,
                            pitch=request.flange_geometry.longitudinal_pitch,
                            gauge=request.flange_geometry.transverse_gauge,
                            centroid=request.flange_geometry.group_centroid_distance,
                            fastener=request.flange_fastener,
                        )
                    )
    flange_bodies = tuple(
        evaluate_flange_plate_body(
            component_id=f"{branch.flange_id}_{branch_id}_FLANGE_SPLICE_PLATE",
            signed_force=force,
            width=width,
            thickness=request.flange_geometry.plate_thickness,
            clear_body_length=preview.flange_clear_body_length,
            material_snapshot=material_for_owner(
                f"{branch.flange_id}_{branch_id}_FLANGE_SPLICE_PLATE",
                create_locked_ice_material_snapshot(),
            ),
            time_effect_category=time_category_for_case(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        )
        for branch in (preview.top_flange, preview.bottom_flange)
        for branch_id, force, width in (
            ("OUTER", branch.outer_force, request.beam.flange_width),
            ("INNER", branch.inner_total_force, request.flange_geometry.inner_plate_width),
        )
    )
    web_bodies = (_web_body(request, preview, "BACK"), _web_body(request, preview, "OPENING"))
    web_bolts = _common_bolts(request, preview, web=True)
    flange_bolts = _common_bolts(request, preview, web=False)
    failures = tuple(
        dict.fromkeys(
            [item for summary in local for item in summary.failed_check_ids]
            + [
                f"FLANGE_BODY:{item.component_id}"
                for item in flange_bodies
                if item.status is FlangeBodyStatus.FAIL
            ]
            + [
                f"WEB_BODY:{branch_id}"
                for branch_id, item in zip(("BACK", "OPENING"), web_bodies, strict=True)
                if item.status is RationalBodyStatus.FAIL_RATIONAL_METHOD
            ]
            + [
                f"FLANGE_BOLT:{item.bolt_id}"
                for item in flange_bolts
                if item.status is AsymmetricBoltStatus.FAIL
            ]
            + [
                f"WEB_BOLT:{item.bolt_id}"
                for item in web_bolts
                if item.status is AsymmetricBoltStatus.FAIL
            ]
        )
    )
    unavailable = tuple(
        dict.fromkeys(
            [
                f"LOCAL:{summary.component_id}"
                for summary in local
                if summary.warnings and not summary.not_required_zero_force
            ]
            + [
                f"FLANGE_BOLT:{item.bolt_id}"
                for item in flange_bolts
                if item.status is AsymmetricBoltStatus.NOT_EVALUATED
            ]
            + [
                f"WEB_BOLT:{item.bolt_id}"
                for item in web_bolts
                if item.status is AsymmetricBoltStatus.NOT_EVALUATED
            ]
            + [
                f"WEB_BODY:{branch_id}"
                for branch_id, item in zip(("BACK", "OPENING"), web_bodies, strict=True)
                if item.status is RationalBodyStatus.NOT_EVALUATED
            ]
        )
    )
    status = (
        ChannelMomentSpliceStatus.FAIL
        if failures
        else ChannelMomentSpliceStatus.NOT_EVALUATED
        if unavailable
        else ChannelMomentSpliceStatus.PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED
    )
    numeric: list[tuple[str, Decimal]] = [
        (f"FLANGE_BODY:{item.component_id}", item.utilization)
        for item in flange_bodies
        if item.utilization is not None
    ]
    numeric.extend(
        (f"WEB_BODY:{branch_id}", item.rational_utilization)
        for branch_id, item in zip(("BACK", "OPENING"), web_bodies, strict=True)
        if item.rational_utilization is not None
    )
    numeric.extend(
        (f"FLANGE_BOLT:{item.bolt_id}", item.governing_utilization)
        for item in flange_bolts
        if item.governing_utilization is not None
    )
    numeric.extend(
        (f"WEB_BOLT:{item.bolt_id}", item.governing_utilization)
        for item in web_bolts
        if item.governing_utilization is not None
    )
    governing = max(numeric, key=lambda item: item[1]) if numeric else None
    payload = (
        preview.application_fingerprint,
        status,
        tuple(local),
        flange_bodies,
        tuple(item.result_fingerprint for item in web_bodies),
        flange_bolts,
        web_bolts,
        failures,
        unavailable,
        CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
    )
    return ChannelMomentSpliceDesignResult(
        preview,
        status,
        status.value,
        False,
        tuple(local),
        flange_bodies,
        web_bodies,
        flange_bolts,
        web_bolts,
        failures,
        unavailable,
        None if governing is None else governing[1],
        None if governing is None else governing[0],
        CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID,
        CHANNEL_MOMENT_SPLICE_DISCLAIMER,
        True,
        _fingerprint(payload),
    )


__all__ = (
    "CHANNEL_MOMENT_SPLICE_CONTROLLED_HASHES",
    "CHANNEL_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION",
    "CHANNEL_MOMENT_SPLICE_RESULT_SCHEMA_VERSION",
    "ChannelGroupDemand",
    "ChannelLocalCheckSummary",
    "ChannelMomentSpliceBolt",
    "ChannelMomentSpliceDesignResult",
    "ChannelMomentSpliceEquilibrium",
    "ChannelMomentSplicePreviewResult",
    "ChannelMomentSpliceVisualization",
    "design_check_channel_moment_splice",
    "preview_channel_moment_splice",
)
