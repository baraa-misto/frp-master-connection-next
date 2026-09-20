"""Direct transcription, branch, and factor tests for Stage 2.1B equations."""

from decimal import Decimal, localcontext

import pytest

from frp_master_connection.calculation import (
    BearingTrace,
    EndUseFactors,
    EndUsePropertyTrace,
    FRPPropertyKind,
    GoverningEquationBranch,
    PhysicalQuantity,
    PultrudedElementForm,
    QualificationStatus,
    ThreadStatus,
    Unit,
)
from frp_master_connection.calculation.equations import (
    DECIMAL_PI,
    adjust_frp_property,
    assemble_frp_design_resistance,
    bolt_body_area,
    bolt_shear_resistance,
    bolt_tension_resistance,
    cleavage_resistance,
    combined_bolt_tension_shear_resistance,
    f593_nominal_shear_stress,
    net_tension_resistance,
    pin_bearing_resistance,
    pull_through_resistance,
    shear_out_resistance,
)


def _property(
    kind: FRPPropertyKind,
    value: str,
    *,
    cm: str = "1",
    ct: str = "1",
    cch: str = "1",
) -> EndUsePropertyTrace:
    return adjust_frp_property(
        kind,
        PhysicalQuantity.of(value, Unit.KSI),
        QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
        EndUseFactors(
            Decimal(cm),
            Decimal(ct),
            Decimal(cch),
            "fixture",
            ("explicit factor test",),
        ),
    )


