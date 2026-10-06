"""F5 actual signed material-specification reports and platform numerical evidence."""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tests.api.test_asce_shape_f5 import f5_body
from tests.api.test_f593_f4 import design, supported
from frp_master_connection.application.asce_shape_materials import SHAPE_BASIS, SHAPE_CATALOG_DIGEST
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

def cases() -> dict[str, dict]:
    result = {
        "isophthalic-70": f5_body(),
        "vinyl-70": f5_body(resin=1),
        "isophthalic-120": f5_body(sustained_temperature={"value": "120", "unit": "degF"}, maximum_temperature={"value": "120", "unit": "degF"}),
        "vinyl-120": f5_body(resin=1, sustained_temperature={"value": "120", "unit": "degF"}, maximum_temperature={"value": "120", "unit": "degF"}),
        "sustained-moisture": f5_body(moisture="SUSTAINED_MOISTURE"),
        "tmax-150": f5_body(maximum_temperature={"value": "150", "unit": "degF"}),
        "sustained-over-140": f5_body(sustained_temperature={"value": "140.001", "unit": "degF"}, maximum_temperature={"value": "150", "unit": "degF"}),
        "chemical-source-required": f5_body(chemical="SPECIFIED", chemical_substance="QA declared chemical", chemical_contact_form="Sustained contact"),
        "characteristic-property-red": f5_body(row_count=1),
        "si-reference": f5_body(si=True, sustained_temperature={"value": "21.1111111111111111111111111111111111111111111111111111111111", "unit": "degC"}, maximum_temperature={"value": "37.7777777777777777777777777777777777777777777777777777777778", "unit": "degC"}),
    }
    result["characteristic-property-red"]["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["y"] = "1.75"
    return result

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True))
    signer = SnapshotSigner(b"ASCE-F5-PLATFORM-REPORT-32-BYTE-KEY")
    manifest = []
    for name, body in cases().items():
        result = design(body)
        source = result["material_sources"]
        basis = source["condition_basis"]["default"]
        rows = supported(result)
        single = result["native_design"]["automatic_group_mode_integration"].get("direct_single_row_result")
        if single is not None:
            rows += [c for c in single["checks"] if c["availability"] == "CALCULATED"]
        assert source["default"]["property_basis"] == SHAPE_BASIS
        assert source["default"]["specification"]["catalog_digest"] == SHAPE_CATALOG_DIGEST
        assert basis["actual_tg_f"] is None
        assert basis["required_tg"]["value"] == ("190" if name in {"tmax-150", "sustained-over-140"} else "180")
        expected = {"isophthalic-120": "0.700", "vinyl-120": "0.740"}.get(name, "1")
        if name not in {"sustained-over-140", "chemical-source-required"}:
            from decimal import Decimal
            assert all(Decimal(l["ct"]) == Decimal(expected) for l in result["material_ledgers"] if "strength" in l["property_id"])
        if name == "sustained-moisture":
            assert all(l["cm"] == ("0.90" if "modulus" in l["property_id"] else "0.75") for l in result["material_ledgers"])
        if name == "sustained-over-140":
            assert "TEST_BASED_TEMPERATURE_FACTOR_REQUIRED" in result["material_issues"]
        if name == "chemical-source-required":
            assert "CHEMICAL_ADJUSTMENT_SOURCE_REQUIRED" in result["material_issues"]
        if name == "characteristic-property-red":
            assert result["overall_status"] == "FAIL"
            assert any(c["limit_state"] == "SINGLE_ROW_CLEAVAGE" and c["numerical_comparison"] == "FAIL" for c in rows)
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, account_id="f5-platform"), account_id="f5-platform")
        original = deepcopy((snapshot.request, snapshot.result))
        for mode in (("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "isophthalic-70" else ("ENGINEER_REPORT",)):
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"asce-f5-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "Table 1-2 minimum characteristic" in text
            assert "actual product Tg not measured" in text
            assert "F593G" in text
            if mode == "ENGINEER_REPORT":
                assert "Development only" not in text
            if mode == "FULL_TECHNICAL_AUDIT":
                compact = "".join(text.split())
                assert "legacy_development_record" in compact and "durability_requirements" in compact
                assert SHAPE_CATALOG_DIGEST in compact
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            manifest.append({"candidate_sha": sha, "tracked_working_tree_modified": dirty, "platform": platform.platform(), "case": name, "mode": mode, "file": filename, "pages": len(pages), "bytes": len(pdf), "sha256": hashlib.sha256(pdf).hexdigest().upper(), "snapshot_digest": snapshot.digest, "material_sources": source, "material_ledgers": result["material_ledgers"], "checks": rows, "overall_status": result["overall_status"], "material_issues": result["material_issues"]})
            print(f"{filename}: {len(pages)} pages", flush=True)
        assert (snapshot.request, snapshot.result) == original
        for kind, payload in (("request", snapshot.request), ("result", snapshot.result)):
            (output / (name + "-signed-" + kind + ".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (output / "ASCE_F5_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
