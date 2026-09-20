"""Fixed owner-approved startup inputs; frozen request builders remain unchanged."""

from dataclasses import replace

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseConnector,
    AngleColumnMomentBaseRequest,
    default_angle_column_moment_base_request,
)


def angle_column_workspace_default(
    *, unequal: bool = False, si: bool = False
) -> AngleColumnMomentBaseRequest:
    """Use fixed valid equal-leg startup geometry, not runtime repair or sizing."""
    historical = default_angle_column_moment_base_request(unequal=unequal, si=si)
    if unequal:
        return historical

    def q(value: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(value, Unit.IN).to(Unit.MM if si else Unit.IN)

    def connector(value: AngleBaseConnector) -> AngleBaseConnector:
        angle = value.angle
        return replace(
            value,
            extrusion_center=q("2.75"),
            angle=replace(
                angle,
                geometry=replace(
                    angle.geometry, length=q("5.5"), member_leg=q("4"), support_leg=q("4")
                ),
                member_pattern=replace(angle.member_pattern, along=1, gauge=q("1.25")),
                support_pattern=replace(angle.support_pattern, across=1, along=1),
            ),
        )

    return replace(
        historical,
        column=replace(historical.column, leg_x=q("4"), leg_y=q("4")),
        leg_1=connector(historical.leg_1),
        leg_2=connector(historical.leg_2),
    )
