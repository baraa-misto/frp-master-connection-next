"""P4 physical-domain data and source-gated receiving-flange shear-out."""

from dataclasses import asdict, dataclass, field
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, cast

from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    Alignment,
    PairedActions,
)
from frp_master_connection.application.hyb1_review import ComparisonRow
from frp_master_connection.application.hyb2_d2 import D2Assessment
from frp_master_connection.application.hybrid_physical_geometry import (
    RECEIVING_FRAME,
    EndCondition,
    ReceivingEnd,
    ReceivingEnds,
    r3_scene_geometry,
)
from frp_master_connection.application.hybrid_same_connection import (
    NEUTRAL,
    SameConnectionDemand,
    SameConnectionMaterials,
)
from frp_master_connection.application.mat1_materials import PropertyLedger
from frp_master_connection.calculation.equations import adjust_frp_property
from frp_master_connection.calculation.in_plane_wrench_demand import (
    ExactWrenchSolution,
    project_rational,
)
from frp_master_connection.calculation.inputs import select_time_effect_factor
from frp_master_connection.calculation.multirow import InterrowShearOutMethod
from frp_master_connection.calculation.multirow_equations import (
    constant_pitch_factor,
    interrow_shear_out_resistance,
)
from frp_master_connection.calculation.properties import FRPPropertyEntry, FRPPropertyKind
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    StandardHoleDefinition,
    Unit,
    create_standard_hole,
)
from frp_master_connection.calculation.resistance_handoff import (
    RESISTANCE_HANDOFF_DECIMAL_PRECISION,
)
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest

CONTRACT = "HYB2-D3-P4-PHYSICAL/1"
PHYSICAL_SCOPE = "ASCE_CURRENT_PHYSICAL_RECEIVING_COMPONENT"
HOLE_CONTAINMENT_LIMIT = "An actual hole crosses a member side or declared receiving end."
OUTSTAND_INPUT_LIMIT = "The declared clear outstand exceeds half the receiving flange width."
type SixActions = tuple[
    PhysicalQuantity | None,
    PhysicalQuantity | None,
    PhysicalQuantity | None,
    PhysicalQuantity | None,
    PhysicalQuantity | None,
    PhysicalQuantity | None,
]


@dataclass(frozen=True, slots=True)
class ReceivingAdditionalActions:
    case_id: str
    components: SixActions


@dataclass(frozen=True, slots=True)
class PhysicalInputs:
    ends: ReceivingEnds = field(default_factory=ReceivingEnds)
    hole_source: PublishedCodeUnitBasis | None = None
    clear_flat_outstand: PhysicalQuantity | None = None
    interface_gap: PhysicalQuantity | None = None
    receiving_actions: tuple[ReceivingAdditionalActions, ...] = ()

    def standard_hole(self, diameter: PhysicalQuantity) -> StandardHoleDefinition | None:
        if self.hole_source is None:
            return None
        with localcontext() as context:
            context.prec = 80
            return create_standard_hole(diameter, self.hole_source)


@dataclass(frozen=True, slots=True)
class PhysicalAssessment:
    rows: tuple[ComparisonRow, ...]
    cases: tuple[dict[str, Any], ...]
    geometry_failures: tuple[dict[str, Any], ...]


def _quantity_record(q: PhysicalQuantity) -> dict[str, str]:
    return {"value": str(q.magnitude), "unit": q.unit.value}


