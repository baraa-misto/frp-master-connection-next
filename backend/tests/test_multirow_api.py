"""Stage 2.4C multi-row transport, HTTP, OpenAPI, and architecture tests."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import cast
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

import frp_master_connection.application.multirow_orchestration as multirow_service
from frp_master_connection.api.app import create_app
from frp_master_connection.api.multirow_mapping import (
    map_multirow_request,
    serialize_multirow_design,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import evaluate_multirow_connection
from frp_master_connection.calculation import (
    EccentricGroupModeWarning,
    EccentricGroupModeWarningCode,
    EccentricLineHandoffStatus,
    PhysicalQuantity,
    Unit,
    multirow_execution_fingerprint,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.security import TrustedIdentity
from tests.api_fixtures import build_j1_preview_api_payload

PREVIEW_ROUTE = "/api/v1/calculations/multi-row/preview"
DESIGN_ROUTE = "/api/v1/calculations/multi-row/design-check"


@dataclass(slots=True)
class _Resolver:
    production_capable: bool = True
    calls: int = 0

    async def resolve(self) -> TrustedIdentity:
        self.calls += 1
        return TrustedIdentity("multirow-test", None, frozenset({"tester"}), "test")


def _app(resolver: _Resolver | None = None) -> FastAPI:
    return create_app(
        settings=AppSettings(environment=ApplicationEnvironment.TEST),
        identity_resolver=resolver,
    )


def _post(
    route: str, payload: dict[str, object], application: FastAPI | None = None
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=_app() if application is None else application)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(route, json=payload)

    return asyncio.run(send())


def _q(value: str, unit: str) -> dict[str, str]:
    return {"value": value, "unit": unit}


def _payload() -> dict[str, object]:
    return {
        "orchestration_contract_version": "2.5C-RC1",
        "demand_source": "EXPLICIT_RESOLVED_CONNECTION_DEMAND",
        "request_id": "REQ-MR-API",
        "connection_id": "CONNECTION-MR-API",
        "interface_id": "INTERFACE-MR-API",
        "load_combination_id": "LC-API",
        "source_reference": "Stage 2.4C API test",
        "display_unit_system": "US_CUSTOMARY",
        "source_length_unit": "in",
        "row_count": 2,
        "bolts_per_row": 2,
        "bolt_diameter": _q(".5", "in"),
        "hole_basis": "US_CUSTOMARY_PRINTED",
        "pitch": _q("2", "in"),
        "gauge": _q("2", "in"),
        "unloaded_end_e1": _q("2", "in"),
        "loaded_boundary_to_row_1_distance": _q("2", "in"),
        "negative_side_distance": _q("1.5", "in"),
        "positive_side_distance": _q("1.5", "in"),
        "geometry_tolerance": _q(".000001", "in"),
        "material_pair": "FRP_FRP",
        "layers": [
            {
                "layer_id": "LAYER-1",
                "component_id": "COMPONENT-1",
                "material_id": "ICE_LOCKED_PULTRUDED_FRP",
                "thickness": _q(".375", "in"),
                "element_classification": "SHAPE",
                "material_axis_angle_degrees": "0",
                "end_use_factors": {
                    "cm": "1",
                    "ct": "1",
                    "cch": "1",
                    "source_reference": "engineer input",
                    "approval_metadata": ["approved"],
                },
                "bearing_thread_status": "EXCLUDED",
            }
        ],
        "signed_force_x": _q("5", "kip"),
        "signed_force_y": _q("0", "kip"),
        "force_reference": "CONNECTION_CENTROID",
        "row_distribution_basis": "ASCE_PRESCRIBED",
        "engineer_distribution_kind": None,
        "engineer_allocations": [],
        "provenance": {
            "source_method": "EXTERNALLY_RESOLVED_CONNECTION_DEMAND",
            "source_document_or_calculation": "engineer calculation",
            "revision": "1",
            "load_combination": "LC-API",
            "reference_point": "CONNECTION_CENTROID",
            "clearance_or_contact_modeled": True,
            "engineer_confirmed": False,
        },
        "bolt_axis_tension_required": False,
        "bolt_axis_tensions": [],
        "time_effect_category": "WIND_TORNADO_SEISMIC",
        "lap_configuration": "DOUBLE_LAP",
        "first_row_method": "ASCE_STANDARD_SIMPLIFIED",
        "prescribed_lbr": ".5",
        "force_line_offset": _q("0", "in"),
        "eccentricity_tolerance": _q(".000001", "in"),
    }


def _automatic_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    zero_moments: bool = False,
    group_local: bool = False,
    normal_force: bool = False,
) -> dict[str, object]:
    if unit_system == "US_CUSTOMARY":
        payload = _payload()
        physical = build_j1_preview_api_payload(explicit_demand=False)
    else:
        from frp_master_connection.domain import EngineeringUnitSystem

        physical = build_j1_preview_api_payload(
            unit_system=EngineeringUnitSystem.SI,
            explicit_demand=False,
        )
        payload = _payload()
        payload.update(
            {
                "display_unit_system": "SI",
                "source_length_unit": "mm",
                "bolt_diameter": _q("12.7", "mm"),
                "pitch": _q("50.8", "mm"),
                "gauge": _q("50.8", "mm"),
                "unloaded_end_e1": _q("50.8", "mm"),
                "loaded_boundary_to_row_1_distance": _q("50.8", "mm"),
                "negative_side_distance": _q("38.1", "mm"),
                "positive_side_distance": _q("38.1", "mm"),
                "geometry_tolerance": _q(".0000254", "mm"),
                "layers": [
                    {
                        **cast(dict[str, object], cast(list[object], payload["layers"])[0]),
                        "thickness": _q("9.525", "mm"),
                    }
                ],
                "force_line_offset": _q("0", "mm"),
                "eccentricity_tolerance": _q(".0000254", "mm"),
            }
        )
    payload["demand_source"] = "AUTOMATIC_MEMBER_END_FORCE"
    payload["interface_id"] = physical["interface_id"]
    payload["load_combination_id"] = "LC-1"
    payload["physical_connection"] = physical
    payload["automatic_action_source_id"] = "action-1"
    payload.pop("signed_force_x")
    payload.pop("signed_force_y")
    payload.pop("force_reference")
    assembly = cast(dict[str, object], physical["joint_assembly"])
    actions = cast(list[dict[str, object]], assembly["member_end_actions"])
    action = actions[0]
    if zero_moments:
        moment = cast(dict[str, str], action["moment"])
        moment.update({"x": "0", "y": "0", "z": "0"})
    if group_local:
        action["coordinate_frame_kind"] = "BOLT_GROUP_LOCAL"
        action["coordinate_frame_owner_id"] = "bolt-group-1"
        action["reference_point"] = {
            "kind": "BOLT_GROUP_ORIGIN",
            "owner_id": "bolt-group-1",
            "position": None,
        }
        force = cast(dict[str, str], action["force"])
        in_plane = ".7" if unit_system == "US_CUSTOMARY" else "3.11375513068235"
        normal = "1" if normal_force and unit_system == "US_CUSTOMARY" else "0"
        force.update({"x": normal, "y": in_plane, "z": "0"})
    return payload


def test_automatic_preview_and_design_preserve_separate_demand_handoff_and_resistance() -> None:
    payload = _automatic_payload()
    preview = _post(PREVIEW_ROUTE, payload)
    design = _post(DESIGN_ROUTE, payload)
    assert preview.status_code == design.status_code == 200
    preview_body = preview.json()
    design_body = design.json()
    assert preview_body["demand_source"] == "AUTOMATIC_MEMBER_END_FORCE"
    assert preview_body["resistance_evaluated"] is False
    assert preview_body["automatic_demand_result"]["availability"] == "CALCULATED"
    assert len(preview_body["visualization"]["automatic_bolt_demands"]) == 4
    assert design_body["automatic_demand_result"]["result_fingerprint"]
    handoff = design_body["automatic_handoff_results"][0]
    assert handoff["coverage"] == "BLOCKED_INCOMPLETE_ACTION_TRANSFER"
    integration = design_body["automatic_group_mode_integration"]
    assert integration["integration_contract_version"] == "2.6B-RC1"
    assert integration["result_fingerprint"]
    assert integration["trace_layers"] == [
        "DEMAND_ANALYSIS",
        "RESISTANCE_HANDOFF",
        "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
        "RESISTANCE_CALCULATION",
        "APPLICATION_INTEGRATION",
    ]
    assert integration["scenario_results"][0]["versions"] == {
        "calculation_contract_version": "2.6A-RC1",
        "eccentric_group_mode_engine_version": "0.1.0.dev1",
        "eccentric_group_mode_rule_set_version": ("asce74-23-ch8-eccentric-group-modes-rc1.dev1"),
        "eccentric_group_mode_result_schema_version": "0.1.0-draft",
        "eccentric_group_mode_fingerprint_schema_version": "0.1.0-draft",
    }
    assert "automatic_group_mode_integration" not in preview_body
    assert design_body["calculation_result"] is None


def test_automatic_api_full_legacy_and_normal_force_boundaries() -> None:
    collinear = _post(
        DESIGN_ROUTE,
        _automatic_payload(zero_moments=True, group_local=True),
    )
    assert collinear.status_code == 200
    full = collinear.json()
    assert full["automatic_handoff_results"][0]["coverage"] == "FULL_LEGACY_COLLINEAR"
    group_mode = full["automatic_group_mode_integration"]["scenario_results"][0]
    assert {item["handoff_status"] for item in group_mode["line_results"]} == {
        "INHERITED_LEGACY_STAGE_2_4B"
    }
    assert full["calculation_result"] is not None

    normal = _post(
        DESIGN_ROUTE,
        _automatic_payload(zero_moments=True, group_local=True, normal_force=True),
    )
    assert normal.status_code == 200
    blocked = normal.json()["automatic_handoff_results"][0]
    assert blocked["coverage"] == "BLOCKED_INCOMPLETE_ACTION_TRANSFER"
    assert blocked["incomplete_required_check_ids"]


def test_automatic_collinear_api_is_exact_and_unit_invariant() -> None:
    responses = tuple(
        _post(
            DESIGN_ROUTE,
            _automatic_payload(
                unit_system=unit_system,
                zero_moments=True,
                group_local=True,
            ),
        )
        for unit_system in ("US_CUSTOMARY", "SI")
    )
    assert all(item.status_code == 200 for item in responses)
    bodies = tuple(item.json() for item in responses)
    for body in bodies:
        demand = cast(dict[str, object], body["automatic_demand_result"])
        scenario = cast(list[dict[str, object]], demand["scenarios"])[0]
        residual = cast(dict[str, str], scenario["residual_moment"])
        assert residual["canonical_value"] == "0"
        handoff = cast(list[dict[str, object]], body["automatic_handoff_results"])[0]
        assert handoff["coverage"] == "FULL_LEGACY_COLLINEAR"
    first = cast(dict[str, object], bodies[0]["automatic_demand_result"])
    second = cast(dict[str, object], bodies[1]["automatic_demand_result"])
    assert first["input_fingerprint"] == second["input_fingerprint"]
    assert first["result_fingerprint"] == second["result_fingerprint"]


def test_r4_corrects_the_controlled_si_execution_fingerprint_exactly() -> None:
    request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(unit_system="SI", zero_moments=True, group_local=True)
        )
    )
    resolved = multirow_service._resolve(request)
    bundle = multirow_service._execution_bundle(request, resolved)

    assert bundle.end_distances.unloaded_end_e1 == PhysicalQuantity.of("50.8", Unit.MM)
    assert bundle.end_distances.physical_pitches == (PhysicalQuantity.of("50.8", Unit.MM),)
    assert bundle.end_distances.row_1_to_unloaded_end_distance == PhysicalQuantity.of(
        "101.6", Unit.MM
    )
    assert bundle.end_distances.loaded_boundary_to_row_1_distance == PhysicalQuantity.of(
        "50.8", Unit.MM
    )
    assert (
        multirow_execution_fingerprint(bundle)
        == "40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69"
    )
    assert (
        multirow_execution_fingerprint(bundle)
        != "7c6d7bb9b3d04246c789ad9ed9b291d5b7349a46435594d9bebb181c8488bf57"
    )
    assert (
        resolved.preview_fingerprint
        == "8b2a9a73704b670f70ffcbbb07b7648bd10857e70678eb7d24483a5b265da3ff"
    )
    assert resolved.preview_fingerprint != (
        "94dee19bc2b27a9a726c94eed9e66ddcfd637d5a80a8d74230d8716b9294e9d2"
    )
    assert (
        resolved.preview_fingerprint
        != "673b55de5986f7c39252f888eef6a2e8a538e66ab54488944b9f4ad820268d8d"
    )


def test_r4_preserves_the_controlled_us_execution_and_preview_fingerprints() -> None:
    request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(unit_system="US_CUSTOMARY", zero_moments=True, group_local=True)
        )
    )
    resolved = multirow_service._resolve(request)
    bundle = multirow_service._execution_bundle(request, resolved)

    assert (
        multirow_execution_fingerprint(bundle)
        == "c61a4d73946a014e218fdf02896ea08de90c1d9f94c6a2ca23495e72ca006a27"
    )
    assert (
        resolved.preview_fingerprint
        == "91bfb0e5dc54ce98d30f46c11e87689ed07b32524cba8c5e997205a8d36ba4c3"
    )
    assert resolved.preview_fingerprint != (
        "f21cd78fc1c332c52268295c4fb273c1dc4ae841e6d94f7edeb5cbd984558961"
    )


@pytest.mark.parametrize(
    ("unit_system", "preview_fingerprint", "first_field", "first_value"),
    [
        (
            "US_CUSTOMARY",
            "91bfb0e5dc54ce98d30f46c11e87689ed07b32524cba8c5e997205a8d36ba4c3",
            "y",
            -3.7640872965260113,
        ),
        (
            "SI",
            "8b2a9a73704b670f70ffcbbb07b7648bd10857e70678eb7d24483a5b265da3ff",
            "z",
            48.07628060534576,
        ),
    ],
)
def test_r5_canonical_preview_payload_exposes_exact_cross_platform_fields(
    unit_system: str,
    preview_fingerprint: str,
    first_field: str,
    first_value: float,
) -> None:
    request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(unit_system=unit_system, zero_moments=True, group_local=True)
        )
    )
    resolved = multirow_service._resolve(request)
    encoded = multirow_service._canonical_multirow_preview_json(request, resolved.visualization)
    payload = cast(dict[str, object], json.loads(encoded))
    request_payload = cast(dict[str, object], payload["request"])
    physical = cast(dict[str, object], request_payload["physical_connection_request"])
    geometry_context = cast(dict[str, object], physical["geometry_context"])
    basis = cast(dict[str, object], geometry_context["basis"])
    surface_sets = cast(list[dict[str, object]], basis["component_surface_sets"])
    patches = cast(list[dict[str, object]], surface_sets[0]["patches"])
    patch_geometry = cast(dict[str, object], patches[0]["geometry"])
    frame = cast(dict[str, object], patch_geometry["frame"])
    origin = cast(dict[str, float], frame["origin"])

    assert origin[first_field] == first_value
    assert hashlib.sha256(encoded.encode("utf-8")).hexdigest() == preview_fingerprint
    assert resolved.preview_fingerprint == preview_fingerprint
    assert '"display_unit_system"' not in encoded
    assert '"camera"' not in encoded


def test_r5_platform_libm_sine_cannot_change_the_canonical_preview_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(zero_moments=True, group_local=True)
        )
    )
    baseline = multirow_service._resolve(baseline_request)
    baseline_json = multirow_service._canonical_multirow_preview_json(
        baseline_request, baseline.visualization
    )
    original_sine = math.sin

    def ubuntu_sine(value: float) -> float:
        result = original_sine(value)
        return math.nextafter(result, -math.inf) if value == math.radians(45.0) else result

    monkeypatch.setattr(math, "sin", ubuntu_sine)
    reconstructed_request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(zero_moments=True, group_local=True)
        )
    )
    reconstructed = multirow_service._resolve(reconstructed_request)

    assert (
        multirow_service._canonical_multirow_preview_json(
            reconstructed_request, reconstructed.visualization
        )
        == baseline_json
    )
    assert reconstructed.preview_fingerprint == baseline.preview_fingerprint


def test_automatic_and_explicit_fields_are_strictly_mutually_exclusive() -> None:
    unknown = _automatic_payload()
    unknown["demand_source"] = "UNKNOWN"
    missing = _automatic_payload()
    missing.pop("automatic_action_source_id")
    mixed = _automatic_payload()
    mixed["signed_force_x"] = _q("1", "kip")
    mismatched = _automatic_payload()
    mismatched["automatic_action_source_id"] = "other-action"
    explicit_missing = _payload()
    explicit_missing.pop("force_reference")
    explicit_automatic = _payload()
    explicit_automatic["automatic_action_source_id"] = "action-1"
    forged_group_mode = _automatic_payload()
    forged_group_mode["automatic_group_mode_integration"] = {
        "result_fingerprint": "client-authored"
    }
    for payload in (
        unknown,
        missing,
        mixed,
        mismatched,
        explicit_missing,
        explicit_automatic,
        forged_group_mode,
    ):
        assert _post(PREVIEW_ROUTE, payload).status_code == 422


def test_automatic_us_si_display_transport_preserves_physical_parent_fingerprints() -> None:
    us_payload = _automatic_payload(zero_moments=True, group_local=True)
    si_payload = copy.deepcopy(us_payload)
    si_payload["display_unit_system"] = "SI"
    us = _post(DESIGN_ROUTE, us_payload)
    si = _post(DESIGN_ROUTE, si_payload)
    assert us.status_code == si.status_code == 200
    us_body = us.json()
    si_body = si.json()
    assert (
        us_body["automatic_demand_result"]["result_fingerprint"]
        == si_body["automatic_demand_result"]["result_fingerprint"]
    )
    assert (
        us_body["automatic_handoff_results"][0]["result_fingerprint"]
        == si_body["automatic_handoff_results"][0]["result_fingerprint"]
    )
    assert (
        us_body["automatic_group_mode_integration"]["result_fingerprint"]
        == si_body["automatic_group_mode_integration"]["result_fingerprint"]
    )


def test_group_mode_line_states_serialize_distinctly_without_api_reduction() -> None:
    request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(
            _automatic_payload(zero_moments=True, group_local=True)
        )
    )
    response = evaluate_multirow_connection(request)
    integration = response.automatic_group_mode_integration
    assert integration is not None
    group_mode = integration.scenario_results[0]
    source_line = group_mode.line_results[0]
    zero_force = PhysicalQuantity.of(0, Unit.N)
    zero_vector = replace(source_line.line_resultant, u=zero_force, v=zero_force)
    zero_line = replace(
        source_line,
        line_resultant=zero_vector,
        parallel_scalar=zero_force,
        transverse_scalar=zero_force,
        handoff_status=EccentricLineHandoffStatus.NOT_REQUIRED_ZERO_LINE_DEMAND,
        required_line_demand=None,
        shear_out_result=None,
        warnings=(),
    )
    nonparallel_line = replace(
        source_line,
        transverse_scalar=PhysicalQuantity.of(1, Unit.N),
        handoff_status=EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
        required_line_demand=None,
        shear_out_result=None,
        warnings=(
            EccentricGroupModeWarning(
                EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE,
                ("bolt_line_id:BOLT_LINE_1",),
            ),
        ),
    )
    reversed_line = replace(
        source_line,
        parallel_scalar=PhysicalQuantity.of(-1, Unit.N),
        handoff_status=EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
        required_line_demand=None,
        shear_out_result=None,
        warnings=(
            EccentricGroupModeWarning(
                EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED,
                ("bolt_line_id:BOLT_LINE_1",),
            ),
        ),
    )
    for line, expected in (
        (zero_line, "NOT_REQUIRED_ZERO_LINE_DEMAND"),
        (nonparallel_line, "CALCULATION_NOT_SUPPORTED"),
        (reversed_line, "CALCULATION_NOT_SUPPORTED"),
    ):
        modified_group = replace(
            group_mode,
            line_results=(line, *group_mode.line_results[1:]),
        )
        modified_integration = replace(integration, scenario_results=(modified_group,))
        serialized = serialize_multirow_design(
            replace(response, automatic_group_mode_integration=modified_integration)
        ).model_dump()
        serialized_line = serialized["automatic_group_mode_integration"]["scenario_results"][0][
            "line_results"
        ][0]
        assert serialized_line["handoff_status"] == expected
        assert serialized_line["line_resultant"]["u"]["canonical_value"] == (
            line.line_resultant.u.canonical_string
        )
        assert serialized_line["parallel_scalar"]["canonical_value"] == (
            line.parallel_scalar.canonical_string
        )
        assert serialized_line["transverse_scalar"]["canonical_value"] == (
            line.transverse_scalar.canonical_string
        )
        assert serialized_line["required_line_demand"] is None
        assert serialized_line["shear_out_result"] is None


def test_preview_and_design_routes_are_stateless_trusted_and_exact() -> None:
    resolver = _Resolver()
    application = _app(resolver)
    preview = _post(PREVIEW_ROUTE, _payload(), application)
    design = _post(DESIGN_ROUTE, _payload(), application)
    assert preview.status_code == design.status_code == 200
    preview_body = preview.json()
    design_body = design.json()
    assert preview_body["api_transport_schema_version"] == "0.3.0-draft"
    assert preview_body["orchestration_contract_version"] == "2.5C-RC1"
    assert preview_body["resistance_evaluated"] is False
    assert "calculation_result" not in preview_body
    assert preview_body["visualization"]["row_ids"] == ["ROW_1", "ROW_2"]
    assert design_body["calculation_result"]["versions"]["calculation_contract_version"] == (
        "2.4B-RC2"
    )
    assert design_body["calculation_result"]["input_fingerprint"]
    assert design_body["calculation_result"]["result_fingerprint"]
    assert design_body["automatic_group_mode_integration"] is None
    assert resolver.calls == 2


def test_loaded_boundary_transport_maps_exactly_into_the_application_request() -> None:
    payload = _payload()
    payload["loaded_boundary_to_row_1_distance"] = _q("4.125", "in")
    mapped = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(payload))
    assert mapped.loaded_boundary_to_row_1_distance == PhysicalQuantity.of("4.125", Unit.IN)


def test_preview_maps_optional_physical_connection_into_same_scene() -> None:
    payload = _payload()
    physical = build_j1_preview_api_payload()
    payload["interface_id"] = physical["interface_id"]
    payload["physical_connection"] = physical
    response = _post(PREVIEW_ROUTE, payload)
    assert response.status_code == 200
    body = response.json()
    visualization = body["visualization"]
    assert visualization["physical_connection"]["assembly_id"] == physical["joint_assembly"]["id"]
    assert [item["bolt_id"] for item in visualization["physical_bolts"]] == [
        "B_R1_L1",
        "B_R1_L2",
        "B_R2_L1",
        "B_R2_L2",
    ]
    assert all(
        item["penetrated_layer_ids"] == ["layer-A", "layer-B"]
        for item in visualization["physical_bolts"]
    )
    assert all(
        item["display"]["bolt_diameter"] == "0.5" for item in visualization["physical_bolts"]
    )
    assert all(
        [hole["diameter"] for hole in item["display"]["holes"]] == ["0.563", "0.563"]
        for item in visualization["physical_bolts"]
    )
    assert visualization["connection_demand"]["resultant"]["value"] == "5"
    assert visualization["connection_demand"]["resultant"]["unit"] == "kip"
    physical_snapshot = visualization["physical_connection"]
    assert all(
        isinstance(parameter["value"], str)
        for primitive in physical_snapshot["primitives"]
        for parameter in primitive["parameters"]
    )
    assert all(
        isinstance(coordinate, str) for coordinate in physical_snapshot["bolt"]["center"].values()
    )


def test_multirow_physical_scene_uses_the_authoritative_standard_hole_for_every_bolt() -> None:
    payload = _payload()
    physical = build_j1_preview_api_payload()
    payload["interface_id"] = physical["interface_id"]
    payload["physical_connection"] = physical
    physical["geometry_template"]["hole_diameter"]["value"] = ".625"

    response = _post(PREVIEW_ROUTE, payload)

    assert response.status_code == 200
    visualization = response.json()["visualization"]
    assert visualization["physical_connection"]["bolt"]["holes"][0]["diameter"] == "0.563"
    assert all(
        [hole["diameter"] for hole in item["display"]["holes"]] == ["0.563", "0.563"]
        for item in visualization["physical_bolts"]
    )
    assert all(item["hole_diameter"]["value"] == "0.563" for item in visualization["bolts"])


def test_invalid_engineering_geometry_returns_structured_http_200() -> None:
    payload = _payload()
    payload["geometry_tolerance"] = _q("3", "in")
    preview = _post(PREVIEW_ROUTE, payload)
    design = _post(DESIGN_ROUTE, payload)
    assert preview.status_code == design.status_code == 200
    assert preview.json()["geometry_status"] == "INVALID_GEOMETRY"
    assert design.json()["calculation_result"] is None


@pytest.mark.parametrize(
    ("mutation", "expected_status"),
    [
        (lambda value: value.pop("row_count"), 422),
        (lambda value: value.__setitem__("row_count", True), 422),
        (lambda value: value.__setitem__("row_count", 1), 422),
        (lambda value: value.__setitem__("pitch", _q("NaN", "in")), 422),
        (lambda value: value.__setitem__("pitch", _q("0", "in")), 422),
        (lambda value: value.__setitem__("source_length_unit", "kip"), 422),
        (lambda value: value.__setitem__("internal_engine_bundle", {}), 422),
    ],
)
def test_malformed_or_untrusted_internal_inputs_are_rejected(
    mutation: Callable[[dict[str, object]], object], expected_status: int
) -> None:
    payload = copy.deepcopy(_payload())
    mutation(payload)
    assert _post(PREVIEW_ROUTE, payload).status_code == expected_status


def test_engineer_distribution_validation_and_deterministic_response() -> None:
    payload = _payload()
    payload["row_distribution_basis"] = "ENGINEER_DEFINED_ROW_DISTRIBUTION"
    payload["engineer_distribution_kind"] = "FRACTIONS"
    payload["engineer_allocations"] = [
        {"row_ordinal": 1, "fraction": ".7"},
        {"row_ordinal": 2, "fraction": ".3"},
    ]
    assert _post(PREVIEW_ROUTE, payload).status_code == 422
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    provenance["engineer_confirmed"] = True
    first = _post(DESIGN_ROUTE, payload)
    second = _post(DESIGN_ROUTE, payload)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content


def test_strict_nested_multirow_validation_rejects_every_ambiguous_shape() -> None:
    invalid_payloads: list[dict[str, object]] = []

    def changed(mutator: Callable[[dict[str, object]], None]) -> dict[str, object]:
        payload = copy.deepcopy(_payload())
        mutator(payload)
        return payload

    def layer(payload: dict[str, object]) -> dict[str, object]:
        layers = payload["layers"]
        assert isinstance(layers, list)
        item = layers[0]
        assert isinstance(item, dict)
        return item

    def factors(payload: dict[str, object]) -> dict[str, object]:
        value = layer(payload)["end_use_factors"]
        assert isinstance(value, dict)
        return value

    invalid_payloads.extend(
        [
            changed(lambda value: factors(value).__setitem__("cm", "bad")),
            changed(lambda value: factors(value).__setitem__("ct", "0")),
            changed(lambda value: factors(value).__setitem__("approval_metadata", [])),
            changed(lambda value: value.__setitem__("layers", [])),
            changed(
                lambda value: value.__setitem__(
                    "layers", [copy.deepcopy(layer(value)), copy.deepcopy(layer(value))]
                )
            ),
            changed(
                lambda value: value.__setitem__(
                    "bolt_axis_tensions",
                    [
                        {"bolt_id": "B_R1_L1", "demand": _q("1", "kip")},
                        {"bolt_id": "B_R1_L1", "demand": _q("2", "kip")},
                    ],
                )
            ),
        ]
    )

    def engineer(
        payload: dict[str, object],
        *,
        kind: str | None,
        allocations: list[dict[str, object]],
        confirmed: bool = True,
    ) -> None:
        payload["row_distribution_basis"] = "ENGINEER_DEFINED_ROW_DISTRIBUTION"
        payload["engineer_distribution_kind"] = kind
        payload["engineer_allocations"] = allocations
        provenance = payload["provenance"]
        assert isinstance(provenance, dict)
        provenance["engineer_confirmed"] = confirmed

    invalid_payloads.extend(
        [
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[{"row_ordinal": 1}],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[
                        {
                            "row_ordinal": 1,
                            "fraction": ".5",
                            "direct_force": _q("1", "kip"),
                        }
                    ],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[{"row_ordinal": 1, "fraction": "bad"}],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[{"row_ordinal": 1, "fraction": "-0.1"}],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[
                        {"row_ordinal": 1, "fraction": ".5"},
                        {"row_ordinal": 1, "fraction": ".5"},
                    ],
                )
            ),
            changed(lambda value: engineer(value, kind=None, allocations=[])),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[{"row_ordinal": 1, "fraction": "1"}],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="FRACTIONS",
                    allocations=[
                        {"row_ordinal": 1, "direct_force": _q("2", "kip")},
                        {"row_ordinal": 2, "direct_force": _q("3", "kip")},
                    ],
                )
            ),
            changed(
                lambda value: engineer(
                    value,
                    kind="DIRECT_ROW_FORCES",
                    allocations=[
                        {"row_ordinal": 1, "fraction": ".5"},
                        {"row_ordinal": 2, "fraction": ".5"},
                    ],
                )
            ),
            changed(lambda value: value.__setitem__("engineer_distribution_kind", "FRACTIONS")),
        ]
    )
    for payload in invalid_payloads:
        assert _post(PREVIEW_ROUTE, payload).status_code == 422


def test_direct_row_force_and_optional_lbr_transport_are_valid() -> None:
    payload = _payload()
    payload["prescribed_lbr"] = None
    payload["row_distribution_basis"] = "ENGINEER_DEFINED_ROW_DISTRIBUTION"
    payload["engineer_distribution_kind"] = "DIRECT_ROW_FORCES"
    payload["engineer_allocations"] = [
        {"row_ordinal": 1, "direct_force": _q("3", "kip")},
        {"row_ordinal": 2, "direct_force": _q("2", "kip")},
    ]
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    provenance["engineer_confirmed"] = True
    assert _post(PREVIEW_ROUTE, payload).status_code == 200


def test_both_routes_map_canonical_decimal_failures_to_http_422() -> None:
    payload = _payload()
    layers = payload["layers"]
    assert isinstance(layers, list)
    layer = layers[0]
    assert isinstance(layer, dict)
    layer["material_axis_angle_degrees"] = "not-a-decimal"
    assert _post(PREVIEW_ROUTE, payload).status_code == 422
    assert _post(DESIGN_ROUTE, payload).status_code == 422
    layer["material_axis_angle_degrees"] = "180"
    assert _post(PREVIEW_ROUTE, payload).status_code == 422

    with patch(
        "frp_master_connection.api.routes.map_multirow_request",
        side_effect=ValueError("canonical mapping failed"),
    ):
        assert _post(PREVIEW_ROUTE, _payload()).status_code == 422
        assert _post(DESIGN_ROUTE, _payload()).status_code == 422


def test_openapi_documents_exact_two_multirow_operations_and_security() -> None:
    document = _app().openapi()
    assert PREVIEW_ROUTE in document["paths"]
    assert DESIGN_ROUTE in document["paths"]
    multirow_paths = [path for path in document["paths"] if "multi-row" in path]
    assert multirow_paths == [PREVIEW_ROUTE, DESIGN_ROUTE]
    for path in multirow_paths:
        operation = document["paths"][path]["post"]
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert "$ref" in schema
        request_schema = document["components"]["schemas"]["MultiRowConnectionRequestDTO"]
        assert "account_id" not in request_schema["properties"]


def test_api_routes_depend_on_application_services_not_calculation_modules() -> None:
    from pathlib import Path

    source = (
        Path(__file__).parents[1] / "src" / "frp_master_connection" / "api" / "routes.py"
    ).read_text(encoding="utf-8")
    assert "application import" in source
    assert "multirow_engine" not in source
    assert "multirow_equations" not in source
    assert "eccentric_group_modes" not in source
    assert "tests/golden" not in source

    with patch(
        "frp_master_connection.api.routes.evaluate_multirow_connection",
        wraps=evaluate_multirow_connection,
    ) as application_service:
        assert _post(DESIGN_ROUTE, _automatic_payload()).status_code == 200
    application_service.assert_called_once()
