"""Stage 4.5 physical inputs. Geometry linking is not load sharing."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from frp_master_connection.calculation.angle_connector_core import AngleConnectorGeometry
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseConnector,
    AngleBaseFoundation,
)
from frp_master_connection.domain.beam_concrete_paired_angle import ExternalAnchorGeometry
from frp_master_connection.domain.wi_frp_support_moment import SupportHardware, length
from frp_master_connection.domain.wi_moment_splice import WIMomentSpliceFastener
from frp_master_connection.domain.wi_wall_moment import WallMomentAngle, WallMomentPattern

PRODUCT = "WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION"
CONTRACT = "4.5-RC1"
MATERIAL = "ICE_LOCKED_PULTRUDED_FRP"
Family = Literal["WI", "RHS", "SRS"]
Layout = Literal["TWO_X", "TWO_Y", "FOUR_XY"]
Face = Literal["X_POS", "X_NEG", "Y_POS", "Y_NEG"]
FACES: tuple[Face, ...] = ("X_POS", "X_NEG", "Y_POS", "Y_NEG")
PRESETS = {
    "WI12": ("WI", "12", "12"),
    "RHS8": ("RHS", "8", "8"),
    "RHS10X8": ("RHS", "10", "8"),
    "SRS8": ("SRS", "8", "8"),
    "SRS10X8": ("SRS", "10", "8"),
}


@dataclass(frozen=True, slots=True)
class ColumnMomentActions:
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
            raise ValueError("INDEPENDENT_COLUMN_TORQUE_OUTSIDE_4_5_RC1")


@dataclass(frozen=True, slots=True)
class MomentBaseColumn:
    family: Family
    width: PhysicalQuantity
    depth: PhysicalQuantity
    web_thickness: PhysicalQuantity
    flange_thickness: PhysicalQuantity
    wall_thickness: PhysicalQuantity
    view_length: PhysicalQuantity
    offset_x: PhysicalQuantity
    offset_y: PhysicalQuantity
    material_id: str = MATERIAL

    def __post_init__(self) -> None:
        if self.family not in {"WI", "RHS", "SRS"} or self.material_id != MATERIAL:
            raise ValueError("Stage 4.5 supports only uniform registered FRP W/I, RHS and SRS")
        for name in (
            "width",
            "depth",
            "web_thickness",
            "flange_thickness",
            "wall_thickness",
            "view_length",
        ):
            length(getattr(self, name), name)
        for name in ("offset_x", "offset_y"):
            length(getattr(self, name), name, positive=False)
        # Native profile constructors additionally enforce the actual section domain.


@dataclass(frozen=True, slots=True)
class ColumnMomentBaseRequest:
    request_id: str
    column: MomentBaseColumn
    layout: Layout
    foundation: AngleBaseFoundation
    x_positive: AngleBaseConnector
    x_negative: AngleBaseConnector
    y_positive: AngleBaseConnector
    y_negative: AngleBaseConnector
    actions: ColumnMomentActions
    response_source_reference: str = ""
    column_zone_source_reference: str = ""
    contract: str = CONTRACT

    def __post_init__(self) -> None:
        if self.contract != CONTRACT or not self.request_id.strip():
            raise ValueError("Stage 4.5 request identity and contract required")
        if self.layout not in {"TWO_X", "TWO_Y", "FOUR_XY"}:
            raise ValueError("Unknown column moment base layout")

    @property
    def active_faces(self) -> tuple[Face, ...]:
        if self.layout == "TWO_X":
            return FACES[:2]
        if self.layout == "TWO_Y":
            return FACES[2:]
        return FACES

    def connector(self, face: Face) -> AngleBaseConnector:
        return {
            "X_POS": self.x_positive,
            "X_NEG": self.x_negative,
            "Y_POS": self.y_positive,
            "Y_NEG": self.y_negative,
        }[face]

    def shared(self, face: Face) -> bool:
        return face.startswith("X") or self.column.family != "WI"

    def physical_connector(self, face: Face) -> AngleBaseConnector:
        """One canonical shared grid/fastener/hardware; partner dimensions stay independent."""
        item = self.connector(face)
        if face.endswith("NEG") and self.shared(face):
            owner = self.x_positive if face == "X_NEG" else self.y_positive
            return replace(
                item,
                extrusion_center=owner.extrusion_center * -1,
                angle=replace(
                    item.angle,
                    member_pattern=owner.angle.member_pattern,
                    fastener=owner.angle.fastener,
                ),
                member_hardware=owner.member_hardware,
            )
        return item

    def engineering_input(self) -> tuple[object, ...]:
        column = replace(self.column, view_length=PhysicalQuantity.of(18, Unit.IN))
        # Inactive controls and derived, noneditable partner grid do not carry authority.
        return (
            CONTRACT,
            column,
            self.layout,
            self.foundation,
            self.actions,
            tuple((face, self.physical_connector(face)) for face in self.active_faces),
            self.response_source_reference,
            self.column_zone_source_reference,
        )


def default_column_moment_base_request(
    preset: str = "WI12", layout: Layout = "FOUR_XY", *, si: bool = False
) -> ColumnMomentBaseRequest:
    """Constructive unqualified presets; no production synthetic response is registered."""
    from typing import cast

    if preset not in PRESETS:
        raise ValueError("Unknown Stage 4.5 section preset")
    family, width, depth = PRESETS[preset]

    def q(value: str, unit: Unit = Unit.IN) -> PhysicalQuantity:
        target = (
            {Unit.IN: Unit.MM, Unit.KIP: Unit.KN, Unit.KIP_IN: Unit.KN_MM}[unit] if si else unit
        )
        return PhysicalQuantity.of(value, unit).to(target)

    hardware = SupportHardware(
        q("1.25"), q(".125"), q(".75"), q(".3125"), q(".75"), q(".4375"), q(".125")
    )

    def connector(center: str) -> AngleBaseConnector:
        return AngleBaseConnector(
            WallMomentAngle(
                AngleConnectorGeometry(q("6"), q("8"), q("6"), q(".5"), q(".25"), (q("0"), q("0"))),
                WallMomentPattern(2, 2, q("3"), q("2"), q(center)),
                WallMomentPattern(2, 2, q("3"), q("2"), q("3")),
                WIMomentSpliceFastener(
                    q(".5"), q(".563"), "ASTM_F593_17_GROUP_2_316_316L", "EXCLUDED"
                ),
                ExternalAnchorGeometry(q(".5"), q(".563"), q("4"), q("1.25"), q(".125")),
            ),
            q("0"),
            hardware,
        )

    return ColumnMomentBaseRequest(
        "stage-4.5-default",
        MomentBaseColumn(
            cast(Family, family),
            q(width),
            q(depth),
            q(".5"),
            q(".5"),
            q(".5"),
            q("18"),
            q("0"),
            q("0"),
        ),
        layout,
        AngleBaseFoundation(q("40"), q("40"), q("12")),
        connector("3"),
        connector("3"),
        connector("6"),
        connector("6"),
        ColumnMomentActions(
            q("-20", Unit.KIP),
            q("5", Unit.KIP),
            q("-3", Unit.KIP),
            q("60", Unit.KIP_IN),
            q("40", Unit.KIP_IN),
            q("0", Unit.KIP_IN),
        ),
    )


def default_column_moment_base_ui_request(
    family: Family = "WI", layout: Layout = "FOUR_XY", *, si: bool = False
) -> ColumnMomentBaseRequest:
    """Generic R2 starting geometry; historical named fixtures remain unchanged.

    Two bolts straddle each selected face's tangential centerline. Zero offset
    uses the native face-centered placement, including column translation. The
    three-inch gauge clears the W/I web without shifting a flange angle. Neither
    centered geometry nor a shared shank supplies branch-sharing authority.
    """
    request = default_column_moment_base_request(
        {"WI": "WI12", "RHS": "RHS8", "SRS": "SRS8"}[family], layout, si=si
    )

    def connector(value: AngleBaseConnector) -> AngleBaseConnector:
        unit = value.extrusion_center.unit
        return replace(
            value,
            extrusion_center=PhysicalQuantity.of("0", Unit.IN).to(unit),
            angle=replace(
                value.angle,
                member_pattern=replace(
                    value.angle.member_pattern,
                    across=2,
                    along=1,
                    gauge=PhysicalQuantity.of("3", Unit.IN).to(unit),
                ),
                support_pattern=replace(value.angle.support_pattern, across=1, along=1),
            ),
        )

    return replace(
        request,
        x_positive=connector(request.x_positive),
        x_negative=connector(request.x_negative),
        y_positive=connector(request.y_positive),
        y_negative=connector(request.y_negative),
    )
