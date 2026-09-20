"""Reviewed native ownership for wall/base families, with no numerical re-evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from frp_master_connection.application.angle_column_base_design import AngleBaseDesign
from frp_master_connection.application.column_moment_base_design import ColumnMomentDesign
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.stainless_native_results import (
    authoritative_multirow_results,
    physical_hardware_owner,
    physical_owner,
)
from frp_master_connection.application.wi_frp_support_moment_design import FRPSupportMomentDesign
from frp_master_connection.application.wi_wall_moment_design import WIWallMomentDesign
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole


@dataclass(frozen=True, slots=True)
class OwnedMomentCheck:
    identity: str
    owner: CanonicalComponent
    native_record: object


@dataclass(frozen=True, slots=True)
class MomentPartition:
    retained_non_body: tuple[OwnedMomentCheck, ...]
    superseded_frp_body: tuple[OwnedMomentCheck, ...]
    response_source_status: tuple[str, ...]
    fingerprint: str


def moment_check_partition(assembly: MaterialAssembly, design: object) -> MomentPartition:
    """Use explicit frozen result namespaces; unknown ownership is a hard failure.

    This partition establishes identity only. It does not certify an inherited
    FRP stiffness/contact/row-distribution response for stainless.
    """
    checks: list[OwnedMomentCheck] = []
    aliases = {"WI_TOP_FLANGE": "WI_BEAM", "WI_BOTTOM_FLANGE": "WI_BEAM", "WI_WEB": "WI_BEAM"}
    if isinstance(design, FRPSupportMomentDesign):
        for physical in design.preview.geometry.support_bolts:
            for layer in physical.crossing.layer_ids:
                aliases[layer] = "FRP_SUPPORT"
        for angle in design.preview.geometry.angles:
            aliases[angle.connector_id + "_SUPPORT_LEG"] = angle.connector_id
    elif isinstance(design, ColumnMomentDesign):
        for bolt in design.preview.response_binding.physical_bolts:
            for physical_layer in bolt.layers:
                aliases[physical_layer.layer_id] = physical_layer.connector_id or "COLUMN"
    elif isinstance(design, AngleBaseDesign):
        aliases.update({"COLUMN_LEG_1": "ANGLE_COLUMN", "COLUMN_LEG_2": "ANGLE_COLUMN"})

    def owner(layer: str) -> CanonicalComponent:
        # Native beam local checks use region IDs, while the physical W/I is one member.
        return physical_owner(assembly, aliases.get(layer, layer))

    def add(identity: str, layer: str, value: object) -> None:
        checks.append(OwnedMomentCheck(identity, owner(layer), value))

    if isinstance(design, (WIWallMomentDesign, FRPSupportMomentDesign)):
        local = (
            design.local_checks
            if isinstance(design, WIWallMomentDesign)
            else design.beam_local_checks
        )
        bearings = (
            (*design.web_bearing, *design.flange_bearing)
            if isinstance(design, WIWallMomentDesign)
            else design.beam_bearings
        )
        for group in local:
            rows = (
                authoritative_multirow_results(group.native_flange_response)
                if group.native_flange_response is not None
                else tuple(("NATIVE", result) for result in group.native_results)
            )
            for scenario, result in rows:
                add(
                    f"{group.connector_id}:{group.layer_id}:{scenario}:{result.result_id}",
                    group.layer_id,
                    result,
                )
        for bearing in bearings:
            add(bearing.check_id, bearing.layer_id, bearing)
        if isinstance(design, FRPSupportMomentDesign):
            for check in design.support_local_checks:
                add(check.check_id, check.layer_id, check)
    elif isinstance(design, (AngleBaseDesign, ColumnMomentDesign)):
        for check in design.local_checks:
            add(check.check_id, check.layer_id, check)
    else:
        raise ValueError("STAINLESS_NATIVE_MOMENT_FAMILY_NOT_REVIEWED")

    if isinstance(design, (WIWallMomentDesign, FRPSupportMomentDesign)):
        hardware = design.common_web_bolts
        attachments = design.attachment_results
        member_id = "WI_BEAM"
    else:
        hardware = ()
        attachments = design.member_attachment_results
        member_id = "ANGLE_COLUMN" if isinstance(design, AngleBaseDesign) else "COLUMN"
    for common_bolt in hardware:
        checks.append(
            OwnedMomentCheck(
                "NATIVE_BOLT:" + common_bolt.bolt_id,
                physical_hardware_owner(assembly, common_bolt.bolt_id),
                common_bolt,
            )
        )
    support_bolts = (
        design.support_bolts
        if isinstance(design, FRPSupportMomentDesign)
        else design.member_bolts
        if isinstance(design, (AngleBaseDesign, ColumnMomentDesign))
        else ()
    )
    for support_bolt in support_bolts:
        checks.append(
            OwnedMomentCheck(
                support_bolt.check_id,
                physical_hardware_owner(assembly, support_bolt.bolt_id),
                support_bolt,
            )
        )
    for attachment in attachments:
        checks.append(
            OwnedMomentCheck(
                "MEMBER_ATTACHMENT:" + attachment.connector_id,
                physical_owner(assembly, member_id),
                attachment,
            )
        )
    if not isinstance(design, WIWallMomentDesign) and design.local_zone is not None:
        checks.append(
            OwnedMomentCheck(
                "NATIVE_LOCAL_ZONE",
                physical_owner(
                    assembly,
                    "FRP_SUPPORT" if isinstance(design, FRPSupportMomentDesign) else member_id,
                ),
                design.local_zone,
            )
        )

    if len({check.identity for check in checks}) != len(checks):
        raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
    retained = tuple(c for c in checks if c.owner.role is not ComponentRole.CONNECTOR_BODY)
    superseded = tuple(c for c in checks if c.owner.role is ComponentRole.CONNECTOR_BODY)
    sources = design.missing_sources
    return MomentPartition(
        retained, superseded, sources, angle_fingerprint((retained, superseded, sources))
    )
