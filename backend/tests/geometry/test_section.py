"""Tests for exact nominal standard cross-section geometry contracts."""

import math
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest

from frp_master_connection.domain import (
    CylindricalMaterialOrientation,
    MaterialRegion,
    MaterialRegionRole,
    PhysicalSectionElement,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    SectionFamily,
    SectionTopology,
    SectionTopologySource,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    AngleDimensions,
    Annulus2D,
    AxisAlignedRectangle2D,
    ChannelDimensions,
    CrossSectionGeometry2D,
    DeferredSectionFeature2D,
    DeferredSectionFeatureKind,
    GeometryIdealization,
    ISectionDimensions,
    PhysicalElementGeometry2D,
    PlateDimensions,
    ProfileRepresentationKind,
    RectangularTubeDimensions,
    RoundTubeDimensions,
    SectionBoundingBox2D,
    SectionLineSegment2D,
    SectionPoint2D,
    SectionVoid2D,
    TeeDimensions,
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
    validate_cross_section_topology,
)


def _topology(family: SectionFamily) -> SectionTopology:
    return create_standard_section_topology(family)


def _rectangle(
    geometry: CrossSectionGeometry2D,
    element_id: str,
) -> AxisAlignedRectangle2D:
    mapping = next(
        mapping for mapping in geometry.physical_elements if mapping.element_id == element_id
    )
    primitive = mapping.geometry[0]
    assert isinstance(primitive, AxisAlignedRectangle2D)
    return primitive


def _deferred(
    geometry: CrossSectionGeometry2D,
    feature_id: str,
) -> DeferredSectionFeature2D:
    return next(feature for feature in geometry.deferred_features if feature.id == feature_id)


def _void(geometry: CrossSectionGeometry2D, void_id: str) -> SectionVoid2D:
    return next(
        nominal_void for nominal_void in geometry.nominal_voids if nominal_void.id == void_id
    )


def _rectangles_overlap(
    first: AxisAlignedRectangle2D,
    second: AxisAlignedRectangle2D,
) -> bool:
    return max(first.min_y, second.min_y) < min(first.max_y, second.max_y) and max(
        first.min_z, second.min_z
    ) < min(first.max_z, second.max_z)


def _plate_geometry() -> CrossSectionGeometry2D:
    return create_plate_geometry(_topology(SectionFamily.PLATE), PlateDimensions(8.0, 2.0))


def _custom_topology() -> SectionTopology:
    return SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(
            PhysicalSectionElement(
                "CUSTOM_ELEMENT",
                "Custom element",
                PhysicalSectionElementRole.CUSTOM,
                "CUSTOM_REGION",
            ),
        ),
        material_regions=(
            MaterialRegion(
                "CUSTOM_REGION",
                "Custom region",
                MaterialRegionRole.CUSTOM,
            ),
        ),
    )


def test_geometry_vocabularies_are_exact_and_controlled() -> None:
    assert tuple(item.value for item in DeferredSectionFeatureKind) == (
        "ANGLE_HEEL",
        "RECTANGULAR_TUBE_CORNER",
        "WEB_TO_FLANGE_JUNCTION",
        "STEM_TO_FLANGE_JUNCTION",
        "CUSTOM_DEFERRED",
    )
    assert tuple(item.value for item in GeometryIdealization) == (
        "NOMINAL_SHARP_CORNER",
        "ANALYTIC_ANNULUS",
    )
    assert tuple(item.value for item in ProfileRepresentationKind) == (
        "RECTANGULAR_COMPOSITE",
        "ANALYTIC_ANNULUS",
    )


def test_finite_geometry_primitives_are_exact_frozen_and_slotted() -> None:
    point = SectionPoint2D(1.0, -2.0)
    bounds = SectionBoundingBox2D(-4.0, 4.0, -3.0, 5.0)
    rectangle = AxisAlignedRectangle2D(-2.0, 2.0, -1.0, 1.0)
    line = SectionLineSegment2D(SectionPoint2D(-1.0, 0.0), SectionPoint2D(1.0, 0.0))
    annulus = Annulus2D(SectionPoint2D(0.0, 0.0), 5.0, 4.0)

    assert bounds.center == SectionPoint2D(0.0, 1.0)
    assert annulus.inner_radius == 4.0
    for value in (point, bounds, rectangle, line, annulus):
        assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        point.y = 3.0  # type: ignore[misc]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("coordinate", ["y", "z"])
def test_section_point_rejects_nonfinite_coordinates(value: float, coordinate: str) -> None:
    arguments = {"y": 0.0, "z": 0.0}
    arguments[coordinate] = value
    with pytest.raises(ValueError, match="finite"):
        SectionPoint2D(**arguments)


