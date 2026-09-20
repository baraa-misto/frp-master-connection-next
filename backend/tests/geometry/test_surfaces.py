"""Tests for exact physical surface patches and bounded support surfaces."""

import math
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest

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
    AnalyticCylindricalSurface3D,
    AngleDimensions,
    CartesianFrame3D,
    ChannelDimensions,
    ComponentSurfaceSet3D,
    CrossSectionGeometry2D,
    ISectionDimensions,
    LongitudinalExtent,
    PlacedComponentGeometry3D,
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    PlateDimensions,
    RadialNormalSense,
    RectangularTubeDimensions,
    RoundTubeDimensions,
    SectionBoundingBox2D,
    SectionDatumOffset,
    SurfaceDisposition,
    SurfaceExposure,
    SurfaceGeometryKind,
    SurfacePatch3D,
    SurfacePatchReference,
    SurfacePatchRole,
    SurfacePatchSource,
    SurfaceSourceKind,
    TeeDimensions,
    UnitVector3D,
    Vector3D,
    create_angle_geometry,
    create_bounded_support_surface,
    create_channel_geometry,
    create_component_surface_set,
    create_i_section_geometry,
    create_plate_geometry,
    create_rectangular_tube_geometry,
    create_round_tube_geometry,
    create_tee_geometry,
    create_wide_flange_geometry,
    place_connector,
    place_member,
)
from frp_master_connection.geometry import surfaces as surface_module


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


def _connector(
    family: SectionFamily = SectionFamily.PLATE,
    *,
    connector_id: str = "connector-1",
    topology: SectionTopology | object | None = Ellipsis,
) -> ConnectorComponent:
    resolved_topology = _topology(family) if topology is Ellipsis else topology
    return ConnectorComponent(
        connector_id,
        "Connector",
        ConnectorComponentKind.OTHER,
        ComponentMaterialKind.STEEL,
        section_topology=cast(SectionTopology | None, resolved_topology),
    )


_DEFAULT_EXTENT = LongitudinalExtent(-2.0, 3.0)
_DEFAULT_PARTICIPANT = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1")
_DEFAULT_SOURCE = SurfacePatchSource.physical_element("PLATE")


def _placed(
    family: SectionFamily = SectionFamily.PLATE,
    *,
    frame: CartesianFrame3D = GLOBAL_FRAME,
    extent: LongitudinalExtent = _DEFAULT_EXTENT,
    offset: SectionDatumOffset = ZERO_SECTION_DATUM_OFFSET,
    connector_id: str = "connector-1",
) -> PlacedComponentGeometry3D:
    return place_connector(
        _connector(family, connector_id=connector_id),
        _geometry(family),
        frame,
        extent,
        offset,
    )


def _surface_set(
    family: SectionFamily = SectionFamily.PLATE,
    *,
    frame: CartesianFrame3D = GLOBAL_FRAME,
    extent: LongitudinalExtent = _DEFAULT_EXTENT,
    offset: SectionDatumOffset = ZERO_SECTION_DATUM_OFFSET,
    connector_id: str = "connector-1",
) -> ComponentSurfaceSet3D:
    return create_component_surface_set(
        _placed(
            family,
            frame=frame,
            extent=extent,
            offset=offset,
            connector_id=connector_id,
        )
    )


def _patch_by_id(surface_set: ComponentSurfaceSet3D, patch_id: str) -> SurfacePatch3D:
    return next(patch for patch in surface_set.patches if patch.id == patch_id)


def _planar_patch(surface_set: ComponentSurfaceSet3D, patch_id: str) -> SurfacePatch3D:
    patch = _patch_by_id(surface_set, patch_id)
    assert isinstance(patch.geometry, PlanarRectangularSurface3D)
    return patch


def _physical_source(element_id: str = "PLATE") -> SurfacePatchSource:
    return SurfacePatchSource.physical_element(element_id)


def _regular_patch(
    *,
    patch_id: str = "PATCH",
    participant: ParticipantReference = _DEFAULT_PARTICIPANT,
    source: SurfacePatchSource = _DEFAULT_SOURCE,
    exposure: SurfaceExposure = SurfaceExposure.EXTERIOR_EXPOSED,
    disposition: SurfaceDisposition = SurfaceDisposition.REGULAR,
    role: SurfacePatchRole = SurfacePatchRole.POSITIVE_THICKNESS_FACE,
    geometry: object = Ellipsis,
) -> SurfacePatch3D:
    resolved_geometry = (
        PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0) if geometry is Ellipsis else geometry
    )
    return SurfacePatch3D(
        patch_id,
        "Patch",
        participant,
        source,
        exposure,
        disposition,
        role,
        cast(PlanarRectangularSurface3D, resolved_geometry),
    )


def test_surface_vocabularies_are_exact_and_controlled() -> None:
    assert tuple(item.value for item in SurfaceGeometryKind) == (
        "PLANAR_RECTANGLE",
        "PLANAR_ANNULUS",
        "ANALYTIC_CYLINDER",
    )
    assert tuple(item.value for item in SurfaceExposure) == (
        "EXTERIOR_EXPOSED",
        "VOID_EXPOSED",
        "END_CUT",
        "INTERNAL_JUNCTION",
    )
    assert tuple(item.value for item in SurfaceDisposition) == ("REGULAR", "DEFERRED")
    assert tuple(item.value for item in SurfaceSourceKind) == (
        "PHYSICAL_SECTION_ELEMENT",
        "DEFERRED_FEATURE",
        "SUPPORT",
    )
    assert tuple(item.value for item in RadialNormalSense) == ("OUTWARD", "INWARD")


