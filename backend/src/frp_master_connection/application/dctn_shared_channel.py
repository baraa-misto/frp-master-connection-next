"""Complete Channel-hole review; no substitution of a net vector for differing actions."""

from dataclasses import dataclass, replace

from frp_master_connection.calculation.block_shear_planning import (
    BoltHoleSource,
    build_block_shear_area_plans,
)
from frp_master_connection.calculation.multirow import (
    PultrudedElementClassification,
    resolve_first_row_geometry,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    create_standard_hole,
)
from frp_master_connection.domain.dctn_geometry import DCTNPlanePlan
from frp_master_connection.domain.double_channel_truss_node import DCTNRequest
from frp_master_connection.geometry.multirow import (
    GeneralBoltGroup,
    MultiRowGeometry,
    MultiRowGeometryTolerance,
    resolve_block_shear_paths,
    resolve_multirow_geometry,
)


@dataclass(frozen=True, slots=True)
class DCTNSharedChannelReview:
    owner_id: str
    hole_ids: tuple[str, ...]
    group_ids: tuple[str, ...]
    candidate_plans: tuple[DCTNPlanePlan, ...]
    common_force_plan: DCTNPlanePlan | None
    reasons: tuple[str, ...]


def review_dctn_shared_channels(
    request: DCTNRequest, plans: tuple[DCTNPlanePlan, ...]
) -> tuple[DCTNSharedChannelReview, ...]:
    """Retain native accepted/rejected paths over every physical Channel hole.

    Every distinct load direction is reviewed against the COMPLETE web hole set.
    Numerical combined execution requires a common direction, native rectangular
    pattern and common lap/pitch authority. Opposing/nonparallel member actions
    are never replaced by their net resultant to obtain a fictitious path demand.
    """
    reviews: list[DCTNSharedChannelReview] = []
    standard = create_standard_hole(
        request.fastener.diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
    )
    tolerance = MultiRowGeometryTolerance(
        float(PhysicalQuantity.of(".000001", Unit.IN).to(request.length_unit).magnitude)
    )
    for owner in ("CHORD_NEG", "CHORD_POS"):
        groups = tuple(p for p in plans if p.owner_id == owner)
        if not groups:
            continue
        bolts = tuple(b for p in groups for b in p.geometry.group.bolts)
        if len({b.id for b in bolts}) != len(bolts):
            raise ValueError("DCTN complete Channel review cannot duplicate physical holes")
        candidates: list[DCTNPlanePlan] = []
        directions = tuple(dict.fromkeys(p.force_direction for p in groups))
        for ordinal, direction in enumerate(directions):
            original = next(p for p in groups if p.force_direction == direction)
            group = GeneralBoltGroup(
                owner + ":ALL:" + str(ordinal), owner + ":WEB", len(bolts), len(bolts), bolts
            )
            geometry: MultiRowGeometry | None = None
            # Ask the native grouping validator which declaration matches. Do
            # not copy its float projection/clustering algorithm into DCTN.
            for count in range(1, len(bolts) + 1):
                try:
                    geometry = resolve_multirow_geometry(
                        replace(group, declared_row_count=count),
                        original.geometry.boundary,
                        direction,
                        tolerance,
                    )
                    break
                except ValueError as error:
                    if str(error) != (
                        "Declared row count does not match force-axis physical row resolution."
                    ):
                        raise
            if geometry is None:
                raise ValueError("DCTN complete Channel grouping could not be resolved")
            first = resolve_first_row_geometry(
                geometry,
                request.length_unit,
                request.fastener.diameter,
                original.material_direction,
                PultrudedElementClassification.SHAPE,
            )
            blocks = (
                build_block_shear_area_plans(
                    resolve_block_shear_paths(geometry),
                    geometry,
                    request.length_unit,
                    original.thickness,
                    tuple(BoltHoleSource(b.id, standard) for b in bolts),
                )
                if standard.hole_diameter == request.fastener.hole_diameter
                else None
            )
            candidates.append(
                replace(
                    original,
                    group_id="ALL:" + str(ordinal),
                    geometry=geometry,
                    first_row=first,
                    block_paths=blocks,
                    native_bolt_mappings=tuple(m for p in groups for m in p.native_bolt_mappings),
                )
            )
        common = candidates[0]
        classification = common.geometry.classification
        supported = (
            len(directions) == 1
            and len({p.incoming_form for p in groups}) == 1
            and common.force_direction[0] * common.force_direction[1] == 0
            and not common.reasons
            and len(common.geometry.rows) <= 3
            and classification.nonstaggered
            and classification.constant_pitch
            and classification.constant_gauge
            and classification.equal_bolts_per_row
            and classification.same_bolt_identity
            and classification.same_hole_identity
        )
        reviews.append(
            DCTNSharedChannelReview(
                owner,
                tuple(b.id for b in bolts),
                tuple(p.group_id for p in groups),
                tuple(candidates),
                common if supported and len(groups) > 1 else None,
                ("DCTN_SHARED_CHORD_CROSS_GROUP_PATH_NOT_QUALIFIED",)
                if len(groups) > 1 and not supported
                else (),
            )
        )
    return tuple(reviews)
