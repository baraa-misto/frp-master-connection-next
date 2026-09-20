"""Stage 4.4 physical input; no load allocation, qualification or resistance here."""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.beam_concrete_paired_angle import ExternalAnchorGeometry
from frp_master_connection.domain.wi_frp_support_moment import SupportHardware, length
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener
from frp_master_connection.domain.wi_wall_moment import WallMomentAngle, WallMomentPattern

PRODUCT = "ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION"
CONTRACT = "4.4-RC1"
MATERIAL = "ICE_LOCKED_PULTRUDED_FRP"
CONNECTORS = ("LEG_1_BASE_ANGLE", "LEG_2_BASE_ANGLE")


@dataclass(frozen=True, slots=True)
class AngleBaseActions:
    axial: PhysicalQuantity
    shear_x: PhysicalQuantity
    shear_y: PhysicalQuantity
    moment_x: PhysicalQuantity
    moment_y: PhysicalQuantity
    applied_torque_z: PhysicalQuantity

    def __post_init__(self) -> None:
        for value, dimension in (
            (self.axial, Dimension.FORCE),
            (self.shear_x, Dimension.FORCE),
            (self.shear_y, Dimension.FORCE),
            (self.moment_x, Dimension.MOMENT),
            (self.moment_y, Dimension.MOMENT),
            (self.applied_torque_z, Dimension.MOMENT),
        ):
            if not isinstance(value, PhysicalQuantity) or value.dimension is not dimension:
                raise ValueError("Finite force/moment quantities required")
        if self.applied_torque_z.canonical_magnitude != 0:
            raise ValueError("INDEPENDENT_COLUMN_TORQUE_OUTSIDE_4_4_RC1")


@dataclass(frozen=True, slots=True)
class AngleBaseColumn:
    leg_x: PhysicalQuantity
    leg_y: PhysicalQuantity
    thickness: PhysicalQuantity
    view_length: PhysicalQuantity
    material_id: str = MATERIAL

    def __post_init__(self) -> None:
        for name in ("leg_x", "leg_y", "thickness", "view_length"):
            length(getattr(self, name), name)
        if self.thickness >= min(self.leg_x, self.leg_y):
            raise ValueError("Column thickness must be smaller than both legs")
        if self.material_id != MATERIAL:
            raise ValueError("Column material must resolve to the registered FRP record")


@dataclass(frozen=True, slots=True)
class AngleBaseFoundation:
    width_x: PhysicalQuantity
    width_y: PhysicalQuantity
    depth: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("width_x", "width_y", "depth"):
            length(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class AngleBaseConnector:
    # Shared immutable angle/core/hardware contracts, not a fabricated wall request.
    angle: WallMomentAngle
    extrusion_center: PhysicalQuantity
    member_hardware: SupportHardware
    normal_response_source_reference: str = ""
    fastener_source_reference: str = ""

    def __post_init__(self) -> None:
        length(self.extrusion_center, "extrusion_center", positive=False)
        # The shared immutable WallMomentAngle leaf already rejects client strengths.


@dataclass(frozen=True, slots=True)
class AngleColumnMomentBaseRequest:
    request_id: str
    column: AngleBaseColumn
    foundation: AngleBaseFoundation
    leg_1: AngleBaseConnector
    leg_2: AngleBaseConnector
    actions: AngleBaseActions
    response_source_reference: str = ""
    column_zone_source_reference: str = ""
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT or not self.request_id.strip():
            raise ValueError("Stage 4.4 request identity and contract required")

    @property
    def connectors(self) -> tuple[AngleBaseConnector, AngleBaseConnector]:
        return self.leg_1, self.leg_2

    def engineering_input(self) -> AngleColumnMomentBaseRequest:
        """Viewer clipping/transport identity do not establish an engineering end plane."""
        return replace(
            self,
            request_id="STAGE_4_4_ENGINEERING_INPUT",
            column=replace(self.column, view_length=PhysicalQuantity.of(18, Unit.IN)),
        )


def default_angle_column_moment_base_request(
    *, unequal: bool = False, si: bool = False
) -> AngleColumnMomentBaseRequest:
    """Constructive, not adequate: no production qualification is preselected."""

    def q(value: str, unit: Unit = Unit.IN) -> PhysicalQuantity:
        target = (
            {Unit.IN: Unit.MM, Unit.KIP: Unit.KN, Unit.KIP_IN: Unit.KN_MM}[unit] if si else unit
        )
        return PhysicalQuantity.of(value, unit).to(target)

    hardware = SupportHardware(
        q("1.25"), q(".125"), q(".75"), q(".3125"), q(".75"), q(".4375"), q(".125")
    )

    def connector(center: str) -> AngleBaseConnector:
        geometry = AngleConnectorGeometry(
            q("6"), q("6"), q("6"), q(".5"), q(".25"), (q("0"), q("0"))
        )
        # These centers are measured above bottom / from column exterior face.
        # The geometry adapter, not the sidebar, maps them into native heel coordinates.
        pattern = WallMomentPattern(2, 2, q("3"), q("2"), q("3"))
        return AngleBaseConnector(
            WallMomentAngle(
                geometry,
                pattern,
                pattern,
                WIMomentSpliceFastener(
                    q(".5"), q(".563"), "ASTM_F593_17_GROUP_2_316_316L", "EXCLUDED"
                ),
                ExternalAnchorGeometry(q(".5"), q(".563"), q("4"), q("1.25"), q(".125")),
            ),
            q(center),
            hardware,
        )

    return AngleColumnMomentBaseRequest(
        "stage-4.4-default",
        AngleBaseColumn(q("8"), q("6" if unequal else "8"), q(".5"), q("18")),
        AngleBaseFoundation(q("32"), q("32"), q("12")),
        connector("4"),
        connector("3" if unequal else "4"),
        AngleBaseActions(
            q("-20", Unit.KIP),
            q("5", Unit.KIP),
            q("-3", Unit.KIP),
            q("60", Unit.KIP_IN),
            q("40", Unit.KIP_IN),
            q("0", Unit.KIP_IN),
        ),
    )