def test_planar_rectangle_is_exact_frozen_slotted_and_has_deterministic_corners() -> None:
    surface = PlanarRectangularSurface3D(GLOBAL_FRAME, 4.0, 2.0)

    assert surface.kind is SurfaceGeometryKind.PLANAR_RECTANGLE
    assert surface.center == PositionVector3D(0.0, 0.0, 0.0)
    assert surface.normal == UnitVector3D(1.0, 0.0, 0.0)
    assert surface.corners == (
        PositionVector3D(0.0, -2.0, -1.0),
        PositionVector3D(0.0, 2.0, -1.0),
        PositionVector3D(0.0, 2.0, 1.0),
        PositionVector3D(0.0, -2.0, 1.0),
    )
    assert not hasattr(surface, "__dict__")
    with pytest.raises(FrozenInstanceError):
        surface.extent_y = 8.0  # type: ignore[misc]


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf, True, "2"])
@pytest.mark.parametrize("field_name", ["extent_y", "extent_z"])
def test_planar_rectangle_rejects_invalid_extents(value: object, field_name: str) -> None:
    values: dict[str, object] = {"extent_y": 2.0, "extent_z": 3.0}
    values[field_name] = value
    with pytest.raises((TypeError, ValueError)):
        PlanarRectangularSurface3D(GLOBAL_FRAME, **values)  # type: ignore[arg-type]


def test_planar_rectangle_rejects_untyped_frame_and_collapsed_half_extent() -> None:
    with pytest.raises(TypeError, match="frame"):
        PlanarRectangularSurface3D(cast(CartesianFrame3D, "frame"), 2.0, 3.0)
    with pytest.raises(ValueError, match="half-extents"):
        PlanarRectangularSurface3D(GLOBAL_FRAME, math.ulp(0.0), 1.0)


def test_planar_rectangle_rejects_nonfinite_transformed_corners() -> None:
    frame = CartesianFrame3D(
        PositionVector3D(0.0, 1.0e308, 0.0),
        GLOBAL_FRAME.x_axis,
        GLOBAL_FRAME.y_axis,
        GLOBAL_FRAME.z_axis,
    )
    with pytest.raises(ValueError, match="finite"):
        PlanarRectangularSurface3D(frame, 1.7e308, 2.0)


def test_planar_annulus_is_exact_and_signed() -> None:
    frame = CartesianFrame3D(
        PositionVector3D(1.0, 2.0, 3.0),
        -GLOBAL_FRAME.x_axis,
        GLOBAL_FRAME.y_axis,
        -GLOBAL_FRAME.z_axis,
    )
    annulus = PlanarAnnularSurface3D(frame, 5.0, 4.0)

    assert annulus.kind is SurfaceGeometryKind.PLANAR_ANNULUS
    assert annulus.center == PositionVector3D(1.0, 2.0, 3.0)
    assert annulus.normal == UnitVector3D(-1.0, 0.0, 0.0)
    assert annulus.outer_radius == 5.0
    assert annulus.inner_radius == 4.0


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PlanarAnnularSurface3D(cast(CartesianFrame3D, "frame"), 2.0, 1.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, cast(float, True), 1.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, math.inf, 1.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 0.0, 0.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, cast(float, "1")),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, math.nan),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, -1.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, 2.0),
        lambda: PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, 3.0),
    ],
)
def test_planar_annulus_rejects_invalid_forms(factory: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_generic_planar_annulus_allows_zero_inner_radius() -> None:
    assert PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, 0.0).inner_radius == 0.0


