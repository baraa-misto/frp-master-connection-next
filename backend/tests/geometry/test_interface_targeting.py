"""Tests for planar interface targeting, connection zones, and local frames."""

import math
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import cast

import pytest

from frp_master_connection.domain import (
    AssemblySupport,
    ComponentMaterialKind,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentKind,
    ParticipantKind,
    ParticipantReference,
    PositionVector3D,
    SectionFamily,
    SupportKind,
    TransferIntent,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    GLOBAL_FRAME,
    ZERO_SECTION_DATUM_OFFSET,
    AnalyticCylindricalSurface3D,
    CartesianFrame3D,
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    ExactSurfaceGeometry3D,
    GeometryComparisonTolerance,
    InterfaceOriginSpecification,
    InterfaceTargetSideSpecification,
    ISectionDimensions,
    LongitudinalExtent,
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    RadialNormalSense,
    RectangularSubzoneBounds,
    RectangularTubeDimensions,
    ResolvedConnectionInterfaceGeometry,
    ResolvedConnectionZone,
    ResolvedInterfaceTargetSide,
    RoundTubeDimensions,
    SurfaceDisposition,
    SurfaceExposure,
    SurfacePatch3D,
    SurfacePatchReference,
    SurfacePatchRole,
    SurfacePatchSource,
    UnitVector3D,
    Vector3D,
    create_bounded_support_surface,
    create_component_surface_set,
    create_rectangular_tube_geometry,
    create_round_tube_geometry,
    create_wide_flange_geometry,
    place_connector,
    resolve_connection_interface_geometry,
)
from frp_master_connection.geometry import interface_targeting as targeting_module

FIRST = ParticipantReference(ParticipantKind.MEMBER, "member-1")
SECOND = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1")
SUPPORT = ParticipantReference(ParticipantKind.SUPPORT, "support-1")
TOLERANCE = GeometryComparisonTolerance(0.01, 1.0e-6)


def _frame(
    origin: PositionVector3D,
    normal: UnitVector3D,
) -> CartesianFrame3D:
    y_axis = UnitVector3D(0.0, 1.0, 0.0) if abs(normal.x) == 1.0 else UnitVector3D(1.0, 0.0, 0.0)
    z_axis = normal.cross(y_axis).normalized()
    y_axis = z_axis.cross(normal).normalized()
    return CartesianFrame3D(origin, normal, y_axis, z_axis)


def _patch(
    patch_id: str,
    participant: ParticipantReference,
    origin: PositionVector3D,
    normal: UnitVector3D,
    *,
    annular: bool = False,
    cylinder: bool = False,
    internal: bool = False,
    deferred: bool = False,
    extent_y: float = 4.0,
    extent_z: float = 4.0,
) -> SurfacePatch3D:
    frame = _frame(origin, normal)
    geometry: ExactSurfaceGeometry3D
    if annular:
        geometry = PlanarAnnularSurface3D(frame, 2.0, 1.0)
        exposure = SurfaceExposure.END_CUT
    elif cylinder:
        geometry = AnalyticCylindricalSurface3D(
            frame,
            LongitudinalExtent(0.0, 1.0),
            2.0,
            RadialNormalSense.OUTWARD,
        )
        exposure = SurfaceExposure.EXTERIOR_EXPOSED
    else:
        geometry = PlanarRectangularSurface3D(frame, extent_y, extent_z)
        exposure = (
            SurfaceExposure.INTERNAL_JUNCTION if internal else SurfaceExposure.EXTERIOR_EXPOSED
        )
    source = (
        SurfacePatchSource.deferred_feature(f"{patch_id}-feature")
        if deferred
        else (
            SurfacePatchSource.support(participant.entity_id)
            if participant.kind is ParticipantKind.SUPPORT
            else SurfacePatchSource.physical_element(f"{patch_id}-element")
        )
    )
    role = (
        SurfacePatchRole.JUNCTION_FACE
        if deferred
        else (
            SurfacePatchRole.SUPPORT_FACE
            if participant.kind is ParticipantKind.SUPPORT
            else (
                SurfacePatchRole.ANNULAR_END_FACE
                if annular
                else (
                    SurfacePatchRole.OUTER_CYLINDRICAL_FACE
                    if cylinder
                    else SurfacePatchRole.POSITIVE_THICKNESS_FACE
                )
            )
        )
    )
    return SurfacePatch3D(
        patch_id,
        f"{patch_id} patch",
        participant,
        source,
        exposure,
        SurfaceDisposition.DEFERRED if deferred else SurfaceDisposition.REGULAR,
        role,
        geometry,
    )


def _whole(
    zone_id: str,
    patch: SurfacePatch3D,
) -> ConnectionZoneSpecification:
    return ConnectionZoneSpecification(
        zone_id,
        f"{zone_id} zone",
        patch.reference,
        ConnectionZoneKind.WHOLE_PATCH,
    )


