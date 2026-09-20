"""Both qualified branch/native resistance paths, including failure and invalidation."""

from dataclasses import fields, replace
from decimal import Decimal
from fractions import Fraction

import pytest

from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_qualification import (
    validate_member_response,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    AngleCoreRequest,
    components,
    exact_decimal,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.equations import (
    bolt_shear_resistance_from_nominal_stress,
    bolt_tension_resistance,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from tests.application.angle_column_base_fixture import complete_sources
from tests.application.test_angle_column_moment_base import request


@pytest.mark.parametrize("load_index", [1, 2, 7, 9, 11, 13])
@pytest.mark.parametrize("unequal", [False, True])
@pytest.mark.parametrize("si", [False, True])
def test_24_fully_sourced_native_member_and_body_integrations(
    load_index: int, unequal: bool, si: bool
) -> None:
    r, p, s = complete_sources(request(load_index, unequal=unequal, si=si))
    d = evaluate_angle_column_moment_base(r, s)
    assert all(v.status == "VALID_QUALIFIED_RESPONSE" for v in d.member_responses), [
        (v.status, v.reasons) for v in d.member_responses
    ]
    assert len(d.member_bolts) == 8
    assert len(d.connector_results) == len(d.member_attachment_results) == 2
    assert all("SOURCE_REQUIRED" not in v.status for v in d.connector_results)
    assert all("SOURCE_REQUIRED" not in v.check.status for v in d.member_attachment_results)
    assert d.local_zone is not None
    assert d.local_zone.comparisons
    for index, t in enumerate(p.transfers):
        # Construct the oracle from the original physical request/source record,
        # not the adapter's core request or its exported Slice 8 input.
        physical = r.connectors[index].angle
        axes = (((1, 0, 0), (0, 0, 1), (0, -1, 0)), ((0, -1, 0), (0, 0, 1), (-1, 0, 0)))[index]
        frame = AngleConnectorFrame(*((Decimal(a[0]), Decimal(a[1]), Decimal(a[2])) for a in axes))
        thickness = Fraction(physical.geometry.thickness.canonical_magnitude)
        member = physical.member_pattern
        foot = physical.support_pattern
        member_center = Fraction(member.center.canonical_magnitude) - thickness / 2
        member_ref = quantity_vector((Fraction(0), member_center, -thickness / 2), Unit.MM)
        support_ref = quantity_vector(
            (
                Fraction(0),
                -thickness / 2,
                Fraction(foot.center.canonical_magnitude) - thickness / 2,
            ),
            Unit.MM,
        )
        branch = s.responses[0].branches[index].member_action
        assert components(branch.reference) == components(member_ref)
        oracle = resolve_angle_connector(
            AngleCoreRequest(
                physical.geometry, frame, replace(branch, reference=member_ref), support_ref
            )
        )
        assert t.core == oracle
        bolts = tuple(
            WrenchBolt(
                f"B_R{row + 1}_L{line + 1}",
                exact_decimal(
                    (Fraction(line) - Fraction(member.across - 1, 2))
                    * Fraction(member.gauge.canonical_magnitude)
                ),
                exact_decimal(
                    member_center
                    + (Fraction(row) - Fraction(member.along - 1, 2))
                    * Fraction(member.pitch.canonical_magnitude)
                ),
            )
            for row in range(member.along)
            for line in range(member.across)
        )
        native = calculate_in_plane_wrench_demand(
            InPlaneWrenchRequest(
                bolts,
                (Decimal(0), exact_decimal(member_center)),
                branch.force.x.canonical_magnitude,
                branch.force.y.canonical_magnitude,
                branch.moment.z.canonical_magnitude,
                Unit.MM,
                Unit.N,
                Unit.N_MM,
            )
        )
        assert t.in_plane_demand == native
        source = s.fasteners[index]
        for b in (v for v in d.member_bolts if v.connector_id == t.connector_id):
            assert b.shear_magnitude is not None
            assert b.total_tension_including_prying is not None
            diameter = r.connectors[index].angle.fastener.bolt_diameter
            assert b.shear_trace == bolt_shear_resistance_from_nominal_stress(
                diameter, source.nominal_shear_stress
            )
            assert b.tension_trace == bolt_tension_resistance(
                diameter, source.nominal_tensile_stress
            )
            assert b.combined_trace == sourced_combined_bolt_resistance(
                diameter,
                source.nominal_tensile_stress,
                source.nominal_shear_stress,
                b.shear_magnitude,
            )
    assert any(c.native_trace is not None for c in d.local_checks)
    assert d.status in {"FAIL", "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"}
    assert not d.ordinary_whole_connection_pass_allowed


def test_native_shear_projection_cannot_be_replaced_by_a_different_balanced_source() -> None:
    _, p, s = complete_sources(request())
    record = s.member_responses[0]
    demand = record.shaft_demands[0]
    bad = replace(
        record, shaft_demands=(replace(demand, force_u=demand.force_v), *record.shaft_demands[1:])
    )
    checked = validate_member_response(record.binding, bad, p.transfers[0].in_plane_demand)
    assert "SHAFT_SHEAR_MUST_EQUAL_OPPOSITE_NATIVE_SLICE8_PROJECTION" in checked.reasons
    assert not checked.shafts


@pytest.mark.parametrize("unequal", [False, True])
@pytest.mark.parametrize("si", [False, True])
def test_small_source_qualified_internal_pass_is_not_foundation_adequacy(
    unequal: bool, si: bool
) -> None:
    r = request(13, unequal=unequal, si=si)
    # Change the test load, never production material or factor values.
    a = r.actions
    r = replace(
        r,
        actions=replace(
            a,
            **{
                f.name: replace(
                    getattr(a, f.name), magnitude=getattr(a, f.name).magnitude * Decimal("0.000001")
                )
                for f in fields(a)
            },
        ),
    )
    r, _, sources = complete_sources(r)
    d = evaluate_angle_column_moment_base(r, sources)
    assert d.status == "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"
    assert not d.ordinary_whole_connection_pass_allowed
    assert d.preview.foundation_strength_status == "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"


@pytest.mark.parametrize("unequal", [False, True])
def test_units_native_identity_bolt_order_and_co_translation(unequal: bool) -> None:
    from frp_master_connection.application.angle_column_base_preview import (
        preview_angle_column_moment_base,
    )

    us = preview_angle_column_moment_base(request(13, unequal=unequal))
    si = preview_angle_column_moment_base(request(13, unequal=unequal, si=True))
    assert us.engineering_fingerprint == si.engineering_fingerprint
    _, p, _ = complete_sources(request(13, unequal=unequal))
    for t in p.transfers:
        req = t.in_plane_input
        reordered = calculate_in_plane_wrench_demand(replace(req, bolts=tuple(reversed(req.bolts))))
        assert {b.bolt_id: b for b in reordered.solution.projected_bolts()} == {
            b.bolt_id: b for b in t.in_plane_demand.solution.projected_bolts()
        }
        # Input ordering remains part of Slice 8 native provenance; do not
        # normalize its fingerprint to impose a new serialization authority.
        assert reordered.fingerprint != t.in_plane_demand.fingerprint
    w = us.column_on_base
    origin = us.required_total_foundation_action.reference
    delta = (Fraction(11), Fraction(-7), Fraction(13))
    x, y, z = components(w.reference)
    translated = replace(
        w, reference=quantity_vector((x + delta[0], y + delta[1], z + delta[2]), Unit.MM)
    )
    new_origin = quantity_vector(delta, Unit.MM)
    before = shift_angle_wrench(w, origin)
    after = shift_angle_wrench(translated, new_origin)
    assert before.force == after.force
    assert before.moment == after.moment
