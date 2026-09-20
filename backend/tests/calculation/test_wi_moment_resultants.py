from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
from typing import cast

import pytest

import frp_master_connection.calculation.wi_moment_resultants as module
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus, SourceClassification
from frp_master_connection.calculation.wi_moment_resultants import (
    WI_MOMENT_ASCE_SOURCE_SHA256,
    WI_MOMENT_CALCULATION_CONTRACT_VERSION,
    WI_MOMENT_DECISION_SHA256,
    WI_MOMENT_DISCLAIMER_ID,
    WI_MOMENT_ERRATUM_SOURCE_SHA256,
    WI_MOMENT_GOLDEN_SHA256,
    WI_MOMENT_LEDGER_SHA256,
    WI_MOMENT_METHOD_ID,
    WI_MOMENT_ORDER_SHA256,
    WI_MOMENT_SOURCE_PROVENANCE,
    WI_MOMENT_SPECIFICATION_SHA256,
    BeamQuantityVector,
    WIMomentActionInput,
    WIMomentCalculationInput,
    WIMomentFingerprintEnvelope,
    WIMomentInputRejected,
    WIMomentInputStatus,
    WIMomentMethod,
    WIMomentRegionForceState,
    WIMomentRegionId,
    WIMomentRejectionReason,
    WIMomentSectionInput,
    calculate_wi_moment_component_resultants,
    canonical_wi_moment_input_json,
    wi_moment_input_fingerprint,
)

_BACKEND = Path(__file__).resolve().parents[2]
_ROOT = _BACKEND.parent
_GOLDEN_PATH = (
    _BACKEND
    / "tests"
    / "golden"
    / "calculation_slice_5_wi_moment_component_resultants_golden_benchmarks_rc1.json"
)
_GOLDEN = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
_BENCHMARKS = {item["id"]: item for item in _GOLDEN["benchmarks"]}
_GIT = cast(str, shutil.which("git"))


def _q(value: str | int | Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _geometry() -> WIMomentSectionInput:
    return WIMomentSectionInput(
        _q("10", Unit.IN),
        _q("8", Unit.IN),
        _q("0.5", Unit.IN),
        _q("0.5", Unit.IN),
    )


def _actions(
    axial: str = "20",
    shear: str = "-10",
    moment: str = "100",
    *,
    minor_shear: str = "0",
    minor_moment: str = "0",
    torsion: str = "0",
) -> WIMomentActionInput:
    return WIMomentActionInput(
        _q(axial, Unit.KIP),
        _q(shear, Unit.KIP),
        _q(moment, Unit.KIP_IN),
        _q(minor_shear, Unit.KIP),
        _q(minor_moment, Unit.KIP_IN),
        _q(torsion, Unit.KIP_IN),
    )


def _calculate(
    axial: str = "20", shear: str = "-10", moment: str = "100"
) -> module.WIMomentComponentResultants:
    return calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(_geometry(), _actions(axial, shear, moment))
    )


def _expected(benchmark_id: str, key: str) -> Decimal:
    return Decimal(_BENCHMARKS[benchmark_id]["expected"][key])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_controlled_artifacts_are_byte_exact_and_sentinels_are_present() -> None:
    controlled = (
        (
            _ROOT
            / "docs"
            / "governance"
            / "CALCULATION_SLICE_5_WI_MOMENT_COMPONENT_RESULTANTS_DECISION.md",
            WI_MOMENT_DECISION_SHA256,
            "END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS DECISION",
        ),
        (
            _ROOT
            / "docs"
            / "engineering"
            / "CALCULATION_SLICE_5_WI_MOMENT_COMPONENT_RESULTANTS_ENGINEERING_SPECIFICATION_RC1.md",
            WI_MOMENT_SPECIFICATION_SHA256,
            (
                "END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS "
                "ENGINEERING SPECIFICATION RC1"
            ),
        ),
        (_GOLDEN_PATH, WI_MOMENT_GOLDEN_SHA256, '"G52_NO_FRONTEND_PRODUCTION_CHANGE"'),
        (
            _ROOT
            / "docs"
            / "qa"
            / "CALCULATION_SLICE_5_WI_MOMENT_COMPONENT_RESULTANTS_AUTHORITY_LEDGER_RC1.md",
            WI_MOMENT_LEDGER_SHA256,
            "END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS AUTHORITY LEDGER RC1",
        ),
    )
    for path, expected_hash, sentinel in controlled:
        assert _sha256(path) == expected_hash
        assert sentinel in path.read_text(encoding="utf-8")


