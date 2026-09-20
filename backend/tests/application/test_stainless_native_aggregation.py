"""Owner-authorized native non-body retention, including duplicate/tamper guards."""

from dataclasses import replace

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.clip_angle_orchestration import ClipAngleDesignResult
from frp_master_connection.application.connector_material_assembly import (
    MaterialAssembly,
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_connection_design import (
    ConnectionAuthority,
    evaluate_stainless_connection,
)
from frp_master_connection.application.stainless_family_activation import (
    RequiredCheck,
    connection_summary,
    evaluate_bound_body,
)
from frp_master_connection.application.stainless_moment_ownership import (
    MomentPartition,
    OwnedMomentCheck,
)
from frp_master_connection.application.stainless_native_aggregation import (
    merge_native_authority,
    retained_native_authority,
)
from frp_master_connection.application.stainless_native_results import (
    NativeCheckPartition,
    OwnedNativeCheck,
    native_row_partition,
    physical_hardware_owner,
)
from frp_master_connection.application.stainless_splice_ownership import splice_check_partition
from frp_master_connection.application.wi_moment_splice_orchestration import (
    WIMomentSpliceDesignResult,
)
from frp_master_connection.calculation.results import NumericalComparison
from frp_master_connection.domain.connector_materials import ComponentRole
from tests.api.test_connector_materials import native_payload
from tests.application.test_stainless_activation_dispatch import bound


def fixture() -> tuple[str, ClipAngleDesignResult, MaterialAssembly, NativeCheckPartition]:
    route = "clip-angle"
    design = FAMILIES[route].design(native_payload(route))
    assert isinstance(design, ClipAngleDesignResult)
    assembly = canonical_material_assembly(route, design.preview)
    partition = native_row_partition(assembly, design)
    return route, design, assembly, partition


def test_unresolved_hardware_identity_and_unreviewed_bolt_record_fail_closed() -> None:
    _, _, assembly, _ = fixture()
    with pytest.raises(ValueError, match="NO_HARDWARE"):
        physical_hardware_owner(assembly, "NOT_A_CANONICAL_BOLT")
    route = "wi-major-axis-moment-splice"
    design = FAMILIES[route].design(native_payload(route))
    assert isinstance(design, WIMomentSpliceDesignResult)
    assembly = canonical_material_assembly(route, design.preview)
    with pytest.raises(ValueError, match="BOLT_RECORD"):
        splice_check_partition(assembly, replace(design, web_double_shear=(object(),)))


@pytest.mark.parametrize(
    "role",
    [
        ComponentRole.PRIMARY_MEMBER,
        ComponentRole.FASTENER_OR_HARDWARE,
        ComponentRole.FOUNDATION,
        ComponentRole.MEMBER_REINFORCEMENT,
    ],
)
def test_native_failure_governs_each_retained_domain_without_stainless_certificate(
    role: ComponentRole,
) -> None:
    route, _design, assembly, partition = fixture()
    native = next(
        c.result
        for c in partition.retained_non_body
        if c.result.numerical_comparison.value == "FAIL"
    )
    # Aggregation-only test records: no source, force or strength is registered.
    owner = replace(partition.retained_non_body[0].owner, role=role)
    assembly = replace(
        assembly,
        components=tuple(
            owner if c.physical_id == owner.physical_id else c for c in assembly.components
        ),
    )
    p = NativeCheckPartition((OwnedNativeCheck("DOMAIN", owner, native),), (), "a" * 64)
    bound = retained_native_authority(route, assembly, p)
    assert bound.response_fingerprints == ()
    assert bound.checks[0].native_record is native
    assert (
        connection_summary(
            tuple(c.check for c in bound.checks),
            ("STAINLESS_RESPONSE_SOURCE_REQUIRED",),
            complete=False,
        )
        == "FAIL"
    )


def test_real_member_failure_is_retained_in_connection_and_frp_body_failure_is_not() -> None:
    route, design, assembly, partition = fixture()
    native = retained_native_authority(route, assembly, partition)
    result = evaluate_stainless_connection(
        route, design.preview, authority=ConnectionAuthority(non_body=native)
    )
    assert result.status == "FAIL"
    assert result.blockers
    assert result.checks == tuple(c.check for c in native.checks)
    assert all(c.domain != ComponentRole.CONNECTOR_BODY.value for c in result.checks)
    assert partition.superseded_frp_body


def test_replaced_frp_body_failure_cannot_govern_valid_stainless_replacement() -> None:
    route, _, assembly, partition = fixture()
    row = next(
        c for c in partition.retained_non_body if c.result.numerical_comparison.value == "PASS"
    )
    body = partition.superseded_frp_body[0]
    failed_body = replace(
        body, result=replace(body.result, numerical_comparison=NumericalComparison.FAIL)
    )
    partition = replace(partition, retained_non_body=(row,), superseded_frp_body=(failed_body,))
    native = retained_native_authority(route, assembly, partition)
    binding, source = bound("ANGLE")
    stainless = evaluate_bound_body(binding, source)
    assert not stainless.blockers
    assert all(c.comparison == "PASS" for c in stainless.checks)
    assert (
        connection_summary(
            (*tuple(c.check for c in native.checks), *stainless.checks), (), complete=True
        )
        == "PASS"
    )
    assert failed_body.result.numerical_comparison is NumericalComparison.FAIL


@pytest.mark.parametrize(
    ("native_status", "body_status", "blockers", "expected"),
    [
        ("FAIL", "PASS", ("SOURCE_REQUIRED",), "FAIL"),
        ("PASS", "FAIL", (), "FAIL"),
        ("PASS", "PASS", ("SOURCE_REQUIRED",), "ENGINEERING_REVIEW_REQUIRED"),
        ("PASS", "PASS", (), "PASS"),
    ],
)
def test_complete_precedence(
    native_status: str, body_status: str, blockers: tuple[str, ...], expected: str
) -> None:
    checks = (
        RequiredCheck("NATIVE", "PRIMARY_MEMBER", native_status, "a" * 64),
        RequiredCheck("STAINLESS", "BODY", body_status, "b" * 64),
    )
    assert connection_summary(checks, blockers, complete=True) == expected


@pytest.mark.parametrize("case", ["duplicate", "body", "role", "unknown_record"])
def test_retention_fails_closed_on_wrong_ownership_or_unreviewed_record(case: str) -> None:
    route, _, assembly, partition = fixture()
    row = partition.retained_non_body[0]
    if case == "duplicate":
        partition = replace(partition, retained_non_body=(row, row))
    elif case == "body":
        partition = replace(partition, retained_non_body=(partition.superseded_frp_body[0],))
    elif case == "role":
        partition = replace(
            partition,
            retained_non_body=(
                replace(row, owner=replace(row.owner, role=ComponentRole.FOUNDATION)),
            ),
        )
    else:
        unknown = MomentPartition(
            (OwnedMomentCheck("UNKNOWN", row.owner, object()),), (), (), "a" * 64
        )
        with pytest.raises(ValueError, match="RECORD_TYPE"):
            retained_native_authority(route, assembly, unknown)
        return
    with pytest.raises(ValueError, match="STAINLESS_"):
        retained_native_authority(route, assembly, partition)


@pytest.mark.parametrize("case", ["same", "none", "new", "tampered", "duplicate", "stale"])
def test_qualified_source_merge_never_discards_or_double_counts_native_checks(case: str) -> None:
    route, _, assembly, partition = fixture()
    native = retained_native_authority(route, assembly, partition)
    qualified = native
    if case == "none":
        assert merge_native_authority(native, None) is native
        return
    if case == "new":
        qualified = replace(
            native,
            checks=(
                replace(native.checks[0], check=replace(native.checks[0].check, id="ADDITIONAL")),
            ),
        )
    elif case == "tampered":
        qualified = replace(
            native,
            checks=(
                replace(
                    native.checks[0],
                    check=replace(native.checks[0].check, provider_fingerprint="b" * 64),
                ),
            ),
        )
    elif case == "duplicate":
        qualified = replace(native, checks=(native.checks[0], native.checks[0]))
    elif case == "stale":
        qualified = replace(native, native_identity="b" * 64)
    if case in {"tampered", "duplicate", "stale"}:
        with pytest.raises(ValueError, match="STAINLESS_"):
            merge_native_authority(native, qualified)
    else:
        merged = merge_native_authority(native, qualified)
        assert merged.checks[: len(native.checks)] == native.checks
        assert len(merged.checks) == len(native.checks) + (case == "new")