def _subzone(
    zone_id: str,
    patch: SurfacePatch3D,
    bounds: RectangularSubzoneBounds,
) -> ConnectionZoneSpecification:
    return ConnectionZoneSpecification(
        zone_id,
        f"{zone_id} zone",
        patch.reference,
        ConnectionZoneKind.RECTANGULAR_SUBZONE,
        bounds,
    )


def _side(
    participant: ParticipantReference,
    zones: tuple[ConnectionZoneSpecification, ...],
    primary: str | None = None,
) -> InterfaceTargetSideSpecification:
    return InterfaceTargetSideSpecification(
        participant,
        zones,
        zones[0].id if primary is None else primary,
    )


def _interface(
    first: ParticipantReference = FIRST,
    second: ParticipantReference = SECOND,
) -> ConnectionInterface:
    return ConnectionInterface(
        "interface-1",
        "Planar interface",
        first,
        second,
        TransferIntent.SHEAR_ONLY,
    )


def _valid_case(
    *,
    first_patch: SurfacePatch3D | None = None,
    second_patch: SurfacePatch3D | None = None,
    first_zones: tuple[ConnectionZoneSpecification, ...] | None = None,
    second_zones: tuple[ConnectionZoneSpecification, ...] | None = None,
    origin: InterfaceOriginSpecification | None = None,
    reference: Vector3D | None = None,
    tolerance: GeometryComparisonTolerance = TOLERANCE,
) -> tuple[ConnectionInterfaceGeometrySpecification, tuple[SurfacePatch3D, ...]]:
    resolved_first = first_patch or _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    resolved_second = second_patch or _patch(
        "second-patch",
        SECOND,
        PositionVector3D(1.0, 0.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )
    zones_first = first_zones or (_whole("first-zone", resolved_first),)
    zones_second = second_zones or (_whole("second-zone", resolved_second),)
    first_side = _side(resolved_first.participant, zones_first)
    second_side = _side(resolved_second.participant, zones_second)
    resolved_origin = origin or InterfaceOriginSpecification(first_side.primary_zone_id, 0.0, 0.0)
    specification = ConnectionInterfaceGeometrySpecification(
        _interface(resolved_first.participant, resolved_second.participant),
        first_side,
        second_side,
        resolved_origin,
        Vector3D(0.0, 1.0, 0.0) if reference is None else reference,
        tolerance,
    )
    return specification, (resolved_first, resolved_second)


def test_tolerance_is_explicit_immutable_and_has_exact_fields() -> None:
    tolerance = GeometryComparisonTolerance(0.25, 0.5)

    assert {item.name for item in fields(tolerance)} == {
        "distance_tolerance",
        "angular_tolerance",
    }
    assert tolerance == GeometryComparisonTolerance(0.25, 0.5)
    with pytest.raises(FrozenInstanceError):
        tolerance.distance_tolerance = 1.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        GeometryComparisonTolerance()  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("distance", "angular", "exception_type"),
    [
        (cast(float, True), 0.1, TypeError),
        (cast(float, "distance"), 0.1, TypeError),
        (math.nan, 0.1, ValueError),
        (math.inf, 0.1, ValueError),
        (-math.inf, 0.1, ValueError),
        (0.0, 0.1, ValueError),
        (-0.1, 0.1, ValueError),
        (0.1, cast(float, False), TypeError),
        (0.1, math.nan, ValueError),
        (0.1, math.inf, ValueError),
        (0.1, -math.inf, ValueError),
        (0.1, 0.0, ValueError),
        (0.1, -0.1, ValueError),
    ],
)
def test_tolerance_rejects_invalid_values(
    distance: float,
    angular: float,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type):
        GeometryComparisonTolerance(distance, angular)


