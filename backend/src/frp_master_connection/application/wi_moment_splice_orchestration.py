"""Backend-authoritative Stage 4.1A W/I major-axis moment-splice orchestration."""

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
    WebSpliceGroupResult,
    WebSpliceMaterialRegion,
    WebSpliceRC2PreviewResult,
    WebSpliceVector,
    WebSpliceWrench,
    _adjusted_ice_property,
    _cross_offset_force,
    _evaluate_double_shear,
    _evaluate_supported_local_resistance,
    _layer_resistance_request,
    _layers,
    preview_web_splice,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    DoubleShearStatus,
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
    calculate_eccentric_bolt_group_demand,
    calculate_wi_moment_component_resultants,
    canonical_decimal_string,
    evaluate_rational_body_interaction,
    plan_row_demands,
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
)
from frp_master_connection.calculation.mat1_flange_body import (
    evaluate_material_flange_plate_body as evaluate_flange_plate_body,
)
from frp_master_connection.calculation.multirow import MethodProvenance, RowDistributionBasis
from frp_master_connection.calculation.properties import create_locked_ice_material_snapshot
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentComponentResult,
    WIMomentComponentResultants,
    WIMomentRegionId,
    WIMomentSectionInput,
)
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    WI_MOMENT_SPLICE_DISCLAIMER,
    WI_MOMENT_SPLICE_DISCLAIMER_ID,
    WI_MOMENT_SPLICE_QUALIFICATION,
    WI_MOMENT_SPLICE_SUBLAYER_METHOD,
    AsymmetricBoltStatus,
    AsymmetricTwoPlaneBoltResult,
    FlangeBodyStatus,
    FlangeBranchDecomposition,
    FlangePlaneDemand,
    FlangePlateBodyResult,
    decompose_flange_wrench,
    evaluate_asymmetric_two_plane_bolt,
)
from frp_master_connection.domain.web_splice import (
    WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    WebSpliceForce,
    WebSpliceGroupId,
    WebSpliceRequest,
)
from frp_master_connection.domain.wi_moment_splice import (
    WI_MOMENT_SPLICE_CONTRACT_VERSION,
    WI_MOMENT_SPLICE_PRODUCT_ID,
    WIMomentSpliceRequest,
    WIMomentSpliceStatus,
)

WI_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION = "4.1A-PREVIEW-RC1"
WI_MOMENT_SPLICE_RESULT_SCHEMA_VERSION = "4.1A-RESULT-RC1"
_ZERO = Decimal(0)
_ONE = Decimal(1)
_HALF = Decimal("0.5")
_LOCAL_FAMILIES = frozenset(
    {
        MultiRowCheckFamily.PIN_BEARING,
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowCheckFamily.INTERROW_SHEAR_OUT,
        MultiRowCheckFamily.BLOCK_SHEAR,
    }
)


@dataclass(frozen=True, slots=True)
class MomentSpliceBolt:
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
class MomentSpliceVisualization:
    frame_axes: tuple[str, str, str]
    joint_reference_l_v_t: WebSpliceVector
    beam_end_planes_l: tuple[PhysicalQuantity, PhysicalQuantity]
    boxes: tuple[WebSpliceBox, ...]
    bolts: tuple[MomentSpliceBolt, ...]
    web_bolt_diameter: PhysicalQuantity
    web_hole_diameter: PhysicalQuantity
    flange_bolt_diameter: PhysicalQuantity
    flange_hole_diameter: PhysicalQuantity
    material_regions: tuple[WebSpliceMaterialRegion, ...]
    action_reference_l_v_t: WebSpliceVector
    applied_force_l_v_t: WebSpliceVector
    applied_moment_l_v_t: WebSpliceVector


@dataclass(frozen=True, slots=True)
class FlangeGroupDemand:
    group_id: str
    flange_id: str
    beam_id: str
    branch_id: str
    strip_id: str | None
    physical_coordinates_l_t: tuple[tuple[PhysicalQuantity, PhysicalQuantity], ...]
    demand: EccentricDemandResult | None
    per_bolt_plane_demands: tuple[FlangePlaneDemand, ...]
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class LocalCheckSummary:
    component_id: str
    required_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    result_fingerprints: tuple[str, ...]
    not_required_zero_force: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class MomentSpliceEquilibrium:
    axial_residual: PhysicalQuantity
    shear_residual: PhysicalQuantity
    major_moment_residual: PhysicalQuantity
    slice5_exact: bool
    top_branch_exact: bool
    bottom_branch_exact: bool
    whole_joint_exact: bool
    beam_a_b_equal_opposite: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class WIMomentSplicePreviewResult:
    request_id: str
    product_id: str
    contract_version: str
    preview_schema_version: str
    geometry_status: WIMomentSpliceStatus
    geometry_invalid_reasons: tuple[str, ...]
    assembly_status: WIMomentSpliceStatus
    ordinary_pass_allowed: bool
    resistance_evaluated: bool
    design_check_ready: bool
    slice5_result: WIMomentComponentResultants
    top_flange: FlangeBranchDecomposition
    bottom_flange: FlangeBranchDecomposition
    web_preview: WebSpliceRC2PreviewResult
    flange_group_demands: tuple[FlangeGroupDemand, ...]
    flange_clear_body_length: PhysicalQuantity
    rational_face_sublayer_thickness: PhysicalQuantity
    equilibrium: MomentSpliceEquilibrium
    visualization: MomentSpliceVisualization
    rational_method_engineering_review_required: bool
    connection_element_qualification: str
    moment_connection_stiffness_classification: str
    moment_rotation_capacity: str
    full_strength_classification: str
    disclaimer_id: str
    disclaimer_text: str
    limitations: tuple[str, ...]
    canonical_input_fingerprint: str
    geometry_fingerprint: str
    engineering_fingerprint: str
    application_fingerprint: str


@dataclass(frozen=True, slots=True)
class WIMomentSpliceDesignResult:
    preview: WIMomentSplicePreviewResult
    assembly_status: WIMomentSpliceStatus
    required_check_status: str
    ordinary_pass_allowed: bool
    local_checks: tuple[LocalCheckSummary, ...]
    flange_plate_bodies: tuple[FlangePlateBodyResult, ...]
    flange_bolts: tuple[AsymmetricTwoPlaneBoltResult, ...]
    web_body: object
    web_double_shear: tuple[object, ...]
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
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
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
    return PhysicalQuantity.of(value.magnitude if sign == _ONE else -value.magnitude, value.unit)


