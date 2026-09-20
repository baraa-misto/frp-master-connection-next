"""Stage 3.5A immutable wall and external-anchor coordination contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from frp_master_connection.calculation.quantities import PhysicalQuantity
else:
    PhysicalQuantity = Any


def _has_dimension(value: object, expected: str) -> bool:
    """Validate quantity dimensions without reversing the domain dependency arrow."""

    dimension = getattr(value, "dimension", None)
    return getattr(dimension, "value", None) == expected


def _finite(value: Decimal, name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal.")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite.")
    if positive and value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


class WallAnchorGroupIdentity(StrEnum):
    POSITIVE_WALL_ANCHOR_GROUP = "POSITIVE_WALL_ANCHOR_GROUP"
    NEGATIVE_WALL_ANCHOR_GROUP = "NEGATIVE_WALL_ANCHOR_GROUP"


class ExternalDesignStatus(StrEnum):
    EXTERNAL_DESIGN_REQUIRED = "EXTERNAL_DESIGN_REQUIRED"
    REQUIRED = "REQUIRED"


@dataclass(frozen=True, slots=True)
class ConcreteWallFrame:
    """Exact right-handed local H/V/N frame used by the handoff."""

    origin_hvn: tuple[Decimal, Decimal, Decimal] = (
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )
    h_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(1),
        Decimal(0),
        Decimal(0),
    )
    v_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(0),
        Decimal(1),
        Decimal(0),
    )
    n_axis: tuple[Decimal, Decimal, Decimal] = (
        Decimal(0),
        Decimal(0),
        Decimal(1),
    )
    handedness: str = "H_W cross V_W = N_W"

    def __post_init__(self) -> None:
        for value in (*self.origin_hvn, *self.h_axis, *self.v_axis, *self.n_axis):
            _finite(value, "ConcreteWallFrame component")
        cross = (
            self.h_axis[1] * self.v_axis[2] - self.h_axis[2] * self.v_axis[1],
            self.h_axis[2] * self.v_axis[0] - self.h_axis[0] * self.v_axis[2],
            self.h_axis[0] * self.v_axis[1] - self.h_axis[1] * self.v_axis[0],
        )
        if cross != self.n_axis or self.handedness != "H_W cross V_W = N_W":
            raise ValueError("Concrete wall frame must be the controlled right-handed H/V/N frame.")


@dataclass(frozen=True, slots=True)
class ConcreteWallGeometry:
    width: Decimal
    height: Decimal
    thickness: Decimal
    connection_origin_h: Decimal
    connection_origin_v: Decimal

    def __post_init__(self) -> None:
        for name in ("width", "height", "thickness"):
            _finite(getattr(self, name), name, positive=True)
        _finite(self.connection_origin_h, "connection_origin_h")
        _finite(self.connection_origin_v, "connection_origin_v")


@dataclass(frozen=True, slots=True)
class WallAnchorPattern:
    row_count: int
    anchors_per_row: int
    pitch: Decimal
    gauge: Decimal
    centroid_offset_h: Decimal
    centroid_v: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        for name in ("row_count", "anchors_per_row"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive non-Boolean integer.")
        _finite(self.pitch, "pitch", positive=True)
        _finite(self.gauge, "gauge", positive=True)
        _finite(self.centroid_offset_h, "centroid_offset_h", positive=True)
        _finite(self.centroid_v, "centroid_v")


@dataclass(frozen=True, slots=True)
class ExternalAnchorGeometry:
    nominal_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    specified_embedment: PhysicalQuantity
    washer_outside_diameter: PhysicalQuantity
    washer_thickness: PhysicalQuantity
    system_classification: str = "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR"

    def __post_init__(self) -> None:
        values = (
            self.nominal_diameter,
            self.hole_diameter,
            self.specified_embedment,
            self.washer_outside_diameter,
            self.washer_thickness,
        )
        if any(not _has_dimension(item, "LENGTH") or item.magnitude <= 0 for item in values):
            raise ValueError("External-anchor geometry values must be positive lengths.")
        if self.hole_diameter.canonical_magnitude < self.nominal_diameter.canonical_magnitude:
            raise ValueError("External-anchor hole diameter cannot be smaller than the anchor.")
        if (
            self.washer_outside_diameter.canonical_magnitude
            <= self.nominal_diameter.canonical_magnitude
        ):
            raise ValueError("External-anchor washer must be wider than the anchor.")
        if self.system_classification != "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR":
            raise ValueError(
                "Stage 3.5A accepts only the controlled external-anchor classification."
            )


@dataclass(frozen=True, slots=True)
class WallQuantityVector:
    h: PhysicalQuantity
    v: PhysicalQuantity
    n: PhysicalQuantity

    def __post_init__(self) -> None:
        if len({self.h.dimension, self.v.dimension, self.n.dimension}) != 1:
            raise ValueError("Wall-vector components must share one physical dimension.")


@dataclass(frozen=True, slots=True)
class WallWrench:
    reference_hvn: WallQuantityVector
    force_hvn: WallQuantityVector
    moment_hvn: WallQuantityVector
    provenance: str

    def __post_init__(self) -> None:
        if not _has_dimension(self.reference_hvn.h, "LENGTH"):
            raise ValueError("Wall-wrench reference must contain length quantities.")
        if not _has_dimension(self.force_hvn.h, "FORCE"):
            raise ValueError("Wall-wrench force must contain force quantities.")
        if not _has_dimension(self.moment_hvn.h, "MOMENT"):
            raise ValueError("Wall-wrench moment must contain moment quantities.")
        if not self.provenance.strip():
            raise ValueError("Wall-wrench provenance must be nonempty.")


@dataclass(frozen=True, slots=True)
class WallEdgeDistances:
    negative_h: PhysicalQuantity
    positive_h: PhysicalQuantity
    negative_v: PhysicalQuantity
    positive_v: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class ExternalAnchorTrace:
    anchor_id: str
    group_id: WallAnchorGroupIdentity
    coordinate_hvn: WallQuantityVector
    wall_edge_distances: WallEdgeDistances
    shank_start_hvn: WallQuantityVector
    shank_end_hvn: WallQuantityVector
    hardware_configuration: str = "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK"
    capacity_status: ExternalDesignStatus = ExternalDesignStatus.EXTERNAL_DESIGN_REQUIRED

    def __post_init__(self) -> None:
        if not self.anchor_id.strip():
            raise ValueError("External anchor ID must be nonempty.")
        if not _has_dimension(self.coordinate_hvn.h, "LENGTH"):
            raise ValueError("External-anchor coordinates must contain length quantities.")
        if self.hardware_configuration != "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK":
            raise ValueError("Stage 3.5A forbids far-side anchor hardware.")


EXTERNAL_DESIGN_LIMITATIONS: tuple[tuple[str, ExternalDesignStatus], ...] = (
    ("CONCRETE_SUBSTRATE_RESISTANCE", ExternalDesignStatus.EXTERNAL_DESIGN_REQUIRED),
    ("ANCHOR_SYSTEM_RESISTANCE", ExternalDesignStatus.EXTERNAL_DESIGN_REQUIRED),
    ("ANCHOR_STEEL_RESISTANCE", ExternalDesignStatus.EXTERNAL_DESIGN_REQUIRED),
    ("ANCHOR_CONCRETE_LIMIT_STATES", ExternalDesignStatus.EXTERNAL_DESIGN_REQUIRED),
    ("EXTERNAL_ANCHOR_DEMAND_VERIFICATION", ExternalDesignStatus.REQUIRED),
)


__all__ = (
    "EXTERNAL_DESIGN_LIMITATIONS",
    "ConcreteWallFrame",
    "ConcreteWallGeometry",
    "ExternalAnchorGeometry",
    "ExternalAnchorTrace",
    "ExternalDesignStatus",
    "WallAnchorGroupIdentity",
    "WallAnchorPattern",
    "WallEdgeDistances",
    "WallQuantityVector",
    "WallWrench",
)