def test_analytic_cylinder_preserves_axis_extent_radius_and_radial_sense() -> None:
    cylinder = AnalyticCylindricalSurface3D(
        GLOBAL_FRAME,
        LongitudinalExtent(-2.0, 3.0),
        4.0,
        RadialNormalSense.INWARD,
    )

    assert cylinder.kind is SurfaceGeometryKind.ANALYTIC_CYLINDER
    assert cylinder.minimum_axis_point == PositionVector3D(-2.0, 0.0, 0.0)
    assert cylinder.maximum_axis_point == PositionVector3D(3.0, 0.0, 0.0)
    assert cylinder.radial_normal_sense is RadialNormalSense.INWARD
    assert not hasattr(cylinder, "normal")
    assert not hasattr(cylinder, "angle")
    assert not hasattr(cylinder, "vertices")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: AnalyticCylindricalSurface3D(
            cast(CartesianFrame3D, "frame"),
            LongitudinalExtent(0.0, 1.0),
            1.0,
            RadialNormalSense.OUTWARD,
        ),
        lambda: AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            cast(LongitudinalExtent, "extent"),
            1.0,
            RadialNormalSense.OUTWARD,
        ),
        lambda: AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            0.0,
            RadialNormalSense.OUTWARD,
        ),
        lambda: AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            math.nan,
            RadialNormalSense.OUTWARD,
        ),
        lambda: AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            cast(float, True),
            RadialNormalSense.OUTWARD,
        ),
        lambda: AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            1.0,
            cast(RadialNormalSense, "OUTWARD"),
        ),
    ],
)
def test_analytic_cylinder_rejects_invalid_forms(factory: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_surface_sources_build_each_exact_identity() -> None:
    physical = SurfacePatchSource.physical_element("WEB")
    deferred = SurfacePatchSource.deferred_feature("JUNCTION")
    support = SurfacePatchSource.support("support-1")

    assert physical.source_id == "WEB"
    assert deferred.source_id == "JUNCTION"
    assert support.source_id == "support-1"
    assert physical.kind is SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT
    assert deferred.kind is SurfaceSourceKind.DEFERRED_FEATURE
    assert support.kind is SurfaceSourceKind.SUPPORT


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SurfacePatchSource(cast(SurfaceSourceKind, "SUPPORT"), support_id="support-1"),
        lambda: SurfacePatchSource(SurfaceSourceKind.SUPPORT),
        lambda: SurfacePatchSource(
            SurfaceSourceKind.SUPPORT,
            support_id="support-1",
            physical_element_id="PLATE",
        ),
        lambda: SurfacePatchSource(
            SurfaceSourceKind.PHYSICAL_SECTION_ELEMENT,
            deferred_feature_id="FEATURE",
        ),
        lambda: SurfacePatchSource(
            SurfaceSourceKind.DEFERRED_FEATURE,
            support_id="support-1",
        ),
        lambda: SurfacePatchSource.physical_element("bad/id"),
        lambda: SurfacePatchSource.deferred_feature("bad/id"),
        lambda: SurfacePatchSource.support("bad/id"),
    ],
)
def test_surface_source_rejects_impossible_mixed_or_invalid_identity(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_surface_source_impossible_unvalidated_state_fails_loudly() -> None:
    source = object.__new__(SurfacePatchSource)
    object.__setattr__(source, "kind", SurfaceSourceKind.SUPPORT)
    object.__setattr__(source, "physical_element_id", None)
    object.__setattr__(source, "deferred_feature_id", None)
    object.__setattr__(source, "support_id", None)
    with pytest.raises(RuntimeError, match="no source ID"):
        _ = source.source_id


def test_surface_patch_reference_is_participant_scoped() -> None:
    participant = ParticipantReference(ParticipantKind.MEMBER, "member-1")
    reference = SurfacePatchReference(participant, "WEB:NEGATIVE_TT_BROAD")

    assert reference.participant is participant
    assert reference.patch_id == "WEB:NEGATIVE_TT_BROAD"
    with pytest.raises(TypeError, match="participant"):
        SurfacePatchReference(cast(ParticipantReference, "participant"), "PATCH")
    with pytest.raises(ValueError, match="ASCII"):
        SurfacePatchReference(participant, "bad/id")


def test_surface_patch_targetability_is_derived_and_has_no_override() -> None:
    regular = _regular_patch()
    internal = _regular_patch(
        patch_id="INTERNAL",
        exposure=SurfaceExposure.INTERNAL_JUNCTION,
    )
    deferred = SurfacePatch3D(
        "DEFERRED",
        "Deferred",
        regular.participant,
        SurfacePatchSource.deferred_feature("FEATURE"),
        SurfaceExposure.EXTERIOR_EXPOSED,
        SurfaceDisposition.DEFERRED,
        SurfacePatchRole.JUNCTION_FACE,
        regular.geometry,
    )

    assert regular.is_targetable
    assert not internal.is_targetable
    assert not deferred.is_targetable
    assert {item.name for item in fields(SurfacePatch3D)} == {
        "id",
        "label",
        "participant",
        "source",
        "exposure",
        "disposition",
        "role",
        "geometry",
    }
    assert regular.reference == SurfacePatchReference(regular.participant, "PATCH")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _regular_patch(patch_id="bad/id"),
        lambda: SurfacePatch3D(
            "PATCH",
            " ",
            ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            _physical_source(),
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.POSITIVE_THICKNESS_FACE,
            PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0),
        ),
        lambda: _regular_patch(participant=cast(ParticipantReference, "participant")),
        lambda: _regular_patch(source=cast(SurfacePatchSource, "source")),
        lambda: _regular_patch(exposure=cast(SurfaceExposure, "EXTERIOR_EXPOSED")),
        lambda: _regular_patch(disposition=cast(SurfaceDisposition, "REGULAR")),
        lambda: _regular_patch(role=cast(SurfacePatchRole, "EDGE_FACE")),
        lambda: _regular_patch(geometry="geometry"),
        lambda: _regular_patch(
            participant=ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            source=_physical_source(),
        ),
        lambda: _regular_patch(
            participant=ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            source=SurfacePatchSource.support("support-1"),
        ),
        lambda: _regular_patch(
            participant=ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            source=SurfacePatchSource.support("other-support"),
        ),
        lambda: _regular_patch(disposition=SurfaceDisposition.DEFERRED),
        lambda: _regular_patch(role=SurfacePatchRole.JUNCTION_FACE),
        lambda: _regular_patch(role=SurfacePatchRole.SUPPORT_FACE),
        lambda: _regular_patch(role=SurfacePatchRole.OUTER_CYLINDRICAL_FACE),
        lambda: _regular_patch(
            exposure=SurfaceExposure.END_CUT,
            role=SurfacePatchRole.EDGE_FACE,
        ),
        lambda: SurfacePatch3D(
            "DEFERRED",
            "Deferred",
            ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            SurfacePatchSource.deferred_feature("FEATURE"),
            SurfaceExposure.INTERNAL_JUNCTION,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.JUNCTION_FACE,
            PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0),
        ),
        lambda: SurfacePatch3D(
            "DEFERRED",
            "Deferred",
            ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
            SurfacePatchSource.deferred_feature("FEATURE"),
            SurfaceExposure.INTERNAL_JUNCTION,
            SurfaceDisposition.DEFERRED,
            SurfacePatchRole.EDGE_FACE,
            PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0),
        ),
        lambda: SurfacePatch3D(
            "SUPPORT",
            "Support",
            ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            SurfacePatchSource.support("support-1"),
            SurfaceExposure.VOID_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.SUPPORT_FACE,
            PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0),
        ),
        lambda: SurfacePatch3D(
            "SUPPORT",
            "Support",
            ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            SurfacePatchSource.support("support-1"),
            SurfaceExposure.EXTERIOR_EXPOSED,
            SurfaceDisposition.REGULAR,
            SurfacePatchRole.SUPPORT_FACE,
            PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, 1.0),
        ),
        lambda: _regular_patch(
            geometry=PlanarAnnularSurface3D(GLOBAL_FRAME, 2.0, 1.0),
            role=SurfacePatchRole.ANNULAR_END_FACE,
        ),
        lambda: _regular_patch(
            exposure=SurfaceExposure.END_CUT,
            role=SurfacePatchRole.OUTER_CYLINDRICAL_FACE,
            geometry=AnalyticCylindricalSurface3D(
                GLOBAL_FRAME,
                LongitudinalExtent(0.0, 1.0),
                1.0,
                RadialNormalSense.OUTWARD,
            ),
        ),
    ],
)
def test_surface_patch_rejects_invalid_identity_ownership_or_semantics(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


@pytest.mark.parametrize(
    ("family", "expected_count", "targetable_count", "deferred_count"),
    [
        (SectionFamily.WIDE_FLANGE, 24, 22, 2),
        (SectionFamily.I_SECTION, 24, 22, 2),
        (SectionFamily.CHANNEL, 18, 16, 2),
        (SectionFamily.TEE, 13, 12, 1),
        (SectionFamily.RECTANGULAR_TUBE, 40, 16, 24),
        (SectionFamily.ANGLE, 16, 10, 6),
        (SectionFamily.PLATE, 6, 6, 0),
        (SectionFamily.ROUND_TUBE, 4, 4, 0),
    ],
)
def test_standard_factory_counts_ownership_sources_and_disposition(
    family: SectionFamily,
    expected_count: int,
    targetable_count: int,
    deferred_count: int,
) -> None:
    surface_set = _surface_set(family)

    assert len(surface_set.patches) == expected_count
    assert sum(patch.is_targetable for patch in surface_set.patches) == targetable_count
    assert (
        sum(patch.disposition is SurfaceDisposition.DEFERRED for patch in surface_set.patches)
        == deferred_count
    )
    assert surface_set.participant == surface_set.placed_component.participant
    assert tuple(patch.id for patch in surface_set.patches) == tuple(
        sorted(patch.id for patch in surface_set.patches)
    )
    assert len({patch.id for patch in surface_set.patches}) == expected_count
    assert len({patch.geometry for patch in surface_set.patches}) == expected_count
    assert all(patch.participant == surface_set.participant for patch in surface_set.patches)


@pytest.mark.parametrize("family", [SectionFamily.WIDE_FLANGE, SectionFamily.I_SECTION])
def test_w_and_i_split_flange_surfaces_and_deferred_junctions(family: SectionFamily) -> None:
    surface_set = _surface_set(family)

    assert {patch.id for patch in surface_set.patches if patch.id.startswith("WEB:")} == {
        "WEB:NEGATIVE_TT_BROAD",
        "WEB:POSITIVE_TT_BROAD",
        "WEB:MINIMUM_X_END_CUT",
        "WEB:MAXIMUM_X_END_CUT",
    }
    for flange_id in ("TOP_FLANGE", "BOTTOM_FLANGE"):
        flange_ids = {
            patch.id for patch in surface_set.patches if patch.id.startswith(f"{flange_id}:")
        }
        assert flange_ids == {
            f"{flange_id}:OUTER_TT_BROAD",
            f"{flange_id}:OUTER_NEGATIVE_CW_STRIP",
            f"{flange_id}:OUTER_POSITIVE_CW_STRIP",
            f"{flange_id}:INNER_NEGATIVE_CW_STRIP",
            f"{flange_id}:INNER_POSITIVE_CW_STRIP",
            f"{flange_id}:NEGATIVE_CW_EDGE",
            f"{flange_id}:POSITIVE_CW_EDGE",
            f"{flange_id}:MINIMUM_X_END_CUT",
            f"{flange_id}:MAXIMUM_X_END_CUT",
        }
    junctions = tuple(
        patch
        for patch in surface_set.patches
        if patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE
    )
    assert len(junctions) == 2
    assert all(patch.exposure is SurfaceExposure.INTERNAL_JUNCTION for patch in junctions)
    assert all(not patch.is_targetable for patch in junctions)
    placed = surface_set.placed_component
    top = next(item for item in placed.physical_elements if item.source_element.id == "TOP_FLANGE")
    bottom = next(
        item for item in placed.physical_elements if item.source_element.id == "BOTTOM_FLANGE"
    )
    assert top.source_material_region is bottom.source_material_region


def test_channel_preserves_back_opening_tip_and_exact_junction_surfaces() -> None:
    surface_set = _surface_set(SectionFamily.CHANNEL)

    assert _patch_by_id(surface_set, "WEB:EXTERIOR_BACK_BROAD").exposure is (
        SurfaceExposure.EXTERIOR_EXPOSED
    )
    assert _patch_by_id(surface_set, "WEB:VOID_FACING_INNER_BROAD").exposure is (
        SurfaceExposure.VOID_EXPOSED
    )
    for flange_id in ("TOP_FLANGE", "BOTTOM_FLANGE"):
        assert _patch_by_id(surface_set, f"{flange_id}:INNER_VOID_STRIP").exposure is (
            SurfaceExposure.VOID_EXPOSED
        )
        assert _patch_by_id(surface_set, f"{flange_id}:POSITIVE_CW_FREE_TIP").is_targetable
        assert _patch_by_id(surface_set, f"{flange_id}:NEGATIVE_CW_BACK_EDGE").is_targetable
    assert (
        sum(
            patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE for patch in surface_set.patches
        )
        == 2
    )


def test_tee_splits_flange_around_stem_and_omits_regular_meeting_face() -> None:
    surface_set = _surface_set(SectionFamily.TEE)

    stem_ids = {patch.id for patch in surface_set.patches if patch.id.startswith("STEM:")}
    assert stem_ids == {
        "STEM:NEGATIVE_TT_BROAD",
        "STEM:POSITIVE_TT_BROAD",
        "STEM:FREE_STEM_EDGE",
        "STEM:MINIMUM_X_END_CUT",
        "STEM:MAXIMUM_X_END_CUT",
    }
    assert _patch_by_id(surface_set, "FLANGE:INNER_NEGATIVE_CW_STRIP").exposure is (
        SurfaceExposure.VOID_EXPOSED
    )
    assert _patch_by_id(surface_set, "FLANGE:INNER_POSITIVE_CW_STRIP").exposure is (
        SurfaceExposure.VOID_EXPOSED
    )
    junction = next(
        patch
        for patch in surface_set.patches
        if patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE
    )
    assert junction.exposure is SurfaceExposure.INTERNAL_JUNCTION
    assert isinstance(junction.geometry, PlanarRectangularSurface3D)


def test_tube_walls_have_only_broad_and_end_surfaces_and_corners_are_deferred() -> None:
    surface_set = _surface_set(SectionFamily.RECTANGULAR_TUBE)
    wall_ids = ("TOP_WALL", "BOTTOM_WALL", "SIDE_WALL_1", "SIDE_WALL_2")

    for wall_id in wall_ids:
        patches = tuple(patch for patch in surface_set.patches if patch.source.source_id == wall_id)
        assert {patch.id.removeprefix(f"{wall_id}:") for patch in patches} == {
            "EXTERIOR_BROAD",
            "VOID_FACING_BROAD",
            "MINIMUM_X_END_CUT",
            "MAXIMUM_X_END_CUT",
        }
        assert _patch_by_id(surface_set, f"{wall_id}:VOID_FACING_BROAD").exposure is (
            SurfaceExposure.VOID_EXPOSED
        )
    corner_sources = {
        patch.source.source_id
        for patch in surface_set.patches
        if patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE
    }
    assert len(corner_sources) == 4
    for source_id in corner_sources:
        patches = tuple(
            patch for patch in surface_set.patches if patch.source.source_id == source_id
        )
        assert len(patches) == 6
        assert sum(patch.exposure is SurfaceExposure.EXTERIOR_EXPOSED for patch in patches) == 2
        assert sum(patch.exposure is SurfaceExposure.INTERNAL_JUNCTION for patch in patches) == 2
        assert sum(patch.exposure is SurfaceExposure.END_CUT for patch in patches) == 2
        assert all(not patch.is_targetable for patch in patches)


def test_angle_legs_have_free_edges_and_heel_has_six_deferred_surfaces() -> None:
    surface_set = _surface_set(SectionFamily.ANGLE)

    for leg_id in ("LEG_1", "LEG_2"):
        assert {
            patch.id.removeprefix(f"{leg_id}:")
            for patch in surface_set.patches
            if patch.id.startswith(f"{leg_id}:")
        } == {
            "EXTERIOR_TT_BROAD",
            "OPEN_AREA_TT_BROAD",
            "FREE_EDGE",
            "MINIMUM_X_END_CUT",
            "MAXIMUM_X_END_CUT",
        }
    heel = tuple(
        patch
        for patch in surface_set.patches
        if patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE
    )
    assert len(heel) == 6
    assert all(patch.disposition is SurfaceDisposition.DEFERRED for patch in heel)
    assert all(not patch.is_targetable for patch in heel)


def test_plate_has_six_separate_regular_targetable_surfaces() -> None:
    surface_set = _surface_set()

    assert {patch.id for patch in surface_set.patches} == {
        "PLATE:NEGATIVE_TT_BROAD",
        "PLATE:POSITIVE_TT_BROAD",
        "PLATE:NEGATIVE_CW_EDGE",
        "PLATE:POSITIVE_CW_EDGE",
        "PLATE:MINIMUM_X_END_CUT",
        "PLATE:MAXIMUM_X_END_CUT",
    }
    assert all(patch.is_targetable for patch in surface_set.patches)
    assert all(patch.disposition is SurfaceDisposition.REGULAR for patch in surface_set.patches)


def test_round_tube_has_exact_outer_inner_cylinders_and_annular_ends() -> None:
    surface_set = _surface_set(
        SectionFamily.ROUND_TUBE,
        offset=SectionDatumOffset(2.0, -3.0),
        extent=LongitudinalExtent(-4.0, 6.0),
    )
    outer = _patch_by_id(surface_set, "CURVED_WALL:OUTER_CYLINDER")
    inner = _patch_by_id(surface_set, "CURVED_WALL:INNER_CYLINDER")
    minimum = _patch_by_id(surface_set, "CURVED_WALL:MINIMUM_X_END_CUT")
    maximum = _patch_by_id(surface_set, "CURVED_WALL:MAXIMUM_X_END_CUT")

    assert isinstance(outer.geometry, AnalyticCylindricalSurface3D)
    assert isinstance(inner.geometry, AnalyticCylindricalSurface3D)
    assert outer.geometry.radius == 5.0
    assert inner.geometry.radius == 4.0
    assert outer.geometry.radial_normal_sense is RadialNormalSense.OUTWARD
    assert inner.geometry.radial_normal_sense is RadialNormalSense.INWARD
    assert outer.geometry.minimum_axis_point == PositionVector3D(-4.0, 2.0, -3.0)
    assert outer.geometry.maximum_axis_point == PositionVector3D(6.0, 2.0, -3.0)
    assert isinstance(minimum.geometry, PlanarAnnularSurface3D)
    assert isinstance(maximum.geometry, PlanarAnnularSurface3D)
    assert (minimum.geometry.outer_radius, minimum.geometry.inner_radius) == (5.0, 4.0)
    assert minimum.geometry.normal == UnitVector3D(-1.0, 0.0, 0.0)
    assert maximum.geometry.normal == UnitVector3D(1.0, 0.0, 0.0)
    assert all(patch.is_targetable for patch in surface_set.patches)


def test_planar_normals_and_points_follow_proper_component_placement_and_offset() -> None:
    frame = CartesianFrame3D(
        PositionVector3D(10.0, 20.0, 30.0),
        UnitVector3D(0.0, 1.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
        UnitVector3D(0.0, 0.0, 1.0),
    )
    base = _surface_set(SectionFamily.PLATE)
    transformed = _surface_set(
        SectionFamily.PLATE,
        frame=frame,
        offset=SectionDatumOffset(2.0, -3.0),
    )
    base_patch = _planar_patch(base, "PLATE:POSITIVE_TT_BROAD")
    transformed_patch = _planar_patch(transformed, "PLATE:POSITIVE_TT_BROAD")
    base_geometry = cast(PlanarRectangularSurface3D, base_patch.geometry)
    transformed_geometry = cast(PlanarRectangularSurface3D, transformed_patch.geometry)

    assert base_patch.id == transformed_patch.id
    assert base_patch.exposure is transformed_patch.exposure
    assert base_patch.is_targetable == transformed_patch.is_targetable
    assert base_geometry.normal == UnitVector3D(0.0, 0.0, 1.0)
    assert transformed_geometry.normal == UnitVector3D(0.0, 0.0, 1.0)
    assert transformed_geometry.center == PositionVector3D(8.0, 20.5, 28.0)
    assert transformed_geometry.frame.inspect().valid


def test_connected_end_change_does_not_change_surface_geometry_identity_or_normals() -> None:
    topology = _topology(SectionFamily.PLATE)
    geometry = create_plate_geometry(topology, PlateDimensions(8.0, 2.0))

    def placed_member(end: MemberEnd) -> ComponentSurfaceSet3D:
        member = AssemblyMember(
            "member-1",
            "Member",
            MemberRole.BEAM,
            end,
            SectionFamily.PLATE,
            ComponentMaterialKind.STEEL,
            section_topology=topology,
        )
        placed = place_member(
            member,
            geometry,
            PositionVector3D(0.0, 0.0, 0.0),
            PositionVector3D(5.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
        return create_component_surface_set(placed)

    at_start = placed_member(MemberEnd.START)
    at_end = placed_member(MemberEnd.END)

    assert tuple(patch.id for patch in at_start.patches) == tuple(
        patch.id for patch in at_end.patches
    )
    assert tuple(patch.geometry for patch in at_start.patches) == tuple(
        patch.geometry for patch in at_end.patches
    )
    assert not any(hasattr(patch, "connected_end") for patch in at_start.patches)


def test_surface_set_reference_resolution_is_strictly_participant_scoped() -> None:
    first = _surface_set(connector_id="connector-1")
    second = _surface_set(connector_id="connector-2")
    patch = _patch_by_id(first, "PLATE:POSITIVE_TT_BROAD")

    assert first.resolve(patch.reference) is patch
    with pytest.raises(TypeError, match="reference"):
        first.resolve(cast(SurfacePatchReference, "reference"))
    with pytest.raises(KeyError, match="participant"):
        first.resolve(SurfacePatchReference(second.participant, patch.id))
    with pytest.raises(KeyError, match="Unknown"):
        first.resolve(SurfacePatchReference(first.participant, "UNKNOWN"))


def test_bounded_support_surface_is_explicit_regular_targetable_and_owner_scoped() -> None:
    support = AssemblySupport("support-1", "Support", SupportKind.CONCRETE)
    patch = create_bounded_support_surface(
        support,
        "BEARING_SURFACE",
        "Bearing surface",
        GLOBAL_FRAME,
        20.0,
        30.0,
    )

    assert patch.participant == ParticipantReference(ParticipantKind.SUPPORT, "support-1")
    assert patch.source == SurfacePatchSource.support("support-1")
    assert patch.exposure is SurfaceExposure.EXTERIOR_EXPOSED
    assert patch.disposition is SurfaceDisposition.REGULAR
    assert patch.is_targetable
    assert isinstance(patch.geometry, PlanarRectangularSurface3D)
    assert patch.geometry.normal == GLOBAL_FRAME.x_axis
    for prohibited in ("body", "thickness", "capacity", "interface", "bolt"):
        assert not hasattr(patch, prohibited)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: create_bounded_support_surface(
            cast(AssemblySupport, _connector()),
            "SURFACE",
            "Surface",
            GLOBAL_FRAME,
            2.0,
            3.0,
        ),
        lambda: create_bounded_support_surface(
            AssemblySupport("support-1", "Support", SupportKind.OTHER),
            "bad/id",
            "Surface",
            GLOBAL_FRAME,
            2.0,
            3.0,
        ),
        lambda: create_bounded_support_surface(
            AssemblySupport("support-1", "Support", SupportKind.OTHER),
            "SURFACE",
            " ",
            GLOBAL_FRAME,
            2.0,
            3.0,
        ),
        lambda: create_bounded_support_surface(
            AssemblySupport("support-1", "Support", SupportKind.OTHER),
            "SURFACE",
            "Surface",
            cast(CartesianFrame3D, "frame"),
            2.0,
            3.0,
        ),
        lambda: create_bounded_support_surface(
            AssemblySupport("support-1", "Support", SupportKind.OTHER),
            "SURFACE",
            "Surface",
            GLOBAL_FRAME,
            0.0,
            3.0,
        ),
    ],
)
def test_bounded_support_surface_rejects_invalid_explicit_input(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_component_surface_set_rejects_invalid_core_structure() -> None:
    valid = _surface_set()
    first = valid.patches[0]

    invalid_factories: tuple[Callable[[], object], ...] = (
        lambda: ComponentSurfaceSet3D(
            cast(ParticipantReference, "participant"),
            valid.placed_component,
            valid.patches,
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            cast(object, "placed"),  # type: ignore[arg-type]
            valid.patches,
        ),
        lambda: ComponentSurfaceSet3D(
            ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "other"),
            valid.placed_component,
            valid.patches,
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            cast(tuple[SurfacePatch3D, ...], list(valid.patches)),
        ),
        lambda: ComponentSurfaceSet3D(valid.participant, valid.placed_component, ()),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            cast(tuple[SurfacePatch3D, ...], ("patch",)),
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            (
                replace(
                    first,
                    participant=ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "other"),
                ),
            ),
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            (first, replace(first, label="Duplicate ID")),
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            tuple(reversed(valid.patches)),
        ),
        lambda: ComponentSurfaceSet3D(
            valid.participant,
            valid.placed_component,
            (first, replace(valid.patches[1], geometry=first.geometry)),
        ),
    )
    for factory in invalid_factories:
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_component_surface_set_rejects_unknown_sources_support_and_geometry_mismatch() -> None:
    valid = _surface_set()
    first = valid.patches[0]
    participant = valid.participant
    unknown_physical = replace(first, source=SurfacePatchSource.physical_element("UNKNOWN"))
    support_patch = create_bounded_support_surface(
        AssemblySupport("support-1", "Support", SupportKind.OTHER),
        "SUPPORT",
        "Support",
        GLOBAL_FRAME,
        2.0,
        3.0,
    )
    support_reowned = object.__new__(SurfacePatch3D)
    for item in fields(SurfacePatch3D):
        value = participant if item.name == "participant" else getattr(support_patch, item.name)
        object.__setattr__(support_reowned, item.name, value)

    for patches in ((unknown_physical,), (support_reowned,)):
        with pytest.raises(ValueError, match=r"unknown physical|support-owned"):
            ComponentSurfaceSet3D(participant, valid.placed_component, patches)

    round_set = _surface_set(SectionFamily.ROUND_TUBE)
    round_patch = round_set.patches[0]
    wrong_round_geometry = object.__new__(SurfacePatch3D)
    for item in fields(SurfacePatch3D):
        value = getattr(round_patch, item.name)
        if item.name == "geometry":
            value = PlanarRectangularSurface3D(GLOBAL_FRAME, 2.0, 3.0)
        elif item.name == "exposure":
            value = SurfaceExposure.EXTERIOR_EXPOSED
        object.__setattr__(wrong_round_geometry, item.name, value)
    with pytest.raises(ValueError, match="geometry kind"):
        ComponentSurfaceSet3D(
            round_set.participant,
            round_set.placed_component,
            (wrong_round_geometry,),
        )

    wrong_plate_geometry = replace(
        first,
        exposure=SurfaceExposure.EXTERIOR_EXPOSED,
        role=SurfacePatchRole.OUTER_CYLINDRICAL_FACE,
        geometry=AnalyticCylindricalSurface3D(
            GLOBAL_FRAME,
            LongitudinalExtent(0.0, 1.0),
            1.0,
            RadialNormalSense.OUTWARD,
        ),
    )
    with pytest.raises(ValueError, match="geometry kind"):
        ComponentSurfaceSet3D(participant, valid.placed_component, (wrong_plate_geometry,))


