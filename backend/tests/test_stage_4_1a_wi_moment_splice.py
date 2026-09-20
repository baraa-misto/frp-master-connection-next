from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import httpx
import pytest

from frp_master_connection.api import routes
from frp_master_connection.api.app import create_app
from frp_master_connection.api.clip_angle_mapping import _serialize
from frp_master_connection.api.wi_moment_splice_mapping import (
    map_wi_moment_splice_request,
    serialize_wi_moment_splice_design,
    serialize_wi_moment_splice_preview,
)
from frp_master_connection.api.wi_moment_splice_schemas import WIMomentSpliceRequestDTO
from frp_master_connection.application import wi_moment_splice_orchestration as service
from frp_master_connection.calculation import (
    ASCE_74_23_ERRATUM,
    PLATE_PI,
    AsymmetricBoltStatus,
    FlangeBodyStatus,
    FlangePlaneDemand,
    PhysicalQuantity,
    Unit,
    WIMomentComponentResult,
    decompose_flange_wrench,
    evaluate_asymmetric_two_plane_bolt,
    evaluate_flange_plate_body,
)
from frp_master_connection.calculation import wi_moment_splice_resistance as resistance
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    WIMomentSpliceActions,
    WIMomentSpliceFastener,
    WIMomentSpliceRequest,
    WIMomentSpliceStatus,
    default_wi_moment_splice_request,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = (
    "backend/tests/golden/stage_4_1a_wi_major_axis_moment_splice_golden_benchmarks_rc1.json"
)
CONTROLLED = {
    "docs/governance/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_DECISION.md": (
        "D60A4F95340E70632E8EB277E9F7353151A2C35D80BA66BF2F71D98A6A06FD05",
        "**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE DECISION**",
    ),
    "docs/engineering/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_ENGINEERING_SPECIFICATION_RC1.md": (
        "2C4FDBB51468C65EBA35D8E887E404C43D5DC620EAC88DDC613232E0CDE7F218",
        "**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE ENGINEERING SPECIFICATION RC1**",
    ),
    GOLDEN_PATH: (
        "386A6C7B3BEFCBABA8006C7421A30C3AF890E803CAF71F3A191F7CD33616D96C",
        None,
    ),
    "docs/qa/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_AUTHORITY_LEDGER_RC1.md": (
        "4DA812A1DFC2825F82688A9F837BACD640DBB7819248C4DD4799D8751E6B1DDD",
        "**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE AUTHORITY LEDGER RC1**",
    ),
}


