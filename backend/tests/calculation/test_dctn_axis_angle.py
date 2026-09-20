"""Correction authority: actual Z-up geometry and backend-owned native angles."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.double_channel_truss_node import (
    DCTNRequestDTO,
    convert_dctn_units,
    map_dctn_request,
    serialize_dctn_value,
)
from frp_master_connection.application.double_channel_truss_node import preview_dctn
from frp_master_connection.application.double_channel_truss_node_geometry import build_dctn_geometry
from frp_master_connection.calculation.angle_connector_core import components, quantity_vector
from frp_master_connection.calculation.deterministic_trigonometry import (
    deterministic_sine_cosine_degrees,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    default_dctn_request,
)
from tests.api.test_angle_column_moment_base_api import TestClient

D = Decimal
F = Fraction
Triple = tuple[Fraction, Fraction, Fraction]


def cross(a: Triple, b: Triple) -> Triple:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


@pytest.mark.parametrize(
    ("angle", "expected"),
    [
        ("0", (1, 0, 0)),
        ("90", (0, 0, 1)),
        ("180", (-1, 0, 0)),
        ("270", (0, 0, -1)),
        ("-90", (0, 0, -1)),
        ("360", (1, 0, 0)),
    ],
)
def test_semantic_cardinals_are_exact_not_trig_residuals(
    angle: str, expected: tuple[int, int, int]
) -> None:
    value = default_dctn_request(DCTNArrangement.ONE_INCLINED)
    member = replace(value.members[0], inclination_deg=D(angle))
    assert member.derived_direction == tuple(D(x) for x in expected)
    geometry = build_dctn_geometry(replace(value, members=(member,)))
    native = geometry.members[-1]
    assert native.u == tuple(F(x) for x in expected)
    assert cross(native.u, native.v) == native.w


@pytest.mark.parametrize("angle", ["53.13010235415599", "126.86989764584402", "-35.5", "405.25"])
def test_noncardinal_angles_use_existing_native_trigonometry_verbatim(angle: str) -> None:
    member = replace(
        default_dctn_request(DCTNArrangement.ONE_INCLINED).members[0],
        inclination_deg=D(angle),
    )
    sine, cosine = deterministic_sine_cosine_degrees(D(angle))
    assert member.derived_direction == (D(str(cosine)), D(0), D(str(sine)))


@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize("arrangement", list(DCTNArrangement))
@pytest.mark.parametrize("form", list(DCTNForm))
def test_native_corrected_frame_and_exact_independent_vector_transport(
    si: bool, arrangement: DCTNArrangement, form: DCTNForm
) -> None:
    value = default_dctn_request(arrangement)
    value = replace(
        value,
        members=tuple(replace(m, section=replace(m.section, form=form)) for m in value.members),
    )
    dto = DCTNRequestDTO.model_validate(serialize_dctn_value(value))
    converted = convert_dctn_units(dto, si)
    assert [m.inclination_deg for m in converted.members] == [
        m.inclination_deg for m in dto.members
    ]
    value = map_dctn_request(converted)
    p = preview_dctn(value)
    assert p.geometry.status == "VALID", p.geometry.reasons
    assert p.response.status == "QUALIFIED", p.response.reasons
    assert p.connector_body_count == 0
    native_by_id = {m.physical_id: m for m in p.geometry.members}
    inputs = {m.slot: m for m in value.members}
    for sign, chord in zip((-1, 1), p.geometry.members[:2], strict=True):
        assert chord.u == (F(1), F(0), F(0))
        assert chord.start[1] == sign * F(p.geometry.gap) / 2
        assert chord.start[2] == 0
        assert cross(chord.u, chord.v) == chord.w
    for member in p.geometry.members[2:]:
        assert member.start[1] == 0
        assert member.u[1] == 0
        assert member.w == (F(0), F(1), F(0))
        # Handedness is native float frame authority; its algebraic orientation
        # has positive determinant without imposing a new exact-unit-norm policy.
        assert cross(member.u, member.v)[1] > 0
        if member.physical_id == "V":
            assert member.u == (F(0), F(0), F(1))
    for shaft in p.geometry.shafts:
        assert shaft.start[0] == shaft.end[0]
        assert shaft.start[2] == shaft.end[2]
        assert shaft.start[1] != shaft.end[1]
        assert len(shaft.layer_owners) == (
            2 if form is DCTNForm.W_I else 4 if form is DCTNForm.RHS else 3
        )
    for response in p.response.rows:
        native = native_by_id[response.member_id]
        row = next(
            r
            for r in p.geometry.rows
            if r.member_id == response.member_id and r.row == response.row
        )
        load = F(inputs[response.member_id].axial_force.canonical_magnitude) * F(
            response.row_fraction
        )
        force: Triple = (load * native.u[0] / 2, F(0), load * native.u[2] / 2)
        for index, point in enumerate((row.negative_point, row.positive_point)):
            wrench = response.negative_at_channel if index == 0 else response.positive_at_channel
            ref = components(p.response.channels[index].engineering_reference)
            # Native quantity construction/conversion remains the controlling
            # finite-Decimal handoff, including its accepted projection path.
            point_si = components(quantity_vector(point, value.length_unit))
            arm: Triple = (
                point_si[0] - ref[0],
                point_si[1] - ref[1],
                point_si[2] - ref[2],
            )
            assert components(wrench.force) == force
            assert wrench.moment == quantity_vector(cross(arm, force), Unit.N_MM)
        assert components(response.pair_at_member_axis.force) == tuple(2 * x for x in force)
        assert components(response.pair_at_member_axis.moment) == (F(0), F(0), F(0))


@pytest.mark.parametrize("force", ["10", "-10", "0"])
def test_vertical_force_is_global_fz(force: str) -> None:
    value = default_dctn_request()
    value = replace(
        value,
        members=(replace(value.members[0], axial_force=PhysicalQuantity.of(force, Unit.KIP)),),
    )
    p = preview_dctn(value)
    for c in p.response.channels:
        assert c.total.force.x.magnitude == c.total.force.y.magnitude == 0
        assert c.total.force.z.to(Unit.KIP).magnitude == D(force) / 2


def test_independent_angles_and_derived_values_are_not_client_authority() -> None:
    value = default_dctn_request(DCTNArrangement.TWO_INCLINED)
    assert [m.inclination_deg for m in value.members] == [
        D("126.86989764584402"),
        D("53.13010235415599"),
    ]
    assert [tuple(q.to(Unit.IN).magnitude for q in m.start) for m in value.members] == [
        (D(-16), D(0), D(-5)),
        (D(16), D(0), D(-5)),
    ]
    changed = replace(
        value, members=(replace(value.members[0], inclination_deg=D(145)), value.members[1])
    )
    assert changed.members[1] is value.members[1]
    assert preview_dctn(changed).geometry.status == "VALID"
    client = TestClient(create_app())
    payload = DCTNRequestDTO.model_validate(serialize_dctn_value(changed)).model_dump(mode="json")
    endpoint = "/api/v1/calculations/double-channel-truss-node/preview"
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200
    for field in ("direction", "derived_direction"):
        invalid = {
            **payload,
            "members": [{**payload["members"][0], field: ["1", "0", "0"]}, payload["members"][1]],
        }
        assert client.post(endpoint, json=invalid).status_code == 422
    for nonfinite in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError, match="finite inclination"):
            replace(value.members[0], inclination_deg=D(nonfinite))


def test_v_cannot_be_reauthored_as_an_inclined_slot() -> None:
    with pytest.raises(ValueError, match="exactly 90"):
        replace(default_dctn_request().members[0], inclination_deg=D(89))
