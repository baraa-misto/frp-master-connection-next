"""Fail-closed geometry/source/contact paths and native local applicability."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from typing import cast

import pytest

from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
    evaluate_column_zone,
)
from frp_master_connection.application.angle_column_base_geometry import resolve_angle_base_geometry
from frp_master_connection.application.angle_column_base_local import (
    connector_group_mapping,
    connector_group_paths,
    member_local_checks,
)
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    preview_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_qualification import (
    find_member_response,
    validate_member_response,
)
from frp_master_connection.application.angle_column_base_sources import AngleBaseSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    ColumnPressurePatch,
    QualifiedFootBreakdown,
    base_fingerprint,
    cross,
    subtract,
    validate_base_response,
    validate_foot_breakdown,
)
from frp_master_connection.calculation.angle_connector_core import (
    components,
    quantity_vector,
    resolve_angle_connector,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import SupportResponseAction
from frp_master_connection.domain.angle_column_moment_base import AngleColumnMomentBaseRequest
from tests.application.angle_column_base_fixture import complete_sources
from tests.application.test_angle_column_moment_base import request, synthetic_response
from tests.calculation.test_support_attachment_response import source


def q(value: str, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


@pytest.fixture
def full() -> tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry]:
    return complete_sources(request())


@pytest.mark.parametrize(
    "case", ["force_unit", "thickness", "material", "untrusted_strength", "patch_unit"]
)
def test_domain_rejects_unsupported_physical_authority(case: str) -> None:
    r = request()

    def invalid() -> None:
        if case == "force_unit":
            replace(r.actions, axial=q("1"))
        elif case == "thickness":
            replace(r.column, thickness=q("8"))
        elif case == "material":
            replace(r.column, material_id="316SS")
        elif case == "untrusted_strength":
            replace(
                r.leg_1,
                angle=replace(
                    r.leg_1.angle,
                    fastener=replace(
                        r.leg_1.angle.fastener, nominal_shear_stress=q("100", Unit.MPA)
                    ),
                ),
            )
        else:
            ColumnPressurePatch("bad", q("1", Unit.N), q("2"), q("0"), q("1"), q("1", Unit.MPA))

    with pytest.raises(
        ValueError, match=r"Finite|thickness|material|SOURCE_REQUIRED|Contact bounds"
    ):
        invalid()


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("pedestal", "COLUMN_END_NOT_CONTAINED_IN_FOUNDATION"),
        ("diameter", "BOLT_DIAMETER_OUTSIDE_ASCE_8_2_RANGE"),
        ("relief", "HEEL_END_RELIEF_OUTSIDE_4_4_PRESET_DOMAIN"),
        ("leg_miss", "MEMBER_BOLT_PATH:"),
        ("member_near_heel", "MEMBER_HOLE_WASHER_FILLET_SEATING_REQUIRED"),
        ("member_overlap", "MEMBER_HOLE_WASHER_ENVELOPES_OVERLAP"),
        ("embedment", "GEOMETRIC_EMBEDMENT_EXCEEDS_PEDESTAL_DEPTH"),
        ("foot_heel", "FOUNDATION_HOLE_WASHER_FILLET_SEATING_REQUIRED"),
        ("anchor_overlap", "FOUNDATION_HOLE_WASHER_ENVELOPES_OVERLAP"),
        ("long_foot", "CONNECTOR_FOOT_NOT_CONTAINED_IN_FOUNDATION"),
        ("solid_interference", "COLUMN_CONNECTOR_FOUNDATION_SOLID_INTERFERENCE"),
    ],
)
def test_physical_envelopes_fail_closed_without_repositioning(case: str, reason: str) -> None:
    r = request()
    c, a = r.leg_1, r.leg_1.angle
    if case == "pedestal":
        r = replace(r, foundation=replace(r.foundation, width_x=q("10"), width_y=q("10")))
    elif case == "diameter":
        c = replace(c, angle=replace(a, fastener=replace(a.fastener, bolt_diameter=q(".3"))))
    elif case == "relief":
        c = replace(
            c, angle=replace(a, geometry=replace(a.geometry, heel_end_reliefs=(q(".1"), q(".1"))))
        )
    elif case == "leg_miss":
        c = replace(c, extrusion_center=q("20"))
    elif case == "member_near_heel":
        c = replace(c, angle=replace(a, member_pattern=replace(a.member_pattern, center=q("1"))))
    elif case == "member_overlap":
        c = replace(c, angle=replace(a, member_pattern=replace(a.member_pattern, pitch=q(".5"))))
    elif case == "embedment":
        c = replace(c, angle=replace(a, anchors=replace(a.anchors, specified_embedment=q("15"))))
    elif case == "foot_heel":
        c = replace(c, angle=replace(a, support_pattern=replace(a.support_pattern, center=q("1"))))
    elif case == "anchor_overlap":
        c = replace(c, angle=replace(a, support_pattern=replace(a.support_pattern, pitch=q(".5"))))
    elif case == "solid_interference":
        c = replace(c, extrusion_center=q("0"))
        r = replace(r, leg_2=replace(r.leg_2, extrusion_center=q("0")))
    else:
        c = replace(c, angle=replace(a, geometry=replace(a.geometry, support_leg=q("20"))))
    changed = replace(r, leg_1=c)
    g = resolve_angle_base_geometry(changed)
    assert g.status == "INVALID_GEOMETRY"
    assert any(reason in r for r in g.reasons), g.reasons
    d = evaluate_angle_column_moment_base(changed)
    assert d.status == "INVALID_GEOMETRY"
    assert not d.resistance_evaluated


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("source", "QUALIFIED_BASE_RESPONSE_PROVENANCE_REQUIRED"),
        ("coverage", "BASE_RESPONSE_COMPATIBILITY_CONTACT_NORMAL_COVERAGE_REQUIRED"),
        ("empty_id", "DUPLICATE_OR_MISSING_CONTACT_PATCH_ID"),
        ("overlap", "OVERLAPPING_CONTACT_PATCHES_DOUBLE_COUNT_PRESSURE"),
        ("tension", "INVALID_CONTACT_PATCH_OR_TENSILE_PRESSURE"),
        ("outside", "CONTACT_PRESSURE_OUTSIDE_REAL_L_FOOTPRINT"),
        ("inactive_nonzero", "NONZERO_BRANCH_MARKED_INACTIVE"),
        ("wrong_ref", "DIRECT_CONTACT_REPORT_REFERENCE_MISMATCH"),
        ("inactive_contact", "NONZERO_CONTACT_MARKED_INACTIVE"),
    ],
)
def test_complete_base_qualification_cannot_hide_contact_or_domain_errors(
    case: str,
    reason: str,
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    _, p, s = full
    record = s.responses[0]
    patch = record.pressure_patches[0]
    if case == "source":
        record = replace(record, issuer="")
    elif case == "coverage":
        record = replace(record, coverage=())
    elif case == "empty_id":
        record = replace(record, pressure_patches=(replace(patch, patch_id=""),))
    elif case == "overlap":
        record = replace(record, pressure_patches=(patch, replace(patch, patch_id="overlap")))
    elif case == "tension":
        record = replace(
            record, pressure_patches=(replace(patch, compressive_pressure=q("-.1", Unit.MPA)),)
        )
    elif case == "outside":
        record = replace(record, pressure_patches=(replace(patch, y_max=q("100", Unit.MM)),))
    elif case == "inactive_nonzero":
        record = replace(
            record,
            branches=(replace(record.branches[0], inactive_certificate="bad"), record.branches[1]),
        )
    elif case == "wrong_ref":
        record = replace(
            record,
            column_on_foundation_contact=replace(
                record.column_on_foundation_contact,
                reference=replace(record.column_on_foundation_contact.reference, x=q("1", Unit.MM)),
            ),
        )
    else:
        record = replace(record, contact_inactive_certificate="bad")
    value = validate_base_response(p.response_binding, record)
    assert reason in value.reasons
    assert not value.qualified
    assert value.response is None


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("binding", "MEMBER_RESPONSE_EXACT_DOMAIN_BINDING_MISMATCH"),
        ("source", "MEMBER_RESPONSE_PROVENANCE_COMPATIBILITY_REQUIRED"),
        ("coverage", "MEMBER_RESPONSE_COMPLETE_NORMAL_PRYING_COVERAGE_REQUIRED"),
        ("native", "NATIVE_IN_PLANE_RESULT_NOT_BOUND"),
        ("shafts", "EXACT_PHYSICAL_BOLT_ACTION_AND_SHAFT_SET_REQUIRED"),
        ("unknown_group", "MEMBER_ACTION_GROUP_NOT_BOUND"),
        ("bolt_point", "BOLT_ACTION_PHYSICAL_POINT_MISMATCH"),
        ("contact_point", "MEMBER_CONTACT_OUTSIDE_PHYSICAL_OVERLAP"),
        ("inplane_force", "NORMAL_SOURCE_CANNOT_REPLACE_IN_PLANE_SLICE8_ACTION"),
        ("inplane_moment", "NORMAL_SOURCE_CANNOT_REPLACE_IN_PLANE_FREE_MOMENT"),
        ("shaft_coverage", "PHYSICAL_SINGLE_INTERFACE_SHAFT_COVERAGE_REQUIRED"),
        ("normal_force", "SHAFT_DEMAND_DOES_NOT_MATCH_EXTERNAL_BOLT_ACTION"),
        ("unknown_kind", "UNKNOWN_RESPONSE_ACTION_KIND"),
    ],
)
def test_member_normal_response_is_bound_and_separate_from_native_inplane(
    case: str,
    reason: str,
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    _, p, s = full
    record = s.member_responses[0]
    binding = record.binding
    action, shaft = record.actions[0], record.shaft_demands[0]
    if case == "binding":
        binding = replace(binding, support_mode="WRONG")
    elif case == "source":
        record = replace(record, issuer="")
    elif case == "coverage":
        record = replace(record, prying_included_in_total=False)
    elif case == "native":
        binding = replace(binding, native_core_fingerprints=())
    elif case == "shafts":
        record = replace(
            record, shaft_demands=(*record.shaft_demands, replace(shaft, bolt_id="unknown"))
        )
    elif case == "unknown_group":
        record = replace(record, actions=(replace(action, group_id="unknown"), *record.actions[1:]))
    elif case == "bolt_point":
        record = replace(
            record,
            actions=(
                replace(action, point=replace(action.point, x=q("1000", Unit.MM))),
                *record.actions[1:],
            ),
        )
    elif case == "contact_point":
        record = replace(
            record,
            actions=(
                *record.actions[:-1],
                replace(
                    record.actions[-1],
                    point=replace(record.actions[-1].point, x=q("1000", Unit.MM)),
                ),
            ),
        )
    elif case == "inplane_force":
        record = replace(
            record,
            actions=(
                replace(action, force=replace(action.force, x=q("1", Unit.N))),
                *record.actions[1:],
            ),
        )
    elif case == "inplane_moment":
        record = replace(
            record,
            actions=(
                replace(action, moment=replace(action.moment, z=q("1", Unit.N_MM))),
                *record.actions[1:],
            ),
        )
    elif case == "shaft_coverage":
        record = replace(
            record,
            shaft_demands=(
                replace(shaft, secondary_bending_covered=False),
                *record.shaft_demands[1:],
            ),
        )
    elif case == "unknown_kind":
        record = replace(
            record, actions=(*record.actions[:-1], replace(record.actions[-1], kind="UNKNOWN"))
        )
    else:
        record = replace(
            record,
            shaft_demands=(
                replace(shaft, tensile_demand=q("0", Unit.N)),
                *record.shaft_demands[1:],
            ),
        )
    checked = validate_member_response(binding, record, p.transfers[0].in_plane_demand)
    assert reason in checked.reasons
    assert not checked.shafts
    assert checked.record is None


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("domain", "COLUMN_END_ZONE_SOURCE_DOMAIN_NOT_APPLICABLE"),
        ("coverage", "COLUMN_END_ZONE_REQUIRED_COVERAGE_MISSING"),
        ("duplicate", "COLUMN_END_ZONE_DUPLICATE_CHECK"),
        ("invalid", "COLUMN_END_ZONE_QUALIFIED_CHECK_INVALID"),
    ],
)
def test_common_column_zone_rejects_invalid_qualified_records(
    case: str,
    reason: str,
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    _, p, s = full
    zone = s.zones[0]
    if case == "domain":
        zone = replace(zone, exact_binding="wrong")
    elif case == "coverage":
        zone = replace(zone, checks=())
    elif case == "duplicate":
        zone = replace(zone, checks=zone.checks * 2)
    else:
        zone = replace(zone, checks=(replace(zone.checks[0], design_capacity=q("0", Unit.N)),))
    value = evaluate_column_zone(p, replace(s, zones=(zone,)), ())
    assert reason in value.reasons
    assert value.status == "SOURCE_REQUIRED"
    assert not value.comparisons


def test_missing_bolt_strength_uses_native_shear_not_another_projection(
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    r, p, s = full
    d = evaluate_angle_column_moment_base(r, replace(s, fasteners=()))
    assert all(b.status == "SOURCE_REQUIRED" for b in d.member_bolts)
    for transfer in p.transfers:
        for bolt in transfer.in_plane_demand.solution.projected_bolts():
            actual = next(
                b for b in d.member_bolts if b.bolt_id == f"{transfer.connector_id}:{bolt.bolt_id}"
            )
            assert actual.shear_magnitude == bolt.total_force_magnitude


def test_native_qualified_zone_failure_remains_visible(
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    r, _, s = full
    zone = s.zones[0]
    s = replace(s, zones=(replace(zone, checks=(replace(zone.checks[0], demand=q("3", Unit.N)),)),))
    d = evaluate_angle_column_moment_base(r, s)
    assert d.status == "FAIL"
    assert "COMMON_COLUMN_END_ZONE" in d.failed_check_ids


def test_changed_member_reference_and_unjustified_inactive_branch_fail() -> None:
    r = replace(request(), response_source_reference="TEST_ONLY")
    p, s = synthetic_response(r)
    record = s.responses[0]
    one, two = record.branches
    bad = replace(
        record,
        branches=(
            replace(
                one,
                member_action=replace(
                    one.member_action,
                    reference=replace(one.member_action.reference, x=q("1", Unit.MM)),
                ),
            ),
            replace(two, inactive_certificate=None),
        ),
    )
    checked = validate_base_response(p.response_binding, bad)
    assert "MEMBER_BRANCH_FRAME_LEG_OR_REFERENCE_MISMATCH" in checked.reasons
    assert "EXPLICIT_INACTIVE_BRANCH_CERTIFICATE_REQUIRED" in checked.reasons
    assert not checked.qualified


def test_native_body_and_attachment_failures_cannot_be_hidden(
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    r, _, s = full
    records = tuple(
        replace(
            record,
            package=replace(
                record.package,
                strengths=tuple(
                    replace(
                        strength,
                        positive=replace(
                            cast(PhysicalQuantity, strength.positive), magnitude=Decimal(".00001")
                        ),
                        negative=replace(
                            cast(PhysicalQuantity, strength.negative), magnitude=Decimal(".00001")
                        ),
                    )
                    for strength in record.package.strengths
                ),
            ),
        )
        for record in s.connector_sources.records
    )
    d = evaluate_angle_column_moment_base(
        r, replace(s, connector_sources=replace(s.connector_sources, records=records))
    )
    assert d.status == "FAIL"
    assert "LEG_1_BASE_ANGLE:BODY" in d.failed_check_ids
    assert "LEG_2_BASE_ANGLE:MEMBER_ATTACHMENT" in d.failed_check_ids


def test_attachment_coverage_and_registry_identity_are_not_optional(
    full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry],
) -> None:
    r, _, s = full
    records = s.connector_sources.records
    d = evaluate_angle_column_moment_base(
        r,
        replace(
            s,
            connector_sources=replace(
                s.connector_sources,
                records=tuple(
                    replace(v, attachment_coverage=()) if v.attachment else v for v in records
                ),
            ),
        ),
    )
    assert all("COVERAGE_MISSING" in a.check.status for a in d.member_attachment_results)
    with pytest.raises(ValueError, match="unique"):
        replace(s, responses=s.responses * 2)
    assert base_fingerprint({"rational": Decimal("1")}) == base_fingerprint(
        {"rational": Decimal("1.0")}
    )


@pytest.mark.parametrize(
    ("force_a", "force_b", "across", "hole"),
    [
        ("100", "0", 2, ".563"),
        ("-100", "0", 2, ".563"),
        ("100", "0", 2, ".5625"),
        ("0", "100", 2, ".563"),
        ("100", "0", 1, ".563"),
    ],
)
def test_native_concentric_local_paths_use_actual_column_and_connector_axes(
    force_a: str, force_b: str, across: int, hole: str
) -> None:
    r = request()
    a = r.leg_1.angle
    r = replace(
        r,
        leg_1=replace(
            r.leg_1,
            angle=replace(
                a,
                member_pattern=replace(a.member_pattern, across=across),
                fastener=replace(a.fastener, hole_diameter=q(hole)),
            ),
        ),
    )
    _, p, _ = complete_sources(r)
    t = p.transfers[0]
    action = replace(
        t.core.request.member_action,
        force=replace(
            t.core.request.member_action.force, x=q(force_a, Unit.N), y=q(force_b, Unit.N)
        ),
        moment=replace(t.core.request.member_action.moment, z=q("0", Unit.N_MM)),
    )
    ip = replace(t.in_plane_input, force_a=force_a, force_b=force_b, moment_c="0")
    t = replace(
        t,
        core=resolve_angle_connector(replace(t.core.request, member_action=action)),
        in_plane_input=ip,
        in_plane_demand=calculate_in_plane_wrench_demand(ip),
    )
    checks = member_local_checks(p, t, find_member_response(p, t, AngleBaseSourceRegistry()))
    bearing = [c for c in checks if c.check_id.startswith("PIN_BEARING")]
    assert bearing
    assert all(c.native_trace is not None for c in bearing)
    assert {c.material_direction for c in bearing} == {"LONGITUDINAL", "TRANSVERSE"}
    paths = connector_group_paths(p, t)
    if force_b == "0" and across == 2 and hole == ".563":
        assert any(c.native_trace is not None for c in paths), paths
    else:
        assert paths[-1].status == "SOURCE_REQUIRED"
    mapping = connector_group_mapping(p, t)
    assert mapping is not None


def furnished_foot_record(p: AngleBasePreview) -> QualifiedFootBreakdown:
    """Explicit TEST ONLY external source with an expressly authorized free couple.

    This is a validation fixture, not a physical anchor solution or a production
    distribution rule. Its independent source stipulates its fixture boundary.
    """
    domain = p.foundation_breakdowns[0].domain
    target = domain.parent_wrench
    force = components(target.force)
    moment = components(target.moment)
    zero = quantity_vector(ZERO, Unit.N_MM)
    actions = []
    first = domain.anchor_points[0][1]
    for i, (identity, point) in enumerate(domain.anchor_points):
        f = (force[0], force[1], max(force[2], Fraction(0))) if i == 0 else ZERO
        actions.append(
            SupportResponseAction(
                identity,
                f"{domain.connector_id}_FOUNDATION_GROUP",
                "BOLT",
                point,
                quantity_vector(f, Unit.N),
                zero,
                identity,
                "FOUNDATION",
            )
        )
    contact = (Fraction(0), Fraction(0), min(force[2], Fraction(0)))
    actions.append(
        SupportResponseAction(
            "FOOT_CONTACT",
            f"{domain.connector_id}_FOUNDATION_GROUP",
            "CONTACT",
            first,
            quantity_vector(contact, Unit.N),
            zero,
            None,
            "FOUNDATION",
        )
    )
    residual = subtract(
        moment, cross(subtract(components(first), components(target.reference)), force)
    )
    actions.append(
        SupportResponseAction(
            "TEST_FIXTURE_COUPLE",
            f"{domain.connector_id}_FOUNDATION_GROUP",
            "COUPLE",
            target.reference,
            quantity_vector(ZERO, Unit.N),
            quantity_vector(residual, Unit.N_MM),
            None,
            "FOUNDATION",
        )
    )
    return QualifiedFootBreakdown(
        "TEST_FOOT_SOURCE",
        source(),
        "TEST_ISSUER",
        domain,
        tuple(actions),
        "TEST_ONLY_STIPULATED_FIXTURE",
        ("TEST_FIXTURE_COUPLE",),
    )


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "duplicate",
        "domain",
        "source",
        "anchors",
        "group",
        "layer",
        "point",
        "contact",
        "equilibrium",
        "unknown_connector",
    ],
)
def test_furnished_foot_breakdown_requires_exact_parent_and_never_enters_total_twice(
    case: str, full: tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry]
) -> None:
    r, p, s = full
    record = furnished_foot_record(p)
    domain = record.domain
    action = record.actions[0]
    if case == "domain":
        record = replace(record, domain=replace(domain, native_core_fingerprint="wrong"))
    elif case == "source":
        record = replace(record, issuer="")
    elif case == "anchors":
        record = replace(record, actions=record.actions[1:])
    elif case == "group":
        record = replace(record, actions=(replace(action, group_id="other"), *record.actions[1:]))
    elif case == "layer":
        record = replace(record, actions=(replace(action, layer_id="other"), *record.actions[1:]))
    elif case == "point":
        record = replace(
            record,
            actions=(
                replace(action, point=replace(action.point, z=q("1", Unit.MM))),
                *record.actions[1:],
            ),
        )
    elif case == "contact":
        record = replace(
            record,
            actions=(
                *record.actions[:-2],
                replace(
                    record.actions[-2],
                    point=replace(record.actions[-2].point, x=q("1000", Unit.MM)),
                ),
                record.actions[-1],
            ),
        )
    elif case == "equilibrium":
        record = replace(record, actions=record.actions[:-1])
    elif case == "unknown_connector":
        record = replace(record, domain=replace(domain, connector_id="other"))
    records = (record, record) if case == "duplicate" else (record,)
    if case == "unknown_connector":
        assert (
            "FOOT_BREAKDOWN_UNKNOWN_CONNECTOR"
            in validate_base_response(
                p.response_binding, replace(s.responses[0], foot_breakdowns=records)
            ).reasons
        )
        return
    checked = validate_foot_breakdown(domain, records)
    assert checked.proof is not None
    if case == "valid":
        assert checked.status == "VALID_QUALIFIED_RESPONSE"
        assert checked.proof.passed
        supplied = replace(s, responses=(replace(s.responses[0], foot_breakdowns=records),))
        actual = preview_angle_column_moment_base(r, supplied)
        assert actual.foundation_breakdowns[0].record == record
        assert actual.assembled_foundation_action == p.assembled_foundation_action
        assert actual.assembled_force_residual == p.assembled_force_residual
        assert actual.assembled_moment_residual == p.assembled_moment_residual
        assert (
            f"{domain.connector_id}:FOUNDATION_BREAKDOWN",
            "VALID_QUALIFIED_RESPONSE",
        ) in evaluate_angle_column_moment_base(r, supplied).scope_statuses
    else:
        assert checked.status == "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE"
        assert checked.record is None
        assert checked.reasons
