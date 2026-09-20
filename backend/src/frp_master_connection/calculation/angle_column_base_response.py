"""Exact two-leg base transport and qualified-response validation, never a solver."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from typing import cast

from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    AngleWrench,
    Rational3,
    angle_fingerprint,
    components,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.fingerprint import _canonicalize
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import (
    ResponseProof,
    SupportResponseAction,
    prove_support_response,
    qualified_source,
)
from frp_master_connection.domain.material_architecture import EngineeringPropertySource

METHOD = "QUALIFIED_ANGLE_COLUMN_TWO_LEG_BASE_RESPONSE_RC1"
ZERO: Rational3 = (Fraction(0), Fraction(0), Fraction(0))
REQUIRED_COVERAGE = (
    "TWO_DIFFERENT_EXTERIOR_COLUMN_LEGS",
    "COMPLETE_SIX_COMPONENT_BRANCH_ACTIONS",
    "COMPATIBILITY_STIFFNESS_LOAD_PATH",
    "DIRECT_COLUMN_CONTACT_ACTIVE_SET",
    "CONNECTOR_FOOT_CONTACT_AND_ANCHOR_NET_ACTION",
    "MEMBER_INTERFACE_NORMAL_AND_PRYING_RESPONSE",
    "EXACT_GEOMETRY_MATERIAL_FASTENER_FIXTURE_REFERENCE",
    "SIGNED_FIVE_ACTION_DOMAIN",
)


def base_fingerprint(value: object) -> str:
    """Extend canonical metadata for rational proof records, not numeric re-projection."""

    def canonical(item: object) -> object:
        if isinstance(item, Fraction):
            return {"numerator": str(item.numerator), "denominator": str(item.denominator)}
        if isinstance(item, PhysicalQuantity):
            return _canonicalize(item)
        if is_dataclass(item) and not isinstance(item, type):
            return {f.name: canonical(getattr(item, f.name)) for f in fields(item)}
        if isinstance(item, (tuple, list)):
            return [canonical(v) for v in item]
        if isinstance(item, dict):
            return {str(k): canonical(v) for k, v in item.items()}
        return _canonicalize(item)

    return angle_fingerprint(canonical(value))


def add(a: Rational3, b: Rational3) -> Rational3:
    return cast(Rational3, tuple(x + y for x, y in zip(a, b, strict=True)))


def subtract(a: Rational3, b: Rational3) -> Rational3:
    return cast(Rational3, tuple(x - y for x, y in zip(a, b, strict=True)))


def cross(a: Rational3, b: Rational3) -> Rational3:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def rotate(frame: AngleConnectorFrame, value: Rational3, *, inverse: bool = False) -> Rational3:
    axes = (frame.a, frame.b, frame.c)
    return cast(
        Rational3,
        tuple(
            sum(Fraction(axes[i][j] if inverse else axes[j][i]) * value[j] for j in range(3))
            for i in range(3)
        ),
    )


def transform_wrench(
    wrench: AngleWrench,
    frame: AngleConnectorFrame,
    origin: ExactQuantityVector3D,
    report: ExactQuantityVector3D,
) -> AngleWrench:
    """Proper global transport of a local member/core result, including every moment."""
    force = rotate(frame, components(wrench.force))
    reference = add(components(origin), rotate(frame, components(wrench.reference)))
    moment = add(
        rotate(frame, components(wrench.moment)),
        cross(subtract(reference, components(report)), force),
    )
    return AngleWrench(report, quantity_vector(force, Unit.N), quantity_vector(moment, Unit.N_MM))


def global_to_local_wrench(
    wrench: AngleWrench,
    frame: AngleConnectorFrame,
    origin: ExactQuantityVector3D,
    local_reference: ExactQuantityVector3D,
) -> AngleWrench:
    global_reference = add(components(origin), rotate(frame, components(local_reference)))
    at_point = shift_angle_wrench(wrench, quantity_vector(global_reference, Unit.MM))
    return AngleWrench(
        local_reference,
        quantity_vector(rotate(frame, components(at_point.force), inverse=True), Unit.N),
        quantity_vector(rotate(frame, components(at_point.moment), inverse=True), Unit.N_MM),
    )


def opposite(wrench: AngleWrench) -> AngleWrench:
    return AngleWrench(
        wrench.reference,
        quantity_vector(subtract(ZERO, components(wrench.force)), Unit.N),
        quantity_vector(subtract(ZERO, components(wrench.moment)), Unit.N_MM),
    )


def sum_wrenches(
    wrenches: tuple[AngleWrench, ...], reference: ExactQuantityVector3D
) -> AngleWrench:
    force = moment = ZERO
    for value in wrenches:
        moved = shift_angle_wrench(value, reference)
        force = add(force, components(moved.force))
        moment = add(moment, components(moved.moment))
    return AngleWrench(
        reference, quantity_vector(force, Unit.N), quantity_vector(moment, Unit.N_MM)
    )


def is_zero(wrench: AngleWrench) -> bool:
    return components(wrench.force) == ZERO and components(wrench.moment) == ZERO


@dataclass(frozen=True, slots=True)
class BaseBranchDomain:
    connector_id: str
    column_leg: str
    frame: AngleConnectorFrame
    global_heel: ExactQuantityVector3D
    local_member_reference: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class BaseResponseBinding:
    geometry_fingerprint: str
    engineering_input_fingerprint: str
    material_fastener_fingerprint: str
    required_total: AngleWrench
    branches: tuple[BaseBranchDomain, ...]
    # Real disjoint column-end rectangles, canonical millimetres. Never the L bounding box.
    column_contact_rectangles: tuple[tuple[Fraction, Fraction, Fraction, Fraction], ...]
    method: str = METHOD


@dataclass(frozen=True, slots=True)
class QualifiedBaseBranch:
    domain: BaseBranchDomain
    member_action: AngleWrench
    inactive_certificate: str | None = None


@dataclass(frozen=True, slots=True)
class ColumnPressurePatch:
    patch_id: str
    x_min: PhysicalQuantity
    x_max: PhysicalQuantity
    y_min: PhysicalQuantity
    y_max: PhysicalQuantity
    compressive_pressure: PhysicalQuantity

    def __post_init__(self) -> None:
        if (
            any(
                q.dimension is not Dimension.LENGTH
                for q in (self.x_min, self.x_max, self.y_min, self.y_max)
            )
            or self.compressive_pressure.dimension is not Dimension.STRESS
        ):
            raise ValueError("Contact bounds require lengths and pressure requires stress")


@dataclass(frozen=True, slots=True)
class QualifiedBaseResponse:
    reference: str
    source: EngineeringPropertySource
    issuer: str
    binding: BaseResponseBinding
    branches: tuple[QualifiedBaseBranch, ...]
    column_on_foundation_contact: AngleWrench
    pressure_patches: tuple[ColumnPressurePatch, ...]
    contact_inactive_certificate: str | None
    compatibility_stiffness_contact_basis: str
    coverage: tuple[str, ...]
    signed_load_domain: str
    method: str = METHOD
    foot_breakdowns: tuple[QualifiedFootBreakdown, ...] = ()


@dataclass(frozen=True, slots=True)
class FootBreakdownDomain:
    connector_id: str
    geometry_fingerprint: str
    native_core_fingerprint: str
    parent_wrench: AngleWrench
    anchor_points: tuple[tuple[str, ExactQuantityVector3D], ...]
    contact_bounds_mm: tuple[Fraction, Fraction, Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class QualifiedFootBreakdown:
    reference: str
    source: EngineeringPropertySource
    issuer: str
    domain: FootBreakdownDomain
    actions: tuple[SupportResponseAction, ...]
    applicability: str
    authorized_couple_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FootBreakdownValidation:
    domain: FootBreakdownDomain
    status: str
    reasons: tuple[str, ...]
    record: QualifiedFootBreakdown | None
    proof: ResponseProof | None
    fingerprint: str


def validate_foot_breakdown(
    domain: FootBreakdownDomain, records: tuple[QualifiedFootBreakdown, ...]
) -> FootBreakdownValidation:
    selected = tuple(r for r in records if r.domain.connector_id == domain.connector_id)
    if not selected:
        return FootBreakdownValidation(
            domain, "UNAVAILABLE_EXTERNAL", (), None, None, base_fingerprint(domain)
        )
    record = selected[0]
    reasons = []
    if len(selected) != 1 or record.domain != domain:
        reasons.append("FOOT_BREAKDOWN_EXACT_PARENT_DOMAIN_REQUIRED")
    if (
        not qualified_source(record.source)
        or not record.reference.strip()
        or not record.issuer.strip()
        or not record.applicability.strip()
    ):
        reasons.append("FOOT_BREAKDOWN_QUALIFIED_SOURCE_REQUIRED")
    anchors = dict(domain.anchor_points)
    declared = [a.bolt_id for a in record.actions if a.kind == "BOLT"]
    if len(declared) != len(anchors) or set(declared) != set(anchors):
        reasons.append("FOOT_BREAKDOWN_EXACT_ANCHOR_SET_REQUIRED")
    for action in record.actions:
        if action.group_id != f"{domain.connector_id}_FOUNDATION_GROUP":
            reasons.append("FOOT_BREAKDOWN_WRONG_GROUP")
        if action.layer_id != "FOUNDATION":
            reasons.append("FOOT_BREAKDOWN_RECEIVING_DOMAIN_MISMATCH")
        if action.kind == "BOLT" and action.point != anchors.get(action.bolt_id or ""):
            reasons.append("FOOT_ANCHOR_PHYSICAL_REFERENCE_MISMATCH")
        if action.kind == "CONTACT":
            x, y, z = components(action.point)
            a, b, c, d = domain.contact_bounds_mm
            if not a <= x <= b or not c <= y <= d or z != 0:
                reasons.append("FOOT_CONTACT_OUTSIDE_PHYSICAL_FOOTPRINT")
    proof = prove_support_response(
        domain.parent_wrench, record.actions, authorized_couple_ids=record.authorized_couple_ids
    )
    reasons.extend(proof.reasons)
    unique = tuple(dict.fromkeys(reasons))
    return FootBreakdownValidation(
        domain,
        "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE" if unique else "VALID_QUALIFIED_RESPONSE",
        unique,
        None if unique else record,
        proof,
        base_fingerprint((domain, record, proof, unique)),
    )


@dataclass(frozen=True, slots=True)
class BaseResponseValidation:
    status: str
    reasons: tuple[str, ...]
    response: QualifiedBaseResponse | None
    reconstructed_total: AngleWrench | None
    residual_force: ExactQuantityVector3D | None
    residual_moment: ExactQuantityVector3D | None
    exact_equilibrium: bool | None
    qualified: bool


def _pressure_contact(
    binding: BaseResponseBinding, record: QualifiedBaseResponse, reasons: list[str]
) -> AngleWrench:
    patches = record.pressure_patches
    ids = [p.patch_id for p in patches]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        reasons.append("DUPLICATE_OR_MISSING_CONTACT_PATCH_ID")
    values = []
    rectangles: list[tuple[Fraction, Fraction, Fraction, Fraction]] = []
    for p in patches:
        x0, x1, y0, y1 = (
            Fraction(q.canonical_magnitude) for q in (p.x_min, p.x_max, p.y_min, p.y_max)
        )
        pressure = Fraction(p.compressive_pressure.canonical_magnitude)
        if x0 >= x1 or y0 >= y1 or pressure < 0:
            reasons.append("INVALID_CONTACT_PATCH_OR_TENSILE_PRESSURE")
        # Union intersection area handles a valid patch that straddles the seam
        # between the two non-overlapping real material rectangles.
        area = sum(
            max(Fraction(0), min(x1, b) - max(x0, a)) * max(Fraction(0), min(y1, d) - max(y0, c))
            for a, b, c, d in binding.column_contact_rectangles
        )
        if area != (x1 - x0) * (y1 - y0):
            reasons.append("CONTACT_PRESSURE_OUTSIDE_REAL_L_FOOTPRINT")
        if any(min(x1, b) > max(x0, a) and min(y1, d) > max(y0, c) for a, b, c, d in rectangles):
            reasons.append("OVERLAPPING_CONTACT_PATCHES_DOUBLE_COUNT_PRESSURE")
        rectangles.append((x0, x1, y0, y1))
        point = quantity_vector(((x0 + x1) / 2, (y0 + y1) / 2, Fraction(0)), Unit.MM)
        values.append(
            AngleWrench(
                point,
                quantity_vector(
                    (Fraction(0), Fraction(0), -pressure * (x1 - x0) * (y1 - y0)), Unit.N
                ),
                quantity_vector(ZERO, Unit.N_MM),
            )
        )
    return sum_wrenches(tuple(values), binding.required_total.reference)


def validate_base_response(
    binding: BaseResponseBinding, record: QualifiedBaseResponse | None
) -> BaseResponseValidation:
    if record is None:
        return BaseResponseValidation(
            "SOURCE_REQUIRED",
            ("COMPLETE_TWO_LEG_BASE_RESPONSE_SOURCE_REQUIRED",),
            None,
            None,
            None,
            None,
            None,
            False,
        )
    reasons: list[str] = []
    if record.binding != binding or binding.method != METHOD or record.method != METHOD:
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
    ids = [b.domain.connector_id for b in record.branches]
    expected = {b.connector_id: b for b in binding.branches}
    if any(r.domain.connector_id not in expected for r in record.foot_breakdowns):
        reasons.append("FOOT_BREAKDOWN_UNKNOWN_CONNECTOR")
    if len(ids) != 2 or len(set(ids)) != 2 or set(ids) != set(expected):
        reasons.append("EXACT_TWO_BRANCH_IDENTITIES_REQUIRED")
    values = []
    for branch in record.branches:
        domain = expected.get(branch.domain.connector_id)
        if (
            branch.domain != domain
            or branch.member_action.reference != branch.domain.local_member_reference
        ):
            reasons.append("MEMBER_BRANCH_FRAME_LEG_OR_REFERENCE_MISMATCH")
        if is_zero(branch.member_action) and not branch.inactive_certificate:
            reasons.append("EXPLICIT_INACTIVE_BRANCH_CERTIFICATE_REQUIRED")
        if not is_zero(branch.member_action) and branch.inactive_certificate:
            reasons.append("NONZERO_BRANCH_MARKED_INACTIVE")
        values.append(
            transform_wrench(
                branch.member_action,
                branch.domain.frame,
                branch.domain.global_heel,
                binding.required_total.reference,
            )
        )
    contact = record.column_on_foundation_contact
    if contact.reference != binding.required_total.reference:
        reasons.append("DIRECT_CONTACT_REPORT_REFERENCE_MISMATCH")
    if is_zero(contact) and (not record.contact_inactive_certificate or record.pressure_patches):
        reasons.append("EXPLICIT_INACTIVE_COLUMN_CONTACT_REQUIRED")
    if not is_zero(contact) and record.contact_inactive_certificate:
        reasons.append("NONZERO_CONTACT_MARKED_INACTIVE")
    pressure = _pressure_contact(binding, record, reasons)
    if components(pressure.force) != components(contact.force) or components(
        pressure.moment
    ) != components(contact.moment):
        reasons.append("DIRECT_CONTACT_RESULTANT_NOT_PROVEN_BY_COMPRESSION_PATCHES")
    reconstructed = sum_wrenches((*values, contact), binding.required_total.reference)
    rf = subtract(components(reconstructed.force), components(binding.required_total.force))
    rm = subtract(components(reconstructed.moment), components(binding.required_total.moment))
    equilibrium = rf == ZERO and rm == ZERO
    if not equilibrium:
        reasons.append("EXACT_BASE_RESPONSE_EQUILIBRIUM_NOT_PROVEN")
    unique = tuple(dict.fromkeys(reasons))
    return BaseResponseValidation(
        "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE" if unique else "VALID_QUALIFIED_RESPONSE",
        unique,
        None if unique else record,
        reconstructed,
        quantity_vector(rf, Unit.N),
        quantity_vector(rm, Unit.N_MM),
        equilibrium,
        not unique,
    )
