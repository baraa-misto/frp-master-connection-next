"""Public aggregation with explicitly test-only, server-resolved response evidence.

Nothing here is a production source or a public source-registration interface.
Native non-body checks retain their objects, fingerprints and comparison values.
"""

from dataclasses import replace
from typing import Any

import pytest
from tests.api.test_connector_materials import http, native_payload
from tests.calculation.test_stainless_response import record

from frp_master_connection.api import stainless_activation as api
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.stainless_connection_design import (
    BoundNonBodyCheck,
    ConnectionAuthority,
    NonBodyAuthority,
)
from frp_master_connection.application.stainless_family_activation import RequiredCheck
from frp_master_connection.application.stainless_native_results import native_row_partition
from frp_master_connection.application.stainless_public_authority import resolve_public_authority
from frp_master_connection.calculation.stainless_response import (
    ResponseContext,
    evaluate_stainless_response,
)


def test_qualified_native_member_failure_governs_public_summary_with_shape_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retained: list[BoundNonBodyCheck] = []

    def qualified(
        route: str, assembly: MaterialAssembly, preview: object, design: object
    ) -> ConnectionAuthority:
        initial = resolve_public_authority(route, assembly, preview, design)
        assert len(initial.bodies) == 1
        source = initial.bodies[0]
        # Test-only external response attests the exact native interface input.
        # It does not assert that a real production slip/contact source exists.
        request = replace(
            source.response_request, output_wrenches=(source.response_request.input_wrench,)
        )
        context = ResponseContext((record(request),))
        response = evaluate_stainless_response(request, context)
        assert response.status == "QUALIFIED_RESPONSE"
        body = replace(source, response_request=request, response_context=context)
        partition = native_row_partition(assembly, design)
        checks = tuple(
            BoundNonBodyCheck(
                check.owner.physical_id,
                RequiredCheck(
                    ":".join(check.identity),
                    check.owner.role.value,
                    check.result.numerical_comparison.value,
                    check.result.input_fingerprint,
                ),
                check.result,
            )
            for check in partition.retained_non_body
            if check.result.numerical_comparison.value in {"PASS", "FAIL"}
        )
        retained.extend(checks)
        assert any(check.check.comparison == "FAIL" for check in checks)
        return ConnectionAuthority(
            (body,),
            NonBodyAuthority(
                route,
                assembly.native_identity,
                (response.fingerprint,),
                checks,
                ("TEST_ONLY_UNRESOLVED_LOCAL_MECHANISM",),
                partition,
                False,
            ),
        )

    monkeypatch.setattr(api, "resolve_public_authority", qualified)
    response = http(
        "POST",
        "/api/v1/calculations/clip-angle/design-check?connector_body_material=SS316",
        native_payload("clip-angle"),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "FAIL"
    assert "STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED" in result["blockers"]
    assert "TEST_ONLY_UNRESOLVED_LOCAL_MECHANISM" in result["blockers"]
    assert result["bodies"][0]["trace"]["shape"] is None
    assert result["bodies"][0]["frp_body_resistance_used"] is False
    actual: list[dict[str, Any]] = result["trace"]["activation"]["checks"]
    assert [(c["id"], c["comparison"], c["provider_fingerprint"]) for c in actual] == [
        (c.check.id, c.check.comparison, c.check.provider_fingerprint) for c in retained
    ]


@pytest.mark.parametrize("route", ["clip-angle", "tee-connector", "beam-web-splice"])
def test_production_dispatch_reaches_frozen_response_gate_without_fabricated_outputs(
    route: str,
) -> None:
    response = http(
        "POST",
        f"/api/v1/calculations/{route}/design-check?connector_body_material=SS316",
        native_payload(route),
    )
    assert response.status_code == 200
    for body in response.json()["bodies"]:
        native_response = body["trace"]["response"]
        assert native_response["status"] == "STAINLESS_RESPONSE_SOURCE_REQUIRED"
        assert native_response["demands"] == []
        assert native_response["authority"] is None
        assert native_response["family_activation"] is False
        assert body["provider_fingerprints"] == [native_response["fingerprint"]]
