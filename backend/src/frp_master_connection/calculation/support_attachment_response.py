"""Exact, source-bound support-response validation; deliberately no distribution solver.

The ledger contains external actions ON the receiving support once. Internal
shaft/layer records are separate demands, never additional equilibrium loads.
The server registry, not a client Boolean or scalar capacity certificate, is
the trust boundary. Synthetic balanced fixtures do not grant qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    angle_fingerprint,
    components,
    quantity_vector,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.domain.material_architecture import (
    EngineeringPropertySource,
    PropertySourceConfirmation,
)

METHOD = "QUALIFIED_FRP_SUPPORT_ATTACHMENT_RESPONSE_RC1"
ZERO: Rational3 = (Fraction(0), Fraction(0), Fraction(0))
REQUIRED_COVERAGE = (
    "TOTAL_BOLT_TENSION_INCLUDING_PRYING",
    "SIGNED_SHEAR_INTERFACES",
    "CONTACT_ACTIVE_SET",
    "SECONDARY_BOLT_BENDING",
    "GROUP_COMPATIBILITY",
    "COMBINED_FOUR_GROUP_RESPONSE",
)


def _cross(a: Rational3, b: Rational3) -> Rational3:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def _add(a: Rational3, b: Rational3) -> Rational3:
    return cast(Rational3, tuple(x + y for x, y in zip(a, b, strict=True)))


def _subtract(a: Rational3, b: Rational3) -> Rational3:
    return cast(Rational3, tuple(x - y for x, y in zip(a, b, strict=True)))


@dataclass(frozen=True, slots=True)
class SupportResponseAction:
    action_id: str
    group_id: str
    kind: str  # BOLT, CONTACT or explicitly authorized COUPLE
    point: ExactQuantityVector3D
    force: ExactQuantityVector3D
    moment: ExactQuantityVector3D
    bolt_id: str | None = None
    layer_id: str | None = None

    def __post_init__(self) -> None:
        AngleWrench(self.point, self.force, self.moment)


@dataclass(frozen=True, slots=True)
class ShaftDemand:
    """A checked physical section/interface, not another external ledger force."""

    bolt_id: str
    section_id: str
    layer_ids: tuple[str, ...]
    force_u: PhysicalQuantity
    force_v: PhysicalQuantity
    tensile_demand: PhysicalQuantity
    applicability: str  # SINGLE_PLANE_8_2_8_3, or explicit source-only long-shank domain
    secondary_bending_covered: bool


@dataclass(frozen=True, slots=True)
class ReceivingLayerForce:
    """Source-declared material participation, separate from shaft-section cuts.

    An inactive penetrated wall is explicitly present with zero action. These
    records never become additional external support actions. Their exact sum
    must recover the physical bolt's externally declared resultant; distribution
    and local bending remain bound to the qualified source, not generated here.
    """

    bolt_id: str
    layer_id: str
    force: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class ResponseProof:
    passed: bool
    reasons: tuple[str, ...]
    reconstructed: AngleWrench
    residual_force: ExactQuantityVector3D
    residual_moment: ExactQuantityVector3D


def prove_support_response(
    target: AngleWrench,
    actions: tuple[SupportResponseAction, ...],
    *,
    authorized_couple_ids: tuple[str, ...] = (),
) -> ResponseProof:
    """Exact six-component reconstruction and unilateral sign checks, not trust."""
    reasons: list[str] = []
    force = moment = ZERO
    ids = tuple(a.action_id for a in actions)
    bolts = tuple(a.bolt_id for a in actions if a.kind == "BOLT")
    if len(ids) != len(set(ids)) or len(bolts) != len(set(bolts)):
        reasons.append("DUPLICATE_EXTERNAL_ACTION_OR_BOLT")
    for action in actions:
        f, m = components(action.force), components(action.moment)
        if action.kind == "BOLT":
            if action.bolt_id is None or f[2] < 0:
                reasons.append("INVALID_BOLT_ID_OR_NEGATIVE_TENSION")
        elif action.kind == "CONTACT":
            if action.bolt_id is not None or f[0] != 0 or f[1] != 0 or f[2] > 0:
                reasons.append("INVALID_COMPRESSION_CONTACT")
        elif action.kind == "COUPLE":
            if (
                f != ZERO
                or action.bolt_id is not None
                or action.action_id not in authorized_couple_ids
            ):
                reasons.append("UNAUTHORIZED_EXTERNAL_COUPLE")
        else:
            reasons.append("UNKNOWN_RESPONSE_ACTION_KIND")
        if m != ZERO and action.action_id not in authorized_couple_ids:
            reasons.append("UNAUTHORIZED_BALANCING_COUPLE")
        force = _add(force, f)
        moment = _add(
            moment,
            _add(_cross(_subtract(components(action.point), components(target.reference)), f), m),
        )
    rf, rm = (
        _subtract(force, components(target.force)),
        _subtract(moment, components(target.moment)),
    )
    if rf != ZERO or rm != ZERO:
        reasons.append("EXACT_RESPONSE_EQUILIBRIUM_NOT_PROVEN")
    return ResponseProof(
        not reasons,
        tuple(dict.fromkeys(reasons)),
        AngleWrench(
            target.reference, quantity_vector(force, Unit.N), quantity_vector(moment, Unit.N_MM)
        ),
        quantity_vector(rf, Unit.N),
        quantity_vector(rm, Unit.N_MM),
    )


@dataclass(frozen=True, slots=True)
class PhysicalResponseBolt:
    bolt_id: str
    group_id: str
    near: ExactQuantityVector3D
    far: ExactQuantityVector3D
    layer_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResponseContactDomain:
    group_id: str
    n: PhysicalQuantity
    u_min: PhysicalQuantity
    u_max: PhysicalQuantity
    v_min: PhysicalQuantity
    v_max: PhysicalQuantity
    layer_id: str


@dataclass(frozen=True, slots=True)
class SupportResponseBinding:
    input_fingerprint: str
    geometry_fingerprint: str
    native_core_fingerprints: tuple[str, ...]
    material_and_fastener_fingerprint: str
    physical_bolts: tuple[PhysicalResponseBolt, ...]
    group_targets: tuple[tuple[str, AngleWrench], ...]
    contact_domains: tuple[ResponseContactDomain, ...]
    support_mode: str
    selected_face: str
    frame_id: str = "SUPPORT_ATTACHMENT_U_V_N_EQUALS_BEAM_V_T_L"


@dataclass(frozen=True, slots=True)
class QualifiedSupportResponse:
    reference: str
    source: EngineeringPropertySource
    issuer: str
    binding: SupportResponseBinding
    actions: tuple[SupportResponseAction, ...]
    shaft_demands: tuple[ShaftDemand, ...]
    contact_stiffness_boundary_assumptions: tuple[str, ...]
    coverage: tuple[str, ...]
    domain: str
    prying_included_in_total: bool
    authorized_couple_ids: tuple[str, ...] = ()
    native_external_precision_and_proof: tuple[str, ...] = ()
    receiving_layer_forces: tuple[ReceivingLayerForce, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedSupportResponse:
    status: str
    reasons: tuple[str, ...]
    group_proofs: tuple[tuple[str, ResponseProof], ...]
    response: QualifiedSupportResponse | None
    fingerprint: str
    method: str = METHOD
    extra_prying_factor: None = None


def qualified_source(source: EngineeringPropertySource) -> bool:
    return bool(
        source.confirmation
        in {PropertySourceConfirmation.TEST_QUALIFIED, PropertySourceConfirmation.ENGINEER_APPROVED}
        and source.approval_authority_id
        and source.qualification_record_ids
        and source.controlling_artifact_sha256
        and source.provenance_reference_ids
    )


def validate_support_response(
    expected: SupportResponseBinding,
    record: QualifiedSupportResponse | None,
) -> ValidatedSupportResponse:
    reasons: list[str] = []
    proofs: list[tuple[str, ResponseProof]] = []
    if record is None:
        return ValidatedSupportResponse(
            "SOURCE_REQUIRED",
            ("COMPLETE_SUPPORT_RESPONSE_UNAVAILABLE",),
            (),
            None,
            angle_fingerprint((METHOD, expected, None)),
        )
    if record.binding != expected:
        reasons.append("SOURCE_NOT_APPLICABLE_EXACT_ASSEMBLY_LOAD_BINDING_MISMATCH")
    if not qualified_source(record.source) or not record.issuer.strip():
        reasons.append("SOURCE_REQUIRED_QUALIFICATION_PROVENANCE")
    if not record.contact_stiffness_boundary_assumptions or not record.domain.strip():
        reasons.append("SOURCE_REQUIRED_CONTACT_STIFFNESS_DOMAIN")
    if not set(REQUIRED_COVERAGE).issubset(record.coverage) or not record.prying_included_in_total:
        reasons.append("SOURCE_REQUIRED_COMPLETE_RESPONSE_COVERAGE")
    bolts = {b.bolt_id: b for b in expected.physical_bolts}
    groups = {group for group, _ in expected.group_targets}
    external_bolts = tuple(a.bolt_id for a in record.actions if a.kind == "BOLT")
    if set(external_bolts) != set(bolts) or len(external_bolts) != len(bolts):
        reasons.append("INVALID_RESPONSE_PHYSICAL_BOLT_COVERAGE")
    if any(a.group_id not in groups for a in record.actions):
        reasons.append("INVALID_RESPONSE_UNKNOWN_GROUP")
    for action in record.actions:
        point = components(action.point)
        if action.kind == "BOLT":
            bolt = bolts.get(action.bolt_id or "")
            if bolt is None:
                reasons.append("INVALID_RESPONSE_UNKNOWN_BOLT")
            else:
                near, far = components(bolt.near), components(bolt.far)
                if (
                    action.group_id != bolt.group_id
                    or point[:2] != near[:2]
                    or not min(near[2], far[2]) <= point[2] <= max(near[2], far[2])
                    or action.layer_id not in bolt.layer_ids
                ):
                    reasons.append("INVALID_RESPONSE_BOLT_ACTION_LOCATION_OR_LAYER")
        elif action.kind == "CONTACT":
            if not any(
                d.group_id == action.group_id
                and d.layer_id == action.layer_id
                and point[2] == Fraction(d.n.canonical_magnitude)
                and Fraction(d.u_min.canonical_magnitude)
                <= point[0]
                <= Fraction(d.u_max.canonical_magnitude)
                and Fraction(d.v_min.canonical_magnitude)
                <= point[1]
                <= Fraction(d.v_max.canonical_magnitude)
                for d in expected.contact_domains
            ):
                reasons.append("INVALID_RESPONSE_CONTACT_OUTSIDE_PHYSICAL_DOMAIN")
    keys = tuple((d.bolt_id, d.section_id) for d in record.shaft_demands)
    if len(keys) != len(set(keys)) or {d.bolt_id for d in record.shaft_demands} != set(bolts):
        reasons.append("INVALID_RESPONSE_SHAFT_SECTION_COVERAGE")
    for demand in record.shaft_demands:
        if (
            demand.bolt_id not in bolts
            or not demand.section_id.strip()
            or not demand.layer_ids
            or not set(demand.layer_ids).issubset(bolts[demand.bolt_id].layer_ids)
            or any(
                q.dimension is not Dimension.FORCE
                for q in (demand.force_u, demand.force_v, demand.tensile_demand)
            )
            or demand.tensile_demand.canonical_magnitude < 0
        ):
            reasons.append("INVALID_RESPONSE_SHAFT_DEMAND_OR_LAYER")
        if not demand.secondary_bending_covered:
            reasons.append("SOURCE_REQUIRED_SECONDARY_BOLT_BENDING")
    # A shaft cut is not a receiving-wall reaction. Never apply every shaft
    # section's force to every penetrated layer or infer equal wall participation.
    long_path = expected.support_mode in {"HOLLOW_SQUARE", "SOLID_SQUARE"}
    if long_path and not record.native_external_precision_and_proof:
        reasons.append("SOURCE_REQUIRED_LONG_PATH_INTERNAL_RESPONSE_PROVENANCE")
    layer_keys = tuple((d.bolt_id, d.layer_id) for d in record.receiving_layer_forces)
    required_layers = {(b.bolt_id, layer) for b in bolts.values() for layer in b.layer_ids}
    if (long_path or layer_keys) and (
        len(layer_keys) != len(set(layer_keys)) or set(layer_keys) != required_layers
    ):
        reasons.append("SOURCE_REQUIRED_EXPLICIT_RECEIVING_LAYER_PARTICIPATION")
    if any(
        any(q.dimension is not Dimension.FORCE for q in (d.force.x, d.force.y, d.force.z))
        or d.force.z.canonical_magnitude < 0
        for d in record.receiving_layer_forces
    ):
        reasons.append("INVALID_RECEIVING_LAYER_FORCE")
    for bolt_id in bolts:
        external_action = next(
            (a for a in record.actions if a.kind == "BOLT" and a.bolt_id == bolt_id), None
        )
        if external_action is None:
            continue
        layers = tuple(d for d in record.receiving_layer_forces if d.bolt_id == bolt_id)
        if layers:
            summed = ZERO
            for layer in layers:
                summed = _add(summed, components(layer.force))
            if summed != components(external_action.force):
                reasons.append("EXACT_RECEIVING_LAYER_FORCE_RECONSTRUCTION_FAILED")
        if not long_path:
            demands = tuple(d for d in record.shaft_demands if d.bolt_id == bolt_id)
            if len(demands) != 1 or any(
                (d.force_u, d.force_v, d.tensile_demand)
                != (external_action.force.x, external_action.force.y, external_action.force.z)
                for d in demands
            ):
                reasons.append("EXACT_SINGLE_LAP_SECTION_RESPONSE_MISMATCH")
    for group, target in expected.group_targets:
        proof = prove_support_response(
            target,
            tuple(a for a in record.actions if a.group_id == group),
            authorized_couple_ids=record.authorized_couple_ids,
        )
        proofs.append((group, proof))
        reasons.extend(proof.reasons)
    status = (
        "VALID_QUALIFIED_RESPONSE"
        if not reasons
        else "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE"
    )
    return ValidatedSupportResponse(
        status,
        tuple(dict.fromkeys(reasons)),
        tuple(proofs),
        record,
        angle_fingerprint((METHOD, expected, record, status, tuple(reasons))),
    )
