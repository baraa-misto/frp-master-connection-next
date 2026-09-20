"""Explicit design dispatch; qualified sharing precedes every local resistance call."""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.application.angle_column_base_local import member_local_checks
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    AngleBaseTransfer,
    preview_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_qualification import (
    BaseMemberResponseValidation,
    column_zone_binding,
    connector_context,
    fastener_binding,
    find_member_response,
)
from frp_master_connection.application.angle_column_base_sources import (
    EMPTY_SOURCES,
    ZONE_COVERAGE,
    AngleBaseSourceRegistry,
    QualifiedColumnBaseZone,
)
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.application.wi_frp_support_moment_design import SupportBoltCheck
from frp_master_connection.application.wi_wall_moment_design import aggregate_internal_status
from frp_master_connection.application.wi_wall_moment_sources import (
    ATTACHMENT_COVERAGE,
    WallMomentAttachmentResult,
)
from frp_master_connection.calculation.angle_column_base_response import base_fingerprint, is_zero
from frp_master_connection.calculation.angle_connector_providers import (
    AngleProviderResult,
    evaluate_angle_provider,
)
from frp_master_connection.calculation.equations import (
    bolt_shear_resistance_from_nominal_stress,
    bolt_tension_resistance,
)
from frp_master_connection.calculation.frp_angle_connector_provider import (
    REVIEW_PASS,
    QualifiedBodyCheck,
    _body,
    frp_source_binding,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckResult,
    _governing_result_ids,
)
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    compare_resistance,
)
from frp_master_connection.calculation.quantities import Dimension
from frp_master_connection.calculation.results import NumericalComparison
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from frp_master_connection.calculation.support_attachment_response import qualified_source
from frp_master_connection.domain.angle_column_moment_base import (
    CONNECTORS,
    AngleColumnMomentBaseRequest,
)


@dataclass(frozen=True, slots=True)
class BaseZoneResult:
    status: str
    reasons: tuple[str, ...]
    required_coverage: tuple[str, ...]
    exact_binding: str
    source: QualifiedColumnBaseZone | None
    comparisons: tuple[ResistanceComparison, ...]


@dataclass(frozen=True, slots=True)
class AngleBaseDesign:
    preview: AngleBasePreview
    status: str
    status_reason: str
    connector_results: tuple[AngleProviderResult, ...]
    member_attachment_results: tuple[WallMomentAttachmentResult, ...]
    member_responses: tuple[BaseMemberResponseValidation, ...]
    member_bolts: tuple[SupportBoltCheck, ...]
    local_checks: tuple[SupportLocalCheck, ...]
    local_zone: BaseZoneResult | None
    native_governing_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    missing_sources: tuple[str, ...]
    scope_statuses: tuple[tuple[str, str], ...]
    result_fingerprint: str
    resistance_evaluated: bool
    ordinary_whole_connection_pass_allowed: bool = False


def _connector(
    preview: AngleBasePreview, transfer: AngleBaseTransfer, sources: AngleBaseSourceRegistry
) -> tuple[AngleProviderResult, WallMomentAttachmentResult]:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    spec = preview.input.connectors[index].angle
    context = connector_context(preview, transfer)
    record = sources.connector_sources.find(spec.connector_source_reference, transfer.connector_id)
    if record is not None:
        context = replace(context, qualified_source=record.package)
    body = evaluate_angle_provider(transfer.core, "FRP", context)
    ctx = connector_context(preview, transfer, attachment=True)
    attachment = sources.connector_sources.find(
        spec.attachment_source_reference, transfer.connector_id, attachment=True
    )
    coverage = () if attachment is None else attachment.attachment_coverage
    if attachment is not None and set(coverage) != set(ATTACHMENT_COVERAGE):
        check = QualifiedBodyCheck("NOT_EVALUATED_QUALIFIED_ATTACHMENT_COVERAGE_MISSING")
    else:
        if attachment is not None:
            ctx = replace(ctx, qualified_source=attachment.package)
        check = _body(replace(transfer.core, heel=transfer.core.request.member_action), ctx)
    result = WallMomentAttachmentResult(
        transfer.connector_id,
        frp_source_binding(transfer.core, ctx),
        spec.attachment_source_reference,
        None if attachment is None else attachment.package.source.revision,
        coverage,
        check,
        base_fingerprint((transfer.core.fingerprint, ctx, attachment, check)),
    )
    return body, result


