"""Tests for local invariants on canonical domain entities."""

from dataclasses import FrozenInstanceError, replace

import pytest

from frp_master_connection.domain import (
    ActionConvention,
    AssemblyMember,
    AssemblySupport,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    CylindricalMaterialOrientation,
    ForceVector3D,
    FRPComponentOrientation,
    LoadCombination,
    LoadInputBasis,
    ManualMemberEndAction,
    MaterialRegionRole,
    MemberEnd,
    MemberRole,
    MomentVector3D,
    ParticipantKind,
    ParticipantReference,
    PlanarFixedMaterialOrientation,
    PositionVector3D,
    PrincipalAxisFamily,
    ReferencePoint,
    ReferencePointKind,
    SectionFamily,
    SupportKind,
    TransferIntent,
    create_standard_section_topology,
)
from tests.domain.factories import (
    make_action,
    make_bolt_group,
    make_connector,
    make_interface,
    make_load_combination,
    make_member,
)


def test_member_and_connector_material_topology_contracts_accept_valid_forms() -> None:
    member = make_member()
    steel_member = replace(
        member,
        material_kind=ComponentMaterialKind.STEEL,
        material_orientation=None,
        section_topology=create_standard_section_topology(SectionFamily.WIDE_FLANGE),
    )
    frp_connector = ConnectorComponent(
        id="connector-frp",
        label="FRP connector",
        kind=ConnectorComponentKind.TEE,
        material_kind=ComponentMaterialKind.PULTRUDED_FRP,
        material_orientation=FRPComponentOrientation(
            CoordinateFrameReference(
                CoordinateFrameKind.CONNECTOR_LOCAL,
                "connector-frp",
            ),
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

    assert member.material_orientation is not None
    assert steel_member.material_orientation is None
    assert frp_connector.material_kind is ComponentMaterialKind.PULTRUDED_FRP
    with pytest.raises(FrozenInstanceError):
        member.label = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "BEAM"},
        {"connected_end": "END"},
        {"section_family": "WIDE_FLANGE"},
        {"material_kind": "PULTRUDED_FRP"},
        {"material_orientation": None},
        {"material_orientation": "orientation"},
        {
            "material_orientation": FRPComponentOrientation(
                CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, "other-member"),
                PrincipalAxisFamily.X,
            )
        },
        {"section_topology": None},
        {"section_topology": "topology"},
        {
            "section_topology": create_standard_section_topology(
                SectionFamily.CHANNEL,
                orientations={
                    MaterialRegionRole.WEB: PlanarFixedMaterialOrientation(
                        PrincipalAxisFamily.Z,
                        PrincipalAxisFamily.Y,
                    ),
                    MaterialRegionRole.FLANGES: PlanarFixedMaterialOrientation(
                        PrincipalAxisFamily.Y,
                        PrincipalAxisFamily.Z,
                    ),
                },
            )
        },
    ],
)
def test_member_rejects_invalid_controlled_values_or_material_contract(
    changes: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(make_member(), **changes)  # type: ignore[arg-type]


def test_non_frp_member_rejects_frp_orientation() -> None:
    member = make_member()

    with pytest.raises(ValueError, match="only permitted"):
        replace(member, material_kind=ComponentMaterialKind.STEEL)


def test_connector_rejects_wrong_kind_and_material_orientation_ownership() -> None:
    connector = make_connector()
    wrong_orientation = FRPComponentOrientation(
        CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "other"),
        PrincipalAxisFamily.X,
    )

    with pytest.raises(TypeError, match="ConnectorComponentKind"):
        replace(connector, kind="PLATE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="matching local frame"):
        replace(
            connector,
            material_kind=ComponentMaterialKind.PULTRUDED_FRP,
            material_orientation=wrong_orientation,
        )


def test_non_frp_component_rejects_region_orientation_but_allows_topology() -> None:
    connector = make_connector()
    oriented_plate = create_standard_section_topology(
        SectionFamily.PLATE,
        orientations={
            MaterialRegionRole.PLATE: PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.Y,
                PrincipalAxisFamily.Z,
            )
        },
    )

    assert connector.section_topology is not None
    with pytest.raises(ValueError, match="must not contain"):
        replace(connector, section_topology=oriented_plate)


