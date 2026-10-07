"""Independent F7 physical paths, native arithmetic, boundaries and report contracts."""

from __future__ import annotations

import io
from copy import deepcopy
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Any, Literal, cast
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from tests.api.test_appendix_rc3_direct_parity import BASELINE
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design, supported

from frp_master_connection.application import multirow_orchestration as service
from frp_master_connection.application.direct_angle_block import (
    HEEL_REASON,
    DirectAngleBlockResult,
    evaluate_direct_angle_block,
)
from frp_master_connection.application.direct_engineering_geometry import DirectEngineeringFace
from frp_master_connection.application.visualization import SingleBoltVisualizationSnapshot
from frp_master_connection.calculation import (
    RESISTANCE_HANDOFF_DECIMAL_PRECISION,
    EccentricResistanceHandoffInput,
    EndUseFactors,
    MaterialDirection,
    MultiRowOverallDisposition,
    PhysicalQuantity,
    StandardHoleDefinition,
    Unit,
)
from frp_master_connection.geometry import MultiRowGeometry
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.reader_data import collect_checks
from frp_master_connection.reporting.snapshot import SnapshotSigner

FREE = "BLOCK_SHEAR:layer-A:BLOCK_L_LEFT_ROW_1_BOLT_LINE_1"
HEEL = "BLOCK_SHEAR:layer-A:BLOCK_L_RIGHT_ROW_1_BOLT_LINE_1"


def block_result(result: dict[str, Any]) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        result["native_design"]["automatic_group_mode_integration"]["direct_angle_block_results"][
            0
        ],
    )


@dataclass(frozen=True)
class Context:
    value: EccentricResistanceHandoffInput
    geometry: MultiRowGeometry
    scene: SingleBoltVisualizationSnapshot
    faces: tuple[DirectEngineeringFace, ...]
    hole: StandardHoleDefinition
    integration: service.DirectLayeredGroupModeIntegrationResult | None = None

    def evaluate(self) -> DirectAngleBlockResult:
        return evaluate_direct_angle_block(
            self.value, self.geometry, self.scene, self.faces, self.hole
        )


@pytest.fixture(scope="module")
def context() -> Context:
    captures = []
    originals = []

    def capture(
        value: EccentricResistanceHandoffInput,
        geometry: MultiRowGeometry,
        scene: SingleBoltVisualizationSnapshot,
        faces: tuple[DirectEngineeringFace, ...],
        hole: StandardHoleDefinition,
    ) -> DirectAngleBlockResult:
        captures.append(Context(value, geometry, scene, faces, hole))
        return evaluate_direct_angle_block(value, geometry, scene, faces, hole)

    # Capture the pre-F7 typed integration without modifying any engine result.
    original_integrate = service._integrate_direct_angle_block

    def integrate(
        original: service.DirectLayeredGroupModeIntegrationResult,
        blocks: tuple[DirectAngleBlockResult, ...],
    ) -> service.DirectLayeredGroupModeIntegrationResult:
        originals.append(original)
        return original_integrate(original, blocks)

    with (
        patch.object(service, "evaluate_direct_angle_block", capture),
        patch.object(service, "_integrate_direct_angle_block", integrate),
    ):
        design(BASELINE["request"])
    assert len(captures) == 1
    return replace(captures[0], integration=originals[0])


def magnitude(quantity: dict[str, Any], unit: Unit) -> Decimal:
    return PhysicalQuantity.of(quantity["value"], Unit(quantity["unit"])).to(unit).magnitude


