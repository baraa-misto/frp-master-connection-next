"""P4 live workflow tests: preview purity precedes resistance activation."""

import io
from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest
from pypdf import PdfReader
from tests.api.test_hybrid_same_connection import assessed, basis_rows
from tests.api.test_hybrid_workflow import BASE, LiveTransport
from tests.hybrid_physical_fixtures import physical_case
from tests.hybrid_same_connection_fixtures import same_connection
from tests.hybrid_workflow_fixtures import live_source

from frp_master_connection.api import hybrid_workflow
from frp_master_connection.api.hybrid_app import create_hybrid_app
from frp_master_connection.calculation import rhm_direct_r3
from frp_master_connection.security import TrustedIdentity


def test_source_preview_executes_zero_resistance(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("A preview executed resistance or assessment.")

    monkeypatch.setattr(rhm_direct_r3, "execute_direct_source", forbidden)
    monkeypatch.setattr(rhm_direct_r3, "bolt_shear_capacity", forbidden)
    monkeypatch.setattr(rhm_direct_r3, "_check", forbidden)
    monkeypatch.setattr(hybrid_workflow, "assess_d2", forbidden)
    with LiveTransport() as client:
        response = client.post(BASE + "/preview", json=live_source())
    assert response.status_code == 200, response.text
    preview = response.json()
    assert "record" not in preview
    assert "report_handle" not in preview
    assert len(preview["scene"]["materialAxes"]) == 5
    assert preview["workflow_available"]


def physical_result(body: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    record = assessed(body)
    return record, record["physical_design"]["cases"][0]


@pytest.mark.parametrize(("force", "outcome"), [(".1", "PASS"), ("10", "FAIL")])
def test_new_physical_capacity_has_independent_hand_arithmetic(force: str, outcome: str) -> None:
    body = physical_case()
    body["lrfd_cases"][0]["components"][0]["value"] = force
    record, result = physical_result(body)
    # Independent printed Eq.8-12: nominal hole .563, true e1=5-1, s=2.
    nominal = Decimal("1.4") * (4 - Decimal(".563") / 2 + 2) * Decimal(".375") * Decimal("7.2")
    resistance = nominal * Decimal(".6") * Decimal(".45")
    assert nominal == Decimal("21.61593")
    assert resistance == Decimal("5.8363011")
    assert Decimal(result["design_resistance_kip"]) == resistance
    assert float(result["utilization"]) == pytest.approx(float(Decimal(force) / resistance))
    assert result["outcome"] == outcome
    assert result["disposition"] == "EXECUTED"
    assert len(basis_rows(record, "LRFD")) == 7
    assert (
        record["physical_design"]["status_axes"]["required_coverage"] == "REQUIRED_COVERAGE_PARTIAL"
    )
    assert (
        record["physical_design"]["status_axes"]["qualification"] == "NOT_ESTABLISHED_SECTION_2_3_2"
    )
    witness = result["physical_release"]
    assert Decimal(witness["actual_free_end_y_in"]) == 5
    assert Decimal(witness["root_clearance_in"]) == Decimal(".2185")
    assert Decimal(result["net_area_screen"]["raw_ratio"]) == Decimal(".8435")
    assert result["derived_complementary_receiving_action"]["components"][0]["value"].startswith(
        "-"
    )
    assert "prying remain unverified" in result["derived_action_scope"]


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("alignment",), "BRACE", "brace alignment"),
        (("physical_context", "hole_source"), None, "original published"),
        (("physical_context", "clear_flat_outstand"), None, "measured clear"),
        (("physical_context", "clear_flat_outstand", "value"), "1.2", "wholly inside"),
        (("physical_context", "clear_flat_outstand", "value"), "2.1", "half the receiving"),
        (("physical_context", "interface_gap"), None, "actual interface gap"),
        (("physical_context", "interface_gap", "value"), ".01", "gapped/standoff"),
        (("physical_context", "positive_end"), {"condition": "UNKNOWN"}, "actual free end"),
        (("physical_context", "negative_end"), {"condition": "UNKNOWN"}, "opposite receiving"),
        (("physical_context", "positive_end", "distance", "value"), "1.9", "2d minimum"),
        (("geometry", "column_thickness", "value"), ".6", "minimum connected thickness"),
        (("geometry", "hole", "value"), ".564", "standard-hole source"),
        (("geometry", "vertical_bolt_pitch", "value"), "13", "maximum"),
        (("physical_context", "receiving_actions"), [], "all six additional"),
        (("include_native_lrfd",), False, "not requested"),
        (("same_connection_lrfd",), None, "shear strength"),
    ],
)
def test_physical_applicability_never_borrows_a_result(
    path: tuple[str, ...], value: object, reason: str
) -> None:
    body = physical_case()
    current = body
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    record, result = physical_result(body)
    assert result["disposition"] != "EXECUTED"
    assert any(reason in item for item in result["reasons"]), result["reasons"]
    assert "design_resistance_kip" not in result
    assert not any(
        row["mechanism"] == "RECEIVING_INTERROW_SHEAR_OUT" for row in basis_rows(record, "LRFD")
    )
    assert len(basis_rows(record, "ASD")) == (0 if path == ("alignment",) else 7)
    assert record["physical_design"]["status_axes"]["whole_connection"] != "PASS"


