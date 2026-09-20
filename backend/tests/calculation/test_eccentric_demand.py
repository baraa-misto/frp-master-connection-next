"""Calculation Slice 3 RC1 eccentric demand engine tests."""

import hashlib
from dataclasses import FrozenInstanceError, replace
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from types import MappingProxyType
from typing import cast
from unittest.mock import patch

import pytest

import frp_master_connection.calculation.eccentric_demand as demand_module
from frp_master_connection.calculation import (
    DEMAND_FRAME_TOLERANCE,
    DemandAnalysisAvailability,
    DemandAnalysisMethod,
    DemandAnalysisWarning,
    DemandAnalysisWarningCode,
    EccentricDemandFingerprintEnvelope,
    EccentricDemandInput,
    EquilibriumVerification,
    ExactInterfaceFrame,
    ExactQuantityVector3D,
    InPlaneQuantityVector,
    MethodProvenance,
    MultiRowBoltGeometryContext,
    MultiRowDemandPlan,
    MultiRowMethodApplicability,
    MultiRowPhysicalGeometryContext,
    MultiRowProjectedGroupContext,
    PerBoltDemandPlan,
    PhysicalQuantity,
    PlanAvailability,
    ProjectedForce,
    QualificationDisposition,
    ResistanceHandoffDisposition,
    RowDemandPlan,
    RowDemandScenario,
    RowDistributionBasis,
    Slice3VersionContext,
    Unit,
    calculate_eccentric_bolt_group_demand,
    canonical_eccentric_demand_input_json,
    eccentric_demand_input_fingerprint,
    verify_eccentric_demand_equilibrium,
)
from tests.calculation.golden_loader import (
    FrozenJson,
    decimal_strings,
    load_slice_3_rc1_golden_fixture,
)

_ZERO = ExactQuantityVector3D(
    PhysicalQuantity.of(0, Unit.KIP_IN),
    PhysicalQuantity.of(0, Unit.KIP_IN),
    PhysicalQuantity.of(0, Unit.KIP_IN),
)


def _provenance() -> MethodProvenance:
    return MethodProvenance(
        "SLICE_2_APPROVED_DIRECT_DISTRIBUTION",
        "Calculation Slice 2 RC2",
        "RC2",
        "LC-1",
        "PHYSICAL_FORCE_REFERENCE_POINT",
        False,
        True,
    )


def _frame(*, length_unit: Unit = Unit.IN) -> ExactInterfaceFrame:
    return ExactInterfaceFrame(
        "INTERFACE-1",
        ExactQuantityVector3D(
            PhysicalQuantity.of(0, length_unit),
            PhysicalQuantity.of(0, length_unit),
            PhysicalQuantity.of(0, length_unit),
        ),
        (Decimal(1), Decimal(0), Decimal(0)),
        (Decimal(0), Decimal(1), Decimal(0)),
        (Decimal(0), Decimal(0), Decimal(1)),
    )


def _physical_geometry(
    coordinates: tuple[tuple[str, str], ...], *, length_unit: Unit = Unit.IN
) -> MultiRowPhysicalGeometryContext:
    xs = tuple(dict.fromkeys(item[0] for item in coordinates))
    ys = tuple(dict.fromkeys(item[1] for item in coordinates))
    bolts = tuple(
        MultiRowBoltGeometryContext(
            f"B{index}",
            Decimal(x),
            Decimal(y),
            Decimal("0.5") if length_unit is Unit.IN else Decimal("12.7"),
            Decimal("0.563") if length_unit is Unit.IN else Decimal("14.3002"),
            "IDENTICAL-BOLT",
            "CONNECTION-1",
        )
        for index, (x, y) in enumerate(coordinates, start=1)
    )
    rows = tuple(
        MultiRowProjectedGroupContext(
            f"ROW_{index}",
            index,
            Decimal(x),
            Decimal(0),
            tuple(
                bolt.bolt_id
                for bolt, coordinate in zip(bolts, coordinates, strict=True)
                if coordinate[0] == x
            ),
        )
        for index, x in enumerate(xs, start=1)
    )
    lines = tuple(
        MultiRowProjectedGroupContext(
            f"LINE_{index}",
            index,
            Decimal(y),
            Decimal(0),
            tuple(
                bolt.bolt_id
                for bolt, coordinate in zip(bolts, coordinates, strict=True)
                if coordinate[1] == y
            ),
        )
        for index, y in enumerate(ys, start=1)
    )
    return MultiRowPhysicalGeometryContext(
        "GROUP-1",
        "INTERFACE-1",
        "BOUNDARY-1",
        length_unit,
        (Decimal(1), Decimal(0)),
        (Decimal(0), Decimal(1)),
        bolts,
        rows,
        lines,
        min(Decimal(item) for item in xs) - Decimal(1),
        max(Decimal(item) for item in xs) + Decimal(1),
        min(Decimal(item) for item in ys) - Decimal(1),
        max(Decimal(item) for item in ys) + Decimal(1),
        Decimal("0.000001"),
    )


