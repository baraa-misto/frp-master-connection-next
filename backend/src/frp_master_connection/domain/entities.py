"""Immutable entities for joint assembly and symbolic section-topology contracts."""

from dataclasses import dataclass

from frp_master_connection.domain.section_topology import (
    CylindricalMaterialOrientation,
    FRPComponentOrientation,
    PlanarFixedMaterialOrientation,
    SectionTopology,
    SectionTopologySource,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import (
    ActionConvention,
    ComponentMaterialKind,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ForceVector3D,
    LoadInputBasis,
    MemberEnd,
    MemberRole,
    MomentVector3D,
    ParticipantKind,
    PositionVector3D,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SupportKind,
    TransferIntent,
)


def _validate_component_material_contract(
    *,
    entity_id: str,
    material_kind: ComponentMaterialKind,
    material_orientation: FRPComponentOrientation | None,
    section_topology: SectionTopology | None,
    expected_frame_kind: CoordinateFrameKind,
    field_name: str,
) -> None:
    require_enum(material_kind, ComponentMaterialKind, f"{field_name}.material_kind")
    if section_topology is not None and not isinstance(section_topology, SectionTopology):
        raise TypeError(f"{field_name}.section_topology must be SectionTopology.")
    if material_kind is ComponentMaterialKind.PULTRUDED_FRP:
        if material_orientation is None:
            raise ValueError(f"{field_name}.material_orientation is required for pultruded FRP.")
        if not isinstance(material_orientation, FRPComponentOrientation):
            raise TypeError(f"{field_name}.material_orientation must be FRPComponentOrientation.")
        if (
            material_orientation.coordinate_frame.kind is not expected_frame_kind
            or material_orientation.coordinate_frame.owner_id != entity_id
        ):
            raise ValueError(
                f"{field_name}.material_orientation must use this component's matching local frame."
            )
        if section_topology is None:
            raise ValueError(f"{field_name}.section_topology is required for pultruded FRP.")
        for region in section_topology.material_regions:
            if region.orientation is None:
                raise ValueError(
                    f"{field_name} pultruded-FRP material regions require orientation rules."
                )
            if isinstance(
                region.orientation, PlanarFixedMaterialOrientation
            ) and material_orientation.lengthwise_axis in {
                region.orientation.crosswise_axis,
                region.orientation.through_thickness_axis,
            }:
                raise ValueError(
                    f"{field_name} planar LW, CW, and TT must use three distinct axis families."
                )
        if section_topology.source is SectionTopologySource.STANDARD:
            if section_topology.standard_family is SectionFamily.ROUND_TUBE:
                if any(
                    not isinstance(region.orientation, CylindricalMaterialOrientation)
                    for region in section_topology.material_regions
                ):
                    raise ValueError(
                        f"{field_name} standard round-tube regions require CYLINDRICAL orientation."
                    )
            elif any(
                not isinstance(region.orientation, PlanarFixedMaterialOrientation)
                for region in section_topology.material_regions
            ):
                raise ValueError(
                    f"{field_name} standard flat-element regions require PLANAR_FIXED orientation."
                )
    else:
        if material_orientation is not None:
            raise ValueError(
                f"{field_name}.material_orientation is only permitted for pultruded FRP."
            )
        if section_topology is not None and any(
            region.orientation is not None for region in section_topology.material_regions
        ):
            raise ValueError(
                f"{field_name} non-FRP material regions must not contain FRP orientation rules."
            )


@dataclass(frozen=True, slots=True)
class AssemblyMember:
    """A member participating in the connection assembly."""

    id: str
    label: str
    role: MemberRole
    connected_end: MemberEnd
    section_family: SectionFamily
    material_kind: ComponentMaterialKind
    material_orientation: FRPComponentOrientation | None = None
    section_topology: SectionTopology | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.id, "AssemblyMember.id")
        validate_label(self.label, "AssemblyMember.label")
        require_enum(self.role, MemberRole, "AssemblyMember.role")
        require_enum(self.connected_end, MemberEnd, "AssemblyMember.connected_end")
        require_enum(self.section_family, SectionFamily, "AssemblyMember.section_family")
        _validate_component_material_contract(
            entity_id=self.id,
            material_kind=self.material_kind,
            material_orientation=self.material_orientation,
            section_topology=self.section_topology,
            expected_frame_kind=CoordinateFrameKind.MEMBER_LOCAL,
            field_name="AssemblyMember",
        )
        if (
            self.section_topology is not None
            and self.section_topology.source is SectionTopologySource.STANDARD
            and self.section_topology.standard_family is not self.section_family
        ):
            raise ValueError("AssemblyMember standard section topology must match section_family.")