def _bearing(*, e_factor: ThreadStatus = ThreadStatus.EXCLUDED) -> BearingTrace:
    return pin_bearing_resistance(
        PhysicalQuantity.of("0.375", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        _property(FRPPropertyKind.FBR_L, "30"),
        e_factor,
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )


def test_bolt_area_shear_multiplier_and_pure_resistances() -> None:
    area = bolt_body_area(PhysicalQuantity.of("0.5", Unit.IN))
    with localcontext() as context:
        context.prec = 60
        expected_area = DECIMAL_PI / Decimal(16)
    assert area.area.to(Unit.IN2).magnitude == expected_area
    included = f593_nominal_shear_stress(
        PhysicalQuantity.of("100", Unit.KSI), ThreadStatus.INCLUDED
    )
    excluded = f593_nominal_shear_stress(
        PhysicalQuantity.of("100", Unit.KSI), ThreadStatus.EXCLUDED
    )
    assert included.to(Unit.KSI).magnitude.quantize(Decimal("0.000000000001")) == Decimal(
        "50.000000000000"
    )
    assert excluded.to(Unit.KSI).magnitude.quantize(Decimal("0.000000000001")) == Decimal(
        "60.000000000000"
    )
    tension = bolt_tension_resistance(
        PhysicalQuantity.of("0.5", Unit.IN), PhysicalQuantity.of("100", Unit.KSI)
    )
    shear = bolt_shear_resistance(
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("100", Unit.KSI),
        ThreadStatus.EXCLUDED,
    )
    assert tension.phi == shear.phi == Decimal("0.75")
    assert tension.lambda_factor == shear.lambda_factor == Decimal(1)
    assert shear.nominal_stress == excluded


def test_bolt_equations_reject_wrong_dimensions_values_and_thread_types() -> None:
    with pytest.raises(ValueError, match="Expected LENGTH"):
        bolt_body_area(PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="positive"):
        bolt_body_area(PhysicalQuantity.of("0", Unit.IN))
    with pytest.raises(ValueError, match="positive"):
        f593_nominal_shear_stress(PhysicalQuantity.of("0", Unit.KSI), ThreadStatus.EXCLUDED)
    with pytest.raises(TypeError, match="ThreadStatus"):
        f593_nominal_shear_stress(
            PhysicalQuantity.of("100", Unit.KSI),
            "EXCLUDED",  # type: ignore[arg-type]
        )


def test_combined_bolt_cap_and_unclamped_negative_raw_branch() -> None:
    capped = combined_bolt_tension_shear_resistance(
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("100", Unit.KSI),
        ThreadStatus.EXCLUDED,
        PhysicalQuantity.of("0", Unit.KIP),
    )
    assert capped.modified_tensile_stress == PhysicalQuantity.of("100", Unit.KSI)
    below_zero = combined_bolt_tension_shear_resistance(
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("100", Unit.KSI),
        ThreadStatus.EXCLUDED,
        PhysicalQuantity.of("30", Unit.KIP),
    )
    assert below_zero.modified_tensile_stress_raw.magnitude < 0
    assert below_zero.modified_tensile_stress == below_zero.modified_tensile_stress_raw
    assert below_zero.design_tensile_resistance.magnitude < 0


@pytest.mark.parametrize(
    ("through", "interlaminar", "expected"),
    [
        ("1", "10", (GoverningEquationBranch.PULL_THROUGH_8_4A,)),
        ("10", "1", (GoverningEquationBranch.PULL_THROUGH_8_4B,)),
        (
            "1",
            "1.25",
            (
                GoverningEquationBranch.PULL_THROUGH_8_4A,
                GoverningEquationBranch.PULL_THROUGH_8_4B,
            ),
        ),
    ],
)
def test_pull_through_governing_branches(
    through: str,
    interlaminar: str,
    expected: tuple[GoverningEquationBranch, ...],
) -> None:
    trace = pull_through_resistance(
        PhysicalQuantity.of("1", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        _property(FRPPropertyKind.FSH_LT, through),
        _property(FRPPropertyKind.FSH_INT, interlaminar),
        c_delta=Decimal(1),
        lambda_factor=Decimal("0.8"),
    )
    assert trace.governing_branches == expected
    assert trace.factor_trace.c_lap == Decimal(1)
    assert trace.factor_trace.lambda_factor == Decimal("0.8")


def test_end_use_and_resistance_factors_are_applied_once_in_declared_order() -> None:
    adjusted = _property(FRPPropertyKind.FBR_L, "10", cm="0.8", ct="0.9", cch="0.7")
    assert adjusted.adjusted_property.to(Unit.KSI).magnitude.quantize(
        Decimal("0.000000000001")
    ) == Decimal("5.040000000000")
    trace = assemble_frp_design_resistance(
        PhysicalQuantity.of("10", Unit.KIP),
        (adjusted,),
        c_delta=Decimal("0.9"),
        c_lap=Decimal("0.6"),
        phi=Decimal("0.5"),
        lambda_factor=Decimal("0.8"),
    )
    assert trace.design_resistance.to(Unit.KIP).magnitude == Decimal("2.16")
    assert (trace.c_delta, trace.c_lap, trace.phi, trace.lambda_factor) == (
        Decimal("0.9"),
        Decimal("0.6"),
        Decimal("0.5"),
        Decimal("0.8"),
    )
    with pytest.raises(ValueError, match="positive"):
        assemble_frp_design_resistance(
            PhysicalQuantity.of("1", Unit.KIP),
            (),
            c_delta=Decimal(0),
            c_lap=Decimal(1),
            phi=Decimal(1),
            lambda_factor=Decimal(1),
        )


def test_bearing_thread_factor_and_lap_factor() -> None:
    excluded = _bearing()
    included = _bearing(e_factor=ThreadStatus.INCLUDED)
    single_lap = pin_bearing_resistance(
        PhysicalQuantity.of("0.375", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        _property(FRPPropertyKind.FBR_T, "18"),
        ThreadStatus.EXCLUDED,
        c_delta=Decimal(1),
        c_lap=Decimal("0.6"),
        lambda_factor=Decimal(1),
    )
    assert excluded.thread_factor == Decimal(1)
    assert included.thread_factor == Decimal("0.60")
    assert (
        included.factor_trace.nominal_resistance
        == excluded.factor_trace.nominal_resistance * Decimal("0.60")
    )
    assert single_lap.factor_trace.c_lap == Decimal("0.6")
    with pytest.raises(TypeError, match="ThreadStatus"):
        _ = pin_bearing_resistance(
            PhysicalQuantity.of("0.375", Unit.IN),
            PhysicalQuantity.of("0.5", Unit.IN),
            _property(FRPPropertyKind.FBR_L, "30"),
            "EXCLUDED",  # type: ignore[arg-type]
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )


@pytest.mark.parametrize(
    ("e1", "expected_theta"),
    [("2.999", None), ("3", "1.0"), ("4", "1.0")],
)
def test_net_tension_theta_boundaries(e1: str, expected_theta: str | None) -> None:
    trace = net_tension_resistance(
        PhysicalQuantity.of("3", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        PhysicalQuantity.of(e1, Unit.IN),
        _property(FRPPropertyKind.FT_L, "33"),
        PultrudedElementForm.SHAPE_ELEMENT,
        True,
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )
    if expected_theta is None:
        assert trace.theta < Decimal(1)
    else:
        assert trace.theta == Decimal(expected_theta)


@pytest.mark.parametrize(
    ("element_form", "longitudinal", "expected_ci"),
    [
        (PultrudedElementForm.SHAPE_ELEMENT, True, "0.50"),
        (PultrudedElementForm.SHAPE_ELEMENT, False, "0.50"),
        (PultrudedElementForm.PLATE, True, "0.40"),
        (PultrudedElementForm.PLATE, False, "0.50"),
    ],
)
def test_net_tension_shape_plate_and_direction_coefficients(
    element_form: PultrudedElementForm,
    longitudinal: bool,
    expected_ci: str,
) -> None:
    trace = net_tension_resistance(
        PhysicalQuantity.of("4", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        _property(FRPPropertyKind.FT_L if longitudinal else FRPPropertyKind.FT_T, "10"),
        element_form,
        longitudinal,
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )
    assert trace.ci == Decimal(expected_ci)
    with localcontext() as context:
        context.prec = 60
        expected_power = (trace.theta * trace.logarithm_ratio.ln()).exp()
    assert trace.ratio_power == expected_power


def test_net_tension_rejects_invalid_geometry_and_contract_types() -> None:
    arguments = (
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        _property(FRPPropertyKind.FT_L, "33"),
    )
    with pytest.raises(ValueError, match="width greater"):
        net_tension_resistance(
            *arguments,
            PultrudedElementForm.SHAPE_ELEMENT,
            True,
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )
    with pytest.raises(ValueError, match="Spr greater than one"):
        net_tension_resistance(
            PhysicalQuantity.of("0.6", Unit.IN),
            PhysicalQuantity.of("1", Unit.IN),
            PhysicalQuantity.of("0.563", Unit.IN),
            PhysicalQuantity.of("0.375", Unit.IN),
            PhysicalQuantity.of("2", Unit.IN),
            _property(FRPPropertyKind.FT_L, "33"),
            PultrudedElementForm.SHAPE_ELEMENT,
            True,
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )
    with pytest.raises(TypeError, match="element_form"):
        net_tension_resistance(
            *arguments,
            "SHAPE",  # type: ignore[arg-type]
            True,
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )
    with pytest.raises(TypeError, match="Boolean"):
        net_tension_resistance(
            *arguments,
            PultrudedElementForm.SHAPE_ELEMENT,
            1,  # type: ignore[arg-type]
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )
    with pytest.raises(ValueError, match="positive bolt diameter"):
        net_tension_resistance(
            PhysicalQuantity.of("4", Unit.IN),
            PhysicalQuantity.of("0", Unit.IN),
            PhysicalQuantity.of("0.563", Unit.IN),
            PhysicalQuantity.of("0.375", Unit.IN),
            PhysicalQuantity.of("0", Unit.IN),
            _property(FRPPropertyKind.FT_L, "33"),
            PultrudedElementForm.SHAPE_ELEMENT,
            True,
            c_delta=Decimal(1),
            c_lap=Decimal(1),
            lambda_factor=Decimal(1),
        )


def test_shear_out_equation() -> None:
    trace = shear_out_resistance(
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        _property(FRPPropertyKind.FSH_LT, "8"),
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )
    assert trace.factor_trace.nominal_resistance == PhysicalQuantity.of("7.2177", Unit.KIP)


@pytest.mark.parametrize(
    ("e1", "expected_ratio", "expected_phi"),
    [("1.5", "3", "0.50"), ("2", "4", "0.60"), ("2.5", "5", "0.60")],
)
def test_cleavage_branch_b_boundaries_and_design_level_selection(
    e1: str,
    expected_ratio: str,
    expected_phi: str,
) -> None:
    bearing = _bearing()
    trace = cleavage_resistance(
        PhysicalQuantity.of(e1, Unit.IN),
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        _property(FRPPropertyKind.FT_L, "33"),
        _property(FRPPropertyKind.FSH_LT, "8"),
        bearing,
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )
    assert trace.branch_b_condition_e1_over_d == Decimal(expected_ratio)
    assert trace.branch_b_factor_trace.phi == Decimal(expected_phi)
    assert trace.selected_design_resistance == min(
        trace.branch_a_factor_trace.design_resistance,
        trace.branch_b_factor_trace.design_resistance,
    )
    assert trace.governing_branches


def test_cleavage_branch_a_can_govern_and_exact_design_tie_is_retained() -> None:
    bearing = _bearing()
    branch_a = cleavage_resistance(
        PhysicalQuantity.of("2", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.5", Unit.IN),
        PhysicalQuantity.of("0.563", Unit.IN),
        PhysicalQuantity.of("0.375", Unit.IN),
        _property(FRPPropertyKind.FT_L, "1"),
        _property(FRPPropertyKind.FSH_LT, "1"),
        bearing,
        c_delta=Decimal(1),
        c_lap=Decimal(1),
        lambda_factor=Decimal(1),
    )
    assert branch_a.governing_branches == (GoverningEquationBranch.CLEAVAGE_A,)
