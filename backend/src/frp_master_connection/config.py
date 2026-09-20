"""Nonengineering application configuration."""

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationEnvironment(StrEnum):
    """Controlled deployment-environment classification."""

    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Backend settings sourced only from project-prefixed environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FRP_MASTER_CONNECTION_",
        env_file=None,
        extra="forbid",
        frozen=True,
    )

    environment: ApplicationEnvironment = ApplicationEnvironment.LOCAL


__all__ = ("AppSettings", "ApplicationEnvironment")
