"""Actual signed Direct F6 PDFs; unresolved methods remain visibly unevaluated."""
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
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design, supported
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True))
    signer = SnapshotSigner(b"DIRECT-F6-PLATFORM-REPORT-32-BYTE-KEY")
    manifest = []
    for name, body in f6_cases().items():
        if name == "real-along-row-force":
            continue
        result = design(body)
        integration = result["native_design"]["automatic_group_mode_integration"]
        assert {"FIRST_ROW:layer-A", "FIRST_ROW:layer-B"} <= set(integration["unsupported_required_check_ids"])
        assert not any(c["result_id"].startswith("FIRST_ROW:") for c in supported(result))
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, account_id="f6-platform"), account_id="f6-platform")
        before = deepcopy((snapshot.request, snapshot.result))
        for mode in (("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "owner-135" else ("ENGINEER_REPORT",)):
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"direct-f6-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "METHOD REQUIRED" in text
            assert "oblique net-section plane" in text
            if mode == "FULL_TECHNICAL_AUDIT":
                assert "F6 first-row authority context" in text
                assert "CS2-APPENDIX-RC3 remains inactive" in text
                assert "0.40/0.20/0.40" in text
            if name == "zero-eccentricity":
                assert "physical Figure C8-11 effective width" in text
            else:
                assert ("external eccentric moment" in text or name == "inside-e1-envelope")
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            manifest.append({"candidate_sha": sha, "platform": platform.platform(), "case": name, "mode": mode, "file": filename, "pages": len(pages), "bytes": len(pdf), "sha256": hashlib.sha256(pdf).hexdigest().upper(), "snapshot_digest": snapshot.digest, "checks": supported(result), "integration": {k: integration[k] for k in ["required_check_ids", "unsupported_required_check_ids", "incomplete_required_check_ids", "not_required_check_ids", "failed_check_ids", "governing_supported_check_ids", "overall_disposition"]}, "demand": result["native_design"]["automatic_demand_result"], "rc3_production_activation": False})
            manifest[-1]["tracked_working_tree_modified"] = dirty
            print(f"{filename}: {len(pages)} pages", flush=True)
        assert (snapshot.request, snapshot.result) == before
        for kind, payload in (("request", snapshot.request), ("result", snapshot.result)):
            (output / (name + "-signed-" + kind + ".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (output / (name + "-api-request.json")).write_text(json.dumps(body, indent=2), encoding="utf-8")
    (output / "DIRECT_F6_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
if __name__ == "__main__":
    main()