def q(value: str | int, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _quantity(value: PhysicalQuantity) -> dict[str, str]:
    return {"value": str(value.magnitude), "unit": value.unit.value}


def _dto_payload(
    request: WIMomentSpliceRequest | None = None,
) -> dict[str, object]:
    value = default_wi_moment_splice_request() if request is None else request
    return {
        "orchestration_contract_version": value.orchestration_contract_version,
        "request_id": value.request_id,
        "unit_system": value.unit_system.value,
        "source_length_unit": value.source_length_unit.value,
        "profile_family": value.profile_family,
        "beams_locked_identical": value.beams_locked_identical,
        "beam": {
            "profile_family": value.beam.profile_family,
            "depth": _quantity(value.beam.depth),
            "flange_width": _quantity(value.beam.flange_width),
            "web_thickness": _quantity(value.beam.web_thickness),
            "flange_thickness": _quantity(value.beam.flange_thickness),
            "display_length_each_side": _quantity(value.beam.display_length_each_side),
        },
        "beam_end_gap": _quantity(value.beam_end_gap),
        "web_splice_plate": {
            "length": _quantity(value.web_splice_plate.length),
            "height": _quantity(value.web_splice_plate.height),
            "thickness": _quantity(value.web_splice_plate.thickness),
            "count": value.web_splice_plate.count,
            "locked_identical": value.web_splice_plate.locked_identical,
        },
        "web_bolt_group": {
            "rows": value.web_bolt_group.rows,
            "bolts_per_row": value.web_bolt_group.bolts_per_row,
            "vertical_pitch": _quantity(value.web_bolt_group.vertical_pitch),
            "longitudinal_gauge": _quantity(value.web_bolt_group.longitudinal_gauge),
            "centroid_offset": _quantity(value.web_bolt_group.centroid_offset),
            "locked_identical_mirror": value.web_bolt_group.locked_identical_mirror,
        },
        "web_fastener": {
            "bolt_diameter": _quantity(value.web_fastener.bolt_diameter),
            "hole_diameter": _quantity(value.web_fastener.hole_diameter),
            "source_authority_id": value.web_fastener.source_authority_id,
            "thread_condition": value.web_fastener.thread_condition,
            "nominal_shear_stress": None
            if value.web_fastener.nominal_shear_stress is None
            else _quantity(value.web_fastener.nominal_shear_stress),
        },
        "flange_geometry": {
            "plate_length": _quantity(value.flange_geometry.plate_length),
            "plate_thickness": _quantity(value.flange_geometry.plate_thickness),
            "inner_strip_width": _quantity(value.flange_geometry.inner_strip_width),
            "bolts_per_line": value.flange_geometry.bolts_per_line,
            "longitudinal_pitch": _quantity(value.flange_geometry.longitudinal_pitch),
            "group_centroid_distance": _quantity(value.flange_geometry.group_centroid_distance),
            "outer_plate_count_per_flange": value.flange_geometry.outer_plate_count_per_flange,
            "inner_strip_count_per_flange": value.flange_geometry.inner_strip_count_per_flange,
            "locked_top_bottom_identical": value.flange_geometry.locked_top_bottom_identical,
            "locked_inner_symmetric": value.flange_geometry.locked_inner_symmetric,
        },
        "flange_fastener": {
            "bolt_diameter": _quantity(value.flange_fastener.bolt_diameter),
            "hole_diameter": _quantity(value.flange_fastener.hole_diameter),
            "source_authority_id": value.flange_fastener.source_authority_id,
            "thread_condition": value.flange_fastener.thread_condition,
            "nominal_shear_stress": None
            if value.flange_fastener.nominal_shear_stress is None
            else _quantity(value.flange_fastener.nominal_shear_stress),
        },
        "actions": {
            "axial_force_l": _quantity(value.actions.axial_force_l),
            "major_shear_v": _quantity(value.actions.major_shear_v),
            "major_moment_t": _quantity(value.actions.major_moment_t),
        },
    }


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def _component(result: service.WIMomentSplicePreviewResult, name: str) -> WIMomentComponentResult:
    return next(item for item in result.slice5_result.components if item.region_id.value == name)


def test_controlled_hashes_sentinels_source_provenance_and_g1_through_g96() -> None:
    for relative, (digest, sentinel) in CONTROLLED.items():
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == digest
        if sentinel is not None:
            assert path.read_text(encoding="utf-8").strip().endswith(sentinel)
    golden = json.loads((ROOT / GOLDEN_PATH).read_text(encoding="utf-8"))
    assert golden["product_id"] == "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
    assert golden["contract"] == "4.1A-RC1"
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{index}" for index in range(1, 97)
    ]
    ledger = (ROOT / next(path for path in CONTROLLED if "AUTHORITY_LEDGER" in path)).read_text(
        encoding="utf-8"
    )
    assert "ASCE/SEI 74-23" in ledger
    assert ASCE_74_23_ERRATUM == "Erratum 1"


