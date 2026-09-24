"""Focused bounded analytical adapter tests; synthetic sources are not production data."""

from dataclasses import replace
from decimal import Decimal
from itertools import product

import pytest

import frp_master_connection.application.ssmc_analytical as analytical
from frp_master_connection.api.ssmc import (
    convert_ssmc_units,
    illustrative_ssmc,
    map_ssmc_request,
)
from frp_master_connection.application.ssmc import preview_ssmc
from frp_master_connection.application.ssmc_analytical import (
    SSMCAnalyticalAuthorities,
    SSMCAnalyticalCheck,
    SSMCAnalyticalRequest,
    SSMCBearingAuthority,
    SSMCDesignAction,
    SSMCHardwareAuthority,
    SSMCQualifiedModeAuthority,
    SSMCSingleLapDeclaration,
    _actions,
    _authority_check,
    evaluate_ssmc_analytical,
)
from frp_master_connection.application.ssmc_cuts import (
    _merge,
    _stations,
    _subtract,
    section_intervals,
)
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


def _qualified_mode(
    binding: str, owner: str, path_id: str, mode: str, direction: str, nominal_N: int
) -> SSMCQualifiedModeAuthority:
    return SSMCQualifiedModeAuthority(
        binding,
        owner,
        path_id,
        mode,
        "SYNTHETIC_PRODUCT",
        "SYNTHETIC_CUT",
        direction,
        "PROJECT_2_3_2:TEST",
        "TEST_QUALIFICATION",
        "a" * 64,
        "b" * 64,
        Q.of(nominal_N, Unit.N),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        binding,
    )


def _hardware(binding: str, fnv_mpa: int) -> SSMCHardwareAuthority:
    return SSMCHardwareAuthority(
        binding,
        "TEST_SPECIFICATION",
        "TEST_ALLOY_CONDITION",
        Q.of(1000, Unit.MPA),
        Q.of(fnv_mpa, Unit.MPA),
        False,
        "NOMINAL_UNTHREADED_BODY_AREA",
        "TEST_GRIP_ENGAGEMENT",
        "TEST_HEAD_NUT_WASHER",
        "a" * 64,
        "b" * 64,
    )


def _mode_check(
    record: SSMCQualifiedModeAuthority,
    authorities: SSMCAnalyticalAuthorities,
    demand: float,
) -> SSMCAnalyticalCheck:
    return _authority_check(
        record.binding,
        authorities,
        owner=record.owner,
        path_id=record.path_id,
        mode=record.mode,
        demand=demand,
        force=(1.0, 0.0),
        direction=record.direction,
        thickness=10.0,
        diameter=12.0,
        hole=13.0,
        proof="TEST_EXACT_PATH",
        lambda_factor=Decimal(1),
    )


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
    request = _request()
    with pytest.raises(ValueError, match="SSMC_SINGLE_LAP_ACTION_DIMENSION_INVALID"):
        replace(request.single_lap, independent_normal_force=Q.of(1, Unit.N_MM))
    with pytest.raises(ValueError, match="SSMC_ANALYTICAL_CONTRACT_INVALID"):
        replace(request, contract="SSMC-2-RC1")


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
    all_exclusions = replace(
        declaration,
        external_actions_at_faying_interface=False,
        independent_out_of_plane_moment=Q.of(1, Unit.N_MM),
        imposed_separation=True,
        non_contact_gap=True,
        friction_or_preload_credit=True,
        miter_bearing_credit=True,
    )
    excluded = evaluate_ssmc_analytical(_request(declaration=all_exclusions))
    assert set(excluded.applicability_reasons) == {
        "EXTERNAL_ACTION_REFERENCE_NOT_FAYING_INTERFACE",
        "INDEPENDENT_BOLT_AXIS_FORCE",
        "INDEPENDENT_OUT_OF_PLANE_MOMENT",
        "IMPOSED_SEPARATION",
        "NON_CONTACT_GAP",
        "FRICTION_OR_PRELOAD_CREDIT",
        "MITER_BEARING_CREDIT",
    }
    assert all(
        c.status == "ENGINEERING_REVIEW_REQUIRED"
        for c in excluded.checks
        if c.mode == "PULL_THROUGH"
    )


