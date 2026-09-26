"""Real-PDF regressions for REPORT1 section and contents destinations."""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any

import httpx
import pytest
from pypdf import PdfReader
from pypdf.generic import ArrayObject, Destination

from frp_master_connection.api.app import create_app
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload


def _direct_pdf(paper: str) -> PdfReader:
    async def run() -> bytes:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1",
                json=build_api_payload("J1-T"),
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_snapshot": design.json()["report_snapshot"], "paper": paper},
            )
            assert report.status_code == 200, report.text
            return report.content

    return PdfReader(io.BytesIO(asyncio.run(run())))


def _outline_entries(items: list[Any]) -> list[Destination]:
    result: list[Destination] = []
    for item in items:
        if isinstance(item, list):
            result.extend(_outline_entries(item))
        else:
            assert isinstance(item, Destination)
            result.append(item)
    return result


@pytest.mark.parametrize("paper", ["LETTER", "A4"])
def test_real_outline_and_contents_links_reach_distinct_named_sections(paper: str) -> None:
    reader = _direct_pdf(paper)
    entries = _outline_entries(reader.outline)
    assert len(entries) >= 10
    destinations = {entry.title: reader.get_destination_page_number(entry) for entry in entries}
    assert len(set(destinations.values())) >= 5
    for title, page_number in destinations.items():
        assert title is not None
        assert page_number is not None
        page_text = re.sub(r"\s+", " ", reader.pages[page_number].extract_text() or "")
        assert title in page_text, (title, page_number)

    links: list[tuple[int, int]] = []
    for source_page, page in enumerate(reader.pages):
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            if annotation.get("/Subtype") != "/Link":
                continue
            destination = annotation.get("/Dest") or (annotation.get("/A") or {}).get("/D")
            if isinstance(destination, ArrayObject):
                target = reader._get_page_number_by_indirect(destination[0])
                assert target is not None
                links.append((source_page, target))
    assert len(links) >= len(entries)
    assert len({target for _, target in links}) >= 5
    assert all(target < len(reader.pages) for _, target in links)


@pytest.mark.parametrize("paper", ["LETTER", "A4"])
def test_wi_support_contents_has_no_stranded_final_entry(paper: str) -> None:
    payload = native_payload("wi-beam-frp-support-moment")

    async def run() -> bytes:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/wi-beam-frp-support-moment/design-check",
                json=payload,
            )
            assert design.status_code == 200, design.text
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"], "paper": paper},
            )
            assert report.status_code == 200, report.text
            return report.content

    reader = PdfReader(io.BytesIO(asyncio.run(run())))
    assert "Contents" in (reader.pages[1].extract_text() or "")
    third_page = reader.pages[2].extract_text() or ""
    assert "Scope and connection model" in third_page
    appendix_page = next(
        index
        for index, page in enumerate(reader.pages[3:], start=3)
        if "Complete native results, traces, materials and limitations"
        in (page.extract_text() or "")
    )
    assert len((reader.pages[appendix_page - 1].extract_text() or "").strip()) >= 500