def test_default_preview_exact_handoff_geometry_paths_demands_and_equilibrium() -> None:
    result = service.preview_wi_moment_splice(default_wi_moment_splice_request())
    assert result.product_id == "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
    assert result.contract_version == "4.1A-RC1"
    assert result.geometry_status is WIMomentSpliceStatus.VALID
    assert result.assembly_status is WIMomentSpliceStatus.NOT_EVALUATED
    assert result.design_check_ready
    assert not result.resistance_evaluated
    assert result.visualization.beam_end_planes_l[0].to(Unit.IN).magnitude == Decimal("-0.25")
    assert result.visualization.beam_end_planes_l[1].to(Unit.IN).magnitude == Decimal("0.25")
    assert result.flange_clear_body_length.to(Unit.IN).magnitude == Decimal("4.4370")
    assert result.rational_face_sublayer_thickness.to(Unit.IN).magnitude == Decimal("0.25")
    assert len(result.visualization.boxes) == 14
    assert len(result.visualization.bolts) == 24
    flange_boxes = [
        item for item in result.visualization.boxes if "FLANGE_SPLICE_PLATE" in item.component_id
    ]
    assert len(flange_boxes) == 6
    assert {item.component_id for item in flange_boxes} == {
        "TOP_OUTER_FLANGE_SPLICE_PLATE",
        "TOP_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
        "TOP_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
        "BOTTOM_OUTER_FLANGE_SPLICE_PLATE",
        "BOTTOM_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
        "BOTTOM_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
    }
    flange_bolts = [
        item
        for item in result.visualization.bolts
        if "_TOP_" in item.bolt_id or "_BOTTOM_" in item.bolt_id
    ]
    assert len(flange_bolts) == 16
    assert len({item.bolt_id for item in flange_bolts}) == 16
    assert all(
        item.washer_count == 2 and item.internal_hardware_count == 0 for item in flange_bolts
    )
    assert all("FLANGE" in item.path_layers[1] for item in flange_bolts)
    assert all(item.path_layers[0].endswith("OUTER_FLANGE_SPLICE_PLATE") for item in flange_bolts)
    assert all(item.path_layers[2].endswith("INNER_FLANGE_SPLICE_PLATE") for item in flange_bolts)
    assert result.equilibrium.slice5_exact
    assert result.equilibrium.top_branch_exact
    assert result.equilibrium.bottom_branch_exact
    assert result.equilibrium.whole_joint_exact
    assert result.equilibrium.beam_a_b_equal_opposite
    top = _component(result, "TOP_FLANGE")
    web = _component(result, "WEB")
    bottom = _component(result, "BOTTOM_FLANGE")
    assert top.wrench.force_lvt.l.to(Unit.KIP).magnitude == Decimal(
        "15.402961500493583415597235932872655478775913129318854886475814412635735439289240"
    )
    assert web.wrench.force_lvt.l.to(Unit.KIP).magnitude == Decimal("7.2")
    assert web.wrench.force_lvt.v.to(Unit.KIP).magnitude == Decimal("-10")
    assert web.wrench.moment_lvt.t.to(Unit.KIP_IN).magnitude == Decimal(
        "14.392892398815399802566633761105626850937808489634748272458045409674234945705824"
    )
    assert bottom.wrench.force_lvt.l.to(Unit.KIP).magnitude == Decimal(
        "-2.6029615004935834155972359328726554787759131293188548864758144126357354392892397"
    )
    assert result.top_flange.outer_force.to(Unit.KIP).magnitude == Decimal(
        "7.74096742349457058242843040473840078973346495557749259624876604146100691016781842"
    )
    assert result.top_flange.inner_total_force.to(Unit.KIP).magnitude == Decimal(
        "7.66199407699901283316880552813425468904244817374136229022704837117472852912142158"
    )
    assert result.bottom_flange.outer_force.to(Unit.KIP).magnitude == Decimal(
        "-1.34096742349457058242843040473840078973346495557749259624876604146100691016781827"
    )
    assert result.bottom_flange.inner_total_force.to(Unit.KIP).magnitude == Decimal(
        "-1.26199407699901283316880552813425468904244817374136229022704837117472852912142143"
    )
    groups = {item.group_id: item for item in result.flange_group_demands}
    outer = groups["BEAM_A_TOP_OUTER"].per_bolt_plane_demands[0]
    inner = groups["BEAM_A_TOP_INNER_NEGATIVE"].per_bolt_plane_demands[0]
    assert outer.force_l.to(Unit.KIP).magnitude == Decimal(
        "1.935241855873642645607107601184600197433366238894373149062191510365251727541954605"
    )
    assert inner.force_l.to(Unit.KIP).magnitude == Decimal(
        "1.915498519249753208292201382033563672260612043435340572556762092793682132280355395"
    )
    assert outer.force_l != inner.force_l
    assert len(result.visualization.material_regions) >= 14
    flange_material_regions = [
        item
        for item in result.visualization.material_regions
        if "FLANGE_SPLICE_PLATE" in item.region_id
    ]
    assert all(
        item.lw_axis == (Decimal(1), Decimal(0), Decimal(0)) for item in flange_material_regions
    )
    assert result.rational_method_engineering_review_required
    assert result.connection_element_qualification == "REQUIRED_2_3_2"
    assert result.moment_connection_stiffness_classification == "NOT_EVALUATED"
    assert result.moment_rotation_capacity == "NOT_EVALUATED"
    assert result.full_strength_classification == "NOT_EVALUATED"


