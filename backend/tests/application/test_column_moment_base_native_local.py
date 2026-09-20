"""Stipulated source forces exercise native local dispatch, never production sharing."""

from dataclasses import replace
from fractions import Fraction
from typing import cast

import pytest

from frp_master_connection.application.column_moment_base_design import physical_bolt_checks
from frp_master_connection.application.column_moment_base_local import member_local_checks
from frp_master_connection.application.column_moment_base_paths import connector_paths
from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    ColumnMomentTransfer,
    preview_column_moment_base,
)
from frp_master_connection.application.column_moment_base_sources import ColumnMomentSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    QualifiedBaseBranch,
    add,
    global_to_local_wrench,
    opposite,
    sum_wrenches,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    components,
    exact_decimal,
    quantity_vector,
)
from frp_master_connection.calculation.column_moment_base_response import LayerResponse
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.column_moment_base import (
    ColumnMomentActions,
    default_column_moment_base_request,
)
from tests.application.column_moment_base_fixtures import response_sources
from tests.application.test_column_moment_base_preview import request


def constant_response(
    *, longitudinal: bool = True, one: bool = False, nonstandard: bool = False
) -> ColumnMomentPreview:
    r = request("WI12", "TWO_Y")
    for key in ("y_positive", "y_negative"):
        c = getattr(r, key)
        a = c.angle
        if one:
            a = replace(a, member_pattern=replace(a.member_pattern, across=1, along=1))
            c = replace(c, extrusion_center=PhysicalQuantity.of(2, Unit.IN))
        if nonstandard:
            a = replace(
                a, fastener=replace(a.fastener, hole_diameter=PhysicalQuantity.of(".6", Unit.IN))
            )
        r = replace(r, **{key: replace(c, angle=a)})
    r, seed, registry = response_sources(r)
    record = registry.responses[0]
    domains = {b.bolt_id: b for b in seed.response_binding.physical_bolts}
    bolts = []
    for b in record.bolts:
        d = domains[b.bolt_id]
        f = (
            (Fraction(1), Fraction(0), Fraction(0))
            if longitudinal
            else (Fraction(0), Fraction(0), Fraction(1))
        )
        angle = next(leaf for leaf in d.layers if leaf.connector_id is not None)
        column = next(leaf for leaf in d.layers if leaf.connector_id is None)
        action = AngleWrench(
            angle.point, quantity_vector(f, Unit.N), quantity_vector(ZERO, Unit.N_MM)
        )
        receiving = opposite(sum_wrenches((action,), column.point))
        layers = {
            angle.layer_id: LayerResponse(angle.layer_id, action, PhysicalQuantity.of(0, Unit.N)),
            column.layer_id: LayerResponse(column.layer_id, receiving),
        }
        ordered = tuple(layers[leaf.layer_id] for leaf in d.layers)
        running = ZERO
        sections = []
        for layer, section in zip(ordered[:-1], b.sections, strict=True):
            running = add(running, components(layer.action.force))
            sections.append(
                replace(
                    section,
                    force_on_upstream=quantity_vector(running, Unit.N),
                    tensile_demand=PhysicalQuantity.of(0, Unit.N),
                )
            )
        bolts.append(replace(b, layers=ordered, sections=tuple(sections)))
    branches = []
    report = seed.response_binding.required_total.reference
    global_actions = []
    for domain in seed.response_binding.branches:
        total = sum_wrenches(
            tuple(
                leaf.action
                for b in bolts
                for leaf in b.layers
                if leaf.layer_id == domain.connector_id + "_MEMBER_LEG"
            ),
            report,
        )
        global_actions.append(total)
        branches.append(
            QualifiedBaseBranch(
                domain,
                global_to_local_wrench(
                    total, domain.frame, domain.global_heel, domain.local_member_reference
                ),
            )
        )
    total = sum_wrenches(tuple(global_actions), report)
    f, m = components(total.force), components(total.moment)
    assert m[2] == 0

    def q(v: Fraction, u: Unit) -> PhysicalQuantity:
        return PhysicalQuantity(exact_decimal(v), u)

    r = replace(
        r,
        actions=ColumnMomentActions(
            q(f[2], Unit.N),
            q(f[0], Unit.N),
            q(f[1], Unit.N),
            q(m[0], Unit.N_MM),
            q(m[1], Unit.N_MM),
            q(m[2], Unit.N_MM),
        ),
    )
    unqualified = preview_column_moment_base(r)
    record = replace(
        record,
        binding=unqualified.response_binding,
        branches=tuple(branches),
        bolts=tuple(bolts),
        pressure_patches=(),
        contact_inactive_certificate="TEST_INACTIVE",
        column_on_foundation_contact=AngleWrench(
            report, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM)
        ),
    )
    registry = replace(registry, responses=(record,))
    p = preview_column_moment_base(r, registry)
    assert p.response.qualified, p.response.reasons
    return p


@pytest.mark.parametrize(
    ("longitudinal", "one", "nonstandard"),
    [(True, False, False), (False, False, False), (True, True, False), (True, False, True)],
)
def test_actual_constant_source_forces_dispatch_only_native_applicable_checks(
    longitudinal: bool, one: bool, nonstandard: bool
) -> None:
    p = constant_response(longitudinal=longitudinal, one=one, nonstandard=nonstandard)
    checks = member_local_checks(p)
    bearing = [
        c for c in checks if c.method == "NATIVE_ASCE_8_5" and c.layer_id.endswith("MEMBER_LEG")
    ]
    assert bearing
    assert all(c.native_trace is not None for c in bearing)
    assert all(c.status == "PASS" for c in bearing)
    paths = [c for c in checks if c.method in {"FIRST_ROW_NET_TENSION", "INTERROW_SHEAR_OUT"}]
    assert bool(paths) is (longitudinal and not one and not nonstandard)
    if nonstandard:
        assert any(
            c.applicability == "NONSTANDARD_HOLE_LOCAL_PATH_AUTHORITY_REQUIRED" for c in checks
        )


def test_absent_response_never_executes_local_or_bolt_resistance() -> None:
    p = preview_column_moment_base(request())
    assert member_local_checks(p) == ()
    assert physical_bolt_checks(p, ColumnMomentSourceRegistry()) == ()
    # No fabricated transfer is consumed: early absent-response return precedes it.
    assert connector_paths(p, cast(ColumnMomentTransfer, None)) == ()
    with pytest.raises(ValueError, match="Unknown"):
        default_column_moment_base_request("UNKNOWN")


def test_zero_j_candidate_does_not_fabricate_forces_for_independent_free_moment() -> None:
    r = request("RHS8", "TWO_X")
    item = r.x_positive
    r = replace(
        r,
        x_positive=replace(
            item,
            angle=replace(
                item.angle, member_pattern=replace(item.angle.member_pattern, across=1, along=1)
            ),
        ),
    )
    _, p, _ = response_sources(r)
    for transfer in p.transfers:
        assert (
            transfer.in_plane_reference_candidate.status
            == "CALCULATION_NOT_SUPPORTED_ZERO_GROUP_POLAR_SUM"
        )
        assert transfer.in_plane_reference_candidate.solution.projected_bolts() == ()
        assert transfer.in_plane_reference_candidate.solution.centroid_moment != 0
        assert transfer.in_plane_candidate_use == "NOT_OVERLAID_ON_QUALIFIED_COUPLED_BOLT_RESPONSE"
    assert p.response.qualified
    assert p.assembled_foundation_action == p.required_total_foundation_action
