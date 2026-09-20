"""Stage 1.3C3 bolt placement, round-hole, and penetrated-layer tests."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest

from frp_master_connection.domain import (
    AssemblySupport,
    BoltGroup,
    BoltLocation,
    ConnectionInterface,
    ParticipantKind,
    ParticipantReference,
    PositionVector3D,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SectionTopology,
    SupportKind,
)
from frp_master_connection.geometry import (
    AngleDimensions,
    AuthoritativeBoltAxis3D,
    BoltGroupGeometrySpecification,
    BoltGroupInterfaceRepresentation3D,
    BoltPathDefinition,
    CartesianFrame3D,
    ChannelDimensions,
    ComponentSurfaceSet3D,
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    CrossSectionGeometry2D,
    GeometryComparisonTolerance,
    IntendedPenetratedLayer,
    InterfaceOriginSpecification,
    InterfaceTargetSide,
    InterfaceTargetSideSpecification,
    InterfaceZoneReference,
    ISectionDimensions,
    JointGeometryBasis,
    PlanarRectangularSurface3D,
    PlateDimensions,
    RectangularSubzoneBounds,
    RectangularTubeDimensions,
    ResolvedConnectionInterfaceGeometry,
    ResolvedRoundHoleCylinder3D,
    SectionDatumOffset,
    SurfacePatch3D,
    SurfacePatchReference,
    SurfacePatchRole,
    TeeDimensions,
    UnitVector3D,
    Vector3D,
    create_angle_geometry,
    create_bounded_support_surface,
    create_channel_geometry,
    create_i_section_geometry,
    create_plate_geometry,
    create_rectangular_tube_geometry,
    create_tee_geometry,
    create_wide_flange_geometry,
    resolve_bolt_group_geometry,
    resolve_connection_interface_geometry,
)
from tests.c3_fixtures import C3Case, build_c3_case


def _replace_group_location(
    case: C3Case,
    position: PositionVector3D,
) -> tuple[JointGeometryBasis, BoltGroupGeometrySpecification]:
    old_group = case.assembly.bolt_groups[0]
    group = replace(old_group, locations=(BoltLocation("bolt-1", position),))
    assembly = replace(case.assembly, bolt_groups=(group,))
    basis = replace(case.basis, assembly=assembly)
    specification = replace(case.bolt_specification, bolt_group=group)
    return basis, specification


def _replace_first_layer(
    specification: BoltGroupGeometrySpecification,
    **changes: object,
) -> BoltGroupGeometrySpecification:
    path = specification.paths[0]
    layer = replace(path.layers[0], **changes)  # type: ignore[arg-type]
    return replace(specification, paths=(replace(path, layers=(layer, *path.layers[1:])),))


def test_resolved_bolt_group_retains_authoritative_centers_axes_holes_and_raw_data() -> None:
    case = build_c3_case()
    resolved = case.resolved_bolt_group
    path = resolved.paths[0]

    assert resolved.bolt_group is case.assembly.bolt_groups[0]
    assert resolved.primary_interface is case.basis.resolved_interfaces[0]
    assert resolved.participating_interfaces == case.basis.resolved_interfaces
    assert resolved.origin is resolved.bolt_group_frame.origin
    assert (
        resolved.bolt_group_frame.x_axis == case.basis.resolved_interfaces[0].interface_frame.x_axis
    )
    assert resolved.master_centers[0].local_position is resolved.bolt_group.locations[0].position
    assert resolved.master_centers[0].global_position == resolved.origin
    assert resolved.bolt_axes[0].point == resolved.origin
    assert resolved.bolt_axes[0].direction is resolved.bolt_group_frame.x_axis
    assert resolved.master_centers[0].bolt_group is resolved.bolt_group
    assert resolved.master_centers[0].bolt_group_frame is resolved.bolt_group_frame
    assert resolved.bolt_axes[0].bolt_group is resolved.bolt_group
    assert resolved.bolt_axes[0].bolt_group_frame is resolved.bolt_group_frame
    assert resolved.is_geometry_only
    assert path.definition is case.bolt_specification.paths[0]
    assert path.center is resolved.master_centers[0]
    assert path.axis is resolved.bolt_axes[0]
    assert path.raw_interlayer_gaps == (0.0,)
    assert path.geometric_stack_span == 2.0
    assert path.first_entry_point == path.layers[0].entry.point
    assert path.last_exit_point == path.layers[-1].exit.point
    assert tuple(layer.raw_thickness for layer in path.layers) == (1.0, 1.0)
    assert tuple(layer.raw_minimum_patch_clearance for layer in path.layers) == (2.0, 2.0)
    assert tuple(layer.raw_minimum_zone_clearance for layer in path.layers) == (2.0, 2.0)
    assert all(layer.hole.axis is path.axis for layer in path.layers)
    assert all(layer.hole.radius == 0.5 for layer in path.layers)
    assert path.layers[0].entry.surface.role is SurfacePatchRole.NEGATIVE_THICKNESS_FACE
    assert path.layers[0].exit.surface.role is SurfacePatchRole.POSITIVE_THICKNESS_FACE
    assert path.layers[0].entry.axis_parameter == -1.0
    assert path.layers[-1].exit.axis_parameter == 1.0
    assert resolved.unit_system is case.assembly.unit_system
    assert tuple(layer.physical_element.source_element.id for layer in path.layers) == (
        "PLATE",
        "PLATE",
    )
    assert all(layer.tolerance is resolved.tolerance for layer in path.layers)
    with pytest.raises(FrozenInstanceError):
        resolved.origin = PositionVector3D(1.0, 2.0, 3.0)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("section_family", "geometry_factory", "physical_element_id"),
    [
        (
            SectionFamily.WIDE_FLANGE,
            lambda topology: create_wide_flange_geometry(
                topology,
                ISectionDimensions(10.0, 8.0, 1.0, 1.0),
            ),
            "WEB",
        ),
        (
            SectionFamily.I_SECTION,
            lambda topology: create_i_section_geometry(
                topology,
                ISectionDimensions(10.0, 8.0, 1.0, 1.0),
            ),
            "TOP_FLANGE",
        ),
        (
            SectionFamily.CHANNEL,
            lambda topology: create_channel_geometry(
                topology,
                ChannelDimensions(10.0, 8.0, 1.0, 1.0),
            ),
            "WEB",
        ),
        (
            SectionFamily.TEE,
            lambda topology: create_tee_geometry(
                topology,
                TeeDimensions(10.0, 8.0, 1.0, 1.0),
            ),
            "STEM",
        ),
        (
            SectionFamily.RECTANGULAR_TUBE,
            lambda topology: create_rectangular_tube_geometry(
                topology,
                RectangularTubeDimensions(10.0, 8.0, 1.0),
            ),
            "TOP_WALL",
        ),
        (
            SectionFamily.ANGLE,
            lambda topology: create_angle_geometry(
                topology,
                AngleDimensions(8.0, 8.0, 1.0),
            ),
            "LEG_1",
        ),
        (
            SectionFamily.PLATE,
            lambda topology: create_plate_geometry(topology, PlateDimensions(8.0, 1.0)),
            "PLATE",
        ),
    ],
)
def test_round_hole_resolves_through_every_supported_flat_walled_shape_family(
    section_family: SectionFamily,
    geometry_factory: Callable[[SectionTopology], CrossSectionGeometry2D],
    physical_element_id: str,
) -> None:
    case = build_c3_case(
        section_family,
        geometry_factory,
        physical_element_id,
        SectionDatumOffset(),
    )

    assert tuple(
        layer.physical_element.source_element.id
        for layer in case.resolved_bolt_group.paths[0].layers
    ) == (physical_element_id, physical_element_id)
    assert all(layer.hole.radius == 0.5 for layer in case.resolved_bolt_group.paths[0].layers)


def test_bolt_path_controlled_vocabularies_and_exact_immutable_fields() -> None:
    case = build_c3_case()
    layer = case.bolt_specification.paths[0].layers[0]

    assert set(InterfaceTargetSide) == {
        InterfaceTargetSide.FIRST,
        InterfaceTargetSide.SECOND,
    }
    assert {item.name for item in fields(IntendedPenetratedLayer)} == {
        "id",
        "participant",
        "physical_element_id",
        "entry_surface",
        "exit_surface",
        "connection_zones",
        "hole_diameter",
    }
    assert {item.name for item in fields(BoltGroupGeometrySpecification)} == {
        "bolt_group",
        "primary_interface_id",
        "origin_y",
        "origin_z",
        "in_plane_reference",
        "tolerance",
        "paths",
    }
    assert {item.name for item in fields(BoltGroupInterfaceRepresentation3D)} == {
        "interface",
        "normal_alignment",
        "signed_plane_offset",
    }
    with pytest.raises(FrozenInstanceError):
        layer.id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: InterfaceZoneReference("bad/id", InterfaceTargetSide.FIRST, "zone"),
        lambda: InterfaceZoneReference(
            "interface",
            cast(InterfaceTargetSide, "FIRST"),
            "zone",
        ),
        lambda: InterfaceZoneReference("interface", InterfaceTargetSide.FIRST, "bad/id"),
    ],
)
def test_zone_reference_rejects_invalid_controlled_identity(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_penetrated_layer_and_path_definitions_fail_closed() -> None:
    case = build_c3_case()
    layer = case.bolt_specification.paths[0].layers[0]
    path = case.bolt_specification.paths[0]

    invalid_layers = (
        lambda: replace(layer, participant=cast(ParticipantReference, "participant")),
        lambda: replace(
            layer,
            participant=ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
        ),
        lambda: replace(layer, physical_element_id="bad/id"),
        lambda: replace(layer, entry_surface=cast(SurfacePatchReference, "surface")),
        lambda: replace(layer, exit_surface=layer.entry_surface),
        lambda: replace(layer, connection_zones=cast(tuple[InterfaceZoneReference, ...], [])),
        lambda: replace(layer, connection_zones=()),
        lambda: replace(
            layer,
            connection_zones=(layer.connection_zones[0], layer.connection_zones[0]),
        ),
        lambda: replace(layer, hole_diameter=True),
        lambda: replace(layer, hole_diameter=0.0),
    )
    for factory in cast(tuple[Callable[[], object], ...], invalid_layers):
        with pytest.raises((TypeError, ValueError)):
            factory()
    with pytest.raises(ValueError, match="nonempty"):
        BoltPathDefinition(path.bolt_location_id, ())
    with pytest.raises(ValueError, match="unique"):
        BoltPathDefinition(path.bolt_location_id, (layer, layer))
    with pytest.raises(ValueError, match="host cannot occur twice"):
        BoltPathDefinition(
            path.bolt_location_id,
            (layer, replace(layer, id="duplicate-host")),
        )
    with pytest.raises(TypeError):
        BoltPathDefinition(path.bolt_location_id, [layer])  # type: ignore[arg-type]


def test_bolt_group_geometry_specification_rejects_inconsistent_logical_contracts() -> None:
    case = build_c3_case()
    specification = case.bolt_specification
    group = specification.bolt_group
    explicit_group = replace(
        group,
        reference_point=ReferencePoint(
            ReferencePointKind.EXPLICIT_POINT,
            position=PositionVector3D(0.0, 0.0, 0.0),
        ),
    )

    invalid = (
        lambda: replace(specification, bolt_group=cast(BoltGroup, "group")),
        lambda: replace(specification, bolt_group=explicit_group),
        lambda: replace(specification, primary_interface_id="bad/id"),
        lambda: replace(specification, primary_interface_id="other-interface"),
        lambda: replace(specification, origin_y=float("nan")),
        lambda: replace(specification, origin_z=cast(float, "zero")),
        lambda: replace(specification, in_plane_reference=cast(Vector3D, "vector")),
        lambda: replace(
            specification,
            tolerance=cast(GeometryComparisonTolerance, "tolerance"),
        ),
        lambda: replace(
            specification,
            paths=cast(tuple[BoltPathDefinition, ...], []),
        ),
        lambda: replace(
            specification,
            paths=cast(tuple[BoltPathDefinition, ...], ("path",)),
        ),
        lambda: replace(specification, paths=()),
    )
    for factory in cast(tuple[Callable[[], object], ...], invalid):
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_group_frame_rejects_zero_parallel_and_nearly_parallel_in_plane_references() -> None:
    case = build_c3_case()
    axis = case.basis.resolved_interfaces[0].interface_frame.x_axis

    for reference in (Vector3D(0.0, 0.0, 0.0), axis, -axis, Vector3D(1.0, 0.0, 1.0e-12)):
        specification = replace(case.bolt_specification, in_plane_reference=reference)
        with pytest.raises(ValueError, match=r"zero|parallel"):
            resolve_bolt_group_geometry(case.basis, specification)


def test_resolver_requires_exact_assembly_owned_group_and_valid_location_plane() -> None:
    case = build_c3_case()
    copied_group = replace(case.assembly.bolt_groups[0], label="Copy")
    with pytest.raises(ValueError, match="assembly-owned"):
        resolve_bolt_group_geometry(
            case.basis,
            replace(case.bolt_specification, bolt_group=copied_group),
        )
    with pytest.raises(TypeError, match="basis"):
        resolve_bolt_group_geometry("basis", case.bolt_specification)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="specification"):
        resolve_bolt_group_geometry(case.basis, "specification")  # type: ignore[arg-type]

    basis, specification = _replace_group_location(
        case,
        PositionVector3D(1.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="local y-z plane"):
        resolve_bolt_group_geometry(basis, specification)


def test_duplicate_master_centers_are_rejected_without_snapping() -> None:
    case = build_c3_case()
    old_group = case.assembly.bolt_groups[0]
    group = replace(
        old_group,
        locations=(
            BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0)),
            BoltLocation("bolt-2", PositionVector3D(0.0, 0.0, 0.0)),
        ),
    )
    first_path = case.bolt_specification.paths[0]
    second_path = replace(first_path, bolt_location_id="bolt-2")
    specification = replace(
        case.bolt_specification,
        bolt_group=group,
        paths=(first_path, second_path),
    )
    basis = replace(case.basis, assembly=replace(case.assembly, bolt_groups=(group,)))

    with pytest.raises(ValueError, match=r"duplicate.*master center"):
        resolve_bolt_group_geometry(basis, specification)


def test_round_hole_disk_containment_uses_raw_clearance_and_explicit_tolerance() -> None:
    case = build_c3_case()
    accepted_basis, accepted_specification = _replace_group_location(
        case,
        PositionVector3D(0.0, 4.5000000005, 0.0),
    )
    accepted = resolve_bolt_group_geometry(
        accepted_basis,
        accepted_specification,
    )
    raw = accepted.paths[0].layers[0].entry.raw_patch_clearance
    assert raw < accepted.paths[0].layers[0].hole.radius
    assert raw + accepted.tolerance.distance_tolerance >= accepted.paths[0].layers[0].hole.radius

    rejected_basis, rejected_specification = _replace_group_location(
        case,
        PositionVector3D(0.0, 4.6, 0.0),
    )
    with pytest.raises(ValueError, match="complete round hole disk"):
        resolve_bolt_group_geometry(
            rejected_basis,
            rejected_specification,
        )


def test_raw_layer_gaps_preserve_positive_and_in_tolerance_negative_values() -> None:
    separated = build_c3_case(interlayer_gap=2.0).resolved_bolt_group.paths[0]
    assert separated.raw_interlayer_gaps == (2.0,)
    assert separated.geometric_stack_span == 4.0

    tiny_overlap = build_c3_case(interlayer_gap=-5.0e-10).resolved_bolt_group.paths[0]
    raw_gap = tiny_overlap.raw_interlayer_gaps[0]
    assert -tiny_overlap.layers[0].tolerance.distance_tolerance <= raw_gap < 0.0
    assert tiny_overlap.geometric_stack_span == 2.0 + raw_gap


def test_layer_faces_physical_element_zone_and_declared_order_fail_closed() -> None:
    case = build_c3_case()
    first = case.bolt_specification.paths[0].layers[0]
    member_surfaces = case.basis.component_surface_sets[0]
    edge = next(
        patch for patch in member_surfaces.patches if patch.role is SurfacePatchRole.EDGE_FACE
    )

    invalid_specs = (
        _replace_first_layer(
            case.bolt_specification,
            entry_surface=first.exit_surface,
            exit_surface=first.entry_surface,
        ),
        _replace_first_layer(case.bolt_specification, physical_element_id="OTHER"),
        _replace_first_layer(case.bolt_specification, entry_surface=edge.reference),
        _replace_first_layer(
            case.bolt_specification,
            connection_zones=(replace(first.connection_zones[0], zone_id="missing-zone"),),
        ),
        _replace_first_layer(
            case.bolt_specification,
            connection_zones=(
                replace(
                    first.connection_zones[0],
                    side=InterfaceTargetSide.SECOND,
                    zone_id="second-zone",
                ),
            ),
        ),
        _replace_first_layer(
            case.bolt_specification,
            connection_zones=(replace(first.connection_zones[0], interface_id="other-interface"),),
        ),
        replace(
            case.bolt_specification,
            paths=(
                replace(
                    case.bolt_specification.paths[0],
                    layers=tuple(reversed(case.bolt_specification.paths[0].layers)),
                ),
            ),
        ),
    )
    for specification in invalid_specs:
        with pytest.raises((KeyError, ValueError)):
            resolve_bolt_group_geometry(case.basis, specification)


def _corrupt_surface_set(
    case: C3Case,
    original: SurfacePatch3D,
    replacement: SurfacePatch3D,
) -> ComponentSurfaceSet3D:
    surface_set = case.basis.component_surface_sets[0]
    corrupted = object.__new__(type(surface_set))
    object.__setattr__(corrupted, "participant", surface_set.participant)
    object.__setattr__(corrupted, "placed_component", surface_set.placed_component)
    object.__setattr__(
        corrupted,
        "patches",
        tuple(replacement if patch is original else patch for patch in surface_set.patches),
    )
    return corrupted


def test_face_alignment_and_positive_layer_separation_are_geometric_not_name_based() -> None:
    case = build_c3_case()
    member_set = case.basis.component_surface_sets[0]
    negative = next(patch for patch in member_set.patches if patch.id.endswith("NEGATIVE_TT_BROAD"))
    positive = next(patch for patch in member_set.patches if patch.id.endswith("POSITIVE_TT_BROAD"))
    assert isinstance(negative.geometry, PlanarRectangularSurface3D)
    assert isinstance(positive.geometry, PlanarRectangularSurface3D)

    wrong_normal = replace(positive, geometry=negative.geometry)
    wrong_normal_set = _corrupt_surface_set(case, positive, wrong_normal)
    wrong_normal_basis = replace(
        case.basis,
        component_surface_sets=(
            wrong_normal_set,
            case.basis.component_surface_sets[1],
        ),
    )
    with pytest.raises(ValueError, match="not aligned"):
        resolve_bolt_group_geometry(wrong_normal_basis, case.bolt_specification)

    reversed_geometry = replace(
        positive.geometry,
        frame=replace(positive.geometry.frame, origin=negative.geometry.center),
    )
    reversed_positive = replace(positive, geometry=reversed_geometry)
    reversed_set = _corrupt_surface_set(case, positive, reversed_positive)
    reversed_basis = replace(
        case.basis,
        component_surface_sets=(
            reversed_set,
            case.basis.component_surface_sets[1],
        ),
    )
    with pytest.raises(ValueError, match="positive entry-to-exit"):
        resolve_bolt_group_geometry(reversed_basis, case.bolt_specification)


def test_rectangular_connection_zone_must_contain_the_complete_hole_disk() -> None:
    case = build_c3_case()
    interface = case.assembly.interfaces[0]
    resolved = case.basis.resolved_interfaces[0]
    first_zone = replace(
        resolved.first_side.zones[0].specification,
        kind=ConnectionZoneKind.RECTANGULAR_SUBZONE,
        rectangular_bounds=RectangularSubzoneBounds(-0.4, 0.4, -0.4, 0.4),
    )
    second_zone = resolved.second_side.zones[0].specification
    specification = ConnectionInterfaceGeometrySpecification(
        interface,
        InterfaceTargetSideSpecification(
            interface.participant_a,
            (first_zone,),
            first_zone.id,
        ),
        InterfaceTargetSideSpecification(
            interface.participant_b,
            (second_zone,),
            second_zone.id,
        ),
        InterfaceOriginSpecification(first_zone.id, 0.0, 0.0),
        resolved.interface_frame.y_axis,
        resolved.tolerance,
    )
    narrowed = resolve_connection_interface_geometry(specification, case.basis.all_surfaces)
    basis = replace(case.basis, resolved_interfaces=(narrowed,))

    with pytest.raises(ValueError, match="contained in a connection zone"):
        resolve_bolt_group_geometry(basis, case.bolt_specification)


def _two_interface_geometry() -> tuple[
    JointGeometryBasis,
    BoltGroupGeometrySpecification,
    tuple[InterfaceZoneReference, InterfaceZoneReference],
]:
    case = build_c3_case()
    first_interface = case.assembly.interfaces[0]
    second_interface = replace(first_interface, id="interface-2", label="Second interface")
    first_resolved = case.basis.resolved_interfaces[0]
    first_zone = replace(
        first_resolved.first_side.zones[0].specification,
        id="first-zone-2",
        label="Second member zone",
    )
    second_zone = replace(
        first_resolved.second_side.zones[0].specification,
        id="second-zone-2",
        label="Second connector zone",
    )
    interface_specification = ConnectionInterfaceGeometrySpecification(
        second_interface,
        InterfaceTargetSideSpecification(
            second_interface.participant_a,
            (first_zone,),
            first_zone.id,
        ),
        InterfaceTargetSideSpecification(
            second_interface.participant_b,
            (second_zone,),
            second_zone.id,
        ),
        InterfaceOriginSpecification(first_zone.id, 0.0, 0.0),
        first_resolved.interface_frame.y_axis,
        first_resolved.tolerance,
    )
    second_resolved = resolve_connection_interface_geometry(
        interface_specification,
        case.basis.all_surfaces,
    )
    group = replace(
        case.assembly.bolt_groups[0],
        interface_ids=(first_interface.id, second_interface.id),
    )
    assembly = replace(
        case.assembly,
        interfaces=(first_interface, second_interface),
        bolt_groups=(group,),
    )
    basis = replace(
        case.basis,
        assembly=assembly,
        resolved_interfaces=(first_resolved, second_resolved),
    )
    specification = replace(case.bolt_specification, bolt_group=group)
    return (
        basis,
        specification,
        (
            InterfaceZoneReference(
                second_interface.id,
                InterfaceTargetSide.FIRST,
                first_zone.id,
            ),
            InterfaceZoneReference(
                second_interface.id,
                InterfaceTargetSide.SECOND,
                second_zone.id,
            ),
        ),
    )


def test_every_path_requires_primary_interface_and_group_requires_all_interfaces() -> None:
    basis, specification, second_references = _two_interface_geometry()
    with pytest.raises(ValueError, match="every and only"):
        resolve_bolt_group_geometry(basis, specification)

    path = specification.paths[0]
    layers = (
        replace(path.layers[0], connection_zones=(second_references[0],)),
        replace(path.layers[1], connection_zones=(second_references[1],)),
    )
    without_primary = replace(specification, paths=(replace(path, layers=layers),))
    with pytest.raises(ValueError, match="represent the primary"):
        resolve_bolt_group_geometry(basis, without_primary)


def test_multi_interface_representations_retain_raw_alignment_and_plane_offset() -> None:
    basis, specification, second_references = _two_interface_geometry()
    path = specification.paths[0]
    layers = (
        replace(
            path.layers[0],
            connection_zones=(path.layers[0].connection_zones[0], second_references[0]),
        ),
        replace(
            path.layers[1],
            connection_zones=(path.layers[1].connection_zones[0], second_references[1]),
        ),
    )
    resolved = resolve_bolt_group_geometry(
        basis,
        replace(specification, paths=(replace(path, layers=layers),)),
    )

    assert tuple(item.interface for item in resolved.interface_representations) == (
        resolved.participating_interfaces
    )
    assert tuple(item.normal_alignment for item in resolved.interface_representations) == (
        1.0,
        1.0,
    )
    assert tuple(item.signed_plane_offset for item in resolved.interface_representations) == (
        0.0,
        0.0,
    )

    second = basis.resolved_interfaces[1]
    primary_frame = basis.resolved_interfaces[0].interface_frame
    antiparallel = replace(
        second,
        interface_frame=CartesianFrame3D(
            second.interface_frame.origin,
            -primary_frame.x_axis,
            primary_frame.y_axis,
            -primary_frame.z_axis,
        ),
    )
    antiparallel_basis = replace(
        basis,
        resolved_interfaces=(basis.resolved_interfaces[0], antiparallel),
    )
    antiparallel_resolved = resolve_bolt_group_geometry(
        antiparallel_basis,
        replace(specification, paths=(replace(path, layers=layers),)),
    )
    assert antiparallel_resolved.interface_representations[1].normal_alignment == -1.0

    oblique = replace(
        second,
        interface_frame=CartesianFrame3D(
            second.interface_frame.origin,
            UnitVector3D(0.0, 1.0, 0.0),
            UnitVector3D(1.0, 0.0, 0.0),
            UnitVector3D(0.0, 0.0, -1.0),
        ),
    )
    oblique_basis = replace(
        basis,
        resolved_interfaces=(basis.resolved_interfaces[0], oblique),
    )
    with pytest.raises(ValueError, match="parallel or antiparallel"):
        resolve_bolt_group_geometry(
            oblique_basis,
            replace(specification, paths=(replace(path, layers=layers),)),
        )

    representation = resolved.interface_representations[0]
    with pytest.raises(TypeError, match="interface"):
        replace(
            representation,
            interface=cast(ResolvedConnectionInterfaceGeometry, "interface"),
        )
    with pytest.raises(TypeError, match="real number"):
        replace(representation, normal_alignment=True)
    with pytest.raises(ValueError, match="finite"):
        replace(representation, signed_plane_offset=float("inf"))


def test_minimum_positive_hole_diameter_must_retain_a_representable_radius() -> None:
    case = build_c3_case()
    specification = _replace_first_layer(case.bolt_specification, hole_diameter=5.0e-324)

    with pytest.raises(ValueError, match=r"radius.*representable"):
        resolve_bolt_group_geometry(case.basis, specification)


def test_each_penetrated_layer_retains_its_own_round_hole_diameter() -> None:
    case = build_c3_case()
    path = case.bolt_specification.paths[0]
    specification = replace(
        case.bolt_specification,
        paths=(
            replace(
                path,
                layers=(path.layers[0], replace(path.layers[1], hole_diameter=2.0)),
            ),
        ),
    )

    resolved = resolve_bolt_group_geometry(case.basis, specification)
    assert tuple(layer.definition.hole_diameter for layer in resolved.paths[0].layers) == (
        1.0,
        2.0,
    )
    assert tuple(layer.hole.radius for layer in resolved.paths[0].layers) == (0.5, 1.0)


def test_support_target_interface_is_valid_but_support_is_not_a_penetrated_layer() -> None:
    case = build_c3_case()
    support = AssemblySupport("support-1", "Support", SupportKind.OTHER)
    support_ref = ParticipantReference(ParticipantKind.SUPPORT, support.id)
    old_interface = case.assembly.interfaces[0]
    interface = ConnectionInterface(
        old_interface.id,
        "Member-to-support interface",
        old_interface.participant_a,
        support_ref,
        old_interface.transfer_intent,
    )
    member_zone = case.basis.resolved_interfaces[0].first_side.zones[0].specification
    member_surface = case.resolved_bolt_group.paths[0].layers[0].exit.surface
    member_geometry = cast(PlanarRectangularSurface3D, member_surface.geometry)
    support_frame = CartesianFrame3D(
        member_geometry.center,
        -member_geometry.frame.x_axis,
        member_geometry.frame.y_axis,
        -member_geometry.frame.z_axis,
    )
    support_surface = create_bounded_support_surface(
        support,
        "SUPPORT_FACE",
        "Support face",
        support_frame,
        member_geometry.extent_y,
        member_geometry.extent_z,
    )
    support_zone = replace(
        member_zone,
        id="support-zone",
        label="Support zone",
        surface_reference=support_surface.reference,
    )
    interface_specification = ConnectionInterfaceGeometrySpecification(
        interface,
        InterfaceTargetSideSpecification(
            interface.participant_a,
            (member_zone,),
            member_zone.id,
        ),
        InterfaceTargetSideSpecification(
            support_ref,
            (support_zone,),
            support_zone.id,
        ),
        InterfaceOriginSpecification(member_zone.id, 0.0, 0.0),
        member_geometry.frame.y_axis,
        case.resolved_bolt_group.tolerance,
    )
    resolved_interface = resolve_connection_interface_geometry(
        interface_specification,
        (*case.basis.all_surfaces, support_surface),
    )
    assembly = replace(case.assembly, supports=(support,), interfaces=(interface,))
    basis = replace(
        case.basis,
        assembly=assembly,
        support_surfaces=(support_surface,),
        resolved_interfaces=(resolved_interface,),
    )
    path = case.bolt_specification.paths[0]
    specification = replace(
        case.bolt_specification,
        paths=(replace(path, layers=(path.layers[0],)),),
    )

    resolved = resolve_bolt_group_geometry(basis, specification)
    assert resolved.participating_interfaces[0].second_participant is support_ref
    assert len(resolved.paths[0].layers) == 1


def test_canonical_resolved_value_constructors_validate_quantity_identity() -> None:
    case = build_c3_case()
    location = case.assembly.bolt_groups[0].locations[0]
    center = case.resolved_bolt_group.master_centers[0]
    axis = case.resolved_bolt_group.bolt_axes[0]
    intersection = case.resolved_bolt_group.paths[0].layers[0].entry

    with pytest.raises(TypeError, match="bolt_group"):
        replace(center, bolt_group=cast(BoltGroup, "group"))
    with pytest.raises(TypeError, match="bolt_location"):
        replace(center, bolt_location=cast(BoltLocation, "bolt"))
    with pytest.raises(ValueError, match="exact bolt-group location"):
        replace(center, bolt_location=replace(location, id="other"))
    with pytest.raises(TypeError, match="bolt_group_frame"):
        replace(center, bolt_group_frame=cast(CartesianFrame3D, "frame"))
    with pytest.raises(ValueError, match="exact logical"):
        replace(center, local_position=PositionVector3D(0.0, 1.0, 0.0))
    with pytest.raises(TypeError, match="global_position"):
        replace(center, global_position=cast(PositionVector3D, "point"))
    with pytest.raises(ValueError, match="exact group-frame transform"):
        replace(center, global_position=PositionVector3D(1.0, 0.0, 0.0))
    with pytest.raises(TypeError, match="bolt_group"):
        replace(axis, bolt_group=cast(BoltGroup, "group"))
    with pytest.raises(TypeError, match="bolt_location"):
        replace(axis, bolt_location=cast(BoltLocation, "bolt"))
    with pytest.raises(ValueError, match="exact bolt-group location"):
        replace(axis, bolt_location=replace(location, id="other"))
    with pytest.raises(TypeError, match="bolt_group_frame"):
        replace(axis, bolt_group_frame=cast(CartesianFrame3D, "frame"))
    with pytest.raises(TypeError, match="position and unit"):
        replace(axis, point=cast(PositionVector3D, "point"))
    with pytest.raises(ValueError, match="transformed master center"):
        replace(axis, point=PositionVector3D(1.0, 0.0, 0.0))
    with pytest.raises(ValueError, match=r"group \+x axis"):
        replace(axis, direction=-axis.direction)
    with pytest.raises(TypeError, match="surface"):
        replace(intersection, surface=cast(SurfacePatch3D, "surface"))
    with pytest.raises(TypeError, match="point"):
        replace(intersection, point=cast(PositionVector3D, "point"))
    with pytest.raises(TypeError, match="real number"):
        replace(intersection, axis_parameter=True)
    with pytest.raises(ValueError, match="finite"):
        replace(intersection, raw_patch_clearance=float("inf"))
    with pytest.raises(ValueError, match="ASCII"):
        ResolvedRoundHoleCylinder3D(
            "bad/id",
            case.basis.placed_members[0].participant,
            "PLATE",
            axis,
            axis.point,
            axis.point,
            0.5,
        )
    with pytest.raises(TypeError, match="participant"):
        replace(
            case.resolved_bolt_group.paths[0].layers[0].hole,
            participant=cast(ParticipantReference, "member"),
        )
    with pytest.raises(TypeError, match="axis"):
        replace(
            case.resolved_bolt_group.paths[0].layers[0].hole,
            axis=cast(AuthoritativeBoltAxis3D, "axis"),
        )
    with pytest.raises(TypeError, match="endpoints"):
        replace(
            case.resolved_bolt_group.paths[0].layers[0].hole,
            start_point=cast(PositionVector3D, "point"),
        )
    with pytest.raises(ValueError, match="positive"):
        replace(case.resolved_bolt_group.paths[0].layers[0].hole, radius=0.0)
