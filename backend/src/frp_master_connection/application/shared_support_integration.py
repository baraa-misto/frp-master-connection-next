"""Stage 3.3C2 shared support and rectangular full-through integration seam."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import cast

from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    ExactProfileVector3D,
    FullThroughBoltHardware,
    FullThroughBoltPath,
    FullThroughContainment,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    PositionVector3D,
    PrincipalAxisFamily,
    RectangularLocalMechanicsLimitation,
    RectangularMaterialBasis,
    SharedSupportSelection,
    SharedSupportTargetId,
    build_rhs_full_through_core,
    build_srs_full_through_core,
    compose_external_connector_layers,
    evaluate_full_through_containment,
    external_connector_layer,
    full_through_bolt_fingerprint,
    full_through_bolt_hardware,
    rectangular_opposing_face_pair,
)
from frp_master_connection.geometry import (
    PlacedComponentGeometry3D,
    SectionPoint2D,
    Vector3D,
    translate_point,
)

_CONNECTOR_BASIS = RectangularMaterialBasis(
    ExactProfileVector3D(Decimal(1), Decimal(0), Decimal(0)),
    ExactProfileVector3D(Decimal(0), Decimal(1), Decimal(0)),
    ExactProfileVector3D(Decimal(0), Decimal(0), Decimal(1)),
)


@dataclass(frozen=True, slots=True)
class IntegratedFullThroughBoltTrace:
    """One C1 path integrated into a connection family without new mechanics."""

    path: FullThroughBoltPath
    hardware: FullThroughBoltHardware
    physical_start_point: PositionVector3D
    physical_end_point: PositionVector3D
    containment: FullThroughContainment
    limitations: tuple[RectangularLocalMechanicsLimitation, ...]
    path_fingerprint: str
    geometry_valid: bool


def _c2_segment_identities(path: FullThroughBoltPath) -> FullThroughBoltPath:
    identities = {
        "NEAR_WALL": "RHS_NEAR_WALL",
        "CAVITY": "RHS_CAVITY",
        "FAR_WALL": "RHS_FAR_WALL",
    }
    return replace(
        path,
        segments=tuple(
            replace(item, identity=identities.get(item.identity, item.identity))
            for item in path.segments
        ),
    )


def _physical_hardware_endpoints(
    profile: MemberProfile,
    placed_profile: PlacedComponentGeometry3D,
    path: FullThroughBoltPath,
    connector_thickness: Decimal,
    far_connector_thickness: Decimal | None = None,
) -> tuple[PositionVector3D, PositionVector3D]:
    """Resolve the physical head-side and nut-side endpoints from placed geometry."""

    faces = rectangular_opposing_face_pair(profile, path.axis.selected_face)
    local_x = path.axis.local_u + profile.dimensions.member_length / Decimal(2)
    selected_coordinate = faces.selected_surface.plane_coordinate
    opposite_coordinate = faces.opposite_surface.plane_coordinate
    if faces.selected_surface.plane_axis is PrincipalAxisFamily.Y:
        selected_section = SectionPoint2D(float(selected_coordinate), float(path.axis.local_v))
        opposite_section = SectionPoint2D(float(opposite_coordinate), float(path.axis.local_v))
    else:
        selected_section = SectionPoint2D(float(path.axis.local_v), float(selected_coordinate))
        opposite_section = SectionPoint2D(float(path.axis.local_v), float(opposite_coordinate))
    selected_exterior = placed_profile.section_point_to_global(float(local_x), selected_section)
    opposite_exterior = placed_profile.section_point_to_global(float(local_x), opposite_section)
    local_normal = faces.selected_surface.local_outward_normal
    outward = placed_profile.global_frame.local_to_parent_vector(
        Vector3D(float(local_normal.x), float(local_normal.y), float(local_normal.z))
    )
    far_thickness = Decimal(0) if far_connector_thickness is None else far_connector_thickness
    return (
        translate_point(selected_exterior, outward * float(connector_thickness)),
        translate_point(opposite_exterior, outward * -float(far_thickness)),
    )


def build_integrated_full_through_bolt(
    profile: MemberProfile,
    *,
    placed_profile: PlacedComponentGeometry3D | None = None,
    selected_surface: MemberProfileSurfaceId,
    bolt_id: str,
    local_uv: tuple[Decimal, Decimal],
    hole_radius: Decimal,
    connector_identity: str,
    connector_thickness: Decimal,
    connector_material_region_id: str,
    rectangular_material_region_id: str,
    source_length_unit: Unit,
    far_connector_identity: str | None = None,
    far_connector_thickness: Decimal | None = None,
    far_connector_material_region_id: str | None = None,
) -> IntegratedFullThroughBoltTrace:
    """Compose an external connector with one exact RHS/SRS C1 core."""

    limitations: tuple[RectangularLocalMechanicsLimitation, ...]
    if profile.family is MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION:
        core = build_rhs_full_through_core(
            profile,
            selected_surface,
            bolt_id=bolt_id,
            local_uv=local_uv,
            material_region_id=rectangular_material_region_id,
        )
        limitations = (
            RectangularLocalMechanicsLimitation.RHS_LOCAL_WALL_RESPONSE,
            RectangularLocalMechanicsLimitation.RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT,
        )
    elif profile.family is MemberProfileFamily.SOLID_RECTANGULAR_SECTION:
        core = build_srs_full_through_core(
            profile,
            selected_surface,
            bolt_id=bolt_id,
            local_uv=local_uv,
            material_region_id=rectangular_material_region_id,
        )
        limitations = (
            RectangularLocalMechanicsLimitation.SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY,
        )
    else:
        raise ValueError("Integrated full-through construction requires RHS or SRS.")
    if not isinstance(placed_profile, PlacedComponentGeometry3D):
        raise TypeError("Integrated full-through construction requires placed_profile.")
    far_values = (
        far_connector_identity,
        far_connector_thickness,
        far_connector_material_region_id,
    )
    if any(item is not None for item in far_values) and not all(
        item is not None for item in far_values
    ):
        raise ValueError("A far connector layer requires identity, thickness, and material region.")
    far_layers = (
        ()
        if far_connector_identity is None
        else (
            external_connector_layer(
                far_connector_identity,
                cast(Decimal, far_connector_thickness),
                material_region_id=cast(str, far_connector_material_region_id),
                material_basis=_CONNECTOR_BASIS,
            ),
        )
    )
    path = compose_external_connector_layers(
        _c2_segment_identities(core),
        near_layers=(
            external_connector_layer(
                connector_identity,
                connector_thickness,
                material_region_id=connector_material_region_id,
                material_basis=_CONNECTOR_BASIS,
            ),
        ),
        far_layers=far_layers,
    )
    containment = evaluate_full_through_containment(
        profile,
        path.axis,
        bolt_id=bolt_id,
        hole_radius=hole_radius,
    )
    scale = Decimal(1) if source_length_unit is Unit.IN else Decimal(1) / Decimal("25.4")

    def fingerprint_length(value: Decimal) -> Decimal:
        # Fingerprint-only transport normalization absorbs sub-picoinch float-kernel
        # projection noise; the authoritative production path remains untouched.
        return (value * scale).quantize(Decimal("0.000000000001"))

    normalized_path = replace(
        path,
        axis=replace(
            path.axis,
            local_u=fingerprint_length(path.axis.local_u),
            local_v=fingerprint_length(path.axis.local_v),
        ),
        segments=tuple(
            replace(item, length=fingerprint_length(item.length)) for item in path.segments
        ),
    )
    physical_start, physical_end = _physical_hardware_endpoints(
        profile,
        placed_profile,
        path,
        connector_thickness,
        far_connector_thickness,
    )
    return IntegratedFullThroughBoltTrace(
        path,
        full_through_bolt_hardware(path),
        physical_start,
        physical_end,
        containment,
        limitations,
        full_through_bolt_fingerprint(normalized_path),
        containment.status.value == "VALID",
    )


def require_shared_support_selection(
    target_id: SharedSupportTargetId,
    profile: MemberProfile,
) -> SharedSupportSelection:
    """The one target/profile contract used by Tee and Single Clip-Angle."""

    return SharedSupportSelection(target_id, profile)


__all__ = (
    "IntegratedFullThroughBoltTrace",
    "build_integrated_full_through_bolt",
    "require_shared_support_selection",
)
