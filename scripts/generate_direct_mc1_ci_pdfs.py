"""Actual authenticated MC1 Engineer/Audit matrix; no renderer calculation authority."""
from __future__ import annotations
import argparse, asyncio, hashlib, io, json, platform, subprocess, sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]
import httpx
from pypdf import PdfReader
from tests.direct_mc1_fixtures import mc1_cases, mc1_body, raw_mc1_native
from tests.api.test_f593_f4 import supported
from frp_master_connection.api.app import create_app
from frp_master_connection.infrastructure.direct_qualification_records import production_provider
from frp_master_connection.application.direct_qualification_records import content_digest

async def generate(output: Path, cases: dict, parity_bodies: list[dict]) -> list[dict]:
    app = create_app()
    records = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        for name, body in cases.items():
            response = await client.post("/api/v1/frp-materials/multi-row/design-check?report_snapshot=1", json=body)
            assert response.status_code == 200, response.text
            handle = response.headers["X-Report-Handle"]
            snapshot = app.state.report_signer.verify(app.state.report_snapshot_store.get(handle), account_id="local-development-account")
            before = deepcopy((snapshot.request, snapshot.result, snapshot.input_provenance))
            result = snapshot.result
            decision = result["final_decision"]
            assert decision["final_status"] == ("RED" if name == "analytical-red" else "YELLOW")
            assert result["qualification_evaluation"]["capacity_state"] == "UNEVALUATED"
            for suffix, data in (("request", snapshot.request), ("result", result), ("provenance", snapshot.input_provenance)):
                (output / f"{name}-signed-{suffix}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            ledgers = result["material_ledgers"]
            if name != "owner-yellow":
                domain = result["material_sources"]["direct_input_policy"]
                assert domain["contract"] == "SHEAR01-DIRECT-MC1"
                assert body["assignments"]["default_conditions"]["uv_weathering"] == "UNKNOWN"
                strength = next(l for l in ledgers if l["property_id"] == "tensile_strength_L")
                if name == "over-140-blocked":
                    assert strength["ct"] is None and strength["adjusted_candidate"] is None
                    assert decision["analytical_check_summary"]["evaluated"] == 2
                    assert len(result["direct_material_applicability"]["blocked_check_ids"]) == 6
                    assert content_digest(raw_mc1_native(result)) == result["direct_material_applicability"]["raw_engine_diagnostic_native_digest"]
                    assert all(row["limit_state"] == "BOLT_SHEAR" for row in supported(result) if row["availability"] == "CALCULATED")
                else:
                    assert Decimal(strength["adjusted_candidate"]) == Decimal(strength["original"]) * Decimal(strength["cm"]) * Decimal(strength["ct"]) * Decimal(strength["cch"])
                if body["assignments"]["default_conditions"]["chemical"] == "SPECIFIED":
                    modulus = [l for l in ledgers if "modulus" in l["property_id"]]
                    assert len(modulus) == 10
                    assert all(l["cch"] is None and l["adjusted_candidate"] is None and l["chemical_modulus_applicability"] == "UNEVALUATED" for l in modulus)
            for mode in ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"):
                pdf = await client.post("/api/v1/reports/export", json={"report_handle": handle, "mode": mode})
                assert pdf.status_code == 200, pdf.text
                filename = f"direct-mc1-{name}-{mode.lower()}.pdf"
                (output / filename).write_bytes(pdf.content)
                reader = PdfReader(io.BytesIO(pdf.content))
                text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
                assert decision["final_status"] in text
                if name != "owner-yellow":
                    assert "Design Temperature" in text and "conservatively assumed sustained" in text
                if name in {"custom-chemical", "analytical-red"}:
                    assert "Engineer-specified strength-only CCH=.80" in text
                    assert "UNEVALUATED (chemical modulus)" in text
                    if mode == "FULL_TECHNICAL_AUDIT":
                        assert "independent_moisture_temperature_candidate" in "".join(text.split())
                        assert "CHEMICAL_MODULUS_APPLICABILITY_UNRESOLVED" in "".join(text.split())
                if name == "over-140-blocked":
                    assert "test" in text.lower() and "required" in text.lower()
                (output / f"{filename}.txt").write_text(text, encoding="utf-8")
                records.append(dict(case=name, mode=mode, file=filename, pages=len(reader.pages),
                    sha256=hashlib.sha256(pdf.content).hexdigest().upper(), decision=decision,
                    ledgers=ledgers, checks=supported(result), native_demand=result["native_design"]["automatic_demand_result"],
                    snapshot_digest=snapshot.digest, material_sources=result["material_sources"],
                    evaluation=result["qualification_evaluation"]))
                assert before == (snapshot.request, snapshot.result, snapshot.input_provenance)
                print(f"{filename}: {len(reader.pages)} pages; {decision['final_status']}", flush=True)
        parity = []
        for body in parity_bodies:
            response = await client.post("/api/v1/frp-materials/multi-row/design-check", json=body)
            assert response.status_code == 200, response.text
            parity.append(response.json())
        for key in ("native_design", "material_ledgers", "material_sources", "qualification_evaluation", "final_decision"):
            assert parity[0][key] == parity[1][key], key
    assert production_provider().read()[0] == ()
    return records

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases = mc1_cases()
    parity_bodies = [mc1_body(temperature, unit, chemical="SPECIFIED", chemical_strength_factor=".80") for temperature, unit in (("104", "degF"), ("40", "degC"))]
    records = asyncio.run(generate(output, cases, parity_bodies))
    assert len(records) == 14
    metadata = dict(candidate_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        tracked_working_tree_modified=bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)),
        platform=platform.platform(), report_count=len(records), reports=records, production_records=[], production_green_available=False,
        numerical_and_provenance_parity=True, renderer_did_not_mutate_snapshot=True)
    (output / "DIRECT_MC1_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("MC1 actual signed PDF matrix passed: 14 PDFs, seven controls, both modes", flush=True)

if __name__ == "__main__":
    main()