def test_round_tube_member_accepts_only_cylindrical_standard_orientation() -> None:
    member = replace(
        make_member(),
        section_family=SectionFamily.ROUND_TUBE,
        section_topology=create_standard_section_topology(
            SectionFamily.ROUND_TUBE,
            orientations={MaterialRegionRole.CYLINDRICAL_WALL: CylindricalMaterialOrientation()},
        ),
    )

    assert member.section_topology is not None
    assert isinstance(
        member.section_topology.material_regions[0].orientation,
        CylindricalMaterialOrientation,
    )


def test_frp_component_rejects_missing_region_orientation_and_lw_axis_collision() -> None:
    missing_orientation = create_standard_section_topology(SectionFamily.WIDE_FLANGE)
    colliding_orientation = create_standard_section_topology(
        SectionFamily.WIDE_FLANGE,
        orientations={
            MaterialRegionRole.WEB: PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.X,
                PrincipalAxisFamily.Y,
            ),
            MaterialRegionRole.FLANGES: PlanarFixedMaterialOrientation(
                PrincipalAxisFamily.Y,
                PrincipalAxisFamily.Z,
            ),
        },
    )

    with pytest.raises(ValueError, match="require orientation"):
        replace(make_member(), section_topology=missing_orientation)
    with pytest.raises(ValueError, match="three distinct"):
        replace(make_member(), section_topology=colliding_orientation)


def test_component_kind_requires_matching_member_or_connector_local_frame() -> None:
    connector_orientation = FRPComponentOrientation(
        CoordinateFrameReference(CoordinateFrameKind.CONNECTOR_LOCAL, "member-1"),
        PrincipalAxisFamily.X,
    )

    with pytest.raises(ValueError, match="matching local frame"):
        replace(make_member(), material_orientation=connector_orientation)


