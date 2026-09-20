"""Tests for action rotation, reference shifts, signs, and display directions."""

import math
from dataclasses import FrozenInstanceError, fields
from typing import cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frp_master_connection.actions import (
    ActionComponent,
    ActionDirectionKind,
    ActionValueSense,
    AppliedActionDirection3D,
    AxialLoadingSense,
    ForceMomentSystem3D,
    PointInFrame3D,
    PositiveActionDirection3D,
    applied_action_direction,
    interpret_member_end_axial_sense,
    positive_action_direction,
    rotate_force,
    rotate_moment,
    shift_force_moment_reference,
)
from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    ForceVector3D,
    MemberEnd,
    MomentVector3D,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    CartesianFrame3D,
    Rotation3D,
    UnitVector3D,
    Vector3D,
    build_member_frame,
)
from tests.domain.factories import make_wide_flange_topology

GLOBAL_REFERENCE = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)


def _point(x: float, y: float, z: float) -> PointInFrame3D:
    return PointInFrame3D(GLOBAL_REFERENCE, PositionVector3D(x, y, z))


def _quarter_turn_z() -> Rotation3D:
    return Rotation3D(
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )


def test_action_vocabularies_are_exact() -> None:
    assert tuple(AxialLoadingSense) == (
        AxialLoadingSense.TENSION,
        AxialLoadingSense.COMPRESSION,
        AxialLoadingSense.ZERO,
    )
    assert tuple(ActionComponent) == (
        ActionComponent.FX,
        ActionComponent.FY,
        ActionComponent.FZ,
        ActionComponent.MX,
        ActionComponent.MY,
        ActionComponent.MZ,
    )
    assert tuple(ActionDirectionKind) == (
        ActionDirectionKind.LINEAR,
        ActionDirectionKind.ROTATIONAL,
    )


def test_force_and_moment_rotate_consistently_without_translation() -> None:
    force = rotate_force(ForceVector3D(1.0, 2.0, 3.0), _quarter_turn_z())
    moment = rotate_moment(MomentVector3D(1.0, 2.0, 3.0), _quarter_turn_z())

    assert force == ForceVector3D(-2.0, 1.0, 3.0)
    assert moment == MomentVector3D(-2.0, 1.0, 3.0)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: rotate_force(cast(ForceVector3D, "force"), _quarter_turn_z()),
        lambda: rotate_force(ForceVector3D(1.0, 0.0, 0.0), cast(Rotation3D, "rotation")),
        lambda: rotate_moment(cast(MomentVector3D, "moment"), _quarter_turn_z()),
        lambda: rotate_moment(MomentVector3D(1.0, 0.0, 0.0), cast(Rotation3D, "rotation")),
    ],
)
def test_force_and_moment_rotation_reject_invalid_types(operation: object) -> None:
    with pytest.raises(TypeError):
        operation()  # type: ignore[operator]


def test_reference_shift_canonical_positive_and_negative_eccentricity_examples() -> None:
    positive = ForceMomentSystem3D(
        _point(2.0, 0.0, 0.0),
        ForceVector3D(0.0, 3.0, 0.0),
        MomentVector3D(0.0, 0.0, 0.0),
    )
    negative = ForceMomentSystem3D(
        _point(-2.0, 0.0, 0.0),
        ForceVector3D(0.0, 3.0, 0.0),
        MomentVector3D(0.0, 0.0, 0.0),
    )

    positive_at_origin = shift_force_moment_reference(positive, _point(0.0, 0.0, 0.0))
    negative_at_origin = shift_force_moment_reference(negative, _point(0.0, 0.0, 0.0))
    assert positive_at_origin.force is positive.force
    assert positive_at_origin.moment == MomentVector3D(0.0, 0.0, 6.0)
    assert negative_at_origin.moment == MomentVector3D(0.0, 0.0, -6.0)


def test_reference_shift_nonzero_moment_round_trip_recovers_original_system() -> None:
    original = ForceMomentSystem3D(
        _point(3.0, -2.0, 1.0),
        ForceVector3D(4.0, 5.0, -6.0),
        MomentVector3D(7.0, -8.0, 9.0),
    )
    target = _point(-4.0, 1.0, 2.0)

    shifted = shift_force_moment_reference(original, target)
    recovered = shift_force_moment_reference(shifted, original.reference_point)
    assert recovered == original


@settings(database=None, derandomize=True, max_examples=50)
@given(
    px=st.integers(min_value=-100, max_value=100),
    py=st.integers(min_value=-100, max_value=100),
    pz=st.integers(min_value=-100, max_value=100),
    qx=st.integers(min_value=-100, max_value=100),
    qy=st.integers(min_value=-100, max_value=100),
    qz=st.integers(min_value=-100, max_value=100),
    fx=st.integers(min_value=-100, max_value=100),
    fy=st.integers(min_value=-100, max_value=100),
    fz=st.integers(min_value=-100, max_value=100),
    mx=st.integers(min_value=-100, max_value=100),
    my=st.integers(min_value=-100, max_value=100),
    mz=st.integers(min_value=-100, max_value=100),
)
def test_reference_shift_round_trip_property(
    px: int,
    py: int,
    pz: int,
    qx: int,
    qy: int,
    qz: int,
    fx: int,
    fy: int,
    fz: int,
    mx: int,
    my: int,
    mz: int,
) -> None:
    original = ForceMomentSystem3D(
        _point(float(px), float(py), float(pz)),
        ForceVector3D(float(fx), float(fy), float(fz)),
        MomentVector3D(float(mx), float(my), float(mz)),
    )
    target = _point(float(qx), float(qy), float(qz))

    shifted = shift_force_moment_reference(original, target)
    assert shift_force_moment_reference(shifted, original.reference_point) == original


