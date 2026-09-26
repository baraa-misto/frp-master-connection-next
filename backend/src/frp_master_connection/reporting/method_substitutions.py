"""Native operand bindings for executed non-multi-row report methods.

The symbolic expressions live in ``method_records``. These bindings put the
actual sealed input, intermediate, and result beside each symbol; they never
produce a calculation result or alter the native trace.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from frp_master_connection.reporting.units import DisplayUnits, display_quantity

Binding = tuple[str, str, str | None]

_BINDINGS: dict[str, tuple[Binding, ...]] = {
    "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1": (
        ("P", "calculation_input.actions.axial_force_l", None),
        ("M", "calculation_input.actions.major_moment_t", None),
        ("A_i", "components[0].area", None),
        ("A", "section_properties.total_area", None),
        ("y_i", "components[0].centroid_v", None),
        ("I_i", "components[0].centroidal_inertia", None),
        ("I", "section_properties.total_major_inertia", None),
        ("N_i", "components[0].wrench.force_lvt.l", None),
        ("M_local,i", "components[0].wrench.moment_lvt.t", None),
        ("M_global,i", "components[0].global_major_moment", None),
    ),
    "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1": (
        ("P", "calculation_input.actions.axial_force_l", None),
        ("M_major", "calculation_input.actions.major_moment_t", None),
        ("A_i", "components[0].area", None),
        ("A", "section_properties.total_area", None),
        ("v_i", "components[0].centroid_v", None),
        ("I_major,i", "components[0].major_centroidal_inertia", None),
        ("I_major", "section_properties.total_major_inertia", None),
        ("N_i", "components[0].wrench.force_lvt.l", None),
        ("M_local,i", "components[0].wrench.moment_lvt.t", None),
        ("M_global,i", "components[0].global_major_moment", None),
    ),
    "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1": (
        ("h_m", "median_web_height", None),
        ("b_m", "median_flange_width", None),
        ("I_m", "median_major_inertia", None),
        ("e", "rational_web_offset", None),
        ("t_sc", "rational_coordinate_t", None),
        ("t_sc,absolute", "absolute_coordinate_t", None),
    ),
    "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1": (
        ("v_f", "flange_reference_v", None),
        ("v_o", "outer_reference_v", None),
        ("v_i", "inner_reference_v", None),
        ("F", "flange_force", None),
        ("M_local", "flange_local_moment", None),
        ("F_o", "outer_force", None),
        ("F_i", "inner_total_force", None),
        ("F_each-inner", "inner_positive_force", None),
        ("force residual", "force_residual", None),
        ("moment residual", "local_moment_residual", None),
    ),
    "RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1": (
        ("t_web", "web_reference_t", None),
        ("t_b", "back_reference_t", None),
        ("t_o", "opening_reference_t", None),
        ("N_web", "web_normal_force", None),
        ("V_web", "web_major_shear", None),
        ("T_free", "web_free_torsion", None),
        ("V_b", "back_major_shear", None),
        ("V_o", "opening_major_shear", None),
        ("N_each", "back_normal_force", None),
        ("M_each", "back_local_major_moment", None),
        ("shear residual", "major_shear_residual", None),
        ("torsion residual", "free_torsion_residual", None),
    ),
    "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1": (
        ("r_source", "request.member_action.reference", None),
        ("F_source", "request.member_action.force", None),
        ("M_source", "request.member_action.moment", None),
        ("r_target", "connector_on_support.reference", None),
        ("F_target", "connector_on_support.force", None),
        ("M_target", "connector_on_support.moment", None),
        ("reaction F", "support_on_connector.force", None),
        ("reaction M", "support_on_connector.moment", None),
        ("equilibrium F", "equilibrium.force", None),
        ("equilibrium M", "equilibrium.moment", None),
    ),
    "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1": (
        ("r_ref,a", "solution.reference[0]", "mm"),
        ("F_a", "solution.force[0]", "N"),
        ("F_b", "solution.force[1]", "N"),
        ("M_ref", "solution.reference_moment", "N-mm"),
        ("c_a", "solution.centroid[0]", "mm"),
        ("J", "solution.polar_sum", "mm2"),
        ("M_c", "solution.centroid_moment", "N-mm"),
        ("delta_a,first", "solution.bolts[0].delta[0]", "mm"),
        ("F_direct,a,first", "solution.bolts[0].direct[0]", "N"),
        ("F_correction,a,first", "solution.bolts[0].correction[0]", "N"),
        ("F_total,a,first", "solution.bolts[0].total[0]", "N"),
    ),
    "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION": (
        ("A_net,eff", "effective_net_area_per_unit_width", None),
        ("F_t,L,adjusted", "adjusted_property.adjusted_property", None),
        ("R_n", "nominal_strength", None),
        ("phi", "resistance_factor", None),
        ("lambda", "time_effect_factor.value", None),
        ("R_d", "design_strength", None),
    ),
    "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1": (
        ("A", "plate_area_in2", "in2"),
        ("I", "plate_inertia_in4", "in4"),
        ("c", "extreme_fiber_in", "in"),
        ("N_plate", "critical_sections[0].plate_axial_force", None),
        ("M_plate", "critical_sections[0].plate_moment", None),
        ("V_plate", "critical_sections[0].plate_shear_force", None),
        ("sigma", "critical_sections[0].signed_normal_stress", None),
        ("tau", "critical_sections[0].signed_shear_stress", None),
        ("F_normal,d", "critical_sections[0].normal_design_stress", None),
        ("F_shear,d", "critical_sections[0].shear_design_stress", None),
        ("U", "critical_sections[0].rational_utilization", None),
    ),
    "ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1": (
        ("L_eff", "length", None),
        ("F_sh,LT,adjusted", "factors.property_traces[0].adjusted_property", None),
        ("R_n", "factors.nominal_resistance", None),
        ("phi", "factors.phi", None),
        ("R_d", "factors.design_resistance", None),
        ("demand", "demand", None),
        ("U", "utilization", None),
    ),
    "NATIVE_ASCE_8_5": (
        ("F_br,adjusted", "native_trace.bearing_property.adjusted_property", None),
        ("C_thread", "native_trace.thread_factor", None),
        ("R_n", "native_trace.factor_trace.nominal_resistance", None),
        ("phi", "native_trace.factor_trace.phi", None),
        ("lambda", "native_trace.factor_trace.lambda_factor", None),
        ("C_lap", "native_trace.factor_trace.c_lap", None),
        ("C_delta", "native_trace.factor_trace.c_delta", None),
        ("R_d", "resistance", None),
        ("demand", "demand", None),
        ("U", "native_comparison.utilization", None),
    ),
    "DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1": (
        ("f_row", "rows[0].row_fraction", None),
        ("P_row", "rows[0].signed_row_force", None),
        ("f_side", "rows[0].side_fraction", None),
        ("P_side,negative", "rows[0].negative_at_bolt.force", None),
        ("P_side,positive", "rows[0].positive_at_bolt.force", None),
        ("shaft transfer", "shafts[0].signed_layer_transfers[0]", None),
        ("first physical cut", "shafts[0].signed_cuts[0]", None),
        ("first plane demand", "shafts[0].shear_plane_demands[0]", None),
        ("terminal residual", "shafts[0].terminal_residual", None),
    ),
    "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1": (
        ("interface action F", "action_reaction[0].action_on_plate.force", None),
        ("interface reaction F", "action_reaction[0].reaction_on_member.force", None),
        ("interface action M", "action_reaction[0].action_on_plate.moment", None),
        ("interface reaction M", "action_reaction[0].reaction_on_member.moment", None),
        ("first cut N", "cuts.cuts[0].cut_N_N", "N"),
        ("first cut V", "cuts.cuts[0].cut_V_N", "N"),
        ("first cut M", "cuts.cuts[0].cut_M_Nmm", "N-mm"),
    ),
    "SSMC_ACTUAL_POLYGON_CUT_FREE_BODY_RC1": (
        ("A_net", "net_area_mm2", "mm2"),
        ("I_net", "second_moment_mm4", "mm4"),
        ("N", "cut_N_N", "N"),
        ("V", "cut_V_N", "N"),
        ("M", "cut_M_Nmm", "N-mm"),
        ("sigma_negative", "sigma_negative_MPa", "MPa"),
        ("sigma_positive", "sigma_positive_MPa", "MPa"),
        ("tau_average", "average_shear_MPa", "MPa"),
    ),
}


def _at(record: dict[str, Any], path: str) -> object:
    current: Any = record
    for part in path.replace("[", ".").replace("]", "").split("."):
        try:
            current = current[int(part)] if isinstance(current, list) else current[part]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Executed method lacks native operand {path}") from exc
    if current is None:
        raise ValueError(f"Executed method lacks native operand {path}")
    return current


def _shown(value: object, system: DisplayUnits, unit: str | None = None) -> str:
    if isinstance(value, dict):
        if "value" in value and "unit" in value:
            return display_quantity(value, system)
        if "numerator" in value and "denominator" in value:
            if unit is None:
                raise ValueError("Exact native rational operand has no physical unit")
            magnitude = Decimal(str(value["numerator"])) / Decimal(str(value["denominator"]))
            return display_quantity({"value": str(magnitude), "unit": unit}, system)
        return (
            "(" + ", ".join(f"{key}={_shown(child, system)}" for key, child in value.items()) + ")"
        )
    if isinstance(value, list):
        return "(" + ", ".join(_shown(child, system, unit) for child in value) + ")"
    if unit is not None:
        return display_quantity({"value": str(value), "unit": unit}, system)
    return str(value)


def native_method_substitution(method: str, record: dict[str, Any], system: DisplayUnits) -> str:
    """Bind every listed symbol to its native value or fail this adapter."""

    bindings = _BINDINGS.get(method)
    if bindings is None:
        raise ValueError(f"Executed method has no REPORT1 numerical binding: {method}")
    return "; ".join(
        f"{symbol} = {_shown(_at(record, path), system, unit)}" for symbol, path, unit in bindings
    )


__all__ = ("native_method_substitution",)
