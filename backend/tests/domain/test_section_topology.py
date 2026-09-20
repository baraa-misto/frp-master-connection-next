"""Tests for symbolic section topology and FRP material-region contracts."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from enum import StrEnum

import pytest

from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    CylindricalMaterialOrientation,
    FRPComponentOrientation,
    MaterialOrientationKind,
    MaterialRegion,
    MaterialRegionRole,
    PhysicalSectionElement,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    SectionFamily,
    SectionTopology,
    SectionTopologySource,
    ValidationCode,
    create_region_specific_planar_orientations,
    create_standard_section_topology,
)


@pytest.mark.parametrize(
    ("enum_type", "expected_values"),
    [
        (MaterialOrientationKind, ("PLANAR_FIXED", "CYLINDRICAL")),
        (SectionTopologySource, ("STANDARD", "CUSTOM")),
        (
            PhysicalSectionElementRole,
            (
                "WEB",
                "TOP_FLANGE",
                "BOTTOM_FLANGE",
                "STEM",
                "FLANGE",
                "TOP_WALL",
                "BOTTOM_WALL",
                "SIDE_WALL_1",
                "SIDE_WALL_2",
                "LEG_1",
                "LEG_2",
                "PLATE",
                "CURVED_WALL",
                "CUSTOM",
            ),
        ),
        (
            MaterialRegionRole,
            (
                "WEB",
                "FLANGES",
                "STEM",
                "FLANGE",
                "WALL_PAIR_1",
                "WALL_PAIR_2",
                "LEG_1",
                "LEG_2",
                "PLATE",
                "CYLINDRICAL_WALL",
                "CUSTOM",
            ),
        ),
    ],
)
def test_topology_vocabularies_are_exact(
    enum_type: type[StrEnum],
    expected_values: tuple[str, ...],
) -> None:
    assert tuple(item.value for item in enum_type) == expected_values


def test_component_and_region_orientation_objects_are_immutable_and_symbolic() -> None:
    component = FRPComponentOrientation(
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
        PrincipalAxisFamily.X,
    )
    connector = FRPComponentOrientation(
        CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "connector-1"),
        PrincipalAxisFamily.Z,
    )
    planar = PlanarFixedMaterialOrientation(
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )
    cylindrical = CylindricalMaterialOrientation()

    assert component.lengthwise_axis is PrincipalAxisFamily.X
    assert connector.coordinate_frame.kind is CoordinateFrameKind.CONNECTOR_LOCAL
    assert planar.kind is MaterialOrientationKind.PLANAR_FIXED
    assert cylindrical.kind is MaterialOrientationKind.CYLINDRICAL
    with pytest.raises(FrozenInstanceError):
        planar.crosswise_axis = PrincipalAxisFamily.X  # type: ignore[misc]


@pytest.mark.parametrize(
    "arguments",
    [
        ("frame", PrincipalAxisFamily.X),
        (CoordinateFrameReference(CoordinateFrameKind.GLOBAL), PrincipalAxisFamily.X),
        (
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
            "X",
        ),
    ],
)
def test_component_orientation_rejects_invalid_forms(arguments: tuple[object, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        FRPComponentOrientation(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "arguments",
    [
        ("Y", PrincipalAxisFamily.Z),
        (PrincipalAxisFamily.Y, "Z"),
        (PrincipalAxisFamily.Y, PrincipalAxisFamily.Y),
    ],
)
def test_planar_orientation_rejects_untyped_or_duplicate_axis_families(
    arguments: tuple[object, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        PlanarFixedMaterialOrientation(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize("sign", [-2, 0, 2, True, False, 1.0, "-1"])
def test_planar_orientation_rejects_non_unit_integer_axis_signs(sign: object) -> None:
    with pytest.raises(ValueError, match="must be -1 or 1"):
        PlanarFixedMaterialOrientation(
            PrincipalAxisFamily.Y,
            PrincipalAxisFamily.Z,
            sign,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("family", "corrected_roles"),
    [
        (SectionFamily.WIDE_FLANGE, {MaterialRegionRole.WEB}),
        (SectionFamily.I_SECTION, {MaterialRegionRole.WEB}),
        (SectionFamily.TEE, {MaterialRegionRole.STEM}),
        (SectionFamily.ANGLE, {MaterialRegionRole.LEG_2}),
        (SectionFamily.CHANNEL, {MaterialRegionRole.WEB}),
        (SectionFamily.RECTANGULAR_TUBE, {MaterialRegionRole.WALL_PAIR_2}),
        (SectionFamily.PLATE, set()),
    ],
)
def test_region_specific_planar_orientation_mechanism_is_exact(
    family: SectionFamily,
    corrected_roles: set[MaterialRegionRole],
) -> None:
    orientations = create_region_specific_planar_orientations(
        family,
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )
    for role, orientation in orientations.items():
        if role in corrected_roles:
            assert orientation == PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.Z,
                PrincipalAxisFamily.Y,
                -1,
                1,
            )
        else:
            assert orientation == PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.Y,
                PrincipalAxisFamily.Z,
            )


def test_physical_element_and_material_region_keep_identity_separate() -> None:
    orientation = PlanarFixedMaterialOrientation(
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )
    region = MaterialRegion(
        "FLANGES",
        "Flanges",
        MaterialRegionRole.FLANGES,
        orientation,
    )
    top = PhysicalSectionElement(
        "TOP_FLANGE",
        "Top flange",
        PhysicalSectionElementRole.TOP_FLANGE,
        region.id,
    )
    bottom = PhysicalSectionElement(
        "BOTTOM_FLANGE",
        "Bottom flange",
        PhysicalSectionElementRole.BOTTOM_FLANGE,
        region.id,
    )

    assert top != bottom
    assert top.material_region_id == bottom.material_region_id == region.id
    assert region.orientation is orientation


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PhysicalSectionElement("bad/id", "Web", PhysicalSectionElementRole.WEB, "WEB"),
        lambda: PhysicalSectionElement("WEB", " ", PhysicalSectionElementRole.WEB, "WEB"),
        lambda: PhysicalSectionElement("WEB", "Web", "WEB", "WEB"),  # type: ignore[arg-type]
        lambda: PhysicalSectionElement("WEB", "Web", PhysicalSectionElementRole.WEB, "bad/id"),
        lambda: MaterialRegion("bad/id", "Web", MaterialRegionRole.WEB),
        lambda: MaterialRegion("WEB", " ", MaterialRegionRole.WEB),
        lambda: MaterialRegion("WEB", "Web", "WEB"),  # type: ignore[arg-type]
        lambda: MaterialRegion(
            "WEB",
            "Web",
            MaterialRegionRole.WEB,
            "orientation",  # type: ignore[arg-type]
        ),
    ],
)
def test_element_and_region_reject_invalid_local_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def _custom_topology() -> SectionTopology:
    return SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(
            PhysicalSectionElement(
                "element-1",
                "Element 1",
                PhysicalSectionElementRole.CUSTOM,
                "region-1",
            ),
        ),
        material_regions=(
            MaterialRegion(
                "region-1",
                "Region 1",
                MaterialRegionRole.CUSTOM,
            ),
        ),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "CUSTOM"},
        {"source": SectionTopologySource.STANDARD, "standard_family": None},
        {
            "source": SectionTopologySource.STANDARD,
            "standard_family": SectionFamily.CUSTOM,
        },
        {"standard_family": SectionFamily.PLATE},
        {"elements": []},
        {"elements": ()},
        {"elements": ("element",)},
        {"material_regions": []},
        {"material_regions": ()},
        {"material_regions": ("region",)},
    ],
)
def test_section_topology_rejects_invalid_structure(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(_custom_topology(), **changes)  # type: ignore[arg-type]


def test_topology_validation_reports_duplicates_missing_regions_and_orphans_in_order() -> None:
    topology = SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(
            PhysicalSectionElement(
                "element-1",
                "First",
                PhysicalSectionElementRole.CUSTOM,
                "missing-region",
            ),
            PhysicalSectionElement(
                "element-1",
                "Duplicate",
                PhysicalSectionElementRole.CUSTOM,
                "missing-region",
            ),
        ),
        material_regions=(
            MaterialRegion("region-1", "First", MaterialRegionRole.CUSTOM),
            MaterialRegion("region-1", "Duplicate", MaterialRegionRole.CUSTOM),
        ),
    )

    issues = topology.validate("component.section_topology")

    assert tuple(issue.code for issue in issues) == (
        ValidationCode.UNRESOLVED_MATERIAL_REGION,
        ValidationCode.DUPLICATE_SECTION_ELEMENT_ID,
        ValidationCode.UNRESOLVED_MATERIAL_REGION,
        ValidationCode.ORPHAN_MATERIAL_REGION,
        ValidationCode.ORPHAN_MATERIAL_REGION,
        ValidationCode.DUPLICATE_MATERIAL_REGION_ID,
    )
    assert issues[0].path == "component.section_topology.elements[0].material_region_id"
    with pytest.raises(ValueError, match="nonempty"):
        topology.validate(" ")


@pytest.mark.parametrize(
    ("family", "expected_element_roles", "expected_region_roles"),
    [
        (
            SectionFamily.WIDE_FLANGE,
            (
                PhysicalSectionElementRole.WEB,
                PhysicalSectionElementRole.TOP_FLANGE,
                PhysicalSectionElementRole.BOTTOM_FLANGE,
            ),
            (MaterialRegionRole.WEB, MaterialRegionRole.FLANGES),
        ),
        (
            SectionFamily.I_SECTION,
            (
                PhysicalSectionElementRole.WEB,
                PhysicalSectionElementRole.TOP_FLANGE,
                PhysicalSectionElementRole.BOTTOM_FLANGE,
            ),
            (MaterialRegionRole.WEB, MaterialRegionRole.FLANGES),
        ),
        (
            SectionFamily.CHANNEL,
            (
                PhysicalSectionElementRole.WEB,
                PhysicalSectionElementRole.TOP_FLANGE,
                PhysicalSectionElementRole.BOTTOM_FLANGE,
            ),
            (MaterialRegionRole.WEB, MaterialRegionRole.FLANGES),
        ),
        (
            SectionFamily.TEE,
            (PhysicalSectionElementRole.STEM, PhysicalSectionElementRole.FLANGE),
            (MaterialRegionRole.STEM, MaterialRegionRole.FLANGE),
        ),
        (
            SectionFamily.RECTANGULAR_TUBE,
            (
                PhysicalSectionElementRole.TOP_WALL,
                PhysicalSectionElementRole.BOTTOM_WALL,
                PhysicalSectionElementRole.SIDE_WALL_1,
                PhysicalSectionElementRole.SIDE_WALL_2,
            ),
            (MaterialRegionRole.WALL_PAIR_1, MaterialRegionRole.WALL_PAIR_2),
        ),
        (
            SectionFamily.ANGLE,
            (PhysicalSectionElementRole.LEG_1, PhysicalSectionElementRole.LEG_2),
            (MaterialRegionRole.LEG_1, MaterialRegionRole.LEG_2),
        ),
        (
            SectionFamily.PLATE,
            (PhysicalSectionElementRole.PLATE,),
            (MaterialRegionRole.PLATE,),
        ),
        (
            SectionFamily.ROUND_TUBE,
            (PhysicalSectionElementRole.CURVED_WALL,),
            (MaterialRegionRole.CYLINDRICAL_WALL,),
        ),
    ],
)
def test_standard_factories_create_exact_explicit_topologies(
    family: SectionFamily,
    expected_element_roles: tuple[PhysicalSectionElementRole, ...],
    expected_region_roles: tuple[MaterialRegionRole, ...],
) -> None:
    topology = create_standard_section_topology(family)

    assert topology.source is SectionTopologySource.STANDARD
    assert topology.standard_family is family
    assert tuple(element.role for element in topology.elements) == expected_element_roles
    assert tuple(region.role for region in topology.material_regions) == expected_region_roles
    assert all(region.orientation is None for region in topology.material_regions)
    assert topology.validate() == ()


def test_w_and_i_topologies_preserve_occurrences_and_directional_representation() -> None:
    component_orientation = FRPComponentOrientation(
        CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
        PrincipalAxisFamily.X,
    )
    region_orientations = {
        MaterialRegionRole.WEB: PlanarFixedMaterialOrientation(
            PrincipalAxisFamily.Z,
            PrincipalAxisFamily.Y,
        ),
        MaterialRegionRole.FLANGES: PlanarFixedMaterialOrientation(
            PrincipalAxisFamily.Y,
            PrincipalAxisFamily.Z,
        ),
    }
    w_topology = create_standard_section_topology(
        SectionFamily.WIDE_FLANGE,
        orientations=region_orientations,
    )
    i_topology = create_standard_section_topology(
        SectionFamily.I_SECTION,
        orientations=region_orientations,
    )

    assert tuple(
        (element.role, element.material_region_id) for element in w_topology.elements
    ) == tuple((element.role, element.material_region_id) for element in i_topology.elements)
    top, bottom = w_topology.elements[1:]
    assert top.id != bottom.id
    assert top.material_region_id == bottom.material_region_id == "FLANGES"
    assert w_topology.elements[0].material_region_id == "WEB"
    web_orientation = w_topology.material_regions[0].orientation
    flange_orientation = w_topology.material_regions[1].orientation
    assert component_orientation.lengthwise_axis is PrincipalAxisFamily.X
    assert isinstance(web_orientation, PlanarFixedMaterialOrientation)
    assert isinstance(flange_orientation, PlanarFixedMaterialOrientation)
    assert (web_orientation.crosswise_axis, web_orientation.through_thickness_axis) == (
        PrincipalAxisFamily.Z,
        PrincipalAxisFamily.Y,
    )
    assert (flange_orientation.crosswise_axis, flange_orientation.through_thickness_axis) == (
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
    )


def test_rectangular_tube_keeps_opposite_walls_distinct_and_supports_split_override() -> None:
    standard = create_standard_section_topology(SectionFamily.RECTANGULAR_TUBE)
    square = create_standard_section_topology(SectionFamily.RECTANGULAR_TUBE)
    top, bottom, side_1, side_2 = standard.elements
    split_top = replace(top, material_region_id="TOP_WALL_REGION")
    override = SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(split_top, bottom, side_1, side_2),
        material_regions=(
            MaterialRegion(
                "TOP_WALL_REGION",
                "Top wall region",
                MaterialRegionRole.CUSTOM,
            ),
            *standard.material_regions,
        ),
    )

    assert top.id != bottom.id
    assert top.material_region_id == bottom.material_region_id == "WALL_PAIR_1"
    assert side_1.id != side_2.id
    assert side_1.material_region_id == side_2.material_region_id == "WALL_PAIR_2"
    assert square == standard
    assert override.validate() == ()


def test_custom_topology_supports_shared_and_separate_nonparallel_regions() -> None:
    shared = MaterialRegion(
        "shared-region",
        "Shared region",
        MaterialRegionRole.CUSTOM,
        PlanarFixedMaterialOrientation(PrincipalAxisFamily.Y, PrincipalAxisFamily.Z),
    )
    separate = MaterialRegion(
        "separate-region",
        "Separate region",
        MaterialRegionRole.CUSTOM,
        PlanarFixedMaterialOrientation(PrincipalAxisFamily.Z, PrincipalAxisFamily.Y),
    )
    topology = SectionTopology(
        source=SectionTopologySource.CUSTOM,
        elements=(
            PhysicalSectionElement(
                "element-1", "Element 1", PhysicalSectionElementRole.CUSTOM, shared.id
            ),
            PhysicalSectionElement(
                "element-2", "Element 2", PhysicalSectionElementRole.CUSTOM, shared.id
            ),
            PhysicalSectionElement(
                "element-3", "Element 3", PhysicalSectionElementRole.CUSTOM, separate.id
            ),
        ),
        material_regions=(shared, separate),
    )

    assert topology.validate() == ()
    assert topology.elements[0].material_region_id == topology.elements[1].material_region_id
    assert topology.elements[2].material_region_id != topology.elements[0].material_region_id


def test_standard_round_tube_accepts_only_symbolic_cylindrical_orientation() -> None:
    orientation = CylindricalMaterialOrientation()
    topology = create_standard_section_topology(
        SectionFamily.ROUND_TUBE,
        orientations={MaterialRegionRole.CYLINDRICAL_WALL: orientation},
    )

    assert topology.material_regions[0].orientation is orientation
    assert fields(orientation) == ()


@pytest.mark.parametrize(
    ("family", "orientations", "message"),
    [
        (
            SectionFamily.CUSTOM,
            None,
            "No standard symbolic topology",
        ),
        (
            SectionFamily.PLATE,
            [],
            "mapping",
        ),
        (
            SectionFamily.PLATE,
            {"PLATE": PlanarFixedMaterialOrientation(PrincipalAxisFamily.Y, PrincipalAxisFamily.Z)},
            "MaterialRegionRole",
        ),
        (
            SectionFamily.PLATE,
            {
                MaterialRegionRole.WEB: PlanarFixedMaterialOrientation(
                    PrincipalAxisFamily.Y, PrincipalAxisFamily.Z
                )
            },
            "not present",
        ),
        (
            SectionFamily.PLATE,
            {MaterialRegionRole.PLATE: "orientation"},
            "material-orientation",
        ),
        (
            SectionFamily.PLATE,
            {MaterialRegionRole.PLATE: CylindricalMaterialOrientation()},
            "PLANAR_FIXED",
        ),
        (
            SectionFamily.ROUND_TUBE,
            {
                MaterialRegionRole.CYLINDRICAL_WALL: PlanarFixedMaterialOrientation(
                    PrincipalAxisFamily.Y, PrincipalAxisFamily.Z
                )
            },
            "CYLINDRICAL",
        ),
    ],
)
def test_standard_factory_rejects_invalid_family_or_orientation_assignments(
    family: SectionFamily,
    orientations: object,
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        create_standard_section_topology(
            family,
            orientations=orientations,  # type: ignore[arg-type]
        )


def test_standard_factory_requires_typed_section_family() -> None:
    with pytest.raises(TypeError, match="SectionFamily"):
        create_standard_section_topology("PLATE")  # type: ignore[arg-type]


def test_manually_malformed_standard_topology_reports_contract_issue() -> None:
    topology = create_standard_section_topology(SectionFamily.PLATE)
    malformed = replace(
        topology,
        elements=(
            replace(
                topology.elements[0],
                role=PhysicalSectionElementRole.CUSTOM,
            ),
        ),
    )

    assert tuple(issue.code for issue in malformed.validate()) == (
        ValidationCode.INVALID_STANDARD_SECTION_TOPOLOGY,
    )