def evaluate_physical(
    actions: PairedActions,
    g: R3Geometry,
    materials: SameConnectionMaterials | None,
    demands: tuple[SameConnectionDemand, ...],
    data: PhysicalInputs | None,
    *,
    requested: bool,
) -> PhysicalAssessment:
    "Existing Eq.8-12 on a complete local flange release; no first-row/block adoption."
    rows: list[ComparisonRow] = []
    cases: list[dict[str, Any]] = []
    geometry_failures: list[dict[str, Any]] = []
    data = PhysicalInputs() if data is None else data
    model = r3_scene_geometry(g, data.ends)
    with localcontext() as context:
        context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
        values = {
            "diameter": g.diameter.to(Unit.IN).magnitude,
            "hole": g.hole.to(Unit.IN).magnitude,
            "pitch": g.vertical_bolt_pitch.to(Unit.IN).magnitude,
            "width": g.column_flange.to(Unit.IN).magnitude,
            "xc": g.xc.to(Unit.IN).magnitude,
            "thickness": g.column_thickness.to(Unit.IN).magnitude,
        }
        d, hole, pitch, width, xc, thickness = values.values()
        flat = (
            None
            if data.clear_flat_outstand is None
            else data.clear_flat_outstand.to(Unit.IN).magnitude
        )
        gap = None if data.interface_gap is None else data.interface_gap.to(Unit.IN).magnitude
        standard = data.standard_hole(g.diameter)
        selected_hole_fit = (
            model.hole_fit
            if actions.identity.alignment is Alignment.SUPPORT
            else model.rotation_fit
        )
        if not selected_hole_fit:
            geometry_failures.append(
                {
                    "case_id": None,
                    "reasons": [HOLE_CONTAINMENT_LIMIT],
                }
            )
        if flat is not None and flat > width / 2:
            geometry_failures.append(
                {
                    "case_id": None,
                    "reasons": [OUTSTAND_INPUT_LIMIT],
                }
            )
        ledger = (
            None
            if materials is None
            else next(
                (
                    item
                    for item in materials.receiving.ledgers
                    if item.property_id == "in_plane_shear_strength_LT"
                ),
                None,
            )
        )
        entry = (
            None
            if materials is None
            else materials.receiving.adjusted_snapshot.lookup(FRPPropertyKind.FSH_LT)
        )
        for case in actions.lrfd:
            issues: list[tuple[str, str]] = []

            def require(
                ok: bool,
                state: str,
                message: str,
                *,
                target: list[tuple[str, str]] = issues,
            ) -> None:
                if not ok:
                    target.append((state, message))

            require(
                requested, "REQUIRED_NOT_EVALUATED", "ASCE physical calculation was not requested."
            )
            require(
                actions.identity.alignment is Alignment.SUPPORT,
                "REQUIRED_NOT_EVALUATED",
                (
                    "Eq.8-12 requires this actual two-row line along receiving LW; brace "
                    "alignment is not borrowed."
                ),
            )
            require(
                g.frame_rotation_degrees == 0 and all(q.magnitude == 0 for q in g.midpoint),
                "REQUIRED_NOT_EVALUATED",
                "The new physical adapter requires the established source drawing datum.",
            )
            require(
                selected_hole_fit,
                "GEOMETRY_FAIL",
                HOLE_CONTAINMENT_LIMIT,
            )
            require(
                standard is not None,
                "SOURCE_OR_MATERIAL_PENDING",
                (
                    "Select the original published ASCE unit column; display units cannot "
                    "recreate a hole."
                ),
            )
            if standard is not None:
                require(
                    g.hole.canonical_magnitude == standard.hole_diameter.canonical_magnitude,
                    "GEOMETRY_FAIL",
                    (
                        "The actual hole must match the declared standard-hole source; no "
                        "resizing is performed."
                    ),
                )
                si = standard.published_source_basis is PublishedCodeUnitBasis.SI_PRINTED
                require(
                    (Decimal("9.53") <= g.diameter.to(Unit.MM).magnitude <= Decimal("25.4"))
                    if si
                    else (Decimal(".375") <= d <= 1),
                    "GEOMETRY_FAIL",
                    "Bolt diameter is outside ASCE Chapter 8 source bounds.",
                )
                t_min = (
                    PhysicalQuantity.of("4.8", Unit.MM)
                    if si
                    else PhysicalQuantity.of(".188", Unit.IN)
                )
                require(
                    min(
                        g.column_thickness.canonical_magnitude,
                        g.brace_thickness.canonical_magnitude,
                    )
                    >= t_min.canonical_magnitude,
                    "GEOMETRY_FAIL",
                    "Connected FRP thickness is below the source minimum.",
                )
            require(
                g.column_thickness <= g.brace_thickness,
                "REQUIRED_NOT_EVALUATED",
                (
                    "This receiving-release domain requires the receiving flange to be the "
                    "minimum connected thickness."
                ),
            )
            require(
                flat is not None,
                "REQUIRED_NOT_EVALUATED",
                (
                    "Enter the measured clear flat receiving outstand width, excluding the "
                    "web/root/fillet."
                ),
            )
            if flat is not None:
                require(
                    flat <= width / 2,
                    "GEOMETRY_FAIL",
                    OUTSTAND_INPUT_LIMIT,
                )
                require(
                    flat - xc - hole / 2 > 0,
                    "REQUIRED_NOT_EVALUATED",
                    (
                        "The actual hole/release strip does not lie wholly inside the declared "
                        "clear outstand."
                    ),
                )
            require(
                min(xc, width - xc) >= Decimal("1.5") * d,
                "GEOMETRY_FAIL",
                (
                    "A true receiving flange free-edge distance is below 1.5d; the root "
                    "datum is not a free edge."
                ),
            )
            require(
                pitch
                <= min(24 * min(thickness, g.brace_thickness.to(Unit.IN).magnitude), Decimal(12)),
                "GEOMETRY_FAIL",
                "Actual pitch exceeds the Chapter 8 maximum; no display extent is substituted.",
            )
            require(
                gap is not None,
                "REQUIRED_NOT_EVALUATED",
                "State the actual interface gap; a zero force component "
                "does not establish contact.",
            )
            if gap is not None:
                require(
                    gap == 0,
                    "REQUIRED_NOT_EVALUATED",
                    "A gapped/standoff joint needs a supported coupled load-transfer model.",
                )
            additional = next(
                (item for item in data.receiving_actions if item.case_id == case.case_id), None
            )
            require(
                additional is not None and all(q is not None for q in additional.components),
                "REQUIRED_NOT_EVALUATED",
                (
                    "Enter all six additional receiving-member actions for this LRFD case; "
                    "unknown is not zero."
                ),
            )
            if additional is not None and all(q is not None for q in additional.components):
                require(
                    all(q is not None and q.magnitude == 0 for q in additional.components),
                    "REQUIRED_NOT_EVALUATED",
                    "Nonzero receiving bypass N/V/M needs an endorsed coupled stress-transfer law.",
                )
            require(
                ledger is not None and ledger.adjusted_candidate is not None and entry is not None,
                "SOURCE_OR_MATERIAL_PENDING",
                "The selected receiving FRP adjusted in-plane shear strength is unavailable.",
            )
            current = next((item for item in demands if item.case.case_id == case.case_id), None)
            require(
                current is not None,
                "REQUIRED_NOT_EVALUATED",
                "A fresh complete supported in-plane wrench on this "
                "exact physical pair is required.",
            )
            equation_e1 = None
            nearest = None
            end = None
            solution = (
                None if current is None else current.wrench.solution.in_units(Unit.IN, Unit.KIP)
            )
            if solution is not None:
                expected_coordinates = tuple(
                    (name, (Fraction(point[0]), Fraction(point[1])))
                    for name, point in model.bolt_centers
                )
                require(
                    current is not None
                    and current.geometry_identity == geometry_digest(g)
                    and current.case.digest == case.digest
                    and solution.coordinates == expected_coordinates,
                    "REQUIRED_NOT_EVALUATED",
                    "A wrench from a different layout or action cannot supply this physical check.",
                )
                require(
                    solution.force[0] == 0 and solution.force[1] != 0,
                    "REQUIRED_NOT_EVALUATED",
                    (
                        "Eq.8-12 needs a nonzero force exactly along receiving LW; entered "
                        "transverse force is retained."
                    ),
                )
                require(
                    solution.centroid_moment == 0,
                    "REQUIRED_NOT_EVALUATED",
                    (
                        "A transported free moment produces eccentric bolt demands outside "
                        "this longitudinal release domain."
                    ),
                )
                require(
                    solution.proof is not None and solution.proof.passed,
                    "REQUIRED_NOT_EVALUATED",
                    "The current exact-rational wrench equilibrium proof is required.",
                )
                if solution.force[1] != 0:
                    positive = solution.force[1] > 0
                    end = data.ends.positive if positive else data.ends.negative
                    opposite = data.ends.negative if positive else data.ends.positive
                    require(
                        end.condition is EndCondition.FREE and end.distance is not None,
                        "REQUIRED_NOT_EVALUATED",
                        (
                            "The unloaded direction needs an actual free end; a view crop or "
                            "continuous member is not an end."
                        ),
                    )
                    require(
                        opposite.condition is EndCondition.CONTINUOUS,
                        "REQUIRED_NOT_EVALUATED",
                        (
                            "The opposite receiving direction must continue into the member for "
                            "this bounded transfer model."
                        ),
                    )
                    if end.distance is not None:
                        nearest = (
                            max(model.bolt_centers, key=lambda item: item[1][1])
                            if positive
                            else min(model.bolt_centers, key=lambda item: item[1][1])
                        )
                        equation_e1 = end.distance.to(Unit.IN).magnitude - abs(nearest[1][1])
                        require(
                            equation_e1 >= 2 * d,
                            "GEOMETRY_FAIL",
                            "Actual unloaded-end distance to its nearest row "
                            "is below the two-row 2d minimum.",
                        )
            net_screen = None
            if standard is not None:
                # Existing Section 2.10 increment affects net area only, never Eq.8-12 d_n.
                area_hole = (g.hole + standard.published_increment).to(Unit.IN).magnitude
                gross_area = width * thickness
                net_area = (width - area_hole) * thickness
                ratio = net_area / gross_area
                net_screen = {
                    "gross_connected_flange_in2": gross_area,
                    "net_connected_flange_in2": net_area,
                    "net_deduction_diameter_in": area_hole,
                    "raw_ratio": ratio,
                    "minimum_ratio": Decimal(".75"),
                    "outcome": "PASS" if ratio >= Decimal(".75") else "FAIL",
                    "bound": (
                        "The one-hole connected-flange ratio is a lower bound on the full I "
                        "ratio; other unperforated section area is nonnegative."
                    ),
                }
                require(
                    ratio >= Decimal(".75"),
                    "GEOMETRY_FAIL",
                    "Raw net connected-flange area is below 75%; "
                    "no area is clamped or substituted.",
                )
            state = (
                "GEOMETRY_FAIL"
                if any(s == "GEOMETRY_FAIL" for s, _ in issues)
                else (
                    "SOURCE_OR_MATERIAL_PENDING"
                    if any(s == "SOURCE_OR_MATERIAL_PENDING" for s, _ in issues)
                    else "REQUIRED_NOT_EVALUATED"
                    if issues
                    else "EXECUTED"
                )
            )
            audit: dict[str, Any] = {
                "case_id": case.case_id,
                "case_digest": case.digest,
                "disposition": state,
                "reasons": [message for _, message in issues],
                "source": "ASCE/SEI 74-23 Section 8.3.3.2 Eq.8-12, printed page 36",
                "component": "member-b/TOP_FLANGE",
                "bolt_line": "L1",
                "raw_actions": asdict(case),
                "additional_receiving_actions": None if additional is None else asdict(additional),
                "net_area_screen": net_screen,
                "actual_geometry_in": values,
                "clear_flat_outstand_in": flat,
                "interface_gap_in": gap,
                "actual_unloaded_e1_in": equation_e1,
                "nearest_unloaded_row": None if nearest is None else nearest[0],
                "physical_bolt_centers_in": model.bolt_centers,
                "qualification": "NOT_ESTABLISHED_SECTION_2_3_2",
                "separate_required": (
                    "First-row/bearing-bypass, global block releases, junction, "
                    "bolt-axis/prying and whole connection remain unverified."
                ),
            }
            if state == "GEOMETRY_FAIL":
                existing_reasons = {
                    reason for failure in geometry_failures for reason in failure["reasons"]
                }
                new_reasons = [
                    message
                    for category, message in issues
                    if category == "GEOMETRY_FAIL" and message not in existing_reasons
                ]
                if new_reasons:
                    geometry_failures.append({"case_id": case.case_id, "reasons": new_reasons})
            if not issues:
                # Every operand is established by the applicability requirements above.
                equation_e1 = cast(Decimal, equation_e1)
                entry = cast(FRPPropertyEntry, entry)
                current = cast(SameConnectionDemand, current)
                ledger = cast(PropertyLedger, ledger)
                solution = cast(ExactWrenchSolution, solution)
                materials = cast(SameConnectionMaterials, materials)
                flat = cast(Decimal, flat)
                end_distance = cast(PhysicalQuantity, cast(ReceivingEnd, end).distance)
                si_solution = current.wrench.solution.in_units(Unit.MM, Unit.N)
                shear = adjust_frp_property(
                    FRPPropertyKind.FSH_LT, entry.value, entry.qualification_status, NEUTRAL
                )
                delta = constant_pitch_factor((g.vertical_bolt_pitch,), g.diameter)
                trace = interrow_shear_out_resistance(
                    InterrowShearOutMethod.ASCE_EQ_8_12,
                    PhysicalQuantity.of(equation_e1, Unit.IN),
                    g.hole,
                    (g.vertical_bolt_pitch,),
                    g.column_thickness,
                    shear,
                    lap_factor_c_lap=Decimal(".6"),
                    pitch_factor_c_delta=delta.pitch_factor_c_delta,
                    time_effect_factor_lambda=select_time_effect_factor(
                        materials.time_category
                    ).value,
                )
                capacity = trace.factor_trace.design_resistance.to(Unit.KIP).magnitude
                force = abs(project_rational(solution.force[1]))
                utilization = force / capacity
                audit.update(
                    equation_trace=asdict(trace),
                    MAT1_ledger=asdict(ledger),
                    line_demand_kip=force,
                    design_resistance_kip=capacity,
                    nominal_resistance_kip=trace.factor_trace.equation_nominal_resistance.to(
                        Unit.KIP
                    ).magnitude,
                    utilization=utilization,
                    outcome="PASS" if utilization <= 1 else "FAIL",
                    exact_wrench=current.wrench.canonical_json(),
                    physical_release={
                        "source_plane": "source x/y -> viewer X/Z; thickness is viewer +Y",
                        "hole_radius_in": hole / 2,
                        "source_shear_face_start_y_in": min(
                            point[1] for _, point in model.bolt_centers
                        )
                        if solution.force[1] > 0
                        else max(point[1] for _, point in model.bolt_centers),
                        "source_x_shear_boundaries_in": [-hole / 2, hole / 2],
                        "actual_free_end_y_in": end_distance.to(Unit.IN).magnitude
                        * (1 if solution.force[1] > 0 else -1),
                        "bottom_closure": "Actual trailing hole void; "
                        "no fracture through the integral web",
                        "receiving_thickness_in": thickness,
                        "root_exclusion_x_in": xc - flat,
                        "root_clearance_in": flat - xc - hole / 2,
                        "scope": (
                            "Local receiving-flange strip only; no outstand-block or "
                            "web-attached-block coverage."
                        ),
                    },
                    derived_complementary_receiving_action={
                        "frame": RECEIVING_FRAME,
                        "reference": [{"value": "0", "unit": "in"}] * 3,
                        "components": [
                            _quantity_record(
                                PhysicalQuantity.of(
                                    project_rational(value), Unit.N if i < 3 else Unit.N_MM
                                )
                            )
                            for i, value in enumerate(
                                (
                                    -si_solution.force[1],
                                    -si_solution.force[0],
                                    Fraction(0),
                                    Fraction(0),
                                    Fraction(0),
                                    si_solution.centroid_moment,
                                )
                            )
                        ],
                    },
                    derived_action_scope=(
                        "Entered in-plane connection contribution at the same datum; "
                        "additional actions are separately supplied. Single-lap secondary "
                        "actions/prying remain unverified."
                    ),
                )
                rows.append(
                    ComparisonRow(
                        "RECEIVING_INTERROW_SHEAR_OUT",
                        case.case_id,
                        case.digest,
                        ActionBasis.LRFD,
                        utilization,
                        audit["outcome"],
                        "ASCE/SEI 74-23 Eq.8-12; current physical receiving flange",
                        str(audit),
                        "CURRENT_PHYSICAL_INPUTS_EXACT_WRENCH",
                        PHYSICAL_SCOPE,
                    )
                )
            cases.append(audit)
    return PhysicalAssessment(tuple(rows), tuple(cases), tuple(geometry_failures))


