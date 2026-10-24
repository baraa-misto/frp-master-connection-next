"""F7 physical Angle block paths, outside the frozen Slice 2/3 engines.

The original layered handoffs remain immutable historical witnesses. This
adapter supplies a separate, authenticated physical path to those same engines.
It never derives group demand from individual bolt forces.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, localcontext

from frp_master_connection.calculation import (
    RESISTANCE_HANDOFF_DECIMAL_PRECISION,
    BlockShearCompatibilityEvidence,
    BlockShearCompatibilityStatus,
    BlockShearEccentricityContext,
    EccentricResistanceHandoffInput,
    EccentricResistanceHandoffResult,
    GeometryStatus,
    MaterialDirection,
    MultiRowCheckResult,
    MultiRowEquationMethod,
    MultiRowFingerprintMetadataEntry,
    MultiRowMethodApplicability,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    NumericalComparison,
    PhysicalQuantity,
    PlanAvailability,
    QualificationDisposition,
    StandardHoleDefinition,
    Unit,
    calculate_eccentric_resistance_handoff,
    classify_block_shear_eccentricity,
)
from frp_master_connection.calculation.block_shear_planning import (
    BlockShearAreaPlan,
    BoltHoleSource,
    NetAreaStatus,
    build_block_shear_area_plans,
)
from frp_master_connection.geometry.multirow import (
    BlockPathFamily,
    BlockPathSegment,
    BlockPathSegmentKind,
    BlockShearCandidatePath,
    BlockShearPathResolution,
    MultiRowGeometry,
    PlanarPoint2D,
    ProjectedPoint2D,
)

from .direct_engineering_geometry import DirectEngineeringBoundary, DirectEngineeringFace
from .visualization import SingleBoltVisualizationSnapshot, VisualizationPrimitive

CONTRACT = "SHEAR01-DIRECT-OR2-F7"
HEEL_REASON = (
    "The isolated flat-L two-cut path does not detach a physical block because the "
    "Angle heel / perpendicular leg remains continuous. Heel/junction/3D behavior "
    "remains within whole-connection qualification."
)


@dataclass(frozen=True, slots=True)
class DirectBlockHistoryResult:
    result_id: str
    layer_id: str
    limit_state: str
    availability: MultiRowResultAvailability
    numerical_comparison: NumericalComparison
    reason: str
    required: bool
    demand: None = None
    design_resistance: None = None
    utilization: None = None


@dataclass(frozen=True, slots=True)
class DirectAngleBlockPath:
    """Raw physical evidence; coordinates use the authenticated scene length unit."""

    check_id: str
    heel_check_id: str
    length_unit: Unit
    component_id: str
    physical_element_id: str
    boundary_ids: tuple[str, ...]
    raw_faces: tuple[DirectEngineeringFace, ...]
    polygon: tuple[tuple[Decimal, Decimal], ...]
    rejected_heel_polygon: tuple[tuple[Decimal, Decimal], ...]
    candidate: BlockShearCandidatePath
    area_plan: BlockShearAreaPlan
    continuity_geometry: tuple[VisualizationPrimitive, ...]
    heel_continuity_proven: bool
    continuity_reason: str


@dataclass(frozen=True, slots=True)
class DirectAngleBlockResult:
    contract_version: str
    scenario_id: str
    method_id: str
    path: DirectAngleBlockPath | None
    eccentricity: BlockShearEccentricityContext | None
    parent_demand_fingerprint: str
    handoff: EccentricResistanceHandoffResult | None
    supported_results: tuple[MultiRowCheckResult, ...]
    history_results: tuple[DirectBlockHistoryResult, ...]
    code_geometry_satisfied: bool
    reason: str
    result_fingerprint: str


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _boundary(face: DirectEngineeringFace, role: str) -> DirectEngineeringBoundary:
    matches = tuple(
        b
        for b in face.boundaries
        if b.role == role
        and not b.computational_only
        and b.source_geometry_id == face.source_geometry_id
    )
    if len(matches) != 1:
        raise ValueError("Physical block has no unique real " + role)
    return matches[0]


def _parameters(primitive: VisualizationPrimitive) -> dict[str, Decimal]:
    return {p.name: Decimal(str(p.value)) for p in primitive.parameters}


def _continuity(
    scene: SingleBoltVisualizationSnapshot, face: DirectEngineeringFace
) -> tuple[tuple[VisualizationPrimitive, ...], bool]:
    """Prove integral Angle topology, without inventing a resolved heel fillet."""

    other_leg = "LEG_2" if face.physical_element_id == "LEG_1" else "LEG_1"
    solids = tuple(
        p
        for p in scene.primitives
        if p.owner_id == face.component_id
        and (
            p.physical_element_id in {face.physical_element_id, other_leg}
            or p.label == "Angle heel"
        )
    )
    if len(solids) != 3:
        return solids, False
    selected = next(p for p in solids if p.physical_element_id == face.physical_element_id)
    perpendicular = next(p for p in solids if p.physical_element_id == other_leg)
    heel = next(p for p in solids if p.label == "Angle heel")
    a, b, h = map(_parameters, (selected, perpendicular, heel))
    transverse = "y" if face.transverse_axis == 1 else "z"
    normal = "y" if face.normal_axis == 1 else "z"
    # This is the existing Direct template/frame representation precision.
    tolerance = PhysicalQuantity.of("1e-9", Unit.IN).to(scene.length_unit).magnitude
    joints = (
        a["min_" + transverse] - h["max_" + transverse],
        a["min_" + normal] - h["min_" + normal],
        a["max_" + normal] - h["max_" + normal],
        b["min_" + normal] - a["max_" + normal],
        b["min_" + transverse] - h["min_" + transverse],
        b["max_" + transverse] - h["max_" + transverse],
    )
    x0, x1 = a["x_start"], a["x_end"]
    return solids, all(abs(v) <= tolerance for v in joints) and all(
        _parameters(p)["x_start"] <= x0 and _parameters(p)["x_end"] >= x1
        for p in (perpendicular, heel)
    )


def resolve_direct_angle_block_path(
    geometry: MultiRowGeometry,
    scene: SingleBoltVisualizationSnapshot,
    faces: tuple[DirectEngineeringFace, ...],
    hole: StandardHoleDefinition,
    layer_id: str,
    component_id: str,
    thickness: PhysicalQuantity,
) -> DirectAngleBlockPath:
    """Resolve a physical single-line, multi-row L strip on either selected Angle leg."""

    if len(geometry.rows) < 2 or len(geometry.bolt_lines) != 1:
        raise ValueError("F7 physical Angle block requires multiple rows on one physical line")
    selected = tuple(f for f in faces if f.component_id == component_id)
    if {f.bolt_id for f in selected} != {b.id for b in geometry.group.bolts}:
        raise ValueError("Physical block hole/bolt inventory is incomplete")
    face = selected[0]
    if face.physical_element_id not in {"LEG_1", "LEG_2"} or any(
        (f.physical_element_id, f.transverse_axis, f.normal_axis)
        != (face.physical_element_id, face.transverse_axis, face.normal_axis)
        for f in selected
    ):
        raise ValueError("Physical block must remain on one selected Angle leg")
    end = _boundary(face, "PHYSICAL_UNLOADED_END")
    free = _boundary(face, "PHYSICAL_FREE_SIDE_EDGE")
    junction = _boundary(face, "INTERNAL_SECTION_JUNCTION")
    x0 = Decimal(str(end.start_local[0]))
    side = Decimal(str(free.start_local[face.transverse_axis]))
    heel_side = Decimal(str(junction.start_local[face.transverse_axis]))
    points = {
        f.bolt_id: (
            Decimal(str(f.bolt_center_member_local[0])),
            Decimal(str(f.bolt_center_member_local[face.transverse_axis])),
        )
        for f in selected
    }
    corner_id = max(points, key=lambda b: abs(points[b][0] - x0))
    x1, line = points[corner_id]
    tolerance = PhysicalQuantity.of("1e-9", Unit.IN).to(scene.length_unit).magnitude
    if (
        x1 <= x0
        or not heel_side < line < side
        or any(x < x0 or x > x1 or abs(y - line) > tolerance for x, y in points.values())
    ):
        raise ValueError("Physical block does not close on a supported unloaded end/free side")
    primitive = next(p for p in scene.primitives if p.id == face.source_geometry_id)
    bounds = _parameters(primitive)
    normal = "y" if face.normal_axis == 1 else "z"
    actual_thickness = bounds["max_" + normal] - bounds["min_" + normal]
    if abs(actual_thickness - thickness.to(scene.length_unit).magnitude) > tolerance:
        raise ValueError("Physical block thickness differs from its material layer")
    line_id = geometry.bolt_lines[0].id
    path_id = f"{layer_id}:BLOCK_L_LEFT_ROW_1_{line_id}"
    candidate = BlockShearCandidatePath(
        path_id,
        BlockPathFamily.L_LEFT,
        "ROW_1",
        (
            BlockPathSegment(
                BlockPathSegmentKind.SHEAR,
                ProjectedPoint2D(float(x0), float(line)),
                ProjectedPoint2D(float(x1), float(line)),
            ),
            BlockPathSegment(
                BlockPathSegmentKind.TENSION,
                ProjectedPoint2D(float(x1), float(line)),
                ProjectedPoint2D(float(x1), float(side)),
            ),
        ),
        tuple(b for b in points if b != corner_id),
        (),
        (corner_id,),
    )
    physical_group = replace(
        geometry.group,
        bolts=tuple(
            replace(
                b,
                center=PlanarPoint2D(*map(float, points[b.id])),
                hole_diameter=float(hole.hole_diameter.to(scene.length_unit).magnitude),
                bolt_diameter=float(hole.bolt_diameter.to(scene.length_unit).magnitude),
            )
            for b in geometry.group.bolts
        ),
    )
    plans = build_block_shear_area_plans(
        BlockShearPathResolution((candidate,)),
        replace(geometry, group=physical_group),
        scene.length_unit,
        PhysicalQuantity.of(actual_thickness, scene.length_unit),
        tuple(BoltHoleSource(b.id, hole) for b in physical_group.bolts),
    )
    solids, proven = _continuity(scene, face)
    return DirectAngleBlockPath(
        "BLOCK_SHEAR:" + path_id,
        f"BLOCK_SHEAR:{layer_id}:BLOCK_L_RIGHT_ROW_1_{line_id}",
        scene.length_unit,
        component_id,
        face.physical_element_id,
        (end.boundary_id, free.boundary_id, junction.boundary_id),
        selected,
        ((x0, line), (x1, line), (x1, side), (x0, side)),
        ((x0, line), (x1, line), (x1, heel_side), (x0, heel_side)),
        candidate,
        plans.candidates[0],
        solids,
        proven,
        HEEL_REASON if proven else "Physical Angle heel/perpendicular-leg continuity is unproved",
    )


def evaluate_direct_angle_block(
    value: EccentricResistanceHandoffInput,
    geometry: MultiRowGeometry,
    scene: SingleBoltVisualizationSnapshot,
    faces: tuple[DirectEngineeringFace, ...],
    hole: StandardHoleDefinition,
) -> DirectAngleBlockResult:
    """Authenticate geometry and force line, then reuse the accepted frozen handoff."""

    bundle = value.execution_bundle
    layer = bundle.layers[0]
    path = None
    eccentricity = None
    handoff = None
    supported: tuple[MultiRowCheckResult, ...] = ()
    history: tuple[DirectBlockHistoryResult, ...] = ()
    method = "DIRECT_PHYSICAL_L_PATH_NOT_SUPPORTED"
    code_satisfied = False
    reason = ""
    try:
        path = resolve_direct_angle_block_path(
            geometry, scene, faces, hole, layer.layer_id, layer.component_id, layer.thickness
        )
        if path.heel_continuity_proven:
            history = (
                DirectBlockHistoryResult(
                    path.heel_check_id,
                    layer.layer_id,
                    "BLOCK_SHEAR",
                    MultiRowResultAvailability.NOT_APPLICABLE,
                    NumericalComparison.NOT_EVALUATED,
                    path.continuity_reason,
                    False,
                ),
            )
        demand = value.demand_result
        force = demand.projected_force
        axis = value.layer_axes[0].lw_axis
        if (
            force.u.canonical_magnitude <= 0
            or force.v.canonical_magnitude != 0
            or axis[1] != 0
            or layer.material_direction is not MaterialDirection.LONGITUDINAL
        ):
            raise ValueError(
                "METHOD / SOURCE NOT SUPPORTED: physical tension cut requires Ft,L "
                "and a longitudinal force"
            )
        scenario = next(s for s in demand.scenarios if s.scenario_id == value.scenario_id)
        if bundle.eccentricity is None:
            raise ValueError("Authenticated eccentricity representation policy is missing")
        with localcontext() as context:
            context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
            offset = PhysicalQuantity.of(
                -scenario.external_moment.canonical_magnitude / force.u.canonical_magnitude,
                Unit.MM,
            )
        reference = "DIRECT_AUTHENTICATED_ACTION_REFERENCE:" + demand.action_source_id
        geometry_ids = tuple(
            dict.fromkeys(
                (
                    *layer.source_geometry_ids,
                    *path.boundary_ids,
                    *[f.source_geometry_id for f in path.raw_faces],
                )
            )
        )
        eccentricity = BlockShearEccentricityContext(
            offset,
            reference,
            bundle.eccentricity.tolerance,
            geometry_ids,
            classify_block_shear_eccentricity(offset, bundle.eccentricity.tolerance),
        )
        concentric = eccentricity.classification.value == "CONCENTRIC"
        method = f"ASCE_8_14{'A' if concentric else 'B'}_DIRECT_PHYSICAL_L_PATH_RATIONAL"
        plan = path.area_plan
        invalid = NetAreaStatus.INVALID_GEOMETRY in {
            plan.shear_net_area_status,
            plan.tension_net_area_status,
        }
        code_satisfied = all(
            s is NetAreaStatus.SATISFIES_MINIMUM_NET_AREA
            for s in (plan.shear_net_area_status, plan.tension_net_area_status)
        )
        check = replace(
            next(c for c in bundle.checks if c.check_id == path.check_id),
            source_plan_id=plan.path_id,
            path_id=plan.path_id,
            block_plan=plan,
            method=(
                MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14A
                if concentric
                else MultiRowEquationMethod.BLOCK_SHEAR_ASCE_EQ_8_14B
            ),
            source_locator="ASCE/SEI 74-23 8.3.3.3, 2.10; Slice 2 physical rational L path; "
            + method,
            method_applicability=MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE,
            qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
            plan_availability=PlanAvailability.READY,
            geometry_status=GeometryStatus.INVALID_GEOMETRY if invalid else GeometryStatus.VALID,
            demand=bundle.signed_demand.in_plane_magnitude,
        )
        physical_bundle = replace(
            bundle,
            eccentricity=eccentricity,
            checks=(check,),
            required_checks=MultiRowRequiredCheckContract((check.check_id,)),
            block_shear_plans=replace(bundle.block_shear_plans, candidates=(plan,)),
            fingerprint_metadata=(
                *bundle.fingerprint_metadata,
                MultiRowFingerprintMetadataEntry(CONTRACT, _fingerprint(asdict(path))),
            ),
        )
        evidence = BlockShearCompatibilityEvidence(
            BlockShearCompatibilityStatus.MATCHED,
            CONTRACT + ":" + demand.result_fingerprint,
            demand.action_source_id,
            demand.interface_frame.interface_id,
            physical_bundle.signed_demand.source_id,
            physical_bundle.physical_geometry.interface_id,
            reference,
            geometry_ids,
            (check.check_id,),
        )
        with localcontext() as context:
            context.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
            handoff = calculate_eccentric_resistance_handoff(
                replace(
                    value,
                    execution_bundle=physical_bundle,
                    block_shear_compatibility=evidence,
                    source_trace=(*value.source_trace, CONTRACT),
                )
            )
        supported = handoff.supported_results
        reason = (
            "Raw net area below 75% of gross area; numerical resistance retained; "
            "ordinary compliant PASS prohibited"
            if not invalid and not code_satisfied
            else ""
        )
    except ValueError as error:
        reason = str(error)
    fingerprint = _fingerprint(
        (
            CONTRACT,
            value.demand_result.result_fingerprint,
            asdict(path) if path else None,
            asdict(eccentricity) if eccentricity else None,
            handoff.result_fingerprint if handoff else None,
            reason,
        )
    )
    return DirectAngleBlockResult(
        CONTRACT,
        value.scenario_id,
        method,
        path,
        eccentricity,
        value.demand_result.result_fingerprint,
        handoff,
        supported,
        history,
        code_satisfied,
        reason,
        fingerprint,
    )
