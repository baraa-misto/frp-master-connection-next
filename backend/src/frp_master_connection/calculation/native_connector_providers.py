"""The accepted CS7 FRP provider exposed through the shared CME capability protocol."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from frp_master_connection.calculation.angle_connector_core import AngleCoreResult
from frp_master_connection.calculation.angle_connector_providers import evaluate_angle_provider
from frp_master_connection.calculation.connector_material_provider import (
    ConnectorProvider,
    NativeFRPAdapter,
    ProviderCapability,
    provider_registry,
)
from frp_master_connection.domain.connector_materials import ConnectorMaterial, Fabrication


@dataclass(frozen=True, slots=True)
class NativeAngleInput:
    core: AngleCoreResult
    context: object


def _native_angle(value: NativeAngleInput) -> object:
    return evaluate_angle_provider(value.core, "FRP", value.context)


def native_connector_providers() -> Mapping[str, ConnectorProvider]:
    return provider_registry(
        (
            NativeFRPAdapter(
                ProviderCapability(
                    "CS7_FRP",
                    ConnectorMaterial.FRP,
                    ("ANGLE",),
                    (Fabrication.PULTRUDED,),
                    "ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1",
                ),
                NativeAngleInput,
                _native_angle,
            ),
        )
    )
