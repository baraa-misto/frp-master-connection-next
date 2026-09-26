"""Read-only schematic bolt-axis sections from native physical stack records."""

from __future__ import annotations

from typing import Any

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors

from frp_master_connection.reporting.units import DisplayUnits, display_quantity


def native_bolt_sections(
    value: object, system: DisplayUnits = "INHERIT"
) -> list[tuple[str, Drawing]]:
    """One identified view for each distinct native penetration stack and hole set."""

    found: list[tuple[str, Drawing]] = []
    seen: set[tuple[object, ...]] = set()

    def visit(item: object) -> None:
        if isinstance(item, dict):
            visual = item.get("visualization")
            if isinstance(visual, dict):
                layers = visual.get("layers")
                bolts = visual.get("physical_bolts")
                if isinstance(layers, list) and isinstance(bolts, list):
                    by_id = {
                        layer["layer_id"]: layer
                        for layer in layers
                        if isinstance(layer, dict) and isinstance(layer.get("layer_id"), str)
                    }
                    for bolt in bolts:
                        if not isinstance(bolt, dict) or not isinstance(bolt.get("display"), dict):
                            continue
                        ids = bolt.get("penetrated_layer_ids")
                        if (
                            not isinstance(ids, list)
                            or not ids
                            or any(key not in by_id for key in ids)
                        ):
                            continue
                        display = bolt["display"]
                        holes = display.get("holes", [])
                        if not isinstance(holes, list):
                            continue
                        thicknesses = tuple(
                            (
                                str(by_id[key]["thickness"]["value"]),
                                str(by_id[key]["thickness"]["unit"]),
                            )
                            for key in ids
                            if isinstance(by_id[key].get("thickness"), dict)
                        )
                        if len(thicknesses) != len(ids):
                            continue
                        hole_diameters = tuple(
                            str(hole.get("diameter")) for hole in holes if isinstance(hole, dict)
                        )
                        signature: tuple[object, ...] = (
                            tuple(ids),
                            thicknesses,
                            str(display.get("bolt_diameter")),
                            hole_diameters,
                        )
                        if signature in seen:
                            continue
                        seen.add(signature)
                        identity = f"{display.get('bolt_group_id')} / {bolt.get('bolt_id')}"
                        found.append((identity, _drawing(ids, thicknesses, display, system)))
            for name, child in item.items():
                if name != "visualization":
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return found


def _drawing(
    layer_ids: list[str],
    thicknesses: tuple[tuple[str, str], ...],
    display: dict[str, Any],
    system: DisplayUnits,
) -> Drawing:
    width, height = 480, 175
    diagram = Drawing(width, height)
    count = len(layer_ids)
    left, right = 32.0, 448.0
    cell = (right - left) / count
    axis_y = 83.0
    diagram.add(
        String(
            8,
            158,
            "Native bolt-axis stack; schematic, not to scale",
            fontName="ReportVeraBold",
            fontSize=9,
        )
    )
    for index, (identity, thickness) in enumerate(zip(layer_ids, thicknesses, strict=True)):
        x = left + index * cell
        rectangle = Rect(x, 65, cell, 42)
        rectangle.strokeColor = colors.HexColor("#526675")
        rectangle.fillColor = colors.HexColor("#f7f9fa")
        rectangle.strokeWidth = 0.7
        diagram.add(rectangle)
        diagram.add(
            String(
                x + 2,
                127,
                f"L{index + 1}: {identity[: max(4, int(cell / 5.3))]}",
                fontName="ReportVera",
                fontSize=9,
            )
        )
        diagram.add(
            String(
                x + 2,
                114,
                f"t = {display_quantity({'value': thickness[0], 'unit': thickness[1]}, system)}",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    diagram.add(
        Line(
            left - 10,
            axis_y,
            right + 10,
            axis_y,
            strokeColor=colors.HexColor("#9b4435"),
            strokeWidth=3,
        )
    )
    diagram.add(
        String(
            12,
            48,
            "Bolt d = "
            + display_quantity(
                {"value": display.get("bolt_diameter"), "unit": thicknesses[0][1]}, system
            ),
            fontName="ReportVera",
            fontSize=9,
        )
    )
    holes = display.get("holes", [])
    if isinstance(holes, list) and holes:
        labels = ", ".join(
            f"L{index + 1}="
            + display_quantity({"value": hole.get("diameter"), "unit": thicknesses[0][1]}, system)
            for index, hole in enumerate(holes)
            if isinstance(hole, dict)
        )
        diagram.add(
            String(
                12,
                33,
                f"Physical hole diameters: {labels}",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    washers = display.get("washers", [])
    if isinstance(washers, list) and washers:
        diagram.add(
            String(
                12,
                18,
                f"Native washer records: {len(washers)}; see full schedule",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    else:
        diagram.add(
            String(
                12,
                18,
                "No washer record supplied for this stack",
                fontName="ReportVera",
                fontSize=9,
            )
        )
    return diagram


__all__ = ("native_bolt_sections",)
