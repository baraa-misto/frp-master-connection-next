"""Actual PDF and destination audit of every registered calculation mode."""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.ssmc import illustrative_ssmc
from frp_master_connection.reporting.generic import (
    _native_equation_examples,
    _native_multirow_visuals,
)
from frp_master_connection.reporting.method_records import EXECUTED_METHODS, executed_records
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload


def _ssmc_payload() -> dict[str, Any]:
    return {
        "physical": illustrative_ssmc().model_dump(mode="json"),
        "action": {
            "basis": "FACTORED_LRFD",
            "combination_id": "REPORT1_AC1",
            "combination_source": "TEST_FIXTURE",
            "already_factored": True,
            "time_effect_category": "OTHER_LIVE",
            "time_effect_reference": "TEST_FIXTURE",
        },
        "single_lap": {
            "external_actions_at_faying_interface": True,
            "independent_normal_force": {"value": "0", "unit": "N"},
            "independent_out_of_plane_moment": {"value": "0", "unit": "N-mm"},
            "imposed_separation": False,
            "non_contact_gap": False,
            "friction_or_preload_credit": False,
            "miter_bearing_credit": False,
        },
    }


@pytest.mark.parametrize("family", tuple(FAMILIES))
@pytest.mark.parametrize("system", ["US_CUSTOMARY", "SI"])
def test_all_current_modes_export_navigable_real_pdfs_with_executed_method_adapters(
    family: str, system: str
) -> None:
    payload = (
        build_api_payload("J1-T")
        if family == "single-bolt"
        else _ssmc_payload()
        if family == "stair-stringer-miter"
        else native_payload(family)
    )
    path = (
        "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1"
        if family == "single-bolt"
        else "/api/v1/calculations/stair-stringer-miter/analytical-design-check"
        if family == "stair-stringer-miter"
        else f"/api/v1/calculations/{family}/design-check"
    )

    async def run() -> tuple[dict[str, Any], bytes]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()),
            base_url="http://test",
            timeout=120,
        ) as client:
            design = await client.post(path, json=payload)
            assert design.status_code == 200, design.text
            export_body: dict[str, str] = {"display_units": system}
            if family == "single-bolt":
                export_body["report_snapshot"] = design.json()["report_snapshot"]
            else:
                export_body["report_handle"] = design.headers["X-Report-Handle"]
            report = await client.post("/api/v1/reports/export", json=export_body)
            assert report.status_code == 200, report.text
            return design.json(), report.content

    native, data = asyncio.run(run())
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) > 2
    assert reader.outline
    destination_pages = []
    outline_titles = []

    def destinations(entries: list[Any]) -> list[Any]:
        return [
            item
            for entry in entries
            for item in (destinations(entry) if isinstance(entry, list) else [entry])
        ]

    for entry in destinations(reader.outline):
        page_number = reader.get_destination_page_number(entry)
        assert page_number is not None
        assert entry.title is not None
        destination_pages.append(page_number)
        outline_titles.append(entry.title)
        page_text = re.sub(r"\s+", "", reader.pages[page_number].extract_text() or "")
        assert re.sub(r"\s+", "", entry.title) in page_text
    assert len(set(destination_pages)) >= 3
    all_text = " ".join(page.extract_text() or "" for page in reader.pages)
    early_text = " ".join(page.extract_text() or "" for page in reader.pages[:12])
    assert "Canonical isometric" in all_text
    assert "Engineering inputs and design basis" in all_text
    assert "Engineering results" in all_text
    assert "Unevaluated checks and design limitations" in all_text
    assert "TECHNICAL AUDIT APPENDIX" in all_text
    native_result = native.get("result", native)
    displayed_length = "in" if system == "US_CUSTOMARY" else "mm"
    if family == "single-bolt":
        assert "native local boundary detail" in early_text
    elif family == "multi-row":
        assert "e1 " in early_text
        assert "hole d " in early_text
    elif family == "stair-stringer-miter":
        assert "Physical polygon face edge dimensions" in early_text
        assert re.search(rf"Polygon edge E1:\s*[-+\d.]+\s+{displayed_length}", all_text)
    else:
        assert "Physical component edge dimensions" in early_text
        assert re.search(
            rf"(?:Physical edge E1|Angle length|Web depth|Flange thickness):"
            rf"\s*[-+\d.]+\s+{displayed_length}",
            all_text,
        )
        if _native_multirow_visuals(native_result):
            assert "Physical bolt-row interface dimensions" in all_text
    for method in (*_native_equation_examples(native_result), *executed_records(native_result)):
        if method in EXECUTED_METHODS and family != "multi-row":
            assert EXECUTED_METHODS[method].title in outline_titles
        else:
            assert method in all_text
    assert "Native factor-stage substitution unavailable" not in all_text
