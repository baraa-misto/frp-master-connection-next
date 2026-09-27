"""Deterministic, read-only report views of native physical geometry.

The report receives only geometry extracted from the authenticated calculation
snapshot.  It projects those same physical primitives at fixed camera settings;
there is no image upload, asset fetch, or engineering geometry inference.
"""

from __future__ import annotations

import math
import re
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
    if view == "bolt_axis":
        return y, z
    if view == "support_face":
        return x, z
    raise ValueError(f"Unknown report camera: {view}")


def _palette(identity: str) -> tuple[str, str]:
    name = identity.lower()
    if "concrete" in name or "foundation" in name:
        return "#b7bfc4", "Concrete or foundation"
    if any(token in name for token in ("bolt", "anchor", "fastener", "shaft")):
        return "#a84e3b", "Hardware"
    if "connected-member" in name or "connected_member" in name:
        return "#326f9b", "Connected member"
    if "angle_column" in name:
        return "#326f9b", "Connected member"
    if any(token in name for token in ("angle", "plate", "tee", "connector", "clip")):
        return "#b48748", "Connector"
    if any(token in name for token in ("support", "column", "chord", "wall")):
        return "#8295a5", "Support member"
    return "#326f9b", "Connected member"


def _shade(hex_color: str, factor: float) -> colors.Color:
    color = colors.HexColor(hex_color)
    return colors.Color(
        min(1.0, color.red * factor),
        min(1.0, color.green * factor),
        min(1.0, color.blue * factor),
    )


def _component_name(identity: str) -> str:
    upper = identity.upper()
    if "POSITIVE_CLIP_ANGLE" in upper or "NEGATIVE_CLIP_ANGLE" in upper:
        side = "Positive" if "POSITIVE" in upper else "Negative"
        leg = "connected leg" if "CONNECTED" in upper else "support leg"
        return f"{side} clip angle, {leg}"
    if "CONCRETE" in upper or "FOUNDATION" in upper:
        return "Concrete support"
    if "ANGLE_COLUMN" in upper:
        return "Connected angle column"
    if "SPLICE_PLATE" in upper:
        side = "Positive " if "POSITIVE" in upper else "Negative " if "NEGATIVE" in upper else ""
        part = (
            "top flange"
            if "TOP_FLANGE" in upper
            else "bottom flange"
            if "BOTTOM_FLANGE" in upper
            else "web"
            if "WEB" in upper
            else "connection"
        )
        return f"{side}{part} splice plate".strip().capitalize()
    if "TOP_FLANGE_ANGLE" in upper:
        return "Top flange connector angle"
    if "BOTTOM_FLANGE_ANGLE" in upper:
        return "Bottom flange connector angle"
    if "WEB_ANGLE" in upper:
        return (
            "Positive web connector angle"
            if "POSITIVE" in upper
            else "Negative web connector angle"
        )
    if "MITER_WEB_PLATE" in upper:
        return "Miter web plate"
    if "TOP_FLANGE" in upper:
        return "Connected member top flange"
    if "BOTTOM_FLANGE" in upper:
        return "Connected member bottom flange"
    if "WEB" in upper:
        return "Connected member web"
    name = identity.split(":")[-1].replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", name).strip().capitalize()


