"""Golden numerical verification for the Calculation Slice 2 primitives."""

from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Decimal
from typing import cast

import pytest

from frp_master_connection.calculation import (
    AppendixThetaBranch,
    BlockShearEccentricityClassification,
    BlockShearEquation,
    EndUseFactors,
    EndUsePropertyTrace,
    FRPPropertyEntry,
    FRPPropertyKind,
    FullFirstRowTrace,
    InterrowShearOutMethod,
    MaterialDirection,
    NumericalComparison,
    PhysicalQuantity,
    PropertyBehavior,
    PultrudedElementClassification,
    QualificationStatus,
    SourceClassification,
    Unit,
    adjusted_property_trace,
    assemble_multirow_resistance,
    block_shear_resistance,
    classify_block_shear_eccentricity,
    compare_resistance,
    constant_pitch_factor,
    full_first_row_resistance,
    interrow_shear_out_resistance,
    lower_first_row_envelope,
    simplified_first_row_resistance,
    unknown_lbr_endpoint_envelope,
)

UNITY = EndUseFactors(Decimal(1), Decimal(1), Decimal(1), "fixture", ("approved",))


def _entry(
    kind: FRPPropertyKind,
    value: str,
    unit: Unit,
    behavior: PropertyBehavior,
) -> FRPPropertyEntry:
    return FRPPropertyEntry(
        kind,
        PhysicalQuantity.of(value, unit),
        behavior,
        SourceClassification.QUALIFIED_TEST_DATA,
        QualificationStatus.QUALIFIED,
        "RC2 synthetic qualified reference material",
        "RC2",
    )


def _strength(
    kind: FRPPropertyKind,
    value: str,
    behavior: PropertyBehavior,
    factors: EndUseFactors = UNITY,
    unit: Unit = Unit.KSI,
) -> EndUsePropertyTrace:
    return adjusted_property_trace(_entry(kind, value, unit, behavior), factors)


def _serialized(quantity: PhysicalQuantity, unit: Unit) -> Decimal:
    return quantity.to(unit).magnitude.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)


def _full(
    *,
    direction: MaterialDirection = MaterialDirection.LONGITUDINAL,
    element: PultrudedElementClassification = PultrudedElementClassification.SHAPE,
    end: str = "2",
    hole: str = ".563",
    lbr: str = ".5",
    bolt_count: int = 1,
    width: str = "3",
    gauge: str | None = None,
) -> FullFirstRowTrace:
    property_kind = (
        FRPPropertyKind.FT_L
        if direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FT_T
    )
    strength = "33" if direction is MaterialDirection.LONGITUDINAL else "7.5"
    return full_first_row_resistance(
        PhysicalQuantity.of(width, Unit.IN),
        PhysicalQuantity.of(".5", Unit.IN),
        PhysicalQuantity.of(hole, Unit.IN),
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of(end, Unit.IN),
        _strength(property_kind, strength, PropertyBehavior.LONGITUDINAL),
        direction,
        element,
        bolt_count,
        Decimal(lbr),
        gauge=None if gauge is None else PhysicalQuantity.of(gauge, Unit.IN),
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )


def test_rc2_asymmetric_e1_mapping_full_method_and_equation_8_12() -> None:
    full = _full(end="1.25")
    assert full.spr == Decimal(6)
    assert full.theta == Decimal("0.3")
    assert full.theta_branch is AppendixThetaBranch.E1_OVER_W_LE_1
    assert _serialized(full.factor_trace.equation_nominal_resistance, Unit.KIP) == Decimal(
        "11.996812753498"
    )
    assert _serialized(full.factor_trace.design_resistance, Unit.KIP) == Decimal("5.998406376749")
    shearout = interrow_shear_out_resistance(
        InterrowShearOutMethod.ASCE_EQ_8_12,
        PhysicalQuantity.of("1.25", Unit.IN),
        PhysicalQuantity.of(".563", Unit.IN),
        (PhysicalQuantity.of("2", Unit.IN),),
        PhysicalQuantity.of(".375", Unit.IN),
        _strength(FRPPropertyKind.FSH_LT, "8", PropertyBehavior.IN_PLANE_SHEAR),
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    assert _serialized(shearout.factor_trace.equation_nominal_resistance, Unit.KIP) == Decimal(
        "12.467700000000"
    )
    assert _serialized(shearout.factor_trace.design_resistance, Unit.KIP) == Decimal(
        "5.610465000000"
    )


@pytest.mark.parametrize(
    ("end", "branch", "theta", "resistance"),
    [
        ("2.999999", AppendixThetaBranch.E1_OVER_W_LE_1, "0.999999833333", "5.837379920471"),
        ("3", AppendixThetaBranch.E1_OVER_W_LE_1, "1.000000000000", "5.837379887382"),
        ("3.000001", AppendixThetaBranch.E1_OVER_W_GE_1, "1.000000000000", "5.837379887382"),
    ],
)
def test_rc2_appendix_branch_boundary(
    end: str,
    branch: AppendixThetaBranch,
    theta: str,
    resistance: str,
) -> None:
    trace = _full(end=end)
    assert trace.theta_branch is branch
    assert trace.theta.quantize(Decimal("0.000000000001")) == Decimal(theta)
    assert _serialized(trace.factor_trace.design_resistance, Unit.KIP) == Decimal(resistance)


@pytest.mark.parametrize(
    ("direction", "element", "ci", "resistance"),
    [
        (
            MaterialDirection.LONGITUDINAL,
            PultrudedElementClassification.SHAPE,
            ".5",
            "5.889623934957",
        ),
        (
            MaterialDirection.LONGITUDINAL,
            PultrudedElementClassification.PLATE,
            ".4",
            "6.486627586212",
        ),
        (
            MaterialDirection.TRANSVERSE,
            PultrudedElementClassification.SHAPE,
            ".5",
            "1.204695804878",
        ),
        (
            MaterialDirection.TRANSVERSE,
            PultrudedElementClassification.PLATE,
            ".5",
            "1.204695804878",
        ),
    ],
)
def test_rc2_appendix_coefficient_matrix(
    direction: MaterialDirection,
    element: PultrudedElementClassification,
    ci: str,
    resistance: str,
) -> None:
    trace = _full(direction=direction, element=element)
    assert trace.appendix_coefficient_c_i == Decimal(ci)
    assert trace.appendix_open_hole_coefficient_c_op_i == Decimal(".5")
    assert _serialized(trace.factor_trace.design_resistance, Unit.KIP) == Decimal(resistance)


def test_rc2_reduced_pitch_and_complete_first_row_factor_stack() -> None:
    pitch = constant_pitch_factor(
        (PhysicalQuantity.of("1.5", Unit.IN),), PhysicalQuantity.of(".5", Unit.IN)
    )
    assert pitch.pitch_factor_c_delta == Decimal(".75")
    assert pitch.minimum_pitch == PhysicalQuantity.of("2", Unit.IN)
    assert pitch.reduced is True

    factors = EndUseFactors(Decimal(".75"), Decimal(".8"), Decimal(".9"), "fixture", ("ok",))
    tensile = _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL, factors)
    trace = simplified_first_row_resistance(
        PhysicalQuantity.of("3", Unit.IN),
        PhysicalQuantity.of(".375", Unit.IN),
        tensile,
        MaterialDirection.LONGITUDINAL,
        lap_factor_c_lap=Decimal(".6"),
        pitch_factor_c_delta=Decimal(".75"),
        time_effect_factor_lambda=Decimal(".8"),
    )
    assert _serialized(tensile.adjusted_property, Unit.KSI) == Decimal("17.820000000000")
    assert _serialized(trace.factor_trace.equation_nominal_resistance, Unit.KIP) == Decimal(
        "4.009500000000"
    )
    assert _serialized(
        trace.factor_trace.connection_adjusted_nominal_resistance, Unit.KIP
    ) == Decimal("1.804275000000")
    assert _serialized(trace.factor_trace.design_resistance, Unit.KIP) == Decimal(".721710000000")
    comparison = compare_resistance(
        PhysicalQuantity.of(".6", Unit.KIP), trace.factor_trace.design_resistance
    )
    assert comparison.numerical_comparison is NumericalComparison.PASS
    assert comparison.utilization is not None
    assert comparison.utilization.quantize(Decimal(".000000000001")) == Decimal(".831358856050")