def test_actual_polygon_minus_circle_chord_intervals() -> None:
    boundary = ((0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0))
    holes = (("H1", (4.0, 4.0), 1.0), ("H2", (7.0, 4.0), 1.0))
    gross, net, ids = section_intervals(boundary, holes, (0.0, -1.0), -4.0)
    assert gross == ((0.0, 10.0),)
    assert net == ((0.0, 3.0), (5.0, 6.0), (8.0, 10.0))
    assert ids == ("H1", "H2")
    assert _merge([(1.0, 1.0), (1.0, 3.0), (2.0, 4.0), (5.0, 6.0)]) == (
        (1.0, 4.0),
        (5.0, 6.0),
    )
    assert _subtract(
        ((0.0, 10.0), (12.0, 20.0)),
        ((-1.0, 3.0), (3.0, 10.0), (11.0, 13.0), (17.0, 25.0)),
    ) == ((13.0, 17.0),)
    coincident_gross, coincident_net, coincident_holes = section_intervals(
        boundary, (), (1.0, 0.0), 0.0
    )
    assert coincident_gross == coincident_net == ((0.0, 8.0),)
    assert coincident_holes == ()
    touching_gross, touching_net, touching_holes = section_intervals(boundary, (), (1.0, 1.0), 0.0)
    assert touching_gross == touching_net == ()
    assert touching_holes == ()
    peak_gross, peak_net, peak_holes = section_intervals(boundary, (), (1.0, 1.0), 18.0)
    assert peak_gross == peak_net == ()
    assert peak_holes == ()
    preview = preview_ssmc(_request().physical)
    no_transition = replace(
        preview,
        geometry=replace(
            preview.geometry,
            polygon=replace(preview.geometry.polygon, transition=()),
        ),
    )
    stations = _stations(no_transition, (1.0, 0.0), 25.4)
    assert any(label.startswith("ROW_") for label, _ in stations)
    assert all(label != "NECK_MIDPOINT" for label, _ in stations)


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
    invalid_sources = SSMCAnalyticalAuthorities(
        {}, {("MITER_WEB_PLATE", shaft.id): replace(record, direction="T")}
    )
    invalid = evaluate_ssmc_analytical(request, invalid_sources)
    invalid_bearing = next(
        c
        for c in invalid.checks
        if c.owner == "MITER_WEB_PLATE" and c.path_id == shaft.id and c.mode == "PIN_BEARING"
    )
    assert invalid_bearing.status == "ENGINEERING_REVIEW_REQUIRED"
    assert invalid_bearing.reason == "PIN_BEARING_SOURCE_GEOMETRY_OR_DIRECTION_INVALID"

    path_id = "TEST_GROUP:FIRST_ROW_TENSION"
    mode = _qualified_mode(
        baseline.existing_demand.engineering_fingerprint,
        "MITER_WEB_PLATE",
        path_id,
        "FIRST_ROW_TENSION",
        "CW",
        1000,
    )
    assert mode.valid_for(mode.binding, mode.owner, path_id, mode.mode)
    mode_sources = SSMCAnalyticalAuthorities({(mode.owner, path_id, mode.mode): mode})
    passing = _mode_check(mode, mode_sources, 1.0)
    failing = _mode_check(mode, mode_sources, 1000.0)
    assert passing.status == "PASS"
    assert passing.design_resistance_N == pytest.approx(600.0)
    assert dict(passing.factors)["C_lap"] == "0.6"
    assert failing.status == "FAIL"
    assert failing.reason == "NUMERICAL_RESISTANCE_EXCEEDED"
    mismatched = _mode_check(
        mode,
        SSMCAnalyticalAuthorities({(mode.owner, path_id, mode.mode): replace(mode, direction="T")}),
        1.0,
    )
    assert mismatched.status == "ENGINEERING_REVIEW_REQUIRED"
    assert mismatched.reason == "FIRST_ROW_TENSION_AUTHORITY_BINDING_INVALID"
    member_mode = _qualified_mode(
        mode.binding,
        "HORIZONTAL_STRINGER",
        "HORIZONTAL_STRINGER:CUT",
        "MEMBER_NVM_AND_CUT_END",
        "MEMBER_LOCAL",
        1000,
    )
    member_check = _authority_check(
        member_mode.binding,
        SSMCAnalyticalAuthorities(
            {(member_mode.owner, member_mode.path_id, member_mode.mode): member_mode}
        ),
        owner=member_mode.owner,
        path_id=member_mode.path_id,
        mode=member_mode.mode,
        demand=1.0,
        force=(1.0, 0.0),
        direction=member_mode.direction,
        thickness=None,
        diameter=None,
        hole=None,
        proof="TEST_MEMBER_CUT",
        lambda_factor=Decimal(1),
    )
    assert member_check.status == "PASS"
    assert dict(member_check.factors)["C_lap"] == "1"
    low_hardware = evaluate_ssmc_analytical(
        request,
        SSMCAnalyticalAuthorities({}, hardware=_hardware(mode.binding, 1)),
    )
    assert any(c.status == "FAIL" for c in low_hardware.checks if c.mode == "BOLT_SHEAR")
    assert low_hardware.whole_connection_status == "FAIL"


