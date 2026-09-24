"""Focused bounded analytical adapter tests; synthetic sources are not production data."""

from dataclasses import replace
from decimal import Decimal
from itertools import product

import pytest

from frp_master_connection.api.ssmc import (
    convert_ssmc_units,
    illustrative_ssmc,
    map_ssmc_request,
)
from frp_master_connection.application.ssmc_analytical import (
    SSMCAnalyticalAuthorities,
    SSMCAnalyticalRequest,
    SSMCBearingAuthority,
    SSMCDesignAction,
    SSMCSingleLapDeclaration,
    evaluate_ssmc_analytical,
)
from frp_master_connection.application.ssmc_cuts import section_intervals
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.ssmc import SSMCRequest, StringerForm
from tests.api.test_connector_materials import http


def _request(
    *,
    physical: SSMCRequest | None = None,
    declaration: SSMCSingleLapDeclaration | None = None,
) -> SSMCAnalyticalRequest:
    model = map_ssmc_request(illustrative_ssmc()) if physical is None else physical
    model = replace(model, N=Q.of(8, Unit.KIP), V=Q.of(-4, Unit.KIP), M=Q.of(20, Unit.KIP_IN))
    action = SSMCDesignAction(
        "FACTORED_LRFD",
        "TEST_LOAD_COMBINATION",
        "TEST_SOURCE_ONLY",
        True,
        TimeEffectCategory.OTHER_LIVE,
        "TEST_TIME_EFFECT_REFERENCE",
    )
    if declaration is None:
        declaration = SSMCSingleLapDeclaration(
            True, Q.of(0, Unit.N), Q.of(0, Unit.N_MM), False, False, False, False
        )
    return SSMCAnalyticalRequest(model, action, declaration)


def test_lrfd_provenance_must_be_explicit() -> None:
    action = _request().action
    for changes in (
        {"basis": "SOURCE_ASD"},
        {"combination_id": ""},
        {"combination_source": ""},
        {"already_factored": False},
        {"time_effect_reference": ""},
    ):
        with pytest.raises(ValueError, match="FACTORED_LRFD"):
            replace(action, **changes)


@pytest.mark.parametrize(
    ("form", "angle", "side", "rows"),
    list(product(StringerForm, (-35, 35), ("NEG_Y", "POS_Y"), (2, 3))),
)
def test_serial_action_reaction_and_exact_planar_proof(
    form: StringerForm, angle: int, side: str, rows: int
) -> None:
    physical = map_ssmc_request(illustrative_ssmc())
    physical = replace(
        physical,
        horizontal=replace(physical.horizontal, form=form),
        inclined=replace(physical.inclined, form=form),
        theta_deg=Decimal(angle),
        plate=replace(physical.plate, side=side),
        horizontal_group=replace(physical.horizontal_group, rows=rows),
        inclined_group=replace(physical.inclined_group, rows=rows),
    )
    result = evaluate_ssmc_analytical(_request(physical=physical))
    assert result.applicability_status == "ELIGIBLE"
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert result.action_reaction
    assert result.cuts.cuts
    for group in result.action_reaction:
        assert group.exact_opposition_proven
        assert group.full_planar_equilibrium_proven
        for key in ("force", "moment"):
            assert components(getattr(group.action_on_plate, key)) == tuple(
                -value for value in components(getattr(group.reaction_on_member, key))
            )
        recovered = shift_angle_wrench(group.member_cut_reaction, group.action_on_plate.reference)
        assert components(recovered.force) == components(group.reaction_on_member.force)
        assert components(recovered.moment) == components(group.reaction_on_member.moment)
    assert all(
        check.status == "NOT_APPLICABLE" for check in result.checks if check.mode == "PULL_THROUGH"
    )


def test_single_lap_violation_requires_review_and_preserves_secondary_moment() -> None:
    declaration = replace(_request().single_lap, independent_normal_force=Q.of(1, Unit.N))
    result = evaluate_ssmc_analytical(_request(declaration=declaration))
    assert result.applicability_status == "ENGINEERING_REVIEW_REQUIRED"
    assert "INDEPENDENT_BOLT_AXIS_FORCE" in result.applicability_reasons
    assert all(
        c.status == "ENGINEERING_REVIEW_REQUIRED" for c in result.checks if c.mode == "PULL_THROUGH"
    )
    assert any(
        abs(moment) > 0
        for group in result.action_reaction
        for moment in group.secondary_thickness_moment
    )


def test_actual_polygon_minus_circle_chord_intervals() -> None:
    boundary = ((0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0))
    holes = (("H1", (4.0, 4.0), 1.0), ("H2", (7.0, 4.0), 1.0))
    gross, net, ids = section_intervals(boundary, holes, (0.0, -1.0), -4.0)
    assert gross == ((0.0, 10.0),)
    assert net == ((0.0, 3.0), (5.0, 6.0), (8.0, 10.0))
    assert ids == ("H1", "H2")


