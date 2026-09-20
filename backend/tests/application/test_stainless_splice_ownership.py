from dataclasses import replace

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_splice_ownership import splice_check_partition
from frp_master_connection.application.web_splice_orchestration import WebSpliceDesignResult
from frp_master_connection.calculation.web_splice_resistance import WebSpliceDoubleShearResult
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    AsymmetricTwoPlaneBoltResult,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from tests.api.test_connector_materials import native_payload


@pytest.mark.parametrize(
    "route", ["beam-web-splice", "wi-major-axis-moment-splice", "channel-major-axis-moment-splice"]
)
def test_every_native_splice_check_is_owned_exactly_once(route: str) -> None:
    family = FAMILIES[route]
    request = native_payload(route)
    design = family.design(request)
    assembly = canonical_material_assembly(route, family.preview(request))
    partition = splice_check_partition(assembly, design)
    assert partition.retained_non_body
    assert partition.superseded_frp_body
    assert {
        c.owner.physical_id
        for c in partition.retained_non_body
        if c.owner.role is ComponentRole.PRIMARY_MEMBER
    } == {"BEAM_A", "BEAM_B"}
    assert all(c.owner.role is ComponentRole.CONNECTOR_BODY for c in partition.superseded_frp_body)
    checks = (*partition.retained_non_body, *partition.superseded_frp_body)
    assert len({c.check_id for c in checks}) == len(checks)
    assert all(c.owner in assembly.components for c in checks)
    assert all(
        c.comparison == ("FAIL" if c.failed else "NATIVE_COMPARISON_NOT_SERIALIZED")
        for c in checks
        if c.native_record is None
    )
    for c in checks:
        if c.native_record is not None:
            assert isinstance(
                c.native_record, (WebSpliceDoubleShearResult, AsymmetricTwoPlaneBoltResult)
            )
            assert c.owner.role is ComponentRole.FASTENER_OR_HARDWARE
            assert c.comparison == c.native_record.status
    assert partition == splice_check_partition(assembly, design)


def test_ambiguous_or_unknown_summary_identity_cannot_govern_stainless() -> None:
    family = FAMILIES["beam-web-splice"]
    request = native_payload("beam-web-splice")
    design = family.design(request)
    assert isinstance(design, WebSpliceDesignResult)
    assembly = canonical_material_assembly("beam-web-splice", family.preview(request))
    for tampered in (
        replace(design, local_check_ids=("CLIENT:FAKE:CHECK",), failed_local_check_ids=()),
        replace(design, failed_local_check_ids=("ORPHAN",)),
    ):
        with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED"):
            splice_check_partition(assembly, tampered)
    with pytest.raises(ValueError, match="DUPLICATE_REQUIRED_CHECK"):
        splice_check_partition(
            assembly, replace(design, local_check_ids=design.local_check_ids * 2)
        )
