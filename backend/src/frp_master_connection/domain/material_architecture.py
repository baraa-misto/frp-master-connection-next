"""Stage 3.1 connector, fastener, source, and assembly architecture contracts.

These contracts sit above the accepted Stage 2 calculation snapshots.  They add
material-family and resistance-authority identity without changing any existing
equation input, result, or fingerprint contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from frp_master_connection.domain.assembly import JointAssembly
from frp_master_connection.domain.entities import ConnectorComponent, ParticipantReference
from frp_master_connection.domain.section_topology import (
    CylindricalMaterialOrientation,
    PlanarFixedMaterialOrientation,
)
from frp_master_connection.domain.validation import (
    require_enum,
    require_tuple,
    validate_identifier,
)
from frp_master_connection.domain.values import ComponentMaterialKind, ParticipantKind

CONNECTION_PLATFORM_CONTRACT_VERSION = "3.1-RC1"
CONNECTOR_MATERIAL_SCHEMA_VERSION = "0.1.0-draft"
FASTENER_SYSTEM_SCHEMA_VERSION = "0.1.0-draft"
CONNECTION_ASSEMBLY_SCHEMA_VERSION = "0.1.0-draft"

_SHA256_PATTERN = re.compile(r"[0-9A-F]{64}\Z")


class EngineeringCoverageClass(StrEnum):
    """Roadmap-level coverage; detailed calculation statuses remain authoritative."""

    PRESCRIPTIVE = "PRESCRIPTIVE"
    QUALIFICATION_REQUIRED = "QUALIFICATION_REQUIRED"
    CROSS_CODE = "CROSS_CODE"
    RESEARCH_OR_PROPRIETARY = "RESEARCH_OR_PROPRIETARY"


class ConnectorMaterialFamily(StrEnum):
    """Exact initial connector-material identities without implied properties."""

    PULTRUDED_FRP = "PULTRUDED_FRP"
    STAINLESS_STEEL_316 = "STAINLESS_STEEL_316"
    CARBON_STEEL = "CARBON_STEEL"


class FastenerMaterialFamily(StrEnum):
    """Exact initial fastener-material identities without implied grade or strength."""

    STAINLESS_STEEL_316 = "STAINLESS_STEEL_316"
    CARBON_STEEL = "CARBON_STEEL"
    CUSTOM_FRP = "CUSTOM_FRP"


class MaterialBehaviorFamily(StrEnum):
    """Constitutive behavior identity, separate from a strength database."""

    DIRECTIONAL_FRP = "DIRECTIONAL_FRP"
    ISOTROPIC_METAL = "ISOTROPIC_METAL"
    CUSTOM_FASTENER_MATERIAL = "CUSTOM_FASTENER_MATERIAL"


class EngineeringPropertySourceKind(StrEnum):
    """Generic provenance kinds for controlled engineering properties."""

    CONTROLLED_PROJECT_DATA = "CONTROLLED_PROJECT_DATA"
    MANUFACTURER_DATA = "MANUFACTURER_DATA"
    STANDARD_OR_GRADE_DATA = "STANDARD_OR_GRADE_DATA"
    TEST_QUALIFIED_DATA = "TEST_QUALIFIED_DATA"
    CUSTOM_ENGINEERING_DATA = "CUSTOM_ENGINEERING_DATA"


class PropertySourceConfirmation(StrEnum):
    """Confirmation state for a property source, independent from its source kind."""

    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ENGINEER_APPROVED = "ENGINEER_APPROVED"
    TEST_QUALIFIED = "TEST_QUALIFIED"


class ConnectorComponentRole(StrEnum):
    """Role of a connector component in a connection assembly."""

    PRIMARY_CONNECTOR = "PRIMARY_CONNECTOR"
    REINFORCEMENT = "REINFORCEMENT"
    ADAPTER = "ADAPTER"
    OTHER = "OTHER"


class ResistanceCalculationFamily(StrEnum):
    """Existing or future calculation families addressable by an authority."""

    EXISTING_METALLIC_BOLT = "EXISTING_METALLIC_BOLT"
    EXISTING_FRP_CONNECTION = "EXISTING_FRP_CONNECTION"
    CUSTOM_QUALIFIED_FASTENER = "CUSTOM_QUALIFIED_FASTENER"


class ResistanceAuthorityKind(StrEnum):
    """Narrow identity describing which resistance family may be considered."""

    EXISTING_METALLIC_BOLT_AUTHORITY = "EXISTING_METALLIC_BOLT_AUTHORITY"
    EXISTING_FRP_CONNECTION_AUTHORITY = "EXISTING_FRP_CONNECTION_AUTHORITY"
    CUSTOM_QUALIFIED_FASTENER_AUTHORITY = "CUSTOM_QUALIFIED_FASTENER_AUTHORITY"
    NO_AUTOMATIC_RESISTANCE_AUTHORITY = "NO_AUTOMATIC_RESISTANCE_AUTHORITY"


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a Boolean value.")


def _require_identifier_tuple(
    value: object,
    field_name: str,
    *,
    allow_empty: bool = True,
) -> None:
    require_tuple(value, field_name)
    identifiers = cast(tuple[object, ...], value)
    if not allow_empty and not identifiers:
        raise ValueError(f"{field_name} must not be empty.")
    for identifier in identifiers:
        validate_identifier(identifier, f"{field_name} item")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(f"{field_name} must not contain duplicates.")


@dataclass(frozen=True, slots=True)
class EngineeringPropertySource:
    """Deeply immutable identity for project, maker, standard, test, or custom data."""

    kind: EngineeringPropertySourceKind
    source_id: str
    revision: str
    confirmation: PropertySourceConfirmation
    provenance_reference_ids: tuple[str, ...]
    qualification_required: bool
    controlling_artifact_sha256: str | None = None
    approval_authority_id: str | None = None
    qualification_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_enum(self.kind, EngineeringPropertySourceKind, "EngineeringPropertySource.kind")
        validate_identifier(self.source_id, "EngineeringPropertySource.source_id")
        validate_identifier(self.revision, "EngineeringPropertySource.revision")
        require_enum(
            self.confirmation,
            PropertySourceConfirmation,
            "EngineeringPropertySource.confirmation",
        )
        _require_identifier_tuple(
            self.provenance_reference_ids,
            "EngineeringPropertySource.provenance_reference_ids",
        )
        _require_bool(
            self.qualification_required,
            "EngineeringPropertySource.qualification_required",
        )
        if (
            self.controlling_artifact_sha256 is not None
            and _SHA256_PATTERN.fullmatch(self.controlling_artifact_sha256) is None
        ):
            raise ValueError(
                "EngineeringPropertySource.controlling_artifact_sha256 must be 64 uppercase "
                "hexadecimal characters."
            )
        if self.approval_authority_id is not None:
            validate_identifier(
                self.approval_authority_id,
                "EngineeringPropertySource.approval_authority_id",
            )
        if (
            self.confirmation
            in {
                PropertySourceConfirmation.ENGINEER_APPROVED,
                PropertySourceConfirmation.TEST_QUALIFIED,
            }
            and self.approval_authority_id is None
        ):
            raise ValueError("An approved or test-qualified source requires approval authority.")
        if self.confirmation is PropertySourceConfirmation.TEST_QUALIFIED and (
            self.kind is not EngineeringPropertySourceKind.TEST_QUALIFIED_DATA
        ):
            raise ValueError("TEST_QUALIFIED confirmation requires TEST_QUALIFIED_DATA.")
        _require_identifier_tuple(
            self.qualification_record_ids,
            "EngineeringPropertySource.qualification_record_ids",
        )


@dataclass(frozen=True, slots=True)
class ConnectorMaterialAssignment:
    """Exact connector material assignment, independent from connector topology."""

    assignment_id: str
    component_id: str
    family: ConnectorMaterialFamily
    behavior: MaterialBehaviorFamily
    property_source: EngineeringPropertySource
    coverage: EngineeringCoverageClass

    def __post_init__(self) -> None:
        validate_identifier(self.assignment_id, "ConnectorMaterialAssignment.assignment_id")
        validate_identifier(self.component_id, "ConnectorMaterialAssignment.component_id")
        require_enum(self.family, ConnectorMaterialFamily, "ConnectorMaterialAssignment.family")
        require_enum(self.behavior, MaterialBehaviorFamily, "ConnectorMaterialAssignment.behavior")
        if not isinstance(self.property_source, EngineeringPropertySource):
            raise TypeError(
                "ConnectorMaterialAssignment.property_source must be an engineering source."
            )
        require_enum(
            self.coverage, EngineeringCoverageClass, "ConnectorMaterialAssignment.coverage"
        )
        expected = (
            MaterialBehaviorFamily.DIRECTIONAL_FRP
            if self.family is ConnectorMaterialFamily.PULTRUDED_FRP
            else MaterialBehaviorFamily.ISOTROPIC_METAL
        )
        if self.behavior is not expected:
            raise ValueError("Connector material family and behavior are inconsistent.")


@dataclass(frozen=True, slots=True)
class FastenerMaterialAssignment:
    """Exact fastener material assignment, independent from fastener geometry."""

    assignment_id: str
    family: FastenerMaterialFamily
    behavior: MaterialBehaviorFamily
    property_source: EngineeringPropertySource
    coverage: EngineeringCoverageClass

    def __post_init__(self) -> None:
        validate_identifier(self.assignment_id, "FastenerMaterialAssignment.assignment_id")
        require_enum(self.family, FastenerMaterialFamily, "FastenerMaterialAssignment.family")
        require_enum(self.behavior, MaterialBehaviorFamily, "FastenerMaterialAssignment.behavior")
        if not isinstance(self.property_source, EngineeringPropertySource):
            raise TypeError(
                "FastenerMaterialAssignment.property_source must be an engineering source."
            )
        require_enum(self.coverage, EngineeringCoverageClass, "FastenerMaterialAssignment.coverage")
        expected = (
            MaterialBehaviorFamily.CUSTOM_FASTENER_MATERIAL
            if self.family is FastenerMaterialFamily.CUSTOM_FRP
            else MaterialBehaviorFamily.ISOTROPIC_METAL
        )
        if self.behavior is not expected:
            raise ValueError("Fastener material family and behavior are inconsistent.")


@dataclass(frozen=True, slots=True)
class EngineeringGeometryReference:
    """Stable geometry/source identity without presentation-only proportions."""

    geometry_id: str
    source: EngineeringPropertySource
    authoritative: bool

    def __post_init__(self) -> None:
        validate_identifier(self.geometry_id, "EngineeringGeometryReference.geometry_id")
        if not isinstance(self.source, EngineeringPropertySource):
            raise TypeError("EngineeringGeometryReference.source must be an engineering source.")
        _require_bool(self.authoritative, "EngineeringGeometryReference.authoritative")


@dataclass(frozen=True, slots=True)
class ResistanceAuthority:
    """Explicit capability gate; a material label never grants equation authority."""

    authority_id: str
    kind: ResistanceAuthorityKind
    approved_for_use: bool
    source: EngineeringPropertySource | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.authority_id, "ResistanceAuthority.authority_id")
        require_enum(self.kind, ResistanceAuthorityKind, "ResistanceAuthority.kind")
        _require_bool(self.approved_for_use, "ResistanceAuthority.approved_for_use")
        if self.kind is ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY:
            if self.approved_for_use or self.source is not None:
                raise ValueError("No-automatic-resistance authority cannot be approved or sourced.")
        elif not isinstance(self.source, EngineeringPropertySource):
            raise TypeError("A resistance authority requires an engineering property source.")
        elif self.approved_for_use and self.source.confirmation not in {
            PropertySourceConfirmation.ENGINEER_APPROVED,
            PropertySourceConfirmation.TEST_QUALIFIED,
        }:
            raise ValueError("Approved resistance authority requires an approved source.")

    def permits(self, family: ResistanceCalculationFamily) -> bool:
        """Return whether this approved authority names the requested calculation family."""

        require_enum(family, ResistanceCalculationFamily, "ResistanceAuthority.permits.family")
        if not self.approved_for_use:
            return False
        mapping = {
            ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY: (
                ResistanceCalculationFamily.EXISTING_METALLIC_BOLT
            ),
            ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY: (
                ResistanceCalculationFamily.EXISTING_FRP_CONNECTION
            ),
            ResistanceAuthorityKind.CUSTOM_QUALIFIED_FASTENER_AUTHORITY: (
                ResistanceCalculationFamily.CUSTOM_QUALIFIED_FASTENER
            ),
        }
        return mapping.get(self.kind) is family


@dataclass(frozen=True, slots=True)
class ConnectorComponentEngineeringAssignment:
    """Stage 3 engineering assignment layered onto the accepted connector entity."""

    component: ConnectorComponent
    material: ConnectorMaterialAssignment
    role: ConnectorComponentRole
    geometry: EngineeringGeometryReference
    resistance_authority: ResistanceAuthority
    provenance: EngineeringPropertySource

    def __post_init__(self) -> None:
        if not isinstance(self.component, ConnectorComponent):
            raise TypeError("Connector engineering assignment requires a ConnectorComponent.")
        if not isinstance(self.material, ConnectorMaterialAssignment):
            raise TypeError("Connector engineering assignment requires a material assignment.")
        if self.material.component_id != self.component.id:
            raise ValueError("Connector material assignment must reference its component.")
        require_enum(
            self.role, ConnectorComponentRole, "ConnectorComponentEngineeringAssignment.role"
        )
        if not isinstance(self.geometry, EngineeringGeometryReference):
            raise TypeError("Connector engineering assignment requires a geometry reference.")
        if not isinstance(self.resistance_authority, ResistanceAuthority):
            raise TypeError("Connector engineering assignment requires resistance authority.")
        if not isinstance(self.provenance, EngineeringPropertySource):
            raise TypeError("Connector engineering assignment requires provenance.")
        expected_kind = (
            ComponentMaterialKind.PULTRUDED_FRP
            if self.material.family is ConnectorMaterialFamily.PULTRUDED_FRP
            else ComponentMaterialKind.STEEL
        )
        if self.component.material_kind is not expected_kind:
            raise ValueError(
                "Connector exact material family conflicts with its coarse material kind."
            )
        allowed_authorities = (
            {
                ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY,
                ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            }
            if self.material.family is ConnectorMaterialFamily.PULTRUDED_FRP
            else {ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY}
        )
        if self.resistance_authority.kind not in allowed_authorities:
            raise ValueError("Connector material family and resistance authority are inconsistent.")


@dataclass(frozen=True, slots=True)
class FastenerSystem:
    """Physical fastener identity above the accepted Stage 2 calculation snapshot."""

    system_id: str
    material: FastenerMaterialAssignment
    geometry: EngineeringGeometryReference
    resistance_authority: ResistanceAuthority
    engineering_property_snapshot_id: str | None
    provenance: EngineeringPropertySource
    washer_source: EngineeringPropertySource | None = None
    head_source: EngineeringPropertySource | None = None
    nut_source: EngineeringPropertySource | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.system_id, "FastenerSystem.system_id")
        if not isinstance(self.material, FastenerMaterialAssignment):
            raise TypeError("FastenerSystem.material must be a fastener material assignment.")
        if not isinstance(self.geometry, EngineeringGeometryReference):
            raise TypeError("FastenerSystem.geometry must be a geometry reference.")
        if not isinstance(self.resistance_authority, ResistanceAuthority):
            raise TypeError("FastenerSystem.resistance_authority must be resistance authority.")
        if self.engineering_property_snapshot_id is not None:
            validate_identifier(
                self.engineering_property_snapshot_id,
                "FastenerSystem.engineering_property_snapshot_id",
            )
        if not isinstance(self.provenance, EngineeringPropertySource):
            raise TypeError("FastenerSystem.provenance must be an engineering source.")
        for name, source in (
            ("washer_source", self.washer_source),
            ("head_source", self.head_source),
            ("nut_source", self.nut_source),
        ):
            if source is not None and not isinstance(source, EngineeringPropertySource):
                raise TypeError(f"FastenerSystem.{name} must be an engineering source.")
        allowed_authorities = (
            {
                ResistanceAuthorityKind.CUSTOM_QUALIFIED_FASTENER_AUTHORITY,
                ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            }
            if self.material.family is FastenerMaterialFamily.CUSTOM_FRP
            else {
                ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY,
                ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            }
        )
        if self.resistance_authority.kind not in allowed_authorities:
            raise ValueError("Fastener material family and resistance authority are inconsistent.")

    @property
    def coverage(self) -> EngineeringCoverageClass:
        """Return the high-level coverage carried by the material assignment."""

        return self.material.coverage

    @property
    def declares_existing_metallic_bolt_compatibility(self) -> bool:
        """Return a handoff declaration, not final equation eligibility.

        The calculation-layer resolver must still inspect the accepted snapshot and
        every existing Stage 2 prerequisite before exposing that snapshot.
        """

        return (
            self.material.family
            in {
                FastenerMaterialFamily.STAINLESS_STEEL_316,
                FastenerMaterialFamily.CARBON_STEEL,
            }
            and self.engineering_property_snapshot_id is not None
            and self.geometry.authoritative
            and self.resistance_authority.permits(
                ResistanceCalculationFamily.EXISTING_METALLIC_BOLT
            )
        )


@dataclass(frozen=True, slots=True)
class BoltGroupFastenerSystemAssignment:
    """Assign one Stage 3 fastener system to one existing bolt-group identity."""

    bolt_group_id: str
    fastener_system_id: str

    def __post_init__(self) -> None:
        validate_identifier(self.bolt_group_id, "BoltGroupFastenerSystemAssignment.bolt_group_id")
        validate_identifier(
            self.fastener_system_id,
            "BoltGroupFastenerSystemAssignment.fastener_system_id",
        )


@dataclass(frozen=True, slots=True)
class ConnectionAssemblyScaffold:
    """Minimal Stage 3 assignment overlay referencing an existing JointAssembly."""

    assembly_id: str
    joint_assembly_id: str
    connected_member_id: str
    supporting_participant: ParticipantReference
    support_surface_ids: tuple[str, ...]
    connector_components: tuple[ConnectorComponentEngineeringAssignment, ...]
    physical_interface_ids: tuple[str, ...]
    bolt_group_ids: tuple[str, ...]
    fastener_systems: tuple[FastenerSystem, ...]
    fastener_assignments: tuple[BoltGroupFastenerSystemAssignment, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.assembly_id, "ConnectionAssemblyScaffold.assembly_id")
        validate_identifier(self.joint_assembly_id, "ConnectionAssemblyScaffold.joint_assembly_id")
        validate_identifier(
            self.connected_member_id, "ConnectionAssemblyScaffold.connected_member_id"
        )
        if not isinstance(self.supporting_participant, ParticipantReference):
            raise TypeError("ConnectionAssemblyScaffold.supporting_participant must be typed.")
        if self.supporting_participant.kind not in {
            ParticipantKind.MEMBER,
            ParticipantKind.SUPPORT,
        }:
            raise ValueError("A supporting participant must be a member or support.")
        if self.supporting_participant.entity_id == self.connected_member_id:
            raise ValueError("Connected and supporting participant identities must differ.")
        for value, name in (
            (self.support_surface_ids, "ConnectionAssemblyScaffold.support_surface_ids"),
            (self.physical_interface_ids, "ConnectionAssemblyScaffold.physical_interface_ids"),
            (self.bolt_group_ids, "ConnectionAssemblyScaffold.bolt_group_ids"),
        ):
            _require_identifier_tuple(value, name, allow_empty=False)
        require_tuple(
            self.connector_components,
            "ConnectionAssemblyScaffold.connector_components",
        )
        if not self.connector_components or any(
            not isinstance(item, ConnectorComponentEngineeringAssignment)
            for item in self.connector_components
        ):
            raise ValueError("ConnectionAssemblyScaffold requires connector assignments.")
        component_ids = tuple(item.component.id for item in self.connector_components)
        if len(set(component_ids)) != len(component_ids):
            raise ValueError("ConnectionAssemblyScaffold connector IDs must be unique.")
        require_tuple(self.fastener_systems, "ConnectionAssemblyScaffold.fastener_systems")
        if not self.fastener_systems or any(
            not isinstance(item, FastenerSystem) for item in self.fastener_systems
        ):
            raise ValueError("ConnectionAssemblyScaffold requires fastener systems.")
        system_ids = tuple(item.system_id for item in self.fastener_systems)
        if len(set(system_ids)) != len(system_ids):
            raise ValueError("ConnectionAssemblyScaffold fastener-system IDs must be unique.")
        require_tuple(
            self.fastener_assignments,
            "ConnectionAssemblyScaffold.fastener_assignments",
        )
        if not self.fastener_assignments or any(
            not isinstance(item, BoltGroupFastenerSystemAssignment)
            for item in self.fastener_assignments
        ):
            raise ValueError("ConnectionAssemblyScaffold requires fastener assignments.")
        assigned_groups = tuple(item.bolt_group_id for item in self.fastener_assignments)
        if len(set(assigned_groups)) != len(assigned_groups):
            raise ValueError("Each bolt group may have only one fastener-system assignment.")
        if set(assigned_groups) != set(self.bolt_group_ids):
            raise ValueError(
                "Fastener assignments must cover every declared bolt group exactly once."
            )
        if any(item.fastener_system_id not in system_ids for item in self.fastener_assignments):
            raise ValueError("A fastener assignment references an undeclared fastener system.")


@dataclass(frozen=True, slots=True)
class ConnectionPlatformVersionContext:
    """Stage 3.1 architecture versions, isolated from every numerical-engine version."""

    connection_platform_contract_version: str = CONNECTION_PLATFORM_CONTRACT_VERSION
    connector_material_schema_version: str = CONNECTOR_MATERIAL_SCHEMA_VERSION
    fastener_system_schema_version: str = FASTENER_SYSTEM_SCHEMA_VERSION
    connection_assembly_schema_version: str = CONNECTION_ASSEMBLY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        actual = (
            self.connection_platform_contract_version,
            self.connector_material_schema_version,
            self.fastener_system_schema_version,
            self.connection_assembly_schema_version,
        )
        expected = (
            CONNECTION_PLATFORM_CONTRACT_VERSION,
            CONNECTOR_MATERIAL_SCHEMA_VERSION,
            FASTENER_SYSTEM_SCHEMA_VERSION,
            CONNECTION_ASSEMBLY_SCHEMA_VERSION,
        )
        if actual != expected:
            raise ValueError("Unsupported Stage 3.1 connection-platform version context.")


def bind_connection_assembly_scaffold(
    scaffold: ConnectionAssemblyScaffold,
    joint_assembly: JointAssembly,
    *,
    available_support_surface_ids: tuple[str, ...],
) -> ConnectionAssemblyScaffold:
    """Validate Stage 3 assignment references against an accepted JointAssembly."""

    if not isinstance(scaffold, ConnectionAssemblyScaffold):
        raise TypeError("scaffold must be a ConnectionAssemblyScaffold.")
    if not isinstance(joint_assembly, JointAssembly):
        raise TypeError("joint_assembly must be a JointAssembly.")
    _require_identifier_tuple(
        available_support_surface_ids,
        "available_support_surface_ids",
        allow_empty=False,
    )
    if scaffold.joint_assembly_id != joint_assembly.id:
        raise ValueError("Connection scaffold references a different JointAssembly.")
    members = {item.id: item for item in joint_assembly.members}
    if scaffold.connected_member_id not in members:
        raise ValueError("Connection scaffold connected member is unresolved.")
    participant_collections = {
        ParticipantKind.MEMBER: {item.id for item in joint_assembly.members},
        ParticipantKind.SUPPORT: {item.id for item in joint_assembly.supports},
    }
    if (
        scaffold.supporting_participant.entity_id
        not in participant_collections[scaffold.supporting_participant.kind]
    ):
        raise ValueError("Connection scaffold supporting participant is unresolved.")
    if any(item not in available_support_surface_ids for item in scaffold.support_surface_ids):
        raise ValueError("Connection scaffold support surface is unresolved.")
    connectors = {item.id: item for item in joint_assembly.connector_components}
    for assignment in scaffold.connector_components:
        if connectors.get(assignment.component.id) != assignment.component:
            raise ValueError(
                "Connection scaffold connector assignment is unresolved or mismatched."
            )
    interface_ids = {item.id for item in joint_assembly.interfaces}
    if any(item not in interface_ids for item in scaffold.physical_interface_ids):
        raise ValueError("Connection scaffold physical interface is unresolved.")
    bolt_group_ids = {item.id for item in joint_assembly.bolt_groups}
    if any(item not in bolt_group_ids for item in scaffold.bolt_group_ids):
        raise ValueError("Connection scaffold bolt group is unresolved.")
    return scaffold


def _source_payload(source: EngineeringPropertySource | None) -> object:
    if source is None:
        return None
    return {
        "kind": source.kind.value,
        "source_id": source.source_id,
        "revision": source.revision,
        "confirmation": source.confirmation.value,
        "provenance_reference_ids": sorted(source.provenance_reference_ids),
        "qualification_required": source.qualification_required,
        "controlling_artifact_sha256": source.controlling_artifact_sha256,
        "approval_authority_id": source.approval_authority_id,
        "qualification_record_ids": sorted(source.qualification_record_ids),
    }


def _material_payload(
    material: ConnectorMaterialAssignment | FastenerMaterialAssignment,
) -> object:
    payload = {
        "assignment_id": material.assignment_id,
        "family": material.family.value,
        "behavior": material.behavior.value,
        "property_source": _source_payload(material.property_source),
        "coverage": material.coverage.value,
    }
    if isinstance(material, ConnectorMaterialAssignment):
        payload["component_id"] = material.component_id
    return payload


def _geometry_payload(geometry: EngineeringGeometryReference) -> object:
    return {
        "geometry_id": geometry.geometry_id,
        "source": _source_payload(geometry.source),
        "authoritative": geometry.authoritative,
    }


def _authority_payload(authority: ResistanceAuthority) -> object:
    return {
        "authority_id": authority.authority_id,
        "kind": authority.kind.value,
        "approved_for_use": authority.approved_for_use,
        "source": _source_payload(authority.source),
    }


def _connector_payload(value: ConnectorComponentEngineeringAssignment) -> object:
    component_orientation = value.component.material_orientation
    orientation_payload = (
        None
        if component_orientation is None
        else {
            "coordinate_frame": {
                "kind": component_orientation.coordinate_frame.kind.value,
                "owner_id": component_orientation.coordinate_frame.owner_id,
            },
            "lengthwise_axis": component_orientation.lengthwise_axis.value,
        }
    )
    topology = value.component.section_topology
    topology_payload: object = None
    if topology is not None:
        regions: list[object] = []
        for region in sorted(topology.material_regions, key=lambda item: item.id):
            orientation = region.orientation
            if isinstance(orientation, PlanarFixedMaterialOrientation):
                region_orientation: object = {
                    "kind": orientation.kind.value,
                    "crosswise_axis": orientation.crosswise_axis.value,
                    "through_thickness_axis": orientation.through_thickness_axis.value,
                    **(
                        {"crosswise_sign": orientation.crosswise_sign}
                        if orientation.crosswise_sign != 1
                        else {}
                    ),
                    **(
                        {"through_thickness_sign": orientation.through_thickness_sign}
                        if orientation.through_thickness_sign != 1
                        else {}
                    ),
                }
            elif isinstance(orientation, CylindricalMaterialOrientation):
                region_orientation = {"kind": orientation.kind.value}
            else:
                region_orientation = None
            regions.append(
                {
                    "id": region.id,
                    "role": region.role.value,
                    "orientation": region_orientation,
                }
            )
        topology_payload = {
            "source": topology.source.value,
            "standard_family": (
                None if topology.standard_family is None else topology.standard_family.value
            ),
            "elements": [
                {
                    "id": item.id,
                    "role": item.role.value,
                    "material_region_id": item.material_region_id,
                }
                for item in sorted(topology.elements, key=lambda item: item.id)
            ],
            "material_regions": regions,
        }
    return {
        "component_id": value.component.id,
        "topology": value.component.kind.value,
        "coarse_material_kind": value.component.material_kind.value,
        "component_material_orientation": orientation_payload,
        "section_topology": topology_payload,
        "material": _material_payload(value.material),
        "role": value.role.value,
        "geometry": _geometry_payload(value.geometry),
        "resistance_authority": _authority_payload(value.resistance_authority),
        "provenance": _source_payload(value.provenance),
    }


def _fastener_payload(value: FastenerSystem) -> object:
    return {
        "system_id": value.system_id,
        "material": _material_payload(value.material),
        "geometry": _geometry_payload(value.geometry),
        "resistance_authority": _authority_payload(value.resistance_authority),
        "engineering_property_snapshot_id": value.engineering_property_snapshot_id,
        "provenance": _source_payload(value.provenance),
        "washer_source": _source_payload(value.washer_source),
        "head_source": _source_payload(value.head_source),
        "nut_source": _source_payload(value.nut_source),
    }


def _assembly_payload(value: ConnectionAssemblyScaffold) -> object:
    return {
        "assembly_id": value.assembly_id,
        "joint_assembly_id": value.joint_assembly_id,
        "connected_member_id": value.connected_member_id,
        "supporting_participant": {
            "kind": value.supporting_participant.kind.value,
            "entity_id": value.supporting_participant.entity_id,
        },
        "support_surface_ids": sorted(value.support_surface_ids),
        "connector_components": [
            _connector_payload(item)
            for item in sorted(value.connector_components, key=lambda item: item.component.id)
        ],
        "physical_interface_ids": sorted(value.physical_interface_ids),
        "bolt_group_ids": sorted(value.bolt_group_ids),
        "fastener_systems": [
            _fastener_payload(item)
            for item in sorted(value.fastener_systems, key=lambda item: item.system_id)
        ],
        "fastener_assignments": [
            {
                "bolt_group_id": item.bolt_group_id,
                "fastener_system_id": item.fastener_system_id,
            }
            for item in sorted(value.fastener_assignments, key=lambda item: item.bolt_group_id)
        ],
    }


type ConnectionPlatformFingerprintValue = (
    ConnectorComponentEngineeringAssignment | FastenerSystem | ConnectionAssemblyScaffold
)


def canonical_connection_platform_json(value: ConnectionPlatformFingerprintValue) -> str:
    """Return deterministic Stage 3 identity JSON, excluding display-only labels/colors."""

    if isinstance(value, ConnectorComponentEngineeringAssignment):
        payload = _connector_payload(value)
    elif isinstance(value, FastenerSystem):
        payload = _fastener_payload(value)
    elif isinstance(value, ConnectionAssemblyScaffold):
        payload = _assembly_payload(value)
    else:
        raise TypeError("Unsupported connection-platform fingerprint value.")
    envelope = {
        "versions": {
            "connection_platform_contract_version": CONNECTION_PLATFORM_CONTRACT_VERSION,
            "connector_material_schema_version": CONNECTOR_MATERIAL_SCHEMA_VERSION,
            "fastener_system_schema_version": FASTENER_SYSTEM_SCHEMA_VERSION,
            "connection_assembly_schema_version": CONNECTION_ASSEMBLY_SCHEMA_VERSION,
        },
        "identity": payload,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def connection_platform_fingerprint(value: ConnectionPlatformFingerprintValue) -> str:
    """Return lowercase SHA-256 for a new Stage 3 architecture identity."""

    return hashlib.sha256(canonical_connection_platform_json(value).encode("utf-8")).hexdigest()


__all__ = (
    "CONNECTION_ASSEMBLY_SCHEMA_VERSION",
    "CONNECTION_PLATFORM_CONTRACT_VERSION",
    "CONNECTOR_MATERIAL_SCHEMA_VERSION",
    "FASTENER_SYSTEM_SCHEMA_VERSION",
    "BoltGroupFastenerSystemAssignment",
    "ConnectionAssemblyScaffold",
    "ConnectionPlatformFingerprintValue",
    "ConnectionPlatformVersionContext",
    "ConnectorComponentEngineeringAssignment",
    "ConnectorComponentRole",
    "ConnectorMaterialAssignment",
    "ConnectorMaterialFamily",
    "EngineeringCoverageClass",
    "EngineeringGeometryReference",
    "EngineeringPropertySource",
    "EngineeringPropertySourceKind",
    "FastenerMaterialAssignment",
    "FastenerMaterialFamily",
    "FastenerSystem",
    "MaterialBehaviorFamily",
    "PropertySourceConfirmation",
    "ResistanceAuthority",
    "ResistanceAuthorityKind",
    "ResistanceCalculationFamily",
    "bind_connection_assembly_scaffold",
    "canonical_connection_platform_json",
    "connection_platform_fingerprint",
)
