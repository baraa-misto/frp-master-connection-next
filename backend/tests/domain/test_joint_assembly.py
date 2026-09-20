"""Positive and negative tests for deterministic JointAssembly validation."""

from dataclasses import FrozenInstanceError, replace

import pytest

from frp_master_connection.domain import (
    AssemblySupport,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    DomainValidationError,
    EngineeringUnitSystem,
    FRPComponentOrientation,
    JointAssembly,
    MaterialRegion,
    MaterialRegionRole,
    MemberEnd,
    ParticipantKind,
    ParticipantReference,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SectionTopologySource,
    SupportKind,
    TransferIntent,
    ValidationCode,
    create_standard_section_topology,
)
from tests.domain.factories import (
    make_action,
    make_assembly,
    make_bolt_group,
    make_connector,
    make_interface,
    make_load_combination,
    make_member,
)


def _codes(assembly: JointAssembly) -> tuple[ValidationCode, ...]:
    return tuple(issue.code for issue in assembly.validate())


def test_valid_shear_and_moment_assemblies_have_no_issues() -> None:
    shear = make_assembly()
    steel_member_assembly = replace(
        shear,
        members=(
            replace(
                make_member(),
                material_kind=ComponentMaterialKind.STEEL,
                material_orientation=None,
                section_topology=create_standard_section_topology(SectionFamily.WIDE_FLANGE),
            ),
        ),
    )
    topology_free_non_frp = replace(
        shear,
        members=(
            replace(
                make_member(),
                material_kind=ComponentMaterialKind.STEEL,
                material_orientation=None,
                section_topology=None,
            ),
        ),
        connector_components=(replace(make_connector(), section_topology=None),),
    )
    moment = make_assembly(
        design_category=ConnectionDesignCategory.MOMENT,
        transfer_intent=TransferIntent.MOMENT_RESISTING,
    )

    assert shear.validate() == ()
    assert steel_member_assembly.validate() == ()
    assert topology_free_non_frp.validate() == ()
    assert moment.validate() == ()
    shear.require_valid()
    assert shear.unit_system is EngineeringUnitSystem.SI
    with pytest.raises(FrozenInstanceError):
        shear.members = ()  # type: ignore[misc]


def test_shared_t_connector_topology_with_two_members_is_valid() -> None:
    member_2 = make_member("member-2")
    shared_tee = replace(
        make_connector(),
        kind=ConnectorComponentKind.TEE,
        section_topology=create_standard_section_topology(SectionFamily.TEE),
    )
    interface_2 = ConnectionInterface(
        id="interface-2",
        label="Second member to shared connector",
        participant_a=ParticipantReference(ParticipantKind.MEMBER, "member-2"),
        participant_b=ParticipantReference(
            ParticipantKind.CONNECTOR_COMPONENT,
            "connector-1",
        ),
        transfer_intent=TransferIntent.SHEAR_ONLY,
    )
    assembly = replace(
        make_assembly(),
        members=(make_member(), member_2),
        connector_components=(shared_tee,),
        interfaces=(make_interface(), interface_2),
        bolt_groups=(),
        member_end_actions=(),
        load_combinations=(),
    )

    assert assembly.validate() == ()


def test_direct_member_to_support_interface_is_valid() -> None:
    support = AssemblySupport("support-1", "Foundation", SupportKind.FOUNDATION)
    interface = ConnectionInterface(
        "interface-support",
        "Member to foundation",
        ParticipantReference(ParticipantKind.MEMBER, "member-1"),
        ParticipantReference(ParticipantKind.SUPPORT, support.id),
        TransferIntent.SHEAR_ONLY,
    )
    assembly = replace(
        make_assembly(),
        connector_components=(),
        supports=(support,),
        interfaces=(interface,),
        bolt_groups=(),
        load_combinations=(),
        member_end_actions=(),
    )

    assert assembly.validate() == ()


def test_direct_member_to_member_and_connector_assisted_interfaces_can_coexist() -> None:
    member_2 = make_member("member-2")
    direct = ConnectionInterface(
        "interface-direct",
        "Direct member interface",
        ParticipantReference(ParticipantKind.MEMBER, "member-1"),
        ParticipantReference(ParticipantKind.MEMBER, "member-2"),
        TransferIntent.SHEAR_ONLY,
    )
    assisted = make_interface("interface-assisted")
    assembly = replace(
        make_assembly(),
        members=(make_member(), member_2),
        interfaces=(direct, assisted),
        bolt_groups=(),
        load_combinations=(),
        member_end_actions=(),
        unit_system=EngineeringUnitSystem.US_CUSTOMARY,
    )

    assert assembly.validate() == ()


