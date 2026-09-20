"""Exact three-component demand, never inferred Channel/row/contact response."""

from dataclasses import dataclass
from fractions import Fraction

from frp_master_connection.calculation.angle_column_base_response import sum_wrenches
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.dctn3b import DCTN3BRequest
from frp_master_connection.domain.dctn_geometry import DCTNGeometry
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, DCTNSection

ZERO: Rational3 = (Fraction(0), Fraction(0), Fraction(0))


@dataclass(frozen=True, slots=True)
class ShearPresentation:
    Qp_label: str
    Qq_label: str
    major_component: str | None
    minor_component: str | None
    I_p: Fraction | None
    I_q: Fraction | None


def shear_presentation(section: DCTNSection) -> ShearPresentation:
    """Nominal section integrals for labels only, never new resistance authority."""
    if section.form is DCTNForm.W_I:
        return ShearPresentation("Minor shear", "Major shear", "Qq", "Qp", None, None)
    b, d, t = (
        Fraction(q.canonical_magnitude) for q in (section.width, section.depth, section.wall_or_web)
    )
    ip, iq = b * d**3 / 12, d * b**3 / 12
    if section.form is DCTNForm.RHS:
        ip -= (b - 2 * t) * (d - 2 * t) ** 3 / 12
        iq -= (d - 2 * t) * (b - 2 * t) ** 3 / 12
    if ip == iq:
        return ShearPresentation("Shear p (equal axes)", "Shear q (equal axes)", None, None, ip, iq)
    if ip > iq:
        return ShearPresentation("Minor shear", "Major shear", "Qq", "Qp", ip, iq)
    return ShearPresentation("Major shear", "Minor shear", "Qp", "Qq", ip, iq)


def member_force(u: Rational3, p: Rational3, q: Rational3, actions: Rational3) -> Rational3:
    return tuple(
        sum(a * axis[i] for a, axis in zip(actions, (u, p, q), strict=True)) for i in range(3)
    )  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ReferencedDemand:
    reference_id: str
    wrench: AngleWrench
    interpretation: str = "WHOLE_MEMBER_DEMAND_AT_REFERENCE_NOT_ALLOCATED_RESPONSE"


@dataclass(frozen=True, slots=True)
class MemberDemand:
    member_id: str
    u: Rational3
    p: Rational3
    q: Rational3
    action_components_N: Rational3
    presentation: ShearPresentation
    at_member_end: AngleWrench
    transported: tuple[ReferencedDemand, ...]


@dataclass(frozen=True, slots=True)
class DCTN3BDemand:
    status: str
    members: tuple[MemberDemand, ...]
    total_at_node: AngleWrench
    fingerprint: str


def calculate_dctn3b_demand(
    value: DCTN3BRequest,
    geometry: DCTNGeometry,
    channel_references: tuple[tuple[str, ExactQuantityVector3D], ...],
) -> DCTN3BDemand:
    """Use native placed frames and native quantity transport, including native unit paths."""
    node = quantity_vector(ZERO, value.length_unit)
    members = []
    for source in value.members:
        native = next(m for m in geometry.members if m.physical_id == source.slot)
        actions: Rational3 = tuple(
            Fraction(x.canonical_magnitude) for x in (source.P, source.Qp, source.Qq)
        )  # type: ignore[assignment]
        force = member_force(native.u, native.v, native.w, actions)
        wrench = AngleWrench(
            quantity_vector(native.start, value.length_unit),
            quantity_vector(force, Unit.N),
            quantity_vector(ZERO, Unit.N_MM),
        )
        refs = [("NODE", node), *channel_references]
        for row in geometry.rows:
            if row.member_id == source.slot:
                refs.append(
                    (
                        f"{source.slot}:ROW_{row.row}:AXIS",
                        quantity_vector(row.axis_point, value.length_unit),
                    )
                )
                refs.append(
                    (
                        f"{source.slot}:ROW_{row.row}:NEGATIVE",
                        quantity_vector(row.negative_point, value.length_unit),
                    )
                )
                refs.append(
                    (
                        f"{source.slot}:ROW_{row.row}:POSITIVE",
                        quantity_vector(row.positive_point, value.length_unit),
                    )
                )
        members.append(
            MemberDemand(
                source.slot,
                native.u,
                native.v,
                native.w,
                actions,
                shear_presentation(source.section),
                wrench,
                tuple(
                    ReferencedDemand(name, shift_angle_wrench(wrench, ref)) for name, ref in refs
                ),
            )
        )
    total = sum_wrenches(tuple(m.at_member_end for m in members), node)
    return DCTN3BDemand(
        "CALCULATED", tuple(members), total, dctn_fingerprint((value, tuple(members), total))
    )
