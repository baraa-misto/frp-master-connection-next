"""Trusted API dependencies."""

from collections.abc import Awaitable, Callable

from fastapi import Request

from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver

TrustedIdentityDependency = Callable[[Request], Awaitable[TrustedIdentity]]


def build_trusted_identity_dependency(
    resolver: TrustedIdentityResolver,
) -> TrustedIdentityDependency:
    """Bind a backend-selected resolver without reading client ownership metadata."""

    async def resolve_trusted_identity(request: Request) -> TrustedIdentity:
        identity = await resolver.resolve()
        request.state.trusted_identity = identity
        return identity

    return resolve_trusted_identity


__all__ = ("TrustedIdentityDependency", "build_trusted_identity_dependency")
