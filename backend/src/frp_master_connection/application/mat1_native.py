"""Typed MAT1 material adapter for existing FRP calculation primitives."""

from __future__ import annotations

from dataclasses import dataclass

from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    MaterialRecord,
    PropertyLedger,
    property_ledger,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyEntry,
    FRPPropertyKind,
    MaterialPropertySnapshot,
    PropertyBehavior,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import (
    QualificationStatus,
    SourceClassification,
)

_KIND: dict[str, FRPPropertyKind] = {
    "tensile_strength_L": FRPPropertyKind.FT_L,
    "tensile_strength_T": FRPPropertyKind.FT_T,
    "tensile_modulus_L": FRPPropertyKind.ET_L,
    "tensile_modulus_T": FRPPropertyKind.ET_T,
    "compressive_strength_L": FRPPropertyKind.FC_L,
    "compressive_modulus_L": FRPPropertyKind.EC_L,
    "compressive_modulus_T": FRPPropertyKind.EC_T,
    "in_plane_shear_strength_LT": FRPPropertyKind.FSH_LT,
    "in_plane_shear_modulus_LT": FRPPropertyKind.G_LT,
    "interlaminar_shear_strength": FRPPropertyKind.FSH_INT,
    "bearing_strength_L": FRPPropertyKind.FBR_L,
    "bearing_strength_T": FRPPropertyKind.FBR_T,
    "pull_through_3_8_as_labeled": FRPPropertyKind.PULL_THROUGH_3_8,
    "pull_through_1_2_as_labeled": FRPPropertyKind.PULL_THROUGH_1_2,
    "pull_through_3_4_as_labeled": FRPPropertyKind.PULL_THROUGH_3_4,
    "major_poisson_ratio_LT": FRPPropertyKind.NU_LT,
}
_BEHAVIOR: dict[FRPPropertyKind, PropertyBehavior] = {
    FRPPropertyKind.FT_L: PropertyBehavior.LONGITUDINAL,
    FRPPropertyKind.ET_L: PropertyBehavior.LONGITUDINAL,
    FRPPropertyKind.FC_L: PropertyBehavior.LONGITUDINAL,
    FRPPropertyKind.EC_L: PropertyBehavior.LONGITUDINAL,
    FRPPropertyKind.FBR_L: PropertyBehavior.LONGITUDINAL,
    FRPPropertyKind.FT_T: PropertyBehavior.TRANSVERSE,
    FRPPropertyKind.ET_T: PropertyBehavior.TRANSVERSE,
    FRPPropertyKind.EC_T: PropertyBehavior.TRANSVERSE,
    FRPPropertyKind.FBR_T: PropertyBehavior.TRANSVERSE,
    FRPPropertyKind.FSH_LT: PropertyBehavior.IN_PLANE_SHEAR,
    FRPPropertyKind.G_LT: PropertyBehavior.IN_PLANE_SHEAR,
    FRPPropertyKind.FSH_INT: PropertyBehavior.INTERLAMINAR,
    FRPPropertyKind.PULL_THROUGH_3_8: PropertyBehavior.DISCRETE_PULL_THROUGH,
    FRPPropertyKind.PULL_THROUGH_1_2: PropertyBehavior.DISCRETE_PULL_THROUGH,
    FRPPropertyKind.PULL_THROUGH_3_4: PropertyBehavior.DISCRETE_PULL_THROUGH,
    FRPPropertyKind.NU_LT: PropertyBehavior.DIMENSIONLESS_RATIO,
}
_PULL_THROUGH = {
    FRPPropertyKind.PULL_THROUGH_3_8,
    FRPPropertyKind.PULL_THROUGH_1_2,
    FRPPropertyKind.PULL_THROUGH_3_4,
}


@dataclass(frozen=True, slots=True)
class NativeMaterialAdapter:
    original: MaterialRecord
    adjusted_snapshot: MaterialPropertySnapshot
    ledgers: tuple[PropertyLedger, ...]
    unresolved_issues: tuple[str, ...]


def adapt_native_material(
    component_id: str, record: MaterialRecord, conditions: DesignConditions
) -> NativeMaterialAdapter:
    """Pass source-bound numeric candidates into native typed checks once.

    Where a candidate cannot be established, retain the declared source value
    solely for partial numeric diagnostics and keep its issue in the result.
    The caller must block a complete PASS whenever unresolved_issues is nonempty.
    """

    if conditions.source_reference_condition == "ALREADY_ADJUSTED":
        raise ValueError("MAT1_ALREADY_ADJUSTED_SOURCE_REQUIRES_NON_DUPLICATING_ADAPTER")
    if any(item.basis == "ALREADY_ADJUSTED" and item.id in _KIND for item in record.properties):
        raise ValueError("MAT1_ALREADY_ADJUSTED_PROPERTY_REQUIRES_NON_DUPLICATING_ADAPTER")

    entries: list[FRPPropertyEntry] = []
    ledgers: list[PropertyLedger] = []
    issues: list[str] = []
    for prop in record.properties:
        kind = _KIND.get(prop.id)
        if kind is None:
            continue
        ledger = property_ledger(component_id, record, prop.id, conditions)
        ledgers.append(ledger)
        issues.extend(ledger.issues)
        unit = Unit.ONE if prop.unit == "dimensionless" else Unit(prop.unit)
        value = (
            ledger.adjusted_candidate if ledger.adjusted_candidate is not None else prop.original
        )
        entries.append(
            FRPPropertyEntry(
                kind=kind,
                value=PhysicalQuantity.of(value, unit),
                behavior=_BEHAVIOR[kind],
                source_classification=SourceClassification.SOURCE_PENDING,
                qualification_status=QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
                source_document=prop.source_locator,
                source_revision=f"{record.revision}:{record.content_digest}",
                applicability_metadata=prop.applicability,
                engineer_notes=(
                    "MAT1 numerical candidate; original source and factors retained in ledger.",
                ),
                use_in_chapter_8_equations=kind not in _PULL_THROUGH,
            )
        )
    missing = tuple(
        sorted(
            set(FRPPropertyKind) - {entry.kind for entry in entries},
            key=lambda kind: kind.value,
        )
    )
    snapshot = MaterialPropertySnapshot(
        id=record.id,
        display_name=record.display_name,
        locked=record.source_kind != "USER_SUPPLIED_SESSION_DATA",
        basis=SourceClassification.SOURCE_PENDING,
        qualification_statuses=(
            QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
            QualificationStatus.SOURCE_PENDING,
        ),
        properties=tuple(sorted(entries, key=lambda entry: entry.kind.value)),
        explicitly_missing=missing,
    )
    return NativeMaterialAdapter(record, snapshot, tuple(ledgers), tuple(dict.fromkeys(issues)))
