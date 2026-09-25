"""Stage 4.2 exact qualified-source bindings over the unchanged CS7 provider.

Source packages are server-controlled records, never a production default or a
client assertion of strength. Member-attachment evaluation is a labelled view
of the complete interface wrench, not a replacement of the neutral core.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.application.wi_wall_moment_geometry import PlacedWallAngle, q
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreResult,
    angle_fingerprint,
)
from frp_master_connection.calculation.angle_connector_providers import (
    AngleProviderResult,
    evaluate_angle_provider,
)
from frp_master_connection.calculation.equations import adjust_frp_property
from frp_master_connection.calculation.frp_angle_connector_provider import (
    FRPAngleContext,
    FRPSourceBinding,
    QualifiedBodyCheck,
    QualifiedFRPAngleSource,
    _body,
    frp_source_binding,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily
from frp_master_connection.domain.wi_wall_moment import WIWallMomentRequest

ATTACHMENT_METHOD = "QUALIFIED_FRP_MEMBER_ANGLE_ATTACHMENT_SOURCE_RC1"
ATTACHMENT_COVERAGE = (
    "MEMBER_THROUGH_THICKNESS_PULL_THROUGH_DELAMINATION",
    "BOLT_AXIS_FORCE_DISTRIBUTION",
    "SECONDARY_BOLT_BENDING",
    "LOCAL_LEG_MEMBER_BENDING_PRYING",
    "COMBINED_INTERACTION",
)


@dataclass(frozen=True, slots=True)
class WallMomentQualifiedSource:
    reference: str
    connector_id: str
    package: QualifiedFRPAngleSource
    attachment: bool = False
    attachment_coverage: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reference.strip() or not self.connector_id.strip():
            raise ValueError("Qualified source reference and physical connector ID are required.")


@dataclass(frozen=True, slots=True)
class WallMomentSourceRegistry:
    records: tuple[WallMomentQualifiedSource, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple((r.reference, r.connector_id, r.attachment) for r in self.records)
        if len(keys) != len(set(keys)):
            raise ValueError("Qualified source lookup must be unique.")

    def find(
        self, reference: str, connector_id: str, *, attachment: bool = False
    ) -> WallMomentQualifiedSource | None:
        return next(
            (
                r
                for r in self.records
                if (r.reference, r.connector_id, r.attachment)
                == (reference, connector_id, attachment)
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class WallMomentAttachmentResult:
    connector_id: str
    binding: FRPSourceBinding
    source_reference: str
    source_version: str | None
    coverage: tuple[str, ...]
    check: QualifiedBodyCheck
    fingerprint: str
    method: str = ATTACHMENT_METHOD
    individual_bolt_axis_forces: None = None
    invented_prying: bool = False


def provider_context(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    core: AngleCoreResult,
    *,
    attachment: bool = False,
) -> FRPAngleContext:
    from frp_master_connection.application.mat1_scope import material_for_owner

    material = material_for_owner(angle.connector_id, create_locked_ice_material_snapshot())
    shear = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_LT)
    trace = adjust_frp_property(shear.kind, shear.value, shear.qualification_status, END_USE)
    spec = angle.specification
    member_binding: object = (spec.member_pattern, spec.fastener)
    if attachment:
        # The physical region and full signed demand are explicit attachment authority.
        # Its fingerprint is distinct from the provider-independent core identity.
        member_binding = (
            ATTACHMENT_METHOD,
            request.beam,
            angle.connector_id,
            material,
            spec.geometry,
            spec.member_pattern,
            spec.fastener,
            angle.frame,
            angle.member_reference,
            core.request.member_action,
        )
    return FRPAngleContext(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        True,
        material,
        trace,
        angle_fingerprint(member_binding),
        angle_fingerprint(
            (
                spec.support_pattern,
                spec.anchors,
                tuple(
                    q(getattr(request.wall, name), request.source_length_unit)
                    for name in (
                        "width",
                        "height",
                        "thickness",
                        "connection_origin_h",
                        "connection_origin_v",
                    )
                ),
                angle.support_reference,
            )
        ),
    )


def evaluate_connector_source(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    core: AngleCoreResult,
    registry: WallMomentSourceRegistry,
) -> AngleProviderResult:
    ctx = provider_context(request, angle, core)
    source = registry.find(angle.specification.connector_source_reference, angle.connector_id)
    return evaluate_angle_provider(
        core,
        angle.specification.provider_id,
        ctx if source is None else replace(ctx, qualified_source=source.package),
    )


def evaluate_attachment_source(
    request: WIWallMomentRequest,
    angle: PlacedWallAngle,
    core: AngleCoreResult,
    registry: WallMomentSourceRegistry,
) -> WallMomentAttachmentResult:
    ctx = provider_context(request, angle, core, attachment=True)
    reference = angle.specification.attachment_source_reference
    record = registry.find(reference, angle.connector_id, attachment=True)
    binding = frp_source_binding(core, ctx)
    coverage = () if record is None else record.attachment_coverage
    if record is not None and set(coverage) != set(ATTACHMENT_COVERAGE):
        check = QualifiedBodyCheck("NOT_EVALUATED_QUALIFIED_ATTACHMENT_COVERAGE_MISSING")
    else:
        if record is not None:
            ctx = replace(ctx, qualified_source=record.package)
        # Only the native signed-envelope evaluator consumes this view. The
        # returned core, heel transport and equilibrium records remain untouched.
        view = replace(core, heel=core.request.member_action)
        check = _body(view, ctx)
    version = None if record is None else record.package.source.revision
    fingerprint = angle_fingerprint(
        (ATTACHMENT_METHOD, core.fingerprint, binding, reference, record, check)
    )
    return WallMomentAttachmentResult(
        angle.connector_id, binding, reference, version, coverage, check, fingerprint
    )
