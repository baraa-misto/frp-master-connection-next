"""DCTN axial row/side allocation with exact native six-component transport."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    base_fingerprint,
    sum_wrenches,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    exact_decimal,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.channel_moment_resultants import (
    ChannelMomentActionInput,
    ChannelMomentCalculationInput,
    ChannelMomentSectionInput,
    ChannelMomentSectionProperties,
    calculate_channel_moment_component_resultants,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.multirow import (
    ConnectedMaterialPair,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.dctn_geometry import (
    DCTNGeometry,
    DCTNShaft,
)
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, DCTNRequest
from frp_master_connection.domain.member_profile import profile_section_geometry_adapter

METHOD = "DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1"
F = Fraction
D = Decimal


def row_fractions(count: int, across: int = 1, *, staggered: bool = False) -> tuple[Decimal, ...]:
    if across != 1:
        raise ValueError("DCTN_BOLTS_ACROSS_ROW_OUTSIDE_RC1_SCOPE")
    if count not in (1, 2, 3):
        raise ValueError("DCTN_ROW_COUNT_OUTSIDE_RC1_SCOPE")
    if staggered:
        raise ValueError("DCTN_STAGGERED_BOLTS_NOT_SUPPORTED_IN_RC1")
    return (D(1),) if count == 1 else prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, count)


def require_axial_action(local_force: Rational3, local_moment: Rational3) -> None:
    if local_force[1:] != (F(0), F(0)) or local_moment != ZERO:
        raise ValueError("DCTN_MEMBER_ACTION_OUTSIDE_AXIAL_TRUSS_SCOPE")


@dataclass(frozen=True, slots=True)
class DCTNSymmetry:
    identical_channel_profile_material_source: bool
    mirrored_channel_placement: bool
    incoming_centered: bool
    identical_hardware: bool
    wi_centrosymmetric: bool
    no_side_specific_response_state: bool

    @property
    def qualified(self) -> bool:
        return all(
            (
                self.identical_channel_profile_material_source,
                self.mirrored_channel_placement,
                self.incoming_centered,
                self.identical_hardware,
                self.wi_centrosymmetric,
                self.no_side_specific_response_state,
            )
        )


def require_symmetry(proof: DCTNSymmetry) -> None:
    if not proof.wi_centrosymmetric:
        raise ValueError("DCTN_WI_ECCENTRICITY_RESPONSE_NOT_QUALIFIED")
    if not proof.qualified:
        raise ValueError("DCTN_CHANNEL_SYMMETRY_RESPONSE_NOT_QUALIFIED")


@dataclass(frozen=True, slots=True)
class DCTNRowResponse:
    member_id: str
    row: int
    row_fraction: Decimal
    signed_row_force: PhysicalQuantity
    side_fraction: Decimal
    negative_at_bolt: AngleWrench
    positive_at_bolt: AngleWrench
    negative_at_member_axis: AngleWrench
    positive_at_member_axis: AngleWrench
    pair_at_member_axis: AngleWrench
    negative_at_channel: AngleWrench
    positive_at_channel: AngleWrench
    member_force_closes: bool
    member_moment_closes: bool


@dataclass(frozen=True, slots=True)
class DCTNShaftResponse:
    bolt_id: str
    layer_owners: tuple[str, ...]
    signed_layer_transfers: tuple[PhysicalQuantity, ...]
    signed_cuts: tuple[PhysicalQuantity, ...]
    shear_plane_demands: tuple[PhysicalQuantity, ...]
    terminal_residual: PhysicalQuantity
    capacity_multiplier: None = None
    physical_capacity_report_count: int = 1


def shaft_response(shaft: DCTNShaft, row_force: PhysicalQuantity) -> DCTNShaftResponse:
    p = F(row_force.canonical_magnitude)
    transfers: tuple[Fraction, ...]
    planes: tuple[Fraction, ...]
    if shaft.side != "THROUGH":
        transfers = (p / 2, -p / 2)
        planes = (abs(p) / 2,)
    elif shaft.free_span:
        transfers = (p / 2, -p / 2, -p / 2, p / 2)
        planes = (abs(p) / 2, abs(p) / 2)
    else:
        transfers = (p / 2, -p, p / 2)
        planes = (abs(p) / 2, abs(p) / 2)
    return prove_shaft_transfers(shaft.bolt_id, shaft.layer_owners, transfers, planes)


def prove_shaft_transfers(
    bolt_id: str,
    owners: tuple[str, ...],
    transfers: tuple[Fraction, ...],
    plane_demands: tuple[Fraction, ...],
) -> DCTNShaftResponse:
    cuts: list[Fraction] = []
    total = F(0)
    for transfer in transfers:
        total += transfer
        cuts.append(total)
    if len(owners) != len(transfers) or total != 0:
        raise ValueError("DCTN_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED")
    # Plane identity is physical, not inferred by discarding zero-valued cuts.
    # Four layers include the unfilled RHS cavity between cuts 0 and 2.
    # Three layers are the single continuous solid region; two are one W/I lap.
    if len(owners) not in (2, 3, 4):
        raise ValueError("DCTN_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED")
    plane_indices = (0, 2) if len(owners) == 4 else tuple(range(len(owners) - 1))
    actual = tuple(abs(cuts[index]) for index in plane_indices)
    if actual != plane_demands:
        raise ValueError("DCTN_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED")

    def q(value: Fraction) -> PhysicalQuantity:
        return PhysicalQuantity.of(exact_decimal(value), Unit.N)

    return DCTNShaftResponse(
        bolt_id,
        owners,
        tuple(q(x) for x in transfers),
        tuple(q(x) for x in cuts),
        tuple(q(x) for x in plane_demands),
        q(total),
    )


def require_unique_shafts(shafts: tuple[DCTNShaftResponse, ...]) -> None:
    identities = tuple(s.bolt_id for s in shafts)
    if len(set(identities)) != len(identities):
        raise ValueError("DCTN_COMMON_SHAFT_DUPLICATE_IDENTITY")


@dataclass(frozen=True, slots=True)
class DCTNChannelResponse:
    member_id: str
    engineering_reference: ExactQuantityVector3D
    contributions: tuple[AngleWrench, ...]
    total: AngleWrench
    hole_ids: tuple[str, ...]
    group_ids: tuple[str, ...]
    global_member_design_evaluated: bool = False


@dataclass(frozen=True, slots=True)
class DCTNResponse:
    status: str
    reasons: tuple[str, ...]
    symmetry: DCTNSymmetry
    channel_section_authority: ChannelMomentSectionProperties
    rows: tuple[DCTNRowResponse, ...]
    shafts: tuple[DCTNShaftResponse, ...]
    channels: tuple[DCTNChannelResponse, ...]
    fingerprint: str
    method: str = METHOD


def channel_section(value: DCTNRequest) -> ChannelMomentSectionProperties:
    channel = value.channel
    force = PhysicalQuantity.of(0, Unit.N)
    moment = PhysicalQuantity.of(0, Unit.N_MM)
    return calculate_channel_moment_component_resultants(
        ChannelMomentCalculationInput(
            ChannelMomentSectionInput(
                channel.depth, channel.flange_width, channel.web_thickness, channel.flange_thickness
            ),
            ChannelMomentActionInput(force, force, moment, force, moment, moment),
        )
    ).section_properties


def _row_pair(
    member_id: str,
    row: int,
    fraction: Decimal,
    p: Fraction,
    axis: Rational3,
    negative: Rational3,
    positive: Rational3,
    start: Rational3,
    unit: Unit,
    channel_references: tuple[ExactQuantityVector3D, ExactQuantityVector3D],
) -> DCTNRowResponse:
    side_force: Rational3 = tuple(p * x / 2 for x in axis)  # type: ignore[assignment]
    at_negative = AngleWrench(
        quantity_vector(negative, unit),
        quantity_vector(side_force, Unit.N),
        quantity_vector(ZERO, Unit.N_MM),
    )
    at_positive = AngleWrench(
        quantity_vector(positive, unit),
        quantity_vector(side_force, Unit.N),
        quantity_vector(ZERO, Unit.N_MM),
    )
    reference = quantity_vector(start, unit)
    neg_axis = shift_angle_wrench(at_negative, reference)
    pos_axis = shift_angle_wrench(at_positive, reference)
    pair = sum_wrenches((neg_axis, pos_axis), reference)
    expected = tuple(p * x for x in axis)
    force_closes = components(pair.force) == expected
    moment_closes = components(pair.moment) == ZERO
    if not force_closes or not moment_closes:
        raise ValueError("DCTN_WI_ECCENTRICITY_RESPONSE_NOT_QUALIFIED")
    return DCTNRowResponse(
        member_id,
        row,
        fraction,
        PhysicalQuantity.of(exact_decimal(p), Unit.N),
        D(".5"),
        at_negative,
        at_positive,
        neg_axis,
        pos_axis,
        pair,
        shift_angle_wrench(at_negative, channel_references[0]),
        shift_angle_wrench(at_positive, channel_references[1]),
        force_closes,
        moment_closes,
    )


def calculate_dctn_response(value: DCTNRequest, geometry: DCTNGeometry) -> DCTNResponse:
    section = channel_section(value)
    natives = {m.physical_id: m for m in geometry.members}
    # Matching channels and hardware are single canonical request records, never side copies.
    wi_pairs = all(
        all(
            a + b == 2 * c
            for a, b, c in zip(row.negative_point, row.positive_point, row.axis_point, strict=True)
        )
        for row in geometry.rows
    )
    proof = DCTNSymmetry(
        natives["CHORD_NEG"].profile.dimensions == natives["CHORD_POS"].profile.dimensions,
        natives["CHORD_NEG"].start[1] == -natives["CHORD_POS"].start[1],
        all(m.start[1].canonical_magnitude == 0 for m in value.members),
        True,
        wi_pairs,
        True,
    )
    reasons = list(geometry.reasons)
    members_by_id = {member.slot: member for member in value.members}
    for shaft in geometry.shafts:
        member = members_by_id[shaft.member_id]
        if member.section.form is DCTNForm.W_I and (
            shaft.side not in {"NEG", "POS"}
            or shaft.native_full_through_core is not None
            or len(shaft.layer_owners) != 2
        ):
            reasons.append("DCTN_WI_FLANGE_PATH_NOT_QUALIFIED")
    # Native construction datum and the engineering centroid are distinct.
    # Reject a changed placement/datum instead of using the expected centroid
    # with an unrelated physical Channel.
    for sign, identity in ((-1, "CHORD_NEG"), (1, "CHORD_POS")):
        native = natives[identity]
        adapter = profile_section_geometry_adapter(native.profile)
        offset = native.placement.section_offset
        expected_start = (
            -F(value.channel.length.to(value.length_unit).magnitude) / 2,
            sign * F(geometry.gap) / 2,
            F(0),
        )
        if (
            native.profile != value.channel.profile(identity, value.length_unit)
            or native.start != expected_start
            or native.u != (F(1), F(0), F(0))
            or native.v != (F(0), F(sign), F(0))
            or native.w != (F(0), F(0), F(sign))
            or offset.offset_y != float(adapter.section_datum_offset_y)
            or offset.offset_z != float(adapter.section_datum_offset_z)
        ):
            reasons.append("DCTN_CHANNEL_REFERENCE_NOT_QUALIFIED")
    try:
        require_symmetry(proof)
    except ValueError as error:
        reasons.append(str(error))
    rows: list[DCTNRowResponse] = []
    shafts: list[DCTNShaftResponse] = []
    references = tuple(
        quantity_vector(
            (
                F(0),
                sign
                * (
                    F(geometry.gap) / 2
                    + F(section.channel_centroid_t_absolute.to(value.length_unit).magnitude)
                ),
                F(0),
            ),
            value.length_unit,
        )
        for sign in (-1, 1)
    )
    refs = references[0], references[1]
    if not reasons:
        for member in value.members:
            native = natives[member.slot]
            fractions = row_fractions(
                member.pattern.rows, member.pattern.across, staggered=member.pattern.staggered
            )
            member_rows = tuple(row for row in geometry.rows if row.member_id == member.slot)
            for row_geometry, fraction in zip(member_rows, fractions, strict=True):
                p = F(member.axial_force.canonical_magnitude) * F(fraction)
                result = _row_pair(
                    member.slot,
                    row_geometry.row,
                    fraction,
                    p,
                    native.u,
                    row_geometry.negative_point,
                    row_geometry.positive_point,
                    native.start,
                    value.length_unit,
                    refs,
                )
                rows.append(result)
                shafts.extend(
                    shaft_response(s, result.signed_row_force)
                    for s in geometry.shafts
                    if s.bolt_id in row_geometry.shaft_ids
                )
    require_unique_shafts(tuple(shafts))
    channels = tuple(
        DCTNChannelResponse(
            identity,
            reference,
            tuple(
                row.negative_at_channel if index == 0 else row.positive_at_channel for row in rows
            ),
            sum_wrenches(
                tuple(
                    row.negative_at_channel if index == 0 else row.positive_at_channel
                    for row in rows
                ),
                reference,
            ),
            tuple(h.hole_id for h in geometry.holes if h.owner_id == identity),
            tuple(dict.fromkeys(h.group_id for h in geometry.holes if h.owner_id == identity)),
        )
        for index, (identity, reference) in enumerate(
            zip(("CHORD_NEG", "CHORD_POS"), refs, strict=True)
        )
    )
    return DCTNResponse(
        "UNQUALIFIED" if reasons else "QUALIFIED",
        tuple(dict.fromkeys(reasons)),
        proof,
        section,
        tuple(rows),
        tuple(shafts),
        channels,
        base_fingerprint((METHOD, geometry.fingerprint, section, rows, shafts, channels, reasons)),
    )
