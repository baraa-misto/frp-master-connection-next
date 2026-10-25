"""R1 independent end-authority, applicability and signed-report regressions."""

from __future__ import annotations

import io
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
from typing import Any, cast

import pytest
from pypdf import PdfReader
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body, owner_request

from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application.direct_support_ends import (
    DirectSupportEndCondition,
    DirectSupportEndInput,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

PREVIEW = "/api/v1/calculations/multi-row/preview"
DESIGN = "/api/v1/frp-materials/multi-row/design-check"
OUTCOME_OK = "PASS"


def r1_request(
    condition: str = "CONTINUOUS_THROUGH_CONNECTION",
    *,
    angle: str = "135",
    si: bool = False,
    above: str = "12",
    below: str = "12",
    rows: int = 2,
    lines: int = 1,
) -> dict[str, Any]:
    request = owner_request(si=si, one_row=rows == 1)
    request["row_count"] = rows
    request["bolts_per_row"] = lines
    request["physical_connection"]["geometry_template"]["brace_to_column_directed_angle_deg"] = (
        angle
    )
    scale = Decimal("25.4") if si else Decimal(1)
    declaration: dict[str, Any] = {"condition": condition}
    with localcontext() as context:
        context.prec = 100
        if condition in {"FINITE_BOTH_ENDS", "FINITE_POSITIVE_END_ONLY"}:
            declaration["positive_end_distance"] = {
                "value": str(Decimal(above) * scale),
                "unit": request["source_length_unit"],
            }
        if condition in {"FINITE_BOTH_ENDS", "FINITE_NEGATIVE_END_ONLY"}:
            declaration["negative_end_distance"] = {
                "value": str(Decimal(below) * scale),
                "unit": request["source_length_unit"],
            }
    request["supporting_w_longitudinal_ends"] = declaration
    return request


def r1_preview(request: dict[str, Any]) -> dict[str, Any]:
    response = call("POST", PREVIEW, request)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def r1_design(request: dict[str, Any]) -> dict[str, Any]:
    body = owner_body(si=request["source_length_unit"] == "mm", one_row=request["row_count"] == 1)
    body["legacy_request"] = request
    response = call("POST", DESIGN, body)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def w_checks(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        c
        for f in data["direct_engineering_geometry"]
        if f["component_id"] == "member-b"
        for c in f["checks"]
    ]


@pytest.mark.parametrize("declared", [False, True])
def test_blank_project_has_no_implicit_end_authority(declared: bool) -> None:
    request = r1_request("UNSPECIFIED")
    if not declared:
        request.pop("supporting_w_longitudinal_ends")
    data = r1_preview(request)
    assert not data["design_check_ready"]
    assert data["direct_support_end_authority"]["condition"] == "UNSPECIFIED"
    assert any(w.startswith("INPUT_NEEDED:") for w in data["warnings"])
    assert not any(c["check_kind"] == "CHAPTER_8_END_DISTANCE" for c in w_checks(data))


@pytest.mark.parametrize("angle", ["45", "135"])
@pytest.mark.parametrize("si", [False, True])
def test_continuous_support_has_no_crop_checks_and_keeps_angle_e1(angle: str, si: bool) -> None:
    data = r1_preview(r1_request(angle=angle, si=si))
    assert data["geometry_status"] == "VALID"
    assert data["design_check_ready"]
    authority = data["direct_support_end_authority"]
    assert authority["negative_end_member_local_station"] is None
    assert authority["positive_end_member_local_station"] is None
    assert all(
        r["loaded_end_state"] == "NO_FINITE_END_IN_DIRECTION" for r in authority["bolt_records"]
    )
    assert all(c["engineering_boundary_role"] != "VIEW_CROP" for c in w_checks(data))
    assert all(c["pass_fail"] == OUTCOME_OK for c in w_checks(data))
    face = next(
        f
        for f in data["direct_engineering_geometry"]
        if f["component_id"] == "member-a" and f["bolt_id"] == "B_R1_L1"
    )
    end = next(c for c in face["checks"] if c["check_kind"] == "CHAPTER_8_END_DISTANCE")
    assert Decimal(end["actual_distance"]) == Decimal(3) * (Decimal("25.4") if si else 1)


@pytest.mark.parametrize(
    "condition", ["FINITE_BOTH_ENDS", "FINITE_POSITIVE_END_ONLY", "FINITE_NEGATIVE_END_ONLY"]
)
@pytest.mark.parametrize("angle", ["45", "135"])
def test_real_end_conditions_are_independent_and_load_selected(condition: str, angle: str) -> None:
    data = r1_preview(r1_request(condition, angle=angle))
    authority = data["direct_support_end_authority"]
    assert data["geometry_status"] == "VALID"
    expected = "POSITIVE_ABOVE" if angle == "45" else "NEGATIVE_BELOW"
    assert all(r["loaded_end_direction"] == expected for r in authority["bolt_records"])
    real = [
        b
        for f in data["direct_engineering_geometry"]
        if f["component_id"] == "member-b"
        for b in f["boundaries"]
        if b["role"] == "REAL_SUPPORT_MEMBER_END"
    ]
    assert len(real) == (4 if condition == "FINITE_BOTH_ENDS" else 2)
    assert all(Decimal(b["actual_distance"]) != 3 for b in real)


@pytest.mark.parametrize(
    ("difference", "passes"),
    [("-0.000000001", False), ("0", True), ("0.000000001", True), ("-0.914", False)],
)
@pytest.mark.parametrize("si", [False, True])
def test_real_finite_end_exact_boundary(difference: str, passes: bool, si: bool) -> None:
    base = r1_preview(r1_request(angle="45"))
    record = next(
        r for r in base["direct_support_end_authority"]["bolt_records"] if r["bolt_id"] == "B_R1_L1"
    )
    with localcontext() as context:
        context.prec = 100
        distance = str(
            Decimal(record["canonical_reference_offset"]) + Decimal(1) + Decimal(difference)
        )
    data = r1_preview(r1_request("FINITE_POSITIVE_END_ONLY", angle="45", si=si, above=distance))
    check = next(
        c
        for c in w_checks(data)
        if c["bolt_id"] == "B_R1_L1" and c["check_kind"] == "CHAPTER_8_END_DISTANCE"
    )
    assert (check["pass_fail"] == OUTCOME_OK) is passes
    assert check["engineering_boundary_role"] == "REAL_SUPPORT_MEMBER_END"
    with localcontext() as context:
        context.prec = 100
        assert Decimal(check["actual_distance"]) == (Decimal(1) + Decimal(difference)) * (
            Decimal("25.4") if si else 1
        )


@pytest.mark.parametrize("condition", ["CONTINUOUS_THROUGH_CONNECTION", "FINITE_BOTH_ENDS"])
def test_presentation_extent_does_not_change_engineering_or_result_currency(condition: str) -> None:
    request = r1_request(condition)
    before = r1_preview(request)
    changed = deepcopy(request)
    changed["physical_connection"]["view_extents"] = {
        name: {"value": "40", "unit": "in"}
        for name in ("brace_view_length", "column_view_extent_above", "column_view_extent_below")
    }
    after = r1_preview(changed)
    assert before["preview_fingerprint"] == after["preview_fingerprint"]
    assert before["direct_engineering_geometry"] == after["direct_engineering_geometry"]
    old_authority, new_authority = (
        deepcopy(before["direct_support_end_authority"]),
        deepcopy(after["direct_support_end_authority"]),
    )
    old_authority.pop("presentation_crop_member_local_stations")
    new_authority.pop("presentation_crop_member_local_stations")
    assert old_authority == new_authority
    a, b = r1_design(request)["native_design"], r1_design(changed)["native_design"]
    assert a["automatic_group_mode_integration"] == b["automatic_group_mode_integration"]
    assert a["automatic_demand_result"] == b["automatic_demand_result"]
    # An absent physical presentation must not erase declared geometry authority.
    from frp_master_connection.application import multirow_orchestration as orchestration

    native_request = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(request))
    native_visual = orchestration._resolve(native_request).visualization
    logical = json.loads(
        orchestration._canonical_multirow_preview_json(
            native_request, replace(native_visual, physical_connection=None)
        )
    )
    assert logical["visualization"]["physical_connection"] is None
    assert logical["request"]["supporting_w_longitudinal_ends"]["condition"] == condition


