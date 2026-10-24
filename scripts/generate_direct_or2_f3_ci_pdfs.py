"""Actual signed-snapshot F3 physical-edge and hardware PDFs on each CI runner."""

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pypdf import PdfReader
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_direct_or2_f3 import f3_request
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    signer = SnapshotSigner(b"DIRECT-F3-PLATFORM-PDF-QA-32-BYTES")
    manifest = []
    for case in ("owner", "45", "free-edge", "patch-only", "web", "heel", "edge-only", "red", "si-owner"):
        si = case == "si-owner"
        body = owner_body(si=si)
        body["legacy_request"] = f3_request("owner" if case in {"red", "si-owner"} else case, si=si)
        if case == "red":
            body["legacy_request"]["physical_connection"]["joint_assembly"][
                "member_end_actions"][0]["force"]["x"] = "7"
        response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
        assert response.status_code == 200, response.text
        result = response.json()
        preview = result["native_design"]["preview"]
        invalid = case in {"45", "free-edge", "web", "heel", "edge-only"}
        assert preview["geometry_status"] == ("INVALID_GEOMETRY" if invalid else "VALID")
        assert len(preview["direct_engineering_geometry"]) == (8 if case == "patch-only" else 4)
        if case == "red":
            assert result["overall_status"] == "FAIL"
        if case in {"owner", "si-owner"}:
            face = next(f for f in preview["direct_engineering_geometry"]
                        if f["component_id"] == "member-a" and f["bolt_id"] == "B_R1_L1")
            end = next(c for c in face["checks"] if c["check_kind"] == "CHAPTER_8_END_DISTANCE")
            assert end["actual_distance"] == ("76.2" if si else "3")
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design",
            request=body, result=result, account_id="f3-platform"), account_id="f3-platform")
        original = deepcopy((snapshot.request, snapshot.result))
        modes = ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if case == "owner" else ("ENGINEER_REPORT",)
        for mode in modes:
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            reader = PdfReader(io.BytesIO(pdf))
            text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
            assert "Direct angle-to-W connection" in text
            assert "NOT AN ENGINEERING EDGE UNLESS MAPPED" in text
            assert len(reader.pages) <= 10 if mode == "ENGINEER_REPORT" else len(reader.pages) > 100
            if case == "45":
                assert "Chapter 8 loaded-end distance" in text and "0.085786" in text
            if case == "free-edge":
                assert "Chapter 8 physical free-edge distance" in text and "0.086047" in text
            if case in {"web", "heel"}:
                assert "Washer seating / hardware clearance" in text
            filename = f"direct-or2-f3-{case}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            (output / f"{filename}.txt").write_text(text, encoding="utf-8")
            manifest.append({"candidate_sha": sha, "working_tree_modified": dirty,
                "platform": platform.platform(), "case": case, "mode": mode,
                "file": filename, "pages": len(reader.pages), "bytes": len(pdf),
                "sha256": hashlib.sha256(pdf).hexdigest().upper(),
                "signed_snapshot_digest": snapshot.digest, "geometry_status": preview["geometry_status"]})
            assert (snapshot.request, snapshot.result) == original
            print(f"{filename}: {len(reader.pages)} pages")
        (output / f"{case}-signed-request.json").write_text(json.dumps(snapshot.request, indent=2), encoding="utf-8")
        (output / f"{case}-signed-result.json").write_text(json.dumps(snapshot.result, indent=2), encoding="utf-8")
    (output / "DIRECT_OR2_F3_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
