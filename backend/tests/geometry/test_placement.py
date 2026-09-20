"""Tests for exact component placement, extrusion, and physical boundary planes."""

import math
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frp_master_connection.domain import (
    AssemblyMember,
    AssemblySupport,
    ComponentMaterialKind,
    ConnectorComponent,
    ConnectorComponentKind,
    MaterialRegion,
    MaterialRegionRole,
    MemberEnd,
    MemberRole,
    ParticipantKind,
    ParticipantReference,
    PhysicalSectionElement,
    PhysicalSectionElementRole,
    PositionVector3D,
    SectionFamily,
    SectionTopology,
    SectionTopologySource,
    SupportKind,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    ZERO_SECTION_DATUM_OFFSET,
    AngleDimensions,
    Annulus2D,
    AxisAlignedRectangle2D,
    CartesianFrame3D,
    ChannelDimensions,
    CrossSectionGeometry2D,
    DeferredSectionFeature2D,
    DeferredSectionFeatureKind,
    ISectionDimensions,
    LocalAnnularCylinder3D,
    LocalRectangularPrism3D,
    LocalRuledSurface3D,
    LongitudinalBoundaryKind,
    LongitudinalExtent,
    PhysicalElementGeometry2D,
    PhysicalLongitudinalBoundaryPlane3D,
    PlacedComponentGeometry3D,
    PlacedDeferredFeature3D,
    PlacedOutsideBounds3D,
    PlacedPhysicalElement3D,
    PlacedSectionVoid3D,
    PlateDimensions,
    ProfileRepresentationKind,
    RectangularTubeDimensions,
    RoundTubeDimensions,
    SectionBoundingBox2D,
    SectionCoordinates3D,
    SectionDatumOffset,
    SectionLineSegment2D,
    SectionPoint2D,
    SectionVoid2D,
    TeeDimensions,
    UnitVector3D,
    Vector3D,
    create_angle_geometry,
    create_channel_geometry,
    create_doubler_geometry,
    create_i_section_geometry,
    create_plate_geometry,
    create_rectangular_tube_geometry,
    create_round_tube_geometry,
    create_square_tube_geometry,
    create_tee_geometry,
    create_wide_flange_geometry,
    place_connector,
    place_member,
)


def _topology(family: SectionFamily) -> SectionTopology:
    return create_standard_section_topology(family)


def _geometry(family: SectionFamily) -> CrossSectionGeometry2D:
    topology = _topology(family)
    if family is SectionFamily.WIDE_FLANGE:
        return create_wide_flange_geometry(topology, ISectionDimensions(12.0, 8.0, 2.0, 2.0))
    if family is SectionFamily.I_SECTION:
        return create_i_section_geometry(topology, ISectionDimensions(14.0, 10.0, 2.0, 2.0))
    if family is SectionFamily.CHANNEL:
        return create_channel_geometry(topology, ChannelDimensions(12.0, 8.0, 2.0, 2.0))
    if family is SectionFamily.TEE:
        return create_tee_geometry(topology, TeeDimensions(10.0, 8.0, 2.0, 2.0))
    if family is SectionFamily.RECTANGULAR_TUBE:
        return create_rectangular_tube_geometry(
            topology,
            RectangularTubeDimensions(10.0, 8.0, 1.0),
        )
    if family is SectionFamily.ANGLE:
        return create_angle_geometry(topology, AngleDimensions(8.0, 6.0, 1.0))
    if family is SectionFamily.ROUND_TUBE:
        return create_round_tube_geometry(topology, RoundTubeDimensions(10.0, 1.0))
    return create_plate_geometry(topology, PlateDimensions(8.0, 2.0))


def _member(
    family: SectionFamily = SectionFamily.WIDE_FLANGE,
    *,
    connected_end: MemberEnd = MemberEnd.END,
    topology: object = Ellipsis,
) -> AssemblyMember:
    resolved_topology = (
        _topology(family) if topology is Ellipsis else cast(SectionTopology | None, topology)
    )
    return AssemblyMember(
        id="member-1",
        label="Placed member",
        role=MemberRole.BEAM,
        connected_end=connected_end,
        section_family=family,
        material_kind=ComponentMaterialKind.STEEL,
        section_topology=resolved_topology,
    )


def _connector(
    family: SectionFamily = SectionFamily.PLATE,
    *,
    topology: object = Ellipsis,
    connector_id: str = "connector-1",
) -> ConnectorComponent:
    resolved_topology = (
        _topology(family) if topology is Ellipsis else cast(SectionTopology | None, topology)
    )
    return ConnectorComponent(
        id=connector_id,
        label="Placed connector",
        kind=ConnectorComponentKind.OTHER,
        material_kind=ComponentMaterialKind.STEEL,
        section_topology=resolved_topology,
    )


def _placed_member(
    *,
    connected_end: MemberEnd = MemberEnd.END,
    offset: SectionDatumOffset = ZERO_SECTION_DATUM_OFFSET,
) -> PlacedComponentGeometry3D:
    member = _member(connected_end=connected_end)
    geometry = create_wide_flange_geometry(
        cast(SectionTopology, member.section_topology),
        ISectionDimensions(12.0, 8.0, 2.0, 2.0),
    )
    return place_member(
        member,
        geometry,
        PositionVector3D(1.0, 2.0, 3.0),
        PositionVector3D(1.0, 2.0, 13.0),
        Vector3D(0.0, 1.0, 0.0),
        offset,
    )


def _rotated_frame() -> CartesianFrame3D:
    return CartesianFrame3D(
        PositionVector3D(10.0, 20.0, 30.0),
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )


_DEFAULT_CONNECTOR_EXTENT = LongitudinalExtent(-2.0, 3.0)


def _placed_connector(
    family: SectionFamily = SectionFamily.PLATE,
    *,
    frame: CartesianFrame3D = GLOBAL_FRAME,
    extent: LongitudinalExtent = _DEFAULT_CONNECTOR_EXTENT,
    offset: SectionDatumOffset = ZERO_SECTION_DATUM_OFFSET,
) -> PlacedComponentGeometry3D:
    connector = _connector(family)
    geometry = _geometry(family)
    return place_connector(connector, geometry, frame, extent, offset)


def _physical(
    placed: PlacedComponentGeometry3D,
    element_id: str,
) -> PlacedPhysicalElement3D:
    return next(
        element for element in placed.physical_elements if element.source_element.id == element_id
    )


def test_placement_values_are_frozen_slotted_and_tuple_backed() -> None:
    placed = _placed_member()
    values = (
        placed,
        placed.extent,
        placed.section_offset,
        placed.physical_elements[0],
        placed.deferred_features[0],
        placed.nominal_voids[0],
        placed.minimum_x_boundary,
        placed.outside_bounds,
    )

    assert all(not hasattr(value, "__dict__") for value in values)
    assert isinstance(placed.physical_elements, tuple)
    assert isinstance(placed.deferred_features, tuple)
    assert isinstance(placed.nominal_voids, tuple)
    with pytest.raises(FrozenInstanceError):
        placed.extent.x_end = 20.0  # type: ignore[misc]


def test_longitudinal_extent_requires_an_exact_finite_increasing_span() -> None:
    assert LongitudinalExtent(-2.0, 3.0).length == 5.0
    with pytest.raises(ValueError, match="greater"):
        LongitudinalExtent(1.0, 1.0)
    with pytest.raises(ValueError, match="greater"):
        LongitudinalExtent(2.0, 1.0)
    with pytest.raises(ValueError, match="length"):
        LongitudinalExtent(-1.0e308, 1.0e308)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("field_name", ["x_start", "x_end"])
def test_longitudinal_extent_rejects_nonfinite_endpoints(
    value: float,
    field_name: str,
) -> None:
    values = {"x_start": 0.0, "x_end": 1.0}
    values[field_name] = value
    with pytest.raises(ValueError, match="finite"):
        LongitudinalExtent(**values)


@pytest.mark.parametrize("value", [True, "0"])
def test_longitudinal_extent_rejects_boolean_and_nonreal_values(value: object) -> None:
    with pytest.raises(TypeError, match="real number"):
        LongitudinalExtent(cast(float, value), 1.0)


def test_section_offset_is_explicit_finite_and_does_not_mutate_source_geometry() -> None:
    source = _geometry(SectionFamily.PLATE)
    original = source
    offset = SectionDatumOffset(3.0, -4.0)
    placed = place_connector(
        _connector(),
        source,
        GLOBAL_FRAME,
        LongitudinalExtent(-1.0, 2.0),
        offset,
    )
    prism = cast(LocalRectangularPrism3D, placed.physical_elements[0].extrusions[0])

    assert SectionDatumOffset(0.0, 0.0) == ZERO_SECTION_DATUM_OFFSET
    assert prism.rectangle == AxisAlignedRectangle2D(-1.0, 7.0, -5.0, -3.0)
    assert placed.reference_line_point(0.0) == PositionVector3D(0.0, 0.0, 0.0)
    assert placed.section_datum_line_point(0.0) == PositionVector3D(0.0, 3.0, -4.0)
    assert source is original
    assert source.construction_datum == SectionPoint2D(0.0, 0.0)
    assert source.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -1.0, 1.0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("coordinate", ["offset_y", "offset_z"])
def test_section_offset_rejects_nonfinite_values(value: float, coordinate: str) -> None:
    arguments = {"offset_y": 0.0, "offset_z": 0.0}
    arguments[coordinate] = value
    with pytest.raises(ValueError, match="finite"):
        SectionDatumOffset(**arguments)


def test_member_builder_establishes_start_to_end_frame_extent_and_planes() -> None:
    placed = _placed_member()

    assert placed.component.id == "member-1"
    assert placed.participant == ParticipantReference(ParticipantKind.MEMBER, "member-1")
    assert placed.global_frame.origin == PositionVector3D(1.0, 2.0, 3.0)
    assert placed.global_frame.x_axis == UnitVector3D(0.0, 0.0, 1.0)
    assert placed.global_frame.y_axis == UnitVector3D(1.0, 0.0, 0.0)
    assert placed.global_frame.z_axis == UnitVector3D(0.0, 1.0, 0.0)
    assert placed.extent == LongitudinalExtent(0.0, 10.0)
    assert placed.minimum_x_boundary.boundary is LongitudinalBoundaryKind.MINIMUM_LOCAL_X
    assert placed.maximum_x_boundary.boundary is LongitudinalBoundaryKind.MAXIMUM_LOCAL_X
    assert placed.minimum_x_boundary.member_end is MemberEnd.START
    assert placed.maximum_x_boundary.member_end is MemberEnd.END
    assert placed.minimum_x_boundary.reference_line_point == PositionVector3D(1.0, 2.0, 3.0)
    assert placed.maximum_x_boundary.reference_line_point == PositionVector3D(1.0, 2.0, 13.0)
    assert placed.minimum_x_boundary.outward_normal == UnitVector3D(0.0, 0.0, -1.0)
    assert placed.maximum_x_boundary.outward_normal == UnitVector3D(0.0, 0.0, 1.0)
    assert placed.global_frame.inspect().valid


