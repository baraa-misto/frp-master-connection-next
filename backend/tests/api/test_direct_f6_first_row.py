"""F6 source gates and immutable report-only interpretation of Direct snapshots."""

from __future__ import annotations

import io
from copy import deepcopy
from decimal import Decimal, localcontext
from typing import Any

import pytest
from pypdf import PdfReader
from tests.api.test_appendix_rc3_direct_parity import BASELINE, direct_projection
from tests.api.test_f593_f4 import design, supported
from tests.calculation.test_appendix_rc3 import arguments, values

from frp_master_connection.calculation.appendix_rc3 import full_first_row_resistance_rc3
from frp_master_connection.reporting.direct_first_row import direct_first_row_reason
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def f6_cases() -> dict[str, dict[str, Any]]:
    """Independent signed design controls; only owner is the owner geometry."""

    owner = deepcopy(BASELINE["request"])
    controls = {"owner-135": owner}
    fortyfive = deepcopy(owner)
    fortyfive["legacy_request"]["physical_connection"]["geometry_template"][
        "brace_to_column_directed_angle_deg"
    ] = "45"
    controls["control-45"] = fortyfive
    finite = deepcopy(owner)
    finite["legacy_request"]["supporting_w_longitudinal_ends"] = {
        "condition": "FINITE_BOTH_ENDS",
        "negative_end_distance": {"value": "20", "unit": "in"},
        "positive_end_distance": {"value": "20", "unit": "in"},
    }
    controls["finite-w"] = finite
    three = deepcopy(owner)
    three["legacy_request"]["row_count"] = 3
    three["legacy_request"]["physical_connection"]["joint_assembly"]["members"][1]["section"][
        "flange_width"
    ]["value"] = "12"
    controls["three-row"] = three
    zero = deepcopy(owner)
    action = zero["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][
        0
    ]
    action["coordinate_frame_kind"] = "BOLT_GROUP_LOCAL"
    action["coordinate_frame_owner_id"] = "bolt-group-1"
    action["force"] = {"x": "0", "y": ".7", "z": "0", "unit": "kip"}
    action["reference_point"] = {
        "kind": "BOLT_GROUP_ORIGIN",
        "owner_id": "bolt-group-1",
        "position": None,
    }
    controls["zero-eccentricity"] = zero
    inside = deepcopy(zero)
    inside["legacy_request"]["unloaded_end_e1"]["value"] = "2"
    inside["legacy_request"]["loaded_boundary_to_row_1_distance"]["value"] = "2"
    inside["legacy_request"]["physical_connection"]["geometry_template"][
        "bolt_to_brace_end_distance"
    ]["value"] = "2"
    controls["inside-e1-envelope"] = inside
    from tests.api.test_asce_shape_f5 import f5_body

    controls["si-owner"] = f5_body(si=True)
    along = deepcopy(zero)
    along["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
        "force"
    ]["z"] = ".001"
    controls["real-along-row-force"] = along
    return controls


@pytest.mark.parametrize("name", list(f6_cases()))
def test_actual_direct_first_row_cannot_execute_unproved_template_plan(name: str) -> None:
    result = design(f6_cases()[name])
    native = result["native_design"]
    integration = native["automatic_group_mode_integration"]
    assert native["preview"]["geometry_status"] != "INVALID_GEOMETRY"
    if name == "real-along-row-force":
        assert integration is None
        assert not native["preview"]["design_check_ready"]
        assert Decimal(native["automatic_demand_result"]["projected_force"]["v"]["canonical_value"])
        return
    assert {"FIRST_ROW:layer-A", "FIRST_ROW:layer-B"} <= set(
        integration["unsupported_required_check_ids"]
    )
    assert not any(check["limit_state"] == "FIRST_ROW_NET_TENSION" for check in supported(result))
    assert not any("RC3" in str(check) for check in supported(result))
    if name == "zero-eccentricity":
        assert (
            native["automatic_demand_result"]["scenarios"][0]["residual_moment"]["canonical_value"]
            == "0"
        )


def test_owner_seven_checks_retain_exact_parity_after_authorized_f7_schedule_delta() -> None:
    actual = direct_projection()
    assert [c for c in actual["checks"] if c["limit_state"] != "BLOCK_SHEAR"] == BASELINE[
        "expected"
    ]["checks"]
    assert (
        actual["integration"]["required_check_ids"]
        == BASELINE["expected"]["integration"]["required_check_ids"]
    )


@pytest.mark.parametrize(
    ("identity", "moment", "expected"),
    [
        ("FIRST_ROW:layer-A", "1", "external eccentric moment"),
        ("FIRST_ROW:layer-A", "-1", "external eccentric moment"),
        ("FIRST_ROW:layer-A", "0", "physical Figure C8-11 effective width"),
        ("FIRST_ROW:layer-B", "0", "oblique net-section plane"),
        ("FIRST_ROW:layer-B", "1", "eccentric stress"),
        ("FIRST_ROW:layer-B", "1E-88", "eccentric stress"),
    ],
)
def test_reason_uses_actual_residual_with_no_tolerance_or_engineering_change(
    identity: str, moment: str, expected: str
) -> None:
    result = {
        "automatic_demand_result": {"scenarios": [{"residual_moment": {"canonical_value": moment}}]}
    }
    before = deepcopy(result)
    assert expected in str(direct_first_row_reason(identity, result))
    assert result == before


def test_missing_demand_and_nonfirstrow_do_not_fabricate_engineering() -> None:
    assert direct_first_row_reason("BOLT_SHEAR:bolt", {}) is None
    assert "authenticated first-row demand" in str(direct_first_row_reason("FIRST_ROW:layer-A", {}))


@pytest.mark.parametrize("case", ["owner-135", "zero-eccentricity", "si-owner"])
def test_actual_engineer_pdf_preserves_snapshot_and_states_exact_first_row_reason(
    case: str,
) -> None:
    body = f6_cases()[case]
    result = design(body)
    signer = SnapshotSigner(b"DIRECT-F6-REPORT-IMMUTABILITY-32-BYTE-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f6"
        ),
        account_id="f6",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions())
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "METHOD REQUIRED" in text
    assert (
        "external eccentric moment" if case != "zero-eccentricity" else "physical Figure C8-11"
    ) in text
    assert "oblique net-section plane" in text
    assert (snapshot.request, snapshot.result) == before


def test_rc3_single_lap_factor_is_applied_exactly_once_in_coefficient_only_qa() -> None:
    from tests.calculation.test_appendix_rc3 import CASES

    kwargs = arguments(CASES[0])
    single = full_first_row_resistance_rc3(**(kwargs | {"lap_factor_c_lap": Decimal(".6")}))
    double = full_first_row_resistance_rc3(**(kwargs | {"lap_factor_c_lap": Decimal(1)}))
    with localcontext() as context:
        context.prec = 60
        assert (
            single.factor_trace.design_resistance
            == double.factor_trace.design_resistance * Decimal(".6")
        )
    assert values(single)["knt"] == values(double)["knt"]
