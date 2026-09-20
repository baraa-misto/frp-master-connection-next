"""Framework-independent trusted-identity tests."""

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from frp_master_connection.security import LocalDevelopmentIdentity, TrustedIdentity


def test_local_identity_is_fixed_backend_generated_and_nonanonymous() -> None:
    resolver = LocalDevelopmentIdentity()

    identity = asyncio.run(resolver.resolve())

    assert identity.account_id == "local-development-account"
    assert identity.account_id != "anonymous"
    assert identity.organization_id is None
    assert identity.roles == frozenset({"developer"})
    assert identity.authentication_source == "local-development"
    assert resolver.production_capable is False
    assert asyncio.run(resolver.resolve()) is identity


def test_trusted_identity_is_immutable() -> None:
    identity = TrustedIdentity(
        account_id="immutable-account",
        organization_id=None,
        roles=frozenset(),
        authentication_source="test",
    )

    attribute_name = "account_id"
    with pytest.raises(FrozenInstanceError):
        setattr(identity, attribute_name, "changed")


def test_trusted_identity_rejects_empty_account_id() -> None:
    with pytest.raises(ValueError, match="account_id"):
        TrustedIdentity(
            account_id=" ",
            organization_id=None,
            roles=frozenset(),
            authentication_source="test",
        )


def test_trusted_identity_rejects_empty_present_organization_id() -> None:
    with pytest.raises(ValueError, match="organization_id"):
        TrustedIdentity(
            account_id="account",
            organization_id="",
            roles=frozenset(),
            authentication_source="test",
        )


def test_trusted_identity_rejects_empty_authentication_source() -> None:
    with pytest.raises(ValueError, match="authentication_source"):
        TrustedIdentity(
            account_id="account",
            organization_id="organization",
            roles=frozenset(),
            authentication_source=" ",
        )


def test_trusted_identity_accepts_opaque_organization_id() -> None:
    identity = TrustedIdentity(
        account_id="account::opaque",
        organization_id="organization::opaque",
        roles=frozenset({"role::opaque"}),
        authentication_source="source::opaque",
    )

    assert identity.organization_id == "organization::opaque"
