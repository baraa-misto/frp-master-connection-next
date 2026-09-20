"""Stage 4.3 preview: native beam/connector demand, no resistance execution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import cast

from frp_master_connection.application.wi_frp_support_moment_geometry import (
    FRPSupportMomentGeometry,
    resolve_frp_support_moment_geometry,
)
from frp_master_connection.application.wi_wall_moment_demand import flange_demand, web_demand
from frp_master_connection.application.wi_wall_moment_geometry import inch, vector
from frp_master_connection.application.wi_wall_moment_orchestration import (
    global_support_wrench,
    member_interface_wrench,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
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
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    InPlaneWrenchResult,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentComponentResultants,
    WIMomentRegionId,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
)
from frp_master_connection.domain.wi_frp_support_moment import (
    CONTRACT,
    PRODUCT,
    SupportMode,
    WIFrpSupportMomentRequest,
)
from frp_master_connection.domain.wi_wall_moment import WIWallMomentRequest

D = Decimal
ZERO: Rational3 = (Fraction(0), Fraction(0), Fraction(0))
DISCLAIMER = (
    "Rational W/I beam-to-FRP-support moment connection: engineering review and Section 2.3.2 "
    "qualification are required. Complete connector/member/support response, contact, prying, "
    "bolt bending and local receiving-zone interaction need applicable separate source coverage. "
    "The support wrench is this connection's contribution only, not full-column or foundation "
    "analysis. No stiffness, rotation-capacity or full-strength classification is provided."
)


@dataclass(frozen=True, slots=True)
class SupportTransfer:
    connector_id: str
    slice5_region: WIMomentRegionId
    share: Decimal
    core: AngleCoreResult
    flange_demand: EccentricDemandResult | None
    web_demand: InPlaneWrenchResult | None
    support_lvt: AngleWrench
    support_uvn: AngleWrench
    support_at_centroid: AngleWrench
    support_in_plane_demand: InPlaneWrenchResult | None
    support_in_plane_scope: str
    member_out_of_plane_f_c_m_a_m_b: tuple[PhysicalQuantity, ...]
    support_out_of_plane_f_n_m_u_m_v: tuple[PhysicalQuantity, ...]
    frame_id: str = "SUPPORT_ATTACHMENT_U_V_N_EQUALS_BEAM_V_T_L"
    component_order: tuple[str, ...] = ("u", "v", "n")


@dataclass(frozen=True, slots=True)
class SupportEquilibrium:
    inherited_slice5_proof: bool
    connector_proofs: tuple[bool, ...]
    web_group_proofs: tuple[bool, ...]
    proof_passed: bool
    algebraic_target: AngleWrench
    serialized_force_residual: ExactQuantityVector3D
    serialized_moment_residual: ExactQuantityVector3D
    residual_role: str = "ACTUAL_NATIVE_SERIALIZATION_DIAGNOSTIC_NOT_TOLERANCE_OR_REDISTRIBUTION"


@dataclass(frozen=True, slots=True)
class FRPSupportMomentPreview:
    request_id: str
    input: WIFrpSupportMomentRequest
    geometry: FRPSupportMomentGeometry
    slice5: WIMomentComponentResultants
    joint_right_hand_action: AngleWrench
    connectors: tuple[SupportTransfer, ...]
    support_contribution: AngleWrench | None
    support_reaction: AngleWrench | None
    equilibrium: SupportEquilibrium | None
    beam_allocation_applicability: str
    engineering_fingerprint: str
    design_check_ready: bool
    source_availability: tuple[tuple[str, str, str], ...] = ()
    product: str = PRODUCT
    contract: str = CONTRACT
    resistance_evaluated: bool = False
    disclaimer: str = DISCLAIMER
    full_receiving_member_design: str = "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"
    ordinary_pass_allowed: bool = False


def beam_native_input(request: WIFrpSupportMomentRequest) -> WIWallMomentRequest:
    """Read-only structural adapter to pinned material-neutral predecessor helpers.

    Those leaf helpers consume beam/gap/angle/material/action fields only; the
    returned object remains a Stage 4.3 request with no wall or anchor fields.
    Its physical length occupies the legacy local-end mapping seam. Viewer length
    never reaches native local capacity/source boundaries. Regression checks pin
    the consumed helper identities; the full Stage 4.2 service is never invoked.
    """
    return cast(WIWallMomentRequest, request.engineering_input())


def support_uvn(wrench: AngleWrench) -> AngleWrench:
    def rotate(values: Rational3) -> Rational3:
        return values[1], values[2], values[0]

    return AngleWrench(
        quantity_vector(rotate(components(wrench.reference)), Unit.MM),
        quantity_vector(rotate(components(wrench.force)), Unit.N),
        quantity_vector(rotate(components(wrench.moment)), Unit.N_MM),
    )


def support_plane_input(
    geometry: FRPSupportMomentGeometry,
    connector: str,
    wrench: AngleWrench,
) -> InPlaneWrenchRequest:
    bolts = tuple(
        b for b in geometry.support_bolts if b.hardware.group_id == f"{connector}_SUPPORT_GROUP"
    )
    return InPlaneWrenchRequest(
        tuple(
            WrenchBolt(
                b.hardware.hardware_id,
                b.support_point.y.canonical_magnitude,
                b.support_point.z.canonical_magnitude,
            )
            for b in bolts
        ),
        (wrench.reference.x.canonical_magnitude, wrench.reference.y.canonical_magnitude),
        wrench.force.x.canonical_magnitude,
        wrench.force.y.canonical_magnitude,
        wrench.moment.z.canonical_magnitude,
        Unit.MM,
        Unit.N,
        Unit.N_MM,
    )


def _sum_at_reference(values: tuple[AngleWrench, ...]) -> AngleWrench:
    def total(name: str) -> Rational3:
        return cast(
            Rational3,
            tuple(
                sum((components(getattr(v, name))[i] for v in values), Fraction(0))
                for i in range(3)
            ),
        )

    return AngleWrench(
        values[0].reference,
        quantity_vector(total("force"), Unit.N),
        quantity_vector(total("moment"), Unit.N_MM),
    )


def preview_wi_frp_support_moment(
    request: WIFrpSupportMomentRequest,
    *,
    registered_sources: tuple[tuple[str, str], ...] = (),
) -> FRPSupportMomentPreview:
    geometry = resolve_frp_support_moment_geometry(request)
    beam, actions = request.beam, request.actions
    slice5 = calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(
            WIMomentSectionInput(
                beam.depth, beam.flange_width, beam.web_thickness, beam.flange_thickness
            ),
            WIMomentActionInput(
                actions.axial,
                actions.major_shear,
                actions.structural_major_moment,
                actions.minor_shear,
                actions.minor_moment,
                actions.torsion,
            ),
        )
    )
    joint = AngleWrench(
        vector((inch(request.gap), D(0), D(0))),
        quantity_vector(
            (
                Fraction(actions.axial.canonical_magnitude),
                Fraction(actions.major_shear.canonical_magnitude),
                Fraction(0),
            ),
            Unit.N,
        ),
        quantity_vector(
            (
                Fraction(0),
                Fraction(0),
                -Fraction(actions.structural_major_moment.canonical_magnitude),
            ),
            Unit.N_MM,
        ),
    )
    transfers = []
    native_request = beam_native_input(request)
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
            member = member_interface_wrench(native_request, angle, slice5.component(region), share)
            core = resolve_angle_connector(
                AngleCoreRequest(
                    angle.specification.geometry, angle.frame, member, angle.support_reference
                )
            )
            flange = (
                flange_demand(native_request, angle, member)
                if region is not WIMomentRegionId.WEB
                else None
            )
            web = web_demand(angle, member) if region is WIMomentRegionId.WEB else None
            support = global_support_wrench(angle, core.connector_on_support)
            uvn = support_uvn(support)
            shifted = shift_angle_wrench(support, geometry.support.centroid)
            thin = request.support.mode in {
                SupportMode.WI_FLANGE,
                SupportMode.WI_WEB,
                SupportMode.CHANNEL_WEB,
            }
            plane = (
                calculate_in_plane_wrench_demand(
                    support_plane_input(geometry, angle.connector_id, uvn)
                )
                if thin
                else None
            )
            transfers.append(
                SupportTransfer(
                    angle.connector_id,
                    region,
                    share,
                    core,
                    flange,
                    web,
                    support,
                    uvn,
                    shifted,
                    plane,
                    "SEPARATE_THIN_SINGLE_LAP_IN_PLANE_PROJECTION_NOT_COMPLETE_RESPONSE"
                    if thin
                    else "SOURCE_REQUIRED_LONG_PATH_PARTICIPATION_AND_RESPONSE",
                    (member.force.z, member.moment.x, member.moment.y),
                    (uvn.force.z, uvn.moment.x, uvn.moment.y),
                )
            )
    contribution = reaction = equilibrium = None
    if transfers:
        contribution = _sum_at_reference(tuple(t.support_at_centroid for t in transfers))
        reaction = AngleWrench(
            contribution.reference,
            quantity_vector(
                cast(Rational3, tuple(-x for x in components(contribution.force))), Unit.N
            ),
            quantity_vector(
                cast(Rational3, tuple(-x for x in components(contribution.moment))), Unit.N_MM
            ),
        )
        target = shift_angle_wrench(joint, geometry.support.centroid)
        inherited = all(
            (
                slice5.equilibrium.axial_equilibrium_exact,
                slice5.equilibrium.shear_equilibrium_exact,
                slice5.equilibrium.moment_equilibrium_exact,
            )
        )
        core_proofs = tuple(
            components(t.core.equilibrium.force) == components(t.core.equilibrium.moment) == ZERO
            for t in transfers
        )
        web_proofs = tuple(
            t.web_demand.solution.proof is not None and t.web_demand.solution.proof.passed
            for t in transfers
            if t.web_demand is not None
        )

        def residual(name: str) -> ExactQuantityVector3D:
            return quantity_vector(
                cast(
                    Rational3,
                    tuple(
                        a - b
                        for a, b in zip(
                            components(getattr(contribution, name)),
                            components(getattr(target, name)),
                            strict=True,
                        )
                    ),
                ),
                Unit.N if name == "force" else Unit.N_MM,
            )

        equilibrium = SupportEquilibrium(
            inherited,
            core_proofs,
            web_proofs,
            inherited
            and geometry.symmetry_proven
            and all(core_proofs)
            and len(web_proofs) == 2
            and all(web_proofs),
            target,
            residual("force"),
            residual("moment"),
        )
    allocation = (
        "GEOMETRIC_WEB_PAIR_SYMMETRY_SUPPORT_RESPONSE_QUALIFICATION_STILL_REQUIRED"
        if request.support.connection_transverse.canonical_magnitude == 0
        else "SOURCE_REQUIRED_OFFSET_SUPPORT_BRANCH_ALLOCATION_COMPATIBILITY"
    )
    fingerprint = angle_fingerprint(
        (
            PRODUCT,
            CONTRACT,
            request.engineering_input(),
            geometry.fingerprint,
            slice5.result_fingerprint,
            tuple(
                (
                    t.connector_id,
                    t.core.fingerprint,
                    None if t.flange_demand is None else t.flange_demand.result_fingerprint,
                    None if t.web_demand is None else t.web_demand.fingerprint,
                    None
                    if t.support_in_plane_demand is None
                    else t.support_in_plane_demand.fingerprint,
                    t.support_uvn,
                    t.support_at_centroid,
                    t.support_in_plane_scope,
                )
                for t in transfers
            ),
            contribution,
            equilibrium,
            allocation,
        )
    )
    return FRPSupportMomentPreview(
        request.request_id,
        request,
        geometry,
        slice5,
        joint,
        tuple(transfers),
        contribution,
        reaction,
        equilibrium,
        allocation,
        fingerprint,
        geometry.status == "VALID",
        tuple(
            (
                name,
                reference,
                "REGISTERED_REQUIRES_EXACT_APPLICABILITY_CHECK"
                if (name, reference) in registered_sources
                else "SOURCE_REQUIRED_NOT_REGISTERED"
                if reference
                else "SOURCE_REQUIRED_NO_REFERENCE",
            )
            for name, reference in (
                ("COMPLETE_SUPPORT_RESPONSE", request.response_source_reference),
                ("LOCAL_SUPPORT_ZONE", request.local_zone_source_reference),
                *(
                    (f"{name}:{kind}", reference)
                    for name, spec in zip(
                        (
                            "TOP_FLANGE_ANGLE",
                            "BOTTOM_FLANGE_ANGLE",
                            "POSITIVE_WEB_ANGLE",
                            "NEGATIVE_WEB_ANGLE",
                        ),
                        request.angles,
                        strict=True,
                    )
                    for kind, reference in (
                        ("ANGLE_BODY", spec.connector_source_reference),
                        ("MEMBER_ATTACHMENT", spec.attachment_source_reference),
                    )
                ),
            )
        ),
    )