def test_branch_equations_guards_and_zero_resultant_nonzero_local_moment() -> None:
    branch = decompose_flange_wrench(
        flange_id="TOP",
        flange_reference_v=q("4.75", Unit.IN),
        outer_reference_v=q("5.25", Unit.IN),
        inner_reference_v=q("4.25", Unit.IN),
        flange_force=q(0, Unit.KIP),
        flange_local_moment=q(
            "0.039486673247778874629812438302073050345508390918065153010858835143139190523198420",
            Unit.KIP_IN,
        ),
    )
    assert branch.outer_force.to(Unit.KIP).magnitude == Decimal(
        "0.03948667324777887462981243830207305034550839091806515301085883514313919052319842"
    )
    assert branch.inner_total_force.magnitude == branch.outer_force.magnitude.copy_negate()
    assert branch.exact_force_equilibrium
    assert branch.exact_local_moment_equilibrium
    with pytest.raises(ValueError, match="flange_force"):
        decompose_flange_wrench(
            flange_id="X",
            flange_reference_v=q(0, Unit.IN),
            outer_reference_v=q(1, Unit.IN),
            inner_reference_v=q(-1, Unit.IN),
            flange_force=q(1, Unit.IN),
            flange_local_moment=q(0, Unit.KIP_IN),
        )
    with pytest.raises(ValueError, match="flange_local_moment"):
        decompose_flange_wrench(
            flange_id="X",
            flange_reference_v=q(0, Unit.IN),
            outer_reference_v=q(1, Unit.IN),
            inner_reference_v=q(-1, Unit.IN),
            flange_force=q(1, Unit.KIP),
            flange_local_moment=q(0, Unit.KIP),
        )
    with pytest.raises(ValueError, match="BALANCED"):
        decompose_flange_wrench(
            flange_id="X",
            flange_reference_v=q(0, Unit.IN),
            outer_reference_v=q(1, Unit.IN),
            inner_reference_v=q(2, Unit.IN),
            flange_force=q(1, Unit.KIP),
            flange_local_moment=q(0, Unit.KIP_IN),
        )