@pytest.mark.parametrize("connected_end", [MemberEnd.START, MemberEnd.END])
def test_member_connected_end_plane_preserves_start_end_identity(
    connected_end: MemberEnd,
) -> None:
    placed = _placed_member(connected_end=connected_end)
    expected = (
        placed.minimum_x_boundary if connected_end is MemberEnd.START else placed.maximum_x_boundary
    )

    assert placed.connected_end_plane is expected
    assert placed.boundary_for_member_end(MemberEnd.START) is placed.minimum_x_boundary
    assert placed.boundary_for_member_end(MemberEnd.END) is placed.maximum_x_boundary
    assert expected.is_connected_member_end is True
    assert (
        placed.maximum_x_boundary if connected_end is MemberEnd.START else placed.minimum_x_boundary
    ).is_connected_member_end is False


def test_connector_uses_explicit_frame_extent_offset_and_neutral_boundaries() -> None:
    placed = _placed_connector(
        frame=_rotated_frame(),
        extent=LongitudinalExtent(-3.0, 4.0),
        offset=SectionDatumOffset(2.0, -1.0),
    )

    assert placed.participant.kind is ParticipantKind.CONNECTOR_COMPONENT
    assert placed.global_frame is _rotated_frame() or placed.global_frame == _rotated_frame()
    assert placed.extent == LongitudinalExtent(-3.0, 4.0)
    assert placed.minimum_x_boundary.member_end is None
    assert placed.maximum_x_boundary.member_end is None
    assert placed.minimum_x_boundary.is_connected_member_end is None
    assert placed.maximum_x_boundary.is_connected_member_end is None
    assert placed.minimum_x_boundary.outward_normal == UnitVector3D(0.0, -1.0, 0.0)
    assert placed.maximum_x_boundary.outward_normal == UnitVector3D(0.0, 1.0, 0.0)
    assert placed.connected_end_plane is None
    with pytest.raises(ValueError, match="no member"):
        placed.boundary_for_member_end(MemberEnd.START)


def test_point_mapping_reference_lines_and_inverse_mapping_are_exact() -> None:
    placed = _placed_connector(
        frame=_rotated_frame(),
        offset=SectionDatumOffset(2.0, -1.0),
    )
    source_point = SectionPoint2D(3.0, 4.0)
    local = placed.section_point_to_local(7.0, source_point)
    global_point = placed.section_point_to_global(7.0, source_point)

    assert local == PositionVector3D(7.0, 5.0, 3.0)
    assert global_point == PositionVector3D(5.0, 27.0, 33.0)
    assert placed.global_to_local(global_point) == local
    assert placed.global_to_section_coordinates(global_point) == SectionCoordinates3D(7.0, 3.0, 4.0)
    assert placed.reference_line_point(7.0) == PositionVector3D(10.0, 27.0, 30.0)
    assert placed.section_datum_line_point(7.0) == PositionVector3D(8.0, 27.0, 29.0)
    assert placed.section_point_to_local(-100.0, SectionPoint2D(0.0, 0.0)).x == -100.0


@settings(database=None, derandomize=True, max_examples=30)
@given(
    x=st.integers(min_value=-100, max_value=100),
    y=st.integers(min_value=-100, max_value=100),
    z=st.integers(min_value=-100, max_value=100),
)
def test_global_section_mapping_round_trip(x: int, y: int, z: int) -> None:
    placed = _placed_connector(
        frame=_rotated_frame(),
        offset=SectionDatumOffset(2.0, -1.0),
    )
    global_point = placed.section_point_to_global(float(x), SectionPoint2D(float(y), float(z)))

    assert placed.global_to_section_coordinates(global_point) == SectionCoordinates3D(
        float(x), float(y), float(z)
    )


def test_boundary_planes_retain_shifted_points_normals_and_geometry_only_status() -> None:
    placed = _placed_member(offset=SectionDatumOffset(2.0, -1.0))
    minimum = placed.minimum_x_boundary
    maximum = placed.maximum_x_boundary

    assert minimum.local_x == 0.0
    assert maximum.local_x == 10.0
    assert minimum.section_datum_point == PositionVector3D(3.0, 1.0, 3.0)
    assert maximum.section_datum_point == PositionVector3D(3.0, 1.0, 13.0)
    assert minimum.outward_normal.norm == pytest.approx(1.0)
    assert maximum.outward_normal.norm == pytest.approx(1.0)
    assert minimum.outward_normal == -maximum.outward_normal
    assert not minimum.is_targetable
    assert not hasattr(minimum, "engineering_status")
    assert not hasattr(minimum, "connection_face")


