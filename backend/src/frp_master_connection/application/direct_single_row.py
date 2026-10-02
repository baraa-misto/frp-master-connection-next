"""Source-bounded Direct one-row FRP limits outside the frozen multi-row engines."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal, localcontext
from enum import Enum

from frp_master_connection.calculation import (
    EccentricDemandResult,
    EndUsePropertyTrace,
    FirstRowGeometryMapping,
    FirstRowNetTensionPlan,
    FRPPropertyKind,
    MaterialDirection,
    MultiRowFactorContext,
    MultiRowLayerExecutionContext,
    MultiRowResultAvailability,
    NumericalComparison,
    PhysicalQuantity,
    PultrudedElementClassification,
    Unit,
)
from frp_master_connection.calculation.equations import (
    adjust_frp_property,
    assemble_frp_design_resistance,
    cleavage_resistance,
    net_tension_resistance,
    pin_bearing_resistance,
    shear_out_resistance,
)
from frp_master_connection.calculation.inputs import PultrudedElementForm
from frp_master_connection.calculation.multirow_equations import compare_resistance
from frp_master_connection.geometry import MultiRowGeometry


@dataclass(frozen=True, slots=True)
class DirectSingleRowCheck:
    result_id: str
    limit_state: str
    equation_method: str
    source_locator: str
    layer_id: str
    bolt_id: str | None
    bolt_line_id: str | None
    demand: PhysicalQuantity | None
    design_resistance: PhysicalQuantity | None
    utilization: Decimal | None
    numerical_comparison: NumericalComparison
    availability: MultiRowResultAvailability
    qualification: str
    required: bool
    reason: str
    equation_trace: object | None


@dataclass(frozen=True, slots=True)
class DirectSingleRowResult:
    contract_version: str
    source_scenario_id: str
    checks: tuple[DirectSingleRowCheck, ...]
    required_check_ids: tuple[str, ...]
    incomplete_required_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    numerical_comparison: NumericalComparison
    overall_disposition: str
    result_fingerprint: str


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"value": str(value.canonical_magnitude), "unit": value.canonical_unit.value}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _canonical(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, tuple | list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _blocked(
    identity: str,
    family: str,
    method: str,
    layer_id: str,
    demand: PhysicalQuantity | None,
    reason: str,
    *,
    bolt_id: str | None = None,
    line_id: str | None = None,
    required: bool = True,
) -> DirectSingleRowCheck:
    return DirectSingleRowCheck(
        identity,
        family,
        method,
        "ASCE/SEI 74-23 Section 8.3.2",
        layer_id,
        bolt_id,
        line_id,
        demand,
        None,
        None,
        NumericalComparison.NOT_EVALUATED,
        MultiRowResultAvailability.CALCULATION_NOT_SUPPORTED
        if required
        else MultiRowResultAvailability.NOT_APPLICABLE,
        "ENGINEERING_REVIEW_REQUIRED",
        required,
        reason,
        None,
    )


def _evaluated(
    identity: str,
    family: str,
    method: str,
    layer_id: str,
    demand: PhysicalQuantity,
    resistance: PhysicalQuantity,
    trace: object,
    *,
    bolt_id: str | None = None,
    line_id: str | None = None,
) -> DirectSingleRowCheck:
    comparison = compare_resistance(demand, resistance)
    return DirectSingleRowCheck(
        identity,
        family,
        method,
        "ASCE/SEI 74-23 Section 8.3.2",
        layer_id,
        bolt_id,
        line_id,
        demand,
        resistance,
        comparison.utilization,
        comparison.numerical_comparison,
        MultiRowResultAvailability.CALCULATED,
        "ENGINEERING_REVIEW_REQUIRED",
        True,
        "Numerical check executed; material and whole-connection qualification remain separate",
        trace,
    )


def _property(
    layer: MultiRowLayerExecutionContext, kind: FRPPropertyKind
) -> EndUsePropertyTrace | None:
    entry = layer.material.lookup(kind)
    if entry is None or not entry.use_in_chapter_8_equations:
        return None
    return adjust_frp_property(kind, entry.value, entry.qualification_status, layer.end_use_factors)


def evaluate_direct_single_row(
    geometry: MultiRowGeometry,
    layer_plans: tuple[tuple[FirstRowNetTensionPlan, ...], ...],
    layers: tuple[MultiRowLayerExecutionContext, ...],
    factors: MultiRowFactorContext,
    demand: EccentricDemandResult,
    bolt_diameter: PhysicalQuantity,
    hole_diameter: PhysicalQuantity,
    total: PhysicalQuantity,
    inherited_required: tuple[str, ...],
    inherited_incomplete: tuple[str, ...],
    inherited_failed: tuple[str, ...],
    inherited_fingerprint: str,
) -> DirectSingleRowResult:
    """Evaluate one row's local paths using the accepted demand scenario.

    A nonzero residual moment blocks section/line demands. Per-bolt bearing and
    bolt checks remain in the inherited handoff; this adapter never replaces them.
    """

    if len(geometry.rows) != 1 or len(layers) != 2:
        raise ValueError("Direct single-row adapter requires one row and two FRP layers.")
    if len(demand.scenarios) != 1:
        raise ValueError("Direct single-row adapter requires one accepted demand scenario.")
    scenario = demand.scenarios[0]
    residual = scenario.residual_moment.canonical_magnitude != 0
    per_bolt = {item.bolt_id: item for item in scenario.per_bolt}
    count = len(geometry.group.bolts)
    if count not in {1, 2, 3}:
        raise ValueError("Direct single-row adapter supports one through three bolts.")
    checks: list[DirectSingleRowCheck] = []
    for layer, plans in zip(layers, layer_plans, strict=True):
        first = plans[0]
        mapping = first.geometry
        if not isinstance(mapping, FirstRowGeometryMapping):
            raise TypeError("Direct single-row geometry must use accepted first-row mapping.")
        tension_kind = (
            FRPPropertyKind.FT_L
            if layer.material_direction is MaterialDirection.LONGITUDINAL
            else FRPPropertyKind.FT_T
        )
        tension = _property(layer, tension_kind)
        shear = _property(layer, FRPPropertyKind.FSH_LT)
        common = {
            "c_delta": factors.pitch_factor_c_delta,
            "c_lap": factors.lap_factor_c_lap,
            "lambda_factor": factors.time_effect_factor_lambda,
        }
        net_id = f"SINGLE_ROW_NET_TENSION:{layer.layer_id}"
        if residual:
            checks.append(
                _blocked(
                    net_id,
                    "SINGLE_ROW_NET_TENSION",
                    "ASCE_EQ_8_7",
                    layer.layer_id,
                    None,
                    "Required first-row section demand under residual moment is not authorized",
                )
            )
        elif mapping.effective_width is None or tension is None:
            checks.append(
                _blocked(
                    net_id,
                    "SINGLE_ROW_NET_TENSION",
                    "ASCE_EQ_8_7",
                    layer.layer_id,
                    total,
                    "Effective width or controlled tensile property unavailable",
                )
            )
        elif count > 1 and (mapping.gauge is None or mapping.gauge > bolt_diameter * Decimal(5)):
            checks.append(
                _blocked(
                    net_id,
                    "SINGLE_ROW_NET_TENSION",
                    "ASCE_EQ_8_7C",
                    layer.layer_id,
                    total,
                    "Single-row constant gauge exceeds the source limit of 5d",
                )
            )
        elif count == 1:
            trace = net_tension_resistance(
                mapping.effective_width,
                bolt_diameter,
                hole_diameter,
                layer.thickness,
                mapping.e1,
                tension,
                PultrudedElementForm.SHAPE_ELEMENT
                if layer.element_classification is PultrudedElementClassification.SHAPE
                else PultrudedElementForm.PLATE,
                layer.material_direction is MaterialDirection.LONGITUDINAL,
                **common,
            )
            checks.append(
                _evaluated(
                    net_id,
                    "SINGLE_ROW_NET_TENSION",
                    "ASCE_EQ_8_7A_8_7B",
                    layer.layer_id,
                    total,
                    trace.factor_trace.design_resistance,
                    {
                        "width": mapping.effective_width,
                        "bolt_diameter": bolt_diameter,
                        "hole_diameter": hole_diameter,
                        "thickness": layer.thickness,
                        "e1": mapping.e1,
                        "native": trace,
                    },
                )
            )
        else:
            width = mapping.effective_width.to(Unit.MM).magnitude
            hole = hole_diameter.to(Unit.MM).magnitude
            ci = (
                Decimal("0.40")
                if layer.element_classification is PultrudedElementClassification.PLATE
                and layer.material_direction is MaterialDirection.LONGITUDINAL
                else Decimal("0.50")
            )
            knt = Decimal("0.65") * ci
            with localcontext() as context:
                context.prec = 60
                nominal = (
                    (width - Decimal(count) * hole)
                    * layer.thickness.to(Unit.MM).magnitude
                    * tension.adjusted_property.to(Unit.MPA).magnitude
                    / knt
                )
            if nominal <= 0:
                checks.append(
                    _blocked(
                        net_id,
                        "SINGLE_ROW_NET_TENSION",
                        "ASCE_EQ_8_7C",
                        layer.layer_id,
                        total,
                        "Net section is nonpositive",
                    )
                )
            else:
                assembly = assemble_frp_design_resistance(
                    PhysicalQuantity.of(nominal, Unit.N),
                    (tension,),
                    phi=Decimal("0.45"),
                    **common,
                )
                checks.append(
                    _evaluated(
                        net_id,
                        "SINGLE_ROW_NET_TENSION",
                        "ASCE_EQ_8_7A_8_7C",
                        layer.layer_id,
                        total,
                        assembly.design_resistance,
                        {
                            "width": mapping.effective_width,
                            "bolt_count": count,
                            "hole_diameter": hole_diameter,
                            "thickness": layer.thickness,
                            "tensile_property": tension,
                            "knt": knt,
                            "factor_trace": assembly,
                        },
                    )
                )
        for line in geometry.bolt_lines:
            bolt_id = line.bolts[0].bolt.id
            line_demand = per_bolt[bolt_id].total_force_magnitude
            identity = f"SINGLE_ROW_SHEAR_OUT:{layer.layer_id}:{line.id}"
            if residual:
                checks.append(
                    _blocked(
                        identity,
                        "SINGLE_ROW_SHEAR_OUT",
                        "ASCE_EQ_8_8",
                        layer.layer_id,
                        line_demand,
                        "Bolt-line shear-out demand under residual moment is not authorized",
                        bolt_id=bolt_id,
                        line_id=line.id,
                    )
                )
            elif shear is None:
                checks.append(
                    _blocked(
                        identity,
                        "SINGLE_ROW_SHEAR_OUT",
                        "ASCE_EQ_8_8",
                        layer.layer_id,
                        line_demand,
                        "Controlled in-plane shear property unavailable",
                        bolt_id=bolt_id,
                        line_id=line.id,
                    )
                )
            else:
                shear_trace = shear_out_resistance(
                    mapping.e1, hole_diameter, layer.thickness, shear, **common
                )
                checks.append(
                    _evaluated(
                        identity,
                        "SINGLE_ROW_SHEAR_OUT",
                        "ASCE_EQ_8_8",
                        layer.layer_id,
                        line_demand,
                        shear_trace.factor_trace.design_resistance,
                        {
                            "e1": mapping.e1,
                            "hole_diameter": hole_diameter,
                            "thickness": layer.thickness,
                            "native": shear_trace,
                        },
                        bolt_id=bolt_id,
                        line_id=line.id,
                    )
                )
        cleavage_id = f"SINGLE_ROW_CLEAVAGE:{layer.layer_id}"
        if layer.material_direction is not MaterialDirection.LONGITUDINAL:
            checks.append(
                _blocked(
                    cleavage_id,
                    "SINGLE_ROW_CLEAVAGE",
                    "SOURCE_NOT_APPLICABLE",
                    layer.layer_id,
                    None,
                    "Cleavage is not applicable to the oblique/transverse material direction",
                    required=False,
                )
            )
        elif residual:
            checks.append(
                _blocked(
                    cleavage_id,
                    "SINGLE_ROW_CLEAVAGE",
                    "ASCE_EQ_8_9",
                    layer.layer_id,
                    None,
                    "Cleavage section demand under residual moment is not authorized",
                )
            )
        elif tension is None or shear is None:
            checks.append(
                _blocked(
                    cleavage_id,
                    "SINGLE_ROW_CLEAVAGE",
                    "ASCE_EQ_8_9",
                    layer.layer_id,
                    total,
                    "Controlled longitudinal tensile or shear property unavailable",
                )
            )
        elif count == 1:
            bearing = _property(layer, FRPPropertyKind.FBR_L)
            if bearing is None:
                checks.append(
                    _blocked(
                        cleavage_id,
                        "SINGLE_ROW_CLEAVAGE",
                        "ASCE_EQ_8_9A_8_9B",
                        layer.layer_id,
                        total,
                        "Controlled longitudinal bearing property unavailable",
                    )
                )
            else:
                bearing_trace = pin_bearing_resistance(
                    layer.thickness, bolt_diameter, bearing, layer.bearing_thread_status, **common
                )
                cleavage_trace = cleavage_resistance(
                    mapping.e1,
                    min(mapping.raw_e3, mapping.raw_e4),
                    bolt_diameter,
                    hole_diameter,
                    layer.thickness,
                    tension,
                    shear,
                    bearing_trace,
                    **common,
                )
                checks.append(
                    _evaluated(
                        cleavage_id,
                        "SINGLE_ROW_CLEAVAGE",
                        "ASCE_EQ_8_9A_8_9B",
                        layer.layer_id,
                        total,
                        cleavage_trace.selected_design_resistance,
                        {
                            "e1": mapping.e1,
                            "e2": min(mapping.raw_e3, mapping.raw_e4),
                            "bolt_diameter": bolt_diameter,
                            "hole_diameter": hole_diameter,
                            "thickness": layer.thickness,
                            "native": cleavage_trace,
                        },
                    )
                )
        elif mapping.gauge is None or mapping.raw_e3 != mapping.raw_e4:
            checks.append(
                _blocked(
                    cleavage_id,
                    "SINGLE_ROW_CLEAVAGE",
                    "ASCE_EQ_8_9C",
                    layer.layer_id,
                    total,
                    "Uniform gauge and symmetric side-distance authority are required",
                )
            )
        else:
            e1 = mapping.e1.to(Unit.MM).magnitude
            e2 = mapping.raw_e3.to(Unit.MM).magnitude
            gauge = mapping.gauge.to(Unit.MM).magnitude
            hole = hole_diameter.to(Unit.MM).magnitude
            ft = tension.adjusted_property.to(Unit.MPA).magnitude
            fsh = shear.adjusted_property.to(Unit.MPA).magnitude
            thickness = layer.thickness.to(Unit.MM).magnitude
            nominal = (
                Decimal("0.15")
                * ((e2 + Decimal("0.5") * gauge - hole) * ft + Decimal(2) * e1 * fsh)
                * thickness
            )
            if nominal <= 0:
                checks.append(
                    _blocked(
                        cleavage_id,
                        "SINGLE_ROW_CLEAVAGE",
                        "ASCE_EQ_8_9C",
                        layer.layer_id,
                        total,
                        "Cleavage nominal resistance is nonpositive",
                    )
                )
            else:
                assembly = assemble_frp_design_resistance(
                    PhysicalQuantity.of(nominal, Unit.N),
                    (tension, shear),
                    phi=Decimal("0.50"),
                    **common,
                )
                checks.append(
                    _evaluated(
                        cleavage_id,
                        "SINGLE_ROW_CLEAVAGE",
                        "ASCE_EQ_8_9C",
                        layer.layer_id,
                        total,
                        assembly.design_resistance,
                        {
                            "e1": mapping.e1,
                            "e2": mapping.raw_e3,
                            "gauge": mapping.gauge,
                            "hole_diameter": hole_diameter,
                            "thickness": layer.thickness,
                            "tensile_property": tension,
                            "shear_property": shear,
                            "factor_trace": assembly,
                        },
                    )
                )
    required_ids = (*inherited_required, *(item.result_id for item in checks if item.required))
    incomplete = (
        *inherited_incomplete,
        *(
            item.result_id
            for item in checks
            if item.required and item.availability is not MultiRowResultAvailability.CALCULATED
        ),
    )
    failed = (
        *inherited_failed,
        *(
            item.result_id
            for item in checks
            if item.required and item.numerical_comparison is NumericalComparison.FAIL
        ),
    )
    comparison = (
        NumericalComparison.FAIL
        if failed
        else NumericalComparison.NOT_EVALUATED
        if incomplete
        else NumericalComparison.PASS
    )
    overall = "FAIL" if failed else "NOT_EVALUATED" if incomplete else "ENGINEERING_REVIEW_REQUIRED"
    payload = {
        "contract_version": "SHEAR01-DIRECT-F1-R1-SINGLE-ROW",
        "scenario_id": scenario.scenario_id,
        "parent_group_mode_fingerprint": inherited_fingerprint,
        "checks": checks,
        "required": required_ids,
        "incomplete": incomplete,
        "failed": failed,
        "overall": overall,
    }
    fingerprint = hashlib.sha256(
        json.dumps(_canonical(payload), sort_keys=True).encode()
    ).hexdigest()
    return DirectSingleRowResult(
        "SHEAR01-DIRECT-F1-R1-SINGLE-ROW",
        scenario.scenario_id,
        tuple(checks),
        required_ids,
        incomplete,
        failed,
        comparison,
        overall,
        fingerprint,
    )
