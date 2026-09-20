"""Stage 4.4-specific source bindings over accepted core and response primitives."""

from dataclasses import dataclass, replace

from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    AngleBaseTransfer,
)
from frp_master_connection.application.angle_column_base_sources import AngleBaseSourceRegistry
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    base_fingerprint,
    opposite,
    rotate,
    subtract,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    components,
    quantity_vector,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.equations import adjust_frp_property
from frp_master_connection.calculation.frp_angle_connector_provider import FRPAngleContext
from frp_master_connection.calculation.in_plane_wrench_demand import InPlaneWrenchResult
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import (
    PhysicalResponseBolt,
    QualifiedSupportResponse,
    ResponseContactDomain,
    ResponseProof,
    ShaftDemand,
    SupportResponseBinding,
    prove_support_response,
    qualified_source,
)
from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily

MEMBER_RESPONSE_DOMAIN = "STAGE_4_4_ANGLE_COLUMN_MEMBER_NORMAL_CONTACT_RESPONSE"
MEMBER_RESPONSE_COVERAGE = (
    "TOTAL_BOLT_TENSION_INCLUDING_PRYING",
    "SIGNED_SHEAR_INTERFACES",
    "CONTACT_ACTIVE_SET",
    "SECONDARY_BOLT_BENDING",
    "GROUP_COMPATIBILITY",
    "ANGLE_COLUMN_DIFFERENT_LEG_BASE_MEMBER_INTERFACE",
    "SLICE8_NATIVE_IN_PLANE_PROJECTION_COMPATIBILITY",
)


def connector_context(
    preview: AngleBasePreview, transfer: AngleBaseTransfer, *, attachment: bool = False
) -> FRPAngleContext:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    item = preview.input.connectors[index]
    material = create_locked_ice_material_snapshot()
    shear = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_LT)
    adjusted = adjust_frp_property(shear.kind, shear.value, shear.qualification_status, END_USE)
    binding = (
        "STAGE_4_4_MEMBER_ATTACHMENT" if attachment else "STAGE_4_4_ANGLE_BODY",
        item,
        preview.response_binding,
        transfer.core.request.member_action,
    )
    return FRPAngleContext(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        True,
        material,
        adjusted,
        base_fingerprint(binding),
        base_fingerprint((preview.response_binding, transfer.connector_id)),
    )


def member_response_binding(
    preview: AngleBasePreview, transfer: AngleBaseTransfer
) -> SupportResponseBinding:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    angle = preview.geometry.angles[index]
    native = angle.specification
    group = f"{transfer.connector_id}_MEMBER_GROUP"
    bolts = []
    for b in preview.geometry.member_bolts:
        if b.group_id != group:
            continue
        # Exact point transformation, separate from wrench/reference transport.
        n = quantity_vector(
            rotate(
                angle.frame, subtract(components(b.start), components(angle.heel)), inverse=True
            ),
            Unit.MM,
        )
        f = quantity_vector(
            rotate(angle.frame, subtract(components(b.end), components(angle.heel)), inverse=True),
            Unit.MM,
        )
        bolts.append(PhysicalResponseBolt(b.hardware_id, b.group_id, n, f, b.layers))
    half = PhysicalQuantity(native.geometry.length.to(Unit.IN).magnitude / 2, Unit.IN)
    t = native.geometry.thickness.to(Unit.IN).magnitude
    domain = ResponseContactDomain(
        group,
        PhysicalQuantity(-t / 2, Unit.IN),
        PhysicalQuantity(-half.magnitude, Unit.IN),
        half,
        PhysicalQuantity(-t / 2, Unit.IN),
        PhysicalQuantity(native.geometry.member_leg.to(Unit.IN).magnitude - t / 2, Unit.IN),
        f"COLUMN_LEG_{index + 1}",
    )
    # Complementary normal response only: do not repeat or replace Slice 8's
    # exact in-plane mechanics with projected-Decimal external equilibrium.
    # Source actions are ON the column; C is its outward face normal.
    complete = opposite(transfer.core.request.member_action)
    zero_force = quantity_vector(ZERO, Unit.N)
    zero_moment = quantity_vector(ZERO, Unit.N_MM)
    normal = AngleWrench(
        complete.reference,
        ExactQuantityVector3D(zero_force.x, zero_force.y, complete.force.z),
        ExactQuantityVector3D(complete.moment.x, complete.moment.y, zero_moment.z),
    )
    return SupportResponseBinding(
        base_fingerprint(preview.input.engineering_input()),
        preview.geometry.fingerprint,
        (transfer.core.fingerprint, transfer.in_plane_demand.fingerprint),
        base_fingerprint((preview.response_binding, preview.input.connectors[index])),
        tuple(bolts),
        ((group, normal),),
        (domain,),
        MEMBER_RESPONSE_DOMAIN,
        f"COLUMN_LEG_{index + 1}_OUTER",
        "MEMBER_A_B_C",
    )


