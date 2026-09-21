"""Synthetic private binding fixtures are not production qualification sources."""

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from frp_master_connection.api.ssmc import illustrative_ssmc, map_ssmc_request, serialize_ssmc_value
from frp_master_connection.application.ssmc import preview_ssmc, vector
from frp_master_connection.calculation.angle_connector_core import AngleWrench
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.ssmc_material import (
    EMPTY_PROPERTY_REGISTRY,
    PROPERTY_DIRECTIONS,
    SSMCQualifiedProperty,
    select_ssmc_property,
)
from frp_master_connection.calculation.ssmc_response import (
    EMPTY_RESPONSE_REGISTRY,
    REQUIRED_RESPONSE,
    SSMCResolvedResponseQuantity,
    SSMCResponseAction,
    SSMCTrustedResponse,
    required_design_status,
    validate_ssmc_response,
)
from frp_master_connection.domain.ssmc import PLATE_POLICY


def response_fixture() -> tuple[SSMCTrustedResponse, dict[str, str], dict[str, AngleWrench]]:
    preview = preview_ssmc(map_ssmc_request(illustrative_ssmc()))
    groups = {g.group_id: g.plate_wrench for g in preview.groups}
    ownership = {s.id: s.group for s in preview.geometry.shafts}
    actions = tuple(
        SSMCResponseAction(s.id, s.group, groups[s.group], "SHAFT") for s in preview.geometry.shafts
    )
    quantities = tuple(
        SSMCResolvedResponseQuantity(
            shaft, mechanism, tuple(Q(Decimal(0), unit) for _ in range(count))
        )
        for shaft in ownership
        for mechanism, unit, count in (
            ("SHAFT_SHEAR", Unit.N, 2),
            ("BOLT_AXIS_TENSION", Unit.N, 1),
            ("PRYING", Unit.N, 1),
            ("SHAFT_BENDING", Unit.N_MM, 3),
        )
    ) + tuple(
        SSMCResolvedResponseQuantity(group, mechanism, tuple(Q(Decimal(0), unit) for _ in range(3)))
        for group in groups
        for mechanism, unit in (
            ("PLATE_LOCAL_BENDING", Unit.N_MM),
            ("WEB_LOCAL_BENDING", Unit.N_MM),
            ("UNILATERAL_CONTACT", Unit.N),
            ("SLIP_COMPATIBILITY", Unit.MM),
        )
    )
    return (
        SSMCTrustedResponse(
            "TEST_ONLY_NO_PRODUCTION_AUTHORITY",
            "SSMC-2-RC1",
            preview.engineering_fingerprint,
            "TEST_1",
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "ZERO_ACTION_TEST_ONLY",
            REQUIRED_RESPONSE,
            tuple(ownership),
            actions,
            quantities,
            tuple(
                (owner, "d" * 64)
                for owner in (
                    "HORIZONTAL_STRINGER_MATERIAL",
                    "INCLINED_STRINGER_MATERIAL",
                    "MITER_WEB_PLATE_MATERIAL",
                    "HARDWARE_SOURCE",
                    "CONTACT_SLIP_ASSUMPTIONS",
                )
            ),
        ),
        ownership,
        groups,
    )


def validate(
    record: SSMCTrustedResponse, ownership: dict[str, str], targets: dict[str, AngleWrench]
) -> None:
    validate_ssmc_response(
        record,
        response_fixture()[0].binding,
        ownership,
        targets,
        vector((Decimal(0),) * 3, Unit.MM),
    )


def test_empty_production_registries_and_private_binding_do_not_qualify_resistance() -> None:
    assert not EMPTY_PROPERTY_REGISTRY
    assert not EMPTY_RESPONSE_REGISTRY
    record, ownership, targets = response_fixture()
    validate(record, ownership, targets)
    result = preview_ssmc(map_ssmc_request(illustrative_ssmc()), {record.binding: record})
    assert result.trusted_complete_response == record
    assert "SSMC_SINGLE_SIDE_RESPONSE_NOT_QUALIFIED" not in result.blockers
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    failed = replace(record, numerical_failures=("QUALIFIED_TEST_CHECK_FAIL",))
    result = preview_ssmc(map_ssmc_request(illustrative_ssmc()), {record.binding: failed})
    assert result.whole_connection_status == "FAIL"
    assert result.blockers
    assert isinstance(serialize_ssmc_value(result), dict)