def _slice5(request: WIMomentSpliceRequest) -> WIMomentComponentResultants:
    return calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(
            WIMomentSectionInput(
                request.beam.depth,
                request.beam.flange_width,
                request.beam.web_thickness,
                request.beam.flange_thickness,
            ),
            WIMomentActionInput(
                request.actions.axial_force_l,
                request.actions.major_shear_v,
                request.actions.major_moment_t,
                request.actions.minor_shear_t,
                request.actions.minor_moment_v,
                request.actions.torsion_l,
            ),
        )
    )


def _web_request(
    request: WIMomentSpliceRequest,
    web: WIMomentComponentResult,
) -> WebSpliceRequest:
    force = web.wrench.force_lvt
    moment_unit = web.wrench.moment_lvt.t.unit
    analysis_gap = (
        request.beam_end_gap
        if request.beam_end_gap.canonical_magnitude > 0
        else _q("0.000000001", request.source_length_unit)
    )
    return WebSpliceRequest(
        f"{request.request_id}:WEB_ADAPTER",
        request.unit_system,
        request.source_length_unit,
        request.beam,
        analysis_gap,
        request.web_splice_plate,
        request.web_bolt_group,
        request.web_fastener.bolt_diameter,
        request.web_fastener.hole_diameter,
        WebSpliceForce(force.l, force.v, force.t),
        (_q(0, moment_unit), _q(0, moment_unit), _q(0, moment_unit)),
        orchestration_contract_version=WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    )


def _web_demand(
    request: WebSpliceRequest,
    group: WebSpliceGroupId,
    force: WebSpliceVector,
    free_moment_t: PhysicalQuantity,
) -> EccentricDemandResult:
    unit = request.source_length_unit
    moment_unit = free_moment_t.unit
    center = (
        -request.group.centroid_offset.to(unit).magnitude
        if group is WebSpliceGroupId.BEAM_A
        else request.group.centroid_offset.to(unit).magnitude
    )
    geometry_force = WebSpliceVector(
        _q(0, force.l.unit),
        _q(force.v.magnitude if force.v.magnitude != 0 else _ONE, force.v.unit),
        _q(0, force.t.unit),
    )
    mapping = cast(
        MultiRowOrchestrationRequest,
        _layer_resistance_request(
            request,
            group,
            geometry_force,
            "POSITIVE_WEB_SPLICE_PLATE",
            analysis_envelope_only=True,
        ),
    )
    resolved = _resolve(mapping)
    bundle = _execution_bundle(mapping, resolved)
    magnitude = _q((force.l.magnitude**2 + force.v.magnitude**2).sqrt(), force.l.unit)
    with localcontext() as context:
        context.prec = 100
        plan = plan_row_demands(
            resolved.geometry,
            magnitude,
            mapping.row_distribution_basis,
            mapping.provenance,
            connected_materials=(
                ConnectedMaterialPair.FRP_FRP
                if mapping.row_distribution_basis is RowDistributionBasis.ASCE_PRESCRIBED
                else None
            ),
        )
    zeros_m = ExactQuantityVector3D(*(_q(0, moment_unit) for _ in range(3)))
    with localcontext() as context:
        context.prec = 100
        return calculate_eccentric_bolt_group_demand(
            EccentricDemandInput(
                f"STAGE_4_1A_{group.value}_WEB_ACTION",
                f"{group.value}_BEAM_WEB",
                ExactQuantityVector3D(force.l, force.v, force.t),
                zeros_m,
                ExactQuantityVector3D(_q(0, moment_unit), _q(0, moment_unit), free_moment_t),
                ExactQuantityVector3D(*(_q(0, unit) for _ in range(3))),
                ExactInterfaceFrame(
                    group.value,
                    ExactQuantityVector3D(_q(center, unit), _q(0, unit), _q(0, unit)),
                    (_ZERO, _ONE, _ZERO),
                    (_ONE, _ZERO, _ZERO),
                    (_ZERO, _ZERO, -_ONE),
                ),
                bundle.physical_geometry,
                plan,
                resolved.applicability.method_applicability,
                resolved.applicability.qualification,
                (
                    "STAGE_2_5A_DEMAND_ANALYSIS",
                    "STAGE_4_1A_SLICE5_WEB_FREE_MOMENT",
                    f"SIGNED_GROUP:{group.value}",
                ),
            )
        )


def _adapt_web_preview(
    request: WIMomentSpliceRequest,
    slice5: WIMomentComponentResultants,
) -> WebSpliceRC2PreviewResult:
    component = slice5.component(WIMomentRegionId.WEB)
    web_request = _web_request(request, component)
    base = preview_web_splice(web_request)
    if not isinstance(base, WebSpliceRC2PreviewResult):  # pragma: no cover - contract invariant
        raise TypeError("Stage 4.1A requires the Stage 3.6B RC2 preview.")
    force_a = WebSpliceVector(
        component.wrench.force_lvt.l,
        component.wrench.force_lvt.v,
        component.wrench.force_lvt.t,
    )
    force_b = WebSpliceVector(
        *(
            PhysicalQuantity.of(item.magnitude.copy_negate(), item.unit)
            for item in (force_a.l, force_a.v, force_a.t)
        )
    )
    free_a = component.wrench.moment_lvt.t
    free_b = PhysicalQuantity.of(free_a.magnitude.copy_negate(), free_a.unit)
    demand_a = _web_demand(web_request, WebSpliceGroupId.BEAM_A, force_a, free_a)
    demand_b = _web_demand(web_request, WebSpliceGroupId.BEAM_B, force_b, free_b)
    unit = request.source_length_unit
    moment_unit = free_a.unit

    def bind(
        group_id: WebSpliceGroupId,
        force: WebSpliceVector,
        free: PhysicalQuantity,
        demand: EccentricDemandResult,
    ) -> WebSpliceGroupResult:
        old = base.beam_a_group if group_id is WebSpliceGroupId.BEAM_A else base.beam_b_group
        center = old.centroid_l_v_t.l.to(unit).magnitude
        shifted = _cross_offset_force(-center, force, moment_unit, unit)
        with localcontext() as context:
            context.prec = 100
            combined_t = PhysicalQuantity.of(shifted.t.magnitude + free.magnitude, moment_unit)
        moment = WebSpliceVector(shifted.l, shifted.v, combined_t)
        wrench = WebSpliceWrench(
            old.centroid_l_v_t,
            force,
            moment,
            "SLICE5_WEB_FREE_MOMENT+cross(r_J-r_GROUP,F_INTERFACE)",
        )
        layers = _layers(group_id, force, demand, base.symmetry_proof.proof_fingerprint)
        return replace(
            old,
            wrench=wrench,
            demand=demand,
            layer_demands=layers,
            group_fingerprint=_fingerprint((group_id, wrench, demand.result_fingerprint, layers)),
        )

    group_a = bind(WebSpliceGroupId.BEAM_A, force_a, free_a, demand_a)
    group_b = bind(WebSpliceGroupId.BEAM_B, force_b, free_b, demand_b)
    adapted_engineering = _fingerprint(
        (base.engineering_fingerprint, component.wrench, group_a, group_b)
    )
    return replace(
        base,
        beam_a_group=group_a,
        beam_b_group=group_b,
        engineering_fingerprint=adapted_engineering,
        application_fingerprint=_fingerprint((adapted_engineering, base.visualization)),
    )


