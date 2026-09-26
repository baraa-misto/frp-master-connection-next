"""Trace presentation guards and the native combined-bolt interaction."""

from __future__ import annotations

from typing import Any

import pytest

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.reporting.substitutions import (
    _canonical,
    _property,
    single_native_substitutions,
)


def _quantity(value: str, unit: str) -> dict[str, str]:
    return {"value": value, "unit": unit}


@pytest.mark.parametrize("value", [None, {}, {"value": "1", "unit": "bogus"}])
def test_unavailable_native_quantity_is_never_fabricated(value: object) -> None:
    assert _canonical(value, Unit.MM) == "unavailable"


def test_missing_adjusted_property_remains_unavailable() -> None:
    assert _property({}, "bearing_property") == "unavailable"


@pytest.mark.parametrize(
    "check",
    [{}, {"plan": {"limit_state": "BOLT_TENSION"}}, {"equation_trace": {}}],
)
def test_incomplete_native_check_has_no_substitution(check: dict[str, Any]) -> None:
    assert single_native_substitutions(check, None, None) == []


def test_native_combined_bolt_interaction_prints_its_own_inputs_and_outputs() -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": "BOLT_COMBINED_TENSION_SHEAR"},
        "nominal_resistance": _quantity("1000", "N"),
        "equation_trace": {
            "area_trace": {"diameter": _quantity("10", "mm"), "area": _quantity("78.5", "mm2")},
            "fnt": _quantity("100", "MPa"),
            "fnv": _quantity("60", "MPa"),
            "required_shear_stress": _quantity("12", "MPa"),
            "modified_tensile_stress": _quantity("90", "MPa"),
            "shear_demand": _quantity("942", "N"),
            "design_tensile_resistance": _quantity("7000", "N"),
            "phi": "0.8",
        },
    }
    rows = dict(single_native_substitutions(check, None, None))
    assert "d(10 mm)^2 / 4" in rows["Native bolt area substitution"]
    assert "V_shear(942 N) / A_b(78.5 mm2)" in rows["Native required shear stress substitution"]
    assert "F'_nt = min[F_nt(100 MPa)" in rows["Native modified tensile stress substitution"]
    assert "native R_d(7000 N)" in rows["Native combined resistance substitution"]
    del check["equation_trace"]["area_trace"]
    missing_area = dict(single_native_substitutions(check, None, None))
    assert "unavailable" in missing_area["Native bolt area substitution"]


def test_missing_optional_layer_and_cleavage_branches_stay_unevaluated() -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": "CLEAVAGE"},
        "equation_trace": {},
    }
    assert single_native_substitutions(check, None, None) == []
    assert single_native_substitutions(check, {}, None) == []
    assert single_native_substitutions(check, {"code_mapping": {}}, None) == []


def test_bolt_tension_without_native_area_does_not_invent_a_diameter() -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": "BOLT_TENSION"},
        "equation_trace": {},
    }
    assert single_native_substitutions(check, None, None) == []


@pytest.mark.parametrize("method", ["BOLT_TENSION", "BOLT_SHEAR"])
def test_native_bolt_area_and_stress_are_printed_for_either_method(method: str) -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": method},
        "nominal_resistance": _quantity("700", "N"),
        "equation_trace": {
            "area_trace": {
                "diameter": _quantity("10", "mm"),
                "area": _quantity("78.5", "mm2"),
            },
            "nominal_stress": _quantity("100", "MPa"),
        },
    }
    rows = dict(single_native_substitutions(check, None, None))
    assert "d(10 mm)^2" in rows["Native bolt area substitution"]
    assert "F_n(100 MPa)" in rows["Native bolt substitution"]
    assert "native R_n(700 N)" in rows["Native bolt substitution"]


def test_incomplete_cleavage_branch_does_not_invent_substitution() -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": "CLEAVAGE"},
        "equation_trace": {"branch_a_factor_trace": {}},
    }
    layer: dict[str, Any] = {"code_mapping": {}}
    assert single_native_substitutions(check, layer, None) == []


def test_unknown_method_has_no_invented_native_substitution() -> None:
    check: dict[str, Any] = {
        "plan": {"limit_state": "FUTURE_METHOD"},
        "equation_trace": {},
    }
    assert single_native_substitutions(check, {"code_mapping": {}}, None) == []