def test_rc2_unknown_lbr_and_lower_envelopes_preserve_exact_ties() -> None:
    endpoints = unknown_lbr_endpoint_envelope(
        PhysicalQuantity.of("3", Unit.IN),
        PhysicalQuantity.of(".5", Unit.IN),
        PhysicalQuantity.of(".563", Unit.IN),
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL),
        MaterialDirection.LONGITUDINAL,
        PultrudedElementClassification.SHAPE,
        1,
        gauge=None,
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    tied_factor = replace(
        endpoints.lbr_0.factor_trace,
        design_resistance=PhysicalQuantity.of("2", Unit.KIP),
    )
    tied_endpoints = replace(
        endpoints,
        lbr_0=replace(endpoints.lbr_0, factor_trace=tied_factor),
        lbr_1=replace(endpoints.lbr_1, factor_trace=tied_factor),
        controlling_endpoint_ids=("LBR_0", "LBR_1"),
        selected_design_resistance=PhysicalQuantity.of("2", Unit.KIP),
    )
    simplified = simplified_first_row_resistance(
        PhysicalQuantity.of("3", Unit.IN),
        PhysicalQuantity.of(".375", Unit.IN),
        _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL),
        MaterialDirection.LONGITUDINAL,
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    tied_simplified = replace(simplified, factor_trace=tied_factor)
    envelope = lower_first_row_envelope(tied_simplified, tied_endpoints)
    assert tied_endpoints.controlling_endpoint_ids == ("LBR_0", "LBR_1")
    assert envelope.controlling_method_ids == (
        "SIMPLIFIED_EXTENSION",
        "FULL_UNKNOWN_LBR_ENVELOPE",
    )


