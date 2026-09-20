"""Slice 8: equal-stiffness, exact-rational in-plane bolt-group wrench demand.

A x B = C. This additive authority transfers a true free moment; it neither
changes Stage 2.5A nor infers a force location. No resistance is evaluated here.
Canonical mechanics use mm, N and N-mm. Unit views and Decimal projections are
interoperability representations, never the equilibrium proof.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from fractions import Fraction

from frp_master_connection.calculation.eccentric_demand import InPlaneQuantityVector
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit

METHOD = "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1"
CONTRACT = "CALCULATION_SLICE_8_RC1"
PROJECTION = "DECIMAL_80_ROUND_HALF_EVEN_FROM_EXACT_RATIONAL"
COMPATIBILITY = "R1_STAGE_25A_MECHANICS_COMPATIBILITY_NOT_DECIMAL_IDENTITY"
ASSUMPTION = "EQUAL_IN_PLANE_TRANSLATIONAL_BOLT_STIFFNESS"
type NumericInput = Decimal | str | int
type Rational2 = tuple[Fraction, Fraction]
type JsonValue = str | bool | list[JsonValue] | dict[str, JsonValue] | None


class WrenchInputError(ValueError):
    """Fail-closed input status; no repaired geometry or fabricated force result."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(status)


@dataclass(frozen=True, slots=True)
class WrenchBolt:
    bolt_id: str
    a: NumericInput
    b: NumericInput


@dataclass(frozen=True, slots=True)
class InPlaneWrenchRequest:
    bolts: tuple[WrenchBolt, ...]
    reference: tuple[NumericInput, NumericInput]
    force_a: NumericInput
    force_b: NumericInput
    moment_c: NumericInput
    length_unit: Unit
    force_unit: Unit
    moment_unit: Unit


def _number(value: object) -> Fraction:
    if isinstance(value, float):
        raise WrenchInputError("INVALID_NUMERIC_TYPE_BINARY_FLOAT_PROHIBITED")
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise WrenchInputError("INVALID_NUMERIC_TYPE")
    try:
        # Even invalid-string handling is independent of the caller's trap settings.
        with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
            parsed = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise WrenchInputError("INVALID_DECIMAL_INPUT") from error
    if not parsed.is_finite():
        raise WrenchInputError("INVALID_NONFINITE_INPUT")
    return Fraction(parsed)


def _scale(unit: Unit, dimension: Dimension) -> Fraction:
    if not isinstance(unit, Unit) or PhysicalQuantity.of(1, unit).dimension is not dimension:
        raise WrenchInputError("INVALID_UNIT_DIMENSION")
    # Reuse the established exact finite unit factors, not a rounded input conversion.
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
        return Fraction(PhysicalQuantity.of(1, unit).canonical_magnitude)


def project_rational(value: Fraction, *, square_root: bool = False) -> Decimal:
    """Project once in a fresh context; squared magnitude is exact before projection."""
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
        result = Decimal(value.numerator) / Decimal(value.denominator)
        return result.sqrt() if square_root else result


@dataclass(frozen=True, slots=True)
class ExactBoltWrenchDemand:
    bolt_id: str
    coordinate: Rational2
    delta: Rational2
    direct: Rational2
    correction: Rational2
    total: Rational2
    magnitude_squared: Fraction


@dataclass(frozen=True, slots=True)
class ExactRecovery:
    target: Fraction
    recovered: Fraction

    @property
    def passed(self) -> bool:
        return self.target == self.recovered


@dataclass(frozen=True, slots=True)
class ExactWrenchProof:
    force_a: ExactRecovery
    force_b: ExactRecovery
    centroid_moment: ExactRecovery
    reference_moment: ExactRecovery

    @property
    def passed(self) -> bool:
        return all(
            record.passed
            for record in (self.force_a, self.force_b, self.centroid_moment, self.reference_moment)
        )


