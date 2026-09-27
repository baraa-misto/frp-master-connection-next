"""Read-only projections of canonical backend geometry for REPORT1 figures."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True, slots=True)
class BoxFigure:
    identity: str
    vertices: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class FaceFigure:
    identity: str
    vertices: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class BoltPoint:
    identity: str
    center: tuple[float, float, float]
    start: tuple[float, float, float] | None = None
    end: tuple[float, float, float] | None = None
    diameter: float | None = None
    role: str = "bolt"
    row: str | None = None
    line: str | None = None
    washer_diameter: float | None = None


def _value(value: Any) -> float:  # noqa: ANN401
    if isinstance(value, dict):
        value = value.get("value", value.get("magnitude"))
    if isinstance(value, str) and "/" in value:
        return float(Fraction(value))
    return float(value)


def _xyz(value: dict[str, Any]) -> tuple[float, float, float]:
    return _value(value["x"]), _value(value["y"]), _value(value["z"])


def _lvt(value: dict[str, Any]) -> tuple[float, float, float]:
    return _value(value["l"]), _value(value["v"]), _value(value["t"])


def _box(
    identity: str,
    center: tuple[float, float, float],
    sizes: tuple[float, float, float],
    axes: tuple[tuple[float, float, float], ...],
) -> BoxFigure:
    vertices = tuple(
        (
            center[0] + sum(sign[index] * sizes[index] * axes[index][0] / 2 for index in range(3)),
            center[1] + sum(sign[index] * sizes[index] * axes[index][1] / 2 for index in range(3)),
            center[2] + sum(sign[index] * sizes[index] * axes[index][2] / 2 for index in range(3)),
        )
        for sign in ((a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1))
    )
    return BoxFigure(identity, vertices)


def _from_native_box(value: dict[str, Any]) -> BoxFigure | None:
    identity = str(
        value.get("component_id")
        or value.get("physical_element_id")
        or value.get("id")
        or value.get("role")
        or "Part"
    )
    if "center_l_v_t" in value and "size_l_v_t" in value:
        return _box(
            identity,
            _lvt(value["center_l_v_t"]),
            _lvt(value["size_l_v_t"]),
            ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        )
    if all(key in value for key in ("center", "size_s", "size_p", "size_l", "basis")):
        center = tuple(_value(item) for item in value["center"])
        sizes = tuple(_value(value[key]) for key in ("size_s", "size_p", "size_l"))
        axes = tuple((float(axis[0]), float(axis[1]), float(axis[2])) for axis in value["basis"])
        if len(center) == len(sizes) == len(axes) == 3 and all(len(axis) == 3 for axis in axes):
            return _box(
                identity,
                (center[0], center[1], center[2]),
                (sizes[0], sizes[1], sizes[2]),
                (axes[0], axes[1], axes[2]),
            )
    if value.get("kind") == "BOX" and "parameters" in value:
        params = {item["name"]: float(item["value"]) for item in value["parameters"]}
        ranges = (
            (params["x_start"], params["x_end"]),
            (params["min_y"], params["max_y"]),
            (params["min_z"], params["max_z"]),
        )
        center = _xyz(value["center"])
        axes = (
            _xyz(value["x_axis"]),
            _xyz(value["y_axis"]),
            _xyz(value["z_axis"]),
        )
        sizes = tuple(high - low for low, high in ranges)
        return _box(identity, center, (sizes[0], sizes[1], sizes[2]), (axes[0], axes[1], axes[2]))
    return None


def _from_extrusions(value: dict[str, Any]) -> list[BoxFigure]:
    """Project DCTN's own framed rectangle extrusions as physical boxes."""

    frame = value.get("global_frame")
    extrusions = value.get("extrusions")
    if not isinstance(frame, dict) or not isinstance(extrusions, list):
        return []
    origin = _xyz(frame["origin"])
    axes = (_xyz(frame["x_axis"]), _xyz(frame["y_axis"]), _xyz(frame["z_axis"]))
    source = value.get("source_element", {})
    component = value.get("component", {})
    identity = str(source.get("id") or component.get("entity_id") or "Element")
    found: list[BoxFigure] = []
    for extrusion in extrusions:
        extent = extrusion["extent"]
        rectangle = extrusion["rectangle"]
        ranges = (
            (float(extent["x_start"]), float(extent["x_end"])),
            (float(rectangle["min_y"]), float(rectangle["max_y"])),
            (float(rectangle["min_z"]), float(rectangle["max_z"])),
        )
        local_center = tuple((low + high) / 2 for low, high in ranges)
        center = tuple(
            origin[coordinate]
            + sum(local_center[index] * axes[index][coordinate] for index in range(3))
            for coordinate in range(3)
        )
        sizes = tuple(high - low for low, high in ranges)
        found.append(
            _box(
                identity,
                (center[0], center[1], center[2]),
                (sizes[0], sizes[1], sizes[2]),
                axes,
            )
        )
    return found


