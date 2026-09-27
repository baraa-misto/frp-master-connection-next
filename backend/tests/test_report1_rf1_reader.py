"""Reader-facing RF1 assertions against native snapshots and actual PDF bytes."""

from __future__ import annotations

import asyncio
import io
import re

import httpx
import pytest
from pypdf import PdfReader
from reportlab.graphics.shapes import Circle, Line, Polygon
from reportlab.platypus import Flowable, Paragraph

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.generic import (
    _box_figure,
    _method_example_data,
    _schedules,
    render_generic_pdf,
)
from frp_master_connection.reporting.geometry import BoltPoint, BoxFigure, FaceFigure
from frp_master_connection.reporting.pdf import (
    ReportOptions,
    _add_linked_contents,
    _drawing,
    _font_setup,
    _reader_engineering_sections,
    _styles,
)
from frp_master_connection.reporting.reader_data import (
    collect_checks,
    governing,
    grouped_inputs,
    humanize,
    load_inputs,
    load_vectors,
    readable_value,
    short_number,
)
from frp_master_connection.reporting.reader_views import (
    colored_view,
    component_legend,
    miter_plate_faces,
    multirow_physical_geometry,
)
from frp_master_connection.reporting.snapshot import ReportSnapshot
from tests.api.test_connector_materials import native_payload


def test_reader_precision_and_grouping_leave_native_values_untouched() -> None:
    near = "1.00000004"
    assert short_number(near, ratio=True) == "1.00000004 (exceeds 1.0)"
    assert short_number("1", ratio=True) == "1 (equals 1.0)"
    assert short_number("0.99999996", ratio=True).endswith("below 1.0)")
    assert short_number("1.0000000001", ratio=True) == "1.0000000001 (exceeds 1.0)"
    assert short_number("not-a-number") == "not-a-number"
    assert short_number("Infinity") == "Infinity"
    assert readable_value({"value": "7206.11901672201", "unit": "N"}, "US_CUSTOMARY") == "1.62 kip"
    assert readable_value({"n": 1, "h": 2, "v": 3}) == "H = 2; V = 3; N = 1"
    assert humanize("QUALIFIED_ASCE_PRESCRIPTIVE") == "ASCE-prescriptive method qualified"
    request = {
        "beam_profile": {"dimensions": {"depth": {"value": "12.000000", "unit": "in"}}},
        "user_force_hvn": {
            "h": {"value": "2.00", "unit": "kip"},
            "v": {"value": "0", "unit": "kip"},
            "n": {"value": "-1", "unit": "kip"},
        },
        "user_moment_hvn": {"x": "0", "y": "2", "z": "0", "unit": "kip-in"},
    }
    original = repr(request)
    groups = grouped_inputs(request, "US_CUSTOMARY")
    assert ("beam profile / dimensions / depth", "12 in") in groups["Connected member"]
    assert load_vectors(request, "US_CUSTOMARY") == [
        ("user force hvn", "2 kip", "0 kip", "-1 kip"),
        ("user moment hvn", "0 kip-in", "2 kip-in", "0 kip-in"),
    ]
    assert repr(request) == original
    assert load_inputs(request, "US_CUSTOMARY") == groups["Loads and moments"]
    assert collect_checks({"check_id": "C1", "utilization": "unavailable"})[0].utilization is None


