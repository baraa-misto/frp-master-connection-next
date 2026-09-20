"""Malformed and out-of-scope inputs remain explicit without auto-repair."""

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.api.double_channel_truss_node import (
    DCTNRequestDTO,
    convert_dctn_units,
    serialize_dctn_value,
)
from frp_master_connection.application.double_channel_truss_node import design_check_dctn
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.double_channel_truss_node_response import (
    prove_shaft_transfers,
)
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNRequest,
    default_dctn_request,
)
from tests.api.test_angle_column_moment_base_api import TestClient
from tests.calculation.test_dctn_sources_and_native import q


@pytest.mark.parametrize(
    "change",
    [
        lambda r: replace(r, contract="INVALID"),
        lambda r: replace(r, unit_system="INVALID"),
        lambda r: replace(r, length_unit=Unit.KIP),
        lambda r: replace(r, members=()),
        lambda r: replace(r, channel=replace(r.channel, material_id="SS316")),
        lambda r: replace(r, members=(replace(r.members[0], material_id="SS316"),)),
        lambda r: replace(r, members=(replace(r.members[0], slot="OTHER"),)),
        lambda r: replace(r, members=(replace(r.members[0], inclination_deg=Decimal(0)),)),
        lambda r: replace(r, members=(replace(r.members[0], inclination_deg=Decimal("NaN")),)),
        lambda r: replace(r, members=(replace(r.members[0], axial_force=q("1", Unit.IN)),)),
        lambda r: replace(r, fastener=replace(r.fastener, diameter=q("0", Unit.IN))),
        lambda r: replace(
            r, members=(replace(r.members[0], pattern=replace(r.members[0].pattern, rows=True)),)
        ),
        lambda r: replace(
            r, members=(replace(r.members[0], pattern=replace(r.members[0].pattern, across=True)),)
        ),
        lambda r: replace(
            r,
            members=(
                replace(
                    r.members[0], section=replace(r.members[0].section, depth=q("1", Unit.KIP))
                ),
            ),
        ),
    ],
)
def test_domain_rejects_invalid_authority_or_dimension(
    change: Callable[[DCTNRequest], object],
) -> None:
    with pytest.raises(ValueError, match="DCTN"):
        change(default_dctn_request())


@pytest.mark.parametrize(
    ("field", "number", "reason"),
    [
        ("rows", 4, "DCTN_ROW_COUNT_OUTSIDE_RC1_SCOPE"),
        ("across", 2, "DCTN_BOLTS_ACROSS_ROW_OUTSIDE_RC1_SCOPE"),
        ("staggered", True, "DCTN_STAGGERED_BOLTS_NOT_SUPPORTED_IN_RC1"),
    ],
)
def test_out_of_scope_pattern_has_no_invented_response(
    field: str, number: int, reason: str
) -> None:
    value = default_dctn_request()
    m = value.members[0]
    pattern = (
        replace(m.pattern, rows=number)
        if field == "rows"
        else replace(m.pattern, across=number)
        if field == "across"
        else replace(m.pattern, staggered=bool(number))
    )
    value = replace(value, members=(replace(m, pattern=pattern),))
    result = design_check_dctn(value)
    assert reason in result.preview.geometry.reasons
    assert result.preview.geometry.status == "INVALID_GEOMETRY"
    assert result.preview.response.rows == ()
    assert result.checks == ()
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"


def test_head_and_nut_must_fit_the_declared_exterior_hardware_envelope() -> None:
    value = default_dctn_request()
    value = replace(
        value,
        fastener=replace(
            value.fastener,
            hardware=replace(value.fastener.hardware, head_across_flats=q("2", Unit.IN)),
        ),
    )
    result = design_check_dctn(value)
    assert "DCTN_INVALID_GEOMETRY:HEAD_NUT_EXCEED_WASHER_ENVELOPE" in result.blockers
    assert result.checks == ()


@pytest.mark.parametrize(
    ("owners", "transfers", "planes"),
    [
        (("A",), (Fraction(0),), ()),
        (("A", "B"), (Fraction(1), Fraction(-1)), (Fraction(2),)),
        (("A", "B"), (Fraction(1),), (Fraction(1),)),
    ],
)
def test_common_shaft_rejects_unknown_layer_count_and_incorrect_cuts(
    owners: tuple[str, ...], transfers: tuple[Fraction, ...], planes: tuple[Fraction, ...]
) -> None:
    with pytest.raises(ValueError, match="COMMON_SHAFT_CONSERVATION"):
        prove_shaft_transfers("BAD", owners, transfers, planes)


def test_transport_and_fingerprint_use_explicit_native_values_only() -> None:
    assert serialize_dctn_value({"x": None, "y": [True, 1, 1.25]}) == {
        "x": None,
        "y": [True, 1, 1.25],
    }
    with pytest.raises(TypeError, match="Unsupported DCTN transport"):
        serialize_dctn_value(object())
    assert dctn_fingerprint({"x": 1.25}) == dctn_fingerprint({"x": Decimal("1.25")})
    assert dctn_fingerprint({"x": 1.25}) != dctn_fingerprint({"x": 1.251})
    with pytest.raises(ValueError, match="finite"):
        dctn_fingerprint(float("nan"))


@pytest.mark.parametrize("endpoint", ["preview", "design-check", "convert-units?unit_system=SI"])
def test_public_canonical_dimension_failure_is_422_not_a_server_failure(endpoint: str) -> None:
    dto = DCTNRequestDTO.model_validate(serialize_dctn_value(default_dctn_request()))
    payload = dto.model_dump(mode="json")
    payload["members"][0]["axial_force"]["unit"] = "in"
    response = TestClient(create_app()).post(
        "/api/v1/calculations/double-channel-truss-node/" + endpoint,
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_DCTN_INPUT_INVALID"


def test_public_defaults_and_conversion_use_direct_native_authority() -> None:
    client = TestClient(create_app())
    base = "/api/v1/calculations/double-channel-truss-node"
    dto = DCTNRequestDTO.model_validate(serialize_dctn_value(default_dctn_request()))
    for system, si in (("US", False), ("SI", True)):
        expected = convert_dctn_units(dto, si).model_dump(mode="json")
        assert (
            client.get(base + "/defaults?contract=DCTN-2-RC1&unit_system=" + system).json()
            == expected
        )
        result = client.post(
            base + "/convert-units?unit_system=" + system, json=dto.model_dump(mode="json")
        )
        assert result.status_code == 200
        assert result.json() == expected
