"""Immutable values and controlled vocabularies for joint-assembly contracts."""

import math
from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.domain.validation import (
    require_enum,
    validate_identifier,
)


class EngineeringUnitSystem(StrEnum):
    """Per-assembly engineering-unit identity; conversion is intentionally excluded."""

    SI = "SI"
    US_CUSTOMARY = "US_CUSTOMARY"


class CoordinateFrameKind(StrEnum):
    """Kinds of symbolic coordinate-frame references."""

    GLOBAL = "GLOBAL"
    JOINT_LOCAL = "JOINT_LOCAL"
    MEMBER_LOCAL = "MEMBER_LOCAL"
    CONNECTOR_LOCAL = "CONNECTOR_LOCAL"
    INTERFACE_LOCAL = "INTERFACE_LOCAL"
    BOLT_GROUP_LOCAL = "BOLT_GROUP_LOCAL"


class ReferencePointKind(StrEnum):
    """Kinds of symbolic moment reference points."""

    JOINT_ORIGIN = "JOINT_ORIGIN"
    MEMBER_CONNECTED_END = "MEMBER_CONNECTED_END"
    INTERFACE_ORIGIN = "INTERFACE_ORIGIN"
    BOLT_GROUP_ORIGIN = "BOLT_GROUP_ORIGIN"
    EXPLICIT_POINT = "EXPLICIT_POINT"


class ComponentMaterialKind(StrEnum):
    """Material classifications needed for domain routing, not properties."""

    PULTRUDED_FRP = "PULTRUDED_FRP"
    STEEL = "STEEL"
    OTHER = "OTHER"


class PrincipalAxisFamily(StrEnum):
    """Sign-insensitive component-local principal-axis lines for material identity."""

    X = "X"
    Y = "Y"
    Z = "Z"


class SignedPrincipalAxis(StrEnum):
    """Signed principal-axis identities within one declared component-local frame."""

    POSITIVE_X = "+X"
    NEGATIVE_X = "-X"
    POSITIVE_Y = "+Y"
    NEGATIVE_Y = "-Y"
    POSITIVE_Z = "+Z"
    NEGATIVE_Z = "-Z"

    @property
    def family(self) -> PrincipalAxisFamily:
        """Return the unsigned X, Y, or Z axis family."""
        return PrincipalAxisFamily(self.value[-1])


class MemberRole(StrEnum):
    """Assembly-member roles."""

    BEAM = "BEAM"
    COLUMN = "COLUMN"
    BRACE = "BRACE"
    OTHER = "OTHER"


class MemberEnd(StrEnum):
    """Connected member ends."""

    START = "START"
    END = "END"


class SectionFamily(StrEnum):
    """Coarse section families without geometry or section-property values."""

    WIDE_FLANGE = "WIDE_FLANGE"
    I_SECTION = "I_SECTION"
    CHANNEL = "CHANNEL"
    ANGLE = "ANGLE"
    TEE = "TEE"
    RECTANGULAR_TUBE = "RECTANGULAR_TUBE"
    ROUND_TUBE = "ROUND_TUBE"
    PLATE = "PLATE"
    CUSTOM = "CUSTOM"


class ConnectorComponentKind(StrEnum):
    """Connector-component classifications."""

    PLATE = "PLATE"
    CLIP_ANGLE = "CLIP_ANGLE"
    TEE = "TEE"
    DOUBLER = "DOUBLER"
    OTHER = "OTHER"


class SupportKind(StrEnum):
    """Assembly-support classifications."""

    CONCRETE = "CONCRETE"
    FOUNDATION = "FOUNDATION"
    OTHER = "OTHER"


class ParticipantKind(StrEnum):
    """Kinds addressable by an interface participant reference."""

    MEMBER = "MEMBER"
    CONNECTOR_COMPONENT = "CONNECTOR_COMPONENT"
    SUPPORT = "SUPPORT"