def test_zone_vocabulary_and_immutable_construction_are_exact() -> None:
    patch = _patch(
        "patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    whole = _whole("whole", patch)
    bounds = RectangularSubzoneBounds(-2.0, 2.0, -2.0, 2.0)
    subzone = _subzone("subzone", patch, bounds)

    assert tuple(item.value for item in ConnectionZoneKind) == (
        "WHOLE_PATCH",
        "RECTANGULAR_SUBZONE",
    )
    assert whole.rectangular_bounds is None
    assert subzone.rectangular_bounds is bounds
    with pytest.raises(FrozenInstanceError):
        whole.label = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        bounds.min_y = -1.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RectangularSubzoneBounds(cast(float, True), 1.0, 0.0, 1.0),
        lambda: RectangularSubzoneBounds(0.0, cast(float, "x"), 0.0, 1.0),
        lambda: RectangularSubzoneBounds(0.0, math.nan, 0.0, 1.0),
        lambda: RectangularSubzoneBounds(1.0, 1.0, 0.0, 1.0),
        lambda: RectangularSubzoneBounds(2.0, 1.0, 0.0, 1.0),
        lambda: RectangularSubzoneBounds(0.0, 1.0, 1.0, 1.0),
        lambda: RectangularSubzoneBounds(0.0, 1.0, 2.0, 1.0),
    ],
)
def test_rectangular_bounds_reject_invalid_values(factory: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_zone_constructor_rejects_inconsistent_and_invalid_contracts() -> None:
    patch = _patch(
        "patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    bounds = RectangularSubzoneBounds(-1.0, 1.0, -1.0, 1.0)

    factories: tuple[Callable[[], object], ...] = (
        lambda: ConnectionZoneSpecification(
            "bad/id", "Zone", patch.reference, ConnectionZoneKind.WHOLE_PATCH
        ),
        lambda: ConnectionZoneSpecification(
            "zone", "", patch.reference, ConnectionZoneKind.WHOLE_PATCH
        ),
        lambda: ConnectionZoneSpecification(
            "zone",
            "Zone",
            cast(SurfacePatchReference, "reference"),
            ConnectionZoneKind.WHOLE_PATCH,
        ),
        lambda: ConnectionZoneSpecification(
            "zone",
            "Zone",
            patch.reference,
            cast(ConnectionZoneKind, "WHOLE_PATCH"),
        ),
        lambda: ConnectionZoneSpecification(
            "zone", "Zone", patch.reference, ConnectionZoneKind.WHOLE_PATCH, bounds
        ),
        lambda: ConnectionZoneSpecification(
            "zone", "Zone", patch.reference, ConnectionZoneKind.RECTANGULAR_SUBZONE
        ),
    )
    for factory in factories:
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_target_side_validates_identity_participant_primary_and_ordering() -> None:
    first = _patch(
        "a-patch",
        FIRST,
        PositionVector3D(0.0, 1.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    second = _patch(
        "b-patch",
        FIRST,
        PositionVector3D(0.0, -1.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    zone_b = _whole("zone-b", second)
    zone_a = _whole("zone-a", first)
    side = InterfaceTargetSideSpecification(FIRST, (zone_b, zone_a), "zone-b")

    assert tuple(zone.id for zone in side.zones) == ("zone-a", "zone-b")
    assert side.primary_zone_id == "zone-b"

    factories: tuple[Callable[[], object], ...] = (
        lambda: InterfaceTargetSideSpecification(
            cast(ParticipantReference, "participant"), (zone_a,), "zone-a"
        ),
        lambda: InterfaceTargetSideSpecification(
            FIRST, cast(tuple[ConnectionZoneSpecification, ...], []), "zone-a"
        ),
        lambda: InterfaceTargetSideSpecification(FIRST, (), "zone-a"),
        lambda: InterfaceTargetSideSpecification(
            FIRST, cast(tuple[ConnectionZoneSpecification, ...], ("zone",)), "zone-a"
        ),
        lambda: InterfaceTargetSideSpecification(FIRST, (zone_a, zone_a), "zone-a"),
        lambda: InterfaceTargetSideSpecification(FIRST, (zone_a,), "bad/id"),
        lambda: InterfaceTargetSideSpecification(FIRST, (zone_a,), "missing"),
        lambda: InterfaceTargetSideSpecification(SECOND, (zone_a,), "zone-a"),
    )
    for factory in factories:
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_origin_is_explicit_finite_and_immutable() -> None:
    origin = InterfaceOriginSpecification("primary", 2.0, -3.0)

    assert origin == InterfaceOriginSpecification("primary", 2.0, -3.0)
    with pytest.raises(FrozenInstanceError):
        origin.local_y = 0.0  # type: ignore[misc]
    factories: tuple[Callable[[], object], ...] = (
        lambda: InterfaceOriginSpecification("bad/id", 0.0, 0.0),
        lambda: InterfaceOriginSpecification("primary", cast(float, True), 0.0),
        lambda: InterfaceOriginSpecification("primary", 0.0, math.inf),
    )
    for factory in factories:
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_whole_rectangle_annulus_and_exact_boundary_subzone_resolve() -> None:
    rectangle = _patch(
        "rectangle",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    annulus = _patch(
        "annulus",
        FIRST,
        PositionVector3D(0.0, 8.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        annular=True,
    )
    exact_bounds = RectangularSubzoneBounds(-2.0, 2.0, -2.0, 2.0)

    for zone in (_whole("rectangle-whole", rectangle), _whole("annulus-whole", annulus)):
        resolved = ResolvedConnectionZone(
            zone, rectangle if zone.id.startswith("rectangle") else annulus
        )
        assert resolved.surface.reference == zone.surface_reference
        assert resolved.normal == UnitVector3D(1.0, 0.0, 0.0)
        assert resolved.plane_point == resolved.geometry.center
    assert (
        ResolvedConnectionZone(_subzone("exact", rectangle, exact_bounds), rectangle).id == "exact"
    )


def test_zone_resolution_rejects_outside_annular_cylindrical_and_nontargetable_surfaces() -> None:
    rectangle = _patch(
        "rectangle",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    annulus = _patch(
        "annulus",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        annular=True,
    )
    cylinder = _patch(
        "cylinder",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        cylinder=True,
    )
    internal = _patch(
        "internal",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        internal=True,
    )
    deferred = _patch(
        "deferred",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        internal=True,
        deferred=True,
    )
    outside = RectangularSubzoneBounds(-3.0, 1.0, -1.0, 1.0)
    bounds = RectangularSubzoneBounds(-1.0, 1.0, -1.0, 1.0)

    cases = (
        (_subzone("outside", rectangle, outside), rectangle),
        (_subzone("annular-subzone", annulus, bounds), annulus),
        (_whole("cylinder-whole", cylinder), cylinder),
        (_whole("internal-whole", internal), internal),
        (_whole("deferred-whole", deferred), deferred),
    )
    for zone, surface in cases:
        with pytest.raises(ValueError, match=r"."):
            ResolvedConnectionZone(zone, surface)
    with pytest.raises(ValueError, match=r"."):
        ResolvedConnectionZone(_whole("wrong", rectangle), replace(rectangle, id="other"))
    with pytest.raises(TypeError):
        ResolvedConnectionZone(cast(ConnectionZoneSpecification, "zone"), rectangle)
    with pytest.raises(TypeError):
        ResolvedConnectionZone(_whole("whole", rectangle), cast(SurfacePatch3D, "surface"))


def test_surface_resolution_is_participant_safe_exact_and_deterministic() -> None:
    specification, surfaces = _valid_case()
    first, second = surfaces

    with pytest.raises(KeyError):
        resolve_connection_interface_geometry(specification, (second,))
    with pytest.raises(ValueError, match=r"."):
        resolve_connection_interface_geometry(specification, (first, first, second))
    wrong_participant = replace(
        specification.first_side.zones[0],
        surface_reference=SurfacePatchReference(SECOND, first.id),
    )
    with pytest.raises(ValueError, match=r"."):
        replace(specification.first_side, zones=(wrong_participant,))


@pytest.mark.parametrize(
    ("first_bounds", "second_bounds", "accepted"),
    [
        (
            RectangularSubzoneBounds(-2.0, -1.0, -1.0, 1.0),
            RectangularSubzoneBounds(0.0, 1.0, -1.0, 1.0),
            True,
        ),
        (
            RectangularSubzoneBounds(-2.0, 0.0, -1.0, 1.0),
            RectangularSubzoneBounds(0.0, 2.0, -1.0, 1.0),
            True,
        ),
        (
            RectangularSubzoneBounds(-2.0, 0.0, -2.0, 0.0),
            RectangularSubzoneBounds(0.0, 2.0, 0.0, 2.0),
            True,
        ),
        (
            RectangularSubzoneBounds(-2.0, 1.0, -1.0, 1.0),
            RectangularSubzoneBounds(0.0, 2.0, -1.0, 1.0),
            False,
        ),
    ],
)
def test_same_patch_subzone_overlap_is_exact(
    first_bounds: RectangularSubzoneBounds,
    second_bounds: RectangularSubzoneBounds,
    accepted: bool,
) -> None:
    first_patch = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    zones = (
        _subzone("a", first_patch, first_bounds),
        _subzone("b", first_patch, second_bounds),
    )
    specification, surfaces = _valid_case(first_patch=first_patch, first_zones=zones)

    if accepted:
        resolved = resolve_connection_interface_geometry(specification, surfaces)
        assert tuple(zone.id for zone in resolved.first_side.zones) == ("a", "b")
    else:
        with pytest.raises(ValueError, match="overlap"):
            resolve_connection_interface_geometry(specification, surfaces)


def test_duplicate_and_whole_patch_zone_geometry_is_rejected() -> None:
    first_patch = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    duplicate_bounds = RectangularSubzoneBounds(-1.0, 1.0, -1.0, 1.0)
    cases = (
        (_whole("a", first_patch), _whole("b", first_patch)),
        (_whole("a", first_patch), _subzone("b", first_patch, duplicate_bounds)),
        (
            _subzone("a", first_patch, duplicate_bounds),
            _subzone("b", first_patch, duplicate_bounds),
        ),
    )

    for zones in cases:
        specification, surfaces = _valid_case(first_patch=first_patch, first_zones=zones)
        with pytest.raises(ValueError, match=r"."):
            resolve_connection_interface_geometry(specification, surfaces)

    annulus = _patch(
        "annulus",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        annular=True,
    )
    specification, surfaces = _valid_case(
        first_patch=annulus,
        first_zones=(_whole("annulus-a", annulus), _whole("annulus-b", annulus)),
    )
    with pytest.raises(ValueError, match="duplicate"):
        resolve_connection_interface_geometry(specification, surfaces)


def test_one_and_multiple_distinct_coplanar_patches_are_valid_without_merging() -> None:
    patch_a = _patch(
        "patch-a",
        FIRST,
        PositionVector3D(0.0, -5.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    patch_b = _patch(
        "patch-b",
        FIRST,
        PositionVector3D(0.0, 5.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    zones = (_whole("zone-b", patch_b), _whole("zone-a", patch_a))
    specification, default_surfaces = _valid_case(first_patch=patch_a, first_zones=zones)

    resolved = resolve_connection_interface_geometry(
        specification,
        (*default_surfaces, patch_b),
    )

    assert tuple(zone.id for zone in resolved.first_side.zones) == ("zone-a", "zone-b")
    assert resolved.first_side.surface_references == (patch_a.reference, patch_b.reference)
    assert resolved.first_side.primary_zone.id == "zone-b"


def test_same_side_signed_normal_and_coplanarity_use_explicit_tolerance() -> None:
    primary = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    reversed_patch = _patch(
        "reversed",
        FIRST,
        PositionVector3D(0.0, 5.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )
    off_plane = _patch(
        "off-plane",
        FIRST,
        PositionVector3D(0.02, 5.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )

    for extra in (reversed_patch, off_plane):
        zones = (_whole("primary", primary), _whole("extra", extra))
        specification, default_surfaces = _valid_case(first_patch=primary, first_zones=zones)
        with pytest.raises(ValueError, match=r"."):
            resolve_connection_interface_geometry(specification, (*default_surfaces, extra))


def test_logical_participant_order_is_canonical_and_never_swapped() -> None:
    specification, _ = _valid_case()

    assert specification.first_side.participant == specification.interface.participant_a
    assert specification.second_side.participant == specification.interface.participant_b
    with pytest.raises(ValueError, match=r"."):
        replace(specification, first_side=specification.second_side)
    with pytest.raises(ValueError, match=r"."):
        replace(specification, second_side=specification.first_side)


def test_geometry_specification_rejects_invalid_types_and_origin_mismatch() -> None:
    specification, _ = _valid_case()
    factories: tuple[Callable[[], object], ...] = (
        lambda: replace(specification, interface=cast(ConnectionInterface, "interface")),
        lambda: replace(
            specification,
            first_side=cast(InterfaceTargetSideSpecification, "first"),
        ),
        lambda: replace(
            specification,
            second_side=cast(InterfaceTargetSideSpecification, "second"),
        ),
        lambda: replace(
            specification,
            origin=cast(InterfaceOriginSpecification, "origin"),
        ),
        lambda: replace(
            specification,
            origin=InterfaceOriginSpecification("different", 0.0, 0.0),
        ),
        lambda: replace(specification, in_plane_reference=cast(Vector3D, "vector")),
        lambda: replace(
            specification,
            tolerance=cast(GeometryComparisonTolerance, "tolerance"),
        ),
    )
    for factory in factories:
        with pytest.raises((TypeError, ValueError)):
            factory()


def test_opposed_normals_and_signed_separation_contract() -> None:
    exact_specification, exact_surfaces = _valid_case()
    exact = resolve_connection_interface_geometry(exact_specification, exact_surfaces)

    assert exact.first_side_normal == UnitVector3D(1.0, 0.0, 0.0)
    assert exact.second_side_normal == UnitVector3D(-1.0, 0.0, 0.0)
    assert exact.signed_plane_separation == 1.0
    assert not exact.is_coincident_within_tolerance

    same_direction = _patch(
        "second-patch",
        SECOND,
        PositionVector3D(1.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    oblique = _patch(
        "second-patch",
        SECOND,
        PositionVector3D(1.0, 0.0, 0.0),
        UnitVector3D(0.0, 1.0, 0.0),
    )
    for second in (same_direction, oblique):
        specification, surfaces = _valid_case(second_patch=second)
        with pytest.raises(ValueError, match="oppose"):
            resolve_connection_interface_geometry(specification, surfaces)


@pytest.mark.parametrize(
    ("separation", "accepted", "coincident"),
    [
        (0.0, True, True),
        (2.0, True, False),
        (-0.005, True, True),
        (-0.02, False, False),
    ],
)
def test_plane_separation_is_raw_unclamped_data(
    separation: float,
    accepted: bool,
    coincident: bool,
) -> None:
    second = _patch(
        "second-patch",
        SECOND,
        PositionVector3D(separation, 7.0, -3.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )
    specification, surfaces = _valid_case(second_patch=second)

    if accepted:
        resolved = resolve_connection_interface_geometry(specification, surfaces)
        assert resolved.signed_plane_separation == separation
        assert resolved.is_coincident_within_tolerance is coincident
        assert resolved.tolerance is TOLERANCE
    else:
        with pytest.raises(ValueError, match="points away"):
            resolve_connection_interface_geometry(specification, surfaces)


def test_explicit_origin_uses_primary_surface_frame_and_may_leave_zone_footprint() -> None:
    first = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 10.0, 20.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    bounds = RectangularSubzoneBounds(-1.0, 1.0, -1.0, 1.0)
    zone = _subzone("first-zone", first, bounds)
    origin = InterfaceOriginSpecification("first-zone", 100.0, -50.0)
    specification, surfaces = _valid_case(
        first_patch=first,
        first_zones=(zone,),
        origin=origin,
    )

    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert resolved.interface_origin == PositionVector3D(0.0, 110.0, -30.0)
    assert resolved.interface_frame.origin == resolved.interface_origin


def test_annulus_center_is_valid_interface_origin_without_centroid_inference() -> None:
    first = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 4.0, 5.0),
        UnitVector3D(1.0, 0.0, 0.0),
        annular=True,
    )
    specification, surfaces = _valid_case(first_patch=first)

    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert isinstance(first.geometry, PlanarAnnularSurface3D)
    assert resolved.interface_origin == first.geometry.center


def test_interface_frame_uses_explicit_projection_and_is_right_handed() -> None:
    specification, surfaces = _valid_case(reference=Vector3D(5.0, 2.0, 3.0))

    resolved = resolve_connection_interface_geometry(specification, surfaces)
    frame = resolved.interface_frame

    assert frame.x_axis == resolved.first_side_normal
    assert frame.x_axis.cross(frame.y_axis).normalized() == frame.z_axis
    assert frame.inspect().valid
    assert math.isclose(frame.y_axis.y / frame.y_axis.z, 2.0 / 3.0)


@pytest.mark.parametrize(
    "reference",
    [
        Vector3D(0.0, 0.0, 0.0),
        Vector3D(1.0, 0.0, 0.0),
        Vector3D(-1.0, 0.0, 0.0),
        Vector3D(1.0, 1.0e-4, 0.0),
    ],
)
def test_interface_frame_rejects_zero_parallel_antiparallel_and_near_parallel(
    reference: Vector3D,
) -> None:
    specification, surfaces = _valid_case(
        reference=reference,
        tolerance=GeometryComparisonTolerance(0.01, 1.0e-6),
    )

    with pytest.raises(ValueError, match=r"."):
        resolve_connection_interface_geometry(specification, surfaces)


def test_interface_geometry_is_rotation_and_translation_invariant() -> None:
    first = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(10.0, 20.0, 30.0),
        UnitVector3D(0.0, 1.0, 0.0),
    )
    second = _patch(
        "second-patch",
        SECOND,
        PositionVector3D(10.0, 22.0, 30.0),
        UnitVector3D(0.0, -1.0, 0.0),
    )
    specification, surfaces = _valid_case(
        first_patch=first,
        second_patch=second,
        reference=Vector3D(0.0, 4.0, 2.0),
        origin=InterfaceOriginSpecification("first-zone", 3.0, -5.0),
    )

    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert resolved.signed_plane_separation == 2.0
    assert resolved.interface_frame.x_axis == UnitVector3D(0.0, 1.0, 0.0)
    assert resolved.interface_frame.y_axis == UnitVector3D(0.0, 0.0, 1.0)
    assert isinstance(first.geometry, PlanarRectangularSurface3D)
    assert resolved.interface_origin == first.geometry.frame.local_to_parent_point(
        PositionVector3D(0.0, 3.0, -5.0)
    )


def test_bounded_support_surface_is_targeted_without_a_support_body() -> None:
    first = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    support = AssemblySupport("support-1", "Foundation surface", SupportKind.FOUNDATION)
    support_patch = create_bounded_support_surface(
        support,
        "support-patch",
        "Bounded support plane",
        _frame(PositionVector3D(1.0, 0.0, 0.0), UnitVector3D(-1.0, 0.0, 0.0)),
        10.0,
        8.0,
    )
    specification, surfaces = _valid_case(first_patch=first, second_patch=support_patch)

    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert resolved.second_participant == SUPPORT
    assert resolved.second_side.primary_zone.surface is support_patch
    assert not hasattr(resolved, "support_body")
    assert not hasattr(resolved, "anchors")


def _connector_surface_set(
    family: SectionFamily,
) -> tuple[ConnectorComponent, tuple[SurfacePatch3D, ...]]:
    connector = ConnectorComponent(
        "component-1",
        "Component",
        ConnectorComponentKind.OTHER,
        ComponentMaterialKind.STEEL,
        section_topology=create_standard_section_topology(family),
    )
    topology = connector.section_topology
    assert topology is not None
    if family is SectionFamily.WIDE_FLANGE:
        geometry = create_wide_flange_geometry(
            topology,
            ISectionDimensions(12.0, 8.0, 2.0, 2.0),
        )
    elif family is SectionFamily.RECTANGULAR_TUBE:
        geometry = create_rectangular_tube_geometry(
            topology,
            RectangularTubeDimensions(10.0, 8.0, 1.0),
        )
    else:
        geometry = create_round_tube_geometry(topology, RoundTubeDimensions(10.0, 1.0))
    surface_set = create_component_surface_set(
        place_connector(
            connector,
            geometry,
            GLOBAL_FRAME,
            LongitudinalExtent(-1.0, 0.0),
            ZERO_SECTION_DATUM_OFFSET,
        )
    )
    return connector, surface_set.patches


@pytest.mark.parametrize(
    ("family", "physical_ids", "zone_count"),
    [
        (
            SectionFamily.WIDE_FLANGE,
            ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
            3,
        ),
        (
            SectionFamily.RECTANGULAR_TUBE,
            ("TOP_WALL", "BOTTOM_WALL", "SIDE_WALL_1", "SIDE_WALL_2"),
            4,
        ),
    ],
)
def test_standard_shape_full_end_target_sides_preserve_separate_physical_patches(
    family: SectionFamily,
    physical_ids: tuple[str, ...],
    zone_count: int,
) -> None:
    connector, patches = _connector_surface_set(family)
    participant = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, connector.id)
    end_patches = tuple(
        next(patch for patch in patches if patch.id == f"{element}:MAXIMUM_X_END_CUT")
        for element in physical_ids
    )
    first_side = _side(
        participant,
        tuple(_whole(f"zone-{index}", patch) for index, patch in enumerate(end_patches)),
    )
    support = _patch(
        "support-patch",
        SUPPORT,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
        extent_y=20.0,
        extent_z=20.0,
    )
    specification = ConnectionInterfaceGeometrySpecification(
        _interface(participant, SUPPORT),
        first_side,
        _side(SUPPORT, (_whole("support-zone", support),)),
        InterfaceOriginSpecification(first_side.primary_zone_id, 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        TOLERANCE,
    )

    resolved = resolve_connection_interface_geometry(specification, (*patches, support))

    assert len(resolved.first_side.zones) == zone_count
    assert len(set(resolved.first_side.surface_references)) == zone_count


def test_rectangular_tube_deferred_corner_end_patch_is_rejected() -> None:
    connector, patches = _connector_surface_set(SectionFamily.RECTANGULAR_TUBE)
    participant = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, connector.id)
    deferred = next(patch for patch in patches if patch.id.endswith("MAXIMUM_X_DEFERRED_END_CUT"))
    zone = _whole("corner-zone", deferred)
    side = _side(participant, (zone,))
    support = _patch(
        "support-patch",
        SUPPORT,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )
    specification = ConnectionInterfaceGeometrySpecification(
        _interface(participant, SUPPORT),
        side,
        _side(SUPPORT, (_whole("support-zone", support),)),
        InterfaceOriginSpecification("corner-zone", 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        TOLERANCE,
    )

    with pytest.raises(ValueError, match="deferred"):
        resolve_connection_interface_geometry(specification, (*patches, support))


def test_round_tube_annular_end_is_valid_but_cylinders_are_rejected() -> None:
    connector, patches = _connector_surface_set(SectionFamily.ROUND_TUBE)
    participant = ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, connector.id)
    annulus = next(patch for patch in patches if patch.id.endswith("MAXIMUM_X_END_CUT"))
    outer = next(patch for patch in patches if patch.id.endswith("OUTER_CYLINDER"))
    inner = next(patch for patch in patches if patch.id.endswith("INNER_CYLINDER"))
    support = _patch(
        "support-patch",
        SUPPORT,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )

    valid_side = _side(participant, (_whole("annular-zone", annulus),))
    valid = ConnectionInterfaceGeometrySpecification(
        _interface(participant, SUPPORT),
        valid_side,
        _side(SUPPORT, (_whole("support-zone", support),)),
        InterfaceOriginSpecification("annular-zone", 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        TOLERANCE,
    )
    resolved = resolve_connection_interface_geometry(valid, (*patches, support))
    assert isinstance(resolved.first_side.primary_zone.geometry, PlanarAnnularSurface3D)

    for cylinder in (outer, inner):
        side = _side(participant, (_whole("cylinder-zone", cylinder),))
        invalid = replace(
            valid,
            first_side=side,
            origin=InterfaceOriginSpecification("cylinder-zone", 0.0, 0.0),
        )
        with pytest.raises(ValueError, match="planar"):
            resolve_connection_interface_geometry(invalid, (*patches, support))


def test_direct_member_to_member_interface_retains_exact_participants() -> None:
    second_member = ParticipantReference(ParticipantKind.MEMBER, "member-2")
    first = _patch(
        "first-patch",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )
    second = _patch(
        "second-patch",
        second_member,
        PositionVector3D(0.5, 0.0, 0.0),
        UnitVector3D(-1.0, 0.0, 0.0),
    )
    specification, surfaces = _valid_case(first_patch=first, second_patch=second)

    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert resolved.interface is specification.interface
    assert (resolved.first_participant, resolved.second_participant) == (FIRST, second_member)


def test_resolved_contracts_are_frozen_slotted_and_geometry_only() -> None:
    specification, surfaces = _valid_case()
    resolved = resolve_connection_interface_geometry(specification, surfaces)

    assert {item.name for item in fields(ResolvedConnectionInterfaceGeometry)} == {
        "interface",
        "first_participant",
        "second_participant",
        "first_side",
        "second_side",
        "interface_frame",
        "signed_plane_separation",
        "tolerance",
    }
    assert {item.name for item in fields(ResolvedConnectionZone)} == {
        "specification",
        "surface",
    }
    forbidden = {
        "api",
        "bolt",
        "capacity",
        "contact",
        "demand",
        "force",
        "moment",
        "pressure",
        "result",
        "stiffness",
        "utilization",
    }
    assert forbidden.isdisjoint(item.name for item in fields(resolved))
    with pytest.raises(FrozenInstanceError):
        resolved.signed_plane_separation = 3.0  # type: ignore[misc]


def test_public_resolver_and_resolved_constructors_reject_invalid_runtime_types() -> None:
    specification, surfaces = _valid_case()
    resolved = resolve_connection_interface_geometry(specification, surfaces)
    zone = resolved.first_side.primary_zone

    with pytest.raises(TypeError):
        resolve_connection_interface_geometry(
            cast(ConnectionInterfaceGeometrySpecification, "specification"),
            surfaces,
        )
    with pytest.raises(TypeError):
        resolve_connection_interface_geometry(specification, cast(tuple[SurfacePatch3D, ...], []))
    with pytest.raises(TypeError):
        resolve_connection_interface_geometry(
            specification,
            cast(tuple[SurfacePatch3D, ...], ("surface",)),
        )
    with pytest.raises(TypeError):
        ResolvedInterfaceTargetSide(cast(ParticipantReference, "participant"), (zone,), zone.id)
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(FIRST, (), zone.id)
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(
            FIRST, cast(tuple[ResolvedConnectionZone, ...], ("zone",)), zone.id
        )
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(SECOND, (zone,), zone.id)
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(FIRST, (zone, zone), zone.id)
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(FIRST, (zone,), "missing")
    with pytest.raises(ValueError, match=r"."):
        ResolvedInterfaceTargetSide(
            FIRST, (replace(zone, specification=replace(zone.specification, id="z")), zone), "z"
        )


def test_resolved_interface_constructor_rejects_inconsistent_state() -> None:
    specification, surfaces = _valid_case()
    resolved = resolve_connection_interface_geometry(specification, surfaces)
    other = _interface(FIRST, ParticipantReference(ParticipantKind.MEMBER, "member-2"))

    factories: tuple[Callable[[], object], ...] = (
        lambda: replace(resolved, interface=cast(ConnectionInterface, "interface")),
        lambda: replace(resolved, interface=other),
        lambda: replace(resolved, first_side=cast(ResolvedInterfaceTargetSide, "side")),
        lambda: replace(resolved, first_participant=SECOND),
        lambda: replace(resolved, interface_frame=cast(CartesianFrame3D, "frame")),
        lambda: replace(resolved, signed_plane_separation=cast(float, True)),
        lambda: replace(resolved, tolerance=cast(GeometryComparisonTolerance, "tolerance")),
    )
    for factory in factories:
        with pytest.raises((TypeError, ValueError)):
            factory()

    with pytest.raises(ValueError, match="target sides"):
        replace(resolved, first_side=resolved.second_side)


def test_defensive_invariant_failures_are_deterministic_for_corrupted_internal_state() -> None:
    specification, surfaces = _valid_case()
    resolved = resolve_connection_interface_geometry(specification, surfaces)
    zone = resolved.first_side.primary_zone

    cylinder = _patch(
        "cylinder",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        cylinder=True,
    )
    corrupted_zone = object.__new__(ResolvedConnectionZone)
    object.__setattr__(corrupted_zone, "specification", zone.specification)
    object.__setattr__(corrupted_zone, "surface", cylinder)
    with pytest.raises(RuntimeError, match="lost its planar geometry"):
        _ = corrupted_zone.geometry

    corrupted_side = object.__new__(ResolvedInterfaceTargetSide)
    object.__setattr__(corrupted_side, "participant", FIRST)
    object.__setattr__(corrupted_side, "zones", (zone,))
    object.__setattr__(corrupted_side, "primary_zone_id", "missing")
    with pytest.raises(RuntimeError, match="lost its primary zone"):
        _ = corrupted_side.primary_zone

    corrupted_specification = object.__new__(ConnectionZoneSpecification)
    object.__setattr__(corrupted_specification, "id", "corrupted")
    object.__setattr__(corrupted_specification, "label", "Corrupted")
    object.__setattr__(corrupted_specification, "surface_reference", zone.surface.reference)
    object.__setattr__(
        corrupted_specification,
        "kind",
        ConnectionZoneKind.RECTANGULAR_SUBZONE,
    )
    object.__setattr__(corrupted_specification, "rectangular_bounds", None)
    assert isinstance(zone.geometry, PlanarRectangularSurface3D)
    with pytest.raises(RuntimeError, match="lost its bounds"):
        targeting_module._validate_zone_geometry(corrupted_specification, zone.geometry)

    annulus = _patch(
        "annulus",
        FIRST,
        PositionVector3D(0.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
        annular=True,
    )
    annular_zone = ResolvedConnectionZone(_whole("annular", annulus), annulus)
    with pytest.raises(TypeError, match="rectangular source"):
        targeting_module._rectangle_bounds(annular_zone)

    corrupted_resolved_zone = object.__new__(ResolvedConnectionZone)
    object.__setattr__(corrupted_resolved_zone, "specification", corrupted_specification)
    object.__setattr__(corrupted_resolved_zone, "surface", zone.surface)
    with pytest.raises(RuntimeError, match="lost its bounds"):
        targeting_module._rectangle_bounds(corrupted_resolved_zone)

    wrong_origin = InterfaceOriginSpecification("other", 0.0, 0.0)
    with pytest.raises(ValueError, match="primary first-side"):
        targeting_module._resolve_origin(wrong_origin, resolved.first_side)
