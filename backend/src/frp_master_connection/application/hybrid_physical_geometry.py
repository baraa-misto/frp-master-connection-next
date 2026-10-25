"""Geometry-only R3 adapter. No property, demand or resistance routine is called."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_corrections import Point
from frp_master_connection.calculation.rhm_direct_r3 import (
    Edge,
    R3Geometry,
    _edges,
    _fit,
    _frame,
)
from frp_master_connection.calculation.rhm_direct_reference import sincos
from frp_master_connection.calculation.rhm_reference import PRECISION

RECEIVING_FRAME = "DIRECT_RECEIVING_LW_CW_TT"


class EndCondition(StrEnum):
    UNKNOWN = "UNKNOWN"
    CONTINUOUS = "CONTINUOUS"
    FREE = "FREE"


@dataclass(frozen=True, slots=True)
class ReceivingEnd:
    condition: EndCondition = EndCondition.UNKNOWN
    distance: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        if self.condition is EndCondition.FREE:
            if self.distance is None or self.distance.to(Unit.IN).magnitude < 0:
                raise ValueError("A real free end requires its nonnegative datum distance.")
        elif self.distance is not None:
            raise ValueError("Unknown or continuous directions cannot carry a fabricated end.")


@dataclass(frozen=True, slots=True)
class ReceivingEnds:
    positive: ReceivingEnd = ReceivingEnd()
    negative: ReceivingEnd = ReceivingEnd()


@dataclass(frozen=True, slots=True)
class R3SceneGeometry:
    geometry: R3Geometry
    bolt_centers: tuple[tuple[str, Point], ...]
    p_axis: Point
    n_axis: Point
    edges: tuple[Edge, ...]
    hole_fit: bool
    rotation_centers: tuple[tuple[str, Point], ...]
    rotation_fit: bool
    end_failures: tuple[tuple[str, str], ...]


def receiving_end_failures(
    g: R3Geometry, centers: tuple[tuple[str, Point], ...], ends: ReceivingEnds
) -> tuple[tuple[str, str], ...]:
    """Actual hole circles, not a display crop or virtual net-hole deduction."""
    radius = g.hole.to(Unit.IN).magnitude / 2
    origin = _frame(g, (Decimal(0), Decimal(0)))
    axis = _frame(g, (Decimal(0), Decimal(1)), vector=True)
    failures = []
    for name, point in centers:
        along = sum((point[i] - origin[i]) * axis[i] for i in range(2))
        for label, sign, end in (
            ("positive", 1, ends.positive),
            ("negative", -1, ends.negative),
        ):
            if (
                end.distance is not None
                and sign * along + radius > end.distance.to(Unit.IN).magnitude
            ):
                failures.append((name, label))
    return tuple(failures)


def r3_scene_geometry(g: R3Geometry, ends: ReceivingEnds | None = None) -> R3SceneGeometry:
    """Reuse the frozen coordinate helpers at their original 60-digit precision."""
    ends = ReceivingEnds() if ends is None else ends
    with localcontext() as context:
        context.prec = PRECISION
        pitch = g.vertical_bolt_pitch.to(Unit.IN).magnitude
        s, c = sincos(g.phi)
        local = (("B1", (Decimal(0), pitch / 2)), ("B2", (Decimal(0), -pitch / 2)))
        centers = tuple((name, _frame(g, point)) for name, point in local)
        if g.reverse_bolt_order:
            centers = tuple(reversed(centers))
        p = _frame(g, (c, -s), vector=True)
        n = _frame(g, (s, c), vector=True)
        edges = _edges(g, (s, c), local[0][1])
        rotated = tuple(
            (name, _frame(g, point))
            for name, point in (
                ("B1", (-pitch * c / 2, pitch * s / 2)),
                ("B2", (pitch * c / 2, -pitch * s / 2)),
            )
        )
        failures = receiving_end_failures(g, centers, ends)
        rotated_failures = receiving_end_failures(g, rotated, ends)
        return R3SceneGeometry(
            g,
            centers,
            p,
            n,
            edges,
            _fit(g, centers, edges) and not failures,
            rotated,
            _fit(g, rotated, edges) and not rotated_failures,
            failures,
        )
