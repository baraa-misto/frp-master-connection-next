"""Stage 3.2 reusable Tee assembly, orchestration, and status tests."""

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import frp_master_connection.application.tee_orchestration as tee_module
from frp_master_connection.application import (
    TEE_ORCHESTRATION_CONTRACT_VERSION,
    SingleBoltOrchestrationRequest,
    TeeAssemblyStatus,
    TeeBodyResistanceStatus,
    TeeConnectorOrchestrationRequest,
    TeeVectorInput,
    design_check_tee_connector,
    preview_single_bolt_connection,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    Dimension,
    ExistingMetallicBoltEligibilityStatus,
    PhysicalQuantity,
    Unit,
)
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    SelectedSupportFlange,
    TeeSupportRole,
)
from frp_master_connection.geometry import UnitVector3D
from tests.tee_fixtures import build_tee_request


def _invalid_layout_request(
    request: TeeConnectorOrchestrationRequest, change: str
) -> TeeConnectorOrchestrationRequest:
    if change == "a_rows":
        return replace(
            request, interface_a_layout=replace(request.interface_a_layout, pitch=Decimal("9"))
        )
    if change == "b_rows":
        return replace(
            request, interface_b_layout=replace(request.interface_b_layout, pitch=Decimal("9"))
        )
    if change == "a_lines":
        return replace(
            request, interface_a_layout=replace(request.interface_a_layout, gauge=Decimal("5"))
        )
    if change == "b_lines":
        return replace(
            request, interface_b_layout=replace(request.interface_b_layout, gauge=Decimal("7"))
        )
    brace_dimensions = request.brace_dimensions
    assert brace_dimensions is not None
    return replace(request, brace_dimensions=replace(brace_dimensions, width=Decimal("7")))


def test_column_tee_has_two_distinct_physical_interfaces_and_groups() -> None:
    request = build_tee_request()
    first = resolve_tee_connector_request(request)
    second = resolve_tee_connector_request(request)
    preview = preview_tee_connector(request)

    assert first.context.assembly.connector_components[0].id == "tee-connector"
    assert len(first.context.assembly.interfaces) == 2
    assert len(first.context.assembly.bolt_groups) == 2
    assert first.interface_a_request is not first.interface_b_request
    assert first.interface_a_request.physical_connection_request is not None
    assert first.interface_b_request.physical_connection_request is not None
    assert preview.engineering_fingerprint == preview_tee_connector(request).engineering_fingerprint
    assert first.context == second.context
    assert preview.visualization is not None
    assert len(preview.visualization.interface_a_bolts) == 4
    assert len(preview.visualization.interface_b_bolts) == 4
    assert {item.bolt_group_id for item in preview.visualization.interface_a_bolts} == {
        "tee-bolt-group-a"
    }
    assert {item.bolt_group_id for item in preview.visualization.interface_b_bolts} == {
        "tee-bolt-group-b"
    }
    assert preview.visualization.interface_a_bolts[0].axis == UnitVector3D(0.0, -1.0, 0.0)
    assert preview.visualization.interface_b_bolts[0].axis == UnitVector3D(-1.0, 0.0, 0.0)
    assert "STEM" in preview.visualization.interface_a_bolts[0].holes[1].physical_element_id
    assert "FLANGE" in preview.visualization.interface_b_bolts[0].holes[0].physical_element_id
    assert preview.visualization.selected_support_surface_id.endswith("TOP_FLANGE:OUTER_TT_BROAD")


@pytest.mark.parametrize(
    ("role", "flange", "expected_axis", "surface_fragment"),
    [
        ("COLUMN", "NEGATIVE_LOCAL_Z", (1.0, 0.0, 0.0), "BOTTOM_FLANGE"),
        ("BEAM", "POSITIVE_LOCAL_Z", (0.0, 0.0, -1.0), "TOP_FLANGE"),
        ("BEAM", "NEGATIVE_LOCAL_Z", (0.0, 0.0, 1.0), "BOTTOM_FLANGE"),
    ],
)
def test_support_role_and_selected_physical_flange_transform_same_tee(
    role: str,
    flange: str,
    expected_axis: tuple[float, float, float],
    surface_fragment: str,
) -> None:
    request = build_tee_request(role=role, selected_flange=flange)
    preview = preview_tee_connector(request)

    assert preview.support_role.value == role
    assert preview.selected_support_flange.value == flange
    assert preview.visualization is not None
    axis = preview.visualization.interface_b_bolts[0].axis
    assert (axis.x, axis.y, axis.z) == expected_axis
    assert surface_fragment in preview.visualization.selected_support_surface_id
    tee_boxes = tuple(
        item
        for item in preview.visualization.base_connection.primitives
        if item.owner_id == "tee-connector"
    )
    assert {item.physical_element_id for item in tee_boxes if item.physical_element_id} == {
        "FLANGE",
        "STEM",
    }