def test_minimum_structure_reports_all_failures_and_require_valid_raises() -> None:
    assembly = replace(
        make_assembly(),
        members=(),
        connector_components=(),
        interfaces=(),
        bolt_groups=(),
        load_combinations=(),
        member_end_actions=(),
    )

    assert _codes(assembly) == (
        ValidationCode.INSUFFICIENT_RESOLVED_PARTICIPANTS,
        ValidationCode.INTERFACE_REQUIRED,
        ValidationCode.MEMBER_REQUIRED,
    )
    with pytest.raises(DomainValidationError) as captured:
        assembly.require_valid()
    assert captured.value.issues == assembly.validate()


def test_duplicate_ids_are_scoped_and_global_collisions_are_reported() -> None:
    duplicate_member = make_member()
    colliding_connector = replace(make_connector(), id="assembly-1")
    assembly = replace(
        make_assembly(),
        members=(make_member(), duplicate_member),
        connector_components=(make_connector(), colliding_connector),
    )

    assert ValidationCode.DUPLICATE_ID in _codes(assembly)
    assert ValidationCode.DUPLICATE_GLOBAL_ID in _codes(assembly)
    duplicate_issue = next(
        issue for issue in assembly.validate() if issue.code is ValidationCode.DUPLICATE_ID
    )
    assert duplicate_issue.path == "members[1].id"


def test_component_scoped_topology_issues_join_deterministic_aggregate_validation() -> None:
    member = make_member()
    assert member.section_topology is not None
    topology = member.section_topology
    malformed = replace(
        topology,
        source=SectionTopologySource.CUSTOM,
        standard_family=None,
        elements=(
            topology.elements[0],
            replace(
                topology.elements[1],
                id=topology.elements[0].id,
                material_region_id="missing-region",
            ),
            topology.elements[2],
        ),
        material_regions=(
            *topology.material_regions,
            MaterialRegion(
                "orphan-region",
                "Orphan region",
                MaterialRegionRole.CUSTOM,
                PlanarFixedMaterialOrientation(
                    PrincipalAxisFamily.Y,
                    PrincipalAxisFamily.Z,
                ),
            ),
        ),
    )
    assembly = replace(make_assembly(), members=(replace(member, section_topology=malformed),))

    issues = assembly.validate()

    assert tuple(issue.code for issue in issues) == (
        ValidationCode.DUPLICATE_SECTION_ELEMENT_ID,
        ValidationCode.UNRESOLVED_MATERIAL_REGION,
        ValidationCode.ORPHAN_MATERIAL_REGION,
    )
    assert issues[0].path.startswith("members[0].section_topology")


def test_cross_collection_id_collision_is_reported_once_per_later_owner() -> None:
    colliding_connector = replace(make_connector(), id="member-1")
    assembly = replace(make_assembly(), connector_components=(colliding_connector,))

    issues = [
        issue for issue in assembly.validate() if issue.code is ValidationCode.DUPLICATE_GLOBAL_ID
    ]

    assert len(issues) == 1
    assert issues[0].related_entity_id == "member-1"


def test_unresolved_participants_and_insufficient_resolved_count_are_reported() -> None:
    interface = replace(
        make_interface(),
        participant_a=ParticipantReference(ParticipantKind.MEMBER, "missing-member"),
        participant_b=ParticipantReference(ParticipantKind.SUPPORT, "missing-support"),
    )
    assembly = replace(make_assembly(), interfaces=(interface,), bolt_groups=())

    codes = _codes(assembly)

    assert codes.count(ValidationCode.UNRESOLVED_PARTICIPANT) == 2
    assert ValidationCode.INSUFFICIENT_RESOLVED_PARTICIPANTS in codes


def test_design_category_and_transfer_intent_must_agree() -> None:
    missing_moment_path = make_assembly(design_category=ConnectionDesignCategory.MOMENT)
    moment_in_shear_path = make_assembly(transfer_intent=TransferIntent.MOMENT_RESISTING)

    assert _codes(missing_moment_path) == (
        ValidationCode.MOMENT_CATEGORY_REQUIRES_MOMENT_INTERFACE,
    )
    assert _codes(moment_in_shear_path) == (ValidationCode.SHEAR_CATEGORY_MOMENT_INTERFACE,)


