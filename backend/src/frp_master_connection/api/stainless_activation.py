"""CME-3 public transport over validated native geometry and server-owned adapters."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from math import isfinite
from typing import Annotated

from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import JsonValue

from frp_master_connection.api.wi_wall_moment_mapping import serialize_wall_moment_value
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_connection_design import (
    evaluate_stainless_connection,
)
from frp_master_connection.application.stainless_family_activation import (
    AUTHORITY,
    ROUTES,
    STACKS,
    canonical_material,
)
from frp_master_connection.application.stainless_moment_ownership import moment_check_partition
from frp_master_connection.application.stainless_native_aggregation import (
    merge_native_authority,
    retained_native_authority,
)
from frp_master_connection.application.stainless_native_results import native_row_partition
from frp_master_connection.application.stainless_public_authority import resolve_public_authority
from frp_master_connection.application.stainless_splice_ownership import splice_check_partition
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.domain.connector_materials import ComponentRole

MOMENT_ANGLES = {
    "wi-beam-concrete-wall-moment",
    "wi-beam-frp-support-moment",
    "angle-column-two-leg-moment-base",
    "wi-rhs-srs-column-moment-base",
}


def serialize_activation_value(value: object) -> JsonValue:
    """Retain native legacy scene floats; never coerce them into engineering Decimal.

    Other native quantities use the accepted exact transport. In particular,
    this serializer does not round either Tee unit path into the other one.
    """
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("STAINLESS_NONFINITE_NATIVE_TRACE")
        return value
    if isinstance(value, PhysicalQuantity):
        return serialize_wall_moment_value(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: serialize_activation_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [serialize_activation_value(item) for item in value]
    return serialize_wall_moment_value(value)


def material_selection(connector_body_material: Annotated[list[str] | None, Query()] = None) -> str:
    """Only material is public. A query cannot carry a server-owned certificate."""
    try:
        if connector_body_material is None:
            return "FRP"
        values = {canonical_material(v) for v in connector_body_material}
        if len(values) != 1:
            raise ValueError("STAINLESS_MIXED_CONNECTOR_BODY_MATERIALS_NOT_SUPPORTED_IN_CME3_RC1")
        return values.pop()
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


def stainless_design_response(route: str, native_design: object) -> JSONResponse:
    """No public qualification deserialization or FRP-body fallback.

    Native checks are retained as individually owned trace, not silently certified
    as material-independent. Production has no qualified stainless slip/contact
    or section registry. Source-present integration enters the application layer
    through reviewed server-owned ConnectionAuthority, never through this DTO.
    """
    if route not in ROUTES:
        raise ValueError("CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE")
    preview = getattr(native_design, "preview", None)
    if preview is None:
        raise ValueError("STAINLESS_NATIVE_DESIGN_PREVIEW_REQUIRED")
    assembly = canonical_material_assembly(route, preview)
    partition = (
        splice_check_partition(assembly, native_design)
        if ROUTES[route] == "PLATE"
        else moment_check_partition(assembly, native_design)
        if route in MOMENT_ANGLES
        else native_row_partition(assembly, native_design)
    )
    authority = resolve_public_authority(route, assembly, preview, native_design)
    authority = replace(
        authority,
        non_body=merge_native_authority(
            retained_native_authority(route, assembly, partition), authority.non_body
        ),
    )
    result = evaluate_stainless_connection(
        route,
        preview,
        authority=authority,
        native_non_body_trace=partition,
    )
    selection = tuple(
        (c.physical_id, c.body_form, "SS316", STACKS[c.body_form])
        for c in assembly.components
        if c.role is ComponentRole.CONNECTOR_BODY
    )
    return JSONResponse(
        {
            "activation_authority": AUTHORITY,
            "route_id": route,
            "connector_body_material": "SS316",
            "status": result.status,
            "fingerprint": result.fingerprint,
            "activation_selection_identity": angle_fingerprint((AUTHORITY, route, selection)),
            "bodies": [
                {
                    "body_id": body.binding.body,
                    "body_form": body.binding.form,
                    "material": body.material,
                    "activation": body.activation,
                    "fingerprint": body.fingerprint,
                    "blockers": list(body.blockers),
                    "provider_fingerprints": [
                        provider.fingerprint
                        for provider in (body.response, body.plate, body.clear, body.shape)
                        if provider is not None
                    ],
                    "required_provider_stack": list(STACKS[body.binding.form]),
                    "frp_body_resistance_used": False,
                    "trace": serialize_activation_value(body),
                }
                for body in result.bodies
            ],
            "blockers": list(result.blockers),
            "native_non_body_checks": serialize_activation_value(partition.retained_non_body),
            "trace": {
                "native_identity": assembly.native_identity,
                "native_non_body": serialize_activation_value(partition.retained_non_body),
                "non_body_response_status": (
                    "STAINLESS_NON_BODY_RESPONSE_REVALIDATION_REQUIRED"
                    if authority.non_body is None
                    else "RETAINED_NON_BODY_AUTHORITY"
                ),
                "superseded_frp_body_checks_not_governing": serialize_activation_value(
                    partition.superseded_frp_body
                ),
                "native_source_trace_not_stainless_qualification": serialize_activation_value(
                    native_design
                ),
                "activation": serialize_activation_value(result),
                "primary_members": "FRP_ONLY",
                "hardware": "INDEPENDENT",
                "foundation": "EXTERNAL_NOT_EVALUATED",
            },
        }
    )
