from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from frp_master_connection.api import routes as routes_module
from frp_master_connection.api.app import create_app
from frp_master_connection.api.channel_moment_splice_mapping import (
    map_channel_moment_splice_request,
    serialize_channel_moment_splice_design,
    serialize_channel_moment_splice_preview,
)
from frp_master_connection.api.channel_moment_splice_schemas import (
    ChannelMomentSpliceRequestDTO,
)
from frp_master_connection.application import channel_moment_splice_orchestration as service
from frp_master_connection.calculation import (
    ASCE_74_23_ERRATUM,
    CHANNEL_WEB_BRANCH_METHOD,
    PLATE_PI,
    AsymmetricBoltStatus,
    FlangePlaneDemand,
    PhysicalQuantity,
    Unit,
    WebSpliceCriticalSectionAction,
    calculate_eccentric_bolt_group_demand,
    decompose_channel_web_wrench,
    evaluate_channel_two_plane_bolt,
    evaluate_rational_body_interaction,
)
from frp_master_connection.calculation import channel_moment_splice_resistance as channel_resistance
from frp_master_connection.calculation.channel_moment_resultants import (
    ChannelMomentRegionId,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import (
    ChannelMomentSpliceActions,
    ChannelMomentSpliceRequest,
    ChannelMomentSpliceShearCenter,
    ChannelMomentSpliceShearCenterMethod,
    ChannelMomentSpliceStatus,
    EngineeringUnitSystem,
    default_channel_moment_splice_request,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = (
    "backend/tests/golden/stage_4_1b_channel_major_axis_moment_splice_golden_benchmarks_rc1.json"
)
CONTROLLED = {
    "docs/governance/STAGE_4_1B_CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_DECISION.md": (
        "3DD77B42FDB3A9799B7C1E380AA2116F6CC1DBBFABCEE9BBF7E9DFB295C0E83E",
        "**END OF STAGE 4.1B CHANNEL MAJOR-AXIS MOMENT SPLICE DECISION**",
    ),
    "docs/engineering/"
    "STAGE_4_1B_CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_ENGINEERING_SPECIFICATION_RC1.md": (
        "3207CAB2F90FE6E3494BEE89297E16D53AE29F67DF6A1FD0D6371408B7C574AF",
        "**END OF STAGE 4.1B CHANNEL MAJOR-AXIS MOMENT SPLICE ENGINEERING SPECIFICATION RC1**",
    ),
    GOLDEN_PATH: (
        "ED636AE37A062768EC3A45D4ED234B9363D0CDD8A49DCCCEA02543ADC50D123A",
        None,
    ),
    "docs/qa/STAGE_4_1B_CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_AUTHORITY_LEDGER_RC1.md": (
        "144A7A86759422CCD88BE7A36FF3483843801A243C9DBFDFF751CE2D8177B519",
        "**END OF STAGE 4.1B CHANNEL MAJOR-AXIS MOMENT SPLICE AUTHORITY LEDGER RC1**",
    ),
}


def q(value: Decimal | str | int, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def assert_decimal_close(actual: Decimal, expected: str, tolerance: str = "1E-88") -> None:
    assert abs(actual - Decimal(expected)) <= Decimal(tolerance)


def _quantity(value: PhysicalQuantity) -> dict[str, str]:
    return {"value": str(value.magnitude), "unit": value.unit.value}


def _dto_payload() -> dict[str, object]:
    value = default_channel_moment_splice_request()
    fastener = {
        "bolt_diameter": _quantity(value.web_fastener.bolt_diameter),
        "hole_diameter": _quantity(value.web_fastener.hole_diameter),
        "source_authority_id": value.web_fastener.source_authority_id,
        "thread_condition": value.web_fastener.thread_condition,
        "nominal_shear_stress": None,
    }
    return {
        "orchestration_contract_version": value.orchestration_contract_version,
        "request_id": value.request_id,
        "unit_system": value.unit_system.value,
        "source_length_unit": value.source_length_unit.value,
        "beams_locked_identical": value.beams_locked_identical,
        "beams_same_orientation": value.beams_same_orientation,
        "opening_direction": value.opening_direction,
        "beam": {
            "profile_family": value.beam.profile_family,
            "depth": _quantity(value.beam.depth),
            "flange_width": _quantity(value.beam.flange_width),
            "web_thickness": _quantity(value.beam.web_thickness),
            "flange_thickness": _quantity(value.beam.flange_thickness),
            "display_length_each_side": _quantity(value.beam.display_length_each_side),
            "equal_flange": value.beam.equal_flange,
            "lipped": value.beam.lipped,
            "back_to_back": value.beam.back_to_back,
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
        "web_fastener": fastener,
        "flange_geometry": {
            "plate_length": _quantity(value.flange_geometry.plate_length),
            "plate_thickness": _quantity(value.flange_geometry.plate_thickness),
            "inner_plate_width": _quantity(value.flange_geometry.inner_plate_width),
            "transverse_gauge": _quantity(value.flange_geometry.transverse_gauge),
            "bolts_per_transverse_line": value.flange_geometry.bolts_per_transverse_line,
            "longitudinal_pitch": _quantity(value.flange_geometry.longitudinal_pitch),
            "group_centroid_distance": _quantity(value.flange_geometry.group_centroid_distance),
            "outer_plate_count_per_flange": 1,
            "inner_plate_count_per_flange": 1,
            "locked_top_bottom_identical": True,
        },
        "flange_fastener": fastener,
        "actions": {
            "axial_force_l": _quantity(value.actions.axial_force_l),
            "major_shear_v": _quantity(value.actions.major_shear_v),
            "major_moment_t": _quantity(value.actions.major_moment_t),
        },
        "shear_center": {
            "method": value.shear_center.method.value,
            "explicit_coordinate_t": None,
            "explicit_provenance": None,
            "include_rational_comparison": False,
        },
    }


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_controlled_hashes_sentinels_and_complete_g1_through_g112() -> None:
    for relative, (digest, sentinel) in CONTROLLED.items():
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == digest
        if sentinel is not None:
            assert path.read_text(encoding="utf-8").strip().endswith(sentinel)
    golden = json.loads((ROOT / GOLDEN_PATH).read_text(encoding="utf-8"))
    assert golden["product_id"] == "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
    assert golden["contract"] == "4.1B-RC1"
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{index}" for index in range(1, 113)
    ]
    assert ASCE_74_23_ERRATUM == "Erratum 1"


def test_default_preview_exact_slice6_handoff_geometry_paths_and_equilibrium() -> None:
    result = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    assert result.product_id == "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE"
    assert result.contract_version == "4.1B-RC1"
    assert result.geometry_status is ChannelMomentSpliceStatus.VALID
    assert result.assembly_status is ChannelMomentSpliceStatus.NOT_EVALUATED
    assert result.design_check_ready
    assert not result.resistance_evaluated
    assert result.visualization.beam_end_planes_l[0].to(Unit.IN).magnitude == Decimal("-0.25")
    assert result.visualization.beam_end_planes_l[1].to(Unit.IN).magnitude == Decimal("0.25")
    assert len(result.visualization.boxes) == 12
    assert len(result.visualization.bolts) == 24
    assert sum("WEB_SPLICE_PLATE" in item.component_id for item in result.visualization.boxes) == 2
    assert (
        sum("FLANGE_SPLICE_PLATE" in item.component_id for item in result.visualization.boxes) == 4
    )
    assert result.visualization.xray_inner_components
    assert all(item.internal_hardware_count == 0 for item in result.visualization.bolts)
    web_paths = {
        item.path_layers
        for item in result.visualization.bolts
        if item.group_id.endswith("WEB_BACK")
    }
    assert web_paths == {("BACK_WEB_SPLICE_PLATE", "CHANNEL_WEB", "OPENING_WEB_SPLICE_PLATE")}
    assert result.equilibrium.whole_connection_six_component_exact
    assert result.equilibrium.beam_a_b_equal_opposite_complete_wrenches

    top = result.slice6_result.component(ChannelMomentRegionId.TOP_FLANGE)
    web = result.slice6_result.component(ChannelMomentRegionId.WEB)
    bottom = result.slice6_result.component(ChannelMomentRegionId.BOTTOM_FLANGE)
    assert result.slice6_result.section_properties.channel_centroid_t_absolute.to(
        Unit.IN
    ).magnitude == Decimal(
        "1.18333333333333333333333333333333333333333333333333333333333333333333333333333333333333333"
    )
    assert result.slice6_result.shear_center.absolute_coordinate_t.to(Unit.IN).magnitude == Decimal(
        "-1.15625"
    )
    assert result.slice6_result.torsion_diagnostics.generated_centroidal_torsion.to(
        Unit.KIP_IN
    ).magnitude == Decimal(
        "-23.3958333333333333333333333333333333333333333333333333333333333333333333333333333333333333"
    )
    assert top.wrench.force_lvt.l.to(Unit.KIP).magnitude == Decimal(
        "15.9528023598820058997050147492625368731563421828908554572271386430678466076696165191740412"
    )
    assert_decimal_close(
        web.wrench.force_lvt.l.to(Unit.KIP).magnitude,
        "9.33333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
    )
    assert_decimal_close(
        bottom.wrench.force_lvt.l.to(Unit.KIP).magnitude,
        "-5.28613569321533923303834808259587020648967551622418879056047197640117994100294985250737457",
    )


def test_web_face_decomposition_exact_values_and_no_equal_shear_assumption() -> None:
    result = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    web = result.web_faces
    assert web.method == CHANNEL_WEB_BRANCH_METHOD
    assert web.back_normal_force.to(Unit.KIP).magnitude == Decimal(
        "4.666666666666666666666666666666666666666666666666666666666666666666666666666666666666666665"
    )
    assert web.opening_normal_force == web.back_normal_force
    assert web.back_major_shear.to(Unit.KIP).magnitude == Decimal("-19.0625")
    assert web.opening_major_shear.to(Unit.KIP).magnitude == Decimal("9.0625")
    assert web.back_local_major_moment == web.opening_local_major_moment
    assert web.exact_normal_force_recovery
    assert web.exact_major_shear_recovery
    assert web.exact_local_major_moment_recovery
    assert web.exact_free_torsion_recovery
    assert not web.blind_equal_shear_assumption_used
    with pytest.raises(ValueError, match="OPPOSITE_SIGN"):
        decompose_channel_web_wrench(
            web_reference_t=q(0, Unit.IN),
            back_reference_t=q(1, Unit.IN),
            opening_reference_t=q(2, Unit.IN),
            web_normal_force=q(1, Unit.KIP),
            web_major_shear=q(1, Unit.KIP),
            web_local_major_moment=q(0, Unit.KIP_IN),
            web_free_torsion=q(0, Unit.KIP_IN),
        )


def test_flange_branches_force_lines_grids_and_actual_plane_demands() -> None:
    result = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    assert result.top_flange.outer_force.to(Unit.KIP).magnitude == Decimal(
        "8.0353982300884955752212389380530973451327433628318584070796460176991150442477876106194689775"
    )
    assert result.top_flange.inner_total_force.to(Unit.KIP).magnitude == Decimal(
        "7.9174041297935103244837758112094395280235988200589970501474926253687315634218289085545722225"
    )
    assert_decimal_close(
        result.bottom_flange.outer_force.to(Unit.KIP).magnitude,
        "-2.70206489675516224188790560471976401179941002949852507374631268436578171091445427728613566",
    )
    assert_decimal_close(
        result.bottom_flange.inner_total_force.to(Unit.KIP).magnitude,
        "-2.58407079646017699115044247787610619469026548672566371681415929203539823008849557522123891",
    )
    groups = {item.group_id: item for item in result.flange_group_demands}
    expected = {
        "BEAM_A_TOP_OUTER": (
            "2.0088495575221238938053097345132743362831858407079646017699115044247787610619"
            "4690265486724"
        ),
        "BEAM_A_TOP_INNER": (
            "1.9793510324483775811209439528023598820058997050147492625368731563421828908554"
            "5722713864306"
        ),
        "BEAM_A_BOTTOM_OUTER": (
            "-0.675516224188790560471976401179941002949852507374631268436578171091445427728"
            "613569321533915"
        ),
        "BEAM_A_BOTTOM_INNER": (
            "-0.646017699115044247787610619469026548672566371681415929203539823008849557522"
            "123893805309725"
        ),
    }
    for group_id, value in expected.items():
        assert_decimal_close(
            groups[group_id].per_bolt_plane_demands[0].force_l.to(Unit.KIP).magnitude,
            value,
        )
    top_bolts = [item for item in result.visualization.bolts if "_TOP_" in item.bolt_id]
    assert {
        (item.center_l_v_t.l.magnitude, item.center_l_v_t.t.magnitude) for item in top_bolts
    } == {
        (Decimal("-5.5"), Decimal("1.25")),
        (Decimal("-2.5"), Decimal("1.25")),
        (Decimal("-5.5"), Decimal("2.75")),
        (Decimal("-2.5"), Decimal("2.75")),
        (Decimal("2.5"), Decimal("1.25")),
        (Decimal("5.5"), Decimal("1.25")),
        (Decimal("2.5"), Decimal("2.75")),
        (Decimal("5.5"), Decimal("2.75")),
    }


def test_web_body_test_arithmetic_and_common_bolt_source_boundary() -> None:
    preview = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    branch = preview.web_faces
    half = preview.web_clear_body_length / 2
    with localcontext() as context:
        context.prec = 100
        internal = q(
            branch.back_local_major_moment.magnitude
            - half.to(Unit.IN).magnitude * branch.back_major_shear.to(Unit.KIP).magnitude,
            Unit.KIP_IN,
        )
    assert_decimal_close(
        internal.magnitude,
        "52.40815035029498525073746312684365781710914454277286135693215339233038348082595870206489675",
    )
    with localcontext() as context:
        context.prec = 100
        body = evaluate_rational_body_interaction(
            plate_height=q("5.5", Unit.IN),
            plate_thickness=q("0.5", Unit.IN),
            actions=(
                WebSpliceCriticalSectionAction(
                    "RIGHT",
                    half,
                    q(branch.back_normal_force.magnitude * 2, branch.back_normal_force.unit),
                    q(branch.back_major_shear.magnitude * 2, branch.back_major_shear.unit),
                    q(internal.magnitude * 2, internal.unit),
                ),
            ),
            symmetry_proven=True,
            tension_design_stress=q(12, Unit.KSI),
            compression_design_stress=q(10, Unit.KSI),
            shear_design_stress=q(5, Unit.KSI),
        )
    assert_decimal_close(
        cast(Decimal, body.rational_utilization),
        "3.29566767229820327165459908822740681147760793778492893537141324751944220970769643336015017",
    )
    design = service.design_check_channel_moment_splice(default_channel_moment_splice_request())
    assert len(design.web_bolts) == 8
    assert len(design.flange_bolts) == 16
    assert all(item.status is AsymmetricBoltStatus.NOT_EVALUATED for item in design.web_bolts)
    assert all(item.status is AsymmetricBoltStatus.NOT_EVALUATED for item in design.flange_bolts)
    assert all(
        item.physical_shear_plane_count == 2 for item in (*design.web_bolts, *design.flange_bolts)
    )
    assert all(
        item.bolt_axis_tension.canonical_magnitude == 0
        for item in (*design.web_bolts, *design.flange_bolts)
    )


def test_test_only_common_bolt_strength_uses_each_actual_plane() -> None:
    preview = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    groups = {item.group_id: item for item in preview.flange_group_demands}
    outer = groups["BEAM_A_TOP_OUTER"].per_bolt_plane_demands[0]
    inner = groups["BEAM_A_TOP_INNER"].per_bolt_plane_demands[0]
    result = evaluate_channel_two_plane_bolt(
        bolt_id="test",
        physical_path=(
            "TOP_OUTER_FLANGE_SPLICE_PLATE",
            "TOP_CHANNEL_FLANGE",
            "TOP_INNER_FLANGE_SPLICE_PLATE",
        ),
        outer_plane=outer,
        inner_plane=inner,
        diameter=q("0.5", Unit.IN),
        thread_condition="EXCLUDED",
        source_authority_id="TEST_ONLY_F3125",
        nominal_shear_stress=q(68, Unit.KSI),
    )
    with localcontext() as context:
        context.prec = 100
        capacity = Decimal("0.75") * Decimal(68) * PLATE_PI * Decimal("0.5") ** 2 / 4
    assert result.per_plane_design_capacity is not None
    assert abs(result.per_plane_design_capacity.to(Unit.KIP).magnitude - capacity) < Decimal(
        "1E-48"
    )
    assert result.outer_utilization != result.inner_utilization
    assert not result.planes_equal


@pytest.mark.parametrize(
    ("axial", "shear", "moment"),
    [
        ("20", "0", "0"),
        ("0", "0", "100"),
        ("0", "-10", "0"),
        ("20", "10", "100"),
        ("-20", "-10", "100"),
        ("20", "-10", "-100"),
    ],
)
def test_pure_modes_and_sign_reversal_close_exactly(axial: str, shear: str, moment: str) -> None:
    base = default_channel_moment_splice_request()
    request = replace(
        base,
        actions=replace(
            base.actions,
            axial_force_l=q(axial, Unit.KIP),
            major_shear_v=q(shear, Unit.KIP),
            major_moment_t=q(moment, Unit.KIP_IN),
        ),
    )
    result = service.preview_channel_moment_splice(request)
    assert result.equilibrium.whole_connection_six_component_exact
    assert result.top_flange.exact_force_equilibrium
    assert result.bottom_flange.exact_local_moment_equilibrium
    assert result.web_faces.exact_free_torsion_recovery


def test_explicit_and_rational_shear_center_modes_and_provenance() -> None:
    base = default_channel_moment_splice_request()
    explicit = replace(
        base,
        shear_center=ChannelMomentSpliceShearCenter(
            ChannelMomentSpliceShearCenterMethod.EXPLICIT_VERIFIED,
            q("-1.25", Unit.IN),
            "Verified project section database record C8",
            True,
        ),
    )
    result = service.preview_channel_moment_splice(explicit)
    assert result.slice6_result.shear_center.absolute_coordinate_t.to(Unit.IN).magnitude == Decimal(
        "-1.25"
    )
    assert not result.slice6_result.shear_center.rational_comparison_is_controlling
    with pytest.raises(ValueError, match="VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED"):
        ChannelMomentSpliceShearCenter(
            ChannelMomentSpliceShearCenterMethod.EXPLICIT_VERIFIED,
            q("-1.25", Unit.IN),
            " ",
        )


def test_contract_rejects_unsupported_actions_and_channel_topologies() -> None:
    base = default_channel_moment_splice_request()
    zero_f = q(0, Unit.KIP)
    zero_m = q(0, Unit.KIP_IN)
    for kwargs, reason in (
        ({"minor_shear_t": q(1, Unit.KIP)}, "MINOR_SHEAR"),
        ({"minor_moment_v": q(1, Unit.KIP_IN)}, "MINOR_AXIS_MOMENT"),
        ({"user_torsion_l": q(1, Unit.KIP_IN)}, "USER_TORSION"),
    ):
        values = {
            "axial_force_l": zero_f,
            "major_shear_v": zero_f,
            "major_moment_t": zero_m,
            "minor_shear_t": zero_f,
            "minor_moment_v": zero_m,
            "user_torsion_l": zero_m,
        }
        values.update(kwargs)
        with pytest.raises(ValueError, match=reason):
            ChannelMomentSpliceActions(**values)
    beam_cases: tuple[tuple[dict[str, Any], str], ...] = (
        ({"lipped": True}, "LIPPED"),
        ({"back_to_back": True}, "BACK_TO_BACK"),
        ({"equal_flange": False}, "UNEQUAL_FLANGE"),
        ({"profile_family": "WIDE_FLANGE_I"}, "UNLIPPED_EQUAL_FLANGE"),
    )
    for beam_kwargs, reason in beam_cases:
        with pytest.raises(ValueError, match=reason):
            replace(base, beam=replace(base.beam, **beam_kwargs))
    with pytest.raises(ValueError, match="IDENTICAL"):
        replace(base, beams_locked_identical=False)
    with pytest.raises(ValueError, match="SAME_ORIENTATION"):
        replace(base, beams_same_orientation=False)


def test_contract_value_objects_reject_every_invalid_identity_and_quantity() -> None:
    base = default_channel_moment_splice_request()
    with pytest.raises(ValueError, match="SINGLE_SHEAR_CENTER_SOURCE_REQUIRED"):
        ChannelMomentSpliceShearCenter(
            ChannelMomentSpliceShearCenterMethod.RATIONAL_THIN_WALL,
            q(-1, Unit.IN),
            "not allowed",
        )
    with pytest.raises(ValueError, match="SINGLE_SHEAR_CENTER_SOURCE_REQUIRED"):
        ChannelMomentSpliceShearCenter(ChannelMomentSpliceShearCenterMethod.EXPLICIT_VERIFIED)
    with pytest.raises(TypeError, match="length quantity"):
        replace(base.beam, depth=q(1, Unit.KIP))
    with pytest.raises(ValueError, match="must be positive"):
        replace(base.beam, depth=q(0, Unit.IN))
    with pytest.raises(ValueError, match="MAX_THREE"):
        replace(base.flange_geometry, bolts_per_transverse_line=4)
    with pytest.raises(ValueError, match="MAX_THREE"):
        replace(base.flange_geometry, bolts_per_transverse_line=True)
    with pytest.raises(ValueError, match="smaller"):
        replace(base.web_fastener, hole_diameter=q("0.4", Unit.IN))
    with pytest.raises(ValueError, match="nonempty"):
        replace(base.web_fastener, source_authority_id=" ")
    with pytest.raises(ValueError, match="INCLUDED or EXCLUDED"):
        replace(base.web_fastener, thread_condition="UNKNOWN")
    with pytest.raises(TypeError, match="stress quantity"):
        replace(base.web_fastener, nominal_shear_stress=q(1, Unit.IN))
    with pytest.raises(ValueError, match="must be positive"):
        replace(base.web_fastener, nominal_shear_stress=q(0, Unit.KSI))
    with pytest.raises(ValueError, match="request_id"):
        replace(base, request_id=" ")
    with pytest.raises(ValueError, match="Unsupported"):
        replace(base, orchestration_contract_version="future")
    with pytest.raises(ValueError, match="in or mm"):
        replace(base, source_length_unit=Unit.KIP)
    with pytest.raises(ValueError, match="SAME_ORIENTATION"):
        replace(base, opening_direction="-T_CH")


def test_channel_web_primitives_reject_wrong_dimensions_and_bad_paths() -> None:
    valid = {
        "web_reference_t": q("0.25", Unit.IN),
        "back_reference_t": q("-0.25", Unit.IN),
        "opening_reference_t": q("0.75", Unit.IN),
        "web_normal_force": q(2, Unit.KIP),
        "web_major_shear": q(-10, Unit.KIP),
        "web_local_major_moment": q(1, Unit.KIP_IN),
        "web_free_torsion": q(-30, Unit.KIP_IN),
    }
    for key, replacement_value, match in (
        ("web_reference_t", q(1, Unit.KIP), "must be a length"),
        ("web_normal_force", q(1, Unit.IN), "must be a force"),
        ("web_free_torsion", q(1, Unit.KIP), "must be a moment"),
    ):
        values = dict(valid)
        values[key] = replacement_value
        with pytest.raises(ValueError, match=match):
            decompose_channel_web_wrench(**values)
    plane = FlangePlaneDemand(q(1, Unit.KIP), q(0, Unit.KIP), "source", "group", "bolt")
    with pytest.raises(ValueError, match="exactly three"):
        evaluate_channel_two_plane_bolt(
            bolt_id="B1",
            physical_path=cast(tuple[str, str, str], ("PLATE", "CHANNEL_WEB")),
            outer_plane=plane,
            inner_plane=plane,
            diameter=q("0.5", Unit.IN),
            thread_condition="EXCLUDED",
            source_authority_id="SOURCE_PENDING",
            nominal_shear_stress=None,
        )
    assert channel_resistance._canonical(date(2026, 9, 4)) == "2026-09-04"
    assert channel_resistance._canonical({"case": [Decimal("1")]}) == {"case": ["1"]}
    assert service._canonical(date(2026, 9, 4)) == "2026-09-04"
    assert service._canonical({"case": [Decimal("1")]}) == {"case": ["1"]}


def test_all_physical_geometry_rejection_paths_are_fail_closed() -> None:
    base = default_channel_moment_splice_request()
    invalid_plate_topology = replace(base.web_splice_plate)
    object.__setattr__(invalid_plate_topology, "count", 1)
    object.__setattr__(invalid_plate_topology, "locked_identical", False)
    topology = replace(
        base,
        beam_end_gap=q(0, Unit.IN),
        web_splice_plate=invalid_plate_topology,
        flange_geometry=replace(
            base.flange_geometry,
            outer_plate_count_per_flange=0,
            inner_plate_count_per_flange=0,
            locked_top_bottom_identical=False,
        ),
    )
    reasons = set(service.preview_channel_moment_splice(topology).geometry_invalid_reasons)
    assert {
        "POSITIVE_BEAM_END_GAP_REQUIRED",
        "IDENTICAL_BACK_AND_OPENING_WEB_PLATES_REQUIRED",
        "ONE_OUTER_AND_ONE_INNER_PLATE_PER_FLANGE_REQUIRED",
        "IDENTICAL_TOP_BOTTOM_FLANGE_TOPOLOGY_REQUIRED",
    } <= reasons
    small_web = replace(
        base,
        web_splice_plate=replace(base.web_splice_plate, length=q(1, Unit.IN), height=q(1, Unit.IN)),
    )
    assert (
        "WEB_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATES"
        in service.preview_channel_moment_splice(small_web).geometry_invalid_reasons
    )
    large_gap = replace(base, beam_end_gap=q(15, Unit.IN))
    gap_reasons = set(service.preview_channel_moment_splice(large_gap).geometry_invalid_reasons)
    assert {
        "WEB_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END",
        "WEB_HOLE_NOT_CONTAINED_AFTER_BEAM_B_END",
        "FLANGE_HOLE_NOT_CONTAINED_BEFORE_BEAM_A_END",
        "FLANGE_HOLE_NOT_CONTAINED_AFTER_BEAM_B_END",
    } <= gap_reasons
    small_flange = replace(
        base,
        flange_geometry=replace(
            base.flange_geometry, plate_length=q(1, Unit.IN), transverse_gauge=q(7, Unit.IN)
        ),
    )
    flange_reasons = set(
        service.preview_channel_moment_splice(small_flange).geometry_invalid_reasons
    )
    assert {
        "FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_SPLICE_PLATES",
        "FLANGE_COMPLETE_HOLE_NOT_CONTAINED_IN_INNER_PLATE",
    } <= flange_reasons
    insufficient = replace(
        base,
        web_bolt_group=replace(
            base.web_bolt_group,
            longitudinal_gauge=q("0.5", Unit.IN),
            centroid_offset=q("0.25", Unit.IN),
        ),
        flange_geometry=replace(
            base.flange_geometry,
            longitudinal_pitch=q("0.5", Unit.IN),
            group_centroid_distance=q("0.25", Unit.IN),
        ),
    )
    insufficient_reasons = set(
        service.preview_channel_moment_splice(insufficient).geometry_invalid_reasons
    )
    assert {
        "FLANGE_BOLT_PITCH_INSUFFICIENT",
        "WEB_BOLT_PITCH_INSUFFICIENT",
        "FLANGE_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS",
        "WEB_CLEAR_BODY_BOUNDARIES_OVERLAP_OR_CROSS",
    } <= insufficient_reasons


def test_internal_exactness_guards_duplicate_scenarios_and_local_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = default_channel_moment_splice_request()
    original_demand = calculate_eccentric_bolt_group_demand

    def duplicate_scenarios(value: object) -> object:
        demand = original_demand(value)  # type: ignore[arg-type]
        return replace(demand, scenarios=demand.scenarios + demand.scenarios)

    monkeypatch.setattr(service, "calculate_eccentric_bolt_group_demand", duplicate_scenarios)
    assert service.preview_channel_moment_splice(base).design_check_ready
    monkeypatch.setattr(service, "calculate_eccentric_bolt_group_demand", original_demand)
    monkeypatch.setattr(
        service,
        "evaluate_multirow_connection_with_resolved_demand",
        lambda *_args: (_ for _ in ()).throw(ValueError("controlled local handoff unavailable")),
    )
    design = service.design_check_channel_moment_splice(base)
    assert any(
        "LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE" in warning
        for item in design.local_checks
        for warning in item.warnings
    )
    zero = replace(
        base,
        actions=ChannelMomentSpliceActions(
            q(0, Unit.KIP),
            q(0, Unit.KIP),
            q(0, Unit.KIP_IN),
            q(0, Unit.KIP),
            q(0, Unit.KIP_IN),
            q(0, Unit.KIP_IN),
        ),
    )
    assert all(
        item.not_required_zero_force
        for item in service.design_check_channel_moment_splice(zero).local_checks
    )


def test_preview_exactness_guards_are_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    base = default_channel_moment_splice_request()
    original_slice = service._slice6
    original_equilibrium = service._equilibrium

    def nonexact_slice(request: ChannelMomentSpliceRequest) -> object:
        result = original_slice(request)
        return replace(
            result, equilibrium=replace(result.equilibrium, axial_equilibrium_exact=False)
        )

    monkeypatch.setattr(service, "_slice6", nonexact_slice)
    with pytest.raises(ValueError, match="SLICE6_EXACT"):
        service.preview_channel_moment_splice(base)
    monkeypatch.setattr(service, "_slice6", original_slice)

    def nonexact_connection(*args: object, **kwargs: object) -> object:
        result = original_equilibrium(*args, **kwargs)  # type: ignore[arg-type]
        return replace(result, whole_connection_six_component_exact=False)

    monkeypatch.setattr(service, "_equilibrium", nonexact_connection)
    with pytest.raises(ValueError, match="WHOLE_CONNECTION"):
        service.preview_channel_moment_splice(base)
    with pytest.raises(TypeError, match="ChannelMomentSpliceRequest"):
        service.preview_channel_moment_splice(object())  # type: ignore[arg-type]


def test_invalid_inner_width_and_web_plate_overlap_fail_closed() -> None:
    base = default_channel_moment_splice_request()
    invalid_inner = replace(
        base,
        flange_geometry=replace(base.flange_geometry, inner_plate_width=q("3.1", Unit.IN)),
    )
    invalid_web = replace(
        base,
        web_splice_plate=replace(base.web_splice_plate, height=q("6.1", Unit.IN)),
    )
    assert (
        "INNER_FLANGE_PLATE_MUST_NOT_OVERLAP_WEB"
        in service.preview_channel_moment_splice(invalid_inner).geometry_invalid_reasons
    )
    preview = service.preview_channel_moment_splice(invalid_web)
    assert "WEB_PLATE_MUST_CLEAR_INNER_FLANGE_PLATES" in preview.geometry_invalid_reasons
    assert (
        service.design_check_channel_moment_splice(invalid_web).assembly_status
        is ChannelMomentSpliceStatus.INVALID_GEOMETRY
    )


def test_us_si_equivalence_and_presentation_exclusion() -> None:
    us = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    si = service.preview_channel_moment_splice(
        default_channel_moment_splice_request(EngineeringUnitSystem.SI)
    )
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.geometry_fingerprint == si.geometry_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert us.application_fingerprint == si.application_fingerprint
    assert us.slice6_result.result_fingerprint == si.slice6_result.result_fingerprint
    display_only = replace(
        default_channel_moment_splice_request(),
        beam=replace(
            default_channel_moment_splice_request().beam,
            display_length_each_side=q(24, Unit.IN),
        ),
    )
    changed = service.preview_channel_moment_splice(display_only)
    assert changed.slice6_result.result_fingerprint == us.slice6_result.result_fingerprint
    assert changed.geometry_fingerprint == us.geometry_fingerprint
    assert changed.engineering_fingerprint == us.engineering_fingerprint
    assert changed.application_fingerprint != us.application_fingerprint


def test_preview_is_resistance_free_and_design_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service,
        "evaluate_flange_plate_body",
        lambda **_kwargs: pytest.fail("preview evaluated resistance"),
    )
    monkeypatch.setattr(
        service,
        "evaluate_channel_two_plane_bolt",
        lambda **_kwargs: pytest.fail("preview evaluated bolt resistance"),
    )
    result = service.preview_channel_moment_splice(default_channel_moment_splice_request())
    assert not result.resistance_evaluated
    assert result.design_check_ready


def test_design_precedence_disclaimer_and_serialization() -> None:
    design = service.design_check_channel_moment_splice(default_channel_moment_splice_request())
    assert design.assembly_status in {
        ChannelMomentSpliceStatus.FAIL,
        ChannelMomentSpliceStatus.NOT_EVALUATED,
    }
    assert not design.ordinary_pass_allowed
    assert design.rational_method_engineering_review_required
    assert design.disclaimer_id == (
        "CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1"
    )
    assert design.preview.connection_element_qualification == "REQUIRED_2_3_2"
    assert design.preview.warping_connection_response == "NOT_EVALUATED"
    preview_dto = serialize_channel_moment_splice_preview(design.preview)
    design_dto = serialize_channel_moment_splice_design(design)
    assert preview_dto.result["engineering_fingerprint"] == design.preview.engineering_fingerprint
    assert design_dto.result["result_fingerprint"] == design.result_fingerprint


def test_dto_api_openapi_and_http_status_boundary() -> None:
    dto = ChannelMomentSpliceRequestDTO.model_validate(_dto_payload())
    assert map_channel_moment_splice_request(dto) == default_channel_moment_splice_request()
    preview = _post("/api/v1/calculations/channel-major-axis-moment-splice/preview", _dto_payload())
    assert preview.status_code == 200
    assert preview.json()["resistance_evaluated"] is False
    design = _post(
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check", _dto_payload()
    )
    assert design.status_code == 200
    assert design.json()["ordinary_pass_allowed"] is False
    invalid = _dto_payload()
    invalid["request_id"] = " "
    assert (
        _post("/api/v1/calculations/channel-major-axis-moment-splice/preview", invalid).status_code
        == 422
    )
    schema = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST)).openapi()
    for path in (
        "/api/v1/calculations/channel-major-axis-moment-splice/preview",
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check",
    ):
        assert path in schema["paths"]
        assert "post" in schema["paths"][path]


def test_preview_and_design_mapping_failures_are_safe_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_mapping(_request: object) -> object:
        raise ValueError("controlled Channel mapping rejection")

    monkeypatch.setattr(routes_module, "map_channel_moment_splice_request", reject_mapping)
    for path in (
        "/api/v1/calculations/channel-major-axis-moment-splice/preview",
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check",
    ):
        response = _post(path, _dto_payload())
        assert response.status_code == 422
        assert response.json()["detail"] == {
            "code": "CANONICAL_CHANNEL_MOMENT_SPLICE_MAPPING_INVALID",
            "message": "controlled Channel mapping rejection",
        }
        assert "Traceback" not in response.text
        assert "C:\\" not in response.text
