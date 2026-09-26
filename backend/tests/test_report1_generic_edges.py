"""Shared report adapters fail closed on incomplete executed native traces."""

from __future__ import annotations

import asyncio
import io
from copy import deepcopy
from typing import Any, cast

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.generic import (
    _bearing_substitution,
    _check_matrix,
    _check_summary,
    _eccentric_demand_example,
    _face_figure,
    _method_example_data,
    _native_box_unit,
    _native_equation_examples,
    render_generic_pdf,
)
from frp_master_connection.reporting.geometry import BoltPoint, FaceFigure
from frp_master_connection.reporting.pdf import ReportingCoverageError, ReportOptions
from frp_master_connection.reporting.snapshot import ReportSnapshot
from tests.api.test_connector_materials import native_payload


def _bearing_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = {"bolt_diameter": {"value": "0.5", "unit": "in"}}
    visual = {
        "visualization": {
            "layers": [
                {
                    "layer_id": "L1",
                    "thickness": {"canonical_value": "9.525", "canonical_unit": "mm"},
                }
            ],
            "physical_bolts": [{"bolt_id": "B1", "display": {"bolt_diameter": "0.5"}}],
        }
    }
    check = {
        "layer_id": "L1",
        "bolt_id": "B1",
        "equation_trace": {
            "bearing_property": {
                "adjusted_property": {"canonical_value": "100", "canonical_unit": "MPa"}
            },
            "thread_factor": "1",
        },
        "equation_nominal_resistance": {"value": "10", "unit": "kN"},
    }
    return request, {"nested": [visual]}, check


def test_native_check_matrix_keeps_distinct_owners_and_exact_outcomes() -> None:
    bearing = {
        "result_id": "B-1",
        "equation_method": "PIN_BEARING",
        "layer_id": "L1",
        "bolt_id": "Bolt-1",
        "availability": "CALCULATED",
        "demand": {"value": "12", "unit": "kN"},
        "design_resistance": {"value": "10", "unit": "kN"},
        "utilization": "1.2",
        "numerical_comparison": "FAIL",
    }
    source_only = {
        "check_id": "S-2",
        "plan": {"limit_state": "BOLT_SHEAR"},
        "component_id": "L2",
        "path_id": "P-2",
        "status": "SOURCE_REQUIRED",
    }
    rows = _check_matrix({"first": bearing, "duplicate": deepcopy(bearing), "other": [source_only]})
    assert len(rows) == 2
    assert rows[0][0] == "B-1"
    assert "PIN_BEARING" in rows[0][1]
    assert "owner L1" in rows[0][1]
    assert "demand 12 kN" in rows[0][1]
    assert "R_d 10 kN" in rows[0][1]
    assert "U 1.2" in rows[0][1]
    assert "outcome FAIL" in rows[0][1]
    assert "result.first" in rows[0][1]
    assert rows[1][0] == "S-2"
    assert "BOLT_SHEAR" in rows[1][1]
    assert "BOLT_SHEAR; SOURCE_REQUIRED" in rows[1][1]
    assert _check_matrix({"metadata": "none"}) == []


@pytest.mark.parametrize(
    ("demand", "utilization", "expected"),
    [
        ("12 kN", "bad", "demand 12 kN"),
        ({"value": "NaN", "unit": "N"}, "NaN", "demand NaN N"),
        ({"unit": "N"}, "1", "demand"),
        ({"value": "bad", "unit": "N"}, "0.9", "demand bad N"),
    ],
)
def test_check_matrix_keeps_unusual_native_values_without_inventing_numbers(
    demand: object, utilization: str, expected: str
) -> None:
    rows = _check_matrix(
        {
            "checks": [
                {
                    "result_id": "C-1",
                    "status": "CALCULATED",
                    "case_id": "LC-1",
                    "demand": demand,
                    "utilization": utilization,
                }
            ]
        }
    )
    assert len(rows) == 1
    assert "case LC-1" in rows[0][1]
    assert expected in rows[0][1]
    if utilization == "bad":
        assert "U bad" in rows[0][1]
    if utilization == "NaN":
        assert "U NaN" in rows[0][1]


def test_native_bearing_substitution_joins_identified_layer_bolt_and_property() -> None:
    request, result, check = _bearing_records()
    text = _bearing_substitution(request, result, check)
    assert text is not None
    assert "t(9.525 mm)" in text
    assert "d(12.70 mm)" in text
    assert "F_br,adjusted(100 MPa)" in text
    assert "native R_n 10 kN" in text


@pytest.mark.parametrize(
    "family",
    [
        "tee-connector",
        "clip-angle",
        "paired-clip-angle",
        "multi-member-tee",
        "beam-concrete-paired-angle",
        "wi-beam-concrete-wall-moment",
        "wi-beam-frp-support-moment",
    ],
)
def test_real_executed_bearing_has_a_joined_native_substitution(family: str) -> None:
    request = native_payload(family)

    async def calculate() -> dict[str, Any]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/calculations/{family}/design-check", json=request
            )
            assert response.status_code == 200
            return cast(dict[str, Any], response.json())

    result = asyncio.run(calculate())
    worked = _native_equation_examples(result)["PIN_BEARING"][1]
    substitution = _bearing_substitution(request, result, worked)
    assert substitution is not None
    assert "R_n = t(" in substitution
    assert "F_br,adjusted(" in substitution
    assert worked["equation_nominal_resistance"]["value"] in substitution


