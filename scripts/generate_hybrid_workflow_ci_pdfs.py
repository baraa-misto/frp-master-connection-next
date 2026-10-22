"""Exercise the live-input application and export actual immutable Hybrid reports.

Input specimens are declared values, not registered review-case keys. No tokens or
private source workbook are written to artifacts. Existing generators are retained.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import platform
import subprocess
import sys
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]

import httpx
from pypdf import PdfReader

from frp_master_connection.api.hybrid_app import create_hybrid_app
from tests.hybrid_workflow_fixtures import live_native, live_source, q

BASE = "/api/v1/direct-hybrid"


async def generate(output: Path, native_inputs: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    source = live_source()
    cases = {"source": source, "native": deepcopy(native_inputs)}
    for name in ["overload", "washer-declared", "washer-unknown", "empty", "unsupported", "si", "varied"]:
        cases[name] = deepcopy(source)
    cases["overload"]["asd_cases"][0]["components"][0]["value"] = "60"
    for name in ["washer-declared", "washer-unknown"]:
        cases[name]["washer_od"] = q("1")
    cases["washer-declared"]["bearing_face"] = "DECLARED_STRAIGHT_FREE_EDGE"
    cases["empty"]["asd_cases"] = []
    cases["unsupported"]["asd_cases"][0]["components"][5]["value"] = "1"
    cases["varied"]["asd_cases"][0]["components"][0]["value"] = ".18310"
    cases["varied"]["geometry"]["xb"]["value"] = ".5"
    cases["invalid-hole"] = deepcopy(source)
    cases["invalid-hole"]["geometry"]["hole"]["value"] = "3"
    cases["brace-placement"] = deepcopy(source)
    cases["brace-placement"]["alignment"] = "BRACE"
    detail = cases["detailing-failure"] = deepcopy(native_inputs)
    legacy = detail["native_request"]["legacy"]
    legacy["loaded_boundary_to_row_1_distance"] = q(".9")
    legacy["unloaded_end_e1"] = q(".9")
    legacy["physical_connection"]["geometry_template"]["bolt_to_brace_end_distance"] = q(".9")
    reports = []
    records = {}
    app = create_hybrid_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        for name, body in cases.items():
            body["workspace_id"] = "ci-live-" + name
            if name == "si":
                converted = await client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
                assert converted.status_code == 200, converted.text
                body = converted.json()
            response = await client.post(BASE + "/assess", json=body)
            assert response.status_code == 200, response.text
            data = response.json()
            record = data["record"]
            handle = data["report_handle"]
            assert data["workflow_available"] and not data["structural_method_activation"]
            assert not record["assessment"]["analytical_complete"]
            assert not record["assessment"]["public_activation"]
            assert record["qualification"] == "NOT_ESTABLISHED_SECTION_2_3_2"
            exported = await client.get(BASE + "/records/" + handle)
            assert exported.status_code == 200 and exported.json() == record
            records[name] = record
            for technical in ([False, True] if name in ["source", "native"] else [False]):
                stem = "hybrid-" + name + ("-technical-audit" if technical else "-calculation")
                pdf = await client.get(BASE + "/reports/" + handle, params={"technical": str(technical).lower()})
                assert pdf.status_code == 200, pdf.text
                reader = PdfReader(io.BytesIO(pdf.content))
                text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
                assert "Hybrid Connection Calculation Report" in text
                assert "Not established; Section 2.3.2 remains open" in text
                assert "C13 and Section 2.3.2 remain open" in text
                assert "field-use history, not physical load-test evidence" in text
                for row in record["assessment"]["comparisons"]:
                    if row["ratio"] is not None:
                        if technical:
                            assert row["ratio"] in text.replace(" ", "")
                        else:
                            assert format(Decimal(row["ratio"]), ".3f") in text
                (output / (stem + ".pdf")).write_bytes(pdf.content)
                (output / (stem + ".json")).write_bytes(exported.content)
                (output / (stem + ".txt")).write_text(text, encoding="utf8")
                reports.append({"file": stem + ".pdf", "sha256": sha256(pdf.content).hexdigest(), "pages": len(reader.pages), "record_sha256": sha256(exported.content).hexdigest(), "evaluated_outcome": record["assessment"]["evaluated_outcome"]})
                print(stem + ": " + str(len(reader.pages)) + " pages", flush=True)
            invalidate = await client.post(BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": body["revision"] + 1})
            assert invalidate.status_code == 200
            assert (await client.get(BASE + "/reports/" + handle)).status_code == 409
        # The source pair and actual native connection are distinct fresh runs.
        native = await client.post("/api/v1/direct-two-bolt/design-check", json=deepcopy(native_inputs)["native_request"])
        assert native.status_code == 200
        assert records["native"]["native_result"] == native.json()["result"]
    a = records["source"]["assessment"]
    assert len(a["comparisons"]) == 7
    assert Decimal(a["governing_asd"]["ratio"]) == Decimal("0.100892136239327322431541891418946393327249809999530689928570")
    assert a["comparisons"] == records["si"]["assessment"]["comparisons"]
    assert records["overload"]["assessment"]["evaluated_outcome"] == "FAIL"
    assert records["empty"]["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
    assert records["unsupported"]["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
    assert records["washer-declared"]["assessment"]["fit"]["state"] == "NOT_FIT"
    assert records["washer-declared"]["assessment"]["evaluated_outcome"] == "PASS"
    assert records["detailing-failure"]["detailing_failures"]
    for name in ["invalid-hole", "brace-placement"]:
        assert records[name]["assessment"]["fit"]["state"] == "NOT_FIT"
        assert "Bolt-hole containment/placement fails" in records[name]["assessment"]["fit"]["action"]
        assert records[name]["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
    assert len(reports) == 14
    metadata = {"candidate_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "platform": platform.platform(), "reports": reports, "report_count": len(reports), "live_api_used": True, "immutable_json_matches": True, "native_exact_preservation": True, "us_si_parity": True, "stale_export_rejected": True, "structural_adoption": False, "qualification_installed": False}
    (output / "HYBRID_WORKFLOW_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(generate(parser.parse_args().output, live_native()))
