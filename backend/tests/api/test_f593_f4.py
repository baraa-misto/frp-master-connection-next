"""F4 controlled row boundaries, source identity, native routing and thread gates."""

from __future__ import annotations

import io
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pypdf import PdfReader
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body

from frp_master_connection.api.f593_catalog_source import (
    catalog_digest,
    controlled_catalog,
    validate_catalog,
)
from frp_master_connection.api.fasteners import CatalogFastenerSelectionDTO, fastener_source_record
from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import multirow_orchestration as multirow_service
from frp_master_connection.application.f593_catalog import (
    CATALOG_DIGEST,
    CATALOG_ID,
    CatalogBinding,
    CatalogPlane,
)
from frp_master_connection.application.f593_catalog import (
    bind_f593_catalog as _bind_f593_catalog,
)
from frp_master_connection.application.mat1_multirow import bind_multirow_material
from frp_master_connection.calculation import (
    MultiRowCheckFamily,
    PhysicalQuantity,
    PlanAvailability,
    Unit,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.reporting.f593_report import f593_bolt_rows, f593_source_rows
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def bind_f593_catalog(
    diameter: PhysicalQuantity, planes: tuple[CatalogPlane, ...], **selectors: str
) -> CatalogBinding:
    return _bind_f593_catalog(diameter, planes, catalog=controlled_catalog(), **selectors)


def dataset() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            Path(__file__)
            .parents[2]
            .joinpath("src/frp_master_connection/data/astm_f593_group2_rc1.json")
            .read_text()
        ),
    )


def binding(
    diameter: str,
    *,
    condition: str = "COLD_WORKED",
    alloy: str = "316",
    unit: Unit = Unit.IN,
    thread: str = "EXCLUDED",
) -> CatalogBinding:
    return bind_f593_catalog(
        PhysicalQuantity.of(diameter, unit),
        (CatalogPlane("SHEAR_PLANE_1", cast(Any, thread)),),
        condition=condition,
        alloy=alloy,
    )


@pytest.mark.parametrize("alloy", ["316", "316L"])
@pytest.mark.parametrize(
    ("diameter", "row", "fnt"),
    [
        (".250", "CW1", "100"),
        (".500", "CW1", "100"),
        (".625", "CW1", "100"),
        (".625000000000000000000000000001", None, None),
        (".749999999999999999999999999999", None, None),
        (".750", "CW2", "85"),
        ("1.000", "CW2", "85"),
        ("1.500", "CW2", "85"),
        ("1.500000000000000000000000000001", None, None),
        (".249999999999999999999999999999", None, None),
    ],
)
def test_inclusive_ranges_and_exact_gap(
    alloy: str, diameter: str, row: str | None, fnt: str | None
) -> None:
    b = binding(diameter, alloy=alloy)
    assert b.fastener.fnt == (PhysicalQuantity.of(fnt, Unit.KSI) if fnt is not None else None)
    assert b.source_record["selected_row"] is None if row is None else b.fastener.condition == row
    assert b.source_record["catalog_digest"] == CATALOG_DIGEST


@pytest.mark.parametrize(
    ("mm", "inch", "condition"),
    [
        ("6.35", ".25", "CW1"),
        ("12.7", ".5", "CW1"),
        ("15.875", ".625", "CW1"),
        ("19.05", ".75", "CW2"),
        ("38.1", "1.5", "CW2"),
    ],
)
def test_si_exact_row_identity(mm: str, inch: str, condition: str) -> None:
    us, si = binding(inch), binding(mm, unit=Unit.MM)
    assert us.fastener == si.fastener
    assert si.fastener.condition == condition
    assert us.source_record["exact_diameter_mm"] == si.source_record["exact_diameter_mm"]


@pytest.mark.parametrize(
    ("condition", "strength"), [("AF", "65"), ("A", "75"), ("CW1", "100"), ("CW2", "85")]
)
@pytest.mark.parametrize("diameter", [".25", ".5", ".625", ".75", "1", "1.5"])
def test_intentional_conditions(condition: str, strength: str, diameter: str) -> None:
    b = binding(diameter, condition=condition)
    supported = (
        condition in {"AF", "A"}
        or (condition == "CW1" and Decimal(diameter) <= Decimal(".625"))
        or (condition == "CW2" and Decimal(diameter) >= Decimal(".75"))
    )
    assert b.fastener.fnt == (PhysicalQuantity.of(strength, Unit.KSI) if supported else None)


