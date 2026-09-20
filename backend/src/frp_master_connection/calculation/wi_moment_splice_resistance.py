"""Stage 4.1A rational flange decomposition, body, and unequal-plane bolt checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, localcontext
from enum import Enum, StrEnum

from frp_master_connection.calculation.equations import (
    BoltResistanceTrace,
    EndUsePropertyTrace,
    bolt_shear_resistance_from_nominal_stress,
)
from frp_master_connection.calculation.inputs import (
    EndUseFactors,
    TimeEffectCategory,
    select_time_effect_factor,
)
from frp_master_connection.calculation.multirow_equations import adjusted_property_trace
from frp_master_connection.calculation.plate_strength import (
    PlateCompressionStrengthResult,
    PlateTensionStrengthResult,
    plate_longitudinal_compression_strength,
    plate_longitudinal_tension_strength,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
)

WI_MOMENT_SPLICE_BRANCH_METHOD = "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1"
WI_MOMENT_SPLICE_SUBLAYER_METHOD = "RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1"
WI_MOMENT_SPLICE_BOLT_METHOD = "RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1"
WI_MOMENT_SPLICE_PANEL_METHOD = "RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1"
WI_MOMENT_SPLICE_QUALIFICATION = "REQUIRED_2_3_2"
WI_MOMENT_SPLICE_DISCLAIMER_ID = "WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1"
WI_MOMENT_SPLICE_DISCLAIMER = (
    "The W/I major-axis moment splice uses the project-controlled Calculation Slice 5 "
    "region-resultant decomposition, rational balanced flange-face force-line and face-"
    "sublayer transfer methods, the Stage 3.6/Calculation Slice 4 rational plate-body "
    "methods, and an unequal two-plane common-bolt shear method. These connection-detail "
    "methods are not prescribed directly by ASCE/SEI 74-23. The engineer of record shall "
    "review the section and contact idealizations, actual stiffness compatibility, "
    "out-of-plane deformation, prying and secondary bolt bending, experimental "
    "qualification under Section 2.3.2, and all source-pending fastener properties. "
    "Connection stiffness, rotation capacity, and full-strength classification are not "
    "evaluated."
)

_ONE = Decimal(1)
_HALF = Decimal("0.5")


class FlangeBodyStatus(StrEnum):
    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    NOT_REQUIRED_ZERO_FORCE = "NOT_REQUIRED_ZERO_FORCE"


class AsymmetricBoltStatus(StrEnum):
    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True, slots=True)
class FlangeBranchDecomposition:
    flange_id: str
    flange_reference_v: PhysicalQuantity
    outer_reference_v: PhysicalQuantity
    inner_reference_v: PhysicalQuantity
    flange_force: PhysicalQuantity
    flange_local_moment: PhysicalQuantity
    outer_force: PhysicalQuantity
    inner_total_force: PhysicalQuantity
    inner_negative_force: PhysicalQuantity
    inner_positive_force: PhysicalQuantity
    force_residual: PhysicalQuantity
    local_moment_residual: PhysicalQuantity
    global_moment: PhysicalQuantity
    exact_force_equilibrium: bool
    exact_local_moment_equilibrium: bool
    exact_inner_symmetry: bool
    method: str
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class FlangePlaneDemand:
    force_l: PhysicalQuantity
    force_t: PhysicalQuantity
    source_demand_fingerprint: str
    group_id: str
    bolt_id: str

    @property
    def magnitude(self) -> PhysicalQuantity:
        unit = self.force_l.unit
        with localcontext() as context:
            context.prec = 100
            return PhysicalQuantity.of(
                (
                    self.force_l.to(unit).magnitude ** 2 + self.force_t.to(unit).magnitude ** 2
                ).sqrt(),
                unit,
            )


@dataclass(frozen=True, slots=True)
class AsymmetricTwoPlaneBoltResult:
    bolt_id: str
    physical_path: tuple[str, str, str]
    physical_shear_plane_count: int
    outer_plane: FlangePlaneDemand
    inner_plane: FlangePlaneDemand
    planes_equal: bool
    source_authority_id: str
    source_authorized: bool
    thread_condition: str
    per_plane_design_capacity: PhysicalQuantity | None
    outer_utilization: Decimal | None
    inner_utilization: Decimal | None
    governing_utilization: Decimal | None
    status: AsymmetricBoltStatus
    source_required_reason: str | None
    resistance_trace: BoltResistanceTrace | None
    bolt_axis_tension: PhysicalQuantity
    pull_through_status: str
    prying_status: str
    method: str
    result_fingerprint: str


@dataclass(frozen=True, slots=True)
class FlangePlateBodyResult:
    component_id: str
    signed_force: PhysicalQuantity
    width: PhysicalQuantity
    thickness: PhysicalQuantity
    clear_body_length: PhysicalQuantity
    mode: str
    design_capacity: PhysicalQuantity | None
    utilization: Decimal | None
    status: FlangeBodyStatus
    tension_strength: PlateTensionStrengthResult | None
    compression_strength: PlateCompressionStrengthResult | None
    slice4_advisories: tuple[str, ...]
    panel_method: str
    result_fingerprint: str


def _canonical(value: object) -> object:
    if isinstance(value, PhysicalQuantity):
        return {"dimension": value.dimension.value, "canonical": value.canonical_string}
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {name: _canonical(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def decompose_flange_wrench(
    *,
    flange_id: str,
    flange_reference_v: PhysicalQuantity,
    outer_reference_v: PhysicalQuantity,
    inner_reference_v: PhysicalQuantity,
    flange_force: PhysicalQuantity,
    flange_local_moment: PhysicalQuantity,
) -> FlangeBranchDecomposition:
    """Solve the two force lines exactly; no stiffness share is introduced."""

    if flange_force.dimension is not Dimension.FORCE:
        raise ValueError("flange_force must be a force.")
    if flange_local_moment.dimension is not Dimension.MOMENT:
        raise ValueError("flange_local_moment must be a moment.")
    unit = flange_reference_v.unit
    force_unit = flange_force.unit
    moment_unit = flange_local_moment.unit
    e_outer = outer_reference_v.to(unit).magnitude - flange_reference_v.to(unit).magnitude
    e_inner = inner_reference_v.to(unit).magnitude - flange_reference_v.to(unit).magnitude
    if e_outer * e_inner >= 0 or e_outer == e_inner:
        raise ValueError("BALANCED_OUTER_AND_INNER_FORCE_LINES_REQUIRED")
    scale = (
        PhysicalQuantity.of(1, force_unit).canonical_magnitude
        * PhysicalQuantity.of(1, unit).canonical_magnitude
        / PhysicalQuantity.of(1, moment_unit).canonical_magnitude
    )
    with localcontext() as context:
        context.prec = 100
        moment_as_force_length = flange_local_moment.magnitude / scale
        force = flange_force.magnitude
        outer = (moment_as_force_length - e_inner * force) / (e_outer - e_inner)
        inner = (e_outer * force - moment_as_force_length) / (e_outer - e_inner)
        outer_q = PhysicalQuantity.of(outer, force_unit)
        inner_q = PhysicalQuantity.of(inner, force_unit)
        each_inner = PhysicalQuantity.of(inner / 2, force_unit)
        force_residual = PhysicalQuantity.of(outer + inner - force, force_unit)
        recovered_local = (e_outer * outer + e_inner * inner) * scale
        moment_residual = PhysicalQuantity.of(
            recovered_local - flange_local_moment.magnitude,
            moment_unit,
        )
        global_moment = PhysicalQuantity.of(
            (
                outer_reference_v.to(unit).magnitude * outer
                + inner_reference_v.to(unit).magnitude * inner
            )
            * scale,
            moment_unit,
        )
    partial = FlangeBranchDecomposition(
        flange_id,
        flange_reference_v,
        outer_reference_v,
        inner_reference_v,
        flange_force,
        flange_local_moment,
        outer_q,
        inner_q,
        each_inner,
        each_inner,
        force_residual,
        moment_residual,
        global_moment,
        force_residual.canonical_magnitude == 0,
        moment_residual.canonical_magnitude == 0,
        True,
        WI_MOMENT_SPLICE_BRANCH_METHOD,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def evaluate_asymmetric_two_plane_bolt(
    *,
    bolt_id: str,
    physical_path: tuple[str, str, str],
    outer_plane: FlangePlaneDemand,
    inner_plane: FlangePlaneDemand,
    diameter: PhysicalQuantity,
    thread_condition: str,
    source_authority_id: str,
    nominal_shear_stress: PhysicalQuantity | None,
) -> AsymmetricTwoPlaneBoltResult:
    """Check each physical shear plane independently using its actual Stage 2.5A demand."""

    if len(physical_path) != 3 or "FLANGE" not in physical_path[1]:
        raise ValueError("A flange common bolt requires an outer/flange/inner path.")
    source_authorized = nominal_shear_stress is not None
    trace = (
        bolt_shear_resistance_from_nominal_stress(diameter, nominal_shear_stress)
        if nominal_shear_stress is not None
        else None
    )
    capacity = None if trace is None else trace.design_resistance
    with localcontext() as context:
        context.prec = 100
        outer_u = (
            None
            if capacity is None
            else outer_plane.magnitude.canonical_magnitude / capacity.canonical_magnitude
        )
        inner_u = (
            None
            if capacity is None
            else inner_plane.magnitude.canonical_magnitude / capacity.canonical_magnitude
        )
        governing = None if outer_u is None or inner_u is None else max(outer_u, inner_u)
    status = (
        AsymmetricBoltStatus.NOT_EVALUATED
        if governing is None
        else AsymmetricBoltStatus.PASS
        if governing <= 1
        else AsymmetricBoltStatus.FAIL
    )
    zero_axis = PhysicalQuantity.of(0, outer_plane.force_l.unit)
    partial = AsymmetricTwoPlaneBoltResult(
        bolt_id,
        physical_path,
        2,
        outer_plane,
        inner_plane,
        outer_plane.force_l.canonical_magnitude == inner_plane.force_l.canonical_magnitude
        and outer_plane.force_t.canonical_magnitude == inner_plane.force_t.canonical_magnitude,
        source_authority_id,
        source_authorized,
        thread_condition,
        capacity,
        outer_u,
        inner_u,
        governing,
        status,
        None if source_authorized else "SOURCE_AUTHORIZED_FNV_REQUIRED",
        trace,
        zero_axis,
        "NOT_REQUIRED",
        "ENGINEERING_REVIEW_REQUIRED_NOT_NUMERICALLY_INVENTED",
        WI_MOMENT_SPLICE_BOLT_METHOD,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def _ice_property(kind: FRPPropertyKind, factors: EndUseFactors) -> EndUsePropertyTrace:
    entry = create_locked_ice_material_snapshot().lookup(kind)
    if entry is None:  # pragma: no cover - controlled ICE snapshot invariant
        raise ValueError(f"Controlled ICE material lacks {kind.value}.")
    return adjusted_property_trace(entry, factors)


def evaluate_flange_plate_body(
    *,
    component_id: str,
    signed_force: PhysicalQuantity,
    width: PhysicalQuantity,
    thickness: PhysicalQuantity,
    clear_body_length: PhysicalQuantity,
) -> FlangePlateBodyResult:
    """Use Calculation Slice 4 for one longitudinal clear-body branch."""

    factors = EndUseFactors(
        _ONE,
        _ONE,
        _ONE,
        "ASCE/SEI 74-23 Section 2.4.4",
        ("STAGE_4_1A_CONTROLLED_UNITY_END_USE_FACTORS",),
    )
    time_effect = select_time_effect_factor(TimeEffectCategory.WIND_TORNADO_SEISMIC)
    if signed_force.canonical_magnitude == 0:
        partial = FlangePlateBodyResult(
            component_id,
            signed_force,
            width,
            thickness,
            clear_body_length,
            "ZERO_FORCE",
            None,
            None,
            FlangeBodyStatus.NOT_REQUIRED_ZERO_FORCE,
            None,
            None,
            (),
            WI_MOMENT_SPLICE_PANEL_METHOD,
            "",
        )
        return replace(partial, result_fingerprint=_fingerprint(partial))
    tension = None
    compression = None
    if signed_force.canonical_magnitude > 0:
        tension = plate_longitudinal_tension_strength(
            thickness,
            _ice_property(FRPPropertyKind.FT_L, factors),
            time_effect,
        )
        capacity = PhysicalQuantity.of(
            tension.design_strength.to(Unit.KIP_PER_IN).magnitude * width.to(Unit.IN).magnitude,
            Unit.KIP,
        )
        mode = "TENSION"
        advisories: tuple[str, ...] = ()
    else:
        compression = plate_longitudinal_compression_strength(
            thickness,
            width,
            _ice_property(FRPPropertyKind.FC_L, factors),
            _ice_property(FRPPropertyKind.ET_L, factors),
            _ice_property(FRPPropertyKind.ET_T, factors),
            _ice_property(FRPPropertyKind.G_LT, factors),
            _ice_property(FRPPropertyKind.NU_LT, factors),
            time_effect,
            longitudinal_span=clear_body_length,
        )
        capacity = PhysicalQuantity.of(
            compression.design_strength.to(Unit.KIP_PER_IN).magnitude * width.to(Unit.IN).magnitude,
            Unit.KIP,
        )
        mode = "COMPRESSION"
        advisories = tuple(item.value for item in compression.advisories)
    utilization = abs(signed_force.canonical_magnitude) / capacity.canonical_magnitude
    status = FlangeBodyStatus.PASS if utilization <= 1 else FlangeBodyStatus.FAIL
    partial = FlangePlateBodyResult(
        component_id,
        signed_force,
        width,
        thickness,
        clear_body_length,
        mode,
        capacity,
        utilization,
        status,
        tension,
        compression,
        advisories,
        WI_MOMENT_SPLICE_PANEL_METHOD,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


__all__ = (
    "WI_MOMENT_SPLICE_BOLT_METHOD",
    "WI_MOMENT_SPLICE_BRANCH_METHOD",
    "WI_MOMENT_SPLICE_DISCLAIMER",
    "WI_MOMENT_SPLICE_DISCLAIMER_ID",
    "WI_MOMENT_SPLICE_PANEL_METHOD",
    "WI_MOMENT_SPLICE_QUALIFICATION",
    "WI_MOMENT_SPLICE_SUBLAYER_METHOD",
    "AsymmetricBoltStatus",
    "AsymmetricTwoPlaneBoltResult",
    "FlangeBodyStatus",
    "FlangeBranchDecomposition",
    "FlangePlaneDemand",
    "FlangePlateBodyResult",
    "decompose_flange_wrench",
    "evaluate_asymmetric_two_plane_bolt",
    "evaluate_flange_plate_body",
)