@dataclass(frozen=True, slots=True)
class ConnectorComponent:
    """A plate, angle, tee, doubler, or other connector component."""

    id: str
    label: str
    kind: ConnectorComponentKind
    material_kind: ComponentMaterialKind
    material_orientation: FRPComponentOrientation | None = None
    section_topology: SectionTopology | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.id, "ConnectorComponent.id")
        validate_label(self.label, "ConnectorComponent.label")
        require_enum(self.kind, ConnectorComponentKind, "ConnectorComponent.kind")
        _validate_component_material_contract(
            entity_id=self.id,
            material_kind=self.material_kind,
            material_orientation=self.material_orientation,
            section_topology=self.section_topology,
            expected_frame_kind=CoordinateFrameKind.CONNECTOR_LOCAL,
            field_name="ConnectorComponent",
        )


@dataclass(frozen=True, slots=True)
class AssemblySupport:
    """A concrete, foundation, or other support participating in the assembly."""

    id: str
    label: str
    kind: SupportKind

    def __post_init__(self) -> None:
        validate_identifier(self.id, "AssemblySupport.id")
        validate_label(self.label, "AssemblySupport.label")
        require_enum(self.kind, SupportKind, "AssemblySupport.kind")


@dataclass(frozen=True, slots=True)
class ParticipantReference:
    """A typed reference to an interface participant."""

    kind: ParticipantKind
    entity_id: str

    def __post_init__(self) -> None:
        require_enum(self.kind, ParticipantKind, "ParticipantReference.kind")
        validate_identifier(self.entity_id, "ParticipantReference.entity_id")


@dataclass(frozen=True, slots=True)
class ConnectionInterface:
    """A declared direct transfer path between two distinct participants."""

    id: str
    label: str
    participant_a: ParticipantReference
    participant_b: ParticipantReference
    transfer_intent: TransferIntent

    def __post_init__(self) -> None:
        validate_identifier(self.id, "ConnectionInterface.id")
        validate_label(self.label, "ConnectionInterface.label")
        if not isinstance(self.participant_a, ParticipantReference):
            raise TypeError("ConnectionInterface.participant_a must be a participant reference.")
        if not isinstance(self.participant_b, ParticipantReference):
            raise TypeError("ConnectionInterface.participant_b must be a participant reference.")
        if self.participant_a == self.participant_b:
            raise ValueError("A connection interface cannot reference one participant twice.")
        require_enum(self.transfer_intent, TransferIntent, "ConnectionInterface.transfer_intent")


@dataclass(frozen=True, slots=True)
class BoltLocation:
    """A bolt-center location in its owning bolt group's declared local frame."""

    id: str
    position: PositionVector3D

    def __post_init__(self) -> None:
        validate_identifier(self.id, "BoltLocation.id")
        if not isinstance(self.position, PositionVector3D):
            raise TypeError("BoltLocation.position must be a PositionVector3D.")