def _bolt_checks(
    preview: AngleBasePreview,
    transfer: AngleBaseTransfer,
    response: BaseMemberResponseValidation,
    sources: AngleBaseSourceRegistry,
) -> tuple[SupportBoltCheck, ...]:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    item = preview.input.connectors[index]
    binding = fastener_binding(preview, transfer)
    source = next(
        (s for s in sources.fasteners if s.reference == item.fastener_source_reference), None
    )
    applicable = (
        source is not None
        and qualified_source(source.source)
        and source.exact_fastener_and_grip_binding == binding
        and source.condition == item.angle.fastener.thread_condition
        and "SINGLE_PLANE_8_2_8_3" in source.authorized_section_methods
        and all(
            p.dimension is Dimension.STRESS and p.canonical_magnitude > 0
            for p in (source.nominal_shear_stress, source.nominal_tensile_stress)
        )
    )
    shafts = {s.bolt_id: s for s in response.shafts}
    native = {
        f"{transfer.connector_id}:{b.bolt_id}": b
        for b in transfer.in_plane_demand.solution.projected_bolts()
    }
    values = []
    for physical in response.binding.physical_bolts:
        demand = shafts.get(physical.bolt_id)
        if demand is None or not applicable or source is None:
            values.append(
                SupportBoltCheck(
                    f"MEMBER_BOLT:{physical.bolt_id}",
                    transfer.connector_id,
                    physical.bolt_id,
                    "UNRESOLVED" if demand is None else demand.section_id,
                    physical.layer_ids,
                    "SOURCE_REQUIRED",
                    "COMPLETE_NORMAL_RESPONSE_REQUIRED"
                    if demand is None
                    else "CONTROLLED_NOMINAL_BOLT_STRENGTH_GRADE_THREAD_GRIP_REQUIRED",
                    None if demand is None else (demand.force_u, demand.force_v),
                    None if demand is None else native[physical.bolt_id].total_force_magnitude,
                    None if demand is None else demand.tensile_demand,
                    source=source,
                    response_fingerprint=response.fingerprint,
                )
            )
            continue
        # Validation binds both signed components to the unchanged Slice 8
        # projection. Consume its magnitude too, without another sqrt/context.
        shear = native[physical.bolt_id].total_force_magnitude
        diameter = item.angle.fastener.bolt_diameter
        st = bolt_shear_resistance_from_nominal_stress(diameter, source.nominal_shear_stress)
        tt = bolt_tension_resistance(diameter, source.nominal_tensile_stress)
        combined = sourced_combined_bolt_resistance(
            diameter, source.nominal_tensile_stress, source.nominal_shear_stress, shear
        )
        comparisons: tuple[ResistanceComparison, ...] = (
            compare_resistance(shear, st.design_resistance),
            compare_resistance(demand.tensile_demand, tt.design_resistance),
        )
        if combined.design_tensile_resistance.canonical_magnitude > 0:
            comparisons += (
                compare_resistance(demand.tensile_demand, combined.design_tensile_resistance),
            )
        failed = (
            any(c.numerical_comparison is NumericalComparison.FAIL for c in comparisons)
            or combined.design_tensile_resistance.canonical_magnitude < 0
            or (
                combined.design_tensile_resistance.canonical_magnitude == 0
                and demand.tensile_demand.canonical_magnitude > 0
            )
        )
        values.append(
            SupportBoltCheck(
                f"MEMBER_BOLT:{physical.bolt_id}:{demand.section_id}",
                transfer.connector_id,
                physical.bolt_id,
                demand.section_id,
                demand.layer_ids,
                "FAIL" if failed else "PASS",
                "NATIVE_ACTUAL_SINGLE_INTERFACE_SOURCE_BOUND_STRENGTH",
                (demand.force_u, demand.force_v),
                shear,
                demand.tensile_demand,
                st,
                tt,
                combined,
                comparisons,
                source,
                response.fingerprint,
            )
        )
    return tuple(values)


def evaluate_column_zone(
    preview: AngleBasePreview,
    sources: AngleBaseSourceRegistry,
    checks: tuple[SupportLocalCheck, ...],
) -> BaseZoneResult:
    required = (
        *ZONE_COVERAGE,
        *(
            f"LOCAL_CHECK:{c.check_id}"
            for c in checks
            if c.status == "SOURCE_REQUIRED" or "NOT_EVALUATED" in c.status
        ),
    )
    binding = column_zone_binding(preview)
    source = next(
        (s for s in sources.zones if s.reference == preview.input.column_zone_source_reference),
        None,
    )
    reasons = []
    if source is None:
        return BaseZoneResult(
            "SOURCE_REQUIRED",
            ("QUALIFIED_COMMON_TWO_LEG_COLUMN_END_ZONE_REQUIRED",),
            required,
            binding,
            None,
            (),
        )
    if (
        not qualified_source(source.source)
        or source.exact_binding != binding
        or not source.applicability.strip()
    ):
        reasons.append("COLUMN_END_ZONE_SOURCE_DOMAIN_NOT_APPLICABLE")
    checked = {c for check in source.checks for c in check.coverage}
    if (
        not set(required).issubset(source.coverage)
        or not set(required).issubset(checked)
        or not source.checks
    ):
        reasons.append("COLUMN_END_ZONE_REQUIRED_COVERAGE_MISSING")
    ids = [c.check_id for c in source.checks]
    if len(ids) != len(set(ids)):
        reasons.append("COLUMN_END_ZONE_DUPLICATE_CHECK")
    if any(
        not c.method.strip()
        or not c.source_locator.strip()
        or c.demand.dimension is not c.design_capacity.dimension
        or c.demand.canonical_magnitude < 0
        or c.design_capacity.canonical_magnitude <= 0
        for c in source.checks
    ):
        reasons.append("COLUMN_END_ZONE_QUALIFIED_CHECK_INVALID")
    comparisons = (
        ()
        if reasons
        else tuple(compare_resistance(c.demand, c.design_capacity) for c in source.checks)
    )
    status = (
        "SOURCE_REQUIRED"
        if reasons
        else "FAIL"
        if any(c.numerical_comparison is NumericalComparison.FAIL for c in comparisons)
        else REVIEW_PASS
    )
    return BaseZoneResult(status, tuple(reasons), required, binding, source, comparisons)


