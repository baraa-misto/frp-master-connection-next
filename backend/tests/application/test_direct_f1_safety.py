"""Focused physical and source gates for the versioned Direct candidate route."""

from __future__ import annotations

import hashlib
import io
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pypdf import PdfReader

from frp_master_connection.api.multirow_mapping import (
    map_multirow_request,
    serialize_multirow_design,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import (
    MultiRowOrchestrationRequest,
    evaluate_multirow_connection,
    preview_multirow_connection,
)
from frp_master_connection.calculation import GeometryStatus, MaterialDirection
from frp_master_connection.calculation.inputs import LapConfiguration, create_lap_factor_plan
from frp_master_connection.reporting.pdf import (
    ReportOptions,
    render_multirow_pdf,
    render_report_pdf,
)
from frp_master_connection.reporting.reader_views import multirow_physical_geometry
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.test_multirow_api import DESIGN_ROUTE, PREVIEW_ROUTE, _automatic_payload, _post, _q


def _direct_payload(*, physically_contained: bool = True) -> dict[str, object]:
    payload = _automatic_payload(zero_moments=True)
    payload["direct_finalization_contract_version"] = "SHEAR01-DIRECT-F1"
    payload["lap_configuration"] = "SINGLE_LAP"
    legacy_layer = cast(dict[str, object], cast(list[object], payload["layers"])[0])
    payload["layers"] = [
        {**legacy_layer, "layer_id": "layer-A", "component_id": "member-a"},
        {
            **legacy_layer,
            "layer_id": "layer-B",
            "component_id": "member-b",
            "thickness": _q(".5", "in"),
        },
    ]
    if physically_contained:
        physical = cast(dict[str, object], payload["physical_connection"])
        members = cast(
            list[dict[str, object]], cast(dict[str, object], physical["joint_assembly"])["members"]
        )
        angle = cast(dict[str, object], members[0]["section"])
        w_section = cast(dict[str, object], members[1]["section"])
        cast(dict[str, str], angle["leg_y"])["value"] = "8"
        cast(dict[str, str], angle["leg_z"])["value"] = "8"
        cast(dict[str, str], w_section["flange_width"])["value"] = "16"
        template = cast(dict[str, object], physical["geometry_template"])
        template["brace_to_column_directed_angle_deg"] = "135"
        cast(dict[str, str], template["bolt_to_brace_end_distance"])["value"] = "6"
        cast(dict[str, str], cast(dict[str, object], payload["unloaded_end_e1"]))["value"] = "6"
        cast(dict[str, str], cast(dict[str, object], payload["loaded_boundary_to_row_1_distance"]))[
            "value"
        ] = "4"
    return payload


def _request(payload: dict[str, object]) -> MultiRowOrchestrationRequest:
    return map_multirow_request(MultiRowConnectionRequestDTO.model_validate(payload))


def _one_row_payload(bolts_per_row: int, *, force: str = ".7") -> dict[str, object]:
    payload = _direct_payload()
    payload["row_count"] = 1
    payload["bolts_per_row"] = bolts_per_row
    local = _automatic_payload(zero_moments=True, group_local=True)
    local_physical = cast(dict[str, object], local["physical_connection"])
    local_assembly = cast(dict[str, object], local_physical["joint_assembly"])
    action = deepcopy(cast(list[dict[str, object]], local_assembly["member_end_actions"])[0])
    cast(dict[str, str], action["force"])["y"] = force
    physical = cast(dict[str, object], payload["physical_connection"])
    assembly = cast(dict[str, object], physical["joint_assembly"])
    cast(list[dict[str, object]], assembly["member_end_actions"])[0] = action
    return payload


def _factor_traces(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        traces = [value] if "c_lap" in value and "nominal_resistance" in value else []
        return traces + [trace for nested in value.values() for trace in _factor_traces(nested)]
    if isinstance(value, list):
        return [trace for nested in value for trace in _factor_traces(nested)]
    return []


def test_direct_lap_contract_rejects_all_double_lap_and_mismatched_states() -> None:
    valid = _request(_direct_payload())
    assert valid.lap_configuration is LapConfiguration.SINGLE_LAP
    assert valid.physical_connection_request is not None
    assert valid.physical_connection_request.lap_configuration is LapConfiguration.SINGLE_LAP
    for calculation_lap, physical_lap in (
        ("DOUBLE_LAP", "SINGLE_LAP"),
        ("SINGLE_LAP", "DOUBLE_LAP"),
        ("DOUBLE_LAP", "DOUBLE_LAP"),
    ):
        payload = _direct_payload()
        payload["lap_configuration"] = calculation_lap
        physical = cast(dict[str, object], payload["physical_connection"])
        physical["lap_configuration"] = physical_lap
        with pytest.raises(ValueError, match="DIRECT_PHYSICAL_LAP_CONTRACT"):
            _request(payload)


@pytest.mark.parametrize("route", [PREVIEW_ROUTE, DESIGN_ROUTE])
def test_direct_api_rejects_contradictory_lap_with_clear_422(route: str) -> None:
    payload = _direct_payload()
    payload["lap_configuration"] = "DOUBLE_LAP"
    response = _post(route, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_MAPPING_INVALID"
    assert "DIRECT_PHYSICAL_LAP_CONTRACT" in response.json()["detail"]["message"]


def test_direct_single_lap_reduces_each_executed_frp_resistance_and_not_steel() -> None:
    plan = create_lap_factor_plan(LapConfiguration.SINGLE_LAP)
    assert plan.applicable_in_plane_frp_factor == Decimal("0.60")
    assert not plan.applies_to_metallic_bolt
    assert not plan.applies_to_pull_through
    for count in (1, 2, 3):
        design = evaluate_multirow_connection(_request(_one_row_payload(count)))
        native = serialize_multirow_design(design).model_dump()
        local = cast(
            dict[str, object],
            cast(dict[str, object], native["automatic_group_mode_integration"])[
                "direct_single_row_result"
            ],
        )
        checks = cast(list[dict[str, object]], local["checks"])
        evaluated = [check for check in checks if check["availability"] == "CALCULATED"]
        assert {check["layer_id"] for check in evaluated} == {"layer-A", "layer-B"}
        assert {check["limit_state"] for check in evaluated} >= {
            "SINGLE_ROW_NET_TENSION",
            "SINGLE_ROW_SHEAR_OUT",
        }
        for check in evaluated:
            traces = _factor_traces(check["equation_trace"])
            assert traces, check["result_id"]
            assert all(Decimal(str(trace["c_lap"])) == Decimal("0.6") for trace in traces)
            resistance = cast(dict[str, str], check["design_resistance"])
            demand = cast(dict[str, str], check["demand"])
            actual = Decimal(resistance["canonical_value"])
            assert actual > 0
            utilization = Decimal(str(check["utilization"]))
            expected_utilization = Decimal(demand["canonical_value"]) / actual
            assert abs(utilization - expected_utilization) < Decimal("1e-18")
            candidate_resistances: list[Decimal] = []
            for trace in traces:
                nominal = cast(dict[str, str], trace["nominal_resistance"])
                expected = Decimal(nominal["canonical_value"])
                for factor in ("c_delta", "c_lap", "phi", "lambda_factor"):
                    expected *= Decimal(str(trace[factor]))
                candidate_resistances.append(expected)
            assert abs(actual - min(candidate_resistances)) <= actual * Decimal("1e-18")
        handoffs = cast(list[dict[str, object]], native["automatic_handoff_results"])
        bolt_checks = [
            check
            for handoff in handoffs
            for check in cast(list[dict[str, object]], handoff["checks"])
            if check.get("family") == "BOLT_SHEAR"
        ]
        assert bolt_checks
        assert all(check["availability"] == "SOURCE_DATA_PENDING" for check in bolt_checks)
        assert all(not _factor_traces(check) for check in bolt_checks)


def test_direct_multirow_bearing_traces_use_physical_single_lap() -> None:
    native = serialize_multirow_design(
        evaluate_multirow_connection(_request(_direct_payload()))
    ).model_dump()
    handoffs = cast(list[dict[str, object]], native["automatic_handoff_results"])
    bearing = [
        check
        for handoff in handoffs
        for check in cast(list[dict[str, object]], handoff["supported_results"])
        if check["limit_state"] == "PIN_BEARING"
    ]
    assert {check["layer_id"] for check in bearing} == {"layer-A", "layer-B"}
    assert all(
        Decimal(str(cast(dict[str, object], check["factor_trace"])["c_lap"])) == Decimal("0.6")
        for check in bearing
    )


def test_direct_valid_two_layer_fixture_keeps_oblique_w_block_path_unevaluated() -> None:
    request = _request(_direct_payload())
    preview = preview_multirow_connection(request)
    assert preview.geometry_status is GeometryStatus.VALID
    assert preview.visualization is not None
    assert len(preview.visualization.physical_bolts) == 4
    assert [item.material_direction for item in preview.visualization.layers] == [
        MaterialDirection.LONGITUDINAL,
        MaterialDirection.TRANSVERSE,
    ]
    design = evaluate_multirow_connection(request)
    assert design.automatic_group_mode_integration is not None
    assert any(
        item.startswith("BLOCK_SHEAR:layer-B:")
        for item in design.automatic_group_mode_integration.unsupported_required_check_ids
    )
    assert "BOLT_SHEAR:B_R1_L1" in (
        design.automatic_group_mode_integration.incomplete_required_check_ids
    )
    assert "DIRECT_WHOLE_CONNECTION_SECTION_2_3_2_QUALIFICATION" in (
        design.automatic_group_mode_integration.incomplete_required_check_ids
    )
    assert design.automatic_group_mode_integration.overall_disposition.value != "PASS"
    native_visual = serialize_multirow_design(design).model_dump()["preview"]["visualization"]
    physical_parts, bolt_paths = multirow_physical_geometry(native_visual)
    assert {part.identity for part in physical_parts} == {
        "LEG_1",
        "LEG_2",
        "TOP_FLANGE",
        "WEB",
        "BOTTOM_FLANGE",
    }
    assert len(bolt_paths) == 4
    assert all(bolt.start is not None and bolt.end is not None for bolt in bolt_paths)
    assert all(bolt.washer_diameter == 1 for bolt in bolt_paths)


def test_direct_historical_two_by_two_fixture_is_physically_invalid() -> None:
    request = _request(_direct_payload(physically_contained=False))
    preview = preview_multirow_connection(request)
    assert preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert any(
        "DIRECT_PHYSICAL_CONTAINMENT:B_R" in item and ":member-b:TOP_FLANGE" in item
        for item in preview.warnings
    )
    assert all(
        "unit=in" in item
        for item in preview.warnings
        if item.startswith("DIRECT_PHYSICAL_CONTAINMENT:")
    )
    assert evaluate_multirow_connection(request).calculation_result is None


def test_direct_bolt_ids_follow_canonical_force_directed_rows() -> None:
    for row_count in (1, 2, 3):
        payload = _one_row_payload(1) if row_count == 1 else _direct_payload()
        payload["row_count"] = row_count
        if row_count == 3:
            cast(dict[str, str], payload["loaded_boundary_to_row_1_distance"])["value"] = "5"
        preview = preview_multirow_connection(_request(payload))
        assert preview.geometry_status is GeometryStatus.VALID
        assert preview.visualization is not None
        for bolt in preview.visualization.bolts:
            assert bolt.bolt_id.split("_L", 1)[0].replace("B_R", "ROW_") == bolt.row_id


def test_direct_one_row_variants_evaluate_source_methods_for_both_physical_layers() -> None:
    for count in (1, 2, 3):
        design = evaluate_multirow_connection(_request(_one_row_payload(count)))
        assert design.preview.geometry_status is GeometryStatus.VALID
        assert design.preview.design_check_ready
        local = getattr(design, "direct_single_row_result", None)
        assert local is not None
        assert (
            len([item for item in local.checks if item.limit_state == "SINGLE_ROW_SHEAR_OUT"])
            == 2 * count
        )
        assert {item.layer_id for item in local.checks} == {"layer-A", "layer-B"}
        assert all(
            item.availability.value == "CALCULATED" for item in local.checks if item.required
        )
        assert any(
            item.layer_id == "layer-B" and item.availability.value == "NOT_APPLICABLE"
            for item in local.checks
        )
        expected_net_method = "ASCE_EQ_8_7A_8_7B" if count == 1 else "ASCE_EQ_8_7A_8_7C"
        assert all(
            item.equation_method == expected_net_method
            for item in local.checks
            if item.limit_state == "SINGLE_ROW_NET_TENSION"
        )
        serialized = serialize_multirow_design(design).model_dump()
        integration = cast(dict[str, object], serialized["automatic_group_mode_integration"])
        assert (
            cast(dict[str, object], integration["direct_single_row_result"])["result_fingerprint"]
            == local.result_fingerprint
        )
        assert "BOLT_SHEAR:B_R1_L1" in local.incomplete_required_check_ids
        assert local.overall_disposition != "PASS"


def test_direct_one_row_residual_moment_blocks_sections_without_fabricated_rotation() -> None:
    payload = _one_row_payload(1)
    physical = cast(dict[str, object], payload["physical_connection"])
    assembly = cast(dict[str, object], physical["joint_assembly"])
    action = cast(list[dict[str, object]], assembly["member_end_actions"])[0]
    action["reference_point"] = {
        "kind": "MEMBER_CONNECTED_END",
        "owner_id": "member-a",
        "position": None,
    }
    design = evaluate_multirow_connection(_request(payload))
    assert design.preview.geometry_status is GeometryStatus.VALID
    assert not design.preview.design_check_ready
    assert "DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT" in design.preview.warnings
    assert getattr(design, "direct_single_row_result", None) is None
    assert design.automatic_group_mode_integration is None
    assert design.automatic_demand_result is not None
    assert design.automatic_demand_result.scenarios[0].residual_moment.canonical_magnitude != 0


def test_direct_one_row_supported_net_or_shear_out_failure_is_red_before_source_gates() -> None:
    design = evaluate_multirow_connection(_request(_one_row_payload(3, force="70")))
    local = getattr(design, "direct_single_row_result", None)
    assert local is not None
    assert any(
        item.limit_state in {"SINGLE_ROW_NET_TENSION", "SINGLE_ROW_SHEAR_OUT"}
        for item in local.checks
        if item.result_id in local.failed_check_ids
    )
    assert local.overall_disposition == "FAIL"
    assert "BOLT_SHEAR:B_R1_L1" in local.incomplete_required_check_ids


def test_direct_missing_w_layer_fails_closed() -> None:
    payload = _direct_payload()
    payload["layers"] = cast(list[object], payload["layers"])[:1]
    preview = preview_multirow_connection(_request(payload))
    assert preview.geometry_status is GeometryStatus.INVALID_GEOMETRY
    assert any("DIRECT_RESISTANCE_LAYERS_MUST_MATCH" in item for item in preview.warnings)


def test_direct_rejects_steel_label_and_beyond_three_by_three_scope() -> None:
    steel = _direct_payload()
    steel["material_pair"] = "FRP_STEEL"
    assert any(
        "DIRECT_FRP_STEEL_VARIANT_UNSUPPORTED" in item
        for item in preview_multirow_connection(_request(steel)).warnings
    )
    oversized = _direct_payload()
    oversized["row_count"] = 4
    assert any(
        "DIRECT_CHAPTER_8_MAXIMUM" in item
        for item in preview_multirow_connection(_request(oversized)).warnings
    )


def test_direct_independent_moment_blocks_design_without_faking_geometry_failure() -> None:
    payload = deepcopy(_direct_payload())
    physical = cast(dict[str, object], payload["physical_connection"])
    assembly = cast(dict[str, object], physical["joint_assembly"])
    action = cast(dict[str, object], cast(list[object], assembly["member_end_actions"])[0])
    cast(dict[str, str], action["moment"])["z"] = "1"
    request = _request(payload)
    preview = preview_multirow_connection(request)
    assert preview.geometry_status is GeometryStatus.VALID
    assert preview.design_check_ready is False
    assert "DIRECT_INDEPENDENT_MEMBER_END_MOMENT_NOT_SUPPORTED" in preview.warnings
    assert evaluate_multirow_connection(request).automatic_group_mode_integration is None


def test_direct_supported_bearing_failure_precedes_separate_source_blockers() -> None:
    payload = _direct_payload()
    physical = cast(dict[str, object], payload["physical_connection"])
    assembly = cast(dict[str, object], physical["joint_assembly"])
    action = cast(dict[str, object], cast(list[object], assembly["member_end_actions"])[0])
    cast(dict[str, str], action["force"])["x"] = "70"
    integration = evaluate_multirow_connection(_request(payload)).automatic_group_mode_integration
    assert integration is not None
    assert integration.overall_disposition.value == "FAIL"
    assert any(item.startswith("PIN_BEARING:layer-B:") for item in integration.failed_check_ids)
    assert "BOLT_SHEAR:B_R1_L1" in integration.incomplete_required_check_ids


def test_direct_pdf_reads_native_snapshot_without_mutating_engineering_state() -> None:
    payload = _direct_payload()
    native = serialize_multirow_design(evaluate_multirow_connection(_request(payload))).model_dump()
    original = deepcopy(native)
    signer = SnapshotSigner(b"direct-f1-test-report-only-key-32-bytes000")
    token = signer.issue(
        family="multi-row",
        kind="design",
        request=payload,
        result=native,
        account_id="direct-f1-test",
    )
    snapshot = signer.verify(token, account_id="direct-f1-test")
    signed_original = deepcopy(snapshot.result)
    report = render_multirow_pdf(
        snapshot,
        ReportOptions(paper="LETTER", display_units="US_CUSTOMARY"),
    )
    assert native == original
    assert snapshot.result == signed_original
    reader = PdfReader(io.BytesIO(report))
    first = reader.pages[0].extract_text() or ""
    assert len(reader.pages) < 20
    assert "Native connection status" in first
    assert "Not evaluated" in first
    assert "W TOP_FLANGE oblique block-shear path lacks an approved" in first
    assert "19 scheduled required checks unevaluated" in first
    audit_report = render_multirow_pdf(
        snapshot,
        ReportOptions(paper="LETTER", display_units="US_CUSTOMARY", mode="FULL_TECHNICAL_AUDIT"),
    )
    audit_reader = PdfReader(io.BytesIO(audit_report))
    assert len(audit_reader.pages) > len(reader.pages)
    audit = audit_reader.pages[len(reader.pages)].extract_text() or ""
    assert "TECHNICAL AUDIT APPENDIX" in audit
    assert "COMPLETE NATIVE RECORD" in audit
    assert snapshot.result == signed_original
    invalid_payload = _direct_payload(physically_contained=False)
    invalid_native = serialize_multirow_design(
        evaluate_multirow_connection(_request(invalid_payload))
    ).model_dump()
    invalid_token = signer.issue(
        family="multi-row",
        kind="design",
        request=invalid_payload,
        result=invalid_native,
        account_id="direct-f1-test",
    )
    invalid_snapshot = signer.verify(invalid_token, account_id="direct-f1-test")
    invalid_pdf = render_multirow_pdf(invalid_snapshot, ReportOptions())
    assert "SUBMITTED GEOMETRY — NOT VALIDATED" in "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(invalid_pdf)).pages
    )


def test_direct_mat1_envelope_pdf_uses_signed_native_geometry_and_keeps_assignments() -> None:
    payload = _direct_payload()
    native = serialize_multirow_design(evaluate_multirow_connection(_request(payload))).model_dump()
    request = {
        "contract": "MAT1-MULTI-ROW-RC0",
        "legacy_request": payload,
        "assignments": {"default_material": {"id": "ICE_ISOPHTHALIC_POLYESTER_OWNER_SEED_RC0"}},
    }
    response = {
        "contract": "MAT1-MULTI-ROW-RC0",
        "native_design": native,
        "overall_status": "SOURCE_REQUIRED",
        "material_sources": {
            "default": {
                "id": "ICE_ISOPHTHALIC_POLYESTER_OWNER_SEED_RC0",
                "revision": "RC0",
                "company": "ICE",
                "display_name": "ICE Isophthalic Polyester",
                "resin": "ISOPHTHALIC_POLYESTER",
            }
        },
        "material_ledgers": [],
    }
    signer = SnapshotSigner(b"direct-mat1-envelope-report-key-32bytes")
    token = signer.issue(
        family="multi-row",
        kind="design",
        request=request,
        result=response,
        account_id="direct-mat1-report-test",
    )
    snapshot = signer.verify(token, account_id="direct-mat1-report-test")
    original_request = deepcopy(snapshot.request)
    original_result = deepcopy(snapshot.result)
    report = render_report_pdf(snapshot, ReportOptions())
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(report)).pages)
    assert "Direct angle-to-W connection" in text
    assert "2 rows x 2 bolts per row" in text
    assert "Materials, conditions and design basis" in text
    assert "ICE Isophthalic Polyester" in text
    assert "ASTM F593-17 Group 2 316/316L" in text
    assert "Controlled source required" in text
    assert snapshot.request == original_request
    assert snapshot.result == original_result


