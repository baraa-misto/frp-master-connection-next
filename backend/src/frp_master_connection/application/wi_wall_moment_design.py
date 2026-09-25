"""Stage 4.2 explicit design check: native results, no automatic preview resistance."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import cast

from frp_master_connection.application.multirow_orchestration import (
    MultiRowOrchestrationResponse,
    _execution_bundle,
    _resolve,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.application.wi_wall_moment_demand import END_USE, flange_local_request
from frp_master_connection.application.wi_wall_moment_geometry import PlacedWallAngle, q
from frp_master_connection.application.wi_wall_moment_orchestration import (
    WallMomentConnectorResult,
    WIWallMomentPreview,
    preview_wi_wall_moment,
)
from frp_master_connection.application.wi_wall_moment_sources import (
    WallMomentAttachmentResult,
    WallMomentSourceRegistry,
    evaluate_attachment_source,
    evaluate_connector_source,
)
from frp_master_connection.calculation import MaterialDirection, NumericalComparison, ThreadStatus
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint, exact_decimal
from frp_master_connection.calculation.angle_connector_providers import AngleProviderResult
from frp_master_connection.calculation.channel_moment_splice_resistance import (
    evaluate_channel_two_plane_bolt,
)
from frp_master_connection.calculation.eccentric_demand import (
    InPlaneQuantityVector,
    PerBoltDemandResult,
)
from frp_master_connection.calculation.eccentric_group_modes import (
    EccentricBoltLineResult,
    _line_result,
)
from frp_master_connection.calculation.equations import BearingTrace, pin_bearing_resistance
from frp_master_connection.calculation.frp_angle_connector_provider import REVIEW_PASS
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchResult,
    project_rational,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowExecutionBundle,
    _governing_result_ids,
    calculate_multirow_connection,
)
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    adjusted_property_trace,
    compare_resistance,
    constant_pitch_factor,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    create_standard_hole,
)
from frp_master_connection.calculation.resistance_handoff import (
    ResistanceHandoffCoverage,
    _material_direction,
)
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    AsymmetricTwoPlaneBoltResult,
    FlangePlaneDemand,
)
from frp_master_connection.domain.wi_wall_moment import WIWallMomentRequest

D = Decimal
EMPTY_SOURCES = WallMomentSourceRegistry()


@dataclass(frozen=True, slots=True)
class WallMomentBearing:
    check_id: str
    layer_id: str
    bolt_id: str
    force_a: PhysicalQuantity
    force_b: PhysicalQuantity
    demand: PhysicalQuantity
    material_direction: MaterialDirection
    trace: BearingTrace
    comparison: ResistanceComparison
    demand_fingerprints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WallMomentLocalChecks:
    connector_id: str
    layer_id: str
    native_flange_response: MultiRowOrchestrationResponse | None = None
    native_results: tuple[MultiRowCheckResult, ...] = ()
    native_governing: tuple[str, ...] = ()
    scope_status: str = "NOT_REQUIRED_ZERO_DEMAND"
    native_line_results: tuple[EccentricBoltLineResult, ...] = ()


@dataclass(frozen=True, slots=True)
class WIWallMomentDesign:
    preview: WIWallMomentPreview
    status: str
    status_reason: str
    connector_results: tuple[AngleProviderResult, ...]
    attachment_results: tuple[WallMomentAttachmentResult, ...]
    local_checks: tuple[WallMomentLocalChecks, ...]
    web_bearing: tuple[WallMomentBearing, ...]
    common_web_bolts: tuple[AsymmetricTwoPlaneBoltResult, ...]
    native_governing_check_ids: tuple[str, ...]
    native_failed_checks: tuple[MultiRowCheckResult, ...]
    missing_sources: tuple[str, ...]
    result_fingerprint: str
    flange_bearing: tuple[WallMomentBearing, ...] = ()
    resistance_evaluated: bool = True


def _source_missing(status: str) -> bool:
    return status != REVIEW_PASS and any(
        s in status for s in ("SOURCE_REQUIRED", "SOURCE_PENDING", "SOURCE_NOT_APPLICABLE")
    )


def aggregate_internal_status(statuses: tuple[str, ...]) -> tuple[str, str]:
    """Failure precedence is independent of missing qualification or source records."""
    if any(s in {"INVALID", "INVALID_GEOMETRY"} for s in statuses):
        return "INVALID_GEOMETRY", "INVALID_GEOMETRY_FAIL_CLOSED"
    if "FAIL" in statuses:
        return "FAIL", "EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE"
    if any(_source_missing(s) for s in statuses):
        return "SOURCE_REQUIRED", "REQUIRED_SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE"
    if not statuses or any("NOT_EVALUATED" in s or "NOT_SUPPORTED" in s for s in statuses):
        return "NOT_EVALUATED", "REQUIRED_INTERNAL_CHECK_NOT_EVALUATED"
    return (
        REVIEW_PASS,
        "REQUIRED_INTERNAL_CHECKS_PASS_ENGINEERING_REVIEW_AND_QUALIFICATION_REQUIRED",
    )


def _flange_local(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    result: WallMomentConnectorResult,
    *,
    beam_layer: bool,
) -> WallMomentLocalChecks:
    layer = (
        ("WI_TOP_FLANGE" if angle.connector_id == "TOP_FLANGE_ANGLE" else "WI_BOTTOM_FLANGE")
        if beam_layer
        else angle.connector_id
    )
    if result.flange_demand is None:
        return WallMomentLocalChecks(angle.connector_id, layer)
    if not _standard_hole(angle):
        return WallMomentLocalChecks(
            angle.connector_id,
            layer,
            scope_status="NOT_EVALUATED_NONSTANDARD_HOLE_GROUP_PATH_AUTHORITY_REQUIRED",
        )
    mapping = flange_local_request(
        request, angle, result.core.request.member_action.force.y, beam_layer=beam_layer
    )
    native = evaluate_multirow_connection_with_resolved_demand(mapping, result.flange_demand)
    checks = tuple(
        c.resistance_result
        for h in native.automatic_handoff_results
        for c in h.checks
        if c.resistance_result is not None
    )
    integration = native.automatic_group_mode_integration
    governing = () if integration is None else integration.governing_supported_check_ids
    return WallMomentLocalChecks(
        angle.connector_id, layer, native, checks, governing, "NATIVE_STAGE25A_HANDOFF_GROUP_MODE"
    )


def _web_group_checks(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    result: WallMomentConnectorResult,
    *,
    beam_layer: bool,
) -> WallMomentLocalChecks:
    """Preserve the accepted group-plan envelope, without an equivalent eccentric force.

    The legacy rectangular row-plan seam requires force-aligned rows and its
    accepted row sharing. Oblique and free-moment demand remains explicit, not
    silently converted into a concentric group resistance check.
    """
    layer = "WI_WEB" if beam_layer else angle.connector_id
    web = cast(InPlaneWrenchResult, result.web_demand)
    solution = web.solution
    if solution.force == (Fraction(0), Fraction(0)) and solution.centroid_moment == 0:
        return WallMomentLocalChecks(angle.connector_id, layer)
    if not _standard_hole(angle):
        return WallMomentLocalChecks(
            angle.connector_id,
            layer,
            scope_status="NOT_EVALUATED_NONSTANDARD_HOLE_GROUP_PATH_AUTHORITY_REQUIRED",
        )
    if solution.force[0] != 0 or angle.specification.member_pattern.along != 2:
        return WallMomentLocalChecks(
            angle.connector_id,
            layer,
            scope_status="NOT_EVALUATED_FORCE_ALIGNED_PRESCRIBED_ROW_COMPATIBILITY_REQUIRED",
        )
    if solution.force[1] == 0:
        return WallMomentLocalChecks(
            angle.connector_id,
            layer,
            scope_status="NOT_EVALUATED_ZERO_CONNECTION_FORCE_GROUP_PATH_REQUIRED",
        )
    wrench = result.core.request.member_action
    mapping = flange_local_request(
        request, angle, wrench.force.y * (D(2) if beam_layer else D(1)), beam_layer=beam_layer
    )
    bundle = _execution_bundle(mapping, _resolve(mapping))
    if solution.centroid_moment != 0:
        lines = _slice8_line_checks(web, bundle, beam_layer=beam_layer)
        checks = tuple(line.shear_out_result for line in lines if line.shear_out_result is not None)
        return WallMomentLocalChecks(
            angle.connector_id,
            layer,
            native_results=checks,
            native_governing=_governing_result_ids(checks),
            scope_status="NOT_EVALUATED_ECCENTRIC_FIRST_ROW_AND_BLOCK_PATH_AUTHORITY_REQUIRED",
            native_line_results=lines,
        )
    native = calculate_multirow_connection(bundle)
    checks = tuple(
        r
        for r in native.results
        if r.limit_state
        in {
            MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
            MultiRowCheckFamily.INTERROW_SHEAR_OUT,
            MultiRowCheckFamily.BLOCK_SHEAR,
        }
    )
    return WallMomentLocalChecks(
        angle.connector_id,
        layer,
        native_results=checks,
        native_governing=_governing_result_ids(checks),
        scope_status="NATIVE_CONCENTRIC_GROUP_CHECKS",
    )


def _slice8_line_checks(
    web: InPlaneWrenchResult,
    bundle: MultiRowExecutionBundle,
    *,
    beam_layer: bool,
) -> tuple[EccentricBoltLineResult, ...]:
    """Transport accepted Slice 8 records to the accepted line-compatibility seam.

    No Stage 2.5A result/warning/equilibrium is fabricated. A/B are permuted to
    the legacy path axes B/A. Only the symmetric beam web sums its two physical
    plane vectors; every projection uses the accepted Slice 8 projector.
    """
    solution = web.solution
    scale = Fraction(2 if beam_layer else 1)
    projected = {b.bolt_id: b for b in solution.projected_bolts()}
    geometry = {b.bolt_id: b for b in bundle.physical_geometry.bolts}
    rows = {bolt: row.id for row in bundle.physical_geometry.rows for bolt in row.bolt_ids}
    line_ids = {
        bolt: line.id for line in bundle.physical_geometry.bolt_lines for bolt in line.bolt_ids
    }
    demands = {}
    for b in solution.bolts:

        def pair(values: tuple[Fraction, Fraction]) -> InPlaneQuantityVector:
            return InPlaneQuantityVector(
                q(project_rational(values[1] * scale), solution.force_unit),
                q(project_rational(values[0] * scale), solution.force_unit),
            )

        total = (
            pair(b.total)
            if beam_layer
            else InPlaneQuantityVector(
                projected[b.bolt_id].total_force.v, projected[b.bolt_id].total_force.u
            )
        )
        physical = geometry[b.bolt_id]
        demands[b.bolt_id] = PerBoltDemandResult(
            b.bolt_id,
            rows[b.bolt_id],
            line_ids[b.bolt_id],
            q(physical.x),
            q(physical.y),
            q(project_rational(b.delta[1]), solution.length_unit),
            q(project_rational(b.delta[0]), solution.length_unit),
            project_rational(Fraction(1, len(solution.bolts))),
            pair(b.direct),
            pair(b.correction),
            total,
            q(
                project_rational(b.magnitude_squared * scale * scale, square_root=True),
                solution.force_unit,
            )
            if beam_layer
            else projected[b.bolt_id].total_force_magnitude,
        )
    checks = {
        c.bolt_line_id: c
        for c in bundle.checks
        if c.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    }
    required = set(bundle.required_checks.required_check_ids)
    direction = (D(1) if solution.force[1] > 0 else D(-1), D(0))
    return tuple(
        _line_result(
            line.id,
            line.bolt_ids,
            checks.get(line.id),
            required,
            demands,
            direction,
            False,
            ResistanceHandoffCoverage.PARTIAL_ECCENTRIC,
            bundle,
            {},
        )
        for line in bundle.physical_geometry.bolt_lines
    )


def _bearing(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    layer: str,
    bolt_id: str,
    a: PhysicalQuantity,
    b: PhysicalQuantity,
    magnitude: PhysicalQuantity,
    fingerprints: tuple[str, ...],
    *,
    beam_layer: bool,
) -> WallMomentBearing:
    from frp_master_connection.application.mat1_scope import material_for_owner

    owner_id = "BEAM" if beam_layer else angle.connector_id
    material = material_for_owner(owner_id, create_locked_ice_material_snapshot())
    with localcontext() as context:
        context.prec = 80  # Existing bearing-axis selection boundary.
        direction = _material_direction(
            (a.canonical_magnitude, b.canonical_magnitude),
            (D(0), D(1)) if beam_layer else (D(1), D(0)),
        )
    kind = (
        FRPPropertyKind.FBR_L
        if direction is MaterialDirection.LONGITUDINAL
        else FRPPropertyKind.FBR_T
    )
    entry = next(p for p in material.properties if p.kind is kind)
    spec = angle.specification
    web = "WEB" in angle.connector_id
    thickness = (
        (request.beam.web_thickness if web else request.beam.flange_thickness)
        if beam_layer
        else spec.geometry.thickness
    )
    trace = pin_bearing_resistance(
        thickness,
        spec.fastener.bolt_diameter,
        adjusted_property_trace(entry, END_USE),
        ThreadStatus(spec.fastener.thread_condition),
        c_delta=(
            constant_pitch_factor(
                (spec.member_pattern.pitch,), spec.fastener.bolt_diameter
            ).pitch_factor_c_delta
            if spec.member_pattern.along > 1
            else D(1)
        ),
        c_lap=D(1) if web else D(".6"),
        lambda_factor=D(1),
    )
    return WallMomentBearing(
        f"BEARING:{layer}:{bolt_id}",
        layer,
        bolt_id,
        a,
        b,
        magnitude,
        direction,
        trace,
        compare_resistance(magnitude, trace.factor_trace.design_resistance),
        fingerprints,
    )


def _standard_hole(angle: PlacedWallAngle) -> bool:
    """The inherited group-path contract authorizes published standard holes only.

    Explicit nonstandard holes remain physical and retain actual per-bolt bearing
    checks; they are never silently replaced with a smaller hole in a net-area plan.
    """
    f = angle.specification.fastener
    return (
        f.hole_diameter
        == create_standard_hole(
            f.bolt_diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
        ).hole_diameter
    )


def _nonstandard_flange_bearings(
    request: WIWallMomentRequest,
    preview: WIWallMomentPreview,
) -> tuple[WallMomentBearing, ...]:
    checks = []
    for angle, result in zip(preview.geometry.angles, preview.connectors, strict=True):
        if result.flange_demand is None or _standard_hole(angle):
            continue
        for scenario in result.flange_demand.scenarios:
            for bolt in scenario.per_bolt:
                for beam_layer in (False, True):
                    layer = (
                        (
                            "WI_TOP_FLANGE"
                            if angle.connector_id == "TOP_FLANGE_ANGLE"
                            else "WI_BOTTOM_FLANGE"
                        )
                        if beam_layer
                        else angle.connector_id
                    )
                    checks.append(
                        _bearing(
                            request,
                            angle,
                            layer,
                            f"{scenario.scenario_id}:{bolt.bolt_id}",
                            bolt.total_force.v,
                            bolt.total_force.u,
                            bolt.total_force_magnitude,
                            (result.flange_demand.result_fingerprint,),
                            beam_layer=beam_layer,
                        )
                    )
    return tuple(checks)


def _web_bearings(
    request: WIWallMomentRequest, preview: WIWallMomentPreview
) -> tuple[WallMomentBearing, ...]:
    records: list[WallMomentBearing] = []
    by_connector: dict[str, tuple[PlacedWallAngle, InPlaneWrenchResult]] = {}
    for angle, result in zip(preview.geometry.angles, preview.connectors, strict=True):
        if result.web_demand is None:
            continue
        by_connector[angle.connector_id] = angle, result.web_demand
        for bolt in result.web_demand.solution.projected_bolts():
            if bolt.total_force_magnitude.magnitude:
                records.append(
                    _bearing(
                        request,
                        angle,
                        angle.connector_id,
                        bolt.bolt_id,
                        bolt.total_force.u,
                        bolt.total_force.v,
                        bolt.total_force_magnitude,
                        (result.web_demand.fingerprint,),
                        beam_layer=False,
                    )
                )
    # The beam web takes both physical plane actions, not another half share.
    for hardware in preview.geometry.member_bolts:
        if len(hardware.connector_bolt_ids) != 2:
            continue
        values = []
        for connector_id, bolt_id in hardware.connector_bolt_ids:
            angle, demand = by_connector[connector_id]
            exact_bolt = next(b for b in demand.solution.bolts if b.bolt_id == bolt_id)
            sign = Fraction(angle.frame.a[1])
            values.append((exact_bolt.total[0] * sign, exact_bolt.total[1], demand.fingerprint))
        a = sum((v[0] for v in values), Fraction(0))
        b = sum((v[1] for v in values), Fraction(0))
        magnitude = q(project_rational(a * a + b * b, square_root=True), Unit.N)
        if magnitude.magnitude:
            angle = by_connector["POSITIVE_WEB_ANGLE"][0]
            records.append(
                _bearing(
                    request,
                    angle,
                    "WI_WEB",
                    hardware.hardware_id,
                    q(project_rational(a), Unit.N),
                    q(project_rational(b), Unit.N),
                    magnitude,
                    tuple(v[2] for v in values),
                    beam_layer=True,
                )
            )
    return tuple(records)


def _common_bolts(
    request: WIWallMomentRequest, preview: WIWallMomentPreview
) -> tuple[AsymmetricTwoPlaneBoltResult, ...]:
    results = {r.connector_id: r for r in preview.connectors}
    angles = {a.connector_id: a for a in preview.geometry.angles}
    checks = []
    for hardware in preview.geometry.member_bolts:
        if len(hardware.connector_bolt_ids) != 2:
            continue
        planes = []
        for connector, bolt_id in hardware.connector_bolt_ids:
            web = cast(InPlaneWrenchResult, results[connector].web_demand)
            bolt = next(b for b in web.solution.projected_bolts() if b.bolt_id == bolt_id)
            sign = angles[connector].frame.a[1]
            planes.append(
                FlangePlaneDemand(
                    bolt.total_force.v,
                    q(
                        exact_decimal(
                            Fraction(bolt.total_force.u.canonical_magnitude) * Fraction(sign)
                        ),
                        Unit.N,
                    ),
                    web.fingerprint,
                    connector,
                    bolt_id,
                )
            )
        f = request.positive_web.fastener
        checks.append(
            evaluate_channel_two_plane_bolt(
                bolt_id=hardware.hardware_id,
                physical_path=(hardware.layers[0], hardware.layers[1], hardware.layers[2]),
                outer_plane=planes[0],
                inner_plane=planes[1],
                diameter=f.bolt_diameter,
                thread_condition=f.thread_condition,
                source_authority_id=f.source_authority_id,
                nominal_shear_stress=f.nominal_shear_stress,
            )
        )
    return tuple(checks)


def evaluate_wi_wall_moment(
    request: WIWallMomentRequest, registry: WallMomentSourceRegistry = EMPTY_SOURCES
) -> WIWallMomentDesign:
    preview = preview_wi_wall_moment(request)
    if not preview.design_check_ready:
        return WIWallMomentDesign(
            preview,
            preview.status,
            "GEOMETRY_PREVENTS_DESIGN_CHECK",
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            angle_fingerprint((preview.engineering_fingerprint, preview.status)),
            resistance_evaluated=False,
        )
    providers, attachments, local = [], [], []
    for angle, result in zip(preview.geometry.angles, preview.connectors, strict=True):
        providers.append(evaluate_connector_source(request, angle, result.core, registry))
        attachments.append(evaluate_attachment_source(request, angle, result.core, registry))
        for beam in (False, True):
            if beam and angle.connector_id == "NEGATIVE_WEB_ANGLE":
                continue  # One full-demand beam web, not two half-demand web checks.
            local.append(
                (_flange_local if result.web_demand is None else _web_group_checks)(
                    request, angle, result, beam_layer=beam
                )
            )
    bearings = _web_bearings(request, preview)
    flange_bearing = _nonstandard_flange_bearings(request, preview)
    bolts = _common_bolts(request, preview)
    native = tuple(r for group in local for r in group.native_results)
    failed = tuple(r for r in native if r.numerical_comparison is NumericalComparison.FAIL)
    governing = _governing_result_ids(native)
    missing = tuple(
        f"{a.connector_id}:{kind}:{status}"
        for a, p, t in zip(preview.geometry.angles, providers, attachments, strict=True)
        for kind, status in (
            ("CONNECTOR_SOURCE", p.status),
            ("MEMBER_ATTACHMENT_SOURCE", t.check.status),
        )
        if _source_missing(status)
    )
    statuses = tuple(p.status for p in providers) + tuple(a.check.status for a in attachments)
    statuses += tuple(r.numerical_comparison.value for r in native)
    statuses += tuple(g.scope_status for g in local if "NOT_EVALUATED" in g.scope_status)
    statuses += tuple(
        b.comparison.numerical_comparison.value for b in (*bearings, *flange_bearing)
    ) + tuple(b.status.value for b in bolts)
    # Native source-pending/unsupported records remain in their original response trace.
    statuses += tuple(
        c.availability.value
        for g in local
        if g.native_flange_response is not None
        for h in g.native_flange_response.automatic_handoff_results
        for c in h.checks
        if "SOURCE" in c.availability.value or "NOT_SUPPORTED" in c.availability.value
    )
    status, reason = aggregate_internal_status(statuses)
    fingerprint = angle_fingerprint(
        (
            preview.engineering_fingerprint,
            providers,
            attachments,
            local,
            bearings,
            flange_bearing,
            bolts,
            status,
            reason,
        )
    )
    return WIWallMomentDesign(
        preview,
        status,
        reason,
        tuple(providers),
        tuple(attachments),
        tuple(local),
        bearings,
        bolts,
        governing,
        failed,
        missing,
        fingerprint,
        flange_bearing=flange_bearing,
    )
