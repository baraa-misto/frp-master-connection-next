"""Independent F5 controlled source, project gates and actual Direct consumption."""

from __future__ import annotations

import io
import json
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal
from typing import Any, cast

import pytest
from pypdf import PdfReader
from tests.api.test_f593_f4 import design, f4_body, supported
from tests.api.test_mat1_routes import call, selection

import frp_master_connection.application.asce_shape_materials as shape
from frp_master_connection.api.mat1 import MaterialConditionsDTO, resolve_conditions
from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    catalog_property_basis,
    predefined_catalog,
    property_ledger,
    session_record,
    temperature_fahrenheit,
)
from frp_master_connection.application.mat1_native import adapt_native_material
from frp_master_connection.calculation import FRPPropertyKind, PhysicalQuantity, Unit
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.sources import SourceClassification
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def f5_body(
    *, resin: int = 0, si: bool = False, row_count: int = 2, **conditions: object
) -> dict[str, Any]:
    body = f4_body(si=si, row_count=row_count)
    record = shape.production_shape_catalog()[resin]
    body["assignments"]["default_material"] = selection(asdict(record))
    body["assignments"]["default_conditions"].update(
        {
            "maximum_temperature": {"value": "100", "unit": "degF"},
            "uv_weathering": "NONE_DECLARED",
            "freeze_thaw": "NONE_DECLARED",
        }
        | conditions
    )
    return body


def project_conditions(**changes: object) -> DesignConditions:
    return replace(
        DesignConditions(
            Decimal(70),
            Decimal(100),
            None,
            "REFERENCE",
            "NONE_DECLARED",
            "F5 QA ONLY",
            TimeEffectCategory.WIND_TORNADO_SEISMIC,
            "UNKNOWN",
            uv_weathering="NONE_DECLARED",
            freeze_thaw="NONE_DECLARED",
        ),
        **cast(Any, changes),
    )


def test_catalog_source_records_and_rc0_are_separate_and_immutable() -> None:
    before = predefined_catalog()
    response = call("GET", "/api/v1/frp-materials/catalog").json()
    assert len(response["records"]) == 4
    assert [r["content_digest"] for r in response["records"][:2]] == [
        r.content_digest for r in before
    ]
    assert all(r["property_basis"] == "DEVELOPMENT_NOMINAL" for r in response["records"][:2])
    minimum = {
        "tensile_strength_L": "30",
        "tensile_strength_T": "7",
        "tensile_modulus_L": "3000",
        "tensile_modulus_T": "800",
        "compressive_strength_L": "30",
        "compressive_modulus_L": "3000",
        "compressive_modulus_T": "1000",
        "in_plane_shear_strength_LT": "8",
        "in_plane_shear_modulus_LT": "400",
        "interlaminar_shear_strength": "3.5",
        "bearing_strength_L": "21",
        "bearing_strength_T": "18",
    }
    for record in shape.production_shape_catalog():
        assert catalog_property_basis(record) == shape.SHAPE_BASIS
        assert record.revision == "RC1"
        assert record.source_kind == shape.SHAPE_SOURCE
        assert {p.id: p.original for p in record.properties if p.id in minimum} == {
            k: Decimal(v) for k, v in minimum.items()
        }
        assert all(p.basis == shape.SHAPE_BASIS for p in record.properties)
        assert record.property("major_poisson_ratio_LT") is None
        assert record.property("compressive_strength_T") is None
        assert all(p.source_bolt_diameter_in is None for p in record.properties)
    assert predefined_catalog() == before
    assert (
        shape.production_shape_catalog()[0].properties
        == shape.production_shape_catalog()[1].properties
    )
    meta = shape.shape_source_metadata(shape.production_shape_catalog()[0])
    assert meta["product_scope"] == "PULTRUDED_SHAPE"
    assert meta["source_table"] == "Table 1-2"
    assert (
        "75%"
        in cast(dict[str, str], meta["durability_requirements"])[
            "longitudinal_transverse_tensile_retention"
        ]
    )
    assert (
        meta["modulus_role"] == "CHARACTERISTIC_STRENGTH_STABILITY_ONLY; NO_MEAN_MODULUS_AUTHORITY"
    )
    meta["product_scope"] = "PLATE"
    assert (
        shape.shape_source_metadata(shape.production_shape_catalog()[0])["product_scope"]
        == "PULTRUDED_SHAPE"
    )


