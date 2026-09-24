"""Stage 4.2 RC1-R7: controlled G1-G128 and independent native-engine oracles."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from frp_master_connection.application import wi_wall_moment_orchestration as app
from frp_master_connection.application.multirow_orchestration import (
    _execution_bundle,
    _resolve,
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.application.wi_wall_moment_demand import (
    flange_local_request,
    flange_stage25_input,
)
from frp_master_connection.application.wi_wall_moment_design import (
    aggregate_internal_status,
    evaluate_wi_wall_moment,
)
from frp_master_connection.application.wi_wall_moment_geometry import (
    FRAMES,
    grid,
    q,
    xyz,
)
from frp_master_connection.application.wi_wall_moment_sources import (
    ATTACHMENT_COVERAGE,
    ATTACHMENT_METHOD,
    WallMomentQualifiedSource,
    WallMomentSourceRegistry,
    evaluate_attachment_source,
    evaluate_connector_source,
    provider_context,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
    Rational3,
    angle_fingerprint,
    components,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.angle_connector_providers import evaluate_angle_provider
from frp_master_connection.calculation.eccentric_demand import calculate_eccentric_bolt_group_demand
from frp_master_connection.calculation.frp_angle_connector_provider import (
    FRPAngleContext,
    FRPAngleDetail,
    QualifiedCoverage,
    QualifiedFRPAngleSource,
    SignedDesignStrength,
    _body,
    frp_source_binding,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.multirow_engine import (
    MultiRowFactorContext,
    PitchFactorSource,
)
from frp_master_connection.calculation.properties import create_locked_ice_material_snapshot
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentComponentResultants,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
)
from frp_master_connection.domain.material_architecture import (
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    PropertySourceConfirmation,
)
from frp_master_connection.domain.values import EngineeringUnitSystem
from frp_master_connection.domain.wi_wall_moment import (
    CONNECTORS,
    CONTRACT,
    PRODUCT,
    WIWallMomentRequest,
    default_wi_wall_moment_request,
)
from tests.calculation.test_angle_connector_core_and_frp_provider import (
    context as instep_test_context,
)

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT
    / "backend/tests/golden"
    / "stage_4_2_wi_beam_concrete_wall_moment_connection_golden_benchmarks_rc1_r7.json"
)
CASES = json.loads(GOLDEN.read_text(encoding="utf-8"))["benchmarks"]
D = Decimal


def expected(n: int) -> dict[str, Any]:
    return cast(dict[str, Any], CASES[n - 1]["expected"])


@pytest.fixture(scope="module")
def case() -> WIWallMomentRequest:
    return default_wi_wall_moment_request()


@pytest.fixture(scope="module")
def preview(case: WIWallMomentRequest) -> app.WIWallMomentPreview:
    return app.preview_wi_wall_moment(case)


def test_g1_g5_g126_scope_and_package(case: WIWallMomentRequest) -> None:
    assert (
        hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper()
        == "6F8A22388BEEFFB1CE1B4EF9556261C63200C632E5D50F5447F4011D2C15EA2B"
    )
    assert [int(c["id"].split("_")[0][1:]) for c in CASES] == list(range(1, 129))
    assert (expected(1)["product_id"], expected(1)["contract"]) == (PRODUCT, CONTRACT)
    for profile in ("CHANNEL", "RECTANGULAR_TUBE", "SOLID_RECTANGULAR", "ANGLE"):
        with pytest.raises(ValueError, match=r"Stage 3\.6A requires WIDE_FLANGE_I beams"):
            replace(case, beam=replace(case.beam, profile_family=profile))
    with pytest.raises(ValueError, match="RESISTANCE_PROVIDER_NOT_IMPLEMENTED"):
        replace(case.top, provider_id="316SS")
    assert case.top.provider_id == expected(4)["implemented_user_provider"]


def test_controlled_package_hashes_sentinels_source_review_and_supersession() -> None:
    package = json.loads(
        (ROOT / "docs/qa/STAGE_4_2_CONTROLLED_PACKAGE.json").read_text(encoding="utf-8")
    )
    assert package["authority"] == "STAGE_4_2_RC1_R7"
    assert package["baseline"] == "473a3c8cd43f13022d254dae2477084895478c74"
    assert len(package["artifacts"]) == 14
    for item in package["artifacts"]:
        raw = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == item["sha256"]
        assert raw.decode("utf-8").rstrip().endswith(item["sentinel"])
    assert package["golden"]["count"] == 128
    assert (
        hashlib.sha256((ROOT / package["golden"]["path"]).read_bytes()).hexdigest().upper()
        == package["golden"]["sha256"]
    )
    assert package["source_pdfs_read_only"]["copied_to_repository"] is False
    assert package["source_pdfs_read_only"]["erratum_effective"] == "2026-01-13"
    assert not list((ROOT / "backend/tests/golden").glob("stage_4_2_*_rc1_r[1-6].json"))


def test_g6_g25_geometry_and_references(
    case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    g = preview.geometry
    assert g.status == "VALID"
    assert not g.reasons
    assert g.symmetry_proven
    assert len(g.angles) == expected(13)["total"]
    assert {p.box.component_id for p in g.parts} == {"CONCRETE_WALL", "WI_BEAM", *CONNECTORS}
    wall = next(p for p in g.parts if p.part_id == "CONCRETE_WALL")
    assert wall.material_region is None
    assert wall.box.size_l_v_t.l.to(Unit.IN).magnitude == D(expected(12)["thickness_in"])
    assert xyz(preview.joint_right_hand_action.reference) == tuple(
        map(D, expected(7)["beam_end_reference_L_V_T_in"])
    )
    assert xyz(preview.joint_right_hand_action.force, Unit.KIP) == tuple(
        map(D, expected(9)["right_hand"]["F_L_V_T_kip"])
    )
    assert xyz(preview.joint_right_hand_action.moment, Unit.KIP_IN) == tuple(
        map(D, expected(9)["right_hand"]["M_L_V_T_kip_in"])
    )
    assert preview.sign_method == expected(8)["method"]
    assert case.gap.to(Unit.IN).magnitude == D(expected(10)["gap_in"])
    assert [
        v.to(Unit.IN).magnitude
        for v in (
            case.beam.depth,
            case.beam.flange_width,
            case.beam.web_thickness,
            case.beam.flange_thickness,
            case.beam.display_length_each_side,
        )
    ] == [D(expected(11)[k]) for k in ("d_in", "b_f_in", "t_w_in", "t_f_in", "display_length_in")]
    for i, (name, a) in enumerate(
        zip(("top", "bottom", "positive_web", "negative_web"), g.angles, strict=True)
    ):
        assert a.frame == FRAMES[i]
        x, y, z = a.frame.a, a.frame.b, a.frame.c
        assert (
            x[1] * y[2] - x[2] * y[1],
            x[2] * y[0] - x[0] * y[2],
            x[0] * y[1] - x[1] * y[0],
        ) == z
        assert xyz(a.heel) == tuple(map(D, expected(22)[name]))
        assert xyz(a.member_reference_global) == tuple(map(D, expected(23)[name]))
        assert xyz(a.support_reference_global) == tuple(map(D, expected(24)[name]))
        assert xyz(a.member_reference) == tuple(map(D, expected(21)["r_M_A_B_C_in"]))
        assert xyz(a.support_reference) == tuple(map(D, expected(21)["r_S_A_B_C_in"]))
        numbers = expected(15 if i < 2 else 16)
        geom = a.specification.geometry
        assert [
            v.to(Unit.IN).magnitude
            for v in (
                geom.length,
                geom.member_leg,
                geom.support_leg,
                geom.thickness,
                geom.inside_radius,
            )
        ] == [D(numbers[k]) for k in ("L_A_in", "b_M_in", "b_S_in", "t_A_in", "r_i_in")]
    assert len({a.group_id for a in g.wall_anchors}) == expected(14)["count"]


def test_g26_g29_slice5_native(case: WIWallMomentRequest, preview: app.WIWallMomentPreview) -> None:
    b, a = case.beam, case.actions
    direct = calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(
            WIMomentSectionInput(b.depth, b.flange_width, b.web_thickness, b.flange_thickness),
            WIMomentActionInput(
                a.axial,
                a.major_shear,
                a.structural_major_moment,
                a.minor_shear,
                a.minor_moment,
                a.torsion,
            ),
        )
    )
    assert preview.slice5 == direct
    for component, n in zip(direct.components, (26, 27, 28), strict=True):
        assert component.wrench.force_lvt.l.to(Unit.KIP).magnitude == D(expected(n)["N_kip"])
        assert component.wrench.moment_lvt.t.to(Unit.KIP_IN).magnitude == D(
            expected(n)["m_structural_kip_in"]
        )
    assert preview.equilibrium is not None
    assert preview.equilibrium.slice5_algebraic_proof


@pytest.mark.parametrize(("index", "golden"), [(0, 30), (1, 33), (2, 38), (3, 41)])
def test_g30_g49_complete_native_core(
    index: int, golden: int, preview: app.WIWallMomentPreview
) -> None:
    result = preview.connectors[index]
    angle = preview.geometry.angles[index]
    member = result.core.request.member_action
    assert xyz(member.force, Unit.KIP) == tuple(map(D, expected(golden)["F_A_B_C_kip"]))
    assert xyz(member.moment, Unit.KIP_IN) == tuple(map(D, expected(golden)["M_A_B_C_kip_in"]))
    direct = resolve_angle_connector(
        AngleCoreRequest(angle.specification.geometry, angle.frame, member, angle.support_reference)
    )
    assert result.core == direct
    assert (
        components(direct.equilibrium.force)
        == components(direct.equilibrium.moment)
        == (Fraction(0),) * 3
    )
    assert result.allocation_fraction == D(".5" if index > 1 else "1")
    assert preview.allocation_method == expected(36)["method"]


@pytest.mark.parametrize("index", range(4))
def test_g50_g58_instep_source_boundaries(
    index: int, case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    result, angle = preview.connectors[index], preview.geometry.angles[index]
    registry = WallMomentSourceRegistry()
    provider = evaluate_connector_source(case, angle, result.core, registry)
    assert provider.provider_id == expected(50)["provider"]
    assert provider.status == "SOURCE_REQUIRED"
    assert isinstance(provider.detail, FRPAngleDetail)
    test_provider = evaluate_angle_provider(result.core, "FRP", instep_test_context())
    assert isinstance(test_provider.detail, FRPAngleDetail)
    instep = test_provider.detail.instep
    assert instep is not None
    assert instep.demand.to(Unit.KIP).magnitude == abs(D(expected(51 + index)["F_A_heel_kip"]))
    if index > 1:
        assert instep.factors.design_resistance.to(Unit.KIP).magnitude == D(
            expected(51 + index)["test_phi_R_kip"]
        )
        assert instep.utilization == D(expected(51 + index)["test_U"])
    else:
        assert instep.utilization == 0
    attachment = evaluate_attachment_source(case, angle, result.core, registry)
    assert attachment.method == expected(56)["id"] == ATTACHMENT_METHOD
    assert attachment.check.status == "SOURCE_REQUIRED"
    assert not attachment.invented_prying
    assert attachment.individual_bolt_axis_forces is None
    ctx = provider_context(case, angle, result.core, attachment=True)
    changed = replace(
        result.core,
        request=replace(
            result.core.request,
            member_action=replace(
                result.core.request.member_action,
                force=replace(result.core.request.member_action.force, x=q(1, Unit.KIP)),
            ),
        ),
    )
    assert frp_source_binding(result.core, ctx) != frp_source_binding(
        changed, provider_context(case, angle, changed, attachment=True)
    )
    assert len(ATTACHMENT_COVERAGE) == 5


def test_g59_g63_g75_g78_physical_bolts(preview: app.WIWallMomentPreview) -> None:
    for index, n in ((0, 59), (1, 59), (2, 60), (3, 60)):
        coords = grid(preview.geometry.angles[index].specification.member_pattern)
        assert [(a, b) for _, a, b in coords] == [
            (D(p["A_in"]), D(p["B_in"])) for p in expected(n)["coordinates_A_B_in"]
        ]
        support = grid(preview.geometry.angles[index].specification.support_pattern)
        assert [(a, b) for _, a, b in support] == [
            (D(p["A_in"]), D(p["C_in"]))
            for p in expected(75 if index < 2 else 76)["coordinates_A_C_in"]
        ]
    member = preview.geometry.member_bolts
    assert len(member) == 12
    assert len({b.group_id for b in member}) == 3
    assert sum(len(b.layers) == 3 for b in member) == 4
    assert all(len(b.layers) == (3 if b.group_id == "COMMON_WEB" else 2) for b in member)
    for bolt in member:
        assert bolt.start != bolt.end
        assert not bolt.blind
    assert len(preview.geometry.wall_anchors) == 16
    assert all(
        b.blind
        and b.end.x.magnitude < 0 < b.start.x.magnitude
        and b.exterior_washer_count == 1
        and b.individual_force is None
        and b.capacity is None
        for b in preview.geometry.wall_anchors
    )


@pytest.mark.parametrize("index", [0, 1])
def test_g64_g65_native_flange_verbatim(
    index: int, case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    angle, result = preview.geometry.angles[index], preview.connectors[index]
    native_input = flange_stage25_input(case, angle, result.core.request.member_action)
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        direct = calculate_eccentric_bolt_group_demand(native_input)
    assert result.flange_demand == direct
    assert result.web_demand is None
    assert direct.scenarios


@pytest.mark.parametrize(("index", "n"), [(2, 66), (3, 68)])
def test_g66_g70_direct_slice8(index: int, n: int, preview: app.WIWallMomentPreview) -> None:
    e = expected(n)
    coords = expected(60)["coordinates_A_B_in"]
    direct = calculate_in_plane_wrench_demand(
        InPlaneWrenchRequest(
            tuple(
                WrenchBolt(f"B_R{i // 2 + 1}_L{i % 2 + 1}", p["A_in"], p["B_in"])
                for i, p in enumerate(coords)
            ),
            (D(0), D(2)),
            e["F_A_kip"],
            e["F_B_kip"],
            e["M_C_R_kip_in"],
            Unit.IN,
            Unit.KIP,
            Unit.KIP_IN,
        )
    )
    integrated = preview.connectors[index].web_demand
    assert integrated == direct
    assert preview.connectors[index].flange_demand is None
    assert direct.solution.centroid_moment == direct.solution.reference_moment
    assert direct.solution.proof is not None
    assert direct.solution.proof.passed
    assert direct.solution.in_units(Unit.IN, Unit.KIP).centroid == (Fraction(0), Fraction(2))


def test_g71_g74_out_of_plane_and_planes(
    case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    result = evaluate_wi_wall_moment(case)
    assert len(result.common_web_bolts) == 4
    for bolt in result.common_web_bolts:
        assert bolt.method == expected(71)["method"]
        assert bolt.physical_shear_plane_count == 2
        assert not bolt.source_authorized
        assert bolt.per_plane_design_capacity is None
        assert bolt.outer_plane.source_demand_fingerprint in {
            c.web_demand.fingerprint for c in preview.connectors if c.web_demand is not None
        }
    for i, c in enumerate(preview.connectors):
        out = c.out_of_plane_attachment_components
        assert out == (
            c.core.request.member_action.force.z,
            c.core.request.member_action.moment.x,
            c.core.request.member_action.moment.y,
        )
        assert out[1].magnitude != 0
        assert (out[2].magnitude != 0) == (i >= 2)


def test_g79_g93_relational_wall(preview: app.WIWallMomentPreview) -> None:
    forces = []
    moments = []
    for result, angle in zip(preview.connectors, preview.geometry.angles, strict=True):
        native = result.core.connector_on_support
        axes = angle.frame.a, angle.frame.b, angle.frame.c
        f = cast(
            Rational3,
            tuple(
                sum(
                    (Fraction(axes[k][j]) * components(native.force)[k] for k in range(3)),
                    Fraction(0),
                )
                for j in range(3)
            ),
        )
        m = cast(
            Rational3,
            tuple(
                sum(
                    (Fraction(axes[k][j]) * components(native.moment)[k] for k in range(3)),
                    Fraction(0),
                )
                for j in range(3)
            ),
        )
        independent = AngleWrench(
            angle.support_reference_global,
            quantity_vector(f, Unit.N),
            quantity_vector(m, Unit.N_MM),
        )
        assert independent == result.support_global
        shifted = shift_angle_wrench(independent, quantity_vector((Fraction(0),) * 3, Unit.MM))
        assert shifted == result.support_at_wall
        forces.append(components(shifted.force))
        moments.append(components(shifted.moment))
    handoff = preview.wall_handoff
    reaction = preview.wall_reaction
    eq = preview.equilibrium
    assert handoff is not None
    assert reaction is not None
    assert eq is not None
    assert components(handoff.force) == tuple(
        sum((f[i] for f in forces), Fraction(0)) for i in range(3)
    )
    assert components(handoff.moment) == tuple(
        sum((m[i] for m in moments), Fraction(0)) for i in range(3)
    )
    assert components(reaction.force) == tuple(-v for v in components(handoff.force))
    assert components(reaction.moment) == tuple(-v for v in components(handoff.moment))
    assert eq.proof_passed
    assert all(eq.connector_core_proofs)
    assert all(eq.web_group_proofs)
    assert eq.serialized_force_diagnostic.x.to(Unit.KIP).magnitude == D("3E-79")
    assert eq.serialized_moment_diagnostic.z.to(Unit.KIP_IN).magnitude == D("6E-79")
    assert eq.structural_major_moment_diagnostic.to(Unit.KIP_IN).magnitude == D("-6E-79")
    assert not eq.tolerance_used
    assert not eq.residual_redistribution
    assert preview.whole_connection_status == expected(92)["status"]


def qualified(core: AngleCoreResult, ctx: FRPAngleContext) -> QualifiedFRPAngleSource:
    pairs = (("50", "40"), ("60", "80"), ("30", "30"), ("24", "20"), ("40", "40"), ("36", "48"))
    strengths = tuple(
        SignedDesignStrength(
            q(p, Unit.KIP if i < 3 else Unit.KIP_IN), q(n, Unit.KIP if i < 3 else Unit.KIP_IN)
        )
        for i, (p, n) in enumerate(pairs)
    )
    source = EngineeringPropertySource(
        EngineeringPropertySourceKind.TEST_QUALIFIED_DATA,
        "TEST_ONLY_STAGE42_DO_NOT_EXPOSE",
        "RC1-R7",
        PropertySourceConfirmation.TEST_QUALIFIED,
        ("STAGE42_ARITHMETIC_ONLY",),
        True,
        approval_authority_id="TEST_ONLY",
        qualification_record_ids=("NOT_PHYSICAL_QUALIFICATION",),
    )
    return QualifiedFRPAngleSource(
        source, frp_source_binding(core, ctx), strengths, tuple(QualifiedCoverage), True
    )


@pytest.mark.parametrize("index", range(4))
def test_g94_g102_qualified_native_values(
    index: int, case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    angle, c = preview.geometry.angles[index], preview.connectors[index].core
    angle = replace(
        angle,
        specification=replace(
            angle.specification,
            connector_source_reference="test",
            attachment_source_reference="test",
        ),
    )
    ctx = provider_context(case, angle, c)
    actx = provider_context(case, angle, c, attachment=True)
    src, asrc = qualified(c, ctx), qualified(c, actx)
    registry = WallMomentSourceRegistry(
        (
            WallMomentQualifiedSource("test", angle.connector_id, src),
            WallMomentQualifiedSource("test", angle.connector_id, asrc, True, ATTACHMENT_COVERAGE),
        )
    )
    provider = evaluate_connector_source(case, angle, c, registry)
    assert provider == evaluate_angle_provider(c, "FRP", replace(ctx, qualified_source=src))
    assert provider.status == expected(95 + index)["expected_status"]
    attachment = evaluate_attachment_source(case, angle, c, registry)
    assert attachment.check == _body(
        replace(c, heel=c.request.member_action), replace(actx, qualified_source=asrc)
    )
    assert attachment.check.status == expected(99 + index)["expected_status"]
    assert c == preview.connectors[index].core


def test_g103_r7_native_selection(
    case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    result = evaluate_wi_wall_moment(case)
    angle, c = preview.geometry.angles[0], preview.connectors[0]
    assert c.flange_demand is not None
    mapping = flange_local_request(case, angle, c.core.request.member_action.force.y)
    direct = evaluate_multirow_connection_with_resolved_demand(mapping, c.flange_demand)
    assert result.local_checks[0].native_flange_response == direct
    assert direct.automatic_group_mode_integration is not None
    assert (
        result.native_governing_check_ids
        == direct.automatic_group_mode_integration.governing_supported_check_ids
        == ("FIRST_ROW:TOP_FLANGE_ANGLE",)
    )
    assert result.status == expected(103)["governing_status"] == "FAIL"
    assert result.status_reason == expected(103)["status_precedence_reason"]
    kinds = {
        r.limit_state.value for r in result.native_failed_checks if r.layer_id == "TOP_FLANGE_ANGLE"
    }
    assert {"FIRST_ROW_NET_TENSION", "PIN_BEARING", "INTERROW_SHEAR_OUT"} <= kinds
    assert len(result.missing_sources) == 8
    assert (
        angle_fingerprint(create_locked_ice_material_snapshot())
        == expected(103)["material_fingerprint"]
    )
    for lap, key in ((".6", "flange_factor_fingerprint"), ("1", "web_factor_fingerprint")):
        assert (
            angle_fingerprint(
                MultiRowFactorContext(
                    D(1), D(lap), D(".75"), PitchFactorSource.AUTOMATIC_CONSTANT_PITCH, None
                )
            )
            == expected(103)[key]
        )
    assert _execution_bundle(mapping, _resolve(mapping)).factors.pitch_factor_c_delta == D(".75")


def test_g104_g107_status_and_preview(case: WIWallMomentRequest) -> None:
    assert (
        aggregate_internal_status(
            ("PASS", "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED")
        )[0]
        == expected(104)["status"]
    )
    assert aggregate_internal_status(("FAIL", "SOURCE_REQUIRED"))[0] == "FAIL"
    assert aggregate_internal_status(("SOURCE_REQUIRED",))[0] == "SOURCE_REQUIRED"
    assert aggregate_internal_status(("NOT_EVALUATED",))[0] == "NOT_EVALUATED"
    assert aggregate_internal_status(())[0] == "NOT_EVALUATED"
    assert aggregate_internal_status(("INVALID_GEOMETRY", "FAIL"))[0] == "INVALID_GEOMETRY"
    with ExitStack() as stack:
        for name in (
            "evaluate_connector_source",
            "evaluate_attachment_source",
            "_bearing",
            "_web_group_checks",
            "evaluate_channel_two_plane_bolt",
            "evaluate_multirow_connection_with_resolved_demand",
        ):
            stack.enter_context(
                patch(
                    "frp_master_connection.application.wi_wall_moment_design." + name,
                    side_effect=AssertionError("Preview attempted resistance"),
                )
            )
        slice5 = stack.enter_context(
            patch.object(
                app,
                "calculate_wi_moment_component_resultants",
                wraps=calculate_wi_moment_component_resultants,
            )
        )
        cores = stack.enter_context(
            patch.object(
                app,
                "resolve_angle_connector",
                wraps=resolve_angle_connector,
            )
        )
        p = app.preview_wi_wall_moment(case)
        assert slice5.call_count == 1
        assert cores.call_count == 4
    assert not p.resistance_evaluated
    assert len(p.connectors) == 4
    assert p.whole_connection_status == "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    assert len(p.source_plans) == 8


def test_g127_g128_inherited_engines_dependencies_and_freeze_identity() -> None:
    from tests.calculation.test_scope_boundaries import (
        _FROZEN_DEPENDENCIES,
        _historical_dependency_bytes,
    )
    from tests.calculation.test_stage_4_1_beam_moment_splice_family_freeze_manifest import audit

    root = Path(__file__).resolve().parents[3]
    records = json.loads((root / "docs/qa/STAGE_4_2_INHERITED_IDENTITIES.json").read_text())
    assert records["baseline"] == "473a3c8cd43f13022d254dae2477084895478c74"
    workflow_identities = {
        "historical_pre_ssmc_3_main": {
            "commit": "9a9b4529faa1287e8df8360daceed2687e1e2b57",
            "blob": "2169d74e008b597793102c0bba25505d840ebdcb",
            "expected_tests": b"--expected-tests 7267",
        },
        "ssmc_3_analytical_successor": {
            "blob": "89687a8099efdf626f0acb209a6d185a2e58d2dd",
            "sha256": "01356CD33808B5DBB01FE150BAB79281924681F8BA109F9AA453F096F14BF98A",
            "expected_tests": b"--expected-tests 7291",
        },
    }
    frozen_ssmc = (root / "backend/src/frp_master_connection/application/ssmc.py").read_bytes()
    assert hashlib.sha256(frozen_ssmc).hexdigest().upper() == (
        "54774E036BBA2061361EDAD5E34DF84FA7D9ED59C8E520342411D8131E202765"
    )
    for item in records["files"]:
        path = item["path"]
        raw = (root / path).read_bytes().replace(b"\r\n", b"\n")
        if path in _FROZEN_DEPENDENCIES:
            raw = _historical_dependency_bytes(root, path)
        elif path == ".github/workflows/ci.yml":
            historical_identity = workflow_identities["historical_pre_ssmc_3_main"]
            successor_identity = workflow_identities["ssmc_3_analytical_successor"]
            successor_blob = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
            ).hexdigest()
            assert successor_blob == successor_identity["blob"]
            assert hashlib.sha256(raw).hexdigest().upper() == successor_identity["sha256"]
            current_count = successor_identity["expected_tests"]
            baseline_count = historical_identity["expected_tests"]
            historical_count = b"--expected-tests 6609"
            assert raw.count(current_count) == 1
            assert raw.count(baseline_count) == 0
            assert raw.count(historical_count) == 0
            baseline_raw = raw.replace(current_count, baseline_count)
            baseline_blob = hashlib.sha1(
                b"blob " + str(len(baseline_raw)).encode() + b"\0" + baseline_raw,
                usedforsecurity=False,
            ).hexdigest()
            assert historical_identity["commit"] == "9a9b4529faa1287e8df8360daceed2687e1e2b57"
            assert baseline_blob == historical_identity["blob"]
            raw = baseline_raw.replace(baseline_count, historical_count)
            historical_blob = hashlib.sha1(  # noqa: S324 - Git object identity
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            assert historical_blob == "1f8a0f207617aa154d0fbe3b9810b9d1a9b7dbf8"
            successor = b"""      - name: Run deterministic backend shards with combined coverage
        run: >-
          python ../scripts/run_backend_windows_shards.py
          --shards 4
          --expected-tests 6609
