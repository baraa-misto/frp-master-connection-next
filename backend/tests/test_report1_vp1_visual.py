"""Owner visual-signoff assertions against a real authenticated beam report."""

from __future__ import annotations

import asyncio
import io
from typing import Any, Literal

import httpx
import pytest
from pypdf import PdfReader
from reportlab.graphics.shapes import Circle, Line

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.generic import _box_figure, render_generic_pdf
from frp_master_connection.reporting.geometry import canonical_bolt_points, canonical_boxes
from frp_master_connection.reporting.pdf import ReportOptions, _reader_opening, _styles
from frp_master_connection.reporting.reader_views import colored_view, component_legend
from frp_master_connection.reporting.snapshot import ReportSnapshot
from tests.api.test_connector_materials import native_payload


@pytest.fixture(scope="module")
def beam_report() -> tuple[dict[str, Any], bytes]:
    async def run() -> tuple[dict[str, Any], bytes]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test", timeout=120
        ) as client:
            design = await client.post(
                "/api/v1/calculations/beam-concrete-paired-angle/design-check",
                json=native_payload("beam-concrete-paired-angle"),
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            assert report.status_code == 200, report.text
            return design.json(), report.content

    return asyncio.run(run())


def test_beam_native_paths_and_anchors_drive_visuals(
    beam_report: tuple[dict[str, Any], bytes],
) -> None:
    native, _ = beam_report
    visual = native["result"]["preview"]["visualization"]
    boxes = canonical_boxes(visual)
    hardware = canonical_bolt_points(visual)
    bolts = [item for item in hardware if item.role == "bolt"]
    anchors = [item for item in hardware if item.role == "anchor"]
    assert (len(bolts), len(anchors)) == (4, 8)
    assert all(item.start is not None and item.end is not None for item in hardware)
    assert all(item.diameter == 0.5 for item in hardware)
    assert all(item.washer_diameter == 1.0625 for item in anchors)
    assert bolts[0].start == tuple(
        float(value["value"]) for value in visual["common_beam_bolts"][0]["stack_start"]
    )
    assert anchors[0].start == (2.0, -0.5, -1.0)
    assert anchors[0].end == (2.0, 4.0, -1.0)

    drawing = colored_view(boxes, [], hardware, "isometric")
    assert sum(isinstance(shape, Line) for shape in drawing.contents) >= 2 * len(hardware)
    assert sum(isinstance(shape, Circle) for shape in drawing.contents) >= 2 * len(hardware)
    tags = component_legend(boxes, [], hardware)
    assert [tag for tag, _ in tags if tag.startswith("B")] == ["B1", "B2", "B3", "B4"]
    assert [tag for tag, _ in tags if tag.startswith("A")] == [f"A{i}" for i in range(1, 9)]
    assert "COMMON-R1-B1" not in str(tags)
    assert "POSITIVE_CLIP_ANGLE" not in str(tags)
    technical = _box_figure(boxes, hardware, "elevation", "in")
    assert not any(isinstance(shape, Line) and shape.x2 == 336 for shape in technical.contents)


def test_beam_pdf_foregrounds_actual_failure_and_keeps_audit(
    beam_report: tuple[dict[str, Any], bytes],
) -> None:
    native, pdf = beam_report
    reader = PdfReader(io.BytesIO(pdf))
    appendix = next(
        item
        for item in reader.outline
        if not isinstance(item, list)
        and item.title is not None
        and item.title.startswith("TECHNICAL AUDIT APPENDIX")
    )
    appendix_page = reader.get_destination_page_number(appendix)
    main = " ".join(page.extract_text() or "" for page in reader.pages[:appendix_page])
    audit = " ".join(page.extract_text() or "" for page in reader.pages[appendix_page:])
    assert "Connection bolt layout" in main
    assert "Support-side anchor layout" in main
    assert "B4" in main
    assert "A8" in main
    assert "GOVERNING" in main
    assert "First-row net tension" in main
    assert main.index("GOVERNING FAILURE — worked native calculation") < main.index(
        "Worked native eccentric bolt-group load assignment"
    )
    assert "FIRST_ROW:CONNECTED_MEMBER" in main
    assert "1.23457 (exceeds 1.0)" in main
    assert "Parameter" in main
    assert "Value" in main
    assert "Beam flange thickness" in main
    assert "Bolt gauge" in main
    assert "POSITIVE_CLIP_ANGLE:clip-angle-connected-leg-solid" in audit
    assert "FIRST_ROW:CONNECTED_MEMBER" in audit
    assert (
        native["result"]["preview"]["external_anchor_handoff"]["external_anchor_geometry"][
            "nominal_diameter"
        ]["value"]
        == "0.5"
    )
    assert reader.pages[1].get("/Annots")


def test_native_hardware_fallback_and_path_upgrade_keep_source_coordinates() -> None:
    visual: dict[str, Any] = {
        "web_bolt_diameter": 0.5,
        "flange_bolt_diameter": 0.625,
        "external_anchor_geometry": {},
        "hardware": [
            {"bolt_id": "F1", "group_id": "TOP_FLANGE", "center": {"x": 1, "y": 2, "z": 3}},
            {"anchor_id": "A1", "center": {"x": 4, "y": 5, "z": 6}},
            {"bolt_id": "B1", "center": {"x": 7, "y": 8, "z": 9}},
            {
                "bolt_id": "B1",
                "center": {"x": 7, "y": 8, "z": 9},
                "start": {"x": 7, "y": 7, "z": 9},
                "end": {"x": 7, "y": 9, "z": 9},
            },
        ],
    }
    hardware = canonical_bolt_points(visual)
    assert [(item.identity, item.diameter) for item in hardware] == [
        ("F1", 0.625),
        ("A1", 0.5),
        ("B1", 0.5),
    ]
    assert hardware[2].start == (7, 7, 9)
    assert hardware[2].end == (7, 9, 9)


@pytest.mark.parametrize(
    ("family", "kind", "status", "expected"),
    [
        (
            "beam-concrete-paired-angle",
            "design",
            "SOURCE_REQUIRED",
            "No anchor path geometry is available",
        ),
        (
            "wi-wall-moment",
            "input_only",
            "INPUT_NOT_EVALUATED",
            "SUBMITTED GEOMETRY — NOT VALIDATED",
        ),
        (
            "angle-column-two-leg-moment-base",
            "design",
            "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED",
            "No anchor path geometry is available",
        ),
    ],
)
def test_native_geometry_without_hardware_is_explicitly_limited(
    family: str, kind: Literal["design", "input_only"], status: str, expected: str
) -> None:
    visual = {
        "physical_boxes": [
            {
                "id": "Concrete foundation",
                "center_l_v_t": {"l": 0, "v": 0, "t": 0},
                "size_l_v_t": {"l": 4, "v": 4, "t": 4},
            }
        ]
    }
    boxes = canonical_boxes(visual)
    assert len(boxes) == 1
    assert _box_figure(boxes, [], "elevation", "in").contents
    snapshot = ReportSnapshot(
        family,
        kind,
        {},
        {"status": status, "preview": {"visualization": visual}},
        1_000,
        "0" * 64,
    )
    pdf = render_generic_pdf(snapshot, ReportOptions())
    content = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert expected in content
    assert "No local numerical check evaluated" in content


def test_direct_reader_explains_no_scheduled_numerical_check() -> None:
    snapshot = ReportSnapshot("single-bolt", "design", {}, {}, 1_000, "0" * 64)
    story = _reader_opening(snapshot, ReportOptions(), {}, "SOURCE_REQUIRED", "INHERIT", _styles())
    assert any(
        "It does not mean the connection is qualified" in getattr(item, "text", "")
        for item in story
    )
