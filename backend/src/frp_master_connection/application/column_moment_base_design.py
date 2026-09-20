"""Explicit Stage 4.5 native/provider design. Never called during preview."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import cast

from frp_master_connection.application.column_moment_base_local import member_local_checks
from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    ColumnMomentTransfer,
    preview_column_moment_base,
)
from frp_master_connection.application.column_moment_base_qualification import (
    column_zone_binding,
    connector_context,
    fastener_binding,
)
from frp_master_connection.application.column_moment_base_sources import (
    EMPTY_SOURCES,
    PROFILE_ZONE_COVERAGE,
    ZONE_COVERAGE,
    ColumnMomentSourceRegistry,
    QualifiedColumnMomentZone,
)
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.application.wi_frp_support_moment_design import SupportBoltCheck
from frp_master_connection.application.wi_wall_moment_design import aggregate_internal_status
from frp_master_connection.application.wi_wall_moment_sources import (
    ATTACHMENT_COVERAGE,
    WallMomentAttachmentResult,
)
from frp_master_connection.calculation.angle_column_base_response import base_fingerprint, is_zero
from frp_master_connection.calculation.angle_connector_core import components, exact_decimal
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
from frp_master_connection.calculation.in_plane_wrench_demand import project_rational
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    compare_resistance,
)
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.results import NumericalComparison
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from frp_master_connection.calculation.support_attachment_response import qualified_source
from frp_master_connection.domain.column_moment_base import ColumnMomentBaseRequest, Face


@dataclass(frozen=True, slots=True)
class ColumnMomentZoneResult:
    status: str
    reasons: tuple[str, ...]
    required_coverage: tuple[str, ...]
    exact_binding: str
    source: QualifiedColumnMomentZone | None
    comparisons: tuple[ResistanceComparison, ...]


@dataclass(frozen=True, slots=True)
class ColumnMomentDesign:
    preview: ColumnMomentPreview
    status: str
    status_reason: str
    connector_results: tuple[AngleProviderResult, ...]
    member_attachment_results: tuple[WallMomentAttachmentResult, ...]
    member_bolts: tuple[SupportBoltCheck, ...]
    local_checks: tuple[SupportLocalCheck, ...]
    local_zone: ColumnMomentZoneResult | None
    failed_check_ids: tuple[str, ...]
    missing_sources: tuple[str, ...]
    scope_statuses: tuple[tuple[str, str], ...]
    result_fingerprint: str
    resistance_evaluated: bool
    ordinary_whole_connection_pass_allowed: bool = False


def _connector(
    preview: ColumnMomentPreview,
    transfer: ColumnMomentTransfer,
    sources: ColumnMomentSourceRegistry,
) -> tuple[AngleProviderResult, WallMomentAttachmentResult]:
    spec = preview.input.physical_connector(cast(Face, transfer.connector_id)).angle
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
    return body, WallMomentAttachmentResult(
        transfer.connector_id,
        frp_source_binding(transfer.core, ctx),
        spec.attachment_source_reference,
        None if attachment is None else attachment.package.source.revision,
        coverage,
        check,
        base_fingerprint((transfer.core.fingerprint, ctx, attachment, check)),
    )


def physical_bolt_checks(
    preview: ColumnMomentPreview, sources: ColumnMomentSourceRegistry
) -> tuple[SupportBoltCheck, ...]:
    record = preview.response.response
    if record is None:
        return ()
    result = []
    domains = {b.bolt_id: b for b in preview.response_binding.physical_bolts}
    for bolt in record.bolts:
        domain = domains[bolt.bolt_id]
        owner = cast(Face, domain.owner_connector)
        item = preview.input.physical_connector(owner)
        source = next(
            (s for s in sources.fasteners if s.reference == item.fastener_source_reference), None
        )
        applicable = (
            source is not None
            and qualified_source(source.source)
            and source.exact_fastener_and_grip_binding == fastener_binding(preview, owner)
            and source.condition == item.angle.fastener.thread_condition
            and all(
                p.dimension is Dimension.STRESS and p.canonical_magnitude > 0
                for p in (source.nominal_shear_stress, source.nominal_tensile_stress)
            )
        )
        for section in bolt.sections:
            f = components(section.force_on_upstream)
            u = sum((x * y for x, y in zip(f, domain.plane_u_global, strict=True)), Fraction(0))
            v = sum((x * y for x, y in zip(f, domain.plane_v_global, strict=True)), Fraction(0))
            signed = (
                PhysicalQuantity(exact_decimal(u), Unit.N),
                PhysicalQuantity(exact_decimal(v), Unit.N),
            )
            # This is a source's exact section vector, not reconstructed output
            # of an inherited engine. Use the existing rational Decimal-80 projection.
            shear = PhysicalQuantity(
                project_rational(Fraction(u * u + v * v), square_root=True), Unit.N
            )
            if (
                not applicable
                or source is None
                or section.native_capacity_applicability not in source.authorized_section_methods
            ):
                result.append(
                    SupportBoltCheck(
                        "MEMBER_BOLT:" + bolt.bolt_id + ":" + section.section_id,
                        owner,
                        bolt.bolt_id,
                        section.section_id,
                        tuple(layer_item.layer_id for layer_item in domain.layers),
                        "SOURCE_REQUIRED",
                        "CONTROLLED_NOMINAL_BOLT_GRADE_THREAD_GRIP_AND_SECTION_AUTHORITY_REQUIRED",
                        signed,
                        shear,
                        section.tensile_demand,
                        source=source,
                        response_fingerprint=preview.response.fingerprint,
                    )
                )
                continue
            # One capacity per actual cut, never multiply because several layers exist.
            st = bolt_shear_resistance_from_nominal_stress(
                item.angle.fastener.bolt_diameter, source.nominal_shear_stress
            )
            tt = bolt_tension_resistance(
                item.angle.fastener.bolt_diameter, source.nominal_tensile_stress
            )
            interaction = sourced_combined_bolt_resistance(
                item.angle.fastener.bolt_diameter,
                source.nominal_tensile_stress,
                source.nominal_shear_stress,
                shear,
            )
            comparisons: tuple[ResistanceComparison, ...] = (
                compare_resistance(shear, st.design_resistance),
                compare_resistance(section.tensile_demand, tt.design_resistance),
            )
            if interaction.design_tensile_resistance.canonical_magnitude > 0:
                comparisons += (
                    compare_resistance(
                        section.tensile_demand, interaction.design_tensile_resistance
                    ),
                )
            failed = (
                any(c.numerical_comparison is NumericalComparison.FAIL for c in comparisons)
                or interaction.design_tensile_resistance.canonical_magnitude < 0
                or (
                    interaction.design_tensile_resistance.canonical_magnitude == 0
                    and section.tensile_demand.canonical_magnitude > 0
                )
            )
            result.append(
                SupportBoltCheck(
                    "MEMBER_BOLT:" + bolt.bolt_id + ":" + section.section_id,
                    owner,
                    bolt.bolt_id,
                    section.section_id,
                    tuple(layer_item.layer_id for layer_item in domain.layers),
                    "FAIL" if failed else "PASS",
                    "NATIVE_ACTUAL_SOURCE_BOUND_SHAFT_SECTION_NOT_MULTIPLIED",
                    signed,
                    shear,
                    section.tensile_demand,
                    st,
                    tt,
                    interaction,
                    comparisons,
                    source,
                    preview.response.fingerprint,
                )
            )
    return tuple(result)


def evaluate_column_zone(
    preview: ColumnMomentPreview,
    sources: ColumnMomentSourceRegistry,
    checks: tuple[SupportLocalCheck, ...],
) -> ColumnMomentZoneResult:
    required = (
        *ZONE_COVERAGE,
        *PROFILE_ZONE_COVERAGE[preview.input.column.family],
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
    if source is None:
        return ColumnMomentZoneResult(
            "SOURCE_REQUIRED",
            ("QUALIFIED_COMMON_COLUMN_END_ZONE_REQUIRED",),
            required,
            binding,
            None,
            (),
        )
    reasons = []
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
    return ColumnMomentZoneResult(status, tuple(reasons), required, binding, source, comparisons)


def evaluate_column_moment_base(
    request: ColumnMomentBaseRequest, sources: ColumnMomentSourceRegistry = EMPTY_SOURCES
) -> ColumnMomentDesign:
    preview = preview_column_moment_base(request, sources)
    bodies = []
    attachments = []
    bolts: tuple[SupportBoltCheck, ...] = ()
    local: tuple[SupportLocalCheck, ...] = ()
    zone = None
    failed = []
    missing = []
    scopes = [
        ("GEOMETRY", preview.geometry.status),
        ("REQUIRED_TOTAL_FOUNDATION_ACTION", "CALCULATED_EXACT"),
        ("COMPLETE_BASE_RESPONSE", preview.branch_allocation_status),
    ]
    if preview.geometry.status != "VALID":
        status, reason = "INVALID_GEOMETRY", "INVALID_PHYSICAL_GEOMETRY_FAIL_CLOSED"
    elif not preview.transfers:
        status, reason = (
            preview.branch_allocation_status,
            "NO_RESISTANCE_ON_UNRESOLVED_BRANCH_DEMAND",
        )
        missing = [
            "COMPLETE_BASE_RESPONSE",
            *(f"{f}:MEMBER_AND_BODY_DEMAND" for f in request.active_faces),
        ]
    elif (
        is_zero(preview.column_on_base)
        and preview.branch_allocation_status == "NOT_REQUIRED_ZERO_DEMAND"
    ):
        status, reason = "NOT_REQUIRED_ZERO_DEMAND", "ZERO_NO_PRELOAD_IS_NOT_A_CAPACITY_CERTIFICATE"
    else:
        statuses = []
        for transfer in preview.transfers:
            body, attachment = _connector(preview, transfer, sources)
            bodies.append(body)
            attachments.append(attachment)
            for name, state in (
                ("BODY", body.status),
                ("MEMBER_ATTACHMENT", attachment.check.status),
            ):
                scopes.append((transfer.connector_id + ":" + name, state))
                statuses.append(state)
                if state == "FAIL":
                    failed.append(transfer.connector_id + ":" + name)
                if state != REVIEW_PASS and ("SOURCE" in state or "NOT_EVALUATED" in state):
                    missing.append(transfer.connector_id + ":" + name + ":" + state)
        bolts = physical_bolt_checks(preview, sources)
        local = member_local_checks(preview)
        statuses.extend(b.status for b in bolts)
        statuses.extend(c.status for c in local if c.status != "SOURCE_REQUIRED")
        failed.extend(b.check_id for b in bolts if b.status == "FAIL")
        failed.extend(c.check_id for c in local if c.status == "FAIL")
        missing.extend(b.check_id for b in bolts if b.status == "SOURCE_REQUIRED")
        zone = evaluate_column_zone(preview, sources, local)
        statuses.append(zone.status)
        scopes.append(("COMMON_COLUMN_END_ZONE", zone.status))
        if zone.status == "SOURCE_REQUIRED":
            missing.extend(c.check_id for c in local if c.status == "SOURCE_REQUIRED")
            missing.append("COMMON_COLUMN_END_ZONE")
        if zone.status == "FAIL":
            failed.append("COMMON_COLUMN_END_ZONE")
        status, reason = aggregate_internal_status(tuple(statuses))
    scopes.extend(
        (b.domain.connector_id + ":FOUNDATION_BREAKDOWN", b.status)
        for b in preview.foundation_breakdowns
    )
    scopes.extend(
        (
            ("FOUNDATION_ANCHOR_CONCRETE", preview.foundation_strength_status),
            ("OVERALL_COLUMN", preview.overall_column_status),
            ("CLASSIFICATION", preview.classification_status),
        )
    )
    fingerprint = base_fingerprint(
        (
            preview.engineering_fingerprint,
            status,
            reason,
            tuple(bodies),
            tuple(attachments),
            bolts,
            local,
            zone,
            tuple(failed),
            tuple(missing),
            tuple(scopes),
        )
    )
    return ColumnMomentDesign(
        preview,
        status,
        reason,
        tuple(bodies),
        tuple(attachments),
        bolts,
        local,
        zone,
        tuple(failed),
        tuple(missing),
        tuple(scopes),
        fingerprint,
        bool(bodies),
    )
