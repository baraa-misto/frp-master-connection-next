"""Stage 4.4 source-absent sweep and test-only complete-response integration."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    preview_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_sources import AngleBaseSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import (
    REQUIRED_COVERAGE,
    ZERO,
    QualifiedBaseBranch,
    QualifiedBaseResponse,
    global_to_local_wrench,
    is_zero,
    validate_base_response,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreRequest,
    AngleWrench,
    components,
    quantity_vector,
    resolve_angle_connector,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseActions,
    AngleColumnMomentBaseRequest,
    default_angle_column_moment_base_request,
)
from tests.calculation.test_support_attachment_response import source

MATRIX: dict[str, Any] = json.loads(
    (Path(__file__).parents[1] / "golden/stage_4_4_acceptance_matrix_rc1.json").read_text(
        encoding="utf-8"
    )
)
LOADS = MATRIX["load_cases"]


def request(
    load_index: int = 13, *, unequal: bool = False, si: bool = False
) -> AngleColumnMomentBaseRequest:
    r = default_angle_column_moment_base_request(unequal=unequal, si=si)
    values = LOADS[load_index]

    def q(value: object, moment: bool = False) -> PhysicalQuantity:
        base = Unit.KIP_IN if moment else Unit.KIP
        target = (Unit.KN_MM if moment else Unit.KN) if si else base
        return PhysicalQuantity.of(str(value), base).to(target)

    return replace(
        r,
        actions=AngleBaseActions(
            q(values["N_kip"]),
            q(values["Vx_kip"]),
            q(values["Vy_kip"]),
            q(values["Mx_kip_in"], True),
            q(values["My_kip_in"], True),
            q(0, True),
        ),
    )


def synthetic_response(
    r: AngleColumnMomentBaseRequest,
) -> tuple[AngleBasePreview, AngleBaseSourceRegistry]:
    """An explicit TEST source allocation, never a production distribution algorithm.

    This particular synthetic fixture assigns the entire action to leg 1 and
    explicitly certifies leg 2/contact inactive. It disproves automatic 50/50.
    Source validity is simulated solely for integration of existing native engines.
    """
    p = preview_angle_column_moment_base(r)
    domains = p.response_binding.branches
    action = global_to_local_wrench(
        p.column_on_base,
        domains[0].frame,
        domains[0].global_heel,
        domains[0].local_member_reference,
    )
    zero = AngleWrench(
        domains[1].local_member_reference,
        quantity_vector(ZERO, Unit.N),
        quantity_vector(ZERO, Unit.N_MM),
    )
    contact = AngleWrench(
        p.required_total_foundation_action.reference,
        quantity_vector(ZERO, Unit.N),
        quantity_vector(ZERO, Unit.N_MM),
    )
    record = QualifiedBaseResponse(
        r.response_source_reference,
        source(),
        "TEST_ONLY_STAGE44_ISSUER",
        p.response_binding,
        (
            QualifiedBaseBranch(domains[0], action, "TEST_ZERO" if is_zero(action) else None),
            QualifiedBaseBranch(domains[1], zero, "TEST_EXPLICIT_INACTIVE_LEG_2"),
        ),
        contact,
        (),
        "TEST_EXPLICIT_NO_COLUMN_CONTACT",
        "TEST_ONLY_COMPATIBILITY_FIXTURE_NOT_PRODUCTION_QUALIFICATION",
        REQUIRED_COVERAGE,
        "EXACT_SINGLE_TEST_ACTION_NO_INTERPOLATION",
    )
    registry = AngleBaseSourceRegistry(responses=(record,))
    return preview_angle_column_moment_base(r, registry), registry


@pytest.mark.parametrize("load_index", range(16))
@pytest.mark.parametrize("unequal", [False, True])
@pytest.mark.parametrize("si", [False, True])
def test_t44_source_absent_64_case_sweep(load_index: int, unequal: bool, si: bool) -> None:
    r = request(load_index, unequal=unequal, si=si)
    p = preview_angle_column_moment_base(r)
    assert p.geometry.status == "VALID", p.geometry.reasons
    assert len(p.geometry.member_bolts) == 8
    assert len(p.geometry.foundation_attachments) == 8
    assert p.exact_total_transport
    assert not p.resistance_evaluated
    assert p.branch_allocation_status == (
        "NOT_REQUIRED_ZERO_DEMAND" if load_index == 0 else "SOURCE_REQUIRED"
    )
    assert not p.transfers if load_index != 0 else len(p.transfers) == 2
    assert p.foundation_strength_status == "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    assert not p.ordinary_whole_connection_pass_allowed
    d = evaluate_angle_column_moment_base(r)
    assert d.status == ("NOT_REQUIRED_ZERO_DEMAND" if load_index == 0 else "SOURCE_REQUIRED")
    assert not d.resistance_evaluated


@pytest.mark.parametrize("load_index", [1, 2, 7, 9, 11, 13])
@pytest.mark.parametrize("unequal", [False, True])
@pytest.mark.parametrize("si", [False, True])
def test_t44_24_qualified_test_only_integrations(load_index: int, unequal: bool, si: bool) -> None:
    r = replace(
        request(load_index, unequal=unequal, si=si),
        response_source_reference="TEST_ONLY_BASE_RESPONSE",
    )
    p, s = synthetic_response(r)
    assert p.response.qualified, p.response.reasons
    assert p.response.exact_equilibrium
    assert len(p.transfers) == 2
    assert components(p.assembled_force_residual) == ZERO  # type: ignore[arg-type]
    assert components(p.assembled_moment_residual) == ZERO  # type: ignore[arg-type]
    for t in p.transfers:
        assert t.native_core_equilibrium
        assert t.core == resolve_angle_connector(
            AngleCoreRequest(
                t.core.request.geometry,
                t.core.request.frame,
                t.core.request.member_action,
                t.core.request.support_reference,
            )
        )
        assert t.in_plane_demand == calculate_in_plane_wrench_demand(t.in_plane_input)
        assert t.member_out_of_plane_f_c_m_a_m_b == (
            t.core.request.member_action.force.z,
            t.core.request.member_action.moment.x,
            t.core.request.member_action.moment.y,
        )
    assert is_zero(p.transfers[1].core.request.member_action)
    assert not is_zero(p.transfers[0].core.request.member_action)
    d = evaluate_angle_column_moment_base(r, s)
    assert d.resistance_evaluated
    assert len(d.connector_results) == 2
    assert len(d.member_responses) == 2
    assert d.missing_sources
    assert not d.ordinary_whole_connection_pass_allowed


def test_native_material_axis_and_view_identity() -> None:
    r = request()
    p = preview_angle_column_moment_base(r)
    edited = preview_angle_column_moment_base(
        replace(r, column=replace(r.column, view_length=PhysicalQuantity.of(50, Unit.IN)))
    )
    assert edited.engineering_fingerprint == p.engineering_fingerprint
    assert edited.geometry.display_parts != p.geometry.display_parts
    assert p.geometry.parts == edited.geometry.parts
    column = [p for p in p.geometry.parts if p.box.component_id == "ANGLE_COLUMN"]
    assert all(
        p.material_region is not None
        and p.material_region.lw_axis == (Decimal(0), Decimal(0), Decimal(1))
        for p in column
    )


def test_test_only_source_does_not_resolve_from_typed_label() -> None:
    r = replace(request(), response_source_reference="TEST_ONLY_BASE_RESPONSE")
    assert preview_angle_column_moment_base(r).branch_allocation_status == "SOURCE_REQUIRED"


def test_qualified_response_rejects_changed_geometry_sign_reference_and_missing_branch() -> None:
    r = replace(request(), response_source_reference="TEST_ONLY_BASE_RESPONSE")
    p, s = synthetic_response(r)
    record = s.responses[0]
    for bad in (
        replace(record, branches=record.branches[:1]),
        replace(record, branches=(record.branches[0], record.branches[0])),
        replace(record, coverage=()),
        replace(record, method="STAGE43_FOUR_GROUP_RESPONSE"),
        replace(record, contact_inactive_certificate=None),
        replace(
            record,
            branches=(
                replace(record.branches[0], inactive_certificate="WRONG_ZERO"),
                record.branches[1],
            ),
        ),
    ):
        checked = validate_base_response(p.response_binding, bad)
        assert not checked.qualified
        assert checked.response is None
        assert checked.status == "NOT_EVALUATED_INVALID_OR_UNQUALIFIED_RESPONSE"
    for changed in (
        replace(r, column=replace(r.column, leg_y=PhysicalQuantity.of(6, Unit.IN))),
        replace(r, actions=replace(r.actions, axial=PhysicalQuantity.of(20, Unit.KIP))),
    ):
        changed_preview = preview_angle_column_moment_base(changed, s)
        assert not changed_preview.response.qualified
        assert not changed_preview.transfers


def test_independent_torque_rejected_but_generated_mz_retained() -> None:
    r = request()
    with pytest.raises(ValueError, match="INDEPENDENT_COLUMN_TORQUE"):
        replace(r.actions, applied_torque_z=PhysicalQuantity.of(1, Unit.KIP_IN))
    p = preview_angle_column_moment_base(r)
    assert p.required_total_foundation_action.moment.z.canonical_magnitude != 0


def test_invalid_geometry_cannot_evaluate_or_manufacture_branch_action() -> None:
    r = request()
    r = replace(r, leg_1=replace(r.leg_1, extrusion_center=PhysicalQuantity.of(-30, Unit.IN)))
    d = evaluate_angle_column_moment_base(r)
    assert d.status == "INVALID_GEOMETRY"
    assert not d.resistance_evaluated
    assert not d.preview.transfers
