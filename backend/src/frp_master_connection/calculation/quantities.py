"""Exact dual-unit physical quantities for calculation-contract planning."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from functools import total_ordering
from typing import Self


class Dimension(StrEnum):
    """Controlled physical dimensions supported by Stage 2.1A."""

    LENGTH = "LENGTH"
    AREA = "AREA"
    SECOND_MOMENT_OF_AREA = "SECOND_MOMENT_OF_AREA"
    FORCE = "FORCE"
    MOMENT = "MOMENT"
    STRESS = "STRESS"
    FORCE_PER_LENGTH = "FORCE_PER_LENGTH"
    DIMENSIONLESS = "DIMENSIONLESS"


class Unit(StrEnum):
    """Controlled engineering units with stable machine strings."""

    IN = "in"
    MM = "mm"
    IN2 = "in2"
    MM2 = "mm2"
    IN4 = "in4"
    MM4 = "mm4"
    LBF = "lbf"
    KIP = "kip"
    N = "N"
    KN = "kN"
    LBF_IN = "lbf-in"
    KIP_IN = "kip-in"
    N_MM = "N-mm"
    KN_MM = "kN-mm"
    PSI = "psi"
    KSI = "ksi"
    MPA = "MPa"
    KIP_PER_IN = "kip/in"
    N_PER_MM = "N/mm"
    ONE = "1"


INCH_TO_MM = Decimal("25.4")
LBF_TO_N = Decimal("4.4482216152605")
KIP_TO_KN = Decimal("4.4482216152605")
PSI_TO_MPA = Decimal("0.00689475729316836133672267344534689069378138756277512555025110")
KSI_TO_MPA = Decimal("6.89475729316836133672267344534689069378138756277512555025110")

_UNIT_DIMENSIONS = {
    Unit.IN: Dimension.LENGTH,
    Unit.MM: Dimension.LENGTH,
    Unit.IN2: Dimension.AREA,
    Unit.MM2: Dimension.AREA,
    Unit.IN4: Dimension.SECOND_MOMENT_OF_AREA,
    Unit.MM4: Dimension.SECOND_MOMENT_OF_AREA,
    Unit.LBF: Dimension.FORCE,
    Unit.KIP: Dimension.FORCE,
    Unit.N: Dimension.FORCE,
    Unit.KN: Dimension.FORCE,
    Unit.LBF_IN: Dimension.MOMENT,
    Unit.KIP_IN: Dimension.MOMENT,
    Unit.N_MM: Dimension.MOMENT,
    Unit.KN_MM: Dimension.MOMENT,
    Unit.PSI: Dimension.STRESS,
    Unit.KSI: Dimension.STRESS,
    Unit.MPA: Dimension.STRESS,
    Unit.KIP_PER_IN: Dimension.FORCE_PER_LENGTH,
    Unit.N_PER_MM: Dimension.FORCE_PER_LENGTH,
    Unit.ONE: Dimension.DIMENSIONLESS,
}

_CANONICAL_UNITS = {
    Dimension.LENGTH: Unit.MM,
    Dimension.AREA: Unit.MM2,
    Dimension.SECOND_MOMENT_OF_AREA: Unit.MM4,
    Dimension.FORCE: Unit.N,
    Dimension.MOMENT: Unit.N_MM,
    Dimension.STRESS: Unit.MPA,
    Dimension.FORCE_PER_LENGTH: Unit.N_PER_MM,
    Dimension.DIMENSIONLESS: Unit.ONE,
}

_TO_CANONICAL = {
    Unit.IN: INCH_TO_MM,
    Unit.MM: Decimal(1),
    Unit.IN2: INCH_TO_MM * INCH_TO_MM,
    Unit.MM2: Decimal(1),
    Unit.IN4: INCH_TO_MM**4,
    Unit.MM4: Decimal(1),
    Unit.LBF: LBF_TO_N,
    Unit.KIP: LBF_TO_N * Decimal(1000),
    Unit.N: Decimal(1),
    Unit.KN: Decimal(1000),
    Unit.LBF_IN: LBF_TO_N * INCH_TO_MM,
    Unit.KIP_IN: LBF_TO_N * Decimal(1000) * INCH_TO_MM,
    Unit.N_MM: Decimal(1),
    Unit.KN_MM: Decimal(1000),
    Unit.PSI: PSI_TO_MPA,
    Unit.KSI: KSI_TO_MPA,
    Unit.MPA: Decimal(1),
    Unit.KIP_PER_IN: Decimal("175.126835246476377952755905511811023622047244094488188976377940"),
    Unit.N_PER_MM: Decimal(1),
    Unit.ONE: Decimal(1),
}


def decimal_value(value: Decimal | int | str) -> Decimal:
    """Return a finite Decimal from an approved public input representation."""

    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise TypeError("A calculation decimal must be Decimal, int, or a decimal string.")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("A calculation decimal string must be valid.") from error
    if not result.is_finite():
        raise ValueError("A calculation decimal must be finite.")
    return Decimal(0) if result.is_zero() else result


def decimal_from_finite_real(value: float | int | Decimal) -> Decimal:
    """Adapt an existing finite real-valued geometry value deterministically."""

    if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
        raise TypeError("A geometry real adapter requires a non-Boolean real value.")
    return decimal_value(str(value))


def canonical_decimal_string(value: Decimal | int | str) -> str:
    """Serialize a finite decimal without exponent, trailing zero, or negative zero."""

    number = decimal_value(value)
    if number.is_zero():
        return "0"
    rendered = format(number, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class PhysicalQuantity:
    """One immutable magnitude/unit pair with exact canonical-unit behavior."""

    magnitude: Decimal
    unit: Unit

    def __post_init__(self) -> None:
        object.__setattr__(self, "magnitude", decimal_value(self.magnitude))
        if not isinstance(self.unit, Unit):
            raise TypeError("PhysicalQuantity.unit must be a Unit.")

    @classmethod
    def of(cls, magnitude: Decimal | int | str, unit: Unit) -> Self:
        """Construct from an approved public decimal representation."""

        return cls(decimal_value(magnitude), unit)

    @classmethod
    def from_finite_real(cls, magnitude: float | int | Decimal, unit: Unit) -> Self:
        """Construct through the explicit adapter for existing geometry values."""

        return cls(decimal_from_finite_real(magnitude), unit)

    @property
    def dimension(self) -> Dimension:
        return _UNIT_DIMENSIONS[self.unit]

    @property
    def canonical_unit(self) -> Unit:
        return _CANONICAL_UNITS[self.dimension]

    @property
    def canonical_magnitude(self) -> Decimal:
        with localcontext() as context:
            context.prec = 100
            return self.magnitude * _TO_CANONICAL[self.unit]

    @property
    def canonical_string(self) -> str:
        return canonical_decimal_string(self.canonical_magnitude)

    def to(self, unit: Unit) -> Self:
        """Convert to a compatible unit without display rounding."""

        if not isinstance(unit, Unit):
            raise TypeError("Conversion target must be a Unit.")
        if _UNIT_DIMENSIONS[unit] is not self.dimension:
            raise ValueError("Cannot convert a quantity to a different dimension.")
        with localcontext() as context:
            context.prec = 100
            magnitude = self.canonical_magnitude / _TO_CANONICAL[unit]
        return type(self)(magnitude, unit)

    def to_canonical(self) -> Self:
        return type(self)(self.canonical_magnitude, self.canonical_unit)

    def _compatible(self, other: object) -> PhysicalQuantity:
        if not isinstance(other, PhysicalQuantity):
            raise TypeError("Quantity operation requires another PhysicalQuantity.")
        if other.dimension is not self.dimension:
            raise ValueError("Quantity operation requires matching dimensions.")
        return other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PhysicalQuantity):
            return NotImplemented
        return (
            self.dimension is other.dimension
            and self.canonical_magnitude == other.canonical_magnitude
        )

    def __lt__(self, other: object) -> bool:
        compatible = self._compatible(other)
        return self.canonical_magnitude < compatible.canonical_magnitude

    def __hash__(self) -> int:
        return hash((self.dimension, self.canonical_magnitude))

    def __add__(self, other: object) -> Self:
        compatible = self._compatible(other)
        converted = compatible.to(self.unit)
        return type(self)(self.magnitude + converted.magnitude, self.unit)

    def __sub__(self, other: object) -> Self:
        compatible = self._compatible(other)
        converted = compatible.to(self.unit)
        return type(self)(self.magnitude - converted.magnitude, self.unit)

    def __mul__(self, scalar: Decimal | int | str) -> Self:
        return type(self)(self.magnitude * decimal_value(scalar), self.unit)

    def __truediv__(self, scalar: Decimal | int | str) -> Self:
        divisor = decimal_value(scalar)
        if divisor.is_zero():
            raise ZeroDivisionError("Cannot divide a quantity by zero.")
        with localcontext() as context:
            context.prec = 100
            return type(self)(self.magnitude / divisor, self.unit)


class PublishedCodeUnitBasis(StrEnum):
    """Printed unit column selected for a published code constant."""

    US_CUSTOMARY_PRINTED = "US_CUSTOMARY_PRINTED"
    SI_PRINTED = "SI_PRINTED"


@dataclass(frozen=True, slots=True)
class StandardHoleDefinition:
    """An authoritative physical standard hole and its printed source basis."""

    bolt_diameter: PhysicalQuantity
    published_source_basis: PublishedCodeUnitBasis
    published_increment: PhysicalQuantity
    hole_diameter: PhysicalQuantity

    def __post_init__(self) -> None:
        quantities = (self.bolt_diameter, self.published_increment, self.hole_diameter)
        if any(item.dimension is not Dimension.LENGTH for item in quantities):
            raise ValueError("Standard-hole values must all be lengths.")
        if self.bolt_diameter.magnitude <= 0 or self.published_increment.magnitude <= 0:
            raise ValueError("Bolt diameter and hole increment must be strictly positive.")
        expected_canonical = (
            self.bolt_diameter.canonical_magnitude + self.published_increment.canonical_magnitude
        )
        if self.hole_diameter.canonical_magnitude != expected_canonical:
            raise ValueError("Stored hole diameter must equal bolt plus printed increment.")


def create_standard_hole(
    bolt_diameter: PhysicalQuantity,
    published_source_basis: PublishedCodeUnitBasis,
) -> StandardHoleDefinition:
    """Generate and store one hole from exactly one published unit column."""

    if bolt_diameter.dimension is not Dimension.LENGTH:
        raise ValueError("A standard-hole bolt diameter must be a length.")
    if not isinstance(published_source_basis, PublishedCodeUnitBasis):
        raise TypeError("published_source_basis must be a PublishedCodeUnitBasis.")
    increment = (
        PhysicalQuantity.of("0.063", Unit.IN)
        if published_source_basis is PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
        else PhysicalQuantity.of("1.6", Unit.MM)
    )
    source_bolt = bolt_diameter.to(increment.unit)
    return StandardHoleDefinition(
        bolt_diameter,
        published_source_basis,
        increment,
        source_bolt + increment,
    )


__all__ = (
    "INCH_TO_MM",
    "KIP_TO_KN",
    "KSI_TO_MPA",
    "LBF_TO_N",
    "PSI_TO_MPA",
    "Dimension",
    "PhysicalQuantity",
    "PublishedCodeUnitBasis",
    "StandardHoleDefinition",
    "Unit",
    "canonical_decimal_string",
    "create_standard_hole",
    "decimal_from_finite_real",
    "decimal_value",
)
