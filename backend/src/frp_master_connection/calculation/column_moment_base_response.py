"""Qualified multi-angle response authority, never a base/contact/stiffness solver."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import cast

from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    BaseBranchDomain,
    BaseResponseBinding,
    ColumnPressurePatch,
    QualifiedBaseBranch,
    QualifiedBaseResponse,
    QualifiedFootBreakdown,
    _pressure_contact,
    add,
    base_fingerprint,
    is_zero,
    subtract,
    sum_wrenches,
    transform_wrench,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    quantity_vector,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import qualified_source
from frp_master_connection.domain.material_architecture import EngineeringPropertySource

METHOD = "QUALIFIED_WI_RHS_SRS_MULTI_ANGLE_BASE_RESPONSE_RC1"
REQUIRED_COVERAGE = (
    "EXACT_PROFILE_ACTIVE_FACES_AND_SHARED_SHANK_TOPOLOGY",
    "COMPLETE_SIX_COMPONENT_BRANCH_ACTIONS",
    "COMPATIBILITY_STIFFNESS_LOAD_PATH",
    "DIRECT_COLUMN_CONTACT_ACTIVE_SET",
    "CONNECTOR_FOOT_CONTACT_AND_ANCHOR_NET_ACTION",
    "MEMBER_INTERFACE_NORMAL_AND_PRYING_RESPONSE",
    "COUPLED_SHAFT_SECTION_EQUILIBRIUM",
    "EXPLICIT_RECEIVING_REGION_PARTICIPATION",
    "LONG_SHANK_BENDING_AND_WALL_DEFORMATION",
    "EXACT_GEOMETRY_MATERIAL_FASTENER_FIXTURE_REFERENCE",
    "SIGNED_FIVE_ACTION_DOMAIN",
)


@dataclass(frozen=True, slots=True)
class BoltLayerDomain:
    layer_id: str
    point: ExactQuantityVector3D
    connector_id: str | None
    material_basis_global: tuple[Rational3, Rational3, Rational3]
    material_thickness: PhysicalQuantity
    local_region_scope: str


@dataclass(frozen=True, slots=True)
class CoupledBoltDomain:
    bolt_id: str
    owner_connector: str
    axis_global: Rational3
    plane_u_global: Rational3
    plane_v_global: Rational3
    layers: tuple[BoltLayerDomain, ...]
    physical_fingerprint: str


@dataclass(frozen=True, slots=True)
class ColumnBaseResponseBinding:
    geometry_fingerprint: str
    engineering_input_fingerprint: str
    material_fastener_fingerprint: str
    required_total: AngleWrench
    branches: tuple[BaseBranchDomain, ...]
    column_contact_rectangles: tuple[tuple[Fraction, Fraction, Fraction, Fraction], ...]
    physical_bolts: tuple[CoupledBoltDomain, ...]
    profile_family: str
    layout: str
    method: str = METHOD


@dataclass(frozen=True, slots=True)
class LayerResponse:
    """Bolt-on-material action; internal ledger, not another foundation action."""

    layer_id: str
    action: AngleWrench
    attachment_tensile_demand: PhysicalQuantity | None = None


@dataclass(frozen=True, slots=True)
class ShaftSectionResponse:
    section_id: str
    after_layer_id: str
    force_on_upstream: ExactQuantityVector3D
    tensile_demand: PhysicalQuantity
    normal_response_basis: str
    native_capacity_applicability: str
    secondary_bending_covered: bool


@dataclass(frozen=True, slots=True)
class CoupledBoltResponse:
    bolt_id: str
    layers: tuple[LayerResponse, ...]
    sections: tuple[ShaftSectionResponse, ...]
    response_model: str
    compatibility_basis: str
    authorized_layer_couple_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QualifiedColumnBaseResponse:
    reference: str
    source: EngineeringPropertySource
    issuer: str
    binding: ColumnBaseResponseBinding
    branches: tuple[QualifiedBaseBranch, ...]
    column_on_foundation_contact: AngleWrench
    pressure_patches: tuple[ColumnPressurePatch, ...]
    contact_inactive_certificate: str | None
    compatibility_stiffness_contact_basis: str
    coverage: tuple[str, ...]
    signed_load_domain: str
    bolts: tuple[CoupledBoltResponse, ...]
    method: str = METHOD
    foot_breakdowns: tuple[QualifiedFootBreakdown, ...] = ()


@dataclass(frozen=True, slots=True)
class CoupledBoltProof:
    bolt_id: str
    passed: bool
    reasons: tuple[str, ...]
    external_force_sum: ExactQuantityVector3D
    ordered_section_forces: tuple[ExactQuantityVector3D, ...]


@dataclass(frozen=True, slots=True)
class ColumnBaseResponseValidation:
    status: str
    reasons: tuple[str, ...]
    response: QualifiedColumnBaseResponse | None
    reconstructed_total: AngleWrench | None
    residual_force: ExactQuantityVector3D | None
    residual_moment: ExactQuantityVector3D | None
    exact_equilibrium: bool | None
    qualified: bool
    coupled_bolt_proofs: tuple[CoupledBoltProof, ...]
    fingerprint: str


def _coupled_proof(domain: CoupledBoltDomain, response: CoupledBoltResponse) -> CoupledBoltProof:
    reasons = []
    layer_ids = tuple(layer.layer_id for layer in domain.layers)
    supplied = tuple(layer.layer_id for layer in response.layers)
    if response.bolt_id != domain.bolt_id or supplied != layer_ids:
        reasons.append("EXACT_ORDERED_PHYSICAL_LAYER_IDENTITIES_REQUIRED")
    if (
        response.response_model != "QUALIFIED_COUPLED_EXPLICIT_LAYER_RESPONSE"
        or not response.compatibility_basis.strip()
    ):
        reasons.append("COUPLED_RESPONSE_COMPATIBILITY_SOURCE_REQUIRED")
    if not set(response.authorized_layer_couple_ids).issubset(layer_ids):
        reasons.append("UNAUTHORIZED_LAYER_COUPLE_ID")
    indexed = {layer.layer_id: layer for layer in response.layers}
    section_ids = tuple(section.section_id for section in response.sections)
    if (
        len(section_ids) != len(set(section_ids))
        or any(not s for s in section_ids)
        or tuple(s.after_layer_id for s in response.sections) != layer_ids[:-1]
    ):
        reasons.append("EXACT_SHAFT_SECTION_COVERAGE_REQUIRED")
    cumulative = ZERO
    cuts = []
    for index, layer in enumerate(domain.layers):
        actual = indexed.get(layer.layer_id)
        if actual is None:
            continue
        if actual.action.reference != layer.point:
            reasons.append("LAYER_FORCE_PHYSICAL_REFERENCE_MISMATCH")
        if layer.connector_id is not None and (
            actual.attachment_tensile_demand is None
            or actual.attachment_tensile_demand.dimension is not Dimension.FORCE
            or actual.attachment_tensile_demand.canonical_magnitude < 0
        ):
            reasons.append("SOURCE_REQUIRED_ACTUAL_TERMINAL_ATTACHMENT_TENSION")
        if (
            components(actual.action.moment) != ZERO
            and layer.layer_id not in response.authorized_layer_couple_ids
        ):
            reasons.append("UNAUTHORIZED_BALANCING_LAYER_COUPLE")
        cumulative = add(cumulative, components(actual.action.force))
        if index < len(domain.layers) - 1:
            cuts.append(quantity_vector(cumulative, Unit.N))
            section = next(
                (s for s in response.sections if s.after_layer_id == layer.layer_id), None
            )
            if section is not None:
                if components(section.force_on_upstream) != cumulative:
                    reasons.append("EXACT_ORDERED_SHAFT_SECTION_FORCE_MISMATCH")
                if (
                    section.tensile_demand.dimension is not Dimension.FORCE
                    or section.tensile_demand.canonical_magnitude < 0
                ):
                    reasons.append("INVALID_SOURCE_TOTAL_BOLT_TENSION")
                if (
                    not section.normal_response_basis.strip()
                    or not section.secondary_bending_covered
                ):
                    reasons.append("SOURCE_REQUIRED_NORMAL_PRYING_SECONDARY_BENDING_COVERAGE")
                if not section.native_capacity_applicability.strip():
                    reasons.append("SOURCE_REQUIRED_SHAFT_CAPACITY_APPLICABILITY")
    if cumulative != ZERO:
        reasons.append("EXACT_INTERNAL_LAYER_FORCE_CLOSURE_FAILED")
    # Moments carried between material layers need the source's bending/contact
    # solution. Their exact whole-shank closure remains independently checked.
    total = sum_wrenches(tuple(layer.action for layer in response.layers), domain.layers[0].point)
    if components(total.moment) != ZERO:
        reasons.append("EXACT_INTERNAL_LAYER_MOMENT_CLOSURE_FAILED")
    unique = tuple(dict.fromkeys(reasons))
    return CoupledBoltProof(
        domain.bolt_id, not unique, unique, quantity_vector(cumulative, Unit.N), tuple(cuts)
    )


def validate_column_base_response(
    binding: ColumnBaseResponseBinding, record: QualifiedColumnBaseResponse | None
) -> ColumnBaseResponseValidation:
    if record is None:
        return ColumnBaseResponseValidation(
            "SOURCE_REQUIRED",
            ("COMPLETE_MULTI_ANGLE_BASE_RESPONSE_SOURCE_REQUIRED",),
            None,
            None,
            None,
            None,
            None,
            False,
            (),
            base_fingerprint((METHOD, binding, None)),
        )
    # These are keyed source records, not a physical sequence. Canonicalize their
    # enumeration only; ordered material layers/shaft cuts must remain untouched.
    record = replace(
        record,
        branches=tuple(sorted(record.branches, key=lambda b: b.domain.connector_id)),
        bolts=tuple(sorted(record.bolts, key=lambda b: b.bolt_id)),
        pressure_patches=tuple(sorted(record.pressure_patches, key=lambda p: p.patch_id)),
        foot_breakdowns=tuple(sorted(record.foot_breakdowns, key=lambda f: f.domain.connector_id)),
    )
    reasons: list[str] = []
    if record.binding != binding or record.method != METHOD or binding.method != METHOD:
        reasons.append("BASE_RESPONSE_BINDING_OR_DOMAIN_MISMATCH")
    if (
        not qualified_source(record.source)
        or not record.reference.strip()
        or not record.issuer.strip()
    ):
        reasons.append("QUALIFIED_BASE_RESPONSE_PROVENANCE_REQUIRED")
    if (
        not record.compatibility_stiffness_contact_basis.strip()
        or not record.signed_load_domain.strip()
        or not set(REQUIRED_COVERAGE).issubset(record.coverage)
    ):
        reasons.append("BASE_RESPONSE_COMPATIBILITY_CONTACT_NORMAL_COVERAGE_REQUIRED")
    active = {
        "TWO_X": {"X_POS", "X_NEG"},
        "TWO_Y": {"Y_POS", "Y_NEG"},
        "FOUR_XY": {"X_POS", "X_NEG", "Y_POS", "Y_NEG"},
    }.get(binding.layout, set())
    expected = {branch.connector_id: branch for branch in binding.branches}
    ids = [b.domain.connector_id for b in record.branches]
    if (
        binding.profile_family not in {"WI", "RHS", "SRS"}
        or set(expected) != active
        or len(ids) != len(active)
        or len(set(ids)) != len(ids)
        or set(ids) != active
    ):
        reasons.append("EXACT_ACTIVE_TWO_OR_FOUR_BRANCH_IDENTITIES_REQUIRED")
    values = []
    for branch in record.branches:
        if (
            branch.domain != expected.get(branch.domain.connector_id)
            or branch.member_action.reference != branch.domain.local_member_reference
        ):
            reasons.append("MEMBER_BRANCH_FRAME_REGION_OR_REFERENCE_MISMATCH")
        if is_zero(branch.member_action) != bool(branch.inactive_certificate):
            reasons.append("EXPLICIT_CORRECT_INACTIVE_BRANCH_CERTIFICATE_REQUIRED")
        values.append(
            transform_wrench(
                branch.member_action,
                branch.domain.frame,
                branch.domain.global_heel,
                binding.required_total.reference,
            )
        )
    if any(f.domain.connector_id not in active for f in record.foot_breakdowns):
        reasons.append("FOOT_BREAKDOWN_UNKNOWN_CONNECTOR")
    contact = record.column_on_foundation_contact
    if contact.reference != binding.required_total.reference:
        reasons.append("DIRECT_CONTACT_REPORT_REFERENCE_MISMATCH")
    if is_zero(contact) != (
        bool(record.contact_inactive_certificate) and not record.pressure_patches
    ):
        reasons.append("EXPLICIT_CORRECT_DIRECT_CONTACT_ACTIVE_STATE_REQUIRED")
    # Structural leaf reuse only: the frozen helper integrates disjoint rectangles,
    # not a load allocation or old two-leg source-domain validator.
    pressure_reasons: list[str] = []
    pressure = _pressure_contact(
        cast(BaseResponseBinding, binding), cast(QualifiedBaseResponse, record), pressure_reasons
    )
    reasons.extend(
        "CONTACT_PRESSURE_OUTSIDE_REAL_PROFILE_FOOTPRINT"
        if r == "CONTACT_PRESSURE_OUTSIDE_REAL_L_FOOTPRINT"
        else r
        for r in pressure_reasons
    )
    if components(pressure.force) != components(contact.force) or components(
        pressure.moment
    ) != components(contact.moment):
        reasons.append("DIRECT_CONTACT_RESULTANT_NOT_PROVEN_BY_COMPRESSION_PATCHES")
    bolt_ids = [r.bolt_id for r in record.bolts]
    bolt_domains = {b.bolt_id: b for b in binding.physical_bolts}
    if len(set(bolt_ids)) != len(bolt_ids) or set(bolt_ids) != set(bolt_domains):
        reasons.append("EXACT_SHARED_PHYSICAL_BOLT_SET_REQUIRED")
    proofs = []
    for supplied in record.bolts:
        domain = bolt_domains.get(supplied.bolt_id)
        if domain is not None:
            proof = _coupled_proof(domain, supplied)
            proofs.append(proof)
            reasons.extend(proof.reasons)
    # The aggregate bolt-on-angle actions must independently recover each complete
    # branch wrench. Shaft sections/layer reactions are not extra external loads.
    for branch in record.branches:
        actions: list[AngleWrench] = []
        for bolt in record.bolts:
            domain = bolt_domains.get(bolt.bolt_id)
            if domain is None:
                continue
            ids_on_branch = {
                layer.layer_id
                for layer in domain.layers
                if layer.connector_id == branch.domain.connector_id
            }
            actions.extend(layer.action for layer in bolt.layers if layer.layer_id in ids_on_branch)
        actual = sum_wrenches(tuple(actions), binding.required_total.reference)
        target = transform_wrench(
            branch.member_action,
            branch.domain.frame,
            branch.domain.global_heel,
            binding.required_total.reference,
        )
        if actual != target:
            reasons.append(
                "EXACT_BOLT_ON_CONNECTOR_COMPLETE_WRENCH_MISMATCH:" + branch.domain.connector_id
            )
    reconstructed = sum_wrenches((*values, contact), binding.required_total.reference)
    rf = subtract(components(reconstructed.force), components(binding.required_total.force))
    rm = subtract(components(reconstructed.moment), components(binding.required_total.moment))
    equilibrium = rf == ZERO and rm == ZERO
    if not equilibrium:
        reasons.append("EXACT_BASE_RESPONSE_EQUILIBRIUM_NOT_PROVEN")
    unique = tuple(dict.fromkeys(reasons))
    return ColumnBaseResponseValidation(
        "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE" if unique else "VALID_QUALIFIED_RESPONSE",
        unique,
        None if unique else record,
        reconstructed,
        quantity_vector(rf, Unit.N),
        quantity_vector(rm, Unit.N_MM),
        equilibrium,
        not unique,
        tuple(proofs),
        base_fingerprint((METHOD, binding, record, unique, tuple(proofs))),
    )
