"""REPORT1 distinguishes submitted values from accepted API defaults."""

from __future__ import annotations

import asyncio
import io
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel, field_validator
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.provenance import server_defaulted_fields
from tests.api_fixtures import build_api_payload


class _Child(BaseModel):
    entered: str
    server_default: str = "applied"


class _Body(BaseModel):
    members: list[_Child]
    optional: str | None = None

    @field_validator("members")
    @classmethod
    def add_server_member(cls, value: list[_Child]) -> list[_Child]:
        return [*value, _Child(entered="server-created")]


def _route() -> APIRoute:
    app = FastAPI()

    @app.post("/capture")
    async def capture(body: _Body) -> dict[str, bool]:
        return {"accepted": True}

    return next(route for route in app.routes if isinstance(route, APIRoute))


def test_server_default_inventory_tracks_nested_fields_and_added_list_entries() -> None:
    defaults = server_defaulted_fields(_route(), {"members": [{"entered": "user"}]})
    assert defaults == {
        "members[0].server_default": "applied",
        "members[1]": {"entered": "server-created", "server_default": "applied"},
        "optional": None,
    }
    assert server_defaulted_fields(_route(), {"members": "invalid"}) == {}
    assert server_defaulted_fields(object(), {}) == {}


def test_non_model_route_has_no_report_defaults() -> None:
    app = FastAPI()

    @app.get("/no-body")
    async def no_body() -> dict[str, bool]:
        return {"accepted": True}

    @app.post("/bare")
    async def bare(body: dict[str, str]) -> dict[str, bool]:
        return {"accepted": True}

    no_body_route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/no-body"
    )
    bare_route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/bare"
    )
    assert server_defaulted_fields(no_body_route, {}) == {}
    assert server_defaulted_fields(bare_route, {"x": "y"}) == {}


def test_route_without_a_body_annotation_has_no_report_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    route = _route()
    assert route.body_field is not None
    monkeypatch.setattr(route.body_field.field_info, "annotation", None)
    assert server_defaulted_fields(route, {"members": [{"entered": "user"}]}) == {}


def test_real_direct_pdf_prints_the_server_accepted_default_separate_from_request() -> None:
    async def run() -> tuple[dict[str, Any], bytes]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/single-bolt/evaluate", json=build_api_payload("J1-T")
            )
            assert design.status_code == 200
            export = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            assert export.status_code == 200
            return design.json(), export.content

    native, pdf_bytes = asyncio.run(run())
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    assert "Server default: geometry_template" in text
    assert "Explicit values sent to the native API" in text
    assert "Backend-resolved fields" in text
    assert "request.geometry_template" not in text
    assert native["calculation_fingerprint"] in text.replace("\n", "")
