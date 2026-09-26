"""Shared report presentation for native multi-component connection responses.

All numerical text comes from the authenticated response.  The presentation
never invokes a resistance equation or treats a missing value as zero.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.platypus import Flowable

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.reporting.flatten import flatten_unique
from frp_master_connection.reporting.geometry import (
    BoltPoint,
    BoxFigure,
    FaceFigure,
    canonical_bolt_points,
    canonical_boxes,
    canonical_faces,
    canonical_visual,
)
from frp_master_connection.reporting.method_records import EXECUTED_METHODS, executed_records
from frp_master_connection.reporting.pdf import (
    _MULTIROW_METHODS,
    PAPER_SIZES,
    ReportingCoverageError,
    ReportOptions,
    _add_linked_contents,
    _factor_substitution,
    _flatten,
    _font_setup,
    _input_source_rows,
    _NumberedCanvas,
    _paragraph,
    _quantity,
    _ratio_side,
    _ReportDocument,
    _styles,
    _table,
    _text,
)
from frp_master_connection.reporting.section import native_bolt_sections
from frp_master_connection.reporting.snapshot import ReportSnapshot

_FAMILY_MODEL = {
    "tee-connector": (
        "The submitted Tee joins a brace and a support through two bolted interfaces. "
        "Native records show the action assignment at each interface."
    ),
    "clip-angle": (
        "The submitted clip angle joins a member and support through its bolted legs. "
        "Native group records identify the actual force assignment."
    ),
    "paired-clip-angle": (
        "Two submitted clip angles form the paired connection. Native records identify "
        "the common member group and each support-side group."
    ),
    "multi-member-tee": (
        "The submitted Tee connects several member slots. The native slot records identify "
        "each physical interface and its assigned actions."
    ),
    "beam-concrete-paired-angle": (
        "The beam connects through paired angles to a concrete support. Concrete and anchor "
        "authority are separate from the local FRP checks."
    ),
    "direct-side-lap-concrete": (
        "The submitted member laps a concrete support. The native record identifies local FRP "
        "demand and separate external support limits."
    ),
    "column-base-web-angles": (
        "The column web connects through base angles. The native group records state the "
        "assigned web and base demands."
    ),
    "beam-web-splice": (
        "Two beam ends are connected through web splice components. The native records "
        "retain demands on each physical side."
    ),
    "wi-major-axis-moment-splice": (
        "The W/I beam splice carries submitted flange and web actions through distinct "
        "plates and bolt paths."
    ),
    "channel-major-axis-moment-splice": (
        "The channel beam splice assigns submitted actions to its flange and web plate paths, "
        "including the native rational panel method where executed."
    ),
    "wi-beam-concrete-wall-moment": (
        "The W/I beam transfers submitted flange and web actions through connectors toward "
        "the concrete support. Anchor and concrete design remain separate."
    ),
    "wi-beam-frp-support-moment": (
        "The W/I beam transfers submitted flange and web actions through connectors to an "
        "FRP support. Local support and whole-member limits remain explicit."
    ),
    "angle-column-two-leg-moment-base": (
        "The two-leg angle column base model separates column, connector, bolt and "
        "foundation action paths."
    ),
    "wi-rhs-srs-column-moment-base": (
        "The column moment base model separates member profile, connectors, bolts and "
        "foundation action paths."
    ),
    "double-channel-truss-node": (
        "The double-channel node carries submitted member actions through named channel and "
        "bolt-group paths. Transverse authority is conditional."
    ),
    "stair-stringer-miter": (
        "The stair-stringer miter model retains serial member-cut actions, single-lap "
        "interfaces and their source-limited checks."
    ),
}


def _project(vertex: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = vertex
    if view == "isometric":
        return x - 0.55 * y, z + 0.35 * (x + y)
    if view == "elevation":
        return x, z
    return x, y


def _native_box_unit(visual: dict[str, Any] | None) -> str | None:
    """Use a unit only when every native box coordinate declares the same one."""

    if visual is None:
        return None
    units: set[str] = set()

    def visit(value: Any) -> None:  # noqa: ANN401
        if isinstance(value, dict):
            if "center_l_v_t" in value and "size_l_v_t" in value:
                for key in ("center_l_v_t", "size_l_v_t"):
                    coordinates = value[key]
                    if isinstance(coordinates, dict):
                        for axis in coordinates.values():
                            if isinstance(axis, dict) and isinstance(axis.get("unit"), str):
                                units.add(axis["unit"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(visual)
    if len(units) > 1:
        raise ReportingCoverageError("Canonical box coordinates use mixed length units")
    return next(iter(units)) if units else None


def _box_figure(boxes: list[BoxFigure], bolts: list[BoltPoint], view: str, unit: str) -> Drawing:
    projected = [[_project(vertex, view) for vertex in box.vertices] for box in boxes]
    bolt_projected = [_project(bolt.center, view) for bolt in bolts]
    all_points = [point for vertices in projected for point in vertices] + bolt_projected
    x0, x1 = min(p[0] for p in all_points), max(p[0] for p in all_points)
    y0, y1 = min(p[1] for p in all_points), max(p[1] for p in all_points)
    width, height = 480.0, 255.0
    scale = min((width - 190) / max(x1 - x0, 0.001), (height - 76) / max(y1 - y0, 0.001))

    def paper(point: tuple[float, float]) -> tuple[float, float]:
        return 35 + (point[0] - x0) * scale, 42 + (point[1] - y0) * scale

    drawing = Drawing(width, height)
    edges = (
        (0, 1),
        (0, 2),
        (0, 4),
        (3, 1),
        (3, 2),
        (3, 7),
        (5, 1),
        (5, 4),
        (5, 7),
        (6, 2),
        (6, 4),
        (6, 7),
    )
    identity_counts = Counter(box.identity for box in boxes)
    box_labels: set[str] = set()
    legend_index = 0
    for box, vertices in zip(boxes, projected, strict=True):
        points = [paper(point) for point in vertices]
        for a, b in edges:
            drawing.add(
                Line(
                    *points[a], *points[b], strokeColor=colors.HexColor("#526675"), strokeWidth=0.55
                )
            )
        cx = sum(point[0] for point in points) / 8
        cy = sum(point[1] for point in points) / 8
        if box.identity not in box_labels and legend_index < 12:
            label_y = height - 33 - legend_index * 12
            drawing.add(
                Line(cx, cy, 336, label_y, strokeColor=colors.HexColor("#a2adb2"), strokeWidth=0.3)
            )
            drawing.add(
                String(
                    339,
                    label_y,
                    f"{box.identity[:18]} ({identity_counts[box.identity]})",
                    fontName="ReportVera",
                    fontSize=9,
                    fillColor=colors.HexColor("#203846"),
                )
            )
            box_labels.add(box.identity)
            legend_index += 1
    for index, (bolt, projected_center) in enumerate(zip(bolts, bolt_projected, strict=True)):
        center = paper(projected_center)
        drawing.add(
            Circle(
                center[0], center[1], 2.2, strokeColor=colors.HexColor("#9b4435"), fillColor=None
            )
        )
        if index < 4 and legend_index < 16:
            label_y = height - 33 - legend_index * 12
            drawing.add(
                Line(
                    center[0],
                    center[1],
                    336,
                    label_y,
                    strokeColor=colors.HexColor("#b57369"),
                    strokeWidth=0.3,
                )
            )
            drawing.add(
                String(
                    339,
                    label_y,
                    f"B{index + 1}. {bolt.identity[:17]}",
                    fontName="ReportVera",
                    fontSize=9,
                    fillColor=colors.HexColor("#7d3a2d"),
                )
            )
            legend_index += 1
    if len(boxes) + len(bolts) > legend_index:
        drawing.add(
            String(
                339,
                20,
                f"All {len(boxes)} parts and {len(bolts)} bolts in schedule",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    if view != "isometric":
        left, right = paper((x0, y0))[0], paper((x1, y0))[0]
        bottom, top = paper((x0, y0))[1], paper((x0, y1))[1]
        drawing.add(Line(left, 20, right, 20, strokeColor=colors.black, strokeWidth=0.7))
        drawing.add(Line(18, bottom, 18, top, strokeColor=colors.black, strokeWidth=0.7))
        for x in (left, right):
            drawing.add(Line(x, 16, x, 25, strokeColor=colors.black, strokeWidth=0.7))
        for y in (bottom, top):
            drawing.add(Line(14, y, 23, y, strokeColor=colors.black, strokeWidth=0.7))
        drawing.add(
            String(
                (left + right) / 2,
                7,
                f"{x1 - x0:.5g} {unit}",
                textAnchor="middle",
                fontName="ReportVera",
                fontSize=9,
            )
        )
        drawing.add(
            String(
                2,
                min(top + 8, height - 22),
                f"{y1 - y0:.5g} {unit}",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    drawing.add(
        String(
            8,
            height - 12,
            f"Canonical {view}; not to scale",
            fontName="ReportVeraBold",
            fontSize=9,
        )
    )
    return drawing


def _face_figure(faces: list[FaceFigure], bolts: list[BoltPoint], view: str, unit: str) -> Drawing:
    projected = [[_project(vertex, view) for vertex in face.vertices] for face in faces]
    bolt_projected = [_project(bolt.center, view) for bolt in bolts]
    all_points = [point for vertices in projected for point in vertices] + bolt_projected
    x0, x1 = min(p[0] for p in all_points), max(p[0] for p in all_points)
    y0, y1 = min(p[1] for p in all_points), max(p[1] for p in all_points)
    width, height = 480.0, 255.0
    scale = min((width - 190) / max(x1 - x0, 0.001), (height - 76) / max(y1 - y0, 0.001))

    def paper(point: tuple[float, float]) -> tuple[float, float]:
        return 35 + (point[0] - x0) * scale, 42 + (point[1] - y0) * scale

    drawing = Drawing(width, height)
    seen_edges: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    labelled: set[str] = set()
    for face, vertices in zip(faces, projected, strict=True):
        points = [paper(point) for point in vertices]
        for first, second in zip(points, points[1:] + points[:1], strict=True):
            edge = (first, second) if first <= second else (second, first)
            if edge not in seen_edges:
                seen_edges.add(edge)
                drawing.add(
                    Line(*first, *second, strokeColor=colors.HexColor("#526675"), strokeWidth=0.6)
                )
        if face.identity not in labelled:
            labelled.add(face.identity)
            drawing.add(
                String(
                    points[0][0] + 2,
                    points[0][1] + 2,
                    face.identity[:20],
                    fontName="ReportVera",
                    fontSize=9,
                )
            )
    for index, (bolt, projected_center) in enumerate(zip(bolts, bolt_projected, strict=True)):
        center = paper(projected_center)
        drawing.add(
            Circle(
                center[0], center[1], 2.2, strokeColor=colors.HexColor("#9b4435"), fillColor=None
            )
        )
        if index < 16:
            label_y = height - 33 - index * 12
            drawing.add(
                Line(
                    center[0],
                    center[1],
                    336,
                    label_y,
                    strokeColor=colors.HexColor("#b57369"),
                    strokeWidth=0.3,
                )
            )
            drawing.add(
                String(
                    339,
                    label_y,
                    f"B{index + 1}. {bolt.identity[:17]}",
                    fontName="ReportVera",
                    fontSize=9,
                    fillColor=colors.HexColor("#7d3a2d"),
                )
            )
    if view != "isometric":
        left, right = paper((x0, y0))[0], paper((x1, y0))[0]
        drawing.add(Line(left, 20, right, 20, strokeColor=colors.black, strokeWidth=0.7))
        for x in (left, right):
            drawing.add(Line(x, 16, x, 25, strokeColor=colors.black, strokeWidth=0.7))
        drawing.add(
            String(
                (left + right) / 2,
                7,
                f"{x1 - x0:.5g} {unit}",
                textAnchor="middle",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    drawing.add(
        String(
            8,
            height - 12,
            f"Canonical {view}; not to scale",
            fontName="ReportVeraBold",
            fontSize=9,
        )
    )
    return drawing


def _key_summary(value: dict[str, Any]) -> list[tuple[str, str]]:
    selected: list[tuple[str, str]] = []
    for key, item in value.items():
        if isinstance(item, (dict, list)):
            continue
        if any(
            part in key
            for part in (
                "status",
                "disposition",
                "governing",
                "qualified",
                "resistance_evaluated",
                "ready",
                "fingerprint",
            )
        ):
            selected.append((key.replace("_", " ").title(), _text(item)))
    return selected


def _method_inventory(value: Any) -> tuple[Counter[str], list[tuple[str, str]]]:  # noqa: ANN401
    methods: Counter[str] = Counter()
    records: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def walk(item: Any, path: str) -> None:  # noqa: ANN401
        if isinstance(item, dict):
            method = item.get("equation_method") or item.get("method")
            if isinstance(method, str):
                identity = str(
                    item.get("result_id")
                    or item.get("check_id")
                    or item.get("component_id")
                    or item.get("bolt_id")
                    or path
                )
                key = (method, identity)
                if key not in seen:
                    seen.add(key)
                    methods[method] += 1
                    status = (
                        item.get("availability") or item.get("status") or "Native method record"
                    )
                    records.append((f"{method} / {identity}", f"{status} | {path}"))
            for name, child in item.items():
                if name not in {"visualization", "geometry"}:
                    walk(child, f"{path}.{name}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")

    walk(value, "result")
    return methods, records


def _native_equation_examples(value: object) -> dict[str, tuple[str, dict[str, Any]]]:
    """Select one executed native trace per equation method, without recalculating it."""

    examples: dict[str, tuple[str, dict[str, Any]]] = {}

    def walk(item: object, path: str) -> None:
        if isinstance(item, dict):
            method = item.get("equation_method")
            if (
                isinstance(method, str)
                and item.get("availability") == "CALCULATED"
                and method not in examples
            ):
                examples[method] = (path, item)
            for name, child in item.items():
                if name not in {"visualization", "geometry"}:
                    walk(child, f"{path}.{name}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")

    walk(value, "result")
    return examples


def _bearing_substitution(
    request: dict[str, Any], result: dict[str, Any], check: dict[str, Any]
) -> str | None:
    """Join a native bearing trace to its identified layer and physical bolt."""

    trace = check.get("equation_trace")
    if not isinstance(trace, dict):
        return None
    bearing = trace.get("bearing_property")
    if not isinstance(bearing, dict):
        return None
    adjusted = bearing.get("adjusted_property")
    if not isinstance(adjusted, dict):
        return None
    layer_id, bolt_id = check.get("layer_id"), check.get("bolt_id")
    if not isinstance(layer_id, str) or not isinstance(bolt_id, str):
        return None
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    thicknesses: set[Decimal] = set()
    canonical_thicknesses: set[str] = set()
    diameters: set[Decimal] = set()
    diameter_values: set[str] = set()

    def native_length_mm(value: object) -> Decimal | None:
        if not isinstance(value, dict):
            return None
        canonical: Decimal | None = None
        if "canonical_value" in value or "canonical_unit" in value:
            if value.get("canonical_unit") != "mm":
                return None
            try:
                canonical = Decimal(str(value["canonical_value"]))
            except KeyError, InvalidOperation, TypeError:
                return None
        if "value" not in value and "unit" not in value:
            return canonical
        try:
            converted = (
                PhysicalQuantity.of(str(value["value"]), Unit(str(value["unit"])))
                .to(Unit.MM)
                .magnitude
            )
        except KeyError, TypeError, ValueError:
            return None
        return converted if canonical is None or canonical == converted else None

    def walk(item: object) -> None:
        if isinstance(item, dict):
            if item.get("layer_id") == layer_id and "thickness" in item:
                thickness = native_length_mm(item["thickness"])
                if thickness is not None:
                    thicknesses.add(thickness)
                    if (
                        isinstance(item["thickness"], dict)
                        and item["thickness"].get("canonical_unit") == "mm"
                    ):
                        canonical_thicknesses.add(str(item["thickness"]["canonical_value"]))
            diameter = item.get("bolt_diameter")
            if isinstance(diameter, dict):
                diameter_mm = native_length_mm(diameter)
                if diameter_mm is not None:
                    diameters.add(diameter_mm)
                    diameter_values.add(str(diameter.get("value")))
            visual = item.get("visualization")
            if isinstance(visual, dict):
                layers = visual.get("layers")
                bolts = visual.get("physical_bolts")
                if isinstance(layers, list) and isinstance(bolts, list):
                    for layer in layers:
                        for bolt in bolts:
                            if (
                                isinstance(layer, dict)
                                and isinstance(bolt, dict)
                                and layer.get("layer_id") == layer_id
                                and bolt.get("bolt_id") == bolt_id
                            ):
                                matches.append((layer, bolt))
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(result)
    walk(request)
    for layer, _ in matches:
        thickness = native_length_mm(layer.get("thickness"))
        if thickness is not None:
            thicknesses.add(thickness)
            if (
                isinstance(layer.get("thickness"), dict)
                and layer["thickness"].get("canonical_unit") == "mm"
            ):
                canonical_thicknesses.add(str(layer["thickness"]["canonical_value"]))
    direct_diameter = request.get("bolt_diameter")
    if isinstance(direct_diameter, dict) and native_length_mm(direct_diameter) is None:
        return None
    if len(thicknesses) != 1 or len(diameters) != 1:
        return None
    t, diameter_mm = next(iter(thicknesses)), next(iter(diameters))
    t_display = (
        min(canonical_thicknesses, key=lambda value: (len(value), value))
        if canonical_thicknesses
        else str(t)
    )
    if matches:
        visual_thicknesses = {native_length_mm(layer.get("thickness")) for layer, _ in matches}
        display_diameters = {
            str(bolt["display"]["bolt_diameter"])
            for _, bolt in matches
            if isinstance(bolt.get("display"), dict) and "bolt_diameter" in bolt["display"]
        }
        if visual_thicknesses != {t} or len(display_diameters) != 1:
            return None
        if not display_diameters <= diameter_values:
            return None
    if "canonical_unit" in adjusted or "canonical_value" in adjusted:
        if adjusted.get("canonical_unit") != "MPa":
            return None
        f_br = adjusted.get("canonical_value")
    elif adjusted.get("unit") == "MPa":
        f_br = adjusted.get("value")
    else:
        return None
    if f_br is None:
        return None
    nominal = check.get("equation_nominal_resistance")
    if not isinstance(nominal, dict):
        return None
    return (
        f"R_n = t({t_display} mm) x d({diameter_mm} mm) x "
        f"F_br,adjusted({f_br} MPa) x C_thread({trace.get('thread_factor')}) "
        f"= native R_n {_quantity(nominal)}"
    )


def _eccentric_demand_example(value: object) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
    """Find one native rational bolt-group scenario and its parent frame record."""

    def walk(item: object, path: str) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
        if isinstance(item, dict):
            scenarios = item.get("scenarios")
            if isinstance(scenarios, list) and "polar_coordinate_sum" in item:
                for scenario in scenarios:
                    if (
                        isinstance(scenario, dict)
                        and scenario.get("method") == "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY"
                        and scenario.get("availability") == "CALCULATED"
                        and isinstance(scenario.get("per_bolt"), list)
                        and scenario["per_bolt"]
                    ):
                        return path, item, scenario
            for name, child in item.items():
                if name not in {"geometry", "visualization"}:
                    found = walk(child, f"{path}.{name}")
                    if found is not None:
                        return found
        elif isinstance(item, list):
            for index, child in enumerate(item):
                found = walk(child, f"{path}[{index}]")
                if found is not None:
                    return found
        return None

    return walk(value, "result")


def _check_summary(value: object) -> list[tuple[str, str]]:
    checks: dict[str, dict[str, Any]] = {}

    def visit(item: object, path: str) -> None:
        if isinstance(item, dict):
            if "availability" in item or "utilization" in item:
                identity = str(item.get("result_id") or item.get("check_id") or path)
                previous = checks.get(identity)
                if previous is None or (
                    previous.get("utilization") is None and item.get("utilization") is not None
                ):
                    checks[identity] = item
            for name, child in item.items():
                if name not in {"visualization", "geometry"}:
                    visit(child, f"{path}.{name}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "result")
    ratios: list[tuple[Decimal, str]] = []
    unevaluated = 0
    for identity, check in checks.items():
        availability = check.get("availability")
        if availability is not None and availability != "CALCULATED":
            unevaluated += 1
        utilization = check.get("utilization")
        if utilization is not None:
            try:
                ratio = Decimal(str(utilization))
                if ratio.is_finite():
                    ratios.append((ratio, identity))
            except InvalidOperation:
                continue
    governing = max(ratios, default=None)
    return [
        ("Native check records", str(len(checks))),
        ("Checks without evaluated resistance", str(unevaluated)),
        (
            "Highest native numerical ratio",
            (
                f"{governing[0]:.6g} ({_ratio_side(governing[0])}; exact native U in results)"
                if governing is not None
                else "None; no native numerical ratio"
            ),
        ),
        ("Governing numerical check", governing[1] if governing is not None else "None"),
    ]


def _check_matrix(value: object) -> list[tuple[str, str]]:
    """Index every distinct native check without changing its scope or outcome."""

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()

    def concise_quantity(item: object) -> str:
        if not isinstance(item, dict):
            return _quantity(item)
        try:
            magnitude = Decimal(str(item["value"]))
            if not magnitude.is_finite():
                return _quantity(item)
            return f"{magnitude:.6g} {_text(item.get('unit'))}"
        except KeyError, InvalidOperation:
            return _quantity(item)

    def concise_ratio(item: object) -> str:
        if item is None:
            return "Not evaluated"
        try:
            ratio = Decimal(str(item))
            if ratio.is_finite():
                return f"{ratio:.6g} ({_ratio_side(ratio)})"
        except InvalidOperation:
            pass
        return _text(item)

    def visit(item: object, path: str) -> None:
        if isinstance(item, dict):
            identity = item.get("result_id") or item.get("check_id")
            if (
                isinstance(identity, str)
                and ("availability" in item or "utilization" in item or "status" in item)
                and not isinstance(item.get("resistance_result"), dict)
            ):
                fingerprint = hashlib.sha256(
                    json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    plan = item.get("plan")
                    method = (
                        item.get("equation_method") or item.get("limit_state") or item.get("family")
                    )
                    if method is None and isinstance(plan, dict):
                        method = plan.get("limit_state")
                    owner = item.get("layer_id") or item.get("component_id")
                    location = item.get("bolt_id") or item.get("path_id") or item.get("row_id")
                    resistance = item.get("design_resistance") or item.get("resistance")
                    summary = [
                        f"{_text(method)}; {_text(item.get('availability') or item.get('status'))}"
                    ]
                    if owner is not None:
                        summary.append(f"owner {_text(owner)}")
                    if location is not None:
                        summary.append(f"bolt/path {_text(location)}")
                    case = item.get("case_id") or item.get("load_case_id")
                    if case is not None:
                        summary.append(f"case {_text(case)}")
                    if item.get("demand") is not None:
                        summary.append(f"demand {concise_quantity(item['demand'])}")
                    if resistance is not None:
                        summary.append(f"R_d {concise_quantity(resistance)}")
                    summary.append(f"U {concise_ratio(item.get('utilization'))}")
                    if item.get("numerical_comparison") is not None:
                        summary.append(f"outcome {_text(item['numerical_comparison'])}")
                    summary.append(f"exact native path {path}")
                    rows.append(
                        (
                            identity,
                            "; ".join(summary),
                        )
                    )
            for name, child in item.items():
                if name not in {"visualization", "geometry"}:
                    visit(child, f"{path}.{name}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "result")
    return rows


def _schedules(
    story: list[Flowable], title: str, rows: list[tuple[str, str]], styles: dict[str, Any]
) -> None:
    story.append(_paragraph(title, styles["heading"]))
    if not rows:
        story.append(_paragraph("No native records in this section.", styles["body"]))
        return
    expanded: list[tuple[str, str]] = []
    for path, value in rows:
        if len(value) <= 480:
            expanded.append((path, value))
        else:
            chunks = [value[index : index + 480] for index in range(0, len(value), 480)]
            expanded.extend(
                (f"{path} [part {index + 1}/{len(chunks)}]", chunk)
                for index, chunk in enumerate(chunks)
            )
    for offset in range(0, len(expanded), 80):
        story.append(_table(expanded[offset : offset + 80], styles))


def _method_example_data(method: str, record: dict[str, Any]) -> dict[str, Any]:
    """Bound a worked example while retaining all other native records later."""

    if method == "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1":
        actions = record.get("action_reaction")
        cuts = record.get("cuts")
        if not isinstance(actions, list) or not actions or not isinstance(cuts, dict):
            raise ReportingCoverageError("SSMC analytical action/cut trace is missing")
        candidates = cuts.get("cuts")
        return {
            "applicability_status": record.get("applicability_status"),
            "first_action_reaction": actions[0],
            "first_member_cut_demand": (record.get("member_cut_demands") or [None])[0],
            "first_actual_polygon_cut": candidates[0]
            if isinstance(candidates, list) and candidates
            else None,
            "cut_coverage_status": cuts.get("status"),
            "whole_connection_status": record.get("whole_connection_status"),
        }
    if method in {
        "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1",
        "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1",
    }:
        components = record.get("components")
        if not isinstance(components, list) or not components:
            raise ReportingCoverageError("Native region decomposition has no components")
        return {
            "calculation_input": record.get("calculation_input"),
            "section_properties": record.get("section_properties"),
            "shear_center": record.get("shear_center"),
            "first_component": components[0],
            "equilibrium": record.get("equilibrium"),
            "couple_diagnostics": record.get("couple_diagnostics"),
        }
    if method == "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1":
        return {
            "request": record.get("request"),
            "heel": record.get("heel"),
            "connector_on_support": record.get("connector_on_support"),
            "support_on_connector": record.get("support_on_connector"),
            "equilibrium": record.get("equilibrium"),
        }
    if method == "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1":
        solution = record.get("solution")
        if not isinstance(solution, dict) or not isinstance(solution.get("bolts"), list):
            raise ReportingCoverageError("Exact in-plane wrench has no native bolt solution")
        return {
            "status": record.get("status"),
            "assumption": record.get("assumption"),
            "reference": solution.get("reference"),
            "force": solution.get("force"),
            "reference_moment": solution.get("reference_moment"),
            "centroid": solution.get("centroid"),
            "polar_sum": solution.get("polar_sum"),
            "centroid_moment": solution.get("centroid_moment"),
            "first_bolt": solution["bolts"][0],
            "proof": solution.get("proof"),
        }
    if method == "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1":
        sections = record.get("critical_sections")
        if not isinstance(sections, list) or not sections:
            raise ReportingCoverageError("Executed web-body interaction has no fiber trace")
        return {
            key: value
            for key, value in record.items()
            if key
            not in {
                "critical_sections",
                "tension_strength",
                "compression_strength",
                "shear_strength",
            }
        } | {"first_critical_section": sections[0]}
    if method == "DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1":
        rows, shafts = record.get("rows"), record.get("shafts")
        if not isinstance(rows, list) or not rows or not isinstance(shafts, list) or not shafts:
            raise ReportingCoverageError("Qualified DCTN response has no row or shaft trace")
        return {
            "status": record.get("status"),
            "symmetry": record.get("symmetry"),
            "first_row": rows[0],
            "first_shaft": shafts[0],
        }
    return record


def _method_substitution_rows(method: str, record: dict[str, Any]) -> list[tuple[str, str]]:
    """Join named native factors to the reviewed expression without recomputation."""

    if method == "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION":
        property_record = record.get("adjusted_property")
        adjusted = (
            property_record.get("adjusted_property") if isinstance(property_record, dict) else None
        )
        time = record.get("time_effect_factor")
        return [
            ("Native A_net,eff", _quantity(record.get("effective_net_area_per_unit_width"))),
            ("Native adjusted F_t,L", _quantity(adjusted)),
            ("Native R_n", _quantity(record.get("nominal_strength"))),
            ("Native phi", _text(record.get("resistance_factor"))),
            ("Native lambda", _text(time.get("value") if isinstance(time, dict) else time)),
            ("Native R_d", _quantity(record.get("design_strength"))),
        ]
    if method == "ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1":
        factors = record.get("factors")
        traces = factors.get("property_traces") if isinstance(factors, dict) else None
        trace = traces[0] if isinstance(traces, list) and traces else None
        return [
            ("Native L_eff", _quantity(record.get("length"))),
            (
                "Native adjusted F_sh,LT",
                _quantity(trace.get("adjusted_property") if isinstance(trace, dict) else None),
            ),
            (
                "Native R_n",
                _quantity(factors.get("nominal_resistance") if isinstance(factors, dict) else None),
            ),
            ("Native phi", _text(factors.get("phi") if isinstance(factors, dict) else None)),
            (
                "Native R_d",
                _quantity(factors.get("design_resistance") if isinstance(factors, dict) else None),
            ),
            ("Native demand", _quantity(record.get("demand"))),
            ("Native U", _text(record.get("utilization"))),
        ]
    if method == "NATIVE_ASCE_8_5":
        trace = record.get("native_trace")
        factors = trace.get("factor_trace") if isinstance(trace, dict) else None
        return [
            ("Native demand", _quantity(record.get("demand"))),
            (
                "Native nominal",
                _quantity(factors.get("nominal_resistance") if isinstance(factors, dict) else None),
            ),
            ("Native phi", _text(factors.get("phi") if isinstance(factors, dict) else None)),
            ("Native C_lap", _text(factors.get("c_lap") if isinstance(factors, dict) else None)),
            (
                "Native C_delta",
                _text(factors.get("c_delta") if isinstance(factors, dict) else None),
            ),
            (
                "Native lambda",
                _text(factors.get("lambda_factor") if isinstance(factors, dict) else None),
            ),
            ("Native R_d", _quantity(record.get("resistance"))),
            ("Native outcome", _text(record.get("status"))),
        ]
    return []


def render_generic_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    """Present the complete native record with a navigable summary and figures."""

    _font_setup()
    styles = _styles()
    native = snapshot.result.get(
        "client_design", snapshot.result.get("native_design", snapshot.result)
    )
    if not isinstance(native, dict):
        raise ReportingCoverageError("Native report response has no dictionary result")
    result = native.get("result", native)
    if not isinstance(result, dict):
        raise ReportingCoverageError("Native report response has no result record")
    status = _text(
        snapshot.result.get("whole_connection_status")
        or snapshot.result.get("assembly_status")
        or snapshot.result.get("overall_status")
        or snapshot.result.get("status")
        or result.get("whole_connection_status")
        or result.get("assembly_status")
        or result.get("design_status")
        or result.get("status")
    )
    visual = canonical_visual(native)
    boxes = canonical_boxes(visual) if visual is not None else []
    bolts = canonical_bolt_points(visual) if visual is not None else []
    faces = canonical_faces(visual) if visual is not None and not boxes else []
    unit = _text(
        snapshot.request.get("length_unit")
        or snapshot.request.get("source_length_unit")
        or (visual or {}).get("length_unit")
        or (visual or {}).get("source_length_unit")
        or _native_box_unit(visual)
        or "native length units"
    )
    methods, method_records = _method_inventory(result)
    title = (
        "Submitted inputs - design not evaluated"
        if snapshot.result.get("status") == "INPUT_NOT_EVALUATED"
        else "Inputs and model report - design not evaluated"
        if snapshot.kind == "input_only"
        else "Connection calculation report"
    )
    story: list[Flowable] = [
        _paragraph(title, styles["title"]),
        _paragraph(f"{snapshot.family} | Native status: {status}", styles["body"]),
        _table(
            [
                ("Project", options.project_name),
                ("Project number", options.project_number),
                ("Connection ID", options.connection_id),
                ("Revision", options.revision),
                ("Native status", status),
                ("Connector body material", _text(snapshot.result.get("connector_body_material"))),
                ("Report kind", snapshot.kind),
                ("Snapshot", snapshot.digest[:16]),
                *_check_summary(result),
            ],
            styles,
        ),
    ]
    story.append(
        _paragraph(
            _FAMILY_MODEL.get(
                snapshot.family, "The native model and assigned actions are listed below."
            ),
            styles["body"],
        )
    )
    if snapshot.kind == "input_only":
        story.append(
            _paragraph(
                "No design resistance or utilization was evaluated for this input-only report. "
                + (
                    "The following values are an unvalidated user draft captured by the server; "
                    "they are not native calculation results."
                    if snapshot.result.get("status") == "INPUT_NOT_EVALUATED"
                    else "Validation issues are recorded in the native response below."
                ),
                styles["body"],
            )
        )
    elif status == "FAIL" and snapshot.result.get("blockers"):
        story.append(
            _paragraph(
                "A supported native check failed. Other source or qualification blockers "
                "remain unresolved; see the complete blocker schedule.",
                styles["body"],
            )
        )
    elif status not in {"PASS", "FAIL"}:
        story.append(
            _paragraph(
                "Incomplete design - engineering review or source evidence "
                "may be required. Numerical diagnostics retain their native "
                "qualification status.",
                styles["body"],
            )
        )
    if boxes:
        story.append(_box_figure(boxes, bolts, "isometric", unit))
    elif faces:
        story.append(_face_figure(faces, bolts, "isometric", unit))
    draft_only = snapshot.result.get("status") == "INPUT_NOT_EVALUATED"
    story.append(
        _paragraph(
            "Submitted input scope" if draft_only else "Scope and connection model",
            styles["heading"],
        )
    )
    story.append(
        _paragraph(
            "This record preserves only the submitted draft. Geometry, load assignment, "
            "material applicability and all engineering checks await a native calculation."
            if draft_only
            else "This record covers the local connection and the load cases in the "
            "identified backend calculation. It does not establish whole-member "
            "or global-structure qualification. Source and method limitations are "
            "listed in the native record below.",
            styles["body"],
        )
    )
    if boxes:
        for view in ("elevation", "plan"):
            story.append(_box_figure(boxes, bolts, view, unit))
    elif faces:
        for view in ("elevation", "plan"):
            story.append(_face_figure(faces, bolts, view, unit))
    else:
        story.append(
            _paragraph(
                "No native geometry was calculated for this input draft."
                if draft_only
                else "No box-based canonical projection is available for this native "
                "geometry. Exact geometry coordinates follow in the schedule.",
                styles["body"],
            )
        )
    sections = native_bolt_sections(result)
    if sections:
        story.append(_paragraph("Bolt-axis and physical stack details", styles["heading"]))
        for bolt_id, drawing in sections:
            story.append(_paragraph(f"Native representative bolt {bolt_id}", styles["small"]))
            story.append(drawing)
    _schedules(
        story,
        "Native outcome and completeness",
        [
            ("Location", options.location),
            ("Prepared by", options.prepared_by),
            ("Checked by", options.checked_by),
            ("Distinct native methods", str(len(methods))),
            *_key_summary(snapshot.result),
            *_key_summary(result),
        ],
        styles,
    )
    _schedules(
        story,
        "Submitted engineering inputs",
        [
            *_input_source_rows(snapshot),
            *flatten_unique(
                "request",
                snapshot.request,
                minimum_alias_leaves=1,
                display_units=options.display_units,
            ),
        ],
        styles,
    )
    if visual is not None:
        story.append(
            _paragraph("Canonical geometry and resolved preview records", styles["heading"])
        )
        story.append(
            _paragraph(
                f"The figures project {len(boxes)} native boxes, {len(faces)} faces and "
                f"{len(bolts)} identified bolt centers. The complete native results appendix "
                "retains every source coordinate, dimension, placement and load-provenance "
                "path, including nested preview and visualization records.",
                styles["body"],
            )
        )
    _schedules(story, "Method and check inventory", method_records, styles)
    story.append(
        _paragraph(
            "The matrix rounds values for navigation and labels the side of the exact 1.0 "
            "limit. The listed native path leads to the full-precision demand, resistance, "
            "factors and outcome in the complete schedule.",
            styles["small"],
        )
    )
    _schedules(story, "Native check and outcome matrix", _check_matrix(result), styles)
    eccentric = _eccentric_demand_example(result)
    if eccentric is not None:
        path, group, scenario = eccentric
        bolt = scenario["per_bolt"][0]
        moment_force = bolt.get("moment_force")
        moment_u = (
            _quantity(moment_force.get("u")) if isinstance(moment_force, dict) else "Not supplied"
        )
        moment_v = (
            _quantity(moment_force.get("v")) if isinstance(moment_force, dict) else "Not supplied"
        )
        residual = _quantity(scenario.get("residual_moment"))
        polar = _quantity(group.get("polar_coordinate_sum"))
        centered_x = _quantity(bolt.get("centered_x"))
        centered_y = _quantity(bolt.get("centered_y"))
        story.append(
            _paragraph("Worked native eccentric bolt-group load assignment", styles["heading"])
        )
        story.append(
            _paragraph(
                "The rational equal-stiffness elastic method projects the applied force into "
                "the group plane. It assigns each bolt its declared direct share, then distributes "
                "only the residual centroidal moment by the coordinate polar sum. The native "
                "equilibrium result and all bolt vectors remain in the complete schedule.",
                styles["body"],
            )
        )
        _schedules(
            story,
            "Method identity and moment balance",
            [
                ("Native group record", path),
                ("Scenario", _text(scenario.get("scenario_id"))),
                ("Method", _text(scenario.get("method"))),
                ("Expression", "M_ext=(x_ref-x_c)F_v-(y_ref-y_c)F_u"),
                ("Native external moment", _quantity(scenario.get("external_moment"))),
                ("Expression", "M_direct=sum[(x_i-x_c)F_v,d,i-(y_i-y_c)F_u,d,i]"),
                ("Native direct moment", _quantity(scenario.get("direct_distribution_moment"))),
                ("Expression", "M_res=M_ext-M_direct"),
                ("Native residual moment", _quantity(scenario.get("residual_moment"))),
                ("J=sum[(x_i-x_c)^2+(y_i-y_c)^2]", _quantity(group.get("polar_coordinate_sum"))),
                ("Force reference", _text(group.get("force_reference_point"))),
                ("Projected force", _text(group.get("projected_force"))),
                ("Group centroid", _text(group.get("geometric_bolt_centroid"))),
                ("Equilibrium", _text(scenario.get("equilibrium"))),
            ],
            styles,
        )
        _schedules(
            story,
            "One physical bolt substitution from that scenario",
            [
                ("Bolt", _text(bolt.get("bolt_id"))),
                ("Direct share", _text(bolt.get("direct_share"))),
                ("Centered x", _quantity(bolt.get("centered_x"))),
                ("Centered y", _quantity(bolt.get("centered_y"))),
                ("Expression", "F_m,u=-(M_res/J)(y_i-y_c); F_m,v=(M_res/J)(x_i-x_c)"),
                ("Native substitution", f"F_m,u=-({residual}/{polar})({centered_y})={moment_u}"),
                ("Native substitution", f"F_m,v=({residual}/{polar})({centered_x})={moment_v}"),
                ("Native direct force", _text(bolt.get("direct_force"))),
                ("Native moment force", _text(bolt.get("moment_force"))),
                ("Expression", "F_total=F_direct+F_m; |F_total|=sqrt(F_u^2+F_v^2)"),
                ("Native total force", _text(bolt.get("total_force"))),
                ("Native magnitude", _quantity(bolt.get("total_force_magnitude"))),
            ],
            styles,
        )
    if snapshot.family == "double-channel-truss-node":
        node_preview = result.get("preview")
        node_demand = node_preview.get("demand") if isinstance(node_preview, dict) else None
        if isinstance(node_demand, dict) and node_demand.get("status") == "CALCULATED":
            members = node_demand.get("members")
            if not isinstance(members, list) or not members or not isinstance(members[0], dict):
                raise ReportingCoverageError("Executed DCTN-3B demand lacks its member trace")
            story.append(_paragraph("DCTN-3B exact member action transport", styles["heading"]))
            story.append(
                _paragraph(
                    "The native three-component P/Qp/Qq action is resolved on each member's "
                    "actual local axes. Every signed six-component wrench is transported "
                    "to its listed reference. An unresolved trusted transverse response "
                    "remains unevaluated in the native result.",
                    styles["body"],
                )
            )
            _schedules(
                story,
                "Executed expression and first member substitution",
                [
                    ("Expression", "F=P u+Qp p+Qq q"),
                    (
                        "Transport",
                        "F_target=F_member; M_target=M_member+(r_member-r_target) cross F",
                    ),
                    ("Native demand status", _text(node_demand.get("status"))),
                    ("First member", _text(members[0].get("member_id"))),
                    *flatten_unique(
                        "member",
                        members[0],
                        minimum_alias_leaves=1,
                        display_units=options.display_units,
                    ),
                ],
                styles,
            )
    examples = _native_equation_examples(result)
    if examples:
        story.append(
            _paragraph("Executed equation methods and worked native traces", styles["heading"])
        )
        story.append(
            _paragraph(
                "The expression identifies the executed method. The following numerical example "
                "is one native check record; the complete native schedule retains every other "
                "check and its varying inputs, factors and result.",
                styles["body"],
            )
        )
        for method, (path, check) in sorted(examples.items()):
            template = _MULTIROW_METHODS.get(method)
            if template is None:
                raise ReportingCoverageError(
                    f"Executed method has no REPORT1 report adapter: {method} at {path}"
                )
            trace = check.get("equation_trace")
            if not isinstance(trace, dict):
                raise ReportingCoverageError(
                    f"Executed method has no native numerical trace: {method} at {path}"
                )
            story.append(_paragraph(f"{method} - {template.title}", styles["heading"]))
            story.append(_paragraph(template.explanation, styles["body"]))
            if method == "PIN_BEARING":
                substitution = _bearing_substitution(snapshot.request, result, check)
                if substitution is None:
                    raise ReportingCoverageError(
                        f"Executed bearing check lacks an identified native substitution: {path}"
                    )
                story.append(_paragraph(substitution, styles["body"]))
            story.append(
                _table(
                    [
                        ("Native record", path),
                        ("Expression", template.expression),
                        ("Source locator", _text(check.get("source_locator"))),
                        ("Factor substitution", _factor_substitution(check.get("factor_trace"))),
                        ("Demand", _quantity(check.get("demand"))),
                        ("Nominal resistance", _quantity(check.get("equation_nominal_resistance"))),
                        ("Design resistance", _quantity(check.get("design_resistance"))),
                        ("Native utilization", _text(check.get("utilization"))),
                        ("Outcome", _text(check.get("numerical_comparison"))),
                    ],
                    styles,
                )
            )
            _schedules(
                story,
                "Executed input and intermediate substitution",
                _flatten("trace", trace),
                styles,
            )
    other_methods = executed_records(result)
    if other_methods:
        story.append(_paragraph("Other executed native methods", styles["heading"]))
        story.append(
            _paragraph(
                "Each method below shows its executed native expression and one worked "
                "record. The complete native schedule lists every other owner, case and path.",
                styles["body"],
            )
        )
        for method, (path, record) in sorted(other_methods.items()):
            other_template = EXECUTED_METHODS.get(method)
            if other_template is None:
                raise ReportingCoverageError(
                    f"Executed method has no REPORT1 report adapter: {method} at {path}"
                )
            story.append(_paragraph(f"{method} - {other_template.title}", styles["heading"]))
            story.append(_paragraph(other_template.explanation, styles["body"]))
            _schedules(
                story,
                "Executed expression and native substitution",
                [
                    ("Native record", path),
                    ("Expression", other_template.expression),
                    *_method_substitution_rows(method, record),
                ],
                styles,
            )
            _schedules(
                story,
                "Worked native inputs, intermediate values and result",
                flatten_unique(
                    "example",
                    _method_example_data(method, record),
                    minimum_alias_leaves=1,
                    display_units=options.display_units,
                ),
                styles,
            )
    _schedules(
        story,
        "Complete native results, traces, materials and limitations",
        flatten_unique(
            "result",
            result,
            minimum_alias_leaves=1,
            display_units=options.display_units,
        ),
        styles,
    )
    if native is not snapshot.result:
        _schedules(
            story,
            "MAT1 material and condition authority",
            flatten_unique(
                "material_wrapper",
                {
                    key: value
                    for key, value in snapshot.result.items()
                    if key not in {"client_design", "native_design"}
                },
                minimum_alias_leaves=1,
                display_units=options.display_units,
            ),
            styles,
        )
    _schedules(
        story,
        "Calculation identity",
        [
            ("Snapshot SHA-256", snapshot.digest),
            ("Calculation time (UTC epoch)", str(snapshot.issued_at)),
            ("Report preparation notes", options.notes),
        ],
        styles,
    )
    stream = io.BytesIO()
    document = _ReportDocument(
        stream,
        pagesize=PAPER_SIZES[options.paper],
        footer=f"{options.connection_id or snapshot.family} | {options.revision or 'No revision'} "
        f"| {status} | {snapshot.digest[:12]}",
    )
    document.title = title
    document.author = options.prepared_by or "FRP Master Connection"
    document.subject = f"{snapshot.family}: native result and explicit design limits"
    _add_linked_contents(story, styles)
    document.build(story, canvasmaker=_NumberedCanvas)
    return stream.getvalue()


__all__ = ("render_generic_pdf",)
