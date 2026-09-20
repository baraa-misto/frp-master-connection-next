"""Actual DCTN flat-wall/hole-set adapters to the frozen native rupture planners.

The full solid is deliberately absent: it is not a fictitious thin plate. Native
rectangular projected-boundary methods are not applied to an oblique rectangle.
Junctions/corners are not presented as free edges to obtain an accepted path.
"""

from __future__ import annotations

from decimal import Decimal

from frp_master_connection.calculation.block_shear_planning import (
    BoltHoleSource,
    build_block_shear_area_plans,
)
from frp_master_connection.calculation.multirow import (
    MaterialDirection,
    PultrudedElementClassification,
    resolve_first_row_geometry,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    create_standard_hole,
)
from frp_master_connection.domain.dctn_geometry import DCTNBoltCode, DCTNGeometry, DCTNPlanePlan
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, DCTNRequest
from frp_master_connection.geometry.multirow import (
    BoundaryObstacleKind,
    GeneralBolt,
    GeneralBoltGroup,
    MultiRowGeometryTolerance,
    PlanarLayerBoundary,
    PlanarPoint2D,
    RectangularObstacle2D,
    resolve_block_shear_paths,
    resolve_multirow_geometry,
)


def dctn_plane_plans(
    value: DCTNRequest, geometry: DCTNGeometry, codes: tuple[DCTNBoltCode, ...] = ()
) -> tuple[DCTNPlanePlan, ...]:
    if geometry.status != "VALID":
        return ()
    unit = value.length_unit
    diameter = value.fastener.diameter.to(unit)
    hole = value.fastener.hole_diameter.to(unit)
    standard = create_standard_hole(
        value.fastener.diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
    )
    # Same physical sorting tolerance as the native multi-row workspace. Never
    # used for loads, moments, equilibrium, numerical comparisons or fingerprints.
    tolerance = MultiRowGeometryTolerance(
        float(PhysicalQuantity.of(".000001", Unit.IN).to(unit).magnitude)
    )
    plans: list[DCTNPlanePlan] = []
    for member in value.members:
        rows = tuple(r for r in geometry.rows if r.member_id == member.slot)
        native = next(p for p in geometry.members if p.physical_id == member.slot)
        for side in ("NEG", "POS"):
            group_id = f"{member.slot}:{side}"
            owners: tuple[str, ...] = (f"CHORD_{side}",)
            if member.section.form is not DCTNForm.SOLID_RECTANGLE:
                owners += (member.slot,)
            for owner in owners:
                owner_holes = tuple(
                    h for h in geometry.holes if h.owner_id == owner and h.group_id == group_id
                )
                sign = -1 if member.axial_force.canonical_magnitude < 0 else 1
                chord = owner != member.slot
                if chord:
                    half_length = float(value.channel.length.to(unit).magnitude / 2)
                    half_web = float(
                        value.channel.depth.to(unit).magnitude / 2
                        - value.channel.flange_thickness.to(unit).magnitude
                    )
                    boundary = PlanarLayerBoundary(
                        owner + ":WEB",
                        -half_length,
                        half_length,
                        -half_web,
                        half_web,
                        # Axial chord ends are free; the transverse web limits
                        # are flange junctions, not free rupture-path closures.
                        unloaded_end_is_free=native.u[2] == 0,
                        negative_side_is_free=native.u[0] == 0,
                        positive_side_is_free=native.u[0] == 0,
                    )
                    points = tuple(
                        PlanarPoint2D(float(h.center[0]), float(h.center[2])) for h in owner_holes
                    )
                    force = sign * float(native.u[0]), sign * float(native.u[2])
                    thickness = value.channel.web_thickness
                    direction = (
                        MaterialDirection.TRANSVERSE
                        if native.u[0] == 0
                        else MaterialDirection.LONGITUDINAL
                    )
                else:
                    width = float(member.section.width.to(unit).magnitude)
                    if member.section.form is DCTNForm.RHS:
                        # Native rectangular-tube TOP/BOTTOM wall regions stop
                        # at the two deferred corner squares. Neither square
                        # belongs to the qualified flat-wall rupture width.
                        width -= 2 * float(member.section.wall_or_web.to(unit).magnitude)
                    obstacles: tuple[RectangularObstacle2D, ...] = ()
                    length = float(member.section.length.to(unit).magnitude)
                    if member.section.form is DCTNForm.W_I:
                        half_root = float(member.section.wall_or_web.to(unit).magnitude / 2)
                        obstacles = (
                            RectangularObstacle2D(
                                owner + ":WEB_JUNCTION",
                                BoundaryObstacleKind.DEFERRED_JUNCTION,
                                0,
                                length,
                                -half_root,
                                half_root,
                            ),
                        )
                    boundary = PlanarLayerBoundary(
                        owner + ":" + side,
                        0,
                        length,
                        -width / 2,
                        width / 2,
                        negative_side_is_free=member.section.form is DCTNForm.W_I,
                        positive_side_is_free=member.section.form is DCTNForm.W_I,
                        obstacles=obstacles,
                    )
                    offset = (
                        member.pattern.wi_offset.to(unit).magnitude * (-1 if side == "NEG" else 1)
                        if member.section.form is DCTNForm.W_I
                        else Decimal(0)
                    )
                    points = tuple(PlanarPoint2D(float(r.from_start), float(offset)) for r in rows)
                    # Native row/end convention follows the signed member action:
                    # +P loads toward END; START is its unloaded free end. This
                    # projection is not a replacement bolt-on-member reaction.
                    force = float(sign), 0.0
                    thickness = (
                        member.section.flange_thickness
                        if member.section.form is DCTNForm.W_I
                        else member.section.wall_or_web
                    )
                    direction = MaterialDirection.LONGITUDINAL
                bolts = tuple(
                    GeneralBolt(
                        h.hole_id,
                        p,
                        float(diameter.magnitude),
                        float(hole.magnitude),
                        value.fastener.product_id,
                        group_id,
                    )
                    for h, p in zip(owner_holes, points, strict=True)
                )
                group = GeneralBoltGroup(
                    owner + ":" + group_id, boundary.id, len(rows), len(bolts), bolts
                )
                resolved = resolve_multirow_geometry(group, boundary, force, tolerance)
                first = resolve_first_row_geometry(
                    resolved, unit, diameter, direction, PultrudedElementClassification.SHAPE
                )
                reasons: list[str] = []
                if force[0] != 0 and force[1] != 0:
                    reasons.append("DCTN_OBLIQUE_RECTANGULAR_LOCAL_PATH_NOT_QUALIFIED")
                blocks = None
                if standard.hole_diameter != hole:
                    reasons.append("DCTN_ORDINARY_HOLE_METHOD_NOT_QUALIFIED")
                elif not reasons:
                    blocks = build_block_shear_area_plans(
                        resolve_block_shear_paths(resolved),
                        resolved,
                        unit,
                        thickness,
                        tuple(BoltHoleSource(b.id, standard) for b in bolts),
                    )
                native_mappings = tuple(
                    record.mapping
                    for h in owner_holes
                    for record in codes
                    if record.shaft_id == h.shaft_id
                    and record.owner_id == owner
                    and (
                        chord
                        or record.physical_element_id.startswith(
                            "BOTTOM" if side == "NEG" else "TOP"
                        )
                    )
                )
                if native_mappings:
                    direction = MaterialDirection(native_mappings[0].direction_family.value)
                    first = resolve_first_row_geometry(
                        resolved, unit, diameter, direction, PultrudedElementClassification.SHAPE
                    )
                plans.append(
                    DCTNPlanePlan(
                        owner,
                        group_id,
                        member.slot,
                        member.section.form,
                        thickness,
                        force,
                        resolved,
                        first,
                        blocks,
                        tuple(reasons),
                        direction,
                        native_mappings,
                    )
                )
    return tuple(plans)