def canonical_boxes(visual: dict[str, Any]) -> list[BoxFigure]:
    """Find actual native box primitives without deriving engineering dimensions."""

    found: list[BoxFigure] = []
    seen: set[tuple[str, tuple[tuple[float, float, float], ...]]] = set()

    def visit(value: Any) -> None:  # noqa: ANN401
        if isinstance(value, dict):
            candidate = _from_native_box(value)
            if candidate is not None:
                key = (candidate.identity, candidate.vertices)
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
            for candidate in _from_extrusions(value):
                key = (candidate.identity, candidate.vertices)
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(visual)
    return found


def canonical_faces(visual: dict[str, Any]) -> list[FaceFigure]:
    """Extract SSMC's already-trimmed physical face polygons."""

    found: list[FaceFigure] = []
    members = visual.get("members", [])
    if not isinstance(members, list):
        return found
    for member in members:
        if not isinstance(member, dict):
            continue
        owner = str(member.get("owner", "Member"))
        trimmed = member.get("trimmed", {})
        for solid in trimmed.get("solids", []):
            identity = str(solid.get("physical_element_id") or owner)
            for face in solid.get("faces", []):
                vertices = face.get("vertices", [])
                if len(vertices) >= 3:
                    found.append(FaceFigure(identity, tuple(_xyz(vertex) for vertex in vertices)))
    return found


