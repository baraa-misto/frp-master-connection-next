"""P4 report presentation of stored physical results; no calculation calls."""

from decimal import Decimal
from html import escape
from typing import Any

from reportlab.graphics.shapes import Drawing, Ellipse, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph

from frp_master_connection.reporting.hybrid_labels import label, utilization


def release_drawing(case: dict[str, Any]) -> Drawing:
    """Plot the stored physical witness, not a new fracture/applicability decision."""
    witness = case["physical_release"]
    drawing = Drawing(500, 310)
    scale = 32.0
    center_x, datum_y = 235.0, 90.0
    free_y = float(witness["actual_free_end_y_in"])
    sign = 1.0 if free_y > 0 else -1.0
    # Mirror the negative-end view so every true end fits on the page.
    # Truncate long lengths graphically only; print the actual dimension.
    extent = max(abs(free_y), 2.0)
    scale = min(scale, 150.0 / extent)

    def xy(x: float, y: float) -> tuple[float, float]:
        return center_x + x * 85, datum_y + sign * y * scale

    radius = float(witness["hole_radius_in"])
    root = float(witness["root_exclusion_x_in"])
    edge = float(case["actual_geometry_in"]["xc"])
    end = xy(0, free_y)[1]
    base = datum_y - 1.4 * scale
    context = Rect(xy(root, 0)[0], base, (edge - root) * 85, end - base)
    context.strokeColor = colors.gray
    context.fillColor = colors.HexColor("#eef2f7")
    drawing.add(context)
    start = xy(0, float(witness["source_shear_face_start_y_in"]))[1]
    for side in (-1, 1):
        drawing.add(
            Line(
                center_x + side * radius * 85,
                start,
                center_x + side * radius * 85,
                end,
                strokeColor=colors.HexColor("#b42318"),
                strokeWidth=1.5,
            )
        )
    for bolt, coordinate in case["physical_bolt_centers_in"]:
        x, y = xy(float(coordinate[0]), float(coordinate[1]))
        # Use the actual two page scales so the holes meet the shear-face tangents.
        drawing.add(
            Ellipse(
                x, y, radius * 85, radius * scale, fillColor=colors.white, strokeColor=colors.black
            )
        )
        drawing.add(String(x + 12, y - 3, bolt, fontSize=9))
    drawing.add(
        Line(
            xy(root, 0)[0],
            base,
            xy(root, 0)[0],
            end,
            strokeColor=colors.HexColor("#5c6670"),
            strokeWidth=2,
        )
    )
    drawing.add(String(8, 294, "Current receiving flange: local longitudinal release", fontSize=11))
    drawing.add(
        String(8, 278, "Actual free end = " + str(free_y) + " in from the common datum", fontSize=9)
    )
    drawing.add(
        String(
            8,
            263,
            "e1 = "
            + case["actual_unloaded_e1_in"]
            + " in; actual vertical pitch = "
            + case["actual_geometry_in"]["pitch"]
            + " in",
            fontSize=9,
        )
    )
    drawing.add(
        String(
            8,
            23,
            "Red: two local shear faces; trailing hole void closes the local strip.",
            fontSize=9,
        )
    )
    drawing.add(
        String(
            8,
            9,
            "Gray: excluded integral root/web. No global block or first-row coverage. Schematic.",
            fontSize=8,
        )
    )
    drawing.add(
        String(
            8,
            36,
            "Lower gray boundary: view crop; member continues. Different LW/CW scales.",
            fontSize=8,
        )
    )
    drawing.add(String(center_x + 92, end - 12, "True free end", fontSize=9))
    nearest_y = xy(
        0,
        float(
            next(
                coordinate[1]
                for bolt, coordinate in case["physical_bolt_centers_in"]
                if bolt == case["nearest_unloaded_row"]
            )
        ),
    )[1]
    drawing.add(Line(410, nearest_y, 410, end, strokeColor=colors.gray))
    for level in (nearest_y, end):
        drawing.add(Line(405, level, 415, level, strokeColor=colors.gray))
    drawing.add(
        String(
            418, (nearest_y + end) / 2, "e1 = " + case["actual_unloaded_e1_in"] + " in", fontSize=9
        )
    )
    drawing.add(String(center_x + 92, datum_y - 8, "Common datum", fontSize=9))
    drawing.add(
        Line(center_x + 75, datum_y + 8, center_x + 75, datum_y + 38, strokeColor=colors.darkblue)
    )
    drawing.add(
        Line(center_x + 75, datum_y + 38, center_x + 71, datum_y + 31, strokeColor=colors.darkblue)
    )
    drawing.add(
        Line(center_x + 75, datum_y + 38, center_x + 79, datum_y + 31, strokeColor=colors.darkblue)
    )
    drawing.add(
        String(
            center_x + 90,
            datum_y + 30,
            ("+LW" if sign > 0 else "-LW") + " connection force",
            fontSize=8,
        )
    )
    return drawing