def test_owner_physical_polygon_areas_equation_demand_and_seven_exact() -> None:
    result = design(BASELINE["request"])
    block = block_result(result)
    path = block["path"]
    assert [(Decimal(x), Decimal(y)) for x, y in path["polygon"]] == [
        (Decimal(0), Decimal(".2500000000000002")),
        (Decimal(5), Decimal(".2500000000000002")),
        (Decimal(5), Decimal(2)),
        (Decimal(0), Decimal(2)),
    ]
    area = path["area_plan"]
    assert magnitude(area["gross_shear_length"], Unit.IN) == 5
    assert magnitude(area["net_shear_area"], Unit.IN2) == Decimal("2.0305")
    assert abs(magnitude(area["net_tension_area"], Unit.IN2) - Decimal(".7185")) < Decimal("1e-14")
    check = block["supported_results"][0]
    assert check["result_id"] == FREE
    assert block["method_id"] == "ASCE_8_14B_DIRECT_PHYSICAL_L_PATH_RATIONAL"
    assert check["equation_trace"]["equation"] == "ASCE_EQ_8_14B"
    assert abs(
        magnitude(check["equation_nominal_resistance"], Unit.KIP) - Decimal("13.51075")
    ) < Decimal("1e-13")
    assert abs(magnitude(check["design_resistance"], Unit.KIP) - Decimal("3.6479025")) < Decimal(
        "1e-13"
    )
    assert abs(magnitude(check["demand"], Unit.KIP) - Decimal(".7")) < Decimal("1e-14")
    assert check["numerical_comparison"] == "PASS"
    assert [c for c in supported(result) if c["limit_state"] != "BLOCK_SHEAR"] == BASELINE[
        "expected"
    ]["checks"]
    i = result["native_design"]["automatic_group_mode_integration"]
    assert len(supported(result)) == 8
    assert len(i["required_check_ids"]) == 17
    assert len(i["unsupported_required_check_ids"]) == 5
    assert len(i["incomplete_required_check_ids"]) == 1
    assert len(i["not_required_check_ids"]) == 3
    assert "FIRST_ROW:layer-A" in i["unsupported_required_check_ids"]
    assert "FIRST_ROW:layer-B" in i["unsupported_required_check_ids"]
    assert "INTERROW:layer-B:BOLT_LINE_1" in i["unsupported_required_check_ids"]
    assert all(
        c["layer_id"] != "layer-B" for c in supported(result) if c["limit_state"] == "BLOCK_SHEAR"
    )
    assert i["qualification"] == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    assert i["incomplete_required_check_ids"] == [
        "DIRECT_WHOLE_CONNECTION_SECTION_2_3_2_QUALIFICATION"
    ]
    assert result["overall_status"] != "PASS"


def test_heel_na_requires_real_continuity_and_has_no_numerical_fields(context: Context) -> None:
    block = context.evaluate()
    assert block.path
    assert block.path.heel_continuity_proven
    assert {p.physical_element_id for p in block.path.continuity_geometry} == {
        "LEG_1",
        "LEG_2",
        None,
    }
    row = block.history_results[0]
    assert row.result_id == HEEL
    assert row.availability.value == "NOT_APPLICABLE"
    assert row.numerical_comparison.value == "NOT_EVALUATED"
    assert row.demand is row.design_resistance is row.utilization is None
    assert row.reason == HEEL_REASON
    assert "whole-connection qualification" in row.reason


@pytest.mark.parametrize(
    "case", ["owner-135", "control-45", "finite-w", "three-row", "zero-eccentricity", "si-owner"]
)
def test_physical_controls_execute_own_path_and_never_activate_first_row(case: str) -> None:
    result = design(f6_cases()[case])
    block = block_result(result)
    assert block["supported_results"][0]["result_id"] == FREE
    assert block["history_results"][0]["result_id"] == HEEL
    assert not any(
        c["limit_state"] == "FIRST_ROW_NET_TENSION" or "RC3" in str(c) for c in supported(result)
    )
    if case == "zero-eccentricity":
        assert block["eccentricity"]["signed_eccentricity"]["canonical_value"] == "0"
        assert block["method_id"] == "ASCE_8_14A_DIRECT_PHYSICAL_L_PATH_RATIONAL"
    if case == "three-row":
        plan = block["path"]["area_plan"]
        assert magnitude(plan["gross_shear_length"], Unit.IN) == 7
        assert len(plan["deductions"]) == 4
        assert [d["fraction"] for d in plan["deductions"]] == ["1", "1", "0.5", "0.5"]


def test_finite_w_changes_no_angle_path_or_resistance() -> None:
    cases = f6_cases()
    a, b = [block_result(design(cases[c])) for c in ("owner-135", "finite-w")]
    assert a["path"] == b["path"]
    assert (
        a["supported_results"][0]["design_resistance"]
        == b["supported_results"][0]["design_resistance"]
    )


