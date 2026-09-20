"""Stage 2.6A RC1 eccentric group-mode compatibility verification."""

import hashlib
from dataclasses import FrozenInstanceError, replace
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import cast

import pytest

import frp_master_connection.calculation.eccentric_group_modes as group_module
from frp_master_connection.calculation import (
    ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION,
    ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION,
    ECCENTRIC_GROUP_MODE_ENGINE_VERSION,
    ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION,
    ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION,
    ECCENTRIC_GROUP_MODE_RULE_SET_VERSION,
    RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF,
    DemandAnalysisAvailability,
    EccentricFirstRowCompatibility,
    EccentricFirstRowHandoffStatus,
    EccentricGroupModeCompatibilityInput,
    EccentricGroupModeFingerprintEnvelope,
    EccentricGroupModeTraceStage,
    EccentricGroupModeVersionContext,
    EccentricGroupModeWarning,
    EccentricGroupModeWarningCode,
    EccentricLineBoltVector,
    EccentricLineHandoffStatus,
    ExactQuantityVector3D,
    FRPPropertyKind,
    GeometryStatus,
    InPlaneQuantityVector,
    InterrowShearOutMethod,
    MultiRowCheckFamily,
    MultiRowCheckResult,
    MultiRowEquationMethod,
    MultiRowExecutionBundle,
    MultiRowMethodApplicability,
    MultiRowOverallDisposition,
    MultiRowRequiredCheckContract,
    MultiRowResultAvailability,
    NumericalComparison,
    PhysicalQuantity,
    PlanAvailability,
    QualificationDisposition,
    Unit,
    calculate_eccentric_bolt_group_demand,
    calculate_eccentric_group_mode_compatibility,
    calculate_eccentric_resistance_handoff,
    canonical_eccentric_group_mode_input_json,
    eccentric_group_mode_input_fingerprint,
)
from tests.calculation.golden_loader import (
    FrozenJson,
    decimal_strings,
    load_slice_3_eccentric_group_modes_rc1_golden_fixture,
)
from tests.calculation.test_multirow_engine import _bundle, _check
from tests.calculation.test_resistance_handoff import (
    _demand_input,
    _handoff_input,
    _scaled_bundle,
)

SPECIFICATION_PATH = (
    Path(__file__).parents[3]
    / "docs"
    / "engineering"
    / "CALCULATION_SLICE_3_ECCENTRIC_GROUP_MODES_ENGINEERING_SPECIFICATION_RC1.md"
)
LEDGER_PATH = (
    Path(__file__).parents[3]
    / "docs"
    / "qa"
    / "CALCULATION_SLICE_3_ECCENTRIC_GROUP_MODES_RC1_INDEPENDENT_VERIFICATION_LEDGER.md"
)
GOLDEN_PATH = (
    Path(__file__).parents[1] / "golden" / "calculation_slice_3_eccentric_group_modes_rc1.json"
)


def _mapping(value: FrozenJson) -> MappingProxyType[str, FrozenJson]:
    return cast(MappingProxyType[str, FrozenJson], value)


def _tuple(value: FrozenJson) -> tuple[FrozenJson, ...]:
    return cast(tuple[FrozenJson, ...], value)


def _serialized(value: PhysicalQuantity, unit: Unit) -> str:
    return format(
        value.to(unit).magnitude.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN),
        ".12f",
    )


def _decimal_serialized(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN), ".12f")


def _with_golden_shear_strength(bundle: MultiRowExecutionBundle) -> MultiRowExecutionBundle:
    actual = bundle
    layers = tuple(
        replace(
            layer,
            material=replace(
                layer.material,
                properties=tuple(
                    replace(item, value=PhysicalQuantity.of("8", Unit.KSI))
                    if item.kind is FRPPropertyKind.FSH_LT
                    else item
                    for item in layer.material.properties
                ),
            ),
        )
        for layer in actual.layers
    )
    e1 = PhysicalQuantity.of("1.25", Unit.IN)
    plans = tuple(replace(item, e1=e1) for item in actual.planning_root.interrow_shear_out)
    plan_by_id = {item.id: item for item in plans}
    checks = tuple(
        replace(item, interrow_plan=plan_by_id[item.source_plan_id])
        if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
        else item
        for item in actual.checks
    )
    row_1_to_unloaded = e1
    for pitch in actual.end_distances.physical_pitches:
        row_1_to_unloaded += pitch
    return replace(
        actual,
        physical_geometry=replace(actual.physical_geometry, unloaded_free_end_u=Decimal("-1.25")),
        planning_root=replace(actual.planning_root, interrow_shear_out=plans),
        end_distances=replace(
            actual.end_distances,
            unloaded_end_e1=e1,
            row_1_to_unloaded_end_distance=row_1_to_unloaded,
        ),
        layers=layers,
        checks=checks,
    )