@pytest.mark.parametrize("value", [True, "1"])
def test_section_point_rejects_boolean_and_nonreal_coordinates(value: object) -> None:
    with pytest.raises(TypeError, match="real number"):
        SectionPoint2D(cast(float, value), 0.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SectionBoundingBox2D(0.0, 0.0, -1.0, 1.0),
        lambda: SectionBoundingBox2D(1.0, 0.0, -1.0, 1.0),
        lambda: SectionBoundingBox2D(-1.0, 1.0, 0.0, 0.0),
        lambda: SectionBoundingBox2D(-1.0, 1.0, 1.0, 0.0),
        lambda: AxisAlignedRectangle2D(0.0, 0.0, -1.0, 1.0),
        lambda: AxisAlignedRectangle2D(1.0, 0.0, -1.0, 1.0),
        lambda: AxisAlignedRectangle2D(-1.0, 1.0, 0.0, 0.0),
        lambda: AxisAlignedRectangle2D(-1.0, 1.0, 1.0, 0.0),
    ],
)
def test_rectangular_primitives_require_positive_spans(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="positive"):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SectionBoundingBox2D(cast(float, True), 1.0, -1.0, 1.0),
        lambda: SectionBoundingBox2D(-1.0, math.nan, -1.0, 1.0),
        lambda: SectionBoundingBox2D(-1.0, 1.0, -math.inf, 1.0),
        lambda: SectionBoundingBox2D(-1.0, 1.0, -1.0, math.inf),
        lambda: AxisAlignedRectangle2D(cast(float, "-1"), 1.0, -1.0, 1.0),
        lambda: AxisAlignedRectangle2D(-1.0, math.nan, -1.0, 1.0),
        lambda: AxisAlignedRectangle2D(-1.0, 1.0, -math.inf, 1.0),
        lambda: AxisAlignedRectangle2D(-1.0, 1.0, -1.0, math.inf),
    ],
)
def test_rectangular_primitives_reject_invalid_coordinates(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_line_segment_requires_typed_distinct_endpoints() -> None:
    point = SectionPoint2D(0.0, 0.0)

    with pytest.raises(TypeError, match="start"):
        SectionLineSegment2D(cast(SectionPoint2D, "start"), SectionPoint2D(1.0, 0.0))
    with pytest.raises(TypeError, match="end"):
        SectionLineSegment2D(point, cast(SectionPoint2D, "end"))
    with pytest.raises(ValueError, match="distinct"):
        SectionLineSegment2D(point, point)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Annulus2D(cast(SectionPoint2D, "center"), 2.0, 1.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), cast(float, True), 1.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), math.inf, 1.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 0.0, 0.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, cast(float, "1")),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, math.nan),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, -1.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, 2.0),
        lambda: Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, 3.0),
    ],
)
def test_annulus_rejects_invalid_center_or_radii(factory: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_zero_inner_radius_is_valid_for_primitive_but_not_standard_round_factory() -> None:
    assert Annulus2D(SectionPoint2D(0.0, 0.0), 2.0, 0.0).inner_radius == 0.0
    with pytest.raises(ValueError, match="positive inner radius"):
        RoundTubeDimensions(4.0, 2.0)

    topology = _topology(SectionFamily.ROUND_TUBE)
    valid = create_round_tube_geometry(topology, RoundTubeDimensions(10.0, 1.0))
    solid = Annulus2D(SectionPoint2D(0.0, 0.0), 5.0, 0.0)
    with pytest.raises(ValueError, match="positive inner radius"):
        replace(
            valid,
            physical_elements=(PhysicalElementGeometry2D("CURVED_WALL", (solid,)),),
        )


def test_geometry_mapping_deferred_feature_and_void_contracts() -> None:
    rectangle = AxisAlignedRectangle2D(-1.0, 1.0, -1.0, 1.0)
    mapping = PhysicalElementGeometry2D("ELEMENT", (rectangle,))
    feature = DeferredSectionFeature2D(
        "FEATURE",
        DeferredSectionFeatureKind.CUSTOM_DEFERRED,
        "Feature",
        rectangle,
    )
    nominal_void = SectionVoid2D("VOID", "Void", rectangle)

    assert mapping.is_targetable
    assert feature.is_deferred
    assert not feature.is_targetable
    assert nominal_void.geometry is rectangle
    assert not hasattr(mapping, "__dict__")
    with pytest.raises(FrozenInstanceError):
        feature.label = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PhysicalElementGeometry2D("bad/id", (AxisAlignedRectangle2D(0, 1, 0, 1),)),
        lambda: PhysicalElementGeometry2D("ELEMENT", cast(tuple[AxisAlignedRectangle2D, ...], [])),
        lambda: PhysicalElementGeometry2D("ELEMENT", ()),
        lambda: PhysicalElementGeometry2D("ELEMENT", (cast(AxisAlignedRectangle2D, "bad"),)),
        lambda: DeferredSectionFeature2D(
            "bad/id",
            DeferredSectionFeatureKind.CUSTOM_DEFERRED,
            "Feature",
            AxisAlignedRectangle2D(0, 1, 0, 1),
        ),
        lambda: DeferredSectionFeature2D(
            "FEATURE",
            cast(DeferredSectionFeatureKind, "CUSTOM_DEFERRED"),
            "Feature",
            AxisAlignedRectangle2D(0, 1, 0, 1),
        ),
        lambda: DeferredSectionFeature2D(
            "FEATURE",
            DeferredSectionFeatureKind.CUSTOM_DEFERRED,
            " ",
            AxisAlignedRectangle2D(0, 1, 0, 1),
        ),
        lambda: DeferredSectionFeature2D(
            "FEATURE",
            DeferredSectionFeatureKind.CUSTOM_DEFERRED,
            "Feature",
            cast(AxisAlignedRectangle2D, "bad"),
        ),
        lambda: SectionVoid2D("bad/id", "Void", AxisAlignedRectangle2D(0, 1, 0, 1)),
        lambda: SectionVoid2D("VOID", " ", AxisAlignedRectangle2D(0, 1, 0, 1)),
        lambda: SectionVoid2D("VOID", "Void", cast(AxisAlignedRectangle2D, "bad")),
    ],
)
def test_geometry_mapping_feature_and_void_reject_invalid_forms(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ISectionDimensions(12.0, 8.0, 2.0, 1.0),
        lambda: ChannelDimensions(12.0, 8.0, 2.0, 1.0),
        lambda: TeeDimensions(12.0, 8.0, 2.0, 1.0),
        lambda: RectangularTubeDimensions(10.0, 8.0, 1.0),
        lambda: AngleDimensions(8.0, 6.0, 1.0),
        lambda: PlateDimensions(8.0, 2.0),
        lambda: RoundTubeDimensions(10.0, 1.0),
    ],
)
def test_dimension_contracts_accept_exact_valid_values(factory: Callable[[], object]) -> None:
    value = factory()
    assert not hasattr(value, "__dict__")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ISectionDimensions(2.0, 8.0, 2.0, 1.0),
        lambda: ISectionDimensions(12.0, 2.0, 2.0, 1.0),
        lambda: ChannelDimensions(2.0, 8.0, 2.0, 1.0),
        lambda: ChannelDimensions(12.0, 2.0, 2.0, 1.0),
        lambda: TeeDimensions(1.0, 8.0, 2.0, 1.0),
        lambda: TeeDimensions(12.0, 2.0, 2.0, 1.0),
        lambda: RectangularTubeDimensions(2.0, 8.0, 1.0),
        lambda: RectangularTubeDimensions(10.0, 2.0, 1.0),
        lambda: AngleDimensions(1.0, 6.0, 1.0),
        lambda: AngleDimensions(8.0, 1.0, 1.0),
        lambda: RoundTubeDimensions(2.0, 1.0),
    ],
)
def test_dimension_contracts_reject_exact_degenerate_boundaries(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError, match=r"requires|positive"):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ISectionDimensions(0.0, 8.0, 2.0, 1.0),
        lambda: ISectionDimensions(12.0, -8.0, 2.0, 1.0),
        lambda: ISectionDimensions(12.0, 8.0, math.nan, 1.0),
        lambda: ISectionDimensions(12.0, 8.0, 2.0, cast(float, True)),
        lambda: ChannelDimensions(math.inf, 8.0, 2.0, 1.0),
        lambda: ChannelDimensions(12.0, 0.0, 2.0, 1.0),
        lambda: ChannelDimensions(12.0, 8.0, -2.0, 1.0),
        lambda: ChannelDimensions(12.0, 8.0, 2.0, 0.0),
        lambda: TeeDimensions(0.0, 8.0, 2.0, 1.0),
        lambda: TeeDimensions(12.0, 0.0, 2.0, 1.0),
        lambda: TeeDimensions(12.0, 8.0, 0.0, 1.0),
        lambda: TeeDimensions(12.0, 8.0, 2.0, 0.0),
        lambda: RectangularTubeDimensions(0.0, 8.0, 1.0),
        lambda: RectangularTubeDimensions(10.0, 0.0, 1.0),
        lambda: RectangularTubeDimensions(10.0, 8.0, 0.0),
        lambda: AngleDimensions(0.0, 6.0, 1.0),
        lambda: AngleDimensions(8.0, 0.0, 1.0),
        lambda: AngleDimensions(8.0, 6.0, 0.0),
        lambda: PlateDimensions(0.0, 2.0),
        lambda: PlateDimensions(8.0, 0.0),
        lambda: RoundTubeDimensions(0.0, 1.0),
        lambda: RoundTubeDimensions(10.0, 0.0),
    ],
)
def test_dimensions_reject_nonpositive_nonfinite_and_boolean_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_dimension_boundaries_are_strict_without_rounding_swapping_or_conversion() -> None:
    just_above_two = math.nextafter(2.0, math.inf)
    just_above_one = math.nextafter(1.0, math.inf)

    assert ISectionDimensions(just_above_two, just_above_two, 2.0, 1.0).overall_depth == (
        just_above_two
    )
    assert ChannelDimensions(just_above_two, just_above_two, 2.0, 1.0).flange_width == (
        just_above_two
    )
    assert TeeDimensions(just_above_one, just_above_two, 2.0, 1.0).overall_depth == (just_above_one)
    assert RectangularTubeDimensions(just_above_two, just_above_two, 1.0).outside_width == (
        just_above_two
    )
    assert AngleDimensions(just_above_one, just_above_one, 1.0).leg_y == just_above_one
    with pytest.raises(TypeError):
        PlateDimensions(cast(float, "8"), 2.0)