@pytest.mark.parametrize(
    "change",
    [
        {"binding": "wrong"},
        {"contract": "future"},
        {"source_id": ""},
        {"method_version": ""},
        {"applicability": ""},
        {"source_sha256": ""},
        {"approval_sha256": "g" * 64},
        {"compatibility_evidence_sha256": "x"},
        {"shaft_ids": ()},
        {"actions": ()},
        {"covered_mechanisms": frozenset()},
        {"resolved_quantities": ()},
        {"authority_snapshots": ()},
    ],
)
def test_unbound_or_incomplete_response_cannot_activate(change: dict[str, Any]) -> None:
    record, ownership, targets = response_fixture()
    with pytest.raises(ValueError, match="SSMC_TRUSTED"):
        validate(replace(record, **change), ownership, targets)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_shaft",
        "duplicate_action",
        "wrong_group",
        "wrong_mechanism",
        "contact_as_shaft",
        "foreign_shaft",
        "duplicate_quantity",
        "wrong_unit",
        "quantity_mismatch",
        "force",
        "moment",
    ],
)
def test_response_owner_quantity_and_exact_closure_adversaries(mutation: str) -> None:
    record, ownership, targets = response_fixture()
    action = record.actions[0]
    if mutation == "duplicate_shaft":
        record = replace(record, shaft_ids=(*record.shaft_ids, record.shaft_ids[0]))
    elif mutation == "duplicate_action":
        record = replace(record, actions=(*record.actions, action))
    elif mutation == "duplicate_quantity":
        record = replace(
            record,
            resolved_quantities=(*record.resolved_quantities, record.resolved_quantities[0]),
        )
    elif mutation in {"wrong_unit", "quantity_mismatch"}:
        q = record.resolved_quantities[0]
        q = replace(q, values=(Q(Decimal(1), Unit.MM if mutation == "wrong_unit" else Unit.N),) * 2)
        record = replace(record, resolved_quantities=(q, *record.resolved_quantities[1:]))
    else:
        if mutation == "wrong_group":
            action = replace(action, group_id="BAD")
        elif mutation == "wrong_mechanism":
            action = replace(action, mechanism="MITER_CONTACT")
        elif mutation == "contact_as_shaft":
            action = replace(action, mechanism="CONTACT")
        elif mutation == "foreign_shaft":
            opposite = record.actions[-1].group_id
            action = replace(action, group_id=opposite)
        else:
            # Change targets, leaving the supplied resolved quantities coherent:
            # this isolates the exact six-component equilibrium guard.
            w = targets[action.group_id]
            if mutation == "force":
                w = replace(w, force=vector((Decimal(1), Decimal(0), Decimal(0)), Unit.N))
            else:
                w = replace(w, moment=vector((Decimal(0), Decimal(1), Decimal(0)), Unit.N_MM))
            targets = targets | {action.group_id: w}
        record = replace(record, actions=(action, *record.actions[1:]))
    with pytest.raises(ValueError, match=r"SSMC_(TRUSTED|SHAFT)"):
        validate(record, ownership, targets)


@pytest.mark.parametrize("check", tuple(PROPERTY_DIRECTIONS))
def test_no_property_lw_fallback_and_distinct_required_source_domains(check: str) -> None:
    missing = select_ssmc_property("test", check)
    assert missing.status == "SSMC_CW_SOURCE_REQUIRED"
    assert missing.authority is None
    assert not missing.isotropic
    assert not missing.longitudinal_strength_credit
    assert missing.owner == "MITER_WEB_PLATE"
    record = SSMCQualifiedProperty(
        "test",
        check,
        PROPERTY_DIRECTIONS[check],
        Q(Decimal(1), Unit.MPA),
        "a" * 64,
        "b" * 64,
        "TEST_ONLY",
        True,
    )
    if PROPERTY_DIRECTIONS[check] in {"ORTHOTROPIC", "QUALIFIED_METHOD"}:
        with pytest.raises(ValueError, match="SSMC_TRUSTED_AUTHORITY_NOT_BOUND"):
            select_ssmc_property("test", check, {("test", check): record})
        return
    bound = select_ssmc_property("test", check, {("test", check): record})
    assert bound.authority == record
    assert bound.status == "QUALIFIED_PROPERTY_BOUND_NOT_WHOLE_PLATE_RESISTANCE"


