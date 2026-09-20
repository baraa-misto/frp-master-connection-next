"""Isolated verified response/strength fixtures; never production registration.

The zero-external-load fixtures explicitly specify a self-equilibrated test
preload/contact set at the actual bolt locations. They are NOT an automatic
response for an unloaded production connection, nor ASTM F593 material data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.wi_frp_support_local_checks import (
    bearing_and_pull_through,
    support_group_paths,
)
from frp_master_connection.application.wi_frp_support_moment_design import (
    _bolt_check,
    evaluate_local_zone,
    evaluate_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    FRPSupportMomentPreview,
    preview_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_sources import (
    FRPSupportSourceRegistry,
    QualifiedLocalSupportZone,
    QualifiedZoneCheck,
    SupportFastenerSource,
    evaluate_frp_support_connector_sources,
    fastener_binding,
    frp_support_provider_context,
    local_zone_binding,
    response_binding,
)
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.application.wi_wall_moment_sources import WallMomentQualifiedSource
from frp_master_connection.calculation import ThreadStatus
from frp_master_connection.calculation.angle_connector_core import (
    components,
)
from frp_master_connection.calculation.equations import (
    bolt_shear_resistance_from_nominal_stress,
    bolt_tension_resistance,
    pin_bearing_resistance,
    pull_through_resistance,
)
from frp_master_connection.calculation.multirow_equations import (
    adjusted_property_trace,
    constant_pitch_factor,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from frp_master_connection.calculation.support_attachment_response import (
    REQUIRED_COVERAGE,
    QualifiedSupportResponse,
    ReceivingLayerForce,
    ShaftDemand,
    SupportResponseAction,
    validate_support_response,
)
from frp_master_connection.domain.wi_frp_support_moment import (
    SupportMode,
    WIFrpSupportMomentRequest,
)
from tests.application.test_wi_frp_support_moment import request
from tests.application.test_wi_wall_moment import qualified
from tests.calculation.test_support_attachment_response import q, source, vec


def verified_fixture(
    mode: SupportMode,
) -> tuple[WIFrpSupportMomentRequest, FRPSupportMomentPreview, FRPSupportSourceRegistry]:
    r = request(mode, 7)
    top = replace(
        r.top,
        support_fastener=replace(
            r.top.support_fastener, source_authority_id="TEST_ONLY_EXPLICIT_STRENGTH"
        ),
    )
    web = replace(
        r.positive_web,
        support_fastener=replace(
            r.positive_web.support_fastener, source_authority_id="TEST_ONLY_EXPLICIT_STRENGTH"
        ),
    )
    r = replace(
        r,
        top=top,
        bottom=top,
        positive_web=web,
        negative_web=web,
        response_source_reference="TEST_ONLY_PRELOAD",
        local_zone_source_reference="TEST_ONLY_ZONE",
    )
    p = preview_wi_frp_support_moment(r)
    binding = response_binding(p)
    actions: list[SupportResponseAction] = []
    sections: list[ShaftDemand] = []
    layers: list[ReceivingLayerForce] = []
    for group, target in binding.group_targets:
        members = tuple(b for b in binding.physical_bolts if b.group_id == group)
        u0, v0, _ = components(target.reference)
        for bolt in members:
            u, v, _ = components(bolt.near)
            fu = "-.1" if u < u0 else ".1"
            fv = "-.2" if v < v0 else ".2"
            force = vec((fu, fv, "1"), Unit.KIP)
            actions.append(
                SupportResponseAction(
                    bolt.bolt_id,
                    group,
                    "BOLT",
                    bolt.near,
                    force,
                    vec(("0", "0", "0"), Unit.KIP_IN),
                    bolt.bolt_id,
                    bolt.layer_ids[0],
                )
            )
            sections.append(
                ShaftDemand(
                    bolt.bolt_id,
                    "TEST_AUTHORIZED_ANGLE_INTERFACE_SECTION",
                    bolt.layer_ids,
                    force.x,
                    force.y,
                    force.z,
                    "SINGLE_PLANE_8_2_8_3",
                    True,
                )
            )
            # Explicit far-wall-only participation. No equal wall-sharing rule.
            layers.extend(
                ReceivingLayerForce(
                    bolt.bolt_id,
                    layer,
                    force if layer == bolt.layer_ids[-1] else vec(("0", "0", "0"), Unit.KIP),
                )
                for layer in bolt.layer_ids
            )
        domain = next(d for d in binding.contact_domains if d.group_id == group)
        actions.append(
            SupportResponseAction(
                f"{group}:CONTACT",
                group,
                "CONTACT",
                target.reference,
                vec(("0", "0", "-4"), Unit.KIP),
                vec(("0", "0", "0"), Unit.KIP_IN),
                layer_id=domain.layer_id,
            )
        )
    response = QualifiedSupportResponse(
        "TEST_ONLY_PRELOAD",
        source(),
        "TEST_ONLY_ISSUER",
        binding,
        tuple(actions),
        tuple(sections),
        ("EXPLICIT_TEST_PRELOAD_SELF_EQUILIBRATED_CONTACT",),
        REQUIRED_COVERAGE,
        "SYNTHETIC_ONLY_NOT_A_PRODUCTION_SOLVER",
        True,
        native_external_precision_and_proof=("EXACT_FINITE_TEST_LAYER_PARTICIPATION",),
        receiving_layer_forces=tuple(layers),
    )
    fasteners = tuple(
        SupportFastenerSource(
            "TEST_ONLY_EXPLICIT_STRENGTH",
            source(),
            fastener_binding(p, t.connector_id),
            q("60", Unit.KSI),
            q("40", Unit.KSI),
            "EXCLUDED",
            ("SINGLE_PLANE_8_2_8_3",),
        )
        for t in p.connectors
    )
    return r, p, FRPSupportSourceRegistry(responses=(response,), fasteners=fasteners)


@pytest.mark.parametrize("mode", list(SupportMode))
def test_t43_052_055_064_real_geometry_source_bound_numeric_bolts_all_five_topologies(
    mode: SupportMode,
) -> None:
    r, p, registry = verified_fixture(mode)
    validated = validate_support_response(response_binding(p), registry.responses[0])
    assert validated.status == "VALID_QUALIFIED_RESPONSE", validated.reasons
    result = evaluate_wi_frp_support_moment(r, registry)
    assert len(result.support_bolts) == 16
    assert result.support_response is not None
    assert result.support_response.status == "VALID_QUALIFIED_RESPONSE"
    for b in result.support_bolts:
        assert b.status == "PASS", b.reason
        assert b.source is not None
        assert b.shear_magnitude is not None
        assert b.total_tension_including_prying == q("1")
        assert not b.prying_added_again
        diameter = r.top.support_fastener.bolt_diameter
        assert b.tension_trace == bolt_tension_resistance(diameter, q("60", Unit.KSI))
        assert b.shear_trace == bolt_shear_resistance_from_nominal_stress(
            diameter, q("40", Unit.KSI)
        )
        assert b.combined_trace == sourced_combined_bolt_resistance(
            diameter, q("60", Unit.KSI), q("40", Unit.KSI), b.shear_magnitude
        )
    if mode is SupportMode.HOLLOW_SQUARE:
        pulls = [
            c
            for c in result.support_local_checks
            if c.method == "NATIVE_ASCE_8_4_LESSER_BOTH_BRANCHES"
        ]
        assert any(c.applicability.startswith("NO_EXTERIOR_WASHER") for c in pulls)
        assert any(c.native_trace is not None and c.demand == q("1") for c in pulls)
    if mode is SupportMode.SOLID_SQUARE:
        assert any(
            c.applicability == "FULL_SOLID_GRIP_IS_NOT_EFFECTIVE_THIN_PLATE_THICKNESS"
            for c in result.support_local_checks
        )
    # Test fixture demonstrates the numerical path, never a complete production PASS.
    assert result.status != "PASS"
    assert result.local_zone is not None
    assert result.local_zone.status == "SOURCE_REQUIRED"


@pytest.mark.parametrize(
    "mutation", ["layers", "duplicate", "unknown", "force", "negative", "unit", "proof"]
)
def test_hollow_source_layer_participation_is_explicit_conserved_and_not_shaft_duplication(
    mutation: str,
) -> None:
    _, p, registry = verified_fixture(SupportMode.HOLLOW_SQUARE)
    r = registry.responses[0]
    first = r.receiving_layer_forces[0]
    if mutation == "layers":
        r = replace(r, receiving_layer_forces=())
    elif mutation == "duplicate":
        r = replace(r, receiving_layer_forces=(*r.receiving_layer_forces, first))
    elif mutation == "unknown":
        r = replace(
            r,
            receiving_layer_forces=(
                replace(first, layer_id="CAVITY"),
                *r.receiving_layer_forces[1:],
            ),
        )
    elif mutation == "force":
        r = replace(
            r,
            receiving_layer_forces=(
                replace(first, force=vec(("1", "0", "0"), Unit.KIP)),
                *r.receiving_layer_forces[1:],
            ),
        )
    elif mutation == "negative":
        r = replace(
            r,
            receiving_layer_forces=(
                replace(first, force=vec(("0", "0", "-1"), Unit.KIP)),
                *r.receiving_layer_forces[1:],
            ),
        )
    elif mutation == "unit":
        r = replace(
            r,
            receiving_layer_forces=(
                replace(first, force=vec(("1", "0", "0"), Unit.IN)),
                *r.receiving_layer_forces[1:],
            ),
        )
    else:
        r = replace(r, native_external_precision_and_proof=())
    result = validate_support_response(response_binding(p), r)
    assert result.status == "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE"


def test_single_plane_cannot_hide_tension_by_issuing_zero_section_demands() -> None:
    _, p, registry = verified_fixture(SupportMode.WI_WEB)
    r = registry.responses[0]
    changed = replace(
        r, shaft_demands=(replace(r.shaft_demands[0], tensile_demand=q("0")), *r.shaft_demands[1:])
    )
    assert (
        "EXACT_SINGLE_LAP_SECTION_RESPONSE_MISMATCH"
        in validate_support_response(response_binding(p), changed).reasons
    )


@pytest.mark.parametrize(
    "mutation", ["source", "binding", "confirmation", "thread", "stress", "method", "bending"]
)
def test_native_capacity_cannot_run_without_matching_bolt_strength_condition_and_section(
    mutation: str,
) -> None:
    _, p, registry = verified_fixture(SupportMode.WI_FLANGE)
    r = registry.responses[0]
    d = r.shaft_demands[0]
    s = registry.fasteners[0]
    validated = validate_support_response(response_binding(p), r)
    if mutation == "source":
        registry = replace(registry, fasteners=())
    elif mutation == "binding":
        registry = replace(
            registry, fasteners=(replace(s, exact_fastener_and_grip_binding="wrong"),)
        )
    elif mutation == "confirmation":
        registry = replace(
            registry, fasteners=(replace(s, source=replace(s.source, qualification_record_ids=())),)
        )
    elif mutation == "thread":
        registry = replace(registry, fasteners=(replace(s, condition="INCLUDED"),))
    elif mutation == "stress":
        registry = replace(
            registry, fasteners=(replace(s, nominal_tensile_stress=q("0", Unit.KSI)),)
        )
    elif mutation == "method":
        d = replace(d, applicability="DOUBLE_SHEAR_NOT_AUTHORIZED")
    else:
        d = replace(d, secondary_bending_covered=False)
    check = _bolt_check(p, "TOP_FLANGE_ANGLE", d.bolt_id, d, validated, registry)
    assert check.status == "SOURCE_REQUIRED"
    assert check.combined_trace is None
    assert check.total_tension_including_prying == q("1")


def test_numeric_failure_is_not_hidden_by_missing_sources_or_clamped_negative_capacity() -> None:
    _, p, registry = verified_fixture(SupportMode.WI_FLANGE)
    r = registry.responses[0]
    d = r.shaft_demands[0]
    validated = validate_support_response(response_binding(p), r)
    failed = _bolt_check(
        p, "TOP_FLANGE_ANGLE", d.bolt_id, replace(d, force_u=q("100")), validated, registry
    )
    assert failed.status == "FAIL"
    assert failed.combined_trace is not None
    assert failed.combined_trace.design_tensile_resistance.canonical_magnitude < 0


def zone_fixture(p: FRPSupportMomentPreview, *, failed: bool = False) -> QualifiedLocalSupportZone:
    required = evaluate_local_zone(p, FRPSupportSourceRegistry()).required_coverage
    return QualifiedLocalSupportZone(
        "TEST_ONLY_ZONE",
        source(),
        local_zone_binding(p),
        p.input.support.mode,
        "TEST_ONLY_ISSUER",
        ("ACTUAL_ASSEMBLY_TEST_ONLY",),
        (
            QualifiedZoneCheck(
                "TEST_INTERACTION",
                required,
                q("2" if failed else "1"),
                q("1"),
                "TEST_ONLY_SOURCE_COMPARISON",
                "ISOLATED_TEST_RECORD",
            ),
        ),
    )


def test_separate_local_zone_qualified_completeness_failure_and_exact_binding() -> None:
    _, p, registry = verified_fixture(SupportMode.WI_FLANGE)
    zone = zone_fixture(p)
    result = evaluate_local_zone(p, replace(registry, local_zones=(zone,)))
    assert result.status == "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"
    assert result.overall_member_design == "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"
    assert (
        evaluate_local_zone(
            p, replace(registry, local_zones=(zone_fixture(p, failed=True),))
        ).status
        == "FAIL"
    )
    for changed in (
        replace(zone, exact_binding="wrong"),
        replace(zone, support_mode=SupportMode.WI_WEB),
        replace(zone, issuer=""),
        replace(zone, contact_stiffness_boundary_domain=()),
        replace(zone, checks=()),
        replace(zone, checks=zone.checks * 2),
        replace(zone, checks=(replace(zone.checks[0], method=""),)),
        replace(zone, checks=(replace(zone.checks[0], demand=q("-1")),)),
    ):
        assert (
            evaluate_local_zone(p, replace(registry, local_zones=(changed,))).status
            == "SOURCE_REQUIRED"
        )
    factories: tuple[Callable[[], FRPSupportSourceRegistry], ...] = (
        lambda: FRPSupportSourceRegistry(responses=registry.responses * 2),
        lambda: FRPSupportSourceRegistry(fasteners=registry.fasteners * 2),
        lambda: FRPSupportSourceRegistry(local_zones=(zone, replace(zone, reference=""))),
    )
    for make in factories:
        with pytest.raises(ValueError, match="unique"):
            make()


def test_native_support_group_paths_use_real_free_ends_and_prescribed_rows_only() -> None:
    # Pure shear leaves each web support group's Fu accompanied by Mn; move the
    # independently supplied plane wrench to its actual centroid with Mn=0 for
    # this isolated applicability test. No production eccentric moment is erased.
    p = preview_wi_frp_support_moment(request(SupportMode.WI_FLANGE, 1))
    from frp_master_connection.application.wi_frp_support_moment_orchestration import (
        support_plane_input,
    )
    from frp_master_connection.calculation.in_plane_wrench_demand import (
        calculate_in_plane_wrench_demand,
    )

    t = p.connectors[2]
    centered = replace(t.support_uvn, moment=vec(("0", "0", "0"), Unit.KIP_IN))
    plane = calculate_in_plane_wrench_demand(
        support_plane_input(p.geometry, t.connector_id, centered)
    )
    modified = replace(
        p,
        connectors=(
            *p.connectors[:2],
            replace(t, support_in_plane_demand=plane, support_uvn=centered),
            p.connectors[3],
        ),
    )
    for receiving in (True, False):
        checks = support_group_paths(modified, t.connector_id, receiving=receiving)
        assert any(c.native_trace is not None for c in checks)
        assert any(c.status.startswith("SOURCE_REQUIRED") for c in checks)
    # A one-row source and a nonstandard hole do not inherit a two-row plan.
    for change, expected in (("row", "JUNCTION_END_OR_ROW"), ("hole", "NONSTANDARD_HOLE")):
        spec = modified.input.positive_web
        changed = (
            replace(spec, support_pattern=replace(spec.support_pattern, across=1))
            if change == "row"
            else replace(
                spec,
                support_fastener=replace(spec.support_fastener, hole_diameter=q(".6", Unit.IN)),
            )
        )
        varied = replace(
            modified, input=replace(modified.input, positive_web=changed, negative_web=changed)
        )
        if change == "row":
            # Use actual one-line geometry, not only a request count.
            actual = preview_wi_frp_support_moment(varied.input)
            vt = actual.connectors[2]
            cp = replace(vt.support_uvn, moment=centered.moment)
            varied = replace(
                actual,
                connectors=(
                    *actual.connectors[:2],
                    replace(
                        vt,
                        support_uvn=cp,
                        support_in_plane_demand=calculate_in_plane_wrench_demand(
                            support_plane_input(actual.geometry, vt.connector_id, cp)
                        ),
                    ),
                    actual.connectors[3],
                ),
            )
        checks = support_group_paths(varied, t.connector_id, receiving=True)
        assert any(expected in c.applicability for c in checks)
    # A flange angle's heel is not a fictitious free end for this force direction.
    ft = modified.connectors[0]
    fw = replace(ft.support_uvn, force=centered.force, moment=centered.moment)
    fc = replace(
        ft,
        support_uvn=fw,
        support_in_plane_demand=calculate_in_plane_wrench_demand(
            support_plane_input(modified.geometry, ft.connector_id, fw)
        ),
    )
    flanged = replace(modified, connectors=(fc, *modified.connectors[1:]))
    assert all(
        c.native_trace is None
        for c in support_group_paths(flanged, ft.connector_id, receiving=False)
    )
    bad_layer = p.geometry.support_bolts[0].hardware.hardware_id
    with pytest.raises(ValueError, match="not penetrated"):
        bearing_and_pull_through(
            p,
            "TOP_FLANGE_ANGLE",
            bad_layer,
            q("1"),
            q("0"),
            q("1"),
            "TEST",
            receiving=True,
            layer_id="CAVITY",
        )


def test_connector_registry_coverage_cannot_be_granted_by_reference_or_incomplete_attachment() -> (
    None
):
    r = request()
    top = replace(r.top, connector_source_reference="TEST", attachment_source_reference="TEST")
    p = preview_wi_frp_support_moment(replace(r, top=top, bottom=top))
    t = p.connectors[0]
    ctx = frp_support_provider_context(p, t, attachment=True)
    record = WallMomentQualifiedSource("TEST", t.connector_id, qualified(t.core, ctx), True, ())
    with pytest.raises(ValueError, match="unique"):
        FRPSupportSourceRegistry(connector_sources=(record, record))
    _, attachment = evaluate_frp_support_connector_sources(
        p, t, FRPSupportSourceRegistry(connector_sources=(record,))
    )
    assert attachment.check.status == "NOT_EVALUATED_QUALIFIED_ATTACHMENT_COVERAGE_MISSING"


@pytest.mark.parametrize("change", ["load", "face", "thickness", "washer"])
def test_source_binding_is_invalidated_by_actual_assembly_and_action_changes(change: str) -> None:
    r, _, registry = verified_fixture(SupportMode.WI_FLANGE)
    if change == "load":
        r = replace(r, actions=replace(r.actions, axial=q("1")))
    elif change == "face":
        r = replace(r, support=replace(r.support, face="FLANGE_NEG_OUTER"))
    elif change == "thickness":
        r = replace(r, support=replace(r.support, flange_thickness=q(".6", Unit.IN)))
    else:
        top = replace(
            r.top,
            support_hardware=replace(r.top.support_hardware, washer_thickness=q(".13", Unit.IN)),
        )
        r = replace(r, top=top, bottom=top)
    p = preview_wi_frp_support_moment(r)
    assert (
        "SOURCE_NOT_APPLICABLE_EXACT_ASSEMBLY_LOAD_BINDING_MISMATCH"
        in validate_support_response(response_binding(p), registry.responses[0]).reasons
    )


def test_zone_must_explicitly_cover_each_unresolved_local_check() -> None:
    r, p, registry = verified_fixture(SupportMode.HOLLOW_SQUARE)
    unqualified = evaluate_wi_frp_support_moment(r, registry)
    required = evaluate_local_zone(p, registry, unqualified.support_local_checks).required_coverage
    zone = zone_fixture(p)
    incomplete = evaluate_local_zone(
        p, replace(registry, local_zones=(zone,)), unqualified.support_local_checks
    )
    assert incomplete.status == "SOURCE_REQUIRED"
    assert any(c.startswith("LOCAL_CHECK:") for c in required)
    complete = replace(zone, checks=(replace(zone.checks[0], coverage=required),))
    result = evaluate_wi_frp_support_moment(r, replace(registry, local_zones=(complete,)))
    assert result.local_zone is not None
    assert result.local_zone.status == "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"
    assert (
        dict(result.scope_statuses)["LOCAL_FRP_REGIONS"]
        == "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"
    )


def test_zero_modified_tensile_resistance_cannot_pass_positive_tension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Aggregation edge only. Independent Eq.8-3 numeric fixtures remain unpatched.
    import frp_master_connection.application.wi_frp_support_moment_design as design

    _, p, registry = verified_fixture(SupportMode.WI_FLANGE)
    d = registry.responses[0].shaft_demands[0]
    response = validate_support_response(response_binding(p), registry.responses[0])
    native = sourced_combined_bolt_resistance(
        p.input.top.support_fastener.bolt_diameter, q("60", Unit.KSI), q("40", Unit.KSI), q("1")
    )
    monkeypatch.setattr(
        design,
        "sourced_combined_bolt_resistance",
        lambda *_args: replace(native, design_tensile_resistance=q("0")),
    )
    assert _bolt_check(p, "TOP_FLANGE_ANGLE", d.bolt_id, d, response, registry).status == "FAIL"


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("count", [1, 2])
def test_independent_local_bearing_row_pitch_and_pull_through_factor_boundaries(
    axis: int, count: int
) -> None:
    r = request(SupportMode.WI_WEB, load=7)
    spec = replace(r.top, support_pattern=replace(r.top.support_pattern, along=count, across=count))
    p = preview_wi_frp_support_moment(replace(r, top=spec, bottom=spec))
    t = p.connectors[0]
    force = vec(("1", "0", "0") if axis == 0 else ("0", "1", "0"), Unit.KIP)
    # Isolated native applicability fixture: source-defined concentric group,
    # not erasure of any production connector's generated moment.
    changed = replace(
        t, support_uvn=replace(t.support_uvn, force=force, moment=vec(("0", "0", "0"), Unit.KIP_IN))
    )
    p = replace(p, connectors=(changed, *p.connectors[1:]))
    bolt = p.geometry.support_bolts[0]
    material = create_locked_ice_material_snapshot()
    for receiving in (True, False):
        bearing, pull = bearing_and_pull_through(
            p,
            t.connector_id,
            bolt.hardware.hardware_id,
            force.x,
            force.y,
            q("1"),
            "ISOLATED_NATIVE_FACTOR_FIXTURE",
            receiving=receiving,
        )
        kind = FRPPropertyKind.FBR_L if (axis == 0) == receiving else FRPPropertyKind.FBR_T
        prop = next(x for x in material.properties if x.kind is kind)
        pitch = spec.support_pattern.pitch if axis == 0 else spec.support_pattern.gauge
        delta = (
            constant_pitch_factor(
                (pitch,), spec.support_fastener.bolt_diameter
            ).pitch_factor_c_delta
            if count == 2
            else Decimal(1)
        )
        assert bearing.native_trace == pin_bearing_resistance(
            q(".5", Unit.IN),
            spec.support_fastener.bolt_diameter,
            adjusted_property_trace(prop, END_USE),
            ThreadStatus.EXCLUDED,
            c_delta=delta,
            c_lap=Decimal(".6"),
            lambda_factor=Decimal(1),
        )
        tt = next(x for x in material.properties if x.kind is FRPPropertyKind.FSH_LT)
        inter = next(x for x in material.properties if x.kind is FRPPropertyKind.FSH_INT)
        assert pull.native_trace == pull_through_resistance(
            spec.support_hardware.washer_diameter,
            q(".5", Unit.IN),
            adjusted_property_trace(tt, END_USE),
            adjusted_property_trace(inter, END_USE),
            c_delta=Decimal(1),
            lambda_factor=Decimal(1),
        )
