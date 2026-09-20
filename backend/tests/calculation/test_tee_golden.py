"""Owner-controlled Stage 3.2 golden verification over accepted mechanics."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from frp_master_connection.application import (
    TeeAssemblyStatus,
    design_check_tee_connector,
    preview_tee_connector,
)
from frp_master_connection.calculation import Unit, calculate_eccentric_bolt_group_demand
from tests.calculation.test_eccentric_demand import _input
from tests.tee_fixtures import build_tee_request

_GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "stage_3_2_tee_connector_rc1.json"
_GOLDEN_SHA256 = "77FD574FC0EE55F565480E131FCDC3D334B8E7047D75FADC00C96979B31F1313"


def _golden() -> list[dict[str, Any]]:
    value = cast(dict[str, Any], json.loads(_GOLDEN_PATH.read_text(encoding="utf-8")))
    return cast(list[dict[str, Any]], value["benchmarks"])


def _case(identifier: str) -> dict[str, Any]:
    return next(item for item in _golden() if item["id"] == identifier)


def _kip_pairs(result: object) -> list[list[Decimal]]:
    scenario = result.scenarios[0]  # type: ignore[attr-defined]
    zero = Decimal("0")
    return [
        [
            item.total_force.u.to(Unit.KIP).magnitude.quantize(Decimal("0.000000000001")),
            (
                zero
                if abs(item.total_force.v.to(Unit.KIP).magnitude) < Decimal("1E-40")
                else item.total_force.v.to(Unit.KIP).magnitude
            ).quantize(Decimal("0.000000000001")),
        ]
        for item in scenario.per_bolt
    ]


def test_controlled_golden_identity_and_all_six_cases_are_present() -> None:
    assert hashlib.sha256(_GOLDEN_PATH.read_bytes()).hexdigest().upper() == _GOLDEN_SHA256
    assert [item["id"] for item in _golden()] == [
        "T32_G1_TWO_INTERFACE_ZERO_ECCENTRIC",
        "T32_G2_PHYSICAL_REFERENCE_ECCENTRIC_INTERFACE",
        "T32_G3_SUPPORT_ROLE_LOCAL_INVARIANCE",
        "T32_G4_INTERFACE_NORMAL_FAIL_CLOSED",
        "T32_G5_TEE_BODY_FAIL_CLOSED",
        "T32_G6_SUPPORTED_INTERFACE_FAILURE_GOVERNS",
    ]


def test_g1_two_interfaces_reproduce_equal_share_stage_2_5a_result() -> None:
    golden = _case("T32_G1_TWO_INTERFACE_ZERO_ECCENTRIC")
    expected = [
        [Decimal(pair[0]), Decimal(pair[1])]
        for pair in golden["expected"]["interface_A_per_bolt_Q_kip"]
    ]
    for key in ("interface_A_bolt_coordinates_in", "interface_B_bolt_coordinates_in"):
        result = calculate_eccentric_bolt_group_demand(
            _input(
                coordinates=tuple(tuple(item) for item in golden[key]),
                force=("3", "0", "0"),
                reference=("0", "0", "0"),
            )
        )
        assert _kip_pairs(result) == expected
        scenario = result.scenarios[0]
        assert scenario.external_moment.magnitude == 0
        assert scenario.residual_moment.magnitude == 0


def test_g2_physical_reference_produces_exact_accepted_eccentric_solution() -> None:
    golden = _case("T32_G2_PHYSICAL_REFERENCE_ECCENTRIC_INTERFACE")
    result = calculate_eccentric_bolt_group_demand(
        _input(
            coordinates=tuple(tuple(item) for item in golden["interface_B_bolt_coordinates_in"]),
            force=("3", "0", "0"),
            reference=("0", "0", "0"),
        )
    )
    expected = [
        [Decimal(pair[0]), Decimal(pair[1])]
        for pair in golden["expected"]["interface_B_per_bolt_Q_kip"]
    ]
    scenario = result.scenarios[0]

    assert result.geometric_bolt_centroid.u.to(Unit.IN).magnitude == Decimal("0")
    assert result.geometric_bolt_centroid.v.to(Unit.IN).magnitude == Decimal("2")
    assert result.polar_coordinate_sum.to(Unit.IN2).magnitude == Decimal("8.0000")
    assert scenario.external_moment.to(Unit.KIP_IN).magnitude == Decimal("6.00")
    assert scenario.residual_moment.to(Unit.KIP_IN).magnitude == Decimal("6.000")
    assert _kip_pairs(result) == expected


def test_g3_through_g6_control_the_integrated_tee_statuses() -> None:
    assert _case("T32_G3_SUPPORT_ROLE_LOCAL_INVARIANCE")["expected_local_demand_equal"] is True
    column = preview_tee_connector(build_tee_request(force=("0", "0", "3")))
    beam = preview_tee_connector(build_tee_request(role="BEAM", force=("3", "0", "0")))
    column_demand = column.interface_b.preview.automatic_demand_result
    beam_demand = beam.interface_b.preview.automatic_demand_result
    assert column_demand is not None
    assert beam_demand is not None
    assert column_demand.projected_force == beam_demand.projected_force
    assert column.engineering_fingerprint != beam.engineering_fingerprint

    normal_golden = _case("T32_G4_INTERFACE_NORMAL_FAIL_CLOSED")["expected"]
    normal = preview_tee_connector(build_tee_request(force=("0", "1", "3")))
    normal_component = normal.interface_a.normal_component
    assert normal_component is not None
    assert normal_component.to(Unit.KIP).magnitude == Decimal("-1.0")
    assert (
        normal.interface_a.automatic_axis_tension_generated
        is normal_golden["automatic_axis_tension_generated"]
    )
    assert normal.ordinary_pass_allowed is normal_golden["ordinary_whole_connection_pass_allowed"]

    g5 = _case("T32_G5_TEE_BODY_FAIL_CLOSED")["expected"]
    no_failure = design_check_tee_connector(build_tee_request(force=("0", "0", ".001")))
    assert no_failure.assembly_status.value == g5["whole_connection_status"]
    assert (
        no_failure.supported_interface_failure_present is g5["supported_interface_failure_present"]
    )
    assert no_failure.ordinary_pass_allowed is g5["ordinary_pass_allowed"]

    g6 = _case("T32_G6_SUPPORTED_INTERFACE_FAILURE_GOVERNS")["expected"]
    failure = design_check_tee_connector(build_tee_request(force=("0", "0", "3")))
    assert failure.assembly_status is TeeAssemblyStatus.FAIL
    assert failure.assembly_status.value == g6["whole_connection_status"]
    assert failure.supported_interface_failure_present is g6["supported_interface_failure_present"]