def test_source_digest_tampering_and_record_impersonation_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = deepcopy(shape.shape_catalog_data())
    raw["records"][0]["properties"]["bearing_strength_L"]["value"] = "30"

    class Resource:
        def joinpath(self, path: str) -> Resource:
            assert path.endswith("asce74_shape_minimum_rc1.json")
            return self

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            return json.dumps(raw)

    shape.shape_catalog_data.cache_clear()
    monkeypatch.setattr(shape, "files", lambda _: Resource())
    try:
        with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
            shape.shape_catalog_data()
    finally:
        shape.shape_catalog_data.cache_clear()
        monkeypatch.undo()
    forged = replace(shape.production_shape_catalog()[0], source_kind="USER_SUPPLIED_SESSION_DATA")
    assert not shape.is_shape_basis(forged)
    assert catalog_property_basis(forged) == "USER_DEFINED"


@pytest.mark.parametrize("resin", [0, 1])
@pytest.mark.parametrize(
    ("f", "strength", "modulus"),
    [
        ("70", ("1", "1"), ("1", "1")),
        ("90", ("1", "1"), ("1", "1")),
        ("90.001", (".99999", ".979992"), (".979992", ".959994")),
        ("100", (".9", ".9"), (".9", ".9")),
        ("120", (".7", ".74"), (".74", ".78")),
        ("140", (".5", ".58"), (".58", ".66")),
        ("140.001", (None, None), (None, None)),
    ],
)
def test_both_resin_exact_table_2_2(
    resin: int, f: str, strength: tuple[str | None, ...], modulus: tuple[str | None, ...]
) -> None:
    record = shape.production_shape_catalog()[resin]
    conditions = project_conditions(sustained_f=Decimal(f), maximum_f=Decimal(f))
    s = property_ledger("ANGLE", record, "tensile_strength_L", conditions)
    e = property_ledger("ANGLE", record, "tensile_modulus_L", conditions)
    assert s.ct == (None if strength[resin] is None else Decimal(cast(str, strength[resin])))
    assert e.ct == (None if modulus[resin] is None else Decimal(cast(str, modulus[resin])))
    assert s.original == 30
    assert s.cm == 1
    assert s.cch == 1
    assert s.lambda_factor == 1
    assert e.lambda_factor is None
    if Decimal(f) > 140:
        assert s.adjusted_candidate is None
        assert "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED" in s.issues
    else:
        assert not s.issues
        assert not e.issues
        assert s.adjusted_candidate == Decimal(30) * cast(Decimal, s.ct)


@pytest.mark.parametrize("resin", [0, 1])
@pytest.mark.parametrize(
    ("state", "strength", "modulus"),
    [
        ("REFERENCE", "1", "1"),
        ("SUSTAINED_MOISTURE", ".75", ".90"),
        ("UNKNOWN", None, None),
        ("OTHER", None, None),
    ],
)
def test_moisture_separate_from_durability_retention(
    resin: int, state: str, strength: str | None, modulus: str | None
) -> None:
    record = shape.production_shape_catalog()[resin]
    conditions = project_conditions(moisture=state)
    s = property_ledger("ANGLE", record, "tensile_strength_L", conditions)
    e = property_ledger("ANGLE", record, "tensile_modulus_L", conditions)
    assert s.cm == (None if strength is None else Decimal(strength))
    assert e.cm == (None if modulus is None else Decimal(modulus))
    assert s.adjusted_candidate == (None if strength is None else 30 * Decimal(strength))
    assert not any("QUALIFICATION" in issue for issue in s.issues)
    if state == "UNKNOWN":
        assert s.issues == ("MOISTURE_PROJECT_CONDITION_REQUIRED",)
    elif state == "OTHER":
        assert s.issues == ("MOISTURE_ADJUSTMENT_SOURCE_REQUIRED",)


@pytest.mark.parametrize("resin", [0, 1])
@pytest.mark.parametrize("chemical", ["NONE_DECLARED", "SPECIFIED", "UNKNOWN"])
def test_chemical_project_state_is_not_material_qualification(resin: int, chemical: str) -> None:
    ledger = property_ledger(
        "ANGLE",
        shape.production_shape_catalog()[resin],
        "bearing_strength_L",
        project_conditions(chemical=chemical),
    )
    assert ledger.cch == (Decimal(1) if chemical == "NONE_DECLARED" else None)
    assert not any("QUALIFICATION" in i for i in ledger.issues)
    if chemical != "NONE_DECLARED":
        assert ledger.adjusted_candidate is None
        assert ledger.issues == (
            (
                "CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED"
                if chemical == "SPECIFIED"
                else "CHEMICAL_EXPOSURE_UNRESOLVED"
            ),
        )