def test_zero_demand_does_not_create_qualification(monkeypatch: pytest.MonkeyPatch) -> None:
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
    zero_request = replace(
        request,
        physical=replace(
            request.physical, N=Q.of(0, Unit.N), V=Q.of(0, Unit.N), M=Q.of(0, Unit.N_MM)
        ),
    )
    binding = result.existing_demand.engineering_fingerprint
    with_hardware = evaluate_ssmc_analytical(
        zero_request,
        SSMCAnalyticalAuthorities({}, hardware=_hardware(binding, 1)),
    )
    assert all(c.status == "PASS" for c in with_hardware.checks if c.mode == "BOLT_SHEAR")
    assert with_hardware.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    monkeypatch.setattr(
        analytical,
        "build_ssmc_cut_ledger",
        lambda _: replace(result.cuts, finite_coverage_proven=True),
    )
    qualified_gates = SSMCAnalyticalAuthorities(
        {},
        plate_product_qualification_id="TEST_PLATE",
        member_applicability_qualification_id="TEST_MEMBER",
        section_2_3_2_qualification_id="TEST_SECTION",
        continuous_cut_coverage_id="TEST_CUT_COVERAGE",
    )
    covered = evaluate_ssmc_analytical(zero_request, qualified_gates)
    assert "POLYGON_CONTINUOUS_CUT_COVERAGE_NOT_PROVEN" not in covered.blockers
    assert "PLATE_PRODUCT_QUALIFICATION_REQUIRED" not in covered.blockers
    assert "MEMBER_APPLICABILITY_QUALIFICATION_REQUIRED" not in covered.blockers
    assert "SECTION_2_3_2_QUALIFICATION_REQUIRED" not in covered.blockers
    assert covered.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"


def test_ineligible_planar_group_returns_review_records(monkeypatch: pytest.MonkeyPatch) -> None:
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
    preview = preview_ssmc(request.physical)
    short_member = replace(
        preview,
        input=replace(
            preview.input,
            inclined=replace(preview.input.inclined, length=Q.of(1, Unit.IN)),
        ),
    )
    with pytest.raises(ArithmeticError, match="SSMC_MEMBER_CUT_BEYOND_GROUP_NOT_AVAILABLE"):
        _actions(short_member)
    invalid_shaft = replace(
        preview.geometry.shafts[0],
        layer_owners=("MITER_WEB_PLATE", "UNREGISTERED_MEMBER"),
    )
    invalid_preview = replace(
        preview,
        geometry=replace(preview.geometry, shafts=(invalid_shaft, *preview.geometry.shafts[1:])),
    )
    monkeypatch.setattr(analytical, "preview_ssmc", lambda _: invalid_preview)
    with pytest.raises(ArithmeticError, match="SSMC_PHYSICAL_LAYER_OWNERSHIP_INVALID"):
        evaluate_ssmc_analytical(request)


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
    stainless = http("POST", path + "?connector_body_material=SS316", payload)
    assert stainless.status_code == 422
    assert stainless.json()["detail"]["code"] == "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"
    assert http("POST", path, payload | {"authorities": "FORGED"}).status_code == 422
    payload["action"]["combination_id"] = " "
    invalid_action = http("POST", path, payload)
    assert invalid_action.status_code == 422
    assert invalid_action.json()["detail"] == {
        "code": "SSMC_INPUT_INVALID",
        "message": "SSMC_FACTORED_LRFD_ACTION_AUTHORITY_REQUIRED",
    }
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