def test_test_only_two_plane_bolt_strength_and_source_pending() -> None:
    outer = FlangePlaneDemand(
        q(
            "1.935241855873642645607107601184600197433366238894373149062191510365251727541954605",
            Unit.KIP,
        ),
        q(0, Unit.KIP),
        "outer",
        "g",
        "b",
    )
    inner = FlangePlaneDemand(
        q(
            "1.915498519249753208292201382033563672260612043435340572556762092793682132280355395",
            Unit.KIP,
        ),
        q(0, Unit.KIP),
        "inner",
        "g",
        "b",
    )
    result = evaluate_asymmetric_two_plane_bolt(
        bolt_id="b",
        physical_path=(
            "TOP_OUTER_FLANGE_SPLICE_PLATE",
            "TOP_BEAM_FLANGE",
            "TOP_INNER_FLANGE_SPLICE_PLATE",
        ),
        outer_plane=outer,
        inner_plane=inner,
        diameter=q("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="TEST_ONLY_F3125",
        nominal_shear_stress=q(68, Unit.KSI),
    )
    assert result.physical_shear_plane_count == 2
    assert result.per_plane_design_capacity is not None
    with localcontext() as context:
        context.prec = 100
        exact_test_capacity = Decimal("0.75") * Decimal(68) * PLATE_PI * Decimal("0.5") ** 2 / 4
        exact_outer_utilization = outer.force_l.magnitude / exact_test_capacity
        exact_inner_utilization = inner.force_l.magnitude / exact_test_capacity
    assert exact_test_capacity == Decimal(
        "10.01382658331746594759967578420341544337847746050814980435763588798116479503662500"
    )
    expected_outer = Decimal(
        "0.193256977217646124300219332034439908070289183057640986934511467808256605822911380886313020"
    )
    expected_inner = Decimal(
        "0.191285369614936002648513360477263414415215839015020695290617247569445581482747012626652272"
    )
    with localcontext() as context:
        context.prec = 100
        assert exact_outer_utilization.quantize(expected_outer) == expected_outer
        assert exact_inner_utilization.quantize(expected_inner) == expected_inner
    assert result.per_plane_design_capacity is not None
    assert abs(
        result.per_plane_design_capacity.to(Unit.KIP).magnitude - exact_test_capacity
    ) < Decimal("1E-48")
    assert result.outer_utilization is not None
    assert result.inner_utilization is not None
    assert abs(result.outer_utilization - exact_outer_utilization) < Decimal("1E-48")
    assert abs(result.inner_utilization - exact_inner_utilization) < Decimal("1E-48")
    assert result.governing_utilization == result.outer_utilization
    assert result.status is AsymmetricBoltStatus.PASS
    assert not result.planes_equal
    assert result.bolt_axis_tension.canonical_magnitude == 0
    pending = evaluate_asymmetric_two_plane_bolt(
        bolt_id="pending",
        physical_path=(
            "BOTTOM_OUTER_FLANGE_SPLICE_PLATE",
            "BOTTOM_BEAM_FLANGE",
            "BOTTOM_INNER_FLANGE_SPLICE_PLATE",
        ),
        outer_plane=inner,
        inner_plane=inner,
        diameter=q("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="ASTM_F593_17_GROUP_2_316_316L",
        nominal_shear_stress=None,
    )
    assert pending.status is AsymmetricBoltStatus.NOT_EVALUATED
    assert pending.planes_equal
    assert pending.per_plane_design_capacity is None
    assert pending.source_required_reason == "SOURCE_AUTHORIZED_FNV_REQUIRED"
    failure = evaluate_asymmetric_two_plane_bolt(
        bolt_id="fail",
        physical_path=(
            "TOP_OUTER_FLANGE_SPLICE_PLATE",
            "TOP_BEAM_FLANGE",
            "TOP_INNER_FLANGE_SPLICE_PLATE",
        ),
        outer_plane=replace(outer, force_l=q(20, Unit.KIP)),
        inner_plane=inner,
        diameter=q("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="TEST_ONLY_F3125",
        nominal_shear_stress=q(68, Unit.KSI),
    )
    assert failure.status is AsymmetricBoltStatus.FAIL
    with pytest.raises(ValueError, match="flange common bolt"):
        evaluate_asymmetric_two_plane_bolt(
            bolt_id="bad",
            physical_path=("a", "web", "b"),
            outer_plane=outer,
            inner_plane=inner,
            diameter=q("0.5", Unit.IN),
            thread_condition="EXCLUDED",
            source_authority_id="TEST",
            nominal_shear_stress=q(68, Unit.KSI),
        )


def test_flange_plate_bodies_use_slice4_and_zero_is_not_required() -> None:
    common = {
        "width": q(8, Unit.IN),
        "thickness": q("0.5", Unit.IN),
        "clear_body_length": q("4.437", Unit.IN),
    }
    zero = evaluate_flange_plate_body(component_id="zero", signed_force=q(0, Unit.KIP), **common)
    tension = evaluate_flange_plate_body(
        component_id="tension",
        signed_force=q(
            "7.74096742349457058242843040473840078973346495557749259624876604146100691016781842",
            Unit.KIP,
        ),
        **common,
    )
    compression = evaluate_flange_plate_body(
        component_id="compression",
        signed_force=q(
            "-1.34096742349457058242843040473840078973346495557749259624876604146100691016781827",
            Unit.KIP,
        ),
        **common,
    )
    assert zero.status is FlangeBodyStatus.NOT_REQUIRED_ZERO_FORCE
    assert zero.mode == "ZERO_FORCE"
    assert zero.design_capacity is None
    assert tension.mode == "TENSION"
    assert tension.tension_strength is not None
    assert compression.mode == "COMPRESSION"
    assert compression.compression_strength is not None
    assert tension.status in {FlangeBodyStatus.PASS, FlangeBodyStatus.FAIL}
    assert compression.status in {FlangeBodyStatus.PASS, FlangeBodyStatus.FAIL}


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("gap", "POSITIVE_BEAM_END_GAP_REQUIRED"),
        ("plate_count", "BALANCED_OUTER_PLUS_TWO_INNER_PLATES_REQUIRED"),
        ("top_bottom", "IDENTICAL_TOP_BOTTOM_FLANGE_TOPOLOGY_REQUIRED"),
        ("inner_symmetry", "TWO_SYMMETRIC_INNER_STRIPS_REQUIRED"),
        ("web_overlap", "INNER_STRIP_WEB_OVERLAP"),
        ("pitch", "FLANGE_BOLT_PITCH_INSUFFICIENT"),
        ("hole", "FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_INNER_STRIP"),
    ],
)
def test_invalid_geometry_fails_closed(field: str, reason: str) -> None:
    base = default_wi_moment_splice_request()
    geometry = base.flange_geometry
    if field == "gap":
        changed = replace(base, beam_end_gap=q(0, Unit.IN))
    elif field == "plate_count":
        changed = replace(base, flange_geometry=replace(geometry, outer_plate_count_per_flange=0))
    elif field == "top_bottom":
        changed = replace(
            base, flange_geometry=replace(geometry, locked_top_bottom_identical=False)
        )
    elif field == "inner_symmetry":
        changed = replace(base, flange_geometry=replace(geometry, locked_inner_symmetric=False))
    elif field == "web_overlap":
        changed = replace(
            base, flange_geometry=replace(geometry, inner_strip_width=q("3.8", Unit.IN))
        )
    elif field == "pitch":
        changed = replace(
            base, flange_geometry=replace(geometry, longitudinal_pitch=q("0.5", Unit.IN))
        )
    else:
        changed = replace(
            base, flange_fastener=replace(base.flange_fastener, hole_diameter=q("3.1", Unit.IN))
        )
    preview = service.preview_wi_moment_splice(changed)
    assert preview.geometry_status is WIMomentSpliceStatus.INVALID_GEOMETRY
    assert reason in preview.geometry_invalid_reasons
    design = service.design_check_wi_moment_splice(changed)
    assert design.assembly_status is WIMomentSpliceStatus.INVALID_GEOMETRY
    assert design.failed_check_ids == ("INVALID_GEOMETRY",)


def test_input_contract_rejects_unsupported_actions_profile_topology_and_values() -> None:
    base = default_wi_moment_splice_request()
    zero_force = q(0, Unit.KIP)
    zero_moment = q(0, Unit.KIP_IN)
    for kwargs, message in (
        ({"minor_shear_t": q(1, Unit.KIP)}, "MINOR_SHEAR"),
        ({"minor_moment_v": q(1, Unit.KIP_IN)}, "MINOR_AXIS_MOMENT"),
        ({"torsion_l": q(1, Unit.KIP_IN)}, "TORSION"),
    ):
        values = {
            "axial_force_l": zero_force,
            "major_shear_v": zero_force,
            "major_moment_t": zero_moment,
            "minor_shear_t": zero_force,
            "minor_moment_v": zero_moment,
            "torsion_l": zero_moment,
        }
        values.update(kwargs)
        with pytest.raises(ValueError, match=message):
            WIMomentSpliceActions(**values)
    with pytest.raises(ValueError, match="CHANNEL"):
        replace(base, profile_family="CHANNEL")
    with pytest.raises(ValueError, match="IDENTICAL"):
        replace(base, beams_locked_identical=False)
    with pytest.raises(ValueError, match="MAX_THREE"):
        replace(base, flange_geometry=replace(base.flange_geometry, bolts_per_line=4))
    with pytest.raises(ValueError, match="Hole diameter"):
        replace(
            base, flange_fastener=replace(base.flange_fastener, hole_diameter=q("0.4", Unit.IN))
        )
    with pytest.raises(ValueError, match="source_authority_id"):
        replace(base, flange_fastener=replace(base.flange_fastener, source_authority_id=" "))
    with pytest.raises(ValueError, match="thread_condition"):
        replace(base, flange_fastener=replace(base.flange_fastener, thread_condition="UNKNOWN"))
    with pytest.raises(ValueError, match="request_id"):
        replace(base, request_id=" ")
    with pytest.raises(ValueError, match="contract"):
        replace(base, orchestration_contract_version="future")
    with pytest.raises(ValueError, match="source_length_unit"):
        replace(base, source_length_unit=Unit.KIP)
    with pytest.raises(TypeError, match="request"):
        service.preview_wi_moment_splice(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("axial", "shear", "moment"),
    [
        ("20", "0", "0"),
        ("0", "0", "100"),
        ("20", "-10", "-100"),
        ("-20", "-10", "100"),
        ("20", "10", "100"),
    ],
)
def test_pure_modes_and_sign_reversal_matrix_closes_exactly(
    axial: str, shear: str, moment: str
) -> None:
    base = default_wi_moment_splice_request()
    request = replace(
        base,
        actions=replace(
            base.actions,
            axial_force_l=q(axial, Unit.KIP),
            major_shear_v=q(shear, Unit.KIP),
            major_moment_t=q(moment, Unit.KIP_IN),
        ),
    )
    result = service.preview_wi_moment_splice(request)
    assert result.equilibrium.whole_joint_exact
    assert result.top_flange.exact_force_equilibrium
    assert result.top_flange.exact_local_moment_equilibrium
    assert result.bottom_flange.exact_force_equilibrium
    assert result.bottom_flange.exact_local_moment_equilibrium


def test_us_si_equivalence_and_deterministic_engineering_fingerprints() -> None:
    us = service.preview_wi_moment_splice(default_wi_moment_splice_request())
    si = service.preview_wi_moment_splice(
        default_wi_moment_splice_request(EngineeringUnitSystem.SI)
    )
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.geometry_fingerprint == si.geometry_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert us.application_fingerprint == si.application_fingerprint
    assert us.slice5_result.result_fingerprint == si.slice5_result.result_fingerprint
    assert us.top_flange.result_fingerprint == si.top_flange.result_fingerprint
    assert us.equilibrium.result_fingerprint == si.equilibrium.result_fingerprint


def test_preview_executes_zero_resistance_and_design_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service,
        "evaluate_flange_plate_body",
        lambda **_kwargs: pytest.fail("preview evaluated flange body resistance"),
    )
    monkeypatch.setattr(
        service,
        "evaluate_asymmetric_two_plane_bolt",
        lambda **_kwargs: pytest.fail("preview evaluated bolt resistance"),
    )
    preview = service.preview_wi_moment_splice(default_wi_moment_splice_request())
    assert not preview.resistance_evaluated
    assert preview.design_check_ready


