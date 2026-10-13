"""Isolated HYB1 executed references and actual Direct fixtures; no live service changes."""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import platform
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]

import httpx
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_two_bolt import TwoBoltRequestDTO, geometry_response
from frp_master_connection.application.hyb1_contract import (
    ActionBasis, ActionCase, Alignment, CaseManifest, PairedActions, PhysicalIdentity,
)
from frp_master_connection.application.hyb1_review import (
    NativeCapture, SupplementalSet, assess_hybrid, calculate_reference_cases,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_reference import ReferenceStream
from frp_master_connection.calculation.rhm_workbook_case import execute_workbook_case
from frp_master_connection.reporting.hyb1_review import (
    TITLE, canonical_record, capture_signed_native, render_hyb1_review, request_digest, review_record,
)
from tests.api.test_direct_two_bolt import sab2_body
from tests.hyb1_fixtures import case, complete_fixture, paired, q


def generate_reference_cases() -> dict[str,tuple]:
    output={}
    for name,stream,scale in (
        ("rhm-corrected-reference",ReferenceStream.CORRECTED_REFERENCE,"1"),
        ("rhm-historical-replication",ReferenceStream.HISTORICAL_REPLICATION,"1"),
        ("rhm-overload-reference",ReferenceStream.CORRECTED_REFERENCE,"5"),
    ):
        action=case(ActionBasis.ASD,"RHM-SAVED",str(Decimal("1.048")*Decimal(scale)),
                    str(Decimal(".566")*Decimal(scale)))
        actions=replace(paired("HYB1_WORKBOOK_REFERENCE"),lrfd=(),asd=(action,),
                        manifest=CaseManifest((),("RHM-SAVED",),False,True,"DECLARED_WORKBOOK_REFERENCE_ONLY"))
        supplemental=calculate_reference_cases(actions)
        payload=b'{"scope":"WORKBOOK_REFERENCE_NO_NATIVE_ASCE"}'
        native=NativeCapture(actions.identity,actions.digest,payload,sha256(payload).hexdigest(),(),
                             "NO_NATIVE_ASCE","WORKBOOK_REFERENCE_ONLY")
        workbook=execute_workbook_case(stream=stream,shear=action.components[0],axial=action.components[1])
        output[name]=(actions,assess_hybrid(actions,native,supplemental),(workbook,))
    actions=paired();native,supplemental=complete_fixture(actions)
    output["synthetic-complete-domain-TEST-ONLY"]=(actions,assess_hybrid(actions,native,supplemental),())
    return output


async def generate_actual_cases(bodies: dict[Alignment,dict]) -> dict[str,tuple]:
    app=create_app();output={}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver") as client:
        for alignment in Alignment:
            body=bodies[alignment]
            geometry=geometry_response(TwoBoltRequestDTO.model_validate(body))
            diagnostic=geometry["moment_diagnostic"]
            reference=tuple(PhysicalQuantity.of(str(x),Unit.IN) for x in diagnostic["P_global_in"])
            components=tuple(PhysicalQuantity.of(str(x),Unit.KIP) for x in diagnostic["F_global_kip"])+tuple(
                PhysicalQuantity.of(str(x),Unit.KIP_IN) for x in diagnostic["M_P_global_kip_in"])
            source_action=body["legacy"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]
            action=ActionCase(ActionBasis.LRFD,source_action["load_combination_id"],source_action["id"],
                              "EXISTING_DIRECT_OWNER_FIXTURE","GLOBAL",reference,components)
            at_g=action.transport(tuple(q(str(x),Unit.IN) for x in diagnostic["G_global_in"]),frame="GLOBAL")
            assert all(abs(value.to(Unit.KIP_IN).magnitude-Decimal(str(expected)))<Decimal("1e-24")
                       for value,expected in zip(at_g.components[3:],diagnostic["M_G_global_kip_in"],strict=True))
            response=await client.post("/api/v1/direct-two-bolt/design-check",json=body)
            assert response.status_code==(200 if alignment is Alignment.BRACE else 422),response.text
            if alignment is Alignment.BRACE:
                data=response.json()
                assert data["structural_route"]=="B_FRESH_LEGACY_COMPATIBLE"
                signer=app.state.report_signer
                original=signer.verify(app.state.report_snapshot_store.get(data["report_handle"]),
                                       account_id="local-development-account")
                before=deepcopy((original.request,original.result,original.input_provenance))
                digest=request_digest(original.request)
                identity=PhysicalIdentity("local-development-account","DIRECT_ACTUAL_REVIEW_FIXTURE",
                                          digest,digest,"DIRECT_ORIGINAL_EXPLICIT_LRFD_ONLY",alignment)
                actions=PairedActions(identity,(at_g,),(),CaseManifest((action.case_id,),(),True,False,
                                      "ASD_COMBINATIONS_NOT_SUPPLIED; existing LRFD source only"),
                                      (action,))
                token=signer.issue(family=original.family,kind=original.kind,request=original.request,
                                   result=original.result,account_id=identity.account,
                                   input_provenance={**original.input_provenance,
                                                     "hyb1_lrfd_action_digest":at_g.digest})
                native=capture_signed_native(signer,token,actions,action.case_id)
                assert original.result["final_decision"]["final_status"]=="YELLOW"
                assert original.result["final_decision"]["analytical_check_summary"]["evaluated"]==8
                assert native.immutable_payload==canonical_record(original.result)
                assert before==(original.request,original.result,original.input_provenance)
            else:
                assert geometry["structural_route"]=="C_GEOMETRY_ONLY"
                assert "result" not in geometry
                digest=request_digest(body)
                identity=PhysicalIdentity("local-development-account","DIRECT_ACTUAL_REVIEW_FIXTURE",
                                          digest,digest,"DIRECT_ORIGINAL_EXPLICIT_LRFD_ONLY",alignment)
                actions=PairedActions(identity,(at_g,),(),CaseManifest((action.case_id,),(),True,False,
                                      "ASD_COMBINATIONS_NOT_SUPPLIED; no structural route activated"),
                                      (action,))
                payload=canonical_record(geometry)
                native=NativeCapture(identity,actions.digest,payload,sha256(payload).hexdigest(),(),
                                     "GRAY_GEOMETRY_ONLY","UNCHANGED_SAB2_ROUTE_C; no old results copied")
            extra=SupplementalSet(actions.identity,actions.digest,())
            review=assess_hybrid(actions,native,extra)
            assert review.current and not review.analytical_candidate_complete
            assert not review.case_sets_complete and not review.public_activation
            output["direct-"+alignment.value.lower()+"-actual-incomplete"]=(actions,review,())
    return output


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    output=parser.parse_args().output.resolve();output.mkdir(parents=True,exist_ok=True)
    bodies={alignment:sab2_body(alignment=alignment.value) for alignment in Alignment}
    cases={**generate_reference_cases(),**asyncio.run(generate_actual_cases(bodies))}
    records=[]
    for name,(actions,review,workbooks) in cases.items():
        before=repr((actions,review,workbooks))
        pdf=render_hyb1_review(review,actions,workbooks=workbooks)
        reader=PdfReader(io.BytesIO(pdf));text=" ".join(" ".join(page.extract_text() or "" for page in reader.pages).split())
        assert TITLE in text
        assert all(row.mechanism in text and str(row.ratio) in text for row in review.rows)
        assert all(str(book.column_summary) in text and book.summary_cell in text for book in workbooks)
        assert "report_handle" not in text and "R1." not in text
        assert before==repr((actions,review,workbooks))
        path=output/(name+".pdf");path.write_bytes(pdf)
        record=review_record(review,actions)
        record["reference_streams"]=[asdict(book) for book in workbooks]
        (output/(name+".json")).write_text(json.dumps(record,indent=2,default=str),encoding="utf-8")
        (output/(name+".txt")).write_text(text,encoding="utf-8")
        records.append({"file":path.name,"sha256":sha256(pdf).hexdigest(),"pages":len(reader.pages),
                        "native_status":review.native_status,"comparison":review.numerical_outcome,
                        "current":review.current,"complete":review.analytical_candidate_complete,
                        "scope":review.evidence_scope,"public_activation":False})
        print(path.name+": "+str(len(reader.pages))+" pages",flush=True)
    metadata={"candidate_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
              "platform":platform.platform(),"report_count":len(records),"reports":records,
              "native_snapshot_preservation":True,"runtime_interference":False,
              "method_adoption":"PENDING_OWNER_REVIEW","qualification_installed":False}
    (output/"HYB1_PLATFORM_QA.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    assert len(records)==6


if __name__=="__main__":
    main()