@pytest.mark.parametrize(("maximum", "required"), [("100", "180"), ("140", "180"), ("150", "190")])
@pytest.mark.parametrize("resin", [0, 1])
def test_tg_specification_threshold_is_not_an_actual_measurement(
    maximum: str, required: str, resin: int
) -> None:
    record = shape.production_shape_catalog()[resin]
    conditions = project_conditions(maximum_f=Decimal(maximum), tg_f=Decimal(1))
    basis = shape.material_condition_basis(record, conditions)
    assert basis["required_tg"] == {"value": required, "unit": "degF"}
    assert basis["actual_tg_f"] is None
    assert basis["status"] == "SPECIFICATION_REQUIREMENT_SATISFIED_BY_PROJECT_CONFORMANCE"
    assert property_ledger("ANGLE", record, "bearing_strength_L", conditions).ct == 1
    assert not property_ledger("ANGLE", record, "bearing_strength_L", conditions).issues


@pytest.mark.parametrize(
    ("tg", "status"),
    [("179.999", "FAIL"), ("180", "PASS"), ("180.001", "PASS"), (None, "NOT_CONFIRMED")],
)
def test_actual_custom_tg_boundary_never_promotes_custom_source(
    tg: str | None, status: str
) -> None:
    record = session_record(
        "SESSION:F5",
        "1",
        "Custom",
        "User",
        "ISOPHTHALIC_POLYESTER",
        {
            "tensile_strength_L": {
                "label": "Ft,L",
                "symbol": "Ft,L",
                "value": "30",
                "unit": "ksi",
                "basis": "CHARACTERISTIC",
            }
        },
    )
    conditions = project_conditions(tg_f=None if tg is None else Decimal(tg))
    assert shape.shape_temperature_state(record, conditions) == status
    assert catalog_property_basis(record) == "USER_DEFINED"
    assert not shape.shape_source_metadata(record)
    assert shape.material_condition_basis(record, conditions)["tg_evidence"] == (
        "MISSING" if tg is None else "USER_SUPPLIED"
    )
    ledger = property_ledger("ANGLE", record, "tensile_strength_L", conditions)
    assert ("ACTUAL_TG_BELOW_PROJECT_REQUIREMENT" in ledger.issues) == (status == "FAIL")


@pytest.mark.parametrize("field", ["uv_weathering", "freeze_thaw"])
@pytest.mark.parametrize("state", ["NONE_DECLARED", "SPECIFIED", "UNKNOWN"])
def test_extraordinary_and_unknown_exposure_are_distinct(field: str, state: str) -> None:
    conditions = project_conditions(**{field: state})
    issues = shape.shape_project_issues(conditions)
    assert len(issues) == (0 if state == "NONE_DECLARED" else 1)
    if issues:
        assert ("EXTRAORDINARY" in issues[0]) == (state == "SPECIFIED")
        assert ("PROJECT_CONDITION" in issues[0]) == (state == "UNKNOWN")
    ledger = property_ledger(
        "ANGLE", shape.production_shape_catalog()[0], "bearing_strength_L", conditions
    )
    assert ledger.issues == issues
    assert ledger.adjusted_candidate == 21


def test_protective_system_and_other_project_exposure_remain_review_required() -> None:
    assert shape.shape_project_issues(
        project_conditions(protective_measures="coating", exposure_notes="unusual immersion")
    ) == ("PROTECTIVE_SYSTEM_REVIEW_REQUIRED", "PROJECT_EXPOSURE_REVIEW_REQUIRED")


@pytest.mark.parametrize(
    ("inch", "kip"), [(".375", ".650"), (".500", ".900"), (".750", "1.250"), (".49", None)]
)
@pytest.mark.parametrize("resin", [0, 1])
def test_pull_through_is_exact_frp_thickness_in_both_units(
    inch: str, kip: str | None, resin: int
) -> None:
    record = shape.production_shape_catalog()[resin]
    expected = None if kip is None else PhysicalQuantity.of(kip, Unit.KIP)
    assert (
        shape.pull_through_for_frp_thickness(record, PhysicalQuantity.of(inch, Unit.IN)) == expected
    )
    assert (
        shape.pull_through_for_frp_thickness(
            record, PhysicalQuantity.of(Decimal(inch) * Decimal("25.4"), Unit.MM)
        )
        == expected
    )
    with pytest.raises(ValueError, match="PRODUCTION_SHAPE"):
        shape.pull_through_for_frp_thickness(
            predefined_catalog()[0], PhysicalQuantity.of(inch, Unit.IN)
        )