@pytest.mark.parametrize(
    ("thread", "d", "expected"),
    [
        ("EXCLUDED", ".5", "60"),
        ("INCLUDED", ".5", "50"),
        ("UNKNOWN", ".5", None),
        ("EXCLUDED", ".75", "51"),
        ("INCLUDED", ".75", "42.5"),
    ],
)
def test_native_fnv(thread: str, d: str, expected: str | None) -> None:
    b = binding(d, thread=thread)
    planes = cast(list[dict[str, Any]], b.source_record["shear_planes"])
    if expected is None:
        assert planes[0]["fnv"] is None
        assert not b.fastener.shear_plane_thread_statuses
    else:
        q = planes[0]["fnv"]
        assert PhysicalQuantity.of(q["value"], Unit.MPA).to(Unit.KSI).magnitude.quantize(
            Decimal(".00000001")
        ) == Decimal(expected)


def test_mixed_planes_are_independent() -> None:
    b = bind_f593_catalog(
        PhysicalQuantity.of(".5", Unit.IN),
        (
            CatalogPlane("PLANE_A", "EXCLUDED"),
            CatalogPlane("PLANE_B", "INCLUDED"),
            CatalogPlane("PLANE_C", "UNKNOWN"),
        ),
    )
    p = cast(list[dict[str, Any]], b.source_record["shear_planes"])
    assert [x["fnv_rule"] for x in p] == ["0.6 Fnt", "0.5 Fnt", "UNRESOLVED"]
    assert p[0]["fnv"] != p[1]["fnv"]
    assert p[2]["fnv"] is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("revision", "WRONG"),
        ("alloy_group", "1"),
        ("alloy_group", "3"),
        ("alloy", "304"),
        ("alloy", "321"),
        ("condition", "UNKNOWN"),
    ],
)
def test_unsupported_selectors_fail_closed(key: str, value: str) -> None:
    b = bind_f593_catalog(
        PhysicalQuantity.of(".5", Unit.IN), (CatalogPlane("P", "EXCLUDED"),), **{key: value}
    )
    assert b.fastener.fnt is None


@pytest.mark.parametrize(
    "corruption",
    [
        "missing",
        "duplicate",
        "overlap",
        "reverse",
        "fnt",
        "marking",
        "revision",
        "digest",
        "approval",
        "hardness",
        "diameter",
        "yield",
    ],
)
def test_catalog_corruption_fails_closed(corruption: str) -> None:
    data = dataset()
    row = data["rows"][0]
    if corruption == "missing":
        row.pop("design_fnt")
    elif corruption == "duplicate":
        data["rows"][3] = deepcopy(data["rows"][2])
    elif corruption == "overlap":
        data["rows"][3]["diameter_min"] = ".625"
    elif corruption == "reverse":
        row["tensile_max"] = "60"
    elif corruption == "fnt":
        row["design_fnt"] = "85"
    elif corruption == "marking":
        row["marking"] = "F593G"
    elif corruption == "revision":
        data["edition"] = "18"
    elif corruption == "approval":
        data["owner_approval"] = ""
    elif corruption == "hardness":
        row["hardness_basis"] = ""
    elif corruption == "diameter":
        row["diameter_max"] = ".01"
    elif corruption == "yield":
        row["yield_min"] = "-1"
    else:
        data["owner_approval"] += " changed"
    with pytest.raises(ValueError, match=r"F593|validation error"):
        validate_catalog(data)
    with pytest.raises(ValueError, match=r"F593|validation error"):
        validate_catalog(data, catalog_digest(data))


@pytest.mark.parametrize(
    "quantity", [PhysicalQuantity.of("1", Unit.KIP), PhysicalQuantity.of("0", Unit.IN)]
)
def test_bad_diameter(quantity: PhysicalQuantity) -> None:
    with pytest.raises(ValueError, match="positive length"):
        bind_f593_catalog(quantity, (CatalogPlane("P", "EXCLUDED"),))


@pytest.mark.parametrize(
    "planes",
    [
        (),
        (CatalogPlane("", "EXCLUDED"),),
        (CatalogPlane("P", "EXCLUDED"), CatalogPlane("P", "INCLUDED")),
        (CatalogPlane("P", cast(Any, "BAD")),),
    ],
)
def test_bad_physical_planes(planes: tuple[CatalogPlane, ...]) -> None:
    with pytest.raises(ValueError, match="unique physical"):
        bind_f593_catalog(PhysicalQuantity.of(".5", Unit.IN), planes)


