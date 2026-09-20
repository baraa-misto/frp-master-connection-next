"""Adversarial provider binding and native P2 dispatch, with test-only sources."""

from dataclasses import replace

import pytest

from frp_master_connection.application.stainless_family_activation import (
    ClearInvocation,
    PlateInvocation,
    ShapeInvocation,
    evaluate_bound_body,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.stainless_plate import PlateContext
from frp_master_connection.calculation.stainless_plate_clear_body import (
    ClearContext,
    evaluate_clear_plate,
)
from frp_master_connection.domain.stainless_shape import ShapeContext
from tests.application.test_stainless_activation_dispatch import bound
from tests.calculation.test_stainless_angle import record as shape_record
from tests.calculation.test_stainless_plate import record as plate_record
from tests.calculation.test_stainless_plate_clear_body import q, record, request


@pytest.mark.parametrize("mode", ["pass", "fail", "combined", "geometry", "source", "empty"])
def test_clear_plate_dispatch_is_exact_frozen_p2_with_bound_response(mode: str) -> None:
    binding, authority = bound("PLATE")
    response = evaluate_bound_body(binding, authority).response
    assert response is not None
    r = request(axial="-1000" if mode == "fail" else "-10")
    r = replace(
        r,
        section=replace(r.section, id=binding.body),
        demand=replace(r.demand, response_method=response.fingerprint),
    )
    if mode == "combined":
        r = replace(r, demand=replace(r.demand, shear=q(1, Unit.KIP)))
    elif mode == "geometry":
        r = replace(r, section=replace(r.section, width=q(0)))
    elif mode == "empty":
        r = replace(r, demand=replace(r.demand, axial=q(0, Unit.KIP)))
    context = ClearContext() if mode in {"geometry", "source"} else ClearContext((record(r),))
    result = evaluate_bound_body(binding, replace(authority, clear=ClearInvocation(r, context)))
    assert result.clear == evaluate_clear_plate(r, context)
    assert result.clear is not None
    assert result.clear.family_activation is False
    if mode == "pass":
        assert any(c.id.endswith("C2_P2") and c.comparison == "PASS" for c in result.checks)
    elif mode == "fail":
        assert any(c.id.endswith("C2_P2") and c.comparison == "FAIL" for c in result.checks)
    elif mode != "empty":
        assert result.blockers


def test_clear_plate_identity_and_actual_response_binding_are_not_aliases() -> None:
    binding, authority = bound("PLATE")
    r = request()
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(binding, replace(authority, clear=ClearInvocation(r, ClearContext())))
    r = replace(r, section=replace(r.section, id=binding.body))
    result = evaluate_bound_body(
        binding, replace(authority, clear=ClearInvocation(r, ClearContext()))
    )
    assert result.clear is None
    assert result.blockers == ("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED",)


def test_provider_form_mismatch_cannot_cross_trusted_binding() -> None:
    plate_binding, plate = bound("PLATE")
    angle_binding, angle = bound("ANGLE")
    assert angle.shape is not None
    assert plate.plate is not None
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(plate_binding, replace(plate, shape=angle.shape))
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(angle_binding, replace(angle, plate=plate.plate))
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(
            plate_binding,
            replace(
                plate,
                plate=replace(
                    plate.plate,
                    request=replace(
                        plate.plate.request,
                        geometry=replace(plate.plate.request.geometry, id="FOREIGN"),
                    ),
                ),
            ),
        )
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(
            angle_binding,
            replace(
                angle,
                shape=replace(
                    angle.shape,
                    request=replace(
                        angle.shape.request,
                        demand=replace(angle.shape.request.demand, body="FOREIGN"),
                    ),
                ),
            ),
        )
    assert (
        "STAINLESS_PLATE_RESOLVED_PLAN_SOURCE_REQUIRED"
        in evaluate_bound_body(
            plate_binding,
            replace(plate, plate=None),
        ).blockers
    )


@pytest.mark.parametrize("form", ["ANGLE", "TEE"])
@pytest.mark.parametrize("condition", ["torsion", "local", "section"])
def test_native_shape_fail_closed_status_survives_activation(form: str, condition: str) -> None:
    binding, authority = bound(form)
    assert authority.shape is not None
    original = authority.shape
    r = original.request
    if condition == "torsion":
        r = replace(r, demand=replace(r.demand, torsion=q(1, Unit.KIP_IN)))
    elif condition == "local":
        r = replace(r, local_mechanism_required=True)
    source = replace(
        shape_record(r), response_fingerprint=original.context.records[0].response_fingerprint
    )
    if condition == "section":
        source = replace(source, section_qualification="")
    result = evaluate_bound_body(
        binding, replace(authority, shape=ShapeInvocation(r, ShapeContext((source,))))
    )
    assert result.shape is not None
    assert result.shape.status in result.blockers
    assert not result.checks
    assert not result.frp_body_resistance_used


@pytest.mark.parametrize("condition", ["geometry", "material", "empty"])
def test_p1_native_unchecked_conditions_remain_blocked(condition: str) -> None:
    binding, authority = bound("PLATE")
    assert authority.plate is not None
    original = authority.plate
    r = original.request
    if condition == "geometry":
        r = replace(r, geometry=replace(r.geometry, width=q(0)))
    elif condition == "empty":
        r = replace(r, checks=())
    source = replace(plate_record(r), demand_authority=original.context.records[0].demand_authority)
    context = (
        PlateContext((source,), final_source_sha256=None)
        if condition == "material"
        else PlateContext((source,))
    )
    result = evaluate_bound_body(binding, replace(authority, plate=PlateInvocation(r, context)))
    assert result.plate is not None
    assert result.blockers
    assert not result.checks


def test_defensive_empty_provider_result_cannot_be_promoted_to_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.application import stainless_family_activation as activation

    binding, authority = bound("PLATE")
    normal = evaluate_bound_body(binding, authority)
    assert normal.plate is not None
    # Inject a malformed internal provider return solely to prove the wrapper
    # does not turn an empty evaluated set into a supported PASS.
    empty = replace(normal.plate, checks=())
    monkeypatch.setattr(activation, "evaluate_stainless_plate", lambda *_: empty)
    result = evaluate_bound_body(binding, authority)
    assert not result.checks
    assert result.blockers == ("STAINLESS_CHECK_PLAN_NOT_RESOLVED",)
