"""Inactive owner-confirmed geometry and same-surface arithmetic witnesses.

Actual cuts are geometric evidence. Applying the workbook's scalar stress-area
sum to an oblique connector is explicitly NOT an adopted orthotropic failure law.
Old DirectGeometry/d_span and every R1/R2 execution remain unchanged.
"""

import json
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from hashlib import sha256

from .quantities import PhysicalQuantity, Unit, decimal_value
from .rhm_direct_corrections import (
    DirectCorrections,
    NetCut,
    PhysicalCut,
    PhysicalHole,
    Point,
    execute_direct_corrections,
    net_cut,
)
from .rhm_direct_reference import execute_direct_source, q, sincos
from .rhm_reference import PRECISION, bolt_shear_capacity, reference_quantity

STREAM = "OWNER_CONFIRMED_GEOMETRY_R3"
ORDER_SHA256 = "b081f0e95676043a22e2fbba4a05bbde6aaf8589f40e7875fcd7c5339356f102"
OWNER_SKETCH_SHA256 = "bbc9e20cf2eebbac69cb3d2916120ab75429cfe7fde586155f1fa77bff76564c"
METHOD_LIMIT = (
    "STRUCTURAL_METHOD_COVERAGE_PENDING: actual oblique connector, source directional "
    "strength choices and scalar P/V interaction are arithmetic witnesses; no adopted "
    "orthotropic mixed-mode law, first-row, junction or independent side-path coverage."
)
ZERO = Decimal(0)
_LENGTHS = {v: q(v) for v in ("2", ".4375", "1", "4", ".5", ".375", ".563", "0")}


def dot(a: Point, b: Point) -> Decimal:
    return a[0] * b[0] + a[1] * b[1]


def add(a: Point, b: Point, scale: Decimal = Decimal(1)) -> Point:
    return a[0] + scale * b[0], a[1] + scale * b[1]


@dataclass(frozen=True, slots=True)
class R3Geometry:
    vertical_bolt_pitch: PhysicalQuantity = _LENGTHS["2"]
    phi: Decimal = Decimal("30.9")
    xb: PhysicalQuantity = _LENGTHS[".4375"]
    xc: PhysicalQuantity = _LENGTHS["1"]
    brace_near_v_edge_distance: PhysicalQuantity = _LENGTHS["1"]
    brace_leg: PhysicalQuantity = _LENGTHS["4"]
    column_flange: PhysicalQuantity = _LENGTHS["4"]
    brace_thickness: PhysicalQuantity = _LENGTHS[".5"]
    column_thickness: PhysicalQuantity = _LENGTHS[".375"]
    diameter: PhysicalQuantity = _LENGTHS[".5"]
    hole: PhysicalQuantity = _LENGTHS[".563"]
    midpoint: tuple[PhysicalQuantity, PhysicalQuantity] = (_LENGTHS["0"], _LENGTHS["0"])
    frame_rotation_degrees: Decimal = ZERO
    reverse_bolt_order: bool = False

    def __post_init__(self) -> None:
        sincos(self.phi)
        angle = decimal_value(self.frame_rotation_degrees)
        if not 0 <= angle < 90 or not isinstance(self.reverse_bolt_order, bool):
            raise ValueError("Rigid review frame requires 0 <= rotation < 90 and Boolean ordering.")
        for value in (
            self.vertical_bolt_pitch,
            self.xb,
            self.xc,
            self.brace_near_v_edge_distance,
            self.brace_leg,
            self.column_flange,
            self.brace_thickness,
            self.column_thickness,
            self.diameter,
            self.hole,
        ):
            reference_quantity(value, Unit.IN)
        for value in self.midpoint:
            decimal_value(value.to(Unit.IN).magnitude)
        if self.hole < self.diameter:
            raise ValueError("Actual circular hole cannot be smaller than bolt.")
        if self.brace_thickness >= self.brace_leg or self.column_thickness >= self.column_flange:
            raise ValueError("Section thickness must be below its declared width.")


