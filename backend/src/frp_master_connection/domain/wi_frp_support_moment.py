"""Stage 4.3 immutable physical input, independent of the frozen concrete product."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.web_splice import WebSpliceBeamGeometry
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener
from frp_master_connection.domain.wi_wall_moment import WallMomentActions, WallMomentPattern

PRODUCT = "WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION"
CONTRACT = "4.3-RC1"
MATERIAL = "ICE_LOCKED_PULTRUDED_FRP"
CONNECTORS = ("TOP_FLANGE_ANGLE", "BOTTOM_FLANGE_ANGLE", "POSITIVE_WEB_ANGLE", "NEGATIVE_WEB_ANGLE")


class SupportMode(StrEnum):
    WI_FLANGE = "WI_FLANGE"
    WI_WEB = "WI_WEB"
    HOLLOW_SQUARE = "HOLLOW_SQUARE"
    SOLID_SQUARE = "SOLID_SQUARE"
    CHANNEL_WEB = "CHANNEL_WEB"


FACES: dict[SupportMode, tuple[str, ...]] = {
    SupportMode.WI_FLANGE: ("FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"),
    SupportMode.WI_WEB: ("WEB_NEG_FACE", "WEB_POS_FACE"),
    SupportMode.CHANNEL_WEB: ("WEB_OUTER", "WEB_INNER"),
    SupportMode.HOLLOW_SQUARE: ("Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"),
    SupportMode.SOLID_SQUARE: ("Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"),
}


def length(value: PhysicalQuantity, name: str, *, positive: bool = True) -> None:
    if not isinstance(value, PhysicalQuantity) or value.dimension is not Dimension.LENGTH:
        raise ValueError(f"{name} requires a finite length quantity")
    if positive and value.canonical_magnitude <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class SupportHardware:
    """Explicit geometry, not an inferred grade/strength or bolt-tension source."""

    washer_diameter: PhysicalQuantity
    washer_thickness: PhysicalQuantity
    head_across_flats: PhysicalQuantity
    head_height: PhysicalQuantity
    nut_across_flats: PhysicalQuantity
    nut_height: PhysicalQuantity
    end_extension: PhysicalQuantity
    geometry_source: str = "STAGE_4_3_EXPLICIT_PRESET_GEOMETRY_NOT_STRENGTH_AUTHORITY"

    def __post_init__(self) -> None:
        for name in (
            "washer_diameter",
            "washer_thickness",
            "head_across_flats",
            "head_height",
            "nut_across_flats",
            "nut_height",
            "end_extension",
        ):
            length(getattr(self, name), name)
        if not self.geometry_source.strip():
            raise ValueError("Hardware geometry source is required")


@dataclass(frozen=True, slots=True)
class FRPMomentAngle:
    geometry: AngleConnectorGeometry
    member_pattern: WallMomentPattern
    support_pattern: WallMomentPattern
    fastener: WIMomentSpliceFastener
    support_fastener: WIMomentSpliceFastener
    member_hardware: SupportHardware
    support_hardware: SupportHardware
    connector_source_reference: str = ""
    attachment_source_reference: str = ""
    material_id: str = MATERIAL
    provider_id: str = "FRP"

    def __post_init__(self) -> None:
        if self.provider_id != "FRP" or self.material_id != MATERIAL:
            raise ValueError("Only the registered FRP connector material/provider is available")
        if any(f.nominal_shear_stress is not None for f in (self.fastener, self.support_fastener)):
            raise ValueError("Fastener strengths must resolve from trusted source records")


@dataclass(frozen=True, slots=True)
class ReceivingSupport:
    mode: SupportMode
    face: str
    depth: PhysicalQuantity
    width: PhysicalQuantity
    web_or_wall_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    physical_length: PhysicalQuantity
    connection_height: PhysicalQuantity
    connection_transverse: PhysicalQuantity
    view_length: PhysicalQuantity
    material_id: str = MATERIAL

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SupportMode) or self.face not in FACES[self.mode]:
            raise ValueError("Unsupported receiving support or selected face")
        for name in (
            "depth",
            "width",
            "web_or_wall_thickness",
            "flange_thickness",
            "physical_length",
            "view_length",
            "connection_height",
            "connection_transverse",
        ):
            length(getattr(self, name), name, positive=not name.startswith("connection_"))
        if self.material_id != MATERIAL:
            raise ValueError("Receiving-member material must resolve from the registered snapshot")
        if (
            self.mode in {SupportMode.HOLLOW_SQUARE, SupportMode.SOLID_SQUARE}
            and self.depth != self.width
        ):
            raise ValueError("Stage 4.3 permits square sections only")


@dataclass(frozen=True, slots=True)
class WIFrpSupportMomentRequest:
    request_id: str
    beam: WebSpliceBeamGeometry
    beam_physical_length: PhysicalQuantity
    gap: PhysicalQuantity
    support: ReceivingSupport
    top: FRPMomentAngle
    bottom: FRPMomentAngle
    positive_web: FRPMomentAngle
    negative_web: FRPMomentAngle
    actions: WallMomentActions
    response_source_reference: str = ""
    local_zone_source_reference: str = ""
    beam_material_id: str = MATERIAL
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT or not self.request_id.strip():
            raise ValueError("Stage 4.3 contract and request identity are required")
        length(self.beam_physical_length, "beam_physical_length")
        length(self.gap, "gap", positive=False)
        if self.beam_material_id != MATERIAL:
            raise ValueError("Beam material must resolve from the registered snapshot")

    @property
    def angles(self) -> tuple[FRPMomentAngle, ...]:
        return self.top, self.bottom, self.positive_web, self.negative_web

    def engineering_input(self) -> WIFrpSupportMomentRequest:
        """Remove only display extents and transport ID from source/fingerprint identity."""
        return replace(
            self,
            request_id="STAGE_4_3_ENGINEERING_INPUT",
            beam=replace(self.beam, display_length_each_side=self.beam_physical_length),
            support=replace(self.support, view_length=self.support.physical_length),
        )


def default_frp_support_moment_request(
    mode: SupportMode = SupportMode.WI_FLANGE,
    *,
    si: bool = False,
) -> WIFrpSupportMomentRequest:
    """Audited feasible presets; no source or physically passing design is fabricated."""

    def q(value: str, unit: Unit = Unit.IN) -> PhysicalQuantity:
        target = (
            {Unit.IN: Unit.MM, Unit.KIP: Unit.KN, Unit.KIP_IN: Unit.KN_MM}[unit] if si else unit
        )
        return PhysicalQuantity.of(value, unit).to(target)

    hardware = SupportHardware(
        q("1.25"), q(".125"), q(".75"), q(".3125"), q(".75"), q(".4375"), q(".125")
    )

    def angle(gauge: str) -> FRPMomentAngle:
        geometry = AngleConnectorGeometry(
            q("8"), q("4"), q("4"), q(".5"), q(".25"), (q("0"), q("0"))
        )
        pattern = WallMomentPattern(2, 2, q(gauge), q("1.5"), q("2"))
        fastener = WIMomentSpliceFastener(
            q(".5"), q(".563"), "ASTM_F593_17_GROUP_2_316_316L", "EXCLUDED"
        )
        return FRPMomentAngle(geometry, pattern, pattern, fastener, fastener, hardware, hardware)

    depth, width = {
        SupportMode.WI_FLANGE: ("16", "12"),
        SupportMode.WI_WEB: ("16", "8"),
        SupportMode.CHANNEL_WEB: ("16", "6"),
        SupportMode.HOLLOW_SQUARE: ("12", "12"),
        SupportMode.SOLID_SQUARE: ("12", "12"),
    }[mode]
    support = ReceivingSupport(
        mode, FACES[mode][0], q(depth), q(width), q(".5"), q(".5"), q("48"), q("0"), q("0"), q("36")
    )
    flange, web = angle("5"), angle("3")
    return WIFrpSupportMomentRequest(
        "stage-4.3-default",
        WebSpliceBeamGeometry(q("10"), q("8"), q(".5"), q(".5"), q("16")),
        q("16"),
        q(".5"),
        support,
        flange,
        flange,
        web,
        web,
        WallMomentActions(
            q("20", Unit.KIP),
            q("-10", Unit.KIP),
            q("100", Unit.KIP_IN),
            q("0", Unit.KIP),
            q("0", Unit.KIP_IN),
            q("0", Unit.KIP_IN),
        ),
    )
