"""Public adapter tests; trusted fixtures here never qualify production sources."""

from dataclasses import replace

import pytest

from frp_master_connection.application.stainless_family_activation import (
    BodyAuthority,
    BodyBinding,
    PlateInvocation,
    ShapeInvocation,
    evaluate_bound_body,
)
from frp_master_connection.calculation.stainless_angle import evaluate_stainless_angle
from frp_master_connection.calculation.stainless_plate import PlateContext, evaluate_stainless_plate
from frp_master_connection.calculation.stainless_response import (
    ResponseContext,
    evaluate_stainless_response,
)
from frp_master_connection.calculation.stainless_tee import evaluate_stainless_tee
from frp_master_connection.domain.stainless_shape import ShapeContext
from tests.calculation.test_stainless_angle import record as shape_record
from tests.calculation.test_stainless_angle import request as shape_request
from tests.calculation.test_stainless_plate import record as plate_record
from tests.calculation.test_stainless_plate import request as plate_request
from tests.calculation.test_stainless_response import record as response_record
from tests.calculation.test_stainless_response import request as response_request


def bound(form: str) -> tuple[BodyBinding, BodyAuthority]:
    route = {"PLATE": "beam-web-splice", "ANGLE": "clip-angle", "TEE": "tee-connector"}[form]
    binding = BodyBinding(route, "TEST_BODY", form, "c" * 64)
    r = replace(response_request(), route=route, bodies=(binding.body,))
    rc = ResponseContext((response_record(r),))
    response = evaluate_stainless_response(r, rc)
    authority = BodyAuthority(binding, r, rc)
    if form == "PLATE":
        p = plate_request()
        p = replace(p, geometry=replace(p.geometry, id=binding.body))
        record = replace(plate_record(p), demand_authority=response.fingerprint)
        authority = replace(authority, plate=PlateInvocation(p, PlateContext((record,))))
    else:
        s = shape_request(form)
        s = replace(s, demand=replace(s.demand, body=binding.body, route=route))
        sr = replace(shape_record(s), response_fingerprint=response.fingerprint)
        authority = replace(authority, shape=ShapeInvocation(s, ShapeContext((sr,))))
    return binding, authority


@pytest.mark.parametrize("form", ["PLATE", "ANGLE", "TEE"])
def test_provider_outputs_are_native_verbatim_and_inner_activation_stays_false(form: str) -> None:
    binding, authority = bound(form)
    result = evaluate_bound_body(binding, authority)
    assert result.response == evaluate_stainless_response(
        authority.response_request, authority.response_context
    )
    assert result.activation == "ACTIVE_CONDITIONAL"
    assert not result.frp_body_resistance_used
    assert not result.blockers
    assert result.checks
    assert result.response is not None
    assert result.response.family_activation is False
    if authority.plate is not None:
        assert result.plate == evaluate_stainless_plate(
            authority.plate.request, authority.plate.context
        )
        assert result.plate is not None
        assert result.plate.family_activation is False
    else:
        assert authority.shape is not None
        evaluator = evaluate_stainless_angle if form == "ANGLE" else evaluate_stainless_tee
        assert result.shape == evaluator(authority.shape.request, authority.shape.context)
        assert result.shape is not None
        assert result.shape.family_activation is False


@pytest.mark.parametrize("form", ["PLATE", "ANGLE", "TEE"])
def test_no_source_or_unresolved_response_never_falls_back_to_frp(form: str) -> None:
    binding, authority = bound(form)
    missing = evaluate_bound_body(binding, None)
    assert missing.checks == ()
    assert "STAINLESS_RESPONSE_SOURCE_REQUIRED" in missing.blockers
    assert not missing.frp_body_resistance_used
    failed = evaluate_bound_body(binding, replace(authority, response_context=ResponseContext()))
    assert failed.checks == ()
    assert failed.response is not None
    assert failed.response.status != "QUALIFIED_RESPONSE"
    assert failed.plate is None
    assert failed.shape is None


@pytest.mark.parametrize("form", ["PLATE", "ANGLE", "TEE"])
def test_body_and_action_state_are_not_interchangeable(form: str) -> None:
    binding, authority = bound(form)
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(replace(binding, body="OTHER"), authority)
    with pytest.raises(ValueError, match="SNAPSHOT_STALE"):
        evaluate_bound_body(replace(binding, native_identity="d" * 64), authority)
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_bound_body(
            binding,
            replace(
                authority, response_request=replace(authority.response_request, bodies=("OTHER",))
            ),
        )
    with pytest.raises(ValueError, match="SNAPSHOT_STALE"):
        evaluate_bound_body(
            binding,
            replace(
                authority,
                response_request=replace(authority.response_request, geometry_sha256="d" * 64),
            ),
        )


@pytest.mark.parametrize("form", ["PLATE", "ANGLE", "TEE"])
def test_same_named_body_request_cannot_reuse_different_response_fingerprint(form: str) -> None:
    binding, authority = bound(form)
    if authority.plate is not None:
        p = authority.plate
        authority = replace(
            authority,
            plate=replace(
                p, context=PlateContext((replace(p.context.records[0], demand_authority="e" * 64),))
            ),
        )
    else:
        assert authority.shape is not None
        s = authority.shape
        authority = replace(
            authority,
            shape=replace(
                s,
                context=ShapeContext(
                    (replace(s.context.records[0], response_fingerprint="e" * 64),)
                ),
            ),
        )
    result = evaluate_bound_body(binding, authority)
    assert result.checks == ()
    assert result.blockers == ("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED",)


@pytest.mark.parametrize("form", ["PLATE", "ANGLE", "TEE"])
def test_c2_request_activation_bypass_remains_rejected(form: str) -> None:
    binding, authority = bound(form)
    request = replace(authority.response_request, family_activation_requested=True)
    result = evaluate_bound_body(
        binding,
        replace(
            authority,
            response_request=request,
            response_context=ResponseContext((response_record(request),)),
        ),
    )
    assert result.checks == ()
    assert "STAINLESS_PUBLIC_FAMILY_ACTIVATION_NOT_AUTHORIZED" in result.blockers


def test_invalid_canonical_bindings_rejected() -> None:
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        BodyBinding("single-bolt", "BODY", "PLATE", "a" * 64)
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        BodyBinding("clip-angle", "", "ANGLE", "a" * 64)
    with pytest.raises(ValueError, match="SNAPSHOT_STALE"):
        BodyBinding("clip-angle", "BODY", "ANGLE", "client supplied")
