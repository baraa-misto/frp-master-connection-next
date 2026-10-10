"""SAB2 presentation meshes from the evaluated geometry; never calculation authority.

Convex cuts clip nominal member prisms. Root exclusions are labeled planar
envelopes, not manufactured fillets. Hardware display is a faceted envelope;
clearance remains the analytic cylinder calculation in the shared kernel.
"""

from __future__ import annotations

import math
from copy import deepcopy
from decimal import Decimal
from typing import Any, cast

from frp_master_connection.application.direct_two_bolt_geometry import (
    P2,
    V3,
    Face,
    PairInput,
    add,
    clip_polygon,
    dot,
    local_point,
    scale,
)


def prism(polygon: tuple[P2, ...], low: Decimal, high: Decimal, face: Face) -> tuple[V3, ...]:
    def point(p: P2, z: Decimal) -> V3:
        return add(
            face.origin,
            add(scale(face.axes[0], p[0]), add(scale(face.axes[1], p[1]), scale(face.axes[2], z))),
        )

    points: list[V3] = []
    for index in range(1, len(polygon) - 1):
        for z in (low, high):
            points.extend(point(p, z) for p in (polygon[0], polygon[index], polygon[index + 1]))
    for index, p in enumerate(polygon):
        q = polygon[(index + 1) % len(polygon)]
        points.extend(
            (
                point(p, low),
                point(q, low),
                point(q, high),
                point(p, low),
                point(q, high),
                point(p, high),
            )
        )
    return tuple(points)


def display_constraints(visual: dict[str, Any], pair: PairInput, factor: Decimal) -> dict[str, Any]:
    """Coordinates originate exclusively in the backend's evaluated PairInput."""
    result = deepcopy(visual)
    snapshot = result["physical_connection"]
    template = snapshot["primitives"][0]

    def vector(p: dict[str, Any]) -> V3:
        return cast(V3, tuple(Decimal(str(p[k])) for k in ("x", "y", "z")))

    def mesh(
        identity: str,
        label: str,
        owner: str,
        points: tuple[V3, ...],
        original: dict[str, Any] = template,
    ) -> dict[str, Any]:
        return {
            **original,
            "id": identity,
            "label": label,
            "owner_id": owner,
            "kind": "TRIANGLE_MESH",
            "points": [
                {k: str(p[i] * factor) for i, k in enumerate(("x", "y", "z"))} for p in points
            ],
            "parameters": [],
            "resolution_status": "RESOLVED",
        }

    # Clip all represented member elements, including the outstanding Angle leg,
    # using the same convex face-plane cut extruded along its proper normal.
    for face in pair.faces:
        cuts = tuple(b for b in face.boundaries if b.role == "PHYSICAL_END_OR_SIDE")
        if not cuts:
            continue
        for name in ("primitives", "view_extension_primitives"):
            output = []
            for primitive in snapshot[name]:
                if primitive["owner_id"] != face.member_id or primitive["kind"] != "BOX":
                    output.append(primitive)
                    continue
                values = {
                    p["name"]: Decimal(str(p["value"])) / factor for p in primitive["parameters"]
                }
                half = (
                    (values["x_end"] - values["x_start"]) / 2,
                    (values["max_y"] - values["min_y"]) / 2,
                    (values["max_z"] - values["min_z"]) / 2,
                )
                axes = tuple(vector(primitive[k]) for k in ("x_axis", "y_axis", "z_axis"))
                center = local_point(
                    scale(vector(primitive["center"]), 1 / factor), face.origin, face.axes
                )
                extent = tuple(
                    sum(
                        (abs(dot(axis, fa)) * h for axis, h in zip(axes, half, strict=True)),
                        Decimal(0),
                    )
                    for fa in face.axes
                )
                u0, u1 = center[0] - extent[0], center[0] + extent[0]
                v0, v1 = center[1] - extent[1], center[1] + extent[1]
                polygon: tuple[P2, ...] = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
                for boundary in cuts:
                    polygon = clip_polygon(polygon, (boundary.a, boundary.b, boundary.limit))
                if len(polygon) >= 3:
                    output.append(
                        mesh(
                            primitive["id"],
                            primitive["label"] + " — declared convex cut",
                            face.member_id,
                            prism(polygon, center[2] - extent[2], center[2] + extent[2], face),
                            primitive,
                        )
                    )
            snapshot[name] = output
    for obstacle in pair.obstacles:
        u0, v0, z0 = obstacle.lower
        u1, v1, z1 = obstacle.upper
        face = Face(
            obstacle.id, obstacle.id, obstacle.origin, obstacle.axes, (), (), (), obstacle.source
        )
        snapshot["primitives"].append(
            mesh(
                obstacle.id,
                "Declared neighboring envelope: " + obstacle.source,
                obstacle.id,
                prism(((u0, v0), (u1, v0), (u1, v1), (u0, v1)), z0, z1, face),
            )
        )
    for face in pair.faces:
        original = next(
            p for p in visual["physical_connection"]["primitives"] if p["id"] == face.source
        )
        values = {p["name"]: Decimal(str(p["value"])) / factor for p in original["parameters"]}
        u0, u1 = values["x_start"], values["x_end"]
        bands = []
        if face.seating_strips:
            web = next(
                p
                for p in visual["physical_connection"]["primitives"]
                if p["owner_id"] == face.member_id and p["physical_element_id"] == "WEB"
            )
            w = {p["name"]: Decimal(str(p["value"])) / factor for p in web["parameters"]}
            bands = [
                (face.seating_strips[0][1], w["min_y"]),
                (w["max_y"], face.seating_strips[1][0]),
            ]
        else:
            coordinate = "z" if ":LEG_2:" in face.id else "y"
            junction = next(b for b in face.boundaries if b.role == "INTERNAL_JUNCTION")
            bands = [(values["min_" + coordinate], -junction.limit)]
        for index, (low, high) in enumerate(bands):
            if low < high:
                snapshot["primitives"].append(
                    mesh(
                        f"ROOT_EXCLUSION:{face.id}:{index}",
                        "Declared root seating exclusion plane — not a fillet profile",
                        "DECLARED_EXCLUSION",
                        prism(
                            ((u0, low), (u1, low), (u1, high), (u0, high)),
                            Decimal(0),
                            Decimal(0),
                            face,
                        ),
                    )
                )
    centers = tuple(
        add(pair.midpoint, scale(pair.direction, sign * pair.spacing / 2))
        for sign in (Decimal(-1), Decimal(1))
    )
    for station, center in enumerate(centers):
        for envelope in pair.hardware:
            ring = tuple(
                (
                    Decimal(str(math.cos(i * math.tau / 32))) * envelope.radius,
                    Decimal(str(math.sin(i * math.tau / 32))) * envelope.radius,
                )
                for i in range(32)
            )
            face = Face(
                "DISPLAY",
                "DISPLAY",
                center,
                (
                    pair.faces[0].axes[0],
                    scale(
                        pair.faces[0].axes[1],
                        Decimal(1) if dot(pair.faces[0].axes[2], pair.normal) > 0 else Decimal(-1),
                    ),
                    pair.normal,
                ),
                (),
                (),
                (),
                envelope.source,
            )
            snapshot["primitives"].append(
                mesh(
                    f"ENVELOPE:B{station + 1}:{envelope.name}",
                    f"Declared {envelope.name} cylinder envelope",
                    "DECLARED_ENVELOPE",
                    prism(ring, envelope.start, envelope.end, face),
                )
            )
    return result
