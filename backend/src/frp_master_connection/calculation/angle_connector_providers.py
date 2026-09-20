"""CS7-RC2 explicit material-provider boundary, separate from the neutral core."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreResult,
    angle_fingerprint,
)

PROVIDER_CONTRACT = "ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1"
PROVIDER_NOT_IMPLEMENTED = "CONNECTOR_RESISTANCE_PROVIDER_NOT_IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class AngleProviderResult:
    core_fingerprint: str
    provider_id: str
    status: str
    reason: str
    detail: object
    fingerprint: str
    contract: str = PROVIDER_CONTRACT


class AngleResistanceProvider(Protocol):
    """A future separately authorized provider need not modify the geometry core."""

    def evaluate(self, core: AngleCoreResult, context: object) -> AngleProviderResult: ...


def angle_provider_registry() -> Mapping[str, AngleResistanceProvider]:
    """The only implemented RC2 provider. No public registration or default fallback."""
    from frp_master_connection.calculation.frp_angle_connector_provider import (
        FRPAngleResistanceProvider,
    )

    return MappingProxyType({"FRP": FRPAngleResistanceProvider()})


def evaluate_angle_provider(
    core: AngleCoreResult,
    provider_key: str,
    context: object = None,
) -> AngleProviderResult:
    provider = angle_provider_registry().get(provider_key)
    if provider is None:
        return AngleProviderResult(
            core.fingerprint,
            provider_key,
            PROVIDER_NOT_IMPLEMENTED,
            "No resistance provider is authorized for this selection.",
            None,
            angle_fingerprint(
                (PROVIDER_CONTRACT, core.fingerprint, provider_key, PROVIDER_NOT_IMPLEMENTED)
            ),
        )
    return provider.evaluate(core, context)
