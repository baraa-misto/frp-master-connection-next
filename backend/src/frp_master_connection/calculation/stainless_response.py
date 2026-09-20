"""C2-R internal trusted response envelope; not a contact/stiffness solver."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    angle_fingerprint,
    components,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.multirow import (
    ConnectedMaterialPair,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity

PROVIDER = "C2_R_TRUSTED_STAINLESS_RESPONSE_ENVELOPE_RC1"
MODES = (
    "MATERIAL_NEUTRAL_TRANSPORT",
    "ASCE74_FRP_STEEL_PRESCRIBED_ROWS",
    "NATIVE_EQUAL_BOLT_STIFFNESS_ECCENTRIC",
    "NATIVE_LOCKED_SYMMETRY",
    "QUALIFIED_EXTERNAL_MATERIAL_SPECIFIC_RESPONSE",
)
ZERO = (Fraction(0), Fraction(0), Fraction(0))


@dataclass(frozen=True, slots=True)
class ShaftLayer:
    id: str
    plane: str
    force: ExactQuantityVector3D
    cut: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class ResponseShaft:
    id: str
    layers: tuple[ShaftLayer, ...]
    terminal_reaction: ExactQuantityVector3D
    near: ExactQuantityVector3D
    far: ExactQuantityVector3D
    hardware_source: str
    frame: str
    reference: ExactQuantityVector3D


@dataclass(frozen=True, slots=True)
class PryingRecord:
    shaft_id: str
    direct: PhysicalQuantity
    component: PhysicalQuantity
    total: PhysicalQuantity
    source: str
    included_in_total: bool = True
    extra_multiplier: Decimal = Decimal(1)
    extra_increment: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class ContactRecord:
    id: str
    footprint_sha256: str
    active: bool
    compression: PhysicalQuantity
    wrench: AngleWrench
    source: str
    frame: str


@dataclass(frozen=True, slots=True)
class ResponseRequest:
    route: str
    bodies: tuple[str, ...]
    material_sha256: str
    product_sha256: str
    geometry_sha256: str
    action_id: str
    load_combination: str
    frame: str
    input_wrench: AngleWrench
    output_wrenches: tuple[AngleWrench, ...]
    mode: str
    shafts: tuple[ResponseShaft, ...] = ()
    contacts: tuple[ContactRecord, ...] = ()
    prying: tuple[PryingRecord, ...] = ()
    contact_prying_required: bool = False
    family_activation_requested: bool = False
    sign_convention: str = "RIGHT_HAND_ACTION_ON_ASSEMBLY"
    source_system: str = "NATIVE_PHYSICAL_QUANTITIES"


@dataclass(frozen=True, slots=True)
class NativeResponseEvidence:
    """Trusted resolver attestation tied to exact input/output, never a client flag.

    It preserves the native solver result fingerprint and exact applicability proof.
    C2-R does not rerun or reinterpret the accepted solver's arithmetic.
    """

    method: str
    request_sha256: str
    result_sha256: str
    applicability_source: str
    resolved_wrenches: tuple[AngleWrench, ...]
    row_fractions: tuple[Decimal, ...] = ()
    branch_identities: tuple[str, ...] = ()
    equal_translation_stiffness: bool = False
    qualified_slip_contact_fixture: bool = False
    native_equilibrium_proof: str = ""


@dataclass(frozen=True, slots=True)
class TrustedResponseRecord:
    request: ResponseRequest
    id: str
    source_sha256: str
    model_version: str
    qualification_date: str
    fixture_source: str
    load_domain: str
    precision_authority: str
    material_dependence_resolved: bool
    native: NativeResponseEvidence | None = None


@dataclass(frozen=True, slots=True)
class ResponseContext:
    records: tuple[TrustedResponseRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class ResponseResult:
    status: str
    source_status: str
    mode_status: str
    equilibrium_status: str
    shaft_status: str
    contact_prying_status: str
    demands: tuple[AngleWrench, ...]
    fingerprint: str
    authority: TrustedResponseRecord | None
    family_activation: bool = False
    body_strength: str = "NOT_EVALUATED"
    fastener_strength: str = "NOT_EVALUATED"
    foundation_strength: str = "EXTERNAL_NOT_EVALUATED"


def valid_hash(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def _equilibrium(r: ResponseRequest) -> bool:
    forces, moments = list(ZERO), list(ZERO)
    for wrench in r.output_wrenches:
        shifted = shift_angle_wrench(wrench, r.input_wrench.reference)
        for i, (f, m) in enumerate(
            zip(components(shifted.force), components(shifted.moment), strict=True)
        ):
            forces[i] += f
            moments[i] += m
    return tuple(forces) == components(r.input_wrench.force) and tuple(moments) == components(
        r.input_wrench.moment
    )


def _mode(r: ResponseRequest, record: TrustedResponseRecord) -> str:
    if r.mode not in MODES or not record.material_dependence_resolved:
        return "STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED"
    if r.mode == MODES[0]:
        if len(r.output_wrenches) != 1 or len(r.bodies) != 1 or r.contact_prying_required:
            return "STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED"
        return "QUALIFIED"
    if r.mode == MODES[4]:
        return "QUALIFIED"
    n = record.native
    if (
        n is None
        or not n.applicability_source
        or n.request_sha256 != angle_fingerprint(r)
        or not valid_hash(n.result_sha256)
        or n.resolved_wrenches != r.output_wrenches
    ):
        return "STAINLESS_RESPONSE_NATIVE_AUTHORITY_REQUIRED"
    if r.mode == MODES[1]:
        count = len(r.output_wrenches)
        fractions = {
            n: prescribed_row_fractions(ConnectedMaterialPair.FRP_STEEL, n) for n in (2, 3)
        }
        if count not in fractions or n.row_fractions != fractions[count]:
            return "STAINLESS_ASCE74_ROW_DISTRIBUTION_OUTSIDE_SCOPE"
        if n.method != "ASCE74_FRP_STEEL_PRESCRIBED_ROWS_NATIVE_GEOMETRY_VALIDATED":
            return "STAINLESS_RESPONSE_NATIVE_AUTHORITY_REQUIRED"
        for fraction, wrench in zip(n.row_fractions, r.output_wrenches, strict=True):
            if components(wrench.force) != tuple(
                Fraction(fraction) * x for x in components(r.input_wrench.force)
            ):
                return "STAINLESS_ASCE74_ROW_DISTRIBUTION_OUTSIDE_SCOPE"
    elif r.mode == MODES[2]:
        if (
            n.method
            not in (
                "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1",
                "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY:2.5A-RC1",
            )
            or not n.equal_translation_stiffness
            or not n.qualified_slip_contact_fixture
            or n.native_equilibrium_proof != "NATIVE_VERIFIED_EQUILIBRIUM"
        ):
            return "STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED"
    elif (
        n.method != "NATIVE_EXACT_SYMMETRY_PREDICATE"
        or len(n.branch_identities) != len(r.output_wrenches)
        or len(set(n.branch_identities)) != 1
        or not all(valid_hash(x) for x in n.branch_identities)
    ):
        return "STAINLESS_NATIVE_SYMMETRY_NOT_QUALIFIED"
    return "QUALIFIED"


def _shafts(r: ResponseRequest) -> str:
    if len({s.id for s in r.shafts}) != len(r.shafts):
        return "STAINLESS_COMMON_SHAFT_DUPLICATE_LAYER"
    for shaft in r.shafts:
        if not shaft.id or not shaft.layers or not shaft.hardware_source:
            return "STAINLESS_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED"
        if shaft.frame != r.frame or shaft.reference != r.input_wrench.reference:
            return "STAINLESS_RESPONSE_REFERENCE_FRAME_MISMATCH"
        if len({x.id for x in shaft.layers}) != len(shaft.layers) or len(
            {x.plane for x in shaft.layers}
        ) != len(shaft.layers):
            return "STAINLESS_COMMON_SHAFT_DUPLICATE_LAYER"
        total = list(ZERO)
        for layer in shaft.layers:
            total = [a + b for a, b in zip(total, components(layer.force), strict=True)]
            if tuple(total) != components(layer.cut):
                return "STAINLESS_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED"
        if tuple(total) != components(shaft.terminal_reaction):
            return "STAINLESS_COMMON_SHAFT_CONSERVATION_NOT_SATISFIED"
    return "QUALIFIED"


def _contact(r: ResponseRequest) -> str:
    if r.contact_prying_required and not (r.contacts or r.prying):
        return "STAINLESS_CONTACT_PRYING_AUTHORITY_REQUIRED"
    if len({x.id for x in r.contacts}) != len(r.contacts) or len(
        {x.shaft_id for x in r.prying}
    ) != len(r.prying):
        return "STAINLESS_CONTACT_PRYING_AUTHORITY_REQUIRED"
    for contact in r.contacts:
        if (
            not contact.source
            or not valid_hash(contact.footprint_sha256)
            or contact.frame != r.frame
            or contact.compression.canonical_magnitude < 0
            or (
                not contact.active
                and (
                    contact.compression.canonical_magnitude != 0
                    or components(contact.wrench.force) != ZERO
                    or components(contact.wrench.moment) != ZERO
                )
            )
        ):
            return "STAINLESS_CONTACT_PRYING_AUTHORITY_REQUIRED"
    for p in r.prying:
        direct, component, total = (
            Fraction(q.canonical_magnitude) for q in (p.direct, p.component, p.total)
        )
        if not p.source or p.shaft_id not in {s.id for s in r.shafts}:
            return "STAINLESS_CONTACT_PRYING_AUTHORITY_REQUIRED"
        if (
            min(direct, component, total) < 0
            or direct + component != total
            or not p.included_in_total
            or p.extra_multiplier != 1
            or p.extra_increment != 0
        ):
            return "STAINLESS_PRYING_TOTAL_TENSION_CONVENTION_INVALID"
    return "QUALIFIED"


def evaluate_stainless_response(r: ResponseRequest, context: ResponseContext) -> ResponseResult:
    """Trusted-context matching precedes numerical checks; unsupported output is absent."""
    matches = [x for x in context.records if x.request == r]
    record = matches[0] if len(matches) == 1 else None
    source = "QUALIFIED"
    if record is None or not all(
        (
            record.id,
            valid_hash(record.source_sha256),
            record.model_version,
            record.qualification_date,
            record.fixture_source,
            record.load_domain,
            record.precision_authority,
            r.route,
            r.bodies,
            r.action_id,
            r.load_combination,
            r.frame,
            r.sign_convention,
            valid_hash(r.material_sha256),
            valid_hash(r.product_sha256),
            valid_hash(r.geometry_sha256),
        )
    ):
        source = "STAINLESS_RESPONSE_SOURCE_REQUIRED"
    mode = _mode(r, record) if source == "QUALIFIED" and record is not None else "NOT_EVALUATED"
    # Native Decimal projections are consumed verbatim. Their native proof, bound
    # by the trusted request/result record, must not be replaced by a second
    # precision path. Other transport/source modes retain exact conservation.
    native_conservation = (
        r.mode == MODES[2]
        and mode == "QUALIFIED"
        and record is not None
        and record.native is not None
        and record.native.native_equilibrium_proof == "NATIVE_VERIFIED_EQUILIBRIUM"
    )
    equilibrium = (
        "QUALIFIED"
        if native_conservation or _equilibrium(r)
        else "STAINLESS_RESPONSE_EQUILIBRIUM_NOT_SATISFIED"
    )
    shafts, contact = _shafts(r), _contact(r)
    errors = [s for s in (source, mode, equilibrium, shafts, contact) if s != "QUALIFIED"]
    status = errors[0] if errors else "QUALIFIED_RESPONSE"
    if r.family_activation_requested:
        status = "STAINLESS_PUBLIC_FAMILY_ACTIVATION_NOT_AUTHORIZED"
    return ResponseResult(
        status,
        source,
        mode,
        equilibrium,
        shafts,
        contact,
        r.output_wrenches if status == "QUALIFIED_RESPONSE" else (),
        angle_fingerprint((PROVIDER, r, record, status)),
        record,
    )
