"""Native local FRP checks at the actual support regions, with explicit path limits."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import pairwise

from frp_master_connection.application.multirow_orchestration import (
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    FRPSupportMomentPreview,
)
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.application.wi_wall_moment_geometry import _bounds, inch, q
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    FirstRowPlanMethod,
    LapConfiguration,
    MaterialDirection,
    MethodProvenance,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
)
from frp_master_connection.calculation.equations import (
    BearingTrace,
    PullThroughTrace,
    pin_bearing_resistance,
    pull_through_resistance,
)
from frp_master_connection.calculation.in_plane_wrench_demand import project_rational
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    MultiRowCheckResult,
    calculate_multirow_connection,
)
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    adjusted_property_trace,
    compare_resistance,
    constant_pitch_factor,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    Unit,
    create_standard_hole,
)
from frp_master_connection.calculation.resistance_handoff import _material_direction
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.wi_frp_support_moment import SupportMode

D = Decimal


@dataclass(frozen=True, slots=True)
class SupportLocalCheck:
    check_id: str
    connector_id: str
    layer_id: str
    bolt_id: str | None
    method: str
    status: str
    demand: PhysicalQuantity | None
    resistance: PhysicalQuantity | None
    native_trace: BearingTrace | PullThroughTrace | MultiRowCheckResult | None
    native_comparison: ResistanceComparison | None
    applicability: str
    source: str
    material_direction: str
    signed_force_lw_cw: tuple[PhysicalQuantity, PhysicalQuantity] | None = None


def magnitude(u: PhysicalQuantity, v: PhysicalQuantity) -> PhysicalQuantity:
    squared = Fraction(u.canonical_magnitude) ** 2 + Fraction(v.canonical_magnitude) ** 2
    return q(project_rational(squared, square_root=True), Unit.N)


def bearing_and_pull_through(
    preview: FRPSupportMomentPreview,
    connector: str,
    bolt_id: str,
    force_u: PhysicalQuantity,
    force_v: PhysicalQuantity,
    tension: PhysicalQuantity | None,
    source: str,
    *,
    receiving: bool,
    layer_id: str | None = None,
) -> tuple[SupportLocalCheck, ...]:
    """Actual receiver LW is vertical. Angle LW is its native A, not beam LW."""
    index = next(i for i, t in enumerate(preview.connectors) if t.connector_id == connector)
    spec = preview.input.angles[index]
    physical = next(b for b in preview.geometry.support_bolts if b.hardware.hardware_id == bolt_id)
    mode = preview.input.support.mode
    layer = layer_id or (
        physical.crossing.layer_ids[0] if receiving else f"{connector}_SUPPORT_LEG"
    )
    if receiving and mode is SupportMode.SOLID_SQUARE:
        return (
            SupportLocalCheck(
                f"LOCAL_3D:{layer}:{bolt_id}",
                connector,
                layer,
                bolt_id,
                "SOLID_RECEIVING_REGION_3D_APPLICABILITY",
                "SOURCE_REQUIRED",
                None,
                None,
                None,
                None,
                "FULL_SOLID_GRIP_IS_NOT_EFFECTIVE_THIN_PLATE_THICKNESS",
                source,
                "ACTUAL_RECEIVER_LW_VERTICAL",
            ),
        )
    if receiving and layer not in physical.crossing.layer_ids:
        raise ValueError("Receiving layer is not penetrated material")
    thickness = (
        q(physical.crossing.material_thicknesses[physical.crossing.layer_ids.index(layer)], Unit.IN)
        if receiving
        else spec.geometry.thickness
    )
    # The pure local demand convention is the support-directed action, not a
    # silently reversed global beam direction. Signed components stay in trace.
    a = preview.geometry.angles[index].frame.a
    c = preview.geometry.angles[index].frame.c
    if receiving:
        lw, cw = force_u, force_v
    else:

        def dot(v: tuple[Decimal, Decimal, Decimal]) -> PhysicalQuantity:
            return q(
                project_rational(
                    Fraction(force_u.canonical_magnitude) * Fraction(v[1])
                    + Fraction(force_v.canonical_magnitude) * Fraction(v[2])
                ),
                Unit.N,
            )

        lw, cw = dot(a), dot(c)
    with localcontext() as context:
        context.prec = 80
        direction = _material_direction(
            (lw.canonical_magnitude, cw.canonical_magnitude), (D(1), D(0))
        )
    from frp_master_connection.application.mat1_scope import material_for_owner

    material = material_for_owner("SUPPORT", create_locked_ice_material_snapshot())
    kind = (
        FRPPropertyKind.FBR_L
        if direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FBR_T
    )
    prop = next(p for p in material.properties if p.kind is kind)
    f = spec.support_fastener
    # Pitch belongs to rows along the actual group force, not the UI field
    # called 'pitch' in a differently oriented angle frame. A free moment or
    # oblique group has no inherited prescriptive row-direction proof here.
    transfer = preview.connectors[index]
    u, v = (
        x.canonical_magnitude for x in (transfer.support_uvn.force.x, transfer.support_uvn.force.y)
    )
    delta: Decimal | None = None
    if force_u.canonical_magnitude == force_v.canonical_magnitude == 0:
        delta = D(1)
    elif transfer.support_uvn.moment.z.canonical_magnitude == 0 and ((u == 0) != (v == 0)):
        points = sorted(
            {
                inch(b.support_point.y if u != 0 else b.support_point.z)
                for b in preview.geometry.support_bolts
                if b.hardware.group_id == f"{connector}_SUPPORT_GROUP"
            }
        )
        delta = (
            constant_pitch_factor(
                tuple(q(b - a) for a, b in pairwise(points)), f.bolt_diameter
            ).pitch_factor_c_delta
            if len(points) > 1
            else D(1)
        )
    demand = magnitude(force_u, force_v)
    result: list[SupportLocalCheck] = []
    if delta is None:
        result.append(
            SupportLocalCheck(
                f"PIN_BEARING:{layer}:{bolt_id}",
                connector,
                layer,
                bolt_id,
                "NATIVE_ASCE_8_5",
                "SOURCE_REQUIRED",
                demand,
                None,
                None,
                None,
                "CONSTANT_FORCE_DIRECTION_ROW_PITCH_AUTHORITY_REQUIRED",
                source,
                direction.value,
                (lw, cw),
            )
        )
    else:
        trace = pin_bearing_resistance(
            thickness,
            f.bolt_diameter,
            adjusted_property_trace(prop, END_USE),
            ThreadStatus(f.thread_condition),
            c_delta=delta,
            c_lap=D(".6"),
            lambda_factor=D(1),
        )
        comparison = compare_resistance(demand, trace.factor_trace.design_resistance)
        result.append(
            SupportLocalCheck(
                f"PIN_BEARING:{layer}:{bolt_id}",
                connector,
                layer,
                bolt_id,
                "NATIVE_ASCE_8_5",
                comparison.numerical_comparison.value,
                demand,
                trace.factor_trace.design_resistance,
                trace,
                comparison,
                "SEPARATE_LOCAL_IN_PLANE_SINGLE_LAP_CHECK_NOT_COMPLETE_ATTACHMENT",
                source,
                direction.value,
                (lw, cw),
            )
        )
    seated = not (
        receiving and mode is SupportMode.HOLLOW_SQUARE and layer != physical.crossing.layer_ids[-1]
    )
    if tension is None or not seated:
        result.append(
            SupportLocalCheck(
                f"PULL_THROUGH:{layer}:{bolt_id}",
                connector,
                layer,
                bolt_id,
                "NATIVE_ASCE_8_4_LESSER_BOTH_BRANCHES",
                "SOURCE_REQUIRED",
                None,
                None,
                None,
                None,
                "NORMAL_DEMAND_UNAVAILABLE_NOT_ZERO"
                if tension is None
                else "NO_EXTERIOR_WASHER_ON_THIS_HOLLOW_WALL_PULL_THROUGH_NOT_APPLICABLE",
                source,
                "TT",
            )
        )
    else:
        # Eq. 8-4 explicitly permits the transverse-through-thickness shear
        # source mapping FshTT=FshLT; both adjusted properties remain visible.
        tt = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_LT)
        inter = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_INT)
        pull = pull_through_resistance(
            spec.support_hardware.washer_diameter,
            thickness,
            adjusted_property_trace(tt, END_USE),
            adjusted_property_trace(inter, END_USE),
            # The accepted Slice 2 factor applicability explicitly excludes
            # pull-through. The bearing-row reduction is not transferable here.
            c_delta=D(1),
            lambda_factor=D(1),
        )
        pc = compare_resistance(tension, pull.factor_trace.design_resistance)
        result.append(
            SupportLocalCheck(
                f"PULL_THROUGH:{layer}:{bolt_id}",
                connector,
                layer,
                bolt_id,
                "NATIVE_ASCE_8_4_LESSER_BOTH_BRANCHES",
                pc.numerical_comparison.value,
                tension,
                pull.factor_trace.design_resistance,
                pull,
                pc,
                "VALIDATED_NORMAL_RESPONSE_ACTUAL_FULLY_SEATED_WASHER_AND_THIN_REGION",
                source,
                "TT",
            )
        )
    return tuple(result)


def support_group_paths(
    preview: FRPSupportMomentPreview, connector: str, *, receiving: bool
) -> tuple[SupportLocalCheck, ...]:
    """Free-boundary rectangular group seam; junction/unproven paths stay open.

    This consumes the accepted Slice 8 vectors only when its actual concentric
    two-row half demands coincide with the prescribed native row plan. No
    independent moment is discarded and no fictitious equivalent force is made.
    """
    index = next(i for i, t in enumerate(preview.connectors) if t.connector_id == connector)
    transfer = preview.connectors[index]
    spec = preview.input.angles[index]
    group = transfer.support_in_plane_demand
    layer = (
        preview.geometry.support.surface.physical_element_role.value
        if receiving
        else f"{connector}_SUPPORT_LEG"
    )
    reason = "SOURCE_REQUIRED_LOCAL_PATH_PARTICIPATION"
    mapping = None
    if group is not None:
        solution = group.solution
        if solution.force == (Fraction(0), Fraction(0)) and solution.centroid_moment == 0:
            return ()
        reason = "NOT_EVALUATED_OBLIQUE_OR_ECCENTRIC_GROUP_PATH_AUTHORITY_REQUIRED"
        if solution.force[1] == 0 and solution.force[0] != 0 and solution.centroid_moment == 0:
            reason = "NOT_EVALUATED_JUNCTION_END_OR_ROW_PLAN_AUTHORITY_REQUIRED"
            # Receiver primary direction is longitudinal. The angle's A-directed
            # free length has two actual free ends. Its C-directed leg terminates
            # at a heel junction: no free-end net/cleavage fiction is permitted.
            if receiving or index >= 2:
                mapping = _group_mapping(preview, index, receiving=receiving)
                if mapping.row_count != 2:
                    mapping = None
    checks = []
    if mapping is not None:
        f = spec.support_fastener
        if (
            f.hole_diameter
            != create_standard_hole(
                f.bolt_diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
            ).hole_diameter
        ):
            reason = "NOT_EVALUATED_NONSTANDARD_HOLE_GROUP_PATH_AUTHORITY_REQUIRED"
        else:
            native = calculate_multirow_connection(_execution_bundle(mapping, _resolve(mapping)))
            allowed = {
                MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                MultiRowCheckFamily.INTERROW_SHEAR_OUT,
            }
            if receiving and preview.input.support.mode is SupportMode.WI_FLANGE:
                allowed.add(MultiRowCheckFamily.BLOCK_SHEAR)
            for record in native.results:
                if record.limit_state in allowed:
                    checks.append(
                        SupportLocalCheck(
                            f"SUPPORT_GROUP:{record.result_id}",
                            connector,
                            layer,
                            None,
                            record.limit_state.value,
                            record.numerical_comparison.value,
                            record.demand,
                            record.design_resistance,
                            record,
                            None,
                            "NATIVE_FORCE_ALIGNED_TWO_ROW_SCOPE_ACTUAL_PHYSICAL_ENDS",
                            group.fingerprint if group else "",
                            mapping.layers[0].material_axis_angle_degrees.to_eng_string(),
                        )
                    )
            reason = "SOURCE_REQUIRED_JUNCTION_CLEAVAGE_AND_COMMON_GROUP_PATH_COVERAGE"
    checks.append(
        SupportLocalCheck(
            f"SUPPORT_PATH_COVERAGE:{connector}:{layer}",
            connector,
            layer,
            None,
            "NET_SHEAR_OUT_CLEAVAGE_INTERROW_BLOCK_APPLICABILITY",
            reason.split(":")[0],
            None,
            None,
            None,
            None,
            reason,
            "STAGE_4_3_LOCAL_SUPPORT_ZONE_REQUIRED",
            "ACTUAL_REGION_AXES",
        )
    )
    return tuple(checks)


def _group_mapping(
    preview: FRPSupportMomentPreview, index: int, *, receiving: bool
) -> MultiRowOrchestrationRequest:
    transfer = preview.connectors[index]
    spec = preview.input.angles[index]
    bolts = tuple(
        b
        for b in preview.geometry.support_bolts
        if b.hardware.group_id == f"{transfer.connector_id}_SUPPORT_GROUP"
    )
    us = sorted({inch(b.support_point.y) for b in bolts})
    vs = sorted({inch(b.support_point.z) for b in bolts})
    if receiving:
        s = preview.input.support
        lo_u, hi_u = (
            -inch(s.physical_length) / 2 - inch(s.connection_height),
            inch(s.physical_length) / 2 - inch(s.connection_height),
        )
        # Actual surface bounds transformed to the common support plane.
        corners = [
            preview.geometry.support.point((x, y, z))
            for bounds in preview.geometry.support.surface.penetration_bounds
            for x in (bounds.min_x, bounds.max_x)
            for y in (bounds.min_y, bounds.max_y)
            for z in (bounds.min_z, bounds.max_z)
        ]
        lo_v, hi_v = min(p[2] for p in corners), max(p[2] for p in corners)
        thickness = q(bolts[0].crossing.material_thicknesses[0], Unit.IN)
        layer = bolts[0].crossing.layer_ids[0]
    else:
        part = next(
            p for p in preview.geometry.parts if p.part_id == f"{transfer.connector_id}_SUPPORT_LEG"
        )
        lo, hi = _bounds(part)
        lo_u, hi_u, lo_v, hi_v = lo[1], hi[1], lo[2], hi[2]
        thickness = spec.geometry.thickness
        layer = part.part_id
    # No derived float is used to invent a physical boundary. The inherited
    # geometric tolerance is only its existing planar mapping contract.
    return MultiRowOrchestrationRequest(
        f"stage43:{layer}:{transfer.connector_id}",
        "STAGE43",
        transfer.connector_id,
        "STAGE43_SUPPORT_ACTION",
        "Native Slice 8 support plane scope",
        EngineeringUnitSystem.US_CUSTOMARY,
        Unit.IN,
        len(us),
        len(vs),
        spec.support_fastener.bolt_diameter.to(Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        q(us[1] - us[0]) if len(us) > 1 else spec.support_pattern.gauge,
        q(vs[1] - vs[0]) if len(vs) > 1 else spec.support_pattern.pitch,
        q(us[0] - lo_u),
        q(hi_u - us[-1]),
        q(vs[0] - lo_v),
        q(hi_v - vs[-1]),
        q(".000000001"),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                layer,
                layer,
                preview.input.support.material_id if receiving else spec.material_id,
                thickness,
                PultrudedElementClassification.SHAPE,
                D(0),
                END_USE,
                ThreadStatus(spec.support_fastener.thread_condition),
            ),
        ),
        transfer.support_uvn.force.x,
        transfer.support_uvn.force.y,
        "ACTUAL_SUPPORT_GROUP_REFERENCE",
        RowDistributionBasis.ASCE_PRESCRIBED
        if len(us) in {2, 3}
        else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        None,
        (),
        MethodProvenance(
            "STAGE43_NATIVE_SLICE8_SUPPORT_PLANE",
            "STAGE43_RC1",
            "RC1",
            "STAGE43_SUPPORT_ACTION",
            transfer.connector_id,
            True,
            True,
        ),
        False,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.SINGLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        None,
        q(0),
        q(".000000001"),
        single_row_geometry_preview_authorized=len(us) == 1,
    )
