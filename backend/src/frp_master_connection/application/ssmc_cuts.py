"""Actual polygon-minus-circle SSMC section and explicit plate free-body ledger.

Finite candidate stations are demand evidence. The ledger deliberately does not
claim a resistance maximum or continuous-envelope proof.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, cast

from frp_master_connection.calculation.in_plane_wrench_demand import InPlaneWrenchResult
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.geometry.ssmc_polygon import Point2, pairs

if TYPE_CHECKING:
    from frp_master_connection.application.ssmc import SSMCPreview

METHOD = "SSMC_ACTUAL_POLYGON_CUT_FREE_BODY_RC1"


@dataclass(frozen=True, slots=True)
class SSMCCut:
    cut_id: str
    owner: str
    normal: Point2
    station_mm: float
    material_intervals_mm: tuple[tuple[float, float], ...]
    intersected_holes: tuple[str, ...]
    gross_area_mm2: float
    net_area_mm2: float
    centroid_mm: Point2 | None
    second_moment_mm4: float | None
    section_modulus_positive_mm3: float | None
    section_modulus_negative_mm3: float | None
    free_body_shaft_ids: tuple[str, ...]
    cut_N_N: float
    cut_V_N: float
    cut_M_Nmm: float
    sigma_negative_MPa: float | None
    sigma_positive_MPa: float | None
    average_shear_MPa: float | None
    status: str
    method: str = METHOD


@dataclass(frozen=True, slots=True)
class SSMCCutLedger:
    cuts: tuple[SSMCCut, ...]
    candidate_classes: tuple[str, ...]
    finite_coverage_proven: bool
    status: str


def _inside(point: Point2, boundary: tuple[Point2, ...]) -> bool:
    x, z = point
    inside = False
    for a, b in pairs(boundary):
        if (a[1] > z) != (b[1] > z):
            crossing = a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if crossing > x:
                inside = not inside
    return inside


def _merge(intervals: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    merged: list[tuple[float, float]] = []
    for left, right in sorted(intervals):
        if right - left <= 1e-9:
            continue
        if merged and left <= merged[-1][1] + 1e-9:
            merged[-1] = merged[-1][0], max(right, merged[-1][1])
        else:
            merged.append((left, right))
    return tuple(merged)


def _subtract(
    intervals: tuple[tuple[float, float], ...],
    removed: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    kept: list[tuple[float, float]] = []
    for left, right in intervals:
        cursor = left
        for a, b in removed:
            if b <= cursor or a >= right:
                continue
            if a > cursor:
                kept.append((cursor, min(a, right)))
            cursor = max(cursor, b)
            if cursor >= right:
                break
        if cursor < right:
            kept.append((cursor, right))
    return _merge(kept)


def section_intervals(
    boundary: tuple[Point2, ...],
    holes: tuple[tuple[str, Point2, float], ...],
    normal: Point2,
    station: float,
) -> tuple[
    tuple[tuple[float, float], ...],
    tuple[tuple[float, float], ...],
    tuple[str, ...],
]:
    """Intersect a transverse line with the actual boundary and circle chords."""
    tangent = (-normal[1], normal[0])

    def project(point: Point2) -> tuple[float, float]:
        return (
            point[0] * normal[0] + point[1] * normal[1],
            point[0] * tangent[0] + point[1] * tangent[1],
        )

    roots: list[float] = []
    for a, b in pairs(boundary):
        na, sa = project(a)
        nb, sb = project(b)
        if abs(na - station) < 1e-9 and abs(nb - station) < 1e-9:
            roots.extend((sa, sb))
        elif (na <= station < nb) or (nb <= station < na):
            roots.append(sa + (station - na) * (sb - sa) / (nb - na))
        elif abs(na - station) < 1e-9:
            roots.append(sa)
    values = sorted({round(value, 10) for value in roots})
    gross = _merge(
        [
            (a, b)
            for a, b in pairwise(values)
            if _inside(
                (
                    normal[0] * station + tangent[0] * (a + b) / 2,
                    normal[1] * station + tangent[1] * (a + b) / 2,
                ),
                boundary,
            )
        ]
    )
    removal: list[tuple[float, float]] = []
    crossed: list[str] = []
    for identity, center, radius in holes:
        nc, sc = project(center)
        delta = station - nc
        if abs(delta) < radius:
            half = math.sqrt(max(0.0, radius * radius - delta * delta))
            removal.append((sc - half, sc + half))
            crossed.append(identity)
    return gross, _subtract(gross, _merge(removal)), tuple(crossed)


def _stations(preview: SSMCPreview, normal: Point2, scale: float) -> tuple[tuple[str, float], ...]:
    boundary = preview.geometry.polygon.boundary
    holes = preview.geometry.polygon_paths.holes
    shafts = preview.geometry.shafts
    rows = sorted({shaft.row for shaft in shafts})
    values: list[tuple[str, float]] = []
    projections = [
        scale * sum(a * b for a, b in zip(point, normal, strict=True)) for point in boundary
    ]
    offset = max(1e-6, (max(projections) - min(projections)) * 1e-8)
    for index, point in enumerate(boundary):
        station = scale * sum(a * b for a, b in zip(point, normal, strict=True))
        values.extend(
            (
                (f"VERTEX_{index}_POSITIVE_LIMIT", station + offset / 2),
                (f"CORNER_{index}_BEFORE", station - offset),
                (f"CORNER_{index}_AFTER", station + offset),
            )
        )
    for hole in holes:
        center = scale * sum(a * b for a, b in zip(hole.center, normal, strict=True))
        radius = scale * hole.radius
        values.extend(
            (
                (f"HOLE_{hole.shaft_id}_LOW_TANGENT", center - radius),
                (f"HOLE_{hole.shaft_id}_CENTER", center),
                (f"HOLE_{hole.shaft_id}_HIGH_TANGENT", center + radius),
            )
        )
    for row in rows:
        row_points = [shaft.center for shaft in shafts if shaft.row == row]
        values.append(
            (
                f"ROW_{row}",
                scale
                * sum(sum(a * b for a, b in zip(p, normal, strict=True)) for p in row_points)
                / len(row_points),
            )
        )
    for branch in preview.geometry.polygon.branches:
        for label, points in (("CUT_FACE", branch.cut_points), ("FAR_END", branch.far_points)):
            value = (
                scale * sum(sum(a * b for a, b in zip(p, normal, strict=True)) for p in points) / 2
            )
            other_points = branch.far_points if label == "CUT_FACE" else branch.cut_points
            other = (
                scale
                * sum(sum(a * b for a, b in zip(p, normal, strict=True)) for p in other_points)
                / 2
            )
            inward = math.copysign(offset / 2, other - value) if other != value else offset / 2
            values.append(
                (
                    f"{branch.owner}_{label}_INTERIOR_LIMIT",
                    value + inward,
                )
            )
    transition = preview.geometry.polygon.transition
    if transition:
        values.append(
            (
                "NECK_MIDPOINT",
                scale
                * sum(sum(a * b for a, b in zip(p, normal, strict=True)) for p in transition)
                / len(transition),
            )
        )
    return tuple(values)


def build_ssmc_cut_ledger(preview: SSMCPreview) -> SSMCCutLedger:
    """Calculate finite critical sections; keep unproven continuous coverage gated."""
    scale = 25.4 if preview.input.length_unit is Unit.IN else 1.0
    thickness = float(preview.input.plate.thickness.to(Unit.MM).magnitude)
    boundary = tuple((p[0] * scale, p[1] * scale) for p in preview.geometry.polygon.boundary)
    holes = tuple(
        (h.shaft_id, (h.center[0] * scale, h.center[1] * scale), h.radius * scale)
        for h in preview.geometry.polygon_paths.holes
    )
    forces: dict[str, tuple[float, float]] = {}
    for group in preview.groups:
        native = cast(InPlaneWrenchResult | None, group.native_slice8)
        if native is None or native.status != "CALCULATED":
            return SSMCCutLedger((), (), False, "PLANAR_DEMAND_REQUIRED")
        for bolt in native.solution.bolts:
            forces[bolt.bolt_id] = float(bolt.total[0]), float(bolt.total[1])
    normals = tuple((branch.owner, branch.axis) for branch in preview.geometry.polygon.branches)
    normals += (("TRANSITION", preview.geometry.polygon.normal),)
    cuts: list[SSMCCut] = []
    classes: set[str] = set()
    for owner, normal in normals:
        tangent = (-normal[1], normal[0])
        for label, station in _stations(preview, normal, scale):
            classes.add(label.split("_")[0])
            gross, net, intersected = section_intervals(boundary, holes, normal, station)
            gross_area = thickness * sum(b - a for a, b in gross)
            area = thickness * sum(b - a for a, b in net)
            first = thickness * sum((b * b - a * a) / 2 for a, b in net)
            centroid_s = first / area if area > 1e-9 else None
            inertia = (
                thickness * sum((b**3 - a**3) / 3 for a, b in net) - area * centroid_s**2
                if centroid_s is not None
                else None
            )
            if inertia is not None and inertia < 0 and abs(inertia) < 1e-6:
                inertia = 0.0
            center = (
                (
                    normal[0] * station + tangent[0] * centroid_s,
                    normal[1] * station + tangent[1] * centroid_s,
                )
                if centroid_s is not None
                else None
            )
            selected = tuple(
                shaft
                for shaft in preview.geometry.shafts
                if scale * sum(a * b for a, b in zip(shaft.center, normal, strict=True))
                >= station - 1e-8
            )
            fx = -sum(forces[shaft.id][0] for shaft in selected)
            fz = -sum(forces[shaft.id][1] for shaft in selected)
            axial = fx * normal[0] + fz * normal[1]
            shear = fx * tangent[0] + fz * tangent[1]
            moment = (
                -sum(
                    ((shaft.center[1] * scale - center[1]) * forces[shaft.id][0])
                    - ((shaft.center[0] * scale - center[0]) * forces[shaft.id][1])
                    for shaft in selected
                )
                if center is not None
                else 0.0
            )
            low = min((a for a, _ in net), default=0.0)
            high = max((b for _, b in net), default=0.0)
            valid = (
                area > 1e-9 and inertia is not None and inertia > 1e-9 and centroid_s is not None
            )
            negative: float | None
            positive: float | None
            modulus_positive: float | None
            modulus_negative: float | None
            if valid and inertia is not None and centroid_s is not None:
                negative = axial / area + moment * (low - centroid_s) / inertia
                positive = axial / area + moment * (high - centroid_s) / inertia
                modulus_positive = inertia / (high - centroid_s) if high > centroid_s else None
                modulus_negative = inertia / (centroid_s - low) if low < centroid_s else None
            else:
                negative = positive = modulus_positive = modulus_negative = None
            cuts.append(
                SSMCCut(
                    f"{owner}:{label}",
                    owner,
                    normal,
                    station,
                    net,
                    intersected,
                    gross_area,
                    area,
                    center,
                    inertia,
                    modulus_positive,
                    modulus_negative,
                    tuple(shaft.id for shaft in selected),
                    axial,
                    shear,
                    moment,
                    negative,
                    positive,
                    shear / area if valid else None,
                    "CALCULATED_DEMAND_ONLY" if valid else "DEGENERATE_SECTION_REVIEW_REQUIRED",
                )
            )
    # Piecewise geometry alone does not prove stress/path extrema between cuts.
    # A later qualified continuous-envelope proof may narrow the accepted domain.
    return SSMCCutLedger(
        tuple(cuts),
        tuple(sorted(classes)),
        False,
        "FINITE_CANDIDATES_CALCULATED_COVERAGE_NOT_PROVEN",
    )


__all__ = ("METHOD", "SSMCCut", "SSMCCutLedger", "build_ssmc_cut_ledger", "section_intervals")
