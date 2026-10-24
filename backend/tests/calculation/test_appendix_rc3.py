"""Independent printed-equation benchmarks; successor remains inactive in Direct."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation.appendix_rc3 import (
    ENGINE_ID,
    GOLDEN_ID,
    METHOD_ID,
    PREDECESSOR_ID,
    SPEC_ID,
    AppendixRC3Trace,
    full_first_row_resistance_rc3,
)
from frp_master_connection.calculation.equations import (
    INTERNAL_DECIMAL_PRECISION,
    EndUsePropertyTrace,
)
from frp_master_connection.calculation.multirow import (
    MaterialDirection,
    PultrudedElementClassification,
)
from frp_master_connection.calculation.multirow_equations import full_first_row_resistance
from frp_master_connection.calculation.properties import FRPPropertyKind
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus

GOLDEN = cast(
    dict[str, Any],
    json.loads(
        (
            Path(__file__).parents[1]
            / "golden/calculation_slice_2_appendix_golden_benchmarks_rc3.json"
        ).read_text(encoding="utf-8")
    ),
)
CASES = cast(list[dict[str, Any]], GOLDEN["cases"])


def arguments(case: dict[str, Any], *, si: bool = False) -> dict[str, Any]:
    """Convert identical physical geometry without deriving any reference result."""
    operands = case["inputs"]

    def length(value: str) -> PhysicalQuantity:
        q = PhysicalQuantity.of(value, Unit.IN)
        return q.to(Unit.MM) if si else q

    stress = PhysicalQuantity.of(operands["ft_ksi"], Unit.KSI).to(Unit.MPA)
    direction = MaterialDirection(case["direction"])
    prop = EndUsePropertyTrace(
        FRPPropertyKind.FT_L
        if direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FT_T,
        stress,
        QualificationStatus.QUALIFIED,
        Decimal(1),
        Decimal(1),
        Decimal(1),
        stress,
    )
    return {
        "width": length(operands["w"]),
        "bolt_diameter": length(operands["d"]),
        "nominal_hole_diameter": length(operands["dn"]),
        "thickness": length(operands["t"]),
        "unloaded_end_e1": length(operands["e1"]),
        "tensile_property": prop,
        "direction": direction,
        "element_classification": PultrudedElementClassification.SHAPE,
        "bolts_per_row": case["bolts_per_row"],
        "row_count": case["row_count"],
        "gauge": None if operands["gauge"] is None else length(operands["gauge"]),
        "lbr": Decimal(operands["lbr"]),
        "lap_factor_c_lap": Decimal(operands["lap"]),
        "pitch_factor_c_delta": Decimal(operands["pitch"]),
        "time_effect_factor_lambda": Decimal(operands["time"]),
    }


def values(trace: AppendixRC3Trace) -> dict[str, Decimal]:
    result = {
        name: cast(Decimal, getattr(trace, name))
        for name in (
            "spr",
            "theta",
            "ratio",
            "ratio_times_theta",
            "knt",
            "kop",
            "coefficient_a",
            "coefficient_b",
            "denominator",
        )
    }
    result["nominal_n"] = trace.factor_trace.equation_nominal_resistance.to(Unit.N).magnitude
    result["design_n"] = trace.factor_trace.design_resistance.to(Unit.N).magnitude
    return result


def serialized(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1E-12"), rounding=ROUND_HALF_EVEN)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
@pytest.mark.parametrize("si", [False, True], ids=["US", "SI"])
def test_independent_reference(case: dict[str, Any], si: bool) -> None:
    trace = full_first_row_resistance_rc3(**arguments(case, si=si))
    assert trace.engine_id == ENGINE_ID != PREDECESSOR_ID
    assert trace.spec_id == SPEC_ID
    assert trace.golden_id == GOLDEN_ID
    assert trace.method_id == METHOD_ID != "FIRST_ROW_COMMENTARY_FULL"
    assert trace.predecessor_id == PREDECESSOR_ID
    assert trace.source_equation == case["equation"]
    assert trace.source_page == (112 if case["equation"] == "CA8-2" else 113)
    assert trace.theta_branch.value == case["theta_branch"]
    assert trace.retained_policy_notices == ()
    assert {k: serialized(v) for k, v in values(trace).items()} == {
        k: Decimal(v) for k, v in case["expected_12"].items()
    }
    assert values(trace) == values(full_first_row_resistance_rc3(**arguments(case, si=not si)))
    assert "ratio_power" not in asdict(trace)
    if case["state"] in {"unit", "exact", "above"}:
        assert trace.theta == 1
    else:
        assert trace.theta < 1


@pytest.mark.parametrize("case", [CASES[0], CASES[1]], ids=["A3-nonunit", "unit-identity"])
def test_dual_frozen_successor_witness(case: dict[str, Any]) -> None:
    args = arguments(case)
    successor = full_first_row_resistance_rc3(**args)
    args.pop("row_count")
    args["bolt_count"] = args.pop("bolts_per_row")
    args["net_hole_diameter"] = args.pop("nominal_hole_diameter")
    with localcontext() as context:
        context.prec = INTERNAL_DECIMAL_PRECISION
        frozen = full_first_row_resistance(**args)
    assert successor.kop == frozen.kop
    if case["state"] == "nonunit":
        assert serialized(successor.knt) == Decimal("0.676893939394")
        assert serialized(frozen.knt) == Decimal("0.671426574084")
        assert successor.knt != frozen.knt
    else:
        assert serialized(successor.knt) == serialized(frozen.knt)
        assert serialized(successor.factor_trace.design_resistance.magnitude) == serialized(
            frozen.factor_trace.design_resistance.magnitude
        )


@pytest.mark.parametrize("direction", list(MaterialDirection))
@pytest.mark.parametrize("lbr", [Decimal(0), Decimal(1)])
def test_retained_plate_and_endpoint_policy(direction: MaterialDirection, lbr: Decimal) -> None:
    args = arguments(CASES[0])
    args.update(
        direction=direction, element_classification=PultrudedElementClassification.PLATE, lbr=lbr
    )
    trace = full_first_row_resistance_rc3(**args)
    assert trace.c_op_i == Decimal(".5")
    if direction is MaterialDirection.LONGITUDINAL:
        assert trace.c_i == Decimal(".4")
        assert trace.retained_policy_notices == ()
    else:
        assert trace.c_i == Decimal(".5")
        assert trace.retained_policy_notices == (
            "RC2_TRANSVERSE_PLATE_C_T_0_50_CONSERVATIVE_POLICY_RETAINED",
        )
    assert trace.denominator == (trace.coefficient_b if lbr == 0 else trace.coefficient_a)


@pytest.mark.parametrize(
    ("name", "value", "error"),
    [
        ("row_count", True, TypeError),
        ("row_count", "2", TypeError),
        ("row_count", 1, ValueError),
        ("row_count", 4, ValueError),
        ("bolts_per_row", False, TypeError),
        ("bolts_per_row", Decimal(2), TypeError),
        ("bolts_per_row", 0, ValueError),
        ("bolts_per_row", 4, ValueError),
        ("direction", "LONGITUDINAL", TypeError),
        ("element_classification", "SHAPE", TypeError),
        ("tensile_property", None, TypeError),
        ("lbr", Decimal("-.01"), ValueError),
        ("lbr", Decimal("1.01"), ValueError),
        ("width", "3.25", ValueError),
        ("width", PhysicalQuantity.of(3, Unit.N), ValueError),
        ("width", PhysicalQuantity.of(0, Unit.IN), ValueError),
        ("thickness", PhysicalQuantity.of(-1, Unit.IN), ValueError),
        ("width", PhysicalQuantity.of(".5", Unit.IN), ValueError),
        ("width", PhysicalQuantity.of(".55", Unit.IN), ValueError),
    ],
)
def test_bounded_input_contract(name: str, value: object, error: type[Exception]) -> None:
    args = arguments(CASES[0])
    args[name] = value
    with pytest.raises(error):
        full_first_row_resistance_rc3(**args)


@pytest.mark.parametrize("gauge", [None, PhysicalQuantity.of(".5", Unit.IN)])
def test_invalid_multi_across_spacing(gauge: PhysicalQuantity | None) -> None:
    args = arguments(CASES[10])  # longitudinal n=3, valid width for three holes
    args["gauge"] = gauge
    with pytest.raises(ValueError, match="require"):
        full_first_row_resistance_rc3(**args)


def test_property_dimension_is_typed() -> None:
    args = arguments(CASES[0])
    args["tensile_property"] = replace(
        args["tensile_property"], adjusted_property=PhysicalQuantity.of(1, Unit.N)
    )
    with pytest.raises(ValueError, match="Expected a STRESS"):
        full_first_row_resistance_rc3(**args)
