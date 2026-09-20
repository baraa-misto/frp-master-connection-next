"""Stage 4.3 native integration, full support/load/unit sweep and physical paths."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from frp_master_connection.application.wi_frp_support_moment_design import (
    evaluate_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    preview_wi_frp_support_moment,
    support_uvn,
)
from frp_master_connection.application.wi_frp_support_moment_sources import (
    EMPTY_SOURCES,
    response_binding,
)
from frp_master_connection.application.wi_wall_moment_demand import flange_stage25_input
from frp_master_connection.application.wi_wall_moment_geometry import inch, q
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleWrench,
    Rational3,
    components,
    quantity_vector,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import calculate_eccentric_bolt_group_demand
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.wi_moment_resultants import (
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
)
from frp_master_connection.domain.wi_frp_support_moment import (
    FACES,
    SupportMode,
    WIFrpSupportMomentRequest,
    default_frp_support_moment_request,
)
from frp_master_connection.domain.wi_wall_moment import WIWallMomentRequest
from tests.application.wi_frp_support_fixture_views import native_catalogue_entry

ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = ROOT / "backend/tests/golden/stage_4_3_acceptance_matrix_rc1.json"
MATRIX = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
LOADS: list[dict[str, str]] = MATRIX["load_sweep"]
CATALOGUE = json.loads(
    (ROOT / "docs/qa/STAGE_4_3_NATIVE_FIXTURE_CATALOGUE.json").read_text(encoding="utf-8")
)
D = Decimal


def request(
    mode: SupportMode = SupportMode.WI_FLANGE, load: int = 0, *, si: bool = False
) -> WIFrpSupportMomentRequest:
    value = default_frp_support_moment_request(mode, si=si)
    f, m = (Unit.KN, Unit.KN_MM) if si else (Unit.KIP, Unit.KIP_IN)
    action = LOADS[load]
    return replace(
        value,
        actions=replace(
            value.actions,
            axial=q(action["P_kip"], Unit.KIP).to(f),
            major_shear=q(action["V_kip"], Unit.KIP).to(f),
            structural_major_moment=q(action["M_structural_kip_in"], Unit.KIP_IN).to(m),
        ),
    )


def test_t43_001_019_authority_hash_and_literal_acceptance_references() -> None:
    assert (
        hashlib.sha256(MATRIX_PATH.read_bytes()).hexdigest().upper()
        == "3E277AF2388F15BA5C2CA2AA0B52ED9AAE7064F15DCFA354C8C233B174EB5043"
    )
    order = ROOT / "docs/qa/STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_CODEX_ORDER_RC1.md"
    assert (
        hashlib.sha256(order.read_bytes()).hexdigest().upper()
        == "1872CB38BE1A3CFED548CE6DEE5D4D183DAD3F3D3957197D61E376EB6D62BC33"
    )
    assert (
        order.read_text(encoding="utf-8")
        .rstrip()
        .endswith(
            "**END OF STAGE 4.3 W/I BEAM FRP SUPPORT MOMENT CONNECTION ORDER RC1 "
            "— DO NOT PROCEED IF THIS LINE IS MISSING**"
        )
    )
    assert [c["id"] for c in MATRIX["acceptance_checks"]] == [f"T43-{i:03}" for i in range(1, 91)]
    fixture_ids = {f["id"] for f in MATRIX["independent_fixtures"]}
    assert len(fixture_ids) == 6
    for check in MATRIX["acceptance_checks"]:
        assert set(check.get("fixture_ids", ())).issubset(fixture_ids)
    assert not any((EMPTY_SOURCES.responses, EMPTY_SOURCES.fasteners, EMPTY_SOURCES.local_zones))


@pytest.mark.parametrize("mode", list(SupportMode))
@pytest.mark.parametrize("load", range(8), ids=[x["id"] for x in LOADS])
def test_t43_five_support_eight_load_dual_unit_native_design_sweep(
    mode: SupportMode, load: int
) -> None:
    us, si = request(mode, load), request(mode, load, si=True)
    results = [evaluate_wi_frp_support_moment(r) for r in (us, si)]
    for r, result in zip((us, si), results, strict=True):
        assert native_catalogue_entry(result) == CATALOGUE["modes"][mode.value][LOADS[load]["id"]]
        p = result.preview
        assert p.geometry.status == "VALID", p.geometry.reasons
        assert p.design_check_ready
        assert result.resistance_evaluated
        assert p.equilibrium is not None
        assert p.equilibrium.proof_passed
        assert len(p.connectors) == 4
        assert len(p.geometry.support_bolts) == 16
        assert len({b.hardware.group_id for b in p.geometry.support_bolts}) == 4
        assert len(p.geometry.member_bolts) == 12
        b, a = r.beam, r.actions
        independent = calculate_wi_moment_component_resultants(
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
        assert p.slice5 == independent
        for spec, transfer in zip(r.angles, p.connectors, strict=True):
            # Independent core invocation consumes the complete exposed member wrench.
            expected = resolve_angle_connector(
                AngleCoreRequest(
                    spec.geometry,
                    transfer.core.request.frame,
                    transfer.core.request.member_action,
                    transfer.core.request.support_reference,
                )
            )
            assert transfer.core == expected
            assert transfer.support_at_centroid == shift_angle_wrench(
                transfer.support_lvt, p.geometry.support.centroid
            )
            for name in ("reference", "force", "moment"):
                native = components(getattr(transfer.support_lvt, name))
                assert components(getattr(transfer.support_uvn, name)) == (
                    native[1],
                    native[2],
                    native[0],
                )
            if transfer.web_demand is not None:
                # Physical heel-local coordinates are NOT recentered. No M/e recreation.
                w = transfer.core.request.member_action
                bolts = tuple(
                    WrenchBolt(f"B_R{row}_L{line}", across, along)
                    for row, along in enumerate((D("1.25"), D("2.75")), 1)
                    for line, across in enumerate((D("-1.5"), D("1.5")), 1)
                )
                direct = calculate_in_plane_wrench_demand(
                    InPlaneWrenchRequest(
                        bolts,
                        (D(0), D(2)),
                        w.force.x.to(Unit.KIP).magnitude,
                        w.force.y.to(Unit.KIP).magnitude,
                        w.moment.z.to(Unit.KIP_IN).magnitude,
                        Unit.IN,
                        Unit.KIP,
                        Unit.KIP_IN,
                    )
                )
                assert direct == transfer.web_demand
            elif transfer.flange_demand is not None:
                angle = next(
                    a for a in p.geometry.angles if a.connector_id == transfer.connector_id
                )
                native_input = flange_stage25_input(
                    cast(WIWallMomentRequest, r.engineering_input()),
                    angle,
                    transfer.core.request.member_action,
                )
                assert transfer.flange_demand == calculate_eccentric_bolt_group_demand(native_input)
                assert all(
                    inch(b.reference.y) == D(2) for b in (transfer.core.request.member_action,)
                )
        assert p.support_contribution is not None
        assert p.support_reaction is not None
        assert components(p.support_reaction.force) == tuple(
            -x for x in components(p.support_contribution.force)
        )
        assert components(p.support_reaction.moment) == tuple(
            -x for x in components(p.support_contribution.moment)
        )
        assert result.status in {"FAIL", "SOURCE_REQUIRED"}
        assert not result.complete_unqualified_pass_allowed
        assert result.support_response is not None
        assert result.support_response.status == "SOURCE_REQUIRED"
        assert all(b.total_tension_including_prying is None for b in result.support_bolts)
        assert all(b.status == "SOURCE_REQUIRED" for b in result.support_bolts)
        assert "ANCHOR" not in p.disclaimer
        assert "concrete" not in p.disclaimer
        if mode in {SupportMode.HOLLOW_SQUARE, SupportMode.SOLID_SQUARE}:
            assert all(t.support_in_plane_demand is None for t in p.connectors)
        else:
            for t in p.connectors:
                physical = [
                    b
                    for b in p.geometry.support_bolts
                    if b.hardware.group_id == f"{t.connector_id}_SUPPORT_GROUP"
                ]
                w = t.support_uvn
                direct = calculate_in_plane_wrench_demand(
                    InPlaneWrenchRequest(
                        tuple(
                            WrenchBolt(
                                b.hardware.hardware_id,
                                b.support_point.y.canonical_magnitude,
                                b.support_point.z.canonical_magnitude,
                            )
                            for b in physical
                        ),
                        (w.reference.x.canonical_magnitude, w.reference.y.canonical_magnitude),
                        w.force.x.canonical_magnitude,
                        w.force.y.canonical_magnitude,
                        w.moment.z.canonical_magnitude,
                        Unit.MM,
                        Unit.N,
                        Unit.N_MM,
                    )
                )
                assert direct == t.support_in_plane_demand
    assert results[0].preview.engineering_fingerprint == results[1].preview.engineering_fingerprint
    assert results[0].result_fingerprint == results[1].result_fingerprint
    assert response_binding(results[0].preview) == response_binding(results[1].preview)


@pytest.mark.parametrize(("mode", "face"), [(m, f) for m in SupportMode for f in FACES[m]])
def test_t43_023_033_all_eligible_face_paths_and_exterior_hardware(
    mode: SupportMode, face: str
) -> None:
    r = request(mode)
    p = preview_wi_frp_support_moment(replace(r, support=replace(r.support, face=face)))
    assert p.geometry.status == "VALID", p.geometry.reasons
    for b in p.geometry.support_bolts:
        assert b.crossing.valid
        assert b.crossing.physical_face == face
        assert inch(b.hardware.start.x) == D(".5")
        assert inch(b.hardware.end.x) == -b.crossing.depth
        assert b.hardware.exterior_washer_count == 2
        assert b.loaded_planes_status.startswith("SOURCE_REQUIRED")
        e = next(e for e in p.geometry.hardware_envelopes if e.bolt_id == b.hardware.hardware_id)
        assert inch(e.head_start.x) > 0
        assert inch(e.nut_end.x) < -b.crossing.depth
        if mode is SupportMode.HOLLOW_SQUARE:
            assert len(b.crossing.layer_ids) == 2
            assert b.crossing.material_thicknesses == (D(".5"), D(".5"))
            assert b.crossing.depth == D(12)
            assert b.crossing.core_path is not None
        elif mode is SupportMode.SOLID_SQUARE:
            assert len(b.crossing.layer_ids) == 1
            assert b.crossing.material_thicknesses == (D(12),)
    assert len(p.geometry.support_contact_patches) == 4
    assert all(part.material_region is not None for part in p.geometry.parts)


def test_t43_035_presentation_extents_do_not_change_sources_physical_paths_or_design() -> None:
    r = request()
    baseline = evaluate_wi_frp_support_moment(r)
    varied = replace(
        r,
        request_id="different transport identity",
        beam=replace(r.beam, display_length_each_side=q(8)),
        support=replace(r.support, view_length=q(20)),
    )
    result = evaluate_wi_frp_support_moment(varied)
    assert result.result_fingerprint == baseline.result_fingerprint
    assert result.preview.geometry.parts == baseline.preview.geometry.parts
    assert result.preview.geometry.display_parts != baseline.preview.geometry.display_parts
    assert response_binding(result.preview) == response_binding(baseline.preview)
    assert (
        preview_wi_frp_support_moment(request(load=5)).geometry.parts
        == baseline.preview.geometry.parts
    )


@pytest.mark.parametrize(
    "change", ["gapzero", "gaplarge", "pair", "hole", "washer", "overlap", "length", "access"]
)
def test_t43_invalid_physical_geometry_prevents_resistance(change: str) -> None:
    r = request()
    if change.startswith("gap"):
        r = replace(r, gap=q(0 if change == "gapzero" else 1))
    elif change == "pair":
        r = replace(r, bottom=replace(r.bottom, geometry=replace(r.bottom.geometry, length=q(7))))
    elif change == "length":
        r = replace(r, support=replace(r.support, physical_length=q(10)))
    elif change == "access":
        r = request(SupportMode.WI_WEB)
        r = replace(r, support=replace(r.support, depth=q(8)))
    else:
        top = r.top
        if change == "hole":
            top = replace(top, support_fastener=replace(top.support_fastener, hole_diameter=q(2)))
        elif change == "washer":
            top = replace(top, support_hardware=replace(top.support_hardware, washer_diameter=q(3)))
        else:
            top = replace(top, support_pattern=replace(top.support_pattern, gauge=q(".5")))
        r = replace(r, top=top, bottom=top)
    result = evaluate_wi_frp_support_moment(r)
    assert result.status == "INVALID_GEOMETRY"
    assert not result.resistance_evaluated
    assert result.preview.geometry.reasons


def test_t43_preview_never_calls_resistance_or_concrete_orchestrator() -> None:
    with ExitStack() as stack:
        for target in (
            "frp_master_connection.application.wi_wall_moment_orchestration.preview_wi_wall_moment",
            "frp_master_connection.application.wi_frp_support_moment_design.evaluate_wi_frp_support_moment",
            "frp_master_connection.calculation.angle_connector_providers.evaluate_angle_provider",
            "frp_master_connection.calculation.equations.pin_bearing_resistance",
        ):
            stack.enter_context(
                patch(target, side_effect=AssertionError("Resistance/concrete preview leak"))
            )
        p = preview_wi_frp_support_moment(request())
        assert not p.resistance_evaluated
        assert p.design_check_ready


def test_support_frame_is_proper_cyclic_rotation_and_exact_arbitrary_reference_shift() -> None:
    w = AngleWrench(
        quantity_vector((Fraction(1), Fraction(2), Fraction(3)), Unit.MM),
        quantity_vector((Fraction(4), Fraction(5), Fraction(6)), Unit.N),
        quantity_vector((Fraction(7), Fraction(8), Fraction(9)), Unit.N_MM),
    )
    rotated = support_uvn(w)
    assert components(rotated.reference) == (Fraction(2), Fraction(3), Fraction(1))
    assert components(rotated.force) == (Fraction(5), Fraction(6), Fraction(4))
    assert components(rotated.moment) == (Fraction(8), Fraction(9), Fraction(7))
    offset = quantity_vector(cast(Rational3, tuple(Fraction(x) for x in (11, -7, 5))), Unit.MM)
    target = replace(w, reference=offset)
    assert support_uvn(shift_angle_wrench(w, offset)) == shift_angle_wrench(
        rotated, support_uvn(target).reference
    )


@pytest.mark.parametrize(
    "case",
    [
        "length",
        "hardware",
        "provider",
        "strength",
        "support_material",
        "contract",
        "identity",
        "beam_material",
    ],
)
def test_domain_rejects_unregistered_material_and_malformed_physical_identity(case: str) -> None:
    r = request()

    def invalid() -> None:
        if case == "length":
            replace(r.top.member_hardware, washer_thickness=q(0))
        elif case == "hardware":
            replace(r.top.member_hardware, geometry_source=" ")
        elif case == "provider":
            replace(r.top, provider_id="316SS")
        elif case == "strength":
            replace(r.top, fastener=replace(r.top.fastener, nominal_shear_stress=q(40, Unit.KSI)))
        elif case == "support_material":
            replace(r.support, material_id="UNREGISTERED")
        elif case == "contract":
            replace(r, contract="4.2-RC1")
        elif case == "identity":
            replace(r, request_id=" ")
        else:
            replace(r, beam_material_id="UNREGISTERED")

    with pytest.raises(ValueError, match=r"positive|source|material|strength|contract"):
        invalid()


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("thin_washer", "WASHER_DIMENSIONS_BELOW_ASCE_8_2_DETAIL"),
        ("head", "HEAD_OR_NUT_ENVELOPE_EXCEEDS_CHECKED_WASHER_FOOTPRINT"),
        ("diameter", "BOLT_DIAMETER_OUTSIDE_ASCE_8_2_RANGE"),
        ("web_pair", "EXACT_WEB_PAIR_SYMMETRY_REQUIRED"),
        ("member_overlap", "MEMBER_HOLE_OR_WASHER_ENVELOPES_OVERLAP"),
    ],
)
def test_exact_installation_and_symmetry_invalidity(case: str, reason: str) -> None:
    r = request()
    top = r.top
    if case == "thin_washer":
        top = replace(
            top, support_hardware=replace(top.support_hardware, washer_thickness=q(".04"))
        )
    elif case == "head":
        top = replace(top, support_hardware=replace(top.support_hardware, head_across_flats=q(2)))
    elif case == "diameter":
        top = replace(top, support_fastener=replace(top.support_fastener, bolt_diameter=q(".25")))
    elif case == "web_pair":
        r = replace(
            r,
            negative_web=replace(
                r.negative_web, geometry=replace(r.negative_web.geometry, length=q(7))
            ),
        )
    else:
        top = replace(top, member_pattern=replace(top.member_pattern, gauge=q(".5")))
    p = preview_wi_frp_support_moment(replace(r, top=top, bottom=top))
    assert p.geometry.status == "INVALID_GEOMETRY"
    assert reason in p.geometry.reasons


def test_extreme_view_clip_does_not_move_engineering_member_or_bolts() -> None:
    r = request()
    shifted = replace(r, support=replace(r.support, connection_height=q(30), view_length=q(1)))
    p = preview_wi_frp_support_moment(shifted)
    assert any(part.box.component_id == "FRP_SUPPORT" for part in p.geometry.parts)
    assert not any(part.box.component_id == "FRP_SUPPORT" for part in p.geometry.display_parts)
    assert len(p.geometry.support_bolts) == 16


def test_single_web_bolt_pure_free_moment_remains_unresolved_not_zero() -> None:
    r = request(load=2)
    web = replace(
        r.positive_web, member_pattern=replace(r.positive_web.member_pattern, across=1, along=1)
    )
    result = evaluate_wi_frp_support_moment(replace(r, positive_web=web, negative_web=web))
    assert result.preview.geometry.status == "VALID"
    assert result.preview.connectors[2].web_demand is not None
    assert result.preview.connectors[2].web_demand.solution.proof is None
    assert any(
        c.scope_status == "NOT_EVALUATED_NATIVE_SLICE8_GROUP_DEMAND_UNAVAILABLE"
        for c in result.beam_local_checks
    )
    assert not result.common_web_bolts