def _flange_mapping_request(
    request: WIMomentSpliceRequest,
    *,
    group_id: str,
    branch_force: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    line_count: int,
) -> MultiRowOrchestrationRequest | None:
    if branch_force.canonical_magnitude == 0:
        return None
    geometry = request.flange_geometry
    unit = request.source_length_unit
    n_l = geometry.bolts_per_line
    pitch = geometry.longitudinal_pitch.to(unit).magnitude
    span = pitch * Decimal(n_l - 1)
    half_length = geometry.plate_length.to(unit).magnitude / 2
    end = half_length - geometry.group_centroid_distance.to(unit).magnitude - span / 2
    side = width.to(unit).magnitude / 2
    gauge = (
        request.beam.flange_width.to(unit).magnitude - geometry.inner_strip_width.to(unit).magnitude
        if line_count == 2
        else geometry.inner_strip_width.to(unit).magnitude
    )
    row_basis = (
        RowDistributionBasis.ASCE_PRESCRIBED
        if n_l in {2, 3}
        else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE
    )
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_4_1A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    return MultiRowOrchestrationRequest(
        f"{request.request_id}:{group_id}",
        f"stage-4.1a:{group_id}",
        group_id,
        "STAGE_4_1A_SLICE5_FLANGE_BRANCH",
        "Stage 4.1A balanced flange branch mapped to one physical bolt group",
        request.unit_system,
        unit,
        n_l,
        line_count,
        request.flange_fastener.bolt_diameter,
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        geometry.longitudinal_pitch,
        _q(gauge, unit),
        _q(max(end, Decimal("0.000000001")), unit),
        _q(max(end, Decimal("0.000000001")), unit),
        _q(max(side - gauge / 2, Decimal("0.000000001")), unit),
        _q(max(side - gauge / 2, Decimal("0.000000001")), unit),
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
                ThreadStatus(request.flange_fastener.thread_condition),
            ),
        ),
        branch_force,
        _q(0, branch_force.unit),
        "STAGE_4_1A_GROUP_CENTROID",
        row_basis,
        None,
        (),
        MethodProvenance(
            "STAGE_4_1A_STAGE_2_5A_RESOLVED_DEMAND",
            "STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_ENGINEERING_SPECIFICATION_RC1",
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
        single_row_geometry_preview_authorized=n_l == 1,
    )


def _flange_demand(
    request: WIMomentSpliceRequest,
    *,
    flange_id: str,
    beam_id: str,
    branch_id: str,
    strip_id: str | None,
    force: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    line_count: int,
    flange_v: PhysicalQuantity,
) -> FlangeGroupDemand:
    group_id = f"{beam_id}_{flange_id}_{branch_id}" + ("" if strip_id is None else f"_{strip_id}")
    unit = request.source_length_unit
    center_l = request.flange_geometry.group_centroid_distance.to(unit).magnitude * (
        -_ONE if beam_id == "BEAM_A" else _ONE
    )
    center_t = (
        _ZERO
        if strip_id is None
        else (
            request.beam.flange_width.to(unit).magnitude / 2
            - request.flange_geometry.inner_strip_width.to(unit).magnitude / 2
        )
        * (-_ONE if strip_id == "NEGATIVE" else _ONE)
    )
    n_l = request.flange_geometry.bolts_per_line
    pitch = request.flange_geometry.longitudinal_pitch.to(unit).magnitude
    start_l = center_l - pitch * Decimal(n_l - 1) / 2
    line_centers = (
        (center_t,)
        if line_count == 1
        else (
            -(
                request.beam.flange_width.to(unit).magnitude / 2
                - request.flange_geometry.inner_strip_width.to(unit).magnitude / 2
            ),
            request.beam.flange_width.to(unit).magnitude / 2
            - request.flange_geometry.inner_strip_width.to(unit).magnitude / 2,
        )
    )
    coordinates = tuple(
        (_q(start_l + Decimal(row) * pitch, unit), _q(line_t, unit))
        for row in range(n_l)
        for line_t in line_centers
    )
    mapping = _flange_mapping_request(
        request,
        group_id=group_id,
        branch_force=force,
        width=width,
        thickness=thickness,
        line_count=line_count,
    )
    if mapping is None:
        return FlangeGroupDemand(
            group_id,
            flange_id,
            beam_id,
            branch_id,
            strip_id,
            coordinates,
            None,
            (),
            _fingerprint((group_id, force, coordinates, "ZERO_FORCE")),
        )
    resolved = _resolve(mapping)
    bundle = _execution_bundle(mapping, resolved)
    with localcontext() as context:
        context.prec = 100
        plan = plan_row_demands(
            resolved.geometry,
            PhysicalQuantity.of(abs(force.magnitude), force.unit),
            mapping.row_distribution_basis,
            mapping.provenance,
            connected_materials=(
                ConnectedMaterialPair.FRP_FRP
                if mapping.row_distribution_basis is RowDistributionBasis.ASCE_PRESCRIBED
                else None
            ),
        )
    force_unit = force.unit
    moment_unit = Unit.KIP_IN if request.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    zeros_m = ExactQuantityVector3D(*(_q(0, moment_unit) for _ in range(3)))
    with localcontext() as context:
        context.prec = 100
        demand = calculate_eccentric_bolt_group_demand(
            EccentricDemandInput(
                f"{group_id}_ACTION",
                group_id,
                ExactQuantityVector3D(force, _q(0, force_unit), _q(0, force_unit)),
                zeros_m,
                zeros_m,
                ExactQuantityVector3D(_q(center_l, unit), flange_v.to(unit), _q(center_t, unit)),
                ExactInterfaceFrame(
                    group_id,
                    ExactQuantityVector3D(
                        _q(center_l, unit), flange_v.to(unit), _q(center_t, unit)
                    ),
                    (_ONE, _ZERO, _ZERO),
                    (_ZERO, _ZERO, _ONE),
                    (_ZERO, -_ONE, _ZERO),
                ),
                bundle.physical_geometry,
                plan,
                resolved.applicability.method_applicability,
                resolved.applicability.qualification,
                (
                    "STAGE_2_5A_DEMAND_ANALYSIS",
                    "STAGE_4_1A_FLANGE_BRANCH_GROUP",
                    group_id,
                ),
            )
        )
    by_id: dict[str, FlangePlaneDemand] = {}
    for scenario in demand.scenarios:
        for item in scenario.per_bolt:
            with localcontext() as context:
                context.prec = 100
                signed_direct = PhysicalQuantity.of(force.magnitude * item.direct_share, force.unit)
            record = FlangePlaneDemand(
                signed_direct,
                _q(0, force.unit),
                demand.result_fingerprint,
                group_id,
                item.bolt_id,
            )
            by_id[item.bolt_id] = record
    plane_demands = tuple(by_id[key] for key in sorted(by_id))
    return FlangeGroupDemand(
        group_id,
        flange_id,
        beam_id,
        branch_id,
        strip_id,
        coordinates,
        demand,
        plane_demands,
        _fingerprint((group_id, force, coordinates, demand.result_fingerprint, plane_demands)),
    )