def test_golden_identity_is_exact_g1_through_g52() -> None:
    ids = tuple(item["id"] for item in _GOLDEN["benchmarks"])
    assert _GOLDEN["contract"] == WI_MOMENT_CALCULATION_CONTRACT_VERSION
    assert _GOLDEN["method"] == WI_MOMENT_METHOD_ID
    assert len(ids) == len(set(ids)) == 52
    assert ids[0] == "G1_WEB_HEIGHT"
    assert ids[-1] == "G52_NO_FRONTEND_PRODUCTION_CHANGE"


def test_source_and_erratum_record_is_complete_and_nonprescriptive() -> None:
    source = WI_MOMENT_SOURCE_PROVENANCE
    assert {item.section for item in source.code_sources} == {
        "2.3.2",
        "2.9",
        "8.1.3",
        "8.3.4.2",
        "C2.9",
        "C8.1.3",
        "C8.3.4",
    }
    assert (
        source.rational_method_classification is SourceClassification.ENGINEER_APPROVED_DEVELOPMENT
    )
    assert source.qualification_statuses == (
        QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
        QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    )
    assert source.erratum_changes_targeted_provisions is False
    assert source.direct_asce_equation_claimed is False
    assert dict(source.authoritative_source_hashes) == {
        "ASCE_SEI_74_23": WI_MOMENT_ASCE_SOURCE_SHA256,
        "ERRATUM_1_EFFECTIVE_2026_01_13": WI_MOMENT_ERRATUM_SOURCE_SHA256,
    }
    assert dict(source.controlled_artifact_hashes)["codex_order"] == WI_MOMENT_ORDER_SHA256


def test_g1_through_g5_exact_section_geometry_and_properties() -> None:
    properties = _calculate().section_properties
    assert properties.web_height.magnitude == _expected("G1_WEB_HEIGHT", "h_w_in")
    assert properties.flange_area.magnitude == _expected("G2_REGION_AREAS", "A_top_in2")
    assert properties.web_area.magnitude == _expected("G2_REGION_AREAS", "A_web_in2")
    assert properties.total_area.magnitude == _expected("G2_REGION_AREAS", "A_total_in2")
    assert properties.top_centroid_v.magnitude == _expected("G3_REGION_CENTROIDS", "y_top_in")
    assert properties.web_centroid_v.magnitude == _expected("G3_REGION_CENTROIDS", "y_web_in")
    assert properties.bottom_centroid_v.magnitude == _expected("G3_REGION_CENTROIDS", "y_bottom_in")
    assert properties.flange_centroidal_inertia.magnitude == _expected(
        "G4_REGION_CENTROIDAL_INERTIAS", "I_top_c_in4"
    )
    assert properties.web_centroidal_inertia.magnitude == _expected(
        "G4_REGION_CENTROIDAL_INERTIAS", "I_web_c_in4"
    )
    assert properties.total_major_inertia.magnitude == _expected(
        "G5_TOTAL_MAJOR_AXIS_INERTIA", "I_T_in4"
    )
    assert properties.total_major_inertia.dimension is Dimension.SECOND_MOMENT_OF_AREA
    assert (
        properties.total_major_inertia.to(Unit.MM4).to(Unit.IN4) == properties.total_major_inertia
    )


def test_existing_wi_geometry_authority_is_reused() -> None:
    dimensions = module._validated_profile_dimensions(_geometry())
    assert dimensions.depth == Decimal("10")
    assert dimensions.flange_width == Decimal("8")
    assert dimensions.web_thickness == Decimal("0.5")
    assert dimensions.flange_thickness == Decimal("0.5")
    assert dimensions.member_length == dimensions.depth


def test_g6_and_g7_pure_axial_area_distribution() -> None:
    result = _calculate(moment="0", shear="0")
    assert result.component(WIMomentRegionId.TOP_FLANGE).wrench.force_lvt.l.magnitude == _expected(
        "G6_PURE_AXIAL_AREA_DISTRIBUTION", "N_top_kip"
    )
    assert result.component(WIMomentRegionId.WEB).wrench.force_lvt.l.magnitude == _expected(
        "G6_PURE_AXIAL_AREA_DISTRIBUTION", "N_web_kip"
    )
    assert result.component(
        WIMomentRegionId.BOTTOM_FLANGE
    ).wrench.force_lvt.l.magnitude == _expected("G6_PURE_AXIAL_AREA_DISTRIBUTION", "N_bottom_kip")
    assert all(item.wrench.moment_lvt.t.magnitude == 0 for item in result.components)


