"Strict live Direct input bridge. No client result or engineering-approval upload."

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import replace
from decimal import Decimal
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.direct_qualification import qualification_snapshot_current
from frp_master_connection.api.direct_status import direct_status_snapshot_current
from frp_master_connection.api.direct_two_bolt import (
    TwoBoltRequestDTO,
    build_two_bolt_router,
    geometry_response,
    resolve_geometry,
)
from frp_master_connection.api.schemas import Identifier, QuantityDTO, _StrictModel
from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    ActionCase,
    Alignment,
    CaseManifest,
    PairedActions,
    PhysicalIdentity,
)
from frp_master_connection.application.hyb1_review import NativeCapture
from frp_master_connection.application.hyb2_d2 import SourceConditions, assess_d2
from frp_master_connection.application.hybrid_workflow import (
    FIELD_USE,
    LIMITS,
    declared_fit,
    source_scene,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, execute_r3, geometry_digest
from frp_master_connection.calculation.rhm_direct_reference import SOURCE_SHA256
from frp_master_connection.reporting.hyb1_review import (
    canonical_record,
    capture_signed_native,
    request_digest,
)
from frp_master_connection.reporting.hyb2_d2_service import ReviewSource, assessment_record
from frp_master_connection.reporting.hybrid_store import HybridStore
from frp_master_connection.reporting.hybrid_workflow import render_hybrid
from frp_master_connection.reporting.routes import (
    MAX_CONCURRENT_REPORTS,
    MAX_PDF_BYTES,
    MAX_QUEUE_SECONDS,
    MAX_RENDER_SECONDS,
)
from frp_master_connection.reporting.snapshot import SnapshotError
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


def quantity(q: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(q.value, q.unit)


def live_identifier(value: str) -> str:
    if "TEST_DOMAIN" in value or "SYNTHETIC" in value:
        raise ValueError("Synthetic engineering domains are not accepted by the live workflow.")
    return value


class R3Inputs(_StrictModel):
    vertical_bolt_pitch: QuantityDTO
    phi: StrictStr
    xb: QuantityDTO
    xc: QuantityDTO
    brace_near_v_edge_distance: QuantityDTO
    brace_leg: QuantityDTO
    column_flange: QuantityDTO
    brace_thickness: QuantityDTO
    column_thickness: QuantityDTO
    diameter: QuantityDTO
    hole: QuantityDTO

    @field_validator("phi")
    @classmethod
    def finite_angle(cls, value: str) -> str:
        return QuantityDTO.validate_decimal_string(value)

    def geometry(self) -> R3Geometry:
        return R3Geometry(
            vertical_bolt_pitch=quantity(self.vertical_bolt_pitch),
            phi=Decimal(self.phi),
            xb=quantity(self.xb),
            xc=quantity(self.xc),
            brace_near_v_edge_distance=quantity(self.brace_near_v_edge_distance),
            brace_leg=quantity(self.brace_leg),
            column_flange=quantity(self.column_flange),
            brace_thickness=quantity(self.brace_thickness),
            column_thickness=quantity(self.column_thickness),
            diameter=quantity(self.diameter),
            hole=quantity(self.hole),
        )


class ASDCase(_StrictModel):
    case_id: Identifier
    frame: Literal["DIRECT_P_SKETCH_V_CENTROID", "DIRECT_P_POSITIVE_N_CENTROID", "GLOBAL"]
    reference: tuple[QuantityDTO, QuantityDTO, QuantityDTO]
    components: tuple[
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
    ]

    @field_validator("case_id")
    @classmethod
    def no_synthetic_case(cls, value: str) -> str:
        return live_identifier(value)

    def case(self, basis: ActionBasis = ActionBasis.ASD) -> ActionCase:
        components = tuple(None if q is None else quantity(q) for q in self.components)
        frame = self.frame
        if frame == "DIRECT_P_POSITIVE_N_CENTROID" and all(
            q is not None and q.magnitude == 0 for q in components[2:]
        ):
            v = components[1]
            components = (
                components[0],
                None if v is None else PhysicalQuantity.of(-v.magnitude, v.unit),
                *components[2:],
            )
            frame = "DIRECT_P_SKETCH_V_CENTROID"
        return ActionCase(
            basis,
            self.case_id,
            "USER_DECLARED_" + basis.value,
            "CURRENT_CONNECTION",
            frame,
            cast(Any, tuple(quantity(q) for q in self.reference)),
            cast(Any, components),
        )


class Revision(_StrictModel):
    workspace_id: Identifier
    revision: Annotated[StrictInt, Field(ge=0, le=2_000_000_000)]

    @field_validator("workspace_id")
    @classmethod
    def no_synthetic_domain(cls, value: str) -> str:
        return live_identifier(value)


class HybridInputs(Revision):
    contract: Literal["HYB2-D3-P1-LIVE"]
    connection: Literal["RHM_R3", "CURRENT_NATIVE"]
    alignment: Literal["BRACE", "SUPPORT"]
    geometry: R3Inputs | None
    native_request: TwoBoltRequestDTO | None
    include_native_lrfd: StrictBool
    asd_cases: Annotated[tuple[ASDCase, ...], Field(max_length=8)]
    lrfd_cases: Annotated[tuple[ASDCase, ...], Field(max_length=8)] = ()
    source_profile: Literal["RHM_POLYESTER_100F_SF4", "UNMATCHED"]
    bearing_face: Literal["UNKNOWN", "DECLARED_STRAIGHT_FREE_EDGE"]
    washer_od: QuantityDTO | None
    native_edge_distance: QuantityDTO | None

    @model_validator(mode="after")
    def physical_scope(self) -> HybridInputs:
        if self.connection == "RHM_R3":
            if self.geometry is None or self.native_request is not None:
                raise ValueError(
                    "R3 inputs require one R3 geometry; native snapshots/results "
                    "cannot be grafted onto it."
                )
        elif (
            self.native_request is None
            or self.geometry is not None
            or self.native_request.alignment != self.alignment
        ):
            raise ValueError(
                "Current native inputs and selected alignment must describe one actual connection."
            )
        elif self.lrfd_cases:
            raise ValueError(
                "Native LRFD actions must remain in their original current native "
                "request, not a second incompatible action upload."
            )
        if self.washer_od is not None and quantity(self.washer_od).to(Unit.IN).magnitude <= 0:
            raise ValueError("Washer outside diameter must be positive.")
        if (
            self.native_edge_distance is not None
            and quantity(self.native_edge_distance).to(Unit.IN).magnitude < 0
        ):
            raise ValueError("Declared edge distance cannot be negative.")
        return self


class UnitConversion(_StrictModel):
    inputs: HybridInputs
    system: Literal["in", "mm"]


async def native_call(
    dto: TwoBoltRequestDTO,
    request: Request,
    identity: TrustedIdentity,
    endpoint: Callable[..., Awaitable[dict[str, Any]]],
) -> tuple[str, dict[str, Any]]:
    """Invoke the existing accepted route with the newly validated original inputs."""
    raw = json.dumps(dto.model_dump(mode="json")).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": raw, "more_body": False}

    inner = Request(dict(request.scope), receive=receive)
    response = await endpoint(dto, inner, identity)
    token = request.app.state.report_snapshot_store.get(response["report_handle"])
    snapshot = request.app.state.report_signer.verify(token, account_id=identity.account_id)
    return token, snapshot.result


def native_actions(
    dto: TwoBoltRequestDTO, geometry: dict[str, Any]
) -> tuple[ActionCase, ActionCase]:
    diagnostic = geometry["moment_diagnostic"]
    action = cast(Any, dto.legacy.physical_connection).joint_assembly.member_end_actions[0]
    ref = tuple(PhysicalQuantity.of(str(x), Unit.IN) for x in diagnostic["P_global_in"])
    force = tuple(PhysicalQuantity.of(str(x), Unit.KIP) for x in diagnostic["F_global_kip"])
    moment = tuple(
        PhysicalQuantity.of(str(x), Unit.KIP_IN) for x in diagnostic["M_P_global_kip_in"]
    )
    original = ActionCase(
        ActionBasis.LRFD,
        action.load_combination_id,
        action.id,
        "CURRENT_CONNECTION",
        "GLOBAL",
        cast(Any, ref),
        cast(Any, force + moment),
    )
    centroid = tuple(PhysicalQuantity.of(str(x), Unit.IN) for x in diagnostic["G_global_in"])
    return original, original.transport(cast(Any, centroid), frame="GLOBAL")


def build_hybrid_router(resolver: TrustedIdentityResolver) -> APIRouter:
    from fastapi.routing import APIRoute

    router = APIRouter(prefix="/api/v1/direct-hybrid", tags=["Current hybrid calculations"])
    dependency = build_trusted_identity_dependency(resolver)
    store = HybridStore()
    gate = asyncio.Semaphore(MAX_CONCURRENT_REPORTS)
    accepted = next(
        r
        for r in build_two_bolt_router(resolver).routes
        if isinstance(r, APIRoute) and r.path == "/api/v1/direct-two-bolt/design-check"
    )
    native_endpoint = cast(Callable[..., Awaitable[dict[str, Any]]], accepted.endpoint)

    @router.post("/units")
    async def convert_units(
        dto: UnitConversion, identity: Annotated[TrustedIdentity, Depends(dependency)]
    ) -> dict[str, Any]:
        data = dto.inputs.model_dump(mode="json")
        if data["geometry"] is None:
            raise HTTPException(
                422, "Use the current native workspace unit control for native geometry."
            )
        length = Unit.IN if dto.system == "in" else Unit.MM
        force = Unit.KIP if dto.system == "in" else Unit.N
        moment = Unit.KIP_IN if dto.system == "in" else Unit.N_MM

        def converted(value: dict[str, Any], target: Unit) -> dict[str, str]:
            q = PhysicalQuantity.of(value["value"], Unit(value["unit"])).to(target)
            return {"value": str(q.magnitude), "unit": target.value}

        for key, value in data["geometry"].items():
            if key != "phi":
                data["geometry"][key] = converted(value, length)
        for field in ["washer_od", "native_edge_distance"]:
            if data[field] is not None:
                data[field] = converted(data[field], length)
        for basis in ["asd_cases", "lrfd_cases"]:
            for case in data[basis]:
                case["reference"] = [converted(q, length) for q in case["reference"]]
                case["components"] = [
                    None if q is None else converted(q, force if i < 3 else moment)
                    for i, q in enumerate(case["components"])
                ]
        return data

    @router.post("/invalidate")
    async def invalidate(
        dto: Revision, identity: Annotated[TrustedIdentity, Depends(dependency)]
    ) -> dict[str, bool]:
        try:
            store.invalidate(identity.account_id, dto.workspace_id, dto.revision)
            return {"invalidated": True}
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error

    async def run(
        dto: HybridInputs, request: Request, identity: TrustedIdentity, *, evaluate: bool
    ) -> dict[str, Any]:
        account = identity.account_id
        inputs = dto.model_dump(mode="json")
        fingerprint = store.register(account, dto.workspace_id, dto.revision, inputs)
        g = None if dto.geometry is None else dto.geometry.geometry()
        native_geometry = None
        detail_checks: list[dict[str, Any]] = []
        scene = None
        if g is not None:
            model = execute_r3(
                geometry=g,
                axial=PhysicalQuantity.of(0, Unit.KIP),
                shear=PhysicalQuantity.of(0, Unit.KIP),
            )
            scene = source_scene(g, model, Alignment(dto.alignment))
        else:
            native_geometry = geometry_response(cast(TwoBoltRequestDTO, dto.native_request))
            _, original_preview = resolve_geometry(cast(TwoBoltRequestDTO, dto.native_request))
            detail_checks = [
                check
                for face in original_preview.get("direct_engineering_geometry", [])
                for check in face["checks"]
            ]
        preview = {
            "contract": "HYB2-D3-P1-LIVE",
            "revision": dto.revision,
            "fingerprint": fingerprint,
            "scene": scene,
            "native_geometry": native_geometry,
            "detailing_checks": detail_checks,
            "workflow_available": True,
            "structural_method_activation": False,
        }
        if not evaluate:
            return preview
        asd = tuple(case.case() for case in dto.asd_cases)
        lrfd = tuple(case.case(ActionBasis.LRFD) for case in dto.lrfd_cases)
        trace: tuple[ActionCase, ...] = ()
        token = ""
        native_result: dict[str, Any] = {"native_authority": "NOT_SUPPLIED_NO_RESULTS_INFERRED"}
        native_reason = (
            "ASCE evaluation unavailable for this arrangement; no native BRACE"
            " result is transferred."
        )
        native_request = None
        native_report_context = None
        if dto.include_native_lrfd and dto.native_request is not None:
            try:
                token, native_result = await native_call(
                    dto.native_request, request, identity, native_endpoint
                )
                original, case = native_actions(
                    dto.native_request, cast(dict[str, Any], native_geometry)
                )
                lrfd, trace = (case,), (original,)
                snapshot = request.app.state.report_signer.verify(token, account_id=account)
                native_request = snapshot.request
                native_report_context = {
                    "family": snapshot.family,
                    "request": snapshot.request,
                    "issued_at": snapshot.issued_at,
                    "digest": snapshot.digest,
                    "input_provenance": snapshot.input_provenance,
                }
                digest = request_digest(native_request)
            except HTTPException as error:
                native_reason = "Native calculation withheld: " + str(error.detail)
        if native_request is None:
            digest = geometry_digest(g) if g is not None else fingerprint
        material = SOURCE_SHA256 if g is not None else digest
        physical = PhysicalIdentity(
            account,
            "DIRECT_USER_HYBRID",
            digest,
            material,
            "USER_CURRENT_ACTIONS",
            Alignment(dto.alignment),
        )
        actions = PairedActions(
            physical,
            lrfd,
            asd,
            CaseManifest(
                tuple(c.case_id for c in lrfd),
                tuple(c.case_id for c in asd),
                False,
                False,
                "User-entered cases; completeness of project envelope not declared",
            ),
            trace,
        )
        if native_request is not None:
            snapshot = request.app.state.report_signer.verify(token, account_id=account)
            token = request.app.state.report_signer.issue(
                family=snapshot.family,
                kind=snapshot.kind,
                request=snapshot.request,
                result=snapshot.result,
                account_id=account,
                input_provenance={
                    **snapshot.input_provenance,
                    "hyb1_lrfd_action_digest": lrfd[0].digest,
                },
            )
            native = capture_signed_native(
                request.app.state.report_signer, token, actions, lrfd[0].case_id
            )
        else:
            payload = canonical_record(native_result)
            from hashlib import sha256

            native = NativeCapture(
                physical,
                actions.digest,
                payload,
                sha256(payload).hexdigest(),
                (),
                "NO_NATIVE_ASCE",
                "LIVE_INPUTS_NO_NATIVE_RESULTS_INFERRED",
            )
        conditions = (
            SourceConditions()
            if dto.source_profile == "RHM_POLYESTER_100F_SF4"
            else SourceConditions(resin="USER_UNMATCHED_PROFILE")
        )
        from datetime import UTC, datetime

        assessment = await asyncio.to_thread(
            assess_d2,
            actions,
            native,
            geometry=g,
            conditions=conditions,
            today=datetime.now(UTC).date(),
        )
        edge = (
            g.xb
            if g is not None
            else None
            if dto.native_edge_distance is None
            else quantity(dto.native_edge_distance)
        )
        assessment = declared_fit(
            assessment,
            edge=edge,
            washer=None if dto.washer_od is None else quantity(dto.washer_od),
            face=dto.bearing_face,
        )
        if (
            native_geometry is not None
            and native_geometry["geometry"]["aggregate_state"] == "DOES_NOT_FIT"
        ):
            assessment = replace(
                assessment,
                fit=replace(
                    assessment.fit,
                    state="NOT_FIT",
                    action="Current native constructability reports DOES_NOT_FIT. "
                    "Resolve the stated containment/seating failure before installation.",
                ),
            )
        assessment = replace(assessment, scope="LIVE_WORKFLOW_NO_STRUCTURAL_METHOD_ACTIVATION")
        source = ReviewSource(actions, geometry=g, conditions=conditions)
        record = assessment_record(assessment, source, native.immutable_payload)
        withheld = list(assessment.withheld)
        if native_request is None:
            withheld.append(
                (
                    "LRFD",
                    native_reason
                    if dto.include_native_lrfd
                    else "Independent LRFD case not supplied/enabled.",
                )
            )
        if g is None:
            withheld.append(
                (
                    "ASD",
                    (
                        "Current native geometry has no established R3 worksheet mapping; "
                        "no different source model is substituted."
                    ),
                )
            )
        record.update(
            title="Hybrid Connection Calculation Report",
            revision=dto.revision,
            fingerprint=fingerprint,
            workflow_available=True,
            structural_method_activation=False,
            inputs=inputs,
            native_report_context=native_report_context,
            detailing_checks=detail_checks,
            detailing_failures=[
                check for check in detail_checks if check.get("pass_fail") == "FAIL"
            ],
            field_use_provenance="OWNER_FIELD_USE_REPORTED",
            field_use_note=FIELD_USE,
            coverage_summary=LIMITS,
            data_provenance=(
                "USER_DECLARED; programmatic input hashes are not engineering certificates"
            ),
            requested_computation={
                "rhm_comparisons_requested": 7 * len(asd),
                "native_run_completed": native_request is not None,
                "rhm_comparisons_executed": sum(
                    1
                    for r in assessment.comparisons
                    if r.basis is ActionBasis.ASD and r.ratio is not None
                ),
                "native_checks_executed": sum(
                    1
                    for r in assessment.comparisons
                    if r.basis is ActionBasis.LRFD and r.ratio is not None
                ),
            },
            withheld=withheld,
        )
        handle = store.seal(account, dto.workspace_id, dto.revision, fingerprint, record)
        return dict(**preview, record=record, report_handle=handle)

    @router.post("/preview")
    async def preview(
        dto: HybridInputs,
        request: Request,
        identity: Annotated[TrustedIdentity, Depends(dependency)],
    ) -> dict[str, Any]:
        try:
            return await run(dto, request, identity, evaluate=False)
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/assess")
    async def assess(
        dto: HybridInputs,
        request: Request,
        identity: Annotated[TrustedIdentity, Depends(dependency)],
    ) -> dict[str, Any]:
        try:
            return await run(dto, request, identity, evaluate=True)
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    def current_record(handle: str, account: str) -> dict[str, Any]:
        record = store.export(handle, account)
        context = record["native_report_context"]
        if context is not None and (
            not direct_status_snapshot_current(record["native_result"], context["request"])
            or not qualification_snapshot_current(record["native_result"])
        ):
            raise SnapshotError("Native design or qualification evidence changed; recalculate.")
        return record

    @router.get("/reports/{handle}")
    async def report(
        handle: str,
        identity: Annotated[TrustedIdentity, Depends(dependency)],
        technical: bool = False,
    ) -> Response:
        try:
            record = current_record(handle, identity.account_id)
            await asyncio.wait_for(gate.acquire(), timeout=MAX_QUEUE_SECONDS)
            render_task = asyncio.create_task(
                asyncio.to_thread(render_hybrid, record, technical=technical)
            )

            def release_slot(task: asyncio.Task[bytes]) -> None:
                # A timed-out caller must not free a slot while its rendering
                # worker still runs. Match the existing report service contract.
                if not task.cancelled():
                    task.exception()
                gate.release()

            render_task.add_done_callback(release_slot)
            pdf = await asyncio.wait_for(asyncio.shield(render_task), timeout=MAX_RENDER_SECONDS)
            current_record(handle, identity.account_id)
            if len(pdf) > MAX_PDF_BYTES:
                raise HTTPException(503, "Hybrid report exceeds the configured PDF size limit.")
            return Response(
                pdf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": 'attachment; filename="hybrid-calculation'
                    + ("-audit" if technical else "")
                    + '.pdf"',
                    "Cache-Control": "no-store",
                },
            )
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error

        except TimeoutError as error:
            raise HTTPException(
                503, "Hybrid report service is busy. Retry current report export."
            ) from error

    @router.get("/records/{handle}")
    async def record_export(
        handle: str, identity: Annotated[TrustedIdentity, Depends(dependency)]
    ) -> Response:
        try:
            record = current_record(handle, identity.account_id)
            return Response(
                canonical_record(record),
                media_type="application/json",
                headers={
                    "Content-Disposition": 'attachment; filename="hybrid-calculation-record.json"',
                    "Cache-Control": "no-store",
                },
            )
        except SnapshotError as error:
            raise HTTPException(409, str(error)) from error

    return router