def test_us_si_same_physical_source_path_not_rounded_metric() -> None:
    cases = f6_cases()
    us, si = [block_result(design(cases[c])) for c in ("owner-135", "si-owner")]
    for key in ("net_shear_area", "net_tension_area", "gross_shear_area", "gross_tension_area"):
        assert abs(
            magnitude(us["path"]["area_plan"][key], Unit.MM2)
            - magnitude(si["path"]["area_plan"][key], Unit.MM2)
        ) < Decimal("1e-10")
    for key in ("demand", "design_resistance", "equation_nominal_resistance"):
        assert abs(
            magnitude(us["supported_results"][0][key], Unit.N)
            - magnitude(si["supported_results"][0][key], Unit.N)
        ) < Decimal("1e-8")
    assert us["method_id"] == si["method_id"]
    assert (
        us["supported_results"][0]["numerical_comparison"]
        == si["supported_results"][0]["numerical_comparison"]
    )


def test_block_fail_has_red_precedence_over_missing_qualification() -> None:
    body = deepcopy(BASELINE["request"])
    body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
        "force"
    ]["x"] = "4"
    result = design(body)
    i = result["native_design"]["automatic_group_mode_integration"]
    assert block_result(result)["supported_results"][0]["numerical_comparison"] == "FAIL"
    assert FREE in i["failed_check_ids"]
    assert i["overall_disposition"] == "FAIL"
    assert i["qualification"] == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    assert result["overall_status"] == "FAIL"


def test_half_shared_corner_and_full_interior_no_duplicate_holes(context: Context) -> None:
    block = context.evaluate()
    assert block.path
    deductions = block.path.area_plan.deductions
    assert [(d.bolt_id, d.plane.value, d.fraction) for d in deductions] == [
        ("B_R2_L1", "SHEAR", Decimal(1)),
        ("B_R1_L1", "SHEAR", Decimal(".5")),
        ("B_R1_L1", "TENSION", Decimal(".5")),
    ]
    assert all(
        d.net_area_hole_diameter.to(Unit.IN).magnitude == Decimal(".626") for d in deductions
    )
    assert sum(d.fraction for d in deductions if d.bolt_id == "B_R1_L1") == 1
    assert {d.bolt_id for d in deductions} == {f.bolt_id for f in block.path.raw_faces}


@pytest.mark.parametrize("lap", [Decimal(".6"), Decimal(1)])
@pytest.mark.parametrize("factor", [Decimal(1), Decimal(".8")])
def test_lap_environment_time_pitch_exact_once(
    context: Context, lap: Decimal, factor: Decimal
) -> None:
    value = context.value
    layers = tuple(
        replace(
            layer,
            end_use_factors=EndUseFactors(factor, factor, factor, "F7 independent QA", ("QA",)),
        )
        for layer in value.execution_bundle.layers
    )
    factors = replace(
        value.execution_bundle.factors,
        lap_factor_c_lap=lap,
        time_effect_factor_lambda=factor,
        pitch_factor_c_delta=factor,
    )
    result = replace(
        context,
        value=replace(
            value, execution_bundle=replace(value.execution_bundle, layers=layers, factors=factors)
        ),
    ).evaluate()
    base = context.evaluate().supported_results[0]
    calculated = result.supported_results[0]
    with localcontext() as ctx:
        ctx.prec = 60
        expected = (
            base.design_resistance.canonical_magnitude / Decimal(".6") * lap * factor**5
            if base.design_resistance
            else None
        )
    assert calculated.design_resistance
    assert expected is not None
    assert abs(calculated.design_resistance.canonical_magnitude - expected) < Decimal("1e-20")


@pytest.mark.parametrize("multiple", [Decimal(".999999"), Decimal(1), Decimal("1.000001")])
def test_actual_eccentricity_boundary_not_display_rounding(
    context: Context, multiple: Decimal
) -> None:
    value = context.value
    assert value.execution_bundle.eccentricity
    e = value.execution_bundle.eccentricity.tolerance.canonical_magnitude * multiple
    moment = PhysicalQuantity.of(
        -e * value.demand_result.projected_force.u.canonical_magnitude, Unit.N_MM
    )
    demand = replace(
        value.demand_result,
        scenarios=tuple(
            replace(s, external_moment=moment, residual_moment=moment)
            for s in value.demand_result.scenarios
        ),
    )
    block = replace(context, value=replace(value, demand_result=demand)).evaluate()
    assert block.eccentricity
    assert block.eccentricity.classification.value == (
        "CONCENTRIC" if multiple <= 1 else "ECCENTRIC"
    )