def test_supported_numerical_fail_wins_over_missing_sources() -> None:
    request = _request()
    baseline = evaluate_ssmc_analytical(request)
    shaft = baseline.existing_demand.geometry.shafts[0]
    record = SSMCBearingAuthority(
        baseline.existing_demand.engineering_fingerprint,
        "MITER_WEB_PLATE",
        shaft.id,
        "SYNTHETIC_PRODUCT",
        "SYNTHETIC_CUT",
        "CW",
        Q.of(1, Unit.MPA),
        request.physical.fastener.diameter,
        request.physical.fastener.hole_diameter,
        "TEST_MATERIAL",
        "TEST_PROCEDURE_C",
        "TEST_D7290",
        "TEST_VARIABILITY_PHI",
        Decimal("0.60"),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        "BOTH_SIDES",
        "TEST_QUALIFICATION",
        "a" * 64,
        "b" * 64,
    )
    sources = SSMCAnalyticalAuthorities({}, {("MITER_WEB_PLATE", shaft.id): record})
    result = evaluate_ssmc_analytical(request, sources)
    bearing = next(
        c
        for c in result.checks
        if c.owner == "MITER_WEB_PLATE" and c.path_id == shaft.id and c.mode == "PIN_BEARING"
    )
    assert bearing.status == "FAIL"
    assert dict(bearing.factors)["C_lap"] == "0.6"
    assert result.blockers
    assert result.whole_connection_status == "FAIL"


def test_zero_demand_does_not_create_qualification() -> None:
    request = _request()
    result = evaluate_ssmc_analytical(
        replace(
            request,
            physical=replace(
                request.physical,
                N=Q.of(0, Unit.N),
                V=Q.of(0, Unit.N),
                M=Q.of(0, Unit.N_MM),
            ),
        )
    )
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert result.cuts.finite_coverage_proven is False
    assert any(c.status == "SOURCE_REQUIRED" for c in result.checks)


def test_ineligible_planar_group_returns_review_records() -> None:
    request = _request()
    physical = replace(
        request.physical,
        horizontal_group=replace(request.physical.horizontal_group, slots=True),
    )
    result = evaluate_ssmc_analytical(replace(request, physical=physical))
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert result.cuts.status == "PLANAR_DEMAND_REQUIRED"
    assert "PLANAR_GROUP_ELIGIBILITY" in result.applicability_reasons
    assert any(c.reason == "PLANAR_DEMAND_REQUIRED" for c in result.checks)


def test_public_analytical_route_requires_lrfd_and_keeps_sources_server_side() -> None:
    path = "/api/v1/calculations/stair-stringer-miter/analytical-design-check"
    payload = {
        "physical": illustrative_ssmc().model_dump(mode="json"),
        "action": {
            "basis": "FACTORED_LRFD",
            "combination_id": "TEST_COMBO",
            "combination_source": "TEST_SOURCE",
            "already_factored": True,
            "time_effect_category": "OTHER_LIVE",
            "time_effect_reference": "TEST_REFERENCE",
        },
        "single_lap": {
            "external_actions_at_faying_interface": True,
            "independent_normal_force": {"value": "0", "unit": "N"},
            "independent_out_of_plane_moment": {"value": "0", "unit": "N-mm"},
            "imposed_separation": False,
            "non_contact_gap": False,
            "friction_or_preload_credit": False,
            "miter_bearing_credit": False,
        },
    }
    response = http("POST", path, payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["contract"] == "SSMC-3-ANALYTICAL-RC1"
    assert result["whole_connection_status"] == "ENGINEERING_REVIEW_REQUIRED"
    assert result["result"]["cuts"]["finite_coverage_proven"] is False
    assert result["result"]["action_reaction"][0]["exact_opposition_proven"] is True
    assert http("POST", path, payload | {"authorities": "FORGED"}).status_code == 422
    payload["action"]["basis"] = "SOURCE_ASD"
    assert http("POST", path, payload).status_code == 422


def test_equivalent_unit_views_preserve_cut_and_bolt_demands() -> None:
    dto = illustrative_ssmc()
    us = evaluate_ssmc_analytical(_request(physical=map_ssmc_request(dto)))
    si_dto = convert_ssmc_units(dto, True)
    si = evaluate_ssmc_analytical(_request(physical=map_ssmc_request(si_dto)))
    assert len(us.cuts.cuts) == len(si.cuts.cuts)
    assert len(us.checks) == len(si.checks)
    for first, second in zip(us.cuts.cuts, si.cuts.cuts, strict=True):
        assert first.cut_id == second.cut_id
        assert first.net_area_mm2 == pytest.approx(second.net_area_mm2, rel=1e-6, abs=1e-6), (
            first.cut_id
        )
        assert first.cut_N_N == pytest.approx(second.cut_N_N, rel=1e-10, abs=1e-7)
        assert first.cut_V_N == pytest.approx(second.cut_V_N, rel=1e-10, abs=1e-7)
