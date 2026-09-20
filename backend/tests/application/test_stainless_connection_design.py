"""Full-connection source-limited aggregation over actual canonical family scenes."""

from dataclasses import replace

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.stainless_connection_design import (
    BoundNonBodyCheck,
    ConnectionAuthority,
    NonBodyAuthority,
    evaluate_stainless_connection,
)
from frp_master_connection.application.stainless_family_activation import ROUTES, RequiredCheck
from frp_master_connection.calculation.stainless_response import (
    ResponseContext,
    evaluate_stainless_response,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from tests.api.test_connector_materials import native_payload
from tests.application.test_stainless_activation_dispatch import bound
from tests.calculation.test_stainless_response import record


@pytest.mark.parametrize("route", tuple(ROUTES))
def test_real_family_without_production_qualification_is_explicitly_source_limited(
    route: str,
) -> None:
    preview = FAMILIES[route].preview(native_payload(route))
    result = evaluate_stainless_connection(route, preview)
    assert result.status == "ENGINEERING_REVIEW_REQUIRED"
    assert result.checks == ()
    assert "STAINLESS_NON_BODY_RESPONSE_REVALIDATION_REQUIRED" in result.blockers
    assert {b.binding.body for b in result.bodies} == {
        c.physical_id for c in result.assembly.components if c.role is ComponentRole.CONNECTOR_BODY
    }
    assert all("STAINLESS_RESPONSE_SOURCE_REQUIRED" in b.blockers for b in result.bodies)
    assert all(not b.frp_body_resistance_used for b in result.bodies)
    assert all(b.plate is None and b.shape is None for b in result.bodies)
    assert result == evaluate_stainless_connection(route, preview)


@pytest.mark.parametrize("route", ["single-bolt", "multi-row", "direct-side-lap-concrete"])
def test_no_body_route_cannot_enter_connector_dispatch(route: str) -> None:
    with pytest.raises(ValueError, match="MATERIAL_NOT_APPLICABLE_TO_ROUTE"):
        evaluate_stainless_connection(route, FAMILIES[route].preview(native_payload(route)))


def test_foreign_and_duplicate_authority_cannot_attach_to_actual_family() -> None:
    preview = FAMILIES["clip-angle"].preview(native_payload("clip-angle"))
    _, source = bound("ANGLE")
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_stainless_connection(
            "clip-angle", preview, authority=ConnectionAuthority((source,))
        )
    identity = evaluate_stainless_connection("clip-angle", preview).bodies[0].binding
    source = replace(source, binding=identity)
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        evaluate_stainless_connection(
            "clip-angle", preview, authority=ConnectionAuthority((source, source))
        )


@pytest.mark.parametrize("case", ["stale", "response", "body", "role", "complete", "incomplete"])
def test_nonbody_certificate_is_bound_and_cannot_substitute_body_authority(case: str) -> None:
    route = "clip-angle"
    preview = FAMILIES[route].preview(native_payload(route))
    initial = evaluate_stainless_connection(route, preview)
    binding = initial.bodies[0].binding
    _, source = bound("ANGLE")
    request = replace(
        source.response_request,
        route=route,
        bodies=(binding.body,),
        geometry_sha256=binding.native_identity,
    )
    context = ResponseContext((record(request),))
    response = evaluate_stainless_response(request, context)
    # No shape properties are asserted by this response-only source.
    source = replace(
        source, binding=binding, response_request=request, response_context=context, shape=None
    )
    member = next(c for c in initial.assembly.components if c.role is ComponentRole.PRIMARY_MEMBER)
    check = RequiredCheck("TEST_MEMBER", member.role.value, "PASS", "a" * 64)
    nonbody = NonBodyAuthority(
        route,
        binding.native_identity,
        (response.fingerprint,),
        (BoundNonBodyCheck(member.physical_id, check, check),),
        (),
        (),
        case == "complete",
    )
    error = None
    if case == "stale":
        nonbody = replace(nonbody, native_identity="b" * 64)
        error = "SNAPSHOT_STALE"
    elif case == "response":
        nonbody = replace(nonbody, response_fingerprints=("b" * 64,))
        error = "MATERIAL_DEPENDENCE_UNRESOLVED"
    elif case == "body":
        nonbody = replace(nonbody, checks=(BoundNonBodyCheck(binding.body, check, check),))
        error = "FRP_BODY_FALLBACK_PROHIBITED"
    elif case == "role":
        nonbody = replace(
            nonbody,
            checks=(BoundNonBodyCheck(member.physical_id, replace(check, domain="BODY"), check),),
        )
        error = "FRP_BODY_FALLBACK_PROHIBITED"
    authority = ConnectionAuthority((source,), nonbody)
    if error:
        with pytest.raises(ValueError, match=error):
            evaluate_stainless_connection(route, preview, authority=authority)
    else:
        result = evaluate_stainless_connection(route, preview, authority=authority)
        assert result.checks == (check,)
        assert result.status == "ENGINEERING_REVIEW_REQUIRED"
        assert result.blockers == ("STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED",)
