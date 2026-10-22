"Successor workflow presentation; existing D2/R3 methods retain their authority."

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from frp_master_connection.application.hyb1_contract import Alignment
from frp_master_connection.application.hyb2_d2 import D2Assessment, FitReview
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, R3Record

FIELD_USE = (
    "The owner reports that the source connection detail was installed and successfully used "
    "in real projects. This is field-use history, not physical load-test evidence or formal "
    "qualification. It does not establish conservatism or coverage of all failure modes."
)
LIMITS = (
    "First-row Angle/I stress transfer; independent receiving-I inter-row and block releases; "
    "heel, flange/web junction and eccentric/contact/prying behavior remain unverified. "
    "Complete connection verification and Section 2.3.2 qualification are not established."
)


def declared_fit(
    assessment: D2Assessment,
    *,
    edge: PhysicalQuantity | None,
    washer: PhysicalQuantity | None,
    face: str,
) -> D2Assessment:
    "Elementary declared footprint screen, never a surveyed/adopted evidence record."
    e = None if edge is None else edge.to(Unit.IN).magnitude
    od = None if washer is None else washer.to(Unit.IN).magnitude
    if (e is not None and e < 0) or (od is not None and od <= 0):
        raise ValueError("Nonnegative edge distance and positive washer OD required.")
    actual = (
        None
        if e is None or od is None or face != "DECLARED_STRAIGHT_FREE_EDGE"
        else max(Decimal(0), od / 2 - e)
    )
    conditional = None if e is None or od is None else max(Decimal(0), od / 2 - e)
    if actual is not None:
        action = (
            f"Insufficient washer edge/end clearance. Center-to-edge: {e} in; washer radius: "
            f"{cast(Decimal, od) / 2} in; overhang: {actual} in. "
            "Increase the distance or revise detailing for full seating."
            if actual > 0
            else (
                "No positive straight-edge washer overhang. This alone does not "
                "establish full hardware/tool fit or structural edge-rule "
                "compliance."
            )
        )
    else:
        action = (
            f"Washer would overhang by {conditional} in if this is the bearing-face free edge. "
            "Face remains unknown."
            if conditional is not None
            else (
                "Washer dimensions or bearing face are unknown; actual seating is not established."
            )
        )
    old = assessment.fit
    if old.hole_state == "NOT_FIT":
        action = (
            "Bolt-hole containment/placement fails the existing fit screen. "
            "Correct the current geometry before installation; no hole relocation is assumed. "
            + action
        )
    fit = FitReview(
        "NOT_FIT"
        if old.hole_state == "NOT_FIT" or (actual is not None and actual > 0)
        else "PHYSICAL_FIT_UNVERIFIED",
        old.hole_state,
        "USER_DECLARED_OVERHANG"
        if actual is not None and actual > 0
        else "USER_DECLARED_EDGE_SCREEN_ONLY"
        if actual is not None
        else "UNKNOWN_OR_CONDITIONAL",
        od,
        conditional,
        actual,
        action,
        old.unknowns,
    )
    return replace(assessment, fit=fit)


