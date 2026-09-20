"""Tests for immutable vectors, vocabularies, frames, points, and axis identities."""

from dataclasses import FrozenInstanceError
from enum import StrEnum

import pytest

from frp_master_connection.domain import (
    ActionConvention,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ForceVector3D,
    LoadInputBasis,
    MemberEnd,
    MemberRole,
    MomentVector3D,
    ParticipantKind,
    PositionVector3D,
    PrincipalAxisFamily,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SignedPrincipalAxis,
    SupportKind,
    TransferIntent,
)


@pytest.mark.parametrize(
    ("enum_type", "expected_values"),
    [
        (EngineeringUnitSystem, ("SI", "US_CUSTOMARY")),
        (
            CoordinateFrameKind,
            (
                "GLOBAL",
                "JOINT_LOCAL",
                "MEMBER_LOCAL",
                "CONNECTOR_LOCAL",
                "INTERFACE_LOCAL",
                "BOLT_GROUP_LOCAL",
            ),
        ),
        (
            ReferencePointKind,
            (
                "JOINT_ORIGIN",
                "MEMBER_CONNECTED_END",
                "INTERFACE_ORIGIN",
                "BOLT_GROUP_ORIGIN",
                "EXPLICIT_POINT",
            ),
        ),
        (ComponentMaterialKind, ("PULTRUDED_FRP", "STEEL", "OTHER")),
        (PrincipalAxisFamily, ("X", "Y", "Z")),
        (MemberRole, ("BEAM", "COLUMN", "BRACE", "OTHER")),
        (MemberEnd, ("START", "END")),
        (
            SectionFamily,
            (
                "WIDE_FLANGE",
                "I_SECTION",
                "CHANNEL",
                "ANGLE",
                "TEE",
                "RECTANGULAR_TUBE",
                "ROUND_TUBE",
                "PLATE",
                "CUSTOM",
            ),
        ),
        (ConnectorComponentKind, ("PLATE", "CLIP_ANGLE", "TEE", "DOUBLER", "OTHER")),
        (SupportKind, ("CONCRETE", "FOUNDATION", "OTHER")),
        (ParticipantKind, ("MEMBER", "CONNECTOR_COMPONENT", "SUPPORT")),
        (TransferIntent, ("SHEAR_ONLY", "MOMENT_RESISTING")),
        (ConnectionDesignCategory, ("SHEAR", "MOMENT")),
        (LoadInputBasis, ("FACTORED_STRENGTH",)),
        (ActionConvention, ("MEMBER_ON_JOINT",)),
    ],
)
def test_controlled_vocabularies_are_exact(
    enum_type: type[StrEnum],
    expected_values: tuple[str, ...],
) -> None:
    assert tuple(member.value for member in enum_type) == expected_values


def test_signed_axes_are_exact_and_expose_axis_family() -> None:
    assert tuple(axis.value for axis in SignedPrincipalAxis) == (
        "+X",
        "-X",
        "+Y",
        "-Y",
        "+Z",
        "-Z",
    )
    assert SignedPrincipalAxis.NEGATIVE_Z.family is PrincipalAxisFamily.Z
    assert SignedPrincipalAxis.POSITIVE_X.family is SignedPrincipalAxis.NEGATIVE_X.family


def test_vector_types_are_distinct_finite_and_immutable() -> None:
    position = PositionVector3D(1, 2.0, 3)
    force = ForceVector3D(1.0, 2.0, 3.0)
    moment = MomentVector3D(1.0, 2.0, 3.0)

    assert type(position) is PositionVector3D
    assert type(force) is ForceVector3D
    assert type(moment) is MomentVector3D
    with pytest.raises(FrozenInstanceError):
        position.x = 4.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("vector_type", "arguments"),
    [
        (PositionVector3D, (True, 0.0, 0.0)),
        (ForceVector3D, (0.0, "bad", 0.0)),
        (MomentVector3D, (0.0, 0.0, float("inf"))),
        (PositionVector3D, (float("nan"), 0.0, 0.0)),
    ],
)
def test_vectors_reject_non_real_or_nonfinite_components(
    vector_type: type[PositionVector3D] | type[ForceVector3D] | type[MomentVector3D],
    arguments: tuple[object, object, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        vector_type(*arguments)  # type: ignore[arg-type]


def test_coordinate_frame_reference_accepts_global_and_owned_local_frames() -> None:
    assert CoordinateFrameReference(CoordinateFrameKind.GLOBAL).owner_id is None
    local = CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, "assembly-1")
    assert local.owner_id == "assembly-1"


@pytest.mark.parametrize(
    "arguments",
    [
        ("GLOBAL", None),
        (CoordinateFrameKind.GLOBAL, "assembly-1"),
        (CoordinateFrameKind.MEMBER_LOCAL, None),
        (CoordinateFrameKind.MEMBER_LOCAL, "bad/id"),
    ],
)
def test_coordinate_frame_reference_rejects_invalid_owner_combinations(
    arguments: tuple[object, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        CoordinateFrameReference(*arguments)  # type: ignore[arg-type]


def test_reference_point_accepts_symbolic_and_explicit_forms() -> None:
    symbolic = ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "assembly-1")
    position = PositionVector3D(1.0, 2.0, 3.0)
    explicit = ReferencePoint(ReferencePointKind.EXPLICIT_POINT, position=position)

    assert symbolic.owner_id == "assembly-1"
    assert explicit.position is position


@pytest.mark.parametrize(
    "arguments",
    [
        ("EXPLICIT_POINT", None, None),
        (ReferencePointKind.EXPLICIT_POINT, "owner", PositionVector3D(0.0, 0.0, 0.0)),
        (ReferencePointKind.EXPLICIT_POINT, None, None),
        (ReferencePointKind.EXPLICIT_POINT, None, "not-a-position"),
        (ReferencePointKind.JOINT_ORIGIN, None, None),
        (
            ReferencePointKind.JOINT_ORIGIN,
            "assembly-1",
            PositionVector3D(0.0, 0.0, 0.0),
        ),
        (ReferencePointKind.JOINT_ORIGIN, "bad/id", None),
    ],
)
def test_reference_point_rejects_invalid_forms(arguments: tuple[object, object, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        ReferencePoint(*arguments)  # type: ignore[arg-type]
