"""Deterministic, read-only report views of native physical geometry.

The report receives only geometry extracted from the authenticated calculation
snapshot.  It projects those same physical primitives at fixed camera settings;
there is no image upload, asset fetch, or engineering geometry inference.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
from reportlab.lib import colors

from frp_master_connection.reporting.geometry import BoltPoint, BoxFigure, FaceFigure

_FACES = (
    (0, 1, 3, 2),
    (4, 6, 7, 5),
    (0, 4, 5, 1),
    (2, 3, 7, 6),
    (0, 2, 6, 4),
    (1, 5, 7, 3),
)
_CAMERA = (-0.55, -1.0, 0.5425)


def _projection(point: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = point
    if view == "isometric":
        return x - 0.55 * y, z + 0.35 * (x + y)
    if view == "elevation":
        return x, z
    if view == "plan":
        return x, y
    raise ValueError(f"Unknown report camera: {view}")


def _palette(identity: str) -> tuple[str, str]:
    name = identity.lower()
    if "concrete" in name or "wall" in name or "foundation" in name:
        return "#b7bfc4", "Concrete or foundation"
    if any(token in name for token in ("bolt", "anchor", "fastener", "shaft")):
        return "#a84e3b", "Hardware"
    if "connected-member" in name or "connected_member" in name:
        return "#326f9b", "Connected member"
    if any(token in name for token in ("angle", "plate", "tee", "connector", "clip")):
        return "#b48748", "Connector"
    if any(token in name for token in ("support", "column", "chord")):
        return "#8295a5", "Support member"
    return "#326f9b", "Connected member"


def _shade(hex_color: str, factor: float) -> colors.Color:
    color = colors.HexColor(hex_color)
    return colors.Color(
        min(1.0, color.red * factor),
        min(1.0, color.green * factor),
        min(1.0, color.blue * factor),
    )


def component_legend(
    boxes: list[BoxFigure], faces: list[FaceFigure], bolts: list[BoltPoint]
) -> list[tuple[str, str]]:
    """List every visible native ID once, including multiplicity and class."""

    counts = Counter([box.identity for box in boxes] + [face.identity for face in faces])
    rows = [
        (
            identity,
            f"{_palette(identity)[1]} ({count} physical primitive{'s' if count != 1 else ''})",
        )
        for identity, count in counts.items()
    ]
    bolt_counts = Counter(bolt.identity for bolt in bolts)
    rows.extend(
        (identity, f"Bolt or anchor ({count} center{'s' if count != 1 else ''})")
        for identity, count in bolt_counts.items()
        if identity not in counts
    )
    return rows


def _clip_polygon(
    points: list[tuple[float, float]], bounds: tuple[float, float, float, float]
) -> list[tuple[float, float]]:
    """Crop a projection viewport without altering the native 3-D primitives."""

    x0, x1, y0, y1 = bounds
    output = points
    for axis, bound, keep_greater in ((0, x0, True), (0, x1, False), (1, y0, True), (1, y1, False)):
        source, output = output, []
        if not source:
            break
        previous = source[-1]
        for current in source:
            old_inside = previous[axis] >= bound if keep_greater else previous[axis] <= bound
            new_inside = current[axis] >= bound if keep_greater else current[axis] <= bound
            if old_inside != new_inside:
                fraction = (bound - previous[axis]) / (current[axis] - previous[axis])
                output.append(
                    (
                        previous[0] + fraction * (current[0] - previous[0]),
                        previous[1] + fraction * (current[1] - previous[1]),
                    )
                )
            if new_inside:
                output.append(current)
            previous = current
    return output


def colored_view(
    boxes: list[BoxFigure],
    faces: list[FaceFigure],
    bolts: list[BoltPoint],
    view: str,
    *,
    action_force: tuple[float, float, float] | None = None,
    action_reference: tuple[float, float, float] | None = None,
    action_label: str = "Applied force at native reference",
) -> Drawing:
    """Render a fixed, vector report camera from native vertices and bolt centers."""

    points_3d = [vertex for box in boxes for vertex in box.vertices]
    points_3d.extend(vertex for face in faces for vertex in face.vertices)
    points_3d.extend(bolt.center for bolt in bolts)
    if not points_3d:
        raise ValueError("Colored report view requires native physical geometry")
    focus_points = [
        vertex
        for box in boxes
        if "concrete" not in box.identity.lower() and "wall" not in box.identity.lower()
        for vertex in box.vertices
    ]
    focus_points.extend(vertex for face in faces for vertex in face.vertices)
    focus_points.extend(bolt.center for bolt in bolts)
    detail_crop = bool(focus_points and len(focus_points) < len(points_3d))
    projected = [_projection(point, view) for point in (focus_points if detail_crop else points_3d)]
    x0, x1 = min(point[0] for point in projected), max(point[0] for point in projected)
    y0, y1 = min(point[1] for point in projected), max(point[1] for point in projected)
    pad_x, pad_y = max((x1 - x0) * 0.12, 0.5), max((y1 - y0) * 0.12, 0.5)
    x0, x1, y0, y1 = x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y
    width, height = 480.0, 242.0
    scale = min(440 / max(x1 - x0, 0.001), 188 / max(y1 - y0, 0.001))

    def paper(point: tuple[float, float, float]) -> tuple[float, float]:
        x, y = _projection(point, view)
        return 20 + (x - x0) * scale, 28 + (y - y0) * scale

    drawing = Drawing(width, height)
    view_scope = "connection detail crop" if detail_crop else "native physical geometry"
    drawing.add(
        String(
            9,
            height - 14,
            f"Canonical {view} | {view_scope} | NOT TO SCALE",
            fontName="ReportVeraBold",
            fontSize=9,
            fillColor=colors.HexColor("#153949"),
        )
    )
    polygons: list[tuple[float, str, float, list[float]]] = []
    for box in boxes:
        base = _palette(box.identity)[0]
        for index, face_ids in enumerate(_FACES):
            face_points = [box.vertices[item] for item in face_ids]
            depth = (
                sum(sum(point[axis] * _CAMERA[axis] for axis in range(3)) for point in face_points)
                / 4
            )
            clipped = _clip_polygon(
                [_projection(point, view) for point in face_points], (x0, x1, y0, y1)
            )
            xy = [
                coordinate
                for point in clipped
                for coordinate in (20 + (point[0] - x0) * scale, 28 + (point[1] - y0) * scale)
            ]
            if len(clipped) >= 3:
                polygons.append((depth, base, (0.84, 1.0, 1.12, 0.9, 0.75, 1.06)[index], xy))
    for face in faces:
        depth = sum(
            sum(point[axis] * _CAMERA[axis] for axis in range(3)) for point in face.vertices
        ) / len(face.vertices)
        clipped = _clip_polygon(
            [_projection(point, view) for point in face.vertices], (x0, x1, y0, y1)
        )
        xy = [
            coordinate
            for point in clipped
            for coordinate in (20 + (point[0] - x0) * scale, 28 + (point[1] - y0) * scale)
        ]
        if len(clipped) >= 3:
            polygons.append((depth, _palette(face.identity)[0], 1.0, xy))
    for _, base, shade, xy in sorted(polygons, key=lambda item: item[0]):
        drawing.add(
            Polygon(
                xy,
                strokeColor=colors.HexColor("#344b59"),
                strokeWidth=0.55,
                fillColor=_shade(base, shade),
            )
        )
    for bolt in bolts:
        x, y = paper(bolt.center)
        drawing.add(
            Circle(
                x,
                y,
                3.2,
                fillColor=colors.HexColor("#a84e3b"),
                strokeColor=colors.HexColor("#4c251e"),
                strokeWidth=0.7,
            )
        )
    if action_force is not None and action_reference is not None:
        dx, dy = _projection(action_force, view)
        magnitude = math.hypot(dx, dy)
        if magnitude > 0:
            ux, uy = dx / magnitude, dy / magnitude
            x, y = paper(action_reference)
            end_x, end_y = x + 52 * ux, y + 52 * uy
            drawing.add(
                Line(
                    x,
                    y,
                    end_x,
                    end_y,
                    strokeColor=colors.HexColor("#b94b20"),
                    strokeWidth=2.2,
                )
            )
            drawing.add(
                Polygon(
                    [
                        end_x,
                        end_y,
                        end_x - 9 * ux - 5 * uy,
                        end_y - 9 * uy + 5 * ux,
                        end_x - 9 * ux + 5 * uy,
                        end_y - 9 * uy - 5 * ux,
                    ],
                    fillColor=colors.HexColor("#b94b20"),
                    strokeColor=None,
                )
            )
            drawing.add(
                String(
                    9,
                    height - 32,
                    f"{action_label} | arrow direction only",
                    fontName="ReportVeraBold",
                    fontSize=8,
                    fillColor=colors.HexColor("#983d1a"),
                )
            )
    return drawing


def multirow_physical_geometry(visual: dict[str, Any]) -> tuple[list[BoxFigure], list[BoltPoint]]:
    """Adapt the native 2-D plate/row visualization to the fixed report cameras."""

    x0, x1, y0, y1 = (float(value) for value in visual["boundary"])
    thickness = sum(float(layer["thickness"]["value"]) for layer in visual["layers"])
    vertices = tuple(
        (x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (-thickness / 2, thickness / 2)
    )
    bolts = [
        BoltPoint(str(bolt["bolt_id"]), (float(bolt["x"]), float(bolt["y"]), 0.0))
        for bolt in visual["bolts"]
    ]
    return [BoxFigure("Connection plate", vertices)], bolts
