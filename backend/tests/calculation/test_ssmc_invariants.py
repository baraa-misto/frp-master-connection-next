"""All 22 immutable SSMC invariants with observable integration assertions."""

from dataclasses import replace
from typing import Any

import pytest

from frp_master_connection.api.ssmc import illustrative_ssmc, map_ssmc_request
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.ssmc import preview_ssmc
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.ssmc_response import (
    EMPTY_RESPONSE_REGISTRY,
    required_design_status,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.geometry.ssmc_polygon import contains_disk
from tests.calculation.test_ssmc_golden import DATA
from tests.calculation.test_ssmc_qualification import response_fixture


@pytest.mark.parametrize("case", DATA["invariants"], ids=lambda c: c["id"])
def test_approved_invariant(case: dict[str, Any]) -> None:
    n = int(case["id"][1:])
    request = replace(
        map_ssmc_request(illustrative_ssmc()),
        N=Q.of(8, Unit.KIP),
        V=Q.of(-4, Unit.KIP),
        M=Q.of(20, Unit.KIP_IN),
    )
    result = preview_ssmc(request)
    if n == 1:
        assembly = canonical_material_assembly("stair-stringer-miter", result)
        bodies = [c for c in assembly.components if c.role is ComponentRole.CONNECTOR_BODY]
        assert len(bodies) == result.method_policy.connector_body_count == 1
    elif n in {2, 4, 6}:
        assert result.method_policy.serial_action_factor == 1
        assert not result.method_policy.axial_row_fraction_mixing
        for i, group in enumerate(result.groups):
            restored = shift_angle_wrench(group.plate_wrench, result.work_point_wrench.reference)
            for key in ("force", "moment"):
                assert components(getattr(restored, key)) == tuple(
                    (-1 if i == 0 else 1) * x
                    for x in components(getattr(result.work_point_wrench, key))
                )
    elif n == 3:
        member = result.geometry.members[1]
        u, p = member.material_longitudinal, member.material_depth
        assert u.y == p.y == 0
        assert u.x > 0
        assert u.z < 0
        # The native right-handed triad's cross direction is retained, not
        # redefined by connector plate CW strength policy.
        assert abs(u.x * p.x + u.z * p.z) < 1e-12
        assert abs(u.x * p.z - u.z * p.x) > 0.99
    elif n == 5:
        assert all(g.native_slice8 is not None for g in result.groups)
        ineligible = preview_ssmc(
            replace(
                request,
                horizontal_group=replace(
                    request.horizontal_group, equal_translational_stiffness=False
                ),
            )
        )
        assert ineligible.groups[0].native_slice8 is None
        assert ineligible.groups[1].native_slice8 == result.groups[1].native_slice8
        assert "SSMC_PLANAR_GROUP_RESPONSE_NOT_QUALIFIED" in ineligible.blockers
    elif n == 7:
        other = preview_ssmc(replace(request, plate=replace(request.plate, side="POS_Y")))
        for a, b in zip(result.groups, other.groups, strict=True):
            am, bm = components(a.plate_wrench.moment), components(b.plate_wrench.moment)
            assert am[0]
            assert am[2]
            assert am == (-bm[0], bm[1], -bm[2])
    elif n == 8:
        for group in result.groups:
            assert group.bolt_axis_tension is None
            assert group.prying is None
            assert group.shaft_bending is None
            assert group.contact_response is None
    elif n in {9, 10, 11}:
        assert all(p.owner == "MITER_WEB_PLATE" for p in result.material_source_ledger)
        assert all(
            not p.isotropic and not p.longitudinal_strength_credit
            for p in result.material_source_ledger
        )
        assert all(
            p.authority is None and p.status == "SSMC_CW_SOURCE_REQUIRED"
            for p in result.material_source_ledger
        )
    elif n == 12:
        changed = preview_ssmc(
            replace(request, plate=replace(request.plate, thickness=Q.of("0.6", Unit.IN)))
        )
        for original_member, changed_member in zip(
            result.geometry.members, changed.geometry.members, strict=True
        ):
            assert (
                original_member.profile.material_orientation
                == changed_member.profile.material_orientation
            )
            assert original_member.material_longitudinal == changed_member.material_longitudinal
            assert original_member.material_depth == changed_member.material_depth
    elif n == 13:
        polygon = result.geometry.polygon
        assert len(polygon.boundary) > 4
        assert len(polygon.edge_ids) == len(polygon.boundary)
        assert len(result.geometry.polygon_paths.holes) == len(result.geometry.shafts)
        assert all(
            contains_disk(polygon.boundary, s.center, s.hardware_envelope_radius)
            for s in result.geometry.shafts
        )
        assert "CONVEX" not in result.method_policy.polygon_authority
    elif n == 14:
        assert "SSMC_POLYGON_RESISTANCE_NOT_QUALIFIED" in result.blockers
        mechanisms = {m for owner, m, _ in result.required_checks if owner == "MITER_WEB_PLATE"}
        assert {
            "TRANSITION_NECK",
            "REENTRANT_CORNER",
            "CONNECTED_LIGAMENT",
            "STABILITY",
        } <= mechanisms
    elif n == 15:
        assert "SSMC_MEMBER_FLANGE_WEB_TRANSFER_NOT_QUALIFIED" in result.blockers
        for owner in ("HORIZONTAL_STRINGER", "INCLINED_STRINGER"):
            assert any(
                o == owner and m == "FLANGE_TO_WEB_JUNCTION" for o, m, _ in result.required_checks
            )
    elif n in {16, 17}:
        assert result.method_policy.hardware_shear_capacity_multiplier == 1
        assert "SSMC_HARDWARE_COMBINED_RESPONSE_NOT_QUALIFIED" in result.blockers
        assert all(s.layer_owners == ("MITER_WEB_PLATE", s.member) for s in result.geometry.shafts)
        assert result.input.fastener == request.fastener
    elif n == 18:
        changed = preview_ssmc(replace(request, source_reference="OWNER APPROVED ALL CHECKS"))
        assert not EMPTY_RESPONSE_REGISTRY
        assert changed.trusted_complete_response is None
        assert "SSMC_TRUSTED_AUTHORITY_NOT_BOUND" in changed.blockers
        assert changed.qualified_material_snapshot is None
    elif n == 19:
        record, _, _ = response_fixture()
        record = replace(record, numerical_failures=("TEST_ONLY_QUALIFIED_FAILURE",))
        zero = map_ssmc_request(illustrative_ssmc())
        failed = preview_ssmc(zero, {record.binding: record})
        assert failed.whole_connection_status == "FAIL"
        assert failed.blockers
    elif n in {20, 21}:
        assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
        assert not result.complete_moment_capacity_qualified
        assert required_design_status((), ()) == "PASS"
        assert required_design_status((), result.blockers) != "PASS"
    else:
        assert n == 22
        # This same immutable-authority regression runs in no-tags clones;
        # publication preflight separately verifies the live tag object/ref.
        from tests.calculation.test_ssmc_approved_contract import test_approved_fail_closed_contract

        test_approved_fail_closed_contract(DATA["negative_cases"][39])
