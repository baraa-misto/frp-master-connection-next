"""Immutable approved DCTN cases exercised against the new production contracts."""

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.application.double_channel_truss_node import (
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.application.double_channel_truss_node_geometry import build_dctn_geometry
from frp_master_connection.calculation.angle_column_base_response import sum_wrenches
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
    characteristic_bearing,
    local_lap_factor,
)
from frp_master_connection.calculation.double_channel_truss_node_response import (
    DCTNSymmetry,
    _row_pair,
    calculate_dctn_response,
    prove_shaft_transfers,
    require_axial_action,
    require_symmetry,
    row_fractions,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    default_dctn_request,
)
from frp_master_connection.domain.member_profile import ChannelProfileDimensions
from tests.calculation.test_dctn_response import request

D = Decimal
GOLDEN = Path(__file__).parents[1] / "golden/dctn_2_golden_benchmarks_rc1.json"
AUTHORITY = json.loads(GOLDEN.read_bytes())


def test_approved_package_identity_and_case_counts() -> None:
    assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper() == (
        "7770B2B8E25922D9131CD339F5EA52D45AB7D6E6A21B760BCCC46FC8FA88881D"
    )
    assert tuple(len(AUTHORITY[k]) for k in ("positive_cases", "negative_cases", "invariants")) == (
        24,
        26,
        18,
    )


def numbers(value: object) -> object:
    """Parse decimal oracle literals exactly; never round a production output."""
    if isinstance(value, list):
        return [numbers(x) for x in value]
    if isinstance(value, dict):
        return {k: numbers(v) for k, v in value.items()}
    if isinstance(value, str) and value.replace("-", "").replace(".", "").isdigit():
        return D(value)
    return value