@pytest.mark.parametrize("kind", ["force", "axis", "direction", "missing-eccentricity"])
def test_source_direction_and_missing_reference_fail_without_rotating_properties(
    context: Context, kind: str
) -> None:
    value = context.value
    if kind == "force":
        value = replace(
            value,
            demand_result=replace(
                value.demand_result,
                projected_force=replace(
                    value.demand_result.projected_force, v=PhysicalQuantity.of(".001", Unit.N)
                ),
            ),
        )
    elif kind == "axis":
        value = replace(
            value,
            layer_axes=(
                replace(value.layer_axes[0], lw_axis=(Decimal(0), Decimal(1))),
                *value.layer_axes[1:],
            ),
        )
    elif kind == "direction":
        value = replace(
            value,
            execution_bundle=replace(
                value.execution_bundle,
                layers=(
                    replace(
                        value.execution_bundle.layers[0],
                        material_direction=MaterialDirection.TRANSVERSE,
                    ),
                    *value.execution_bundle.layers[1:],
                ),
            ),
        )
    else:
        value = replace(value, execution_bundle=replace(value.execution_bundle, eccentricity=None))
    block = replace(context, value=value).evaluate()
    assert not block.supported_results
    assert block.reason


@pytest.mark.parametrize(
    "kind",
    [
        "one-row",
        "multiple-lines",
        "missing-face",
        "wrong-leg",
        "nonclosing",
        "thickness",
        "computational",
    ],
)
def test_unproved_physical_path_cannot_execute(context: Context, kind: str) -> None:
    c = context
    if kind == "one-row":
        c = replace(c, geometry=replace(c.geometry, rows=c.geometry.rows[:1]))
    elif kind == "multiple-lines":
        c = replace(c, geometry=replace(c.geometry, bolt_lines=c.geometry.bolt_lines * 2))
    elif kind == "missing-face":
        c = replace(c, faces=c.faces[1:])
    elif kind == "wrong-leg":
        c = replace(
            c,
            faces=tuple(
                replace(f, physical_element_id="WEB") if f.component_id == "member-a" else f
                for f in c.faces
            ),
        )
    elif kind == "nonclosing":
        c = replace(
            c,
            faces=tuple(
                replace(f, bolt_center_member_local=(-1, *f.bolt_center_member_local[1:]))
                if f.component_id == "member-a"
                else f
                for f in c.faces
            ),
        )
    elif kind == "thickness":
        c = replace(
            c,
            value=replace(
                c.value,
                execution_bundle=replace(
                    c.value.execution_bundle,
                    layers=(
                        replace(
                            c.value.execution_bundle.layers[0],
                            thickness=PhysicalQuantity.of(".6", Unit.IN),
                        ),
                        *c.value.execution_bundle.layers[1:],
                    ),
                ),
            ),
        )
    else:
        c = replace(
            c,
            faces=tuple(
                replace(
                    f,
                    boundaries=tuple(
                        replace(b, computational_only=True)
                        if b.role == "PHYSICAL_FREE_SIDE_EDGE"
                        else b
                        for b in f.boundaries
                    ),
                )
                for f in c.faces
            ),
        )
    assert not c.evaluate().supported_results
    assert c.evaluate().path is None


@pytest.mark.parametrize("kind", ["missing", "detached"])
def test_no_heel_na_without_geometry_continuity(context: Context, kind: str) -> None:
    scene = context.scene
    if kind == "missing":
        scene = replace(
            scene, primitives=tuple(p for p in scene.primitives if p.label != "Angle heel")
        )
    else:
        scene = replace(
            scene,
            primitives=tuple(
                replace(
                    p,
                    parameters=tuple(
                        replace(v, value=v.value + 1) if v.name == "min_z" else v
                        for v in p.parameters
                    ),
                )
                if p.physical_element_id == "LEG_2"
                else p
                for p in scene.primitives
            ),
        )
    block = replace(context, scene=scene).evaluate()
    assert block.path
    assert not block.path.heel_continuity_proven
    assert not block.history_results


