"""Inactive R2 arithmetic and actual circle/cut evidence, never adopted resistance.

Source effective areas and physical cut-surface areas are different records. The
source-minus-hole scenarios are explicit conditional arithmetic sensitivities;
unreconciled effective-length geometry cannot install actual net resistance.
"""

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from .quantities import PhysicalQuantity, Unit, decimal_value
from .rhm_direct_reference import (
    DirectCandidateStream,
    DirectGeometry,
    DirectSourceCase,
    execute_direct_source,
    q,
    sincos,
    source_paths,
)
from .rhm_reference import PRECISION, ReferenceStream, additive_comparison, reference_quantity

ORDER_SHA256 = "5818f42056ae28965f5f9704cfde4914332bc5328b2bfe933a647814194ba475"
METHOD_VERSION = "HYB2-D1-R2-CORRECTED-LTV-REFERENCE"
ENDPOINT_QUESTION = (
    "For each global V branch, which two physical endpoints define d_span=2 in, "
    "and what is the V direction relative to that segment, so d_span*cos(phi) "
    "is its force-perpendicular fracture length with the unchanged bolt centers?"
)
Point = tuple[Decimal, Decimal]
_DEFAULT_GEOMETRY = DirectGeometry()
_DEFAULT_SHEAR = q("13.4", Unit.LBF)
_DEFAULT_AXIAL = q("91.55", Unit.LBF)


@dataclass(frozen=True, slots=True)
class PhysicalHole:
    member: str
    hole_id: str
    center: Point
    diameter: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class PhysicalCut:
    member: str
    cut_id: str
    start: Point
    end: Point
    thickness: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class HoleIntersection:
    hole_id: str
    entry_in: Decimal
    exit_in: Decimal
    removed_length_in: Decimal
    diameter_fraction: Decimal
    disposition: str


@dataclass(frozen=True, slots=True)
class NetCut:
    cut: PhysicalCut
    gross_length_in: Decimal
    removed_length_in: Decimal
    gross_area_in2: Decimal
    removed_area_in2: Decimal
    net_area_in2: Decimal
    intersections: tuple[HoleIntersection, ...]
    available: bool


def net_cut(cut: PhysicalCut, holes: tuple[PhysicalHole, ...]) -> NetCut:
    """Intersect actual circles with a finite physical cut; union each removed interval.

    Exact endpoint/collinearity identities have no invented engineering tolerance.
    A hole can intersect two different surfaces of a release; it is counted once
    on each surface and never duplicated on the same surface.
    """
    with localcontext() as ctx:
        ctx.prec = PRECISION
        coordinates = tuple(decimal_value(v) for p in (cut.start, cut.end) for v in p)
        x, y, ex, ey = coordinates
        dx, dy = ex - x, ey - y
        a = dx * dx + dy * dy
        if not cut.member or not cut.cut_id or a == 0:
            raise ValueError("A named member/cut and distinct finite endpoints are required.")
        length = a.sqrt()
        thickness = reference_quantity(cut.thickness, Unit.IN)
        ids: set[tuple[str, str]] = set()
        hits: list[HoleIntersection] = []
        intervals: list[tuple[Decimal, Decimal]] = []
        for hole in holes:
            key = hole.member, hole.hole_id
            if not all(key) or key in ids:
                raise ValueError("Actual hole identities must be nonempty and unique per member.")
            ids.add(key)
            diameter = reference_quantity(hole.diameter, Unit.IN)
            hx, hy = (decimal_value(v) for v in hole.center)
            if hole.member != cut.member:
                continue
            rx, ry = hx - x, hy - y
            cross = rx * dy - ry * dx
            radius = diameter / 2
            if cross * cross >= radius * radius * a:
                # Equality is tangency: zero material length, not a hole allowance.
                hits.append(
                    HoleIntersection(
                        hole.hole_id,
                        Decimal(0),
                        Decimal(0),
                        Decimal(0),
                        Decimal(0),
                        "NO_LENGTH_INTERSECTION",
                    )
                )
                continue
            position = (rx * dx + ry * dy) / length
            if hole.center == cut.start:
                position = Decimal(0)
            elif hole.center == cut.end:
                position = length
            half = (radius * radius - cross * cross / a).sqrt()
            lo, hi = max(Decimal(0), position - half), min(length, position + half)
            if hi <= lo:
                hits.append(
                    HoleIntersection(
                        hole.hole_id, lo, hi, Decimal(0), Decimal(0), "OUTSIDE_SEGMENT"
                    )
                )
                continue
            removed = hi - lo
            kind = "PARTIAL_CHORD"
            if (
                cross == 0
                and (hole.center == cut.start or hole.center == cut.end)
                and length >= radius
            ):
                removed, kind = radius, "HALF_AT_CENTER_ENDPOINT"
            elif cross == 0 and position - radius >= 0 and position + radius <= length:
                removed, kind = diameter, "FULL_CENTERLINE_DIAMETER"
            hits.append(HoleIntersection(hole.hole_id, lo, hi, removed, removed / diameter, kind))
            intervals.append((lo, hi))
        merged: list[tuple[Decimal, Decimal]] = []
        for lo, hi in sorted(intervals):
            if merged and lo <= merged[-1][1]:
                merged[-1] = merged[-1][0], max(merged[-1][1], hi)
            else:
                merged.append((lo, hi))
        removed_length = sum((hi - lo for lo, hi in merged), Decimal(0))
        gross, removed_area = length * thickness, removed_length * thickness
        net = gross - removed_area
        return NetCut(cut, length, removed_length, gross, removed_area, net, tuple(hits), net > 0)