def test_component_surface_set_rejects_unknown_or_nonplanar_deferred_source() -> None:
    valid = _surface_set(SectionFamily.TEE)
    deferred = next(
        patch for patch in valid.patches if patch.source.kind is SurfaceSourceKind.DEFERRED_FEATURE
    )
    unknown = replace(deferred, source=SurfacePatchSource.deferred_feature("UNKNOWN"))
    with pytest.raises(ValueError, match="unknown deferred"):
        ComponentSurfaceSet3D(valid.participant, valid.placed_component, (unknown,))

    nonplanar = object.__new__(SurfacePatch3D)
    for item in fields(SurfacePatch3D):
        value = getattr(deferred, item.name)
        if item.name == "geometry":
            value = AnalyticCylindricalSurface3D(
                GLOBAL_FRAME,
                LongitudinalExtent(0.0, 1.0),
                1.0,
                RadialNormalSense.OUTWARD,
            )
        elif item.name == "exposure":
            value = SurfaceExposure.EXTERIOR_EXPOSED
        object.__setattr__(nonplanar, item.name, value)
    with pytest.raises(ValueError, match="planar rectangles"):
        ComponentSurfaceSet3D(valid.participant, valid.placed_component, (nonplanar,))


def test_factory_is_deterministic_and_does_not_mutate_placement() -> None:
    placed = _placed(SectionFamily.WIDE_FLANGE)
    first = create_component_surface_set(placed)
    second = create_component_surface_set(placed)

    assert first == second
    assert first.placed_component is placed
    assert isinstance(first.patches, tuple)
    assert not hasattr(first, "__dict__")
    with pytest.raises(FrozenInstanceError):
        first.patches = ()  # type: ignore[misc]