def test_only_direct_shape_binding_and_no_unused_property_gate() -> None:
    record = shape.production_shape_catalog()[0]
    with pytest.raises(ValueError, match="FAMILY_BINDING_DEFERRED"):
        adapt_native_material("PLATE", record, project_conditions())
    adapter = adapt_native_material(
        "ANGLE", record, project_conditions(), shape_binding_verified=True
    )
    assert adapter.adjusted_snapshot.basis is SourceClassification.CODE_CHARACTERISTIC
    assert adapter.adjusted_snapshot.lookup(FRPPropertyKind.FC_T) is None
    assert adapter.adjusted_snapshot.lookup(FRPPropertyKind.NU_LT) is None
    assert not adapter.unresolved_issues
    body = f5_body()
    body["legacy_request"]["direct_finalization_contract_version"] = None
    body["legacy_request"]["supporting_w_longitudinal_ends"] = None
    response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert response.status_code == 422
    assert "FAMILY_BINDING_DEFERRED" in response.text
    body = f5_body()
    body["legacy_request"]["layers"][0]["element_classification"] = "PLATE"
    assert call("POST", "/api/v1/frp-materials/multi-row/design-check", body).status_code == 422


@pytest.mark.parametrize("resin", [0, 1])
def test_direct_signed_source_and_native_property_authority(resin: int) -> None:
    body = f5_body(resin=resin)
    result = design(body)
    assert result["overall_status"] == "ENGINEERING_REVIEW_REQUIRED"
    assert not result["material_issues"]
    source = result["material_sources"]["default"]
    assert source["id"] == body["assignments"]["default_material"]["id"]
    assert source["property_basis"] == shape.SHAPE_BASIS
    assert source["specification"]["reference_condition"] == "REFERENCE"
    assert (
        result["material_sources"]["temperature_applicability"]["default"]
        == "SPECIFICATION_REQUIREMENT_SATISFIED_BY_PROJECT_CONFORMANCE"
    )
    native = result["native_design"]
    assert "MAT1_MATERIAL_SOURCE_QUALIFICATION_REQUIRED" not in native["preview"]["warnings"]
    assert len(supported(result)) == 8
    assert all("PULL_THROUGH" not in c["limit_state"] for c in supported(result))
    assert all(
        ledger["original"] == "21" and ledger["adjusted_candidate"] == "21"
        for ledger in result["material_ledgers"]
        if ledger["property_id"] == "bearing_strength_L"
    )
    integration = native["automatic_group_mode_integration"]
    assert all(
        not i.startswith("MATERIAL_SOURCE_REVIEW")
        for i in integration["incomplete_required_check_ids"]
    )
    assert (
        "DIRECT_WHOLE_CONNECTION_SECTION_2_3_2_QUALIFICATION"
        in integration["incomplete_required_check_ids"]
    )


