"""Stage 3.1 connector and fastener material-architecture tests."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import cast

import pytest

import frp_master_connection.domain.material_architecture as architecture_module
from frp_master_connection.domain import (
    CONNECTION_ASSEMBLY_SCHEMA_VERSION,
    CONNECTION_PLATFORM_CONTRACT_VERSION,
    CONNECTOR_MATERIAL_SCHEMA_VERSION,
    FASTENER_SYSTEM_SCHEMA_VERSION,
    BoltGroupFastenerSystemAssignment,
    ComponentMaterialKind,
    ConnectionAssemblyScaffold,
    ConnectionPlatformVersionContext,
    ConnectorComponent,
    ConnectorComponentEngineeringAssignment,
    ConnectorComponentKind,
    ConnectorComponentRole,
    ConnectorMaterialAssignment,
    ConnectorMaterialFamily,
    CoordinateFrameKind,
    CoordinateFrameReference,
    CylindricalMaterialOrientation,
    EngineeringCoverageClass,
    EngineeringGeometryReference,
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    FastenerMaterialAssignment,
    FastenerMaterialFamily,
    FastenerSystem,
    FRPComponentOrientation,
    JointAssembly,
    MaterialBehaviorFamily,
    MaterialRegionRole,
    ParticipantKind,
    ParticipantReference,
    PhysicalSectionElementRole,
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    PropertySourceConfirmation,
    ResistanceAuthority,
    ResistanceAuthorityKind,
    ResistanceCalculationFamily,
    SectionFamily,
    bind_connection_assembly_scaffold,
    canonical_connection_platform_json,
    connection_platform_fingerprint,
    create_standard_section_topology,
)
from tests.domain.factories import make_assembly, make_member


def _source(
    *,
    kind: EngineeringPropertySourceKind = EngineeringPropertySourceKind.CONTROLLED_PROJECT_DATA,
    source_id: str = "source-1",
    revision: str = "rev-1",
    confirmation: PropertySourceConfirmation = PropertySourceConfirmation.CONFIRMED,
    qualification_required: bool = False,
    approval_authority_id: str | None = None,
) -> EngineeringPropertySource:
    return EngineeringPropertySource(
        kind=kind,
        source_id=source_id,
        revision=revision,
        confirmation=confirmation,
        provenance_reference_ids=("artifact-1",),
        qualification_required=qualification_required,
        approval_authority_id=approval_authority_id,
    )


def _geometry(*, authoritative: bool = True) -> EngineeringGeometryReference:
    return EngineeringGeometryReference("geometry-reference", _source(), authoritative)


def _authority(
    kind: ResistanceAuthorityKind = ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY,
    *,
    approved: bool = True,
) -> ResistanceAuthority:
    if kind is ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY:
        return ResistanceAuthority("authority-none", kind, False)
    return ResistanceAuthority(
        "authority-1",
        kind,
        approved,
        _source(
            source_id="authority-source",
            confirmation=PropertySourceConfirmation.ENGINEER_APPROVED,
            approval_authority_id="engineer-1",
        ),
    )


def _connector_component(family: ConnectorMaterialFamily) -> ConnectorComponent:
    if family is ConnectorMaterialFamily.PULTRUDED_FRP:
        component_id = "connector-1"
        return ConnectorComponent(
            id=component_id,
            label="Connector label",
            kind=ConnectorComponentKind.TEE,
            material_kind=ComponentMaterialKind.PULTRUDED_FRP,
            material_orientation=FRPComponentOrientation(
                CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, component_id),
                PrincipalAxisFamily.X,
            ),
            section_topology=create_standard_section_topology(
                SectionFamily.TEE,
                orientations={
                    MaterialRegionRole.STEM: PlanarFixedMaterialOrientation(
                        PrincipalAxisFamily.Z,
                        PrincipalAxisFamily.Y,
                    ),
                    MaterialRegionRole.FLANGE: PlanarFixedMaterialOrientation(
                        PrincipalAxisFamily.Y,
                        PrincipalAxisFamily.Z,
                    ),
                },
            ),
        )
    return ConnectorComponent(
        id="connector-1",
        label="Connector label",
        kind=ConnectorComponentKind.TEE,
        material_kind=ComponentMaterialKind.STEEL,
    )


def _connector_assignment(
    family: ConnectorMaterialFamily = ConnectorMaterialFamily.STAINLESS_STEEL_316,
) -> ConnectorComponentEngineeringAssignment:
    behavior = (
        MaterialBehaviorFamily.DIRECTIONAL_FRP
        if family is ConnectorMaterialFamily.PULTRUDED_FRP
        else MaterialBehaviorFamily.ISOTROPIC_METAL
    )
    material = ConnectorMaterialAssignment(
        "connector-material-1",
        "connector-1",
        family,
        behavior,
        _source(),
        EngineeringCoverageClass.QUALIFICATION_REQUIRED,
    )
    authority = (
        _authority(ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY)
        if family is ConnectorMaterialFamily.PULTRUDED_FRP
        else _authority(ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY)
    )
    return ConnectorComponentEngineeringAssignment(
        _connector_component(family),
        material,
        ConnectorComponentRole.PRIMARY_CONNECTOR,
        _geometry(),
        authority,
        _source(source_id="connector-provenance"),
    )


def _fastener_system(
    family: FastenerMaterialFamily = FastenerMaterialFamily.STAINLESS_STEEL_316,
    *,
    snapshot_id: str | None = "snapshot-1",
    geometry_authoritative: bool = True,
    approved: bool = True,
) -> FastenerSystem:
    custom = family is FastenerMaterialFamily.CUSTOM_FRP
    material = FastenerMaterialAssignment(
        "fastener-material-1",
        family,
        (
            MaterialBehaviorFamily.CUSTOM_FASTENER_MATERIAL
            if custom
            else MaterialBehaviorFamily.ISOTROPIC_METAL
        ),
        _source(source_id="fastener-material-source"),
        (
            EngineeringCoverageClass.RESEARCH_OR_PROPRIETARY
            if custom
            else EngineeringCoverageClass.QUALIFICATION_REQUIRED
        ),
    )
    authority = (
        _authority(ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY)
        if custom
        else _authority(approved=approved)
    )
    return FastenerSystem(
        "fastener-system-1",
        material,
        _geometry(authoritative=geometry_authoritative),
        authority,
        None if custom else snapshot_id,
        _source(source_id="fastener-provenance"),
    )


def _scaffold(
    connector: ConnectorComponentEngineeringAssignment | None = None,
    fastener: FastenerSystem | None = None,
) -> ConnectionAssemblyScaffold:
    connector = connector or _connector_assignment()
    fastener = fastener or _fastener_system()
    return ConnectionAssemblyScaffold(
        assembly_id="platform-assembly-1",
        joint_assembly_id="joint-assembly-1",
        connected_member_id="member-connected",
        supporting_participant=ParticipantReference(
            ParticipantKind.MEMBER,
            "member-supporting",
        ),
        support_surface_ids=("support-surface-1",),
        connector_components=(connector,),
        physical_interface_ids=("interface-1",),
        bolt_group_ids=("bolt-group-1",),
        fastener_systems=(fastener,),
        fastener_assignments=(
            BoltGroupFastenerSystemAssignment("bolt-group-1", fastener.system_id),
        ),
    )


def test_stage_3_versions_and_controlled_vocabularies_are_exact() -> None:
    versions = ConnectionPlatformVersionContext()

    assert CONNECTION_PLATFORM_CONTRACT_VERSION == "3.1-RC1"
    assert CONNECTOR_MATERIAL_SCHEMA_VERSION == "0.1.0-draft"
    assert FASTENER_SYSTEM_SCHEMA_VERSION == "0.1.0-draft"
    assert CONNECTION_ASSEMBLY_SCHEMA_VERSION == "0.1.0-draft"
    assert versions.connection_platform_contract_version == "3.1-RC1"
    assert tuple(ConnectorMaterialFamily) == (
        ConnectorMaterialFamily.PULTRUDED_FRP,
        ConnectorMaterialFamily.STAINLESS_STEEL_316,
        ConnectorMaterialFamily.CARBON_STEEL,
    )
    assert tuple(FastenerMaterialFamily) == (
        FastenerMaterialFamily.STAINLESS_STEEL_316,
        FastenerMaterialFamily.CARBON_STEEL,
        FastenerMaterialFamily.CUSTOM_FRP,
    )
    assert len(EngineeringCoverageClass) == 4
    assert len(MaterialBehaviorFamily) == 3
    with pytest.raises(ValueError, match="Unsupported"):
        replace(versions, connection_platform_contract_version="changed")


@pytest.mark.parametrize("kind", tuple(EngineeringPropertySourceKind))
def test_every_property_source_kind_is_deeply_immutable_and_hashable(
    kind: EngineeringPropertySourceKind,
) -> None:
    source = _source(kind=kind)

    assert hash(source)
    assert source.provenance_reference_ids == ("artifact-1",)
    with pytest.raises(FrozenInstanceError):
        source.revision = "changed"  # type: ignore[misc]


def test_property_source_supports_confirmed_approved_test_and_artifact_identity() -> None:
    approved = replace(
        _source(),
        confirmation=PropertySourceConfirmation.ENGINEER_APPROVED,
        approval_authority_id="engineer-1",
        controlling_artifact_sha256="A" * 64,
        qualification_record_ids=("qualification-record-1",),
    )
    qualified = _source(
        kind=EngineeringPropertySourceKind.TEST_QUALIFIED_DATA,
        confirmation=PropertySourceConfirmation.TEST_QUALIFIED,
        qualification_required=True,
        approval_authority_id="test-authority-1",
    )
    pending = replace(_source(), confirmation=PropertySourceConfirmation.PENDING_CONFIRMATION)

    assert approved.controlling_artifact_sha256 == "A" * 64
    assert qualified.qualification_required
    assert pending.approval_authority_id is None


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"kind": "CONTROLLED_PROJECT_DATA"}, TypeError),
        ({"source_id": "bad/id"}, ValueError),
        ({"revision": "bad revision"}, ValueError),
        ({"confirmation": "CONFIRMED"}, TypeError),
        ({"provenance_reference_ids": ["artifact-1"]}, TypeError),
        ({"provenance_reference_ids": ("bad/id",)}, ValueError),
        ({"provenance_reference_ids": ("artifact-1", "artifact-1")}, ValueError),
        ({"qualification_required": 1}, TypeError),
        ({"controlling_artifact_sha256": "a" * 64}, ValueError),
        ({"approval_authority_id": "bad/id"}, ValueError),
        (
            {"confirmation": PropertySourceConfirmation.ENGINEER_APPROVED},
            ValueError,
        ),
        (
            {
                "confirmation": PropertySourceConfirmation.TEST_QUALIFIED,
                "approval_authority_id": "test-authority-1",
            },
            ValueError,
        ),
        ({"qualification_record_ids": ["qualification-record-1"]}, TypeError),
        ({"qualification_record_ids": ("bad/id",)}, ValueError),
        (
            {"qualification_record_ids": ("qualification-record-1",) * 2},
            ValueError,
        ),
    ],
)
def test_property_source_rejects_invalid_or_mutable_identity(
    changes: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        replace(_source(), **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("family", "behavior"),
    [
        (ConnectorMaterialFamily.PULTRUDED_FRP, MaterialBehaviorFamily.DIRECTIONAL_FRP),
        (ConnectorMaterialFamily.STAINLESS_STEEL_316, MaterialBehaviorFamily.ISOTROPIC_METAL),
        (ConnectorMaterialFamily.CARBON_STEEL, MaterialBehaviorFamily.ISOTROPIC_METAL),
    ],
)
def test_same_connector_topology_accepts_exact_material_assignments(
    family: ConnectorMaterialFamily,
    behavior: MaterialBehaviorFamily,
) -> None:
    connector = _connector_assignment(family)

    assert connector.component.kind is ConnectorComponentKind.TEE
    assert connector.material.family is family
    assert connector.material.behavior is behavior
    assert connector.geometry.geometry_id == "geometry-reference"
    assert connector.role is ConnectorComponentRole.PRIMARY_CONNECTOR


@pytest.mark.parametrize(
    "family",
    [
        FastenerMaterialFamily.STAINLESS_STEEL_316,
        FastenerMaterialFamily.CARBON_STEEL,
        FastenerMaterialFamily.CUSTOM_FRP,
    ],
)
def test_same_fastener_geometry_accepts_exact_material_assignments(
    family: FastenerMaterialFamily,
) -> None:
    fastener = _fastener_system(family)

    assert fastener.material.family is family
    assert fastener.geometry.geometry_id == "geometry-reference"
    if family is FastenerMaterialFamily.CUSTOM_FRP:
        assert fastener.coverage is EngineeringCoverageClass.RESEARCH_OR_PROPRIETARY
        assert not fastener.declares_existing_metallic_bolt_compatibility
    else:
        assert fastener.coverage is EngineeringCoverageClass.QUALIFICATION_REQUIRED
        assert fastener.declares_existing_metallic_bolt_compatibility


def test_material_identity_never_contains_or_infers_strength_values() -> None:
    connector_fields = {item.name for item in fields(ConnectorMaterialAssignment)}
    fastener_fields = {item.name for item in fields(FastenerMaterialAssignment)}
    system_fields = {item.name for item in fields(FastenerSystem)}
    strength_names = {
        "fnt",
        "fy",
        "fu",
        "yield_strength",
        "tensile_strength",
        "shear_strength",
        "resistance_factor",
        "grade",
    }

    assert connector_fields.isdisjoint(strength_names)
    assert fastener_fields.isdisjoint(strength_names)
    assert system_fields.isdisjoint(strength_names)
    assert _fastener_system(FastenerMaterialFamily.STAINLESS_STEEL_316).material.family.value == (
        "STAINLESS_STEEL_316"
    )
    assert _fastener_system(FastenerMaterialFamily.CARBON_STEEL).material.family.value == (
        "CARBON_STEEL"
    )


def test_material_assignments_reject_unknown_types_and_inconsistent_behavior() -> None:
    connector = _connector_assignment().material
    fastener = _fastener_system().material

    for changes in (
        {"assignment_id": "bad/id"},
        {"component_id": "bad/id"},
        {"family": "STEEL"},
        {"behavior": "ISOTROPIC_METAL"},
        {"property_source": object()},
        {"coverage": "PRESCRIPTIVE"},
        {"behavior": MaterialBehaviorFamily.DIRECTIONAL_FRP},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(connector, **changes)
    for changes in (
        {"assignment_id": "bad/id"},
        {"family": "CUSTOM_FRP"},
        {"behavior": "ISOTROPIC_METAL"},
        {"property_source": object()},
        {"coverage": "PRESCRIPTIVE"},
        {"behavior": MaterialBehaviorFamily.CUSTOM_FASTENER_MATERIAL},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(fastener, **changes)


def test_geometry_and_authority_contracts_are_explicit_and_fail_closed() -> None:
    geometry = _geometry()
    existing = _authority()
    frp = _authority(ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY)
    custom = _authority(ResistanceAuthorityKind.CUSTOM_QUALIFIED_FASTENER_AUTHORITY)
    pending = _authority(approved=False)
    none = _authority(ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY)

    assert geometry.authoritative
    assert existing.permits(ResistanceCalculationFamily.EXISTING_METALLIC_BOLT)
    assert not existing.permits(ResistanceCalculationFamily.EXISTING_FRP_CONNECTION)
    assert frp.permits(ResistanceCalculationFamily.EXISTING_FRP_CONNECTION)
    assert custom.permits(ResistanceCalculationFamily.CUSTOM_QUALIFIED_FASTENER)
    assert not pending.permits(ResistanceCalculationFamily.EXISTING_METALLIC_BOLT)
    assert not none.permits(ResistanceCalculationFamily.EXISTING_METALLIC_BOLT)
    with pytest.raises(TypeError):
        existing.permits(cast(ResistanceCalculationFamily, "EXISTING_METALLIC_BOLT"))


def test_geometry_and_authority_reject_invalid_contracts() -> None:
    geometry = _geometry()
    authority = _authority()

    for changes in (
        {"geometry_id": "bad/id"},
        {"source": object()},
        {"authoritative": 1},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(geometry, **changes)
    for authority_changes in (
        {"authority_id": "bad/id"},
        {"kind": "EXISTING_METALLIC_BOLT_AUTHORITY"},
        {"approved_for_use": 1},
        {"source": None},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(authority, **authority_changes)
    with pytest.raises(ValueError, match="cannot be approved"):
        ResistanceAuthority(
            "authority-none",
            ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            True,
        )
    with pytest.raises(ValueError, match="cannot be approved"):
        ResistanceAuthority(
            "authority-none",
            ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY,
            False,
            _source(),
        )
    with pytest.raises(ValueError, match="approved source"):
        ResistanceAuthority(
            "authority-unapproved",
            ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY,
            True,
            _source(),
        )


def test_connector_engineering_assignment_validates_existing_component_reference() -> None:
    connector = _connector_assignment()

    invalid_values = (
        {"component": object()},
        {"material": object()},
        {"material": replace(connector.material, component_id="other-component")},
        {"role": "PRIMARY_CONNECTOR"},
        {"geometry": object()},
        {"resistance_authority": object()},
        {"provenance": object()},
        {
            "component": replace(
                connector.component,
                material_kind=ComponentMaterialKind.OTHER,
            )
        },
    )
    for changes in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            replace(connector, **changes)

    metal = _connector_assignment(ConnectorMaterialFamily.CARBON_STEEL)
    with pytest.raises(ValueError, match="coarse material"):
        replace(
            metal,
            material=replace(
                metal.material,
                family=ConnectorMaterialFamily.PULTRUDED_FRP,
                behavior=MaterialBehaviorFamily.DIRECTIONAL_FRP,
            ),
        )
    with pytest.raises(ValueError, match="resistance authority"):
        replace(
            metal,
            resistance_authority=_authority(
                ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY
            ),
        )
    frp = _connector_assignment(ConnectorMaterialFamily.PULTRUDED_FRP)
    assert replace(
        frp,
        resistance_authority=_authority(ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY),
    )


def test_fastener_system_requires_typed_sources_and_explicit_metallic_prerequisites() -> None:
    fastener = _fastener_system()

    assert replace(fastener, washer_source=_source()).washer_source is not None
    assert replace(fastener, head_source=_source(), nut_source=_source()).head_source is not None
    assert not _fastener_system(snapshot_id=None).declares_existing_metallic_bolt_compatibility
    assert not _fastener_system(
        geometry_authoritative=False
    ).declares_existing_metallic_bolt_compatibility
    assert not _fastener_system(approved=False).declares_existing_metallic_bolt_compatibility
    for changes in (
        {"system_id": "bad/id"},
        {"material": object()},
        {"geometry": object()},
        {"resistance_authority": object()},
        {"engineering_property_snapshot_id": "bad/id"},
        {"provenance": object()},
        {"washer_source": object()},
        {"head_source": object()},
        {"nut_source": object()},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(fastener, **changes)
    with pytest.raises(ValueError, match="resistance authority"):
        replace(
            fastener,
            resistance_authority=_authority(
                ResistanceAuthorityKind.EXISTING_FRP_CONNECTION_AUTHORITY
            ),
        )
    custom = _fastener_system(FastenerMaterialFamily.CUSTOM_FRP)
    assert replace(
        custom,
        resistance_authority=_authority(
            ResistanceAuthorityKind.CUSTOM_QUALIFIED_FASTENER_AUTHORITY
        ),
    )
    with pytest.raises(ValueError, match="resistance authority"):
        replace(custom, resistance_authority=_authority())


def test_connection_assembly_scaffold_composes_existing_identities_without_topology() -> None:
    scaffold = _scaffold()
    support_scaffold = replace(
        scaffold,
        supporting_participant=ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
    )

    assert scaffold.connector_components[0].component.id == "connector-1"
    assert scaffold.fastener_assignments[0].bolt_group_id == "bolt-group-1"
    assert support_scaffold.supporting_participant.kind is ParticipantKind.SUPPORT
    assert hash(scaffold)


def test_connection_assembly_scaffold_binds_to_existing_joint_assembly() -> None:
    connector = _connector_assignment()
    scaffold = replace(
        _scaffold(connector),
        joint_assembly_id="assembly-1",
        connected_member_id="member-1",
        supporting_participant=ParticipantReference(ParticipantKind.MEMBER, "member-2"),
    )
    assembly = replace(
        make_assembly(),
        members=(make_member(), make_member("member-2")),
        connector_components=(connector.component,),
    )

    assert (
        bind_connection_assembly_scaffold(
            scaffold,
            assembly,
            available_support_surface_ids=("support-surface-1",),
        )
        is scaffold
    )
    with pytest.raises(TypeError, match="ConnectionAssemblyScaffold"):
        bind_connection_assembly_scaffold(
            cast(ConnectionAssemblyScaffold, object()),
            assembly,
            available_support_surface_ids=("support-surface-1",),
        )
    with pytest.raises(TypeError, match="JointAssembly"):
        bind_connection_assembly_scaffold(
            scaffold,
            cast(JointAssembly, object()),
            available_support_surface_ids=("support-surface-1",),
        )
    with pytest.raises(TypeError, match="immutable tuple"):
        bind_connection_assembly_scaffold(
            scaffold,
            assembly,
            available_support_surface_ids=cast(tuple[str, ...], ["support-surface-1"]),
        )
    with pytest.raises(ValueError, match="support surface"):
        bind_connection_assembly_scaffold(
            scaffold,
            assembly,
            available_support_surface_ids=("other-surface",),
        )
    for changes, message in (
        ({"joint_assembly_id": "other-assembly"}, "different JointAssembly"),
        ({"connected_member_id": "missing-member"}, "connected member"),
        (
            {
                "supporting_participant": ParticipantReference(
                    ParticipantKind.MEMBER,
                    "missing-member",
                )
            },
            "supporting participant",
        ),
        (
            {
                "connector_components": (
                    replace(
                        connector,
                        component=replace(connector.component, label="Mismatched component"),
                    ),
                )
            },
            "connector assignment",
        ),
        ({"physical_interface_ids": ("missing-interface",)}, "physical interface"),
        (
            {
                "bolt_group_ids": ("missing-bolt-group",),
                "fastener_assignments": (
                    BoltGroupFastenerSystemAssignment(
                        "missing-bolt-group",
                        "fastener-system-1",
                    ),
                ),
            },
            "bolt group",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            bind_connection_assembly_scaffold(
                replace(scaffold, **changes),
                assembly,
                available_support_surface_ids=("support-surface-1",),
            )


@pytest.mark.parametrize(
    "changes",
    [
        {"assembly_id": "bad/id"},
        {"joint_assembly_id": "bad/id"},
        {"connected_member_id": "bad/id"},
        {"supporting_participant": object()},
        {
            "supporting_participant": ParticipantReference(
                ParticipantKind.CONNECTOR_COMPONENT,
                "connector-1",
            )
        },
        {
            "supporting_participant": ParticipantReference(
                ParticipantKind.MEMBER,
                "member-connected",
            )
        },
        {"support_surface_ids": []},
        {"support_surface_ids": ()},
        {"support_surface_ids": ("bad/id",)},
        {"support_surface_ids": ("surface-1", "surface-1")},
        {"physical_interface_ids": ()},
        {"bolt_group_ids": ()},
        {"connector_components": []},
        {"connector_components": ()},
        {"connector_components": (object(),)},
        {
            "connector_components": (
                _connector_assignment(),
                _connector_assignment(),
            )
        },
        {"fastener_systems": []},
        {"fastener_systems": ()},
        {"fastener_systems": (object(),)},
        {"fastener_systems": (_fastener_system(), _fastener_system())},
        {"fastener_assignments": []},
        {"fastener_assignments": ()},
        {"fastener_assignments": (object(),)},
        {
            "bolt_group_ids": ("bolt-group-1", "bolt-group-2"),
            "fastener_assignments": (
                BoltGroupFastenerSystemAssignment("bolt-group-1", "fastener-system-1"),
                BoltGroupFastenerSystemAssignment("bolt-group-1", "fastener-system-1"),
            ),
        },
        {
            "fastener_assignments": (
                BoltGroupFastenerSystemAssignment("other-group", "fastener-system-1"),
            )
        },
        {
            "fastener_assignments": (
                BoltGroupFastenerSystemAssignment("bolt-group-1", "other-system"),
            )
        },
    ],
)
def test_connection_assembly_scaffold_rejects_invalid_or_mutable_collections(
    changes: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(_scaffold(), **changes)  # type: ignore[arg-type]


def test_bolt_group_fastener_assignment_rejects_invalid_ids() -> None:
    assignment = BoltGroupFastenerSystemAssignment("bolt-group-1", "fastener-system-1")

    with pytest.raises(ValueError, match="ASCII"):
        replace(assignment, bolt_group_id="bad/id")
    with pytest.raises(ValueError, match="ASCII"):
        replace(assignment, fastener_system_id="bad/id")


def test_stage_3_fingerprint_is_deterministic_and_excludes_display_label() -> None:
    connector = _connector_assignment(ConnectorMaterialFamily.PULTRUDED_FRP)
    fastener = replace(
        _fastener_system(),
        washer_source=_source(source_id="washer-source"),
        head_source=_source(source_id="head-source"),
        nut_source=_source(source_id="nut-source"),
    )
    scaffold = _scaffold(connector, fastener)

    connector_json = canonical_connection_platform_json(connector)
    fastener_json = canonical_connection_platform_json(fastener)
    assembly_json = canonical_connection_platform_json(scaffold)
    assert '"connection_platform_contract_version":"3.1-RC1"' in connector_json
    assert "Connector label" not in connector_json
    assert "washer-source" in fastener_json
    assert "platform-assembly-1" in assembly_json
    assert connection_platform_fingerprint(connector) == connection_platform_fingerprint(
        replace(
            connector,
            component=replace(connector.component, label="Presentation-only label"),
        )
    )
    changed_source = replace(
        connector,
        material=replace(
            connector.material,
            property_source=replace(connector.material.property_source, revision="rev-2"),
        ),
    )
    assert connection_platform_fingerprint(connector) != connection_platform_fingerprint(
        changed_source
    )
    assert connector.component.section_topology is not None
    changed_topology = replace(
        connector,
        component=replace(
            connector.component,
            section_topology=replace(
                connector.component.section_topology,
                elements=(
                    replace(
                        connector.component.section_topology.elements[0],
                        role=PhysicalSectionElementRole.CUSTOM,
                    ),
                    *connector.component.section_topology.elements[1:],
                ),
            ),
        ),
    )
    assert connection_platform_fingerprint(connector) != connection_platform_fingerprint(
        changed_topology
    )
    round_tube = replace(
        connector,
        component=replace(
            connector.component,
            kind=ConnectorComponentKind.OTHER,
            section_topology=create_standard_section_topology(
                SectionFamily.ROUND_TUBE,
                orientations={
                    MaterialRegionRole.CYLINDRICAL_WALL: CylindricalMaterialOrientation()
                },
            ),
        ),
    )
    assert "CYLINDRICAL" in canonical_connection_platform_json(round_tube)
    unoriented_metal = _connector_assignment()
    unoriented_metal = replace(
        unoriented_metal,
        component=replace(
            unoriented_metal.component,
            section_topology=create_standard_section_topology(SectionFamily.TEE),
        ),
    )
    assert '"orientation":null' in canonical_connection_platform_json(unoriented_metal)
    with pytest.raises(TypeError, match="Unsupported"):
        canonical_connection_platform_json(cast(ConnectorComponentEngineeringAssignment, object()))


def test_stage_3_fingerprint_sorts_semantically_unordered_identity_collections() -> None:
    fastener = _fastener_system()
    first_source = replace(
        fastener.provenance,
        provenance_reference_ids=("artifact-b", "artifact-a"),
        qualification_record_ids=("qualification-b", "qualification-a"),
    )
    second_source = replace(
        first_source,
        provenance_reference_ids=tuple(reversed(first_source.provenance_reference_ids)),
        qualification_record_ids=tuple(reversed(first_source.qualification_record_ids)),
    )
    first = replace(fastener, provenance=first_source)
    second = replace(fastener, provenance=second_source)

    assert connection_platform_fingerprint(first) == connection_platform_fingerprint(second)

    scaffold = _scaffold(fastener=first)
    first_assembly = replace(
        scaffold,
        support_surface_ids=("surface-b", "surface-a"),
        physical_interface_ids=("interface-b", "interface-a"),
        bolt_group_ids=("bolt-group-b", "bolt-group-a"),
        fastener_assignments=(
            BoltGroupFastenerSystemAssignment("bolt-group-b", first.system_id),
            BoltGroupFastenerSystemAssignment("bolt-group-a", first.system_id),
        ),
    )
    second_assembly = replace(
        first_assembly,
        support_surface_ids=tuple(reversed(first_assembly.support_surface_ids)),
        physical_interface_ids=tuple(reversed(first_assembly.physical_interface_ids)),
        bolt_group_ids=tuple(reversed(first_assembly.bolt_group_ids)),
        fastener_assignments=tuple(reversed(first_assembly.fastener_assignments)),
    )
    assert connection_platform_fingerprint(first_assembly) == connection_platform_fingerprint(
        second_assembly
    )


def test_stage_3_domain_contract_has_no_framework_golden_or_equation_dependency() -> None:
    assert architecture_module.__file__ is not None
    source_path = Path(architecture_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert all(
        not name.startswith(
            (
                "fastapi",
                "pydantic",
                "sqlalchemy",
                "frp_master_connection.api",
                "frp_master_connection.application",
                "frp_master_connection.calculation",
            )
        )
        for name in imported_modules
    )
    assert all("golden" not in name.lower() for name in imported_modules)
    assert all(not name.startswith("calculate_") for name in function_names)