def test_design_aggregation_source_pending_precedence_and_serialization() -> None:
    request = default_wi_moment_splice_request()
    design = service.design_check_wi_moment_splice(request)
    assert design.assembly_status in {WIMomentSpliceStatus.FAIL, WIMomentSpliceStatus.NOT_EVALUATED}
    assert not design.ordinary_pass_allowed
    assert design.rational_method_engineering_review_required
    assert design.disclaimer_id == "WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1"
    assert all(item.status is AsymmetricBoltStatus.NOT_EVALUATED for item in design.flange_bolts)
    assert any(item.startswith("FLANGE_BOLT:") for item in design.unavailable_check_ids)
    assert design.governing_utilization is not None
    preview_dto = serialize_wi_moment_splice_preview(design.preview)
    design_dto = serialize_wi_moment_splice_design(design)
    assert preview_dto.result["engineering_fingerprint"] == design.preview.engineering_fingerprint
    assert design_dto.result["result_fingerprint"] == design.result_fingerprint
    assert "canonical_value" in json.dumps(_serialize(design))


def test_dto_mapping_api_openapi_and_http_engineering_statuses() -> None:
    dto = WIMomentSpliceRequestDTO.model_validate(_dto_payload())
    mapped = map_wi_moment_splice_request(dto)
    assert mapped == default_wi_moment_splice_request()
    preview = _post("/api/v1/calculations/wi-major-axis-moment-splice/preview", _dto_payload())
    assert preview.status_code == 200
    assert preview.json()["resistance_evaluated"] is False
    design = _post("/api/v1/calculations/wi-major-axis-moment-splice/design-check", _dto_payload())
    assert design.status_code == 200
    assert design.json()["assembly_status"] in {"FAIL", "NOT_EVALUATED"}
    rejected = _dto_payload()
    rejected["request_id"] = " "
    assert (
        _post("/api/v1/calculations/wi-major-axis-moment-splice/preview", rejected).status_code
        == 422
    )
    app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
    schema = app.openapi()
    for path in (
        "/api/v1/calculations/wi-major-axis-moment-splice/preview",
        "/api/v1/calculations/wi-major-axis-moment-splice/design-check",
    ):
        assert path in schema["paths"]
        assert "post" in schema["paths"][path]


