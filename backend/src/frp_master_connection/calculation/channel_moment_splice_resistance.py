"""Stage 4.1B Channel web-face decomposition and inherited rational checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, localcontext
from enum import Enum

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    canonical_decimal_string,
)
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    WI_MOMENT_SPLICE_BOLT_METHOD,
    WI_MOMENT_SPLICE_BRANCH_METHOD,
    WI_MOMENT_SPLICE_PANEL_METHOD,
    WI_MOMENT_SPLICE_SUBLAYER_METHOD,
    AsymmetricBoltStatus,
    AsymmetricTwoPlaneBoltResult,
    FlangeBodyStatus,
    FlangeBranchDecomposition,
    FlangePlaneDemand,
    FlangePlateBodyResult,
    decompose_flange_wrench,
    evaluate_asymmetric_two_plane_bolt,
    evaluate_flange_plate_body,
)

CHANNEL_WEB_BRANCH_METHOD = "RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1"
CHANNEL_WEB_SUBLAYER_METHOD = "RATIONAL_CHANNEL_WEB_FACE_SUBLAYER_TRANSFER_RC1"
CHANNEL_MOMENT_SPLICE_QUALIFICATION = "REQUIRED_2_3_2"
CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID = (
    "CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1"
)
CHANNEL_MOMENT_SPLICE_DISCLAIMER = (
    "The Channel major-axis moment splice uses the project-controlled Calculation Slice 6 "
    "Channel reference and complete region-resultant decomposition, a rational back/opening "
    "web-face shear-center couple decomposition, rational web/flange face-sublayer transfers, "
    "Calculation Slice 4 plate strengths, inherited rational plate-body interaction, and actual "
    "unequal two-plane common-bolt shear demands. These connection-detail methods are not "
    "prescribed directly by ASCE/SEI 74-23. The engineer of record shall review the section, "
    "contact and shear-center idealizations, stiffness compatibility, open-section torsion and "
    "warping response, out-of-plane deformation, prying, secondary bolt bending, experimental "
    "qualification under Section 2.3.2, and all source-pending fastener properties. Connection "
    "stiffness, rotation capacity, and full-strength classification are not evaluated."
)


@dataclass(frozen=True, slots=True)
class ChannelWebFaceDecomposition:
    web_reference_t: PhysicalQuantity
    back_reference_t: PhysicalQuantity
    opening_reference_t: PhysicalQuantity
    web_normal_force: PhysicalQuantity
    web_major_shear: PhysicalQuantity
    web_local_major_moment: PhysicalQuantity
    web_free_torsion: PhysicalQuantity
    back_normal_force: PhysicalQuantity
    opening_normal_force: PhysicalQuantity
    back_major_shear: PhysicalQuantity
    opening_major_shear: PhysicalQuantity
    back_local_major_moment: PhysicalQuantity
    opening_local_major_moment: PhysicalQuantity
    normal_force_residual: PhysicalQuantity
    major_shear_residual: PhysicalQuantity
    local_major_moment_residual: PhysicalQuantity
    free_torsion_residual: PhysicalQuantity
    exact_normal_force_recovery: bool
    exact_major_shear_recovery: bool
    exact_local_major_moment_recovery: bool
    exact_free_torsion_recovery: bool
    blind_equal_shear_assumption_used: bool
    method: str
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
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def decompose_channel_web_wrench(
    *,
    web_reference_t: PhysicalQuantity,
    back_reference_t: PhysicalQuantity,
    opening_reference_t: PhysicalQuantity,
    web_normal_force: PhysicalQuantity,
    web_major_shear: PhysicalQuantity,
    web_local_major_moment: PhysicalQuantity,
    web_free_torsion: PhysicalQuantity,
) -> ChannelWebFaceDecomposition:
    """Resolve the two web-face branches from exact force and torsional-couple equilibrium."""

    for name, value in (
        ("web_reference_t", web_reference_t),
        ("back_reference_t", back_reference_t),
        ("opening_reference_t", opening_reference_t),
    ):
        if value.dimension is not Dimension.LENGTH:
            raise ValueError(f"{name} must be a length.")
    for name, value in (
        ("web_normal_force", web_normal_force),
        ("web_major_shear", web_major_shear),
    ):
        if value.dimension is not Dimension.FORCE:
            raise ValueError(f"{name} must be a force.")
    for name, value in (
        ("web_local_major_moment", web_local_major_moment),
        ("web_free_torsion", web_free_torsion),
    ):
        if value.dimension is not Dimension.MOMENT:
            raise ValueError(f"{name} must be a moment.")

    length_unit = web_reference_t.unit
    force_unit = web_major_shear.unit
    moment_unit = web_free_torsion.unit
    e_back = back_reference_t.to(length_unit).magnitude - web_reference_t.magnitude
    e_open = opening_reference_t.to(length_unit).magnitude - web_reference_t.magnitude
    if e_back >= 0 or e_open <= 0 or e_back == e_open:
        raise ValueError("OPPOSITE_SIGN_CHANNEL_WEB_FACE_OFFSETS_REQUIRED")
    scale = (
        PhysicalQuantity.of(1, force_unit).canonical_magnitude
        * PhysicalQuantity.of(1, length_unit).canonical_magnitude
        / PhysicalQuantity.of(1, moment_unit).canonical_magnitude
    )
    with localcontext() as context:
        context.prec = 100
        normal_each = web_normal_force.magnitude / 2
        moment_each = web_local_major_moment.magnitude / 2
        torsion_as_force_length = web_free_torsion.magnitude / scale
        back_shear = (torsion_as_force_length + e_open * web_major_shear.magnitude) / (
            e_open - e_back
        )
        opening_shear = web_major_shear.magnitude - back_shear
        normal_residual = normal_each * 2 - web_normal_force.magnitude
        shear_residual = back_shear + opening_shear - web_major_shear.magnitude
        moment_residual = moment_each * 2 - web_local_major_moment.magnitude
        torsion_residual = (
            -(e_back * back_shear + e_open * opening_shear) * scale - web_free_torsion.magnitude
        )

    q = PhysicalQuantity.of
    partial = ChannelWebFaceDecomposition(
        web_reference_t,
        back_reference_t,
        opening_reference_t,
        web_normal_force,
        web_major_shear,
        web_local_major_moment,
        web_free_torsion,
        q(normal_each, web_normal_force.unit),
        q(normal_each, web_normal_force.unit),
        q(back_shear, force_unit),
        q(opening_shear, force_unit),
        q(moment_each, web_local_major_moment.unit),
        q(moment_each, web_local_major_moment.unit),
        q(normal_residual, web_normal_force.unit),
        q(shear_residual, force_unit),
        q(moment_residual, web_local_major_moment.unit),
        q(torsion_residual, moment_unit),
        normal_residual == 0,
        shear_residual == 0,
        moment_residual == 0,
        torsion_residual == 0,
        False,
        CHANNEL_WEB_BRANCH_METHOD,
        "",
    )
    return replace(partial, result_fingerprint=_fingerprint(partial))


def evaluate_channel_two_plane_bolt(
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
    """Reuse the accepted unequal-plane method for Channel web or flange paths."""

    if len(physical_path) != 3:
        raise ValueError("A Channel common bolt requires exactly three physical layers.")
    evaluation_path = (
        physical_path
        if "FLANGE" in physical_path[1]
        else (physical_path[0], "CHANNEL_WEB_FLANGE_COMPATIBLE_EVALUATION", physical_path[2])
    )
    inherited = evaluate_asymmetric_two_plane_bolt(
        bolt_id=bolt_id,
        physical_path=evaluation_path,
        outer_plane=outer_plane,
        inner_plane=inner_plane,
        diameter=diameter,
        thread_condition=thread_condition,
        source_authority_id=source_authority_id,
        nominal_shear_stress=nominal_shear_stress,
    )
    rebound = replace(inherited, physical_path=physical_path, result_fingerprint="")
    return replace(rebound, result_fingerprint=_fingerprint(rebound))


__all__ = (
    "CHANNEL_MOMENT_SPLICE_DISCLAIMER",
    "CHANNEL_MOMENT_SPLICE_DISCLAIMER_ID",
    "CHANNEL_MOMENT_SPLICE_QUALIFICATION",
    "CHANNEL_WEB_BRANCH_METHOD",
    "CHANNEL_WEB_SUBLAYER_METHOD",
    "WI_MOMENT_SPLICE_BOLT_METHOD",
    "WI_MOMENT_SPLICE_BRANCH_METHOD",
    "WI_MOMENT_SPLICE_PANEL_METHOD",
    "WI_MOMENT_SPLICE_SUBLAYER_METHOD",
    "AsymmetricBoltStatus",
    "AsymmetricTwoPlaneBoltResult",
    "ChannelWebFaceDecomposition",
    "FlangeBodyStatus",
    "FlangeBranchDecomposition",
    "FlangePlaneDemand",
    "FlangePlateBodyResult",
    "decompose_channel_web_wrench",
    "decompose_flange_wrench",
    "evaluate_asymmetric_two_plane_bolt",
    "evaluate_channel_two_plane_bolt",
    "evaluate_flange_plate_body",
)
