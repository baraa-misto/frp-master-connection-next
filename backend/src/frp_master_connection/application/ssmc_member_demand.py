"""Native normal-resultant subproblem; full local transfer remains unresolved.

Slice 6's shear input is referenced to a shear center, not the SSMC web-end
reference. Its assumed shear-center force path is not silently substituted here.
The native subproblem therefore decomposes axial/major bending only. The full
six-component physical end wrench is retained alongside that bounded primitive.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.application.ssmc_geometry import SSMCMemberGeometry
from frp_master_connection.calculation.angle_connector_core import AngleWrench, exact_decimal
from frp_master_connection.calculation.channel_moment_resultants import (
    ChannelMomentActionInput,
    ChannelMomentCalculationInput,
    ChannelMomentComponentResultants,
    ChannelMomentSectionInput,
    calculate_channel_moment_component_resultants,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentComponentResultants,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
)
from frp_master_connection.domain.ssmc import StringerForm, StringerSection


@dataclass(frozen=True, slots=True)
class SSMCMemberTransferDemand:
    member: str
    complete_end_wrench: AngleWrench
    native_normal_resultants: WIMomentComponentResultants | ChannelMomentComponentResultants
    primitive_scope: str = "AXIAL_AND_MAJOR_BENDING_ONLY"
    retained_unresolved_scope: str = "FULL_SHEAR_SECONDARY_MOMENTS_AND_LOCAL_FLANGE_WEB_TRANSFER"
    status: str = "SSMC_MEMBER_FLANGE_WEB_TRANSFER_NOT_QUALIFIED"


def member_transfer_demand(
    section: StringerSection, geometry: SSMCMemberGeometry, wrench: AngleWrench
) -> SSMCMemberTransferDemand:
    longitudinal = geometry.material_longitudinal
    depth = geometry.material_depth
    # Positive native structural M means tension at positive material depth.
    # The corresponding physical couple is -(longitudinal x depth).
    cross_y = longitudinal.z * depth.x - longitudinal.x * depth.z
    axial = sum(
        Fraction(q.to(Unit.N).magnitude) * Fraction(str(v))
        for q, v in zip(
            (wrench.force.x, wrench.force.y, wrench.force.z),
            (longitudinal.x, longitudinal.y, longitudinal.z),
            strict=True,
        )
    )
    major = -Fraction(wrench.moment.y.to(Unit.N_MM).magnitude) * Fraction(str(cross_y))
    n = PhysicalQuantity(exact_decimal(Fraction(axial)), Unit.N)
    m = PhysicalQuantity(exact_decimal(major), Unit.N_MM)
    force_zero = PhysicalQuantity(Decimal(0), Unit.N)
    moment_zero = PhysicalQuantity(Decimal(0), Unit.N_MM)
    dimensions = (section.depth, section.width, section.web_thickness, section.flange_thickness)
    native: WIMomentComponentResultants | ChannelMomentComponentResultants
    if section.form is StringerForm.W_I:
        native = calculate_wi_moment_component_resultants(
            WIMomentCalculationInput(
                WIMomentSectionInput(*dimensions),
                WIMomentActionInput(n, force_zero, m, force_zero, moment_zero, moment_zero),
            )
        )
    else:
        native = calculate_channel_moment_component_resultants(
            ChannelMomentCalculationInput(
                ChannelMomentSectionInput(*dimensions),
                ChannelMomentActionInput(n, force_zero, m, force_zero, moment_zero, moment_zero),
            )
        )
    return SSMCMemberTransferDemand(geometry.owner, wrench, native)