def test_canonical_helpers_and_fastener_stress_validation() -> None:
    assert resistance._fingerprint({"a": [Decimal("1.20")]}) == resistance._fingerprint(
        {"a": [Decimal("1.2")]}
    )
    assert service._fingerprint({"a": [Decimal("1.20")]}) == service._fingerprint(
        {"a": [Decimal("1.2")]}
    )
    base = default_wi_moment_splice_request()
    with pytest.raises(TypeError, match="stress"):
        replace(
            base, flange_fastener=replace(base.flange_fastener, nominal_shear_stress=q(1, Unit.KIP))
        )
    with pytest.raises(ValueError, match="positive"):
        WIMomentSpliceFastener(
            q("0.5", Unit.IN), q("0.563", Unit.IN), "x", "EXCLUDED", q(0, Unit.KSI)
        )


def test_zero_resultant_service_path_one_bolt_line_and_zero_design() -> None:
    base = default_wi_moment_splice_request()
    actions = replace(
        base.actions,
        axial_force_l=q(
            "-28.1342546890424481737413622902270483711747285291214215202369200394866732477788750",
            Unit.KIP,
        ),
        major_shear_v=q(0, Unit.KIP),
    )
    zero_branch = service.preview_wi_moment_splice(replace(base, actions=actions))
    assert abs(zero_branch.top_flange.flange_force.to(Unit.KIP).magnitude) <= Decimal("3E-79")
    assert zero_branch.top_flange.outer_force.magnitude > 0
    assert zero_branch.top_flange.inner_total_force.magnitude < 0
    assert zero_branch.top_flange.exact_local_moment_equilibrium
    zero_groups = [item for item in zero_branch.flange_group_demands if item.demand is None]
    assert len(zero_groups) == 0
    one_line = replace(
        base,
        flange_geometry=replace(base.flange_geometry, bolts_per_line=1),
    )
    one_line_preview = service.preview_wi_moment_splice(one_line)
    assert one_line_preview.geometry_status is WIMomentSpliceStatus.VALID
    assert all(
        len(item.per_bolt_plane_demands) in {1, 2} for item in one_line_preview.flange_group_demands
    )
    all_zero = replace(
        base,
        actions=replace(
            base.actions,
            axial_force_l=q(0, Unit.KIP),
            major_shear_v=q(0, Unit.KIP),
            major_moment_t=q(0, Unit.KIP_IN),
        ),
    )
    zero_preview = service.preview_wi_moment_splice(all_zero)
    assert all(item.demand is None for item in zero_preview.flange_group_demands)
    zero_design = service.design_check_wi_moment_splice(all_zero)
    assert zero_design.governing_utilization == 0
    assert zero_design.governing_check_id == "WEB_BODY"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"plate_length": "8"}, "FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATE"),
        ({"gap": "6"}, "FLANGE_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END"),
        ({"hole": "5"}, "FLANGE_HOLE_WEB_COLLISION"),
        ({"group_centroid": "0.2"}, "FLANGE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS"),
    ],
)
def test_additional_physical_hole_and_clear_body_rejections(
    change: dict[str, str], reason: str
) -> None:
    base = default_wi_moment_splice_request()
    geometry = base.flange_geometry
    fastener = base.flange_fastener
    request = base
    if "plate_length" in change:
        request = replace(
            base,
            flange_geometry=replace(geometry, plate_length=q(change["plate_length"], Unit.IN)),
        )
    if "gap" in change:
        request = replace(base, beam_end_gap=q(change["gap"], Unit.IN))
    if "hole" in change:
        request = replace(
            base,
            flange_fastener=replace(fastener, hole_diameter=q(change["hole"], Unit.IN)),
        )
    if "group_centroid" in change:
        request = replace(
            base,
            flange_geometry=replace(
                geometry, group_centroid_distance=q(change["group_centroid"], Unit.IN)
            ),
        )
    preview = service.preview_wi_moment_splice(request)
    assert reason in preview.geometry_invalid_reasons


