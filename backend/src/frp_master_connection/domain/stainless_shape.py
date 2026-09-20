"""Internal server-owned hot-shape authority, separate from frozen flat products.

There is deliberately no catalogue, DTO, public registration or procurement claim.
Section moduli are source-native in3; all other dimensional inputs use quantities.
Only records supplied by a trusted application context can authorize evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit

SOURCE = "A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1"
FY = PhysicalQuantity.of(25, Unit.KSI)
FU = PhysicalQuantity.of(70, Unit.KSI)
ELASTIC = PhysicalQuantity.of(28000, Unit.KSI)
SHEAR_MODULUS = PhysicalQuantity.of(10800, Unit.KSI)
PRODUCT = "A276_A484_HOT_ROLLED_EXTRUDED_UNWELDED_316_FAMILY_RC1"
GRADES = (
    "GENERIC_316SS_CONSERVATIVE_BASIS",
    "S31600_316",
    "S31603_316L",
    "S31600_S31603_DUAL_CERTIFIED",
)


@dataclass(frozen=True, slots=True)
class ShapeProduct:
    id: str
    source: str
    content_sha256: str
    grade: str = GRADES[0]
    route: str = PRODUCT
    specification: str = "ASTM A276/A276M"
    general_requirements: str = "ASTM A484/A484M"
    processing: str = "HOT_ROLLED"
    condition: str = "A"
    source_sha256: str = SOURCE
    fy: PhysicalQuantity = FY
    fu: PhysicalQuantity = FU
    elastic_modulus: PhysicalQuantity = ELASTIC
    shear_modulus: PhysicalQuantity = SHEAR_MODULUS
    welded: bool = False
    strength_credit: bool = False
    source_system: str = "US_CUSTOMARY"


@dataclass(frozen=True, slots=True)
class ShapeElement:
    id: str
    width: PhysicalQuantity
    thickness: PhysicalQuantity
    boundary_source: str
    stiffened: bool = False


@dataclass(frozen=True, slots=True)
class ShapeAxis:
    id: str
    radius: PhysicalQuantity
    smin_in3: Decimal
    sft_in3: Decimal


@dataclass(frozen=True, slots=True)
class ShapeSection:
    id: str
    form: str
    geometry_sha256: str
    geometry_source: str
    area: PhysicalQuantity
    centroid: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    elements: tuple[ShapeElement, ...]
    axes: tuple[ShapeAxis, ShapeAxis]
    equal_leg: bool = True
    principal_frame: str = "SECTION_PRINCIPAL_W_Z"
    net_area: PhysicalQuantity | None = None
    net_area_source: str = ""


@dataclass(frozen=True, slots=True)
class ShearLag:
    case: str
    source: str
    all_elements_direct: bool = False
    x: PhysicalQuantity | None = None
    length: PhysicalQuantity | None = None
    fasteners_per_line: int = 0


@dataclass(frozen=True, slots=True)
class ShapeStability:
    axis: str
    effective_length: PhysicalQuantity
    source: str
    lb: PhysicalQuantity
    ly: PhysicalQuantity
    lr: PhysicalQuantity
    fcr: PhysicalQuantity | None = None


@dataclass(frozen=True, slots=True)
class ShapeDemand:
    id: str
    route: str
    body: str
    region: str
    load_combination: str
    frame: str
    reference: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    axial: PhysicalQuantity
    moment_w: PhysicalQuantity
    moment_z: PhysicalQuantity
    shear: PhysicalQuantity
    torsion: PhysicalQuantity
    sign_convention: str = "POSITIVE_AXIAL_TENSION_PRINCIPAL_MOMENT_MAGNITUDES"


@dataclass(frozen=True, slots=True)
class ShapeRequest:
    product: ShapeProduct
    section: ShapeSection
    demand: ShapeDemand
    checks: tuple[str, ...]
    shear_lag: ShearLag | None = None
    shear_elements: tuple[ShapeElement, ...] = ()
    stability: tuple[ShapeStability, ...] = ()
    e4_fe: PhysicalQuantity | None = None
    e4_source: str = ""
    local_mechanism_required: bool = False
    family_activation_requested: bool = False


@dataclass(frozen=True, slots=True)
class LocalShapeSnapshot:
    """Already-resolved P1/P2 result: no production imports or recomputation."""

    provider: str
    body: str
    region: str
    request_sha256: str
    result_sha256: str
    source_sha256: str
    covered_mechanism: str
    status: str


@dataclass(frozen=True, slots=True)
class TrustedShapeRecord:
    request: ShapeRequest
    id: str
    source_sha256: str
    section_qualification: str
    response_fingerprint: str
    response_demand: ShapeDemand
    response_authority: str
    local_snapshots: tuple[LocalShapeSnapshot, ...] = ()
    local_qualification: str = ""


@dataclass(frozen=True, slots=True)
class ShapeContext:
    records: tuple[TrustedShapeRecord, ...] = ()
