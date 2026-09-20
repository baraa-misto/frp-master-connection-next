"""Resolved Stage 1.3C3 joint geometry context and symbolic frame bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from frp_master_connection.domain import (
    CoordinateFrameKind,
    CoordinateFrameReference,
    JointAssembly,
    ParticipantKind,
)
from frp_master_connection.domain.validation import require_tuple
from frp_master_connection.geometry.interface_targeting import (
    ResolvedConnectionInterfaceGeometry,
)
from frp_master_connection.geometry.placement import PlacedComponentGeometry3D
from frp_master_connection.geometry.spatial import GLOBAL_FRAME, CartesianFrame3D
from frp_master_connection.geometry.surfaces import ComponentSurfaceSet3D, SurfacePatch3D

if TYPE_CHECKING:
    from frp_master_connection.geometry.bolt_paths import ResolvedBoltGroupGeometry


def _require_exact_ids(actual: tuple[str, ...], expected: tuple[str, ...], field_name: str) -> None:
    if actual != expected:
        raise ValueError(f"{field_name} must match the JointAssembly declaration order exactly.")


@dataclass(frozen=True, slots=True)
class ResolvedFrameBinding:
    """One symbolic frame reference bound to exact resolved geometry and owner provenance."""

    reference: CoordinateFrameReference
    frame: CartesianFrame3D
    owner: object | None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, CoordinateFrameReference):
            raise TypeError("ResolvedFrameBinding.reference must be CoordinateFrameReference.")
        if not isinstance(self.frame, CartesianFrame3D):
            raise TypeError("ResolvedFrameBinding.frame must be CartesianFrame3D.")
        if self.reference.kind is CoordinateFrameKind.GLOBAL:
            if self.owner is not None or self.frame is not GLOBAL_FRAME:
                raise ValueError("The global binding requires GLOBAL_FRAME and no owner.")
        elif self.owner is None:
            raise ValueError("A local resolved frame binding requires exact owner provenance.")


@dataclass(frozen=True, slots=True)
class JointGeometryBasis:
    """Complete assembly geometry that exists before bolt paths are resolved."""

    assembly: JointAssembly
    joint_frame: CartesianFrame3D
    placed_members: tuple[PlacedComponentGeometry3D, ...]
    placed_connectors: tuple[PlacedComponentGeometry3D, ...]
    component_surface_sets: tuple[ComponentSurfaceSet3D, ...]
    support_surfaces: tuple[SurfacePatch3D, ...]
    resolved_interfaces: tuple[ResolvedConnectionInterfaceGeometry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.assembly, JointAssembly):
            raise TypeError("JointGeometryBasis.assembly must be JointAssembly.")
        self.assembly.require_valid()
        if not isinstance(self.joint_frame, CartesianFrame3D):
            raise TypeError("JointGeometryBasis.joint_frame must be CartesianFrame3D.")
        for name, values, item_type in (
            ("placed_members", self.placed_members, PlacedComponentGeometry3D),
            ("placed_connectors", self.placed_connectors, PlacedComponentGeometry3D),
            ("component_surface_sets", self.component_surface_sets, ComponentSurfaceSet3D),
            ("support_surfaces", self.support_surfaces, SurfacePatch3D),
            (
                "resolved_interfaces",
                self.resolved_interfaces,
                ResolvedConnectionInterfaceGeometry,
            ),
        ):
            require_tuple(values, f"JointGeometryBasis.{name}")
            if any(not isinstance(value, item_type) for value in values):
                raise TypeError(f"JointGeometryBasis.{name} contains an invalid item.")

        _require_exact_ids(
            tuple(item.component.id for item in self.placed_members),
            tuple(item.id for item in self.assembly.members),
            "JointGeometryBasis.placed_members",
        )
        _require_exact_ids(
            tuple(item.component.id for item in self.placed_connectors),
            tuple(item.id for item in self.assembly.connector_components),
            "JointGeometryBasis.placed_connectors",
        )
        if any(
            placed.component is not declared
            for placed, declared in zip(self.placed_members, self.assembly.members, strict=True)
        ) or any(
            placed.component is not declared
            for placed, declared in zip(
                self.placed_connectors,
                self.assembly.connector_components,
                strict=True,
            )
        ):
            raise ValueError("Placed component objects must be exact assembly-owned entities.")

        expected_surface_participants = tuple(
            placed.participant for placed in (*self.placed_members, *self.placed_connectors)
        )
        if tuple(item.participant for item in self.component_surface_sets) != (
            expected_surface_participants
        ):
            raise ValueError("Component surface sets must cover every placed component in order.")
        if any(
            surfaces.placed_component is not placed
            for surfaces, placed in zip(
                self.component_surface_sets,
                (*self.placed_members, *self.placed_connectors),
                strict=True,
            )
        ):
            raise ValueError("Surface sets must retain their exact placed component objects.")

        support_ids = {support.id for support in self.assembly.supports}
        support_keys = tuple(
            (surface.participant.entity_id, surface.id) for surface in self.support_surfaces
        )
        if support_keys != tuple(sorted(support_keys)) or len(set(support_keys)) != len(
            support_keys
        ):
            raise ValueError("Support surfaces must have unique deterministic participant/IDs.")
        if any(
            surface.participant.kind is not ParticipantKind.SUPPORT
            or surface.participant.entity_id not in support_ids
            for surface in self.support_surfaces
        ):
            raise ValueError("Every support surface must belong to a declared assembly support.")

        _require_exact_ids(
            tuple(item.interface.id for item in self.resolved_interfaces),
            tuple(item.id for item in self.assembly.interfaces),
            "JointGeometryBasis.resolved_interfaces",
        )
        if any(
            resolved.interface is not declared
            for resolved, declared in zip(
                self.resolved_interfaces, self.assembly.interfaces, strict=True
            )
        ):
            raise ValueError("Resolved interfaces must retain exact assembly interface objects.")

    @property
    def all_surfaces(self) -> tuple[SurfacePatch3D, ...]:
        """Return every authoritative component/support patch in deterministic order."""
        return (
            tuple(
                patch
                for surface_set in self.component_surface_sets
                for patch in surface_set.patches
            )
            + self.support_surfaces
        )

    def component_surface_set(
        self, participant_kind: ParticipantKind, owner_id: str
    ) -> ComponentSurfaceSet3D:
        """Resolve one exact component surface set without fallback."""
        for surface_set in self.component_surface_sets:
            if (
                surface_set.participant.kind is participant_kind
                and surface_set.participant.entity_id == owner_id
            ):
                return surface_set
        raise KeyError(
            f"No component surface set exists for {participant_kind.value} {owner_id!r}."
        )


@dataclass(frozen=True, slots=True)
class JointGeometryContext:
    """Complete resolved assembly geometry including every logical bolt group."""

    basis: JointGeometryBasis
    resolved_bolt_groups: tuple[ResolvedBoltGroupGeometry, ...]

    def __post_init__(self) -> None:
        from frp_master_connection.geometry.bolt_paths import ResolvedBoltGroupGeometry

        if not isinstance(self.basis, JointGeometryBasis):
            raise TypeError("JointGeometryContext.basis must be JointGeometryBasis.")
        require_tuple(self.resolved_bolt_groups, "JointGeometryContext.resolved_bolt_groups")
        if any(
            not isinstance(item, ResolvedBoltGroupGeometry) for item in self.resolved_bolt_groups
        ):
            raise TypeError("resolved_bolt_groups contains an invalid item.")
        _require_exact_ids(
            tuple(item.bolt_group.id for item in self.resolved_bolt_groups),
            tuple(item.id for item in self.basis.assembly.bolt_groups),
            "JointGeometryContext.resolved_bolt_groups",
        )
        if any(
            resolved.bolt_group is not declared
            for resolved, declared in zip(
                self.resolved_bolt_groups,
                self.basis.assembly.bolt_groups,
                strict=True,
            )
        ):
            raise ValueError("Resolved bolt groups must retain exact assembly bolt-group objects.")
        if any(
            resolved.unit_system is not self.basis.assembly.unit_system
            for resolved in self.resolved_bolt_groups
        ):
            raise ValueError(
                "Resolved bolt geometry must retain the assembly unit-system identity."
            )

    @property
    def assembly(self) -> JointAssembly:
        return self.basis.assembly

    def resolve_frame(self, reference: CoordinateFrameReference) -> ResolvedFrameBinding:
        """Bind one symbolic frame to exact context geometry without fallback."""
        if not isinstance(reference, CoordinateFrameReference):
            raise TypeError("reference must be CoordinateFrameReference.")
        owner_id = reference.owner_id
        if reference.kind is CoordinateFrameKind.GLOBAL:
            return ResolvedFrameBinding(reference, GLOBAL_FRAME, None)
        if reference.kind is CoordinateFrameKind.JOINT_LOCAL:
            if owner_id != self.assembly.id:
                raise KeyError("Joint-local frame owner does not match this assembly.")
            return ResolvedFrameBinding(reference, self.basis.joint_frame, self.assembly)
        if reference.kind is CoordinateFrameKind.MEMBER_LOCAL:
            for placed in self.basis.placed_members:
                if placed.component.id == owner_id:
                    return ResolvedFrameBinding(reference, placed.global_frame, placed.component)
        elif reference.kind is CoordinateFrameKind.CONNECTOR_LOCAL:
            for placed in self.basis.placed_connectors:
                if placed.component.id == owner_id:
                    return ResolvedFrameBinding(reference, placed.global_frame, placed.component)
        elif reference.kind is CoordinateFrameKind.INTERFACE_LOCAL:
            for resolved_interface in self.basis.resolved_interfaces:
                if resolved_interface.interface.id == owner_id:
                    return ResolvedFrameBinding(
                        reference,
                        resolved_interface.interface_frame,
                        resolved_interface.interface,
                    )
        else:
            for resolved_bolt_group in self.resolved_bolt_groups:
                if resolved_bolt_group.bolt_group.id == owner_id:
                    return ResolvedFrameBinding(
                        reference,
                        resolved_bolt_group.bolt_group_frame,
                        resolved_bolt_group.bolt_group,
                    )
        raise KeyError(f"Unresolved {reference.kind.value} frame owner {owner_id!r}.")


__all__ = (
    "JointGeometryBasis",
    "JointGeometryContext",
    "ResolvedFrameBinding",
)
