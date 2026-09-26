"""Read-only substitutions from native single-bolt traces and resolved geometry.

Values are converted only for display. No equation is evaluated in this module.
"""

from __future__ import annotations

import re
from typing import Any

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.reporting.units import DisplayUnits, display_quantity

_NATIVE_QUANTITY = re.compile(
    r"(?<![\w.])(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?) (mm2|mm|MPa|N)(?![\w])"
)


def _display_rows(rows: list[tuple[str, str]], system: DisplayUnits) -> list[tuple[str, str]]:
    if system == "INHERIT":
        return rows

    def convert(match: re.Match[str]) -> str:
        return display_quantity({"value": match.group(1), "unit": match.group(2)}, system)

    return [(name, _NATIVE_QUANTITY.sub(convert, expression)) for name, expression in rows]


def _canonical(value: object, target: Unit) -> str:
    if not isinstance(value, dict):
        return "unavailable"
    try:
        return str(
            PhysicalQuantity.of(str(value["value"]), Unit(str(value["unit"]))).to(target).magnitude
        )
    except KeyError, TypeError, ValueError:
        return "unavailable"


def _property(trace: dict[str, Any], key: str) -> str:
    record = trace.get(key)
    if not isinstance(record, dict):
        return "unavailable"
    return _canonical(record.get("adjusted_property"), Unit.MPA)