def test_bolt_group_interface_reference_must_resolve() -> None:
    assembly = replace(
        make_assembly(),
        bolt_groups=(make_bolt_group(interface_id="missing-interface"),),
    )

    assert _codes(assembly) == (ValidationCode.UNRESOLVED_BOLT_GROUP_INTERFACE,)


def test_all_owned_frame_and_reference_point_kinds_can_resolve() -> None:
    frp_connector = ConnectorComponent(
        "connector-1",
        "FRP connector",
        ConnectorComponentKind.PLATE,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "connector-1"),
            PrincipalAxisFamily.X,
        ),
        create_standard_section_topology(
            SectionFamily.PLATE,
            orientations={
                MaterialRegionRole.PLATE: PlanarFixedMaterialOrientation(
                    PrincipalAxisFamily.Y,
                    PrincipalAxisFamily.Z,
                )
            },
        ),
    )
    frame_and_point_pairs = (
        (
            CoordinateFrameReference(CoordinateFrameKind.JOINT_LOCAL, "assembly-1"),
            ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "assembly-1"),
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "member-1"),
            ReferencePoint(ReferencePointKind.MEMBER_CONNECTED_END, "member-1"),
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "connector-1"),
            ReferencePoint(ReferencePointKind.INTERFACE_ORIGIN, "interface-1"),
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.INTERFACE_LOCAL, "interface-1"),
            ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, "bolt-group-1"),
        ),
        (
            CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, "bolt-group-1"),
            ReferencePoint(
                ReferencePointKind.EXPLICIT_POINT,
                position=PositionVector3D(0.0, 0.0, 0.0),
            ),
        ),
    )
    actions = tuple(
        replace(
            make_action(f"action-{index}"),
            coordinate_frame=frame,
            reference_point=point,
            load_combination_id=f"load-{index}",
        )
        for index, (frame, point) in enumerate(frame_and_point_pairs, start=1)
    )
    loads = tuple(make_load_combination(f"load-{index}") for index in range(1, 6))
    assembly = replace(
        make_assembly(),
        connector_components=(frp_connector,),
        load_combinations=loads,
        member_end_actions=actions,
    )

    assert assembly.validate() == ()


def test_unresolved_frame_and_reference_point_owners_are_reported() -> None:
    action = replace(
        make_action(),
        coordinate_frame=CoordinateFrameReference(
            CoordinateFrameKind.INTERFACE_LOCAL,
            "missing-interface",
        ),
        reference_point=ReferencePoint(
            ReferencePointKind.INTERFACE_ORIGIN,
            "missing-interface",
        ),
    )
    assembly = replace(make_assembly(), member_end_actions=(action,))

    assert _codes(assembly) == (
        ValidationCode.UNRESOLVED_FRAME_OWNER,
        ValidationCode.UNRESOLVED_REFERENCE_POINT_OWNER,
    )


def test_action_member_load_end_and_pair_invariants_report_together() -> None:
    first = replace(
        make_action("action-1"),
        member_end=MemberEnd.START,
        load_combination_id="missing-load",
    )
    second = replace(first, id="action-2")
    missing_member = replace(make_action("action-3"), member_id="missing-member")
    assembly = replace(
        make_assembly(),
        member_end_actions=(first, second, missing_member),
    )

    codes = _codes(assembly)

    assert codes.count(ValidationCode.ACTION_MEMBER_END_MISMATCH) == 2
    assert ValidationCode.DUPLICATE_MEMBER_LOAD_COMBINATION_ACTION in codes
    assert codes.count(ValidationCode.UNRESOLVED_LOAD_COMBINATION) == 2
    assert ValidationCode.UNRESOLVED_ACTION_MEMBER in codes


@pytest.mark.parametrize(
    "changes",
    [
        {"design_category": "SHEAR"},
        {"unit_system": "SI"},
        {"members": [make_member()]},
        {"members": ("member-1",)},
    ],
)
def test_aggregate_constructor_rejects_mutable_or_untyped_contract_values(
    changes: dict[str, object],
) -> None:
    with pytest.raises(TypeError):
        replace(make_assembly(), **changes)  # type: ignore[arg-type]


def test_aggregate_identifier_and_label_are_validated() -> None:
    with pytest.raises(ValueError, match="ASCII"):
        replace(make_assembly(), id="bad/id")
    with pytest.raises(ValueError, match="nonempty"):
        replace(make_assembly(), label=" ")
