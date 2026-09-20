"""Stage 4.3 independent synthetic arithmetic, NOT production qualification."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
    sourced_modified_tensile_stress,
)
from frp_master_connection.calculation.support_attachment_response import (
    REQUIRED_COVERAGE,
    PhysicalResponseBolt,
    QualifiedSupportResponse,
    ResponseContactDomain,
    ShaftDemand,
    SupportResponseAction,
    SupportResponseBinding,
    prove_support_response,
    qualified_source,
    validate_support_response,
)
from frp_master_connection.domain.material_architecture import (
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    PropertySourceConfirmation,
)

MATRIX = json.loads(
    (Path(__file__).parents[1] / "golden/stage_4_3_acceptance_matrix_rc1.json").read_text(
        encoding="utf-8"
    )
)
FIXTURES: list[dict[str, Any]] = MATRIX["independent_fixtures"]


def q(value: str, unit: Unit = Unit.KIP) -> PhysicalQuantity:
    fraction = Fraction(value)
    return quantity_vector((fraction, Fraction(0), Fraction(0)), unit).x


def vec(values: list[str] | tuple[str, ...], unit: Unit) -> ExactQuantityVector3D:
    return quantity_vector(cast(Rational3, tuple(Fraction(x) for x in values)), unit)


def source() -> EngineeringPropertySource:
    return EngineeringPropertySource(
        EngineeringPropertySourceKind.TEST_QUALIFIED_DATA,
        "TEST_ONLY_NOT_CONSTRUCTION_AUTHORITY",
        "1",
        PropertySourceConfirmation.TEST_QUALIFIED,
        ("SYNTHETIC_TEST_ONLY",),
        True,
        "A" * 64,
        "TEST_ISSUER",
        ("TEST_QUALIFICATION",),
    )


def fixture_response(n: int = 0) -> tuple[SupportResponseBinding, QualifiedSupportResponse]:
    fixture = FIXTURES[n]
    target = AngleWrench(
        vec(fixture["reference"], Unit.IN),
        vec(fixture["expected_total"]["force"], Unit.KIP),
        vec(fixture["expected_total"]["moment"], Unit.KIP_IN),
    )
    actions = tuple(
        SupportResponseAction(
            item["id"],
            "GROUP",
            kind,
            vec(item["point"], Unit.IN),
            vec(item["force_on_support"], Unit.KIP),
            vec(("0", "0", "0"), Unit.KIP_IN),
            item["id"] if kind == "BOLT" else None,
            "LAYER",
        )
        for items, kind in ((fixture["bolts"], "BOLT"), (fixture["contacts"], "CONTACT"))
        for item in items
    )
    bolts = tuple(a for a in actions if a.kind == "BOLT")
    binding = SupportResponseBinding(
        "TEST_INPUT",
        "TEST_GEOMETRY",
        ("TEST_CORE",),
        "TEST_MATERIAL_FASTENER",
        tuple(
            PhysicalResponseBolt(a.action_id, "GROUP", a.point, a.point, ("LAYER",)) for a in bolts
        ),
        (("GROUP", target),),
        (
            ResponseContactDomain(
                "GROUP",
                q("0", Unit.IN),
                q("-2", Unit.IN),
                q("2", Unit.IN),
                q("-1", Unit.IN),
                q("1", Unit.IN),
                "LAYER",
            ),
        ),
        "TEST_ONLY",
        "TEST_FACE",
    )
    record = QualifiedSupportResponse(
        "TEST_ONLY",
        source(),
        "TEST_ISSUER",
        binding,
        actions,
        tuple(
            ShaftDemand(
                a.action_id,
                "SECTION",
                ("LAYER",),
                a.force.x,
                a.force.y,
                a.force.z,
                "SINGLE_PLANE_8_2_8_3",
                True,
            )
            for a in bolts
        ),
        ("SYNTHETIC_CONTACT_DOMAIN_NOT_CONSTRUCTION",),
        REQUIRED_COVERAGE,
        "TEST_ONLY",
        True,
    )
    return binding, record


@pytest.mark.parametrize("n", range(4), ids=[f"F43-R0{i}" for i in range(1, 5)])
def test_independent_exact_external_fixture_and_qualified_transport(n: int) -> None:
    binding, record = fixture_response(n)
    proof = prove_support_response(binding.group_targets[0][1], record.actions)
    assert proof.passed
    assert (
        components(proof.residual_force)
        == components(proof.residual_moment)
        == (Fraction(0), Fraction(0), Fraction(0))
    )
    assert proof.reconstructed == binding.group_targets[0][1]
    result = validate_support_response(binding, record)
    assert result.status == "VALID_QUALIFIED_RESPONSE"
    assert result.extra_prying_factor is None
    assert all(p.passed for _, p in result.group_proofs)
    assert not FIXTURES[n]["production_use_permitted"]


def test_f43_t01_independent_reference_shift() -> None:
    f = FIXTURES[4]
    incoming = AngleWrench(
        vec(f["from_reference"], Unit.IN),
        vec(f["input_force"], Unit.KIP),
        vec(f["input_moment"], Unit.KIP_IN),
    )
    result = shift_angle_wrench(incoming, vec(f["to_reference"], Unit.IN))
    assert result.force == vec(f["expected_force"], Unit.KIP)
    assert result.moment == vec(f["expected_moment"], Unit.KIP_IN)
    assert shift_angle_wrench(result, incoming.reference) == incoming
    assert not f["defines_support_profile_dimensions"]


def test_source_authorized_couple_is_validated_without_becoming_an_extra_bolt() -> None:
    binding, record = fixture_response(0)
    target = binding.group_targets[0][1]
    couple = SupportResponseAction(
        "EXPLICIT_COUPLE",
        binding.group_targets[0][0],
        "COUPLE",
        target.reference,
        vec(("0", "0", "0"), Unit.KIP),
        vec(("1", "2", "3"), Unit.KIP_IN),
    )
    target = replace(target, moment=couple.moment)
    binding = replace(binding, group_targets=((binding.group_targets[0][0], target),))
    record = replace(
        record,
        binding=binding,
        actions=(*record.actions, couple),
        authorized_couple_ids=(couple.action_id,),
    )
    assert validate_support_response(binding, record).status == "VALID_QUALIFIED_RESPONSE"


def test_t43_072_response_proofs_are_independent_of_ambient_decimal_precision() -> None:
    from decimal import ROUND_DOWN, localcontext

    binding, record = fixture_response(3)
    expected = validate_support_response(binding, record)
    for precision in (6, 28, 80, 120):
        with localcontext() as context:
            context.prec = precision
            context.rounding = ROUND_DOWN
            assert validate_support_response(binding, record) == expected


def test_f43_b01_source_unit_native_stress_boundary_exact() -> None:
    f = FIXTURES[5]
    nominal = q(f["inputs"]["Fnt"], Unit.KSI)
    shear = q(f["inputs"]["Fnv"], Unit.KSI)
    raw, modified = sourced_modified_tensile_stress(nominal, shear, q("20", Unit.KSI))
    assert raw == modified == q(f["expected"]["modified_nominal_tension_stress"], Unit.KSI)
    assert modified.magnitude * Decimal(".75") == Decimal("28.5")
    assert shear.magnitude * Decimal(".75") == Decimal("30")
    assert Decimal("28.5") <= modified.magnitude * Decimal(".75")
    assert Decimal("29") > modified.magnitude * Decimal(".75")
    assert sourced_modified_tensile_stress(nominal, shear, q("0", Unit.KSI))[1] == nominal
    # Negative Eq.8-3 result remains negative, never clamped to a passing zero.
    assert sourced_modified_tensile_stress(nominal, shear, q("100", Unit.KSI))[1].magnitude < 0
    force_trace = sourced_combined_bolt_resistance(q(".5", Unit.IN), nominal, shear, q("2"))
    independent = sourced_modified_tensile_stress(nominal, shear, force_trace.required_shear_stress)
    assert force_trace.modified_tensile_stress == independent[1]


@pytest.mark.parametrize("strengths", [("0", "40", "20"), ("60", "0", "20"), ("60", "40", "-1")])
def test_invalid_stress_signs_rejected(strengths: tuple[str, str, str]) -> None:
    with pytest.raises(ValueError, match="positive"):
        sourced_modified_tensile_stress(*(q(s, Unit.KSI) for s in strengths))


def test_invalid_stress_and_force_dimensions_rejected() -> None:
    with pytest.raises(ValueError, match="stress quantities"):
        sourced_modified_tensile_stress(q("60"), q("40", Unit.KSI), q("20", Unit.KSI))
    for bad in (q("-1"), q("2", Unit.IN)):
        with pytest.raises(ValueError, match="nonnegative force"):
            sourced_combined_bolt_resistance(
                q(".5", Unit.IN), q("60", Unit.KSI), q("40", Unit.KSI), bad
            )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("binding", "SOURCE_NOT_APPLICABLE"),
        ("issuer", "QUALIFICATION_PROVENANCE"),
        ("qualification", "QUALIFICATION_PROVENANCE"),
        ("domain", "STIFFNESS_DOMAIN"),
        ("boundary", "STIFFNESS_DOMAIN"),
        ("coverage", "COMPLETE_RESPONSE_COVERAGE"),
        ("prying", "COMPLETE_RESPONSE_COVERAGE"),
        ("missingbolt", "PHYSICAL_BOLT_COVERAGE"),
        ("duplicate", "PHYSICAL_BOLT_COVERAGE"),
        ("unknowngroup", "UNKNOWN_GROUP"),
        ("unknownbolt", "UNKNOWN_BOLT"),
        ("location", "LOCATION_OR_LAYER"),
        ("layer", "LOCATION_OR_LAYER"),
        ("contact", "CONTACT_OUTSIDE_PHYSICAL_DOMAIN"),
        ("section", "SHAFT_SECTION_COVERAGE"),
        ("duplicatesection", "SHAFT_SECTION_COVERAGE"),
        ("unknownsectionbolt", "SHAFT_DEMAND_OR_LAYER"),
        ("emptysection", "SHAFT_DEMAND_OR_LAYER"),
        ("emptylayer", "SHAFT_DEMAND_OR_LAYER"),
        ("badlayer", "SHAFT_DEMAND_OR_LAYER"),
        ("dimension", "SHAFT_DEMAND_OR_LAYER"),
        ("negative", "SHAFT_DEMAND_OR_LAYER"),
        ("bending", "SECONDARY_BOLT_BENDING"),
    ],
)
def test_source_response_fail_closed(mutation: str, reason: str) -> None:
    binding, r = fixture_response(1)
    a, d = r.actions[0], r.shaft_demands[0]
    edits: dict[str, Any] = {
        "binding": {"binding": replace(binding, selected_face="DIFFERENT")},
        "issuer": {"issuer": " "},
        "qualification": {
            "source": replace(r.source, confirmation=PropertySourceConfirmation.CONFIRMED)
        },
        "domain": {"domain": ""},
        "boundary": {"contact_stiffness_boundary_assumptions": ()},
        "coverage": {"coverage": ()},
        "prying": {"prying_included_in_total": False},
        "missingbolt": {"actions": r.actions[1:]},
        "duplicate": {"actions": (*r.actions, a)},
        "unknowngroup": {"actions": (replace(a, group_id="UNKNOWN"), *r.actions[1:])},
        "unknownbolt": {"actions": (replace(a, bolt_id="UNKNOWN"), *r.actions[1:])},
        "location": {"actions": (replace(a, point=vec(("9", "0", "0"), Unit.IN)), *r.actions[1:])},
        "layer": {"actions": (replace(a, layer_id="UNKNOWN"), *r.actions[1:])},
        "contact": {
            "actions": (
                *r.actions[:-1],
                replace(r.actions[-1], point=vec(("9", "0", "0"), Unit.IN)),
            )
        },
        "section": {"shaft_demands": ()},
        "duplicatesection": {"shaft_demands": (*r.shaft_demands, d)},
        "unknownsectionbolt": {
            "shaft_demands": (replace(d, bolt_id="UNKNOWN"), *r.shaft_demands[1:])
        },
        "emptysection": {"shaft_demands": (replace(d, section_id=""), *r.shaft_demands[1:])},
        "emptylayer": {"shaft_demands": (replace(d, layer_ids=()), *r.shaft_demands[1:])},
        "badlayer": {"shaft_demands": (replace(d, layer_ids=("UNKNOWN",)), *r.shaft_demands[1:])},
        "dimension": {"shaft_demands": (replace(d, force_u=q("1", Unit.IN)), *r.shaft_demands[1:])},
        "negative": {"shaft_demands": (replace(d, tensile_demand=q("-1")), *r.shaft_demands[1:])},
        "bending": {
            "shaft_demands": (replace(d, secondary_bending_covered=False), *r.shaft_demands[1:])
        },
    }
    result = validate_support_response(binding, replace(r, **edits[mutation]))
    assert result.status == "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE"
    assert any(reason in value for value in result.reasons)


def test_missing_source_and_unilateral_contact_reversal_are_not_abs_repaired() -> None:
    binding, r = fixture_response(1)
    assert validate_support_response(binding, None).status == "SOURCE_REQUIRED"
    assert not qualified_source(replace(source(), qualification_record_ids=()))
    flipped = tuple(
        replace(
            a,
            force=quantity_vector(cast(Rational3, tuple(-x for x in components(a.force))), Unit.N),
        )
        for a in r.actions
    )
    target = replace(binding.group_targets[0][1], moment=vec(("0", "24", "0"), Unit.KIP_IN))
    proof = prove_support_response(target, flipped)
    assert not proof.passed
    assert "INVALID_BOLT_ID_OR_NEGATIVE_TENSION" in proof.reasons
    assert "INVALID_COMPRESSION_CONTACT" in proof.reasons
    # R03 is an independently specified opposite active set, not negated R02 tensions.
    reverse_binding, reverse = fixture_response(2)
    assert prove_support_response(reverse_binding.group_targets[0][1], reverse.actions).passed


def test_unknown_action_duplicate_and_source_authorized_couple() -> None:
    binding, r = fixture_response()
    target = binding.group_targets[0][1]
    a = r.actions[0]
    assert (
        "UNKNOWN_RESPONSE_ACTION_KIND"
        in prove_support_response(target, (replace(a, kind="OTHER"),)).reasons
    )
    assert (
        "DUPLICATE_EXTERNAL_ACTION_OR_BOLT"
        in prove_support_response(target, (*r.actions, a)).reasons
    )
    couple = SupportResponseAction(
        "COUPLE",
        "GROUP",
        "COUPLE",
        target.reference,
        vec(("0", "0", "0"), Unit.KIP),
        vec(("0", "0", "2"), Unit.KIP_IN),
    )
    assert (
        "UNAUTHORIZED_EXTERNAL_COUPLE"
        in prove_support_response(target, (*r.actions, couple)).reasons
    )
    assert (
        "UNAUTHORIZED_BALANCING_COUPLE"
        in prove_support_response(target, (*r.actions, couple)).reasons
    )
    with_couple = replace(target, moment=vec(("0", "0", "2"), Unit.KIP_IN))
    assert prove_support_response(
        with_couple, (*r.actions, couple), authorized_couple_ids=("COUPLE",)
    ).passed
