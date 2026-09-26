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
    """Read physical bolt and shaft centers from native visual records."""

    found: list[BoltPoint] = []
    seen: set[tuple[str, tuple[float, float, float]]] = set()

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
        if isinstance(item, list) and len(item) == 3:
            return coordinate(item[0]), coordinate(item[1]), coordinate(item[2])
        return None

    def visit(value: Any) -> None:  # noqa: ANN401
        if isinstance(value, dict):
            identity = value.get("bolt_location_id") or value.get("bolt_id")
            if identity is None and "layer_owners" in value and "plate_midpoint" in value:
                identity = value.get("id")
            center = (
                value.get("center")
                or value.get("global_center")
                or value.get("center_l_v_t")
                or value.get("plate_midpoint")
            )
            resolved = point(center)
            if resolved is None and "start" in value and "end" in value:
                start, end = point(value["start"]), point(value["end"])
                if start is not None and end is not None:
                    resolved = (
                        (start[0] + end[0]) / 2,
                        (start[1] + end[1]) / 2,
                        (start[2] + end[2]) / 2,
                    )
            if isinstance(identity, str) and resolved is not None:
                marker = BoltPoint(identity, (resolved[0], resolved[1], resolved[2]))
                key = (marker.identity, marker.center)
                if key not in seen:
                    seen.add(key)
                    found.append(marker)
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