def _group_input(
    *,
    total: str = "3",
    offset_v: str = "0.1",
    force_u: str | None = None,
    force_v: str = "0",
    member_moment: str = "0",
    bundle: MultiRowExecutionBundle | None = None,
) -> EccentricGroupModeCompatibilityInput:
    actual_bundle = _with_golden_shear_strength(_scaled_bundle(total) if bundle is None else bundle)
    handoff_input = _handoff_input(
        total=total,
        offset_v=offset_v,
        member_moment=member_moment,
        bundle=actual_bundle,
    )
    if force_u is not None or force_v != "0":
        demand_input = _demand_input(
            actual_bundle,
            total=total,
            offset_v=offset_v,
            member_moment=member_moment,
        )
        demand_input = replace(
            demand_input,
            global_force=ExactQuantityVector3D(
                PhysicalQuantity.of(total if force_u is None else force_u, Unit.KIP),
                PhysicalQuantity.of(force_v, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP),
            ),
        )
        handoff_input = replace(
            handoff_input,
            demand_result=calculate_eccentric_bolt_group_demand(demand_input),
        )
    handoff_result = calculate_eccentric_resistance_handoff(handoff_input)
    return EccentricGroupModeCompatibilityInput(
        handoff_input,
        handoff_result,
        (
            "DEMAND_ANALYSIS",
            "RESISTANCE_HANDOFF",
            "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
            "RESISTANCE_CALCULATION",
        ),
    )


def _group_only_bundle(rows: tuple[float, ...]) -> MultiRowExecutionBundle:
    base = _bundle(rows=rows, checks=(), required_ids=())
    first_plan = (
        base.planning_root.first_row_net_tension[2]
        if len(rows) > 3
        else base.planning_root.first_row_net_tension[0]
    )
    first = _check(
        "first-row",
        MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
        MultiRowEquationMethod.FIRST_ROW_RATIONAL_LOWER_ENVELOPE
        if len(rows) > 3
        else MultiRowEquationMethod.FIRST_ROW_SIMPLIFIED,
        demand="2",
        layer_id="LAYER-1",
        plan=first_plan,
        applicability=first_plan.method_applicability,
        qualification=first_plan.qualification,
    )
    method_by_plan = {
        InterrowShearOutMethod.ASCE_EQ_8_12: MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12,
        InterrowShearOutMethod.ASCE_EQ_8_13: MultiRowEquationMethod.INTERROW_ASCE_EQ_8_13,
        InterrowShearOutMethod.RATIONAL_EXTENSION_EQ_8_13: (
            MultiRowEquationMethod.INTERROW_RATIONAL_EXTENSION_EQ_8_13
        ),
    }
    interrow = tuple(
        _check(
            f"interrow:{index}",
            MultiRowCheckFamily.INTERROW_SHEAR_OUT,
            method_by_plan[plan.method],
            demand="1",
            layer_id="LAYER-1",
            bolt_line_id=plan.bolt_line_id,
            plan=plan,
            applicability=plan.method_applicability,
            qualification=plan.qualification,
        )
        for index, plan in enumerate(base.planning_root.interrow_shear_out, start=1)
    )
    checks = (first, *interrow)
    return replace(
        base,
        checks=checks,
        required_checks=MultiRowRequiredCheckContract(tuple(item.check_id for item in checks)),
    )


def _case(case_id: str) -> MappingProxyType[str, FrozenJson]:
    fixture = load_slice_3_eccentric_group_modes_rc1_golden_fixture()
    return next(
        _mapping(item) for item in _tuple(fixture["cases"]) if _mapping(item)["id"] == case_id
    )


def test_controlled_authority_hashes_schema_inventory_decimal_data_and_immutability() -> None:
    assert hashlib.sha256(SPECIFICATION_PATH.read_bytes()).hexdigest().upper() == (
        "CBC11F8793F7B85873DB5C52D7A90536DD20CB87005895EAF3B43D319AB1B5D6"
    )
    assert hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest().upper() == (
        "F1E306C7648510E87CD258D433C0FA85AF131EA504D4F04A1B39FA1C1DB530D9"
    )
    assert hashlib.sha256(LEDGER_PATH.read_bytes()).hexdigest().upper() == (
        "477D8F19C50B39ED10EEFE95A3C93F73897147BB456CF412350960C9C3D24E10"
    )
    fixture = load_slice_3_eccentric_group_modes_rc1_golden_fixture()
    assert fixture["schema_version"] == (
        "frp-master-connection-calculation-slice-3-eccentric-group-modes-golden-rc1"
    )
    assert tuple(_mapping(item)["id"] for item in _tuple(fixture["cases"])) == (
        "SMALL_ECCENTRIC_2X2_SHEAROUT_SUPPORTED",
        "LARGE_ECCENTRIC_2X2_SHEAROUT_REDISTRIBUTION_FAIL",
        "NONCOLLINEAR_BOLT_LINE_RESULTANT_UNSUPPORTED",
        "REVERSED_BOLT_LINE_RESULTANT_UNSUPPORTED",
        "ZERO_BOLT_LINE_RESULTANT_NOT_REQUIRED",
        "ZERO_RESIDUAL_FIRST_ROW_LEGACY_HANDOFF",
        "NONZERO_RESIDUAL_FIRST_ROW_GENERAL_CASE_UNSUPPORTED",
    )
    assert decimal_strings(fixture)
    with pytest.raises(TypeError):
        fixture["schema_version"] = "changed"  # type: ignore[index]