@pytest.mark.parametrize(
    "side", [Decimal("1.251999"), Decimal("1.252"), Decimal("1.252001"), Decimal(".2")]
)
def test_raw_net_area_boundary_and_nonpositive_area(context: Context, side: Decimal) -> None:
    y = float(Decimal(2) - side)
    c = replace(
        context,
        faces=tuple(
            replace(
                f,
                bolt_center_member_local=(
                    f.bolt_center_member_local[0],
                    y,
                    f.bolt_center_member_local[2],
                ),
            )
            if f.component_id == "member-a"
            else f
            for f in context.faces
        ),
    )
    block = c.evaluate()
    assert block.path
    assert context.integration
    integrated = service._integrate_direct_angle_block(context.integration, (block,))
    ratio = block.path.area_plan.tension_net_to_gross
    if side == Decimal(".2"):
        assert not block.supported_results
        assert block.handoff
        assert block.handoff.overall_disposition is MultiRowOverallDisposition.INVALID_GEOMETRY
        assert integrated.overall_disposition is MultiRowOverallDisposition.INVALID_GEOMETRY
    else:
        assert block.supported_results
        assert ratio is not None
        assert block.code_geometry_satisfied is (side >= Decimal("1.252"))
        assert (ratio < Decimal(".75")) is (side < Decimal("1.252"))
        if side < Decimal("1.252"):
            assert "ordinary compliant PASS prohibited" in block.reason
            assert (
                integrated.overall_disposition
                is MultiRowOverallDisposition.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
            )


@pytest.mark.parametrize(
    "multiple", [Decimal(".999999999999"), Decimal(1), Decimal("1.000000000001")]
)
def test_block_numerical_unity_boundary_uses_exact_frozen_comparison(
    context: Context, multiple: Decimal
) -> None:
    base = context.evaluate().supported_results[0]
    assert base.design_resistance
    with localcontext() as precision:
        precision.prec = RESISTANCE_HANDOFF_DECIMAL_PRECISION
        quantity = base.design_resistance * multiple
    bundle = replace(
        context.value.execution_bundle,
        signed_demand=replace(
            context.value.execution_bundle.signed_demand, in_plane_magnitude=quantity
        ),
    )
    block = replace(context, value=replace(context.value, execution_bundle=bundle)).evaluate()
    check = block.supported_results[0]
    assert check.utilization == multiple
    assert check.numerical_comparison.value == ("PASS" if multiple <= 1 else "FAIL")
    # Isolate the new block from all seven existing PASS records, proving
    # that missing qualification cannot mask this block's independent FAIL.
    assert context.integration
    assert not context.integration.failed_check_ids
    integrated = service._integrate_direct_angle_block(context.integration, (block,))
    assert integrated.qualification.value == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    if multiple > 1:
        assert integrated.failed_check_ids == (FREE,)
        assert integrated.overall_disposition.value == "FAIL"
    else:
        assert not integrated.failed_check_ids
        assert integrated.overall_disposition.value != "PASS"


def test_missing_physical_scene_cannot_activate_block_or_heel_na() -> None:
    from frp_master_connection.api.multirow_mapping import map_multirow_request
    from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO

    request = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(BASELINE["request"]["legacy_request"])
    )
    resolved = service._resolve(request)
    preview = service.preview_multirow_connection(request)
    without_scene = replace(
        resolved, visualization=replace(resolved.visualization, physical_connection=None)
    )
    with (
        patch.object(service, "_resolve", return_value=without_scene),
        patch.object(service, "_preview_from_resolved", return_value=preview),
    ):
        result = service.evaluate_multirow_connection(request)
    integration = cast(
        service.DirectLayeredGroupModeIntegrationResult,
        result.automatic_group_mode_integration,
    )
    assert integration.direct_angle_block_results == ()
    assert FREE in integration.unsupported_required_check_ids
    assert HEEL in integration.unsupported_required_check_ids
    assert integration.overall_disposition.value != "PASS"