def test_internal_fail_closed_invariants_and_local_mapping_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = default_wi_moment_splice_request()
    preview = service.preview_wi_moment_splice(base)
    group = preview.flange_group_demands[0]
    monkeypatch.setattr(
        service,
        "evaluate_multirow_connection_with_resolved_demand",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("controlled mapping stop")),
    )
    summary = service._local_summary(
        base,
        group,
        component_id="TEST_LOCAL",
        force=preview.top_flange.outer_force,
        width=base.beam.flange_width,
        thickness=base.flange_geometry.plate_thickness,
        line_count=2,
    )
    assert summary.warnings == ("LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE:controlled mapping stop",)
    slice5 = service._slice5(base)
    top, bottom = service._branch_geometry(base, slice5)
    nonexact = replace(top, exact_force_equilibrium=False)
    equilibrium = service._equilibrium(base, slice5, nonexact, bottom)
    assert not equilibrium.whole_joint_exact
    monkeypatch.setattr(service, "_equilibrium", lambda *_args: equilibrium)
    with pytest.raises(ValueError, match="EXACT_WHOLE_JOINT"):
        service.preview_wi_moment_splice(base)
    bad_slice = replace(
        slice5,
        equilibrium=replace(slice5.equilibrium, axial_equilibrium_exact=False),
    )
    monkeypatch.setattr(service, "_slice5", lambda _request: bad_slice)
    with pytest.raises(ValueError, match="SLICE5_EXACT"):
        service.preview_wi_moment_splice(base)


def test_http_mapping_exception_boundary_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        routes,
        "preview_wi_moment_splice",
        lambda _request: (_ for _ in ()).throw(ValueError("preview boundary")),
    )
    preview = _post("/api/v1/calculations/wi-major-axis-moment-splice/preview", _dto_payload())
    assert preview.status_code == 422
    assert preview.json()["detail"]["message"] == "preview boundary"
    monkeypatch.setattr(
        routes,
        "design_check_wi_moment_splice",
        lambda _request: (_ for _ in ()).throw(ValueError("design boundary")),
    )
    design = _post("/api/v1/calculations/wi-major-axis-moment-splice/design-check", _dto_payload())
    assert design.status_code == 422
    assert design.json()["detail"]["message"] == "design boundary"


def test_design_handles_unavailable_web_body_utilization(monkeypatch: pytest.MonkeyPatch) -> None:
    request = default_wi_moment_splice_request()
    preview = service.preview_wi_moment_splice(request)
    body = service._web_body(request, preview)
    monkeypatch.setattr(
        service,
        "_web_body",
        lambda *_args: replace(body, rational_utilization=None),
    )
    result = service.design_check_wi_moment_splice(request)
    assert result.governing_check_id is not None
    assert result.governing_check_id.startswith("FLANGE_BODY:")
