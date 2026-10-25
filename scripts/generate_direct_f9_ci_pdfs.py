"""Generate the twelve real F9 review PDFs; every QA record remains nonactivating."""
from __future__ import annotations
import argparse, asyncio, hashlib, io, json, platform, subprocess, sys, tempfile
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]
import httpx
from pypdf import PdfReader
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design, supported
from tests.direct_f8_fixtures import qa_design, synthetic_record
from frp_master_connection.api.app import create_app
from frp_master_connection.api.direct_qualification import authenticated_scope, evaluate_record, qualification_snapshot_provenance
from frp_master_connection.api.direct_status import attach_direct_status, direct_status_snapshot_current
from frp_master_connection.api.mat1 import MaterialAssignmentsDTO, _json_value, resolve_material, resolve_conditions
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application.direct_qualification_records import content_digest
from frp_master_connection.application.mat1_materials import property_ledger
from frp_master_connection.infrastructure.direct_qualification_records import canonical_record, QualificationRecordProvider, production_provider
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True))
    controls = f6_cases()
    baseline = controls["owner-135"]
    cases = {"owner-no-record": baseline, "si-owner": controls["si-owner"]}
    red = deepcopy(baseline)
    force = red["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]
    with localcontext() as ctx:
        ctx.prec=80
        for axis in ("x", "y", "z"): force[axis]=str(Decimal(force[axis])*10)
    cases["analytical-red"] = red
    invalid = deepcopy(baseline); invalid["legacy_request"]["row_count"] = 0
    cases["geometry-invalid-input-only"] = invalid
    app = create_app()
    snapshots = {}
    api_pdfs = {}
    async def actual() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            for name, body in cases.items():
                response = await client.post("/api/v1/frp-materials/multi-row/design-check?report_snapshot=1",json=body)
                assert response.status_code == (422 if name == "geometry-invalid-input-only" else 200),response.text
                handle=response.headers["X-Report-Handle"]
                snapshots[name]=app.state.report_signer.verify(app.state.report_snapshot_store.get(handle),account_id="local-development-account")
                pdf=await client.post("/api/v1/reports/export",json={"report_handle":handle})
                assert pdf.status_code==200,pdf.text
                api_pdfs[name] = pdf.content
            draft=await client.post("/api/v1/reports/input-only-snapshot",json={"family":"multi-row","draft":baseline})
            handle=draft.json()["report_handle"]
            snapshots["stale-no-current-design"]=app.state.report_signer.verify(app.state.report_snapshot_store.get(handle),account_id="local-development-account")
            assert (await client.post("/api/v1/reports/direct-decision-current",json={"report_handle":handle})).status_code==409
            pdf = await client.post("/api/v1/reports/export", json={"report_handle":handle})
            assert pdf.status_code == 200, pdf.text
            api_pdfs["stale-no-current-design"] = pdf.content
    asyncio.run(actual())
    qa_body, _, _, _, _, base_context = qa_design()
    signer=SnapshotSigner(b"DIRECT-F9-ISOLATED-NONACTIVATING-PDF-QA-KEY")
    for name in ("selected-record-mismatch","incomplete-response-coverage","qualification-capacity-fail-qa","synthetic-matching-qa","gravity-eq-2-2","unsupported-action-history"):
        body=deepcopy(qa_body)
        context=base_context
        if name=="gravity-eq-2-2":
            data=context.model_dump(mode="json")
            data.update(loading_type="GRAVITY_D_L",dead_load={"value":".35","unit":"kip"},live_load={"value":".175","unit":"kip"})
            context=type(context).model_validate(data)
            body["legacy_request"]["time_effect_category"]="OTHER_LIVE"
            body["assignments"]["default_conditions"].update(time_effect_category="OTHER_LIVE",live_load_subtype="OTHER_LIVE",load_case_name="SYNTHETIC QA 1.2D + 1.6L")
        if name=="unsupported-action-history":
            context=context.model_copy(update={"loading_history":"REVERSED"})
        body["qualification_context"]=context.model_dump(mode="json")
        result=design(body)
        provenance=qualification_snapshot_provenance(result)
        scope=provenance["direct_qualification_audit"]["design_scope"]
        required=Decimal(result["qualification_evaluation"]["Ru"]["value"])
        assignment=MaterialAssignmentsDTO.model_validate(body["assignments"])
        material=resolve_material(assignment.default_material)
        conditions=resolve_conditions(assignment.default_conditions)
        ledgers=[property_ledger("member-a",material,"tensile_strength_L",conditions)]
        with tempfile.TemporaryDirectory(prefix="direct-f9-nonactivating-") as tmp:
            directory=Path(tmp)
            payload=synthetic_record(scope,directory,strength="100" if name=="qualification-capacity-fail-qa" else "10000")
            if name=="selected-record-mismatch": payload["geometry_scope"]["row_count"]=3
            elif name=="incomplete-response-coverage": payload["coverage_ids"]=payload["coverage_ids"][:-1]
            elif name=="gravity-eq-2-2": payload["statistical_protocol"]["gravity_protocol_approved"]=True
            elif name=="unsupported-action-history": payload["action_scope"]["loading_history"]="MONOTONIC_STATIC"
            payload["digest"]=""
            population=content_digest({key:payload[key] for key in ("connection_scope","material_identity","fastener_identity","geometry_scope","action_scope","environmental_scope","support_scope")})
            for specimen in payload["specimens"]: specimen["population_scope_digest"]=population
            record=canonical_record(payload)
            assert not QualificationRecordProvider(directory,(record,)).read()[0]
            public,audit=evaluate_record(record,scope,required,ledgers,context,qa_preview=True)
        assert public["synthetic"] is True and public["activation_permitted"] is False
        augmented=attach_direct_status({**result,"qualification_evaluation":public},MultiRowConnectionRequestDTO.model_validate(body["legacy_request"]).model_dump(mode="json"),{"direct_qualification_audit":audit})
        assert augmented["final_decision"]["final_status"]=="YELLOW"
        assert direct_status_snapshot_current(augmented,body)
        snapshots[name]=signer.verify(signer.issue(family="multi-row",kind="design",request=body,result=augmented,input_provenance={"direct_qualification_audit":audit},account_id="f9-qa"),account_id="f9-qa")
    reports=[]
    for name,snapshot in snapshots.items():
        mode="ENGINEER_REPORT"
        before=deepcopy((snapshot.request,snapshot.result,snapshot.input_provenance))
        pdf=api_pdfs[name] if name in api_pdfs else render_report_pdf(snapshot,ReportOptions())
        filename=f"direct-f9-{name}-{mode.lower()}.pdf"
        (output/filename).write_bytes(pdf)
        pages=PdfReader(io.BytesIO(pdf)).pages
        text=" ".join(" ".join(p.extract_text() or "" for p in pages).split())
        decision=snapshot.result["final_decision"]
        assert decision["final_status"] in text
        assert "final status integration pending" not in text
        if snapshot.result.get("qualification_evaluation",{}).get("synthetic"):
            assert "SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN" in text
        if name=="owner-no-record":
            assert decision["analytical_check_summary"]["evaluated"]==8
            assert decision["analytical_check_summary"]["counts"]["REQUIRED_UNRESOLVED"]==6
            assert "YELLOW — QUALIFICATION REQUIRED" in text and "Not stated" not in text
        if name=="analytical-red": assert decision["final_status"]=="RED"
        if snapshot.kind=="input_only": assert decision["final_status"]=="GRAY"
        (output/(filename+".txt")).write_text(text,encoding="utf-8")
        checks=supported(snapshot.result) if snapshot.result.get("native_design",{}).get("automatic_group_mode_integration") else []
        reports.append(dict(case=name,mode=mode,file=filename,pages=len(pages),sha256=hashlib.sha256(pdf).hexdigest().upper(),decision=decision,checks=checks,evaluation=snapshot.result.get("qualification_evaluation"),snapshot_digest=snapshot.digest))
        assert before==(snapshot.request,snapshot.result,snapshot.input_provenance)
        for label,data in (("request",snapshot.request),("result",snapshot.result),("provenance",snapshot.input_provenance)):
            (output/(name+"-signed-"+label+".json")).write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(f"{filename}: {len(pages)} pages; {decision['final_status']}",flush=True)
    # The matrix has twelve PDFs: eleven Engineer Reports plus one representative audit.
    audit_snapshot=snapshots["synthetic-matching-qa"]
    pdf=render_report_pdf(audit_snapshot,ReportOptions(mode="FULL_TECHNICAL_AUDIT"))
    filename="direct-f9-synthetic-matching-qa-full_technical_audit.pdf"
    (output/filename).write_bytes(pdf)
    pages=PdfReader(io.BytesIO(pdf)).pages
    text=" ".join(p.extract_text() or "" for p in pages)
    assert "SYNTHETIC_QA_10" in text and "final_status" in text
    assert audit_snapshot.input_provenance["direct_qualification_audit"]["record"]["digest"] in text.replace("\n","")
    reports.append(dict(case="synthetic-matching-qa",mode="FULL_TECHNICAL_AUDIT",file=filename,pages=len(pages),sha256=hashlib.sha256(pdf).hexdigest().upper(),decision=audit_snapshot.result["final_decision"],checks=supported(audit_snapshot.result),evaluation=audit_snapshot.result["qualification_evaluation"],snapshot_digest=audit_snapshot.digest))
    assert production_provider().read()[0]==()
    metadata=dict(candidate_sha=sha,tracked_working_tree_modified=dirty,platform=platform.platform(),report_count=len(reports),reports=reports,production_green_available=False,production_records=[])
    (output/"DIRECT_F9_PLATFORM_QA.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(f"F9 actual platform PDF matrix: {len(reports)} PDFs; no approved record installed",flush=True)

if __name__=="__main__": main()

