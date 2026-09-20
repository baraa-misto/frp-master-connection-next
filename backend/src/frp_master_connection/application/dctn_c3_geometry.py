"""Native C3 validation of DCTN actual interfaces and complete physical shafts.

The native surface/zone/penetration solvers receive the real placed primary
members. No fictitious C3 layer or connector body is introduced for calculation.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from frp_master_connection.application.member_profile_geometry import (
    kernel_profile_surface_patch_ids,
)
from frp_master_connection.calculation.geometry_mapping import (
    GeometryToCodeMappingRequest,
    resolve_geometry_to_code_mapping,
    validate_code_geometry,
)
from frp_master_connection.calculation.inputs import LayerLoadingSense
from frp_master_connection.calculation.properties import (
    WasherGeometry,
    create_locked_f593_fastener_snapshot,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    create_standard_hole,
)
from frp_master_connection.domain.assembly import JointAssembly
from frp_master_connection.domain.dctn_geometry import DCTNBoltCode, DCTNGeometry
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, DCTNRequest
from frp_master_connection.domain.entities import (
    AssemblyMember,
    BoltGroup,
    BoltLocation,
    ConnectionInterface,
)
from frp_master_connection.domain.member_profile import MemberProfile, MemberProfileSurfaceId
from frp_master_connection.domain.values import (
    ConnectionDesignCategory,
    CoordinateFrameKind,
    CoordinateFrameReference,
    EngineeringUnitSystem,
    PositionVector3D,
    PrincipalAxisFamily,
    ReferencePoint,
    ReferencePointKind,
    TransferIntent,
)
from frp_master_connection.geometry.bolt_paths import (
    BoltGroupGeometrySpecification,
    BoltPathDefinition,
    IntendedPenetratedLayer,
    InterfaceTargetSide,
    InterfaceZoneReference,
    ResolvedBoltGroupGeometry,
    resolve_bolt_group_geometry,
)
from frp_master_connection.geometry.interface_targeting import (
    ConnectionInterfaceGeometrySpecification,
    ConnectionZoneKind,
    ConnectionZoneSpecification,
    GeometryComparisonTolerance,
    InterfaceOriginSpecification,
    InterfaceTargetSideSpecification,
    ResolvedConnectionInterfaceGeometry,
    resolve_connection_interface_geometry,
)
from frp_master_connection.geometry.joint_context import JointGeometryBasis
from frp_master_connection.geometry.spatial import CartesianFrame3D, UnitVector3D, Vector3D
from frp_master_connection.geometry.surfaces import (
    ComponentSurfaceSet3D,
    PlanarRectangularSurface3D,
    SurfacePatch3D,
    create_component_surface_set,
)


def _surface_pair(
    profile: MemberProfile, surfaces: ComponentSurfaceSet3D, point: PositionVector3D, radius: float
) -> tuple[SurfacePatch3D, SurfacePatch3D, str]:
    outside, opposite_ids, element = kernel_profile_surface_patch_ids(profile)
    outer = next(p for p in surfaces.patches if p.id == outside)
    candidates = []
    for patch in surfaces.patches:
        if patch.id not in opposite_ids or not isinstance(
            patch.geometry, PlanarRectangularSurface3D
        ):
            continue
        g = patch.geometry
        local = g.frame.parent_to_local_point(point)
        if min(g.extent_y / 2 - abs(local.y), g.extent_z / 2 - abs(local.z)) >= radius:
            candidates.append(patch)
    if len(candidates) != 1:
        raise ValueError("DCTN_NATIVE_OPPOSING_PATCH_NOT_UNAMBIGUOUS")
    return outer, candidates[0], element


def _side(surface: SurfacePatch3D, identity: str) -> InterfaceTargetSideSpecification:
    zone = ConnectionZoneSpecification(
        identity, identity, surface.reference, ConnectionZoneKind.WHOLE_PATCH
    )
    return InterfaceTargetSideSpecification(surface.participant, (zone,), identity)


def build_dctn_c3(
    value: DCTNRequest, geometry: DCTNGeometry
) -> tuple[ResolvedBoltGroupGeometry, ...]:
    if geometry.status != "VALID":
        return ()
    placements = tuple(p.placement for p in geometry.members)
    surface_sets = tuple(create_component_surface_set(p) for p in placements)
    all_surfaces = tuple(s for group in surface_sets for s in group.patches)
    surfaces = {s.participant.entity_id: s for s in surface_sets}
    profiles = {m.physical_id: m.profile for m in geometry.members}
    natives = {m.physical_id: m for m in geometry.members}
    interfaces: list[ResolvedConnectionInterfaceGeometry] = []
    groups: list[BoltGroup] = []
    specs: list[BoltGroupGeometrySpecification] = []
    tolerance = GeometryComparisonTolerance(
        float(PhysicalQuantity.of(".000001", Unit.IN).to(value.length_unit).magnitude), 1e-9
    )
    hole = float(value.fastener.hole_diameter.to(value.length_unit).magnitude)
    for member in value.members:
        rows = tuple(r for r in geometry.rows if r.member_id == member.slot)
        axis = Vector3D(*(float(x) for x in natives[member.slot].u))
        pairs: dict[
            str, tuple[SurfacePatch3D, SurfacePatch3D, str, SurfacePatch3D, SurfacePatch3D, str]
        ] = {}
        resolved_by_side: dict[str, ResolvedConnectionInterfaceGeometry] = {}
        for side in ("NEG", "POS"):
            negative = side == "NEG"
            point = PositionVector3D(
                *(
                    float(x)
                    for x in (rows[0].negative_point if negative else rows[0].positive_point)
                )
            )
            chord = "CHORD_" + side
            cp = _surface_pair(profiles[chord], surfaces[chord], point, hole / 2)
            sid = (
                (
                    MemberProfileSurfaceId.FLANGE_NEG_OUTER
                    if negative
                    else MemberProfileSurfaceId.FLANGE_POS_OUTER
                )
                if member.section.form is DCTNForm.W_I
                else (
                    MemberProfileSurfaceId.Z_NEG_FACE
                    if negative
                    else MemberProfileSurfaceId.Z_POS_FACE
                )
            )
            mp = _surface_pair(
                replace(profiles[member.slot], selected_surface=sid),
                surfaces[member.slot],
                point,
                hole / 2,
            )
            pairs[side] = (*cp, *mp)
            identity = f"{member.slot}:{side}:INTERFACE"
            logical = ConnectionInterface(
                identity, identity, cp[0].participant, mp[0].participant, TransferIntent.SHEAR_ONLY
            )
            first, second = (
                _side(cp[0], identity + ":CHORD_ZONE"),
                _side(mp[0], identity + ":MEMBER_ZONE"),
            )
            primary_surface = cast(PlanarRectangularSurface3D, cp[0].geometry)
            origin = primary_surface.frame.parent_to_local_point(point)
            resolved = resolve_connection_interface_geometry(
                ConnectionInterfaceGeometrySpecification(
                    logical,
                    first,
                    second,
                    InterfaceOriginSpecification(first.primary_zone_id, origin.y, origin.z),
                    axis,
                    tolerance,
                ),
                all_surfaces,
            )
            interfaces.append(resolved)
            resolved_by_side[side] = resolved
        for physical_side in (
            ("NEG", "POS") if member.section.form is DCTNForm.W_I else ("THROUGH",)
        ):
            primary_side = "POS" if physical_side == "POS" else "NEG"
            primary = resolved_by_side[primary_side]
            identity = f"{member.slot}:{physical_side}:GROUP"
            selected_interfaces = (
                (resolved_by_side["NEG"], resolved_by_side["POS"])
                if physical_side == "THROUGH"
                else (primary,)
            )
            locations = tuple(
                BoltLocation(
                    f"{member.slot}:ROW_{r.row}:{physical_side}",
                    PositionVector3D(0, float(r.from_start - rows[0].from_start), 0),
                )
                for r in rows
            )
            group = BoltGroup(
                identity,
                identity,
                CoordinateFrameReference(CoordinateFrameKind.BOLT_GROUP_LOCAL, identity),
                ReferencePoint(ReferencePointKind.BOLT_GROUP_ORIGIN, identity),
                tuple(i.interface.id for i in selected_interfaces),
                locations,
            )
            groups.append(group)
            layers: list[IntendedPenetratedLayer] = []

            def layer(
                side: str,
                *,
                chord_layer: bool,
                reverse: bool = False,
                pair_set: dict[
                    str,
                    tuple[SurfacePatch3D, SurfacePatch3D, str, SurfacePatch3D, SurfacePatch3D, str],
                ] = pairs,
                interface_set: dict[str, ResolvedConnectionInterfaceGeometry] = resolved_by_side,
                owner: str = member.slot,
            ) -> IntendedPenetratedLayer:
                pair = pair_set[side]
                outer, inner, element = pair[:3] if chord_layer else pair[3:]
                interface = interface_set[side]
                target = interface.first_side if chord_layer else interface.second_side
                entry, exit_patch = (outer, inner) if reverse else (inner, outer)
                return IntendedPenetratedLayer(
                    ("CHORD_" + side if chord_layer else owner) + ":" + element,
                    outer.participant,
                    element,
                    entry.reference,
                    exit_patch.reference,
                    (
                        InterfaceZoneReference(
                            interface.interface.id,
                            InterfaceTargetSide.FIRST
                            if chord_layer
                            else InterfaceTargetSide.SECOND,
                            target.primary_zone_id,
                        ),
                    ),
                    hole,
                )

            if physical_side == "THROUGH":
                layers.append(layer("NEG", chord_layer=True))
                if member.section.form is DCTNForm.RHS:
                    layers.extend(
                        (
                            layer("NEG", chord_layer=False, reverse=True),
                            layer("POS", chord_layer=False),
                        )
                    )
                else:
                    near, far = pairs["NEG"][3], pairs["POS"][3]
                    layers.append(
                        IntendedPenetratedLayer(
                            member.slot + ":PLATE",
                            near.participant,
                            "PLATE",
                            near.reference,
                            far.reference,
                            tuple(
                                InterfaceZoneReference(
                                    i.interface.id,
                                    InterfaceTargetSide.SECOND,
                                    i.second_side.primary_zone_id,
                                )
                                for i in selected_interfaces
                            ),
                            hole,
                        )
                    )
                layers.append(layer("POS", chord_layer=True, reverse=True))
            else:
                layers.extend(
                    (
                        layer(physical_side, chord_layer=True),
                        layer(physical_side, chord_layer=False, reverse=True),
                    )
                )
            paths = tuple(BoltPathDefinition(b.id, tuple(layers)) for b in locations)
            specs.append(
                BoltGroupGeometrySpecification(
                    group, primary.interface.id, 0, 0, axis, tolerance, paths
                )
            )
    assembly = JointAssembly(
        "DCTN_NATIVE_ASSEMBLY",
        "Double-Channel Truss Node",
        ConnectionDesignCategory.SHEAR,
        EngineeringUnitSystem.US_CUSTOMARY
        if value.length_unit is Unit.IN
        else EngineeringUnitSystem.SI,
        tuple(cast(AssemblyMember, p.component) for p in placements),
        (),
        (),
        tuple(i.interface for i in interfaces),
        tuple(groups),
        (),
        (),
    )
    frame = CartesianFrame3D(
        PositionVector3D(0, 0, 0),
        UnitVector3D(1, 0, 0),
        UnitVector3D(0, 1, 0),
        UnitVector3D(0, 0, 1),
    )
    basis = JointGeometryBasis(assembly, frame, placements, (), surface_sets, (), tuple(interfaces))
    return tuple(resolve_bolt_group_geometry(basis, spec) for spec in specs)


def dctn_code_mappings(
    value: DCTNRequest, geometry: DCTNGeometry, groups: tuple[ResolvedBoltGroupGeometry, ...]
) -> tuple[DCTNBoltCode, ...]:
    """Consume native C3 material axes, ray/end/edge mapping and code prerequisites."""
    hardware = value.fastener.hardware
    washer = WasherGeometry(hardware.washer_diameter, hardware.washer_thickness, True, True)
    standard = create_standard_hole(
        value.fastener.diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
    )
    records = []
    for group in groups:
        slot = group.bolt_group.id.split(":")[0]
        member = next(m for m in value.members if m.slot == slot)
        native = next(m for m in geometry.members if m.physical_id == slot)
        sign = -1 if member.axial_force.canonical_magnitude < 0 else 1
        for path in group.paths:
            for layer in path.layers:
                owner = layer.definition.participant.entity_id
                # Actual in-plane bearing reaction on the member is opposite
                # its transfer into the chords; native material axes are reused.
                factor = -sign if owner == slot else sign
                force = Vector3D(*(float(factor * x) for x in native.u))
                mapping = resolve_geometry_to_code_mapping(
                    GeometryToCodeMappingRequest(
                        group,
                        path.definition.bolt_location_id,
                        layer.definition.id,
                        value.fastener.diameter,
                        force,
                        PrincipalAxisFamily.X,
                        value.length_unit,
                    )
                )
                validation = validate_code_geometry(
                    mapping=mapping,
                    standard_hole=standard,
                    fastener=create_locked_f593_fastener_snapshot(),
                    washer=washer,
                    loading_sense=LayerLoadingSense.COMPRESSION
                    if sign < 0
                    else LayerLoadingSense.TENSION,
                    connection_hole_diameters=(value.fastener.hole_diameter,) * len(group.paths),
                    logical_bolt_count=len(group.paths),
                    row_count=member.pattern.rows,
                )
                records.append(
                    DCTNBoltCode(
                        path.definition.bolt_location_id,
                        owner,
                        layer.definition.physical_element_id,
                        mapping,
                        validation,
                    )
                )
    return tuple(records)
