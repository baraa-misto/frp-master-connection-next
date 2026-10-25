"""Explicit reference inputs and real signed native Direct capture; never adoption evidence."""

import asyncio
from dataclasses import replace
from decimal import Decimal
from typing import Any

import httpx

from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_two_bolt import TwoBoltRequestDTO, geometry_response
from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    ActionCase,
    Alignment,
    CaseManifest,
    PairedActions,
    PhysicalIdentity,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest
from frp_master_connection.reporting.hyb1_review import request_digest
from frp_master_connection.reporting.hyb2_d2_service import ReviewSource
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_direct_two_bolt import sab2_body
from tests.application.test_hyb2_direct_status import source_actions
from tests.hyb1_fixtures import q


def support_source() -> ReviewSource:
    a = source_actions()
    a = replace(
        a,
        identity=replace(
            a.identity, connection="HYB2_D2_DIRECT_REVIEW", geometry=geometry_digest(R3Geometry())
        ),
        asd=(
            replace(
                a.asd[0],
                frame="DIRECT_P_SKETCH_V_CENTROID",
                source_id="RHM_INPUT_L48_L49_WITH_OWNER_R3_GEOMETRY",
                scenario_family="SAVED_SOURCE_REFERENCE_NOT_FULL_DESIGN_ENVELOPE",
            ),
        ),
    )
    return ReviewSource(a, R3Geometry())


def actual_native_source(
    *, overload: bool = False
) -> tuple[SnapshotSigner, ReviewSource, dict[str, Any]]:
    app = create_app()
    body = sab2_body(alignment="BRACE")
    if overload:
        for action in body["legacy"]["physical_connection"]["joint_assembly"]["member_end_actions"]:
            # Independent hand-defined overload retains this real native design route.
            for axis in ("x", "y", "z"):
                action["force"][axis] = str(Decimal(action["force"][axis]) * 1000)
    geometry = geometry_response(TwoBoltRequestDTO.model_validate(body))
    diagnostic = geometry["moment_diagnostic"]
    original_action = body["legacy"]["physical_connection"]["joint_assembly"]["member_end_actions"][
        0
    ]
    force = tuple(PhysicalQuantity.of(str(x), Unit.KIP) for x in diagnostic["F_global_kip"])
    moment = tuple(
        PhysicalQuantity.of(str(x), Unit.KIP_IN) for x in diagnostic["M_P_global_kip_in"]
    )
    reference = tuple(q(str(x), Unit.IN) for x in diagnostic["P_global_in"])
    centroid = tuple(q(str(x), Unit.IN) for x in diagnostic["G_global_in"])
    at_p = ActionCase(
        ActionBasis.LRFD,
        original_action["load_combination_id"],
        original_action["id"],
        "EXISTING_DIRECT_OWNER_FIXTURE",
        "GLOBAL",
        (reference[0], reference[1], reference[2]),
        (force[0], force[1], force[2], moment[0], moment[1], moment[2]),
    )
    at_g = at_p.transport((centroid[0], centroid[1], centroid[2]), frame="GLOBAL")

    async def send() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return await client.post("/api/v1/direct-two-bolt/design-check", json=body)

    response = asyncio.run(send())
    assert response.status_code == 200, response.text
    token = app.state.report_snapshot_store.get(response.json()["report_handle"])
    signer = app.state.report_signer
    snapshot = signer.verify(token, account_id="local-development-account")
    digest = request_digest(snapshot.request)
    identity = PhysicalIdentity(
        "local-development-account",
        "DIRECT_ACTUAL_D2_REVIEW",
        digest,
        digest,
        "ORIGINAL_EXPLICIT_LRFD_ONLY",
        Alignment.BRACE,
    )
    actions = PairedActions(
        identity,
        (at_g,),
        (),
        CaseManifest((at_g.case_id,), (), True, False, "Independent ASD cases not supplied"),
        (at_p,),
    )
    sealed = signer.issue(
        family=snapshot.family,
        kind=snapshot.kind,
        request=snapshot.request,
        result=snapshot.result,
        account_id=identity.account,
        input_provenance={**snapshot.input_provenance, "hyb1_lrfd_action_digest": at_g.digest},
    )
    return (
        signer,
        ReviewSource(actions, native_token=sealed, native_case_id=at_g.case_id),
        snapshot.result,
    )