def test_nested_native_bearing_fallback_requires_unique_layer_and_diameter() -> None:
    request, _, check = _bearing_records()
    result: dict[str, Any] = {
        "layer": {
            "layer_id": "L1",
            "thickness": {"value": "0.375", "unit": "in"},
        }
    }
    adjusted = check["equation_trace"]["bearing_property"]["adjusted_property"]
    adjusted.pop("canonical_value")
    adjusted.pop("canonical_unit")
    adjusted["value"] = "100"
    adjusted["unit"] = "MPa"
    assert _bearing_substitution(request, result, check) is not None
    result["conflicting_layer"] = {
        "layer_id": "L1",
        "thickness": {"value": "0.5", "unit": "in"},
    }
    assert _bearing_substitution(request, result, check) is None
    del result["conflicting_layer"]
    result["conflicting_bolt"] = {"bolt_diameter": {"value": "0.75", "unit": "in"}}
    assert _bearing_substitution(request, result, check) is None


@pytest.mark.parametrize(
    "fault",
    [
        "missing_trace",
        "missing_bearing",
        "missing_adjusted",
        "bad_layer_identity",
        "wrong_layer",
        "ambiguous_thickness",
        "wrong_diameter",
        "wrong_thickness_unit",
        "invalid_thickness_shape",
        "missing_canonical_value",
        "no_bolt_display",
        "bad_diameter_unit",
        "bad_property_unit",
        "missing_property_unit",
        "missing_property_value",
        "missing_nominal",
    ],
)
def test_bearing_substitution_never_guesses_missing_native_inputs(fault: str) -> None:
    request, result, check = _bearing_records()
    visual = result["nested"][0]["visualization"]
    trace = check["equation_trace"]
    if fault == "missing_trace":
        del check["equation_trace"]
    elif fault == "missing_bearing":
        del trace["bearing_property"]
    elif fault == "missing_adjusted":
        del trace["bearing_property"]["adjusted_property"]
    elif fault == "bad_layer_identity":
        check["layer_id"] = None
    elif fault == "wrong_layer":
        check["layer_id"] = "L2"
    elif fault == "ambiguous_thickness":
        alternate = deepcopy(result["nested"][0])
        alternate["visualization"]["layers"][0]["thickness"]["canonical_value"] = "12"
        result["nested"].append(alternate)
    elif fault == "wrong_diameter":
        visual["physical_bolts"][0]["display"]["bolt_diameter"] = "0.75"
    elif fault == "wrong_thickness_unit":
        visual["layers"][0]["thickness"]["canonical_unit"] = "in"
    elif fault == "invalid_thickness_shape":
        visual["layers"][0]["thickness"] = "invalid"
    elif fault == "missing_canonical_value":
        del visual["layers"][0]["thickness"]["canonical_value"]
    elif fault == "no_bolt_display":
        visual["physical_bolts"][0]["display"] = {}
    elif fault == "bad_diameter_unit":
        request["bolt_diameter"]["unit"] = "bad"
    elif fault == "bad_property_unit":
        trace["bearing_property"]["adjusted_property"]["canonical_unit"] = "ksi"
    elif fault == "missing_property_unit":
        trace["bearing_property"]["adjusted_property"] = {"value": "100", "unit": "ksi"}
    elif fault == "missing_property_value":
        trace["bearing_property"]["adjusted_property"] = {"canonical_unit": "MPa"}
    elif fault == "missing_nominal":
        del check["equation_nominal_resistance"]
    assert _bearing_substitution(request, result, check) is None


def test_visual_layer_with_only_native_length_still_joins_safely() -> None:
    request, result, check = _bearing_records()
    result["nested"][0]["visualization"]["layers"][0]["thickness"] = {
        "value": "0.375",
        "unit": "in",
    }
    assert _bearing_substitution(request, result, check) is not None


@pytest.mark.parametrize("invalid", [None, "bad", {"center_l_v_t": {}, "size_l_v_t": []}])
def test_figure_unit_is_not_inferred_from_malformed_coordinates(invalid: object) -> None:
    if invalid is None:
        assert _native_box_unit(None) is None
    else:
        assert _native_box_unit({"part": invalid}) is None


def test_figure_unit_requires_declared_axis_unit() -> None:
    assert (
        _native_box_unit(
            {
                "center_l_v_t": {"l": {"value": "2"}},
                "size_l_v_t": {"l": {"value": "4"}},
            }
        )
        is None
    )