def test_colored_views_use_native_vertices_and_stable_nonduplicated_ids() -> None:
    first = BoxFigure(
        "CONNECTED_BEAM",
        tuple((x, y, z) for x in (-2.0, 2.0) for y in (-1.0, 1.0) for z in (-0.5, 0.5)),
    )
    face = FaceFigure("MITER_PLATE", ((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0)))
    bolts = [BoltPoint("B1", (0.0, 0.0, 0.0))]
    legend = component_legend([first, first], [face], bolts)
    assert [identity for identity, _ in legend] == ["M1", "C1", "B1"]
    assert "2 parts" in legend[0][1]
    assert "CONNECTED_BEAM" not in str(legend)
    assert component_legend([BoxFigure("BOLT_SHAFT", first.vertices)], [], [])[0] == (
        "B1",
        "Bolt shaft",
    )
    with pytest.raises(ValueError, match="native physical geometry"):
        colored_view([], [], [], "plan")
    with pytest.raises(ValueError, match="Unknown report camera"):
        colored_view([first], [], [], "unknown")
    for camera in ("isometric", "elevation", "plan"):
        view = colored_view([first], [face], bolts, camera)
        assert sum(isinstance(item, Polygon) for item in view.contents) >= 3
        assert sum(isinstance(item, Circle) for item in view.contents) == 1
        repeated = colored_view([first], [face], bolts, camera)
        assert [item.points for item in view.contents if isinstance(item, Polygon)] == [
            item.points for item in repeated.contents if isinstance(item, Polygon)
        ]
    moved = BoxFigure(first.identity, tuple((x * 2, y, z) for x, y, z in first.vertices))
    before = colored_view([first], [], bolts, "plan")
    after = colored_view([moved], [], bolts, "plan")
    assert [shape.points for shape in before.contents if isinstance(shape, Polygon)] != [
        shape.points for shape in after.contents if isinstance(shape, Polygon)
    ]
    degenerate = FaceFigure("DETAIL", ((0.0, 0.0, 0.0),))
    degenerate_view = colored_view([], [degenerate], [], "plan")
    assert not any(isinstance(shape, Polygon) for shape in degenerate_view.contents)
    load_view = colored_view(
        [first], [], bolts, "isometric", action_force=(0.0, -4.0, 0.0), action_reference=(0, 0, 0)
    )
    assert any(isinstance(shape, Line) for shape in load_view.contents)
    assert any(
        getattr(shape, "text", "").startswith("Applied force") for shape in load_view.contents
    )
    zero_projection = colored_view(
        [first], [], bolts, "plan", action_force=(0.0, 0.0, 4.0), action_reference=(0, 0, 0)
    )
    baseline_lines = sum(
        isinstance(shape, Line) for shape in colored_view([first], [], bolts, "plan").contents
    )
    assert sum(isinstance(shape, Line) for shape in zero_projection.contents) == baseline_lines
    missing_reference = colored_view([first], [], bolts, "plan", action_force=(1, 0, 0))
    assert sum(isinstance(shape, Line) for shape in missing_reference.contents) == baseline_lines


def test_multirow_view_uses_native_boundary_layers_and_bolt_centers() -> None:
    visual = {
        "boundary": [0, 10, -2, 2],
        "layers": [{"thickness": {"value": "0.5", "unit": "in"}}],
        "bolts": [{"bolt_id": "B_R1_L1", "x": 3, "y": 1}],
    }
    boxes, bolts = multirow_physical_geometry(visual)
    assert boxes[0].vertices[0] == (0.0, -2.0, -0.25)
    assert bolts == [BoltPoint("B_R1_L1", (3.0, 1.0, 0.0))]
    plate = miter_plate_faces(
        {
            "polygon": {"boundary": [[0, 0], [2, 0], [2, 1], [0, 1]]},
            "plate_y_interval": [-0.5, 0],
        }
    )
    assert plate[0].identity == "MITER_WEB_PLATE"
    assert plate[0].vertices[0] == (0.0, -0.5, 0.0)
    assert plate[1].vertices[-1] == (0.0, 0.0, 1.0)


def test_technical_dimension_views_and_empty_audit_schedule_remain_available() -> None:
    box = BoxFigure(
        "CONNECTED_MEMBER",
        tuple((x, y, z) for x in (0.0, 2.0) for y in (0.0, 1.0) for z in (0.0, 1.0)),
    )
    bolt = BoltPoint("B1", (1.0, 0.5, 0.5))
    for camera in ("isometric", "elevation", "plan"):
        figure = _box_figure([box], [bolt], camera, "in")
        assert any(isinstance(item, Line) for item in figure.contents)
    _font_setup()
    styles = _styles()
    story: list[Flowable] = []
    _schedules(story, "Empty native section", [], styles)
    assert any(
        isinstance(item, Paragraph) and "No native records" in item.getPlainText() for item in story
    )


def test_worked_method_examples_preserve_each_native_trace_shape() -> None:
    cases = (
        (
            "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1",
            {"components": [{"id": "C1"}], "equilibrium": {"ok": True}},
            "first_component",
        ),
        (
            "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1",
            {"request": {"id": "A1"}},
            "request",
        ),
        (
            "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1",
            {"solution": {"bolts": [{"id": "B1"}]}},
            "first_bolt",
        ),
        (
            "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1",
            {"critical_sections": [{"id": "S1"}], "tension_strength": "native"},
            "first_critical_section",
        ),
        (
            "DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1",
            {"rows": [{"id": "R1"}], "shafts": [{"id": "H1"}]},
            "first_row",
        ),
    )
    for method, native, retained_key in cases:
        selected = _method_example_data(method, native)
        assert selected[retained_key]
    assert _method_example_data("OTHER_NATIVE_METHOD", {"native": "intact"}) == {"native": "intact"}