@dataclass(frozen=True, slots=True)
class PhysicalBlock:
    member: str
    branch: str
    cuts: tuple[NetCut, ...]
    force_axis: Point
    force_perpendicular_width_in: Decimal
    actual_shear_gross_area_in2: Decimal
    actual_tension_gross_area_in2: Decimal
    removed_shear_area_in2: Decimal
    removed_tension_area_in2: Decimal
    actual_shear_net_area_in2: Decimal
    actual_tension_net_area_in2: Decimal
    disposition: str = "EXPLICIT_2D_CUT_GEOMETRY_ONLY_NO_STRESS_TRANSFER_ADOPTION"


def physical_blocks(g: DirectGeometry) -> tuple[PhysicalBlock, ...]:
    """Same two centers/holes per actual member; positive source P/V directions only.

    The brace V cut rays reach the same physical free edge, giving unequal 1/3-in
    lengths in the saved case. They are not relabelled as two source 1-in paths.
    The vertical connector is an actual cut surface, not automatically its projected
    or calibrated effective length. Source/effective-area mismatch remains explicit.
    """
    with localcontext() as ctx:
        ctx.prec = PRECISION
        paths = source_paths(g)
        if not paths.fit:
            raise ValueError("Physical source holes must be contained and non-overlapping.")
        s, c = sincos(g.phi)
        top, bottom = paths.bolt_centers
        span, xb, xc, lv = (
            v.to(Unit.IN).magnitude for v in (g.d_span, g.xb, g.xc, g.brace_v_length)
        )
        holes = tuple(
            PhysicalHole(member, f"B{i}", center, g.hole)
            for member in ("BRACE", "COLUMN")
            for i, center in enumerate(paths.bolt_centers, 1)
        )
        blocks: list[PhysicalBlock] = []
        for member, thick in (("BRACE", g.brace_thickness), ("COLUMN", g.column_thickness)):
            for branch in ("V", "P"):
                cuts: list[NetCut] = []
                for i, center in enumerate((top, bottom), 1):
                    _, y = center
                    if branch == "P":
                        end = (-xb, y + xb * s / c) if member == "BRACE" else (xc, y - xc * s / c)
                    elif member == "BRACE":
                        distance = lv if i == 1 else lv + span
                        end = distance * s, y + distance * c
                    else:
                        end = xc, y + xc * c / s
                    cuts.append(
                        net_cut(
                            PhysicalCut(member, f"{branch}:SHEAR:{i}", center, end, thick), holes
                        )
                    )
                cuts.append(
                    net_cut(PhysicalCut(member, f"{branch}:TENSION", top, bottom, thick), holes)
                )
                shear_gross = sum((cut.gross_area_in2 for cut in cuts[:2]), Decimal(0))
                shear_removed = sum((cut.removed_area_in2 for cut in cuts[:2]), Decimal(0))
                axis = (c, -s) if branch == "P" else (s, c)
                width = span if branch == "P" else paths.vertical_spacing.magnitude * s
                tension = cuts[2]
                blocks.append(
                    PhysicalBlock(
                        member,
                        branch,
                        tuple(cuts),
                        axis,
                        width,
                        shear_gross,
                        tension.gross_area_in2,
                        shear_removed,
                        tension.removed_area_in2,
                        shear_gross - shear_removed,
                        tension.net_area_in2,
                    )
                )
        return tuple(blocks)