@pytest.mark.parametrize("condition", ["CONTINUOUS_THROUGH_CONNECTION", "FINITE_BOTH_ENDS"])
@pytest.mark.parametrize("rows", [1, 2, 3])
def test_w_end_dependent_checks_cannot_execute_angle_template(condition: str, rows: int) -> None:
    request = r1_request(condition, rows=rows)
    if rows == 3:
        from tests.application.test_direct_f1_safety import _direct_payload

        request = cast(dict[str, Any], _direct_payload())
        request["row_count"] = 3
        request["loaded_boundary_to_row_1_distance"]["value"] = "5"
        request["supporting_w_longitudinal_ends"] = r1_request(condition)[
            "supporting_w_longitudinal_ends"
        ]
    data = r1_design(request)["native_design"]
    integration = data["automatic_group_mode_integration"]
    for scenario in integration["scenario_results"]:
        assert not any(
            c["result_id"].startswith(
                ("FIRST_ROW:layer-B:", "INTERROW:layer-B:", "BLOCK_SHEAR:layer-B:")
            )
            for c in scenario["supported_results"]
        )
    if rows == 1:
        single = integration["direct_single_row_result"]
        for check in single["checks"]:
            if check["layer_id"] == "layer-B":
                assert check["availability"] in {"CALCULATION_NOT_SUPPORTED", "NOT_APPLICABLE"}
                assert check["design_resistance"] is None
                assert check["equation_trace"] is None


