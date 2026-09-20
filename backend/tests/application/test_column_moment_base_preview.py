"""Stage 4.5 360-case source-absent physical/reference/status sweep."""

import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.application.column_moment_base_design import evaluate_column_moment_base
from frp_master_connection.application.column_moment_base_preview import preview_column_moment_base
from frp_master_connection.application.column_moment_base_sources import EMPTY_SOURCES
from frp_master_connection.application.wi_wall_moment_geometry import _bounds, inch, xyz
from frp_master_connection.calculation.angle_column_base_response import ZERO
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.column_moment_base import (
    PRESETS,
    ColumnMomentActions,
    ColumnMomentBaseRequest,
    Face,
    Family,
    Layout,
    default_column_moment_base_request,
    default_column_moment_base_ui_request,
)

MATRIX: dict[str, Any] = json.loads(
    (Path(__file__).parents[1] / "golden/stage_4_5_acceptance_matrix_rc1.json").read_text()
)
LOADS = {v["id"]: v for v in MATRIX["load_cases"]}
LAYOUTS: tuple[Layout, ...] = ("TWO_X", "TWO_Y", "FOUR_XY")


@pytest.mark.parametrize("family", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("offset", ["0", ".25", "-.25"])
@pytest.mark.parametrize("translation", [("0", "0"), ("1", "-.5")])
def test_r2_centered_faces_offsets_hardware_and_units(
    family: Family, layout: Layout, offset: str, translation: tuple[str, str]
) -> None:
    previews = []
    for si in (False, True):
        r = default_column_moment_base_ui_request(family, layout, si=si)

        def q(value: str, target: Unit = Unit.MM if si else Unit.IN) -> PhysicalQuantity:
            return PhysicalQuantity.of(value, Unit.IN).to(target)

        r = replace(
            r,
            column=replace(r.column, offset_x=q(translation[0]), offset_y=q(translation[1])),
            x_positive=replace(r.x_positive, extrusion_center=q(offset)),
            x_negative=replace(r.x_negative, extrusion_center=q(offset)),
            y_positive=replace(r.y_positive, extrusion_center=q(offset)),
            y_negative=replace(r.y_negative, extrusion_center=q(offset)),
        )
        p = preview_column_moment_base(r)
        previews.append(p)
        g = p.geometry
        assert g.status == "VALID", g.reasons
        assert {a.connector_id for a in g.angles} == set(r.active_faces)
        assert len(g.foundation_attachments) == len(r.active_faces)
        expected_shanks = 2 if layout == "TWO_X" else 4 if layout == "TWO_Y" else 6
        if family != "WI":
            expected_shanks = 4 if layout == "FOUR_XY" else 2
        assert len(g.member_bolts) == expected_shanks
        assert len({b.hardware_id for b in g.member_bolts}) == expected_shanks
        assert all(
            face in r.active_faces for b in g.member_bolts for face, _ in b.connector_bolt_ids
        )
        for a in g.angles:
            face = cast(Face, a.connector_id)
            v = r.physical_connector(face)
            tangent = a.frame.a
            center = xyz(a.heel)
            # All three accepted symmetric profiles have tangential face midlines
            # at their translated section center, independently of the pedestal.
            origin = (Decimal(translation[0]), Decimal(translation[1]), Decimal(0))
            displacement = sum((center[i] - origin[i]) * tangent[i] for i in range(3))
            assert displacement == inch(v.extrusion_center)
            assert (v.angle.member_pattern.across, v.angle.member_pattern.along) == (2, 1)
            for part in g.parts:
                if part.box.component_id != face:
                    continue
                lo, hi = _bounds(part)
                middle = tuple((lo[i] + hi[i]) / 2 for i in range(3))
                assert sum((middle[i] - center[i]) * tangent[i] for i in range(3)) == 0
                assert sum((hi[i] - lo[i]) * abs(tangent[i]) for i in range(3)) == inch(
                    v.angle.geometry.length
                )
            bolts = [b for b in g.member_bolts if any(f == face for f, _ in b.connector_bolt_ids)]
            assert len(bolts) == 2
            positions = sorted(
                sum((xyz(b.start)[i] - center[i]) * tangent[i] for i in range(3)) for b in bolts
            )
            assert positions == [
                -inch(v.angle.member_pattern.gauge) / 2,
                inch(v.angle.member_pattern.gauge) / 2,
            ]
            assert len({inch(b.start.z) for b in bolts}) == 1
            assert all(len(b.connector_bolt_ids) == (2 if r.shared(face) else 1) for b in bolts)
            anchors = [
                b for b in g.foundation_attachments if b.group_id == face + "_FOUNDATION_GROUP"
            ]
            assert len(anchors) == 1
            assert sum((xyz(anchors[0].start)[i] - center[i]) * tangent[i] for i in range(3)) == 0
        assert g.minimum_member_axis_distance_squared_in2 is not None
        assert g.minimum_member_axis_distance_squared_in2 >= Decimal(".563") ** 2
    assert previews[0].engineering_fingerprint == previews[1].engineering_fingerprint


def request(
    preset: str = "WI12",
    layout: Layout = "FOUR_XY",
    load: str = "COMBINED_COMPRESSION",
    *,
    si: bool = False,
) -> ColumnMomentBaseRequest:
    data = LOADS[load]
    quantities = []
    for name in ("N_kip", "Vx_kip", "Vy_kip", "Mx_kip_in", "My_kip_in", "Mz_kip_in"):
        moment = name.endswith("_in")
        q = PhysicalQuantity.of(data[name], Unit.KIP_IN if moment else Unit.KIP)
        quantities.append(q.to(Unit.KN_MM if moment else Unit.KN) if si else q)
    return replace(
        default_column_moment_base_request(preset, layout, si=si),
        actions=ColumnMomentActions(*quantities),
    )


@pytest.mark.parametrize("preset", tuple(PRESETS))
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("load", tuple(LOADS))
@pytest.mark.parametrize("si", [False, True])
def test_360_source_absent_sweep(preset: str, layout: Layout, load: str, si: bool) -> None:
    r = request(preset, layout, load, si=si)
    p = preview_column_moment_base(r)
    assert p.geometry.status == "VALID", p.geometry.reasons
    assert len(p.geometry.angles) == (4 if layout == "FOUR_XY" else 2)
    assert p.required_total_foundation_action == shift_angle_wrench(
        p.column_on_base, p.required_total_foundation_action.reference
    )
    assert components(p.column_on_base.force) == tuple(
        Fraction(q.canonical_magnitude)
        for q in (r.actions.shear_x, r.actions.shear_y, r.actions.axial)
    )
    assert components(p.column_on_base.moment) == tuple(
        Fraction(q.canonical_magnitude)
        for q in (r.actions.moment_x, r.actions.moment_y, r.actions.applied_torque_z)
    )
    assert p.column_on_base.reference == p.geometry.column_centroid
    assert components(p.geometry.column_centroid) == ZERO
    assert p.exact_total_transport
    assert not p.resistance_evaluated
    assert not p.ordinary_whole_connection_pass_allowed
    assert p.foundation_strength_status == "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    assert p.overall_column_status == "NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY"
    assert p.geometry.symmetry_allocation == "NO_AUTOMATIC_LOAD_SHARING_AUTHORITY"
    assert p.geometry.column_upper_failure_boundary == "NOT_DEFINED_BY_VIEW_EXTENT"
    assert len({b.hardware_id for b in p.geometry.member_bolts}) == len(p.geometry.member_bolts)
    assert {e.bolt_id for e in p.geometry.member_hardware_envelopes} == {
        b.hardware_id for b in p.geometry.member_bolts
    }
    for b in p.geometry.member_bolts:
        assert not b.blind
        assert b.start != b.end
        assert len(b.connector_bolt_ids) == (
            2 if r.shared(cast(Face, b.connector_bolt_ids[0][0])) else 1
        )
        if r.column.family == "RHS":
            assert len(b.layers) == 5
            assert "CAVITY" in b.layers
            domain = next(
                d for d in p.response_binding.physical_bolts if d.bolt_id == b.hardware_id
            )
            assert len(domain.layers) == 4
            assert all(layer_item.layer_id != "CAVITY" for layer_item in domain.layers)
        elif r.column.family == "SRS":
            assert len(b.layers) == 3
    if layout == "FOUR_XY":
        assert p.geometry.minimum_member_axis_distance_squared_in2 is not None
        assert p.geometry.minimum_member_axis_distance_squared_in2 >= Decimal(1)
    d = evaluate_column_moment_base(r)
    assert not d.resistance_evaluated
    assert not d.failed_check_ids
    assert not d.member_bolts
    assert not d.local_checks
    if load == "ZERO":
        assert p.branch_allocation_status == d.status == "NOT_REQUIRED_ZERO_DEMAND"
        assert len(p.transfers) == len(r.active_faces)
        assert all(
            components(t.core.heel.force) == components(t.core.heel.moment) == ZERO
            for t in p.transfers
        )
        assert p.direct_column_contact is not None
        assert p.assembled_foundation_action == p.required_total_foundation_action
    else:
        assert p.branch_allocation_status == d.status == "SOURCE_REQUIRED"
        assert not p.transfers
        assert p.direct_column_contact is None
        assert p.assembled_foundation_action is None
        assert p.response.exact_equilibrium is None
        assert d.missing_sources
    assert not EMPTY_SOURCES.responses
    assert not EMPTY_SOURCES.fasteners
    assert not EMPTY_SOURCES.zones


@pytest.mark.parametrize("preset", tuple(PRESETS))
@pytest.mark.parametrize("layout", LAYOUTS)
def test_native_unit_and_view_identity(preset: str, layout: Layout) -> None:
    r = request(preset, layout)
    a, b = (
        preview_column_moment_base(r),
        preview_column_moment_base(request(preset, layout, si=True)),
    )
    assert a.engineering_fingerprint == b.engineering_fingerprint
    assert a.geometry.fingerprint == b.geometry.fingerprint
    assert a.required_total_foundation_action == b.required_total_foundation_action
    view = preview_column_moment_base(
        replace(r, column=replace(r.column, view_length=PhysicalQuantity.of(35, Unit.IN)))
    )
    assert view.engineering_fingerprint == a.engineering_fingerprint
    assert view.geometry.display_parts != a.geometry.display_parts
    assert view.response_binding == a.response_binding


def test_actual_offsets_generate_torsion_and_no_action_duplication() -> None:
    r = request()
    r = replace(
        r,
        column=replace(
            r.column,
            offset_x=PhysicalQuantity.of(2, Unit.IN),
            offset_y=PhysicalQuantity.of(-1, Unit.IN),
        ),
    )
    p = preview_column_moment_base(r)
    assert tuple(
        q.to(Unit.KIP_IN).magnitude
        for q in (
            p.required_total_foundation_action.moment.x,
            p.required_total_foundation_action.moment.y,
            p.required_total_foundation_action.moment.z,
        )
    ) == (Decimal(80), Decimal(80), Decimal(-1))
    assert components(p.opposite_foundation_reaction.force) == tuple(
        -v for v in components(p.required_total_foundation_action.force)
    )
