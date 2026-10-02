"""Direct-only exact template representation for a proven axial member action.

No force tolerance is added to the frozen group-mode engine. The existing frame
contract bounds representation differences; entered transverse actions are never
eligible. Raw demand is retained in the trace before the canonical input runs.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal, localcontext
from typing import cast

from frp_master_connection.actions import ResolvedManualMemberEndAction
from frp_master_connection.calculation.eccentric_demand import (
    DEMAND_FRAME_TOLERANCE,
    EccentricDemandInput,
    EccentricDemandResult,
    ExactQuantityVector3D,
)
from frp_master_connection.calculation.eccentric_group_modes import (
    ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    Unit,
    decimal_from_finite_real,
)
from frp_master_connection.domain import CoordinateFrameKind

Axes = tuple[
    tuple[Decimal, Decimal, Decimal],
    tuple[Decimal, Decimal, Decimal],
    tuple[Decimal, Decimal, Decimal],
]


def representation_residue_is_zero(raw: Decimal, scale: Decimal) -> bool:
    """Inclusive, dimensionless governed frame bound; physical-zero proof is separate."""
    return abs(raw) <= abs(scale) * DEMAND_FRAME_TOLERANCE


def direct_axial_frame_input(
    value: EccentricDemandInput,
    raw: EccentricDemandResult,
    action: ResolvedManualMemberEndAction,
    axes: Axes,
    force_unit: Unit,
) -> EccentricDemandInput | None:
    """Use exact template axes only for a physically axial, single-line Direct load."""
    source = action.action
    if (
        source.coordinate_frame.kind is not CoordinateFrameKind.MEMBER_LOCAL
        or source.force.fx == 0
        or source.force.fy != 0
        or source.force.fz != 0
        or any(
            component != 0 for component in (source.moment.mx, source.moment.my, source.moment.mz)
        )
    ):
        return None
    row, line, normal = axes
    if any(
        abs(a - b) > DEMAND_FRAME_TOLERANCE
        for a, b in zip(value.interface_frame.u, row, strict=True)
    ):
        return None
    scale = raw.projected_force.u.canonical_magnitude
    if not all(
        representation_residue_is_zero(item.canonical_magnitude, scale)
        for item in (raw.projected_force.v, raw.projected_force.n)
    ):
        return None
    if not raw.scenarios or any(
        scenario.equilibrium is None
        or not scenario.equilibrium.satisfied
        or any(bolt.centered_y.canonical_magnitude != 0 for bolt in scenario.per_bolt)
        for scenario in raw.scenarios
    ):
        return None
    force = PhysicalQuantity.of(
        decimal_from_finite_real(source.force.fx), force_unit
    ).canonical_magnitude
    with localcontext() as context:
        context.prec = 100
        vector = ExactQuantityVector3D(
            *(PhysicalQuantity.of(force * component, Unit.N) for component in row)
        )
    frame = replace(value.interface_frame, u=row, v=line, n=normal)
    trace = {
        "contract": "DIRECT-AXIAL-FRAME-CANONICALIZATION-OR2-F1",
        "rule": "Existing exact template direction quantum = DEMAND_FRAME_TOLERANCE squared",
        "frame_tolerance": str(DEMAND_FRAME_TOLERANCE),
        "physical_zero_proof": (
            "Entered member-local +X/-X only; zero local Y/Z and moments; one physical bolt line"
        ),
        "raw_global_force_N": [
            str(item.canonical_magnitude)
            for item in (
                raw.original_global_force.x,
                raw.original_global_force.y,
                raw.original_global_force.z,
            )
        ],
        "raw_projected_force_N": [
            str(item.canonical_magnitude)
            for item in (raw.projected_force.u, raw.projected_force.v, raw.projected_force.n)
        ],
        "canonical_applicability_transverse_N": "0",
        "raw_demand_input_fingerprint": raw.input_fingerprint,
        "raw_demand_result_fingerprint": raw.result_fingerprint,
        "raw_bolt_vectors_N": {},
        "raw_line_transverse_N": {},
    }
    vectors = cast(dict[str, object], trace["raw_bolt_vectors_N"])
    transverse = cast(dict[str, object], trace["raw_line_transverse_N"])
    with localcontext() as context:
        context.prec = ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION
        magnitude = (scale * scale + raw.projected_force.v.canonical_magnitude**2).sqrt()
        direction = (scale / magnitude, raw.projected_force.v.canonical_magnitude / magnitude)
        for scenario in raw.scenarios:
            u = sum(
                (bolt.total_force.u.canonical_magnitude for bolt in scenario.per_bolt), Decimal(0)
            )
            v = sum(
                (bolt.total_force.v.canonical_magnitude for bolt in scenario.per_bolt), Decimal(0)
            )
            transverse[scenario.scenario_id] = str(direction[0] * v - direction[1] * u)
            vectors[scenario.scenario_id] = {
                bolt.bolt_id: {
                    name: [
                        str(getattr(bolt, name).u.canonical_magnitude),
                        str(getattr(bolt, name).v.canonical_magnitude),
                    ]
                    for name in ("direct_force", "moment_force", "total_force")
                }
                for bolt in scenario.per_bolt
            }
    return replace(
        value,
        global_force=vector,
        interface_frame=frame,
        source_trace=(*value.source_trace, json.dumps(trace, sort_keys=True)),
    )