@pytest.mark.parametrize("case", AUTHORITY["positive_cases"], ids=lambda c: c["id"])
def test_approved_positive(case: dict[str, Any]) -> None:
    ordinal = int(case["id"][1:3])
    actual: dict[str, Any]
    if ordinal in {1, 2, 3, 4, 6, 7, 16, 17, 18}:
        form = (
            DCTNForm.SOLID_RECTANGLE
            if ordinal == 6
            else (DCTNForm.W_I if ordinal in {7, 16, 17} else DCTNForm.RHS)
        )
        rows = 3 if ordinal in {4, 17} else 2 if ordinal in {3, 6, 7} else 1
        force = "-10" if ordinal == 2 else "30" if ordinal == 4 else "20" if rows == 2 else "10"
        value = request(form, rows, force)
        geometry = build_dctn_geometry(value)
        result = calculate_dctn_response(value, geometry)
        assert geometry.status == "VALID"
        assert result.status == "QUALIFIED"
        member_rows = [r.signed_row_force.to(Unit.KIP).magnitude for r in result.rows]
        neg = [r.negative_at_bolt.force.z.to(Unit.KIP).magnitude for r in result.rows]
        pos = [r.positive_at_bolt.force.z.to(Unit.KIP).magnitude for r in result.rows]
        if ordinal in {1, 2}:
            actual = {
                "member_rows_kip": member_rows,
                "channel_neg_rows_kip": neg,
                "channel_pos_rows_kip": pos,
                "physical_bolts": len(geometry.shafts),
            }
            if ordinal == 1:
                actual.update(
                    rhs_near_wall_rows_kip=[
                        -s.signed_layer_transfers[1].to(Unit.KIP).magnitude for s in result.shafts
                    ],
                    rhs_far_wall_rows_kip=[
                        -s.signed_layer_transfers[2].to(Unit.KIP).magnitude for s in result.shafts
                    ],
                )
        elif ordinal in {3, 4}:
            actual = {
                "member_rows_kip": member_rows,
                "channel_each_rows_kip": neg,
                "physical_bolts": len(geometry.shafts),
            }
            assert pos == neg
        elif ordinal == 6:
            actual = {
                "member_rows_kip": member_rows,
                "channel_each_rows_kip": neg,
                "solid_full_depth_rows_kip": [
                    -s.signed_layer_transfers[1].to(Unit.KIP).magnitude for s in result.shafts
                ],
                "closed_section_factor_applied": characteristic_bearing(
                    PhysicalQuantity.of("24", Unit.KSI), form
                ).magnitude
                != D(24),
            }
            assert all(len(s.layer_owners) == 3 for s in result.shafts)
        elif ordinal == 7:
            actual = {
                "member_rows_kip": member_rows,
                "negative_side_rows_kip": neg,
                "positive_side_rows_kip": pos,
                "physical_bolts": len(geometry.shafts),
            }
        elif ordinal in {16, 17}:
            actual = {
                "side_groups": len({s.side for s in geometry.shafts}),
                "physical_bolts": len(geometry.shafts),
                "holes_per_channel_web": len(result.channels[0].hole_ids),
            }
            assert all(s.native_full_through_core is None for s in geometry.shafts)
        else:
            shaft = result.shafts[0]
            actual = {
                "one_physical_shaft": len(result.shafts) == 1,
                "near_shear_plane_demand_kip": shaft.shear_plane_demands[0].to(Unit.KIP).magnitude,
                "far_shear_plane_demand_kip": shaft.shear_plane_demands[1].to(Unit.KIP).magnitude,
                "capacity_multiplier": shaft.capacity_multiplier,
            }
    elif ordinal == 5:
        source = PhysicalQuantity.of(case["input"]["characteristic_Fbr"], Unit.KSI)
        effective = characteristic_bearing(source, DCTNForm.RHS)
        actual = {
            "effective_characteristic_Fbr": effective.magnitude,
            "factor": effective.magnitude / source.magnitude,
        }
    elif ordinal == 8:
        factor = local_lap_factor(DCTNForm.W_I)
        actual = {
            "single_lap_strength": D(case["input"]["applicable_double_lap_strength"]) * factor,
            "factor": factor,
        }
    elif ordinal in {9, 10, 11, 12, 13}:
        arrangement = (
            DCTNArrangement.VERTICAL_ONLY
            if ordinal == 9
            else (
                DCTNArrangement.TWO_INCLINED
                if ordinal in {10, 11}
                else DCTNArrangement.VERTICAL_TWO_INCLINED
            )
        )
        value = request(DCTNForm.RHS, 2, "10", arrangement)
        forces = {"V": "8", "D1": "10", "D2": "6"} if ordinal == 13 else {}
        if ordinal in {10, 11}:
            forces = {"D1": "10" if ordinal == 10 else "0", "D2": "10" if ordinal == 11 else "0"}
        value = replace(
            value,
            members=tuple(
                replace(m, axial_force=PhysicalQuantity.of(forces.get(m.slot, "10"), Unit.KIP))
                for m in value.members
            ),
        )
        result = calculate_dctn_response(value, build_dctn_geometry(value))
        assert result.status == "QUALIFIED"
        # These immutable mathematical goldens specify rational 3/5, 4/5
        # directions, NOT rounded degree strings. Exercise the unchanged native
        # row/transport engine on those exact reference inputs in the corrected
        # frame. Angle-authored production results are checked independently in
        # test_dctn_axis_angle.py; never force their native frame to these values.
        references = tuple(c.engineering_reference for c in result.channels)
        reference_rows = []
        for member in value.members:
            axis = {
                "V": (Fraction(0), Fraction(0), Fraction(1)),
                "D1": (Fraction("-0.6"), Fraction(0), Fraction("0.8")),
                "D2": (Fraction("0.6"), Fraction(0), Fraction("0.8")),
            }[member.slot]
            start = tuple(Fraction(q.to(Unit.IN).magnitude) for q in member.start)
            for row, fraction in enumerate(row_fractions(member.pattern.rows), 1):
                distance = Fraction(member.pattern.first_from_start.to(Unit.IN).magnitude) + (
                    row - 1
                ) * Fraction(member.pattern.pitch.to(Unit.IN).magnitude)
                point = tuple(s + distance * a for s, a in zip(start, axis, strict=True))
                reference_rows.append(
                    _row_pair(
                        member.slot,
                        row,
                        fraction,
                        Fraction(member.axial_force.canonical_magnitude) * Fraction(fraction),
                        axis,
                        (point[0], Fraction(-3), point[2]),
                        (point[0], Fraction(3), point[2]),
                        (start[0], start[1], start[2]),
                        Unit.IN,
                        (references[0], references[1]),
                    )
                )
        for index, channel in enumerate(result.channels):
            total = sum_wrenches(
                tuple(
                    r.negative_at_channel if index == 0 else r.positive_at_channel
                    for r in reference_rows
                ),
                channel.engineering_reference,
            )
            actual = {
                "channel_each_force_kip": [
                    total.force.x.to(Unit.KIP).magnitude,
                    total.force.z.to(Unit.KIP).magnitude,
                ],
                # Old X-Y reference moment +Z becomes corrected X-Z moment -Y.
                "channel_each_moment_kip_in": -total.moment.y.to(Unit.KIP_IN).magnitude,
            }
            assert actual == numbers(case["expected"])
        return
    elif ordinal == 14:
        value = default_dctn_request(DCTNArrangement.VERTICAL_ONE_INCLINED)
        value = replace(
            value,
            members=tuple(
                replace(m, section=replace(m.section, form=DCTNForm(case["input"][m.slot]["form"])))
                for m in value.members
            ),
        )
        geometry = build_dctn_geometry(value)
        actual = {"compatible": geometry.status == "VALID" and geometry.gap == D(6)}
    elif ordinal == 15:
        value = default_dctn_request(DCTNArrangement.TWO_INCLINED)
        members = []
        for m in value.members:
            angle = D(case["input"][m.slot + "_angle_deg"])
            members.append(replace(m, inclination_deg=180 - angle if m.slot == "D1" else angle))
        value = replace(value, members=tuple(members))
        geometry = build_dctn_geometry(value)
        actual = {
            "compatible": geometry.status == "VALID"
            and members[0].section.linked_section() == members[1].section.linked_section()
        }
    elif ordinal in {19, 20, 21}:
        fail = ordinal == 19
        q = PhysicalQuantity.of
        check = DCTNRequiredCheck(
            "APPROVED_AGGREGATION",
            "LOCAL",
            "FAIL" if fail else "PASS",
            q("2" if fail else "1", Unit.KIP),
            q("1" if fail else "2", Unit.KIP),
            (),
            "TEST_ONLY",
        )
        blockers = () if ordinal == 21 else ("REQUIRED_UNRESOLVED_SOURCE",)
        actual = {"summary": aggregate_dctn_checks((check,), blockers)}
        if ordinal == 19:
            actual["blocker_visible"] = bool(blockers)
        elif ordinal == 21:
            actual["global_chord_certified"] = preview_dctn(
                default_dctn_request()
            ).global_chord_design_evaluated
    elif ordinal == 22:
        p = preview_dctn(default_dctn_request(DCTNArrangement.VERTICAL_TWO_INCLINED))
        assembly = canonical_material_assembly("double-channel-truss-node", p)
        actual = {
            "connector_body_count": sum(
                c.role is ComponentRole.CONNECTOR_BODY for c in assembly.components
            ),
            "primary_member_roles": [
                c.physical_id for c in assembly.components if c.role is ComponentRole.PRIMARY_MEMBER
            ],
            "hardware_role": "INDEPENDENT_316SS_HARDWARE"
            if all(c.role is ComponentRole.FASTENER_OR_HARDWARE for c in assembly.components[5:])
            and p.input.fastener.product_id == "ASTM_F593_GROUP2_316"
            else "INVALID",
        }
    elif ordinal == 23:
        from tests.api.test_connector_materials import native_payload

        # Original approved counts and every original route/body remain exact.
        historical = {r: f for r, f in FAMILIES.items() if r != "stair-stringer-miter"}
        bodies = {
            (route, c.physical_id)
            for route, family in historical.items()
            if route not in NO_BODY_ROUTES
            for c in canonical_material_assembly(
                route, family.preview(native_payload(route))
            ).components
            if c.role is ComponentRole.CONNECTOR_BODY
        }
        actual = {
            "routes": len(historical),
            "connector_bodies": len(bodies),
            "no_body_routes": len(NO_BODY_ROUTES),
            "ui_workspaces": len({f.product_id for f in historical.values()}),
        }
    else:
        assert ordinal == 24
        unit_force = PhysicalQuantity.of(case["input"]["force_kip"], Unit.KIP)
        actual = {
            "force_kN": unit_force.to(Unit.KN).magnitude,
            "half_force_kN": (unit_force * D(".5")).to(Unit.KN).magnitude,
        }
    assert actual == numbers(case["expected"])


