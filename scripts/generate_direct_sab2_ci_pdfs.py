"""Authenticated SAB2 geometry reviews and exact legacy-route regression evidence."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import platform
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]
import httpx
from pypdf import PdfReader
from tests.direct_sab2_cases import sab2_cases
from frp_master_connection.api.app import create_app
from frp_master_connection.application.direct_two_bolt_geometry import GEOMETRY_BANNER

EXPECTED = {
    "exact-mc1-brace":"CONDITIONAL", "wider-w-brace-relocated":"CONDITIONAL",
    "detail2-support-nominal":"CONDITIONAL", "narrow-i-fixed-brace-no-fit":"DOES_NOT_FIT",
    "brace-split-outstand-relocated":"CONDITIONAL", "smaller-angle-no-fit":"DOES_NOT_FIT",
    "known-neighbor-no-fit":"DOES_NOT_FIT", "finite-cut-root-contact-unknown-access":"CONDITIONAL",
}

async def generate(output: Path, cases: dict) -> list[dict]:
    app = create_app()
    records = []
    legacy_records = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver") as client:
        for name, body in cases.items():
            response = await client.post("/api/v1/direct-two-bolt/preview",json=body)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["geometry"]["aggregate_state"] == EXPECTED[name]
            assert data["resistance_evaluated"] is False and data["qualification_activated"] is False
            assert not data["visualization"]["automatic_bolt_demands"]
            for station in ("B1","B2"):
                points=[p for p in data["geometry"]["face_points"] if p["station"] == station]
                assert len(points)==2 and points[0]["global_center"]==points[1]["global_center"]
            if name == "exact-mc1-brace":
                fresh = await client.post("/api/v1/direct-two-bolt/design-check",json=body)
                old = await client.post("/api/v1/frp-materials/multi-row/design-check",json=body["material_request"])
                assert fresh.status_code == old.status_code == 200
                assert fresh.json()["result"] == old.json()
                assert fresh.json()["result"]["final_decision"]["final_status"] == "YELLOW"
                (output / (name+"-fresh-structural-result.json")).write_text(json.dumps(fresh.json()["result"],indent=2),encoding="utf-8")
                for mode in ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"):
                    structural_pdf = await client.post("/api/v1/reports/export",json={
                        "report_handle":fresh.json()["report_handle"],"mode":mode,
                    })
                    assert structural_pdf.status_code == 200, structural_pdf.text
                    structural_reader = PdfReader(io.BytesIO(structural_pdf.content))
                    structural_text = "\n".join(p.extract_text() or "" for p in structural_reader.pages)
                    assert "YELLOW" in structural_text
                    structural_file = "direct-sab2-fresh-legacy-" + mode.lower() + ".pdf"
                    (output/structural_file).write_bytes(structural_pdf.content)
                    (output/(structural_file+".txt")).write_text(structural_text,encoding="utf-8")
                    legacy_records.append(dict(mode=mode,file=structural_file,pages=len(structural_reader.pages),
                        sha256=hashlib.sha256(structural_pdf.content).hexdigest().upper(),
                        structural_route="B_FRESH_LEGACY_COMPATIBLE",final_status="YELLOW",
                        fresh_result_exactly_equals_legacy=True))
            else:
                blocked = await client.post("/api/v1/direct-two-bolt/design-check",json=body)
                assert blocked.status_code == 422
                assert data["structural_route"] == "C_GEOMETRY_ONLY"
            handle = data.pop("geometry_report_handle")
            snapshot = app.state.report_signer.verify(app.state.report_snapshot_store.get(handle),account_id="local-development-account")
            before=deepcopy((snapshot.request,snapshot.result,snapshot.input_provenance))
            pdf=await client.post("/api/v1/direct-two-bolt/geometry-review",json={"report_handle":handle,"current_request":body})
            assert pdf.status_code == 200,pdf.text
            reader=PdfReader(io.BytesIO(pdf.content))
            embedded=json.loads(reader.attachments["SAB2_complete_technical_audit.json"][0])
            assert embedded==dict(request=snapshot.request,geometry_snapshot=snapshot.result,input_provenance=snapshot.input_provenance)
            texts=[page.extract_text() or "" for page in reader.pages]
            assert all(GEOMETRY_BANNER in text for text in texts)
            text="\n".join(texts)
            assert data["geometry_fingerprint"] in text
            assert "Technical audit appendix" in text
            assert "Pair spacing p =" in text and "B1:" in text and "B2:" in text
            assert before==(snapshot.request,snapshot.result,snapshot.input_provenance)
            filename="direct-sab2-"+name+".pdf"
            (output/filename).write_bytes(pdf.content)
            (output/(filename+".txt")).write_text(text,encoding="utf-8")
            for suffix,value in (("request",snapshot.request),("result",snapshot.result),("provenance",snapshot.input_provenance)):
                (output/(name+"-"+suffix+".json")).write_text(json.dumps(value,indent=2),encoding="utf-8")
            records.append(dict(case=name,file=filename,pages=len(reader.pages),bytes=len(pdf.content),
                                sha256=hashlib.sha256(pdf.content).hexdigest().upper(),
                                geometry_fingerprint=data["geometry_fingerprint"],snapshot_digest=snapshot.digest,
                                state=data["geometry"]["aggregate_state"],route=data["structural_route"],
                                renderer_did_not_mutate_snapshot=True))
            print(f"{filename}: {len(reader.pages)} pages; {data['geometry']['aggregate_state']}",flush=True)
    (output/"DIRECT_SAB2_FRESH_LEGACY_REPORT_QA.json").write_text(json.dumps(legacy_records,indent=2),encoding="utf-8")
    assert len(legacy_records)==2
    return records

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    output=parser.parse_args().output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    cases=sab2_cases()
    records=asyncio.run(generate(output,cases))
    assert len(records)==8
    metadata=dict(candidate_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                  tracked_working_tree_modified=bool(subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True)),
                  platform=platform.platform(),python=platform.python_version(),reports=records,
                  report_count=len(records),structural_qualification_activated=False,
                  private_reference_pdfs_included=False)
    (output/"DIRECT_SAB2_PLATFORM_QA.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")

if __name__ == "__main__":
    main()
