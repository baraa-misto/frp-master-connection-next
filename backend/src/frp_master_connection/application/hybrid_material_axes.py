"""Presentation of the established pultruded R3 member axes, never resistance."""

from decimal import Decimal
from typing import Any

from frp_master_connection.domain.section_topology import (
    create_region_specific_planar_orientations,
    create_standard_section_topology,
)
from frp_master_connection.domain.values import PrincipalAxisFamily, SectionFamily


def _vector(direction: tuple[float, float, float], sign: int = 1) -> dict[str, float]:
    return dict(zip(("x", "y", "z"), (sign * x for x in direction), strict=True))


def source_material_axes(
    p: tuple[Decimal, Decimal], n: tuple[Decimal, Decimal]
) -> list[dict[str, Any]]:
    """LW follows the source brace P and receiving-member longitudinal direction.

    The source x/y plane maps to viewer X/Z; +Y is stack thickness. CW is
    bidirectional. Choose -n for the connected leg so LW/CW/TT is right handed.
    Canonical region rules rotate CW/TT for the other Angle leg and I web.
    Fillet/junction regions have no established planar basis and are omitted.
    """
    bases = (
        (
            "member-a",
            "Angle brace",
            SectionFamily.ANGLE,
            ((float(p[0]), 0.0, float(p[1])), (-float(n[0]), 0.0, -float(n[1])), (0.0, 1.0, 0.0)),
        ),
        (
            "member-b",
            "Receiving I",
            SectionFamily.I_SECTION,
            ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ),
    )
    result = []
    for owner, label, family, vectors in bases:
        rules = create_region_specific_planar_orientations(
            family, PrincipalAxisFamily.Y, PrincipalAxisFamily.Z
        )
        topology = create_standard_section_topology(family)
        directions = dict(zip(PrincipalAxisFamily, vectors, strict=True))
        for element in topology.elements:
            region = next(
                r for r in topology.material_regions if r.id == element.material_region_id
            )
            rule = rules[region.role]

            result.append(
                {
                    "id": owner + ":" + element.id + ":material-axes",
                    "componentId": owner,
                    "componentLabel": label,
                    "sectionFamily": family.value,
                    "elementId": element.id,
                    "elementLabel": element.label,
                    "materialRegionId": region.id,
                    "origin": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "presentation": None,
                    "lengthwise": _vector(directions[PrincipalAxisFamily.X]),
                    "crosswise": _vector(directions[rule.crosswise_axis], rule.crosswise_sign),
                    "throughThickness": _vector(
                        directions[rule.through_thickness_axis], rule.through_thickness_sign
                    ),
                }
            )
    return result
