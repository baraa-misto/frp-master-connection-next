"""JointAssembly aggregate and deterministic cross-entity contract validation."""

from dataclasses import dataclass
from typing import cast

from frp_master_connection.domain.entities import (
    AssemblyMember,
    AssemblySupport,
    BoltGroup,
    ConnectionInterface,
    ConnectorComponent,
    LoadCombination,
    ManualMemberEndAction,
)
from frp_master_connection.domain.validation import (
    DomainValidationError,
    ValidationCode,
    ValidationIssue,
    order_issues,
    require_enum,
    validate_identifier,
    validate_label,
)
from frp_master_connection.domain.values import (
    ConnectionDesignCategory,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    ParticipantKind,
    ReferencePoint,
    ReferencePointKind,
    TransferIntent,
)


def _require_tuple_items(value: object, item_type: type[object], field_name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be an immutable tuple.")
    for item in value:
        if not isinstance(item, item_type):
            raise TypeError(f"{field_name} items must be {item_type.__name__} values.")


@dataclass(frozen=True, slots=True)
class JointAssembly:
    """Immutable root aggregate for a connection assembly's canonical inputs."""

    id: str
    label: str
    design_category: ConnectionDesignCategory
    unit_system: EngineeringUnitSystem
    members: tuple[AssemblyMember, ...]
    connector_components: tuple[ConnectorComponent, ...]
    supports: tuple[AssemblySupport, ...]
    interfaces: tuple[ConnectionInterface, ...]
    bolt_groups: tuple[BoltGroup, ...]
    load_combinations: tuple[LoadCombination, ...]
    member_end_actions: tuple[ManualMemberEndAction, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.id, "JointAssembly.id")
        validate_label(self.label, "JointAssembly.label")
        require_enum(
            self.design_category,
            ConnectionDesignCategory,
            "JointAssembly.design_category",
        )
        require_enum(self.unit_system, EngineeringUnitSystem, "JointAssembly.unit_system")
        _require_tuple_items(self.members, AssemblyMember, "JointAssembly.members")
        _require_tuple_items(
            self.connector_components,
            ConnectorComponent,
            "JointAssembly.connector_components",
        )
        _require_tuple_items(self.supports, AssemblySupport, "JointAssembly.supports")
        _require_tuple_items(
            self.interfaces,
            ConnectionInterface,
            "JointAssembly.interfaces",
        )
        _require_tuple_items(self.bolt_groups, BoltGroup, "JointAssembly.bolt_groups")
        _require_tuple_items(
            self.load_combinations,
            LoadCombination,
            "JointAssembly.load_combinations",
        )
        _require_tuple_items(
            self.member_end_actions,
            ManualMemberEndAction,
            "JointAssembly.member_end_actions",
        )

    def validate(self) -> tuple[ValidationIssue, ...]:
        """Return every aggregate issue in deterministic order without mutation."""
        issues: list[ValidationIssue] = []

        if not self.members:
            issues.append(
                ValidationIssue(
                    ValidationCode.MEMBER_REQUIRED,
                    "A joint assembly requires at least one member.",
                    "members",
                )
            )
        if not self.interfaces:
            issues.append(
                ValidationIssue(
                    ValidationCode.INTERFACE_REQUIRED,
                    "A joint assembly requires at least one connection interface.",
                    "interfaces",
                )
            )

        collections: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("members", tuple(member.id for member in self.members)),
            (
                "connector_components",
                tuple(component.id for component in self.connector_components),
            ),
            ("supports", tuple(support.id for support in self.supports)),
            ("interfaces", tuple(interface.id for interface in self.interfaces)),
            ("bolt_groups", tuple(bolt_group.id for bolt_group in self.bolt_groups)),
            (
                "load_combinations",
                tuple(load_combination.id for load_combination in self.load_combinations),
            ),
            (
                "member_end_actions",
                tuple(action.id for action in self.member_end_actions),
            ),
        )
        for collection_name, collection in collections:
            seen_within: set[str] = set()
            for index, entity_id in enumerate(collection):
                if entity_id in seen_within:
                    issues.append(
                        ValidationIssue(
                            ValidationCode.DUPLICATE_ID,
                            f"Duplicate id {entity_id!r} in {collection_name}.",
                            f"{collection_name}[{index}].id",
                            entity_id,
                        )
                    )
                seen_within.add(entity_id)

        global_id_owners: dict[str, str] = {self.id: "assembly"}
        for collection_name, collection in collections:
            for index, entity_id in enumerate(collection):
                prior_owner = global_id_owners.get(entity_id)
                if prior_owner is None:
                    global_id_owners[entity_id] = collection_name
                elif prior_owner != collection_name:
                    issues.append(
                        ValidationIssue(
                            ValidationCode.DUPLICATE_GLOBAL_ID,
                            f"Top-level id {entity_id!r} is also used by {prior_owner}.",
                            f"{collection_name}[{index}].id",
                            entity_id,
                        )
                    )

        for member_index, member in enumerate(self.members):
            if member.section_topology is not None:
                issues.extend(
                    member.section_topology.validate(f"members[{member_index}].section_topology")
                )
        for component_index, component in enumerate(self.connector_components):
            if component.section_topology is not None:
                issues.extend(
                    component.section_topology.validate(
                        f"connector_components[{component_index}].section_topology"
                    )
                )

        member_ids = {member.id for member in self.members}
        connector_ids = {component.id for component in self.connector_components}
        support_ids = {support.id for support in self.supports}
        interface_ids = {interface.id for interface in self.interfaces}
        bolt_group_ids = {bolt_group.id for bolt_group in self.bolt_groups}
        load_combination_ids = {load_combination.id for load_combination in self.load_combinations}

        participant_ids = {
            ParticipantKind.MEMBER: member_ids,
            ParticipantKind.CONNECTOR_COMPONENT: connector_ids,
            ParticipantKind.SUPPORT: support_ids,
        }
        resolved_participants: set[tuple[ParticipantKind, str]] = set()
        for interface_index, interface in enumerate(self.interfaces):
            for participant_name, participant in (
                ("participant_a", interface.participant_a),
                ("participant_b", interface.participant_b),
            ):
                if participant.entity_id in participant_ids[participant.kind]:
                    resolved_participants.add((participant.kind, participant.entity_id))
                else:
                    issues.append(
                        ValidationIssue(
                            ValidationCode.UNRESOLVED_PARTICIPANT,
                            (
                                f"{participant.kind.value} participant "
                                f"{participant.entity_id!r} is not declared."
                            ),
                            f"interfaces[{interface_index}].{participant_name}",
                            participant.entity_id,
                        )
                    )
        if len(resolved_participants) < 2:
            issues.append(
                ValidationIssue(
                    ValidationCode.INSUFFICIENT_RESOLVED_PARTICIPANTS,
                    "A joint assembly requires at least two distinct resolved participants.",
                    "interfaces",
                )
            )

        if self.design_category is ConnectionDesignCategory.MOMENT:
            if not any(
                interface.transfer_intent is TransferIntent.MOMENT_RESISTING
                for interface in self.interfaces
            ):
                issues.append(
                    ValidationIssue(
                        ValidationCode.MOMENT_CATEGORY_REQUIRES_MOMENT_INTERFACE,
                        "A moment design requires a moment-resisting interface.",
                        "design_category",
                    )
                )
        else:
            for interface_index, interface in enumerate(self.interfaces):
                if interface.transfer_intent is TransferIntent.MOMENT_RESISTING:
                    issues.append(
                        ValidationIssue(
                            ValidationCode.SHEAR_CATEGORY_MOMENT_INTERFACE,
                            "A shear design cannot declare a moment-resisting interface.",
                            f"interfaces[{interface_index}].transfer_intent",
                            interface.id,
                        )
                    )

        for bolt_group_index, bolt_group in enumerate(self.bolt_groups):
            for interface_index, interface_id in enumerate(bolt_group.interface_ids):
                if interface_id not in interface_ids:
                    issues.append(
                        ValidationIssue(
                            ValidationCode.UNRESOLVED_BOLT_GROUP_INTERFACE,
                            f"Bolt-group interface {interface_id!r} is not declared.",
                            (f"bolt_groups[{bolt_group_index}].interface_ids[{interface_index}]"),
                            interface_id,
                        )
                    )

        frames: list[tuple[str, CoordinateFrameReference]] = []
        reference_points: list[tuple[str, ReferencePoint]] = []
        for member_index, member in enumerate(self.members):
            if member.material_orientation is not None:
                frames.append(
                    (
                        f"members[{member_index}].material_orientation.coordinate_frame",
                        member.material_orientation.coordinate_frame,
                    )
                )
        for component_index, component in enumerate(self.connector_components):
            if component.material_orientation is not None:
                frames.append(
                    (
                        (
                            f"connector_components[{component_index}]"
                            ".material_orientation.coordinate_frame"
                        ),
                        component.material_orientation.coordinate_frame,
                    )
                )
        for bolt_group_index, bolt_group in enumerate(self.bolt_groups):
            frames.append(
                (f"bolt_groups[{bolt_group_index}].coordinate_frame", bolt_group.coordinate_frame)
            )
            reference_points.append(
                (f"bolt_groups[{bolt_group_index}].reference_point", bolt_group.reference_point)
            )
        for action_index, action in enumerate(self.member_end_actions):
            frames.append(
                (f"member_end_actions[{action_index}].coordinate_frame", action.coordinate_frame)
            )
            reference_points.append(
                (f"member_end_actions[{action_index}].reference_point", action.reference_point)
            )

        frame_owner_ids = {
            CoordinateFrameKind.JOINT_LOCAL: {self.id},
            CoordinateFrameKind.MEMBER_LOCAL: member_ids,
            CoordinateFrameKind.CONNECTOR_LOCAL: connector_ids,
            CoordinateFrameKind.INTERFACE_LOCAL: interface_ids,
            CoordinateFrameKind.BOLT_GROUP_LOCAL: bolt_group_ids,
        }
        for path, frame in frames:
            if frame.kind is CoordinateFrameKind.GLOBAL:
                continue
            owner_id = cast(str, frame.owner_id)
            if owner_id not in frame_owner_ids[frame.kind]:
                issues.append(
                    ValidationIssue(
                        ValidationCode.UNRESOLVED_FRAME_OWNER,
                        f"Frame owner {owner_id!r} is not declared for {frame.kind.value}.",
                        path,
                        owner_id,
                    )
                )

        reference_owner_ids = {
            ReferencePointKind.JOINT_ORIGIN: {self.id},
            ReferencePointKind.MEMBER_CONNECTED_END: member_ids,
            ReferencePointKind.INTERFACE_ORIGIN: interface_ids,
            ReferencePointKind.BOLT_GROUP_ORIGIN: bolt_group_ids,
        }
        for path, reference_point in reference_points:
            if reference_point.kind is ReferencePointKind.EXPLICIT_POINT:
                continue
            owner_id = cast(str, reference_point.owner_id)
            if owner_id not in reference_owner_ids[reference_point.kind]:
                issues.append(
                    ValidationIssue(
                        ValidationCode.UNRESOLVED_REFERENCE_POINT_OWNER,
                        (
                            f"Reference-point owner {owner_id!r} is not "
                            f"declared for {reference_point.kind.value}."
                        ),
                        path,
                        owner_id,
                    )
                )

        members_by_id = {member.id: member for member in self.members}
        seen_action_pairs: set[tuple[str, str]] = set()
        for action_index, action in enumerate(self.member_end_actions):
            resolved_member = members_by_id.get(action.member_id)
            if resolved_member is None:
                issues.append(
                    ValidationIssue(
                        ValidationCode.UNRESOLVED_ACTION_MEMBER,
                        f"Action member {action.member_id!r} is not declared.",
                        f"member_end_actions[{action_index}].member_id",
                        action.member_id,
                    )
                )
            elif action.member_end is not resolved_member.connected_end:
                issues.append(
                    ValidationIssue(
                        ValidationCode.ACTION_MEMBER_END_MISMATCH,
                        "Action member_end does not match the member's declared connected_end.",
                        f"member_end_actions[{action_index}].member_end",
                        action.member_id,
                    )
                )
            if action.load_combination_id not in load_combination_ids:
                issues.append(
                    ValidationIssue(
                        ValidationCode.UNRESOLVED_LOAD_COMBINATION,
                        f"Load combination {action.load_combination_id!r} is not declared.",
                        f"member_end_actions[{action_index}].load_combination_id",
                        action.load_combination_id,
                    )
                )
            action_pair = (action.member_id, action.load_combination_id)
            if action_pair in seen_action_pairs:
                issues.append(
                    ValidationIssue(
                        ValidationCode.DUPLICATE_MEMBER_LOAD_COMBINATION_ACTION,
                        "Only one action is permitted per member and load combination.",
                        f"member_end_actions[{action_index}]",
                        action.id,
                    )
                )
            seen_action_pairs.add(action_pair)

        return order_issues(issues)

    def require_valid(self) -> None:
        """Raise one domain exception containing all deterministic issues when invalid."""
        issues = self.validate()
        if issues:
            raise DomainValidationError(issues)


__all__ = ("JointAssembly",)
