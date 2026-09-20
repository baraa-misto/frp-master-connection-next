"""Thin-wall DCTN adapters; all resistance equations execute in frozen natives."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.calculation.angle_connector_core import exact_decimal
from frp_master_connection.calculation.dctn_sources import DCTNMaterialSource
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    evaluate_dctn_bearing,
    local_lap_factor,
)
from frp_master_connection.calculation.equations import (
    adjust_frp_property,
    cleavage_resistance,
    net_tension_resistance,
    pin_bearing_resistance,
    shear_out_resistance,
)
from frp_master_connection.calculation.inputs import PultrudedElementForm
from frp_master_connection.calculation.multirow import (
    InterrowShearOutMethod,
    MaterialDirection,
    PlanAvailability,
)
from frp_master_connection.calculation.multirow_engine import resolve_multirow_end_distances
from frp_master_connection.calculation.multirow_equations import (
    BlockShearEccentricityClassification,
    BlockShearEquation,
    block_shear_resistance,
    classify_block_shear_eccentricity,
    compare_resistance,
    constant_pitch_factor,
    interrow_shear_out_resistance,
    simplified_first_row_resistance,
)
from frp_master_connection.calculation.properties import FRPPropertyKind, ThreadStatus
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.dctn_geometry import DCTNPlanePlan
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, DCTNRequest


@dataclass(frozen=True, slots=True)
class DCTNLocalEvaluation:
    checks: tuple[DCTNRequiredCheck, ...]
    reasons: tuple[str, ...]


def exact_force_sum(values: tuple[PhysicalQuantity, ...]) -> PhysicalQuantity:
    return PhysicalQuantity.of(
        exact_decimal(sum((Fraction(v.canonical_magnitude) for v in values), Fraction(0))), Unit.N
    )


def numerical_check(
    identity: str,
    owner: str,
    demand: PhysicalQuantity,
    resistance: PhysicalQuantity,
    trace: object,
    source: str,
) -> DCTNRequiredCheck:
    comparison = compare_resistance(demand, resistance)
    return DCTNRequiredCheck(
        identity, owner, comparison.numerical_comparison.value, demand, resistance, trace, source
    )


def evaluate_native_dctn_plane(
    request: DCTNRequest,
    plan: DCTNPlanePlan,
    source: DCTNMaterialSource,
    hole_demands: tuple[tuple[str, PhysicalQuantity], ...],
) -> DCTNLocalEvaluation:
    """Evaluate supported actual-plane checks without qualifying missing mechanisms."""
    reasons: list[str] = list(plan.reasons)
    kinds = (
        FRPPropertyKind.FBR_L
        if plan.material_direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FBR_T,
        FRPPropertyKind.FT_L
        if plan.material_direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FT_T,
        FRPPropertyKind.FSH_LT,
    )
    properties = tuple(
        next((p for p in source.material.properties if p.kind is kind), None) for kind in kinds
    )
    bearing, tension, shear = properties
    if bearing is None or tension is None or shear is None:
        return DCTNLocalEvaluation((), ("DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED",))
    if any(not p.use_in_chapter_8_equations for p in (bearing, tension, shear)):
        return DCTNLocalEvaluation((), ("DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED",))
    if any(
        p.qualification_status is not QualificationStatus.QUALIFIED
        for p in (bearing, tension, shear)
    ):
        reasons.append("DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED")
    t = adjust_frp_property(
        tension.kind, tension.value, tension.qualification_status, source.factors
    )
    s = adjust_frp_property(shear.kind, shear.value, shear.qualification_status, source.factors)
    b = adjust_frp_property(
        bearing.kind, bearing.value, bearing.qualification_status, source.factors
    )
    unit = request.length_unit
    ends = resolve_multirow_end_distances(plan.geometry, unit)
    pitches = ends.physical_pitches
    c_delta = (
        constant_pitch_factor(pitches, request.fastener.diameter).pitch_factor_c_delta
        if pitches
        else Decimal(1)
    )
    lap = local_lap_factor(plan.incoming_form)
    factors = {"c_delta": c_delta, "c_lap": lap, "lambda_factor": source.lambda_factor}
    multi_factors = {
        "pitch_factor_c_delta": c_delta,
        "lap_factor_c_lap": lap,
        "time_effect_factor_lambda": source.lambda_factor,
    }
    thread = ThreadStatus.EXCLUDED if request.fastener.threads_excluded else ThreadStatus.INCLUDED
    lookup = dict(hole_demands)
    if len(lookup) != len(hole_demands) or set(lookup) != {b.id for b in plan.geometry.group.bolts}:
        raise ValueError("DCTN local demand must cover the actual physical hole set exactly")
    checks: list[DCTNRequiredCheck] = []
    for hole in plan.geometry.group.bolts:
        result = evaluate_dctn_bearing(
            owner_id=plan.owner_id,
            bolt_id=hole.id,
            incoming_form=plan.incoming_form,
            designated_rhs_wall=plan.incoming_form is DCTNForm.RHS
            and plan.owner_id == plan.member_id,
            thickness=plan.thickness,
            diameter=request.fastener.diameter,
            demand=lookup[hole.id],
            characteristic=bearing.value,
            property_kind=bearing.kind,
            qualification=bearing.qualification_status,
            factors=source.factors,
            thread=thread,
            c_delta=c_delta,
            lambda_factor=source.lambda_factor,
        )
        checks.append(
            numerical_check(
                "PIN_BEARING:" + hole.id,
                plan.owner_id,
                lookup[hole.id],
                result.native_trace.factor_trace.design_resistance,
                result,
                source.reference,
            )
        )
    first = plan.first_row
    if plan.reasons:
        # Native C3 direction/bearing remains usable for oblique members; only
        # the projected rectangular rupture-path plan remains unqualified.
        return DCTNLocalEvaluation(tuple(checks), tuple(reasons))
    total = exact_force_sum(tuple(lookup[b.id] for b in plan.geometry.group.bolts))
    first_demand = exact_force_sum(tuple(lookup[b.bolt.id] for b in plan.geometry.rows[0].bolts))
    width = first.effective_width
    prefix = plan.owner_id + ":" + plan.group_id
    if width is None:
        reasons.append("DCTN_NATIVE_EFFECTIVE_WIDTH_NOT_QUALIFIED")
    elif len(plan.geometry.group.bolts) == 1:
        nt = net_tension_resistance(
            width,
            request.fastener.diameter,
            request.fastener.hole_diameter,
            plan.thickness,
            ends.unloaded_end_e1,
            t,
            PultrudedElementForm.SHAPE_ELEMENT,
            plan.material_direction is MaterialDirection.LONGITUDINAL,
            **factors,
        )
        checks.append(
            numerical_check(
                "NET_TENSION:" + prefix,
                plan.owner_id,
                first_demand,
                nt.factor_trace.design_resistance,
                nt,
                source.reference,
            )
        )
    else:
        nt_multi = simplified_first_row_resistance(
            width, plan.thickness, t, plan.material_direction, **multi_factors
        )
        checks.append(
            numerical_check(
                "FIRST_ROW:" + prefix,
                plan.owner_id,
                first_demand,
                nt_multi.factor_trace.design_resistance,
                nt_multi,
                source.reference,
            )
        )
    # End-directed rupture at a flange/root junction is not a free-end path.
    if plan.geometry.boundary.unloaded_end_is_free:
        so = shear_out_resistance(
            ends.unloaded_end_e1, request.fastener.hole_diameter, plan.thickness, s, **factors
        )
        checks.append(
            numerical_check(
                "SHEAR_OUT:" + prefix,
                plan.owner_id,
                first_demand,
                so.factor_trace.design_resistance,
                so,
                source.reference,
            )
        )
        # Cleavage uses ORIGINAL characteristic bearing, never the RHS-only 0.50.
        original_bearing = pin_bearing_resistance(
            plan.thickness, request.fastener.diameter, b, thread, **factors
        )
        cl = cleavage_resistance(
            ends.unloaded_end_e1,
            min(first.raw_e3, first.raw_e4),
            request.fastener.diameter,
            request.fastener.hole_diameter,
            plan.thickness,
            t,
            s,
            original_bearing,
            **factors,
        )
        checks.append(
            numerical_check(
                "CLEAVAGE:" + prefix,
                plan.owner_id,
                first_demand,
                cl.selected_design_resistance,
                cl,
                source.reference,
            )
        )
        if pitches:
            inter = interrow_shear_out_resistance(
                InterrowShearOutMethod.ASCE_EQ_8_12
                if len(pitches) == 1
                else InterrowShearOutMethod.ASCE_EQ_8_13,
                ends.unloaded_end_e1,
                request.fastener.hole_diameter,
                pitches,
                plan.thickness,
                s,
                **multi_factors,
            )
            checks.append(
                numerical_check(
                    "INTERROW:" + prefix,
                    plan.owner_id,
                    total,
                    inter.factor_trace.design_resistance,
                    inter,
                    source.reference,
                )
            )
    else:
        reasons.append("DCTN_END_JUNCTION_LOCAL_PATH_NOT_QUALIFIED")
    accepted = (
        ()
        if plan.block_paths is None
        else tuple(
            p for p in plan.block_paths.candidates if p.availability is PlanAvailability.READY
        )
    )
    if plan.material_direction is not MaterialDirection.LONGITUDINAL:
        accepted = ()
    if not accepted:
        reasons.append("DCTN_LOCAL_BLOCK_PATH_NOT_QUALIFIED")
    geo = plan.geometry
    eccentricity = PhysicalQuantity.from_finite_real(
        geo.bolt_lines[0].projected_coordinate - (geo.negative_side_v + geo.positive_side_v) / 2,
        unit,
    )
    classification = classify_block_shear_eccentricity(
        eccentricity, PhysicalQuantity.from_finite_real(geo.sorting_tolerance, unit)
    )
    equation = (
        BlockShearEquation.ASCE_EQ_8_14A
        if classification is BlockShearEccentricityClassification.CONCENTRIC
        else BlockShearEquation.ASCE_EQ_8_14B
    )
    if accepted and equation is BlockShearEquation.ASCE_EQ_8_14B:
        reasons.append("DCTN_ECCENTRIC_BLOCK_PATH_NOT_QUALIFIED")
    for path in accepted:
        block = block_shear_resistance(
            equation, path.net_shear_area, path.net_tension_area, s, t, **multi_factors
        )
        checks.append(
            numerical_check(
                "BLOCK_SHEAR:" + prefix + ":" + path.path_id + ":" + equation.value,
                plan.owner_id,
                total,
                block.factor_trace.design_resistance,
                (block, eccentricity, classification),
                source.reference,
            )
        )
    return DCTNLocalEvaluation(tuple(checks), tuple(dict.fromkeys(reasons)))
