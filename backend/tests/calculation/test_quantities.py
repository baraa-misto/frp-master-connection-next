"""Exact Stage 2.1A dual-unit quantity tests."""

from decimal import Decimal

import pytest

from frp_master_connection.calculation import (
    INCH_TO_MM,
    KIP_TO_KN,
    KSI_TO_MPA,
    LBF_TO_N,
    PSI_TO_MPA,
    Dimension,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    StandardHoleDefinition,
    Unit,
    canonical_decimal_string,
    create_standard_hole,
    decimal_from_finite_real,
    decimal_value,
)


def test_exact_approved_conversion_constants_and_controlled_vocabularies() -> None:
    assert Decimal("25.4") == INCH_TO_MM
    assert Decimal("4.4482216152605") == LBF_TO_N
    assert Decimal("4.4482216152605") == KIP_TO_KN
    assert Decimal("0.00689475729316836133672267344534689069378138756277512555025110") == PSI_TO_MPA
    assert Decimal("6.89475729316836133672267344534689069378138756277512555025110") == KSI_TO_MPA
    assert set(Dimension) == {
        Dimension.LENGTH,
        Dimension.AREA,
        Dimension.FORCE,
        Dimension.MOMENT,
        Dimension.STRESS,
        Dimension.FORCE_PER_LENGTH,
        Dimension.SECOND_MOMENT_OF_AREA,
        Dimension.DIMENSIONLESS,
    }
    assert len(Unit) == 20


@pytest.mark.parametrize(
    ("source", "expected"),
    [(Decimal("1.25"), Decimal("1.25")), (2, Decimal(2)), ("-0.00", Decimal(0))],
)
def test_decimal_value_accepts_only_approved_public_representations(
    source: Decimal | int | str,
    expected: Decimal,
) -> None:
    assert decimal_value(source) == expected


@pytest.mark.parametrize("source", [True, False, 1.5, object(), None])
def test_decimal_value_rejects_boolean_float_and_other_types(source: object) -> None:
    with pytest.raises(TypeError, match="Decimal, int, or a decimal string"):
        decimal_value(source)  # type: ignore[arg-type]


@pytest.mark.parametrize("source", ["not-a-number", "1.2.3"])
def test_decimal_value_rejects_invalid_strings(source: str) -> None:
    with pytest.raises(ValueError, match="string must be valid"):
        decimal_value(source)


@pytest.mark.parametrize("source", ["NaN", "Infinity", "-Infinity"])
def test_decimal_value_rejects_nonfinite_values(source: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        decimal_value(source)


def test_explicit_geometry_adapter_uses_deterministic_string_representation() -> None:
    assert decimal_from_finite_real(0.1) == Decimal("0.1")
    assert decimal_from_finite_real(2) == Decimal(2)
    assert decimal_from_finite_real(Decimal("3.50")) == Decimal("3.50")
    with pytest.raises(TypeError, match="non-Boolean real"):
        decimal_from_finite_real(True)
    with pytest.raises(TypeError, match="non-Boolean real"):
        decimal_from_finite_real("1")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        decimal_from_finite_real(float("inf"))


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (Decimal("-0.000"), "0"),
        (Decimal("12.34000"), "12.34"),
        (Decimal("1200"), "1200"),
        (Decimal("1E+3"), "1000"),
        (Decimal("0.00010"), "0.0001"),
    ],
)
def test_canonical_decimal_string_avoids_exponents_and_insignificant_zeroes(
    source: Decimal,
    expected: str,
) -> None:
    assert canonical_decimal_string(source) == expected


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        (PhysicalQuantity.of("1", Unit.IN), Unit.MM, "25.4"),
        (PhysicalQuantity.of("1", Unit.IN2), Unit.MM2, "645.16"),
        (PhysicalQuantity.of("1", Unit.LBF), Unit.N, "4.4482216152605"),
        (PhysicalQuantity.of("1", Unit.KIP), Unit.KN, "4.4482216152605"),
        (PhysicalQuantity.of("1", Unit.LBF_IN), Unit.N_MM, "112.98482902761670"),
        (PhysicalQuantity.of("1", Unit.KIP_IN), Unit.KN_MM, "112.98482902761670"),
        (PhysicalQuantity.of("1", Unit.PSI), Unit.MPA, str(PSI_TO_MPA)),
        (PhysicalQuantity.of("1", Unit.KSI), Unit.MPA, str(KSI_TO_MPA)),
        (PhysicalQuantity.of("1", Unit.ONE), Unit.ONE, "1"),
    ],
)
def test_physical_quantity_exact_conversions(
    source: PhysicalQuantity,
    target: Unit,
    expected: str,
) -> None:
    converted = source.to(target)
    assert converted.magnitude == Decimal(expected)
    assert converted.dimension is source.dimension
    assert source.to_canonical().unit is source.canonical_unit


