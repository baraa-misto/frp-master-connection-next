"""Faithful display of already executed multi-row numerical stages.

Every operand comes from the sealed native check trace or its identified
canonical layer/bolt record. This module never supplies a resistance.
"""

from __future__ import annotations

from typing import Any

from frp_master_connection.reporting.units import DisplayUnits, display_quantity


def _record(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Executed multi-row trace lacks {key}")
    return value


def _quantity(parent: dict[str, Any], key: str, system: DisplayUnits) -> str:
    value = _record(parent, key)
    if "value" not in value or "unit" not in value:
        raise ValueError(f"Executed multi-row trace lacks quantity {key}")
    return display_quantity(value, system)


def _scalar(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str | int | float):
        raise ValueError(f"Executed multi-row trace lacks scalar {key}")
    return str(value)


def _property(trace: dict[str, Any], key: str, system: DisplayUnits) -> str:
    return _quantity(_record(trace, key), "adjusted_property", system)


def _layer_thickness(visual: dict[str, Any], check: dict[str, Any], system: DisplayUnits) -> str:
    layers = visual.get("layers")
    if not isinstance(layers, list):
        raise ValueError("Executed multi-row check lacks canonical layers")
    selected = [
        layer
        for layer in layers
        if isinstance(layer, dict) and layer.get("layer_id") == check.get("layer_id")
    ]
    if len(selected) != 1:
        raise ValueError("Executed multi-row check has no unique canonical layer")
    return _quantity(selected[0], "thickness", system)


def _bolt_diameter(visual: dict[str, Any], check: dict[str, Any], system: DisplayUnits) -> str:
    bolts = visual.get("bolts")
    if not isinstance(bolts, list):
        raise ValueError("Executed multi-row check lacks canonical bolts")
    selected = [
        bolt
        for bolt in bolts
        if isinstance(bolt, dict) and bolt.get("bolt_id") == check.get("bolt_id")
    ]
    if len(selected) != 1:
        raise ValueError("Executed multi-row check has no unique canonical bolt")
    return _quantity(selected[0], "bolt_diameter", system)


def _first_row_full(
    trace: dict[str, Any], thickness: str, nominal: str, system: DisplayUnits
) -> str:
    width = _quantity(trace, "width", system)
    force = _property(trace, "tensile_property", system)
    return (
        f"S_pr = {_scalar(trace, 'spr')}; theta = {_scalar(trace, 'theta')}; "
        f"C_i = {_scalar(trace, 'appendix_coefficient_c_i')}; "
        f"C_op = {_scalar(trace, 'appendix_open_hole_coefficient_c_op_i')}; "
        f"K_nt = {_scalar(trace, 'knt')}; K_op = {_scalar(trace, 'kop')}; "
        f"A = {_scalar(trace, 'coefficient_a')}; B = {_scalar(trace, 'coefficient_b')}; "
        f"L_br = {_scalar(trace, 'lbr')}; denominator = {_scalar(trace, 'denominator')}; "
        f"R_n = w({width}) x t({thickness}) x F_t({force}) / "
        f"denominator({_scalar(trace, 'denominator')}) = {nominal}"
    )


def multirow_native_substitution(
    check: dict[str, Any], visual: dict[str, Any], system: DisplayUnits
) -> str:
    """Return the actual method operands and native result or fail closed."""

    method = str(check.get("equation_method"))
    trace = _record(check, "equation_trace")
    nominal = _quantity(check, "equation_nominal_resistance", system)
    if method == "PIN_BEARING":
        return (
            f"R_n = t({_layer_thickness(visual, check, system)}) x "
            f"d({_bolt_diameter(visual, check, system)}) x "
            f"F_br({_property(trace, 'bearing_property', system)}) x "
            f"C_thread({_scalar(trace, 'thread_factor')}) = {nominal}"
        )
    if method == "FIRST_ROW_SIMPLIFIED":
        return (
            f"R_n = 0.2 x w({_quantity(trace, 'width', system)}) x "
            f"t({_quantity(trace, 'thickness', system)}) x "
            f"F_t({_property(trace, 'tensile_property', system)}) = {nominal}"
        )
    if method == "FIRST_ROW_COMMENTARY_FULL":
        return _first_row_full(trace, _layer_thickness(visual, check, system), nominal, system)
    if method == "FIRST_ROW_RATIONAL_LOWER_ENVELOPE":
        simplified = _record(trace, "simplified")
        full = _record(trace, "full_unknown_lbr")
        selected = _quantity(trace, "selected_design_resistance", system)
        endpoints = []
        for key in ("lbr_0", "lbr_1"):
            endpoint = _record(full, key)
            factors = _record(endpoint, "factor_trace")
            endpoints.append(
                f"{key}: "
                + _first_row_full(
                    endpoint,
                    _layer_thickness(visual, check, system),
                    _quantity(factors, "equation_nominal_resistance", system),
                    system,
                )
                + f"; R_d = {_quantity(factors, 'design_resistance', system)}"
            )
        simplified_factors = _record(simplified, "factor_trace")
        return (
            f"Simplified: R_n = 0.2 x w({_quantity(simplified, 'width', system)}) x "
            f"t({_quantity(simplified, 'thickness', system)}) x "
            f"F_t({_property(simplified, 'tensile_property', system)}) = "
            f"{_quantity(simplified_factors, 'equation_nominal_resistance', system)}; "
            f"R_d = {_quantity(simplified_factors, 'design_resistance', system)}. "
            + ". ".join(endpoints)
            + f". Native lower envelope R_d = {selected}"
        )
    if method in {
        "INTERROW_ASCE_EQ_8_12",
        "INTERROW_ASCE_EQ_8_13",
        "INTERROW_RATIONAL_EXTENSION_EQ_8_13",
    }:
        pitches = trace.get("pitches")
        if not isinstance(pitches, list) or not pitches:
            raise ValueError("Executed inter-row check lacks physical pitches")
        pitch_values = [display_quantity(pitch, system) for pitch in pitches]
        if any(value == "Not supplied" for value in pitch_values):
            raise ValueError("Executed inter-row check has a malformed pitch")
        thickness = _layer_thickness(visual, check, system)
        shear = _property(trace, "shear_property", system)
        if method == "INTERROW_ASCE_EQ_8_12":
            return (
                f"R_n = 1.4 x [e_1({_quantity(trace, 'unloaded_end_e1', system)}) - "
                f"d_n({_quantity(trace, 'net_hole_diameter', system)}) / 2 + "
                f"p({pitch_values[0]})] x t({thickness}) x F_s({shear}) = {nominal}"
            )
        return (
            f"R_n = 2 x sum(pitches: {', '.join(pitch_values)}) x "
            f"t({thickness}) x F_s({shear}) = {nominal}"
        )
    if method in {"BLOCK_SHEAR_ASCE_EQ_8_14A", "BLOCK_SHEAR_ASCE_EQ_8_14B"}:
        tension_factor = "1" if method.endswith("14A") else "0.5"
        return (
            f"R_n = 0.5 x [A_nv({_quantity(trace, 'net_shear_area', system)}) x "
            f"F_s({_property(trace, 'shear_property', system)}) + "
            f"{tension_factor} x A_nt({_quantity(trace, 'net_tension_area', system)}) x "
            f"F_t({_property(trace, 'tensile_property', system)})] = {nominal}; "
            f"native shear component {_quantity(trace, 'shear_component', system)}, "
            f"tension component {_quantity(trace, 'tension_component', system)}"
        )
    raise ValueError(f"Executed multi-row method lacks a REPORT1 substitution: {method}")


__all__ = ("multirow_native_substitution",)
