"""Synthetic supplied responses prove validation, never production qualification."""

import json
from dataclasses import replace
from fractions import Fraction
from typing import cast

import pytest

from frp_master_connection.application.dctn3b import (
    TRANSVERSE,
    DCTN3BPreview,
    design_check_dctn3b,
    preview_dctn3b,
)
from frp_master_connection.calculation.angle_column_base_response import sum_wrenches
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.dctn3b_trusted_response import (
    COVERAGE,
    EMPTY_TRUSTED_RESPONSES,
    ChannelTransfer,
    CompleteShaftResponse,
    ContactTransfer,
    LayerTransfer,
    ShaftSection,
    TrustedCompleteResponse,
    resolve_complete_response,
    response_binding,
    validate_complete_response,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.dctn3b import DCTN3BRequest, default_dctn3b_request
from frp_master_connection.domain.double_channel_truss_node import DCTNForm
from tests.calculation.test_dctn3b_native import GOLDEN
from tests.calculation.test_dctn_sources_and_native import synthetic_source

F = Fraction
ZERO = (F(0), F(0), F(0))


def scaled(w: AngleWrench, factor: Fraction) -> AngleWrench:
    return AngleWrench(
        w.reference,
        quantity_vector(cast(Rational3, tuple(factor * x for x in components(w.force))), Unit.N),
        quantity_vector(
            cast(Rational3, tuple(factor * x for x in components(w.moment))), Unit.N_MM
        ),
    )


def cuts(layers: tuple[LayerTransfer, ...], direction: int) -> tuple[ShaftSection, ...]:
    sections = []
    for i, layer in enumerate(layers):
        internal = scaled(
            sum_wrenches(tuple(t.on_shaft for t in layers[: i + 1]), layer.on_shaft.reference),
            F(-1),
        )
        force, moment = components(internal.force), components(internal.moment)
        sections.append(
            ShaftSection(
                i,
                internal,
                max(F(0), direction * force[1]),
                (force[0], F(0), force[2]),
                (moment[0], F(0), moment[2]),
            )
        )
    return tuple(sections)


def supplied(
    form: DCTNForm = DCTNForm.RHS,
) -> tuple[DCTN3BRequest, DCTN3BPreview, TrustedCompleteResponse]:
    request = default_dctn3b_request()
    request = replace(
        request,
        members=(
            replace(
                request.members[0],
                section=replace(request.members[0].section, form=form),
                Qp=Q.of(2, Unit.KIP),
                Qq=Q.of(3, Unit.KIP),
            ),
        ),
    )
    preview = preview_dctn3b(request)
    demand = preview.demand.members[0].at_member_end
    shafts = []
    channel_terms: dict[str, list[AngleWrench]] = {"CHORD_NEG": [], "CHORD_POS": []}
    count = len(preview.geometry.shafts)
    for shaft in preview.geometry.shafts:
        reference = quantity_vector(shaft.start, preview.geometry.length_unit)
        per_shaft = scaled(shift_angle_wrench(demand, reference), F(1, count))
        layers = []
        non_body_seen = False
        for owner in shaft.layer_owners:
            if owner.startswith("CHORD"):
                # TEST ONLY prescribed unequal transfer, not a production sharing rule.
                share = (
                    F(1)
                    if form is DCTNForm.W_I
                    else F(2, 5)
                    if owner.startswith("CHORD_NEG")
                    else F(3, 5)
                )
                wrench = scaled(per_shaft, -share)
                channel_terms[owner.split(":")[0]].append(scaled(wrench, F(-1)))
            else:
                wrench = scaled(per_shaft, F(0) if non_body_seen else F(1))
                non_body_seen = True
            layers.append(LayerTransfer(owner, wrench))
        ordered = tuple(layers)
        direction = 1 if shaft.end[1] > shaft.start[1] else -1
        shafts.append(CompleteShaftResponse(shaft.bolt_id, ordered, cuts(ordered, direction)))
    channels = tuple(
        ChannelTransfer("V", name, sum_wrenches(tuple(terms), demand.reference))
        for name, terms in channel_terms.items()
    )
    record = TrustedCompleteResponse(
        response_binding(request, preview.geometry, preview.demand, "SYNTHETIC_TEST_RESPONSE_ONLY"),
        synthetic_source(),
        "A" * 64,
        "TEST_ONLY_QUALIFICATION",
        COVERAGE,
        tuple(shafts),
        channels,
        (),
        "SOURCE_PROVEN_NO_CONTACT",
    )
    return request, preview, record


@pytest.mark.parametrize("form", tuple(DCTNForm))
def test_complete_response_is_supplied_not_inferred_and_local_strength_stays_missing(
    form: DCTNForm,
) -> None:
    request, preview, record = supplied(form)
    result = validate_complete_response(request, preview.geometry, preview.demand, record)
    assert result.status == "QUALIFIED", result.reasons
    assert result.response == record
    resolved = preview_dctn3b(request, (record,))
    assert resolved.response_status == "QUALIFIED"
    assert resolved.historical_preview is None
    assert resolved.design_status == "ENGINEERING_REVIEW_REQUIRED"
    assert design_check_dctn3b(request, trusted=(record,)).checks == ()
    assert EMPTY_TRUSTED_RESPONSES == ()
    assert preview_dctn3b(request).response_status == TRANSVERSE
    assert (
        resolve_complete_response(
            request, preview.geometry, preview.demand, (record, record)
        ).response
        is None
    )
    if form is not DCTNForm.W_I:
        assert components(record.channels[0].wrench.force) != components(
            record.channels[1].wrench.force
        )


@pytest.mark.parametrize(
    "change",
    [
        "geometry",
        "action",
        "sign",
        "hardware",
        "material",
        "reference",
        "method",
        "artifact",
        "qualification",
        "source",
        "missing_shaft",
        "duplicate_shaft",
        "unknown_shaft",
        "layer_order",
        "missing_cut",
        "cut_reference",
        "cut_tension",
        "cut_shear",
        "cut_bending",
        "shaft_force",
        "shaft_moment",
        "channel_force",
        "channel_moment",
        "missing_channel",
        "member_closure",
        "coverage",
        "bad_hash",
        "bad_hex",
        "empty_qualification",
    ],
)
def test_trusted_response_binding_coverage_and_closure_fail_closed(change: str) -> None:
    request, preview, record = supplied()
    first = record.shafts[0]
    if change in {"geometry", "action", "sign", "hardware", "material", "reference", "method"}:
        field = {
            "method": "method",
            "geometry": "geometry_fingerprint",
            "action": "demand_fingerprint",
            "sign": "demand_fingerprint",
            "reference": "demand_fingerprint",
        }.get(change, "request_fingerprint")
        record = replace(
            record, binding=replace(record.binding, **{field: "" if field == "method" else change})
        )
    elif change in {"artifact", "bad_hash", "bad_hex"}:
        record = replace(
            record,
            artifact_sha256={"artifact": "B" * 64, "bad_hash": "A", "bad_hex": "Z" * 64}[change],
        )
    elif change in {"qualification", "empty_qualification"}:
        record = replace(
            record, qualification_record="" if change == "empty_qualification" else "WRONG_RECORD"
        )
    elif change == "source":
        record = replace(record, source=replace(record.source, qualification_record_ids=()))
    elif change == "missing_shaft":
        record = replace(record, shafts=record.shafts[1:])
    elif change == "duplicate_shaft":
        record = replace(record, shafts=(*record.shafts, first))
    elif change == "unknown_shaft":
        record = replace(record, shafts=(replace(first, shaft_id="UNKNOWN"), *record.shafts[1:]))
    elif change in {"layer_order", "missing_cut"}:
        record = replace(
            record,
            shafts=(
                replace(first, layers=first.layers[::-1])
                if change == "layer_order"
                else replace(first, sections=first.sections[:-1]),
                *record.shafts[1:],
            ),
        )
    elif change.startswith("cut_"):
        section = first.sections[0]
        if change == "cut_reference":
            section = replace(
                section,
                internal_wrench=replace(
                    section.internal_wrench,
                    reference=quantity_vector((F(999), F(0), F(0)), Unit.IN),
                ),
            )
        elif change == "cut_tension":
            section = replace(section, tension_N=F(-1))
        elif change == "cut_shear":
            section = replace(section, shear_N=(F(999), F(0), F(0)))
        else:
            section = replace(section, bending_N_mm=(F(999), F(0), F(0)))
        record = replace(
            record,
            shafts=(replace(first, sections=(section, *first.sections[1:])), *record.shafts[1:]),
        )
    elif change.startswith("shaft_"):
        layer = first.layers[0]
        component = "force" if change == "shaft_force" else "moment"
        wrong = quantity_vector((F(999), F(0), F(0)), Unit.N if component == "force" else Unit.N_MM)
        layer = replace(layer, on_shaft=replace(layer.on_shaft, **{component: wrong}))
        record = replace(
            record, shafts=(replace(first, layers=(layer, *first.layers[1:])), *record.shafts[1:])
        )
    elif change.startswith("channel_"):
        transfer = record.channels[0]
        component = "force" if change == "channel_force" else "moment"
        wrong = quantity_vector((F(999), F(0), F(0)), Unit.N if component == "force" else Unit.N_MM)
        record = replace(
            record,
            channels=(
                replace(transfer, wrench=replace(transfer.wrench, **{component: wrong})),
                *record.channels[1:],
            ),
        )
    elif change == "missing_channel":
        record = replace(record, channels=record.channels[1:])
    elif change == "member_closure":
        record = replace(
            record,
            shafts=tuple(
                replace(
                    s,
                    layers=tuple(
                        replace(layer, on_shaft=scaled(layer.on_shaft, F(2))) for layer in s.layers
                    ),
                    sections=cuts(
                        tuple(
                            replace(layer, on_shaft=scaled(layer.on_shaft, F(2)))
                            for layer in s.layers
                        ),
                        1,
                    ),
                )
                for s in record.shafts
            ),
            channels=tuple(replace(c, wrench=scaled(c.wrench, F(2))) for c in record.channels),
        )
    else:
        assert change == "coverage"
        record = replace(record, applicability=())
    result = validate_complete_response(request, preview.geometry, preview.demand, record)
    assert result.status == "REJECTED", change
    assert result.reasons
    assert result.response is None
    approved = {
        "geometry": 11,
        "action": 12,
        "sign": 13,
        "hardware": 14,
        "missing_shaft": 15,
        "shaft_force": 16,
        "shaft_moment": 17,
        "duplicate_shaft": 18,
    }
    if change in approved:
        case = json.loads(GOLDEN.read_bytes())["negative_cases"][approved[change] - 1]
        assert case["expected_status"] in result.reasons


@pytest.mark.parametrize(
    "change",
    [
        "valid",
        "negative",
        "gap",
        "normal",
        "force",
        "moment",
        "duplicate",
        "empty_id",
        "unknown_member",
        "unknown_domain",
        "missing",
        "forbidden",
    ],
)
def test_unilateral_contact_source_domain(change: str) -> None:
    request, preview, record = supplied()
    zero = scaled(preview.demand.members[0].at_member_end, F(0))
    contact = ContactTransfer(
        "TEST_ONLY_PATCH", "V", "CHORD_NEG", (F(0), F(1), F(0)), F(1), F(0), zero
    )
    if change == "negative":
        contact = replace(contact, compression_N=F(-1))
    elif change == "gap":
        contact = replace(contact, gap_mm=F(-1))
    elif change == "normal":
        contact = replace(contact, normal=(F(0), F(2), F(0)))
    elif change == "force":
        contact = replace(
            contact, on_channel=replace(zero, force=quantity_vector((F(1), F(0), F(0)), Unit.N))
        )
    elif change == "moment":
        contact = replace(
            contact, on_channel=replace(zero, moment=quantity_vector((F(1), F(0), F(0)), Unit.N_MM))
        )
    elif change == "empty_id":
        contact = replace(contact, patch_id="")
    elif change == "unknown_member":
        contact = replace(contact, member_id="UNKNOWN")
    contacts = (
        () if change == "missing" else (contact, contact) if change == "duplicate" else (contact,)
    )
    domain = (
        "UNKNOWN"
        if change == "unknown_domain"
        else "SOURCE_PROVEN_NO_CONTACT"
        if change == "forbidden"
        else "COMPLETE_UNILATERAL_PATCHES"
    )
    record = replace(record, contact_domain=domain, contacts=contacts)
    result = validate_complete_response(request, preview.geometry, preview.demand, record)
    assert result.status == ("QUALIFIED" if change == "valid" else "REJECTED")
    if change == "negative":
        assert (
            json.loads(GOLDEN.read_bytes())["negative_cases"][18]["expected_status"]
            in result.reasons
        )


def test_actual_input_changes_and_invalid_geometry_do_not_bind() -> None:
    request, preview, record = supplied()
    for altered in (
        replace(request, fastener=replace(request.fastener, source_reference="FORGED")),
        replace(request, members=(replace(request.members[0], Qq=Q.of(-3, Unit.KIP)),)),
        replace(request, channel=replace(request.channel, depth=Q.of(4, Unit.IN))),
    ):
        result = preview_dctn3b(altered, (record,))
        assert result.response_status == TRANSVERSE
        assert result.historical_preview is None
    invalid = replace(preview.geometry, status="INVALID_GEOMETRY")
    assert validate_complete_response(request, invalid, preview.demand, record).status == "REJECTED"