def test_g8_through_g15_pure_moment_complete_region_wrenches_and_equilibrium() -> None:
    result = _calculate(axial="0", shear="0")
    top, web, bottom = result.components
    assert top.wrench.force_lvt.l.magnitude == _expected("G8_PURE_MOMENT_TOP_FORCE", "N_top_kip")
    assert web.wrench.force_lvt.l.magnitude == _expected(
        "G9_PURE_MOMENT_WEB_FORCE_ZERO", "N_web_kip"
    )
    assert bottom.wrench.force_lvt.l.magnitude == _expected(
        "G10_PURE_MOMENT_BOTTOM_FORCE", "N_bottom_kip"
    )
    assert top.wrench.moment_lvt.t.magnitude == _expected(
        "G11_PURE_MOMENT_TOP_LOCAL_MOMENT", "m_top_kip_in"
    )
    assert web.wrench.moment_lvt.t.magnitude == _expected(
        "G12_PURE_MOMENT_WEB_LOCAL_MOMENT", "m_web_kip_in"
    )
    assert bottom.wrench.moment_lvt.t.magnitude == _expected(
        "G13_PURE_MOMENT_BOTTOM_LOCAL_MOMENT", "m_bottom_kip_in"
    )
    assert result.equilibrium.summed_axial_force.magnitude == _expected(
        "G14_PURE_MOMENT_AXIAL_EQUILIBRIUM", "sum_N_kip"
    )
    assert result.equilibrium.summed_major_moment.magnitude == _expected(
        "G15_PURE_MOMENT_MOMENT_EQUILIBRIUM", "sum_M_T_kip_in"
    )
    assert result.equilibrium.exact_axial_balance_numerator == 0
    assert result.equilibrium.exact_moment_balance_numerator == 0


def test_g16_through_g25_default_component_wrenches_and_exact_equilibrium() -> None:
    result = _calculate()
    top, web, bottom = result.components
    assert top.wrench.force_lvt.l.magnitude == _expected("G16_DEFAULT_TOP_FORCE", "N_top_kip")
    assert web.wrench.force_lvt.l.magnitude == _expected("G17_DEFAULT_WEB_FORCE", "N_web_kip")
    assert bottom.wrench.force_lvt.l.magnitude == _expected(
        "G18_DEFAULT_BOTTOM_FORCE", "N_bottom_kip"
    )
    assert top.wrench.moment_lvt.t.magnitude == _expected(
        "G19_DEFAULT_TOP_LOCAL_MOMENT", "m_top_kip_in"
    )
    assert web.wrench.moment_lvt.t.magnitude == _expected(
        "G20_DEFAULT_WEB_LOCAL_MOMENT", "m_web_kip_in"
    )
    assert bottom.wrench.moment_lvt.t.magnitude == _expected(
        "G21_DEFAULT_BOTTOM_LOCAL_MOMENT", "m_bottom_kip_in"
    )
    assert [item.wrench.force_lvt.v.magnitude for item in result.components] == [
        _expected("G22_DEFAULT_MAJOR_SHEAR_ALLOCATION", "V_top_kip"),
        _expected("G22_DEFAULT_MAJOR_SHEAR_ALLOCATION", "V_web_kip"),
        _expected("G22_DEFAULT_MAJOR_SHEAR_ALLOCATION", "V_bottom_kip"),
    ]
    trace = result.equilibrium
    assert trace.summed_axial_force.magnitude == _expected(
        "G23_DEFAULT_AXIAL_EQUILIBRIUM", "sum_N_kip"
    )
    assert trace.summed_major_shear.magnitude == _expected(
        "G24_DEFAULT_SHEAR_EQUILIBRIUM", "sum_V_kip"
    )
    assert trace.summed_major_moment.magnitude == _expected(
        "G25_DEFAULT_MOMENT_EQUILIBRIUM", "sum_M_T_kip_in"
    )
    assert trace.axial_equilibrium_exact
    assert trace.shear_equilibrium_exact
    assert trace.moment_equilibrium_exact
    assert trace.unsupported_components_zero
    assert trace.exact_axial_balance_numerator == trace.exact_shear_residual == 0
    assert trace.exact_moment_balance_numerator == 0


