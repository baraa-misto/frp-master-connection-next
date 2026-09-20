"""Native local FRP dispatch with actual layer axes and explicit path boundaries."""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import pairwise

from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    AngleBaseTransfer,
)
from frp_master_connection.application.angle_column_base_qualification import (
    BaseMemberResponseValidation,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
)
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.application.wi_wall_moment_geometry import grid, inch, q
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
    pin_bearing_resistance,
    pull_through_resistance,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    calculate_multirow_connection,
)
from frp_master_connection.calculation.multirow_equations import (
    adjusted_property_trace,
    compare_resistance,
    constant_pitch_factor,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import (
    Unit,
    create_standard_hole,
)
from frp_master_connection.calculation.resistance_handoff import _material_direction
from frp_master_connection.domain.values import EngineeringUnitSystem

D = Decimal


def member_local_checks(
    preview: AngleBasePreview, transfer: AngleBaseTransfer, response: BaseMemberResponseValidation
) -> tuple[SupportLocalCheck, ...]:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    spec = preview.geometry.angles[index].specification
    hw = preview.input.connectors[index].member_hardware
    material = create_locked_ice_material_snapshot()
    properties = {p.kind: p for p in material.properties}
    solution = transfer.in_plane_demand.solution
    delta = None
    if solution.force == (Fraction(0), Fraction(0)) and solution.centroid_moment == 0:
        delta = D(1)
    elif solution.centroid_moment == 0 and ((solution.force[0] == 0) != (solution.force[1] == 0)):
        axis = 0 if solution.force[0] != 0 else 1
        positions = sorted({p[1] if axis == 0 else p[2] for p in grid(spec.member_pattern)})
        delta = (
            constant_pitch_factor(
                tuple(q(b - a) for a, b in pairwise(positions)), spec.fastener.bolt_diameter
            ).pitch_factor_c_delta
            if len(positions) > 1
            else D(1)
        )
    checks = []
    shafts = {s.bolt_id: s for s in response.shafts}
    # Native projected vectors and magnitudes are consumed verbatim, not regenerated.
    for bolt in solution.projected_bolts():
        ident = f"{transfer.connector_id}:{bolt.bolt_id}"
        shaft = shafts.get(ident)
        for column in (False, True):
            layer = f"COLUMN_LEG_{index + 1}" if column else f"{transfer.connector_id}_MEMBER_LEG"
            thickness = preview.input.column.thickness if column else spec.geometry.thickness
            u, v = bolt.total_force.u, bolt.total_force.v
            # On the column the physical action is opposite; the sign-independent
            # material direction still uses column LW=B and connector LW=A.
            lw, cw = (
                (
                    q(v.canonical_magnitude.copy_negate(), Unit.N),
                    q(u.canonical_magnitude.copy_negate(), Unit.N),
                )
                if column
                else (u, v)
            )
            with localcontext() as ctx:
                ctx.prec = 80
                direction = _material_direction(
                    (lw.canonical_magnitude, cw.canonical_magnitude), (D(1), D(0))
                )
            kind = (
                FRPPropertyKind.FBR_L
                if direction is MaterialDirection.LONGITUDINAL
                else FRPPropertyKind.FBR_T
            )
            trace = (
                None
                if delta is None
                else pin_bearing_resistance(
                    thickness,
                    spec.fastener.bolt_diameter,
                    adjusted_property_trace(properties[kind], END_USE),
                    ThreadStatus(spec.fastener.thread_condition),
                    c_delta=delta,
                    c_lap=D(".6"),
                    lambda_factor=D(1),
                )
            )
            comparison = (
                None
                if trace is None
                else compare_resistance(
                    bolt.total_force_magnitude, trace.factor_trace.design_resistance
                )
            )
            checks.append(
                SupportLocalCheck(
                    f"PIN_BEARING:{layer}:{bolt.bolt_id}",
                    transfer.connector_id,
                    layer,
                    ident,
                    "NATIVE_ASCE_8_5",
                    "SOURCE_REQUIRED"
                    if comparison is None
                    else comparison.numerical_comparison.value,
                    bolt.total_force_magnitude,
                    None if trace is None else trace.factor_trace.design_resistance,
                    trace,
                    comparison,
                    "CONSTANT_FORCE_DIRECTION_ROW_PITCH_AUTHORITY_REQUIRED"
                    if delta is None
                    else "ACTUAL_SINGLE_LAP_LEAF_NATIVE_BEARING",
                    transfer.in_plane_demand.fingerprint,
                    direction.value,
                    (lw, cw),
                )
            )
            pull = (
                None
                if shaft is None
                else pull_through_resistance(
                    hw.washer_diameter,
                    thickness,
                    adjusted_property_trace(properties[FRPPropertyKind.FSH_LT], END_USE),
                    adjusted_property_trace(properties[FRPPropertyKind.FSH_INT], END_USE),
                    c_delta=D(1),
                    lambda_factor=D(1),
                )
            )
            pc = (
                None
                if pull is None or shaft is None
                else compare_resistance(shaft.tensile_demand, pull.factor_trace.design_resistance)
            )
            checks.append(
                SupportLocalCheck(
                    f"PULL_THROUGH:{layer}:{bolt.bolt_id}",
                    transfer.connector_id,
                    layer,
                    ident,
                    "NATIVE_ASCE_8_4_LESSER_BOTH_BRANCHES",
                    "SOURCE_REQUIRED" if pc is None else pc.numerical_comparison.value,
                    None if shaft is None else shaft.tensile_demand,
                    None if pull is None else pull.factor_trace.design_resistance,
                    pull,
                    pc,
                    "NORMAL_DEMAND_UNAVAILABLE_NOT_ZERO"
                    if shaft is None
                    else "QUALIFIED_RESPONSE_ACTUAL_EXTERIOR_WASHER",
                    response.fingerprint,
                    "TT",
                )
            )
    checks.extend(connector_group_paths(preview, transfer))
    checks.append(
        SupportLocalCheck(
            f"COLUMN_COMMON_PATHS:{transfer.connector_id}",
            transfer.connector_id,
            f"COLUMN_LEG_{index + 1}",
            None,
            "ANGLE_COLUMN_TWO_LEG_END_ZONE",
            "SOURCE_REQUIRED",
            None,
            None,
            None,
            None,
            "COMMON_NET_BLOCK_CLEAVAGE_JUNCTION_AND_REVERSE_PATH_COVERAGE_REQUIRED_NOT_VIEW_ENDS",
            transfer.in_plane_demand.fingerprint,
            "COLUMN_LW_VERTICAL",
        )
    )
    return tuple(checks)


def connector_group_mapping(
    preview: AngleBasePreview, transfer: AngleBaseTransfer
) -> MultiRowOrchestrationRequest:
    """Concentric A-directed rows at physical extrusion free ends; no heel-as-free-end."""
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    spec = preview.geometry.angles[index].specification
    points = grid(spec.member_pattern)
    xs, ys = sorted({p[1] for p in points}), sorted({p[2] for p in points})
    low, high = -inch(spec.geometry.length) / 2, inch(spec.geometry.length) / 2
    bottom, top = (
        -inch(spec.geometry.thickness) / 2,
        inch(spec.geometry.member_leg) - inch(spec.geometry.thickness) / 2,
    )
    layer = f"{transfer.connector_id}_MEMBER_LEG"
    return MultiRowOrchestrationRequest(
        f"stage44:{layer}",
        "STAGE44",
        transfer.connector_id,
        "STAGE44_MEMBER_ACTION",
        "Native Slice 8 concentric A-directed free-end scope",
        EngineeringUnitSystem.US_CUSTOMARY,
        Unit.IN,
        len(xs),
        len(ys),
        spec.fastener.bolt_diameter.to(Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        spec.member_pattern.gauge.to(Unit.IN),
        spec.member_pattern.pitch.to(Unit.IN),
        q(xs[0] - low),
        q(high - xs[-1]),
        q(ys[0] - bottom),
        q(top - ys[-1]),
        q(".000000001"),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                layer,
                layer,
                spec.material_id,
                spec.geometry.thickness,
                PultrudedElementClassification.SHAPE,
                D(0),
                END_USE,
                ThreadStatus(spec.fastener.thread_condition),
            ),
        ),
        transfer.core.request.member_action.force.x,
        transfer.core.request.member_action.force.y,
        "ACTUAL_MEMBER_GROUP_REFERENCE",
        RowDistributionBasis.ASCE_PRESCRIBED
        if len(xs) in (2, 3)
        else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        None,
        (),
        MethodProvenance(
            "STAGE44_NATIVE_SLICE8_MEMBER_PLANE",
            "STAGE44_RC1",
            "RC1",
            "STAGE44_MEMBER_ACTION",
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
        single_row_geometry_preview_authorized=len(xs) == 1,
    )


def connector_group_paths(
    preview: AngleBasePreview, transfer: AngleBaseTransfer
) -> tuple[SupportLocalCheck, ...]:
    solution = transfer.in_plane_demand.solution
    if solution.force == (Fraction(0), Fraction(0)) and solution.centroid_moment == 0:
        return ()
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    spec = preview.geometry.angles[index].specification
    reason = "OBLIQUE_FREE_MOMENT_OR_HEEL_DIRECTED_PATH_REQUIRES_QUALIFICATION"
    result = []
    if (
        solution.force[0] != 0
        and solution.force[1] == 0
        and solution.centroid_moment == 0
        and spec.member_pattern.across == 2
    ):
        if (
            spec.fastener.hole_diameter
            != create_standard_hole(
                spec.fastener.bolt_diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
            ).hole_diameter
        ):
            reason = "NONSTANDARD_HOLE_LOCAL_PATH_AUTHORITY_REQUIRED"
        else:
            mapping = connector_group_mapping(preview, transfer)
            native = calculate_multirow_connection(_execution_bundle(mapping, _resolve(mapping)))
            # Net and inter-row paths are local to this actual connected leaf.
            # Heel-intersecting cleavage/block paths require body/zone qualification.
            for r in native.results:
                if r.limit_state in {
                    MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                    MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                }:
                    result.append(
                        SupportLocalCheck(
                            r.result_id,
                            transfer.connector_id,
                            f"{transfer.connector_id}_MEMBER_LEG",
                            None,
                            r.limit_state.value,
                            r.numerical_comparison.value,
                            r.demand,
                            r.design_resistance,
                            r,
                            None,
                            "NATIVE_LOCAL_CONNECTED_LEAF_NOT_WHOLE_ANGLE",
                            transfer.in_plane_demand.fingerprint,
                            "LONGITUDINAL",
                        )
                    )
            reason = "HEEL_JUNCTION_BLOCK_CLEAVAGE_COVERAGE_REQUIRED"
    result.append(
        SupportLocalCheck(
            f"CONNECTOR_PATH_SCOPE:{transfer.connector_id}",
            transfer.connector_id,
            f"{transfer.connector_id}_MEMBER_LEG",
            None,
            "NATIVE_LOCAL_PATH_APPLICABILITY",
            "SOURCE_REQUIRED",
            None,
            None,
            None,
            None,
            reason,
            transfer.in_plane_demand.fingerprint,
            "CONNECTOR_LW_A",
        )
    )
    return tuple(result)
