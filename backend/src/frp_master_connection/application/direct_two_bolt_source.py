"""Geometry source for faces that the existing resistance router cannot evaluate.

No resistance router is relaxed. The single-bolt physical preview supplies the
actual solids, proper frames, selected faces and ordered stack. The submitted
two-station/end definition supplies the same finite Angle end as the established
Direct multi-row physical mapping. No display crop becomes a support end.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from frp_master_connection.application.connection_preview import preview_single_bolt_connection
from frp_master_connection.application.direct_support_ends import DirectSupportEndCondition
from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationRequest,
    MultiRowPhysicalBoltVisualization,
)
from frp_master_connection.application.visualization import (
    ConnectionViewExtents,
    SingleBoltVisualizationSnapshot,
)
from frp_master_connection.domain import PositionVector3D


@dataclass(frozen=True, slots=True)
class GeometrySupportEnds:
    condition: DirectSupportEndCondition
    negative: Decimal | None
    positive: Decimal | None
    reference_source: str = "Submitted support ends from actual interface-origin projection"

    def actual_end(self, minimum: bool) -> Decimal | None:
        return self.negative if minimum else self.positive


@dataclass(frozen=True, slots=True)
class GeometrySourceView:
    physical_connection: SingleBoltVisualizationSnapshot
    physical_bolts: tuple[MultiRowPhysicalBoltVisualization, ...]
    placement_trace: tuple[tuple[str, str], ...]


def unmapped_geometry_source(
    request: MultiRowOrchestrationRequest,
) -> tuple[GeometrySourceView, GeometrySupportEnds]:
    physical = request.physical_connection_request
    if physical is None:
        raise ValueError("Typed physical connection geometry is required.")
    # Same submitted/native loaded-end definition as the accepted Direct mapping.
    # This is a physical end, independent of any later viewer crop.
    true_angle_length = (
        (request.unloaded_end_e1 + request.pitch + request.loaded_boundary_to_row_1_distance)
        .to(request.source_length_unit)
        .magnitude
    )
    extents = request.connection_view_extents
    if extents is None:
        # No caller-supplied display extents: obtain the existing nominal support
        # crop from its trusted physical solids; it remains presentation only.
        initial = preview_single_bolt_connection(physical).visualization
        if initial is None:
            raise ValueError("Physical geometry is unresolved.")
        crop_support = next(c for c in initial.components if c.section_family == "WIDE_FLANGE")
        frame = next(f.frame for f in initial.frames if f.id == f"MEMBER_LOCAL:{crop_support.id}")
        origin = next(
            f.frame.origin
            for f in initial.frames
            if f.id == f"INTERFACE_LOCAL:{request.interface_id}"
        )
        crop_station = frame.parent_to_local_point(origin).x
        primitive = next(
            p for p in initial.primitives if p.owner_id == crop_support.id and p.kind.value == "BOX"
        )
        values = {p.name: p.value for p in primitive.parameters}
        extents = ConnectionViewExtents(
            float(true_angle_length),
            crop_station - values["x_start"],
            values["x_end"] - crop_station,
        )
    else:
        extents = replace(extents, brace_view_length=float(true_angle_length))
    preview = preview_single_bolt_connection(physical, extents)
    base = preview.visualization
    if base is None or len(base.bolt.holes) != 2 or len(base.bolt.washers) != 2:
        raise ValueError("Selected physical faces and the ordered two-member stack are unresolved.")
    brace_id = base.bolt.holes[0].participant_id
    support_id = base.bolt.holes[1].participant_id
    frames = {f.id: f.frame for f in base.frames}
    brace = frames[f"MEMBER_LOCAL:{brace_id}"]
    pitch = float(request.pitch.to(request.source_length_unit).magnitude)

    def translated(point: PositionVector3D, distance: float = pitch) -> PositionVector3D:
        return PositionVector3D(
            point.x + distance * brace.x_axis.x,
            point.y + distance * brace.x_axis.y,
            point.z + distance * brace.x_axis.z,
        )

    first = base.bolt
    raw_anchor = first.center
    raw_local_station = brace.parent_to_local_point(first.center).x
    # The single-station template anchor does not define the submitted unloaded
    # end of a two-station group. Honor that explicit input in this geometry-only
    # adapter; changing it never relaxes the unchanged resistance router.
    displacement = (
        float(request.unloaded_end_e1.to(request.source_length_unit).magnitude) - raw_local_station
    )
    first = replace(
        first,
        center=translated(first.center, displacement),
        stack_start=translated(first.stack_start, displacement),
        stack_end=translated(first.stack_end, displacement),
        holes=tuple(
            replace(h, start=translated(h.start, displacement), end=translated(h.end, displacement))
            for h in first.holes
        ),
        washers=tuple(
            replace(w, start=translated(w.start, displacement), end=translated(w.end, displacement))
            for w in first.washers
        ),
    )
    base = replace(base, bolt=first)
    second = replace(
        first,
        bolt_location_id="SAB2-SOURCE-SECOND",
        center=translated(first.center),
        stack_start=translated(first.stack_start),
        stack_end=translated(first.stack_end),
        holes=tuple(
            replace(h, start=translated(h.start), end=translated(h.end)) for h in first.holes
        ),
        washers=tuple(
            replace(w, start=translated(w.start), end=translated(w.end)) for w in first.washers
        ),
    )
    bolts = tuple(
        MultiRowPhysicalBoltVisualization(
            bolt.bolt_location_id,
            f"GEOMETRIC_STATION_{i + 1}",
            "GEOMETRIC_LINE",
            (),
            bolt,
        )
        for i, bolt in enumerate((first, second))
    )
    support_frame = frames[f"MEMBER_LOCAL:{support_id}"]
    reference = support_frame.parent_to_local_point(
        frames[f"INTERFACE_LOCAL:{request.interface_id}"].origin
    )
    station = Decimal(str(reference.x))
    declaration = request.supporting_w_longitudinal_ends
    condition = (
        DirectSupportEndCondition.UNSPECIFIED if declaration is None else declaration.condition
    )
    negative = (
        None
        if declaration is None or declaration.negative_end_distance is None
        else (station - declaration.negative_end_distance.to(request.source_length_unit).magnitude)
    )
    positive = (
        None
        if declaration is None or declaration.positive_end_distance is None
        else (station + declaration.positive_end_distance.to(request.source_length_unit).magnitude)
    )
    trace = (
        ("scope", "Geometry-only station placement; no resistance method activation"),
        ("length_unit", request.source_length_unit.value),
        ("raw_template_anchor_global", str((raw_anchor.x, raw_anchor.y, raw_anchor.z))),
        ("raw_template_anchor_brace_station", str(raw_local_station)),
        ("submitted_unloaded_end_e1", str(request.unloaded_end_e1.magnitude)),
        ("submitted_unloaded_end_e1_unit", request.unloaded_end_e1.unit.value),
        ("actual_translation_along_brace", str(displacement)),
        ("placed_first_center_global", str((first.center.x, first.center.y, first.center.z))),
        ("second_station_pitch", str(pitch)),
    )
    return GeometrySourceView(base, bolts, trace), GeometrySupportEnds(
        condition, negative, positive
    )
