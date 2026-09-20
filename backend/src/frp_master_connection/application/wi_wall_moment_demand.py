"""Stage 4.2 dependency-only demand dispatch. No bolt-vector equations live here."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext

from frp_master_connection.application.multirow_orchestration import (
    MultiRowLayerInput,
    MultiRowOrchestrationRequest,
    _execution_bundle,
    _resolve,
)
from frp_master_connection.application.wi_wall_moment_geometry import (
    PlacedWallAngle,
    grid,
    inch,
    q,
    vector,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    EndUseFactors,
    FirstRowPlanMethod,
    LapConfiguration,
    MethodProvenance,
    PublishedCodeUnitBasis,
    PultrudedElementClassification,
    RowDistributionBasis,
    ThreadStatus,
    TimeEffectCategory,
    calculate_eccentric_bolt_group_demand,
    plan_row_demands,
)
from frp_master_connection.calculation.angle_connector_core import AngleWrench
from frp_master_connection.calculation.eccentric_demand import (
    EccentricDemandInput,
    EccentricDemandResult,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    InPlaneWrenchResult,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.wi_wall_moment import WIWallMomentRequest

D = Decimal
END_USE = EndUseFactors(
    D(1),
    D(1),
    D(1),
    "ASCE/SEI 74-23 Section 2.4.4",
    ("STAGE_4_2_CONTROLLED_UNITY_END_USE_FACTORS",),
)


def flange_local_request(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    force: PhysicalQuantity,
    *,
    beam_layer: bool = False,
    force_a: PhysicalQuantity | None = None,
) -> MultiRowOrchestrationRequest:
    """Map actual leg boundaries into the accepted local-check geometry contract."""
    spec = angle.specification
    g, pattern = spec.geometry, spec.member_pattern
    points = grid(pattern)
    first, last = min(p[2] for p in points), max(p[2] for p in points)
    t = inch(g.thickness)
    if beam_layer:
        low = inch(request.gap) - t / 2
        high = low + inch(request.beam.display_length_each_side)
        web = "WEB" in angle.connector_id
        width = (
            inch(request.beam.depth) - 2 * inch(request.beam.flange_thickness)
            if web
            else inch(request.beam.flange_width)
        )
        thickness = request.beam.web_thickness if web else request.beam.flange_thickness
        material_angle = D(0)
        layer_id = (
            "WI_WEB"
            if web
            else "WI_TOP_FLANGE"
            if angle.connector_id == "TOP_FLANGE_ANGLE"
            else "WI_BOTTOM_FLANGE"
        )
    else:
        low, high = -t / 2, inch(g.member_leg) - t / 2
        width, thickness = inch(g.length), g.thickness
        material_angle = D(90)
        layer_id = angle.connector_id
    side = (width - inch(pattern.gauge) * D(pattern.across - 1)) / 2
    basis = (
        RowDistributionBasis.ASCE_PRESCRIBED
        if pattern.along in {2, 3}
        else RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE
    )
    return MultiRowOrchestrationRequest(
        f"stage42:{angle.connector_id}:{layer_id}",
        "STAGE_4_2_CONNECTION",
        angle.connector_id,
        "STAGE_4_2_MEMBER_ACTION",
        "Stage 4.2 physical member-interface native demand",
        EngineeringUnitSystem.US_CUSTOMARY,
        Unit.IN,
        pattern.along,
        pattern.across,
        spec.fastener.bolt_diameter.to(Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        pattern.pitch.to(Unit.IN),
        pattern.gauge.to(Unit.IN),
        q(first - low),
        q(high - last),
        q(side),
        q(side),
        q(".000000001"),
        ConnectedMaterialPair.FRP_FRP,
        (
            MultiRowLayerInput(
                layer_id,
                layer_id,
                spec.material_id,
                thickness.to(Unit.IN),
                PultrudedElementClassification.SHAPE,
                material_angle,
                END_USE,
                ThreadStatus(spec.fastener.thread_condition),
            ),
        ),
        force,
        q(0, Unit.KIP) if force_a is None else force_a,
        "PHYSICAL_MEMBER_GROUP_CENTROID",
        basis,
        None,
        (),
        MethodProvenance(
            "STAGE_4_2_NATIVE_SLICE8_WEB_DEMAND"
            if "WEB" in angle.connector_id
            else "STAGE_4_2_NATIVE_STAGE25A_FLANGE_DEMAND",
            "STAGE_4_2_RC1_R7",
            "RC1-R7",
            "STAGE_4_2_MEMBER_ACTION",
            angle.connector_id,
            True,
            True,
        ),
        False,
        (),
        TimeEffectCategory.WIND_TORNADO_SEISMIC,
        LapConfiguration.DOUBLE_LAP if "WEB" in angle.connector_id else LapConfiguration.SINGLE_LAP,
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        None,
        q(0),
        q(".000000001"),
        single_row_geometry_preview_authorized=pattern.along == 1,
    )


def flange_stage25_input(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    wrench: AngleWrench,
) -> EccentricDemandInput:
    mapping = flange_local_request(request, angle, wrench.force.y)
    resolved = _resolve(mapping)
    bundle = _execution_bundle(mapping, resolved)
    physical = grid(angle.specification.member_pattern)
    old = {b.bolt_id: b for b in bundle.physical_geometry.bolts}
    offset = physical[0][2] - old[physical[0][0]].x
    # Preserve the specified coordinates exactly rather than accepting float-derived
    # placement from the historical preview kernel. IDs/planning remain native.
    geometry = replace(
        bundle.physical_geometry,
        bolts=tuple(
            replace(
                old[ident],
                x=b - offset,
                y=a,
                hole_diameter=inch(angle.specification.fastener.hole_diameter),
            )
            for ident, a, b in physical
        ),
    )
    with localcontext() as context:
        context.prec = 100  # Existing Stage 2.5A invocation boundary, not Slice 8 emulation.
        plan = plan_row_demands(
            resolved.geometry,
            PhysicalQuantity.of(abs(wrench.force.y.magnitude), wrench.force.y.unit),
            mapping.row_distribution_basis,
            mapping.provenance,
            connected_materials=ConnectedMaterialPair.FRP_FRP
            if mapping.row_distribution_basis is RowDistributionBasis.ASCE_PRESCRIBED
            else None,
        )
    zero_moment = vector((D(0), D(0), D(0)), Unit.KIP_IN)
    return EccentricDemandInput(
        f"{angle.connector_id}_MEMBER_ACTION",
        angle.connector_id,
        ExactQuantityVector3D(q(0, Unit.KIP), wrench.force.y, q(0, Unit.KIP)),
        zero_moment,
        zero_moment,
        vector((D(0), inch(angle.specification.member_pattern.center), D(0))),
        ExactInterfaceFrame(
            angle.connector_id,
            vector((D(0), offset, D(0))),
            (D(0), D(1), D(0)),
            (D(1), D(0), D(0)),
            (D(0), D(0), D(-1)),
        ),
        geometry,
        plan,
        resolved.applicability.method_applicability,
        resolved.applicability.qualification,
        ("STAGE_4_2_FLANGE_IN_PLANE_ONLY", "OUT_OF_PLANE_WRENCH_RETAINED_FOR_QUALIFIED_ATTACHMENT"),
    )


def flange_demand(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    wrench: AngleWrench,
) -> EccentricDemandResult | None:
    if wrench.force.y.canonical_magnitude == 0:
        return None
    native_input = flange_stage25_input(request, angle, wrench)
    with localcontext() as context:
        context.prec = 100
        return calculate_eccentric_bolt_group_demand(native_input)


def web_slice8_input(angle: PlacedWallAngle, wrench: AngleWrench) -> InPlaneWrenchRequest:
    return InPlaneWrenchRequest(
        tuple(WrenchBolt(ident, a, b) for ident, a, b in grid(angle.specification.member_pattern)),
        (D(0), inch(angle.specification.member_pattern.center)),
        wrench.force.x.to(Unit.KIP).magnitude,
        wrench.force.y.to(Unit.KIP).magnitude,
        wrench.moment.z.to(Unit.KIP_IN).magnitude,
        Unit.IN,
        Unit.KIP,
        Unit.KIP_IN,
    )


def web_demand(angle: PlacedWallAngle, wrench: AngleWrench) -> InPlaneWrenchResult:
    return calculate_in_plane_wrench_demand(web_slice8_input(angle, wrench))
