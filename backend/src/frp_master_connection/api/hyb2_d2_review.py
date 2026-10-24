"""Explicit isolated app factory. Never mounted by the public application."""

from html import escape
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.reporting.hyb2_d2_review import render_d2
from frp_master_connection.reporting.hyb2_d2_service import D2ReviewService
from frp_master_connection.reporting.snapshot import SnapshotError
from frp_master_connection.security.identity import TrustedIdentity, TrustedIdentityResolver


class ReviewSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_key: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=1)


def create_d2_review_app(service: D2ReviewService, resolver: TrustedIdentityResolver) -> FastAPI:
    app = FastAPI(title="Direct D2 isolated engineering review - no public adoption")
    trusted = build_trusted_identity_dependency(resolver)

    @app.post("/review/assess")
    def assess(
        selection: ReviewSelection, identity: Annotated[TrustedIdentity, Depends(trusted)]
    ) -> dict[str, object]:
        try:
            handle, record = service.calculate(
                selection.case_key, selection.revision, identity.account_id
            )
        except (SnapshotError, ValueError) as error:
            raise HTTPException(409, str(error)) from error
        return {"report_handle": handle, "record": record}

    @app.get("/review/report/{handle}")
    def report(handle: str, identity: Annotated[TrustedIdentity, Depends(trusted)]) -> Response:
        try:
            record = service.export_record(handle, identity.account_id)
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error
        return Response(render_d2(record), media_type="application/pdf")

    @app.get("/review/view/{handle}", response_class=HTMLResponse)
    def view(handle: str, identity: Annotated[TrustedIdentity, Depends(trusted)]) -> str:
        try:
            record = service.export_record(handle, identity.account_id)
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error
        a = record["assessment"]
        rows = "".join(
            "<tr><td>"
            + escape(r["mechanism"])
            + "</td><td>"
            + escape(r["basis"])
            + "</td><td>"
            + escape(r["case_id"])
            + "</td><td>"
            + escape(str(r["ratio"]))
            + "</td><td>"
            + escape(r["outcome"])
            + "</td></tr>"
            for r in a["comparisons"]
        )
        html = (
            "<!doctype html><html lang='en'><meta charset='utf-8'><title>Direct hybrid "
            "review</title>"
            "<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}"
            "td,th{padding:9px;border-bottom:1px solid #ccc;text-align:left}</style>"
            "<h1>Direct hybrid engineering review</h1><p>Review only. No method "
            "adoption granted.</p>"
            "<h2 style='color:"
            + a["tone"]
            + "'>Evaluated checks: "
            + a["evaluated_outcome"]
            + " (scoped)</h2><p>Analytical coverage: "
            + a["coverage_state"]
            + "; Physical fit: "
            + a["fit"]["state"]
            + "; Qualification: "
            + a["qualification"]
            + ". Complete connection verification is not established.</p>"
            "<p>ASCE LRFD and RHM ASD comparisons retain independent action and "
            "resistance bases.</p>"
            "<table><tr><th>Check</th><th>Basis</th><th>Combination</th><th>Utilization</th>"
            "<th>Outcome</th></tr>"
            + rows
            + "</table><p><a href='/review/report/"
            + escape(handle, quote=True)
            + "'>Download current review PDF</a></p></html>"
        )
        return str(html)

    return app
