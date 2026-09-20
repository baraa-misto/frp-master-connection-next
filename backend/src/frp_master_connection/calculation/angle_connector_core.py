"""CS7-RC2 material-neutral geometry and exact local interface-wrench transport.

All vectors are expressed in the connector A/B/C basis, never a material basis.
No resistance provider, property, source package, or factor enters this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction

from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.fingerprint import _canonicalize
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.member_profile import AngleProfileDimensions

CORE_METHOD = "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1"
TRANSPORT_METHOD = "EXACT_ANGLE_CONNECTOR_INTERFACE_WRENCH_TRANSPORT_RC1"
HANDOFF_METHOD = "EXACT_ANGLE_CONNECTOR_SUPPORT_HANDOFF_RC1"
EXTERNAL_DISTRIBUTION = "FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED"
Decimal3 = tuple[Decimal, Decimal, Decimal]
Rational3 = tuple[Fraction, Fraction, Fraction]


def angle_fingerprint(value: object) -> str:
    """Reuse the established canonical dimensional serialization, without an envelope."""
    raw = json.dumps(
        _canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def exact_decimal(value: Fraction) -> Decimal:
    """Exactly render finite-decimal algebra; reject a nonterminating transport result."""
    with localcontext() as context:
        context.prec = len(str(abs(value.numerator))) + len(str(value.denominator)) + 100
        result = Decimal(value.numerator) / Decimal(value.denominator)
    if Fraction(result) != value:
        raise ValueError("Exact transport cannot round a nonterminating result.")
    return result


def components(vector: ExactQuantityVector3D) -> Rational3:
    """Canonical SI components; existing unit conversions are the unit authority."""
    return (
        Fraction(vector.x.canonical_magnitude),
        Fraction(vector.y.canonical_magnitude),
        Fraction(vector.z.canonical_magnitude),
    )


def quantity_vector(values: Rational3, unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity(exact_decimal(v), unit) for v in values))


def _cross(left: Rational3, right: Rational3) -> Rational3:
    a, b, c = left
    x, y, z = right
    return b * z - c * y, c * x - a * z, a * y - b * x


def _require_vector(vector: ExactQuantityVector3D, dimension: Dimension) -> None:
    if not isinstance(vector, ExactQuantityVector3D) or vector.x.dimension is not dimension:
        raise ValueError(f"Expected an exact {dimension.value} vector.")


@dataclass(frozen=True, slots=True)
class AngleConnectorGeometry:
    length: PhysicalQuantity
    member_leg: PhysicalQuantity
    support_leg: PhysicalQuantity
    thickness: PhysicalQuantity
    inside_radius: PhysicalQuantity
    # Actual cutbacks at the two extrusion ends intersecting the continuous heel.
    heel_end_reliefs: tuple[PhysicalQuantity, PhysicalQuantity]

    def __post_init__(self) -> None:
        if not isinstance(self.heel_end_reliefs, tuple) or len(self.heel_end_reliefs) != 2:
            raise ValueError("Specify both immutable physical heel-end cutbacks.")
        values = (
            self.length,
            self.member_leg,
            self.support_leg,
            self.thickness,
            self.inside_radius,
            *self.heel_end_reliefs,
        )
        if any(
            not isinstance(q, PhysicalQuantity) or q.dimension is not Dimension.LENGTH
            for q in values
        ):
            raise ValueError("Angle dimensions and physical cutbacks must be lengths.")
        length, member, support, thickness, radius, start, end = (
            Fraction(q.canonical_magnitude) for q in values
        )
        AngleProfileDimensions(*(exact_decimal(v) for v in (length, member, support, thickness)))
        if radius < 0 or radius + thickness >= min(member, support):
            raise ValueError("Inside heel radius must fit both physical legs.")
        if min(start, end) < 0 or start + end >= length:
            raise ValueError("Physical end cutbacks require a positive continuous heel length.")


@dataclass(frozen=True, slots=True)
class AngleConnectorFrame:
    a: Decimal3
    b: Decimal3
    c: Decimal3

    def __post_init__(self) -> None:
        for axis in (self.a, self.b, self.c):
            if (
                not isinstance(axis, tuple)
                or len(axis) != 3
                or any(not isinstance(v, Decimal) or not v.is_finite() for v in axis)
            ):
                raise ValueError("Frame axes require immutable finite Decimal triples.")
        a, b, c = (tuple(Fraction(v) for v in axis) for axis in (self.a, self.b, self.c))
        if (
            any(sum(v * v for v in axis) != 1 for axis in (a, b, c))
            or (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )
            != c
        ):
            raise ValueError("An exact orthonormal right-handed A x B = C frame is required.")


@dataclass(frozen=True, slots=True)
class AngleWrench:
    reference: ExactQuantityVector3D
    force: ExactQuantityVector3D
    moment: ExactQuantityVector3D

    def __post_init__(self) -> None:
        _require_vector(self.reference, Dimension.LENGTH)
        _require_vector(self.force, Dimension.FORCE)
        _require_vector(self.moment, Dimension.MOMENT)


def shift_angle_wrench(wrench: AngleWrench, target: ExactQuantityVector3D) -> AngleWrench:
    """M_Q = M_P + (r_P-r_Q) x F, with exact finite-decimal algebra."""
    _require_vector(target, Dimension.LENGTH)
    r, q = components(wrench.reference), components(target)
    offset = (r[0] - q[0], r[1] - q[1], r[2] - q[2])
    cross = _cross(offset, components(wrench.force))
    moment = components(wrench.moment)
    return AngleWrench(
        target,
        wrench.force,
        quantity_vector(
            (moment[0] + cross[0], moment[1] + cross[1], moment[2] + cross[2]),
            Unit.N_MM,
        ),
    )


@dataclass(frozen=True, slots=True)
class AngleCoreRequest:
    geometry: AngleConnectorGeometry
    frame: AngleConnectorFrame
    member_action: AngleWrench
    support_reference: ExactQuantityVector3D

    def __post_init__(self) -> None:
        if (
            not isinstance(self.geometry, AngleConnectorGeometry)
            or not isinstance(self.frame, AngleConnectorFrame)
            or not isinstance(self.member_action, AngleWrench)
        ):
            raise TypeError("Core requires immutable geometry, frame, and full member wrench.")
        _require_vector(self.support_reference, Dimension.LENGTH)


@dataclass(frozen=True, slots=True)
class AngleCoreResult:
    request: AngleCoreRequest
    heel: AngleWrench
    connector_on_support: AngleWrench
    support_on_connector: AngleWrench
    equilibrium: AngleWrench
    geometry_fingerprint: str
    reference_fingerprint: str
    fingerprint: str
    method: str = CORE_METHOD
    transport_method: str = TRANSPORT_METHOD
    handoff_method: str = HANDOFF_METHOD
    support_distribution_status: str = EXTERNAL_DISTRIBUTION


def resolve_angle_connector(request: AngleCoreRequest) -> AngleCoreResult:
    """Resolve one neutral angle; providers cannot change its physical demand identity."""
    zero = (Fraction(0), Fraction(0), Fraction(0))
    heel_reference = quantity_vector(zero, Unit.MM)
    heel = shift_angle_wrench(request.member_action, heel_reference)
    handoff = shift_angle_wrench(request.member_action, request.support_reference)
    f, m = components(handoff.force), components(handoff.moment)
    reaction = AngleWrench(
        handoff.reference,
        quantity_vector((-f[0], -f[1], -f[2]), Unit.N),
        quantity_vector((-m[0], -m[1], -m[2]), Unit.N_MM),
    )
    reaction_at_heel = shift_angle_wrench(reaction, heel_reference)
    hf, hm = components(heel.force), components(heel.moment)
    rf, rm = components(reaction_at_heel.force), components(reaction_at_heel.moment)
    equilibrium = AngleWrench(
        heel_reference,
        quantity_vector((hf[0] + rf[0], hf[1] + rf[1], hf[2] + rf[2]), Unit.N),
        quantity_vector((hm[0] + rm[0], hm[1] + rm[1], hm[2] + rm[2]), Unit.N_MM),
    )
    if components(equilibrium.force) != zero or components(equilibrium.moment) != zero:
        raise ArithmeticError("Exact connector equilibrium failed; residuals were not suppressed.")
    geometry_fp = angle_fingerprint(request.geometry)
    reference_fp = angle_fingerprint(
        (request.frame, request.member_action.reference, request.support_reference, heel_reference)
    )
    fingerprint = angle_fingerprint(
        (
            CORE_METHOD,
            TRANSPORT_METHOD,
            HANDOFF_METHOD,
            request,
            heel,
            handoff,
            reaction,
            equilibrium,
        )
    )
    return AngleCoreResult(
        request, heel, handoff, reaction, equilibrium, geometry_fp, reference_fp, fingerprint
    )