@pytest.mark.parametrize(
    ("family", "expected_ids", "deferred_count", "void_count"),
    [
        (SectionFamily.WIDE_FLANGE, ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"), 2, 2),
        (SectionFamily.I_SECTION, ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"), 2, 2),
        (SectionFamily.CHANNEL, ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"), 2, 1),
        (SectionFamily.TEE, ("STEM", "FLANGE"), 1, 2),
        (
            SectionFamily.RECTANGULAR_TUBE,
            ("TOP_WALL", "BOTTOM_WALL", "SIDE_WALL_1", "SIDE_WALL_2"),
            4,
            1,
        ),
        (SectionFamily.ANGLE, ("LEG_1", "LEG_2"), 1, 1),
        (SectionFamily.PLATE, ("PLATE",), 0, 0),
        (SectionFamily.ROUND_TUBE, ("CURVED_WALL",), 0, 0),
    ],
)
def test_all_standard_profiles_preserve_separate_occurrences_and_exact_extrusions(
    family: SectionFamily,
    expected_ids: tuple[str, ...],
    deferred_count: int,
    void_count: int,
) -> None:
    placed = _placed_connector(family, offset=SectionDatumOffset(3.0, -2.0))
    topology = cast(SectionTopology, placed.component.section_topology)

    assert tuple(item.source_element.id for item in placed.physical_elements) == expected_ids
    assert len(placed.deferred_features) == deferred_count
    assert len(placed.nominal_voids) == void_count
    for placed_element, source_mapping in zip(
        placed.physical_elements,
        placed.cross_section.physical_elements,
        strict=True,
    ):
        source_element = next(
            element for element in topology.elements if element.id == source_mapping.element_id
        )
        source_region = next(
            region
            for region in topology.material_regions
            if region.id == source_element.material_region_id
        )
        assert placed_element.source_element is source_element
        assert placed_element.source_material_region is source_region
        assert placed_element.source_geometry is source_mapping
        assert placed_element.global_frame is placed.global_frame
        assert placed_element.is_targetable
    assert all(item.is_deferred and not item.is_targetable for item in placed.deferred_features)
    assert all(
        not item.is_material and not item.is_physical_element and not item.is_targetable
        for item in placed.nominal_voids
    )


def test_wide_flange_rectangular_prisms_voids_junction_surfaces_and_shared_region() -> None:
    placed = _placed_member(offset=SectionDatumOffset(3.0, -2.0))
    web = cast(LocalRectangularPrism3D, _physical(placed, "WEB").extrusions[0])
    top = cast(LocalRectangularPrism3D, _physical(placed, "TOP_FLANGE").extrusions[0])
    bottom = cast(LocalRectangularPrism3D, _physical(placed, "BOTTOM_FLANGE").extrusions[0])

    assert web.rectangle == AxisAlignedRectangle2D(2.0, 4.0, -6.0, 2.0)
    assert top.rectangle == AxisAlignedRectangle2D(-1.0, 7.0, 2.0, 4.0)
    assert bottom.rectangle == AxisAlignedRectangle2D(-1.0, 7.0, -8.0, -6.0)
    assert top.extent == bottom.extent == web.extent == LongitudinalExtent(0.0, 10.0)
    assert top is not bottom
    assert (
        _physical(placed, "TOP_FLANGE").source_material_region
        is _physical(placed, "BOTTOM_FLANGE").source_material_region
    )
    assert len(placed.nominal_voids) == 2
    assert all(
        isinstance(feature.extrusion, LocalRuledSurface3D) and feature.extrusion.is_zero_thickness
        for feature in placed.deferred_features
    )
    assert not any(
        isinstance(feature.extrusion, LocalRectangularPrism3D)
        for feature in placed.deferred_features
    )


def test_channel_and_tee_canonical_orientation_is_preserved_without_mirroring() -> None:
    channel = _placed_connector(SectionFamily.CHANNEL, frame=_rotated_frame())
    channel_web = cast(LocalRectangularPrism3D, _physical(channel, "WEB").extrusions[0])
    channel_opening = channel.nominal_voids[0].extrusion.rectangle
    tee = _placed_connector(SectionFamily.TEE)
    tee_flange = cast(LocalRectangularPrism3D, _physical(tee, "FLANGE").extrusions[0])

    assert channel_web.rectangle.max_y == channel_opening.min_y
    assert channel.global_frame.inspect().right_handed
    assert tee_flange.rectangle.min_z > 0.0
    assert all(isinstance(item.extrusion, LocalRuledSurface3D) for item in tee.deferred_features)
    assert not hasattr(channel, "mirror")
    assert not hasattr(channel, "roll_angle")


def test_rectangular_and_square_tubes_retain_walls_corners_void_and_region_pairs() -> None:
    rectangular = _placed_connector(SectionFamily.RECTANGULAR_TUBE)
    square_topology = _topology(SectionFamily.RECTANGULAR_TUBE)
    square_geometry = create_square_tube_geometry(
        square_topology,
        RectangularTubeDimensions(8.0, 8.0, 1.0),
    )
    square = place_connector(
        _connector(SectionFamily.RECTANGULAR_TUBE, topology=square_topology),
        square_geometry,
        GLOBAL_FRAME,
        LongitudinalExtent(1.0, 5.0),
        ZERO_SECTION_DATUM_OFFSET,
    )

    assert len(rectangular.physical_elements) == 4
    assert len(rectangular.deferred_features) == 4
    assert len(rectangular.nominal_voids) == 1
    assert all(
        isinstance(item.extrusion, LocalRectangularPrism3D)
        for item in rectangular.deferred_features
    )
    assert (
        _physical(rectangular, "TOP_WALL").source_material_region
        is _physical(rectangular, "BOTTOM_WALL").source_material_region
    )
    assert (
        _physical(rectangular, "SIDE_WALL_1").source_material_region
        is _physical(rectangular, "SIDE_WALL_2").source_material_region
    )
    assert _physical(rectangular, "TOP_WALL") is not _physical(rectangular, "BOTTOM_WALL")
    assert square.cross_section.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -4.0, 4.0)


def test_angle_plate_and_doubler_extrusions_keep_deferred_and_noncalculation_semantics() -> None:
    angle = _placed_connector(SectionFamily.ANGLE)
    plate = _placed_connector(SectionFamily.PLATE, extent=LongitudinalExtent(2.0, 7.0))
    doubler_topology = _topology(SectionFamily.PLATE)
    doubler = place_connector(
        _connector(SectionFamily.PLATE, topology=doubler_topology),
        create_doubler_geometry(doubler_topology, PlateDimensions(6.0, 1.0)),
        GLOBAL_FRAME,
        LongitudinalExtent(-1.0, 1.0),
        SectionDatumOffset(-2.0, 3.0),
    )

    assert {item.source_element.id for item in angle.physical_elements} == {"LEG_1", "LEG_2"}
    assert angle.deferred_features[0].source_feature.id == "ANGLE_HEEL"
    assert angle.nominal_voids[0].source_void.id == "ANGLE_OPEN_AREA"
    assert not hasattr(angle.deferred_features[0], "material_region")
    assert plate.physical_elements[0].extrusions[0].extent.length == 5.0
    assert len(doubler.physical_elements) == 1
    assert cast(
        LocalRectangularPrism3D,
        doubler.physical_elements[0].extrusions[0],
    ).rectangle == AxisAlignedRectangle2D(-5.0, 1.0, 2.5, 3.5)
    for placed in (angle, plate, doubler):
        assert not hasattr(placed, "volume")
        assert not hasattr(placed, "capacity")
        assert not hasattr(placed, "interfaces")


def test_round_tube_is_one_exact_analytic_annular_cylinder() -> None:
    placed = _placed_connector(
        SectionFamily.ROUND_TUBE,
        extent=LongitudinalExtent(-4.0, 6.0),
        offset=SectionDatumOffset(2.0, -3.0),
    )
    extrusion = placed.physical_elements[0].extrusions[0]

    assert isinstance(extrusion, LocalAnnularCylinder3D)
    assert extrusion.extent == LongitudinalExtent(-4.0, 6.0)
    assert extrusion.annulus == Annulus2D(SectionPoint2D(2.0, -3.0), 5.0, 4.0)
    assert placed.cross_section.profile_kind is ProfileRepresentationKind.ANALYTIC_ANNULUS
    assert not hasattr(extrusion, "mesh")
    assert not hasattr(extrusion, "vertices")
    assert not hasattr(extrusion, "material_crosswise_vector")


def test_renderer_neutral_outside_bounds_and_global_corners_are_deterministic() -> None:
    placed = _placed_connector(
        frame=_rotated_frame(),
        extent=LongitudinalExtent(-1.0, 2.0),
        offset=SectionDatumOffset(2.0, -3.0),
    )

    assert placed.outside_bounds.shifted_section_bounds == SectionBoundingBox2D(
        -2.0, 6.0, -4.0, -2.0
    )
    assert placed.outside_bounds.global_corners == (
        PositionVector3D(12.0, 19.0, 26.0),
        PositionVector3D(12.0, 19.0, 28.0),
        PositionVector3D(4.0, 19.0, 26.0),
        PositionVector3D(4.0, 19.0, 28.0),
        PositionVector3D(12.0, 22.0, 26.0),
        PositionVector3D(12.0, 22.0, 28.0),
        PositionVector3D(4.0, 22.0, 26.0),
        PositionVector3D(4.0, 22.0, 28.0),
    )
    for prohibited in ("camera", "color", "display_scale", "mesh", "pixels"):
        assert not hasattr(placed.outside_bounds, prohibited)


def test_shared_connector_identity_is_not_duplicated_or_distributed() -> None:
    connector = _connector(SectionFamily.TEE, connector_id="shared-tee")
    geometry = create_tee_geometry(
        cast(SectionTopology, connector.section_topology),
        TeeDimensions(10.0, 8.0, 2.0, 2.0),
    )
    placed = place_connector(
        connector,
        geometry,
        GLOBAL_FRAME,
        LongitudinalExtent(-1.0, 1.0),
        ZERO_SECTION_DATUM_OFFSET,
    )

    assert placed.component is connector
    assert placed.participant.entity_id == "shared-tee"
    assert all(item.component is placed.participant for item in placed.physical_elements)
    assert not hasattr(placed, "interface_distribution")
    assert not hasattr(placed, "force_distribution")


def test_scope_contract_contains_no_stage_1_3c2_or_calculation_state() -> None:
    aggregate_fields = {item.name for item in fields(PlacedComponentGeometry3D)}
    boundary_fields = {item.name for item in fields(PhysicalLongitudinalBoundaryPlane3D)}
    prohibited = {
        "bolt",
        "capacity",
        "centroid",
        "connection_face",
        "eccentricity",
        "hole",
        "interface",
        "joint_origin",
        "mesh",
        "moment_shift",
        "resistance",
        "section_property",
        "utilization",
    }

    assert aggregate_fields.isdisjoint(prohibited)
    assert boundary_fields.isdisjoint(prohibited)
    assert "transform" not in aggregate_fields
    assert "roll" not in aggregate_fields
    assert "mirror" not in aggregate_fields


def _descriptor_parts() -> tuple[
    ParticipantReference,
    PhysicalSectionElement,
    MaterialRegion,
    PhysicalElementGeometry2D,
    LocalRectangularPrism3D,
]:
    participant = ParticipantReference(ParticipantKind.MEMBER, "member-1")
    element = PhysicalSectionElement(
        "ELEMENT",
        "Element",
        PhysicalSectionElementRole.CUSTOM,
        "REGION",
    )
    region = MaterialRegion("REGION", "Region", MaterialRegionRole.CUSTOM)
    rectangle = AxisAlignedRectangle2D(-1.0, 1.0, -2.0, 2.0)
    source = PhysicalElementGeometry2D("ELEMENT", (rectangle,))
    prism = LocalRectangularPrism3D(LongitudinalExtent(0.0, 2.0), rectangle)
    return participant, element, region, source, prism


@pytest.mark.parametrize(
    "factory",
    [
        lambda: LocalRectangularPrism3D(
            cast(LongitudinalExtent, "extent"),
            AxisAlignedRectangle2D(-1.0, 1.0, -1.0, 1.0),
        ),
        lambda: LocalRectangularPrism3D(
            LongitudinalExtent(0.0, 1.0),
            cast(AxisAlignedRectangle2D, "rectangle"),
        ),
        lambda: LocalAnnularCylinder3D(
            cast(LongitudinalExtent, "extent"),
            Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, 1.0),
        ),
        lambda: LocalAnnularCylinder3D(
            LongitudinalExtent(0.0, 1.0),
            cast(Annulus2D, "annulus"),
        ),
        lambda: LocalRuledSurface3D(
            cast(LongitudinalExtent, "extent"),
            SectionLineSegment2D(SectionPoint2D(0.0, 0.0), SectionPoint2D(1.0, 0.0)),
        ),
        lambda: LocalRuledSurface3D(
            LongitudinalExtent(0.0, 1.0),
            cast(SectionLineSegment2D, "line"),
        ),
    ],
)
def test_local_extrusion_descriptors_reject_invalid_typed_fields(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(TypeError):
        factory()


def test_placed_physical_element_validates_identity_and_exact_primitive_tuple() -> None:
    participant, element, region, source, prism = _descriptor_parts()

    with pytest.raises(TypeError, match="ParticipantReference"):
        PlacedPhysicalElement3D(
            cast(ParticipantReference, "participant"),
            element,
            region,
            source,
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(ValueError, match="member or connector"):
        PlacedPhysicalElement3D(
            ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            element,
            region,
            source,
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(TypeError, match="source_element"):
        PlacedPhysicalElement3D(
            participant,
            cast(PhysicalSectionElement, "element"),
            region,
            source,
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(TypeError, match="source_material_region"):
        PlacedPhysicalElement3D(
            participant,
            element,
            cast(MaterialRegion, "region"),
            source,
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(ValueError, match="material-region"):
        PlacedPhysicalElement3D(
            participant,
            element,
            MaterialRegion("OTHER", "Other", MaterialRegionRole.CUSTOM),
            source,
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(TypeError, match="source_geometry"):
        PlacedPhysicalElement3D(
            participant,
            element,
            region,
            cast(PhysicalElementGeometry2D, "geometry"),
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(ValueError, match="source geometry"):
        PlacedPhysicalElement3D(
            participant,
            element,
            region,
            PhysicalElementGeometry2D("OTHER", source.geometry),
            GLOBAL_FRAME,
            (prism,),
        )
    with pytest.raises(TypeError, match="global_frame"):
        PlacedPhysicalElement3D(
            participant,
            element,
            region,
            source,
            cast(CartesianFrame3D, "frame"),
            (prism,),
        )
    with pytest.raises(TypeError, match="tuple"):
        PlacedPhysicalElement3D(
            participant,
            element,
            region,
            source,
            GLOBAL_FRAME,
            cast(tuple[LocalRectangularPrism3D, ...], [prism]),
        )
    with pytest.raises(ValueError, match="must not be empty"):
        PlacedPhysicalElement3D(participant, element, region, source, GLOBAL_FRAME, ())
    with pytest.raises(TypeError, match="supported primitives"):
        PlacedPhysicalElement3D(
            participant,
            element,
            region,
            source,
            GLOBAL_FRAME,
            cast(tuple[LocalRectangularPrism3D, ...], ("prism",)),
        )


def test_placed_deferred_feature_validates_source_frame_and_primitive_kind() -> None:
    participant, _, _, _, prism = _descriptor_parts()
    rectangle_feature = DeferredSectionFeature2D(
        "RECTANGLE",
        DeferredSectionFeatureKind.CUSTOM_DEFERRED,
        "Rectangle",
        prism.rectangle,
    )
    line = SectionLineSegment2D(SectionPoint2D(-1.0, 0.0), SectionPoint2D(1.0, 0.0))
    line_feature = DeferredSectionFeature2D(
        "LINE",
        DeferredSectionFeatureKind.CUSTOM_DEFERRED,
        "Line",
        line,
    )
    surface = LocalRuledSurface3D(prism.extent, line)

    with pytest.raises(TypeError, match="source_feature"):
        PlacedDeferredFeature3D(
            participant,
            cast(DeferredSectionFeature2D, "feature"),
            GLOBAL_FRAME,
            prism,
        )
    with pytest.raises(TypeError, match="global_frame"):
        PlacedDeferredFeature3D(
            participant,
            rectangle_feature,
            cast(CartesianFrame3D, "frame"),
            prism,
        )
    with pytest.raises(TypeError, match="deferred rectangle"):
        PlacedDeferredFeature3D(participant, rectangle_feature, GLOBAL_FRAME, surface)
    with pytest.raises(TypeError, match="deferred line"):
        PlacedDeferredFeature3D(participant, line_feature, GLOBAL_FRAME, prism)


def test_placed_void_validates_source_frame_and_rectangular_prism() -> None:
    participant, _, _, _, prism = _descriptor_parts()
    source_void = SectionVoid2D("VOID", "Void", prism.rectangle)

    with pytest.raises(TypeError, match="source_void"):
        PlacedSectionVoid3D(
            participant,
            cast(SectionVoid2D, "void"),
            GLOBAL_FRAME,
            prism,
        )
    with pytest.raises(TypeError, match="global_frame"):
        PlacedSectionVoid3D(
            participant,
            source_void,
            cast(CartesianFrame3D, "frame"),
            prism,
        )
    with pytest.raises(TypeError, match="LocalRectangularPrism3D"):
        PlacedSectionVoid3D(
            participant,
            source_void,
            GLOBAL_FRAME,
            cast(LocalRectangularPrism3D, "prism"),
        )


_MEMBER_REFERENCE = ParticipantReference(ParticipantKind.MEMBER, "member-1")
_ZERO_POINT = PositionVector3D(0.0, 0.0, 0.0)
_NEGATIVE_X = UnitVector3D(-1.0, 0.0, 0.0)


def _boundary(
    *,
    component: ParticipantReference = _MEMBER_REFERENCE,
    boundary: LongitudinalBoundaryKind = LongitudinalBoundaryKind.MINIMUM_LOCAL_X,
    local_x: float = 0.0,
    reference_line_point: PositionVector3D = _ZERO_POINT,
    section_datum_point: PositionVector3D = _ZERO_POINT,
    outward_normal: UnitVector3D = _NEGATIVE_X,
    global_frame: CartesianFrame3D = GLOBAL_FRAME,
    member_end: MemberEnd | None = MemberEnd.START,
    is_connected_member_end: bool | None = False,
) -> PhysicalLongitudinalBoundaryPlane3D:
    return PhysicalLongitudinalBoundaryPlane3D(
        component,
        boundary,
        local_x,
        reference_line_point,
        section_datum_point,
        outward_normal,
        global_frame,
        member_end,
        is_connected_member_end,
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _boundary(boundary=cast(LongitudinalBoundaryKind, "minimum")),
        lambda: _boundary(reference_line_point=cast(PositionVector3D, "point")),
        lambda: _boundary(section_datum_point=cast(PositionVector3D, "point")),
        lambda: _boundary(outward_normal=cast(UnitVector3D, Vector3D(-1.0, 0.0, 0.0))),
        lambda: _boundary(global_frame=cast(CartesianFrame3D, "frame")),
        lambda: _boundary(outward_normal=UnitVector3D(1.0, 0.0, 0.0)),
        lambda: _boundary(member_end=None),
        lambda: _boundary(member_end=MemberEnd.END),
        lambda: _boundary(is_connected_member_end=None),
        lambda: _boundary(
            component=ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            member_end=MemberEnd.START,
            is_connected_member_end=None,
        ),
        lambda: _boundary(
            component=ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            member_end=None,
            is_connected_member_end=True,
        ),
    ],
)
def test_boundary_plane_rejects_invalid_identity_geometry_or_member_semantics(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PlacedOutsideBounds3D(
            cast(CartesianFrame3D, "frame"),
            LongitudinalExtent(0.0, 1.0),
            SectionBoundingBox2D(-1.0, 1.0, -1.0, 1.0),
            ProfileRepresentationKind.RECTANGULAR_COMPOSITE,
        ),
        lambda: PlacedOutsideBounds3D(
            GLOBAL_FRAME,
            cast(LongitudinalExtent, "extent"),
            SectionBoundingBox2D(-1.0, 1.0, -1.0, 1.0),
            ProfileRepresentationKind.RECTANGULAR_COMPOSITE,
        ),
        lambda: PlacedOutsideBounds3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            cast(SectionBoundingBox2D, "bounds"),
            ProfileRepresentationKind.RECTANGULAR_COMPOSITE,
        ),
        lambda: PlacedOutsideBounds3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            SectionBoundingBox2D(-1.0, 1.0, -1.0, 1.0),
            cast(ProfileRepresentationKind, "profile"),
        ),
    ],
)
def test_outside_bounds_reject_invalid_typed_fields(factory: Callable[[], object]) -> None:
    with pytest.raises(TypeError):
        factory()


def _custom_topology(element_ids: tuple[str, ...]) -> SectionTopology:
    return SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=tuple(
            PhysicalSectionElement(
                element_id,
                element_id.title(),
                PhysicalSectionElementRole.CUSTOM,
                "CUSTOM_REGION",
            )
            for element_id in element_ids
        ),
        material_regions=(
            MaterialRegion(
                "CUSTOM_REGION",
                "Custom region",
                MaterialRegionRole.CUSTOM,
            ),
        ),
    )


def test_aggregate_rejects_missing_invalid_or_incompatible_component_topology() -> None:
    plate = _geometry(SectionFamily.PLATE)
    extent = LongitudinalExtent(0.0, 1.0)

    with pytest.raises(ValueError, match="explicit component section topology"):
        PlacedComponentGeometry3D(
            _connector(topology=None),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            plate,
        )

    duplicate_topology = SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(
            PhysicalSectionElement(
                "DUPLICATE",
                "First",
                PhysicalSectionElementRole.CUSTOM,
                "CUSTOM_REGION",
            ),
            PhysicalSectionElement(
                "DUPLICATE",
                "Second",
                PhysicalSectionElementRole.CUSTOM,
                "CUSTOM_REGION",
            ),
        ),
        material_regions=(MaterialRegion("CUSTOM_REGION", "Custom", MaterialRegionRole.CUSTOM),),
    )
    with pytest.raises(ValueError, match="valid component section topology"):
        PlacedComponentGeometry3D(
            _connector(topology=duplicate_topology),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            plate,
        )

    with pytest.raises(ValueError, match=r"AssemblyMember\.section_family"):
        PlacedComponentGeometry3D(
            _member(SectionFamily.WIDE_FLANGE),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            plate,
        )
    with pytest.raises(ValueError, match="standard topology"):
        PlacedComponentGeometry3D(
            _connector(SectionFamily.PLATE),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            _geometry(SectionFamily.WIDE_FLANGE),
        )
    with pytest.raises(ValueError, match="every topology element"):
        PlacedComponentGeometry3D(
            _connector(topology=_custom_topology(("PLATE", "OTHER"))),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            plate,
        )
    wrong_id = replace(
        plate,
        physical_elements=(
            PhysicalElementGeometry2D("OTHER", plate.physical_elements[0].geometry),
        ),
    )
    with pytest.raises(ValueError, match="every topology element"):
        PlacedComponentGeometry3D(
            _connector(topology=_custom_topology(("PLATE",))),
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            wrong_id,
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PlacedComponentGeometry3D(
            cast(
                AssemblyMember | ConnectorComponent,
                AssemblySupport("support-1", "Support", SupportKind.OTHER),
            ),
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            ZERO_SECTION_DATUM_OFFSET,
            _geometry(SectionFamily.PLATE),
        ),
        lambda: PlacedComponentGeometry3D(
            _connector(),
            cast(CartesianFrame3D, "frame"),
            LongitudinalExtent(0.0, 1.0),
            ZERO_SECTION_DATUM_OFFSET,
            _geometry(SectionFamily.PLATE),
        ),
        lambda: PlacedComponentGeometry3D(
            _connector(),
            GLOBAL_FRAME,
            cast(LongitudinalExtent, "extent"),
            ZERO_SECTION_DATUM_OFFSET,
            _geometry(SectionFamily.PLATE),
        ),
        lambda: PlacedComponentGeometry3D(
            _connector(),
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            cast(SectionDatumOffset, "offset"),
            _geometry(SectionFamily.PLATE),
        ),
        lambda: PlacedComponentGeometry3D(
            _connector(),
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            ZERO_SECTION_DATUM_OFFSET,
            cast(CrossSectionGeometry2D, "geometry"),
        ),
        lambda: PlacedComponentGeometry3D(
            _member(SectionFamily.PLATE),
            GLOBAL_FRAME,
            LongitudinalExtent(-1.0, 1.0),
            ZERO_SECTION_DATUM_OFFSET,
            _geometry(SectionFamily.PLATE),
        ),
    ],
)
def test_aggregate_direct_construction_rejects_invalid_core_state(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_placed_aggregate_and_derived_descriptors_require_controlled_construction() -> None:
    connector = _connector()
    geometry = _geometry(SectionFamily.PLATE)
    extent = LongitudinalExtent(0.0, 1.0)

    with pytest.raises(TypeError, match="controlled placement builder"):
        PlacedComponentGeometry3D(
            connector,
            GLOBAL_FRAME,
            extent,
            ZERO_SECTION_DATUM_OFFSET,
            geometry,
        )

    placed = _placed_member()
    uncontrolled_replacements = (
        lambda: replace(placed, extent=LongitudinalExtent(0.0, 20.0)),
        lambda: replace(
            placed.minimum_x_boundary,
            reference_line_point=PositionVector3D(99.0, 98.0, 97.0),
        ),
        lambda: replace(
            placed.physical_elements[0],
            extrusions=placed.physical_elements[0].extrusions,
        ),
        lambda: replace(
            placed.deferred_features[0],
            extrusion=placed.deferred_features[0].extrusion,
        ),
        lambda: replace(
            placed.nominal_voids[0],
            extrusion=placed.nominal_voids[0].extrusion,
        ),
    )
    for uncontrolled_replacement in uncontrolled_replacements:
        with pytest.raises(TypeError, match="controlled placement builder"):
            uncontrolled_replacement()


def test_mapping_and_member_boundary_access_reject_invalid_inputs() -> None:
    placed = _placed_member()

    with pytest.raises(TypeError, match="section_point"):
        placed.section_point_to_local(0.0, cast(SectionPoint2D, "point"))
    with pytest.raises(TypeError, match="member_end"):
        placed.boundary_for_member_end(cast(MemberEnd, "START"))
    with pytest.raises((TypeError, ValueError), match="local_x"):
        placed.reference_line_point(cast(float, True))
    with pytest.raises(ValueError, match="finite"):
        placed.section_datum_line_point(math.inf)


def test_member_and_connector_builders_reject_wrong_entities_and_member_endpoints() -> None:
    member = _member()
    geometry = _geometry(SectionFamily.WIDE_FLANGE)
    point = PositionVector3D(0.0, 0.0, 0.0)

    with pytest.raises(TypeError, match="member must"):
        place_member(
            cast(AssemblyMember, _connector()),
            geometry,
            point,
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
    with pytest.raises(TypeError, match="start"):
        place_member(
            member,
            geometry,
            cast(PositionVector3D, "start"),
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
    with pytest.raises(TypeError, match="end"):
        place_member(
            member,
            geometry,
            point,
            cast(PositionVector3D, "end"),
            Vector3D(0.0, 0.0, 1.0),
        )
    with pytest.raises(ValueError, match="distinct"):
        place_member(member, geometry, point, point, Vector3D(0.0, 0.0, 1.0))
    with pytest.raises(ValueError, match="parallel"):
        place_member(
            member,
            geometry,
            point,
            PositionVector3D(1.0, 0.0, 0.0),
            Vector3D(1.0, 0.0, 0.0),
        )
    with pytest.raises(TypeError, match="connector must"):
        place_connector(
            cast(ConnectorComponent, member),
            _geometry(SectionFamily.PLATE),
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            ZERO_SECTION_DATUM_OFFSET,
        )


def test_default_member_offset_is_the_explicit_shared_zero_value() -> None:
    member = _member(SectionFamily.PLATE)
    geometry = create_plate_geometry(
        cast(SectionTopology, member.section_topology),
        PlateDimensions(4.0, 1.0),
    )
    placed = place_member(
        member,
        geometry,
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(2.0, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )

    assert placed.section_offset is ZERO_SECTION_DATUM_OFFSET
