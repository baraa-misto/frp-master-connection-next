"""Internal exact-bound DCTN qualification records; never public request data.

An empty production registry is deliberate. A reference string is not a source,
and static row/shaft equilibrium is not local material or installation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.double_channel_truss_node import DCTNRequiredCheck
from frp_master_connection.calculation.inputs import EndUseFactors
from frp_master_connection.calculation.properties import MaterialPropertySnapshot
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity
from frp_master_connection.calculation.support_attachment_response import qualified_source
from frp_master_connection.domain.double_channel_truss_node import require_quantity
from frp_master_connection.domain.material_architecture import EngineeringPropertySource


@dataclass(frozen=True, slots=True)
class DCTNMaterialSource:
    reference: str
    owner_id: str
    source: EngineeringPropertySource
    exact_binding: str
    material: MaterialPropertySnapshot
    factors: EndUseFactors
    lambda_factor: Decimal
    full_depth_solid_bearing: bool = False

    def __post_init__(self) -> None:
        if not self.lambda_factor.is_finite() or self.lambda_factor <= 0:
            raise ValueError("DCTN time-effect factor requires explicit positive authority")


@dataclass(frozen=True, slots=True)
class DCTNHardwareSource:
    reference: str
    source: EngineeringPropertySource
    exact_binding: str
    nominal_shear_stress: PhysicalQuantity
    installation_coverage: tuple[str, ...]

    def __post_init__(self) -> None:
        require_quantity(self.nominal_shear_stress, Dimension.STRESS)
        if self.nominal_shear_stress.canonical_magnitude <= 0:
            raise ValueError("DCTN hardware strength must be positive")


HARDWARE_COVERAGE = frozenset(
    {"PRODUCT_GRADE_CONDITION", "ACTUAL_GRIP", "THREAD_PLANES", "NUT", "WASHERS", "SNUG_TIGHT"}
)


@dataclass(frozen=True, slots=True)
class DCTNQualifiedMechanism:
    """Source-issued results for unresolved mechanisms at this exact assembly/load.

    These cannot replace applicable native pin bearing or other native FRP checks.
    Coverage and every issued numerical result are retained, including failures.
    """

    reference: str
    owner_id: str
    source: EngineeringPropertySource
    exact_binding: str
    coverage: tuple[str, ...]
    checks: tuple[DCTNRequiredCheck, ...]
    method: str


@dataclass(frozen=True, slots=True)
class DCTNSources:
    materials: tuple[DCTNMaterialSource, ...] = ()
    hardware: tuple[DCTNHardwareSource, ...] = ()
    mechanisms: tuple[DCTNQualifiedMechanism, ...] = ()

    def __post_init__(self) -> None:
        for records in (self.materials, self.hardware, self.mechanisms):
            identities = tuple((r.reference, r.exact_binding) for r in records)
            if any(not ref or not binding for ref, binding in identities) or len(
                set(identities)
            ) != len(identities):
                raise ValueError("DCTN server sources require unique nonempty exact-bound keys")


EMPTY_SOURCES = DCTNSources()


def source_matches(source: EngineeringPropertySource, expected: str, actual: str) -> bool:
    return bool(expected and expected == actual and qualified_source(source))


def material_source(
    registry: DCTNSources, reference: str, owner: str, binding: str
) -> DCTNMaterialSource | None:
    return next(
        (
            s
            for s in registry.materials
            if s.reference == reference
            and s.owner_id == owner
            and source_matches(s.source, binding, s.exact_binding)
        ),
        None,
    )


def hardware_source(
    registry: DCTNSources, reference: str, binding: str
) -> DCTNHardwareSource | None:
    return next(
        (
            s
            for s in registry.hardware
            if s.reference == reference
            and source_matches(s.source, binding, s.exact_binding)
            and set(s.installation_coverage) >= HARDWARE_COVERAGE
        ),
        None,
    )


def mechanism_checks(
    registry: DCTNSources,
    reference: str,
    owner: str,
    binding: str,
    required: frozenset[str],
) -> tuple[DCTNRequiredCheck, ...] | None:
    record = next(
        (
            s
            for s in registry.mechanisms
            if s.reference == reference
            and s.owner_id == owner
            and source_matches(s.source, binding, s.exact_binding)
        ),
        None,
    )
    if (
        record is None
        or not required <= set(record.coverage)
        or not record.method.strip()
        or not record.checks
        or any(
            c.owner_id != owner
            or c.status not in {"PASS", "FAIL"}
            or c.source_reference != reference
            for c in record.checks
        )
        or len({c.check_id for c in record.checks}) != len(record.checks)
    ):
        return None
    return record.checks


def dctn_binding(scope: str, owner: str, physical: object, response: object) -> str:
    return dctn_fingerprint(
        ("DCTN_EXACT_QUALIFIED_SOURCE_BINDING_RC1", scope, owner, physical, response)
    )
