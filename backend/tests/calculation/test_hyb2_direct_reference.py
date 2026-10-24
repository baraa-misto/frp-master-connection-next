"""Independent source/cache controls, fresh geometry and corrected-reference regressions."""

from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from math import cos, radians, sin
from typing import Any, cast

import pytest

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_reference import (
    DirectGeometry,
    brace_rotation,
    execute_direct_source,
    moment_witness,
    q,
    sincos,
    source_paths,
)
from frp_master_connection.calculation.rhm_reference import ReferenceStream

CACHES = (
    ".04079661668589004",
    ".018479542999209356",
    ".10089213623932733",
    ".018108108446212381",
    ".073167755991285388",
    ".018479542999209356",
    ".059564127161013773",
    ".040397678801026446",
)
GEOMETRY = (
    "2.33082600938364968289118689315335971529802931620828219708731",
    "2.33082600938364968289118689315335971529802931620828219708731",
    "1.16541300469182484144559344657667985764901465810414109854365",
    ".509868189552673368132447132877297437721443912920561730612848",
    "1.16541300469182484144559344657667985764901465810414109854365",
    ".509868189552673368132447132877297437721443912920561730612848",
    "1.94726323541137352715246985270196281035904109865215349997771",
    "1.94726323541137352715246985270196281035904109865215349997771",
    "1.02708250411634020687761302731598338240463414433978652257411",
    "1.02708250411634020687761302731598338240463414433978652257411",
)


@pytest.mark.parametrize("stream", list(ReferenceStream))
def test_eight_summary_and_ten_geometry_controls(stream: ReferenceStream) -> None:
    book = execute_direct_source(stream=stream)
    assert len(book.comparisons) == 7
    for (_, actual), expected in zip(book.source_summary, CACHES, strict=True):
        assert abs(actual - Decimal(expected)) < Decimal("1e-12")  # cache arithmetic only
    for (_, actual_length), expected in zip(book.paths.lengths, GEOMETRY, strict=True):
        assert abs(actual_length.magnitude - Decimal(expected)) < Decimal("1e-57")
    assert book.source_summary[1][1] == book.source_summary[5][1]
    assert book.paths.hole_inventory == ("BRACE:B1", "BRACE:B2", "COLUMN:B1", "COLUMN:B2")
    assert book.coverage == "NOT_ESTABLISHED"
    assert not book.public_activation


def test_independent_fraction_capacities_and_repeated_temperature_trace() -> None:
    book = execute_direct_source()
    column = book.comparisons[4]
    expected = Fraction(2) * Fraction(1, 2) * Fraction(3, 8) * Fraction(18, 4) * Fraction(85, 100)
    assert column.capacities[0] == q(str(float(expected)), Unit.KIP)
    assert column.capacities[0] == column.capacities[1]
    assert any("D31" in entry and "twice" in entry for entry in book.factor_ledger)
    assert any("D221" in entry and "twice" in entry for entry in book.factor_ledger)
    assert any("CW" in entry for entry in book.factor_ledger)
    assert "REINFORCEMENT_ABSENT" in book.optional_state


@pytest.mark.parametrize(
    ("angle", "span", "xb", "xc", "tb", "tc"),
    [
        ("25", "1.5", ".6", "1.2", ".4", ".3"),
        ("45", "2.1", ".8", "1.4", ".6", ".45"),
        ("60", "1.25", ".5", ".7", ".55", ".4"),
    ],
)
def test_fresh_parametric_paths_against_independent_float_oracle(
    angle: str, span: str, xb: str, xc: str, tb: str, tc: str
) -> None:
    g = DirectGeometry(Decimal(angle), q(span), q(xb), q(xc), q(tb), q(tc))
    book = execute_direct_source(geometry=g)
    a, b, c, d, e, f = map(float, (angle, span, xb, xc, tb, tc))
    co, si = cos(radians(a)), sin(radians(a))
    fs = 1.125 * 0.85
    expected = 0.0134 / (2 * (2 * d / si * f * fs)) + 0.09155 / (2 * (2 * d / co * f * fs))
    assert float(book.comparisons[5].utilization) == pytest.approx(expected, rel=1e-14)
    expected_global = 0.0134 / (2 * d / si * f * fs + b * si * f * 2.5 * 0.85 * 0.85) + 0.09155 / (
        2 * d / co * f * fs + b / co * f * 2.5 * 0.85
    )
    assert float(book.comparisons[6].utilization) == pytest.approx(expected_global, rel=1e-14)
    assert float(dict(book.paths.lengths)["L55"].magnitude) == pytest.approx(c / co)
    assert book.geometry.brace_thickness == q(tb)
    assert book.geometry.column_thickness == q(tc)
    assert e != f


