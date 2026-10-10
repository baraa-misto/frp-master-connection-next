"""Independent boundary witnesses and catalog/thermal roles; no source activation."""

from __future__ import annotations

import io
import math
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
from pypdf import PdfReader
from tests.api.test_mat1_routes import call
from tests.application.test_direct_f1_safety import _direct_payload
from tests.direct_or2_fixtures import owner_body, owner_request

from frp_master_connection.api.mat1 import MaterialConditionsDTO, resolve_conditions
from frp_master_connection.api.multirow_mapping import (
    map_multirow_request,
    serialize_multirow_preview,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import preview_multirow_connection
from frp_master_connection.application.direct_physical import direct_face_clearance_provenance
from frp_master_connection.application.mat1_materials import (
    catalog_property_basis,
    predefined_catalog,
    property_ledger,
    temperature_applicability,
    thermal_gate,
)
from frp_master_connection.domain import ComponentMaterialKind
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

PREVIEW = "/api/v1/calculations/multi-row/preview"
DESIGN = "/api/v1/frp-materials/multi-row/design-check"


@pytest.mark.parametrize("si", [False, True])
def test_all_owner_faces_match_independent_edge_distance(si: bool) -> None:
    payload = owner_request(si=si)
    response = call("POST", PREVIEW, payload)
    assert response.status_code == 200
    data = response.json()
    records = data["direct_clearance_provenance"]
    assert len(records) == 4
    assert data["geometry_status"] == "VALID"
    scale = 25.4 if si else 1
    w_distances = []
    for record in records:
        assert record["valid"]
        point = tuple(float(x) for x in record["face_point_global"])
        distances = []
        for boundary in record["boundaries"]:
            a = tuple(float(x) for x in boundary["start_global"])
            b = tuple(float(x) for x in boundary["end_global"])
            ab = tuple(y - x for x, y in zip(a, b, strict=True))
            ap = tuple(y - x for x, y in zip(a, point, strict=True))
            cross = (
                ab[1] * ap[2] - ab[2] * ap[1],
                ab[2] * ap[0] - ab[0] * ap[2],
                ab[0] * ap[1] - ab[1] * ap[0],
            )
            distance = math.sqrt(sum(x * x for x in cross) / sum(x * x for x in ab))
            assert float(boundary["distance"]) == pytest.approx(distance, abs=1e-12)
            distances.append((distance, boundary["boundary_id"]))
        controlling = min(distances)
        assert float(record["center_to_boundary"]) == pytest.approx(controlling[0], abs=1e-12)
        assert record["controlling_boundary_id"] == controlling[1]
        assert float(record["chapter_8_minimum"]) == pytest.approx(0.75 * scale)
        assert float(record["hole_radius"]) == pytest.approx(0.2815 * scale)
        assert float(record["washer_radius"]) == pytest.approx(0.5 * scale)
        assert float(record["plane_offset"]) == 0
        if record["component_id"] == "member-b":
            w_distances.append(float(record["center_to_boundary"]) / scale)
    assert w_distances == pytest.approx([1.3376262658470832, 0.9981601717798214])
    changed = deepcopy(payload)
    changed["physical_connection"]["view_extents"] = {
        "brace_view_length": {"value": str(30 * scale), "unit": "mm" if si else "in"},
        "column_view_extent_above": {"value": str(30 * scale), "unit": "mm" if si else "in"},
        "column_view_extent_below": {"value": str(30 * scale), "unit": "mm" if si else "in"},
    }
    other = call("POST", PREVIEW, changed)
    assert other.status_code == 200, other.text
    assert other.json()["direct_clearance_provenance"] == records


def near_edge_request() -> dict[str, Any]:
    payload = owner_request()
    payload["unloaded_end_e1"]["value"] = "4.77"
    payload["physical_connection"]["geometry_template"]["bolt_to_brace_end_distance"]["value"] = (
        "4.77"
    )
    return payload


def test_deliberate_near_edge_is_visible_separate_from_spacing_and_footprints() -> None:
    preview = call("POST", PREVIEW, near_edge_request()).json()
    assert preview["geometry_status"] == "INVALID_GEOMETRY"
    assert not preview["design_check_ready"]
    record = next(r for r in preview["direct_clearance_provenance"] if not r["valid"])
    actual = float(record["center_to_boundary"])
    assert actual == pytest.approx(0.086047263146894, abs=0.0001)
    assert record["controlling_boundary_id"].endswith(":E1")
    assert actual != float(preview["visualization"]["pitch"]["value"])
    assert float(record["hole_ligament"]) == pytest.approx(actual - 0.2815)
    assert float(record["washer_ligament"]) == pytest.approx(actual - 0.5)
    assert float(record["validator_minimum"]) == 0.75


def test_provenance_keeps_existing_unresolved_face_and_hardware_issues() -> None:
    response = preview_multirow_connection(
        map_multirow_request(MultiRowConnectionRequestDTO.model_validate(owner_request()))
    )
    visual = response.visualization
    assert visual is not None
    assert visual.physical_connection is not None
    physical = visual.physical_connection
    for incomplete in (
        replace(response, visualization=None),
        replace(response, visualization=replace(visual, physical_connection=None)),
    ):
        assert "direct_clearance_provenance" not in serialize_multirow_preview(
            incomplete, include_direct_clearance=True
        ).model_dump(mode="json")
    bolt = visual.physical_bolts[0].display
    assert direct_face_clearance_provenance(physical, (replace(bolt, holes=()),)) == ()
    assert direct_face_clearance_provenance(physical, (replace(bolt, washers=()),)) == ()
    assert direct_face_clearance_provenance(replace(physical, interface_zones=()), (bolt,)) == ()
    assert direct_face_clearance_provenance(replace(physical, components=()), (bolt,)) == ()
    steel = replace(
        physical,
        components=tuple(
            replace(c, material_kind=ComponentMaterialKind.STEEL) for c in physical.components
        ),
    )
    assert direct_face_clearance_provenance(steel, (bolt,)) == ()


@pytest.mark.parametrize(
    ("sustained", "maximum", "tg", "expected"),
    [
        # F5 adds the ASCE 180°F baseline to the existing Tmax + 40°F requirement.
        ("70", "120", "160", "FAIL"),
        ("120", "120", "160", "FAIL"),
        ("70", "120", "159.999999", "FAIL"),
        ("70", "120", "160.000001", "FAIL"),
        ("70", "120", None, "NOT_CONFIRMED"),
        ("141", "150", "200", "PASS"),
    ],
)
def test_tg_boundary_is_separate_from_sustained_factor(
    sustained: str, maximum: str, tg: str | None, expected: str
) -> None:
    body = owner_body()
    raw = body["assignments"]["default_conditions"]
    raw["sustained_temperature"]["value"] = sustained
    raw["maximum_temperature"]["value"] = maximum
    raw["glass_transition_temperature"] = None if tg is None else {"value": tg, "unit": "degF"}
    conditions = resolve_conditions(MaterialConditionsDTO.model_validate(raw))
    ledger = property_ledger("member-a", predefined_catalog()[0], "bearing_strength_L", conditions)
    assert temperature_applicability(conditions) == expected
    response = call("POST", DESIGN, body)
    assert response.status_code == 200
    assert response.json()["material_sources"]["temperature_applicability"]["default"] == expected
    assert response.json()["design_check_performed"]
    assert ledger.ct == (
        Decimal(1) if Decimal(sustained) <= 90 else Decimal(".7") if sustained == "120" else None
    )
    if sustained == "120":
        assert (
            thermal_gate(conditions.sustained_f, conditions.maximum_f, conditions.tg_f)
            == "TEMPERATURE_FACTOR_BOUNDARY_REVIEW"
        )
    changed = replace(conditions, maximum_f=conditions.maximum_f + 1)
    assert (
        property_ledger("member-a", predefined_catalog()[0], "bearing_strength_L", changed).ct
        == ledger.ct
    )


def test_catalog_authority_and_numerical_checks_remain_honest() -> None:
    catalog = call("GET", "/api/v1/frp-materials/catalog").json()
    assert {r["property_basis"] for r in catalog["records"]} == {
        "DEVELOPMENT_NOMINAL",
        "ASCE_74_23_MINIMUM_CHARACTERISTIC",
    }
    assert {r["property_basis"] for r in catalog["records"][:2]} == {"DEVELOPMENT_NOMINAL"}
    assert (
        catalog_property_basis(
            replace(predefined_catalog()[0], source_kind="USER_SUPPLIED_SESSION_DATA")
        )
        == "USER_DEFINED"
    )
    fastener = call("GET", "/api/v1/fasteners/catalog").json()["records"][0]
    assert fastener["fnt"] is None
    assert "Catalog source-data gap" in fastener["source_requirement"]
    assert "supplier certification is not required" in fastener["source_requirement"]
    body = owner_body()
    result = call("POST", DESIGN, body).json()
    assert result["design_check_performed"]
    assert result["overall_status"] == "SOURCE_REQUIRED"
    assert result["material_sources"]["temperature_applicability"]["default"] == "NOT_CONFIRMED"
    assert result["material_sources"]["default"]["property_basis"] == "DEVELOPMENT_NOMINAL"
    assert "TG_REQUIRED" in result["material_issues"]


@pytest.mark.parametrize("case", ["owner", "near", "temperatures"])
def test_signed_report_reads_temperature_and_geometry_witnesses_without_recalculation(
    case: str,
) -> None:
    body = owner_body()
    if case == "near":
        body["legacy_request"] = near_edge_request()
        result = call("POST", PREVIEW, body["legacy_request"]).json()
    else:
        if case == "temperatures":
            body["assignments"]["default_conditions"]["maximum_temperature"]["value"] = "120"
        result = call("POST", DESIGN, body).json()
    signer = SnapshotSigner(b"DIRECT-OR2-F2-REPORT-ONLY-SIGNER-32")
    token = signer.issue(
        family="multi-row",
        kind="input_only" if case == "near" else "design",
        request=body,
        result=result,
        account_id="f2",
    )
    snapshot = signer.verify(token, account_id="f2")
    original = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions(mode="ENGINEER_REPORT"))
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages).split()
    )
    if case == "near":
        assert "Chapter 8 physical free-edge distance" in text
        assert "negative physical free side edge" in text
        assert ":E1" not in text
        assert "0.086" in text
    else:
        assert "Sustained operating material temperature" in text
        assert "Maximum expected material temperature" in text
        assert "Tg applicability" in text
        assert "NOT CONFIRMED" in text
    assert (snapshot.request, snapshot.result) == original
    if case == "near":
        # The legacy OR1 case has seven invalid faces; report evidence must fit
        # the existing ten-page gate without losing any face measurements.
        body["legacy_request"] = _direct_payload(physically_contained=False)
        result = call("POST", DESIGN, body).json()
        snapshot = signer.verify(
            signer.issue(
                family="multi-row", kind="design", request=body, result=result, account_id="f2"
            ),
            account_id="f2",
        )
        original = deepcopy((snapshot.request, snapshot.result))
        reader = PdfReader(
            io.BytesIO(render_report_pdf(snapshot, ReportOptions(mode="ENGINEER_REPORT")))
        )
        assert len(reader.pages) <= 10
        text = "".join("".join(p.extract_text() or "" for p in reader.pages).split())
        invalid = [
            item
            for item in result["native_design"]["preview"]["direct_clearance_provenance"]
            if not item["valid"]
        ]
        assert len(invalid) == 7
        # Exhaustive computational/native evidence belongs to the technical
        # appendix after F3, rather than the normal engineering explanation.
        audit_reader = PdfReader(
            io.BytesIO(render_report_pdf(snapshot, ReportOptions(mode="FULL_TECHNICAL_AUDIT")))
        )
        audit_text = "".join("".join(p.extract_text() or "" for p in audit_reader.pages).split())
        for witness in invalid:
            assert witness["controlling_boundary_id"] in audit_text
            for key in (
                "center_to_boundary",
                "validator_minimum",
                "chapter_8_minimum",
                "bolt_radius",
                "hole_radius",
                "washer_radius",
                "plane_offset",
            ):
                assert str(witness[key]) in audit_text
        assert (snapshot.request, snapshot.result) == original