@pytest.mark.parametrize("condition", list(DirectSupportEndCondition))
def test_end_input_validates_exact_selected_fields(condition: DirectSupportEndCondition) -> None:
    payload = r1_request(condition.value)
    declaration = MultiRowConnectionRequestDTO.model_validate(
        payload
    ).supporting_w_longitudinal_ends
    assert declaration is not None
    for name in ("negative_end_distance", "positive_end_distance"):
        invalid = deepcopy(payload)
        end = invalid["supporting_w_longitudinal_ends"]
        if name in end:
            end.pop(name)
        else:
            end[name] = {"value": "12", "unit": "in"}
        with pytest.raises(ValueError, match="exactly"):
            MultiRowConnectionRequestDTO.model_validate(invalid)


@pytest.mark.parametrize(("value", "unit"), [("0", Unit.IN), ("-1", Unit.MM), ("1", Unit.N)])
def test_invalid_real_end_distance_rejected(value: str, unit: Unit) -> None:
    with pytest.raises(ValueError, match="positive"):
        DirectSupportEndInput(
            DirectSupportEndCondition.FINITE_POSITIVE_END_ONLY,
            positive_end_distance=PhysicalQuantity.of(value, unit),
        )


def test_cross_family_end_contract_and_invalid_enum_are_rejected() -> None:
    request = r1_request()
    request.pop("direct_finalization_contract_version")
    with pytest.raises(ValueError, match="only by Direct"):
        MultiRowConnectionRequestDTO.model_validate(request)
    with pytest.raises(TypeError, match="governed enum"):
        DirectSupportEndInput(cast(DirectSupportEndCondition, "CONTINUOUS_THROUGH_CONNECTION"))
    mapped = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(r1_request()))
    assert mapped.supporting_w_longitudinal_ends is not None


@pytest.mark.parametrize("condition", list(DirectSupportEndCondition))
def test_report_preserves_signed_end_authority_and_audit(
    condition: DirectSupportEndCondition,
) -> None:
    request = r1_request(condition.value)
    body = owner_body()
    body["legacy_request"] = request
    result = r1_design(request)
    signer = SnapshotSigner(b"DIRECT-R1-END-AUTHORITY-32-BYTES-KEY")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="r1"
        ),
        account_id="r1",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions())
    text = " ".join(
        " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    assert "Supporting W longitudinal condition" in text
    assert "Angle e1 does not supply W end authority" in text
    assert "W end above - from fixed connection reference" in text
    assert (
        "presentation-only" in text
        if condition is DirectSupportEndCondition.CONTINUOUS_THROUGH_CONNECTION
        else "Supporting W" in text
    )
    assert (snapshot.request, snapshot.result) == original
    if condition is DirectSupportEndCondition.CONTINUOUS_THROUGH_CONNECTION:
        # Older authenticated reports lack the additive R1 authority metadata.
        # Their stored method limitation must remain readable and unmodified.
        historical_result = deepcopy(snapshot.result)
        historical_result["native_design"]["preview"].pop("direct_support_end_authority")
        historical_request = deepcopy(snapshot.request)
        historical_request["legacy_request"].pop("supporting_w_longitudinal_ends")
        historical_snapshot = signer.verify(
            signer.issue(
                family="multi-row",
                kind="design",
                request=historical_request,
                result=historical_result,
                account_id="r1",
            ),
            account_id="r1",
        )
        historical_before = deepcopy(historical_result)
        historical_pdf = render_report_pdf(historical_snapshot, ReportOptions())
        historical_text = " ".join(
            " ".join(
                page.extract_text() or "" for page in PdfReader(io.BytesIO(historical_pdf)).pages
            ).split()
        )
        assert "Required W top-flange oblique block shear: approved method unavailable" in (
            historical_text
        )
        assert historical_snapshot.result == historical_before


def test_fixed_reference_and_real_ends_do_not_move_with_layout_or_orientation() -> None:
    request = r1_request("FINITE_BOTH_ENDS")
    base = r1_preview(request)["direct_support_end_authority"]
    for angle, rows, pitch, lines in (("45", 2, "2", 1), ("90", 3, "1.5", 2), ("135", 1, "3", 1)):
        changed = deepcopy(request)
        changed["row_count"], changed["bolts_per_row"] = rows, lines
        changed["pitch"]["value"] = pitch
        changed["physical_connection"]["geometry_template"][
            "brace_to_column_directed_angle_deg"
        ] = angle
        after = r1_preview(changed)["direct_support_end_authority"]
        assert after["reference_global"] == base["reference_global"]
        assert after["negative_end_global"] == base["negative_end_global"]
        assert after["positive_end_global"] == base["positive_end_global"]


def test_raw_w_coordinate_witness_cannot_disagree_with_canonical_native_layout() -> None:
    from frp_master_connection.application import multirow_orchestration as orchestration
    from frp_master_connection.application.direct_support_ends import resolve_direct_support_ends

    request = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(r1_request()))
    resolved = orchestration._resolve(request)
    visual = resolved.visualization
    physical = visual.physical_connection
    assert physical is not None
    assert request.physical_connection_request is not None
    axes = orchestration._exact_template_group_axes(request.physical_connection_request)
    assert axes is not None
    assert visual.connection_demand is not None
    force = visual.connection_demand.axis
    with pytest.raises(ValueError, match="station and native"):
        resolve_direct_support_ends(
            DirectSupportEndInput(DirectSupportEndCondition.CONTINUOUS_THROUGH_CONNECTION),
            physical,
            tuple(b.display for b in visual.physical_bolts),
            interface_id=request.physical_connection_request.interface_id,
            anchor_x=request.unloaded_end_e1.magnitude,
            native_centers={b.bolt_id: (b.x + 1, b.y) for b in visual.bolts},
            template_axes=axes,
            force_global=(force.x, force.y, force.z),
        )
    missing = replace(request, supporting_w_longitudinal_ends=None)
    assert missing.supporting_w_longitudinal_ends == DirectSupportEndInput()