def test_physical_quantity_equality_hash_ordering_and_limited_arithmetic() -> None:
    inch = PhysicalQuantity.of("1", Unit.IN)
    millimetres = PhysicalQuantity.of("25.4", Unit.MM)
    assert inch == millimetres
    assert hash(inch) == hash(millimetres)
    assert inch != object()
    assert PhysicalQuantity.of("0.5", Unit.IN) < inch
    assert inch + PhysicalQuantity.of("25.4", Unit.MM) == PhysicalQuantity.of("2", Unit.IN)
    assert inch - PhysicalQuantity.of("12.7", Unit.MM) == PhysicalQuantity.of("0.5", Unit.IN)
    assert inch * "2.5" == PhysicalQuantity.of("2.5", Unit.IN)
    assert inch / 4 == PhysicalQuantity.of("0.25", Unit.IN)
    assert inch.canonical_string == "25.4"
    assert PhysicalQuantity.from_finite_real(1.25, Unit.MM) == PhysicalQuantity.of("1.25", Unit.MM)


def test_physical_quantity_rejects_invalid_unit_dimension_and_operations() -> None:
    with pytest.raises(TypeError, match="unit must be a Unit"):
        PhysicalQuantity(Decimal(1), "mm")  # type: ignore[arg-type]
    length = PhysicalQuantity.of("1", Unit.MM)
    force = PhysicalQuantity.of("1", Unit.N)
    with pytest.raises(TypeError, match="target must be a Unit"):
        length.to("in")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="different dimension"):
        length.to(Unit.N)
    with pytest.raises(TypeError, match="another PhysicalQuantity"):
        _ = length < object()
    with pytest.raises(ValueError, match="matching dimensions"):
        _ = length + force
    with pytest.raises(ZeroDivisionError, match="by zero"):
        _ = length / 0


def test_us_and_si_standard_holes_preserve_distinct_authoritative_physical_values() -> None:
    us = create_standard_hole(
        PhysicalQuantity.of("0.500", Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    si = create_standard_hole(
        PhysicalQuantity.of("12.7", Unit.MM),
        PublishedCodeUnitBasis.SI_PRINTED,
    )
    assert us.published_increment == PhysicalQuantity.of("0.063", Unit.IN)
    assert us.hole_diameter == PhysicalQuantity.of("0.563", Unit.IN)
    assert us.hole_diameter.to(Unit.MM).magnitude == Decimal("14.3002")
    assert si.published_increment == PhysicalQuantity.of("1.6", Unit.MM)
    assert si.hole_diameter == PhysicalQuantity.of("14.3", Unit.MM)
    assert str(si.hole_diameter.to(Unit.IN).magnitude).startswith("0.5629921259842519685")
    assert us.hole_diameter != si.hole_diameter
    assert us.published_source_basis is PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
    assert si.published_source_basis is PublishedCodeUnitBasis.SI_PRINTED


def test_standard_hole_rejects_invalid_source_and_inconsistent_definition() -> None:
    bolt = PhysicalQuantity.of("0.5", Unit.IN)
    increment = PhysicalQuantity.of("0.063", Unit.IN)
    with pytest.raises(ValueError, match="must all be lengths"):
        StandardHoleDefinition(
            bolt,
            PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
            PhysicalQuantity.of("1", Unit.N),
            PhysicalQuantity.of("0.563", Unit.IN),
        )
    with pytest.raises(ValueError, match="strictly positive"):
        StandardHoleDefinition(
            PhysicalQuantity.of("0", Unit.IN),
            PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
            increment,
            increment,
        )
    with pytest.raises(ValueError, match="must equal"):
        StandardHoleDefinition(
            bolt,
            PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
            increment,
            PhysicalQuantity.of("0.600", Unit.IN),
        )
    with pytest.raises(ValueError, match="must be a length"):
        create_standard_hole(
            PhysicalQuantity.of("1", Unit.N),
            PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        )
    with pytest.raises(TypeError, match="PublishedCodeUnitBasis"):
        create_standard_hole(bolt, "US")  # type: ignore[arg-type]