def test_direct_projection_and_sparse_reader_guards_keep_native_geometry() -> None:
    primitive = {
        "kind": "BOX",
        "physical_element_id": "M1",
        "parameters": [
            {"name": "x_start", "value": "0"},
            {"name": "x_end", "value": "2"},
            {"name": "min_y", "value": "0"},
            {"name": "max_y", "value": "1"},
            {"name": "min_z", "value": "0"},
            {"name": "max_z", "value": "1"},
        ],
        "center": {"x": "0", "y": "0", "z": "0"},
        "x_axis": {"x": "1", "y": "0", "z": "0"},
        "y_axis": {"x": "0", "y": "1", "z": "0"},
        "z_axis": {"x": "0", "y": "0", "z": "1"},
    }
    visual = {
        "primitives": [primitive, primitive],
        "bolt": {
            "stack_start": {"x": "0", "y": "0", "z": "0"},
            "stack_end": {"x": "0", "y": "0", "z": "1"},
            "center": {"x": "0", "y": "0", "z": "0.5"},
            "bolt_diameter": "0.5",
            "bolt_location_id": "B1",
        },
        "length_unit": "in",
    }
    for camera in ("isometric", "plan", "elevation"):
        drawing = _drawing(visual, camera)
        assert any(isinstance(item, Line) for item in drawing.contents)
    _font_setup()
    styles = _styles()
    story: list[Flowable] = []
    _add_linked_contents(story, styles)
    assert not story
    snapshot = ReportSnapshot("single-bolt", "design", {}, {}, 1_000, "0" * 64)
    sections = _reader_engineering_sections(snapshot, {}, "US_CUSTOMARY", styles)
    assert any(
        isinstance(item, Paragraph) and "No native numerical check" in item.getPlainText()
        for item in sections
    )


def test_input_only_validation_issues_are_prominent_and_do_not_claim_results() -> None:
    snapshot = ReportSnapshot(
        "beam-concrete-paired-angle",
        "input_only",
        {},
        {
            "status": "INPUT_NOT_EVALUATED",
            "validation_issues": [
                {"loc": ["beam_depth"], "msg": "Required value missing"},
                "unstructured native issue",
            ],
        },
        1_000,
        "0" * 64,
    )
    pdf = render_generic_pdf(snapshot, ReportOptions())
    pages = PdfReader(io.BytesIO(pdf)).pages
    first_page = pages[0].extract_text()
    assert "Validation / calculation" in first_page
    assert "Required value missing" in first_page
    assert "design not evaluated" in first_page.lower()
    assert "Validation issue 1" in " ".join(page.extract_text() for page in pages)


@pytest.mark.parametrize("paper", ["LETTER", "A4"])
def test_beam_concrete_reader_summary_matches_native_and_audit_remains_complete(
    paper: str,
) -> None:
    payload = native_payload("beam-concrete-paired-angle")

    async def run() -> tuple[dict[str, object], bytes]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test", timeout=120
        ) as client:
            design = await client.post(
                "/api/v1/calculations/beam-concrete-paired-angle/design-check", json=payload
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"], "paper": paper},
            )
            assert report.status_code == 200, report.text
            return design.json(), report.content

    native, data = asyncio.run(run())
    reader = PdfReader(io.BytesIO(data))
    appendix = next(
        entry
        for entry in reader.outline
        if not isinstance(entry, list)
        and isinstance(entry.title, str)
        and entry.title.startswith("TECHNICAL AUDIT APPENDIX")
    )
    appendix_page = reader.get_destination_page_number(appendix)
    assert appendix_page is not None
    assert 5 < appendix_page < 25
    main = " ".join(page.extract_text() or "" for page in reader.pages[:appendix_page])
    audit = " ".join(page.extract_text() or "" for page in reader.pages[appendix_page:])
    native_result = native["result"]
    assert isinstance(native_result, dict)
    checks = collect_checks(native_result)
    critical = governing(checks)
    assert critical is not None
    assert critical.identity == "FIRST_ROW:CONNECTED_MEMBER"
    assert readable_value(critical.demand, "US_CUSTOMARY") in main
    assert readable_value(critical.resistance, "US_CUSTOMARY") in main
    assert short_number(critical.utilization, ratio=True) in main
    assert "7 scheduled required checks unevaluated" in main
    assert "external resistance is inferred" in main
    assert "Load path at wall reference" in main
    assert "V = -4 kip" in main
    assert "H = 16 kip-in" in main
    assert (
        sum(
            entry.title == "4 Submitted loads and moments"
            for entry in reader.outline
            if not isinstance(entry, list)
        )
        == 1
    )
    assert "connection detail crop" in main
    assert not re.search(r"\brequest\.[A-Za-z_]", main)
    assert not re.search(r"\bresult\.[A-Za-z_]", main)
    assert "Identical native record at" not in main
    assert "{'" not in main
    assert "request.beam_profile" in audit
    assert "result.preview" in audit
    assert "FIRST_ROW:CONNECTED_MEMBER" in audit
    assert reader.pages[1].get("/Annots")