def test_many_face_bolts_are_drawn_without_overflowing_the_legend() -> None:
    face = FaceFigure("Plate", ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
    bolts = [BoltPoint(f"B{index}", (float(index) / 20, 0.5, 0.0)) for index in range(17)]
    drawing = _face_figure([face], bolts, "isometric", "in")
    assert drawing.width == 480


@pytest.mark.parametrize(
    ("method", "record", "message"),
    [
        ("SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", {}, "action/cut"),
        ("RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1", {}, "components"),
        ("RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1", {}, "bolt solution"),
        ("RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1", {}, "fiber trace"),
        ("DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1", {}, "row or shaft"),
    ],
)
def test_executed_native_method_without_required_worked_trace_is_rejected(
    method: str, record: dict[str, Any], message: str
) -> None:
    with pytest.raises(ReportingCoverageError, match=message):
        _method_example_data(method, record)


def test_ssmc_absent_finite_cut_stays_explicitly_unavailable() -> None:
    record = {"action_reaction": [{}], "cuts": {"cuts": [], "status": "SOURCE_REQUIRED"}}
    selected = _method_example_data("SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", record)
    assert selected["first_actual_polygon_cut"] is None
    assert selected["cut_coverage_status"] == "SOURCE_REQUIRED"


@pytest.mark.parametrize("invalid", ["invalid", "NaN", "Infinity"])
def test_non_numeric_native_ratio_is_not_presented_as_a_governing_result(invalid: str) -> None:
    rows = dict(_check_summary({"checks": [{"result_id": "C1", "utilization": invalid}]}))
    assert rows["Highest native numerical ratio"] == "None; no native numerical ratio"


@pytest.mark.parametrize(
    ("ratio", "side"),
    [("1", "at 1.0"), ("1.0000000000001", "above 1.0"), ("0.9999999999999", "below 1.0")],
)
def test_native_summary_identifies_unrounded_side_of_limit(ratio: str, side: str) -> None:
    rows = dict(_check_summary({"checks": [{"result_id": "C1", "utilization": ratio}]}))
    assert side in rows["Highest native numerical ratio"]
    assert "exact native U in results" in rows["Highest native numerical ratio"]


def test_incomplete_eccentric_scenario_is_not_presented_as_executed() -> None:
    result = {
        "groups": [
            {
                "polar_coordinate_sum": "1",
                "scenarios": [
                    None,
                    {
                        "method": "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY",
                        "availability": "CALCULATED",
                        "per_bolt": [],
                    },
                ],
            }
        ]
    }
    assert _eccentric_demand_example(result) is None


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ({"client_design": []}, "dictionary result"),
        ({"client_design": {"result": []}}, "result record"),
        (
            {
                "result": {
                    "checks": [{"equation_method": "PIN_BEARING", "availability": "CALCULATED"}]
                }
            },
            "numerical trace",
        ),
        (
            {"result": {"preview": {"demand": {"status": "CALCULATED", "members": []}}}},
            "member trace",
        ),
    ],
)
def test_generic_report_rejects_missing_authoritative_native_records(
    result: dict[str, Any], message: str
) -> None:
    family = "double-channel-truss-node" if message == "member trace" else "clip-angle"
    snapshot = ReportSnapshot(family, "design", {}, result, 1_000, "0" * 64)
    with pytest.raises(ReportingCoverageError, match=message):
        render_generic_pdf(snapshot, ReportOptions())


def test_long_native_text_remains_searchable_and_mat1_wrapper_is_printed() -> None:
    native = {"result": {"note": "A" * 1000}}
    snapshot = ReportSnapshot(
        "clip-angle",
        "design",
        {},
        {"client_design": native, "material_ledgers": [{"record_id": "M1"}]},
        1_000,
        "0" * 64,
    )
    pdf = render_generic_pdf(snapshot, ReportOptions())
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "M1" in text
    assert "part 1/3" in text


def test_nonexecuted_dctn_demand_has_no_worked_transport() -> None:
    snapshot = ReportSnapshot(
        "double-channel-truss-node",
        "input_only",
        {},
        {"result": {"preview": {"demand": {"status": "SOURCE_REQUIRED"}}}},
        1_000,
        "0" * 64,
    )
    pdf = render_generic_pdf(snapshot, ReportOptions())
    content = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "DCTN-3B exact member action transport" not in content


def test_unknown_executed_native_method_fails_closed() -> None:
    snapshot = ReportSnapshot(
        "clip-angle",
        "design",
        {},
        {"result": {"method": "UNKNOWN_EXECUTED", "status": "CALCULATED"}},
        1_000,
        "0" * 64,
    )
    with pytest.raises(ReportingCoverageError, match="no REPORT1 report adapter"):
        render_generic_pdf(snapshot, ReportOptions())


def test_executed_bearing_with_no_joinable_geometry_fails_report_export() -> None:
    snapshot = ReportSnapshot(
        "clip-angle",
        "design",
        {},
        {
            "result": {
                "checks": [
                    {
                        "equation_method": "PIN_BEARING",
                        "availability": "CALCULATED",
                        "equation_trace": {"bearing_property": {"adjusted_property": {}}},
                    }
                ]
            }
        },
        1_000,
        "0" * 64,
    )
    with pytest.raises(ReportingCoverageError, match="identified native substitution"):
        render_generic_pdf(snapshot, ReportOptions())