@pytest.mark.parametrize(
    "change", ["SUSTAINED_MOISTURE", "HOT", "MAX150", "CHEMICAL", "UV", "FREEZE", "UNKNOWN", "RED"]
)
def test_direct_factors_project_limits_and_numerical_red(change: str) -> None:
    body = f5_body()
    c = body["assignments"]["default_conditions"]
    if change == "SUSTAINED_MOISTURE":
        c["moisture"] = "SUSTAINED_MOISTURE"
    if change == "HOT":
        c["sustained_temperature"]["value"] = "140.001"
        c["maximum_temperature"]["value"] = "150"
    if change == "MAX150":
        c["maximum_temperature"]["value"] = "150"
    if change == "CHEMICAL":
        c["chemical"] = "SPECIFIED"
    if change == "UV":
        c["uv_weathering"] = "SPECIFIED"
    if change == "FREEZE":
        c["freeze_thaw"] = "SPECIFIED"
    if change == "UNKNOWN":
        c["moisture"] = "UNKNOWN"
    if change == "RED":
        body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
            "force"
        ]["x"] = "-7"
    result = design(body)
    if change == "RED":
        assert result["overall_status"] == "FAIL"
    if change == "HOT":
        assert "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED" in result["material_issues"]
    if change == "MAX150":
        assert (
            result["material_sources"]["condition_basis"]["default"]["required_tg"]["value"]
            == "190"
        )
        assert not result["material_issues"]
        assert all(ledger["ct"] == "1" for ledger in result["material_ledgers"])
    if change == "SUSTAINED_MOISTURE":
        assert not result["material_issues"]
        assert all(
            ledger["cm"] == ("0.90" if "modulus" in ledger["property_id"] else "0.75")
            for ledger in result["material_ledgers"]
        )
    if change in {"HOT", "CHEMICAL", "UV", "FREEZE", "UNKNOWN"}:
        assert result["material_issues"]
        assert any(
            i.startswith("PROJECT_CONDITION_REVIEW")
            for i in result["native_design"]["automatic_group_mode_integration"][
                "incomplete_required_check_ids"
            ]
        )


def test_real_pdf_material_basis_and_nonmutation() -> None:
    body = f5_body()
    result = design(body)
    signer = SnapshotSigner(b"F5-REPORT-QA-32-BYTE-KEY-01234567")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f5"
        ),
        account_id="f5",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    text = " ".join(
        " ".join(
            p.extract_text() or ""
            for p in PdfReader(io.BytesIO(render_report_pdf(snapshot, ReportOptions()))).pages
        ).split()
    )
    assert "Table 1-2 minimum characteristic" in text
    assert ">= 180 degF" in text
    assert "actual product Tg not measured" in text
    assert "no mean-modulus authority" in text
    assert "Development only" not in text
    assert "ASCE minimum characteristic shape specification; whole-connection" in text
    assert "F593G" in text
    assert "100 ksi" in text
    assert (snapshot.request, snapshot.result) == before

    # A source-required project condition must remain visible in an export,
    # independently of the resolved production material specification.
    body["assignments"]["default_conditions"]["chemical"] = "SPECIFIED"
    result = design(body)
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f5"
        ),
        account_id="f5",
    )
    before = deepcopy((snapshot.request, snapshot.result))
    text = " ".join(
        " ".join(
            p.extract_text() or ""
            for p in PdfReader(io.BytesIO(render_report_pdf(snapshot, ReportOptions()))).pages
        ).split()
    )
    assert "Actual project environmental conditions / adjustment sources remain unresolved" in text
    assert "CCH=source required" in text
    assert "Development only" not in text
    assert (snapshot.request, snapshot.result) == before


def test_existing_single_row_methods_consume_characteristic_values_and_preserve_red() -> None:
    # A previously governed one-row regression case, not a change to owner geometry.
    body = f5_body(row_count=1)
    body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
        "force"
    ]["y"] = "1.75"
    result = design(body)
    single = result["native_design"]["automatic_group_mode_integration"]["direct_single_row_result"]
    checks = {c["limit_state"]: c for c in single["checks"] if c["layer_id"] == "layer-A"}
    assert checks["SINGLE_ROW_CLEAVAGE"]["numerical_comparison"] == "FAIL"
    assert (
        checks["SINGLE_ROW_NET_TENSION"]["equation_trace"]["native"]["tensile_property"][
            "source_property"
        ]["value"]
        == "30"
    )
    assert result["overall_status"] == "FAIL"
    assert (
        "DIRECT_WHOLE_CONNECTION_SECTION_2_3_2_QUALIFICATION"
        in single["incomplete_required_check_ids"]
    )


@pytest.mark.parametrize("f", ["70", "90", "90.001", "100", "120", "140", "140.001"])
def test_fahrenheit_celsius_factor_input_round_trip(f: str) -> None:
    value = Decimal(f)
    c = str((value - Decimal(32)) * Decimal(5) / Decimal(9))
    # Repeating Celsius representations round only through the project's existing
    # decimal representation arithmetic; no engineering tolerance is introduced.
    assert temperature_fahrenheit(c, "degC") == value
    original = f5_body()["assignments"]["default_conditions"]
    original.update(
        sustained_temperature={"value": c, "unit": "degC"},
        maximum_temperature={"value": c, "unit": "degC"},
    )
    assert resolve_conditions(MaterialConditionsDTO.model_validate(original)).sustained_f == value
