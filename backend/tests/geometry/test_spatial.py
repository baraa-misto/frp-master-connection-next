"""Tests for finite vectors, Cartesian frames, and proper rigid transforms."""

import math
import sys
from dataclasses import FrozenInstanceError, fields
from typing import cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frp_master_connection.domain import ForceVector3D, MomentVector3D, PositionVector3D
from frp_master_connection.geometry import (
    DIMENSIONLESS_MATHEMATICAL_TOLERANCE,
    GLOBAL_FRAME,
    IDENTITY_ROTATION,
    CartesianFrame3D,
    FrameInspection3D,
    RigidTransform3D,
    Rotation3D,
    UnitVector3D,
    Vector3D,
    build_cartesian_frame,
    build_member_frame,
    inspect_cartesian_basis,
    transform_between_frames,
    translate_point,
    vector_between,
)


def _quarter_turn_z() -> Rotation3D:
    return Rotation3D(
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )


def _assert_vector_close(actual: Vector3D, expected: Vector3D) -> None:
    assert actual.x == pytest.approx(expected.x, abs=1.0e-10)
    assert actual.y == pytest.approx(expected.y, abs=1.0e-10)
    assert actual.z == pytest.approx(expected.z, abs=1.0e-10)


def _assert_point_close(actual: PositionVector3D, expected: PositionVector3D) -> None:
    assert actual.x == pytest.approx(expected.x, abs=1.0e-10)
    assert actual.y == pytest.approx(expected.y, abs=1.0e-10)
    assert actual.z == pytest.approx(expected.z, abs=1.0e-10)


def test_spatial_values_are_finite_immutable_and_semantically_distinct() -> None:
    point = PositionVector3D(1.0, 2.0, 3.0)
    vector = Vector3D(1.0, 2.0, 3.0)
    force = ForceVector3D(1.0, 2.0, 3.0)
    moment = MomentVector3D(1.0, 2.0, 3.0)

    assert type(point) is PositionVector3D
    assert type(vector) is Vector3D
    assert type(force) is ForceVector3D
    assert type(moment) is MomentVector3D
    assert len({type(point), type(vector), type(force), type(moment)}) == 4
    with pytest.raises(FrozenInstanceError):
        vector.x = 4.0  # type: ignore[misc]


def test_resolved_spatial_contracts_are_immutable() -> None:
    unit = UnitVector3D(1.0, 0.0, 0.0)
    rotation = IDENTITY_ROTATION
    transform = RigidTransform3D(rotation, Vector3D(0.0, 0.0, 0.0))
    inspection = GLOBAL_FRAME.inspect()

    with pytest.raises(FrozenInstanceError):
        unit.x = 2.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        rotation.x_axis = GLOBAL_FRAME.y_axis  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        transform.translation = Vector3D(1.0, 0.0, 0.0)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        inspection.origin = PositionVector3D(1.0, 0.0, 0.0)  # type: ignore[misc]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_vector_rejects_nonfinite_components(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        Vector3D(value, 0.0, 0.0)


@pytest.mark.parametrize("value", [True, "1"])
def test_vector_rejects_nonreal_components(value: object) -> None:
    with pytest.raises(TypeError, match="real number"):
        Vector3D(value, 0.0, 0.0)  # type: ignore[arg-type]


def test_vector_arithmetic_dot_cross_norm_and_normalization() -> None:
    first = Vector3D(1.0, 2.0, 3.0)
    second = Vector3D(-2.0, 4.0, 1.0)
    x_axis = Vector3D(1.0, 0.0, 0.0)
    y_axis = Vector3D(0.0, 1.0, 0.0)
    z_axis = Vector3D(0.0, 0.0, 1.0)

    assert first + second == Vector3D(-1.0, 6.0, 4.0)
    assert first - second == Vector3D(3.0, -2.0, 2.0)
    assert -first == Vector3D(-1.0, -2.0, -3.0)
    assert first * 2.0 == Vector3D(2.0, 4.0, 6.0)
    assert 2.0 * first == Vector3D(2.0, 4.0, 6.0)
    assert first.dot(second) == pytest.approx(9.0)
    assert x_axis.cross(y_axis) == z_axis
    assert y_axis.cross(x_axis) == -z_axis
    assert x_axis.cross(y_axis).dot(x_axis) == pytest.approx(0.0)
    assert x_axis.cross(y_axis).dot(y_axis) == pytest.approx(0.0)
    assert first.norm == pytest.approx(math.sqrt(14.0))
    assert first.normalized().norm == pytest.approx(1.0)