def test_rc2_interrow_equation_8_13_and_rational_actual_row_span() -> None:
    end = PhysicalQuantity.of("2", Unit.IN)
    hole = PhysicalQuantity.of(".563", Unit.IN)
    thickness = PhysicalQuantity.of(".375", Unit.IN)
    shear = _strength(FRPPropertyKind.FSH_LT, "8", PropertyBehavior.IN_PLANE_SHEAR)
    direct = interrow_shear_out_resistance(
        InterrowShearOutMethod.ASCE_EQ_8_13,
        end,
        hole,
        (PhysicalQuantity.of("2", Unit.IN),) * 2,
        thickness,
        shear,
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    extension = interrow_shear_out_resistance(
        InterrowShearOutMethod.RATIONAL_EXTENSION_EQ_8_13,
        end,
        hole,
        (
            PhysicalQuantity.of("1.5", Unit.IN),
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of("2.5", Unit.IN),
        ),
        thickness,
        shear,
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    assert direct.row_span == PhysicalQuantity.of("4", Unit.IN)
    assert extension.row_span == PhysicalQuantity.of("6", Unit.IN)
    assert extension.factor_trace.design_resistance > direct.factor_trace.design_resistance


def test_rc2_block_shear_single_lap_full_factors_and_native_si() -> None:
    shear = _strength(FRPPropertyKind.FSH_LT, "8", PropertyBehavior.IN_PLANE_SHEAR)
    tensile = _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL)
    single_lap = block_shear_resistance(
        BlockShearEquation.ASCE_EQ_8_14A,
        PhysicalQuantity.of("4.82625", Unit.IN2),
        PhysicalQuantity.of(".7965", Unit.IN2),
        shear,
        tensile,
        lap_factor_c_lap=Decimal(".6"),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    assert _serialized(single_lap.factor_trace.equation_nominal_resistance, Unit.KIP) == Decimal(
        "32.447250000000"
    )
    assert _serialized(
        single_lap.factor_trace.connection_adjusted_nominal_resistance, Unit.KIP
    ) == Decimal("19.468350000000")
    assert _serialized(single_lap.factor_trace.design_resistance, Unit.KIP) == Decimal(
        "8.760757500000"
    )

    factors = EndUseFactors(Decimal(".75"), Decimal(".8"), Decimal(".9"), "fixture", ("ok",))
    factored = block_shear_resistance(
        BlockShearEquation.ASCE_EQ_8_14A,
        PhysicalQuantity.of("4.82625", Unit.IN2),
        PhysicalQuantity.of(".7965", Unit.IN2),
        _strength(FRPPropertyKind.FSH_LT, "8", PropertyBehavior.IN_PLANE_SHEAR, factors),
        _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL, factors),
        lap_factor_c_lap=Decimal(".6"),
        pitch_factor_c_delta=Decimal(".75"),
        time_effect_factor_lambda=Decimal(".8"),
    )
    assert _serialized(factored.factor_trace.equation_nominal_resistance, Unit.KIP) == Decimal(
        "17.521515000000"
    )
    assert _serialized(factored.factor_trace.design_resistance, Unit.KIP) == Decimal(
        "2.838485430000"
    )

    native_si = block_shear_resistance(
        BlockShearEquation.ASCE_EQ_8_14A,
        PhysicalQuantity.of("1220", Unit.MM2),
        PhysicalQuantity.of("344", Unit.MM2),
        _strength(FRPPropertyKind.FSH_LT, "55", PropertyBehavior.IN_PLANE_SHEAR, unit=Unit.MPA),
        _strength(FRPPropertyKind.FT_L, "225", PropertyBehavior.LONGITUDINAL, unit=Unit.MPA),
        lap_factor_c_lap=Decimal(1),
        pitch_factor_c_delta=Decimal(1),
        time_effect_factor_lambda=Decimal(1),
    )
    assert _serialized(native_si.factor_trace.equation_nominal_resistance, Unit.KN) == Decimal(
        "72.250000000000"
    )
    assert _serialized(native_si.factor_trace.design_resistance, Unit.KN) == Decimal(
        "32.512500000000"
    )


@pytest.mark.parametrize(
    ("eccentricity", "classification"),
    [
        ("0", BlockShearEccentricityClassification.CONCENTRIC),
        (".000001", BlockShearEccentricityClassification.CONCENTRIC),
        (".000001000001", BlockShearEccentricityClassification.ECCENTRIC),
        ("-.000001000001", BlockShearEccentricityClassification.ECCENTRIC),
    ],
)
def test_rc2_block_shear_eccentricity_tolerance(
    eccentricity: str,
    classification: BlockShearEccentricityClassification,
) -> None:
    assert (
        classify_block_shear_eccentricity(
            PhysicalQuantity.of(eccentricity, Unit.IN), PhysicalQuantity.of(".000001", Unit.IN)
        )
        is classification
    )


def test_resistance_comparison_zero_negative_and_monotonic_cases() -> None:
    zero = compare_resistance(
        PhysicalQuantity.of("0", Unit.KIP), PhysicalQuantity.of("3.375", Unit.KIP)
    )
    assert zero == replace(
        zero, utilization=Decimal(0), numerical_comparison=NumericalComparison.PASS
    )
    for resistance in ("0", "-1"):
        result = compare_resistance(
            PhysicalQuantity.of("0" if resistance == "0" else "1", Unit.KIP),
            PhysicalQuantity.of(resistance, Unit.KIP),
        )
        assert result.utilization is None
        assert result.numerical_comparison is NumericalComparison.FAIL
        assert result.warnings == ("NONPOSITIVE_DESIGN_RESISTANCE",)
    lower = compare_resistance(
        PhysicalQuantity.of("1", Unit.KIP), PhysicalQuantity.of("3.375", Unit.KIP)
    )
    higher = compare_resistance(
        PhysicalQuantity.of("2", Unit.KIP), PhysicalQuantity.of("3.375", Unit.KIP)
    )
    assert higher.utilization is not None
    assert lower.utilization is not None
    assert higher.utilization > lower.utilization


def test_equation_contracts_fail_closed_for_types_domains_and_unsupported_geometry() -> None:
    tensile = _strength(FRPPropertyKind.FT_L, "33", PropertyBehavior.LONGITUDINAL)
    shear = _strength(FRPPropertyKind.FSH_LT, "8", PropertyBehavior.IN_PLANE_SHEAR)
    with pytest.raises(TypeError, match="FRPPropertyEntry"):
        adjusted_property_trace(object(), UNITY)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EndUseFactors"):
        adjusted_property_trace(
            _entry(FRPPropertyKind.FT_L, "33", Unit.KSI, PropertyBehavior.LONGITUDINAL),
            cast(EndUseFactors, object()),
        )
    with pytest.raises(TypeError, match="tuple"):
        assemble_multirow_resistance(
            PhysicalQuantity.of("1", Unit.KIP),
            cast(tuple[EndUsePropertyTrace, ...], []),
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            resistance_factor_phi=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="positive"):
        assemble_multirow_resistance(
            PhysicalQuantity.of("1", Unit.KIP),
            (tensile,),
            lap_factor_c_lap=Decimal(0),
            pitch_factor_c_delta=Decimal(1),
            resistance_factor_phi=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="pitch"):
        constant_pitch_factor((), PhysicalQuantity.of(".5", Unit.IN))
    with pytest.raises(ValueError, match="constant"):
        constant_pitch_factor(
            (PhysicalQuantity.of("1.5", Unit.IN), PhysicalQuantity.of("2", Unit.IN)),
            PhysicalQuantity.of(".5", Unit.IN),
        )
    with pytest.raises(TypeError, match="direction"):
        simplified_first_row_resistance(
            PhysicalQuantity.of("3", Unit.IN),
            PhysicalQuantity.of(".375", Unit.IN),
            tensile,
            cast(MaterialDirection, "L"),
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(TypeError, match="EndUsePropertyTrace"):
        simplified_first_row_resistance(
            PhysicalQuantity.of("3", Unit.IN),
            PhysicalQuantity.of(".375", Unit.IN),
            cast(EndUsePropertyTrace, object()),
            MaterialDirection.LONGITUDINAL,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="PhysicalQuantity"):
        simplified_first_row_resistance(
            PhysicalQuantity.of("3", Unit.KIP),
            PhysicalQuantity.of(".375", Unit.IN),
            tensile,
            MaterialDirection.LONGITUDINAL,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="must be positive"):
        simplified_first_row_resistance(
            PhysicalQuantity.of("0", Unit.IN),
            PhysicalQuantity.of(".375", Unit.IN),
            tensile,
            MaterialDirection.LONGITUDINAL,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(TypeError, match="direction"):
        _full(direction=cast(MaterialDirection, "BAD"))
    with pytest.raises(TypeError, match="element_classification"):
        _full(element=cast(PultrudedElementClassification, "BAD"))
    with pytest.raises(ValueError, match="one to three"):
        _full(bolt_count=4)
    with pytest.raises(TypeError, match="non-Boolean"):
        _full(bolt_count=True)
    with pytest.raises(ValueError, match="inclusive"):
        _full(lbr="-0.000000000001")
    with pytest.raises(ValueError, match="inclusive"):
        _full(lbr="1.000000000001")
    with pytest.raises(ValueError, match="w > N_b d"):
        _full(bolt_count=2, width="1", gauge=".5")
    with pytest.raises(ValueError, match="w > N_b d_n"):
        _full(bolt_count=2, width="1.126", gauge=".5")
    with pytest.raises(ValueError, match="requires gauge"):
        _full(bolt_count=2)
    with pytest.raises(ValueError, match="S_pr > 1"):
        _full(bolt_count=2, gauge=".5")
    with pytest.raises(TypeError, match="SimplifiedFirstRowTrace"):
        lower_first_row_envelope(object(), object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="UnknownLbrEnvelopeTrace"):
        lower_first_row_envelope(
            simplified_first_row_resistance(
                PhysicalQuantity.of("3", Unit.IN),
                PhysicalQuantity.of(".375", Unit.IN),
                tensile,
                MaterialDirection.LONGITUDINAL,
                lap_factor_c_lap=Decimal(1),
                pitch_factor_c_delta=Decimal(1),
                time_effect_factor_lambda=Decimal(1),
            ),
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="InterrowShearOutMethod"):
        interrow_shear_out_resistance(
            cast(InterrowShearOutMethod, "8-12"),
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (PhysicalQuantity.of("2", Unit.IN),),
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="physical pitches"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.ASCE_EQ_8_12,
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (),
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="exactly two rows"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.ASCE_EQ_8_12,
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (PhysicalQuantity.of("2", Unit.IN),) * 2,
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="constant pitch"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.ASCE_EQ_8_13,
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (PhysicalQuantity.of("2", Unit.IN), PhysicalQuantity.of("2.5", Unit.IN)),
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="exactly three rows"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.ASCE_EQ_8_13,
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (PhysicalQuantity.of("2", Unit.IN),),
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="more than three"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.RATIONAL_EXTENSION_EQ_8_13,
            PhysicalQuantity.of("2", Unit.IN),
            PhysicalQuantity.of(".563", Unit.IN),
            (PhysicalQuantity.of("2", Unit.IN),) * 2,
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="effective length"):
        interrow_shear_out_resistance(
            InterrowShearOutMethod.ASCE_EQ_8_12,
            PhysicalQuantity.of(".1", Unit.IN),
            PhysicalQuantity.of("1", Unit.IN),
            (PhysicalQuantity.of(".1", Unit.IN),),
            PhysicalQuantity.of(".375", Unit.IN),
            shear,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(TypeError, match="BlockShearEquation"):
        block_shear_resistance(
            cast(BlockShearEquation, "8-14a"),
            PhysicalQuantity.of("1", Unit.IN2),
            PhysicalQuantity.of("1", Unit.IN2),
            shear,
            tensile,
            lap_factor_c_lap=Decimal(1),
            pitch_factor_c_delta=Decimal(1),
            time_effect_factor_lambda=Decimal(1),
        )
    with pytest.raises(ValueError, match="nonnegative"):
        compare_resistance(PhysicalQuantity.of("-1", Unit.KIP), PhysicalQuantity.of("1", Unit.KIP))