def f4_body(
    *, si: bool = False, row_count: int = 2, thread: str = "EXCLUDED", diameter: str | None = None
) -> dict[str, Any]:
    body = owner_body(si=si, one_row=row_count == 1)
    body["fastener"] = {
        "kind": "CATALOG",
        "contract": "FASTENER-F4-RC1",
        "revision": CATALOG_ID,
        "shear_thread_status": thread,
    }
    if diameter is not None:
        body["legacy_request"]["bolt_diameter"]["value"] = diameter
        body["legacy_request"]["physical_connection"]["bolt_diameter"]["value"] = diameter
    return body


def design(body: dict[str, Any]) -> dict[str, Any]:
    r = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert r.status_code == 200, r.text
    return cast(dict[str, Any], r.json())


def supported(data: dict[str, Any]) -> list[dict[str, Any]]:
    i = data["native_design"]["automatic_group_mode_integration"]
    return [r for s in i["scenario_results"] for r in s["supported_results"]]


@pytest.mark.parametrize("thread", ["EXCLUDED", "INCLUDED", "UNKNOWN"])
@pytest.mark.parametrize("rows", [1, 2])
def test_design_executes_only_known_thread_planes(thread: str, rows: int) -> None:
    d = design(f4_body(thread=thread, row_count=rows))
    checks = [
        r
        for r in supported(d)
        if r["limit_state"] == "BOLT_SHEAR" and r["availability"] == "CALCULATED"
    ]
    assert len(checks) == (0 if thread == "UNKNOWN" else rows)
    assert d["fastener_source"]["fnt"] == {"value": "100", "unit": "ksi"}
    assert not any(
        w == "F593_TENSILE_SOURCE_DATA_PENDING" for w in d["native_design"]["preview"]["warnings"]
    )


def test_endpoint_authorization_selectors_and_validation() -> None:
    body = {
        "selection": {"kind": "CATALOG", "contract": "FASTENER-F4-RC1"},
        "diameter": {"value": ".5", "unit": "in"},
    }
    r = call("POST", "/api/v1/fasteners/resolve", body)
    assert r.status_code == 200
    assert r.json()["shear_planes"][0]["thread_status"] == "UNKNOWN"
    body["diameter"] = {"value": "1", "unit": "kip"}
    assert call("POST", "/api/v1/fasteners/resolve", body).status_code == 422
    with pytest.raises(ValueError, match="physical diameter"):
        fastener_source_record(
            CatalogFastenerSelectionDTO(kind="CATALOG", contract="FASTENER-F4-RC1")
        )
    controlled_catalog()


def test_report_source_and_worked_operands_remain_native() -> None:
    d = design(f4_body())
    rows = f593_source_rows(d["fastener_source"], "US_CUSTOMARY")
    assert "100-150 ksi" in str(rows)
    native = d["native_design"]
    bolt_rows = f593_bolt_rows(
        d["fastener_source"], native, native["preview"]["visualization"], "US_CUSTOMARY"
    )
    assert len(bolt_rows) == 2
    assert "lambda = 1" in str(bolt_rows)
    assert f593_source_rows(None, "SI") == []
    assert f593_bolt_rows({}, {}, {}, "SI") == []
    assert "Unresolved catalog row" in str(f593_source_rows(binding(".7").source_record, "SI"))
    signer = SnapshotSigner(b"F4-REPORT-TEST-32-BYTE-KEY-0000000")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=f4_body(), result=d, account_id="qa"
        ),
        account_id="qa",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    for mode in ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"):
        pdf = render_report_pdf(snapshot, ReportOptions(mode=cast(Any, mode)))
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
        assert "Catalog-resolved native bolt shear calculations" in text
        assert "F593G" in text
        assert "100-150 ksi" in text
        assert (snapshot.request, snapshot.result) == original


def test_no_catalog_strength_client_injection() -> None:
    body = f4_body()
    body["fastener"]["fnt"] = {"value": "999", "unit": "ksi"}
    assert call("POST", "/api/v1/frp-materials/multi-row/design-check", body).status_code == 422


