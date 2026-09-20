"""Stage 4.3 server-only source registry and actual FRP-support fixture bindings."""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    FRPSupportMomentPreview,
    SupportTransfer,
    support_uvn,
)
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.application.wi_wall_moment_geometry import _bounds, q
from frp_master_connection.application.wi_wall_moment_sources import (
    ATTACHMENT_COVERAGE,
    WallMomentAttachmentResult,
    WallMomentQualifiedSource,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    angle_fingerprint,
)
from frp_master_connection.calculation.angle_connector_providers import (
    AngleProviderResult,
    evaluate_angle_provider,
)
from frp_master_connection.calculation.equations import adjust_frp_property
from frp_master_connection.calculation.frp_angle_connector_provider import (
    FRPAngleContext,
    QualifiedBodyCheck,
    _body,
    frp_source_binding,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import (
    PhysicalResponseBolt,
    QualifiedSupportResponse,
    ResponseContactDomain,
    SupportResponseBinding,
)
from frp_master_connection.domain.material_architecture import (
    ConnectorMaterialFamily,
    EngineeringPropertySource,
)
from frp_master_connection.domain.wi_frp_support_moment import SupportMode

ZONE_REQUIREMENTS = {
    SupportMode.WI_FLANGE: ("FLANGE_FACE_BENDING", "FLANGE_WEB_JUNCTION_TRANSFER"),
    SupportMode.WI_WEB: ("WEB_LOCAL_RESPONSE", "WEB_TO_SECTION_TRANSFER"),
    SupportMode.CHANNEL_WEB: ("CHANNEL_WEB_FLANGE_JUNCTION", "ASYMMETRIC_SECTION_TRANSFER"),
    SupportMode.HOLLOW_SQUARE: (
        "NEAR_FAR_WALL_RESPONSE",
        "SIDE_WALL_INTERACTION",
        "WALL_BENDING_CRUSHING_OVALIZATION",
        "LONG_BOLT_RESPONSE",
    ),
    SupportMode.SOLID_SQUARE: (
        "THREE_DIMENSIONAL_BEARING",
        "WASHER_BOLT_LOAD_SPREAD",
        "LOCAL_SPLITTING_THROUGH_THICKNESS",
        "LONG_BOLT_RESPONSE",
    ),
}
SHARED_ZONE_REQUIREMENTS = ("COMMON_NET_AND_BLOCK_SHEAR_PATHS", "FOUR_GROUP_COMBINED_INTERACTION")


@dataclass(frozen=True, slots=True)
class SupportFastenerSource:
    reference: str
    source: EngineeringPropertySource
    exact_fastener_and_grip_binding: str
    nominal_tensile_stress: PhysicalQuantity
    nominal_shear_stress: PhysicalQuantity
    condition: str
    authorized_section_methods: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QualifiedZoneCheck:
    check_id: str
    coverage: tuple[str, ...]
    demand: PhysicalQuantity
    design_capacity: PhysicalQuantity
    method: str
    source_locator: str


@dataclass(frozen=True, slots=True)
class QualifiedLocalSupportZone:
    reference: str
    source: EngineeringPropertySource
    exact_binding: str
    support_mode: SupportMode
    issuer: str
    contact_stiffness_boundary_domain: tuple[str, ...]
    checks: tuple[QualifiedZoneCheck, ...]
    # Already-qualified source results for this complete assembly/load, not an
    # invented analytical wall/solid strength model or an angle-body certificate.
    method: str = "QUALIFIED_FRP_LOCAL_SUPPORT_ASSEMBLY_CAPACITY_AND_INTERACTION_RC1"


@dataclass(frozen=True, slots=True)
class FRPSupportSourceRegistry:
    connector_sources: tuple[WallMomentQualifiedSource, ...] = ()
    responses: tuple[QualifiedSupportResponse, ...] = ()
    fasteners: tuple[SupportFastenerSource, ...] = ()
    local_zones: tuple[QualifiedLocalSupportZone, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple((r.reference, r.connector_id, r.attachment) for r in self.connector_sources)
        if len(keys) != len(set(keys)):
            raise ValueError("Connector qualification lookup must be unique")
        fastener_keys = tuple(
            (r.reference, r.exact_fastener_and_grip_binding) for r in self.fasteners
        )
        if len(fastener_keys) != len(set(fastener_keys)):
            raise ValueError("Bound fastener lookup must be unique")
        for records in (self.responses, self.local_zones):
            refs = tuple(r.reference for r in records)
            if any(not ref.strip() for ref in refs) or len(refs) != len(set(refs)):
                raise ValueError("Server source references must be unique and nonempty")


EMPTY_SOURCES = FRPSupportSourceRegistry()


def response_binding(preview: FRPSupportMomentPreview) -> SupportResponseBinding:
    """Bind exact native outputs, all physical inputs, and actual contact domains."""
    geometry = preview.geometry
    bolts = []
    for bolt in geometry.support_bolts:
        near = support_uvn(
            AngleWrench(
                bolt.support_point,
                preview.joint_right_hand_action.force,
                preview.joint_right_hand_action.moment,
            )
        ).reference
        far = support_uvn(
            AngleWrench(
                bolt.hardware.end,
                preview.joint_right_hand_action.force,
                preview.joint_right_hand_action.moment,
            )
        ).reference
        bolts.append(
            PhysicalResponseBolt(
                bolt.hardware.hardware_id,
                bolt.hardware.group_id,
                near,
                far,
                bolt.crossing.layer_ids,
            )
        )
    contacts = []
    for angle in geometry.angles:
        part = next(p for p in geometry.parts if p.part_id == f"{angle.connector_id}_SUPPORT_LEG")
        lo, hi = _bounds(part)
        layer = next(
            b.crossing.layer_ids[0]
            for b in geometry.support_bolts
            if b.hardware.group_id == f"{angle.connector_id}_SUPPORT_GROUP"
        )
        contacts.append(
            ResponseContactDomain(
                f"{angle.connector_id}_SUPPORT_GROUP",
                q(0, Unit.IN),
                q(lo[1], Unit.IN),
                q(hi[1], Unit.IN),
                q(lo[2], Unit.IN),
                q(hi[2], Unit.IN),
                layer,
            )
        )
    return SupportResponseBinding(
        angle_fingerprint(preview.input.engineering_input()),
        geometry.fingerprint,
        tuple(t.core.fingerprint for t in preview.connectors),
        angle_fingerprint(
            (
                create_locked_ice_material_snapshot(),
                preview.input.engineering_input().angles,
                preview.input.support.material_id,
                preview.input.beam_material_id,
            )
        ),
        tuple(bolts),
        tuple((f"{t.connector_id}_SUPPORT_GROUP", t.support_uvn) for t in preview.connectors),
        tuple(contacts),
        preview.input.support.mode.value,
        preview.input.support.face,
    )


def fastener_binding(preview: FRPSupportMomentPreview, connector: str) -> str:
    index = next(i for i, t in enumerate(preview.connectors) if t.connector_id == connector)
    spec = preview.input.angles[index]
    return angle_fingerprint(
        (
            spec.support_fastener,
            spec.support_hardware,
            tuple(
                (b.hardware, b.crossing)
                for b in preview.geometry.support_bolts
                if b.hardware.group_id == f"{connector}_SUPPORT_GROUP"
            ),
        )
    )


def local_zone_binding(preview: FRPSupportMomentPreview) -> str:
    return angle_fingerprint(
        (
            response_binding(preview),
            preview.support_contribution,
            preview.beam_allocation_applicability,
            ZONE_REQUIREMENTS[preview.input.support.mode],
            SHARED_ZONE_REQUIREMENTS,
        )
    )


def frp_support_provider_context(
    preview: FRPSupportMomentPreview,
    transfer: SupportTransfer,
    *,
    attachment: bool = False,
) -> FRPAngleContext:
    index = next(
        i for i, t in enumerate(preview.connectors) if t.connector_id == transfer.connector_id
    )
    spec = preview.input.angles[index]
    material = create_locked_ice_material_snapshot()
    shear = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_LT)
    adjusted = adjust_frp_property(shear.kind, shear.value, shear.qualification_status, END_USE)
    member = (
        spec.member_pattern,
        spec.fastener,
        spec.member_hardware,
        preview.input.beam_material_id,
    )
    member_binding: object = (
        member
        if not attachment
        else (
            "STAGE43_QUALIFIED_MEMBER_ATTACHMENT",
            member,
            preview.input.engineering_input().beam,
            preview.input.beam_physical_length,
            transfer.connector_id,
            transfer.core.request.member_action,
        )
    )
    return FRPAngleContext(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        True,
        material,
        adjusted,
        angle_fingerprint(member_binding),
        angle_fingerprint((response_binding(preview), transfer.connector_id)),
    )


def evaluate_frp_support_connector_sources(
    preview: FRPSupportMomentPreview,
    transfer: SupportTransfer,
    registry: FRPSupportSourceRegistry,
) -> tuple[AngleProviderResult, WallMomentAttachmentResult]:
    index = next(
        i for i, t in enumerate(preview.connectors) if t.connector_id == transfer.connector_id
    )
    spec, core = preview.input.angles[index], transfer.core
    ctx = frp_support_provider_context(preview, transfer)
    record = next(
        (
            r
            for r in registry.connector_sources
            if (r.reference, r.connector_id, r.attachment)
            == (spec.connector_source_reference, transfer.connector_id, False)
        ),
        None,
    )
    provider = evaluate_angle_provider(
        core,
        spec.provider_id,
        ctx if record is None else replace(ctx, qualified_source=record.package),
    )
    ctx = frp_support_provider_context(preview, transfer, attachment=True)
    record = next(
        (
            r
            for r in registry.connector_sources
            if (r.reference, r.connector_id, r.attachment)
            == (spec.attachment_source_reference, transfer.connector_id, True)
        ),
        None,
    )
    coverage = () if record is None else record.attachment_coverage
    if record is not None and set(coverage) != set(ATTACHMENT_COVERAGE):
        check = QualifiedBodyCheck("NOT_EVALUATED_QUALIFIED_ATTACHMENT_COVERAGE_MISSING")
    else:
        check = _body(
            replace(core, heel=core.request.member_action),
            ctx if record is None else replace(ctx, qualified_source=record.package),
        )
    attachment_result = WallMomentAttachmentResult(
        transfer.connector_id,
        frp_source_binding(core, ctx),
        spec.attachment_source_reference,
        None if record is None else record.package.source.revision,
        coverage,
        check,
        angle_fingerprint((core.fingerprint, ctx, record, check)),
    )
    return provider, attachment_result
