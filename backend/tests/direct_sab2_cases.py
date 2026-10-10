"""Explicit review controls; none of these study dimensions become UI defaults."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from typing import Any

from frp_master_connection.api.direct_two_bolt import TwoBoltRequestDTO, geometry_response
from tests.api.test_direct_two_bolt import quantity, sab2_body


def fixed_drawing_case(small: bool = False) -> dict[str, Any]:
    """Resolve the declared study datum in the production proper support frame.

    Actual production Angle length remains its submitted e1/pitch/end definition;
    the SAB1 illustrative five-inch crop is deliberately not imported.
    """
    body = sab2_body(alignment="SUPPORT", spacing=quantity("2.25"), hole_diameter=quantity(".5625"))
    physical = body["legacy"]["physical_connection"]
    members = physical["joint_assembly"]["members"]
    support = next(m["section"] for m in members if m["section"]["kind"] == "WIDE_FLANGE")
    support.update(
        flange_width=quantity("4"),
        web_thickness=quantity(".375"),
        flange_thickness=quantity(".375"),
    )
    angle = next(m["section"] for m in members if m["section"]["kind"] == "ANGLE")
    if small:
        angle.update(leg_y=quantity("3"), leg_z=quantity("3"), thickness=quantity(".375"))
        body["legacy"]["layers"][0]["thickness"] = quantity(".375")
    physical["geometry_template"]["brace_to_column_directed_angle_deg"] = "120.9"
    # Explicit review member extent: a five-inch unloaded end, not SAB1's
    # five-inch total display window. Neither member moves during A/B comparison.
    body["legacy"]["unloaded_end_e1"] = quantity("5")
    body["legacy"]["loaded_boundary_to_row_1_distance"] = quantity("5")
    physical["geometry_template"]["bolt_to_brace_end_distance"] = quantity("5")
    body["material_request"]["legacy_request"] = deepcopy(body["legacy"])
    data = geometry_response(TwoBoltRequestDTO.model_validate(body))
    faces = data["pair_input"]["faces"]
    local = []
    for face in faces:
        points = [
            p["local_center"] for p in data["geometry"]["face_points"] if p["face_id"] == face["id"]
        ]
        local.append(tuple((Decimal(points[0][i]) + Decimal(points[1][i])) / 2 for i in range(3)))
    with localcontext() as context:
        context.prec = 64
        # Stated v_G=2.125 in in SAB1 becomes +.125 relative to the centered L4
        # section; the smaller case has its separately disclosed +.0625 datum.
        target_angle_v = Decimal(".0625" if small else ".125")
        target_support_v = Decimal("1")
        dv = target_support_v - local[1][1]

        def projection(index: int) -> Decimal:
            return sum(
                (
                    Decimal(a) * Decimal(b)
                    for a, b in zip(faces[0]["axes"][1], faces[1]["axes"][index], strict=True)
                ),
                Decimal(0),
            )

        du = (target_angle_v - local[0][1] - projection(1) * dv) / projection(0)
    body["offset"] = {
        "support_longitudinal": quantity(str(du)),
        "support_transverse": quantity(str(dv)),
    }
    return body


def sab2_cases() -> dict[str, dict[str, Any]]:
    exact = sab2_body()
    wide = sab2_body(
        offset={"support_longitudinal": quantity(".25"), "support_transverse": quantity("0")}
    )
    support = fixed_drawing_case()
    brace = deepcopy(support)
    brace["alignment"] = "BRACE"
    shifted = deepcopy(brace)
    shifted["offset"]["support_longitudinal"]["value"] = str(
        Decimal(shifted["offset"]["support_longitudinal"]["value"]) - Decimal(".26532874724302")
    )
    shifted["offset"]["support_transverse"]["value"] = str(
        Decimal(shifted["offset"]["support_transverse"]["value"]) - Decimal(".86108849053045")
    )
    neighbor = deepcopy(support)
    neighbor["neighbors"] = [
        {
            "id": "EXPLICIT-REVIEW-OBSTRUCTION",
            "support_local_lower": [quantity("-100")] * 3,
            "support_local_upper": [quantity("100")] * 3,
            "source": "Assumed finite QA obstruction; not neighboring assembly credit",
        }
    ]
    conditional = deepcopy(support)
    conditional["angle_root_encroachment"] = quantity(".15")
    conditional["support_root_encroachment"] = quantity(".1")
    conditional["manufactured_geometry_source"] = (
        "Specified scalar sensitivity envelopes; actual fillet profile unknown"
    )
    conditional["end_cuts"] = [
        {
            "member_id": "member-a",
            "polygon": [
                [quantity("0"), quantity("-1.5")],
                [quantity("8"), quantity("-1.5")],
                [quantity("8"), quantity("1.75")],
                [quantity("7.75"), quantity("2")],
                [quantity("0"), quantity("2")],
            ],
            "source": "Explicit finite convex bevel for review; not a fabrication default",
        }
    ]
    legacy = conditional["legacy"]
    legacy["supporting_w_longitudinal_ends"] = {
        "condition": "FINITE_BOTH_ENDS",
        "negative_end_distance": quantity("5"),
        "positive_end_distance": quantity("5"),
    }
    conditional["material_request"]["legacy_request"] = deepcopy(legacy)
    # A declared head envelope has exact axial contact with another declared box;
    # it is separate from nominal section seating and from unknown tool access.
    conditional["hardware"] = [
        {
            "kind": "HEAD",
            "radius": quantity(".25"),
            "axial_start": quantity("1"),
            "axial_end": quantity("2"),
            "source": "Assumed finite cylindrical QA envelope; actual head not certified",
        }
    ]
    data = geometry_response(TwoBoltRequestDTO.model_validate(conditional))
    # Use the actual support member frame, not the outer-seat-local normal origin.
    pair = data["pair_input"]
    frame = next(
        f["frame"]
        for f in data["visualization"]["physical_connection"]["frames"]
        if f["id"] == "MEMBER_LOCAL:member-b"
    )
    point = pair["midpoint"]
    normal_projection = sum(
        (
            Decimal(pair["normal"][i]) * Decimal(frame["z_axis"][a])
            for i, a in enumerate(("x", "y", "z"))
        ),
        Decimal(0),
    )
    axial_center = sum(
        (
            (Decimal(point[i]) - Decimal(frame["origin"][a])) * Decimal(frame["z_axis"][a])
            for i, a in enumerate(("x", "y", "z"))
        ),
        Decimal(0),
    )
    low = axial_center + (Decimal("2") if normal_projection > 0 else Decimal("-3"))
    conditional["neighbors"] = [
        {
            "id": "AXIAL-CONTACT-ONLY",
            "support_local_lower": [quantity("-100"), quantity("-100"), quantity(str(low))],
            "support_local_upper": [quantity("100"), quantity("100"), quantity(str(low + 1))],
            "source": "Explicit axial contact QA; no favorable unknown dimensions",
        }
    ]
    return {
        "exact-mc1-brace": exact,
        "wider-w-brace-relocated": wide,
        "detail2-support-nominal": support,
        "narrow-i-fixed-brace-no-fit": brace,
        "brace-split-outstand-relocated": shifted,
        "smaller-angle-no-fit": fixed_drawing_case(True),
        "known-neighbor-no-fit": neighbor,
        "finite-cut-root-contact-unknown-access": conditional,
    }