def test_component_references_and_global_moment_contributions_are_complete() -> None:
    result = _calculate()
    assert [item.wrench.reference_lvt.v.magnitude for item in result.components] == [
        Decimal("4.75"),
        Decimal(0),
        Decimal("-4.75"),
    ]
    assert all(item.wrench.reference_lvt.l.magnitude == 0 for item in result.components)
    assert all(item.wrench.reference_lvt.t.magnitude == 0 for item in result.components)
    assert all(item.wrench.force_lvt.t.magnitude == 0 for item in result.components)
    assert all(item.wrench.moment_lvt.l.magnitude == 0 for item in result.components)
    assert all(item.wrench.moment_lvt.v.magnitude == 0 for item in result.components)
    with localcontext() as context:
        context.prec = 80
        summed = sum((item.global_major_moment.magnitude for item in result.components), Decimal(0))
    assert summed == result.equilibrium.summed_major_moment.magnitude
    assert all(item.wrench.provenance.endswith("REGION_CENTROID") for item in result.components)


def test_g26_through_g31_couple_diagnostics_preserve_residual_moment() -> None:
    diagnostics = _calculate().couple_diagnostics
    assert diagnostics.flange_lever_arm.magnitude == _expected("G26_FLANGE_LEVER_ARM", "z_f_in")
    assert diagnostics.exact_flange_couple_force.magnitude == _expected(
        "G27_EXACT_FLANGE_COUPLE_FORCE", "C_f_kip"
    )
    assert diagnostics.exact_flange_couple_moment.magnitude == _expected(
        "G28_EXACT_FLANGE_COUPLE_MOMENT", "M_couple_kip_in"
    )
    assert diagnostics.full_moment_over_z_reference_force.magnitude == _expected(
        "G29_FULL_MOMENT_M_OVER_Z_REFERENCE", "C_M_over_z_kip"
    )
    assert diagnostics.full_moment_over_z_is_controlling is False
    assert diagnostics.residual_moment.magnitude == _expected(
        "G30_RESIDUAL_MOMENT", "M_residual_kip_in"
    )
    assert diagnostics.local_and_web_moment_sum.magnitude == _expected(
        "G31_RESIDUAL_IDENTITY", "local_and_web_sum_kip_in"
    )
    assert diagnostics.residual_identity_exact is True


def test_g32_through_g36_stress_extrema_states_and_zero_crossing() -> None:
    result = _calculate()
    top, web, bottom = result.components
    assert top.stress_extrema.first_stress_l.magnitude == _expected(
        "G32_TOP_STRESS_EXTREMA", "inner_ksi"
    )
    assert top.stress_extrema.second_stress_l.magnitude == _expected(
        "G32_TOP_STRESS_EXTREMA", "outer_ksi"
    )
    assert web.stress_extrema.first_stress_l.magnitude == _expected(
        "G33_WEB_STRESS_EXTREMA", "bottom_ksi"
    )
    assert web.stress_extrema.second_stress_l.magnitude == _expected(
        "G33_WEB_STRESS_EXTREMA", "top_ksi"
    )
    assert bottom.stress_extrema.first_stress_l.magnitude == _expected(
        "G34_BOTTOM_STRESS_EXTREMA", "outer_ksi"
    )
    assert bottom.stress_extrema.second_stress_l.magnitude == _expected(
        "G34_BOTTOM_STRESS_EXTREMA", "inner_ksi"
    )
    assert [item.force_state.value for item in result.components] == [
        _BENCHMARKS["G35_REGION_FORCE_STATE"]["expected"][key] for key in ("top", "web", "bottom")
    ]
    assert [item.stress_extrema.crosses_zero for item in result.components] == [
        _BENCHMARKS["G36_REGION_STRESS_ZERO_CROSSING"]["expected"][key]
        for key in ("top", "web", "bottom")
    ]
    assert top.stress_extrema.first_boundary_id == "INNER_FACE"
    assert web.stress_extrema.first_boundary_id == "BOTTOM_WEB_EDGE"
    assert bottom.stress_extrema.second_boundary_id == "INNER_FACE"


