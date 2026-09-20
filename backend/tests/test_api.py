"""API, configuration, identity-wiring, and metadata tests."""

import asyncio
import json
from dataclasses import dataclass
from importlib.metadata import version as installed_version
from typing import Final

import httpx
import pytest
from fastapi import FastAPI

import frp_master_connection
from frp_master_connection.api.app import IdentityConfigurationError, create_app
from frp_master_connection.api.schemas import HealthResponse
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.security import LocalDevelopmentIdentity, TrustedIdentity
from frp_master_connection.version import (
    APPLICATION_VERSION,
    CALCULATION_ENGINE_VERSION,
    CODE_BASIS,
    ENGINEERING_RULE_SET_VERSION,
    ERRATA_STATUS,
    PRODUCT_ID,
    PROJECT_SCHEMA_VERSION,
)

EXPECTED_META_KEYS: Final = {
    "application_version",
    "calculation_engine_version",
    "code_basis",
    "engineering_calculations_available",
    "engineering_rule_set_version",
    "errata_status",
    "product_id",
    "project_schema_version",
    "report_generation_available",
}


@dataclass(slots=True)
class TrackingIdentityResolver:
    """Test resolver that records protected-route resolution."""

    identity: TrustedIdentity
    production_capable: bool = True
    calls: int = 0

    async def resolve(self) -> TrustedIdentity:
        """Return a fixed test identity and record the trusted resolution."""
        self.calls += 1
        return self.identity


def _trusted_test_identity() -> TrustedIdentity:
    return TrustedIdentity(
        account_id="test-account",
        organization_id="test-organization",
        roles=frozenset({"tester"}),
        authentication_source="test-resolver",
    )


def _get(
    application: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


def test_health_response_has_exact_core_fields_and_requires_no_identity() -> None:
    resolver = TrackingIdentityResolver(_trusted_test_identity())
    application = create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )

    response = _get(application, "/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "product_id": PRODUCT_ID,
        "application_version": APPLICATION_VERSION,
    }
    assert resolver.calls == 0


def test_health_schema_documents_service_health_not_engineering_pass() -> None:
    description = HealthResponse.model_fields["status"].description

    assert description is not None
    assert "Service/process health only" in description
    assert "never an engineering PASS result" in description


def test_metadata_response_uses_trusted_identity_and_exact_versions() -> None:
    resolver = TrackingIdentityResolver(_trusted_test_identity())
    application = create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )

    response = _get(application, "/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "product_id": PRODUCT_ID,
        "application_version": APPLICATION_VERSION,
        "project_schema_version": PROJECT_SCHEMA_VERSION,
        "calculation_engine_version": CALCULATION_ENGINE_VERSION,
        "engineering_rule_set_version": ENGINEERING_RULE_SET_VERSION,
        "code_basis": CODE_BASIS,
        "errata_status": ERRATA_STATUS,
        "engineering_calculations_available": True,
        "report_generation_available": False,
    }
    assert resolver.calls == 1


def test_spoofed_identity_headers_cannot_change_backend_identity() -> None:
    trusted_identity = _trusted_test_identity()
    resolver = TrackingIdentityResolver(trusted_identity)
    application = create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )

    response = _get(
        application,
        "/api/v1/meta",
        headers={
            "x-account-id": "spoofed-account",
            "x-owner-account-id": "spoofed-owner",
            "x-organization-id": "spoofed-organization",
        },
    )

    assert response.status_code == 200
    assert resolver.identity == trusted_identity
    assert resolver.calls == 1
    assert set(response.json()) == EXPECTED_META_KEYS
    assert "test-account" not in response.text
    assert "test-organization" not in response.text
    assert "spoofed" not in response.text