def test_zero_scaling_overload_historical_literal_and_corrected_status() -> None:
    zero = execute_direct_source(shear=q("0", Unit.KIP), axial=q("0", Unit.KIP))
    assert all(row.utilization == 0 for row in zero.comparisons)
    a = execute_direct_source()
    b = execute_direct_source(shear=q("26.8", Unit.LBF), axial=q("183.1", Unit.LBF))
    assert all(
        abs(y.utilization / 2 - x.utilization) < Decimal("1e-27")
        for x, y in zip(a.comparisons, b.comparisons, strict=True)
    )
    historic = execute_direct_source(
        axial=q("6000", Unit.LBF), stream=ReferenceStream.HISTORICAL_REPLICATION
    )
    corrected = execute_direct_source(axial=q("6000", Unit.LBF))
    assert historic.comparisons[1].utilization > 1
    assert historic.bolt_status == "OK"
    assert corrected.bolt_status == "FAIL"
    assert corrected.original_literal_e46 == "OK"
    assert historic.comparisons == corrected.comparisons


@pytest.mark.parametrize("phi", ["0", "90", "-1", "NaN", "Infinity"])
def test_angle_singular_and_nonfinite(phi: str) -> None:
    with pytest.raises(ValueError, match=r"(requires|positive|finite|NaN|Infinity)"):
        DirectGeometry(phi=Decimal(phi))


@pytest.mark.parametrize(
    "field",
    [
        "d_span",
        "xb",
        "xc",
        "brace_thickness",
        "column_thickness",
        "diameter",
        "hole",
        "brace_v_length",
        "brace_leg",
        "column_flange",
    ],
)
def test_nonpositive_geometry(field: str) -> None:
    with pytest.raises(ValueError, match=r"(requires|positive|finite|NaN|Infinity)"):
        replace(cast(Any, DirectGeometry()), **{field: q("0")})


def test_real_hole_no_fit_and_boundary_does_not_override_method_uncertainty() -> None:
    with pytest.raises(ValueError, match="section thickness"):
        DirectGeometry(brace_thickness=q("4"))
    with pytest.raises(ValueError, match="section thickness"):
        DirectGeometry(column_thickness=q("4"))
    with pytest.raises(ValueError, match="hole cannot"):
        DirectGeometry(hole=q(".49"))
    for span in ("4", "5", ".1"):
        with pytest.raises(ValueError, match="outside"):
            execute_direct_source(geometry=DirectGeometry(d_span=q(span)))
    radius = Decimal(".563") / 2
    for delta, fit in (("-.000001", False), ("0", True), (".000001", True)):
        g = DirectGeometry(xb=q(radius + Decimal(delta)))
        assert source_paths(g).fit is fit
    assert (
        execute_direct_source(geometry=DirectGeometry(xb=q(radius))).coverage == "NOT_ESTABLISHED"
    )
    with localcontext() as context:
        context.prec = 60
        base = DirectGeometry(d_span=q(".5"), xb=q("1"), xc=q("1"))
        spacing = source_paths(base).vertical_spacing.magnitude
        for delta, fit in (("-.0000000001", True), ("0", True), (".0000000001", False)):
            boundary = replace(base, hole=q(spacing + Decimal(delta)))
            assert source_paths(boundary).fit is fit
            assert brace_rotation(boundary).nominal_fit is fit