@dataclass(frozen=True, slots=True)
class BaseMemberResponseValidation:
    status: str
    reasons: tuple[str, ...]
    binding: SupportResponseBinding
    record: QualifiedSupportResponse | None
    proofs: tuple[ResponseProof, ...]
    shafts: tuple[ShaftDemand, ...]
    fingerprint: str
    proof_scope: str = "EXACT_F_C_M_A_M_B_ONLY_PLUS_UNCHANGED_SLICE8_IN_PLANE_PROOF"


def validate_member_response(
    binding: SupportResponseBinding,
    record: QualifiedSupportResponse | None,
    in_plane: InPlaneWrenchResult,
) -> BaseMemberResponseValidation:
    """New domain policy; never claim Stage 4.3 four-group coverage for this base."""
    if record is None:
        return BaseMemberResponseValidation(
            "SOURCE_REQUIRED",
            ("MEMBER_NORMAL_CONTACT_PRYING_RESPONSE_REQUIRED",),
            binding,
            None,
            (),
            (),
            base_fingerprint(binding),
        )
    reasons: list[str] = []
    if record.binding != binding or binding.support_mode != MEMBER_RESPONSE_DOMAIN:
        reasons.append("MEMBER_RESPONSE_EXACT_DOMAIN_BINDING_MISMATCH")
    if (
        not qualified_source(record.source)
        or not record.issuer.strip()
        or not record.domain.strip()
        or not record.contact_stiffness_boundary_assumptions
        or any(not s.strip() for s in record.contact_stiffness_boundary_assumptions)
    ):
        reasons.append("MEMBER_RESPONSE_PROVENANCE_COMPATIBILITY_REQUIRED")
    if (
        not set(MEMBER_RESPONSE_COVERAGE).issubset(record.coverage)
        or not record.prying_included_in_total
    ):
        reasons.append("MEMBER_RESPONSE_COMPLETE_NORMAL_PRYING_COVERAGE_REQUIRED")
    physical = {b.bolt_id: b for b in binding.physical_bolts}
    prefix = binding.group_targets[0][0].removesuffix("_MEMBER_GROUP")
    projected = {f"{prefix}:{b.bolt_id}": b for b in in_plane.solution.projected_bolts()}
    if in_plane.fingerprint not in binding.native_core_fingerprints:
        reasons.append("NATIVE_IN_PLANE_RESULT_NOT_BOUND")
    actions = {a.bolt_id: a for a in record.actions if a.kind == "BOLT"}
    shafts = {s.bolt_id: s for s in record.shaft_demands}
    if (
        set(actions) != set(physical)
        or set(shafts) != set(physical)
        or len(shafts) != len(record.shaft_demands)
    ):
        reasons.append("EXACT_PHYSICAL_BOLT_ACTION_AND_SHAFT_SET_REQUIRED")
    for action in record.actions:
        domain = next((d for d in binding.contact_domains if d.group_id == action.group_id), None)
        if domain is None:
            reasons.append("MEMBER_ACTION_GROUP_NOT_BOUND")
            continue
        if action.kind == "BOLT":
            p = physical.get(action.bolt_id or "")
            if (
                p is None
                or action.point.z != domain.n
                or action.point.x != p.near.x
                or action.point.y != p.near.y
                or action.layer_id != domain.layer_id
            ):
                reasons.append("BOLT_ACTION_PHYSICAL_POINT_MISMATCH")
        elif action.kind == "CONTACT":
            if (
                action.layer_id != domain.layer_id
                or action.point.z != domain.n
                or not domain.u_min <= action.point.x <= domain.u_max
                or not domain.v_min <= action.point.y <= domain.v_max
            ):
                reasons.append("MEMBER_CONTACT_OUTSIDE_PHYSICAL_OVERLAP")
        if action.force.x.canonical_magnitude != 0 or action.force.y.canonical_magnitude != 0:
            reasons.append("NORMAL_SOURCE_CANNOT_REPLACE_IN_PLANE_SLICE8_ACTION")
        if action.moment.z.canonical_magnitude != 0:
            reasons.append("NORMAL_SOURCE_CANNOT_REPLACE_IN_PLANE_FREE_MOMENT")
    for ident, shaft in shafts.items():
        a = actions.get(ident)
        p = physical.get(ident)
        if a is None or p is None:
            continue
        if (
            set(shaft.layer_ids) != set(p.layer_ids)
            or len(set(shaft.layer_ids)) != len(shaft.layer_ids)
            or not shaft.section_id.strip()
            or shaft.applicability != "SINGLE_PLANE_8_2_8_3"
            or not shaft.secondary_bending_covered
        ):
            reasons.append("PHYSICAL_SINGLE_INTERFACE_SHAFT_COVERAGE_REQUIRED")
        native = projected.get(ident)
        if native is None or (shaft.force_u, shaft.force_v) != (
            replace(native.total_force.u, magnitude=native.total_force.u.magnitude.copy_negate()),
            replace(native.total_force.v, magnitude=native.total_force.v.magnitude.copy_negate()),
        ):
            reasons.append("SHAFT_SHEAR_MUST_EQUAL_OPPOSITE_NATIVE_SLICE8_PROJECTION")
        if shaft.tensile_demand != a.force.z or shaft.tensile_demand.canonical_magnitude < 0:
            reasons.append("SHAFT_DEMAND_DOES_NOT_MATCH_EXTERNAL_BOLT_ACTION")
    proofs = tuple(
        prove_support_response(
            target,
            tuple(a for a in record.actions if a.group_id == group),
            authorized_couple_ids=record.authorized_couple_ids,
        )
        for group, target in binding.group_targets
    )
    reasons.extend(reason for proof in proofs for reason in proof.reasons)
    unique = tuple(dict.fromkeys(reasons))
    return BaseMemberResponseValidation(
        "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE" if unique else "VALID_QUALIFIED_RESPONSE",
        unique,
        binding,
        None if unique else record,
        proofs,
        () if unique else record.shaft_demands,
        base_fingerprint((binding, record, unique, proofs)),
    )


def find_member_response(
    preview: AngleBasePreview, transfer: AngleBaseTransfer, sources: AngleBaseSourceRegistry
) -> BaseMemberResponseValidation:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    reference = preview.input.connectors[index].normal_response_source_reference
    return validate_member_response(
        member_response_binding(preview, transfer),
        next((r for r in sources.member_responses if r.reference == reference), None),
        transfer.in_plane_demand,
    )


def fastener_binding(preview: AngleBasePreview, transfer: AngleBaseTransfer) -> str:
    index = next(
        i for i, a in enumerate(preview.geometry.angles) if a.connector_id == transfer.connector_id
    )
    return base_fingerprint(
        (
            preview.input.connectors[index],
            tuple(
                b
                for b in preview.geometry.member_bolts
                if b.group_id == f"{transfer.connector_id}_MEMBER_GROUP"
            ),
        )
    )


def column_zone_binding(preview: AngleBasePreview) -> str:
    return base_fingerprint(
        (
            preview.response_binding,
            preview.response.response,
            tuple(t.core.fingerprint for t in preview.transfers),
        )
    )
