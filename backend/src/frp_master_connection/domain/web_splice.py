"""Controlled Stage 3.6A symmetric double-web-splice input contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.values import EngineeringUnitSystem

WEB_SPLICE_CONTRACT_VERSION = "3.6A-RC1"
WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION = "3.6B-RC2"
WEB_SPLICE_SUPPORTED_CONTRACT_VERSIONS = (
    WEB_SPLICE_CONTRACT_VERSION,
    WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
)


class WebSpliceGroupId(StrEnum):
    BEAM_A = "BEAM_A_WEB_SPLICE_GROUP"
    BEAM_B = "BEAM_B_WEB_SPLICE_GROUP"


class WebSpliceStatus(StrEnum):
    VALID = "VALID"
    FAIL = "FAIL"
    PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED = "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"  # noqa: S105
    NOT_EVALUATED = "NOT_EVALUATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


def _require_quantity(
    value: PhysicalQuantity, dimension: Dimension, name: str, *, positive: bool = False
) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not dimension:
        raise TypeError(f"{name} must be a {dimension.value.lower()} quantity.")
    if positive and value.canonical_magnitude <= 0:
        raise ValueError(f"{name} must be positive.")


@dataclass(frozen=True, slots=True)
class WebSpliceBeamGeometry:
    depth: PhysicalQuantity
    flange_width: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    display_length_each_side: PhysicalQuantity
    profile_family: str = "WIDE_FLANGE_I"

    def __post_init__(self) -> None:
        if self.profile_family != "WIDE_FLANGE_I":
            raise ValueError("Stage 3.6A requires WIDE_FLANGE_I beams.")
        for name in (
            "depth",
            "flange_width",
            "web_thickness",
            "flange_thickness",
            "display_length_each_side",
        ):
            _require_quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if self.web_thickness >= self.flange_width:
            raise ValueError("Beam web thickness must be less than flange width.")
        if self.flange_thickness * 2 >= self.depth:
            raise ValueError("Beam flanges must leave a positive clear web depth.")


@dataclass(frozen=True, slots=True)
class WebSplicePlateGeometry:
    length: PhysicalQuantity
    height: PhysicalQuantity
    thickness: PhysicalQuantity
    count: int = 2
    locked_identical: bool = True

    def __post_init__(self) -> None:
        for name in ("length", "height", "thickness"):
            _require_quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if self.count != 2 or not self.locked_identical:
            raise ValueError("SYMMETRIC_DOUBLE_WEB_SPLICE_PLATES_REQUIRED")


@dataclass(frozen=True, slots=True)
class WebSpliceBoltGroupLayout:
    rows: int
    bolts_per_row: int
    vertical_pitch: PhysicalQuantity
    longitudinal_gauge: PhysicalQuantity
    centroid_offset: PhysicalQuantity
    locked_identical_mirror: bool = True

    def __post_init__(self) -> None:
        if (
            isinstance(self.rows, bool)
            or self.rows < 1
            or isinstance(self.bolts_per_row, bool)
            or self.bolts_per_row < 1
        ):
            raise ValueError("A web-splice group requires positive row and bolt counts.")
        for name in ("vertical_pitch", "longitudinal_gauge", "centroid_offset"):
            _require_quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if not self.locked_identical_mirror:
            raise ValueError("Stage 3.6A requires locked mirrored bolt groups.")


@dataclass(frozen=True, slots=True)
class WebSpliceForce:
    axial: PhysicalQuantity
    major_shear: PhysicalQuantity
    minor_shear: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial", "major_shear", "minor_shear"):
            _require_quantity(getattr(self, name), Dimension.FORCE, name)


@dataclass(frozen=True, slots=True)
class WebSpliceRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beam: WebSpliceBeamGeometry
    beam_end_gap: PhysicalQuantity
    splice_plate: WebSplicePlateGeometry
    group: WebSpliceBoltGroupLayout
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    transfer_force: WebSpliceForce
    user_moment_l_v_t: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    flange_splice_enabled: bool = False
    orchestration_contract_version: str = WEB_SPLICE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version not in WEB_SPLICE_SUPPORTED_CONTRACT_VERSIONS:
            raise ValueError("Unsupported web-splice orchestration contract version.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        _require_quantity(self.beam_end_gap, Dimension.LENGTH, "beam_end_gap", positive=True)
        _require_quantity(self.bolt_diameter, Dimension.LENGTH, "bolt_diameter", positive=True)
        _require_quantity(self.hole_diameter, Dimension.LENGTH, "hole_diameter", positive=True)
        if self.hole_diameter < self.bolt_diameter:
            raise ValueError("Hole diameter cannot be smaller than bolt diameter.")
        if len(self.user_moment_l_v_t) != 3:
            raise ValueError("User moment must have exactly three components.")
        for item in self.user_moment_l_v_t:
            _require_quantity(item, Dimension.MOMENT, "user_moment_l_v_t")
            if item.canonical_magnitude != 0:
                raise ValueError("WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER_NOT_AUTHORIZED")
        if self.flange_splice_enabled:
            raise ValueError("FLANGE_SPLICE_NOT_AUTHORIZED_IN_RC1")


def default_web_splice_request(
    *,
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
    orchestration_contract_version: str = WEB_SPLICE_CONTRACT_VERSION,
) -> WebSpliceRequest:
    if unit_system is EngineeringUnitSystem.US_CUSTOMARY:
        lu, fu, mu = Unit.IN, Unit.KIP, Unit.KIP_IN
        values = (
            "10",
            "8",
            "0.5",
            "0.5",
            "18",
            "0.5",
            "16",
            "8",
            "0.5",
            "3",
            "3",
            "4",
            "0.5",
            "0.563",
            "-10",
        )
    else:
        lu, fu, mu = Unit.MM, Unit.KN, Unit.KN_MM
        values = (
            "254",
            "203.2",
            "12.7",
            "12.7",
            "457.2",
            "12.7",
            "406.4",
            "203.2",
            "12.7",
            "76.2",
            "76.2",
            "101.6",
            "12.7",
            "14.3002",
            "-44.482216152605",
        )
    (
        depth,
        width,
        web,
        flange,
        beam_len,
        gap,
        plate_len,
        plate_height,
        plate_t,
        pitch,
        gauge,
        centroid,
        bolt,
        hole,
        shear,
    ) = values
    zero_force = PhysicalQuantity.of(0, fu)
    return WebSpliceRequest(
        (
            "stage-3.6b-default"
            if orchestration_contract_version == WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION
            else "stage-3.6a-default"
        ),
        unit_system,
        lu,
        WebSpliceBeamGeometry(
            PhysicalQuantity.of(depth, lu),
            PhysicalQuantity.of(width, lu),
            PhysicalQuantity.of(web, lu),
            PhysicalQuantity.of(flange, lu),
            PhysicalQuantity.of(beam_len, lu),
        ),
        PhysicalQuantity.of(gap, lu),
        WebSplicePlateGeometry(
            PhysicalQuantity.of(plate_len, lu),
            PhysicalQuantity.of(plate_height, lu),
            PhysicalQuantity.of(plate_t, lu),
        ),
        WebSpliceBoltGroupLayout(
            2,
            2,
            PhysicalQuantity.of(pitch, lu),
            PhysicalQuantity.of(gauge, lu),
            PhysicalQuantity.of(centroid, lu),
        ),
        PhysicalQuantity.of(bolt, lu),
        PhysicalQuantity.of(hole, lu),
        WebSpliceForce(zero_force, PhysicalQuantity.of(shear, fu), zero_force),
        (
            PhysicalQuantity.of(0, mu),
            PhysicalQuantity.of(0, mu),
            PhysicalQuantity.of(0, mu),
        ),
        orchestration_contract_version=orchestration_contract_version,
    )


__all__ = (
    "WEB_SPLICE_CONTRACT_VERSION",
    "WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION",
    "WEB_SPLICE_SUPPORTED_CONTRACT_VERSIONS",
    "WebSpliceBeamGeometry",
    "WebSpliceBoltGroupLayout",
    "WebSpliceForce",
    "WebSpliceGroupId",
    "WebSplicePlateGeometry",
    "WebSpliceRequest",
    "WebSpliceStatus",
    "default_web_splice_request",
)
