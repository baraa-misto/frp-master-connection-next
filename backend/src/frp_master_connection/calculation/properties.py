"""Material, fastener, and hardware snapshots for calculation planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
)
from frp_master_connection.calculation.sources import (
    QualificationStatus,
    SourceClassification,
)


class FRPPropertyKind(StrEnum):
    """Controlled material-property identities used by the first slice."""

    FT_L = "FT_L"
    FT_T = "FT_T"
    ET_L = "ET_L"
    ET_T = "ET_T"
    FC_L = "FC_L"
    FC_T = "FC_T"
    EC_L = "EC_L"
    EC_T = "EC_T"
    FSH_LT = "FSH_LT"
    G_LT = "G_LT"
    FSH_INT = "FSH_INT"
    FBR_L = "FBR_L"
    FBR_T = "FBR_T"
    PULL_THROUGH_3_8 = "PULL_THROUGH_3_8"
    PULL_THROUGH_1_2 = "PULL_THROUGH_1_2"
    PULL_THROUGH_3_4 = "PULL_THROUGH_3_4"
    NU_LT = "NU_LT"


class PropertyBehavior(StrEnum):
    """Material direction or behavior attached to a property value."""

    LONGITUDINAL = "LONGITUDINAL"
    TRANSVERSE = "TRANSVERSE"
    IN_PLANE_SHEAR = "IN_PLANE_SHEAR"
    INTERLAMINAR = "INTERLAMINAR"
    DISCRETE_PULL_THROUGH = "DISCRETE_PULL_THROUGH"
    DIMENSIONLESS_RATIO = "DIMENSIONLESS_RATIO"


_FORCE_PROPERTIES = {
    FRPPropertyKind.PULL_THROUGH_3_8,
    FRPPropertyKind.PULL_THROUGH_1_2,
    FRPPropertyKind.PULL_THROUGH_3_4,
}


@dataclass(frozen=True, slots=True)
class FRPPropertyEntry:
    """One immutable sourced material value."""

    kind: FRPPropertyKind
    value: PhysicalQuantity
    behavior: PropertyBehavior
    source_classification: SourceClassification
    qualification_status: QualificationStatus
    source_document: str
    source_revision: str
    applicability_metadata: tuple[str, ...] = ()
    engineer_notes: tuple[str, ...] = ()
    use_in_chapter_8_equations: bool = True

    def __post_init__(self) -> None:
        expected = (
            Dimension.DIMENSIONLESS
            if self.kind is FRPPropertyKind.NU_LT
            else Dimension.FORCE
            if self.kind in _FORCE_PROPERTIES
            else Dimension.STRESS
        )
        if self.value.dimension is not expected:
            raise ValueError(f"{self.kind.value} must have dimension {expected.value}.")
        if not self.source_document.strip() or not self.source_revision.strip():
            raise ValueError("Property source document and revision must be nonempty.")
        if not isinstance(self.applicability_metadata, tuple) or not isinstance(
            self.engineer_notes, tuple
        ):
            raise TypeError("Property metadata collections must be tuples.")


@dataclass(frozen=True, slots=True)
class MaterialPropertySnapshot:
    """One deterministic immutable material data snapshot."""

    id: str
    display_name: str
    locked: bool
    basis: SourceClassification
    qualification_statuses: tuple[QualificationStatus, ...]
    properties: tuple[FRPPropertyEntry, ...]
    explicitly_missing: tuple[FRPPropertyKind, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.display_name.strip():
            raise ValueError("Material snapshot identity and display name must be nonempty.")
        if not isinstance(self.properties, tuple) or not isinstance(self.explicitly_missing, tuple):
            raise TypeError("Material snapshot collections must be tuples.")
        kinds = [entry.kind for entry in self.properties]
        if len(kinds) != len(set(kinds)):
            raise ValueError("Material property kinds must be unique.")
        if len(self.explicitly_missing) != len(set(self.explicitly_missing)):
            raise ValueError("Explicitly missing property kinds must be unique.")
        if set(kinds) & set(self.explicitly_missing):
            raise ValueError("A property cannot be present and explicitly missing.")
        if tuple(sorted(self.properties, key=lambda entry: entry.kind.value)) != self.properties:
            raise ValueError("Material properties must use deterministic kind order.")
        if tuple(sorted(self.explicitly_missing, key=lambda kind: kind.value)) != (
            self.explicitly_missing
        ):
            raise ValueError("Missing property kinds must use deterministic order.")

    def lookup(self, kind: FRPPropertyKind) -> FRPPropertyEntry | None:
        """Return an exact value, explicit absence, or reject an undeclared kind."""

        for entry in self.properties:
            if entry.kind is kind:
                return entry
        if kind in self.explicitly_missing:
            return None
        raise KeyError(f"Property {kind.value!r} is not declared by snapshot {self.id!r}.")


def _ice_entry(
    kind: FRPPropertyKind,
    value: str,
    unit: Unit,
    behavior: PropertyBehavior,
    *,
    use_in_chapter_8_equations: bool = True,
) -> FRPPropertyEntry:
    return FRPPropertyEntry(
        kind=kind,
        value=PhysicalQuantity.of(value, unit),
        behavior=behavior,
        source_classification=SourceClassification.ENGINEER_APPROVED_DEVELOPMENT,
        qualification_status=QualificationStatus.DEVELOPMENT_ONLY,
        source_document="First Calculation Slice Engineering Specification - RC2",
        source_revision="RC2",
        applicability_metadata=("STAGE_2_1A_DEVELOPMENT_DATA",),
        engineer_notes=("Independent characteristic-basis verification remains required.",),
        use_in_chapter_8_equations=use_in_chapter_8_equations,
    )


def create_locked_ice_material_snapshot() -> MaterialPropertySnapshot:
    """Create the approved locked ICE development material without shared mutation."""

    entries = (
        _ice_entry(FRPPropertyKind.EC_L, "3000", Unit.KSI, PropertyBehavior.LONGITUDINAL),
        _ice_entry(FRPPropertyKind.EC_T, "1000", Unit.KSI, PropertyBehavior.TRANSVERSE),
        _ice_entry(FRPPropertyKind.ET_L, "3000", Unit.KSI, PropertyBehavior.LONGITUDINAL),
        _ice_entry(FRPPropertyKind.ET_T, "800", Unit.KSI, PropertyBehavior.TRANSVERSE),
        _ice_entry(FRPPropertyKind.FBR_L, "30", Unit.KSI, PropertyBehavior.LONGITUDINAL),
        _ice_entry(FRPPropertyKind.FBR_T, "18", Unit.KSI, PropertyBehavior.TRANSVERSE),
        _ice_entry(FRPPropertyKind.FC_L, "33", Unit.KSI, PropertyBehavior.LONGITUDINAL),
        _ice_entry(FRPPropertyKind.FSH_INT, "4.5", Unit.KSI, PropertyBehavior.INTERLAMINAR),
        _ice_entry(FRPPropertyKind.FSH_LT, "8", Unit.KSI, PropertyBehavior.IN_PLANE_SHEAR),
        _ice_entry(FRPPropertyKind.FT_L, "33", Unit.KSI, PropertyBehavior.LONGITUDINAL),
        _ice_entry(FRPPropertyKind.FT_T, "7.5", Unit.KSI, PropertyBehavior.TRANSVERSE),
        _ice_entry(FRPPropertyKind.G_LT, "420", Unit.KSI, PropertyBehavior.IN_PLANE_SHEAR),
        _ice_entry(
            FRPPropertyKind.NU_LT,
            "0.30",
            Unit.ONE,
            PropertyBehavior.DIMENSIONLESS_RATIO,
        ),
        _ice_entry(
            FRPPropertyKind.PULL_THROUGH_1_2,
            "0.90",
            Unit.KIP,
            PropertyBehavior.DISCRETE_PULL_THROUGH,
            use_in_chapter_8_equations=False,
        ),
        _ice_entry(
            FRPPropertyKind.PULL_THROUGH_3_4,
            "1.25",
            Unit.KIP,
            PropertyBehavior.DISCRETE_PULL_THROUGH,
            use_in_chapter_8_equations=False,
        ),
        _ice_entry(
            FRPPropertyKind.PULL_THROUGH_3_8,
            "0.65",
            Unit.KIP,
            PropertyBehavior.DISCRETE_PULL_THROUGH,
            use_in_chapter_8_equations=False,
        ),
    )
    return MaterialPropertySnapshot(
        id="ICE_LOCKED_PULTRUDED_FRP",
        display_name="ICE Locked Pultruded FRP",
        locked=True,
        basis=SourceClassification.ENGINEER_APPROVED_DEVELOPMENT,
        qualification_statuses=(
            QualificationStatus.DEVELOPMENT_ONLY,
            QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
        ),
        properties=tuple(sorted(entries, key=lambda entry: entry.kind.value)),
        explicitly_missing=(FRPPropertyKind.FC_T,),
    )


class ThreadStatus(StrEnum):
    """Whether threads intersect one explicitly identified physical location."""

    INCLUDED = "INCLUDED"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True, slots=True)
class ThreadStatusAssignment:
    """Thread status for one shear plane or one FRP bearing layer."""

    location_id: str
    status: ThreadStatus

    def __post_init__(self) -> None:
        if not self.location_id.strip():
            raise ValueError("Thread-status location identity must be nonempty.")
        if not isinstance(self.status, ThreadStatus):
            raise TypeError("Thread-status assignment requires a ThreadStatus.")


@dataclass(frozen=True, slots=True)
class WasherGeometry:
    """Explicit washer geometry and placement at both bolt ends."""

    outside_diameter: PhysicalQuantity
    thickness: PhysicalQuantity
    under_head: bool
    under_nut: bool

    def __post_init__(self) -> None:
        if self.outside_diameter.dimension is not Dimension.LENGTH or (
            self.thickness.dimension is not Dimension.LENGTH
        ):
            raise ValueError("Washer diameter and thickness must be lengths.")
        if self.outside_diameter.magnitude <= 0 or self.thickness.magnitude <= 0:
            raise ValueError("Washer geometry must be strictly positive.")


@dataclass(frozen=True, slots=True)
class FastenerSnapshot:
    """Immutable fastener source snapshot, separate from connection geometry."""

    id: str
    display_name: str
    locked: bool
    bolt_specification: str
    alloy_group: str
    alloys: tuple[str, ...]
    condition: str
    nut_specification: str
    washer_material_basis: str
    installation_condition: str
    diameter_min: PhysicalQuantity
    diameter_max: PhysicalQuantity
    fnt: PhysicalQuantity | None
    fnt_source_classification: SourceClassification
    fnt_qualification_status: QualificationStatus
    shear_plane_thread_statuses: tuple[ThreadStatusAssignment, ...]
    bearing_layer_thread_statuses: tuple[ThreadStatusAssignment, ...]
    number_of_shear_planes: int
    washer_geometry: WasherGeometry | None
    source_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        text_values = (
            self.id,
            self.display_name,
            self.bolt_specification,
            self.alloy_group,
            self.condition,
            self.nut_specification,
            self.washer_material_basis,
            self.installation_condition,
        )
        if any(not value.strip() for value in text_values) or not self.alloys:
            raise ValueError("Fastener identity and source metadata must be nonempty.")
        if self.diameter_min.dimension is not Dimension.LENGTH or (
            self.diameter_max.dimension is not Dimension.LENGTH
        ):
            raise ValueError("Fastener diameter limits must be lengths.")
        if self.diameter_min <= PhysicalQuantity.of(0, self.diameter_min.unit):
            raise ValueError("Fastener minimum diameter must be positive.")
        if self.diameter_max < self.diameter_min:
            raise ValueError("Fastener diameter range must be ordered.")
        if self.fnt is not None and self.fnt.dimension is not Dimension.STRESS:
            raise ValueError("Fastener Fnt must be a stress.")
        if isinstance(self.number_of_shear_planes, bool) or not isinstance(
            self.number_of_shear_planes, int
        ):
            raise TypeError("Number of shear planes must be an integer.")
        if self.number_of_shear_planes < 0:
            raise ValueError("Number of shear planes must be nonnegative.")
        if self.number_of_shear_planes != len(self.shear_plane_thread_statuses):
            raise ValueError("Each declared shear plane requires a separate thread status.")
        for assignments in (
            self.shear_plane_thread_statuses,
            self.bearing_layer_thread_statuses,
        ):
            ids = [assignment.location_id for assignment in assignments]
            if len(ids) != len(set(ids)):
                raise ValueError("Thread-status location identities must be unique by category.")
        if (
            self.fnt is None
            and self.fnt_source_classification is not SourceClassification.SOURCE_PENDING
        ):
            raise ValueError("An absent Fnt must retain SOURCE_PENDING classification.")


def create_locked_f593_fastener_snapshot() -> FastenerSnapshot:
    """Create the locked F593 Group 2 316/316L source-pending preset."""

    return FastenerSnapshot(
        id="ASTM_F593_17_GROUP_2_316_316L",
        display_name="316/316L Stainless-Steel Fastener System",
        locked=True,
        bolt_specification="ASTM F593-17",
        alloy_group="2",
        alloys=("316", "316L"),
        condition="COLD_WORKED_FASTENER_BASIS",
        nut_specification="ASTM F594-15",
        washer_material_basis="compatible 316/316L stainless steel",
        installation_condition="SNUG_TIGHT",
        diameter_min=PhysicalQuantity.of("0.375", Unit.IN),
        diameter_max=PhysicalQuantity.of("1.0", Unit.IN),
        fnt=None,
        fnt_source_classification=SourceClassification.SOURCE_PENDING,
        fnt_qualification_status=QualificationStatus.SOURCE_PENDING,
        shear_plane_thread_statuses=(),
        bearing_layer_thread_statuses=(),
        number_of_shear_planes=0,
        washer_geometry=None,
        source_notes=("No generic tensile strength is substituted.",),
    )


def create_synthetic_fastener_snapshot(
    *,
    id: str,
    fnt: PhysicalQuantity,
    source_classification: SourceClassification = SourceClassification.USER_DEFINED,
) -> FastenerSnapshot:
    """Create a non-F593 explicit-Fnt fixture/source snapshot."""

    if source_classification not in {
        SourceClassification.USER_DEFINED,
        SourceClassification.ENGINEER_APPROVED_DEVELOPMENT,
    }:
        raise ValueError(
            "Synthetic Fnt must be user-defined or engineer-approved development data."
        )
    return FastenerSnapshot(
        id=id,
        display_name="Explicit synthetic fastener",
        locked=False,
        bolt_specification="SYNTHETIC_NOT_ASTMF593_QUALIFIED",
        alloy_group="NOT_APPLICABLE",
        alloys=("SYNTHETIC",),
        condition="EXPLICIT_FIXTURE_INPUT",
        nut_specification="FIXTURE_ONLY",
        washer_material_basis="FIXTURE_ONLY",
        installation_condition="EXPLICIT_FIXTURE_INPUT",
        diameter_min=PhysicalQuantity.of("0.375", Unit.IN),
        diameter_max=PhysicalQuantity.of("1.0", Unit.IN),
        fnt=fnt,
        fnt_source_classification=source_classification,
        fnt_qualification_status=QualificationStatus.DEVELOPMENT_ONLY,
        shear_plane_thread_statuses=(),
        bearing_layer_thread_statuses=(),
        number_of_shear_planes=0,
        washer_geometry=None,
        source_notes=("Not the locked ASTM F593 preset.",),
    )


__all__ = (
    "FRPPropertyEntry",
    "FRPPropertyKind",
    "FastenerSnapshot",
    "MaterialPropertySnapshot",
    "PropertyBehavior",
    "ThreadStatus",
    "ThreadStatusAssignment",
    "WasherGeometry",
    "create_locked_f593_fastener_snapshot",
    "create_locked_ice_material_snapshot",
    "create_synthetic_fastener_snapshot",
)
