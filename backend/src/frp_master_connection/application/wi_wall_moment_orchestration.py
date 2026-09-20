"""Stage 4.2 native-engine composition; preview performs no resistance evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from typing import cast

from frp_master_connection.application.wi_wall_moment_demand import flange_demand, web_demand
from frp_master_connection.application.wi_wall_moment_geometry import (
    PlacedWallAngle,
    WallMomentGeometry,
    inch,
    resolve_wall_moment_geometry,
    vector,
    xyz,
)
from frp_master_connection.application.wi_wall_moment_sources import (
    ATTACHMENT_COVERAGE,
    ATTACHMENT_METHOD,
    provider_context,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
    Decimal3,
    Rational3,
    angle_fingerprint,
    components,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import (
    EccentricDemandResult,
    ExactQuantityVector3D,
)
from frp_master_connection.calculation.frp_angle_connector_provider import (
    FRPSourceBinding,
    QualifiedCoverage,
    frp_source_binding,
)
from frp_master_connection.calculation.in_plane_wrench_demand import InPlaneWrenchResult
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentComponentResult,
    WIMomentComponentResultants,
    WIMomentRegionId,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
)
from frp_master_connection.domain.wi_wall_moment import (
    CONTRACT,
    PRODUCT,
    WallMomentActions,
    WIWallMomentRequest,
)

D = Decimal
SIGN_METHOD = "EXACT_WI_NEGATIVE_END_STRUCTURAL_TO_RIGHT_HAND_WRENCH_MAP_RC1"
ALLOCATION_METHOD = "RATIONAL_SYMMETRIC_PAIRED_WEB_ANGLE_WRENCH_ALLOCATION_RC1"
WALL_METHOD = "EXACT_FOUR_ANGLE_WALL_SUPPORT_HANDOFF_ASSEMBLY_RC1"
EXTERNAL_STATUS = "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
NUMERIC_AUTHORITY = (
    "STAGE_4_2_RC1_R7",
    "SLICE5_NATIVE_DECIMAL80_HALF_EVEN",
    "STAGE42_PRE_CORE_DECIMAL80_HALF_EVEN",
    "SLICE7_NATIVE_UNCHANGED",
    "STAGE42_POST_CORE_EXACT_FINITE_RATIONAL",
    "R4_WEB_HEEL_GRID_REFERENCE_0_2",
    "R5_NATIVE_STAGE25A_FLANGES",
    "R6_NATIVE_STATUS_AND_PURE_MOMENT_PROOF_TARGET",
    "R7_NATIVE_GOVERNING_SELECTION",
)
DISCLAIMER_ID = "WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_DISCLAIMER_RC1"
DISCLAIMER = (
    "Rational W/I beam-to-concrete-wall moment connection requiring engineering review and "
    "Section 2.3.2 qualification. Qualified connector and member-attachment sources must "
    "cover the complete signed wrench, including through-thickness, prying, contact and "
    "secondary bolt bending. Anchor/concrete design and individual anchor distribution are "
    "external. Stiffness, rotation capacity and full-strength classification are not evaluated."
)


@dataclass(frozen=True, slots=True)
class WallMomentConnectorResult:
    connector_id: str
    slice5_region: WIMomentRegionId
    allocation_fraction: Decimal
    core: AngleCoreResult
    flange_demand: EccentricDemandResult | None
    web_demand: InPlaneWrenchResult | None
    support_global: AngleWrench
    support_at_wall: AngleWrench
    out_of_plane_attachment_components: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    instep_plan_status: str


@dataclass(frozen=True, slots=True)
class WallMomentSourcePlan:
    connector_id: str
    method: str
    selected_reference: str
    binding: FRPSourceBinding
    required_coverage: tuple[str, ...]
    resistance_evaluated: bool = False


@dataclass(frozen=True, slots=True)
class WallMomentEquilibrium:
    slice5_algebraic_proof: bool
    paired_web_symmetry_proof: bool
    connector_core_proofs: tuple[bool, ...]
    web_group_proofs: tuple[bool, ...]
    proof_passed: bool
    algebraic_wall_target: AngleWrench
    serialized_force_diagnostic: ExactQuantityVector3D
    serialized_moment_diagnostic: ExactQuantityVector3D
    structural_major_moment: PhysicalQuantity
    structural_major_moment_diagnostic: PhysicalQuantity
    tolerance_used: bool = False
    residual_redistribution: bool = False


@dataclass(frozen=True, slots=True)
class WIWallMomentPreview:
    request_id: str
    product_id: str
    contract: str
    geometry: WallMomentGeometry
    slice5: WIMomentComponentResultants
    connectors: tuple[WallMomentConnectorResult, ...]
    joint_right_hand_action: AngleWrench
    wall_handoff: AngleWrench | None
    wall_reaction: AngleWrench | None
    equilibrium: WallMomentEquilibrium | None
    engineering_fingerprint: str
    status: str
    design_check_ready: bool
    applied_actions: WallMomentActions
    source_plans: tuple[WallMomentSourcePlan, ...]
    resistance_evaluated: bool = False
    whole_connection_status: str = EXTERNAL_STATUS
    sign_method: str = SIGN_METHOD
    allocation_method: str = ALLOCATION_METHOD
    wall_method: str = WALL_METHOD
    numeric_authority: tuple[str, ...] = NUMERIC_AUTHORITY
    disclaimer_id: str = DISCLAIMER_ID
    disclaimer: str = DISCLAIMER
    qualification: str = "REQUIRED_2_3_2"
    stiffness: str = "NOT_EVALUATED"
    rotation_capacity: str = "NOT_EVALUATED"
    full_strength_classification: str = "NOT_EVALUATED"
    flexible_fixture_status: str = "FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED"


def _cross(x: tuple[Decimal, ...], y: Decimal3) -> Decimal3:
    return x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]


def member_interface_wrench(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    component: WIMomentComponentResult,
    share: Decimal,
) -> AngleWrench:
    """R3 boundary: copy Slice 5 then construct physical member demand at Decimal-80."""
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
        force = (
            component.wrench.force_lvt.l.to(Unit.KIP).magnitude * share,
            component.wrench.force_lvt.v.to(Unit.KIP).magnitude * share,
            D(0),
        )
        moment = (D(0), D(0), -component.wrench.moment_lvt.t.to(Unit.KIP_IN).magnitude * share)
        source = (inch(request.gap), component.centroid_v.to(Unit.IN).magnitude, D(0))
        target = xyz(angle.member_reference_global)
        offset = tuple(source[i] - target[i] for i in range(3))
        cross = _cross(offset, force)
        shifted = tuple(moment[i] + cross[i] for i in range(3))
        axes = (angle.frame.a, angle.frame.b, angle.frame.c)
        local_force = tuple(
            sum((x * y for x, y in zip(force, axis, strict=True)), D(0)) for axis in axes
        )
        local_moment = tuple(
            sum((x * y for x, y in zip(shifted, axis, strict=True)), D(0)) for axis in axes
        )
        return AngleWrench(
            angle.member_reference, vector(local_force, Unit.KIP), vector(local_moment, Unit.KIP_IN)
        )


def global_support_wrench(angle: PlacedWallAngle, local: AngleWrench) -> AngleWrench:
    """Exact signed permutation of native Slice 7 finite canonical quantities."""
    axes = (angle.frame.a, angle.frame.b, angle.frame.c)

    def transform(values: Rational3) -> Rational3:
        return cast(
            Rational3,
            tuple(
                sum((Fraction(axes[k][j]) * values[k] for k in range(3)), Fraction(0))
                for j in range(3)
            ),
        )

    return AngleWrench(
        angle.support_reference_global,
        quantity_vector(transform(components(local.force)), Unit.N),
        quantity_vector(transform(components(local.moment)), Unit.N_MM),
    )


def _sum_wrenches(wrenches: tuple[AngleWrench, ...]) -> AngleWrench:
    zero = (Fraction(0), Fraction(0), Fraction(0))
    return AngleWrench(
        quantity_vector(zero, Unit.MM),
        quantity_vector(
            cast(
                Rational3,
                tuple(
                    sum((components(w.force)[i] for w in wrenches), Fraction(0)) for i in range(3)
                ),
            ),
            Unit.N,
        ),
        quantity_vector(
            cast(
                Rational3,
                tuple(
                    sum((components(w.moment)[i] for w in wrenches), Fraction(0)) for i in range(3)
                ),
            ),
            Unit.N_MM,
        ),
    )


def preview_wi_wall_moment(request: WIWallMomentRequest) -> WIWallMomentPreview:
    geometry = resolve_wall_moment_geometry(request)
    b, a = request.beam, request.actions
    slice5 = calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(
            WIMomentSectionInput(b.depth, b.flange_width, b.web_thickness, b.flange_thickness),
            WIMomentActionInput(
                a.axial,
                a.major_shear,
                a.structural_major_moment,
                a.minor_shear,
                a.minor_moment,
                a.torsion,
            ),
        )
    )
    zero = (Fraction(0), Fraction(0), Fraction(0))
    joint = AngleWrench(
        vector((inch(request.gap), D(0), D(0))),
        vector(
            (a.axial.to(Unit.KIP).magnitude, a.major_shear.to(Unit.KIP).magnitude, D(0)), Unit.KIP
        ),
        quantity_vector(
            (Fraction(0), Fraction(0), -Fraction(a.structural_major_moment.canonical_magnitude)),
            Unit.N_MM,
        ),
    )
    results: list[WallMomentConnectorResult] = []
    if geometry.status == "VALID":
        for angle, region, share in zip(
            geometry.angles,
            (
                WIMomentRegionId.TOP_FLANGE,
                WIMomentRegionId.BOTTOM_FLANGE,
                WIMomentRegionId.WEB,
                WIMomentRegionId.WEB,
            ),
            (D(1), D(1), D(".5"), D(".5")),
            strict=True,
        ):
            member = member_interface_wrench(request, angle, slice5.component(region), share)
            core = resolve_angle_connector(
                AngleCoreRequest(
                    angle.specification.geometry, angle.frame, member, angle.support_reference
                )
            )
            flange = (
                flange_demand(request, angle, member)
                if region is not WIMomentRegionId.WEB
                else None
            )
            web = web_demand(angle, member) if region is WIMomentRegionId.WEB else None
            support = global_support_wrench(angle, core.connector_on_support)
            shifted = shift_angle_wrench(support, quantity_vector(zero, Unit.MM))
            results.append(
                WallMomentConnectorResult(
                    angle.connector_id,
                    region,
                    share,
                    core,
                    flange,
                    web,
                    support,
                    shifted,
                    (member.force.z, member.moment.x, member.moment.y),
                    "NOT_REQUIRED_ZERO_SHEAR"
                    if core.heel.force.x.canonical_magnitude == 0
                    else "ASCE_8_15_DIRECT_INSTEP_SHEAR_CHECK_REQUIRED",
                )
            )
    handoff, reaction, equilibrium = None, None, None
    if results:
        handoff = _sum_wrenches(tuple(r.support_at_wall for r in results))
        reaction = AngleWrench(
            handoff.reference,
            quantity_vector(cast(Rational3, tuple(-v for v in components(handoff.force))), Unit.N),
            quantity_vector(
                cast(Rational3, tuple(-v for v in components(handoff.moment))), Unit.N_MM
            ),
        )
        target = shift_angle_wrench(joint, handoff.reference)
        fd = cast(
            Rational3,
            tuple(
                v - t
                for v, t in zip(components(handoff.force), components(target.force), strict=True)
            ),
        )
        md = cast(
            Rational3,
            tuple(
                v - t
                for v, t in zip(components(handoff.moment), components(target.moment), strict=True)
            ),
        )
        cores = tuple(
            components(r.core.equilibrium.force) == components(r.core.equilibrium.moment) == zero
            for r in results
        )
        webs = tuple(
            r.web_demand.solution.proof is not None and r.web_demand.solution.proof.passed
            for r in results
            if r.web_demand is not None
        )
        inherited = all(
            (
                slice5.equilibrium.axial_equilibrium_exact,
                slice5.equilibrium.shear_equilibrium_exact,
                slice5.equilibrium.moment_equilibrium_exact,
            )
        )
        structural = quantity_vector(
            (Fraction(0), Fraction(0), -components(handoff.moment)[2]), Unit.N_MM
        ).z
        structural_diagnostic = quantity_vector((Fraction(0), Fraction(0), -md[2]), Unit.N_MM).z
        equilibrium = WallMomentEquilibrium(
            inherited,
            geometry.symmetry_proven,
            cores,
            webs,
            inherited and geometry.symmetry_proven and all(cores) and len(webs) == 2 and all(webs),
            target,
            quantity_vector(fd, Unit.N),
            quantity_vector(md, Unit.N_MM),
            structural,
            structural_diagnostic,
        )
        if not equilibrium.proof_passed:
            raise ArithmeticError("STAGE_4_2_INHERITED_EXACT_EQUILIBRIUM_PROOF_FAILED")
    source_plans = tuple(
        WallMomentSourcePlan(
            angle.connector_id,
            ATTACHMENT_METHOD if attachment else "QUALIFIED_FRP_ANGLE_CONNECTOR_FULL_WRENCH_SOURCE",
            angle.specification.attachment_source_reference
            if attachment
            else angle.specification.connector_source_reference,
            frp_source_binding(
                result.core, provider_context(request, angle, result.core, attachment=attachment)
            ),
            ATTACHMENT_COVERAGE if attachment else tuple(item.value for item in QualifiedCoverage),
        )
        for angle, result in zip(geometry.angles, results, strict=False)
        for attachment in (False, True)
    )
    fingerprint = angle_fingerprint(
        (
            PRODUCT,
            CONTRACT,
            NUMERIC_AUTHORITY,
            geometry.fingerprint,
            slice5.result_fingerprint,
            tuple(
                (
                    r.connector_id,
                    r.core.fingerprint,
                    None if r.flange_demand is None else r.flange_demand.result_fingerprint,
                    None if r.web_demand is None else r.web_demand.fingerprint,
                    r.support_global,
                    r.support_at_wall,
                )
                for r in results
            ),
            handoff,
            equilibrium,
            source_plans,
        )
    )
    return WIWallMomentPreview(
        request.request_id,
        PRODUCT,
        CONTRACT,
        geometry,
        slice5,
        tuple(results),
        joint,
        handoff,
        reaction,
        equilibrium,
        fingerprint,
        geometry.status,
        geometry.status == "VALID",
        request.actions,
        source_plans,
    )
