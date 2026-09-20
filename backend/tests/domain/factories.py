"""Small explicit factories shared by domain contract tests."""

from frp_master_connection.domain import (
    ActionConvention,
    AssemblyMember,
    BoltGroup,
    BoltLocation,
    ComponentMaterialKind,
    ConnectionDesignCategory,
    ConnectionInterface,
    ConnectorComponent,
    ConnectorComponentKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ForceVector3D,
    FRPComponentOrientation,
    JointAssembly,
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
    SectionTopology,
    TransferIntent,
    create_standard_section_topology,
)


def make_wide_flange_topology() -> SectionTopology:
    """Create the shared-WEB/FLANGES FRP topology used by member fixtures."""
    return create_standard_section_topology(
        SectionFamily.WIDE_FLANGE,
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


def make_member(member_id: str = "member-1") -> AssemblyMember:
    return AssemblyMember(
        id=member_id,
        label="Connected member",
        role=MemberRole.BEAM,
        connected_end=MemberEnd.END,
        section_family=SectionFamily.WIDE_FLANGE,
        material_kind=ComponentMaterialKind.PULTRUDED_FRP,
        material_orientation=FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        section_topology=make_wide_flange_topology(),
    )


def make_connector(component_id: str = "connector-1") -> ConnectorComponent:
    return ConnectorComponent(
        id=component_id,
        label="Connector plate",
        kind=ConnectorComponentKind.PLATE,
        material_kind=ComponentMaterialKind.STEEL,
        section_topology=create_standard_section_topology(SectionFamily.PLATE),
    )


def make_interface(
    interface_id: str = "interface-1",
    *,
    transfer_intent: TransferIntent = TransferIntent.SHEAR_ONLY,
) -> ConnectionInterface:
    return ConnectionInterface(
        id=interface_id,
        label="Member to connector",
        participant_a=ParticipantReference(ParticipantKind.MEMBER, "member-1"),
        participant_b=ParticipantReference(
            ParticipantKind.CONNECTOR_COMPONENT,
            "connector-1",
        ),
        transfer_intent=transfer_intent,
    )


def make_bolt_group(
    bolt_group_id: str = "bolt-group-1",
    interface_id: str = "interface-1",
) -> BoltGroup:
    return BoltGroup(
        id=bolt_group_id,
        label="Primary bolt group",
        coordinate_frame=CoordinateFrameReference(
            CoordinateFrameKind.BOLT_GROUP_LOCAL,
            bolt_group_id,
        ),
        reference_point=ReferencePoint(
            ReferencePointKind.BOLT_GROUP_ORIGIN,
            bolt_group_id,
        ),
        interface_ids=(interface_id,),
        locations=(BoltLocation("bolt-1", PositionVector3D(0.0, 0.0, 0.0)),),
    )


def make_load_combination(load_id: str = "load-1") -> LoadCombination:
    return LoadCombination(load_id, "Factored load", LoadInputBasis.FACTORED_STRENGTH)


def make_action(action_id: str = "action-1") -> ManualMemberEndAction:
    return ManualMemberEndAction(
        id=action_id,
        member_id="member-1",
        member_end=MemberEnd.END,
        load_combination_id="load-1",
        coordinate_frame=CoordinateFrameReference(CoordinateFrameKind.GLOBAL),
        reference_point=ReferencePoint(
            ReferencePointKind.MEMBER_CONNECTED_END,
            "member-1",
        ),
        force=ForceVector3D(1.0, 2.0, 3.0),
        moment=MomentVector3D(4.0, 5.0, 6.0),
        convention=ActionConvention.MEMBER_ON_JOINT,
    )


def make_assembly(
    *,
    design_category: ConnectionDesignCategory = ConnectionDesignCategory.SHEAR,
    transfer_intent: TransferIntent = TransferIntent.SHEAR_ONLY,
) -> JointAssembly:
    return JointAssembly(
        id="assembly-1",
        label="Joint assembly",
        design_category=design_category,
        unit_system=EngineeringUnitSystem.SI,
        members=(make_member(),),
        connector_components=(make_connector(),),
        supports=(),
        interfaces=(make_interface(transfer_intent=transfer_intent),),
        bolt_groups=(make_bolt_group(),),
        load_combinations=(make_load_combination(),),
        member_end_actions=(make_action(),),
    )