def test_vector_operations_fail_loudly_on_unrepresentable_scalar_results() -> None:
    maximum = sys.float_info.max

    with pytest.raises(ValueError, match="dot product"):
        Vector3D(maximum, 0.0, 0.0).dot(Vector3D(maximum, 0.0, 0.0))
    with pytest.raises(ValueError, match="norm"):
        _ = Vector3D(maximum, maximum, maximum).norm

    assert Vector3D(maximum, maximum, maximum).normalized().norm == pytest.approx(1.0)


@settings(database=None, derandomize=True, max_examples=50)
@given(
    ax=st.integers(min_value=-100, max_value=100),
    ay=st.integers(min_value=-100, max_value=100),
    az=st.integers(min_value=-100, max_value=100),
    bx=st.integers(min_value=-100, max_value=100),
    by=st.integers(min_value=-100, max_value=100),
    bz=st.integers(min_value=-100, max_value=100),
)
def test_cross_product_algebraic_invariants(
    ax: int,
    ay: int,
    az: int,
    bx: int,
    by: int,
    bz: int,
) -> None:
    left = Vector3D(float(ax), float(ay), float(az))
    right = Vector3D(float(bx), float(by), float(bz))
    cross = left.cross(right)

    assert cross == -right.cross(left)
    assert cross.dot(left) == pytest.approx(0.0)
    assert cross.dot(right) == pytest.approx(0.0)


@pytest.mark.parametrize("operation", ["add", "subtract", "dot", "cross"])
def test_vector_binary_operations_reject_nonvectors(operation: str) -> None:
    vector = Vector3D(1.0, 0.0, 0.0)
    with pytest.raises(TypeError, match="Vector3D"):
        _apply_invalid_vector_operation(vector, operation)


def _apply_invalid_vector_operation(vector: Vector3D, operation: str) -> object:
    if operation == "add":
        return vector + "bad"  # type: ignore[operator]
    if operation == "subtract":
        return vector - "bad"  # type: ignore[operator]
    if operation == "dot":
        return vector.dot("bad")  # type: ignore[arg-type]
    return vector.cross("bad")  # type: ignore[arg-type]


@pytest.mark.parametrize("scalar", [True, math.inf, "2"])
def test_vector_scalar_multiplication_rejects_invalid_scalars(scalar: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        Vector3D(1.0, 0.0, 0.0) * scalar  # type: ignore[operator]


def test_zero_normalization_and_nonunit_construction_are_rejected() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        Vector3D(0.0, 0.0, 0.0).normalized()
    with pytest.raises(ValueError, match="unit length"):
        UnitVector3D(2.0, 0.0, 0.0)
    assert -UnitVector3D(1.0, 0.0, 0.0) == UnitVector3D(-1.0, 0.0, 0.0)


def test_point_vector_helpers_preserve_semantic_types() -> None:
    start = PositionVector3D(1.0, 2.0, 3.0)
    end = PositionVector3D(4.0, 6.0, 8.0)
    displacement = vector_between(start, end)

    assert displacement == Vector3D(3.0, 4.0, 5.0)
    assert translate_point(start, displacement) == end
    with pytest.raises(TypeError, match="start"):
        vector_between("start", end)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="end"):
        vector_between(start, "end")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="point"):
        translate_point("point", displacement)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="offset"):
        translate_point(start, "offset")  # type: ignore[arg-type]