def test_independent_layouts_move_only_their_own_bolts_and_fingerprint() -> None:
    base = build_tee_request()
    base_preview = preview_tee_connector(base)
    changed_a = replace(
        base,
        interface_a_layout=replace(base.interface_a_layout, pitch=Decimal("2.5")),
    )
    changed_b = replace(
        base,
        interface_b_layout=replace(base.interface_b_layout, gauge=Decimal("1.5")),
    )
    preview_a = preview_tee_connector(changed_a)
    preview_b = preview_tee_connector(changed_b)

    assert base_preview.visualization is not None
    assert preview_a.visualization is not None
    assert preview_b.visualization is not None
    assert preview_a.visualization.interface_a_bolts != base_preview.visualization.interface_a_bolts
    assert preview_a.visualization.interface_b_bolts == base_preview.visualization.interface_b_bolts
    assert preview_b.visualization.interface_a_bolts == base_preview.visualization.interface_a_bolts
    assert preview_b.visualization.interface_b_bolts != base_preview.visualization.interface_b_bolts
    assert (
        len(
            {
                base_preview.engineering_fingerprint,
                preview_a.engineering_fingerprint,
                preview_b.engineering_fingerprint,
            }
        )
        == 3
    )


def test_material_authority_is_exact_and_strength_is_not_inferred() -> None:
    preview = preview_tee_connector(build_tee_request())
    authority = preview.material_authority

    assert authority.connector_material_family.value == "PULTRUDED_FRP"
    assert authority.fastener_material_family.value == "STAINLESS_STEEL_316"
    assert authority.fastener_snapshot_id == "ASTM_F593_17_GROUP_2_316_316L"
    assert (
        authority.metallic_bolt_eligibility.status
        is ExistingMetallicBoltEligibilityStatus.BLOCKED_EXPLICIT_FNT_REQUIRED
    )
    assert authority.metallic_bolt_eligibility.eligible_snapshot is None


def test_global_reference_and_action_are_preserved_for_both_interface_transforms() -> None:
    request = build_tee_request(
        force=("0", "0", "3"),
        moment=("1", "2", "3"),
        reference=("2.5", ".1875", "-2"),
    )
    resolved = resolve_tee_connector_request(request)

    assert resolved.context.basis.joint_frame.origin.x == 2.5
    assert resolved.context.basis.joint_frame.origin.y == 0.1875
    assert resolved.context.basis.joint_frame.origin.z == -2.0
    for interface_request in (resolved.interface_a_request, resolved.interface_b_request):
        physical = interface_request.physical_connection_request
        assert physical is not None
        action = physical.assembly.member_end_actions[0]
        assert (action.force.fx, action.force.fy, action.force.fz) == (0.0, 0.0, 3.0)
        assert (action.moment.mx, action.moment.my, action.moment.mz) == (1.0, 2.0, 3.0)


def test_nonzero_normal_action_is_retained_without_generated_axis_tension() -> None:
    preview = preview_tee_connector(build_tee_request(force=("0", "1", "3")))

    assert preview.interface_a.normal_component is not None
    assert preview.interface_a.normal_component.to(Unit.KIP).magnitude == Decimal("-1.0")
    assert preview.interface_a.normal_action_supported is False
    assert preview.interface_a.automatic_axis_tension_generated is False
    assert preview.interface_b.normal_component is not None
    assert preview.interface_b.normal_component.magnitude == 0
    assert preview.ordinary_pass_allowed is False
    assert any("INTERFACE_NORMAL_ACTION_NOT_SUPPORTED" in item for item in preview.warnings)


def test_tee_body_limitation_prevents_pass_and_supported_failure_governs() -> None:
    no_failure = design_check_tee_connector(build_tee_request(force=("0", "0", ".001")))
    failure = design_check_tee_connector(build_tee_request(force=("0", "0", "3")))

    assert no_failure.tee_body_resistance_status is TeeBodyResistanceStatus.NOT_EVALUATED
    assert no_failure.supported_interface_failure_present is False
    assert no_failure.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert no_failure.ordinary_pass_allowed is False
    assert failure.supported_interface_failure_present is True
    assert failure.assembly_status is TeeAssemblyStatus.FAIL
    assert failure.ordinary_pass_allowed is False
    assert failure.interface_a.design is not None
    assert failure.interface_b.design is not None
    assert (
        failure.result_fingerprint
        == design_check_tee_connector(build_tee_request(force=("0", "0", "3"))).result_fingerprint
    )


def test_column_and_beam_equivalent_local_actions_have_equal_demands() -> None:
    column = preview_tee_connector(build_tee_request(force=("0", "0", "3")))
    beam = preview_tee_connector(build_tee_request(role="BEAM", force=("3", "0", "0")))

    for column_interface, beam_interface in (
        (column.interface_a, beam.interface_a),
        (column.interface_b, beam.interface_b),
    ):
        column_demand = column_interface.preview.automatic_demand_result
        beam_demand = beam_interface.preview.automatic_demand_result
        assert column_demand is not None
        assert beam_demand is not None
        assert column_demand.projected_force.u == beam_demand.projected_force.u
        assert column_demand.projected_force.v == beam_demand.projected_force.v
        assert tuple(
            (item.total_force.u, item.total_force.v) for item in column_demand.scenarios[0].per_bolt
        ) == tuple(
            (item.total_force.u, item.total_force.v) for item in beam_demand.scenarios[0].per_bolt
        )
    assert column.engineering_fingerprint != beam.engineering_fingerprint


