"""P3: existing ASCE primitives on the actual R3 pair, never a native-layout copy.

This is a scoped in-plane component assessment. It does not resolve FRP stress
transfer, single-lap prying, physical release laws or Section 2.3.2 qualification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, localcontext
from hashlib import sha256
from typing import Any, cast

from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    ActionCase,
    Alignment,
    PairedActions,
)
from frp_master_connection.application.hyb1_review import ComparisonRow
from frp_master_connection.application.hyb2_d2 import D2Assessment
from frp_master_connection.application.hybrid_physical_geometry import (
    RECEIVING_FRAME,
    R3SceneGeometry,
    r3_scene_geometry,
)
from frp_master_connection.application.mat1_native import NativeMaterialAdapter
from frp_master_connection.calculation.equations import (
    adjust_frp_property,
    bolt_shear_resistance,
    pin_bearing_resistance,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    InPlaneWrenchResult,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.inputs import (
    EndUseFactors,
    TimeEffectCategory,
    select_time_effect_factor,
)
from frp_master_connection.calculation.multirow_equations import constant_pitch_factor
from frp_master_connection.calculation.properties import (
    FastenerSnapshot,
    FRPPropertyKind,
    ThreadStatus,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.resistance_handoff import (
    RESISTANCE_HANDOFF_DECIMAL_PRECISION,
    _acute_angle_degrees,
    _material_direction,
)
from frp_master_connection.calculation.rhm_direct_r3 import (
    R3Geometry,
    geometry_digest,
    intersect_edge,
)

CONTRACT = "HYB2-D3-P3-SAME-CONNECTION-ASCE/1"
SCOPE = "ASCE_SAME_CONNECTION_COMPONENT_CALCULATION"
NEUTRAL = EndUseFactors(Decimal(1), Decimal(1), Decimal(1), "MAT1 adjusted once", (CONTRACT,))
ASSUMPTIONS = (
    "Existing Slice 8 equal in-plane translational bolt stiffness; both holes engaged. "
    "Equilibrium is not validation of clearance/contact, prying or FRP bypass stress.",
    "ASCE Figure 8-1 row pitch is measured along the connection resultant, with transverse "
    "stagger retained. No Angle/inter-row/block path or first-row width is inferred.",
    "Bearing uses existing Eq. 8-6 per-bolt directions, phi=0.6, single-lap 0.6, and "
    "included/unknown bearing-thread factor 0.6. MAT1 strength adjustments apply once. "
    "Bolt shear uses phi=0.75 and lambda=1; bearing lambda follows the declared classification.",
    "RHM listed/SF4 reference properties and independent ASD cases remain separate from "
    "the selected ASCE characteristic/specification properties and LRFD cases.",
)


@dataclass(frozen=True, slots=True)
class SameConnectionMaterials:
    angle: NativeMaterialAdapter
    receiving: NativeMaterialAdapter
    time_category: TimeEffectCategory
    fastener: FastenerSnapshot | None
    provenance: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SameConnectionResult:
    rows: tuple[ComparisonRow, ...]
    withheld: tuple[tuple[str, str], ...]
    trace: dict[str, Any]
    detailing: tuple[dict[str, Any], ...]
    demands: tuple[SameConnectionDemand, ...] = ()


@dataclass(frozen=True, slots=True)
class SameConnectionDemand:
    case: ActionCase
    source_force: tuple[Decimal, Decimal]
    source_reference: tuple[Decimal, Decimal]
    source_moment: Decimal
    wrench: InPlaneWrenchResult
    geometry_identity: str


def canonicalize_same_connection_reference(case: ActionCase, declared_frame: str) -> ActionCase:
    """The new LRFD seam also maps the reference when legacy code aliases +n to -n.

    The original DTO remains in signed inputs. Legacy requests outside this seam
    retain their existing behavior; nonzero-moment +n inputs remain unsupported.
    """
    if (
        declared_frame == "DIRECT_P_POSITIVE_N_CENTROID"
        and case.frame == "DIRECT_P_SKETCH_V_CENTROID"
    ):
        second = case.reference[1]
        return replace(
            case,
            reference=(
                case.reference[0],
                PhysicalQuantity.of(-second.magnitude, second.unit),
                case.reference[2],
            ),
        )
    return case


def _comparison(
    case: ActionCase,
    name: str,
    magnitude: PhysicalQuantity,
    key: str,
    equation: str,
    trace: object,
    capacity: PhysicalQuantity,
    extra: dict[str, Any],
) -> tuple[ComparisonRow, dict[str, Any]]:
    ratio = magnitude.to(Unit.KIP).magnitude / capacity.to(Unit.KIP).magnitude
    audit = {
        "mechanism": key,
        "bolt_id": name,
        "demand_kip": magnitude.magnitude,
        "resistance_kip": capacity.to(Unit.KIP).magnitude,
        "equation_trace": asdict(cast(Any, trace)),
        **extra,
    }
    return ComparisonRow(
        key,
        case.case_id,
        case.digest,
        ActionBasis.LRFD,
        ratio,
        "PASS" if ratio <= 1 else "FAIL",
        equation,
        str(audit),
        "SAME_R3_PHYSICAL_PAIR_SCOPED_COMPONENT",
        SCOPE,
    ), audit


def calculate_same_connection(
    actions: PairedActions,
    g: R3Geometry,
    materials: SameConnectionMaterials,
    *,
    geometry_model: R3SceneGeometry | None = None,
    allow_receiving_frame: bool = False,
    nominal_hole: PhysicalQuantity | None = None,
    minimum_thickness: PhysicalQuantity | None = None,
    minimum_diameter: PhysicalQuantity | None = None,
    bearing_source_known: bool = True,
    contact_supported: bool = True,
) -> SameConnectionResult:
    """Fresh full-vector demand, exact R3 centers/thicknesses, unchanged resistance code."""
    if actions.identity.geometry != geometry_digest(g):
        raise ValueError("Same-connection ASCE geometry identity mismatch.")
    model = r3_scene_geometry(g) if geometry_model is None else geometry_model
    if model.geometry != g:
        raise ValueError("A different physical geometry cannot supply this demand.")
    rows: list[ComparisonRow] = []
    withheld: list[tuple[str, str]] = []
    cases: list[dict[str, Any]] = []
    detailing: list[dict[str, Any]] = []
    demands: list[SameConnectionDemand] = []
    if not actions.lrfd:
        withheld.append(("LRFD", "Enter independent LRFD combinations; no ASD conversion."))
    for case in actions.lrfd:
        if (
            actions.identity.alignment is not Alignment.SUPPORT
            or not model.hole_fit
            or not (
                (
                    PhysicalQuantity.of(".375", Unit.IN)
                    if minimum_diameter is None
                    else minimum_diameter
                ).canonical_magnitude
                <= g.diameter.canonical_magnitude
                <= PhysicalQuantity.of("1", Unit.IN).canonical_magnitude
            )
        ):
            withheld.append(
                (
                    case.case_id,
                    "R3 SUPPORT pair with contained, separate holes required; "
                    "ASCE bolt diameter must be 3/8 through 1 in; "
                    "no native BRACE result or N/A is transferred.",
                )
            )
            continue
        if (
            not case.complete
            or not (
                case.frame == "DIRECT_P_SKETCH_V_CENTROID"
                or (allow_receiving_frame and case.frame == RECEIVING_FRAME)
            )
            or any(q is not None and q.magnitude != 0 for q in case.components[2:5])
            or case.reference[2].magnitude != 0
        ):
            withheld.append(
                (
                    case.case_id,
                    (
                        "Complete supported-frame six-action input required; "
                        "out-of-plane force/moments/reference need a separate 3D model."
                        if allow_receiving_frame
                        else "Complete P/sketch V six-action input required; "
                        "out-of-plane force/moments/reference need a separate 3D model."
                    ),
                )
            )
            continue
        with localcontext() as ctx:
            ctx.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
            p, v, mz = (
                cast(PhysicalQuantity, case.components[i]).to(u).magnitude
                for i, u in ((0, Unit.KIP), (1, Unit.KIP), (5, Unit.KIP_IN))
            )
            pa, n = model.p_axis, model.n_axis
            force = (
                (v, p)
                if case.frame == RECEIVING_FRAME
                else (p * pa[0] - v * n[0], p * pa[1] - v * n[1])
            )
            ref = tuple(q.to(Unit.IN).magnitude for q in case.reference)
            reference = (
                (ref[1], ref[0])
                if case.frame == RECEIVING_FRAME
                else (ref[0] * pa[0] - ref[1] * n[0], ref[0] * pa[1] - ref[1] * n[1])
            )
            demand = calculate_in_plane_wrench_demand(
                InPlaneWrenchRequest(
                    tuple(WrenchBolt(name, x, y) for name, (x, y) in model.bolt_centers),
                    reference,
                    *force,
                    -mz,
                    Unit.IN,
                    Unit.KIP,
                    Unit.KIP_IN,
                )
            )
            demands.append(
                SameConnectionDemand(
                    case,
                    force,
                    reference,
                    -mz,
                    demand,
                    actions.identity.geometry,
                )
            )
            force_mag = (force[0] ** 2 + force[1] ** 2).sqrt()
            if force_mag != 0:
                for name, point in model.bolt_centers:
                    path = intersect_edge(
                        "BRACE",
                        "ASCE_END_DISTANCE_LOWER_BOUND",
                        name,
                        point,
                        (-force[0] / force_mag, -force[1] / force_mag),
                        model.edges[0],
                    )
                    minimum = 2 * g.diameter.to(Unit.IN).magnitude
                    failed = path.length_in is not None and path.length_in < minimum
                    detailing.append(
                        {
                            "check_kind": "BRACE_END_DISTANCE_MINIMUM_LOWER_BOUND",
                            "case_id": case.case_id,
                            "bolt_id": name,
                            "actual_distance": path.length_in,
                            "required_distance": minimum,
                            "unit": "in",
                            "pass_fail": "FAIL" if failed else "NOT_EVALUATED",
                            "boundary_label": "Actual R3 oblique end; ray opposite LRFD resultant",
                            "source_rule": "ASCE Table 8-1: least end-distance requirement is 2d; "
                            "meeting this lower bound does not prove full detailing.",
                            "path": asdict(path),
                        }
                    )
            delta = tuple(
                model.bolt_centers[1][1][i] - model.bolt_centers[0][1][i] for i in range(2)
            )
            pitch = (
                None
                if force_mag == 0
                else abs(delta[0] * force[0] + delta[1] * force[1]) / force_mag
            )
            c_delta = (
                Decimal(1)
                if pitch is None or pitch == 0
                else constant_pitch_factor(
                    (PhysicalQuantity.of(pitch, Unit.IN),), g.diameter
                ).pitch_factor_c_delta
            )
            shear_plane = (
                None
                if materials.fastener is None
                else next(iter(materials.fastener.shear_plane_thread_statuses), None)
            )
            bolt_trace = (
                None
                if materials.fastener is None
                or materials.fastener.fnt is None
                or shear_plane is None
                else bolt_shear_resistance(
                    g.diameter.to(Unit.IN), materials.fastener.fnt, shear_plane.status
                )
            )
            case_trace: dict[str, Any] = {
                "case_id": case.case_id,
                "case_digest": case.digest,
                "geometry_digest": actions.identity.geometry,
                "raw_actions": asdict(case),
                "source_global_force_kip": force,
                "source_global_reference_in": reference,
                "source_global_moment_kip_in": -mz,
                "demand": demand.canonical_json(),
                "row_pitch_in": pitch,
                "c_delta": c_delta,
                "checks": [],
            }
            for bolt in demand.solution.in_units(Unit.IN, Unit.KIP).projected_bolts():
                name = bolt.bolt_id
                magnitude = bolt.total_force_magnitude

                if bolt_trace is None:
                    withheld.append(
                        (
                            "BOLT_SHEAR:" + name,
                            "Select sourced Fnt and an explicit shear-plane thread state; "
                            "the RHM ASD allowance is not an LRFD nominal stress.",
                        )
                    )
                else:
                    row, audit = _comparison(
                        case,
                        name,
                        magnitude,
                        "BOLT_SHEAR:" + name,
                        "ASCE/SEI 74-23 Eq. 8-2; phi=.75, lambda=1",
                        bolt_trace,
                        bolt_trace.design_resistance,
                        {},
                    )
                    rows.append(row)
                    case_trace["checks"].append(audit)
                for owner, adapter, thickness, axis in (
                    ("layer-A", materials.angle, g.brace_thickness, pa),
                    ("layer-B", materials.receiving, g.column_thickness, (Decimal(0), Decimal(1))),
                ):
                    thickness = thickness.to(Unit.IN)
                    key = "PIN_BEARING:" + owner + ":" + name
                    threshold = (
                        PhysicalQuantity.of(".188", Unit.IN)
                        if minimum_thickness is None
                        else minimum_thickness
                    )
                    hole_matches = (
                        g.hole.to(Unit.IN).magnitude
                        == g.diameter.to(Unit.IN).magnitude + Decimal(".063")
                        if nominal_hole is None
                        else g.hole.canonical_magnitude == nominal_hole.canonical_magnitude
                    )
                    if (
                        thickness.canonical_magnitude < threshold.canonical_magnitude
                        or not hole_matches
                        or not contact_supported
                        or not bearing_source_known
                    ):
                        withheld.append(
                            (
                                key,
                                (
                                    "ASCE bearing scope requires the selected source thickness "
                                    "minimum, its actual nominal hole and supported interface "
                                    "contact; missing source or a standoff is not assumed valid. "
                                    "Independent bolt calculations remain available."
                                    if allow_receiving_frame
                                    else "ASCE bearing scope requires FRP thickness at least "
                                    ".188 in and the declared nominal hole d + .063 in; "
                                    "independent bolt calculations remain available."
                                ),
                            )
                        )
                        continue
                    if magnitude.magnitude == 0 or pitch is None:
                        withheld.append(
                            (
                                key,
                                "Bearing force direction/connection row pitch is "
                                "undefined for zero resultant; no arbitrary direction.",
                            )
                        )
                        continue
                    vector = (bolt.total_force.u.magnitude, bolt.total_force.v.magnitude)
                    direction = _material_direction(vector, axis)
                    kind = (
                        FRPPropertyKind.FBR_L
                        if direction.value == "LONGITUDINAL"
                        else FRPPropertyKind.FBR_T
                    )
                    prop_id = (
                        "bearing_strength_L"
                        if kind is FRPPropertyKind.FBR_L
                        else "bearing_strength_T"
                    )
                    ledger = next((x for x in adapter.ledgers if x.property_id == prop_id), None)
                    if ledger is None or ledger.adjusted_candidate is None:
                        withheld.append(
                            (
                                key,
                                "Selected MAT1 bearing property or applicable "
                                "moisture/temperature/chemical strength factor unavailable.",
                            )
                        )
                        continue
                    entry = cast(Any, adapter.adjusted_snapshot.lookup(kind))
                    prop = adjust_frp_property(
                        kind, entry.value, entry.qualification_status, NEUTRAL
                    )
                    bearing = pin_bearing_resistance(
                        thickness,
                        g.diameter.to(Unit.IN),
                        prop,
                        ThreadStatus.INCLUDED,
                        c_delta=c_delta,
                        c_lap=Decimal(".6"),
                        lambda_factor=select_time_effect_factor(materials.time_category).value,
                    )
                    row, audit = _comparison(
                        case,
                        name,
                        magnitude,
                        key,
                        "ASCE/SEI 74-23 Eqs. 8-5/8-6 and 8-1; single lap",
                        bearing,
                        bearing.factor_trace.design_resistance,
                        {
                            "angle_degrees": _acute_angle_degrees(vector, axis),
                            "material_axis": axis,
                            "selected_property": kind,
                            "MAT1_ledger": asdict(ledger),
                            "physical_thickness": asdict(thickness),
                        },
                    )
                    rows.append(row)
                    case_trace["checks"].append(audit)
            cases.append(case_trace)
    return SameConnectionResult(
        tuple(rows),
        tuple(withheld),
        {
            "contract": CONTRACT,
            "scope": SCOPE,
            "geometry_digest": geometry_digest(g),
            "paired_actions_digest": actions.digest,
            "material_context_digest": sha256(repr(materials).encode()).hexdigest(),
            "physical_centers_in": model.bolt_centers,
            "materials": materials.provenance,
            "assumptions": ASSUMPTIONS,
            "cases": cases,
            "authority": "COMPONENT_CALCULATION_ONLY_NO_CONNECTION_ADOPTION_OR_QUALIFICATION",
        },
        tuple(detailing),
        tuple(demands),
    )


def physical_mechanisms(rows: tuple[ComparisonRow, ...]) -> tuple[dict[str, Any], ...]:
    """Physical mechanisms, not a count of ASCE names or unreviewed coverage grants."""
    specifications = (
        (
            "Shared bolts, in-plane shear",
            ("BOLT_SHEAR:", "DIRECT_SHARED_BOLTS"),
            "Existing ASCE Eq. 8-2 on fresh Slice 8 forces; "
            "RHM saved uniform zero-moment ASD case.",
            "Single-lap bolt-axis tension/bending and prying are separate; source ASD allowance "
            "does not establish selected F593 strength.",
        ),
        (
            "Angle and receiving-flange hole bearing",
            ("PIN_BEARING:", "DIRECT_BRACE_BEARING", "DIRECT_COLUMN_BEARING"),
            "ASCE Eqs. 8-5/8-6 per bolt vector and member LW; separate RHM interactions.",
            "Characteristic/specification conformance, contact and full installation "
            "remain required.",
        ),
        (
            "Angle local end/side tear-out",
            ("DIRECT_BRACE_LOCAL",),
            "RHM Calcs D59:D87, actual unequal directed R3 paths to their shared real edges.",
            "Reference interaction only: directional properties and bearing/bypass applicability "
            "require method review. It does not prove an arbitrary inter-hole release.",
        ),
        (
            "Receiving-flange local tear-out",
            ("DIRECT_COLUMN_LOCAL",),
            "RHM Calcs D183:D205 directed receiving-member paths; actual shared bolt centers.",
            "The long V path reaches across the integral web; a flange-only sum does not "
            "validate the web/junction or establish an independent inter-row failure law.",
        ),
        (
            "Angle coupled block release",
            ("DIRECT_BRACE_GLOBAL",),
            "RHM Calcs D93:D121, R3 same-surface net shear and connector areas with actual holes.",
            "Oblique orthotropic mixed-mode and first-row bearing/bypass validation are missing. "
            "A tensile term is not independent net-tension coverage; one combined proof may "
            "cover both mechanisms if it actually establishes their common envelope.",
        ),
        (
            "Receiving-member coupled block release",
            ("DIRECT_COLUMN_GLOBAL",),
            "RHM Calcs D211:D239, actual net surfaces and independent receiving reactions.",
            "Define and validate detachable occupied-outstand and web-attached 3D fragments "
            "with true longitudinal ends and remote N/V/M; P/V paths are not LEFT/RIGHT blocks.",
        ),
        (
            "Angle and I first-row net failure",
            (),
            "No valid separate first-row calculation or substantiated joint-coverage "
            "proof supplied.",
            "Establish actual effective cut/width, local bearing/bypass stress field and "
            "orthotropic criterion, or validate the combined RHM envelope for this geometry.",
        ),
        (
            "Heel and flange/web junction transfer",
            (),
            "Integral material is retained, never replaced with a free edge.",
            "Actual roots/fillets and remote load transfer require a validated 3D model or "
            "a geometry-specific physical non-applicability proof.",
        ),
        (
            "Bolt-axis force, pull-through and prying",
            (),
            "In-plane component results make no absence claim for single-lap secondary actions.",
            "Provide contact/standoff, hardware stiffness and actual force references; "
            "zero entered out-of-plane actions are not proof that prying is absent.",
        ),
    )
    return tuple(
        {
            "mechanism": name,
            "executed_comparisons": tuple(
                {
                    "basis": r.basis.value,
                    "case_id": r.case_id,
                    "check_id": r.mechanism,
                    "scope": r.evidence_scope,
                    "outcome": r.outcome,
                }
                for r in rows
                if r.ratio is not None and r.mechanism.startswith(prefixes)
            ),
            "evidence": evidence,
            "remaining_evidence": remaining,
            "coverage_authority": "SCOPED_COMPONENT_OR_REFERENCE_ONLY_NO_ADOPTION_GRANTED",
        }
        for name, prefixes, evidence, remaining in specifications
    )


def integrate_same_connection(a: D2Assessment, result: SameConnectionResult) -> D2Assessment:
    rows = (*a.comparisons, *result.rows)
    numerical = [r for r in rows if r.ratio is not None]
    fail = any(r.outcome == "FAIL" for r in numerical) or a.evaluated_outcome == "FAIL"
    return replace(
        a,
        comparisons=rows,
        evaluated_outcome="FAIL" if fail else "PASS" if numerical else "NOT_EVALUATED",
        tone="red" if fail else "green" if numerical else "neutral",
        coverage_state="PARTIAL" if result.rows else a.coverage_state,
        governing_lrfd=max(
            (r for r in numerical if r.basis is ActionBasis.LRFD),
            key=lambda r: cast(Decimal, r.ratio),
            default=None,
        ),
        withheld=(*a.withheld, *result.withheld),
    )
