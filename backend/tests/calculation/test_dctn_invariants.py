"""All eighteen immutable DCTN invariants, separate from the owner W/I regressions."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.api.double_channel_truss_node import (
    DCTNRequestDTO,
    convert_dctn_units,
    map_dctn_request,
    serialize_dctn_value,
)
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.double_channel_truss_node import (
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.angle_column_base_response import sum_wrenches
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
)
from frp_master_connection.calculation.double_channel_truss_node_response import row_fractions
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    default_dctn_request,
)
from tests.api.test_dctn_api_and_parent import PARENT
from tests.api.test_dctn_api_and_parent import (
    test_exact_old_preview_design_geometry_defaults_and_material_plan as prove_parent,
)
from tests.calculation.test_dctn_approved_goldens import AUTHORITY
from tests.calculation.test_dctn_response import request
from tests.calculation.test_dctn_sources_and_native import (
    registry,
    sourced_request,
)
from tests.calculation.test_dctn_sources_and_native import (
    test_native_numerical_failures_outrank_independent_qualification as prove_failure_precedence,
)
from tests.calculation.test_dctn_sources_and_native import (
    test_resistance_factor_adapter_uses_native_equation_verbatim as prove_wi_factor,
)
from tests.calculation.test_dctn_sources_and_native import (
    test_rhs_characteristic_factor_does_not_leak_to_channel_or_other_modes as prove_rhs_factor,
)

q = PhysicalQuantity.of


@pytest.mark.parametrize("case", AUTHORITY["invariants"], ids=lambda c: c["id"])
def test_approved_invariant(case: dict[str, str]) -> None:
    identity = case["id"]
    if identity == "I01":
        for count in (1, 2, 3):
            assert sum(row_fractions(count)) == 1
        for count in (0, 4, 5):
            with pytest.raises(ValueError, match="ROW_COUNT_OUTSIDE"):
                row_fractions(count)
    elif identity in {"I02", "I03", "I04", "I05", "I06", "I09"}:
        for form in DCTNForm:
            for force in ("10", "0", "-10"):
                value = request(form, 3, force)
                p = preview_dctn(value)
                assert p.response.status == "QUALIFIED"
                assert len(p.geometry.shafts) == (6 if form is DCTNForm.W_I else 3)
                assert len({s.bolt_id for s in p.geometry.shafts}) == len(p.geometry.shafts)
                for row in p.response.rows:
                    assert row.negative_at_bolt.force.z.to(Unit.KIP) == row.signed_row_force.to(
                        Unit.KIP
                    ) * Decimal(".5")
                    assert row.positive_at_bolt.force.z == row.negative_at_bolt.force.z
                    assert row.member_force_closes
                    assert row.member_moment_closes
                for shaft in p.response.shafts:
                    assert shaft.capacity_multiplier is None
                    assert shaft.physical_capacity_report_count == 1
                    assert shaft.terminal_residual.magnitude == 0
                    assert len(shaft.shear_plane_demands) == (1 if form is DCTNForm.W_I else 2)
                    if form is DCTNForm.SOLID_RECTANGLE:
                        assert len(shaft.signed_layer_transfers) == 3
                        assert shaft.signed_layer_transfers[1] == (
                            shaft.signed_layer_transfers[0] + shaft.signed_layer_transfers[2]
                        ) * Decimal(-1)
        if identity in {"I05", "I06", "I09"}:
            for form in DCTNForm:
                prove_failure_precedence(form)
    elif identity == "I07":
        prove_rhs_factor()
    elif identity == "I08":
        prove_wi_factor()
    elif identity == "I10":
        value = default_dctn_request(DCTNArrangement.TWO_INCLINED)
        first, second = value.members
        second = replace(
            second,
            section=replace(second.section, length=q("25", Unit.IN)),
            axial_force=q("-3", Unit.KIP),
        )
        assert first.section.linked_section() == second.section.linked_section()
        assert first.start != second.start
        assert first.inclination_deg != second.inclination_deg
        p = preview_dctn(replace(value, members=(first, second)))
        assert p.geometry.status == "VALID"
        assert p.response.status == "QUALIFIED"
        invalid = replace(second, section=replace(second.section, width=q("5", Unit.IN)))
        assert (
            "DCTN_DIAGONAL_SECTION_LINK_MISMATCH"
            in preview_dctn(replace(value, members=(first, invalid))).geometry.reasons
        )
    elif identity == "I11":
        for form in DCTNForm:
            value = request(form, 2, arrangement=DCTNArrangement.VERTICAL_ONE_INCLINED)
            p = preview_dctn(value)
            assert p.geometry.gap == value.members[0].section.depth.to(Unit.IN).magnitude
            changed = replace(
                value.members[1], section=replace(value.members[1].section, depth=q(8, Unit.IN))
            )
            assert (
                "DCTN_COMMON_GAP_MISMATCH"
                in preview_dctn(
                    replace(value, members=(value.members[0], changed))
                ).geometry.reasons
            )
    elif identity == "I12":
        for form in DCTNForm:
            p = preview_dctn(request(form, 3, arrangement=DCTNArrangement.VERTICAL_TWO_INCLINED))
            for channel in p.response.channels:
                assert channel.total == sum_wrenches(
                    channel.contributions, channel.engineering_reference
                )
                assert len(channel.contributions) == 9
                assert len(channel.hole_ids) == 9
                assert len(channel.group_ids) == 3
    elif identity == "I13":
        for form in DCTNForm:
            prove_failure_precedence(form)
    elif identity == "I14":
        base = sourced_request()
        value = default_dctn_request(DCTNArrangement.VERTICAL_TWO_INCLINED)
        value = replace(
            value,
            channel=base.channel,
            fastener=base.fastener,
            members=tuple(
                replace(m, material_source_reference="MATERIAL_FIXTURE") for m in value.members
            ),
        )
        p = preview_dctn(value)
        sources = registry(p)
        result = design_check_dctn(value, sources)
        assert any("DCTN_SHARED_CHORD_CROSS_GROUP_PATH_NOT_QUALIFIED" in b for b in result.blockers)
        assert result.whole_connection_status != "PASS"
        assert result.checks
        assert result.preview.response.channels == p.response.channels
        for review in p.shared_channel_review:
            assert len(review.hole_ids) == 6
            assert len(review.group_ids) == 3
            assert all(len(c.geometry.group.bolts) == 6 for c in review.candidate_plans)
    elif identity == "I15":
        p = preview_dctn(default_dctn_request(DCTNArrangement.VERTICAL_TWO_INCLINED))
        a = canonical_material_assembly("double-channel-truss-node", p)
        assert not any(c.role is ComponentRole.CONNECTOR_BODY for c in a.components)
        assert p.connector_body_count == 0
    elif identity == "I16":
        for route in PARENT["routes"]:
            prove_parent(route)
    elif identity == "I17":
        value = default_dctn_request()
        us = DCTNRequestDTO.model_validate(serialize_dctn_value(value))
        si = convert_dctn_units(us, True)
        before = preview_dctn(map_dctn_request(us))
        after = preview_dctn(map_dctn_request(si))
        assert before.response.method == after.response.method
        assert [(s.bolt_id, s.layer_owners) for s in before.geometry.shafts] == [
            (s.bolt_id, s.layer_owners) for s in after.geometry.shafts
        ]
        assert convert_dctn_units(si, False) == us
        assert si.fastener.hole_diameter.value == "14.3002"
    else:
        assert identity == "I18"
        check = DCTNRequiredCheck(
            "LOCAL", "MEMBER", "PASS", q(1, Unit.KIP), q(2, Unit.KIP), (), "TEST_ONLY"
        )
        assert aggregate_dctn_checks((check,), ()) == "PASS"
        p = preview_dctn(default_dctn_request())
        assert not p.global_chord_design_evaluated
        assert all(not c.global_member_design_evaluated for c in p.response.channels)