def _branch_geometry(
    request: WIMomentSpliceRequest,
    slice5: WIMomentComponentResultants,
) -> tuple[FlangeBranchDecomposition, FlangeBranchDecomposition]:
    d = request.beam.depth.to(Unit.IN).magnitude
    tf = request.beam.flange_thickness.to(Unit.IN).magnitude
    tp = request.flange_geometry.plate_thickness.to(Unit.IN).magnitude
    top = slice5.component(WIMomentRegionId.TOP_FLANGE)
    bottom = slice5.component(WIMomentRegionId.BOTTOM_FLANGE)
    return (
        decompose_flange_wrench(
            flange_id="TOP",
            flange_reference_v=_q((d - tf) / 2, Unit.IN),
            outer_reference_v=_q(d / 2 + tp / 2, Unit.IN),
            inner_reference_v=_q(d / 2 - tf - tp / 2, Unit.IN),
            flange_force=top.wrench.force_lvt.l,
            flange_local_moment=top.wrench.moment_lvt.t,
        ),
        decompose_flange_wrench(
            flange_id="BOTTOM",
            flange_reference_v=_q(-(d - tf) / 2, Unit.IN),
            outer_reference_v=_q(-d / 2 - tp / 2, Unit.IN),
            inner_reference_v=_q(-d / 2 + tf + tp / 2, Unit.IN),
            flange_force=bottom.wrench.force_lvt.l,
            flange_local_moment=bottom.wrench.moment_lvt.t,
        ),
    )


def _physical_groups(
    request: WIMomentSpliceRequest,
    top: FlangeBranchDecomposition,
    bottom: FlangeBranchDecomposition,
) -> tuple[FlangeGroupDemand, ...]:
    groups: list[FlangeGroupDemand] = []
    width = request.beam.flange_width
    strip = request.flange_geometry.inner_strip_width
    thickness = request.flange_geometry.plate_thickness
    for branch in (top, bottom):
        for beam_id, sign in (("BEAM_A", _ONE), ("BEAM_B", -_ONE)):
            outer = _signed(branch.outer_force, sign)
            each = _signed(branch.inner_negative_force, sign)
            groups.append(
                _flange_demand(
                    request,
                    flange_id=branch.flange_id,
                    beam_id=beam_id,
                    branch_id="OUTER",
                    strip_id=None,
                    force=outer,
                    width=width,
                    thickness=thickness,
                    line_count=2,
                    flange_v=branch.outer_reference_v,
                )
            )
            for strip_id in ("NEGATIVE", "POSITIVE"):
                groups.append(
                    _flange_demand(
                        request,
                        flange_id=branch.flange_id,
                        beam_id=beam_id,
                        branch_id="INNER",
                        strip_id=strip_id,
                        force=each,
                        width=strip,
                        thickness=thickness,
                        line_count=1,
                        flange_v=branch.inner_reference_v,
                    )
                )
    return tuple(groups)


def _geometry_reasons(
    request: WIMomentSpliceRequest,
    web: WebSpliceRC2PreviewResult,
    groups: tuple[FlangeGroupDemand, ...],
) -> tuple[str, ...]:
    unit = request.source_length_unit
    reasons = list(web.geometry_invalid_reasons)
    if request.beam_end_gap.canonical_magnitude <= 0:
        reasons.append("POSITIVE_BEAM_END_GAP_REQUIRED")
    geometry = request.flange_geometry
    if geometry.outer_plate_count_per_flange != 1 or geometry.inner_strip_count_per_flange != 2:
        reasons.append("BALANCED_OUTER_PLUS_TWO_INNER_PLATES_REQUIRED")
    if not geometry.locked_top_bottom_identical:
        reasons.append("IDENTICAL_TOP_BOTTOM_FLANGE_TOPOLOGY_REQUIRED")
    if not geometry.locked_inner_symmetric:
        reasons.append("TWO_SYMMETRIC_INNER_STRIPS_REQUIRED")
    clearance = (
        request.beam.flange_width.to(unit).magnitude / 2
        - geometry.inner_strip_width.to(unit).magnitude
        - request.beam.web_thickness.to(unit).magnitude / 2
    )
    if clearance < 0:
        reasons.append("INNER_STRIP_WEB_OVERLAP")
    radius = request.flange_fastener.hole_diameter.to(unit).magnitude / 2
    half_outer = request.beam.flange_width.to(unit).magnitude / 2
    half_strip = geometry.inner_strip_width.to(unit).magnitude / 2
    half_plate_l = geometry.plate_length.to(unit).magnitude / 2
    gap = request.beam_end_gap.to(unit).magnitude
    for group in groups:
        for l_coord, t_coord in group.physical_coordinates_l_t:
            if abs(l_coord.to(unit).magnitude) + radius > half_plate_l:
                reasons.append("FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATE")
            if group.branch_id == "OUTER" and abs(t_coord.to(unit).magnitude) + radius > half_outer:
                reasons.append("FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_OUTER_PLATE")
            if group.branch_id == "INNER" and radius > half_strip:
                reasons.append("FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_INNER_STRIP")
            if (
                abs(t_coord.to(unit).magnitude) - radius
                < request.beam.web_thickness.to(unit).magnitude / 2
            ):
                reasons.append("FLANGE_HOLE_WEB_COLLISION")
            if group.beam_id == "BEAM_A" and l_coord.to(unit).magnitude + radius > -gap / 2:
                reasons.append("FLANGE_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END")
            if group.beam_id == "BEAM_B" and l_coord.to(unit).magnitude - radius < gap / 2:
                reasons.append("FLANGE_HOLE_NOT_CONTAINED_AFTER_BEAM_B_END")
    if geometry.longitudinal_pitch < request.flange_fastener.hole_diameter:
        reasons.append("FLANGE_BOLT_PITCH_INSUFFICIENT")
    clear = _flange_clear_body(request)
    if clear.canonical_magnitude <= 0:
        reasons.append("FLANGE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS")
    return tuple(dict.fromkeys(reasons))


