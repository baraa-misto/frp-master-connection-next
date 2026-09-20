"""Framework-independent three-dimensional Cartesian spatial mathematics."""

import math
from dataclasses import dataclass, field
from typing import Final

from frp_master_connection.domain.values import PositionVector3D

DIMENSIONLESS_MATHEMATICAL_TOLERANCE: Final[float] = 1.0e-12


def _require_finite_real(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


def _require_vector(value: object, field_name: str) -> Vector3D:
    if not isinstance(value, Vector3D):
        raise TypeError(f"{field_name} must be a Vector3D.")
    return value


@dataclass(frozen=True, slots=True)
class Vector3D:
    """A finite geometric displacement or direction vector."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for field_name, value in (("x", self.x), ("y", self.y), ("z", self.z)):
            _require_finite_real(value, f"Vector3D.{field_name}")

    def __add__(self, other: Vector3D) -> Vector3D:
        other_vector = _require_vector(other, "other")
        return Vector3D(
            self.x + other_vector.x,
            self.y + other_vector.y,
            self.z + other_vector.z,
        )

    def __sub__(self, other: Vector3D) -> Vector3D:
        other_vector = _require_vector(other, "other")
        return Vector3D(
            self.x - other_vector.x,
            self.y - other_vector.y,
            self.z - other_vector.z,
        )

    def __neg__(self) -> Vector3D:
        return Vector3D(-self.x, -self.y, -self.z)

    def __mul__(self, scalar: float) -> Vector3D:
        _require_finite_real(scalar, "scalar")
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        return self * scalar

    def dot(self, other: Vector3D) -> float:
        """Return the Euclidean dot product."""
        other_vector = _require_vector(other, "other")
        result = self.x * other_vector.x + self.y * other_vector.y + self.z * other_vector.z
        if not math.isfinite(result):
            raise ValueError("Vector3D dot product must remain finite.")
        return result

    def cross(self, other: Vector3D) -> Vector3D:
        """Return the right-handed Euclidean cross product."""
        other_vector = _require_vector(other, "other")
        return Vector3D(
            self.y * other_vector.z - self.z * other_vector.y,
            self.z * other_vector.x - self.x * other_vector.z,
            self.x * other_vector.y - self.y * other_vector.x,
        )

    @property
    def norm(self) -> float:
        """Return the Euclidean length."""
        result = math.hypot(self.x, self.y, self.z)
        if not math.isfinite(result):
            raise ValueError("Vector3D norm exceeds the finite floating-point range.")
        return result

    def normalized(self) -> UnitVector3D:
        """Return the vector normalized to unit length, rejecting an exact zero vector."""
        scale = max(abs(self.x), abs(self.y), abs(self.z))
        if scale == 0.0:
            raise ValueError("A zero vector cannot be normalized.")
        scaled_x = self.x / scale
        scaled_y = self.y / scale
        scaled_z = self.z / scale
        scaled_magnitude = math.hypot(scaled_x, scaled_y, scaled_z)
        return UnitVector3D(
            scaled_x / scaled_magnitude,
            scaled_y / scaled_magnitude,
            scaled_z / scaled_magnitude,
        )


@dataclass(frozen=True, slots=True)
class UnitVector3D(Vector3D):
    """A finite geometric vector whose Euclidean norm is one within tolerance."""

    def __post_init__(self) -> None:
        Vector3D.__post_init__(self)
        if abs(self.norm - 1.0) > DIMENSIONLESS_MATHEMATICAL_TOLERANCE:
            raise ValueError(
                "UnitVector3D must have unit length within the dimensionless "
                "mathematical tolerance."
            )

    def __neg__(self) -> UnitVector3D:
        return UnitVector3D(-self.x, -self.y, -self.z)


def vector_between(start: PositionVector3D, end: PositionVector3D) -> Vector3D:
    """Return the displacement from start to end."""
    if not isinstance(start, PositionVector3D):
        raise TypeError("start must be a PositionVector3D.")
    if not isinstance(end, PositionVector3D):
        raise TypeError("end must be a PositionVector3D.")
    return Vector3D(end.x - start.x, end.y - start.y, end.z - start.z)


def translate_point(point: PositionVector3D, offset: Vector3D) -> PositionVector3D:
    """Translate a point by a geometric displacement vector."""
    if not isinstance(point, PositionVector3D):
        raise TypeError("point must be a PositionVector3D.")
    offset_vector = _require_vector(offset, "offset")
    return PositionVector3D(
        point.x + offset_vector.x,
        point.y + offset_vector.y,
        point.z + offset_vector.z,
    )


@dataclass(frozen=True, slots=True)
class FrameInspection3D:
    """Renderer-neutral numerical inspection of one supplied Cartesian basis."""

    origin: PositionVector3D
    x_axis: Vector3D
    y_axis: Vector3D
    z_axis: Vector3D
    x_norm: float = field(init=False)
    y_norm: float = field(init=False)
    z_norm: float = field(init=False)
    xy_dot: float = field(init=False)
    xz_dot: float = field(init=False)
    yz_dot: float = field(init=False)
    determinant: float = field(init=False)
    right_handed: bool = field(init=False)
    orthonormal: bool = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.origin, PositionVector3D):
            raise TypeError("FrameInspection3D.origin must be a PositionVector3D.")
        x_vector = _require_vector(self.x_axis, "FrameInspection3D.x_axis")
        y_vector = _require_vector(self.y_axis, "FrameInspection3D.y_axis")
        z_vector = _require_vector(self.z_axis, "FrameInspection3D.z_axis")
        x_norm = x_vector.norm
        y_norm = y_vector.norm
        z_norm = z_vector.norm
        xy_dot = x_vector.dot(y_vector)
        xz_dot = x_vector.dot(z_vector)
        yz_dot = y_vector.dot(z_vector)
        determinant = x_vector.dot(y_vector.cross(z_vector))
        tolerance = DIMENSIONLESS_MATHEMATICAL_TOLERANCE
        orthonormal = (
            abs(x_norm - 1.0) <= tolerance
            and abs(y_norm - 1.0) <= tolerance
            and abs(z_norm - 1.0) <= tolerance
            and abs(xy_dot) <= tolerance
            and abs(xz_dot) <= tolerance
            and abs(yz_dot) <= tolerance
        )
        object.__setattr__(self, "x_norm", x_norm)
        object.__setattr__(self, "y_norm", y_norm)
        object.__setattr__(self, "z_norm", z_norm)
        object.__setattr__(self, "xy_dot", xy_dot)
        object.__setattr__(self, "xz_dot", xz_dot)
        object.__setattr__(self, "yz_dot", yz_dot)
        object.__setattr__(self, "determinant", determinant)
        object.__setattr__(
            self,
            "right_handed",
            abs(determinant - 1.0) <= tolerance,
        )
        object.__setattr__(self, "orthonormal", orthonormal)

    @property
    def valid(self) -> bool:
        """Return whether the basis is both orthonormal and right-handed."""
        return self.right_handed and self.orthonormal


def inspect_cartesian_basis(
    origin: PositionVector3D,
    x_axis: Vector3D,
    y_axis: Vector3D,
    z_axis: Vector3D,
) -> FrameInspection3D:
    """Inspect raw basis data without representing invalid data as a Cartesian frame."""
    if not isinstance(origin, PositionVector3D):
        raise TypeError("origin must be a PositionVector3D.")
    x_vector = _require_vector(x_axis, "x_axis")
    y_vector = _require_vector(y_axis, "y_axis")
    z_vector = _require_vector(z_axis, "z_axis")
    return FrameInspection3D(origin, x_vector, y_vector, z_vector)


@dataclass(frozen=True, slots=True)
class Rotation3D:
    """A proper right-handed orthonormal rotation represented by its columns."""

    x_axis: UnitVector3D
    y_axis: UnitVector3D
    z_axis: UnitVector3D

    def __post_init__(self) -> None:
        for field_name, axis in (
            ("x_axis", self.x_axis),
            ("y_axis", self.y_axis),
            ("z_axis", self.z_axis),
        ):
            if not isinstance(axis, UnitVector3D):
                raise TypeError(f"Rotation3D.{field_name} must be a UnitVector3D.")
        inspection = inspect_cartesian_basis(
            PositionVector3D(0.0, 0.0, 0.0),
            self.x_axis,
            self.y_axis,
            self.z_axis,
        )
        if not inspection.orthonormal:
            raise ValueError("Rotation3D axes must be mutually orthonormal.")
        if not inspection.right_handed:
            raise ValueError("Rotation3D must be proper and right-handed.")

    def apply(self, vector: Vector3D) -> Vector3D:
        """Rotate a local vector into the parent coordinates."""
        local = _require_vector(vector, "vector")
        return Vector3D(
            self.x_axis.x * local.x + self.y_axis.x * local.y + self.z_axis.x * local.z,
            self.x_axis.y * local.x + self.y_axis.y * local.y + self.z_axis.y * local.z,
            self.x_axis.z * local.x + self.y_axis.z * local.y + self.z_axis.z * local.z,
        )

    def apply_inverse(self, vector: Vector3D) -> Vector3D:
        """Rotate a parent vector into the local coordinates using the transpose."""
        parent = _require_vector(vector, "vector")
        return Vector3D(
            self.x_axis.dot(parent),
            self.y_axis.dot(parent),
            self.z_axis.dot(parent),
        )

    def inverse(self) -> Rotation3D:
        """Return the transpose/inverse proper rotation."""
        return Rotation3D(
            UnitVector3D(self.x_axis.x, self.y_axis.x, self.z_axis.x),
            UnitVector3D(self.x_axis.y, self.y_axis.y, self.z_axis.y),
            UnitVector3D(self.x_axis.z, self.y_axis.z, self.z_axis.z),
        )

    def then(self, next_rotation: Rotation3D) -> Rotation3D:
        """Compose rotations so this rotation is applied before next_rotation."""
        if not isinstance(next_rotation, Rotation3D):
            raise TypeError("next_rotation must be a Rotation3D.")
        return Rotation3D(
            next_rotation.apply(self.x_axis).normalized(),
            next_rotation.apply(self.y_axis).normalized(),
            next_rotation.apply(self.z_axis).normalized(),
        )


IDENTITY_ROTATION: Final[Rotation3D] = Rotation3D(
    UnitVector3D(1.0, 0.0, 0.0),
    UnitVector3D(0.0, 1.0, 0.0),
    UnitVector3D(0.0, 0.0, 1.0),
)


@dataclass(frozen=True, slots=True)
class RigidTransform3D:
    """A proper rotation followed by a translation in parent coordinates."""

    rotation: Rotation3D
    translation: Vector3D

    def __post_init__(self) -> None:
        if not isinstance(self.rotation, Rotation3D):
            raise TypeError("RigidTransform3D.rotation must be a Rotation3D.")
        _require_vector(self.translation, "RigidTransform3D.translation")

    def apply_point(self, point: PositionVector3D) -> PositionVector3D:
        """Apply rotation and translation to a point."""
        if not isinstance(point, PositionVector3D):
            raise TypeError("point must be a PositionVector3D.")
        rotated = self.rotation.apply(Vector3D(point.x, point.y, point.z))
        return PositionVector3D(
            rotated.x + self.translation.x,
            rotated.y + self.translation.y,
            rotated.z + self.translation.z,
        )

    def apply_vector(self, vector: Vector3D) -> Vector3D:
        """Apply rotation to a vector without translation."""
        return self.rotation.apply(vector)

    def inverse(self) -> RigidTransform3D:
        """Return the exact inverse rigid transform."""
        inverse_rotation = self.rotation.inverse()
        inverse_translation = -inverse_rotation.apply(self.translation)
        return RigidTransform3D(inverse_rotation, inverse_translation)

    def then(self, next_transform: RigidTransform3D) -> RigidTransform3D:
        """Compose transforms so this transform is applied before next_transform."""
        if not isinstance(next_transform, RigidTransform3D):
            raise TypeError("next_transform must be a RigidTransform3D.")
        return RigidTransform3D(
            self.rotation.then(next_transform.rotation),
            next_transform.rotation.apply(self.translation) + next_transform.translation,
        )


@dataclass(frozen=True, slots=True)
class CartesianFrame3D:
    """A resolved right-handed Cartesian frame expressed in one parent frame."""

    origin: PositionVector3D
    x_axis: UnitVector3D
    y_axis: UnitVector3D
    z_axis: UnitVector3D

    def __post_init__(self) -> None:
        if not isinstance(self.origin, PositionVector3D):
            raise TypeError("CartesianFrame3D.origin must be a PositionVector3D.")
        Rotation3D(self.x_axis, self.y_axis, self.z_axis)

    @property
    def rotation(self) -> Rotation3D:
        """Return this frame's local-to-parent proper rotation."""
        return Rotation3D(self.x_axis, self.y_axis, self.z_axis)

    @property
    def transform(self) -> RigidTransform3D:
        """Return this frame's local-to-parent rigid transform."""
        return RigidTransform3D(
            self.rotation,
            Vector3D(self.origin.x, self.origin.y, self.origin.z),
        )

    def local_to_parent_point(self, point: PositionVector3D) -> PositionVector3D:
        """Transform a local point into parent coordinates."""
        return self.transform.apply_point(point)

    def parent_to_local_point(self, point: PositionVector3D) -> PositionVector3D:
        """Transform a parent point into local coordinates."""
        return self.transform.inverse().apply_point(point)

    def local_to_parent_vector(self, vector: Vector3D) -> Vector3D:
        """Transform a local vector into parent coordinates."""
        return self.rotation.apply(vector)

    def parent_to_local_vector(self, vector: Vector3D) -> Vector3D:
        """Transform a parent vector into local coordinates."""
        return self.rotation.apply_inverse(vector)

    def inspect(self) -> FrameInspection3D:
        """Return numerical renderer-neutral inspection data."""
        return inspect_cartesian_basis(
            self.origin,
            self.x_axis,
            self.y_axis,
            self.z_axis,
        )


GLOBAL_FRAME: Final[CartesianFrame3D] = CartesianFrame3D(
    origin=PositionVector3D(0.0, 0.0, 0.0),
    x_axis=IDENTITY_ROTATION.x_axis,
    y_axis=IDENTITY_ROTATION.y_axis,
    z_axis=IDENTITY_ROTATION.z_axis,
)


def build_cartesian_frame(
    origin: PositionVector3D,
    x_direction: Vector3D,
    local_z_reference: Vector3D,
) -> CartesianFrame3D:
    """Build a right-handed frame from explicit x and local-z reference directions."""
    if not isinstance(origin, PositionVector3D):
        raise TypeError("origin must be a PositionVector3D.")
    x_vector = _require_vector(x_direction, "x_direction")
    z_reference = _require_vector(local_z_reference, "local_z_reference")
    ex = x_vector.normalized()
    if z_reference.x == z_reference.y == z_reference.z == 0.0:
        raise ValueError("local_z_reference must not be the zero vector.")
    z_reference_unit = z_reference.normalized()
    z_projected = z_reference_unit - ex * z_reference_unit.dot(ex)
    if z_projected.norm <= DIMENSIONLESS_MATHEMATICAL_TOLERANCE:
        raise ValueError("local_z_reference must not be parallel or nearly parallel to local x.")
    ez_projected = z_projected.normalized()
    ey = ez_projected.cross(ex).normalized()
    ez = ex.cross(ey).normalized()
    return CartesianFrame3D(origin, ex, ey, ez)


def build_member_frame(
    start: PositionVector3D,
    end: PositionVector3D,
    local_z_reference: Vector3D,
) -> CartesianFrame3D:
    """Build a member frame with origin at START and local x fixed START to END."""
    return build_cartesian_frame(start, vector_between(start, end), local_z_reference)


def transform_between_frames(
    source: CartesianFrame3D,
    target: CartesianFrame3D,
) -> RigidTransform3D:
    """Return the transform from source coordinates to target coordinates."""
    if not isinstance(source, CartesianFrame3D):
        raise TypeError("source must be a CartesianFrame3D.")
    if not isinstance(target, CartesianFrame3D):
        raise TypeError("target must be a CartesianFrame3D.")
    return source.transform.then(target.transform.inverse())


__all__ = (
    "DIMENSIONLESS_MATHEMATICAL_TOLERANCE",
    "GLOBAL_FRAME",
    "IDENTITY_ROTATION",
    "CartesianFrame3D",
    "FrameInspection3D",
    "RigidTransform3D",
    "Rotation3D",
    "UnitVector3D",
    "Vector3D",
    "build_cartesian_frame",
    "build_member_frame",
    "inspect_cartesian_basis",
    "transform_between_frames",
    "translate_point",
    "vector_between",
)
