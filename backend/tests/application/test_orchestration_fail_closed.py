"""Fail-closed identity, assignment, geometry, and contract tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application import (
    OrchestrationIssue,
    OrchestrationIssueCode,
    SingleBoltOrchestrationRequest,
    SourceActionOrchestrationTrace,
    evaluate_single_bolt_connection,
)
from frp_master_connection.application.calculation_orchestration import _participant
from frp_master_connection.calculation import (
    DemandDistributionStatus,
    DemandSourceKind,
    EndUseFactors,
    FinalResultAvailability,
    LapConfiguration,
    LimitState,
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    ThreadStatus,
    ThreadStatusAssignment,
    TimeEffectCategory,
    Unit,
    select_time_effect_factor,
)
from frp_master_connection.domain import (
    ComponentMaterialKind,
    EngineeringUnitSystem,
    ParticipantKind,
    ParticipantReference,
)
from frp_master_connection.geometry import Vector3D
from tests.application.orchestration_fixtures import build_j1_case, build_plate_case
from tests.c3_fixtures import build_c3_case
from tests.calculation.test_numerical_golden import _result


def _codes(request: SingleBoltOrchestrationRequest) -> tuple[OrchestrationIssueCode, ...]:
    return tuple(issue.code for issue in evaluate_single_bolt_connection(request).issues)


def test_issue_and_assignment_contracts_reject_invalid_programming_values() -> None:
    with pytest.raises(TypeError, match="OrchestrationIssueCode"):
        OrchestrationIssue("INVALID", "message")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="factual message"):
        OrchestrationIssue(OrchestrationIssueCode.INVALID_GEOMETRY, "")
    with pytest.raises(TypeError, match="immutable tuple"):
        OrchestrationIssue(
            OrchestrationIssueCode.INVALID_GEOMETRY,
            "message",
            [],  # type: ignore[arg-type]
        )

    source = build_plate_case("P1").request.material_assignments[0]
    with pytest.raises(ValueError, match="identities must be nonempty"):
        replace(source, participant_id="")
    invalid_assignments = (
        ("material_snapshot", object(), TypeError),
        ("bearing_thread_status", "EXCLUDED", TypeError),
        ("element_form", "PLATE", TypeError),
        ("potential_perpendicular_element_exemption", 1, TypeError),
    )
    for field, value, error in invalid_assignments:
        with pytest.raises(error):
            replace(source, **{field: value})  # type: ignore[arg-type]


def test_explicit_demand_and_request_contracts_are_narrow_and_typed() -> None:
    source = build_plate_case("P1").request
    assignment = source.resolved_demand
    assert assignment is not None
    with pytest.raises(ValueError, match="target identities"):
        replace(assignment, interface_id="")
    with pytest.raises(TypeError, match="ResolvedSingleBoltDemand"):
        replace(assignment, demand=object())  # type: ignore[arg-type]

    invalid_values: tuple[tuple[str, object, type[Exception]], ...] = (
        ("calculation_id", "", ValueError),
        ("assembly", object(), TypeError),
        ("geometry_context", object(), TypeError),
        ("material_assignments", [], TypeError),
        ("material_assignments", (object(),), TypeError),
        ("fastener_snapshot", object(), TypeError),
        ("bolt_diameter", object(), TypeError),
        ("bolt_diameter", PhysicalQuantity.of("0", Unit.IN), ValueError),
        ("bolt_diameter", PhysicalQuantity.of("1", Unit.KIP), ValueError),
        ("published_code_unit_basis", "US", TypeError),
        ("time_effect", object(), TypeError),
        ("end_use_factors", object(), TypeError),
        ("lap_configuration", "DOUBLE", TypeError),
        ("resolved_demand", object(), TypeError),
        ("source_action_id", "", ValueError),
        ("whole_connection_requires_section_2_3_2", 1, TypeError),
    )
    for field, value, error in invalid_values:
        with pytest.raises(error):
            replace(source, **{field: value})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="SingleBoltOrchestrationRequest"):
        evaluate_single_bolt_connection(object())  # type: ignore[arg-type]


def test_source_action_trace_prohibits_automatic_moment_shift() -> None:
    response = evaluate_single_bolt_connection(build_j1_case(explicit_demand=False).request)
    trace = response.source_action_trace
    assert trace is not None
    with pytest.raises(ValueError, match="automatic moment shift"):
        SourceActionOrchestrationTrace(
            trace.resolved_action,
            trace.selected_bolt_center,
            trace.raw_source_to_bolt_offset,
            True,
        )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("interface_id", "missing-interface", OrchestrationIssueCode.INTERFACE_NOT_FOUND),
        ("bolt_group_id", "missing-group", OrchestrationIssueCode.BOLT_GROUP_NOT_FOUND),
        ("bolt_location_id", "missing-bolt", OrchestrationIssueCode.BOLT_LOCATION_NOT_FOUND),
        (
            "load_combination_id",
            "missing-load",
            OrchestrationIssueCode.LOAD_COMBINATION_NOT_FOUND,
        ),
    ],
)
def test_unknown_target_identities_are_not_repaired(
    field: str,
    value: str,
    expected: OrchestrationIssueCode,
) -> None:
    request = build_plate_case("P1").request
    response = evaluate_single_bolt_connection(
        replace(request, **{field: value})  # type: ignore[arg-type]
    )
    assert response.calculation_result is None
    assert expected in {issue.code for issue in response.issues}


def test_context_and_path_identity_mixing_fails_closed() -> None:
    first = build_plate_case("P1")
    second = build_plate_case("P1")
    mismatch = replace(first.request, assembly=second.request.assembly)
    assert _codes(mismatch) == (OrchestrationIssueCode.JOINT_CONTEXT_MISMATCH,)

    path = first.context.resolved_bolt_groups[0].paths[0]
    definition = path.definition.layers[0]
    object.__setattr__(definition.connection_zones[0], "interface_id", "other-interface")
    codes = _codes(first.request)
    assert OrchestrationIssueCode.BOLT_PATH_NOT_FOUND in codes


def test_source_action_and_resolved_demand_conflicts_are_explicit() -> None:
    request = build_plate_case("P1").request
    assert request.resolved_demand is not None
    assert OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT in _codes(
        replace(request, source_action_id="different-action")
    )
    assert OrchestrationIssueCode.SOURCE_ACTION_NOT_FOUND in _codes(
        replace(request, resolved_demand=None, source_action_id="missing-action")
    )
    derived_action = evaluate_single_bolt_connection(replace(request, source_action_id=None))
    assert derived_action.calculation_result is not None
    assert derived_action.source_action_trace is not None

    no_sources = evaluate_single_bolt_connection(
        replace(request, resolved_demand=None, source_action_id=None)
    )
    assert no_sources.calculation_result is None
    assert OrchestrationIssueCode.RESOLVED_DEMAND_REQUIRED in {
        issue.code for issue in no_sources.issues
    }

    action = request.assembly.member_end_actions[0]
    object.__setattr__(action, "load_combination_id", "other-load")
    assert OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT in _codes(
        replace(request, resolved_demand=None)
    )


def test_demand_target_load_member_and_distribution_conflicts_fail_closed() -> None:
    base = build_plate_case("P1").request
    assignment = base.resolved_demand
    assert assignment is not None
    demand = assignment.demand
    variants = (
        replace(assignment, bolt_location_id="other-bolt"),
        replace(assignment, demand=replace(demand, load_combination_id="other-load")),
        replace(assignment, demand=replace(demand, source_member_id="other-member")),
        replace(
            assignment,
            demand=replace(
                demand,
                source_kind=DemandSourceKind.MEMBER_END_ACTION_UNDISTRIBUTED,
                distribution_status=DemandDistributionStatus.UNRESOLVED,
            ),
        ),
    )
    for variant in variants:
        response = evaluate_single_bolt_connection(replace(base, resolved_demand=variant))
        assert response.calculation_result is None
        assert OrchestrationIssueCode.RESOLVED_DEMAND_CONFLICT in {
            issue.code for issue in response.issues
        }


def test_material_assignment_order_is_irrelevant_but_layer_order_is_authoritative() -> None:
    request = build_plate_case("P2A").request
    reversed_request = replace(
        request,
        material_assignments=tuple(reversed(request.material_assignments)),
    )
    first = evaluate_single_bolt_connection(request)
    second = evaluate_single_bolt_connection(reversed_request)
    assert first == second
    assert tuple(item.layer_id for item in first.resolved_layers) == ("layer-A", "layer-B")


def test_duplicate_missing_mismatched_and_multiple_material_snapshots_fail_closed() -> None:
    request = build_plate_case("P2A").request
    first, second = request.material_assignments
    duplicate = replace(request, material_assignments=(first, first, first))
    duplicate_codes = _codes(duplicate)
    assert duplicate_codes.count(OrchestrationIssueCode.DUPLICATE_MATERIAL_ASSIGNMENT) == 1
    assert OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISSING in _codes(
        replace(request, material_assignments=(first,))
    )
    mismatch = replace(first, participant_id="unknown-participant")
    assert OrchestrationIssueCode.MATERIAL_ASSIGNMENT_MISMATCH in _codes(
        replace(request, material_assignments=(mismatch, second))
    )
    distinct_material = replace(
        second,
        material_snapshot=replace(second.material_snapshot, id="OTHER_MATERIAL"),
    )
    assert OrchestrationIssueCode.MULTIPLE_MATERIAL_SNAPSHOTS_NOT_SUPPORTED in _codes(
        replace(request, material_assignments=(first, distinct_material))
    )


def test_participant_topology_element_region_and_material_kind_failures_are_closed() -> None:
    participant_case = build_plate_case("P2A")
    participant_layer = participant_case.context.resolved_bolt_groups[0].paths[0].layers[0]
    object.__setattr__(
        participant_layer.definition,
        "participant",
        ParticipantReference(ParticipantKind.MEMBER, "missing-member"),
    )
    assert OrchestrationIssueCode.PARTICIPANT_NOT_FOUND in _codes(participant_case.request)

    topology_case = build_plate_case("P2A")
    object.__setattr__(topology_case.request.assembly.members[0], "section_topology", None)
    assert OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND in _codes(topology_case.request)

    element_case = build_plate_case("P2A")
    layers = element_case.context.resolved_bolt_groups[0].paths[0].layers
    object.__setattr__(
        layers[0].physical_element,
        "source_element",
        layers[1].physical_element.source_element,
    )
    assert OrchestrationIssueCode.PHYSICAL_ELEMENT_NOT_FOUND in _codes(element_case.request)

    region_case = build_plate_case("P2A")
    layers = region_case.context.resolved_bolt_groups[0].paths[0].layers
    object.__setattr__(
        layers[0].physical_element,
        "source_material_region",
        layers[1].physical_element.source_material_region,
    )
    assert OrchestrationIssueCode.MATERIAL_REGION_NOT_FOUND in _codes(region_case.request)

    other_case = build_plate_case("P1")
    object.__setattr__(
        other_case.request.assembly.members[0],
        "material_kind",
        ComponentMaterialKind.OTHER,
    )
    other_request = replace(other_case.request, material_assignments=())
    assert OrchestrationIssueCode.UNSUPPORTED_MATERIAL_KIND in _codes(other_request)

    steel_case = build_plate_case("P1")
    object.__setattr__(
        steel_case.request.assembly.members[0],
        "material_kind",
        ComponentMaterialKind.STEEL,
    )
    response = evaluate_single_bolt_connection(replace(steel_case.request, material_assignments=()))
    assert response.aggregate_status is not None
    assert response.aggregate_status.value == "CALCULATION_NOT_SUPPORTED"


def test_missing_region_orientation_component_orientation_and_out_of_plane_force_fail() -> None:
    region_case = build_plate_case("P1")
    region = (
        region_case.context.resolved_bolt_groups[0]
        .paths[0]
        .layers[0]
        .physical_element.source_material_region
    )
    object.__setattr__(region, "orientation", None)
    assert OrchestrationIssueCode.INVALID_GEOMETRY in _codes(region_case.request)

    component_case = build_plate_case("P1")
    object.__setattr__(
        component_case.request.assembly.members[0],
        "material_orientation",
        None,
    )
    assert OrchestrationIssueCode.INVALID_GEOMETRY in _codes(component_case.request)

    force_case = build_plate_case("P1")
    assignment = force_case.request.resolved_demand
    assert assignment is not None
    demand = replace(assignment.demand, in_plane_force_vector=Vector3D(0.0, 0.0, 3.0))
    response = evaluate_single_bolt_connection(
        replace(
            force_case.request,
            resolved_demand=replace(assignment, demand=demand),
        )
    )
    assert response.calculation_result is None
    assert OrchestrationIssueCode.INVALID_GEOMETRY in {issue.code for issue in response.issues}


def test_unequal_code_holes_produce_invalid_geometry_without_repair() -> None:
    case = build_plate_case("P2A")
    second_layer = case.context.resolved_bolt_groups[0].paths[0].layers[1]
    object.__setattr__(second_layer.definition, "hole_diameter", 0.600)
    response = evaluate_single_bolt_connection(case.request)
    assert response.calculation_result is not None
    assert response.aggregate_status is not None
    assert response.aggregate_status.value == "INVALID_GEOMETRY"
    assert OrchestrationIssueCode.INVALID_GEOMETRY in {issue.code for issue in response.issues}
    assert all(result.equation_trace is None for result in response.calculation_result.results)


def test_bearing_and_shear_plane_thread_statuses_remain_independent() -> None:
    base = build_plate_case("B1").request
    included_bearing = replace(
        base.material_assignments[0],
        bearing_thread_status=ThreadStatus.INCLUDED,
    )
    bearing_response = evaluate_single_bolt_connection(
        replace(base, material_assignments=(included_bearing,))
    )
    assert bearing_response.calculation_result is not None
    bearing = _result(
        bearing_response.calculation_result,
        LimitState.PIN_BEARING,
        "layer-A",
    )
    assert bearing.availability is FinalResultAvailability.CALCULATED

    shear_status = replace(
        base.fastener_snapshot,
        shear_plane_thread_statuses=(
            ThreadStatusAssignment("shear-plane-1", ThreadStatus.INCLUDED),
        ),
    )
    shear_response = evaluate_single_bolt_connection(replace(base, fastener_snapshot=shear_status))
    assert shear_response.calculation_result is not None
    shear = _result(shear_response.calculation_result, LimitState.BOLT_SHEAR, None)
    assert shear.availability is FinalResultAvailability.CALCULATED
    assert (
        bearing_response.material_assignments_used[0].bearing_thread_status is ThreadStatus.INCLUDED
    )
    assert (
        shear_response.fastener_snapshot.shear_plane_thread_statuses[0].status
        is ThreadStatus.INCLUDED
    )


def test_component_lookup_covers_member_connector_unknown_and_support() -> None:
    c3 = build_c3_case(pultruded_frp=True)
    member = _participant(
        c3.assembly,
        ParticipantReference(ParticipantKind.MEMBER, "member-1"),
    )
    connector = _participant(
        c3.assembly,
        ParticipantReference(ParticipantKind.CONNECTOR_COMPONENT, "connector-1"),
    )
    unknown = _participant(
        c3.assembly,
        ParticipantReference(ParticipantKind.MEMBER, "missing"),
    )
    support = _participant(
        c3.assembly,
        ParticipantReference(ParticipantKind.SUPPORT, "support"),
    )
    assert member is c3.assembly.members[0]
    assert connector is c3.assembly.connector_components[0]
    assert unknown is None
    assert support is None


def test_request_does_not_mutate_any_canonical_or_snapshot_input() -> None:
    request = build_plate_case("P2A").request
    before = (
        request.assembly,
        request.geometry_context,
        request.material_assignments,
        request.fastener_snapshot,
        request.resolved_demand,
    )
    evaluate_single_bolt_connection(request)
    after = (
        request.assembly,
        request.geometry_context,
        request.material_assignments,
        request.fastener_snapshot,
        request.resolved_demand,
    )
    assert before == after


def test_request_factor_metadata_never_defaults_from_load_name() -> None:
    request = build_plate_case("P1").request
    explicit = replace(
        request,
        time_effect=select_time_effect_factor(TimeEffectCategory.OTHER_LIVE),
        end_use_factors=EndUseFactors(
            Decimal("0.9"),
            Decimal("0.8"),
            Decimal("0.7"),
            "Engineer-issued factors",
            ("Approval E-1",),
        ),
        lap_configuration=LapConfiguration.SINGLE_LAP,
        published_code_unit_basis=PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
        bolt_diameter=PhysicalQuantity.of("0.500", Unit.IN),
    )
    response = evaluate_single_bolt_connection(explicit)
    assert response.calculation_result is not None
    plans = response.calculation_result.planning_result.checks
    assert any("lambda:0.8" in plan.factor_metadata for plan in plans)
    assert any("CM:0.9" in plan.factor_metadata for plan in plans)
    assert response.unit_system is EngineeringUnitSystem.US_CUSTOMARY