def physical_status_axes(
    assessment: D2Assessment, result: PhysicalAssessment, detailing: list[dict[str, Any]]
) -> dict[str, str]:
    """Display independent backend decisions; no numerical failure is fabricated."""
    detail_fail = (
        bool(result.geometry_failures)
        or any(item.get("pass_fail") == "FAIL" for item in detailing)
        or (assessment.fit.actual_overhang_in is not None and assessment.fit.actual_overhang_in > 0)
    )
    numerical_fail = assessment.evaluated_outcome == "FAIL"
    return {
        "scoped_numerical": "SCOPED_NUMERICAL_" + assessment.evaluated_outcome,
        "detailing": "DETAILING_FAIL" if detail_fail else "DETAILING_UNKNOWN",
        "required_coverage": "REQUIRED_COVERAGE_PARTIAL",
        "material_method": "SCOPED_COMPONENTS_WITH_UNRESOLVED_COUPLED_METHODS",
        "qualification": "NOT_ESTABLISHED_SECTION_2_3_2",
        "whole_connection": (
            "FAIL_EVALUATED_CHECKS_AND_DETAILING"
            if numerical_fail and detail_fail
            else "FAIL_EVALUATED_CHECKS"
            if numerical_fail
            else "FAIL_DETAILING"
            if detail_fail
            else "NOT_VERIFIED"
        ),
        "viewer_tone": "red" if numerical_fail or detail_fail else "gray",
    }


