"""Server-only complete response validation. This module does not determine reactions."""

from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from frp_master_connection.calculation.angle_column_base_response import sum_wrenches
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.dctn3b_demand import DCTN3BDemand
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.support_attachment_response import qualified_source
from frp_master_connection.domain.dctn3b import CONTRACT, DCTN3BRequest
from frp_master_connection.domain.dctn_geometry import DCTNGeometry, DCTNShaft
from frp_master_connection.domain.material_architecture import EngineeringPropertySource

ZERO: Rational3 = (Fraction(0), Fraction(0), Fraction(0))
COVERAGE = (
    "SIDE_CHANNEL_WRENCHES",
    "SHAFT_SHEAR_TENSION_BENDING",
    "ORDERED_LAYER_TRANSFERS",
    "UNILATERAL_CONTACT",
    "SIX_COMPONENT_CLOSURE",
)


@dataclass(frozen=True, slots=True)
class CompleteResponseBinding:
    contract: str
    method: str
    geometry_fingerprint: str
    request_fingerprint: str
    demand_fingerprint: str


def response_binding(
    value: DCTN3BRequest, geometry: DCTNGeometry, demand: DCTN3BDemand, method: str
) -> CompleteResponseBinding:
    return CompleteResponseBinding(
        CONTRACT, method, geometry.fingerprint, dctn_fingerprint(value), demand.fingerprint
    )


@dataclass(frozen=True, slots=True)
class LayerTransfer:
    owner_id: str
    on_shaft: AngleWrench


@dataclass(frozen=True, slots=True)
class ShaftSection:
    # Internal resultant balances the accumulated layer actions at this section.
    after_layer: int
    internal_wrench: AngleWrench
    tension_N: Fraction
    shear_N: Rational3
    bending_N_mm: Rational3


@dataclass(frozen=True, slots=True)
class CompleteShaftResponse:
    shaft_id: str
    layers: tuple[LayerTransfer, ...]
    sections: tuple[ShaftSection, ...]


@dataclass(frozen=True, slots=True)
class ChannelTransfer:
    member_id: str
    channel_id: str
    wrench: AngleWrench


@dataclass(frozen=True, slots=True)
class ContactTransfer:
    patch_id: str
    member_id: str
    channel_id: str
    normal: Rational3
    gap_mm: Fraction
    compression_N: Fraction
    on_channel: AngleWrench


@dataclass(frozen=True, slots=True)
class TrustedCompleteResponse:
    binding: CompleteResponseBinding
    source: EngineeringPropertySource
    artifact_sha256: str
    qualification_record: str
    applicability: tuple[str, ...]
    shafts: tuple[CompleteShaftResponse, ...]
    channels: tuple[ChannelTransfer, ...]
    contacts: tuple[ContactTransfer, ...]
    contact_domain: str


@dataclass(frozen=True, slots=True)
class CompleteResponseValidation:
    status: str
    reasons: tuple[str, ...]
    response: TrustedCompleteResponse | None


EMPTY_TRUSTED_RESPONSES: tuple[TrustedCompleteResponse, ...] = ()


def _same_wrench(a: AngleWrench, b: AngleWrench) -> bool:
    shifted = shift_angle_wrench(a, b.reference)
    return components(shifted.force) == components(b.force) and (
        components(shifted.moment) == components(b.moment)
    )


