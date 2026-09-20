"""Trusted API dependencies."""

from collections.abc import Awaitable, Callable

from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver

TrustedIdentityDependency = Callable[[], Awaitable[TrustedIdentity]]


def build_trusted_identity_dependency(
    resolver: TrustedIdentityResolver,
) -> TrustedIdentityDependency:
    """Bind a backend-selected resolver without reading client ownership metadata."""

    async def resolve_trusted_identity() -> TrustedIdentity:
        return await resolver.resolve()

    return resolve_trusted_identity


__all__ = ("TrustedIdentityDependency", "build_trusted_identity_dependency")
