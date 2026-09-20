"""Fail-closed physical/source/capacity boundaries, not permissive aggregate qualification."""

from dataclasses import replace
from fractions import Fraction
from typing import cast

import pytest

from frp_master_connection.application.column_moment_base_design import evaluate_column_moment_base
from frp_master_connection.application.column_moment_base_preview import preview_column_moment_base
from frp_master_connection.application.column_moment_base_sources import ColumnMomentSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import ZERO, ColumnPressurePatch
from frp_master_connection.calculation.angle_connector_core import quantity_vector
from frp_master_connection.calculation.column_moment_base_response import (
    validate_column_base_response,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.column_moment_base import Family, Layout
from tests.application.column_moment_base_fixtures import complete_sources, response_sources
from tests.application.test_column_moment_base_preview import request


@pytest.mark.parametrize(
    "change",
    [
        "method",
        "binding",
        "source_reference",
        "issuer",
        "compatibility",
        "coverage",
        "signed_domain",
        "missing_branch",
        "duplicate_branch",
        "extra_branch",
        "branch_domain",
        "branch_reference",
        "false_inactive",
        "missing_bolt",
        "duplicate_bolt",
        "unknown_bolt",
        "wrong_layer_order",
        "missing_layer",
        "unknown_layer",
        "layer_reference",
        "layer_couple",
        "tensile_absent",
        "negative_tension",
        "length_tension",
        "wrong_section",
        "missing_section",
        "duplicate_section",
        "empty_section_id",
        "section_force",
        "section_basis",
        "section_bending",
        "section_capacity",
        "section_negative",
        "section_dimension",
        "response_model",
        "bolt_basis",
        "unauthorized_couple",
        "layer_force",
        "layer_moment",
        "contact_reference",
        "contact_active",
        "contact_wrench",
        "void_patch",
        "negative_pressure",
        "empty_binding_faces",
        "wrong_profile",
    ],
)
def test_source_admissibility_and_binding_rejects_mutation(change: str) -> None:
    r, p, s = response_sources(request("RHS8"))
    original = s.responses[0]
    rec = original
    branch = rec.branches[0]
    bolt = rec.bolts[0]
    layer = bolt.layers[0]
    section = bolt.sections[0]
    v = quantity_vector((Fraction(1), Fraction(2), Fraction(3)), Unit.N)
    binding = p.response_binding
    if change == "method":
        rec = replace(rec, method="STAGE44")
    elif change == "binding":
        rec = replace(rec, binding=replace(binding, geometry_fingerprint="changed"))
    elif change == "source_reference":
        rec = replace(rec, reference="")
    elif change == "issuer":
        rec = replace(rec, issuer="")
    elif change == "compatibility":
        rec = replace(rec, compatibility_stiffness_contact_basis="")
    elif change == "coverage":
        rec = replace(rec, coverage=())
    elif change == "signed_domain":
        rec = replace(rec, signed_load_domain="")
    elif change == "missing_branch":
        rec = replace(rec, branches=rec.branches[1:])
    elif change == "duplicate_branch":
        rec = replace(rec, branches=(branch, *rec.branches))
    elif change == "extra_branch":
        rec = replace(
            rec,
            branches=(
                *rec.branches,
                replace(branch, domain=replace(branch.domain, connector_id="OTHER")),
            ),
        )
    elif change == "branch_domain":
        rec = replace(
            rec,
            branches=(
                replace(branch, domain=replace(branch.domain, connector_id="OTHER")),
                *rec.branches[1:],
            ),
        )
    elif change == "branch_reference":
        rec = replace(
            rec,
            branches=(
                replace(
                    branch,
                    member_action=replace(
                        branch.member_action, reference=quantity_vector(ZERO, Unit.MM)
                    ),
                ),
                *rec.branches[1:],
            ),
        )
    elif change == "false_inactive":
        rec = replace(
            rec, branches=(replace(branch, inactive_certificate="inactive"), *rec.branches[1:])
        )
    elif change == "missing_bolt":
        rec = replace(rec, bolts=rec.bolts[1:])
    elif change == "duplicate_bolt":
        rec = replace(rec, bolts=(bolt, *rec.bolts))
    elif change == "unknown_bolt":
        rec = replace(rec, bolts=(replace(bolt, bolt_id="UNKNOWN"), *rec.bolts[1:]))
    elif change == "wrong_layer_order":
        bolt = replace(bolt, layers=tuple(reversed(bolt.layers)))
    elif change == "missing_layer":
        bolt = replace(bolt, layers=bolt.layers[1:])
    elif change == "unknown_layer":
        layer = replace(layer, layer_id="UNKNOWN")
    elif change == "layer_reference":
        layer = replace(
            layer, action=replace(layer.action, reference=quantity_vector(ZERO, Unit.MM))
        )
    elif change == "layer_couple":
        bolt = replace(bolt, authorized_layer_couple_ids=())
    elif change == "tensile_absent":
        layer = replace(layer, attachment_tensile_demand=None)
    elif change == "negative_tension":
        layer = replace(layer, attachment_tensile_demand=PhysicalQuantity.of(-1, Unit.N))
    elif change == "length_tension":
        layer = replace(layer, attachment_tensile_demand=PhysicalQuantity.of(1, Unit.MM))
    elif change == "wrong_section":
        section = replace(section, after_layer_id="UNKNOWN")
    elif change == "missing_section":
        bolt = replace(bolt, sections=())
    elif change == "duplicate_section":
        bolt = replace(bolt, sections=(section, *bolt.sections))
    elif change == "empty_section_id":
        section = replace(section, section_id="")
    elif change == "section_force":
        section = replace(section, force_on_upstream=v)
    elif change == "section_basis":
        section = replace(section, normal_response_basis="")
    elif change == "section_bending":
        section = replace(section, secondary_bending_covered=False)
    elif change == "section_capacity":
        section = replace(section, native_capacity_applicability="")
    elif change == "section_negative":
        section = replace(section, tensile_demand=PhysicalQuantity.of(-1, Unit.N))
    elif change == "section_dimension":
        section = replace(section, tensile_demand=PhysicalQuantity.of(1, Unit.MM))
    elif change == "response_model":
        bolt = replace(bolt, response_model="TWO_INDEPENDENT_SINGLE_LAPS")
    elif change == "bolt_basis":
        bolt = replace(bolt, compatibility_basis="")
    elif change == "unauthorized_couple":
        bolt = replace(bolt, authorized_layer_couple_ids=("UNKNOWN",))
    elif change == "layer_force":
        layer = replace(layer, action=replace(layer.action, force=v))
    elif change == "layer_moment":
        layer = replace(
            layer, action=replace(layer.action, moment=quantity_vector(ZERO, Unit.N_MM))
        )
    elif change == "contact_reference":
        rec = replace(
            rec,
            column_on_foundation_contact=replace(
                rec.column_on_foundation_contact,
                reference=quantity_vector((Fraction(1), Fraction(0), Fraction(0)), Unit.MM),
            ),
        )
    elif change == "contact_active":
        rec = replace(rec, pressure_patches=(), contact_inactive_certificate="inactive")
    elif change == "contact_wrench":
        rec = replace(
            rec, column_on_foundation_contact=replace(rec.column_on_foundation_contact, force=v)
        )
    elif change == "void_patch":
        rec = replace(
            rec,
            pressure_patches=(
                ColumnPressurePatch(
                    "VOID",
                    PhysicalQuantity.of(-1, Unit.MM),
                    PhysicalQuantity.of(1, Unit.MM),
                    PhysicalQuantity.of(-1, Unit.MM),
                    PhysicalQuantity.of(1, Unit.MM),
                    PhysicalQuantity.of(1, Unit.MPA),
                ),
            ),
        )
    elif change == "negative_pressure":
        rec = replace(
            rec,
            pressure_patches=(
                replace(
                    rec.pressure_patches[0], compressive_pressure=PhysicalQuantity.of(-1, Unit.MPA)
                ),
            ),
        )
    elif change == "empty_binding_faces":
        binding = replace(binding, branches=())
    elif change == "wrong_profile":
        binding = replace(binding, profile_family="ANGLE")
    if layer != original.bolts[0].layers[0]:
        bolt = replace(bolt, layers=(layer, *bolt.layers[1:]))
    if section != original.bolts[0].sections[0]:
        bolt = replace(bolt, sections=(section, *bolt.sections[1:]))
    if bolt != original.bolts[0]:
        rec = replace(rec, bolts=(bolt, *rec.bolts[1:]))
    checked = validate_column_base_response(binding, rec)
    assert not checked.qualified, (change, checked)
    assert checked.response is None
    assert checked.reasons
    if not rec.reference:
        with pytest.raises(ValueError, match="nonempty"):
            replace(s, responses=(rec,))
        return
    # Invalid records never turn into fabricated zero branch demands or resistance.
    if binding == p.response_binding:
        d = evaluate_column_moment_base(r, replace(s, responses=(rec,)))
        assert not d.member_bolts
        assert not d.local_checks
        assert not d.resistance_evaluated


@pytest.mark.parametrize(
    "change",
    [
        "reference",
        "binding",
        "method",
        "capacity",
        "negative",
        "dimension",
        "duplicate",
        "coverage",
        "locator",
    ],
)
def test_qualified_zone_cannot_mask_missing_or_invalid_capacity(change: str) -> None:
    r, p, s = complete_sources(request())
    zone = s.zones[0]
    check = zone.checks[0]
    if change == "reference":
        zone = replace(zone, reference="OTHER")
    elif change == "binding":
        zone = replace(zone, exact_binding="wrong")
    elif change == "method":
        check = replace(check, method="")
    elif change == "capacity":
        check = replace(check, design_capacity=PhysicalQuantity.of(0, Unit.N))
    elif change == "negative":
        check = replace(check, demand=PhysicalQuantity.of(-1, Unit.N))
    elif change == "dimension":
        check = replace(check, demand=PhysicalQuantity.of(1, Unit.MM))
    elif change == "duplicate":
        zone = replace(zone, checks=(check, check))
    elif change == "coverage":
        zone = replace(zone, coverage=())
    elif change == "locator":
        check = replace(check, source_locator="")
    if check != s.zones[0].checks[0]:
        zone = replace(zone, checks=(check,))
    d = evaluate_column_moment_base(r, replace(s, zones=(zone,)))
    assert p.response.qualified
    assert d.local_zone is not None
    assert d.local_zone.status == "SOURCE_REQUIRED"
    assert "COMMON_COLUMN_END_ZONE" in d.missing_sources


def test_zone_failure_is_identified_and_partial_fastener_source_is_not_f593_strength() -> None:
    r, p, s = complete_sources(request())
    zone = s.zones[0]
    bad = replace(
        zone, checks=(replace(zone.checks[0], design_capacity=PhysicalQuantity.of(".5", Unit.N)),)
    )
    d = evaluate_column_moment_base(r, replace(s, zones=(bad,), fasteners=()))
    assert d.status == "FAIL"
    assert "COMMON_COLUMN_END_ZONE" in d.failed_check_ids
    assert all(b.status == "SOURCE_REQUIRED" for b in d.member_bolts)
    assert p.response.qualified


@pytest.mark.parametrize("family", ["RHS8", "SRS8"])
def test_true_intersecting_holes_fail_closed_without_silently_relocating(family: str) -> None:
    r = request(family)
    changed = replace(
        r,
        y_positive=replace(
            r.y_positive,
            angle=replace(
                r.y_positive.angle,
                member_pattern=replace(
                    r.y_positive.angle.member_pattern,
                    center=r.x_positive.angle.member_pattern.center,
                ),
            ),
        ),
    )
    p = preview_column_moment_base(changed)
    assert p.geometry.status == "INVALID_GEOMETRY"
    assert any("SHANK_HOLE_COLLISION" in v for v in p.geometry.reasons)
    assert p.input == changed
    assert not p.design_check_ready
    assert not p.transfers
    assert evaluate_column_moment_base(changed).status == "INVALID_GEOMETRY"
    assert preview_column_moment_base(r).geometry.status == "VALID"


def test_unknown_family_layout_and_contract_do_not_reuse_old_domain() -> None:
    r = request()
    with pytest.raises(ValueError, match="uniform registered"):
        replace(r.column, family=cast(Family, "ANGLE"))
    with pytest.raises(ValueError, match="layout"):
        replace(r, layout=cast(Layout, "SINGLE"))
    with pytest.raises(ValueError, match="contract"):
        replace(r, contract="4.4-RC1")
    with pytest.raises(ValueError, match="identity"):
        replace(r, request_id="")
    with pytest.raises(ValueError, match="Finite"):
        replace(r.actions, axial=PhysicalQuantity.of(1, Unit.IN))
    with pytest.raises(ValueError, match="TORQUE"):
        replace(r.actions, applied_torque_z=PhysicalQuantity.of(1, Unit.N_MM))


def test_source_catalogues_are_exact_unique_not_user_registration() -> None:
    _, _, s = response_sources(request())
    with pytest.raises(ValueError, match="unique"):
        ColumnMomentSourceRegistry(responses=(s.responses[0], s.responses[0]))
    with pytest.raises(ValueError, match="nonempty"):
        ColumnMomentSourceRegistry(responses=(replace(s.responses[0], reference=""),))


def test_qualified_response_without_capacity_remains_explicitly_source_limited() -> None:
    r, _, sources = response_sources(request())
    d = evaluate_column_moment_base(r, sources)
    assert d.resistance_evaluated
    assert d.missing_sources
    assert all(a.check.status != "PASS" for a in d.member_attachment_results)


def test_native_body_failures_and_incomplete_attachment_coverage_are_retained() -> None:
    r, _, sources = complete_sources(request())
    records = sources.connector_sources.records
    weak = []
    for record in records:
        package = replace(
            record.package,
            strengths=tuple(
                replace(
                    v,
                    positive=PhysicalQuantity.of("1E-20", Unit.N if i < 3 else Unit.N_MM),
                    negative=PhysicalQuantity.of("1E-20", Unit.N if i < 3 else Unit.N_MM),
                )
                for i, v in enumerate(record.package.strengths)
            ),
        )
        weak.append(replace(record, package=package))
    d = evaluate_column_moment_base(
        r,
        replace(sources, connector_sources=replace(sources.connector_sources, records=tuple(weak))),
    )
    assert d.status == "FAIL"
    assert any(v.endswith(":BODY") for v in d.failed_check_ids)
    assert any(v.endswith(":MEMBER_ATTACHMENT") for v in d.failed_check_ids)
    incomplete = tuple(replace(v, attachment_coverage=()) if v.attachment else v for v in records)
    bad = evaluate_column_moment_base(
        r,
        replace(sources, connector_sources=replace(sources.connector_sources, records=incomplete)),
    )
    assert any("COVERAGE_MISSING" in v.check.status for v in bad.member_attachment_results)


def test_unknown_foot_breakdown_rejected_and_qualified_foot_recovered_once() -> None:
    from frp_master_connection.application.angle_column_base_preview import AngleBasePreview
    from tests.application.test_angle_column_base_negative import furnished_foot_record

    r, p, sources = response_sources(request())
    foot = furnished_foot_record(cast(AngleBasePreview, p))
    record = replace(sources.responses[0], foot_breakdowns=(foot,))
    accepted = preview_column_moment_base(r, replace(sources, responses=(record,)))
    assert accepted.response.qualified
    assert accepted.foundation_breakdowns[0].proof is not None
    assert accepted.foundation_breakdowns[0].proof.passed
    assert accepted.assembled_foundation_action == p.assembled_foundation_action
    wrong = replace(foot, domain=replace(foot.domain, connector_id="UNKNOWN"))
    bad = validate_column_base_response(
        p.response_binding, replace(record, foot_breakdowns=(wrong,))
    )
    assert "FOOT_BREAKDOWN_UNKNOWN_CONNECTOR" in bad.reasons


def test_corrupted_opposite_physical_grid_is_rejected_before_shank_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.application import column_moment_base_geometry as geometry
    from frp_master_connection.application.wi_wall_moment_geometry import PlacedWallAngle
    from frp_master_connection.domain.column_moment_base import ColumnMomentBaseRequest, Face
    from frp_master_connection.domain.member_profile import MemberProfile

    original = geometry._placed

    def mismatched(r: ColumnMomentBaseRequest, p: MemberProfile, face: Face) -> PlacedWallAngle:
        placed = original(r, p, face)
        if face == "X_NEG":
            spec = placed.specification
            placed = replace(
                placed,
                specification=replace(
                    spec,
                    member_pattern=replace(
                        spec.member_pattern, center=PhysicalQuantity.of("2.875", Unit.IN)
                    ),
                ),
            )
        return placed

    monkeypatch.setattr(geometry, "_placed", mismatched)
    result = geometry.resolve_column_moment_base_geometry(request("RHS8"))
    assert result.status == "INVALID_GEOMETRY"
    assert "X_POS:OPPOSITE_PHYSICAL_GRID_MISMATCH" in result.reasons
