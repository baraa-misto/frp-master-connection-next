from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from frp_master_connection.api.web_splice_mapping import (
    serialize_web_splice_design,
    serialize_web_splice_preview,
)
from frp_master_connection.application import web_splice_orchestration as service
from frp_master_connection.calculation import (
    DoubleShearStatus,
    PhysicalQuantity,
    RationalBodyStatus,
    Unit,
    WebSpliceBodyInteractionResult,
    WebSpliceCriticalSectionAction,
    evaluate_double_shear_bolt,
    evaluate_rational_body_interaction,
)
from frp_master_connection.calculation import equations as equation_module
from frp_master_connection.calculation import web_splice_resistance as resistance_module
from frp_master_connection.domain import (
    WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    EngineeringUnitSystem,
    WebSpliceRequest,
    WebSpliceStatus,
    default_web_splice_request,
)

ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = "docs/governance/STAGE_3_6B_WEB_SPLICE_RESISTANCE_AUTHORITY_EXPANSION_DECISION.md"
SPECIFICATION_PATH = (
    "docs/engineering/"
    "STAGE_3_6B_WEB_SPLICE_RESISTANCE_AUTHORITY_EXPANSION_ENGINEERING_SPECIFICATION_RC2.md"
)
GOLDEN_PATH = (
    "backend/tests/golden/"
    "stage_3_6b_web_splice_resistance_authority_expansion_golden_benchmarks_rc2.json"
)
LEDGER_PATH = "docs/qa/STAGE_3_6B_WEB_SPLICE_RESISTANCE_AUTHORITY_EXPANSION_AUTHORITY_LEDGER_RC2.md"
GOLDEN = ROOT / GOLDEN_PATH


def _request(
    system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY,
) -> WebSpliceRequest:
    return default_web_splice_request(
        unit_system=system,
        orchestration_contract_version=WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    )


def _actions(axial: str, major: str) -> tuple[WebSpliceCriticalSectionAction, ...]:
    p = Decimal(axial)
    v = Decimal(major)
    return tuple(
        WebSpliceCriticalSectionAction(
            section,
            PhysicalQuantity.of(x, Unit.IN),
            PhysicalQuantity.of(p, Unit.KIP),
            PhysicalQuantity.of(v, Unit.KIP),
            PhysicalQuantity.of(Decimal(x) * v, Unit.KIP_IN),
        )
        for section, x in (
            ("SECTION_A_CLEAR_BOUNDARY", "-2.2185"),
            ("SECTION_JOINT", "0"),
            ("SECTION_B_CLEAR_BOUNDARY", "2.2185"),
        )
    )


def _arithmetic(axial: str, major: str) -> WebSpliceBodyInteractionResult:
    return evaluate_rational_body_interaction(
        plate_height=PhysicalQuantity.of(8, Unit.IN),
        plate_thickness=PhysicalQuantity.of("0.5", Unit.IN),
        actions=_actions(axial, major),
        symmetry_proven=True,
        tension_design_stress=PhysicalQuantity.of(12, Unit.KSI),
        compression_design_stress=PhysicalQuantity.of(10, Unit.KSI),
        shear_design_stress=PhysicalQuantity.of(5, Unit.KSI),
    )


