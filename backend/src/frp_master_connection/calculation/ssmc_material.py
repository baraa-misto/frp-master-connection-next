"""Plate-only source-selection contract; contains no strength or design equation."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity
from frp_master_connection.domain.ssmc import PLATE_POLICY

# Shear/TT/stiffness are deliberately not aliases for transverse normal strength.
PROPERTY_DIRECTIONS = MappingProxyType(
    {
        "NORMAL_TENSION": "CW",
        "NORMAL_COMPRESSION": "CW",
        "FLEXURE": "CW",
        "BEARING": "CW",
        "IN_PLANE_SHEAR": "LT",
        "INTERLAMINAR_SHEAR": "INTERLAMINAR",
        "THROUGH_THICKNESS": "TT",
        "STIFFNESS": "ORTHOTROPIC",
        "STABILITY": "QUALIFIED_METHOD",
        "NOTCH_CORNER": "QUALIFIED_METHOD",
    }
)


@dataclass(frozen=True, slots=True)
class SSMCQualifiedProperty:
    """Server-resolved authority for one exact check/domain, not public input.

    For CW normal/bearing properties the authority must explicitly establish
    conservatism. If an alternate orientation is compared, both values must be
    qualified like-for-like design properties, not unrelated coupon strengths.
    """

    binding: str
    check: str
    direction: str
    value: PhysicalQuantity
    source_sha256: str
    approval_sha256: str
    method_version: str
    cw_conservatism_demonstrated: bool
    qualified_alternate: PhysicalQuantity | None = None


EMPTY_PROPERTY_REGISTRY: Mapping[tuple[str, str], SSMCQualifiedProperty] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class SSMCPropertySelection:
    check: str
    required_direction: str
    status: str
    authority: SSMCQualifiedProperty | None
    policy: str = PLATE_POLICY
    owner: str = "MITER_WEB_PLATE"
    isotropic: bool = False
    longitudinal_strength_credit: bool = False


def select_ssmc_property(
    binding: str,
    check: str,
    registry: Mapping[tuple[str, str], SSMCQualifiedProperty] = EMPTY_PROPERTY_REGISTRY,
    *,
    owner: str = "MITER_WEB_PLATE",
    policy: str = PLATE_POLICY,
    isotropic: bool = False,
) -> SSMCPropertySelection:
    if owner != "MITER_WEB_PLATE" or policy != PLATE_POLICY or isotropic:
        raise ValueError("SSMC_CW_POLICY_INVALID")
    if check not in PROPERTY_DIRECTIONS:
        raise ValueError("SSMC_CW_POLICY_INVALID")
    direction = PROPERTY_DIRECTIONS[check]
    record = registry.get((binding, check))
    status = "SSMC_CW_SOURCE_REQUIRED"
    if record is not None:
        valid = (
            record.binding == binding
            and record.check == check
            and record.direction == direction
            # A scalar strength cannot qualify an orthotropic E/G/nu bundle,
            # stability method or notch/corner model. Those separate obligations
            # remain source-required in this bounded milestone.
            and direction not in {"ORTHOTROPIC", "QUALIFIED_METHOD"}
            and record.value.dimension == Dimension.STRESS
            and bool(record.method_version)
            and record.value.magnitude > 0
            and all(
                len(h) == 64 and all(c in "0123456789abcdefABCDEF" for c in h)
                for h in (record.source_sha256, record.approval_sha256)
            )
        )
        if not valid:
            raise ValueError("SSMC_TRUSTED_AUTHORITY_NOT_BOUND")
        if direction == "CW" and (
            not record.cw_conservatism_demonstrated
            or (
                record.qualified_alternate is not None
                and (
                    record.value.dimension != record.qualified_alternate.dimension
                    or record.value.canonical_magnitude
                    > record.qualified_alternate.canonical_magnitude
                )
            )
        ):
            status = "SSMC_CW_CONSERVATISM_CONFLICT"
            record = None
        else:
            status = "QUALIFIED_PROPERTY_BOUND_NOT_WHOLE_PLATE_RESISTANCE"
    return SSMCPropertySelection(check, direction, status, record)