def test_openapi_product_path_set_is_exact() -> None:
    application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))

    assert set(application.openapi()["paths"]) == {
        "/api/v1/connector-materials/capabilities",
        "/api/v1/connector-materials/plan",
        "/health",
        "/api/v1/meta",
        "/api/v1/calculations/single-bolt/evaluate",
        "/api/v1/calculations/single-bolt/preview",
        "/api/v1/calculations/multi-row/preview",
        "/api/v1/calculations/multi-row/design-check",
        "/api/v1/calculations/tee-connector/preview",
        "/api/v1/calculations/tee-connector/design-check",
        "/api/v1/calculations/clip-angle/preview",
        "/api/v1/calculations/clip-angle/design-check",
        "/api/v1/calculations/paired-clip-angle/preview",
        "/api/v1/calculations/paired-clip-angle/design-check",
        "/api/v1/calculations/multi-member-tee/preview",
        "/api/v1/calculations/multi-member-tee/design-check",
        "/api/v1/calculations/beam-concrete-paired-angle/preview",
        "/api/v1/calculations/beam-concrete-paired-angle/design-check",
        "/api/v1/calculations/direct-side-lap-concrete/preview",
        "/api/v1/calculations/direct-side-lap-concrete/design-check",
        "/api/v1/calculations/column-base-web-angles/preview",
        "/api/v1/calculations/column-base-web-angles/design-check",
        "/api/v1/calculations/beam-web-splice/preview",
        "/api/v1/calculations/beam-web-splice/design-check",
        "/api/v1/calculations/wi-major-axis-moment-splice/preview",
        "/api/v1/calculations/wi-major-axis-moment-splice/design-check",
        "/api/v1/calculations/channel-major-axis-moment-splice/preview",
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check",
        "/api/v1/calculations/wi-beam-concrete-wall-moment/preview",
        "/api/v1/calculations/wi-beam-concrete-wall-moment/design-check",
        "/api/v1/calculations/wi-beam-frp-support-moment/preview",
        "/api/v1/calculations/wi-beam-frp-support-moment/design-check",
        "/api/v1/calculations/angle-column-two-leg-moment-base/defaults",
        "/api/v1/calculations/angle-column-two-leg-moment-base/preview",
        "/api/v1/calculations/angle-column-two-leg-moment-base/design-check",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/defaults",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/preview",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/design-check",
        "/api/v1/calculations/wi-rhs-srs-column-moment-base/convert-units",
        "/api/v1/calculations/double-channel-truss-node/defaults",
        "/api/v1/calculations/double-channel-truss-node/preview",
        "/api/v1/calculations/double-channel-truss-node/design-check",
        "/api/v1/calculations/double-channel-truss-node/convert-units",
    }


def test_no_prohibited_product_endpoint_exists() -> None:
    application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    prohibited_paths = {
        "/billing",
        "/calculate",
        "/check",
        "/design",
        "/entitlements",
        "/login",
        "/logout",
        "/organizations",
        "/projects",
        "/reports",
        "/users",
    }

    assert prohibited_paths.isdisjoint(application.openapi()["paths"])


def test_openapi_has_no_owner_or_organization_input_schema() -> None:
    application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    serialized_openapi = json.dumps(application.openapi(), sort_keys=True)

    assert "owner_account_id" not in serialized_openapi
    assert "organization_id" not in serialized_openapi


def test_installed_package_api_and_runtime_versions_are_identical() -> None:
    application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))

    assert installed_version("frp-master-connection") == APPLICATION_VERSION
    assert frp_master_connection.__version__ == APPLICATION_VERSION
    assert application.version == APPLICATION_VERSION


def test_metadata_constants_are_exact_and_calculation_capability_is_available() -> None:
    assert PROJECT_SCHEMA_VERSION == "0.1.0-draft"
    assert CALCULATION_ENGINE_VERSION == "0.1.0.dev1"
    assert ENGINEERING_RULE_SET_VERSION == "asce74-23-ch8-single-bolt-rc2.dev1"
    assert CODE_BASIS == "ASCE/SEI 74-23"
    assert ERRATA_STATUS == "Erratum 1 verified; effective 2026-01-13"


def test_test_mode_default_identity_is_deterministic() -> None:
    first = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    second = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))

    assert _get(first, "/api/v1/meta").json() == _get(second, "/api/v1/meta").json()


def test_default_configuration_is_local_and_contains_no_secret_default() -> None:
    settings = AppSettings()

    assert settings.environment is ApplicationEnvironment.LOCAL
    assert set(AppSettings.model_fields) == {"environment"}
    assert AppSettings.model_config["env_prefix"] == "FRP_MASTER_CONNECTION_"
    assert AppSettings.model_config["env_file"] is None


def test_prefixed_environment_variable_selects_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRP_MASTER_CONNECTION_ENVIRONMENT", "production")

    assert AppSettings().environment is ApplicationEnvironment.PRODUCTION


def test_production_without_explicit_resolver_fails_closed() -> None:
    with pytest.raises(IdentityConfigurationError, match="explicit trusted"):
        create_app(settings=AppSettings(environment=ApplicationEnvironment.PRODUCTION))


def test_production_rejects_local_development_resolver() -> None:
    with pytest.raises(IdentityConfigurationError, match="forbidden in production"):
        create_app(
            settings=AppSettings(environment=ApplicationEnvironment.PRODUCTION),
            identity_resolver=LocalDevelopmentIdentity(),
        )


def test_production_accepts_explicit_production_capable_resolver() -> None:
    resolver = TrackingIdentityResolver(_trusted_test_identity(), production_capable=True)
    application = create_app(
        settings=AppSettings(environment=ApplicationEnvironment.PRODUCTION),
        identity_resolver=resolver,
    )

    response = _get(application, "/api/v1/meta")

    assert response.status_code == 200
    assert resolver.calls == 1