def test_g37_all_zero_action_is_exact() -> None:
    result = _calculate(axial="0", shear="0", moment="0")
    assert all(
        component.wrench.force_lvt.l.magnitude
        == component.wrench.force_lvt.v.magnitude
        == component.wrench.force_lvt.t.magnitude
        == component.wrench.moment_lvt.l.magnitude
        == component.wrench.moment_lvt.v.magnitude
        == component.wrench.moment_lvt.t.magnitude
        == 0
        for component in result.components
    )
    assert all(
        component.force_state is WIMomentRegionForceState.ZERO_FORCE
        for component in result.components
    )
    assert all(component.stress_extrema.crosses_zero for component in result.components)
    assert result.couple_diagnostics.exact_flange_couple_force.magnitude == 0
    assert result.couple_diagnostics.residual_identity_exact


def test_g38_axial_sign_reversal_preserves_bending_terms() -> None:
    positive = _calculate(axial="20")
    negative = _calculate(axial="-20")
    pure_moment = _calculate(axial="0")
    for positive_region, negative_region, bending_region in zip(
        positive.components, negative.components, pure_moment.components, strict=True
    ):
        assert (
            positive_region.wrench.force_lvt.l.magnitude
            + negative_region.wrench.force_lvt.l.magnitude
            == Decimal(2) * bending_region.wrench.force_lvt.l.magnitude
        )
        assert positive_region.wrench.moment_lvt == negative_region.wrench.moment_lvt


def test_g39_moment_sign_reversal_reverses_bending_and_stress_gradient() -> None:
    positive = _calculate(moment="100")
    negative = _calculate(moment="-100")
    axial = _calculate(moment="0")
    for plus, minus, uniform in zip(
        positive.components, negative.components, axial.components, strict=True
    ):
        assert plus.wrench.force_lvt.l.magnitude + minus.wrench.force_lvt.l.magnitude == (
            Decimal(2) * uniform.wrench.force_lvt.l.magnitude
        )
        assert plus.wrench.moment_lvt.t.magnitude == (
            minus.wrench.moment_lvt.t.magnitude.copy_negate()
        )
    assert positive.component(
        WIMomentRegionId.TOP_FLANGE
    ).stress_extrema.second_stress_l.magnitude > (
        positive.component(WIMomentRegionId.TOP_FLANGE).stress_extrema.first_stress_l.magnitude
    )
    assert negative.component(
        WIMomentRegionId.TOP_FLANGE
    ).stress_extrema.second_stress_l.magnitude < (
        negative.component(WIMomentRegionId.TOP_FLANGE).stress_extrema.first_stress_l.magnitude
    )


def test_g40_shear_sign_reversal_changes_only_web_shear() -> None:
    positive = _calculate(shear="10")
    negative = _calculate(shear="-10")
    assert [item.wrench.force_lvt.v.magnitude for item in positive.components] == [0, 10, 0]
    assert [item.wrench.force_lvt.v.magnitude for item in negative.components] == [0, -10, 0]
    assert [item.wrench.force_lvt.l for item in positive.components] == [
        item.wrench.force_lvt.l for item in negative.components
    ]


@pytest.mark.parametrize(
    ("action_overrides", "reason"),
    [
        ({"minor_shear": "1"}, WIMomentRejectionReason.MINOR_SHEAR_NOT_SUPPORTED),
        (
            {"minor_moment": "1"},
            WIMomentRejectionReason.MINOR_AXIS_MOMENT_NOT_SUPPORTED,
        ),
        ({"torsion": "1"}, WIMomentRejectionReason.TORSION_NOT_SUPPORTED),
    ],
)
def test_g41_through_g43_unsupported_actions_fail_closed(
    action_overrides: dict[str, str], reason: WIMomentRejectionReason
) -> None:
    with pytest.raises(WIMomentInputRejected) as caught:
        calculate_wi_moment_component_resultants(
            WIMomentCalculationInput(_geometry(), _actions(**action_overrides))
        )
    assert caught.value.status is WIMomentInputStatus.REJECTED
    assert caught.value.reason is reason
    assert str(caught.value) == reason.value


