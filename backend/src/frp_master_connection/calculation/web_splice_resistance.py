"""Stage 3.6B RC2 rational web-splice body and physical double-shear checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import cast

from frp_master_connection.calculation.equations import (
    BoltResistanceTrace,
    bolt_shear_resistance_from_nominal_stress,
)
from frp_master_connection.calculation.plate_strength import (
    PlateCompressionStrengthResult,
    PlateShearStrengthResult,
    PlateTensionStrengthResult,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_value,
)

WEB_SPLICE_RATIONAL_METHOD = "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1"
WEB_SPLICE_RATIONAL_PANEL_MODEL = "RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1"
WEB_SPLICE_RATIONAL_DISCLAIMER_ID = "WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1"
WEB_SPLICE_RATIONAL_DISCLAIMER = (
    "The FRP web-splice plate inter-group body under combined longitudinal normal force "
    "and in-plane shear is evaluated using a project-specific conservative linear "
    "interaction of separately derived ASCE/SEI 74-23 Chapter 7 pure-mode plate design "
    "resistances. The interaction equation and the selected clear-body panel boundary "
    "idealization are rational engineering methods and are not prescribed directly by "
    "ASCE/SEI 74-23. The engineer of record shall review the assumptions, actual "
    "restraint/buckling boundary conditions, Calculation Slice 4 advisories, and Section "
    "2.3.2 connection-element qualification requirements."
)
WEB_SPLICE_QUALIFICATION = "REQUIRED_2_3_2"
WEB_SPLICE_SLICE4_COMMIT = "a93aa5d127a51dc81a6c7cd108af15c44d59ff9f"
WEB_SPLICE_SLICE4_GOLDEN_SHA256 = "E6F00A1421751386980321A5AA046A13C706D9D32E42AAC6242F0D89525AC4CD"
_HALF = Decimal("0.5")
_ONE = Decimal(1)


class RationalBodyStatus(StrEnum):
    PASS_RATIONAL_METHOD = "PASS_RATIONAL_METHOD"  # noqa: S105 - engineering status
    FAIL_RATIONAL_METHOD = "FAIL_RATIONAL_METHOD"
    NOT_EVALUATED = "NOT_EVALUATED"


class RationalNormalMode(StrEnum):
    TENSION = "TENSION"
    COMPRESSION = "COMPRESSION"


class DoubleShearStatus(StrEnum):
    PASS = "PASS"  # noqa: S105 - engineering status, not a credential
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True, slots=True)
class WebSpliceCriticalSectionAction:
    section_id: str
    coordinate: PhysicalQuantity
    pair_axial_force: PhysicalQuantity
    pair_shear_force: PhysicalQuantity
    pair_moment: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class WebSpliceBodySectionResult:
    section_id: str
    fiber_id: str
    coordinate: PhysicalQuantity
    plate_axial_force: PhysicalQuantity
    plate_shear_force: PhysicalQuantity
    plate_moment: PhysicalQuantity
    signed_normal_stress: PhysicalQuantity
    signed_shear_stress: PhysicalQuantity
    normal_mode: RationalNormalMode
    normal_design_stress: PhysicalQuantity
    shear_design_stress: PhysicalQuantity
    normal_utilization: Decimal
    shear_utilization: Decimal
    rational_utilization: Decimal


@dataclass(frozen=True, slots=True)
class WebSpliceBodyInteractionResult:
    method: str
    panel_model: str
    status: RationalBodyStatus
    symmetry_proven: bool
    plate_fraction: Decimal | None
    plate_area_in2: Decimal | None
    plate_inertia_in4: Decimal | None
    extreme_fiber_in: Decimal | None
    critical_sections: tuple[WebSpliceBodySectionResult, ...]
    governing_section_id: str | None
    governing_fiber_id: str | None
    governing_signed_normal_stress: PhysicalQuantity | None
    governing_signed_shear_stress: PhysicalQuantity | None
    governing_normal_mode: RationalNormalMode | None
    tension_design_stress: PhysicalQuantity | None
    compression_design_stress: PhysicalQuantity | None
    shear_design_stress: PhysicalQuantity | None
    normal_utilization: Decimal | None
    shear_utilization: Decimal | None
    rational_utilization: Decimal | None
    tension_strength: PlateTensionStrengthResult | None
    compression_strength: PlateCompressionStrengthResult | None
    shear_strength: PlateShearStrengthResult | None
    slice4_result_fingerprints: tuple[str, ...]
    slice4_advisories: tuple[str, ...]
    engineering_review_required: bool
    qualification: str
    disclaimer_id: str
    disclaimer_text: str
    future_report_final_disclaimer_section: bool
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class WebSpliceDoubleShearResult:
    group_id: str
    bolt_id: str
    physical_path: tuple[str, ...]
    physical_shear_plane_count: int
    thread_condition: str
    source_authority_id: str
    source_authorized: bool
    physical_in_plane_demand: PhysicalQuantity
    per_plane_demand: PhysicalQuantity
    per_plane_design_capacity: PhysicalQuantity | None
    two_plane_design_capacity: PhysicalQuantity | None
    utilization: Decimal | None
    status: DoubleShearStatus
    source_required_reason: str | None
    resistance_trace: BoltResistanceTrace | None
    result_fingerprint: str


def _payload(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {name: _payload(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, tuple):
        return [_payload(item) for item in value]
    if isinstance(value, list):
        return [_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _payload(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_payload(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _stress_from_force_area(force: PhysicalQuantity, area_in2: Decimal) -> PhysicalQuantity:
    return PhysicalQuantity.of(force.to(Unit.KIP).magnitude / area_in2, Unit.KSI)


def _stress_from_moment(
    moment: PhysicalQuantity, extreme_fiber_in: Decimal, inertia_in4: Decimal
) -> PhysicalQuantity:
    return PhysicalQuantity.of(
        moment.to(Unit.KIP_IN).magnitude * extreme_fiber_in / inertia_in4,
        Unit.KSI,
    )


def _design_stress(strength: PhysicalQuantity, thickness: PhysicalQuantity) -> PhysicalQuantity:
    if strength.dimension is not Dimension.FORCE_PER_LENGTH:
        raise ValueError("Slice 4 design strength must be force per unit width.")
    with localcontext() as context:
        context.prec = 100
        return PhysicalQuantity.of(
            strength.to(Unit.KIP_PER_IN).magnitude / thickness.to(Unit.IN).magnitude,
            Unit.KSI,
        )


def evaluate_rational_body_interaction(
    *,
    plate_height: PhysicalQuantity,
    plate_thickness: PhysicalQuantity,
    actions: tuple[WebSpliceCriticalSectionAction, ...],
    symmetry_proven: bool,
    tension_design_stress: PhysicalQuantity | None = None,
    compression_design_stress: PhysicalQuantity | None = None,
    shear_design_stress: PhysicalQuantity | None = None,
    tension_strength: PlateTensionStrengthResult | None = None,
    compression_strength: PlateCompressionStrengthResult | None = None,
    shear_strength: PlateShearStrengthResult | None = None,
) -> WebSpliceBodyInteractionResult:
    """Evaluate only the controlled rational interaction; Chapter 7 remains in Slice 4."""

    h = plate_height.to(Unit.IN).magnitude
    t = plate_thickness.to(Unit.IN).magnitude
    if h <= 0 or t <= 0:
        raise ValueError("Plate height and thickness must be positive.")
    if tension_strength is not None:
        tension_design_stress = _design_stress(tension_strength.design_strength, plate_thickness)
    if compression_strength is not None:
        compression_design_stress = _design_stress(
            compression_strength.design_strength, plate_thickness
        )
    if shear_strength is not None:
        shear_design_stress = _design_stress(shear_strength.design_strength, plate_thickness)
    available = all(
        item is not None and item.dimension is Dimension.STRESS and item.canonical_magnitude > 0
        for item in (
            tension_design_stress,
            compression_design_stress,
            shear_design_stress,
        )
    )
    if not symmetry_proven or not available:
        result = WebSpliceBodyInteractionResult(
            WEB_SPLICE_RATIONAL_METHOD,
            WEB_SPLICE_RATIONAL_PANEL_MODEL,
            RationalBodyStatus.NOT_EVALUATED,
            symmetry_proven,
            None,
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            None,
            None,
            tension_design_stress,
            compression_design_stress,
            shear_design_stress,
            None,
            None,
            None,
            tension_strength,
            compression_strength,
            shear_strength,
            tuple(
                item.result_fingerprint
                for item in (tension_strength, compression_strength, shear_strength)
                if item is not None
            ),
            (),
            False,
            WEB_SPLICE_QUALIFICATION,
            WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
            WEB_SPLICE_RATIONAL_DISCLAIMER,
            True,
            "",
        )
        return replace(result, result_fingerprint=_fingerprint(result))

    tension_design_stress = cast(PhysicalQuantity, tension_design_stress)
    compression_design_stress = cast(PhysicalQuantity, compression_design_stress)
    shear_design_stress = cast(PhysicalQuantity, shear_design_stress)
    with localcontext() as context:
        context.prec = 100
        area = h * t
        inertia = t * h**3 / Decimal(12)
        extreme = h / 2
        section_results: list[WebSpliceBodySectionResult] = []
        for action in actions:
            plate_axial = action.pair_axial_force / 2
            plate_shear = action.pair_shear_force / 2
            plate_moment = action.pair_moment / 2
            membrane = _stress_from_force_area(plate_axial, area)
            bending = _stress_from_moment(plate_moment, extreme, inertia)
            tau = _stress_from_force_area(plate_shear, area)
            for fiber_id, signed in (
                ("FIBER_POSITIVE_V", membrane + bending),
                ("FIBER_NEGATIVE_V", membrane - bending),
            ):
                mode = (
                    RationalNormalMode.TENSION
                    if signed.magnitude >= 0
                    else RationalNormalMode.COMPRESSION
                )
                normal_design = (
                    tension_design_stress
                    if mode is RationalNormalMode.TENSION
                    else compression_design_stress
                )
                normal_u = abs(signed.to(Unit.KSI).magnitude) / normal_design.to(Unit.KSI).magnitude
                shear_u = (
                    abs(tau.to(Unit.KSI).magnitude) / shear_design_stress.to(Unit.KSI).magnitude
                )
                section_results.append(
                    WebSpliceBodySectionResult(
                        action.section_id,
                        fiber_id,
                        action.coordinate,
                        plate_axial,
                        plate_shear,
                        plate_moment,
                        signed,
                        tau,
                        mode,
                        normal_design,
                        shear_design_stress,
                        normal_u,
                        shear_u,
                        normal_u + shear_u,
                    )
                )
    governing = max(section_results, key=lambda item: item.rational_utilization)
    status = (
        RationalBodyStatus.PASS_RATIONAL_METHOD
        if governing.rational_utilization <= 1
        else RationalBodyStatus.FAIL_RATIONAL_METHOD
    )
    advisories = tuple(
        dict.fromkeys(
            item.value
            for strength in (compression_strength, shear_strength)
            if strength is not None
            for item in strength.advisories
        )
    )
    fingerprints = tuple(
        item.result_fingerprint
        for item in (tension_strength, compression_strength, shear_strength)
        if item is not None
    )
    result = WebSpliceBodyInteractionResult(
        WEB_SPLICE_RATIONAL_METHOD,
        WEB_SPLICE_RATIONAL_PANEL_MODEL,
        status,
        True,
        _HALF,
        area,
        inertia,
        extreme,
        tuple(section_results),
        governing.section_id,
        governing.fiber_id,
        governing.signed_normal_stress,
        governing.signed_shear_stress,
        governing.normal_mode,
        tension_design_stress,
        compression_design_stress,
        shear_design_stress,
        governing.normal_utilization,
        governing.shear_utilization,
        governing.rational_utilization,
        tension_strength,
        compression_strength,
        shear_strength,
        fingerprints,
        advisories,
        True,
        WEB_SPLICE_QUALIFICATION,
        WEB_SPLICE_RATIONAL_DISCLAIMER_ID,
        WEB_SPLICE_RATIONAL_DISCLAIMER,
        True,
        "",
    )
    return replace(result, result_fingerprint=_fingerprint(result))


def evaluate_double_shear_bolt(
    *,
    group_id: str,
    bolt_id: str,
    physical_path: tuple[str, ...],
    physical_in_plane_demand: PhysicalQuantity,
    symmetry_proven: bool,
    plate_fraction: Decimal,
    diameter: PhysicalQuantity,
    thread_condition: str,
    source_authority_id: str,
    nominal_shear_stress: PhysicalQuantity | None,
) -> WebSpliceDoubleShearResult:
    """Evaluate a physical two-plane bolt only when explicit shear authority is present."""

    if physical_in_plane_demand.dimension is not Dimension.FORCE:
        raise ValueError("Physical bolt demand must be a force.")
    if diameter.dimension is not Dimension.LENGTH or diameter.canonical_magnitude <= 0:
        raise ValueError("Bolt diameter must be a positive length.")
    complete = (
        len(physical_path) == 3
        and "SPLICE_PLATE" in physical_path[0]
        and "WEB" in physical_path[1]
        and "SPLICE_PLATE" in physical_path[2]
    )
    plane_count = len(physical_path) - 1 if complete else 0
    applicable = (
        complete
        and plane_count == 2
        and symmetry_proven
        and decimal_value(plate_fraction) == _HALF
        and thread_condition in {"INCLUDED", "EXCLUDED"}
    )
    source_authorized = (
        nominal_shear_stress is not None
        and nominal_shear_stress.dimension is Dimension.STRESS
        and nominal_shear_stress.canonical_magnitude > 0
    )
    per_plane_demand = physical_in_plane_demand / 2
    trace = (
        bolt_shear_resistance_from_nominal_stress(diameter, nominal_shear_stress)
        if applicable and source_authorized and nominal_shear_stress is not None
        else None
    )
    per_plane_capacity = None if trace is None else trace.design_resistance
    with localcontext() as context:
        context.prec = 100
        total_capacity = (
            None
            if trace is None
            else PhysicalQuantity.of(
                trace.design_resistance.magnitude * 2,
                trace.design_resistance.unit,
            )
        )
        utilization = (
            None
            if total_capacity is None
            else physical_in_plane_demand.canonical_magnitude / total_capacity.canonical_magnitude
        )
    status = (
        DoubleShearStatus.NOT_EVALUATED
        if utilization is None
        else DoubleShearStatus.PASS
        if utilization <= 1
        else DoubleShearStatus.FAIL
    )
    reason = (
        None
        if utilization is not None
        else "SOURCE_AUTHORIZED_FNV_REQUIRED"
        if applicable and not source_authorized
        else "PHYSICAL_DOUBLE_SHEAR_PREREQUISITE_NOT_SATISFIED"
    )
    partial = WebSpliceDoubleShearResult(
        group_id,
        bolt_id,
        physical_path,
        plane_count,
        thread_condition,
        source_authority_id,
        source_authorized,
        physical_in_plane_demand,
        per_plane_demand,
        per_plane_capacity,
        total_capacity,
        utilization,
        status,
        reason,
        trace,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


__all__ = (
    "WEB_SPLICE_QUALIFICATION",
    "WEB_SPLICE_RATIONAL_DISCLAIMER",
    "WEB_SPLICE_RATIONAL_DISCLAIMER_ID",
    "WEB_SPLICE_RATIONAL_METHOD",
    "WEB_SPLICE_RATIONAL_PANEL_MODEL",
    "WEB_SPLICE_SLICE4_COMMIT",
    "WEB_SPLICE_SLICE4_GOLDEN_SHA256",
    "DoubleShearStatus",
    "RationalBodyStatus",
    "RationalNormalMode",
    "WebSpliceBodyInteractionResult",
    "WebSpliceBodySectionResult",
    "WebSpliceCriticalSectionAction",
    "WebSpliceDoubleShearResult",
    "evaluate_double_shear_bolt",
    "evaluate_rational_body_interaction",
)