def test_small_eccentric_golden_uses_actual_vectors_and_existing_eq_8_12() -> None:
    value = _group_input()
    parent_input = value.parent_handoff_input
    parent_result = value.parent_handoff_result
    result = calculate_eccentric_group_mode_compatibility(value)
    expected = _case("SMALL_ECCENTRIC_2X2_SHEAROUT_SUPPORTED")
    expected_lines = _tuple(expected["bolt_line_results"])

    assert value.parent_handoff_input == parent_input
    assert value.parent_handoff_result == parent_result
    assert parent_input.demand_result.result_fingerprint == result.parent_demand_result_fingerprint
    assert parent_result.result_fingerprint == result.parent_handoff_result_fingerprint
    assert tuple(item.bolt_line_id for item in result.line_results) == (
        "BOLT_LINE_1",
        "BOLT_LINE_2",
    )
    for actual, expected_line in zip(result.line_results, expected_lines, strict=True):
        line = _mapping(expected_line)
        assert actual.contributing_bolt_ids == tuple(item.bolt_id for item in actual.bolt_vectors)
        assert actual.line_resultant.u == sum(
            (item.force.u for item in actual.bolt_vectors), PhysicalQuantity.of(0, Unit.N)
        )
        assert actual.line_resultant.v == sum(
            (item.force.v for item in actual.bolt_vectors), PhysicalQuantity.of(0, Unit.N)
        )
        assert _serialized(actual.line_resultant.u, Unit.KIP) == _tuple(line["resultant_kip"])[0]
        assert _serialized(actual.line_resultant.v, Unit.KIP) == _tuple(line["resultant_kip"])[1]
        assert _serialized(actual.parallel_scalar, Unit.KIP) == line["parallel_scalar_kip"]
        assert _serialized(actual.transverse_scalar, Unit.KIP) == line["transverse_scalar_kip"]
        assert actual.handoff_status.value == line["handoff"]
        assert (
            _serialized(cast(PhysicalQuantity, actual.required_line_demand), Unit.KIP)
            == (line["parallel_scalar_kip"])
        )
        resistance = cast(MultiRowCheckResult, actual.shear_out_result)
        assert resistance.equation_method is MultiRowEquationMethod.INTERROW_ASCE_EQ_8_12
        assert (
            _serialized(cast(PhysicalQuantity, resistance.design_resistance), Unit.KIP)
            == (line["design_resistance_kip"])
        )
        assert _decimal_serialized(cast(Decimal, resistance.utilization)) == line["utilization"]
    assert result.first_row_compatibility.status is (
        EccentricFirstRowHandoffStatus.CALCULATION_NOT_SUPPORTED
    )
    first_row_expected = _case("NONZERO_RESIDUAL_FIRST_ROW_GENERAL_CASE_UNSUPPORTED")
    assert (
        result.first_row_compatibility.status.value
        == first_row_expected["expected_first_row_handoff"]
    )
    assert first_row_expected["required_warning"] in {
        warning.code.value for warning in result.first_row_compatibility.warnings
    }
    assert result.unsupported_required_check_ids == ("first-row",)
    assert result.numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert result.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
    assert result.trace_stages == tuple(EccentricGroupModeTraceStage)


def test_large_eccentric_zero_line_and_supported_line_failure_preserve_precedence() -> None:
    result = calculate_eccentric_group_mode_compatibility(_group_input(total="10", offset_v="2"))
    expected = _case("LARGE_ECCENTRIC_2X2_SHEAROUT_REDISTRIBUTION_FAIL")
    expected_lines = _tuple(expected["bolt_line_results"])
    for actual, expected_line in zip(result.line_results, expected_lines, strict=True):
        line = _mapping(expected_line)
        assert _serialized(actual.line_resultant.u, Unit.KIP) == _tuple(line["resultant_kip"])[0]
        assert actual.handoff_status.value == line["handoff"]
        if actual.shear_out_result is None:
            assert actual.required_line_demand is None
        else:
            assert (
                _decimal_serialized(cast(Decimal, actual.shear_out_result.utilization))
                == (line["utilization"])
            )
    assert result.not_required_check_ids == ("interrow:1",)
    assert "interrow:2" in result.failed_check_ids
    assert result.numerical_comparison is NumericalComparison.FAIL
    assert result.overall_disposition is MultiRowOverallDisposition.FAIL
    assert result.governing_supported_check_ids


