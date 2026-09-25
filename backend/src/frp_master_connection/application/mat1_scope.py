"""Request-local MAT1 bindings for legacy orchestration successor routes.

Only the versioned MAT1 API enters this scope. Legacy requests see their exact
original material and time-effect paths, including their historical fingerprints.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    MaterialRecord,
    PropertyLedger,
)
from frp_master_connection.application.mat1_native import adapt_native_material
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.properties import MaterialPropertySnapshot

Assignment = tuple[MaterialRecord, DesignConditions]


@dataclass(slots=True)
class MAT1Scope:
    default: Assignment
    overrides: Mapping[str, Assignment]
    family_id: str = ""
    canonical_owners: frozenset[str] | None = None
    adapters: dict[str, MaterialPropertySnapshot] = field(default_factory=dict)
    ledgers: list[PropertyLedger] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def _owner(self, name: str) -> str:
        owners = self.canonical_owners
        if owners is None or name in owners:
            return name
        if name == "tee-brace" and self.family_id == "multi-member-tee":
            slot = _ACTIVE_TEE_SLOT.get()
            if slot is not None and slot in owners:
                return slot
            raise ValueError("MAT1_TEE_BRACE_REQUIRES_ACTIVE_SLOT")
        if name.startswith("BEAM_A_") and "BEAM_A" in owners:
            return "BEAM_A"
        if name.startswith("BEAM_B_") and "BEAM_B" in owners:
            return "BEAM_B"
        if self.family_id in {
            "wi-beam-concrete-wall-moment",
            "wi-beam-frp-support-moment",
        }:
            if name in {"BEAM", "WI_TOP_FLANGE", "WI_BOTTOM_FLANGE"}:
                return "WI_BEAM"
            if name == "SUPPORT" and "FRP_SUPPORT" in owners:
                return "FRP_SUPPORT"
        if name == "single-clip-angle-connector" and {
            "POSITIVE_CLIP_ANGLE",
            "NEGATIVE_CLIP_ANGLE",
        }.issubset(owners):
            if self.material("POSITIVE_CLIP_ANGLE") != self.material("NEGATIVE_CLIP_ANGLE"):
                raise ValueError("MAT1_PAIRED_CLIP_ANGLE_MATERIALS_MUST_MATCH")
            return "POSITIVE_CLIP_ANGLE"
        if name == "clip-angle-support" and self.family_id == "beam-concrete-paired-angle":
            raise ValueError("MAT1_CONCRETE_INTERFACE_NON_FRP_ADAPTER_REQUIRED")
        raise ValueError(f"MAT1_UNMAPPED_PHYSICAL_OWNER:{name}")

    def material(self, owner_id: str) -> MaterialPropertySnapshot:
        owner_id = self._owner(owner_id)
        if owner_id not in self.adapters:
            record, conditions = self.overrides.get(owner_id, self.default)
            adapted = adapt_native_material(owner_id, record, conditions)
            self.adapters[owner_id] = adapted.adjusted_snapshot
            self.ledgers.extend(adapted.ledgers)
            self.issues.extend(adapted.unresolved_issues)
        return self.adapters[owner_id]

    def unconsumed_overrides(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.overrides) - set(self.adapters)))


_ACTIVE: ContextVar[MAT1Scope | None] = ContextVar("MAT1_ACTIVE_SCOPE", default=None)
_ACTIVE_TEE_SLOT: ContextVar[str | None] = ContextVar("MAT1_ACTIVE_TEE_SLOT", default=None)


@contextmanager
def bind_mat1_scope(scope: MAT1Scope) -> Iterator[MAT1Scope]:
    token = _ACTIVE.set(scope)
    try:
        yield scope
    finally:
        _ACTIVE.reset(token)


@contextmanager
def bind_mat1_tee_slot(owner_id: str) -> Iterator[None]:
    """Identify the physical brace while the legacy Tee interface is evaluated."""

    token = _ACTIVE_TEE_SLOT.set(owner_id)
    try:
        yield
    finally:
        _ACTIVE_TEE_SLOT.reset(token)


def material_for_owner(owner_id: str, legacy: MaterialPropertySnapshot) -> MaterialPropertySnapshot:
    active = _ACTIVE.get()
    return legacy if active is None else active.material(owner_id)


def time_category_for_case(legacy: TimeEffectCategory) -> TimeEffectCategory:
    active = _ACTIVE.get()
    return legacy if active is None else active.default[1].time_category


def current_scope() -> MAT1Scope | None:
    """Inspect the active successor scope without creating persistent state."""

    return _ACTIVE.get()
