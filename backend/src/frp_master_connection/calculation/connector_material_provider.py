"""Provider-independent dispatch; no stainless numerical implementation in CME-1."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from frp_master_connection.domain.connector_materials import (
    CanonicalComponent,
    ComponentRole,
    ConnectorMaterial,
    Fabrication,
    MaterialDescriptor,
)


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    provider_id: str
    material: ConnectorMaterial
    body_forms: tuple[str, ...]
    fabrication: tuple[Fabrication, ...]
    method: str


class ConnectorProvider(Protocol):
    @property
    def capability(self) -> ProviderCapability: ...

    def evaluate(self, native_input: object) -> object: ...


@dataclass(frozen=True, slots=True)
class NativeFRPAdapter[T]:
    """Return the original native result, including native arithmetic/fingerprint."""

    capability: ProviderCapability
    input_type: type[T]
    native: Callable[[T], object]

    def evaluate(self, native_input: object) -> object:
        if not isinstance(native_input, self.input_type):
            raise TypeError("Wrong native input type for the declared FRP method")
        return self.native(native_input)


@dataclass(frozen=True, slots=True)
class ProviderDispatch:
    provider_id: str | None
    status: str
    native_result: object | None
    capacity: None = None
    utilization: None = None


def provider_registry(providers: tuple[ConnectorProvider, ...]) -> Mapping[str, ConnectorProvider]:
    registry = {p.capability.provider_id: p for p in providers}
    if len(registry) != len(providers):
        raise ValueError("Duplicate provider identity")
    return MappingProxyType(registry)


def dispatch_connector_provider(
    component: CanonicalComponent,
    material: MaterialDescriptor,
    provider_id: str,
    method: str,
    native_input: object,
    registry: Mapping[str, ConnectorProvider],
) -> ProviderDispatch:
    if component.role is not ComponentRole.CONNECTOR_BODY:
        raise ValueError("Connector resistance cannot override a protected component role")
    # This guard also applies to injected registries: synthetic stainless sources
    # cannot accidentally enable a production steel calculation in this phase.
    if material.family is ConnectorMaterial.SS316:
        return ProviderDispatch(None, "PROVIDER_NOT_IMPLEMENTED", None)
    provider = registry.get(provider_id)
    if provider is None:
        return ProviderDispatch(None, "PROVIDER_NOT_IMPLEMENTED", None)
    capability = provider.capability
    if (
        capability.material is not material.family
        or component.body_form not in capability.body_forms
        or material.fabrication not in capability.fabrication
        or method != capability.method
    ):
        return ProviderDispatch(provider_id, "PROVIDER_NOT_APPLICABLE", None)
    return ProviderDispatch(
        provider_id, "NATIVE_RESULT_UNMODIFIED", provider.evaluate(native_input)
    )
