"""Controlled Stage 4.1B Channel major-axis moment-splice input contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.web_splice import (
    WebSpliceBoltGroupLayout,
    WebSplicePlateGeometry,
)

CHANNEL_MOMENT_SPLICE_PRODUCT_ID = "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION = "4.1B-RC1"


class ChannelMomentSpliceStatus(StrEnum):
    VALID = "VALID"
    REJECTED = "REJECTED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_REQUIRED = "NOT_REQUIRED"
    PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED = "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"  # noqa: S105


class ChannelMomentSpliceShearCenterMethod(StrEnum):
    RATIONAL_THIN_WALL = "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1"
    EXPLICIT_VERIFIED = "EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1"


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceShearCenter:
    method: ChannelMomentSpliceShearCenterMethod = (
        ChannelMomentSpliceShearCenterMethod.RATIONAL_THIN_WALL
    )
    explicit_coordinate_t: PhysicalQuantity | None = None
    explicit_provenance: str | None = None
    include_rational_comparison: bool = False

    def __post_init__(self) -> None:
        if self.explicit_coordinate_t is not None:
            _quantity(
                self.explicit_coordinate_t,
                Dimension.LENGTH,
                "explicit_coordinate_t",
            )
        if self.method is ChannelMomentSpliceShearCenterMethod.RATIONAL_THIN_WALL:
            if self.explicit_coordinate_t is not None or self.explicit_provenance is not None:
                raise ValueError("SINGLE_SHEAR_CENTER_SOURCE_REQUIRED")
        elif self.explicit_coordinate_t is None:
            raise ValueError("SINGLE_SHEAR_CENTER_SOURCE_REQUIRED")
        elif self.explicit_provenance is None or not self.explicit_provenance.strip():
            raise ValueError("VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED")


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
class ChannelMomentSpliceBeamGeometry:
    depth: PhysicalQuantity
    flange_width: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    display_length_each_side: PhysicalQuantity
    profile_family: str = "CHANNEL"
    equal_flange: bool = True
    lipped: bool = False
    back_to_back: bool = False

    def __post_init__(self) -> None:
        for name in (
            "depth",
            "flange_width",
            "web_thickness",
            "flange_thickness",
            "display_length_each_side",
        ):
            _quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if self.profile_family != "CHANNEL":
            raise ValueError("UNLIPPED_EQUAL_FLANGE_CHANNEL_REQUIRED")
        if not self.equal_flange:
            raise ValueError("UNEQUAL_FLANGE_CHANNEL_NOT_SUPPORTED_IN_4_1B_RC1")
        if self.lipped:
            raise ValueError("LIPPED_CHANNEL_NOT_SUPPORTED_IN_4_1B_RC1")
        if self.back_to_back:
            raise ValueError("BACK_TO_BACK_CHANNEL_NOT_SUPPORTED_IN_4_1B_RC1")


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceActions:
    axial_force_l: PhysicalQuantity
    major_shear_v: PhysicalQuantity
    major_moment_t: PhysicalQuantity
    minor_shear_t: PhysicalQuantity
    minor_moment_v: PhysicalQuantity
    user_torsion_l: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial_force_l", "major_shear_v", "minor_shear_t"):
            _quantity(getattr(self, name), Dimension.FORCE, name)
        for name in ("major_moment_t", "minor_moment_v", "user_torsion_l"):
            _quantity(getattr(self, name), Dimension.MOMENT, name)
        if self.minor_shear_t.canonical_magnitude != 0:
            raise ValueError("MINOR_SHEAR_NOT_SUPPORTED_IN_4_1B_RC1")
        if self.minor_moment_v.canonical_magnitude != 0:
            raise ValueError("MINOR_AXIS_MOMENT_NOT_SUPPORTED_IN_4_1B_RC1")
        if self.user_torsion_l.canonical_magnitude != 0:
            raise ValueError("USER_TORSION_NOT_SUPPORTED_IN_4_1B_RC1")


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceFlangeGeometry:
    plate_length: PhysicalQuantity
    plate_thickness: PhysicalQuantity
    inner_plate_width: PhysicalQuantity
    transverse_gauge: PhysicalQuantity
    bolts_per_transverse_line: int
    longitudinal_pitch: PhysicalQuantity
    group_centroid_distance: PhysicalQuantity
    outer_plate_count_per_flange: int = 1
    inner_plate_count_per_flange: int = 1
    locked_top_bottom_identical: bool = True

    def __post_init__(self) -> None:
        for name in (
            "plate_length",
            "plate_thickness",
            "inner_plate_width",
            "transverse_gauge",
            "longitudinal_pitch",
            "group_centroid_distance",
        ):
            _quantity(getattr(self, name), Dimension.LENGTH, name, positive=True)
        if (
            isinstance(self.bolts_per_transverse_line, bool)
            or not 1 <= self.bolts_per_transverse_line <= 3
        ):
            raise ValueError("STAGE_4_1B_RC1_MAX_THREE_BOLTS_PER_TRANSVERSE_LINE")


@dataclass(frozen=True, slots=True)
class ChannelMomentSpliceFastener:
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
class ChannelMomentSpliceRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beam: ChannelMomentSpliceBeamGeometry
    beam_end_gap: PhysicalQuantity
    web_splice_plate: WebSplicePlateGeometry
    web_bolt_group: WebSpliceBoltGroupLayout
    web_fastener: ChannelMomentSpliceFastener
    flange_geometry: ChannelMomentSpliceFlangeGeometry
    flange_fastener: ChannelMomentSpliceFastener
    actions: ChannelMomentSpliceActions
    shear_center: ChannelMomentSpliceShearCenter = field(
        default_factory=ChannelMomentSpliceShearCenter
    )
    beams_locked_identical: bool = True
    beams_same_orientation: bool = True
    opening_direction: str = "+T_CH"
    orchestration_contract_version: str = CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be nonempty.")
        if self.orchestration_contract_version != CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION:
            raise ValueError("Unsupported Channel moment-splice contract version.")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("source_length_unit must be in or mm.")
        if not self.beams_locked_identical:
            raise ValueError("IDENTICAL_CHANNEL_BEAMS_REQUIRED")
        if not self.beams_same_orientation or self.opening_direction != "+T_CH":
            raise ValueError("SAME_ORIENTATION_POSITIVE_T_CHANNEL_OPENINGS_REQUIRED")
        _quantity(self.beam_end_gap, Dimension.LENGTH, "beam_end_gap")


def default_channel_moment_splice_request(
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
) -> ChannelMomentSpliceRequest:
    """Return the exact equivalent U.S./SI Stage 4.1B default."""

    si = unit_system is EngineeringUnitSystem.SI
    lu, fu, mu = (Unit.MM, Unit.KN, Unit.KN_MM) if si else (Unit.IN, Unit.KIP, Unit.KIP_IN)

    def length(us: str, metric: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(metric if si else us, lu)

    def force(us: str, metric: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(metric if si else us, fu)

    def moment(us: str, metric: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(metric if si else us, mu)

    fastener = ChannelMomentSpliceFastener(
        length("0.5", "12.7"),
        length("0.563", "14.3002"),
        "ASTM_F593_17_GROUP_2_316_316L",
        "EXCLUDED",
    )
    zero_force = force("0", "0")
    zero_moment = moment("0", "0")
    return ChannelMomentSpliceRequest(
        "stage-4.1b-default",
        unit_system,
        lu,
        ChannelMomentSpliceBeamGeometry(
            length("8", "203.2"),
            length("4", "101.6"),
            length("0.5", "12.7"),
            length("0.5", "12.7"),
            length("18", "457.2"),
        ),
        length("0.5", "12.7"),
        WebSplicePlateGeometry(
            length("16", "406.4"),
            length("5.5", "139.7"),
            length("0.5", "12.7"),
        ),
        WebSpliceBoltGroupLayout(
            2,
            2,
            length("3", "76.2"),
            length("3", "76.2"),
            length("4", "101.6"),
        ),
        fastener,
        ChannelMomentSpliceFlangeGeometry(
            length("16", "406.4"),
            length("0.5", "12.7"),
            length("3", "76.2"),
            length("1.5", "38.1"),
            2,
            length("3", "76.2"),
            length("4", "101.6"),
        ),
        fastener,
        ChannelMomentSpliceActions(
            force("20", "88.96443230521"),
            force("-10", "-44.482216152605"),
            moment("100", "11298.48290276167"),
            zero_force,
            zero_moment,
            zero_moment,
        ),
        ChannelMomentSpliceShearCenter(),
    )


__all__ = (
    "CHANNEL_MOMENT_SPLICE_CONTRACT_VERSION",
    "CHANNEL_MOMENT_SPLICE_PRODUCT_ID",
    "ChannelMomentSpliceActions",
    "ChannelMomentSpliceBeamGeometry",
    "ChannelMomentSpliceFastener",
    "ChannelMomentSpliceFlangeGeometry",
    "ChannelMomentSpliceRequest",
    "ChannelMomentSpliceShearCenter",
    "ChannelMomentSpliceShearCenterMethod",
    "ChannelMomentSpliceStatus",
    "default_channel_moment_splice_request",
)
