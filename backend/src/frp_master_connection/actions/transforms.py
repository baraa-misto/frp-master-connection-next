"""Framework-independent action transformations and renderer-neutral directions."""

import math
from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.domain.values import (
    CoordinateFrameReference,
    ForceVector3D,
    MemberEnd,
    MomentVector3D,
    PositionVector3D,
)
from frp_master_connection.geometry import (
    CartesianFrame3D,
    Rotation3D,
    UnitVector3D,
    Vector3D,
    vector_between,
)


class AxialLoadingSense(StrEnum):
    """Connected-end axial interpretation for member-on-joint actions."""

    TENSION = "TENSION"
    COMPRESSION = "COMPRESSION"
    ZERO = "ZERO"


class ActionComponent(StrEnum):
    """Exactly the six canonical action components."""

    FX = "FX"
    FY = "FY"
    FZ = "FZ"
    MX = "MX"
    MY = "MY"
    MZ = "MZ"


class ActionDirectionKind(StrEnum):
    """Renderer-neutral linear or right-hand rotational direction kind."""

    LINEAR = "LINEAR"
    ROTATIONAL = "ROTATIONAL"


class ActionValueSense(StrEnum):
    """Sign sense retained separately from the authoritative signed value."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ZERO = "ZERO"


def _require_finite_value(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


def _component_kind(component: ActionComponent) -> ActionDirectionKind:
    if not isinstance(component, ActionComponent):
        raise TypeError("component must be an ActionComponent.")
    if component in {ActionComponent.FX, ActionComponent.FY, ActionComponent.FZ}:
        return ActionDirectionKind.LINEAR
    return ActionDirectionKind.ROTATIONAL


def _component_axis(
    component: ActionComponent,
    frame: CartesianFrame3D,
) -> UnitVector3D:
    if not isinstance(frame, CartesianFrame3D):
        raise TypeError("frame must be a CartesianFrame3D.")
    if component in {ActionComponent.FX, ActionComponent.MX}:
        return frame.x_axis
    if component in {ActionComponent.FY, ActionComponent.MY}:
        return frame.y_axis
    return frame.z_axis


@dataclass(frozen=True, slots=True)
class PositiveActionDirection3D:
    """Permanent positive component direction expressed in frame-parent coordinates."""

    component: ActionComponent
    kind: ActionDirectionKind
    axis: UnitVector3D

    def __post_init__(self) -> None:
        expected_kind = _component_kind(self.component)
        if self.kind is not expected_kind:
            raise ValueError("Positive action direction kind must match its component.")
        if not isinstance(self.axis, UnitVector3D):
            raise TypeError("PositiveActionDirection3D.axis must be a UnitVector3D.")


@dataclass(frozen=True, slots=True)
class AppliedActionDirection3D:
    """Signed renderer-neutral action direction with no display styling."""

    component: ActionComponent
    kind: ActionDirectionKind
    signed_value: float
    axis: UnitVector3D
    sense: ActionValueSense
    is_zero: bool

    def __post_init__(self) -> None:
        expected_kind = _component_kind(self.component)
        if self.kind is not expected_kind:
            raise ValueError("Applied action direction kind must match its component.")
        _require_finite_value(self.signed_value, "AppliedActionDirection3D.signed_value")
        if not isinstance(self.axis, UnitVector3D):
            raise TypeError("AppliedActionDirection3D.axis must be a UnitVector3D.")
        if not isinstance(self.sense, ActionValueSense):
            raise TypeError("AppliedActionDirection3D.sense must be an ActionValueSense.")
        expected_sense = (
            ActionValueSense.ZERO
            if self.signed_value == 0.0
            else ActionValueSense.POSITIVE
            if self.signed_value > 0.0
            else ActionValueSense.NEGATIVE
        )
        if self.sense is not expected_sense or self.is_zero is not (
            expected_sense is ActionValueSense.ZERO
        ):
            raise ValueError("Applied action sign, sense, and zero status must agree.")


@dataclass(frozen=True, slots=True)
class PointInFrame3D:
    """An existing finite position explicitly associated with one symbolic frame."""

    coordinate_frame: CoordinateFrameReference
    position: PositionVector3D

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate_frame, CoordinateFrameReference):
            raise TypeError("PointInFrame3D.coordinate_frame must be a frame reference.")
        if not isinstance(self.position, PositionVector3D):
            raise TypeError("PointInFrame3D.position must be a PositionVector3D.")


@dataclass(frozen=True, slots=True)
class ForceMomentSystem3D:
    """A force and moment at one explicit point in one identified common frame."""

    reference_point: PointInFrame3D
    force: ForceVector3D
    moment: MomentVector3D

    def __post_init__(self) -> None:
        if not isinstance(self.reference_point, PointInFrame3D):
            raise TypeError("ForceMomentSystem3D.reference_point must be a PointInFrame3D.")
        if not isinstance(self.force, ForceVector3D):
            raise TypeError("ForceMomentSystem3D.force must be a ForceVector3D.")
        if not isinstance(self.moment, MomentVector3D):
            raise TypeError("ForceMomentSystem3D.moment must be a MomentVector3D.")


def rotate_force(force: ForceVector3D, rotation: Rotation3D) -> ForceVector3D:
    """Rotate force components at the same physical reference point."""
    if not isinstance(force, ForceVector3D):
        raise TypeError("force must be a ForceVector3D.")
    if not isinstance(rotation, Rotation3D):
        raise TypeError("rotation must be a Rotation3D.")
    rotated = rotation.apply(Vector3D(force.fx, force.fy, force.fz))
    return ForceVector3D(rotated.x, rotated.y, rotated.z)


def rotate_moment(moment: MomentVector3D, rotation: Rotation3D) -> MomentVector3D:
    """Rotate moment components without adding a reference-point shift."""
    if not isinstance(moment, MomentVector3D):
        raise TypeError("moment must be a MomentVector3D.")
    if not isinstance(rotation, Rotation3D):
        raise TypeError("rotation must be a Rotation3D.")
    rotated = rotation.apply(Vector3D(moment.mx, moment.my, moment.mz))
    return MomentVector3D(rotated.x, rotated.y, rotated.z)


def shift_force_moment_reference(
    system: ForceMomentSystem3D,
    target_point: PointInFrame3D,
) -> ForceMomentSystem3D:
    """Shift one force/moment system using M_Q = M_P + (r_P - r_Q) cross F."""
    if not isinstance(system, ForceMomentSystem3D):
        raise TypeError("system must be a ForceMomentSystem3D.")
    if not isinstance(target_point, PointInFrame3D):
        raise TypeError("target_point must be a PointInFrame3D.")
    if target_point.coordinate_frame != system.reference_point.coordinate_frame:
        raise ValueError("Reference-point shifting requires one identified common frame.")
    offset_p_minus_q = vector_between(target_point.position, system.reference_point.position)
    force_vector = Vector3D(system.force.fx, system.force.fy, system.force.fz)
    moment_delta = offset_p_minus_q.cross(force_vector)
    return ForceMomentSystem3D(
        reference_point=target_point,
        force=system.force,
        moment=MomentVector3D(
            system.moment.mx + moment_delta.x,
            system.moment.my + moment_delta.y,
            system.moment.mz + moment_delta.z,
        ),
    )


def interpret_member_end_axial_sense(
    member_end: MemberEnd,
    fx: float,
) -> AxialLoadingSense:
    """Interpret signed member-on-joint Fx without changing the stored sign."""
    if not isinstance(member_end, MemberEnd):
        raise TypeError("member_end must be a MemberEnd.")
    _require_finite_value(fx, "fx")
    if fx == 0.0:
        return AxialLoadingSense.ZERO
    tension = (member_end is MemberEnd.START and fx > 0.0) or (
        member_end is MemberEnd.END and fx < 0.0
    )
    return AxialLoadingSense.TENSION if tension else AxialLoadingSense.COMPRESSION


def positive_action_direction(
    component: ActionComponent,
    frame: CartesianFrame3D,
) -> PositiveActionDirection3D:
    """Return a canonical positive linear or right-hand rotational direction."""
    kind = _component_kind(component)
    return PositiveActionDirection3D(component, kind, _component_axis(component, frame))


def applied_action_direction(
    component: ActionComponent,
    signed_value: float,
    frame: CartesianFrame3D,
) -> AppliedActionDirection3D:
    """Return immutable signed direction data for later rendering."""
    _require_finite_value(signed_value, "signed_value")
    positive = positive_action_direction(component, frame)
    if signed_value == 0.0:
        sense = ActionValueSense.ZERO
        axis = positive.axis
    elif signed_value > 0.0:
        sense = ActionValueSense.POSITIVE
        axis = positive.axis
    else:
        sense = ActionValueSense.NEGATIVE
        axis = -positive.axis
    return AppliedActionDirection3D(
        component=component,
        kind=positive.kind,
        signed_value=signed_value,
        axis=axis,
        sense=sense,
        is_zero=sense is ActionValueSense.ZERO,
    )


__all__ = (
    "ActionComponent",
    "ActionDirectionKind",
    "ActionValueSense",
    "AppliedActionDirection3D",
    "AxialLoadingSense",
    "ForceMomentSystem3D",
    "PointInFrame3D",
    "PositiveActionDirection3D",
    "applied_action_direction",
    "interpret_member_end_axial_sense",
    "positive_action_direction",
    "rotate_force",
    "rotate_moment",
    "shift_force_moment_reference",
)