def test_controlled_rc2_hashes_sentinels_and_g1_through_g50() -> None:
    expected = {
        DECISION_PATH: "1F4151F9FAB0359B5B455D11265A46C68CBE8C305A7A874628593989871CC716",
        SPECIFICATION_PATH: "F42A7D0F29C9DB19FB9BEACAE5C6029833E5B17F4FAC7C58E533F46E37D9F864",
        GOLDEN_PATH: "6A80263CF0A1632F009DC9952665197F4581B31018C2C98D076E36264FA94908",
        LEDGER_PATH: "C3DE28C17FB09181C49F7917DA11A89FE6633E35A59A05CB824C981BA3B7D7B4",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == digest
    sentinels = {
        DECISION_PATH: "**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION DECISION**",
        SPECIFICATION_PATH: (
            "**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION ENGINEERING SPECIFICATION**"
        ),
        LEDGER_PATH: (
            "**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION AUTHORITY LEDGER**"
        ),
    }
    for path, sentinel in sentinels.items():
        assert (ROOT / path).read_text(encoding="utf-8").strip().endswith(sentinel)
    fixture = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert fixture["successor_contract"] == "3.6B-RC2"
    assert [item["id"].split("_", 1)[0] for item in fixture["benchmarks"]] == [
        f"G{index}" for index in range(1, 51)
    ]


def test_clear_body_plan_geometry_actions_and_preview_zero_resistance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service,
        "plate_longitudinal_tension_strength",
        lambda *_args, **_kwargs: pytest.fail("Preview called Slice 4 tension."),
    )
    preview = service.preview_web_splice(_request())
    assert isinstance(preview, service.WebSpliceRC2PreviewResult)
    plan = preview.clear_body_plan
    assert plan.left_clear_boundary.to(Unit.IN).magnitude == Decimal("-2.2185")
    assert plan.right_clear_boundary.to(Unit.IN).magnitude == Decimal("2.2185")
    assert plan.clear_body_length.to(Unit.IN).magnitude == Decimal("4.437")
    assert plan.critical_section_ids == (
        "SECTION_A_CLEAR_BOUNDARY",
        "SECTION_JOINT",
        "SECTION_B_CLEAR_BOUNDARY",
    )
    assert plan.exact_linear_envelope_proven
    assert plan.physical_shear_plane_count == 2
    assert not preview.resistance_evaluated
    actions = service._body_actions(_request(), preview)
    assert [item.pair_moment.to(Unit.KIP_IN).magnitude for item in actions] == [
        Decimal("22.185"),
        Decimal(0),
        Decimal("-22.185"),
    ]


def test_clear_body_overlap_is_geometry_invalid() -> None:
    base = _request()
    crossed = replace(
        base,
        group=replace(
            base.group,
            centroid_offset=PhysicalQuantity.of("1.5", Unit.IN),
            longitudinal_gauge=PhysicalQuantity.of("3", Unit.IN),
        ),
    )
    preview = service.preview_web_splice(crossed)
    assert "WEB_SPLICE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS" in preview.geometry_invalid_reasons
    assert preview.geometry_status is WebSpliceStatus.INVALID_GEOMETRY


@pytest.mark.parametrize(
    ("axial", "major", "expected", "status"),
    [
        ("0", "-10", "0.457984375", RationalBodyStatus.PASS_RATIONAL_METHOD),
        (
            "20",
            "-10",
            "0.6316536458333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
            RationalBodyStatus.PASS_RATIONAL_METHOD,
        ),
        ("-20", "-10", "0.707984375", RationalBodyStatus.PASS_RATIONAL_METHOD),
        ("-30", "-15", "1.0619765625", RationalBodyStatus.FAIL_RATIONAL_METHOD),
    ],
)
def test_exact_rational_arithmetic_benchmarks(
    axial: str, major: str, expected: str, status: RationalBodyStatus
) -> None:
    result = _arithmetic(axial, major)
    assert result.rational_utilization == Decimal(expected)
    assert result.status is status
    assert result.plate_fraction == Decimal("0.5")
    assert result.plate_area_in2 == Decimal("4.0")
    assert str(result.plate_inertia_in4).startswith(
        "21.3333333333333333333333333333333333333333333333333333333333"
    )
    assert result.extreme_fiber_in == 4
    assert result.governing_signed_shear_stress is not None
    assert abs(result.governing_signed_shear_stress.to(Unit.KSI).magnitude) == abs(
        Decimal(major) / 2 / Decimal(4)
    )
    assert result.engineering_review_required
    assert result.qualification == "REQUIRED_2_3_2"
    assert result.disclaimer_id == "WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1"


