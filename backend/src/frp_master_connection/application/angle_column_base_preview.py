"""Stateless Stage 4.4 geometry/demand preview; no resistance evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from frp_master_connection.application.angle_column_base_geometry import (
    AngleBaseGeometry,
    resolve_angle_base_geometry,
)
from frp_master_connection.application.angle_column_base_sources import (
    EMPTY_SOURCES,
    AngleBaseSourceRegistry,
)
from frp_master_connection.application.wi_wall_moment_geometry import grid
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    BaseBranchDomain,
    BaseResponseBinding,
    BaseResponseValidation,
    FootBreakdownDomain,
    FootBreakdownValidation,
    QualifiedBaseResponse,
    base_fingerprint,
    is_zero,
    opposite,
    subtract,
    sum_wrenches,
    transform_wrench,
    validate_base_response,
    validate_foot_breakdown,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
    components,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    InPlaneWrenchResult,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.properties import create_locked_ice_material_snapshot
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    CONTRACT,
    PRODUCT,
    AngleColumnMomentBaseRequest,
)

DISCLAIMER = (
    "Two-leg Angle-column base: complete branch/contact sharing needs exact applicable "
    "qualified response authority. Rational methods require engineering review and ASCE "
    "Section 2.3.2 qualification. Total foundation actions are this connection's contribution, "
    "not anchor forces or foundation capacity. Concrete/anchor design and overall column "
    "strength/stability are external. Stiffness, rotation capacity and full-strength "
    "classification are not evaluated. No automatic 50/50 sharing."
)


@dataclass(frozen=True, slots=True)
class AngleBaseTransfer:
    connector_id: str
    core: AngleCoreResult
    in_plane_input: InPlaneWrenchRequest
    in_plane_demand: InPlaneWrenchResult
    member_out_of_plane_f_c_m_a_m_b: tuple[PhysicalQuantity, ...]
    connector_on_foundation: AngleWrench
    foundation_reaction: AngleWrench
    foundation_at_report: AngleWrench
    native_core_equilibrium: bool


@dataclass(frozen=True, slots=True)
class AngleBasePreview:
    request_id: str
    input: AngleColumnMomentBaseRequest
    geometry: AngleBaseGeometry
    column_on_base: AngleWrench
    required_total_foundation_action: AngleWrench
    opposite_foundation_reaction: AngleWrench
    response_binding: BaseResponseBinding
    response: BaseResponseValidation
    branch_allocation_status: str
    transfers: tuple[AngleBaseTransfer, ...]
    direct_column_contact: AngleWrench | None
    assembled_foundation_action: AngleWrench | None
    assembled_force_residual: ExactQuantityVector3D | None
    assembled_moment_residual: ExactQuantityVector3D | None
    exact_total_transport: bool
    engineering_fingerprint: str
    design_check_ready: bool
    foundation_breakdowns: tuple[FootBreakdownValidation, ...]
    product: str = PRODUCT
    contract: str = CONTRACT
    resistance_evaluated: bool = False
    ordinary_whole_connection_pass_allowed: bool = False
    foundation_strength_status: str = "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    overall_column_status: str = "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"
    classification_status: str = "STIFFNESS_ROTATION_FULL_STRENGTH_NOT_EVALUATED"
    disclaimer: str = DISCLAIMER


def base_response_binding(
    request: AngleColumnMomentBaseRequest, geometry: AngleBaseGeometry, required: AngleWrench
) -> BaseResponseBinding:
    mm = Fraction(PhysicalQuantity.of(1, Unit.IN).canonical_magnitude)
    return BaseResponseBinding(
        geometry.fingerprint,
        base_fingerprint(request.engineering_input()),
        base_fingerprint(
            (create_locked_ice_material_snapshot(), request.column.material_id, request.connectors)
        ),
        required,
        tuple(
            BaseBranchDomain(
                a.connector_id, f"COLUMN_LEG_{i + 1}", a.frame, a.heel, a.member_reference
            )
            for i, a in enumerate(geometry.angles)
        ),
        tuple(
            cast(
                tuple[Fraction, Fraction, Fraction, Fraction],
                tuple(v * mm for v in map(Fraction, p.xy_bounds)),
            )
            for p in geometry.footprints
            if p.owner_id == "ANGLE_COLUMN"
        ),
    )


def preview_angle_column_moment_base(
    request: AngleColumnMomentBaseRequest, sources: AngleBaseSourceRegistry = EMPTY_SOURCES
) -> AngleBasePreview:
    geometry = resolve_angle_base_geometry(request)
    a = request.actions
    applied = AngleWrench(
        geometry.column_centroid,
        ExactQuantityVector3D(a.shear_x, a.shear_y, a.axial),
        ExactQuantityVector3D(a.moment_x, a.moment_y, a.applied_torque_z),
    )
    origin = quantity_vector(ZERO, Unit.MM)
    required = shift_angle_wrench(applied, origin)
    binding = base_response_binding(request, geometry, required)
    record = next(
        (r for r in sources.responses if r.reference == request.response_source_reference), None
    )
    validation = validate_base_response(binding, record)
    transfers = []
    contact = None
    status = validation.status
    # Zero/no-preload is a no-demand case, not a synthetic qualified-capacity source.
    zero = is_zero(applied) and not request.response_source_reference
    if geometry.status == "VALID" and (validation.qualified or zero):
        if zero:
            status = "NOT_REQUIRED_ZERO_DEMAND"
            contact = AngleWrench(
                origin, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM)
            )
        else:
            contact = cast(QualifiedBaseResponse, validation.response).column_on_foundation_contact
        for angle in geometry.angles:
            if zero:
                branch = AngleWrench(
                    angle.member_reference,
                    quantity_vector(ZERO, Unit.N),
                    quantity_vector(ZERO, Unit.N_MM),
                )
            else:
                qualified_response = cast(QualifiedBaseResponse, validation.response)
                branch = next(
                    b.member_action
                    for b in qualified_response.branches
                    if b.domain.connector_id == angle.connector_id
                )
            core = resolve_angle_connector(
                AngleCoreRequest(
                    angle.specification.geometry, angle.frame, branch, angle.support_reference
                )
            )
            # Hand the native finite wrench straight to Slice 8 in its canonical units.
            # No kip round-trip, recreated force vectors or equivalent eccentricity.
            native_input = InPlaneWrenchRequest(
                tuple(
                    WrenchBolt(
                        ident,
                        PhysicalQuantity(x, Unit.IN).canonical_magnitude,
                        PhysicalQuantity(y, Unit.IN).canonical_magnitude,
                    )
                    for ident, x, y in grid(angle.specification.member_pattern)
                ),
                (branch.reference.x.canonical_magnitude, branch.reference.y.canonical_magnitude),
                branch.force.x.canonical_magnitude,
                branch.force.y.canonical_magnitude,
                branch.moment.z.canonical_magnitude,
                Unit.MM,
                Unit.N,
                Unit.N_MM,
            )
            demand = calculate_in_plane_wrench_demand(native_input)
            global_support_reference = angle.support_reference_global
            support = transform_wrench(
                core.connector_on_support, angle.frame, angle.heel, global_support_reference
            )
            at_report = shift_angle_wrench(support, origin)
            transfers.append(
                AngleBaseTransfer(
                    angle.connector_id,
                    core,
                    native_input,
                    demand,
                    (branch.force.z, branch.moment.x, branch.moment.y),
                    support,
                    opposite(support),
                    at_report,
                    is_zero(core.equilibrium),
                )
            )
    breakdowns = []
    for transfer in transfers:
        footprint = next(f for f in geometry.footprints if f.owner_id == transfer.connector_id)
        mm = Fraction(PhysicalQuantity.of(1, Unit.IN).canonical_magnitude)
        domain = FootBreakdownDomain(
            transfer.connector_id,
            geometry.fingerprint,
            transfer.core.fingerprint,
            transfer.connector_on_foundation,
            tuple(
                (
                    a.hardware_id,
                    ExactQuantityVector3D(a.start.x, a.start.y, PhysicalQuantity.of(0, Unit.MM)),
                )
                for a in geometry.foundation_attachments
                if a.group_id == f"{transfer.connector_id}_FOUNDATION_GROUP"
            ),
            cast(
                tuple[Fraction, Fraction, Fraction, Fraction],
                tuple(Fraction(v) * mm for v in footprint.xy_bounds),
            ),
        )
        breakdowns.append(
            validate_foot_breakdown(
                domain, () if validation.response is None else validation.response.foot_breakdowns
            )
        )
    # Net foot wrenches are counted once; breakdown actions never enter this sum.
    assembled = (
        None
        if contact is None
        else sum_wrenches((*tuple(t.foundation_at_report for t in transfers), contact), origin)
    )
    rf = (
        None
        if assembled is None
        else quantity_vector(
            subtract(components(assembled.force), components(required.force)), Unit.N
        )
    )
    rm = (
        None
        if assembled is None
        else quantity_vector(
            subtract(components(assembled.moment), components(required.moment)), Unit.N_MM
        )
    )
    if geometry.status != "VALID":
        status = "INVALID_GEOMETRY"
    fingerprint = base_fingerprint(
        (
            CONTRACT,
            request.engineering_input(),
            geometry.fingerprint,
            applied,
            required,
            binding,
            validation,
            tuple(transfers),
            contact,
            assembled,
            rf,
            rm,
            tuple(breakdowns),
        )
    )
    return AngleBasePreview(
        request.request_id,
        request,
        geometry,
        applied,
        required,
        opposite(required),
        binding,
        validation,
        status,
        tuple(transfers),
        contact,
        assembled,
        rf,
        rm,
        True,
        fingerprint,
        geometry.status == "VALID",
        tuple(breakdowns),
    )
