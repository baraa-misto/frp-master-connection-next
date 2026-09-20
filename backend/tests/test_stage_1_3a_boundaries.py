"""Stage 1.3A boundary tests for intentionally deferred integration and calculation work."""

from dataclasses import fields

import frp_master_connection.calculation as calculation
from frp_master_connection.domain import (
    AssemblyMember,
    CoordinateFrameKind,
    CoordinateFrameReference,
    JointAssembly,
)
from frp_master_connection.geometry import GLOBAL_FRAME, CartesianFrame3D


def test_symbolic_frame_reference_remains_distinct_from_resolved_frame() -> None:
    symbolic = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)
    resolved = GLOBAL_FRAME

    assert isinstance(symbolic, CoordinateFrameReference)
    assert isinstance(resolved, CartesianFrame3D)
    assert not isinstance(symbolic, CartesianFrame3D)
    assert not isinstance(resolved, CoordinateFrameReference)


def test_joint_assembly_and_member_have_no_resolved_geometry_registry() -> None:
    deferred_fields = {
        "frame_registry",
        "resolved_frames",
        "geometry_registry",
        "start_position",
        "end_position",
        "placement",
    }

    assert {field.name for field in fields(JointAssembly)}.isdisjoint(deferred_fields)
    assert {field.name for field in fields(AssemblyMember)}.isdisjoint(deferred_fields)


def test_calculation_boundary_exposes_only_the_authorized_numerical_entry_points() -> None:
    numerical_entry_points = {name for name in calculation.__all__ if name.startswith("calculate_")}
    assert numerical_entry_points == {
        "calculate_channel_moment_component_resultants",
        "calculate_eccentric_bolt_group_demand",
        "calculate_eccentric_group_mode_compatibility",
        "calculate_eccentric_resistance_handoff",
        "calculate_multirow_connection",
        "calculate_single_bolt",
        "calculate_wi_moment_component_resultants",
    }