class TransferIntent(StrEnum):
    """Declared force-transfer intent without calculation behavior."""

    SHEAR_ONLY = "SHEAR_ONLY"
    MOMENT_RESISTING = "MOMENT_RESISTING"


class ConnectionDesignCategory(StrEnum):
    """Exactly the two Stage 1.1 connection design categories."""

    SHEAR = "SHEAR"
    MOMENT = "MOMENT"


class LoadInputBasis(StrEnum):
    """Controlled load-input basis supported by Stage 1.1."""

    FACTORED_STRENGTH = "FACTORED_STRENGTH"


class ActionConvention(StrEnum):
    """Controlled sign convention for manually supplied member-end actions."""

    MEMBER_ON_JOINT = "MEMBER_ON_JOINT"


def _require_finite(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


@dataclass(frozen=True, slots=True)
class PositionVector3D:
    """A finite position vector in the assembly's declared length unit."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for field_name, value in (("x", self.x), ("y", self.y), ("z", self.z)):
            _require_finite(value, f"PositionVector3D.{field_name}")


@dataclass(frozen=True, slots=True)
class ForceVector3D:
    """A finite force vector in the assembly's declared force unit."""

    fx: float
    fy: float
    fz: float

    def __post_init__(self) -> None:
        for field_name, value in (("fx", self.fx), ("fy", self.fy), ("fz", self.fz)):
            _require_finite(value, f"ForceVector3D.{field_name}")


@dataclass(frozen=True, slots=True)
class MomentVector3D:
    """A finite moment vector in the assembly's declared force-length unit."""

    mx: float
    my: float
    mz: float

    def __post_init__(self) -> None:
        for field_name, value in (("mx", self.mx), ("my", self.my), ("mz", self.mz)):
            _require_finite(value, f"MomentVector3D.{field_name}")


@dataclass(frozen=True, slots=True)
class CoordinateFrameReference:
    """A symbolic frame identity; Stage 1.1 does not define transformations."""

    kind: CoordinateFrameKind
    owner_id: str | None = None

    def __post_init__(self) -> None:
        require_enum(self.kind, CoordinateFrameKind, "CoordinateFrameReference.kind")
        if self.kind is CoordinateFrameKind.GLOBAL:
            if self.owner_id is not None:
                raise ValueError("The global coordinate frame must not have an owner_id.")
        elif self.owner_id is None:
            raise ValueError("A local coordinate frame requires an owner_id.")
        else:
            validate_identifier(self.owner_id, "CoordinateFrameReference.owner_id")


@dataclass(frozen=True, slots=True)
class ReferencePoint:
    """A symbolic or explicit point about which a moment is reported."""

    kind: ReferencePointKind
    owner_id: str | None = None
    position: PositionVector3D | None = None

    def __post_init__(self) -> None:
        require_enum(self.kind, ReferencePointKind, "ReferencePoint.kind")
        if self.kind is ReferencePointKind.EXPLICIT_POINT:
            if self.owner_id is not None or self.position is None:
                raise ValueError(
                    "An explicit reference point requires position and must not have owner_id."
                )
            if not isinstance(self.position, PositionVector3D):
                raise TypeError("ReferencePoint.position must be a PositionVector3D.")
        else:
            if self.owner_id is None or self.position is not None:
                raise ValueError(
                    "A symbolic reference point requires owner_id and must not have position."
                )
            validate_identifier(self.owner_id, "ReferencePoint.owner_id")


__all__ = (
    "ActionConvention",
    "ComponentMaterialKind",
    "ConnectionDesignCategory",
    "ConnectorComponentKind",
    "CoordinateFrameKind",
    "CoordinateFrameReference",
    "EngineeringUnitSystem",
    "ForceVector3D",
    "LoadInputBasis",
    "MemberEnd",
    "MemberRole",
    "MomentVector3D",
    "ParticipantKind",
    "PositionVector3D",
    "PrincipalAxisFamily",
    "ReferencePoint",
    "ReferencePointKind",
    "SectionFamily",
    "SignedPrincipalAxis",
    "SupportKind",
    "TransferIntent",
)