def physical_flowables(record: dict[str, Any], *, technical: bool) -> list[Flowable]:
    """Read only the backend-sealed physical data and decisions."""
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    styles["BodyText"].wordWrap = "CJK"
    styles["BodyText"].spaceAfter = 6 if technical else 4
    if not technical:
        styles["Heading3"].spaceBefore = 8
        styles["Heading3"].spaceAfter = 4
    story: list[Flowable] = []

    def p(value: object, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(str(value)), styles[style]))

    physical = record["physical_design"]
    p("Current physical structural components", "Heading1")
    p("User-declared actual geometry and actions. Owner engineering adoption remains pending.")
    if technical:
        for key, value in physical["status_axes"].items():
            if key != "viewer_tone":
                p(label(key) + ": " + label(value))
    for failure in physical["geometry_failures"]:
        for reason in failure["reasons"]:
            p("Physical geometry FAIL: " + reason + " Revise the actual detailing.")
    context = record["inputs"]["physical_context"]

    def quantity_text(value: dict[str, Any] | None) -> str:
        return (
            "Unknown"
            if value is None
            else format(Decimal(value["value"]), ".6g") + " " + value["unit"]
        )

    for key, name in (
        ("positive_end", "+LW receiving direction"),
        ("negative_end", "-LW receiving direction"),
    ):
        end = context[key]
        p(
            name
            + ": "
            + label(end["condition"])
            + "; actual free-end distance: "
            + quantity_text(end["distance"])
            + " from the common datum."
        )
    p(
        "Measured clear flat outstand: "
        + quantity_text(context["clear_flat_outstand"])
        + "; actual interface gap: "
        + quantity_text(context["interface_gap"])
        + "."
    )
    p(
        "Original published standard-hole unit column: "
        + ("Unknown" if context["hole_source"] is None else label(context["hole_source"]))
        + "; display conversion does not recreate the hole."
    )
    for receiving in context["receiving_actions"]:
        p(
            "Additional receiving actions / "
            + receiving["case_id"]
            + "; receiving LW/CW/TT at the common datum: "
            + "; ".join(
                name + " = " + quantity_text(value)
                for name, value in zip(
                    ("F_LW", "F_CW", "F_TT", "M_LW", "M_CW", "M_TT"),
                    receiving["components"],
                    strict=True,
                )
            )
            + "."
        )
    if technical:
        p("Complete original physical input record: " + str(context))
    for case in physical["cases"]:
        p("Receiving inter-row shear-out / " + case["case_id"], "Heading2")
        p("Disposition: " + case["disposition"] + ". " + case["source"])
        for reason in case["reasons"]:
            p("Not evaluated: " + reason)
        if case["disposition"] == "EXECUTED":
            story.append(release_drawing(case))
            geometry = case["actual_geometry_in"]
            ledger = case["MAT1_ledger"]
            factors = case["equation_trace"]["factor_trace"]
            p("Rn = 1.4 (e1 - dn/2 + s) t Fsh; ASCE/SEI 74-23 Eq.8-12.")
            p(
                "Substitution: 1.4 ("
                + case["actual_unloaded_e1_in"]
                + " - "
                + geometry["hole"]
                + "/2 + "
                + geometry["pitch"]
                + ") x "
                + geometry["thickness"]
                + " x "
                + ledger["adjusted_candidate"]
                + " [in, "
                + ledger["unit"]
                + "]. Rn = "
                + utilization(case["nominal_resistance_kip"], technical=technical)
                + " kip."
            )
            p(
                "Adjusted receiving shear property: "
                + ledger["record_id"]
                + "; original "
                + ledger["original"]
                + " "
                + ledger["unit"]
                + "; CM="
                + ledger["cm"]
                + ", CT="
                + ledger["ct"]
                + ", CCH="
                + ledger["cch"]
                + ". Already adjusted by MAT1 once; no second property reduction."
            )
            p(
                "Rd = Rn x C_lap x C_delta x phi x lambda. Separate factors: "
                + str(factors["lap_factor_c_lap"])
                + " x "
                + str(factors["pitch_factor_c_delta"])
                + " x "
                + str(factors["resistance_factor_phi"])
                + " x "
                + str(factors["time_effect_factor_lambda"])
                + ". Rd = "
                + utilization(case["design_resistance_kip"], technical=technical)
                + " kip."
            )
            p(
                "Full single-line demand = "
                + case["line_demand_kip"]
                + " kip; UR = "
                + utilization(case["utilization"], technical=technical)
                + "; "
                + case["outcome"]
                + ". No P/n force is substituted for the complete line."
            )
            screen = case["net_area_screen"]
            p(
                "Net-area screen (not first-row resistance): gross connected flange "
                + utilization(screen["gross_connected_flange_in2"], technical=technical)
                + " in2; net "
                + utilization(screen["net_connected_flange_in2"], technical=technical)
                + " in2; net deduction diameter "
                + utilization(screen["net_deduction_diameter_in"], technical=technical)
                + " in; raw An/Ag "
                + utilization(screen["raw_ratio"], technical=technical)
                + "; minimum 0.75; "
                + screen["outcome"]
                + ". Exact operands and the lower-bound proof are retained in Technical Audit/JSON."
            )
            p("Coupled mechanisms remain independent: " + case["separate_required"])
        if technical:
            for key, value in case.items():
                p(key + ": " + str(value))
    p("Required physical mechanism dispositions", "Heading2")
    for mechanism in physical["mechanism_matrix"]:
        p(
            mechanism["mechanism"]
            + " - "
            + (mechanism["disposition"] if technical else label(mechanism["disposition"])),
            "Heading3",
        )
        p(mechanism["source"] + ". " + mechanism["remaining_evidence"])
    return story