def mechanism_matrix(
    comparisons: tuple[ComparisonRow, ...], result: PhysicalAssessment
) -> tuple[dict[str, Any], ...]:
    "Required mechanisms remain explicit even when a reference arithmetic row passed."
    definitions = (
        (
            "Shared bolts - in-plane shear",
            ("BOLT_SHEAR:",),
            "ASCE Eq.8-2; current exact wrench",
            "Bolt-axis tension, bending and prying are separate required mechanisms.",
        ),
        (
            "Angle connected leg - hole bearing",
            ("PIN_BEARING:layer-A:",),
            "ASCE Eqs.8-5/8-6; actual member axes and bolt forces",
            "First-row bearing/bypass stress transfer remains separate.",
        ),
        (
            "Receiving I flange - hole bearing",
            ("PIN_BEARING:layer-B:",),
            "ASCE Eqs.8-5/8-6; current receiving flange",
            "First-row and coupled receiving stress transfer remain separate.",
        ),
        (
            "Angle first-row net tension",
            (),
            "ASCE 8.3.3.1 applicability not established",
            (
                "Establish actual effective cut/width, orthotropic bearing/bypass "
                "field and source limits; the native BRACE F6 layout is different."
            ),
        ),
        (
            "Receiving I first-row net tension",
            (),
            "ASCE 8.3.3.1 applicability not established",
            (
                "Validate the receiving flange/web load-transfer field and effective "
                "width with actual section actions. A net-area screen is not "
                "net-tension capacity."
            ),
        ),
        (
            "Angle inter-row shear-out",
            (),
            "Longitudinal source method cannot be borrowed for oblique R3 force",
            "A physical release and applicable Angle force/axis method are required.",
        ),
        (
            "Angle block release",
            (),
            "Native F7 longitudinal path is not the oblique R3 release",
            (
                "Validate the complete detachable 3D fragment and mixed-mode "
                "bearing/bypass stress; RHM scalar arithmetic is reference evidence."
            ),
        ),
        (
            "Receiving I occupied-outstand block release",
            (),
            "ASCE 8-14 requires a substantiated physical control volume",
            (
                "Supply the complete release, true boundaries and full receiving "
                "N/V/M; local shear-out is not global block coverage."
            ),
        ),
        (
            "Receiving I web-attached block release",
            (),
            "The integral web is not a free edge",
            (
                "A separate web-attached 3D release and applicable combined-stress "
                "model are required."
            ),
        ),
        (
            "Angle heel and receiving flange/web junction",
            (),
            "Integral material and unknown roots are retained",
            "Actual root/fillet geometry and an endorsed transfer/stiffness model are needed.",
        ),
        (
            "Bolt-axis force, pull-through and prying",
            (),
            "Single-lap secondary actions remain unverified",
            (
                "Contact/gap data and zero entered normal actions do not establish "
                "actual prying. Provide a validated contact/bolt-axis model."
            ),
        ),
        (
            "Cleavage and longitudinal splitting",
            (),
            "No unverified multi-row exemption is applied",
            (
                "Establish actual action/axis, complete fracture geometry and "
                "applicable source method."
            ),
        ),
    )
    rows: list[dict[str, Any]] = []
    for name, prefixes, source, missing in definitions:
        executed = tuple(
            {
                "case_id": row.case_id,
                "check_id": row.mechanism,
                "basis": row.basis.value,
                "outcome": row.outcome,
                "scope": row.evidence_scope,
            }
            for row in comparisons
            if row.basis is ActionBasis.LRFD
            and row.ratio is not None
            and row.mechanism.startswith(prefixes)
        )
        rows.append(
            {
                "mechanism": name,
                "disposition": "EXECUTED" if executed else "REQUIRED_NOT_EVALUATED",
                "executed_comparisons": executed,
                "source": source,
                "remaining_evidence": missing,
            }
        )
    executed = tuple(
        {
            "case_id": row.case_id,
            "check_id": row.mechanism,
            "basis": row.basis.value,
            "outcome": row.outcome,
            "scope": row.evidence_scope,
        }
        for row in result.rows
    )
    all_executed = bool(result.cases) and all(
        item["disposition"] == "EXECUTED" for item in result.cases
    )
    rows.insert(
        6,
        {
            "mechanism": "Receiving I flange - longitudinal inter-row shear-out",
            "disposition": "EXECUTED"
            if all_executed
            else ("GEOMETRY_FAIL" if result.geometry_failures else "REQUIRED_NOT_EVALUATED"),
            "executed_comparisons": executed,
            "source": "ASCE/SEI 74-23 Eq.8-12; actual unloaded end and full single-line wrench",
            "remaining_evidence": (
                "Every entered LRFD case must satisfy the stated physical/source "
                "domain. First-row and both global block releases remain independent."
            ),
            "case_applicability": result.cases,
        },
    )
    return tuple(rows)