def _direct_plan(
    geometry: MultiRowPhysicalGeometryContext,
    shares: tuple[str, ...],
    total: PhysicalQuantity,
    *,
    basis: RowDistributionBasis = RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
) -> MultiRowDemandPlan:
    share_by_bolt = {
        bolt.bolt_id: Decimal(share) for bolt, share in zip(geometry.bolts, shares, strict=True)
    }
    rows = tuple(
        RowDemandPlan(
            row.id,
            total * sum((share_by_bolt[bolt_id] for bolt_id in row.bolt_ids), Decimal(0)),
            sum((share_by_bolt[bolt_id] for bolt_id in row.bolt_ids), Decimal(0)),
            tuple(
                PerBoltDemandPlan(bolt_id, total * share_by_bolt[bolt_id])
                for bolt_id in row.bolt_ids
            ),
        )
        for row in geometry.rows
    )
    scenario_id = {
        RowDistributionBasis.ASCE_PRESCRIBED: "ASCE_PRESCRIBED",
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE: "FULL_ROW_ROW_1",
        RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION: "ENGINEER_DEFINED",
    }[basis]
    return MultiRowDemandPlan(
        basis,
        total,
        (RowDemandScenario(scenario_id, None, rows),),
        PlanAvailability.READY,
        _provenance(),
        (),
    )


def _input(
    *,
    coordinates: tuple[tuple[str, str], ...] = (
        ("-1", "-1"),
        ("-1", "1"),
        ("1", "-1"),
        ("1", "1"),
    ),
    shares: tuple[str, ...] = (".25", ".25", ".25", ".25"),
    force: tuple[str, str, str] = ("10", "0", "0"),
    reference: tuple[str, str, str] = ("0", "2", "0"),
    length_unit: Unit = Unit.IN,
    force_unit: Unit = Unit.KIP,
    member_moments: ExactQuantityVector3D = _ZERO,
    connection_moments: ExactQuantityVector3D = _ZERO,
    basis: RowDistributionBasis = RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
) -> EccentricDemandInput:
    geometry = _physical_geometry(coordinates, length_unit=length_unit)
    magnitude = (Decimal(force[0]) ** 2 + Decimal(force[1]) ** 2).sqrt()
    total = PhysicalQuantity.of(magnitude, force_unit)
    return EccentricDemandInput(
        "ACTION-SOURCE-1",
        "MEMBER-1",
        ExactQuantityVector3D(*(PhysicalQuantity.of(item, force_unit) for item in force)),
        member_moments,
        connection_moments,
        ExactQuantityVector3D(*(PhysicalQuantity.of(item, length_unit) for item in reference)),
        _frame(length_unit=length_unit),
        geometry,
        _direct_plan(geometry, shares, total, basis=basis),
        MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE,
        QualificationDisposition.ENGINEERING_REVIEW_REQUIRED,
        (
            "ASCE/SEI 74-23 Section 2.9",
            "Commentary C8.1",
            "Commentary C8.3.2",
        ),
    )


def _mapping(value: FrozenJson) -> MappingProxyType[str, FrozenJson]:
    return cast(MappingProxyType[str, FrozenJson], value)


def _tuple(value: FrozenJson) -> tuple[FrozenJson, ...]:
    return cast(tuple[FrozenJson, ...], value)


def _serialized(value: PhysicalQuantity, unit: Unit) -> str:
    rounded = value.to(unit).magnitude.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
    return format(rounded, ".12f")


