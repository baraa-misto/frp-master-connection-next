"""HYB1 pure workbook-reference arithmetic; no public or physical method activation.

Cell locators refer to the immutable RHM workbook, SHA256 WORKBOOK_SHA256.
The positive directional, direct/uniform reference is not an eccentric demand model.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from .quantities import PhysicalQuantity, Unit, decimal_value

WORKBOOK_SHA256 = "37402af592b45e3fa1a869c0470a758c74d0c1d706d31d8f4bc981096e0d6be5"
METHOD_VERSION = "RHM-WORKBOOK-REFERENCE-HYB1-R00"
PI = Decimal("3.1415926535897932384626433832795028841971693993751058209749445923078164")
PRECISION = 60


class RhmShape(StrEnum):
    """Actual workbook columns, not a new MAT1 property catalog."""

    W_I = "W_I"
    ANGLE_L3_OR_LESS = "ANGLE_L3_OR_LESS"
    ANGLE_L4_OR_LARGER = "ANGLE_L4_OR_LARGER"


class ReferenceStream(StrEnum):
    HISTORICAL_REPLICATION = "HISTORICAL_REPLICATION"
    CORRECTED_REFERENCE = "CORRECTED_REFERENCE"


class StormSetting(StrEnum):
    NONE = "NONE"
    HISTORICAL_TWO_THIRDS = "HISTORICAL_TWO_THIRDS"
    UNADOPTED_INCREASE = "UNADOPTED_INCREASE"


class OptionalState(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE = "INCOMPLETE"
    PASS = "PASS"  # noqa: S105 - engineering outcome enumeration, not a password
    FAIL = "FAIL"


def reference_quantity(
    quantity: PhysicalQuantity, unit: Unit, *, zero_allowed: bool = False
) -> Decimal:
    """Check dimension and magnitude before any reference arithmetic."""

    if not isinstance(quantity, PhysicalQuantity):
        raise TypeError("RHM quantities must use the existing PhysicalQuantity contract.")
    value = quantity.to(unit).magnitude
    if value < 0 or (value == 0 and not zero_allowed):
        raise ValueError("RHM reference operands must be positive; demands may be true zero.")
    return value


def reference_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("A bolt or shear-plane count must be an integer, not Boolean.")
    if value <= 0:
        raise ValueError("A bolt or shear-plane count must be positive.")
    return value


@dataclass(frozen=True, slots=True)
class RhmAllowable:
    """Recorded listed stress divided by its own explicit source safety factor."""

    listed_stress: PhysicalQuantity
    safety_factor: Decimal
    source_cell: str
    factor_cell: str
    shape: RhmShape
    product_id: str = "RHM_WORKBOOK_POLYESTER_TABLE"
    value_definition: str = "WORKBOOK_LISTED_STRENGTH_STATISTICAL_BASIS_UNESTABLISHED"

    def __post_init__(self) -> None:
        reference_quantity(self.listed_stress, Unit.KSI)
        factor = decimal_value(self.safety_factor)
        if factor <= 0:
            raise ValueError("An explicit positive safety factor is required.")
        if not self.source_cell or not self.factor_cell or not isinstance(self.shape, RhmShape):
            raise ValueError("Property cell, factor cell and actual shape column are required.")
        if self.product_id != "RHM_WORKBOOK_POLYESTER_TABLE":
            raise ValueError("The reference table cannot resolve a different product.")
        if self.value_definition != "WORKBOOK_LISTED_STRENGTH_STATISTICAL_BASIS_UNESTABLISHED":
            raise ValueError("No average-to-characteristic or allowable-to-LRFD conversion exists.")
        object.__setattr__(self, "safety_factor", factor)

    @property
    def stress(self) -> PhysicalQuantity:
        with localcontext() as context:
            context.prec = PRECISION
            return PhysicalQuantity.of(
                self.listed_stress.to(Unit.KSI).magnitude / self.safety_factor, Unit.KSI
            )


# Keys are printed property regions/directions. Values are the original listed psi.
# Column D=W/I, E=L3 or less, F=L4 or larger. No live material provider uses this map.
_PROPERTIES = {
    "FLANGE_BEARING_LW": (112, ("33000", "30000", "33000")),
    "FLANGE_BEARING_CW": (115, ("23000", "18000", "33000")),
    "WEB_BEARING_LW": (133, ("33980", "30000", "33000")),
    "WEB_BEARING_CW": (136, ("30000", "18000", "33000")),
    "WEB_TENSION_LW": (139, ("30300", "33000", "31000")),
    "WEB_TENSION_CW": (142, ("10500", "7500", "16500")),
    "WEB_SHEAR_LW": (145, ("7000", "7000", "7000")),
    "WEB_SHEAR_CW": (148, ("4500", "4500", "4500")),
}


def workbook_allowable(
    shape: RhmShape, property_key: str, *, product_id: str, resin: str = "POLYESTER"
) -> RhmAllowable:
    """Resolve only a recorded workbook property; this grants no Angle method."""

    if not isinstance(shape, RhmShape) or resin != "POLYESTER":
        raise ValueError("A governed workbook shape and polyester reference are required.")
    if property_key not in _PROPERTIES:
        raise ValueError("The requested region/direction property is not recorded.")
    index = tuple(RhmShape).index(shape)
    column = ("D", "E", "F")[index]
    row, values = _PROPERTIES[property_key]
    return RhmAllowable(
        PhysicalQuantity.of(values[index], Unit.PSI),
        Decimal(4),
        f"Dim & Properties!{column}{row}",
        f"Dim & Properties!{column}{row + 1}",
        shape,
        product_id,
    )


@dataclass(frozen=True, slots=True)
class RhmOperand:
    name: str
    quantity: PhysicalQuantity
    source_cell: str
    meaning: str


@dataclass(frozen=True, slots=True)
class RhmComparison:
    method_id: str
    cells: tuple[str, ...]
    operands: tuple[RhmOperand, ...]
    capacities: tuple[PhysicalQuantity, ...]
    components: tuple[Decimal, ...]
    utilization: Decimal
    numerical_outcome: str
    equation: str
    assumptions: tuple[str, ...]
    basis: str = "ASD"
    source_domain: str = "WORKBOOK_REFERENCE"
    mapping: str = "REFERENCE_ONLY"
    method_adoption: str = "PENDING_OWNER_REVIEW"


def additive_comparison(
    method_id: str,
    demands: tuple[PhysicalQuantity, ...],
    capacities: tuple[PhysicalQuantity, ...],
    *,
    cells: tuple[str, ...],
    operands: tuple[RhmOperand, ...],
    equation: str,
    assumptions: tuple[str, ...],
) -> RhmComparison:
    """Each term keeps its own simultaneous demand and valid allowable capacity."""

    if not demands or len(demands) != len(capacities):
        raise ValueError("Every directional term requires its own capacity.")
    with localcontext() as context:
        context.prec = PRECISION
        terms = tuple(
            reference_quantity(d, Unit.KIP, zero_allowed=True) / reference_quantity(r, Unit.KIP)
            for d, r in zip(demands, capacities, strict=True)
        )
        ratio = sum(terms, Decimal(0))
    return RhmComparison(
        method_id,
        cells,
        operands,
        capacities,
        terms,
        ratio,
        "PASS" if ratio <= 1 else "FAIL",
        equation,
        assumptions,
    )


def bearing_capacity(
    count: int, diameter: PhysicalQuantity, thickness: PhysicalQuantity, allowable: RhmAllowable
) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = PRECISION
        value = (
            reference_count(count)
            * reference_quantity(diameter, Unit.IN)
            * reference_quantity(thickness, Unit.IN)
            * reference_quantity(allowable.stress, Unit.KSI)
        )
        return PhysicalQuantity.of(value, Unit.KIP)


def bolt_shear_capacity(
    count: int,
    planes: int,
    diameter: PhysicalQuantity,
    allowable_shear: PhysicalQuantity,
) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = PRECISION
        d = reference_quantity(diameter, Unit.IN)
        value = (
            reference_count(count)
            * reference_count(planes)
            * PI
            * d
            * d
            / 4
            * reference_quantity(allowable_shear, Unit.KSI)
        )
        return PhysicalQuantity.of(value, Unit.KIP)


def local_shear_capacity(
    planes: int, length: PhysicalQuantity, thickness: PhysicalQuantity, allowable: RhmAllowable
) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = PRECISION
        value = (
            reference_count(planes)
            * reference_quantity(length, Unit.IN)
            * reference_quantity(thickness, Unit.IN)
            * reference_quantity(allowable.stress, Unit.KSI)
        )
        return PhysicalQuantity.of(value, Unit.KIP)


def global_block_capacity(
    shear_area: PhysicalQuantity,
    tension_area: PhysicalQuantity,
    shear_allowable: RhmAllowable,
    tension_allowable: RhmAllowable,
) -> PhysicalQuantity:
    with localcontext() as context:
        context.prec = PRECISION
        value = reference_quantity(shear_area, Unit.IN2) * reference_quantity(
            shear_allowable.stress, Unit.KSI
        ) + reference_quantity(tension_area, Unit.IN2) * reference_quantity(
            tension_allowable.stress, Unit.KSI
        )
        return PhysicalQuantity.of(value, Unit.KIP)


@dataclass(frozen=True, slots=True)
class OptionalComparison:
    component_id: str
    state: OptionalState
    reason: str
    comparison: RhmComparison | None = None


def optional_part_comparison(
    component_id: str,
    *,
    present: bool,
    transfer_established: bool,
    demand: PhysicalQuantity | None,
    capacity: PhysicalQuantity | None,
) -> OptionalComparison:
    """Absent own-part checks are N/A; receiving-member coverage is unaffected."""

    if component_id not in ("REINFORCING_ANGLE_FASTENERS", "BEAM_DOUBLER_ADHESIVE"):
        raise ValueError("Optional-part N/A cannot cover the receiving member.")
    if not isinstance(present, bool) or not isinstance(transfer_established, bool):
        raise TypeError("Optional presence and transfer declaration must be Boolean.")
    if not present:
        return OptionalComparison(component_id, OptionalState.NOT_APPLICABLE, "OWN_PART_ABSENT")
    if not transfer_established or demand is None or capacity is None:
        return OptionalComparison(
            component_id, OptionalState.INCOMPLETE, "ACTIVE_PART_TRANSFER_OR_DATA_MISSING"
        )
    result = additive_comparison(
        "RHM_OPTIONAL_REFERENCE",
        (demand,),
        (capacity,),
        cells=("Calcs!D181", "Calcs!D195"),
        operands=(),
        equation="supplied applicable demand / supplied reference allowable capacity",
        assumptions=("REFERENCE_ONLY; supplied capacity does not validate adhesive transfer",),
    )
    return OptionalComparison(
        component_id,
        OptionalState.PASS if result.numerical_outcome == "PASS" else OptionalState.FAIL,
        "REFERENCE_COMPARISON_ONLY",
        result,
    )


def validate_reference_storm(stream: ReferenceStream, setting: StormSetting) -> Decimal:
    if not isinstance(stream, ReferenceStream) or not isinstance(setting, StormSetting):
        raise TypeError("Reference stream and storm setting require governed enums.")
    if setting is StormSetting.NONE:
        return Decimal(1)
    if (
        stream is ReferenceStream.HISTORICAL_REPLICATION
        and setting is StormSetting.HISTORICAL_TWO_THIRDS
    ):
        with localcontext() as context:
            context.prec = PRECISION
            return Decimal(2) / 3
    raise ValueError("RHM storm adjustment is unadopted; corrected reference uses NONE only.")


def area_from_reference_lengths(
    length: PhysicalQuantity, thickness: PhysicalQuantity
) -> PhysicalQuantity:
    """Submitted reference path only; not a hole deduction or actual geometry adapter."""

    with localcontext() as context:
        context.prec = PRECISION
        return PhysicalQuantity.of(
            reference_quantity(length, Unit.IN) * reference_quantity(thickness, Unit.IN), Unit.IN2
        )
