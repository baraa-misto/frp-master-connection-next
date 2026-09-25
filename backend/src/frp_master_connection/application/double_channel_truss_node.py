"""DCTN preview/design assembly; statics, local checks and global scope stay separate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.application.dctn_c3_geometry import build_dctn_c3, dctn_code_mappings
from frp_master_connection.application.dctn_native_local import dctn_plane_plans
from frp_master_connection.application.dctn_shared_channel import (
    DCTNSharedChannelReview,
    review_dctn_shared_channels,
)
from frp_master_connection.application.double_channel_truss_node_geometry import build_dctn_geometry
from frp_master_connection.application.mat1_scope import current_scope
from frp_master_connection.calculation.angle_connector_core import exact_decimal
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.dctn_local_resistance import (
    evaluate_native_dctn_plane,
    numerical_check,
)
from frp_master_connection.calculation.dctn_sources import (
    EMPTY_SOURCES,
    DCTNMaterialSource,
    DCTNSources,
    dctn_binding,
    hardware_source,
    material_source,
    mechanism_checks,
)
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
    evaluate_dctn_bearing,
)
from frp_master_connection.calculation.double_channel_truss_node_response import (
    DCTNResponse,
    calculate_dctn_response,
)
from frp_master_connection.calculation.equations import bolt_shear_resistance_from_nominal_stress
from frp_master_connection.calculation.geometry_mapping import CodeGeometryIssue
from frp_master_connection.calculation.inputs import EndUseFactors, select_time_effect_factor
from frp_master_connection.calculation.multirow_equations import constant_pitch_factor
from frp_master_connection.calculation.properties import FRPPropertyKind, ThreadStatus
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.dctn_geometry import DCTNBoltCode, DCTNGeometry, DCTNPlanePlan
from frp_master_connection.domain.double_channel_truss_node import (
    CONTRACT,
    PRODUCT,
    DCTNForm,
    DCTNRequest,
)
from frp_master_connection.domain.material_architecture import (
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    PropertySourceConfirmation,
)
from frp_master_connection.geometry.bolt_paths import ResolvedBoltGroupGeometry


@dataclass(frozen=True, slots=True)
class DCTNPreview:
    input: DCTNRequest
    geometry: DCTNGeometry
    response: DCTNResponse
    local_plans: tuple[DCTNPlanePlan, ...]
    native_bolt_groups: tuple[ResolvedBoltGroupGeometry, ...]
    native_code_geometry: tuple[DCTNBoltCode, ...]
    shared_channel_review: tuple[DCTNSharedChannelReview, ...]
    fingerprint: str
    connector_body_count: int = 0
    product: str = PRODUCT
    contract: str = CONTRACT
    global_chord_design_evaluated: bool = False
    global_boundary: str = "DCTN_GLOBAL_CHORD_DESIGN_OUTSIDE_LOCAL_CONNECTION_SCOPE"


def preview_dctn(value: DCTNRequest) -> DCTNPreview:
    geometry = build_dctn_geometry(value)
    response = calculate_dctn_response(value, geometry)
    groups = build_dctn_c3(value, geometry)
    codes = dctn_code_mappings(value, geometry, groups)
    plans = dctn_plane_plans(value, geometry, codes)
    shared = review_dctn_shared_channels(value, plans)
    return DCTNPreview(
        value,
        geometry,
        response,
        plans,
        groups,
        codes,
        shared,
        dctn_fingerprint((value, geometry, response, plans, groups, codes, shared)),
    )


def dctn_material_binding(preview: DCTNPreview, owner: str) -> str:
    return dctn_binding("FRP_PRODUCT_SECTION_USE", owner, preview.geometry, preview.input)


def _material_for_design(
    registry: DCTNSources, reference: str, owner: str, binding: str
) -> DCTNMaterialSource | None:
    """Expose pending MAT1 numbers to native checks without minting source authority."""

    scope = current_scope()
    if scope is None:
        return material_source(registry, reference, owner, binding)
    material = scope.material(owner)
    record = scope.overrides.get(owner, scope.default)[0]
    return DCTNMaterialSource(
        reference=f"MAT1:{record.id}:{record.revision}",
        owner_id=owner,
        source=EngineeringPropertySource(
            EngineeringPropertySourceKind.CONTROLLED_PROJECT_DATA,
            record.id,
            record.revision,
            PropertySourceConfirmation.PENDING_CONFIRMATION,
            (record.content_digest,),
            True,
        ),
        exact_binding=binding,
        material=material,
        factors=EndUseFactors(
            Decimal(1),
            Decimal(1),
            Decimal(1),
            "MAT1 condition coefficients already applied to typed property candidates",
            ("MAT1_PENDING_SOURCE_NUMERICAL_DIAGNOSTIC_ONLY",),
        ),
        lambda_factor=select_time_effect_factor(scope.default[1].time_category).value,
    )


def dctn_hardware_binding(preview: DCTNPreview) -> str:
    return dctn_binding(
        "INDEPENDENT_HARDWARE",
        "PHYSICAL_SHAFTS",
        (preview.input.fastener, preview.geometry.shafts),
        preview.response.shafts,
    )


def dctn_mechanism_binding(preview: DCTNPreview, owner: str) -> str:
    return dctn_binding(
        "LOCAL_MECHANISM", owner, (preview.geometry, preview.local_plans), preview.response
    )


@dataclass(frozen=True, slots=True)
class DCTNDesign:
    preview: DCTNPreview
    checks: tuple[DCTNRequiredCheck, ...]
    blockers: tuple[str, ...]
    governing_checks: tuple[str, ...]
    whole_connection_status: str
    fingerprint: str
    global_chord_design_evaluated: bool = False


def _absolute(value: PhysicalQuantity, divisor: int = 1) -> PhysicalQuantity:
    return PhysicalQuantity.of(
        exact_decimal(abs(Fraction(value.canonical_magnitude)) / divisor), Unit.N
    )


def _solid_checks(
    preview: DCTNPreview, registry: DCTNSources
) -> tuple[list[DCTNRequiredCheck], list[str]]:
    checks: list[DCTNRequiredCheck] = []
    blockers: list[str] = []
    request = preview.input
    for member in request.members:
        if member.section.form is not DCTNForm.SOLID_RECTANGLE:
            continue
        source = _material_for_design(
            registry,
            member.material_source_reference,
            member.slot,
            dctn_material_binding(preview, member.slot),
        )
        if source is None or not source.full_depth_solid_bearing:
            blockers.append(member.slot + ":DCTN_SOLID_FULL_DEPTH_PIN_BEARING_SOURCE_NOT_QUALIFIED")
            continue
        prop = next(
            (
                p
                for p in source.material.properties
                if p.kind is FRPPropertyKind.FBR_L
                and p.use_in_chapter_8_equations
                and p.qualification_status is QualificationStatus.QUALIFIED
            ),
            None,
        )
        if prop is None:
            blockers.append(member.slot + ":DCTN_SOLID_FULL_DEPTH_PIN_BEARING_SOURCE_NOT_QUALIFIED")
            continue
        c_delta = (
            constant_pitch_factor(
                (member.pattern.pitch,) * (member.pattern.rows - 1), request.fastener.diameter
            ).pitch_factor_c_delta
            if member.pattern.rows > 1
            else Decimal(1)
        )
        for row in preview.response.rows:
            if row.member_id != member.slot:
                continue
            demand = _absolute(row.signed_row_force)
            result = evaluate_dctn_bearing(
                owner_id=member.slot,
                bolt_id=f"{member.slot}:ROW_{row.row}:THROUGH",
                incoming_form=DCTNForm.SOLID_RECTANGLE,
                designated_rhs_wall=False,
                thickness=member.section.depth,
                diameter=request.fastener.diameter,
                demand=demand,
                characteristic=prop.value,
                property_kind=prop.kind,
                qualification=prop.qualification_status,
                factors=source.factors,
                thread=ThreadStatus.EXCLUDED
                if request.fastener.threads_excluded
                else ThreadStatus.INCLUDED,
                c_delta=c_delta,
                lambda_factor=source.lambda_factor,
            )
            checks.append(
                numerical_check(
                    "FULL_DEPTH_PIN_BEARING:" + result.bolt_id,
                    member.slot,
                    demand,
                    result.native_trace.factor_trace.design_resistance,
                    result,
                    source.reference,
                )
            )
    return checks, blockers


def design_check_dctn(value: DCTNRequest, registry: DCTNSources = EMPTY_SOURCES) -> DCTNDesign:
    preview = preview_dctn(value)
    checks: list[DCTNRequiredCheck] = []
    blockers = list(preview.response.reasons)
    unresolved: dict[str, set[str]] = {}
    rows = {(r.member_id, r.row): r for r in preview.response.rows}
    if preview.response.status == "QUALIFIED":
        for record in preview.native_code_geometry:
            # Preserve the native finding in trace. Only its historical one-row
            # method limit is replaced by DCTN's explicitly approved 1..3-row
            # executor; every physical/qualification finding remains blocking.
            blockers.extend(
                record.owner_id + ":" + issue.value
                for issue in record.validation.issues
                if issue is not CodeGeometryIssue.STAGE_2_1A_SUPPORTS_ONE_BOLT_ONE_ROW
            )
        for plan in preview.local_plans:
            member = next(m for m in value.members if m.slot == plan.member_id)
            reference = (
                member.material_source_reference
                if plan.owner_id == member.slot
                else value.channel.material_source_reference
            )
            source = _material_for_design(
                registry, reference, plan.owner_id, dctn_material_binding(preview, plan.owner_id)
            )
            if source is None:
                blockers.append(plan.owner_id + ":DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED")
                # Geometry-derived unresolved paths remain visible independently.
                unresolved.setdefault(plan.owner_id, set()).update(plan.reasons)
                continue
            demands = []
            for hole in plan.geometry.group.bolts:
                physical = next(h for h in preview.geometry.holes if h.hole_id == hole.id)
                shaft = next(s for s in preview.geometry.shafts if s.bolt_id == physical.shaft_id)
                demands.append(
                    (hole.id, _absolute(rows[(shaft.member_id, shaft.row)].signed_row_force, 2))
                )
            local = evaluate_native_dctn_plane(value, plan, source, tuple(demands))
            checks.extend(local.checks)
            for reason in local.reasons:
                if reason == "DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED":
                    blockers.append(plan.owner_id + ":" + reason)
                else:
                    unresolved.setdefault(plan.owner_id, set()).add(reason)
        solid_checks, solid_blockers = _solid_checks(preview, registry)
        checks.extend(solid_checks)
        blockers.extend(solid_blockers)
        hardware = hardware_source(
            registry, value.fastener.source_reference, dctn_hardware_binding(preview)
        )
        if hardware is None or not value.fastener.snug_tight:
            blockers.append("DCTN_HARDWARE_SOURCE_OR_INSTALLATION_NOT_QUALIFIED")
        else:
            trace = bolt_shear_resistance_from_nominal_stress(
                value.fastener.diameter, hardware.nominal_shear_stress
            )
            for shaft_result in preview.response.shafts:
                # One physical bolt capacity, compared to actual distinct plane
                # demands. No sum of capacities or double-shear multiplier.
                demand = max(shaft_result.shear_plane_demands)
                checks.append(
                    numerical_check(
                        "HARDWARE_SHEAR:" + shaft_result.bolt_id,
                        shaft_result.bolt_id,
                        demand,
                        trace.design_resistance,
                        (trace, shaft_result),
                        hardware.reference,
                    )
                )
        for member in value.members:
            if member.section.form is DCTNForm.W_I:
                unresolved.setdefault(member.slot, set()).update(
                    {
                        "DCTN_WI_FLANGE_PATH_NOT_QUALIFIED",
                        "LOCAL_FLANGE_BENDING_ROOT_PULLTHROUGH_PRYING",
                    }
                )
            elif member.section.form is DCTNForm.SOLID_RECTANGLE:
                unresolved.setdefault(member.slot, set()).add(
                    "FULL_SOLID_THREE_DIMENSIONAL_LOCAL_PATHS"
                )
        for review in preview.shared_channel_review:
            if len(review.group_ids) <= 1:
                continue
            owner = review.owner_id
            unresolved.setdefault(owner, set()).update(review.reasons)
            combined_plan = review.common_force_plan
            if combined_plan is None:
                continue
            source = _material_for_design(
                registry,
                value.channel.material_source_reference,
                owner,
                dctn_material_binding(preview, owner),
            )
            if source is None:
                blockers.append(owner + ":DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED")
                continue
            combined_demands = []
            for hole in combined_plan.geometry.group.bolts:
                physical = next(h for h in preview.geometry.holes if h.hole_id == hole.id)
                shaft = next(s for s in preview.geometry.shafts if s.bolt_id == physical.shaft_id)
                combined_demands.append(
                    (hole.id, _absolute(rows[(shaft.member_id, shaft.row)].signed_row_force, 2))
                )
            combined = evaluate_native_dctn_plane(
                value, combined_plan, source, tuple(combined_demands)
            )
            # Bearing remains the existing per-physical-hole check exactly once.
            checks.extend(c for c in combined.checks if not c.check_id.startswith("PIN_BEARING:"))
            if combined.reasons:
                unresolved.setdefault(owner, set()).update(combined.reasons)
                unresolved[owner].add("DCTN_SHARED_CHORD_CROSS_GROUP_PATH_NOT_QUALIFIED")
        for owner, requirements in unresolved.items():
            owner_member = next((m for m in value.members if m.slot == owner), None)
            reference = (
                value.shared_channel_source_reference
                if owner_member is None
                else owner_member.local_path_source_reference
            )
            qualified = mechanism_checks(
                registry,
                reference,
                owner,
                dctn_mechanism_binding(preview, owner),
                frozenset(requirements),
            )
            if qualified is None:
                blockers.extend(owner + ":" + reason for reason in sorted(requirements))
            else:
                checks.extend(qualified)
    identities = tuple(c.check_id for c in checks)
    if len(set(identities)) != len(identities):
        raise ValueError("DCTN required native/source checks cannot duplicate a physical check")
    unique = tuple(dict.fromkeys(blockers))
    status = aggregate_dctn_checks(tuple(checks), unique)
    governing = tuple(c.check_id for c in checks if c.status == "FAIL")
    return DCTNDesign(
        preview,
        tuple(checks),
        unique,
        governing,
        status,
        dctn_fingerprint((preview.fingerprint, checks, unique, status)),
    )
