"""SSMC-specific trusted binding validator, never a contact/compatibility solver."""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    components,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity

REQUIRED_RESPONSE = frozenset(
    {
        "SHAFT_SHEAR",
        "BOLT_AXIS_TENSION",
        "PRYING",
        "SHAFT_BENDING",
        "PLATE_LOCAL_BENDING",
        "WEB_LOCAL_BENDING",
        "UNILATERAL_CONTACT",
        "SLIP_COMPATIBILITY",
    }
)


@dataclass(frozen=True, slots=True)
class SSMCResponseAction:
    physical_id: str
    group_id: str
    wrench: AngleWrench
    mechanism: str


@dataclass(frozen=True, slots=True)
class SSMCResolvedResponseQuantity:
    owner_id: str
    mechanism: str
    values: tuple[PhysicalQuantity, ...]


@dataclass(frozen=True, slots=True)
class SSMCTrustedResponse:
    source_id: str
    contract: str
    binding: str
    method_version: str
    source_sha256: str
    approval_sha256: str
    compatibility_evidence_sha256: str
    applicability: str
    covered_mechanisms: frozenset[str]
    shaft_ids: tuple[str, ...]
    actions: tuple[SSMCResponseAction, ...]
    resolved_quantities: tuple[SSMCResolvedResponseQuantity, ...]
    authority_snapshots: tuple[tuple[str, str], ...]
    numerical_failures: tuple[str, ...] = ()


EMPTY_RESPONSE_REGISTRY: Mapping[str, SSMCTrustedResponse] = MappingProxyType({})


def validate_ssmc_response(
    record: SSMCTrustedResponse,
    binding: str,
    shaft_groups: Mapping[str, str],
    targets: Mapping[str, AngleWrench],
    origin: ExactQuantityVector3D,
) -> None:
    shafts = tuple(shaft_groups)
    if record.binding != binding or record.contract != "SSMC-2-RC1":
        raise ValueError("SSMC_TRUSTED_RESPONSE_BINDING_MISMATCH")
    if not all((record.source_id, record.method_version, record.applicability)) or any(
        len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest)
        for digest in (
            record.source_sha256,
            record.approval_sha256,
            record.compatibility_evidence_sha256,
        )
    ):
        raise ValueError("SSMC_TRUSTED_AUTHORITY_NOT_BOUND")
    # These are immutable server-resolved snapshot identities, not public source
    # strings. The approved record binds them together with the exact request
    # fingerprint (cuts, polygon, layers, installation and all applied actions).
    required_snapshots = {
        "HORIZONTAL_STRINGER_MATERIAL",
        "INCLINED_STRINGER_MATERIAL",
        "MITER_WEB_PLATE_MATERIAL",
        "HARDWARE_SOURCE",
        "CONTACT_SLIP_ASSUMPTIONS",
    }
    if (
        {owner for owner, _ in record.authority_snapshots} != required_snapshots
        or len(record.authority_snapshots) != len(required_snapshots)
        or any(
            len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest)
            for _, digest in record.authority_snapshots
        )
    ):
        raise ValueError("SSMC_TRUSTED_AUTHORITY_NOT_BOUND")
    if set(record.shaft_ids) != set(shafts) or len(record.shaft_ids) != len(set(record.shaft_ids)):
        raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    if record.covered_mechanisms != REQUIRED_RESPONSE:
        raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    ids = tuple(a.physical_id for a in record.actions)
    if len(set(ids)) != len(ids) or not set(shafts).issubset(ids):
        raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    if any(
        a.group_id not in targets or a.mechanism not in {"SHAFT", "CONTACT"} for a in record.actions
    ):
        raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    for action in record.actions:
        if action.mechanism == "SHAFT":
            if shaft_groups.get(action.physical_id) != action.group_id:
                raise ValueError("SSMC_SHAFT_OWNERSHIP_INVALID")
        elif action.physical_id in shaft_groups:
            raise ValueError("SSMC_SHAFT_OWNERSHIP_INVALID")
    expected_coverage = {
        (shaft, mechanism)
        for shaft in shafts
        for mechanism in ("SHAFT_SHEAR", "BOLT_AXIS_TENSION", "PRYING", "SHAFT_BENDING")
    } | {
        (group, mechanism)
        for group in targets
        for mechanism in (
            "PLATE_LOCAL_BENDING",
            "WEB_LOCAL_BENDING",
            "UNILATERAL_CONTACT",
            "SLIP_COMPATIBILITY",
        )
    }
    observed = tuple((q.owner_id, q.mechanism) for q in record.resolved_quantities)
    if set(observed) != expected_coverage or len(observed) != len(set(observed)):
        raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    for quantity in record.resolved_quantities:
        dimension = (
            Dimension.MOMENT
            if "BENDING" in quantity.mechanism
            else Dimension.LENGTH
            if quantity.mechanism == "SLIP_COMPATIBILITY"
            else Dimension.FORCE
        )
        expected_count = (
            2
            if quantity.mechanism == "SHAFT_SHEAR"
            else 1
            if quantity.mechanism in {"BOLT_AXIS_TENSION", "PRYING"}
            else 3
        )
        if len(quantity.values) != expected_count or any(
            q.dimension != dimension for q in quantity.values
        ):
            raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
        if quantity.owner_id in shaft_groups:
            action = next(a for a in record.actions if a.physical_id == quantity.owner_id)
            force, moment = components(action.wrench.force), components(action.wrench.moment)
            expected_values = (
                (force[0], force[2])
                if quantity.mechanism == "SHAFT_SHEAR"
                else (force[1],)
                if quantity.mechanism == "BOLT_AXIS_TENSION"
                else moment
                if quantity.mechanism == "SHAFT_BENDING"
                else None
            )
            if (
                expected_values is not None
                and tuple(Fraction(q.canonical_magnitude) for q in quantity.values)
                != expected_values
            ):
                raise ValueError("SSMC_TRUSTED_RESPONSE_COVERAGE_INVALID")
    for group, target in targets.items():
        expected = shift_angle_wrench(target, origin)
        actions = tuple(
            shift_angle_wrench(a.wrench, origin) for a in record.actions if a.group_id == group
        )
        for name in ("force", "moment"):
            actual = tuple(sum(components(getattr(a, name))[i] for a in actions) for i in range(3))
            if actual != components(getattr(expected, name)):
                raise ValueError("SSMC_TRUSTED_RESPONSE_EQUILIBRIUM_INVALID")


def required_design_status(failures: tuple[str, ...], blockers: tuple[str, ...]) -> str:
    if failures:
        return "FAIL"
    return "ENGINEERING_REVIEW_REQUIRED" if blockers else "PASS"