def test_standard_families_reject_wrong_orientation_rule_kind_after_construction() -> None:
    plate = create_standard_section_topology(SectionFamily.PLATE)
    cylindrical_plate = replace(
        plate,
        material_regions=(
            replace(
                plate.material_regions[0],
                orientation=CylindricalMaterialOrientation(),
            ),
        ),
    )
    round_tube = create_standard_section_topology(SectionFamily.ROUND_TUBE)
    planar_round_tube = replace(
        round_tube,
        material_regions=(
            replace(
                round_tube.material_regions[0],
                orientation=PlanarFixedMaterialOrientation(
                    PrincipalAxisFamily.Y,
                    PrincipalAxisFamily.Z,
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="PLANAR_FIXED"):
        replace(
            make_member(),
            section_family=SectionFamily.PLATE,
            section_topology=cylindrical_plate,
        )
    with pytest.raises(ValueError, match="CYLINDRICAL"):
        replace(
            make_member(),
            section_family=SectionFamily.ROUND_TUBE,
            section_topology=planar_round_tube,
        )


def test_support_participant_and_load_combination_validate_vocabularies() -> None:
    support = AssemblySupport("support-1", "Concrete support", SupportKind.CONCRETE)
    participant = ParticipantReference(ParticipantKind.SUPPORT, support.id)
    load = make_load_combination()

    assert participant.entity_id == support.id
    assert load.input_basis is LoadInputBasis.FACTORED_STRENGTH
    with pytest.raises(TypeError):
        replace(support, kind="CONCRETE")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(participant, kind="SUPPORT")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ASCII"):
        replace(participant, entity_id="bad/id")
    with pytest.raises(TypeError):
        replace(load, input_basis="FACTORED_STRENGTH")  # type: ignore[arg-type]


def test_interface_accepts_two_typed_distinct_participants() -> None:
    interface = make_interface()

    assert interface.participant_a.kind is ParticipantKind.MEMBER
    assert interface.participant_b.kind is ParticipantKind.CONNECTOR_COMPONENT


@pytest.mark.parametrize(
    "changes",
    [
        {"participant_a": "member-1"},
        {"participant_b": "connector-1"},
        {
            "participant_b": ParticipantReference(
                ParticipantKind.MEMBER,
                "member-1",
            )
        },
        {"transfer_intent": "SHEAR_ONLY"},
    ],
)
def test_interface_rejects_invalid_participants_or_transfer_intent(
    changes: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(make_interface(), **changes)  # type: ignore[arg-type]


def test_bolt_location_requires_a_position_vector() -> None:
    location = BoltLocation("bolt-1", PositionVector3D(1.0, 2.0, 3.0))

    assert location.position.x == 1.0
    with pytest.raises(TypeError):
        replace(location, position=(1.0, 2.0, 3.0))  # type: ignore[arg-type]


def test_bolt_group_accepts_origin_and_explicit_reference_points() -> None:
    bolt_group = make_bolt_group()
    explicit = replace(
        bolt_group,
        reference_point=ReferencePoint(
            ReferencePointKind.EXPLICIT_POINT,
            position=PositionVector3D(1.0, 2.0, 3.0),
        ),
    )

    assert bolt_group.reference_point.kind is ReferencePointKind.BOLT_GROUP_ORIGIN
    assert explicit.reference_point.kind is ReferencePointKind.EXPLICIT_POINT


@pytest.mark.parametrize(
    "changes",
    [
        {"coordinate_frame": "bolt-group-frame"},
        {"coordinate_frame": CoordinateFrameReference(CoordinateFrameKind.GLOBAL)},
        {"reference_point": "bolt-group-origin"},
        {
            "reference_point": ReferencePoint(
                ReferencePointKind.BOLT_GROUP_ORIGIN,
                "other-bolt-group",
            )
        },
        {
            "reference_point": ReferencePoint(
                ReferencePointKind.JOINT_ORIGIN,
                "assembly-1",
            )
        },
        {"interface_ids": ["interface-1"]},
        {"interface_ids": ()},
        {"interface_ids": ("bad/id",)},
        {"interface_ids": ("interface-1", "interface-1")},
        {"locations": [BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0))]},
        {"locations": ()},
        {"locations": ("bolt-1",)},
        {
            "locations": (
                BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0)),
                BoltLocation("bolt-1", PositionVector3D(1.0, 0.0, 0.0)),
            )
        },
    ],
)
def test_bolt_group_rejects_invalid_local_contracts(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(make_bolt_group(), **changes)  # type: ignore[arg-type]


def test_manual_member_end_action_accepts_all_six_components() -> None:
    action = make_action()

    assert action.force == ForceVector3D(1.0, 2.0, 3.0)
    assert action.moment == MomentVector3D(4.0, 5.0, 6.0)
    assert action.convention is ActionConvention.MEMBER_ON_JOINT


@pytest.mark.parametrize(
    "changes",
    [
        {"member_end": "END"},
        {"coordinate_frame": "GLOBAL"},
        {"reference_point": "MEMBER_CONNECTED_END"},
        {"force": (1.0, 2.0, 3.0)},
        {"moment": (4.0, 5.0, 6.0)},
        {"convention": "MEMBER_ON_JOINT"},
    ],
)
def test_manual_member_end_action_rejects_untyped_contract_values(
    changes: dict[str, object],
) -> None:
    with pytest.raises(TypeError):
        replace(make_action(), **changes)  # type: ignore[arg-type]


def test_entity_identifiers_and_labels_are_validated_at_construction() -> None:
    with pytest.raises(ValueError, match="ASCII"):
        AssemblyMember(
            id="bad/id",
            label="Member",
            role=MemberRole.OTHER,
            connected_end=MemberEnd.START,
            section_family=SectionFamily.CUSTOM,
            material_kind=ComponentMaterialKind.OTHER,
        )
    with pytest.raises(ValueError, match="nonempty"):
        ConnectionInterface(
            id="interface-1",
            label=" ",
            participant_a=ParticipantReference(ParticipantKind.MEMBER, "member-1"),
            participant_b=ParticipantReference(ParticipantKind.SUPPORT, "support-1"),
            transfer_intent=TransferIntent.SHEAR_ONLY,
        )
    with pytest.raises(ValueError, match="ASCII"):
        LoadCombination("bad/id", "Load", LoadInputBasis.FACTORED_STRENGTH)
    with pytest.raises(ValueError, match="ASCII"):
        ManualMemberEndAction(
            id="action-1",
            member_id="bad/id",
            member_end=MemberEnd.END,
            load_combination_id="load-1",
            coordinate_frame=CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
            reference_point=ReferencePoint(ReferencePointKind.JOINT_ORIGIN, "assembly-1"),
            force=ForceVector3D(0.0, 0.0, 0.0),
            moment=MomentVector3D(0.0, 0.0, 0.0),
            convention=ActionConvention.MEMBER_ON_JOINT,
        )
    with pytest.raises(ValueError, match="ASCII"):
        replace(make_action(), load_combination_id="bad/id")