def test_pure_mode_reductions_and_symmetry_fail_closed() -> None:
    axial = _arithmetic("10", "0")
    assert axial.rational_utilization == axial.normal_utilization
    pure_shear = evaluate_rational_body_interaction(
        plate_height=PhysicalQuantity.of(8, Unit.IN),
        plate_thickness=PhysicalQuantity.of("0.5", Unit.IN),
        actions=(
            WebSpliceCriticalSectionAction(
                "SECTION_JOINT",
                PhysicalQuantity.of(0, Unit.IN),
                PhysicalQuantity.of(0, Unit.KIP),
                PhysicalQuantity.of(-10, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP_IN),
            ),
        ),
        symmetry_proven=True,
        tension_design_stress=PhysicalQuantity.of(12, Unit.KSI),
        compression_design_stress=PhysicalQuantity.of(10, Unit.KSI),
        shear_design_stress=PhysicalQuantity.of(5, Unit.KSI),
    )
    assert pure_shear.rational_utilization == pure_shear.shear_utilization
    symmetry = evaluate_rational_body_interaction(
        plate_height=PhysicalQuantity.of(8, Unit.IN),
        plate_thickness=PhysicalQuantity.of("0.5", Unit.IN),
        actions=_actions("0", "-10"),
        symmetry_proven=False,
        tension_design_stress=PhysicalQuantity.of(12, Unit.KSI),
        compression_design_stress=PhysicalQuantity.of(10, Unit.KSI),
        shear_design_stress=PhysicalQuantity.of(5, Unit.KSI),
    )
    assert symmetry.status is RationalBodyStatus.NOT_EVALUATED
    assert symmetry.plate_fraction is None


def test_rational_input_guards_and_canonical_payload_branches() -> None:
    with pytest.raises(ValueError, match="height and thickness"):
        evaluate_rational_body_interaction(
            plate_height=PhysicalQuantity.of(0, Unit.IN),
            plate_thickness=PhysicalQuantity.of("0.5", Unit.IN),
            actions=_actions("0", "-10"),
            symmetry_proven=True,
        )
    with pytest.raises(ValueError, match="force per unit width"):
        resistance_module._design_stress(
            PhysicalQuantity.of(1, Unit.KIP),
            PhysicalQuantity.of("0.5", Unit.IN),
        )
    unavailable = evaluate_rational_body_interaction(
        plate_height=PhysicalQuantity.of(8, Unit.IN),
        plate_thickness=PhysicalQuantity.of("0.5", Unit.IN),
        actions=_actions("0", "-10"),
        symmetry_proven=True,
        tension_design_stress=PhysicalQuantity.of(12, Unit.KIP),
        compression_design_stress=PhysicalQuantity.of(0, Unit.KSI),
        shear_design_stress=PhysicalQuantity.of(5, Unit.KSI),
    )
    assert unavailable.status is RationalBodyStatus.NOT_EVALUATED
    assert resistance_module._fingerprint(
        {"items": [date(2026, 8, 30), Decimal("1.25")]}
    ) == resistance_module._fingerprint({"items": [date(2026, 8, 30), Decimal("1.25")]})


def test_slice4_is_reused_with_buckling_advisories_and_successor_provenance() -> None:
    design = service.design_check_web_splice(_request())
    assert isinstance(design, service.WebSpliceRC2DesignResult)
    body = design.plate_body_interaction
    assert body.tension_strength is not None
    assert body.compression_strength is not None
    assert body.shear_strength is not None
    assert body.tension_strength.method.value == "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION"
    assert len(body.compression_strength.methods) == 4
    assert len(body.shear_strength.methods) == 4
    assert "C7_6_3_NARROW_PLATE_VALIDATION_CAUTION" in body.slice4_advisories
    assert "C7_6_3_SHORT_PLATE_CONSERVATIVE_APPROXIMATION" in body.slice4_advisories
    assert "C7_7_3_LONG_PLATE_EQUATION_CONSERVATIVE_FOR_A_LT_B" in body.slice4_advisories
    assert len(body.slice4_result_fingerprints) == 3
    source = inspect.getsource(service)
    assert "PLATE_PI" not in source
    assert "buckling_stress_ksi" not in source