"""
            historical = b"""      - name: Run tests with line and branch coverage
        run: >-
          python -m pytest
          --cov=frp_master_connection
          --cov-branch
          --cov-report=term-missing
          --cov-fail-under=100
"""
            assert raw.count(successor) == 1
            raw = raw.replace(successor, historical)
        git_blob = b"blob " + str(len(raw)).encode() + b"\0" + raw
        assert hashlib.sha1(git_blob, usedforsecurity=False).hexdigest() == item["blob"]
    # Resolve the immutable historical family, never successor HEAD:frontend/src.
    assert audit().source in {"tag", "object", "manifest_only"}
    assert set(expected(127).values()) == {"EXACT"}
    assert expected(128)["slice8_test_only_stabilization_preserved"]
    assert not expected(128)["later_moment_family_begun"]


@pytest.mark.parametrize(
    ("n", "p", "v", "m"),
    [
        (108, "20", "0", "0"),
        (109, "0", "-10", "0"),
        (110, "0", "0", "100"),
        (111, "-20", "0", "0"),
        (112, "0", "10", "0"),
        (113, "0", "0", "-100"),
    ],
)
def test_g108_g113_pure_and_signed(
    n: int, p: str, v: str, m: str, case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    r = replace(
        case,
        actions=replace(
            case.actions,
            axial=q(p, Unit.KIP),
            major_shear=q(v, Unit.KIP),
            structural_major_moment=q(m, Unit.KIP_IN),
        ),
    )
    result = evaluate_wi_wall_moment(r)
    x = result.preview
    assert x.geometry == preview.geometry
    assert x.equilibrium is not None
    assert x.equilibrium.proof_passed
    assert x.wall_handoff is not None
    if n == 108:
        assert [c.wrench.force_lvt.l.to(Unit.KIP).magnitude for c in x.slice5.components] == [
            D("6.4"),
            D("7.2"),
            D("6.4"),
        ]
    if n == 109:
        assert all(
            components(c.core.heel.force) == components(c.core.heel.moment) == (Fraction(0),) * 3
            for c in x.connectors[:2]
        )
    if n == 110:
        assert x.equilibrium.serialized_moment_diagnostic.z.to(Unit.KIP_IN).magnitude == D("2E-78")
        assert x.equilibrium.structural_major_moment_diagnostic.to(Unit.KIP_IN).magnitude == D(
            "-2E-78"
        )
        assert all(
            c.web_demand is not None and c.web_demand.solution.centroid_moment != 0
            for c in x.connectors[2:]
        )


@pytest.mark.parametrize(
    ("field", "unit", "reason"),
    [
        ("minor_shear", Unit.KIP, "MINOR_SHEAR"),
        ("minor_moment", Unit.KIP_IN, "MINOR_AXIS_MOMENT"),
        ("torsion", Unit.KIP_IN, "TORSION"),
    ],
)
def test_g114_g116_unsupported_actions(
    field: str, unit: Unit, reason: str, case: WIWallMomentRequest
) -> None:
    with pytest.raises(ValueError, match=reason):
        replace(case.actions, **{field: q(1, unit)})


@pytest.mark.parametrize("n", [117, 118, 119, 120, 121])
def test_g117_g121_invalid_geometry(n: int, case: WIWallMomentRequest) -> None:
    if n == 117:
        r = replace(case, gap=q(0))
    elif n == 118:
        web = replace(case.positive_web, geometry=replace(case.positive_web.geometry, length=q(12)))
        r = replace(case, positive_web=web, negative_web=web)
    elif n == 119:
        r = replace(case, wall=replace(case.wall, width=D(3)))
    elif n == 120:
        r = replace(
            case, negative_web=replace(case.negative_web, connector_source_reference="unmatched")
        )
    else:
        r = replace(
            case, bottom=replace(case.bottom, geometry=replace(case.bottom.geometry, length=q(9)))
        )
    result = evaluate_wi_wall_moment(r)
    assert result.status == expected(n)["status"]
    assert expected(n)["reason"] in result.preview.geometry.reasons
    assert not result.preview.design_check_ready
    assert not result.resistance_evaluated


def test_g122_source_invalid(case: WIWallMomentRequest, preview: app.WIWallMomentPreview) -> None:
    angle = preview.geometry.angles[0]
    core = preview.connectors[0].core
    angle = replace(
        angle, specification=replace(angle.specification, connector_source_reference="wrong")
    )
    source = qualified(core, provider_context(case, angle, core))
    source = replace(source, binding=replace(source.binding, geometry="0" * 64))
    result = evaluate_connector_source(
        case,
        angle,
        core,
        WallMomentSourceRegistry((WallMomentQualifiedSource("wrong", angle.connector_id, source),)),
    )
    assert result.status == expected(122)["status"]


def test_g123_g124_determinism(case: WIWallMomentRequest, preview: app.WIWallMomentPreview) -> None:
    us = evaluate_wi_wall_moment(case)
    si = evaluate_wi_wall_moment(default_wi_wall_moment_request(EngineeringUnitSystem.SI))
    assert us.result_fingerprint == si.result_fingerprint
    assert preview.engineering_fingerprint == si.preview.engineering_fingerprint
    assert (
        preview.engineering_fingerprint
        == app.preview_wi_wall_moment(
            replace(case, request_id="presentation-case-id")
        ).engineering_fingerprint
    )
    assert all(
        a.core.fingerprint == b.core.fingerprint
        for a, b in zip(preview.connectors, si.preview.connectors, strict=True)
    )
    assert "R7_NATIVE_GOVERNING_SELECTION" in preview.numeric_authority


def test_g125_visual_source_contract(preview: app.WIWallMomentPreview) -> None:
    assert len(preview.geometry.parts) == 12
    assert (
        len({b.group_id for b in preview.geometry.member_bolts})
        == expected(125)["member_bolt_groups"]
    )
    assert (
        len({b.group_id for b in preview.geometry.wall_anchors})
        == expected(125)["wall_anchor_groups"]
    )
    assert sum(p.material_region is not None for p in preview.geometry.parts) == 11


@pytest.mark.parametrize(
    ("p", "v", "m"), [(20, 0, 0), (20, 0, 100), (-20, 0, -100), (0, 0, 100), (0, -10, 0), (0, 0, 0)]
)
def test_native_web_group_path_envelopes_and_full_beam_demand(
    p: int,
    v: int,
    m: int,
    case: WIWallMomentRequest,
) -> None:
    changed = replace(
        case,
        actions=replace(
            case.actions,
            axial=q(p, Unit.KIP),
            major_shear=q(v, Unit.KIP),
            structural_major_moment=q(m, Unit.KIP_IN),
        ),
    )
    result = evaluate_wi_wall_moment(changed)
    groups = [g for g in result.local_checks if "WEB" in g.layer_id]
    assert len(groups) == 3
    assert result.status != "PASS"
    if p and not v and m:
        positive = next(g for g in groups if g.layer_id == "POSITIVE_WEB_ANGLE")
        beam = next(g for g in groups if g.layer_id == "WI_WEB")
        assert len(positive.native_line_results) == 2
        for a, b in zip(positive.native_line_results, beam.native_line_results, strict=True):
            if a.required_line_demand is not None:
                assert b.required_line_demand is not None
                assert Fraction(b.required_line_demand.canonical_magnitude) == 2 * Fraction(
                    a.required_line_demand.canonical_magnitude
                )
            assert "NOT_EVALUATED" in positive.scope_status
    elif p and not v:
        assert all(g.scope_status == "NATIVE_CONCENTRIC_GROUP_CHECKS" for g in groups)
    elif not p and not v and not m:
        assert result.web_bearing == ()
        assert all(g.scope_status == "NOT_REQUIRED_ZERO_DEMAND" for g in groups)


def test_explicit_holes_remain_physical_without_false_standard_net_area(
    case: WIWallMomentRequest,
) -> None:
    flange = replace(case.top, fastener=replace(case.top.fastener, hole_diameter=q(".6")))
    web = replace(
        case.positive_web, fastener=replace(case.positive_web.fastener, hole_diameter=q(".6"))
    )
    result = evaluate_wi_wall_moment(
        replace(case, top=flange, bottom=flange, positive_web=web, negative_web=web)
    )
    assert result.preview.geometry.status == "VALID"
    assert all(b.hole_diameter == q(".6") for b in result.preview.geometry.member_bolts)
    assert all(
        g.scope_status == "NOT_EVALUATED_NONSTANDARD_HOLE_GROUP_PATH_AUTHORITY_REQUIRED"
        for g in result.local_checks
    )
    assert result.flange_bearing
    assert result.web_bearing
    assert result.native_failed_checks == ()
    native = result.preview.connectors[0].flange_demand
    assert native is not None
    input_value = flange_stage25_input(
        replace(case, top=flange, bottom=flange, positive_web=web, negative_web=web),
        result.preview.geometry.angles[0],
        result.preview.connectors[0].core.request.member_action,
    )
    assert all(b.hole_diameter == D(".6") for b in input_value.physical_geometry.bolts)


@pytest.mark.parametrize(
    "mutation",
    [
        "member_gauge",
        "member_pitch",
        "support_gauge",
        "support_pitch",
        "member_edge",
        "support_edge",
        "locked_pattern",
    ],
)
def test_physical_hole_and_lock_boundaries(mutation: str, case: WIWallMomentRequest) -> None:
    angle = case.top
    if mutation.startswith("member_"):
        key = "center" if mutation == "member_edge" else mutation.removeprefix("member_")
        angle = replace(
            angle,
            member_pattern=replace(angle.member_pattern, **cast(dict[str, Any], {key: q(".1")})),
        )
    elif mutation.startswith("support_"):
        key = "center" if mutation == "support_edge" else mutation.removeprefix("support_")
        angle = replace(
            angle,
            support_pattern=replace(angle.support_pattern, **cast(dict[str, Any], {key: q(".1")})),
        )
    else:
        angle = replace(angle, member_pattern=replace(angle.member_pattern, gauge=q("4.5")))
    changed = replace(
        case, top=angle, bottom=case.bottom if mutation == "locked_pattern" else angle
    )
    result = app.preview_wi_wall_moment(changed)
    assert result.status == "INVALID_GEOMETRY"
    assert not result.design_check_ready


def test_source_registry_unique_reference_and_attachment_coverage(
    case: WIWallMomentRequest, preview: app.WIWallMomentPreview
) -> None:
    angle = preview.geometry.angles[0]
    core = preview.connectors[0].core
    package = qualified(core, provider_context(case, angle, core, attachment=True))
    with pytest.raises(ValueError, match="reference and physical connector ID"):
        WallMomentQualifiedSource("", angle.connector_id, package)
    record = WallMomentQualifiedSource("test", angle.connector_id, package, True, ())
    with pytest.raises(ValueError, match="unique"):
        WallMomentSourceRegistry((record, record))
    selected = replace(
        angle, specification=replace(angle.specification, attachment_source_reference="test")
    )
    actual = evaluate_attachment_source(case, selected, core, WallMomentSourceRegistry((record,)))
    assert actual.check.status == "NOT_EVALUATED_QUALIFIED_ATTACHMENT_COVERAGE_MISSING"


def test_domain_fail_closed_inputs(case: WIWallMomentRequest) -> None:
    from frp_master_connection.domain.channel_moment_splice import (
        default_channel_moment_splice_request,
    )
    from frp_master_connection.domain.web_splice import WebSpliceBeamGeometry
    from frp_master_connection.domain.wi_wall_moment import WallMomentPattern, _length

    with pytest.raises(TypeError, match="length quantity"):
        _length(q(1, Unit.KIP), "not-length")
    with pytest.raises(ValueError, match="must be positive"):
        _length(q(0), "zero")
    for kwargs in ({"axial": q(1)}, {"major_shear": q(1)}, {"structural_major_moment": q(1)}):
        with pytest.raises(ValueError, match=r"must be a (force|moment)"):
            replace(case.actions, **kwargs)
    for bad in (0, True, 1.5):
        with pytest.raises(ValueError, match="positive integers"):
            WallMomentPattern(cast(int, bad), 2, q(1), q(1), q(1))
    with pytest.raises(ValueError, match="unchanged locked ICE"):
        replace(case.top, material_id="invented")
    with pytest.raises(ValueError, match="NO_CLIENT_STRENGTH"):
        replace(case.top, fastener=replace(case.top.fastener, nominal_shear_stress=q(50, Unit.KSI)))
    with pytest.raises(ValueError, match="identity/contract"):
        replace(case, request_id=" ")
    with pytest.raises(ValueError, match="ONLY_WI_BEAM"):
        replace(
            case, beam=cast(WebSpliceBeamGeometry, default_channel_moment_splice_request().beam)
        )
    with pytest.raises(ValueError, match="source length"):
        replace(case, source_length_unit=Unit.KIP)


def test_nonexact_inherited_proof_is_never_promoted(
    case: WIWallMomentRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = calculate_wi_moment_component_resultants

    def broken(value: WIMomentCalculationInput) -> WIMomentComponentResultants:
        result = original(value)
        return replace(
            result, equilibrium=replace(result.equilibrium, axial_equilibrium_exact=False)
        )

    monkeypatch.setattr(app, "calculate_wi_moment_component_resultants", broken)
    with pytest.raises(ArithmeticError, match="EXACT_EQUILIBRIUM_PROOF_FAILED"):
        app.preview_wi_wall_moment(case)