def _shaft_reference(wrench: AngleWrench, shaft: DCTNShaft, unit: Unit) -> bool:
    start = components(quantity_vector(shaft.start, unit))
    end = components(quantity_vector(shaft.end, unit))
    point = components(wrench.reference)
    return (
        point[0] == start[0]
        and point[2] == start[2]
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def validate_complete_response(
    value: DCTN3BRequest,
    geometry: DCTNGeometry,
    demand: DCTN3BDemand,
    record: TrustedCompleteResponse,
) -> CompleteResponseValidation:
    """No public source text enters this function; each record is server supplied."""
    reasons: list[str] = []
    binding = response_binding(value, geometry, demand, record.binding.method)
    if (
        record.binding != binding
        or not record.binding.method
        or geometry.status != "VALID"
        or not qualified_source(record.source)
        or record.artifact_sha256 != record.source.controlling_artifact_sha256
        or record.qualification_record not in record.source.qualification_record_ids
    ):
        reasons.append("DCTN_TRUSTED_RESPONSE_BINDING_MISMATCH")
    if (
        len(record.artifact_sha256) != 64
        or any(c not in "0123456789abcdefABCDEF" for c in record.artifact_sha256)
        or not record.qualification_record
        or not set(record.applicability) >= set(COVERAGE)
    ):
        reasons.append("DCTN_TRUSTED_RESPONSE_COVERAGE_INVALID")
    expected = {s.bolt_id: s for s in geometry.shafts}
    if len(record.shafts) != len(expected) or {s.shaft_id for s in record.shafts} != set(expected):
        reasons.append("DCTN_TRUSTED_RESPONSE_COVERAGE_INVALID")
    node = demand.total_at_node.reference
    zero = AngleWrench(node, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM))
    layer_channels: dict[tuple[str, str], list[AngleWrench]] = {}
    for supplied in record.shafts:
        shaft = expected.get(supplied.shaft_id)
        if shaft is None:
            continue
        if tuple(layer.owner_id for layer in supplied.layers) != shaft.layer_owners or tuple(
            s.after_layer for s in supplied.sections
        ) != tuple(range(len(shaft.layer_owners))):
            reasons.append("DCTN_TRUSTED_RESPONSE_COVERAGE_INVALID")
            continue
        if any(
            not _shaft_reference(w, shaft, geometry.length_unit)
            for w in (
                *tuple(layer.on_shaft for layer in supplied.layers),
                *tuple(s.internal_wrench for s in supplied.sections),
            )
        ):
            reasons.append("DCTN_TRUSTED_RESPONSE_BINDING_MISMATCH")
        if not _same_wrench(
            sum_wrenches(tuple(layer.on_shaft for layer in supplied.layers), node), zero
        ):
            reasons.append("DCTN_TRUSTED_RESPONSE_EQUILIBRIUM_INVALID")
        for i, section in enumerate(supplied.sections):
            accumulated = sum_wrenches(
                tuple(layer.on_shaft for layer in supplied.layers[: i + 1]),
                section.internal_wrench.reference,
            )
            balanced = sum_wrenches((accumulated, section.internal_wrench), node)
            f, m = (
                components(section.internal_wrench.force),
                components(section.internal_wrench.moment),
            )
            # Positive cut tension follows the actual shaft ordering, including W/I POS -Y.
            direction = Fraction(1 if shaft.end[1] > shaft.start[1] else -1)
            if (
                not _same_wrench(balanced, zero)
                or section.tension_N < 0
                or section.tension_N != max(Fraction(0), direction * f[1])
                or section.shear_N != (f[0], Fraction(0), f[2])
                or section.bending_N_mm != (m[0], Fraction(0), m[2])
            ):
                reasons.append("DCTN_TRUSTED_RESPONSE_EQUILIBRIUM_INVALID")
        for layer in supplied.layers:
            if layer.owner_id.startswith("CHORD"):
                w = layer.on_shaft
                reaction = AngleWrench(
                    w.reference,
                    quantity_vector(
                        cast(Rational3, tuple(-x for x in components(w.force))), Unit.N
                    ),
                    quantity_vector(
                        cast(Rational3, tuple(-x for x in components(w.moment))), Unit.N_MM
                    ),
                )
                layer_channels.setdefault(
                    (shaft.member_id, layer.owner_id.split(":")[0]), []
                ).append(reaction)
    if record.contact_domain not in {"SOURCE_PROVEN_NO_CONTACT", "COMPLETE_UNILATERAL_PATCHES"}:
        reasons.append("DCTN_TRUSTED_RESPONSE_CONTACT_INVALID")
    if (record.contact_domain == "SOURCE_PROVEN_NO_CONTACT" and record.contacts) or (
        record.contact_domain == "COMPLETE_UNILATERAL_PATCHES" and not record.contacts
    ):
        reasons.append("DCTN_TRUSTED_RESPONSE_CONTACT_INVALID")
    patch_ids = [c.patch_id for c in record.contacts]
    if len(set(patch_ids)) != len(patch_ids) or any(not p for p in patch_ids):
        reasons.append("DCTN_TRUSTED_RESPONSE_CONTACT_INVALID")
    for contact in record.contacts:
        if (
            contact.gap_mm < 0
            or contact.compression_N < 0
            or contact.gap_mm * contact.compression_N != 0
            or sum(x * x for x in contact.normal) != 1
            or components(contact.on_channel.force)
            != tuple(contact.compression_N * x for x in contact.normal)
            or components(contact.on_channel.moment) != ZERO
        ):
            reasons.append("DCTN_TRUSTED_RESPONSE_CONTACT_INVALID")
        layer_channels.setdefault((contact.member_id, contact.channel_id), []).append(
            contact.on_channel
        )
    keys = {(m.member_id, c) for m in demand.members for c in ("CHORD_NEG", "CHORD_POS")}
    supplied_keys = [(c.member_id, c.channel_id) for c in record.channels]
    if len(supplied_keys) != len(keys) or set(supplied_keys) != keys or set(layer_channels) != keys:
        reasons.append("DCTN_TRUSTED_RESPONSE_COVERAGE_INVALID")
    for transfer in record.channels:
        terms = tuple(layer_channels.get((transfer.member_id, transfer.channel_id), ()))
        if not terms or not _same_wrench(sum_wrenches(terms, node), transfer.wrench):
            reasons.append("DCTN_TRUSTED_RESPONSE_EQUILIBRIUM_INVALID")
    for member in demand.members:
        transfers = tuple(c.wrench for c in record.channels if c.member_id == member.member_id)
        if not transfers or not _same_wrench(sum_wrenches(transfers, node), member.at_member_end):
            reasons.append("DCTN_TRUSTED_RESPONSE_EQUILIBRIUM_INVALID")
    unique = tuple(dict.fromkeys(reasons))
    return CompleteResponseValidation(
        "QUALIFIED" if not unique else "REJECTED", unique, record if not unique else None
    )


def resolve_complete_response(
    value: DCTN3BRequest,
    geometry: DCTNGeometry,
    demand: DCTN3BDemand,
    registry: tuple[TrustedCompleteResponse, ...] = EMPTY_TRUSTED_RESPONSES,
) -> CompleteResponseValidation:
    records = tuple(
        r
        for r in registry
        if r.binding == response_binding(value, geometry, demand, r.binding.method)
    )
    if len(records) != 1:
        return CompleteResponseValidation("UNRESOLVED", ("DCTN_TRUSTED_RESPONSE_NOT_BOUND",), None)
    return validate_complete_response(value, geometry, demand, records[0])
