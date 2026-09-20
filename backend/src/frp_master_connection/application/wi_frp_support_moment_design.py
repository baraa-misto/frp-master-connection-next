"""Explicit Stage 4.3 design execution and failure/completeness trace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from frp_master_connection.application.wi_frp_support_local_checks import (
    SupportLocalCheck,
    bearing_and_pull_through,
    magnitude,
    support_group_paths,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    FRPSupportMomentPreview,
    SupportTransfer,
    beam_native_input,
    preview_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_sources import (
    EMPTY_SOURCES,
    SHARED_ZONE_REQUIREMENTS,
    ZONE_REQUIREMENTS,
    FRPSupportSourceRegistry,
    QualifiedLocalSupportZone,
    SupportFastenerSource,
    evaluate_frp_support_connector_sources,
    fastener_binding,
    local_zone_binding,
    response_binding,
)
from frp_master_connection.application.wi_wall_moment_design import (
    WallMomentBearing,
    WallMomentLocalChecks,
    _common_bolts,
    _flange_local,
    _nonstandard_flange_bearings,
    _source_missing,
    _web_bearings,
    _web_group_checks,
    aggregate_internal_status,
)
from frp_master_connection.application.wi_wall_moment_orchestration import (
    WallMomentConnectorResult,
    WIWallMomentPreview,
)
from frp_master_connection.application.wi_wall_moment_sources import WallMomentAttachmentResult
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.angle_connector_providers import AngleProviderResult
from frp_master_connection.calculation.equations import (
    BoltResistanceTrace,
    CombinedBoltTrace,
    bolt_shear_resistance_from_nominal_stress,
    bolt_tension_resistance,
)
from frp_master_connection.calculation.frp_angle_connector_provider import REVIEW_PASS
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckResult,
    _governing_result_ids,
)
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    compare_resistance,
)
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity
from frp_master_connection.calculation.results import NumericalComparison
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from frp_master_connection.calculation.support_attachment_response import (
    ShaftDemand,
    ValidatedSupportResponse,
    qualified_source,
    validate_support_response,
)
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    AsymmetricTwoPlaneBoltResult,
)
from frp_master_connection.domain.wi_frp_support_moment import (
    WIFrpSupportMomentRequest,
)


@dataclass(frozen=True, slots=True)
class SupportBoltCheck:
    check_id: str
    connector_id: str
    bolt_id: str
    section_id: str
    layer_ids: tuple[str, ...]
    status: str
    reason: str
    signed_shear: tuple[PhysicalQuantity, PhysicalQuantity] | None
    shear_magnitude: PhysicalQuantity | None
    total_tension_including_prying: PhysicalQuantity | None
    shear_trace: BoltResistanceTrace | None = None
    tension_trace: BoltResistanceTrace | None = None
    combined_trace: CombinedBoltTrace | None = None
    comparisons: tuple[ResistanceComparison, ...] = ()
    source: SupportFastenerSource | None = None
    response_fingerprint: str | None = None
    method: str = "ASCE_74_23_8_2_8_3_ACTUAL_SOURCE_BOUND_SECTION"
    prying_added_again: bool = False


@dataclass(frozen=True, slots=True)
class LocalZoneResult:
    status: str
    reasons: tuple[str, ...]
    required_coverage: tuple[str, ...]
    source: QualifiedLocalSupportZone | None
    comparisons: tuple[ResistanceComparison, ...]
    exact_binding: str
    overall_member_design: str = "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"


@dataclass(frozen=True, slots=True)
class FRPSupportMomentDesign:
    preview: FRPSupportMomentPreview
    status: str
    status_reason: str
    connector_results: tuple[AngleProviderResult, ...]
    attachment_results: tuple[WallMomentAttachmentResult, ...]
    beam_local_checks: tuple[WallMomentLocalChecks, ...]
    beam_bearings: tuple[WallMomentBearing, ...]
    common_web_bolts: tuple[AsymmetricTwoPlaneBoltResult, ...]
    support_response: ValidatedSupportResponse | None
    support_bolts: tuple[SupportBoltCheck, ...]
    support_local_checks: tuple[SupportLocalCheck, ...]
    local_zone: LocalZoneResult | None
    native_failed_checks: tuple[MultiRowCheckResult, ...]
    native_governing_check_ids: tuple[str, ...]
    missing_sources: tuple[str, ...]
    scope_statuses: tuple[tuple[str, str], ...]
    result_fingerprint: str
    resistance_evaluated: bool
    complete_unqualified_pass_allowed: bool = False


def _native_transfer(t: SupportTransfer) -> WallMomentConnectorResult:
    return WallMomentConnectorResult(
        t.connector_id,
        t.slice5_region,
        t.share,
        t.core,
        t.flange_demand,
        t.web_demand,
        t.support_lvt,
        t.support_at_centroid,
        cast(
            tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
            t.member_out_of_plane_f_c_m_a_m_b,
        ),
        "NOT_REQUIRED_ZERO_SHEAR"
        if t.core.heel.force.x.canonical_magnitude == 0
        else "ASCE_8_15_DIRECT_INSTEP_SHEAR_REQUIRED",
    )


def _bolt_check(
    preview: FRPSupportMomentPreview,
    connector: str,
    bolt_id: str,
    demand: ShaftDemand | None,
    response: ValidatedSupportResponse,
    registry: FRPSupportSourceRegistry,
) -> SupportBoltCheck:
    prefix = f"SUPPORT_BOLT:{bolt_id}"
    if demand is None or response.status != "VALID_QUALIFIED_RESPONSE":
        return SupportBoltCheck(
            prefix,
            connector,
            bolt_id,
            "UNRESOLVED",
            (),
            "SOURCE_REQUIRED",
            "COMPLETE_NORMAL_CONTACT_SECTION_RESPONSE_UNAVAILABLE_NOT_ZERO",
            None,
            None,
            None,
            response_fingerprint=response.fingerprint,
        )
    spec = preview.input.angles[
        next(i for i, t in enumerate(preview.connectors) if t.connector_id == connector)
    ]
    binding = fastener_binding(preview, connector)
    source = next(
        (
            s
            for s in registry.fasteners
            if s.reference == spec.support_fastener.source_authority_id
            and s.exact_fastener_and_grip_binding == binding
        ),
        None,
    )
    shear = magnitude(demand.force_u, demand.force_v)
    reason = "SOURCE_REQUIRED_BOLT_NOMINAL_STRENGTH_GRADE_CONDITION_AND_GRIP"
    applicable = (
        source is not None
        and qualified_source(source.source)
        and source.condition == spec.support_fastener.thread_condition
    )
    if applicable and source is not None:
        applicable = all(
            q.dimension is Dimension.STRESS and q.canonical_magnitude > 0
            for q in (source.nominal_tensile_stress, source.nominal_shear_stress)
        )
    if applicable and source is not None:
        applicable = (
            demand.applicability == "SINGLE_PLANE_8_2_8_3"
            and demand.applicability in source.authorized_section_methods
            and demand.secondary_bending_covered
        )
        reason = "SOURCE_REQUIRED_ACTUAL_MULTI_PLANE_OR_LONG_SHAFT_INTERACTION_BENDING_METHOD"
    if not applicable or source is None:
        return SupportBoltCheck(
            f"{prefix}:{demand.section_id}",
            connector,
            bolt_id,
            demand.section_id,
            demand.layer_ids,
            "SOURCE_REQUIRED",
            reason,
            (demand.force_u, demand.force_v),
            shear,
            demand.tensile_demand,
            source=source,
            response_fingerprint=response.fingerprint,
        )
    f = spec.support_fastener
    shear_trace = bolt_shear_resistance_from_nominal_stress(
        f.bolt_diameter, source.nominal_shear_stress
    )
    tension_trace = bolt_tension_resistance(f.bolt_diameter, source.nominal_tensile_stress)
    combined = sourced_combined_bolt_resistance(
        f.bolt_diameter, source.nominal_tensile_stress, source.nominal_shear_stress, shear
    )
    # Negative modified tensile resistance is not clamped. Shear exceedance or
    # negative Eq.8-3 branch is a direct failure, never a zero-strength PASS.
    comparisons: tuple[ResistanceComparison, ...] = (
        compare_resistance(shear, shear_trace.design_resistance),
        compare_resistance(demand.tensile_demand, tension_trace.design_resistance),
    )
    if combined.design_tensile_resistance.canonical_magnitude > 0:
        comparisons += (
            compare_resistance(demand.tensile_demand, combined.design_tensile_resistance),
        )
    failed = combined.design_tensile_resistance.canonical_magnitude < 0 or any(
        c.numerical_comparison is NumericalComparison.FAIL for c in comparisons
    )
    if (
        combined.design_tensile_resistance.canonical_magnitude == 0
        and demand.tensile_demand.canonical_magnitude > 0
    ):
        failed = True
    return SupportBoltCheck(
        f"{prefix}:{demand.section_id}",
        connector,
        bolt_id,
        demand.section_id,
        demand.layer_ids,
        "FAIL" if failed else "PASS",
        "NATIVE_STRENGTH_AND_SOURCE_BOUND_ACTUAL_SECTION_ONLY",
        (demand.force_u, demand.force_v),
        shear,
        demand.tensile_demand,
        shear_trace,
        tension_trace,
        combined,
        comparisons,
        source,
        response.fingerprint,
    )


def evaluate_local_zone(
    preview: FRPSupportMomentPreview,
    registry: FRPSupportSourceRegistry,
    local_checks: tuple[SupportLocalCheck, ...] = (),
) -> LocalZoneResult:
    required = (
        ZONE_REQUIREMENTS[preview.input.support.mode]
        + SHARED_ZONE_REQUIREMENTS
        + tuple(
            f"LOCAL_CHECK:{c.check_id}"
            for c in local_checks
            if _source_missing(c.status) or "NOT_EVALUATED" in c.status
        )
    )
    binding = local_zone_binding(preview)
    source = next(
        (
            s
            for s in registry.local_zones
            if s.reference == preview.input.local_zone_source_reference
        ),
        None,
    )
    reasons = []
    comparisons = []
    if source is None:
        reasons.append("SOURCE_REQUIRED_QUALIFIED_LOCAL_SUPPORT_ASSEMBLY_CAPACITY")
    elif (
        source.exact_binding != binding
        or source.support_mode is not preview.input.support.mode
        or not qualified_source(source.source)
        or not source.issuer.strip()
        or not source.contact_stiffness_boundary_domain
    ):
        reasons.append("SOURCE_REQUIRED_LOCAL_ZONE_EXACT_BINDING_QUALIFICATION_AND_DOMAIN")
    else:
        coverage = {c for check in source.checks for c in check.coverage}
        if not set(required).issubset(coverage):
            reasons.append("SOURCE_REQUIRED_LOCAL_ZONE_COMPLETE_INTERACTION_COVERAGE")
        ids = tuple(c.check_id for c in source.checks)
        if len(ids) != len(set(ids)):
            reasons.append("NOT_EVALUATED_DUPLICATE_LOCAL_ZONE_CHECK")
        for check in source.checks:
            if (
                check.demand.dimension is not Dimension.FORCE
                or check.design_capacity.dimension is not Dimension.FORCE
                or check.demand.canonical_magnitude < 0
                or check.design_capacity.canonical_magnitude <= 0
                or not check.method.strip()
                or not check.source_locator.strip()
            ):
                reasons.append("NOT_EVALUATED_LOCAL_ZONE_NATIVE_COMPARISON_CONTRACT")
            else:
                comparisons.append(compare_resistance(check.demand, check.design_capacity))
    status = (
        "FAIL"
        if any(c.numerical_comparison is NumericalComparison.FAIL for c in comparisons)
        else ("SOURCE_REQUIRED" if reasons else REVIEW_PASS)
    )
    return LocalZoneResult(status, tuple(reasons), required, source, tuple(comparisons), binding)


def evaluate_wi_frp_support_moment(
    request: WIFrpSupportMomentRequest,
    registry: FRPSupportSourceRegistry = EMPTY_SOURCES,
) -> FRPSupportMomentDesign:
    preview = preview_wi_frp_support_moment(
        request,
        registered_sources=(
            *(("COMPLETE_SUPPORT_RESPONSE", r.reference) for r in registry.responses),
            *(("LOCAL_SUPPORT_ZONE", r.reference) for r in registry.local_zones),
            *(
                (
                    f"{r.connector_id}:{'MEMBER_ATTACHMENT' if r.attachment else 'ANGLE_BODY'}",
                    r.reference,
                )
                for r in registry.connector_sources
            ),
        ),
    )
    if not preview.design_check_ready:
        return FRPSupportMomentDesign(
            preview,
            "INVALID_GEOMETRY",
            "GEOMETRY_PREVENTS_DESIGN",
            (),
            (),
            (),
            (),
            (),
            None,
            (),
            (),
            None,
            (),
            (),
            (),
            (("GEOMETRY", "INVALID_GEOMETRY"),),
            angle_fingerprint((preview.engineering_fingerprint, "INVALID_GEOMETRY")),
            False,
        )
    # Only pinned leaf check adapters are used, never the concrete orchestration
    # service. The structural view supplies just geometry.angles/member_bolts and
    # connector.core/flange_demand/web_demand consumed by these historical leaves.
    native_request = beam_native_input(request)
    native_view = cast(WIWallMomentPreview, preview)
    local = []
    providers = []
    attachments = []
    web_resolved = all(
        t.web_demand is None or t.web_demand.solution.proof is not None for t in preview.connectors
    )
    for angle, t in zip(preview.geometry.angles, preview.connectors, strict=True):
        provider, attachment = evaluate_frp_support_connector_sources(preview, t, registry)
        providers.append(provider)
        attachments.append(attachment)
        for beam in (False, True):
            if beam and angle.connector_id == "NEGATIVE_WEB_ANGLE":
                continue
            if t.web_demand is not None and t.web_demand.solution.proof is None:
                local.append(
                    WallMomentLocalChecks(
                        angle.connector_id,
                        "WI_WEB" if beam else angle.connector_id,
                        scope_status="NOT_EVALUATED_NATIVE_SLICE8_GROUP_DEMAND_UNAVAILABLE",
                    )
                )
                continue
            local.append(
                (_flange_local if t.web_demand is None else _web_group_checks)(
                    native_request, angle, _native_transfer(t), beam_layer=beam
                )
            )
    bearings = (
        *(_web_bearings(native_request, native_view) if web_resolved else ()),
        *_nonstandard_flange_bearings(native_request, native_view),
    )
    common = _common_bolts(native_request, native_view) if web_resolved else ()
    record = next(
        (s for s in registry.responses if s.reference == request.response_source_reference), None
    )
    response = validate_support_response(response_binding(preview), record)
    support_bolts = []
    support_local: list[SupportLocalCheck] = []
    for t in preview.connectors:
        physical = tuple(
            b
            for b in preview.geometry.support_bolts
            if b.hardware.group_id == f"{t.connector_id}_SUPPORT_GROUP"
        )
        projected = (
            {}
            if t.support_in_plane_demand is None
            else {b.bolt_id: b for b in t.support_in_plane_demand.solution.projected_bolts()}
        )
        for bolt in physical:
            bolt_id = bolt.hardware.hardware_id
            demands = (
                tuple(d for d in record.shaft_demands if d.bolt_id == bolt_id)
                if record and response.status == "VALID_QUALIFIED_RESPONSE"
                else ()
            )
            for demand in demands or (None,):
                support_bolts.append(
                    _bolt_check(preview, t.connector_id, bolt_id, demand, response, registry)
                )
            # Only the external physical force record / expressly participating
            # layer demands feed local checks. A cavity is never a material layer.
            if demands and record is not None:
                layer_forces = tuple(
                    d for d in record.receiving_layer_forces if d.bolt_id == bolt_id
                )
                action = next(
                    a for a in record.actions if a.kind == "BOLT" and a.bolt_id == bolt_id
                )
                resolved_layers = (
                    tuple((d.layer_id, d.force) for d in layer_forces)
                    if layer_forces
                    else ((bolt.crossing.layer_ids[0], action.force),)
                )
                for layer, force in resolved_layers:
                    support_local.extend(
                        bearing_and_pull_through(
                            preview,
                            t.connector_id,
                            bolt_id,
                            force.x,
                            force.y,
                            force.z,
                            response.fingerprint,
                            receiving=True,
                            layer_id=layer,
                        )
                    )
                # Single physical angle leg: no sum of duplicate shaft sections.
                support_local.extend(
                    bearing_and_pull_through(
                        preview,
                        t.connector_id,
                        bolt_id,
                        action.force.x,
                        action.force.y,
                        action.force.z,
                        response.fingerprint,
                        receiving=False,
                    )
                )
            elif bolt_id in projected and t.support_in_plane_demand is not None:
                p = projected[bolt_id]
                for receiving in (False, True):
                    support_local.extend(
                        bearing_and_pull_through(
                            preview,
                            t.connector_id,
                            bolt_id,
                            p.total_force.u,
                            p.total_force.v,
                            None,
                            t.support_in_plane_demand.fingerprint,
                            receiving=receiving,
                        )
                    )
        for receiving in (False, True):
            support_local.extend(support_group_paths(preview, t.connector_id, receiving=receiving))
    zone = evaluate_local_zone(preview, registry, tuple(support_local))
    native = tuple(r for g in local for r in g.native_results)
    failed = tuple(r for r in native if r.numerical_comparison is NumericalComparison.FAIL)
    governing = _governing_result_ids(native)
    scopes = (
        (
            "BEAM_ATTACHMENT",
            aggregate_internal_status(
                tuple(a.check.status for a in attachments)
                + tuple(r.numerical_comparison.value for r in native)
                + tuple(b.comparison.numerical_comparison.value for b in bearings)
                + tuple(g.scope_status for g in local if "NOT_EVALUATED" in g.scope_status)
                + tuple(b.status.value for b in common)
                + tuple(
                    c.availability.value
                    for g in local
                    if g.native_flange_response is not None
                    for h in g.native_flange_response.automatic_handoff_results
                    for c in h.checks
                    if "SOURCE" in c.availability.value or "NOT_SUPPORTED" in c.availability.value
                )
            )[0],
        ),
        ("ANGLE_BODIES", aggregate_internal_status(tuple(p.status for p in providers))[0]),
        ("SUPPORT_RESPONSE", response.status),
        ("SUPPORT_FASTENERS", aggregate_internal_status(tuple(b.status for b in support_bolts))[0]),
        (
            "LOCAL_FRP_REGIONS",
            aggregate_internal_status(
                tuple(
                    REVIEW_PASS
                    if zone.status == REVIEW_PASS
                    and f"LOCAL_CHECK:{c.check_id}" in zone.required_coverage
                    else c.status
                    for c in support_local
                )
            )[0],
        ),
        ("LOCAL_SUPPORT_ZONE", zone.status),
        (
            "BRANCH_ALLOCATION",
            "SOURCE_REQUIRED"
            if request.support.connection_transverse.canonical_magnitude != 0
            else "PASS",
        ),
        ("FULL_RECEIVING_MEMBER_DESIGN", "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"),
    )
    statuses = tuple(status for name, status in scopes if name != "FULL_RECEIVING_MEMBER_DESIGN")
    status, reason = aggregate_internal_status(statuses)
    missing = tuple(
        f"{name}:{value}"
        for name, value in scopes
        if _source_missing(value) or "NOT_EVALUATED" in value
    )
    missing += tuple(
        f"{t.connector_id}:{kind}:{value}"
        for t, p, a in zip(preview.connectors, providers, attachments, strict=True)
        for kind, value in (
            ("CONNECTOR_SOURCE", p.status),
            ("MEMBER_ATTACHMENT_SOURCE", a.check.status),
        )
        if _source_missing(value)
    )
    fp = angle_fingerprint(
        (
            preview.engineering_fingerprint,
            tuple(providers),
            tuple(attachments),
            tuple(local),
            bearings,
            common,
            response.fingerprint,
            tuple(support_bolts),
            tuple(support_local),
            zone,
            scopes,
            status,
            reason,
        )
    )
    return FRPSupportMomentDesign(
        preview,
        status,
        reason,
        tuple(providers),
        tuple(attachments),
        tuple(local),
        bearings,
        common,
        response,
        tuple(support_bolts),
        tuple(support_local),
        zone,
        failed,
        governing,
        missing,
        scopes,
        fp,
        True,
    )