@pytest.mark.parametrize(
    ("factory", "field_pattern"),
    [
        (
            lambda: ISectionDimensions(1.0, 1.0, 0.25, math.ulp(0.0)),
            r"ISectionDimensions\.flange_thickness",
        ),
        (
            lambda: ChannelDimensions(1.0, 1.0, 0.25, math.ulp(0.0)),
            r"ChannelDimensions\.flange_thickness",
        ),
        (
            lambda: TeeDimensions(1.0, 1.0, 0.25, math.ulp(0.0)),
            r"TeeDimensions\.flange_thickness",
        ),
        (
            lambda: RectangularTubeDimensions(1.0, 1.0, math.ulp(0.0)),
            r"RectangularTubeDimensions\.wall_thickness",
        ),
        (
            lambda: AngleDimensions(1.0, 1.0, math.ulp(0.0)),
            r"AngleDimensions\.thickness",
        ),
        (
            lambda: PlateDimensions(1.0, math.ulp(0.0)),
            r"PlateDimensions\.thickness",
        ),
    ],
)
def test_flat_dimension_families_reject_unrepresentable_positive_spans(
    factory: Callable[[], object],
    field_pattern: str,
) -> None:
    with pytest.raises(ValueError, match=field_pattern):
        factory()


@pytest.mark.parametrize(
    ("factory", "field_pattern"),
    [
        (
            lambda: ISectionDimensions(12.0, 8.0, 0.0, 1.0),
            r"ISectionDimensions\.web_thickness",
        ),
        (
            lambda: ChannelDimensions(12.0, 8.0, 0.0, 1.0),
            r"ChannelDimensions\.web_thickness",
        ),
        (
            lambda: TeeDimensions(12.0, 8.0, 0.0, 1.0),
            r"TeeDimensions\.stem_thickness",
        ),
    ],
)
def test_flanged_dimension_diagnostics_name_the_public_thickness_field(
    factory: Callable[[], object],
    field_pattern: str,
) -> None:
    with pytest.raises(ValueError, match=field_pattern):
        factory()


def test_channel_offset_web_uses_actual_representable_coordinates() -> None:
    smallest = math.ulp(0.0)
    dimensions = ChannelDimensions(1.0, 2.0 * smallest, smallest, 0.25)
    geometry = create_channel_geometry(_topology(SectionFamily.CHANNEL), dimensions)

    assert _rectangle(geometry, "WEB") == AxisAlignedRectangle2D(-smallest, 0.0, -0.25, 0.25)
    assert _void(geometry, "CHANNEL_OPENING").geometry == AxisAlignedRectangle2D(
        0.0, smallest, -0.25, 0.25
    )


def test_channel_offset_web_rejects_coordinate_collapse_at_large_scale() -> None:
    with pytest.raises(ValueError, match=r"ChannelDimensions\.web_thickness"):
        ChannelDimensions(12.0, 1.0e308, 1.0, 1.0)


def test_round_tube_rejects_wall_span_collapse_at_large_scale() -> None:
    with pytest.raises(ValueError, match=r"RoundTubeDimensions\.wall_thickness"):
        RoundTubeDimensions(1.0e308, 1.0)


