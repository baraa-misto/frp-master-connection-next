"""Corrected kernel controls from independent rationals and source cell arithmetic."""

from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, cast

import pytest

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_reference import (
    OptionalState,
    ReferenceStream,
    RhmShape,
    StormSetting,
    additive_comparison,
    bearing_capacity,
    bolt_shear_capacity,
    global_block_capacity,
    local_shear_capacity,
    optional_part_comparison,
    reference_count,
    reference_quantity,
    validate_reference_storm,
    workbook_allowable,
)
from frp_master_connection.calculation.rhm_workbook_case import PRODUCT, execute_workbook_case
from tests.hyb1_fixtures import q

ERROR_PATTERN = (
    r"(required|must|needs|match|mandatory|duplicate|Duplicate|wrong|basis|Case|Reference|"
    r"Snapshot|positive|finite|Every|cannot|An|No |RHM|Unknown|dimension|convert|original|"
    r"recorded|Retain|excludes)"
)


@pytest.mark.parametrize(
    ("index", "target"),
    [
        (0, Fraction(1048, 5625) + Fraction(56600, 637125)),
        (2, Fraction(1048, 6750) + Fraction(566, 63000)),
        (3, Fraction(1048, 7125) + Fraction(566, 28575)),
        (4, Fraction(4192, 37125) + Fraction(2264, 25875)),
    ],
)
def test_five_reference_ratios_match_independent_arithmetic(index: int, target: Fraction) -> None:
    result = execute_workbook_case()
    with localcontext() as context:
        context.prec = 60
        expected = Decimal(target.numerator) / Decimal(target.denominator)
    assert abs(result.comparisons[index].utilization - expected) < Decimal("1e-58")
    assert abs(
        result.comparisons[1].utilization - Decimal(".15859074246389776534206686392058")
    ) < Decimal("1e-30")
    assert result.column_summary == result.comparisons[4].utilization
    assert result.summary_cell == "Calcs!D168"
    assert result.comparisons[4].capacities[0] == q("9.28125")


@pytest.mark.parametrize("scale", ["0", "1", "5"])
def test_zero_load_and_overload_with_real_positive_capacity(scale: str) -> None:
    result = execute_workbook_case(
        shear=q(str(Decimal("1.048") * Decimal(scale))),
        axial=q(str(Decimal(".566") * Decimal(scale))),
    )
    assert len(result.comparisons) == 5
    assert all(c.capacities[0].magnitude > 0 for c in result.comparisons)
    if scale == "5":
        assert result.comparisons[0].numerical_outcome == "FAIL"
        assert result.comparisons[4].numerical_outcome == "FAIL"
    elif scale == "0":
        assert all(c.utilization == 0 for c in result.comparisons)
    else:
        assert all(c.numerical_outcome == "PASS" for c in result.comparisons)


