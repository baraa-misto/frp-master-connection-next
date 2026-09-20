"""DCTN renderer-neutral physical records shared inward by geometry and response."""

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.angle_connector_core import Rational3
from frp_master_connection.calculation.block_shear_planning import BlockShearPlanSet
from frp_master_connection.calculation.geometry_mapping import (
    CodeGeometryValidation,
    GeometryToCodeMapping,
)
from frp_master_connection.calculation.multirow import FirstRowGeometryMapping, MaterialDirection
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.double_channel_truss_node import DCTNForm
from frp_master_connection.domain.member_profile import MemberProfile
from frp_master_connection.domain.rectangular_full_through_bolt import FullThroughBoltPath
from frp_master_connection.geometry.multirow import MultiRowGeometry
from frp_master_connection.geometry.placement import PlacedComponentGeometry3D


@dataclass(frozen=True, slots=True)
class DCTNPlacedMember:
    physical_id: str
    profile: MemberProfile
    placement: PlacedComponentGeometry3D
    start: Rational3
    u: Rational3
    v: Rational3
    w: Rational3


@dataclass(frozen=True, slots=True)
class DCTNHole:
    hole_id: str
    group_id: str
    owner_id: str
    shaft_id: str
    surface_id: str
    center: Rational3
    hole_valid: bool
    hardware_footprint_valid: bool


@dataclass(frozen=True, slots=True)
class DCTNShaft:
    bolt_id: str
    member_id: str
    row: int
    side: str
    start: Rational3
    end: Rational3
    layer_owners: tuple[str, ...]
    layer_lengths: tuple[Decimal, ...]
    free_span: Decimal
    native_full_through_core: FullThroughBoltPath | None
    head_envelope: PlacedComponentGeometry3D
    nut_envelope: PlacedComponentGeometry3D
    physical_bolt_count: int = 1
    head_count: int = 1
    nut_count: int = 1
    exterior_washer_count: int = 2
    cavity_hardware_count: int = 0


@dataclass(frozen=True, slots=True)
class DCTNRowGeometry:
    member_id: str
    row: int
    from_start: Decimal
    axis_point: Rational3
    negative_point: Rational3
    positive_point: Rational3
    shaft_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DCTNGeometry:
    status: str
    reasons: tuple[str, ...]
    length_unit: Unit
    gap: Decimal
    members: tuple[DCTNPlacedMember, ...]
    rows: tuple[DCTNRowGeometry, ...]
    holes: tuple[DCTNHole, ...]
    shafts: tuple[DCTNShaft, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class DCTNPlanePlan:
    owner_id: str
    group_id: str
    member_id: str
    incoming_form: DCTNForm
    thickness: PhysicalQuantity
    force_direction: tuple[float, float]
    geometry: MultiRowGeometry
    first_row: FirstRowGeometryMapping
    block_paths: BlockShearPlanSet | None
    reasons: tuple[str, ...]
    material_direction: MaterialDirection
    native_bolt_mappings: tuple[GeometryToCodeMapping, ...] = ()


@dataclass(frozen=True, slots=True)
class DCTNBoltCode:
    shaft_id: str
    owner_id: str
    physical_element_id: str
    mapping: GeometryToCodeMapping
    validation: CodeGeometryValidation
