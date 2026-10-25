"""P4 real authenticated reports and independently fixed numerical acceptance cases."""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import platform
import subprocess
import sys
from copy import deepcopy
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]

import httpx
from pypdf import PdfReader

from frp_master_connection.api.hybrid_app import create_hybrid_app
from tests.hybrid_physical_fixtures import physical_case
from tests.hybrid_same_connection_fixtures import same_connection

BASE = "/api/v1/direct-hybrid"


async def generate(output: Path, original: dict, physical: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    original["physical_context"] = {
        "contract": "HYB2-D3-P4-PHYSICAL/1", "hole_source": "US_CUSTOMARY_PRINTED",
    }
    cases = {name: deepcopy(original) for name in ("p3-preserved", "washer-declared", "improved-angle")}
    cases["washer-declared"].update(
        bearing_face="DECLARED_STRAIGHT_FREE_EDGE",
        washer_od={"value": "1", "unit": "in"},
    )
    cases["improved-angle"]["geometry"]["xb"]["value"] = "1"
    for name in ("new-physical-positive", "new-physical-fail", "partial-contact", "new-physical-si"):
        cases[name] = deepcopy(physical)
    cases["new-physical-fail"]["lrfd_cases"][0]["components"][0]["value"] = "10"
    cases["partial-contact"]["physical_context"]["interface_gap"] = None
    records, receipts = {}, []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_hybrid_app()), base_url="http://testserver"
    ) as client:
        for name, body in cases.items():
            body["workspace_id"] = "p4-ci-" + name
            if name == "new-physical-si":
                converted = await client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
                assert converted.status_code == 200, converted.text
                body = converted.json()
            preview = await client.post(BASE + "/preview", json=body)
            assert preview.status_code == 200 and "record" not in preview.json()
            response = await client.post(BASE + "/assess", json=body)
            assert response.status_code == 200, response.text
            data = response.json()
            record, handle = data["record"], data["report_handle"]
            records[name] = record
            axes = record["physical_design"]["status_axes"]
            assert axes["required_coverage"] == "REQUIRED_COVERAGE_PARTIAL"
            assert axes["qualification"] == "NOT_ESTABLISHED_SECTION_2_3_2"
            assert axes["whole_connection"] != "PASS"
            assert not record["assessment"]["public_activation"]
            assert not record["assessment"]["complete_connection_verification"]
            exported = await client.get(BASE + "/records/" + handle)
            assert exported.status_code == 200 and exported.json() == record
            (output / (name + "-record.json")).write_bytes(exported.content)
            for technical in (False, True):
                stem = name + ("-technical-audit" if technical else "-engineer-report")
                pdf = await client.get(
                    BASE + "/reports/" + handle, params={"technical": str(technical).lower()}
                )
                assert pdf.status_code == 200, pdf.text
                pages = PdfReader(io.BytesIO(pdf.content)).pages
                text = " ".join(" ".join(page.extract_text() for page in pages).split())
                assert "Current physical structural components" in text
                assert "Required physical mechanism dispositions" in text
                assert "Section 2.3.2" in text and "prying" in text
                for item in record["physical_design"]["cases"]:
                    if item["disposition"] == "EXECUTED":
                        assert "ASCE/SEI 74-23 Eq.8-12" in text
                        assert "actual free end" in text.lower()
                        assert (item["design_resistance_kip"] in text.replace(" ", "")
                                if technical else format(Decimal(item["design_resistance_kip"]), ".3f") in text)
                (output / (stem + ".pdf")).write_bytes(pdf.content)
                (output / (stem + ".txt")).write_text(text, encoding="utf8")
                receipts.append({
                    "file": stem + ".pdf", "sha256": sha256(pdf.content).hexdigest(),
                    "record_sha256": sha256(exported.content).hexdigest(), "pages": len(pages),
                    "status_axes": axes,
                })
                print(stem, len(pages), "pages", flush=True)
            assert (await client.post(BASE + "/invalidate", json={
                "workspace_id": body["workspace_id"], "revision": body["revision"] + 1
            })).status_code == 200
            assert (await client.get(BASE + "/reports/" + handle)).status_code == 409
            assert (await client.get(BASE + "/records/" + handle)).status_code == 409
    positive = records["new-physical-positive"]["physical_design"]["cases"][0]
    failure = records["new-physical-fail"]["physical_design"]["cases"][0]
    si = records["new-physical-si"]["physical_design"]["cases"][0]
    assert Decimal(positive["nominal_resistance_kip"]) == Decimal("21.61593")
    assert Decimal(positive["design_resistance_kip"]) == Decimal("5.8363011")
    assert positive["outcome"] == "PASS" and failure["outcome"] == "FAIL"
    assert Decimal(failure["design_resistance_kip"]) == Decimal(positive["design_resistance_kip"])
    with localcontext() as context:
        context.prec = 80
        assert Decimal(failure["utilization"]) == Decimal(positive["utilization"]) * 100
    assert si["design_resistance_kip"] == positive["design_resistance_kip"]
    assert si["utilization"] == positive["utilization"]
    assert records["partial-contact"]["physical_design"]["cases"][0]["disposition"] == "REQUIRED_NOT_EVALUATED"
    assert len(records["p3-preserved"]["detailing_failures"]) == 2
    assert not records["improved-angle"]["detailing_failures"]
    assert records["p3-preserved"]["assessment"]["comparisons"] == original_comparisons(records["washer-declared"])
    assert Decimal(records["washer-declared"]["assessment"]["fit"]["actual_overhang_in"]) == Decimal(".0625")
    assert records["washer-declared"]["physical_design"]["status_axes"]["viewer_tone"] == "red"
    assert len(receipts) == 14
    metadata = {
        "result": "PASS", "candidate_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(), "reports": receipts, "report_count": len(receipts),
        "new_physical_mode": "ASCE_EQ_8_12_RECEIVING_LONGITUDINAL_SHEAR_OUT",
        "independent_nominal_kip": "21.61593", "independent_design_kip": "5.8363011",
        "positive_failure_inapplicability": True, "US_SI_physical_capacity_and_UR_equal": True,
        "P3_numerical_results_preserved": True, "actual_short_end_failure_retained": True,
        "declared_washer_overhang_in": ".0625", "current_record_export_and_stale_rejection": True,
        "adoption": "PENDING_OWNER_ENGINEERING_REVIEW",
    }
    (output / "P4_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")


def original_comparisons(record: dict) -> list:
    return record["assessment"]["comparisons"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.output, same_connection(), physical_case()))