@pytest.mark.parametrize("si", [False, True])
def test_non_bolt_engineering_exact_parity_and_owner_schedule(si: bool) -> None:
    before = design(owner_body(si=si))
    after = design(f4_body(si=si))
    old, new = before["native_design"], after["native_design"]
    assert old["automatic_demand_result"] == new["automatic_demand_result"]
    assert before["material_ledgers"] == after["material_ledgers"]
    assert before["material_issues"] == after["material_issues"]
    for key in (
        "visualization",
        "direct_physical_clearance",
        "direct_engineering_geometry",
        "direct_support_end_authority",
    ):
        assert old["preview"].get(key) == new["preview"].get(key)
    old_checks = {c["result_id"]: c for c in supported(before)}
    new_checks = {c["result_id"]: c for c in supported(after)}
    assert len(old_checks) == 5
    assert len(new_checks) == 7
    for check_id, original in old_checks.items():
        current = new_checks[check_id]
        for key in original:
            if key != "input_fingerprint":
                assert current[key] == original[key], (check_id, key)
    old_i, new_i = old["automatic_group_mode_integration"], new["automatic_group_mode_integration"]
    assert old_i["required_check_ids"] == new_i["required_check_ids"]
    assert len(new_i["required_check_ids"]) - len(new_checks) == 10
    assert old_i["unsupported_required_check_ids"] == new_i["unsupported_required_check_ids"]
    assert [
        x for x in old_i["incomplete_required_check_ids"] if not x.startswith("BOLT_")
    ] == new_i["incomplete_required_check_ids"]


def test_true_bolt_fail_retains_red_precedence() -> None:
    body = f4_body()
    body["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0][
        "force"
    ]["x"] = "-100"
    d = design(body)
    bolts = [r for r in supported(d) if r["limit_state"] == "BOLT_SHEAR"]
    assert any(Decimal(r["utilization"]) > 1 for r in bolts)
    assert d["overall_status"] == "FAIL"
    assert any(
        x.startswith("BOLT_SHEAR")
        for x in d["native_design"]["automatic_group_mode_integration"]["failed_check_ids"]
    )


def test_unit_invariant_native_bolt_results() -> None:
    us, si = design(f4_body()), design(f4_body(si=True))
    a, b = (
        [r for r in supported(us) if r["limit_state"] == "BOLT_SHEAR"],
        [r for r in supported(si) if r["limit_state"] == "BOLT_SHEAR"],
    )
    assert len(a) == len(b) == 2
    for first, second in zip(a, b, strict=True):
        for key in ("design_resistance", "equation_nominal_resistance", "numerical_comparison"):
            assert first[key] == second[key]
        assert (
            first["equation_trace"]["area_trace"]["area"]
            == second["equation_trace"]["area_trace"]["area"]
        )
        assert (
            first["equation_trace"]["nominal_stress"] == second["equation_trace"]["nominal_stress"]
        )


def test_report_single_row_and_unevaluated_bolt_paths() -> None:
    for thread in ("EXCLUDED", "UNKNOWN"):
        d = design(f4_body(row_count=1, thread=thread))
        n = d["native_design"]
        rows = f593_bolt_rows(
            d["fastener_source"], n, n["preview"]["visualization"], "US_CUSTOMARY"
        )
        assert len(rows) == (0 if thread == "UNKNOWN" else 1)


def test_catalog_binding_cannot_activate_another_family() -> None:
    body = f4_body()
    body["legacy_request"].pop("direct_finalization_contract_version")
    body["legacy_request"].pop("supporting_w_longitudinal_ends")
    r = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
    assert r.status_code == 422
    assert "requires the Direct finalization" in r.text
    legacy = map_multirow_request(
        MultiRowConnectionRequestDTO.model_validate(f4_body()["legacy_request"])
    )
    bound = bind_multirow_material(
        legacy, create_locked_ice_material_snapshot(), catalog_binding=binding(".5")
    )
    with pytest.raises(ValueError, match="trusted Direct catalog"):
        multirow_service._resolve(replace(bound, f593_catalog_binding=cast(Any, object())))
    with pytest.raises(ValueError, match="trusted Direct catalog"):
        multirow_service._resolve(
            replace(bound, direct_finalization_mode=False, supporting_w_longitudinal_ends=None)
        )
    # Defensive orchestration contract: an unknown shear plane also blocks the
    # combined equation, even when a future caller supplies an axis-tension case.
    # This does not activate that currently unsupported Direct physical action.
    unknown = replace(
        bound,
        f593_catalog_binding=binding(".5", thread="UNKNOWN"),
        bolt_axis_tension_required=True,
    )
    bundle = multirow_service._execution_bundle(unknown, multirow_service._resolve(unknown))
    combined = [
        check
        for check in bundle.checks
        if check.family is MultiRowCheckFamily.BOLT_COMBINED_TENSION_SHEAR
    ]
    assert len(combined) == 2
    assert all(check.plan_availability is PlanAvailability.INCOMPLETE_INPUT for check in combined)


def test_catalog_discovery_preserves_legacy_revision_and_publishes_controlled_data() -> None:
    r = call("GET", "/api/v1/fasteners/catalog")
    assert r.status_code == 200
    assert r.json()["controlled_datasets"] == [controlled_catalog().model_dump(mode="json")]
    assert r.json()["records"][0]["fnt"] is None