def test_no_support_end_is_inferred_without_canonical_template_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.application import multirow_orchestration as orchestration

    request = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(r1_request()))
    monkeypatch.setattr(orchestration, "_exact_template_group_axes", lambda _: None)
    preview = orchestration.preview_multirow_connection(request)
    assert not preview.design_check_ready
    assert any("DIRECT_SUPPORT_END_CANONICAL_TEMPLATE_REQUIRED" in w for w in preview.warnings)


def test_reversing_real_load_selects_existing_opposite_end_without_moving_ends() -> None:
    request = r1_request("FINITE_BOTH_ENDS", angle="45", above="12", below="15")
    before = r1_preview(request)["direct_support_end_authority"]
    request["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["x"] = "-0.7"
    after = r1_preview(request)["direct_support_end_authority"]
    for field in ("reference_global", "negative_end_global", "positive_end_global"):
        assert before[field] == after[field]
    assert {b["loaded_end_direction"] for b in before["bolt_records"]} == {"POSITIVE_ABOVE"}
    assert {b["loaded_end_direction"] for b in after["bolt_records"]} == {"NEGATIVE_BELOW"}


def test_finite_authority_and_per_bolt_distances_have_exact_us_si_parity() -> None:
    us = r1_preview(r1_request("FINITE_BOTH_ENDS", angle="45"))["direct_support_end_authority"]
    si = r1_preview(r1_request("FINITE_BOTH_ENDS", angle="45", si=True))[
        "direct_support_end_authority"
    ]
    with localcontext() as context:
        context.prec = 100
        for field in (
            "reference_member_local_station",
            "negative_end_member_local_station",
            "positive_end_member_local_station",
        ):
            assert Decimal(si[field]) == Decimal(us[field]) * Decimal("25.4")
        for a, b in zip(us["bolt_records"], si["bolt_records"], strict=True):
            for field in (
                "canonical_reference_offset",
                "negative_end_distance",
                "positive_end_distance",
                "loaded_end_distance",
            ):
                assert Decimal(b[field]) == Decimal(a[field]) * Decimal("25.4")
            assert a["loaded_end_direction"] == b["loaded_end_direction"]


def test_actual_end_edit_changes_engineering_preview_identity() -> None:
    before = r1_preview(r1_request("FINITE_BOTH_ENDS", above="12"))
    after = r1_preview(r1_request("FINITE_BOTH_ENDS", above="13"))
    assert before["preview_fingerprint"] != after["preview_fingerprint"]
    assert (
        before["direct_support_end_authority"]["positive_end_global"]
        != after["direct_support_end_authority"]["positive_end_global"]
    )
