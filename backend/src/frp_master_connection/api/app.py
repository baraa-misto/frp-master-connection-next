"""FastAPI application factory for the trusted stateless backend."""

from fastapi import FastAPI

from frp_master_connection.api.routes import build_router
from frp_master_connection.config import ApplicationEnvironment, AppSettings
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
            "Trusted stateless backend for the current verified single-bolt/single-row slice; "
            "no persistence, report generation, or automatic bolt-demand distribution."
        ),
    )
    application.state.product_id = PRODUCT_ID
    application.state.environment = resolved_settings.environment
    application.include_router(build_router(resolved_identity))
    return application


app = create_app()

__all__ = ("IdentityConfigurationError", "app", "create_app")