def test_factory_rejects_untyped_or_custom_topology() -> None:
    with pytest.raises(TypeError, match="PlacedComponentGeometry3D"):
        create_component_surface_set(cast(object, "placed"))  # type: ignore[arg-type]

    custom_topology = SectionTopology(
        SectionTopologySource.CUSTOM,
        (
            PhysicalSectionElement(
                "PLATE",
                "Plate",
                PhysicalSectionElementRole.CUSTOM,
                "CUSTOM_REGION",
            ),
        ),
        (MaterialRegion("CUSTOM_REGION", "Custom", MaterialRegionRole.CUSTOM),),
    )
    connector = _connector(SectionFamily.PLATE, topology=custom_topology)
    placed = place_connector(
        connector,
        _geometry(SectionFamily.PLATE),
        GLOBAL_FRAME,
        LongitudinalExtent(0.0, 1.0),
        ZERO_SECTION_DATUM_OFFSET,
    )
    with pytest.raises(ValueError, match="standard"):
        create_component_surface_set(placed)


def test_factory_rejects_corrupt_family_association_and_unknown_family() -> None:
    valid = _placed()
    topology = valid.component.section_topology
    assert topology is not None
    object.__setattr__(topology, "standard_family", SectionFamily.ANGLE)
    with pytest.raises(ValueError, match="must match"):
        create_component_surface_set(valid)

    object.__setattr__(topology, "standard_family", SectionFamily.CUSTOM)
    object.__setattr__(valid.cross_section, "section_family", SectionFamily.CUSTOM)
    with pytest.raises(ValueError, match="unsupported"):
        create_component_surface_set(valid)