def test_reference_shift_enforces_one_identified_common_frame() -> None:
    system = ForceMomentSystem3D(
        _point(1.0, 0.0, 0.0),
        ForceVector3D(0.0, 1.0, 0.0),
        MomentVector3D(0.0, 0.0, 0.0),
    )
    member_point = PointInFrame3D(
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
        PositionVector3D(0.0, 0.0, 0.0),
    )

    with pytest.raises(ValueError, match="common frame"):
        shift_force_moment_reference(system, member_point)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PointInFrame3D(
            cast(CoordinateFrameReference, "frame"),
            PositionVector3D(0.0, 0.0, 0.0),
        ),
        lambda: PointInFrame3D(GLOBAL_REFERENCE, cast(PositionVector3D, "point")),
        lambda: ForceMomentSystem3D(
            cast(PointInFrame3D, "point"),
            ForceVector3D(0.0, 0.0, 0.0),
            MomentVector3D(0.0, 0.0, 0.0),
        ),
        lambda: ForceMomentSystem3D(
            _point(0.0, 0.0, 0.0),
            cast(ForceVector3D, "force"),
            MomentVector3D(0.0, 0.0, 0.0),
        ),
        lambda: ForceMomentSystem3D(
            _point(0.0, 0.0, 0.0),
            ForceVector3D(0.0, 0.0, 0.0),
            cast(MomentVector3D, "moment"),
        ),
        lambda: shift_force_moment_reference(
            cast(ForceMomentSystem3D, "system"), _point(0.0, 0.0, 0.0)
        ),
        lambda: shift_force_moment_reference(
            ForceMomentSystem3D(
                _point(0.0, 0.0, 0.0),
                ForceVector3D(0.0, 0.0, 0.0),
                MomentVector3D(0.0, 0.0, 0.0),
            ),
            cast(PointInFrame3D, "target"),
        ),
    ],
)
def test_reference_shift_contracts_reject_invalid_types(factory: object) -> None:
    with pytest.raises(TypeError):
        factory()  # type: ignore[operator]


@pytest.mark.parametrize(
    ("member_end", "fx", "expected"),
    [
        (MemberEnd.START, 10.0, AxialLoadingSense.TENSION),
        (MemberEnd.START, -10.0, AxialLoadingSense.COMPRESSION),
        (MemberEnd.END, -10.0, AxialLoadingSense.TENSION),
        (MemberEnd.END, 10.0, AxialLoadingSense.COMPRESSION),
        (MemberEnd.START, 0.0, AxialLoadingSense.ZERO),
        (MemberEnd.END, -0.0, AxialLoadingSense.ZERO),
    ],
)
def test_connected_end_axial_sense_preserves_stored_sign(
    member_end: MemberEnd,
    fx: float,
    expected: AxialLoadingSense,
) -> None:
    stored_fx = fx
    assert interpret_member_end_axial_sense(member_end, fx) is expected
    assert fx == stored_fx


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_axial_sense_rejects_invalid_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        interpret_member_end_axial_sense(MemberEnd.START, value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="MemberEnd"):
        interpret_member_end_axial_sense("START", 1.0)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("component", "kind", "axis"),
    [
        (ActionComponent.FX, ActionDirectionKind.LINEAR, GLOBAL_FRAME.x_axis),
        (ActionComponent.FY, ActionDirectionKind.LINEAR, GLOBAL_FRAME.y_axis),
        (ActionComponent.FZ, ActionDirectionKind.LINEAR, GLOBAL_FRAME.z_axis),
        (ActionComponent.MX, ActionDirectionKind.ROTATIONAL, GLOBAL_FRAME.x_axis),
        (ActionComponent.MY, ActionDirectionKind.ROTATIONAL, GLOBAL_FRAME.y_axis),
        (ActionComponent.MZ, ActionDirectionKind.ROTATIONAL, GLOBAL_FRAME.z_axis),
    ],
)
def test_positive_action_components_map_to_frame_axes_and_right_hand_rotation(
    component: ActionComponent,
    kind: ActionDirectionKind,
    axis: UnitVector3D,
) -> None:
    direction = positive_action_direction(component, GLOBAL_FRAME)
    assert direction == PositiveActionDirection3D(component, kind, axis)