@pytest.mark.parametrize("demand", ["-1", "NaN", "Infinity"])
def test_invalid_positive_direction_domain(demand: str) -> None:
    with pytest.raises(ValueError, match=r"(requires|positive|finite|NaN|Infinity)"):
        execute_direct_source(axial=q(demand, Unit.KIP))


@pytest.mark.parametrize("temperature", [75, 90, 100, 125, 135, 150])
def test_actual_source_temperature_points(temperature: int) -> None:
    assert execute_direct_source(temperature_f=temperature).factor_ledger[1].startswith("Calcs!D10")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature_f": True},
        {"temperature_f": 175},
        {"temperature_f": 101},
        {"reinforcement": True},
        {"reinforcement": 1},
        {"stream": "HISTORY"},
    ],
)
def test_unsupported_factor_and_reinforcement_are_not_silently_accepted(
    kwargs: dict[str, Any],
) -> None:
    with pytest.raises((ValueError, TypeError)):
        execute_direct_source(**kwargs)


def test_us_si_preserves_same_physical_reference() -> None:
    g = DirectGeometry()
    si = replace(
        g,
        brace_thickness=g.brace_thickness.to(Unit.MM),
        column_thickness=g.column_thickness.to(Unit.MM),
        d_span=g.d_span.to(Unit.MM),
        xb=g.xb.to(Unit.MM),
        xc=g.xc.to(Unit.MM),
        diameter=g.diameter.to(Unit.MM),
    )
    a = execute_direct_source()
    b = execute_direct_source(
        geometry=si, axial=q("91.55", Unit.LBF).to(Unit.N), shear=q("13.4", Unit.LBF).to(Unit.N)
    )
    assert a.source_summary == b.source_summary
    assert a.paths == b.paths


@pytest.mark.parametrize("moment", ["12", "-12", "0"])
def test_moment_link_repair_is_distinct_from_vector_equilibrium(moment: str) -> None:
    m = Decimal(moment)
    witness = moment_witness(
        DirectGeometry(), q("100", Unit.LBF), q("30", Unit.LBF), q(moment, Unit.LBF_IN)
    )
    assert witness.historical_p_addition_lb == 0
    assert witness.corrected_link_p_addition_lb == witness.historical_v_addition_lb
    assert witness.reconstructed_force_lb == (Decimal(100), Decimal(30))
    assert abs(witness.reconstructed_moment_in_lb - m) < Decimal("1e-55")
    assert "NOT_ADOPTED" in witness.applicability


def test_pure_couple_reversal_and_rotated_no_fit_are_explicit() -> None:
    g = DirectGeometry()
    a = moment_witness(g, q("0", Unit.LBF), q("0", Unit.LBF), q("12", Unit.LBF_IN))
    b = moment_witness(g, q("0", Unit.LBF), q("0", Unit.LBF), q("-12", Unit.LBF_IN))
    assert a.equilibrium_bolt_forces_lb[0][0] == b.equilibrium_bolt_forces_lb[0][0].copy_negate()
    assert a.reconstructed_force_lb == (Decimal(0), Decimal(0))
    rotated = brace_rotation(g)
    assert not rotated.nominal_fit
    assert min(rotated.brace_p_paths) < 0
    assert rotated.brace_cut_distances_x == (Decimal("-.5625"), Decimal("1.4375"))
    assert rotated.column_edge_distances_x == (Decimal(2), Decimal(0))
    fit = brace_rotation(DirectGeometry(d_span=q(".5"), xb=q("1"), xc=q("1")))
    assert fit.nominal_fit
    assert not brace_rotation(DirectGeometry(d_span=q(".1"), xb=q("1"), xc=q("1"))).nominal_fit
    assert "GEOMETRY_ONLY" in fit.disposition
    with localcontext() as ctx:
        ctx.prec = 60
        s, c = sincos(g.phi)
        projection = source_paths(g).vertical_spacing.magnitude * s
        source = dict(source_paths(g).lengths)["L64"].magnitude
        assert source != projection
        assert abs(source / c - projection) < Decimal("1e-57")