def _flange_clear_body(request: WIMomentSpliceRequest) -> PhysicalQuantity:
    unit = request.source_length_unit
    nearest = (
        request.flange_geometry.group_centroid_distance.to(unit).magnitude
        - request.flange_geometry.longitudinal_pitch.to(unit).magnitude
        * Decimal(request.flange_geometry.bolts_per_line - 1)
        / 2
    )
    radius = request.flange_fastener.hole_diameter.to(unit).magnitude / 2
    return _q(2 * (nearest - radius), unit)


def _equilibrium(
    request: WIMomentSpliceRequest,
    slice5: WIMomentComponentResultants,
    top: FlangeBranchDecomposition,
    bottom: FlangeBranchDecomposition,
) -> MomentSpliceEquilibrium:
    web = slice5.component(WIMomentRegionId.WEB)
    force_unit = request.actions.axial_force_l.unit
    moment_unit = request.actions.major_moment_t.unit
    with localcontext() as context:
        context.prec = 100
        axial_residual = _q(
            sum(
                (
                    item.to(force_unit).magnitude
                    for item in (top.flange_force, web.wrench.force_lvt.l, bottom.flange_force)
                ),
                _ZERO,
            )
            - request.actions.axial_force_l.magnitude,
            force_unit,
        )
        shear_residual = _q(
            web.wrench.force_lvt.v.to(force_unit).magnitude
            - request.actions.major_shear_v.to(force_unit).magnitude,
            force_unit,
        )
        moment_residual = _q(
            sum(
                (
                    item.to(moment_unit).magnitude
                    for item in (top.global_moment, web.global_major_moment, bottom.global_moment)
                ),
                _ZERO,
            )
            - request.actions.major_moment_t.magnitude,
            moment_unit,
        )
    slice_exact = (
        slice5.equilibrium.axial_equilibrium_exact
        and slice5.equilibrium.shear_equilibrium_exact
        and slice5.equilibrium.moment_equilibrium_exact
    )
    branch_exact = (
        top.exact_force_equilibrium
        and top.exact_local_moment_equilibrium
        and bottom.exact_force_equilibrium
        and bottom.exact_local_moment_equilibrium
    )
    if slice_exact and branch_exact:
        axial_residual = _q(0, force_unit)
        shear_residual = _q(0, force_unit)
        moment_residual = _q(0, moment_unit)
    whole = slice_exact and branch_exact
    partial = MomentSpliceEquilibrium(
        axial_residual,
        shear_residual,
        moment_residual,
        slice_exact,
        top.exact_force_equilibrium and top.exact_local_moment_equilibrium,
        bottom.exact_force_equilibrium and bottom.exact_local_moment_equilibrium,
        whole,
        True,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def _visualization(
    request: WIMomentSpliceRequest,
    web: WebSpliceRC2PreviewResult,
    groups: tuple[FlangeGroupDemand, ...],
) -> MomentSpliceVisualization:
    unit = request.source_length_unit
    boxes = list(web.visualization.boxes)
    regions = list(web.visualization.material_regions)
    plate_l = request.flange_geometry.plate_length.to(unit).magnitude
    plate_t = request.flange_geometry.plate_thickness.to(unit).magnitude
    width = request.beam.flange_width.to(unit).magnitude
    strip_width = request.flange_geometry.inner_strip_width.to(unit).magnitude
    strip_center = width / 2 - strip_width / 2
    d = request.beam.depth.to(unit).magnitude
    tf = request.beam.flange_thickness.to(unit).magnitude
    positions = (
        ("TOP_OUTER_FLANGE_SPLICE_PLATE", "TOP_OUTER", d / 2 + plate_t / 2, _ZERO, width),
        (
            "TOP_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
            "TOP_INNER",
            d / 2 - tf - plate_t / 2,
            -strip_center,
            strip_width,
        ),
        (
            "TOP_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
            "TOP_INNER",
            d / 2 - tf - plate_t / 2,
            strip_center,
            strip_width,
        ),
        ("BOTTOM_OUTER_FLANGE_SPLICE_PLATE", "BOTTOM_OUTER", -d / 2 - plate_t / 2, _ZERO, width),
        (
            "BOTTOM_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
            "BOTTOM_INNER",
            -d / 2 + tf + plate_t / 2,
            -strip_center,
            strip_width,
        ),
        (
            "BOTTOM_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
            "BOTTOM_INNER",
            -d / 2 + tf + plate_t / 2,
            strip_center,
            strip_width,
        ),
    )
    for component, role, v, t, plate_width in positions:
        boxes.append(
            WebSpliceBox(
                component,
                f"FRP_FLANGE_SPLICE_PLATE_{role}",
                _vector((_ZERO, v, t), unit),
                _vector((plate_l, plate_t, plate_width), unit),
            )
        )
        top = component.startswith("TOP")
        regions.append(
            WebSpliceMaterialRegion(
                component,
                component,
                (_ONE, _ZERO, _ZERO),
                (_ZERO, _ZERO, _ONE if top else -_ONE),
                (_ZERO, -_ONE if top else _ONE, _ZERO),
            )
        )
    bolts: list[MomentSpliceBolt] = [
        MomentSpliceBolt(
            item.bolt_id,
            item.group_id.value,
            item.center_l_v_t,
            item.path_layers,
            item.stack_start_l_v_t,
            item.stack_end_l_v_t,
            item.shank_length,
            item.head_location,
            item.nut_location,
            item.washer_count,
            item.internal_hardware_count,
        )
        for item in web.visualization.bolts
    ]
    group_lookup = {group.group_id: group for group in groups}
    for flange_id, v_center in (("TOP", (d - tf) / 2), ("BOTTOM", -(d - tf) / 2)):
        outer_v = d / 2 + plate_t if flange_id == "TOP" else -d / 2 - plate_t
        inner_v = d / 2 - tf - plate_t if flange_id == "TOP" else -d / 2 + tf + plate_t
        shank = _q(tf + 2 * plate_t, unit)
        for beam_id in ("BEAM_A", "BEAM_B"):
            outer_group = group_lookup[f"{beam_id}_{flange_id}_OUTER"]
            inner_groups = {
                strip: group_lookup[f"{beam_id}_{flange_id}_INNER_{strip}"]
                for strip in ("NEGATIVE", "POSITIVE")
            }
            for index, (l_coord, t_coord) in enumerate(outer_group.physical_coordinates_l_t):
                strip = "NEGATIVE" if t_coord.to(unit).magnitude < 0 else "POSITIVE"
                inner_id = f"{flange_id}_{strip}_INNER_FLANGE_SPLICE_PLATE"
                outer_id = f"{flange_id}_OUTER_FLANGE_SPLICE_PLATE"
                path = (outer_id, f"{beam_id}_{flange_id}_FLANGE", inner_id)
                bolt_id = f"{beam_id}_{flange_id}_B{index + 1}"
                bolts.append(
                    MomentSpliceBolt(
                        bolt_id,
                        outer_group.group_id,
                        _vector(
                            (l_coord.to(unit).magnitude, v_center, t_coord.to(unit).magnitude), unit
                        ),
                        path,
                        _vector(
                            (l_coord.to(unit).magnitude, outer_v, t_coord.to(unit).magnitude), unit
                        ),
                        _vector(
                            (l_coord.to(unit).magnitude, inner_v, t_coord.to(unit).magnitude), unit
                        ),
                        shank,
                        "EXTERIOR_OUTER_FLANGE_SPLICE_PLATE_FACE",
                        "EXTERIOR_INNER_FLANGE_SPLICE_PLATE_FACE",
                    )
                )
                if strip not in inner_groups:  # pragma: no cover - topology invariant
                    raise ValueError("A flange bolt lacks its corresponding inner strip.")
    force = request.actions
    return MomentSpliceVisualization(
        ("L_S", "V_S", "T_S"),
        _zero_vector(unit),
        (
            _q(-request.beam_end_gap.to(unit).magnitude / 2, unit),
            _q(request.beam_end_gap.to(unit).magnitude / 2, unit),
        ),
        tuple(boxes),
        tuple(bolts),
        request.web_fastener.bolt_diameter,
        request.web_fastener.hole_diameter,
        request.flange_fastener.bolt_diameter,
        request.flange_fastener.hole_diameter,
        tuple(regions),
        _zero_vector(unit),
        WebSpliceVector(force.axial_force_l, force.major_shear_v, force.minor_shear_t),
        WebSpliceVector(force.torsion_l, force.minor_moment_v, force.major_moment_t),
    )


def preview_wi_moment_splice(request: WIMomentSpliceRequest) -> WIMomentSplicePreviewResult:
    if not isinstance(request, WIMomentSpliceRequest):
        raise TypeError("request must be WIMomentSpliceRequest.")
    slice5 = _slice5(request)
    if not (
        slice5.equilibrium.axial_equilibrium_exact
        and slice5.equilibrium.shear_equilibrium_exact
        and slice5.equilibrium.moment_equilibrium_exact
    ):
        raise ValueError("SLICE5_EXACT_COMPONENT_EQUILIBRIUM_REQUIRED")
    top, bottom = _branch_geometry(request, slice5)
    web = _adapt_web_preview(request, slice5)
    groups = _physical_groups(request, top, bottom)
    reasons = _geometry_reasons(request, web, groups)
    equilibrium = _equilibrium(request, slice5, top, bottom)
    if not equilibrium.whole_joint_exact:
        raise ValueError("STAGE_4_1A_EXACT_WHOLE_JOINT_EQUILIBRIUM_REQUIRED")
    visualization = _visualization(request, web, groups)
    geometry_payload = (
        request.beam,
        request.beam_end_gap,
        request.web_splice_plate,
        request.web_bolt_group,
        request.flange_geometry,
        request.web_fastener.bolt_diameter,
        request.web_fastener.hole_diameter,
        request.flange_fastener.bolt_diameter,
        request.flange_fastener.hole_diameter,
        visualization.boxes,
        visualization.bolts,
        visualization.material_regions,
    )
    engineering_payload = (
        WI_MOMENT_SPLICE_CONTRACT_VERSION,
        geometry_payload,
        request.actions,
        request.web_fastener,
        request.flange_fastener,
        slice5.result_fingerprint,
        top,
        bottom,
        web.engineering_fingerprint,
        groups,
        equilibrium,
        WI_MOMENT_SPLICE_DISCLAIMER_ID,
        WI_MOMENT_SPLICE_QUALIFICATION,
    )
    valid = not reasons
    return WIMomentSplicePreviewResult(
        request.request_id,
        WI_MOMENT_SPLICE_PRODUCT_ID,
        WI_MOMENT_SPLICE_CONTRACT_VERSION,
        WI_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION,
        WIMomentSpliceStatus.VALID if valid else WIMomentSpliceStatus.INVALID_GEOMETRY,
        reasons,
        WIMomentSpliceStatus.NOT_EVALUATED if valid else WIMomentSpliceStatus.INVALID_GEOMETRY,
        False,
        False,
        valid
        and all(
            group.demand is None
            or group.demand.availability is DemandAnalysisAvailability.CALCULATED
            for group in groups
        )
        and web.design_check_ready,
        slice5,
        top,
        bottom,
        web,
        groups,
        _flange_clear_body(request),
        request.beam.flange_thickness / 2,
        equilibrium,
        visualization,
        True,
        WI_MOMENT_SPLICE_QUALIFICATION,
        "NOT_EVALUATED",
        "NOT_EVALUATED",
        "NOT_EVALUATED",
        WI_MOMENT_SPLICE_DISCLAIMER_ID,
        WI_MOMENT_SPLICE_DISCLAIMER,
        (
            "BOLT_AXIS_TENSION_AND_PRYING_NOT_EVALUATED",
            "UNEQUAL_PLANE_SECONDARY_BOLT_BENDING_REQUIRES_ENGINEERING_REVIEW",
            "MOMENT_CONNECTION_STIFFNESS_ROTATION_AND_FULL_STRENGTH_NOT_EVALUATED",
        ),
        _fingerprint(
            (
                WI_MOMENT_SPLICE_CONTRACT_VERSION,
                geometry_payload,
                request.actions,
                request.web_fastener,
                request.flange_fastener,
            )
        ),
        _fingerprint(geometry_payload),
        _fingerprint(engineering_payload),
        _fingerprint((engineering_payload, visualization)),
    )


def _local_summary(
    request: WIMomentSpliceRequest,
    group: FlangeGroupDemand,
    *,
    component_id: str,
    force: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    line_count: int,
) -> LocalCheckSummary:
    if group.demand is None or force.canonical_magnitude == 0:
        partial = LocalCheckSummary(component_id, (), (), (), (), True, "")
        return replace(partial, result_fingerprint=_fingerprint(partial))
    mapping = cast(
        MultiRowOrchestrationRequest,
        _flange_mapping_request(
            request,
            group_id=group.group_id,
            branch_force=force,
            width=width,
            thickness=thickness,
            line_count=line_count,
        ),
    )
    allocations = tuple(
        LayerInPlaneDemandAllocation(
            bolt.bolt_id,
            group.group_id,
            _ONE,
            "STAGE_4_1A_EXACT_LAYER_ALLOCATION",
            group.demand.result_fingerprint,
        )
        for scenario in group.demand.scenarios
        for bolt in scenario.per_bolt
    )
    allocations = tuple({item.bolt_id: item for item in allocations}.values())
    try:
        response = evaluate_multirow_connection_with_resolved_demand(
            mapping,
            group.demand,
            allocations,
        )
    except ValueError as error:
        partial = LocalCheckSummary(
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
    partial = LocalCheckSummary(
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
    request: WIMomentSpliceRequest,
    preview: WIMomentSplicePreviewResult,
) -> WebSpliceBodyInteractionResult:
    from frp_master_connection.application.mat1_scope import current_scope

    scope = current_scope()
    if scope is not None and scope.material("POSITIVE_WEB_SPLICE_PLATE") != scope.material(
        "NEGATIVE_WEB_SPLICE_PLATE"
    ):
        raise ValueError("MAT1_SYMMETRIC_WEB_SPLICE_PLATE_MATERIALS_MUST_MATCH")
    web_component = preview.slice5_result.component(WIMomentRegionId.WEB)
    web_request = _web_request(request, web_component)
    force = web_component.wrench.force_lvt
    free_moment = web_component.wrench.moment_lvt.t
    plan = preview.web_preview.clear_body_plan
    actions = tuple(
        # Internal pair moment retains both the Slice 5 free moment and -xV variation.
        WebSpliceCriticalSectionAction(
            section,
            coordinate,
            force.l,
            force.v,
            PhysicalQuantity.of(
                free_moment.magnitude
                - coordinate.to(request.source_length_unit).magnitude * force.v.magnitude,
                free_moment.unit,
            ),
        )
        for section, coordinate in (
            (plan.critical_section_ids[0], plan.left_clear_boundary),
            (plan.critical_section_ids[1], _q(0, request.source_length_unit)),
            (plan.critical_section_ids[2], plan.right_clear_boundary),
        )
    )
    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_4_1A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    from frp_master_connection.application.mat1_scope import time_category_for_case

    time_effect = select_time_effect_factor(
        time_category_for_case(TimeEffectCategory.WIND_TORNADO_SEISMIC)
    )
    thickness = web_request.splice_plate.thickness
    height = web_request.splice_plate.height
    length = plan.clear_body_length
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
        actions=actions,
        symmetry_proven=True,
        tension_strength=tension,
        compression_strength=compression,
        shear_strength=shear,
    )


def _flange_bolt_results(
    request: WIMomentSpliceRequest,
    preview: WIMomentSplicePreviewResult,
) -> tuple[AsymmetricTwoPlaneBoltResult, ...]:
    groups = {group.group_id: group for group in preview.flange_group_demands}
    results: list[AsymmetricTwoPlaneBoltResult] = []
    for bolt in preview.visualization.bolts:
        if "FLANGE" not in bolt.path_layers[1]:
            continue
        outer = groups[bolt.group_id]
        strip = "NEGATIVE" if bolt.center_l_v_t.t.canonical_magnitude < 0 else "POSITIVE"
        inner_id = outer.group_id.replace("_OUTER", f"_INNER_{strip}")
        inner = groups[inner_id]
        index = int(bolt.bolt_id.rsplit("B", 1)[1]) - 1
        inner_index = index // 2
        zero = FlangePlaneDemand(
            _q(0, request.actions.axial_force_l.unit),
            _q(0, request.actions.axial_force_l.unit),
            _fingerprint((bolt.bolt_id, "ZERO_FLANGE_PLANE_DEMAND")),
            bolt.group_id,
            bolt.bolt_id,
        )
        outer_plane = (
            zero if not outer.per_bolt_plane_demands else outer.per_bolt_plane_demands[index]
        )
        inner_plane = (
            zero if not inner.per_bolt_plane_demands else inner.per_bolt_plane_demands[inner_index]
        )
        results.append(
            evaluate_asymmetric_two_plane_bolt(
                bolt_id=bolt.bolt_id,
                physical_path=bolt.path_layers,
                outer_plane=outer_plane,
                inner_plane=inner_plane,
                diameter=request.flange_fastener.bolt_diameter,
                thread_condition=request.flange_fastener.thread_condition,
                source_authority_id=request.flange_fastener.source_authority_id,
                nominal_shear_stress=request.flange_fastener.nominal_shear_stress,
            )
        )
    return tuple(results)


def design_check_wi_moment_splice(request: WIMomentSpliceRequest) -> WIMomentSpliceDesignResult:
    preview = preview_wi_moment_splice(request)
    if preview.geometry_invalid_reasons:
        return WIMomentSpliceDesignResult(
            preview,
            WIMomentSpliceStatus.INVALID_GEOMETRY,
            "NOT_EVALUATED",
            False,
            (),
            (),
            (),
            None,
            (),
            ("INVALID_GEOMETRY",),
            (),
            None,
            None,
            WI_MOMENT_SPLICE_DISCLAIMER_ID,
            WI_MOMENT_SPLICE_DISCLAIMER,
            True,
            _fingerprint((preview.application_fingerprint, "INVALID_GEOMETRY")),
        )
    top, bottom = preview.top_flange, preview.bottom_flange
    groups = {group.group_id: group for group in preview.flange_group_demands}
    local: list[LocalCheckSummary] = []
    width = request.beam.flange_width
    strip_width = request.flange_geometry.inner_strip_width
    plate_t = request.flange_geometry.plate_thickness
    face_t = request.beam.flange_thickness / 2
    for branch in (top, bottom):
        for beam_id, sign in (("BEAM_A", _ONE), ("BEAM_B", -_ONE)):
            outer_force = _signed(branch.outer_force, sign)
            inner_total = _signed(branch.inner_total_force, sign)
            outer = groups[f"{beam_id}_{branch.flange_id}_OUTER"]
            local.append(
                _local_summary(
                    request,
                    outer,
                    component_id=f"{outer.group_id}:OUTER_PLATE",
                    force=outer_force,
                    width=width,
                    thickness=plate_t,
                    line_count=2,
                )
            )
            local.append(
                _local_summary(
                    request,
                    outer,
                    component_id=f"{outer.group_id}:BEAM_FLANGE_OUTER_FACE:{WI_MOMENT_SPLICE_SUBLAYER_METHOD}",
                    force=outer_force,
                    width=width,
                    thickness=face_t,
                    line_count=2,
                )
            )
            face_inner = _flange_demand(
                request,
                flange_id=branch.flange_id,
                beam_id=beam_id,
                branch_id="FACE_INNER",
                strip_id=None,
                force=inner_total,
                width=width,
                thickness=face_t,
                line_count=2,
                flange_v=branch.inner_reference_v,
            )
            local.append(
                _local_summary(
                    request,
                    face_inner,
                    component_id=f"{beam_id}_{branch.flange_id}:BEAM_FLANGE_INNER_FACE:{WI_MOMENT_SPLICE_SUBLAYER_METHOD}",
                    force=inner_total,
                    width=width,
                    thickness=face_t,
                    line_count=2,
                )
            )
            for strip in ("NEGATIVE", "POSITIVE"):
                inner = groups[f"{beam_id}_{branch.flange_id}_INNER_{strip}"]
                force = _signed(branch.inner_negative_force, sign)
                local.append(
                    _local_summary(
                        request,
                        inner,
                        component_id=f"{inner.group_id}:INNER_PLATE",
                        force=force,
                        width=strip_width,
                        thickness=plate_t,
                        line_count=1,
                    )
                )
    web_request = _web_request(request, preview.slice5_result.component(WIMomentRegionId.WEB))
    web_checks, web_failures, web_warnings, web_fingerprints = _evaluate_supported_local_resistance(
        web_request,
        preview.web_preview,
    )
    web_local = LocalCheckSummary(
        "WEB_SUBSYSTEM",
        web_checks,
        web_failures,
        web_warnings,
        web_fingerprints,
        False,
        "",
    )
    local.append(replace(web_local, result_fingerprint=_fingerprint(web_local)))
    clear = preview.flange_clear_body_length
    bodies = tuple(
        evaluate_flange_plate_body(
            component_id=component,
            signed_force=force,
            width=body_width,
            thickness=plate_t,
            clear_body_length=clear,
            material_snapshot=material_for_owner(component, create_locked_ice_material_snapshot()),
            time_effect_category=time_category_for_case(TimeEffectCategory.WIND_TORNADO_SEISMIC),
        )
        for branch in (top, bottom)
        for component, force, body_width in (
            (f"{branch.flange_id}_OUTER_FLANGE_SPLICE_PLATE", branch.outer_force, width),
            (
                f"{branch.flange_id}_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
                branch.inner_negative_force,
                strip_width,
            ),
            (
                f"{branch.flange_id}_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
                branch.inner_positive_force,
                strip_width,
            ),
        )
    )
    web_body = _web_body(request, preview)
    web_bolts = _evaluate_double_shear(web_request, preview.web_preview)
    flange_bolts = _flange_bolt_results(request, preview)
    failures = tuple(
        dict.fromkeys(
            [item for summary in local for item in summary.failed_check_ids]
            + [
                f"FLANGE_BODY:{item.component_id}"
                for item in bodies
                if item.status is FlangeBodyStatus.FAIL
            ]
            + (["WEB_BODY"] if web_body.status is RationalBodyStatus.FAIL_RATIONAL_METHOD else [])
            + [
                f"FLANGE_BOLT:{item.bolt_id}"
                for item in flange_bolts
                if item.status is AsymmetricBoltStatus.FAIL
            ]
            + [
                f"WEB_BOLT:{item.bolt_id}"
                for item in web_bolts
                if item.status is DoubleShearStatus.FAIL
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
                if item.status is DoubleShearStatus.NOT_EVALUATED
            ]
            + (["WEB_BODY"] if web_body.status is RationalBodyStatus.NOT_EVALUATED else [])
        )
    )
    status = (
        WIMomentSpliceStatus.FAIL
        if failures
        else WIMomentSpliceStatus.NOT_EVALUATED
        if unavailable
        else WIMomentSpliceStatus.PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED
    )
    numeric: list[tuple[str, Decimal]] = [
        (f"FLANGE_BODY:{item.component_id}", item.utilization)
        for item in bodies
        if item.utilization is not None
    ] + [
        (f"FLANGE_BOLT:{item.bolt_id}", item.governing_utilization)
        for item in flange_bolts
        if item.governing_utilization is not None
    ]
    if web_body.rational_utilization is not None:
        numeric.append(("WEB_BODY", web_body.rational_utilization))
    governing = max(numeric, key=lambda item: item[1]) if numeric else None
    payload = (
        preview.application_fingerprint,
        status,
        tuple(local),
        bodies,
        web_body.result_fingerprint,
        tuple(item.result_fingerprint for item in web_bolts),
        flange_bolts,
        failures,
        unavailable,
        WI_MOMENT_SPLICE_DISCLAIMER_ID,
    )
    return WIMomentSpliceDesignResult(
        preview,
        status,
        status.value,
        False,
        tuple(local),
        bodies,
        flange_bolts,
        web_body,
        web_bolts,
        failures,
        unavailable,
        None if governing is None else governing[1],
        None if governing is None else governing[0],
        WI_MOMENT_SPLICE_DISCLAIMER_ID,
        WI_MOMENT_SPLICE_DISCLAIMER,
        True,
        _fingerprint(payload),
    )


__all__ = (
    "WI_MOMENT_SPLICE_PREVIEW_SCHEMA_VERSION",
    "WI_MOMENT_SPLICE_RESULT_SCHEMA_VERSION",
    "FlangeGroupDemand",
    "LocalCheckSummary",
    "MomentSpliceBolt",
    "MomentSpliceEquilibrium",
    "MomentSpliceVisualization",
    "WIMomentSpliceDesignResult",
    "WIMomentSplicePreviewResult",
    "design_check_wi_moment_splice",
    "preview_wi_moment_splice",
)