def component_tags(
    boxes: list[BoxFigure], faces: list[FaceFigure], bolts: list[BoltPoint]
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Assign stable report-only tags; native IDs remain in the audit record."""

    counts = Counter([box.identity for box in boxes] + [face.identity for face in faces])
    tags: dict[str, str] = {}
    totals: Counter[str] = Counter()
    rows: list[tuple[str, str]] = []
    for identity, count in counts.items():
        category = _palette(identity)[1]
        prefix = (
            "S"
            if category in {"Concrete or foundation", "Support member"}
            else "C"
            if category == "Connector"
            else "B"
            if category == "Hardware"
            else "M"
        )
        totals[prefix] += 1
        tag = f"{prefix}{totals[prefix]}"
        tags[identity] = tag
        rows.append(
            (tag, f"{_component_name(identity)}" + (f" ({count} parts)" if count > 1 else ""))
        )
    for bolt in bolts:
        if bolt.identity in tags:
            continue
        prefix = "A" if bolt.role == "anchor" else "B"
        totals[prefix] += 1
        tag = f"{prefix}{totals[prefix]}"
        tags[bolt.identity] = tag
        location = ", ".join(
            item
            for item in (
                bolt.row.replace("_", " ").lower() if bolt.row else "",
                bolt.line.replace("_", " ").lower() if bolt.line else "",
            )
            if item
        )
        description = "External anchor" if bolt.role == "anchor" else "Connection bolt"
        if bolt.role == "anchor":
            side = (
                "positive"
                if bolt.identity.upper().startswith("POS")
                else "negative"
                if bolt.identity.upper().startswith("NEG")
                else ""
            )
            position = re.search(r"R(\d+)[-_]A(\d+)", bolt.identity.upper())
            location = ", ".join(
                item
                for item in (
                    side + " support" if side else "",
                    f"row {position[1]}" if position else "",
                    f"position {position[2]}" if position else "",
                )
                if item
            )
        rows.append((tag, description + (f", {location}" if location else "")))
    return tags, rows


def component_legend(
    boxes: list[BoxFigure], faces: list[FaceFigure], bolts: list[BoltPoint]
) -> list[tuple[str, str]]:
    return component_tags(boxes, faces, bolts)[1]


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
    hardware_detail: bool = False,
) -> Drawing:
    """Render a fixed vector camera from native solids and hardware paths."""

    points_3d = [vertex for box in boxes for vertex in box.vertices]
    points_3d.extend(vertex for face in faces for vertex in face.vertices)
    points_3d.extend(
        point for bolt in bolts for point in (bolt.center, bolt.start, bolt.end) if point
    )
    if not points_3d:
        raise ValueError("Colored report view requires native physical geometry")
    focus_points = [
        vertex
        for box in boxes
        if "concrete" not in box.identity.lower() and "foundation" not in box.identity.lower()
        for vertex in box.vertices
    ]
    focus_points.extend(vertex for face in faces for vertex in face.vertices)
    focus_points.extend(
        point for bolt in bolts for point in (bolt.center, bolt.start, bolt.end) if point
    )
    if hardware_detail:
        focus_points = [
            point for bolt in bolts for point in (bolt.center, bolt.start, bolt.end) if point
        ]
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
    view_scope = (
        "hardware detail"
        if hardware_detail
        else "connection detail crop"
        if detail_crop
        else "native physical geometry"
    )
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
    tags, _ = component_tags(boxes, faces, bolts)
    for bolt in bolts:
        color = colors.HexColor("#8b4a25" if bolt.role == "anchor" else "#b43e28")
        dark = colors.HexColor("#4c251e")
        radius = min(8.0, max(3.5, (bolt.diameter or 0.0) * scale / 2))
        if bolt.start is not None and bolt.end is not None:
            first, last = paper(bolt.start), paper(bolt.end)
            drawing.add(Line(*first, *last, strokeColor=dark, strokeWidth=radius * 2 + 1.5))
            drawing.add(Line(*first, *last, strokeColor=color, strokeWidth=radius * 2))
            for x, y in (first, last):
                drawing.add(
                    Circle(x, y, radius * 1.35, fillColor=color, strokeColor=dark, strokeWidth=0.8)
                )
            if bolt.washer_diameter is not None:
                x, y = first
                washer_radius = min(12.0, max(radius * 1.4, bolt.washer_diameter * scale / 2))
                drawing.add(
                    Circle(x, y, washer_radius, fillColor=None, strokeColor=dark, strokeWidth=1.3)
                )
        else:
            x, y = paper(bolt.center)
            drawing.add(
                Circle(
                    x, y, radius * 1.5, fillColor=colors.white, strokeColor=dark, strokeWidth=1.0
                )
            )
            drawing.add(Line(x - radius, y, x + radius, y, strokeColor=color, strokeWidth=1.8))
        if hardware_detail:
            x, y = paper(bolt.center)
            drawing.add(
                String(
                    x + radius + 4,
                    y + radius + 2,
                    tags[bolt.identity],
                    fontName="ReportVeraBold",
                    fontSize=8,
                    fillColor=dark,
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
        BoltPoint(
            str(bolt["bolt_id"]),
            (float(bolt["x"]), float(bolt["y"]), 0.0),
            diameter=float(bolt["bolt_diameter"]["value"]) if bolt.get("bolt_diameter") else None,
            row=str(bolt["row_id"]) if bolt.get("row_id") else None,
            line=str(bolt["bolt_line_id"]) if bolt.get("bolt_line_id") else None,
        )
        for bolt in visual["bolts"]
    ]
    return [BoxFigure("Connection plate", vertices)], bolts


def miter_plate_faces(visual: dict[str, Any]) -> list[FaceFigure]:
    """Show the SSMC plate from its native polygon and native thickness interval."""

    boundary = visual["polygon"]["boundary"]
    first, second = visual["plate_y_interval"]
    return [
        FaceFigure(
            "MITER_WEB_PLATE",
            tuple((float(x), float(y), float(z)) for x, z in boundary),
        )
        for y in (first, second)
    ]
