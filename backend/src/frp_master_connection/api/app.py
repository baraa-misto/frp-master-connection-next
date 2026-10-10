"""FastAPI application factory for the trusted stateless backend."""

import json
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from frp_master_connection.api.direct_status import input_direct_status
from frp_master_connection.api.routes import build_router
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.reporting.capture import reportable_route
from frp_master_connection.reporting.provenance import server_defaulted_fields
from frp_master_connection.reporting.routes import build_report_router
from frp_master_connection.reporting.snapshot import (
    ReportSnapshotStore,
    SnapshotError,
    SnapshotSigner,
)
from frp_master_connection.security import LocalDevelopmentIdentity, TrustedIdentityResolver
from frp_master_connection.version import APPLICATION_VERSION, PRODUCT_ID


class IdentityConfigurationError(RuntimeError):
    """Raised when a deployment lacks a permitted trusted identity resolver."""


def _select_identity_resolver(
    settings: AppSettings,
    resolver: TrustedIdentityResolver | None,
) -> TrustedIdentityResolver:
    """Select a resolver while preventing local-identity fallback in production."""
    if resolver is None:
        if settings.environment is ApplicationEnvironment.PRODUCTION:
            raise IdentityConfigurationError(
                "Production requires an explicit trusted production-capable identity resolver."
            )
        return LocalDevelopmentIdentity()

    if (
        settings.environment is ApplicationEnvironment.PRODUCTION
        and not resolver.production_capable
    ):
        raise IdentityConfigurationError(
            "Local or test identity resolvers are forbidden in production."
        )
    return resolver


def create_app(
    *,
    settings: AppSettings | None = None,
    identity_resolver: TrustedIdentityResolver | None = None,
) -> FastAPI:
    """Create a FastAPI shell with explicit configuration and trusted identity wiring."""
    resolved_settings = settings if settings is not None else AppSettings()
    resolved_identity = _select_identity_resolver(resolved_settings, identity_resolver)
    application = FastAPI(
        title="FRP Master Connection API",
        version=APPLICATION_VERSION,
        description=(
            "Trusted calculation backend for the current connection catalog, with "
            "authenticated transient calculation snapshots and PDF report export."
        ),
    )
    application.state.product_id = PRODUCT_ID
    application.state.environment = resolved_settings.environment
    signer = SnapshotSigner()
    snapshot_store = ReportSnapshotStore()
    application.state.report_signer = signer
    application.state.report_snapshot_store = snapshot_store

    @application.middleware("http")
    async def capture_report_snapshot(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Seal the validated native response from this exact calculation call."""

        if (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/direct-two-bolt/")
            and len(await request.body()) > 8_000_000
        ):
            return JSONResponse({"detail": "SAB2 request size limit exceeded"}, status_code=413)
        if request.method != "POST" or not request.url.path.startswith(
            ("/api/v1/calculations/", "/api/v1/frp-materials/")
        ):
            return await call_next(request)
        raw_request = await request.body()
        if len(raw_request) > 8_000_000:
            return JSONResponse({"detail": "REPORT1 request size limit exceeded"}, status_code=413)
        try:
            parsed_request = json.loads(raw_request)
        except UnicodeDecodeError, ValueError:
            return await call_next(request)
        if not isinstance(parsed_request, dict):
            return await call_next(request)
        route = reportable_route(request.url.path, parsed_request)
        response = await call_next(request)
        if route is None or response.status_code not in {200, 422}:
            return response
        report_request = dict(parsed_request)
        calculation_query = {
            key: values
            for key in request.query_params
            if key != "report_snapshot"
            if (values := request.query_params.getlist(key))
        }
        if calculation_query:
            report_request["_calculation_query_parameters"] = calculation_query
        raw_response = b"".join(
            [cast(bytes, part) async for part in cast(StreamingResponse, response).body_iterator]
        )
        native_response = json.loads(raw_response)
        invalid_request = response.status_code == 422
        result = (
            {
                "status": "INPUT_VALIDATION_FAILED",
                "geometry_status": "INVALID_INPUT",
                "validation_issues": native_response.get("detail"),
                "design_evaluated": False,
            }
            if invalid_request
            else native_response
        )
        identity = request.state.trusted_identity
        if invalid_request and route[0] == "multi-row":
            result = input_direct_status(result, report_request)
        opt_in = request.query_params.get("report_snapshot") == "1"
        safe_headers = {
            key: value for key, value in response.headers.items() if key.lower() != "content-length"
        }
        try:
            token = signer.issue(
                family=route[0],
                kind="input_only" if invalid_request else route[1],
                request=report_request,
                result=result,
                input_provenance={
                    **getattr(request.state, "direct_qualification_provenance", {}),
                    "server_defaulted_fields": server_defaulted_fields(
                        request.scope.get("route"), parsed_request
                    )
                    if not invalid_request
                    else {},
                },
                account_id=identity.account_id,
            )
            safe_headers["X-Report-Handle"] = snapshot_store.put(token)
            safe_headers["X-Report-Kind"] = "input_only" if invalid_request else route[1]
            if opt_in and not invalid_request:
                result["report_snapshot"] = token
        except SnapshotError as error:
            if opt_in and not invalid_request:
                result["report_snapshot_error"] = str(error)
            else:
                safe_headers["X-Report-Error"] = "snapshot-unavailable"
        if opt_in and not invalid_request:
            return JSONResponse(result, headers=safe_headers)
        return Response(
            content=raw_response, status_code=response.status_code, headers=safe_headers
        )

    application.include_router(build_router(resolved_identity))
    application.include_router(build_report_router(signer, snapshot_store, resolved_identity))
    return application


app = create_app()

__all__ = ("IdentityConfigurationError", "app", "create_app")
