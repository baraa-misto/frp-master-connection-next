"""Real-PDF guards for physical dimension witnesses missing at eae3374."""

from __future__ import annotations

import asyncio
import io

import httpx
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from tests.api.test_connector_materials import native_payload
from tests.test_report1_ac1_navigation import _direct_pdf


def test_direct_physical_boundary_and_bolt_axis_views_show_native_witnesses() -> None:
    reader = _direct_pdf("LETTER")
    detail = " ".join(
        page.extract_text() or ""
        for page in reader.pages
        if "native local boundary detail" in (page.extract_text() or "")
    )
    for witness in (
        "reverse end 2 in",
        "forward e1 2 in",
        "e3 1.5 in",
        "e4 1.5 in",
        "t 0.375 in",
        "bolt d 0.5 in",
        "hole d 0.563 in",
        "Native through-bolt and ply stack",
        "UNDER_HEAD washer OD 1 in",
        "UNDER_NUT washer OD 1 in",
    ):
        assert witness in detail


def test_multirow_plan_witnesses_track_changed_native_pitch_and_gauge() -> None:
    payload = native_payload("multi-row")
    payload["pitch"] = {"value": "1.75", "unit": "in"}
    payload["gauge"] = {"value": "1.75", "unit": "in"}

    async def run() -> bytes:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            design = await client.post("/api/v1/calculations/multi-row/design-check", json=payload)
            assert design.status_code == 200, design.text
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            assert report.status_code == 200, report.text
            return report.content

    reader = PdfReader(io.BytesIO(asyncio.run(run())))
    drawing = " ".join((reader.pages[index].extract_text() or "") for index in (2, 3))
    for witness in (
        "e1 2 in",
        "p 1.75 in",
        "g 1.75 in",
        "s- 1.5 in",
        "s+ 1.5 in",
        "Bolt d 0.5 in; hole d 0.563 in",
        "LAYER-1: t 0.375 in",
        "B_R1_L1",
        "B_R2_L2",
    ):
        assert witness in drawing