@dataclass(frozen=True, slots=True)
class BranchCorrection:
    member: str
    branch: str
    variant: str
    ltv_in: Decimal
    source_shear_area_in2: Decimal
    source_tension_area_in2: Decimal
    removed_shear_area_in2: Decimal
    removed_tension_area_in2: Decimal
    conditional_net_shear_area_in2: Decimal
    conditional_net_tension_area_in2: Decimal
    listed_shear_stress_ksi: Decimal
    listed_tension_stress_ksi: Decimal
    allowable_shear_stress_ksi: Decimal
    allowable_tension_stress_ksi: Decimal
    listed_stress_area_sum_kip: Decimal | None
    allowable_capacity_kip: Decimal | None
    demand_kip: Decimal
    ratio: Decimal | None
    source_cells: tuple[str, ...]
    cell_trace: tuple[tuple[str, Decimal | None], ...]
    available: bool
    reason: str
    applicability: str = "PHYSICAL_EFFECTIVE_LENGTH_NOT_RECONCILED_REFERENCE_ONLY"


@dataclass(frozen=True, slots=True)
class GlobalCorrection:
    member: str
    variant: str
    branches: tuple[BranchCorrection, ...]
    utilization: Decimal | None
    numerical_outcome: str


@dataclass(frozen=True, slots=True)
class DirectCorrections:
    historical: DirectSourceCase
    corrected: DirectSourceCase
    physical_blocks: tuple[PhysicalBlock, ...]
    variants: tuple[GlobalCorrection, ...]
    historical_ltv_in: Decimal
    corrected_ltv_in: Decimal
    vertical_bolt_spacing_in: Decimal
    actual_v_perpendicular_spacing_in: Decimal
    d_segment_projection_endpoints: tuple[Point, Point]
    endpoint_question: str = ENDPOINT_QUESTION
    order_sha256: str = ORDER_SHA256
    actual_hole_input_provenance: str = "EXPLICIT_REVIEW_GEOMETRY_INPUT_NOT_ORIGINAL_XLSX_OPERAND"
    additional_hole_allowance_in: Decimal = Decimal(0)
    net_sensitivity_scope: str = (
        "SOURCE_EFFECTIVE_AREA_MINUS_ACTUAL_CUT_HOLE_AREA_IS_CONDITIONAL_"
        "NOT_A_VERIFIED_NET_RESISTANCE"
    )
    physical_applicability: str = "NOT_RECONCILED"
    actual_coverage_credited: tuple[str, ...] = ()
    public_activation: bool = False
    qualification: str = "SECTION_2_3_2_UNRESOLVED"


