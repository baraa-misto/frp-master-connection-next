"""CME-3 bound connection aggregation over native geometry and frozen providers.

This module receives only server-built objects. No public payload can supply a
body source, response certificate, member role, or pre-resolved resistance.
"""

from __future__ import annotations

from dataclasses import dataclass

from frp_master_connection.application.connector_material_assembly import (
    MaterialAssembly,
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_family_activation import (
    AUTHORITY,
    ROUTES,
    ActivatedBodyResult,
    BodyAuthority,
    BodyBinding,
    RequiredCheck,
    connection_summary,
    evaluate_bound_body,
)
from frp_master_connection.application.stainless_native_results import physical_owner
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.domain.connector_materials import ComponentRole


@dataclass(frozen=True, slots=True)
class BoundNonBodyCheck:
    component_id: str
    check: RequiredCheck
    native_record: object


@dataclass(frozen=True, slots=True)
class NonBodyAuthority:
    """Reviewed resolver output for independently owned checks at this exact state.

    Native retained checks need no stainless response recertification. Optional
    response fingerprints bind additional source-qualified checks; they do not
    authorize suppressing existing native failures. No alternative arithmetic.
    """

    route: str
    native_identity: str
    response_fingerprints: tuple[str, ...]
    checks: tuple[BoundNonBodyCheck, ...]
    blockers: tuple[str, ...]
    trace: object
    complete: bool


@dataclass(frozen=True, slots=True)
class ConnectionAuthority:
    bodies: tuple[BodyAuthority, ...] = ()
    non_body: NonBodyAuthority | None = None


@dataclass(frozen=True, slots=True)
class StainlessConnectionResult:
    route: str
    assembly: MaterialAssembly
    bodies: tuple[ActivatedBodyResult, ...]
    checks: tuple[RequiredCheck, ...]
    blockers: tuple[str, ...]
    status: str
    native_non_body_trace: object
    fingerprint: str
    material: str = "SS316"
    authority: str = AUTHORITY


def evaluate_stainless_connection(
    route: str,
    native_preview: object,
    *,
    authority: ConnectionAuthority | None = None,
    native_non_body_trace: object = None,
) -> StainlessConnectionResult:
    """Geometry/physical roles precede source resolution and C2 dispatch.

    Absent production qualification is explicit. In particular a native FRP
    stiffness/contact-dependent force distribution is not certified for SS316
    by merely retaining its old result fingerprint.
    """
    if route not in ROUTES:
        raise ValueError("CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE")
    if authority is None:
        authority = ConnectionAuthority()
    assembly = canonical_material_assembly(route, native_preview)
    bindings = tuple(
        BodyBinding(route, c.physical_id, c.body_form, assembly.native_identity)
        for c in assembly.components
        if c.role is ComponentRole.CONNECTOR_BODY
    )
    if not bindings:
        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
    by_body = {a.binding.body: a for a in authority.bodies}
    if len(by_body) != len(authority.bodies) or not set(by_body).issubset(b.body for b in bindings):
        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
    bodies = tuple(evaluate_bound_body(b, by_body.get(b.body)) for b in bindings)
    checks = tuple(c for body in bodies for c in body.checks)
    blockers = tuple(reason for body in bodies for reason in body.blockers)
    non_body = authority.non_body
    complete = False
    if non_body is None:
        blockers += ("STAINLESS_NON_BODY_RESPONSE_REVALIDATION_REQUIRED",)
    else:
        if non_body.route != route or non_body.native_identity != assembly.native_identity:
            raise ValueError("STAINLESS_ACTIVATION_SNAPSHOT_STALE")
        responses = {
            body.response.fingerprint
            for body in bodies
            if body.response is not None and body.response.status == "QUALIFIED_RESPONSE"
        }
        if not set(non_body.response_fingerprints).issubset(responses):
            raise ValueError("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED")
        for bound in non_body.checks:
            owner = physical_owner(assembly, bound.component_id)
            if owner.role is ComponentRole.CONNECTOR_BODY or bound.check.domain != owner.role.value:
                raise ValueError("STAINLESS_FRP_BODY_FALLBACK_PROHIBITED")
        checks += tuple(bound.check for bound in non_body.checks)
        blockers += non_body.blockers
        complete = non_body.complete
        native_non_body_trace = non_body.trace
    status = connection_summary(checks, blockers, complete=complete)
    return StainlessConnectionResult(
        route,
        assembly,
        bodies,
        checks,
        blockers,
        status,
        native_non_body_trace,
        angle_fingerprint(
            (
                AUTHORITY,
                "SS316",
                route,
                assembly.native_identity,
                bodies,
                checks,
                blockers,
                status,
                complete,
            )
        ),
    )
