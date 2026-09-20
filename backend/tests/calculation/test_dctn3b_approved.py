"""Approved new oracle, keeping analytical references separate from native angles."""

import json
from dataclasses import replace
from fractions import Fraction
from typing import Any, cast

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.dctn3b import dctn3b_defaults
from frp_master_connection.api.double_channel_truss_node import serialize_dctn_value
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.application.dctn3b import preview_dctn3b
from frp_master_connection.application.double_channel_truss_node import preview_dctn
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    exact_decimal,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.dctn3b_demand import ZERO, member_force, shear_presentation
from frp_master_connection.calculation.dctn3b_trusted_response import EMPTY_TRUSTED_RESPONSES
from frp_master_connection.calculation.double_channel_truss_node_response import row_fractions
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.connector_materials import ComponentRole
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
from tests.api.test_connector_materials import http, native_payload
from tests.api.test_dctn_api_and_parent import BASE
from tests.calculation.test_dctn3b_native import GOLDEN

AUTHORITY = json.loads(GOLDEN.read_bytes())
F = Fraction
BACKEND_POSITIVES = [c for c in AUTHORITY["positive_cases"] if not 29 <= int(c["id"][1:3]) <= 34]


@pytest.mark.parametrize("case", BACKEND_POSITIVES, ids=lambda c: c["id"])
def test_approved_positive(case: dict[str, Any]) -> None:
    number = int(case["id"][1:3])
    given, expected = case.get("input", {}), case["expected"]
    request = default_dctn3b_request()
    if number in {1, 2, 3, 4, 7}:
        channel = replace(
            request.channel,
            depth=Q.of(given["D"], Unit.IN),
            flange_thickness=Q.of(given["tf"], Unit.IN),
        )
        point = relative_start(
            channel, Q.of(given.get("s", "0"), Unit.IN), Q.of(given["h"], Unit.IN), Unit.IN
        )
        if number == 7:
            # Translation of the named node frame, not a new public placement DOF.
            actual = tuple(F(q.magnitude) + F(o) for q, o in zip(point, given["O"], strict=True))
            assert actual == tuple(F(x) for x in expected["A"])
        else:
            assert F(point[2].magnitude) == F(expected["z"])
            if number == 4:
                assert (
                    preview_dctn3b(replace(request, channel=channel)).geometry_status
                    == "INVALID_GEOMETRY"
                )
    elif number in {5, 6}:
        old = default_dctn_request()
        old = replace(
            old,
            members=(
                replace(
                    old.members[0],
                    start=(
                        Q.of(given.get("start_x", "0"), Unit.IN),
                        Q.of(given.get("start_y", "0"), Unit.IN),
                        Q.of(given["start_z"], Unit.IN),
                    ),
                ),
            ),
        )
        migrated = migrate_dctn2(old)
        assert F(migrated.members[0].end_center_above_lower_web.magnitude) == F(expected["h"])
        assert migrated.legacy_geometry_request() == old
        if number == 6:
            assert F(migrated.members[0].chord_station.magnitude) == F(expected["s"])
            assert expected["migratable"] is True
    elif 8 <= number <= 16:
        u = cast(Rational3, tuple(F(x) for x in given.get("u", ("0", "0", "1"))))
        p, q = (u[2], F(0), -u[0]), (F(0), F(1), F(0))
        actions = (F(given["P"]), F(given["Qp"]), F(given["Qq"]))
        force = member_force(u, p, q, actions)
        if number <= 13:
            assert force == tuple(F(x) for x in expected["F"])
        else:
            end = quantity_vector(ZERO, Unit.MM)
            target = quantity_vector(
                cast(Rational3, tuple(F(given["ell"]) * v for v in u)), Unit.MM
            )
            wrench = AngleWrench(
                end, quantity_vector(force, Unit.N), quantity_vector(ZERO, Unit.N_MM)
            )
            assert components(shift_angle_wrench(wrench, target).moment) == tuple(
                F(x) for x in expected["M"]
            )
    elif 17 <= number <= 20:
        request = replace(
            request,
            members=(
                replace(
                    request.members[0],
                    P=Q.of(given["P"], Unit.KIP),
                    Qp=Q.of(given["Qp"], Unit.KIP),
                    Qq=Q.of(given["Qq"], Unit.KIP),
                ),
            ),
        )
        result = preview_dctn3b(request)
        if number == 17:
            assert expected["branch"] == "HISTORICAL_DCTN2_AXIAL"
            assert result.historical_preview == preview_dctn(request.legacy_geometry_request())
        else:
            assert (result.demand_status, result.response_status, result.design_status) == (
                expected["demand"],
                expected["response"],
                expected["design"],
            )
            assert result.historical_preview is None
    elif 21 <= number <= 27:
        form = DCTNForm.SOLID_RECTANGLE if given["form"] == "SRS" else DCTNForm(given["form"])
        section = replace(
            request.members[0].section,
            form=form,
            width=Q.of(given.get("b", "4"), Unit.IN),
            depth=Q.of(given.get("d", "6"), Unit.IN),
            wall_or_web=Q.of(exact_decimal(F(given.get("t", "3/8"))), Unit.IN),
        )
        labels = shear_presentation(section)
        if "Ip" in expected:
            assert labels.I_p == F(expected["Ip"]) * F("25.4") ** 4
            assert labels.I_q == F(expected["Iq"]) * F("25.4") ** 4
        if "labels" in expected:
            assert [labels.Qp_label, labels.Qq_label] == expected["labels"]
            assert labels.major_component is labels.minor_component is None
        else:
            assert labels.major_component == expected["major_component"]
            assert labels.minor_component == expected["minor_component"]
    elif number == 28:
        assert row_fractions(3) == tuple(F(x) for x in expected["fractions"])
        request = replace(
            request,
            members=(
                replace(request.members[0], pattern=replace(request.members[0].pattern, rows=3)),
            ),
        )
        result = preview_dctn3b(request)
        assert result.historical_preview == preview_dctn(request.legacy_geometry_request())
        assert result.historical_preview is not None
        assert tuple(
            r.row_fraction for r in result.historical_preview.response.rows
        ) == row_fractions(3)
    elif number == 35:
        bodies = {
            (route, c.physical_id)
            for route, family in FAMILIES.items()
            if route not in NO_BODY_ROUTES
            for c in canonical_material_assembly(
                route, family.preview(native_payload(route))
            ).components
            if c.role is ComponentRole.CONNECTOR_BODY
        }
        assert {
            "routes": len(FAMILIES),
            "connector_bodies": len(bodies),
            "no_body_routes": len(NO_BODY_ROUTES),
            "workspaces": len({f.product_id for f in FAMILIES.values()}),
            "cme3_selectors": len(FAMILIES) - len(NO_BODY_ROUTES),
        } == expected
    else:
        assert number == 36
        assert EMPTY_TRUSTED_RESPONSES == ()
        request = replace(
            request,
            members=(
                replace(
                    request.members[0],
                    Qp=Q.of(2, Unit.KIP),
                    local_path_source_reference="QUALIFIED_APPROVED",
                ),
            ),
            shared_channel_source_reference="QUALIFIED_APPROVED",
        )
        result = preview_dctn3b(request)
        assert result.trusted_response is not None
        assert result.trusted_response.response is None
        assert result.response_status == "DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED"


