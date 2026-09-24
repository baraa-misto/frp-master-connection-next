"""Versioned SSMC single-lap analytical adapter with exact source gates.

This is additive to SSMC-2. No public-supplied string is accepted as a
material, hardware, resistance, or Section 2.3.2 authority.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from frp_master_connection.application.ssmc import (
    SSMCPreview,
    negate,
    preview_ssmc,
    vector,
)
from frp_master_connection.application.ssmc_member_demand import (
    SSMCMemberTransferDemand,
    member_transfer_demand,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    components,
    shift_angle_wrench,
)
from frp_master_connection.calculation.equations import bolt_shear_resistance_from_nominal_stress
from frp_master_connection.calculation.inputs import TimeEffectCategory, select_time_effect_factor
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.ssmc_cuts import SSMCCutLedger, build_ssmc_cut_ledger
from frp_master_connection.domain.ssmc import SSMCRequest

METHOD = "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1"
CONTRACT = "SSMC-3-ANALYTICAL-RC1"
IDEALIZATION = "SSMC_SINGLE_LAP_IN_PLANE_NO_PRYING"
LAP_MODES = frozenset(
    {"PIN_BEARING", "FIRST_ROW_TENSION", "INTERROW_SHEAR_OUT", "BLOCK_SHEAR", "CLEAVAGE"}
)
FRP_PATH_MODES = (
    "PIN_BEARING",
    "FIRST_ROW_TENSION",
    "INTERROW_SHEAR_OUT",
    "CLEAVAGE",
    "BLOCK_SHEAR",
)
CLAUSES = MappingProxyType(
    {
        "PIN_BEARING": "ASCE/SEI 74-23 8.3.2.3, 8.3.3",
        "FIRST_ROW_TENSION": "ASCE/SEI 74-23 8.3.3.1",
        "INTERROW_SHEAR_OUT": "ASCE/SEI 74-23 8.3.3.2",
        "CLEAVAGE": "ASCE/SEI 74-23 8.3.2.6, 8.3.3",
        "BLOCK_SHEAR": "ASCE/SEI 74-23 8.3.3.3",
        "PULL_THROUGH": "ASCE/SEI 74-23 8.3.2.2",
        "BOLT_SHEAR": "ASCE/SEI 74-23 8.3.2.1",
    }
)


def _digest(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


@dataclass(frozen=True, slots=True)
class SSMCDesignAction:
    basis: str
    combination_id: str
    combination_source: str
    already_factored: bool
    time_effect_category: TimeEffectCategory
    time_effect_reference: str

    def __post_init__(self) -> None:
        if (
            self.basis != "FACTORED_LRFD"
            or not self.combination_id.strip()
            or not self.combination_source.strip()
            or self.already_factored is not True
            or not isinstance(self.time_effect_category, TimeEffectCategory)
            or not self.time_effect_reference.strip()
        ):
            raise ValueError("SSMC_FACTORED_LRFD_ACTION_AUTHORITY_REQUIRED")


@dataclass(frozen=True, slots=True)
class SSMCSingleLapDeclaration:
    external_actions_at_faying_interface: bool
    independent_normal_force: PhysicalQuantity
    independent_out_of_plane_moment: PhysicalQuantity
    imposed_separation: bool
    non_contact_gap: bool
    friction_or_preload_credit: bool
    miter_bearing_credit: bool

    def __post_init__(self) -> None:
        if (
            self.independent_normal_force.dimension is not Dimension.FORCE
            or self.independent_out_of_plane_moment.dimension is not Dimension.MOMENT
        ):
            raise ValueError("SSMC_SINGLE_LAP_ACTION_DIMENSION_INVALID")


@dataclass(frozen=True, slots=True)
class SSMCAnalyticalRequest:
    physical: SSMCRequest
    action: SSMCDesignAction
    single_lap: SSMCSingleLapDeclaration
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT:
            raise ValueError("SSMC_ANALYTICAL_CONTRACT_INVALID")


@dataclass(frozen=True, slots=True)
class SSMCQualifiedModeAuthority:
    """Exact configuration/path qualification; no generic scalar conversion."""

    binding: str
    owner: str
    path_id: str
    mode: str
    product_id: str
    cut_process_id: str
    direction: str
    method_id: str
    qualification_id: str
    source_sha256: str
    approval_sha256: str
    nominal_resistance: PhysicalQuantity
    phi: Decimal
    c_delta: Decimal
    cm: Decimal
    ct: Decimal
    cch: Decimal
    transfer_envelope: str

    def valid_for(self, binding: str, owner: str, path_id: str, mode: str) -> bool:
        return (
            mode != "PIN_BEARING"
            and self.binding == binding
            and self.owner == owner
            and self.path_id == path_id
            and self.mode == mode
            and self.method_id.startswith("PROJECT_2_3_2:")
            and self.transfer_envelope == binding
            and all(
                value.strip()
                for value in (
                    self.product_id,
                    self.cut_process_id,
                    self.direction,
                    self.method_id,
                    self.qualification_id,
                    self.transfer_envelope,
                )
            )
            and _digest(self.source_sha256)
            and _digest(self.approval_sha256)
            and self.nominal_resistance.dimension is Dimension.FORCE
            and self.nominal_resistance.canonical_magnitude > 0
            and all(
                math.isfinite(float(factor)) and factor > 0
                for factor in (self.phi, self.c_delta, self.cm, self.ct, self.cch)
            )
        )


@dataclass(frozen=True, slots=True)
class SSMCBearingAuthority:
    """Procedure-C/D7290 pin-bearing source for one actual layer and shaft."""

    binding: str
    owner: str
    shaft_id: str
    product_id: str
    cut_process_id: str
    direction: str
    characteristic_strength: PhysicalQuantity
    tested_bolt_diameter: PhysicalQuantity
    tested_hole_diameter: PhysicalQuantity
    tested_material_id: str
    procedure_c_report_id: str
    d7290_characteristic_id: str
    production_variability_phi_basis_id: str
    phi: Decimal
    cm: Decimal
    ct: Decimal
    cch: Decimal
    c_delta: Decimal
    washer_nut_condition: str
    qualification_id: str
    source_sha256: str
    approval_sha256: str

    def valid_for(
        self,
        binding: str,
        owner: str,
        shaft_id: str,
        direction: str,
        diameter_mm: float,
        hole_mm: float,
    ) -> bool:
        return (
            self.binding == binding
            and self.owner == owner
            and self.shaft_id == shaft_id
            and self.direction == direction
            and all(
                value.strip()
                for value in (
                    self.product_id,
                    self.cut_process_id,
                    self.tested_material_id,
                    self.procedure_c_report_id,
                    self.d7290_characteristic_id,
                    self.production_variability_phi_basis_id,
                    self.qualification_id,
                )
            )
            and self.characteristic_strength.dimension is Dimension.STRESS
            and self.characteristic_strength.canonical_magnitude > 0
            and self.tested_bolt_diameter.to(Unit.MM).magnitude == Decimal(str(diameter_mm))
            and self.tested_hole_diameter.to(Unit.MM).magnitude == Decimal(str(hole_mm))
            and self.washer_nut_condition in {"BOTH_SIDES", "ONE_SIDE_MISSING"}
            and _digest(self.source_sha256)
            and _digest(self.approval_sha256)
            and all(
                math.isfinite(float(factor)) and factor > 0
                for factor in (self.phi, self.cm, self.ct, self.cch, self.c_delta)
            )
        )


@dataclass(frozen=True, slots=True)
class SSMCHardwareAuthority:
    binding: str
    specification: str
    alloy_group_condition: str
    fnt: PhysicalQuantity
    fnv: PhysicalQuantity
    threads_at_shear_plane: bool
    body_area_basis: str
    grip_engagement_id: str
    head_nut_washer_compatibility_id: str
    source_sha256: str
    approval_sha256: str

    def valid_for(self, binding: str, threads: str) -> bool:
        return (
            self.binding == binding
            and self.body_area_basis == "NOMINAL_UNTHREADED_BODY_AREA"
            and all(
                value.strip()
                for value in (
                    self.specification,
                    self.alloy_group_condition,
                    self.body_area_basis,
                    self.grip_engagement_id,
                    self.head_nut_washer_compatibility_id,
                )
            )
            and self.fnt.dimension is Dimension.STRESS
            and self.fnv.dimension is Dimension.STRESS
            and self.fnt.canonical_magnitude > 0
            and self.fnv.canonical_magnitude > 0
            and self.threads_at_shear_plane == (threads == "INCLUDED")
            and _digest(self.source_sha256)
            and _digest(self.approval_sha256)
        )


@dataclass(frozen=True, slots=True)
class SSMCAnalyticalAuthorities:
    modes: Mapping[tuple[str, str, str], SSMCQualifiedModeAuthority]
    bearings: Mapping[tuple[str, str], SSMCBearingAuthority] | None = None
    hardware: SSMCHardwareAuthority | None = None
    plate_product_qualification_id: str = ""
    member_applicability_qualification_id: str = ""
    section_2_3_2_qualification_id: str = ""
    continuous_cut_coverage_id: str = ""


EMPTY_ANALYTICAL_AUTHORITIES = SSMCAnalyticalAuthorities(MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class SSMCActionReaction:
    group_id: str
    action_on_plate: AngleWrench
    reaction_on_member: AngleWrench
    member_cut_reaction: AngleWrench
    faying_interface_action: AngleWrench
    secondary_thickness_moment: tuple[float, float]
    exact_opposition_proven: bool
    full_planar_equilibrium_proven: bool


@dataclass(frozen=True, slots=True)
class SSMCAnalyticalCheck:
    owner: str
    path_id: str
    mode: str
    demand_N: float
    signed_force_N: tuple[float, float]
    direction: str
    thickness_mm: float | None
    bolt_diameter_mm: float | None
    hole_diameter_mm: float | None
    clause: str
    applicability_proof: str
    source_id: str | None
    qualification_id: str | None
    nominal_resistance_N: float | None
    design_resistance_N: float | None
    factors: tuple[tuple[str, str], ...]
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class SSMCAnalyticalResult:
    contract: str
    method: str
    request: SSMCAnalyticalRequest
    existing_demand: SSMCPreview
    applicability_status: str
    applicability_reasons: tuple[str, ...]
    action_reaction: tuple[SSMCActionReaction, ...]
    member_cut_demands: tuple[SSMCMemberTransferDemand, ...]
    cuts: SSMCCutLedger
    checks: tuple[SSMCAnalyticalCheck, ...]
    blockers: tuple[str, ...]
    numerical_failures: tuple[str, ...]
    whole_connection_status: str


def _applicability(
    request: SSMCAnalyticalRequest, preview: SSMCPreview
) -> tuple[str, tuple[str, ...]]:
    declaration = request.single_lap
    reasons = []
    if not declaration.external_actions_at_faying_interface:
        reasons.append("EXTERNAL_ACTION_REFERENCE_NOT_FAYING_INTERFACE")
    if declaration.independent_normal_force.canonical_magnitude != 0:
        reasons.append("INDEPENDENT_BOLT_AXIS_FORCE")
    if declaration.independent_out_of_plane_moment.canonical_magnitude != 0:
        reasons.append("INDEPENDENT_OUT_OF_PLANE_MOMENT")
    if declaration.imposed_separation:
        reasons.append("IMPOSED_SEPARATION")
    if declaration.non_contact_gap:
        reasons.append("NON_CONTACT_GAP")
    if declaration.friction_or_preload_credit:
        reasons.append("FRICTION_OR_PRELOAD_CREDIT")
    if declaration.miter_bearing_credit:
        reasons.append("MITER_BEARING_CREDIT")
    if any(g.native_slice8 is None for g in preview.groups):
        reasons.append("PLANAR_GROUP_ELIGIBILITY")
    if any(
        g.slots or not g.ordinary_snug_tight
        for g in (request.physical.horizontal_group, request.physical.inclined_group)
    ):
        reasons.append("SLOT_OR_INSTALLATION")
    return (
        ("ENGINEERING_REVIEW_REQUIRED" if reasons else "ELIGIBLE"),
        tuple(reasons),
    )


def _faying_wrench(wrench: AngleWrench, unit: Unit) -> AngleWrench:
    point = wrench.reference
    return shift_angle_wrench(
        wrench,
        vector((point.x.magnitude, Decimal(0), point.z.magnitude), unit),
    )


def _actions(preview: SSMCPreview) -> tuple[SSMCActionReaction, ...]:
    records = []
    for index, (group, member) in enumerate(
        zip(preview.groups, preview.geometry.members, strict=True)
    ):
        action = group.plate_wrench
        reaction = negate(action)
        axis = member.material_longitudinal
        shafts = tuple(s for s in preview.geometry.shafts if s.group == group.group_id)
        pattern = preview.input.horizontal_group if index == 0 else preview.input.inclined_group
        section = preview.input.horizontal if index == 0 else preview.input.inclined
        last_shaft_station = max(s.center[0] * axis.x + s.center[1] * axis.z for s in shafts)
        member_end_station = float(section.length.to(preview.input.length_unit).magnitude) / 2
        if member_end_station <= last_shaft_station:
            raise ArithmeticError("SSMC_MEMBER_CUT_BEYOND_GROUP_NOT_AVAILABLE")
        station = min(
            last_shaft_station + float(pattern.pitch.to(preview.input.length_unit).magnitude) / 2,
            (last_shaft_station + member_end_station) / 2,
        )
        cut = shift_angle_wrench(
            reaction,
            vector(
                (
                    Decimal(str(station * axis.x)),
                    Decimal(str(member.web_reference_y)),
                    Decimal(str(station * axis.z)),
                ),
                preview.input.length_unit,
            ),
        )
        faying = _faying_wrench(action, preview.input.length_unit)
        m = components(action.moment)
        mf = components(faying.moment)
        opposite = all(
            tuple(-v for v in components(getattr(action, key)))
            == components(getattr(reaction, key))
            for key in ("force", "moment")
        )
        planar = (
            group.native_slice8 is not None
            and group.native_slice8.status == "CALCULATED"
            and group.native_slice8.solution.proof is not None
            and group.native_slice8.solution.proof.passed
        )
        records.append(
            SSMCActionReaction(
                group.group_id,
                action,
                reaction,
                cut,
                faying,
                (float(m[0] - mf[0]), float(m[2] - mf[2])),
                opposite,
                planar,
            )
        )
    return tuple(records)


def _authority_check(
    binding: str,
    authorities: SSMCAnalyticalAuthorities,
    *,
    owner: str,
    path_id: str,
    mode: str,
    demand: float,
    force: tuple[float, float],
    direction: str,
    thickness: float | None,
    diameter: float | None,
    hole: float | None,
    proof: str,
    lambda_factor: Decimal,
) -> SSMCAnalyticalCheck:
    record = authorities.modes.get((owner, path_id, mode))
    if record is None:
        status, reason = "SOURCE_REQUIRED", f"{mode}_EXACT_PATH_AUTHORITY_REQUIRED"
        nominal = design = None
        factors: tuple[tuple[str, str], ...] = ()
        source = qualification = None
    elif not record.valid_for(binding, owner, path_id, mode) or record.direction != direction:
        status, reason = "ENGINEERING_REVIEW_REQUIRED", f"{mode}_AUTHORITY_BINDING_INVALID"
        nominal = design = None
        factors = ()
        source = qualification = None
    else:
        lap = Decimal("0.6") if mode in LAP_MODES else Decimal(1)
        nominal = float(record.nominal_resistance.to(Unit.N).magnitude)
        design = float(
            record.nominal_resistance.to(Unit.N).magnitude
            * record.cm
            * record.ct
            * record.cch
            * record.c_delta
            * lap
            * record.phi
            * lambda_factor
        )
        status = "FAIL" if demand > design else "PASS"
        reason = "NUMERICAL_RESISTANCE_EXCEEDED" if status == "FAIL" else "QUALIFIED_CHECK_PASSED"
        factors = (
            ("Cm", str(record.cm)),
            ("Ct", str(record.ct)),
            ("Cch", str(record.cch)),
            ("C_delta", str(record.c_delta)),
            ("C_lap", str(lap)),
            ("phi", str(record.phi)),
            ("lambda", str(lambda_factor)),
        )
        source, qualification = record.source_sha256, record.qualification_id
    return SSMCAnalyticalCheck(
        owner,
        path_id,
        mode,
        demand,
        force,
        direction,
        thickness,
        diameter,
        hole,
        CLAUSES.get(mode, "PROJECT-SPECIFIC QUALIFIED METHOD"),
        proof,
        source,
        qualification,
        nominal,
        design,
        factors,
        status,
        reason,
    )


def _bearing_check(
    binding: str,
    authorities: SSMCAnalyticalAuthorities,
    *,
    owner: str,
    shaft_id: str,
    demand: float,
    force: tuple[float, float],
    direction: str,
    thickness: float,
    diameter: float,
    hole: float,
    threads: str,
    lambda_factor: Decimal,
) -> SSMCAnalyticalCheck:
    record = (authorities.bearings or {}).get((owner, shaft_id))
    if record is None:
        status, reason = "SOURCE_REQUIRED", "PIN_BEARING_PROCEDURE_C_D7290_SOURCE_REQUIRED"
        nominal = design = None
        factors: tuple[tuple[str, str], ...] = ()
        source = qualification = None
    elif not record.valid_for(binding, owner, shaft_id, direction, diameter, hole):
        status, reason = (
            "ENGINEERING_REVIEW_REQUIRED",
            "PIN_BEARING_SOURCE_GEOMETRY_OR_DIRECTION_INVALID",
        )
        nominal = design = None
        factors = ()
        source = qualification = None
    else:
        zeta = Decimal(1) if threads == "EXCLUDED" else Decimal("0.6")
        washer = Decimal(1) if record.washer_nut_condition == "BOTH_SIDES" else Decimal("0.5")
        lap = Decimal("0.6")
        nominal_decimal = (
            Decimal(str(thickness))
            * Decimal(str(diameter))
            * record.characteristic_strength.to(Unit.MPA).magnitude
            * record.cm
            * record.ct
            * record.cch
            * zeta
            * washer
        )
        design_decimal = nominal_decimal * record.c_delta * lap * record.phi * lambda_factor
        nominal, design = float(nominal_decimal), float(design_decimal)
        status = "FAIL" if demand > design else "PASS"
        reason = "NUMERICAL_RESISTANCE_EXCEEDED" if status == "FAIL" else "QUALIFIED_CHECK_PASSED"
        factors = (
            ("Cm", str(record.cm)),
            ("Ct", str(record.ct)),
            ("Cch", str(record.cch)),
            ("zeta", str(zeta)),
            ("washer_nut", str(washer)),
            ("C_delta", str(record.c_delta)),
            ("C_lap", str(lap)),
            ("phi", str(record.phi)),
            ("lambda", str(lambda_factor)),
        )
        source, qualification = record.source_sha256, record.qualification_id
    return SSMCAnalyticalCheck(
        owner,
        shaft_id,
        "PIN_BEARING",
        demand,
        force,
        direction,
        thickness,
        diameter,
        hole,
        CLAUSES["PIN_BEARING"],
        "ACTUAL_SIGNED_VECTOR;PHYSICAL_LAYER;MATCHED_BOLT_HOLE_TEST_GEOMETRY",
        source,
        qualification,
        nominal,
        design,
        factors,
        status,
        reason,
    )


def evaluate_ssmc_analytical(
    request: SSMCAnalyticalRequest,
    authorities: SSMCAnalyticalAuthorities = EMPTY_ANALYTICAL_AUTHORITIES,
) -> SSMCAnalyticalResult:
    """Return truthful demand, path and source ledgers; no historical ASD PASS."""
    preview = preview_ssmc(request.physical)
    applicability, reasons = _applicability(request, preview)
    actions = _actions(preview)
    member_cut_demands = tuple(
        member_transfer_demand(
            section,
            member,
            action.member_cut_reaction,
        )
        for section, member, action in zip(
            (request.physical.horizontal, request.physical.inclined),
            preview.geometry.members,
            actions,
            strict=True,
        )
    )
    cuts = build_ssmc_cut_ledger(preview)
    binding = preview.engineering_fingerprint
    lambda_factor = select_time_effect_factor(request.action.time_effect_category).value
    diameter = float(request.physical.fastener.diameter.to(Unit.MM).magnitude)
    hole = float(request.physical.fastener.hole_diameter.to(Unit.MM).magnitude)
    plate_thickness = float(request.physical.plate.thickness.to(Unit.MM).magnitude)
    length_scale = 25.4 if request.physical.length_unit is Unit.IN else 1.0
    checks: list[SSMCAnalyticalCheck] = []
    group_bolts = {
        group.group_id: {bolt.bolt_id: bolt for bolt in group.native_slice8.solution.bolts}
        for group in preview.groups
        if group.native_slice8 is not None and group.native_slice8.status == "CALCULATED"
    }
    for shaft in preview.geometry.shafts:
        bolt = group_bolts.get(shaft.group, {}).get(shaft.id)
        force = (float(bolt.total[0]), float(bolt.total[1])) if bolt is not None else (0.0, 0.0)
        demand = math.hypot(*force)
        for owner in shaft.layer_owners:
            member = next((m for m in preview.geometry.members if m.owner == owner), None)
            thickness = (
                plate_thickness
                if member is None
                else float(
                    (
                        request.physical.horizontal
                        if owner == "HORIZONTAL_STRINGER"
                        else request.physical.inclined
                    )
                    .web_thickness.to(Unit.MM)
                    .magnitude
                )
            )
            if owner == "MITER_WEB_PLATE":
                direction = "CW"
            else:
                if member is None:
                    raise ArithmeticError("SSMC_PHYSICAL_LAYER_OWNERSHIP_INVALID")
                axis = member.material_longitudinal
                dot = abs(force[0] * axis.x + force[1] * axis.z)
                angle = math.degrees(math.acos(min(1.0, dot / demand))) if demand else 0.0
                direction = "L" if angle <= 5 else "T"
            checks.append(
                _bearing_check(
                    binding,
                    authorities,
                    owner=owner,
                    shaft_id=shaft.id,
                    demand=demand,
                    force=force,
                    direction=direction,
                    thickness=thickness,
                    diameter=diameter,
                    hole=hole,
                    threads=request.physical.fastener.threads,
                    lambda_factor=lambda_factor,
                )
            )
        hardware = authorities.hardware
        if hardware is None or not hardware.valid_for(binding, request.physical.fastener.threads):
            checks.append(
                SSMCAnalyticalCheck(
                    shaft.id,
                    shaft.id,
                    "BOLT_SHEAR",
                    demand,
                    force,
                    "IN_PLANE",
                    None,
                    diameter,
                    hole,
                    CLAUSES["BOLT_SHEAR"],
                    "ONE_PHYSICAL_SHAFT_ONE_SHEAR_PLANE",
                    None,
                    None,
                    None,
                    None,
                    (),
                    "SOURCE_REQUIRED",
                    "HARDWARE_FNT_FNV_GRIP_THREAD_AUTHORITY_REQUIRED",
                )
            )
        else:
            trace = bolt_shear_resistance_from_nominal_stress(
                request.physical.fastener.diameter, hardware.fnv
            )
            nominal = float(trace.nominal_resistance.to(Unit.N).magnitude)
            design = float(trace.design_resistance.to(Unit.N).magnitude)
            checks.append(
                SSMCAnalyticalCheck(
                    shaft.id,
                    shaft.id,
                    "BOLT_SHEAR",
                    demand,
                    force,
                    "IN_PLANE",
                    None,
                    diameter,
                    hole,
                    CLAUSES["BOLT_SHEAR"],
                    "ONE_PHYSICAL_SHAFT_ONE_SHEAR_PLANE",
                    hardware.source_sha256,
                    hardware.approval_sha256,
                    nominal,
                    design,
                    (("phi", "0.75"), ("lambda", "1.0"), ("C_lap", "1")),
                    "FAIL" if demand > design else "PASS",
                    (
                        "NUMERICAL_RESISTANCE_EXCEEDED"
                        if demand > design
                        else "QUALIFIED_CHECK_PASSED"
                    ),
                )
            )
        checks.append(
            SSMCAnalyticalCheck(
                shaft.id,
                shaft.id,
                "PULL_THROUGH",
                0.0,
                force,
                "BOLT_AXIS",
                None,
                diameter,
                hole,
                CLAUSES["PULL_THROUGH"],
                "PURE_IN_PLANE_NO_INDEPENDENT_AXIS_FORCE_OR_PRYING"
                if applicability == "ELIGIBLE"
                else "APPLICABILITY_NOT_PROVEN",
                None,
                None,
                None,
                None,
                (),
                "NOT_APPLICABLE" if applicability == "ELIGIBLE" else "ENGINEERING_REVIEW_REQUIRED",
                "BOUNDED_SINGLE_LAP_PROOF"
                if applicability == "ELIGIBLE"
                else "PULL_THROUGH_REVIEW_REQUIRED",
            )
        )
    for group in preview.groups:
        force = (
            float(group.plate_wrench.force.x.to(Unit.N).magnitude),
            float(group.plate_wrench.force.z.to(Unit.N).magnitude),
        )
        demand = math.hypot(*force)
        for owner in (
            "MITER_WEB_PLATE",
            preview.geometry.shafts[
                0
                if group.group_id == preview.groups[0].group_id
                else len(
                    [s for s in preview.geometry.shafts if s.group == preview.groups[0].group_id]
                )
            ].member,
        ):
            for mode in FRP_PATH_MODES[1:]:
                # Cleavage remains a conditional local cut-end mode. Its
                # single-row FRP strength receives the lap factor once.
                direction = "CW" if owner == "MITER_WEB_PLATE" else "MEMBER_LOCAL"
                checks.append(
                    _authority_check(
                        binding,
                        authorities,
                        owner=owner,
                        path_id=f"{group.group_id}:{mode}",
                        mode=mode,
                        demand=demand,
                        force=force,
                        direction=direction,
                        thickness=plate_thickness if owner == "MITER_WEB_PLATE" else None,
                        diameter=diameter,
                        hole=hole,
                        proof="ACTUAL_GROUP_VECTOR;PATH_GEOMETRY_AND_CLAUSE_GATE_REQUIRED",
                        lambda_factor=lambda_factor,
                    )
                )
    for path in preview.geometry.polygon_paths.candidates:
        shaft = next(s for s in preview.geometry.shafts if s.id == path.from_owner)
        bolt = group_bolts.get(shaft.group, {}).get(shaft.id)
        force = (float(bolt.total[0]), float(bolt.total[1])) if bolt is not None else (0.0, 0.0)
        if path.kind == "HOLE_TO_EDGE":
            path_vector = (
                path.end[0] - path.start[0],
                path.end[1] - path.start[1],
            )
            projection = force[0] * path_vector[0] + force[1] * path_vector[1]
            mode = "SHEAR_OUT_EDGE_PATH" if projection > 0 else "CLEAVAGE_EDGE_PATH"
            directed = projection > 0
        else:
            mode = "BLOCK_SHEAR_HOLE_PATH"
            directed = True
        if bolt is None:
            status = "ENGINEERING_REVIEW_REQUIRED"
            reason = "PLANAR_DEMAND_REQUIRED"
        elif path.connected_material and directed:
            status = "SOURCE_REQUIRED"
            reason = "LOAD_DIRECTED_POLYGON_PATH_METHOD_AND_QUALIFICATION_REQUIRED"
        else:
            status = "NOT_APPLICABLE"
            reason = (
                "NO_CONNECTED_MATERIAL"
                if not path.connected_material
                else "FORCE_DIRECTED_AWAY_FROM_EDGE"
            )
        checks.append(
            SSMCAnalyticalCheck(
                "MITER_WEB_PLATE",
                path.id,
                mode,
                math.hypot(*force),
                force,
                "CW",
                plate_thickness,
                diameter,
                hole,
                "ASCE/SEI 74-23 8.3.2.5-8.3.3.3; EXACT POLYGON PATH",
                f"CONNECTED={path.connected_material};DIRECTED={directed};"
                f"CLEAR_LENGTH_MM={path.clear_length * length_scale}",
                None,
                None,
                None,
                None,
                (),
                status,
                reason,
            )
        )
    for cut in cuts.cuts:
        checks.append(
            SSMCAnalyticalCheck(
                "MITER_WEB_PLATE",
                cut.cut_id,
                "POLYGON_CUT_NVM",
                abs(cut.cut_N_N),
                (cut.cut_N_N, cut.cut_V_N),
                "CW",
                plate_thickness,
                diameter,
                hole,
                "ASCE/SEI 74-23 2.3.2; ACTUAL POLYGON SECTION",
                f"SIGNED_N_N={cut.cut_N_N};SIGNED_V_N={cut.cut_V_N};"
                f"SIGNED_M_NMM={cut.cut_M_Nmm};NET_AREA_MM2={cut.net_area_mm2}",
                None,
                None,
                None,
                None,
                (),
                "ENGINEERING_REVIEW_REQUIRED",
                "POLYGON_CUT_STRENGTH_INTERACTION_STABILITY_AND_COVERAGE_AUTHORITY_REQUIRED",
            )
        )
    for transfer in member_cut_demands:
        group = next(
            g
            for g in preview.groups
            if g.group_id.startswith(
                "HORIZONTAL" if transfer.member == "HORIZONTAL_STRINGER" else "INCLINED"
            )
        )
        force = (
            float(group.plate_wrench.force.x.to(Unit.N).magnitude),
            float(group.plate_wrench.force.z.to(Unit.N).magnitude),
        )
        checks.append(
            _authority_check(
                binding,
                authorities,
                owner=transfer.member,
                path_id=f"{transfer.member}:CUT",
                mode="MEMBER_NVM_AND_CUT_END",
                demand=math.hypot(*force),
                force=force,
                direction="MEMBER_LOCAL",
                thickness=None,
                diameter=None,
                hole=None,
                proof="REACTION_TRANSPORTED_TO_MEMBER_CUT;NATIVE_AXIAL_MAJOR_RESULTANTS_ONLY",
                lambda_factor=lambda_factor,
            )
        )
    blockers = list(reasons)
    if not cuts.finite_coverage_proven or not authorities.continuous_cut_coverage_id:
        blockers.append("POLYGON_CONTINUOUS_CUT_COVERAGE_NOT_PROVEN")
    for name, value in (
        ("PLATE_PRODUCT_QUALIFICATION_REQUIRED", authorities.plate_product_qualification_id),
        (
            "MEMBER_APPLICABILITY_QUALIFICATION_REQUIRED",
            authorities.member_applicability_qualification_id,
        ),
        ("SECTION_2_3_2_QUALIFICATION_REQUIRED", authorities.section_2_3_2_qualification_id),
    ):
        if not value:
            blockers.append(name)
    blockers.extend(
        f"{c.owner}:{c.path_id}:{c.reason}"
        for c in checks
        if c.status in {"SOURCE_REQUIRED", "ENGINEERING_REVIEW_REQUIRED"}
    )
    failures = tuple(f"{c.owner}:{c.path_id}:{c.mode}" for c in checks if c.status == "FAIL")
    status = "FAIL" if failures else "ENGINEERING_REVIEW_REQUIRED" if blockers else "PASS"
    return SSMCAnalyticalResult(
        CONTRACT,
        METHOD,
        request,
        preview,
        applicability,
        reasons,
        actions,
        member_cut_demands,
        cuts,
        tuple(checks),
        tuple(blockers),
        failures,
        status,
    )


__all__ = (
    "CONTRACT",
    "EMPTY_ANALYTICAL_AUTHORITIES",
    "IDEALIZATION",
    "METHOD",
    "SSMCActionReaction",
    "SSMCAnalyticalAuthorities",
    "SSMCAnalyticalCheck",
    "SSMCAnalyticalRequest",
    "SSMCAnalyticalResult",
    "SSMCBearingAuthority",
    "SSMCDesignAction",
    "SSMCHardwareAuthority",
    "SSMCQualifiedModeAuthority",
    "SSMCSingleLapDeclaration",
    "evaluate_ssmc_analytical",
)
