"""Exact nominal two-dimensional standard cross-section geometry."""

import math
from dataclasses import dataclass, field
from enum import StrEnum

from frp_master_connection.domain.section_topology import (
    PhysicalSectionElementRole,
    SectionTopology,
    SectionTopologySource,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import SectionFamily


def _require_finite_real(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number.")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


def _require_positive_dimension(value: float, field_name: str) -> None:
    _require_finite_real(value, field_name)
    if value <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero.")


def _require_representable_positive_span(
    minimum: float,
    maximum: float,
    field_name: str,
) -> None:
    if maximum <= minimum:
        raise ValueError(f"{field_name} must remain representably positive.")


def _exact_half_dimension(value: float, field_name: str) -> float:
    half = value / 2.0
    if half * 2.0 != value:
        raise ValueError(f"{field_name} must have an exactly representable half-dimension.")
    return half


@dataclass(frozen=True, slots=True)
class SectionPoint2D:
    """A finite point in the component-local y-z cross-section plane."""

    y: float
    z: float

    def __post_init__(self) -> None:
        _require_finite_real(self.y, "SectionPoint2D.y")
        _require_finite_real(self.z, "SectionPoint2D.z")


@dataclass(frozen=True, slots=True)
class SectionBoundingBox2D:
    """Exact axis-aligned outside bounds in the local y-z plane."""

    min_y: float
    max_y: float
    min_z: float
    max_z: float

    def __post_init__(self) -> None:
        for field_name, value in (
            ("min_y", self.min_y),
            ("max_y", self.max_y),
            ("min_z", self.min_z),
            ("max_z", self.max_z),
        ):
            _require_finite_real(value, f"SectionBoundingBox2D.{field_name}")
        if self.max_y <= self.min_y:
            raise ValueError("SectionBoundingBox2D requires positive width.")
        if self.max_z <= self.min_z:
            raise ValueError("SectionBoundingBox2D requires positive depth.")

    @property
    def center(self) -> SectionPoint2D:
        """Return the exact outside-bounds construction center."""
        return SectionPoint2D(
            self.min_y / 2.0 + self.max_y / 2.0,
            self.min_z / 2.0 + self.max_z / 2.0,
        )


@dataclass(frozen=True, slots=True)
class AxisAlignedRectangle2D:
    """An exact positive-span rectangle in the local y-z plane."""

    min_y: float
    max_y: float
    min_z: float
    max_z: float

    def __post_init__(self) -> None:
        for field_name, value in (
            ("min_y", self.min_y),
            ("max_y", self.max_y),
            ("min_z", self.min_z),
            ("max_z", self.max_z),
        ):
            _require_finite_real(value, f"AxisAlignedRectangle2D.{field_name}")
        if self.max_y <= self.min_y:
            raise ValueError("AxisAlignedRectangle2D requires positive y span.")
        if self.max_z <= self.min_z:
            raise ValueError("AxisAlignedRectangle2D requires positive z span.")


@dataclass(frozen=True, slots=True)
class SectionLineSegment2D:
    """An exact nonzero line segment used only for deferred boundaries."""

    start: SectionPoint2D
    end: SectionPoint2D

    def __post_init__(self) -> None:
        if not isinstance(self.start, SectionPoint2D):
            raise TypeError("SectionLineSegment2D.start must be a SectionPoint2D.")
        if not isinstance(self.end, SectionPoint2D):
            raise TypeError("SectionLineSegment2D.end must be a SectionPoint2D.")
        if self.start == self.end:
            raise ValueError("SectionLineSegment2D endpoints must be distinct.")


@dataclass(frozen=True, slots=True)
class Annulus2D:
    """An exact analytic annulus with no tessellated representation."""

    center: SectionPoint2D
    outer_radius: float
    inner_radius: float

    def __post_init__(self) -> None:
        if not isinstance(self.center, SectionPoint2D):
            raise TypeError("Annulus2D.center must be a SectionPoint2D.")
        _require_positive_dimension(self.outer_radius, "Annulus2D.outer_radius")
        _require_finite_real(self.inner_radius, "Annulus2D.inner_radius")
        if self.inner_radius < 0.0:
            raise ValueError("Annulus2D.inner_radius must be nonnegative.")
        if self.outer_radius <= self.inner_radius:
            raise ValueError("Annulus2D.outer_radius must exceed inner_radius.")


type PhysicalGeometryPrimitive2D = AxisAlignedRectangle2D | Annulus2D
type DeferredGeometryPrimitive2D = AxisAlignedRectangle2D | SectionLineSegment2D


class DeferredSectionFeatureKind(StrEnum):
    """Controlled kinds of explicitly unsupported junction/corner geometry."""

    ANGLE_HEEL = "ANGLE_HEEL"
    RECTANGULAR_TUBE_CORNER = "RECTANGULAR_TUBE_CORNER"
    WEB_TO_FLANGE_JUNCTION = "WEB_TO_FLANGE_JUNCTION"
    STEM_TO_FLANGE_JUNCTION = "STEM_TO_FLANGE_JUNCTION"
    CUSTOM_DEFERRED = "CUSTOM_DEFERRED"


class GeometryIdealization(StrEnum):
    """Controlled nominal standard-section idealizations."""

    NOMINAL_SHARP_CORNER = "NOMINAL_SHARP_CORNER"
    ANALYTIC_ANNULUS = "ANALYTIC_ANNULUS"


class ProfileRepresentationKind(StrEnum):
    """Exact canonical profile representation kind."""

    RECTANGULAR_COMPOSITE = "RECTANGULAR_COMPOSITE"
    ANALYTIC_ANNULUS = "ANALYTIC_ANNULUS"


@dataclass(frozen=True, slots=True)
class PhysicalElementGeometry2D:
    """Geometry for exactly one existing targetable physical section element."""

    element_id: str
    geometry: tuple[PhysicalGeometryPrimitive2D, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.element_id, "PhysicalElementGeometry2D.element_id")
        require_tuple(self.geometry, "PhysicalElementGeometry2D.geometry")
        if not self.geometry:
            raise ValueError("PhysicalElementGeometry2D.geometry must not be empty.")
        for primitive in self.geometry:
            if not isinstance(primitive, (AxisAlignedRectangle2D, Annulus2D)):
                raise TypeError(
                    "PhysicalElementGeometry2D.geometry items must be exact physical primitives."
                )

    @property
    def is_targetable(self) -> bool:
        """Return the future-targeting status of a physical element."""
        return True


@dataclass(frozen=True, slots=True)
class DeferredSectionFeature2D:
    """A stable deferred geometric feature with no material ownership or targetability."""

    id: str
    kind: DeferredSectionFeatureKind
    label: str
    geometry: DeferredGeometryPrimitive2D
    is_targetable: bool = field(default=False, init=False)
    is_deferred: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        validate_identifier(self.id, "DeferredSectionFeature2D.id")
        require_enum(self.kind, DeferredSectionFeatureKind, "DeferredSectionFeature2D.kind")
        validate_label(self.label, "DeferredSectionFeature2D.label")
        if not isinstance(self.geometry, (AxisAlignedRectangle2D, SectionLineSegment2D)):
            raise TypeError(
                "DeferredSectionFeature2D.geometry must be a rectangle or line segment."
            )


@dataclass(frozen=True, slots=True)
class SectionVoid2D:
    """One exact nominal rectangular opening or missing region."""

    id: str
    label: str
    geometry: AxisAlignedRectangle2D

    def __post_init__(self) -> None:
        validate_identifier(self.id, "SectionVoid2D.id")
        validate_label(self.label, "SectionVoid2D.label")
        if not isinstance(self.geometry, AxisAlignedRectangle2D):
            raise TypeError("SectionVoid2D.geometry must be an AxisAlignedRectangle2D.")


def _rectangles_have_interior_overlap(
    first: AxisAlignedRectangle2D,
    second: AxisAlignedRectangle2D,
) -> bool:
    return max(first.min_y, second.min_y) < min(first.max_y, second.max_y) and max(
        first.min_z, second.min_z
    ) < min(first.max_z, second.max_z)


def _rectangle_is_within_bounds(
    rectangle: AxisAlignedRectangle2D,
    bounds: SectionBoundingBox2D,
) -> bool:
    return (
        rectangle.min_y >= bounds.min_y
        and rectangle.max_y <= bounds.max_y
        and rectangle.min_z >= bounds.min_z
        and rectangle.max_z <= bounds.max_z
    )


def _point_is_within_bounds(
    point: SectionPoint2D,
    bounds: SectionBoundingBox2D,
) -> bool:
    return bounds.min_y <= point.y <= bounds.max_y and bounds.min_z <= point.z <= bounds.max_z


def _physical_rectangles(
    mapping: PhysicalElementGeometry2D,
) -> tuple[AxisAlignedRectangle2D, ...]:
    return tuple(
        primitive for primitive in mapping.geometry if isinstance(primitive, AxisAlignedRectangle2D)
    )


@dataclass(frozen=True, slots=True)
class CrossSectionGeometry2D:
    """Exact nominal standard-section geometry independent of assembly placement."""

    construction_datum: SectionPoint2D
    outside_bounds: SectionBoundingBox2D
    section_family: SectionFamily
    geometry_idealization: GeometryIdealization
    physical_elements: tuple[PhysicalElementGeometry2D, ...]
    deferred_features: tuple[DeferredSectionFeature2D, ...]
    nominal_voids: tuple[SectionVoid2D, ...]
    profile_kind: ProfileRepresentationKind

    def __post_init__(self) -> None:
        if not isinstance(self.construction_datum, SectionPoint2D):
            raise TypeError("CrossSectionGeometry2D.construction_datum must be a SectionPoint2D.")
        if not isinstance(self.outside_bounds, SectionBoundingBox2D):
            raise TypeError("CrossSectionGeometry2D.outside_bounds must be a SectionBoundingBox2D.")
        require_enum(self.section_family, SectionFamily, "CrossSectionGeometry2D.section_family")
        if self.section_family is SectionFamily.CUSTOM:
            raise ValueError("Exact custom cross-section geometry is deferred.")
        require_enum(
            self.geometry_idealization,
            GeometryIdealization,
            "CrossSectionGeometry2D.geometry_idealization",
        )
        require_enum(
            self.profile_kind,
            ProfileRepresentationKind,
            "CrossSectionGeometry2D.profile_kind",
        )
        if self.construction_datum != SectionPoint2D(0.0, 0.0):
            raise ValueError("CrossSectionGeometry2D construction datum must equal (0, 0).")
        if self.outside_bounds.center != self.construction_datum:
            raise ValueError("Outside bounding-box center must equal the construction datum.")

        self._validate_collections()
        self._validate_profile_representation()
        self._validate_profile_consistency()

    def _validate_collections(self) -> None:
        require_tuple(self.physical_elements, "CrossSectionGeometry2D.physical_elements")
        if not self.physical_elements:
            raise ValueError("CrossSectionGeometry2D requires physical-element geometry.")
        for mapping in self.physical_elements:
            if not isinstance(mapping, PhysicalElementGeometry2D):
                raise TypeError(
                    "CrossSectionGeometry2D.physical_elements items must be "
                    "PhysicalElementGeometry2D values."
                )
        element_ids = tuple(mapping.element_id for mapping in self.physical_elements)
        if len(set(element_ids)) != len(element_ids):
            raise ValueError("Physical-element geometry IDs must be unique.")

        require_tuple(self.deferred_features, "CrossSectionGeometry2D.deferred_features")
        for feature in self.deferred_features:
            if not isinstance(feature, DeferredSectionFeature2D):
                raise TypeError(
                    "CrossSectionGeometry2D.deferred_features items must be "
                    "DeferredSectionFeature2D values."
                )
        feature_ids = tuple(feature.id for feature in self.deferred_features)
        if len(set(feature_ids)) != len(feature_ids):
            raise ValueError("Deferred feature IDs must be unique.")

        require_tuple(self.nominal_voids, "CrossSectionGeometry2D.nominal_voids")
        for nominal_void in self.nominal_voids:
            if not isinstance(nominal_void, SectionVoid2D):
                raise TypeError(
                    "CrossSectionGeometry2D.nominal_voids items must be SectionVoid2D values."
                )
        void_ids = tuple(nominal_void.id for nominal_void in self.nominal_voids)
        if len(set(void_ids)) != len(void_ids):
            raise ValueError("Nominal void IDs must be unique.")

    def _validate_profile_representation(self) -> None:
        if self.section_family is SectionFamily.ROUND_TUBE:
            if (
                self.geometry_idealization is not GeometryIdealization.ANALYTIC_ANNULUS
                or self.profile_kind is not ProfileRepresentationKind.ANALYTIC_ANNULUS
            ):
                raise ValueError("Round-tube geometry requires the analytic-annulus profile.")
            if len(self.physical_elements) != 1:
                raise ValueError(
                    "Analytic round-tube geometry requires exactly one physical element."
                )
            primitives = self.physical_elements[0].geometry
            if len(primitives) != 1 or not isinstance(primitives[0], Annulus2D):
                raise ValueError("Analytic round-tube geometry requires exactly one Annulus2D.")
            if self.deferred_features or self.nominal_voids:
                raise ValueError(
                    "Analytic round-tube geometry has no separate deferred or void data."
                )
            annulus = primitives[0]
            expected_bounds = SectionBoundingBox2D(
                annulus.center.y - annulus.outer_radius,
                annulus.center.y + annulus.outer_radius,
                annulus.center.z - annulus.outer_radius,
                annulus.center.z + annulus.outer_radius,
            )
            if annulus.center != self.construction_datum or self.outside_bounds != expected_bounds:
                raise ValueError(
                    "Annulus center/radius must reproduce the declared outside bounds."
                )
            if annulus.inner_radius <= 0.0:
                raise ValueError("Standard round-tube geometry requires a positive inner radius.")
            return

        if (
            self.geometry_idealization is not GeometryIdealization.NOMINAL_SHARP_CORNER
            or self.profile_kind is not ProfileRepresentationKind.RECTANGULAR_COMPOSITE
        ):
            raise ValueError(
                "Flat-wall standard geometry requires a sharp-corner rectangle profile."
            )
        if any(
            isinstance(primitive, Annulus2D)
            for mapping in self.physical_elements
            for primitive in mapping.geometry
        ):
            raise ValueError("Flat-wall standard geometry cannot contain an annulus.")

    def _validate_profile_consistency(self) -> None:
        physical_rectangles = tuple(
            rectangle
            for mapping in self.physical_elements
            for rectangle in _physical_rectangles(mapping)
        )
        deferred_rectangles = tuple(
            feature.geometry
            for feature in self.deferred_features
            if isinstance(feature.geometry, AxisAlignedRectangle2D)
        )
        deferred_lines = tuple(
            feature.geometry
            for feature in self.deferred_features
            if isinstance(feature.geometry, SectionLineSegment2D)
        )
        void_rectangles = tuple(nominal_void.geometry for nominal_void in self.nominal_voids)

        if any(
            not _rectangle_is_within_bounds(rectangle, self.outside_bounds)
            for rectangle in (*physical_rectangles, *deferred_rectangles, *void_rectangles)
        ):
            raise ValueError("Every rectangular section region must lie within outside bounds.")
        if any(
            not _point_is_within_bounds(endpoint, self.outside_bounds)
            for line in deferred_lines
            for endpoint in (line.start, line.end)
        ):
            raise ValueError("Every deferred line endpoint must lie within outside bounds.")

        if any(
            _rectangles_have_interior_overlap(first, second)
            for first_index, first in enumerate(physical_rectangles)
            for second in physical_rectangles[first_index + 1 :]
        ):
            raise ValueError("Physical-element rectangle interiors must not overlap.")

        if any(
            _rectangles_have_interior_overlap(deferred, physical)
            for deferred in deferred_rectangles
            for physical in physical_rectangles
        ):
            raise ValueError("Deferred finite-area zones must not overlap physical interiors.")

        if any(
            _rectangles_have_interior_overlap(first, second)
            for first_index, first in enumerate(deferred_rectangles)
            for second in deferred_rectangles[first_index + 1 :]
        ):
            raise ValueError("Deferred finite-area zone interiors must not overlap each other.")

        if any(
            _rectangles_have_interior_overlap(nominal_void, occupied)
            for nominal_void in void_rectangles
            for occupied in (*physical_rectangles, *deferred_rectangles)
        ):
            raise ValueError("Nominal void interiors must not overlap occupied section regions.")
        if any(
            _rectangles_have_interior_overlap(first, second)
            for first_index, first in enumerate(void_rectangles)
            for second in void_rectangles[first_index + 1 :]
        ):
            raise ValueError("Nominal void interiors must not overlap each other.")


@dataclass(frozen=True, slots=True)
class ISectionDimensions:
    """Shared exact dimensions for WIDE_FLANGE and general I sections."""

    overall_depth: float
    flange_width: float
    web_thickness: float
    flange_thickness: float

    def __post_init__(self) -> None:
        _validate_flanged_dimensions(
            "ISectionDimensions",
            self.overall_depth,
            self.flange_width,
            self.web_thickness,
            self.flange_thickness,
            thickness_field_name="web_thickness",
            centered_web_or_stem=True,
            has_opposed_flanges=True,
            minimum_depth_multiplier=2.0,
        )


@dataclass(frozen=True, slots=True)
class ChannelDimensions:
    """Exact overall dimensions for the standard channel orientation."""

    overall_depth: float
    flange_width: float
    web_thickness: float
    flange_thickness: float

    def __post_init__(self) -> None:
        _validate_flanged_dimensions(
            "ChannelDimensions",
            self.overall_depth,
            self.flange_width,
            self.web_thickness,
            self.flange_thickness,
            thickness_field_name="web_thickness",
            centered_web_or_stem=False,
            has_opposed_flanges=True,
            minimum_depth_multiplier=2.0,
        )


@dataclass(frozen=True, slots=True)
class TeeDimensions:
    """Exact overall dimensions for the standard tee orientation."""

    overall_depth: float
    flange_width: float
    stem_thickness: float
    flange_thickness: float

    def __post_init__(self) -> None:
        _validate_flanged_dimensions(
            "TeeDimensions",
            self.overall_depth,
            self.flange_width,
            self.stem_thickness,
            self.flange_thickness,
            thickness_field_name="stem_thickness",
            centered_web_or_stem=True,
            has_opposed_flanges=False,
            minimum_depth_multiplier=1.0,
        )


def _validate_flanged_dimensions(
    owner: str,
    overall_depth: float,
    flange_width: float,
    web_or_stem_thickness: float,
    flange_thickness: float,
    *,
    thickness_field_name: str,
    centered_web_or_stem: bool,
    has_opposed_flanges: bool,
    minimum_depth_multiplier: float,
) -> None:
    _require_positive_dimension(overall_depth, f"{owner}.overall_depth")
    _require_positive_dimension(flange_width, f"{owner}.flange_width")
    _require_positive_dimension(
        web_or_stem_thickness,
        f"{owner}.{thickness_field_name}",
    )
    _require_positive_dimension(flange_thickness, f"{owner}.flange_thickness")
    if overall_depth <= minimum_depth_multiplier * flange_thickness:
        raise ValueError(f"{owner} requires positive clear depth.")
    if flange_width <= web_or_stem_thickness:
        raise ValueError(f"{owner} requires flange width greater than web/stem thickness.")

    half_depth = _exact_half_dimension(overall_depth, f"{owner}.overall_depth")
    half_width = _exact_half_dimension(flange_width, f"{owner}.flange_width")
    clear_bottom = -half_depth + flange_thickness
    clear_top = half_depth - flange_thickness
    _require_representable_positive_span(-half_depth, half_depth, f"{owner}.overall_depth")
    _require_representable_positive_span(-half_width, half_width, f"{owner}.flange_width")
    if centered_web_or_stem:
        half_web_or_stem = _exact_half_dimension(
            web_or_stem_thickness,
            f"{owner}.{thickness_field_name}",
        )
        _require_representable_positive_span(
            -half_web_or_stem,
            half_web_or_stem,
            f"{owner}.{thickness_field_name}",
        )
        _require_representable_positive_span(
            half_web_or_stem,
            half_width,
            f"{owner}.clear_flange_width",
        )
    else:
        web_inside = -half_width + web_or_stem_thickness
        _require_representable_positive_span(
            -half_width,
            web_inside,
            f"{owner}.{thickness_field_name}",
        )
        _require_representable_positive_span(
            web_inside,
            half_width,
            f"{owner}.clear_flange_width",
        )
    _require_representable_positive_span(
        clear_top,
        half_depth,
        f"{owner}.flange_thickness",
    )
    if has_opposed_flanges:
        _require_representable_positive_span(
            -half_depth,
            clear_bottom,
            f"{owner}.flange_thickness",
        )
        _require_representable_positive_span(
            clear_bottom,
            clear_top,
            f"{owner}.clear_depth",
        )
    else:
        _require_representable_positive_span(
            -half_depth,
            clear_top,
            f"{owner}.clear_depth",
        )


@dataclass(frozen=True, slots=True)
class RectangularTubeDimensions:
    """Exact outside dimensions and uniform wall thickness for a rectangular tube."""

    outside_width: float
    outside_depth: float
    wall_thickness: float

    def __post_init__(self) -> None:
        _require_positive_dimension(
            self.outside_width,
            "RectangularTubeDimensions.outside_width",
        )
        _require_positive_dimension(
            self.outside_depth,
            "RectangularTubeDimensions.outside_depth",
        )
        _require_positive_dimension(
            self.wall_thickness,
            "RectangularTubeDimensions.wall_thickness",
        )
        if self.outside_width <= 2.0 * self.wall_thickness:
            raise ValueError("RectangularTubeDimensions requires positive inside width.")
        if self.outside_depth <= 2.0 * self.wall_thickness:
            raise ValueError("RectangularTubeDimensions requires positive inside depth.")

        half_width = _exact_half_dimension(
            self.outside_width,
            "RectangularTubeDimensions.outside_width",
        )
        half_depth = _exact_half_dimension(
            self.outside_depth,
            "RectangularTubeDimensions.outside_depth",
        )
        negative_y_inside = -half_width + self.wall_thickness
        positive_y_inside = half_width - self.wall_thickness
        negative_z_inside = -half_depth + self.wall_thickness
        positive_z_inside = half_depth - self.wall_thickness
        for minimum, maximum, field_name in (
            (-half_width, negative_y_inside, "wall_thickness"),
            (negative_y_inside, positive_y_inside, "inside_width"),
            (positive_y_inside, half_width, "wall_thickness"),
            (-half_depth, negative_z_inside, "wall_thickness"),
            (negative_z_inside, positive_z_inside, "inside_depth"),
            (positive_z_inside, half_depth, "wall_thickness"),
        ):
            _require_representable_positive_span(
                minimum,
                maximum,
                f"RectangularTubeDimensions.{field_name}",
            )

    @property
    def is_square(self) -> bool:
        """Return whether the exact nominal outside dimensions are equal."""
        return self.outside_width == self.outside_depth


@dataclass(frozen=True, slots=True)
class AngleDimensions:
    """Exact leg extents and uniform thickness for the standard angle orientation."""

    leg_y: float
    leg_z: float
    thickness: float

    def __post_init__(self) -> None:
        _require_positive_dimension(self.leg_y, "AngleDimensions.leg_y")
        _require_positive_dimension(self.leg_z, "AngleDimensions.leg_z")
        _require_positive_dimension(self.thickness, "AngleDimensions.thickness")
        if self.leg_y <= self.thickness:
            raise ValueError("AngleDimensions requires leg_y greater than thickness.")
        if self.leg_z <= self.thickness:
            raise ValueError("AngleDimensions requires leg_z greater than thickness.")

        half_y = _exact_half_dimension(self.leg_y, "AngleDimensions.leg_y")
        half_z = _exact_half_dimension(self.leg_z, "AngleDimensions.leg_z")
        heel_y = -half_y + self.thickness
        heel_z = -half_z + self.thickness
        for minimum, maximum, field_name in (
            (-half_y, heel_y, "thickness"),
            (heel_y, half_y, "leg_y_clear_extent"),
            (-half_z, heel_z, "thickness"),
            (heel_z, half_z, "leg_z_clear_extent"),
        ):
            _require_representable_positive_span(
                minimum,
                maximum,
                f"AngleDimensions.{field_name}",
            )


@dataclass(frozen=True, slots=True)
class PlateDimensions:
    """Exact local-y width and local-z thickness for a plate or doubler."""

    width: float
    thickness: float

    def __post_init__(self) -> None:
        _require_positive_dimension(self.width, "PlateDimensions.width")
        _require_positive_dimension(self.thickness, "PlateDimensions.thickness")
        half_width = _exact_half_dimension(self.width, "PlateDimensions.width")
        half_thickness = _exact_half_dimension(self.thickness, "PlateDimensions.thickness")
        _require_representable_positive_span(
            -half_width,
            half_width,
            "PlateDimensions.width",
        )
        _require_representable_positive_span(
            -half_thickness,
            half_thickness,
            "PlateDimensions.thickness",
        )


@dataclass(frozen=True, slots=True)
class RoundTubeDimensions:
    """Exact outside diameter and wall thickness for an analytic round tube."""

    outside_diameter: float
    wall_thickness: float

    def __post_init__(self) -> None:
        _require_positive_dimension(
            self.outside_diameter,
            "RoundTubeDimensions.outside_diameter",
        )
        _require_positive_dimension(
            self.wall_thickness,
            "RoundTubeDimensions.wall_thickness",
        )
        outer_radius = _exact_half_dimension(
            self.outside_diameter,
            "RoundTubeDimensions.outside_diameter",
        )
        if self.outside_diameter <= 2.0 * self.wall_thickness:
            raise ValueError("RoundTubeDimensions requires positive inner radius.")
        inner_radius = outer_radius - self.wall_thickness
        _require_representable_positive_span(
            0.0,
            inner_radius,
            "RoundTubeDimensions.inner_radius",
        )
        _require_representable_positive_span(
            inner_radius,
            outer_radius,
            "RoundTubeDimensions.wall_thickness",
        )

    @property
    def outer_radius(self) -> float:
        """Return the exact nominal outside radius."""
        return self.outside_diameter / 2.0

    @property
    def inner_radius(self) -> float:
        """Return the exact nominal inside radius."""
        return self.outer_radius - self.wall_thickness


def _require_standard_topology(
    topology: SectionTopology,
    expected_family: SectionFamily,
) -> None:
    if not isinstance(topology, SectionTopology):
        raise TypeError("topology must be a SectionTopology.")
    if topology.source is not SectionTopologySource.STANDARD:
        raise ValueError("A standard geometry factory requires a STANDARD topology.")
    if topology.standard_family is not expected_family:
        raise ValueError(
            f"Topology family must be {expected_family.value} for this geometry factory."
        )
    if topology.validate():
        raise ValueError("Supplied standard topology does not match its canonical definition.")


def validate_cross_section_topology(
    geometry: CrossSectionGeometry2D,
    topology: SectionTopology,
) -> None:
    """Require one exact geometry mapping for every supplied topology element."""
    if not isinstance(geometry, CrossSectionGeometry2D):
        raise TypeError("geometry must be a CrossSectionGeometry2D.")
    if not isinstance(topology, SectionTopology):
        raise TypeError("topology must be a SectionTopology.")
    if topology.source is not SectionTopologySource.STANDARD:
        raise ValueError("Standard cross-section geometry cannot target a custom topology.")
    if topology.standard_family is not geometry.section_family:
        raise ValueError("Geometry and topology standard families must match.")
    if topology.validate():
        raise ValueError("Supplied standard topology is not canonical.")
    topology_ids = tuple(element.id for element in topology.elements)
    geometry_ids = tuple(mapping.element_id for mapping in geometry.physical_elements)
    if len(geometry_ids) != len(topology_ids) or set(geometry_ids) != set(topology_ids):
        raise ValueError("Geometry must map every topology element exactly once and no others.")


def _element_geometry(
    topology: SectionTopology,
    rectangles_by_role: dict[PhysicalSectionElementRole, AxisAlignedRectangle2D],
) -> tuple[PhysicalElementGeometry2D, ...]:
    return tuple(
        PhysicalElementGeometry2D(element.id, (rectangles_by_role[element.role],))
        for element in topology.elements
    )


def _sharp_corner_geometry(
    *,
    topology: SectionTopology,
    section_family: SectionFamily,
    outside_bounds: SectionBoundingBox2D,
    physical_elements: tuple[PhysicalElementGeometry2D, ...],
    deferred_features: tuple[DeferredSectionFeature2D, ...],
    nominal_voids: tuple[SectionVoid2D, ...],
) -> CrossSectionGeometry2D:
    geometry = CrossSectionGeometry2D(
        construction_datum=SectionPoint2D(0.0, 0.0),
        outside_bounds=outside_bounds,
        section_family=section_family,
        geometry_idealization=GeometryIdealization.NOMINAL_SHARP_CORNER,
        physical_elements=physical_elements,
        deferred_features=deferred_features,
        nominal_voids=nominal_voids,
        profile_kind=ProfileRepresentationKind.RECTANGULAR_COMPOSITE,
    )
    validate_cross_section_topology(geometry, topology)
    return geometry


def _create_i_geometry(
    topology: SectionTopology,
    dimensions: ISectionDimensions,
    family: SectionFamily,
) -> CrossSectionGeometry2D:
    _require_standard_topology(topology, family)
    if not isinstance(dimensions, ISectionDimensions):
        raise TypeError("dimensions must be ISectionDimensions.")
    half_depth = dimensions.overall_depth / 2.0
    half_width = dimensions.flange_width / 2.0
    half_web = dimensions.web_thickness / 2.0
    clear_bottom = -half_depth + dimensions.flange_thickness
    clear_top = half_depth - dimensions.flange_thickness
    rectangles = {
        PhysicalSectionElementRole.WEB: AxisAlignedRectangle2D(
            -half_web,
            half_web,
            clear_bottom,
            clear_top,
        ),
        PhysicalSectionElementRole.TOP_FLANGE: AxisAlignedRectangle2D(
            -half_width,
            half_width,
            clear_top,
            half_depth,
        ),
        PhysicalSectionElementRole.BOTTOM_FLANGE: AxisAlignedRectangle2D(
            -half_width,
            half_width,
            -half_depth,
            clear_bottom,
        ),
    }
    return _sharp_corner_geometry(
        topology=topology,
        section_family=family,
        outside_bounds=SectionBoundingBox2D(-half_width, half_width, -half_depth, half_depth),
        physical_elements=_element_geometry(topology, rectangles),
        deferred_features=(
            DeferredSectionFeature2D(
                "TOP_WEB_TO_FLANGE_JUNCTION",
                DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
                "Top web-to-flange junction",
                SectionLineSegment2D(
                    SectionPoint2D(-half_web, clear_top),
                    SectionPoint2D(half_web, clear_top),
                ),
            ),
            DeferredSectionFeature2D(
                "BOTTOM_WEB_TO_FLANGE_JUNCTION",
                DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
                "Bottom web-to-flange junction",
                SectionLineSegment2D(
                    SectionPoint2D(-half_web, clear_bottom),
                    SectionPoint2D(half_web, clear_bottom),
                ),
            ),
        ),
        nominal_voids=(
            SectionVoid2D(
                "LEFT_WEB_VOID",
                "Left web void",
                AxisAlignedRectangle2D(-half_width, -half_web, clear_bottom, clear_top),
            ),
            SectionVoid2D(
                "RIGHT_WEB_VOID",
                "Right web void",
                AxisAlignedRectangle2D(half_web, half_width, clear_bottom, clear_top),
            ),
        ),
    )


def create_wide_flange_geometry(
    topology: SectionTopology,
    dimensions: ISectionDimensions,
) -> CrossSectionGeometry2D:
    """Create exact nominal WIDE_FLANGE geometry for an explicit matching topology."""
    return _create_i_geometry(topology, dimensions, SectionFamily.WIDE_FLANGE)


def create_i_section_geometry(
    topology: SectionTopology,
    dimensions: ISectionDimensions,
) -> CrossSectionGeometry2D:
    """Create exact nominal general I-section geometry for an explicit matching topology."""
    return _create_i_geometry(topology, dimensions, SectionFamily.I_SECTION)


def create_channel_geometry(
    topology: SectionTopology,
    dimensions: ChannelDimensions,
) -> CrossSectionGeometry2D:
    """Create a channel with its web at local -y and opening toward local +y."""
    _require_standard_topology(topology, SectionFamily.CHANNEL)
    if not isinstance(dimensions, ChannelDimensions):
        raise TypeError("dimensions must be ChannelDimensions.")
    half_depth = dimensions.overall_depth / 2.0
    half_width = dimensions.flange_width / 2.0
    web_inside = -half_width + dimensions.web_thickness
    clear_bottom = -half_depth + dimensions.flange_thickness
    clear_top = half_depth - dimensions.flange_thickness
    rectangles = {
        PhysicalSectionElementRole.WEB: AxisAlignedRectangle2D(
            -half_width,
            web_inside,
            clear_bottom,
            clear_top,
        ),
        PhysicalSectionElementRole.TOP_FLANGE: AxisAlignedRectangle2D(
            -half_width,
            half_width,
            clear_top,
            half_depth,
        ),
        PhysicalSectionElementRole.BOTTOM_FLANGE: AxisAlignedRectangle2D(
            -half_width,
            half_width,
            -half_depth,
            clear_bottom,
        ),
    }
    return _sharp_corner_geometry(
        topology=topology,
        section_family=SectionFamily.CHANNEL,
        outside_bounds=SectionBoundingBox2D(-half_width, half_width, -half_depth, half_depth),
        physical_elements=_element_geometry(topology, rectangles),
        deferred_features=(
            DeferredSectionFeature2D(
                "TOP_WEB_TO_FLANGE_JUNCTION",
                DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
                "Top web-to-flange junction",
                SectionLineSegment2D(
                    SectionPoint2D(-half_width, clear_top),
                    SectionPoint2D(web_inside, clear_top),
                ),
            ),
            DeferredSectionFeature2D(
                "BOTTOM_WEB_TO_FLANGE_JUNCTION",
                DeferredSectionFeatureKind.WEB_TO_FLANGE_JUNCTION,
                "Bottom web-to-flange junction",
                SectionLineSegment2D(
                    SectionPoint2D(-half_width, clear_bottom),
                    SectionPoint2D(web_inside, clear_bottom),
                ),
            ),
        ),
        nominal_voids=(
            SectionVoid2D(
                "CHANNEL_OPENING",
                "Channel opening",
                AxisAlignedRectangle2D(web_inside, half_width, clear_bottom, clear_top),
            ),
        ),
    )


def create_tee_geometry(
    topology: SectionTopology,
    dimensions: TeeDimensions,
) -> CrossSectionGeometry2D:
    """Create a tee with flange at local +z and stem extending toward local -z."""
    _require_standard_topology(topology, SectionFamily.TEE)
    if not isinstance(dimensions, TeeDimensions):
        raise TypeError("dimensions must be TeeDimensions.")
    half_depth = dimensions.overall_depth / 2.0
    half_width = dimensions.flange_width / 2.0
    half_stem = dimensions.stem_thickness / 2.0
    flange_bottom = half_depth - dimensions.flange_thickness
    rectangles = {
        PhysicalSectionElementRole.STEM: AxisAlignedRectangle2D(
            -half_stem,
            half_stem,
            -half_depth,
            flange_bottom,
        ),
        PhysicalSectionElementRole.FLANGE: AxisAlignedRectangle2D(
            -half_width,
            half_width,
            flange_bottom,
            half_depth,
        ),
    }
    return _sharp_corner_geometry(
        topology=topology,
        section_family=SectionFamily.TEE,
        outside_bounds=SectionBoundingBox2D(-half_width, half_width, -half_depth, half_depth),
        physical_elements=_element_geometry(topology, rectangles),
        deferred_features=(
            DeferredSectionFeature2D(
                "STEM_TO_FLANGE_JUNCTION",
                DeferredSectionFeatureKind.STEM_TO_FLANGE_JUNCTION,
                "Stem-to-flange junction",
                SectionLineSegment2D(
                    SectionPoint2D(-half_stem, flange_bottom),
                    SectionPoint2D(half_stem, flange_bottom),
                ),
            ),
        ),
        nominal_voids=(
            SectionVoid2D(
                "LEFT_STEM_VOID",
                "Left stem void",
                AxisAlignedRectangle2D(-half_width, -half_stem, -half_depth, flange_bottom),
            ),
            SectionVoid2D(
                "RIGHT_STEM_VOID",
                "Right stem void",
                AxisAlignedRectangle2D(half_stem, half_width, -half_depth, flange_bottom),
            ),
        ),
    )


def create_rectangular_tube_geometry(
    topology: SectionTopology,
    dimensions: RectangularTubeDimensions,
) -> CrossSectionGeometry2D:
    """Create exact four-wall tube geometry with four deferred corner squares."""
    _require_standard_topology(topology, SectionFamily.RECTANGULAR_TUBE)
    if not isinstance(dimensions, RectangularTubeDimensions):
        raise TypeError("dimensions must be RectangularTubeDimensions.")
    half_width = dimensions.outside_width / 2.0
    half_depth = dimensions.outside_depth / 2.0
    negative_y_inside = -half_width + dimensions.wall_thickness
    positive_y_inside = half_width - dimensions.wall_thickness
    negative_z_inside = -half_depth + dimensions.wall_thickness
    positive_z_inside = half_depth - dimensions.wall_thickness
    rectangles = {
        PhysicalSectionElementRole.TOP_WALL: AxisAlignedRectangle2D(
            negative_y_inside,
            positive_y_inside,
            positive_z_inside,
            half_depth,
        ),
        PhysicalSectionElementRole.BOTTOM_WALL: AxisAlignedRectangle2D(
            negative_y_inside,
            positive_y_inside,
            -half_depth,
            negative_z_inside,
        ),
        PhysicalSectionElementRole.SIDE_WALL_1: AxisAlignedRectangle2D(
            -half_width,
            negative_y_inside,
            negative_z_inside,
            positive_z_inside,
        ),
        PhysicalSectionElementRole.SIDE_WALL_2: AxisAlignedRectangle2D(
            positive_y_inside,
            half_width,
            negative_z_inside,
            positive_z_inside,
        ),
    }
    corner_definitions = (
        (
            "CORNER_NEGATIVE_Y_NEGATIVE_Z",
            "Negative-y negative-z corner",
            AxisAlignedRectangle2D(
                -half_width,
                negative_y_inside,
                -half_depth,
                negative_z_inside,
            ),
        ),
        (
            "CORNER_POSITIVE_Y_NEGATIVE_Z",
            "Positive-y negative-z corner",
            AxisAlignedRectangle2D(
                positive_y_inside,
                half_width,
                -half_depth,
                negative_z_inside,
            ),
        ),
        (
            "CORNER_NEGATIVE_Y_POSITIVE_Z",
            "Negative-y positive-z corner",
            AxisAlignedRectangle2D(
                -half_width,
                negative_y_inside,
                positive_z_inside,
                half_depth,
            ),
        ),
        (
            "CORNER_POSITIVE_Y_POSITIVE_Z",
            "Positive-y positive-z corner",
            AxisAlignedRectangle2D(
                positive_y_inside,
                half_width,
                positive_z_inside,
                half_depth,
            ),
        ),
    )
    return _sharp_corner_geometry(
        topology=topology,
        section_family=SectionFamily.RECTANGULAR_TUBE,
        outside_bounds=SectionBoundingBox2D(-half_width, half_width, -half_depth, half_depth),
        physical_elements=_element_geometry(topology, rectangles),
        deferred_features=tuple(
            DeferredSectionFeature2D(
                feature_id,
                DeferredSectionFeatureKind.RECTANGULAR_TUBE_CORNER,
                label,
                rectangle,
            )
            for feature_id, label, rectangle in corner_definitions
        ),
        nominal_voids=(
            SectionVoid2D(
                "TUBE_INSIDE_OPENING",
                "Tube inside opening",
                AxisAlignedRectangle2D(
                    negative_y_inside,
                    positive_y_inside,
                    negative_z_inside,
                    positive_z_inside,
                ),
            ),
        ),
    )


def create_square_tube_geometry(
    topology: SectionTopology,
    dimensions: RectangularTubeDimensions,
) -> CrossSectionGeometry2D:
    """Create square-tube geometry through the rectangular-tube contract."""
    if not isinstance(dimensions, RectangularTubeDimensions):
        raise TypeError("dimensions must be RectangularTubeDimensions.")
    if not dimensions.is_square:
        raise ValueError("Square-tube geometry requires equal outside width and depth.")
    return create_rectangular_tube_geometry(topology, dimensions)


def create_angle_geometry(
    topology: SectionTopology,
    dimensions: AngleDimensions,
) -> CrossSectionGeometry2D:
    """Create the standard +y/+z angle with a deferred negative-y/negative-z heel."""
    _require_standard_topology(topology, SectionFamily.ANGLE)
    if not isinstance(dimensions, AngleDimensions):
        raise TypeError("dimensions must be AngleDimensions.")
    half_y = dimensions.leg_y / 2.0
    half_z = dimensions.leg_z / 2.0
    heel_y = -half_y + dimensions.thickness
    heel_z = -half_z + dimensions.thickness
    rectangles = {
        PhysicalSectionElementRole.LEG_1: AxisAlignedRectangle2D(
            heel_y,
            half_y,
            -half_z,
            heel_z,
        ),
        PhysicalSectionElementRole.LEG_2: AxisAlignedRectangle2D(
            -half_y,
            heel_y,
            heel_z,
            half_z,
        ),
    }
    return _sharp_corner_geometry(
        topology=topology,
        section_family=SectionFamily.ANGLE,
        outside_bounds=SectionBoundingBox2D(-half_y, half_y, -half_z, half_z),
        physical_elements=_element_geometry(topology, rectangles),
        deferred_features=(
            DeferredSectionFeature2D(
                "ANGLE_HEEL",
                DeferredSectionFeatureKind.ANGLE_HEEL,
                "Angle heel",
                AxisAlignedRectangle2D(-half_y, heel_y, -half_z, heel_z),
            ),
        ),
        nominal_voids=(
            SectionVoid2D(
                "ANGLE_OPEN_AREA",
                "Angle open area",
                AxisAlignedRectangle2D(heel_y, half_y, heel_z, half_z),
            ),
        ),
    )


def create_plate_geometry(
    topology: SectionTopology,
    dimensions: PlateDimensions,
) -> CrossSectionGeometry2D:
    """Create the centered local-y width/local-z thickness plate profile."""
    _require_standard_topology(topology, SectionFamily.PLATE)
    if not isinstance(dimensions, PlateDimensions):
        raise TypeError("dimensions must be PlateDimensions.")
    half_width = dimensions.width / 2.0
    half_thickness = dimensions.thickness / 2.0
    rectangle = AxisAlignedRectangle2D(
        -half_width,
        half_width,
        -half_thickness,
        half_thickness,
    )
    return _sharp_corner_geometry(
        topology=topology,
        section_family=SectionFamily.PLATE,
        outside_bounds=SectionBoundingBox2D(
            -half_width,
            half_width,
            -half_thickness,
            half_thickness,
        ),
        physical_elements=_element_geometry(
            topology,
            {PhysicalSectionElementRole.PLATE: rectangle},
        ),
        deferred_features=(),
        nominal_voids=(),
    )


def create_doubler_geometry(
    topology: SectionTopology,
    dimensions: PlateDimensions,
) -> CrossSectionGeometry2D:
    """Create a flat-doubler cross-section through the plate geometry contract."""
    return create_plate_geometry(topology, dimensions)


def create_round_tube_geometry(
    topology: SectionTopology,
    dimensions: RoundTubeDimensions,
) -> CrossSectionGeometry2D:
    """Create one exact analytic annulus for the standard CURVED_WALL element."""
    _require_standard_topology(topology, SectionFamily.ROUND_TUBE)
    if not isinstance(dimensions, RoundTubeDimensions):
        raise TypeError("dimensions must be RoundTubeDimensions.")
    center = SectionPoint2D(0.0, 0.0)
    annulus = Annulus2D(center, dimensions.outer_radius, dimensions.inner_radius)
    element = topology.elements[0]
    geometry = CrossSectionGeometry2D(
        construction_datum=center,
        outside_bounds=SectionBoundingBox2D(
            -dimensions.outer_radius,
            dimensions.outer_radius,
            -dimensions.outer_radius,
            dimensions.outer_radius,
        ),
        section_family=SectionFamily.ROUND_TUBE,
        geometry_idealization=GeometryIdealization.ANALYTIC_ANNULUS,
        physical_elements=(PhysicalElementGeometry2D(element.id, (annulus,)),),
        deferred_features=(),
        nominal_voids=(),
        profile_kind=ProfileRepresentationKind.ANALYTIC_ANNULUS,
    )
    validate_cross_section_topology(geometry, topology)
    return geometry


__all__ = (
    "AngleDimensions",
    "Annulus2D",
    "AxisAlignedRectangle2D",
    "ChannelDimensions",
    "CrossSectionGeometry2D",
    "DeferredSectionFeature2D",
    "DeferredSectionFeatureKind",
    "GeometryIdealization",
    "ISectionDimensions",
    "PhysicalElementGeometry2D",
    "PlateDimensions",
    "ProfileRepresentationKind",
    "RectangularTubeDimensions",
    "RoundTubeDimensions",
    "SectionBoundingBox2D",
    "SectionLineSegment2D",
    "SectionPoint2D",
    "SectionVoid2D",
    "TeeDimensions",
    "create_angle_geometry",
    "create_channel_geometry",
    "create_doubler_geometry",
    "create_i_section_geometry",
    "create_plate_geometry",
    "create_rectangular_tube_geometry",
    "create_round_tube_geometry",
    "create_square_tube_geometry",
    "create_tee_geometry",
    "create_wide_flange_geometry",
    "validate_cross_section_topology",
)