def single_native_substitutions(
    check: dict[str, Any],
    layer: dict[str, Any] | None,
    fastener: dict[str, Any] | None,
    system: DisplayUnits = "INHERIT",
) -> list[tuple[str, str]]:
    """Format actual input quantities beside the native result without recomputing it."""

    plan = check.get("plan")
    trace = check.get("equation_trace")
    if not isinstance(plan, dict) or not isinstance(trace, dict):
        return []
    method = plan.get("limit_state")
    native_nominal = _canonical(check.get("nominal_resistance"), Unit.N)
    rows: list[tuple[str, str]] = []
    if method in {"BOLT_TENSION", "BOLT_SHEAR"}:
        area = trace.get("area_trace")
        if isinstance(area, dict):
            rows.append(
                (
                    "Native bolt area substitution",
                    f"A_b = pi d({_canonical(area.get('diameter'), Unit.MM)} mm)^2 / 4 "
                    f"= native A_b({_canonical(area.get('area'), Unit.MM2)} mm2)",
                )
            )
            rows.append(
                (
                    "Native bolt substitution",
                    f"A_b({_canonical(area.get('area'), Unit.MM2)} mm2) x "
                    f"F_n({_canonical(trace.get('nominal_stress'), Unit.MPA)} MPa) "
                    f"= native R_n({native_nominal} N)",
                )
            )
    elif method == "BOLT_COMBINED_TENSION_SHEAR":
        area = trace.get("area_trace")
        bolt_area = (
            _canonical(area.get("area"), Unit.MM2) if isinstance(area, dict) else "unavailable"
        )
        diameter = (
            _canonical(area.get("diameter"), Unit.MM) if isinstance(area, dict) else "unavailable"
        )
        fnt = _canonical(trace.get("fnt"), Unit.MPA)
        fnv = _canonical(trace.get("fnv"), Unit.MPA)
        fv = _canonical(trace.get("required_shear_stress"), Unit.MPA)
        modified = _canonical(trace.get("modified_tensile_stress"), Unit.MPA)
        rows.extend(
            [
                (
                    "Native bolt area substitution",
                    f"A_b = pi d({diameter} mm)^2 / 4 = native A_b({bolt_area} mm2)",
                ),
                (
                    "Native required shear stress substitution",
                    f"f_v = V_shear({_canonical(trace.get('shear_demand'), Unit.N)} N) "
                    f"/ A_b({bolt_area} mm2) = "
                    f"native f_v({fv} MPa)",
                ),
                (
                    "Native modified tensile stress substitution",
                    f"F'_nt = min[F_nt({fnt} MPa), "
                    f"1.3 F_nt - F_nt f_v({fv} MPa) "
                    f"/ (phi({trace.get('phi')}) F_nv({fnv} MPa))] "
                    f"= native F'_nt({modified} MPa)",
                ),
                (
                    "Native combined resistance substitution",
                    f"R_d = phi({trace.get('phi')}) A_b({bolt_area} mm2) "
                    f"F'_nt({modified} MPa) "
                    f"= native R_d({_canonical(trace.get('design_tensile_resistance'), Unit.N)} N)",
                ),
            ]
        )
    if layer is None:
        return _display_rows(rows, system)
    code = layer.get("code_mapping")
    if not isinstance(code, dict):
        return _display_rows(rows, system)
    t = _canonical(code.get("layer_thickness"), Unit.MM)
    d = _canonical(code.get("bolt_diameter"), Unit.MM)
    dn = _canonical(code.get("hole_diameter"), Unit.MM)
    e1 = _canonical(code.get("forward_e1"), Unit.MM)
    e2 = _canonical(code.get("e2_min"), Unit.MM)
    w = _canonical(code.get("effective_width"), Unit.MM)
    if method == "PULL_THROUGH":
        washer = fastener.get("washer_geometry") if isinstance(fastener, dict) else None
        washer_d = (
            _canonical(washer.get("outside_diameter"), Unit.MM)
            if isinstance(washer, dict)
            else "unavailable"
        )
        rows.extend(
            [
                (
                    "Native pull-through branch 8-4a substitution",
                    f"R_n,A = 0.5 pi D_w({washer_d} mm) t({t} mm) "
                    f"F_LT({_property(trace, 'through_thickness_property')} MPa) "
                    f"= native R_n,A({_canonical(trace.get('branch_8_4a_nominal'), Unit.N)} N)",
                ),
                (
                    "Native pull-through branch 8-4b substitution",
                    f"R_n,B = 0.4 pi D_w({washer_d} mm) t({t} mm) "
                    f"F_INT({_property(trace, 'interlaminar_property')} MPa) "
                    f"= native R_n,B({_canonical(trace.get('branch_8_4b_nominal'), Unit.N)} N)",
                ),
                ("Native governing branch", str(trace.get("governing_branches"))),
            ]
        )
    elif method == "PIN_BEARING":
        rows.append(
            (
                "Native nominal substitution",
                f"R_n = t({t} mm) x d({d} mm) x "
                f"F_br({_property(trace, 'bearing_property')} MPa) x "
                f"C_thread({trace.get('thread_factor')}) = native R_n({native_nominal} N)",
            )
        )
    elif method == "NET_SECTION_TENSION":
        rows.extend(
            [
                (
                    "Native K_nt substitution",
                    f"K_nt = 1 + C_i({trace.get('ci')})[S_pr({trace.get('spr')}) "
                    f"- 1.5 r^theta({trace.get('ratio_power')})] = {trace.get('knt')}",
                ),
                (
                    "Native nominal substitution",
                    f"R_n = [w({w} mm) - d_n({dn} mm)] x t({t} mm) x "
                    f"F_t({_property(trace, 'tensile_property')} MPa) / "
                    f"K_nt({trace.get('knt')}) = native R_n({native_nominal} N)",
                ),
            ]
        )
    elif method == "SHEAR_OUT":
        rows.append(
            (
                "Native nominal substitution",
                f"R_n = 1.4[e_1({e1} mm) - d_n({dn} mm)/2] x t({t} mm) x "
                f"F_s({_property(trace, 'shear_property')} MPa) = native R_n({native_nominal} N)",
            )
        )
    elif method == "CLEAVAGE":
        branch_a = trace.get("branch_a_factor_trace")
        branch_b = trace.get("branch_b_factor_trace")
        bearing = trace.get("bearing_trace")
        if isinstance(branch_a, dict) and isinstance(branch_b, dict):
            rows.append(
                (
                    "Native cleavage branch A substitution",
                    f"R_n,A = 0.15[(2 e_2({e2} mm) - d_n({dn} mm)) "
                    f"F_t({_property(trace, 'tensile_property')} MPa) + "
                    f"2 e_1({e1} mm) F_s({_property(trace, 'shear_property')} MPa)] "
                    f"t({t} mm) = native R_n,A("
                    f"{_canonical(branch_a.get('nominal_resistance'), Unit.N)} N)",
                )
            )
            bearing_nominal = (
                _canonical(bearing.get("factor_trace", {}).get("nominal_resistance"), Unit.N)
                if isinstance(bearing, dict) and isinstance(bearing.get("factor_trace"), dict)
                else "unavailable"
            )
            rows.append(
                (
                    "Native cleavage branch B substitution",
                    f"R_n,B = R_n,bearing({bearing_nominal} N) x "
                    f"C_B({trace.get('branch_b_coefficient')}) "
                    f"= native R_n,B({_canonical(branch_b.get('nominal_resistance'), Unit.N)} N); "
                    f"e_1/d={trace.get('branch_b_condition_e1_over_d')}",
                )
            )
            rows.append(("Native selected branch", str(trace.get("governing_branches"))))
    return _display_rows(rows, system)


__all__ = ("single_native_substitutions",)