def test_us_si_physical_reference_equivalence() -> None:
    us = execute_workbook_case()
    si = execute_workbook_case(shear=q("1.048").to(Unit.N), axial=q(".566").to(Unit.N))
    assert us == si


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "-Infinity"])
def test_invalid_magnitude_is_never_an_absolute_value_or_subtracted_ratio(value: str) -> None:
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        execute_workbook_case(shear=q(value))


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "3"])
def test_invalid_count(value: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        reference_count(cast(int, value))


@pytest.mark.parametrize("value", ["0", "-1"])
def test_invalid_denominators(value: str) -> None:
    prop = workbook_allowable(RhmShape.W_I, "WEB_SHEAR_LW", product_id=PRODUCT)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        bearing_capacity(3, q(value, Unit.IN), q(".5", Unit.IN), prop)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        bolt_shear_capacity(3, 1, q(".5", Unit.IN), q(value, Unit.KSI))
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        local_shear_capacity(2, q(value, Unit.IN), q(".5", Unit.IN), prop)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        global_block_capacity(q(value, Unit.IN2), q("1", Unit.IN2), prop, prop)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        additive_comparison(
            "X", (q(),), (q(value),), cells=(), operands=(), equation="D/R", assumptions=()
        )


def test_reference_type_dimensions_and_term_count() -> None:
    with pytest.raises(TypeError):
        reference_quantity(cast(PhysicalQuantity, 1), Unit.KIP)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        reference_quantity(q("1", Unit.IN), Unit.KIP)
    for demands, capacities in [((), ()), ((q(),), (q("1"), q("2")))]:
        with pytest.raises(
            ValueError,
            match=ERROR_PATTERN,
        ):
            additive_comparison(
                "X", demands, capacities, cells=(), operands=(), equation="D/R", assumptions=()
            )


@pytest.mark.parametrize(
    ("shape", "column", "expected"),
    [
        (RhmShape.W_I, "D", "5.75"),
        (RhmShape.ANGLE_L3_OR_LESS, "E", "4.5"),
        (RhmShape.ANGLE_L4_OR_LARGER, "F", "8.25"),
    ],
)
def test_shape_region_axis_source_factor_once(shape: RhmShape, column: str, expected: str) -> None:
    prop = workbook_allowable(shape, "FLANGE_BEARING_CW", product_id=PRODUCT)
    assert prop.stress == q(expected, Unit.KSI)
    assert prop.source_cell == "Dim & Properties!" + column + "115"
    assert prop.factor_cell == "Dim & Properties!" + column + "116"
    assert prop.safety_factor == 4
    assert "UNESTABLISHED" in prop.value_definition


@pytest.mark.parametrize("change", ["shape", "resin", "property", "product"])
def test_wrong_shape_region_resin_product_refused(change: str) -> None:
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        workbook_allowable(
            cast(RhmShape, "W_I") if change == "shape" else RhmShape.W_I,
            "ABSENT" if change == "property" else "WEB_SHEAR_LW",
            product_id="OTHER" if change == "product" else PRODUCT,
            resin="VINYL_ESTER" if change == "resin" else "POLYESTER",
        )


@pytest.mark.parametrize("change", ["factor", "source", "factor_cell", "shape", "value_definition"])
def test_missing_or_invented_property_authority(change: str) -> None:
    prop = workbook_allowable(RhmShape.W_I, "WEB_SHEAR_LW", product_id=PRODUCT)
    alterations: dict[str, object] = {
        "factor": Decimal(0),
        "source": "",
        "factor_cell": "",
        "shape": "W_I",
        "value_definition": "ASCE_CHARACTERISTIC",
    }
    key = {"factor": "safety_factor", "source": "source_cell"}.get(change, change)
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        replace(cast(Any, prop), **{key: alterations[change]})


@pytest.mark.parametrize(
    ("present", "transfer", "demand", "capacity", "expected"),
    [
        (False, False, None, None, OptionalState.NOT_APPLICABLE),
        (True, False, q(), q("1"), OptionalState.INCOMPLETE),
        (True, True, None, q("1"), OptionalState.INCOMPLETE),
        (True, True, q(), None, OptionalState.INCOMPLETE),
        (True, True, q(), q("1"), OptionalState.PASS),
        (True, True, q("2"), q("1"), OptionalState.FAIL),
    ],
)
def test_optional_part_applicability(
    present: bool,
    transfer: bool,
    demand: PhysicalQuantity | None,
    capacity: PhysicalQuantity | None,
    expected: OptionalState,
) -> None:
    result = optional_part_comparison(
        "BEAM_DOUBLER_ADHESIVE",
        present=present,
        transfer_established=transfer,
        demand=demand,
        capacity=capacity,
    )
    assert result.state is expected


def test_optional_part_cannot_close_receiving_member_or_accept_non_boolean() -> None:
    for key, present, transfer in [
        ("W_BLOCK", True, True),
        ("BEAM_DOUBLER_ADHESIVE", 1, True),
        ("BEAM_DOUBLER_ADHESIVE", True, 1),
    ]:
        with pytest.raises((ValueError, TypeError)):
            optional_part_comparison(
                key,
                present=cast(bool, present),
                transfer_established=cast(bool, transfer),
                demand=None,
                capacity=None,
            )


@pytest.mark.parametrize(
    ("stream", "storm"),
    [
        (ReferenceStream.CORRECTED_REFERENCE, StormSetting.HISTORICAL_TWO_THIRDS),
        (ReferenceStream.CORRECTED_REFERENCE, StormSetting.UNADOPTED_INCREASE),
        (ReferenceStream.HISTORICAL_REPLICATION, StormSetting.UNADOPTED_INCREASE),
    ],
)
def test_unadopted_storm_policy_not_invented(stream: ReferenceStream, storm: StormSetting) -> None:
    with pytest.raises(
        ValueError,
        match=ERROR_PATTERN,
    ):
        validate_reference_storm(stream, storm)


def test_storm_types_mandatory() -> None:
    with pytest.raises(TypeError):
        validate_reference_storm(cast(ReferenceStream, "corrected"), StormSetting.NONE)


@pytest.mark.parametrize(
    ("demand", "outcome"),
    [(".999999999999999999", "PASS"), ("1", "PASS"), ("1.000000000000000001", "FAIL")],
)
def test_exact_comparison_boundary(demand: str, outcome: str) -> None:
    result = additive_comparison(
        "BOUNDARY", (q(demand),), (q("1"),), cells=(), operands=(), equation="D/R", assumptions=()
    )
    assert result.numerical_outcome == outcome