def test_slice_3_golden_identity_hash_schema_cases_and_immutability() -> None:
    path = Path(__file__).parents[1] / "golden" / "calculation_slice_3_rc1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == (
        "0B2999DE96F1C4C02A1B68D4E4F262E4BFE3FBD65F3D8D1A50DE7F9B65C01D7B"
    )
    first = load_slice_3_rc1_golden_fixture()
    second = load_slice_3_rc1_golden_fixture()
    assert first == second
    assert first["schema_version"] == "frp-master-connection-calculation-slice-3-golden-rc1"
    assert tuple(_mapping(item)["id"] for item in _tuple(first["numerical_cases"])) == (
        "CONCENTRIC_2X2_EQUAL",
        "ECCENTRIC_2X2_EQUAL",
        "DIAGONAL_FORCE_ECCENTRIC_2X2",
        "FORCE_REVERSAL_2X2",
        "FRP_STEEL_3ROW_ECCENTRIC",
    )
    assert tuple(_mapping(item)["id"] for item in _tuple(first["status_cases"])) == (
        "PURE_MOMENT_ZERO_FORCE",
        "OUT_OF_PLANE_FORCE_PRESENT",
        "MEMBER_END_MOMENT_PRESENT",
        "SINGLE_BOLT_ECCENTRIC_FORCE",
    )
    assert decimal_strings(first)
    with pytest.raises(TypeError):
        first["schema_version"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    "case_id",
    [
        "CONCENTRIC_2X2_EQUAL",
        "ECCENTRIC_2X2_EQUAL",
        "DIAGONAL_FORCE_ECCENTRIC_2X2",
        "FORCE_REVERSAL_2X2",
        "FRP_STEEL_3ROW_ECCENTRIC",
    ],
)
def test_every_slice_3_golden_numerical_case(case_id: str) -> None:
    golden = load_slice_3_rc1_golden_fixture()
    cases = tuple(_mapping(item) for item in _tuple(golden["numerical_cases"]))
    case = next(item for item in cases if item["id"] == case_id)
    coordinates = tuple(
        (cast(str, _tuple(item)[0]), cast(str, _tuple(item)[1]))
        for item in _tuple(case["bolt_coordinates_in"])
    )
    force_values = _tuple(case["in_plane_force_kip"])
    reference_values = _tuple(case["force_reference_point_in"])
    value = _input(
        coordinates=coordinates,
        shares=tuple(cast(str, item) for item in _tuple(case["direct_share_per_bolt"])),
        force=(cast(str, force_values[0]), cast(str, force_values[1]), "0"),
        reference=(cast(str, reference_values[0]), cast(str, reference_values[1]), "0"),
    )
    result = calculate_eccentric_bolt_group_demand(value)
    scenario = result.scenarios[0]
    centroid_values = _tuple(case["geometric_bolt_centroid_in"])
    assert result.availability is DemandAnalysisAvailability.CALCULATED
    assert result.geometric_bolt_centroid.u.to(Unit.IN).magnitude == Decimal(
        cast(str, centroid_values[0])
    )
    assert result.geometric_bolt_centroid.v.to(Unit.IN).magnitude == Decimal(
        cast(str, centroid_values[1])
    )
    assert _serialized(result.polar_coordinate_sum, Unit.IN2) == case["polar_coordinate_sum_in2"]
    assert (
        _serialized(scenario.external_moment, Unit.KIP_IN)
        == case["external_moment_about_centroid_kip_in"]
    )
    assert (
        _serialized(scenario.direct_distribution_moment, Unit.KIP_IN)
        == case["direct_distribution_moment_kip_in"]
    )
    assert _serialized(scenario.residual_moment, Unit.KIP_IN) == case["residual_moment_kip_in"]
    for actual, expected_value in zip(scenario.per_bolt, _tuple(case["per_bolt"]), strict=True):
        expected = _mapping(expected_value)
        expected_direct = _tuple(expected["direct_force_kip"])
        expected_moment = _tuple(expected["moment_force_kip"])
        expected_total = _tuple(expected["total_force_kip"])
        assert (
            tuple(
                _serialized(item, Unit.KIP)
                for item in (actual.direct_force.u, actual.direct_force.v)
            )
            == expected_direct
        )
        assert (
            tuple(
                _serialized(item, Unit.KIP)
                for item in (actual.moment_force.u, actual.moment_force.v)
            )
            == expected_moment
        )
        assert (
            tuple(
                _serialized(item, Unit.KIP) for item in (actual.total_force.u, actual.total_force.v)
            )
            == expected_total
        )
        assert (
            _serialized(actual.total_force_magnitude, Unit.KIP)
            == expected["total_force_magnitude_kip"]
        )
    assert scenario.equilibrium is not None
    assert scenario.equilibrium.satisfied
    assert scenario.equilibrium.force_residual.u.canonical_magnitude == 0
    assert scenario.equilibrium.force_residual.v.canonical_magnitude == 0
    assert scenario.equilibrium.moment_residual.canonical_magnitude == 0
    assert result.resistance_handoff is ResistanceHandoffDisposition.NOT_AUTHORIZED_IN_RC1
    assert scenario.method is DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY


def test_us_si_physical_equivalence_and_display_envelope_fingerprint_exclusions() -> None:
    us = _input()
    si = _input(
        coordinates=(("-25.4", "-25.4"), ("-25.4", "25.4"), ("25.4", "-25.4"), ("25.4", "25.4")),
        force=("44.482216152605", "0", "0"),
        reference=("0", "50.8", "0"),
        length_unit=Unit.MM,
        force_unit=Unit.KN,
    )
    us_result = calculate_eccentric_bolt_group_demand(us)
    si_result = calculate_eccentric_bolt_group_demand(si)
    unit_case = _mapping(load_slice_3_rc1_golden_fixture()["unit_equivalence_case"])
    assert us_result.input_fingerprint == si_result.input_fingerprint
    assert us_result.result_fingerprint == si_result.result_fingerprint
    assert tuple(item.total_force_magnitude for item in us_result.scenarios[0].per_bolt) == tuple(
        item.total_force_magnitude for item in si_result.scenarios[0].per_bolt
    )
    assert (
        _serialized(si_result.scenarios[0].external_moment, Unit.KN_MM)
        == unit_case["external_moment_kN_mm"]
    )
    assert tuple(
        _serialized(item.total_force_magnitude, Unit.KN) for item in si_result.scenarios[0].per_bolt
    ) == _tuple(unit_case["per_bolt_magnitudes_kN"])
    envelope = EccentricDemandFingerprintEnvelope(
        us, "SI", "3 decimals", {"eye": [1, 2, 3]}, "B1", "200ms", "now"
    )
    assert eccentric_demand_input_fingerprint(envelope) == eccentric_demand_input_fingerprint(us)
    canonical = canonical_eccentric_demand_input_json(envelope)
    assert all(word not in canonical for word in ("camera", "rounding", "timestamp", "selection"))


def test_rotated_frame_projection_and_common_translation_invariance() -> None:
    base = _input(force=("6", "8", "0"), reference=("1.2", "-.5", "0"))
    rotated_frame = ExactInterfaceFrame(
        "INTERFACE-1",
        base.interface_frame.origin,
        (Decimal(0), Decimal(1), Decimal(0)),
        (Decimal(-1), Decimal(0), Decimal(0)),
        (Decimal(0), Decimal(0), Decimal(1)),
    )
    rotated = calculate_eccentric_bolt_group_demand(replace(base, interface_frame=rotated_frame))
    assert rotated.projected_force.u == PhysicalQuantity.of("8", Unit.KIP)
    assert rotated.projected_force.v == PhysicalQuantity.of("-6", Unit.KIP)
    translated = _input(
        coordinates=(("9", "19"), ("9", "21"), ("11", "19"), ("11", "21")),
        force=("6", "8", "0"),
        reference=("11.2", "19.5", "0"),
    )
    first = calculate_eccentric_bolt_group_demand(base).scenarios[0]
    second = calculate_eccentric_bolt_group_demand(translated).scenarios[0]
    assert tuple(item.total_force for item in first.per_bolt) == tuple(
        item.total_force for item in second.per_bolt
    )


def test_direct_distribution_moment_is_retained_and_residual_component_is_linear() -> None:
    nonuniform = calculate_eccentric_bolt_group_demand(
        _input(shares=(".4", ".3", ".2", ".1"))
    ).scenarios[0]
    assert nonuniform.direct_distribution_moment != PhysicalQuantity.of(0, Unit.N_MM)
    one = calculate_eccentric_bolt_group_demand(_input(reference=("0", "1", "0"))).scenarios[0]
    two = calculate_eccentric_bolt_group_demand(_input(reference=("0", "2", "0"))).scenarios[0]
    assert two.residual_moment == one.residual_moment * 2
    assert tuple(item.moment_force.u for item in two.per_bolt) == tuple(
        item.moment_force.u * 2 for item in one.per_bolt
    )
    concentric = calculate_eccentric_bolt_group_demand(_input(reference=("0", "0", "0")))
    assert all(
        item.moment_force
        == InPlaneQuantityVector(PhysicalQuantity.of(0, Unit.N), PhysicalQuantity.of(0, Unit.N))
        for item in concentric.scenarios[0].per_bolt
    )


def test_force_reversal_and_increasing_eccentricity_invariants() -> None:
    positive = calculate_eccentric_bolt_group_demand(_input()).scenarios[0]
    negative = calculate_eccentric_bolt_group_demand(_input(force=("-10", "0", "0"))).scenarios[0]
    assert negative.external_moment == positive.external_moment * -1
    assert tuple(item.total_force.u for item in negative.per_bolt) == tuple(
        item.total_force.u * -1 for item in positive.per_bolt
    )
    farther = calculate_eccentric_bolt_group_demand(_input(reference=("0", "4", "0"))).scenarios[0]
    assert any(
        far.total_force_magnitude > near.total_force_magnitude
        for near, far in zip(positive.per_bolt, farther.per_bolt, strict=True)
    )


def test_all_direct_basis_scenarios_are_preserved_independently() -> None:
    base = _input(basis=RowDistributionBasis.ASCE_PRESCRIBED)
    prescribed = calculate_eccentric_bolt_group_demand(base)
    assert prescribed.scenarios[0].direct_basis is RowDistributionBasis.ASCE_PRESCRIBED
    first_row, second_row = base.direct_demand_plan.scenarios[0].rows
    envelope_plan = replace(
        base.direct_demand_plan,
        basis=RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        scenarios=(
            RowDemandScenario(
                "FULL_ROW_ROW_1",
                "ROW_1",
                (
                    replace(
                        first_row,
                        row_fraction=Decimal(1),
                        row_demand=base.direct_demand_plan.total_in_plane_demand,
                        per_bolt_demands=tuple(
                            replace(item, demand=base.direct_demand_plan.total_in_plane_demand / 2)
                            for item in first_row.per_bolt_demands
                        ),
                    ),
                ),
            ),
            RowDemandScenario(
                "FULL_ROW_ROW_2",
                "ROW_2",
                (
                    replace(
                        second_row,
                        row_fraction=Decimal(1),
                        row_demand=base.direct_demand_plan.total_in_plane_demand,
                        per_bolt_demands=tuple(
                            replace(item, demand=base.direct_demand_plan.total_in_plane_demand / 2)
                            for item in second_row.per_bolt_demands
                        ),
                    ),
                ),
            ),
        ),
    )
    envelope = calculate_eccentric_bolt_group_demand(
        replace(base, direct_demand_plan=envelope_plan)
    )
    assert tuple(item.scenario_id for item in envelope.scenarios) == (
        "FULL_ROW_ROW_1",
        "FULL_ROW_ROW_2",
    )
    assert tuple(item.controlling_row_id for item in envelope.scenarios) == ("ROW_1", "ROW_2")
    assert all(item.direct_provenance is envelope_plan.provenance for item in envelope.scenarios)


def test_status_boundaries_are_fail_closed_and_trace_only_actions_are_retained() -> None:
    nonzero_moment = ExactQuantityVector3D(
        PhysicalQuantity.of(1, Unit.KIP_IN),
        PhysicalQuantity.of(0, Unit.KIP_IN),
        PhysicalQuantity.of(0, Unit.KIP_IN),
    )
    pure = calculate_eccentric_bolt_group_demand(
        _input(force=("0", "0", "0"), member_moments=nonzero_moment)
    )
    pure_codes = {item.code for item in pure.warnings}
    assert pure.availability is DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED
    assert DemandAnalysisWarningCode.PURE_CONNECTION_MOMENT_NOT_SUPPORTED in pure_codes
    assert (
        DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL
        in pure_codes
    )
    assert pure.original_member_end_moments is nonzero_moment
    diagnostic = calculate_eccentric_bolt_group_demand(
        _input(force=("5", "0", "1"), member_moments=nonzero_moment)
    )
    diagnostic_codes = {item.code for item in diagnostic.warnings}
    assert diagnostic.availability is DemandAnalysisAvailability.CALCULATED
    assert (
        DemandAnalysisWarningCode.OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND
        in diagnostic_codes
    )
    assert (
        DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL
        in diagnostic_codes
    )
    assert diagnostic.projected_force.n == PhysicalQuantity.of(1, Unit.KIP)
    assert not hasattr(diagnostic.scenarios[0].per_bolt[0], "bolt_axis_tension")
    connection_only = calculate_eccentric_bolt_group_demand(
        _input(connection_moments=nonzero_moment)
    )
    warning = next(
        item
        for item in connection_only.warnings
        if item.code
        is DemandAnalysisWarningCode.MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL
    )
    assert warning.trace == ("independent_connection_moments:trace_only",)


def test_single_bolt_eccentric_force_is_degenerate_but_concentric_force_calculates() -> None:
    eccentric = calculate_eccentric_bolt_group_demand(
        _input(coordinates=(("0", "0"),), shares=("1",))
    )
    assert eccentric.availability is DemandAnalysisAvailability.CALCULATION_NOT_SUPPORTED
    assert eccentric.scenarios[0].warnings[0].code is (
        DemandAnalysisWarningCode.DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT
    )
    concentric = calculate_eccentric_bolt_group_demand(
        _input(coordinates=(("0", "0"),), shares=("1",), reference=("0", "0", "0"))
    )
    assert concentric.availability is DemandAnalysisAvailability.CALCULATED
    assert concentric.scenarios[0].per_bolt[0].total_force == InPlaneQuantityVector(
        PhysicalQuantity.of(10, Unit.KIP), PhysicalQuantity.of(0, Unit.KIP)
    )


def test_unavailable_friction_and_nonrectangular_geometry_do_not_calculate() -> None:
    base = _input()
    unavailable = calculate_eccentric_bolt_group_demand(
        replace(
            base,
            direct_demand_plan=replace(
                base.direct_demand_plan, availability=PlanAvailability.CALCULATION_NOT_SUPPORTED
            ),
        )
    )
    assert unavailable.warnings[-1].code is DemandAnalysisWarningCode.DIRECT_DEMAND_PLAN_NOT_READY
    friction = calculate_eccentric_bolt_group_demand(
        replace(base, direct_demand_plan=replace(base.direct_demand_plan, friction_credit=True))
    )
    assert friction.warnings[-1].code is DemandAnalysisWarningCode.FRICTION_TRANSFER_NOT_SUPPORTED
    geometry = base.physical_geometry
    staggered = replace(
        geometry,
        rows=(replace(geometry.rows[0], raw_deviation=Decimal(".1")), *geometry.rows[1:]),
    )
    unsupported = calculate_eccentric_bolt_group_demand(replace(base, physical_geometry=staggered))
    assert (
        unsupported.warnings[-1].code is DemandAnalysisWarningCode.UNSUPPORTED_BOLT_GROUP_GEOMETRY
    )


def test_invalid_direct_scenarios_and_equilibrium_failure_are_structured() -> None:
    base = _input()
    scenario = base.direct_demand_plan.scenarios[0]
    first_row = scenario.rows[0]
    wrong_row = replace(
        first_row,
        per_bolt_demands=(replace(first_row.per_bolt_demands[0], bolt_id="UNKNOWN"),),
    )
    invalid = calculate_eccentric_bolt_group_demand(
        replace(
            base,
            direct_demand_plan=replace(
                base.direct_demand_plan,
                scenarios=(replace(scenario, rows=(wrong_row,)),),
            ),
        )
    )
    assert invalid.availability is DemandAnalysisAvailability.CALCULATION_FAILED
    assert invalid.scenarios[0].warnings[0].code is (
        DemandAnalysisWarningCode.INVALID_DIRECT_DEMAND_SCENARIO
    )
    valid = calculate_eccentric_bolt_group_demand(base)
    equilibrium = valid.scenarios[0].equilibrium
    assert equilibrium is not None
    failed_equilibrium = replace(equilibrium, satisfied=False)
    with patch(
        "frp_master_connection.calculation.eccentric_demand.verify_eccentric_demand_equilibrium",
        return_value=failed_equilibrium,
    ):
        failed = calculate_eccentric_bolt_group_demand(base)
    assert failed.availability is DemandAnalysisAvailability.CALCULATION_FAILED
    assert DemandAnalysisWarningCode.EQUILIBRIUM_VERIFICATION_FAILED in {
        item.code for item in failed.warnings
    }


def test_zero_total_fraction_path_and_other_invalid_share_paths_are_explicit() -> None:
    zero = _input(force=("0", "0", "0"))
    calculated_zero = calculate_eccentric_bolt_group_demand(zero)
    assert calculated_zero.availability is DemandAnalysisAvailability.CALCULATED
    assert all(
        item.total_force_magnitude.canonical_magnitude == 0
        for item in calculated_zero.scenarios[0].per_bolt
    )

    scenario = zero.direct_demand_plan.scenarios[0]
    no_fraction_rows = tuple(replace(row, row_fraction=None) for row in scenario.rows)
    no_fraction = calculate_eccentric_bolt_group_demand(
        replace(
            zero,
            direct_demand_plan=replace(
                zero.direct_demand_plan,
                scenarios=(replace(scenario, rows=no_fraction_rows),),
            ),
        )
    )
    assert no_fraction.availability is DemandAnalysisAvailability.CALCULATION_FAILED

    base = _input()
    scenario = base.direct_demand_plan.scenarios[0]
    first_row = scenario.rows[0]
    negative_row = replace(
        first_row,
        per_bolt_demands=(
            replace(first_row.per_bolt_demands[0], demand=PhysicalQuantity.of("-1", Unit.KIP)),
            *first_row.per_bolt_demands[1:],
        ),
    )
    negative = calculate_eccentric_bolt_group_demand(
        replace(
            base,
            direct_demand_plan=replace(
                base.direct_demand_plan,
                scenarios=(replace(scenario, rows=(negative_row, *scenario.rows[1:])),),
            ),
        )
    )
    assert negative.availability is DemandAnalysisAvailability.CALCULATION_FAILED

    incomplete_rows = tuple(
        replace(
            row,
            per_bolt_demands=tuple(
                replace(item, demand=PhysicalQuantity.of(".1", Unit.KIP))
                for item in row.per_bolt_demands
            ),
        )
        for row in scenario.rows
    )
    incomplete = calculate_eccentric_bolt_group_demand(
        replace(
            base,
            direct_demand_plan=replace(
                base.direct_demand_plan,
                scenarios=(replace(scenario, rows=incomplete_rows),),
            ),
        )
    )
    assert incomplete.availability is DemandAnalysisAvailability.CALCULATION_FAILED


def test_equilibrium_verifier_detects_deliberate_force_and_moment_tampering() -> None:
    result = calculate_eccentric_bolt_group_demand(_input())
    scenario = result.scenarios[0]
    first = scenario.per_bolt[0]
    force_tamper = replace(
        first,
        total_force=replace(
            first.total_force, u=first.total_force.u + PhysicalQuantity.of(".1", Unit.KIP)
        ),
    )
    force_check = verify_eccentric_demand_equilibrium(
        result.projected_force,
        scenario.external_moment,
        result.geometric_bolt_centroid,
        (force_tamper, *scenario.per_bolt[1:]),
    )
    assert not force_check.satisfied
    assert force_check.force_residual.u.canonical_magnitude != 0
    moment_tamper = replace(
        first,
        total_force=replace(
            first.total_force, v=first.total_force.v + PhysicalQuantity.of(".1", Unit.KIP)
        ),
    )
    moment_check = verify_eccentric_demand_equilibrium(
        result.projected_force,
        scenario.external_moment,
        result.geometric_bolt_centroid,
        (moment_tamper, *scenario.per_bolt[1:]),
    )
    assert not moment_check.satisfied
    assert moment_check.moment_residual.canonical_magnitude != 0


def test_fingerprint_is_deterministic_directional_and_reference_sensitive() -> None:
    base = _input()
    assert eccentric_demand_input_fingerprint(base) == eccentric_demand_input_fingerprint(base)
    assert calculate_eccentric_bolt_group_demand(base) == calculate_eccentric_bolt_group_demand(
        base
    )
    assert eccentric_demand_input_fingerprint(base) != eccentric_demand_input_fingerprint(
        _input(force=("-10", "0", "0"))
    )
    assert eccentric_demand_input_fingerprint(base) != eccentric_demand_input_fingerprint(
        _input(reference=("0", "3", "0"))
    )
    assert len(calculate_eccentric_bolt_group_demand(base).result_fingerprint) == 64


def test_contract_validation_immutability_versions_and_wrong_root_types() -> None:
    base = _input()
    with pytest.raises(FrozenInstanceError):
        base.action_source_id = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError, match="EccentricDemandInput"):
        calculate_eccentric_bolt_group_demand(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="input or presentation"):
        canonical_eccentric_demand_input_json(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="approved RC1 identities"):
        replace(Slice3VersionContext(), demand_analysis_engine_version="wrong")
    with pytest.raises(ValueError, match="external_moment"):
        verify_eccentric_demand_equilibrium(
            ProjectedForce(
                PhysicalQuantity.of(0, Unit.N),
                PhysicalQuantity.of(0, Unit.N),
                PhysicalQuantity.of(0, Unit.N),
            ),
            PhysicalQuantity.of(0, Unit.N),
            InPlaneQuantityVector(PhysicalQuantity.of(0, Unit.MM), PhysicalQuantity.of(0, Unit.MM)),
            (),
        )
    assert Decimal("1E-12") == DEMAND_FRAME_TOLERANCE


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"action_source_id": ""}, "action_source_id"),
        (
            {
                "global_force": ExactQuantityVector3D(
                    PhysicalQuantity.of(0, Unit.MM),
                    PhysicalQuantity.of(0, Unit.MM),
                    PhysicalQuantity.of(0, Unit.MM),
                )
            },
            "global_force",
        ),
        (
            {
                "member_end_moments": ExactQuantityVector3D(
                    PhysicalQuantity.of(0, Unit.N),
                    PhysicalQuantity.of(0, Unit.N),
                    PhysicalQuantity.of(0, Unit.N),
                )
            },
            "Moment vectors",
        ),
        (
            {
                "force_reference_point": ExactQuantityVector3D(
                    PhysicalQuantity.of(0, Unit.N),
                    PhysicalQuantity.of(0, Unit.N),
                    PhysicalQuantity.of(0, Unit.N),
                )
            },
            "force_reference_point",
        ),
        (
            {
                "interface_frame": ExactInterfaceFrame(
                    "OTHER", _frame().origin, _frame().u, _frame().v, _frame().n
                )
            },
            "identities",
        ),
    ],
)
def test_input_rejects_incompatible_authority(mutation: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(_input(), **mutation)  # type: ignore[arg-type]


def test_low_level_contracts_reject_invalid_dimensions_axes_and_warnings() -> None:
    with pytest.raises(TypeError, match="PhysicalQuantity"):
        ExactQuantityVector3D(
            cast(PhysicalQuantity, "1"),
            PhysicalQuantity.of(0, Unit.N),
            PhysicalQuantity.of(0, Unit.N),
        )
    with pytest.raises(ValueError, match="share one dimension"):
        ExactQuantityVector3D(
            PhysicalQuantity.of(0, Unit.N),
            PhysicalQuantity.of(0, Unit.MM),
            PhysicalQuantity.of(0, Unit.N),
        )
    with pytest.raises(ValueError, match="length"):
        ExactInterfaceFrame(
            "I",
            ExactQuantityVector3D(
                PhysicalQuantity.of(0, Unit.N),
                PhysicalQuantity.of(0, Unit.N),
                PhysicalQuantity.of(0, Unit.N),
            ),
            _frame().u,
            _frame().v,
            _frame().n,
        )
    with pytest.raises(TypeError, match="three-Decimal"):
        replace(_frame(), u=cast(tuple[Decimal, Decimal, Decimal], (Decimal(1), Decimal(0))))
    with pytest.raises(ValueError, match="orthonormal"):
        replace(_frame(), u=(Decimal(2), Decimal(0), Decimal(0)))
    with pytest.raises(TypeError, match="PhysicalQuantity"):
        InPlaneQuantityVector(cast(PhysicalQuantity, "1"), PhysicalQuantity.of(0, Unit.N))
    with pytest.raises(ValueError, match="one dimension"):
        InPlaneQuantityVector(PhysicalQuantity.of(0, Unit.N), PhysicalQuantity.of(0, Unit.MM))
    with pytest.raises(ValueError, match="force quantities"):
        ProjectedForce(
            PhysicalQuantity.of(0, Unit.N),
            PhysicalQuantity.of(0, Unit.N),
            PhysicalQuantity.of(0, Unit.MM),
        )
    with pytest.raises(TypeError, match="code"):
        DemandAnalysisWarning(cast(DemandAnalysisWarningCode, "bad"))
    with pytest.raises(TypeError, match="trace"):
        DemandAnalysisWarning(
            DemandAnalysisWarningCode.PURE_CONNECTION_MOMENT_NOT_SUPPORTED,
            cast(tuple[str, ...], ["bad"]),
        )
    equilibrium = calculate_eccentric_bolt_group_demand(_input()).scenarios[0].equilibrium
    assert isinstance(equilibrium, EquilibriumVerification)
    with pytest.raises(TypeError, match="Boolean"):
        replace(
            equilibrium,
            satisfied=cast(bool, 1),
        )
    actual = calculate_eccentric_bolt_group_demand(_input()).scenarios[0].per_bolt[0]
    with pytest.raises(ValueError, match="direct_share"):
        replace(actual, direct_share=Decimal(-1))


def test_input_rejects_wrong_contract_types() -> None:
    base = _input()
    for field_name in (
        "global_force",
        "member_end_moments",
        "independent_connection_moments",
        "force_reference_point",
    ):
        with pytest.raises(TypeError, match=field_name):
            replace(base, **{field_name: object()})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="interface_frame"):
        replace(base, interface_frame=cast(ExactInterfaceFrame, object()))
    with pytest.raises(TypeError, match="physical_geometry"):
        replace(base, physical_geometry=cast(MultiRowPhysicalGeometryContext, object()))
    with pytest.raises(TypeError, match="direct_demand_plan"):
        replace(base, direct_demand_plan=cast(MultiRowDemandPlan, object()))
    with pytest.raises(TypeError, match="method_applicability"):
        replace(base, method_applicability=cast(MultiRowMethodApplicability, object()))
    with pytest.raises(TypeError, match="qualification"):
        replace(base, qualification=cast(QualificationDisposition, object()))
    with pytest.raises(TypeError, match="versions"):
        replace(base, versions=cast(Slice3VersionContext, object()))
    with pytest.raises(TypeError, match="origin"):
        replace(_frame(), origin=cast(ExactQuantityVector3D, object()))