def canonical_bolt_points(visual: dict[str, Any]) -> list[BoltPoint]:
    """Read native hardware paths and centers without deriving new placements."""

    found: list[BoltPoint] = []
    seen: dict[tuple[str, tuple[float, float, float]], int] = {}

    def coordinate(item: Any) -> float:  # noqa: ANN401
        if isinstance(item, dict) and "numerator" in item and "denominator" in item:
            return float(item["numerator"]) / float(item["denominator"])
        return _value(item)

    def point(item: Any) -> tuple[float, float, float] | None:  # noqa: ANN401
        if isinstance(item, dict):
            if all(axis in item for axis in ("x", "y", "z")):
                return _xyz(item)
            if all(axis in item for axis in ("l", "v", "t")):
                return _lvt(item)
            if all(axis in item for axis in ("s", "t", "longitudinal")):
                return _value(item["s"]), _value(item["t"]), _value(item["longitudinal"])
            if all(axis in item for axis in ("h", "v", "n")):
                return _value(item["h"]), -_value(item["n"]), _value(item["v"])
            if all(axis in item for axis in ("l", "s", "n")):
                return _value(item["l"]), -_value(item["n"]), _value(item["s"])
        if isinstance(item, list) and len(item) == 3:
            return coordinate(item[0]), coordinate(item[1]), coordinate(item[2])
        return None

    def first_point(
        value: dict[str, Any], names: tuple[str, ...]
    ) -> tuple[float, float, float] | None:
        for name in names:
            resolved = point(value.get(name))
            if resolved is not None:
                return resolved
        return None

    def diameter(value: dict[str, Any], role: str) -> float | None:
        for name in ("diameter", "bolt_diameter"):
            if value.get(name) is not None:
                return _value(value[name])
        if role == "anchor":
            geometry = visual.get("external_anchor_geometry")
            if isinstance(geometry, dict) and geometry.get("nominal_diameter") is not None:
                return _value(geometry["nominal_diameter"])
        for name in (
            "common_bolt_diameter",
            "web_bolt_diameter",
            "flange_bolt_diameter",
            "bolt_diameter",
        ):
            if visual.get(name) is not None:
                if name == "web_bolt_diameter" and "FLANGE" in str(value.get("group_id", "")):
                    continue
                return _value(visual[name])
        return None

    def visit(value: Any) -> None:  # noqa: ANN401
        if isinstance(value, dict):
            identity = (
                value.get("anchor_id")
                or value.get("hardware_id")
                or value.get("bolt_location_id")
                or value.get("bolt_id")
            )
            if identity is None and "layer_owners" in value and "plate_midpoint" in value:
                identity = value.get("id")
            start = first_point(
                value,
                (
                    "stack_start",
                    "stack_start_l_v_t",
                    "stack_start_s_t_l",
                    "shank_start_hvn",
                    "shank_start_lsn",
                    "shank_start_s_t_l",
                    "start",
                ),
            )
            end = first_point(
                value,
                (
                    "stack_end",
                    "stack_end_l_v_t",
                    "stack_end_s_t_l",
                    "shank_end_hvn",
                    "shank_end_lsn",
                    "shank_end_s_t_l",
                    "end",
                ),
            )
            resolved = first_point(
                value,
                (
                    "center",
                    "global_center",
                    "center_l_v_t",
                    "coordinate_hvn",
                    "coordinate_lsn",
                    "coordinate_s_t_l",
                    "plate_midpoint",
                ),
            )
            if resolved is None and start is not None and end is not None:
                resolved = (
                    (start[0] + end[0]) / 2,
                    (start[1] + end[1]) / 2,
                    (start[2] + end[2]) / 2,
                )
            if isinstance(identity, str) and resolved is not None:
                role = (
                    "anchor" if value.get("anchor_id") or "ANCHOR" in identity.upper() else "bolt"
                )
                anchor_geometry = visual.get("external_anchor_geometry")
                washer = (
                    _value(anchor_geometry["washer_outside_diameter"])
                    if role == "anchor"
                    and isinstance(anchor_geometry, dict)
                    and anchor_geometry.get("washer_outside_diameter") is not None
                    else None
                )
                marker = BoltPoint(
                    identity,
                    resolved,
                    start,
                    end,
                    diameter(value, role),
                    role,
                    str(value["row_id"]) if value.get("row_id") is not None else None,
                    str(value["bolt_line_id"]) if value.get("bolt_line_id") is not None else None,
                    washer,
                )
                key = (marker.identity, marker.center)
                if key not in seen:
                    seen[key] = len(found)
                    found.append(marker)
                elif marker.start is not None and found[seen[key]].start is None:
                    found[seen[key]] = marker
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(visual)
    return found


def canonical_visual(result: dict[str, Any]) -> dict[str, Any] | None:
    """Select the native design's own preview/visualization, never a browser image."""

    native = result.get("client_design", result.get("native_design", result))
    if not isinstance(native, dict):
        return None
    root = native.get("result", native)
    if not isinstance(root, dict):
        return None
    preview = root.get("preview", root)
    if not isinstance(preview, dict):
        return None
    visual = preview.get("visualization", preview.get("geometry"))
    if visual is None:
        visual = root.get("geometry")
    if visual is None:
        demand = root.get("existing_demand")
        if isinstance(demand, dict):
            visual = demand.get("geometry")
    return visual if isinstance(visual, dict) else None


__all__ = (
    "BoltPoint",
    "BoxFigure",
    "FaceFigure",
    "canonical_bolt_points",
    "canonical_boxes",
    "canonical_faces",
    "canonical_visual",
)
