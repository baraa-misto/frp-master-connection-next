"""Stage 1.3C3 joint geometry context and frame-registry tests."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace

import pytest

from frp_master_connection.domain import (
    AssemblySupport,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ParticipantKind,
    SupportKind,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    CartesianFrame3D,
    ComponentSurfaceSet3D,
    JointGeometryBasis,
    JointGeometryContext,
    ResolvedFrameBinding,
    create_bounded_support_surface,
)
from tests.c3_fixtures import build_c3_case


def test_complete_context_retains_exact_assembly_geometry_and_is_immutable() -> None:
    case = build_c3_case()

    assert case.context.assembly is case.assembly
    assert case.basis.all_surfaces == tuple(
        patch for surface_set in case.basis.component_surface_sets for patch in surface_set.patches
    )
    member_set = case.basis.component_surface_set(ParticipantKind.MEMBER, "member-1")
    assert member_set is case.basis.component_surface_sets[0]
    with pytest.raises(KeyError, match="No component surface set"):
        case.basis.component_surface_set(ParticipantKind.MEMBER, "missing")
    with pytest.raises(FrozenInstanceError):
        case.context.basis = case.basis  # type: ignore[misc]


@pytest.mark.parametrize(
    ("reference", "frame_attribute", "owner_attribute"),
    [
        (CoordinateFrameReference(CoordinateFrameKind.GLOBAL), None, None),
        (
            CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, "assembly-1"),
            "joint_frame",
            "assembly",
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
            "member_frame",
            "member",
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "connector-1"),
            "connector_frame",
            "connector",
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.INTERFACE_LOCAL, "interface-1"),
            "interface_frame",
            "interface",
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, "bolt-group-1"),
            "bolt_frame",
            "bolt_group",
        ),
    ],
)
def test_symbolic_frame_registry_resolves_every_controlled_kind(
    reference: CoordinateFrameReference,
    frame_attribute: str | None,
    owner_attribute: str | None,
) -> None:
    case = build_c3_case()
    binding = case.context.resolve_frame(reference)

    assert binding.reference is reference
    if frame_attribute is None:
        assert binding.frame is GLOBAL_FRAME
        assert binding.owner is None
    elif frame_attribute == "joint_frame":
        assert binding.frame is case.basis.joint_frame
        assert binding.owner is case.assembly
    elif frame_attribute == "member_frame":
        assert binding.frame is case.basis.placed_members[0].global_frame
        assert binding.owner is case.assembly.members[0]
    elif frame_attribute == "connector_frame":
        assert binding.frame is case.basis.placed_connectors[0].global_frame
        assert binding.owner is case.assembly.connector_components[0]
    elif frame_attribute == "interface_frame":
        assert binding.frame is case.basis.resolved_interfaces[0].interface_frame
        assert binding.owner is case.assembly.interfaces[0]
    else:
        assert frame_attribute == "bolt_frame"
        assert binding.frame is case.resolved_bolt_group.bolt_group_frame
        assert binding.owner is case.assembly.bolt_groups[0]


def test_frame_registry_rejects_wrong_owner_missing_owner_and_runtime_types() -> None:
    context = build_c3_case().context

    for reference in (
        CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, "wrong-joint"),
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "wrong-member"),
        CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "wrong-connector"),
        CoordinateFrameReference(CoordinateFrameKind.INTERFACE_LOCAL, "wrong-interface"),
        CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, "wrong-group"),
    ):
        with pytest.raises(KeyError):
            context.resolve_frame(reference)
    with pytest.raises(TypeError, match="reference"):
        context.resolve_frame("GLOBAL")  # type: ignore[arg-type]


def test_resolved_frame_binding_rejects_inconsistent_global_and_local_provenance() -> None:
    local_reference = CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, "assembly-1")
    with pytest.raises(ValueError, match=r"local.*owner"):
        ResolvedFrameBinding(local_reference, GLOBAL_FRAME, None)
    with pytest.raises(ValueError, match="GLOBAL_FRAME"):
        ResolvedFrameBinding(
            CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
            CartesianFrame3D(
                GLOBAL_FRAME.origin,
                GLOBAL_FRAME.x_axis,
                GLOBAL_FRAME.y_axis,
                GLOBAL_FRAME.z_axis,
            ),
            None,
        )
    with pytest.raises(TypeError, match="reference"):
        ResolvedFrameBinding("GLOBAL", GLOBAL_FRAME, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="frame"):
        ResolvedFrameBinding(
            CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
            "frame",  # type: ignore[arg-type]
            None,
        )


def test_basis_accepts_declared_bounded_support_surfaces_in_deterministic_order() -> None:
    case = build_c3_case()
    support = AssemblySupport("support-1", "Support", SupportKind.CONCRETE)
    assembly = replace(case.assembly, supports=(support,))
    surface = create_bounded_support_surface(
        support,
        "support-face",
        "Support face",
        GLOBAL_FRAME,
        10.0,
        10.0,
    )
    basis = JointGeometryBasis(
        assembly,
        case.basis.joint_frame,
        case.basis.placed_members,
        case.basis.placed_connectors,
        case.basis.component_surface_sets,
        (surface,),
        case.basis.resolved_interfaces,
    )

    assert basis.all_surfaces[-1] is surface
    with pytest.raises(ValueError, match="unique deterministic"):
        replace(basis, support_surfaces=(surface, surface))
    with pytest.raises(ValueError, match="declared assembly support"):
        replace(case.basis, support_surfaces=(surface,))


def test_basis_rejects_incomplete_reordered_or_cross_assembly_content() -> None:
    case = build_c3_case()
    basis = case.basis

    invalid_factories: tuple[Callable[[], object], ...] = (
        lambda: replace(basis, placed_members=()),
        lambda: replace(basis, placed_connectors=()),
        lambda: replace(
            basis, component_surface_sets=tuple(reversed(basis.component_surface_sets))
        ),
        lambda: replace(basis, resolved_interfaces=()),
        lambda: replace(
            basis,
            assembly=replace(
                case.assembly,
                members=(replace(case.assembly.members[0], label="Other object"),),
            ),
        ),
        lambda: replace(
            basis,
            component_surface_sets=(
                replace(
                    basis.component_surface_sets[0],
                    placed_component=basis.placed_connectors[0],
                ),
                basis.component_surface_sets[1],
            ),
        ),
        lambda: replace(
            basis,
            resolved_interfaces=(
                replace(
                    basis.resolved_interfaces[0],
                    interface=replace(case.assembly.interfaces[0], label="Copy"),
                ),
            ),
        ),
    )
    for factory in invalid_factories:
        with pytest.raises(ValueError, match=r"must|exact|match"):
            factory()

    original_surface_set = basis.component_surface_sets[0]
    mismatched_surface_set = object.__new__(ComponentSurfaceSet3D)
    object.__setattr__(
        mismatched_surface_set,
        "participant",
        original_surface_set.participant,
    )
    object.__setattr__(
        mismatched_surface_set,
        "placed_component",
        basis.placed_connectors[0],
    )
    object.__setattr__(mismatched_surface_set, "patches", original_surface_set.patches)
    with pytest.raises(ValueError, match="exact placed component"):
        replace(
            basis,
            component_surface_sets=(
                mismatched_surface_set,
                basis.component_surface_sets[1],
            ),
        )
    with pytest.raises(TypeError, match="assembly"):
        replace(basis, assembly="assembly")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="joint_frame"):
        replace(basis, joint_frame="frame")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(basis, placed_members=[])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="invalid item"):
        replace(basis, support_surfaces=("surface",))  # type: ignore[arg-type]


def test_final_context_requires_exact_complete_unit_consistent_bolt_geometry() -> None:
    case = build_c3_case()

    with pytest.raises(TypeError, match="basis"):
        JointGeometryContext("basis", ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuple"):
        JointGeometryContext(case.basis, [])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="invalid item"):
        JointGeometryContext(case.basis, ("bolt",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="declaration order"):
        JointGeometryContext(case.basis, ())
    with pytest.raises(ValueError, match="unit-system"):
        JointGeometryContext(
            case.basis,
            (
                replace(
                    case.resolved_bolt_group,
                    unit_system=EngineeringUnitSystem.US_CUSTOMARY,
                ),
            ),
        )

    copied_group = replace(case.assembly.bolt_groups[0], label="Copied group")
    copied_assembly = replace(case.assembly, bolt_groups=(copied_group,))
    copied_basis = replace(case.basis, assembly=copied_assembly)
    with pytest.raises(ValueError, match="exact assembly bolt-group"):
        JointGeometryContext(copied_basis, (case.resolved_bolt_group,))
