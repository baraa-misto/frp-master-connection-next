"""Physical proof and governed representation boundaries for Direct canonicalization."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.direct_frame import (
    direct_axial_frame_input,
    representation_residue_is_zero,
)
from frp_master_connection.application.multirow_orchestration import (
    _automatic_demand,
    _automatic_demand_input,
    _exact_template_group_axes,
    _execution_bundle,
    _resolve,
)
from frp_master_connection.calculation.eccentric_demand import (
    DEMAND_FRAME_TOLERANCE,
    calculate_eccentric_bolt_group_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    ForceVector3D,
)
from tests.application.test_direct_f1_safety import _request
from tests.direct_or2_fixtures import owner_request


@pytest.mark.parametrize(
    ("ratio", "expected"), [("0.999999", True), ("1", True), ("1.000001", False)]
)
def test_governed_representation_boundary_is_inclusive(ratio: str, expected: bool) -> None:
    scale = Decimal("3113")
    residual = scale * DEMAND_FRAME_TOLERANCE * Decimal(ratio)
    assert representation_residue_is_zero(residual, scale) is expected
    assert representation_residue_is_zero(-residual, scale) is expected


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "boundary-below",
        "boundary-at",
        "boundary-above",
        "entered-tiny",
        "entered-large",
        "frame",
        "zero",
        "axis-mismatch",
        "missing-equilibrium",
        "failed-equilibrium",
        "multiple-lines",
        "missing-scenarios",
    ],
)
def test_only_proven_physical_zero_is_canonicalized(case: str) -> None:
    request = _request(owner_request(si=True))
    resolved = _resolve(request)
    original = _automatic_demand_input(request, resolved, _execution_bundle(request, resolved))
    raw = calculate_eccentric_bolt_group_demand(original)
    action = resolved.authority.resolved_action
    physical = request.physical_connection_request
    assert action is not None
    assert physical is not None
    axes = _exact_template_group_axes(physical)
    assert axes is not None
    if case.startswith("boundary-"):
        ratio = {"boundary-below": "0.999999", "boundary-at": "1", "boundary-above": "1.000001"}[
            case
        ]
        residual = (
            raw.projected_force.u.canonical_magnitude * DEMAND_FRAME_TOLERANCE * Decimal(ratio)
        )
        raw = replace(
            raw,
            projected_force=replace(raw.projected_force, v=PhysicalQuantity.of(residual, Unit.N)),
        )
    if case.startswith("entered-"):
        force = ForceVector3D(action.action.force.fx, 1e-14 if case == "entered-tiny" else 1.0, 0.0)
        action = replace(action, action=replace(action.action, force=force))
    if case == "frame":
        action = replace(
            action,
            action=replace(
                action.action, coordinate_frame=CoordinateFrameReference(CoordinateFrameKind.GLOBAL)
            ),
        )
    if case == "zero":
        action = replace(action, action=replace(action.action, force=ForceVector3D(0.0, 0.0, 0.0)))
    if case == "axis-mismatch":
        original = replace(
            original,
            interface_frame=replace(
                original.interface_frame,
                u=axes[1],
                v=(-axes[0][0], -axes[0][1], -axes[0][2]),
            ),
        )
    if case in {"missing-equilibrium", "failed-equilibrium", "multiple-lines"}:
        scenario = raw.scenarios[0]
        equilibrium = scenario.equilibrium
        assert equilibrium is not None
        if case == "missing-equilibrium":
            scenario = replace(scenario, equilibrium=None)
        elif case == "failed-equilibrium":
            scenario = replace(scenario, equilibrium=replace(equilibrium, satisfied=False))
        else:
            scenario = replace(
                scenario,
                per_bolt=(
                    replace(scenario.per_bolt[0], centered_y=PhysicalQuantity.of("1", Unit.MM)),
                    *scenario.per_bolt[1:],
                ),
            )
        raw = replace(raw, scenarios=(scenario,))
    if case == "missing-scenarios":
        raw = replace(raw, scenarios=())
    candidate = direct_axial_frame_input(original, raw, action, axes, Unit.KN)
    accepted = case in {"valid", "boundary-below", "boundary-at"}
    assert (candidate is not None) is accepted
    if candidate is not None:
        canonical = calculate_eccentric_bolt_group_demand(candidate)
        assert canonical.projected_force.v.canonical_magnitude == 0
        trace = json.loads(canonical.source_trace[-1])
        assert trace["raw_projected_force_N"][1] == str(raw.projected_force.v.canonical_magnitude)
        assert trace["canonical_applicability_transverse_N"] == "0"
        assert trace["raw_line_transverse_N"]


def test_real_entered_transverse_action_remains_nonzero_and_blocked() -> None:
    from tests.api.test_mat1_routes import call

    payload = owner_request()
    payload["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["y"] = (
        "0.001"
    )
    preview = call("POST", "/api/v1/calculations/multi-row/preview", payload).json()
    assert preview["design_check_ready"] is False
    assert preview["automatic_demand_result"]["projected_force"]["v"]["canonical_value"] != "0"
    assert "DIRECT-AXIAL-FRAME-CANONICALIZATION-OR2-F1" not in str(preview)


def test_unavailable_semantic_template_axes_preserve_raw_demand() -> None:
    request = _request(owner_request())
    resolved = _resolve(request)
    bundle = _execution_bundle(request, resolved)
    physical = request.physical_connection_request
    assert physical is not None
    orientation = physical.template_orientation
    assert orientation is not None
    request = replace(
        request,
        physical_connection_request=replace(
            physical, template_orientation=replace(orientation, plan_angle_degrees=Decimal("1"))
        ),
    )
    raw = calculate_eccentric_bolt_group_demand(_automatic_demand_input(request, resolved, bundle))
    actual = _automatic_demand(request, resolved, bundle)
    assert actual == raw
    assert "DIRECT-AXIAL-FRAME-CANONICALIZATION-OR2-F1" not in str(actual.source_trace)
