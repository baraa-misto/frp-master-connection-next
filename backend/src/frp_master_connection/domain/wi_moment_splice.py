"""Controlled Stage 4.1A W/I major-axis moment-splice input contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.web_splice import (
    WebSpliceBeamGeometry,
    WebSpliceBoltGroupLayout,
    WebSplicePlateGeometry,
)

WI_MOMENT_SPLICE_PRODUCT_ID = "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
WI_MOMENT_SPLICE_CONTRACT_VERSION = "4.1A-RC1"


class WIMomentSpliceStatus(StrEnum):
    VALID = "VALID"
    REJECTED = "REJECTED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_REQUIRED = "NOT_REQUIRED"
    PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED = "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"  # noqa: S105


def _quantity(
    value: PhysicalQuantity,
    dimension: Dimension,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not dimension:
        raise TypeError(f"{name} must be a {dimension.value.lower()} quantity.")
    if positive and value.canonical_magnitude <= 0:
        raise ValueError(f"{name} must be positive.")


@dataclass(frozen=True, slots=True)
class WIMomentSpliceActions:
    axial_force_l: PhysicalQuantity
    major_shear_v: PhysicalQuantity
    major_moment_t: PhysicalQuantity
    minor_shear_t: PhysicalQuantity
    minor_moment_v: PhysicalQuantity
    torsion_l: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial_force_l", "major_shear_v", "minor_shear_t"):
            _quantity(getattr(self, name), Dimension.FORCE, name)
        for name in ("major_moment_t", "minor_moment_v", "torsion_l"):
            _quantity(getattr(self, name), Dimension.MOMENT, name)
        if self.minor_shear_t.canonical_magnitude != 0:
            raise ValueError("MINOR_SHEAR_NOT_SUPPORTED_IN_4_1A_RC1")
        if self.minor_moment_v.canonical_magnitude != 0:
            raise ValueError("MINOR_AXIS_MOMENT_NOT_SUPPORTED_IN_4_1A_RC1")
        if self.torsion_l.canonical_magnitude != 0:
            raise ValueError("TORSION_NOT_SUPPORTED_IN_4_1A_RC1")


@dataclass(frozen=True, slots=True)
class WIMomentSpliceFlangeGeometry:
    plate_length: PhysicalQuantity
    plate_thickness: PhysicalQuantity
    inner_strip_width: PhysicalQuantity
    bolts_per_line: int
    longitudinal_pitch: PhysicalQuantity
    group_centroid_distance: PhysicalQuantity
    outer_plate_count_per_flange: int = 1
    inner_strip_count_per_flange: int = 2
    locked_top_bottom_identical: bool = True
    locked_inner_symmetric: bool = True

    def __post_init__(self) -> None:
        for name in (
            "plate_length",
            "plate_thickness",
            "inner_strip_width",
            "longitudinal_pitch",
            "group_centroid_distance",
        ):
            _quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if isinstance(self.bolts_per_line, bool) or not 1 <= self.bolts_per_line <= 3:
            raise ValueError("STAGE_4_1A_RC1_MAX_THREE_BOLTS_PER_LINE")


@dataclass(frozen=True, slots=True)
class WIMomentSpliceFastener:
    bolt_diameter: PhysicalQuantity
    hole_diameter: PhysicalQuantity
    source_authority_id: str
    thread_condition: str
    nominal_shear_stress: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        _quantity(self.bolt_diameter, Dimension.LENGTH, "bolt_diameter", positive=True)
        _quantity(self.hole_diameter, Dimension.LENGTH, "hole_diameter", positive=True)
        if self.hole_diameter < self.bolt_diameter:
            raise ValueError("Hole diameter cannot be smaller than bolt diameter.")
        if not self.source_authority_id.strip():
            raise ValueError("source_authority_id must be nonempty.")
        if self.thread_condition not in {"INCLUDED", "EXCLUDED"}:
            raise ValueError("thread_condition must be INCLUDED or EXCLUDED.")
        if self.nominal_shear_stress is not None:
            _quantity(
                self.nominal_shear_stress,
                Dimension.STRESS,
                "nominal_shear_stress",
                positive=True,
            )


@dataclass(frozen=True, slots=True)
class WIMomentSpliceRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beam: WebSpliceBeamGeometry
    beam_end_gap: PhysicalQuantity
    web_splice_plate: WebSplicePlateGeometry
    web_bolt_group: WebSpliceBoltGroupLayout
    web_fastener: WIMomentSpliceFastener
    flange_geometry: WIMomentSpliceFlangeGeometry
    flange_fastener: WIMomentSpliceFastener
    actions: WIMomentSpliceActions
    profile_family: str = "WIDE_FLANGE_I"
    beams_locked_identical: bool = True
    orchestration_contract_version: str = WI_MOMENT_SPLICE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version != WI_MOMENT_SPLICE_CONTRACT_VERSION:
            raise ValueError("Unsupported W/I moment-splice contract version.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        if self.profile_family != "WIDE_FLANGE_I":
            raise ValueError("CHANNEL_MOMENT_SPLICE_NOT_IN_STAGE_4_1A_RC1")
        if not self.beams_locked_identical:
            raise ValueError("IDENTICAL_WI_BEAMS_REQUIRED")
        _quantity(self.beam_end_gap, Dimension.LENGTH, "beam_end_gap")


def default_wi_moment_splice_request(
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
) -> WIMomentSpliceRequest:
    """Return the exact equivalent U.S./SI Stage 4.1A default."""

    if unit_system is EngineeringUnitSystem.US_CUSTOMARY:
        lu, fu, mu = Unit.IN, Unit.KIP, Unit.KIP_IN
        lengths = (
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
            "16",
            "0.5",
            "3",
            "3",
            "4",
            "0.5",
            "0.563",
        )
        actions = ("20", "-10", "100")
    else:
        lu, fu, mu = Unit.MM, Unit.KN, Unit.KN_MM
        lengths = (
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
            "406.4",
            "12.7",
            "76.2",
            "76.2",
            "101.6",
            "12.7",
            "14.3002",
        )
        actions = ("88.96443230521", "-44.482216152605", "11298.48290276167")
    (
        depth,
        width,
        web_t,
        flange_t,
        display,
        gap,
        web_l,
        web_h,
        web_plate_t,
        web_pitch,
        web_gauge,
        web_center,
        web_bolt,
        web_hole,
        flange_l,
        flange_plate_t,
        strip_width,
        flange_pitch,
        flange_center,
        flange_bolt,
        flange_hole,
    ) = lengths
    zero_force = PhysicalQuantity.of(0, fu)
    zero_moment = PhysicalQuantity.of(0, mu)
    source_pending = "ASTM_F593_17_GROUP_2_316_316L"
    return WIMomentSpliceRequest(
        "stage-4.1a-default",
        unit_system,
        lu,
        WebSpliceBeamGeometry(
            PhysicalQuantity.of(depth, lu),
            PhysicalQuantity.of(width, lu),
            PhysicalQuantity.of(web_t, lu),
            PhysicalQuantity.of(flange_t, lu),
            PhysicalQuantity.of(display, lu),
        ),
        PhysicalQuantity.of(gap, lu),
        WebSplicePlateGeometry(
            PhysicalQuantity.of(web_l, lu),
            PhysicalQuantity.of(web_h, lu),
            PhysicalQuantity.of(web_plate_t, lu),
        ),
        WebSpliceBoltGroupLayout(
            2,
            2,
            PhysicalQuantity.of(web_pitch, lu),
            PhysicalQuantity.of(web_gauge, lu),
            PhysicalQuantity.of(web_center, lu),
        ),
        WIMomentSpliceFastener(
            PhysicalQuantity.of(web_bolt, lu),
            PhysicalQuantity.of(web_hole, lu),
            source_pending,
            "EXCLUDED",
        ),
        WIMomentSpliceFlangeGeometry(
            PhysicalQuantity.of(flange_l, lu),
            PhysicalQuantity.of(flange_plate_t, lu),
            PhysicalQuantity.of(strip_width, lu),
            2,
            PhysicalQuantity.of(flange_pitch, lu),
            PhysicalQuantity.of(flange_center, lu),
        ),
        WIMomentSpliceFastener(
            PhysicalQuantity.of(flange_bolt, lu),
            PhysicalQuantity.of(flange_hole, lu),
            source_pending,
            "EXCLUDED",
        ),
        WIMomentSpliceActions(
            PhysicalQuantity.of(actions[0], fu),
            PhysicalQuantity.of(actions[1], fu),
            PhysicalQuantity.of(actions[2], mu),
            zero_force,
            zero_moment,
            zero_moment,
        ),
    )


__all__ = (
    "WI_MOMENT_SPLICE_CONTRACT_VERSION",
    "WI_MOMENT_SPLICE_PRODUCT_ID",
    "WIMomentSpliceActions",
    "WIMomentSpliceFastener",
    "WIMomentSpliceFlangeGeometry",
    "WIMomentSpliceRequest",
    "WIMomentSpliceStatus",
    "default_wi_moment_splice_request",
)
