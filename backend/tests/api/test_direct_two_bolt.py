"""Authenticated route proof, fresh legacy parity, geometry-only and export guards."""

from __future__ import annotations

import asyncio
import io
import json
from copy import deepcopy
from decimal import Decimal, localcontext
from typing import Any

import httpx
import pytest
from pypdf import PdfReader
from tests.api.test_f593_f4 import design
from tests.api.test_mat1_routes import call
from tests.direct_mc1_fixtures import mc1_body, mc1_cases

from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_two_bolt import (
    CONTRACT,
    TwoBoltRequestDTO,
    geometry_response,
    moment_diagnostic,
)
from frp_master_connection.application.direct_two_bolt_geometry import GEOMETRY_BANNER


def sab2_body(material: dict[str, Any] | None = None, /, **changes: object) -> dict[str, Any]:
    accepted = deepcopy(mc1_body() if material is None else material)
    return {
        "contract": CONTRACT,
        "revision": "SAB2-TEST-CURRENT",
        "legacy": accepted["legacy_request"],
        "material_request": accepted,
        **changes,
    }


@pytest.mark.parametrize("case", list(mc1_cases()))
def test_identical_brace_route_freshly_preserves_every_mc1_design_field(case: str) -> None:
    material = mc1_cases()[case]
    expected = design(material)
    response = call("POST", "/api/v1/direct-two-bolt/design-check", sab2_body(material))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["structural_route"] == "B_FRESH_LEGACY_COMPATIBLE"
    assert data["result"] == expected
    assert len(data["report_handle"]) >= 32
    assert material == mc1_cases()[case]


@pytest.mark.parametrize(
    "changes",
    [
        {"alignment": "SUPPORT"},
        {"spacing": {"value": "2.25", "unit": "in"}},
        {
            "offset": {
                "support_longitudinal": {"value": "1", "unit": "in"},
                "support_transverse": {"value": "0", "unit": "in"},
            }
        },
    ],
)
def test_unmapped_layout_has_no_structural_result_and_cannot_use_design_route(
    changes: dict[str, Any],
) -> None:
    body = sab2_body(**changes)
    preview = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert data["structural_route"] == "C_GEOMETRY_ONLY"
    assert data["resistance_evaluated"] is False
    assert data["qualification_activated"] is False
    assert "result" not in data
    assert not data["visualization"]["automatic_bolt_demands"]
    result = call("POST", "/api/v1/direct-two-bolt/design-check", body)
    assert result.status_code == 422
    assert result.json()["detail"]["code"] == "SAB2_GEOMETRY_ONLY"
    for station in ("B1", "B2"):
        points = [p for p in data["geometry"]["face_points"] if p["station"] == station]
        assert len(points) == 2
        assert points[0]["global_center"] == points[1]["global_center"]