def source_scene(g: R3Geometry, r: R3Record, alignment: Alignment) -> dict[str, Any]:
    """Backend-authored R3 surfaces in the existing viewer's scene transport.

    Source x/y becomes global X/Z; +Y is the bolt/stack direction. Display crops
    remain labelled view cuts, never new engineering ends. No frontend geometry
    reconstruction or resistance calculation is required.
    """

    def v(x: Decimal | int, y: Decimal | int, z: Decimal | int) -> dict[str, float]:
        return {"x": float(x), "y": float(y), "z": float(z)}

    w, t, cw, ct = (
        q.to(Unit.IN).magnitude
        for q in (g.brace_leg, g.brace_thickness, g.column_flange, g.column_thickness)
    )
    xc = g.xc.to(Unit.IN).magnitude
    clear_web = Decimal(8) - 2 * ct
    if clear_web <= 0:
        raise ValueError("The displayed source I8 requires flange thickness below 4 in.")
    # R3 supplies the real oblique cut. Connected-leg polygon extends only to a
    # clearly designated display crop along +P.
    end = cast(Any, r.edges[0].endpoints)
    p, n = r.p_axis, r.n_axis
    points = [
        end[0],
        end[1],
        (end[1][0] + 8 * p[0], end[1][1] + 8 * p[1]),
        (end[0][0] + 8 * p[0], end[0][1] + 8 * p[1]),
    ]
    vertices = [v(x, -t, z) for x, z in points] + [v(x, 0, z) for x, z in points]
    triangles = [
        0,
        1,
        2,
        0,
        2,
        3,
        4,
        6,
        5,
        4,
        7,
        6,
        0,
        4,
        5,
        0,
        5,
        1,
        1,
        5,
        6,
        1,
        6,
        2,
        2,
        6,
        7,
        2,
        7,
        3,
        3,
        7,
        4,
        3,
        4,
        0,
    ]
    meshes = [
        {
            "id": "r3-angle-connected",
            "label": "Angle connected leg; far cap is a view cut",
            "ownerId": "member-a",
            "ownerLabel": "Angle brace",
            "ownerRole": "BRACE",
            "elementId": "LEG_1",
            "materialRegionId": "LEG_1",
            "points": [vertices[i] for i in triangles],
        }
    ]
    identity = [v(1, 0, 0), v(0, 1, 0), v(0, 0, 1)]

    def box(
        key: str,
        label: str,
        owner: str,
        role: str,
        center: dict[str, float],
        size: dict[str, float],
        basis: list[dict[str, float]],
    ) -> dict[str, Any]:
        return {
            "id": key,
            "label": label,
            "ownerId": owner,
            "ownerLabel": label,
            "ownerRole": role,
            "elementId": None,
            "materialRegionId": None,
            "center": center,
            "size": size,
            "basis": basis,
            "deferred": False,
            "interference": False,
        }

    boxes = [
        box(
            "I-flange",
            "Receiving I flange; top/bottom caps are view cuts",
            "member-b",
            "COLUMN",
            v(xc - cw / 2, ct / 2, 0),
            v(cw, ct, 12),
            identity,
        ),
        box(
            "I-web",
            "I8 web; source nominal .375 thickness, roots unverified",
            "member-b",
            "COLUMN",
            v(xc - cw / 2, 4, 0),
            v(Decimal(".375"), clear_web, 12),
            identity,
        ),
        box(
            "I-back-flange",
            "I opposite flange; view context",
            "member-b",
            "COLUMN",
            v(xc - cw / 2, 8 - ct / 2, 0),
            v(cw, ct, 12),
            identity,
        ),
    ]
    # Outstanding Angle leg follows the same R3 member axes; root fillets unknown.
    mid = points[1]
    boxes.append(
        box(
            "angle-outstanding",
            "Angle outstanding leg; root/fillet unverified",
            "member-a",
            "BRACE",
            v(mid[0] + 4 * p[0], -w / 2, mid[1] + 4 * p[1]),
            v(8, w, t),
            [v(p[0], 0, p[1]), v(0, 1, 0), v(n[0], 0, n[1])],
        )
    )
    centers = r.bolt_centers if alignment is Alignment.SUPPORT else r.rotation_centers
    cylinders = []
    for name, (x, z) in centers:
        for kind, diam, start, end_y in [
            ("BOLT", g.diameter.to(Unit.IN).magnitude, -t, ct),
            ("HOLE", g.hole.to(Unit.IN).magnitude, -t, ct),
        ]:
            cylinders.append(
                {
                    "id": name + kind,
                    "label": name + " " + kind,
                    "start": v(x, start, z),
                    "end": v(x, end_y, z),
                    "diameter": float(diam),
                    "kind": kind,
                    "hardwareLocation": None,
                    "ownerBoltId": name,
                    "rowId": name,
                    "boltLineId": "L1",
                    "penetratedLayerIds": ["member-a", "member-b"],
                    "interfaceId": "R3_SHARED_PAIR",
                }
            )
    from frp_master_connection.application.hybrid_material_axes import source_material_axes

    for item, element, region in zip(
        boxes,
        ("TOP_FLANGE", "WEB", "BOTTOM_FLANGE", "LEG_2"),
        ("FLANGES", "WEB", "FLANGES", "LEG_2"),
        strict=True,
    ):
        item["elementId"], item["materialRegionId"] = element, region
    return {
        "snapshotVersion": "HYB2-D3-P1-R3",
        "unitSystem": "US_CUSTOMARY",
        "lengthUnit": "in",
        "boxes": boxes,
        "meshes": meshes,
        "cylinders": cylinders,
        "frames": [],
        "markers": [],
        "positiveArrows": [],
        "appliedArrows": [],
        "connectionDemandArrows": [],
        "perBoltDemandArrows": [],
        "materialAxes": source_material_axes(r.p_axis, r.n_axis),
        "zones": [],
        "connectionOrientation": None,
        "boundsCenter": v(1, 2, 0),
        "boundsRadius": 10,
        "fitCenter": v(0, 0, 0),
        "fitRadius": 7,
    }