def evaluate_angle_column_moment_base(
    request: AngleColumnMomentBaseRequest, sources: AngleBaseSourceRegistry = EMPTY_SOURCES
) -> AngleBaseDesign:
    preview = preview_angle_column_moment_base(request, sources)
    bodies = []
    attachments = []
    responses = []
    bolts: list[SupportBoltCheck] = []
    local: list[SupportLocalCheck] = []
    scopes = [
        ("GEOMETRY", preview.geometry.status),
        ("REQUIRED_TOTAL_FOUNDATION_ACTION", "CALCULATED_EXACT"),
        ("COMPLETE_BASE_RESPONSE", preview.branch_allocation_status),
    ]
    missing = []
    failed = []
    zone = None
    statuses = []
    zero = (
        is_zero(preview.column_on_base)
        and preview.branch_allocation_status == "NOT_REQUIRED_ZERO_DEMAND"
    )
    if preview.geometry.status != "VALID":
        status, reason = "INVALID_GEOMETRY", "INVALID_PHYSICAL_GEOMETRY_FAIL_CLOSED"
    elif not preview.transfers:
        status = preview.branch_allocation_status
        reason = "NO_RESISTANCE_ON_UNRESOLVED_BRANCH_DEMAND"
        missing = [
            "COMPLETE_BASE_RESPONSE",
            *(f"{identity}:MEMBER_AND_BODY_DEMAND" for identity in CONNECTORS),
        ]
    elif zero:
        status, reason = "NOT_REQUIRED_ZERO_DEMAND", "ZERO_NO_PRELOAD_IS_NOT_A_CAPACITY_CERTIFICATE"
    else:
        for t in preview.transfers:
            body, attachment = _connector(preview, t, sources)
            response = find_member_response(preview, t, sources)
            body_status = body.status
            bodies.append(body)
            attachments.append(attachment)
            responses.append(response)
            member_bolts = _bolt_checks(preview, t, response, sources)
            checks = member_local_checks(preview, t, response)
            bolts.extend(member_bolts)
            local.extend(checks)
            for name, state in (
                ("BODY", body_status),
                ("MEMBER_ATTACHMENT", attachment.check.status),
                ("MEMBER_NORMAL_RESPONSE", response.status),
            ):
                scopes.append((f"{t.connector_id}:{name}", state))
                statuses.append(state)
                if state == "FAIL":
                    failed.append(f"{t.connector_id}:{name}")
                if "SOURCE" in state or "NOT_EVALUATED" in state:
                    missing.append(f"{t.connector_id}:{name}:{state}")
            statuses.extend(b.status for b in member_bolts)
            statuses.extend(c.status for c in checks if c.status != "SOURCE_REQUIRED")
            failed.extend(b.check_id for b in member_bolts if b.status == "FAIL")
            failed.extend(c.check_id for c in checks if c.status == "FAIL")
            missing.extend(b.check_id for b in member_bolts if b.status == "SOURCE_REQUIRED")
        zone = evaluate_column_zone(preview, sources, tuple(local))
        statuses.append(zone.status)
        scopes.append(("COMMON_COLUMN_END_ZONE", zone.status))
        if zone.status == "SOURCE_REQUIRED":
            missing.extend(c.check_id for c in local if c.status == "SOURCE_REQUIRED")
            missing.append("COMMON_COLUMN_END_ZONE")
        if zone.status == "FAIL":
            failed.append("COMMON_COLUMN_END_ZONE")
        status, reason = aggregate_internal_status(tuple(statuses))
    scopes.extend(
        (f"{b.domain.connector_id}:FOUNDATION_BREAKDOWN", b.status)
        for b in preview.foundation_breakdowns
    )
    scopes.extend(
        (
            ("FOUNDATION_ANCHOR_CONCRETE", preview.foundation_strength_status),
            ("OVERALL_COLUMN", preview.overall_column_status),
            ("CLASSIFICATION", preview.classification_status),
        )
    )
    native = tuple(c.native_trace for c in local if isinstance(c.native_trace, MultiRowCheckResult))
    governing = _governing_result_ids(native)
    fingerprint = base_fingerprint(
        (
            preview.engineering_fingerprint,
            status,
            reason,
            tuple(bodies),
            tuple(attachments),
            tuple(responses),
            tuple(bolts),
            tuple(local),
            zone,
            governing,
            tuple(failed),
            tuple(missing),
            tuple(scopes),
        )
    )
    return AngleBaseDesign(
        preview,
        status,
        reason,
        tuple(bodies),
        tuple(attachments),
        tuple(responses),
        tuple(bolts),
        tuple(local),
        zone,
        governing,
        tuple(failed),
        tuple(missing),
        tuple(scopes),
        fingerprint,
        bool(bodies),
    )
