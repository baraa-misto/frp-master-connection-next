"""Versioned relative placement; the historical DCTN-2 contract is not reinterpreted."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.calculation.angle_connector_core import exact_decimal
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNChannel,
    DCTNFastener,
    DCTNMember,
    DCTNPattern,
    DCTNRequest,
    DCTNSection,
    default_dctn_request,
    require_quantity,
)

CONTRACT = "DCTN-3B-RC1"
DATUM = "CHANNEL_PAIR_LOWER_CLEAR_WEB"
Q = PhysicalQuantity


def relative_start(channel: DCTNChannel, station: Q, height: Q, unit: Unit) -> tuple[Q, Q, Q]:
    """Use the current nominal native Channel flange boundary, not a capacity edge."""
    for value in (station, height):
        require_quantity(value, Dimension.LENGTH)
    depth = Fraction(channel.depth.to(unit).magnitude)
    flange = Fraction(channel.flange_thickness.to(unit).magnitude)
    z = -depth / 2 + flange + Fraction(height.to(unit).magnitude)
    return station.to(unit), Q.of(0, unit), Q.of(exact_decimal(z), unit)


@dataclass(frozen=True, slots=True)
class DCTN3BMember:
    slot: str
    section: DCTNSection
    chord_station: Q
    end_center_above_lower_web: Q
    inclination_deg: Decimal
    P: Q
    Qp: Q
    Qq: Q
    pattern: DCTNPattern
    material_source_reference: str = ""
    local_path_source_reference: str = ""
    material_id: str = "ICE_LOCKED_PULTRUDED_FRP"

    def __post_init__(self) -> None:
        for value in (self.chord_station, self.end_center_above_lower_web):
            require_quantity(value, Dimension.LENGTH)
        for value in (self.P, self.Qp, self.Qq):
            require_quantity(value, Dimension.FORCE)
        # Delegate all inherited member/profile/angle/material validation verbatim.
        self.at_start((Q.of(0, Unit.IN),) * 3)

    def at_start(self, start: tuple[Q, Q, Q]) -> DCTNMember:
        return DCTNMember(
            self.slot,
            self.section,
            start,
            self.inclination_deg,
            self.P,
            self.pattern,
            self.material_source_reference,
            self.local_path_source_reference,
            self.material_id,
        )


@dataclass(frozen=True, slots=True)
class DCTN3BRequest:
    request_id: str
    unit_system: str
    length_unit: Unit
    arrangement: DCTNArrangement
    channel: DCTNChannel
    members: tuple[DCTN3BMember, ...]
    fastener: DCTNFastener
    shared_channel_source_reference: str = ""
    placement_datum: str = DATUM
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT:
            raise ValueError("DCTN_PLACEMENT_CONTRACT_CONFLICT")
        if self.placement_datum != DATUM:
            raise ValueError("DCTN_PLACEMENT_DATUM_NOT_SUPPORTED")
        self.legacy_geometry_request()

    def legacy_geometry_request(self) -> DCTNRequest:
        """P is retained for the exact axial branch; callers must not solve shear with it."""
        return DCTNRequest(
            self.request_id,
            self.unit_system,
            self.length_unit,
            self.arrangement,
            self.channel,
            tuple(
                m.at_start(
                    relative_start(
                        self.channel,
                        m.chord_station,
                        m.end_center_above_lower_web,
                        self.length_unit,
                    )
                )
                for m in self.members
            ),
            self.fastener,
            self.shared_channel_source_reference,
        )

    @property
    def has_transverse(self) -> bool:
        return any(m.Qp.magnitude != 0 or m.Qq.magnitude != 0 for m in self.members)


def migrate_dctn2(value: DCTNRequest) -> DCTN3BRequest:
    """Explicit lossless native-unit migration only; off-midgap states stay historical."""
    unit = value.length_unit
    lower = -Fraction(value.channel.depth.to(unit).magnitude) / 2
    lower += Fraction(value.channel.flange_thickness.to(unit).magnitude)
    members = []
    for member in value.members:
        if member.start[1].magnitude != 0:
            raise ValueError("DCTN_LEGACY_PLACEMENT_NOT_MIGRATABLE")
        height = Fraction(member.start[2].to(unit).magnitude) - lower
        zero = Q.of(0, member.axial_force.unit)
        members.append(
            DCTN3BMember(
                member.slot,
                member.section,
                member.start[0],
                Q.of(exact_decimal(height), unit),
                member.inclination_deg,
                member.axial_force,
                zero,
                zero,
                member.pattern,
                member.material_source_reference,
                member.local_path_source_reference,
                member.material_id,
            )
        )
    return DCTN3BRequest(
        value.request_id,
        value.unit_system,
        unit,
        value.arrangement,
        value.channel,
        tuple(members),
        value.fastener,
        value.shared_channel_source_reference,
    )


def default_dctn3b_request(
    arrangement: DCTNArrangement = DCTNArrangement.VERTICAL_ONLY,
) -> DCTN3BRequest:
    return migrate_dctn2(default_dctn_request(arrangement))
