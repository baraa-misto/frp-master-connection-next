"""MC1 strength-only chemistry, canonical inputs and historical authority."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest
from pydantic import ValidationError
from tests.api.test_asce_shape_f5 import f5_body
from tests.api.test_f593_f4 import design, supported
from tests.api.test_mat1_routes import call
from tests.direct_mc1_fixtures import mc1_body, mc1_cases, mc1_other_resin_body, raw_mc1_native

from frp_master_connection.api.mat1 import (
    FactorRequestDTO,
    MaterialAssignmentsDTO,
    MaterialConditionsDTO,
    MultiRowMAT1RequestDTO,
    require_legacy_policy,
    resolve_conditions,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application.asce_shape_materials import production_shape_catalog
from frp_master_connection.application.direct_material_conditions import (
    conditions_audit,
    gate_direct_temperature_result,
    ledger_audit,
    modulus_cm_ct_candidate,
)
from frp_master_connection.application.direct_qualification_records import content_digest
from frp_master_connection.application.mat1_materials import property_ledger
from frp_master_connection.application.mat1_native import adapt_native_material


def conditions(
    temperature: str = "100", unit: str = "degF", **changes: object
) -> MaterialConditionsDTO:
    return MaterialConditionsDTO.model_validate(
        mc1_body(temperature, unit, **changes)["assignments"]["default_conditions"]
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "bad",
        True,
        "NaN",
        "Infinity",
        "-Infinity",
        "-1",
        "0",
        "-0",
        "1.000000000000000001",
        None,
    ],
)
def test_reject_custom_factor_exactly(value: object) -> None:
    with pytest.raises(ValidationError):
        conditions(chemical="SPECIFIED", chemical_strength_factor=value)


@pytest.mark.parametrize("value", [".8", "1.00", "0.000000000000000001", "1e-88"])
def test_accept_exact_factor_without_documents(value: str) -> None:
    dto = conditions(chemical="SPECIFIED", chemical_strength_factor=value)
    assert Decimal(dto.chemical_strength_factor or "0") == Decimal(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("design_temperature", None),
        ("sustained_temperature", {"value": "90", "unit": "degF"}),
        ("maximum_temperature", {"value": "101", "unit": "degF"}),
        ("moisture", "UNKNOWN"),
        ("moisture", "OTHER"),
        ("chemical", "UNKNOWN"),
        ("chemical_strength_factor", ".8"),
    ],
)
def test_new_policy_fails_closed(field: str, value: object) -> None:
    body = mc1_body()["assignments"]["default_conditions"]
    body[field] = value
    with pytest.raises(ValidationError):
        MaterialConditionsDTO.model_validate(body)


@pytest.mark.parametrize(
    ("key", "value"),
    [("design_temperature", {"value": "100", "unit": "degF"}), ("chemical_strength_factor", ".8")],
)
def test_legacy_cannot_smuggle_new_fields(key: str, value: object) -> None:
    body = f5_body()["assignments"]["default_conditions"]
    body[key] = value
    with pytest.raises(ValidationError, match="explicit Direct"):
        MaterialConditionsDTO.model_validate(body)


def test_direct_only_boundary() -> None:
    body = mc1_body()
    with pytest.raises(ValueError, match="Direct"):
        require_legacy_policy(MaterialAssignmentsDTO.model_validate(body["assignments"]))
    body["legacy_request"]["direct_finalization_contract_version"] = None
    with pytest.raises(ValidationError, match="Direct"):
        MultiRowMAT1RequestDTO.model_validate(body)
    factor = {
        "contract": "MAT1-FACTOR-RC0",
        "material": body["assignments"]["default_material"],
        "conditions": mc1_body()["assignments"]["default_conditions"],
        "component_id": "BRACE",
        "property_ids": ["tensile_strength_L"],
    }
    with pytest.raises(ValidationError, match="Direct"):
        FactorRequestDTO.model_validate(factor)
    assert FactorRequestDTO.model_validate({**factor, "family_id": "multi-row"})
    assert (
        call(
            "POST", "/api/v1/frp-materials/factor-candidates", {**factor, "family_id": "multi-row"}
        ).status_code
        == 200
    )


def test_mc1_rejects_valid_non_direct_legacy_contract() -> None:
    body = mc1_body()
    legacy = body["legacy_request"]
    legacy["direct_finalization_contract_version"] = None
    # Preserve the separate Supporting W authority test above; reach the outer MC1 guard here.
    legacy["supporting_w_longitudinal_ends"] = None
    validated_legacy = MultiRowConnectionRequestDTO.model_validate(legacy)
    assert validated_legacy.row_count == 2
    assert validated_legacy.direct_finalization_contract_version is None

    with pytest.raises(
        ValidationError,
        match="MC1 material policy requires the Direct finalization contract",
    ) as error:
        MultiRowMAT1RequestDTO.model_validate(body)
    assert len(error.value.errors()) == 1
    assert error.value.errors()[0]["msg"] == (
        "Value error, MC1 material policy requires the Direct finalization contract."
    )


@pytest.mark.parametrize("conflict", ["legacy-overrides", "override-only", "different-new-inputs"])
def test_shared_mc1_conditions_cannot_be_bypassed_by_overrides(conflict: str) -> None:
    body = mc1_body(chemical="SPECIFIED", chemical_strength_factor=".8")
    default = body["assignments"]["default_conditions"]
    historical = mc1_cases()["owner-yellow"]["assignments"]["default_conditions"]
    override = historical
    if conflict == "override-only":
        body["assignments"]["default_conditions"] = historical
        override = default
    elif conflict == "different-new-inputs":
        override = mc1_body("90", chemical="SPECIFIED", chemical_strength_factor=".9")[
            "assignments"
        ]["default_conditions"]
    body["assignments"]["condition_overrides"] = {
        layer["component_id"]: deepcopy(override) for layer in body["legacy_request"]["layers"]
    }
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert response.status_code == 422
    assert "one shared set of connection conditions" in response.text


def test_matching_mc1_overrides_preserve_canonical_units_and_native_results() -> None:
    body = mc1_body("104", chemical="SPECIFIED", chemical_strength_factor=".80")
    original = design(body)
    override = mc1_body("40", "degC", chemical="SPECIFIED", chemical_strength_factor=".8")[
        "assignments"
    ]["default_conditions"]
    body["assignments"]["condition_overrides"] = {
        layer["component_id"]: deepcopy(override) for layer in body["legacy_request"]["layers"]
    }
    result = design(body)
    assert result["native_design"] == original["native_design"]
    assert result["material_ledgers"] == original["material_ledgers"]
    assert result["final_decision"]["final_status"] == "YELLOW"


@pytest.mark.parametrize(
    ("moisture", "cm_strength", "cm_modulus"),
    [("REFERENCE", "1", "1"), ("SUSTAINED_MOISTURE", ".75", ".9")],
)
def test_strength_once_and_modulus_unresolved(
    moisture: str, cm_strength: str, cm_modulus: str
) -> None:
    domain = resolve_conditions(
        conditions(moisture=moisture, chemical="SPECIFIED", chemical_strength_factor=".8")
    )
    native = adapt_native_material(
        "BRACE", production_shape_catalog()[0], domain, shape_binding_verified=True
    )
    for ledger in native.ledgers:
        if "strength" in ledger.property_id:
            assert ledger.cm == Decimal(cm_strength)
            assert ledger.ct == Decimal(".90")
            assert ledger.cch == Decimal(".8")
            assert ledger.adjusted_candidate == ledger.original * ledger.cm * ledger.ct * ledger.cch
            assert "CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED" not in ledger.issues
            assert "ENGINEER_SPECIFIED" in ledger_audit(ledger, domain)["chemical_factor_origin"]
        elif "modulus" in ledger.property_id:
            assert ledger.cm == Decimal(cm_modulus)
            assert ledger.ct == Decimal(".90")
            assert ledger.cch is None
            assert ledger.adjusted_candidate is None
            assert modulus_cm_ct_candidate(ledger) == ledger.original * ledger.cm * ledger.ct
            assert ledger_audit(ledger, domain)["chemical_modulus_applicability"] == "UNEVALUATED"
            entries = [
                p
                for p in native.adjusted_snapshot.properties
                if any("chemical modulus" in note for note in p.engineer_notes)
            ]
            assert len(entries) == 5
            assert all(not p.use_in_chapter_8_equations for p in entries)
    assert modulus_cm_ct_candidate(native.ledgers[0]) is None
    modulus = next(item for item in native.ledgers if "modulus" in item.property_id)
    assert modulus_cm_ct_candidate(replace(modulus, cm=None)) is None
    assert modulus_cm_ct_candidate(replace(modulus, ct=None)) is None


@pytest.mark.parametrize(
    ("temperature", "ct", "tg"),
    [
        ("90", "1", "180"),
        ("100", ".9", "180"),
        ("140", ".5", "180"),
        ("140.0001", None, "180.0001"),
    ],
)
def test_temperature_boundaries(temperature: str, ct: str | None, tg: str) -> None:
    result = design(mc1_body(temperature))
    ledger = next(
        item for item in result["material_ledgers"] if item["property_id"] == "tensile_strength_L"
    )
    assert ledger["ct"] is None if ct is None else Decimal(ledger["ct"]) == Decimal(ct)
    basis = result["material_sources"]["condition_basis"]["default"]
    assert Decimal(basis["required_tg"]["value"]) == Decimal(tg)
    assert result["final_decision"]["final_status"] == "YELLOW"
    if ct is None:
        assert ledger["adjusted_candidate"] is None
        assert "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED" in ledger["issues"]
        assert result["final_decision"]["analytical_check_summary"]["evaluated"] == 2
        assert all(
            row["limit_state"] == "BOLT_SHEAR"
            for row in supported(result)
            if row["availability"] == "CALCULATED"
        )


@pytest.mark.parametrize("source", ["over-140", "other-resin"])
def test_missing_temperature_factor_retains_raw_diagnostics_without_frp_pass(source: str) -> None:
    body = mc1_body("140.0001") if source == "over-140" else mc1_other_resin_body()
    result = design(body)
    evidence = result["direct_material_applicability"]
    raw = raw_mc1_native(result)
    assert content_digest(raw) == evidence["raw_engine_diagnostic_native_digest"]
    assert raw != result["native_design"]
    assert len(evidence["blocked_check_ids"]) == 6
    rows = supported(result)
    blocked = [row for row in rows if row["result_id"] in evidence["blocked_check_ids"]]
    assert len(blocked) == 6
    assert result["final_decision"]["analytical_check_summary"]["evaluated"] == 2
    assert result["final_decision"]["final_status"] == "YELLOW"
    assert all(
        row["availability"] == "SOURCE_DATA_PENDING"
        and row["numerical_comparison"] == "NOT_EVALUATED"
        and row["design_resistance"] is None
        and row["utilization"] is None
        for row in blocked
    )
    historical = deepcopy(body)
    conditions_body = historical["assignments"]["default_conditions"]
    conditions_body.pop("direct_policy")
    conditions_body.pop("design_temperature")
    old = design(historical)
    assert supported({"native_design": raw}) == supported(old)
    assert old["final_decision"]["analytical_check_summary"]["evaluated"] == 8
    assert evidence["raw_engine_fingerprints_are_diagnostic_only"] is True
    assert gate_direct_temperature_result(old) is old


def test_independent_bolt_failure_keeps_red_above_temperature_domain() -> None:
    body = mc1_cases()["analytical-red"]
    for key in ("design_temperature", "sustained_temperature", "maximum_temperature"):
        body["assignments"]["default_conditions"][key] = {"value": "140.0001", "unit": "degF"}
    force = body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][
        0
    ]["force"]
    for axis in ("x", "y", "z"):
        force[axis] = str(Decimal(force[axis]) * 10)
    result = design(body)
    assert result["final_decision"]["final_status"] == "RED"
    assert result["final_decision"]["analytical_check_summary"]["failed"] == 2
    assert all(
        identity.startswith("BOLT_SHEAR:")
        for identity in result["native_design"]["automatic_group_mode_integration"][
            "failed_check_ids"
        ]
    )


def test_source_gate_does_not_create_results_for_missing_native_integration() -> None:
    result = {
        "material_ledgers": [
            {
                "direct_policy": "SHEAR01-DIRECT-MC1",
                "issues": ["TEST_BASED_TEMPERATURE_FACTOR_REQUIRED"],
            }
        ],
        "native_design": {"automatic_group_mode_integration": None},
    }
    gated = gate_direct_temperature_result(result)
    assert gated["native_design"]["automatic_group_mode_integration"] is None
    assert gated["direct_material_applicability"]["blocked_check_ids"] == []


def test_single_row_frp_diagnostics_do_not_pass_above_temperature_domain() -> None:
    body = mc1_body("140.0001")
    body["legacy_request"] = f5_body(row_count=1)["legacy_request"]
    body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
        "force"
    ]["y"] = "1.75"
    result = design(body)
    single = result["native_design"]["automatic_group_mode_integration"]["direct_single_row_result"]
    assert all(row["availability"] != "CALCULATED" for row in single["checks"])
    assert any(
        identity.startswith("SINGLE_ROW_")
        for identity in result["direct_material_applicability"]["blocked_check_ids"]
    )
    assert result["final_decision"]["final_status"] == "YELLOW"


def test_exact_f_c_parity() -> None:
    us = design(mc1_body("104", "degF", chemical="SPECIFIED", chemical_strength_factor=".80"))
    si = design(mc1_body("40", "degC", chemical="SPECIFIED", chemical_strength_factor="0.8"))
    for key in (
        "native_design",
        "material_ledgers",
        "material_sources",
        "final_decision",
        "qualification_evaluation",
    ):
        assert us[key] == si[key], key
    assert conditions_audit(resolve_conditions(conditions(temperature="104"))) == conditions_audit(
        resolve_conditions(conditions(temperature="40", unit="degC"))
    )


def test_old_two_temperature_behavior_and_approved_new_difference() -> None:
    legacy = f5_body()
    dto = MaterialConditionsDTO.model_validate(legacy["assignments"]["default_conditions"])
    dumped = dto.model_dump(mode="json")
    assert all(dumped[k] == v for k, v in legacy["assignments"]["default_conditions"].items())
    assert not {"direct_policy", "design_temperature", "chemical_strength_factor"} & dumped.keys()
    old, new = design(legacy), design(mc1_body())
    old_l = next(
        item for item in old["material_ledgers"] if item["property_id"] == "tensile_strength_L"
    )
    new_l = next(
        item for item in new["material_ledgers"] if item["property_id"] == "tensile_strength_L"
    )
    assert Decimal(old_l["ct"]) == 1
    assert Decimal(new_l["ct"]) == Decimal(".9")
    assert (
        new["native_design"]["automatic_demand_result"]
        == old["native_design"]["automatic_demand_result"]
    )
    assert "direct_policy" not in conditions_audit(resolve_conditions(dto))
    ledger = property_ledger(
        "BRACE", production_shape_catalog()[0], "tensile_strength_L", resolve_conditions(dto)
    )
    assert "direct_policy" not in ledger_audit(ledger, resolve_conditions(dto))
    specified = deepcopy(legacy)
    specified["assignments"]["default_conditions"]["chemical"] = "SPECIFIED"
    assert (
        "CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED" in design(specified)["material_ledgers"][0]["issues"]
    )


@pytest.mark.parametrize(
    ("category", "factor"),
    [
        ("DEAD_ONLY", ".4"),
        ("IMPACT", "1"),
        ("STORAGE", ".6"),
        ("LONG_TERM_OPERATING", ".4"),
        ("OTHER_LIVE", ".8"),
        ("SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE", ".75"),
        ("WIND_TORNADO_SEISMIC", "1"),
    ],
)
def test_seven_lambda_values(category: str, factor: str) -> None:
    dto = conditions(
        time_effect_category=category,
        full_amplitude_duration="MORE_THAN_ONE_YEAR" if category == "LONG_TERM_OPERATING" else "",
    )
    ledger = property_ledger(
        "BRACE", production_shape_catalog()[0], "tensile_strength_L", resolve_conditions(dto)
    )
    assert ledger.lambda_factor == Decimal(factor)
    assert ledger.adjusted_candidate == Decimal("27")


def test_no_hidden_traps_or_fabricated_no_exposure() -> None:
    assert not design(mc1_body())["material_issues"]
    new = conditions().model_dump(mode="json")
    assert new["uv_weathering"] == new["freeze_thaw"] == "UNKNOWN"
    extraordinary = design(
        mc1_body(
            uv_weathering="SPECIFIED",
            freeze_thaw="SPECIFIED",
            exposure_notes="Known extraordinary exposure",
            protective_measures="Imported coating",
        )
    )
    assert "EXTRAORDINARY_UV_WEATHERING_REVIEW_REQUIRED" in extraordinary["material_issues"]
    assert "EXTRAORDINARY_FREEZE_THAW_REVIEW_REQUIRED" in extraordinary["material_issues"]
    assert extraordinary["final_decision"]["final_status"] == "YELLOW"


@pytest.mark.parametrize("name", list(mc1_cases()))
def test_real_cases_preserve_status_and_qualification(name: str) -> None:
    result = design(mc1_cases()[name])
    decision = result["final_decision"]
    assert decision["final_status"] == ("RED" if name == "analytical-red" else "YELLOW")
    assert result["qualification_evaluation"]["capacity_state"] == "UNEVALUATED"
    unresolved = {
        r["check_id"] for r in decision["schedule"] if r["category"] == "REQUIRED_UNRESOLVED"
    }
    legacy = design(mc1_cases()["owner-yellow"])
    required = {
        r["check_id"]
        for r in legacy["final_decision"]["schedule"]
        if r["category"] == "REQUIRED_UNRESOLVED"
    }
    assert len(required) == 6
    assert required <= unresolved
    if name == "custom-chemical":
        assert len(supported(result)) == 8
        assert "CHEMICAL_MODULUS_APPLICABILITY_UNRESOLVED" in result["material_issues"]
