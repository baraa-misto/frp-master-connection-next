"""Stage 3.1 adapters into unchanged Stage 2 material and fastener contracts.

This module deliberately performs no resistance calculation.  It resolves only the
strict legacy material-pair identity and whether a Stage 3 fastener system may hand
an accepted Stage 2 fastener snapshot to the existing metallic-bolt equation family.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.calculation.multirow import ConnectedMaterialPair
from frp_master_connection.calculation.properties import FastenerSnapshot
from frp_master_connection.domain.material_architecture import (
    ConnectorMaterialFamily,
    FastenerMaterialFamily,
    FastenerSystem,
    ResistanceCalculationFamily,
)

_CONNECTOR_METAL_FAMILIES = frozenset(
    {
        ConnectorMaterialFamily.STAINLESS_STEEL_316,
        ConnectorMaterialFamily.CARBON_STEEL,
    }
)
_FASTENER_METAL_FAMILIES = frozenset(
    {
        FastenerMaterialFamily.STAINLESS_STEEL_316,
        FastenerMaterialFamily.CARBON_STEEL,
    }
)


@dataclass(frozen=True, slots=True)
class LegacyMaterialPairResolution:
    """Exact Stage 3 families plus their narrow, unchanged Stage 2 pair identity."""

    participant_a: ConnectorMaterialFamily
    participant_b: ConnectorMaterialFamily
    legacy_pair: ConnectedMaterialPair
    metal_subtype: ConnectorMaterialFamily | None

    def __post_init__(self) -> None:
        if not isinstance(self.participant_a, ConnectorMaterialFamily) or not isinstance(
            self.participant_b, ConnectorMaterialFamily
        ):
            raise TypeError(
                "Legacy material-pair participants must be connector material families."
            )
        if not isinstance(self.legacy_pair, ConnectedMaterialPair):
            raise TypeError("legacy_pair must be an unchanged ConnectedMaterialPair value.")
        if self.metal_subtype is not None and self.metal_subtype not in _CONNECTOR_METAL_FAMILIES:
            raise ValueError("metal_subtype must be an exact supported connector metal family.")

        expected_pair, expected_metal = _expected_legacy_pair(
            self.participant_a,
            self.participant_b,
        )
        if self.legacy_pair is not expected_pair or self.metal_subtype is not expected_metal:
            raise ValueError("Stored legacy material-pair resolution is inconsistent.")


def _expected_legacy_pair(
    participant_a: ConnectorMaterialFamily,
    participant_b: ConnectorMaterialFamily,
) -> tuple[ConnectedMaterialPair, ConnectorMaterialFamily | None]:
    frp = ConnectorMaterialFamily.PULTRUDED_FRP
    if participant_a is frp and participant_b is frp:
        return ConnectedMaterialPair.FRP_FRP, None
    if participant_a is frp and participant_b in _CONNECTOR_METAL_FAMILIES:
        return ConnectedMaterialPair.FRP_STEEL, participant_b
    if participant_b is frp and participant_a in _CONNECTOR_METAL_FAMILIES:
        return ConnectedMaterialPair.FRP_STEEL, participant_a
    raise ValueError("No legacy material-pair mapping exists for these exact material families.")


def resolve_legacy_material_pair(
    participant_a: ConnectorMaterialFamily,
    participant_b: ConnectorMaterialFamily,
) -> LegacyMaterialPairResolution:
    """Resolve only FRP/FRP or FRP/supported-metal pairs without a fallback."""

    if not isinstance(participant_a, ConnectorMaterialFamily) or not isinstance(
        participant_b, ConnectorMaterialFamily
    ):
        raise TypeError("Material-pair resolution requires exact ConnectorMaterialFamily values.")
    legacy_pair, metal_subtype = _expected_legacy_pair(participant_a, participant_b)
    return LegacyMaterialPairResolution(
        participant_a,
        participant_b,
        legacy_pair,
        metal_subtype,
    )


class ExistingMetallicBoltEligibilityStatus(StrEnum):
    """Fail-closed reasons for the Stage 3-to-Stage 2 metallic-bolt boundary."""

    ELIGIBLE = "ELIGIBLE"
    BLOCKED_CUSTOM_FRP_MATERIAL = "BLOCKED_CUSTOM_FRP_MATERIAL"
    BLOCKED_AUTHORITATIVE_GEOMETRY_REQUIRED = "BLOCKED_AUTHORITATIVE_GEOMETRY_REQUIRED"
    BLOCKED_EXISTING_METALLIC_AUTHORITY_REQUIRED = "BLOCKED_EXISTING_METALLIC_AUTHORITY_REQUIRED"
    BLOCKED_PROPERTY_SNAPSHOT_ID_REQUIRED = "BLOCKED_PROPERTY_SNAPSHOT_ID_REQUIRED"
    BLOCKED_PROPERTY_SNAPSHOT_REQUIRED = "BLOCKED_PROPERTY_SNAPSHOT_REQUIRED"
    BLOCKED_PROPERTY_SNAPSHOT_ID_MISMATCH = "BLOCKED_PROPERTY_SNAPSHOT_ID_MISMATCH"
    BLOCKED_EXPLICIT_FNT_REQUIRED = "BLOCKED_EXPLICIT_FNT_REQUIRED"
    BLOCKED_POSITIVE_FNT_REQUIRED = "BLOCKED_POSITIVE_FNT_REQUIRED"


@dataclass(frozen=True, slots=True)
class ExistingMetallicBoltEligibilityResult:
    """Eligibility evidence that exposes a Stage 2 snapshot only when authorized."""

    fastener_system_id: str
    material_family: FastenerMaterialFamily
    status: ExistingMetallicBoltEligibilityStatus
    expected_snapshot_id: str | None
    provided_snapshot_id: str | None
    eligible_snapshot: FastenerSnapshot | None = None

    def __post_init__(self) -> None:
        if not self.fastener_system_id.strip():
            raise ValueError("fastener_system_id must be nonempty.")
        if not isinstance(self.material_family, FastenerMaterialFamily):
            raise TypeError("material_family must be a FastenerMaterialFamily.")
        if not isinstance(self.status, ExistingMetallicBoltEligibilityStatus):
            raise TypeError("status must be an ExistingMetallicBoltEligibilityStatus.")
        for name, value in (
            ("expected_snapshot_id", self.expected_snapshot_id),
            ("provided_snapshot_id", self.provided_snapshot_id),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{name} must be absent or nonempty.")

        eligible = self.status is ExistingMetallicBoltEligibilityStatus.ELIGIBLE
        if eligible:
            if self.material_family not in _FASTENER_METAL_FAMILIES:
                raise ValueError("Only a supported metallic family can be eligible.")
            if not isinstance(self.eligible_snapshot, FastenerSnapshot):
                raise TypeError("Eligible metallic-bolt status requires a FastenerSnapshot.")
            if (
                self.expected_snapshot_id is None
                or self.provided_snapshot_id != self.expected_snapshot_id
                or self.eligible_snapshot.id != self.expected_snapshot_id
            ):
                raise ValueError("Eligible metallic-bolt snapshot identities must match exactly.")
            if self.eligible_snapshot.fnt is None or self.eligible_snapshot.fnt.magnitude <= 0:
                raise ValueError("Eligible metallic-bolt snapshot requires positive explicit Fnt.")
        elif self.eligible_snapshot is not None:
            raise ValueError("A blocked metallic-bolt result must not expose a Stage 2 snapshot.")

    @property
    def is_eligible(self) -> bool:
        """Return whether the existing metallic-bolt family may consume the snapshot."""

        return self.status is ExistingMetallicBoltEligibilityStatus.ELIGIBLE


def _eligibility_result(
    system: FastenerSystem,
    status: ExistingMetallicBoltEligibilityStatus,
    supplied_snapshot: FastenerSnapshot | None,
    *,
    eligible_snapshot: FastenerSnapshot | None = None,
) -> ExistingMetallicBoltEligibilityResult:
    return ExistingMetallicBoltEligibilityResult(
        fastener_system_id=system.system_id,
        material_family=system.material.family,
        status=status,
        expected_snapshot_id=system.engineering_property_snapshot_id,
        provided_snapshot_id=None if supplied_snapshot is None else supplied_snapshot.id,
        eligible_snapshot=eligible_snapshot,
    )


def resolve_existing_metallic_bolt_eligibility(
    system: FastenerSystem,
    property_snapshot: FastenerSnapshot | None,
) -> ExistingMetallicBoltEligibilityResult:
    """Fail closed unless a supported metal has every accepted Stage 2 prerequisite."""

    if not isinstance(system, FastenerSystem):
        raise TypeError("system must be a FastenerSystem.")
    if property_snapshot is not None and not isinstance(property_snapshot, FastenerSnapshot):
        raise TypeError("property_snapshot must be a FastenerSnapshot or None.")

    family = system.material.family
    if family is FastenerMaterialFamily.CUSTOM_FRP:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_CUSTOM_FRP_MATERIAL,
            property_snapshot,
        )
    if family not in _FASTENER_METAL_FAMILIES:
        raise ValueError("Unsupported fastener material family cannot use the metallic-bolt path.")
    if not system.geometry.authoritative:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_AUTHORITATIVE_GEOMETRY_REQUIRED,
            property_snapshot,
        )
    if not system.resistance_authority.permits(ResistanceCalculationFamily.EXISTING_METALLIC_BOLT):
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_EXISTING_METALLIC_AUTHORITY_REQUIRED,
            property_snapshot,
        )
    expected_id = system.engineering_property_snapshot_id
    if expected_id is None:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_ID_REQUIRED,
            property_snapshot,
        )
    if property_snapshot is None:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_REQUIRED,
            None,
        )
    if property_snapshot.id != expected_id:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_ID_MISMATCH,
            property_snapshot,
        )
    if property_snapshot.fnt is None:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_EXPLICIT_FNT_REQUIRED,
            property_snapshot,
        )
    if property_snapshot.fnt.magnitude <= 0:
        return _eligibility_result(
            system,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_POSITIVE_FNT_REQUIRED,
            property_snapshot,
        )
    return _eligibility_result(
        system,
        ExistingMetallicBoltEligibilityStatus.ELIGIBLE,
        property_snapshot,
        eligible_snapshot=property_snapshot,
    )


__all__ = (
    "ExistingMetallicBoltEligibilityResult",
    "ExistingMetallicBoltEligibilityStatus",
    "LegacyMaterialPairResolution",
    "resolve_existing_metallic_bolt_eligibility",
    "resolve_legacy_material_pair",
)