@pytest.mark.parametrize(
    ("component", "value", "kind"),
    [
        (ActionComponent.FX, 4.0, ActionDirectionKind.LINEAR),
        (ActionComponent.FY, -4.0, ActionDirectionKind.LINEAR),
        (ActionComponent.FZ, 0.0, ActionDirectionKind.LINEAR),
        (ActionComponent.MX, 4.0, ActionDirectionKind.ROTATIONAL),
        (ActionComponent.MY, -4.0, ActionDirectionKind.ROTATIONAL),
        (ActionComponent.MZ, 0.0, ActionDirectionKind.ROTATIONAL),
    ],
)
def test_applied_action_directions_preserve_value_sign_kind_and_zero(
    component: ActionComponent,
    value: float,
    kind: ActionDirectionKind,
) -> None:
    direction = applied_action_direction(component, value, GLOBAL_FRAME)
    positive_axis = positive_action_direction(component, GLOBAL_FRAME).axis
    assert direction.signed_value == value
    assert direction.kind is kind
    if value > 0.0:
        assert direction.axis == positive_axis
        assert direction.sense is ActionValueSense.POSITIVE
        assert not direction.is_zero
    elif value < 0.0:
        assert direction.axis == -positive_axis
        assert direction.sense is ActionValueSense.NEGATIVE
        assert not direction.is_zero
    else:
        assert direction.axis == positive_axis
        assert direction.sense is ActionValueSense.ZERO
        assert direction.is_zero


def test_action_direction_changes_with_resolved_frame_rotation() -> None:
    rotated_frame = CartesianFrame3D(
        PositionVector3D(5.0, 6.0, 7.0),
        _quarter_turn_z().x_axis,
        _quarter_turn_z().y_axis,
        _quarter_turn_z().z_axis,
    )

    assert positive_action_direction(ActionComponent.FX, rotated_frame).axis == UnitVector3D(
        0.0, 1.0, 0.0
    )
    assert applied_action_direction(ActionComponent.MY, -2.0, rotated_frame).axis == UnitVector3D(
        1.0, 0.0, 0.0
    )


def test_applied_direction_preserves_negative_zero_as_explicit_zero() -> None:
    direction = applied_action_direction(ActionComponent.FX, -0.0, GLOBAL_FRAME)

    assert math.copysign(1.0, direction.signed_value) == -1.0
    assert direction.sense is ActionValueSense.ZERO
    assert direction.is_zero
    with pytest.raises(FrozenInstanceError):
        direction.signed_value = 1.0  # type: ignore[misc]


def test_direction_contract_contains_no_renderer_style_or_reference_point() -> None:
    names = {field.name for field in fields(AppliedActionDirection3D)}
    assert names == {"component", "kind", "signed_value", "axis", "sense", "is_zero"}
    assert names.isdisjoint(
        {"pixel_length", "color", "screen_coordinate", "mesh", "camera", "display_scale"}
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: positive_action_direction(cast(ActionComponent, "FX"), GLOBAL_FRAME),
        lambda: positive_action_direction(ActionComponent.FX, cast(CartesianFrame3D, "frame")),
        lambda: PositiveActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.ROTATIONAL,
            GLOBAL_FRAME.x_axis,
        ),
        lambda: PositiveActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.LINEAR,
            cast(UnitVector3D, Vector3D(1.0, 0.0, 0.0)),
        ),
        lambda: AppliedActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.ROTATIONAL,
            1.0,
            GLOBAL_FRAME.x_axis,
            ActionValueSense.POSITIVE,
            False,
        ),
        lambda: AppliedActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.LINEAR,
            1.0,
            cast(UnitVector3D, Vector3D(1.0, 0.0, 0.0)),
            ActionValueSense.POSITIVE,
            False,
        ),
        lambda: AppliedActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.LINEAR,
            1.0,
            GLOBAL_FRAME.x_axis,
            cast(ActionValueSense, "POSITIVE"),
            False,
        ),
        lambda: AppliedActionDirection3D(
            ActionComponent.FX,
            ActionDirectionKind.LINEAR,
            -1.0,
            GLOBAL_FRAME.x_axis,
            ActionValueSense.POSITIVE,
            False,
        ),
    ],
)
def test_action_direction_contracts_reject_inconsistent_construction(factory: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()  # type: ignore[operator]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_applied_direction_rejects_invalid_signed_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        applied_action_direction(ActionComponent.FX, value, GLOBAL_FRAME)  # type: ignore[arg-type]


def test_wide_flange_geometric_axes_match_stage_1_2_material_families() -> None:
    frame = build_member_frame(
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(10.0, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )
    topology = make_wide_flange_topology()
    web = topology.material_regions[0].orientation
    flanges = topology.material_regions[1].orientation

    assert frame.x_axis == UnitVector3D(1.0, 0.0, 0.0)
    assert frame.y_axis == UnitVector3D(0.0, 1.0, 0.0)
    assert frame.z_axis == UnitVector3D(0.0, 0.0, 1.0)
    assert isinstance(web, PlanarFixedMaterialOrientation)
    assert isinstance(flanges, PlanarFixedMaterialOrientation)
    assert (web.crosswise_axis, web.through_thickness_axis) == (
        PrincipalAxisFamily.Z,
        PrincipalAxisFamily.Y,
    )
    assert (flanges.crosswise_axis, flanges.through_thickness_axis) == (
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )
