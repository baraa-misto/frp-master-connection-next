"""Reject ambiguous native ownership rather than assigning an SS body capacity."""

from dataclasses import replace
from typing import Any

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.stainless_activation import (
    serialize_activation_value,
    stainless_design_response,
)
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_moment_ownership import moment_check_partition
from frp_master_connection.application.stainless_native_results import (
    authoritative_multirow_results,
    native_row_partition,
    own_multirow_results,
)
from frp_master_connection.application.stainless_public_authority import _native_input
from frp_master_connection.application.stainless_splice_ownership import splice_check_partition
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole
from tests.api.test_connector_materials import native_payload


@pytest.fixture
def clip() -> tuple[Any, Any, Any]:
    design: Any = FAMILIES["clip-angle"].design(native_payload("clip-angle"))
    assembly = canonical_material_assembly("clip-angle", design.preview)
    return design, assembly, design.interface_a.resistance


def test_missing_final_results_are_not_invented(clip: tuple[Any, Any, Any]) -> None:
    _, assembly, response = clip
    empty = replace(
        response,
        automatic_group_mode_integration=None,
        automatic_handoff_results=(),
        calculation_result=None,
    )
    assert authoritative_multirow_results(empty) == ()
    assert (
        own_multirow_results(
            assembly,
            "A",
            replace(empty, preview=replace(empty.preview, visualization=None)),
            bolt_group_id="A",
        )
        == ()
    )


@pytest.mark.parametrize("case", ["alias", "scene", "layers", "layer"])
def test_layer_binding_ambiguities_fail_closed(clip: tuple[Any, Any, Any], case: str) -> None:
    _, assembly, response = clip
    aliases: tuple[tuple[str, str], ...] = ()
    scene = response.preview.visualization
    assert scene is not None
    if case == "alias":
        aliases = (("a", "b"), ("a", "c"))
    elif case == "scene":
        response = replace(response, preview=replace(response.preview, visualization=None))
    elif case == "layers":
        response = replace(
            response,
            preview=replace(
                response.preview, visualization=replace(scene, layers=scene.layers * 2)
            ),
        )
    else:
        response = replace(
            response, preview=replace(response.preview, visualization=replace(scene, layers=()))
        )
    with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED"):
        own_multirow_results(assembly, "A", response, bolt_group_id="A", component_aliases=aliases)


def test_hardware_ownership_needs_actual_unique_physical_bolt(
    clip: tuple[Any, Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, assembly, response = clip
    from frp_master_connection.application import stainless_native_results as module

    original = authoritative_multirow_results(response)[0][1]
    bolt = replace(
        original,
        layer_id=None,
        bolt_id="BOLT_TEST",
        limit_state=type(original.limit_state)("BOLT_SHEAR"),
    )
    monkeypatch.setattr(module, "authoritative_multirow_results", lambda _: (("CASE", bolt),))
    hardware = CanonicalComponent(
        "HARDWARE:A:BOLT_TEST", ComponentRole.FASTENER_OR_HARDWARE, "BOLT"
    )
    exact = replace(assembly, components=(*assembly.components, hardware))
    result = own_multirow_results(exact, "A", response, bolt_group_id="A")
    assert result[0].owner == hardware
    assert result[0].result is bolt
    fallback = replace(hardware, physical_id="HARDWARE:LEGACY:BOLT_TEST")
    unique = replace(assembly, components=(*assembly.components, fallback))
    assert own_multirow_results(unique, "A", response, bolt_group_id="A")[0].owner == fallback
    with pytest.raises(ValueError, match="NO_HARDWARE"):
        own_multirow_results(assembly, "A", response, bolt_group_id="A")
    malformed = replace(original, layer_id=None, bolt_id=None)
    monkeypatch.setattr(module, "authoritative_multirow_results", lambda _: (("CASE", malformed),))
    with pytest.raises(ValueError, match="NO_LAYER"):
        own_multirow_results(assembly, "A", response, bolt_group_id="A")


def test_unreviewed_families_and_nonfinite_trace_are_rejected(clip: tuple[Any, Any, Any]) -> None:
    _, assembly, _ = clip
    for partition in (native_row_partition, splice_check_partition, moment_check_partition):
        with pytest.raises(ValueError, match="FAMILY_NOT_REVIEWED"):
            partition(assembly, object())
    with pytest.raises(ValueError, match="NOT_APPLICABLE_TO_ROUTE"):
        stainless_design_response("single-bolt", object())
    with pytest.raises(ValueError, match="PREVIEW_REQUIRED"):
        stainless_design_response("clip-angle", object())
    for value in (float("inf"), float("-inf"), float("nan")):
        with pytest.raises(ValueError, match="NONFINITE_NATIVE_TRACE"):
            serialize_activation_value(value)


def test_independent_moment_is_not_added_through_a_second_native_path(
    clip: tuple[Any, Any, Any],
) -> None:
    design, _, _ = clip
    assert _native_input(None) is None
    demand = design.preview.interface_a.demand
    assert demand is not None
    moment = replace(
        demand.original_independent_connection_moments, x=PhysicalQuantity.of(1, Unit.KIP_IN)
    )
    assert _native_input(replace(demand, original_independent_connection_moments=moment)) is None


@pytest.mark.parametrize(
    "route", ["wi-major-axis-moment-splice", "channel-major-axis-moment-splice"]
)
@pytest.mark.parametrize("change", ["unknown", "orphan"])
def test_splice_summary_namespace_and_orphan_failures_are_rejected(route: str, change: str) -> None:
    design: Any = FAMILIES[route].design(native_payload(route))
    assembly = canonical_material_assembly(route, design.preview)
    summary = next(c for c in design.local_checks if c.component_id != "WEB_SUBSYSTEM")
    broken = (
        replace(summary, component_id="UNKNOWN")
        if change == "unknown"
        else replace(summary, failed_check_ids=("ORPHAN",))
    )
    with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED"):
        splice_check_partition(assembly, replace(design, local_checks=(broken,)))


def test_duplicate_moment_check_does_not_double_count() -> None:
    route = "wi-beam-concrete-wall-moment"
    design: Any = FAMILIES[route].design(native_payload(route))
    assembly = canonical_material_assembly(route, design.preview)
    with pytest.raises(ValueError, match="DUPLICATE_REQUIRED_CHECK"):
        moment_check_partition(assembly, replace(design, local_checks=design.local_checks * 2))


def test_native_base_source_present_checks_retain_exact_ownership() -> None:
    from frp_master_connection.application.angle_column_base_design import (
        evaluate_angle_column_moment_base,
    )
    from tests.application.test_angle_column_moment_base import request, synthetic_response

    r = replace(request(), response_source_reference="TEST_ONLY_BASE_RESPONSE")
    _, sources = synthetic_response(r)
    design = evaluate_angle_column_moment_base(r, sources)
    assembly = canonical_material_assembly("angle-column-two-leg-moment-base", design.preview)
    partition = moment_check_partition(assembly, design)
    assert len(partition.retained_non_body) + len(partition.superseded_frp_body) == (
        len(design.local_checks)
        + len(design.member_bolts)
        + len(design.member_attachment_results)
        + (design.local_zone is not None)
    )
    assert design.local_checks


def test_defensive_empty_body_and_no_resistance_paths(
    clip: tuple[Any, Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.application import stainless_connection_design as connection

    design, assembly, _ = clip
    no_body = replace(
        assembly,
        components=tuple(
            c for c in assembly.components if c.role is not ComponentRole.CONNECTOR_BODY
        ),
    )
    monkeypatch.setattr(connection, "canonical_material_assembly", lambda *_: no_body)
    with pytest.raises(ValueError, match="BODY_IDENTITY_MISMATCH"):
        connection.evaluate_stainless_connection("clip-angle", design.preview)
    empty_design = replace(design, interface_a=replace(design.interface_a, resistance=None))
    native_row_partition(assembly, empty_design)


def test_untyped_column_response_is_rejected() -> None:
    design: Any = FAMILIES["column-base-web-angles"].design(
        native_payload("column-base-web-angles")
    )
    assembly = canonical_material_assembly("column-base-web-angles", design.preview)
    with pytest.raises(ValueError, match="OWNERSHIP_NOT_RESOLVED:WEB_GROUP"):
        native_row_partition(assembly, replace(design, web_group_resistance=object()))


def test_legacy_final_calculation_path_is_retained_verbatim(clip: tuple[Any, Any, Any]) -> None:
    _, _, response = clip
    legacy = replace(response, automatic_group_mode_integration=None, automatic_handoff_results=())
    assert legacy.calculation_result is not None
    assert authoritative_multirow_results(legacy) == tuple(
        ("NATIVE_LEGACY", r) for r in legacy.calculation_result.results
    )
