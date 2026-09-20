"""Stage 1.3C3 reference-point, action, and eccentricity-transform tests."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest

from frp_master_connection.actions import (
    AxialLoadingSense,
    ExplicitEccentricityTransform,
    ExplicitPointFrameBinding,
    ReferencePointResolutionKind,
    ResolvedManualMemberEndAction,
    ResolvedReferencePointGeometry,
    resolve_manual_member_end_action,
    resolve_reference_point,
    shift_resolved_manual_action,
)
from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ForceVector3D,
    ManualMemberEndAction,
    MomentVector3D,
    PositionVector3D,
    ReferencePoint,
    ReferencePointKind,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    CartesianFrame3D,
    JointGeometryContext,
    Vector3D,
)
from tests.c3_fixtures import C3Case, build_c3_case


def _context_with_action(
    case: C3Case,
    action: ManualMemberEndAction,
) -> JointGeometryContext:
    assembly = replace(case.assembly, member_end_actions=(action,))
    basis = replace(case.basis, assembly=assembly)
    return JointGeometryContext(basis, (case.resolved_bolt_group,))


@pytest.mark.parametrize(
    ("reference_point", "provenance"),
    [
        (
            ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "assembly-1"),
            ReferencePointResolutionKind.JOINT_FRAME_ORIGIN,
        ),
        (
            ReferencePoint(ReferencePointKind.MEMBER_CONNECTED_END, "member-1"),
            ReferencePointResolutionKind.MEMBER_CONNECTED_END_SECTION_DATUM,
        ),
        (
            ReferencePoint(ReferencePointKind.INTERFACE_ORIGIN, "interface-1"),
            ReferencePointResolutionKind.INTERFACE_FRAME_ORIGIN,
        ),
        (
            ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, "bolt-group-1"),
            ReferencePointResolutionKind.BOLT_GROUP_FRAME_ORIGIN,
        ),
    ],
)
def test_symbolic_reference_points_resolve_to_exact_geometry_and_provenance(
    reference_point: ReferencePoint,
    provenance: ReferencePointResolutionKind,
) -> None:
    case = build_c3_case()
    resolved = resolve_reference_point(case.context, reference_point)

    assert resolved.reference_point is reference_point
    assert resolved.provenance is provenance
    if reference_point.kind is ReferencePointKind.JOINT_ORIGIN:
        assert resolved.global_position is case.basis.joint_frame.origin
        assert resolved.owner is case.assembly
    elif reference_point.kind is ReferencePointKind.MEMBER_CONNECTED_END:
        boundary = case.basis.placed_members[0].connected_end_plane
        assert boundary is not None
        assert resolved.global_position is boundary.section_datum_point
        assert resolved.connected_end_boundary is boundary
        assert resolved.owner is case.assembly.members[0]
    elif reference_point.kind is ReferencePointKind.INTERFACE_ORIGIN:
        assert resolved.global_position is case.basis.resolved_interfaces[0].interface_frame.origin
        assert resolved.owner is case.assembly.interfaces[0]
    else:
        assert resolved.global_position is case.resolved_bolt_group.origin
        assert resolved.owner is case.assembly.bolt_groups[0]


def test_explicit_reference_point_requires_exact_declared_frame_binding() -> None:
    case = build_c3_case()
    point = ReferencePoint(
        ReferencePointKind.EXPLICIT_POINT,
        position=PositionVector3D(1.0, 2.0, 3.0),
    )
    global_reference = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)
    binding = ExplicitPointFrameBinding(point, global_reference, GLOBAL_FRAME)
    resolved = resolve_reference_point(case.context, point, binding)

    assert resolved.global_position == point.position
    assert resolved.source_frame_reference is global_reference
    assert resolved.source_frame is GLOBAL_FRAME
    assert resolved.owner is None
    assert resolved.provenance is ReferencePointResolutionKind.EXPLICIT_POINT_IN_DECLARED_FRAME

    connector_reference = CoordinateFrameReference(
        CoordinateFrameKind.CONNECTOR_LOCAL,
        "connector-1",
    )
    connector_frame = case.basis.placed_connectors[0].global_frame
    connector_point = ReferencePoint(
        ReferencePointKind.EXPLICIT_POINT,
        position=PositionVector3D(0.0, 1.0, 0.0),
    )
    connector_resolved = resolve_reference_point(
        case.context,
        connector_point,
        ExplicitPointFrameBinding(connector_point, connector_reference, connector_frame),
    )
    assert connector_point.position is not None
    assert connector_resolved.global_position == connector_frame.local_to_parent_point(
        connector_point.position
    )
    assert connector_resolved.owner is case.assembly.connector_components[0]


def test_reference_resolution_rejects_missing_wrong_owner_and_inapplicable_bindings() -> None:
    case = build_c3_case()
    explicit = ReferencePoint(
        ReferencePointKind.EXPLICIT_POINT,
        position=PositionVector3D(0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="requires its exact"):
        resolve_reference_point(case.context, explicit)
    other_explicit = ReferencePoint(
        ReferencePointKind.EXPLICIT_POINT,
        position=PositionVector3D(0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="requires its exact"):
        resolve_reference_point(
            case.context,
            explicit,
            ExplicitPointFrameBinding(
                other_explicit, CoordinateFrameReference(CoordinateFrameKind.GLOBAL), GLOBAL_FRAME
            ),
        )
    copied_global = CartesianFrame3D(
        GLOBAL_FRAME.origin,
        GLOBAL_FRAME.x_axis,
        GLOBAL_FRAME.y_axis,
        GLOBAL_FRAME.z_axis,
    )
    with pytest.raises(ValueError, match="exact context-resolved"):
        resolve_reference_point(
            case.context,
            explicit,
            ExplicitPointFrameBinding(
                explicit,
                CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
                copied_global,
            ),
        )
    symbolic = ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "assembly-1")
    with pytest.raises(ValueError, match="only valid"):
        resolve_reference_point(
            case.context,
            symbolic,
            ExplicitPointFrameBinding(
                explicit,
                CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
                GLOBAL_FRAME,
            ),
        )
    for point in (
        ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "wrong-joint"),
        ReferencePoint(ReferencePointKind.MEMBER_CONNECTED_END, "wrong-member"),
        ReferencePoint(ReferencePointKind.INTERFACE_ORIGIN, "wrong-interface"),
        ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, "wrong-group"),
    ):
        with pytest.raises(KeyError):
            resolve_reference_point(case.context, point)
    with pytest.raises(TypeError, match="context"):
        resolve_reference_point("context", symbolic)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="reference_point"):
        resolve_reference_point(case.context, "point")  # type: ignore[arg-type]


def test_explicit_binding_and_resolved_point_constructors_validate_exact_types() -> None:
    point = ReferencePoint(
        ReferencePointKind.EXPLICIT_POINT,
        position=PositionVector3D(0.0, 0.0, 0.0),
    )
    reference = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)

    with pytest.raises(ValueError, match="explicit"):
        ExplicitPointFrameBinding(
            ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "joint"),
            reference,
            GLOBAL_FRAME,
        )
    with pytest.raises(TypeError, match="frame_reference"):
        ExplicitPointFrameBinding(point, "frame", GLOBAL_FRAME)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="frame must"):
        ExplicitPointFrameBinding(point, reference, "frame")  # type: ignore[arg-type]

    case = build_c3_case()
    valid = resolve_reference_point(
        case.context,
        point,
        ExplicitPointFrameBinding(point, reference, GLOBAL_FRAME),
    )
    invalid_changes = (
        {"reference_point": "point"},
        {"global_position": "position"},
        {"source_frame_reference": "frame"},
        {"source_frame": "frame"},
        {"provenance": "provenance"},
        {
            "source_frame_reference": CoordinateFrameReference(
                CoordinateFrameKind.JOINT_LOCAL,
                "assembly-1",
            ),
            "owner": None,
        },
        {"connected_end_boundary": "boundary"},
    )
    for changes in invalid_changes:
        with pytest.raises((TypeError, ValueError)):
            replace(valid, **changes)


def test_manual_action_resolution_rotates_without_shifting_and_retains_identity() -> None:
    case = build_c3_case()
    action = case.assembly.member_end_actions[0]
    resolved = resolve_manual_member_end_action(case.context, action)

    assert resolved.action is action
    assert resolved.member is case.assembly.members[0]
    assert resolved.load_combination is case.assembly.load_combinations[0]
    assert resolved.original_frame_reference is action.coordinate_frame
    assert resolved.original_reference_point is action.reference_point
    assert resolved.resolved_frame_binding.frame is case.basis.placed_members[0].global_frame
    assert resolved.resolved_reference_point.global_position == PositionVector3D(-1.0, 0.0, 0.0)
    assert resolved.global_force == ForceVector3D(5.0, -3.0, 2.0)
    assert resolved.global_moment == MomentVector3D(13.0, -11.0, 7.0)
    assert resolved.axial_loading_sense is AxialLoadingSense.TENSION
    assert resolved.unit_system is case.assembly.unit_system
    with pytest.raises(FrozenInstanceError):
        resolved.global_force = ForceVector3D(0.0, 0.0, 0.0)  # type: ignore[misc]


def test_axial_sense_is_only_derived_for_the_same_member_local_frame() -> None:
    case = build_c3_case()
    action = case.assembly.member_end_actions[0]
    global_action = replace(
        action,
        coordinate_frame=CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
    )
    context = _context_with_action(case, global_action)
    resolved = resolve_manual_member_end_action(context, global_action)

    assert resolved.axial_loading_sense is None
    assert resolved.global_force == global_action.force
    assert resolved.global_moment == global_action.moment


def test_manual_action_resolution_rejects_cross_assembly_or_invalid_runtime_content() -> None:
    case = build_c3_case()
    action = case.assembly.member_end_actions[0]
    copied = replace(action, id="copied-action")

    with pytest.raises(ValueError, match="assembly-owned"):
        resolve_manual_member_end_action(case.context, copied)
    with pytest.raises(TypeError, match="context"):
        resolve_manual_member_end_action("context", action)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="action"):
        resolve_manual_member_end_action(case.context, "action")  # type: ignore[arg-type]


def test_explicit_eccentricity_shift_uses_source_minus_target_cross_force() -> None:
    case = build_c3_case()
    source = resolve_manual_member_end_action(
        case.context,
        case.assembly.member_end_actions[0],
    )
    target = resolve_reference_point(
        case.context,
        ReferencePoint(ReferencePointKind.INTERFACE_ORIGIN, "interface-1"),
    )
    output_reference = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)
    trace = shift_resolved_manual_action(
        case.context,
        source,
        target,
        output_reference,
        GLOBAL_FRAME,
    )

    assert trace.source_action is source
    assert trace.source_point is source.resolved_reference_point
    assert trace.target_point is target
    assert trace.output_frame_reference is output_reference
    assert trace.output_frame is GLOBAL_FRAME
    assert trace.raw_offset_source_minus_target == Vector3D(-0.5, 0.0, -5.0)
    assert trace.force_in_output_frame == ForceVector3D(5.0, -3.0, 2.0)
    assert trace.moment_at_source_in_output_frame == MomentVector3D(13.0, -11.0, 7.0)
    assert trace.eccentricity_moment_in_output_frame == MomentVector3D(-15.0, -24.0, 1.5)
    assert trace.shifted_moment_in_output_frame == MomentVector3D(-2.0, -35.0, 8.5)
    assert trace.unit_system is case.assembly.unit_system


def test_zero_eccentricity_and_alternate_output_frame_preserve_physical_system() -> None:
    case = build_c3_case()
    source = resolve_manual_member_end_action(
        case.context,
        case.assembly.member_end_actions[0],
    )
    zero = shift_resolved_manual_action(
        case.context,
        source,
        source.resolved_reference_point,
        CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
        GLOBAL_FRAME,
    )
    assert zero.raw_offset_source_minus_target == Vector3D(0.0, 0.0, 0.0)
    assert zero.eccentricity_moment_in_output_frame == MomentVector3D(0.0, 0.0, 0.0)
    assert zero.shifted_moment_in_output_frame == zero.moment_at_source_in_output_frame

    interface_reference = CoordinateFrameReference(
        CoordinateFrameKind.INTERFACE_LOCAL,
        "interface-1",
    )
    interface_frame = case.basis.resolved_interfaces[0].interface_frame
    alternate = shift_resolved_manual_action(
        case.context,
        source,
        source.resolved_reference_point,
        interface_reference,
        interface_frame,
    )
    force_back = interface_frame.local_to_parent_vector(
        Vector3D(
            alternate.force_in_output_frame.fx,
            alternate.force_in_output_frame.fy,
            alternate.force_in_output_frame.fz,
        )
    )
    assert force_back == Vector3D(
        source.global_force.fx,
        source.global_force.fy,
        source.global_force.fz,
    )


def test_eccentricity_shift_rejects_implicit_or_cross_context_inputs() -> None:
    case = build_c3_case()
    source = resolve_manual_member_end_action(
        case.context,
        case.assembly.member_end_actions[0],
    )
    target = source.resolved_reference_point
    global_reference = CoordinateFrameReference(CoordinateFrameKind.GLOBAL)
    copied_global = CartesianFrame3D(
        GLOBAL_FRAME.origin,
        GLOBAL_FRAME.x_axis,
        GLOBAL_FRAME.y_axis,
        GLOBAL_FRAME.z_axis,
    )

    invalid_calls: tuple[Callable[[], object], ...] = (
        lambda: shift_resolved_manual_action(
            cast(JointGeometryContext, "context"),
            source,
            target,
            global_reference,
            GLOBAL_FRAME,
        ),
        lambda: shift_resolved_manual_action(
            case.context,
            cast(ResolvedManualMemberEndAction, "source"),
            target,
            global_reference,
            GLOBAL_FRAME,
        ),
        lambda: shift_resolved_manual_action(
            case.context,
            source,
            cast(ResolvedReferencePointGeometry, "target"),
            global_reference,
            GLOBAL_FRAME,
        ),
        lambda: shift_resolved_manual_action(
            case.context,
            source,
            target,
            cast(CoordinateFrameReference, "GLOBAL"),
            GLOBAL_FRAME,
        ),
        lambda: shift_resolved_manual_action(
            case.context, source, target, global_reference, copied_global
        ),
    )
    for call in invalid_calls:
        with pytest.raises((TypeError, ValueError)):
            call()

    other_action = replace(source.action, id="other-action")
    cross_context_source = replace(source, action=other_action)
    with pytest.raises(ValueError, match="does not belong"):
        shift_resolved_manual_action(
            case.context,
            cross_context_source,
            target,
            global_reference,
            GLOBAL_FRAME,
        )

    copied_action = replace(source.action)
    copied_source = replace(source, action=copied_action)
    with pytest.raises(ValueError, match="does not belong"):
        shift_resolved_manual_action(
            case.context,
            copied_source,
            target,
            global_reference,
            GLOBAL_FRAME,
        )

    wrong_units = replace(source, unit_system=cast(EngineeringUnitSystem, object()))
    with pytest.raises(ValueError, match="does not belong"):
        shift_resolved_manual_action(
            case.context,
            wrong_units,
            target,
            global_reference,
            GLOBAL_FRAME,
        )


def test_action_resolution_public_records_have_complete_explicit_trace_fields() -> None:
    assert {item.name for item in fields(ResolvedManualMemberEndAction)} == {
        "action",
        "member",
        "load_combination",
        "original_frame_reference",
        "resolved_frame_binding",
        "original_reference_point",
        "resolved_reference_point",
        "global_force",
        "global_moment",
        "axial_loading_sense",
        "unit_system",
    }
    assert {item.name for item in fields(ExplicitEccentricityTransform)} == {
        "source_action",
        "source_point",
        "target_point",
        "output_frame_reference",
        "output_frame",
        "source_position_in_output_frame",
        "target_position_in_output_frame",
        "raw_offset_source_minus_target",
        "force_in_output_frame",
        "moment_at_source_in_output_frame",
        "eccentricity_moment_in_output_frame",
        "shifted_moment_in_output_frame",
        "unit_system",
    }
