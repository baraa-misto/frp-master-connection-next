"""F4 actual Windows/Ubuntu signed catalog reports and numerical checks."""
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
from tests.api.test_f593_f4 import design, f4_body, supported
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    cases = {
        "owner-cw1-excluded": f4_body(),
        "owner-cw1-included": f4_body(thread="INCLUDED"),
        "cw2-excluded": f4_body(diameter=".75"),
        "cw2-included": f4_body(diameter=".75", thread="INCLUDED"),
        "unsupported-cw-gap": f4_body(diameter=".7"),
        "bolt-numerical-red": f4_body(),
        "si-12p7": f4_body(si=True),
        "si-19p05": f4_body(si=True, diameter="19.05"),
        "thread-unresolved": f4_body(thread="UNKNOWN"),
    }
    cases["bolt-numerical-red"]["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["x"] = "-100"
    signer = SnapshotSigner(b"F593-F4-PLATFORM-REPORT-32-BYTE-KEY")
    manifest = []
    for name, body in cases.items():
        result = design(body)
        source = result["fastener_source"]
        rows = [c for c in supported(result) if c["limit_state"] == "BOLT_SHEAR"]
        if name == "unsupported-cw-gap":
            assert source["fnt"] is None and not rows
        elif name == "thread-unresolved":
            assert source["fnt"]["value"] == "100" and not rows
        else:
            assert len(rows) == 2
            assert source["fnt"]["value"] == ("85" if name.startswith("cw2") or name == "si-19p05" else "100")
        if name == "bolt-numerical-red":
            assert result["overall_status"] == "FAIL"
            assert all(c["numerical_comparison"] == "FAIL" for c in rows)
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, account_id="f4-platform"), account_id="f4-platform")
        original = deepcopy((snapshot.request, snapshot.result))
        modes = ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "owner-cw1-excluded" else ("ENGINEER_REPORT",)
        for mode in modes:
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"f593-f4-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "OWNER_APPROVED_ASTMF593_TABLE_TRANSCRIPTION_RC1" in text
            assert "ASTM_F593_17_GROUP_2_316_316L_RC1" in text
            assert "No per-connection supplier certification required" in text
            if rows:
                assert "Catalog-resolved native bolt shear calculations" in text or mode == "FULL_TECHNICAL_AUDIT"
                assert "F_nv" in text
            if name == "unsupported-cw-gap":
                assert "No controlled cold-worked ASTM F593 table row" in text
            if mode == "FULL_TECHNICAL_AUDIT":
                raw_text = "".join(text.split())
                assert "catalog_digest" in raw_text and "tensile_max" in raw_text and "0.6 Fnt" in text
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            manifest.append({"candidate_sha": sha, "working_tree_modified": dirty, "platform": platform.platform(),
                "case": name, "mode": mode, "file": filename, "pages": len(pages), "bytes": len(pdf),
                "sha256": hashlib.sha256(pdf).hexdigest().upper(), "snapshot_digest": snapshot.digest,
                "catalog_source": source, "bolt_results": rows})
            print(f"{filename}: {len(pages)} pages", flush=True)
        assert (snapshot.request, snapshot.result) == original
        (output / (name + "-signed-request.json")).write_text(json.dumps(snapshot.request, indent=2), encoding="utf-8")
        (output / (name + "-signed-result.json")).write_text(json.dumps(snapshot.result, indent=2), encoding="utf-8")
    (output / "F593_F4_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