def test_nonparallel_and_reversed_actual_line_states_fail_closed_without_projection() -> None:
    nonparallel_expected = _case("NONCOLLINEAR_BOLT_LINE_RESULTANT_UNSUPPORTED")
    nonparallel = calculate_eccentric_group_mode_compatibility(
        _group_input(force_v="1", offset_v="0.1")
    )
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED
        and item.transverse_scalar.canonical_magnitude != 0
        and item.required_line_demand is None
        and item.shear_out_result is None
        for item in nonparallel.line_results
    )
    assert all(
        item.handoff_status.value == nonparallel_expected["expected_handoff"]
        for item in nonparallel.line_results
    )
    assert {warning.code for warning in nonparallel.warnings} >= {
        EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE
    }
    assert nonparallel_expected["warning"] in {
        warning.code.value for warning in nonparallel.warnings
    }

    tiny_transverse = calculate_eccentric_group_mode_compatibility(
        _group_input(force_v="1E-30", offset_v="0.1")
    )
    assert all(
        item.transverse_scalar.canonical_magnitude != 0
        and item.handoff_status is EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED
        for item in tiny_transverse.line_results
    )

    reversed_expected = _case("REVERSED_BOLT_LINE_RESULTANT_UNSUPPORTED")
    reversed_result = calculate_eccentric_group_mode_compatibility(
        _group_input(total="10", offset_v="3")
    )
    reversed_lines = tuple(
        item
        for item in reversed_result.line_results
        if item.parallel_scalar.canonical_magnitude < 0
    )
    assert len(reversed_lines) == 1
    assert reversed_lines[0].handoff_status.value == reversed_expected["expected_handoff"]
    assert reversed_lines[0].required_line_demand is None
    assert reversed_lines[0].warnings[0].code.value == reversed_expected["warning"]


def test_zero_residual_inherits_the_complete_legacy_stage_2_4b_path_exactly() -> None:
    value = _group_input(offset_v="0")
    result = calculate_eccentric_group_mode_compatibility(value)
    parent = value.parent_handoff_result
    expected = _case("ZERO_RESIDUAL_FIRST_ROW_LEGACY_HANDOFF")
    assert parent.legacy_result is not None
    assert result.first_row_compatibility.status.value == expected["expected_first_row_handoff"]
    assert all(
        item.handoff_status.value == expected["expected_shearout_handoff"]
        for item in result.line_results
    )
    assert result.supported_results == parent.supported_results
    assert result.numerical_comparison is parent.numerical_comparison
    assert result.overall_disposition is parent.overall_disposition
    assert not result.warnings


def test_parent_exemptions_are_preserved_and_can_permit_supported_pass() -> None:
    base = _with_golden_shear_strength(_scaled_bundle())
    required = tuple(
        item.check_id
        for item in base.checks
        if item.family is not MultiRowCheckFamily.FIRST_ROW_NET_TENSION
    )
    result = calculate_eccentric_group_mode_compatibility(
        _group_input(bundle=replace(base, required_checks=MultiRowRequiredCheckContract(required)))
    )
    assert result.first_row_compatibility == EccentricFirstRowCompatibility(
        EccentricFirstRowHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION, ()
    )
    assert not result.unsupported_required_check_ids
    assert result.numerical_comparison is NumericalComparison.PASS
    assert result.overall_disposition is MultiRowOverallDisposition.PASS

    no_required = calculate_eccentric_group_mode_compatibility(
        _group_input(bundle=replace(base, required_checks=MultiRowRequiredCheckContract(())))
    )
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION
        for item in no_required.line_results
    )
    assert no_required.numerical_comparison is NumericalComparison.NOT_EVALUATED
    assert no_required.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED


@pytest.mark.parametrize(
    ("rows", "method", "qualification"),
    [
        (
            (4.0, 2.0, 0.0),
            MultiRowEquationMethod.INTERROW_ASCE_EQ_8_13,
            QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE,
        ),
        (
            (6.0, 4.0, 2.0, 0.0),
            MultiRowEquationMethod.INTERROW_RATIONAL_EXTENSION_EQ_8_13,
            QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
    ],
)
def test_three_and_more_than_three_row_methods_reuse_existing_execution(
    rows: tuple[float, ...],
    method: MultiRowEquationMethod,
    qualification: QualificationDisposition,
) -> None:
    bundle = _group_only_bundle(rows)
    result = calculate_eccentric_group_mode_compatibility(
        _group_input(total="2", offset_v="0.1", bundle=bundle)
    )
    line_results = tuple(
        cast(MultiRowCheckResult, item.shear_out_result) for item in result.line_results
    )
    assert line_results
    assert all(item.equation_method is method for item in line_results)
    assert result.qualification is qualification
    if len(rows) > 3:
        assert result.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED
        assert all(
            item.method_applicability
            is MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
            for item in line_results
        )


def test_us_si_action_equivalence_repeatability_and_presentation_independence() -> None:
    us_value = _group_input()
    us_result = calculate_eccentric_group_mode_compatibility(us_value)
    demand_input = _demand_input(
        us_value.parent_handoff_input.execution_bundle,
        total="3",
        offset_v="0.1",
    )

    def converted(vector: ExactQuantityVector3D, unit: Unit) -> ExactQuantityVector3D:
        return ExactQuantityVector3D(vector.x.to(unit), vector.y.to(unit), vector.z.to(unit))

    si_demand_input = replace(
        demand_input,
        global_force=converted(demand_input.global_force, Unit.KN),
        member_end_moments=converted(demand_input.member_end_moments, Unit.KN_MM),
        independent_connection_moments=converted(
            demand_input.independent_connection_moments, Unit.KN_MM
        ),
        force_reference_point=converted(demand_input.force_reference_point, Unit.MM),
        interface_frame=replace(
            demand_input.interface_frame,
            origin=converted(demand_input.interface_frame.origin, Unit.MM),
        ),
    )
    si_parent_demand = calculate_eccentric_bolt_group_demand(si_demand_input)
    si_handoff_input = replace(
        us_value.parent_handoff_input,
        demand_result=si_parent_demand,
    )
    si_parent_handoff = calculate_eccentric_resistance_handoff(si_handoff_input)
    si_value = EccentricGroupModeCompatibilityInput(
        si_handoff_input, si_parent_handoff, us_value.source_trace
    )
    si_result = calculate_eccentric_group_mode_compatibility(si_value)
    assert tuple(item.line_resultant for item in si_result.line_results) == tuple(
        item.line_resultant for item in us_result.line_results
    )
    assert tuple(item.handoff_status for item in si_result.line_results) == tuple(
        item.handoff_status for item in us_result.line_results
    )
    assert tuple(item.shear_out_result for item in si_result.line_results) == tuple(
        item.shear_out_result for item in us_result.line_results
    )
    assert calculate_eccentric_group_mode_compatibility(us_value) == us_result
    assert eccentric_group_mode_input_fingerprint(
        EccentricGroupModeFingerprintEnvelope(
            us_value, "US", "3 decimals", {"camera": 1}, "BOLT", "later"
        )
    ) == eccentric_group_mode_input_fingerprint(
        EccentricGroupModeFingerprintEnvelope(
            us_value, "SI", "6 decimals", {"camera": 2}, "LINE", "now"
        )
    )


def test_positive_scaling_is_monotonic_and_force_reversal_is_deterministic() -> None:
    lower = calculate_eccentric_group_mode_compatibility(_group_input(total="3"))
    higher = calculate_eccentric_group_mode_compatibility(_group_input(total="4"))
    assert all(
        cast(Decimal, cast(MultiRowCheckResult, high.shear_out_result).utilization)
        > cast(Decimal, cast(MultiRowCheckResult, low.shear_out_result).utilization)
        for low, high in zip(lower.line_results, higher.line_results, strict=True)
    )
    reversed_force = calculate_eccentric_group_mode_compatibility(
        _group_input(force_u="-3", offset_v="0.1")
    )
    assert reversed_force.connection_force_unit_direction == (Decimal(-1), Decimal(0))
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT
        for item in reversed_force.line_results
    )
    assert tuple(
        abs(item.parallel_scalar.canonical_magnitude) for item in reversed_force.line_results
    )


def test_parent_block_and_zero_connection_force_states_remain_fail_closed() -> None:
    blocked = calculate_eccentric_group_mode_compatibility(_group_input(member_moment="1"))
    assert all(
        item.handoff_status is EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED
        and item.warnings[0].code
        is EccentricGroupModeWarningCode.PARENT_RESISTANCE_HANDOFF_NOT_AVAILABLE
        for item in blocked.line_results
    )
    assert blocked.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED

    value = _group_input()
    demand = value.parent_handoff_input.demand_result
    zero_force = replace(
        demand.projected_force,
        u=PhysicalQuantity.of(0, Unit.N),
        v=PhysicalQuantity.of(0, Unit.N),
    )
    synthetic_demand = replace(demand, projected_force=zero_force)
    handoff_input = replace(value.parent_handoff_input, demand_result=synthetic_demand)
    handoff_result = calculate_eccentric_resistance_handoff(handoff_input)
    synthetic = calculate_eccentric_group_mode_compatibility(
        EccentricGroupModeCompatibilityInput(handoff_input, handoff_result, value.source_trace)
    )
    assert synthetic.connection_force_unit_direction is None
    assert all(
        item.warnings[0].code
        is EccentricGroupModeWarningCode.ECCENTRIC_SHEAROUT_ZERO_CONNECTION_FORCE_NOT_SUPPORTED
        for item in synthetic.line_results
    )


def test_invalid_or_incomplete_existing_interrow_results_remain_explicit() -> None:
    base = _scaled_bundle()
    checks = tuple(
        replace(item, geometry_status=GeometryStatus.INVALID_GEOMETRY)
        if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
        else item
        for item in base.checks
    )
    invalid = calculate_eccentric_group_mode_compatibility(
        _group_input(bundle=replace(base, checks=checks))
    )
    assert invalid.overall_disposition is MultiRowOverallDisposition.INVALID_GEOMETRY
    assert all(
        item.shear_out_result is not None
        and item.shear_out_result.availability is MultiRowResultAvailability.INVALID_GEOMETRY
        for item in invalid.line_results
    )

    checks = tuple(
        replace(item, plan_availability=PlanAvailability.INCOMPLETE_INPUT)
        if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
        else item
        for item in base.checks
    )
    incomplete = calculate_eccentric_group_mode_compatibility(
        _group_input(bundle=replace(base, checks=checks))
    )
    assert set(incomplete.incomplete_required_check_ids) >= {"interrow:1", "interrow:2"}
    assert incomplete.overall_disposition is MultiRowOverallDisposition.NOT_EVALUATED