def execute_direct_corrections(
    *,
    geometry: DirectGeometry = _DEFAULT_GEOMETRY,
    shear: PhysicalQuantity = _DEFAULT_SHEAR,
    axial: PhysicalQuantity = _DEFAULT_AXIAL,
    temperature_f: int = 100,
) -> DirectCorrections:
    """Recompute isolated COS, isolated actual-hole removal and combined sensitivities.

    Hole subtraction from an unreconciled *effective* area is labelled conditional.
    Actual cut net areas are independently recorded and never silently substituted
    for source effective areas. Nonpositive residuals withhold only that comparison.
    """
    historical = execute_direct_source(
        geometry=geometry,
        shear=shear,
        axial=axial,
        stream=ReferenceStream.HISTORICAL_REPLICATION,
        temperature_f=temperature_f,
    )
    base = execute_direct_source(
        geometry=geometry, shear=shear, axial=axial, temperature_f=temperature_f
    )
    blocks = physical_blocks(geometry)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        s, c = sincos(geometry.phi)
        span = geometry.d_span.to(Unit.IN).magnitude
        old_ltv, new_ltv = span * s, span * c
        lengths = {k: v.to(Unit.IN).magnitude for k, v in base.paths.lengths}
        ops = {op.name: op.quantity for op in base.comparisons[0].operands}
        ts = ops["Ts"].magnitude
        v, p = shear.to(Unit.KIP).magnitude, axial.to(Unit.KIP).magnitude
        variants: list[GlobalCorrection] = []
        for name, ltv, remove in (
            ("HISTORICAL_GROSS", old_ltv, False),
            ("LTV_ONLY", new_ltv, False),
            ("HOLES_ONLY_CONDITIONAL", old_ltv, True),
            ("COMBINED_CONDITIONAL", new_ltv, True),
        ):
            for member, thick in (
                ("BRACE", geometry.brace_thickness),
                ("COLUMN", geometry.column_thickness),
            ):
                t = thick.to(Unit.IN).magnitude
                rows: list[BranchCorrection] = []
                for branch, demand in (("V", v), ("P", p)):
                    physical = next(b for b in blocks if b.member == member and b.branch == branch)
                    lv = (
                        (
                            geometry.brace_v_length.to(Unit.IN).magnitude
                            if member == "BRACE"
                            else lengths["L63"]
                        )
                        if branch == "V"
                        else lengths["L55" if member == "BRACE" else "L54"]
                    )
                    lt = ltv if branch == "V" else lengths["L53" if member == "BRACE" else "L52"]
                    av, at = 2 * lv * t, lt * t
                    ds = physical.removed_shear_area_in2 if remove else Decimal(0)
                    dt = physical.removed_tension_area_in2 if remove else Decimal(0)
                    ans, ant = av - ds, at - dt
                    fs = (
                        ops[
                            "brace_shear_LW_CW_allowable_before_Ts"
                            if member == "BRACE"
                            else "column_shear_CW_allowable_before_Ts"
                        ]
                        .to(Unit.KSI)
                        .magnitude
                    )
                    ft = (
                        ops[
                            "brace_tension_LW_allowable_before_Ts"
                            if member == "BRACE" and branch == "P"
                            else "brace_tension_CW_allowable_before_Ts"
                            if member == "BRACE"
                            else "column_tension_CW_allowable_before_Ts"
                        ]
                        .to(Unit.KSI)
                        .magnitude
                    )
                    afs, aft = fs * ts, ft * ts
                    if member == "COLUMN" and branch == "V":
                        aft *= ts  # Existing D221 repeated Ts remains unchanged.
                    valid = ans > 0 and ant > 0
                    nominal = ans * fs * 4 + ant * ft * 4 if valid else None
                    capacity = ans * afs + ant * aft if valid else None
                    ratio = demand / capacity if capacity is not None else None
                    cells = (
                        ("D98", "D101", "D104", "D105")
                        if member == "BRACE" and branch == "V"
                        else ("D112", "D115", "D118", "D119")
                        if member == "BRACE"
                        else ("D216", "D219", "D222", "D223")
                        if branch == "V"
                        else ("D230", "D233", "D236", "D237")
                    )
                    shear_cap = ans * afs if ans > 0 else None
                    tension_cap = ant * aft if ant > 0 else None
                    if member == "BRACE":
                        labels = (
                            (
                                "D94",
                                "D95",
                                "D96",
                                "D97",
                                "D98",
                                "D99",
                                "D100",
                                "D101",
                                "D102",
                                "D103",
                                "D104",
                                "D105",
                            )
                            if branch == "V"
                            else (
                                "D108",
                                "D109",
                                "D110",
                                "D111",
                                "D112",
                                "D113",
                                "D114",
                                "D115",
                                "D116",
                                "D117",
                                "D118",
                                "D119",
                            )
                        )
                    else:
                        labels = (
                            (
                                "D212",
                                "D213",
                                "D214",
                                "D215",
                                "D216",
                                "D217",
                                "D218",
                                "D219",
                                "D220",
                                "D221",
                                "D222",
                                "D223",
                            )
                            if branch == "V"
                            else (
                                "D226",
                                "D227",
                                "D228",
                                "D229",
                                "D230",
                                "D231",
                                "D232",
                                "D233",
                                "D234",
                                "D235",
                                "D236",
                                "D237",
                            )
                        )
                    # D220 is before D221's separately retained extra Ts.
                    cell_ft = ft * ts if member == "COLUMN" and branch == "V" else aft
                    values = (
                        lv,
                        Decimal(2),
                        lt,
                        t,
                        ans,
                        afs * 1000,
                        shear_cap,
                        ant,
                        cell_ft * 1000,
                        tension_cap,
                        capacity,
                        ratio,
                    )
                    trace = tuple(zip(labels, values, strict=True))
                    rows.append(
                        BranchCorrection(
                            member,
                            branch,
                            name,
                            ltv,
                            av,
                            at,
                            ds,
                            dt,
                            ans,
                            ant,
                            fs * 4,
                            ft * 4,
                            afs,
                            aft,
                            nominal,
                            capacity,
                            demand,
                            ratio,
                            cells,
                            trace,
                            valid,
                            ""
                            if valid
                            else "Nonpositive residual reference material area; "
                            "affected check NOT EVALUATED.",
                        )
                    )
                utilization = (
                    sum((r.ratio for r in rows if r.ratio is not None), Decimal(0))
                    if all(r.available for r in rows)
                    else None
                )
                outcome = (
                    "NOT_EVALUATED"
                    if utilization is None
                    else "PASS"
                    if utilization <= 1
                    else "FAIL"
                )
                variants.append(GlobalCorrection(member, name, tuple(rows), utilization, outcome))
        ledger = (
            *base.factor_ledger,
            "R2 owner correction Input!L64=L51*COS(N45); L65=L64; original SIN remains historical.",
            "Xb is owner-confirmed brace-edge to bolt-column centerline distance; "
            "saved arithmetic recipe is historical only.",
            "Local lengths remain true edge-to-bolt-centerline distances; "
            "no half-hole local deduction.",
            "R2 actual-hole cut ledger is separate from conditional source-area subtraction; "
            "effective fracture endpoints remain unreconciled.",
            ENDPOINT_QUESTION,
        )
        checks = list(base.comparisons)
        for index, member in ((3, "BRACE"), (6, "COLUMN")):
            result = next(x for x in variants if x.member == member and x.variant == "LTV_ONLY")
            capacities = tuple(
                q(r.allowable_capacity_kip, Unit.KIP)
                for r in result.branches
                if r.allowable_capacity_kip is not None
            )
            # Existing comparison order is V, then P; only these two globals depend on LTV.
            checks[index] = additive_comparison(
                checks[index].method_id,
                (q(v, Unit.KIP), q(p, Unit.KIP)),
                capacities,
                cells=checks[index].cells,
                operands=checks[index].operands,
                equation=checks[index].equation + "; R2 LtV=d_span*cos(phi)",
                assumptions=ledger,
            )
        paths = replace(
            base.paths,
            lengths=tuple(
                (k, q(new_ltv)) if k in ("L64", "L65") else (k, value)
                for k, value in base.paths.lengths
            ),
            interpretation="OWNER_COS_EFFECTIVE_LENGTH_CANDIDATE_PHYSICAL_ENDPOINTS_NOT_RECONCILED",
        )
        summary = tuple(
            (
                cell,
                checks[3].utilization
                if cell == "D121"
                else checks[6].utilization
                if cell == "D239"
                else value,
            )
            for cell, value in base.source_summary
        )
        corrected = replace(
            base,
            stream=DirectCandidateStream.CORRECTED_SOURCE_CANDIDATE,
            paths=paths,
            comparisons=tuple(checks),
            source_summary=summary,
            factor_ledger=ledger,
        )
        _top, bottom = base.paths.bolt_centers
        # d_span is the actual pair's projection along v, not a demonstrated
        # 2-in physical connector. Its projection endpoints are shown explicitly.
        projected = (bottom[0] + span * s, bottom[1] + span * c)
        return DirectCorrections(
            historical,
            corrected,
            blocks,
            tuple(variants),
            old_ltv,
            new_ltv,
            base.paths.vertical_spacing.magnitude,
            base.paths.vertical_spacing.magnitude * s,
            (bottom, projected),
        )