_DEFAULT_GEOMETRY = R3Geometry()
_DEFAULT_AXIAL = q("91.55", Unit.LBF)
_DEFAULT_SHEAR = q("13.4", Unit.LBF)


def geometry_digest(geometry: R3Geometry) -> str:
    """Mechanics input identity; camera state is deliberately not an operand."""
    return sha256(json.dumps(asdict(geometry), sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Edge:
    member: str
    edge_id: str
    normal: Point
    offset_in: Decimal
    endpoints: tuple[Point, Point] | None
    provenance: str


@dataclass(frozen=True, slots=True)
class RayPath:
    member: str
    branch: str
    bolt_id: str
    edge_id: str
    start: Point
    direction: Point
    end: Point | None
    length_in: Decimal | None
    signed_parameter_in: Decimal | None
    reason: str


def intersect_edge(
    member: str, branch: str, bolt_id: str, start: Point, direction: Point, edge: Edge
) -> RayPath:
    """Directed line intersection with explicit finite-edge and member checks."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        start = tuple_point(start)
        direction = tuple_point(direction)
        normal = tuple_point(edge.normal)
        k = decimal_value(edge.offset_in)
        norm2 = dot(direction, direction)
        if norm2 == 0 or dot(normal, normal) == 0:
            raise ValueError("Nonzero finite ray and edge normal required.")
        den = dot(normal, direction)
        reason = "WRONG_MEMBER" if member != edge.member else "PARALLEL_TO_EDGE" if den == 0 else ""
        if reason:
            return RayPath(
                member, branch, bolt_id, edge.edge_id, start, direction, None, None, None, reason
            )
        parameter = (k - dot(normal, start)) / den
        end = add(start, direction, parameter)
        if parameter <= 0:
            reason = "NONPOSITIVE_DIRECTED_EDGE_DISTANCE"
        elif edge.endpoints is not None:
            lo, hi = edge.endpoints
            segment = add(hi, lo, Decimal(-1))
            station = dot(add(end, lo, Decimal(-1)), segment)
            if not 0 <= station <= dot(segment, segment):
                reason = "OUTSIDE_FINITE_EDGE"
        return RayPath(
            member,
            branch,
            bolt_id,
            edge.edge_id,
            start,
            direction,
            end,
            parameter * norm2.sqrt() if not reason else None,
            parameter,
            reason,
        )


def tuple_point(point: Point) -> Point:
    return decimal_value(point[0]), decimal_value(point[1])


@dataclass(frozen=True, slots=True)
class R3Block:
    member: str
    branch: str
    member_action_axis: Point
    release_axis: Point
    edge: Edge
    paths: tuple[RayPath, ...]
    cuts: tuple[NetCut, ...]
    shear_gross_area_in2: Decimal
    shear_removed_area_in2: Decimal
    shear_net_area_in2: Decimal
    connector_gross_area_in2: Decimal
    connector_removed_area_in2: Decimal
    connector_net_area_in2: Decimal
    perpendicular_projected_gross_area_in2: Decimal
    perpendicular_projected_removed_area_in2: Decimal
    perpendicular_projected_net_area_in2: Decimal
    available: bool
    disposition: str


@dataclass(frozen=True, slots=True)
class R3Check:
    method_id: str
    variant: str
    demands_kip: tuple[Decimal, ...]
    capacities_kip: tuple[Decimal, ...]
    utilization: Decimal | None
    numerical_outcome: str
    equation: str
    source_cells: str
    applicability: str


@dataclass(frozen=True, slots=True)
class Dependency:
    quantity: str
    old_meaning: str
    r3_meaning: str
    old_value: str
    new_value: str
    disposition: str


@dataclass(frozen=True, slots=True)
class R3Record:
    geometry: R3Geometry
    input_digest: str
    bolt_centers: tuple[tuple[str, Point], ...]
    p_axis: Point
    n_axis: Point
    sketch_v_axis: Point
    projection_foot: Point
    vertical_pitch_in: Decimal
    transverse_ltv_in: Decimal
    longitudinal_stagger_in: Decimal
    edges: tuple[Edge, ...]
    hole_fit: bool
    blocks: tuple[R3Block, ...]
    checks: tuple[R3Check, ...]
    factor_trace: tuple[tuple[str, Decimal], ...]
    factor_ledger: tuple[str, ...]
    dependencies: tuple[Dependency, ...]
    rotation_centers: tuple[tuple[str, Point], ...]
    rotation_fit: bool
    rotation_blocks: tuple[R3Block, ...]
    placement_contract: str
    limitations: tuple[str, ...]
    geometry_status: str = "OWNER_SPACING_AND_AXES_RECONCILED"
    stream: str = STREAM
    order_sha256: str = ORDER_SHA256
    sketch_sha256: str = OWNER_SKETCH_SHA256
    actual_coverage_credited: tuple[str, ...] = ()
    public_activation: bool = False
    qualification: str = "SECTION_2_3_2_UNRESOLVED"


def _frame(g: R3Geometry, point: Point, *, vector: bool = False) -> Point:
    if g.frame_rotation_degrees == 0:
        s, c = ZERO, Decimal(1)
    else:
        s, c = sincos(g.frame_rotation_degrees)
    x, y = point
    result = c * x - s * y, s * x + c * y
    if vector:
        return result
    return add(result, (g.midpoint[0].to(Unit.IN).magnitude, g.midpoint[1].to(Unit.IN).magnitude))


def signed_force(
    g: R3Geometry,
    axial: PhysicalQuantity,
    sketch_v: PhysicalQuantity,
    *,
    positive_n_basis: bool = False,
) -> tuple[Point, Point]:
    """Same Cartesian force; switching from sketch -n to backend +n negates V."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        p, v = (decimal_value(x.to(Unit.LBF).magnitude) for x in (axial, sketch_v))
        s, c = sincos(g.phi)
        return (p, -v if positive_n_basis else v), _frame(
            g, (p * c - v * s, -p * s - v * c), vector=True
        )


def _edges(g: R3Geometry, n: Point, top: Point) -> tuple[Edge, ...]:
    xb, xc, near, width, cw = (
        x.to(Unit.IN).magnitude
        for x in (g.xb, g.xc, g.brace_near_v_edge_distance, g.brace_leg, g.column_flange)
    )
    k = dot(n, top) + near
    # These datums are in the local gauge. Transform equations with the same rigid frame.
    local = (
        Edge(
            "BRACE",
            "BRACE_END_X_MINUS_XB",
            (Decimal(1), ZERO),
            -xb,
            ((-xb, (k - width + n[0] * xb) / n[1]), (-xb, (k + n[0] * xb) / n[1])),
            "Source Xb is independent end-edge to bolt-column datum, not a thickness recipe.",
        ),
        Edge(
            "BRACE",
            "BRACE_TRANSVERSE_PLUS",
            n,
            k,
            None,
            f"Independent near-B1 centerline edge input={near} in; "
            "source nominal 1 in; offset explicitly n.B1+near.",
        ),
        Edge(
            "BRACE",
            "BRACE_TRANSVERSE_MINUS",
            n,
            k - width,
            None,
            f"Opposite boundary from declared brace leg={width} in; no pixel measurement.",
        ),
        Edge(
            "COLUMN",
            "COLUMN_RIGHT_XC",
            (Decimal(1), ZERO),
            xc,
            None,
            f"Declared Xc={xc} in (source nominal 1); column end cuts unspecified.",
        ),
        Edge(
            "COLUMN",
            "COLUMN_LEFT_XC_MINUS_WIDTH",
            (Decimal(1), ZERO),
            xc - cw,
            None,
            f"Declared column width={cw} in; opposite signed V reaction reaches this edge.",
        ),
    )
    result = []
    midpoint = g.midpoint[0].to(Unit.IN).magnitude, g.midpoint[1].to(Unit.IN).magnitude
    for e in local:
        normal = _frame(g, e.normal, vector=True)
        endpoints = None if e.endpoints is None else tuple(_frame(g, p) for p in e.endpoints)
        result.append(
            Edge(
                e.member,
                e.edge_id,
                normal,
                e.offset_in + dot(normal, midpoint),
                None if endpoints is None else (endpoints[0], endpoints[1]),
                e.provenance,
            )
        )
    return tuple(result)


def _fit(g: R3Geometry, centers: tuple[tuple[str, Point], ...], edges: tuple[Edge, ...]) -> bool:
    radius = g.hole.to(Unit.IN).magnitude / 2
    for _, center in centers:
        distances = tuple(
            (e.offset_in - dot(e.normal, center)) / dot(e.normal, e.normal).sqrt() for e in edges
        )
        # End and lower brace boundary are inward-positive; other boundaries inward-negative.
        if min(-distances[0], distances[1], -distances[2], distances[3], -distances[4]) < radius:
            return False
    delta = add(centers[0][1], centers[1][1], Decimal(-1))
    return dot(delta, delta).sqrt() >= 2 * radius


def _blocks(
    g: R3Geometry,
    centers: tuple[tuple[str, Point], ...],
    edges: tuple[Edge, ...],
    p: Point,
    n: Point,
    fit: bool,
) -> tuple[R3Block, ...]:
    output = []
    for member, thickness in (("BRACE", g.brace_thickness), ("COLUMN", g.column_thickness)):
        holes = tuple(PhysicalHole(member, name, xy, g.hole) for name, xy in centers)
        for branch in ("P", "V"):
            # Brace receives +P*p - V*n; column receives its opposite reaction.
            action = p if branch == "P" else (-n[0], -n[1])
            if member == "COLUMN":
                action = -action[0], -action[1]
            release = -action[0], -action[1]
            index = (
                (0 if branch == "P" else 1) if member == "BRACE" else (3 if branch == "P" else 4)
            )
            edge = edges[index]
            paths = tuple(
                intersect_edge(member, branch, name, xy, release, edge) for name, xy in centers
            )
            cuts = tuple(
                net_cut(
                    PhysicalCut(
                        member, f"{branch}:SHEAR:{path.bolt_id}", path.start, path.end, thickness
                    ),
                    holes,
                )
                for path in paths
                if path.length_in is not None and path.end is not None
            )
            connector = net_cut(
                PhysicalCut(
                    member, f"{branch}:OBLIQUE_CONNECTOR", centers[0][1], centers[1][1], thickness
                ),
                holes,
            )
            cuts = (*cuts, connector)
            av = sum((cut.gross_area_in2 for cut in cuts[:-1]), ZERO)
            ds = sum((cut.removed_area_in2 for cut in cuts[:-1]), ZERO)
            delta = add(centers[0][1], centers[1][1], Decimal(-1))
            projection = (
                abs(delta[0] * release[1] - delta[1] * release[0]) / connector.gross_length_in
            )
            valid = fit and len(cuts) == 3 and all(cut.available for cut in cuts)
            output.append(
                R3Block(
                    member,
                    branch,
                    action,
                    release,
                    edge,
                    paths,
                    cuts,
                    av,
                    ds,
                    av - ds,
                    connector.gross_area_in2,
                    connector.removed_area_in2,
                    connector.net_area_in2,
                    connector.gross_area_in2 * projection,
                    connector.removed_area_in2 * projection,
                    connector.net_area_in2 * projection,
                    valid,
                    "EDGE_AND_HOLE_GEOMETRY_RECONCILED"
                    if valid
                    else "AFFECTED_PATH_UNAVAILABLE: hole fit, directed edge or net "
                    "material invalid",
                )
            )
    return tuple(output)


def _check(
    key: str,
    variant: str,
    demands: tuple[Decimal, ...],
    caps: tuple[Decimal, ...],
    equation: str,
    cells: str,
    valid: bool,
    scope: str,
) -> R3Check:
    available = valid and all(c > 0 for c in caps)
    ur = sum((d / c for d, c in zip(demands, caps, strict=True)), ZERO) if available else None
    return R3Check(
        key,
        variant,
        demands,
        caps,
        ur,
        "NOT_EVALUATED" if ur is None else "PASS" if ur <= 1 else "FAIL",
        equation,
        cells,
        scope,
    )


def execute_r3(
    *,
    geometry: R3Geometry = _DEFAULT_GEOMETRY,
    axial: PhysicalQuantity = _DEFAULT_AXIAL,
    shear: PhysicalQuantity = _DEFAULT_SHEAR,
    temperature_f: int = 100,
) -> R3Record:
    """Fresh geometry and seven comparisons per gross/net stream, never public resistance."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        p_load, v_load = (
            reference_quantity(x, Unit.KIP, zero_allowed=True) for x in (axial, shear)
        )
        g = geometry
        pitch = g.vertical_bolt_pitch.to(Unit.IN).magnitude
        s, c = sincos(g.phi)
        local_centers = (("B1", (ZERO, pitch / 2)), ("B2", (ZERO, -pitch / 2)))
        centers = tuple((name, _frame(g, xy)) for name, xy in local_centers)
        if g.reverse_bolt_order:
            centers = tuple(reversed(centers))
        p, n = _frame(g, (c, -s), vector=True), _frame(g, (s, c), vector=True)
        foot = _frame(g, add(local_centers[0][1], (c, -s), pitch * s))
        edges = _edges(g, (s, c), local_centers[0][1])
        fit = _fit(g, centers, edges)
        blocks = _blocks(g, centers, edges, p, n, fit)
        # Only fixed source property/temperature authority is reused, not old geometry/results.
        source = execute_direct_source(temperature_f=temperature_f)
        ops = {x.name: x.quantity for x in source.comparisons[0].operands}
        ts = ops["Ts"].magnitude
        fs = ops["brace_shear_LW_CW_allowable_before_Ts"].to(Unit.KSI).magnitude * ts
        ft_lw = ops["brace_tension_LW_allowable_before_Ts"].to(Unit.KSI).magnitude * ts
        ft_cw = ops["brace_tension_CW_allowable_before_Ts"].to(Unit.KSI).magnitude * ts
        bcw = ops["brace_bearing_CW_allowable_before_Ts"].to(Unit.KSI).magnitude * ts
        blw = ops["brace_bearing_LW_allowable_before_Ts"].to(Unit.KSI).magnitude * ts * ts
        d = g.diameter.to(Unit.IN).magnitude
        bolt = bolt_shear_capacity(2, 1, g.diameter, q("12.75", Unit.KSI)).to(Unit.KIP).magnitude
        checks: list[R3Check] = []
        for variant in ("R3_ACTUAL_GROSS_ARITHMETIC", "R3_SAME_SURFACE_NET_ARITHMETIC"):
            checks.append(
                _check(
                    "DIRECT_SHARED_BOLTS",
                    variant,
                    ((p_load * p_load + v_load * v_load).sqrt(),),
                    (bolt,),
                    "sqrt(P^2+V^2)/(2*pi*d^2/4*12.75)",
                    "D46;D159",
                    fit,
                    "SOURCE_UNIFORM_CENTROID_REFERENCE_ONLY",
                )
            )
            for member, thickness in (("BRACE", g.brace_thickness), ("COLUMN", g.column_thickness)):
                t = thickness.to(Unit.IN).magnitude
                checks.append(
                    _check(
                        f"DIRECT_{member}_BEARING",
                        variant,
                        (v_load, p_load),
                        (2 * d * t * bcw, 2 * d * t * (blw if member == "BRACE" else bcw)),
                        "V/(2*d*t*FbV)+P/(2*d*t*FbP)",
                        "D34" if member == "BRACE" else "D146",
                        fit,
                        "SOURCE_UNIFORM_CENTROID_REFERENCE_ONLY",
                    )
                )
                selected = tuple(b for b in blocks if b.member == member)
                for block in selected:
                    for path in block.paths:
                        # Local tear-out is edge-to-centerline, with no hole deduction.
                        capacity = ZERO if path.length_in is None else 2 * path.length_in * t * fs
                        checks.append(
                            _check(
                                f"{member}_LOCAL_{block.branch}_{path.bolt_id}",
                                variant,
                                ((p_load if block.branch == "P" else v_load) / 2,),
                                (capacity,),
                                "(component/2)/(2*actual_edge_to_centerline*t*Fs)",
                                "D53:D75" if member == "BRACE" else "D183:D205",
                                fit and path.length_in is not None,
                                "PER_BOLT_LOCAL_SOURCE_ASSUMPTION_NOT_GENERAL_ECCENTRIC_TRANSFER",
                            )
                        )
                local_caps = tuple(
                    2 * min((path.length_in or ZERO) for path in b.paths) * t * fs for b in selected
                )
                checks.append(
                    _check(
                        f"DIRECT_{member}_LOCAL",
                        variant,
                        (p_load / 2, v_load / 2),
                        local_caps,
                        "sum component/n over shortest independent local 2*L*t*Fs; "
                        "per-bolt rows retained",
                        "D75" if member == "BRACE" else "D205",
                        all(b.available for b in selected),
                        "SOURCE_UNIFORM_CENTROID_REFERENCE_ONLY",
                    )
                )
                capacities = []
                for b in selected:
                    av = (
                        b.shear_gross_area_in2
                        if variant == "R3_ACTUAL_GROSS_ARITHMETIC"
                        else b.shear_net_area_in2
                    )
                    at = (
                        b.connector_gross_area_in2
                        if variant == "R3_ACTUAL_GROSS_ARITHMETIC"
                        else b.connector_net_area_in2
                    )
                    ft = ft_lw if member == "BRACE" and b.branch == "P" else ft_cw
                    if member == "COLUMN" and b.branch == "V":
                        ft *= ts
                    capacities.append(av * fs + (at or ZERO) * ft)
                checks.append(
                    _check(
                        f"DIRECT_{member}_GLOBAL",
                        variant,
                        (p_load, v_load),
                        tuple(capacities),
                        "P/(Fs*actual_AvP+FtP*actual_AtP)+V/(Fs*actual_AvV+FtV*actual_AtV); "
                        "oblique-connector arithmetic only, NOT an adopted mixed-mode law",
                        "D121" if member == "BRACE" else "D239",
                        all(b.available for b in selected),
                        METHOD_LIMIT,
                    )
                )
        rotated_local = (
            ("B1", (-pitch * c / 2, pitch * s / 2)),
            ("B2", (pitch * c / 2, -pitch * s / 2)),
        )
        rotated = tuple((name, _frame(g, xy)) for name, xy in rotated_local)
        rotated_fit = _fit(g, rotated, edges)
        rotated_blocks = _blocks(g, rotated, edges, p, n, rotated_fit)
        old_pitch = Decimal(2) / c
        deps = [
            Dependency(
                "L52/L53",
                "Legacy 2/c at current phi; saved nominal R2 separately executed",
                "R3 actual shared connector",
                str(old_pitch),
                str(pitch),
                "Changed physical pair; source gross area not carried forward",
            ),
            Dependency(
                "L64/L65",
                "R2 2*cos(phi) effective width",
                "R3 transverse center projection, not a V tensile face",
                str(Decimal(2) * c),
                str(pitch * c),
                "Same number, changed semantic role; actual connector recalculated",
            ),
            Dependency(
                "V-perpendicular projection",
                "Legacy (2/cos)*sin at current phi; saved R2 separate",
                "actual pitch*sin",
                str(old_pitch * s),
                str(pitch * s),
                "Not LTV",
            ),
            Dependency(
                "moment lever arm",
                "Legacy 2/cos at current phi; saved R2 separate",
                "new actual pitch",
                str(old_pitch),
                str(pitch),
                "Isolated equal-stiffness equilibrium only; no finite-moment resistance adoption",
            ),
        ]
        for b in blocks:
            deps.append(
                Dependency(
                    f"{b.member}:{b.branch}:Lv/At/net",
                    "R2 repeated short Lv and unrelated effective At",
                    "two actual directed cuts + same actual connector/hole union",
                    "See preserved R2 record; never subtracted here",
                    str(asdict(b)),
                    b.disposition,
                )
            )
        for row in checks:
            if row.method_id.startswith("DIRECT_"):
                deps.append(
                    Dependency(
                        row.method_id + ":" + row.variant,
                        "Workbook/R2 separately preserved",
                        row.equation,
                        "See unchanged predecessor records",
                        str(row.utilization),
                        row.applicability,
                    )
                )
        return R3Record(
            g,
            sha256(
                json.dumps(
                    {
                        "geometry": geometry_digest(g),
                        "P_kip": str(p_load),
                        "sketch_V_kip": str(v_load),
                        "temperature_f": temperature_f,
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
            centers,
            p,
            n,
            (-n[0], -n[1]),
            foot,
            pitch,
            pitch * c,
            pitch * s,
            edges,
            fit,
            blocks,
            tuple(checks),
            (
                ("Ts", ts),
                ("SF", Decimal(4)),
                ("Fs", fs),
                ("FtLW", ft_lw),
                ("FtCW", ft_cw),
                ("FtColumnV_extra_Ts", ft_cw * ts),
                ("FbBraceLW_Ts_twice", blw),
            ),
            source.factor_ledger,
            tuple(deps),
            rotated,
            rotated_fit,
            rotated_blocks,
            "Midpoint is explicit gauge transform; x=-Xb, column x=Xc and x=Xc-width are fixed. "
            f"Brace +n edge anchored by independent SOURCE near-B1 edge-to-centerline input="
            f"{g.brace_near_v_edge_distance.to(Unit.IN).magnitude} in; "
            "opposite edge offset by declared brace leg. Rebuilding anchor is "
            "recorded, not held-global-boundary parity. "
            "Release rays oppose each member's action; opposite column reactions retained.",
            (
                METHOD_LIMIT,
                f"Hole {g.hole.to(Unit.IN).magnitude} in is explicit review input, "
                "not owner measurement; "
                "zero extra allowance.",
                "Column longitudinal end-cut positions and brace distal end are "
                "not supplied; nominal face only, no complete fit claim.",
                "Source positive P/sketch V, independent ASD, centroid/uniform "
                "demands only; no general eccentric adoption.",
                "C13, native F8/F9 authority and all qualifications remain unchanged.",
            ),
        )


@dataclass(frozen=True, slots=True)
class R3Moment:
    forces_lbf: tuple[Point, Point]
    sum_force_lbf: Point
    reconstructed_moment_lbf_in: Decimal
    actual_lever_arm_in: Decimal
    applicability: str = "ISOLATED_PLANAR_EQUILIBRIUM_ONLY_NOT_ADOPTED_FRP_STRESS_TRANSFER"


def moment_witness_r3(
    g: R3Geometry, fx: PhysicalQuantity, fy: PhysicalQuantity, moment: PhysicalQuantity
) -> R3Moment:
    """Fx/Fy and M already transported to the declared pair midpoint in local gauge."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        x, y, m = (
            decimal_value(v.to(u).magnitude)
            for v, u in ((fx, Unit.LBF), (fy, Unit.LBF), (moment, Unit.LBF_IN))
        )
        pitch = g.vertical_bolt_pitch.to(Unit.IN).magnitude
        forces = ((x / 2 - m / pitch, y / 2), (x / 2 + m / pitch, y / 2))
        return R3Moment(
            forces,
            (forces[0][0] + forces[1][0], forces[0][1] + forces[1][1]),
            pitch / 2 * (forces[1][0] - forces[0][0]),
            pitch,
        )


@dataclass(frozen=True, slots=True)
class R3ReviewBundle:
    current: R3Record
    predecessor: DirectCorrections
    dependency_ledger: tuple[Dependency, ...]
    moment: R3Moment
    baseline_scope: str = (
        "Unchanged original/R2 nominal source controls; NOT the corrected physical pair."
    )


def execute_r3_review(
    *,
    geometry: R3Geometry = _DEFAULT_GEOMETRY,
    axial: PhysicalQuantity = _DEFAULT_AXIAL,
    shear: PhysicalQuantity = _DEFAULT_SHEAR,
    temperature_f: int = 100,
) -> R3ReviewBundle:
    """Execute named predecessor streams independently; do not graft R3 onto d_span."""
    record = execute_r3(geometry=geometry, axial=axial, shear=shear, temperature_f=temperature_f)
    old = execute_direct_corrections(axial=axial, shear=shear, temperature_f=temperature_f)
    ledger = list(record.dependencies)
    for b in record.blocks:
        prior = next(x for x in old.physical_blocks if (x.member, x.branch) == (b.member, b.branch))
        for label, a, z in (
            ("Lv1", prior.cuts[0].gross_length_in, b.paths[0].length_in),
            ("Lv2", prior.cuts[1].gross_length_in, b.paths[1].length_in),
            ("shear gross", prior.actual_shear_gross_area_in2, b.shear_gross_area_in2),
            ("shear removed", prior.removed_shear_area_in2, b.shear_removed_area_in2),
            ("shear net", prior.actual_shear_net_area_in2, b.shear_net_area_in2),
            ("connector gross", prior.actual_tension_gross_area_in2, b.connector_gross_area_in2),
            ("connector removed", prior.removed_tension_area_in2, b.connector_removed_area_in2),
            ("connector net", prior.actual_tension_net_area_in2, b.connector_net_area_in2),
        ):
            ledger.append(
                Dependency(
                    f"{b.member}:{b.branch}:{label}",
                    "R2 actual cut ledger",
                    "R3 actual same-surface ledger",
                    str(a),
                    str(z),
                    b.disposition,
                )
            )
    for member, index in (("BRACE", 3), ("COLUMN", 6)):
        for variant, old_variant in (
            ("R3_ACTUAL_GROSS_ARITHMETIC", "LTV_ONLY"),
            ("R3_SAME_SURFACE_NET_ARITHMETIC", "COMBINED_CONDITIONAL"),
        ):
            current = next(
                c
                for c in record.checks
                if c.method_id == f"DIRECT_{member}_GLOBAL" and c.variant == variant
            )
            previous = next(
                x for x in old.variants if x.member == member and x.variant == old_variant
            )
            ledger.append(
                Dependency(
                    "D121" if member == "BRACE" else "D239",
                    old_variant,
                    variant,
                    str(previous.utilization),
                    str(current.utilization),
                    METHOD_LIMIT,
                )
            )
        for old_check in old.corrected.comparisons:
            if old_check.method_id.startswith(f"DIRECT_{member}_"):
                current = next(c for c in record.checks if c.method_id == old_check.method_id)
                ledger.append(
                    Dependency(
                        old_check.method_id,
                        "R2 COS source arithmetic",
                        "Fresh R3 gross arithmetic",
                        str(old_check.utilization),
                        str(current.utilization),
                        current.applicability,
                    )
                )
        ledger.append(
            Dependency(
                f"{member}:historical global",
                "Historical SIN",
                "R3 gross physical cut",
                str(old.historical.comparisons[index].utilization),
                str(
                    next(
                        c.utilization
                        for c in record.checks
                        if c.method_id == f"DIRECT_{member}_GLOBAL"
                    )
                ),
                METHOD_LIMIT,
            )
        )
    return R3ReviewBundle(
        record,
        old,
        tuple(ledger),
        moment_witness_r3(geometry, q("0", Unit.LBF), q("0", Unit.LBF), q("12", Unit.LBF_IN)),
    )