def test_analytical_double_shear_and_default_f593_source_pending() -> None:
    result = evaluate_double_shear_bolt(
        group_id="TEST_GROUP",
        bolt_id="TEST_BOLT",
        physical_path=("POSITIVE_SPLICE_PLATE", "BEAM_WEB", "NEGATIVE_SPLICE_PLATE"),
        physical_in_plane_demand=PhysicalQuantity.of(10, Unit.KIP),
        symmetry_proven=True,
        plate_fraction=Decimal("0.5"),
        diameter=PhysicalQuantity.of("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="TEST_ONLY_F3125_FNV_68_KSI",
        nominal_shear_stress=PhysicalQuantity.of(68, Unit.KSI),
    )
    assert result.physical_shear_plane_count == 2
    assert result.per_plane_demand.to(Unit.KIP).magnitude == 5
    assert result.resistance_trace is not None
    assert result.resistance_trace.area_trace.area.to(Unit.IN2).magnitude == Decimal(
        "0.19634954084936207740391521145496893026232308746094375"
    )
    assert result.per_plane_design_capacity is not None
    assert result.per_plane_design_capacity.to(Unit.KIP).magnitude == Decimal(
        "10.0138265833174659475996757842034154433784774605081312500"
    )
    assert result.two_plane_design_capacity is not None
    assert result.two_plane_design_capacity.to(Unit.KIP).magnitude == Decimal(
        "20.0276531666349318951993515684068308867569549210162625000"
    )
    assert result.utilization == Decimal(
        "0.4993096253863383082945372968549470181473243787935897839739702378069769314241893360082479609733547742"
    )
    assert result.status is DoubleShearStatus.PASS
    design = service.design_check_web_splice(_request())
    assert isinstance(design, service.WebSpliceRC2DesignResult)
    assert design.double_shear_status is DoubleShearStatus.NOT_EVALUATED
    assert all(not item.source_authorized for item in design.double_shear_results)
    assert all(item.two_plane_design_capacity is None for item in design.double_shear_results)
    assert all(
        item.source_required_reason == "SOURCE_AUTHORIZED_FNV_REQUIRED"
        for item in design.double_shear_results
    )


def test_source_authorized_metric_shear_and_invalid_input_guards() -> None:
    metric = equation_module.bolt_shear_resistance_from_nominal_stress(
        PhysicalQuantity.of("12.7", Unit.MM),
        PhysicalQuantity.of("468.84256", Unit.MPA),
    )
    assert metric.nominal_resistance.unit is Unit.N
    assert metric.design_resistance.unit is Unit.N
    with pytest.raises(ValueError, match="stress quantity"):
        equation_module.bolt_shear_resistance_from_nominal_stress(
            PhysicalQuantity.of("0.5", Unit.IN),
            PhysicalQuantity.of(1, Unit.KIP),
        )
    with pytest.raises(ValueError, match="positive"):
        equation_module.bolt_shear_resistance_from_nominal_stress(
            PhysicalQuantity.of("0.5", Unit.IN),
            PhysicalQuantity.of(0, Unit.KSI),
        )
    with pytest.raises(ValueError, match="demand must be a force"):
        evaluate_double_shear_bolt(
            group_id="TEST",
            bolt_id="TEST",
            physical_path=("SPLICE_PLATE", "WEB", "SPLICE_PLATE"),
            physical_in_plane_demand=PhysicalQuantity.of(1, Unit.KSI),
            symmetry_proven=True,
            plate_fraction=Decimal("0.5"),
            diameter=PhysicalQuantity.of("0.5", Unit.IN),
            thread_condition="EXCLUDED",
            source_authority_id="TEST",
            nominal_shear_stress=None,
        )
    with pytest.raises(ValueError, match="positive length"):
        evaluate_double_shear_bolt(
            group_id="TEST",
            bolt_id="TEST",
            physical_path=("SPLICE_PLATE", "WEB", "SPLICE_PLATE"),
            physical_in_plane_demand=PhysicalQuantity.of(1, Unit.KIP),
            symmetry_proven=True,
            plate_fraction=Decimal("0.5"),
            diameter=PhysicalQuantity.of(0, Unit.IN),
            thread_condition="EXCLUDED",
            source_authority_id="TEST",
            nominal_shear_stress=None,
        )


@pytest.mark.parametrize(
    ("path", "symmetry", "fraction", "thread", "stress"),
    [
        (("SPLICE_PLATE", "WEB"), True, "0.5", "EXCLUDED", None),
        (("SPLICE_PLATE", "WEB", "SPLICE_PLATE"), False, "0.5", "EXCLUDED", None),
        (("SPLICE_PLATE", "WEB", "SPLICE_PLATE"), True, "0.4", "EXCLUDED", None),
        (("SPLICE_PLATE", "WEB", "SPLICE_PLATE"), True, "0.5", "UNKNOWN", None),
        (
            ("SPLICE_PLATE", "WEB", "SPLICE_PLATE"),
            True,
            "0.5",
            "INCLUDED",
            PhysicalQuantity.of(1, Unit.KIP),
        ),
        (
            ("SPLICE_PLATE", "WEB", "SPLICE_PLATE"),
            True,
            "0.5",
            "INCLUDED",
            PhysicalQuantity.of(0, Unit.KSI),
        ),
    ],
)
def test_double_shear_prerequisites_fail_closed(
    path: tuple[str, ...],
    symmetry: bool,
    fraction: str,
    thread: str,
    stress: PhysicalQuantity | None,
) -> None:
    result = evaluate_double_shear_bolt(
        group_id="TEST",
        bolt_id="TEST",
        physical_path=path,
        physical_in_plane_demand=PhysicalQuantity.of(1, Unit.KIP),
        symmetry_proven=symmetry,
        plate_fraction=Decimal(fraction),
        diameter=PhysicalQuantity.of("0.5", Unit.IN),
        thread_condition=thread,
        source_authority_id="TEST",
        nominal_shear_stress=stress,
    )
    assert result.status is DoubleShearStatus.NOT_EVALUATED
    assert result.utilization is None


def test_actual_stage_2_5a_vectors_beam_independence_and_minor_boundary() -> None:
    design = service.design_check_web_splice(_request())
    assert isinstance(design, service.WebSpliceRC2DesignResult)
    by_group = {
        group.group_id.value: sorted(
            item.total_force_magnitude.canonical_magnitude
            for scenario in group.demand.scenarios
            for item in scenario.per_bolt
        )
        for group in (design.preview.beam_a_group, design.preview.beam_b_group)
    }
    evaluated = {
        group: sorted(
            item.physical_in_plane_demand.canonical_magnitude
            for item in design.double_shear_results
            if item.group_id == group
        )
        for group in by_group
    }
    assert evaluated == by_group
    assert (
        design.preview.beam_a_group.demand.result_fingerprint
        != design.preview.beam_b_group.demand.result_fingerprint
    )
    base = _request()
    minor = replace(
        base,
        transfer_force=replace(
            base.transfer_force,
            major_shear=PhysicalQuantity.of("-0.01", Unit.KIP),
            minor_shear=PhysicalQuantity.of(2, Unit.KIP),
        ),
    )
    limited = service.design_check_web_splice(minor)
    assert isinstance(limited, service.WebSpliceRC2DesignResult)
    assert limited.assembly_status is WebSpliceStatus.NOT_EVALUATED
    assert "WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE" in limited.preview.limitations
    assert limited.double_shear_results


def test_actual_per_bolt_reducer_retains_maximum_duplicate_scenario() -> None:
    preview = service.preview_web_splice(_request())
    assert isinstance(preview, service.WebSpliceRC2PreviewResult)
    demand = preview.beam_a_group.demand
    duplicated = replace(demand, scenarios=demand.scenarios * 2)
    repeated = replace(
        preview,
        beam_a_group=replace(preview.beam_a_group, demand=duplicated),
    )
    records = service._evaluate_double_shear(_request(), repeated)
    assert len(records) == len(preview.visualization.bolts)


def test_us_si_equivalence_fingerprint_scope_and_transport() -> None:
    us_preview = service.preview_web_splice(_request())
    si_preview = service.preview_web_splice(_request(EngineeringUnitSystem.SI))
    assert isinstance(us_preview, service.WebSpliceRC2PreviewResult)
    assert isinstance(si_preview, service.WebSpliceRC2PreviewResult)
    assert us_preview.connector_geometry_fingerprint == si_preview.connector_geometry_fingerprint
    assert us_preview.engineering_fingerprint == si_preview.engineering_fingerprint
    assert (
        us_preview.clear_body_plan.plan_fingerprint == si_preview.clear_body_plan.plan_fingerprint
    )
    us = service.design_check_web_splice(_request())
    si = service.design_check_web_splice(_request(EngineeringUnitSystem.SI))
    assert isinstance(us, service.WebSpliceRC2DesignResult)
    assert isinstance(si, service.WebSpliceRC2DesignResult)
    assert (
        us.plate_body_interaction.result_fingerprint == si.plate_body_interaction.result_fingerprint
    )
    assert [item.result_fingerprint for item in us.double_shear_results] == [
        item.result_fingerprint for item in si.double_shear_results
    ]
    preview_dto = serialize_web_splice_preview(us_preview)
    design_dto = serialize_web_splice_design(us)
    assert preview_dto.orchestration_contract_version == "3.6B-RC2"
    assert preview_dto.preview_schema_version == "0.2.0-draft"
    design_result = cast(dict[str, object], design_dto.result)
    body_result = cast(dict[str, object], design_result["plate_body_interaction"])
    assert body_result["engineering_review_required"] is True
    assert design_result["disclaimer_id"] == ("WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1")


def test_failure_and_pass_with_review_aggregation(monkeypatch: pytest.MonkeyPatch) -> None:
    base = _request()
    body_failure = _arithmetic("-30", "-15")
    monkeypatch.setattr(service, "_evaluate_body_interaction", lambda *_args: body_failure)
    failed = service.design_check_web_splice(base)
    assert failed.assembly_status is WebSpliceStatus.FAIL
    passing_body = _arithmetic("0", "-10")
    passing_bolt = evaluate_double_shear_bolt(
        group_id="TEST",
        bolt_id="TEST",
        physical_path=("POSITIVE_SPLICE_PLATE", "BEAM_WEB", "NEGATIVE_SPLICE_PLATE"),
        physical_in_plane_demand=PhysicalQuantity.of(1, Unit.KIP),
        symmetry_proven=True,
        plate_fraction=Decimal("0.5"),
        diameter=PhysicalQuantity.of("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="TEST",
        nominal_shear_stress=PhysicalQuantity.of(68, Unit.KSI),
    )
    monkeypatch.setattr(service, "_evaluate_body_interaction", lambda *_args: passing_body)
    monkeypatch.setattr(service, "_evaluate_double_shear", lambda *_args: (passing_bolt,))
    monkeypatch.setattr(
        service,
        "_evaluate_supported_local_resistance",
        lambda *_args: (("CHECK",), (), (), ("f" * 64,)),
    )
    passed = service.design_check_web_splice(base)
    assert passed.assembly_status is WebSpliceStatus.PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED
    assert passed.required_check_status == "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED"
    assert not passed.ordinary_pass_allowed


def test_historical_3_6a_and_slice4_sources_remain_separate() -> None:
    historical = default_web_splice_request()
    preview = service.preview_web_splice(historical)
    design = service.design_check_web_splice(historical)
    assert type(preview) is service.WebSplicePreviewResult
    assert type(design) is service.WebSpliceDesignResult
    assert preview.orchestration_contract_version == "3.6A-RC1"
    assert preview.preview_schema_version == "0.1.0-draft"
    assert preview.limitations == service.WEB_SPLICE_API_LIMITATIONS
    assert not hasattr(preview, "clear_body_plan")
    assert not hasattr(design, "plate_body_interaction")
    production = ROOT / "backend/src"
    marker = "stage_3_6b_web_splice_resistance_authority_expansion_golden_benchmarks_rc2"
    assert not any(marker in path.read_text(encoding="utf-8") for path in production.rglob("*.py"))