def test_incomplete_project_conditions_do_not_invent_design_defaults_for_geometry() -> None:
    body = sab2_body()
    body.pop("material_request")
    preview = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert preview.status_code == 200
    response = call("POST", "/api/v1/direct-two-bolt/design-check", body)
    assert response.status_code == 422
    assert "Materials and Project Conditions" in response.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract", "OTHER"),
        ("alignment", "ANY"),
        ("result", {"utilization": 0}),
        ("resistance", "1"),
        ("spacing", {"value": "0", "unit": "in"}),
        ("spacing", {"value": "1", "unit": "deg"}),
        ("angle_root_encroachment", {"value": "-.1", "unit": "in"}),
        ("support_root_encroachment", {"value": ".1", "unit": "in"}),
        (
            "offset",
            {
                "support_longitudinal": {"value": "0", "unit": "deg"},
                "support_transverse": {"value": "0", "unit": "in"},
            },
        ),
    ],
)
def test_new_transport_rejects_untrusted_results_and_invalid_geometry(
    field: str, value: object
) -> None:
    response = call("POST", "/api/v1/direct-two-bolt/preview", sab2_body(**{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize(("rows", "columns"), [(1, 1), (1, 2), (2, 2), (3, 1)])
def test_two_bolt_option_never_truncates_a_legacy_arrangement(rows: int, columns: int) -> None:
    body = sab2_body()
    body.pop("material_request")
    body["legacy"]["row_count"], body["legacy"]["bolts_per_row"] = rows, columns
    response = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert response.status_code == 422
    assert "exactly two collinear bolts" in response.text


def test_changed_material_envelope_and_old_endpoint_contract_grafts_are_rejected() -> None:
    body = sab2_body()
    body["material_request"]["legacy_request"] = deepcopy(body["legacy"])
    body["material_request"]["legacy_request"]["pitch"]["value"] = "2.1"
    assert call("POST", "/api/v1/direct-two-bolt/preview", body).status_code == 422
    for route in (
        "/api/v1/calculations/multi-row/preview",
        "/api/v1/calculations/multi-row/design-check",
        "/api/v1/frp-materials/multi-row/design-check",
    ):
        assert call("POST", route, sab2_body()).status_code == 422


def test_geometry_review_is_authenticated_current_and_every_page_has_its_banner() -> None:
    body = sab2_body(alignment="SUPPORT")

    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            preview = await client.post("/api/v1/direct-two-bolt/preview", json=body)
            assert preview.status_code == 200
            geometry = preview.json()
            handle = geometry["geometry_report_handle"]
            pdf = await client.post(
                "/api/v1/direct-two-bolt/geometry-review",
                json={
                    "report_handle": handle,
                    "current_request": body,
                },
            )
            assert pdf.status_code == 200, pdf.text
            reader = PdfReader(io.BytesIO(pdf.content))
            pages = reader.pages
            audit = json.loads(reader.attachments["SAB2_complete_technical_audit.json"][0])
            assert audit["request"] == TwoBoltRequestDTO.model_validate(body).model_dump(
                mode="json"
            )
            expected_geometry = {
                key: value for key, value in geometry.items() if key != "geometry_report_handle"
            }
            assert audit["geometry_snapshot"] == expected_geometry
            assert len(pages) >= 4
            assert all(GEOMETRY_BANNER in (page.extract_text() or "") for page in pages)
            text = " ".join(page.extract_text() or "" for page in pages)
            assert geometry["geometry_fingerprint"] in text
            assert "Structural design is not evaluated" in text
            assert "Technical audit appendix" in text
            assert "M_G = M_P + (P-G) x F" in text
            assert "material_request" in text
            assert Decimal(geometry["pair_input"]["spacing"]) == 2
            changed = deepcopy(body)
            changed["spacing"] = {"value": "2.25", "unit": "in"}
            assert (
                await client.post(
                    "/api/v1/direct-two-bolt/geometry-review",
                    json={
                        "report_handle": handle,
                        "current_request": changed,
                    },
                )
            ).status_code == 409
            assert (
                await client.post("/api/v1/reports/export", json={"report_handle": handle})
            ).status_code == 409
            assert (
                await client.post(
                    "/api/v1/direct-two-bolt/geometry-review",
                    json={
                        "report_handle": "z" * 64,
                        "current_request": body,
                    },
                )
            ).status_code == 409

    asyncio.run(run())


def test_display_extents_do_not_change_geometry_identity_or_physical_margins() -> None:
    body = sab2_body()
    first = geometry_response(TwoBoltRequestDTO.model_validate(body))
    body["legacy"]["physical_connection"]["view_extents"]["column_view_extent_below"]["value"] = (
        "99"
    )
    body["legacy"]["physical_connection"]["view_extents"]["column_view_extent_above"]["value"] = (
        "88"
    )
    body["material_request"]["legacy_request"] = deepcopy(body["legacy"])
    second = geometry_response(TwoBoltRequestDTO.model_validate(body))
    assert first["geometry_fingerprint"] == second["geometry_fingerprint"]
    assert first["geometry"] == second["geometry"]


def quantity(value: str) -> dict[str, str]:
    return {"value": value, "unit": "in"}


@pytest.mark.parametrize("leg", ["LEG_1", "LEG_2"])
def test_actual_selected_angle_faces_keep_proper_frames_and_explicit_method_limits(
    leg: str,
) -> None:
    body = sab2_body()
    body.pop("material_request")
    body["legacy"]["physical_connection"]["geometry_template"]["angle_connected_leg"] = leg
    response = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert leg in data["pair_input"]["faces"][0]["id"]
    limits = data["pair_input"]["faces"][0]["boundaries"]
    end = Decimal(next(b["limit"] for b in limits if b["id"].endswith("END_MAX")))
    coordinates = [
        Decimal(p["local_center"][0])
        for p in data["geometry"]["face_points"]
        if p["member_id"] == "member-a"
    ]
    assert abs(end - max(coordinates) - 3) < Decimal("1e-9")
    if leg == "LEG_2":
        assert not data["structural_eligible"]
        assert data["structural_route"] == "C_GEOMETRY_ONLY"
        assert call("POST", "/api/v1/direct-two-bolt/design-check", body).status_code == 422


@pytest.mark.parametrize("condition", ["UNSPECIFIED", "FINITE_BOTH_ENDS"])
def test_actual_support_ends_and_stated_root_envelopes_are_independent_of_view_crops(
    condition: str,
) -> None:
    body = sab2_body(
        angle_root_encroachment=quantity(".1"),
        support_root_encroachment=quantity(".1"),
        manufactured_geometry_source="Explicit geometry QA dimensions",
    )
    body.pop("material_request")
    body["legacy"]["supporting_w_longitudinal_ends"] = {
        "condition": condition,
        **(
            {"negative_end_distance": quantity("5"), "positive_end_distance": quantity("5")}
            if condition == "FINITE_BOTH_ENDS"
            else {}
        ),
    }
    response = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert response.status_code == 200, response.text
    data = response.json()
    support = data["pair_input"]["faces"][1]
    ends = [b for b in support["boundaries"] if b["role"] == "REAL_SUPPORT_MEMBER_END"]
    assert len(ends) == (2 if condition == "FINITE_BOTH_ENDS" else 0)
    assert (any("end condition is unspecified" in u for u in data["geometry"]["unknowns"])) == (
        condition == "UNSPECIFIED"
    )
    assert not any("root/fillet profile is unknown" in u for u in data["geometry"]["unknowns"])


def test_bounded_proposals_show_every_candidate_recheck_and_moment_shift_without_mutation() -> None:
    body = sab2_body(
        midpoint_search={
            "minimum": {
                "support_longitudinal": quantity("-1"),
                "support_transverse": quantity("-1"),
            },
            "maximum": {"support_longitudinal": quantity("1"), "support_transverse": quantity("1")},
        },
    )
    before = deepcopy(body)
    result = geometry_response(TwoBoltRequestDTO.model_validate(body))
    assert result["midpoint_regions"]
    assert body == before
    assert all(
        "candidate_geometry" in r and "moment_diagnostic" in r for r in result["midpoint_regions"]
    )
    for region in result["midpoint_regions"]:
        assert region["proposed_request_offset"] == region["proposed_offset"]
    body["offset"] = {
        "support_longitudinal": quantity(".125"),
        "support_transverse": quantity("-.25"),
    }
    moved = geometry_response(TwoBoltRequestDTO.model_validate(body))
    for region in moved["midpoint_regions"]:
        with localcontext() as context:
            context.prec = 64
            assert [Decimal(v) for v in region["proposed_request_offset"]] == [
                Decimal(region["proposed_offset"][0]) + Decimal(".125"),
                Decimal(region["proposed_offset"][1]) - Decimal(".25"),
            ]
    body["midpoint_search"]["minimum"]["support_longitudinal"] = quantity("10")
    body["midpoint_search"]["maximum"]["support_longitudinal"] = quantity("11")
    assert not geometry_response(TwoBoltRequestDTO.model_validate(body))["midpoint_regions"]


@pytest.mark.parametrize("hole", [".5625", ".563"])
def test_drawing_and_legacy_holes_remain_distinct_geometry_only_specifications(hole: str) -> None:
    body = sab2_body(hole_diameter=quantity(hole))
    data = geometry_response(TwoBoltRequestDTO.model_validate(body))
    assert data["structural_route"] == "C_GEOMETRY_ONLY"
    assert Decimal(data["pair_input"]["hole_radius"]) * 2 == Decimal(hole)
    assert all(
        Decimal(h["diameter"]) == Decimal(hole)
        for b in data["visualization"]["physical_bolts"]
        for h in b["display"]["holes"]
    )
    invalid = sab2_body(hole_diameter=quantity(".49"))
    assert call("POST", "/api/v1/direct-two-bolt/preview", invalid).status_code == 422


def test_explicit_cut_and_known_neighbor_override_other_positive_seating_margins() -> None:
    body = sab2_body(
        end_cuts=[
            {
                "member_id": "member-a",
                "polygon": [
                    [quantity("0"), quantity("-1.5")],
                    [quantity("8"), quantity("-1.5")],
                    [quantity("7.5"), quantity("2")],
                    [quantity("0"), quantity("2")],
                ],
                "source": "Explicit convex beveled Angle end QA",
            }
        ],
        neighbors=[
            {
                "id": "KNOWN-NEIGHBOR",
                "support_local_lower": [quantity("-100"), quantity("-100"), quantity("-100")],
                "support_local_upper": [quantity("100"), quantity("100"), quantity("100")],
                "source": "Explicit obstruction QA; not a guessed neighboring assembly",
            }
        ],
        hardware=[
            {
                "kind": "TOOL",
                "radius": quantity(".5"),
                "axial_start": quantity("1"),
                "axial_end": quantity("2"),
                "source": "Explicit cylindrical access envelope only",
            }
        ],
    )
    response = call("POST", "/api/v1/direct-two-bolt/preview", body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["geometry"]["washer_state"] != "DOES_NOT_FIT"
    assert data["geometry"]["obstruction_state"] == "DOES_NOT_FIT"
    assert data["geometry"]["aggregate_state"] == "DOES_NOT_FIT"
    assert data["structural_eligible"] is False
    assert any("beveled" in m["source"] for m in data["geometry"]["margins"])
    for field in ("end_cuts", "neighbors", "hardware"):
        invalid = deepcopy(body)
        invalid[field] *= 2
        assert call("POST", "/api/v1/direct-two-bolt/preview", invalid).status_code == 422
    invalid = deepcopy(body)
    invalid["end_cuts"][0]["member_id"] = "FOREIGN"
    assert call("POST", "/api/v1/direct-two-bolt/preview", invalid).status_code == 422
    for route in ("preview", "design-check"):
        invalid = sab2_body(
            hardware=[
                {
                    "kind": "TOOL",
                    "radius": {"value": "1", "unit": "deg"},
                    "axial_start": quantity("1"),
                    "axial_end": quantity("2"),
                    "source": "Invalid units QA",
                }
            ]
        )
        assert call("POST", "/api/v1/direct-two-bolt/" + route, invalid).status_code == 422


@pytest.mark.parametrize("kind", ["origins", "magnitude", "units"])
def test_unresolved_moment_diagnostic_does_not_invent_actions(kind: str) -> None:
    data = geometry_response(TwoBoltRequestDTO.model_validate(sab2_body()))
    visual = deepcopy(data["visualization"])
    arrows = visual["physical_connection"]["applied_action_directions"]
    if kind == "origins":
        visual["physical_connection"]["applied_action_directions"] = []
    elif kind == "magnitude":
        arrows[0]["signed_value"] = None
    else:
        arrows[0]["unit"] = None
    result = moment_diagnostic(visual, (Decimal(0), Decimal(0), Decimal(0)))
    assert result["state"] == "NOT_EVALUATED"


def test_new_request_size_limit_and_legacy_report_grafts_are_fail_closed() -> None:
    oversized = sab2_body()
    oversized["padding"] = "x" * 8_000_001
    assert call("POST", "/api/v1/direct-two-bolt/preview", oversized).status_code == 413
    for draft in (sab2_body(), {"nested": [0, {"contract": CONTRACT}]}):
        assert (
            call(
                "POST",
                "/api/v1/reports/input-only-snapshot",
                {
                    "family": "multi-row",
                    "draft": draft,
                },
            ).status_code
            == 422
        )
