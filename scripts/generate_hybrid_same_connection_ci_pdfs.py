"""P3 actual same-connection reports, numerical preservation and signed-currentness evidence."""

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
from tests.hybrid_same_connection_fixtures import same_connection
from tests.hybrid_workflow_fixtures import live_source, live_native

BASE = "/api/v1/direct-hybrid"


async def generate(output: Path, original: dict, native: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cases = {name: deepcopy(original) for name in (
        "same-connection", "lrfd-overload", "asd-overload", "eccentric-lrfd", "modified-spacing",
        "si", "washer-clearance", "brace-domain", "temperature-source-gap", "missing-asd",
        "shifted-reference", "positive-n-reference",
    )}
    cases["lrfd-overload"]["lrfd_cases"][0]["components"][0]["value"] = "20"
    cases["asd-overload"]["asd_cases"][0]["components"][0]["value"] = "20"
    cases["eccentric-lrfd"]["lrfd_cases"][0]["components"][5]["value"] = ".012"
    cases["shifted-reference"]["lrfd_cases"][0]["reference"][1]["value"] = ".25"
    cases["positive-n-reference"]["lrfd_cases"][0]["frame"] = "DIRECT_P_POSITIVE_N_CENTROID"
    cases["positive-n-reference"]["lrfd_cases"][0]["components"][1]["value"] = "-.02"
    cases["positive-n-reference"]["lrfd_cases"][0]["reference"][1]["value"] = "-.25"
    cases["modified-spacing"]["geometry"]["vertical_bolt_pitch"]["value"] = "3"
    cases["washer-clearance"].update(bearing_face="DECLARED_STRAIGHT_FREE_EDGE",
                                       washer_od={"value": "1", "unit": "in"})
    cases["brace-domain"]["alignment"] = "BRACE"
    for key in ("design_temperature", "sustained_temperature", "maximum_temperature"):
        cases["temperature-source-gap"]["same_connection_lrfd"]["assignments"]["default_conditions"][key]["value"] = "150"
    cases["missing-asd"]["asd_cases"] = []
    records, receipts = {}, []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_hybrid_app()),
                                 base_url="http://testserver") as client:
        preserved_source = live_source()
        preserved_source["workspace_id"] = "p3-original-source-control"
        native["workspace_id"] = "p3-original-native-control"
        old_source = (await client.post(BASE + "/assess", json=preserved_source)).json()["record"]
        response = await client.post(BASE + "/assess", json=native)
        assert response.status_code == 200, response.text
        old_native = response.json()["record"]
        assert old_native["requested_computation"]["native_checks_executed"] == 8
        direct = await client.post("/api/v1/direct-two-bolt/design-check", json=native["native_request"])
        assert direct.status_code == 200, direct.text
        assert old_native["native_result"] == direct.json()["result"]
        for name, body in cases.items():
            body["workspace_id"] = "p3-ci-" + name
            if name == "si":
                response = await client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
                assert response.status_code == 200, response.text
                body = response.json()
            response = await client.post(BASE + "/assess", json=body)
            assert response.status_code == 200, response.text
            data = response.json()
            record, handle = data["record"], data["report_handle"]
            records[name] = record
            a = record["assessment"]
            assert not a["public_activation"] and not a["analytical_complete"]
            assert not a["complete_connection_verification"]
            assert record["qualification"] == "NOT_ESTABLISHED_SECTION_2_3_2"
            exported = await client.get(BASE + "/records/" + handle)
            assert exported.status_code == 200 and exported.json() == record
            for technical in ([False, True] if name == "same-connection" else [False]):
                stem = "p3-" + name + ("-technical-audit" if technical else "-calculation")
                pdf = await client.get(BASE + "/reports/" + handle,
                                       params={"technical": str(technical).lower()})
                assert pdf.status_code == 200, pdf.text
                pages = PdfReader(io.BytesIO(pdf.content)).pages
                text = " ".join(" ".join(page.extract_text() for page in pages).split())
                assert "Same physical connection - ASCE component mapping" in text
                assert "Section 2.3.2" in text and "first-row" in text
                assert "field-use history, not physical load-test evidence" in text
                for row in a["comparisons"]:
                    if row["ratio"] is not None:
                        assert (row["ratio"] in text.replace(" ", "") if technical else
                                format(Decimal(row["ratio"]), ".3f") in text)
                if technical:
                    assert "Same-connection ASCE exact technical audit" in text
                    assert "equation_trace" in text and "DECIMAL_80" in text
                (output / (stem + ".pdf")).write_bytes(pdf.content)
                (output / (stem + ".json")).write_bytes(exported.content)
                (output / (stem + ".txt")).write_text(text, encoding="utf8")
                receipts.append({"file": stem + ".pdf", "sha256": sha256(pdf.content).hexdigest(),
                                 "record_sha256": sha256(exported.content).hexdigest(),
                                 "pages": len(pages), "numerical_outcome": a["evaluated_outcome"],
                                 "LRFD_checks": sum(r["basis"] == "LRFD" for r in a["comparisons"]),
                                 "RHM_comparisons": sum(r["basis"] == "ASD" for r in a["comparisons"])})
                print(stem, len(pages), "pages", flush=True)
            body["revision"] += 1
            assert (await client.post(BASE + "/invalidate", json=body)).status_code == 422
            assert (await client.post(BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": body["revision"]})).status_code == 200
            assert (await client.get(BASE + "/reports/" + handle)).status_code == 409
            assert (await client.get(BASE + "/records/" + handle)).status_code == 409
    base = records["same-connection"]["assessment"]
    rows = lambda a, b: [r for r in a["comparisons"] if r["basis"] == b]
    assert len(rows(base, "LRFD")) == 6 and len(rows(base, "ASD")) == 7
    assert rows(base, "ASD") == old_source["assessment"]["comparisons"]
    assert base["comparisons"] == records["si"]["assessment"]["comparisons"]
    assert rows(base, "ASD") == rows(records["lrfd-overload"]["assessment"], "ASD")
    assert rows(base, "LRFD") == rows(records["asd-overload"]["assessment"], "LRFD")
    assert all(records[n]["assessment"]["evaluated_outcome"] == "FAIL"
               for n in ("lrfd-overload", "asd-overload"))
    assert records["washer-clearance"]["assessment"]["fit"]["state"] == "NOT_FIT"
    assert records["same-connection"]["detailing_failures"]
    assert records["brace-domain"]["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
    assert len(rows(records["temperature-source-gap"]["assessment"], "LRFD")) == 2
    assert len(rows(records["missing-asd"]["assessment"], "LRFD")) == 6
    assert rows(records["shifted-reference"]["assessment"], "LRFD") == rows(records["positive-n-reference"]["assessment"], "LRFD")
    assert records["shifted-reference"]["same_connection_lrfd"]["cases"][0]["demand"] == records["positive-n-reference"]["same_connection_lrfd"]["cases"][0]["demand"]
    assert len(receipts) == 13
    metadata = {"result": "PASS", "candidate_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(), "reports": receipts, "report_count": len(receipts),
        "native_original_eight_preserved": True, "original_RHM_seven_preserved": True,
        "same_geometry_ASCE_checks": 6, "same_geometry_RHM_comparisons": 7,
        "exact_US_SI_comparisons": True, "independent_overloads_executed": True,
        "stale_records_and_PDFs_rejected": True, "no_method_or_qualification_installed": True,
        "nonzero_reference_signed_frame_parity": True}
    (output / "P3_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(generate(arguments.output, same_connection(), live_native()))