@pytest.mark.parametrize(
    ("factory", "field_pattern"),
    [
        (
            lambda: ISectionDimensions(
                3.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                2.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"ISectionDimensions\.overall_depth.*exactly representable half-dimension",
        ),
        (
            lambda: ISectionDimensions(
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"ISectionDimensions\.flange_width.*exactly representable half-dimension",
        ),
        (
            lambda: ISectionDimensions(
                4.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"ISectionDimensions\.web_thickness.*exactly representable half-dimension",
        ),
        (
            lambda: ChannelDimensions(
                3.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"ChannelDimensions\.overall_depth.*exactly representable half-dimension",
        ),
        (
            lambda: ChannelDimensions(
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"ChannelDimensions\.flange_width.*exactly representable half-dimension",
        ),
        (
            lambda: TeeDimensions(
                3.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                2.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"TeeDimensions\.overall_depth.*exactly representable half-dimension",
        ),
        (
            lambda: TeeDimensions(
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"TeeDimensions\.flange_width.*exactly representable half-dimension",
        ),
        (
            lambda: TeeDimensions(
                4.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"TeeDimensions\.stem_thickness.*exactly representable half-dimension",
        ),
        (
            lambda: RectangularTubeDimensions(
                3.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"RectangularTubeDimensions\.outside_width.*exactly representable half-dimension",
        ),
        (
            lambda: RectangularTubeDimensions(
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"RectangularTubeDimensions\.outside_depth.*exactly representable half-dimension",
        ),
        (
            lambda: AngleDimensions(
                3.0 * math.ulp(0.0),
                4.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"AngleDimensions\.leg_y.*exactly representable half-dimension",
        ),
        (
            lambda: AngleDimensions(
                4.0 * math.ulp(0.0),
                3.0 * math.ulp(0.0),
                math.ulp(0.0),
            ),
            r"AngleDimensions\.leg_z.*exactly representable half-dimension",
        ),
        (
            lambda: PlateDimensions(3.0 * math.ulp(0.0), 4.0 * math.ulp(0.0)),
            r"PlateDimensions\.width.*exactly representable half-dimension",
        ),
        (
            lambda: PlateDimensions(4.0 * math.ulp(0.0), 3.0 * math.ulp(0.0)),
            r"PlateDimensions\.thickness.*exactly representable half-dimension",
        ),
        (
            lambda: RoundTubeDimensions(3.0 * math.ulp(0.0), math.ulp(0.0)),
            r"RoundTubeDimensions\.outside_diameter.*exactly representable half-dimension",
        ),
    ],
)
def test_centered_dimensions_reject_inexact_subnormal_halves(
    factory: Callable[[], object],
    field_pattern: str,
) -> None:
    with pytest.raises(ValueError, match=field_pattern):
        factory()


def test_tube_and_round_dimension_derived_values_are_exact() -> None:
    rectangle = RectangularTubeDimensions(10.0, 8.0, 1.0)
    square = RectangularTubeDimensions(8.0, 8.0, 1.0)
    round_tube = RoundTubeDimensions(10.0, 1.0)

    assert not rectangle.is_square
    assert square.is_square
    assert round_tube.outer_radius == 5.0
    assert round_tube.inner_radius == 4.0


@pytest.mark.parametrize("family", [SectionFamily.WIDE_FLANGE, SectionFamily.I_SECTION])
def test_w_and_i_geometry_has_exact_bounds_elements_voids_and_junctions(
    family: SectionFamily,
) -> None:
    topology = _topology(family)
    factory = (
        create_wide_flange_geometry
        if family is SectionFamily.WIDE_FLANGE
        else create_i_section_geometry
    )
    geometry = factory(topology, ISectionDimensions(12.0, 8.0, 2.0, 1.0))

    assert geometry.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -6.0, 6.0)
    assert _rectangle(geometry, "TOP_FLANGE") == AxisAlignedRectangle2D(-4.0, 4.0, 5.0, 6.0)
    assert _rectangle(geometry, "BOTTOM_FLANGE") == AxisAlignedRectangle2D(-4.0, 4.0, -6.0, -5.0)
    assert _rectangle(geometry, "WEB") == AxisAlignedRectangle2D(-1.0, 1.0, -5.0, 5.0)
    assert _void(geometry, "LEFT_WEB_VOID").geometry == AxisAlignedRectangle2D(
        -4.0, -1.0, -5.0, 5.0
    )
    assert _void(geometry, "RIGHT_WEB_VOID").geometry == AxisAlignedRectangle2D(1.0, 4.0, -5.0, 5.0)
    assert _deferred(geometry, "TOP_WEB_TO_FLANGE_JUNCTION").geometry == SectionLineSegment2D(
        SectionPoint2D(-1.0, 5.0), SectionPoint2D(1.0, 5.0)
    )
    assert _deferred(geometry, "BOTTOM_WEB_TO_FLANGE_JUNCTION").geometry == SectionLineSegment2D(
        SectionPoint2D(-1.0, -5.0), SectionPoint2D(1.0, -5.0)
    )
    assert tuple(feature.kind for feature in geometry.deferred_features) == (
        DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
        DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
    )
    assert tuple(mapping.element_id for mapping in geometry.physical_elements) == (
        "WEB",
        "TOP_FLANGE",
        "BOTTOM_FLANGE",
    )
    assert (
        topology.elements[1].material_region_id
        == topology.elements[2].material_region_id
        == ("FLANGES")
    )
    assert topology.elements[0].material_region_id == "WEB"
    rectangles = tuple(_rectangle(geometry, element.id) for element in topology.elements)
    assert not any(
        _rectangles_overlap(first, second)
        for index, first in enumerate(rectangles)
        for second in rectangles[index + 1 :]
    )


def test_wide_flange_and_i_structures_are_equivalent_except_family() -> None:
    dimensions = ISectionDimensions(12.0, 8.0, 2.0, 1.0)
    wide = create_wide_flange_geometry(_topology(SectionFamily.WIDE_FLANGE), dimensions)
    general = create_i_section_geometry(_topology(SectionFamily.I_SECTION), dimensions)

    assert replace(wide, section_family=SectionFamily.I_SECTION) == general


def test_channel_geometry_has_exact_negative_y_web_positive_y_opening() -> None:
    topology = _topology(SectionFamily.CHANNEL)
    geometry = create_channel_geometry(topology, ChannelDimensions(12.0, 8.0, 2.0, 1.0))

    assert geometry.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -6.0, 6.0)
    assert _rectangle(geometry, "WEB") == AxisAlignedRectangle2D(-4.0, -2.0, -5.0, 5.0)
    assert _rectangle(geometry, "TOP_FLANGE") == AxisAlignedRectangle2D(-4.0, 4.0, 5.0, 6.0)
    assert _rectangle(geometry, "BOTTOM_FLANGE") == AxisAlignedRectangle2D(-4.0, 4.0, -6.0, -5.0)
    assert _void(geometry, "CHANNEL_OPENING").geometry == AxisAlignedRectangle2D(
        -2.0, 4.0, -5.0, 5.0
    )
    assert _deferred(geometry, "TOP_WEB_TO_FLANGE_JUNCTION").geometry == SectionLineSegment2D(
        SectionPoint2D(-4.0, 5.0), SectionPoint2D(-2.0, 5.0)
    )
    assert _deferred(geometry, "BOTTOM_WEB_TO_FLANGE_JUNCTION").geometry == SectionLineSegment2D(
        SectionPoint2D(-4.0, -5.0), SectionPoint2D(-2.0, -5.0)
    )
    assert tuple(feature.kind for feature in geometry.deferred_features) == (
        DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
        DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
    )
    assert topology.elements[1].id != topology.elements[2].id
    assert (
        topology.elements[1].material_region_id
        == topology.elements[2].material_region_id
        == ("FLANGES")
    )


def test_tee_geometry_has_exact_positive_z_flange_and_negative_z_stem() -> None:
    topology = _topology(SectionFamily.TEE)
    geometry = create_tee_geometry(topology, TeeDimensions(12.0, 8.0, 2.0, 1.0))

    assert geometry.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -6.0, 6.0)
    assert _rectangle(geometry, "FLANGE") == AxisAlignedRectangle2D(-4.0, 4.0, 5.0, 6.0)
    assert _rectangle(geometry, "STEM") == AxisAlignedRectangle2D(-1.0, 1.0, -6.0, 5.0)
    assert _void(geometry, "LEFT_STEM_VOID").geometry == AxisAlignedRectangle2D(
        -4.0, -1.0, -6.0, 5.0
    )
    assert _void(geometry, "RIGHT_STEM_VOID").geometry == AxisAlignedRectangle2D(
        1.0, 4.0, -6.0, 5.0
    )
    assert _deferred(geometry, "STEM_TO_FLANGE_JUNCTION").geometry == SectionLineSegment2D(
        SectionPoint2D(-1.0, 5.0), SectionPoint2D(1.0, 5.0)
    )
    assert tuple(feature.kind for feature in geometry.deferred_features) == (
        DeferredSectionFeatureKind.STEM_TO_FLANGE_JUNCTION,
    )
    validate_cross_section_topology(geometry, topology)


def test_rectangular_tube_exact_walls_corners_opening_and_membership() -> None:
    topology = _topology(SectionFamily.RECTANGULAR_TUBE)
    geometry = create_rectangular_tube_geometry(topology, RectangularTubeDimensions(10.0, 8.0, 1.0))
    expected_walls = {
        "TOP_WALL": AxisAlignedRectangle2D(-4.0, 4.0, 3.0, 4.0),
        "BOTTOM_WALL": AxisAlignedRectangle2D(-4.0, 4.0, -4.0, -3.0),
        "SIDE_WALL_1": AxisAlignedRectangle2D(-5.0, -4.0, -3.0, 3.0),
        "SIDE_WALL_2": AxisAlignedRectangle2D(4.0, 5.0, -3.0, 3.0),
    }
    expected_corners = {
        "CORNER_NEGATIVE_Y_NEGATIVE_Z": AxisAlignedRectangle2D(-5.0, -4.0, -4.0, -3.0),
        "CORNER_POSITIVE_Y_NEGATIVE_Z": AxisAlignedRectangle2D(4.0, 5.0, -4.0, -3.0),
        "CORNER_NEGATIVE_Y_POSITIVE_Z": AxisAlignedRectangle2D(-5.0, -4.0, 3.0, 4.0),
        "CORNER_POSITIVE_Y_POSITIVE_Z": AxisAlignedRectangle2D(4.0, 5.0, 3.0, 4.0),
    }

    assert geometry.outside_bounds == SectionBoundingBox2D(-5.0, 5.0, -4.0, 4.0)
    assert _void(geometry, "TUBE_INSIDE_OPENING").geometry == AxisAlignedRectangle2D(
        -4.0, 4.0, -3.0, 3.0
    )
    assert {item.element_id: item.geometry[0] for item in geometry.physical_elements} == (
        expected_walls
    )
    assert {item.id: item.geometry for item in geometry.deferred_features} == expected_corners
    assert (
        tuple(feature.kind for feature in geometry.deferred_features)
        == (DeferredSectionFeatureKind.RECTANGULAR_TUBE_CORNER,) * 4
    )
    assert all(not item.is_targetable and item.is_deferred for item in geometry.deferred_features)
    assert (
        sum(
            (rectangle.max_y - rectangle.min_y) * (rectangle.max_z - rectangle.min_z)
            for rectangle in (*expected_walls.values(), *expected_corners.values())
        )
        == 32.0
    )
    assert (
        topology.elements[0].material_region_id
        == topology.elements[1].material_region_id
        == ("WALL_PAIR_1")
    )
    assert (
        topology.elements[2].material_region_id
        == topology.elements[3].material_region_id
        == ("WALL_PAIR_2")
    )
    occupied = (*expected_walls.values(), *expected_corners.values())
    assert not any(
        _rectangles_overlap(first, second)
        for index, first in enumerate(occupied)
        for second in occupied[index + 1 :]
    )


def test_square_tube_uses_rectangular_contract_and_rejects_nonsquare_dimensions() -> None:
    topology = _topology(SectionFamily.RECTANGULAR_TUBE)
    dimensions = RectangularTubeDimensions(8.0, 8.0, 1.0)

    assert create_square_tube_geometry(topology, dimensions) == create_rectangular_tube_geometry(
        topology, dimensions
    )
    with pytest.raises(TypeError, match="RectangularTubeDimensions"):
        create_square_tube_geometry(topology, cast(RectangularTubeDimensions, "dimensions"))
    with pytest.raises(ValueError, match="equal"):
        create_square_tube_geometry(topology, RectangularTubeDimensions(10.0, 8.0, 1.0))


def test_angle_geometry_exact_legs_deferred_heel_open_area_and_membership() -> None:
    topology = _topology(SectionFamily.ANGLE)
    geometry = create_angle_geometry(topology, AngleDimensions(8.0, 6.0, 1.0))
    leg_1 = AxisAlignedRectangle2D(-3.0, 4.0, -3.0, -2.0)
    leg_2 = AxisAlignedRectangle2D(-4.0, -3.0, -2.0, 3.0)
    heel = AxisAlignedRectangle2D(-4.0, -3.0, -3.0, -2.0)
    open_area = AxisAlignedRectangle2D(-3.0, 4.0, -2.0, 3.0)

    assert geometry.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -3.0, 3.0)
    assert _rectangle(geometry, "LEG_1") == leg_1
    assert _rectangle(geometry, "LEG_2") == leg_2
    assert _deferred(geometry, "ANGLE_HEEL").geometry == heel
    assert _deferred(geometry, "ANGLE_HEEL").kind is DeferredSectionFeatureKind.ANGLE_HEEL
    assert _void(geometry, "ANGLE_OPEN_AREA").geometry == open_area
    assert not _rectangles_overlap(leg_1, leg_2)
    assert not _rectangles_overlap(heel, leg_1)
    assert not _rectangles_overlap(heel, leg_2)
    assert (
        sum(
            (rectangle.max_y - rectangle.min_y) * (rectangle.max_z - rectangle.min_z)
            for rectangle in (leg_1, leg_2, heel)
        )
        == 13.0
    )
    assert not _deferred(geometry, "ANGLE_HEEL").is_targetable
    assert topology.elements[0].material_region_id == "LEG_1"
    assert topology.elements[1].material_region_id == "LEG_2"


def test_plate_and_doubler_are_exact_centered_y_width_z_thickness_profiles() -> None:
    topology = _topology(SectionFamily.PLATE)
    dimensions = PlateDimensions(8.0, 2.0)
    plate = create_plate_geometry(topology, dimensions)
    doubler = create_doubler_geometry(topology, dimensions)

    assert plate == doubler
    assert plate.outside_bounds == SectionBoundingBox2D(-4.0, 4.0, -1.0, 1.0)
    assert _rectangle(plate, "PLATE") == AxisAlignedRectangle2D(-4.0, 4.0, -1.0, 1.0)
    assert plate.deferred_features == ()
    assert plate.nominal_voids == ()
    assert {field.name for field in fields(PlateDimensions)} == {"width", "thickness"}


def test_round_tube_is_one_exact_analytic_annulus_with_cylindrical_membership() -> None:
    orientation = CylindricalMaterialOrientation()
    topology = create_standard_section_topology(
        SectionFamily.ROUND_TUBE,
        orientations={MaterialRegionRole.CYLINDRICAL_WALL: orientation},
    )
    geometry = create_round_tube_geometry(topology, RoundTubeDimensions(10.0, 1.0))
    primitive = geometry.physical_elements[0].geometry[0]

    assert primitive == Annulus2D(SectionPoint2D(0.0, 0.0), 5.0, 4.0)
    assert geometry.outside_bounds == SectionBoundingBox2D(-5.0, 5.0, -5.0, 5.0)
    assert geometry.geometry_idealization is GeometryIdealization.ANALYTIC_ANNULUS
    assert geometry.profile_kind is ProfileRepresentationKind.ANALYTIC_ANNULUS
    assert geometry.physical_elements[0].element_id == "CURVED_WALL"
    assert geometry.deferred_features == ()
    assert geometry.nominal_voids == ()
    assert topology.material_regions[0].role is MaterialRegionRole.CYLINDRICAL_WALL
    assert topology.material_regions[0].orientation is orientation
    assert isinstance(primitive, Annulus2D)
    assert not hasattr(primitive, "vertices")


@pytest.mark.parametrize(
    ("family", "dimensions", "factory"),
    [
        (
            SectionFamily.WIDE_FLANGE,
            ISectionDimensions(12.0, 8.0, 2.0, 1.0),
            create_wide_flange_geometry,
        ),
        (
            SectionFamily.I_SECTION,
            ISectionDimensions(12.0, 8.0, 2.0, 1.0),
            create_i_section_geometry,
        ),
        (
            SectionFamily.CHANNEL,
            ChannelDimensions(12.0, 8.0, 2.0, 1.0),
            create_channel_geometry,
        ),
        (SectionFamily.TEE, TeeDimensions(12.0, 8.0, 2.0, 1.0), create_tee_geometry),
        (
            SectionFamily.RECTANGULAR_TUBE,
            RectangularTubeDimensions(10.0, 8.0, 1.0),
            create_rectangular_tube_geometry,
        ),
        (SectionFamily.ANGLE, AngleDimensions(8.0, 6.0, 1.0), create_angle_geometry),
        (SectionFamily.PLATE, PlateDimensions(8.0, 2.0), create_plate_geometry),
        (
            SectionFamily.ROUND_TUBE,
            RoundTubeDimensions(10.0, 1.0),
            create_round_tube_geometry,
        ),
    ],
)
def test_factories_are_deterministic_immutable_and_preserve_supplied_topology(
    family: SectionFamily,
    dimensions: object,
    factory: Callable[[SectionTopology, object], CrossSectionGeometry2D],
) -> None:
    topology = _topology(family)
    original = topology

    first = factory(topology, dimensions)
    second = factory(topology, dimensions)

    assert first == second
    assert topology == original
    assert isinstance(first.physical_elements, tuple)
    assert isinstance(first.deferred_features, tuple)
    assert isinstance(first.nominal_voids, tuple)
    assert not hasattr(first, "__dict__")
    with pytest.raises(FrozenInstanceError):
        first.section_family = SectionFamily.CUSTOM  # type: ignore[misc]


@pytest.mark.parametrize(
    ("family", "dimensions", "factory"),
    [
        (
            SectionFamily.WIDE_FLANGE,
            cast(ISectionDimensions, "dimensions"),
            create_wide_flange_geometry,
        ),
        (
            SectionFamily.I_SECTION,
            cast(ISectionDimensions, "dimensions"),
            create_i_section_geometry,
        ),
        (
            SectionFamily.CHANNEL,
            cast(ChannelDimensions, "dimensions"),
            create_channel_geometry,
        ),
        (SectionFamily.TEE, cast(TeeDimensions, "dimensions"), create_tee_geometry),
        (
            SectionFamily.RECTANGULAR_TUBE,
            cast(RectangularTubeDimensions, "dimensions"),
            create_rectangular_tube_geometry,
        ),
        (SectionFamily.ANGLE, cast(AngleDimensions, "dimensions"), create_angle_geometry),
        (SectionFamily.PLATE, cast(PlateDimensions, "dimensions"), create_plate_geometry),
        (
            SectionFamily.ROUND_TUBE,
            cast(RoundTubeDimensions, "dimensions"),
            create_round_tube_geometry,
        ),
    ],
)
def test_factories_reject_untyped_dimension_objects(
    family: SectionFamily,
    dimensions: object,
    factory: Callable[[SectionTopology, object], CrossSectionGeometry2D],
) -> None:
    with pytest.raises(TypeError, match="dimensions"):
        factory(_topology(family), dimensions)


def test_standard_factories_reject_untyped_custom_wrong_and_noncanonical_topologies() -> None:
    dimensions = PlateDimensions(8.0, 2.0)
    canonical = _topology(SectionFamily.PLATE)
    malformed = replace(
        canonical,
        elements=(replace(canonical.elements[0], role=PhysicalSectionElementRole.CUSTOM),),
    )
    wide_topology = _topology(SectionFamily.WIDE_FLANGE)
    wrong_membership = replace(
        wide_topology,
        elements=(
            wide_topology.elements[0],
            replace(wide_topology.elements[1], material_region_id="WEB"),
            wide_topology.elements[2],
        ),
    )

    with pytest.raises(TypeError, match="SectionTopology"):
        create_plate_geometry(cast(SectionTopology, "topology"), dimensions)
    with pytest.raises(ValueError, match="STANDARD"):
        create_plate_geometry(_custom_topology(), dimensions)
    with pytest.raises(ValueError, match="PLATE"):
        create_plate_geometry(_topology(SectionFamily.ANGLE), dimensions)
    with pytest.raises(ValueError, match="canonical"):
        create_plate_geometry(malformed, dimensions)
    with pytest.raises(ValueError, match="canonical"):
        create_wide_flange_geometry(
            wrong_membership,
            ISectionDimensions(12.0, 8.0, 2.0, 1.0),
        )


def test_topology_labels_and_orientations_are_accepted_but_mapping_stays_in_topology() -> None:
    orientation = PlanarFixedMaterialOrientation(
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )
    topology = create_standard_section_topology(
        SectionFamily.PLATE,
        orientations={MaterialRegionRole.PLATE: orientation},
    )
    topology = replace(
        topology,
        elements=(replace(topology.elements[0], label="Custom plate label"),),
        material_regions=(replace(topology.material_regions[0], label="Custom region label"),),
    )

    geometry = create_plate_geometry(topology, PlateDimensions(8.0, 2.0))

    assert geometry.physical_elements[0].element_id == topology.elements[0].id
    assert topology.elements[0].material_region_id == topology.material_regions[0].id
    assert topology.material_regions[0].orientation is orientation
    geometry_field_names = {field.name for field in fields(CrossSectionGeometry2D)}
    assert "material_regions" not in geometry_field_names
    assert "material_region_id" not in geometry_field_names


def test_validate_cross_section_topology_rejects_invalid_types_and_sources() -> None:
    plate = _plate_geometry()
    topology = _topology(SectionFamily.PLATE)

    with pytest.raises(TypeError, match="geometry"):
        validate_cross_section_topology(cast(CrossSectionGeometry2D, "geometry"), topology)
    with pytest.raises(TypeError, match="topology"):
        validate_cross_section_topology(plate, cast(SectionTopology, "topology"))
    with pytest.raises(ValueError, match="custom"):
        validate_cross_section_topology(plate, _custom_topology())
    with pytest.raises(ValueError, match="families"):
        validate_cross_section_topology(plate, _topology(SectionFamily.ANGLE))


def test_validate_cross_section_topology_rejects_noncanonical_missing_and_unknown_mappings() -> (
    None
):
    plate = _plate_geometry()
    plate_topology = _topology(SectionFamily.PLATE)
    malformed = replace(
        plate_topology,
        elements=(replace(plate_topology.elements[0], role=PhysicalSectionElementRole.CUSTOM),),
    )
    wrong_id = replace(
        plate,
        physical_elements=(
            PhysicalElementGeometry2D("UNKNOWN", plate.physical_elements[0].geometry),
        ),
    )
    wide_topology = _topology(SectionFamily.WIDE_FLANGE)
    wide = create_wide_flange_geometry(
        wide_topology,
        ISectionDimensions(12.0, 8.0, 2.0, 1.0),
    )
    missing = replace(wide, physical_elements=wide.physical_elements[:-1])

    with pytest.raises(ValueError, match="canonical"):
        validate_cross_section_topology(plate, malformed)
    with pytest.raises(ValueError, match="exactly once"):
        validate_cross_section_topology(wrong_id, plate_topology)
    with pytest.raises(ValueError, match="exactly once"):
        validate_cross_section_topology(missing, wide_topology)


def test_cross_section_collection_structure_is_strict() -> None:
    base = _plate_geometry()
    rectangle = AxisAlignedRectangle2D(-4.0, 4.0, -1.0, 1.0)
    feature = DeferredSectionFeature2D(
        "FEATURE",
        DeferredSectionFeatureKind.CUSTOM_DEFERRED,
        "Feature",
        SectionLineSegment2D(SectionPoint2D(-1.0, 0.0), SectionPoint2D(1.0, 0.0)),
    )
    nominal_void = SectionVoid2D("VOID", "Void", AxisAlignedRectangle2D(-1.0, 1.0, -0.5, 0.5))

    invalid_changes: tuple[dict[str, object], ...] = (
        {"construction_datum": "point"},
        {"outside_bounds": "bounds"},
        {"section_family": "PLATE"},
        {"section_family": SectionFamily.CUSTOM},
        {"geometry_idealization": "NOMINAL_SHARP_CORNER"},
        {"profile_kind": "RECTANGULAR_COMPOSITE"},
        {"construction_datum": SectionPoint2D(1.0, 0.0)},
        {"outside_bounds": SectionBoundingBox2D(-5.0, 4.0, -1.0, 1.0)},
        {"physical_elements": []},
        {"physical_elements": ()},
        {"physical_elements": ("mapping",)},
        {
            "physical_elements": (
                base.physical_elements[0],
                PhysicalElementGeometry2D("PLATE", (rectangle,)),
            )
        },
        {"deferred_features": []},
        {"deferred_features": ("feature",)},
        {"deferred_features": (feature, replace(feature, label="Duplicate"))},
        {"nominal_voids": []},
        {"nominal_voids": ("void",)},
        {"nominal_voids": (nominal_void, replace(nominal_void, label="Duplicate"))},
    )

    for changes in invalid_changes:
        with pytest.raises((TypeError, ValueError)):
            replace(base, **changes)  # type: ignore[arg-type]


def test_cross_section_rejects_invalid_round_and_flat_profile_representations() -> None:
    plate = _plate_geometry()
    round_topology = _topology(SectionFamily.ROUND_TUBE)
    round_geometry = create_round_tube_geometry(round_topology, RoundTubeDimensions(10.0, 1.0))
    annulus = cast(Annulus2D, round_geometry.physical_elements[0].geometry[0])
    rectangle = AxisAlignedRectangle2D(-1.0, 1.0, -1.0, 1.0)

    invalid_round_changes: tuple[dict[str, object], ...] = (
        {"geometry_idealization": GeometryIdealization.NOMINAL_SHARP_CORNER},
        {"profile_kind": ProfileRepresentationKind.RECTANGULAR_COMPOSITE},
        {
            "physical_elements": (
                round_geometry.physical_elements[0],
                PhysicalElementGeometry2D("EXTRA", (rectangle,)),
            )
        },
        {"physical_elements": (PhysicalElementGeometry2D("CURVED_WALL", (annulus, annulus)),)},
        {"physical_elements": (PhysicalElementGeometry2D("CURVED_WALL", (rectangle,)),)},
        {
            "deferred_features": (
                DeferredSectionFeature2D(
                    "LINE",
                    DeferredSectionFeatureKind.CUSTOM_DEFERRED,
                    "Line",
                    SectionLineSegment2D(SectionPoint2D(-1.0, 0.0), SectionPoint2D(1.0, 0.0)),
                ),
            )
        },
        {
            "nominal_voids": (
                SectionVoid2D("VOID", "Void", AxisAlignedRectangle2D(-1.0, 1.0, -1.0, 1.0)),
            )
        },
        {
            "physical_elements": (
                PhysicalElementGeometry2D(
                    "CURVED_WALL",
                    (Annulus2D(SectionPoint2D(1.0, 0.0), 5.0, 4.0),),
                ),
            )
        },
        {"outside_bounds": SectionBoundingBox2D(-6.0, 6.0, -5.0, 5.0)},
    )
    for changes in invalid_round_changes:
        with pytest.raises(ValueError, match=r"[Rr]ound-tube|Annulus"):
            replace(round_geometry, **changes)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="sharp-corner"):
        replace(plate, geometry_idealization=GeometryIdealization.ANALYTIC_ANNULUS)
    with pytest.raises(ValueError, match="sharp-corner"):
        replace(plate, profile_kind=ProfileRepresentationKind.ANALYTIC_ANNULUS)
    with pytest.raises(ValueError, match="annulus"):
        replace(
            plate,
            physical_elements=(PhysicalElementGeometry2D("PLATE", (annulus,)),),
        )


def _flat_custom_geometry(
    *,
    physical: tuple[PhysicalElementGeometry2D, ...],
    deferred: tuple[DeferredSectionFeature2D, ...] = (),
    voids: tuple[SectionVoid2D, ...] = (),
) -> CrossSectionGeometry2D:
    return CrossSectionGeometry2D(
        construction_datum=SectionPoint2D(0.0, 0.0),
        outside_bounds=SectionBoundingBox2D(-5.0, 5.0, -5.0, 5.0),
        section_family=SectionFamily.PLATE,
        geometry_idealization=GeometryIdealization.NOMINAL_SHARP_CORNER,
        physical_elements=physical,
        deferred_features=deferred,
        nominal_voids=voids,
        profile_kind=ProfileRepresentationKind.RECTANGULAR_COMPOSITE,
    )


def test_cross_section_rejects_out_of_bounds_rectangles_and_lines() -> None:
    physical = (
        PhysicalElementGeometry2D(
            "PHYSICAL",
            (AxisAlignedRectangle2D(-1.0, 1.0, -1.0, 1.0),),
        ),
    )
    outside_rectangle = AxisAlignedRectangle2D(-6.0, -5.5, -1.0, 1.0)
    outside_line = SectionLineSegment2D(SectionPoint2D(-6.0, 0.0), SectionPoint2D(0.0, 0.0))

    with pytest.raises(ValueError, match="within outside bounds"):
        _flat_custom_geometry(
            physical=(PhysicalElementGeometry2D("PHYSICAL", (outside_rectangle,)),)
        )
    with pytest.raises(ValueError, match="within outside bounds"):
        _flat_custom_geometry(
            physical=physical,
            deferred=(
                DeferredSectionFeature2D(
                    "OUTSIDE",
                    DeferredSectionFeatureKind.CUSTOM_DEFERRED,
                    "Outside",
                    outside_line,
                ),
            ),
        )


def test_cross_section_rejects_every_interior_overlap_category() -> None:
    first = AxisAlignedRectangle2D(-4.0, 1.0, -1.0, 1.0)
    overlap = AxisAlignedRectangle2D(0.0, 4.0, -1.0, 1.0)
    separate = AxisAlignedRectangle2D(2.0, 4.0, 2.0, 4.0)
    physical = (PhysicalElementGeometry2D("FIRST", (first,)),)

    with pytest.raises(ValueError, match="Physical-element"):
        _flat_custom_geometry(physical=(PhysicalElementGeometry2D("BOTH", (first, overlap)),))
    with pytest.raises(ValueError, match="Physical-element"):
        _flat_custom_geometry(
            physical=(
                *physical,
                PhysicalElementGeometry2D("SECOND", (overlap,)),
            )
        )
    with pytest.raises(ValueError, match="Deferred finite-area"):
        _flat_custom_geometry(
            physical=physical,
            deferred=(
                DeferredSectionFeature2D(
                    "DEFERRED",
                    DeferredSectionFeatureKind.CUSTOM_DEFERRED,
                    "Deferred",
                    overlap,
                ),
            ),
        )
    with pytest.raises(ValueError, match="each other"):
        _flat_custom_geometry(
            physical=physical,
            deferred=(
                DeferredSectionFeature2D(
                    "FIRST_DEFERRED",
                    DeferredSectionFeatureKind.CUSTOM_DEFERRED,
                    "First deferred",
                    separate,
                ),
                DeferredSectionFeature2D(
                    "SECOND_DEFERRED",
                    DeferredSectionFeatureKind.CUSTOM_DEFERRED,
                    "Second deferred",
                    AxisAlignedRectangle2D(3.0, 4.5, 3.0, 4.5),
                ),
            ),
        )
    with pytest.raises(ValueError, match="occupied"):
        _flat_custom_geometry(
            physical=physical,
            voids=(SectionVoid2D("VOID", "Void", overlap),),
        )
    with pytest.raises(ValueError, match="each other"):
        _flat_custom_geometry(
            physical=physical,
            voids=(
                SectionVoid2D("FIRST_VOID", "First void", separate),
                SectionVoid2D(
                    "SECOND_VOID",
                    "Second void",
                    AxisAlignedRectangle2D(3.0, 4.5, 3.0, 4.5),
                ),
            ),
        )


def test_boundary_contact_is_not_interior_overlap() -> None:
    first = AxisAlignedRectangle2D(-4.0, 0.0, -1.0, 1.0)
    touches_y = AxisAlignedRectangle2D(0.0, 4.0, -1.0, 1.0)
    touches_z = AxisAlignedRectangle2D(-4.0, 0.0, 1.0, 2.0)

    geometry = _flat_custom_geometry(
        physical=(
            PhysicalElementGeometry2D("FIRST", (first,)),
            PhysicalElementGeometry2D("TOUCHES_Y", (touches_y,)),
            PhysicalElementGeometry2D("TOUCHES_Z", (touches_z,)),
        )
    )

    assert len(geometry.physical_elements) == 3


def test_all_standard_datums_are_outside_box_center_not_derived_properties() -> None:
    geometries = (
        create_channel_geometry(
            _topology(SectionFamily.CHANNEL), ChannelDimensions(12.0, 8.0, 2.0, 1.0)
        ),
        create_tee_geometry(_topology(SectionFamily.TEE), TeeDimensions(12.0, 8.0, 2.0, 1.0)),
        create_angle_geometry(_topology(SectionFamily.ANGLE), AngleDimensions(8.0, 6.0, 1.0)),
    )

    for geometry in geometries:
        assert geometry.construction_datum == SectionPoint2D(0.0, 0.0)
        assert geometry.outside_bounds.center == geometry.construction_datum
        field_names = {field.name for field in fields(geometry)}
        assert "centroid" not in field_names
        assert "shear_center" not in field_names
        assert "analytical_line" not in field_names


def test_section_geometry_has_no_property_capacity_or_extrusion_api() -> None:
    forbidden_names = {
        "area",
        "first_moment",
        "first_moments",
        "centroid",
        "shear_center",
        "moment_of_inertia",
        "moments_of_inertia",
        "torsional_constant",
        "warping_constant",
        "section_modulus",
        "radius_of_gyration",
        "plastic_modulus",
        "stress_distribution",
        "capacity",
        "resistance",
        "material_strength",
        "resistance_factor",
        "time_effect_factor",
        "force_distribution",
        "demand_capacity_ratio",
        "utilization",
        "engineering_pass_fail",
        "governing_limit_state",
        "neutral_axis",
        "principal_axes",
        "member_length",
        "local_x_length",
        "extrusion_length",
        "global_position",
        "crosswise_axis",
        "through_thickness_axis",
        "cw_axis",
        "tt_axis",
        "circumferential_evaluation_angle",
        "vertices",
        "mesh",
        "polygon",
    }
    public_names = {
        name
        for contract in (
            CrossSectionGeometry2D,
            SectionPoint2D,
            SectionBoundingBox2D,
            AxisAlignedRectangle2D,
            SectionLineSegment2D,
            Annulus2D,
            PhysicalElementGeometry2D,
            DeferredSectionFeature2D,
            SectionVoid2D,
            ISectionDimensions,
            ChannelDimensions,
            TeeDimensions,
            RectangularTubeDimensions,
            AngleDimensions,
            PlateDimensions,
            RoundTubeDimensions,
        )
        for name in dir(contract)
        if not name.startswith("_")
    }

    assert forbidden_names.isdisjoint(public_names)