def test_direct_one_row_pdf_uses_same_native_result_in_engineer_and_audit_modes() -> None:
    payload = _one_row_payload(2)
    native = serialize_multirow_design(evaluate_multirow_connection(_request(payload))).model_dump()
    signer = SnapshotSigner(b"direct-one-row-report-only-test-key-32")
    token = signer.issue(
        family="multi-row",
        kind="design",
        request=payload,
        result=native,
        account_id="direct-one-row-test",
    )
    snapshot = signer.verify(token, account_id="direct-one-row-test")
    original = deepcopy(snapshot.result)
    engineer = PdfReader(
        io.BytesIO(render_multirow_pdf(snapshot, ReportOptions(display_units="US_CUSTOMARY")))
    )
    audit = PdfReader(
        io.BytesIO(
            render_multirow_pdf(
                snapshot,
                ReportOptions(display_units="US_CUSTOMARY", mode="FULL_TECHNICAL_AUDIT"),
            )
        )
    )
    text = "\n".join(page.extract_text() or "" for page in engineer.pages)
    assert len(engineer.pages) < 10
    assert len(audit.pages) > 100
    assert "Direct angle-to-W connection" in text
    assert "1 row x 2 bolts per row" in text
    assert "SINGLE_LAP" in text
    assert "Canonical single-row bolt layout" in text
    assert "Pitch / gauge" not in text
    assert "Pitch\nNot applicable" in text
    assert "c lap: 0.6" in text
    assert "SINGLE_ROW_CLEAVAGE:layer-A" in text
    assert "nominal resistance" in text.lower()
    assert "0.375 in" in text
    assert "Full Technical Audit" in text
    assert "TECHNICAL AUDIT APPENDIX" not in text
    audit_text = "\n".join(page.extract_text() or "" for page in audit.pages)
    assert "c lap: 0.6" in audit_text
    assert "request.lap_configuration" in audit_text
    assert "SINGLE_LAP" in audit_text
    assert snapshot.result == original


def test_inherited_group_mode_source_matches_protected_blob() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "src/frp_master_connection/calculation/eccentric_group_modes.py"
    )
    data = source.read_bytes()
    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    assert blob == "c29ce8ffba6fdab1684e0e3e08623bd373fb43c4"