@dataclass(frozen=True, slots=True)
class ProjectedBoltWrenchDemand:
    bolt_id: str
    total_force: InPlaneQuantityVector
    total_force_magnitude: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class ExactWrenchSolution:
    """Fractions expose normalized numerator/denominator; moment units = force x length."""

    length_unit: Unit
    force_unit: Unit
    coordinates: tuple[tuple[str, Rational2], ...]
    reference: Rational2
    force: Rational2
    reference_moment: Fraction
    centroid: Rational2
    polar_sum: Fraction
    centroid_moment: Fraction
    bolts: tuple[ExactBoltWrenchDemand, ...]
    proof: ExactWrenchProof | None

    def in_units(self, length_unit: Unit, force_unit: Unit) -> ExactWrenchSolution:
        """Lossless view conversion, including proof records; no Decimal arithmetic."""
        length = _scale(self.length_unit, Dimension.LENGTH) / _scale(length_unit, Dimension.LENGTH)
        force = _scale(self.force_unit, Dimension.FORCE) / _scale(force_unit, Dimension.FORCE)
        moment = length * force

        def pair(value: Rational2, factor: Fraction) -> Rational2:
            return value[0] * factor, value[1] * factor

        def proof_record(value: ExactRecovery, factor: Fraction) -> ExactRecovery:
            return ExactRecovery(value.target * factor, value.recovered * factor)

        proof = self.proof
        return ExactWrenchSolution(
            length_unit,
            force_unit,
            tuple((identity, pair(point, length)) for identity, point in self.coordinates),
            pair(self.reference, length),
            pair(self.force, force),
            self.reference_moment * moment,
            pair(self.centroid, length),
            self.polar_sum * length**2,
            self.centroid_moment * moment,
            tuple(
                ExactBoltWrenchDemand(
                    bolt.bolt_id,
                    pair(bolt.coordinate, length),
                    pair(bolt.delta, length),
                    pair(bolt.direct, force),
                    pair(bolt.correction, force),
                    pair(bolt.total, force),
                    bolt.magnitude_squared * force**2,
                )
                for bolt in self.bolts
            ),
            None
            if proof is None
            else ExactWrenchProof(
                proof_record(proof.force_a, force),
                proof_record(proof.force_b, force),
                proof_record(proof.centroid_moment, moment),
                proof_record(proof.reference_moment, moment),
            ),
        )

    def projected_bolts(self) -> tuple[ProjectedBoltWrenchDemand, ...]:
        return tuple(
            ProjectedBoltWrenchDemand(
                bolt.bolt_id,
                InPlaneQuantityVector(
                    *(
                        PhysicalQuantity(project_rational(value), self.force_unit)
                        for value in bolt.total
                    )
                ),
                PhysicalQuantity(
                    project_rational(bolt.magnitude_squared, square_root=True), self.force_unit
                ),
            )
            for bolt in self.bolts
        )


def _record(value: object) -> JsonValue:
    if isinstance(value, Fraction):
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _record(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_record(item) for item in value]
    if value is None or isinstance(value, (str, bool)):
        return value
    raise TypeError("Unsupported exact wrench fingerprint record.")


@dataclass(frozen=True, slots=True)
class InPlaneWrenchResult:
    status: str
    solution: ExactWrenchSolution
    fingerprint: str
    method: str = METHOD
    contract: str = CONTRACT
    projection: str = PROJECTION
    compatibility: str = COMPATIBILITY
    assumption: str = ASSUMPTION

    def canonical_json(self) -> str:
        """Authoritative SI rational records, not a display-unit serialization."""
        return json.dumps(
            _record(replace(self, fingerprint="")), sort_keys=True, separators=(",", ":")
        )