@dataclass(frozen=True, slots=True)
class BoltGroup:
    """An explicit bolt group associated with one or more declared interfaces."""

    id: str
    label: str
    coordinate_frame: CoordinateFrameReference
    reference_point: ReferencePoint
    interface_ids: tuple[str, ...]
    locations: tuple[BoltLocation, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.id, "BoltGroup.id")
        validate_label(self.label, "BoltGroup.label")
        if not isinstance(self.coordinate_frame, CoordinateFrameReference):
            raise TypeError("BoltGroup.coordinate_frame must be a frame reference.")
        if (
            self.coordinate_frame.kind is not CoordinateFrameKind.BOLT_GROUP_LOCAL
            or self.coordinate_frame.owner_id != self.id
        ):
            raise ValueError("BoltGroup.coordinate_frame must be this bolt group's local frame.")
        if not isinstance(self.reference_point, ReferencePoint):
            raise TypeError("BoltGroup.reference_point must be a reference point.")
        if self.reference_point.kind is ReferencePointKind.BOLT_GROUP_ORIGIN:
            if self.reference_point.owner_id != self.id:
                raise ValueError("A bolt-group-origin reference point must name this bolt group.")
        elif self.reference_point.kind is not ReferencePointKind.EXPLICIT_POINT:
            raise ValueError("A bolt group requires its origin or an explicit reference point.")
        require_tuple(self.interface_ids, "BoltGroup.interface_ids")
        if not self.interface_ids:
            raise ValueError("BoltGroup.interface_ids must contain at least one interface id.")
        for interface_id in self.interface_ids:
            validate_identifier(interface_id, "BoltGroup.interface_ids item")
        if len(set(self.interface_ids)) != len(self.interface_ids):
            raise ValueError("BoltGroup.interface_ids must not contain duplicates.")
        require_tuple(self.locations, "BoltGroup.locations")
        if not self.locations:
            raise ValueError("BoltGroup.locations must contain at least one bolt location.")
        for location in self.locations:
            if not isinstance(location, BoltLocation):
                raise TypeError("BoltGroup.locations items must be BoltLocation values.")
        location_ids = [location.id for location in self.locations]
        if len(set(location_ids)) != len(location_ids):
            raise ValueError("Bolt location ids must be unique within a bolt group.")


@dataclass(frozen=True, slots=True)
class LoadCombination:
    """A named factored-strength load combination."""

    id: str
    label: str
    input_basis: LoadInputBasis

    def __post_init__(self) -> None:
        validate_identifier(self.id, "LoadCombination.id")
        validate_label(self.label, "LoadCombination.label")
        require_enum(self.input_basis, LoadInputBasis, "LoadCombination.input_basis")


@dataclass(frozen=True, slots=True)
class ManualMemberEndAction:
    """One complete manually entered six-component member-end action."""

    id: str
    member_id: str
    member_end: MemberEnd
    load_combination_id: str
    coordinate_frame: CoordinateFrameReference
    reference_point: ReferencePoint
    force: ForceVector3D
    moment: MomentVector3D
    convention: ActionConvention

    def __post_init__(self) -> None:
        validate_identifier(self.id, "ManualMemberEndAction.id")
        validate_identifier(self.member_id, "ManualMemberEndAction.member_id")
        require_enum(self.member_end, MemberEnd, "ManualMemberEndAction.member_end")
        validate_identifier(
            self.load_combination_id,
            "ManualMemberEndAction.load_combination_id",
        )
        if not isinstance(self.coordinate_frame, CoordinateFrameReference):
            raise TypeError("ManualMemberEndAction.coordinate_frame must be a frame reference.")
        if not isinstance(self.reference_point, ReferencePoint):
            raise TypeError("ManualMemberEndAction.reference_point must be a reference point.")
        if not isinstance(self.force, ForceVector3D):
            raise TypeError("ManualMemberEndAction.force must be a ForceVector3D.")
        if not isinstance(self.moment, MomentVector3D):
            raise TypeError("ManualMemberEndAction.moment must be a MomentVector3D.")
        require_enum(self.convention, ActionConvention, "ManualMemberEndAction.convention")


__all__ = (
    "AssemblyMember",
    "AssemblySupport",
    "BoltGroup",
    "BoltLocation",
    "ConnectionInterface",
    "ConnectorComponent",
    "LoadCombination",
    "ManualMemberEndAction",
    "ParticipantReference",
)