@pytest.mark.parametrize("case", AUTHORITY["negative_cases"], ids=lambda c: c["id"])
def test_approved_fail_closed(case: dict[str, Any]) -> None:
    ordinal = int(case["id"][1:3])
    expected = case["expected_status"]
    zero = (Fraction(0),) * 3
    if ordinal in {1, 2, 3, 4}:
        force, moment = zero, zero
        if ordinal == 1:
            moment = (Fraction(0), Fraction(1), Fraction(0))
        elif ordinal == 2:
            force = (Fraction(0), Fraction(1), Fraction(0))
        elif ordinal == 3:
            force = (Fraction(0), Fraction(0), Fraction(1))
        else:
            moment = (Fraction(1), Fraction(0), Fraction(0))
        with pytest.raises(ValueError, match=expected):
            require_axial_action(force, moment)
    elif ordinal in {5, 6, 7}:
        if ordinal == 7:
            with pytest.raises(ValueError, match=expected):
                require_symmetry(DCTNSymmetry(True, True, True, False, True, True))
        else:
            value = default_dctn_request()
            if ordinal == 6:
                m = value.members[0]
                value = replace(
                    value,
                    members=(
                        replace(m, start=(m.start[0], PhysicalQuantity.of(1, Unit.IN), m.start[2])),
                    ),
                )
            geometry = build_dctn_geometry(value)
            if ordinal == 5:
                positive = geometry.members[1]
                profile = value.channel.profile("CHORD_POS", Unit.IN)
                assert isinstance(profile.dimensions, ChannelProfileDimensions)
                dimensions = replace(profile.dimensions, web_thickness=D(".4"))
                geometry = replace(
                    geometry,
                    members=(
                        geometry.members[0],
                        replace(positive, profile=replace(profile, dimensions=dimensions)),
                        *geometry.members[2:],
                    ),
                )
            result = calculate_dctn_response(value, geometry)
            assert expected in result.reasons
            assert result.status == "UNQUALIFIED"
            assert not result.rows
    elif ordinal in {8, 9, 10}:
        value = default_dctn_request(DCTNArrangement.TWO_INCLINED)
        second = value.members[1]
        section = replace(
            second.section,
            **(
                {"depth": PhysicalQuantity.of(8, Unit.IN)}
                if ordinal == 8
                else {"width": PhysicalQuantity.of(5, Unit.IN)}
                if ordinal == 9
                else {"form": DCTNForm.W_I}
            ),
        )
        value = replace(value, members=(value.members[0], replace(second, section=section)))
        geometry = build_dctn_geometry(value)
        assert expected in geometry.reasons
        assert geometry.status == "INVALID_GEOMETRY"
        assert not calculate_dctn_response(value, geometry).rows
    elif ordinal in {11, 12, 13}:
        with pytest.raises(ValueError, match=expected):
            row_fractions(
                4 if ordinal == 11 else 2, 2 if ordinal == 12 else 1, staggered=ordinal == 13
            )
    elif ordinal == 14:
        with pytest.raises(ValueError, match=expected):
            characteristic_bearing(PhysicalQuantity.of(24, Unit.KSI), DCTNForm.RHS, rhs_factor=D(1))
    elif ordinal in {15, 18, 21, 22}:
        form = DCTNForm.SOLID_RECTANGLE if ordinal == 15 else DCTNForm.RHS
        arrangement = (
            DCTNArrangement.VERTICAL_TWO_INCLINED
            if ordinal == 21
            else DCTNArrangement.VERTICAL_ONLY
        )
        design = design_check_dctn(request(form, 2, "10", arrangement))
        assert any(expected in b for b in design.blockers)
        assert design.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
        assert design.preview.response.status == "QUALIFIED"
    elif ordinal == 16:
        value = request(DCTNForm.W_I)
        geometry = build_dctn_geometry(value)
        geometry = replace(
            geometry, shafts=(replace(geometry.shafts[0], side="THROUGH"), *geometry.shafts[1:])
        )
        result = calculate_dctn_response(value, geometry)
        assert expected in result.reasons
        assert result.status == "UNQUALIFIED"
        assert not result.rows
    elif ordinal == 17:
        with pytest.raises(ValueError, match=expected):
            local_lap_factor(DCTNForm.W_I, requested=D(1))
    elif ordinal == 19:
        value = default_dctn_request()
        geometry = build_dctn_geometry(value)
        with pytest.raises(ValueError, match=expected):
            calculate_dctn_response(value, replace(geometry, shafts=geometry.shafts * 2))
    elif ordinal == 20:
        with pytest.raises(ValueError, match=expected):
            prove_shaft_transfers(
                "INVALID_CUT",
                ("CHORD_NEG", "SOLID", "CHORD_POS"),
                (Fraction(5), Fraction(-9), Fraction(5)),
                (Fraction(5), Fraction(5)),
            )
    elif ordinal == 23:
        preview = preview_dctn(default_dctn_request())
        assert preview.global_boundary == expected
        assert not preview.global_chord_design_evaluated
        assert all(not c.global_member_design_evaluated for c in preview.response.channels)
    elif ordinal == 24:
        from frp_master_connection.api.app import create_app
        from frp_master_connection.api.double_channel_truss_node import serialize_dctn_value
        from tests.api.test_angle_column_moment_base_api import TestClient

        client = TestClient(create_app())
        response = client.post(
            "/api/v1/calculations/double-channel-truss-node/preview?connector_body_material=SS316",
            json=serialize_dctn_value(default_dctn_request()),
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == expected
    elif ordinal == 25:
        value = default_dctn_request()
        geometry = build_dctn_geometry(value)
        negative = geometry.members[0]
        geometry = replace(
            geometry,
            members=(
                replace(negative, start=(Fraction(1), *negative.start[1:])),
                *geometry.members[1:],
            ),
        )
        result = calculate_dctn_response(value, geometry)
        assert expected in result.reasons
        assert result.status == "UNQUALIFIED"
        assert not result.rows
    else:
        assert ordinal == 26
        value = default_dctn_request()
        value = replace(
            value,
            fastener=replace(
                value.fastener,
                hardware=replace(
                    value.fastener.hardware, washer_diameter=PhysicalQuantity.of(8, Unit.IN)
                ),
            ),
        )
        invalid_geometry = build_dctn_geometry(value)
        assert invalid_geometry.status == expected
        assert any(not h.hardware_footprint_valid for h in invalid_geometry.holes)
