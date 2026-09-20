"""Versioned relative placement and exact per-unit parent preservation."""

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from itertools import product
from pathlib import Path

import pytest

from frp_master_connection.api.dctn3b import (
    DCTN3BRequestDTO,
    convert_dctn3b_units,
    dctn3b_defaults,
    dctn3b_response,
    map_dctn3b_request,
    migrate_dctn2_dto,
)
from frp_master_connection.api.double_channel_truss_node import (
    DCTNRequestDTO,
    convert_dctn_units,
    map_dctn_request,
    serialize_dctn_value,
)
from frp_master_connection.application.dctn3b import (
    TRANSVERSE,
    design_check_dctn3b,
    preview_dctn3b,
)
from frp_master_connection.application.double_channel_truss_node import (
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.angle_connector_core import (
    components,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.dctn3b_demand import (
    ZERO,
    member_force,
    shear_presentation,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.dctn3b import (
    default_dctn3b_request,
    migrate_dctn2,
    relative_start,
)
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    default_dctn_request,
)
from tests.api.test_connector_materials import http
from tests.api.test_dctn_api_and_parent import BASE, COMBINATIONS

GOLDEN = Path(__file__).parents[1] / "golden/dctn_3b_golden_benchmarks_rc1.json"
F = Fraction


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("transverse", [False, True])
def test_material_planning_uses_versioned_no_body_authority(legacy: bool, transverse: bool) -> None:
    from frp_master_connection.api.connector_material_native import FAMILIES
    from frp_master_connection.application.connector_material_assembly import (
        canonical_material_assembly,
    )

    request = default_dctn3b_request()
    if transverse:
        request = replace(request, members=(replace(request.members[0], Qp=Q.of(2, Unit.KIP)),))
    native = request.legacy_geometry_request() if legacy else request
    payload = serialize_dctn_value(native)
    assert isinstance(payload, dict)
    family = FAMILIES["double-channel-truss-node"]
    preview = family.preview(payload)
    expected_preview = (
        preview_dctn(request.legacy_geometry_request()) if legacy else preview_dctn3b(request)
    )
    assert preview == expected_preview
    assert family.design(payload) == (
        design_check_dctn(request.legacy_geometry_request())
        if legacy
        else design_check_dctn3b(request)
    )
    assembly = canonical_material_assembly(family.route_id, preview)
    response = http(
        "POST",
        "/api/v1/connector-materials/plan",
        {
            "route_id": family.route_id,
            "product_id": family.product_id,
            "native_input": payload,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["targets"] == []
    assert result["native_identity_unchanged"] == assembly.native_identity


def test_approved_golden_identity_and_complete_counts() -> None:
    assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper() == (
        "6A4AECE4205107102C64B54DF95866C17D7D776DA289078918BB9F775D3637E5"
    )
    data = json.loads(GOLDEN.read_bytes())
    assert len(data["positive_cases"]) == 36
    assert len(data["negative_cases"]) == 34
    assert len(data["invariants"]) == 22


@pytest.mark.parametrize(("arrangement", "vertical", "diagonal"), COMBINATIONS)
@pytest.mark.parametrize("si", [False, True])
def test_54_transverse_combinations_preserve_native_geometry_and_full_demand(
    arrangement: DCTNArrangement,
    vertical: DCTNForm,
    diagonal: DCTNForm,
    si: bool,
) -> None:
    from frp_master_connection.calculation.angle_column_base_response import sum_wrenches

    request = default_dctn3b_request(arrangement)
    request = replace(
        request,
        members=tuple(
            replace(
                m,
                section=replace(m.section, form=vertical if m.slot == "V" else diagonal),
                Qp=Q.of(2, Unit.KIP),
                Qq=Q.of(-3, Unit.KIP),
            )
            for m in request.members
        ),
    )
    dto = DCTN3BRequestDTO.model_validate(serialize_dctn_value(request))
    request = map_dctn3b_request(convert_dctn3b_units(dto, si))
    result = preview_dctn3b(request)
    assert result.geometry_status == "VALID"
    assert result.historical_preview is None
    assert result.response_status == TRANSVERSE
    assert result.trusted_response is not None
    assert result.trusted_response.response is None
    total = sum_wrenches(
        tuple(m.at_member_end for m in result.demand.members), result.demand.total_at_node.reference
    )
    assert total == result.demand.total_at_node
    for m in result.demand.members:
        for target in m.transported:
            assert shift_angle_wrench(m.at_member_end, target.wrench.reference) == target.wrench


@pytest.mark.parametrize(("arrangement", "vertical", "diagonal"), COMBINATIONS)
@pytest.mark.parametrize("si", [False, True])
def test_54_exact_native_parent_migrations(
    arrangement: DCTNArrangement,
    vertical: DCTNForm,
    diagonal: DCTNForm,
    si: bool,
) -> None:
    old = default_dctn_request(arrangement)
    old = replace(
        old,
        members=tuple(
            replace(
                m,
                section=replace(
                    m.section,
                    form=vertical if m.slot == "V" else diagonal,
                ),
            )
            for m in old.members
        ),
    )
    dto = DCTNRequestDTO.model_validate(serialize_dctn_value(old))
    dto = convert_dctn_units(dto, si)
    old = map_dctn_request(dto)
    migrated = migrate_dctn2_dto(dto)
    current = map_dctn3b_request(migrated)
    assert current.legacy_geometry_request() == old
    preview = preview_dctn3b(current)
    assert preview.historical_preview == preview_dctn(old)
    assert preview.geometry == preview_dctn(old).geometry
    assert design_check_dctn3b(current).historical_design == design_check_dctn(old)
    assert preview.geometry_status == "VALID"
    assert preview.trusted_response is None
    for endpoint, expected in (
        ("preview", preview),
        ("design-check", design_check_dctn3b(current)),
    ):
        response = http("POST", BASE + "/" + endpoint, migrated.model_dump(mode="json"))
        assert response.status_code == 200, response.text
        assert response.json() == dctn3b_response(expected)


@pytest.mark.parametrize("arrangement", tuple(DCTNArrangement))
@pytest.mark.parametrize(
    ("depth", "z", "valid"),
    [
        ("12", "-5", True),
        ("10", "-4", True),
        ("8", "-3", True),
        ("4", "-1", False),
    ],
)
def test_relative_depth_without_repair(
    arrangement: DCTNArrangement,
    depth: str,
    z: str,
    valid: bool,
) -> None:
    request = default_dctn3b_request(arrangement)
    request = replace(request, channel=replace(request.channel, depth=Q.of(depth, Unit.IN)))
    preview = preview_dctn3b(request)
    assert (preview.geometry_status == "VALID") is valid
    assert all(m.end_center_above_lower_web == Q.of(".625", Unit.IN) for m in request.members)
    assert all(m.start[2] == Q.of(z, Unit.IN) for m in request.legacy_geometry_request().members)
    assert len(request.members) == len(default_dctn3b_request(arrangement).members)


@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize(("P", "Qp", "Qq"), tuple(product((-10, 0, 10), repeat=3)))
def test_signed_component_demand_and_no_unqualified_response(
    si: bool,
    P: int,
    Qp: int,
    Qq: int,
) -> None:
    request = map_dctn3b_request(dctn3b_defaults(DCTNArrangement.VERTICAL_ONLY, si))
    unit = Unit.KN if si else Unit.KIP
    request = replace(
        request,
        members=(
            replace(
                request.members[0],
                P=Q.of(P, unit),
                Qp=Q.of(Qp, unit),
                Qq=Q.of(Qq, unit),
            ),
        ),
    )
    preview = preview_dctn3b(request)
    member = preview.demand.members[0]
    assert components(member.at_member_end.force) == (
        F(Q.of(Qp, unit).canonical_magnitude),
        F(Q.of(Qq, unit).canonical_magnitude),
        F(Q.of(P, unit).canonical_magnitude),
    )
    assert components(member.at_member_end.moment) == ZERO
    for transported in member.transported:
        assert transported.wrench == shift_angle_wrench(
            member.at_member_end,
            transported.wrench.reference,
        )
        assert transported.interpretation.endswith("NOT_ALLOCATED_RESPONSE")
    if Qp or Qq:
        assert preview.historical_preview is None
        assert preview.response_status == TRANSVERSE
        assert preview.demand_status == "CALCULATED"
        assert preview.design_status == "ENGINEERING_REVIEW_REQUIRED"
        assert preview.trusted_response is not None
        assert preview.trusted_response.response is None
        assert design_check_dctn3b(request).checks == ()
    else:
        assert preview.historical_preview == preview_dctn(request.legacy_geometry_request())


def test_independent_exact_345_reference_and_generated_moment() -> None:
    for sign, expected_force, expected_moment in (
        (1, (F(38, 5), F(3), F(34, 5)), (F(36, 5), F(-6), F(-27, 5))),
        (-1, (F(-22, 5), F(3), F(46, 5)), (F(36, 5), F(-6), F(27, 5))),
    ):
        u = (sign * F(3, 5), F(0), F(4, 5))
        p = (F(4, 5), F(0), -sign * F(3, 5))
        force = member_force(u, p, (F(0), F(1), F(0)), (F(10), F(2), F(3)))
        assert force == expected_force
        r = tuple(-3 * a for a in u)
        moment = (
            r[1] * force[2] - r[2] * force[1],
            r[2] * force[0] - r[0] * force[2],
            r[0] * force[1] - r[1] * force[0],
        )
        assert moment == expected_moment


@pytest.mark.parametrize(
    ("form", "width", "depth", "ip", "iq"),
    [
        (DCTNForm.RHS, "4", "6", F(33597, 1024), F(17389, 1024)),
        (DCTNForm.RHS, "6", "4", F(17389, 1024), F(33597, 1024)),
        (DCTNForm.RHS, "4", "4", F(12325, 1024), F(12325, 1024)),
        (DCTNForm.SOLID_RECTANGLE, "4", "6", F(72), F(32)),
        (DCTNForm.SOLID_RECTANGLE, "6", "4", F(32), F(72)),
        (DCTNForm.SOLID_RECTANGLE, "4", "4", F(64, 3), F(64, 3)),
    ],
)
def test_exact_section_label_integrals(
    form: DCTNForm,
    width: str,
    depth: str,
    ip: Fraction,
    iq: Fraction,
) -> None:
    section = replace(
        default_dctn3b_request().members[0].section,
        form=form,
        width=Q.of(width, Unit.IN),
        depth=Q.of(depth, Unit.IN),
    )
    labels = shear_presentation(section)
    assert labels.I_p == ip * F("25.4") ** 4
    assert labels.I_q == iq * F("25.4") ** 4
    assert labels.major_component == ("Qq" if ip > iq else "Qp" if iq > ip else None)
    assert shear_presentation(replace(section, form=DCTNForm.W_I)).major_component == "Qq"


def test_version_datum_migration_and_finite_boundaries() -> None:
    old = default_dctn_request()
    member = old.members[0]
    with pytest.raises(ValueError, match="NOT_MIGRATABLE"):
        migrate_dctn2(
            replace(
                old,
                members=(
                    replace(
                        member,
                        start=(
                            member.start[0],
                            Q.of(1, Unit.IN),
                            member.start[2],
                        ),
                    ),
                ),
            )
        )
    request = default_dctn3b_request()
    with pytest.raises(ValueError, match="CONFLICT"):
        replace(request, contract="unknown")
    with pytest.raises(ValueError, match="DATUM_NOT_SUPPORTED"):
        replace(request, placement_datum="centroid")
    with pytest.raises(ValueError, match="finite"):
        replace(request.members[0], P=Q.of("NaN", Unit.KIP))
    with pytest.raises(ValueError, match="DCTN requires a LENGTH quantity"):
        relative_start(request.channel, Q.of(1, Unit.KIP), Q.of(1, Unit.IN), Unit.IN)
    assert request.fastener.hole_diameter == Q.of(".563", Unit.IN)
    assert request.fastener.hole_diameter.to(Unit.MM).magnitude == Decimal("14.3002")
    assert request.fastener.hole_diameter != Q.of(".5625", Unit.IN)


@pytest.mark.parametrize("name", ["start", "global_start", "direction", "dx", "free_moment", "Mx"])
def test_strict_new_contract_rejects_alternative_authority(name: str) -> None:
    payload = dctn3b_defaults(DCTNArrangement.VERTICAL_ONLY, False).model_dump(mode="json")
    payload["members"][0][name] = "1"
    response = http("POST", BASE + "/preview", payload)
    assert response.status_code == 422


@pytest.mark.parametrize("member", [None, "invalid-member", 42, []])
def test_strict_new_contract_rejects_non_object_members(member: object) -> None:
    payload = dctn3b_defaults(DCTNArrangement.VERTICAL_ONLY, False).model_dump(mode="json")
    payload["members"] = [member]
    response = http("POST", BASE + "/preview", payload)
    assert response.status_code == 422


def test_current_defaults_and_both_unit_conversion_endpoints() -> None:
    for si in (False, True):
        system = "SI" if si else "US"
        dto = dctn3b_defaults(DCTNArrangement.VERTICAL_ONLY, si)
        assert http("GET", BASE + "/defaults?unit_system=" + system).json() == dto.model_dump(
            mode="json"
        )
        converted = http(
            "POST", BASE + "/convert-units?unit_system=" + system, dto.model_dump(mode="json")
        )
        assert converted.status_code == 200
        assert converted.json() == convert_dctn3b_units(dto, si).model_dump(mode="json")
        assert map_dctn3b_request(
            DCTN3BRequestDTO.model_validate(converted.json())
        ) == map_dctn3b_request(dto)


def test_native_direction_uses_current_geometry_not_rational_reference_substitution() -> None:
    request = default_dctn3b_request(DCTNArrangement.TWO_INCLINED)
    request = replace(
        request,
        members=tuple(
            replace(
                m,
                inclination_deg=Decimal("42.7") if m.slot == "D1" else Decimal("139.1"),
                Qp=Q.of(2, Unit.KIP),
                Qq=Q.of(-3, Unit.KIP),
            )
            for m in request.members
        ),
    )
    result = preview_dctn3b(request)
    for demand in result.demand.members:
        native = next(m for m in result.geometry.members if m.physical_id == demand.member_id)
        assert (demand.u, demand.p, demand.q) == (native.u, native.v, native.w)
        assert demand.u[0] not in {F(3, 5), F(-3, 5)}
        assert demand.at_member_end.force == quantity_vector(
            member_force(
                native.u,
                native.v,
                native.w,
                demand.action_components_N,
            ),
            Unit.N,
        )