def test_global_frame_is_exact_right_handed_orthonormal_and_immutable() -> None:
    inspection = GLOBAL_FRAME.inspect()

    assert DIMENSIONLESS_MATHEMATICAL_TOLERANCE == 1.0e-12
    assert GLOBAL_FRAME.origin == PositionVector3D(0.0, 0.0, 0.0)
    assert GLOBAL_FRAME.x_axis == UnitVector3D(1.0, 0.0, 0.0)
    assert GLOBAL_FRAME.y_axis == UnitVector3D(0.0, 1.0, 0.0)
    assert GLOBAL_FRAME.z_axis == UnitVector3D(0.0, 0.0, 1.0)
    assert GLOBAL_FRAME.rotation == IDENTITY_ROTATION
    assert inspection.x_norm == inspection.y_norm == inspection.z_norm == pytest.approx(1.0)
    assert inspection.xy_dot == inspection.xz_dot == inspection.yz_dot == pytest.approx(0.0)
    assert inspection.determinant == pytest.approx(1.0)
    assert inspection.right_handed
    assert inspection.orthonormal
    assert inspection.valid
    with pytest.raises(FrozenInstanceError):
        GLOBAL_FRAME.origin = PositionVector3D(1.0, 0.0, 0.0)  # type: ignore[misc]


def test_global_frame_point_and_vector_transformations_are_identity() -> None:
    point = PositionVector3D(2.0, -3.0, 4.0)
    vector = Vector3D(-5.0, 6.0, 7.0)

    assert GLOBAL_FRAME.local_to_parent_point(point) == point
    assert GLOBAL_FRAME.parent_to_local_point(point) == point
    assert GLOBAL_FRAME.local_to_parent_vector(vector) == vector
    assert GLOBAL_FRAME.parent_to_local_vector(vector) == vector


