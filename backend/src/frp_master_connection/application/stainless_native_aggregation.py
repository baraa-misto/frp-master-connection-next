"""Canonical native ownership to CME-3 aggregation, without numerical reruns.

Only CONNECTOR_BODY resistance is superseded. Retained native numerical FAILs
remain governing independently of stainless response/section qualification.
"""

from dataclasses import replace

from frp_master_connection.application.angle_column_base_design import BaseZoneResult
from frp_master_connection.application.column_moment_base_design import ColumnMomentZoneResult
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.stainless_connection_design import (
    BoundNonBodyCheck,
    NonBodyAuthority,
)
from frp_master_connection.application.stainless_family_activation import RequiredCheck
from frp_master_connection.application.stainless_moment_ownership import MomentPartition
from frp_master_connection.application.stainless_native_results import (
    NativeCheckPartition,
    physical_owner,
)
from frp_master_connection.application.stainless_splice_ownership import SplicePartition
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.application.wi_frp_support_moment_design import (
    LocalZoneResult,
    SupportBoltCheck,
)
from frp_master_connection.application.wi_wall_moment_design import WallMomentBearing
from frp_master_connection.application.wi_wall_moment_sources import WallMomentAttachmentResult
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.multirow_engine import MultiRowCheckResult
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    AsymmetricTwoPlaneBoltResult,
)
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole


def retained_native_authority(
    route: str,
    assembly: MaterialAssembly,
    partition: NativeCheckPartition | SplicePartition | MomentPartition,
) -> NonBodyAuthority:
    checks: list[BoundNonBodyCheck] = []
    blockers: list[str] = []
    identities: set[tuple[str, str]] = set()

    def add(
        identity: str, owner: CanonicalComponent, comparison: str, fingerprint: str, record: object
    ) -> None:
        canonical = physical_owner(assembly, owner.physical_id)
        if canonical != owner or owner.role is ComponentRole.CONNECTOR_BODY:
            raise ValueError("STAINLESS_FRP_BODY_FALLBACK_PROHIBITED")
        key = (owner.physical_id, identity)
        if key in identities:
            raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
        identities.add(key)
        if comparison in {"PASS", "FAIL"}:
            checks.append(
                BoundNonBodyCheck(
                    owner.physical_id,
                    RequiredCheck(identity, owner.role.value, comparison, fingerprint),
                    record,
                )
            )
        else:
            blockers.append(f"NATIVE_NON_BODY:{owner.physical_id}:{identity}:{comparison}")

    if isinstance(partition, NativeCheckPartition):
        for row in partition.retained_non_body:
            add(
                ":".join(row.identity),
                row.owner,
                row.result.numerical_comparison.value,
                row.result.input_fingerprint,
                row.result,
            )
    elif isinstance(partition, SplicePartition):
        for splice in partition.retained_non_body:
            add(
                splice.check_id,
                splice.owner,
                splice.comparison,
                angle_fingerprint(splice.native_fingerprints),
                splice,
            )
        blockers.extend(partition.native_warnings)
    else:
        for moment in partition.retained_non_body:
            record = moment.native_record
            if isinstance(record, MultiRowCheckResult):
                comparison = record.numerical_comparison.value
                fingerprint = record.input_fingerprint
            elif isinstance(record, WallMomentBearing):
                comparison = record.comparison.numerical_comparison.value
                fingerprint = angle_fingerprint(record)
            elif isinstance(record, SupportLocalCheck):
                comparison = record.status
                fingerprint = angle_fingerprint(record)
            elif isinstance(record, AsymmetricTwoPlaneBoltResult):
                comparison = record.status.value
                fingerprint = record.result_fingerprint
            elif isinstance(
                record, (SupportBoltCheck, BaseZoneResult, ColumnMomentZoneResult, LocalZoneResult)
            ):
                comparison = record.status
                fingerprint = angle_fingerprint(record)
            elif isinstance(record, WallMomentAttachmentResult):
                comparison = record.check.status
                fingerprint = record.fingerprint
            else:
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:RECORD_TYPE")
            add(moment.identity, moment.owner, comparison, fingerprint, record)
        blockers.extend(partition.response_source_status)
    return NonBodyAuthority(
        route,
        assembly.native_identity,
        (),
        tuple(checks),
        tuple(blockers),
        partition,
        False,
    )


def merge_native_authority(
    native: NonBodyAuthority, qualified: NonBodyAuthority | None
) -> NonBodyAuthority:
    """A later qualification may add evidence, never erase or duplicate a check."""
    if qualified is None:
        return native
    if (native.route, native.native_identity) != (qualified.route, qualified.native_identity):
        raise ValueError("STAINLESS_ACTIVATION_SNAPSHOT_STALE")
    checks = list(native.checks)
    by_id = {(c.component_id, c.check.id): c for c in checks}
    seen: set[tuple[str, str]] = set()
    for check in qualified.checks:
        identity = (check.component_id, check.check.id)
        if identity in seen:
            raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
        seen.add(identity)
        original = by_id.get(identity)
        if original is not None:
            if original != check:
                raise ValueError("STAINLESS_NATIVE_AUTHORITY_MODIFICATION_PROHIBITED")
        else:
            checks.append(check)
    return replace(
        qualified,
        checks=tuple(checks),
        blockers=(*native.blockers, *qualified.blockers),
        trace=(native.trace, qualified.trace),
    )