def test_canonicalizer_covers_integer_and_plain_enum_values() -> None:
    assert demand_module._canonicalize(7) == "7"
    assert (
        demand_module._canonicalize(DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY)
        == DemandAnalysisMethod.RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY.value
    )


def test_canonicalizer_rejects_binary_float_and_unknown_values() -> None:
    base = _input()
    object.__setattr__(
        base.interface_frame,
        "u",
        cast(tuple[Decimal, Decimal, Decimal], (1.0, Decimal(0), Decimal(0))),
    )
    with pytest.raises(TypeError, match="binary floats"):
        eccentric_demand_input_fingerprint(base)
    clean = _input()
    object.__setattr__(clean, "source_trace", cast(tuple[str, ...], (object(),)))
    with pytest.raises(TypeError, match="Unsupported demand fingerprint"):
        eccentric_demand_input_fingerprint(clean)


def test_slice_3_engine_is_pure_demand_only_and_has_no_integration_or_golden_access() -> None:
    repository_root = Path(__file__).parents[3]
    source_path = (
        repository_root
        / "backend"
        / "src"
        / "frp_master_connection"
        / "calculation"
        / "eccentric_demand.py"
    )
    source = source_path.read_text(encoding="utf-8")
    forbidden_production_tokens = (
        "calculate_multirow_connection",
        "bolt_shear_resistance",
        "block_shear_resistance",
        "tests.golden",
        "calculation_slice_3_rc1.json",
        "frp_master_connection.api",
        "frp_master_connection.application",
        "random.",
        "datetime.now",
        "open(",
        "socket",
    )
    assert all(token not in source for token in forbidden_production_tokens)
    application_path = (
        repository_root / "backend/src/frp_master_connection/application/multirow_orchestration.py"
    )
    application_source = application_path.read_text(encoding="utf-8")
    assert application_source.count("calculate_eccentric_bolt_group_demand") == 2
    api_sources = tuple((repository_root / "backend/src/frp_master_connection/api").rglob("*.py"))
    frontend_sources = tuple((repository_root / "frontend" / "src").rglob("*"))
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (*api_sources, *frontend_sources)
        if path.is_file()
    )
    assert "calculate_eccentric_bolt_group_demand" not in combined