def test_raw_basis_inspection_reports_reflection_scaling_and_skew_without_valid_frame() -> None:
    origin = PositionVector3D(0.0, 0.0, 0.0)
    reflected = inspect_cartesian_basis(
        origin,
        Vector3D(1.0, 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        Vector3D(0.0, 0.0, -1.0),
    )
    scaled = inspect_cartesian_basis(
        origin,
        Vector3D(2.0, 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )
    skewed = inspect_cartesian_basis(
        origin,
        Vector3D(1.0, 0.0, 0.0),
        Vector3D(1.0, 1.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )

    assert reflected.orthonormal
    assert not reflected.right_handed
    assert not reflected.valid
    assert not scaled.orthonormal
    assert not scaled.valid
    assert not skewed.orthonormal
    assert not skewed.valid
    derived_field_names = {field.name for field in fields(FrameInspection3D) if not field.init}
    assert derived_field_names == {
        "x_norm",
        "y_norm",
        "z_norm",
        "xy_dot",
        "xz_dot",
        "yz_dot",
        "determinant",
        "right_handed",
        "orthonormal",
    }


def test_frame_inspection_cannot_be_constructed_with_an_invalid_origin() -> None:
    with pytest.raises(TypeError, match="origin"):
        FrameInspection3D(
            cast(PositionVector3D, "origin"),
            Vector3D(1.0, 0.0, 0.0),
            Vector3D(0.0, 1.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )


@pytest.mark.parametrize("field", ["origin", "x", "y", "z"])
def test_basis_inspection_rejects_invalid_types(field: str) -> None:
    origin: object = PositionVector3D(0.0, 0.0, 0.0)
    x_axis: object = Vector3D(1.0, 0.0, 0.0)
    y_axis: object = Vector3D(0.0, 1.0, 0.0)
    z_axis: object = Vector3D(0.0, 0.0, 1.0)
    if field == "origin":
        origin = "bad"
    elif field == "x":
        x_axis = "bad"
    elif field == "y":
        y_axis = "bad"
    else:
        z_axis = "bad"
    with pytest.raises(TypeError):
        inspect_cartesian_basis(origin, x_axis, y_axis, z_axis)  # type: ignore[arg-type]


def test_rotation_rejects_reflected_skewed_scaled_and_untyped_bases() -> None:
    x_axis = UnitVector3D(1.0, 0.0, 0.0)
    y_axis = UnitVector3D(0.0, 1.0, 0.0)
    z_axis = UnitVector3D(0.0, 0.0, 1.0)
    with pytest.raises(ValueError, match="right-handed"):
        Rotation3D(x_axis, y_axis, -z_axis)
    with pytest.raises(ValueError, match="orthonormal"):
        Rotation3D(
            x_axis,
            UnitVector3D(math.sqrt(0.5), math.sqrt(0.5), 0.0),
            z_axis,
        )
    with pytest.raises(ValueError, match="unit length"):
        UnitVector3D(1.5, 0.0, 0.0)
    with pytest.raises(TypeError, match="UnitVector3D"):
        Rotation3D(Vector3D(1.0, 0.0, 0.0), y_axis, z_axis)  # type: ignore[arg-type]


def test_member_frame_standard_orientation_and_explicit_projection() -> None:
    start = PositionVector3D(2.0, 3.0, 4.0)
    end = PositionVector3D(12.0, 3.0, 4.0)
    frame = build_member_frame(start, end, Vector3D(4.0, 0.0, 3.0))

    assert frame.origin == start
    assert frame.x_axis == UnitVector3D(1.0, 0.0, 0.0)
    assert frame.y_axis == UnitVector3D(0.0, 1.0, 0.0)
    assert frame.z_axis == UnitVector3D(0.0, 0.0, 1.0)
    assert frame.x_axis.cross(frame.y_axis).normalized() == frame.z_axis


def test_arbitrarily_rotated_member_frame_is_right_handed_and_follows_start_to_end() -> None:
    start = PositionVector3D(1.0, -2.0, 3.0)
    end = PositionVector3D(4.0, 2.0, 8.0)
    frame = build_member_frame(start, end, Vector3D(0.0, 0.0, 1.0))

    expected_x = vector_between(start, end).normalized()
    assert frame.x_axis == expected_x
    assert frame.origin == start
    assert frame.inspect().valid
    assert frame.x_axis.dot(frame.z_axis) == pytest.approx(
        0.0, abs=DIMENSIONLESS_MATHEMATICAL_TOLERANCE
    )


@pytest.mark.parametrize(
    ("start", "end", "reference", "message"),
    [
        (
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(0.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
            "zero vector",
        ),
        (
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 0.0),
            "zero vector",
        ),
        (
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(1.0, 0.0, 0.0),
            "parallel",
        ),
        (
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(-1.0, 0.0, 0.0),
            "parallel",
        ),
        (
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(1.0, 0.0, 5.0e-13),
            "nearly parallel",
        ),
    ],
)
def test_member_frame_rejects_degenerate_inputs_without_fallback(
    start: PositionVector3D,
    end: PositionVector3D,
    reference: Vector3D,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_member_frame(start, end, reference)


@pytest.mark.parametrize("reference_scale", [1.0e-200, 1.0, 1.0e200])
def test_near_parallel_rejection_is_dimensionless_and_scale_invariant(
    reference_scale: float,
) -> None:
    reference = Vector3D(
        reference_scale,
        0.0,
        reference_scale * 5.0e-13,
    )

    with pytest.raises(ValueError, match="nearly parallel"):
        build_member_frame(
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(1.0, 0.0, 0.0),
            reference,
        )


def test_nonzero_member_direction_has_no_hidden_dimensionful_tolerance() -> None:
    frame = build_member_frame(
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(1.0e-300, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )

    assert frame.x_axis == UnitVector3D(1.0, 0.0, 0.0)


@pytest.mark.parametrize("field", ["origin", "x", "z"])
def test_frame_builder_rejects_invalid_types(field: str) -> None:
    origin: object = PositionVector3D(0.0, 0.0, 0.0)
    x_direction: object = Vector3D(1.0, 0.0, 0.0)
    z_reference: object = Vector3D(0.0, 0.0, 1.0)
    if field == "origin":
        origin = "bad"
    elif field == "x":
        x_direction = "bad"
    else:
        z_reference = "bad"
    with pytest.raises(TypeError):
        build_cartesian_frame(origin, x_direction, z_reference)  # type: ignore[arg-type]


def test_frame_and_rigid_transform_point_vector_round_trips() -> None:
    frame = CartesianFrame3D(
        PositionVector3D(10.0, 20.0, 30.0),
        _quarter_turn_z().x_axis,
        _quarter_turn_z().y_axis,
        _quarter_turn_z().z_axis,
    )
    local_point = PositionVector3D(1.0, 2.0, 3.0)
    local_vector = Vector3D(1.0, 2.0, 3.0)

    parent_point = frame.local_to_parent_point(local_point)
    parent_vector = frame.local_to_parent_vector(local_vector)
    assert parent_point == PositionVector3D(8.0, 21.0, 33.0)
    assert parent_vector == Vector3D(-2.0, 1.0, 3.0)
    assert frame.parent_to_local_point(parent_point) == local_point
    assert frame.parent_to_local_vector(parent_vector) == local_vector
    assert frame.transform.inverse().apply_point(parent_point) == local_point
    assert frame.transform.inverse().apply_vector(parent_vector) == local_vector


def test_translation_affects_points_but_not_vectors() -> None:
    transform = RigidTransform3D(IDENTITY_ROTATION, Vector3D(5.0, 6.0, 7.0))
    point = PositionVector3D(1.0, 2.0, 3.0)
    vector = Vector3D(1.0, 2.0, 3.0)

    assert transform.apply_point(point) == PositionVector3D(6.0, 8.0, 10.0)
    assert transform.apply_vector(vector) == vector


def test_transform_composition_order_and_rotation_composition_are_explicit() -> None:
    translate_x = RigidTransform3D(IDENTITY_ROTATION, Vector3D(1.0, 0.0, 0.0))
    rotate_z = RigidTransform3D(_quarter_turn_z(), Vector3D(0.0, 0.0, 0.0))
    point = PositionVector3D(1.0, 0.0, 0.0)

    composed = translate_x.then(rotate_z)
    assert composed.apply_point(point) == PositionVector3D(0.0, 2.0, 0.0)
    assert rotate_z.then(translate_x).apply_point(point) == PositionVector3D(1.0, 1.0, 0.0)
    assert IDENTITY_ROTATION.then(_quarter_turn_z()) == _quarter_turn_z()
    assert _quarter_turn_z().then(_quarter_turn_z().inverse()) == IDENTITY_ROTATION


def test_transform_between_frames_maps_source_coordinates_to_target_coordinates() -> None:
    source = CartesianFrame3D(
        PositionVector3D(10.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )
    target = CartesianFrame3D(
        PositionVector3D(4.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )

    transform = transform_between_frames(source, target)
    assert transform.apply_point(PositionVector3D(1.0, 0.0, 0.0)) == PositionVector3D(7.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: CartesianFrame3D(
            cast(PositionVector3D, "origin"),
            GLOBAL_FRAME.x_axis,
            GLOBAL_FRAME.y_axis,
            GLOBAL_FRAME.z_axis,
        ),
        lambda: RigidTransform3D(cast(Rotation3D, "rotation"), Vector3D(0.0, 0.0, 0.0)),
        lambda: RigidTransform3D(IDENTITY_ROTATION, cast(Vector3D, "translation")),
        lambda: RigidTransform3D(IDENTITY_ROTATION, Vector3D(0.0, 0.0, 0.0)).apply_point(
            cast(PositionVector3D, "point")
        ),
        lambda: IDENTITY_ROTATION.apply(cast(Vector3D, "vector")),
        lambda: IDENTITY_ROTATION.apply_inverse(cast(Vector3D, "vector")),
        lambda: IDENTITY_ROTATION.then(cast(Rotation3D, "rotation")),
        lambda: RigidTransform3D(IDENTITY_ROTATION, Vector3D(0.0, 0.0, 0.0)).then(
            cast(RigidTransform3D, "transform")
        ),
        lambda: transform_between_frames(cast(CartesianFrame3D, "source"), GLOBAL_FRAME),
        lambda: transform_between_frames(GLOBAL_FRAME, cast(CartesianFrame3D, "target")),
    ],
)
def test_frame_and_transform_operations_reject_invalid_types(factory: object) -> None:
    with pytest.raises(TypeError):
        factory()  # type: ignore[operator]


@settings(database=None, derandomize=True, max_examples=40)
@given(
    x=st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
    y=st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
    z=st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
)
def test_rigid_transform_round_trip_property(x: float, y: float, z: float) -> None:
    transform = RigidTransform3D(_quarter_turn_z(), Vector3D(13.0, -7.0, 2.0))
    point = PositionVector3D(x, y, z)
    vector = Vector3D(x, y, z)

    _assert_point_close(transform.inverse().apply_point(transform.apply_point(point)), point)
    _assert_vector_close(transform.inverse().apply_vector(transform.apply_vector(vector)), vector)