def test_aggregate_governing_changes_only_when_new_block_governs(context: Context) -> None:
    assert context.integration
    original = context.integration
    block = context.evaluate()
    baseline = service._integrate_direct_angle_block(original, (block,))
    assert baseline.governing_supported_check_ids == original.governing_supported_check_ids
    unavailable = replace(block, supported_results=())
    unchanged = service._integrate_direct_angle_block(original, (unavailable,))
    assert unchanged.governing_supported_check_ids == original.governing_supported_check_ids
    maximum = max(
        c.utilization
        for scenario in original.scenario_results
        for c in scenario.supported_results
        if c.utilization is not None
    )
    tied = replace(
        block, supported_results=(replace(block.supported_results[0], utilization=maximum),)
    )
    assert service._integrate_direct_angle_block(
        original, (tied,)
    ).governing_supported_check_ids == (*original.governing_supported_check_ids, FREE)
    empty = replace(
        original,
        scenario_results=tuple(
            replace(s, supported_results=(), governing_supported_check_ids=())
            for s in original.scenario_results
        ),
        governing_supported_check_ids=(),
    )
    assert service._integrate_direct_angle_block(empty, (block,)).governing_supported_check_ids == (
        FREE,
    )


def test_legacy_nonrecord_history_is_ignored_without_changing_final_checks() -> None:
    native = design(BASELINE["request"])["native_design"]
    expected = collect_checks(native)
    original = deepcopy(native)
    native["automatic_group_mode_integration"]["direct_angle_block_results"].append(None)
    assert collect_checks(native) == expected
    native["automatic_group_mode_integration"]["direct_angle_block_results"].pop()
    assert native == original


def test_one_row_orchestration_retains_source_scope_without_new_multirow_block() -> None:
    from tests.api.test_asce_shape_f5 import f5_body

    result = design(f5_body(row_count=1))
    assert (
        result["native_design"]["automatic_group_mode_integration"]["direct_angle_block_results"]
        == []
    )
    assert not any(c["limit_state"] == "BLOCK_SHEAR" for c in supported(result))


@pytest.mark.parametrize(
    ("case", "mode"),
    [
        ("owner-135", "ENGINEER_REPORT"),
        ("owner-135", "FULL_TECHNICAL_AUDIT"),
        ("zero-eccentricity", "ENGINEER_REPORT"),
        ("zero-eccentricity", "FULL_TECHNICAL_AUDIT"),
        ("control-45", "ENGINEER_REPORT"),
        ("si-owner", "ENGINEER_REPORT"),
        ("raw75", "ENGINEER_REPORT"),
        ("block-red", "ENGINEER_REPORT"),
    ],
)
def test_real_pdf_native_calculation_heel_reason_qualification_and_snapshot_immutable(
    case: str, mode: Literal["ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"]
) -> None:
    body = deepcopy(BASELINE["request"]) if case in {"raw75", "block-red"} else f6_cases()[case]
    if case == "raw75":
        body["legacy_request"]["physical_connection"]["joint_assembly"]["members"][0]["section"][
            "leg_y"
        ]["value"] = "3"
    if case == "block-red":
        body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
            "force"
        ]["x"] = "4"
    result = design(body)
    signer = SnapshotSigner(b"F7-INDEPENDENT-PDF-SNAPSHOT-TEST-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f7"
        ),
        account_id="f7",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    options = ReportOptions(mode=mode)
    pdf = render_report_pdf(snapshot, options)
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "8 supported checks evaluated" in text
    assert "6 required checks/evidence items unresolved" in text
    assert "Angle heel side: NOT APPLICABLE" in text
    assert "perpendicular leg remains continuous" in text
    assert "Section 2.3.2" in text
    assert block_result(result)["method_id"] in text
    assert "FSH_LT: CM=1, CT=1, CCH=1" in text
    assert "FT_L: CM=1, CT=1, CCH=1" in text
    assert (snapshot.request, snapshot.result) == before
    checks = collect_checks(result["native_design"])
    heel = next(c for c in checks if c.identity == HEEL)
    assert heel.availability == "NOT_APPLICABLE"
    assert not heel.required
    assert heel.utilization is None
    assert heel.demand is None
    assert heel.resistance is None