def test_engine_rejects_missing_duplicate_or_mismatched_physical_membership() -> None:
    value = _group_input()
    bundle = value.parent_handoff_input.execution_bundle
    lines = bundle.physical_geometry.bolt_lines
    duplicate_geometry = replace(
        bundle.physical_geometry,
        bolt_lines=(
            lines[0],
            replace(lines[1], bolt_ids=(lines[0].bolt_ids[0], *lines[1].bolt_ids)),
        ),
    )
    duplicate_bundle = replace(bundle, physical_geometry=duplicate_geometry)
    duplicate_handoff = replace(value.parent_handoff_input, execution_bundle=duplicate_bundle)
    duplicate_parent = calculate_eccentric_resistance_handoff(duplicate_handoff)
    with pytest.raises(ValueError, match="exactly once"):
        calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(
                duplicate_handoff, duplicate_parent, value.source_trace
            )
        )

    missing_geometry = replace(
        bundle.physical_geometry,
        bolt_lines=(lines[0], replace(lines[1], bolt_ids=lines[1].bolt_ids[:-1])),
    )
    missing_bundle = replace(bundle, physical_geometry=missing_geometry)
    missing_handoff = replace(value.parent_handoff_input, execution_bundle=missing_bundle)
    missing_parent = calculate_eccentric_resistance_handoff(missing_handoff)
    with pytest.raises(ValueError, match="exactly once"):
        calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(
                missing_handoff, missing_parent, value.source_trace
            )
        )

    scenario = value.parent_handoff_input.demand_result.scenarios[0]
    mismatched_bolt = replace(scenario.per_bolt[0], bolt_line_id="WRONG")
    mismatched_scenario = replace(scenario, per_bolt=(mismatched_bolt, *scenario.per_bolt[1:]))
    mismatched_demand = replace(
        value.parent_handoff_input.demand_result,
        scenarios=(mismatched_scenario,),
    )
    mismatched_handoff = replace(value.parent_handoff_input, demand_result=mismatched_demand)
    mismatched_parent = calculate_eccentric_resistance_handoff(mismatched_handoff)
    with pytest.raises(ValueError, match="bolt-line identities"):
        calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(
                mismatched_handoff, mismatched_parent, value.source_trace
            )
        )


