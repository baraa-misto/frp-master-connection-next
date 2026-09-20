"""DCTN native geometry/transport proofs, including both controlling clarifications."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from itertools import product

import pytest

from frp_master_connection.application.double_channel_truss_node_geometry import build_dctn_geometry
from frp_master_connection.calculation.angle_column_base_response import ZERO, sum_wrenches
from frp_master_connection.calculation.angle_connector_core import components, quantity_vector
from frp_master_connection.calculation.double_channel_truss_node_response import (
    DCTNSymmetry,
    calculate_dctn_response,
    require_axial_action,
    require_symmetry,
    row_fractions,
)
from frp_master_connection.calculation.multirow import (
    ConnectedMaterialPair,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    DCTNRequest,
    default_dctn_request,
)

D = Decimal
F = Fraction


def request(
    form: DCTNForm = DCTNForm.W_I,
    rows: int = 1,
    force: str = "10",
    arrangement: DCTNArrangement = DCTNArrangement.VERTICAL_ONLY,
) -> DCTNRequest:
    value = default_dctn_request(arrangement)
    return replace(
        value,
        members=tuple(
            replace(
                m,
                section=replace(
                    m.section, form=form, flange_thickness=PhysicalQuantity.of(".5", Unit.IN)
                ),
                pattern=replace(m.pattern, rows=rows),
                axial_force=PhysicalQuantity.of(force, Unit.KIP),
            )
            for m in value.members
        ),
    )


@pytest.mark.parametrize(("rows", "force"), list(product((1, 2, 3), ("10", "-10"))))
def test_owner_centrosymmetric_wi_each_row_closes_without_discarding_side_moments(
    rows: int,
    force: str,
) -> None:
    value = request(rows=rows, force=force)
    geometry = build_dctn_geometry(value)
    assert geometry.status == "VALID", geometry.reasons
    assert all(h.hole_valid and h.hardware_footprint_valid for h in geometry.holes)
    result = calculate_dctn_response(value, geometry)
    assert result.status == "QUALIFIED"
    assert len(result.shafts) == 2 * rows
    assert len({s.bolt_id for s in result.shafts}) == 2 * rows
    assert all(s.native_full_through_core is None for s in geometry.shafts)
    moment_unit = F(PhysicalQuantity.of(1, Unit.KIP_IN).canonical_magnitude)
    for row in result.rows:
        assert row.member_force_closes
        assert row.member_moment_closes
        assert components(row.pair_at_member_axis.moment) == ZERO
        neg = components(row.negative_at_member_axis.moment)
        pos = components(row.positive_at_member_axis.moment)
        assert neg == tuple(-x for x in pos)
        p = F(force) * F(row.row_fraction)
        assert neg[1] / moment_unit == p / 2
        assert pos[1] / moment_unit == -p / 2
        # Cross-gap moments are retained as well, not just the width eccentricity.
        assert neg[0] / moment_unit == -3 * p / 2
        assert pos[0] / moment_unit == 3 * p / 2
        assert row.negative_at_channel.reference == result.channels[0].engineering_reference
        assert components(row.negative_at_channel.moment) != ZERO


@pytest.mark.parametrize(("rows", "force"), list(product((1, 2, 3), ("10", "-10"))))
def test_owner_centered_wi_hole_and_hardware_remain_native_invalid(rows: int, force: str) -> None:
    value = request(rows=rows, force=force)
    value = replace(
        value,
        members=tuple(
            replace(m, pattern=replace(m.pattern, wi_offset=PhysicalQuantity.of(0, Unit.IN)))
            for m in value.members
        ),
    )
    geometry = build_dctn_geometry(value)
    assert geometry.status == "INVALID_GEOMETRY"
    assert any(not h.hole_valid for h in geometry.holes if h.owner_id == "V")
    assert calculate_dctn_response(value, geometry).rows == ()


@pytest.mark.parametrize(("rows", "force"), list(product((1, 2, 3), ("10", "-10"))))
def test_owner_same_sign_pattern_retains_residual_and_is_unqualified(rows: int, force: str) -> None:
    value = request(rows=rows, force=force)
    geometry = build_dctn_geometry(value)
    changed_rows = tuple(
        replace(
            row,
            negative_point=(row.positive_point[0], row.negative_point[1], row.positive_point[2]),
        )
        for row in geometry.rows
    )
    result = calculate_dctn_response(value, replace(geometry, rows=changed_rows))
    assert "DCTN_WI_ECCENTRICITY_RESPONSE_NOT_QUALIFIED" in result.reasons
    assert result.status == "UNQUALIFIED"
    assert result.rows == ()
    from frp_master_connection.calculation.angle_connector_core import AngleWrench

    for row, fraction in zip(changed_rows, row_fractions(rows), strict=True):
        force_vector = quantity_vector((F(0), F(0), F(force) * F(fraction) / 2), Unit.KIP)
        pair = tuple(
            AngleWrench(
                quantity_vector(point, Unit.IN), force_vector, quantity_vector(ZERO, Unit.KIP_IN)
            )
            for point in (row.negative_point, row.positive_point)
        )
        total = sum_wrenches(pair, quantity_vector(ZERO, Unit.IN))
        assert total.moment.y.to(Unit.KIP_IN).magnitude == -D(force) * fraction


@pytest.mark.parametrize("arrangement", tuple(DCTNArrangement))
@pytest.mark.parametrize("form", tuple(DCTNForm))
def test_all_fifteen_uniform_form_arrangements_native_full_member_hardware_geometry(
    arrangement: DCTNArrangement,
    form: DCTNForm,
) -> None:
    value = request(form, 2, arrangement=arrangement)
    geometry = build_dctn_geometry(value)
    assert geometry.status == "VALID", geometry.reasons
    result = calculate_dctn_response(value, geometry)
    assert result.status == "QUALIFIED"
    assert all(s.terminal_residual.canonical_magnitude == 0 for s in result.shafts)
    assert all(s.capacity_multiplier is None for s in result.shafts)
    for channel in result.channels:
        assert channel.total == sum_wrenches(channel.contributions, channel.engineering_reference)
        assert channel.global_member_design_evaluated is False


def test_exact_startup_hole_authority_no_fractional_substitution() -> None:
    value = default_dctn_request()
    assert value.fastener.hole_diameter.to(Unit.IN).magnitude == D(".563")
    assert value.fastener.hole_diameter.to(Unit.MM).magnitude == D("14.3002")
    assert value.fastener.hole_diameter != PhysicalQuantity.of(".5625", Unit.IN)
    assert value.members[0].pattern.rows == 2
    assert value.members[0].pattern.across == 1
    assert build_dctn_geometry(value).status == "VALID"


@pytest.mark.parametrize("form", tuple(DCTNForm))
@pytest.mark.parametrize("rows", [1, 2, 3])
def test_zero_action_retains_physical_zero_shear_planes(form: DCTNForm, rows: int) -> None:
    value = request(form, rows, "0")
    result = calculate_dctn_response(value, build_dctn_geometry(value))
    assert result.status == "QUALIFIED"
    for shaft in result.shafts:
        assert len(shaft.shear_plane_demands) == (1 if form is DCTNForm.W_I else 2)
        assert all(q.canonical_magnitude == 0 for q in shaft.shear_plane_demands)
        assert shaft.terminal_residual.canonical_magnitude == 0


@pytest.mark.parametrize("rows", [1, 2, 3])
def test_row_native_authority_and_exact_unit_sum(rows: int) -> None:
    fractions = row_fractions(rows)
    assert sum(fractions) == 1
    if rows > 1:
        assert fractions == prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, rows)


@pytest.mark.parametrize(
    ("count", "across", "staggered", "reason"),
    [
        (4, 1, False, "DCTN_ROW_COUNT_OUTSIDE_RC1_SCOPE"),
        (2, 2, False, "DCTN_BOLTS_ACROSS_ROW_OUTSIDE_RC1_SCOPE"),
        (2, 1, True, "DCTN_STAGGERED_BOLTS_NOT_SUPPORTED_IN_RC1"),
    ],
)
def test_rows_outside_scope_fail_closed(
    count: int, across: int, staggered: bool, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        row_fractions(count, across, staggered=staggered)


@pytest.mark.parametrize(
    "field",
    [
        "identical_channel_profile_material_source",
        "mirrored_channel_placement",
        "incoming_centered",
        "identical_hardware",
        "no_side_specific_response_state",
    ],
)
def test_each_symmetry_prerequisite_is_required(field: str) -> None:
    proof = DCTNSymmetry(True, True, True, True, True, True)
    require_symmetry(proof)
    with pytest.raises(ValueError, match="DCTN_CHANNEL_SYMMETRY_RESPONSE_NOT_QUALIFIED"):
        require_symmetry(replace(proof, **{field: False}))


@pytest.mark.parametrize(
    ("force", "moment"),
    [
        ((F(1), F(1), F(0)), ZERO),
        ((F(1), F(0), F(1)), ZERO),
        (ZERO, (F(1), F(0), F(0))),
        (ZERO, (F(0), F(1), F(0))),
        (ZERO, (F(0), F(0), F(1))),
    ],
)
def test_nonaxial_member_actions_remain_outside_rc1(
    force: tuple[Fraction, Fraction, Fraction],
    moment: tuple[Fraction, Fraction, Fraction],
) -> None:
    with pytest.raises(ValueError, match="DCTN_MEMBER_ACTION_OUTSIDE_AXIAL_TRUSS_SCOPE"):
        require_axial_action(force, moment)
    require_axial_action((F(-1), F(0), F(0)), ZERO)