@pytest.mark.parametrize(
    ("geometry", "reason"),
    [
        (
            WIMomentSectionInput(
                _q("1", Unit.IN), _q("8", Unit.IN), _q("0.5", Unit.IN), _q("0.5", Unit.IN)
            ),
            WIMomentRejectionReason.POSITIVE_WEB_HEIGHT_REQUIRED,
        ),
        (
            WIMomentSectionInput(
                _q("10", Unit.IN),
                _q("0.5", Unit.IN),
                _q("0.5", Unit.IN),
                _q("0.5", Unit.IN),
            ),
            WIMomentRejectionReason.FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS,
        ),
        (
            WIMomentSectionInput(
                _q("10", Unit.IN), _q("8", Unit.IN), _q("0", Unit.IN), _q("0.5", Unit.IN)
            ),
            WIMomentRejectionReason.POSITIVE_DIMENSIONS_REQUIRED,
        ),
    ],
)
def test_g44_and_g45_invalid_geometry_fails_closed(
    geometry: WIMomentSectionInput, reason: WIMomentRejectionReason
) -> None:
    with pytest.raises(WIMomentInputRejected) as caught:
        calculate_wi_moment_component_resultants(WIMomentCalculationInput(geometry, _actions()))
    assert caught.value.reason is reason


def test_g46_us_si_equivalence_is_exact() -> None:
    us_input = WIMomentCalculationInput(_geometry(), _actions())
    si_geometry = WIMomentSectionInput(
        *(getattr(us_input.geometry, name).to(Unit.MM) for name in ("d", "b_f", "t_w", "t_f"))
    )
    si_actions = WIMomentActionInput(
        us_input.actions.axial_force_l.to(Unit.KN),
        us_input.actions.major_shear_v.to(Unit.KN),
        us_input.actions.major_moment_t.to(Unit.KN_MM),
        us_input.actions.minor_shear_t.to(Unit.KN),
        us_input.actions.minor_moment_v.to(Unit.KN_MM),
        us_input.actions.torsion_l.to(Unit.KN_MM),
    )
    si_input = WIMomentCalculationInput(si_geometry, si_actions)
    us = calculate_wi_moment_component_resultants(us_input)
    si = calculate_wi_moment_component_resultants(si_input)
    assert us.section_properties == si.section_properties
    assert us.components == si.components
    assert us.couple_diagnostics == si.couple_diagnostics
    assert us.equilibrium == si.equilibrium
    assert us.input_fingerprint == si.input_fingerprint
    assert us.result_fingerprint == si.result_fingerprint


def test_g47_fingerprints_are_deterministic_and_presentation_excluded() -> None:
    calculation_input = WIMomentCalculationInput(_geometry(), _actions())
    baseline = wi_moment_input_fingerprint(calculation_input)
    envelope = WIMomentFingerprintEnvelope(
        calculation_input,
        display_unit_profile="US",
        display_rounding="2 decimals",
        camera_state={"orbit": "presentation"},
        ui_selection="top flange",
        request_timestamp="not engineering identity",
    )
    assert wi_moment_input_fingerprint(envelope) == baseline
    assert canonical_wi_moment_input_json(envelope) == canonical_wi_moment_input_json(
        calculation_input
    )
    assert _calculate().result_fingerprint == _calculate().result_fingerprint
    changed = calculate_wi_moment_component_resultants(
        WIMomentCalculationInput(_geometry(), _actions(moment="101"))
    )
    assert changed.input_fingerprint != baseline
    assert changed.result_fingerprint != _calculate().result_fingerprint


def test_g48_review_and_disclaimer_are_backend_owned() -> None:
    result = _calculate()
    assert result.rational_method_engineering_review_required is True
    assert result.disclaimer_id == WI_MOMENT_DISCLAIMER_ID
    assert "not a direct ASCE/SEI 74-23 connection-detail equation" in result.disclaimer
    production = Path(module.__file__).read_text(encoding="utf-8")
    assert WI_MOMENT_DISCLAIMER_ID in production


