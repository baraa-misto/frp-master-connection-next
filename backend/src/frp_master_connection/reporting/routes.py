"""Authenticated, bounded PDF export of a sealed native calculation response."""

import asyncio
import re
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.direct_qualification import qualification_snapshot_current
from frp_master_connection.api.direct_status import (
    direct_status_snapshot_current,
    input_direct_status,
)
from frp_master_connection.reporting.capture import _CALCULATION_FAMILIES
from frp_master_connection.reporting.pdf import (
    ReportingCoverageError,
    ReportOptions,
    render_report_pdf,
)
from frp_master_connection.reporting.snapshot import (
    ReportSnapshotStore,
    SnapshotError,
    SnapshotSigner,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver

MAX_CONCURRENT_REPORTS = 2
MAX_RENDER_SECONDS = 110.0
MAX_QUEUE_SECONDS = 5.0
MAX_PDF_BYTES = 20_000_000


class ExportRequest(BaseModel):
    """Only identification and presentation choices are accepted from the browser."""

    model_config = ConfigDict(extra="forbid", strict=True)

    report_snapshot: str | None = Field(default=None, min_length=80, max_length=10_000_000)
    report_handle: str | None = Field(default=None, min_length=32, max_length=80)
    paper: Literal["LETTER", "A4"] = "LETTER"
    display_units: Literal["INHERIT", "US_CUSTOMARY", "SI"] = "INHERIT"
    mode: Literal["ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"] = "ENGINEER_REPORT"
    project_name: str = Field(default="", max_length=150)
    project_number: str = Field(default="", max_length=80)
    connection_id: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=150)
    revision: str = Field(default="", max_length=40)
    prepared_by: str = Field(default="", max_length=120)
    checked_by: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def exactly_one_authority(self) -> ExportRequest:
        if (self.report_snapshot is None) == (self.report_handle is None):
            raise ValueError("Provide exactly one REPORT1 snapshot or handle")
        return self


class InputOnlyDraftRequest(BaseModel):
    """A current user input draft, with no claimed calculation authority."""

    model_config = ConfigDict(extra="forbid", strict=True)
    family: str = Field(min_length=1, max_length=80)
    draft: dict[str, Any]


class DecisionCurrencyRequest(BaseModel):
    """Revalidate existing server authority, never accept an engineering result."""

    model_config = ConfigDict(extra="forbid", strict=True)
    report_handle: str = Field(min_length=32, max_length=80)


def contains_sab2_contract(value: object) -> bool:
    """A SAB2 geometry wrapper cannot become a legacy report by nesting it."""
    if isinstance(value, dict):
        return value.get("contract") == "SHEAR01-DIRECT-SAB2-GEOMETRY-V1" or any(
            contains_sab2_contract(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(contains_sab2_contract(item) for item in value)
    return False


def _filename(request: ExportRequest) -> str:
    parts = (request.project_number, request.connection_id, request.revision)
    stem = "_".join(
        re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_\n\r")[:60]
        for value in parts
        if value.strip()
    )
    suffix = "_technical-audit" if request.mode == "FULL_TECHNICAL_AUDIT" else ""
    return f"{stem or 'connection-report'}{suffix}.pdf"


def build_report_router(
    signer: SnapshotSigner,
    store: ReportSnapshotStore,
    identity_resolver: TrustedIdentityResolver,
) -> APIRouter:
    """Bind export to the same server-selected identity as calculation routes."""

    router = APIRouter(prefix="/api/v1/reports")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)
    render_slots = asyncio.Semaphore(MAX_CONCURRENT_REPORTS)

    @router.post("/direct-decision-current")
    async def direct_decision_current(
        request: DecisionCurrencyRequest,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> JSONResponse:
        try:
            snapshot = signer.verify(
                store.get(request.report_handle), account_id=identity.account_id
            )
            if (
                snapshot.family != "multi-row"
                or snapshot.kind != "design"
                or "final_decision" not in snapshot.result
                or not direct_status_snapshot_current(snapshot.result, snapshot.request)
                or not qualification_snapshot_current(snapshot.result)
            ):
                raise SnapshotError(
                    "Direct design or qualification evidence is no longer current; run Design Check"
                )
        except SnapshotError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return JSONResponse(
            {"current": True, "snapshot_digest": snapshot.digest},
            headers={"Cache-Control": "no-store, private"},
        )

    @router.post("/input-only-snapshot")
    async def input_only_snapshot(
        request: InputOnlyDraftRequest,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> JSONResponse:
        if request.family not in _CALCULATION_FAMILIES:
            raise HTTPException(status_code=422, detail="Unknown REPORT1 connection family")
        if contains_sab2_contract(request.draft):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Use the authenticated Geometry and Constructability Review for SAB2 layouts."
                ),
            )
        try:
            token = signer.issue(
                family=request.family,
                kind="input_only",
                request={"client_draft": request.draft},
                result=input_direct_status(
                    {
                        "status": "INPUT_NOT_EVALUATED",
                        "reason": "Client draft captured without native validation or calculation",
                    },
                    {"client_draft": request.draft},
                )
                if request.family == "multi-row"
                else {
                    "status": "INPUT_NOT_EVALUATED",
                    "reason": "Client draft captured without native validation or calculation",
                },
                account_id=identity.account_id,
            )
            handle = store.put(token)
        except SnapshotError as error:
            raise HTTPException(status_code=413, detail=str(error)) from error
        return JSONResponse(
            {"report_handle": handle, "report_kind": "input_only"},
            status_code=201,
            headers={"Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff"},
        )

    @router.post("/export", response_class=Response)
    async def export_pdf(
        request: ExportRequest,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> Response:
        try:
            token = (
                store.get(request.report_handle)
                if request.report_handle is not None
                else cast(str, request.report_snapshot)
            )
            snapshot = signer.verify(token, account_id=identity.account_id)
            if snapshot.family == "direct-sab2-geometry":
                raise SnapshotError(
                    "Geometry-only layouts require the Geometry and Constructability Review export."
                )
            if snapshot.kind == "design" and not direct_status_snapshot_current(
                snapshot.result, snapshot.request
            ):
                raise SnapshotError("Direct decision does not match the current design snapshot")
            if not qualification_snapshot_current(snapshot.result):
                raise SnapshotError(
                    "Qualification record changed or became unavailable; run a fresh Design Check"
                )
        except SnapshotError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        options = ReportOptions(**request.model_dump(exclude={"report_snapshot", "report_handle"}))
        try:
            await asyncio.wait_for(render_slots.acquire(), timeout=MAX_QUEUE_SECONDS)
        except TimeoutError as error:
            raise HTTPException(
                status_code=503, detail="REPORT1 renderer is busy; try again"
            ) from error
        render_task = asyncio.create_task(asyncio.to_thread(render_report_pdf, snapshot, options))

        def release_slot(task: asyncio.Task[bytes]) -> None:
            # A timed-out or cancelled request may leave the worker finishing a page.
            # Keep its slot occupied until that work actually stops.
            if not task.cancelled():
                task.exception()
            render_slots.release()

        render_task.add_done_callback(release_slot)
        try:
            pdf = await asyncio.wait_for(asyncio.shield(render_task), timeout=MAX_RENDER_SECONDS)
        except ReportingCoverageError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except TimeoutError as error:
            raise HTTPException(status_code=503, detail="REPORT1 rendering timed out") from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="REPORT1 rendering failed") from error
        if len(pdf) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="REPORT1 PDF exceeds the export size limit")
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{_filename(request)}"',
                "Cache-Control": "no-store, private",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return router


__all__ = ("ExportRequest", "build_report_router")