def test_line_check_identity_and_parent_identity_validation_are_exact() -> None:
    value = _group_input()
    bundle = value.parent_handoff_input.execution_bundle
    interrow = tuple(
        item for item in bundle.checks if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
    )
    duplicated = replace(interrow[1], bolt_line_id=interrow[0].bolt_line_id)
    checks = tuple(
        duplicated if item.check_id == duplicated.check_id else item for item in bundle.checks
    )
    duplicate_bundle = replace(bundle, checks=checks)
    handoff_input = replace(value.parent_handoff_input, execution_bundle=duplicate_bundle)
    parent = calculate_eccentric_resistance_handoff(handoff_input)
    with pytest.raises(ValueError, match="unique physical bolt line"):
        calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(handoff_input, parent, value.source_trace)
        )

    for mutation, message in (
        (
            replace(
                value.parent_handoff_result,
                parent_demand_input_fingerprint="0" * 64,
            ),
            "demand input",
        ),
        (
            replace(
                value.parent_handoff_result,
                parent_demand_result_fingerprint="0" * 64,
            ),
            "demand result",
        ),
        (
            replace(
                value.parent_handoff_result,
                parent_resistance_input_fingerprint="0" * 64,
            ),
            "resistance fingerprints",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            EccentricGroupModeCompatibilityInput(
                value.parent_handoff_input, mutation, value.source_trace
            )


def test_versions_fingerprints_and_immutable_contracts_are_exact() -> None:
    versions = EccentricGroupModeVersionContext()
    assert (
        versions.calculation_contract_version,
        versions.eccentric_group_mode_engine_version,
        versions.eccentric_group_mode_rule_set_version,
        versions.eccentric_group_mode_result_schema_version,
        versions.eccentric_group_mode_fingerprint_schema_version,
        ECCENTRIC_GROUP_MODE_DECIMAL_PRECISION,
    ) == (
        ECCENTRIC_GROUP_MODE_CALCULATION_CONTRACT_VERSION,
        ECCENTRIC_GROUP_MODE_ENGINE_VERSION,
        ECCENTRIC_GROUP_MODE_RULE_SET_VERSION,
        ECCENTRIC_GROUP_MODE_RESULT_SCHEMA_VERSION,
        ECCENTRIC_GROUP_MODE_FINGERPRINT_SCHEMA_VERSION,
        80,
    )
    with pytest.raises(ValueError, match="approved RC1"):
        EccentricGroupModeVersionContext(calculation_contract_version="wrong")

    value = _group_input()
    first = calculate_eccentric_group_mode_compatibility(value)
    changed = calculate_eccentric_group_mode_compatibility(_group_input(total="4"))
    assert first.input_fingerprint == eccentric_group_mode_input_fingerprint(value)
    assert first.result_fingerprint != changed.result_fingerprint
    assert first.parent_demand_result_fingerprint != changed.parent_demand_result_fingerprint
    assert canonical_eccentric_group_mode_input_json(
        value
    ) == canonical_eccentric_group_mode_input_json(
        EccentricGroupModeFingerprintEnvelope(value, "SI")
    )
    with pytest.raises(FrozenInstanceError):
        first.scenario_id = "changed"  # type: ignore[misc]


def test_contract_guards_reject_wrong_types_invalid_vectors_and_contradictory_states() -> None:
    value = _group_input()
    result = calculate_eccentric_group_mode_compatibility(value)
    line = result.line_results[0]
    with pytest.raises(TypeError, match="CompatibilityInput"):
        calculate_eccentric_group_mode_compatibility(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="fingerprinting"):
        canonical_eccentric_group_mode_input_json(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="binary floats"):
        group_module._canonicalize(1.0)
    with pytest.raises(TypeError, match="Unsupported"):
        group_module._canonicalize(object())
    with pytest.raises(ValueError, match="in-plane force vector"):
        EccentricLineBoltVector(
            "BOLT",
            InPlaneQuantityVector(PhysicalQuantity.of(1, Unit.IN), PhysicalQuantity.of(1, Unit.IN)),
        )
    with pytest.raises(ValueError, match="match contributing"):
        replace(line, contributing_bolt_ids=("WRONG", *line.contributing_bolt_ids[1:]))
    with pytest.raises(ValueError, match="cannot retain resistance"):
        replace(
            line,
            handoff_status=EccentricLineHandoffStatus.CALCULATION_NOT_SUPPORTED,
        )
    with pytest.raises(ValueError, match="requires demand"):
        replace(line, required_line_demand=None, shear_out_result=None)
    with pytest.raises(ValueError, match="parent-exempt"):
        EccentricFirstRowCompatibility(
            EccentricFirstRowHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION,
            ("required",),
        )
    with pytest.raises(ValueError, match="SHA-256"):
        replace(result, result_fingerprint="bad")


def test_defensive_contract_and_fail_closed_helper_branches() -> None:
    value = _group_input()
    result = calculate_eccentric_group_mode_compatibility(value)
    line = result.line_results[0]
    parent_input = value.parent_handoff_input
    parent = value.parent_handoff_result
    bundle = parent_input.execution_bundle

    with pytest.raises(TypeError, match="WarningCode"):
        EccentricGroupModeWarning("bad")  # type: ignore[arg-type]
    exempt_line = replace(
        line,
        check_id=None,
        handoff_status=EccentricLineHandoffStatus.NOT_REQUIRED_PARENT_EXEMPTION,
        required_line_demand=None,
        shear_out_result=None,
    )
    assert exempt_line.check_id is None
    with pytest.raises(TypeError, match="handoff_status"):
        replace(line, handoff_status="bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="MultiRowCheckResult"):
        replace(line, shear_out_result=object())  # type: ignore[arg-type]
    wrong_result = next(
        item
        for item in parent.supported_results
        if item.limit_state is MultiRowCheckFamily.BOLT_SHEAR
    )
    with pytest.raises(ValueError, match="physical bolt line"):
        replace(line, shear_out_result=wrong_result)
    with pytest.raises(TypeError, match="FirstRowHandoffStatus"):
        EccentricFirstRowCompatibility("bad", ())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="parent_handoff_input"):
        EccentricGroupModeCompatibilityInput(object(), parent, ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="parent_handoff_result"):
        EccentricGroupModeCompatibilityInput(parent_input, object(), ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="VersionContext"):
        EccentricGroupModeCompatibilityInput(
            parent_input,
            parent,
            (),
            versions=object(),  # type: ignore[arg-type]
        )
    for mutation, message in (
        (
            replace(parent, parent_demand_versions=object()),  # type: ignore[arg-type]
            "demand versions",
        ),
        (
            replace(parent, parent_resistance_versions=object()),  # type: ignore[arg-type]
            "resistance versions",
        ),
        (
            replace(parent, versions=object()),  # type: ignore[arg-type]
            "handoff versions",
        ),
        (replace(parent, checks=tuple(reversed(parent.checks))), "checks"),
    ):
        with pytest.raises(ValueError, match=message):
            EccentricGroupModeCompatibilityInput(parent_input, mutation, ())

    with pytest.raises(TypeError, match="two-Decimal"):
        replace(result, connection_force_unit_direction=(Decimal(1),))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="first_row_compatibility"):
        replace(result, first_row_compatibility=object())  # type: ignore[arg-type]

    scenario = parent_input.demand_result.scenarios[0]
    unavailable = replace(
        scenario, availability=DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED
    )
    with pytest.raises(ValueError, match="calculated parent"):
        group_module._scenario(
            replace(
                parent_input,
                demand_result=replace(parent_input.demand_result, scenarios=(unavailable,)),
            )
        )
    with pytest.raises(ValueError, match="scenario_id"):
        group_module._scenario(replace(parent_input, scenario_id="missing"))
    preceding = replace(scenario, scenario_id="preceding")
    selected = group_module._scenario(
        replace(
            parent_input,
            demand_result=replace(parent_input.demand_result, scenarios=(preceding, scenario)),
        )
    )
    assert selected is scenario

    duplicate_bolts = replace(scenario, per_bolt=(scenario.per_bolt[0], scenario.per_bolt[0]))
    with pytest.raises(ValueError, match="unique"):
        group_module._validated_line_membership(bundle, duplicate_bolts)
    missing_bolts = replace(scenario, per_bolt=scenario.per_bolt[:-1])
    with pytest.raises(ValueError, match="all and only"):
        group_module._validated_line_membership(bundle, missing_bolts)

    physical_lines = bundle.physical_geometry.bolt_lines
    unknown_physical = replace(
        bundle.physical_geometry,
        bolt_lines=(replace(physical_lines[0], id="UNKNOWN"), physical_lines[1]),
    )
    with pytest.raises(ValueError, match="canonical physical"):
        group_module._line_checks(replace(bundle, physical_geometry=unknown_physical))
    fake_bundle = SimpleNamespace(
        checks=(SimpleNamespace(family=MultiRowCheckFamily.INTERROW_SHEAR_OUT, bolt_line_id=None),),
        physical_geometry=bundle.physical_geometry,
    )
    with pytest.raises(ValueError, match="unique physical"):
        group_module._line_checks(fake_bundle)  # type: ignore[arg-type]

    bolt_check = next(
        item for item in bundle.checks if item.family is MultiRowCheckFamily.BOLT_SHEAR
    )
    with pytest.raises(ValueError, match="accepted inter-row plan"):
        group_module._execute_line(bundle, bolt_check, PhysicalQuantity.of(1, Unit.KIP))
    legacy_bundle = _with_golden_shear_strength(_scaled_bundle())
    legacy_bundle = replace(
        legacy_bundle,
        checks=tuple(
            replace(item, demand=None)
            if item.family is MultiRowCheckFamily.INTERROW_SHEAR_OUT
            else item
            for item in legacy_bundle.checks
        ),
    )
    legacy_input = _handoff_input(total="3", offset_v="0", bundle=legacy_bundle)
    legacy_parent = calculate_eccentric_resistance_handoff(legacy_input)
    with pytest.raises(ValueError, match="accepted legacy demand"):
        calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(legacy_input, legacy_parent, ())
        )
    assert group_module._unsupported_ids(parent, (exempt_line,), set(), ()) == ()
    assert group_module._numerical(("missing",), (), (), (), ()) is (
        NumericalComparison.NOT_EVALUATED
    )
    assert group_module._governing((), set()) == ()
    assert (
        group_module._overall(
            replace(
                parent, qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
            ),
            (),
            NumericalComparison.PASS,
            (),
            (),
            set(),
        )
        is MultiRowOverallDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )
    assert (
        group_module._overall(
            replace(parent, qualification=QualificationDisposition.ENGINEERING_REVIEW_REQUIRED),
            (),
            NumericalComparison.PASS,
            (),
            (),
            set(),
        )
        is MultiRowOverallDisposition.ENGINEERING_REVIEW_REQUIRED
    )
    invalid_parent = replace(
        parent,
        checks=(
            replace(parent.checks[0], availability=MultiRowResultAvailability.INVALID_GEOMETRY),
            *parent.checks[1:],
        ),
    )
    assert (
        group_module._overall(
            invalid_parent,
            (),
            NumericalComparison.PASS,
            (),
            (),
            {invalid_parent.checks[0].check_id},
        )
        is MultiRowOverallDisposition.INVALID_GEOMETRY
    )

    assert group_module._canonicalize(EccentricGroupModeFingerprintEnvelope(value))
    assert group_module._canonicalize(1) == "1"
    with pytest.raises(ValueError, match="nonempty text"):
        group_module._require_text("", "value")
    for bad, message in (
        ((), "nonempty tuple"),
        (("",), "nonempty text"),
        (("duplicate", "duplicate"), "unique"),
    ):
        with pytest.raises(ValueError, match=message):
            group_module._require_text_tuple(bad, "value")
    with pytest.raises(TypeError, match="immutable tuple"):
        group_module._require_typed_tuple((object(),), EccentricLineBoltVector, "value")
    with pytest.raises(ValueError, match="force quantity"):
        group_module._require_force(PhysicalQuantity.of(1, Unit.IN), "value")
    with pytest.raises(ValueError, match="negative"):
        group_module._require_force(PhysicalQuantity.of(-1, Unit.N), "value")


def test_no_new_equation_golden_framework_or_integration_boundary() -> None:
    source = Path(group_module.__file__).read_text(encoding="utf-8")
    assert "interrow_shear_out_resistance(" not in source
    assert "calculate_multirow_connection(" in source
    assert "backend/tests/golden" not in source
    assert "fastapi" not in source.lower()
    assert "pydantic" not in source.lower()
    assert "frontend" not in source.lower()
    assert "application" not in source.lower()
    assert all(
        token not in source for token in ("open(", "urlopen", "requests.", "time.", "random.")
    )
    root = Path(__file__).parents[2]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for folder in (
            root / "backend" / "src" / "frp_master_connection" / "application",
            root / "backend" / "src" / "frp_master_connection" / "api",
        )
        for path in folder.rglob("*.py")
    )
    assert "calculate_eccentric_group_mode_compatibility" not in combined
    assert RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF in source
