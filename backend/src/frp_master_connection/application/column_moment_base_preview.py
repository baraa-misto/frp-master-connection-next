"""Stage 4.5 exact total actions and source-qualified demand preview. No resistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from frp_master_connection.application.column_moment_base_geometry import (
    ColumnMomentGeometry,
    resolve_column_moment_base_geometry,
)
from frp_master_connection.application.column_moment_base_sources import (
    EMPTY_SOURCES,
    ColumnMomentSourceRegistry,
)
from frp_master_connection.application.web_splice_orchestration import WebSpliceMaterialRegion
from frp_master_connection.application.wi_wall_moment_geometry import _bounds, grid
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    BaseBranchDomain,
    FootBreakdownDomain,
    FootBreakdownValidation,
    base_fingerprint,
    is_zero,
    opposite,
    subtract,
    sum_wrenches,
    transform_wrench,
    validate_foot_breakdown,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
    Rational3,
    components,
    exact_decimal,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.column_moment_base_response import (
    BoltLayerDomain,
    ColumnBaseResponseBinding,
    ColumnBaseResponseValidation,
    CoupledBoltDomain,
    QualifiedColumnBaseResponse,
    validate_column_base_response,
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
from frp_master_connection.domain.column_moment_base import (
    CONTRACT,
    PRODUCT,
    ColumnMomentBaseRequest,
)

DISCLAIMER = (
    "Multi-angle column moment base: complete branch/contact/shank response requires exact "
    "applicable qualification. No automatic half or quarter sharing. Rational methods require "
    "engineering review and ASCE Section 2.3.2 qualification. Required foundation actions are "
    "this connection's contribution, not individual anchor forces or capacity. Concrete/anchor "
    "design and whole-column strength/stability are external. Stiffness, rotation capacity and "
    "full-strength classification are not evaluated."
)


@dataclass(frozen=True, slots=True)
class ColumnMomentTransfer:
    connector_id: str
    core: AngleCoreResult
    in_plane_input: InPlaneWrenchRequest
    in_plane_reference_candidate: InPlaneWrenchResult
    member_out_of_plane_f_c_m_a_m_b: tuple[PhysicalQuantity, ...]
    connector_on_foundation: AngleWrench
    foundation_reaction: AngleWrench
    foundation_at_report: AngleWrench
    native_core_equilibrium: bool
    controlling_bolt_response: str = "QUALIFIED_COUPLED_EXPLICIT_LAYER_RESPONSE"
    in_plane_candidate_use: str = "NOT_OVERLAID_ON_QUALIFIED_COUPLED_BOLT_RESPONSE"


@dataclass(frozen=True, slots=True)
class ColumnMomentPreview:
    request_id: str
    input: ColumnMomentBaseRequest
    geometry: ColumnMomentGeometry
    column_on_base: AngleWrench
    required_total_foundation_action: AngleWrench
    opposite_foundation_reaction: AngleWrench
    response_binding: ColumnBaseResponseBinding
    response: ColumnBaseResponseValidation
    branch_allocation_status: str
    transfers: tuple[ColumnMomentTransfer, ...]
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


def _rational(v: tuple[object, ...]) -> Rational3:
    return cast(Rational3, tuple(Fraction(str(x)) for x in v))


def physical_bolt_domains(geometry: ColumnMomentGeometry) -> tuple[CoupledBoltDomain, ...]:
    """Real material layers only; void is a free span, never a force-bearing layer."""
    if geometry.status != "VALID":
        return ()
    domains = []
    mm = Fraction(PhysicalQuantity.of(1, Unit.IN).canonical_magnitude)
    angles = {a.connector_id: a for a in geometry.angles}
    for bolt in geometry.member_bolts:
        owner = bolt.connector_bolt_ids[0][0]
        angle = angles[owner]
        near, far = components(bolt.start), components(bolt.end)
        axis = cast(
            Rational3,
            tuple(
                Fraction(0) if a == b else Fraction(1 if b > a else -1)
                for a, b in zip(near, far, strict=True)
            ),
        )
        axis_index = next(i for i, v in enumerate(axis) if v)
        path = next((p for p in geometry.full_through_paths if p.bolt_id == bolt.hardware_id), None)
        # length, material ID, is_material; all values in canonical millimetres.
        if path is not None:
            intervals = tuple(
                (Fraction(seg.length) * mm, seg.identity, seg in path.material_layers)
                for seg in path.segments
            )
        else:
            first = Fraction(angle.specification.geometry.thickness.canonical_magnitude)
            full = abs(far[axis_index] - near[axis_index])
            if len(bolt.connector_bolt_ids) == 2:
                other = angles[bolt.connector_bolt_ids[1][0]]
                last = Fraction(other.specification.geometry.thickness.canonical_magnitude)
                intervals = (
                    (first, bolt.layers[0], True),
                    (full - first - last, bolt.layers[1], True),
                    (last, bolt.layers[2], True),
                )
            else:
                intervals = ((first, bolt.layers[0], True), (full - first, bolt.layers[1], True))
        offset = Fraction(0)
        layers = []
        for thickness, identity, material in intervals:
            midpoint = cast(
                Rational3, tuple(near[i] + axis[i] * (offset + thickness / 2) for i in range(3))
            )
            offset += thickness
            if not material:
                continue
            connector = next((face for face in angles if identity == face + "_MEMBER_LEG"), None)
            # Native R14B region, not a camera-derived or assumed plate basis.
            point_in = tuple(v / mm for v in midpoint)
            part = next(
                p
                for p in geometry.parts
                if p.material_region is not None
                and all(
                    Fraction(lo) <= v <= Fraction(hi)
                    for lo, v, hi in zip(*(_bounds(p)[0], point_in, _bounds(p)[1]), strict=True)
                )
            )
            region = cast(WebSpliceMaterialRegion, part.material_region)
            basis = (
                _rational(region.lw_axis),
                _rational(region.cw_axis),
                _rational(region.tt_axis),
            )
            layers.append(
                BoltLayerDomain(
                    identity,
                    quantity_vector(midpoint, Unit.MM),
                    connector,
                    basis,
                    PhysicalQuantity(exact_decimal(thickness), Unit.MM),
                    "ACTUAL_ANGLE_UPRIGHT"
                    if connector
                    else "QUALIFIED_3D_SOLID_REGION_REQUIRED"
                    if len(geometry.full_through_paths) > 0 and len(intervals) == 3
                    else "ACTUAL_RECEIVING_PROFILE_REGION",
                )
            )
        domains.append(
            CoupledBoltDomain(
                bolt.hardware_id,
                owner,
                axis,
                _rational(angle.frame.a),
                _rational(angle.frame.b),
                tuple(layers),
                base_fingerprint((bolt, path, tuple(layers))),
            )
        )
    return tuple(domains)


def base_response_binding(
    request: ColumnMomentBaseRequest, geometry: ColumnMomentGeometry, required: AngleWrench
) -> ColumnBaseResponseBinding:
    mm = Fraction(PhysicalQuantity.of(1, Unit.IN).canonical_magnitude)
    return ColumnBaseResponseBinding(
        geometry.fingerprint,
        base_fingerprint(request.engineering_input()),
        base_fingerprint((create_locked_ice_material_snapshot(), request.engineering_input())),
        required,
        tuple(
            BaseBranchDomain(
                a.connector_id, "COLUMN_" + a.connector_id, a.frame, a.heel, a.member_reference
            )
            for a in geometry.angles
        ),
        tuple(
            cast(
                tuple[Fraction, Fraction, Fraction, Fraction],
                tuple(Fraction(v) * mm for v in p.xy_bounds),
            )
            for p in geometry.footprints
            if p.owner_id == "COLUMN"
        ),
        physical_bolt_domains(geometry),
        request.column.family,
        request.layout,
    )


def preview_column_moment_base(
    request: ColumnMomentBaseRequest, sources: ColumnMomentSourceRegistry = EMPTY_SOURCES
) -> ColumnMomentPreview:
    geometry = resolve_column_moment_base_geometry(request)
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
    validation = validate_column_base_response(binding, record)
    transfers = []
    contact = None
    status = validation.status
    zero = is_zero(applied) and not request.response_source_reference
    if geometry.status == "VALID" and (validation.qualified or zero):
        contact = (
            AngleWrench(origin, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM))
            if zero
            else cast(QualifiedColumnBaseResponse, validation.response).column_on_foundation_contact
        )
        if zero:
            status = "NOT_REQUIRED_ZERO_DEMAND"
        for angle in geometry.angles:
            if zero:
                branch = AngleWrench(
                    angle.member_reference,
                    quantity_vector(ZERO, Unit.N),
                    quantity_vector(ZERO, Unit.N_MM),
                )
            else:
                branch = next(
                    b.member_action
                    for b in cast(QualifiedColumnBaseResponse, validation.response).branches
                    if b.domain.connector_id == angle.connector_id
                )
            core = resolve_angle_connector(
                AngleCoreRequest(
                    angle.specification.geometry,
                    angle.frame,
                    branch,
                    angle.support_reference,
                )
            )
            native = InPlaneWrenchRequest(
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
            demand = calculate_in_plane_wrench_demand(native)
            support = transform_wrench(
                core.connector_on_support, angle.frame, angle.heel, angle.support_reference_global
            )
            transfers.append(
                ColumnMomentTransfer(
                    angle.connector_id,
                    core,
                    native,
                    demand,
                    (branch.force.z, branch.moment.x, branch.moment.y),
                    support,
                    opposite(support),
                    shift_angle_wrench(support, origin),
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
                if a.group_id == transfer.connector_id + "_FOUNDATION_GROUP"
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
    fp = base_fingerprint(
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
    return ColumnMomentPreview(
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
        fp,
        geometry.status == "VALID",
        tuple(breakdowns),
    )