@pytest.mark.parametrize("index", range(6))
def test_additional_receiving_actions_are_never_assumed_zero(index: int) -> None:
    body = physical_case()
    body["physical_context"]["receiving_actions"][0]["components"][index] = None
    _, missing = physical_result(body)
    assert missing["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert any("all six" in reason for reason in missing["reasons"])
    body["physical_context"]["receiving_actions"][0]["components"][index] = {
        "value": "1e-88",
        "unit": "kip" if index < 3 else "kip-in",
    }
    _, nonzero = physical_result(body)
    assert nonzero["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert any("Nonzero receiving bypass" in reason for reason in nonzero["reasons"])
    assert nonzero["additional_receiving_actions"]["components"][index]["magnitude"] == "1E-88"


@pytest.mark.parametrize("index", [1, 2, 3, 4, 5])
def test_actual_transverse_and_out_of_plane_actions_fail_closed(index: int) -> None:
    body = physical_case()
    body["lrfd_cases"][0]["components"][index]["value"] = "1e-88"
    record, result = physical_result(body)
    assert result["disposition"] != "EXECUTED"
    assert "design_resistance_kip" not in result
    if index == 1:
        assert any("entered transverse force" in reason for reason in result["reasons"])
        assert len(record["same_connection_lrfd"]["cases"]) == 1
    elif index == 5:
        assert any("transported free moment" in reason for reason in result["reasons"])
        assert len(record["same_connection_lrfd"]["cases"]) == 1
    else:
        assert len(basis_rows(record, "LRFD")) == 0


def test_reverse_force_requires_the_opposite_real_unloaded_end() -> None:
    body = physical_case()
    body["lrfd_cases"][0]["components"][0]["value"] = "-.1"
    _, blocked = physical_result(body)
    assert blocked["disposition"] != "EXECUTED"
    ends = body["physical_context"]
    ends["positive_end"], ends["negative_end"] = ends["negative_end"], ends["positive_end"]
    _, result = physical_result(body)
    assert result["disposition"] == "EXECUTED"
    assert result["nearest_unloaded_row"] == "B2"
    assert Decimal(result["physical_release"]["actual_free_end_y_in"]) == -5
    assert Decimal(result["design_resistance_kip"]) == Decimal("5.8363011")


def test_zero_force_has_no_invented_longitudinal_failure_direction() -> None:
    body = physical_case()
    body["lrfd_cases"][0]["components"][0]["value"] = "0"
    record, result = physical_result(body)
    assert result["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert result["actual_unloaded_e1_in"] is None
    assert "design_resistance_kip" not in result
    assert any("nonzero force exactly" in reason for reason in result["reasons"])
    assert len(basis_rows(record, "ASD")) == 7


def test_true_end_not_view_crop_controls_resistance_and_model() -> None:
    body = physical_case()
    body["physical_context"]["positive_end"]["distance"]["value"] = "9"
    with LiveTransport() as c:
        response = c.post(BASE + "/assess", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    result = data["record"]["physical_design"]["cases"][0]
    assert Decimal(result["actual_unloaded_e1_in"]) == 8
    assert Decimal(result["physical_release"]["actual_free_end_y_in"]) == 9
    assert "beyond view crop" in data["scene"]["boxes"][0]["label"]
    assert data["scene"]["boxes"][0]["size"]["z"] == 12
    assert Decimal(result["design_resistance_kip"]) == Decimal("9.9187011")


def test_p3_numbers_and_known_detailing_remain_independent_and_red() -> None:
    body = same_connection()
    original = assessed(body)
    body["physical_context"] = {
        "contract": "HYB2-D3-P4-PHYSICAL/1",
        "hole_source": "US_CUSTOMARY_PRINTED",
    }
    r = assessed(body)
    assert r["assessment"]["comparisons"] == original["assessment"]["comparisons"]
    assert r["detailing_failures"] == original["detailing_failures"]
    assert r["assessment"]["evaluated_outcome"] == "PASS"
    axes = r["physical_design"]["status_axes"]
    assert axes["scoped_numerical"] == "SCOPED_NUMERICAL_PASS"
    assert axes["detailing"] == "DETAILING_FAIL"
    assert axes["viewer_tone"] == "red"
    assert axes["whole_connection"] == "FAIL_DETAILING"
    assert len(r["physical_design"]["mechanism_matrix"]) == 13


def test_display_conversion_preserves_current_signed_report_but_real_edit_does_not() -> None:
    body = physical_case()
    with LiveTransport() as c:
        initial = c.post(BASE + "/assess", json=body).json()
        converted = c.post(BASE + "/units", json={"inputs": body, "system": "mm"}).json()
        assert converted["physical_context"]["positive_end"]["distance"] == {
            "value": "127.0",
            "unit": "mm",
        }
        assert converted["physical_context"]["hole_source"] == "US_CUSTOMARY_PRINTED"
        preview = c.post(BASE + "/preview", json=converted)
        assert preview.status_code == 200, preview.text
        assert preview.json()["fingerprint"] == initial["fingerprint"]
        assert c.get(BASE + "/records/" + initial["report_handle"]).status_code == 200
        si = c.post(BASE + "/assess", json=converted)
        assert si.status_code == 200, si.text
        assert Decimal(
            si.json()["record"]["physical_design"]["cases"][0]["design_resistance_kip"]
        ) == Decimal("5.8363011")
        changed = deepcopy(converted)
        changed["revision"] += 1
        changed["physical_context"]["positive_end"]["distance"]["value"] = "128"
        assert c.post(BASE + "/preview", json=changed).status_code == 200
        assert c.get(BASE + "/records/" + initial["report_handle"]).status_code == 409


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("physical_context", "clear_flat_outstand", "value"), "0"),
        (("physical_context", "clear_flat_outstand", "value"), "-1"),
        (("physical_context", "interface_gap", "value"), "-.01"),
        (("physical_context", "positive_end", "distance", "unit"), "kip"),
        (("physical_context", "positive_end", "distance", "value"), "-1"),
        (("physical_context", "positive_end"), {"condition": "FREE"}),
        (
            ("physical_context", "negative_end"),
            {"condition": "CONTINUOUS", "distance": {"value": "5", "unit": "in"}},
        ),
        (
            ("physical_context", "receiving_actions"),
            [{"case_id": "absent", "components": [None] * 6}],
        ),
        (
            ("asd_cases",),
            [
                {
                    "case_id": "wrong-ASD-frame",
                    "frame": "DIRECT_RECEIVING_LW_CW_TT",
                    "reference": [{"value": "0", "unit": "in"}] * 3,
                    "components": [
                        {"value": "0", "unit": "kip" if i < 3 else "kip-in"} for i in range(6)
                    ],
                }
            ],
        ),
    ],
)
def test_invalid_physical_inputs_are_rejected_before_preview(
    path: tuple[str, ...], value: object
) -> None:
    body = physical_case()
    parent = body
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with LiveTransport() as client:
        response = client.post(BASE + "/preview", json=body)
    assert response.status_code == 422, response.text
    assert "report_handle" not in response.json()


def test_receiving_action_duplicates_and_wrong_dimensions_are_rejected() -> None:
    body = physical_case()
    body["physical_context"]["receiving_actions"] *= 2
    with LiveTransport() as c:
        assert c.post(BASE + "/preview", json=body).status_code == 422
        body["physical_context"]["receiving_actions"] = body["physical_context"][
            "receiving_actions"
        ][:1]
        body["physical_context"]["receiving_actions"][0]["components"][0]["unit"] = "in"
        assert c.post(BASE + "/preview", json=body).status_code == 422


def test_no_zero_length_member_or_material_frame_without_physical_context() -> None:
    body = physical_case()
    body["physical_context"]["positive_end"]["distance"]["value"] = "0"
    body["physical_context"]["negative_end"] = deepcopy(body["physical_context"]["positive_end"])
    with LiveTransport() as c:
        assert c.post(BASE + "/preview", json=body).status_code == 422
        del body["physical_context"]
        assert c.post(BASE + "/preview", json=body).status_code == 422


@pytest.mark.parametrize(
    ("distance", "state"),
    [
        ("1.999999999999", "GEOMETRY_FAIL"),
        ("2", "EXECUTED"),
        ("2.000000000001", "EXECUTED"),
    ],
)
def test_two_row_unloaded_end_limit_is_exact(distance: str, state: str) -> None:
    body = physical_case()
    body["physical_context"]["positive_end"]["distance"]["value"] = distance
    _, result = physical_result(body)
    assert result["disposition"] == state


def test_known_hole_end_failure_is_red_even_without_an_lrfd_case() -> None:
    body = physical_case()
    body["lrfd_cases"] = []
    body["physical_context"]["receiving_actions"] = []
    body["physical_context"]["positive_end"]["distance"]["value"] = "1.2"
    result = assessed(body)
    assert result["physical_design"]["cases"] == []
    assert result["physical_design"]["status_axes"]["detailing"] == "DETAILING_FAIL"
    assert result["physical_design"]["status_axes"]["viewer_tone"] == "red"
    assert "actual hole" in result["physical_design"]["geometry_failures"][0]["reasons"][0]
    assert len(basis_rows(result, "ASD")) == 7


def test_unsupported_case_and_material_notes_do_not_hide_other_valid_cases() -> None:
    body = physical_case()
    unsupported = deepcopy(body["lrfd_cases"][0])
    unsupported["case_id"] = "eccentric-independent"
    unsupported["components"][5]["value"] = "1"
    body["lrfd_cases"].append(unsupported)
    record = assessed(body)
    cases = record["physical_design"]["cases"]
    assert cases[0]["disposition"] == "EXECUTED"
    assert cases[1]["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert len(basis_rows(record, "LRFD")) == 13
    assert len(basis_rows(record, "ASD")) == 7
    assert (
        record["physical_design"]["mechanism_matrix"][6]["disposition"] == "REQUIRED_NOT_EVALUATED"
    )


@pytest.mark.parametrize(("factor", "ratio"), [("1", "1"), (".8", ".8")])
def test_new_resistance_uses_existing_mc1_strength_adjustments_once(
    factor: str, ratio: str
) -> None:
    body = physical_case()
    if factor != "1":
        conditions = body["same_connection_lrfd"]["assignments"]["default_conditions"]
        conditions.update(chemical="SPECIFIED", chemical_strength_factor=factor)
    _, result = physical_result(body)
    assert Decimal(result["design_resistance_kip"]) == Decimal("5.8363011") * Decimal(ratio)
    assert Decimal(result["MAT1_ledger"]["cch"]) == Decimal(factor)


@pytest.mark.parametrize("technical", [False, True])
@pytest.mark.parametrize("specimen", ["positive", "reverse", "unknown", "geometry-fail"])
def test_actual_physical_reports_read_only_the_current_backend_record(
    technical: bool, specimen: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = physical_case()
    if specimen == "reverse":
        body["lrfd_cases"][0]["components"][0]["value"] = "-.1"
        ends = body["physical_context"]
        ends["positive_end"], ends["negative_end"] = ends["negative_end"], ends["positive_end"]
    elif specimen == "unknown":
        body["physical_context"]["interface_gap"] = None
        body["physical_context"]["positive_end"] = {"condition": "UNKNOWN"}
        body["physical_context"]["negative_end"] = {"condition": "UNKNOWN"}
        body["physical_context"]["clear_flat_outstand"] = None
        body["physical_context"]["hole_source"] = None
        body["physical_context"]["receiving_actions"][0]["components"][1] = None
    elif specimen == "geometry-fail":
        body["physical_context"]["positive_end"]["distance"]["value"] = "1.2"
    with LiveTransport() as client:
        assessed_response = client.post(BASE + "/assess", json=body)
        assert assessed_response.status_code == 200, assessed_response.text
        data = assessed_response.json()

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("Export attempted to calculate engineering.")

        monkeypatch.setattr(hybrid_workflow, "calculate_same_connection", forbidden)
        monkeypatch.setattr(hybrid_workflow, "evaluate_physical", forbidden)
        monkeypatch.setattr(hybrid_workflow, "assess_d2", forbidden)
        monkeypatch.setattr(rhm_direct_r3, "execute_r3", forbidden)
        handle = data["report_handle"]
        response = client.get(
            BASE + "/reports/" + handle + ("?technical=true" if technical else "")
        )
        assert response.status_code == 200, response.text
        text = " ".join(
            page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages
        )
        assert "Required physical mechanism dispositions" in text
        assert "Section 2.3.2" in text
        if specimen in ("positive", "reverse"):
            assert "Substitution: 1.4" in text
            assert "5.836" in text
            assert "True free end" in text
            assert "No global block or first-row coverage" in text
        elif specimen == "unknown":
            assert "State the actual interface gap" in text
        else:
            assert "Physical geometry FAIL" in text
        assert client.get(BASE + "/records/" + handle).json() == data["record"]


def test_physical_records_and_reports_keep_the_existing_account_boundary() -> None:
    class Identity:
        production_capable = True
        account = "P4-owner-A"

        async def resolve(self) -> TrustedIdentity:
            return TrustedIdentity(self.account, None, frozenset(), "trusted-physical-test")

    identity = Identity()
    with LiveTransport() as client:
        client.app = create_hybrid_app(identity_resolver=identity)
        data = client.post(BASE + "/assess", json=physical_case()).json()
        handle = data["report_handle"]
        assert client.get(BASE + "/records/" + handle).json() == data["record"]
        identity.account = "P4-other-B"
        assert client.get(BASE + "/records/" + handle).status_code == 409
        assert client.get(BASE + "/reports/" + handle).status_code == 409


@pytest.mark.parametrize(
    ("width", "state"),
    [
        ("2.503999999999", "GEOMETRY_FAIL"),
        ("2.504", "EXECUTED"),
        ("2.504000000001", "EXECUTED"),
    ],
)
def test_raw_net_area_boundary_is_not_clamped(width: str, state: str) -> None:
    body = physical_case()
    body["geometry"]["column_flange"]["value"] = width
    body["geometry"]["xc"]["value"] = ".76"
    body["physical_context"]["clear_flat_outstand"]["value"] = "1.05"
    _, result = physical_result(body)
    assert result["disposition"] == state
    ratio = Decimal(result["net_area_screen"]["raw_ratio"])
    assert (ratio >= Decimal(".75")) is (state == "EXECUTED")
    assert result["net_area_screen"]["net_deduction_diameter_in"] == "0.626"


def test_si_printed_hole_is_a_distinct_physical_input_not_a_display_conversion() -> None:
    from decimal import localcontext

    body = physical_case()
    body["physical_context"]["hole_source"] = "SI_PRINTED"
    body["geometry"]["hole"] = {"value": "14.3", "unit": "mm"}
    _, result = physical_result(body)
    assert result["disposition"] == "EXECUTED"
    with localcontext() as context:
        context.prec = 60
        expected = Decimal("1.4") * (4 - Decimal("14.3") / Decimal("25.4") / 2 + 2)
        expected *= Decimal(".375") * Decimal("7.2") * Decimal(".6") * Decimal(".45")
    assert float(result["design_resistance_kip"]) == pytest.approx(float(expected))
    assert Decimal(result["design_resistance_kip"]) != Decimal("5.8363011")
    assert result["equation_trace"]["net_hole_diameter"] == {"magnitude": "14.3", "unit": "mm"}


def test_receiving_signed_reference_transport_preserves_the_same_physical_force() -> None:
    body = physical_case()
    _, original = physical_result(body)
    body["lrfd_cases"][0]["reference"][1]["value"] = "1"
    body["lrfd_cases"][0]["components"][5]["value"] = ".1"
    record, shifted = physical_result(body)
    assert shifted["disposition"] == "EXECUTED"
    assert shifted["utilization"] == original["utilization"]
    assert shifted["design_resistance_kip"] == original["design_resistance_kip"]
    assert shifted["raw_actions"]["reference"][1]["magnitude"] == "1"
    assert record["inputs"]["lrfd_cases"][0]["components"][5]["value"] == ".1"
    body["lrfd_cases"][0]["components"][5]["value"] = "-.1"
    eccentric, blocked = physical_result(body)
    assert blocked["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert any("transported free moment" in reason for reason in blocked["reasons"])
    assert len(basis_rows(eccentric, "LRFD")) == 6


def test_si_source_minimum_diameter_is_not_replaced_by_the_us_rounding() -> None:
    body = physical_case()
    body["physical_context"]["hole_source"] = "SI_PRINTED"
    body["geometry"]["diameter"] = {"value": "9.529", "unit": "mm"}
    body["geometry"]["hole"] = {"value": "11.129", "unit": "mm"}
    record, result = physical_result(body)
    assert result["disposition"] == "GEOMETRY_FAIL"
    assert any("diameter" in reason for reason in result["reasons"])
    assert not basis_rows(record, "LRFD")
    assert len(basis_rows(record, "ASD")) == 7


@pytest.mark.parametrize("contained", [False, True])
def test_selected_brace_pair_fit_controls_red_without_activating_any_method(
    contained: bool,
) -> None:
    body = physical_case()
    body["alignment"] = "BRACE"
    if contained:
        body["geometry"]["xb"]["value"] = "2"
        body["geometry"]["xc"]["value"] = "1.5"
        body["physical_context"]["clear_flat_outstand"] = None
    record, result = physical_result(body)
    axes = record["physical_design"]["status_axes"]
    assert not basis_rows(record, "LRFD")
    assert not basis_rows(record, "ASD")
    assert result["disposition"] != "EXECUTED"
    if contained:
        assert record["assessment"]["fit"]["hole_state"] != "NOT_FIT"
        assert axes["whole_connection"] == "NOT_VERIFIED"
    else:
        assert record["assessment"]["fit"]["hole_state"] == "NOT_FIT"
        assert axes["detailing"] == "DETAILING_FAIL"
        assert axes["whole_connection"] == "FAIL_DETAILING"
        assert axes["viewer_tone"] == "red"


def test_native_geometry_rejects_valid_source_physical_context_at_outer_guard() -> None:
    from tests.hybrid_workflow_fixtures import live_native

    body = live_native()
    assert hybrid_workflow.HybridInputs.model_validate(body).connection == "CURRENT_NATIVE"
    body["physical_context"] = {"contract": "HYB2-D3-P4-PHYSICAL/1"}
    with LiveTransport() as client:
        rejected = client.post(BASE + "/preview", json=body)
    assert rejected.status_code == 422
    errors = rejected.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body"]
    assert errors[0]["msg"] == (
        "Value error, Source physical end/contact data cannot be grafted onto native geometry."
    )


def test_display_unit_conversion_keeps_unknown_outstand_and_gap_unknown() -> None:
    body = physical_case()
    body["physical_context"]["clear_flat_outstand"] = None
    body["physical_context"]["interface_gap"] = None
    with LiveTransport() as client:
        converted = client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
    assert converted.status_code == 200
    physical = converted.json()["physical_context"]
    assert physical["clear_flat_outstand"] is None
    assert physical["interface_gap"] is None
    assert physical["positive_end"]["distance"] == {"value": "127.0", "unit": "mm"}
    assert physical["hole_source"] == "US_CUSTOMARY_PRINTED"
    assert body["physical_context"]["positive_end"]["distance"] == {"value": "5", "unit": "in"}