def test_request_and_vector_validation_fail_closed() -> None:
    request = build_tee_request()
    with pytest.raises(TypeError, match="TeeConnectorOrchestrationRequest"):
        resolve_tee_connector_request(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="request_id"):
        replace(request, request_id=" ")
    with pytest.raises(ValueError, match="contract version"):
        replace(request, orchestration_contract_version="wrong")
    with pytest.raises(ValueError, match="in or mm"):
        replace(request, source_length_unit=Unit.ONE)
    with pytest.raises(ValueError, match="match"):
        replace(request, unit_system=EngineeringUnitSystem.SI)
    with pytest.raises(ValueError, match="positive length"):
        replace(request, bolt_diameter=PhysicalQuantity.of(0, Unit.IN))
    with pytest.raises(ValueError, match="positive length"):
        replace(request, bolt_diameter=PhysicalQuantity.of(1, Unit.KIP))
    with pytest.raises(ValueError, match="contain forces"):
        replace(request, global_force=request.global_reference_point)
    with pytest.raises(ValueError, match="contain moments"):
        replace(request, global_moment=request.global_reference_point)
    with pytest.raises(ValueError, match="contain lengths"):
        replace(request, global_reference_point=request.global_force)
    with pytest.raises(TypeError, match="physical quantities"):
        TeeVectorInput(request.global_force.x, request.global_force.y, object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="share one dimension"):
        TeeVectorInput(request.global_force.x, request.global_force.y, request.bolt_diameter)


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("a_rows", "Interface A rows"),
        ("b_rows", "Interface B rows"),
        ("a_lines", "Interface A bolt lines"),
        ("b_lines", "Interface B bolt lines"),
        ("brace", "connected brace plate"),
    ],
)
def test_layout_containment_validation(change: str, error: str) -> None:
    request = build_tee_request()
    with pytest.raises(ValueError, match=error):
        _invalid_layout_request(request, change)


def test_contract_identity_and_quantity_dimensions_are_explicit() -> None:
    request = build_tee_request()
    assert request.orchestration_contract_version == TEE_ORCHESTRATION_CONTRACT_VERSION
    assert request.global_force.x.dimension is Dimension.FORCE
    assert request.global_moment.x.dimension is Dimension.MOMENT
    assert request.global_reference_point.x.dimension is Dimension.LENGTH
    assert request.support_role is TeeSupportRole.COLUMN
    assert request.selected_support_flange is SelectedSupportFlange.POSITIVE_LOCAL_Z


def test_internal_invariant_guards_fail_closed() -> None:
    request = build_tee_request()
    resolved = resolve_tee_connector_request(request)
    with pytest.raises(ValueError, match="Expected one surface"):
        tee_module._surface((), "missing", "missing")
    physical = resolved.interface_a_request.physical_connection_request
    assert isinstance(physical, SingleBoltOrchestrationRequest)
    with (
        patch.object(
            tee_module,
            "resolve_legacy_material_pair",
            return_value=SimpleNamespace(legacy_pair=ConnectedMaterialPair.FRP_STEEL),
        ),
        pytest.raises(RuntimeError, match="legacy mapping changed"),
    ):
        tee_module._multirow_request(
            request,
            "test-interface",
            request.interface_a_layout,
            physical,
            (),
        )


def test_preview_retains_fail_closed_result_when_physical_visualization_is_missing() -> None:
    request = build_tee_request()
    resolved = resolve_tee_connector_request(request)
    physical = resolved.interface_a_request.physical_connection_request
    assert isinstance(physical, SingleBoltOrchestrationRequest)
    real_preview = preview_single_bolt_connection(physical)
    missing = replace(real_preview, visualization=None)
    with patch.object(tee_module, "preview_single_bolt_connection", return_value=missing):
        preview = tee_module._preview_result(resolved)
        design = design_check_tee_connector(request)

    assert preview.visualization is None
    assert preview.assembly_status is TeeAssemblyStatus.INVALID_GEOMETRY
    assert preview.design_check_ready is False
    assert design.assembly_status is TeeAssemblyStatus.INVALID_GEOMETRY
    assert design.supported_interface_failure_present is False


def test_expansion_and_canonical_helpers_cover_absent_and_transport_shapes() -> None:
    resolved = resolve_tee_connector_request(build_tee_request())
    physical = resolved.interface_a_request.physical_connection_request
    assert isinstance(physical, SingleBoltOrchestrationRequest)
    base = preview_single_bolt_connection(physical)
    assert (
        tee_module._expanded_bolts(
            replace(base, visualization=None),
            resolved.request.interface_a_layout,
            "A",
        )
        == ()
    )
    assert tee_module._canonical(1.25) == "1.25"


def test_unexpected_interface_evaluation_error_is_not_suppressed() -> None:
    resolved = resolve_tee_connector_request(build_tee_request())
    with (
        patch.object(
            tee_module, "evaluate_multirow_connection", side_effect=ValueError("unexpected")
        ),
        pytest.raises(ValueError, match="unexpected"),
    ):
        tee_module._evaluate_interface(resolved.interface_a_request)
