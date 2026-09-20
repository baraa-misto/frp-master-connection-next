"""Trusted identity values and resolver contracts independent of web frameworks."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TrustedIdentity:
    """Immutable server-established identity context."""

    account_id: str
    organization_id: str | None
    roles: frozenset[str]
    authentication_source: str

    def __post_init__(self) -> None:
        """Reject ambiguous identity values before they reach a protected route."""
        if not self.account_id.strip():
            raise ValueError("Trusted account_id must be a nonempty opaque string.")
        if self.organization_id is not None and not self.organization_id.strip():
            raise ValueError("Trusted organization_id must be absent or nonempty.")
        if not self.authentication_source.strip():
            raise ValueError("Trusted authentication_source must be nonempty.")


class TrustedIdentityResolver(Protocol):
    """API-boundary contract for a backend-controlled identity source."""

    @property
    def production_capable(self) -> bool:
        """Return whether this resolver is permitted in production."""
        ...

    async def resolve(self) -> TrustedIdentity:
        """Return identity established by trusted server context."""
        ...


@dataclass(frozen=True, slots=True)
class LocalDevelopmentIdentity:
    """Fixed backend-generated identity permitted only in local or test mode."""

    production_capable: bool = field(default=False, init=False)
    _identity: TrustedIdentity = field(
        default=TrustedIdentity(
            account_id="local-development-account",
            organization_id=None,
            roles=frozenset({"developer"}),
            authentication_source="local-development",
        ),
        init=False,
        repr=False,
    )

    async def resolve(self) -> TrustedIdentity:
        """Return the fixed server-owned local-development identity."""
        return self._identity


__all__ = ("LocalDevelopmentIdentity", "TrustedIdentity", "TrustedIdentityResolver")