def test_surface_contract_contains_no_targeting_calculation_or_render_state() -> None:
    prohibited = {
        "bolt",
        "camera",
        "capacity",
        "color",
        "connection_zone",
        "force",
        "hole",
        "interface_id",
        "pixels",
        "resistance",
        "utilization",
    }
    public_fields = {
        item.name
        for contract in (
            PlanarRectangularSurface3D,
            PlanarAnnularSurface3D,
            AnalyticCylindricalSurface3D,
            SurfacePatch3D,
            ComponentSurfaceSet3D,
        )
        for item in fields(contract)
    }

    assert prohibited.isdisjoint(public_fields)
    assert not hasattr(_surface_set(), "interfaces")


@pytest.mark.parametrize(
    "family",
    [
        SectionFamily.WIDE_FLANGE,
        SectionFamily.I_SECTION,
        SectionFamily.CHANNEL,
        SectionFamily.TEE,
        SectionFamily.RECTANGULAR_TUBE,
        SectionFamily.ANGLE,
        SectionFamily.PLATE,
        SectionFamily.ROUND_TUBE,
    ],
)
def test_every_standard_family_has_signed_separate_element_level_end_cuts(
    family: SectionFamily,
) -> None:
    surface_set = _surface_set(family)
    minimum = tuple(patch for patch in surface_set.patches if "MINIMUM_X" in patch.id)
    maximum = tuple(patch for patch in surface_set.patches if "MAXIMUM_X" in patch.id)

    assert len(minimum) == len(maximum)
    assert minimum
    for patch in minimum:
        assert isinstance(
            patch.geometry,
            (PlanarRectangularSurface3D, PlanarAnnularSurface3D),
        )
        assert patch.geometry.normal == -surface_set.placed_component.global_frame.x_axis
    for patch in maximum:
        assert isinstance(
            patch.geometry,
            (PlanarRectangularSurface3D, PlanarAnnularSurface3D),
        )
        assert patch.geometry.normal == surface_set.placed_component.global_frame.x_axis


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_role",
        "flat_has_annulus",
        "angle_missing_heel",
        "round_has_prism",
        "ruled_has_prism",
        "corner_has_ruled",
        "corner_not_on_bounds",
    ],
)
def test_factory_fails_closed_on_corrupt_standard_placed_geometry(corruption: str) -> None:
    if corruption == "missing_role":
        placed = _placed()
        object.__setattr__(placed, "physical_elements", ())
        match = "exactly one"
    elif corruption == "flat_has_annulus":
        placed = _placed()
        round_placed = _placed(SectionFamily.ROUND_TUBE)
        object.__setattr__(
            placed.physical_elements[0],
            "extrusions",
            round_placed.physical_elements[0].extrusions,
        )
        match = "rectangular prism"
    elif corruption == "angle_missing_heel":
        placed = _placed(SectionFamily.ANGLE)
        object.__setattr__(placed, "deferred_features", ())
        match = "deferred heel"
    elif corruption == "round_has_prism":
        placed = _placed(SectionFamily.ROUND_TUBE)
        plate_placed = _placed()
        object.__setattr__(
            placed.physical_elements[0],
            "extrusions",
            plate_placed.physical_elements[0].extrusions,
        )
        match = "annular cylinder"
    elif corruption == "ruled_has_prism":
        placed = _placed(SectionFamily.TEE)
        angle_placed = _placed(SectionFamily.ANGLE)
        object.__setattr__(
            placed.deferred_features[0],
            "extrusion",
            angle_placed.deferred_features[0].extrusion,
        )
        match = "ruled surfaces"
    elif corruption == "corner_has_ruled":
        placed = _placed(SectionFamily.ANGLE)
        tee_placed = _placed(SectionFamily.TEE)
        object.__setattr__(
            placed.deferred_features[0],
            "extrusion",
            tee_placed.deferred_features[0].extrusion,
        )
        match = "rectangular prisms"
    else:
        placed = _placed(SectionFamily.ANGLE)
        object.__setattr__(
            placed.outside_bounds,
            "shifted_section_bounds",
            SectionBoundingBox2D(-10.0, 10.0, -10.0, 10.0),
        )
        match = "two exterior"
    with pytest.raises(ValueError, match=match):
        create_component_surface_set(placed)


def test_surface_midpoint_rejects_nonfinite_derived_value() -> None:
    with pytest.raises(ValueError, match="midpoint"):
        surface_module._midpoint(-1.0e308, 1.0e308)
