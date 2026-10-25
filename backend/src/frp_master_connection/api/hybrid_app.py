"Candidate composition: native application plus the authorized live hybrid mode."

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from frp_master_connection.api.app import create_app
from frp_master_connection.api.hybrid_workflow import build_hybrid_router
from frp_master_connection.config import AppSettings
from frp_master_connection.security import LocalDevelopmentIdentity, TrustedIdentityResolver


def create_hybrid_app(
    *, settings: AppSettings | None = None, identity_resolver: TrustedIdentityResolver | None = None
) -> FastAPI:
    application = create_app(settings=settings, identity_resolver=identity_resolver)
    resolver = identity_resolver if identity_resolver is not None else LocalDevelopmentIdentity()
    application.include_router(build_hybrid_router(resolver))

    @application.middleware("http")
    async def bounded_hybrid_input(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/direct-hybrid/")
            and len(await request.body()) > 8_000_000
        ):
            return JSONResponse({"detail": "Hybrid input size limit exceeded."}, status_code=413)
        return await call_next(request)

    @application.get("/api/v1/direct-hybrid/runtime")
    def runtime() -> dict[str, str | bool]:
        root = Path(__file__).resolve().parents[4]
        sha = os.environ.get("FRP_HYBRID_CANDIDATE_SHA", "UNPUBLISHED_WORKTREE")
        return {
            "candidate_sha": sha,
            "workflow_available": True,
            "structural_method_activation": False,
            "backend_module": str(Path(__file__).resolve()),
            "repository": str(root),
        }

    return application


app = create_hybrid_app()