@pytest.mark.parametrize(
    "case",
    [
        c
        for c in AUTHORITY["negative_cases"]
        if int(c["id"][1:3]) in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 22, 23, 24, 25, 26, 27, 28}
    ],
    ids=lambda c: c["id"],
)
def test_approved_native_negative(case: dict[str, Any]) -> None:
    number, expected = int(case["id"][1:3]), case["expected_status"]
    request = default_dctn3b_request()
    if number == 1:
        old = default_dctn_request()
        with pytest.raises(ValueError, match=expected):
            migrate_dctn2(
                replace(
                    old,
                    members=(
                        replace(
                            old.members[0],
                            start=(
                                Q.of(0, Unit.IN),
                                Q.of(1, Unit.IN),
                                Q.of(-5, Unit.IN),
                            ),
                        ),
                    ),
                )
            )
    elif number in {2, 3, 4, 5, 6, 7}:
        dto = dctn3b_defaults(DCTNArrangement.VERTICAL_ONLY, False).model_dump(mode="json")
        member = dto["members"][0]
        if number in {2, 3}:
            member["start" if number == 2 else "global_start_x"] = "0"
        elif number == 4:
            dto["placement_datum"] = "CHANNEL_CENTROID"
        elif number == 5:
            member["chord_station"]["value"] = "NaN"
        elif number == 6:
            member["direction"] = [0, 0, 1]
        else:
            member["free_moment"] = "1"
        response = http("POST", BASE + "/preview", dto)
        assert response.status_code == 422
        assert (
            expected in response.text
            if number != 5
            else "INVALID" in response.text or "finite" in response.text
        )
    elif number == 22:
        assert (
            preview_dctn3b(
                replace(request, channel=replace(request.channel, depth=Q.of(4, Unit.IN)))
            ).geometry_status
            == expected
        )
    elif number == 23:
        with pytest.raises(AssertionError, match=expected):
            assert request.fastener.hole_diameter == Q.of(".5625", Unit.IN), expected
    elif number == 27:
        with pytest.raises(AssertionError, match=expected):
            assert tuple(F(x) for x in row_fractions(3)) == (F(1, 3),) * 3, expected
    elif number == 28:
        payload = serialize_dctn_value(request)
        assert isinstance(payload, dict)
        response = http("POST", BASE + "/preview?connector_body_material=SS316", payload)
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == expected
    else:
        request = replace(
            request,
            members=(
                replace(
                    request.members[0],
                    Qp=Q.of(2, Unit.KIP),
                    local_path_source_reference="HALF_SHARE_ROW_FRACTIONS_SLICE8_ZERO_APPROVED",
                ),
            ),
        )
        result = preview_dctn3b(request)
        assert result.historical_preview is None
        assert result.trusted_response is not None
        assert result.trusted_response.response is None
        if number == 10:
            assert expected in result.trusted_response.reasons
        elif number == 24:
            assert result.design_status == expected
        else:
            assert result.response_status == expected
