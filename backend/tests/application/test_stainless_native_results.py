"""Native role partitions preserve exact results, not an SS resistance fallback."""

from dataclasses import replace

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_native_results import (
    native_row_partition,
    partition_native_checks,
    physical_owner,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from tests.api.test_connector_materials import native_payload
from tests.column_base_web_angle_fixtures import build_column_base_web_angle_payload


@pytest.mark.parametrize(
    "route",
    [
        "clip-angle",
        "tee-connector",
        "paired-clip-angle",
        "multi-member-tee",
        "beam-concrete-paired-angle",
    ],
)
def test_native_final_checks_have_disjoint_canonical_owners(route: str) -> None:
    family = FAMILIES[route]
    payload = native_payload(route)
    preview = family.preview(payload)
    design = family.design(payload)
    assembly = canonical_material_assembly(route, preview)
    partition = native_row_partition(assembly, design)
    assert partition.retained_non_body
    assert partition.superseded_frp_body
    assert all(
        c.owner.role is not ComponentRole.CONNECTOR_BODY for c in partition.retained_non_body
    )
    assert all(c.owner.role is ComponentRole.CONNECTOR_BODY for c in partition.superseded_frp_body)
    checks = (*partition.retained_non_body, *partition.superseded_frp_body)
    assert len({c.identity for c in checks}) == len(checks)
    assert all(not c.governs_stainless_body for c in checks)
    assert all(c.owner in assembly.components for c in checks)
    assert partition == native_row_partition(assembly, design)
    with pytest.raises(ValueError, match="DUPLICATE_REQUIRED_CHECK"):
        partition_native_checks((*checks, checks[0]))


def test_no_client_owner_or_unclassified_owner_can_qualify_a_native_check() -> None:
    family = FAMILIES["clip-angle"]
    payload = native_payload("clip-angle")
    assembly = canonical_material_assembly("clip-angle", family.preview(payload))
    with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED"):
        physical_owner(assembly, "client-supplied-body")
    check = native_row_partition(assembly, family.design(payload)).retained_non_body[0]
    altered = replace(check, owner=replace(check.owner, role=ComponentRole.UNCLASSIFIED))
    with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED"):
        partition_native_checks((altered,))


@pytest.mark.parametrize("side", ["+T_C", "-T_C"])
@pytest.mark.parametrize("assembly_kind", ["SINGLE_BASE_ANGLE", "SYMMETRIC_DOUBLE_BASE_ANGLES"])
def test_column_base_actual_layer_ownership(side: str, assembly_kind: str) -> None:
    route = "column-base-web-angles"
    payload = build_column_base_web_angle_payload(
        assembly=assembly_kind, single_side=side, web_plane_shear="0"
    )
    native = FAMILIES[route]
    result = native.design(payload)
    assembly = canonical_material_assembly(route, native.preview(payload))
    partition = native_row_partition(assembly, result)
    assert partition.retained_non_body
    assert partition.superseded_frp_body
    assert {c.owner.physical_id for c in partition.retained_non_body} == {"column"}
    expected = {"positive-base-angle", "negative-base-angle"}
    if assembly_kind == "SINGLE_BASE_ANGLE":
        expected = {"positive-base-angle" if side == "+T_C" else "negative-base-angle"}
    assert {c.owner.physical_id for c in partition.superseded_frp_body} == expected