def calculate_in_plane_wrench_demand(request: InPlaneWrenchRequest) -> InPlaneWrenchResult:
    """Distribute (F_A,F_B,M_C,R), retaining exact four-identity equilibrium proofs."""
    if not isinstance(request, InPlaneWrenchRequest):
        raise WrenchInputError("INVALID_WRENCH_REQUEST")
    if not isinstance(request.bolts, tuple):
        raise WrenchInputError("INVALID_BOLT_COLLECTION")
    if not request.bolts:
        raise WrenchInputError("INVALID_EMPTY_BOLT_GROUP")
    length = _scale(request.length_unit, Dimension.LENGTH)
    force = _scale(request.force_unit, Dimension.FORCE)
    moment = _scale(request.moment_unit, Dimension.MOMENT)
    points: list[tuple[str, Rational2]] = []
    for bolt in request.bolts:
        if not isinstance(bolt, WrenchBolt):
            raise WrenchInputError("INVALID_BOLT_COORDINATE")
        if not isinstance(bolt.bolt_id, str) or not bolt.bolt_id.strip():
            raise WrenchInputError("INVALID_BOLT_ID")
        if any(identity == bolt.bolt_id for identity, _ in points):
            raise WrenchInputError("INVALID_DUPLICATE_BOLT_ID")
        coordinate = (_number(bolt.a) * length, _number(bolt.b) * length)
        if any(point == coordinate for _, point in points):
            raise WrenchInputError("INVALID_DUPLICATE_BOLT_COORDINATE")
        points.append((bolt.bolt_id, coordinate))
    if not isinstance(request.reference, tuple) or len(request.reference) != 2:
        raise WrenchInputError("INVALID_WRENCH_REFERENCE")
    reference = (_number(request.reference[0]) * length, _number(request.reference[1]) * length)
    fa, fb = _number(request.force_a) * force, _number(request.force_b) * force
    mr = _number(request.moment_c) * moment
    n = len(points)
    ca = sum((point[0] for _, point in points), Fraction(0)) / n
    cb = sum((point[1] for _, point in points), Fraction(0)) / n
    polar = sum(((a - ca) ** 2 + (b - cb) ** 2 for _, (a, b) in points), Fraction(0))
    mc = mr + (reference[0] - ca) * fb - (reference[1] - cb) * fa
    solution = ExactWrenchSolution(
        Unit.MM, Unit.N, tuple(points), reference, (fa, fb), mr, (ca, cb), polar, mc, (), None
    )
    status = "CALCULATION_NOT_SUPPORTED_ZERO_GROUP_POLAR_SUM"
    if polar != 0 or mc == 0:
        bolts = []
        for identity, (a, b) in points:
            da, db = a - ca, b - cb
            ma, mb = (-mc * db / polar, mc * da / polar) if mc else (Fraction(0), Fraction(0))
            qa, qb = fa / n + ma, fb / n + mb
            bolts.append(
                ExactBoltWrenchDemand(
                    identity, (a, b), (da, db), (fa / n, fb / n), (ma, mb), (qa, qb), qa**2 + qb**2
                )
            )
        proof = ExactWrenchProof(
            ExactRecovery(fa, sum((bolt.total[0] for bolt in bolts), Fraction(0))),
            ExactRecovery(fb, sum((bolt.total[1] for bolt in bolts), Fraction(0))),
            ExactRecovery(
                mc,
                sum(
                    (
                        bolt.delta[0] * bolt.total[1] - bolt.delta[1] * bolt.total[0]
                        for bolt in bolts
                    ),
                    Fraction(0),
                ),
            ),
            ExactRecovery(
                mr,
                sum(
                    (
                        (bolt.coordinate[0] - reference[0]) * bolt.total[1]
                        - (bolt.coordinate[1] - reference[1]) * bolt.total[0]
                        for bolt in bolts
                    ),
                    Fraction(0),
                ),
            ),
        )
        if not proof.passed:
            raise ArithmeticError("Exact wrench recovery failed; no residual was redistributed.")
        solution = replace(solution, bolts=tuple(bolts), proof=proof)
        status = "CALCULATED"
    result = InPlaneWrenchResult(status, solution, "")
    return replace(result, fingerprint=hashlib.sha256(result.canonical_json().encode()).hexdigest())
