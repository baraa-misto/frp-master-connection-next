"""Executable approved SSMC contract cases, additive to the numerical goldens."""

import hashlib
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.ssmc import illustrative_ssmc, map_ssmc_request
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.application.ssmc import preview_ssmc
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.ssmc_material import (
    SSMCQualifiedProperty,
    select_ssmc_property,
)
from frp_master_connection.calculation.ssmc_response import (
    EMPTY_RESPONSE_REGISTRY,
    required_design_status,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.domain.ssmc import SSMCMethodPolicy, StringerForm
from frp_master_connection.geometry.ssmc_polygon import construct_miter_polygon, validate_polygon
from tests.api.test_connector_materials import http
from tests.application.test_ssmc_geometry_adversaries import inch
from tests.calculation.test_ssmc_golden import DATA
from tests.calculation.test_ssmc_qualification import response_fixture, validate


@pytest.mark.parametrize("case", DATA["positive_cases"][11:], ids=lambda c: c["id"])
def test_approved_contract_positive(case: dict[str, Any]) -> None:
    n = int(case["id"][1:3])
    expected, given = case["expected"], case.get("input", {})
    request = map_ssmc_request(illustrative_ssmc())
    if n in {13, 14}:
        request = replace(request, theta_deg=Decimal(given["theta_deg"]))
    if 15 <= n <= 18:
        request = replace(
            request,
            horizontal=replace(request.horizontal, form=StringerForm(given["H"])),
            inclined=replace(request.inclined, form=StringerForm(given["I"])),
        )
    if n in {19, 20}:
        request = replace(request, plate=replace(request.plate, side=given["side"]))
    if n in {21, 22}:
        rows = int(given["topology"][0])
        request = replace(request, horizontal_group=replace(request.horizontal_group, rows=rows))
    result = preview_ssmc(replace(request, N=Q.of(8, Unit.KIP), M=Q.of(20, Unit.KIP_IN)))
    actual: dict[str, Any]
    if n == 12:
        recovered = [
            shift_angle_wrench(g.plate_wrench, result.work_point_wrench.reference)
            for g in result.groups
        ]
        assert components(recovered[1].force) == components(result.work_point_wrench.force)
        assert components(recovered[0].force) == tuple(
            -v for v in components(result.work_point_wrench.force)
        )
        actual = {
            "horizontal_group": "FULL_WRENCH",
            "inclined_group": "FULL_WRENCH",
            "action_halving": result.method_policy.serial_action_factor != 1,
        }
    elif 13 <= n <= 22:
        actual = {
            "geometry_demand_eligible" if 15 <= n <= 18 else "eligible": all(
                g.native_slice8 is not None for g in result.groups
            )
        }
    elif n == 23:
        actual = {
            "policy": result.plate_policy,
            "lw_strength_credit": any(
                s.longitudinal_strength_credit for s in result.material_source_ledger
            ),
            "isotropic": any(s.isotropic for s in result.material_source_ledger),
        }
    elif 24 <= n <= 27:
        key, status_name = {
            24: ("complete_response", "Complete response"),
            25: ("plate_resistance", "Plate resistance"),
            26: ("member_transfer", "Member local transfer"),
            27: ("hardware_combined", "Hardware"),
        }[n]
        actual = {key: dict(result.statuses)[status_name], "design": result.whole_connection_status}
    elif n == 28:
        assert not EMPTY_RESPONSE_REGISTRY
        actual = {"production_registry": "EMPTY"}
    elif n == 29:
        from frp_master_connection.application.stainless_family_activation import ROUTES

        actual = {
            "routes": len(FAMILIES),
            "body_bearing_routes": len(set(FAMILIES) - NO_BODY_ROUTES),
            "no_body_routes": len(NO_BODY_ROUTES),
            "cme3_selectors": len(ROUTES),
        }
    elif n == 30:
        assembly = canonical_material_assembly("stair-stringer-miter", result)
        actual = {
            "connector_bodies_per_instance": sum(
                c.role is ComponentRole.CONNECTOR_BODY for c in assembly.components
            )
        }
    elif n == 31:
        actual = {"whole_connection_pass_allowed": result.whole_connection_status == "PASS"}
    else:
        assert n == 32
        assert required_design_status(("FAIL",), ("MISSING",)) == "FAIL"
        assert required_design_status((), ("MISSING",)) == "ENGINEERING_REVIEW_REQUIRED"
        assert required_design_status((), ()) == "PASS"
        actual = {
            "order": [
                "FAIL",
                "ENGINEERING_REVIEW_REQUIRED",
                "PASS_WITH_COMPLETE_REQUIRED_COVERAGE_ONLY",
            ]
        }
    assert actual == expected


@pytest.mark.parametrize("case", DATA["negative_cases"], ids=lambda c: c["id"])
def test_approved_fail_closed_contract(case: dict[str, Any]) -> None:
    n, expected = int(case["id"][1:3]), case["expected_status"]
    request = map_ssmc_request(illustrative_ssmc())
    if n in {1, 2, 3}:
        with pytest.raises(ValueError, match=expected):
            replace(request, theta_deg=Decimal({1: 0, 2: 20, 3: 50}[n]))
    elif n in {4, 6, 7, 18, 35, 36}:
        changes: dict[int, dict[str, Any]] = {
            4: {"connector_body_count": 2},
            6: {"serial_action_factor": Decimal("0.5")},
            7: {"axial_row_fraction_mixing": True},
            18: {"polygon_authority": "CONVEX_HULL"},
            35: {"miter_contact_credit": True},
            36: {"hardware_shear_capacity_multiplier": Decimal(2)},
        }
        with pytest.raises(ValueError, match=expected):
            SSMCMethodPolicy(**changes[n])
    elif n == 5:
        record, ownership, targets = response_fixture()
        action = replace(record.actions[0], group_id=record.actions[-1].group_id)
        with pytest.raises(ValueError, match=expected):
            validate(replace(record, actions=(action, *record.actions[1:])), ownership, targets)
    elif n == 8:
        native_result = calculate_in_plane_wrench_demand(
            InPlaneWrenchRequest(
                (WrenchBolt("only", "0", "0"),),
                ("0", "0"),
                "0",
                "0",
                "20",
                Unit.IN,
                Unit.KIP,
                Unit.KIP_IN,
            )
        )
        assert native_result.status == expected
    elif n in {9, 10}:
        with pytest.raises(ValueError, match=expected):
            replace(request.horizontal_group, rows=1 if n == 9 else 4)
    elif n in {11, 12}:
        group = replace(
            request.horizontal_group, slots=n == 11, equal_translational_stiffness=n != 12
        )
        assert (
            preview_ssmc(replace(request, horizontal_group=group)).groups[0].planar_status
            == expected
        )
    elif n in {13, 14}:
        polygon = (
            ((0.0, 0.0), (3.0, 2.0), (0.0, 2.0), (2.0, 0.0))
            if n == 13
            else (
                (0.0, 0.0),
                (1.0, 0.0),
                (1.0, 1.0),
                (0.0, 1.0),
                (0.0, 0.0),
                (3.0, 0.0),
                (4.0, 0.0),
                (4.0, 1.0),
                (3.0, 1.0),
                (3.0, 0.0),
            )
        )
        with pytest.raises(ValueError, match=expected):
            validate_polygon(polygon)
    elif n == 15:
        with pytest.raises(ValueError, match=expected):
            construct_miter_polygon(35, 0, (0, 4), (8, 8))
    elif n in {16, 17}:
        with pytest.raises(ValueError, match=expected):
            preview_ssmc(
                replace(
                    request,
                    plate=replace(request.plate, horizontal_depth=inch("2" if n == 16 else "2.8")),
                )
            )
    elif n in {19, 31, 32, 33, 34}:
        result = preview_ssmc(request)
        assert expected in result.blockers
        assert not result.complete_moment_capacity_qualified
        assert all(g.prying is None and g.bolt_axis_tension is None for g in result.groups)
        assert any(m == "REENTRANT_CORNER" for _, m, _ in result.required_checks)
    elif n in {20, 23, 24}:
        assert (
            select_ssmc_property(
                "test", {20: "NORMAL_TENSION", 23: "NORMAL_COMPRESSION", 24: "FLEXURE"}[n]
            ).status
            == expected
        )
    elif n == 21:
        with pytest.raises(ValueError, match=expected):
            select_ssmc_property("test", "NORMAL_TENSION", isotropic=True)
    elif n == 22:
        property_record = SSMCQualifiedProperty(
            "test",
            "NORMAL_TENSION",
            "CW",
            Q.of(2, Unit.MPA),
            "a" * 64,
            "b" * 64,
            "TEST",
            True,
            Q.of(1, Unit.MPA),
        )
        assert (
            select_ssmc_property(
                "test", "NORMAL_TENSION", {("test", "NORMAL_TENSION"): property_record}
            ).status
            == expected
        )
    elif n == 25:
        assert (
            expected
            in preview_ssmc(replace(request, source_reference="APPROVED BY PUBLIC TEXT")).blockers
        )
    elif n in {26, 27, 28, 29, 30}:
        record, ownership, targets = response_fixture()
        if n in {26, 27}:
            changed = (
                replace(request, plate=replace(request.plate, thickness=inch("0.6")))
                if n == 26
                else replace(request, N=Q.of(1, Unit.KIP))
            )
            record = replace(record, binding=preview_ssmc(changed).engineering_fingerprint)
        elif n == 28:
            record = replace(record, shaft_ids=record.shaft_ids[1:])
        else:
            from frp_master_connection.application.ssmc import vector

            group_id = next(iter(targets))
            target = targets[group_id]
            target = replace(
                target,
                **{
                    "force" if n == 29 else "moment": vector(
                        (Decimal(1), Decimal(0), Decimal(0)), Unit.N if n == 29 else Unit.N_MM
                    )
                },
            )
            targets = targets | {group_id: target}
        with pytest.raises(ValueError, match=expected):
            validate(record, ownership, targets)
    elif n == 37:
        api_result = http(
            "POST",
            "/api/v1/calculations/stair-stringer-miter/preview?connector_body_material=SS316",
            illustrative_ssmc().model_dump(mode="json"),
        )
        assert api_result.status_code == 422
        assert api_result.json()["detail"]["code"] == expected
    elif n == 38:

        def inventory_guard(routes: set[str]) -> None:
            if len(routes) != 18 or "stair-stringer-miter" not in routes:
                raise ValueError("SSMC_SUCCESSOR_INVENTORY_MISMATCH")

        inventory_guard(set(FAMILIES))
        with pytest.raises(ValueError, match=expected):
            inventory_guard(set(FAMILIES) - {"stair-stringer-miter"})
    elif n == 39:
        assert required_design_status((), preview_ssmc(request).blockers) == expected
    else:
        assert n == 40
        # No-tags isolated clones verify the controlled freeze record. Local and
        # hosted publication preflight independently checks the actual Git ref.
        frozen = Path(__file__).parents[3] / "docs/governance/DCTN_3B_CONTINUATION_FREEZE.md"
        original = frozen.read_bytes()
        expected_digest = "8a4ccd484b265ffcd84ed014015540fe22317eef2ece27deae7b9f1dfd013c21"
        # The historical authority is the canonical Git text blob, independent
        # of checkout-only CRLF conversion on Windows.
        assert hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest() == expected_digest
        assert b"cf33dd5b939bbed35cb8bb1b770d9fe929e9152e" in original
        assert b"d556585c1b905532431e4ec9b7be9ab23acabc10" in original

        def frozen_guard(content: bytes) -> None:
            if hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest() != expected_digest:
                raise ValueError("FROZEN_BASELINE_MUTATION")

        with pytest.raises(ValueError, match=expected):
            frozen_guard(original.replace(b"cf33dd5", b"0000000"))
