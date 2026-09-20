"""Controlled Stage 3.2-R9 Tee interface and brace-direction regressions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import frp_master_connection.application.tee_orchestration as tee_orchestration
from frp_master_connection.api.tee_mapping import map_tee_connector_request
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    TeeAssemblyStatus,
    design_check_tee_connector,
    evaluate_multirow_connection,
    evaluate_multirow_connection_through_handoff,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.application.tee_orchestration import (
    TeeConnectorOrchestrationRequest,
    _TeeResolvedAssembly,
)
from frp_master_connection.calculation import GeometryStatus, PlanAvailability
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.domain import INTERNAL_FASTENER_ACCESS_REQUIRED
from frp_master_connection.geometry import PlacedComponentGeometry3D, UnitVector3D
from tests.tee_fixtures import (
    build_tee_r7_angle_payload,
    build_tee_r8_profile_wall_payload,
)

_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "stage_3_2_r9_tee_interface_brace_direction_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "7D888ACB32220049B3522BA19D0A9217E796E4F4E5A8294463B10C8D078E54B9"


def _request(payload: dict[str, Any]) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))


def _angle_payload(angle: str = "0") -> dict[str, Any]:
    payload = build_tee_r7_angle_payload()
    payload["brace_inclination_degrees"] = angle
    return payload


def _large_profile_wall_payload(family: str, angle: str) -> dict[str, Any]:
    payload = build_tee_r8_profile_wall_payload(
        profile_family=family,
        unloaded_end_distance="6",
    )
    payload["brace_inclination_degrees"] = angle
    payload["interface_a_layout"]["bolts_per_row"] = 1
    payload["connector_dimensions"]["connector_length"]["value"] = "16"
    payload["connected_member_profile"]["dimensions"]["depth"]["value"] = "12"
    return payload


def _fixed_grid_angle_payload(angle: str) -> dict[str, Any]:
    """Use enough physical Angle surface for the R10-fixed grid at inclination."""

    payload = build_tee_r7_angle_payload(unloaded_end_distance="6")
    payload["brace_inclination_degrees"] = angle
    payload["interface_a_layout"]["bolts_per_row"] = 1
    payload["connector_dimensions"]["connector_length"]["value"] = "16"
    payload["connected_member_profile"]["dimensions"].update(
        {
            "leg_y": {"value": "12", "unit": "in"},
            "leg_z": {"value": "12", "unit": "in"},
            "member_length": {"value": "20", "unit": "in"},
        }
    )
    return payload


def _placed_member(
    resolved: _TeeResolvedAssembly,
    member_id: str,
) -> PlacedComponentGeometry3D:
    return next(
        item for item in resolved.context.basis.placed_members if item.component.id == member_id
    )


def test_r9_owner_golden_is_byte_exact_and_complete() -> None:
    raw = _GOLDEN_PATH.read_bytes()
    fixture = json.loads(raw)

    assert hashlib.sha256(raw).hexdigest().upper() == _GOLDEN_SHA256
    assert fixture["version"] == "RC1"
    assert [item["id"] for item in fixture["benchmarks"]] == [
        "R9_I1_STEM_2X1_FLANGE_2X2",
        "R9_I2_STEM_1X2_FLANGE_2X2",
        "R9_D1_ZERO_INCLINATION_BACKWARD_COMPATIBILITY",
        "R9_D2_POSITIVE_30_DEGREES",
        "R9_D3_NEGATIVE_30_DEGREES",
        "R9_D4_ARBITRARY_27_5_DEGREES",
        "R9_D5_INCLINATION_DOMAIN",
        "R9_H1_SCHEMATIC_FASTENER_PRESENTATION",
        "R9_X1_COMBINED_ANGLE_30_INDEPENDENT_GROUPS",
    ]


def test_r9_i1_two_by_one_stem_and_two_by_two_flange_are_independent() -> None:
    base = _angle_payload()
    changed_a = deepcopy(base)
    changed_a["interface_a_layout"]["bolts_per_row"] = 1
    changed_b = deepcopy(base)
    changed_b["interface_b_layout"]["row_count"] = 3

    base_preview = preview_tee_connector(_request(base))
    a_preview = preview_tee_connector(_request(changed_a))
    b_preview = preview_tee_connector(_request(changed_b))

    assert a_preview.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert a_preview.visualization is not None
    assert base_preview.visualization is not None
    assert b_preview.visualization is not None
    assert len(a_preview.visualization.interface_a_bolts) == 2
    assert len(a_preview.visualization.interface_b_bolts) == 4
    assert a_preview.visualization.interface_b_bolts == (
        base_preview.visualization.interface_b_bolts
    )
    assert a_preview.interface_b.interface_fingerprint == (
        base_preview.interface_b.interface_fingerprint
    )
    assert a_preview.interface_a.interface_fingerprint != (
        base_preview.interface_a.interface_fingerprint
    )
    assert b_preview.visualization.interface_a_bolts == (
        base_preview.visualization.interface_a_bolts
    )
    assert b_preview.interface_a.interface_fingerprint == (
        base_preview.interface_a.interface_fingerprint
    )
    assert b_preview.interface_b.interface_fingerprint != (
        base_preview.interface_b.interface_fingerprint
    )


def test_r9_i2_one_row_stem_is_geometry_valid_and_calculation_unsupported() -> None:
    payload = _angle_payload()
    payload["interface_a_layout"]["row_count"] = 1
    request = _request(payload)

    preview = preview_tee_connector(request)
    design = design_check_tee_connector(request)

    assert preview.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert preview.visualization is not None
    assert len(preview.visualization.interface_a_bolts) == 2
    assert len(preview.visualization.interface_b_bolts) == 4
    assert preview.interface_a.preview.geometry_status is GeometryStatus.VALID
    assert preview.interface_a.preview.plan_availability is (
        PlanAvailability.CALCULATION_NOT_SUPPORTED
    )
    assert preview.interface_a.preview.design_check_ready is False
    assert preview.design_check_ready is False
    assert design.interface_a.design is None
    assert design.interface_b.design is not None
    assert design.ordinary_pass_allowed is False
    assert design.assembly_status is TeeAssemblyStatus.NOT_EVALUATED


def test_r9_single_row_design_path_is_independently_fail_closed_for_both_interfaces() -> None:
    payload = _angle_payload()
    payload["interface_a_layout"]["row_count"] = 1
    payload["interface_b_layout"]["row_count"] = 1

    design = design_check_tee_connector(_request(payload))

    assert design.interface_a.design is None
    assert design.interface_b.design is None
    assert design.supported_interface_failure_present is False
    assert design.ordinary_pass_allowed is False


def test_r9_single_row_preview_authority_cannot_execute_multirow_resistance() -> None:
    payload = _angle_payload()
    payload["interface_a_layout"]["row_count"] = 1
    request = resolve_tee_connector_request(_request(payload)).interface_a_request

    evaluated = evaluate_multirow_connection(request)
    handoff = evaluate_multirow_connection_through_handoff(request)

    for response in (evaluated, handoff):
        assert response.preview.geometry_status is GeometryStatus.VALID
        assert response.preview.plan_availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
        assert response.preview.resistance_evaluated is False
        assert response.calculation_result is None
        assert response.automatic_handoff_results == ()
        assert response.automatic_group_mode_integration is None


def test_r9_omitted_and_explicit_zero_preserve_exact_legacy_identity() -> None:
    omitted = _angle_payload()
    omitted.pop("brace_inclination_degrees")
    explicit = _angle_payload("0")

    omitted_preview = preview_tee_connector(_request(omitted))
    explicit_preview = preview_tee_connector(_request(explicit))

    assert omitted_preview.engineering_fingerprint == explicit_preview.engineering_fingerprint
    assert omitted_preview.visualization == explicit_preview.visualization
    assert omitted_preview.connected_member_profile.brace_inclination_degrees == 0
    assert omitted_preview.connected_member_profile.brace_placement_frame == (
        explicit_preview.connected_member_profile.brace_placement_frame
    )


@pytest.mark.parametrize(
    ("angle", "expected_sine", "expected_cosine"),
    [
        ("30", Decimal("0.5"), Decimal("0.8660254037844386")),
        ("-30", Decimal("-0.5"), Decimal("0.8660254037844386")),
    ],
)
def test_r9_signed_thirty_degree_basis_rotates_only_brace_interface_a(
    angle: str,
    expected_sine: Decimal,
    expected_cosine: Decimal,
) -> None:
    rotated_payload = _fixed_grid_angle_payload(angle)
    zero_payload = _fixed_grid_angle_payload("0")
    zero = resolve_tee_connector_request(_request(zero_payload))
    rotated = resolve_tee_connector_request(_request(rotated_payload))
    zero_preview = preview_tee_connector(zero.request)
    rotated_preview = preview_tee_connector(rotated.request)
    zero_brace = _placed_member(zero, "tee-brace")
    rotated_brace = _placed_member(rotated, "tee-brace")
    zero_support = _placed_member(zero, "tee-support")
    rotated_support = _placed_member(rotated, "tee-support")
    zero_tee = zero.context.basis.placed_connectors[0]
    rotated_tee = rotated.context.basis.placed_connectors[0]
    l0 = zero_brace.global_frame.x_axis
    u0 = zero.context.basis.joint_frame.x_axis
    ltheta = rotated_brace.global_frame.x_axis

    assert Decimal(str(ltheta.dot(l0))) == pytest.approx(expected_cosine, abs=Decimal("1e-15"))
    assert Decimal(str(ltheta.dot(u0))) == pytest.approx(expected_sine, abs=Decimal("1e-15"))
    assert rotated.request.global_force == zero.request.global_force
    assert rotated.request.global_moment == zero.request.global_moment
    assert rotated.request.global_reference_point == zero.request.global_reference_point
    assert rotated_support == zero_support
    assert rotated_tee == zero_tee
    assert zero_preview.visualization is not None
    assert rotated_preview.visualization is not None
    assert rotated_preview.visualization.interface_b_bolts == (
        zero_preview.visualization.interface_b_bolts
    )
    assert rotated_preview.interface_b.interface_fingerprint == (
        zero_preview.interface_b.interface_fingerprint
    )
    assert rotated_preview.connected_member_profile.brace_inclination_sine == expected_sine
    assert rotated_preview.connected_member_profile.brace_inclination_cosine == expected_cosine
    assert rotated_preview.engineering_fingerprint != zero_preview.engineering_fingerprint


def test_r9_arbitrary_angle_is_deterministic_and_profile_roll_is_separate() -> None:
    payload = _fixed_grid_angle_payload("27.5")
    first = resolve_tee_connector_request(_request(payload))
    second = resolve_tee_connector_request(_request(payload))
    rolled_payload = deepcopy(payload)
    rolled_payload["connected_member_profile"]["profile_orientation"] = "ROTATION_90"
    rolled = resolve_tee_connector_request(_request(rolled_payload))

    assert first.connected_member_profile.brace_inclination_degrees == Decimal("27.5")
    assert first.connected_member_profile.brace_placement_frame == (
        second.connected_member_profile.brace_placement_frame
    )
    assert _placed_member(first, "tee-brace").global_frame.x_axis == (
        _placed_member(rolled, "tee-brace").global_frame.x_axis
    )
    assert tee_orchestration._owner_profile_frame(
        _placed_member(first, "tee-brace"), first.request.connected_member_profile
    ) != tee_orchestration._owner_profile_frame(
        _placed_member(rolled, "tee-brace"), rolled.request.connected_member_profile
    )


def test_r9_shared_r5_trigonometry_is_used_without_libm() -> None:
    assert deterministic_sine_cosine_degrees(Decimal("30")) == (
        float.fromhex("0x1.fffffffffffffp-2"),
        float.fromhex("0x1.bb67ae8584cabp-1"),
    )
    assert tee_orchestration._brace_inclination_axes(
        UnitVector3D(0, 0, 1),
        UnitVector3D(1, 0, 0),
        Decimal(0),
    ) == (
        UnitVector3D(1, 0, 0),
        UnitVector3D(0, 0, 1),
    )
    assert tee_orchestration._brace_inclination_coefficients(Decimal(90)) == (
        Decimal(1),
        Decimal(0),
    )
    assert tee_orchestration._brace_inclination_coefficients(Decimal(-90)) == (
        Decimal(-1),
        Decimal(0),
    )


@pytest.mark.parametrize("angle", ["90", "-90"])
def test_r9_inclination_boundaries_are_accepted_by_exact_contract(angle: str) -> None:
    request = _request(_angle_payload(angle))
    assert request.brace_inclination_degrees == Decimal(angle)


@pytest.mark.parametrize("angle", ["90.0001", "-90.0001", "NaN", "not-a-number"])
def test_r9_invalid_inclination_strings_are_rejected(angle: str) -> None:
    payload = _angle_payload()
    payload["brace_inclination_degrees"] = angle
    with pytest.raises(ValidationError, match="brace_inclination_degrees"):
        TeeConnectorRequestDTO.model_validate(payload)


def test_r9_inclination_transport_rejects_non_string_and_domain_rejects_bad_types() -> None:
    payload = _angle_payload()
    payload["brace_inclination_degrees"] = 30
    with pytest.raises(ValidationError, match="valid string"):
        TeeConnectorRequestDTO.model_validate(payload)

    request = _request(_angle_payload())
    with pytest.raises(TypeError, match="must be a Decimal"):
        replace(request, brace_inclination_degrees=cast(Decimal, object()))
    with pytest.raises(ValueError, match="finite"):
        replace(request, brace_inclination_degrees=Decimal("NaN"))
    with pytest.raises(ValueError, match="between -90 and 90"):
        replace(request, brace_inclination_degrees=Decimal("91"))


@pytest.mark.parametrize("role", ["COLUMN", "BEAM"])
def test_r9_column_and_beam_use_the_same_signed_inclination_semantics(role: str) -> None:
    payload = _fixed_grid_angle_payload("30")
    payload["support_role"] = role
    if role == "BEAM":
        payload["global_force"] = {"x": "0.1", "y": "0", "z": "0", "unit": "kip"}
    resolved = resolve_tee_connector_request(_request(payload))
    zero_payload = deepcopy(payload)
    zero_payload["brace_inclination_degrees"] = "0"
    zero = resolve_tee_connector_request(_request(zero_payload))
    ltheta = _placed_member(resolved, "tee-brace").global_frame.x_axis
    l0 = _placed_member(zero, "tee-brace").global_frame.x_axis
    u0 = zero.context.basis.joint_frame.x_axis

    assert ltheta.dot(l0) == pytest.approx(0.8660254037844386)
    assert ltheta.dot(u0) == pytest.approx(0.5)


def test_r9_nonzero_channel_and_rhs_preserve_profile_wall_authority() -> None:
    channel = preview_tee_connector(_request(_large_profile_wall_payload("CHANNEL", "-30")))
    rhs = preview_tee_connector(
        _request(_large_profile_wall_payload("RECTANGULAR_HOLLOW_SECTION", "30"))
    )

    assert channel.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert rhs.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert channel.visualization is not None
    assert rhs.visualization is not None
    assert len(channel.visualization.interface_a_bolts) == 2
    assert len(rhs.visualization.interface_a_bolts) == 2
    assert INTERNAL_FASTENER_ACCESS_REQUIRED not in channel.warnings
    assert INTERNAL_FASTENER_ACCESS_REQUIRED not in rhs.warnings
    assert rhs.design_limitations == (
        "RHS_LOCAL_WALL_RESPONSE",
        "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
    )
    assert all(
        trace.hardware.internal_hardware_count == 0 for trace in rhs.rectangular_full_through_paths
    )


def test_r9_tee_bolt_snapshots_retain_authoritative_axes_and_washer_behavior() -> None:
    payload = _fixed_grid_angle_payload("30")
    preview = preview_tee_connector(_request(payload))
    assert preview.visualization is not None
    bolts = (
        *preview.visualization.interface_a_bolts,
        *preview.visualization.interface_b_bolts,
    )

    assert len(bolts) == 6
    assert all(
        bolt.bolt_diameter == preview.visualization.base_connection.bolt.bolt_diameter
        for bolt in bolts
    )
    assert all(bolt.axis.norm == pytest.approx(1) for bolt in bolts)
    assert all(bolt.washers == () for bolt in bolts)


def test_r9_internal_single_row_preview_authority_is_strict_boolean() -> None:
    resolved = resolve_tee_connector_request(_request(_angle_payload()))
    with pytest.raises(TypeError, match="must be Boolean"):
        replace(
            resolved.interface_a_request,
            single_row_geometry_preview_authorized=cast(bool, 1),
        )
