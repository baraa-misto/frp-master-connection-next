"""Symbolic section topology and FRP material-orientation contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from frp_master_connection.domain.validation import (
    ValidationCode,
    ValidationIssue,
    order_issues,
    require_enum,
    require_tuple,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    PrincipalAxisFamily,
    SectionFamily,
)


class MaterialOrientationKind(StrEnum):
    """Symbolic FRP material-orientation rule kinds."""

    PLANAR_FIXED = "PLANAR_FIXED"
    CYLINDRICAL = "CYLINDRICAL"


class SectionTopologySource(StrEnum):
    """Whether topology was explicitly built from a standard definition or custom data."""

    STANDARD = "STANDARD"
    CUSTOM = "CUSTOM"


class PhysicalSectionElementRole(StrEnum):
    """Controlled physical occurrence roles without geometry."""

    WEB = "WEB"
    TOP_FLANGE = "TOP_FLANGE"
    BOTTOM_FLANGE = "BOTTOM_FLANGE"
    STEM = "STEM"
    FLANGE = "FLANGE"
    TOP_WALL = "TOP_WALL"
    BOTTOM_WALL = "BOTTOM_WALL"
    SIDE_WALL_1 = "SIDE_WALL_1"
    SIDE_WALL_2 = "SIDE_WALL_2"
    LEG_1 = "LEG_1"
    LEG_2 = "LEG_2"
    PLATE = "PLATE"
    CURVED_WALL = "CURVED_WALL"
    CUSTOM = "CUSTOM"


class MaterialRegionRole(StrEnum):
    """Controlled material-region roles kept separate from physical occurrences."""

    WEB = "WEB"
    FLANGES = "FLANGES"
    STEM = "STEM"
    FLANGE = "FLANGE"
    WALL_PAIR_1 = "WALL_PAIR_1"
    WALL_PAIR_2 = "WALL_PAIR_2"
    LEG_1 = "LEG_1"
    LEG_2 = "LEG_2"
    PLATE = "PLATE"
    CYLINDRICAL_WALL = "CYLINDRICAL_WALL"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class FRPComponentOrientation:
    """One component-local frame and shared sign-insensitive LW axis family."""

    coordinate_frame: CoordinateFrameReference
    lengthwise_axis: PrincipalAxisFamily

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate_frame, CoordinateFrameReference):
            raise TypeError("FRPComponentOrientation.coordinate_frame must be a frame reference.")
        if self.coordinate_frame.kind not in {
            CoordinateFrameKind.MEMBER_LOCAL,
            CoordinateFrameKind.CONNECTOR_LOCAL,
        }:
            raise ValueError(
                "FRP component orientation requires a member-local or connector-local frame."
            )
        require_enum(
            self.lengthwise_axis,
            PrincipalAxisFamily,
            "FRPComponentOrientation.lengthwise_axis",
        )


@dataclass(frozen=True, slots=True)
class PlanarFixedMaterialOrientation:
    """Fixed CW and TT axis families for one planar FRP material region."""

    crosswise_axis: PrincipalAxisFamily
    through_thickness_axis: PrincipalAxisFamily
    crosswise_sign: int = 1
    through_thickness_sign: int = 1

    kind: ClassVar[MaterialOrientationKind] = MaterialOrientationKind.PLANAR_FIXED

    def __post_init__(self) -> None:
        require_enum(
            self.crosswise_axis,
            PrincipalAxisFamily,
            "PlanarFixedMaterialOrientation.crosswise_axis",
        )
        require_enum(
            self.through_thickness_axis,
            PrincipalAxisFamily,
            "PlanarFixedMaterialOrientation.through_thickness_axis",
        )
        if self.crosswise_axis is self.through_thickness_axis:
            raise ValueError("Planar CW and TT must use different axis families.")
        for name, sign in (
            ("crosswise_sign", self.crosswise_sign),
            ("through_thickness_sign", self.through_thickness_sign),
        ):
            if isinstance(sign, bool) or not isinstance(sign, int) or sign not in {-1, 1}:
                raise ValueError(f"PlanarFixedMaterialOrientation.{name} must be -1 or 1.")


@dataclass(frozen=True, slots=True)
class CylindricalMaterialOrientation:
    """Symbolic axial-LW, tangential-CW, radial-TT round-wall orientation."""

    kind: ClassVar[MaterialOrientationKind] = MaterialOrientationKind.CYLINDRICAL


type MaterialOrientationRule = PlanarFixedMaterialOrientation | CylindricalMaterialOrientation


@dataclass(frozen=True, slots=True)
class PhysicalSectionElement:
    """One scoped physical section-element occurrence without exact geometry."""

    id: str
    label: str
    role: PhysicalSectionElementRole
    material_region_id: str

    def __post_init__(self) -> None:
        validate_identifier(self.id, "PhysicalSectionElement.id")
        validate_label(self.label, "PhysicalSectionElement.label")
        require_enum(self.role, PhysicalSectionElementRole, "PhysicalSectionElement.role")
        validate_identifier(
            self.material_region_id,
            "PhysicalSectionElement.material_region_id",
        )


@dataclass(frozen=True, slots=True)
class MaterialRegion:
    """A scoped material-definition grouping, not a physical geometry occurrence."""

    id: str
    label: str
    role: MaterialRegionRole
    orientation: MaterialOrientationRule | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.id, "MaterialRegion.id")
        validate_label(self.label, "MaterialRegion.label")
        require_enum(self.role, MaterialRegionRole, "MaterialRegion.role")
        if self.orientation is not None and not isinstance(
            self.orientation,
            (PlanarFixedMaterialOrientation, CylindricalMaterialOrientation),
        ):
            raise TypeError("MaterialRegion.orientation must be a material-orientation rule.")


@dataclass(frozen=True, slots=True)
class SectionTopology:
    """Explicit immutable physical elements and their scoped material regions."""

    source: SectionTopologySource
    elements: tuple[PhysicalSectionElement, ...]
    material_regions: tuple[MaterialRegion, ...]
    standard_family: SectionFamily | None = None

    def __post_init__(self) -> None:
        require_enum(self.source, SectionTopologySource, "SectionTopology.source")
        if self.source is SectionTopologySource.STANDARD:
            if self.standard_family is None:
                raise ValueError("Standard section topology requires standard_family.")
            require_enum(self.standard_family, SectionFamily, "SectionTopology.standard_family")
            if self.standard_family is SectionFamily.CUSTOM:
                raise ValueError("Standard section topology cannot use the CUSTOM family.")
        elif self.standard_family is not None:
            raise ValueError("Custom section topology must not declare standard_family.")

        require_tuple(self.elements, "SectionTopology.elements")
        if not self.elements:
            raise ValueError("SectionTopology.elements must contain at least one element.")
        for element in self.elements:
            if not isinstance(element, PhysicalSectionElement):
                raise TypeError(
                    "SectionTopology.elements items must be PhysicalSectionElement values."
                )

        require_tuple(self.material_regions, "SectionTopology.material_regions")
        if not self.material_regions:
            raise ValueError(
                "SectionTopology.material_regions must contain at least one material region."
            )
        for region in self.material_regions:
            if not isinstance(region, MaterialRegion):
                raise TypeError(
                    "SectionTopology.material_regions items must be MaterialRegion values."
                )

    def validate(self, path: str = "section_topology") -> tuple[ValidationIssue, ...]:
        """Return scoped topology issues in deterministic logical-path order."""
        validate_label(path, "SectionTopology.validate.path")
        issues: list[ValidationIssue] = []

        seen_element_ids: set[str] = set()
        for index, element in enumerate(self.elements):
            if element.id in seen_element_ids:
                issues.append(
                    ValidationIssue(
                        ValidationCode.DUPLICATE_SECTION_ELEMENT_ID,
                        f"Duplicate physical section element id {element.id!r}.",
                        f"{path}.elements[{index}].id",
                        element.id,
                    )
                )
            seen_element_ids.add(element.id)

        seen_region_ids: set[str] = set()
        for index, region in enumerate(self.material_regions):
            if region.id in seen_region_ids:
                issues.append(
                    ValidationIssue(
                        ValidationCode.DUPLICATE_MATERIAL_REGION_ID,
                        f"Duplicate material region id {region.id!r}.",
                        f"{path}.material_regions[{index}].id",
                        region.id,
                    )
                )
            seen_region_ids.add(region.id)

        declared_region_ids = {region.id for region in self.material_regions}
        referenced_region_ids: set[str] = set()
        for index, element in enumerate(self.elements):
            referenced_region_ids.add(element.material_region_id)
            if element.material_region_id not in declared_region_ids:
                issues.append(
                    ValidationIssue(
                        ValidationCode.UNRESOLVED_MATERIAL_REGION,
                        (
                            f"Material region {element.material_region_id!r} referenced by "
                            f"element {element.id!r} is not declared in this topology."
                        ),
                        f"{path}.elements[{index}].material_region_id",
                        element.material_region_id,
                    )
                )

        for index, region in enumerate(self.material_regions):
            if region.id not in referenced_region_ids:
                issues.append(
                    ValidationIssue(
                        ValidationCode.ORPHAN_MATERIAL_REGION,
                        f"Material region {region.id!r} is not referenced by any element.",
                        f"{path}.material_regions[{index}]",
                        region.id,
                    )
                )

        if self.source is SectionTopologySource.STANDARD:
            standard_family = cast(SectionFamily, self.standard_family)
            expected_elements, expected_regions = _standard_definition(standard_family)
            actual_elements = tuple(
                (element.id, element.role, element.material_region_id) for element in self.elements
            )
            expected_element_membership = tuple(
                (element_role.value, element_role, region_role.value)
                for element_role, region_role in expected_elements
            )
            actual_regions = tuple((region.id, region.role) for region in self.material_regions)
            expected_region_definitions = tuple((role.value, role) for role in expected_regions)
            if (
                actual_elements != expected_element_membership
                or actual_regions != expected_region_definitions
            ):
                issues.append(
                    ValidationIssue(
                        ValidationCode.INVALID_STANDARD_SECTION_TOPOLOGY,
                        (
                            f"Stored topology does not match the canonical "
                            f"{standard_family.value} symbolic definition."
                        ),
                        path,
                    )
                )

        return order_issues(issues)


type _StandardElementDefinition = tuple[tuple[PhysicalSectionElementRole, MaterialRegionRole], ...]


def _standard_definition(
    section_family: SectionFamily,
) -> tuple[_StandardElementDefinition, tuple[MaterialRegionRole, ...]]:
    if section_family in {
        SectionFamily.WIDE_FLANGE,
        SectionFamily.I_SECTION,
        SectionFamily.CHANNEL,
    }:
        return (
            (
                (PhysicalSectionElementRole.WEB, MaterialRegionRole.WEB),
                (PhysicalSectionElementRole.TOP_FLANGE, MaterialRegionRole.FLANGES),
                (PhysicalSectionElementRole.BOTTOM_FLANGE, MaterialRegionRole.FLANGES),
            ),
            (MaterialRegionRole.WEB, MaterialRegionRole.FLANGES),
        )
    if section_family is SectionFamily.TEE:
        return (
            (
                (PhysicalSectionElementRole.STEM, MaterialRegionRole.STEM),
                (PhysicalSectionElementRole.FLANGE, MaterialRegionRole.FLANGE),
            ),
            (MaterialRegionRole.STEM, MaterialRegionRole.FLANGE),
        )
    if section_family is SectionFamily.RECTANGULAR_TUBE:
        return (
            (
                (PhysicalSectionElementRole.TOP_WALL, MaterialRegionRole.WALL_PAIR_1),
                (PhysicalSectionElementRole.BOTTOM_WALL, MaterialRegionRole.WALL_PAIR_1),
                (PhysicalSectionElementRole.SIDE_WALL_1, MaterialRegionRole.WALL_PAIR_2),
                (PhysicalSectionElementRole.SIDE_WALL_2, MaterialRegionRole.WALL_PAIR_2),
            ),
            (MaterialRegionRole.WALL_PAIR_1, MaterialRegionRole.WALL_PAIR_2),
        )
    if section_family is SectionFamily.ANGLE:
        return (
            (
                (PhysicalSectionElementRole.LEG_1, MaterialRegionRole.LEG_1),
                (PhysicalSectionElementRole.LEG_2, MaterialRegionRole.LEG_2),
            ),
            (MaterialRegionRole.LEG_1, MaterialRegionRole.LEG_2),
        )
    if section_family is SectionFamily.PLATE:
        return (
            ((PhysicalSectionElementRole.PLATE, MaterialRegionRole.PLATE),),
            (MaterialRegionRole.PLATE,),
        )
    if section_family is SectionFamily.ROUND_TUBE:
        return (
            (
                (
                    PhysicalSectionElementRole.CURVED_WALL,
                    MaterialRegionRole.CYLINDRICAL_WALL,
                ),
            ),
            (MaterialRegionRole.CYLINDRICAL_WALL,),
        )
    raise ValueError(f"No standard symbolic topology exists for {section_family.value}.")


def create_standard_section_topology(
    section_family: SectionFamily,
    *,
    orientations: Mapping[MaterialRegionRole, MaterialOrientationRule] | None = None,
) -> SectionTopology:
    """Create explicit canonical symbolic data for one supported standard family."""
    require_enum(section_family, SectionFamily, "section_family")
    element_definitions, region_roles = _standard_definition(section_family)
    supplied_orientations = {} if orientations is None else orientations
    if not isinstance(supplied_orientations, Mapping):
        raise TypeError("orientations must be a mapping of material-region roles to rules.")
    for role, orientation in supplied_orientations.items():
        require_enum(role, MaterialRegionRole, "orientations key")
        if role not in region_roles:
            raise ValueError(
                f"Orientation role {role.value} is not present in {section_family.value}."
            )
        if not isinstance(
            orientation,
            (PlanarFixedMaterialOrientation, CylindricalMaterialOrientation),
        ):
            raise TypeError("orientations values must be material-orientation rules.")
        if section_family is SectionFamily.ROUND_TUBE:
            if not isinstance(orientation, CylindricalMaterialOrientation):
                raise ValueError("Round-tube orientation must be CYLINDRICAL.")
        elif not isinstance(orientation, PlanarFixedMaterialOrientation):
            raise ValueError("Standard flat-element regions require PLANAR_FIXED orientation.")

    regions = tuple(
        MaterialRegion(
            id=role.value,
            label=role.value.replace("_", " ").title(),
            role=role,
            orientation=supplied_orientations.get(role),
        )
        for role in region_roles
    )
    elements = tuple(
        PhysicalSectionElement(
            id=element_role.value,
            label=element_role.value.replace("_", " ").title(),
            role=element_role,
            material_region_id=region_role.value,
        )
        for element_role, region_role in element_definitions
    )
    return SectionTopology(
        source=SectionTopologySource.STANDARD,
        elements=elements,
        material_regions=regions,
        standard_family=section_family,
    )


def create_region_specific_planar_orientations(
    family: SectionFamily,
    crosswise_axis: PrincipalAxisFamily,
    through_thickness_axis: PrincipalAxisFamily,
) -> dict[MaterialRegionRole, PlanarFixedMaterialOrientation]:
    """Resolve exact planar bases for parallel and perpendicular profile regions."""

    require_enum(family, SectionFamily, "family")
    base = PlanarFixedMaterialOrientation(crosswise_axis, through_thickness_axis)
    topology = create_standard_section_topology(family)
    perpendicular_regions = {
        SectionFamily.WIDE_FLANGE: {MaterialRegionRole.WEB},
        SectionFamily.I_SECTION: {MaterialRegionRole.WEB},
        SectionFamily.TEE: {MaterialRegionRole.STEM},
        SectionFamily.ANGLE: {MaterialRegionRole.LEG_2},
        SectionFamily.CHANNEL: {MaterialRegionRole.WEB},
        SectionFamily.RECTANGULAR_TUBE: {MaterialRegionRole.WALL_PAIR_2},
    }.get(family, set())
    return {
        region.role: (
            PlanarFixedMaterialOrientation(
                through_thickness_axis,
                crosswise_axis,
                -1,
                1,
            )
            if region.role in perpendicular_regions
            else base
        )
        for region in topology.material_regions
    }


__all__ = (
    "CylindricalMaterialOrientation",
    "FRPComponentOrientation",
    "MaterialOrientationKind",
    "MaterialOrientationRule",
    "MaterialRegion",
    "MaterialRegionRole",
    "PhysicalSectionElement",
    "PhysicalSectionElementRole",
    "PlanarFixedMaterialOrientation",
    "SectionTopology",
    "SectionTopologySource",
    "create_region_specific_planar_orientations",
    "create_standard_section_topology",
)