def test_g49_through_g51_freeze_audit_modules_and_available_tags_remain_present() -> None:
    for stage in ("3_2", "3_3", "3_4", "3_5", "3_6", "3_7"):
        assert (
            _BACKEND / "tests" / "calculation" / f"test_stage_{stage}_freeze_manifest.py"
        ).is_file()
    tags = set(
        subprocess.run(  # noqa: S603 - executable is resolved from the test host
            [_GIT, "tag", "--list"],
            cwd=_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    required_tags = {
        "stage-2.3-interface-geometry-freeze",
        "stage-3.7-column-base-shear-family-freeze",
    }
    assert not tags or required_tags <= tags


def test_g52_slice5_frontend_identity_is_successor_safe_and_production_never_reads_golden() -> None:
    manifest = json.loads((_ROOT / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["calculation_slice_5_frontend_production_change_count"] == 0
    accepted_commit = manifest["calculation_slice_5_accepted_commit"]
    available = subprocess.run(  # noqa: S603 - executable is resolved from the test host
        [_GIT, "cat-file", "-e", f"{accepted_commit}^{{commit}}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if available.returncode == 0:
        accepted_tree = subprocess.run(  # noqa: S603 - executable is resolved from test host
            [_GIT, "rev-parse", f"{accepted_commit}:frontend/src"],
            cwd=_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert accepted_tree == manifest["stage_3_7_freeze_frontend_src_tree"]
    production = Path(module.__file__).read_text(encoding="utf-8")
    assert "tests/golden" not in production
    assert "calculation_slice_5_wi_moment_component_resultants_golden" not in production


def test_public_input_and_vector_validation_is_strict() -> None:
    with pytest.raises(TypeError, match=r"WIMomentSectionInput\.d"):
        WIMomentSectionInput("10", _q(8, Unit.IN), _q(1, Unit.IN), _q(1, Unit.IN))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be a length"):
        WIMomentSectionInput(_q(10, Unit.KIP), _q(8, Unit.IN), _q(1, Unit.IN), _q(1, Unit.IN))
    with pytest.raises(TypeError, match="axial_force_l"):
        replace(_actions(), axial_force_l="20")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="axial_force_l must be a force"):
        replace(_actions(), axial_force_l=_q(20, Unit.IN))
    with pytest.raises(TypeError, match="major_moment_t"):
        replace(_actions(), major_moment_t="100")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="major_moment_t must be a moment"):
        replace(_actions(), major_moment_t=_q(100, Unit.KIP))
    with pytest.raises(TypeError, match="BeamQuantityVector components"):
        BeamQuantityVector("0", _q(0, Unit.IN), _q(0, Unit.IN))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="share one dimension"):
        BeamQuantityVector(_q(0, Unit.IN), _q(0, Unit.KIP), _q(0, Unit.IN))


def test_calculation_input_contract_and_type_boundaries_fail_closed() -> None:
    with pytest.raises(TypeError, match="geometry"):
        WIMomentCalculationInput("geometry", _actions())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="actions"):
        WIMomentCalculationInput(_geometry(), "actions")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="contract_version"):
        WIMomentCalculationInput(_geometry(), _actions(), 5)  # type: ignore[arg-type]
    with pytest.raises(WIMomentInputRejected) as caught:
        WIMomentCalculationInput(_geometry(), _actions(), "CS5-RC2")
    assert caught.value.reason is WIMomentRejectionReason.UNSUPPORTED_CONTRACT_VERSION
    with pytest.raises(TypeError, match="method"):
        WIMomentCalculationInput(_geometry(), _actions(), method=WI_MOMENT_METHOD_ID)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="calculation_input"):
        calculate_wi_moment_component_resultants("input")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="region_id"):
        _calculate().component("WEB")  # type: ignore[arg-type]
    assert WIMomentMethod.RATIONAL_ELASTIC_REGION_RESULTANTS.value == WI_MOMENT_METHOD_ID


def test_fingerprint_canonicalizer_rejects_ambiguous_values() -> None:
    assert module._canonicalize(5) == "5"
    assert module._canonicalize(WIMomentRegionId.WEB) == "WEB"
    with pytest.raises(TypeError, match="calculation input or envelope"):
        canonical_wi_moment_input_json("input")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Raw floating-point"):
        module._canonicalize(1.0)
    with pytest.raises(TypeError, match="mapping keys"):
        module._canonicalize({1: "not text"})
    with pytest.raises(TypeError, match="Unsupported Slice 5"):
        module._canonicalize(object())


def test_no_connection_strength_or_stage_4_1a_product_symbols_are_returned() -> None:
    result = _calculate()
    names = set(result.__dataclass_fields__)
    assert names.isdisjoint(
        {
            "status",
            "pass_fail",
            "capacity",
            "utilization",
            "bolt_distribution",
            "prying",
            "connection_stiffness",
            "moment_rotation",
        }
    )
