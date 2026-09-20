"""Stage 4.2 successor contracts; frozen beam/wall and neutral angle inputs reused."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.beam_concrete_paired_angle import (
    ConcreteWallGeometry,
    ExternalAnchorGeometry,
)
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.web_splice import WebSpliceBeamGeometry
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener

PRODUCT = "WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION"
CONTRACT = "4.2-RC1"
CONNECTORS = ("TOP_FLANGE_ANGLE", "BOTTOM_FLANGE_ANGLE", "POSITIVE_WEB_ANGLE", "NEGATIVE_WEB_ANGLE")


def _length(value: PhysicalQuantity, name: str, *, positive: bool = True) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.LENGTH:
        raise TypeError(f"{name} requires a length quantity.")
    if positive and value.canonical_magnitude <= 0:
        raise ValueError(f"{name} must be positive.")


@dataclass(frozen=True, slots=True)
class WallMomentActions:
    axial: PhysicalQuantity
    major_shear: PhysicalQuantity
    structural_major_moment: PhysicalQuantity
    minor_shear: PhysicalQuantity
    minor_moment: PhysicalQuantity
    torsion: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial", "major_shear", "minor_shear"):
            if getattr(self, name).dimension is not Dimension.FORCE:
                raise ValueError(f"{name} must be a force.")
        for name in ("structural_major_moment", "minor_moment", "torsion"):
            if getattr(self, name).dimension is not Dimension.MOMENT:
                raise ValueError(f"{name} must be a moment.")
        for name, reason in (
            ("minor_shear", "MINOR_SHEAR_NOT_SUPPORTED_IN_4_2_RC1"),
            ("minor_moment", "MINOR_AXIS_MOMENT_NOT_SUPPORTED_IN_4_2_RC1"),
            ("torsion", "TORSION_NOT_SUPPORTED_IN_4_2_RC1"),
        ):
            if getattr(self, name).canonical_magnitude != 0:
                raise ValueError(reason)


@dataclass(frozen=True, slots=True)
class WallMomentPattern:
    """Heel-local A/B (member) or A/C (support) physical grid, not recentered."""

    across: int
    along: int
    gauge: PhysicalQuantity
    pitch: PhysicalQuantity
    center: PhysicalQuantity

    def __post_init__(self) -> None:
        for value in (self.across, self.along):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Bolt/anchor counts must be positive integers.")
        for name in ("gauge", "pitch", "center"):
            _length(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class WallMomentAngle:
    geometry: AngleConnectorGeometry
    member_pattern: WallMomentPattern
    support_pattern: WallMomentPattern
    fastener: WIMomentSpliceFastener
    anchors: ExternalAnchorGeometry
    connector_source_reference: str = ""
    attachment_source_reference: str = ""
    material_id: str = "ICE_LOCKED_PULTRUDED_FRP"
    provider_id: str = "FRP"

    def __post_init__(self) -> None:
        if self.material_id != "ICE_LOCKED_PULTRUDED_FRP":
            raise ValueError("Stage 4.2 requires the unchanged locked ICE material.")
        if self.provider_id != "FRP":
            raise ValueError("RESISTANCE_PROVIDER_NOT_IMPLEMENTED")
        if (
            self.fastener.source_authority_id != "ASTM_F593_17_GROUP_2_316_316L"
            or self.fastener.nominal_shear_stress is not None
        ):
            raise ValueError("CONTROLLED_F593_SOURCE_REQUIRED_NO_CLIENT_STRENGTH")


@dataclass(frozen=True, slots=True)
class WIWallMomentRequest:
    request_id: str
    unit_system: EngineeringUnitSystem
    source_length_unit: Unit
    beam: WebSpliceBeamGeometry
    gap: PhysicalQuantity
    wall: ConcreteWallGeometry
    top: WallMomentAngle
    bottom: WallMomentAngle
    positive_web: WallMomentAngle
    negative_web: WallMomentAngle
    actions: WallMomentActions
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if not self.request_id.strip() or self.contract != CONTRACT:
            raise ValueError("Invalid Stage 4.2 request identity/contract.")
        if self.beam.profile_family != "WIDE_FLANGE_I":
            raise ValueError("ONLY_WI_BEAM_SUPPORTED_IN_4_2_RC1")
        if self.source_length_unit not in {Unit.IN, Unit.MM}:
            raise ValueError("Stage 4.2 source length must be in or mm.")
        _length(self.gap, "gap", positive=False)

    @property
    def angles(self) -> tuple[WallMomentAngle, ...]:
        return self.top, self.bottom, self.positive_web, self.negative_web


def default_wi_wall_moment_request(
    unit_system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
) -> WIWallMomentRequest:
    """Exact equivalent default; qualified sources and F593 strength remain absent."""

    si = unit_system is EngineeringUnitSystem.SI
    lu, fu, mu = (Unit.MM, Unit.KN, Unit.KN_MM) if si else (Unit.IN, Unit.KIP, Unit.KIP_IN)

    def length(value: str) -> PhysicalQuantity:
        return PhysicalQuantity.of(value, Unit.IN).to(lu)

    def angle(gauge: str) -> WallMomentAngle:
        geometry = AngleConnectorGeometry(
            length("8"),
            length("4"),
            length("4"),
            length(".5"),
            length(".25"),
            (length("0"), length("0")),
        )
        pattern = WallMomentPattern(2, 2, length(gauge), length("1.5"), length("2"))
        return WallMomentAngle(
            geometry,
            pattern,
            pattern,
            WIMomentSpliceFastener(
                length(".5"), length(".563"), "ASTM_F593_17_GROUP_2_316_316L", "EXCLUDED"
            ),
            ExternalAnchorGeometry(
                length(".5"), length(".563"), length("4"), length("1.25"), length(".125")
            ),
        )

    flange, web = angle("5"), angle("3")
    return WIWallMomentRequest(
        "stage-4.2-default",
        unit_system,
        lu,
        WebSpliceBeamGeometry(length("10"), length("8"), length(".5"), length(".5"), length("16")),
        length(".5"),
        ConcreteWallGeometry(
            length("48").magnitude,
            length("48").magnitude,
            length("8").magnitude,
            Decimal(0),
            Decimal(0),
        ),
        flange,
        flange,
        web,
        web,
        WallMomentActions(
            PhysicalQuantity.of("20", Unit.KIP).to(fu),
            PhysicalQuantity.of("-10", Unit.KIP).to(fu),
            PhysicalQuantity.of("100", Unit.KIP_IN).to(mu),
            PhysicalQuantity.of(0, fu),
            PhysicalQuantity.of(0, mu),
            PhysicalQuantity.of(0, mu),
        ),
    )
