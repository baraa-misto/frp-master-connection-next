"""Isolated C2-P1 LRFD checks on trusted resolved plans; no family dispatch.

The application owns the plan catalogue. No API accepts that catalogue, path areas,
source approval, U/Ubs or per-hole forces. No demand or block-path solver lives here.
Engineering comparisons use exact rational arithmetic over native unit conversions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.stainless_material import (
    METHOD,
    SOURCE_SHA256,
    StainlessMaterial,
    is_trusted_material,
)

F = Fraction
ZERO = F(0)
TABLE = (
    (F(1, 2), F(9, 16), F(3, 4)),
    (F(5, 8), F(11, 16), F(7, 8)),
    (F(3, 4), F(13, 16), F(1)),
    (F(7, 8), F(15, 16), F(9, 8)),
    (F(1), F(9, 8), F(5, 4)),
)
GEOMETRY_FAILURE = "STAINLESS_CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED"
EXTERNAL = (
    "FRP_MEMBER_NOT_EVALUATED",
    "FASTENER_NOT_EVALUATED",
    "RECEIVING_MEMBER_NOT_EVALUATED",
    "FOUNDATION_ANCHOR_EXTERNAL",
    "CORROSION_SUITABILITY_NOT_EVALUATED",
    "WHOLE_CONNECTION_NOT_EVALUATED",
)


def magnitude(value: PhysicalQuantity, unit: Unit) -> Fraction:
    return F(value.to(unit).magnitude)


def projection(value: Fraction) -> Decimal:
    """Native quantity precision for output only; rational values govern comparisons."""
    with localcontext() as context:
        context.prec = 100
        context.rounding = ROUND_HALF_EVEN
        return Decimal(value.numerator) / Decimal(value.denominator)


def quantity(value: Fraction, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity(projection(value), unit)


@dataclass(frozen=True, slots=True)
class PlateHole:
    id: str
    x: PhysicalQuantity
    y: PhysicalQuantity
    bolt_diameter: PhysicalQuantity
    diameter: PhysicalQuantity
    kind: str = "STANDARD_ROUND"


@dataclass(frozen=True, slots=True)
class PlateGeometry:
    id: str
    width: PhysicalQuantity
    length: PhysicalQuantity
    nominal_thickness: PhysicalQuantity
    holes: tuple[PlateHole, ...] = ()
    frame: str = "PLATE_LOCAL_X_Y_Z"
    elements_in_contact: bool = False
    continuous_contact: bool = False
    thinner_contact_thickness: PhysicalQuantity | None = None
    reduced_edge_exception: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedPlateDemand:
    id: str
    load_combination: str
    force: PhysicalQuantity
    reference: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    frame: str
    direction: str
    response_method: str
    material_dependent: bool = False
    response_qualified: bool = False


@dataclass(frozen=True, slots=True)
class PlateCheckPlan:
    """Canonical section/path/hole plan supplied by trusted server context.

    Section lengths derive areas with design thickness. Block areas are explicit
    resolved-path output, never raw client area inputs or an FRP-path assumption.
    """

    id: str
    family: str
    kind: str
    demand: ResolvedPlateDemand | None
    physical_ids: tuple[str, ...] = ()
    gross_length: PhysicalQuantity | None = None
    net_length: PhysicalQuantity | None = None
    distribution: str = "UNRESOLVED"
    agv: PhysicalQuantity | None = None
    anv: PhysicalQuantity | None = None
    ant: PhysicalQuantity | None = None
    l1: PhysicalQuantity | None = None
    l1_basis: str = "UNRESOLVED"
    deformation_considered: bool = True
    path_kind: str = "STRAIGHT"


@dataclass(frozen=True, slots=True)
class PlateRequest:
    geometry: PlateGeometry
    material: StainlessMaterial
    checks: tuple[PlateCheckPlan, ...]
    product_form: str = "FLAT_PLATE"
    fabrication: str = "CUT_DRILLED_MACHINED"
    welding_required: bool = False
    nominal_credit_requested: bool = False


@dataclass(frozen=True, slots=True)
class TrustedPlateRecord:
    """Exact immutable server-approved plan binding, not an HTTP source descriptor."""

    request: PlateRequest
    source_id: str
    content_sha256: str
    geometry_authority: str
    demand_authority: str
    property_domain: tuple[PhysicalQuantity, PhysicalQuantity]
    tolerance_fraction: Decimal | None = None
    tolerance_source: str | None = None


@dataclass(frozen=True, slots=True)
class PlateContext:
    records: tuple[TrustedPlateRecord, ...] = ()
    final_source_sha256: str | None = SOURCE_SHA256


@dataclass(frozen=True, slots=True)
class PlateCheck:
    id: str
    family: str
    method: str
    nominal: PhysicalQuantity
    phi: Decimal
    resistance: PhysicalQuantity
    demand: PhysicalQuantity
    utilization: Decimal
    comparison: str
    rational_resistance: tuple[int, int]
    rational_utilization: tuple[int, int]


@dataclass(frozen=True, slots=True)
class PlateResult:
    geometry_status: str
    material_source_status: str
    method_status: tuple[str, ...]
    demand_status: tuple[str, ...]
    response_status: tuple[str, ...]
    numerical_comparison: str
    checks: tuple[PlateCheck, ...]
    governing: tuple[tuple[str, str], ...]
    nominal_thickness: PhysicalQuantity
    design_thickness: PhysicalQuantity
    thickness_rule: str
    warnings: tuple[str, ...]
    source_trace: tuple[str, ...]
    fingerprint: str
    resolved_input: PlateRequest
    resolved_authority: TrustedPlateRecord | None
    external_scopes: tuple[str, ...] = EXTERNAL
    family_activation: bool = False


def standard_hole(diameter: PhysicalQuantity) -> tuple[PhysicalQuantity, PhysicalQuantity]:
    d = magnitude(diameter, Unit.IN)
    for bolt, hole, edge in TABLE:
        if bolt == d:
            return quantity(hole, Unit.IN), quantity(edge, Unit.IN)
    raise ValueError("STAINLESS_BOLT_DIAMETER_OUTSIDE_AUTOMATIC_J3_TABLE_SCOPE")


def _record(request: PlateRequest, context: PlateContext) -> TrustedPlateRecord | None:
    matches = [record for record in context.records if record.request == request]
    if len(matches) != 1:
        return None
    record = matches[0]
    if not all((record.source_id, record.geometry_authority, record.demand_authority)):
        return None
    if len(record.content_sha256) != 64 or any(
        c not in "0123456789abcdefABCDEF" for c in record.content_sha256
    ):
        return None
    return record


def _geometry(g: PlateGeometry, thickness: Fraction) -> tuple[str, tuple[str, ...]]:
    w, length, nominal = (magnitude(q, Unit.IN) for q in (g.width, g.length, g.nominal_thickness))
    if min(w, length, nominal) <= 0 or not g.id or not g.frame:
        return GEOMETRY_FAILURE, ()
    ids = [hole.id for hole in g.holes]
    if len(set(ids)) != len(ids) or any(not name for name in ids):
        return GEOMETRY_FAILURE, ()
    warnings: list[str] = []
    for hole in g.holes:
        if hole.kind != "STANDARD_ROUND":
            return "STAINLESS_HOLE_TYPE_NOT_SUPPORTED_IN_C2_P1", ()
        try:
            dh, minimum = standard_hole(hole.bolt_diameter)
        except ValueError as error:
            return str(error), ()
        d, actual_hole, x, y = (
            magnitude(q, Unit.IN) for q in (hole.bolt_diameter, hole.diameter, hole.x, hole.y)
        )
        nearest = min(x, w - x, y, length - y)
        if hole.diameter != dh or nearest < actual_hole / 2:
            return GEOMETRY_FAILURE, ()
        if nearest < magnitude(minimum, Unit.IN):
            return (
                "STAINLESS_ENGINEERING_REVIEW_REQUIRED"
                if g.reduced_edge_exception
                else GEOMETRY_FAILURE
            ), ()
        if g.elements_in_contact and nearest > min(12 * thickness, F(6)):
            return GEOMETRY_FAILURE, ()
        for other in g.holes:
            if other.id == hole.id:
                continue
            dx = magnitude(other.x, Unit.IN) - x
            dy = magnitude(other.y, Unit.IN) - y
            squared = dx * dx + dy * dy
            clear_limit = d + (actual_hole + magnitude(other.diameter, Unit.IN)) / 2
            if squared < (F(8, 3) * d) ** 2 or squared < clear_limit**2:
                return GEOMETRY_FAILURE, ()
            if squared < (3 * d) ** 2:
                warnings.append("PREFERRED_3D_SPACING_NOT_PROVIDED")
            adjacent_longitudinal = dx == 0 and not any(
                magnitude(middle.x, Unit.IN) == x
                and min(y, y + dy) < magnitude(middle.y, Unit.IN) < max(y, y + dy)
                for middle in g.holes
            )
            if g.continuous_contact and adjacent_longitudinal:
                if g.thinner_contact_thickness is None:
                    return GEOMETRY_FAILURE, ()
                thinner = min(thickness, magnitude(g.thinner_contact_thickness, Unit.IN))
                if thinner <= 0 or abs(dy) > min(24 * thinner, F(12)):
                    return GEOMETRY_FAILURE, ()
    return "VALID", tuple(sorted(set(warnings)))


def _add(
    checks: list[PlateCheck],
    plan: PlateCheckPlan,
    method: str,
    nominal: Fraction,
    phi: Fraction,
    force: Fraction,
) -> None:
    resistance = nominal * phi
    utilization = abs(force) / resistance
    checks.append(
        PlateCheck(
            plan.id + ":" + method,
            plan.family,
            method,
            quantity(nominal, Unit.KIP),
            projection(phi),
            quantity(resistance, Unit.KIP),
            quantity(force, Unit.KIP),
            projection(utilization),
            "FAIL" if utilization > 1 else "PASS",
            (resistance.numerator, resistance.denominator),
            (utilization.numerator, utilization.denominator),
        )
    )


def _evaluate_plan(
    plan: PlateCheckPlan, request: PlateRequest, t: Fraction, checks: list[PlateCheck]
) -> str | None:
    if plan.demand is None:
        return (
            "STAINLESS_PER_HOLE_DEMAND_NOT_RESOLVED"
            if plan.kind == "HOLE"
            else "STAINLESS_DEMAND_NOT_RESOLVED"
        )
    demand = plan.demand
    if not all(
        (
            plan.id,
            plan.family,
            demand.id,
            demand.load_combination,
            demand.frame,
            demand.direction,
            demand.response_method,
        )
    ):
        return "STAINLESS_DEMAND_NOT_RESOLVED"
    if len(demand.reference) != 3 or any(
        q.dimension is not Dimension.LENGTH for q in demand.reference
    ):
        return "STAINLESS_DEMAND_NOT_RESOLVED"
    force = magnitude(demand.force, Unit.KIP)
    fy, fu = (magnitude(q, Unit.KSI) for q in (request.material.fy, request.material.fu))
    if plan.path_kind != "STRAIGHT":
        return "STAINLESS_STAGGERED_NET_PATH_NOT_SUPPORTED_IN_C2_P1"
    if plan.kind in ("TENSION", "SHEAR"):
        if plan.gross_length is None:
            return GEOMETRY_FAILURE
        gross = magnitude(plan.gross_length, Unit.IN)
        if plan.kind == "TENSION":
            if plan.distribution != "DIRECT_ALL_CROSS_SECTION_ELEMENTS":
                return "STAINLESS_SHEAR_LAG_METHOD_NOT_AVAILABLE"
            if force < 0:
                return "STAINLESS_COMPRESSION_NOT_SUPPORTED_IN_C2_P1"
            holes = {h.id: h for h in request.geometry.holes}
            if len(set(plan.physical_ids)) != len(plan.physical_ids) or any(
                name not in holes for name in plan.physical_ids
            ):
                return GEOMETRY_FAILURE
            net = gross - sum(
                (magnitude(holes[name].diameter, Unit.IN) + F(1, 16) for name in plan.physical_ids),
                ZERO,
            )
        else:
            if plan.net_length is None:
                return GEOMETRY_FAILURE
            net = magnitude(plan.net_length, Unit.IN)
        if not 0 < net <= gross:
            return GEOMETRY_FAILURE
        if plan.kind == "TENSION":
            _add(checks, plan, "TENSILE_GROSS_YIELDING", fy * gross * t, F(9, 10), force)
            _add(checks, plan, "TENSILE_NET_RUPTURE", fu * net * t, F(3, 4), force)
        else:
            _add(
                checks, plan, "SHEAR_YIELDING", F(3, 5) * F(6, 5) * fy * gross * t, F(9, 10), force
            )
            _add(checks, plan, "SHEAR_RUPTURE", F(3, 5) * fu * net * t, F(3, 4), force)
    elif plan.kind == "BLOCK":
        if plan.distribution not in ("UNIFORM", "NONUNIFORM") or any(
            q is None for q in (plan.agv, plan.anv, plan.ant)
        ):
            return "STAINLESS_BLOCK_PATH_NOT_RESOLVED"
        agv, anv, ant = (
            magnitude(q, Unit.IN2) for q in (plan.agv, plan.anv, plan.ant) if q is not None
        )
        if not 0 < anv <= agv or ant <= 0:
            return GEOMETRY_FAILURE
        ubs = F(1) if plan.distribution == "UNIFORM" else F(1, 2)
        _add(checks, plan, "BLOCK_RUPTURE", F(3, 5) * fu * anv + ubs * fu * ant, F(3, 4), force)
        _add(
            checks,
            plan,
            "SHEAR_YIELD_CAP",
            F(3, 5) * F(6, 5) * fy * agv + ubs * fu * ant,
            F(3, 4),
            force,
        )
    elif plan.kind == "HOLE":
        if not plan.deformation_considered:
            return "STAINLESS_SERVICE_DEFORMATION_NOT_CONSIDERED_METHOD_NOT_AVAILABLE"
        bearing_holes = [h for h in request.geometry.holes if (h.id,) == plan.physical_ids]
        if (
            len(bearing_holes) != 1
            or plan.l1 is None
            or plan.l1_basis
            not in ("EDGE_IN_FORCE_DIRECTION", "HALF_ADJACENT_CENTER_SPACING_IN_FORCE_DIRECTION")
        ):
            return GEOMETRY_FAILURE
        d, dh, l1 = (
            magnitude(q, Unit.IN)
            for q in (bearing_holes[0].bolt_diameter, bearing_holes[0].diameter, plan.l1)
        )
        if l1 <= 0:
            return GEOMETRY_FAILURE
        nominal = F(5, 4) * d * t * fu
        _add(checks, plan, "BEARING", nominal, F(3, 4), force)
        _add(checks, plan, "TEAROUT", nominal * l1 / (2 * dh), F(3, 4), force)
    else:
        return "STAINLESS_METHOD_NOT_SUPPORTED_IN_C2_P1"
    return None


def evaluate_stainless_plate(request: PlateRequest, context: PlateContext) -> PlateResult:
    """Evaluate only exact approved plans. Public CME-1 dispatch never calls this."""
    record = _record(request, context)
    nominal = magnitude(request.geometry.nominal_thickness, Unit.IN)
    credit = (
        record is not None
        and record.tolerance_fraction is not None
        and record.tolerance_source is not None
        and bool(record.tolerance_source)
        and 0 <= record.tolerance_fraction <= Decimal("0.05")
    )
    t = nominal if nominal > F(3, 16) or credit else F(95, 100) * nominal
    rule = (
        "NOMINAL_GT_3_16"
        if nominal > F(3, 16)
        else ("VERIFIED_NOMINAL_CREDIT" if credit else "NOMINAL_LE_3_16_DEFAULT_095")
    )
    geometry, warnings = _geometry(request.geometry, t)
    source = "VERIFIED"
    if context.final_source_sha256 != SOURCE_SHA256:
        source = "STAINLESS_SOURCE_AUTHORITY_NOT_LOCKED"
    elif not is_trusted_material(request.material) or record is None:
        source = "STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED"
    elif (
        not 0
        < magnitude(record.property_domain[0], Unit.IN)
        <= nominal
        <= magnitude(record.property_domain[1], Unit.IN)
    ):
        source = "STAINLESS_PROPERTY_DOMAIN_NOT_APPLICABLE"
    methods: list[str] = []
    if request.product_form not in ("FLAT_PLATE", "FLAT_SHEET", "FLAT_STRIP"):
        methods.append("STAINLESS_PRODUCT_FORM_NOT_SUPPORTED")
    if request.fabrication != "CUT_DRILLED_MACHINED":
        methods.append("STAINLESS_FABRICATION_METHOD_NOT_SUPPORTED")
    if request.welding_required:
        methods.append("STAINLESS_WELDING_AUTHORITY_NOT_AVAILABLE")
    if request.nominal_credit_requested and nominal <= F(3, 16) and not credit:
        methods.append("STAINLESS_NOMINAL_THICKNESS_CREDIT_NOT_QUALIFIED")
    checks: list[PlateCheck] = []
    demands: list[str] = []
    response: list[str] = []
    if geometry == "VALID" and source == "VERIFIED" and not methods:
        if not request.checks or len({p.id for p in request.checks}) != len(request.checks):
            methods.append("STAINLESS_CHECK_PLAN_NOT_RESOLVED")
        else:
            for plan in request.checks:
                problem = _evaluate_plan(plan, request, t, checks)
                if problem:
                    (demands if "DEMAND" in problem else methods).append(problem)
                if (
                    plan.demand is not None
                    and plan.demand.material_dependent
                    and not plan.demand.response_qualified
                ):
                    response.append("STAINLESS_MATERIAL_DEPENDENT_RESPONSE_NOT_QUALIFIED")
    governing: list[tuple[str, str]] = []
    for family in sorted({c.family for c in checks}):
        members = [c for c in checks if c.family == family]
        selected = min(
            members, key=lambda c: (-F(*c.rational_utilization), F(*c.rational_resistance), c.id)
        )
        governing.append((family, selected.id))
    comparison = "NOT_EVALUATED"
    if any(c.comparison == "FAIL" for c in checks):
        comparison = "FAIL"
    elif checks and not methods and not demands:
        comparison = "ISOLATED_COVERED_CHECKS_PASS"
    trace = (
        METHOD,
        request.material.source,
        SOURCE_SHA256,
        request.material.bridge,
        request.material.snapshot,
        request.material.product_specification,
        request.material.general_requirements,
        "B4.2a/B4.4b/D3/J3.2-J3.5/J3.10a/J4.1-J4.3",
    )
    return PlateResult(
        geometry,
        source,
        tuple(methods),
        tuple(demands),
        tuple(sorted(set(response))),
        comparison,
        tuple(checks),
        tuple(governing),
        request.geometry.nominal_thickness,
        quantity(t, Unit.IN),
        rule,
        warnings,
        trace,
        angle_fingerprint(
            (METHOD, request, record, context.final_source_sha256, quantity(t, Unit.IN), rule)
        ),
        request,
        record,
    )