@pytest.mark.parametrize(
    "change",
    [
        {"owner": "HORIZONTAL_STRINGER"},
        {"policy": "LW"},
        {"isotropic": True},
        {"check": "invented"},
    ],
)
def test_plate_policy_cannot_escape_owner_or_invent_isotropy(change: dict[str, Any]) -> None:
    args = {"binding": "test", "check": "NORMAL_TENSION", "policy": PLATE_POLICY} | change
    with pytest.raises(ValueError, match="SSMC_CW_POLICY_INVALID"):
        select_ssmc_property(**args)


@pytest.mark.parametrize("alternate", [Q(Decimal("0.5"), Unit.MPA), Q(Decimal(1), Unit.IN), None])
def test_no_unapproved_cw_conservatism_or_automatic_lower_envelope(alternate: Q | None) -> None:
    record = SSMCQualifiedProperty(
        "test",
        "NORMAL_TENSION",
        "CW",
        Q(Decimal(1), Unit.MPA),
        "a" * 64,
        "b" * 64,
        "TEST_ONLY",
        alternate is not None,
        alternate,
    )
    result = select_ssmc_property("test", "NORMAL_TENSION", {("test", "NORMAL_TENSION"): record})
    assert result.status == "SSMC_CW_CONSERVATISM_CONFLICT"
    assert result.authority is None


def test_numerical_fail_then_unresolved_then_complete_status_precedence() -> None:
    assert required_design_status(("FAIL",), ("MISSING",)) == "FAIL"
    assert required_design_status((), ("MISSING",)) == "ENGINEERING_REVIEW_REQUIRED"
    assert required_design_status((), ()) == "PASS"


def test_nonzero_private_response_closure_without_production_activation() -> None:
    from frp_master_connection.calculation.angle_connector_core import shift_angle_wrench

    request = replace(
        map_ssmc_request(illustrative_ssmc()),
        N=Q.of(8, Unit.KIP),
        V=Q.of(-4, Unit.KIP),
        M=Q.of(20, Unit.KIP_IN),
    )
    demand = preview_ssmc(request)
    template, ownership, _ = response_fixture()
    targets = {g.group_id: g.plate_wrench for g in demand.groups}
    # Deliberately synthetic, asymmetric test oracle, not a physical response
    # method: first shaft owns the complete transported group wrench. The other
    # shafts have explicitly resolved zero actions. No such source is registered.
    actions = []
    first_ids = {next(s.id for s in demand.geometry.shafts if s.group == g) for g in targets}
    for shaft in demand.geometry.shafts:
        ref = vector(
            tuple(
                Decimal(str(v))
                for v in (
                    shaft.plate_midpoint.x,
                    shaft.plate_midpoint.y,
                    shaft.plate_midpoint.z,
                )
            ),
            request.length_unit,
        )
        wrench = shift_angle_wrench(targets[shaft.group], ref)
        if shaft.id not in first_ids:
            wrench = replace(
                wrench,
                force=vector((Decimal(0),) * 3, Unit.N),
                moment=vector((Decimal(0),) * 3, Unit.N_MM),
            )
        actions.append(SSMCResponseAction(shaft.id, shaft.group, wrench, "SHAFT"))
    action_by_id = {a.physical_id: a for a in actions}
    quantities = []
    for q in template.resolved_quantities:
        if q.owner_id in action_by_id:
            w = action_by_id[q.owner_id].wrench
            values = {
                "SHAFT_SHEAR": (w.force.x, w.force.z),
                "BOLT_AXIS_TENSION": (w.force.y,),
                "SHAFT_BENDING": (w.moment.x, w.moment.y, w.moment.z),
            }
            q = replace(q, values=values.get(q.mechanism, q.values))
        quantities.append(q)
    zero = vector((Decimal(0),) * 3, Unit.N)
    contact = SSMCResponseAction(
        "TEST_CONTACT",
        demand.groups[0].group_id,
        replace(
            demand.groups[0].plate_wrench, force=zero, moment=vector((Decimal(0),) * 3, Unit.N_MM)
        ),
        "CONTACT",
    )
    record = replace(
        template,
        binding=demand.engineering_fingerprint,
        applicability="SYNTHETIC_NONZERO_VALIDATOR_TEST_ONLY",
        actions=(*actions, contact),
        resolved_quantities=tuple(quantities),
    )
    validate_ssmc_response(
        record, record.binding, ownership, targets, demand.work_point_wrench.reference
    )
    bound = preview_ssmc(request, {record.binding: record})
    assert bound.trusted_complete_response == record
    assert bound.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert preview_ssmc(request).trusted_complete_response is None
    assert not EMPTY_RESPONSE_REGISTRY
