"""SSMC-2 serial full-wrench demand and explicitly unqualified resistance ledgers."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.application.ssmc_geometry import SSMCGeometry, geometry_ssmc
from frp_master_connection.application.ssmc_member_demand import (
    SSMCMemberTransferDemand,
    member_transfer_demand,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    angle_fingerprint,
    exact_decimal,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.ssmc_material import (
    PROPERTY_DIRECTIONS,
    SSMCPropertySelection,
    select_ssmc_property,
)
from frp_master_connection.calculation.ssmc_response import (
    EMPTY_RESPONSE_REGISTRY,
    SSMCTrustedResponse,
    required_design_status,
    validate_ssmc_response,
)
from frp_master_connection.domain.ssmc import (
    GROUPS,
    MEMBERS,
    PLATE_POLICY,
    SSMC_METHOD_POLICY,
    SSMCMethodPolicy,
    SSMCRequest,
)

Q = PhysicalQuantity
BLOCKERS = (
    "SSMC_SINGLE_SIDE_RESPONSE_NOT_QUALIFIED",
    "SSMC_POLYGON_RESISTANCE_NOT_QUALIFIED",
    "SSMC_MEMBER_FLANGE_WEB_TRANSFER_NOT_QUALIFIED",
    "SSMC_HARDWARE_COMBINED_RESPONSE_NOT_QUALIFIED",
    "SSMC_CW_SOURCE_REQUIRED",
)
POLYGON_MECHANISMS = (
    "BEARING",
    "NET_LIGAMENT",
    "FIRST_ROW",
    "SHEAR_OUT",
    "BLOCK_SHEAR",
    "CLEAVAGE",
    "TRANSITION_NECK",
    "REENTRANT_CORNER",
    "HOLE_TO_EDGE",
    "CONNECTED_LIGAMENT",
    "STABILITY",
)
MEMBER_MECHANISMS = (
    "WEB_RESULTANT",
    "INTERRUPTED_FLANGES",
    "FLANGE_TO_WEB_JUNCTION",
    "WEB_LOCAL_BENDING",
    "WEB_LOCAL_BUCKLING",
    "CUT_END_WEAKENING",
    "SHEAR_CENTER",
    "TORSION_WARPING",
)
PLATE_PROPERTIES = ("FT_T", "FC_T", "FLEXURE_T", "FBR_T", "FSH_LT", "FSH_INT", "TT", "E_G_NU")


def vector(values: tuple[Decimal, ...], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(Q(v, unit) for v in values))


def negate(wrench: AngleWrench) -> AngleWrench:
    def negative(v: ExactQuantityVector3D) -> ExactQuantityVector3D:
        return ExactQuantityVector3D(
            *(Q(q.magnitude.copy_negate(), q.unit) for q in (v.x, v.y, v.z))
        )

    return AngleWrench(wrench.reference, negative(wrench.force), negative(wrench.moment))


@dataclass(frozen=True, slots=True)
class SSMCGroupDemand:
    group_id: str
    member_end_wrench: AngleWrench
    plate_wrench: AngleWrench
    planar_status: str
    native_slice8: object | None
    bolt_axis_tension: None = None
    prying: None = None
    shaft_bending: None = None
    contact_response: None = None


@dataclass(frozen=True, slots=True)
class SSMCPreview:
    input: SSMCRequest
    geometry: SSMCGeometry
    work_point_wrench: AngleWrench
    groups: tuple[SSMCGroupDemand, ...]
    engineering_fingerprint: str
    statuses: tuple[tuple[str, str], ...]
    required_checks: tuple[tuple[str, str, str], ...]
    blockers: tuple[str, ...]
    evaluated_failures: tuple[str, ...]
    whole_connection_status: str
    material_source_ledger: tuple[SSMCPropertySelection, ...]
    trusted_complete_response: SSMCTrustedResponse | None
    member_transfer_demands: tuple[SSMCMemberTransferDemand, ...]
    method_policy: SSMCMethodPolicy = SSMC_METHOD_POLICY
    plate_policy: str = PLATE_POLICY
    qualified_material_snapshot: None = None
    complete_moment_capacity_qualified: bool = False


def preview_ssmc(
    request: SSMCRequest,
    registry: Mapping[str, SSMCTrustedResponse] = EMPTY_RESPONSE_REGISTRY,
) -> SSMCPreview:
    geometry = geometry_ssmc(request)
    unit = request.length_unit
    zero = Decimal(0)
    origin = vector((zero, zero, zero), unit)
    angle = math.radians(float(request.theta_deg))
    c, s = Fraction(str(math.cos(angle))), Fraction(str(math.sin(angle)))
    n, v = Fraction(request.N.to(Unit.N).magnitude), Fraction(request.V.to(Unit.N).magnitude)
    force = vector((exact_decimal(n * c - v * s), zero, exact_decimal(n * s + v * c)), Unit.N)
    first = geometry.members[1].end_reference
    reference = vector(tuple(Decimal(str(x)) for x in (first.x, first.y, first.z)), unit)
    applied = AngleWrench(
        reference,
        force,
        vector((zero, request.M.to(Unit.N_MM).magnitude.copy_negate(), zero), Unit.N_MM),
    )
    at_origin = shift_angle_wrench(applied, origin)
    group_demands = []
    targets = {}
    for index, (owner, group_id, pattern) in enumerate(
        zip(MEMBERS, GROUPS, (request.horizontal_group, request.inclined_group), strict=True)
    ):
        source = negate(at_origin) if index == 0 else at_origin
        end = geometry.members[index].end_reference
        at_end = shift_angle_wrench(
            source, vector(tuple(Decimal(str(x)) for x in (end.x, end.y, end.z)), unit)
        )
        shafts = tuple(b for b in geometry.shafts if b.member == owner)
        # Native exact finite-decimal transport requires a finite reference.
        # Use a physical named group reference (first station pair midpoint),
        # not a rounded repeating arithmetic centroid. Slice 8 shifts it exactly.
        first_pair = shafts[:2]
        group_ref = tuple(
            (
                Fraction(str(getattr(first_pair[0].plate_midpoint, k)))
                + Fraction(str(getattr(first_pair[1].plate_midpoint, k)))
            )
            / 2
            for k in ("x", "y", "z")
        )
        at_plate = shift_angle_wrench(
            source, vector(tuple(exact_decimal(x) for x in group_ref), unit)
        )
        targets[group_id] = at_plate
        native = None
        planar_status = "SSMC_PLANAR_GROUP_RESPONSE_NOT_QUALIFIED"
        if pattern.planar_eligible:
            native = calculate_in_plane_wrench_demand(
                InPlaneWrenchRequest(
                    tuple(WrenchBolt(b.id, str(b.center[0]), str(b.center[1])) for b in shafts),
                    (at_plate.reference.x.magnitude, at_plate.reference.z.magnitude),
                    at_plate.force.x.to(Unit.N).magnitude,
                    at_plate.force.z.to(Unit.N).magnitude,
                    at_plate.moment.y.to(Unit.N_MM).magnitude.copy_negate(),
                    unit,
                    Unit.N,
                    Unit.N_MM,
                )
            )
            planar_status = "CALCULATED_BOUNDED_PLANAR_DEMAND"
        group_demands.append(SSMCGroupDemand(group_id, at_end, at_plate, planar_status, native))
    binding = angle_fingerprint(
        (
            replace(request, request_id="SSMC_CANONICAL"),
            SSMC_METHOD_POLICY,
            tuple(m.trimmed.geometry_fingerprint for m in geometry.members),
            tuple(tuple(format(v, ".17g") for v in p) for p in geometry.polygon.boundary),
            geometry.polygon.edge_ids,
            tuple(
                (g.group_id, g.member_end_wrench, g.plate_wrench, g.planar_status)
                for g in group_demands
            ),
        )
    )
    blockers = list(BLOCKERS)
    failures: tuple[str, ...] = ()
    trusted = registry.get(binding)
    if trusted is not None:
        validate_ssmc_response(
            trusted, binding, {s.id: s.group for s in geometry.shafts}, targets, origin
        )
        blockers.remove("SSMC_SINGLE_SIDE_RESPONSE_NOT_QUALIFIED")
        failures = trusted.numerical_failures
    if any(g.native_slice8 is None for g in group_demands):
        blockers.append("SSMC_PLANAR_GROUP_RESPONSE_NOT_QUALIFIED")
    if request.source_reference or request.fastener.source_reference:
        blockers.append("SSMC_TRUSTED_AUTHORITY_NOT_BOUND")
    checks = tuple(
        ("MITER_WEB_PLATE", mechanism, "SSMC_POLYGON_RESISTANCE_NOT_QUALIFIED")
        for mechanism in POLYGON_MECHANISMS
    )
    checks += tuple(
        (owner, mechanism, "SSMC_MEMBER_FLANGE_WEB_TRANSFER_NOT_QUALIFIED")
        for owner in MEMBERS
        for mechanism in MEMBER_MECHANISMS
    )
    checks += tuple(
        ("MITER_WEB_PLATE", prop, "SSMC_CW_SOURCE_REQUIRED") for prop in PLATE_PROPERTIES
    )
    checks += tuple(
        (shaft.id, "COMBINED_RESPONSE", "SSMC_HARDWARE_COMBINED_RESPONSE_NOT_QUALIFIED")
        for shaft in geometry.shafts
    )
    status = required_design_status(failures, tuple(blockers))
    statuses = (
        ("Geometry", "VALID"),
        ("Demand", "CALCULATED"),
        (
            "Planar group response",
            "CALCULATED_BOUNDED_PLANAR_DEMAND"
            if all(g.native_slice8 is not None for g in group_demands)
            else "SSMC_PLANAR_GROUP_RESPONSE_NOT_QUALIFIED",
        ),
        ("Complete response", "TRUSTED_RESPONSE_BOUND" if trusted is not None else BLOCKERS[0]),
        ("Plate resistance", BLOCKERS[1]),
        ("Member local transfer", BLOCKERS[2]),
        ("Hardware", BLOCKERS[3]),
        ("Qualification", "REQUIRED_QUALIFICATION_MISSING"),
        ("Design", status),
    )
    return SSMCPreview(
        request,
        geometry,
        at_origin,
        tuple(group_demands),
        binding,
        statuses,
        checks,
        tuple(blockers),
        failures,
        status,
        tuple(select_ssmc_property(binding, check) for check in PROPERTY_DIRECTIONS),
        trusted,
        tuple(
            member_transfer_demand(section, member, group.member_end_wrench)
            for section, member, group in zip(
                (request.horizontal, request.inclined), geometry.members, group_demands, strict=True
            )
        ),
    )


def design_ssmc(request: SSMCRequest) -> SSMCPreview:
    """Production design is the same truthful source-limited demand workflow."""
    return preview_ssmc(request)
