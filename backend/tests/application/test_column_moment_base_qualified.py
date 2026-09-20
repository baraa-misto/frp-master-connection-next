"""90 non-mocked complete source-present native integrations; synthetic sources stay in tests."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from typing import cast

import pytest

from frp_master_connection.application.column_moment_base_design import evaluate_column_moment_base
from frp_master_connection.application.column_moment_base_preview import preview_column_moment_base
from frp_master_connection.calculation.angle_column_base_response import ZERO
from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    AngleCoreRequest,
    Decimal3,
    components,
    exact_decimal,
    quantity_vector,
    resolve_angle_connector,
)
from frp_master_connection.calculation.equations import (
    bolt_shear_resistance_from_nominal_stress,
    bolt_tension_resistance,
)
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sourced_bolt_interaction import (
    sourced_combined_bolt_resistance,
)
from frp_master_connection.domain.column_moment_base import PRESETS, Layout
from tests.application.column_moment_base_fixtures import complete_sources
from tests.application.test_column_moment_base_preview import LAYOUTS, request


@pytest.mark.parametrize("preset", tuple(PRESETS))
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("load", ["COMBINED_COMPRESSION", "COMBINED_UPLIFT_REVERSAL", "BIAXIAL"])
@pytest.mark.parametrize("si", [False, True])
def test_90_source_present_integrations(preset: str, layout: Layout, load: str, si: bool) -> None:
    r, p, s = complete_sources(request(preset, layout, load, si=si))
    d = evaluate_column_moment_base(r, s)
    assert p.response.qualified, p.response.reasons
    assert p.response.exact_equilibrium
    assert len(p.transfers) == len(r.active_faces)
    assert p.assembled_foundation_action == p.required_total_foundation_action
    assert p.assembled_force_residual is not None
    assert components(p.assembled_force_residual) == ZERO
    assert p.assembled_moment_residual is not None
    assert components(p.assembled_moment_residual) == ZERO
    assert len(d.connector_results) == len(d.member_attachment_results) == len(r.active_faces)
    assert d.member_bolts
    assert all(b.shear_trace is not None for b in d.member_bolts)
    assert d.local_zone is not None
    assert d.local_zone.comparisons
    assert any(c.native_trace is not None for c in d.local_checks)
    assert not d.missing_sources
    assert d.status in {"FAIL", "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"}
    assert d.resistance_evaluated
    assert not d.ordinary_whole_connection_pass_allowed
    frames = {
        "X_POS": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
        "X_NEG": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
        "Y_POS": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
        "Y_NEG": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    }
    for face, t in zip(r.active_faces, p.transfers, strict=True):
        spec = r.physical_connector(face).angle
        thickness = Fraction(spec.geometry.thickness.canonical_magnitude)
        center = Fraction(spec.member_pattern.center.canonical_magnitude) - thickness / 2
        support = Fraction(spec.support_pattern.center.canonical_magnitude) - thickness / 2
        mr = quantity_vector((Fraction(0), center, -thickness / 2), Unit.MM)
        sr = quantity_vector((Fraction(0), -thickness / 2, support), Unit.MM)
        frame = AngleConnectorFrame(
            *(cast(Decimal3, tuple(Decimal(v) for v in axis)) for axis in frames[face])
        )
        branch = next(
            b.member_action for b in s.responses[0].branches if b.domain.connector_id == face
        )
        oracle = resolve_angle_connector(
            AngleCoreRequest(spec.geometry, frame, replace(branch, reference=mr), sr)
        )
        assert t.core == oracle
        assert t.native_core_equilibrium
        pattern = spec.member_pattern
        bolts = tuple(
            WrenchBolt(
                f"B_R{row + 1}_L{line + 1}",
                exact_decimal(
                    (Fraction(line) - Fraction(pattern.across - 1, 2))
                    * Fraction(pattern.gauge.canonical_magnitude)
                ),
                exact_decimal(
                    center
                    + (Fraction(row) - Fraction(pattern.along - 1, 2))
                    * Fraction(pattern.pitch.canonical_magnitude)
                ),
            )
            for row in range(pattern.along)
            for line in range(pattern.across)
        )
        native = calculate_in_plane_wrench_demand(
            InPlaneWrenchRequest(
                bolts,
                (Decimal(0), exact_decimal(center)),
                branch.force.x.canonical_magnitude,
                branch.force.y.canonical_magnitude,
                branch.moment.z.canonical_magnitude,
                Unit.MM,
                Unit.N,
                Unit.N_MM,
            )
        )
        assert t.in_plane_reference_candidate == native
        assert t.in_plane_candidate_use == "NOT_OVERLAID_ON_QUALIFIED_COUPLED_BOLT_RESPONSE"
        assert t.member_out_of_plane_f_c_m_a_m_b == (
            branch.force.z,
            branch.moment.x,
            branch.moment.y,
        )
    for bolt in d.member_bolts:
        source = bolt.source
        assert source is not None
        assert bolt.shear_magnitude is not None
        physical = next(b for b in p.geometry.member_bolts if b.hardware_id == bolt.bolt_id)
        assert bolt.shear_trace == bolt_shear_resistance_from_nominal_stress(
            physical.diameter, source.nominal_shear_stress
        )
        assert bolt.tension_trace == bolt_tension_resistance(
            physical.diameter, source.nominal_tensile_stress
        )
        assert bolt.combined_trace == sourced_combined_bolt_resistance(
            physical.diameter,
            source.nominal_tensile_stress,
            source.nominal_shear_stress,
            bolt.shear_magnitude,
        )
    assert all(
        proof.passed and components(proof.external_force_sum) == ZERO
        for proof in p.response.coupled_bolt_proofs
    )
    if preset.startswith("RHS"):
        # The explicit fixture leaves the far wall inactive, rather than equal sharing.
        for domain, response_bolt in zip(
            p.response_binding.physical_bolts, s.responses[0].bolts, strict=True
        ):
            walls = [
                layer_item.layer_id
                for layer_item in domain.layers
                if layer_item.connector_id is None
            ]
            assert len(walls) == 2
            far = next(
                layer_item for layer_item in response_bolt.layers if layer_item.layer_id == walls[1]
            )
            assert components(far.action.force) == ZERO


def test_evaluated_failure_outranks_missing_source_and_has_check_id() -> None:
    r, p, s = complete_sources(request())
    weak = replace(s.fasteners[0], nominal_shear_stress=PhysicalQuantity.of(".001", Unit.MPA))
    d = evaluate_column_moment_base(r, replace(s, fasteners=(weak, *s.fasteners[1:]), zones=()))
    assert d.status == "FAIL"
    assert d.failed_check_ids
    assert d.missing_sources
    assert any(b.status == "FAIL" for b in d.member_bolts)
    assert p.response.qualified


def test_stable_physical_id_enumeration_is_not_an_engineering_change() -> None:
    r, p, sources = complete_sources(request("RHS10X8"))
    record = sources.responses[0]
    reordered = replace(
        record,
        bolts=tuple(reversed(record.bolts)),
        branches=tuple(reversed(record.branches)),
        pressure_patches=tuple(reversed(record.pressure_patches)),
    )
    shuffled = replace(sources, responses=(reordered,))
    other = preview_column_moment_base(r, shuffled)
    assert other == p
    assert evaluate_column_moment_base(r, shuffled) == evaluate_column_moment_base(r, sources)
