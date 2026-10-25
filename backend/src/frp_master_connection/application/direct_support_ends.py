"""Explicit Direct W end authority, independent of the finite presentation segment.

The reference is the fixed interface origin projected on the W longitudinal
axis. Native row/line offsets use the already governed Direct template axes;
raw inverse transforms remain witnesses, never a new engineering tolerance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation import PhysicalQuantity, Unit, decimal_from_finite_real
from frp_master_connection.domain import PositionVector3D

from .visualization import BoltDisplaySnapshot, SingleBoltVisualizationSnapshot


class DirectSupportEndCondition(StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    CONTINUOUS_THROUGH_CONNECTION = "CONTINUOUS_THROUGH_CONNECTION"
    FINITE_BOTH_ENDS = "FINITE_BOTH_ENDS"
    FINITE_NEGATIVE_END_ONLY = "FINITE_NEGATIVE_END_ONLY"
    FINITE_POSITIVE_END_ONLY = "FINITE_POSITIVE_END_ONLY"


@dataclass(frozen=True, slots=True)
class DirectSupportEndInput:
    condition: DirectSupportEndCondition = DirectSupportEndCondition.UNSPECIFIED
    negative_end_distance: PhysicalQuantity | None = None
    positive_end_distance: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.condition, DirectSupportEndCondition):
            raise TypeError("Direct support end condition must be a governed enum.")
        negative = self.condition in {
            DirectSupportEndCondition.FINITE_BOTH_ENDS,
            DirectSupportEndCondition.FINITE_NEGATIVE_END_ONLY,
        }
        positive = self.condition in {
            DirectSupportEndCondition.FINITE_BOTH_ENDS,
            DirectSupportEndCondition.FINITE_POSITIVE_END_ONLY,
        }
        for expected, value in (
            (negative, self.negative_end_distance),
            (positive, self.positive_end_distance),
        ):
            if expected != (value is not None):
                raise ValueError("Supply exactly the real end distances selected by the condition.")
            if value is not None and (value.unit not in {Unit.IN, Unit.MM} or value.magnitude <= 0):
                raise ValueError("Real support end distances must be positive in or mm.")


@dataclass(frozen=True, slots=True)
class DirectSupportBoltEndRecord:
    bolt_id: str
    raw_member_local_station: Decimal
    raw_reference_offset: Decimal
    canonical_reference_offset: Decimal
    negative_end_distance: Decimal | None
    positive_end_distance: Decimal | None
    loaded_end_direction: str
    loaded_end_distance: Decimal | None
    loaded_end_state: str


@dataclass(frozen=True, slots=True)
class DirectSupportEndAuthority:
    contract_version: str
    condition: DirectSupportEndCondition
    component_id: str
    length_unit: Unit
    reference_source: str
    reference_global: tuple[float, float, float]
    raw_reference_global: tuple[float, float, float]
    reference_member_local_station: Decimal
    longitudinal_axis_global: tuple[float, float, float]
    negative_end_distance: PhysicalQuantity | None
    positive_end_distance: PhysicalQuantity | None
    negative_end_member_local_station: Decimal | None
    positive_end_member_local_station: Decimal | None
    negative_end_global: tuple[float, float, float] | None
    positive_end_global: tuple[float, float, float] | None
    presentation_crop_member_local_stations: tuple[Decimal, Decimal]
    presentation_crop_authority: str
    bolt_records: tuple[DirectSupportBoltEndRecord, ...]
    coordinate_canonicalization: str
    applicability: tuple[tuple[str, str, str], ...]

    def actual_end(self, minimum: bool) -> Decimal | None:
        return (
            self.negative_end_member_local_station
            if minimum
            else self.positive_end_member_local_station
        )


def resolve_direct_support_ends(
    declaration: DirectSupportEndInput,
    snapshot: SingleBoltVisualizationSnapshot,
    bolts: Sequence[BoltDisplaySnapshot],
    *,
    interface_id: str,
    anchor_x: Decimal,
    native_centers: Mapping[str, tuple[Decimal, Decimal]],
    template_axes: tuple[tuple[Decimal, Decimal, Decimal], ...],
    force_global: tuple[float, float, float],
) -> DirectSupportEndAuthority:
    """Resolve real ends before physics; crops remain separately named witnesses."""
    support = next(c for c in snapshot.components if c.section_family == "WIDE_FLANGE")
    frames = {f.id: f.frame for f in snapshot.frames}
    frame = frames[f"MEMBER_LOCAL:{support.id}"]
    origin = frames[f"INTERFACE_LOCAL:{interface_id}"].origin
    projected = frame.parent_to_local_point(origin)
    raw_reference = decimal_from_finite_real(projected.x)

    def canonical_station(value: float) -> Decimal:
        return (
            PhysicalQuantity.of(
                PhysicalQuantity.of(decimal_from_finite_real(value), snapshot.length_unit)
                .to(Unit.IN)
                .magnitude.quantize(Decimal("1e-9")),
                Unit.IN,
            )
            .to(snapshot.length_unit)
            .magnitude
        )

    reference = canonical_station(projected.x)
    axis = (frame.x_axis.x, frame.x_axis.y, frame.x_axis.z)
    reference_point = frame.local_to_parent_point(PositionVector3D(projected.x, 0, 0))
    canonical_global = tuple(
        float(canonical_station(v))
        for v in (reference_point.x, reference_point.y, reference_point.z)
    )
    negative = (
        None
        if declaration.negative_end_distance is None
        else reference - declaration.negative_end_distance.to(snapshot.length_unit).magnitude
    )
    positive = (
        None
        if declaration.positive_end_distance is None
        else reference + declaration.positive_end_distance.to(snapshot.length_unit).magnitude
    )

    def global_end(station: Decimal | None) -> tuple[float, float, float] | None:
        if station is None:
            return None
        delta = station - reference
        values = tuple(
            float(decimal_from_finite_real(p) + delta * decimal_from_finite_real(a))
            for p, a in zip(canonical_global, axis, strict=True)
        )
        return values[0], values[1], values[2]

    solids = [
        p
        for p in (*snapshot.view_extension_primitives, *snapshot.primitives)
        if p.owner_id == support.id and p.kind.value == "BOX"
    ]
    parameters = {p.name: p.value for p in solids[0].parameters}
    crops = (
        decimal_from_finite_real(parameters["x_start"]),
        decimal_from_finite_real(parameters["x_end"]),
    )
    loaded_positive = sum(f * a for f, a in zip(force_global, axis, strict=True)) >= 0
    precision = PhysicalQuantity.of("1e-9", Unit.IN).to(snapshot.length_unit).magnitude
    records = []
    with localcontext() as context:
        context.prec = 100
        longitudinal = tuple(decimal_from_finite_real(a) for a in axis)
        row_projection, line_projection = (
            sum((a * b for a, b in zip(direction, longitudinal, strict=True)), Decimal(0))
            for direction in template_axes[:2]
        )
        for bolt in bolts:
            raw_station = decimal_from_finite_real(frame.parent_to_local_point(bolt.center).x)
            x, y = native_centers[bolt.bolt_location_id]
            offset = (x - anchor_x) * row_projection + y * line_projection
            raw_offset = raw_station - raw_reference
            if abs(raw_offset - offset) > precision:
                raise ValueError("Direct W station and native row/line projection disagree.")
            below = None if negative is None else offset + reference - negative
            above = None if positive is None else positive - reference - offset
            loaded = above if loaded_positive else below
            records.append(
                DirectSupportBoltEndRecord(
                    bolt.bolt_location_id,
                    raw_station,
                    raw_offset,
                    offset,
                    below,
                    above,
                    "POSITIVE_ABOVE" if loaded_positive else "NEGATIVE_BELOW",
                    loaded,
                    "NO_FINITE_END_IN_DIRECTION" if loaded is None else "REAL_SUPPORT_MEMBER_END",
                )
            )
    return DirectSupportEndAuthority(
        "SHEAR01-DIRECT-OR2-F3-R1",
        declaration.condition,
        support.id,
        snapshot.length_unit,
        f"INTERFACE_LOCAL:{interface_id}:ORIGIN_PROJECTED_ON_SUPPORT_LONGITUDINAL_AXIS",
        (canonical_global[0], canonical_global[1], canonical_global[2]),
        (reference_point.x, reference_point.y, reference_point.z),
        reference,
        axis,
        declaration.negative_end_distance,
        declaration.positive_end_distance,
        negative,
        positive,
        global_end(negative),
        global_end(positive),
        crops,
        "VIEW_CROP_ONLY_NO_ENGINEERING_END_AUTHORITY",
        tuple(records),
        "DIRECT_NATIVE_ROW_LINE_PROJECTION_WITHIN_EXISTING_1E-9_IN_TEMPLATE_FRAME_PRECISION",
        (
            ("PHYSICAL_LOADED_END_MINIMUM", "NOT_APPLICABLE_WITHOUT_REAL_END", "ASCE Table 8-1"),
            (
                "W_FIRST_ROW_NET_TENSION",
                "METHOD_REQUIRED",
                "ASCE 8.3.3.1: independent W path mapping absent",
            ),
            (
                "W_INTERROW_SHEAR_OUT",
                "METHOD_REQUIRED",
                "ASCE 8.3.3.2: Eq 8-12 needs real free end; independent W path mapping absent",
            ),
            ("W_BLOCK_SHEAR", "METHOD_REQUIRED", "ASCE 8.3.3.3: independent W failure path absent"),
            (
                "W_SINGLE_ROW_LIMITS",
                "METHOD_REQUIRED_OR_SOURCE_DIRECTION_NOT_APPLICABLE",
                "ASCE 8.3.2.2-4: independent W section/free-end mapping absent",
            ),
            ("W_PIN_BEARING", "UNCHANGED", "ASCE 8.3.2.1: no end-distance parameter"),
        ),
    )
