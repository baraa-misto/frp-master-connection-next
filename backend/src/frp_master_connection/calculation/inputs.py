"""Factor and resolved-demand input contracts for Stage 2.1A planning."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_from_finite_real,
    decimal_value,
)
from frp_master_connection.domain.values import PositionVector3D
from frp_master_connection.geometry.spatial import CartesianFrame3D, Vector3D


class TimeEffectCategory(StrEnum):
    """Table 2-1 time-effect categories retained as explicit selections."""

    DEAD_ONLY = "DEAD_ONLY"
    IMPACT = "IMPACT"
    STORAGE = "STORAGE"
    LONG_TERM_OPERATING = "LONG_TERM_OPERATING"
    OTHER_LIVE = "OTHER_LIVE"
    SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE = "SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE"
    WIND_TORNADO_SEISMIC = "WIND_TORNADO_SEISMIC"


_TIME_EFFECT_VALUES = {
    TimeEffectCategory.DEAD_ONLY: Decimal("0.4"),
    TimeEffectCategory.IMPACT: Decimal("1.0"),
    TimeEffectCategory.STORAGE: Decimal("0.6"),
    TimeEffectCategory.LONG_TERM_OPERATING: Decimal("0.4"),
    TimeEffectCategory.OTHER_LIVE: Decimal("0.8"),
    TimeEffectCategory.SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE: Decimal("0.75"),
    TimeEffectCategory.WIND_TORNADO_SEISMIC: Decimal("1.0"),
}


@dataclass(frozen=True, slots=True)
class TimeEffectFactor:
    """An explicit time-effect selection; never inferred from a combination name."""

    category: TimeEffectCategory
    value: Decimal
    source_reference: str
    notes: tuple[str, ...] = ()
    approved_override_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.category, TimeEffectCategory):
            raise TypeError("Time-effect category must be a TimeEffectCategory.")
        object.__setattr__(self, "value", decimal_value(self.value))
        if self.value <= 0:
            raise ValueError("A time-effect factor must be strictly positive.")
        if not self.source_reference.strip():
            raise ValueError("A time-effect source reference is required.")
        if not isinstance(self.notes, tuple):
            raise TypeError("Time-effect notes must be an immutable tuple.")
        if self.approved_override_id is None and self.value != _TIME_EFFECT_VALUES[self.category]:
            raise ValueError(
                "A non-tabulated time-effect value requires approved override metadata."
            )


def select_time_effect_factor(category: TimeEffectCategory) -> TimeEffectFactor:
    """Select the approved value without combination-name inference or exceptions."""

    if not isinstance(category, TimeEffectCategory):
        raise TypeError("category must be a TimeEffectCategory.")
    return TimeEffectFactor(category, _TIME_EFFECT_VALUES[category], "ASCE/SEI 74-23 Table 2-1")


@dataclass(frozen=True, slots=True)
class EndUseFactors:
    """Explicit moisture, temperature, and chemical end-use factors."""

    cm: Decimal
    ct: Decimal
    cch: Decimal
    source_reference: str
    approval_metadata: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("cm", "ct", "cch"):
            value = decimal_value(getattr(self, field_name))
            if value <= 0:
                raise ValueError("End-use factors must be strictly positive.")
            object.__setattr__(self, field_name, value)
        if not isinstance(self.approval_metadata, tuple):
            raise TypeError("End-use approval metadata must be an immutable tuple.")
        if not self.source_reference.strip() or not self.approval_metadata:
            raise ValueError("Issued end-use factors require source and approval metadata.")


class LapConfiguration(StrEnum):
    """Controlled lap configuration for applicability metadata."""

    DOUBLE_LAP = "DOUBLE_LAP"
    SINGLE_LAP = "SINGLE_LAP"


@dataclass(frozen=True, slots=True)
class LapFactorPlan:
    """Stored lap metadata; Stage 2.1A never applies it to resistance."""

    configuration: LapConfiguration
    applicable_in_plane_frp_factor: Decimal
    applies_to_metallic_bolt: bool = False
    applies_to_pull_through: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, LapConfiguration):
            raise TypeError("Lap-factor configuration must be a LapConfiguration.")
        object.__setattr__(
            self,
            "applicable_in_plane_frp_factor",
            decimal_value(self.applicable_in_plane_frp_factor),
        )
        expected = (
            Decimal("1.0") if self.configuration is LapConfiguration.DOUBLE_LAP else Decimal("0.60")
        )
        if self.applicable_in_plane_frp_factor != expected:
            raise ValueError("Lap factor metadata does not match its controlled configuration.")
        if self.applies_to_metallic_bolt or self.applies_to_pull_through:
            raise ValueError("The first-slice lap factor excludes bolt and pull-through checks.")


def create_lap_factor_plan(configuration: LapConfiguration) -> LapFactorPlan:
    if not isinstance(configuration, LapConfiguration):
        raise TypeError("configuration must be a LapConfiguration.")
    factor = "1.0" if configuration is LapConfiguration.DOUBLE_LAP else "0.60"
    return LapFactorPlan(configuration, Decimal(factor))


@dataclass(frozen=True, slots=True)
class GeometryFactorPlan:
    """C-delta planning metadata for the one-bolt/one-row first slice."""

    bolt_count_in_row: int
    row_count: int
    pitch: PhysicalQuantity | None
    planning_value: Decimal
    applied_to_resistance: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.bolt_count_in_row, bool) or not isinstance(self.bolt_count_in_row, int):
            raise TypeError("bolt_count_in_row must be an integer.")
        if isinstance(self.row_count, bool) or not isinstance(self.row_count, int):
            raise TypeError("row_count must be an integer.")
        if self.bolt_count_in_row < 1 or self.row_count < 1:
            raise ValueError("Bolt and row counts must be positive.")
        if self.pitch is not None and self.pitch.dimension is not Dimension.LENGTH:
            raise ValueError("Geometry-factor pitch must be a length when present.")
        object.__setattr__(self, "planning_value", decimal_value(self.planning_value))
        if (
            self.bolt_count_in_row == 1
            and self.row_count == 1
            and (self.pitch is not None or self.planning_value != Decimal("1.0"))
        ):
            raise ValueError("One bolt/one row requires no pitch and C-delta planning value 1.0.")
        if self.applied_to_resistance:
            raise ValueError("Stage 2.1A cannot apply C-delta to resistance.")


def create_single_bolt_geometry_factor_plan() -> GeometryFactorPlan:
    return GeometryFactorPlan(1, 1, None, Decimal("1.0"))


class DemandSourceKind(StrEnum):
    """How the bolt demand reached the planning contract."""

    EXPLICIT_RESOLVED_BOLT_DEMAND = "EXPLICIT_RESOLVED_BOLT_DEMAND"
    MEMBER_END_ACTION_UNDISTRIBUTED = "MEMBER_END_ACTION_UNDISTRIBUTED"
    EXTERNAL_APPROVED_METHOD = "EXTERNAL_APPROVED_METHOD"


class DemandDistributionStatus(StrEnum):
    """Explicit status of bolt-demand resolution/distribution."""

    EXPLICITLY_RESOLVED = "EXPLICITLY_RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    EXTERNAL_METHOD_APPROVED = "EXTERNAL_METHOD_APPROVED"


class LayerLoadingSense(StrEnum):
    """Signed connection-force sense acting on the checked layer."""

    TENSION = "TENSION"
    COMPRESSION = "COMPRESSION"


class PultrudedElementForm(StrEnum):
    """Approved net-section coefficient family for one checked FRP layer."""

    SHAPE_ELEMENT = "SHAPE_ELEMENT"
    PLATE = "PLATE"


@dataclass(frozen=True, slots=True)
class ResolvedSingleBoltDemand:
    """Resolved demand provenance without shift, distribution, or prying invention."""

    id: str
    load_combination_id: str
    source_member_id: str
    source_action_id: str
    source_kind: DemandSourceKind
    factored_action_confirmed: bool
    coordinate_frame_reference: str
    resolved_frame: CartesianFrame3D
    source_reference_point_id: str
    resolved_global_reference_point: PositionVector3D
    in_plane_force_vector: Vector3D
    force_vector_unit: Unit
    bolt_axis_tensile_demand: PhysicalQuantity
    externally_supplied_prying_demand: PhysicalQuantity
    loading_sense: LayerLoadingSense
    provenance: tuple[str, ...]
    distribution_status: DemandDistributionStatus

    def __post_init__(self) -> None:
        identities = (
            self.id,
            self.load_combination_id,
            self.source_member_id,
            self.source_action_id,
            self.coordinate_frame_reference,
            self.source_reference_point_id,
        )
        if any(not identity.strip() for identity in identities):
            raise ValueError("Demand identities and references must be nonempty.")
        if not isinstance(self.resolved_frame, CartesianFrame3D):
            raise TypeError("resolved_frame must be a CartesianFrame3D.")
        if not isinstance(self.resolved_global_reference_point, PositionVector3D):
            raise TypeError("resolved_global_reference_point must be a PositionVector3D.")
        if not isinstance(self.in_plane_force_vector, Vector3D):
            raise TypeError("in_plane_force_vector must be a Vector3D.")
        if not isinstance(self.source_kind, DemandSourceKind):
            raise TypeError("source_kind must be a DemandSourceKind.")
        if not isinstance(self.factored_action_confirmed, bool):
            raise TypeError("factored_action_confirmed must be Boolean.")
        if not isinstance(self.loading_sense, LayerLoadingSense):
            raise TypeError("loading_sense must be a LayerLoadingSense.")
        if not isinstance(self.distribution_status, DemandDistributionStatus):
            raise TypeError("distribution_status must be a DemandDistributionStatus.")
        if self.force_vector_unit not in {Unit.LBF, Unit.KIP, Unit.N, Unit.KN}:
            raise ValueError("force_vector_unit must have force dimension.")
        demands = (self.bolt_axis_tensile_demand, self.externally_supplied_prying_demand)
        if any(value.dimension is not Dimension.FORCE for value in demands):
            raise ValueError("Bolt-axis and prying demands must be forces.")
        if any(value.magnitude < 0 for value in demands):
            raise ValueError("Bolt-axis and prying tensile demands must be nonnegative.")
        expected_distribution = {
            DemandSourceKind.EXPLICIT_RESOLVED_BOLT_DEMAND: (
                DemandDistributionStatus.EXPLICITLY_RESOLVED
            ),
            DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED: (DemandDistributionStatus.UNRESOLVED),
            DemandSourceKind.EXTERNAL_APPROVED_METHOD: (
                DemandDistributionStatus.EXTERNAL_METHOD_APPROVED
            ),
        }[self.source_kind]
        if self.distribution_status is not expected_distribution:
            raise ValueError("Demand source and distribution status are inconsistent.")
        if not isinstance(self.provenance, tuple):
            raise TypeError("Demand provenance must be an immutable tuple.")
        if not self.provenance:
            raise ValueError("Demand provenance is required.")

    @property
    def in_plane_force_magnitude(self) -> PhysicalQuantity:
        """Derive the nonnegative magnitude from the resolved vector."""

        return PhysicalQuantity(
            decimal_from_finite_real(self.in_plane_force_vector.norm),
            self.force_vector_unit,
        )


__all__ = (
    "DemandDistributionStatus",
    "DemandSourceKind",
    "EndUseFactors",
    "GeometryFactorPlan",
    "LapConfiguration",
    "LapFactorPlan",
    "LayerLoadingSense",
    "PultrudedElementForm",
    "ResolvedSingleBoltDemand",
    "TimeEffectCategory",
    "TimeEffectFactor",
    "create_lap_factor_plan",
    "create_single_bolt_geometry_factor_plan",
    "select_time_effect_factor",
)
